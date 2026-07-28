from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
for search_path in (ROOT / "scripts", ROOT / "scripts" / "story_recovery"):
    if str(search_path) not in sys.path:
        sys.path.insert(0, str(search_path))

import build_native_receiver_activation_frontier as frontier  # noqa: E402


class NativeReceiverActivationFrontierTests(unittest.TestCase):
    def test_frontend_renders_objective_consumer_as_observation_only(self) -> None:
        source = (
            ROOT / "webui" / "src" / "features" / "mission_pipeline" / "index.js"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "activation.missionRuntimeScriptConsumers",
            source,
        )
        self.assertIn('class="is-boundary"', source)
        self.assertIn('t("questObserver")', source)
        self.assertIn('t("observationOnly")', source)
        self.assertIn(
            "playback handoff sets the observed property",
            source,
        )

    def test_receiver_nodes_collapse_by_exact_levelscript(self) -> None:
        payload = {
            "storyCoverage": {
                "missionlessNativeRuntimeNodes": [
                    {
                        "eventName": "LevelEvent_OnCustomEvent",
                        "selector": {
                            "levelId": "map_fixture",
                            "listenerScriptId": "1001",
                        },
                        "storyFiles": [
                            {
                                "key": "radio_fixture_1",
                                "kind": "radio",
                                "sourceFiles": ["source/a.json"],
                            }
                        ],
                    },
                    {
                        "eventName": "LevelEvent_OnEntityHpChanged",
                        "selector": {
                            "levelId": "map_fixture",
                            "listenerScriptId": "1001",
                        },
                        "storyFiles": [
                            {
                                "key": "black_fixture_1",
                                "kind": "black",
                                "sourceFiles": ["source/a.json"],
                            }
                        ],
                    },
                ]
            }
        }
        rows = frontier.receiver_script_rows(payload)
        self.assertEqual(1, len(rows))
        self.assertEqual(2, rows[0]["receiverNodeCount"])
        self.assertEqual(2, rows[0]["receiverToStoryPlacementCount"])
        self.assertEqual(
            ["black_fixture_1", "radio_fixture_1"],
            rows[0]["storyKeys"],
        )

    def test_manual_control_index_preserves_self_boundary(self) -> None:
        indexed = frontier.manual_control_targets(
            {
                "rows": [
                    {
                        "levelId": "map_fixture",
                        "scriptId": "1001",
                        "localId": 4,
                        "action": "ManualStartLevelScript",
                        "file": "source.json",
                        "literalTargets": [
                            {"levelId": "map_fixture", "scriptId": "1001"},
                            {"levelId": "map_fixture", "scriptId": "1002"},
                        ],
                    }
                ]
            }
        )
        self.assertTrue(indexed[("map_fixture", "1001")][0]["selfTarget"])
        self.assertFalse(indexed[("map_fixture", "1002")][0]["selfTarget"])

    def test_manual_null_shapes_task_and_parent_is_static_frontier(self) -> None:
        levelscript = {
            "startTypeName": "Manual",
            "startShapeListStatus": "null",
            "startShapeListCount": None,
            "taskMapStatus": "null",
            "taskMapCount": None,
        }
        hosts = [{"briefData": {"parentLevelScriptId": "0"}}]
        self.assertEqual(
            "manual_start_no_static_activation_carrier",
            frontier.activation_class(levelscript, hosts, []),
        )

    def test_missing_leveldata_host_fails_closed(self) -> None:
        self.assertEqual(
            "manual_start_static_carrier_unresolved",
            frontier.activation_class(
                {
                    "startTypeName": "Manual",
                    "startShapeListStatus": "null",
                    "taskMapStatus": "null",
                },
                [],
                [],
            ),
        )

    def test_literal_cross_script_control_wins_over_manual_frontier(self) -> None:
        self.assertEqual(
            "literal_cross_script_manual_control",
            frontier.activation_class(
                {"startTypeName": "Manual"},
                [],
                [{"selfTarget": False}],
            ),
        )

    def test_subgame_binding_is_an_exact_activation_scope(self) -> None:
        self.assertEqual(
            "subgame_bind_script_activation_scope",
            frontier.activation_class(
                {"startTypeName": "SameWithActive"},
                [],
                [],
                [{"subGameId": "fixture_game"}],
            ),
        )

    def test_dungeon_scene_context_keeps_sibling_receiver_non_owning(
        self,
    ) -> None:
        contexts = frontier.dungeon_scene_contexts(
            {
                "dataTable": {
                    "dungeon_fixture": {
                        "id": "dungeon_fixture",
                        "bindScriptId": 1002,
                        "dungeonMissionId": "different_mission",
                    }
                }
            },
            {
                "dungeon_fixture": {
                    "dungeonId": "dungeon_fixture",
                    "sceneId": "map_fixture",
                    "levelId": "level_fixture",
                    "dungeonSeriesId": "series_fixture",
                }
            },
            {
                "condition_fixture": {
                    "conditionId": "condition_fixture",
                    "gameMechanicsId": "dungeon_fixture",
                    "conditionType": 19,
                    "parameter": [
                        {"valueStringList": ["mission_fixture"]}
                    ],
                }
            },
            subgame_source="subgame.json",
            dungeon_source="dungeon.json",
            condition_source="condition.json",
        )
        context = contexts["map_fixture"][0]
        self.assertEqual("1002", context["bindScriptId"])
        self.assertFalse(context["ownership"])
        self.assertFalse(context["storyBinding"])
        self.assertEqual(
            "different_mission",
            context["dungeonMissionContext"]["missionId"],
        )
        self.assertFalse(context["dungeonMissionContext"]["ownership"])
        self.assertFalse(context["dungeonMissionContext"]["playback"])
        self.assertEqual(
            "mission_fixture",
            context["associations"][0]["targetId"],
        )
        self.assertFalse(context["associations"][0]["ownership"])

    def test_unknown_subgame_condition_type_fails_closed(self) -> None:
        self.assertEqual(
            {},
            frontier.subgame_availability_associations(
                {
                    "condition_fixture": {
                        "gameMechanicsId": "dungeon_fixture",
                        "conditionType": 9999,
                        "parameter": [
                            {"valueStringList": ["mission_fixture"]}
                        ],
                    }
                }
            ),
        )

    def test_start_shape_requires_complete_exact_mission_area_geometry(self) -> None:
        shape = {
            "offset": "0x10",
            "typeRaw": 2,
            "position": {"x": 1.0, "y": 2.0, "z": 3.0},
            "radius": 5.0,
        }
        area = {
            "missionAreaId": "fixture_area",
            "subDataParentId": 10,
            "shape": {
                "type": 2,
                "position": {"x": 1.0, "y": 2.0, "z": 3.0},
                "radius": 5.0,
            },
        }
        self.assertEqual(
            "fixture_area",
            frontier.exact_start_shape_mission_area_matches(
                [shape],
                [area],
            )[0]["missionAreaId"],
        )
        area["shape"]["position"]["x"] = 1.01
        self.assertEqual(
            [],
            frontier.exact_start_shape_mission_area_matches(
                [shape],
                [area],
            ),
        )

    def test_memorypack_string_scan_requires_exact_length_prefix(self) -> None:
        exact = (7).to_bytes(4, "little", signed=True) + b"mission"
        embedded = (13).to_bytes(4, "little", signed=True) + b"radio_mission"
        self.assertEqual(
            ["mission"],
            frontier.exact_memorypack_string_tokens(
                exact + embedded,
                {"mission", "missing"},
            ),
        )
        self.assertEqual(
            [],
            frontier.exact_memorypack_string_tokens(
                embedded,
                {"mission"},
            ),
        )

    def test_nonmanual_shape_is_kept_separate(self) -> None:
        self.assertEqual(
            "nonmanual_start_with_shapes",
            frontier.activation_class(
                {
                    "startTypeName": "Auto",
                    "startShapeListCount": 1,
                },
                [],
                [],
            ),
        )

    def test_pipeline_publication_is_compact_and_non_owning(self) -> None:
        index = {
            "storyCoverage": {
                "missionlessNativeRuntimeNodes": [
                    {
                        "selector": {
                            "levelId": "map_fixture",
                            "listenerScriptId": "1001",
                        }
                    }
                ]
            }
        }
        report = {
            "schemaVersion": frontier.SCHEMA,
            "generated": "fixture",
            "counts": {"receiverScripts": 1},
            "evidencePolicy": {"noPromotion": "fixture"},
            "rows": [
                {
                    "levelId": "map_fixture",
                    "scriptId": "1001",
                    "activationClass": "manual_start_no_static_activation_carrier",
                    "levelScript": {
                        "startTypeName": "Manual",
                        "startShapeListStatus": "null",
                    },
                    "levelDataHosts": [
                        {
                            "fileName": "fixture.json",
                            "dictionaryEntryCount": 1,
                            "hostMissionId": None,
                        }
                    ],
                    "subGameBindings": [],
                    "dungeonSceneContexts": [
                        {
                            "subGameId": "dungeon_fixture",
                            "sceneId": "map_fixture",
                            "levelId": "",
                            "dungeonSeriesId": "series_fixture",
                            "bindScriptId": "1002",
                            "receiverIsBoundScript": False,
                            "dungeonMissionContext": {
                                "missionId": "different_mission",
                                "ownership": False,
                                "playback": False,
                                "finding": "mission shell only",
                            },
                            "associations": [
                                {
                                    "relation": (
                                        "subgame_unlock_quest_prerequisite"
                                    ),
                                    "targetType": "quest",
                                    "targetId": "unrelated_quest",
                                    "conditionTypeName": "QuestStateEqual",
                                    "ownership": False,
                                    "finding": "availability only",
                                }
                            ],
                            "ownership": False,
                            "storyBinding": False,
                            "evidenceBoundary": "scene context only",
                        }
                    ],
                    "incomingLiteralManualControls": [],
                    "missionRuntimeScriptConsumers": [
                        {
                            "missionId": "fixture_mission",
                            "questId": "fixture_mission_q#1",
                            "objectiveIndex": 1,
                            "conditionTypes": [
                                "CheckLevelScriptPropertyBool"
                            ],
                            "sourceFile": "fixture_mission.json",
                        }
                    ],
                    "decodedTaskMap": {
                        "taskCount": 1,
                        "tasks": [
                            {
                                "taskKey": "fixture_task",
                                "conditions": [
                                    {
                                        "conditionKey": "fixture_condition",
                                        "condition": {
                                            "type": "TaskReachDestination",
                                            "areaId": {
                                                "kind": "string",
                                                "value": "fixture_area",
                                            },
                                        },
                                    }
                                ],
                            }
                        ],
                    },
                }
            ],
        }
        self.assertEqual(
            1,
            frontier.publish_to_pipeline_index(index, report),
        )
        annotation = index["storyCoverage"]["missionlessNativeRuntimeNodes"][0][
            "activationFrontier"
        ]
        self.assertEqual("Manual", annotation["startTypeName"])
        self.assertNotIn("missionOwnerStatus", annotation)
        self.assertFalse(
            annotation["dungeonSceneContexts"][0]["receiverIsBoundScript"]
        )
        self.assertFalse(
            annotation["dungeonSceneContexts"][0]["storyBinding"]
        )
        self.assertEqual(
            "different_mission",
            annotation["dungeonSceneContexts"][0][
                "dungeonMissionContext"
            ]["missionId"],
        )
        self.assertFalse(
            annotation["dungeonSceneContexts"][0][
                "dungeonMissionContext"
            ]["ownership"],
        )
        self.assertEqual(
            "unrelated_quest",
            annotation["dungeonSceneContexts"][0]["associations"][0][
                "targetId"
            ],
        )
        self.assertEqual(
            "fixture_area",
            annotation["decodedTaskMap"]["tasks"][0]["conditions"][0][
                "condition"
            ]["areaId"]["value"],
        )
        self.assertEqual(
            1,
            annotation["missionRuntimeObjectiveConsumerCount"],
        )
        consumer = annotation["missionRuntimeScriptConsumers"][0]
        self.assertEqual(
            "mission_runtime_objective_references_level_script",
            consumer["relation"],
        )
        self.assertEqual("fixture_mission", consumer["missionId"])
        self.assertEqual("fixture_mission_q#1", consumer["questId"])
        self.assertEqual(
            ["CheckLevelScriptPropertyBool"],
            consumer["conditionTypes"],
        )
        self.assertFalse(consumer["ownership"])
        self.assertFalse(consumer["activation"])
        self.assertFalse(consumer["storyPlayback"])
        self.assertNotIn("sourceFile", consumer)
        self.assertEqual(
            1,
            index["storyCoverage"]["nativeReceiverActivationFrontier"][
                "annotatedReceiverNodes"
            ],
        )

    def test_task_source_annotations_require_exact_keys(self) -> None:
        task_map = {
            "tasks": [
                {"taskKey": "fixture_task"},
                {"taskKey": "unmatched_task"},
            ]
        }
        extra = frontier.script_task_extra_info_rows(
            {
                "dataTable": {
                    "map_fixture": {
                        "1001": {
                            "fixture_task": {
                                "taskTitle": {"key": "fixture_title"},
                                "objectiveCount": 1,
                                "trackingInfoDict": {
                                    "Objective1": {
                                        "description": {
                                            "key": "fixture_description"
                                        },
                                        "needFormatProgress": True,
                                        "progressDisplayMode": 0,
                                    }
                                },
                            }
                        }
                    }
                }
            },
            source_file="fixture.json",
        )
        frontier.annotate_task_sources(
            task_map,
            level_id="map_fixture",
            script_id="1001",
            subgames=[
                {
                    "subGameId": "fixture_game",
                    "mainTaskIds": ["fixture_task"],
                    "missionOwnerStatus": "unresolved",
                }
            ],
            extra_info=extra,
        )
        task = task_map["tasks"][0]
        self.assertEqual("fixture_title", task["taskExtraInfo"]["taskTitleKey"])
        self.assertEqual(
            "fixture_description",
            task["taskExtraInfo"]["objectives"][0]["descriptionKey"],
        )
        self.assertEqual(
            "fixture_game",
            task["subGameMainTaskBindings"][0]["subGameId"],
        )
        self.assertNotIn("taskExtraInfo", task_map["tasks"][1])

    def test_mission_runtime_operand_consumers_require_exact_typed_operands(
        self,
    ) -> None:
        indexes = frontier.mission_runtime_operand_consumers_from_payloads(
            [
                (
                    "mission_fixture",
                    {
                        "questId": "quest_fixture",
                        "conditions": [
                            {
                                "$type": "CheckTalkOptionFinish",
                                "_dialogId": {
                                    "constValue": "dialog_fixture"
                                },
                                "_finishId": {"constValue": 2},
                            },
                            {
                                "$type": "CheckLevelScriptTaskFinished",
                                "_sceneId": {"constValue": "map_fixture"},
                                "_scriptId": {
                                    "constValue": {"scriptId": 1001}
                                },
                                "_taskId": {"constValue": "task_fixture"},
                            },
                        ],
                    },
                    "fixture.json",
                )
            ]
        )
        self.assertEqual(
            "mission_fixture",
            indexes["dialog"][("dialog_fixture", 2)][0]["missionId"],
        )
        self.assertNotIn(("dialog_fixture", 1), indexes["dialog"])
        self.assertEqual({}, indexes["area"])
        self.assertEqual(
            "quest_fixture",
            indexes["task"][("map_fixture", "1001", "task_fixture")][0][
                "questId"
            ],
        )

    def test_world_entity_sources_keep_only_unique_script_slots(self) -> None:
        logic_rows, slot_rows = frontier.world_entity_operand_sources(
            {
                "worldEntityBriefInfos": {
                    "9001": {
                        "entityType": 2,
                        "detailId": "enemy_fixture",
                    }
                },
                "m_scriptEntityIdList": [
                    {"scriptIdGlobal": "1001", "slotId": 4},
                    {"scriptIdGlobal": "1001", "slotId": 5},
                    {"scriptIdGlobal": "1001", "slotId": 5},
                ],
                "m_scriptEntityBriefInfo": [
                    {"entityType": 2, "detailId": "slot_fixture"},
                    {"entityType": 2, "detailId": "duplicate_a"},
                    {"entityType": 2, "detailId": "duplicate_b"},
                ],
            }
        )
        self.assertEqual("enemy_fixture", logic_rows["9001"]["detailId"])
        self.assertEqual("slot_fixture", slot_rows[("1001", 4)]["entityDetailId"])
        self.assertNotIn(("1001", 5), slot_rows)

    def test_task_operand_annotations_preserve_non_owning_sources(self) -> None:
        task_map = {
            "tasks": [
                {
                    "taskKey": "fixture_task",
                    "conditions": [
                        {
                            "condition": {
                                "type": "CheckEntityHp",
                                "entity": {
                                    "useSlotId": False,
                                    "logicId": "9001",
                                },
                            }
                        },
                        {
                            "condition": {
                                "type": "TaskReachDestination",
                                "areaId": {"value": "area_fixture"},
                            }
                        },
                    ],
                }
            ]
        }
        consumers = {
            kind: {}
            for kind in (
                "dialog",
                "area",
                "spawner",
                "script",
                "entity",
                "task",
            )
        }
        consumers["entity"][("map_fixture", 9001)] = [
            {
                "missionId": "mission_fixture",
                "questId": "quest_fixture",
                "conditionType": "CheckEntityHp",
                "sourceFile": "mission_fixture.json",
            }
        ]
        consumers["task"][("map_fixture", "1001", "fixture_task")] = [
            {
                "missionId": "task_mission_fixture",
                "questId": "task_quest_fixture",
                "conditionType": "CheckLevelScriptTaskFinished",
                "sourceFile": "task_mission_fixture.json",
            }
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            empty_root = Path(temp_dir)
            frontier.annotate_task_condition_operands(
                task_map,
                level_id="map_fixture",
                script_id="1001",
                story_keys=[],
                mission_areas=[
                    {
                        "missionAreaId": "area_fixture",
                        "subDataParentId": 7,
                        "shape": {"type": 2},
                    }
                ],
                logic_entities={
                    "9001": {
                        "entityType": 2,
                        "detailId": "enemy_fixture",
                    }
                },
                slot_entities={},
                mission_consumers=consumers,
                levelscript_root=empty_root,
                spawner_root=empty_root,
            )
        entity_row, area_row = task_map["tasks"][0]["conditions"]
        self.assertEqual(
            "task_mission_fixture",
            task_map["tasks"][0]["missionRuntimeTaskConsumers"][0][
                "missionId"
            ],
        )
        self.assertEqual(
            "world_entity_logic_id",
            entity_row["operandSources"][0]["kind"],
        )
        self.assertEqual(
            "mission_fixture",
            entity_row["missionRuntimeOperandConsumers"][0]["missionId"],
        )
        self.assertEqual(
            "same_level_mission_area",
            area_row["operandSources"][0]["kind"],
        )
        self.assertNotIn("missionRuntimeOperandConsumers", area_row)


if __name__ == "__main__":
    unittest.main()
