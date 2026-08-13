from __future__ import annotations

import unittest

from scripts.story_builder.option_route_projection import (
    dialog_tree_option_node_layout_for_group,
    preferred_timeline_option_route,
    preferred_timeline_option_row,
    timeline_route_branch_for_group,
)
from scripts.story_builder.option_timeline_continuation import (
    classify_runtime_jump_option_routes,
)


def _unique_preserve(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


class OptionRouteProjectionTests(unittest.TestCase):
    def test_preferred_timeline_rows_and_routes_keep_original_ordering(self):
        rows = {
            "option_1": [
                {"anchorMode": "fallback", "start": 1.0, "optionIndex": 0},
                {"anchorMode": "trunkBinding", "start": 2.0, "optionIndex": 1},
            ]
        }
        routes = {
            "option_1": [
                {"pathLineIds": ["line_1"], "start": 1.0, "source": "z"},
                {"pathLineIds": ["line_1", "line_2"], "start": 2.0, "source": "a"},
            ]
        }
        self.assertIs(
            preferred_timeline_option_row(
                "option_1",
                timeline_option_rows=rows,
            ),
            rows["option_1"][1],
        )
        self.assertIs(
            preferred_timeline_option_route(
                "option_1",
                timeline_option_routes=routes,
            ),
            routes["option_1"][1],
        )
        self.assertEqual(
            preferred_timeline_option_route(
                "missing",
                timeline_option_routes=routes,
            ),
            {},
        )

    def test_dialog_tree_layout_classifies_sequence_separate_and_orphan_nodes(self):
        option_ids = ["option_1", "option_2"]
        sequence_layouts = {
            "option_1": [{
                "sourceKey": "scene",
                "file": "tree.json",
                "nodeId": "10",
                "reachableFromPrime": True,
                "distanceFromPrime": 1,
                "reachableNodeIds": ["20"],
                "outgoingNodeIds": ["20"],
            }],
            "option_2": [{
                "sourceKey": "scene",
                "file": "tree.json",
                "nodeId": "20",
                "reachableFromPrime": True,
                "distanceFromPrime": 2,
                "reachableNodeIds": [],
                "outgoingNodeIds": ["30"],
            }],
        }
        result = dialog_tree_option_node_layout_for_group(
            option_ids,
            "line_0",
            tree_option_node_layouts=sequence_layouts,
        )
        self.assertEqual(result["code"], "sequentialDialogTreeOptionNodes")
        self.assertEqual(result["promptSequenceOptionIds"], option_ids)

        separate_layouts = {
            **sequence_layouts,
            "option_1": [{**sequence_layouts["option_1"][0], "reachableNodeIds": []}],
        }
        self.assertEqual(
            dialog_tree_option_node_layout_for_group(
                option_ids,
                "line_0",
                tree_option_node_layouts=separate_layouts,
            )["code"],
            "separateDialogTreeOptionNodes",
        )

        orphan = {
            option_id: [{
                "sourceKey": "scene",
                "file": "tree.json",
                "nodeId": "10",
                "outgoingNodeIds": [],
            }]
            for option_id in option_ids
        }
        self.assertEqual(
            dialog_tree_option_node_layout_for_group(
                option_ids,
                "line_0",
                tree_option_node_layouts=orphan,
            )["code"],
            "orphanDialogTreeOptionDefinitions",
        )

    def test_dialog_tree_layout_fails_closed_for_incomplete_group(self):
        self.assertEqual(
            dialog_tree_option_node_layout_for_group(
                ["option_1", "option_2"],
                "line_0",
                tree_option_node_layouts={"option_1": [{"nodeId": "10"}]},
            ),
            {},
        )

    def test_timeline_route_projects_nonempty_runtime_jump_evidence(self):
        option_ids = ["option_1", "option_2"]
        routes = {
            "option_1": [{
                "pathLineIds": ["line_a", "line_common"],
                "skippedLineIds": ["line_b", "not_local"],
                "reverseRangeLineIds": ["line_a"],
                "continuationOptionIds": ["option_next"],
                "optionIndex": 1,
                "skipRanges": [{"track": "jump_track"}],
            }],
            "option_2": [{
                "pathLineIds": ["line_b", "line_common"],
                "skippedLineIds": ["line_a"],
                "continuationOptionIds": ["option_next", "option_after"],
                "optionIndex": 2,
                "reverseRanges": [{"assetTrack": "reverse_track"}],
            }],
        }
        result = timeline_route_branch_for_group(
            option_ids,
            "line_0",
            valid_line_ids={"line_0", "line_a", "line_b", "line_common"},
            tree_branches={},
            timeline_after={option_id: "line_0" for option_id in option_ids},
            timeline_pre=set(),
            timeline_option_routes=routes,
            local_ordered_line_ids=["line_0", "line_a", "line_b", "line_common"],
            classify_runtime_jump_option_routes=classify_runtime_jump_option_routes,
            unique_preserve=_unique_preserve,
        )
        self.assertEqual(result["code"], "timelineRouteBranches")
        self.assertEqual(result["branchLineIdsByOption"], {
            "option_1": ["line_a"],
            "option_2": ["line_b"],
        })
        self.assertEqual(result["commonContinuationLineId"], "line_common")
        self.assertEqual(result["skippedLineIdsByOption"]["option_1"], ["line_b"])
        self.assertEqual(result["continuationOptionIds"], ["option_next", "option_after"])
        self.assertEqual(result["assetTracks"], ["jump_track", "reverse_track"])

    def test_timeline_route_fails_closed_for_authored_tree_branch(self):
        self.assertEqual(
            timeline_route_branch_for_group(
                ["option_1", "option_2"],
                "line_0",
                valid_line_ids={"line_0", "tree_line"},
                tree_branches={"option_1": ["tree_line"]},
                timeline_after={"option_1": "line_0", "option_2": "line_0"},
                timeline_pre=set(),
                timeline_option_routes={},
                local_ordered_line_ids=["line_0", "tree_line"],
                classify_runtime_jump_option_routes=classify_runtime_jump_option_routes,
                unique_preserve=_unique_preserve,
            ),
            {},
        )


if __name__ == "__main__":
    unittest.main()
