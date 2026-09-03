from __future__ import annotations

import struct
import unittest


from scripts.story_builder.spawner_binary import (
    SPAWNER_ENEMY_LIBRARY_ITEM_MEMBER_COUNT,
    SPAWNER_GROUP_MEMBER_COUNT,
    SPAWNER_WAVE_MEMBER_COUNT,
    SpawnerEnemyLibraryDecodeError,
    SpawnerWaveDecodeError,
    decode_spawner_enemy_library,
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


def spawner_fixture(second_mode: int = 2, second_map_key: int = 5) -> bytes:
    wave_map = (
        struct.pack("<I", 2)
        + wave_entry(
            4,
            wave_id=186,
            wave_key="w4",
            mode=2,
            kill_count=5,
            target_key="2",
            groups=[group_entry(1, group_id=1, group_key="401", mode=0)],
        )
        + wave_entry(
            second_map_key,
            wave_id=193,
            wave_key="elite",
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


def enemy_buff(buff_id: str) -> bytes:
    blackboard = bytes([4]) + mp_string("ratio") + b"\x00" + struct.pack("<f", 5.0) + mp_string(None)
    return bytes([2]) + struct.pack("<I", 1) + blackboard + mp_string(buff_id)


def enemy_library_item(
    *,
    enemy_id: str,
    template_id: str | None,
    event_id: str,
    effect_id: str,
    pre_warn_time: float,
) -> bytes:
    return (
        bytes([SPAWNER_ENEMY_LIBRARY_ITEM_MEMBER_COUNT, 0xFF])
        + struct.pack("<I", 1)
        + enemy_buff("buff_common_born")
        + mp_string(template_id)
        + mp_string(enemy_id)
        + struct.pack("<i", 20)
        + b"\x01"
        + mp_string("2C065AAE")
        + mp_string("EnemyAIConfig/Test")
        + struct.pack("<i", 2)
        + mp_string(event_id)
        + struct.pack("<ffff", 0.0, 0.5, 0.0, 1.0)
        + mp_string(effect_id)
        + struct.pack("<f", pre_warn_time)
    )


def enemy_library_fixture() -> bytes:
    rows = [
        enemy_library_item(
            enemy_id="eny_0018_lbtough_train",
            template_id=None,
            event_id="au_interactive_monsterspawn_white_2s",
            effect_id="P_monsterspawn_summon_02_2s",
            pre_warn_time=2.0,
        ),
        enemy_library_item(
            enemy_id="eny_test_template",
            template_id="eny_template_override",
            event_id="au_int_electric_fence_hit",
            effect_id="P_monsterspawn_summon_01_1s",
            pre_warn_time=1.25,
        ),
    ]
    return b"\x05" + mp_string("sc_base01_dg001_9900010011") + struct.pack("<I", len(rows)) + b"".join(rows) + b"opaque-tail"


class SpawnerBinaryTests(unittest.TestCase):
    def test_decodes_exact_mc13_enemy_library_prefix(self) -> None:
        fixture = enemy_library_fixture()
        decoded = decode_spawner_enemy_library(fixture)

        self.assertEqual(decoded["configId"], "sc_base01_dg001_9900010011")
        self.assertEqual(decoded["enemyLibraryCount"], 2)
        self.assertEqual(decoded["enemyLibraryEndOffset"], len(fixture) - len(b"opaque-tail"))
        first = decoded["enemyLibrary"][0]
        self.assertIsNone(first["bornBehaviorData"])
        self.assertEqual(first["bornBuffList"][0]["buffId"], "buff_common_born")
        self.assertEqual(first["bornBuffList"][0]["blackboards"][0]["key"], "ratio")
        self.assertEqual(first["bornTemplateId"], "")
        self.assertEqual(first["enemyId"], "eny_0018_lbtough_train")
        self.assertEqual(first["preWarnAudioEventKey"], "au_interactive_monsterspawn_white_2s")
        self.assertEqual(first["preWarnEffectKey"], "P_monsterspawn_summon_02_2s")
        self.assertEqual(first["preWarnTime"], 2.0)
        self.assertEqual(first["preWarnEffectFixedRotation"], [0.0, 0.5, 0.0, 1.0])
        self.assertEqual(decoded["enemyLibrary"][1]["bornTemplateId"], "eny_template_override")

    def test_rejects_changed_enemy_item_member_count(self) -> None:
        fixture = enemy_library_fixture()
        item_offset = 1 + len(mp_string("sc_base01_dg001_9900010011")) + 4
        changed = fixture[:item_offset] + b"\x0c" + fixture[item_offset + 1:]
        with self.assertRaises(SpawnerEnemyLibraryDecodeError):
            decode_spawner_enemy_library(changed)

    def test_rejects_unverified_non_null_born_behavior(self) -> None:
        fixture = enemy_library_fixture()
        item_offset = 1 + len(mp_string("sc_base01_dg001_9900010011")) + 4
        behavior_offset = item_offset + 1
        changed = fixture[:behavior_offset] + b"\x12" + fixture[behavior_offset + 1:]
        with self.assertRaisesRegex(SpawnerEnemyLibraryDecodeError, "no current authored fixture"):
            decode_spawner_enemy_library(changed)

    def test_decodes_unique_complete_wave_and_group_maps(self) -> None:
        result = decode_spawner_wave_map(spawner_fixture())

        self.assertEqual(result["configId"], "sc_map_test_1004")
        self.assertEqual(result["waveCount"], 2)
        self.assertEqual([row["mapKey"] for row in result["waves"]], [4, 5])
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
            [("w4", 2, 5, "2"), ("elite", 2, 5, "4")],
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
                ("w4", [(1, "401", 0, "")]),
                ("elite", [(1, "501", 0, ""), (2, "502", 2, "501")]),
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

    def test_rejects_duplicate_wave_map_keys(self) -> None:
        with self.assertRaisesRegex(SpawnerWaveDecodeError, "duplicate wave map key"):
            decode_spawner_wave_map(spawner_fixture(second_map_key=4))

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
