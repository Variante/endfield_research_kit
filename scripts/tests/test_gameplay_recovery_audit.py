import json
import io
import tempfile
import unittest
from copy import deepcopy
from contextlib import redirect_stderr
from types import SimpleNamespace
from unittest.mock import patch

from scripts import build_gameplay
from pathlib import Path

from scripts.gameplay_builder.recovery_audit import (
    build_full_corpus_payload,
    build_report,
    content_sha256,
    iter_action_occurrences,
    main,
    render_markdown,
)


def action(
    name: str,
    *,
    status: str = "exact",
    semantic: str = "exact-test",
    member_count: int = 3,
    tag: str = "0x0001",
    offset: str = "0x13",
    bytes_count: int = 10,
    boundary_proof: str | None = None,
    nested: dict | None = None,
) -> dict:
    decoded = {
        "type": name,
        "decodeStatus": status,
        "semanticStatus": semantic,
        "byteLength": bytes_count,
    }
    if nested is not None:
        decoded["conditionAction"] = {"actionDataCount": 1, "actionDataItems": [nested]}
    return {
        "name": name,
        "decodeStatus": status,
        "memberCount": member_count,
        "tag": tag,
        "offset": offset,
        "bytes": bytes_count,
        "boundaryProof": boundary_proof if boundary_proof is not None else (
            "typed-consumption" if status == "exact" else "partial"
        ),
        "decoded": decoded,
    }


def fixture_payload() -> dict:
    return {
        "language": "CN",
        "generated": 123,
        "buffs": {
            "buff_a": {
                "abilityEventActions": [
                    {"actions": [{"actionDataCount": 2, "actionDataItems": [
                        action("Core_A", tag="0x0001", offset="0x13", bytes_count=10),
                        action("Core_B", status="partial", semantic="partial-test", member_count=4,
                               tag="0x0002", offset="0x20", bytes_count=11,
                               nested=action("Core_Nested", member_count=5, tag="0x0003", offset="0x30", bytes_count=12)),
                    ]}]},
                ],
            },
        },
    }


class GameplayRecoveryAuditTests(unittest.TestCase):
    def test_full_corpus_uses_persistent_overlay_and_records_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            export_root = Path(directory)
            streaming = export_root / "structured" / "StreamingAssets" / "Data" / "Json" / "BuffData"
            persistent = export_root / "structured" / "Persistent" / "Data" / "Json" / "BuffData"
            streaming.mkdir(parents=True)
            persistent.mkdir(parents=True)
            (streaming / "buff_shared.json").write_text("stream", encoding="utf-8")
            (streaming / "buff_stream_only.json").write_text("stream", encoding="utf-8")
            (persistent / "buff_shared.json").write_text("persistent", encoding="utf-8")
            (persistent / "buff_persist_only.json").write_text("persistent", encoding="utf-8")

            def decode(path: Path) -> dict:
                return {
                    "id": path.stem,
                    "status": "parsed-through-exact-tail",
                    "abilityEventActions": [],
                }

            with patch("scripts.game_data.memorypack.buff.buff_gameplay_semantics", side_effect=decode):
                payload, meta = build_full_corpus_payload(export_root)
            self.assertEqual("ok", meta["status"])
            self.assertEqual(["buff_persist_only", "buff_shared", "buff_stream_only"], meta["selected"])
            self.assertEqual(["buff_shared"], [row["id"] for row in meta["shadowed"]])
            self.assertEqual(["buff_persist_only"], meta["persistentOnly"])
            self.assertEqual(["buff_stream_only"], meta["streamingOnly"])
            self.assertEqual("Persistent", meta["selectedSources"]["buff_shared"])
            self.assertEqual(2, meta["sourceFileCounts"]["Persistent"])
            self.assertEqual(2, meta["sourceFileCounts"]["StreamingAssets"])
            self.assertEqual(64, len(meta["manifestHashes"]["Persistent"]))
            self.assertEqual("Persistent", payload["buffs"]["buff_shared"]["source"]["kind"])
            shadow = meta["shadowed"][0]
            self.assertEqual("Persistent", shadow["selectedSource"])
            self.assertFalse(shadow["sameBytesAsSelected"])
            self.assertEqual(4, len(meta["sourceManifest"]))
            self.assertEqual(64, len(meta["selectedManifestSha256"]))
            self.assertEqual(64, len(meta["allSourceManifestSha256"]))
            report = build_report(payload, scope="full", full_corpus=meta)
            self.assertEqual("full", report["scope"])
            self.assertIn("fullCorpus", report)

    def test_full_corpus_missing_root_and_decode_errors_are_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            export_root = Path(directory)
            streaming = export_root / "structured" / "StreamingAssets" / "Data" / "Json" / "BuffData"
            streaming.mkdir(parents=True)
            (streaming / "buff_bad.json").write_text("bad", encoding="utf-8")
            (streaming / "buff_good.json").write_text("good", encoding="utf-8")

            def decode(path: Path) -> dict:
                if path.stem == "buff_bad":
                    raise OSError("unreadable")
                return {"id": path.stem, "status": "unsupported-version", "abilityEventActions": []}

            with patch("scripts.game_data.memorypack.buff.buff_gameplay_semantics", side_effect=decode):
                payload, meta = build_full_corpus_payload(export_root)
            self.assertEqual("error", meta["status"])
            self.assertEqual(["Persistent"], meta["missingRoots"])
            self.assertEqual(2, meta["errorCount"])
            self.assertEqual(2, meta["invalidFileCount"])
            self.assertEqual(["buff_bad", "buff_good"], meta["selected"])
            self.assertEqual([], payload["buffs"]["buff_bad"]["abilityEventActions"])

            source = export_root / "index.json"
            output = export_root / "reports" / "gameplay_recovery_audit_full.json"
            source.write_text("{}", encoding="utf-8")
            with patch("scripts.game_data.memorypack.buff.buff_gameplay_semantics", side_effect=decode):
                self.assertEqual(
                    1,
                    main([
                        "--full-corpus", "--export-root", str(export_root),
                        "--output", str(output),
                    ]),
                )
            self.assertTrue(output.is_file())
            written = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual("full", written["scope"])
            self.assertEqual("error", written["fullCorpus"]["status"])

    def test_full_corpus_rejects_noncanonical_direct_filenames(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            export_root = Path(directory)
            for source in ("StreamingAssets", "Persistent"):
                root = export_root / "structured" / source / "Data" / "Json" / "BuffData"
                root.mkdir(parents=True)
            valid = export_root / "structured" / "StreamingAssets" / "Data" / "Json" / "BuffData" / "buff_valid.json"
            valid.write_text("valid", encoding="utf-8")
            invalid_root = export_root / "structured" / "Persistent" / "Data" / "Json" / "BuffData"
            for name in ("Buff_upper.json", "buff_has.dot.json", "buff-no.json", "notes.txt"):
                (invalid_root / name).write_text(name, encoding="utf-8")
            with patch(
                "scripts.game_data.memorypack.buff.buff_gameplay_semantics",
                return_value={"id": "buff_valid", "status": "parsed-through-exact-tail", "abilityEventActions": []},
            ):
                payload, meta = build_full_corpus_payload(export_root)
            self.assertEqual(["buff_valid"], meta["selected"])
            self.assertEqual(4, meta["invalidFileCount"])
            invalid = [row for row in meta["invalidFiles"] if row["kind"] == "invalid-filename"]
            self.assertEqual(4, len(invalid))
            self.assertTrue(all({"source", "relativePath", "expected", "actual", "size", "sha256"} <= row.keys() for row in invalid))
            self.assertEqual("error", meta["status"])
            report = build_report(payload, scope="full", full_corpus=meta)
            self.assertEqual(0, report["counts"]["actionOccurrences"])

    def test_full_baseline_scope_and_manifest_changes_fail_closed(self) -> None:
        payload = fixture_payload()
        full_meta = {
            "selectedManifestSha256": "a" * 64,
            "allSourceManifestSha256": "b" * 64,
        }
        previous = build_report(payload, scope="full", full_corpus=full_meta)
        changed_meta = dict(full_meta, selectedManifestSha256="c" * 64)
        current = build_report(payload, previous, scope="full", full_corpus=changed_meta)
        self.assertEqual("compared", current["comparison"]["status"])
        self.assertTrue(current["comparison"]["reviewRequired"])
        self.assertIn("full-manifest-changed", {item["kind"] for item in current["changeDiagnostics"]})
        scope_mismatch = build_report(payload, previous, scope="active")
        self.assertEqual("error", scope_mismatch["comparison"]["status"])
        self.assertIn("scope", scope_mismatch["comparison"]["reason"])

    def test_build_gameplay_rejects_audit_options_without_audit_stage(self) -> None:
        with self.assertRaises(SystemExit):
            build_gameplay.parse_args(["--stage", "base", "--audit-scope", "full"])
        with self.assertRaises(SystemExit):
            build_gameplay.parse_args(["--stage", "projectiles", "--export-root", "export"])
        with self.assertRaises(SystemExit):
            build_gameplay.parse_args(["--stage", "audit", "--export-root", "export"])

    def test_walks_top_level_and_nested_action_data(self) -> None:
        rows = list(iter_action_occurrences(fixture_payload()))
        self.assertEqual(3, len(rows))
        self.assertEqual(
            ["Core_A", "Core_B", "Core_Nested"],
            [row["actionType"] for row in rows],
        )
        self.assertEqual("buff_a", rows[0]["owner"])
        self.assertNotEqual(rows[1]["id"], rows[2]["id"])

    def test_report_has_deterministic_dimension_histograms(self) -> None:
        report = build_report(fixture_payload())
        self.assertEqual(
            {"Core_A": 1, "Core_B": 1, "Core_Nested": 1},
            report["histograms"]["actionType"],
        )
        self.assertEqual({"3": 1, "4": 1, "5": 1}, report["histograms"]["memberCount"])
        self.assertEqual({"0x0001": 1, "0x0002": 1, "0x0003": 1}, report["histograms"]["tag"])
        self.assertEqual(3, report["counts"]["actionOccurrences"])
        self.assertEqual(report["histograms"]["decodeStatus"], report["histograms"]["status"])
        self.assertEqual(sorted(report["occurrences"], key=lambda row: row["id"]), report["occurrences"])
        self.assertEqual("gameplay-recovery-audit.v2", report["schemaVersion"])

    def test_generated_timestamp_does_not_change_content_sha256(self) -> None:
        first = fixture_payload()
        second = deepcopy(first)
        second["generated"] = 999999
        self.assertEqual(content_sha256(first), content_sha256(second))
        self.assertEqual(build_report(first)["contentSha256"], build_report(second)["contentSha256"])
        comparison = build_report(second, build_report(first))["comparison"]
        self.assertTrue(comparison["sameInput"])
        self.assertEqual(comparison["currentContentSha256"], comparison["previousContentSha256"])

    def test_only_typed_roots_and_branches_are_scanned(self) -> None:
        payload = fixture_payload()
        payload["unrelated"] = {"actionDataItems": [action("Core_ShouldNotCount")]}
        self.assertEqual(3, len(list(iter_action_occurrences(payload))))

    def test_structural_diagnostics_are_separate_and_include_bounds(self) -> None:
        payload = deepcopy(fixture_payload())
        sequence = payload["buffs"]["buff_a"]["abilityEventActions"][0]["actions"][0]
        sequence["actionDataCount"] = 9
        item = sequence["actionDataItems"][0]
        item["name"] = "Core_WrongSummary"
        item["bytes"] = 99
        item["semanticStatus"] = "summary-semantic"
        item["decoded"]["semanticStatus"] = "decoded-semantic"
        item["memberCount"] = 7
        item["decoded"]["memberCount"] = 8
        item["decoded"]["failActions"] = []
        report = build_report(payload)
        kinds = {item["kind"] for item in report["structureDiagnostics"]}
        self.assertIn("sequence-count-mismatch", kinds)
        self.assertIn("summary-decoded-mismatch", kinds)
        self.assertIn("invalid-nested-branch", kinds)
        self.assertIn(
            "semanticStatus",
            {item.get("field") for item in report["structureDiagnostics"]},
        )
        self.assertIn(
            "memberCount",
            {item.get("field") for item in report["structureDiagnostics"]},
        )
        mismatch = next(
            item for item in report["structureDiagnostics"]
            if item["kind"] == "summary-decoded-mismatch"
        )
        self.assertEqual("buff_a", mismatch["owner"])
        self.assertIn("expected", mismatch)
        self.assertIn("actual", mismatch)
        self.assertNotIn("diagnostics", report)

    def test_materialized_action_requires_decoded_object(self) -> None:
        payload = deepcopy(fixture_payload())
        payload["buffs"]["buff_a"]["abilityEventActions"][0]["actions"][0]["actionDataItems"][0]["decoded"] = "typed-failed"
        report = build_report(payload)
        self.assertIn(
            "invalid-decoded-action",
            {item["kind"] for item in report["structureDiagnostics"]},
        )

    def test_invalid_action_summary_fields_fail_closed_individually(self) -> None:
        payload = deepcopy(fixture_payload())
        item = payload["buffs"]["buff_a"]["abilityEventActions"][0]["actions"][0]["actionDataItems"][0]
        item.pop("offset")
        item["bytes"] = -1
        item["tag"] = "not-a-tag"
        item["memberCount"] = True
        report = build_report(payload)
        errors = {
            item["field"]
            for item in report["structureDiagnostics"]
            if item["kind"] == "invalid-action-summary-field"
        }
        self.assertEqual({"offset", "bytes", "tag", "memberCount"}, errors)

    def test_canonical_ids_do_not_miscompare_after_prepend(self) -> None:
        previous = build_report(fixture_payload())
        current_payload = deepcopy(fixture_payload())
        sequence = current_payload["buffs"]["buff_a"]["abilityEventActions"][0]["actions"][0]
        sequence["actionDataCount"] = 3
        sequence["actionDataItems"].insert(
            0, action("Core_Prepend", tag="0x0009", offset="0x05", bytes_count=8)
        )
        current = build_report(current_payload, previous)
        kinds = {item["kind"] for item in current["changeDiagnostics"]}
        self.assertIn("occurrence-added", kinds)
        self.assertNotIn("status-regression", kinds)
        self.assertNotIn("status-changed", kinds)

    def test_explicit_added_occurrence_requires_review_and_cli_nonzero(self) -> None:
        previous_payload = fixture_payload()
        previous = build_report(previous_payload)
        current_payload = deepcopy(previous_payload)
        sequence = current_payload["buffs"]["buff_a"]["abilityEventActions"][0]["actions"][0]
        sequence["actionDataCount"] = 3
        sequence["actionDataItems"].insert(
            0, action("Core_Added", tag="0x0009", offset="0x05", bytes_count=8)
        )
        current = build_report(current_payload, previous)
        self.assertTrue(current["comparison"]["reviewRequired"])
        self.assertTrue(any(item["kind"] == "occurrence-added" for item in current["changeDiagnostics"]))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "current.json"
            previous_path = root / "previous.json"
            output = root / "audit.json"
            source.write_text(json.dumps(current_payload), encoding="utf-8")
            previous_path.write_text(json.dumps(previous), encoding="utf-8")
            self.assertEqual(
                1,
                main([
                    "--input", str(source), "--previous", str(previous_path),
                    "--output", str(output),
                ]),
            )

    def test_non_exact_aggregate_catches_offset_shift_with_exact_count_flat(self) -> None:
        previous = build_report(fixture_payload())
        current_payload = deepcopy(fixture_payload())
        sequence = current_payload["buffs"]["buff_a"]["abilityEventActions"][0]["actions"][0]
        sequence["actionDataCount"] = 4
        sequence["actionDataItems"][0]["offset"] = "0x14"
        sequence["actionDataItems"][0]["decodeStatus"] = "partial"
        sequence["actionDataItems"][0]["decoded"]["decodeStatus"] = "partial"
        sequence["actionDataItems"][1]["offset"] = "0x21"
        sequence["actionDataItems"].insert(
            0, action("Core_NewExact", tag="0x0009", offset="0x05", bytes_count=8)
        )
        current = build_report(current_payload, previous)
        self.assertEqual(previous["counts"]["exactActions"], current["counts"]["exactActions"])
        self.assertGreater(current["counts"]["nonExactActions"], previous["counts"]["nonExactActions"])
        regression = next(
            item for item in current["changeDiagnostics"]
            if item["kind"] == "non-exact-count-regression"
        )
        self.assertEqual("error", regression["severity"])

    def test_exact_to_typed_failed_is_a_status_regression(self) -> None:
        previous = build_report(fixture_payload())
        current_payload = deepcopy(fixture_payload())
        item = current_payload["buffs"]["buff_a"]["abilityEventActions"][0]["actions"][0]["actionDataItems"][0]
        item["decodeStatus"] = "typed-failed"
        item["decoded"]["decodeStatus"] = "typed-failed"
        current = build_report(current_payload, previous)
        regression = next(item for item in current["changeDiagnostics"] if item["kind"] == "status-regression")
        self.assertEqual("error", regression["severity"])
        self.assertEqual("typed-failed", regression["currentStatus"])

    def test_partial_promotion_does_not_turn_nonexact_count_drop_into_error(self) -> None:
        previous = build_report(fixture_payload())
        current_payload = deepcopy(fixture_payload())
        item = current_payload["buffs"]["buff_a"]["abilityEventActions"][0]["actions"][0]["actionDataItems"][1]
        item["decodeStatus"] = "exact"
        item["decoded"]["decodeStatus"] = "exact"
        current = build_report(current_payload, previous)
        promotion = [item for item in current["changeDiagnostics"] if item["kind"] == "status-promotion"]
        self.assertEqual(1, len(promotion))
        partial_count = next(item for item in current["changeDiagnostics"] if item["kind"] == "status-count-regression" and item["status"] == "partial")
        self.assertEqual("info", partial_count["severity"])
        self.assertFalse(any(item["severity"] in {"warning", "error"} for item in current["changeDiagnostics"]))
        self.assertFalse(current["comparison"]["reviewRequired"])

    def test_duplicate_canonical_id_is_structural_error(self) -> None:
        payload = deepcopy(fixture_payload())
        items = payload["buffs"]["buff_a"]["abilityEventActions"][0]["actions"][0]["actionDataItems"]
        items[1]["offset"] = items[0]["offset"]
        items[1]["bytes"] = items[0]["bytes"]
        items[1]["tag"] = items[0]["tag"]
        report = build_report(payload)
        duplicate = [item for item in report["structureDiagnostics"] if item["kind"] == "duplicate-occurrence-id"]
        self.assertEqual(2, len(duplicate))
        self.assertTrue(all(item["owner"] == "buff_a" for item in duplicate))

    def test_strict_boundary_proof_and_markdown_escaping(self) -> None:
        payload = deepcopy(fixture_payload())
        item = payload["buffs"]["buff_a"]["abilityEventActions"][0]["actions"][0]["actionDataItems"][0]
        item["boundaryProof"] = "heuristic|proof`"
        item["name"] = "Core|A`"
        item["decoded"]["type"] = "Core|A`"
        report = build_report(payload)
        self.assertIn(
            "exact-boundary-proof-invalid",
            {item["kind"] for item in report["structureDiagnostics"]},
        )
        markdown = render_markdown(report)
        self.assertIn("Core\\|A\\`", markdown)

    def test_malformed_roots_and_cli_return_nonzero_after_writing_report(self) -> None:
        variants = []
        malformed = deepcopy(fixture_payload())
        malformed["buffs"] = []
        variants.append((malformed, "invalid-buffs"))
        malformed = deepcopy(fixture_payload())
        malformed["buffs"]["buff_a"]["abilityEventActions"] = ["bad-event"]
        variants.append((malformed, "invalid-event"))
        malformed = deepcopy(fixture_payload())
        malformed["buffs"]["buff_a"]["abilityEventActions"] = [{"actions": "bad-actions"}]
        variants.append((malformed, "invalid-event-actions"))
        malformed = deepcopy(fixture_payload())
        malformed["buffs"]["buff_a"]["abilityEventActions"][0]["actions"] = ["bad-sequence"]
        variants.append((malformed, "invalid-root-sequence"))
        for payload, expected_kind in variants:
            report = build_report(payload)
            self.assertIn(expected_kind, {item["kind"] for item in report["structureDiagnostics"]})

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "malformed.json"
            output = root / "audit.json"
            source.write_text(json.dumps(variants[0][0]), encoding="utf-8")
            self.assertEqual(
                1,
                main(["--input", str(source), "--output", str(output)]),
            )
            self.assertTrue(output.is_file())

    def test_previous_schema_and_language_mismatch_fail_closed_and_cli_nonzero(self) -> None:
        payload = fixture_payload()
        previous = build_report(payload)
        previous["language"] = "EN"
        report = build_report(payload, previous)
        self.assertEqual("error", report["comparison"]["status"])
        self.assertIn("language", report["comparison"]["reason"])
        previous["language"] = "CN"
        previous["schemaVersion"] = "wrong"
        report = build_report(payload, previous)
        self.assertEqual("error", report["comparison"]["status"])
        self.assertIn("schemaVersion", report["comparison"]["reason"])
        previous["schemaVersion"] = "gameplay-recovery-audit.v2"
        previous["occurrences"].append(deepcopy(previous["occurrences"][0]))
        report = build_report(payload, previous)
        self.assertEqual("error", report["comparison"]["status"])
        self.assertIn("duplicate", report["comparison"]["reason"])
        previous["occurrences"].pop()
        previous["occurrences"][0].pop("boundaryProof")
        report = build_report(payload, previous)
        self.assertEqual("error", report["comparison"]["status"])
        self.assertIn("malformed", report["comparison"]["reason"])
        previous["occurrences"][0]["boundaryProof"] = "typed-consumption"
        previous["contentSha256"] = "not-a-sha"
        report = build_report(payload, previous)
        self.assertEqual("error", report["comparison"]["status"])
        self.assertIn("contentSha256", report["comparison"]["reason"])
        previous["contentSha256"] = build_report(payload)["contentSha256"]
        previous["occurrences"][0]["boundaryProof"] = "wrong-proof"
        report = build_report(payload, previous)
        self.assertEqual("error", report["comparison"]["status"])
        self.assertIn("boundaryProof", report["comparison"]["reason"])
        previous["occurrences"][0]["boundaryProof"] = "typed-consumption"
        previous["language"] = "EN"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "current.json"
            previous_path = root / "previous.json"
            output = root / "audit.json"
            source.write_text(json.dumps(payload), encoding="utf-8")
            previous_path.write_text(json.dumps(previous), encoding="utf-8")
            self.assertEqual(
                1,
                main([
                    "--input", str(source), "--previous", str(previous_path),
                    "--output", str(output),
                ]),
            )
            self.assertTrue(output.is_file())

    def test_previous_occurrence_format_validation_fails_closed(self) -> None:
        payload = fixture_payload()
        previous = build_report(payload)
        cases = (
            ("status", "not-a-status"),
            ("decodeStatus", "not-a-status"),
            ("offset", "not-hex"),
            ("bytes", 10),
            ("tag", "not-hex"),
            ("memberCount", 3),
        )
        for field, value in cases:
            with self.subTest(field=field):
                malformed = deepcopy(previous)
                malformed["occurrences"][0][field] = value
                report = build_report(payload, malformed)
                self.assertEqual("error", report["comparison"]["status"])
                self.assertIn("malformed", report["comparison"]["reason"])
                self.assertEqual(field, report["comparison"]["field"])

    def test_malformed_previous_json_writes_error_report_without_traceback(self) -> None:
        payload = fixture_payload()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "current.json"
            previous = root / "previous.json"
            output = root / "audit.json"
            markdown = root / "audit.md"
            source.write_text(json.dumps(payload), encoding="utf-8")
            previous.write_text('{"schemaVersion":', encoding="utf-8")
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                result = main([
                    "--input", str(source), "--previous", str(previous),
                    "--output", str(output), "--markdown-output", str(markdown),
                ])
            self.assertEqual(1, result)
            self.assertTrue(output.is_file())
            self.assertTrue(markdown.is_file())
            report = json.loads(output.read_text(encoding="utf-8"))
            comparison = report["comparison"]
            self.assertEqual("error", comparison["status"])
            self.assertEqual("previous-report-load-failed", comparison["code"])
            self.assertEqual(str(previous), comparison["path"])
            self.assertIn("JSONDecodeError", comparison["actual"])
            self.assertIn("comparison error", stderr.getvalue())
            self.assertIn("previous-report-load-failed", stderr.getvalue())

    def test_comparison_reports_exact_to_partial_new_tag_and_member_count(self) -> None:
        previous_payload = fixture_payload()
        previous_payload["buffs"]["buff_a"]["abilityEventActions"][0]["actions"][0]["actionDataItems"] = [
            action("Core_A", tag="0x0001", offset="0x13", bytes_count=10, member_count=3),
            action("Core_B", tag="0x0002", offset="0x20", bytes_count=11, member_count=3),
        ]
        previous = build_report(previous_payload)
        current = build_report(fixture_payload(), previous)
        kinds = [item["kind"] for item in current["changeDiagnostics"]]
        self.assertIn("status-regression", kinds)
        self.assertIn("new-tag", kinds)
        self.assertIn("new-member-count", kinds)
        self.assertEqual("compared", current["comparison"]["status"])

    def test_old_report_without_occurrences_fails_closed(self) -> None:
        report = build_report(fixture_payload(), {"schemaVersion": 1})
        self.assertEqual("error", report["comparison"]["status"])
        self.assertEqual([], report["changeDiagnostics"])

    def test_markdown_and_cli_outputs_are_stable(self) -> None:
        report = build_report(fixture_payload())
        markdown = render_markdown(report)
        self.assertIn("# Gameplay recovery coverage audit", markdown)
        self.assertIn("Core_A", markdown)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "index.json"
            output = root / "audit.json"
            markdown_output = root / "audit.md"
            source.write_text(json.dumps(fixture_payload()), encoding="utf-8")
            self.assertEqual(
                0,
                main([
                    "--input", str(source),
                    "--output", str(output),
                    "--markdown-output", str(markdown_output),
                ]),
            )
            written = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["histograms"], written["histograms"])
            self.assertEqual(64, len(written["inputSha256"]))
            self.assertTrue(markdown_output.is_file())

    def test_build_gameplay_audit_stage_is_last_and_read_only(self) -> None:
        self.assertEqual("audit", build_gameplay.STAGES[-1])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "lang" / "CN" / "gameplay" / "index.json"
            source.parent.mkdir(parents=True)
            source.write_text(json.dumps(fixture_payload()), encoding="utf-8")
            args = SimpleNamespace(languages=["CN"], audit_scope="active", export_root=None)
            with patch.object(build_gameplay, "WEBUI_DATA_ROOT", root), patch(
                "scripts.gameplay_builder.recovery_audit.main", return_value=0
            ) as audit_main:
                self.assertEqual(0, build_gameplay.run_stage("audit", args))
            audit_main.assert_called_once_with(["--input", str(source)])
            self.assertEqual(json.dumps(fixture_payload()), source.read_text(encoding="utf-8"))
            with patch.object(build_gameplay, "WEBUI_DATA_ROOT", root), patch(
                "scripts.gameplay_builder.recovery_audit.main", return_value=1
            ):
                self.assertEqual(1, build_gameplay.run_stage("audit", args))

    def test_build_gameplay_full_audit_runs_once_for_all_languages(self) -> None:
        args = SimpleNamespace(languages=["CN", "EN"], audit_scope="full", export_root=Path("export"))
        with patch("scripts.gameplay_builder.recovery_audit.main", return_value=0) as audit_main:
            self.assertEqual(0, build_gameplay.run_stage("audit", args))
        audit_main.assert_called_once_with(["--full-corpus", "--export-root", "export"])


if __name__ == "__main__":
    unittest.main()
