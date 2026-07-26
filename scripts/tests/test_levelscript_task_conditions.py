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


def u64_param(value: int) -> bytes:
    return b"\x04" + struct.pack("<Q", value) + PARAM_TAIL


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
        self.assertEqual("exact_declared_task_count", rows[0]["taskMapBoundaryStatus"])
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

    def test_decoder_rejects_partial_or_unknown_condition_maps(self) -> None:
        valid = levelscript_blob(task_entry())
        self.assertEqual(
            [],
            decode_levelscript_task_conditions(valid[:-20], SCRIPT_ID),
        )
        unknown = bytearray(valid)
        unknown[unknown.index(b"\x67\x07")] = 0x66
        self.assertEqual(
            [],
            decode_levelscript_task_conditions(bytes(unknown), SCRIPT_ID),
        )


if __name__ == "__main__":
    unittest.main()
