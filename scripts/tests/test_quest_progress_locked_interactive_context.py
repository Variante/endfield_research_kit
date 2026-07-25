import json
import struct
import tempfile
import unittest
from pathlib import Path

from scripts.story_builder.level_bindings import (
    LEVELSCRIPT_NATIVE_HEADER_MAPPING_ID,
    build_quest_progress_locked_interactive_story_contexts,
    parse_level_interactive_quest_progress_lock,
)


class QuestProgressLockedInteractiveContextTests(unittest.TestCase):
    MISSION_ID = "mission_fixture"
    QUEST_ID = "mission_fixture_q#1"
    STORY_KEY = "radio_mission_fixture_1"
    SCENE_ID = "map_fixture"
    SCRIPT_ID = "21000000001"
    LOGIC_ID_A = 2100070023
    LOGIC_ID_B = 2100070024
    DETAIL_ID_A = "int_fixture_a"
    DETAIL_ID_B = "int_fixture_b"

    @staticmethod
    def _mp_string(value: str) -> bytes:
        encoded = value.encode("utf-8")
        return len(encoded).to_bytes(4, "little", signed=True) + encoded

    @classmethod
    def _record(
        cls,
        logic_id: int,
        detail_id: str,
        quest_id: str,
        *,
        compare_target: int = 3,
    ) -> bytes:
        component_properties = (
            (1).to_bytes(4, "little", signed=True)
            + (0).to_bytes(4, "little", signed=True)
            + (0).to_bytes(4, "little", signed=True)
        )
        return (
            b"\x19"
            + (b"\x00" * 24)
            + cls._mp_string(detail_id)
            + (32).to_bytes(4, "little", signed=True)
            + b"\x00\x00"
            + logic_id.to_bytes(8, "little", signed=False)
            + (b"\x00" * 38)
            + component_properties
            + (-1).to_bytes(4, "little", signed=True)
            + (-1).to_bytes(4, "little", signed=True)
            + b"\x00\x00\x00"
            + (-1).to_bytes(4, "little", signed=True)
            + (-1).to_bytes(4, "little", signed=True)
            + struct.pack("<f", 0.0)
            + b"\x10\x03"
            + (0).to_bytes(4, "little", signed=True)
            + compare_target.to_bytes(4, "little", signed=True)
            + cls._mp_string(quest_id)
            + (0).to_bytes(4, "little", signed=True)
        )

    @classmethod
    def _leveldata(
        cls,
        *,
        quest_id_b: str | None = None,
    ) -> tuple[bytes, list[tuple[int, int]]]:
        prefix = b"\x2bfixture" + (3).to_bytes(4, "little", signed=True)
        record_a = cls._record(cls.LOGIC_ID_A, cls.DETAIL_ID_A, cls.QUEST_ID)
        record_b = cls._record(
            cls.LOGIC_ID_B,
            cls.DETAIL_ID_B,
            quest_id_b or cls.QUEST_ID,
        )
        tail = b"\x19" + (b"\x00" * 24) + cls._mp_string("int_tail")
        start_a = len(prefix)
        start_b = start_a + len(record_a)
        start_tail = start_b + len(record_b)
        return (
            prefix + record_a + record_b + tail,
            [(start_a, start_b), (start_b, start_tail)],
        )

    @classmethod
    def _interactive_owner(cls, logic_id: int, local_id: int) -> dict:
        return {
            "status": "exact_serialized_control_path",
            "nativeHeaderMappingId": LEVELSCRIPT_NATIVE_HEADER_MAPPING_ID,
            "headerName": "EntityEvent_OnInteractiveStateChanged",
            "headerUnionTag": "0x001e",
            "headerSerializedMemberCount": 20,
            "headerLocalId": local_id,
            "pathLocalIds": [local_id + 1, local_id + 2],
            "eventDetail": {
                "type": "EntityEvent_OnInteractiveStateChanged",
                "payloadSchemaStatus": "exact_current_build_memorypack_fields",
                "entityEventScope": "specified-entity",
                "triggerTarget": "SPECIFY_ENTITY",
                "targetEntity": {
                    "logicId": logic_id,
                    "slotId": 0,
                    "useSlotId": False,
                },
                "targetEntityParam": {
                    "idRef": -1,
                    "paramSource": 0,
                    "path": None,
                },
                "targetEntityListPresent": False,
                "targetEntityListOutputPresent": False,
                "serverExchange": False,
                "serializedMissionOrQuestId": False,
            },
        }

    @classmethod
    def _custom_owner(cls) -> dict:
        return {
            "status": "exact_serialized_control_path",
            "nativeHeaderMappingId": LEVELSCRIPT_NATIVE_HEADER_MAPPING_ID,
            "headerName": "ScriptEvent_OnCustomEvent",
            "headerLocalId": 59,
            "pathLocalIds": [60, 70],
            "eventDetail": {
                "type": "ScriptEvent_OnCustomEvent",
                "payloadSchemaStatus": "exact_current_build_memorypack_fields",
                "eventKey": "fixture_event",
            },
        }

    @classmethod
    def _native_inputs(cls) -> tuple[dict[str, list[dict]], list[dict]]:
        listener_owner = cls._custom_owner()
        direct = {
            "levelId": cls.SCENE_ID,
            "scriptId": cls.SCRIPT_ID,
            "sourceFile": "LevelScriptData/map_fixture/21000000001.json",
            "recordOffset": 100,
            "localId": 77,
            "nativeEventOwners": [
                cls._interactive_owner(cls.LOGIC_ID_B, 74)
            ],
        }
        custom = {
            "levelId": cls.SCENE_ID,
            "scriptId": cls.SCRIPT_ID,
            "sourceFile": "LevelScriptData/map_fixture/21000000001.json",
            "recordOffset": 200,
            "localId": 70,
            "nativeEventOwners": [listener_owner],
        }
        route = {
            "status": "exact_serialized_local_producer",
            "storyKey": cls.STORY_KEY,
            "levelId": cls.SCENE_ID,
            "producerAction": "RaiseCustomScriptEvent",
            "receiverMode": "current_script",
            "serverExchange": False,
            "serializedMissionOrQuestId": False,
            "producerControlPaths": [
                cls._interactive_owner(cls.LOGIC_ID_A, 85)
            ],
            "listenerRoutes": [{
                "listenerScriptId": cls.SCRIPT_ID,
                "listenerSourceFile": custom["sourceFile"],
                "listenerPlaybackActionOffset": custom["recordOffset"],
                "listenerEventOwner": listener_owner,
            }],
        }
        return {cls.STORY_KEY: [custom, direct]}, [route]

    @classmethod
    def _write_fixture(
        cls,
        root: Path,
        *,
        quest_id_b: str | None = None,
    ) -> dict[str, Path]:
        mission_root = root / "MissionRuntimeAsset"
        level_root = root / "Streaming" / "LevelData"
        mirror_root = root / "Persistent" / "LevelData"
        registry_path = root / "GameplayConfig" / "WorldEntityRegistry.json"
        for path in (
            mission_root,
            level_root / cls.SCENE_ID,
            mirror_root / cls.SCENE_ID,
            registry_path.parent,
        ):
            path.mkdir(parents=True, exist_ok=True)
        quests = {cls.QUEST_ID: {"questId": cls.QUEST_ID}}
        if quest_id_b and quest_id_b != cls.QUEST_ID:
            quests[quest_id_b] = {"questId": quest_id_b}
        (mission_root / f"{cls.MISSION_ID}.json").write_text(
            json.dumps({
                "missionId": cls.MISSION_ID,
                "questDic": quests,
            }),
            encoding="utf-8",
        )
        leveldata, _bounds = cls._leveldata(quest_id_b=quest_id_b)
        level_path = level_root / cls.SCENE_ID / "fixture.json"
        mirror_path = mirror_root / cls.SCENE_ID / "fixture.json"
        level_path.write_bytes(leveldata)
        mirror_path.write_bytes(leveldata)
        registry_path.write_text(json.dumps({
            "worldEntityBriefInfos": {
                str(cls.LOGIC_ID_A): {
                    "entityType": 32,
                    "detailId": cls.DETAIL_ID_A,
                },
                str(cls.LOGIC_ID_B): {
                    "entityType": 32,
                    "detailId": cls.DETAIL_ID_B,
                },
            },
        }), encoding="utf-8")
        return {
            "mission_runtime_root": mission_root,
            "leveldata_root": level_root,
            "leveldata_mirror_root": mirror_root,
            "world_entity_registry_path": registry_path,
            "level_path": level_path,
            "mirror_path": mirror_path,
        }

    def test_parser_requires_complete_equal_completed_progress_lock(self):
        data, bounds = self._leveldata()
        parsed = parse_level_interactive_quest_progress_lock(
            data,
            *bounds[0],
        )
        self.assertIsNotNone(parsed)
        self.assertEqual(self.QUEST_ID, parsed["questId"])
        self.assertEqual("SimpleConditionCheckQuestState", parsed[
            "progressLockConditionType"
        ])
        self.assertEqual("QuestState.Completed", parsed["compareTargetName"])
        self.assertEqual(bounds[0][1], parsed["recordEndOffset"])

        bad_record = self._record(
            self.LOGIC_ID_A,
            self.DETAIL_ID_A,
            self.QUEST_ID,
            compare_target=2,
        )
        self.assertIsNone(
            parse_level_interactive_quest_progress_lock(
                bad_record,
                0,
                len(bad_record),
            )
        )

    def test_builder_accepts_direct_and_custom_routes_only_when_all_agree(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self._write_fixture(Path(temp_dir))
            native, routes = self._native_inputs()
            rows = build_quest_progress_locked_interactive_story_contexts(
                native,
                routes,
                {self.MISSION_ID},
                **{
                    key: value
                    for key, value in paths.items()
                    if key in {
                        "mission_runtime_root",
                        "leveldata_root",
                        "leveldata_mirror_root",
                        "world_entity_registry_path",
                    }
                },
            )
            self.assertEqual(1, len(rows))
            row = rows[0]
            self.assertEqual(self.MISSION_ID, row["missionId"])
            self.assertEqual(self.QUEST_ID, row["questId"])
            self.assertEqual(self.STORY_KEY, row["storyKey"])
            self.assertEqual(2, row["occurrenceCount"])
            self.assertEqual(
                [str(self.LOGIC_ID_A), str(self.LOGIC_ID_B)],
                row["entityLogicIds"],
            )
            self.assertTrue(row["storyBinding"])
            self.assertFalse(row["ownership"])
            self.assertFalse(row["questActivation"])
            self.assertFalse(row["questPlayback"])
            self.assertFalse(row["questCompletion"])
            self.assertFalse(row["serverExchange"])
            self.assertFalse(row["clientRequest"])
            self.assertFalse(row["expectedClientReply"])

    def test_builder_fails_closed_on_mirror_route_registry_and_quest_conflicts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = self._write_fixture(root)
            native, routes = self._native_inputs()
            kwargs = {
                key: value
                for key, value in paths.items()
                if key in {
                    "mission_runtime_root",
                    "leveldata_root",
                    "leveldata_mirror_root",
                    "world_entity_registry_path",
                }
            }

            paths["mirror_path"].write_bytes(b"mismatch")
            self.assertEqual([], build_quest_progress_locked_interactive_story_contexts(
                native, routes, {self.MISSION_ID}, **kwargs
            ))

            paths = self._write_fixture(root)
            routes[0]["producerControlPaths"] = []
            self.assertEqual([], build_quest_progress_locked_interactive_story_contexts(
                native, routes, {self.MISSION_ID}, **kwargs
            ))

            native, routes = self._native_inputs()
            registry = json.loads(paths["world_entity_registry_path"].read_text(
                encoding="utf-8"
            ))
            registry["worldEntityBriefInfos"][str(self.LOGIC_ID_A)][
                "detailId"
            ] = "int_wrong"
            paths["world_entity_registry_path"].write_text(
                json.dumps(registry),
                encoding="utf-8",
            )
            self.assertEqual([], build_quest_progress_locked_interactive_story_contexts(
                native, routes, {self.MISSION_ID}, **kwargs
            ))

            conflicting_quest = f"{self.MISSION_ID}_q#2"
            paths = self._write_fixture(root, quest_id_b=conflicting_quest)
            kwargs = {
                key: value
                for key, value in paths.items()
                if key in {
                    "mission_runtime_root",
                    "leveldata_root",
                    "leveldata_mirror_root",
                    "world_entity_registry_path",
                }
            }
            self.assertEqual([], build_quest_progress_locked_interactive_story_contexts(
                native, routes, {self.MISSION_ID}, **kwargs
            ))


if __name__ == "__main__":
    unittest.main()
