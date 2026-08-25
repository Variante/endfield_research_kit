import json
import sys
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import build_secondary_dynamics_angle_golden_vectors as target


class AngleGoldenVectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = target.build_contract()
        cls.vectors = {row["name"]: row for row in cls.contract["vectors"]}

    def test_native_hash_gates_and_range_index_abi_are_pinned(self):
        self.assertEqual(self.contract["core"], {
            "rva": "0x303d40", "bytes": 6480,
            "sha256": "d3d5d8f685a57d0495d39a5068d8bae97db9fae0b247235a734293264edd2666",
            "argument21": "int32 rangeIndex value"})
        self.assertEqual(self.contract["rangeWrapperAbi"]["rva"], "0x3108b0")
        self.assertEqual(self.contract["rangeWrapperAbi"]["bytes"], 334)
        self.assertEqual(self.contract["rangeWrapperAbi"]["sha256"],
                         "362a8deabacb21f171f513ee892cabccfc47c1bd6a565d2b0d8ffd67dbaafc34")
        self.assertEqual(self.contract["rangeWrapperAbi"]["coreArgument21"],
                         "int32 rangeIndex value")

    def test_native_and_source_transcription_match_all_written_bits(self):
        boundary = self.contract["boundary"]
        self.assertTrue(boundary["nativeCoreExecuted"])
        self.assertTrue(boundary["sourceTranscriptionAllWrittenBitsMatched"])
        self.assertTrue(boundary["sourceTranscriptionCallsPinnedNativeSincos"])
        self.assertFalse(boundary["standaloneSincosTranscriptionComplete"])
        self.assertEqual(len(self.contract["vectors"]), 7)

    def test_requested_case_coverage(self):
        self.assertEqual(set(self.vectors), {
            "restoration_only_aligned", "restoration_only_bent",
            "hair_limit_inside_cone", "hair_limit_outside_cone",
            "combined_limit_then_restoration", "active_parent_writeback",
            "friction_mobility"})

    def test_aligned_case_is_stable_and_scratch_is_initialized(self):
        row = self.vectors["restoration_only_aligned"]
        # The aligned branch still exposes Burst's bounded acos/sincos
        # approximation: after three sweeps the child is microscopically below
        # one instead of being algebraically unchanged.
        self.assertEqual(row["output"]["next"],
                         [(0.0, 0.0, 0.0), (0.9999999776482582, 0.0, 0.0)])
        self.assertEqual(row["output"]["restorationVector"][1], (1.0, 0.0, 0.0))

    def test_generated_contract_matches(self):
        self.assertEqual(target.OUTPUT.read_text(encoding="utf-8"),
                         json.dumps(self.contract, indent=2) + "\n")


if __name__ == "__main__":
    unittest.main()
