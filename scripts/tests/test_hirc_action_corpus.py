from __future__ import annotations

import copy
import gzip
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.audio_semantics.hirc_action_corpus import (
    _type02_markdown,
    aggregate_current_hirc_actions,
    load_current_outer,
)


def valid_action_fixture():
    outer = {
        "primaryAssets": "D:/Persistent",
        "fallbackAssets": "D:/StreamingAssets",
    }
    expected_files = [
        {
            "block": "Audio",
            "path": "Data/Audio/banks.pck",
            "declaredBytes": 100,
            "fileDataMd5": "A" * 32,
            "chunk": "bank.chk",
            "source": "D:/Persistent/VFS/AA/bank.chk",
        }
    ]
    excluded_files = [
        {
            "block": "AudioJapanese",
            "path": f"Data/Audio/voice_{index}.pck",
            "status": "excluded_missing_voice",
            "chunkFile": f"voice_{index}.chk",
        }
        for index in range(2)
    ]
    frame = {
        "count": 2,
        "exact": 2,
        "unsupported": 0,
        "failed": 0,
        "ambiguous": 0,
        "bodyBytes": 19,
        "exactCursorBytes": 19,
        "operationCounts": {"0x0400": 1, "0x1200": 1},
        "failureCategories": {},
        "nonExactExamples": [],
    }
    type02_prefix = {
        "count": 2,
        "prefixBytes": 36,
        "opaqueTailBytes": 32,
        "minOpaqueTailBytes": 16,
        "maxOpaqueTailBytes": 16,
        "pluginTypeCounts": {"0x1": 1, "0x2": 1},
    }
    type02_stats = {"count": 2, "declaredLengthBytes": 76}
    audio_audit = {
        "streamingAssets": "D:/Persistent",
        "fallbackAssets": "D:/StreamingAssets",
        "summary": {
            "packages": 1,
            "verified": 1,
            "failures": 0,
            "missingBlocks": 0,
            "excluded": 1,
        },
        "rows": [
            {
                "block": "Audio",
                "path": "Data/Audio/banks.pck",
                "declaredBytes": 100,
                "verifiedFileDataMd5": "A" * 32,
                "chunk": "bank.chk",
                "source": r"D:\Persistent\VFS\AA\bank.chk",
                "status": "verified",
                "package": {
                    "hircObjectTypeCounts": {"0x02": 2, "0x03": 2},
                    "hircObjectTypeStats": {"0x02": copy.deepcopy(type02_stats)},
                    "hircType02Prefix": copy.deepcopy(type02_prefix),
                    "hircType03ActionFrame": copy.deepcopy(frame),
                    "bnkStructures": [
                        {
                            "version": 150,
                            "hircObjectTypeStats": {
                                "0x02": copy.deepcopy(type02_stats),
                                "0x03": {"count": 2},
                            },
                            "hircType02Prefix": copy.deepcopy(type02_prefix),
                            "hircType03ActionFrame": copy.deepcopy(frame),
                        }
                    ],
                },
            },
            {
                "block": "AudioJapanese",
                "status": "excluded_missing_voice",
                "source": "missing_both",
                "declaredChunks": 2,
                "declaredFiles": 2,
            },
        ],
    }
    return outer, expected_files, excluded_files, audio_audit


class HircActionCorpusTests(unittest.TestCase):
    def test_type02_markdown_reports_gate_and_evidence_boundary(self) -> None:
        report = {
            "status": "complete",
            "inputSetSha256": "A" * 64,
            "outer": {
                "ledgerSha256": "B" * 64,
                "animeStudioCliFingerprint": {
                    "matchesOuterAudit": False,
                    "outerAuditSha256": "C" * 64,
                    "currentSha256": "D" * 64,
                },
            },
            "audioAudit": {
                "toolSha256": "D" * 64,
                "intermediatePath": "tmp/audio-audit.json",
                "sha256": "E" * 64,
            },
            "corpusGate": {"sha256": "F" * 64},
            "corpus": {
                "packageCount": 1,
                "verifiedPackageCount": 1,
                "excludedBlockCount": 0,
                "type02SourcePrefixes": {
                    "wholeBodyCursor": "not-claimed-opaque-tail-remains",
                    "count": 1,
                    "packagesWithObjects": 1,
                    "banksWithObjects": 1,
                    "prefixBytes": 14,
                    "opaqueTailBytes": 8,
                    "bodyBytes": 22,
                    "minOpaqueTailBytes": 8,
                    "maxOpaqueTailBytes": 8,
                    "pluginTypeCounts": {"0x1": 1},
                    "objectCountsByBlock": {"Audio": 1},
                },
            },
        }

        markdown = _type02_markdown(report)

        self.assertIn("not-claimed-opaque-tail-remains", markdown)
        self.assertIn("opaque tail bytes: 8", markdown)
        self.assertIn("Corpus gate SHA-256: `" + "F" * 64, markdown)
        self.assertIn("Low-nibble type", markdown)
        self.assertIn("Remaining body bytes stay opaque", markdown)

    def test_outer_gate_binds_expected_set_ledger_and_physical_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            primary = root / "Persistent"
            fallback = root / "StreamingAssets"
            primary.mkdir()
            fallback.mkdir()
            metadata = root / "fixture.blc"
            metadata.write_bytes(b"metadata-v1")
            ledger = root / "ledger.jsonl.gz"
            with gzip.open(ledger, "wt", encoding="utf-8") as handle:
                handle.write("{}\n")
            input_set = "A" * 64
            outer = {
                "format": "animestudio-vfs-boundary-audit",
                "schemaVersion": 1,
                "inputSetSha256": input_set,
                "primaryAssets": str(primary),
                "fallbackAssets": str(fallback),
                "summary": {
                    "fullAuditPassed": True,
                    "allAvailableBoundaryVerified": True,
                    "failureCount": 0,
                },
                "publication": {
                    "ledgerSha256": hashlib.sha256(ledger.read_bytes()).hexdigest().upper(),
                },
                "sourceFingerprints": [
                    {
                        "path": str(metadata),
                        "sha256": hashlib.sha256(metadata.read_bytes()).hexdigest().upper(),
                    }
                ],
            }
            outer_path = root / "outer.json"
            outer_path.write_text(json.dumps(outer), encoding="utf-8")

            loaded, evidence = load_current_outer(outer_path, ledger, input_set)
            self.assertEqual(loaded["inputSetSha256"], input_set)
            self.assertEqual(evidence["sourceFingerprintsMatched"], 1)

            with self.assertRaisesRegex(ValueError, "input-set mismatch"):
                load_current_outer(outer_path, ledger, "B" * 64)

            metadata.write_bytes(b"metadata-v2")
            with self.assertRaisesRegex(ValueError, "source fingerprints changed"):
                load_current_outer(outer_path, ledger, input_set)

    def test_action_corpus_aggregate_closes_every_current_body(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        actions = result["type03Objects"]
        self.assertEqual(actions["count"], 2)
        self.assertEqual(actions["exact"], 2)
        self.assertEqual(actions["frameClosure"], "exact")
        self.assertEqual(actions["bodyBytes"], actions["exactCursorBytes"])
        self.assertEqual(result["excludedBlockCount"], 1)
        self.assertTrue(result["identityReconciliation"]["verifiedPackagesMatchedToOuterLedger"])
        self.assertTrue(result["identityReconciliation"]["excludedBlocksMatchedToOuterLedger"])
        self.assertTrue(result["identityReconciliation"]["perBankFramesMatchedToPackageFrames"])
        prefixes = result["type02SourcePrefixes"]
        self.assertEqual(prefixes["count"], 2)
        self.assertEqual(prefixes["prefixBytes"], 36)
        self.assertEqual(prefixes["opaqueTailBytes"], 32)
        self.assertEqual(prefixes["bodyBytes"], 68)
        self.assertEqual(prefixes["pluginTypeCounts"], {"0x1": 1, "0x2": 1})
        self.assertEqual(prefixes["wholeBodyCursor"], "not-claimed-opaque-tail-remains")

    def test_type02_prefix_gate_rejects_byte_count_and_bank_mismatches(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        bad_tail = copy.deepcopy(audio_audit)
        bad_tail["rows"][0]["package"]["hircType02Prefix"]["opaqueTailBytes"] = 31
        with self.assertRaisesRegex(ValueError, "prefix-plus-tail body accounting mismatch"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, bad_tail)

        bad_plugins = copy.deepcopy(audio_audit)
        bad_plugins["rows"][0]["package"]["hircType02Prefix"]["pluginTypeCounts"]["0x2"] = 0
        with self.assertRaisesRegex(ValueError, "plugin-type count mismatch"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, bad_plugins)

        bad_bank = copy.deepcopy(audio_audit)
        bank_prefix = bad_bank["rows"][0]["package"]["bnkStructures"][0]["hircType02Prefix"]
        bank_prefix.update({
            "prefixBytes": 35,
            "opaqueTailBytes": 33,
            "maxOpaqueTailBytes": 17,
        })
        with self.assertRaisesRegex(ValueError, "per-bank/package type 0x02"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, bad_bank)

    def test_package_identity_includes_checksum_chunk_and_physical_source(self) -> None:
        mutations = (
            ("verifiedFileDataMd5", "B" * 32),
            ("chunk", "other.chk"),
            ("source", r"D:\Persistent\VFS\BB\bank.chk"),
        )
        for field, value in mutations:
            with self.subTest(field=field):
                outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
                audio_audit["rows"][0][field] = value
                with self.assertRaisesRegex(ValueError, "verified package identities"):
                    aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)

    def test_excluded_blocks_match_exact_status_and_multiplicity(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        wrong_status = copy.deepcopy(audio_audit)
        wrong_status["rows"][1]["status"] = "excluded_missing_audio"
        with self.assertRaisesRegex(ValueError, "conditional-exclusion identity mismatch"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, wrong_status)

        duplicate_row = copy.deepcopy(audio_audit)
        duplicate_row["rows"].append(copy.deepcopy(duplicate_row["rows"][1]))
        with self.assertRaisesRegex(ValueError, "conditional-exclusion identity mismatch"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, duplicate_row)

        wrong_multiplicity = copy.deepcopy(audio_audit)
        wrong_multiplicity["rows"][1]["declaredFiles"] = 1
        with self.assertRaisesRegex(ValueError, "conditional-exclusion multiplicity mismatch"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, wrong_multiplicity)

    def test_per_bank_outcomes_and_totals_reconcile_with_package(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        per_bank_partition = copy.deepcopy(audio_audit)
        bank_frame = per_bank_partition["rows"][0]["package"]["bnkStructures"][0]["hircType03ActionFrame"]
        bank_frame["failed"] = 1
        with self.assertRaisesRegex(ValueError, "outcome partition mismatch"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, per_bank_partition)

        package_total_mismatch = copy.deepcopy(audio_audit)
        bank_frame = package_total_mismatch["rows"][0]["package"]["bnkStructures"][0]["hircType03ActionFrame"]
        bank_frame["exact"] = 1
        bank_frame["failed"] = 1
        with self.assertRaisesRegex(ValueError, "per-bank/package type 0x03 total mismatch"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, package_total_mismatch)

    def test_action_corpus_aggregate_rejects_missing_or_unclassified_objects(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        frame = audio_audit["rows"][0]["package"]["hircType03ActionFrame"]
        frame["count"] = 1
        frame["exact"] = 1
        frame["bodyBytes"] = 9
        frame["exactCursorBytes"] = 9
        with self.assertRaisesRegex(ValueError, "type 0x03 audit count mismatch"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)


if __name__ == "__main__":
    unittest.main()
