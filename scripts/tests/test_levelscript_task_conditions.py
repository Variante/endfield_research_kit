from __future__ import annotations

import struct
import unittest

from scripts.story_builder.levelscript_binary import (
    LEVELSCRIPT_TASK_CONDITION_MAPPING_ID,
    decode_levelscript_task_conditions,
)


PARAM_TAIL = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"
SCRIPT_ID = 23_300_090_001


def compact_string(value: str) -> bytes:
    encoded = value.encode("ascii")
    return struct.pack("<I", len(encoded)) + encoded


def i32_param(value: int) -> bytes:
    return b"\x04" + struct.pack("<i", value) + PARAM_TAIL


def bool_param(value: bool) -> bytes:
    return b"\x04" + bytes([int(value)]) + PARAM_TAIL


def u64_param(value: int) -> bytes:
    return b"\x04" + struct.pack("<Q", value) + PARAM_TAIL


def levelscript_ptr_param(script_id: int) -> bytes:
    return b"\x04" + struct.pack("<QQ", script_id, 0) + PARAM_TAIL


def levelscript_task_ptr_param(task_key: str) -> bytes:
    return b"\x04\x01" + compact_string(task_key) + PARAM_TAIL


def string_param(value: str | None, *, source: int = 0) -> bytes:
    if value is None:
        encoded = struct.pack("<i", -1)
    else:
        raw = value.encode("ascii")
        encoded = struct.pack("<i", len(raw)) + raw
    return (
        b"\x04"
        + encoded
        + struct.pack("<iii", -1, source, -1)
    )


def entity_list_param(logic_ids: list[int]) -> bytes:
    return (
        b"\x04"
        + struct.pack("<I", len(logic_ids))
        + b"".join(
            b"\x03" + struct.pack("<QI?", logic_id, 0, False)
            for logic_id in logic_ids
        )
        + PARAM_TAIL
    )


def common(condition_key: str) -> bytes:
    return (
        struct.pack("<i", 1)
        + compact_string(condition_key)
        + b"\x00\x01"
    )


def condition_entry(
    condition_key: str,
    condition: bytes,
    *,
    objective: int = 0,
) -> bytes:
    return (
        compact_string(condition_key)
        + b"\x03"
        + condition
        + b"\x01"
        + struct.pack("<i", objective)
    )


def task_entry() -> bytes:
    mission_key = "11111111"
    monster_key = "22222222"
    talk_key = "33333333"
    area_key = "44444444"
    conditions = [
        condition_entry(
            mission_key,
            b"\x67\x07"
            + common(mission_key)
            + i32_param(0)
            + string_param("e7m4")
            + i32_param(3),
        ),
        condition_entry(
            monster_key,
            b"\x6a\x09"
            + common(monster_key)
            + i32_param(0)
            + entity_list_param([21_000_000_001])
            + string_param(None, source=1000)
            + u64_param(1)
            + b"\x00",
            objective=1,
        ),
        condition_entry(
            talk_key,
            b"\x9f\x06"
            + common(talk_key)
            + string_param("dlg_fixture")
            + i32_param(2),
            objective=2,
        ),
        condition_entry(
            area_key,
            b"\xfa\x32\x01\x06"
            + common(area_key)
            + string_param("data_002")
            + string_param(None, source=1000),
            objective=3,
        ),
    ]
    return (
        compact_string("abcdef12")
        + b"\x04\x01"
        + struct.pack("<I", len(conditions))
        + b"".join(conditions)
        + b"\x00"
        + struct.pack("<i", 0)
    )


def factory_task_entry() -> bytes:
    specs = [
        (0x0017, 8, [string_param("a"), string_param("b"), i32_param(2), string_param("level")]),
        (0x0018, 8, [string_param("a"), string_param("b"), i32_param(2), string_param(None, source=1000)]),
        (0x0019, 8, [string_param("end"), string_param("start"), bool_param(True), string_param("level")]),
        (0x001A, 9, [bool_param(True), i32_param(1), string_param("a"), string_param("b"), string_param("level")]),
        (0x001B, 9, [string_param("building"), i32_param(10), string_param("area"), i32_param(3), string_param("map")]),
        (0x0035, 8, [i32_param(2), string_param("instance"), bool_param(True), string_param("scene")]),
        (0x0038, 9, [i32_param(3), i32_param(8), string_param("level"), u64_param(42), string_param("water")]),
        (0x0084, 6, [string_param("repair"), string_param("level")]),
        (0x008D, 9, [i32_param(0), string_param("level"), levelscript_ptr_param(SCRIPT_ID), i32_param(2), levelscript_task_ptr_param("1234abcd")]),
        (0x00D0, 6, [string_param("building"), bool_param(True)]),
        (0x0108, 7, [i32_param(3), string_param("item"), i32_param(4)]),
        (0x010B, 8, [i32_param(3), i32_param(5), string_param("instance"), string_param("level")]),
        (0x010D, 8, [i32_param(3), i32_param(5), string_param("building"), string_param("level")]),
        (0x010E, 9, [i32_param(3), i32_param(5), string_param("instance"), string_param("item"), string_param("level")]),
        (0x010F, 8, [i32_param(3), i32_param(5), string_param("building"), string_param("level")]),
        (0x0112, 6, [i32_param(12), string_param("level")]),
        (0x0113, 8, [i32_param(3), i32_param(5), string_param("formula"), string_param("level")]),
        (0x0114, 8, [i32_param(3), i32_param(5), string_param("item"), string_param("level")]),
        (0x0115, 8, [i32_param(3), i32_param(5), string_param("item"), string_param("level")]),
        (0x0127, 7, [i32_param(3), i32_param(5), string_param("item")]),
        (0x012D, 8, [struct.pack("<i", -1), i32_param(3), string_param("item"), i32_param(5)]),
        (0x012E, 8, [struct.pack("<i", -1), i32_param(3), string_param("item"), i32_param(5)]),
    ]
    conditions = []
    for index, (tag, member_count, fields) in enumerate(specs):
        key = f"{index + 1:08x}"
        union = (
            bytes([tag, member_count])
            if tag < 0xFA
            else b"\xfa" + struct.pack("<H", tag) + bytes([member_count])
        )
        conditions.append(
            condition_entry(key, union + common(key) + b"".join(fields))
        )
    conditions.append(condition_entry("eeeeeeee", b"\xff"))
    return (
        compact_string("fedcba98")
        + b"\x04\x01"
        + struct.pack("<I", len(conditions))
        + b"".join(conditions)
        + b"\x00"
        + struct.pack("<i", 0)
    )


def levelscript_blob(entry: bytes) -> bytes:
    return (
        b"\x1b"
        + b"\x00" * 7
        + struct.pack("<Q", SCRIPT_ID)
        + struct.pack("<I", 0xFFFFFFFF)
        + struct.pack("<I", 1)
        + struct.pack("<I", 1)
        + entry
        + struct.pack("<I", 0)
    )


class LevelScriptTaskConditionTests(unittest.TestCase):
    def test_complete_task_map_decodes_named_root_conditions(self) -> None:
        rows = decode_levelscript_task_conditions(
            levelscript_blob(task_entry()),
            SCRIPT_ID,
        )

        self.assertEqual(1, len(rows))
        self.assertEqual(
            "exact_trigger_volumes_offset",
            rows[0]["taskMapBoundaryStatus"],
        )
        self.assertEqual(1, len(rows[0]["tasks"]))
        task = rows[0]["tasks"][0]
        self.assertTrue(task["canBeTracked"])
        self.assertEqual(4, task["conditionDictCount"])
        conditions = [row["condition"] for row in task["conditions"]]
        self.assertEqual(
            [
                "CheckMissionState",
                "CheckMonsterKilled",
                "CheckTalkOptionFinish",
                "TaskReachDestination",
            ],
            [row["type"] for row in conditions],
        )
        self.assertEqual("e7m4", conditions[0]["missionId"]["value"])
        self.assertEqual(
            "21000000001",
            conditions[1]["enemyIds"]["values"][0]["logicId"],
        )
        self.assertEqual("dlg_fixture", conditions[2]["dialogId"]["value"])
        self.assertEqual("memorypack-fa-u16", conditions[3]["conditionUnionTagEncoding"])
        self.assertTrue(
            all(
                row["nativeMappingId"] == LEVELSCRIPT_TASK_CONDITION_MAPPING_ID
                for row in conditions
            )
        )

    def test_complete_factory_condition_family_decodes_by_formatter_layout(self) -> None:
        rows = decode_levelscript_task_conditions(
            levelscript_blob(factory_task_entry()),
            SCRIPT_ID,
        )

        self.assertEqual(1, len(rows))
        conditions = [
            row["condition"]
            for row in rows[0]["tasks"][0]["conditions"]
        ]
        self.assertEqual(
            [
                "CheckBuildingConnected",
                "CheckBuildingConnectedAsMA2SB",
                "CheckBuildingConnectedExist",
                "CheckBuildingConnectedSpecify",
                "CheckBuildingStateInArea",
                "CheckFacBuildingState",
                "CheckFluidVolume",
                "CheckRepairBuilding",
                "CheckScriptTaskStateEqual",
                "OnBuildingPanelOpen",
                "DepotHasItem",
                "FacBattleBuildingCurEnergy",
                "FacBuildingCountInScene",
                "FacBuildingFluidContainerHasItem",
                "FacBuildingProducingCountInScene",
                "FacProducePowerReach",
                "FacProducingFormulaCountInScene",
                "FacStatisticItemGen",
                "FacStatisticItemGenRate",
                "HasItemCount",
                "PlayerHasItem",
                "PlayerHasItemInItemBag",
                "NullGameCondition",
            ],
            [row["type"] for row in conditions],
        )
        self.assertEqual("a", conditions[0]["facBuildingIdA"]["value"])
        self.assertEqual("area", conditions[4]["targetAreaId"]["value"])
        self.assertEqual("42", conditions[6]["volumeId"]["value"])
        self.assertEqual("formula", conditions[16]["facFormulaId"]["value"])
        self.assertEqual(
            "memorypack-null",
            conditions[-1]["conditionUnionTagEncoding"],
        )

    def test_factory_condition_member_count_drift_fails_closed(self) -> None:
        valid = bytearray(levelscript_blob(factory_task_entry()))
        condition_offset = valid.index(b"\x18\x08")
        valid[condition_offset + 1] = 7
        diagnostics: list[dict[str, object]] = []
        self.assertEqual(
            [],
            decode_levelscript_task_conditions(
                bytes(valid),
                SCRIPT_ID,
                diagnostics=diagnostics,
            ),
        )
        self.assertEqual("supportedConditionPayloadLayout", diagnostics[0]["gate"])
        self.assertEqual("0x0018", diagnostics[0]["conditionUnionTag"])
        self.assertEqual(7, diagnostics[0]["serializedMemberCount"])
        self.assertEqual(8, diagnostics[0]["expectedSerializedMemberCount"])

    def test_decoder_rejects_partial_or_unknown_condition_maps(self) -> None:
        valid = levelscript_blob(task_entry())
        self.assertEqual(
            [],
            decode_levelscript_task_conditions(valid[:-20], SCRIPT_ID),
        )
        unknown = bytearray(valid)
        unknown[unknown.index(b"\x67\x07")] = 0x66
        diagnostics: list[dict[str, object]] = []
        self.assertEqual(
            [],
            decode_levelscript_task_conditions(
                bytes(unknown),
                SCRIPT_ID,
                diagnostics=diagnostics,
            ),
        )
        self.assertEqual("supportedConditionUnionTag", diagnostics[0]["gate"])
        self.assertEqual("0x0066", diagnostics[0]["conditionUnionTag"])


if __name__ == "__main__":
    unittest.main()
