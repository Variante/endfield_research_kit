import unittest

from scripts.story_builder.language_helpers import (
    classify_runtime_jump_option_routes,
    classify_timeline_clip_option_index_routes,
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

    def test_nonzero_clip_indices_are_exact_with_forward_convergence(self):
        result = classify_timeline_clip_option_index_routes(
            ["option_1", "option_2"],
            [1, 2],
            {
                "option_1": ["line_1a", "line_1b"],
                "option_2": ["line_2a", "line_2b"],
            },
            {
                "option_1": [1, 1],
                "option_2": [2, 2],
            },
            {
                "line_1a": {"start": 150.767, "duration": 3.716},
                "line_1b": {"start": 154.617, "duration": 4.55},
                "line_2a": {"start": 150.15, "duration": 4.333},
                "line_2b": {"start": 157.267, "duration": 7.7},
                "shared": {"start": 164.967, "duration": 7.433},
            },
            [{
                "optionIndex": 1,
                "start": 162.767,
                "end": 164.967,
                "isReverseJump": 0,
                "needChangeOptionAfterJump": 0,
            }],
            "shared",
        )

        self.assertEqual(result["status"], "exact")
        self.assertEqual(result["reason"], "runtimeClipOptionIndex")
        self.assertEqual(len(result["convergenceRuntimeJumps"]), 1)

    def test_nonzero_clip_indices_reject_a_jump_that_skips_response(self):
        result = classify_timeline_clip_option_index_routes(
            ["option_1", "option_2"],
            [1, 2],
            {"option_1": ["line_1"], "option_2": ["line_2"]},
            {"option_1": [1], "option_2": [2]},
            {
                "line_1": {"start": 10.0, "duration": 5.0},
                "line_2": {"start": 10.0, "duration": 5.0},
                "shared": {"start": 20.0, "duration": 1.0},
            },
            [{
                "optionIndex": 1,
                "start": 12.0,
                "end": 20.0,
                "isReverseJump": 0,
                "needChangeOptionAfterJump": 0,
            }],
            "shared",
        )

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(
            result["reason"],
            "runtimeJumpDoesNotConvergeAfterBranch",
        )

    def test_runtime_jump_paths_trim_a_shared_suffix(self):
        result = classify_runtime_jump_option_routes(
            ["option_1", "option_2"],
            [
                {"pathLineIds": ["line_2", "line_3"]},
                {"pathLineIds": ["line_1", "line_2", "line_3"]},
            ],
            ["anchor", "line_1", "line_2", "line_3"],
            after_line_id="anchor",
        )

        self.assertEqual(result["status"], "branched")
        self.assertEqual(
            result["branchLineIdsByOption"],
            {"option_1": [], "option_2": ["line_1"]},
        )
        self.assertEqual(
            result["directContinuationOptionIds"],
            ["option_1"],
        )
        self.assertEqual(result["commonContinuationLineId"], "line_2")

    def test_terminating_slot_resumes_after_the_response_window(self):
        result = classify_runtime_jump_option_routes(
            ["option_1", "option_2"],
            [
                {"pathLineIds": ["reply"]},
                {"pathLineIds": [], "terminatesSlot": True},
            ],
            ["anchor", "reply", "shared"],
            after_line_id="anchor",
        )

        self.assertEqual(result["status"], "branched")
        self.assertEqual(
            result["branchLineIdsByOption"],
            {"option_1": ["reply"], "option_2": []},
        )
        self.assertEqual(
            result["directContinuationOptionIds"],
            ["option_2"],
        )
        self.assertEqual(result["commonContinuationLineId"], "shared")

    def test_identical_runtime_paths_are_shared_not_branches(self):
        result = classify_runtime_jump_option_routes(
            ["option_1", "option_2"],
            [
                {"pathLineIds": ["shared"]},
                {"pathLineIds": ["shared"]},
            ],
            ["anchor", "shared"],
            after_line_id="anchor",
        )

        self.assertEqual(result["status"], "shared")

    def test_runtime_jump_paths_can_branch_before_the_first_local_line(self):
        result = classify_runtime_jump_option_routes(
            ["option_1", "option_2"],
            [
                {"pathLineIds": ["line_1", "line_2", "line_3"]},
                {"pathLineIds": ["line_4", "line_5", "line_6"]},
            ],
            [
                "line_1",
                "line_2",
                "line_3",
                "line_4",
                "line_5",
                "line_6",
                "shared",
            ],
        )

        self.assertEqual(result["status"], "branched")
        self.assertEqual(
            result["branchLineIdsByOption"],
            {
                "option_1": ["line_1", "line_2", "line_3"],
                "option_2": ["line_4", "line_5", "line_6"],
            },
        )


if __name__ == "__main__":
    unittest.main()
