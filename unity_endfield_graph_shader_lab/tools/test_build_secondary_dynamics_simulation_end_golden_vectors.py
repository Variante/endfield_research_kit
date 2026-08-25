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

    def test_executes_three_bounded_native_paths(self):
        self.assertEqual(len(self.contract["vectors"]), 3)
        self.assertTrue(self.contract["boundary"]["nativeCoreExecuted"])
        self.assertTrue(self.contract["boundary"]["sourceTranscriptionMatched"])

    def test_records_remaining_branch_gap(self):
        self.assertFalse(self.contract["boundary"]["completeKernelGoldenCoverage"])
        self.assertIn("static friction", self.contract["boundary"]["notCovered"])

    def test_generated_contract_matches(self):
        expected = json.dumps(self.contract, indent=2) + "\n"
        self.assertEqual(target.OUTPUT.read_text(encoding="utf-8"), expected)


if __name__ == "__main__":
    unittest.main()
