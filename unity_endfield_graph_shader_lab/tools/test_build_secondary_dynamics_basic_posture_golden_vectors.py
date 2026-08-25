import json
import sys
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import build_secondary_dynamics_basic_posture_golden_vectors as target


class BasicPostureGoldenVectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = target.build_contract()
        cls.vectors = {row["name"]: row for row in cls.contract["vectors"]}

    def test_native_identities_and_abi_are_pinned(self):
        self.assertEqual(self.contract["core"]["rva"], "0x241aa0")
        self.assertEqual(self.contract["core"]["bytes"], 1804)
        self.assertEqual(self.contract["core"]["sha256"], "1a83498696a2e50778d1aed396decdafacbae129c3ae4196daa9391497eaae98")
        self.assertEqual(self.contract["abi"]["entry"]["rva"], "0x241910")
        self.assertEqual(self.contract["abi"]["range"]["rva"], "0x2421b0")
        self.assertEqual(self.contract["abi"]["coreArgument14"], "int32 rangeIndex value")

    def test_native_execution_matches_source_bits(self):
        self.assertTrue(self.contract["boundary"]["nativeCoreExecuted"])
        self.assertTrue(self.contract["boundary"]["sourceTranscriptionBinary32Matched"])
        self.assertEqual(len(self.contract["vectors"]), 6)

    def test_required_case_coverage(self):
        coverage = set(self.contract["boundary"]["caseCoverage"])
        for required in ("root hierarchy", "non-root hierarchy", "positive scale", "negative scale",
                         "animation-pose ratio zero", "animation-pose ratio partial",
                         "animation-pose ratio one early exit", "quaternion nlerp", "quaternion slerp"):
            self.assertIn(required, coverage)

    def test_ratio_one_preserves_supplied_step_buffers(self):
        row = self.vectors["pose_ratio_one_early_exit"]
        self.assertEqual(row["output"]["stepPositionsFloat32"], [[target._f32(x) for x in v] for v in row["input"]["stepPositionsFloat32"]])
        self.assertEqual(row["output"]["stepRotationsFloat32"], [[target._f32(x) for x in v] for v in row["input"]["stepRotationsFloat32"]])

    def test_sine_helper_is_pinned(self):
        self.assertEqual(self.contract["sineHelper"], {
            "rva": "0x1de610", "bytes": 557,
            "sha256": "d11fc448307689e5bf1c981bf1cae17af4604d6fa0105aa2196b162048a1c6ac",
        })

    def test_generated_contract_matches(self):
        self.assertEqual(target.OUTPUT.read_text(encoding="utf-8"), json.dumps(self.contract, indent=2) + "\n")


if __name__ == "__main__":
    unittest.main()
