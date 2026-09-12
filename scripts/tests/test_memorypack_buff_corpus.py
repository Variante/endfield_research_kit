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
        self.assertIn(row['boundaryClass'],('structural-prefix','failed','unsupported'))

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
        self.assertEqual(row['candidates'][0]['boundaryClass'],'rejected-anchor')
        self.assertEqual(gate.boundary_evidence_summary([row])['unsupportedCandidates'],0)
        self.assertEqual(gate.boundary_evidence_summary([row])['rejectedAnchorCandidates'],1)

    def test_ambiguity_is_preserved_not_arbitrarily_selected(self):
        raw=b'\x1e'+(struct.pack('<I',7)+b'fixture')*2
        with mock.patch.object(gate,'decode_buff_post_id_prefix_at',return_value={
            'status':'parsed-through-exact-tail','endOffset':hex(len(raw))}):
            row=self.frame(raw)
        self.assertEqual((row['coverageStatus'],row['candidateCount']),('ambiguous',2))
        with mock.patch.object(gate,'decode_buff_post_id_prefix_at',return_value={
            'status':'parsed-through-exact-tail','endOffset':hex(len(raw))}),mock.patch.object(
                gate,'event_prefix',return_value={'status':'supported-prefix','consumedEnd':1}),mock.patch.object(
                gate,'root_continuation',return_value={'status':'supported-prefix'}):
            row=self.frame(raw)
        self.assertEqual(row['eventPrefixStatus'],'ambiguous')
        self.assertEqual(row['rootContinuationStatus'],'ambiguous')

    def test_root_continuation_joins_supported_first_collection(self):
        prefix=b'\x1e'+bytes(4)
        segment=b'\xff'+struct.pack('<i',2)+bytes(8)+b'\x02'+struct.pack('<i',-1)+b'\x7f'+struct.pack('<i',0)+struct.pack('<i',0)
        raw=prefix+segment+b'opaque'+_normal()[1:]
        row=self.frame(raw)
        self.assertEqual(row['rootContinuationStatus'],'success')
        candidate=row['candidates'][0]
        continued=candidate['currentRootContinuation']
        self.assertEqual(continued['startOffset'],candidate['currentEventPrefix']['consumedEnd'])
        self.assertEqual(continued['consumedEnd'],len(prefix+segment))
        self.assertEqual(continued['boundaryClass'],'structural-prefix')
        self.assertEqual(continued['parserCursor'],continued['consumedEnd'])
        self.assertEqual(continued['hardLimit'],candidate['anchorOffset'])
        self.assertEqual(candidate['boundaryClass'],'structural-prefix')
        self.assertEqual(continued['opaqueRemainderRange'],[len(prefix+segment),len(raw)])
        bad=prefix+b'\xff'+struct.pack('<i',-2)+_normal()[1:]
        row=self.frame(bad)
        self.assertEqual(row['eventPrefixStatus'],'success')
        self.assertEqual(row['rootContinuationStatus'],'failed')
        self.assertEqual(row['candidates'][0]['currentRootContinuation']['diagnostic']['category'],'count-bounds')

    def test_boundary_summary_keeps_closed_prefix_opaque_and_uncertain_counts_separate(self):
        rows=[
            {'boundaryClass':'ambiguous','candidates':[
                {'boundaryClass':'structural-prefix','exactClosedActionRecords':2,
                 'opaqueByteRanges':[{'start':20,'end':30,'kind':'opaque-before-hard-limit'}]}]},
            {'boundaryClass':'unsupported','candidates':[
                {'boundaryClass':'unsupported','exactClosedActionRecords':1,
                 'opaqueByteRanges':[{'start':8,'end':13,'kind':'opaque-before-hard-limit'},
                                     {'start':13,'end':17,'kind':'opaque-after-hard-limit'}]}]},
            {'boundaryClass':'failed','candidates':[
                {'boundaryClass':'failed','exactClosedActionRecords':0,'opaqueByteRanges':[]}]},
            {'boundaryClass':'unsupported','candidates':[
                {'boundaryClass':'rejected-anchor','exactClosedActionRecords':0,'opaqueByteRanges':[]}]},
        ]
        summary=gate.boundary_evidence_summary(rows)
        self.assertEqual(summary['exactClosedActionRecords'],3)
        self.assertEqual(summary['structuralPrefixCandidates'],1)
        self.assertEqual(summary['opaqueBytesByCandidate'],19)
        self.assertEqual(summary['unsupportedCandidates'],1)
        self.assertEqual(summary['failedCandidates'],1)
        self.assertEqual(summary['rejectedAnchorCandidates'],1)
        self.assertEqual(summary['ambiguousFiles'],1)
        self.assertIn('whole-record',summary['boundary'])

    def test_joined_boundaries_bind_input_identity_hash_and_hard_limit(self):
        data=_normal()
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'fixture.chk';path.write_bytes(data)
            identity=_ledger_row(path,data)
            rows=gate.join_and_frame([identity],[_stream_row(data)],stderr='Streamed 1 files\n')
        candidate=rows[0]['candidates'][0]
        context=candidate['boundaryContext']
        self.assertEqual(context['inputSetSha256'],'A'*64)
        self.assertEqual(context['logicalFileIdentity'],identity['virtualPath'])
        self.assertEqual(context['logicalSha256'],rows[0]['logicalSha256'])
        self.assertEqual(context['startOffset'],candidate['startOffset'])
        self.assertEqual(context['hardLimit'],candidate['anchorOffset'])
        profile=candidate.get('currentRootContinuation') or candidate['currentEventPrefix']
        self.assertEqual(profile['boundaryContext'],context)
        self.assertEqual(profile['parserCursor'],profile['consumedEnd'])
        self.assertEqual(candidate['byteRanges'],profile['ranges'])

    def test_current_event_profile_has_independent_status_and_bounded_gap(self):
        raw=b'\x1e'+bytes(4)+_normal()[1:]
        row=self.frame(raw)
        self.assertEqual(row['eventPrefixStatus'],'success')
        profile=row['candidates'][0]['currentEventPrefix']
        self.assertEqual(profile['consumedEnd'],5)
        self.assertEqual(profile['readLimit'],5)
        self.assertEqual(profile['opaqueRemainderRange'],[5,len(raw)])
        malformed=b'\x1e'+struct.pack('<i',-2)+_normal()[1:]
        row=self.frame(malformed)
        self.assertEqual(row['coverageStatus'],'unique')
        self.assertEqual(row['eventPrefixStatus'],'failed')
        self.assertEqual(row['candidates'][0]['currentEventPrefix']['diagnostic']['category'],'count-bounds')

    def test_false_reader_eof_and_search_limit_fail_closed(self):
        with mock.patch.object(gate,'decode_buff_post_id_prefix_at',return_value={
            'status':'parsed-through-exact-tail','endOffset':'0x1'}):
            with self.assertRaises(gate.vfs.CensusGateError):self.frame(_normal())
        raw=b'\x1e'+(struct.pack('<I',7)+b'fixture')*65
        row=self.frame(raw)
        self.assertEqual(row['coverageStatus'],'unsupported')
        self.assertEqual(row['candidates'],[])

    def test_prefix_limit_rejects_invalid_or_truncated_anchors(self):
        raw=b'\x1e'+bytes(4)+b'\x03'+bytes(9)+bytes(4)+b'\x02'+bytes(5)
        reader=gate.decode_buff_pre_id_modifier_prefix
        good=reader(raw,len(raw))
        self.assertEqual(good['status'],'parsed-through-attribute-modifier')
        for limit in (-1,True,'25',len(raw)+1,2,4,6,len(raw)-1):
            with self.subTest(limit=limit):self.assertEqual(reader(raw,limit)['status'],'parse-error')

    def test_prefix_never_borrows_suffix_for_count_or_record(self):
        raw=b'\x1e'+bytes(4)+b'\x03'+bytes(9)+bytes(4)+b'\x02'+bytes(5)
        for at in range(1,len(raw)):
            before=gate.decode_buff_pre_id_modifier_prefix(raw,at)
            changed=gate.decode_buff_pre_id_modifier_prefix(raw[:at]+b'\xff'*100,at)
            with self.subTest(at=at):self.assertEqual(before,changed)

    def test_prefix_gap_and_overlap_guard(self):
        prefix={'status':'parsed-through-attribute-modifier','endOffset':'0x1'}
        with mock.patch.object(gate,'decode_buff_pre_id_modifier_prefix',return_value=prefix):
            row=self.frame(_normal())
            self.assertEqual(row['candidates'][0]['prefixProbe']['remainingGapRange'],[1,1])
        with mock.patch.object(gate,'decode_buff_pre_id_modifier_prefix',return_value={**prefix,'endOffset':'0x2'}):
            with self.assertRaises(gate.vfs.CensusGateError):self.frame(_normal())


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

    def test_tag10c_corpus_report_closes_frame_and_keeps_candidate_tail_opaque(self):
        prefix=b'\x1e'+struct.pack('<i',0)
        action=(b'\xfa\x0c\x01\x06'+b'\x01'+struct.pack('<III',1,2,3)+
                struct.pack('<i',3)+b'xyz'+b'\x00\x00\xf0\x41')
        root_before_action=(b'\xff'+struct.pack('<i',0)+b'\xff'+struct.pack('<i',0)+
            struct.pack('<i',1)+b'\x02'+struct.pack('<i',1)+b'\x03'+struct.pack('<i',1))
        action_start=len(prefix)+len(root_before_action)
        anchor=prefix+root_before_action+action+b'\x00\x00'+bytes(4)
        hard_limit=len(anchor)
        marker=struct.pack('<I',7)+b'fixture'
        self.data=anchor+marker+b'opaque-tail'
        self.path.write_bytes(self.data)
        self.ledger=_ledger_row(self.path,self.data)
        with mock.patch.object(gate,'decode_buff_post_id_prefix_at',return_value={
                'status':'parsed-through-exact-tail','endOffset':hex(len(self.data))}), \
             mock.patch.object(gate,'buff_post_id_result_is_exact_tail',return_value=True):
            report=self.build()

        self.assertEqual(report['inputSetSha256'],'A'*64)
        self.assertEqual(report['status'],'complete')
        self.assertFalse(report['wholeSchemaExact'])
        row=report['files'][0]
        candidate=row['candidates'][0]
        context=candidate['boundaryContext']
        self.assertEqual(context['inputSetSha256'],'A'*64)
        self.assertEqual(context['logicalFileIdentity'],self.ledger['virtualPath'])
        self.assertEqual(context['logicalSha256'],hashlib.sha256(self.data).hexdigest().upper())
        self.assertEqual(context['hardLimit'],hard_limit)
        profile=candidate['currentRootContinuation']
        self.assertEqual((profile['parserCursor'],profile['hardLimit']),(hard_limit,hard_limit))
        self.assertEqual(profile['boundaryClass'],'structural-prefix')
        closed=[record for record in profile['completedRecords']
                if record.get('kind')=='union' and record.get('tag')==268]
        self.assertEqual(len(closed),1)
        self.assertEqual((closed[0]['start'],closed[0]['end']),
                         (action_start,action_start+len(action)))
        self.assertEqual(closed[0]['boundaryClass'],'exact-closed')
        self.assertEqual(closed[0]['hardLimit'],hard_limit)
        self.assertEqual(closed[0]['boundaryContext'],{
            **context,'recordRange':[action_start,action_start+len(action)]})
        self.assertEqual(profile['opaqueByteRanges'],[
            {'start':hard_limit,'end':len(self.data),'kind':'opaque-after-hard-limit'}])
        summary=report['summary']['byteBoundaryEvidence']
        self.assertEqual(summary['exactClosedActionRecords'],1)
        self.assertGreater(summary['opaqueBytesByCandidate'],0)
        self.assertEqual(summary['structuralPrefixCandidates'],1)

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
        event=summary['currentEventPrefix']
        self.assertEqual(event['total'],sum(event[k] for k in ('success','failed','unsupported','ambiguous')))
        # This suffix-only fixture has no valid event prefix. Its failure is
        # published and closes the gate despite the legacy suffix succeeding.
        self.assertEqual(event['failed'],1)
        self.assertEqual(report['status'],'failed')
        self.assertFalse(report['publicationEligible'])

    def test_chunk_overlay_tool_and_parser_drift_have_specific_diagnostics(self):
        for name in ('_chunk_fingerprints','_chunk_selection_snapshot','_stream_tool_snapshot','_parser_source_snapshots'):
            with self.subTest(name=name),self.assertRaises(gate.vfs.CensusGateError) as caught:self.build(drift=name)
            self.assertEqual(caught.exception.diagnostic['code'],'buff-corpus-input-drift')
            self.assertNotEqual(caught.exception.diagnostic['expected'],caught.exception.diagnostic['actual'])

    def test_root_continuation_failure_closes_publication_with_diagnostics(self):
        for segment,expected in ((b'\xff'+struct.pack('<i',0)+b'\xff'+struct.pack('<i',0)+struct.pack('<i',0),'complete'),
                                 (b'\xff'+struct.pack('<i',-2),'failed')):
            with self.subTest(expected=expected):
                self.data=b'\x1e'+bytes(4)+segment+_normal()[1:]
                self.path.write_bytes(self.data)
                self.ledger=_ledger_row(self.path,self.data)
                report=self.build()
                self.assertEqual(report['status'],expected)
                self.assertEqual(report['publicationEligible'],expected=='complete')
                self.assertEqual(report['summary']['currentEventPrefix']['success'],1)
                summary=report['summary']['currentRootContinuation']
                self.assertEqual(summary['success' if expected=='complete' else 'failed'],1)
                if expected=='failed':
                    self.assertEqual(summary['failureCategories']['failed'],{'count-bounds':1})
                    row=report['files'][0]
                    diagnostic=row['candidates'][0]['currentRootContinuation']['diagnostic']
                    self.assertEqual(diagnostic['source'],self.ledger['virtualPath'])
                    self.assertEqual((diagnostic['offset'],diagnostic['actual']),(6,-2))
                    self.assertEqual(row['logicalSha256'],hashlib.sha256(self.data).hexdigest().upper())

    def test_unknown_sixth_action_is_reported_without_aliasing_or_false_success(self):
        before=b'\x1e'+bytes(4)+b'\xff'+bytes(4)+b'\xff'+bytes(4)
        before+=struct.pack('<i',1)+b'\x02'+struct.pack('<i',1)+b'\x03'+struct.pack('<i',1)
        self.data=before+b'\x59'+bytes(6)+_normal()[1:]
        self.path.write_bytes(self.data)
        self.ledger=_ledger_row(self.path,self.data)
        report=self.build()
        self.assertTrue(report['publicationEligible'])
        self.assertEqual(report['status'],'complete')
        summary=report['summary']['currentRootContinuation']
        self.assertEqual([summary[k] for k in ('success','failed','unsupported','ambiguous')],[0,0,1,0])
        self.assertEqual(summary['failureCategories']['unsupported'],{'union-tag':1})
        profile=report['files'][0]['candidates'][0]['currentRootContinuation']
        self.assertEqual(profile['consumedEnd'],len(before))
        self.assertEqual(profile['diagnostic']['actual'],89)
        self.assertFalse(profile['wholeSchemaExact'])

    def test_output_cannot_overwrite_input_or_alias_other_output(self):
        root=Path(self.temp.name)
        for outputs in ((self.path,), (root/'primary'/'report.json',), (root/'out.json',root/'out.json')):
            with self.subTest(outputs=outputs),self.assertRaises(gate.vfs.CensusGateError):self.build(outputs=outputs)


if __name__=='__main__':unittest.main()


