from __future__ import annotations

import base64
import gzip
import hashlib
import json
import os
import struct
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.game_data.memorypack import skill_corpus as gate


def _payload() -> bytes:
    # Prefix consumes [0,10), byte 10 stays opaque, terminal consumes [11,EOF).
    return bytes([48, 2]) + struct.pack("<II", 0, 0) + b"\x7f\x00" + struct.pack("<III", 0, 0, 0) + b"\x01"


def _ledger_row(path: Path, data: bytes, *, virtual_path: str = "Data/Json/SkillData/fixture.json") -> dict:
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


def _stream_row(data: bytes, *, path: str = "Data/Json/SkillData/fixture.json") -> dict:
    return {
        "blockType": "JsonData",
        "blockTypeValue": 19,
        "fileName": path,
        "length": len(data),
        "dataBase64": base64.b64encode(data).decode("ascii"),
    }


class SkillDataCurrentCorpusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data = _payload()
        self.chunk = self.root / "fixture.chk"
        self.chunk.write_bytes(self.data)
        self.row = _ledger_row(self.chunk, self.data)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_join_normal_retains_disjoint_ranges_and_opaque_gap(self) -> None:
        rows, statuses, coverage = gate._join_and_frame(
            [self.row], [_stream_row(self.data)], stderr="Streamed 1 files\n"
        )
        self.assertEqual({"unique-exact-terminal-shape": 1}, statuses)
        self.assertEqual({"unique-disjoint-independent-ranges": 1}, coverage)
        item = rows[0]
        self.assertEqual({"start": 0, "end": 10, "endExclusive": True}, item["candidateCoverage"][0]["prefixCertifiedRange"])
        self.assertEqual({"start": 10, "end": 11, "length": 1}, item["candidateCoverage"][0]["opaqueGap"])
        self.assertFalse(item["wholeSchemaExact"])
        self.assertEqual(item["boundaryClass"], "structural-prefix")
        self.assertEqual(item["inputSetSha256"], "A" * 64)
        self.assertEqual(item["boundaryContext"]["logicalFileIdentity"], item["virtualPath"])
        self.assertEqual(item["boundaryContext"]["logicalSha256"], item["logicalSha256"])
        self.assertEqual(item["boundaryContext"]["parserCursor"], 10)
        self.assertEqual(item["boundaryContext"]["hardLimit"], len(self.data))
        candidate = item["framing"]["candidates"][0]
        self.assertEqual(candidate["boundaryClass"], "structural-prefix")
        self.assertEqual(candidate["boundaryContext"]["startOffset"], 11)
        self.assertEqual(candidate["boundaryContext"]["parserCursor"], len(self.data))
        self.assertEqual(candidate["boundaryContext"]["hardLimit"], len(self.data))
        self.assertEqual(candidate["byteRanges"][0]["start"], 11)
        self.assertEqual(item["byteRanges"][-1]["end"], 10)
        boundary = gate._boundary_evidence_summary(rows)
        self.assertEqual(boundary["exactClosedRecords"], 0)
        self.assertEqual(boundary["filesWithStructuralPrefix"], 1)
        self.assertEqual(boundary["opaqueBytesByCandidate"], 1)
        self.assertEqual(boundary["opaqueBytesAtFileLevel"], 1)

    def test_one_byte_terminal_collision_stays_ambiguous_with_bound_candidate_cursors(self) -> None:
        self.data = bytes([48, 2]) + struct.pack("<II", 0, 0) + b"\x00\x01" + struct.pack("<III", 0, 0, 0) + b"\x00"
        self.chunk.write_bytes(self.data)
        self.row = _ledger_row(self.chunk, self.data)
        rows, statuses, coverage = gate._join_and_frame(
            [self.row], [_stream_row(self.data)], stderr="Streamed 1 files\n"
        )
        self.assertEqual({"ambiguous-disjoint-independent-ranges": 1}, coverage)
        item = rows[0]
        self.assertEqual(item["boundaryClass"], "ambiguous")
        candidates = item["framing"]["candidates"]
        self.assertEqual([int(row["startOffset"], 0) for row in candidates], [10, 11])
        for candidate in candidates:
            self.assertEqual(candidate["boundaryClass"], "ambiguous")
            self.assertEqual(candidate["parserCursor"], len(self.data))
            self.assertEqual(candidate["hardLimit"], len(self.data))
            self.assertEqual(candidate["boundaryContext"]["inputSetSha256"], "A" * 64)
            self.assertEqual(candidate["boundaryContext"]["logicalFileIdentity"], item["virtualPath"])
            self.assertEqual(candidate["boundaryContext"]["logicalSha256"], item["logicalSha256"])
        self.assertEqual(item["opaqueByteRanges"], [])
        boundary = gate._boundary_evidence_summary(rows)
        self.assertEqual(boundary["exactClosedRecords"], 0)
        self.assertEqual(boundary["filesWithStructuralPrefix"], 1)
        self.assertEqual(boundary["ambiguousFiles"], 1)
        self.assertEqual(boundary["unsupportedFiles"], 0)
        self.assertEqual(boundary["opaqueBytesByCandidate"], 1)
        self.assertEqual(boundary["opaqueBytesAtFileLevel"], 0)

    def test_overlap_is_reported_unsupported_not_filtered(self) -> None:
        fake_prefix = {"cursorOffset": "0xa"}
        fake_terminal = {
            "status": "unique-exact-terminal-shape",
            "candidateCount": 1,
            "candidates": [{"startOffset": "0x9"}],
        }
        with mock.patch.object(gate, "frame_skill_common_prefix", return_value=fake_prefix), mock.patch.object(
            gate, "frame_skill_memorypack", return_value=fake_terminal
        ):
            rows, _statuses, coverage = gate._join_and_frame(
                [self.row], [_stream_row(self.data)], stderr="Streamed 1 files\n"
            )
        self.assertEqual({"unsupported-overlapping-independent-ranges": 1}, coverage)
        self.assertEqual(1, len(rows[0]["candidateCoverage"]))
        self.assertTrue(rows[0]["candidateCoverage"][0]["rangesOverlap"])

    def test_duplicate_missing_and_extra_stream_identities_fail(self) -> None:
        with self.assertRaisesRegex(gate.CensusGateError, "duplicate-stream-identity"):
            gate._join_and_frame(self.row and [self.row], [_stream_row(self.data), _stream_row(self.data)], stderr="Streamed 2 files\n")
        with self.assertRaisesRegex(gate.CensusGateError, "stream-missing-identities"):
            gate._join_and_frame([self.row], [], stderr="Streamed 0 files\n")
        with self.assertRaisesRegex(gate.CensusGateError, "unexpected-stream-identity"):
            gate._join_and_frame([self.row], [_stream_row(self.data, path="Data/Json/SkillData/extra.json")], stderr="Streamed 1 files\n")

    def test_stream_length_md5_type_and_base64_fail_closed(self) -> None:
        cases = []
        row = _stream_row(self.data); row["length"] += 1; cases.append((row, "stream-length-mismatch"))
        row = _stream_row(self.data[:-1] + b"\x00"); cases.append((row, "stream-ledger-md5-mismatch"))
        row = _stream_row(self.data); row["blockTypeValue"] = 18; cases.append((row, "stream-block-mismatch"))
        row = _stream_row(self.data); row["dataBase64"] = "not*base64"; cases.append((row, "stream-base64-invalid"))
        for stream, code in cases:
            with self.subTest(code=code), self.assertRaisesRegex(gate.CensusGateError, code):
                gate._join_and_frame([self.row], [stream], stderr="Streamed 1 files\n")

    def test_terminal_stream_count_is_required(self) -> None:
        with self.assertRaisesRegex(gate.CensusGateError, "stream-terminal-count-mismatch"):
            gate._join_and_frame([self.row], [_stream_row(self.data)], stderr="")

    def test_one_framing_failure_keeps_complete_stream_denominator(self) -> None:
        bad_data = bytes([47]) + self.data[1:]
        bad_row = dict(self.row)
        bad_row["virtualPath"] = bad_row["fileName"] = "Data/Json/SkillData/bad.json"
        bad_row["recomputedFileDataMd5"] = hashlib.md5(bad_data).hexdigest().upper()
        rows, _statuses, coverage = gate._join_and_frame(
            [self.row, bad_row],
            [_stream_row(self.data), _stream_row(bad_data, path=bad_row["virtualPath"])],
            stderr="Streamed 2 files\n",
        )
        self.assertEqual(2, len(rows))
        self.assertEqual(1, coverage["failed-framing"])
        failed = next(row for row in rows if row["coverageStatus"] == "failed-framing")
        self.assertEqual("skill-framer-failed", failed["framingFailure"]["code"])

    def test_negative_bool_and_out_of_bounds_ranges_fail_before_read(self) -> None:
        for field, value, code in (
            ("offset", -1, "invalid-integer"),
            ("length", -1, "invalid-integer"),
            ("length", len(self.data) + 1, "skill-ledger-range-out-of-bounds"),
            ("actualBytesRead", True, "invalid-integer"),
        ):
            row = dict(self.row); row[field] = value
            if field == "length" and value > 0:
                row["actualBytesRead"] = value
            with self.subTest(field=field, value=value), self.assertRaisesRegex(gate.CensusGateError, code):
                gate._skill_rows([row], expected_input="A" * 64)

    def test_duplicate_and_malformed_skill_paths_fail(self) -> None:
        with self.assertRaisesRegex(gate.CensusGateError, "duplicate-skill-identity"):
            gate._skill_rows([self.row, dict(self.row)], expected_input="A" * 64)
        row = dict(self.row); row["virtualPath"] = "Data/Json/SkillData/nested/bad.json"
        with self.assertRaisesRegex(gate.CensusGateError, "unsupported-skill-path"):
            gate._skill_rows([row], expected_input="A" * 64)

    def test_output_overlap_and_hardlink_fail_before_publication(self) -> None:
        with self.assertRaisesRegex(gate.CensusGateError, "output-overlaps-input"):
            gate._guard_output_path(self.chunk, [self.chunk])
        alias = self.root / "alias.json"
        try:
            os.link(self.chunk, alias)
        except OSError:
            self.skipTest("hardlinks unavailable")
        with self.assertRaisesRegex(gate.CensusGateError, "output-hardlinks-input"):
            gate._guard_output_path(alias, [self.chunk])

    def test_chunk_raw_hash_drift_fails(self) -> None:
        before = gate._chunk_fingerprints([self.row])
        self.chunk.write_bytes(self.data + b"drift")
        after = gate._chunk_fingerprints([self.row])
        self.assertNotEqual(before, after)
        self.assertNotEqual(before[0]["rawMd5"], after[0]["rawMd5"])

    def test_expected_input_set_is_mandatory_and_cannot_be_rebound(self) -> None:
        with self.assertRaisesRegex(gate.CensusGateError, "invalid-expected-input-set"):
            gate._read_outer_and_ledger(self.root / "old-census.json", self.root / "old-ledger.gz", expected_input_set_sha256="")
        self.assertNotIn("census_path", gate.build_current_census.__annotations__)

    def _write_full_fixture(self) -> tuple[Path, Path, Path]:
        primary = self.root / "Persistent"
        fallback = self.root / "StreamingAssets"
        blc = primary / "VFS/775A31D1/775A31D1.blc"
        blc.parent.mkdir(parents=True, exist_ok=True)
        blc.write_bytes(b"metadata")
        chunk = blc.parent / (hashlib.md5(self.data).hexdigest().upper() + ".chk")
        chunk.write_bytes(self.data)
        self.row = _ledger_row(chunk, self.data)
        self.row["physicalChunkRoot"] = str(primary)
        self.row["chunkFile"] = chunk.name
        cli = self.root / "AnimeStudio.CLI.exe"
        cli.write_bytes(b"fixture cli")
        (self.root / "AnimeStudio.CLI.dll").write_bytes(b"fixture managed cli")
        source_fp = {"role": "primary", **gate._fingerprint(blc)}
        build_fp = gate._fingerprint(cli)
        ledger = self.root / "outer.jsonl.gz"
        header = {
            "recordType": "audit_header", "schemaVersion": 1, "inputSetSha256": "A" * 64,
            "primaryAssets": str(primary), "fallbackAssets": str(fallback),
            "sourceFingerprints": [source_fp], "buildFingerprints": [build_fp],
        }
        with gzip.open(ledger, "wt", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(header) + "\n")
            handle.write(json.dumps(self.row) + "\n")
        outer = self.root / "outer.json"
        outer.write_text(json.dumps({
            "format": "animestudio-vfs-boundary-audit", "schemaVersion": 1,
            "primaryAssets": str(primary), "fallbackAssets": str(fallback),
            "inputSetSha256": "A" * 64, "sourceFingerprints": [source_fp],
            "buildFingerprints": [build_fp], "summary": {"fullAuditPassed": True, "ledgerFileCount": 1},
            "publication": {"ledgerSha256": gate._sha256_file(ledger)},
        }), encoding="utf-8")
        return outer, ledger, cli

    def test_full_fixture_binds_outer_ledger_stream_and_logical_hash(self) -> None:
        outer, ledger, cli = self._write_full_fixture()
        output = self.root / "result.json"
        with mock.patch.object(gate, "_read_stream_rows", return_value=([_stream_row(self.data)], "Streamed 1 files\n")):
            result = gate.build_current_census(
                outer_path=outer, ledger_path=ledger, cli_path=cli,
                expected_input_set_sha256="A" * 64, output_path=output,
            )
        self.assertEqual("complete", result["status"])
        self.assertEqual(gate._sha256_file(ledger), result["provenance"]["ledger"]["sha256"])
        self.assertEqual(hashlib.sha256(self.data).hexdigest().upper(), result["files"][0]["logicalSha256"])
        self.assertEqual(1, result["summary"]["filesUnique"])

    def test_partial_fixture_is_not_publication_eligible(self) -> None:
        outer, ledger, cli = self._write_full_fixture()
        # Add a second ledger identity backed by the same chunk.
        with gzip.open(ledger, "rt", encoding="utf-8") as handle:
            lines = [json.loads(line) for line in handle]
        second = dict(lines[1]); second["virtualPath"] = second["fileName"] = "Data/Json/SkillData/z.json"
        with gzip.open(ledger, "wt", encoding="utf-8", newline="\n") as handle:
            for row in (lines[0], lines[1], second): handle.write(json.dumps(row) + "\n")
        outer_data = json.loads(outer.read_text()); outer_data["summary"]["ledgerFileCount"] = 2
        outer_data["publication"]["ledgerSha256"] = gate._sha256_file(ledger)
        outer.write_text(json.dumps(outer_data), encoding="utf-8")
        with mock.patch.object(gate, "_read_stream_rows", return_value=([_stream_row(self.data)], "Streamed 1 files\n")):
            result = gate.build_current_census(
                outer_path=outer, ledger_path=ledger, cli_path=cli,
                expected_input_set_sha256="A" * 64, max_files=1,
                output_path=gate.MODULE_REPO_ROOT / "tmp/animestudio/skilldata_test/partial.json",
            )
        self.assertEqual("partial", result["status"])
        self.assertFalse(result["publicationEligible"])
        self.assertEqual(2, result["summary"]["ledgerSkillFiles"])

    def test_ledger_hash_and_input_set_drift_fail(self) -> None:
        outer, ledger, _cli = self._write_full_fixture()
        with self.assertRaisesRegex(gate.CensusGateError, "outer-input-set-mismatch"):
            gate._read_outer_and_ledger(outer, ledger, expected_input_set_sha256="B" * 64)
        outer_data = json.loads(outer.read_text()); outer_data["publication"]["ledgerSha256"] = "0" * 64
        outer.write_text(json.dumps(outer_data), encoding="utf-8")
        with self.assertRaisesRegex(gate.CensusGateError, "ledger-publication-sha256-mismatch"):
            gate._read_outer_and_ledger(outer, ledger, expected_input_set_sha256="A" * 64)

    def test_blc_addition_is_rejected(self) -> None:
        outer, ledger, _cli = self._write_full_fixture()
        extra = self.root / "Persistent/VFS/OTHER/OTHER.blc"
        extra.parent.mkdir(parents=True); extra.write_bytes(b"new")
        with self.assertRaisesRegex(gate.CensusGateError, "blc-path-set-mismatch"):
            gate._read_outer_and_ledger(outer, ledger, expected_input_set_sha256="A" * 64)

    def test_new_primary_chunk_invalidates_recorded_fallback_selection(self) -> None:
        primary = self.root / "Persistent"
        fallback = self.root / "StreamingAssets"
        chunk_name = hashlib.md5(self.data).hexdigest().upper() + ".chk"
        fallback_chunk = fallback / "VFS/775A31D1" / chunk_name
        fallback_chunk.parent.mkdir(parents=True); fallback_chunk.write_bytes(self.data)
        row = _ledger_row(fallback_chunk, self.data)
        row["chunkFile"] = chunk_name
        row["physicalChunkRoot"] = str(fallback)
        row["physicalChunkSource"] = "fallback"
        outer = {"primaryAssets": str(primary), "fallbackAssets": str(fallback)}
        first = gate._chunk_selection_snapshot([row], outer)
        self.assertEqual("fallback", first[0]["selectedRole"])
        primary_chunk = primary / "VFS/775A31D1" / chunk_name
        primary_chunk.parent.mkdir(parents=True); primary_chunk.write_bytes(self.data)
        with self.assertRaisesRegex(gate.CensusGateError, "chunk-overlay-selection-mismatch"):
            gate._chunk_selection_snapshot([row], outer)

    def test_chunk_identity_rejects_path_traversal(self) -> None:
        row = dict(self.row); row["hashDirectory"] = "../escape"
        with self.assertRaisesRegex(gate.CensusGateError, "invalid-hash-directory"):
            gate._chunk_selection_snapshot([row], {"primaryAssets": str(self.root), "fallbackAssets": str(self.root / "f")})

    def test_chunk_symlink_cannot_escape_selected_assets_root(self) -> None:
        primary = self.root / "Persistent"
        fallback = self.root / "StreamingAssets"
        outside_target = self.root / "outside.chk"
        outside_target.write_bytes(self.data)
        chunk_file = "0123456789ABCDEF0123456789ABCDEF.chk"
        selected_path = primary / "VFS" / self.row["hashDirectory"] / chunk_file
        row = _ledger_row(outside_target, self.data)
        row["chunkFile"] = chunk_file
        row["physicalChunkPath"] = str(selected_path)
        row["physicalChunkRoot"] = str(primary)
        row["physicalChunkSource"] = "primary"
        outer = {"primaryAssets": str(primary), "fallbackAssets": str(fallback)}
        original_resolve = Path.resolve

        def resolve_with_symlink_escape(path: Path, *args, **kwargs) -> Path:
            if path == selected_path:
                return original_resolve(outside_target)
            return original_resolve(path, *args, **kwargs)

        with mock.patch.object(Path, "resolve", new=resolve_with_symlink_escape):
            with self.assertRaisesRegex(gate.CensusGateError, "chunk-path-outside-assets-root"):
                gate._chunk_selection_snapshot([row], outer)

    def test_partial_output_cannot_replace_reports(self) -> None:
        with self.assertRaisesRegex(gate.CensusGateError, "partial-output-outside-scratch"):
            gate._guard_partial_output(gate.MODULE_REPO_ROOT / "reports/animestudio/skilldata_latest.json")
        gate._guard_partial_output(gate.MODULE_REPO_ROOT / "tmp/animestudio/skilldata/partial.json")

    def test_outputs_cannot_overwrite_unselected_chunks_or_hardlinks(self) -> None:
        outer, ledger, cli = self._write_full_fixture()
        other = self.root / "Persistent/VFS/775A31D1/unselected.chk"
        other.write_bytes(b"unselected other-format data")
        with gzip.open(ledger, "rt", encoding="utf-8") as handle:
            rows = [json.loads(line) for line in handle]
        rows.append({"recordType": "file", "virtualPath": "Data/Other.bin",
                     "physicalChunkPath": str(other)})
        with gzip.open(ledger, "wt", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row) + "\n")
        document = json.loads(outer.read_text())
        document["summary"]["ledgerFileCount"] = 2
        document["publication"]["ledgerSha256"] = gate._sha256_file(ledger)
        outer.write_text(json.dumps(document), encoding="utf-8")
        link = self.root / "report-hardlink.json"
        os.link(other, link)
        for field in ("output_path", "output_md_path"):
            for target in (other, link):
                with self.subTest(field=field, target=target):
                    with mock.patch.object(gate, "_read_stream_rows") as stream:
                        with self.assertRaisesRegex(gate.CensusGateError, "output-"):
                            gate.build_current_census(
                                outer_path=outer, ledger_path=ledger, cli_path=cli,
                                expected_input_set_sha256="A" * 64, **{field: target},
                            )
                    stream.assert_not_called()
                    self.assertEqual(b"unselected other-format data", other.read_bytes())

    def test_unselected_cli_cannot_supply_current_receipt(self) -> None:
        outer, ledger, _cli = self._write_full_fixture()
        foreign_cli = self.root / "foreign.exe"
        foreign_cli.write_bytes(b"other executable")
        with mock.patch.object(gate, "_read_stream_rows") as stream:
            with self.assertRaisesRegex(gate.CensusGateError, "stream-cli-not-in-outer-build-fingerprints"):
                gate.build_current_census(
                    outer_path=outer, ledger_path=ledger, cli_path=foreign_cli,
                    expected_input_set_sha256="A" * 64,
                )
        stream.assert_not_called()

    def test_end_gate_rejects_changed_cli_and_chunk(self) -> None:
        for changed in ("cli", "chunk"):
            with self.subTest(changed=changed):
                outer, ledger, cli = self._write_full_fixture()
                with gzip.open(ledger, "rt", encoding="utf-8") as handle:
                    next(handle)
                    row = json.loads(next(handle))
                target = cli if changed == "cli" else Path(row["physicalChunkPath"])
                def mutate(_command):
                    target.write_bytes(target.read_bytes() + b"drift")
                    return [_stream_row(self.data)], "Streamed 1 files\n"
                with mock.patch.object(gate, "_read_stream_rows", side_effect=mutate):
                    with self.assertRaises(gate.CensusGateError) as caught:
                        gate.build_current_census(
                            outer_path=outer, ledger_path=ledger, cli_path=cli,
                            expected_input_set_sha256="A" * 64,
                        )
                self.assertIn(caught.exception.diagnostic["code"],
                              ("fingerprint-length-mismatch", "selected-chunk-drift"))

    def test_end_gate_rejects_parser_source_drift_without_editing_sources(self) -> None:
        outer, ledger, cli = self._write_full_fixture()
        snapshots = gate._parser_source_snapshots()
        changed = [dict(row) for row in snapshots]
        changed[0]["sha256"] = "0" * 64
        with mock.patch.object(gate, "_parser_source_snapshots", side_effect=[snapshots, changed]), \
                mock.patch.object(gate, "_read_stream_rows", return_value=([_stream_row(self.data)], "Streamed 1 files\n")):
            with self.assertRaisesRegex(gate.CensusGateError, "code-drift"):
                gate.build_current_census(
                    outer_path=outer, ledger_path=ledger, cli_path=cli,
                    expected_input_set_sha256="A" * 64,
                )


if __name__ == "__main__":
    unittest.main()
