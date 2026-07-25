from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from story_builder.spawner_binary import (
    SPAWNER_GROUP_MEMBER_COUNT,
    SPAWNER_WAVE_MEMBER_COUNT,
    SpawnerWaveDecodeError,
    decode_spawner_wave_map,
)


def mp_string(value: str | None) -> bytes:
    if value is None:
        return struct.pack("<I", 0xFFFFFFFF)
    encoded = value.encode("utf-8")
    return struct.pack("<I", len(encoded)) + encoded


def group_entry(
    map_key: int,
    *,
    group_id: int,
    group_key: str | None,
    mode: int,
    kill_count: int = 0,
    target_key: str | None = None,
    opaque_action_map: bytes = b"\x00\x00\x00\x00",
) -> bytes:
    tail = (
        struct.pack("<fii", 0.0, 0, group_id)
        + mp_string(group_key)
        + struct.pack("<iii", 0, mode, kill_count)
        + mp_string(target_key)
        + b"\x00\x00"
        + struct.pack("<f", 1.0)
    )
    return (
        struct.pack("<i", map_key)
        + bytes([SPAWNER_GROUP_MEMBER_COUNT])
        + opaque_action_map
        + tail
    )


def wave_entry(
    map_key: int,
    *,
    wave_id: int,
    wave_key: str,
    mode: int,
    kill_count: int,
    target_key: str | None,
    groups: list[bytes],
) -> bytes:
    tail = (
        b"\x00\x00\x00"
        + struct.pack("<f", 1.0)
        + struct.pack("<i", wave_id)
        + mp_string(wave_key)
        + struct.pack("<ii", mode, kill_count)
        + mp_string(target_key)
    )
    return (
        struct.pack("<i", map_key)
        + bytes([SPAWNER_WAVE_MEMBER_COUNT])
        + struct.pack("<f", 10.0)
        + struct.pack("<I", len(groups))
        + b"".join(groups)
        + tail
    )


def spawner_fixture(second_mode: int = 2) -> bytes:
    wave_map = (
        struct.pack("<I", 2)
        + wave_entry(
            4,
            wave_id=186,
            wave_key="4",
            mode=2,
            kill_count=5,
            target_key="2",
            groups=[group_entry(1, group_id=1, group_key="401", mode=0)],
        )
        + wave_entry(
            5,
            wave_id=193,
            wave_key="5",
            mode=second_mode,
            kill_count=5,
            target_key="4",
            groups=[
                group_entry(1, group_id=2, group_key="501", mode=0),
                group_entry(
                    2,
                    group_id=3,
                    group_key="502",
                    mode=2,
                    kill_count=1,
                    target_key="501",
                ),
            ],
        )
    )
    return b"\x05" + mp_string("sc_map_test_1004") + b"opaque-prefix" + wave_map


class SpawnerBinaryTests(unittest.TestCase):
    def test_decodes_unique_complete_wave_and_group_maps(self) -> None:
        result = decode_spawner_wave_map(spawner_fixture())

        self.assertEqual(result["configId"], "sc_map_test_1004")
        self.assertEqual(result["waveCount"], 2)
        self.assertEqual(
            [
                (
                    row["waveKey"],
                    row["waveMode"],
                    row["waveModeKillCount"],
                    row["waveModeTargetKey"],
                )
                for row in result["waves"]
            ],
            [("4", 2, 5, "2"), ("5", 2, 5, "4")],
        )
        self.assertEqual(
            [
                (
                    row["waveKey"],
                    [
                        (
                            group["mapKey"],
                            group["groupKey"],
                            group["groupMode"],
                            group["groupModeTargetKey"],
                        )
                        for group in row["groups"]
                    ],
                )
                for row in result["waves"]
            ],
            [
                ("4", [(1, "401", 0, "")]),
                ("5", [(1, "501", 0, ""), (2, "502", 2, "501")]),
            ],
        )

    def test_decodes_null_key_sentinel_group(self) -> None:
        fixture = (
            b"\x05"
            + mp_string("sc_map_test_1004")
            + b"opaque-prefix"
            + struct.pack("<I", 1)
            + wave_entry(
                9,
                wave_id=46,
                wave_key="9",
                mode=1,
                kill_count=1,
                target_key="8",
                groups=[
                    group_entry(
                        1,
                        group_id=43,
                        group_key=None,
                        mode=1,
                    )
                ],
            )
        )
        group = decode_spawner_wave_map(fixture)["waves"][0]["groups"][0]
        self.assertEqual(group["mapKey"], 1)
        self.assertEqual(group["groupKey"], "")

    def test_rejects_changed_wave_mode_shape(self) -> None:
        with self.assertRaises(SpawnerWaveDecodeError):
            decode_spawner_wave_map(spawner_fixture(second_mode=7))

    def test_rejects_changed_group_member_shape(self) -> None:
        fixture = spawner_fixture()
        marker = struct.pack("<i", 1) + bytes([SPAWNER_GROUP_MEMBER_COUNT])
        offset = fixture.index(marker)
        changed = (
            fixture[:offset + 4]
            + bytes([SPAWNER_GROUP_MEMBER_COUNT + 1])
            + fixture[offset + 5:]
        )
        with self.assertRaises(SpawnerWaveDecodeError):
            decode_spawner_wave_map(changed)


if __name__ == "__main__":
    unittest.main()
