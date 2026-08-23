from __future__ import annotations

import struct
import unittest

from scripts.story_builder.codecs.levelscript.entity_cast_and_death_events import (
    ANY_ENTITY_DIE,
    ENTITY_CAST_SKILL,
    SPECIFIC_ENTITY_DIE,
    SPECIFIC_ENTITY_LIST_DIE,
    decode_entity_event_fields,
)


_PARAM_TAIL = struct.pack("<iii", -1, 0, -1)


def _event_prefix(*, filter_mode: bool = False) -> bytes:
    prefix = bytearray(17)
    prefix[4] = int(filter_mode)
    return bytes(prefix) + b"\x04\x01" + _PARAM_TAIL


def _output(path: str) -> bytes:
    value = path.encode("ascii")
    return b"\x02" + struct.pack("<ii", 0, len(value)) + value


def _constant_bool(value: bool) -> bytes:
    return b"\x04" + bytes([value]) + _PARAM_TAIL


def _constant_i32(value: int) -> bytes:
    return b"\x04" + struct.pack("<i", value) + _PARAM_TAIL


class LevelScriptEntityCastAndDeathEventTests(unittest.TestCase):
    def test_entity_cast_skill_decodes_outputs_and_filters(self) -> None:
        payload = _event_prefix(filter_mode=True)
        payload += b"".join(
            _output(path)
            for path in (
                "$7@_entity",
                "$7@_entityTemplateId",
                "$7@_firstTargetId",
            )
        )
        payload += _constant_bool(True)
        payload += _output("$7@_skillId")
        payload += _constant_i32(3)

        fields = decode_entity_event_fields(payload, ENTITY_CAST_SKILL)

        self.assertEqual("$7@_entity", fields["entityOutputRef"])
        self.assertTrue(fields["isCharacterFilter"])
        self.assertEqual(3, fields["skillTypeFilter"])
        self.assertTrue(fields["filterModeEnabled"])
        self.assertEqual(0, fields["trailingContainerBytes"])

    def test_specific_entity_die_decodes_constant_entity_pointer(self) -> None:
        entity_pointer = (
            b"\x04\x03"
            + struct.pack("<QI?ii", 1234, 88, True, -1, 0)
            + struct.pack("<i", -1)
        )
        payload = _event_prefix() + _output("$9@_entity") + entity_pointer

        fields = decode_entity_event_fields(payload, SPECIFIC_ENTITY_DIE)

        self.assertEqual("$9@_entity", fields["entityOutputRef"])
        self.assertEqual(1234, fields["entityFilter"]["logicId"])
        self.assertEqual(88, fields["entityFilter"]["slotId"])
        self.assertTrue(fields["entityFilter"]["useSlotId"])

    def test_any_entity_die_decodes_list_and_boolean_filters(self) -> None:
        entity_list = b"\x04" + struct.pack("<I", 2)
        entity_list += b"\x03" + struct.pack("<QI?", 100, 4, False)
        entity_list += b"\x03" + struct.pack("<QI?", 200, 5, True)
        payload = (
            _event_prefix()
            + _output("$3@_entity")
            + entity_list
            + _PARAM_TAIL
            + _constant_bool(True)
            + _constant_bool(False)
        )

        fields = decode_entity_event_fields(payload, ANY_ENTITY_DIE)

        self.assertEqual([100, 200], [item["logicId"] for item in fields["entityListFilter"]])
        self.assertTrue(fields["isMonsterFilter"])
        self.assertFalse(fields["filterByList"])

    def test_specific_entity_list_die_decodes_constant_slot_list(self) -> None:
        entity_list = (
            b"\x04"
            + struct.pack("<I", 1)
            + b"\x03"
            + struct.pack("<QI?", 0, 30005, True)
            + _PARAM_TAIL
        )
        payload = _event_prefix() + _output("$78@_entity") + entity_list

        fields = decode_entity_event_fields(payload, SPECIFIC_ENTITY_LIST_DIE)

        self.assertEqual("$78@_entity", fields["entityOutputRef"])
        self.assertEqual(
            [{"logicId": 0, "slotId": 30005, "useSlotId": True}],
            fields["entityListFilter"],
        )
        self.assertEqual("specific-constant-entity-list-exact-eof", fields["payloadShape"])

    def test_unknown_and_malformed_payloads_fail_closed(self) -> None:
        self.assertEqual({}, decode_entity_event_fields(b"", ENTITY_CAST_SKILL))
        self.assertEqual({}, decode_entity_event_fields(_event_prefix(), "Other"))
        self.assertEqual(
            {},
            decode_entity_event_fields(
                _event_prefix() + _output("$1@_entity") + b"\x00",
                SPECIFIC_ENTITY_DIE,
            ),
        )


if __name__ == "__main__":
    unittest.main()
