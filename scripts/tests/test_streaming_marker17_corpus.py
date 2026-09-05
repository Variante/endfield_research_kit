from __future__ import annotations

import copy
import gzip
import hashlib
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
from scripts.game_data import streaming_marker17_corpus as gate

INPUT_SET = "A" * 64


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


class Fixture:
    def __init__(self, root: Path, *, key: int = 0x09000000):
        self.root = root
        self.key = key
        self.clear = self.make_clear(key=key)
        self.chunk = root / "chunk.chk"
        self.chunk.write_bytes(self.clear)
        self.ledger = root / "ledger.jsonl.gz"
        self.outer = root / "outer.json"
        self.report = root / "v15.json"
        fp = root / "fingerprint.bin"
        fp.write_bytes(b"authenticated outer source")
        self.fingerprints = [{"path": fp.as_posix(), "length": fp.stat().st_size,
                              "sha256": gate.sha256_file(fp)}]
        self.primary = (root / "Persistent").as_posix()
        self.fallback = (root / "StreamingAssets").as_posix()
        self.files = [self.make_file("fixture", self.chunk.as_posix(), key=key)]
        self.write_all()

    @staticmethod
    def make_clear(*, key: int = 0x09000000, tag: int = 5) -> bytes:
        body = bytearray(64)
        struct.pack_into("<h", body, 28, tag)
        clear = bytearray(110)
        struct.pack_into("<I", clear, 0, 16)
        clear[4] = 17
        struct.pack_into("<I", clear, 6, key)
        struct.pack_into("<HHH", clear, 10, 6, 8, 4)
        struct.pack_into("<iI", clear, 16, 6, 10)
        struct.pack_into("<HHH", clear, 24, 6, 8, 4)
        struct.pack_into("<iI", clear, 30, 6, 8)
        struct.pack_into("<I", clear, 42, len(body))
        clear[46:] = body
        return bytes(clear)

    @staticmethod
    def directory_row(*, key: int) -> dict:
        return {
            "outerRowIndex": 0, "outerRowOffset": 0, "rootMarker": 2,
            "rowSelectorU32": 6, "rowSelectorLowByte": 6,
            "nestedTableOffset": 0, "nestedElementCount": 1, "elementIndex": 0,
            "key": key, "keyHex": f"{key:08X}", "keyOffset": 6,
            "keyOccurrenceCountInTable": 1, "keyStatus": "unique",
            "marker": 17, "markerOffset": 4, "targetSlotOffset": 0,
            "byteCount": 64,
            "wrapperAndByteRanges": [
                {"start": 10, "end": 16, "kind": "vtable"},
                {"start": 16, "end": 24, "kind": "table"},
                {"start": 24, "end": 30, "kind": "vtable"},
                {"start": 30, "end": 38, "kind": "table"},
                {"start": 42, "end": 110, "kind": "length-prefixed-byte-range"},
            ],
        }

    def make_file(self, suffix: str, chunk: str, *, key: int) -> dict:
        return {
            "virtualPath": f"Data/Streaming/PC/{suffix}/Streaming/StreamingChunkData_0_0_0_0.bytes",
            "physicalChunkPath": chunk, "physicalChunkSource": "fallback",
            "metadataProvenance": "primary", "overlayState": "identical",
            "offset": 0, "length": len(self.clear), "packedSha256": gate.sha256_bytes(self.clear),
            "family": "streaming", "rows": [self.directory_row(key=key)],
        }

    def ledger_rows(self) -> list[dict]:
        rows = [{"recordType": "audit_header", "schemaVersion": 1,
                 "inputSetSha256": INPUT_SET, "primaryAssets": self.primary,
                 "fallbackAssets": self.fallback}]
        for item in self.files:
            rows.append({
                "recordType": "file", "blockTypeValue": 15,
                **{field: item[field] for field in (
                    "virtualPath", "physicalChunkPath", "physicalChunkSource",
                    "metadataProvenance", "overlayState", "offset", "length")},
                "status": "verified", "boundaryStatus": "boundary_verified",
                "inputSetSha256": INPUT_SET, "encrypted": False,
                "actualBytesRead": item["length"],
                "recomputedFileDataMd5": hashlib.md5(self.clear, usedforsecurity=False).hexdigest().upper(),
            })
        return rows

    def write_ledger(self) -> None:
        with gzip.open(self.ledger, "wt", encoding="utf-8") as stream:
            for row in self.ledger_rows():
                stream.write(json.dumps(row) + "\n")

    def write_outer(self) -> None:
        write_json(self.outer, {
            "format": "animestudio-vfs-boundary-audit", "schemaVersion": 1,
            "inputSetSha256": INPUT_SET, "primaryAssets": self.primary,
            "fallbackAssets": self.fallback, "summary": {"fullAuditPassed": True},
            "sourceFingerprints": self.fingerprints, "buildFingerprints": [],
            "publication": {"ledgerSha256": gate.sha256_file(self.ledger)},
        })

    def write_report(self) -> None:
        refs = sum(len(item["rows"]) for item in self.files)
        counted = sum(row["byteCount"] for item in self.files for row in item["rows"])
        paths = gate._source_paths(ROOT)
        provenance = {
            "inputSetSha256": INPUT_SET, "outerLedgerSha256": gate.sha256_file(self.ledger),
            "primaryAssets": self.primary, "fallbackAssets": self.fallback,
            "parserSha256": gate.sha256_file(paths["v15ParserSha256"]),
            "corpusGateSha256": gate.sha256_file(paths["v15CorpusGateSha256"]),
            "nativeValidatorSha256": gate.sha256_file(paths["v15NativeValidatorSha256"]),
            "nativeContractSha256": gate.sha256_file(paths["v15NativeContractSha256"]),
        }
        write_json(self.report, {
            "schema": gate.V15_SCHEMA, "status": "complete", "failed": False,
            "inputSetSha256": INPUT_SET, "provenance": provenance,
            "summary": {"streamingFiles": len(self.files), "parsed": len(self.files),
                        "failed": 0, "unsupported": 0, "gateFailures": 0},
            "layer3": {
                "nestedElementFraming": {
                    "nestedElementMarkerCounts": {"17": refs},
                    "nestedElementFramedCounts": {"17": refs},
                    "nestedElementByteCounts": {"17": counted}, "opaqueElementCount": 0,
                    "marker17Representation": "two-wrappers-to-opaque-counted-bytes",
                    "markerMeaning": "unresolved-not-a-proven-union-registry",
                },
                "marker17KeyDirectory": {
                    "status": "exact-structural-directory", "evidenceLevel": "structural-only",
                    "referenceCount": refs, "countedBytes": counted,
                    "ambiguousReferenceCount": sum(
                        row["keyStatus"] == "ambiguous" for item in self.files for row in item["rows"]),
                    "filesWithReferences": len(self.files), "targetOwnedBytes": 0,
                    "bodyStatus": "opaque", "runtimeSelectionStatus": "unresolved",
                    "files": self.files,
                },
            }, "failures": [],
        })

    def write_all(self) -> None:
        self.write_ledger()
        self.write_outer()
        self.write_report()

    def native(self) -> dict:
        return {
            "status": "validated", "validationFailures": [],
            "contractSha256": gate.sha256_file(ROOT / "scripts/game_data/streaming_marker17_native.json"),
            "profile": {
                "tag": 5, "tagByteOffset": 28, "headerSize": 64,
                "selectedSlot3Keys": [
                    {"selector": 6, "key": [9, 0, 0]},
                    {"selector": 9, "key": [255, 3, 0]},
                ],
                "countByteOffsets": [40, 44, 48, 52, 56, 60],
                "recordWidths": list(gate.TAG5_RECORD_WIDTHS),
                "fields": "opaque", "evidenceLevel": "structural-only",
            },
        }

    def refresh_clear(self, clear: bytes) -> None:
        self.clear = clear
        self.chunk.write_bytes(clear)
        for item in self.files:
            item["length"] = len(clear)
            item["packedSha256"] = gate.sha256_bytes(clear)
        self.write_all()

    def run(self, *, max_files=None):
        with mock.patch.object(gate, "validate_marker17_native_contract", return_value=self.native()), \
             mock.patch.object(gate.fmt, "_decode_compressed", side_effect=lambda data: data):
            return gate.sweep(repo_root=ROOT, report_path=self.report,
                              outer_summary_path=self.outer, ledger_path=self.ledger,
                              expected_input_set_sha256=INPUT_SET,
                              game_root=self.root / "Endfield_Data", max_files=max_files)


class GateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.fx = Fixture(Path(self.temporary.name))

    def tearDown(self):
        self.temporary.cleanup()

    def test_full_normal_is_publication_eligible_and_retains_parser_ranges(self):
        result = self.fx.run()
        self.assertEqual((result["status"], result["publicationEligible"]), ("complete", True))
        self.assertEqual(result["summary"]["referencesValidated"], 1)
        row = result["layer3"]["marker17Tag5Directory"]["files"][0]["rows"][0]
        self.assertEqual((row["family"], row["rootMarker"], row["selector"]), ("streaming", 2, 6))
        self.assertEqual(row["parsed"]["opaqueHeaderRanges"], [{"start": 46, "end": 74}, {"start": 76, "end": 86}])
        self.assertEqual([(a["start"], a["end"]) for a in row["parsed"]["arrays"]], [(110, 110)] * 6)

    def test_max_files_is_always_partial_and_not_publishable(self):
        result = self.fx.run(max_files=1)
        self.assertEqual((result["status"], result["publicationEligible"]), ("partial", False))

    def test_profile_excluded_reference_is_still_physically_revalidated(self):
        self.fx = Fixture(Path(self.temporary.name), key=0x05000000)
        result = self.fx.run()
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["summary"]["profileExcludedReferences"], 1)
        self.assertEqual(result["summary"]["targetReferences"], 0)

    def test_invalid_native_profile_clears_directory_before_body_scan(self):
        native = self.fx.native()
        native["profile"]["recordWidths"][-1] = 52
        with mock.patch.object(gate, "validate_marker17_native_contract", return_value=native), \
             mock.patch.object(gate.fmt, "_decode_compressed") as decoder:
            result = gate.sweep(repo_root=ROOT, report_path=self.fx.report,
                                outer_summary_path=self.fx.outer, ledger_path=self.fx.ledger,
                                expected_input_set_sha256=INPUT_SET,
                                game_root=self.fx.root / "Endfield_Data")
        decoder.assert_not_called()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["layer3"]["marker17Tag5Directory"]["files"], [])

    def test_stale_v15_source_hash_fails_closed(self):
        report = json.loads(self.fx.report.read_text())
        report["provenance"]["parserSha256"] = "0" * 64
        write_json(self.fx.report, report)
        result = self.fx.run()
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any(row.get("field") == "parserSha256" for row in result["failures"]))

    def test_negative_offset_is_rejected_before_seek_or_read(self):
        self.fx.files[0]["offset"] = -1
        self.fx.write_all()
        result = self.fx.run()
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any("nonnegative integer" in str(row["actual"]) for row in result["failures"]))

    def test_malformed_wrapper_offset_fails(self):
        self.fx.files[0]["rows"][0]["targetSlotOffset"] = 1
        self.fx.write_report()
        result = self.fx.run()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["layer3"]["marker17Tag5Directory"]["files"], [])

    def test_negative_length_is_rejected_before_decode(self):
        self.fx.files[0]["length"] = -1
        self.fx.write_all()
        with mock.patch.object(gate.fmt, "_decode_compressed") as decoder, \
             mock.patch.object(gate, "validate_marker17_native_contract", return_value=self.fx.native()):
            result = gate.sweep(repo_root=ROOT, report_path=self.fx.report,
                                outer_summary_path=self.fx.outer, ledger_path=self.fx.ledger,
                                expected_input_set_sha256=INPUT_SET, game_root=self.fx.root / "Endfield_Data")
        decoder.assert_not_called()
        self.assertTrue(result["failed"])
        self.assertTrue(any("length: expected nonnegative" in str(r["actual"]) for r in result["failures"]))

    def test_partial_cli_rejects_default_output_before_sweep(self):
        with mock.patch.object(sys, "argv", ["gate", "--input-set-sha256", INPUT_SET, "--max-files", "1"]), \
             mock.patch.object(gate, "sweep") as sweep, \
             mock.patch("sys.stderr"), self.assertRaises(SystemExit) as error:
            gate.main()
        self.assertEqual(error.exception.code, 2)
        sweep.assert_not_called()

    def test_directory_key_is_checked_against_decoded_bytes(self):
        changed = bytearray(self.fx.clear)
        struct.pack_into("<I", changed, 6, 0x09000001)
        self.fx.refresh_clear(bytes(changed))
        result = self.fx.run()
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any("expected directory key" in str(row["actual"]) for row in result["failures"]))

    def test_directory_marker_is_checked_against_decoded_bytes(self):
        changed = bytearray(self.fx.clear)
        changed[4] = 16
        self.fx.refresh_clear(bytes(changed))
        result = self.fx.run()
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any("expected directory marker" in str(row["actual"]) for row in result["failures"]))

    def test_unknown_target_tag_is_failure_not_exclusion(self):
        changed = bytearray(self.fx.clear)
        struct.pack_into("<h", changed, 74, 4)
        self.fx.refresh_clear(bytes(changed))
        result = self.fx.run()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["summary"]["profileExcludedReferences"], 0)

    def test_truncated_array_count_fails(self):
        changed = bytearray(self.fx.clear)
        struct.pack_into("<i", changed, 102, 1)
        self.fx.refresh_clear(bytes(changed))
        result = self.fx.run()
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any("width 56" in str(row["actual"]) for row in result["failures"]))

    def test_invalid_negative_key_is_not_masked(self):
        self.fx.files[0]["rows"][0]["key"] = -1
        self.fx.files[0]["rows"][0]["keyHex"] = "FFFFFFFF"
        self.fx.write_report()
        result = self.fx.run()
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any(row.get("field") == "key" for row in result["failures"]))

    def test_ambiguous_selected_key_fails(self):
        self.fx.files[0]["rows"][0]["keyStatus"] = "ambiguous"
        self.fx.write_report()
        result = self.fx.run()
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any(row.get("field") == "selectedKeyContext" for row in result["failures"]))

    def test_chunk_open_failure_counts_every_file_in_chunk(self):
        missing = (self.fx.root / "missing.chk").as_posix()
        first = self.fx.make_file("a", missing, key=self.fx.key)
        second = self.fx.make_file("b", missing, key=self.fx.key)
        self.fx.files = [first, second]
        self.fx.write_all()
        result = self.fx.run()
        self.assertEqual(result["summary"]["filesFailed"], 2)
        self.assertEqual(sum(row["stage"] == "chunk-open" for row in result["failures"]), 2)

    def test_outer_fingerprint_inventory_must_be_nonempty(self):
        outer = json.loads(self.fx.outer.read_text())
        outer["sourceFingerprints"] = []
        write_json(self.fx.outer, outer)
        result = self.fx.run()
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any(row.get("field") == "sourceFingerprints+buildFingerprints" for row in result["failures"]))

    def test_end_source_drift_clears_staged_directory(self):
        original = gate._snapshot_sources
        calls = 0

        def drifting(paths, failures, stage):
            nonlocal calls
            calls += 1
            value = original(paths, failures, stage)
            if calls == 2:
                value = dict(value)
                value["tag5CorpusGateSha256"] = "0" * 64
            return value

        with mock.patch.object(gate, "validate_marker17_native_contract", return_value=self.fx.native()), \
             mock.patch.object(gate.fmt, "_decode_compressed", side_effect=lambda data: data), \
             mock.patch.object(gate, "_snapshot_sources", side_effect=drifting):
            result = gate.sweep(repo_root=ROOT, report_path=self.fx.report,
                                outer_summary_path=self.fx.outer, ledger_path=self.fx.ledger,
                                expected_input_set_sha256=INPUT_SET,
                                game_root=self.fx.root / "Endfield_Data")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["layer3"]["marker17Tag5Directory"]["files"], [])


if __name__ == "__main__":
    unittest.main()
