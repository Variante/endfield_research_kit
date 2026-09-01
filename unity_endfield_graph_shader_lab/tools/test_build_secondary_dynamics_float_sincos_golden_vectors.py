import json
import ctypes
import struct
import sys
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import build_secondary_dynamics_float_sincos_golden_vectors as target


class FloatSincosGoldenVectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = target.build_contract()

    def test_native_and_source_only_transcription_match(self):
        self.assertTrue(self.contract["boundary"]["nativeHelperExecuted"])
        self.assertEqual(
            self.contract["boundary"]["nativeCpuVariantsExecuted"],
            ["x64_sse2", "avx2"],
        )
        self.assertEqual(
            [row["rva"] for row in self.contract["helpers"]],
            ["0x6e860", "0x1e5d30"],
        )
        self.assertTrue(self.contract["boundary"]["sourceOnlyTranscriptionMatchedBitForBit"])
        self.assertFalse(self.contract["operationContract"]["sourceCallsNativeHelper"])
        self.assertFalse(self.contract["operationContract"]["sourceReadsNativeReducerTable"])

    def test_branch_and_special_case_coverage(self):
        paths = {row["path"] for row in self.contract["vectors"]}
        self.assertEqual(paths, {"small_split_pi_over_2", "medium_split_pi_over_2",
                                 "large_table_reducer", "nonfinite_canonical_nan"})
        rows = {row["name"]: row for row in self.contract["vectors"]}
        self.assertEqual(rows["negative_zero"]["output"]["sinBitsLe"], "00000080")
        for name in ("positive_infinity", "negative_infinity", "quiet_nan_payload",
                     "negative_quiet_nan", "signaling_nan_payload"):
            self.assertEqual(rows[name]["output"]["sinBitsLe"], "0000c07f")
            self.assertEqual(rows[name]["output"]["cosBitsLe"], "0000c07f")

    def test_reducer_table_is_fully_pinned(self):
        self.assertEqual(len(target._TABLE), 416)
        self.assertEqual(self.contract["reducerTable"]["sha256"], target.TABLE_SHA256)

    def test_source_function_is_deterministic_without_native_initialization(self):
        self.assertEqual(target.source_sincos(0x3F800000), (0x3F576AA4, 0x3F0A5140, "small_split_pi_over_2"))

    def test_stratified_native_sweep_covers_every_finite_exponent(self):
        gate = target.burst._native_gate(None, None)
        module = ctypes.WinDLL(gate["libBurstGenerated"]["path"])
        for variant, rva, _size, _sha256 in target.SINCOS_VARIANTS:
            native, _address = target._make_native(module, rva)
            for exponent in range(255):
                for sign in (0, 0x80000000):
                    for mantissa in (0, 1, 0x12345, 0x3FFFFF, 0x7FFFFF):
                        bits = sign | (exponent << 23) | mantissa
                        self.assertEqual(
                            native(bits), target.source_sincos(bits)[:2],
                            f"{variant} input 0x{bits:08x}",
                        )

    def test_generated_contract_matches(self):
        expected = json.dumps(self.contract, indent=2, allow_nan=True) + "\n"
        self.assertEqual(target.OUTPUT.read_text(encoding="utf-8"), expected)


if __name__ == "__main__":
    unittest.main()
