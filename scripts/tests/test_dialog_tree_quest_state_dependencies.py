from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.story_builder import anime_assets
from scripts.story_builder.anime_assets import (
    _extract_dialog_tree_quest_state_dependencies,
    recover_dialog_tree_quest_state_dependencies,
)


def connection(source: str, target: str) -> dict:
    return {
        "_sourceNode": {"$ref": source},
        "_targetNode": {"$ref": target},
        "$type": "Beyond.Gameplay.DialogTreeConnection",
    }


def trunk(node_id: str, trunk_id: str) -> dict:
    return {
        "$id": node_id,
        "$type": "Beyond.Gameplay.DialogTreeTrunkNode",
        "_actorNodeData": {
            "mfTrunkActionData": {"_trunkId": trunk_id},
        },
    }


def quest_condition(quest_id: str, state: int) -> dict:
    return {
        "$type": "Beyond.Gameplay.CheckQuestState",
        "_questId": {"constValue": quest_id},
        "_comparer": {},
        "_targetQuestState": {"constValue": state},
    }


class DialogTreeQuestStateDependencyTests(unittest.TestCase):
    def test_root_if_reaching_current_story_trunk_is_retained(self) -> None:
        payload = {
            "type": "Beyond.Gameplay.DialogTree",
            "nodes": [{
                "$id": "0",
                "$type": "Beyond.Gameplay.DialogTreeIfNode",
                "_dialogIfData": {
                    "condition": quest_condition("mission_q#4", 3),
                },
            }, trunk("1", "dlg_exact_001"), {
                "$id": "2",
                "$type": "Beyond.Gameplay.DialogTreeFinishNode",
            }],
            "connections": [connection("0", "1"), connection("0", "2")],
        }

        rows = _extract_dialog_tree_quest_state_dependencies(
            payload,
            "dlg_exact",
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["questId"], "mission_q#4")
        self.assertEqual(rows[0]["targetQuestStates"], [3])
        self.assertEqual(rows[0]["comparerValues"], [0])
        self.assertEqual(
            rows[0]["descendantCurrentStoryTrunks"],
            {"1": "dlg_exact_001"},
        )

    def test_isolated_alternate_root_for_other_story_is_rejected(self) -> None:
        payload = {
            "type": "Beyond.Gameplay.DialogTree",
            "nodes": [
                trunk("0", "dlg_exact_001"),
                {
                    "$id": "5",
                    "$type": "Beyond.Gameplay.DialogTreeIfNode",
                    "_dialogIfData": {
                        "condition": quest_condition("mission_q#9", 3),
                    },
                },
                trunk("6", "dlg_other_001"),
            ],
            "connections": [connection("5", "6")],
        }

        self.assertEqual(_extract_dialog_tree_quest_state_dependencies(
            payload,
            "dlg_exact",
        ), [])

    def test_downstream_branch_conditions_are_current_story_dependencies(self) -> None:
        payload = {
            "type": "Beyond.Gameplay.DialogTree",
            "nodes": [
                trunk("0", "dlg_exact_001"),
                {
                    "$id": "12",
                    "$type": "Beyond.Gameplay.DialogTreeBranchNode",
                    "_dialogBranchData": {
                        "conditions": [
                            quest_condition("opaque_quest", 3),
                            quest_condition("opaque_quest", 2),
                        ],
                    },
                },
                {
                    "$id": "13",
                    "$type": "Beyond.Gameplay.DialogTreeFinishNode",
                },
            ],
            "connections": [connection("0", "12"), connection("12", "13")],
        }

        rows = _extract_dialog_tree_quest_state_dependencies(
            payload,
            "dlg_exact",
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["questId"], "opaque_quest")
        self.assertEqual(rows[0]["targetQuestStates"], [2, 3])
        self.assertEqual(
            rows[0]["ancestorCurrentStoryTrunks"],
            {"0": "dlg_exact_001"},
        )

    def test_untyped_or_unconnected_conditions_do_not_match(self) -> None:
        for condition_type in (
            "Beyond.Gameplay.CheckMissionState",
            "",
        ):
            with self.subTest(condition_type=condition_type):
                condition = quest_condition("mission_q#1", 3)
                condition["$type"] = condition_type
                payload = {
                    "type": "Beyond.Gameplay.DialogTree",
                    "nodes": [{
                        "$id": "0",
                        "$type": "Beyond.Gameplay.DialogTreeIfNode",
                        "_dialogIfData": {"condition": condition},
                    }, trunk("1", "dlg_exact_001")],
                    "connections": [connection("0", "1")],
                }
                self.assertEqual(_extract_dialog_tree_quest_state_dependencies(
                    payload,
                    "dlg_exact",
                ), [])

    def test_malformed_connection_component_fails_closed(self) -> None:
        base_nodes = [{
            "$id": "0",
            "$type": "Beyond.Gameplay.DialogTreeIfNode",
            "_dialogIfData": {
                "condition": quest_condition("mission_q#1", 3),
            },
        }, trunk("1", "dlg_exact_001")]
        bad_connections = [
            {**connection("0", "1"), "$type": "Other.Connection"},
            connection("0", "missing"),
        ]
        for bad_connection in bad_connections:
            with self.subTest(connection=bad_connection):
                self.assertEqual(_extract_dialog_tree_quest_state_dependencies({
                    "type": "Beyond.Gameplay.DialogTree",
                    "nodes": base_nodes,
                    "connections": [bad_connection],
                }, "dlg_exact"), [])

    def test_duplicate_node_identity_fails_closed(self) -> None:
        condition_node = {
            "$id": "0",
            "$type": "Beyond.Gameplay.DialogTreeIfNode",
            "_dialogIfData": {
                "condition": quest_condition("mission_q#1", 3),
            },
        }
        self.assertEqual(_extract_dialog_tree_quest_state_dependencies({
            "type": "Beyond.Gameplay.DialogTree",
            "nodes": [condition_node, trunk("0", "dlg_exact_001")],
            "connections": [],
        }, "dlg_exact"), [])

    def test_current_trunk_requires_numeric_same_root_suffix(self) -> None:
        condition_node = {
            "$id": "0",
            "$type": "Beyond.Gameplay.DialogTreeIfNode",
            "_dialogIfData": {
                "condition": quest_condition("mission_q#1", 3),
            },
        }
        self.assertEqual(_extract_dialog_tree_quest_state_dependencies({
            "type": "Beyond.Gameplay.DialogTree",
            "nodes": [condition_node, trunk("1", "dlg_exact_other")],
            "connections": [connection("0", "1")],
        }, "dlg_exact"), [])

    def test_missing_or_dynamic_comparer_is_rejected(self) -> None:
        for comparer in (None, {"blackboardKey": "cmp"}):
            with self.subTest(comparer=comparer):
                condition = quest_condition("mission_q#1", 3)
                if comparer is None:
                    condition.pop("_comparer")
                else:
                    condition["_comparer"] = comparer
                payload = {
                    "type": "Beyond.Gameplay.DialogTree",
                    "nodes": [{
                        "$id": "0",
                        "$type": "Beyond.Gameplay.DialogTreeIfNode",
                        "_dialogIfData": {"condition": condition},
                    }, trunk("1", "dlg_exact_001")],
                    "connections": [connection("0", "1")],
                }
                self.assertEqual(_extract_dialog_tree_quest_state_dependencies(
                    payload,
                    "dlg_exact",
                ), [])

    def test_recovery_requires_exact_registration_and_matching_asset_name(self) -> None:
        payload = {
            "type": "Beyond.Gameplay.DialogTree",
            "_assetName": "dlg_exact",
            "nodes": [{
                "$id": "0",
                "$type": "Beyond.Gameplay.DialogTreeIfNode",
                "_dialogIfData": {
                    "condition": quest_condition("mission_q#1", 3),
                },
            }, trunk("1", "dlg_exact_001")],
            "connections": [connection("0", "1")],
        }
        with (
            patch.object(
                anime_assets,
                "_iter_anime_tree_files",
                return_value=[Path("fixture.json")],
            ),
            patch.object(
                anime_assets,
                "_anime_tree_logical_stem",
                return_value="dlg_exact",
            ),
            patch.object(
                anime_assets,
                "_load_anime_resource_payload",
                return_value=payload,
            ),
            patch.object(anime_assets, "repo_rel", return_value="fixture.json"),
        ):
            printable_only = {
                "dlg_exact": {
                    "registered": True,
                    "memoryPackRecordKey": False,
                    "registrationEvidence": ["printable_root_token"],
                },
            }
            self.assertEqual(
                recover_dialog_tree_quest_state_dependencies(printable_only),
                [],
            )

            exact = {
                "dlg_exact": {
                    "registered": True,
                    "memoryPackRecordKey": True,
                    "registrationEvidence": ["memorypack_record_key"],
                },
            }
            self.assertEqual(
                len(recover_dialog_tree_quest_state_dependencies(exact)),
                1,
            )

            payload["_assetName"] = "dlg_other"
            self.assertEqual(
                recover_dialog_tree_quest_state_dependencies(exact),
                [],
            )


if __name__ == "__main__":
    unittest.main()
