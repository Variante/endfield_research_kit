from __future__ import annotations

import struct
import unittest

from scripts.story_builder.levelscript_binary import (
    _decode_trigger_volume_map,
    _find_final_trigger_volume_map,
    decode_levelscript_binary_summary,
    decode_levelscript_encounter_module_target,
)


class LevelScriptTriggerVolumeTests(unittest.TestCase):
    @staticmethod
    def _single_encounter_script(pointer: int, script_id: int) -> bytes:
        slot_ptr = lambda logic_id, slot_id: (
            b"\x03"
            + struct.pack("<Q", logic_id)
            + struct.pack("<I", slot_id)
            + b"\x01"
        )
        intro = (
            b"\x0d"
            + struct.pack("<ii", 2, 1)
            + struct.pack("<ff", 0.0, 0.0)
            + b"\x00\x00"
            + struct.pack("<i", -1)
            + struct.pack("<i", 0)
            + struct.pack("<" + "f" * 24, *([0.0] * 24))
            + struct.pack("<i", 0)
        )
        encounter = (
            struct.pack("<iQ", 1, pointer)
            + b"\x02\x10\x01"
            + struct.pack("<QiiII", pointer, 1, 0, 80007, 0)
            + struct.pack("<i", -1)
            + struct.pack("<i", 1)
            + slot_ptr(script_id, 90001)
            + b"\x08"
            + struct.pack("<fii", 0.0, 0, 0)
            + struct.pack("<i", 0)
            + b"\x00"
            + struct.pack("<I", 80005)
            + b"\x01\x00"
            + struct.pack("<i", 1)
            + slot_ptr(0, 30001)
            + intro
            + b"\xff"
            + struct.pack("<iQ", 0, 0)
            + b"\xff"
            + struct.pack("<i", 0)
        )
        tail = (
            struct.pack("<iQ", 0, 0)
            + struct.pack("<iii", -1, -1, -1)
            + struct.pack("<iiQ", 0, 0, script_id)
            + struct.pack("<iii", -1, 1, -1)
            + struct.pack("<i", 0)
        )
        return b"\x1b" + b"\xaa" * 31 + encounter + tail

    @staticmethod
    def _leader_volume(slot_id: int) -> bytes:
        shape = (
            b"\x06"
            + (0).to_bytes(4, "little", signed=True)
            + struct.pack("<fff", 1.25, 2.5, 3.75)
            + struct.pack("<f", 8.0)
            + struct.pack("<fff", 0.0, 45.0, 0.0)
            + (2).to_bytes(4, "little", signed=True)
            + struct.pack("<fff", 3.0, 3.0, 3.0)
        )
        return (
            slot_id.to_bytes(4, "little", signed=False)
            + b"\x01"  # current-build Leader union tag
            + b"\x08"  # base member count
            + b"\x00"
            + (-1).to_bytes(4, "little", signed=True)
            + b"\x00"
            + (1).to_bytes(4, "little", signed=True)
            + shape
            + slot_id.to_bytes(4, "little", signed=False)
            + (1).to_bytes(4, "little", signed=True)
            + b"\x00\x00"
        )

    def test_union_tag_and_exact_geometry_decode_to_eof(self) -> None:
        map_payload = (
            (1).to_bytes(4, "little", signed=True)
            + self._leader_volume(80001)
        )
        decoded, cursor = _decode_trigger_volume_map(map_payload, 0)
        self.assertEqual(len(map_payload), cursor)
        self.assertEqual([80001], decoded["slotIds"])
        volume = decoded["volumes"][0]
        self.assertEqual("Leader", volume["triggerVolumeType"])
        self.assertEqual(80001, volume["keySlotId"])
        self.assertEqual("Sphere", volume["shapeList"]["shapes"][0]["shapeType"])
        self.assertEqual(8.0, volume["shapeList"]["shapes"][0]["radius"])

        wrapped = b"task-prefix" + map_payload
        offset, tail, cursor = _find_final_trigger_volume_map(
            wrapped,
            search_start=0,
        )
        self.assertEqual(len(b"task-prefix"), offset)
        self.assertEqual(len(wrapped), cursor)
        self.assertEqual([80001], tail["slotIds"])

    def test_finds_exact_empty_or_null_map_at_eof(self) -> None:
        for encoded_count, expected_status, expected_count in (
            (0, "present", 0),
            (-1, "null", None),
        ):
            with self.subTest(encoded_count=encoded_count):
                payload = (
                    b"task-prefix"
                    + encoded_count.to_bytes(4, "little", signed=True)
                )
                offset, tail, cursor = _find_final_trigger_volume_map(
                    payload,
                    search_start=0,
                )
                self.assertEqual(len(b"task-prefix"), offset)
                self.assertEqual(len(payload), cursor)
                self.assertEqual(expected_status, tail["status"])
                self.assertEqual(expected_count, tail.get("count"))
                self.assertEqual("decoded", tail["parseStatus"])
                self.assertNotIn("volumes", tail)

    def test_empty_task_map_does_not_search_past_embedded_script_id(self) -> None:
        script_id = 3400160000
        embedded = (
            struct.pack("<Q", script_id)
            + struct.pack("<i", 0)  # empty start shapes
            + struct.pack("<i", 1)  # valid start type
            + struct.pack("<i", 0)  # empty task map
            + b"embedded-logic-record"
        )
        top_level_offset = len(embedded)
        top_level = (
            struct.pack("<Q", script_id)
            + struct.pack("<i", -1)  # null start shapes
            + struct.pack("<i", 1)  # valid start type
            + struct.pack("<i", 0)  # empty task map
            + struct.pack("<i", 0)  # exact empty trigger-volume map at EOF
        )
        summary = decode_levelscript_binary_summary(
            b"\x1b" + embedded + top_level,
            script_id,
        )
        self.assertEqual(top_level_offset + 1, summary["probableScriptIdOffset"])
        self.assertEqual("present", summary["triggerVolumesStatus"])
        self.assertEqual(0, summary["triggerVolumesCount"])

    def test_rejects_missing_union_tag_and_key_slot_mismatch(self) -> None:
        valid = self._leader_volume(80001)
        missing_tag = valid[:4] + valid[5:]
        decoded, cursor = _decode_trigger_volume_map(
            (1).to_bytes(4, "little", signed=True) + missing_tag,
            0,
        )
        self.assertIsNone(cursor)
        self.assertEqual("truncated", decoded["parseStatus"])

        mismatched = bytearray(valid)
        mismatched[-10:-6] = (80002).to_bytes(4, "little", signed=False)
        decoded, cursor = _decode_trigger_volume_map(
            (1).to_bytes(4, "little", signed=True) + bytes(mismatched),
            0,
        )
        self.assertIsNone(cursor)
        self.assertEqual("truncated", decoded["parseStatus"])

    def test_encounter_pointer_resolves_only_complete_top_level_target(self) -> None:
        pointer = 34700000003
        script_id = 34700000018
        payload = self._single_encounter_script(pointer, script_id)
        target = decode_levelscript_encounter_module_target(
            payload,
            pointer,
            script_id,
        )
        self.assertEqual("EncounterData", target["moduleType"])
        self.assertEqual("3", str(target["moduleLocalId"]))
        self.assertEqual(80007, target["activateTriggerSlotId"])
        self.assertEqual(80005, target["battlePart"]["exitTriggerSlotId"])
        self.assertEqual([30001], [row["slotId"] for row in target["enemyPointers"]])
        self.assertFalse(target["serializedMissionOrQuestId"])
        self.assertIn("no missionId", target["ownershipBoundary"])

        self.assertEqual(
            {},
            decode_levelscript_encounter_module_target(payload, pointer + 1, script_id),
        )
        self.assertEqual(
            {},
            decode_levelscript_encounter_module_target(payload[:-1], pointer, script_id),
        )

if __name__ == "__main__":
    unittest.main()
