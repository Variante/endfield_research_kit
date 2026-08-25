import json
import sys
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import build_secondary_dynamics_collider_end_semantics_contract as target


class ColliderEndSemanticsContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = target.build_contract()

    def test_pins_transform_snapshot_core(self):
        self.assertEqual(self.contract["core"]["rva"], "0x24a1a0")
        self.assertEqual(self.contract["core"]["bytes"], 117)
        self.assertTrue(self.contract["implementationBoundary"]["equationsClosed"])

    def test_rejects_contact_solver_classification(self):
        self.assertFalse(self.contract["implementationBoundary"]["contactProducer"])
        self.assertIn("collisionNormal", self.contract["nonAccesses"])

    def test_generated_contract_matches(self):
        expected = json.dumps(self.contract, indent=2) + "\n"
        self.assertEqual(target.OUTPUT.read_text(encoding="utf-8"), expected)


if __name__ == "__main__":
    unittest.main()
