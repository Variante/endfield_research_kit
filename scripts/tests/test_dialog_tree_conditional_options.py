from __future__ import annotations

import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts.story_builder import dialog_tree


def option_node(node_id: str, *option_ids: str) -> dict:
    return {
        "$id": node_id,
        "$type": "Beyond.Gameplay.DialogTreeOptionNode",
        "_normalOptions": [
            {"_optionId": option_id, "index": ordinal}
            for ordinal, option_id in enumerate(option_ids)
        ],
        "_hasExOption": False,
    }


def node(node_id: str, node_type: str, *, trunk_id: str = "") -> dict:
    out = {"$id": node_id, "$type": node_type}
    if trunk_id:
        out["_trunkId"] = trunk_id
    return out


def connection(source: str, target: str) -> dict:
    return {
        "_sourceNode": {"$ref": source},
        "_targetNode": {"$ref": target},
    }


class DialogTreeConditionalOptionTests(unittest.TestCase):
    def test_option_to_if_node_retains_all_authored_outcomes(self) -> None:
        payload = {
            "type": "Beyond.Gameplay.DialogTree",
            "nodes": [
                node(
                    "0",
                    "Beyond.Gameplay.DialogTreeTrunkNode",
                    trunk_id="dlg_test_1_001",
                ),
                option_node(
                    "1",
                    "option_dlg_test_1_1_001",
                    "option_dlg_test_1_1_002",
                ),
                node("2", "Beyond.Gameplay.DialogTreeIfNode"),
                node("3", "Beyond.Gameplay.DialogTreeIfNode"),
                node("4", "Beyond.Gameplay.DialogTreeOpenUINode"),
                node(
                    "5",
                    "Beyond.Gameplay.DialogTreeTrunkNode",
                    trunk_id="dlg_test_1_002",
                ),
                node("6", "Beyond.Gameplay.DialogTreeFinishNode"),
                node(
                    "7",
                    "Beyond.Gameplay.DialogTreeTrunkNode",
                    trunk_id="dlg_test_1_003",
                ),
            ],
            "connections": [
                connection("0", "1"),
                connection("1", "2"),
                connection("1", "3"),
                connection("2", "4"),
                connection("2", "5"),
                connection("3", "6"),
                connection("3", "7"),
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "dlg_test_1.json"
            path.write_text(
                json.dumps(payload),
                encoding="utf-8",
            )
            dialog_tree._DIALOG_TREE_SOURCE_CACHE.clear()
            with patch.object(
                dialog_tree,
                "_find_anime_tree_path",
                return_value=path,
            ):
                source = dialog_tree._load_dialog_tree_source(
                    "dlg_test_1"
                )

        links = source["sceneLinks"]
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["after"], "dlg_test_1_001")
        options = links[0]["options"]
        self.assertEqual(
            [option["outcomeKind"] for option in options],
            [
                "authoredConditionalBranch",
                "authoredConditionalBranch",
            ],
        )
        self.assertEqual(
            options[0]["conditionalOutcomes"][0]["terminal"],
            "openUi",
        )
        self.assertEqual(
            options[0]["conditionalOutcomes"][1]["firstLineId"],
            "dlg_test_1_002",
        )
        self.assertEqual(
            options[1]["conditionalOutcomes"][0]["terminal"],
            "finish",
        )
        self.assertEqual(
            options[1]["conditionalOutcomes"][1]["firstLineId"],
            "dlg_test_1_003",
        )

    def test_option_to_following_option_node_is_not_conditional(self) -> None:
        payload = {
            "type": "Beyond.Gameplay.DialogTree",
            "nodes": [
                node(
                    "0",
                    "Beyond.Gameplay.DialogTreeTrunkNode",
                    trunk_id="dlg_test_2_001",
                ),
                option_node(
                    "1",
                    "option_dlg_test_2_1_001",
                ),
                option_node(
                    "2",
                    "option_dlg_test_2_2_001",
                    "option_dlg_test_2_2_002",
                ),
                node(
                    "3",
                    "Beyond.Gameplay.DialogTreeTrunkNode",
                    trunk_id="dlg_test_2_002",
                ),
                node(
                    "4",
                    "Beyond.Gameplay.DialogTreeTrunkNode",
                    trunk_id="dlg_test_2_003",
                ),
            ],
            "connections": [
                connection("0", "1"),
                connection("1", "2"),
                connection("2", "3"),
                connection("2", "4"),
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "dlg_test_2.json"
            path.write_text(
                json.dumps(payload),
                encoding="utf-8",
            )
            dialog_tree._DIALOG_TREE_SOURCE_CACHE.clear()
            with patch.object(
                dialog_tree,
                "_find_anime_tree_path",
                return_value=path,
            ):
                source = dialog_tree._load_dialog_tree_source(
                    "dlg_test_2"
                )

        first_option = source["sceneLinks"][0]["options"][0]
        self.assertNotIn("conditionalOutcomes", first_option)
        self.assertNotEqual(
            first_option.get("outcomeKind"),
            "authoredConditionalBranch",
        )

    def test_out_of_bounds_option_is_not_duplicated_onto_only_edge(self) -> None:
        options = option_node(
            "1",
            "option_dlg_test_3_1_001",
            "option_dlg_test_3_1_002",
        )
        payload = {
            "type": "Beyond.Gameplay.DialogTree",
            "nodes": [
                node(
                    "0",
                    "Beyond.Gameplay.DialogTreeTrunkNode",
                    trunk_id="dlg_test_3_001",
                ),
                options,
                node("2", "Beyond.Gameplay.DialogTreeFinishNode"),
            ],
            "connections": [connection("0", "1"), connection("1", "2")],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "dlg_test_3.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            dialog_tree._DIALOG_TREE_SOURCE_CACHE.clear()
            with patch.object(dialog_tree, "_find_anime_tree_path", return_value=path):
                source = dialog_tree._load_dialog_tree_source("dlg_test_3")

        routes = source["optionRouteRecovery"]["nodes"][0]["routes"]
        self.assertEqual(routes[0]["targetNodeId"], "2")
        self.assertEqual(routes[1]["status"], "rejected")
        self.assertEqual(
            routes[1]["issue"]["gate"], "normalOptionConnectionIndexBounds"
        )
        scene_options = source["sceneLinks"][0]["options"]
        invalid = next(
            row
            for row in scene_options
            if row["optionId"] == "option_dlg_test_3_1_002"
        )
        self.assertEqual(invalid["routeEvidence"]["status"], "rejected")
        self.assertNotIn("firstLineId", invalid)


if __name__ == "__main__":
    unittest.main()
