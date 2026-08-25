import json
import sys
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import build_secondary_dynamics_simulation_update_semantics_contract as target


class SimulationUpdateSemanticsContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = target.build_contract()

    def test_pins_core_and_effective_float3_widths(self):
        self.assertEqual(self.contract["core"]["rva"], "0x241aa0")
        self.assertEqual(self.contract["core"]["bytes"], 1804)
        self.assertEqual(self.contract["argumentElementStridesBytes"][9:13], [12, 16, 12, 16])

    def test_closes_hierarchy_and_blend_but_not_solver(self):
        self.assertEqual(
            [row["name"] for row in self.contract["stages"]],
            ["baseline_selection", "hierarchy_reconstruction", "animation_pose_blend"],
        )
        self.assertTrue(self.contract["implementation_boundary"]["equationsClosed"])
        self.assertFalse(self.contract["implementation_boundary"]["solverImplemented"])
        self.assertFalse(self.contract["implementation_boundary"]["bitIdenticalSinePort"])

    def test_generated_contract_matches(self):
        expected = json.dumps(self.contract, indent=2) + "\n"
        self.assertEqual(target.OUTPUT.read_text(encoding="utf-8"), expected)


if __name__ == "__main__":
    unittest.main()
