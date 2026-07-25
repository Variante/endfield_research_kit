from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.story_builder import level_bindings
from scripts.story_builder.level_bindings import (
    build_levelscript_manual_guide_group_story_routes,
    decode_levelscript_mission_state_control_gates,
    build_levelscript_travel_pole_custom_event_story_routes,
    select_leveldata_native_event_story_context,
)
from scripts.story_builder.language_bundle import (
    attach_unconnected_mission_shell_fallbacks,
    collect_globally_attached_story_keys,
    is_exact_processing_mission_state_story_context,
)


class NativeEventShellContextTests(unittest.TestCase):
    def test_only_equal_processing_true_is_promotable_mission_context(self) -> None:
        gate = {
            "missionId": "testm1",
            "comparerName": "Equal",
            "expectedStateName": "Processing",
            "selectedBranch": "true",
        }
        route = {
            "gateMissionIds": ["testm1"],
            "gatePaths": [{"missionStateGates": [gate]}],
        }
        self.assertTrue(is_exact_processing_mission_state_story_context(
            route,
            "testm1",
        ))
        for field, value in (
            ("comparerName", "NotEqual"),
            ("expectedStateName", "Completed"),
            ("selectedBranch", "false"),
        ):
            with self.subTest(field=field):
                changed = {**gate, field: value}
                self.assertFalse(is_exact_processing_mission_state_story_context(
                    {
                        "gateMissionIds": ["testm1"],
                        "gatePaths": [{"missionStateGates": [changed]}],
                    },
                    "testm1",
                ))
        self.assertFalse(is_exact_processing_mission_state_story_context(
            {
                "gateMissionIds": ["older", "testm1"],
                "gatePaths": [{"missionStateGates": [gate, {
                    **gate,
                    "missionId": "older",
                }]}],
            },
            "testm1",
        ))

    def test_mission_state_gate_uses_native_comparer_and_selected_branch(self) -> None:
        records = [
            {"code": 0x00FF, "kind": 0x0B, "start": 10, "localId": 1},
            {"code": 0x001F, "kind": 0x0A, "start": 20, "localId": 2},
            {"code": 0x013A, "kind": 0x08, "start": 30, "localId": 3},
        ]
        membership = {
            10: "actionList#1",
            20: "getterList#1",
            30: "getterList#2",
        }

        def decoded(_data, record, **_kwargs):
            if record["localId"] == 1:
                return {"conditionGetterLocalId": 2}
            if record["localId"] == 2:
                return {"compareMissionState": {
                    "comparerRaw": 1,
                    "comparerName": "NotEqual",
                    "valueAGetterLocalId": 3,
                    "valueBStateRaw": 3,
                    "valueBStateName": "Completed",
                    "nativeMappingId": "fixture",
                }}
            return {"getMissionState": {"missionId": "testm1"}}

        with patch.object(
            level_bindings,
            "decode_levelscript_record_payload",
            side_effect=decoded,
        ):
            true_gates = decode_levelscript_mission_state_control_gates(
                b"\x00" * 40,
                records,
                membership,
                {"path": [
                    {"actionName": "IfElseAction", "localId": 1},
                    {"edge": "IfElseAction.trueAction", "localId": 9},
                ]},
            )
            false_gates = decode_levelscript_mission_state_control_gates(
                b"\x00" * 40,
                records,
                membership,
                {"path": [
                    {"actionName": "IfElseAction", "localId": 1},
                    {"edge": "IfElseAction.falseAction", "localId": 9},
                ]},
            )
        self.assertEqual("not_completed", true_gates[0]["selectedStateRelation"])
        self.assertEqual("completed", false_gates[0]["selectedStateRelation"])
        self.assertFalse(true_gates[0]["serverExchange"])

    def test_global_attachment_guard_reads_accumulated_mission_and_quest_edges(self) -> None:
        attached = collect_globally_attached_story_keys(
            {
                "mission_a": {
                    "missionStoryConnections": [{"key": "dlg_mission_shell"}],
                    "quests": [{
                        "storyConnections": [{"key": "dlg_quest_edge"}],
                    }],
                },
                "mission_b": {
                    "missionStoryConnections": [],
                    "quests": [],
                },
            },
            {
                "mission_b": {"dlg_auxiliary_index"},
            },
        )
        self.assertEqual(
            {
                "dlg_mission_shell",
                "dlg_quest_edge",
                "dlg_auxiliary_index",
            },
            attached,
        )

    def test_shell_fallback_does_not_duplicate_a_later_stronger_edge(self) -> None:
        flows = {
            "mission_a": {
                "missionStoryConnections": [],
                "quests": [{
                    "storyConnections": [{"key": "dlg_already_bound"}],
                }],
            },
        }
        preexisting = {"mission_a": set()}
        emitted = attach_unconnected_mission_shell_fallbacks(
            flows,
            preexisting,
            [
                (
                    "mission_a",
                    "dlg_already_bound",
                    {"key": "dlg_already_bound", "relation": "fallback"},
                ),
                (
                    "mission_a",
                    "dlg_true_residual",
                    {"key": "dlg_true_residual", "relation": "fallback"},
                ),
            ],
        )
        self.assertEqual([("mission_a", "dlg_true_residual")], emitted)
        self.assertEqual(
            [{"key": "dlg_true_residual", "relation": "fallback"}],
            flows["mission_a"]["missionStoryConnections"],
        )
        self.assertEqual({"dlg_true_residual"}, preexisting["mission_a"])

    @staticmethod
    def _records() -> list[dict]:
        return [
            {
                "code": 0x00FF,
                "kind": 0x0B,
                "start": 100,
                "localId": 27,
                "nextId": -1,
                "strings": [],
                "plainStrings": [],
            },
            {
                "code": 0x0028,
                "kind": 0x0A,
                "start": 200,
                "localId": 30,
                "nextId": -1,
                "strings": [{"text": "$26@_entityOutput"}],
                "plainStrings": [],
            },
            {
                "code": 0x037E,
                "kind": 0x0A,
                "start": 300,
                "localId": 29,
                "nextId": -1,
                "strings": [{"text": "PLAY_SEQ_TEST"}],
                "plainStrings": [],
            },
        ]

    @staticmethod
    def _playback_index() -> dict[str, list[dict]]:
        return {
            "cutscene_testm1_zipline": [{
                "levelId": "map_test",
                "scriptId": "1008",
                "sourceFile": "listener.bin",
                "nativeEventOwners": [{
                    "status": "exact_serialized_control_path",
                    "headerName": "LevelEvent_OnCustomEvent",
                    "headerLocalId": 1,
                    "headerTexts": [
                        "PLAY_SEQ_TEST",
                        "$1@_eventArgsPtr",
                    ],
                }],
            }],
        }

    @staticmethod
    def _membership(_data: bytes, _records: list[dict]) -> tuple[dict, dict]:
        return {}, {
            100: "actionList#1 root",
            200: "getterList#1 root",
            300: "actionList#2 linked",
        }

    @staticmethod
    def _control_path(
        _data: bytes,
        _records: list[dict],
        _membership: dict,
        target: dict,
        **_kwargs,
    ) -> list[dict]:
        if target.get("localId") != 29:
            return []
        return [{
            "status": "exact_serialized_control_path",
            "headerName": "LevelEvent_OnTravelPoleBegin",
            "headerLocalId": 26,
            "path": [{
                "actionName": "IfElseAction",
                "localId": 27,
            }, {
                "actionName": "RaiseCustomLevelEvent",
                "localId": 29,
            }],
        }]

    @staticmethod
    def _decode(_data: bytes, record: dict, **_kwargs) -> dict:
        if record.get("localId") == 27:
            return {"conditionGetterLocalId": 30}
        if record.get("localId") == 30:
            return {
                "entityCompare": {
                    "type": "EntityCompare",
                    "propertyOutputRefs": [{
                        "localId": 26,
                        "field": "entityOutput",
                        "ref": "$26@_entityOutput",
                    }],
                    "scriptEntity": {
                        "logicId": 0,
                        "slotId": 40007,
                        "useSlotId": True,
                    },
                },
            }
        return {}

    def test_exact_travel_pole_raise_and_unique_listener_route(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "producer.bin").write_bytes(bytes(400))
            binding = {
                "files": [{
                    "file": "producer.bin",
                    "fileStem": "1013",
                    "records": self._records(),
                }],
            }
            with (
                patch.object(level_bindings, "ROOT", root),
                patch.object(
                    level_bindings,
                    "_load_levelscript_binding_data",
                    return_value=binding,
                ),
                patch.object(
                    level_bindings,
                    "levelscript_action_map_membership",
                    side_effect=self._membership,
                ),
                patch.object(
                    level_bindings,
                    "_levelscript_native_control_paths_to_record",
                    side_effect=self._control_path,
                ),
                patch.object(
                    level_bindings,
                    "decode_levelscript_record_payload",
                    side_effect=self._decode,
                ),
            ):
                routes = build_levelscript_travel_pole_custom_event_story_routes(
                    self._playback_index()
                )

        self.assertEqual(1, len(routes))
        self.assertEqual("cutscene_testm1_zipline", routes[0]["storyKey"])
        self.assertEqual("1013", routes[0]["producerScriptId"])
        self.assertEqual("PLAY_SEQ_TEST", routes[0]["raisedEventKey"])
        self.assertEqual(
            40007,
            routes[0]["entityCompareBridge"]["entityCompare"][
                "scriptEntity"
            ]["slotId"],
        )

    def test_multiple_producer_signatures_for_one_event_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            files = []
            for script_id in ("1013", "1014"):
                filename = f"producer_{script_id}.bin"
                (root / filename).write_bytes(bytes(400))
                files.append({
                    "file": filename,
                    "fileStem": script_id,
                    "records": self._records(),
                })
            with (
                patch.object(level_bindings, "ROOT", root),
                patch.object(
                    level_bindings,
                    "_load_levelscript_binding_data",
                    return_value={"files": files},
                ),
                patch.object(
                    level_bindings,
                    "levelscript_action_map_membership",
                    side_effect=self._membership,
                ),
                patch.object(
                    level_bindings,
                    "_levelscript_native_control_paths_to_record",
                    side_effect=self._control_path,
                ),
                patch.object(
                    level_bindings,
                    "decode_levelscript_record_payload",
                    side_effect=self._decode,
                ),
            ):
                routes = build_levelscript_travel_pole_custom_event_story_routes(
                    self._playback_index()
                )
        self.assertEqual([], routes)

    def test_unique_shell_selection_skips_stronger_existing_route(self) -> None:
        route_names = (
            "cutscene_testm1_1st",
            "cutscene_testm1_2a",
            "cutscene_testm1_2b",
            "cutscene_testm1_2c",
        )
        routes = [
            {
                "storyKey": story_key,
                "levelId": "map_test",
                "producerScriptId": "1013",
                "raisedEventKey": f"PLAY_SEQ_{index}",
            }
            for index, story_key in enumerate(route_names, 1)
        ]
        shell_index = {
            ("map_test", "1013"): {
                "status": "unique",
                "hostMissionIds": ["testm1"],
                "hosts": [{"levelDataFile": "opaque_shell.bin"}],
            },
        }
        selected = select_leveldata_native_event_story_context(
            routes,
            shell_index,
            {"testm1": {route_names[0]}},
        )
        self.assertEqual(list(route_names[1:]), [row["storyKey"] for row in selected])
        self.assertTrue(all(row["missionId"] == "testm1" for row in selected))

    def test_shared_or_conflicting_story_mission_unions_fail_closed(self) -> None:
        routes = [{
            "storyKey": "cutscene_conflict",
            "levelId": "map_test",
            "producerScriptId": "1001",
        }, {
            "storyKey": "cutscene_conflict",
            "levelId": "map_test",
            "producerScriptId": "2001",
        }, {
            "storyKey": "cutscene_shared",
            "levelId": "map_test",
            "producerScriptId": "3001",
        }]
        shell_index = {
            ("map_test", "1001"): {
                "status": "unique",
                "hostMissionIds": ["mission_a"],
                "hosts": [],
            },
            ("map_test", "2001"): {
                "status": "unique",
                "hostMissionIds": ["mission_b"],
                "hosts": [],
            },
            ("map_test", "3001"): {
                "status": "shared",
                "hostMissionIds": ["mission_a", "mission_b"],
                "hosts": [],
            },
        }
        self.assertEqual(
            [],
            select_leveldata_native_event_story_context(routes, shell_index),
        )

    @staticmethod
    def _guide_playback_index() -> dict[str, list[dict]]:
        return {
            "radio_c33m2_30": [{
                "levelId": "dung02_rdg005",
                "scriptId": "34700000019",
                "sourceFile": "listener.bin",
                "nativeEventOwners": [{
                    "status": "exact_serialized_control_path",
                    "headerName": "LevelEvent_OnGuideGroupComplete",
                    "headerTexts": [
                        "guide_group_camille_skill_intro",
                        "$0@_guideId",
                    ],
                    "eventDetail": {
                        "guideIdFilter": "guide_group_camille_skill_intro",
                    },
                }],
            }],
        }

    def test_exact_manual_guide_start_and_completion_listener_route(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            levelscript_root = root / "LevelScript"
            (levelscript_root / "map01_lv007").mkdir(parents=True)
            (root / "producer.bin").write_bytes(bytes(200))
            binding = {
                "files": [{
                    "file": "producer.bin",
                    "fileStem": "2800340004",
                    "records": [{
                        "code": 0x0304,
                        "kind": 0x09,
                        "start": 100,
                        "payloadStart": 100,
                        "localId": 9,
                        "nextId": -1,
                        "strings": [{
                            "text": "guide_group_camille_skill_intro",
                        }],
                        "plainStrings": [],
                    }],
                }],
            }
            with (
                patch.object(level_bindings, "ROOT", root),
                patch.object(
                    level_bindings,
                    "LEVELSCRIPT_DIR",
                    levelscript_root,
                ),
                patch.object(
                    level_bindings,
                    "_load_levelscript_binding_data",
                    return_value=binding,
                ),
                patch.object(
                    level_bindings,
                    "levelscript_action_map_membership",
                    return_value=({}, {100: "actionList#1 root"}),
                ),
            ):
                routes = build_levelscript_manual_guide_group_story_routes(
                    self._guide_playback_index()
                )
        self.assertEqual(1, len(routes))
        self.assertEqual("radio_c33m2_30", routes[0]["storyKey"])
        self.assertEqual("map01_lv007", routes[0]["levelId"])
        self.assertEqual("2800340004", routes[0]["producerScriptId"])
        self.assertEqual(
            "guide_group_camille_skill_intro",
            routes[0]["guideGroupId"],
        )

    def test_multiple_manual_guide_producers_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            levelscript_root = root / "LevelScript"
            (levelscript_root / "map01_lv007").mkdir(parents=True)
            files = []
            for script_id in ("2800340004", "2800340005"):
                filename = f"producer_{script_id}.bin"
                (root / filename).write_bytes(bytes(200))
                files.append({
                    "file": filename,
                    "fileStem": script_id,
                    "records": [{
                        "code": 0x0304,
                        "kind": 0x09,
                        "start": 100,
                        "payloadStart": 100,
                        "localId": 9,
                        "nextId": -1,
                        "strings": [{
                            "text": "guide_group_camille_skill_intro",
                        }],
                        "plainStrings": [],
                    }],
                })
            with (
                patch.object(level_bindings, "ROOT", root),
                patch.object(
                    level_bindings,
                    "LEVELSCRIPT_DIR",
                    levelscript_root,
                ),
                patch.object(
                    level_bindings,
                    "_load_levelscript_binding_data",
                    return_value={"files": files},
                ),
                patch.object(
                    level_bindings,
                    "levelscript_action_map_membership",
                    return_value=({}, {100: "actionList#1 root"}),
                ),
            ):
                routes = build_levelscript_manual_guide_group_story_routes(
                    self._guide_playback_index()
                )
        self.assertEqual([], routes)


if __name__ == "__main__":
    unittest.main()
