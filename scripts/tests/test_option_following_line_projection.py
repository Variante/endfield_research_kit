from __future__ import annotations

import unittest

from scripts.story_builder.option_following_line_projection import (
    following_line_risk_for_group,
)
from scripts.story_builder.option_route_projection import (
    preferred_timeline_option_route,
    preferred_timeline_option_row,
)
from scripts.story_builder.option_timeline_continuation import (
    classify_timeline_clip_option_index_routes,
    classify_zero_index_timeline_continuation,
)


def _unique_preserve(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


class OptionFollowingLineProjectionTests(unittest.TestCase):
    option_ids = ["option_1", "option_2"]

    def project(self, after_id: str = "anchor", **overrides: object) -> dict:
        inputs = {
            "valid_line_ids": {"anchor", "trunk", "line_1", "line_2", "shared"},
            "tree_branches": {},
            "tree_converge": {},
            "timeline_option_rows": {},
            "timeline_after": {},
            "timeline_pre": set(),
            "timeline_after_line_ids": {},
            "timeline_after_line_timings": {},
            "timeline_after_runtime_jump_clips": {},
            "timeline_option_routes": {},
        }
        inputs.update(overrides)
        return following_line_risk_for_group(
            self.option_ids,
            after_id,
            **inputs,
            preferred_timeline_option_row=preferred_timeline_option_row,
            preferred_timeline_option_route=preferred_timeline_option_route,
            classify_zero_index_timeline_continuation=(
                classify_zero_index_timeline_continuation
            ),
            classify_timeline_clip_option_index_routes=(
                classify_timeline_clip_option_index_routes
            ),
            unique_preserve=_unique_preserve,
        )

    def timeline_inputs(self, clip_indices: tuple[int, int]) -> dict:
        return {
            "timeline_option_rows": {
                "option_1": [{"optionIndex": 1, "start": 2.0, "assetTrack": "a"}],
                "option_2": [{"optionIndex": 2, "start": 2.0, "assetTrack": "b"}],
            },
            "timeline_after": {"option_1": "anchor", "option_2": "anchor"},
            "timeline_after_line_ids": {
                "option_1": ["anchor", "line_1", "line_2", "shared"],
            },
            "timeline_after_line_timings": {
                "option_1": {
                    "line_1": {
                        "clipOptionIndex": clip_indices[0],
                        "start": 10.0,
                        "duration": 1.0,
                    },
                    "line_2": {
                        "clipOptionIndex": clip_indices[1],
                        "start": 12.0,
                        "duration": 1.0,
                    },
                    "shared": {
                        "clipOptionIndex": 0,
                        "start": 14.0,
                        "duration": 1.0,
                    },
                },
            },
            "timeline_after_runtime_jump_clips": {"option_1": []},
        }

    def test_dialog_tree_convergence_is_cosmetic_choice(self) -> None:
        result = self.project(
            tree_converge={"option_1": "trunk", "option_2": "trunk"},
        )
        self.assertEqual(result["code"], "cosmeticChoice")
        self.assertEqual(result["commonContinuationLineId"], "trunk")

    def test_distinct_zero_index_slots_are_sequential_prompts(self) -> None:
        result = self.project(
            timeline_option_rows={
                "option_1": [{"optionIndex": 0, "start": 1.0}],
                "option_2": [{"optionIndex": 0, "start": 2.0}],
            },
            timeline_after={"option_1": "line_1", "option_2": "line_2"},
        )
        self.assertEqual(result["code"], "sequentialTimelineOptionPrompts")
        self.assertEqual(result["optionAnchors"], ["line_1", "line_2"])

    def test_terminal_slot_requires_complete_empty_route_evidence(self) -> None:
        result = self.project(
            timeline_option_rows={
                "option_1": [{"optionIndex": 1, "start": 2.0}],
                "option_2": [{"optionIndex": 2, "start": 2.0}],
            },
            timeline_after={"option_1": "anchor", "option_2": "anchor"},
            timeline_after_line_ids={"option_1": ["anchor"]},
            timeline_after_line_timings={"option_1": {}},
            timeline_after_runtime_jump_clips={"option_1": []},
        )
        self.assertEqual(result["code"], "terminalTimelineOptionSlot")

    def test_zero_index_candidate_clips_are_shared_continuation(self) -> None:
        result = self.project(**self.timeline_inputs((0, 0)))
        self.assertEqual(result["code"], "sharedTimelineContinuation")
        self.assertEqual(result["commonContinuationLineIds"], ["line_1", "line_2"])

    def test_positive_clip_indices_form_exact_branches(self) -> None:
        result = self.project(**self.timeline_inputs((1, 2)))
        self.assertEqual(result["code"], "timelineClipOptionIndexBranches")
        self.assertEqual(result["branchLineIdsByOption"], {
            "option_1": ["line_1"],
            "option_2": ["line_2"],
        })
        self.assertEqual(result["assetTracks"], ["a", "b"])

    def test_unmatched_clip_indices_remain_visible_inference(self) -> None:
        result = self.project(**self.timeline_inputs((3, 4)))
        self.assertEqual(result["code"], "inferredFollowingLines")
        self.assertEqual(result["candidateLineIds"], ["line_1", "line_2"])

    def test_authored_tree_branch_fails_closed(self) -> None:
        self.assertEqual(
            self.project(tree_branches={"option_1": ["line_1"]}),
            {},
        )


if __name__ == "__main__":
    unittest.main()
