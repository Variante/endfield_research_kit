from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.story_builder import level_bindings
from scripts.story_builder.anime_assets import (
    _build_mission_area_index,
    _extract_tracking_hints,
)
from scripts.story_builder.level_bindings import (
    _parse_interactive_object_template_index,
    extract_tracked_interactive_story_targets,
    resolve_interactive_condition_script_entity,
    resolve_entity_tracking_script,
)
from scripts.story_builder.mission_recovery import (
    _logic_id_from_entity_ptr,
    decode_mission_interactive_script_entity_conditions,
    decode_mission_world_entity_condition_groups,
    decode_mission_world_entity_condition_refs,
)


class EntityTrackingStoryContextTests(unittest.TestCase):
    def test_entity_ptr_logic_id_gate_is_shared_and_fail_closed(self) -> None:
        self.assertEqual(
            _logic_id_from_entity_ptr({
                "constValue": {"useSlotId": False, "logicId": 42},
            }),
            42,
        )
        self.assertIsNone(_logic_id_from_entity_ptr({
            "useSlotId": True,
            "logicId": 42,
        }))
        self.assertIsNone(_logic_id_from_entity_ptr({
            "useSlotId": False,
            "logicId": True,
        }))

    def test_decodes_grouped_world_entity_condition_foreign_keys(self) -> None:
        raw = {
            "questDic": {
                "mission_q#1": {
                    "questId": "mission_q#1",
                    "objectiveList": [{
                        "condition": {
                            "$type": (
                                "Beyond.Gameplay.CheckMonsterKilled, "
                                "Gameplay.Beyond"
                            ),
                            "_sceneId": {"constValue": "map_fixture_lv001"},
                            "_enemyIds": {"constValue": [
                                {"useSlotId": False, "logicId": 101, "slotId": 0},
                                {"useSlotId": False, "logicId": 102, "slotId": 0},
                                {"useSlotId": False, "logicId": 103, "slotId": 0},
                            ]},
                        },
                    }],
                },
                "mission_q#2": {
                    "questId": "mission_q#2",
                    "objectiveList": [{
                        "condition": {
                            "$type": (
                                "Beyond.Gameplay.CombineCondition, "
                                "Gameplay.Beyond"
                            ),
                            "conditionEvalString": "{0}and{1}",
                            "subConditions": [
                                {
                                    "$type": (
                                        "Beyond.Gameplay.InteractiveCheckInt, "
                                        "Gameplay.Beyond"
                                    ),
                                    "_levelId": {
                                        "constValue": "map_fixture_lv002"
                                    },
                                    "_entityId": {"constValue": {
                                        "useSlotId": False,
                                        "logicId": 201,
                                        "slotId": 0,
                                    }},
                                },
                                {
                                    "$type": (
                                        "Beyond.Gameplay.InteractiveCheckInt, "
                                        "Gameplay.Beyond"
                                    ),
                                    "_levelId": {
                                        "constValue": "map_fixture_lv002"
                                    },
                                    "_entityId": {"constValue": {
                                        "useSlotId": False,
                                        "logicId": 202,
                                        "slotId": 0,
                                    }},
                                },
                            ],
                        },
                    }],
                },
            },
        }
        groups = decode_mission_world_entity_condition_groups(raw)
        self.assertEqual(2, len(groups))
        self.assertEqual(
            [101, 102, 103],
            groups[0]["entityLogicIds"],
        )
        self.assertEqual(
            "combined_interactive_int_entity_set",
            groups[1]["groupType"],
        )
        self.assertEqual([201, 202], groups[1]["entityLogicIds"])

        refs = decode_mission_world_entity_condition_refs(raw)
        self.assertEqual(5, len(refs))
        self.assertEqual(
            {101, 102, 103, 201, 202},
            {row["logicId"] for row in refs},
        )

    def test_decodes_only_logic_backed_interactive_check_int(self) -> None:
        raw = {
            "questDic": {
                "mission_q#1": {
                    "questId": "mission_q#1",
                    "objectiveList": [{
                        "condition": {
                            "$type": (
                                "Beyond.Gameplay.InteractiveCheckInt, "
                                "Gameplay.Beyond"
                            ),
                            "_entityId": {"constValue": {
                                "useSlotId": False,
                                "logicId": 90100123456,
                                "slotId": 0,
                            }},
                            "_levelId": {"constValue": "map_fixture_lv001"},
                            "_key": {"constValue": "state"},
                            "_compareValue": {"constValue": 1},
                            "_comparer": {"constValue": 0},
                        },
                    }, {
                        "condition": {
                            "$type": (
                                "Beyond.Gameplay.InteractiveCheckInt, "
                                "Gameplay.Beyond"
                            ),
                            "_entityId": {"constValue": {
                                "useSlotId": True,
                                "logicId": 90100123457,
                                "slotId": 40001,
                            }},
                            "_levelId": {"constValue": "map_fixture_lv001"},
                        },
                    }],
                },
            },
        }
        self.assertEqual([{
            "questId": "mission_q#1",
            "type": "Beyond.Gameplay.InteractiveCheckInt, Gameplay.Beyond",
            "mapId": "map_fixture_lv001",
            "logicId": 90100123456,
            "useSlotId": False,
            "slotId": 0,
            "key": "state",
            "compareValue": 1,
            "comparer": 0,
        }], decode_mission_interactive_script_entity_conditions(raw))

    def test_interactive_condition_requires_registry_and_exact_levelscript(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            gameplay_dir = root / "GameplayConfig"
            levelscript_dir = root / "LevelScriptData"
            level_id = "map_fixture_lv001"
            script_id = 90100123456
            gameplay_dir.mkdir(parents=True)
            (levelscript_dir / level_id).mkdir(parents=True)
            (gameplay_dir / "WorldEntityRegistry.json").write_text(
                json.dumps({
                    "m_scriptEntityIdList": [{
                        "scriptIdGlobal": script_id,
                        "slotId": 40001,
                    }],
                    "m_scriptEntityBriefInfo": [{
                        "entityType": 32,
                        "detailId": "int_option_proxy",
                    }],
                }),
                encoding="utf-8",
            )
            (levelscript_dir / level_id / f"{script_id}.json").write_bytes(
                b"fixture"
            )
            condition = {
                "type": "Beyond.Gameplay.InteractiveCheckInt, Gameplay.Beyond",
                "mapId": level_id,
                "logicId": script_id,
                "useSlotId": False,
            }
            with (
                patch.object(level_bindings, "GAMEPLAY_CONFIG_DIR", gameplay_dir),
                patch.object(level_bindings, "LEVELSCRIPT_DIR", levelscript_dir),
            ):
                resolution = resolve_interactive_condition_script_entity(
                    condition
                )
                missing = resolve_interactive_condition_script_entity({
                    **condition,
                    "logicId": script_id + 1,
                })

            self.assertEqual("unique", resolution["status"])
            self.assertEqual(str(script_id), resolution["scriptId"])
            self.assertEqual(40001, resolution["entitySlotId"])
            self.assertEqual("int_option_proxy", resolution["entityDetailId"])
            self.assertEqual("missing", missing["status"])

    def test_tracking_extractor_retains_native_script_entity_tuple(self) -> None:
        quest = {
            "objectiveList": [{
                "trackingInfoList": [{
                    "$type": "Beyond.Gameplay.EntityTrackingInfo, Gameplay.Beyond",
                    "sceneId": "map02_lv003",
                    "trackScriptEntity": True,
                    "entityLogicId": 70000,
                    "scriptId": 70000,
                    "entitySlotId": 40002,
                }],
            }],
        }

        self.assertEqual([{
            "type": "EntityTrackingInfo",
            "scene": "map02_lv003",
            "trackScriptEntity": True,
            "entityLogicId": 70000,
            "scriptId": 70000,
            "entitySlotId": 40002,
            "objectiveIndex": 1,
            "trackingIndex": 0,
        }], _extract_tracking_hints(quest))

    def test_tracking_extractor_reads_runtime_multi_description_wrapper(self) -> None:
        quest = {
            "objectiveList": [{
                "mapTrackingToMultiDesc": True,
                "trackingInfoList": [],
                "multiDescTrackingInfoList": [{
                    "actualList": [{
                        "$type": (
                            "Beyond.Gameplay.MissionAreaTrackingInfo, "
                            "Gameplay.Beyond"
                        ),
                        "sceneId": "dung_fixture",
                        "missionAreaId": "display_only",
                    }],
                }, {
                    "actualList": [{
                        "$type": (
                            "Beyond.Gameplay.EntityTrackingInfo, Gameplay.Beyond"
                        ),
                        "sceneId": "dung_fixture",
                        "trackScriptEntity": True,
                        "entityLogicId": 40001,
                        "scriptId": 8,
                        "entitySlotId": 40001,
                    }],
                }],
            }],
        }

        self.assertEqual([{
            "type": "EntityTrackingInfo",
            "scene": "dung_fixture",
            "trackScriptEntity": True,
            "entityLogicId": 40001,
            "scriptId": 8,
            "entitySlotId": 40001,
            "objectiveIndex": 1,
            "trackingIndex": 0,
            "trackingListSource": "multiDescTrackingInfoList.actualList",
            "multiDescriptionIndex": 1,
            "actualListIndex": 0,
        }], _extract_tracking_hints(quest))

    @staticmethod
    def _interactive_payload(slot_id: int, story_key: str) -> bytes:
        property_marker = (
            b"\x02\x07\x00\x00\x00type_id"
            b"\x02\x07\x00\x00\x00\x01\x00\x00\x00"
            b"\x02\x00\x00\x00\x00\x00\x00\x00\x00"
        )
        encoded_story = story_key.encode("ascii")
        return (
            b"\x1b\x02fixture-prefix"
            + slot_id.to_bytes(4, "little", signed=True)
            + b"\x19\x00\x00\x00"
            + b"int_narrative_empty"
            + property_marker
            + len(encoded_story).to_bytes(4, "little", signed=True)
            + encoded_story
            + b"fixture-tail"
        )

    @staticmethod
    def _interactive_table(object_id: str, template_id: str) -> bytes:
        def string(value: str) -> bytes:
            encoded = value.encode("utf-8")
            return len(encoded).to_bytes(4, "little", signed=True) + encoded

        return (
            b"\x02"
            + (1).to_bytes(4, "little", signed=True)
            + string(template_id)
            + string(f"Data/Json/Interactive/InteractiveData/data_{template_id}.json")
            + (1).to_bytes(4, "little", signed=True)
            + string(object_id)
            + b"\x01"
            + string(template_id)
        )

    def test_registry_resolution_and_exact_slot_type_id_property(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            gameplay_dir = root / "GameplayConfig"
            data_json_dir = root / "Data" / "Json"
            interactive_dir = data_json_dir / "Interactive"
            levelscript_dir = root / "LevelScriptData"
            scene_id = "map_fixture_lv001"
            scene_dir = levelscript_dir / scene_id
            gameplay_dir.mkdir(parents=True)
            interactive_dir.mkdir(parents=True)
            scene_dir.mkdir(parents=True)

            global_script_id = 90100123456
            local_script_id = global_script_id % 100_000_000
            slot_id = 40001
            story_key = "dlg_fixture_1"
            (gameplay_dir / "WorldEntityRegistry.json").write_text(
                json.dumps({
                    "m_scriptEntityIdList": [{
                        "scriptIdGlobal": global_script_id,
                        "slotId": slot_id,
                    }],
                    "m_scriptEntityBriefInfo": [{
                        "entityType": 5,
                        "detailId": "int_narrative_chip",
                        "position": {"x": 1, "y": 2, "z": 3},
                    }],
                }),
                encoding="utf-8",
            )
            (scene_dir / f"{global_script_id}.json").write_bytes(
                self._interactive_payload(slot_id, story_key)
            )
            (interactive_dir / "InteractiveTable.json").write_bytes(
                self._interactive_table(
                    "int_narrative_chip",
                    "int_narrative_mission",
                )
            )

            hint = {
                "type": "EntityTrackingInfo",
                "scene": scene_id,
                "trackScriptEntity": True,
                "scriptId": local_script_id,
                "entitySlotId": slot_id,
            }
            with (
                patch.object(level_bindings, "GAMEPLAY_CONFIG_DIR", gameplay_dir),
                patch.object(level_bindings, "DATA_JSON_DIR", data_json_dir),
                patch.object(level_bindings, "EXPORT_ROOT", root),
                patch.object(level_bindings, "LEVELSCRIPT_DIR", levelscript_dir),
                patch.object(
                    level_bindings,
                    "_INTERACTIVE_OBJECT_TEMPLATE_CACHE",
                    None,
                ),
            ):
                resolution = resolve_entity_tracking_script(hint)
                targets = extract_tracked_interactive_story_targets(resolution)

            self.assertEqual("unique", resolution["status"])
            self.assertEqual(str(global_script_id), resolution["scriptId"])
            self.assertEqual("int_narrative_chip", resolution["entityDetailId"])
            self.assertEqual([story_key], [row["storyKey"] for row in targets])
            self.assertEqual("type_id", targets[0]["propertyKey"])
            self.assertEqual(
                "int_narrative_mission",
                targets[0]["entityTemplateId"],
            )

    def test_interactive_template_guard_rejects_non_narrative_alias(self) -> None:
        narrative = _parse_interactive_object_template_index(
            self._interactive_table("int_narrative_chip", "int_narrative_mission")
        )
        beacon = _parse_interactive_object_template_index(
            self._interactive_table("int_mission_beacon_high", "int_mission_beacon")
        )
        self.assertEqual(
            "int_narrative_mission",
            narrative["objectToTemplate"]["int_narrative_chip"],
        )
        self.assertEqual(
            "int_mission_beacon",
            beacon["objectToTemplate"]["int_mission_beacon_high"],
        )
        self.assertEqual(
            {},
            _parse_interactive_object_template_index(
                self._interactive_table(
                    "int_narrative_chip",
                    "int_narrative_mission",
                )
                + b"trailing"
            ),
        )

    def test_mission_area_index_uses_level_num_for_duplicate_ids(self) -> None:
        table = {
            "m_areas": {
                "28": {
                    "same": {
                        "missionAreaId": "same",
                        "subDataParentId": 2800,
                    },
                },
                "131": {
                    "same": {
                        "missionAreaId": "same",
                        "subDataParentId": 13100,
                    },
                },
                "101": {
                    "unique": {
                        "missionAreaId": "unique",
                        "subDataParentId": 10100,
                    },
                },
            },
        }
        level_basic = {
            "map_a": {"id": "map_a", "idNum": 28},
            "dungeon_b": {"id": "dungeon_b", "idNum": 131},
            "map_unique": {"id": "map_unique", "idNum": 101},
        }
        index = _build_mission_area_index(table, level_basic)
        self.assertEqual(2800, index[("map_a", "same")]["subDataParentId"])
        self.assertEqual(
            13100,
            index[("dungeon_b", "same")]["subDataParentId"],
        )
        self.assertNotIn(("", "same"), index)
        self.assertEqual(10100, index[("", "unique")]["subDataParentId"])

    def test_rejects_misaligned_registry_arrays_and_untyped_hint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            gameplay_dir = root / "GameplayConfig"
            levelscript_dir = root / "LevelScriptData"
            scene_id = "map_fixture_lv002"
            (levelscript_dir / scene_id).mkdir(parents=True)
            gameplay_dir.mkdir(parents=True)
            (gameplay_dir / "WorldEntityRegistry.json").write_text(
                json.dumps({
                    "m_scriptEntityIdList": [{
                        "scriptIdGlobal": 90200000001,
                        "slotId": 40001,
                    }],
                    "m_scriptEntityBriefInfo": [],
                }),
                encoding="utf-8",
            )
            (levelscript_dir / scene_id / "90200000001.json").write_bytes(b"fixture")
            hint = {
                "type": "EntityTrackingInfo",
                "scene": scene_id,
                "trackScriptEntity": True,
                "scriptId": 1,
                "entitySlotId": 40001,
            }
            with (
                patch.object(level_bindings, "GAMEPLAY_CONFIG_DIR", gameplay_dir),
                patch.object(level_bindings, "LEVELSCRIPT_DIR", levelscript_dir),
            ):
                self.assertEqual("missing", resolve_entity_tracking_script(hint)["status"])
                self.assertEqual(
                    "not_script_entity",
                    resolve_entity_tracking_script({**hint, "type": "OtherTrackingInfo"})[
                        "status"
                    ],
                )


if __name__ == "__main__":
    unittest.main()
