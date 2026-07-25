from __future__ import annotations

import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.story_builder import level_bindings
from scripts.story_builder.level_bindings import (
    build_levelscript_task_mission_state_story_dependencies,
)
from scripts.story_builder.levelscript_binary import (
    LEVELSCRIPT_TASK_MISSION_STATE_MAPPING_ID,
    decode_levelscript_task_mission_state_dependencies,
)


PARAM_TAIL = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"


def compact_string(value: str) -> bytes:
    encoded = value.encode("ascii")
    return struct.pack("<I", len(encoded)) + encoded


def constant_i32(value: int) -> bytes:
    return b"\x04" + struct.pack("<i", value) + PARAM_TAIL


def constant_string(value: str) -> bytes:
    encoded = value.encode("ascii")
    return b"\x04" + struct.pack("<i", len(encoded)) + encoded + PARAM_TAIL


def task_entry(
    *,
    task_key: str = "cf5a771c",
    condition_key: str = "cb696abe",
    mission_id: str = "e7m4",
    comparer: int = 0,
    state: int = 3,
) -> bytes:
    condition = (
        b"\x67\x07"
        + struct.pack("<i", 1)
        + compact_string(condition_key)
        + b"\x00\x01"
        + constant_i32(comparer)
        + constant_string(mission_id)
        + constant_i32(state)
    )
    return (
        compact_string(task_key)
        + b"\x04\x00"
        + struct.pack("<I", 1)
        + compact_string(condition_key)
        + b"\x03"
        + condition
        + b"\x01"
        + struct.pack("<i", 0)
        + b"\x00"
        + struct.pack("<i", 0)
    )


def levelscript_blob(entry: bytes, *, script_id: int = 23_300_090_001) -> bytes:
    return (
        b"\x1b"
        + b"\x00" * 7
        + struct.pack("<Q", script_id)
        + struct.pack("<I", 0xFFFFFFFF)
        + struct.pack("<I", 1)
        + struct.pack("<I", 1)
        + entry
        + struct.pack("<I", 0)
    )


class LevelScriptTaskMissionStateDependencyTests(unittest.TestCase):
    def test_exact_task_map_check_mission_state_decodes(self) -> None:
        rows = decode_levelscript_task_mission_state_dependencies(
            levelscript_blob(task_entry()),
            23_300_090_001,
        )

        self.assertEqual(1, len(rows))
        self.assertEqual("cf5a771c", rows[0]["taskKey"])
        self.assertEqual("cb696abe", rows[0]["conditionKey"])
        self.assertEqual("e7m4", rows[0]["condition"]["missionId"])
        self.assertEqual("Equal", rows[0]["condition"]["comparerName"])
        self.assertEqual("Completed", rows[0]["condition"]["targetMissionStateName"])
        self.assertEqual(
            LEVELSCRIPT_TASK_MISSION_STATE_MAPPING_ID,
            rows[0]["condition"]["nativeMappingId"],
        )

    def test_decoder_rejects_wrong_script_tag_and_dynamic_param_shape(self) -> None:
        valid = bytearray(levelscript_blob(task_entry()))
        self.assertEqual(
            [],
            decode_levelscript_task_mission_state_dependencies(
                bytes(valid),
                23_300_090_002,
            ),
        )
        union_offset = valid.index(b"\x67\x07")
        valid[union_offset] = 0x66
        self.assertEqual(
            [],
            decode_levelscript_task_mission_state_dependencies(
                bytes(valid),
                23_300_090_001,
            ),
        )

        dynamic = bytearray(levelscript_blob(task_entry()))
        comparer_offset = dynamic.index(b"\x04" + struct.pack("<i", 0) + PARAM_TAIL)
        dynamic[comparer_offset] = 0x02
        self.assertEqual(
            [],
            decode_levelscript_task_mission_state_dependencies(
                bytes(dynamic),
                23_300_090_001,
            ),
        )

    def test_builder_emits_dependency_only_for_equal_completed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.bin"
            source.write_bytes(levelscript_blob(task_entry()))
            playback = {
                "black_map02_lv003liuhan_1": [{
                    "levelId": "map02_lv003",
                    "scriptId": "23300090001",
                    "sourceFile": "source.bin",
                    "actionName": "NarrativeBlackScreenAction",
                    "localId": 21,
                    "recordOffset": 0x752,
                }],
            }
            with patch.object(level_bindings, "ROOT", root):
                rows = build_levelscript_task_mission_state_story_dependencies(
                    playback,
                )

        self.assertEqual(1, len(rows))
        self.assertEqual("e7m4 Equal Completed", rows[0]["predicate"])
        self.assertTrue(rows[0]["sameScriptOnly"])
        self.assertFalse(rows[0]["controlPathLinked"])
        self.assertFalse(rows[0]["storyBinding"])
        self.assertFalse(rows[0]["serverExchange"])

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "source.bin").write_bytes(
                levelscript_blob(task_entry(state=2))
            )
            with patch.object(level_bindings, "ROOT", root):
                self.assertEqual(
                    [],
                    build_levelscript_task_mission_state_story_dependencies(
                        playback,
                    ),
                )


if __name__ == "__main__":
    unittest.main()
