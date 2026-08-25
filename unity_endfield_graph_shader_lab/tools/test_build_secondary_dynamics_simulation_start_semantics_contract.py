import json
import sys
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import build_secondary_dynamics_simulation_start_semantics_contract as target


class SimulationStartSemanticsContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = target.build_contract()

    def test_pins_exact_avx2_core(self):
        self.assertEqual(self.contract["core"]["rva"], "0x25e830")
        self.assertEqual(self.contract["core"]["bytes"], 5074)
        self.assertEqual(
            self.contract["core"]["sha256"],
            "19b635fc37d878779e286408bcb58ea5abd3746f2f508f90fe634028d6bae9cc",
        )

    def test_closes_main_equations_but_keeps_helpers_fail_closed(self):
        names = {stage["name"] for stage in self.contract["stages"]}
        self.assertIn("damping_forces_prediction", names)
        self.assertIn("spring_distance_and_noise", names)
        self.assertFalse(self.contract["implementation_boundary"]["solverImplemented"])
        self.assertEqual(
            self.contract["nested_helpers"]["wind"]["status"],
            "call_abi_bounded_equations_open",
        )
        self.assertEqual(
            self.contract["nested_helpers"]["normalConeCos"]["status"],
            "exact_scalar_binary64_cosine_implementation_closed",
        )

    def test_generated_contract_matches(self):
        expected = json.dumps(self.contract, indent=2) + "\n"
        self.assertEqual(target.OUTPUT.read_text(encoding="utf-8"), expected)


if __name__ == "__main__":
    unittest.main()
