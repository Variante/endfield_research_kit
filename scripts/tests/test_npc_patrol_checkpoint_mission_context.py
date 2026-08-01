from __future__ import annotations

import json
from pathlib import Path
import struct
import unittest

from scripts.story_builder.context import ROOT
from scripts.story_builder.level_bindings import (
    build_leveldata_npc_patrol_radio_story_contexts,
    build_levelscript_native_story_playback_index,
    build_npc_patrol_checkpoint_mission_contexts,
    parse_leveldata_npc_patrol_data_entry,
)
from scripts.story_builder.levelscript_binary import decode_levelscript_record_payload


PARAM_TAIL = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"


def bool_param(value: bool) -> bytes:
    return b"\x04" + bytes([int(value)]) + PARAM_TAIL


def int_param(value: int) -> bytes:
    return b"\x04" + struct.pack("<i", value) + PARAM_TAIL


def dynamic_entity(alias: str) -> bytes:
    encoded = alias.encode("utf-8")
    return (
        b"\x04\x03"
        + struct.pack("<Q", 0)
        + struct.pack("<I", 0)
        + b"\x00"
        + struct.pack("<i", -1)
        + struct.pack("<i", 200)
        + struct.pack("<i", len(encoded))
        + encoded
    )


def patrol_row(patrol_id: int, points: int) -> bytes:
    fixed = (
        b"\x09"
        + struct.pack("<i", 0)
        + struct.pack("<f", 4.0)
        + b"\x00\x00\x01"
        + struct.pack("<i", 0)
        + struct.pack("<i", 0)
        + struct.pack("<i", patrol_id)
        + struct.pack("<i", points)
    )
    point = (
        b"\x03"
        + struct.pack("<i", 0)
        + struct.pack("<i", 0)
        + struct.pack("<fff", 1.0, 2.0, 3.0)
    )
    return fixed + point * points


class NpcPatrolCheckpointMissionContextTests(unittest.TestCase):
    def test_npc_patrol_start_requires_the_exact_four_field_eof(self) -> None:
        payload = (
            bool_param(True)
            + int_param(10030)
            + bool_param(False)
            + dynamic_entity("robot")
        )
        record = {
            "start": 0,
            "payloadStart": 0,
            "code": 0x031E,
            "kind": 0x0C,
            "unionTag": 0x031E,
            "serializedMemberCount": 12,
            "localId": 17,
            "nextId": -1,
        }
        decoded = decode_levelscript_record_payload(
            payload,
            record,
            next_start=len(payload),
            action_map_role="actionList#1",
        )["npcPatrolStart"]
        self.assertEqual(10030, decoded["patrolId"])
        self.assertEqual("robot", decoded["targetNpc"]["path"])
        self.assertEqual("npc-patrol-start-four-field-exact-eof", decoded["payloadShape"])

        rejected = decode_levelscript_record_payload(
            payload + b"\x00",
            record,
            next_start=len(payload) + 1,
            action_map_role="actionList#1",
        )
        self.assertNotIn("npcPatrolStart", rejected)

    def test_npc_patrol_data_consumes_every_typed_point(self) -> None:
        first = patrol_row(10030, 4)
        payload = first + patrol_row(10031, 1)
        decoded = parse_leveldata_npc_patrol_data_entry(
            payload,
            0,
            expected_patrol_id=10030,
        )
        self.assertIsNotNone(decoded)
        self.assertEqual(4, decoded["pointCount"])
        self.assertEqual(len(first), decoded["recordEndOffset"])
        self.assertEqual([0, 1, 2, 3], [row["pointIndex"] for row in decoded["points"]])

        damaged = bytearray(payload)
        damaged[28] = 0x02
        self.assertIsNone(
            parse_leveldata_npc_patrol_data_entry(
                bytes(damaged),
                0,
                expected_patrol_id=10030,
            )
        )

    def test_current_original_data_recovers_only_the_six_patrol_story_files(self) -> None:
        flows: dict[str, dict] = {}
        for path in sorted((ROOT / "webui/data/lang/CN/mission").glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and isinstance(payload.get("flow"), dict):
                flows[path.stem] = payload["flow"]
        rows = build_npc_patrol_checkpoint_mission_contexts(
            build_levelscript_native_story_playback_index(),
            flows,
        )
        by_key = {row["storyKey"]: row for row in rows}
        self.assertEqual({
            "radio_sm2l5m1_6",
            "radio_sm2l5m1_18",
            "radio_sm2l5m1_20",
            "radio_sm2l5m1_26",
            "radio_sm2l5m1_32",
            "radio_sm2l5m1_37",
        }, set(by_key))
        self.assertEqual({"sm2l5m1"}, {row["missionId"] for row in rows})
        self.assertEqual(2, len(by_key["radio_sm2l5m1_18"]["occurrences"]))
        self.assertEqual(
            ["sm2l5m1_q#10", "sm2l5m1_q#9"],
            by_key["radio_sm2l5m1_32"]["candidateQuestIds"],
        )

    def test_current_gm01m16_patrol_radios_keep_exact_binary_boundaries(self) -> None:
        rows = build_leveldata_npc_patrol_radio_story_contexts({
            "radio_gm01m16_5",
            "radio_gm01m16_6",
            "radio_gm01m16_15",
        })
        by_key = {row["radioId"]: row for row in rows}
        self.assertEqual(
            {
                "radio_gm01m16_5",
                "radio_gm01m16_6",
                "radio_gm01m16_15",
            },
            set(by_key),
        )
        self.assertEqual(
            (160002, 1, 0, 8742, 8841),
            tuple(by_key["radio_gm01m16_5"][key] for key in (
                "patrolId",
                "pointIndex",
                "pointActionIndex",
                "radioActionRecordOffset",
                "radioActionRecordEndOffset",
            )),
        )
        self.assertEqual(
            (160002, 14, 0, 9198, 9297),
            tuple(by_key["radio_gm01m16_6"][key] for key in (
                "patrolId",
                "pointIndex",
                "pointActionIndex",
                "radioActionRecordOffset",
                "radioActionRecordEndOffset",
            )),
        )
        self.assertEqual(20001, by_key["radio_gm01m16_15"]["patrolId"])
        self.assertEqual(
            "exact_typed_neighbor_boundaries_partial_point_decode",
            by_key["radio_gm01m16_15"]["patrolEnvelopeStatus"],
        )
        self.assertEqual(9, by_key["radio_gm01m16_15"]["type"])
        self.assertEqual(
            26,
            by_key["radio_gm01m16_15"][
                "radioActionSerializedMemberCount"
            ],
        )
        self.assertEqual(6.0, by_key["radio_gm01m16_15"]["radius"])


if __name__ == "__main__":
    unittest.main()
