import unittest

from scripts.story_builder.language_helpers import (
    classify_zero_index_timeline_continuation,
)


class OptionTimelineContinuationTests(unittest.TestCase):
    def classify(self, jumps):
        return classify_zero_index_timeline_continuation(
            [1, 2],
            [0, 0],
            candidate_window_start=10.0,
            candidate_window_end=14.0,
            runtime_jump_clips=jumps,
        )

    def test_all_zero_adjacent_clips_without_jump_are_shared(self):
        self.assertEqual(self.classify([])["status"], "shared")

    def test_overlapping_runtime_jump_keeps_route_uncertainty_without_inferred_replies(self):
        result = self.classify(
            [{"optionIndex": 1, "start": 11.0, "end": 12.0}]
        )

        self.assertEqual(result["status"], "shared")
        self.assertEqual(
            result["reason"],
            "defaultTrunkClipContinuationWithRuntimeJump",
        )
        self.assertEqual(result["runtimeJumpRouteStatus"], "overlapUnresolved")

    def test_non_overlapping_runtime_jump_does_not_block_shared_continuation(self):
        result = self.classify(
            [{"optionIndex": 1, "start": 20.0, "end": 21.0}]
        )

        self.assertEqual(result["status"], "shared")

    def test_missing_or_malformed_jump_evidence_preserves_warning(self):
        self.assertEqual(self.classify(None)["status"], "unverified")
        self.assertEqual(self.classify([{"optionIndex": 1}])["status"], "blocked")

    def test_positive_candidate_indices_are_not_shared(self):
        result = classify_zero_index_timeline_continuation(
            [1, 2],
            [2, 1],
            candidate_window_start=10.0,
            candidate_window_end=14.0,
            runtime_jump_clips=[],
        )

        self.assertEqual(result["status"], "notApplicable")


if __name__ == "__main__":
    unittest.main()
