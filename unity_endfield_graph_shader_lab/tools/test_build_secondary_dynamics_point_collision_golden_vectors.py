import json
import sys
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import build_secondary_dynamics_point_collision_golden_vectors as target


class PointCollisionGoldenVectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = target.build_contract()

    def test_executes_native_core_and_matches_source_port(self):
        boundary = self.contract["boundary"]
        self.assertTrue(boundary["nativeCoreExecuted"])
        self.assertTrue(boundary["sourceTranscriptionExactBitsMatched"])
        self.assertTrue(boundary["rangeIndexPassedByValue"])
        self.assertEqual(len(self.contract["vectors"]), 6)

    def test_required_cases_are_present(self):
        names = {row["name"] for row in self.contract["vectors"]}
        self.assertEqual(names, {case["name"] for case in target.CASES})

    def test_no_contact_writes_zero_normal(self):
        row = next(row for row in self.contract["vectors"] if row["name"] == "no_contact_normal_zero")
        self.assertEqual(row["output"]["collisionNormalBinary32Le"], ["00000000"] * 3)
        self.assertEqual(row["output"]["frictionBinary32Le"], "00000000")

    def test_near_contact_increases_friction_without_projection(self):
        row = next(row for row in self.contract["vectors"] if row["name"] == "friction_near_contact")
        self.assertEqual(row["output"]["next"], row["input"]["particle"])
        self.assertGreater(row["output"]["friction"], 0.0)
        self.assertEqual(row["output"]["collisionNormal"], [1.0, 0.0, 0.0])

    def test_generated_contract_matches(self):
        expected = json.dumps(self.contract, indent=2) + "\n"
        self.assertEqual(target.OUTPUT.read_text(encoding="utf-8"), expected)


if __name__ == "__main__":
    unittest.main()
