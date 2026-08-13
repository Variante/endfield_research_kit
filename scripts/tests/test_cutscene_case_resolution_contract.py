from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts import build_mission_pipeline_data as pipeline
from scripts.story_builder.native_contracts import cutscene_case_resolution


class CutsceneCaseResolutionContractTests(unittest.TestCase):
    def _native(self, status: str = "validated") -> SimpleNamespace:
        return SimpleNamespace(status=status, detail=f"fixture {status}")

    def test_current_contract_validates_and_matches_only_the_reviewed_row(self) -> None:
        with patch.object(
            cutscene_case_resolution,
            "check_installed_native_inputs",
            return_value=self._native(),
        ):
            audit = cutscene_case_resolution.load_cutscene_case_resolution_contract()

        self.assertEqual("validated", audit["status"])
        row = dict(audit["nativeContract"]["luaPlayback"])
        self.assertTrue(
            cutscene_case_resolution.matches_reviewed_lua_playback(row, audit)
        )
        row["line"] += 1
        self.assertFalse(
            cutscene_case_resolution.matches_reviewed_lua_playback(row, audit)
        )

    def test_contract_drift_fails_closed_with_a_bounded_gate(self) -> None:
        payload = json.loads(
            cutscene_case_resolution.DEFAULT_CONTRACT.read_text(encoding="utf-8")
        )
        payload["conclusion"]["caseResolution"] = "case_insensitive"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "contract.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with patch.object(
                cutscene_case_resolution,
                "check_installed_native_inputs",
                return_value=self._native(),
            ):
                audit = (
                    cutscene_case_resolution.load_cutscene_case_resolution_contract(
                        path
                    )
                )

        self.assertEqual("mismatched", audit["status"])
        self.assertEqual({}, audit["nativeContract"])
        failure = audit["validationFailures"][0]
        self.assertEqual("case_resolution", failure["gate"])
        self.assertEqual("case_sensitive", failure["expected"])
        self.assertEqual("case_insensitive", failure["actual"])

    def test_installed_build_drift_drops_the_rejection_rule(self) -> None:
        with patch.object(
            cutscene_case_resolution,
            "check_installed_native_inputs",
            return_value=self._native("mismatched"),
        ):
            audit = cutscene_case_resolution.load_cutscene_case_resolution_contract()

        self.assertEqual("mismatched", audit["status"])
        self.assertEqual({}, audit["nativeContract"])
        self.assertEqual(
            "installed_native_inputs",
            audit["validationFailures"][0]["gate"],
        )

    def test_pipeline_keeps_contract_failure_and_does_not_classify_rejection(self) -> None:
        row = json.loads(
            cutscene_case_resolution.DEFAULT_CONTRACT.read_text(encoding="utf-8")
        )["luaPlayback"]
        row.update({
            "classification": "story_playback",
            "playbackKind": "cutscene",
            "argumentSemantics": "story_id",
            "playbackRole": "authored_reference",
            "firstArgument": "EnterCutsceneId",
            "literalResolution": "module_constant",
            "nearbyTables": [],
            "tableFieldResolution": None,
        })
        invalid_audit = {
            "schema": cutscene_case_resolution.AUDIT_SCHEMA,
            "status": "mismatched",
            "sourceFile": "fixture/case-contract.json",
            "sourceSha256": "a" * 64,
            "nativeContract": {},
            "validationFailures": [{
                "validator": "cutsceneCaseResolutionNativeContract",
                "gate": "installed_native_inputs",
                "sourceFile": "fixture/GameAssembly.dll",
                "expected": {"status": "validated"},
                "actual": {"status": "mismatched"},
            }],
        }
        with tempfile.TemporaryDirectory() as temporary:
            audit_path = Path(temporary) / "lua.json"
            audit_path.write_text(json.dumps({
                "schemaVersion": pipeline.LUA_CONSUMER_REFERENCE_SCHEMA,
                "summary": {"readErrorCount": 0},
                "gameActionAudit": {"storyPlaybackCalls": [row]},
            }), encoding="utf-8")
            evidence = pipeline.load_lua_story_playback_evidence(
                audit_path,
                case_resolution_contract_audit=invalid_audit,
            )

        self.assertEqual([], evidence["rejectedCaseMismatchCalls"])
        self.assertEqual(1, evidence["unresolvedPlaybackCalls"])
        self.assertEqual(
            "installed_native_inputs",
            evidence["caseResolutionContract"]["validationFailures"][0]["gate"],
        )


if __name__ == "__main__":
    unittest.main()
