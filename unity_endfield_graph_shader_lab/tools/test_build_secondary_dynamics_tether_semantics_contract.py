import json
import sys
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import build_secondary_dynamics_tether_semantics_contract as target


class TetherSemanticsContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = target.build_contract()

    def test_pins_call_free_core_and_double3_state(self):
        self.assertEqual(self.contract["core"]["rva"], "0x29f7d0")
        self.assertEqual(self.contract["core"]["bytes"], 648)
        self.assertEqual(self.contract["core"]["directCallCount"], 0)
        self.assertEqual(self.contract["arguments"][8]["strideBytes"], 24)

    def test_closes_projection_but_keeps_runtime_gated(self):
        boundary = self.contract["implementationBoundary"]
        self.assertTrue(boundary["equationsClosed"])
        self.assertFalse(boundary["helperGap"])
        self.assertTrue(boundary["goldenVectorsCaptured"])
        self.assertTrue(boundary["solverImplemented"])
        self.assertFalse(boundary["solverConnectedToRuntime"])

    def test_generated_contract_matches(self):
        expected = json.dumps(self.contract, indent=2) + "\n"
        self.assertEqual(target.OUTPUT.read_text(encoding="utf-8"), expected)


if __name__ == "__main__":
    unittest.main()
