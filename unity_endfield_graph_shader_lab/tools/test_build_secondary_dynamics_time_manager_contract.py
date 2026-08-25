from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import build_secondary_dynamics_time_manager_contract as builder


class SecondaryDynamicsTimeManagerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = builder.build_contract()

    def test_default_step_scalars_are_closed(self) -> None:
        self.assertEqual(
            self.payload["status"],
            "retail_default_step_scalars_closed_nondefault_power_helper_unported",
        )
        self.assertEqual(self.payload["constructorDefaults"], {
            "simulationFrequency": 90,
            "maxSimulationCountPerFrame": 3,
            "GlobalTimeScale": 1.0,
        })
        self.assertEqual(
            self.payload["frameUpdate"]["retailDefault"]["SimulationPower"],
            [1.0, 1.0, 1.0, 1.0],
        )

    def test_methods_and_field_offsets_are_pinned(self) -> None:
        self.assertEqual(len(self.payload["methods"]), 8)
        self.assertEqual(self.payload["fieldOffsets"]["SimulationPower"], "0x30")
        self.assertEqual(self.payload["callbacks"]["AfterFixedUpdate"], "FixedUpdateCount += 1")
        self.assertEqual(self.payload["callbacks"]["AfterRenderring"], "FixedUpdateCount = 0")

    def test_open_boundaries_remain_fail_closed(self) -> None:
        boundary = self.payload["implementationBoundary"]
        self.assertTrue(boundary["retailDefaultStepScalarsClosed"])
        self.assertFalse(boundary["nondefaultScalarPowerHelperPorted"])
        self.assertFalse(boundary["simulationSubstepAccumulatorClosed"])
        self.assertFalse(boundary["solverWritebackEnabled"])
        self.assertFalse(boundary["visualVerificationPerformed"])

    def test_generated_contract_matches_builder(self) -> None:
        path = builder.DEFAULT_OUTPUT
        if not path.exists():
            self.skipTest("generated contract has not been published yet")
        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), self.payload)


if __name__ == "__main__":
    unittest.main()
