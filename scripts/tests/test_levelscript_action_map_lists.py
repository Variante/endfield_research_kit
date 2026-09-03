from __future__ import annotations

import struct
import unittest

from scripts.story_builder.levelscript_binary import (
    LevelScriptTopLevelFramingError,
    decode_levelscript_action_map_lists,
    frame_levelscript_empty_action_map_top_level,
    levelscript_action_map_membership,
)


class LevelScriptActionMapListTests(unittest.TestCase):
    SCRIPT_ID = 9_900_000_001

    @classmethod
    def _partial_top_level_frame(cls, *, opaque: bytes = b"opaque") -> bytes:
        return (
            b"\x1b\x02\x03"
            + struct.pack("<III", 0, 0, 0)
            + opaque
            + struct.pack("<Q", cls.SCRIPT_ID)
            + struct.pack("<I", 0xFFFFFFFF)  # null start-shape list
            + struct.pack("<i", 1)           # observed start-type code
            + struct.pack("<I", 0xFFFFFFFF)  # null task map
            + struct.pack("<I", 0)           # empty trigger-volume map
        )

    def test_exact_empty_map_keeps_later_uid_records_outside(self) -> None:
        data = bytearray(96)
        data[0:3] = b"\x1b\x02\x03"
        struct.pack_into("<III", data, 3, 0, 0, 0)
        records = [{
            "start": 32,
            "localId": 1,
            "nextId": -1,
            "code": 0,
            "kind": 0,
        }]

        action_map, membership = levelscript_action_map_membership(
            bytes(data),
            records,
        )

        self.assertTrue(action_map["exactEmptyActionMap"])
        self.assertEqual(action_map["emptyMapBoundaryEndOffset"], "0xf")
        self.assertEqual(
            action_map["listCounts"],
            {"actionList": 0, "getterList": 0, "headerList": 0},
        )
        self.assertEqual(membership, {})
        self.assertEqual(
            action_map["serializedLists"][-1]["status"],
            "residual-uid-records-after-exact-empty-map",
        )

    def test_empty_map_decodes_without_uid_records(self) -> None:
        data = b"\x1b\x02\x03" + struct.pack("<III", 0, 0, 0)

        action_map = decode_levelscript_action_map_lists(data, [])

        self.assertTrue(action_map["exactEmptyActionMap"])
        self.assertEqual(len(action_map["serializedLists"]), 3)
        self.assertEqual(
            [row["countOffset"] for row in action_map["serializedLists"]],
            ["0x3", "0x7", "0xb"],
        )

    def test_partial_top_level_frame_partitions_every_byte(self) -> None:
        payload = self._partial_top_level_frame()
        framed = frame_levelscript_empty_action_map_top_level(
            payload,
        )

        self.assertEqual(len(payload), framed["bytesConsumed"])
        ranges = framed["ranges"]
        self.assertEqual(1, ranges["actionSerializedMap"]["startOffset"])
        self.assertEqual(15, ranges["actionSerializedMap"]["endOffset"])
        self.assertEqual(15, ranges["opaqueTopLevelMembers"][0]["startOffset"])
        self.assertEqual(21, ranges["opaqueTopLevelMembers"][0]["endOffset"])
        self.assertEqual(21, ranges["suffixEnvelope"]["startOffset"])
        self.assertEqual(len(payload), ranges["suffixEnvelope"]["endOffset"])
        suffix = framed["suffixEnvelope"]
        self.assertEqual(self.SCRIPT_ID, suffix["anchorU64"])
        self.assertEqual(1, suffix["rawSelectorI32"])
        self.assertEqual("present", suffix["finalCollection"]["status"])
        self.assertEqual(
            "unproven_for_current_native_build",
            suffix["fieldIdentityStatus"],
        )

    def test_partial_top_level_frame_rejects_truncation_and_trailing_bytes(self) -> None:
        payload = self._partial_top_level_frame()
        with self.assertRaisesRegex(LevelScriptTopLevelFramingError, "not unique"):
            frame_levelscript_empty_action_map_top_level(
                payload[:-1],
            )
        with self.assertRaisesRegex(LevelScriptTopLevelFramingError, "not unique"):
            frame_levelscript_empty_action_map_top_level(
                payload + b"\x00",
            )

    def test_partial_top_level_frame_ignores_non_structural_script_id_copy(self) -> None:
        duplicate = struct.pack("<Q", self.SCRIPT_ID)
        payload = self._partial_top_level_frame(opaque=duplicate)
        framed = frame_levelscript_empty_action_map_top_level(
            payload,
        )
        self.assertEqual(23, framed["ranges"]["suffixEnvelope"]["startOffset"])

    def test_partial_top_level_frame_rejects_nonempty_action_map(self) -> None:
        payload = bytearray(self._partial_top_level_frame())
        struct.pack_into("<I", payload, 3, 1)
        with self.assertRaisesRegex(LevelScriptTopLevelFramingError, "non-empty"):
            frame_levelscript_empty_action_map_top_level(
                bytes(payload),
            )


if __name__ == "__main__":
    unittest.main()
