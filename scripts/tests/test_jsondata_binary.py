from __future__ import annotations

import struct
import unittest

from scripts.story_builder.char_interact_perform_binary import (
    CharInteractPerformDecodeError,
    decode_char_interact_complete_frame,
)


def _empty_char_interact_frame() -> bytes:
    out = bytearray([27])

    def count(value: int = 0) -> None:
        out.extend(struct.pack("<I", value))

    def boolean(value: bool = False) -> None:
        out.append(1 if value else 0)

    # The fixture follows the exact 27-member setter order. Nullable
    # serialized dictionaries/objects use MemoryPack's 0xff null marker.
    count()                         # activeTags
    boolean()                       # allowInheritPerform
    out.append(0xFF)                 # bodyTypeActDataDict
    out.extend(struct.pack("<i", 0))  # charPerformType
    count()                         # chars
    count()                         # decos
    out.append(0xFF)                 # defaultSubPerformEntry
    boolean()                       # disableIKAndFollow
    count()                         # effects
    count()                         # endActions
    out.extend(struct.pack("<f", 0.0))  # fixedTime
    boolean()                       # forceExitCommandsContinuous
    count()                         # guardActiveTags
    count()                         # guardInterruptReasons
    boolean()                       # hideWeapon
    count()                         # inheritPerformIds
    count()                         # interactives
    count()                         # interruptReasons
    boolean()                       # keepFightState
    count()                         # loopActions
    count()                         # npcs
    out.extend(struct.pack("<i", 0))  # performType
    count()                         # preStartActions
    count()                         # startActions
    out.append(0xFF)                 # subPerformEntries
    count()                         # tmpObjects
    boolean()                       # usePreStartActions
    return bytes(out)


class JsonDataBinaryFrameTests(unittest.TestCase):
    def test_empty_owner_consumes_exactly_to_eof(self) -> None:
        payload = _empty_char_interact_frame()
        decoded = decode_char_interact_complete_frame(payload)
        self.assertEqual("exact_current_char_interact_frame", decoded["status"])
        self.assertEqual(27, decoded["serializedMemberCount"])
        self.assertEqual(len(payload), decoded["bytesConsumed"])
        self.assertEqual(0, decoded["actionCount"])

    def test_truncated_owner_fails_closed(self) -> None:
        with self.assertRaisesRegex(CharInteractPerformDecodeError, "truncated"):
            decode_char_interact_complete_frame(_empty_char_interact_frame()[:-1])

    def test_outer_member_count_drift_fails_closed(self) -> None:
        payload = bytearray(_empty_char_interact_frame())
        payload[0] = 26
        with self.assertRaisesRegex(CharInteractPerformDecodeError, "member count"):
            decode_char_interact_complete_frame(payload)

    def test_trailing_bytes_fail_closed(self) -> None:
        with self.assertRaisesRegex(CharInteractPerformDecodeError, "trailing bytes"):
            decode_char_interact_complete_frame(_empty_char_interact_frame() + b"\x00")
