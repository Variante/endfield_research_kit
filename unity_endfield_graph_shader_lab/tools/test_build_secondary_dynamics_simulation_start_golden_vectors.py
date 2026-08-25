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
                         "base_transform_rotation_slerp",
                         "base_transform_rotation_nlerp",
                         "base_transform_rotation_shortest_arc_sign_flip",
                         "inertia_position_and_velocity_rotation",
                         "damping_and_gravity_prediction", "spring_distance_clamp",
                         "spring_noise", "normal_cone_restriction"):
            self.assertIn(required, names)

    def test_wind_is_fail_closed(self) -> None:
        self.assertTrue(self.payload["windIsolation"]["teamWindDataZeroed"])
        self.assertTrue(self.payload["windIsolation"]["movingWindZeroed"])
        self.assertIn("nonzero wind", self.payload["boundary"]["notCovered"])
        self.assertTrue(self.payload["boundary"]["unityPortExecuted"])
        self.assertEqual(
            "StartSimulationParticleZeroWind; all 13 controlled vectors bit-exact",
            self.payload["boundary"]["unityPortDomain"],
        )
        target = self.payload["endminfOverviewWindRequirement"]
        self.assertEqual(target["postmodelWindZoneCount"], 0)
        self.assertEqual(target["characterInfoEnvironmentWindZoneCount"], 0)
        self.assertFalse(target["targetRequiresNonzeroWind"])

    def test_helpers_are_explicitly_pinned(self) -> None:
        for name, helper in self.payload["directHelpers"].items():
            self.assertEqual(64, len(helper["sha256"]))
            if name == "quaternionSlerpSin":
                self.assertFalse(helper["usedBySourceTranscription"])
                self.assertEqual("standalone bounded-path transcription", helper["sourceBoundary"])
            else:
                self.assertTrue(helper["usedBySourceTranscription"])

    def test_shortest_arc_sign_flip_matches_positive_representation(self) -> None:
        rows = {row["name"]: row for row in self.payload["vectors"]}
        positive = rows["base_transform_rotation_slerp"]["output"]
        flipped = rows["base_transform_rotation_shortest_arc_sign_flip"]["output"]
        self.assertEqual(positive["baseRotBinary32Le"], flipped["baseRotBinary32Le"])
        self.assertEqual(positive["stepBasicRotationBinary32Le"],
                         flipped["stepBasicRotationBinary32Le"])

    def test_nonidentity_rotation_boundary_is_closed(self) -> None:
        boundary = self.payload["boundary"]
        self.assertNotIn("non-identity quaternion interpolation", boundary["notCovered"])
        self.assertIn("center step/inertia quaternion interpolation and rotated position/velocity",
                      boundary["covered"])

    def test_generated_file_matches(self) -> None:
        expected = json.dumps(self.payload, indent=2) + "\n"
        self.assertEqual(expected, MODULE.OUTPUT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
