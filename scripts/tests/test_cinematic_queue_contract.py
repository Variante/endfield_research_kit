from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from scripts.story_builder.native_contracts import cinematic_queue as contract


class CinematicQueueNativeContractTests(unittest.TestCase):
    def read_contract(self) -> dict:
        return json.loads(contract.DEFAULT_CONTRACT.read_text(encoding="utf-8"))

    def validated_native_inputs(self) -> SimpleNamespace:
        return SimpleNamespace(status="validated", detail="")

    def test_checked_in_contract_projects_complete_production_facts(self) -> None:
        with mock.patch.object(
            contract,
            "check_installed_native_inputs",
            return_value=self.validated_native_inputs(),
        ):
            projected = contract.load_cinematic_queue_contract()

        self.assertEqual("validated", projected["status"])
        self.assertEqual(contract.EXPECTED_DISPATCHERS, projected["dispatcherMethods"])
        self.assertEqual(16, len(projected["actionProducerRoutes"]))
        self.assertEqual(10, projected["nativeProducerCount"])
        self.assertEqual(
            "scripts/story_builder/native_contracts/cinematic_queue.json",
            projected["report"],
        )

    def test_contract_drift_fails_closed_with_named_gate(self) -> None:
        payload = self.read_contract()
        payload["actionProducerRoutes"][0]["producerMethod"] = "DriftedProducer"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "cinematic_queue.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with mock.patch.object(
                contract,
                "check_installed_native_inputs",
                return_value=self.validated_native_inputs(),
            ):
                projected = contract.load_cinematic_queue_contract(path)

        self.assertEqual("mismatched", projected["status"])
        self.assertEqual(
            "action_producer_routes_sha256",
            projected["validationFailures"][0]["gate"],
        )

    def test_installed_build_mismatch_fails_closed(self) -> None:
        native = SimpleNamespace(status="mismatched", detail="fixture build drift")
        with mock.patch.object(
            contract,
            "check_installed_native_inputs",
            return_value=native,
        ):
            projected = contract.load_cinematic_queue_contract()

        self.assertEqual("mismatched", projected["status"])
        self.assertEqual(
            "installed_native_inputs",
            projected["validationFailures"][0]["gate"],
        )

    def test_recovery_projection_reconciles_every_retained_fact(self) -> None:
        reviewed = self.read_contract()
        counts = reviewed["counts"]
        recovery_audit = {
            "schemaVersion": contract.RECOVERY_AUDIT_SCHEMA,
            "source": {
                "gameAssemblySha256": reviewed["sources"]["gameAssemblySha256"],
                "metadataSha256": reviewed["sources"]["globalMetadataSha256"],
            },
            "summary": {
                "payloadTypeCount": counts["payloadTypes"],
                "nativeDispatcherCount": counts["nativeDispatchers"],
                "enqueueEdgeCount": counts["enqueueEdges"],
                "nativeProducerCount": counts["nativeProducers"],
                "typedActionProducerRouteCount": counts["typedActionProducerRoutes"],
                "typedActionProducerTypeCount": counts["typedActionProducerTypes"],
            },
            "contract": {
                "queueBase": {"type": reviewed["queueBaseType"]},
                "queueHandle": {"type": reviewed["queueHandleType"]},
                "nativeDispatcherMethods": reviewed["dispatcherMethods"],
                "actionProducerRoutes": reviewed["actionProducerRoutes"],
            },
            "conclusion": reviewed["conclusion"],
        }

        self.assertEqual([], contract.reconcile_runtime_audit(recovery_audit, reviewed))
        recovery_audit["summary"]["nativeProducerCount"] += 1
        failures = contract.reconcile_runtime_audit(recovery_audit, reviewed)
        self.assertEqual("counts", failures[0]["gate"])


if __name__ == "__main__":
    unittest.main()
