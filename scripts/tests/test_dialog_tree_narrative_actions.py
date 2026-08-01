from __future__ import annotations

import unittest

from scripts.story_builder.anime_assets import (
    _extract_dialog_tree_left_subtitle_actions,
    _extract_dialog_tree_narrative_mask_actions,
    _extract_dialog_tree_open_ui_actions,
    _extract_dialog_tree_open_ui_content_actions,
    extract_dialog_tree_definition_evidence,
)
from scripts.story_builder.language_bundle import (
    classify_leveldata_mission_shell_occurrences,
    collect_native_story_occurrences,
    is_typed_dialog_tree_runtime_action_connection,
    quest_attached_dialog_tree_runtime_actions,
    select_unique_original_parent_mission,
    select_unique_typed_mission_area_parent_mission,
    suppresses_generic_levelscript_mission_context,
)


NARRATIVE_TYPE = "Beyond.Gameplay.DialogNarrativeMaskActionData"
COMPLEX_TYPE = "Beyond.Gameplay.DialogComplexNarrativeMaskActionData"
LEFT_SUBTITLE_TYPE = "Beyond.Gameplay.DialogLeftSubtitleActionData"


class DialogTreeNarrativeActionTests(unittest.TestCase):
    def test_extracts_exact_dialog_tree_definition_shape(self) -> None:
        payload = {
            "_assetName": "dlg_fixture_1",
            "type": "Beyond.Gameplay.DialogTree",
            "nodes": [
                {
                    "$id": "0",
                    "$type": "Beyond.Gameplay.DialogTreeTrunkNode",
                    "_actorNodeData": {
                        "mfTrunkActionData": {"_trunkId": "dlg_fixture_1_001"},
                    },
                },
                {
                    "$id": "1",
                    "$type": "Beyond.Gameplay.DialogTreeOptionNode",
                    "_normalOptions": [
                        {"_optionId": "option_dlg_fixture_1_1_001"},
                        {"_optionId": "option_dlg_fixture_1_1_002"},
                    ],
                },
            ],
            "connections": [{
                "$type": "Beyond.Gameplay.DialogTreeConnection",
                "_sourceNode": {"$ref": "0"},
                "_targetNode": {"$ref": "1"},
            }],
        }

        evidence = extract_dialog_tree_definition_evidence(
            payload,
            "dlg_fixture_1",
        )

        self.assertIsNotNone(evidence)
        self.assertEqual(["dlg_fixture_1_001"], evidence["lineIds"])
        self.assertEqual(2, evidence["nodeCount"])
        self.assertEqual(1, evidence["connectionCount"])
        self.assertEqual(1, evidence["branchingOptionGroupCount"])

    def test_rejects_dialog_tree_definition_name_or_type_mismatch(self) -> None:
        payload = {
            "_assetName": "dlg_other_1",
            "type": "Beyond.Gameplay.DialogTree",
            "nodes": [],
            "connections": [],
        }
        self.assertIsNone(
            extract_dialog_tree_definition_evidence(payload, "dlg_fixture_1")
        )
        payload["_assetName"] = "dlg_fixture_1"
        payload["type"] = "Beyond.Gameplay.OtherAsset"
        self.assertIsNone(
            extract_dialog_tree_definition_evidence(payload, "dlg_fixture_1")
        )

    def test_script_condition_scope_keeps_richer_levelscript_fallback_open(
        self,
    ) -> None:
        self.assertFalse(
            suppresses_generic_levelscript_mission_context({
                "key": "dlg_e1m2_1",
                "relation": "levelscript_condition_scope",
            })
        )
        self.assertTrue(
            suppresses_generic_levelscript_mission_context({
                "key": "dlg_e1m2_1",
                "relation": "objective_condition",
            })
        )

    def test_extracts_only_typed_left_subtitle_langkey_slots(self) -> None:
        payload = {
            "type": "Beyond.Gameplay.DialogTree",
            "nodes": [{
                "$id": "0",
                "_transitionData": {
                    "actions": [{
                        "$type": LEFT_SUBTITLE_TYPE,
                        "text1": {"key": "black_test_1_001"},
                        "text2": {"key": "black_test_1_002"},
                        "text3": {"key": ""},
                        "textStayTime": 2.0,
                        "duration": 4.02,
                    }],
                },
                "misleadingRecursiveObject": {
                    "$type": LEFT_SUBTITLE_TYPE,
                    "text1": {"key": "black_false_1_001"},
                },
            }],
        }

        rows = _extract_dialog_tree_left_subtitle_actions(payload)

        self.assertEqual(
            ["black_test_1_001", "black_test_1_002"],
            [row["textId"] for row in rows],
        )
        self.assertEqual(["text1", "text2"], [row["textField"] for row in rows])
        self.assertEqual(2.0, rows[0]["textStayTime"])
        self.assertEqual(4.02, rows[0]["duration"])

    def test_extracts_typed_open_ui_terminal_to_finish_nodes(self) -> None:
        payload = {
            "type": "Beyond.Gameplay.DialogTree",
            "nodes": [{
                "$id": "0",
                "$type": "Beyond.Gameplay.DialogTreeOpenUINode",
                "_actionData": {
                    "$type": "Beyond.Gameplay.DialogOpenUIAction",
                    "actionEnum": 57,
                    "panelType": 22,
                    "param": '{"activityId":"activity_fixture"}',
                },
            }, {
                "$id": "1",
                "$type": "Beyond.Gameplay.DialogTreeFinishNode",
                "finishId": 1,
            }],
            "connections": [{
                "_sourceNode": {"$ref": "0"},
                "_targetNode": {"$ref": "1"},
                "$type": "Beyond.Gameplay.DialogTreeConnection",
            }],
        }

        rows = _extract_dialog_tree_open_ui_actions(payload)

        self.assertEqual(1, len(rows))
        self.assertEqual("open_ui", rows[0]["terminalKind"])
        self.assertEqual(22, rows[0]["panelType"])
        self.assertEqual("activity_fixture", rows[0]["paramData"]["activityId"])
        self.assertEqual([1], rows[0]["finishIds"])

    def test_extracts_inline_open_ui_with_exact_adjacent_trunks(self) -> None:
        def trunk(node_id: str, line_id: str) -> dict:
            return {
                "$id": node_id,
                "$type": "Beyond.Gameplay.DialogTreeTrunkNode",
                "_actorNodeData": {
                    "mfTrunkActionData": {"_trunkId": line_id},
                },
            }

        payload = {
            "type": "Beyond.Gameplay.DialogTree",
            "nodes": [
                trunk("0", "dlg_fixture_001"),
                {
                    "$id": "1",
                    "$type": "Beyond.Gameplay.DialogTreeOpenUINode",
                    "_actionData": {
                        "$type": "Beyond.Gameplay.DialogOpenUIAction",
                        "actionEnum": 57,
                        "panelType": 17,
                        "param": '{"id":"rp_text_fixture_1"}',
                    },
                },
                trunk("2", "dlg_fixture_002"),
            ],
            "connections": [{
                "$type": "Beyond.Gameplay.DialogTreeConnection",
                "_sourceNode": {"$ref": source},
                "_targetNode": {"$ref": target},
            } for source, target in (("0", "1"), ("1", "2"))],
        }

        rows = _extract_dialog_tree_open_ui_content_actions(payload)

        self.assertEqual(1, len(rows))
        self.assertEqual("rp_text_fixture_1", rows[0]["readingPopupId"])
        self.assertEqual(
            "exact_between_adjacent_parent_trunks",
            rows[0]["dialogTreeConnectionPlacementStatus"],
        )
        self.assertEqual(["dlg_fixture_001"], rows[0]["embeddedAfterLineIds"])
        self.assertEqual(["dlg_fixture_002"], rows[0]["embeddedBeforeLineIds"])

    def test_open_ui_content_extractor_fails_closed_on_untyped_connection(self) -> None:
        payload = {
            "type": "Beyond.Gameplay.DialogTree",
            "nodes": [{
                "$id": "0",
                "$type": "Beyond.Gameplay.DialogTreeOpenUINode",
                "_actionData": {
                    "$type": "Beyond.Gameplay.DialogOpenUIAction",
                    "param": '{"id":"rp_text_fixture_1"}',
                },
            }, {
                "$id": "1",
                "$type": "Beyond.Gameplay.DialogTreeFinishNode",
            }],
            "connections": [{
                "$type": "Fixture.NotDialogTreeConnection",
                "_sourceNode": {"$ref": "0"},
                "_targetNode": {"$ref": "1"},
            }],
        }

        self.assertEqual([], _extract_dialog_tree_open_ui_content_actions(payload))

    def test_open_ui_dialog_tree_stays_runtime_action_not_story_alias(self) -> None:
        connection = {
            "key": "dlg_a1m4_OpenUI",
            "relation": "levelscript_quest_completed_action",
            "event": "LevelEvent_OnQuestStateChanged",
            "actionName": "StartDialogAction",
            "phase": "succeed",
            "levelId": "map01_lv001",
            "scriptId": "2100680001",
            "headerLocalId": 19,
            "actionLocalId": 20,
            "questState": 3,
            "questStateName": "Completed",
            "source": "fixture exact native chain",
        }
        action_index = {
            "dlg_a1m4_OpenUI": [{
                "panelType": 22,
                "actionEnum": 57,
                "param": '{"activityId":"activity_high_difficulty_1"}',
                "paramData": {"activityId": "activity_high_difficulty_1"},
                "finishIds": [0],
                "sourceFile": "TextAsset/dlg_a1m4_OpenUI.json",
                "nodeId": "0",
                "sourceType": "AnimeStudio TextAsset/DialogTree",
            }],
        }
        available = {"misc_dlg_a1m4_OpenUI"}

        self.assertTrue(is_typed_dialog_tree_runtime_action_connection(
            connection,
            available,
            action_index,
        ))
        rows = quest_attached_dialog_tree_runtime_actions(
            {"storyConnections": [connection]},
            available,
            action_index,
        )
        self.assertEqual(1, len(rows))
        self.assertEqual("dialog_tree_action", rows[0]["kind"])
        self.assertEqual("activity_high_difficulty_1", rows[0]["paramData"]["activityId"])
        self.assertFalse(rows[0]["storyBinding"])
        self.assertNotIn("key", rows[0])

    def test_typed_mission_area_scope_ignores_leveldata_filename_token(self) -> None:
        mission, contexts = select_unique_typed_mission_area_parent_mission(
            {"c27m4d5": [{"scriptId": "26900010002"}]},
            [],
            1,
            {
                "c27m4": [{
                    "relation": "leveldata_levelscript_mission_context",
                }],
                "c27m4d5": [{
                    "relation": "mission_area_leveldata_mission_context",
                }],
            },
        )

        self.assertEqual("c27m4d5", mission)
        self.assertNotIn("c27m4", contexts)

    def test_typed_mission_area_scope_still_honors_exact_parent_conflict(self) -> None:
        mission, _contexts = select_unique_typed_mission_area_parent_mission(
            {"mission_b": [{"scriptId": "100"}]},
            [],
            1,
            {"mission_a": [{"relation": "mission_accept_dialog"}]},
        )

        self.assertEqual("", mission)

    def test_parent_mission_requires_shell_and_context_union_to_agree(self) -> None:
        shell = {"c27m4": [{"scriptId": "100"}]}
        self.assertEqual(
            "c27m4",
            select_unique_original_parent_mission(
                shell,
                [],
                1,
                {"c27m4": [{"relation": "leveldata_levelscript_mission_context"}]},
            ),
        )
        self.assertEqual(
            "",
            select_unique_original_parent_mission(
                shell,
                [],
                1,
                {
                    "c27m4": [{"relation": "leveldata_levelscript_mission_context"}],
                    "c27m4d5": [{"relation": "mission_area_leveldata_mission_context"}],
                },
            ),
        )
        self.assertEqual(
            "",
            select_unique_original_parent_mission(shell, [{"status": "shared"}], 1, {}),
        )

    def test_collects_authored_and_emitted_parent_aliases_once(self) -> None:
        occurrence = {
            "levelId": "map_a",
            "scriptId": "100",
            "sourceFile": "100.bin",
            "recordOffset": 20,
            "actionName": "StartDialogAction",
        }
        index = {
            "misc_dlg_test_1": [occurrence],
            "dlg_test_1": [dict(occurrence)],
        }

        self.assertEqual(
            [occurrence],
            collect_native_story_occurrences(
                index,
                "misc_dlg_test_1",
                "dlg_test_1",
            ),
        )

    def test_classifies_only_unique_validated_leveldata_shells(self) -> None:
        occurrences = [
            {"levelId": "map_a", "scriptId": "100", "actionName": "StartDialog"},
            {"levelId": "map_a", "scriptId": "200", "actionName": "StartDialog"},
            {"levelId": "map_a", "scriptId": "300", "actionName": "StartDialog"},
        ]
        hosts = {
            ("map_a", "100"): {
                "status": "unique",
                "hostMissionIds": ["mission_a"],
                "hosts": [{"levelDataFile": "mission_a.bin"}],
            },
            ("map_a", "200"): {
                "status": "shared",
                "hostMissionIds": ["mission_a", "mission_b"],
                "hosts": [{"levelDataFile": "shared.bin"}],
            },
            ("map_a", "300"): {
                "status": "unique",
                "hostMissionIds": ["missing_mission"],
                "hosts": [{"levelDataFile": "missing.bin"}],
            },
        }

        scoped, shared = classify_leveldata_mission_shell_occurrences(
            occurrences,
            hosts,
            {"mission_a", "mission_b"},
        )

        self.assertEqual(["mission_a"], list(scoped))
        self.assertEqual("mission_a.bin", scoped["mission_a"][0]["levelDataHosts"][0]["levelDataFile"])
        self.assertEqual(
            ["mission_leveldata_member22_contains_validated_levelscript_brief"],
            scoped["mission_a"][0]["scopeEvidenceKinds"],
        )
        self.assertEqual([hosts[("map_a", "200")]], shared)

    def test_extracts_only_native_typed_langkey_fields(self) -> None:
        payload = {
            "type": "Beyond.Gameplay.DialogTree",
            "nodes": [
                {
                    "$id": "0",
                    "_transitionData": {
                        "actions": [
                            {
                                "$type": NARRATIVE_TYPE,
                                "texts": [
                                    {"key": "black_test_1_001"},
                                    {"key": ""},
                                ],
                            }
                        ],
                        "_actionGroups": [
                            {
                                "actions": [
                                    {
                                        "$type": COMPLEX_TYPE,
                                        "textDataList": [
                                            {
                                                "langKey": {"key": "black_test_2_001"},
                                                "customText": "display annotation only",
                                                "textBeforeTime": 1.5,
                                            }
                                        ],
                                    }
                                ]
                            }
                        ],
                    },
                    "misleadingRecursiveObject": {
                        "$type": NARRATIVE_TYPE,
                        "texts": [{"key": "black_false_1_001"}],
                    },
                }
            ],
        }

        rows = _extract_dialog_tree_narrative_mask_actions(payload)

        self.assertEqual(
            ["black_test_1_001", "black_test_2_001"],
            [row["textId"] for row in rows],
        )
        self.assertEqual(
            "nodes[0]._transitionData.actions[0]",
            rows[0]["actionPath"],
        )
        self.assertEqual("display annotation only", rows[1]["customText"])

    def test_connection_edges_place_narrative_between_exact_trunks(self) -> None:
        payload = {
            "type": "Beyond.Gameplay.DialogTree",
            # Deliberately keep array order different from graph order.
            "nodes": [{
                "$id": "before",
                "$type": "Beyond.Gameplay.DialogTreeTrunkNode",
                "_actorNodeData": {
                    "mfTrunkActionData": {"_trunkId": "dlg_test_1_006"},
                },
            }, {
                "$id": "after",
                "$type": "Beyond.Gameplay.DialogTreeTrunkNode",
                "_actorNodeData": {
                    "mfTrunkActionData": {"_trunkId": "dlg_test_1_007"},
                },
            }, {
                "$id": "action",
                "_transitionData": {
                    "_actionGroups": [{
                        "actions": [{
                            "$type": NARRATIVE_TYPE,
                            "texts": [{"key": "black_test_1_001"}],
                            "duration": 5.0,
                            "textBeforeTime": 0.2,
                            "textAfterTime": 0.5,
                            "isMainAction": True,
                        }],
                    }],
                },
            }],
            "connections": [{
                "$type": "Beyond.Gameplay.DialogTreeConnection",
                "_sourceNode": {"$ref": "before"},
                "_targetNode": {"$ref": "action"},
            }, {
                "$type": "Beyond.Gameplay.DialogTreeConnection",
                "_sourceNode": {"$ref": "action"},
                "_targetNode": {"$ref": "after"},
            }],
        }

        rows = _extract_dialog_tree_narrative_mask_actions(payload)

        self.assertEqual(1, len(rows))
        self.assertEqual(
            "exact_unique_adjacent_trunks",
            rows[0]["dialogTreeConnectionPlacementStatus"],
        )
        self.assertEqual(
            ["dlg_test_1_006"],
            rows[0]["immediatelyPrecedingTrunkIds"],
        )
        self.assertEqual(
            ["dlg_test_1_007"],
            rows[0]["immediatelyFollowingTrunkIds"],
        )
        self.assertEqual(["before"], rows[0]["incomingNodeIds"])
        self.assertEqual(["after"], rows[0]["outgoingNodeIds"])
        self.assertTrue(rows[0]["reachableFromPrimeNode"])
        self.assertEqual(
            ["before", "action"],
            rows[0]["primeToActionNodePath"],
        )
        self.assertEqual(5.0, rows[0]["duration"])
        self.assertEqual(0.2, rows[0]["textBeforeTime"])
        self.assertEqual(0.5, rows[0]["textAfterTime"])
        self.assertTrue(rows[0]["isMainAction"])

    def test_branched_narrative_node_has_no_exact_trunk_placement(self) -> None:
        payload = {
            "type": "Beyond.Gameplay.DialogTree",
            "nodes": [{
                "$id": "before",
                "$type": "Beyond.Gameplay.DialogTreeTrunkNode",
                "_actorNodeData": {
                    "mfTrunkActionData": {"_trunkId": "dlg_test_1_006"},
                },
            }, {
                "$id": "action",
                "_transitionData": {
                    "actions": [{
                        "$type": NARRATIVE_TYPE,
                        "texts": [{"key": "black_test_1_001"}],
                    }],
                },
            }, {
                "$id": "after_a",
                "$type": "Beyond.Gameplay.DialogTreeTrunkNode",
                "_actorNodeData": {
                    "mfTrunkActionData": {"_trunkId": "dlg_test_1_007"},
                },
            }, {
                "$id": "after_b",
                "$type": "Beyond.Gameplay.DialogTreeTrunkNode",
                "_actorNodeData": {
                    "mfTrunkActionData": {"_trunkId": "dlg_test_1_008"},
                },
            }],
            "connections": [{
                "$type": "Beyond.Gameplay.DialogTreeConnection",
                "_sourceNode": {"$ref": "before"},
                "_targetNode": {"$ref": "action"},
            }, {
                "$type": "Beyond.Gameplay.DialogTreeConnection",
                "_sourceNode": {"$ref": "action"},
                "_targetNode": {"$ref": "after_a"},
            }, {
                "$type": "Beyond.Gameplay.DialogTreeConnection",
                "_sourceNode": {"$ref": "action"},
                "_targetNode": {"$ref": "after_b"},
            }],
        }

        rows = _extract_dialog_tree_narrative_mask_actions(payload)

        self.assertEqual(1, len(rows))
        self.assertEqual(
            "not_exact_unique_adjacent_trunks",
            rows[0]["dialogTreeConnectionPlacementStatus"],
        )

    def test_disconnected_addressable_narrative_node_is_not_exact(self) -> None:
        payload = {
            "type": "Beyond.Gameplay.DialogTree",
            "nodes": [{
                "$id": "prime",
            }, {
                "$id": "before",
                "$type": "Beyond.Gameplay.DialogTreeTrunkNode",
                "_actorNodeData": {
                    "mfTrunkActionData": {"_trunkId": "dlg_test_1_006"},
                },
            }, {
                "$id": "action",
                "_transitionData": {
                    "actions": [{
                        "$type": NARRATIVE_TYPE,
                        "texts": [{"key": "black_test_1_001"}],
                    }],
                },
            }, {
                "$id": "after",
                "$type": "Beyond.Gameplay.DialogTreeTrunkNode",
                "_actorNodeData": {
                    "mfTrunkActionData": {"_trunkId": "dlg_test_1_007"},
                },
            }],
            "connections": [{
                "$type": "Beyond.Gameplay.DialogTreeConnection",
                "_sourceNode": {"$ref": "before"},
                "_targetNode": {"$ref": "action"},
            }, {
                "$type": "Beyond.Gameplay.DialogTreeConnection",
                "_sourceNode": {"$ref": "action"},
                "_targetNode": {"$ref": "after"},
            }],
        }

        rows = _extract_dialog_tree_narrative_mask_actions(payload)

        self.assertEqual(1, len(rows))
        self.assertFalse(rows[0]["reachableFromPrimeNode"])
        self.assertEqual(
            "not_exact_unique_adjacent_trunks",
            rows[0]["dialogTreeConnectionPlacementStatus"],
        )

    def test_accepts_native_actor_action_containers(self) -> None:
        payload = {
            "type": "Beyond.Gameplay.DialogTree",
            "nodes": [
                {
                    "$id": "0",
                    "_actorNodeData": {
                        "actions": [
                            {
                                "$type": NARRATIVE_TYPE,
                                "texts": [{"key": "black_actor_1_001"}],
                            }
                        ],
                        "actionGroups": [
                            {
                                "actions": [
                                    {
                                        "$type": NARRATIVE_TYPE,
                                        "texts": [{"key": "black_actor_2_001"}],
                                    }
                                ]
                            }
                        ],
                    }
                }
            ],
        }

        rows = _extract_dialog_tree_narrative_mask_actions(payload)

        self.assertEqual(
            ["black_actor_1_001", "black_actor_2_001"],
            [row["textId"] for row in rows],
        )

    def test_rejects_wrong_root_or_action_type(self) -> None:
        wrong_root = {
            "type": "Beyond.Gameplay.NotDialogTree",
            "nodes": [
                {
                    "$id": "0",
                    "_transitionData": {
                        "actions": [
                            {
                                "$type": NARRATIVE_TYPE,
                                "texts": [{"key": "black_false_1_001"}],
                            }
                        ]
                    }
                }
            ],
        }
        wrong_action = {
            "type": "Beyond.Gameplay.DialogTree",
            "nodes": [
                {
                    "$id": "0",
                    "_transitionData": {
                        "actions": [
                            {
                                "$type": "Beyond.Gameplay.OtherActionData",
                                "texts": [{"key": "black_false_2_001"}],
                            }
                        ]
                    }
                }
            ],
        }

        self.assertEqual([], _extract_dialog_tree_narrative_mask_actions(wrong_root))
        self.assertEqual([], _extract_dialog_tree_narrative_mask_actions(wrong_action))

    def test_rejects_unreachable_node_without_managed_reference_id(self) -> None:
        payload = {
            "type": "Beyond.Gameplay.DialogTree",
            "nodes": [{
                "_transitionData": {
                    "actions": [{
                        "$type": NARRATIVE_TYPE,
                        "texts": [{"key": "black_orphan_1_001"}],
                    }],
                },
            }],
            "connections": [],
        }

        self.assertEqual([], _extract_dialog_tree_narrative_mask_actions(payload))


if __name__ == "__main__":
    unittest.main()
