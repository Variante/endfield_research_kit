import json
import sys
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import build_secondary_dynamics_distance_golden_vectors as target


class DistanceGoldenVectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = target.build_contract()
        cls.vectors = {row["name"]: row for row in cls.contract["vectors"]}

    def test_native_hash_gates_and_range_index_abi_are_pinned(self):
        self.assertEqual(self.contract["core"]["rva"], "0x321ef0")
        self.assertEqual(
            self.contract["core"]["sha256"],
            "bca4c3f13dff30f5de4cdc982372849514c7a3cd21641e82cf0ecca536764a1c",
        )
        wrapper = self.contract["rangeWrapperAbi"]
        self.assertEqual(wrapper["rva"], "0x322550")
        self.assertEqual(
            wrapper["sha256"],
            "b2aad3d1ae110f5f06e25daacf399a8efbac95fd4ab23941409d1703b531918d",
        )
        self.assertEqual(wrapper["coreArgument15"], "int32 rangeIndex value")

    def test_executes_native_core_and_matches_source_port(self):
        boundary = self.contract["boundary"]
        self.assertTrue(boundary["nativeCoreExecuted"])
        self.assertTrue(boundary["sourceTranscriptionBinary64Matched"])
        self.assertTrue(boundary["rangeWrapperArgument15Confirmed"])
        self.assertEqual(len(self.contract["vectors"]), 8)

    def test_controlled_axis_vectors(self):
        self.assertEqual(
            self.vectors["single_constraint_stretch"]["output"]["next"],
            [0.5, 0.0, 0.0],
        )
        self.assertEqual(
            self.vectors["single_constraint_compression"]["output"]["next"],
            [-0.25, 0.0, 0.0],
        )
        self.assertEqual(
            self.vectors["negative_signed_rest_half_stiffness"]["output"]["next"],
            [0.25, 0.0, 0.0],
        )

    def test_averaging_and_no_write_boundaries(self):
        self.assertEqual(
            self.vectors["two_constraint_mean"]["output"]["next"],
            [0.25, 0.25, 0.0],
        )
        for name in ("degenerate_constraint_no_write", "empty_packed_range_no_write"):
            row = self.vectors[name]
            self.assertEqual(row["output"]["next"], row["input"]["next"][0])
            self.assertEqual(row["output"]["velocityPos"], row["input"]["velocity"][0])
            self.assertEqual(row["output"]["acceptedConstraintCount"], 0)

    def test_generated_contract_matches(self):
        expected = json.dumps(self.contract, indent=2) + "\n"
        self.assertEqual(target.OUTPUT.read_text(encoding="utf-8"), expected)


if __name__ == "__main__":
    unittest.main()
