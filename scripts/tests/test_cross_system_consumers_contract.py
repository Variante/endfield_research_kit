import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.common import InstalledNativeInputs
from scripts.story_builder.native_contracts import cross_system_consumers as contract


class CrossSystemConsumersContractTests(unittest.TestCase):
    def test_current_contract_preserves_every_reviewed_row(self):
        payload = json.loads(contract.DEFAULT_CONTRACT.read_text(encoding="utf-8"))

        self.assertEqual(contract.validate_cross_system_consumers(
            payload, str(contract.DEFAULT_CONTRACT)
        ), [])
        with patch.object(
            contract,
            "check_installed_native_inputs",
            return_value=InstalledNativeInputs(
                Path("game"), Path("metadata"), "a" * 64, "b" * 64,
                "validated", "fixture",
            ),
        ):
            projected = contract.load_cross_system_consumers_contract()

        self.assertEqual(projected["status"], "validated")
        self.assertEqual(projected["rows"], payload["rows"])
        self.assertEqual(
            projected["deferredRefreshClosure"], payload["deferredRefreshClosure"]
        )
        self.assertEqual(
            projected["missionRuntimeSurface"], payload["missionRuntimeSurface"]
        )
        self.assertEqual(
            projected["managedCallableSurface"], payload["managedCallableSurface"]
        )

    def test_contract_fails_closed_on_row_classification_drift(self):
        payload = json.loads(contract.DEFAULT_CONTRACT.read_text(encoding="utf-8"))
        payload["rows"][0]["classification"] = "unreviewed_cross_system_call_shape"
        failures = contract.validate_cross_system_consumers(payload, "fixture.json")

        self.assertEqual(failures[0]["gate"], "row_classification_counts")
        self.assertEqual(failures[0]["sourceFile"], "fixture.json")
        self.assertEqual(failures[0]["expected"], contract.EXPECTED_CLASS_COUNTS)

    def test_contract_fails_closed_on_installed_build_mismatch(self):
        with patch.object(
            contract,
            "check_installed_native_inputs",
            return_value=InstalledNativeInputs(
                Path("game"), Path("metadata"), "a" * 64, "b" * 64,
                "mismatched", "fixture mismatch",
            ),
        ):
            result = contract.load_cross_system_consumers_contract()

        self.assertEqual(result["status"], "mismatched")
        self.assertEqual(result["finding"], "")
        self.assertNotIn("rows", result)
        self.assertEqual(
            result["validationFailures"][0]["gate"], "installed_native_inputs"
        )

    def test_contract_fails_closed_on_missing_or_invalid_profile(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "profile.json"
            with patch.object(
                contract,
                "check_installed_native_inputs",
                return_value=InstalledNativeInputs(
                    Path("game"), Path("metadata"), "a" * 64, "b" * 64,
                    "validated", "fixture",
                ),
            ):
                missing = contract.load_cross_system_consumers_contract(path)
                path.write_text("[]", encoding="utf-8")
                invalid = contract.load_cross_system_consumers_contract(path)

        self.assertEqual(missing["status"], "missing")
        self.assertEqual(invalid["status"], "mismatched")
        self.assertEqual(missing["validationFailures"][0]["gate"], "read_valid_json")
        self.assertEqual(invalid["validationFailures"][0]["gate"], "read_valid_json")


if __name__ == "__main__":
    unittest.main()
