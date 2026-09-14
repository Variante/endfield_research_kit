from __future__ import annotations

import copy
import gzip
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.audio_semantics.hirc_action_corpus import (
    _capture_cli_output_closure,
    _load_json_with_sha256,
    _body_lane_markdown,
    _type02_markdown,
    _type04_markdown,
    aggregate_current_hirc_actions,
    load_current_outer,
    body_lane_corpus_is_closed,
    reference_graph_is_closed,
    _reference_graph_markdown,
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
        "opaqueTailBytes": 64,
        "minOpaqueTailBytes": 32,
        "maxOpaqueTailBytes": 32,
        "pluginTypeCounts": {"0x1": 1, "0x2": 1},
    }
    type02_stats = {"count": 2, "declaredLengthBytes": 108}
    type07_stats = {"count": 2, "declaredLengthBytes": 248}
    type05_stats = {"count": 2, "declaredLengthBytes": 148}
    type05_body = {
        "count": 2,
        "exact": 2,
        "unsupported": 0,
        "failed": 0,
        "ambiguous": 0,
        "bodyBytes": 140,
        "exactCursorBytes": 140,
        "nonExactBodyBytes": 0,
        "minExactBodyBytes": 61,
        "maxExactBodyBytes": 79,
        "groupCounts": {
            "referenceEntries": 3,
            "recordEntries": 2,
            "referenceRecordCountMismatch": 1,
            "groupIEntries": 0,
            "groupIKeyBytes": 0,
        },
        "selectorCounts": {
            "groupAFlag_00": 2,
            "groupBFlag_00": 2,
            "groupESelector_00": 2,
            "groupFSelector_00": 2,
        },
        "failureCategories": {},
        "unsupportedCategories": {},
        "nonExactExamples": [],
    }
    type07_body = {
        "count": 2,
        "exact": 2,
        "unsupported": 0,
        "failed": 0,
        "ambiguous": 0,
        "bodyBytes": 240,
        "exactCursorBytes": 240,
        "nonExactBodyBytes": 0,
        "minExactBodyBytes": 110,
        "maxExactBodyBytes": 130,
        "groupCounts": {
            "childEntries": 4,
            "groupIEntries": 2,
            "groupIKeyBytes": 3,
            "groupHStates": 2,
            "groupHStateElements": 3,
        },
        "selectorCounts": {
            "groupAFlag_00": 2,
            "groupBFlag_00": 2,
            "groupESelector_00": 2,
            "groupFSelector_00": 2,
            "groupIKeyWidth_1": 1,
            "groupIKeyWidth_2": 1,
            "groupHStateWidth_12": 1,
            "groupHStateWidth_18": 1,
        },
        "failureCategories": {},
        "unsupportedCategories": {},
        "nonExactExamples": [],
    }
    type02_body = {
        "count": 2,
        "exact": 2,
        "unsupported": 0,
        "failed": 0,
        "ambiguous": 0,
        "bodyBytes": 100,
        "exactCursorBytes": 100,
        "nonExactBodyBytes": 0,
        "minExactBodyBytes": 45,
        "maxExactBodyBytes": 55,
        "groupCounts": {
            "groupAEntries": 0,
            "groupCEntries": 3,
            "groupIEntries": 1,
            "groupIKeyBytes": 1,
            "groupIPoints": 4,
        },
        "selectorCounts": {
            "groupAFlag_00": 2,
            "groupBFlag_00": 2,
            "groupESelector_00": 2,
            "groupFSelector_00": 2,
            "groupIKeyWidth_1": 1,
        },
        "failureCategories": {},
        "unsupportedCategories": {},
        "nonExactExamples": [],
    }
    type04_vector = {
        "count": 2,
        "exact": 1,
        "unsupported": 1,
        "failed": 0,
        "ambiguous": 0,
        "bodyBytes": 11,
        "candidatePrefixBytes": 10,
        "unsupportedCandidatePrefixBytes": 5,
        "exactCursorBytes": 5,
        "opaqueTailBytes": 1,
        "failedBodyBytes": 0,
        "candidateEntryCount": 2,
        "exactEntryCount": 1,
        "failureCategories": {},
        "unsupportedCategories": {"opaque_tail_after_candidate_vector": 1},
        "nonExactExamples": [
            {
                "bankId": 123,
                "ordinal": 2,
                "objectId": 456,
                "status": "unsupported",
                "category": "opaque_tail_after_candidate_vector",
                "expectedBytes": 5,
                "actualBytes": 6,
                "opaqueTailBytes": 1,
            }
        ],
    }
    type04_stats = {"count": 2, "declaredLengthBytes": 19}
    reference_census = {
        "references": 8,
        "resolvedSameBank": 8,
        "unresolvedInBank": 0,
        "selfReferences": 0,
        "targetsWithMultipleReferrers": 0,
        "duplicateObjectIds": 0,
        "referencesToDuplicateIds": 0,
        "referenceCycleOrFeedingNodes": 0,
        "distinctDuplicateObjectIds": 0,
        "maximumReferenceDepth": 3,
        "objectCountsByType": {"type02": 20, "type03": 10, "type04": 5, "type05": 8, "type07": 8},
        "edgeCounts": {"type07_to_type02": 4, "type04_to_type03": 1, "type05_to_type02": 3},
    }
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
                    "hircObjectTypeCounts": {"0x02": 2, "0x03": 2, "0x04": 2, "0x05": 2, "0x07": 2},
                    "hircObjectTypeStats": {
                        "0x02": copy.deepcopy(type02_stats),
                        "0x04": copy.deepcopy(type04_stats),
                        "0x07": copy.deepcopy(type07_stats),
                        "0x05": copy.deepcopy(type05_stats),
                    },
                    "hircType02Prefix": copy.deepcopy(type02_prefix),
                    "hircType02BodyFrame": copy.deepcopy(type02_body),
                    "hircType07BodyFrame": copy.deepcopy(type07_body),
                    "hircType05BodyFrame": copy.deepcopy(type05_body),
                    "hircReferenceCensus": copy.deepcopy(reference_census),
                    "hircType03ActionFrame": copy.deepcopy(frame),
                    "hircType04U32VectorFrame": copy.deepcopy(type04_vector),
                    "bnkStructures": [
                        {
                            "version": 150,
                            "hircObjectTypeStats": {
                                "0x02": copy.deepcopy(type02_stats),
                                "0x03": {"count": 2},
                                "0x04": copy.deepcopy(type04_stats),
                                "0x07": copy.deepcopy(type07_stats),
                                "0x05": copy.deepcopy(type05_stats),
                            },
                            "hircType02Prefix": copy.deepcopy(type02_prefix),
                            "hircType02BodyFrame": copy.deepcopy(type02_body),
                            "hircType07BodyFrame": copy.deepcopy(type07_body),
                            "hircType05BodyFrame": copy.deepcopy(type05_body),
                            "hircReferenceCensus": copy.deepcopy(reference_census),
                            "hircType03ActionFrame": copy.deepcopy(frame),
                            "hircType04U32VectorFrame": copy.deepcopy(type04_vector),
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
                "toolClosure": {"fileCount": 79, "manifestSha256": "G" * 64},
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

    def test_type04_markdown_keeps_vector_values_anonymous(self) -> None:
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
                "toolClosure": {"fileCount": 79, "manifestSha256": "G" * 64},
                "intermediatePath": "tmp/audio-audit.json",
                "sha256": "E" * 64,
            },
            "corpusGate": {"sha256": "F" * 64},
            "corpus": {
                "packageCount": 1,
                "verifiedPackageCount": 1,
                "excludedBlockCount": 0,
                "type04U32VectorCandidates": {
                    "frameClosure": "all-candidate-vectors-exact",
                    "count": 1,
                    "exact": 1,
                    "unsupported": 0,
                    "failed": 0,
                    "ambiguous": 0,
                    "bodyBytes": 5,
                    "candidatePrefixBytes": 5,
                    "exactCursorBytes": 5,
                    "opaqueTailBytes": 0,
                    "failedBodyBytes": 0,
                    "candidateEntryCount": 1,
                    "packagesWithObjects": 1,
                    "banksWithObjects": 1,
                    "failureCategories": {},
                    "unsupportedCategories": {},
                    "objectCountsByBlock": {"Audio": 1},
                },
            },
        }

        markdown = _type04_markdown(report)

        self.assertIn("all-candidate-vectors-exact", markdown)
        self.assertIn("Entry values remain unnamed", markdown)
        self.assertIn("does not establish serialized field ownership", markdown)
        self.assertIn("Corpus gate SHA-256: `" + "F" * 64, markdown)
        self.assertIn("79 files", markdown)
        self.assertIn("G" * 64, markdown)

    def test_cli_output_closure_hash_covers_apphost_and_managed_sidecars(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "cli"
            nested = output / "runtimes" / "win-x64"
            nested.mkdir(parents=True)
            cli = output / "AnimeStudio.CLI.exe"
            cli.write_bytes(b"apphost")
            (output / "AnimeStudio.CLI.dll").write_bytes(b"cli assembly")
            assembly = output / "AnimeStudio.dll"
            assembly.write_bytes(b"parser assembly v1")
            (nested / "native.dll").write_bytes(b"native support")

            first = _capture_cli_output_closure(cli)
            repeated = _capture_cli_output_closure(cli)
            self.assertEqual(first["fileCount"], 4)
            self.assertEqual(first["manifestSha256"], repeated["manifestSha256"])
            self.assertIn("AnimeStudio.dll", {row["path"] for row in first["files"]})

            assembly.write_bytes(b"parser assembly v2")
            changed = _capture_cli_output_closure(cli)
            self.assertNotEqual(first["manifestSha256"], changed["manifestSha256"])

    def test_intermediate_report_hash_uses_the_bytes_that_were_parsed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.json"
            original = b'{"revision":1}\n'
            path.write_bytes(original)

            parsed, digest = _load_json_with_sha256(path)

            path.write_bytes(b'{"revision":2}\n')
            self.assertEqual(parsed, {"revision": 1})
            self.assertEqual(digest, hashlib.sha256(original).hexdigest().upper())

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
        self.assertEqual(prefixes["opaqueTailBytes"], 64)
        self.assertEqual(prefixes["bodyBytes"], 100)
        self.assertEqual(prefixes["pluginTypeCounts"], {"0x1": 1, "0x2": 1})
        self.assertEqual(prefixes["wholeBodyCursor"], "not-claimed-opaque-tail-remains")
        vectors = result["type04U32VectorCandidates"]
        self.assertEqual(vectors["count"], 2)
        self.assertEqual(vectors["exact"], 1)
        self.assertEqual(vectors["unsupported"], 1)
        self.assertEqual(vectors["bodyBytes"], 11)
        self.assertEqual(vectors["candidatePrefixBytes"], 10)
        self.assertEqual(vectors["opaqueTailBytes"], 1)
        self.assertEqual(vectors["candidateEntryCount"], 2)
        self.assertEqual(vectors["frameClosure"], "incomplete")
        self.assertEqual(vectors["unsupportedCategories"], {"opaque_tail_after_candidate_vector": 1})
        self.assertTrue(result["identityReconciliation"]["perBankType04FramesMatchedToPackageFrames"])

    def test_type02_body_frames_close_every_current_body_anonymously(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        bodies = result["type02BodyFrames"]
        self.assertEqual(bodies["count"], 2)
        self.assertEqual(bodies["exact"], 2)
        self.assertEqual(bodies["frameClosure"], "all-bodies-exact")
        self.assertEqual(bodies["bodyBytes"], bodies["exactCursorBytes"])
        self.assertEqual(bodies["nonExactBodyBytes"], 0)
        self.assertEqual(bodies["anonymousGroupCounts"]["groupCEntries"], 3)
        self.assertEqual(bodies["anonymousSelectorCounts"]["groupBFlag_00"], 2)
        # Both lanes publish the shared framer's residuals, so neither can quietly
        # carry a shorter list than the other.
        self.assertEqual(len(bodies["unresolvedWidths"]), 9)
        joined = " ".join(bodies["unresolvedWidths"])
        self.assertIn("group A slot split", joined)
        self.assertIn("group E branch 2", joined)
        self.assertIn("inherited from the type 0x03 Action reader", joined)
        self.assertIn("aborts the whole package", bodies["upstreamAbortsNotCountedHere"])
        self.assertEqual(bodies["minExactBodyBytes"], 45)
        self.assertTrue(
            result["identityReconciliation"]["verifiedPackagesMatchedToOuterLedger"]
        )

    def test_type02_body_gate_rejects_partition_and_byte_mismatches(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()

        bad_partition = copy.deepcopy(audio_audit)
        bad_partition["rows"][0]["package"]["hircType02BodyFrame"]["exact"] = 1
        with self.assertRaisesRegex(ValueError, "type 0x02 body outcome partition mismatch"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, bad_partition)

        bad_bytes = copy.deepcopy(audio_audit)
        bad_bytes["rows"][0]["package"]["hircType02BodyFrame"]["nonExactBodyBytes"] = 4
        with self.assertRaisesRegex(ValueError, "exact/non-exact body accounting mismatch"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, bad_bytes)

        bad_declared = copy.deepcopy(audio_audit)
        bad_declared["rows"][0]["package"]["hircType02BodyFrame"]["bodyBytes"] = 96
        bad_declared["rows"][0]["package"]["hircType02BodyFrame"]["exactCursorBytes"] = 96
        with self.assertRaisesRegex(ValueError, "body bytes differ from declared HIRC object bodies"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, bad_declared)

        # A single undersized body must be rejected even when the mean is healthy.
        short_bodies = copy.deepcopy(audio_audit)
        for scope in (
            short_bodies["rows"][0]["package"],
            short_bodies["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircType02BodyFrame"].update(
                {"minExactBodyBytes": 44, "maxExactBodyBytes": 56}
            )
        with self.assertRaisesRegex(ValueError, "falls below the minimum frame"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, short_bodies)

        unbounded_range = copy.deepcopy(audio_audit)
        for scope in (
            unbounded_range["rows"][0]["package"],
            unbounded_range["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircType02BodyFrame"]["maxExactBodyBytes"] = 49
        with self.assertRaisesRegex(ValueError, "exact-length range does not bound its total"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, unbounded_range)

    def test_type02_body_gate_requires_selector_and_bank_reconciliation(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()

        bad_selector = copy.deepcopy(audio_audit)
        bad_selector["rows"][0]["package"]["hircType02BodyFrame"]["selectorCounts"][
            "groupESelector_00"
        ] = 1
        with self.assertRaisesRegex(ValueError, "selector family groupESelector_"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, bad_selector)

        bad_bank = copy.deepcopy(audio_audit)
        bank_body = bad_bank["rows"][0]["package"]["bnkStructures"][0]["hircType02BodyFrame"]
        bank_body["groupCounts"]["groupCEntries"] = 2
        with self.assertRaisesRegex(ValueError, "type 0x02 group inventory mismatch"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, bad_bank)

        bad_range = copy.deepcopy(audio_audit)
        bad_range["rows"][0]["package"]["bnkStructures"][0]["hircType02BodyFrame"][
            "minExactBodyBytes"
        ] = 46
        with self.assertRaisesRegex(ValueError, "type 0x02 exact-length range mismatch"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, bad_range)

        missing_frame = copy.deepcopy(audio_audit)
        del missing_frame["rows"][0]["package"]["hircType02BodyFrame"]
        with self.assertRaisesRegex(ValueError, "missing type 0x02 body-frame result"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, missing_frame)

    def test_type02_body_gate_preserves_unsupported_and_failed_outcomes(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        held = copy.deepcopy(audio_audit)
        for scope in (
            held["rows"][0]["package"],
            held["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircType02BodyFrame"].update(
                {
                    "exact": 0,
                    "unsupported": 1,
                    "failed": 1,
                    "exactCursorBytes": 0,
                    "nonExactBodyBytes": 100,
                    "minExactBodyBytes": 0,
                    "maxExactBodyBytes": 0,
                    "groupCounts": {},
                    "selectorCounts": {},
                    "failureCategories": {"trailing_bytes": 1},
                    "unsupportedCategories": {"unsupported_groupB_nonempty": 1},
                }
            )
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, held)
        bodies = result["type02BodyFrames"]
        self.assertEqual(bodies["exact"], 0)
        self.assertEqual(bodies["frameClosure"], "incomplete")
        self.assertEqual(bodies["nonExactBodyBytes"], 100)
        self.assertEqual(bodies["failureCategories"], {"trailing_bytes": 1})
        self.assertEqual(
            bodies["unsupportedCategories"], {"unsupported_groupB_nonempty": 1}
        )

        miscounted = copy.deepcopy(held)
        miscounted["rows"][0]["package"]["hircType02BodyFrame"]["unsupportedCategories"] = {}
        with self.assertRaisesRegex(ValueError, "unsupportedCategories do not match outcome counts"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, miscounted)

    def test_type02_body_closure_is_enforced_not_just_reported(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        closed = aggregate_current_hirc_actions(
            outer, expected_files, excluded_files, audio_audit
        )["type02BodyFrames"]
        self.assertTrue(body_lane_corpus_is_closed(closed))

        # Every way of not closing must be refused, including a lane that reports
        # itself exact while leaving bytes unaccounted.
        for field, value in (
            ("frameClosure", "incomplete"),
            ("exact", 1),
            ("unsupported", 1),
            ("failed", 1),
            ("ambiguous", 1),
            ("nonExactBodyBytes", 1),
        ):
            regressed = dict(closed)
            regressed[field] = value
            self.assertFalse(
                body_lane_corpus_is_closed(regressed),
                f"{field}={value} must not count as a closed corpus",
            )

    def test_type02_body_markdown_keeps_groups_and_widths_anonymous(self) -> None:
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
                "toolClosure": {"fileCount": 79, "manifestSha256": "G" * 64},
                "intermediatePath": "tmp/audio-audit.json",
                "sha256": "E" * 64,
            },
            "corpusGate": {"sha256": "F" * 64},
            "corpus": {
                "packageCount": 1,
                "verifiedPackageCount": 1,
                "excludedBlockCount": 0,
                "type02BodyFrames": {
                    "frameClosure": "all-bodies-exact",
                    "count": 1,
                    "exact": 1,
                    "unsupported": 0,
                    "failed": 0,
                    "ambiguous": 0,
                    "bodyBytes": 45,
                    "exactCursorBytes": 45,
                    "nonExactBodyBytes": 0,
                    "packagesWithObjects": 1,
                    "banksWithObjects": 1,
                    "anonymousGroupCounts": {"groupCEntries": 2},
                    "anonymousSelectorCounts": {"groupAFlag_00": 1},
                    "failureCategories": {},
                    "unsupportedCategories": {},
                    "minExactBodyBytes": 45,
                    "maxExactBodyBytes": 45,
                    "minimumPossibleFrameBytes": 45,
                    "frameLayout": "The reader consumes the bounded source prefix and the node groups.",
                    "objectCountsByBlock": {"Audio": 1},
                    "unresolvedWidths": ["group B element width: no nonempty vector"],
                    "upstreamAbortsNotCountedHere": "a malformed source prefix aborts the package",
                },
            },
        }

        markdown = _body_lane_markdown(report, "type02BodyFrames", "0x02")

        self.assertIn("all-bodies-exact", markdown)
        self.assertIn("What this corpus does not resolve", markdown)
        self.assertIn("group B element width", markdown)
        self.assertIn("Failures this lane cannot count", markdown)
        self.assertIn("aborts the package", markdown)
        self.assertIn("internal consistency assert, not independent evidence", markdown)
        self.assertIn("Closure is enforced", markdown)
        self.assertIn("stay anonymous", markdown)
        self.assertIn("does not establish serialized field ownership", markdown)
        self.assertIn("Corpus gate SHA-256: `" + "F" * 64, markdown)

    def test_reference_graph_joins_every_reference_to_one_same_bank_object(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        graph = aggregate_current_hirc_actions(
            outer, expected_files, excluded_files, audio_audit
        )["referenceGraph"]
        self.assertEqual(graph["references"], 8)
        self.assertEqual(graph["resolvedSameBank"], 8)
        self.assertEqual(graph["framedVectorEntries"], 8)
        # One type 0x04 body is unsupported, so one framed entry never resolves.
        self.assertEqual(graph["entriesNotReachingCensus"], 1)
        self.assertFalse(reference_graph_is_closed(graph))
        self.assertEqual(graph["semanticStatus"], "structural-only")
        # The edges stay numeric on both sides.
        self.assertEqual(
            sorted(graph["edgeCounts"]),
            ["type04_to_type03", "type05_to_type02", "type07_to_type02"],
        )

    def test_reference_graph_rejects_every_way_of_not_naming_one_object(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()

        for field, value, pattern in (
            ("unresolvedInBank", 1, "reference outcome partition mismatch"),
            ("selfReferences", 99, "self references exceed total references"),
            ("referencesToDuplicateIds", 99, "duplicate-id references exceed total"),
            ("targetsWithMultipleReferrers", 99, "multi-referrer targets exceed total"),
        ):
            broken = copy.deepcopy(audio_audit)
            for scope in (
                broken["rows"][0]["package"],
                broken["rows"][0]["package"]["bnkStructures"][0],
            ):
                scope["hircReferenceCensus"][field] = value
            with self.assertRaisesRegex(ValueError, pattern):
                aggregate_current_hirc_actions(outer, expected_files, excluded_files, broken)

        unaccounted = copy.deepcopy(audio_audit)
        for scope in (
            unaccounted["rows"][0]["package"],
            unaccounted["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircReferenceCensus"]["edgeCounts"]["type04_to_type03"] = 2
        with self.assertRaisesRegex(ValueError, "edges do not account for every resolved"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, unaccounted)

        named = copy.deepcopy(audio_audit)
        for scope in (
            named["rows"][0]["package"],
            named["rows"][0]["package"]["bnkStructures"][0],
        ):
            edges = scope["hircReferenceCensus"]["edgeCounts"]
            del edges["type04_to_type03"]
            edges["event_to_action"] = 2
        with self.assertRaisesRegex(ValueError, "edge is not a numeric type pair"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, named)

        # Drift the bank totals while keeping each census internally consistent, so the
        # per-bank reconciliation is what fires rather than a local partition check.
        bank_drift = copy.deepcopy(audio_audit)
        bank_census = bank_drift["rows"][0]["package"]["bnkStructures"][0]["hircReferenceCensus"]
        bank_census["references"] = 7
        bank_census["resolvedSameBank"] = 7
        bank_census["edgeCounts"] = {"type07_to_type02": 3, "type04_to_type03": 1, "type05_to_type02": 3}
        with self.assertRaisesRegex(ValueError, "per-bank/package HIRC reference census mismatch"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, bank_drift)

    def test_reference_graph_closure_is_enforced_not_just_reported(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        closed = aggregate_current_hirc_actions(
            outer, expected_files, excluded_files, audio_audit
        )["referenceGraph"]
        closed = dict(closed, entriesNotReachingCensus=0)
        self.assertTrue(reference_graph_is_closed(closed))
        for field, value in (
            ("entriesNotReachingCensus", 1),
            ("references", 0),
            ("unresolvedInBank", 1),
            ("selfReferences", 1),
            ("targetsWithMultipleReferrers", 1),
            ("referencesToDuplicateIds", 1),
            ("resolvedSameBank", 7),
            ("referenceCycleOrFeedingNodes", 1),
        ):
            regressed = dict(closed)
            regressed[field] = value
            self.assertFalse(
                reference_graph_is_closed(regressed),
                f"{field}={value} must not count as a closed reference graph",
            )

    def test_reference_graph_markdown_refuses_to_name_the_relation(self) -> None:
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
                "toolClosure": {"fileCount": 79, "manifestSha256": "G" * 64},
                "intermediatePath": "tmp/audio-audit.json",
                "sha256": "E" * 64,
            },
            "corpusGate": {"sha256": "F" * 64},
            "corpus": {
                "packageCount": 1,
                "verifiedPackageCount": 1,
                "excludedBlockCount": 0,
                "referenceGraph": {
                    "closure": "every-reference-names-one-same-bank-object",
                    "references": 6,
                    "resolvedSameBank": 6,
                    "unresolvedInBank": 0,
                    "selfReferences": 0,
                    "targetsWithMultipleReferrers": 0,
                    "duplicateObjectIds": 0,
                    "referencesToDuplicateIds": 0,
                    "referenceCycleOrFeedingNodes": 0,
                    "distinctDuplicateObjectIds": 0,
                    "entriesNotReachingCensus": 0,
                    "maximumReferenceDepth": 3,
                    "referenceTargetsByType": {"type03": 2},
                    "objectCountsByType": {"type03": 10, "type04": 5},
                    "edgeCounts": {"type04_to_type03": 2},
                },
            },
        }

        markdown = _reference_graph_markdown(report)

        self.assertIn("Resolution is an identity fact and nothing more", markdown)
        self.assertIn("does not establish direction", markdown)
        self.assertIn("The type pairs are numeric on both sides", markdown)
        self.assertIn("a property of this corpus, not a rule", markdown)
        # No edge may be rendered with a domain name.
        for word in ("event", "action", "parent", "child", "container", "playlist"):
            self.assertNotIn(f"`{word}", markdown.lower())

    def test_histogram_labels_must_be_physically_possible_widths(self) -> None:
        # A sum-only check accepts impossible buckets: width 0, or {12,12} standing in
        # for {6,18}. The label itself has to be a key plus whole six-byte elements.
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()

        impossible = copy.deepcopy(audio_audit)
        for scope in (
            impossible["rows"][0]["package"],
            impossible["rows"][0]["package"]["bnkStructures"][0],
        ):
            selectors = scope["hircType07BodyFrame"]["selectorCounts"]
            del selectors["groupHStateWidth_12"]
            del selectors["groupHStateWidth_18"]
            selectors["groupHStateWidth_0"] = 2
            selectors["groupHStateWidth_30"] = 1
            scope["hircType07BodyFrame"]["groupCounts"]["groupHStates"] = 3
            scope["hircType07BodyFrame"]["groupCounts"]["groupHStateElements"] = 2
        with self.assertRaisesRegex(ValueError, "not a key plus whole elements"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, impossible)

        malformed = copy.deepcopy(audio_audit)
        for scope in (
            malformed["rows"][0]["package"],
            malformed["rows"][0]["package"]["bnkStructures"][0],
        ):
            selectors = scope["hircType07BodyFrame"]["selectorCounts"]
            # Swap, not add: the count check would otherwise fire first.
            del selectors["groupIKeyWidth_1"]
            selectors["groupIKeyWidth_x"] = 1
        with self.assertRaisesRegex(ValueError, "histogram key is not a plain width"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, malformed)

        out_of_range = copy.deepcopy(audio_audit)
        for scope in (
            out_of_range["rows"][0]["package"],
            out_of_range["rows"][0]["package"]["bnkStructures"][0],
        ):
            selectors = scope["hircType07BodyFrame"]["selectorCounts"]
            del selectors["groupIKeyWidth_2"]
            selectors["groupIKeyWidth_9"] = 1
        with self.assertRaisesRegex(ValueError, "key width is outside the reader's range"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, out_of_range)

        bucketed = copy.deepcopy(audio_audit)
        for scope in (
            bucketed["rows"][0]["package"],
            bucketed["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircType07BodyFrame"]["selectorCounts"]["groupHStateWidth_over_54"] = 1
        with self.assertRaisesRegex(ValueError, "histogram is bucketed"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, bucketed)

    def test_group_h_state_widths_must_reconcile_with_their_elements(self) -> None:
        # The state was read as a fixed twelve bytes until a two-element sample
        # disproved it, so the census must keep the width histogram honest rather
        # than let a degenerate corpus hide the variable part again.
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        bodies = result["type07BodyFrames"]
        self.assertEqual(bodies["anonymousGroupCounts"]["groupHStates"], 2)
        self.assertEqual(bodies["anonymousGroupCounts"]["groupHStateElements"], 3)
        self.assertEqual(bodies["anonymousSelectorCounts"]["groupHStateWidth_18"], 1)

        miscounted = copy.deepcopy(audio_audit)
        for scope in (
            miscounted["rows"][0]["package"],
            miscounted["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircType07BodyFrame"]["selectorCounts"]["groupHStateWidth_12"] = 2
        with self.assertRaisesRegex(ValueError, "state width histogram does not match its state count"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, miscounted)

        inconsistent = copy.deepcopy(audio_audit)
        for scope in (
            inconsistent["rows"][0]["package"],
            inconsistent["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircType07BodyFrame"]["groupCounts"]["groupHStateElements"] = 4
        with self.assertRaisesRegex(ValueError, "state width histogram does not sum to its element total"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, inconsistent)

    def test_type05_body_lane_frames_two_independent_vectors(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        bodies = result["type05BodyFrames"]
        self.assertEqual(bodies["count"], 2)
        self.assertEqual(bodies["exact"], 2)
        self.assertEqual(bodies["frameClosure"], "all-bodies-exact")
        self.assertEqual(bodies["minimumPossibleFrameBytes"], 61)
        # The two vectors are counted separately and the mismatch count is measured,
        # not asserted in prose.
        self.assertEqual(bodies["anonymousGroupCounts"]["referenceEntries"], 3)
        self.assertEqual(bodies["anonymousGroupCounts"]["recordEntries"], 2)
        self.assertEqual(bodies["anonymousGroupCounts"]["referenceRecordCountMismatch"], 1)
        self.assertTrue(body_lane_corpus_is_closed(bodies))
        self.assertIn("eight-byte anonymous records", bodies["frameLayout"])

    def test_every_lane_publishes_its_own_layout_and_non_claims(self) -> None:
        # The shared publisher must not flatten what each lane actually consumes, and
        # the type 0x02 lane must keep disclaiming source and cross-bank identity.
        from scripts.audio_semantics.hirc_action_corpus import _build_body_lanes

        lanes = _build_body_lanes()
        self.assertEqual(sorted(lanes), ["0x02", "0x05", "0x07"])
        layouts = {key: lane.layout for key, lane in lanes.items()}
        self.assertEqual(len(set(layouts.values())), 3)
        self.assertIn("source prefix", layouts["0x02"])
        self.assertIn("four-byte anonymous references.", layouts["0x07"])
        self.assertIn("twenty-four-byte opaque", layouts["0x05"])
        self.assertIn("source, effect, bus, or parent object identity", lanes["0x02"].non_claims)
        self.assertIn("cross-object or cross-bank relationships", lanes["0x02"].non_claims)
        for lane in lanes.values():
            for shared in (
                "serialized field ownership or field names",
                "runtime execution, event selection, or audibility",
            ):
                self.assertIn(shared, lane.non_claims)

    def test_every_counted_element_has_a_declared_byte_width(self) -> None:
        # A lane that forgets to declare its terminal vector would leave that counter
        # unbounded, which is exactly how a reader-side over-count could hide.
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        undeclared = copy.deepcopy(audio_audit)
        for scope in (
            undeclared["rows"][0]["package"],
            undeclared["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircType05BodyFrame"]["groupCounts"]["mysteryEntries"] = 4
        with self.assertRaisesRegex(ValueError, "no declared byte width"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, undeclared)

        oversized = copy.deepcopy(audio_audit)
        for scope in (
            oversized["rows"][0]["package"],
            oversized["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircType05BodyFrame"]["groupCounts"]["recordEntries"] = 1_000_000
        with self.assertRaisesRegex(ValueError, "anonymous element bytes exceed the framed bodies"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, oversized)

    def test_type07_body_frames_reuse_the_shared_node_frame(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)
        bodies = result["type07BodyFrames"]
        self.assertEqual(bodies["count"], 2)
        self.assertEqual(bodies["exact"], 2)
        self.assertEqual(bodies["frameClosure"], "all-bodies-exact")
        self.assertEqual(bodies["bodyBytes"], bodies["exactCursorBytes"])
        self.assertEqual(bodies["nonExactBodyBytes"], 0)
        self.assertEqual(bodies["anonymousGroupCounts"]["childEntries"], 4)
        self.assertEqual(bodies["minExactBodyBytes"], 110)
        self.assertIn("same ones proven on type 0x02", bodies["sharedNodeFrame"])
        self.assertTrue(body_lane_corpus_is_closed(bodies))

    def test_type07_body_gate_rejects_partition_and_byte_mismatches(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()

        bad_partition = copy.deepcopy(audio_audit)
        bad_partition["rows"][0]["package"]["hircType07BodyFrame"]["exact"] = 1
        with self.assertRaisesRegex(ValueError, "type 0x07 body outcome partition mismatch"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, bad_partition)

        bad_declared = copy.deepcopy(audio_audit)
        for scope in (
            bad_declared["rows"][0]["package"],
            bad_declared["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircType07BodyFrame"]["bodyBytes"] = 236
            scope["hircType07BodyFrame"]["exactCursorBytes"] = 236
        with self.assertRaisesRegex(ValueError, "type 0x07 body bytes differ from declared"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, bad_declared)

        # A single body below the 35-byte floor must be refused even when the mean is fine.
        short_body = copy.deepcopy(audio_audit)
        for scope in (
            short_body["rows"][0]["package"],
            short_body["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircType07BodyFrame"].update(
                {"minExactBodyBytes": 34, "maxExactBodyBytes": 130}
            )
        with self.assertRaisesRegex(ValueError, "type 0x07 exact body falls below the minimum frame"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, short_body)

        bad_bank = copy.deepcopy(audio_audit)
        bad_bank["rows"][0]["package"]["bnkStructures"][0]["hircType07BodyFrame"][
            "groupCounts"
        ]["childEntries"] = 3
        with self.assertRaisesRegex(ValueError, "type 0x07 group inventory mismatch"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, bad_bank)

        missing = copy.deepcopy(audio_audit)
        del missing["rows"][0]["package"]["hircType07BodyFrame"]
        with self.assertRaisesRegex(ValueError, "missing type 0x07 body-frame result"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, missing)

    def test_body_gate_bounds_every_variable_length_inventory(self) -> None:
        # Outcome counts were already policed; the anonymous inventories are where a
        # reader-side over-consumption could otherwise grow without being noticed.
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()

        for scale, pattern in ((99, "not bounded by their entry count"), (0, "not bounded")):
            inflated = copy.deepcopy(audio_audit)
            for scope in (
                inflated["rows"][0]["package"],
                inflated["rows"][0]["package"]["bnkStructures"][0],
            ):
                scope["hircType07BodyFrame"]["groupCounts"]["groupIKeyBytes"] = scale
            with self.assertRaisesRegex(ValueError, pattern):
                aggregate_current_hirc_actions(outer, expected_files, excluded_files, inflated)

        histogram = copy.deepcopy(audio_audit)
        for scope in (
            histogram["rows"][0]["package"],
            histogram["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircType07BodyFrame"]["selectorCounts"]["groupIKeyWidth_2"] = 2
        with self.assertRaisesRegex(ValueError, "key width histogram does not match its entry count"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, histogram)

        mismatched = copy.deepcopy(audio_audit)
        for scope in (
            mismatched["rows"][0]["package"],
            mismatched["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircType07BodyFrame"]["selectorCounts"] = {
                "groupAFlag_00": 2,
                "groupBFlag_00": 2,
                "groupESelector_00": 2,
                "groupFSelector_00": 2,
                "groupIKeyWidth_1": 2,
                "groupHStateWidth_12": 1,
                "groupHStateWidth_18": 1,
            }
        with self.assertRaisesRegex(ValueError, "key width histogram does not sum to its byte total"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, mismatched)

        oversized = copy.deepcopy(audio_audit)
        for scope in (
            oversized["rows"][0]["package"],
            oversized["rows"][0]["package"]["bnkStructures"][0],
        ):
            scope["hircType07BodyFrame"]["groupCounts"]["childEntries"] = 1_000_000
        with self.assertRaisesRegex(ValueError, "anonymous element bytes exceed the framed bodies"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, oversized)

    def test_type07_body_closure_is_enforced_not_just_reported(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        closed = aggregate_current_hirc_actions(
            outer, expected_files, excluded_files, audio_audit
        )["type07BodyFrames"]
        self.assertTrue(body_lane_corpus_is_closed(closed))
        for field, value in (
            ("frameClosure", "incomplete"),
            ("exact", 1),
            ("unsupported", 1),
            ("failed", 1),
            ("ambiguous", 1),
            ("nonExactBodyBytes", 1),
        ):
            regressed = dict(closed)
            regressed[field] = value
            self.assertFalse(
                body_lane_corpus_is_closed(regressed),
                f"{field}={value} must not count as a closed corpus",
            )

    def test_type07_body_markdown_records_the_shared_frame_and_open_questions(self) -> None:
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
                "toolClosure": {"fileCount": 79, "manifestSha256": "G" * 64},
                "intermediatePath": "tmp/audio-audit.json",
                "sha256": "E" * 64,
            },
            "corpusGate": {"sha256": "F" * 64},
            "corpus": {
                "packageCount": 1,
                "verifiedPackageCount": 1,
                "excludedBlockCount": 0,
                "type07BodyFrames": {
                    "frameClosure": "all-bodies-exact",
                    "count": 1,
                    "exact": 1,
                    "unsupported": 0,
                    "failed": 0,
                    "ambiguous": 0,
                    "bodyBytes": 35,
                    "exactCursorBytes": 35,
                    "nonExactBodyBytes": 0,
                    "minExactBodyBytes": 35,
                    "maxExactBodyBytes": 35,
                    "minimumPossibleFrameBytes": 35,
                    "frameLayout": "The reader consumes the node groups and one counted reference vector.",
                    "packagesWithObjects": 1,
                    "banksWithObjects": 1,
                    "sharedNodeFrame": "the nine anonymous groups are the same ones proven on type 0x02 bodies",
                    "anonymousGroupCounts": {"childEntries": 0},
                    "anonymousSelectorCounts": {"groupAFlag_00": 1},
                    "failureCategories": {},
                    "unsupportedCategories": {},
                    "objectCountsByBlock": {"Audio": 1},
                    "unresolvedWidths": ["group B element width: no nonempty vector"],
                    "upstreamAbortsNotCountedHere": "every malformed body reaches this lane",
                },
            },
        }

        markdown = _body_lane_markdown(report, "type07BodyFrames", "0x07")

        self.assertIn("all-bodies-exact", markdown)
        self.assertIn("same ones proven on type 0x02", markdown)
        self.assertIn("What this corpus does not resolve", markdown)
        self.assertIn("stay anonymous", markdown)
        self.assertIn("does not establish serialized field ownership", markdown)
        self.assertIn("Closure is enforced", markdown)

    def test_type04_candidate_vector_gate_rejects_structural_mismatches(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        bad_prefix_math = copy.deepcopy(audio_audit)
        bad_prefix_math["rows"][0]["package"]["hircType04U32VectorFrame"]["candidateEntryCount"] = 1
        with self.assertRaisesRegex(ValueError, "count-byte/u32-entry arithmetic"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, bad_prefix_math)

        bad_package_bytes = copy.deepcopy(audio_audit)
        bad_package_bytes["rows"][0]["package"]["hircType04U32VectorFrame"]["opaqueTailBytes"] = 2
        with self.assertRaisesRegex(ValueError, "candidate-prefix/tail/failed body accounting"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, bad_package_bytes)

        bad_bank_partition = copy.deepcopy(audio_audit)
        bank_frame = bad_bank_partition["rows"][0]["package"]["bnkStructures"][0]["hircType04U32VectorFrame"]
        bank_frame["exact"] = 2
        bank_frame["unsupported"] = 0
        bank_frame["unsupportedCandidatePrefixBytes"] = 0
        bank_frame["exactCursorBytes"] = 10
        bank_frame["opaqueTailBytes"] = 0
        bank_frame["bodyBytes"] = 10
        bank_frame["unsupportedCategories"] = {}
        bank_stats = bad_bank_partition["rows"][0]["package"]["bnkStructures"][0]["hircObjectTypeStats"]["0x04"]
        bank_stats["declaredLengthBytes"] = 18
        with self.assertRaisesRegex(ValueError, "per-bank/package type 0x04 candidate-vector total mismatch"):
            aggregate_current_hirc_actions(outer, expected_files, excluded_files, bad_bank_partition)

    def test_type04_gate_preserves_a_counted_short_body_failure(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        failed_frame = {
            "count": 2,
            "exactEntryCount": 1,
            "exact": 1,
            "unsupported": 0,
            "failed": 1,
            "ambiguous": 0,
            "bodyBytes": 11,
            "candidatePrefixBytes": 5,
            "unsupportedCandidatePrefixBytes": 0,
            "exactCursorBytes": 5,
            "opaqueTailBytes": 0,
            "failedBodyBytes": 6,
            "candidateEntryCount": 1,
            "failureCategories": {"truncated_entries": 1},
            "unsupportedCategories": {},
            "nonExactExamples": [
                {
                    "bankId": 123,
                    "ordinal": 2,
                    "objectId": 456,
                    "status": "failed",
                    "category": "truncated_entries",
                    "expectedBytes": 9,
                    "actualBytes": 6,
                    "opaqueTailBytes": 0,
                }
            ],
        }
        package = audio_audit["rows"][0]["package"]
        package["hircType04U32VectorFrame"] = copy.deepcopy(failed_frame)
        package["bnkStructures"][0]["hircType04U32VectorFrame"] = copy.deepcopy(failed_frame)

        result = aggregate_current_hirc_actions(outer, expected_files, excluded_files, audio_audit)

        vectors = result["type04U32VectorCandidates"]
        self.assertEqual(vectors["exact"], 1)
        self.assertEqual(vectors["failed"], 1)
        self.assertEqual(vectors["failedBodyBytes"], 6)
        self.assertEqual(vectors["failureCategories"], {"truncated_entries": 1})
        self.assertEqual(vectors["frameClosure"], "incomplete")

    def test_type02_prefix_gate_rejects_byte_count_and_bank_mismatches(self) -> None:
        outer, expected_files, excluded_files, audio_audit = valid_action_fixture()
        bad_tail = copy.deepcopy(audio_audit)
        bad_tail["rows"][0]["package"]["hircType02Prefix"]["opaqueTailBytes"] = 63
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
            "opaqueTailBytes": 65,
            "maxOpaqueTailBytes": 33,
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
