from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from scripts import build_mission_pipeline_data as pipeline
from scripts.story_builder import dialog_tree_control_flow
from scripts.story_builder.native_contracts import ifix_patch


ROOT = Path(__file__).resolve().parents[2]


class IfixPatchContractTests(unittest.TestCase):
    @staticmethod
    def native(status: str = "validated") -> SimpleNamespace:
        return SimpleNamespace(status=status, detail=f"fixture {status}")

    def load(self, path: Path = ifix_patch.DEFAULT_CONTRACT, status: str = "validated") -> dict:
        with mock.patch.object(
            ifix_patch,
            "check_installed_native_inputs",
            return_value=self.native(status),
        ):
            return ifix_patch.load_ifix_patch_contract(path)

    def test_tracked_contract_validates_all_production_facts(self) -> None:
        audit = self.load()

        self.assertEqual("validated", audit["status"])
        self.assertEqual(30, len(audit["fixedMethodSignatures"]))
        self.assertEqual(ifix_patch.PATCH_SHA256, audit["source"]["patchSha256"])
        self.assertEqual([], audit["validationFailures"])
        self.assertEqual(
            "scripts/story_builder/native_contracts/ifix_patch.json",
            audit["sourceFile"],
        )

    def test_clean_clone_missing_contract_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            audit = self.load(Path(temporary) / "missing.json")

        self.assertEqual("missing", audit["status"])
        self.assertNotIn("fixedMethodSignatures", audit)
        self.assertEqual("read_valid_json", audit["validationFailures"][0]["gate"])

    def test_malformed_contract_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "ifix.json"
            path.write_text("{", encoding="utf-8")
            audit = self.load(path)

        self.assertEqual("mismatched", audit["status"])
        self.assertEqual("read_valid_json", audit["validationFailures"][0]["gate"])

    def test_signature_drift_fails_with_exact_hash_gate(self) -> None:
        payload = json.loads(ifix_patch.DEFAULT_CONTRACT.read_text(encoding="utf-8"))
        payload["fixedMethodSignatures"][0] += " drift"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "ifix.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            audit = self.load(path)

        self.assertEqual("mismatched", audit["status"])
        failures = {row["gate"]: row for row in audit["validationFailures"]}
        self.assertIn("fixed_signatures_sha256", failures)
        self.assertEqual(
            ifix_patch.FIXED_SIGNATURES_SHA256,
            failures["fixed_signatures_sha256"]["expected"],
        )

    def test_installed_native_mismatch_drops_all_patch_facts(self) -> None:
        audit = self.load(status="mismatched")

        self.assertEqual("mismatched", audit["status"])
        self.assertNotIn("source", audit)
        self.assertEqual(
            "installed_native_inputs",
            audit["validationFailures"][0]["gate"],
        )

    def test_dialog_gate_rejects_missing_malformed_and_relevant_fix(self) -> None:
        source = Path("fixture/ifix_patch.json")
        for status in ("missing", "mismatched"):
            with self.subTest(status=status):
                with self.assertRaisesRegex(
                    dialog_tree_control_flow.ContractError,
                    "gate=current_ifix_contract",
                ):
                    dialog_tree_control_flow._validated_current_ifix_evidence(
                        {
                            "status": status,
                            "validationFailures": [{
                                "gate": "read_valid_json",
                                "sourceFile": str(source),
                            }],
                        },
                        relevant_prefixes={"Game.Node::DoAction("},
                        source=source,
                    )

        audit = self.load()
        audit = copy.deepcopy(audit)
        audit["fixedMethodSignatures"].append("Game.Node::DoAction()")
        with self.assertRaisesRegex(
            dialog_tree_control_flow.ContractError,
            "gate=current_ifix_exclusion",
        ):
            dialog_tree_control_flow._validated_current_ifix_evidence(
                audit,
                relevant_prefixes={"Game.Node::DoAction("},
                source=source,
            )

    def test_dialog_projection_preserves_current_shape_with_tracked_source(self) -> None:
        evidence = dialog_tree_control_flow._validated_current_ifix_evidence(
            self.load(),
            relevant_prefixes={"Game.Node::DoAction("},
            source=ifix_patch.DEFAULT_CONTRACT,
        )

        self.assertEqual("audited", evidence["status"])
        self.assertEqual(30, evidence["fixedMethodCount"])
        self.assertEqual([], evidence["relevantFixedMethods"])
        self.assertEqual(
            "scripts/story_builder/native_contracts/ifix_patch.json",
            evidence["reportFile"],
        )

    def test_mission_pipeline_projects_all_three_consumers(self) -> None:
        runtime = pipeline.project_ifix_runtime_contract(
            pipeline.RUNTIME_CONTRACT,
            self.load(),
        )

        server = runtime["serverPlaceholder"]["installedPatch"]
        protobuf = runtime["protobufIdentityCarrierAudit"]["installedPatch"]
        air_wall = runtime["airWallMissionRadioContext"]["installedPatch"]
        self.assertEqual(30, server["signatureTargetCount"])
        self.assertEqual(0, server["taskCompletionTargetMatches"])
        self.assertEqual(2, server["missionHudTargets"])
        self.assertEqual(7, server["dialogCinematicTargets"])
        self.assertEqual(
            "scripts/story_builder/native_contracts/ifix_patch.json",
            server["auditReport"],
        )
        self.assertEqual(0, protobuf["matchedMethods"])
        self.assertEqual(0, air_wall["matchedAirWallMethods"])

    def test_mission_pipeline_does_not_publish_stale_facts_on_failure(self) -> None:
        runtime = pipeline.project_ifix_runtime_contract(
            pipeline.RUNTIME_CONTRACT,
            {
                "status": "missing",
                "sourceFile": "fixture/missing.json",
                "sourceSha256": "",
                "validationFailures": [{"gate": "read_valid_json"}],
            },
        )

        for key in (
            "serverPlaceholder",
            "protobufIdentityCarrierAudit",
            "airWallMissionRadioContext",
        ):
            patch_row = runtime[key]["installedPatch"]
            self.assertEqual("missing", patch_row["status"])
            self.assertNotIn("sha256", patch_row)
            self.assertNotIn("signatureTargetCount", patch_row)

    def test_both_supported_package_identities_import(self) -> None:
        cases = (
            ("scripts.story_builder.native_contracts.ifix_patch", None),
            ("story_builder.native_contracts.ifix_patch", str(ROOT / "scripts")),
        )
        for module, pythonpath in cases:
            env = os.environ.copy()
            if pythonpath is None:
                env.pop("PYTHONPATH", None)
            else:
                env["PYTHONPATH"] = pythonpath
            result = subprocess.run(
                [sys.executable, "-c", f"import {module}; print({module}.SCHEMA)"],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(ifix_patch.SCHEMA, result.stdout.strip())


if __name__ == "__main__":
    unittest.main()
