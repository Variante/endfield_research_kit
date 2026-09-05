import copy
import json
import struct
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.game_data import streaming_marker2_native as n

def fixture():
    doc=json.loads(n.DEFAULT_CONTRACT.read_text())
    rows=doc['unityPlayerRanges']
    image=bytearray(0x400+len(rows)*0x200)
    struct.pack_into('<I',image,0x3c,0x80)
    image[0x80:0x84]=b'PE\0\0'
    struct.pack_into('<H',image,0x86,len(rows))
    for i,row in enumerate(rows):
        off=0x400+i*0x200
        body=bytes([i+1])*row['size']
        if row['role']=='selector6FullCountKeyLiteral':body=struct.pack('<3I',9,2,0)
        image[off:off+len(body)]=body
        struct.pack_into('<IIII',image,0x98+i*40+8,0x200,row['rva'],0x200,off)
        row.update(fileOffset=off,bodySha256=n.sha256(body),entryBytesHex=body[:32].hex().upper())
    inputs=dict(n.EXPECTED_INPUTS,unityPlayerSha256=n.sha256(image))
    doc['nativeInputs']=inputs
    return doc,bytes(image),inputs

class RangeTests(unittest.TestCase):
    def setUp(self):self.doc,self.image,self.inputs=fixture()
    def validate(self,rows=None,image=None):
        return n._validate_ranges(self.image if image is None else image,
            self.doc['unityPlayerRanges'] if rows is None else rows,n.EXPECTED_RANGES)
    def test_normal_six_exact_roles(self):self.assertEqual(self.validate(),[])
    def test_truncated_source(self):
        failures=self.validate(image=self.image[:-0x200])
        self.assertTrue(any(f['gate'].endswith('.bounded_range') for f in failures))
        self.assertIn('expected',failures[-1]);self.assertIn('actual',failures[-1])
        self.assertIn('rva',failures[-1])
    def test_cross_section_and_virtual_only_span(self):
        image=bytearray(self.image)
        struct.pack_into('<I',image,0x98+16,228)
        failures=self.validate(image=bytes(image))
        self.assertTrue(any('raw end' in str(f['actual']) for f in failures))
    def test_malformed_section_count(self):
        image=bytearray(self.image)
        struct.pack_into('<H',image,0x86,0xffff)
        rows=copy.deepcopy(self.doc['unityPlayerRanges']);rows[0]['rva']=0xffffffff
        self.assertTrue(self.validate(rows=rows,image=bytes(image)))
    def test_body_hash_and_entry_and_offset(self):
        for key,value in [('bodySha256','0'*64),('entryBytesHex','FF'),('fileOffset',0)]:
            rows=copy.deepcopy(self.doc['unityPlayerRanges']);rows[0][key]=value
            self.assertTrue(any(f['gate'].endswith('.'+{'bodySha256':'body_sha256','entryBytesHex':'entry_bytes','fileOffset':'file_offset'}[key]) for f in self.validate(rows=rows)))
    def test_duplicate_missing_unknown_role(self):
        for rows in (self.doc['unityPlayerRanges'][:-1],self.doc['unityPlayerRanges']+[self.doc['unityPlayerRanges'][0]],
                     [dict(self.doc['unityPlayerRanges'][0],role='unreviewed')]+self.doc['unityPlayerRanges'][1:]):
            self.assertTrue(any(f['gate']=='range_role_catalog' for f in self.validate(rows=rows)))
    def test_wrong_rva_size_or_bool(self):
        for key,value in [('rva',1),('size',0),('size',230),('rva',True)]:
            rows=copy.deepcopy(self.doc['unityPlayerRanges']);rows[0][key]=value
            self.assertTrue(self.validate(rows=rows))

class PublicGateTests(unittest.TestCase):
    def run_gate(self,*,mutate=None,wrong_sha=False,native_status='validated',image_change=False):
        doc,image,inputs=fixture()
        if mutate:mutate(doc)
        raw=(json.dumps(doc,indent=2)+'\n').encode()
        candidate=Path('synthetic_marker2.json')
        root=Path('synthetic_game')/'Endfield_Data'
        original=Path.read_bytes
        def read(path):
            if path==candidate:return raw
            if path==root.parent/'UnityPlayer.dll':return image+b'X' if image_change else image
            return original(path)
        gate=dict(status=native_status,contractSha256=n.DEPENDENCY_SHA256,nativeInputs=inputs,validationFailures=[])
        with patch.object(Path,'read_bytes',read),patch.object(n,'CONTRACT_SHA256','0'*64 if wrong_sha else n.sha256(raw)),\
             patch.object(n,'EXPECTED_INPUTS',inputs),patch.object(n.dependency,'validate_marker17_native_contract',return_value=gate):
            return n.validate_marker2_native_contract(game_root=root,contract_path=candidate)
    def assert_closed(self,result):
        self.assertEqual(result['status'],'validation_failed')
        self.assertIsNone(result['profile']);self.assertIsNone(result['consumerReview']);self.assertIsNone(result['evidenceBoundary'])
        self.assertTrue(result['validationFailures'])
    def test_synthetic_full_success(self):
        result=self.run_gate()
        self.assertEqual(result['status'],'validated')
        self.assertEqual(result['profile']['allowedWordValues'],'all-u32-bit-patterns')
        self.assertEqual(result['profile']['targetOwnedBytes'],0)
    def test_stale_contract_and_native_gate(self):
        self.assert_closed(self.run_gate(wrong_sha=True))
        self.assert_closed(self.run_gate(native_status='mismatched'))
    def test_image_changed_after_gate(self):self.assert_closed(self.run_gate(image_change=True))
    def test_wrong_context_or_semantic_validity_requirement(self):
        for key,value in [('rawSelector',None),('rawSelector',262),('marker',15),('readWidth',6),
                          ('allowedWordValues','zero-only'),('targetOwnedBytes',4)]:
            with self.subTest(key=key):
                self.assert_closed(self.run_gate(mutate=lambda d:d['profile'].update({key:value})))
    def test_dependency_catalog_and_registration(self):
        self.assert_closed(self.run_gate(mutate=lambda d:d['baseContract']['requiredUnityPlayerRoles'].append('unreviewed')))
        self.assert_closed(self.run_gate(mutate=lambda d:d['dependency']['registration'].update(selector=9)))
    def test_hash_matching_contract_wrong_literal(self):
        # Per-role byte validation must still reject forged selected body evidence.
        self.assert_closed(self.run_gate(mutate=lambda d:d['unityPlayerRanges'][1].update(bodySha256='0'*64)))

if __name__=='__main__':unittest.main()
