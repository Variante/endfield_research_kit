from __future__ import annotations

import struct
import unittest

from scripts.game_data.memorypack.lipsync import (
    LIPSYNC_FIELD_NAMES,
    LIPSYNC_ROW_FIELDS,
    LipSyncDecodeError,
    decode_lipsync_memorypack,
    lip_sync_keyframes,
)


def _payload(*, rows_by_field: dict[str, list[tuple[float, ...]] | None] | None = None) -> bytes:
    rows_by_field = rows_by_field or {}
    output = bytearray([len(LIPSYNC_FIELD_NAMES)])
    for field_name in LIPSYNC_FIELD_NAMES:
        rows = rows_by_field.get(field_name)
        if rows is None:
            output.extend(struct.pack("<I", 0xFFFFFFFF))
            continue
        output.extend(struct.pack("<I", len(rows)))
        for row in rows:
            output.extend(struct.pack("<I", len(row)))
            output.extend(struct.pack(f"<{len(row)}f", *row))
    return bytes(output)


class LipSyncMemoryPackTests(unittest.TestCase):
    def test_decodes_nullable_channels_and_keyframe_labels(self) -> None:
        values = (1.0, 0.25, -1.0, 2.0, 0.5, 0.75)
        decoded = decode_lipsync_memorypack(_payload(rows_by_field={"A": [values], "E": []}))
        self.assertEqual(decoded["A"], (values,))
        self.assertEqual(decoded["E"], ())
        self.assertIsNone(decoded["EyebrowRaise"])
        self.assertEqual(
            lip_sync_keyframes(decoded, "A"),
            (dict(zip(LIPSYNC_ROW_FIELDS, values, strict=True)),),
        )

    def test_rejects_wrong_root_member_count(self) -> None:
        data = bytearray(_payload())
        data[0] = len(LIPSYNC_FIELD_NAMES) - 1
        with self.assertRaisesRegex(LipSyncDecodeError, "member-count"):
            decode_lipsync_memorypack(bytes(data))

    def test_rejects_truncated_count_and_rows(self) -> None:
        with self.assertRaisesRegex(LipSyncDecodeError, "truncated-count"):
            decode_lipsync_memorypack(bytes([len(LIPSYNC_FIELD_NAMES)]))
        data = bytearray([len(LIPSYNC_FIELD_NAMES)])
        data.extend(struct.pack("<II", 1, 6))
        data.extend(struct.pack("<5f", 0.0, 0.0, 0.0, 0.0, 0.0))
        with self.assertRaisesRegex(LipSyncDecodeError, "truncated-row"):
            decode_lipsync_memorypack(bytes(data))

    def test_rejects_wrong_row_width_nonfinite_and_trailing_bytes(self) -> None:
        with self.assertRaisesRegex(LipSyncDecodeError, "width=5"):
            decode_lipsync_memorypack(
                _payload(rows_by_field={"A": [(0.0, 0.0, 0.0, 0.0, 0.0)]})
            )
        with self.assertRaisesRegex(LipSyncDecodeError, "nonfinite-float"):
            decode_lipsync_memorypack(
                _payload(rows_by_field={"A": [(float("nan"), 0.0, 0.0, 0.0, 0.0, 0.0)]})
            )
        with self.assertRaisesRegex(LipSyncDecodeError, "trailing-bytes=1"):
            decode_lipsync_memorypack(_payload() + b"x")

    def test_rejects_unreasonable_count_before_reading_rows(self) -> None:
        data = bytearray([len(LIPSYNC_FIELD_NAMES)])
        data.extend(struct.pack("<I", 1_000_001))
        with self.assertRaisesRegex(LipSyncDecodeError, "max=1000000"):
            decode_lipsync_memorypack(bytes(data))

    def test_keyframe_labels_reject_unknown_channel(self) -> None:
        with self.assertRaises(KeyError):
            lip_sync_keyframes({name: None for name in LIPSYNC_FIELD_NAMES}, "unknown")


if __name__ == "__main__":
    unittest.main()
