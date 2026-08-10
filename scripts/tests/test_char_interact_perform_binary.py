from __future__ import annotations

import importlib.util
import struct
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "story_builder/char_interact_perform_binary.py"
SPEC = importlib.util.spec_from_file_location("char_interact_perform_binary_test", SCRIPT)
char_interact = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(char_interact)
CharInteractPerformDecodeError = char_interact.CharInteractPerformDecodeError
decode_char_interact_audio_actions = char_interact.decode_char_interact_audio_actions


def u32(value: int) -> bytes:
    return struct.pack("<I", value & 0xFFFFFFFF)


def i32(value: int) -> bytes:
    return struct.pack("<i", value)


def f32(value: float) -> bytes:
    return struct.pack("<f", value)


def audio_action(event_id: int = 0x12345678) -> bytes:
    return b"".join((
        b"\x02\x0f",              # union tag, concrete member count
        b"\x03\x00",              # BodyTypeDef members, bodyType byte
        i32(0), u32(0),             # CustomId, empty CustomName
        f32(0.25), b"\x00",        # delay, devOnly
        f32(-1.0), u32(0),          # duration, empty eventId
        b"\x00", u32(7),           # ifOverridePlayFast, logicId
        b"\x00\x00\x00",          # override/playBefore/useEvent
        i32(1), u32(event_id),       # attachedActorType, AudioId
        i32(-1), b"\x01\x01",      # charIndex, endStop, is2D
    ))


def owner_fixture(action: bytes | None = None) -> bytes:
    action = action or audio_action()
    return b"".join((
        b"\x1b",                   # CharInteractPerformRuntimeCfg members
        u32(0), b"\x00",           # activeTags, allowInheritPerform
        b"\x01" + u32(0),          # bodyTypeActDataDict wrapper + dictionary
        i32(0),                     # charPerformType
        u32(0), u32(0),             # chars, decos
        b"\xff", b"\x00",        # defaultSubPerformEntry, disableIKAndFollow
        u32(0), u32(0),             # effects, endActions
        f32(0.0), b"\x00",         # fixedTime, forceExitCommandsContinuous
        u32(0), u32(0), b"\x00",   # guardActiveTags/reasons, hideWeapon
        u32(0), u32(0), u32(0),     # inherit ids, interactives, interrupt reasons
        b"\x00", u32(0), u32(0),  # keepFightState, loopActions, npcs
        i32(0), u32(0),             # performType, preStartActions
        u32(1), action,             # startActions
        b"\x01" + u32(0),          # subPerformEntries wrapper + dictionary
        u32(0), b"\x00",           # tmpObjects, usePreStartActions
    ))


class CharInteractPerformBinaryTests(unittest.TestCase):
    def test_decodes_audio_only_through_complete_owner_and_phase(self) -> None:
        data = owner_fixture()
        rows = decode_char_interact_audio_actions(data)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["placement"], "startActions")
        self.assertEqual(row["actionIndex"], 0)
        self.assertEqual(row["audioEvent"], 0x12345678)
        self.assertEqual(row["logicId"], 7)
        self.assertEqual(row["attachedActorType"], 1)
        self.assertTrue(row["endStop"])
        self.assertTrue(row["is2D"])
        self.assertEqual(row["endOffset"] - row["sourceOffset"], 47)
        self.assertEqual(row["schemaStatus"], "exact-current-complete-owner-container")

    def test_candidate_with_outer_drift_fails_closed(self) -> None:
        data = bytearray(owner_fixture())
        data[0] = 26
        with self.assertRaisesRegex(
            CharInteractPerformDecodeError,
            "member count changed",
        ):
            decode_char_interact_audio_actions(bytes(data))

    def test_non_candidate_owner_is_outside_narrow_family(self) -> None:
        self.assertEqual(decode_char_interact_audio_actions(b"\x1b" + b"\x00" * 16), [])


if __name__ == "__main__":
    unittest.main()
