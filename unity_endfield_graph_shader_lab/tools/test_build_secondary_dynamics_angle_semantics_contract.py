import json
import sys
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import build_secondary_dynamics_angle_semantics_contract as target


class AngleSemanticsContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = target.build_contract()

    def test_pins_full_core_and_helpers(self):
        self.assertEqual(self.contract["spans"]["core"]["bytes"], 6480)
        self.assertEqual(self.contract["spans"]["sincos"]["rva"], "0x1e5d30")
        self.assertEqual(self.contract["shared"]["sweeps"], 3)

    def test_endminf_activation_is_narrowed(self):
        self.assertEqual(len(self.contract["endminf"]["restorationOwners"]), 4)
        self.assertEqual(self.contract["endminf"]["limitOwners"], ["Hair"])

    def test_remains_runtime_gated(self):
        boundary = self.contract["implementationBoundary"]
        self.assertTrue(boundary["equationsClosed"])
        self.assertTrue(boundary["goldenVectorsCaptured"])
        self.assertTrue(boundary["helperGap"])
        self.assertFalse(boundary["solverImplemented"])

    def test_generated_contract_matches(self):
        expected = json.dumps(self.contract, indent=2) + "\n"
        self.assertEqual(target.OUTPUT.read_text(encoding="utf-8"), expected)


if __name__ == "__main__":
    unittest.main()
