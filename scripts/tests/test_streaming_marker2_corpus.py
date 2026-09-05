from __future__ import annotations

import gzip
import hashlib
import json
import copy
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.game_data import streaming_marker2_corpus as gate
from scripts.game_data.streaming_marker2 import parse_marker2_gaps
from scripts.tests.test_streaming_marker2 import SOURCE as REAL_SOURCE
from scripts.tests.test_streaming_marker2 import fixture as real_marker2_fixture


INPUT_SET = "A" * 64


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


class Fixture:
    def __init__(self, root: Path):
        self.root = root
        self.game_root = root / "Endfield_Data"
        (self.game_root / "il2cpp_data/Metadata").mkdir(parents=True)
        (root / "GameAssembly.dll").write_bytes(b"ga")
        (root / "UnityPlayer.dll").write_bytes(b"unity")
        (self.game_root / "il2cpp_data/Metadata/global-metadata.dat").write_bytes(b"metadata")
        self.clear = bytes(range(64))
        self.chunk = root / "chunk.chk"
        self.chunk.write_bytes(self.clear)
        self.ledger = root / "ledger.jsonl.gz"
        self.outer = root / "outer.json"
        self.report = root / "v15.json"
        self.inventory = root / "inventory.jsonl.gz"
        self.synthetic_source = root / "synthetic-source.py"
        self.synthetic_source.write_bytes(b"source")
        self.virtual_path = (
            "Data/Streaming/PC/test/one/Streaming/StreamingChunkData_0_0_0_0.bytes"
        )
        self.primary = (self.game_root / "Persistent").as_posix()
        self.fallback = (self.game_root / "StreamingAssets").as_posix()
        (Path(self.primary) / "VFS").mkdir(parents=True)
        (Path(self.fallback) / "VFS").mkdir(parents=True)
        self.fingerprint = Path(self.primary) / "VFS/source.blc"
        self.fingerprint.write_bytes(b"outer source")
        self.certified_ranges = [(0, 32, "before"), (36, 64, "after")]
        self.write_all()

    def paths(self, _repo_root: Path) -> dict[str, Path]:
        names = (
            "rootParserSha256", "orderedPairValidatorSha256",
            "invertedLz4DecoderSha256", "commonNativeGateSha256",
            "rootCorpusGateSha256", "rootNativeValidatorSha256",
            "rootNativeContractSha256", "marker17ParserSha256",
            "marker17NativeValidatorSha256", "marker17NativeContractSha256",
            "sharedMarker13ParserSha256", "sharedMarker13NativeValidatorSha256",
            "sharedMarker13NativeContractSha256", "marker2DirectorySha256",
            "marker2ParserSha256", "marker2NativeValidatorSha256",
            "marker2NativeContractSha256", "sharedCorpusHelpersSha256",
            "marker2CorpusGateSha256",
        )
        return {name: self.synthetic_source for name in names}

    def ledger_rows(self) -> list[dict]:
        return [
            {
                "recordType": "audit_header", "schemaVersion": 1,
                "inputSetSha256": INPUT_SET, "primaryAssets": self.primary,
                "fallbackAssets": self.fallback,
            },
            {
                "recordType": "file", "blockTypeValue": 15,
                "virtualPath": self.virtual_path,
                "physicalChunkPath": self.chunk.as_posix(),
                "physicalChunkSource": "primary", "metadataProvenance": "primary",
                "overlayState": "primary_only", "chunkFile": self.chunk.name,
                "offset": 0, "length": len(self.clear),
                "status": "verified", "boundaryStatus": "boundary_verified",
                "inputSetSha256": INPUT_SET, "encrypted": False,
                "actualBytesRead": len(self.clear),
                "recomputedFileDataMd5": hashlib.md5(
                    self.clear, usedforsecurity=False
                ).hexdigest().upper(),
            },
        ]

    def write_ledger(self) -> None:
        with gzip.open(self.ledger, "wt", encoding="utf-8") as stream:
            for row in self.ledger_rows():
                stream.write(json.dumps(row) + "\n")

    def write_outer(self) -> None:
        write_json(self.outer, {
            "inputSetSha256": INPUT_SET, "primaryAssets": self.primary,
            "fallbackAssets": self.fallback, "summary": {"fullAuditPassed": True},
            "sourceFingerprints": [{
                "path": self.fingerprint.as_posix(),
                "length": self.fingerprint.stat().st_size,
                "sha256": gate.shared.sha256_file(self.fingerprint),
            }],
            "buildFingerprints": [],
            "publication": {"ledgerSha256": gate.shared.sha256_file(self.ledger)},
        })

    def write_report(self, *, marker2_count: int = 1) -> None:
        source_hash = gate.shared.sha256_file(self.synthetic_source)
        packed_md5 = hashlib.md5(
            self.clear, usedforsecurity=False
        ).hexdigest().upper()
        identity = "\0".join((
            self.virtual_path, "primary", self.chunk.name, "0", str(len(self.clear)),
            packed_md5, gate.shared.sha256_bytes(self.clear),
        ))
        write_json(self.report, {
            "schema": gate.ROOT_SCHEMA, "status": "complete", "failed": False,
            "inputSetSha256": INPUT_SET,
            "provenance": {
                "inputSetSha256": INPUT_SET,
                "outerLedgerSha256": gate.shared.sha256_file(self.ledger),
                "primaryAssets": self.primary, "fallbackAssets": self.fallback,
                "parserSha256": source_hash, "corpusGateSha256": source_hash,
                "nativeValidatorSha256": source_hash,
                "nativeContractSha256": source_hash,
            },
            "summary": {"streamingFiles": 1, "parsed": 1, "failed": 0,
                        "unsupported": 0, "gateFailures": 0},
            "layer1": {"logicalIdentitySetSha256": gate.shared.sha256_bytes(
                identity.encode("utf-8")
            )},
            "layer3": {
                "nestedElementFraming": {"nestedElementMarkerCounts": {
                    "2": marker2_count,
                }},
            },
            "failures": [],
        })

    def write_all(self) -> None:
        self.write_ledger()
        self.write_outer()
        self.write_report()

    def parsed(self, family: str, packed: bytes, **kwargs) -> dict:
        if family != "streaming" or packed != self.clear:
            raise ValueError("unexpected root parser input")
        if kwargs.get("native_layout_validated") is not True:
            raise ValueError("native layout must be validated")
        if kwargs.get("include_certified_ranges") is not True:
            raise ValueError("certified ranges must be requested")
        return {
            "encoding": "raw_flatbuffer", "decodedBytes": len(packed),
            "decodedCertifiedRanges": list(self.certified_ranges),
            "anonymousParallelSubgraph": {"nestedElementMarkerCounts": {2: 1}},
        }

    @staticmethod
    def directory_row() -> dict:
        return {
            "rootMarker": 2, "rowSelectorU32": 6, "key": 0x09020000,
            "marker": 2, "targetStart": 32, "targetOwnedBytes": 0,
        }

    def projection(self, *, status: str = gate.FRAMED_STATUS,
                   gap_end: int = 36) -> dict:
        row = {
            **self.directory_row(), "status": status, "targetOwnedBytes": 0,
            "family": "streaming",
        }
        if status == gate.FRAMED_STATUS:
            row.update({
                "physicalGapRange": {"start": 32, "end": gap_end,
                                     "length": gap_end-32},
                "nativeReadWindowRange": {"start": 32, "end": 36, "length": 4},
                "residualOpaqueRange": (
                    None if gap_end == 36 else
                    {"start": 36, "end": gap_end, "length": gap_end-36}
                ),
            })
        framed = int(status == gate.FRAMED_STATUS)
        unsupported = int(status in gate.UNSUPPORTED_STATUSES)
        ambiguous = int(status in gate.AMBIGUOUS_STATUSES)
        return {
            "status": (
                "ambiguous" if ambiguous else "partial" if unsupported
                else "exact-anonymous-physical-gaps"
            ),
            "family": "streaming",
            "profile": {**dict(gate.NATIVE_PROFILE), "physicalGapLengths": [4, 6]},
            "directory": {
                "status": "exact-structural-marker2-reference-directory",
                "rows": [self.directory_row()],
                "counts": {"marker2References": 1},
            },
            "rows": [row],
            "summary": {
                "references": 1, "framed": framed, "unsupported": unsupported,
                "ambiguous": ambiguous,
                "physicalGapBytes": gap_end-32 if framed else 0,
                "nativeReadWindowBytes": 4 if framed else 0,
                "opaqueBytes": max(0, gap_end-36) if framed else 0,
                "targetOwnedBytes": 0,
            },
            "statusCounts": {status: 1},
            "targetOwnedBytes": 0,
        }

    def native(self) -> dict:
        return {
            "status": "validated", "validationFailures": [],
            "contractSha256": gate.shared.sha256_file(self.synthetic_source),
            "profile": dict(gate.NATIVE_PROFILE),
        }

    def run(self, *, projection: dict | None = None, **kwargs) -> dict:
        selected_projection = projection or self.projection()
        repo_root = kwargs.pop("repo_root", self.root)
        with (
            mock.patch.object(gate, "MODULE_REPO_ROOT", self.root),
            mock.patch.object(gate, "source_paths", side_effect=self.paths),
            mock.patch.object(gate, "validate_marker2_native_contract", return_value=self.native()),
            mock.patch.object(gate.fmt, "parse_streaming_file", side_effect=self.parsed),
            mock.patch.object(gate, "index_ordered_pairs", return_value={self.virtual_path: None}),
            mock.patch.object(gate, "bind_current_pair", return_value={
                "source": self.virtual_path, "side": "streaming",
                "decodedSha256": gate.shared.sha256_bytes(self.clear),
            }) as bind,
            mock.patch.object(gate, "parse_marker2_gaps", return_value=selected_projection),
        ):
            result = gate.sweep(
                repo_root=repo_root, root_report_path=self.report,
                outer_summary_path=self.outer, ledger_path=self.ledger,
                expected_input_set_sha256=INPUT_SET, game_root=self.game_root,
                **kwargs,
            )
        self.bind = bind
        return result


class Marker2CorpusTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.fx = Fixture(Path(self.temporary.name))

    def tearDown(self):
        self.temporary.cleanup()

    def test_normal_full_gate_reconciles_one_reference_and_pair(self):
        result = self.fx.run()
        self.assertEqual((result["status"], result["publicationEligible"]), ("complete", True))
        self.assertEqual(result["summary"]["marker2References"], 1)
        self.assertEqual(result["summary"]["framedReferences"], 1)
        self.assertEqual(result["summary"]["nativeReadWindowReferenceBytes"], 4)
        self.assertEqual(result["summary"]["targetOwnedBytes"], 0)
        self.fx.bind.assert_called_once()
        inventory = result["_inventoryRows"]
        self.assertEqual(inventory[0]["recordType"], "inventory_header")
        self.assertEqual(inventory[-1]["recordType"], "inventory_terminal")

    def test_adapter_accepts_actual_root_parser_collector_and_streaming_pair(self):
        data, parsed, context = real_marker2_fixture()
        projection = parse_marker2_gaps(
            data, source=REAL_SOURCE, family="streaming", parsed=parsed,
            native_layout_validated=True, pair_context=context,
        )
        counts, coverage = gate.validate_projection(
            projection, family="streaming", expected_references=1,
            decoded_length=len(data), certified_ranges=parsed["decodedCertifiedRanges"],
        )
        self.assertEqual((counts["framed"], coverage["nativeReadWindowReferenceBytes"]), (1, 4))

    def test_adapter_accepts_actual_init_root_and_keeps_it_unsupported(self):
        data, parsed, _context = real_marker2_fixture(family="init")
        projection = parse_marker2_gaps(
            data, source=REAL_SOURCE, family="init", parsed=parsed,
            native_layout_validated=True, pair_context=None,
        )
        counts, coverage = gate.validate_projection(
            projection, family="init", expected_references=1,
            decoded_length=len(data), certified_ranges=parsed["decodedCertifiedRanges"],
        )
        self.assertEqual((counts["unsupported"], coverage["nativeReadWindowReferenceBytes"]), (1, 0))

    def test_gap6_keeps_two_bytes_in_opaque_complement(self):
        self.fx.certified_ranges = [(0, 32, "before"), (38, 64, "after")]
        result = self.fx.run(projection=self.fx.projection(gap_end=38))
        self.assertFalse(result["failed"])
        self.assertEqual(result["summary"]["physicalGapReferenceBytes"], 6)
        self.assertEqual(result["summary"]["nativeReadWindowReferenceBytes"], 4)
        self.assertEqual(result["summary"]["residualOpaqueReferenceBytes"], 2)
        coverage = result["_inventoryRows"][1]["rangeCoverage"]
        self.assertEqual(coverage["opaqueComplement"], [
            {"start": 36, "end": 38, "length": 2},
        ])

    def test_unknown_exclusive_gap5_is_a_file_failure(self):
        self.fx.certified_ranges = [(0, 32, "before"), (37, 64, "after")]
        result = self.fx.run(projection=self.fx.projection(gap_end=37))
        self.assertTrue(result["failed"])
        self.assertEqual(result["summary"]["filesFailed"], 1)
        self.assertIn("physical gap4/6", result["failures"][-1]["actual"])

    def test_framed_window_cannot_move_away_from_directory_target(self):
        projection = self.fx.projection()
        projection["rows"][0]["physicalGapRange"] = {
            "start": 40, "end": 44, "length": 4,
        }
        projection["rows"][0]["nativeReadWindowRange"] = {
            "start": 40, "end": 44, "length": 4,
        }
        with self.assertRaisesRegex(ValueError, "target-started read4"):
            gate.validate_projection(
                projection, family="streaming", expected_references=1,
                decoded_length=64,
                certified_ranges=[(0, 40, "before"), (44, 64, "after")],
            )

    def test_framed_row_must_match_native_selected_identity(self):
        projection = self.fx.projection()
        projection["rows"][0]["family"] = "init"
        with self.assertRaisesRegex(ValueError, "native selected identity"):
            gate.validate_projection(
                projection, family="streaming", expected_references=1,
                decoded_length=64, certified_ranges=self.fx.certified_ranges,
            )

    def test_projection_cannot_duplicate_first_identity_and_drop_second(self):
        projection = self.fx.projection()
        first_directory = {**self.fx.directory_row(), "outerRowIndex": 0}
        second_directory = {**self.fx.directory_row(), "outerRowIndex": 1, "targetStart": 40}
        first_projection = {**projection["rows"][0], **first_directory}
        second_projection = copy.deepcopy(first_projection)
        projection["directory"]["rows"] = [first_directory, second_directory]
        projection["directory"]["counts"]["marker2References"] = 2
        projection["rows"] = [first_projection, second_projection]
        projection["summary"].update(
            references=2, framed=2, physicalGapBytes=8,
            nativeReadWindowBytes=8, opaqueBytes=0,
        )
        projection["statusCounts"] = {"framed": 2}
        with self.assertRaisesRegex(ValueError, "complete directory identity"):
            gate.validate_projection(
                projection, family="streaming", expected_references=2,
                decoded_length=64, certified_ranges=self.fx.certified_ranges,
            )

    def test_overlapping_physical_gaps_and_residual_read_overlap_fail(self):
        projection = self.fx.projection(gap_end=38)
        first = projection["rows"][0]
        second = {
            **copy.deepcopy(first), "outerRowIndex": 1, "targetStart": 36,
            "physicalGapRange": {"start": 36, "end": 40, "length": 4},
            "nativeReadWindowRange": {"start": 36, "end": 40, "length": 4},
            "residualOpaqueRange": None,
        }
        projection["directory"]["rows"] = [
            {key: value for key, value in first.items() if key not in {
                "status", "physicalGapRange", "nativeReadWindowRange",
                "residualOpaqueRange", "targetOwnedBytes",
            }},
            {key: value for key, value in second.items() if key not in {
                "status", "physicalGapRange", "nativeReadWindowRange",
                "residualOpaqueRange", "targetOwnedBytes",
            }},
        ]
        # targetOwnedBytes belongs to the directory too in the actual collector.
        for row in projection["directory"]["rows"]:
            row["targetOwnedBytes"] = 0
        projection["directory"]["counts"]["marker2References"] = 2
        projection["rows"] = [first, second]
        projection["summary"].update(
            references=2, framed=2, physicalGapBytes=10,
            nativeReadWindowBytes=8, opaqueBytes=2,
        )
        projection["statusCounts"] = {"framed": 2}
        with self.assertRaisesRegex(ValueError, "physical gaps.*pairwise disjoint"):
            gate.validate_projection(
                projection, family="streaming", expected_references=2,
                decoded_length=64,
                certified_ranges=[(0, 32, "before"), (40, 64, "after")],
            )

    def test_exact_read_window_equal_to_certified_range_does_not_deduplicate(self):
        projection = self.fx.projection()
        with self.assertRaisesRegex(ValueError, "category-disjoint"):
            gate.validate_projection(
                projection, family="streaming", expected_references=1,
                decoded_length=64,
                certified_ranges=[
                    (0, 32, "before"), (32, 36, "certified-equal-window"),
                    (36, 64, "after"),
                ],
            )

    def test_nonframed_row_cannot_smuggle_a_read_window(self):
        projection = self.fx.projection(status="unsupported-cluster")
        projection["rows"][0]["nativeReadWindowRange"] = {
            "start": 32, "end": 36, "length": 4,
        }
        result = self.fx.run(projection=projection)
        self.assertTrue(result["failed"])
        self.assertIn("must not expose ranges", result["failures"][-1]["actual"])

    def test_bool_summary_count_is_rejected(self):
        projection = self.fx.projection()
        projection["summary"]["framed"] = True
        result = self.fx.run(projection=projection)
        self.assertTrue(result["failed"])
        self.assertIn("summary.framed", result["failures"][-1]["actual"])

    def test_executed_source_changes_before_terminal_discard_inventory(self):
        original = gate.shared.snapshot_sources

        def snapshot(paths, failures, stage):
            if stage == "source-end":
                self.fx.synthetic_source.write_bytes(b"changed source")
            return original(paths, failures, stage)

        with mock.patch.object(gate.shared, "snapshot_sources", side_effect=snapshot):
            result = self.fx.run()
        self.assertTrue(result["failed"])
        self.assertEqual(result["_inventoryRows"], [])
        self.assertTrue(any(row.get("field") == "sourceHashes" for row in result["failures"]))

    def test_native_image_changes_before_terminal_discard_inventory(self):
        original = gate.shared.snapshot_native_inputs

        def snapshot(game_root, failures, stage):
            if stage == "native-inputs-end":
                (self.fx.root / "UnityPlayer.dll").write_bytes(b"changed image")
            return original(game_root, failures, stage)

        with mock.patch.object(gate.shared, "snapshot_native_inputs", side_effect=snapshot):
            result = self.fx.run()
        self.assertTrue(result["failed"])
        self.assertEqual(result["_inventoryRows"], [])
        self.assertTrue(any(row.get("field") == "nativeInputHashes" for row in result["failures"]))

    def test_blc_added_before_terminal_discard_inventory(self):
        original = gate.snapshot_blc_manifest_set

        def snapshot(outer, failures, stage):
            if stage == "blc-manifest-end":
                (Path(self.fx.primary) / "VFS/new.blc").write_bytes(b"new manifest")
            return original(outer, failures, stage)

        with mock.patch.object(gate, "snapshot_blc_manifest_set", side_effect=snapshot):
            result = self.fx.run()
        self.assertTrue(result["failed"])
        self.assertEqual(result["_inventoryRows"], [])
        self.assertTrue(any(row.get("field") == "blcManifestPathSet" for row in result["failures"]))

    def test_nonframed_row_cannot_smuggle_scalar_or_pair_evidence(self):
        for field, value in (("anonymousU32", 0), ("pairRow", {"outerRowIndex": 0})):
            with self.subTest(field=field):
                projection = self.fx.projection(status="unsupported-cluster")
                projection["rows"][0][field] = value
                result = self.fx.run(projection=projection)
                self.assertTrue(result["failed"])
                self.assertIn("must not expose ranges", result["failures"][-1]["actual"])

    def test_root_report_marker2_count_mismatch_blocks_publication(self):
        self.fx.write_report(marker2_count=2)
        result = self.fx.run()
        self.assertTrue(result["failed"])
        self.assertFalse(result["publicationEligible"])
        self.assertTrue(any(
            row.get("field") == "marker2ReferenceCount" for row in result["failures"]
        ))

    def test_partial_is_never_publication_eligible(self):
        result = self.fx.run(max_files=1)
        self.assertEqual(result["status"], "partial")
        self.assertFalse(result["publicationEligible"])

    def test_partial_direct_api_inventory_must_stay_in_tmp_or_scratch(self):
        unsafe = self.fx.root / "reports/partial.jsonl.gz"
        result = self.fx.run(max_files=1, inventory_path=unsafe)
        self.assertTrue(result["failed"])
        self.assertFalse(unsafe.exists())
        self.assertTrue(any(
            row.get("field") == "inventoryPath" for row in result["failures"]
        ))

    def test_failed_gate_does_not_replace_existing_inventory(self):
        self.fx.inventory.write_bytes(b"old inventory")
        projection = self.fx.projection(gap_end=37)
        self.fx.certified_ranges = [(0, 32, "before"), (37, 64, "after")]
        result = self.fx.run(projection=projection, inventory_path=self.fx.inventory)
        self.assertTrue(result["failed"])
        self.assertEqual(self.fx.inventory.read_bytes(), b"old inventory")

    def test_inventory_cannot_alias_a_physical_chunk(self):
        original = self.fx.chunk.read_bytes()
        result = self.fx.run(inventory_path=self.fx.chunk)
        self.assertTrue(result["failed"])
        self.assertEqual(self.fx.chunk.read_bytes(), original)
        self.assertTrue(any(
            row["stage"] == "output-path-isolation" for row in result["failures"]
        ))

    def test_repo_root_cannot_name_a_different_checkout(self):
        other = self.fx.root / "other-checkout"
        other.mkdir()
        result = self.fx.run(repo_root=other)
        self.assertTrue(result["failed"])
        self.assertTrue(any(
            row["stage"] == "source-root-gate" for row in result["failures"]
        ))

    def test_new_live_blc_not_in_authenticated_manifest_fails(self):
        extra = Path(self.fx.fallback) / "VFS/new.blc"
        extra.write_bytes(b"new")
        result = self.fx.run()
        self.assertTrue(result["failed"])
        self.assertTrue(any(
            row.get("field") == "blcManifestPathSet"
            and row["stage"] == "blc-manifest-start"
            for row in result["failures"]
        ))

    def test_authenticated_blc_missing_from_live_roots_fails(self):
        self.fx.fingerprint.unlink()
        result = self.fx.run()
        self.assertTrue(result["failed"])
        self.assertTrue(any(
            row.get("field") == "blcManifestPathSet"
            and row["stage"] == "blc-manifest-start"
            for row in result["failures"]
        ))


if __name__ == "__main__":
    unittest.main()
