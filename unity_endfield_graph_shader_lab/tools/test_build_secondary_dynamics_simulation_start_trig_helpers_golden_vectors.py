import ctypes
import json
import sys
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import build_secondary_dynamics_simulation_start_trig_helpers_golden_vectors as target


class SimulationStartTrigHelperGoldenVectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = target.build_contract(run_broad_audit=False)

    def test_controlled_native_vectors_match_source(self):
        self.assertEqual(len(self.contract["vectors"]), len(target.CASES))
        self.assertEqual(self.contract["status"],
                         "native_helpers_and_standalone_source_transcriptions_bit_exact")

    def test_code_and_table_identities_are_pinned(self):
        self.assertEqual(self.contract["helpers"]["springSine"]["sha256"], target.SIN_SHA256)
        self.assertEqual(self.contract["helpers"]["coneCosine"]["sha256"], target.COS_SHA256)
        self.assertEqual(self.contract["sharedReducer"]["sha256"], target.REDUCER_SHA256)
        self.assertEqual(self.contract["reducerTable"]["sha256"], target.TABLE_SHA256)
        self.assertEqual(len(target._TABLE), 3876)

    def test_source_call_graph_cannot_reach_native_execution(self):
        proof = self.contract["sourceIndependenceProof"]
        self.assertFalse(proof["sourceCallsNativeCode"])
        self.assertFalse(proof["sourceReadsNativeDllTable"])
        self.assertEqual(proof["violations"], [])

    def test_source_is_deterministic_without_native_initialization(self):
        self.assertEqual(target.source_sin(0x3FF0000000000000), 0x3FEAED548F090CEE)
        self.assertEqual(target.source_cos(0x3FF0000000000000), 0x3FE14A280FB5068C)

    def test_stratified_sweep_covers_every_finite_exponent(self):
        gate = target.burst._native_gate(None, None)
        module = ctypes.WinDLL(gate["libBurstGenerated"]["path"])
        native_sin, native_cos = target._native_functions(module)
        count = 0
        for exponent in range(2047):
            for sign in (0, 0x8000000000000000):
                for mantissa in (0, 1, 0x123456789AB, 0x7FFFFFFFFFFFF, 0xFFFFFFFFFFFFF):
                    bits = sign | (exponent << 52) | mantissa
                    self.assertEqual(native_sin(bits), target.source_sin(bits), f"sin 0x{bits:016x}")
                    self.assertEqual(native_cos(bits), target.source_cos(bits), f"cos 0x{bits:016x}")
                    count += 1
        self.assertEqual(count, 20470)

    def test_generated_contract_matches(self):
        expected = json.dumps(target.build_contract(), indent=2) + "\n"
        self.assertEqual(target.OUTPUT.read_text(encoding="utf-8"), expected)


if __name__ == "__main__":
    unittest.main()
