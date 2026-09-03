from __future__ import annotations

import struct
import unittest

from scripts.story_builder.leveldata_binary import (
    LevelDataTopLevelFramingError,
    frame_leveldata_empty_tail,
)


class LevelDataTopLevelFramingTests(unittest.TestCase):
    @staticmethod
    def _frame(*, opaque: bytes = b"opaque", string_value: str = "map_fixture") -> bytes:
        encoded = string_value.encode("utf-8")
        return (
            b"\x2b"
            + opaque
            + struct.pack("<i", 7)
            + (struct.pack("<i", 0) * 14)
            + b"\x01"
            + struct.pack("<i", 0)
            + struct.pack("<i", len(encoded))
            + encoded
            + (struct.pack("<i", 0) * 2)
            + b"\xff"
            + (struct.pack("<i", 0) * 3)
        )

    def test_empty_tail_partitions_every_byte_and_preserves_raw_union_tag(self) -> None:
        payload = self._frame()
        framed = frame_leveldata_empty_tail(payload)

        self.assertEqual(len(payload), framed["bytesConsumed"])
        ranges = framed["ranges"]
        self.assertEqual(1, ranges["opaqueTopLevelPrefix"]["startOffset"])
        self.assertEqual(7, ranges["opaqueTopLevelPrefix"]["endOffset"])
        self.assertEqual(0xFF, ranges["emptyTail"]["nullUnionRawTag"])
        self.assertEqual(len(payload), ranges["emptyTail"]["endOffset"])

    def test_empty_tail_rejects_truncation_and_trailing_bytes(self) -> None:
        payload = self._frame()
        with self.assertRaisesRegex(LevelDataTopLevelFramingError, "not unique"):
            frame_leveldata_empty_tail(payload[:-1])
        with self.assertRaisesRegex(LevelDataTopLevelFramingError, "not unique"):
            frame_leveldata_empty_tail(payload + b"\x00")

    def test_empty_tail_rejects_member_count_drift(self) -> None:
        payload = bytearray(self._frame())
        payload[0] = 42
        with self.assertRaisesRegex(LevelDataTopLevelFramingError, "member count"):
            frame_leveldata_empty_tail(bytes(payload))

    def test_empty_tail_rejects_non_null_union_tag(self) -> None:
        payload = bytearray(self._frame())
        payload[-13] = 0x00
        with self.assertRaisesRegex(LevelDataTopLevelFramingError, "not unique"):
            frame_leveldata_empty_tail(bytes(payload))


if __name__ == "__main__":
    unittest.main()
