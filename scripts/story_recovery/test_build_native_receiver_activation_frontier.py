from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
for search_path in (ROOT / "scripts", ROOT / "scripts" / "story_recovery"):
    if str(search_path) not in sys.path:
        sys.path.insert(0, str(search_path))

import build_native_receiver_activation_frontier as frontier  # noqa: E402


class NativeReceiverActivationFrontierTests(unittest.TestCase):
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
                    "incomingLiteralManualControls": [],
                    "missionRuntimeScriptConsumers": [],
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
        self.assertEqual(
            "fixture_area",
            annotation["decodedTaskMap"]["tasks"][0]["conditions"][0][
                "condition"
            ]["areaId"]["value"],
        )
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


if __name__ == "__main__":
    unittest.main()
