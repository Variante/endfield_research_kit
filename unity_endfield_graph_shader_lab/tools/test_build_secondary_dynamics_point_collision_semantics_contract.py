import json
import sys
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import build_secondary_dynamics_point_collision_semantics_contract as target


class PointCollisionSemanticsContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = target.build_contract()

    def test_pins_point_core_and_work_data(self):
        self.assertEqual(self.contract["kernels"]["point"]["rva"], "0x2fcda0")
        self.assertEqual(self.contract["collider"]["workData"]["strideBytes"], 184)
        self.assertTrue(self.contract["kernels"]["point"]["capsuleRoutineInline"])

    def test_excludes_edge_for_every_endminf_owner(self):
        boundary = self.contract["modeBoundary"]
        self.assertEqual(set(boundary["endminfAuthoredModes"].values()), {1})
        self.assertEqual(boundary["edge"], 2)
        self.assertTrue(boundary["edgeTopologyDoesNotOverrideMode"])

    def test_remains_runtime_gated(self):
        boundary = self.contract["implementationBoundary"]
        self.assertTrue(boundary["equationsClosed"])
        self.assertTrue(boundary["goldenVectorsCaptured"])
        self.assertFalse(boundary["solverImplemented"])

    def test_generated_contract_matches(self):
        expected = json.dumps(self.contract, indent=2) + "\n"
        self.assertEqual(target.OUTPUT.read_text(encoding="utf-8"), expected)


if __name__ == "__main__":
    unittest.main()
