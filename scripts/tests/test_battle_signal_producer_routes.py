from __future__ import annotations

import struct
import tempfile
import unittest
from pathlib import Path

from scripts.story_builder.ability_binary import (
    BATTLE_SIGNAL_PAYLOAD_MAPPING_ID,
    BATTLE_SIGNAL_PRODUCER_MAPPING_ID,
    build_battle_signal_producer_index,
    decode_battle_signal_action,
    match_battle_signal_story_producers,
)
from scripts.story_builder.levelscript_binary import (
    LEVELSCRIPT_NATIVE_HEADER_MAPPING_ID,
)


def memorypack_string(value: str | None) -> bytes:
    if value is None:
        return struct.pack("<I", 0xFFFFFFFF)
    encoded = value.encode("utf-8")
    return struct.pack("<I", len(encoded)) + encoded


def battle_signal_action(
    signal: str,
    value: float,
    *,
    signal_blackboard_key: str | None = None,
    is_enable: bool = True,
) -> bytes:
    return b"".join((
        b"\xfa\x34\x01\x06",
        b"\x01" if is_enable else b"\x00",
        struct.pack("<iii", 0, 0, -1),
        b"\x03",
        memorypack_string(None),
        b"\x00",
        struct.pack("<f", value),
        b"\x03",
        memorypack_string(signal_blackboard_key),
        b"\x01" if signal_blackboard_key else b"\x00",
        memorypack_string(signal),
    ))


class BattleSignalProducerRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        build_battle_signal_producer_index.cache_clear()

    def tearDown(self) -> None:
        build_battle_signal_producer_index.cache_clear()

    def test_exact_current_action_layout_decodes(self) -> None:
        data = b"prefix" + battle_signal_action("fixture_signal", 1.0) + b"tail"
        decoded = decode_battle_signal_action(data, 6)
        self.assertEqual(decoded["actionUnionTag"], "0x0134")
        self.assertEqual(decoded["serializedMemberCount"], 6)
        self.assertEqual(decoded["producerMappingId"], BATTLE_SIGNAL_PRODUCER_MAPPING_ID)
        self.assertEqual(decoded["signalId"]["value"], "fixture_signal")
        self.assertFalse(decoded["signalId"]["useBlackboardKey"])
        self.assertEqual(decoded["doubleValue"]["value"], 1.0)
        stale_tag = bytearray(data)
        stale_tag[7:9] = b"\x1f\x01"
        with self.assertRaisesRegex(ValueError, "tag/member-count"):
            decode_battle_signal_action(bytes(stale_tag), 6)
        wrong_count = bytearray(data)
        wrong_count[9] = 5
        with self.assertRaisesRegex(ValueError, "tag/member-count"):
            decode_battle_signal_action(bytes(wrong_count), 6)

    def test_index_rejects_dynamic_signal_and_matches_exact_receiver(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            skill_root = root / "SkillData"
            buff_root = root / "BuffData"
            skill_root.mkdir()
            buff_root.mkdir()
            (skill_root / "skill_fixture.json").write_bytes(
                b"envelope" + battle_signal_action("fixture_signal", 0.0)
            )
            (buff_root / "buff_dynamic.json").write_bytes(
                battle_signal_action(
                    "ignored_literal",
                    2.0,
                    signal_blackboard_key="dynamic_signal",
                )
            )
            (buff_root / "buff_disabled.json").write_bytes(
                battle_signal_action(
                    "disabled_signal",
                    3.0,
                    is_enable=False,
                )
            )

            producer_index = build_battle_signal_producer_index(root)
            self.assertEqual(list(producer_index), ["fixture_signal"])
            producer = producer_index["fixture_signal"][0]
            self.assertEqual(producer["producerAssetId"], "skill_fixture")
            self.assertEqual(producer["producerDomain"], "SkillData")
            self.assertFalse(producer["serverExchange"])
            self.assertFalse(producer["storyBinding"])

            occurrence = {
                "levelId": "map_fixture",
                "scriptId": "70000000001",
                "sourceFile": "fixture/70000000001.json",
                "actionName": "PlayRadioAction",
                "nativeEventOwners": [{
                    "status": "exact_serialized_control_path",
                    "headerName": "LevelEvent_OnBattleSignal",
                    "headerUnionTag": "0x004c",
                    "headerSerializedMemberCount": 16,
                    "headerLocalId": 9,
                    "nativeHeaderMappingId": LEVELSCRIPT_NATIVE_HEADER_MAPPING_ID,
                    "eventDetail": {
                        "type": "LevelEvent_OnBattleSignal",
                        "signalId": "fixture_signal",
                        "payloadSchemaStatus": (
                            "exact_current_build_memorypack_fields"
                        ),
                        "payloadSchemaMappingId": (
                            BATTLE_SIGNAL_PAYLOAD_MAPPING_ID
                        ),
                    },
                }],
            }
            routes = match_battle_signal_story_producers(
                "radio_fixture_1",
                [occurrence],
                producer_index,
            )
            self.assertEqual(len(routes), 1)
            self.assertEqual(routes[0]["storyKey"], "radio_fixture_1")
            self.assertEqual(routes[0]["listenerHeaderLocalId"], 9)
            self.assertEqual(
                routes[0]["relation"],
                "ability_battle_signal_local_causality",
            )
            self.assertEqual(routes[0]["missionOwnerStatus"], "unresolved")
            self.assertFalse(routes[0]["serverExchange"])

            occurrence["nativeEventOwners"][0]["headerUnionTag"] = "0x004d"
            self.assertEqual(
                match_battle_signal_story_producers(
                    "radio_fixture_1",
                    [occurrence],
                    producer_index,
                ),
                [],
            )


if __name__ == "__main__":
    unittest.main()
