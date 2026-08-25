#!/usr/bin/env python3

import importlib.util
import json
import sys
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
SPEC = importlib.util.spec_from_file_location(
    "simulation_start_vectors", TOOLS / "build_secondary_dynamics_simulation_start_golden_vectors.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class SimulationStartGoldenVectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = MODULE.build_contract()

    def test_pinned_core_and_abi(self) -> None:
        self.assertEqual("0x25e830", self.payload["core"]["rva"])
        self.assertEqual(5074, self.payload["core"]["bytes"])
        self.assertEqual(23, len(self.payload["abi"]["pointerOrder"]))
        self.assertEqual("rangeIndex int32", self.payload["abi"]["trailingValue"])

    def test_requested_controlled_coverage(self) -> None:
        names = {row["name"] for row in self.payload["vectors"]}
        self.assertEqual({raw["name"] for raw in MODULE.CASES}, names)
        for required in ("inactive_bypass", "base_transform_interpolation",
                         "damping_and_gravity_prediction", "spring_distance_clamp",
                         "spring_noise", "normal_cone_restriction"):
            self.assertIn(required, names)

    def test_wind_is_fail_closed(self) -> None:
        self.assertTrue(self.payload["windIsolation"]["teamWindDataZeroed"])
        self.assertTrue(self.payload["windIsolation"]["movingWindZeroed"])
        self.assertIn("nonzero wind", self.payload["boundary"]["notCovered"])

    def test_helpers_are_explicitly_pinned(self) -> None:
        for helper in self.payload["directHelpers"].values():
            self.assertTrue(helper["usedBySourceTranscription"])
            self.assertEqual(64, len(helper["sha256"]))

    def test_generated_file_matches(self) -> None:
        expected = json.dumps(self.payload, indent=2) + "\n"
        self.assertEqual(expected, MODULE.OUTPUT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
