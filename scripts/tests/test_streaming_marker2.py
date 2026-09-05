import copy
import hashlib
import struct
import unittest
from unittest.mock import patch
from scripts.game_data import streaming as fmt,streaming_pairs as pairs
from scripts.tests.test_streaming import _packed,_parallel_target_data_root
from scripts.game_data import streaming_marker2 as parser

SOURCE='Data/Streaming/PC/test/Streaming/StreamingChunkData_1_2_0_0.bytes'

def prepare(data,*,family='streaming'):
    data=bytes(data)
    parsed=fmt.parse_streaming_file(family,_packed(data),include_certified_ranges=True,native_layout_validated=True)
    identity={'virtualPath':SOURCE,'physicalChunkPath':'D:/synthetic/A.chk','physicalChunkSource':'fallback',
        'metadataProvenance':'primary','overlayState':'identical','offset':0,'length':len(_packed(data)),
        'packedSha256':hashlib.sha256(_packed(data)).hexdigest().upper()}
    witness=copy.deepcopy(parsed['anonymousParallelSubgraph']['orderedRootWitness'])
    left={**identity,'virtualPath':SOURCE.replace('/StreamingChunkData_','/InitChunkData_'),
          'witness':{**witness,'rowField0ValuesSha256':'D'*64}}
    right={**identity,'witness':witness}
    pair={'init':left,'streaming':right,'status':'exact-ordered-witness-match','differences':[]}
    report={'layer3':{'pairedRootIdentities':{'status':'exact-ordered-witness-matches','candidatePairCount':1,
        'matchedPairCount':1,'mismatchedPairCount':0,'unpairedFileCount':0,'unpairedFiles':[],'pairs':[pair]}}}
    context=pairs.bind_current_pair(pair_index=pairs.index_ordered_pairs(report),identity=identity,decoded=data,
                                   parsed=parsed,root_report_sha256='F'*64)
    return data,parsed,context

def fixture(*,gap=4,word=0,tail=b'\xA5\xFF',selector=6,key=0x09020000,
            second_marker=15,second_target=332,duplicate_key=False,selector_absent=False,family='streaming'):
    data=bytearray(_parallel_target_data_root())
    field0=bytes(data[260:268])
    struct.pack_into('<I',data,148,252+gap-148)
    data[252+gap:260+gap]=field0
    struct.pack_into('<I',data,156,selector)
    if selector_absent:struct.pack_into('<H',data,136,0)
    struct.pack_into('<II',data,224,key,key if duplicate_key else 0x09010000)
    data[236:238]=bytes((2,second_marker))
    struct.pack_into('<II',data,244,252-244,second_target-248)
    struct.pack_into('<I',data,252,word)
    if gap==6:data[256:258]=tail
    return prepare(data,family=family)

def parse(parts,**kwargs):
    data,parsed,context=parts
    return parser.parse_marker2_gaps(data,source=SOURCE,family=kwargs.pop('family','streaming'),parsed=kwargs.pop('parsed',parsed),
        pair_context=kwargs.pop('pair_context',context),native_layout_validated=kwargs.pop('native_layout_validated',True),**kwargs)

class Marker2ParserTests(unittest.TestCase):
    def test_normal4_actual_pair_binding(self):
        result=parse(fixture(word=0xffffffff))
        row=result['rows'][0]
        self.assertEqual(row['status'],'framed');self.assertEqual(row['anonymousU32'],0xffffffff)
        self.assertEqual(row['pairRow']['outerRowOffset'],144)
        self.assertEqual(row['nativeReadWindowRange'],{'start':252,'end':256,'length':4})
        self.assertEqual(result['summary'],dict(references=1,framed=1,unsupported=0,ambiguous=0,
            physicalGapBytes=4,nativeReadWindowBytes=4,opaqueBytes=0,targetOwnedBytes=0))
    def test_normal6_nonzero_opaque_arbitrary_scalar(self):
        result=parse(fixture(gap=6,word=123))
        row=result['rows'][0]
        self.assertEqual(row['physicalGapRange']['length'],6)
        self.assertEqual(row['residualOpaqueRange']['bytesHex'],'A5FF')
        self.assertEqual(row['nativeReadWindowRange']['length'],4)
        self.assertEqual(result['summary']['opaqueBytes'],2)
        self.assertEqual(row['targetOwnedBytes'],0)
    def test_unknown_exclusive_gap5_and8_fail(self):
        for length in (5,8):
            with self.subTest(length=length),self.assertRaisesRegex(ValueError,'exclusive physical gap length4 or6'):
                parse(fixture(gap=length))
    def test_known_cluster_unsupported_no_pair_read_projection(self):
        result=parse(fixture(gap=8,word=0xffffffff,second_target=256),pair_context=None)
        row=result['rows'][0]
        self.assertEqual(row['status'],'unsupported-cluster')
        self.assertNotIn('anonymousU32',row);self.assertNotIn('pairRow',row)
        self.assertEqual(result['summary']['nativeReadWindowBytes'],0)
    def test_alias_is_ambiguous(self):
        result=parse(fixture(second_target=252),pair_context=None)
        self.assertEqual(result['rows'][0]['status'],'ambiguous-target')
        self.assertEqual(result['summary']['ambiguous'],1)
    def test_interior_target_is_ambiguous(self):
        self.assertEqual(parse(fixture(second_target=254))['rows'][0]['status'],'ambiguous-target')
    def test_complete_key_duplicate_ambiguous(self):
        result=parse(fixture(duplicate_key=True))
        self.assertEqual(result['rows'][0]['status'],'ambiguous-key')
        self.assertEqual(result['rows'][0]['keyOccurrenceCountInTable'],2)
    def test_unknown_marker_occupancy_is_unsupported(self):
        result=parse(fixture(second_marker=255),pair_context=None)
        self.assertEqual(result['rows'][0]['status'],'unsupported-occupancy')
        self.assertEqual(result['directory']['unresolvedMarkerRows'][0]['marker'],255)
        self.assertNotIn('targetStart',result['directory']['unresolvedMarkerRows'][0])
    def test_unknown_marker_rawslot_not_coerced_to_target(self):
        data,_,_=fixture(second_marker=255)
        for word in (0,0xffffffff):
            changed=bytearray(data);struct.pack_into('<I',changed,248,word)
            self.assertEqual(parse(prepare(changed),pair_context=None)['rows'][0]['status'],'unsupported-occupancy')
    def test_wrong_context_and_absent_not_defaulted(self):
        for args in ({'selector':262},{'selector_absent':True},{'key':0xff000000}):
            result=parse(fixture(**args),pair_context=None)
            self.assertEqual(result['rows'][0]['status'],'unsupported-context')
    def test_init_directory_no_streaming_pair_required(self):
        result=parse(fixture(family='init'),family='init',pair_context=None)
        self.assertEqual(result['rows'][0]['status'],'unsupported-context')
        self.assertEqual(result['directory']['counts']['marker2References'],1)
    def test_default_gate_closed(self):
        with self.assertRaisesRegex(ValueError,'native gate'):
            parse(fixture(),native_layout_validated=False)
    def test_malformed_parser_projection_diagnostic(self):
        with self.assertRaisesRegex(ValueError,'parsed root: expected mapping'):
            parse(fixture(),parsed=None)
    def test_bare_or_missing_pair_rejected_for_finite(self):
        for context in (None,True,False):
            with self.assertRaisesRegex(ValueError,'structured current source-pair'):
                parse(fixture(),pair_context=context)
    def test_pair_source_sha_rowvector_or_marker_mismatch(self):
        parts=fixture()
        for key,value in [('source','other.bytes'),('decodedSha256','0'*64),('rowVectorStart',0),('markerVectorStart',0)]:
            with self.subTest(key=key),self.assertRaises(ValueError):
                parse(parts,pair_context={**parts[2],key:value})
    def test_truncated_payload_and_trailing_payload(self):
        data,parsed,context=fixture()
        for changed in (data[:-1],data+b'X'):
            with self.assertRaisesRegex(ValueError,'decoded length'):
                parse((changed,parsed,context))
    def test_target_zero_offset_and_malformed_count(self):
        data,parsed,context=fixture()
        for offset,value in ((244,0),(244,0xffffffff),(232,0xffffffff)):
            changed=bytearray(data);struct.pack_into('<I',changed,offset,value)
            with self.assertRaises(ValueError):parse((bytes(changed),parsed,context))
    def test_actual_selector_read_is_not_directory_trusted(self):
        parts=fixture()
        original=parser.directory_module.collect_marker2_directory
        def forged(*args,**kwargs):
            doc=original(*args,**kwargs);doc['rows'][0]['rowSelectorOffset']=152;return doc
        with patch.object(parser.directory_module,'collect_marker2_directory',side_effect=forged):
            with self.assertRaisesRegex(ValueError,'rowSelectorOffset'):parse(parts)
    def test_collector_called_once_and_profile_not_mutable(self):
        original=parser.directory_module.collect_marker2_directory
        with patch.object(parser.directory_module,'collect_marker2_directory',wraps=original) as mock:
            result=parse(fixture());self.assertEqual(mock.call_count,1)
        result['profile']['physicalGapLengths'].append(8)
        with self.assertRaisesRegex(ValueError,'exclusive physical gap length4 or6'):parse(fixture(gap=8))

if __name__=='__main__':unittest.main()
