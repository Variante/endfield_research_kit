from __future__ import annotations

import struct
import unittest

from scripts.story_builder.codecs.levelscript.proxy_patrol_checkpoint import (
    EVENT_SEMANTIC_KEY,
    decode_proxy_patrol_checkpoint_event,
)
from scripts.story_builder.levelscript_binary import decode_levelscript_record_payload


TAIL = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"


def i32_param(value: int) -> bytes:
    return b"\x04" + struct.pack("<i", value) + TAIL


def output(local_id: int, field: str) -> bytes:
    path = f"${local_id}@_{field}".encode()
    return b"\x02" + struct.pack("<ii", 0, len(path)) + path


def string_param(value: str) -> bytes:
    raw = value.encode()
    return b"\x04" + struct.pack("<i", len(raw)) + raw + TAIL


def payload(*, all_outputs: bool = False) -> bytes:
    prefix = b"\x00" * 17 + b"\x04\x01" + TAIL
    outputs = (
        b"".join(output(41, name) for name in (
            "npcEntity", "npcPosition", "patrolId", "pointIndex"
        ))
        if all_outputs
        else b"\xff" + output(41, "npcPosition") + b"\xff\xff"
    )
    return prefix + i32_param(10000) + i32_param(4) + outputs + string_param("npc_fixture")


class ProxyPatrolCheckpointEventTests(unittest.TestCase):
    def test_exact_payload_decodes_nullable_and_present_outputs(self) -> None:
        decoded = decode_proxy_patrol_checkpoint_event(
            payload(), EVENT_SEMANTIC_KEY, header_role=True,
        )
        self.assertEqual("npc_fixture", decoded["proxyIdFilter"])
        self.assertEqual(10000, decoded["patrolIdFilter"])
        self.assertEqual(4, decoded["pointIndexFilter"])
        self.assertIsNone(decoded["npcEntityOutputParam"])
        self.assertEqual("$41@_npcPosition", decoded["npcPositionOutputParam"]["path"])
        self.assertEqual(
            "constant-proxy-patrol-checkpoint-and-outputs-exact-eof",
            decoded["payloadShape"],
        )

        complete = decode_proxy_patrol_checkpoint_event(
            payload(all_outputs=True), EVENT_SEMANTIC_KEY, header_role=True,
        )
        self.assertTrue(all(complete[f"{name}OutputParam"] for name in (
            "npcEntity", "npcPosition", "patrolId", "pointIndex"
        )))

    def test_wrong_shape_and_dynamic_proxy_fail_closed(self) -> None:
        exact = payload()
        self.assertEqual({}, decode_proxy_patrol_checkpoint_event(
            exact, (0x0083, 21), header_role=True,
        ))
        self.assertEqual({}, decode_proxy_patrol_checkpoint_event(
            exact, EVENT_SEMANTIC_KEY, header_role=False,
        ))
        self.assertEqual({}, decode_proxy_patrol_checkpoint_event(
            exact[:-1], EVENT_SEMANTIC_KEY, header_role=True,
        ))
        dynamic = exact[:-12] + struct.pack("<iii", 7, 0, -1)
        self.assertEqual({}, decode_proxy_patrol_checkpoint_event(
            dynamic, EVENT_SEMANTIC_KEY, header_role=True,
        ))

    def test_record_decoder_publishes_only_exact_union(self) -> None:
        data = payload()
        record = {
            "start": 0, "payloadStart": 0, "unionTag": 0x0084,
            "serializedMemberCount": 21, "localId": 41, "nextId": -1,
            "code": 0x1584, "kind": 0,
        }
        decoded = decode_levelscript_record_payload(
            data, record, next_start=len(data), action_map_role="headerList#0",
        )
        self.assertEqual(
            "npc_fixture",
            decoded["nativeEventDetail"]["proxyIdFilter"],
        )
        adjacent = dict(record, unionTag=0x0083)
        rejected = decode_levelscript_record_payload(
            data, adjacent, next_start=len(data), action_map_role="headerList#0",
        )
        self.assertNotEqual(
            "LevelEvent_OnProxyPatrolCheckpointReach",
            (rejected.get("nativeEventDetail") or {}).get("type"),
        )


if __name__ == "__main__":
    unittest.main()
