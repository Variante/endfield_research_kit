import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import build_map_recovery_data as builder
from scripts.story_builder import level_bindings


class BuildMapRecoveryDataTests(unittest.TestCase):
    def setUp(self):
        builder._NATIVE_TRIGGER_FRONTIER_CACHE = None

    def test_exact_encounter_marker_requires_positive_typed_spawner_and_unique_host(self):
        level_id = "map_fixture"
        script_id = "42000010001"
        lsm_ptr = 42000010002
        spawner_id = 42000010003
        context = {
            "classification": "encounter_controller_property_contract",
            "mappingId": "gameassembly-2026-08-02-levelscriptmodule-save-prefix-encounter-contract",
            "runtimeType": "Beyond.Gameplay.Core.EncounterBase<T>",
            "dataType": "Beyond.Gameplay.EncounterData",
            "moduleId": str(lsm_ptr),
            "spawnerId": str(spawner_id),
            "matchedPropertyNames": [f"@{lsm_ptr}_spawner_id"],
        }
        observation = {
            "status": "exact_non_spatial_event_trigger",
            "levelId": level_id,
            "scriptId": script_id,
            "sourceFile": f"LevelScriptData/{level_id}/{script_id}.json",
            "listenerHeaderLocalId": 4,
            "eventName": "LevelEvent_OnEncounterActivated",
            "headerUnionTag": "0x0058",
            "headerSerializedMemberCount": 16,
            "eventDetail": {
                "type": "LevelEvent_OnEncounterActivated",
                "lsmPtrFilter": lsm_ptr,
                "lsmPtrOutputPresent": False,
                "payloadShape": "constant-lsm-pointer-null-output-exact-prefix",
                "payloadSchemaStatus": "exact_current_build_memorypack_fields",
                "payloadSchemaMappingId": "gameassembly-2026-07-17-memorypack-native-event-fields",
                "serverExchange": False,
                "serializedMissionOrQuestId": False,
            },
        }
        report = {
            "rows": [{
                "levelId": level_id,
                "scriptId": script_id,
                "encounterControllerContexts": [context],
            }],
            "storyTriggerZoneCoverage": {"rows": [{
                "storyKey": "radio_fixture",
                "observations": [observation],
            }]},
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = root / "export_full/structured/StreamingAssets/Data/Json/SpawnerConfig" / level_id / f"sc_{level_id}_{spawner_id}.json"
            config.parent.mkdir(parents=True)
            config.write_bytes(b"config")
            leveldata = root / "export_full/structured/StreamingAssets/Data/Json/LevelData" / level_id / "host.json"
            leveldata.parent.mkdir(parents=True)
            name = f"sc_{level_id}_{spawner_id}".encode("ascii")
            leveldata.write_bytes(
                len(name).to_bytes(4, "little")
                + name
                + b"\x00"
                + struct.pack("<6f", 1.0, 2.0, 3.0, 0.0, 90.0, 0.0)
            )
            with (
                mock.patch.object(builder, "ROOT", root),
                mock.patch.object(builder, "_native_trigger_frontier", return_value=report),
            ):
                markers = builder._exact_story_encounter_markers(level_id, "CN")
                self.assertEqual(1, len(markers))
                self.assertEqual(["radio_fixture"], markers[0]["sceneKeys"])
                self.assertEqual(
                    "unresolved_non_owning",
                    markers[0]["missionOwnershipStatus"],
                )
                report["rows"][0]["encounterControllerContexts"][0]["spawnerId"] = "0"
                self.assertEqual(
                    [],
                    builder._exact_story_encounter_markers(level_id, "CN"),
                )
                report["rows"][0]["encounterControllerContexts"][0]["spawnerId"] = str(spawner_id)
                duplicate = leveldata.with_name("other.json")
                duplicate.write_bytes(leveldata.read_bytes())
                self.assertEqual(
                    [],
                    builder._exact_story_encounter_markers(level_id, "CN"),
                )

    def test_exact_proxy_patrol_event_index_requires_unique_equal_npc_join(self):
        report = {"storyTriggerZoneCoverage": {"rows": [{
            "storyKey": "radio_proxy_patrol",
            "observations": [{
                "status": "exact_non_spatial_event_trigger",
                "levelId": "map_fixture",
                "scriptId": "42000010001",
                "listenerHeaderLocalId": 9,
                "eventName": "LevelEvent_OnProxyPatrolCheckpointReach",
                "sourceFile": "LevelScriptData/map_fixture/42000010001.json",
                "eventDetail": {
                    "payloadSchemaStatus": "exact_current_build_memorypack_fields",
                    "payloadSchemaMappingId": "gameassembly-2026-07-17-memorypack-native-event-fields",
                    "payloadShape": "constant-proxy-patrol-checkpoint-and-outputs-exact-eof",
                    "serverExchange": False,
                    "serializedMissionOrQuestId": False,
                    "proxyIdFilter": "npc_fixture",
                    "patrolIdFilter": 10000,
                    "pointIndexFilter": 4,
                },
            }],
        }]}}
        registry = {"npcProxyBriefInfos": {"4200000101": {
            "segmentIdGlobal": 4200000101,
            "proxyId": "npc_fixture",
            "position": {"x": 1.0, "y": 2.0, "z": 3.0},
        }}}
        table = {"dataTable": {"npc_fixture": {
            "position": {"x": 1.0, "y": 2.0, "z": 3.0},
            "rotation": {"x": 0.0, "y": 90.0, "z": 0.0},
        }}}

        def load(path, default):
            return table if str(path).endswith("NpcProxyTable.json") else registry

        with (
            mock.patch.object(builder, "_native_trigger_frontier", return_value=report),
            mock.patch.object(builder, "_level_catalog", return_value={"map_fixture": 42}),
            mock.patch.object(builder, "_load_json", side_effect=load),
        ):
            index = builder._exact_story_proxy_patrol_event_index("map_fixture")
        self.assertEqual(list(index), ["npc:4200000101"])
        binding = index["npc:4200000101"][0]
        self.assertEqual("exact_proxy_patrol_event_target", binding["status"])
        self.assertEqual("unresolved", binding["runtimeCheckpointPositionStatus"])

        table["dataTable"]["npc_fixture"]["position"]["x"] = 1.5
        with (
            mock.patch.object(builder, "_native_trigger_frontier", return_value=report),
            mock.patch.object(builder, "_level_catalog", return_value={"map_fixture": 42}),
            mock.patch.object(builder, "_load_json", side_effect=load),
        ):
            self.assertEqual(
                {}, builder._exact_story_proxy_patrol_event_index("map_fixture")
            )

    def test_spawner_marker_requires_complete_validated_native_payload(self):
        detail = {
            "type": "LevelEvent_OnSpawnerGroupBegin",
            "payloadDecodeStatus": "exact_complete_subtype",
            "payloadSchemaStatus": "exact_current_build_memorypack_fields",
            "payloadSchemaMappingId": "gameassembly-2026-07-17-memorypack-native-event-fields",
            "spawnerFilterId": 420001,
        }
        report = {"storyTriggerZoneCoverage": {"rows": [{
            "storyKey": "radio_spawner",
            "observations": [{
                "status": "exact_non_spatial_event_trigger",
                "levelId": "map_fixture",
                "eventName": "LevelEvent_OnSpawnerGroupBegin",
                "sourceFile": "LevelScriptData/map_fixture/1001.json",
                "eventDetail": detail,
            }],
        }]}}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "export_full/structured/StreamingAssets/Data/Json/SpawnerConfig/map_fixture/sc_map_fixture_420001.json"
            config.parent.mkdir(parents=True)
            config.write_bytes(b"config")
            leveldata = root / "export_full/structured/Persistent/Data/Json/LevelData/map_fixture/map_fixture_lv_data.json"
            leveldata.parent.mkdir(parents=True)
            name = b"sc_map_fixture_420001"
            leveldata.write_bytes(
                struct.pack("<I", len(name)) + name + b"\x00"
                + struct.pack("<6f", 1.0, 2.0, 3.0, 0.0, 90.0, 0.0)
            )
            with (
                mock.patch.object(builder, "ROOT", root),
                mock.patch.object(builder, "_native_trigger_frontier", return_value=report),
            ):
                markers = builder._exact_story_spawner_markers("map_fixture", "CN")
                self.assertEqual(1, len(markers))
                self.assertEqual({"x": 1.0, "y": 2.0, "z": 3.0}, markers[0]["position"])

                detail["payloadSchemaMappingId"] = "wrong-build"
                self.assertEqual([], builder._exact_story_spawner_markers("map_fixture", "CN"))

    def test_proxy_patrol_checkpoint_context_uses_unique_typed_patrol_point(self):
        report = {"storyTriggerZoneCoverage": {"rows": [{
            "storyKey": "radio_checkpoint",
            "observations": [{
                "status": "exact_non_spatial_event_trigger",
                "levelId": "map_fixture",
                "scriptId": "1001",
                "listenerHeaderLocalId": 9,
                "eventName": "LevelEvent_OnProxyPatrolCheckpointReach",
                "sourceFile": "LevelScriptData/map_fixture/1001.json",
                "eventDetail": {
                    "payloadSchemaStatus": "exact_current_build_memorypack_fields",
                    "payloadSchemaMappingId": "gameassembly-2026-07-17-memorypack-native-event-fields",
                    "payloadShape": "constant-proxy-patrol-checkpoint-and-outputs-exact-eof",
                    "serverExchange": False,
                    "serializedMissionOrQuestId": False,
                    "proxyIdFilter": "npc_fixture",
                    "patrolIdFilter": 10000,
                    "pointIndexFilter": 1,
                },
            }],
        }]}}
        decoded = {
            "status": "exactNonemptyTypedPatrolList",
            "patrols": [{
                "patrolId": 10000,
                "pointCount": 2,
                "points": [
                    {"pointIndex": 0, "position": {"x": 1.0, "y": 2.0, "z": 3.0}},
                    {"pointIndex": 1, "position": {"x": 4.0, "y": 5.0, "z": 6.0}},
                ],
            }],
        }
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "fixture.json"
            source.write_bytes(b"fixture")
            with (
                mock.patch.object(builder, "_native_trigger_frontier", return_value=report),
                mock.patch.object(builder, "_active_leveldata_files", return_value=[source]),
                mock.patch.object(builder, "decode_leveldata_npc_patrol_list", return_value=decoded),
            ):
                contexts = builder._exact_story_proxy_patrol_checkpoint_contexts(
                    "map_fixture"
                )
        self.assertEqual(1, len(contexts))
        self.assertEqual({"x": 4.0, "y": 5.0, "z": 6.0}, contexts[0]["position"])
        self.assertTrue(
            builder._exact_story_patrol_checkpoint_markers(contexts, "CN")[0][
                "authoredCheckpointPosition"
            ]
        )

        decoded["patrols"].append(dict(decoded["patrols"][0]))
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "fixture.json"
            source.write_bytes(b"fixture")
            with (
                mock.patch.object(builder, "_native_trigger_frontier", return_value=report),
                mock.patch.object(builder, "_active_leveldata_files", return_value=[source]),
                mock.patch.object(builder, "decode_leveldata_npc_patrol_list", return_value=decoded),
            ):
                self.assertEqual(
                    [],
                    builder._exact_story_proxy_patrol_checkpoint_contexts("map_fixture"),
                )

    def test_npc_patrol_checkpoint_context_keeps_dynamic_identity_non_owning(self):
        report = {"storyTriggerZoneCoverage": {"rows": [{
            "storyKey": "radio_dynamic_npc_checkpoint",
            "observations": [{
                "status": "exact_non_spatial_event_trigger",
                "levelId": "map_fixture",
                "scriptId": "1001",
                "listenerHeaderLocalId": 4,
                "eventName": "LevelEvent_OnNpcPatrolCheckpointReach",
                "sourceFile": "LevelScriptData/map_fixture/1001.json",
                "eventDetail": {
                    "payloadSchemaStatus": "exact_current_build_memorypack_fields",
                    "payloadSchemaMappingId": "gameassembly-2026-07-17-memorypack-native-event-fields",
                    "payloadShape": "dynamic-npc-patrol-checkpoint-fields",
                    "serverExchange": False,
                    "serializedMissionOrQuestId": False,
                    "npcEntityFilter": {
                        "logicId": 0,
                        "slotId": 0,
                        "useSlotId": False,
                        "idRef": -1,
                        "paramSource": 200,
                        "path": "Robot2",
                    },
                    "patrolIdFilter": 10000,
                    "checkpointIndexFilter": 1,
                },
            }],
        }]}}
        decoded = {
            "status": "exactNonemptyTypedPatrolList",
            "patrols": [{
                "patrolId": 10000,
                "pointCount": 2,
                "points": [
                    {"pointIndex": 0, "position": {"x": 1.0, "y": 2.0, "z": 3.0}},
                    {"pointIndex": 1, "position": {"x": 4.0, "y": 5.0, "z": 6.0}},
                ],
            }],
        }
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "fixture.json"
            source.write_bytes(b"fixture")
            with (
                mock.patch.object(builder, "_native_trigger_frontier", return_value=report),
                mock.patch.object(builder, "_active_leveldata_files", return_value=[source]),
                mock.patch.object(builder, "decode_leveldata_npc_patrol_list", return_value=decoded),
            ):
                contexts = builder._exact_story_npc_patrol_checkpoint_contexts("map_fixture")
        self.assertEqual(1, len(contexts))
        self.assertEqual("dynamic_script_property", contexts[0]["runtimeNpcIdentityStatus"])
        marker = builder._exact_story_patrol_checkpoint_markers(contexts, "CN")[0]
        self.assertEqual("npc_patrol_checkpoint", marker["subKind"])
        self.assertFalse(marker["ownership"])
        self.assertEqual("unresolved", marker["runtimeNpcPositionStatus"])

        decoded["patrols"].append(dict(decoded["patrols"][0]))
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "fixture.json"
            source.write_bytes(b"fixture")
            with (
                mock.patch.object(builder, "_native_trigger_frontier", return_value=report),
                mock.patch.object(builder, "_active_leveldata_files", return_value=[source]),
                mock.patch.object(builder, "decode_leveldata_npc_patrol_list", return_value=decoded),
            ):
                self.assertEqual([], builder._exact_story_npc_patrol_checkpoint_contexts("map_fixture"))

    def test_exact_story_entity_event_index_accepts_getter_validated_constant_target(self):
        exact = {
            "storyTriggerZoneCoverage": {"rows": [{
                "storyKey": "radio_exact",
                "observations": [{
                    "status": "exact_non_spatial_event_trigger",
                    "levelId": "map_fixture",
                    "scriptId": "1001",
                    "eventName": "EntityEvent_OnInteractiveStateChanged",
                    "sourceFile": "LevelScriptData/map_fixture/1001.json",
                    "eventDetail": {
                        "type": "EntityEvent_OnInteractiveStateChanged",
                        "payloadSchemaStatus": "exact_current_build_memorypack_fields",
                        "payloadSchemaMappingId": "native-event-v1",
                        "serverExchange": False,
                        "serializedMissionOrQuestId": False,
                        "entityEventScope": "specified-entity",
                        "triggerTarget": "SPECIFY_ENTITY",
                        "targetEntity": {"logicId": 0, "slotId": 40001, "useSlotId": True},
                        "targetEntityParam": {"idRef": -1, "paramSource": 0, "path": None},
                        "targetEntityListPresent": False,
                        "targetEntityListOutputPresent": False,
                        "validateParam": {"constValue": True, "idRef": -1, "paramSource": 0, "path": None},
                    },
                }],
            }]},
        }
        with mock.patch.object(builder, "_load_json", return_value=exact):
            index = builder._exact_story_entity_event_index("map_fixture")
        self.assertEqual(list(index), ["script:1001:40001"])
        self.assertEqual(index["script:1001:40001"][0]["status"], "exact_entity_event_target")

        validate = exact["storyTriggerZoneCoverage"]["rows"][0]["observations"][0]["eventDetail"]["validateParam"]
        validate.update({"idRef": 7, "paramSource": -1})
        with mock.patch.object(builder, "_load_json", return_value=exact):
            index = builder._exact_story_entity_event_index("map_fixture")
        binding = index["script:1001:40001"][0]
        self.assertEqual("exact_structure_only", binding["validateParamStatus"])
        self.assertEqual(7, binding["validateParam"]["idRef"])
        self.assertFalse(binding["activation"])

    def test_exact_story_entity_event_index_rejects_dynamic_target(self):
        report = {"storyTriggerZoneCoverage": {"rows": [{
            "storyKey": "radio_dynamic_target",
            "observations": [{
                "status": "exact_non_spatial_event_trigger",
                "levelId": "map_fixture",
                "scriptId": "1001",
                "eventName": "EntityEvent_OnInteractiveStateChanged",
                "eventDetail": {
                    "payloadSchemaStatus": "exact_current_build_memorypack_fields",
                    "serverExchange": False,
                    "serializedMissionOrQuestId": False,
                    "entityEventScope": "specified-entity",
                    "triggerTarget": "SPECIFY_ENTITY",
                    "targetEntity": {
                        "logicId": 0, "slotId": 0, "useSlotId": False,
                    },
                    "targetEntityParam": {
                        "idRef": 9, "paramSource": -1, "path": None,
                    },
                    "targetEntityListPresent": False,
                    "targetEntityListOutputPresent": False,
                    "validateParam": {
                        "constValue": True,
                        "idRef": 7,
                        "paramSource": -1,
                        "path": None,
                    },
                },
            }],
        }]}}
        with mock.patch.object(builder, "_load_json", return_value=report):
            self.assertEqual({}, builder._exact_story_entity_event_index("map_fixture"))

    def test_exact_story_entity_event_index_keeps_multiple_targets_separate_nonactivating(self):
        observations = []
        for header_id, logic_id in ((12, 10101), (19, 10102)):
            observations.append({
                "status": "exact_non_spatial_event_trigger",
                "levelId": "map_fixture",
                "scriptId": "1001",
                "listenerHeaderLocalId": header_id,
                "eventName": "EntityEvent_OnInteractiveStateChanged",
                "eventDetail": {
                    "payloadSchemaStatus": "exact_current_build_memorypack_fields",
                    "serverExchange": False,
                    "serializedMissionOrQuestId": False,
                    "entityEventScope": "specified-entity",
                    "triggerTarget": "SPECIFY_ENTITY",
                    "targetEntity": {
                        "logicId": logic_id, "slotId": 0, "useSlotId": False,
                    },
                    "targetEntityParam": {
                        "idRef": -1, "paramSource": 0, "path": None,
                    },
                    "targetEntityListPresent": False,
                    "targetEntityListOutputPresent": False,
                    "validateParam": {
                        "constValue": True,
                        "idRef": header_id - 1,
                        "paramSource": -1,
                        "path": None,
                    },
                },
            })
        report = {"storyTriggerZoneCoverage": {"rows": [{
            "storyKey": "radio_multiple_targets",
            "observations": observations,
        }]}}
        with mock.patch.object(builder, "_load_json", return_value=report):
            index = builder._exact_story_entity_event_index("map_fixture")
        self.assertEqual(["world:10101", "world:10102"], list(index))
        self.assertEqual(
            [12, 19],
            [index[identity][0]["headerLocalId"] for identity in index],
        )
        self.assertTrue(all(
            binding["activation"] is False
            for bindings in index.values()
            for binding in bindings
        ))

    def test_exact_story_entity_event_index_accepts_bounded_single_entity_die_list(self):
        report = {"storyTriggerZoneCoverage": {"rows": [{
            "storyKey": "radio_die",
            "observations": [{
                "status": "exact_non_spatial_event_trigger",
                "levelId": "map_fixture",
                "scriptId": "1001",
                "eventName": "LevelEvent_OnAnyEntityDie",
                "eventDetail": {
                    "payloadSchemaStatus": "exact_current_build_memorypack_fields",
                    "serverExchange": False,
                    "serializedMissionOrQuestId": False,
                    "filterByList": True,
                    "isMonsterFilter": True,
                    "payloadShape": "constant-entity-list-and-bool-filters-exact-eof",
                    "entityListFilter": [{
                        "logicId": 0, "slotId": 30004, "useSlotId": True,
                    }],
                },
            }],
        }]}}
        with mock.patch.object(builder, "_load_json", return_value=report):
            index = builder._exact_story_entity_event_index("map_fixture")
        self.assertEqual(list(index), ["script:1001:30004"])

        report["storyTriggerZoneCoverage"]["rows"][0]["observations"][0]["eventDetail"]["filterByList"] = False
        with mock.patch.object(builder, "_load_json", return_value=report):
            self.assertEqual(builder._exact_story_entity_event_index("map_fixture"), {})

    def test_exact_story_entity_event_index_accepts_exact_inherited_scope_only(self):
        report = {"storyTriggerZoneCoverage": {"rows": [{
            "storyKey": "radio_scope",
            "observations": [{
                "status": "non_spatial_event_payload_unresolved",
                "levelId": "map_fixture",
                "scriptId": "1001",
                "listenerHeaderLocalId": 19,
                "eventName": "EntityEvent_OnEntityDestroy",
                "eventDetail": {
                    "payloadSchemaStatus": "exact_current_build_entity_event_scope_fields",
                    "serverExchange": False,
                    "serializedMissionOrQuestId": False,
                    "entityEventScope": "specified-entity",
                    "triggerTarget": "SPECIFY_ENTITY",
                    "targetEntity": {"logicId": 101, "slotId": 0, "useSlotId": False},
                    "targetEntityParam": {"idRef": -1, "paramSource": 0, "path": None},
                    "targetEntityListPresent": False,
                    "targetEntityListOutputPresent": False,
                    "validateParam": {"constValue": True, "idRef": -1, "paramSource": 0, "path": None},
                },
            }],
        }]}}
        with mock.patch.object(builder, "_load_json", return_value=report):
            index = builder._exact_story_entity_event_index("map_fixture")
        self.assertEqual(list(index), ["world:101"])
        self.assertEqual(index["world:101"][0]["headerLocalId"], 19)

    def test_exact_story_trigger_levels_include_undeclared_trigger_coordinate_spaces(self):
        report = {
            "storyTriggerZoneCoverage": {"rows": [{
                "observations": [
                    {
                        "status": "exact_local_trigger_volume",
                        "levelId": "dung_trigger_only",
                        "decodedShape": [{
                            "shapeType": "Box",
                            "position": {"x": 1.0, "y": 2.0, "z": 3.0},
                        }],
                    },
                    {
                        "status": "trigger_event_known_spatial_unresolved",
                        "levelId": "unresolved_only",
                        "decodedShape": [],
                    },
                ],
            }]},
        }
        with mock.patch.object(builder, "_load_json", return_value=report):
            self.assertEqual(
                builder._exact_story_trigger_level_ids(),
                {"dung_trigger_only"},
            )

    def test_entity_ptr_dynamic_kinds_are_normalized_without_resolution(self):
        fixtures = [
            ({"idRef": 7, "paramSource": -1, "path": None}, "getter_id_ref"),
            ({"idRef": -1, "paramSource": 100, "path": "$12@entity"}, "local_output_ref"),
            ({"idRef": -1, "paramSource": 100, "path": "target"}, "named_action_argument"),
            ({"idRef": -1, "paramSource": 200, "path": "owner"}, "named_script_variable"),
            ({"idRef": -1, "paramSource": 200, "path": None}, "unnamed_script_variable"),
        ]
        for pointer, expected_kind in fixtures:
            with self.subTest(kind=expected_kind):
                self.assertEqual(
                    level_bindings._entity_ptr_field_state(pointer),
                    ("dynamic", expected_kind),
                )
        self.assertEqual(
            level_bindings._entity_ptr_field_state(
                {"idRef": -1, "paramSource": 0, "path": None}
            ),
            ("constant", None),
        )

    def test_action_binding_report_keeps_dynamic_refs_unplaced(self):
        dynamic = {
            "state": "dynamic",
            "dynamicKind": "local_output_ref",
            "idRef": -1,
            "paramSource": 100,
            "path": "$12@entity",
            "sourceFile": "LevelScriptData/map_fixture/1.json",
            "scriptId": "1",
            "actionName": "EntityCastSkill",
            "actionRecordOffset": 100,
            "fieldName": "_targetEntity",
            "memberOrdinalZeroBased": 12,
            "nativeFieldOffset": 64,
            "pointerOffset": 120,
            "pointerEndOffset": 160,
        }
        report = builder._action_binding_report([{
            "id": "map_fixture",
            "levelId": "map_fixture",
            "markers": [],
            "unplacedActionTargets": {"targets": []},
            "actionEntityFieldDiagnostics": {"fields": [dynamic]},
        }], "CN")

        self.assertEqual(report["dynamicReferenceSummary"]["count"], 1)
        self.assertEqual(
            report["dynamicReferenceSummary"]["resolvedDynamicReferenceCount"],
            0,
        )
        self.assertEqual(
            report["dynamicReferenceSummary"]["unresolvedDynamicReferenceCount"],
            1,
        )
        self.assertEqual(
            report["dynamicReferenceSummary"]["kindCounts"],
            {"local_output_ref": 1},
        )
        self.assertEqual(report["unplacedDynamicReferences"][0]["path"], "$12@entity")
        self.assertEqual(report["maps"][0]["slots"], [])

    def test_action_binding_report_preserves_resolved_dynamic_evidence(self):
        getter = {
            "state": "dynamic",
            "dynamicKind": "getter_id_ref",
            "idRef": 7,
            "paramSource": -1,
            "path": None,
            "sourceFile": "LevelScriptData/map_fixture/1.json",
            "scriptId": "1",
            "actionName": "NpcEnableStim",
            "actionRecordOffset": 100,
            "fieldName": "_target",
            "pointerOffset": 120,
            "pointerEndOffset": 147,
            "getterResolution": {
                "status": "exact_constant_proxy_id_lookup",
                "getterLocalId": 7,
                "proxyId": "npc_exact",
            },
        }
        output_alias = {
            **getter,
            "dynamicKind": "local_output_ref",
            "idRef": -1,
            "paramSource": 100,
            "path": "$12@entity",
            "pointerOffset": 150,
            "pointerEndOffset": 187,
            "getterResolution": None,
            "localOutputAliasResolution": {
                "status": "exact_constant_filter_alias",
                "producerHeaderLocalId": 12,
            },
        }
        unresolved = {
            **getter,
            "idRef": 8,
            "pointerOffset": 190,
            "pointerEndOffset": 217,
            "getterResolution": {
                "status": "validated_runtime_dependent",
                "getterLocalId": 8,
            },
        }
        runtime_non_spatial = {
            **getter,
            "dynamicKind": "local_output_ref",
            "idRef": -1,
            "paramSource": 100,
            "path": "$20@_entity",
            "pointerOffset": 220,
            "pointerEndOffset": 257,
            "getterResolution": None,
            "nativeOutputAliasContractStatus": "validated",
            "localOutputAliasResolution": {
                "status": "runtime_list_element_non_spatial",
                "nativeMappingId": "native-output-contract",
            },
        }
        report = builder._action_binding_report([{
            "id": "map_fixture",
            "levelId": "map_fixture",
            "markers": [{
                "identity": "npc:101",
                "actions": [
                    {
                        "sourceFile": getter["sourceFile"],
                        "actionRecordOffset": getter["actionRecordOffset"],
                        "pointerOffset": getter["pointerOffset"],
                        "entityPtrGetterResolution": getter["getterResolution"],
                    },
                    {
                        "sourceFile": output_alias["sourceFile"],
                        "actionRecordOffset": output_alias["actionRecordOffset"],
                        "pointerOffset": output_alias["pointerOffset"],
                        "entityPtrOutputAliasEvidence": (
                            output_alias["localOutputAliasResolution"]
                        ),
                    },
                ],
                "unresolvedActionReferences": [],
            }],
            "unplacedActionTargets": {"targets": []},
            "actionEntityFieldDiagnostics": {
                "fields": [getter, output_alias, unresolved, runtime_non_spatial]
            },
        }], "CN")

        summary = report["dynamicReferenceSummary"]
        self.assertEqual(summary["count"], 4)
        self.assertEqual(summary["resolvedDynamicReferenceCount"], 2)
        self.assertEqual(
            summary["exactSpatiallyResolvedDynamicReferenceCount"], 2
        )
        self.assertEqual(
            summary["validatedRuntimeNonSpatialReferenceCount"], 1
        )
        self.assertEqual(summary["unresolvedDynamicReferenceCount"], 1)
        self.assertEqual(
            [
                (row["pointerOffset"], row["dynamicResolutionClass"])
                for row in report["unplacedDynamicReferences"]
            ],
            [(190, "unresolved"), (220, "validated_runtime_non_spatial")],
        )
        self.assertEqual(len(report["entityPtrFieldDiagnostics"]), 4)
        self.assertEqual(
            report["entityPtrFieldDiagnostics"][0]["getterResolution"]["proxyId"],
            "npc_exact",
        )

    def test_local_output_diagnostics_distinguish_runtime_producer_domains(self):
        contracts, _audit = (
            level_bindings.load_entityptr_output_alias_contract()
        )

        def classify(path, *, actions=None, headers=None, aliases=None, paths=None):
            return level_bindings._classify_levelscript_entityptr_output_reference(
                path,
                prepared={
                    "actionByLocal": actions or {},
                    "headerByLocal": headers or {},
                },
                contracts=contracts,
                aliases=aliases or {},
                consumer_paths=paths or [],
            )

        repeat = classify(
            "$12@_entity",
            actions={12: {
                "start": 40,
                "unionTag": 0x0391,
                "serializedMemberCount": 12,
            }},
        )
        spawned = classify(
            "$7@_entityOutput",
            headers={7: {
                "start": 50,
                "unionTag": 0x0094,
                "serializedMemberCount": 21,
            }},
        )
        event = classify(
            "$8@_entityOutput",
            headers={8: {
                "start": 60,
                "unionTag": 0x00BC,
                "serializedMemberCount": 20,
            }},
        )
        patrol_event = classify(
            "$9@_entityOutput",
            headers={9: {
                "start": 70,
                "unionTag": 0x0066,
                "serializedMemberCount": 18,
            }},
        )

        self.assertEqual(
            repeat["producerName"],
            "Beyond.Gameplay.Actions.RepeatEntityPtrListAction",
        )
        self.assertEqual(repeat["status"], "runtime_list_element_non_spatial")
        self.assertEqual(repeat["aliasStatus"], "validated_non_alias")
        self.assertEqual(
            repeat["failureGate"],
            "native_runtime_list_element_is_not_constant_alias",
        )
        self.assertEqual(spawned["status"], "runtime_spawned_entity")
        self.assertEqual(event["status"], "runtime_event_entity")
        self.assertEqual(patrol_event["status"], "runtime_event_entity")
        self.assertEqual(event["producerRecordOffset"], 60)

    def test_local_output_diagnostics_preserve_alias_and_non_alias_gates(self):
        contracts, _audit = (
            level_bindings.load_entityptr_output_alias_contract()
        )
        exact_alias = {
            "status": "exact_constant_filter_alias",
            "producerHeaderLocalId": 5,
            "constantPointerOffset": 100,
        }
        exact = level_bindings._classify_levelscript_entityptr_output_reference(
            "$5@_entity",
            prepared={
                "actionByLocal": {},
                "headerByLocal": {5: {
                    "start": 20,
                    "unionTag": 0x00A0,
                    "serializedMemberCount": 16,
                }},
            },
            contracts=contracts,
            aliases={"$5@_entity": exact_alias},
            consumer_paths=[{
                "status": "exact_serialized_control_path",
                "headerLocalId": 5,
            }],
        )
        non_alias = level_bindings._classify_levelscript_entityptr_output_reference(
            "$9@_entityOutput",
            prepared={
                "actionByLocal": {},
                "headerByLocal": {9: {
                    "start": 30,
                    "unionTag": 0x00BD,
                    "serializedMemberCount": 20,
                }},
            },
            contracts=contracts,
            aliases={},
            consumer_paths=[],
        )

        self.assertEqual(exact["status"], "exact_constant_filter_alias")
        self.assertIsNone(exact["failureGate"])
        self.assertEqual(exact["controlPathStatus"],
                         "exact_same_header_execution_path")
        self.assertEqual(non_alias["status"], "validated_non_alias")
        self.assertEqual(non_alias["failureGate"],
                         "native_output_is_not_filter_alias")

    def test_named_entityptr_initializer_requires_exact_consumer_script_host(self):
        pointer = {"idRef": -1, "paramSource": 200, "path": "puzzle4"}
        brief = {
            "properties": [{
                "name": "puzzle4",
                "valueType": 13,
                "atomCount": 1,
                "atoms": [{"valueBit64": 10100020736, "text": ""}],
            }],
            "refWorldEntityIds": ["10100020736"],
        }
        mismatch = level_bindings._resolve_levelscript_named_entityptr_initial_value(
            pointer,
            level_id="map02_lv001",
            script_id="10100020024",
            brief_hosts_by_script={"different_receiver_context": [{"brief": brief}]},
            world_briefs={"10100020736": {"detailId": "int_target"}},
            native_audit={"status": "validated"},
            graph_writer_count=0,
        )
        exact = level_bindings._resolve_levelscript_named_entityptr_initial_value(
            pointer,
            level_id="map02_lv001",
            script_id="10100020024",
            brief_hosts_by_script={"10100020024": [{
                "brief": brief,
                "sourceFile": "LevelData/map02_lv001/sub.json",
                "sourceSha256": "ABC",
            }]},
            world_briefs={"10100020736": {"detailId": "int_target"}},
            native_audit={"status": "validated"},
            graph_writer_count=2,
        )

        self.assertEqual(mismatch["failureGate"], "unique_exact_script_brief_host")
        self.assertEqual(exact["status"],
                         "validated_initial_entityptr_value_nonfinal")
        self.assertEqual(exact["briefHostScriptId"], "10100020024")
        self.assertEqual(exact["initialEntityLogicId"], 10100020736)
        self.assertEqual(exact["graphWriterCount"], 2)
        self.assertTrue(exact["diagnosticOnly"])
        self.assertTrue(exact["mutableAfterBind"])
        self.assertFalse(exact["allowTargetPromotion"])
        self.assertIn("mutable", exact["evidenceBoundary"])

    def test_named_entityptr_initializer_is_nonspatial_dynamic_summary_class(self):
        diagnostic = {
            "state": "dynamic",
            "dynamicKind": "named_script_variable",
            "sourceFile": "LevelScriptData/map/1.json",
            "actionRecordOffset": 10,
            "pointerOffset": 20,
            "namedEntityPtrResolution": {
                "status": "validated_initial_entityptr_value_nonfinal",
                "nativeMappingId": "native-property-init",
                "allowTargetPromotion": False,
            },
            "nativePropertyInitializationContractStatus": "validated",
        }
        report = builder._action_binding_report([{
            "id": "map",
            "levelId": "map",
            "markers": [],
            "actionEntityFieldDiagnostics": {"fields": [diagnostic]},
        }], "CN")

        summary = report["dynamicReferenceSummary"]
        self.assertEqual(summary["count"], 1)
        self.assertEqual(summary["exactSpatiallyResolvedDynamicReferenceCount"], 0)
        self.assertEqual(summary["validatedRuntimeNonSpatialReferenceCount"], 1)
        self.assertEqual(summary["unresolvedDynamicReferenceCount"], 0)
        self.assertEqual(
            report["unplacedDynamicReferences"][0]["dynamicResolutionClass"],
            "validated_runtime_non_spatial",
        )
        self.assertEqual(
            report["unplacedDynamicReferences"][0]["dynamicResolutionFailureGate"],
            "native_validated_runtime_non_spatial",
        )

    def test_dynamic_summary_assigns_actionable_gate_to_every_unresolved_family(self):
        rows = [
            {"state": "dynamic", "dynamicKind": "named_action_argument"},
            {"state": "dynamic", "dynamicKind": "unnamed_script_variable"},
            {"state": "dynamic", "dynamicKind": "opaque_dynamic"},
            {
                "state": "dynamic",
                "dynamicKind": "getter_id_ref",
                "getterResolution": {"status": "validated_runtime_dependent"},
            },
            {
                "state": "dynamic",
                "dynamicKind": "local_output_ref",
                "localOutputAliasResolution": {
                    "status": "exact_constant_filter_alias",
                    "failureGate": None,
                },
            },
        ]
        report = builder._action_binding_report([{
            "id": "map",
            "levelId": "map",
            "markers": [],
            "actionEntityFieldDiagnostics": {"fields": rows},
        }], "CN")

        gates = [
            row["dynamicResolutionFailureGate"]
            for row in report["unplacedDynamicReferences"]
        ]
        self.assertEqual(gates, [
            "runtime_named_action_argument",
            "unnamed_script_property",
            "opaque_dynamic_form",
            "validated_runtime_dependent",
            "exact_output_alias_not_spatially_placed",
        ])
        self.assertEqual(
            sum(report["dynamicReferenceSummary"]["resolutionFailureGateCounts"].values()),
            5,
        )

    def test_null_getter_and_dynamic_filter_alias_are_validated_nonspatial(self):
        rows = [
            {
                "state": "dynamic",
                "dynamicKind": "getter_id_ref",
                "getterResolution": {
                    "status": "exact_constant_param_alias",
                    "resolvedValue": {
                        "logicId": 0,
                        "slotId": 0,
                        "useSlotId": False,
                    },
                },
                "nativeGetterContractStatus": "validated",
            },
            {
                "state": "dynamic",
                "dynamicKind": "local_output_ref",
                "localOutputAliasResolution": {
                    "status": "validated_dynamic_filter_alias",
                    "failureGate": "native_alias_filter_value_is_dynamic",
                    "nativeMappingId": "native-output-alias",
                },
                "nativeOutputAliasContractStatus": "validated",
            },
        ]
        report = builder._action_binding_report([{
            "id": "map",
            "levelId": "map",
            "markers": [],
            "actionEntityFieldDiagnostics": {"fields": rows},
        }], "CN")

        summary = report["dynamicReferenceSummary"]
        self.assertEqual(summary["exactSpatiallyResolvedDynamicReferenceCount"], 0)
        self.assertEqual(summary["validatedRuntimeNonSpatialReferenceCount"], 2)
        self.assertEqual(summary["unresolvedDynamicReferenceCount"], 0)
        self.assertEqual(
            [row["dynamicResolutionFailureGate"]
             for row in report["unplacedDynamicReferences"]],
            [
                "validated_null_entityptr_value",
                "native_alias_filter_value_is_dynamic",
            ],
        )

    def test_exact_npc_proxy_spatial_fallback_requires_identity_and_equal_transform(self):
        target, diagnostic = level_bindings._resolve_exact_npc_proxy_spatial_target(
            2100290001,
            {"2100290001": {
                "segmentIdGlobal": 2100290001,
                "proxyId": "modun_map01_sm1l1m10",
                "position": {"x": 1.0, "y": 2.0, "z": 3.0},
            }},
            {"dataTable": {"modun_map01_sm1l1m10": {
                "entityType": 256,
                "position": {"x": 1.0, "y": 2.0, "z": 3.0},
                "rotation": {"x": 0.0, "y": 90.0, "z": 0.0},
            }}},
            registry_source_file="WorldEntityRegistry.json",
            npc_proxy_table_source_file="NpcProxyTable.json",
        )

        self.assertEqual(diagnostic["status"], "validated")
        self.assertEqual(target["npcProxyId"], "modun_map01_sm1l1m10")
        self.assertEqual(target["position"], {"x": 1.0, "y": 2.0, "z": 3.0})
        self.assertEqual(target["rotation"], {"x": 0.0, "y": 90.0, "z": 0.0})
        self.assertEqual(
            target["spatialResolutionEvidence"],
            "exact_npc_proxy_brief_and_table_join",
        )

    def test_npc_proxy_spatial_fallback_rejects_every_identity_and_transform_gap(self):
        valid_brief = {"101": {
            "segmentIdGlobal": 101,
            "proxyId": "npc_exact",
            "position": {"x": 1.0, "y": 2.0, "z": 3.0},
        }}
        valid_table = {"dataTable": {"npc_exact": {
            "entityType": 256,
            "position": {"x": 1.0, "y": 2.0, "z": 3.0},
            "rotation": {"x": 0.0, "y": 90.0, "z": 0.0},
        }}}

        fixtures = [
            ({}, valid_table, "exact_npc_proxy_brief_key"),
            ({"101": {**valid_brief["101"], "segmentIdGlobal": 102}}, valid_table,
             "npc_proxy_segment_identity"),
            (valid_brief, {"dataTable": {}}, "unique_proxy_id_join"),
            (valid_brief, {"dataTable": {"npc_exact": {
                **valid_table["dataTable"]["npc_exact"],
                "position": {"x": 9.0, "y": 2.0, "z": 3.0},
            }}}, "equal_authored_position"),
            (valid_brief, {"dataTable": {"npc_exact": {
                **valid_table["dataTable"]["npc_exact"],
                "rotation": {"x": 0.0, "y": float("nan"), "z": 0.0},
            }}}, "finite_table_rotation"),
        ]
        for briefs, table, expected_gate in fixtures:
            with self.subTest(gate=expected_gate):
                target, diagnostic = (
                    level_bindings._resolve_exact_npc_proxy_spatial_target(
                        101,
                        briefs,
                        table,
                        registry_source_file="WorldEntityRegistry.json",
                        npc_proxy_table_source_file="NpcProxyTable.json",
                    )
                )
                self.assertIsNone(target)
                self.assertEqual(diagnostic["gate"], expected_gate)

    def test_npc_proxy_action_target_is_published_as_world_identity(self):
        rows = builder._registry_markers(
            {"world": [], "script": [], "npc": [("101", {
                "proxyId": "npc_exact",
                "position": {"x": 1.0, "y": 2.0, "z": 3.0},
            })]},
            "map_fixture",
            "CN",
            {},
            {},
            {},
            {},
            {"world:101": [{
                "status": "exact_world_entity_action_target",
                "actionName": "LevelCameraLookAt",
                "fieldName": "lookAt1",
                "sourceFile": "LevelScriptData/map_fixture/1.json",
                "spatialResolutionEvidence": (
                    "exact_npc_proxy_brief_and_table_join"
                ),
            }]},
            {},
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["identity"], "world:101")
        self.assertEqual(rows[0]["actionBindingStatus"], "exact_bound")
        self.assertEqual(rows[0]["placementEvidenceStatus"],
                         "exact_npc_proxy_brief_and_table_join")

    def test_registry_marker_attaches_exact_entity_event_story_without_ownership(self):
        binding = {
            "storyKey": "radio_exact",
            "eventName": "EntityEvent_OnInteractiveStateChanged",
            "sourceFile": "LevelScriptData/map_fixture/1001.json",
            "status": "exact_entity_event_target",
            "ownership": False,
            "activation": False,
            "orderEvidence": False,
        }
        rows = builder._registry_markers(
            {"world": [], "npc": [], "script": [(
                {"scriptIdGlobal": 1001, "slotId": 40001},
                {
                    "detailId": "int_exact",
                    "entityType": 32,
                    "position": {"x": 1.0, "y": 2.0, "z": 3.0},
                },
            )]},
            "map_fixture", "CN", {}, {}, {}, {}, {}, {},
            {"script:1001:40001": [binding]},
        )
        self.assertEqual(rows[0]["sceneKeys"], ["radio_exact"])
        self.assertEqual(rows[0]["entityEventStoryBindings"], [binding])
        self.assertFalse(rows[0]["entityEventStoryBindings"][0]["ownership"])

    def test_npc_proxy_getter_identity_does_not_collide_with_world_fallback(self):
        getter_target = {
            "status": "exact_npc_proxy_action_target",
            "actionName": "FinishBuffUsingId",
            "fieldName": "target",
            "sourceFile": "LevelScriptData/map_fixture/1.json",
            "targetDomain": "npc_proxy_logic_id",
            "npcProxyId": "npc_exact",
            "entityLogicId": 101,
            "entityPtrGetterResolution": {
                "status": "exact_constant_proxy_id_lookup",
                "getterName": "NpcProxyGetter",
            },
            "nativeGetterContractStatus": "validated",
        }
        world_target = {
            "status": "exact_world_entity_action_target",
            "actionName": "LevelCameraLookAt",
            "fieldName": "lookAt1",
            "sourceFile": "LevelScriptData/map_fixture/2.json",
            "targetDomain": "world_logic_id",
            "entityLogicId": 101,
            "spatialResolutionEvidence": "exact_npc_proxy_brief_and_table_join",
        }
        rows = builder._registry_markers(
            {"world": [], "script": [], "npc": [("101", {
                "proxyId": "npc_exact",
                "position": {"x": 1.0, "y": 2.0, "z": 3.0},
            })]},
            "map_fixture", "CN", {}, {}, {}, {},
            {"npc:101": [getter_target], "world:101": [world_target]},
            {},
        )

        self.assertEqual(rows[0]["identity"], "npc:101")
        self.assertEqual(len(rows[0]["actions"]), 1)
        self.assertEqual(rows[0]["actions"][0]["name"], "FinishBuffUsingId")
        self.assertEqual(rows[0]["actions"][0]["targetDomain"],
                         "npc_proxy_logic_id")
        self.assertEqual(rows[0]["worldFallbackActionTargets"], [world_target])

        report = builder._action_binding_report([{
            "id": "map_fixture",
            "levelId": "map_fixture",
            "markers": rows,
        }], "CN")
        slots = report["maps"][0]["slots"]
        self.assertEqual(
            [(row["identity"], row["domain"]) for row in slots],
            [("npc:101", "npc_proxy_logic_id"),
             ("world:101", "world_logic_id")],
        )
        self.assertEqual(slots[0]["actions"][0]["targetDomain"],
                         "npc_proxy_logic_id")
        self.assertEqual(
            slots[0]["actions"][0]["entityPtrGetterResolution"]["getterName"],
            "NpcProxyGetter",
        )
        self.assertEqual(
            slots[0]["actions"][0]["nativeGetterContractStatus"],
            "validated",
        )
        self.assertEqual(slots[1]["actions"][0]["targetDomain"],
                         "world_logic_id")

    def test_empty_interactive_shell_is_not_claimed_as_generic_interactive(self):
        self.assertEqual(
            builder._classify_entity("int_empty", 32),
            ("empty_slot", "unresolved_empty_slot", "未解析空槽", "empty_interactive_shell"),
        )

    def test_enemy_name_and_document_title_use_exact_localized_sources(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(builder, "ROOT", Path(tmp)):
            root = Path(tmp)
            display = root / builder.ENEMY_TEMPLATE_DISPLAY_REL
            display.parent.mkdir(parents=True)
            display.write_text(json.dumps({"eny_test": {"name": {"id": 42}}}), encoding="utf-8")
            i18n = root / builder.I18N_TEXT_REL.format("CN")
            i18n.parent.mkdir(parents=True, exist_ok=True)
            i18n.write_text(json.dumps({"42": "测试敌人"}), encoding="utf-8")
            conv = root / "webui/data/lang/CN/conv/text_test.json"
            conv.parent.mkdir(parents=True)
            conv.write_text(json.dumps({"title": "测试文档"}), encoding="utf-8")
            builder._ENTITY_NAMES.clear()
            builder._STORY_TITLES.clear()
            with mock.patch.object(builder, "_conv_file_for_key", return_value="webui/data/lang/CN/conv/text_test.json"):
                self.assertEqual(builder._entity_display_name("eny_test", "CN"), "测试敌人")
                self.assertEqual(builder._story_display_title("CN", "text_test"), "测试文档")

    def test_grenade_tower_enemy_and_tomb_have_exact_semantic_evidence(self):
        self.assertEqual(
            builder._classify_entity("int_fac_battle_cannon_1_dg002", 32),
            ("device", "grenade_tower", "榴弹塔", "authored_combat_device"),
        )
        self.assertEqual(
            [row["path"] for row in builder._interactive_semantic_files("int_fac_battle_cannon_1_dg002")],
            [builder.FACTORY_BUILDING_REL, builder.FACTORY_BATTLE_REL, builder.MODEL_TABLE_REL],
        )
        self.assertEqual(
            [row["path"] for row in builder._interactive_semantic_files("eny_0080_reaper")],
            [builder.ENEMY_TEMPLATE_REL, builder.ENEMY_TEMPLATE_DISPLAY_REL, builder.MODEL_TABLE_REL],
        )
        self.assertEqual(
            [row["path"] for row in builder._interactive_semantic_files("int_narrative_common_BTomb01")],
            [builder.MODEL_TABLE_REL],
        )

    def test_exact_story_trigger_markers_publish_decoded_box_and_story_link(self):
        report = {"rows": [{"levelId": "indie_dg002", "scriptId": "8700010001", "storyTriggerZoneConfirmations": [{
            "storyKey": "radio_e0m0_9", "status": "exact_local_trigger_volume", "observations": [{
                "status": "exact_local_trigger_volume", "levelId": "indie_dg002",
                "scriptId": "8700010001", "triggerSlotIdFilter": 80002,
                "sourceFile": "export_full/structured/Persistent/Data/Json/LevelScriptData/indie_dg002/8700010001.json",
                "triggerVolume": {"slotId": 80002, "triggerVolumeType": "Leader"},
                "triggerVolumeContext": {
                    "status": "exact_local_levelscript_trigger_volume_without_foreign_identity",
                    "scriptIdVerified": True, "matchedSlotIds": [80002],
                    "missingSlotIds": [], "ambiguousSlotIds": [],
                },
                "decodedShape": [{"offset": "0x114c", "shapeType": "Box",
                    "position": {"x": 275.328, "y": 47.044, "z": 491.653},
                    "rotation": {"x": 0, "y": 327.299, "z": 0},
                    "size": {"x": 8, "y": 25, "z": 35}, "radius": 3}],
            }],
        }]}]}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(builder, "ROOT", Path(tmp)):
            path = Path(tmp) / builder.NATIVE_TRIGGER_FRONTIER_REL
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(report), encoding="utf-8")
            with mock.patch.object(builder, "_conv_file_for_key", return_value="webui/data/lang/CN/conv/radio_e0m0_9.json"):
                rows = builder._exact_story_trigger_markers("indie_dg002", "CN")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["triggerShape"]["type"], "box")
        self.assertEqual(rows[0]["triggerShape"]["size"]["z"], 35)
        self.assertEqual(rows[0]["sceneKeys"], ["radio_e0m0_9"])
        self.assertEqual(rows[0]["missionContexts"], ["e0m0"])
        self.assertEqual(rows[0]["triggerIdentityDomain"], "LevelScriptData.triggerVolumes local slot")
        self.assertEqual(rows[0]["registryIdentityStatus"], "not_applicable")
        self.assertNotIn("missions", rows[0])

    def test_exact_story_trigger_markers_fail_closed_for_non_spatial_events(self):
        report = {"rows": [{"levelId": "indie_dg002", "scriptId": "1", "storyTriggerZoneConfirmations": [{
            "storyKey": "radio_e0m0_2", "status": "exact_non_spatial_event_trigger",
            "observations": [{"status": "exact_non_spatial_event_trigger"}],
        }]}]}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(builder, "ROOT", Path(tmp)):
            path = Path(tmp) / builder.NATIVE_TRIGGER_FRONTIER_REL
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(report), encoding="utf-8")
            self.assertEqual(builder._exact_story_trigger_markers("indie_dg002", "CN"), [])

    def test_exact_story_trigger_markers_publish_each_explicit_list_slot(self):
        slots = [80001, 80002]
        observations = []
        for index, slot_id in enumerate(slots):
            observations.append({
                "status": "exact_local_trigger_volume", "levelId": "map",
                "scriptId": "100", "triggerSlotIdFilter": slot_id,
                "triggerSlotIdFilters": slots,
                "multiLocationSemantics": "explicit_independent_trigger_slots",
                "sourceFile": "LevelScriptData/map/100.json",
                "playbackControlPathEvidence": {
                    "status": "exact_trigger_rooted_playback",
                },
                "triggerVolume": {
                    "slotId": slot_id, "triggerVolumeType": "Leader",
                },
                "triggerVolumeContext": {
                    "status": "exact_local_levelscript_trigger_volume_without_foreign_identity",
                    "scriptIdVerified": True, "matchedSlotIds": slots,
                    "missingSlotIds": [], "ambiguousSlotIds": [],
                },
                "decodedShape": [{
                    "offset": f"0x{100 + index:x}", "shapeType": "Box",
                    "position": {"x": index + 1, "y": 2, "z": 3},
                    "rotation": {}, "size": {"x": 1, "y": 1, "z": 1},
                }],
            })
        report = {"storyTriggerZoneCoverage": {"rows": [{
            "storyKey": "radio_multi", "status": "multiple_or_ambiguous_trigger_zones",
            "observations": observations,
        }]}}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(builder, "ROOT", Path(tmp)):
            path = Path(tmp) / builder.NATIVE_TRIGGER_FRONTIER_REL
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(report), encoding="utf-8")
            rows = builder._exact_story_trigger_markers("map", "CN")
        self.assertEqual(["80001", "80002"], [row["triggerSlotId"] for row in rows])
        self.assertTrue(all(row["sceneKeys"] == ["radio_multi"] for row in rows))

    def test_exact_story_trigger_markers_merge_stories_sharing_one_shape(self):
        observation = {
            "status": "exact_local_trigger_volume", "levelId": "map", "scriptId": "100",
            "triggerSlotIdFilter": 80001, "sourceFile": "LevelScriptData/map/100.json",
            "triggerVolume": {"slotId": 80001, "triggerVolumeType": "Leader"},
            "triggerVolumeContext": {
                "status": "exact_local_levelscript_trigger_volume_without_foreign_identity",
                "scriptIdVerified": True, "matchedSlotIds": [80001],
                "missingSlotIds": [], "ambiguousSlotIds": [],
            },
            "decodedShape": [{"offset": "0x100", "shapeType": "Sphere",
                "position": {"x": 1, "y": 2, "z": 3},
                "rotation": {"x": 0, "y": 0, "z": 0},
                "size": {"x": 0, "y": 0, "z": 0}, "radius": 5}],
        }
        report = {"rows": [{"levelId": "map", "scriptId": "100", "storyTriggerZoneConfirmations": [
            {"storyKey": "radio_e1m1_1", "status": "exact_local_trigger_volume",
             "observations": [observation]},
            {"storyKey": "cutscene_e1m1_2", "status": "exact_local_trigger_volume",
             "observations": [observation]},
        ]}]}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(builder, "ROOT", Path(tmp)):
            path = Path(tmp) / builder.NATIVE_TRIGGER_FRONTIER_REL
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(report), encoding="utf-8")
            with mock.patch.object(builder, "_conv_file_for_key", side_effect=lambda _lang, key: f"conv/{key}.json"):
                rows = builder._exact_story_trigger_markers("map", "CN")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["sceneKeys"], ["radio_e1m1_1", "cutscene_e1m1_2"])
        self.assertEqual(rows[0]["missionContexts"], ["e1m1"])
        self.assertEqual(
            sorted(pin["path"] for pin in rows[0]["relatedFiles"] if pin["relation"] == "story_exact_trigger"),
            ["conv/cutscene_e1m1_2.json", "conv/radio_e1m1_1.json"],
        )

    def test_exact_story_trigger_markers_preserve_world_polyline_points(self):
        points = [{"x": -440.0, "y": -180.0}, {"x": -430.0, "y": -180.0},
                  {"x": -435.0, "y": -170.0}]
        report = {"storyTriggerZoneCoverage": {"rows": [{
            "storyKey": "radio_poly", "status": "exact_local_trigger_volume", "observations": [{
                "status": "exact_local_trigger_volume", "levelId": "map", "scriptId": "100",
                "sourceFile": "LevelScriptData/map/100.json", "triggerSlotIdFilter": 80002,
                "triggerVolumeContext": {
                    "status": "exact_local_levelscript_trigger_volume_without_foreign_identity",
                    "scriptIdVerified": True, "matchedSlotIds": [80002],
                    "missingSlotIds": [], "ambiguousSlotIds": [],
                },
                "triggerVolume": {"slotId": 80002, "triggerVolumeType": "Leader"},
                "decodedShape": [{"shapeType": "PolyLine", "offset": "0x200",
                    "position": {"x": -435, "y": 246, "z": -175},
                    "polyLinePoints": {"status": "present", "parseStatus": "decoded",
                                       "points": points}}],
            }],
        }]}}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(builder, "ROOT", Path(tmp)):
            path = Path(tmp) / builder.NATIVE_TRIGGER_FRONTIER_REL
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(report), encoding="utf-8")
            rows = builder._exact_story_trigger_markers("map", "CN")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["triggerShape"]["type"], "polyline")
        self.assertEqual(rows[0]["triggerShape"]["polyLinePoints"], points)

    def test_multiple_exact_trigger_zones_project_only_current_script_observation(self):
        def observation(level, script, slot, x):
            return {
                "status": "exact_local_trigger_volume", "levelId": level,
                "scriptId": script, "triggerSlotIdFilter": slot,
                "sourceFile": f"root/{level}/{script}.json",
                "decodedShape": [{"shapeType": "Box", "position": {"x": x, "y": 2, "z": 3}}],
                "triggerVolume": {"slotId": slot, "triggerVolumeType": "Leader"},
                "triggerVolumeContext": {
                    "status": "exact_local_levelscript_trigger_volume_without_foreign_identity",
                    "scriptIdVerified": True, "matchedSlotIds": [slot],
                    "missingSlotIds": [], "ambiguousSlotIds": [],
                },
                "playbackControlPathEvidence": {"status": "exact_trigger_rooted_playback"},
            }
        report = {"rows": [{"levelId": "map", "scriptId": "outer", "storyTriggerZoneConfirmations": [{
            "storyKey": "radio_e1m1_1", "status": "multiple_or_ambiguous_trigger_zones",
            "observations": [observation("map", "100", 80001, 1), observation("other", "200", 80002, 9)],
        }]}]}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(builder, "ROOT", Path(tmp)):
            path = Path(tmp) / builder.NATIVE_TRIGGER_FRONTIER_REL
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(report), encoding="utf-8")
            rows = builder._exact_story_trigger_markers("map", "CN")

        self.assertEqual(1, len(rows))
        self.assertEqual("100", rows[0]["scriptId"])
        self.assertEqual("80001", rows[0]["triggerSlotId"])
        self.assertEqual("multiple_or_ambiguous_trigger_zones", rows[0]["storyTriggerMultiplicityStatus"])

    def test_unplaced_story_trigger_evidence_distinguishes_nonspatial_and_missing_projection(self):
        report = {"rows": [{"levelId": "indie_dg002", "scriptId": "1", "storyTriggerZoneConfirmations": [
            {"storyKey": "nonspatial", "status": "exact_non_spatial_event_trigger",
             "observations": [{"levelId": "indie_dg002"}]},
            {"storyKey": "spatial", "status": "exact_local_trigger_volume",
             "observations": [{"levelId": "indie_dg002"}]},
        ]}]}
        rows = [{"key": "nonspatial"}, {"key": "spatial"}, {"key": "unknown"}]
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(builder, "ROOT", Path(tmp)):
            path = Path(tmp) / builder.NATIVE_TRIGGER_FRONTIER_REL
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(report), encoding="utf-8")
            builder._annotate_unplaced_story_trigger_evidence(rows, "indie_dg002")

        self.assertEqual(
            rows[0]["storyTriggerEvidence"]["resolutionClass"],
            "exact_non_spatial_trigger_context_only",
        )
        self.assertEqual(
            rows[1]["storyTriggerEvidence"]["failureGate"],
            "exact_trigger_marker_missing_from_current_map_payload",
        )
        self.assertNotIn("storyTriggerEvidence", rows[2])

    def test_unplaced_story_trigger_evidence_uses_complete_direct_coverage_and_level_scope(self):
        report = {"storyTriggerZoneCoverage": {"rows": [{
            "storyKey": "radio_direct", "status": "exact_non_spatial_event_trigger",
            "observations": [
                {"levelId": "map", "scriptId": "100", "status": "exact_non_spatial_event_trigger"},
                {"levelId": "other", "scriptId": "200", "status": "exact_non_spatial_event_trigger"},
            ],
        }]}, "rows": []}
        rows = [{"key": "radio_direct"}]
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(builder, "ROOT", Path(tmp)):
            path = Path(tmp) / builder.NATIVE_TRIGGER_FRONTIER_REL
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(report), encoding="utf-8")
            builder._annotate_unplaced_story_trigger_evidence(rows, "map")

        evidence = rows[0]["storyTriggerEvidence"]
        self.assertEqual("exact_non_spatial_trigger_context_only", evidence["resolutionClass"])
        self.assertEqual(["100"], evidence["confirmations"][0]["scriptIds"])
        self.assertEqual(1, evidence["confirmations"][0]["observationCount"])

    def test_unplaced_story_absence_requires_complete_validated_active_coverage(self):
        validated = {
            "storyTriggerZoneCoverage": {
                "schema": "nativeReceiverStoryTriggerZone.v1",
                "overlay": {"status": "validated_active_overlay", "validationFailures": []},
                "rows": [{
                    "storyKey": "different_story", "status": "exact_non_spatial_event_trigger",
                    "observations": [{"levelId": "map", "scriptId": "100"}],
                }],
            }
        }
        rows = [{"key": "missing_story", "reason": "graph_evidence_only"}]
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(builder, "ROOT", Path(tmp)):
            path = Path(tmp) / builder.NATIVE_TRIGGER_FRONTIER_REL
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(validated), encoding="utf-8")
            builder._annotate_unplaced_story_trigger_evidence(rows, "map")
        absence = rows[0]["storyCarrierAbsenceEvidence"]
        self.assertEqual("not_observed_in_active_direct_playback_frontier", absence["status"])
        self.assertFalse(absence["spatialPromotion"])
        self.assertEqual("graph_evidence_only", rows[0]["reason"])
        self.assertEqual(
            {"not_observed_in_active_direct_playback_frontier": 1},
            builder._unplaced_report(rows)["carrierAbsenceCounts"],
        )

        degraded_rows = [{"key": "missing_story"}]
        validated["storyTriggerZoneCoverage"]["overlay"]["status"] = "unavailable_fail_closed"
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(builder, "ROOT", Path(tmp)):
            path = Path(tmp) / builder.NATIVE_TRIGGER_FRONTIER_REL
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(validated), encoding="utf-8")
            builder._annotate_unplaced_story_trigger_evidence(degraded_rows, "map")
        self.assertNotIn("storyCarrierAbsenceEvidence", degraded_rows[0])

    def test_unplaced_cutscene_definition_adds_related_files_without_spatial_promotion(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(builder, "ROOT", Path(tmp)):
            conv = Path(tmp) / "webui/data/lang/CN/conv/cutscene_fixture.json"
            conv.parent.mkdir(parents=True)
            conv.write_text(json.dumps({
                "key": "cutscene_fixture",
                "cutscene": {
                    "semanticShape": "unityTimeline", "hasSubtitleTrack": True,
                    "audioEvents": ["au_fixture"],
                    "variants": [
                        {"name": "cutscene_fixture", "file": "export/root.json"},
                        {"name": "cutscene_fixture_Audio", "file": "export/audio.json"},
                    ],
                },
            }), encoding="utf-8")
            rows = [{
                "key": "cutscene_fixture", "reason": "no_placement_evidence",
                "path": "webui/data/lang/CN/conv/cutscene_fixture.json",
            }]
            builder._annotate_unplaced_story_definition_evidence(rows)

        evidence = rows[0]["storyDefinitionEvidence"]
        self.assertEqual("exact_published_cutscene_definition", evidence["status"])
        self.assertEqual(2, evidence["variantCount"])
        self.assertFalse(evidence["spatialPromotion"])
        self.assertEqual(
            ["export/audio.json", "export/root.json"],
            [item["path"] for item in rows[0]["relatedFiles"]],
        )
        self.assertEqual(
            {"exact_published_cutscene_definition": 1},
            builder._unplaced_report(rows)["definitionEvidenceCounts"],
        )

    def test_unplaced_story_absence_does_not_reclassify_cross_level_carrier(self):
        report = {
            "storyTriggerZoneCoverage": {
                "schema": "nativeReceiverStoryTriggerZone.v1",
                "overlay": {"status": "validated_active_overlay", "validationFailures": []},
                "rows": [{
                    "storyKey": "cross_level_story",
                    "status": "exact_local_trigger_volume",
                    "observations": [{
                        "levelId": "other_map",
                        "scriptId": "200",
                        "status": "exact_local_trigger_volume",
                    }],
                }],
            },
        }
        rows = [{"key": "cross_level_story", "reason": "cross_level_binding"}]
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(builder, "ROOT", Path(tmp)):
            path = Path(tmp) / builder.NATIVE_TRIGGER_FRONTIER_REL
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(report), encoding="utf-8")
            builder._annotate_unplaced_story_trigger_evidence(rows, "current_map")

        self.assertNotIn("storyCarrierAbsenceEvidence", rows[0])

    def test_authored_teleport_interactives_get_specific_travel_facets(self):
        self.assertEqual(
            builder._classify_entity("int_campfire_v2", 32),
            ("travel", "campfire_teleport", "营火传送点", "teleport_related_map_mark"),
        )
        self.assertEqual(
            builder._classify_entity("int_system_spaceship_visit_portal", 32),
            ("travel", "spaceship_visit_portal", "访问传送门", "authored_visit_portal"),
        )
        self.assertEqual(
            builder._classify_entity("int_teleport_test", 32)[:2],
            ("travel", "teleport_point"),
        )
        self.assertEqual(
            builder._classify_entity("int_campfire_base_quest_smaller", 32)[:2],
            ("device", "interactive"),
        )

    def test_interactive_semantic_evidence_fails_closed_for_unknown_details(self):
        campfire = builder._interactive_semantic_files("int_campfire_v2_smaller")
        portal = builder._interactive_semantic_files("int_system_spaceship_visit_portal")
        self.assertEqual([row["path"] for row in campfire], [builder.MAP_MARK_TEMP_REL, builder.TEXT_TABLE_REL])
        self.assertEqual([row["path"] for row in portal], [builder.MODEL_TABLE_REL, builder.SPACESHIP_CONST_REL])
        self.assertEqual(builder._interactive_semantic_files("int_campfire_base_quest_smaller"), [])
        self.assertEqual(builder._interactive_semantic_files("int_system_unknown_portal"), [])

    def test_index_collapses_authored_map_variants_without_losing_task_data(self):
        rows = [
            {
                "id": "base01_lv001", "levelId": "base01_lv001", "src": "maps/base01_lv001.json",
                "missions": ["main"], "missionNames": {"main": "Main"},
                "markerCount": 10, "questPointCount": 2, "storyKeyCount": 3, "missionCount": 1,
            },
            {
                "id": "base01_lv003", "levelId": "base01_lv003", "src": "maps/base01_lv003.json",
                "missions": ["variant"], "missionNames": {"variant": "Variant"},
                "markerCount": 4, "questPointCount": 1, "storyKeyCount": 2, "missionCount": 1,
            },
        ]

        grouped = builder._collapse_index_variants(rows)

        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0]["id"], "base01_lv001")
        self.assertEqual(grouped[0]["missions"], ["main", "variant"])
        self.assertEqual(grouped[0]["markerCount"], 14)
        self.assertEqual([row["id"] for row in grouped[0]["variants"]], ["base01_lv001", "base01_lv003"])
        self.assertEqual(grouped[0]["variants"][1]["src"], "maps/base01_lv003.json")

    def test_grouped_index_expands_for_focused_variant_replacement(self):
        grouped = builder._collapse_index_variants([
            {"id": "dung01_wrdg001", "missions": [], "missionNames": {}, "markerCount": 1},
            {"id": "dung01_wrdg001_guide", "missions": ["db01m3"], "missionNames": {"db01m3": "Guide"}, "markerCount": 2},
        ])

        expanded = builder._expand_index_variants(grouped)

        self.assertEqual([row["id"] for row in expanded], ["dung01_wrdg001", "dung01_wrdg001_guide"])
        self.assertNotIn("variants", expanded[0])

    def test_blackbox_region_key_uses_authored_shared_scene(self):
        with mock.patch.object(builder, "authored_streaming_scene", return_value={"sceneId": "blackbox02_dg001"}):
            self.assertEqual(builder._region_key("blackbox_miner_3"), "blackbox02_dg001")
        # Large-world level families retain their established union region.
        with mock.patch.object(builder, "authored_streaming_scene") as resolver:
            self.assertEqual(builder._region_key("map02_lv003"), "map02")
            resolver.assert_not_called()

    def test_shared_large_region_suppresses_sparse_level_point_cloud(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(builder, "ROOT", Path(tmp)), mock.patch.object(
                builder, "authored_streaming_scene",
                return_value={"sceneId": "map01", "method": "level_config_embedded_streaming_path"},
        ), mock.patch.object(builder, "isolated_art_source", return_value=None):
            background = builder._render_background("dung01_cdg011")
        self.assertEqual(background["status"], "shared_authored_region_background")
        self.assertIsNone(background["src"])

    def test_inferred_hlod_is_suppressed_even_when_a_region_has_a_minimap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            render = root / "webui/data/map_recovery/render"
            render.mkdir(parents=True)
            expected = {"status": "inferred_hlod_grid_preview", "src": "render/map01_lv001_hlod_surface.png"}
            (render / "map01_lv001_hlod_grid_inferred.json").write_text(json.dumps(expected), encoding="utf-8")
            with mock.patch.object(builder, "ROOT", root):
                background = builder._render_background("map01_lv001")
        self.assertEqual(background["status"], "inferred_hlod_alignment_suppressed")
        self.assertIsNone(background["src"])
        self.assertIsNone(background["worldBounds"])
        self.assertEqual(background["diagnosticManifest"], "render/map01_lv001_hlod_grid_inferred.json")

    def test_inferred_hlod_without_minimap_restores_exact_point_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            render = root / "webui/data/map_recovery/render"
            render.mkdir(parents=True)
            expected = {
                "status": "inferred_hlod_grid_preview",
                "src": "render/test_hlod_surface.png",
                "exactPointFallback": {
                    "status": "exact_registry_transform_point_cloud",
                    "src": "render/test_registry_point_cloud.png",
                    "worldBounds": {"minX": 0, "maxX": 1, "minZ": 0, "maxZ": 1},
                    "pointCloudOverlay": {"src": "render/test_registry_point_cloud.png"},
                },
            }
            (render / "test_hlod_grid_inferred.json").write_text(json.dumps(expected), encoding="utf-8")
            with mock.patch.object(builder, "ROOT", root):
                background = builder._render_background("test")

        self.assertEqual(background["status"], "exact_registry_transform_point_cloud")
        self.assertEqual(background["src"], "render/test_registry_point_cloud.png")
        self.assertTrue(background["suppressedInferredSurface"])

    def test_danger_surface_accuracy_labels_are_evidence_specific(self):
        for level_id in (
            "dung01_bdg001", "dung01_bdg002", "dung01_bdg003", "dung02_bdg001",
        ):
            with self.subTest(level_id=level_id):
                evidence = builder._danger_surface_evidence(
                    level_id, {"status": "inferred_hlod_textured_preview"},
                )
                self.assertEqual(evidence["accuracy"], "inferred_hlod_crop")

        mesh = builder._danger_surface_evidence(
            "dung02_bdg002", {"status": "recovered_streaming_mesh_topdown"},
        )
        textured = builder._danger_surface_evidence(
            "dung02_bdg005", {"status": "recovered_streaming_textured_topdown"},
        )
        self.assertEqual(mesh["accuracy"], "exact_mesh_color_unverified")
        self.assertEqual(textured["accuracy"], "exact_mesh_partial_base_color")

    def test_danger_surface_accuracy_fails_closed_on_mismatched_preview(self):
        self.assertIsNone(builder._danger_surface_evidence(
            "dung02_bdg005", {"status": "recovered_streaming_mesh_topdown"},
        ))

    def test_render_background_publishes_danger_surface_accuracy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            render = root / "webui/data/map_recovery/render"
            render.mkdir(parents=True)
            preview = {"status": "recovered_streaming_mesh_topdown", "src": "render/bdg002.png"}
            (render / "dung02_bdg002_hlod_grid_inferred.json").write_text(
                json.dumps(preview), encoding="utf-8",
            )
            with mock.patch.object(builder, "ROOT", root):
                background = builder._render_background("dung02_bdg002")

        self.assertEqual(background["surfaceEvidence"]["accuracy"], "exact_mesh_color_unverified")

    def test_danger_map_reusing_large_region_art_remains_its_own_region(self):
        with mock.patch.object(
            builder, "isolated_art_source",
            return_value={"levelId": "map01_lv002", "method": "level_config_embedded_art_level"},
        ):
            self.assertEqual(builder._region_key("dung01_bdg001"), "dung01_bdg001")

        with mock.patch.object(builder, "isolated_art_source", return_value=None), mock.patch.object(
            builder, "authored_streaming_scene", return_value={"sceneId": "indie_dg006"},
        ):
            self.assertEqual(builder._region_key("dung02_bdg002"), "dung02_bdg002")

    def test_render_background_exposes_exact_level_obj_assets_without_placing_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mesh_root = root / "export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/Mesh"
            mesh_root.mkdir(parents=True)
            exact = mesh_root / "S_mod_test_lv001_hull_lod0_pABC.obj"
            family = mesh_root / "S_mod_test_lv002_hull_lod0_pDEF.obj"
            exact.write_text("v 0 0 0\nf 1 1 1\n", encoding="utf-8")
            family.write_text("v 0 0 0\n", encoding="utf-8")
            with mock.patch.object(builder, "ROOT", root):
                builder._MODEL_ASSET_INDEX.clear()
                background = builder._render_background("test_lv001")

        self.assertIsNone(background["src"])
        scene = background["modelScene"]
        self.assertEqual(scene["status"], "obj_level_assets_unplaced")
        self.assertEqual(scene["positionStatus"], "unplaced")
        self.assertEqual(scene["meshCount"], 1)
        self.assertEqual(scene["meshes"][0]["assetRel"], "StreamingAssets/Mesh/S_mod_test_lv001_hull_lod0_pABC.obj")
        self.assertNotIn("translation", scene["meshes"][0])

    def test_unplaced_obj_fallback_does_not_match_a_shared_level_family(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mesh_root = root / "export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/Mesh"
            mesh_root.mkdir(parents=True)
            (mesh_root / "S_mod_base01_shared_lod0_pABC.obj").write_text("v 0 0 0\n", encoding="utf-8")
            with mock.patch.object(builder, "ROOT", root):
                builder._MODEL_ASSET_INDEX.clear()
                background = builder._render_background("base01_dg001")

        self.assertEqual(background["modelScene"]["status"], "obj_level_assets_unavailable")
        self.assertEqual(background["modelScene"]["meshes"], [])

class RelatedFilePinningTests(unittest.TestCase):
    """The published pins carry their own evidence strength and stay fetchable."""

    def test_href_maps_both_published_path_spaces_onto_server_routes(self):
        self.assertEqual(
            builder._href("export_full/structured/a.json"),
            "/export_full/structured/a.json",
        )
        # serve.py mounts webui/ at the site root, so the `webui/` prefix has to
        # be dropped or the published dialog file would 404.
        self.assertEqual(builder._href("webui/data/lang/CN/conv/text_e0m0_1.json"), "/data/lang/CN/conv/text_e0m0_1.json")

    def test_related_rows_declare_strength_and_sort_by_usefulness(self):
        rows = [
            builder._related("a.json", "entity_registry", "registry"),
            builder._related("b.json", "story_proximity", "scene"),
            builder._related("c.json", "story_exact_producer", "text"),
        ]
        self.assertEqual([row["strength"] for row in rows], ["strong", "weak", "strong"])
        ordered = builder._sorted_related(rows)
        # The exact story wins over the level-wide registry file, and every weak
        # pin sorts after every strong one.
        self.assertEqual([row["path"] for row in ordered], ["c.json", "a.json", "b.json"])

    def test_resolved_slot_stops_the_story_reaching_the_scripts_other_slots(self):
        """A named slot is a gate, not a hint.

        `cutscene_e0m0_2ndZiplineA` names slot 40007 on producer 8700040013.
        Indexing it under the bare script id pinned it to slots 40004/40005/
        40006 as well - entities the same row proves are the wrong ones.
        """
        mission = {
            "flow": {
                "missionStoryConnections": [{
                    "key": "zipline_a",
                    "producerEntityPositionStatus": "exact_unique_world_entity_registry_script_slot",
                    "producerEntities": [{"scriptIdGlobal": "8700040013", "slotId": "40007"}],
                    "producerScriptIds": ["8700040013"],
                    "listenerScriptIds": ["8700010008"],
                    "anchorScriptIds": ["8700040001"],
                    "entitySlotIds": ["40007"],
                }],
            },
        }
        with mock.patch.object(builder, "_conv_file_for_key", side_effect=lambda language, key: f"webui/data/lang/{language}/conv/{key}.json"):
            index = builder._story_index(mission, "CN")

        self.assertEqual([row["key"] for row in index["slot:8700040013:40007"]], ["zipline_a"])
        # Nothing may fall back to the whole script, the listener, or the
        # ordering anchor once the exact producer entity is known.
        self.assertNotIn("script:8700040013", index)
        self.assertNotIn("script:8700010008", index)
        self.assertNotIn("anchor:8700040001", index)

    def test_named_slots_without_a_registry_row_stay_slot_scoped(self):
        mission = {
            "flow": {
                "missionStoryConnections": [{
                    "key": "slotted",
                    "producerScriptIds": ["8700040013"],
                    "entitySlotIds": ["40006"],
                }],
            },
        }
        with mock.patch.object(builder, "_conv_file_for_key", side_effect=lambda language, key: f"webui/data/lang/{language}/conv/{key}.json"):
            index = builder._story_index(mission, "CN")

        self.assertEqual([row["key"] for row in index["scriptslot:8700040013:40006"]], ["slotted"])
        self.assertNotIn("script:8700040013", index)

    def test_anchor_scripts_are_kept_apart_from_the_story_player(self):
        """Anchors order a scene; they are not the entity that plays it."""
        mission = {
            "flow": {
                "missionStoryConnections": [{
                    "key": "unplaced",
                    "producerScriptIds": ["8700020019"],
                    "anchorScriptIds": ["8700040001"],
                }],
            },
        }
        with mock.patch.object(builder, "_conv_file_for_key", side_effect=lambda language, key: f"webui/data/lang/{language}/conv/{key}.json"):
            index = builder._story_index(mission, "CN")

        self.assertEqual([row["key"] for row in index["script:8700020019"]], ["unplaced"])
        self.assertEqual([row["key"] for row in index["anchor:8700040001"]], ["unplaced"])
        self.assertNotIn("script:8700040001", index)

    def test_scene_bindings_are_keyed_by_script_without_claiming_a_slot(self):
        """The chains name a level-script file but never an entity slot."""
        mission = {
            "extras": {
                "sceneBindings": {
                    "cutscene_e0m0_6": {"chains": [{
                        "levelId": "indie_dg004",
                        "file": "export_full/structured/StreamingAssets/Data/Json/LevelScriptData/indie_dg004/23900030000.json",
                        "steps": [
                            {"payloads": [{"sceneKey": "cutscene_e0m0_6", "kind": "cutscene"}]},
                            {"payloads": [{"sceneKey": "cutscene_e0m0_7", "kind": "cutscene"}]},
                        ],
                    }]},
                    "elsewhere": {"chains": [{
                        "levelId": "indie_dg002",
                        "file": "export_full/x.json",
                        "steps": [{"payloads": [{"sceneKey": "ignored", "kind": "cutscene"}]}],
                    }]},
                },
            },
        }
        with mock.patch.object(builder, "_conv_file_for_key", side_effect=lambda language, key: f"webui/data/lang/{language}/conv/{key}.json"):
            index = builder._scene_binding_pins_by_level(mission, "e0m0", "CN")

        # Each chain is filed under the level it declares, so one mission's
        # chains can place dialog on several maps without ever crossing over.
        self.assertEqual(sorted(index), ["indie_dg002", "indie_dg004"])
        self.assertEqual(sorted(index["indie_dg004"]), ["condition:23900030000"])
        self.assertEqual(
            [row["key"] for row in index["indie_dg004"]["condition:23900030000"]],
            ["cutscene_e0m0_6", "cutscene_e0m0_7"],
        )
        self.assertEqual([row["key"] for row in index["indie_dg002"]["condition:x"]], ["ignored"])

    def test_trigger_slots_outside_the_registry_id_space_are_reported_not_placed(self):
        mission = {
            "flow": {
                "missionStoryConnections": [
                    {"key": "radio_in_volume", "triggerSlotIds": ["80009"]},
                    {"key": "on_a_real_entity", "triggerSlotIds": ["40007"]},
                ],
            },
        }
        registry = {"m_scriptEntityIdList": [{"scriptIdGlobal": 8700040013, "slotId": 40007}]}
        report = builder._unresolved_trigger_slots(mission, registry)

        self.assertEqual(report["count"], 1)
        self.assertEqual(report["stories"][0]["key"], "radio_in_volume")
        self.assertIn("not the recovered trigger position", report["boundary"])

    def test_proximity_rows_do_not_bind_story_files_to_a_quest_centroid(self):
        timeline = {
            "levelscriptSpatialProximity": [{
                "sceneKey": "radio_e0m0_8d4",
                "questId": "e0m0_q#7",
                "scriptId": "8700040000",
                "file": "export_full/structured/StreamingAssets/Data/Json/LevelScriptData/indie_dg002/8700040000.json",
                "pin": {"sourceType": "trackingPos", "position": {"x": 1, "y": 2, "z": 3}},
            }],
            "scenePlacement": {},
        }
        index = builder._quest_proximity_index(timeline)
        self.assertEqual([row["sceneKey"] for row in index["e0m0_q#7"]], ["radio_e0m0_8d4"])

        with mock.patch.object(builder, "_conv_file_for_key", side_effect=lambda language, key: f"webui/data/lang/{language}/conv/{key}.json"), \
                mock.patch.object(builder, "_script_file_for_id", return_value=None):
            point = builder._quest_point(
                {"questId": "e0m0_q#7", "centroid": {"x": 0, "y": 0, "z": 0}},
                "CN",
                {},
                {},
                index,
            )

        self.assertEqual(point["sceneKeys"], [])
        self.assertEqual(point["storyBindingStatus"], "unresolved")
        paths = {pin["path"] for pin in point["relatedFiles"]}
        self.assertNotIn("webui/data/lang/CN/conv/radio_e0m0_8d4.json", paths)
        self.assertNotIn("export_full/structured/StreamingAssets/Data/Json/LevelScriptData/indie_dg002/8700040000.json", paths)

    def test_mission_area_uses_authored_pin_without_proximity_story_fanout(self):
        mission = {
            "flow": {"mapPins": [{
                "scene": "indie_dg002",
                "sourceType": "missionArea",
                "trackingType": "MissionAreaTrackingInfo",
                "missionAreaId": "e0m1_002",
                "position": {"x": -231.85, "y": 86.76, "z": -72.0},
                "questIds": ["e0m0_q#1"],
            }]},
            "timelineRecovery": {"levelscriptSpatialProximity": [{
                "sceneKey": "cutscene_e0m0_13",
                "scriptId": "8700040001",
                "pin": {"sourceType": "missionArea", "missionAreaId": "e0m1_002"},
            }]},
        }
        area = {"subDataParentId": 8700020000, "shape": {
            "type": 1,
            "position": {"x": -231.85, "y": 86.76, "z": -72.0},
            "eulerAngles": {"x": 0, "y": 355.854, "z": 0},
            "size": {"x": 10, "y": 10, "z": 25},
            "radius": 0,
        }}
        with mock.patch.object(builder, "_mission_runtime_asset", return_value="mission.json"), \
                mock.patch.object(builder, "_exact_mission_area_definition", return_value=area):
            rows = builder._collect_trigger_markers(mission, "e0m0", "indie_dg002")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["sceneKeys"], [])
        self.assertEqual(rows[0]["storyBindingStatus"], "unresolved")
        self.assertEqual(rows[0]["identity"], "mission_area:e0m0:e0m1_002:0")
        self.assertEqual(rows[0]["triggerShape"]["type"], "box")
        self.assertEqual(rows[0]["triggerShape"]["size"]["z"], 25)
        self.assertEqual(rows[0]["subDataParentId"], 8700020000)
        self.assertEqual(
            [pin["path"] for pin in rows[0]["relatedFiles"]],
            [builder.MISSION_AREA_TABLE_REL, "mission.json"],
        )

    def test_unplaced_stories_state_why_each_scene_is_absent(self):
        mission = {
            "flow": {
                "sceneGraph": {"nodes": [
                    {"key": "placed", "kind": "radio"},
                    {"key": "scoped", "kind": "radio"},
                    {"key": "elsewhere", "kind": "cutscene"},
                    {"key": "ordered", "kind": "cutscene"},
                    {"key": "nothing", "kind": "cutscene"},
                ]},
                "missionStoryConnections": [],
            },
            "timelineRecovery": {"scenePlacement": {"ordered": {"kind": "cutscene"}}},
            "extras": {"sceneBindings": {"elsewhere": {"chains": [{"levelId": "indie_dg004", "steps": []}]}}},
        }
        with mock.patch.object(builder, "_conv_file_for_key", side_effect=lambda language, key: f"webui/data/lang/{language}/conv/{key}.json"):
            report = builder._unplaced_report(builder._unplaced_story_rows(
                builder._placement_marked_scene_universe(mission),
                builder._cross_level_scenes(mission, "indie_dg002"),
                "indie_dg002",
                "CN",
                {"webui/data/lang/CN/conv/placed.json"},
                {"webui/data/lang/CN/conv/scoped.json"},
            ))

        reasons = {row["key"]: row["reason"] for row in report["stories"]}
        self.assertNotIn("placed", reasons)
        self.assertEqual(reasons["scoped"], "mission_scope_only")
        self.assertEqual(reasons["elsewhere"], "cross_level_binding")
        self.assertEqual(reasons["ordered"], "graph_evidence_only")
        self.assertEqual(reasons["nothing"], "no_placement_evidence")
        self.assertEqual(report["count"], 4)
        self.assertIn("indie_dg004", next(row["detail"] for row in report["stories"] if row["key"] == "elsewhere"))

    def test_story_index_separates_exact_narrow_and_whole_mission_scopes(self):
        mission = {
            "flow": {
                "missionStoryConnections": [
                    {
                        "key": "exact_scene",
                        "producerEntityPositionStatus": "exact_unique_world_entity_registry_script_slot",
                        "producerEntities": [{"scriptIdGlobal": "8700040013", "slotId": "40007"}],
                        "producerScriptIds": ["8700040013"],
                        "anchorQuestIds": ["e0m0_q#2"],
                        "missionAreaIds": ["area_a"],
                        "sourceFiles": ["export_full/x.json"],
                    },
                    {"key": "broad_scene", "missionAreaIds": ["area_a", "area_b"]},
                ],
            },
        }
        with mock.patch.object(builder, "_conv_file_for_key", side_effect=lambda language, key: f"webui/data/lang/{language}/conv/{key}.json"):
            index = builder._story_index(mission, "CN")

        self.assertEqual([row["key"] for row in index["slot:8700040013:40007"]], ["exact_scene"])
        # The slot gate is independent of the quest and mission-area scopes:
        # those describe when the scene plays, not which entity plays it.
        self.assertNotIn("script:8700040013", index)
        self.assertEqual([row["key"] for row in index["quest:e0m0_q#2"]], ["exact_scene"])
        # `area_a` is narrower than the mission's full area set, so it keeps its
        # per-area pin; the scene covering every area is filed mission-wide
        # instead of being repeated on each trigger.
        self.assertEqual([row["key"] for row in index["area:area_a"]], ["exact_scene"])
        self.assertNotIn("area:area_b", index)
        self.assertEqual([row["key"] for row in index["mission:areas"]], ["broad_scene"])


class LevelGeneralizationTests(unittest.TestCase):
    """Every level is recovered from the same sources, with no level named in code."""

    def test_registry_ids_bucket_onto_the_level_their_leading_digits_encode(self):
        registry = {
            "worldEntityBriefInfos": {"8700020001": {"detailId": "int_doodad_a", "position": {"x": 0, "y": 0, "z": 0}}},
            "m_scriptEntityIdList": [
                {"scriptIdGlobal": 8700040013, "slotId": 40007},
                {"scriptIdGlobal": 23900030000, "slotId": 30001},
                # idNum 4242 is declared by no level row, so it can be plotted
                # in no coordinate space and must be dropped rather than guessed.
                {"scriptIdGlobal": 424200000001, "slotId": 1},
            ],
            "m_scriptEntityBriefInfo": [
                {"entityType": 32, "detailId": "int_simple_travel_pole", "position": {"x": 1, "y": 2, "z": 3}},
                {"entityType": 32, "detailId": "int_narrative_empty", "position": {"x": 4, "y": 5, "z": 6}},
                {"entityType": 32, "detailId": "int_empty", "position": {"x": 7, "y": 8, "z": 9}},
            ],
            "npcProxyBriefInfos": {"8700010000": {"proxyId": "chen_indie_dg002", "position": {"x": 0, "y": 0, "z": 0}}},
        }
        buckets = builder._registry_by_level(registry, {"indie_dg002": 87, "indie_dg004": 239})

        self.assertEqual(len(buckets["indie_dg002"]["world"]), 1)
        self.assertEqual(len(buckets["indie_dg002"]["script"]), 1)
        self.assertEqual(len(buckets["indie_dg002"]["npc"]), 1)
        self.assertEqual(len(buckets["indie_dg004"]["script"]), 1)
        self.assertNotIn("", buckets)
        self.assertEqual(sorted(buckets), ["indie_dg002", "indie_dg004"])

    def test_entity_classification_prefers_detail_id_then_entity_type(self):
        kind, sub_kind, label, _ = builder._classify_entity("int_narrative_common_BTomb01", 32)
        self.assertEqual((kind, sub_kind, label), ("scenery", "tomb", "墓碑"))
        self.assertEqual(builder._classify_entity("int_narrative_empty", 32)[0], "narrative")
        # A second filter level separates chests from the other collectibles,
        # which is the distinction the layer tree exposes.
        self.assertEqual(builder._classify_entity("int_trchest_common_normal", 32)[:2], ("collectible", "chest"))
        self.assertEqual(builder._classify_entity("int_goldcoin_1", 32)[:2], ("collectible", "currency"))
        self.assertEqual(builder._classify_entity("eny_0029_lbmob", 16)[0], "enemy")
        # No detailId rule matches, so the registry's own entityType decides.
        self.assertEqual(builder._classify_entity("int_unknown_thing", 16)[0], "enemy")
        self.assertEqual(builder._classify_entity("", None)[:2], ("scenery", "unclassified"))

    def test_quest_centroid_spanning_two_levels_is_plotted_on_neither(self):
        self.assertTrue(builder._quest_belongs_to_level({"scenes": ["map01_lv001"]}, "map01_lv001"))
        self.assertFalse(builder._quest_belongs_to_level({"scenes": ["map01_lv001"]}, "map02_lv002"))
        # A centroid averaged over two coordinate spaces exists in neither.
        self.assertFalse(builder._quest_belongs_to_level({"scenes": ["map01_lv001", "map02_lv002"]}, "map01_lv001"))
        # A row that names no scene claims no other level.
        self.assertTrue(builder._quest_belongs_to_level({}, "map01_lv001"))

    def test_attachment_index_keeps_proxy_and_script_bindings_apart(self):
        mission = {
            "timelineRecovery": {
                "npcProxyDialogAttachments": [{"sceneKey": "dlg_a1m9_2", "questId": "a1m9_q#3", "npcProxyId": "weiermolin_map02_v1d2d0_a1m9Start"}],
                "scriptConditionAttachments": [{"sceneKey": "dlg_c13m2_5", "questId": "c13m2_q#5", "mapId": "map01_lv007", "scriptId": "2800080001"}],
            },
        }
        with mock.patch.object(builder, "_conv_file_for_key", side_effect=lambda language, key: f"webui/data/lang/{language}/conv/{key}.json"), \
                mock.patch.object(builder, "_script_file_for_id", return_value=None):
            index = builder._attachment_story_index(mission, "CN")

        self.assertEqual([row["key"] for row in index["proxy:weiermolin_map02_v1d2d0_a1m9Start"]], ["dlg_a1m9_2"])
        self.assertEqual([row["key"] for row in index["condition:2800080001"]], ["dlg_c13m2_5"])

    def test_npc_phases_keep_only_explicit_mission_quest_attachments(self):
        phases = builder._npc_mission_phases([
            {"mission": "a1m9", "questId": "a1m9_q#3", "key": "dlg_a1m9_2"},
            {"mission": "a1m9", "questId": "a1m9_q#3", "key": "dlg_a1m9_3"},
            {"mission": "a1m9", "questId": None, "key": "dlg_without_phase"},
            {"mission": "", "questId": "unknown_q#1", "key": "dlg_without_mission"},
        ])

        self.assertEqual(phases, [{
            "missionId": "a1m9",
            "questId": "a1m9_q#3",
            "sceneKeys": ["dlg_a1m9_2", "dlg_a1m9_3"],
        }])

    def test_map_pins_only_plot_in_the_level_they_name(self):
        mission = {
            "flow": {
                "mapPins": [
                    {"scene": "base01_lv001", "sourceType": "npcProxy", "position": {"x": 1, "y": 2, "z": 3}, "questIds": ["a1m10_q#2"], "npcProxyId": "pelica_base01_lv001"},
                    {"scene": "map02_lv002", "sourceType": "trackingPos", "position": {"x": 9, "y": 9, "z": 9}, "questIds": []},
                    # Mission-area pins are plotted from the proximity rows,
                    # which also carry the level script behind the volume.
                    {"scene": "base01_lv001", "sourceType": "missionArea", "position": {"x": 4, "y": 4, "z": 4}},
                ],
            },
        }
        attachments = {"proxy:pelica_base01_lv001": [{"key": "dlg_a1m10_1", "convFile": "webui/data/lang/CN/conv/dlg_a1m10_1.json", "sourceFiles": []}]}
        with mock.patch.object(builder, "_mission_runtime_asset", return_value=None):
            rows = builder._map_pin_markers(mission, "CN", {}, attachments, "a1m10", "base01_lv001")

        self.assertEqual([row["kind"] for row in rows], ["npc"])
        self.assertEqual(rows[0]["sceneKeys"], ["dlg_a1m10_1"])
        self.assertTrue(rows[0]["registryBacked"])
        self.assertEqual(
            [pin["relation"] for pin in rows[0]["relatedFiles"]],
            ["story_npc_proxy"],
        )

    def test_reading_receivers_are_indexed_by_running_and_producing_script(self):
        index = builder._reading_receivers_by_level({
            "text_c13m2_1": [{"levelId": "map01_lv007", "scriptId": "2800080008", "sourceFile": "a.json"}],
            "text_e0m0_1": [{
                "scriptId": "8700020019",
                "sourceFile": "b.json",
                "interactiveEventProducers": [{"scriptIdGlobal": "8700020018", "entitySlotId": 40001}],
            }],
        })

        self.assertEqual([row["key"] for row in index["map01_lv007"]["2800080008"]], ["text_c13m2_1"])
        # The row declares no level, so it is offered to every level under "".
        # It reaches both the script that runs the action and the script that
        # serializes the producing entity, which are different identities.
        self.assertEqual(sorted(index[""]), ["8700020018", "8700020019"])

    def test_registry_backed_markers_drop_the_repeated_level_wide_registry_pin(self):
        entities = {
            "world": [("8700020001", {"entityType": 32, "detailId": "int_doodad_a", "position": {"x": 0, "y": 0, "z": 0}})],
            "script": [],
            "npc": [],
        }
        with mock.patch.object(builder, "_script_file_for_id", return_value=None):
            rows = builder._registry_markers(entities, "indie_dg002", "CN", {}, {}, {}, {})

        self.assertTrue(rows[0]["registryBacked"])
        # Repeating one identical 7 MB path on every node is what the flag
        # replaces; the map's own relatedFiles still publishes it once.
        self.assertEqual([pin["relation"] for pin in rows[0]["relatedFiles"]], [])

    def test_world_tomb_marker_uses_exact_leveldata_narrative_binding(self):
        entities = {
            "world": [("8700020002", {
                "entityType": 32,
                "detailId": "int_narrative_common_BTomb02",
                "position": {"x": 264.8843, "y": 60.1501, "z": 624.9785},
            })],
            "script": [],
            "npc": [],
        }
        binding = {
            "embeddedLogicId": 8700020002,
            "entityDetailId": "int_narrative_common_BTomb02",
            "sourceFile": "export_full/structured/StreamingAssets/Data/Json/LevelData/indie_dg002/sub.json",
            "levelDataAsset": "indie_dg002_lv_data_sub_mission_e0m1",
            "recordIndex": 1,
            "recordOffset": 947,
            "originalStoryKey": "dlg_e0m0_0d9",
            "webuiStoryKey": "misc_dlg_e0m0_0d9",
            "nativeConsumer": "NarrativeComponent.ClientCollectNarrative",
            "nativeMappingId": "leveldata-interactive-narrative-config-v5",
        }
        with mock.patch.object(
            builder,
            "_conv_file_for_key",
            return_value="webui/data/lang/CN/conv/misc_dlg_e0m0_0d9.json",
        ):
            row = builder._registry_markers(
                entities, "indie_dg002", "CN", {}, {}, {}, {}, None,
                {"indie_dg002:8700020002": [binding]},
            )[0]

        self.assertEqual(row["sceneKeys"], ["misc_dlg_e0m0_0d9"])
        self.assertEqual(row["interactionStatus"], "exact_narrative_component")
        self.assertEqual(row["narrativeBindings"][0]["originalStoryKey"], "dlg_e0m0_0d9")
        self.assertEqual(
            [pin["relation"] for pin in row["relatedFiles"][:2]],
            ["story_world_narrative", "story_world_narrative"],
        )
        self.assertTrue(all(pin["strength"] == "strong" for pin in row["relatedFiles"][:2]))

    def test_script_container_context_does_not_fan_out_across_sibling_slots(self):
        entities = {
            "world": [],
            "script": [
                ({"scriptIdGlobal": "8700040001", "slotId": "40003"}, {"entityType": 32, "detailId": "int_empty", "position": {"x": 1, "y": 2, "z": 3}}),
                ({"scriptIdGlobal": "8700040001", "slotId": "40004"}, {"entityType": 32, "detailId": "int_empty", "position": {"x": 4, "y": 5, "z": 6}}),
            ],
            "npc": [],
        }
        broad_story = {"key": "radio_broad", "convFile": "webui/data/lang/CN/conv/radio_broad.json", "sourceFiles": ["shared.json"], "mission": "e0m0"}
        exact_story = {"key": "radio_exact", "convFile": "webui/data/lang/CN/conv/radio_exact.json", "sourceFiles": ["exact.json"], "mission": "e0m0"}
        rows = builder._registry_markers(
            entities,
            "indie_dg002",
            "CN",
            {
                "anchor:8700040001": [broad_story],
                "script:8700040001": [broad_story],
                "slot:8700040001:40003": [exact_story],
            },
            {"condition:8700040001": [broad_story]},
            {},
            {"8700040001": "shared.json"},
        )

        first, second = rows
        self.assertEqual(first["sceneKeys"], ["radio_exact"])
        self.assertEqual(first["missions"], ["e0m0"])
        self.assertEqual([pin["path"] for pin in first["relatedFiles"]], [
            "webui/data/lang/CN/conv/radio_exact.json",
            "exact.json",
        ])
        self.assertEqual(second["sceneKeys"], [])
        self.assertEqual(second["missions"], [])
        self.assertEqual(second["relatedFiles"], [])
        self.assertNotIn("sourceFiles", first)
        self.assertNotIn("sourceFiles", second)

    def test_registered_action_pointer_candidate_gets_own_hidden_layer_without_story_fanout(self):
        entities = {
            "world": [],
            "script": [
                ({"scriptIdGlobal": "8700010002", "slotId": "40003"}, {"entityType": 32, "detailId": "int_empty", "position": {"x": 1, "y": 2, "z": 3}}),
                ({"scriptIdGlobal": "8700010002", "slotId": "40004"}, {"entityType": 32, "detailId": "int_empty", "position": {"x": 4, "y": 5, "z": 6}}),
            ],
            "npc": [],
        }
        targets = {"8700010002:40003": [{
            "actionName": "LevelCameraLookAt",
            "actionLocalId": 23,
            "actionRecordOffset": 777,
            "pointerOffset": 1037,
            "sourceFile": "8700010002.json",
            "controlTriggers": [{"headerName": "ScriptEvent_OnLeaderEnterTriggerVolume", "triggerSlotId": 80002}],
        }]}
        rows = builder._registry_markers(entities, "indie_dg002", "CN", {}, {}, {}, {}, targets)

        first, second = rows
        self.assertEqual(first["kind"], "script_target_candidate")
        self.assertEqual(first["interactionStatus"], "unresolved_action_formatter_member")
        self.assertEqual(first["sceneKeys"], [])
        self.assertEqual(first["missions"], [])
        self.assertEqual(first["actions"], [])
        self.assertEqual(first["actionBindingStatus"], "unresolved_decoder")
        self.assertEqual(
            first["unresolvedActionReferences"][0]["name"],
            "LevelCameraLookAt",
        )
        self.assertEqual(
            first["unresolvedActionReferences"][0]["controlTriggers"][0]["triggerSlotId"],
            80002,
        )
        self.assertEqual(first["relatedFiles"][0]["strength"], "weak")
        self.assertEqual(second["kind"], "empty_slot")
        self.assertEqual(second["actionBindingStatus"], "no_reference_observed")
        self.assertEqual(second["actions"], [])
        self.assertEqual(second["unresolvedActionReferences"], [])
        self.assertEqual(second["relatedFiles"], [])

    def test_native_formatter_resolved_action_target_gets_exact_layer(self):
        entities = {
            "world": [],
            "script": [
                ({"scriptIdGlobal": "8700010002", "slotId": "40003"},
                 {"entityType": 32, "detailId": "int_empty",
                  "position": {"x": 1, "y": 2, "z": 3}}),
            ],
            "npc": [],
        }
        targets = {"8700010002:40003": [{
            "status": "exact_registered_script_action_target",
            "actionName": "EntityMoveToWithDuration",
            "fieldName": "_entity",
            "memberOrdinalZeroBased": 11,
            "sourceFile": "8700010002.json",
            "controlTriggers": [],
        }]}
        row = builder._registry_markers(
            entities, "indie_dg002", "CN", {}, {}, {}, {}, targets
        )[0]

        self.assertEqual(row["kind"], "script_target")
        self.assertEqual(row["subKind"], "registered_action_target")
        self.assertEqual(row["interactionStatus"], "exact_script_action_target")
        self.assertEqual(row["actions"][0]["fieldName"], "_entity")
        self.assertEqual(row["sceneKeys"], [])
        self.assertEqual(row["missions"], [])

    def test_exact_world_action_target_preserves_entity_kind_and_name(self):
        entities = {
            "world": [
                ("8700040028", {
                    "entityType": 32,
                    "detailId": "int_fac_battle_cannon_1_dg002",
                    "position": {"x": 1, "y": 2, "z": 3},
                }),
            ],
            "script": [],
            "npc": [],
        }
        targets = {"world:8700040028": [{
            "status": "exact_world_entity_action_target",
            "actionName": "FacForceBattleBuildingCast",
            "fieldName": "_entity",
            "fieldManagedType": "Beyond.Gameplay.Actions.Param<Beyond.Gameplay.Core.EntityPtr>",
            "memberOrdinalZeroBased": 8,
            "sourceFile": "8700040000.json",
            "controlTriggers": [{
                "headerName": "ScriptEvent_OnLeaderEnterTriggerVolume",
                "triggerSlotId": 80002,
            }],
        }]}

        row = builder._registry_markers(
            entities, "indie_dg002", "CN", {}, {}, {}, {}, targets
        )[0]

        self.assertEqual(row["kind"], "device")
        self.assertEqual(row["subKind"], "grenade_tower")
        self.assertEqual(row["label"], "榴弹塔")
        self.assertEqual(row["actions"][0]["fieldName"], "_entity")
        self.assertEqual(row["controlledByTriggers"][0]["triggerSlotId"], 80002)
        self.assertEqual(row["sceneKeys"], [])
        self.assertEqual(row["relatedFiles"][0]["relation"], "script_action_target_source")
        self.assertEqual(row["relatedFiles"][0]["strength"], "strong")

    def test_exact_world_action_target_promotes_consumed_empty_shell(self):
        entities = {
            "world": [("8700040999", {
                "entityType": 32,
                "detailId": "int_empty",
                "position": {"x": 1, "y": 2, "z": 3},
            })],
            "script": [],
            "npc": [],
        }
        targets = {"world:8700040999": [{
            "status": "exact_world_entity_action_target",
            "actionName": "SetEntityPosition",
            "fieldName": "_target",
            "sourceFile": "8700040000.json",
            "controlTriggers": [],
        }]}

        row = builder._registry_markers(
            entities, "indie_dg002", "CN", {}, {}, {}, {}, targets
        )[0]

        self.assertEqual(row["kind"], "script_target")
        self.assertEqual(row["subKind"], "world_action_target")
        self.assertEqual(row["label"], "SetEntityPosition")
        self.assertEqual(row["interactionStatus"], "exact_world_entity_action_target")


class FilterFacetTests(unittest.TestCase):
    """The page's mission and layer filters are driven by published facets."""

    def test_stories_remember_the_mission_that_authored_them(self):
        mission = {"flow": {"missionStoryConnections": [{"key": "scene", "producerScriptIds": ["1"]}]}}
        with mock.patch.object(builder, "_conv_file_for_key", side_effect=lambda language, key: f"webui/data/lang/{language}/conv/{key}.json"):
            index = builder._story_index(mission, "CN", "a1m9")
        self.assertEqual(index["script:1"][0]["mission"], "a1m9")
        # A level pools several missions, so the node has to be able to say
        # which of them put dialog on it.
        self.assertEqual(builder._story_missions(index["script:1"]), ["a1m9"])

    def test_story_missions_ignores_rows_with_no_owner(self):
        self.assertEqual(builder._story_missions([{"mission": ""}, {"key": "x"}]), [])
        self.assertEqual(
            builder._story_missions([{"mission": "b"}], [{"mission": "a"}, {"mission": "b"}]),
            ["a", "b"],
        )

    def test_facets_publish_a_two_level_layer_tree_and_mission_weights(self):
        markers = [
            {"kind": "collectible", "subKind": "chest", "label": "宝箱", "storyCount": 0, "sceneKeys": []},
            {"kind": "collectible", "subKind": "chest", "label": "宝箱", "storyCount": 0, "sceneKeys": []},
            {"kind": "collectible", "subKind": "currency", "label": "货币", "storyCount": 0, "sceneKeys": []},
            {"kind": "npc", "subKind": "npc_proxy", "label": "pelica", "storyCount": 1, "sceneKeys": ["dlg_1"], "missions": ["a1m10"]},
        ]
        quests = [{"questId": "a1m10_q#1", "missions": ["a1m10"]}]
        facets = builder._facets(markers, quests, ["a1m10"])

        self.assertEqual(facets["kinds"]["collectible"]["count"], 3)
        # Chests are separable from the other collectibles, which is the whole
        # point of the second level.
        self.assertEqual(facets["kinds"]["collectible"]["subKinds"]["chest"]["count"], 2)
        self.assertEqual(facets["kinds"]["collectible"]["subKinds"]["currency"]["label"], "货币")
        self.assertEqual(facets["kinds"]["npc"]["storyCount"], 1)
        self.assertEqual(facets["missions"]["a1m10"], {"markers": 1, "questPoints": 1, "stories": 1})

    def test_a_mission_with_no_plotted_node_still_appears_with_zero_weight(self):
        facets = builder._facets([], [], ["e0m0"])
        self.assertEqual(facets["missions"]["e0m0"], {"markers": 0, "questPoints": 0, "stories": 0})


class MapNamingAndMinimapTests(unittest.TestCase):
    """Level display names and the in-game map-screen background."""

    def _write_tile(self, root, name, rgba):
        tile_dir = root / "export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/Texture2D"
        tile_dir.mkdir(parents=True, exist_ok=True)
        path = tile_dir / name
        row = bytes(rgba) * 4
        builder._png_write(path, 4, 4, [row] * 4)
        return path

    def _write_config(self, root, level_id, cells):
        config_dir = root / "export_full/structured/StreamingAssets/Data/Json/UILevelMapLoadConfig"
        config_dir.mkdir(parents=True, exist_ok=True)
        chunks = {
            f"m_{level_id}_{x}_{y}": {
                "chunkId": f"m_{level_id}_{x}_{y}",
                "lodType": 1,
                "x": x,
                "y": y,
                "worldCenter": {"x": x * 128 - 64, "y": y * 128 - 64},
                "worldLeftBottom": {"x": (x - 1) * 128.0, "y": (y - 1) * 128.0},
                "worldRightTop": {"x": x * 128.0, "y": y * 128.0},
            }
            for x, y in cells
        }
        (config_dir / f"{level_id}.json").write_text(json.dumps({"basic": {}, "mediumChunks": chunks}), encoding="utf-8")

    def test_level_families_use_the_recovered_region_names(self):
        self.assertEqual(builder._level_family("map01_lv001"), "四号谷地 / Valley-IV Map01")
        self.assertEqual(builder._level_family("map02_lv002"), "武陵 / Wuling Map02")
        self.assertEqual(builder._level_family("indie_dg002"), "独立场景 / Indie")

    def test_region_key_keeps_each_large_scene_coordinate_space_separate(self):
        self.assertEqual(builder._region_key("map01_lv001"), "map01")
        self.assertEqual(builder._region_key("map02_lv008"), "map02")
        self.assertEqual(builder._region_key("indie_dg002"), "indie_dg002")

    def test_ui_config_tiers_are_read_from_tier_names_and_tier_infos(self):
        config = {
            "tierNames": {"254": "scene_layer_upper"},
            "tierInfos": {
                "h_test_lv001_2_3_tier_254": {
                    "tierId": 254,
                    "tierLoadId": "h_test_lv001_2_3_tier_254",
                    "worldLeftBottom": {"x": 10, "y": 20},
                    "worldRightTop": {"x": 30, "y": 40},
                }
            },
        }
        rows = builder._config_tier_rows(config)
        self.assertEqual(rows["254"][0]["layer"], "h")
        self.assertEqual((rows["254"][0]["x"], rows["254"][0]["y"]), (2, 3))
        self.assertEqual(rows["254"][0]["rect"], (10.0, 20.0, 30.0, 40.0))

    def test_map_layer_metadata_joins_marker_by_raw_tier_footprint_and_reports_y(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_dir = root / "export_full/structured/StreamingAssets/Data/Json/UILevelMapLoadConfig"
            config_dir.mkdir(parents=True)
            (config_dir / "test_lv_tier.json").write_text(json.dumps({
                "basic": {
                    "worldRectLeftBottom": {"x": 0, "y": 0},
                    "worldRectRightTop": {"x": 128, "y": 128},
                    "needInverseXZ": False,
                },
                "tierNames": {"7": "scene_upper"},
                "tierInfos": {
                    "h_test_lv_tier_1_1_tier_7": {
                        "tierId": 7,
                        "tierLoadId": "h_test_lv_tier_1_1_tier_7",
                        "worldLeftBottom": {"x": 0, "y": 0},
                        "worldRightTop": {"x": 64, "y": 64},
                    }
                },
            }), encoding="utf-8")
            points = [{"x": 10.0, "y": 42.5, "z": 20.0}, {"x": 100.0, "y": 5.0, "z": 100.0}]
            with mock.patch.object(builder, "ROOT", root):
                result = builder._map_layer_metadata("test_lv_tier", points)
        self.assertEqual(points[0]["mapLayerIds"], ["tier:7"])
        self.assertNotIn("mapLayerIds", points[1])
        self.assertEqual(result["layers"][0]["heightRange"], {"minY": 42.5, "maxY": 42.5})
        self.assertFalse(result["needInverseXZ"])

    def test_map_layer_metadata_publishes_membership_on_full_node_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_dir = root / "export_full/structured/StreamingAssets/Data/Json/UILevelMapLoadConfig"
            config_dir.mkdir(parents=True)
            (config_dir / "test_lv_node.json").write_text(json.dumps({
                "tierNames": {"7": "floor_7"},
                "tierInfos": {"h_test_lv_node_1_1_tier_7": {
                    "tierLoadId": "h_test_lv_node_1_1_tier_7", "tierId": 7,
                    "worldLeftBottom": {"x": 0, "y": 0},
                    "worldRightTop": {"x": 64, "y": 64},
                }},
            }), encoding="utf-8")
            nodes = [{"identity": "marker:1", "position": {"x": 10.0, "y": 3.0, "z": 20.0}}]
            with mock.patch.object(builder, "ROOT", root):
                builder._map_layer_metadata("test_lv_node", nodes)
        self.assertEqual(nodes[0]["mapLayerIds"], ["tier:7"])
        self.assertNotIn("mapLayerIds", nodes[0]["position"])

    def test_map_layer_metadata_publishes_static_elements_in_authored_xz_space(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_dir = root / "export_full/structured/StreamingAssets/Data/Json/UILevelMapLoadConfig"
            config_dir.mkdir(parents=True)
            tables = root / "export_full/structured/StreamingAssets/Table"
            tables.mkdir(parents=True)
            (tables / "TextTable.json").write_text(json.dumps({
                "test_place": {"id": 987, "text": ""},
            }), encoding="utf-8")
            (tables / "I18nTextTable_CN.json").write_text(json.dumps({"987": "测试地点"}), encoding="utf-8")
            (config_dir / "test_lv_static.json").write_text(json.dumps({
                "basic": {
                    "worldRectLeftBottom": {"x": -64, "y": -128},
                    "worldRectRightTop": {"x": 192, "y": 256},
                    "needInverseXZ": True,
                },
                "staticElements": {
                    "se_1": {
                        "id": "test_lv_static_se_1",
                        "type": 1,
                        "position": {"x": 12.5, "y": 3.0, "z": -20.0},
                        "targetLevelId": "test_lv_other",
                        "textId": "test_place",
                    },
                    "se_invalid": {"id": "bad", "position": {"x": "12", "z": 4}},
                },
            }), encoding="utf-8")
            with mock.patch.object(builder, "ROOT", root):
                result = builder._map_layer_metadata("test_lv_static", [{"x": 1, "y": 2, "z": 3}])
        self.assertEqual(result["worldBounds"], {"minX": -64.0, "maxX": 192.0, "minZ": -128.0, "maxZ": 256.0})
        self.assertTrue(result["needInverseXZ"])
        self.assertEqual(result["orientation"], "world_xz_quarter_turn_clockwise")
        self.assertEqual(result["coordinateSystem"], "UILevelMapLoadConfig world X/Z; image top is +Z")
        self.assertEqual(result["staticElements"], [{
            "id": "test_lv_static_se_1",
            "type": 1,
            "position": {"x": 12.5, "y": 3.0, "z": -20.0},
            "targetLevelId": "test_lv_other",
            "textId": "test_place",
            "text": "测试地点",
            "evidence": "UILevelMapLoadConfig.staticElements exact X/Z position",
            "source": "export_full/structured/StreamingAssets/Data/Json/UILevelMapLoadConfig/test_lv_static.json",
        }])

    def test_level_names_resolve_the_level_table_rows_per_language(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tables = root / "export_full/structured/StreamingAssets/Table"
            tables.mkdir(parents=True)
            (tables / "LevelDescTable.json").write_text(json.dumps({
                "map01_lv001": {"id": "map01_lv001", "showName": {"id": 111, "text": ""}},
                "map02_lv002": {"id": "map02_lv002", "showName": {"id": 222, "text": ""}},
                "map02_lv000": {"id": "map02_lv000", "showName": {"id": 333, "text": ""}},
                "indie_dg002": {"id": "indie_dg002", "showName": {"id": 444, "text": ""}},
            }), encoding="utf-8")
            (tables / "I18nTextTable_CN.json").write_text(json.dumps({
                "111": "枢纽区",
                "222": "武陵城\t",
                "333": "?",
                "444": "？？？",
            }), encoding="utf-8")
            with mock.patch.object(builder, "ROOT", root):
                names = builder._level_names("CN")
        # Trailing tabs are stripped; empty and placeholder texts publish no
        # name so the reader falls back to the level id instead.
        self.assertEqual(names, {"map01_lv001": "枢纽区", "map02_lv002": "武陵城"})

    def test_mission_names_use_the_published_language_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "webui/data/lang/CN"
            folder.mkdir(parents=True)
            (folder / "missions.json").write_text(json.dumps({
                "missionNames": {"e0m0": "Cold Start", "blank": ""},
            }), encoding="utf-8")
            with mock.patch.object(builder, "ROOT", root):
                names = builder._mission_names("CN")
        self.assertEqual(names, {"e0m0": "Cold Start"})

    def test_minimap_background_composites_the_chunk_grid_top_z_up(self):
        red = (255, 0, 0, 255)
        green = (0, 255, 0, 255)
        blue = (0, 0, 255, 255)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_config(root, "test_lv001", [(1, 1), (1, 2)])
            # Cell (1,1) owns two near-duplicate exports; the lexicographically
            # first filename is the stable choice, so green wins over red.
            self._write_tile(root, "m_test_lv001_1_1_pAAAA.png", red)
            self._write_tile(root, "m_test_lv001_1_1_p0000.png", green)
            self._write_tile(root, "m_test_lv001_1_2_pBBBB.png", blue)
            with mock.patch.object(builder, "ROOT", root):
                info = builder._minimap_background("test_lv001")
                self.assertEqual(info["status"], "in_game_minimap")
                self.assertEqual(info["src"], "render/test_lv001_minimap.png")
                self.assertEqual(info["layer"], "m")
                self.assertEqual(info["tileCount"], 2)
                self.assertEqual(info["worldBounds"], {"minX": 0.0, "maxX": 128.0, "minZ": 0.0, "maxZ": 256.0})
                # y index 2 is the +Z side, so blue must sit on top and the
                # chosen (1,1) art, green, on the bottom.
                _w, _h, rgba = builder._png_decode(root / "webui/data/map_recovery/render/test_lv001_minimap.png")
                self.assertEqual((_w, _h), (4, 8))
                self.assertEqual(bytes(rgba[0][:4]), bytes(blue))
                self.assertEqual(bytes(rgba[7][:4]), bytes(green))
                # The sidecar records the chosen files by hash so an unchanged
                # rebuild reuses the composite instead of repainting it.
                self.assertTrue((root / "webui/data/map_recovery/render/test_lv001_minimap.sources.json").exists())
                again = builder._minimap_background("test_lv001")
                self.assertEqual(again, info)

    def test_minimap_background_preserves_exported_tile_rows_for_world_plus_z(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_config(root, "test_lv_axis", [(1, 1)])
            path = root / "export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/Texture2D/m_test_lv_axis_1_1_pABCD.png"
            # Source texture rows are top-to-bottom. Distinct corners make
            # both the local Z flip and X direction observable.
            rows = [
                bytes((10, 0, 0, 255)) * 2 + bytes((20, 0, 0, 255)) * 2,
                bytes((0, 0, 0, 0)) * 4,
                bytes((0, 0, 0, 0)) * 4,
                bytes((30, 0, 0, 255)) * 2 + bytes((40, 0, 0, 255)) * 2,
            ]
            path.parent.mkdir(parents=True, exist_ok=True)
            builder._png_write(path, 4, 4, rows)
            with mock.patch.object(builder, "ROOT", root):
                builder._minimap_background("test_lv_axis")
            _width, _height, rgba = builder._png_decode(root / "webui/data/map_recovery/render/test_lv_axis_minimap.png")
        # Exported tile rows are already authored top-to-bottom with +Z at
        # the image top; only the config-level inverse flag rotates the full
        # composite. X is not mirrored for a normal level.
        self.assertEqual(bytes(rgba[0][:4]), bytes((10, 0, 0, 255)))
        self.assertEqual(bytes(rgba[0][-4:]), bytes((20, 0, 0, 255)))
        self.assertEqual(bytes(rgba[-1][:4]), bytes((30, 0, 0, 255)))
        self.assertEqual(bytes(rgba[-1][-4:]), bytes((40, 0, 0, 255)))

    def test_minimap_background_preserves_art_when_world_pins_invert_xz(self):
        green = (0, 255, 0, 255)
        blue = (0, 0, 255, 255)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_dir = root / "export_full/structured/StreamingAssets/Data/Json/UILevelMapLoadConfig"
            config_dir.mkdir(parents=True)
            # needInverseXZ changes the world-pin projection, not the exported
            # image. The in-game Dijiang reference keeps this chunk ordering.
            (config_dir / "test_lv004.json").write_text(json.dumps({
                "basic": {"needInverseXZ": True},
                "mediumChunks": {
                    "m_test_lv004_1_1": {
                        "x": 1, "y": 1,
                        "worldLeftBottom": {"x": 0.0, "y": 0.0},
                        "worldRightTop": {"x": 128.0, "y": 128.0},
                    },
                    "m_test_lv004_1_2": {
                        "x": 1, "y": 2,
                        "worldLeftBottom": {"x": 0.0, "y": 128.0},
                        "worldRightTop": {"x": 128.0, "y": 256.0},
                    },
                },
            }), encoding="utf-8")
            self._write_tile(root, "m_test_lv004_1_1_pDDDD.png", green)
            self._write_tile(root, "m_test_lv004_1_2_pEEEE.png", blue)
            with mock.patch.object(builder, "ROOT", root):
                info = builder._minimap_background("test_lv004")
            self.assertEqual(info["status"], "in_game_minimap")
            self.assertTrue(info["inverted"])
            # The world rectangle and exported picture orientation are unchanged.
            self.assertEqual(info["worldBounds"], {"minX": 0.0, "maxX": 128.0, "minZ": 0.0, "maxZ": 256.0})
            _w, _h, rgba = builder._png_decode(root / "webui/data/map_recovery/render/test_lv004_minimap.png")
            self.assertEqual(bytes(rgba[0][:4]), bytes(blue))
            self.assertEqual(bytes(rgba[7][:4]), bytes(green))
            sidecar = json.loads((root / "webui/data/map_recovery/render/test_lv004_minimap.sources.json").read_text(encoding="utf-8"))
            self.assertTrue(sidecar["inverted"])
            self.assertEqual(sidecar["imageOrientation"], "exported")

    def test_minimap_background_publishes_transparent_configured_tier_art_separately(self):
        base = (40, 40, 40, 255)
        tier_top = (255, 0, 0, 255)
        tier_bottom = (0, 0, 255, 255)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_dir = root / "export_full/structured/StreamingAssets/Data/Json/UILevelMapLoadConfig"
            config_dir.mkdir(parents=True)
            (config_dir / "test_lv_tier.json").write_text(json.dumps({
                "basic": {},
                "tierNames": {"7": "scene_upper"},
                "tierInfos": {
                    "h_test_lv_tier_1_1_tier_7": {
                        "tierId": 7,
                        "tierLoadId": "h_test_lv_tier_1_1_tier_7",
                        "worldLeftBottom": {"x": 0, "y": 0},
                        "worldRightTop": {"x": 128, "y": 128},
                    }
                },
                "mediumChunks": {
                    "m_test_lv_tier_1_1": {
                        "x": 1, "y": 1,
                        "worldLeftBottom": {"x": 0, "y": 0},
                        "worldRightTop": {"x": 128, "y": 128},
                    }
                },
            }), encoding="utf-8")
            self._write_tile(root, "m_test_lv_tier_1_1_pAAAA.png", base)
            tier_path = root / "export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/Texture2D/h_test_lv_tier_1_1_tier_7_pBBBB.png"
            tier_path.parent.mkdir(parents=True, exist_ok=True)
            builder._png_write(tier_path, 4, 4, [bytes(tier_top) * 4, bytes((0, 0, 0, 0)) * 4, bytes((0, 0, 0, 0)) * 4, bytes(tier_bottom) * 4])
            with mock.patch.object(builder, "ROOT", root):
                info = builder._minimap_background("test_lv_tier")
            self.assertEqual(info["layers"][0]["id"], "tier:7")
            self.assertEqual(info["layers"][0]["status"], "in_game_map_tier")
            self.assertEqual(info["layers"][0]["tileCount"], 1)
            self.assertTrue((root / "webui/data/map_recovery/render/test_lv_tier_tier_7.png").exists())
            _w, _h, rgba = builder._png_decode(root / "webui/data/map_recovery/render/test_lv_tier_tier_7.png")
            self.assertEqual(bytes(rgba[0][:4]), bytes(tier_top))
            self.assertEqual(bytes(rgba[-1][:4]), bytes(tier_bottom))

    def test_minimap_background_stretches_half_size_chunks_to_their_rect(self):
        green = (0, 255, 0, 255)
        blue = (0, 0, 255, 255)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_dir = root / "export_full/structured/StreamingAssets/Data/Json/UILevelMapLoadConfig"
            config_dir.mkdir(parents=True)
            # (1,1) covers 128x128 world units, (1,2) covers 256x128: the same
            # 4x4 texture must draw at a different pixel size for each.
            (config_dir / "test_lv003.json").write_text(json.dumps({"basic": {}, "mediumChunks": {
                "m_test_lv003_1_1": {
                    "x": 1, "y": 1,
                    "worldLeftBottom": {"x": 0.0, "y": 0.0},
                    "worldRightTop": {"x": 128.0, "y": 128.0},
                },
                "m_test_lv003_1_2": {
                    "x": 1, "y": 2,
                    "worldLeftBottom": {"x": 0.0, "y": 128.0},
                    "worldRightTop": {"x": 256.0, "y": 256.0},
                },
            }}), encoding="utf-8")
            self._write_tile(root, "m_test_lv003_1_1_pDDDD.png", green)
            self._write_tile(root, "m_test_lv003_1_2_pEEEE.png", blue)
            with mock.patch.object(builder, "ROOT", root):
                info = builder._minimap_background("test_lv003")
            self.assertEqual(info["status"], "in_game_minimap")
            self.assertEqual(info["worldBounds"], {"minX": 0.0, "maxX": 256.0, "minZ": 0.0, "maxZ": 256.0})
            _w, _h, rgba = builder._png_decode(root / "webui/data/map_recovery/render/test_lv003_minimap.png")
            # The canvas follows the world rectangle (256x256 units) at the
            # scale of the largest chunk, so the big chunk fills the +Z half
            # natively while the small chunk is drawn at reduced size in its
            # own 128x128 corner of the -Z half; the remaining corner stays
            # clear.
            self.assertEqual((_w, _h), (4, 8))
            self.assertEqual(bytes(rgba[0][:4]), bytes(blue))
            self.assertEqual(bytes(rgba[7][:4]), bytes(green))
            self.assertEqual(bytes(rgba[7][8:12]), bytes((0, 0, 0, 0)))

    def test_minimap_background_fails_closed_on_an_incomplete_grid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cells = [(1, 1), (1, 2), (2, 2)]  # a hole at (2,1)
            self._write_config(root, "test_lv002", cells)
            for x, y in cells:
                self._write_tile(root, f"m_test_lv002_{x}_{y}_pCCCC.png", (10, 20, 30, 255))
            with mock.patch.object(builder, "ROOT", root):
                info = builder._minimap_background("test_lv002")
            self.assertEqual(info["status"], "in_game_minimap_missing")
            self.assertIsNone(info["src"])
            self.assertFalse((root / "webui/data/map_recovery").exists())


if __name__ == "__main__":
    unittest.main()
