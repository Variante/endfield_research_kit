#!/usr/bin/env python3
"""Focused tests for the combined concrete-slot/generic-size boundary."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(TOOLS_ROOT))

import verify_secondary_dynamics_concrete_slots as verifier


class SecondaryDynamicsConcreteSlotTests(unittest.TestCase):
    def _contracts(self) -> tuple[dict, dict]:
        job = json.loads(verifier.JOB_OUTPUT.read_text(encoding="utf-8"))
        inner = json.loads(verifier.INNER_OUTPUT.read_text(encoding="utf-8"))
        return job, inner

    def test_published_contracts_join_at_concrete_slot_boundary(self) -> None:
        job, inner = self._contracts()
        result = verifier._validate_combined(job, inner)
        self.assertEqual(result["status"], "validated")
        self.assertEqual(result["concreteSlotWidthsBytes"], {
            "NativeArray": 16,
            "NativeReference": 16,
        })
        self.assertEqual(result["genericSizeStatus"], "unresolved_lower_bound_only")
        self.assertEqual(result["genericLowerBoundsBytes"], {
            "NativeArray": 16,
            "NativeReference": 12,
        })

    def test_width_drift_is_rejected_without_promoting_generic_size(self) -> None:
        job, inner = self._contracts()
        drifted = copy.deepcopy(job)
        row = next(
            field for field in drifted["jobs"][0]["fields"]
            if field["kind"] == "NativeArray"
        )
        row["slotWidthBytes"] = 24
        with self.assertRaisesRegex(verifier.ContractError, "width/span drift"):
            verifier._validate_combined(drifted, inner)

    def test_generic_size_claim_is_rejected(self) -> None:
        job, inner = self._contracts()
        drifted = copy.deepcopy(inner)
        drifted["nativeArray"]["nativeSizeBytes"] = 16
        with self.assertRaisesRegex(verifier.ContractError, "generic native size is unexpectedly closed"):
            verifier._validate_combined(job, drifted)


if __name__ == "__main__":
    unittest.main()
