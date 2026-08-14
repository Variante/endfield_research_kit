from __future__ import annotations

import unittest

from scripts.story_builder.option_branch_projection import (
    all_option_response_risk_line_ids,
    collect_local_scene_link_options,
    expand_transparent_single_option_branch,
    normalize_group_branch_convergence,
    option_risk_line_ids,
)


class OptionBranchProjectionTests(unittest.TestCase):
    def test_risk_line_projection_preserves_authored_option_order(self) -> None:
        risk = {
            "optionIds": ["option_b", "option_a"],
            "candidateLineIdsByOption": {
                "option_a": ["missing", "line_a"],
                "option_b": "line_b",
            },
            "candidateLineIds": ["unused_a", "unused_b"],
            "commonContinuationLineId": "common",
        }
        valid = {"line_a", "line_b", "unused_a", "unused_b", "common"}

        self.assertEqual(
            option_risk_line_ids(risk, 2, valid_line_ids=valid),
            ["line_b", "line_a"],
        )
        self.assertEqual(
            all_option_response_risk_line_ids(
                {
                    "candidateLineIds": ["line_b", "missing", "line_b"],
                    "branchLineIdsByOption": {
                        "option_a": ["line_a", "line_b"],
                        "option_b": "common",
                    },
                },
                valid_line_ids=valid,
            ),
            ["line_b", "line_a", "common"],
        )

    def test_collect_scene_links_filters_and_deduplicates_paths(self) -> None:
        option = {"optionId": "option_dlg_demo_1_1", "pathLineIds": ["line_2"]}
        result = collect_local_scene_link_options(
            [
                {"after": "line_1", "options": [option, dict(option), None]},
                {
                    "after": "line_1",
                    "options": [
                        {"optionId": "option_dlg_demo_1_2", "pathLineIds": ["missing"]}
                    ],
                },
                {"after": "missing", "options": [option]},
            ],
            valid_line_ids={"line_1", "line_2"},
        )

        self.assertEqual(result, {"line_1": [option]})

    def test_expands_hidden_single_option_path_with_rendered_gap(self) -> None:
        scene_options = {
            "line_1": [
                {
                    "optionId": "option_dlg_demo_1_1",
                    "pathLineIds": ["line_3", "line_4"],
                }
            ]
        }
        ordered = ["line_1", "line_2", "line_3", "line_4"]

        self.assertEqual(
            expand_transparent_single_option_branch(
                ["line_1"],
                valid_line_ids=set(ordered),
                rendered_ordered_line_ids=ordered,
                rendered_line_order_index={line_id: i for i, line_id in enumerate(ordered)},
                local_scene_link_options_by_after=scene_options,
                conversation_key="dlg_demo_1",
                dialog_option_signature_by_id={
                    "option_dlg_demo_1_1": ("", "Default")
                },
                dialog_tree_option_prefix=lambda option_id: "dlg_demo_1"
                if option_id.startswith("option_dlg_demo_1_")
                else "",
            ),
            ordered,
        )

    def test_normalizes_common_suffix_and_fails_closed_for_whole_path(self) -> None:
        options = [
            {"branchLines": ["left", "shared_1", "shared_2"]},
            {"branchLines": ["right", "shared_1", "shared_2"]},
        ]
        risk = normalize_group_branch_convergence(
            {"after": "anchor"},
            options,
            ["option_left", "option_right"],
            valid_line_ids={"left", "right", "shared_1", "shared_2"},
        )

        self.assertEqual(
            [option["branchLines"] for option in options],
            [["left"], ["right"]],
        )
        self.assertEqual(risk["commonContinuationLineIds"], ["shared_1", "shared_2"])
        self.assertEqual(
            risk["branchLineIdsByOption"],
            {"option_left": ["left"], "option_right": ["right"]},
        )
        self.assertEqual(
            normalize_group_branch_convergence(
                {},
                [{"branchLines": ["shared"]}, {"branchLines": ["shared"]}],
                ["a", "b"],
                valid_line_ids={"shared"},
            ),
            {},
        )


if __name__ == "__main__":
    unittest.main()
