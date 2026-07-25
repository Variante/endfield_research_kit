from __future__ import annotations

import struct
import unittest

from scripts.story_builder.language_bundle import (
    match_play3d_npc_tracking_context,
)
from scripts.story_builder.levelscript_binary import (
    decode_levelscript_record_payload,
)


SENTINEL = bytes.fromhex(
    "ff ff ff ff 00 00 00 00 ff ff ff ff"
)


def scalar(value: bytes) -> bytes:
    return b"\x04" + value + SENTINEL


def boolean(value: bool) -> bytes:
    return b"\x04" + bytes([int(value)]) + SENTINEL


def string(value: str) -> bytes:
    raw = value.encode("utf-8")
    return b"\x04" + struct.pack("<I", len(raw)) + raw + SENTINEL


def play3d_payload(*, radio_id: str, proxy_id: str, use_proxy: bool) -> bytes:
    return b"".join((
        scalar(struct.pack("<I", 36)),
        boolean(False),
        b"\x04" + b"\x03" + b"\x00" * 13 + SENTINEL,
        boolean(True),
        scalar(struct.pack("<i", -1)),
        boolean(False),
        string(proxy_id),
        boolean(False),
        string(radio_id),
        scalar(struct.pack("<f", 1.0)),
        boolean(use_proxy),
        scalar(struct.pack("<f", 1.0)),
    ))


class Play3DNpcContextTests(unittest.TestCase):
    def test_exact_native_payload_decodes_target_fields_to_eof(self) -> None:
        payload = play3d_payload(
            radio_id="radio_e3m3_1",
            proxy_id="dengen_map01_e3m301",
            use_proxy=True,
        )
        record = {
            "code": 0x034A,
            "kind": 0x14,
            "unionTag": 0x034A,
            "serializedMemberCount": 0x14,
            "payloadStart": 0,
        }
        decoded = decode_levelscript_record_payload(
            payload,
            record,
            next_start=len(payload),
            action_map_role="actionList#1 root",
        )["play3DRadio"]
        self.assertEqual("radio_e3m3_1", decoded["radioId"])
        self.assertEqual("dengen_map01_e3m301", decoded["npcProxyId"])
        self.assertTrue(decoded["useNpcProxy"])
        self.assertEqual(len(payload), decoded["consumedBytes"])

        framed = decode_levelscript_record_payload(
            payload + b"\x00\x00\x00\x00",
            record,
            next_start=len(payload) + 4,
            action_map_role="actionList#1 root",
        )
        self.assertNotIn("play3DRadio", framed)

    def test_context_requires_true_flag_same_scene_and_unique_mission(self) -> None:
        occurrence = {
            "actionName": "Play3DRadio",
            "levelId": "map01_lv007",
            "play3DRadio": {
                "payloadShape": "play3d-radio-native-12-field-exact-eof",
                "radioId": "radio_e3m3_1",
                "npcProxyId": "dengen_map01_e3m301",
                "useNpcProxy": True,
            },
        }
        consumers = {
            "dengen_map01_e3m301": [{
                "missionId": "e3m3",
                "questId": "e3m3_q#16",
                "scene": "map01_lv007",
            }],
        }
        matched = match_play3d_npc_tracking_context(
            "radio_e3m3_1",
            occurrence,
            consumers,
        )
        self.assertEqual("e3m3", matched["missionId"])
        self.assertEqual("e3m3_q#16", matched["consumers"][0]["questId"])

        occurrence["play3DRadio"]["useNpcProxy"] = False
        self.assertEqual(
            {},
            match_play3d_npc_tracking_context(
                "radio_e3m3_1", occurrence, consumers
            ),
        )
        occurrence["play3DRadio"]["useNpcProxy"] = True
        consumers["dengen_map01_e3m301"].append({
            "missionId": "other",
            "questId": "other_q#1",
            "scene": "map01_lv007",
        })
        self.assertEqual(
            {},
            match_play3d_npc_tracking_context(
                "radio_e3m3_1", occurrence, consumers
            ),
        )


if __name__ == "__main__":
    unittest.main()
