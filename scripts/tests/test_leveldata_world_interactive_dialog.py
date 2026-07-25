import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.story_builder import level_bindings
from scripts.story_builder.level_bindings import (
    build_entity_tracking_world_interactive_dialog_contexts,
    parse_level_interactive_world_dialog_context,
)


class LevelDataWorldInteractiveDialogTests(unittest.TestCase):
    MISSION_ID = "mission_fixture"
    QUEST_ID = "mission_fixture_q#1"
    STORY_KEY = "dlg_mission_fixture_1"
    SCENE_ID = "map_fixture"
    LOCAL_LOGIC_ID = 70023
    GLOBAL_LOGIC_ID = 2100070023
    DETAIL_ID = "int_narrative_common_empty"

    @staticmethod
    def _mp_string(value: str | None) -> bytes:
        if value is None:
            return (-1).to_bytes(4, "little", signed=True)
        encoded = value.encode("utf-8")
        return len(encoded).to_bytes(4, "little", signed=True) + encoded

    @classmethod
    def _param_entry(
        cls,
        key: str,
        value_type: int,
        value_bits: int,
        string_value: str | None,
    ) -> bytes:
        return (
            b"\x02"
            + cls._mp_string(key)
            + b"\x02"
            + value_type.to_bytes(4, "little", signed=True)
            + (1).to_bytes(4, "little", signed=True)
            + b"\x02"
            + value_bits.to_bytes(8, "little", signed=False)
            + cls._mp_string(string_value)
        )

    @classmethod
    def _record(
        cls,
        *,
        narrative_type: int = 1,
        extra_narrative_key: bool = False,
        mission_id: str | None = None,
        story_key: str | None = None,
        global_logic_id: int | None = None,
        detail_id: str | None = None,
    ) -> bytes:
        mission_id = cls.MISSION_ID if mission_id is None else mission_id
        story_key = cls.STORY_KEY if story_key is None else story_key
        global_logic_id = (
            cls.GLOBAL_LOGIC_ID
            if global_logic_id is None
            else global_logic_id
        )
        detail_id = cls.DETAIL_ID if detail_id is None else detail_id
        narrative_entries = [
            cls._param_entry(
                "fx_change_mission_id", 7, 0, mission_id
            ),
            cls._param_entry("type", 3, narrative_type, None),
            cls._param_entry("type_id", 7, 0, story_key),
        ]
        if extra_narrative_key:
            narrative_entries.append(cls._param_entry("extra", 7, 0, "bad"))
        component_properties = (
            (3).to_bytes(4, "little", signed=True)
            + (0).to_bytes(4, "little", signed=True)
            + (1).to_bytes(4, "little", signed=True)
            + cls._param_entry("shape", 3, 1, None)
            + (61).to_bytes(4, "little", signed=True)
            + (0).to_bytes(4, "little", signed=True)
            + (94).to_bytes(4, "little", signed=True)
            + len(narrative_entries).to_bytes(4, "little", signed=True)
            + b"".join(narrative_entries)
        )
        return (
            b"\x19"
            + (b"\x00" * 24)
            + cls._mp_string(detail_id)
            + (32).to_bytes(4, "little", signed=True)
            + b"\x00\x00"
            + global_logic_id.to_bytes(8, "little", signed=False)
            + (b"\x00" * 38)
            + component_properties
            + (b"\xff" * 16)
        )

    @classmethod
    def _leveldata_records(cls, records: list[bytes]) -> bytes:
        prefix = (
            b"\x2bfixture"
            + (len(records) + 1).to_bytes(4, "little", signed=True)
        )
        tail = b"\x19" + (b"\x00" * 24) + cls._mp_string("int_tail")
        return prefix + b"".join(records) + tail

    @classmethod
    def _leveldata(cls, **record_kwargs) -> tuple[bytes, int, int]:
        record = cls._record(**record_kwargs)
        data = cls._leveldata_records([record])
        start = len(b"\x2bfixture") + 4
        return data, start, start + len(record)

    @classmethod
    def _interactive_table(cls) -> bytes:
        template_path = (
            "Data/Json/Interactive/InteractiveData/"
            "data_int_narrative_common.json"
        )
        return (
            b"\x02"
            + (1).to_bytes(4, "little", signed=True)
            + cls._mp_string("int_narrative_common")
            + cls._mp_string(template_path)
            + (1).to_bytes(4, "little", signed=True)
            + cls._mp_string(cls.DETAIL_ID)
            + b"\x01"
            + cls._mp_string("int_narrative_common")
        )

    @classmethod
    def _write_fixture(cls, root: Path) -> dict[str, Path]:
        mra_root = root / "MissionRuntimeAsset"
        leveldata_root = root / "Streaming" / "LevelData"
        leveldata_mirror_root = root / "Persistent" / "LevelData"
        interactive_root = root / "Streaming" / "Interactive"
        interactive_mirror_root = root / "Persistent" / "Interactive"
        gameplay_root = root / "GameplayConfig"
        for path in (
            mra_root,
            leveldata_root / cls.SCENE_ID,
            leveldata_mirror_root / cls.SCENE_ID,
            interactive_root / "InteractiveData",
            interactive_mirror_root / "InteractiveData",
            gameplay_root,
        ):
            path.mkdir(parents=True, exist_ok=True)

        mra_path = mra_root / f"{cls.MISSION_ID}.json"
        mra_path.write_text(
            json.dumps({
                "missionId": cls.MISSION_ID,
                "questDic": {
                    cls.QUEST_ID: {
                        "questId": cls.QUEST_ID,
                        "objectiveList": [{
                            "trackingInfoList": [{
                                "$type": (
                                    "Beyond.Gameplay.EntityTrackingInfo, "
                                    "Gameplay.Beyond"
                                ),
                                "sceneId": cls.SCENE_ID,
                                "trackScriptEntity": False,
                                "entityLogicId": cls.LOCAL_LOGIC_ID,
                                "scriptId": 0,
                                "entitySlotId": 0,
                            }],
                        }],
                    },
                },
            }),
            encoding="utf-8",
        )
        leveldata, _start, _end = cls._leveldata()
        level_path = leveldata_root / cls.SCENE_ID / "opaque.json"
        level_mirror_path = (
            leveldata_mirror_root / cls.SCENE_ID / "opaque.json"
        )
        level_path.write_bytes(leveldata)
        level_mirror_path.write_bytes(leveldata)

        table = cls._interactive_table()
        table_path = interactive_root / "InteractiveTable.json"
        table_mirror_path = interactive_mirror_root / "InteractiveTable.json"
        table_path.write_bytes(table)
        table_mirror_path.write_bytes(table)
        template_path = (
            interactive_root
            / "InteractiveData"
            / "data_int_narrative_common.json"
        )
        template_mirror_path = (
            interactive_mirror_root
            / "InteractiveData"
            / "data_int_narrative_common.json"
        )
        template_path.write_bytes(b"verified-template")
        template_mirror_path.write_bytes(b"verified-template")

        registry_path = gameplay_root / "WorldEntityRegistry.json"
        registry_path.write_text(
            json.dumps({
                "worldEntityBriefInfos": {
                    str(cls.GLOBAL_LOGIC_ID): {
                        "entityType": 32,
                        "detailId": cls.DETAIL_ID,
                    },
                },
            }),
            encoding="utf-8",
        )
        return {
            "mission_runtime_root": mra_root,
            "leveldata_root": leveldata_root,
            "leveldata_mirror_root": leveldata_mirror_root,
            "world_entity_registry_path": registry_path,
            "interactive_table_path": table_path,
            "interactive_table_mirror_path": table_mirror_path,
            "level_path": level_path,
            "level_mirror_path": level_mirror_path,
            "template_mirror_path": template_mirror_path,
            "mra_path": mra_path,
        }

    def test_parser_requires_exact_component_94_heterogeneous_dialog_map(self):
        data, start, end = self._leveldata()
        parsed = parse_level_interactive_world_dialog_context(data, start, end)
        self.assertIsNotNone(parsed)
        self.assertEqual(self.MISSION_ID, parsed["missionStateId"])
        self.assertEqual(self.STORY_KEY, parsed["storyKey"])
        self.assertEqual(94, parsed["componentPropertiesKey"])
        self.assertEqual(3, parsed["componentPropertyMapEntryCount"])
        self.assertEqual("Dialog", parsed["narrativeTypeName"])

        wrong_type, wrong_start, wrong_end = self._leveldata(narrative_type=2)
        self.assertIsNone(
            parse_level_interactive_world_dialog_context(
                wrong_type, wrong_start, wrong_end
            )
        )
        extra_key, extra_start, extra_end = self._leveldata(
            extra_narrative_key=True
        )
        self.assertIsNone(
            parse_level_interactive_world_dialog_context(
                extra_key, extra_start, extra_end
            )
        )

    def test_builder_returns_exact_original_data_join(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self._write_fixture(Path(temp_dir))
            rows = build_entity_tracking_world_interactive_dialog_contexts(
                {self.STORY_KEY},
                {self.MISSION_ID},
                **{
                    key: value
                    for key, value in paths.items()
                    if key
                    in {
                        "mission_runtime_root",
                        "leveldata_root",
                        "leveldata_mirror_root",
                        "world_entity_registry_path",
                        "interactive_table_path",
                        "interactive_table_mirror_path",
                    }
                },
            )
            self.assertEqual(1, len(rows))
            row = rows[0]
            self.assertEqual(self.QUEST_ID, row["questId"])
            self.assertEqual(self.STORY_KEY, row["storyKey"])
            self.assertEqual(str(self.GLOBAL_LOGIC_ID), row["worldEntityGlobalLogicId"])
            self.assertEqual("int_narrative_common", row["entityTemplateId"])
            self.assertFalse(row["ownership"])
            self.assertFalse(row["questPlayback"])
            self.assertFalse(row["serverExchange"])

    def test_builder_parses_one_leveldata_blob_once_for_two_ids_in_scene(self):
        second_story_key = "dlg_mission_fixture_2"
        second_local_logic_id = self.LOCAL_LOGIC_ID + 1
        second_global_logic_id = self.GLOBAL_LOGIC_ID + 1
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self._write_fixture(Path(temp_dir))
            payload = json.loads(paths["mra_path"].read_text(encoding="utf-8"))
            tracking_rows = payload["questDic"][self.QUEST_ID][
                "objectiveList"
            ][0]["trackingInfoList"]
            second_tracking = dict(tracking_rows[0])
            second_tracking["entityLogicId"] = second_local_logic_id
            tracking_rows.append(second_tracking)
            paths["mra_path"].write_text(
                json.dumps(payload), encoding="utf-8"
            )

            registry = json.loads(
                paths["world_entity_registry_path"].read_text(
                    encoding="utf-8"
                )
            )
            registry["worldEntityBriefInfos"][str(second_global_logic_id)] = {
                "entityType": 32,
                "detailId": self.DETAIL_ID,
            }
            paths["world_entity_registry_path"].write_text(
                json.dumps(registry), encoding="utf-8"
            )
            leveldata = self._leveldata_records([
                self._record(),
                self._record(
                    story_key=second_story_key,
                    global_logic_id=second_global_logic_id,
                ),
            ])
            paths["level_path"].write_bytes(leveldata)
            paths["level_mirror_path"].write_bytes(leveldata)
            kwargs = {
                key: value
                for key, value in paths.items()
                if key
                in {
                    "mission_runtime_root",
                    "leveldata_root",
                    "leveldata_mirror_root",
                    "world_entity_registry_path",
                    "interactive_table_path",
                    "interactive_table_mirror_path",
                }
            }

            with (
                patch.object(
                    level_bindings,
                    "_level_interactive_data_list_frames",
                    wraps=level_bindings._level_interactive_data_list_frames,
                ) as frame_parser,
                patch.object(
                    level_bindings,
                    "parse_level_interactive_world_dialog_context",
                    wraps=(
                        level_bindings.parse_level_interactive_world_dialog_context
                    ),
                ) as record_parser,
            ):
                rows = build_entity_tracking_world_interactive_dialog_contexts(
                    {self.STORY_KEY, second_story_key},
                    {self.MISSION_ID},
                    **kwargs,
                )

            self.assertEqual(
                {self.STORY_KEY, second_story_key},
                {row["storyKey"] for row in rows},
            )
            frame_parser.assert_called_once()
            self.assertEqual(2, record_parser.call_count)

    def test_builder_rejects_duplicate_leveldata_candidates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self._write_fixture(Path(temp_dir))
            leveldata = self._leveldata_records([
                self._record(),
                self._record(),
            ])
            paths["level_path"].write_bytes(leveldata)
            paths["level_mirror_path"].write_bytes(leveldata)
            kwargs = {
                key: value
                for key, value in paths.items()
                if key
                in {
                    "mission_runtime_root",
                    "leveldata_root",
                    "leveldata_mirror_root",
                    "world_entity_registry_path",
                    "interactive_table_path",
                    "interactive_table_mirror_path",
                }
            }

            self.assertEqual(
                [],
                build_entity_tracking_world_interactive_dialog_contexts(
                    {self.STORY_KEY}, {self.MISSION_ID}, **kwargs
                ),
            )

    def test_builder_fails_closed_on_leveldata_mirror_mismatch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = self._write_fixture(root)
            kwargs = {
                key: value
                for key, value in paths.items()
                if key
                in {
                    "mission_runtime_root",
                    "leveldata_root",
                    "leveldata_mirror_root",
                    "world_entity_registry_path",
                    "interactive_table_path",
                    "interactive_table_mirror_path",
                }
            }
            paths["level_mirror_path"].write_bytes(b"mismatch")
            self.assertEqual(
                [],
                build_entity_tracking_world_interactive_dialog_contexts(
                    {self.STORY_KEY}, {self.MISSION_ID}, **kwargs
                ),
            )

    def test_builder_fails_closed_on_missing_leveldata_mirror(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self._write_fixture(Path(temp_dir))
            kwargs = {
                key: value
                for key, value in paths.items()
                if key
                in {
                    "mission_runtime_root",
                    "leveldata_root",
                    "leveldata_mirror_root",
                    "world_entity_registry_path",
                    "interactive_table_path",
                    "interactive_table_mirror_path",
                }
            }
            paths["level_mirror_path"].unlink()
            self.assertEqual(
                [],
                build_entity_tracking_world_interactive_dialog_contexts(
                    {self.STORY_KEY}, {self.MISSION_ID}, **kwargs
                ),
            )

    def test_builder_keeps_leveldata_candidates_isolated_by_scene(self):
        second_scene_id = "map_fixture_other"
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self._write_fixture(Path(temp_dir))
            payload = json.loads(paths["mra_path"].read_text(encoding="utf-8"))
            tracking_rows = payload["questDic"][self.QUEST_ID][
                "objectiveList"
            ][0]["trackingInfoList"]
            second_tracking = dict(tracking_rows[0])
            second_tracking["sceneId"] = second_scene_id
            tracking_rows.append(second_tracking)
            paths["mra_path"].write_text(
                json.dumps(payload), encoding="utf-8"
            )

            second_path = (
                paths["leveldata_root"] / second_scene_id / "opaque.json"
            )
            second_mirror_path = (
                paths["leveldata_mirror_root"]
                / second_scene_id
                / "opaque.json"
            )
            second_path.parent.mkdir(parents=True)
            second_mirror_path.parent.mkdir(parents=True)
            leveldata = paths["level_path"].read_bytes()
            second_path.write_bytes(leveldata)
            second_mirror_path.write_bytes(leveldata)
            kwargs = {
                key: value
                for key, value in paths.items()
                if key
                in {
                    "mission_runtime_root",
                    "leveldata_root",
                    "leveldata_mirror_root",
                    "world_entity_registry_path",
                    "interactive_table_path",
                    "interactive_table_mirror_path",
                }
            }

            with patch.object(
                level_bindings,
                "_level_interactive_data_list_frames",
                wraps=level_bindings._level_interactive_data_list_frames,
            ) as frame_parser:
                rows = build_entity_tracking_world_interactive_dialog_contexts(
                    {self.STORY_KEY}, {self.MISSION_ID}, **kwargs
                )

            self.assertEqual(
                {self.SCENE_ID, second_scene_id},
                {row["levelId"] for row in rows},
            )
            self.assertEqual(2, frame_parser.call_count)

    def test_builder_requires_unique_tracking_mission_story_template_and_global_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = self._write_fixture(root)
            kwargs = {
                key: value
                for key, value in paths.items()
                if key
                in {
                    "mission_runtime_root",
                    "leveldata_root",
                    "leveldata_mirror_root",
                    "world_entity_registry_path",
                    "interactive_table_path",
                    "interactive_table_mirror_path",
                }
            }
            self.assertEqual(
                [],
                build_entity_tracking_world_interactive_dialog_contexts(
                    {"dlg_other"}, {self.MISSION_ID}, **kwargs
                ),
            )
            self.assertEqual(
                [],
                build_entity_tracking_world_interactive_dialog_contexts(
                    {self.STORY_KEY}, {"mission_other"}, **kwargs
                ),
            )

            paths = self._write_fixture(root)
            table = paths["interactive_table_path"].read_bytes()
            old_template = b"int_narrative_common"
            bad_template = b"int_narrative_badbad"
            self.assertEqual(len(old_template), len(bad_template))
            offset = table.rfind(old_template)
            table = (
                table[:offset]
                + bad_template
                + table[offset + len(old_template) :]
            )
            paths["interactive_table_path"].write_bytes(table)
            paths["interactive_table_mirror_path"].write_bytes(table)
            self.assertEqual(
                [],
                build_entity_tracking_world_interactive_dialog_contexts(
                    {self.STORY_KEY}, {self.MISSION_ID}, **kwargs
                ),
            )

            paths = self._write_fixture(root)
            registry = json.loads(
                paths["world_entity_registry_path"].read_text(
                    encoding="utf-8"
                )
            )
            brief = registry["worldEntityBriefInfos"].pop(
                str(self.GLOBAL_LOGIC_ID)
            )
            registry["worldEntityBriefInfos"][
                str(self.GLOBAL_LOGIC_ID + 1_000_000_000)
            ] = brief
            paths["world_entity_registry_path"].write_text(
                json.dumps(registry), encoding="utf-8"
            )
            self.assertEqual(
                [],
                build_entity_tracking_world_interactive_dialog_contexts(
                    {self.STORY_KEY}, {self.MISSION_ID}, **kwargs
                ),
            )

            paths = self._write_fixture(root)
            payload = json.loads(paths["mra_path"].read_text(encoding="utf-8"))
            duplicate = json.loads(
                json.dumps(payload["questDic"][self.QUEST_ID])
            )
            duplicate["questId"] = f"{self.MISSION_ID}_q#2"
            payload["questDic"][duplicate["questId"]] = duplicate
            paths["mra_path"].write_text(json.dumps(payload), encoding="utf-8")
            self.assertEqual(
                [],
                build_entity_tracking_world_interactive_dialog_contexts(
                    {self.STORY_KEY}, {self.MISSION_ID}, **kwargs
                ),
            )


if __name__ == "__main__":
    unittest.main()
