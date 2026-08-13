from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.common import InstalledNativeInputs
from scripts.story_builder.native_contracts import teleport_param


class TeleportParamContractTests(unittest.TestCase):
    def test_default_contract_projects_the_reviewed_carrier(self):
        contract = teleport_param.load_teleport_param_contract()

        self.assertEqual("validated", contract["validation"]["status"])
        self.assertEqual("Beyond.Gameplay.TeleportParam", contract["type"])
        self.assertEqual("0x38", contract["size"])
        self.assertEqual("0x28", contract["layout"]["actionId"])
        self.assertEqual(15, contract["metadataSignatureMethodCount"])
        self.assertEqual(10, contract["containerPathCount"])
        self.assertEqual(23, contract["focusFieldAccessCount"])
        self.assertEqual(
            ["levelScriptId", "actionId"],
            [row["field"] for row in contract["loadFinishConsumerAccesses"]],
        )
        self.assertEqual(0, contract["storyBindingsAdded"])

    def test_layout_drift_fails_closed_with_actionable_diagnostic(self):
        payload = json.loads(teleport_param.DEFAULT_CONTRACT.read_text("utf-8"))
        payload["carrier"]["layout"]["actionId"] = "0x30"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "teleport_param.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            contract = teleport_param.load_teleport_param_contract(path)

        self.assertEqual("mismatched", contract["validation"]["status"])
        self.assertNotIn("layout", contract)
        failure = next(
            row for row in contract["validation"]["failures"]
            if row["gate"] == "runtime_field_layout"
        )
        self.assertEqual("teleportParamNativeContract", failure["validator"])
        self.assertEqual("0x28", failure["expected"]["actionId"])
        self.assertEqual("0x30", failure["actual"]["actionId"])

    def test_installed_native_drift_fails_closed(self):
        native = InstalledNativeInputs(
            status="mismatched",
            gameassembly=Path("GameAssembly.dll"),
            metadata=Path("global-metadata.dat"),
            gameassembly_sha256="BAD",
            metadata_sha256="BAD",
            detail="test drift",
        )
        with patch.object(
            teleport_param, "check_installed_native_inputs", return_value=native
        ):
            contract = teleport_param.load_teleport_param_contract()

        self.assertEqual("mismatched", contract["validation"]["status"])
        self.assertEqual([], contract["relatedOriginalFiles"])
        failure = contract["validation"]["failures"][-1]
        self.assertEqual("installed_native_inputs", failure["gate"])

    def test_generic_audit_reconciliation_is_exact_and_reports_drift(self):
        contract = json.loads(
            teleport_param.DEFAULT_CONTRACT.read_text(encoding="utf-8-sig")
        )
        old_report = {
            "schema": contract["auditSchema"],
            "validation": {"status": "validated", "failures": []},
            "source": contract["sources"],
            "carrier": {
                "type": contract["carrier"]["type"],
                "nativeSize": contract["carrier"]["nativeSize"],
                "fields": [
                    {"name": name, "offset": offset}
                    for name, offset in contract["carrier"]["layout"].items()
                ],
            },
            "summary": contract["counts"].copy(),
            "directCallsites": [
                {
                    "targets": [{"type": key.rsplit(".", 1)[0], "method": key.rsplit(".", 1)[1]}]
                }
                for key, count in contract["directCallerCensus"].items()
                for _ in range(count)
            ],
            "focusFieldSummary": contract["focusFieldSummary"],
            "fieldAccesses": contract["loadFinishConsumerAccesses"],
        }
        self.assertEqual(
            [], teleport_param.reconcile_generic_audit(old_report, contract)
        )

        old_report["summary"]["containerPaths"] = 9
        failures = teleport_param.reconcile_generic_audit(old_report, contract)
        self.assertEqual("counts", failures[0]["gate"])


if __name__ == "__main__":
    unittest.main()
