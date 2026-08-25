import json
import sys
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import build_secondary_dynamics_simulation_end_golden_vectors as target


class SimulationEndGoldenVectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = target.build_contract()

    def test_executes_all_closed_native_paths(self):
        self.assertEqual(
            [row["name"] for row in self.contract["vectors"]],
            [
                "inactive_bypass",
                "active_unlimited",
                "active_speed_limit",
                "static_friction_accumulation",
                "static_friction_release",
                "static_friction_no_contact_decay",
                "dynamic_friction_attenuation",
                "center_centrifugal_response",
            ],
        )
        self.assertTrue(self.contract["boundary"]["nativeCoreExecuted"])
        self.assertTrue(self.contract["boundary"]["sourceTranscriptionMatched"])

    def test_records_complete_closed_branch_coverage(self):
        self.assertTrue(self.contract["boundary"]["completeKernelGoldenCoverage"])
        self.assertEqual(self.contract["boundary"]["notCovered"], [])
        self.assertIn("static-friction accumulation", self.contract["boundary"]["covered"])
        self.assertIn("static-friction release", self.contract["boundary"]["covered"])
        self.assertIn("static-friction no-contact decay", self.contract["boundary"]["covered"])
        self.assertIn("dynamic-friction attenuation", self.contract["boundary"]["covered"])
        self.assertIn("center centrifugal response", self.contract["boundary"]["covered"])

    def test_pins_core_abi_order(self):
        self.assertEqual(self.contract["abi"]["leadingValue"], "dt float32")
        self.assertEqual(
            self.contract["abi"]["pointerOrder"],
            [
                "stepParticleIndexArray", "teamDataArray", "parameterArray", "centerDataArray",
                "attributes", "vertexDepths", "teamIdArray", "nextPosArray", "oldPosArray",
                "velocityArray", "realVelocityArray", "velocityPosArray", "frictionArray",
                "staticFrictionArray", "collisionNormalArray",
            ],
        )
        self.assertEqual(self.contract["abi"]["trailingValue"], "rangeIndex int32")

    def test_records_mutated_friction_state_bits(self):
        rows = {row["name"]: row for row in self.contract["vectors"]}
        self.assertEqual(
            rows["static_friction_accumulation"]["output"]["staticFrictionBinary32Le"],
            "e17a943e",
        )
        self.assertEqual(
            rows["static_friction_no_contact_decay"]["output"]["staticFrictionBinary32Le"],
            "3333b33e",
        )
        self.assertEqual(
            rows["dynamic_friction_attenuation"]["output"]["frictionBinary32Le"],
            "9a99993e",
        )

    def test_generated_contract_matches(self):
        expected = json.dumps(self.contract, indent=2) + "\n"
        self.assertEqual(target.OUTPUT.read_text(encoding="utf-8"), expected)


if __name__ == "__main__":
    unittest.main()
