from __future__ import annotations

import hashlib
import io
import json
import struct
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from scripts.game_data.memorypack.skill import frame_skill_memorypack
from scripts.game_data.memorypack.skill_cursor_receipt import (
    OUTPUT_SCHEMA,
    SKILL_REPORT_FORMAT,
    ReceiptVerificationError,
    main,
    preflight_skilldata_corpus,
    verify_skilldata_cursor_capture,
)


INPUT_SET = "2FC7CA89AF0F64842412667CC363446BD21B89C07C6F54E10E87D63B16464E16"
GAME_HASH = "C24495E51B406F03B03890C4788EE618AE022C991405BE5D5B8B787CB775AE89"
METADATA_HASH = "0076743397ACADF03D3B0064343A963C7C88863B8160526D397E4B3EFB96F02E"
LOGICAL_PATH = "Data/Json/SkillData/Potential_test.json"


def u32(value: int) -> bytes:
    return struct.pack("<I", value)


def source_bytes(*, wrapped: bool = True) -> bytes:
    # Same anonymous 48-member/two-list prefix as the corpus framer; terminal
    # counts are empty so this fixture isolates the one-byte collision.
    return b"\x30\x02" + u32(0) + u32(0) + b"\x00" + (b"\x01" if wrapped else b"") + u32(0) + u32(0) + u32(0) + b"\x00"


class CursorReceiptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = source_bytes(wrapped=True)
        self.digest = hashlib.sha256(self.data).hexdigest().upper()
        framed = frame_skill_memorypack(self.data, source=LOGICAL_PATH)
        self.candidate = next(
            row for row in framed["candidates"]
            if row["encoding"] == "counted"
        )
        self.start = int(self.candidate["startOffset"], 0)
        final_range = self.candidate["members"][-1]["range"]
        self.final_before = final_range["start"]
        self.receipt = {
            "schema": "endfieldCapture.skillDataCursorCapture.v1",
            "inputSetSha256": INPUT_SET,
            "nativeInputs": {
                "gameAssemblySha256": GAME_HASH,
                "metadataSha256": METADATA_HASH,
            },
            "captureComplete": True,
            "hooksInstalled": True,
            "quiescentCleanup": True,
            "losses": 0,
            "overflow": 0,
            "unsupported": 0,
            "observations": [{
                "sourceLength": len(self.data),
                "sourceHex": self.data.hex(),
                "startCallsiteRva": "0x37DE8C5",
                "startCursorBefore": self.start,
                "startByte": self.data[self.start],
                "startResult": self.data[self.start] == 1,
                "startCursorAfter": self.start + 1,
                "finalCallsiteRva": "0x37DE99D",
                "finalCursorBefore": self.final_before,
                "finalByte": self.data[self.final_before],
                "finalResult": self.data[self.final_before] == 1,
                "finalCursorAfter": len(self.data),
                "sameReader": True,
                "sameThread": True,
            }],
        }
        self.corpus = {
            "format": SKILL_REPORT_FORMAT,
            "status": "complete",
            "publicationEligible": True,
            "inputSetSha256": INPUT_SET,
            "files": [{
                "inputSetSha256": INPUT_SET,
                "virtualPath": LOGICAL_PATH,
                "blockName": "JsonData",
                "blockTypeValue": 19,
                "length": len(self.data),
                "logicalSha256": self.digest,
            }],
        }
        self.native_context = {
            "schemaVersion": 1,
            "inputSetSha256": INPUT_SET,
            "nativeInputs": {
                "gameassemblySha256": GAME_HASH,
                "metadataSha256": METADATA_HASH,
            },
            "corpusReference": {"sha256": self.corpus_sha256()},
        }

    def corpus_sha256(self) -> str:
        # Deterministic fixture bytes stand in for the exact serialized report.
        encoded = json.dumps(self.corpus, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest().upper()

    def write_verification_reports(
        self,
        directory: Path,
        *,
        sync_corpus_reference: bool = True,
    ) -> tuple[Path, Path]:
        corpus_path = directory / "skilldata.json"
        context_path = directory / "context.json"
        corpus_bytes = json.dumps(
            self.corpus, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        corpus_path.write_bytes(corpus_bytes)
        context = json.loads(json.dumps(self.native_context))
        if sync_corpus_reference:
            context.setdefault("corpusReference", {})["sha256"] = (
                hashlib.sha256(corpus_bytes).hexdigest().upper()
            )
        context_path.write_text(
            json.dumps(context, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
        return corpus_path, context_path

    def verify(
        self,
        *,
        required: tuple[str, ...] = (),
        sync_corpus_reference: bool = True,
    ) -> dict:
        with tempfile.TemporaryDirectory() as temp_dir:
            corpus_path, context_path = self.write_verification_reports(
                Path(temp_dir), sync_corpus_reference=sync_corpus_reference,
            )
            return verify_skilldata_cursor_capture(
                self.receipt,
                corpus_report_path=corpus_path,
                native_context_path=context_path,
                required_logical_paths=required,
            )

    def write_preflight_reports(
        self,
        directory: Path,
        *,
        context_input_set: str = INPUT_SET,
        context_corpus_sha256: str | None = None,
    ) -> tuple[Path, Path]:
        corpus_path = directory / "skilldata.json"
        context_path = directory / "context.json"
        corpus_bytes = json.dumps(self.corpus, sort_keys=True, separators=(",", ":")).encode()
        corpus_path.write_bytes(corpus_bytes)
        context = {
            "schemaVersion": 1,
            "inputSetSha256": context_input_set,
            "nativeInputs": {
                "gameassemblySha256": GAME_HASH,
                "metadataSha256": METADATA_HASH,
            },
            "corpusReference": {
                "sha256": context_corpus_sha256 or hashlib.sha256(corpus_bytes).hexdigest().upper(),
            },
        }
        context_path.write_text(json.dumps(context), encoding="utf-8")
        return corpus_path, context_path

    def test_preflight_authenticates_current_reports_and_prints_only_input_set(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            corpus_path, context_path = self.write_preflight_reports(Path(temp_dir))
            self.assertEqual(
                preflight_skilldata_corpus(
                    corpus_report_path=corpus_path,
                    native_context_path=context_path,
                ),
                INPUT_SET,
            )
            stdout, stderr = io.StringIO(), io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                result = main([
                    "--preflight",
                    "--corpus-report", str(corpus_path),
                    "--native-context", str(context_path),
                ])
            self.assertEqual(result, 0)
            self.assertEqual(stdout.getvalue(), INPUT_SET + "\n")
            self.assertEqual(stderr.getvalue(), "")

    def test_preflight_rejects_stale_missing_and_mismatched_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            corpus_path, context_path = self.write_preflight_reports(
                directory, context_input_set="0" * 64,
            )
            with self.assertRaisesRegex(ReceiptVerificationError, "input set"):
                preflight_skilldata_corpus(
                    corpus_report_path=corpus_path,
                    native_context_path=context_path,
                )

            with self.assertRaisesRegex(ReceiptVerificationError, "cannot read valid JSON"):
                preflight_skilldata_corpus(
                    corpus_report_path=corpus_path,
                    native_context_path=directory / "missing-context.json",
                )

            corpus_path, context_path = self.write_preflight_reports(
                directory, context_corpus_sha256="0" * 64,
            )
            with self.assertRaisesRegex(ReceiptVerificationError, "report bytes differ"):
                preflight_skilldata_corpus(
                    corpus_report_path=corpus_path,
                    native_context_path=context_path,
                )

    def test_runtime_cursor_resolves_two_framer_candidates_and_redacts_bytes(self) -> None:
        self.assertEqual(len(frame_skill_memorypack(self.data)["candidates"]), 2)
        report = self.verify(required=("Potential_test.json",))
        row = report["rows"][0]
        self.assertEqual(report["schema"], OUTPUT_SCHEMA)
        self.assertEqual(report["status"], "complete")
        self.assertEqual(row["boundaryClass"], "exact-closed")
        self.assertEqual(row["candidate"]["framerCandidateCount"], 2)
        self.assertEqual(row["range"], {"start": self.start, "end": len(self.data)})
        self.assertEqual(row["parserCursor"], len(self.data))
        self.assertEqual(report["summary"]["exactClosed"], 1)
        self.assertEqual(report["summary"]["structuralPrefix"], 1)
        self.assertEqual(report["summary"]["ambiguous"], 0)
        self.assertEqual(report["summary"]["opaque"], 1)
        self.assertEqual(report["summary"]["opaqueBytes"], 1)
        self.assertNotIn("sourceHex", str(report))
        self.assertNotIn(self.data.hex(), str(report))

    def test_start_that_is_not_a_candidate_remains_ambiguous(self) -> None:
        observation = self.receipt["observations"][0]
        observation["startCursorBefore"] = self.start + 2
        observation["startByte"] = self.data[self.start + 2]
        observation["startResult"] = self.data[self.start + 2] == 1
        observation["startCursorAfter"] = self.start + 3
        report = self.verify()
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["rows"][0]["boundaryClass"], "ambiguous")
        self.assertEqual(report["summary"]["ambiguous"], 1)
        self.assertEqual(len(report["rows"][0]["candidateAlternatives"]), 2)
        self.assertTrue(all(
            alt["start"] < alt["end"]
            for alt in report["rows"][0]["candidateAlternatives"]
        ))
        self.assertEqual(
            [
                sum(span["end"] - span["start"] for span in alt["opaqueByteRanges"])
                for alt in report["rows"][0]["candidateAlternatives"]
            ],
            [0, 1],
        )
        self.assertEqual(report["summary"]["opaque"], 1)
        self.assertEqual(report["summary"]["opaqueBytes"], 1)

    def test_final_cursor_must_close_candidate_at_hard_limit(self) -> None:
        observation = self.receipt["observations"][0]
        observation["finalCursorBefore"] = len(self.data) - 2
        observation["finalByte"] = self.data[-2]
        observation["finalCursorAfter"] = len(self.data) - 1
        report = self.verify()
        self.assertEqual(report["rows"][0]["boundaryClass"], "ambiguous")
        self.assertEqual(report["rows"][0]["parserCursor"], len(self.data) - 1)
        self.assertIn(
            {"start": len(self.data) - 1, "end": len(self.data), "kind": "unresolved-opaque-range"},
            report["rows"][0]["opaqueByteRanges"],
        )
        self.assertEqual(len(report["rows"][0]["candidateAlternatives"]), 2)
        self.assertEqual(report["summary"]["opaqueBytes"], 2)

    def test_only_selected_candidate_prefix_overlap_blocks_promotion(self) -> None:
        candidate_start = self.start
        mocked_prefix = {
            # The selected counted candidate starts exactly at the prefix end;
            # its competing wrapper candidate overlaps the prefix by one byte.
            "cursorOffset": hex(candidate_start),
            "provenPrefixByteLength": candidate_start,
            "recordLists": [],
        }
        with patch(
            "scripts.game_data.memorypack.skill_cursor_receipt.frame_skill_common_prefix",
            return_value=mocked_prefix,
        ):
            report = self.verify()
        row = report["rows"][0]
        self.assertEqual(row["boundaryClass"], "exact-closed")
        self.assertFalse(row["prefixCandidateOverlap"])
        self.assertEqual(
            [
                (alt["prefixCandidateOverlap"], alt["selected"])
                for alt in row["candidateAlternatives"]
            ],
            [(True, False), (False, True)],
        )

    def test_selected_candidate_prefix_overlap_blocks_promotion(self) -> None:
        mocked_prefix = {
            "cursorOffset": hex(self.start + 1),
            "provenPrefixByteLength": self.start + 1,
            "recordLists": [],
        }
        with patch(
            "scripts.game_data.memorypack.skill_cursor_receipt.frame_skill_common_prefix",
            return_value=mocked_prefix,
        ):
            report = self.verify()
        row = report["rows"][0]
        self.assertEqual(row["boundaryClass"], "ambiguous")
        self.assertEqual(row["diagnostic"], "prefix-candidate-range-overlap")
        self.assertTrue(row["prefixCandidateOverlap"])
        self.assertTrue(any(alt["prefixCandidateOverlap"] for alt in row["candidateAlternatives"]))

    def test_native_corpus_reference_authenticates_report_bytes(self) -> None:
        self.native_context["corpusReference"] = {"sha256": "A" * 64}
        with self.assertRaisesRegex(ReceiptVerificationError, "differ"):
            self.verify(sync_corpus_reference=False)
        self.native_context["corpusReference"]["sha256"] = self.corpus_sha256()
        report = self.verify(sync_corpus_reference=False)
        self.assertEqual(report["status"], "complete")

    def test_verifier_does_not_accept_unhashed_report_mappings(self) -> None:
        with self.assertRaises(TypeError):
            verify_skilldata_cursor_capture(
                self.receipt,
                corpus_report=self.corpus,
                native_context=self.native_context,
                corpus_report_sha256=self.corpus_sha256(),
            )

    def test_present_corpus_reference_requires_sha256(self) -> None:
        self.native_context["corpusReference"] = {}
        with self.assertRaisesRegex(ReceiptVerificationError, "corpusReference.sha256"):
            self.verify(sync_corpus_reference=False)

    def test_missing_corpus_reference_is_rejected(self) -> None:
        del self.native_context["corpusReference"]
        with self.assertRaisesRegex(ReceiptVerificationError, "corpusReference"):
            self.verify(sync_corpus_reference=False)

    def test_corpus_paths_must_be_unique_and_jsondata(self) -> None:
        self.corpus["files"][0]["blockName"] = "Other"
        with self.assertRaisesRegex(ReceiptVerificationError, "not a JsonData block"):
            self.verify()

    def test_duplicate_logical_path_is_rejected_even_with_different_hash(self) -> None:
        self.corpus["files"].append({
            **self.corpus["files"][0],
            "logicalSha256": "0" * 64,
        })
        with self.assertRaisesRegex(ReceiptVerificationError, "duplicate logical path"):
            self.verify()

    def test_content_hash_must_join_unique_current_corpus_row(self) -> None:
        self.receipt["observations"][0]["sourceHex"] = (self.data + b"\x00").hex()
        self.receipt["observations"][0]["sourceLength"] += 1
        report = self.verify()
        self.assertEqual(report["rows"][0]["boundaryClass"], "unsupported")
        self.assertEqual(report["rows"][0]["diagnostic"], "source-hash-join-missing")
        self.assertEqual(report["summary"]["unsupported"], 1)

    def test_bool_helper_results_must_be_present_json_booleans(self) -> None:
        for field in ("startResult", "finalResult"):
            with self.subTest(field=field):
                observation = self.receipt["observations"][0]
                original = observation.pop(field)
                report = self.verify()
                self.assertEqual(report["rows"][0]["boundaryClass"], "unsupported")
                self.assertEqual(report["rows"][0]["diagnostic"], f"{field.removesuffix('Result')}-result-not-boolean")
                observation[field] = original
                observation[field] = 1
                report = self.verify()
                self.assertEqual(report["rows"][0]["boundaryClass"], "unsupported")
                self.assertEqual(report["rows"][0]["diagnostic"], f"{field.removesuffix('Result')}-result-not-boolean")
                observation[field] = original

    def test_bool_helper_results_must_match_observed_bytes(self) -> None:
        observation = self.receipt["observations"][0]
        observation["startResult"] = False
        report = self.verify()
        self.assertEqual(report["rows"][0]["boundaryClass"], "unsupported")
        self.assertEqual(report["rows"][0]["diagnostic"], "start-result-does-not-match-source-byte")

        observation["startResult"] = self.data[self.start] == 1
        observation["finalResult"] = True
        report = self.verify()
        self.assertEqual(report["rows"][0]["boundaryClass"], "unsupported")
        self.assertEqual(report["rows"][0]["diagnostic"], "final-result-does-not-match-source-byte")

    def test_required_logical_paths_gate_completion(self) -> None:
        report = self.verify(required=(
            "Potential_test.json", "eny_0007_mimicw_passive.json",
        ))
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["summary"]["verifiedRequiredLogicalPaths"], [LOGICAL_PATH])
        self.assertEqual(report["summary"]["missingRequiredLogicalPaths"], [
            "Data/Json/SkillData/eny_0007_mimicw_passive.json",
        ])

    def test_both_empty_and_count_three_paths_can_be_required(self) -> None:
        second_path = "Data/Json/SkillData/eny_0007_mimicw_passive.json"
        records = b"".join(b"\x01" + u32(index) for index in range(3))
        second_data = (
            b"\x30\x02" + u32(0) + u32(0)
            + b"\x00\x01" + u32(3) + records + u32(0) + u32(0) + b"\x00"
        )
        candidate = next(
            row for row in frame_skill_memorypack(second_data)["candidates"]
            if row["encoding"] == "counted"
        )
        start = int(candidate["startOffset"], 0)
        final_before = candidate["members"][-1]["range"]["start"]
        second_digest = hashlib.sha256(second_data).hexdigest().upper()
        self.corpus["files"].append({
            "inputSetSha256": INPUT_SET,
            "virtualPath": second_path,
            "blockName": "JsonData",
            "blockTypeValue": 19,
            "length": len(second_data),
            "logicalSha256": second_digest,
        })
        self.receipt["observations"].append({
            "sourceLength": len(second_data),
            "sourceHex": second_data.hex(),
            "startCallsiteRva": "0x37DE8C5",
            "startCursorBefore": start,
            "startByte": second_data[start],
            "startResult": second_data[start] == 1,
            "startCursorAfter": start + 1,
            "finalCallsiteRva": "0x37DE99D",
            "finalCursorBefore": final_before,
            "finalByte": second_data[final_before],
            "finalResult": second_data[final_before] == 1,
            "finalCursorAfter": len(second_data),
            "sameReader": True,
            "sameThread": True,
        })
        report = self.verify(required=(
            "Potential_test.json", "eny_0007_mimicw_passive.json",
        ))
        self.assertEqual(report["status"], "complete")
        self.assertEqual(report["summary"]["exactClosed"], 2)
        self.assertEqual(report["summary"]["verifiedRequiredLogicalPaths"], [
            LOGICAL_PATH, second_path,
        ])
        self.assertGreaterEqual(report["rows"][1]["candidate"]["framerCandidateCount"], 2)

    def test_native_hash_and_capture_gates_fail_closed(self) -> None:
        self.native_context["nativeInputs"]["gameassemblySha256"] = "0" * 64
        with self.assertRaises(ReceiptVerificationError):
            self.verify()
        self.native_context["nativeInputs"]["gameassemblySha256"] = GAME_HASH
        self.receipt["overflow"] = 1
        with self.assertRaises(ReceiptVerificationError):
            self.verify()
        self.receipt["overflow"] = 0
        self.receipt["unsupported"] = True
        with self.assertRaises(ReceiptVerificationError):
            self.verify()

    def test_losses_status_flags_and_empty_counters_fail_closed(self) -> None:
        cases = (
            ("losses", 1),
            ("losses", {"unreadableReaderState": 1}),
            ("losses", {}),
            ("overflow", []),
        )
        for field, value in cases:
            with self.subTest(field=field, value=value):
                original = self.receipt[field]
                self.receipt[field] = value
                with self.assertRaisesRegex(ReceiptVerificationError, field):
                    self.verify()
                self.receipt[field] = original

        for field in ("captureComplete", "hooksInstalled", "quiescentCleanup"):
            with self.subTest(field=field):
                original = self.receipt[field]
                self.receipt[field] = False
                with self.assertRaisesRegex(ReceiptVerificationError, field):
                    self.verify()
                self.receipt[field] = original

    def test_unsupported_receipt_counter_is_retained_without_becoming_loss(self) -> None:
        self.receipt["unsupported"] = 4
        report = self.verify()
        self.assertEqual(report["status"], "complete")
        self.assertEqual(report["summary"]["unsupportedReceiptEvents"], 4)
        self.assertEqual(report["summary"]["unsupported"], 4)

    def test_duplicate_source_hash_is_not_a_unique_path_join(self) -> None:
        self.corpus["files"].append({
            **self.corpus["files"][0],
            "virtualPath": "Data/Json/SkillData/duplicate.json",
        })
        report = self.verify()
        self.assertEqual(report["rows"][0]["boundaryClass"], "unsupported")
        self.assertEqual(report["rows"][0]["diagnostic"], "source-hash-join-ambiguous")


if __name__ == "__main__":
    unittest.main()
