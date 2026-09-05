from __future__ import annotations

import base64
import gzip
import hashlib
import json
import tempfile
import unittest
import struct
from contextlib import ExitStack
from pathlib import Path
from unittest import mock

from scripts.game_data.memorypack import buff_corpus as gate
from scripts.game_data.memorypack.schemas import BUFF_MEMBER_COUNT


def _payload() -> bytes:
    """Minimal current-build shape: correct member count, no id anchor."""
    return bytes([BUFF_MEMBER_COUNT]) + b"\x00" * 32


def _ledger_row(path: Path, data: bytes, *, virtual_path: str = "Data/Json/BuffData/fixture.json") -> dict:
    raw = path.read_bytes()
    return {
        "recordType": "file",
        "inputSetSha256": "A" * 64,
        "status": "verified",
        "boundaryStatus": "boundary_verified",
        "overlayState": "primary_only",
        "chunkOverlayState": "primary_only",
        "blockName": "JsonData",
        "blockTypeValue": 19,
        "hashDirectory": "775A31D1",
        "chunkFile": path.name,
        "fileName": virtual_path,
        "virtualPath": virtual_path,
        "offset": 0,
        "length": len(data),
        "actualBytesRead": len(data),
        "physicalChunkPath": str(path),
        "physicalChunkSource": "primary",
        "physicalChunkRoot": str(path.parent),
        "metadataProvenance": "primary",
        "encrypted": True,
        "fileChunkMd5LittleEndianHex": hashlib.md5(raw).hexdigest().upper(),
        "recomputedFileDataMd5": hashlib.md5(data).hexdigest().upper(),
    }


def _stream_row(data: bytes, *, path: str = "Data/Json/BuffData/fixture.json") -> dict:
    return {
        "blockType": "JsonData",
        "blockTypeValue": 19,
        "fileName": path,
        "length": len(data),
        "dataBase64": base64.b64encode(data).decode("ascii"),
    }


def _normal():
    p=struct.pack
    marker=p('<I',7)+b'fixture'
    scalar=b'\x03'+bytes(5)+p('<i',1)
    stack=b'\x0c\x00\x00'+p('<i',1)+bytes(20)
    tail=bytes(7)+scalar+b'\x00'+bytes(8)+stack+bytes(13)+scalar+bytes(2)
    return b'\x1e'+marker+tail


class BuffCandidateTests(unittest.TestCase):
    def frame(self,data):return gate.frame_candidates(data,source='Data/Json/BuffData/fixture.json')

    def test_normal_candidate_does_not_claim_whole_schema(self):
        row=self.frame(_normal())
        self.assertEqual(row['coverageStatus'],'unique')
        self.assertFalse(row['wholeSchemaExact'])
        self.assertFalse(row['candidates'][0]['readerInternalOpaqueRangesCertified'])

    def test_truncated_trailing_and_malformed_count(self):
        good=_normal()
        bad_count=good[:12]+struct.pack('<I',257)+good[16:]
        for bad in (good[:-1],good+b'!',bad_count,b'\x1f'+good[1:]):
            with self.subTest(length=len(bad)):
                self.assertEqual(self.frame(bad)['coverageStatus'],'unsupported')

    def test_all_anchors_kept_even_if_one_is_rejected(self):
        raw=b'\x1e'+struct.pack('<I',7)+b'fixture'+b'\xff'*4+_normal()[1:]
        row=self.frame(raw)
        self.assertEqual((row['anchorCount'],row['candidateCount']),(2,1))
        self.assertEqual(len(row['candidates']),2)

    def test_ambiguity_is_preserved_not_arbitrarily_selected(self):
        raw=b'\x1e'+(struct.pack('<I',7)+b'fixture')*2
        with mock.patch.object(gate,'decode_buff_post_id_prefix_at',return_value={
            'status':'parsed-through-exact-tail','endOffset':hex(len(raw))}):
            row=self.frame(raw)
        self.assertEqual((row['coverageStatus'],row['candidateCount']),('ambiguous',2))

    def test_false_reader_eof_and_search_limit_fail_closed(self):
        with mock.patch.object(gate,'decode_buff_post_id_prefix_at',return_value={
            'status':'parsed-through-exact-tail','endOffset':'0x1'}):
            with self.assertRaises(gate.vfs.CensusGateError):self.frame(_normal())
        raw=b'\x1e'+(struct.pack('<I',7)+b'fixture')*65
        row=self.frame(raw)
        self.assertEqual(row['coverageStatus'],'unsupported')
        self.assertEqual(row['candidates'],[])


class BuffJoinTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/('A'*32+'.chk')
        self.data=_normal();self.path.write_bytes(self.data)
        self.ledger=_ledger_row(self.path,self.data)

    def test_normal_and_no_anchor_denominators(self):
        selected=gate.select_rows([self.ledger],expected_input='A'*64)
        rows=gate.join_and_frame(selected,[_stream_row(self.data)],stderr='Streamed 1 files\n')
        self.assertEqual(rows[0]['coverageStatus'],'unique')
        self.assertEqual(rows[0]['logicalSha256'],hashlib.sha256(self.data).hexdigest().upper())
        self.assertEqual(gate.frame_candidates(_payload(),source='fixture.json')['coverageStatus'],'unsupported')

    def test_ledger_identity_offset_count_and_fingerprint_failures(self):
        for change in ({'offset':1},{'length':True},{'inputSetSha256':'B'*64},{'encrypted':False},
                       {'actualBytesRead':0},{'recomputedFileDataMd5':'bad'}):
            with self.subTest(change=change),self.assertRaises(gate.vfs.CensusGateError):
                gate.select_rows([{**self.ledger,**change}],expected_input='A'*64)
        with self.assertRaises(gate.vfs.CensusGateError):
            gate.select_rows([self.ledger,self.ledger],expected_input='A'*64)

    def test_stream_missing_duplicate_hash_length_and_terminal_failures(self):
        good=_stream_row(self.data)
        bad_hash=_stream_row(bytes(len(self.data)))
        for stream,stderr in (([], 'Streamed 0 files'),([good,good],'Streamed 2 files'),
            ([bad_hash],'Streamed 1 files'),([{**good,'length':1}],'Streamed 1 files'),
            ([{**good,'dataBase64':'!'}],'Streamed 1 files'),([good],'Streamed 2 files'),
            ([{**good,'fileName':'other'}],'Streamed 1 files')):
            with self.subTest(stream=stream),self.assertRaises(gate.vfs.CensusGateError):
                gate.join_and_frame([self.ledger],stream,stderr=stderr)

    def build(self, *, drift=None, outputs=()):
        root=Path(self.temp.name)
        cli=root/'cli.exe'
        outer={'primaryAssets':str(root/'primary'),'fallbackAssets':str(root/'fallback')}
        for value in outer.values():Path(value).mkdir(exist_ok=True)
        fingerprint={'path':str(cli),'length':1,'sha256':'A'*64}
        provenance={'sourceFingerprints':[fingerprint],'buildFingerprints':[fingerprint]}
        returned=(outer,{},[self.ledger],provenance)
        with ExitStack() as patches:
            patches.enter_context(mock.patch.object(gate.vfs,'_read_outer_and_ledger',return_value=returned))
            for name in ('_chunk_fingerprints','_chunk_selection_snapshot','_stream_tool_snapshot','_parser_source_snapshots'):
                patches.enter_context(mock.patch.object(gate.vfs,name,side_effect=[
                    [fingerprint],[{**fingerprint,'sha256':'B'*64}] if drift==name else [fingerprint]]))
            patches.enter_context(mock.patch.object(gate.vfs,'_fingerprint',return_value=fingerprint))
            patches.enter_context(mock.patch.object(gate,'_read_stream_rows',return_value=([_stream_row(self.data)],'Streamed 1 files')))
            return gate.build_current_census(outer_path=root/'outer.json',ledger_path=root/'ledger.gz',
                cli_path=cli,expected_input_set_sha256='A'*64,outputs=outputs)

    def test_build_partitions_denominator_and_pins_reusable_provenance(self):
        report=self.build()
        summary=report['summary']
        self.assertEqual(summary['filesSelected'],summary['filesSucceeded']+summary['filesFailed']+summary['filesUnsupported'])
        self.assertEqual(summary['filesUnique'],1)
        self.assertIn('selectedChunkResolution',report['provenance'])
        self.assertIn('corpusGate',report['provenance'])
        self.assertFalse(report['wholeSchemaExact'])

    def test_chunk_overlay_tool_and_parser_drift_have_specific_diagnostics(self):
        for name in ('_chunk_fingerprints','_chunk_selection_snapshot','_stream_tool_snapshot','_parser_source_snapshots'):
            with self.subTest(name=name),self.assertRaises(gate.vfs.CensusGateError) as caught:self.build(drift=name)
            self.assertEqual(caught.exception.diagnostic['code'],'buff-corpus-input-drift')
            self.assertNotEqual(caught.exception.diagnostic['expected'],caught.exception.diagnostic['actual'])

    def test_output_cannot_overwrite_input_or_alias_other_output(self):
        root=Path(self.temp.name)
        for outputs in ((self.path,), (root/'primary'/'report.json',), (root/'out.json',root/'out.json')):
            with self.subTest(outputs=outputs),self.assertRaises(gate.vfs.CensusGateError):self.build(outputs=outputs)


if __name__=='__main__':unittest.main()


