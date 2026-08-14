import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from scripts.story_builder.native_contracts import identity_carrier_boundaries as contract
from scripts.story_builder.native_contracts import ifix_patch


class IdentityCarrierBoundariesContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.contract_path = self.root / "contract.json"
        self.contract_path.write_bytes(contract.DEFAULT_CONTRACT.read_bytes())

    @staticmethod
    def native(status: str = "validated") -> SimpleNamespace:
        return SimpleNamespace(status=status, detail=f"native {status}")

    def load(self, native_status: str = "validated") -> dict:
        with (
            mock.patch.object(
                ifix_patch,
                "check_installed_native_inputs",
                return_value=self.native(),
            ),
            mock.patch.object(
                contract,
                "check_installed_native_inputs",
                return_value=self.native(native_status),
            ),
        ):
            return contract.load_identity_carrier_boundaries_contract(
                self.contract_path,
            )

    def test_validated_contract_publishes_all_closed_boundaries(self) -> None:
        audit = self.load()

        self.assertEqual("validated", audit["status"])
        self.assertEqual(
            list(contract.BOUNDARY_IDS),
            [row["id"] for row in audit["boundaries"]],
        )
        self.assertTrue(audit["sourceSha256"])
        self.assertFalse(audit["validationFailures"])
        self.assertTrue(
            all(row["storyBindingsAdded"] == 0 for row in audit["boundaries"])
        )
        self.assertTrue(
            all(row["missionOrderEdgesAdded"] == 0 for row in audit["boundaries"])
        )

    def test_contract_content_drift_fails_closed_with_diagnostic(self) -> None:
        payload = json.loads(self.contract_path.read_text(encoding="utf-8"))
        payload["boundaries"][0]["storyBindingsAdded"] = 1
        self.contract_path.write_text(json.dumps(payload), encoding="utf-8")

        audit = self.load()

        self.assertEqual("mismatched", audit["status"])
        self.assertEqual([], audit["boundaries"])
        failure = next(
            row
            for row in audit["validationFailures"]
            if row["gate"] == "story_bindings_added"
        )
        self.assertEqual([0] * len(contract.BOUNDARY_IDS), failure["expected"])
        self.assertEqual(1, failure["actual"][0])
        self.assertEqual(
            str(self.contract_path.resolve()).replace("\\", "/"),
            failure["sourceFile"],
        )

    def test_installed_build_mismatch_fails_closed(self) -> None:
        audit = self.load("mismatched")

        self.assertEqual("mismatched", audit["status"])
        self.assertEqual([], audit["boundaries"])
        failure = next(
            row
            for row in audit["validationFailures"]
            if row["gate"] == "installed_native_inputs"
        )
        self.assertEqual("validated", failure["expected"]["status"])
        self.assertEqual("mismatched", failure["actual"]["status"])

    def test_shared_ifix_contract_failure_drops_all_boundaries(self) -> None:
        failed_ifix = {
            "status": "missing",
            "sourceFile": "fixture/ifix.json",
            "validationFailures": [{"gate": "read_valid_json"}],
        }
        with (
            mock.patch.object(
                contract,
                "load_ifix_patch_contract",
                return_value=failed_ifix,
            ),
            mock.patch.object(
                contract,
                "check_installed_native_inputs",
                return_value=self.native(),
            ),
        ):
            audit = contract.load_identity_carrier_boundaries_contract(
                self.contract_path,
            )

        self.assertEqual("missing", audit["status"])
        self.assertEqual([], audit["boundaries"])
        failure = next(
            row
            for row in audit["validationFailures"]
            if row["gate"] == "ifix_contract_status"
        )
        self.assertEqual("missing", failure["actual"]["status"])


if __name__ == "__main__":
    unittest.main()
