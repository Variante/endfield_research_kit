from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_source_story_partial_order as partial_order  # noqa: E402


def mission_payload(
    edges: list[dict] | None = None,
    *,
    branch_points: list[dict] | None = None,
    quest_edges: list[dict] | None = None,
    node_orders: dict[str, int] | None = None,
) -> dict:
    keys = {
        str(edge.get("from") or "")
        for edge in edges or []
    } | {
        str(edge.get("to") or "")
        for edge in edges or []
    }
    return {
        "flow": {
            "sceneGraph": {
                "nodes": [
                    {
                        "key": key,
                        "kind": "dlg",
                        "order": (node_orders or {}).get(key, 999),
                    }
                    for key in sorted(keys)
                    if key
                ],
                "edges": edges or [],
            }
        },
        "timelineRecovery": {
            "branchPoints": branch_points or [],
            "questEdges": quest_edges or [],
            # Deliberately contradictory: this field must never affect output.
            "sceneOrderInfo": {
                key: {"questOrder": 1000 - index, "orderSource": "numericFallback"}
                for index, key in enumerate(sorted(keys))
                if key
            },
        },
    }


class SourceStoryPartialOrderTests(unittest.TestCase):
    def test_chain_is_transitively_reduced(self) -> None:
        candidates = {"dlg_a": "dlg", "dlg_b": "dlg", "dlg_c": "dlg"}
        payload = mission_payload([
            {"from": "dlg_a", "to": "dlg_b", "kind": "questSequence"},
            {"from": "dlg_b", "to": "dlg_c", "kind": "questSequence"},
            {"from": "dlg_a", "to": "dlg_c", "kind": "questPrev"},
        ])

        result = partial_order.build_mission_partial_order("m1", candidates, payload)

        component_by_scene = {row["key"]: row["component"] for row in result["nodes"]}
        reduced = {(row["from"], row["to"]) for row in result["reducedComponentEdges"]}
        self.assertEqual(reduced, {
            (component_by_scene["dlg_a"], component_by_scene["dlg_b"]),
            (component_by_scene["dlg_b"], component_by_scene["dlg_c"]),
        })
        self.assertEqual(result["summary"]["comparableScenePairs"], 3)
        self.assertEqual(result["summary"]["unorderedScenePairs"], 0)

    def test_option_fork_remains_partial(self) -> None:
        candidates = {"dlg_a": "dlg", "dlg_b": "dlg", "dlg_c": "dlg"}
        payload = mission_payload([
            {
                "from": "dlg_a",
                "to": "dlg_b",
                "kind": "authoredDirect",
                "optionIds": ["option_a_1"],
                "sourceKeys": ["tree_a"],
            },
            {
                "from": "dlg_a",
                "to": "dlg_c",
                "kind": "authoredMenu",
                "optionIds": ["option_a_2"],
                "sourceKeys": ["tree_a"],
            },
        ])

        result = partial_order.build_mission_partial_order("m1", candidates, payload)

        self.assertEqual(result["summary"]["comparableScenePairs"], 2)
        self.assertEqual(result["summary"]["unorderedScenePairs"], 1)
        option_group = result["branches"]["sceneGraphOptions"][0]
        self.assertTrue(option_group["isFork"])
        self.assertEqual(
            {arm["optionId"] for arm in option_group["arms"]},
            {"option_a_1", "option_a_2"},
        )

    def test_cycle_is_collapsed_without_internal_order(self) -> None:
        candidates = {"dlg_a": "dlg", "dlg_b": "dlg", "dlg_c": "dlg"}
        payload = mission_payload([
            {"from": "dlg_a", "to": "dlg_b", "kind": "questSequence"},
            {"from": "dlg_b", "to": "dlg_a", "kind": "questPrev"},
            {"from": "dlg_b", "to": "dlg_c", "kind": "questSequence"},
        ])

        result = partial_order.build_mission_partial_order("m1", candidates, payload)

        self.assertEqual(len(result["cycles"]), 1)
        self.assertEqual(set(result["cycles"][0]["sceneKeys"]), {"dlg_a", "dlg_b"})
        self.assertEqual(result["summary"]["cyclicInternalPairs"], 1)
        self.assertEqual(result["summary"]["comparableScenePairs"], 2)
        self.assertEqual(
            {node["relationStatus"] for node in result["nodes"] if node["key"] in {"dlg_a", "dlg_b"}},
            {"cycle"},
        )

    def test_weak_and_supported_edges_do_not_create_order(self) -> None:
        candidates = {"dlg_a": "dlg", "dlg_b": "dlg", "dlg_c": "dlg"}
        payload = mission_payload([
            {"from": "dlg_a", "to": "dlg_b", "kind": "levelscriptFileOrder"},
            {"from": "dlg_b", "to": "dlg_c", "kind": "radioContinuation"},
        ])

        result = partial_order.build_mission_partial_order("m1", candidates, payload)

        self.assertEqual(result["reducedComponentEdges"], [])
        self.assertEqual(result["summary"]["comparableScenePairs"], 0)
        self.assertEqual(result["summary"]["weakEdgeCount"], 1)
        self.assertEqual(result["summary"]["supportedEdgeCount"], 1)
        self.assertEqual(set(result["weakOnlySceneKeys"]), set(candidates))

    def test_candidates_ignore_rank_order_and_non_index_scene(self) -> None:
        candidates = {"dlg_a": "dlg", "dlg_b": "dlg"}
        payload = mission_payload(
            [{"from": "dlg_a", "to": "dlg_override_only", "kind": "questSequence"}],
            node_orders={"dlg_a": 50, "dlg_b": 1, "dlg_override_only": 0},
        )

        result = partial_order.build_mission_partial_order("m1", candidates, payload)

        self.assertEqual({node["key"] for node in result["nodes"]}, set(candidates))
        self.assertEqual(result["directEdges"], [])
        self.assertEqual(result["isolatedSceneKeys"], ["dlg_a", "dlg_b"])
        self.assertEqual(
            [row["key"] for row in result["unresolvedSourceNodes"]],
            ["dlg_override_only"],
        )

    def test_quest_forks_and_merges_are_preserved(self) -> None:
        candidates = {"dlg_a": "dlg"}
        payload = mission_payload(
            [],
            branch_points=[{
                "questId": "m1_q#1",
                "successorQuestIds": ["m1_q#2", "m1_q#3"],
                "source": "MissionRuntimeAsset.questDic[*].prevQuestIdList",
            }],
            quest_edges=[
                {"from": "m1_q#2", "to": "m1_q#4", "kind": "questPrev", "source": {"field": "a"}},
                {"from": "m1_q#3", "to": "m1_q#4", "kind": "questPrev", "source": {"field": "b"}},
            ],
        )

        result = partial_order.build_mission_partial_order("m1", candidates, payload)

        self.assertEqual(result["branches"]["questForks"][0]["questId"], "m1_q#1")
        self.assertEqual(result["summary"]["questForkCount"], 1)
        self.assertEqual(result["summary"]["questMergeCount"], 1)
        self.assertEqual(
            result["branches"]["questMerges"][0]["predecessorQuestIds"],
            ["m1_q#2", "m1_q#3"],
        )

    def test_direct_dialog_tree_branch_lines_are_source_backed(self) -> None:
        conv = {
            "key": "dlg_m1_1",
            "optionGroups": [{
                "g": 1,
                "after": "dlg_m1_1_001",
                "options": [
                    {"id": "option_1", "i": 1, "branchLines": ["dlg_m1_1_002"]},
                    {"id": "option_2", "i": 2, "branchLines": ["dlg_m1_1_003"]},
                ],
            }],
            "sceneGraphLinks": [{
                "sourceKey": "dlg_m1_1",
                "file": "export_full/source/DialogTree/dlg_m1_1.json",
                "after": "dlg_m1_1_001",
                "options": [
                    {"optionId": "option_1", "firstLineId": "dlg_m1_1_002", "pathLineIds": ["dlg_m1_1_002"]},
                    {"optionId": "option_2", "firstLineId": "dlg_m1_1_003", "pathLineIds": ["dlg_m1_1_003"]},
                ],
            }],
        }

        result = partial_order.build_mission_partial_order(
            "m1", {"dlg_m1_1": "dlg"}, mission_payload([]), [("conv/dlg_m1_1.json", conv)]
        )

        groups = result["branches"]["dialogLineOptions"]
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["provenance"]["kind"], "DialogTreeBranchLines")
        self.assertEqual(
            [option["branchLineIds"] for option in groups[0]["options"]],
            [["dlg_m1_1_002"], ["dlg_m1_1_003"]],
        )

    def test_exact_runtime_jump_signature_is_source_backed(self) -> None:
        conv = {
            "key": "dlg_m1_2",
            "optionGroups": [{
                "g": 1,
                "after": "dlg_m1_2_001",
                "options": [
                    {"id": "option_1", "branchLines": ["dlg_m1_2_002"]},
                    {"id": "option_2", "branchLines": ["dlg_m1_2_003"]},
                ],
                "optionBranchRisk": {
                    "code": "timelineRouteBranches",
                    "reason": "runtimeJumpTrack",
                    "source": "dialogTimeline",
                    "branchLineIdsByOption": {
                        "option_1": ["dlg_m1_2_002"],
                        "option_2": ["dlg_m1_2_003"],
                    },
                    "skippedLineIdsByOption": {
                        "option_1": ["dlg_m1_2_003"],
                        "option_2": ["dlg_m1_2_002"],
                    },
                    "assetTracks": ["Runtime Jump Track.json"],
                },
            }],
        }

        result = partial_order.build_mission_partial_order(
            "m1", {"dlg_m1_2": "dlg"}, mission_payload([]), [("conv/dlg_m1_2.json", conv)]
        )

        groups = result["branches"]["dialogLineOptions"]
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["provenance"]["kind"], "DialogTimelineRuntimeJump")
        self.assertEqual(result["summary"]["dialogLineOptionRouteCount"], 2)

    def test_inferred_option_routes_are_excluded(self) -> None:
        conv = {
            "key": "dlg_m1_3",
            "optionGroups": [{
                "g": 4,
                "after": "dlg_m1_3_001",
                "options": [{"id": "option_1"}, {"id": "option_2"}],
                "optionBranchRisk": {
                    "code": "inferredFollowingLines",
                    "reason": "optionTargetsMissing",
                    "source": "dialogTimeline",
                    "candidateLineIds": ["dlg_m1_3_002", "dlg_m1_3_003"],
                },
            }],
        }

        result = partial_order.build_mission_partial_order(
            "m1", {"dlg_m1_3": "dlg"}, mission_payload([]), [("conv/dlg_m1_3.json", conv)]
        )

        self.assertEqual(result["branches"]["dialogLineOptions"], [])
        self.assertEqual(
            result["branches"]["excludedDialogLineOptions"][0]["exclusionReason"],
            "inferredOrUnsupportedRisk",
        )

    def test_option_group_without_explicit_route_stays_unknown(self) -> None:
        conv = {
            "key": "dlg_m1_4",
            "optionGroups": [{
                "g": 1,
                "after": "dlg_m1_4_001",
                "options": [{"id": "option_1"}, {"id": "option_2"}],
            }],
        }

        result = partial_order.build_mission_partial_order(
            "m1", {"dlg_m1_4": "dlg"}, mission_payload([]), [("conv/dlg_m1_4.json", conv)]
        )

        self.assertEqual(result["branches"]["dialogLineOptions"], [])
        self.assertEqual(
            result["branches"]["noExplicitRouteGroups"][0]["reason"],
            "noExplicitSourceRoute",
        )

    def test_manual_option_evidence_is_never_promoted(self) -> None:
        conv = {
            "key": "dlg_m1_5",
            "optionGroups": [{
                "g": 1,
                "after": "dlg_m1_5_001",
                "manualOverride": {"source": "webui/overrides/options.json"},
                "options": [{"id": "option_1", "branchLines": ["dlg_m1_5_002"]}],
            }],
            "sceneGraphLinks": [{
                "sourceKey": "dlg_m1_5",
                "file": "export_full/source/DialogTree/dlg_m1_5.json",
                "after": "dlg_m1_5_001",
                "options": [{"optionId": "option_1", "pathLineIds": ["dlg_m1_5_002"]}],
            }],
        }

        result = partial_order.build_mission_partial_order(
            "m1", {"dlg_m1_5": "dlg"}, mission_payload([]), [("conv/dlg_m1_5.json", conv)]
        )

        self.assertEqual(result["branches"]["dialogLineOptions"], [])
        self.assertEqual(
            result["branches"]["excludedDialogLineOptions"][0]["exclusionReason"],
            "manualOptionEvidence",
        )


if __name__ == "__main__":
    unittest.main()
