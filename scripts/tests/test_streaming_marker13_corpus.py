from __future__ import annotations

import gzip
import hashlib
import io
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.game_data import streaming_marker13_corpus as gate
from scripts.tests.test_streaming import _data_root, _packed, _root


ROOT = Path(__file__).resolve().parents[2]
INPUT_SET = "A" * 64


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


class Fixture:
    def __init__(self, root: Path, *, key: int = 0xFF000000):
        self.root = root
        self.game_root = root / "Endfield_Data"
        (self.game_root / "il2cpp_data/Metadata").mkdir(parents=True)
        (root / "GameAssembly.dll").write_bytes(b"ga")
        (root / "UnityPlayer.dll").write_bytes(b"unity")
        (self.game_root / "il2cpp_data/Metadata/global-metadata.dat").write_bytes(b"metadata")
        self.key = key
        self.clear = self.make_clear(key)
        self.chunk = root / "chunk.chk"
        self.ledger = root / "ledger.jsonl.gz"
        self.outer = root / "outer.json"
        self.report = root / "v15.json"
        self.inventory = root / "inventory.jsonl.gz"
        self.fingerprint = root / "source.blc"
        self.fingerprint.write_bytes(b"outer source")
        self.primary = (self.game_root / "Persistent").as_posix()
        self.fallback = (self.game_root / "StreamingAssets").as_posix()
        self.certified_ranges = [(0, 32, "before"), (48, 64, "after")]
        self.occurrences = 1
        self.files = [self.make_file("one", 0)]
        self.write_all()

    @staticmethod
    def make_clear(key: int, *, trailing: bytes = b"") -> bytes:
        data = bytearray(64)
        data[0] = 2
        struct.pack_into("<I", data, 4, 9)
        struct.pack_into("<I", data, 8, key)
        data[12] = 13
        struct.pack_into("<I", data, 16, 16)
        struct.pack_into("<4I", data, 32, 10, 20, 30, 40)
        return bytes(data) + trailing

    def make_file(self, suffix: str, offset: int) -> dict:
        virtual_path = f"Data/Streaming/PC/test/{suffix}/Streaming/StreamingChunkData_0_0_0_0.bytes"
        return {
            "virtualPath": virtual_path, "physicalChunkPath": self.chunk.as_posix(),
            "physicalChunkSource": "primary", "metadataProvenance": "primary",
            "overlayState": "primary_only", "chunkFile": self.chunk.name,
            "offset": offset, "length": len(self.clear),
        }

    def directory_row(self, data: bytes) -> dict:
        key = struct.unpack_from("<I", data, 8)[0]
        return {
            "outerRowIndex": 0, "outerRowOffset": 0,
            "rootMarker": data[0], "rootMarkerOffset": 0,
            "rowSelectorU32": struct.unpack_from("<I", data, 4)[0],
            "rowSelectorLowByte": data[4], "rowSelectorOffset": 4,
            "nestedTableOffset": 4, "nestedElementCount": 1, "elementIndex": 0,
            "key": key, "keyHex": f"{key:08X}", "keyOffset": 8,
            "keyOccurrenceCountInTable": self.occurrences,
            "keyStatus": "unique" if self.occurrences == 1 else "ambiguous",
            "marker": data[12], "markerOffset": 12,
            "targetSlotOffset": 16, "targetStart": 32,
        }

    def parsed(self, family: str, data: bytes, **kwargs) -> dict:
        if family != "streaming":
            raise ValueError(f"unexpected family {family}")
        if kwargs.get("native_layout_validated") is not True:
            raise ValueError("native layout was not validated")
        if kwargs.get("include_certified_ranges") is not True:
            raise ValueError("certified ranges were not requested")
        if len(data) != 64:
            raise ValueError(f"root exact EOF: expected 64 bytes, actual {len(data)}")
        return {
            "encoding": "raw_flatbuffer", "decodedBytes": len(data),
            "decodedCertifiedRanges": list(self.certified_ranges),
            "anonymousParallelSubgraph": {
                "nestedElementMarkerCounts": {13: 1},
                "marker13KeyDirectory": {
                    "status": "exact-structural-reference-directory",
                    "rows": [self.directory_row(data)],
                }
            },
        }

    def native(self) -> dict:
        return {
            "status": "validated", "validationFailures": [],
            "absentSelectorContextWitness": dict(gate.EXPECTED_ABSENT_WITNESS),
            "contractSha256": gate.sha256_file(ROOT / "scripts/game_data/streaming_marker13_native.json"),
            "profile": {
                "family": "streaming", "rootMarker": 2, "rawSelector": 9,
                "key": [255, 0, 0], "packedKey": 0xFF000000, "marker": 13,
                "readWidth": 16, "dwordOffsets": [0, 4, 8, 12],
                "allocatedSizeStatus": "not-proven-by-native",
                "markerBinding": "external authenticated same-element corpus join; native reader does not inspect marker13",
                "extentStatus": "read-window-only; record extent and EOF unresolved",
                "evidenceLevel": "structural-only",
            },
        }

    def ledger_rows(self) -> list[dict]:
        rows = [{
            "recordType": "audit_header", "schemaVersion": 1,
            "inputSetSha256": INPUT_SET, "primaryAssets": self.primary,
            "fallbackAssets": self.fallback,
        }]
        chunk_bytes = self.chunk.read_bytes()
        for item in self.files:
            packed = chunk_bytes[item["offset"]:item["offset"] + item["length"]]
            rows.append({
                "recordType": "file", "blockTypeValue": 15,
                **item, "status": "verified", "boundaryStatus": "boundary_verified",
                "inputSetSha256": INPUT_SET, "encrypted": False,
                "actualBytesRead": item["length"],
                "recomputedFileDataMd5": hashlib.md5(
                    packed, usedforsecurity=False).hexdigest().upper(),
            })
        return rows

    def write_ledger(self) -> None:
        with gzip.open(self.ledger, "wt", encoding="utf-8") as stream:
            for row in self.ledger_rows():
                stream.write(json.dumps(row) + "\n")

    def write_outer(self) -> None:
        write_json(self.outer, {
            "inputSetSha256": INPUT_SET, "primaryAssets": self.primary,
            "fallbackAssets": self.fallback, "summary": {"fullAuditPassed": True},
            "sourceFingerprints": [{
                "path": self.fingerprint.as_posix(), "length": self.fingerprint.stat().st_size,
                "sha256": gate.sha256_file(self.fingerprint),
            }],
            "buildFingerprints": [],
            "publication": {"ledgerSha256": gate.sha256_file(self.ledger)},
        })

    def write_report(self) -> None:
        paths = gate.source_paths(ROOT)
        source_hashes = {name: gate.sha256_file(path) for name, path in paths.items()}
        chunk_bytes = self.chunk.read_bytes()
        identities = []
        for item in self.files:
            packed = chunk_bytes[item["offset"]:item["offset"] + item["length"]]
            packed_md5 = hashlib.md5(packed, usedforsecurity=False).hexdigest().upper()
            identities.append("\0".join((
                item["virtualPath"], item["physicalChunkSource"], item["chunkFile"],
                str(item["offset"]), str(item["length"]), packed_md5,
                gate.sha256_bytes(packed),
            )))
        write_json(self.report, {
            "schema": gate.ROOT_SCHEMA, "status": "complete", "failed": False,
            "inputSetSha256": INPUT_SET,
            "provenance": {
                "inputSetSha256": INPUT_SET,
                "outerLedgerSha256": gate.sha256_file(self.ledger),
                "primaryAssets": self.primary, "fallbackAssets": self.fallback,
                "parserSha256": source_hashes["rootParserSha256"],
                "corpusGateSha256": source_hashes["rootCorpusGateSha256"],
                "nativeValidatorSha256": source_hashes["rootNativeValidatorSha256"],
                "nativeContractSha256": source_hashes["rootNativeContractSha256"],
            },
            "summary": {"streamingFiles": len(self.files), "parsed": len(self.files),
                        "failed": 0, "unsupported": 0, "gateFailures": 0},
            "layer1": {"logicalIdentitySetSha256": gate.sha256_bytes(
                "\n".join(sorted(identities)).encode("utf-8"))},
            "layer3": {"nestedElementFraming": {"nestedElementMarkerCounts": {"13": len(self.files)}}},
            "failures": [],
        })

    def write_all(self) -> None:
        self.chunk.write_bytes(b"".join(self.clear for _ in self.files))
        for index, item in enumerate(self.files):
            item["offset"] = index * len(self.clear)
            item["length"] = len(self.clear)
        self.write_ledger()
        self.write_outer()
        self.write_report()

    def run(self, **kwargs) -> dict:
        inventory_path = kwargs.pop("inventory_path", None)
        with mock.patch.object(gate, "validate_marker13_native_contract", return_value=self.native()), \
             mock.patch.object(gate.fmt, "parse_streaming_file", side_effect=self.parsed), \
             mock.patch.object(gate, "index_ordered_pairs", return_value={
                 row["virtualPath"]: None for row in self.files
                 if gate.root_corpus._family(row["virtualPath"]) != "info"
             }), \
             mock.patch.object(gate, "bind_current_pair", side_effect=lambda **args: {
                 "source": args["identity"]["virtualPath"],
                 "decodedSha256": gate.sha256_bytes(args["decoded"]),
             }):
            return gate.sweep(
                repo_root=ROOT, root_report_path=self.report,
                outer_summary_path=self.outer, ledger_path=self.ledger,
                expected_input_set_sha256=INPUT_SET, game_root=self.game_root,
                inventory_path=inventory_path, **kwargs,
            )


class CorpusGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.fx = Fixture(Path(self.temporary.name))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_normal_full_gate_replays_gap_and_records_opaque_complement(self):
        result = self.fx.run()
        self.assertEqual((result["status"], result["publicationEligible"]), ("complete", True))
        self.assertEqual((result["summary"]["exactGapReferences"],
                          result["summary"]["uniqueReadWindowBytes"]), (1, 16))
        file_row = result["_inventoryRows"][1]
        self.assertEqual(file_row["wholeLogicalFileStatus"],
                         "partial-with-explicit-opaque-complement")
        coverage = file_row["rangeCoverage"]
        self.assertEqual(coverage["opaqueComplement"], [])
        self.assertEqual(coverage["selectedReadWindowRanges"], [
            {"start": 32, "end": 48, "kind": "marker13-native-read-window16"}
        ])
        self.assertEqual(file_row["marker13"]["rows"][0]["anonymousScalar32Projection"][3]["anonymousU32"], 40)

    def test_gap18_residual_remains_in_whole_file_opaque_complement(self):
        self.fx.certified_ranges = [(0, 32, "before"), (50, 64, "vtable")]
        changed = bytearray(self.fx.clear)
        changed[48:50] = b"\xA5\x5A"
        self.fx.clear = bytes(changed)
        self.fx.write_all()
        result = self.fx.run()
        self.assertTrue(result["publicationEligible"])
        self.assertEqual(result["summary"]["uniqueReadWindowBytes"], 16)
        coverage = result["_inventoryRows"][1]["rangeCoverage"]
        self.assertEqual(coverage["opaqueComplement"], [{"start": 48, "end": 50, "length": 2}])

    def test_unselected_key_stays_unsupported_opaque(self):
        self.fx.key = 0xFE000000
        self.fx.clear = self.fx.make_clear(self.fx.key)
        self.fx.write_all()
        result = self.fx.run()
        self.assertFalse(result["failed"])
        self.assertEqual((result["summary"]["exactGapReferences"],
                          result["summary"]["unsupportedOpaqueReferences"]), (0, 1))
        self.assertEqual(result["_inventoryRows"][1]["rangeCoverage"]["opaqueComplement"], [
            {"start": 32, "end": 48, "length": 16}
        ])

    def test_unsupported_family_retains_authenticated_reference_offsets(self):
        row = self.fx.directory_row(self.fx.clear)
        result = gate.unsupported_rows([row], "init")
        for field, value in row.items():
            self.assertEqual(result["rows"][0][field], value)
        self.assertEqual(result["partitionedBytes"], 0)

    def test_selected_ambiguous_key_fails_closed_and_clears_rows(self):
        self.fx.occurrences = 2
        result = self.fx.run()
        self.assertTrue(result["failed"])
        self.assertEqual(result["_inventoryRows"], [])
        self.assertIn("ambiguity", result["failures"][0]["actual"])

    def test_selected_wrong_gap_boundary_fails_closed(self):
        self.fx.certified_ranges = [(0, 32, "before"), (49, 64, "after")]
        result = self.fx.run()
        self.assertTrue(result["failed"])
        self.assertEqual(result["summary"]["filesFailed"], 1)
        self.assertIn("following certified start in [48, 50], actual 49", result["failures"][0]["actual"])

    def test_trailing_whole_logical_file_is_rejected_by_root_eof_gate(self):
        self.fx.clear = self.fx.make_clear(self.fx.key, trailing=b"X")
        self.fx.certified_ranges = [(0, 32, "before"), (48, 64, "after")]
        self.fx.write_all()
        result = self.fx.run()
        self.assertTrue(result["failed"])
        self.assertIn("root exact EOF", result["failures"][0]["actual"])

    def test_truncated_whole_logical_file_is_rejected_by_root_eof_gate(self):
        self.fx.clear = self.fx.make_clear(self.fx.key)[:-1]
        self.fx.write_all()
        result = self.fx.run()
        self.assertTrue(result["failed"])
        self.assertIn("root exact EOF", result["failures"][0]["actual"])

    def test_malformed_target_offset_fails_closed(self):
        data = bytearray(self.fx.clear)
        struct.pack_into("<I", data, 16, 0xFFFFFFFF)
        self.fx.clear = bytes(data)
        self.fx.write_all()
        result = self.fx.run()
        self.assertTrue(result["failed"])
        self.assertIn("positive in-bounds uoffset", result["failures"][0]["actual"])

    def test_malformed_key_occurrence_count_fails_closed(self):
        self.fx.occurrences = 0
        result = self.fx.run()
        self.assertTrue(result["failed"])
        self.assertIn("expected positive integer", result["failures"][0]["actual"])

    def test_cross_subgraph_certified_overlap_fails_closed(self):
        self.fx.certified_ranges = [(0, 32, "before"), (24, 32, "overlap"),
                                    (48, 64, "after")]
        result = self.fx.run()
        self.assertTrue(result["failed"])
        self.assertIn("expected no non-identical overlap", result["failures"][0]["actual"])

    def test_packed_md5_mismatch_fails_before_parse(self):
        rows = self.fx.ledger_rows()
        rows[1]["recomputedFileDataMd5"] = "0" * 32
        with gzip.open(self.fx.ledger, "wt", encoding="utf-8") as stream:
            for row in rows:
                stream.write(json.dumps(row) + "\n")
        self.fx.write_outer()
        self.fx.write_report()
        with mock.patch.object(gate, "validate_marker13_native_contract", return_value=self.fx.native()), \
             mock.patch.object(gate.fmt, "parse_streaming_file") as parser, \
             mock.patch.object(gate, "index_ordered_pairs", return_value={self.fx.files[0]["virtualPath"]: None}):
            result = gate.sweep(
                repo_root=ROOT, root_report_path=self.fx.report,
                outer_summary_path=self.fx.outer, ledger_path=self.fx.ledger,
                expected_input_set_sha256=INPUT_SET, game_root=self.fx.game_root,
            )
        self.assertTrue(result["failed"])
        parser.assert_not_called()
        self.assertIn("packed MD5", result["failures"][0]["actual"])

    def test_wrong_native_profile_blocks_all_file_reads(self):
        native = self.fx.native()
        native["profile"]["readWidth"] = 20
        with mock.patch.object(gate, "validate_marker13_native_contract", return_value=native), \
             mock.patch.object(gate.fmt, "parse_streaming_file") as parser:
            result = gate.sweep(
                repo_root=ROOT, root_report_path=self.fx.report,
                outer_summary_path=self.fx.outer, ledger_path=self.fx.ledger,
                expected_input_set_sha256=INPUT_SET, game_root=self.fx.game_root,
            )
        self.assertTrue(result["failed"])
        parser.assert_not_called()
        self.assertEqual(result["failures"][0]["field"], "profile")

    def test_partial_run_is_never_publication_eligible(self):
        result = self.fx.run(max_files=1)
        self.assertEqual((result["status"], result["publicationEligible"]), ("partial", False))

    def test_failed_run_does_not_publish_inventory(self):
        self.fx.occurrences = 2
        result = self.fx.run(inventory_path=self.fx.inventory)
        self.assertTrue(result["failed"])
        self.assertFalse(self.fx.inventory.exists())

    def test_failed_run_preserves_previous_inventory(self):
        self.fx.inventory.write_bytes(b"previous authenticated inventory")
        self.fx.occurrences = 2
        result = self.fx.run(inventory_path=self.fx.inventory)
        self.assertTrue(result["failed"])
        self.assertIsNone(result["layer3"]["inventory"])
        self.assertEqual(self.fx.inventory.read_bytes(), b"previous authenticated inventory")

    def test_direct_sweep_rejects_input_as_inventory_without_modification(self):
        for path in (self.fx.ledger, self.fx.report, self.fx.outer, self.fx.chunk,
                     self.fx.game_root.parent / "UnityPlayer.dll"):
            with self.subTest(path=path):
                before = path.read_bytes()
                result = self.fx.run(inventory_path=path)
                self.assertTrue(result["failed"])
                self.assertFalse(result["publicationEligible"])
                self.assertIsNone(result["layer3"]["inventory"])
                self.assertEqual(path.read_bytes(), before)
                self.assertTrue(any(item["stage"] == "output-path-isolation" for item in result["failures"]))

    def test_full_cli_rejects_ledger_output_before_sweep(self):
        arguments = ["streaming_marker13_corpus", "--input-set-sha256", INPUT_SET,
                     "--root-report", str(self.fx.report), "--outer-summary", str(self.fx.outer),
                     "--outer-ledger", str(self.fx.ledger), "--game-root", str(self.fx.game_root),
                     "--output-inventory", str(self.fx.ledger)]
        before = self.fx.ledger.read_bytes()
        with mock.patch.object(sys, "argv", arguments), \
                mock.patch.object(sys, "stderr", io.StringIO()) as stderr, \
                mock.patch.object(gate, "sweep") as sweep:
            with self.assertRaises(SystemExit) as raised:
                gate.main()
            self.assertEqual(raised.exception.code, 2)
            self.assertIn("outerLedger", stderr.getvalue())
            sweep.assert_not_called()
        self.assertEqual(self.fx.ledger.read_bytes(), before)

    def test_first_file_failure_is_emitted_before_terminal_summary(self):
        self.fx.occurrences = 2
        updates = []
        result = self.fx.run(progress=updates.append)
        self.assertTrue(result["failed"])
        self.assertEqual(updates[0]["firstFailure"]["source"], self.fx.files[0]["virtualPath"])
        self.assertIn("ambiguity", updates[0]["firstFailure"]["actual"])

    def test_partial_cli_rejects_implicit_or_report_outputs_before_sweep(self):
        base = ["streaming_marker13_corpus", "--input-set-sha256", INPUT_SET, "--max-files", "1"]
        protected = ["--output-json", str(ROOT / "reports/probe.json"),
                     "--output-md", str(ROOT / "tmp/probe.md"),
                     "--output-inventory", str(ROOT / "tmp/probe.gz")]
        for extra in ([], protected):
            with self.subTest(extra=extra), mock.patch.object(sys, "argv", base + extra), \
                    mock.patch.object(sys, "stderr", io.StringIO()), \
                    mock.patch.object(gate, "sweep") as sweep:
                with self.assertRaises(SystemExit) as raised:
                    gate.main()
                self.assertEqual(raised.exception.code, 2)
                sweep.assert_not_called()

    def test_success_inventory_is_deterministic_gzip_jsonl(self):
        first = self.fx.run(inventory_path=self.fx.inventory)
        first_gzip = gate.sha256_file(self.fx.inventory)
        first_content = first["layer3"]["inventory"]["contentSha256"]
        second = self.fx.run(inventory_path=self.fx.inventory)
        self.assertEqual(gate.sha256_file(self.fx.inventory), first_gzip)
        self.assertEqual(second["layer3"]["inventory"]["contentSha256"], first_content)
        with gzip.open(self.fx.inventory, "rt", encoding="utf-8") as stream:
            rows = [json.loads(line) for line in stream]
        self.assertEqual(rows[0]["publicationStatus"], "staged-until-terminal-summary-gate")
        self.assertEqual(rows[1]["recordType"], "file")
        self.assertEqual(rows[-1]["recordType"], "inventory_terminal")
        self.assertTrue(rows[-1]["publicationEligible"])
        self.assertEqual(rows[-1]["counts"]["filesSucceeded"], 1)

    def test_source_end_drift_fails_closed(self):
        original = gate.snapshot_sources

        def drift(paths, failures, stage):
            result = original(paths, failures, stage)
            if stage == "source-end":
                result = dict(result)
                result["marker13CorpusGateSha256"] = "0" * 64
            return result

        with mock.patch.object(gate, "snapshot_sources", side_effect=drift):
            result = self.fx.run()
        self.assertTrue(result["failed"])
        self.assertEqual(result["_inventoryRows"], [])
        self.assertEqual(result["failures"][-1]["field"], "sourceHashes")

    def test_actual_root_parser_normal_and_negative_eof_composition(self):
        for suffix, truncated in ((b"", False), (b"X", False), (b"", True)):
            with self.subTest(suffix=suffix, truncated=truncated):
                clear = _data_root()
                self.fx.clear = _packed(clear[:-1] if truncated else clear + suffix)
                self.fx.write_all()
                document = json.loads(self.fx.report.read_text())
                document["layer3"]["nestedElementFraming"]["nestedElementMarkerCounts"]["13"] = 0
                write_json(self.fx.report, document)
                with mock.patch.object(gate, "validate_marker13_native_contract", return_value=self.fx.native()), \
                     mock.patch.object(gate, "index_ordered_pairs", return_value={self.fx.files[0]["virtualPath"]: None}), \
                     mock.patch.object(gate, "bind_current_pair", side_effect=lambda **args: {
                         "source": args["identity"]["virtualPath"],
                         "decodedSha256": gate.sha256_bytes(args["decoded"]),
                     }):
                    result = gate.sweep(
                        repo_root=ROOT, root_report_path=self.fx.report,
                        outer_summary_path=self.fx.outer, ledger_path=self.fx.ledger,
                        expected_input_set_sha256=INPUT_SET, game_root=self.fx.game_root,
                    )
                self.assertEqual(result["failed"], bool(suffix) or truncated)
                if suffix or truncated:
                    self.assertEqual(result["summary"]["filesFailed"], 1)
                    self.assertEqual(result["_inventoryRows"], [])
                else:
                    self.assertEqual(result["summary"]["filesSucceeded"], 1)
                    self.assertEqual(result["summary"]["marker13References"], 0)

    def test_root_marker13_total_mismatch_is_not_complete_coverage(self):
        document = json.loads(self.fx.report.read_text())
        document["layer3"]["nestedElementFraming"]["nestedElementMarkerCounts"]["13"] = 2
        write_json(self.fx.report, document)
        result = self.fx.run()
        self.assertTrue(result["failed"])
        self.assertEqual(result["_inventoryRows"], [])
        self.assertEqual(result["failures"][0]["field"], "marker13ReferenceCount")

    def test_actual_two_file_pair_composition_and_forged_first_root(self):
        self.fx.clear = _packed(_data_root())
        streaming = self.fx.make_file("pair", 0)
        init = {**streaming, "virtualPath": streaming["virtualPath"].replace("/StreamingChunkData_", "/InitChunkData_")}
        self.fx.files = [init, streaming]
        self.fx.write_all()
        document = json.loads(self.fx.report.read_text())
        records = []
        for row in self.fx.files:
            parsed = gate.fmt.parse_streaming_file(gate.root_corpus._family(row["virtualPath"]), self.fx.clear,
                                                   native_layout_validated=True, include_certified_ranges=True)
            records.append({**row, "packedSha256": gate.sha256_bytes(self.fx.clear),
                            "witness": parsed["anonymousParallelSubgraph"]["orderedRootWitness"]})
        document["layer3"]["pairedRootIdentities"] = gate.root_corpus._join_root_witnesses(records)
        document["layer3"]["nestedElementFraming"]["nestedElementMarkerCounts"]["13"] = 0
        for mutation in (None, "firstMarkerDigest", "firstPackedSha"):
            with self.subTest(mutation=mutation):
                changed = json.loads(json.dumps(document))
                first = changed["layer3"]["pairedRootIdentities"]["pairs"][0]["init"]
                if mutation == "firstMarkerDigest":
                    first["witness"]["field4VectorSha256"] = "F" * 64
                elif mutation == "firstPackedSha":
                    first["packedSha256"] = "F" * 64
                write_json(self.fx.report, changed)
                with mock.patch.object(gate, "validate_marker13_native_contract", return_value=self.fx.native()):
                    result = gate.sweep(
                        repo_root=ROOT, root_report_path=self.fx.report, outer_summary_path=self.fx.outer,
                        ledger_path=self.fx.ledger, expected_input_set_sha256=INPUT_SET,
                        game_root=self.fx.game_root,
                    )
                self.assertEqual(result["failed"], mutation is not None, result["failures"])
                if mutation is None:
                    self.assertTrue(result["publicationEligible"])
                    self.assertEqual(result["summary"]["filesSucceeded"], 2)
                else:
                    self.assertEqual(result["_inventoryRows"], [])

    def test_actual_info_eof_graph_is_not_mislabeled_opaque(self):
        self.fx.clear = _root("info")
        self.fx.files[0]["virtualPath"] = "Data/Streaming/PC/test/Streaming/StreamingChunkInfo.bytes"
        self.fx.write_all()
        document = json.loads(self.fx.report.read_text())
        document["layer3"]["nestedElementFraming"]["nestedElementMarkerCounts"]["13"] = 0
        document["layer3"]["pairedRootIdentities"] = {
            "status": "exact-ordered-witness-matches", "pairs": [],
            "candidatePairCount": 0, "matchedPairCount": 0, "mismatchedPairCount": 0,
            "unpairedFileCount": 0, "unpairedFiles": [],
        }
        write_json(self.fx.report, document)
        with mock.patch.object(gate, "validate_marker13_native_contract", return_value=self.fx.native()):
            result = gate.sweep(
                repo_root=ROOT, root_report_path=self.fx.report,
                outer_summary_path=self.fx.outer, ledger_path=self.fx.ledger,
                expected_input_set_sha256=INPUT_SET, game_root=self.fx.game_root,
            )
        self.assertFalse(result["failed"], result["failures"])
        row = result["_inventoryRows"][1]
        self.assertEqual(row["wholeLogicalFileStatus"], "exact-anonymous-eof")
        self.assertEqual(row["rangeCoverage"]["opaqueBytes"], 0)
        self.assertEqual(row["rangeCoverage"]["unionBytes"], len(self.fx.clear))

    def test_native_input_end_drift_fails_closed(self):
        original = gate.snapshot_native_inputs
        calls = 0

        def drift(game_root, failures, stage):
            nonlocal calls
            result = original(game_root, failures, stage)
            calls += 1
            if calls == 2:
                result = json.loads(json.dumps(result))
                result["UnityPlayer.dll"]["sha256"] = "0" * 64
            return result

        with mock.patch.object(gate, "snapshot_native_inputs", side_effect=drift):
            result = self.fx.run()
        self.assertTrue(result["failed"])
        self.assertEqual(result["_inventoryRows"], [])
        self.assertEqual(result["failures"][-1]["field"], "nativeInputHashes")


if __name__ == "__main__":
    unittest.main()
