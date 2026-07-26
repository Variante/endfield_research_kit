from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.story_builder import level_bindings
from scripts.story_builder.level_bindings import (
    _find_exact_bytes_offsets,
    _parse_leveldata_mission_host_name,
    build_leveldata_airwall_mission_radio_contexts,
    build_level_function_area_radio_trigger_story_contexts,
    build_level_interactive_narrative_mission_story_contexts,
    build_leveldata_authoritative_scope_script_host_index,
    build_leveldata_mission_area_script_host_index,
    build_leveldata_world_entity_quest_script_context,
    classify_world_entity_story_receiver_owner,
    build_npc_proxy_segment_script_host_index,
    find_levelscript_brief_data_entries,
    parse_leveldata_levelscript_brief_dictionary,
    parse_leveldata_airwall_groups,
    parse_level_function_area_radio_trigger_zone_entry,
    parse_level_interactive_narrative_mission_context,
    parse_levelscript_brief_data_entry,
)


class LevelDataScriptHostTests(unittest.TestCase):
    def test_brief_dictionary_decode_is_reused_for_identical_binary_inputs(self) -> None:
        data = self._brief_dictionary([101, 202])
        level_bindings._parse_leveldata_levelscript_brief_dictionary_cached.cache_clear()
        first = parse_leveldata_levelscript_brief_dictionary(data, {202, 101})
        second = parse_leveldata_levelscript_brief_dictionary(data, {101, 202})

        self.assertIs(first, second)
        self.assertEqual([101, 202], sorted(first))
        self.assertEqual(1, level_bindings._parse_leveldata_levelscript_brief_dictionary_cached.cache_info().misses)

    def test_world_entity_story_receiver_owner_whitelist(self):
        common = {
            "status": "exact_serialized_control_path",
            "nativeHeaderMappingId": (
                "gameassembly-2026-07-11-cr-0x18b9217d0-actionheader"
            ),
        }
        schema = {
            "payloadSchemaStatus": "exact_current_build_memorypack_fields",
            "payloadSchemaMappingId": (
                "gameassembly-2026-07-17-memorypack-native-event-fields"
            ),
        }
        stage = {
            **common,
            "headerName": "ScriptEvent_OnScriptStageChanged",
            "headerUnionTag": "0x00c9",
            "headerSerializedMemberCount": 18,
            "eventDetail": {
                **schema,
                "type": "ScriptEvent_OnScriptStageChanged",
                "scriptEventScope": "owning-level-script",
                "triggerTarget": "SELF",
                "targetScriptPresent": False,
                "newStageFilterPresent": True,
                "newStageFilter": 3,
                "newStageOutputPresent": False,
            },
        }
        self.assertEqual(
            "ScriptEvent_OnScriptStageChanged",
            classify_world_entity_story_receiver_owner(stage),
        )
        invalid = json.loads(json.dumps(stage))
        invalid["eventDetail"]["newStageOutputPresent"] = True
        self.assertEqual("", classify_world_entity_story_receiver_owner(invalid))

    @staticmethod
    def _mp_string(value: str) -> bytes:
        encoded = value.encode("utf-8")
        return len(encoded).to_bytes(4, "little", signed=True) + encoded

    @classmethod
    def _radio_trigger_zone_entry(
        cls,
        *,
        hide_after: str = "mission_after",
        hide_before: str = "mission_before",
        hide_complete: str = "",
        radio_id: str = "radio_test_1",
        list_count: int = 1,
    ) -> tuple[bytes, int]:
        prefix = b"\x2bfixture" + list_count.to_bytes(4, "little", signed=True)
        entry = (
            b"\x09\x07"
            + cls._mp_string(hide_after)
            + cls._mp_string(hide_before)
            + cls._mp_string(hide_complete)
            + cls._mp_string("")
            + cls._mp_string(radio_id)
            + (35).to_bytes(8, "little")
            + b"\x01"
        )
        return prefix + entry, len(prefix)

    @classmethod
    def _param_string_entry(cls, key: str, value: str) -> bytes:
        return (
            b"\x02"
            + cls._mp_string(key)
            + level_bindings._LEVEL_INTERACTIVE_PARAM_STRING_PREFIX
            + cls._mp_string(value)
        )

    @classmethod
    def _airwall_mission_check(
        cls,
        check_id: str,
        *,
        is_quest: bool,
        detail_state: int = 3,
        is_same: bool = True,
    ) -> bytes:
        return (
            b"\x04"
            + detail_state.to_bytes(4, "little", signed=True)
            + cls._mp_string(check_id)
            + bytes((is_quest, is_same))
        )

    @classmethod
    def _airwall_leveldata(
        cls,
        *,
        mission_id: str = "mission_test",
        quest_id: str = "mission_test_q#1",
        radio_id: str = "radio_test_airwall",
        group_members: int = 8,
    ) -> bytes:
        down = cls._airwall_mission_check(
            mission_id,
            is_quest=False,
            detail_state=4,
            is_same=False,
        )
        rise = cls._airwall_mission_check(
            quest_id,
            is_quest=True,
            detail_state=3,
            is_same=True,
        )
        mission_total = (
            b"\x04"
            + (1).to_bytes(4, "little", signed=True)
            + down
            + b"\x00"
            + b"\x01"
            + (1).to_bytes(4, "little", signed=True)
            + rise
        )
        group = (
            bytes((group_members,))
            + b"\x02"
            + (b"\x00" * 24)
            + b"\x02"
            + (1).to_bytes(4, "little", signed=True)
            + mission_total
            + b"\x01"
            + (123).to_bytes(8, "little")
            + (-1).to_bytes(4, "little", signed=True)
            + cls._mp_string(radio_id)
            + (456).to_bytes(8, "little")
            + (0xF0000001).to_bytes(4, "little")
        )
        return b"\x2b" + (1).to_bytes(4, "little", signed=True) + group

    @classmethod
    def _interactive_record(
        cls,
        entity_detail_id: str,
        *,
        mission_id: str = "",
        popup_id: str = "",
    ) -> bytes:
        payload = b"\x19" + (b"\x00" * 24) + cls._mp_string(entity_detail_id)
        if mission_id and popup_id:
            payload += (
                (2).to_bytes(4, "little", signed=True)
                + cls._param_string_entry("fx_change_mission_id", mission_id)
                + cls._param_string_entry("type_id", popup_id)
            )
        return payload + b"\xff\x00\x00\x00"

    @staticmethod
    def _brief_entry(
        script_id: int,
        world_entity_ids: list[int] | None = None,
    ) -> bytes:
        world_refs = (
            (-1).to_bytes(4, "little", signed=True)
            if world_entity_ids is None
            else (
                len(world_entity_ids).to_bytes(4, "little", signed=True)
                + b"".join(
                    entity_id.to_bytes(8, "little")
                    for entity_id in world_entity_ids
                )
            )
        )
        return (
            script_id.to_bytes(8, "little")
            + b"\x08"
            + (script_id + 100).to_bytes(8, "little")
            + (1).to_bytes(4, "little", signed=True)
            + (2).to_bytes(4, "little", signed=True)
            + (0).to_bytes(8, "little")
            + (0).to_bytes(4, "little", signed=True)
            + (0).to_bytes(4, "little", signed=True)
            + world_refs
            + script_id.to_bytes(8, "little")
        )

    @classmethod
    def _brief_dictionary(cls, script_ids: list[int]) -> bytes:
        return (
            b"\x2bfixture"
            + len(script_ids).to_bytes(4, "little", signed=True)
            + b"".join(cls._brief_entry(script_id) for script_id in script_ids)
        )

    def test_exact_level_and_runtime_token_are_required(self) -> None:
        missions = {"sm2l8m1", "c27m4d5"}
        self.assertEqual(
            "sm2l8m1",
            _parse_leveldata_mission_host_name(
                "map02_lv008_lv_data_sub_sm2l8m1.json",
                "map02_lv008",
                missions,
            ),
        )
        self.assertEqual(
            "c27m4d5",
            _parse_leveldata_mission_host_name(
                "map02_lv003_lv_data_sub_mission_c27m4d5_v1d2d0.json",
                "map02_lv003",
                missions,
            ),
        )
        self.assertEqual(
            "",
            _parse_leveldata_mission_host_name(
                "map02_lv008_lv_data_sub_sm2l8m1.json",
                "map02_lv003",
                missions,
            ),
        )
        self.assertEqual(
            "",
            _parse_leveldata_mission_host_name(
                "map02_lv008_lv_data_sub_not_a_runtime.json",
                "map02_lv008",
                missions,
            ),
        )

    def test_exact_u64_pattern_offsets_preserve_every_occurrence(self) -> None:
        needle = (23100180015).to_bytes(8, "little")
        blob = b"abc" + needle + b"xyz" + needle
        self.assertEqual([3, 14], _find_exact_bytes_offsets(blob, needle))

    def test_brief_data_requires_eight_members_and_matching_final_id(self) -> None:
        script_id = 22800200005
        entry = (
            script_id.to_bytes(8, "little")
            + b"\x08"
            + (1234).to_bytes(8, "little")
            + (1).to_bytes(4, "little", signed=True)
            + (2).to_bytes(4, "little", signed=True)
            + (0).to_bytes(8, "little")
            + (0).to_bytes(4, "little", signed=True)
            + (0).to_bytes(4, "little", signed=True)
            + (-1).to_bytes(4, "little", signed=True)
            + script_id.to_bytes(8, "little")
        )
        payload = b"\x2b" + b"prefix" + entry

        parsed = parse_levelscript_brief_data_entry(
            payload,
            7,
            expected_script_id=script_id,
        )
        self.assertIsNotNone(parsed)
        self.assertEqual(str(script_id), parsed["scriptId"])
        self.assertEqual(1, parsed["levelScriptType"])
        self.assertEqual([parsed], find_levelscript_brief_data_entries(payload, script_id))

        mismatched = payload[:-8] + (script_id + 1).to_bytes(8, "little")
        self.assertIsNone(
            parse_levelscript_brief_data_entry(
                mismatched,
                7,
                expected_script_id=script_id,
            )
        )

    def test_world_entity_group_uniquely_scopes_exact_brief_data_script(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            leveldata_root = root / "LevelData"
            levelscript_root = root / "LevelScriptData"
            level_id = "map_fixture_lv001"
            target_script = 90100000001
            sibling_script = 90100000002
            (leveldata_root / level_id).mkdir(parents=True)
            (levelscript_root / level_id).mkdir(parents=True)
            for script_id in (target_script, sibling_script):
                (levelscript_root / level_id / f"{script_id}.json").write_bytes(
                    b"fixture"
                )
            payload = (
                b"\x2bfixture"
                + (2).to_bytes(4, "little", signed=True)
                + self._brief_entry(target_script, [101, 102, 103])
                + self._brief_entry(sibling_script, [999])
            )
            (leveldata_root / level_id / "opaque.json").write_bytes(payload)
            group = {
                "missionId": "mission_fixture",
                "questId": "mission_fixture_q#1",
                "groupType": "check_monster_killed_entity_set",
                "mapId": level_id,
                "entityLogicIds": [101, 102, 103],
                "sourceFile": "MissionRuntimeAsset/mission_fixture.json",
            }
            refs = [
                {
                    "missionId": "mission_fixture",
                    "questId": "mission_fixture_q#1",
                    "mapId": level_id,
                    "logicId": entity_id,
                }
                for entity_id in (101, 102, 103)
            ]
            result = build_leveldata_world_entity_quest_script_context(
                {(level_id, str(target_script))},
                [group],
                refs,
                leveldata_root=leveldata_root,
                levelscript_root=levelscript_root,
                world_entity_registry_briefs={
                    str(entity_id): {"entityType": 16, "detailId": "fixture"}
                    for entity_id in (101, 102, 103)
                },
            )
            context = result[(level_id, str(target_script))]
            self.assertEqual("unique", context["status"])
            self.assertEqual(["mission_fixture"], context["hostMissionIds"])
            self.assertEqual(
                ["101", "102", "103"],
                context["candidates"][0]["entityLogicIds"],
            )
            self.assertEqual(
                ["101", "102", "103"],
                [
                    row["entityLogicId"]
                    for row in context["candidates"][0][
                        "worldEntityRegistryBriefs"
                    ]
                ],
            )
            self.assertEqual(
                ["101", "102", "103"],
                context["candidates"][0]["levelDataHosts"][0]
                ["briefData"]["refWorldEntityIds"],
            )

            ambiguous_refs = [
                *refs,
                {
                    "missionId": "other_mission",
                    "questId": "other_mission_q#1",
                    "mapId": level_id,
                    "logicId": 101,
                },
            ]
            self.assertEqual(
                {},
                build_leveldata_world_entity_quest_script_context(
                    {(level_id, str(target_script))},
                    [group],
                    ambiguous_refs,
                    leveldata_root=leveldata_root,
                    levelscript_root=levelscript_root,
                    world_entity_registry_briefs={
                        str(entity_id): {
                            "entityType": 16,
                            "detailId": "fixture",
                        }
                        for entity_id in (101, 102, 103)
                    },
                ),
            )
            self.assertEqual(
                {},
                build_leveldata_world_entity_quest_script_context(
                    {(level_id, str(target_script))},
                    [group],
                    refs,
                    leveldata_root=leveldata_root,
                    levelscript_root=levelscript_root,
                    world_entity_registry_briefs={
                        "101": {"entityType": 16, "detailId": "fixture"},
                        "102": {"entityType": 16, "detailId": "fixture"},
                    },
                ),
            )

    def test_radio_trigger_zone_requires_typed_union_and_single_item_frame(self) -> None:
        payload, offset = self._radio_trigger_zone_entry()
        parsed = parse_level_function_area_radio_trigger_zone_entry(
            payload,
            offset,
        )
        self.assertIsNotNone(parsed)
        self.assertEqual("radio_test_1", parsed["radioId"])
        self.assertEqual("mission_before", parsed["hideBeforeMissionId"])
        self.assertEqual("35", parsed["triggerId"])
        self.assertTrue(parsed["useRadioTriggerOnce"])

        wrong_count, wrong_offset = self._radio_trigger_zone_entry(list_count=2)
        self.assertIsNone(
            parse_level_function_area_radio_trigger_zone_entry(
                wrong_count,
                wrong_offset,
            )
        )
        wrong_tag = payload[:offset] + b"\x08" + payload[offset + 1 :]
        self.assertIsNone(
            parse_level_function_area_radio_trigger_zone_entry(
                wrong_tag,
                offset,
            )
        )

    def test_radio_trigger_zone_context_retains_each_exact_mission_role(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "LevelData"
            level_dir = root / "map_test"
            level_dir.mkdir(parents=True)
            payload, _offset = self._radio_trigger_zone_entry()
            (level_dir / "opaque.json").write_bytes(payload)

            rows = build_level_function_area_radio_trigger_story_contexts(
                {"radio_test_1"},
                {"mission_after", "mission_before"},
                leveldata_root=root,
            )
            self.assertEqual(1, len(rows))
            self.assertEqual(
                ["mission_after", "mission_before"],
                rows[0]["missionStateIds"],
            )
            self.assertEqual(
                ["hideAfterMissionId"],
                rows[0]["missionStateRolesById"]["mission_after"],
            )
            self.assertEqual(
                ["hideBeforeMissionId"],
                rows[0]["missionStateRolesById"]["mission_before"],
            )
            self.assertEqual("map_test", rows[0]["levelId"])

            self.assertEqual(
                [],
                build_level_function_area_radio_trigger_story_contexts(
                    {"radio_test_1"},
                    {"mission_after"},
                    leveldata_root=root,
                ),
            )

    def test_airwall_group_decodes_exact_nested_state_predicates(self) -> None:
        rows = parse_leveldata_airwall_groups(self._airwall_leveldata())
        self.assertEqual(1, len(rows))
        row = rows[0]
        self.assertEqual("123", row["groupId"])
        self.assertEqual("456", row["scriptId"])
        self.assertEqual(0xF0000001, row["slotId"])
        self.assertEqual("radio_test_airwall", row["pushBackRadioId"])
        self.assertTrue(row["defaultOn"])
        mission_data = row["checkData"]["missionData"]
        self.assertTrue(mission_data["isRiseAny"])
        self.assertFalse(mission_data["isDownAny"])
        self.assertEqual("mission_test_q#1", mission_data["riseReason"][0]["id"])
        self.assertTrue(mission_data["riseReason"][0]["isQuest"])
        self.assertEqual("mission_test", mission_data["downReason"][0]["id"])
        self.assertFalse(mission_data["downReason"][0]["isSame"])

        malformed = self._airwall_leveldata(group_members=7)
        self.assertEqual([], parse_leveldata_airwall_groups(malformed))

    def test_airwall_context_requires_every_typed_state_check_to_resolve(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "LevelData"
            level_dir = root / "map_test"
            level_dir.mkdir(parents=True)
            (level_dir / "airwalls.json").write_bytes(
                self._airwall_leveldata()
            )
            rows = build_leveldata_airwall_mission_radio_contexts(
                {"radio_test_airwall"},
                {"mission_test"},
                {"mission_test_q#1": "mission_test"},
                leveldata_root=root,
            )
            self.assertEqual(1, len(rows))
            self.assertEqual(["mission_test"], rows[0]["missionStateIds"])
            self.assertEqual(
                {"down", "rise"},
                {
                    check["transition"]
                    for check in rows[0]["missionStateChecks"]
                },
            )
            self.assertEqual(
                {"equal", "not_equal"},
                {
                    check["comparison"]
                    for check in rows[0]["missionStateChecks"]
                },
            )
            self.assertEqual("map_test", rows[0]["levelId"])

            self.assertEqual(
                [],
                build_leveldata_airwall_mission_radio_contexts(
                    {"radio_test_airwall"},
                    {"mission_test"},
                    {},
                    leveldata_root=root,
                ),
            )

    def test_interactive_narrative_context_requires_same_counted_param_map(self) -> None:
        first = self._interactive_record(
            "int_narrative_common_empty",
            mission_id="c16m4d5",
            popup_id="rp_radio_c16m4_51",
        )
        second = self._interactive_record("int_narrative_common_news")
        prefix = b"\x2bfixture" + (2).to_bytes(4, "little", signed=True)
        payload = prefix + first + second
        start = len(prefix)
        end = start + len(first)

        parsed = parse_level_interactive_narrative_mission_context(
            payload,
            start,
            end,
        )
        self.assertIsNotNone(parsed)
        self.assertEqual("c16m4d5", parsed["missionStateId"])
        self.assertEqual("rp_radio_c16m4_51", parsed["readingPopupId"])
        self.assertEqual(2, parsed["paramMapEntryCount"])

        map_offset = parsed["paramMapOffset"]
        wrong_count = payload[:map_offset] + (1).to_bytes(4, "little") + payload[map_offset + 4 :]
        self.assertIsNone(
            parse_level_interactive_narrative_mission_context(
                wrong_count,
                start,
                end,
            )
        )

    def test_interactive_narrative_context_joins_original_popup_table(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            leveldata_root = root / "LevelData"
            level_dir = leveldata_root / "map_test"
            level_dir.mkdir(parents=True)
            first = self._interactive_record(
                "int_narrative_common_empty",
                mission_id="c16m4d5",
                popup_id="rp_radio_c16m4_51",
            )
            second = self._interactive_record("int_narrative_common_news")
            (level_dir / "opaque.json").write_bytes(
                b"\x2bfixture"
                + (2).to_bytes(4, "little", signed=True)
                + first
                + second
            )
            popup_path = root / "ReadingPopUpTable.json"
            popup_path.write_text(
                json.dumps({
                    "rp_radio_c16m4_51": {"contentId": "radio_c16m4_51"},
                }),
                encoding="utf-8",
            )
            rows = build_level_interactive_narrative_mission_story_contexts(
                {"radio_c16m4_51"},
                {"c16m4d5"},
                leveldata_root=leveldata_root,
                reading_popup_path=popup_path,
            )
            self.assertEqual(1, len(rows))
            self.assertEqual("radio_c16m4_51", rows[0]["storyKey"])
            self.assertEqual("int_narrative_common", rows[0]["entityTemplateId"])
            self.assertEqual(2, rows[0]["interactiveListCount"])

    def test_mission_area_parent_root_scopes_file_without_filename_inference(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            mra_dir = root / "MissionRuntimeAsset"
            gameplay_dir = root / "GameplayConfig"
            leveldata_dir = root / "LevelData"
            levelscript_dir = root / "LevelScriptData"
            for path in (mra_dir, gameplay_dir, leveldata_dir, levelscript_dir):
                path.mkdir(parents=True)

            areas = [
                {"missionAreaId": "unique_area", "subDataParentId": 1000},
                {"missionAreaId": "c13_area_a", "subDataParentId": 13100010000},
                {"missionAreaId": "c13_area_b", "subDataParentId": 13100010000},
                {"missionAreaId": "multi_a", "subDataParentId": 3000},
                {"missionAreaId": "multi_b", "subDataParentId": 4000},
                {"missionAreaId": "untyped_area", "subDataParentId": 5000},
            ]
            (gameplay_dir / "MissionAreaTable.json").write_text(
                json.dumps({"m_areas": areas}),
                encoding="utf-8",
            )

            def write_mra(mission_id: str, area_id: str, type_name: str) -> None:
                payload = {
                    "missionId": mission_id,
                    "questDic": {
                        f"{mission_id}_q#1": {
                            "questId": f"{mission_id}_q#1",
                            "trackingInfoList": [{
                                "$type": type_name,
                                "missionAreaId": area_id,
                            }],
                        },
                    },
                }
                (mra_dir / f"{mission_id}.json").write_text(
                    json.dumps(payload),
                    encoding="utf-8",
                )

            tracking_type = (
                "Beyond.Gameplay.MissionAreaTrackingInfo, Gameplay.Beyond"
            )
            write_mra("unique_mission", "unique_area", tracking_type)
            write_mra("c13m2", "c13_area_a", tracking_type)
            write_mra("c13m2d5", "c13_area_b", tracking_type)
            write_mra("multi_mission_a", "multi_a", tracking_type)
            write_mra("multi_mission_b", "multi_b", tracking_type)
            write_mra(
                "untyped_mission",
                "untyped_area",
                "Beyond.Gameplay.MissionAcceptMode+EnterAreaInfo, Gameplay.Beyond",
            )

            level_id = "map_test"
            (leveldata_dir / level_id).mkdir()
            (levelscript_dir / level_id).mkdir()
            dictionaries = {
                "opaque_unique.json": [1000, 1001, 1002],
                "opaque_c13_shared.json": [13100010000, 13100010001],
                "opaque_multiroot_shared.json": [3000, 3001, 4000],
                "opaque_untyped.json": [5000, 5001],
            }
            for filename, script_ids in dictionaries.items():
                (leveldata_dir / level_id / filename).write_bytes(
                    self._brief_dictionary(script_ids)
                )
                for script_id in script_ids:
                    (levelscript_dir / level_id / f"{script_id}.json").write_text(
                        "{}",
                        encoding="utf-8",
                    )

            targets = {
                (level_id, "1001"),
                (level_id, "1002"),
                (level_id, "13100010001"),
                (level_id, "3001"),
                (level_id, "5001"),
            }
            with (
                patch.object(level_bindings, "MRA_DIR", mra_dir),
                patch.object(level_bindings, "GAMEPLAY_CONFIG_DIR", gameplay_dir),
                patch.object(level_bindings, "LEVELDATA_DIR", leveldata_dir),
                patch.object(level_bindings, "LEVELSCRIPT_DIR", levelscript_dir),
            ):
                index = build_leveldata_mission_area_script_host_index(targets)

            self.assertEqual("unique", index[(level_id, "1001")]["status"])
            self.assertEqual(
                ["unique_mission"],
                index[(level_id, "1001")]["hostMissionIds"],
            )
            self.assertEqual(
                ["unique_mission"],
                index[(level_id, "1002")]["hostMissionIds"],
            )
            self.assertIn(
                "opaque_unique.json",
                index[(level_id, "1002")]["hosts"][0]["levelDataFile"],
            )

            c13 = index[(level_id, "13100010001")]
            self.assertEqual("shared", c13["status"])
            self.assertEqual(["c13m2", "c13m2d5"], c13["hostMissionIds"])

            multi_root = index[(level_id, "3001")]
            self.assertEqual("shared", multi_root["status"])
            self.assertEqual(
                ["multi_mission_a", "multi_mission_b"],
                multi_root["hostMissionIds"],
            )
            self.assertNotIn((level_id, "5001"), index)

    def test_authoritative_sibling_scope_requires_one_mission_union(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            mra_dir = root / "MissionRuntimeAsset"
            gameplay_dir = root / "GameplayConfig"
            leveldata_dir = root / "LevelData"
            levelscript_dir = root / "LevelScriptData"
            for path in (mra_dir, gameplay_dir, leveldata_dir, levelscript_dir):
                path.mkdir(parents=True)
            (gameplay_dir / "MissionAreaTable.json").write_text(
                json.dumps({"m_areas": {}}),
                encoding="utf-8",
            )
            level_id = "map_test"
            (leveldata_dir / level_id).mkdir()
            (levelscript_dir / level_id).mkdir()
            for filename, script_ids in {
                "opaque_unique.json": [1000, 1001, 1002],
                "opaque_shared.json": [2000, 2001, 2002],
            }.items():
                (leveldata_dir / level_id / filename).write_bytes(
                    self._brief_dictionary(script_ids)
                )
                for script_id in script_ids:
                    (levelscript_dir / level_id / f"{script_id}.json").write_bytes(
                        b"fixture"
                    )
            scope_refs = {
                (level_id, "1000"): [{
                    "missionId": "mission_a",
                    "questId": "mission_a_q#1",
                    "scopeKind": "typed_mission_runtime_script_condition",
                    "sourceFile": "mission_a.json",
                }],
                (level_id, "1001"): [{
                    "missionId": "mission_a",
                    "questId": "mission_a_q#2",
                    "scopeKind": "typed_entity_tracking_registry_script",
                    "sourceFile": "mission_a.json",
                }],
                (level_id, "2000"): [{
                    "missionId": "mission_a",
                    "questId": "mission_a_q#3",
                    "scopeKind": "typed_mission_runtime_script_condition",
                    "sourceFile": "mission_a.json",
                }],
                (level_id, "2001"): [{
                    "missionId": "mission_b",
                    "questId": "mission_b_q#1",
                    "scopeKind": "typed_entity_tracking_registry_script",
                    "sourceFile": "mission_b.json",
                }],
            }
            with (
                patch.object(level_bindings, "MRA_DIR", mra_dir),
                patch.object(level_bindings, "GAMEPLAY_CONFIG_DIR", gameplay_dir),
                patch.object(level_bindings, "LEVELDATA_DIR", leveldata_dir),
                patch.object(level_bindings, "LEVELSCRIPT_DIR", levelscript_dir),
            ):
                index = build_leveldata_authoritative_scope_script_host_index(
                    {(level_id, "1002"), (level_id, "2002")},
                    {"mission_a", "mission_b"},
                    scope_refs,
                )
            self.assertEqual("unique", index[(level_id, "1002")]["status"])
            self.assertEqual(
                ["mission_a"],
                index[(level_id, "1002")]["hostMissionIds"],
            )
            self.assertEqual("shared", index[(level_id, "2002")]["status"])
            self.assertEqual(
                ["mission_a", "mission_b"],
                index[(level_id, "2002")]["hostMissionIds"],
            )

    def test_npc_proxy_segment_scope_requires_exact_typed_source_agreement(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            gameplay_dir = Path(temp_dir) / "GameplayConfig"
            gameplay_dir.mkdir(parents=True)
            registry_path = gameplay_dir / "WorldEntityRegistry.json"
            proxy_ex_path = gameplay_dir / "NpcProxyExDataTable.json"
            registry_path.write_text(
                json.dumps({
                    "npcProxyBriefInfos": {
                        "1001": {
                            "proxyId": "proxy_unique",
                            "segmentIdGlobal": 1001,
                        },
                        "9999": {
                            "proxyId": "proxy_bad_key",
                            "segmentIdGlobal": 1002,
                        },
                        "1003": {
                            "proxyId": "proxy_shared",
                            "segmentIdGlobal": 1003,
                        },
                    },
                }),
                encoding="utf-8",
            )
            proxy_ex_path.write_text(
                json.dumps({
                    "data": {
                        "proxy_unique": {"missionId": "mission_a"},
                        "proxy_bad_key": {"missionId": "mission_a"},
                        "proxy_shared": [
                            {"missionId": "mission_a"},
                            {"missionId": "mission_b"},
                        ],
                    },
                }),
                encoding="utf-8",
            )
            consumers = {
                "proxy_unique": [{
                    "type": "NpcProxyTrackingInfo",
                    "missionId": "mission_a",
                    "questId": "mission_a_q#1",
                    "scene": "map_test",
                }],
                "proxy_bad_key": [{
                    "type": "NpcProxyTrackingInfo",
                    "missionId": "mission_a",
                    "questId": "mission_a_q#2",
                    "scene": "map_test",
                }],
                "proxy_shared": [{
                    "type": "NpcProxyTrackingInfo",
                    "missionId": "mission_a",
                    "questId": "mission_a_q#3",
                    "scene": "map_test",
                }],
            }
            previous_cache = level_bindings._NPC_PROXY_EX_CACHE
            try:
                level_bindings._NPC_PROXY_EX_CACHE = None
                with (
                    patch.object(level_bindings, "GAMEPLAY_CONFIG_DIR", gameplay_dir),
                    patch.object(level_bindings, "NPC_PROXY_EX_PATH", proxy_ex_path),
                ):
                    index = build_npc_proxy_segment_script_host_index(
                        {
                            ("map_test", "1001"),
                            ("wrong_scene", "1001"),
                            ("map_test", "1002"),
                            ("map_test", "1003"),
                        },
                        consumers,
                    )
            finally:
                level_bindings._NPC_PROXY_EX_CACHE = previous_cache

            unique = index[("map_test", "1001")]
            self.assertEqual("unique", unique["status"])
            self.assertEqual(["mission_a"], unique["hostMissionIds"])
            self.assertEqual("proxy_unique", unique["hosts"][0]["proxyId"])
            self.assertNotIn(("wrong_scene", "1001"), index)
            self.assertNotIn(("map_test", "1002"), index)
            self.assertEqual("shared", index[("map_test", "1003")]["status"])
            self.assertEqual(
                ["mission_a", "mission_b"],
                index[("map_test", "1003")]["hostMissionIds"],
            )


if __name__ == "__main__":
    unittest.main()
