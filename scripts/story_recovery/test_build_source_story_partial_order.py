from __future__ import annotations

import copy
import struct
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_source_story_partial_order as partial_order  # noqa: E402


def mp_string(value: str | None) -> bytes:
    if value is None:
        return struct.pack("<I", 0xFFFFFFFF)
    encoded = value.encode("utf-8")
    return struct.pack("<I", len(encoded)) + encoded


def spawner_wave_fixture() -> bytes:
    def group_entry(
        map_key: int,
        group_key: int,
        group_id: int,
        mode: int,
        target: str | None = None,
    ) -> bytes:
        return (
            struct.pack("<i", map_key)
            + b"\x0c"
            + struct.pack("<I", 0)
            + struct.pack("<fii", 0.0, 0, group_id)
            + mp_string(str(group_key))
            + struct.pack("<iii", 0, mode, 0)
            + mp_string(target)
            + b"\x00\x00"
            + struct.pack("<f", 1.0)
        )

    def entry(
        map_key: int,
        wave_id: int,
        mode: int,
        target: str | None,
        groups: list[bytes],
    ) -> bytes:
        return (
            struct.pack("<i", map_key)
            + b"\x0b"
            + struct.pack("<fI", 0.0, len(groups))
            + b"".join(groups)
            + b"\x00\x00\x00"
            + struct.pack("<f", 0.0)
            + struct.pack("<i", wave_id)
            + mp_string(str(map_key))
            + struct.pack("<ii", mode, 5)
            + mp_string(target)
        )

    return (
        b"\x05"
        + mp_string("sc_map_test_1004")
        + b"opaque-prefix"
        + struct.pack("<I", 2)
        + entry(4, 186, 2, "2", [group_entry(1, 401, 1, 0)])
        + entry(5, 193, 2, "4", [group_entry(1, 501, 2, 0)])
    )


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
    def test_spawner_part_killed_target_recovers_wave_begin_order(self) -> None:
        candidates = {
            "radio_m1_wave4": "radio",
            "radio_m1_wave5": "radio",
        }
        flow = mission_payload([])["flow"]

        def connection(story_key: str, wave_key: str, local_id: int) -> dict:
            return {
                "key": story_key,
                "confidence": "native_typed_direct_unscoped",
                "nativeMappingId": "gameassembly-test-actionbase",
                "occurrences": [{
                    "levelId": "map_test",
                    "scriptId": "1001",
                    "sourceFile": "LevelScriptData/map_test/1001.json",
                    "localId": local_id,
                    "actionName": "Play3DRadio",
                    "recordClass": "play_radio",
                    "allStoryKeysInRecord": [story_key],
                    "nativeEventOwners": [{
                        "status": "exact_serialized_control_path",
                        "headerName": "LevelEvent_OnSpawnerWaveBegin",
                        "headerLocalId": local_id - 1,
                        "eventDetail": {
                            "type": "LevelEvent_OnSpawnerWaveBegin",
                            "spawnerFilterId": 1004,
                            "waveKeyFilter": wave_key,
                            "payloadSchemaStatus":
                                "exact_current_build_memorypack_fields",
                            "payloadSchemaMappingId":
                                "gameassembly-test-spawner-wave-event",
                        },
                    }],
                }],
            }

        flow["unlinkedNativePlayback"] = [
            connection("radio_m1_wave4", "4", 40),
            connection("radio_m1_wave5", "5", 50),
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_dir = root / "map_test"
            config_dir.mkdir()
            (config_dir / "sc_map_test_1004.json").write_bytes(
                spawner_wave_fixture()
            )
            edges = partial_order._spawner_wave_part_killed_story_edges(
                flow,
                set(candidates),
                spawner_roots=[root],
            )

        self.assertEqual(len(edges), 1)
        self.assertEqual(
            (edges[0]["from"], edges[0]["to"]),
            ("radio_m1_wave4", "radio_m1_wave5"),
        )
        self.assertEqual(edges[0]["kind"], "spawnerWavePartKilled")
        self.assertEqual(edges[0]["tier"], "strong")
        self.assertEqual(edges[0]["targetWaveKey"], "4")
        self.assertEqual(edges[0]["waveKey"], "5")

    def test_spawner_group_and_wave_callbacks_cross_part_killed_gate(self) -> None:
        candidates = {
            "radio_m1_wave4",
            "radio_m1_group401",
            "radio_m1_wave5",
            "radio_m1_group501",
        }
        flow = mission_payload([])["flow"]

        def connection(
            story_key: str,
            selector_key: str,
            event_type: str,
            local_id: int,
        ) -> dict:
            selector_field = (
                "waveKeyFilter"
                if event_type == "LevelEvent_OnSpawnerWaveBegin"
                else "groupKeyFilter"
            )
            return {
                "key": story_key,
                "confidence": "native_typed_direct_unscoped",
                "nativeMappingId": "gameassembly-test-actionbase",
                "occurrences": [{
                    "levelId": "map_test",
                    "scriptId": "1001",
                    "sourceFile": "LevelScriptData/map_test/1001.json",
                    "localId": local_id,
                    "actionName": "Play3DRadio",
                    "recordClass": "play_radio",
                    "allStoryKeysInRecord": [story_key],
                    "nativeEventOwners": [{
                        "status": "exact_serialized_control_path",
                        "headerName": event_type,
                        "headerLocalId": local_id - 1,
                        "eventDetail": {
                            "type": event_type,
                            "spawnerFilterId": 1004,
                            selector_field: selector_key,
                            "payloadSchemaStatus":
                                "exact_current_build_memorypack_fields",
                            "payloadSchemaMappingId":
                                "gameassembly-test-spawner-event",
                        },
                    }],
                }],
            }

        flow["unlinkedNativePlayback"] = [
            connection(
                "radio_m1_wave4",
                "4",
                "LevelEvent_OnSpawnerWaveBegin",
                40,
            ),
            connection(
                "radio_m1_group401",
                "401",
                "LevelEvent_OnSpawnerGroupBegin",
                41,
            ),
            connection(
                "radio_m1_wave5",
                "5",
                "LevelEvent_OnSpawnerWaveBegin",
                50,
            ),
            connection(
                "radio_m1_group501",
                "501",
                "LevelEvent_OnSpawnerGroupBegin",
                51,
            ),
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_dir = root / "map_test"
            config_dir.mkdir()
            (config_dir / "sc_map_test_1004.json").write_bytes(
                spawner_wave_fixture()
            )
            edges = (
                partial_order._spawner_wave_group_part_killed_story_edges(
                    flow,
                    candidates,
                    spawner_roots=[root],
                )
            )

        self.assertEqual(
            {(edge["from"], edge["to"]) for edge in edges},
            {
                ("radio_m1_wave4", "radio_m1_group501"),
                ("radio_m1_group401", "radio_m1_wave5"),
                ("radio_m1_group401", "radio_m1_group501"),
            },
        )
        self.assertTrue(
            all(edge["kind"] == "spawnerWaveGroupPartKilled" for edge in edges)
        )
        self.assertTrue(all(edge["tier"] == "strong" for edge in edges))

    def test_spawner_group_callback_follows_exact_local_custom_event_relay(
        self,
    ) -> None:
        candidates = {"radio_m1_group401", "cutscene_m1_group501"}
        flow = mission_payload([])["flow"]
        flow["unlinkedNativePlayback"] = [
            {
                "key": "radio_m1_group401",
                "confidence": "native_typed_direct_unscoped",
                "nativeMappingId": "gameassembly-test-actionbase",
                "occurrences": [{
                    "levelId": "map_test",
                    "scriptId": "1001",
                    "sourceFile": "LevelScriptData/map_test/1001.json",
                    "localId": 41,
                    "actionName": "Play3DRadio",
                    "recordClass": "play_radio",
                    "allStoryKeysInRecord": ["radio_m1_group401"],
                    "nativeEventOwners": [{
                        "status": "exact_serialized_control_path",
                        "headerName": "LevelEvent_OnSpawnerGroupBegin",
                        "headerLocalId": 40,
                        "eventDetail": {
                            "type": "LevelEvent_OnSpawnerGroupBegin",
                            "spawnerFilterId": 1004,
                            "groupKeyFilter": "401",
                            "payloadSchemaStatus":
                                "exact_current_build_memorypack_fields",
                            "payloadSchemaMappingId":
                                "gameassembly-test-spawner-event",
                        },
                    }],
                }],
            },
            {
                "key": "cutscene_m1_group501",
                "confidence": "native_typed_direct_unscoped",
                "nativeMappingId": "gameassembly-test-actionbase",
                "nativeEventProducerRoutes": [{
                    "status": "exact_serialized_local_producer",
                    "storyKey": "cutscene_m1_group501",
                    "levelId": "map_test",
                    "raisedEventKey": "TigerStart",
                    "producerAction": "RaiseCustomScriptEvent",
                    "producerActionLocalId": 51,
                    "producerScriptId": "1001",
                    "producerSourceFile":
                        "LevelScriptData/map_test/1001.json",
                    "receiverMode": "current_script",
                    "targetScriptId": "1001",
                    "listenerScriptIds": ["1001"],
                    "listenerSourceFiles": [
                        "LevelScriptData/map_test/1001.json",
                    ],
                    "listenerRoutes": [{
                        "listenerScriptId": "1001",
                        "listenerSourceFile":
                            "LevelScriptData/map_test/1001.json",
                        "listenerEventOwner": {
                            "status": "exact_serialized_control_path",
                            "headerName": "ScriptEvent_OnCustomEvent",
                            "headerLocalId": 60,
                            "eventDetail": {
                                "type": "ScriptEvent_OnCustomEvent",
                                "eventKey": "TigerStart",
                            },
                        },
                    }],
                    "producerControlPaths": [{
                        "status": "exact_serialized_control_path",
                        "headerName": "LevelEvent_OnSpawnerGroupBegin",
                        "headerLocalId": 50,
                        "eventDetail": {
                            "type": "LevelEvent_OnSpawnerGroupBegin",
                            "spawnerFilterId": 1004,
                            "groupKeyFilter": "501",
                            "payloadSchemaStatus":
                                "exact_current_build_memorypack_fields",
                            "payloadSchemaMappingId":
                                "gameassembly-test-spawner-event",
                        },
                    }],
                    "nativeMappingId": "gameassembly-test-actionbase",
                    "serverExchange": False,
                }],
            },
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_dir = root / "map_test"
            config_dir.mkdir()
            (config_dir / "sc_map_test_1004.json").write_bytes(
                spawner_wave_fixture()
            )
            edges = (
                partial_order._spawner_wave_group_part_killed_story_edges(
                    flow,
                    candidates,
                    spawner_roots=[root],
                )
            )

        self.assertEqual(len(edges), 1)
        self.assertEqual(
            (edges[0]["from"], edges[0]["to"]),
            ("radio_m1_group401", "cutscene_m1_group501"),
        )
        child_event = edges[0]["events"][0]["childEvents"][0]
        self.assertEqual(
            child_event["routeMode"],
            "sameScriptCustomEventRelay",
        )
        self.assertEqual(child_event["raisedEventKey"], "TigerStart")

        rejected_mutations = {
            "cross-script listener route": lambda route: route.update(
                listenerScriptId="1002"
            ),
            "mismatched listener event key": lambda route: route[
                "listenerEventOwner"
            ]["eventDetail"].update(eventKey="OtherEvent"),
            "non-current receiver": lambda route: route.update(
                receiverMode="specified_script"
            ),
            "non-binary producer mapping": lambda route: route.update(
                nativeMappingId="manual-test-mapping"
            ),
            "missing producer mapping": lambda route: route.pop(
                "nativeMappingId"
            ),
        }
        for label, mutate in rejected_mutations.items():
            with self.subTest(label=label):
                rejected_flow = copy.deepcopy(flow)
                producer = rejected_flow["unlinkedNativePlayback"][1][
                    "nativeEventProducerRoutes"
                ][0]
                if label in {
                    "cross-script listener route",
                    "mismatched listener event key",
                }:
                    mutate(producer["listenerRoutes"][0])
                else:
                    mutate(producer)
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    config_dir = root / "map_test"
                    config_dir.mkdir()
                    (config_dir / "sc_map_test_1004.json").write_bytes(
                        spawner_wave_fixture()
                    )
                    rejected_edges = (
                        partial_order
                        ._spawner_wave_group_part_killed_story_edges(
                            rejected_flow,
                            candidates,
                            spawner_roots=[root],
                        )
                    )
                self.assertEqual(rejected_edges, [])

    def test_quest_state_typed_action_path_recovers_strict_story_order(self) -> None:
        candidates = {
            "cutscene_m1_1": "cutscene",
            "radio_m1_1": "radio",
            "radio_m1_2": "radio",
        }
        payload = mission_payload([])
        action_path = [9, 10, 11, 12]
        payload["flow"]["quests"] = [{
            "id": "m1_q#2",
            "storyConnections": [
                {
                    "key": key,
                    "relation": "levelscript_quest_completed_action",
                    "confidence": "native_typed_direct",
                    "event": "LevelEvent_OnQuestStateChanged",
                    "questState": 3,
                    "levelId": "map_test",
                    "scriptId": "1001",
                    "sourceFile": "LevelScriptData/map_test/1001.json",
                    "headerLocalId": 8,
                    "actionLocalId": local_id,
                    "actionPathIndex": index,
                    "actionPathLocalIds": action_path,
                    "nativeMappingId": "gameassembly-test-actionbase",
                }
                for key, local_id, index in (
                    ("cutscene_m1_1", 9, 0),
                    ("radio_m1_1", 11, 2),
                    ("radio_m1_2", 12, 3),
                )
            ],
        }]

        result = partial_order.build_mission_partial_order("m1", candidates, payload)

        edges = [
            edge for edge in result["directEdges"]
            if edge["kind"] == "levelscriptQuestStateActionPath"
        ]
        self.assertEqual(
            {(edge["from"], edge["to"]) for edge in edges},
            {
                ("cutscene_m1_1", "radio_m1_1"),
                ("radio_m1_1", "radio_m1_2"),
            },
        )
        self.assertTrue(all(edge["tier"] == "strong" for edge in edges))
        self.assertEqual(result["summary"]["comparableScenePairs"], 3)

    def test_native_control_path_prefix_recovers_strict_story_order(self) -> None:
        candidates = {"cutscene_m1_1": "cutscene", "dlg_m1_1": "dlg", "radio_m1_1": "radio"}
        payload = mission_payload([])
        owner = lambda path: {  # noqa: E731 - compact fixture helper
            "status": "exact_serialized_control_path",
            "headerName": "ScriptEvent_OnCustomEvent",
            "headerLocalId": 4,
            "path": [{"localId": local_id} for local_id in path],
        }
        payload["flow"]["missionStoryConnections"] = [
            {
                "key": "cutscene_m1_1",
                "levelScriptOccurrences": [{
                    "levelId": "map_test",
                    "scriptId": "70000000001",
                    "sourceFile": "fixture.json",
                    "nativeEventOwners": [owner([5])],
                }],
            },
            {
                "key": "dlg_m1_1",
                "nativeOccurrences": [{
                    "levelId": "map_test",
                    "scriptId": "70000000001",
                    "sourceFile": "fixture.json",
                    "nativeEventOwners": [owner([5, 6])],
                }],
            },
            {
                "key": "radio_m1_1",
                "nativeOccurrences": [{
                    "levelId": "map_test",
                    "scriptId": "70000000001",
                    "sourceFile": "fixture.json",
                    "nativeEventOwners": [owner([5, 6, 7])],
                }],
            },
        ]

        result = partial_order.build_mission_partial_order("m1", candidates, payload)

        native_edges = [
            edge for edge in result["directEdges"]
            if edge["kind"] == "levelscriptNativeControlPath"
        ]
        self.assertEqual(
            {(edge["from"], edge["to"]) for edge in native_edges},
            {
                ("cutscene_m1_1", "dlg_m1_1"),
                ("cutscene_m1_1", "radio_m1_1"),
                ("dlg_m1_1", "radio_m1_1"),
            },
        )
        self.assertTrue(all(edge["tier"] == "strong" for edge in native_edges))
        self.assertEqual(result["summary"]["comparableScenePairs"], 3)

    def test_while_action_path_is_reachability_not_global_story_order(self) -> None:
        candidates = {"radio_m1_1": "radio", "radio_m1_2": "radio"}
        payload = mission_payload([])

        def owner(path: list[tuple[int, str]]) -> dict:
            return {
                "status": "exact_serialized_control_path",
                "headerName": "ScriptEvent_OnLeaderEnterTriggerVolume",
                "headerLocalId": 4,
                "path": [
                    {"localId": local_id, "edge": edge}
                    for local_id, edge in path
                ],
            }

        payload["flow"]["missionStoryConnections"] = [
            {
                "key": "radio_m1_1",
                "levelScriptOccurrences": [{
                    "levelId": "map_test",
                    "scriptId": "70000000001",
                    "sourceFile": "fixture.json",
                    "nativeEventOwners": [owner([
                        (5, "ActionHeader.nextId"),
                        (6, "WhileAction.doAction"),
                    ])],
                }],
            },
            {
                "key": "radio_m1_2",
                "levelScriptOccurrences": [{
                    "levelId": "map_test",
                    "scriptId": "70000000001",
                    "sourceFile": "fixture.json",
                    "nativeEventOwners": [owner([
                        (5, "ActionHeader.nextId"),
                        (6, "WhileAction.doAction"),
                        (7, "ActionBase.nextId"),
                    ])],
                }],
            },
        ]

        result = partial_order.build_mission_partial_order(
            "m1",
            candidates,
            payload,
        )

        self.assertEqual(
            [],
            [
                edge
                for edge in result["directEdges"]
                if edge["kind"] == "levelscriptNativeControlPath"
            ],
        )

    def test_exact_native_path_admits_cross_owner_scene_context(self) -> None:
        candidates = {"radio_m1_1": "radio"}
        payload = mission_payload([])

        def owner(path: list[int], header_local_id: int = 4) -> dict:
            return {
                "status": "exact_serialized_control_path",
                "headerName": "ScriptEvent_OnLeaderEnterTriggerVolume",
                "headerLocalId": header_local_id,
                "path": [{"localId": local_id} for local_id in path],
            }

        payload["flow"]["missionStoryConnections"] = [
            {
                "key": "dlg_other_9",
                "levelScriptOccurrences": [{
                    "levelId": "map_test",
                    "scriptId": "70000000001",
                    "sourceFile": "fixture.json",
                    "nativeEventOwners": [owner([5])],
                }],
            },
            {
                "key": "radio_m1_1",
                "levelScriptOccurrences": [{
                    "levelId": "map_test",
                    "scriptId": "70000000001",
                    "sourceFile": "fixture.json",
                    "nativeEventOwners": [owner([5, 6])],
                }],
            },
        ]

        result = partial_order.build_mission_partial_order(
            "m1",
            candidates,
            payload,
        )

        self.assertEqual(
            result["nativeControlPathContextSceneKeys"],
            ["dlg_other_9"],
        )
        self.assertEqual(
            result["summary"]["nativeControlPathContextSceneCount"],
            1,
        )
        self.assertEqual(
            {
                (edge["from"], edge["to"])
                for edge in result["directEdges"]
                if edge["kind"] == "levelscriptNativeControlPath"
            },
            {("dlg_other_9", "radio_m1_1")},
        )
        membership = {
            node["key"]: node["membership"]
            for node in result["nodes"]
        }
        self.assertEqual(membership["radio_m1_1"], "index")
        self.assertEqual(
            membership["dlg_other_9"],
            "exactNativeControlPathContext",
        )

    def test_cross_owner_context_rejects_non_prefix_native_and_graph_clues(
        self,
    ) -> None:
        candidates = {"radio_m1_1": "radio"}
        payload = mission_payload([{
            "from": "dlg_other_graph",
            "to": "radio_m1_1",
            "kind": "levelscriptChain",
        }])

        def connection(
            key: str,
            path: list[int],
            header_local_id: int = 4,
        ) -> dict:
            return {
                "key": key,
                "levelScriptOccurrences": [{
                    "levelId": "map_test",
                    "scriptId": "70000000001",
                    "sourceFile": "fixture.json",
                    "nativeEventOwners": [{
                        "status": "exact_serialized_control_path",
                        "headerName": "ScriptEvent_OnLeaderEnterTriggerVolume",
                        "headerLocalId": header_local_id,
                        "path": [
                            {"localId": local_id}
                            for local_id in path
                        ],
                    }],
                }],
            }

        payload["flow"]["missionStoryConnections"] = [
            connection("radio_m1_1", [5, 6]),
            connection("dlg_other_equal", [5, 6]),
            connection("dlg_other_divergent", [5, 7]),
            connection("dlg_other_event", [5], header_local_id=40),
        ]

        result = partial_order.build_mission_partial_order(
            "m1",
            candidates,
            payload,
        )

        self.assertEqual(result["nativeControlPathContextSceneKeys"], [])
        self.assertEqual(
            {node["key"] for node in result["nodes"]},
            {"radio_m1_1"},
        )
        self.assertEqual(result["directEdges"], [])

    def test_native_control_paths_preserve_branch_arms_and_merge(self) -> None:
        candidates = {"radio_m1_true": "radio", "radio_m1_false": "radio"}
        payload = mission_payload([])

        def owner(path: list[tuple[int, str]]) -> dict:
            return {
                "status": "exact_serialized_control_path",
                "headerName": "ScriptEvent_OnCustomEvent",
                "headerLocalId": 4,
                "eventDetail": {
                    "type": "ScriptEvent_OnCustomEvent",
                    "eventKey": "branch_test",
                    "summary": "custom event branch_test",
                },
                "path": [
                    {"localId": local_id, "edge": edge}
                    for local_id, edge in path
                ],
            }

        def connection(key: str, path: list[tuple[int, str]]) -> dict:
            return {
                "key": key,
                "levelScriptOccurrences": [{
                    "levelId": "map_test",
                    "scriptId": "70000000001",
                    "sourceFile": "fixture.json",
                    "nativeEventOwners": [owner(path)],
                }],
            }

        payload["flow"]["missionStoryConnections"] = [
            connection("radio_m1_true", [
                (5, "ActionHeader.nextId"),
                (6, "IfElseAction.trueAction"),
                (9, "ActionBase.nextId"),
                (12, "ActionBase.nextId"),
            ]),
            connection("radio_m1_false", [
                (5, "ActionHeader.nextId"),
                (7, "IfElseAction.falseAction"),
                (9, "ActionBase.nextId"),
                (13, "ActionBase.nextId"),
            ]),
        ]
        predicate = {
            "status": "exact_unique_getter",
            "getterLocalId": 20,
            "getterName": "BooleanCompare",
            "getterUnionTag": "0x0004",
            "detailKind": "booleanCompare",
            "detail": {
                "comparerName": "Equal",
                "valueA": {"path": "enabled", "value": False},
                "valueB": {"value": True},
            },
        }
        for connection_row in payload["flow"]["missionStoryConnections"]:
            connection_row["levelScriptOccurrences"][0]["nativeEventOwners"][0]["path"][0][
                "branchPredicate"
            ] = predicate

        result = partial_order.build_mission_partial_order("m1", candidates, payload)

        branch = result["branches"]["nativeControlBranches"][0]
        self.assertEqual(branch["kind"], "ifElse")
        self.assertEqual(branch["branchLocalId"], 5)
        self.assertEqual(branch["predicate"]["getterName"], "BooleanCompare")
        self.assertEqual(branch["eventDetail"]["eventKey"], "branch_test")
        self.assertEqual(
            {arm["edge"] for arm in branch["arms"]},
            {"IfElseAction.trueAction", "IfElseAction.falseAction"},
        )
        merge = result["branches"]["nativeControlMerges"][0]
        self.assertEqual(merge["mergeLocalId"], 9)
        self.assertEqual(result["summary"]["nativeControlBranchCount"], 1)
        self.assertEqual(result["summary"]["nativeControlMergeCount"], 1)
        self.assertEqual(result["summary"]["nativeNamedPredicateCount"], 1)
        self.assertEqual(result["summary"]["nativeSemanticPredicateCount"], 1)
        self.assertEqual(result["summary"]["nativeClassOnlyPredicateCount"], 0)

    def test_chain_is_transitively_reduced(self) -> None:
        candidates = {"dlg_a": "dlg", "dlg_b": "dlg", "dlg_c": "dlg"}
        payload = mission_payload([
            {"from": "dlg_a", "to": "dlg_b", "kind": "questPrev"},
            {"from": "dlg_b", "to": "dlg_c", "kind": "questPrev"},
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

        self.assertEqual(result["summary"]["comparableScenePairs"], 1)
        self.assertEqual(result["summary"]["unorderedScenePairs"], 2)
        self.assertEqual(result["summary"]["supportedEdgeCount"], 1)
        option_group = result["branches"]["sceneGraphOptions"][0]
        self.assertTrue(option_group["isFork"])
        self.assertEqual(
            {arm["optionId"] for arm in option_group["arms"]},
            {"option_a_1", "option_a_2"},
        )

    def test_cycle_is_collapsed_without_internal_order(self) -> None:
        candidates = {"dlg_a": "dlg", "dlg_b": "dlg", "dlg_c": "dlg"}
        payload = mission_payload([
            {"from": "dlg_a", "to": "dlg_b", "kind": "authoredDirect"},
            {"from": "dlg_b", "to": "dlg_a", "kind": "authoredDirect"},
            {"from": "dlg_b", "to": "dlg_c", "kind": "questPrev"},
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

    def test_source_topology_without_playback_contract_does_not_create_order(self) -> None:
        candidates = {
            "dlg_a": "dlg",
            "dlg_b": "dlg",
            "dlg_c": "dlg",
            "dlg_d": "dlg",
            "dlg_e": "dlg",
        }
        payload = mission_payload([
            {"from": "dlg_a", "to": "dlg_b", "kind": "questSequence"},
            {"from": "dlg_b", "to": "dlg_c", "kind": "questFailGuard"},
            {"from": "dlg_c", "to": "dlg_d", "kind": "authoredMenu"},
            {"from": "dlg_d", "to": "dlg_e", "kind": "levelscriptSceneChain"},
        ])

        result = partial_order.build_mission_partial_order("m1", candidates, payload)

        self.assertEqual(result["summary"]["strongEdgeCount"], 0)
        self.assertEqual(result["summary"]["supportedEdgeCount"], 4)
        self.assertEqual(result["summary"]["comparableScenePairs"], 0)
        self.assertEqual(result["cycles"], [])
        self.assertEqual(set(result["weakOnlySceneKeys"]), set(candidates))

    def test_reciprocal_quest_file_projection_is_supported_not_chronology(self) -> None:
        candidates = {"dlg_a": "dlg", "dlg_b": "dlg"}
        payload = mission_payload([
            {
                "from": "dlg_a",
                "to": "dlg_b",
                "kind": "questPrev",
                "questIds": ["m1_q#1", "m1_q#2"],
            },
            {
                "from": "dlg_b",
                "to": "dlg_a",
                "kind": "questPrev",
                "questIds": ["m1_q#3", "m1_q#4"],
            },
        ])

        result = partial_order.build_mission_partial_order("m1", candidates, payload)

        self.assertEqual(result["summary"]["strongEdgeCount"], 0)
        self.assertEqual(result["summary"]["supportedEdgeCount"], 2)
        self.assertEqual(result["summary"]["comparableScenePairs"], 0)
        self.assertEqual(result["cycles"], [])
        self.assertTrue(all(
            edge.get("demotionReason") == "reciprocalQuestProjection"
            for edge in result["directEdges"]
        ))

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
        self.assertEqual(
            result["summary"]["actionableExcludedDialogLineOptionGroupCount"],
            1,
        )
        self.assertEqual(
            result["summary"]["closedExcludedDialogLineOptionGroupCount"],
            0,
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
        self.assertEqual(
            result["summary"]["branchingNoExplicitRouteGroupCount"],
            1,
        )
        self.assertEqual(
            result["summary"]["singleOptionNoExplicitRouteGroupCount"],
            0,
        )

    def test_single_option_without_route_is_not_a_missing_choice_branch(self) -> None:
        conv = {
            "key": "dlg_m1_ack",
            "optionGroups": [{
                "g": 1,
                "after": "dlg_m1_ack_001",
                "options": [{"id": "option_ack"}],
            }],
        }

        result = partial_order.build_mission_partial_order(
            "m1",
            {"dlg_m1_ack": "dlg"},
            mission_payload([]),
            [("conv/dlg_m1_ack.json", conv)],
        )

        self.assertEqual(
            result["summary"]["singleOptionNoExplicitRouteGroupCount"],
            1,
        )
        self.assertEqual(
            result["summary"]["branchingNoExplicitRouteGroupCount"],
            0,
        )
        self.assertEqual(
            result["branches"]["singleOptionNoExplicitRouteGroups"][0][
                "storyKey"
            ],
            "dlg_m1_ack",
        )

    def test_shared_and_cosmetic_exclusions_are_closed_option_evidence(self) -> None:
        conversations = [
            ("conv/dlg_m1_shared.json", {
                "key": "dlg_m1_shared",
                "optionGroups": [{
                    "g": 1,
                    "after": "dlg_m1_shared_001",
                    "options": [{"id": "option_1"}, {"id": "option_2"}],
                    "optionBranchRisk": {
                        "code": "sharedTimelineContinuation",
                        "reason": "defaultTrunkClipContinuation",
                    },
                }],
            }),
            ("conv/dlg_m1_cosmetic.json", {
                "key": "dlg_m1_cosmetic",
                "optionGroups": [{
                    "g": 1,
                    "after": "dlg_m1_cosmetic_001",
                    "options": [{"id": "option_1"}, {"id": "option_2"}],
                    "optionBranchRisk": {
                        "code": "cosmeticChoice",
                        "reason": "treeSourcedConvergence",
                    },
                }],
            }),
        ]

        result = partial_order.build_mission_partial_order(
            "m1",
            {
                "dlg_m1_shared": "dlg",
                "dlg_m1_cosmetic": "dlg",
            },
            mission_payload([]),
            conversations,
        )

        self.assertEqual(
            result["summary"]["closedExcludedDialogLineOptionGroupCount"],
            2,
        )
        self.assertEqual(
            result["summary"]["actionableExcludedDialogLineOptionGroupCount"],
            0,
        )
        self.assertEqual(
            len(result["branches"]["closedExcludedDialogLineOptions"]),
            2,
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
