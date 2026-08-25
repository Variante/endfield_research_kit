import json
import sys
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import build_secondary_dynamics_simulation_end_semantics_contract as target


class SimulationEndSemanticsContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = target.build_contract()

    def test_pins_call_free_avx2_core(self):
        self.assertEqual(self.contract["core"]["rva"], "0x24fa60")
        self.assertEqual(self.contract["core"]["bytes"], 1745)
        self.assertEqual(self.contract["core"]["directCallCount"], 0)

    def test_closes_all_end_stages_but_not_runtime(self):
        self.assertEqual(
            [row["name"] for row in self.contract["stages"]],
            [
                "inactive_bypass",
                "static_friction",
                "initial_velocity_and_dynamic_friction",
                "particle_speed_limit",
                "center_centrifugal_effect",
                "final_state_writeback",
            ],
        )
        boundary = self.contract["implementation_boundary"]
        self.assertTrue(boundary["equationsClosed"])
        self.assertFalse(boundary["helperGap"])
        self.assertTrue(boundary["goldenVectorsCaptured"])
        self.assertTrue(boundary["completeClosedBranchGoldenCoverage"])
        self.assertEqual(
            boundary["boundedGoldenVectorCoverage"],
            [
                "inactive bypass",
                "active base velocity",
                "particle speed limit",
                "static-friction accumulation",
                "static-friction release",
                "static-friction no-contact decay",
                "dynamic-friction attenuation",
                "center centrifugal response",
            ],
        )
        self.assertFalse(boundary["solverImplemented"])

    def test_generated_contract_matches(self):
        expected = json.dumps(self.contract, indent=2) + "\n"
        self.assertEqual(target.OUTPUT.read_text(encoding="utf-8"), expected)


if __name__ == "__main__":
    unittest.main()
