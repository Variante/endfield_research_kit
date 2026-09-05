import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from scripts.game_data.memorypack.skill_corpus import CensusGateError, verify_current_report_inputs


class CurrentReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.assets = self.root / 'assets'
        (self.assets / 'VFS').mkdir(parents=True)
        self.blc = self.assets / 'VFS/test.blc'
        self.blc.write_bytes(b'catalog')
        self.file = self.root / 'tool.dll'
        self.file.write_bytes(b'original')
        self.outer = self.root / 'outer.json'
        self.fallback = self.root / 'fallback'
        self.chunk = self.assets / ('VFS/12345678/'+'0'*32+'.chk')
        self.chunk.parent.mkdir(parents=True)
        self.chunk.write_bytes(b'chunk')
        self.fallback_chunk = self.fallback / ('VFS/12345678/'+'0'*32+'.chk')
        self.outer.write_text(json.dumps({'primaryAssets': str(self.assets), 'fallbackAssets': str(self.fallback),
                                         'inputSetSha256': 'A'*64}))
        pin = self.pin(self.file)
        self.report = {'format': 'animestudio-skilldata-current-vfs-corpus', 'schemaVersion': 1,
                       'status': 'complete', 'publicationEligible': True, 'inputSetSha256': 'A'*64,
                       'provenance': {'outer': self.pin(self.outer), 'ledger': pin, 'corpusGate': pin,
                                      'blcPaths': [os.path.normcase(str(self.blc.resolve()))]}}
        self.report['provenance']['selectedChunkResolution'] = [{
            'hashDirectory':'12345678', 'chunkFile':'0'*32+'.CHK',
            'primaryPath':self.chunk.as_posix(), 'primaryExists':True,
            'fallbackPath':self.fallback_chunk.as_posix(), 'fallbackExists':False,
            'selectedRole':'primary', 'selectedPath':self.chunk.as_posix()}]
        for role in ('sourceFingerprints', 'buildFingerprints', 'streamToolFingerprints',
                     'selectedChunkFingerprints', 'parser'):
            self.report['provenance'][role] = [pin]

    def pin(self, path):
        return {'path': str(path), 'length': path.stat().st_size,
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest().upper()}

    def test_normal(self):
        self.assertEqual(len(verify_current_report_inputs(self.report)), 8)

    def test_same_length_tool_drift(self):
        self.file.write_bytes(b'modified')
        with self.assertRaises(CensusGateError) as caught:
            verify_current_report_inputs(self.report)
        self.assertEqual(caught.exception.diagnostic['code'], 'fingerprint-sha256-mismatch')
        self.assertEqual(caught.exception.diagnostic['source'], str(self.file.resolve()))

    def test_every_live_role_checked(self):
        for role in ('sourceFingerprints', 'buildFingerprints', 'streamToolFingerprints',
                     'selectedChunkFingerprints', 'parser'):
            with self.subTest(role=role):
                good = self.report['provenance'][role]
                self.report['provenance'][role] = [{**good[0], 'sha256': '0'*64}]
                with self.assertRaises(CensusGateError):
                    verify_current_report_inputs(self.report)
                self.report['provenance'][role] = good

    def test_new_catalog_path(self):
        (self.assets / 'VFS/new.blc').write_bytes(b'new')
        with self.assertRaises(CensusGateError) as caught:
            verify_current_report_inputs(self.report)
        self.assertEqual(caught.exception.diagnostic['code'], 'blc-path-set-mismatch')

    def test_malformed_and_empty_pin_lists(self):
        for bad in (None, [], 'bad', [None]):
            with self.subTest(bad=bad):
                self.report['provenance']['parser'] = bad
                with self.assertRaises(CensusGateError):
                    verify_current_report_inputs(self.report)

    def test_partial_rejected(self):
        self.report['publicationEligible'] = False
        with self.assertRaises(CensusGateError):
            verify_current_report_inputs(self.report)

    def test_input_set_mismatch(self):
        self.report['inputSetSha256'] = 'B'*64
        with self.assertRaises(CensusGateError):
            verify_current_report_inputs(self.report)

    def test_new_primary_cannot_preserve_old_fallback_selection(self):
        self.chunk.unlink()
        self.fallback_chunk.parent.mkdir(parents=True)
        self.fallback_chunk.write_bytes(b'chunk')
        row = self.report['provenance']['selectedChunkResolution'][0]
        row.update(primaryExists=False, fallbackExists=True, selectedRole='fallback', selectedPath=self.fallback_chunk.as_posix())
        verify_current_report_inputs(self.report)
        self.chunk.write_bytes(b'new primary')
        with self.assertRaises(CensusGateError) as caught:
            verify_current_report_inputs(self.report)
        self.assertEqual(caught.exception.diagnostic['code'], 'chunk-overlay-selection-mismatch')


if __name__ == '__main__':
    unittest.main()
