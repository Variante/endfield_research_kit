from __future__ import annotations

import unittest

from scripts.story_builder.option_sibling_timeline_projection import (
    foreign_timeline_option_definition_for_group,
    option_signature_sequence,
    option_signatures_compatible,
    sibling_scene_text_branch_for_group,
)


class OptionSiblingTimelineProjectionTests(unittest.TestCase):
    def test_option_signatures_preserve_order_and_fail_closed(self) -> None:
        signatures = {
            "local_a": ("accept", "left"),
            "local_b": ("decline", "right"),
            "sibling_a": ("accept!", "left"),
            "sibling_b": ("decline", "right"),
        }
        self.assertEqual(
            option_signature_sequence(
                ["local_b", "local_a"], option_signatures_by_id=signatures
            ),
            [("decline", "right"), ("accept", "left")],
        )
        self.assertEqual(
            option_signature_sequence(
                ["local_a", "missing"], option_signatures_by_id=signatures
            ),
            [],
        )
        self.assertTrue(
            option_signatures_compatible(
                ["local_a", "local_b"],
                ["sibling_a", "sibling_b"],
                option_signatures_by_id=signatures,
                sequence_similarity_at_least=lambda _a, _b, _threshold: False,
            )
        )

    def test_projects_exact_sibling_timeline_text_branches(self) -> None:
        option_signatures = {
            "local_a": ("accept", "left"),
            "local_b": ("decline", "right"),
            "sibling_a": ("accept", "left"),
            "sibling_b": ("decline", "right"),
        }
        dialog_rows = {
            "sibling_line_a": {"dialogText": {"id": "alpha"}},
            "sibling_line_b": {"dialogText": {"id": "beta"}},
        }
        result = sibling_scene_text_branch_for_group(
            ["local_a", "local_b"],
            "anchor",
            {"siblingScenes": ["dlg_sibling"], "timeline": "timeline_1"},
            3,
            conversation_key="dlg_local",
            line_indices=[(1, "anchor"), (2, "local_a_line"), (3, "local_b_line")],
            valid_line_ids={"anchor", "local_a_line", "local_b_line"},
            lines=[
                {"id": "anchor", "text": "anchor"},
                {"id": "local_a_line", "text": "alpha"},
                {"id": "local_b_line", "text": "beta"},
            ],
            option_group_ids_by_key={
                ("dlg_sibling", 3): ["sibling_a", "sibling_b"]
            },
            option_signatures_by_id=option_signatures,
            dialog_rows=dialog_rows,
            translate=lambda value: str(value or ""),
            load_dialog_tree=lambda key: {
                "branches": {
                    "sibling_a": ["sibling_line_a"],
                    "sibling_b": ["sibling_line_b"],
                },
                "sourceKey": "tree/source",
                "file": "tree.json",
            }
            if key == "dlg_sibling"
            else {},
            option_text_signature=lambda text: text.casefold(),
            sequence_similarity_at_least=lambda left, right, _threshold: left == right,
            unique_preserve=lambda values: list(dict.fromkeys(values)),
        )

        self.assertEqual(
            result["branchLineIdsByOption"],
            {"local_a": ["local_a_line"], "local_b": ["local_b_line"]},
        )
        self.assertEqual(
            result["sources"],
            ["dlg_sibling", "tree/source", "tree.json", "timeline_1"],
        )

    def test_closes_foreign_timeline_option_definitions(self) -> None:
        result = foreign_timeline_option_definition_for_group(
            ["local_a", "local_b"],
            {
                "code": "siblingSceneTextBranches",
                "after": "anchor",
                "siblingOptionIdsByOption": {
                    "local_a": "option_dlg_sibling_1_001",
                    "local_b": "option_dlg_sibling_1_002",
                },
                "sources": ["tree.json"],
            },
            authored_option_ids=set(),
            conversation_key="dlg_local",
            cinematic_finish_groups=[
                {"timeline": "timeline_1", "finishNums": [2, 3], "file": "finish.json"}
            ],
            timeline_entries=[
                {
                    "timeline": "timeline_1",
                    "file": "timeline.json",
                    "optionRows": [
                        {
                            "id": "option_dlg_sibling_1_001",
                            "changeFinishNum": 1,
                            "targetFinishNum": 2,
                        },
                        {
                            "id": "option_dlg_sibling_1_002",
                            "changeFinishNum": 1,
                            "targetFinishNum": 3,
                        },
                    ],
                }
            ],
            dialog_tree_option_prefix=lambda option_id: "dlg_sibling"
            if "sibling" in option_id
            else "dlg_local",
            unique_preserve=lambda values: list(dict.fromkeys(values)),
        )

        self.assertEqual(result["foreignOptionIds"], [
            "option_dlg_sibling_1_001",
            "option_dlg_sibling_1_002",
        ])
        self.assertEqual(result["finishNums"], [2, 3])
        self.assertEqual(result["sources"], ["finish.json", "timeline.json", "tree.json"])


if __name__ == "__main__":
    unittest.main()
