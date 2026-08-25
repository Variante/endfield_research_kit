import json
import sys
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import build_secondary_dynamics_distance_semantics_contract as target


class DistanceSemanticsContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = target.build_contract()

    def test_pins_call_free_mixed_precision_core(self):
        self.assertEqual(self.contract["core"]["rva"], "0x321ef0")
        self.assertEqual(self.contract["core"]["bytes"], 1624)
        self.assertEqual(self.contract["core"]["directCallCount"], 0)
        self.assertEqual(self.contract["arguments"][7]["strideBytes"], 24)
        self.assertEqual(self.contract["precision"]["positionAndCorrectionDomain"], "binary64")

    def test_pins_two_identical_passes_but_keeps_runtime_gated(self):
        self.assertEqual(self.contract["schedule"]["passCountPerSubstep"], 2)
        self.assertTrue(self.contract["schedule"]["sameKernelAndEquations"])
        boundary = self.contract["implementationBoundary"]
        self.assertTrue(boundary["equationsClosed"])
        self.assertTrue(boundary["goldenVectorsCaptured"])
        self.assertFalse(boundary["solverImplemented"])

    def test_generated_contract_matches(self):
        expected = json.dumps(self.contract, indent=2) + "\n"
        self.assertEqual(target.OUTPUT.read_text(encoding="utf-8"), expected)


if __name__ == "__main__":
    unittest.main()
