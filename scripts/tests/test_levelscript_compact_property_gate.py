from __future__ import annotations

import struct
import unittest

from scripts.story_builder.codecs.levelscript.compact_property_gate import (
    decode_compact_property_gate,
)


_SENTINEL = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"


class LevelScriptCompactPropertyGateTests(unittest.TestCase):
    def test_decodes_single_and_two_slot_key_schemas(self) -> None:
        key = b"mission_stage"
        single = (
            b"\x00" + _SENTINEL + b"\x04\x00"
            + b"\xff\xff\xff\xff" + struct.pack("<II", 7, len(key)) + key
            + b"\x04\x01" + _SENTINEL + struct.pack("<i", 42)
        )
        single_detail = decode_compact_property_gate(single)
        self.assertEqual("single-key", single_detail["schema"])
        self.assertEqual("mission_stage", single_detail["propertyKey"])
        self.assertEqual([42], single_detail["gateLocalRefs"])
        self.assertTrue(single_detail["postSentinel"])

        two_slot = (
            b"\x00" + _SENTINEL + b"\x04\x01" + _SENTINEL
            + b"\x04\x00\xff\xff\xff\xff"
            + struct.pack("<II", 9, len(key)) + key
        )
        two_slot_detail = decode_compact_property_gate(two_slot)
        self.assertEqual("two-slot-key", two_slot_detail["schema"])
        self.assertEqual(9, two_slot_detail["typeCode"])
        self.assertEqual("mission_stage", two_slot_detail["propertyKey"])

    def test_decodes_local_ref_and_rejects_bad_head_gate(self) -> None:
        local_ref = (
            b"\x00" + _SENTINEL + b"\x04\x01"
            + struct.pack("<i", 7) + b"\xff" * 8
            + b"\x04\x00" + _SENTINEL + struct.pack("<i", 12)
        )
        detail = decode_compact_property_gate(local_ref)
        self.assertEqual("local-ref", detail["schema"])
        self.assertEqual(7, detail["firstLocalRef"])
        self.assertEqual([12], detail["gateLocalRefs"])

        malformed = bytearray(local_ref)
        malformed[1] = 0
        rejected = decode_compact_property_gate(bytes(malformed))
        self.assertFalse(rejected["headSentinel"])
        self.assertNotIn("schema", rejected)


if __name__ == "__main__":
    unittest.main()
