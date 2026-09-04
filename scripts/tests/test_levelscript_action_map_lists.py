from __future__ import annotations

import struct
import unittest

from scripts.story_builder.levelscript_binary import (
    LevelScriptTopLevelFramingError,
    decode_levelscript_action_map_lists,
    frame_levelscript_action_map_anonymous_prefix,
    frame_levelscript_empty_action_map_top_level,
    frame_levelscript_first_record_35_0e_00_anonymous_body,
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

    @staticmethod
    def _fa_first_record_prefix(*, payload: bytes = b"opaque") -> bytes:
        record = bytearray(32)
        record[0] = 0xFA
        struct.pack_into("<H", record, 1, 0x04B0)
        record[3] = 15
        record[4] = 1
        struct.pack_into("<I", record, 5, 7)
        record[9] = 0
        struct.pack_into("<I", record, 10, 8)
        record[14:22] = b"12ab34cd"
        struct.pack_into("<i", record, 28, -1)
        return b"\x1b\x02\x03" + struct.pack("<I", 1) + bytes(record) + payload

    @staticmethod
    def _plain_first_record_prefix(*, payload: bytes = b"opaque") -> bytes:
        record = bytearray(30)
        struct.pack_into("<H", record, 0, 0x0102)
        record[2] = 0
        struct.pack_into("<I", record, 3, 3)
        record[7] = 0
        struct.pack_into("<I", record, 8, 8)
        record[12:20] = b"deadbeef"
        struct.pack_into("<i", record, 26, -1)
        return b"\x1b\x02\x03" + struct.pack("<I", 1) + bytes(record) + payload

    @staticmethod
    def _anonymous_35_0e_00_body(
        *,
        leading_values: tuple[str, ...] | None = None,
        trailing: bytes = b"opaque",
    ) -> bytes:
        def nullable(value: str | None) -> bytes:
            if value is None:
                return struct.pack("<i", -1)
            raw = value.encode("utf-8")
            return struct.pack("<i", len(raw)) + raw

        if leading_values is None:
            leading = struct.pack("<i", -1)
        else:
            leading = struct.pack("<i", len(leading_values)) + b"".join(
                nullable(value) for value in leading_values
            )
        anonymous_tail = struct.pack("<ii", -1, 0) + nullable(None)
        body = (
            leading
            + b"\x04\x01"
            + nullable("event_args")
            + anonymous_tail
            + b"\x04"
            + nullable("#12ab34cd")
            + anonymous_tail
            + b"\x00\x01\x00"
        )
        record = bytearray(30)
        record[0:3] = b"\x35\x0e\x00"
        struct.pack_into("<I", record, 3, 3)
        record[7] = 0
        struct.pack_into("<I", record, 8, 8)
        record[12:20] = b"deadbeef"
        struct.pack_into("<i", record, 26, -1)
        return b"\x1b\x02\x03" + struct.pack("<I", 1) + bytes(record) + body + trailing

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

    def test_anonymous_prefix_frames_fa_record_without_naming_lists(self) -> None:
        payload = self._fa_first_record_prefix()
        framed = frame_levelscript_action_map_anonymous_prefix(payload)

        self.assertEqual(
            "exact_anonymous_nonempty_action_map_first_record_prefix",
            framed["status"],
        )
        self.assertEqual(39, framed["bytesConsumed"])
        prefix = framed["ranges"]["actionSerializedMapPrefix"]
        self.assertEqual(1, prefix["anonymousFirstListCount"])
        self.assertEqual("not_interpreted", prefix["serializedFieldOrderStatus"])
        envelope = framed["ranges"]["firstRecordEnvelope"]
        self.assertEqual("fa", envelope["layout"])
        self.assertEqual(0x04B0, envelope["rawUnionTag"])
        self.assertEqual(15, envelope["rawSerializedMemberCount"])
        self.assertEqual("12ab34cd", envelope["uidAnchorAscii"])
        self.assertEqual(39, framed["ranges"]["opaqueRemainder"][0]["startOffset"])
        self.assertNotIn("actionList", repr(framed))

    def test_anonymous_prefix_frames_plain_record_envelope(self) -> None:
        framed = frame_levelscript_action_map_anonymous_prefix(
            self._plain_first_record_prefix(),
        )

        self.assertEqual(37, framed["bytesConsumed"])
        envelope = framed["ranges"]["firstRecordEnvelope"]
        self.assertEqual("plain", envelope["layout"])
        self.assertEqual("memorypack-u8", envelope["unionTagEncoding"])
        self.assertEqual(0x02, envelope["rawUnionTag"])

    def test_anonymous_prefix_frames_only_one_byte_for_null_map(self) -> None:
        payload = b"\x1b\xff\x01remaining"
        framed = frame_levelscript_action_map_anonymous_prefix(payload)

        self.assertEqual("exact_anonymous_null_action_map_boundary", framed["status"])
        self.assertEqual(2, framed["bytesConsumed"])
        action_map = framed["ranges"]["actionSerializedMap"]
        self.assertEqual({
            "startOffset": 1,
            "endOffset": 2,
            "rawUnionTag": 0xFF,
            "unionTagEncoding": "memorypack-null-u8",
            "serializedFieldOrderStatus": "not_interpreted",
        }, action_map)
        self.assertEqual(2, framed["ranges"]["opaqueTopLevelMembers"][0]["startOffset"])

    def test_anonymous_prefix_rejects_empty_map_and_bad_outer_marker(self) -> None:
        empty_map = b"\x1b\x02\x03" + struct.pack("<III", 0, 0, 0)
        with self.assertRaisesRegex(LevelScriptTopLevelFramingError, "empty-map"):
            frame_levelscript_action_map_anonymous_prefix(empty_map)
        with self.assertRaisesRegex(LevelScriptTopLevelFramingError, "member count"):
            frame_levelscript_action_map_anonymous_prefix(
                b"\x1a" + self._fa_first_record_prefix()[1:],
            )

    def test_anonymous_prefix_rejects_truncated_or_corrupt_record_envelope(self) -> None:
        payload = self._fa_first_record_prefix()
        with self.assertRaisesRegex(LevelScriptTopLevelFramingError, "not unique"):
            frame_levelscript_action_map_anonymous_prefix(payload[:30])

        corrupt_uid = bytearray(payload)
        corrupt_uid[21] = ord("G")
        with self.assertRaisesRegex(LevelScriptTopLevelFramingError, "not unique"):
            frame_levelscript_action_map_anonymous_prefix(bytes(corrupt_uid))

        impossible_count = bytearray(payload)
        struct.pack_into("<I", impossible_count, 3, len(payload))
        with self.assertRaisesRegex(LevelScriptTopLevelFramingError, "impossible"):
            frame_levelscript_action_map_anonymous_prefix(bytes(impossible_count))

    def test_selected_anonymous_body_advances_exact_cursor(self) -> None:
        payload = self._anonymous_35_0e_00_body()
        framed = frame_levelscript_first_record_35_0e_00_anonymous_body(payload)

        self.assertEqual("exact_anonymous_first_record_35_0e_00_body", framed["status"])
        self.assertEqual(61, framed["bodyBytesConsumed"])
        self.assertEqual(98, framed["bytesConsumed"])
        body = framed["ranges"]["firstRecordBody"]
        self.assertEqual(37, body["startOffset"])
        self.assertEqual(98, body["endOffset"])
        segments = body["anonymousSegments"]
        self.assertIsNone(segments[0]["values"])
        self.assertEqual(["event_args"], segments[1]["values"])
        self.assertEqual("#12ab34cd", segments[2]["value"])
        self.assertEqual("00 01 00", segments[3]["rawHex"])
        self.assertEqual(98, framed["ranges"]["opaqueRemainder"][0]["startOffset"])
        self.assertNotIn("actionList", repr(framed))

    def test_selected_anonymous_body_handles_bounded_leading_collection(self) -> None:
        payload = self._anonymous_35_0e_00_body(
            leading_values=("12345678", "90abcdef"),
        )
        framed = frame_levelscript_first_record_35_0e_00_anonymous_body(payload)

        self.assertEqual(85, framed["bodyBytesConsumed"])
        self.assertEqual(122, framed["bytesConsumed"])
        leading = framed["ranges"]["firstRecordBody"]["anonymousSegments"][0]
        self.assertEqual(["12345678", "90abcdef"], leading["values"])

    def test_selected_anonymous_body_does_not_scan_opaque_uid_like_trailer(self) -> None:
        fake_later_record = self._fa_first_record_prefix()[7:]
        payload = self._anonymous_35_0e_00_body(trailing=fake_later_record)
        framed = frame_levelscript_first_record_35_0e_00_anonymous_body(payload)

        self.assertEqual(98, framed["bytesConsumed"])
        opaque = framed["ranges"]["opaqueRemainder"][0]
        self.assertEqual(len(fake_later_record), opaque["length"])

    def test_selected_anonymous_body_rejects_wrong_variant_and_truncation(self) -> None:
        with self.assertRaisesRegex(LevelScriptTopLevelFramingError, "variant mismatch"):
            frame_levelscript_first_record_35_0e_00_anonymous_body(
                self._plain_first_record_prefix(),
            )
        payload = self._anonymous_35_0e_00_body(trailing=b"")
        with self.assertRaisesRegex(LevelScriptTopLevelFramingError, "truncated"):
            frame_levelscript_first_record_35_0e_00_anonymous_body(payload[:-1])

    def test_selected_anonymous_body_rejects_bad_length_marker_and_suffix(self) -> None:
        bad_length = bytearray(self._anonymous_35_0e_00_body())
        struct.pack_into("<i", bad_length, 37, -2)
        with self.assertRaisesRegex(LevelScriptTopLevelFramingError, "collection count"):
            frame_levelscript_first_record_35_0e_00_anonymous_body(bytes(bad_length))

        bad_marker = bytearray(self._anonymous_35_0e_00_body())
        bad_marker[41] = 3
        with self.assertRaisesRegex(LevelScriptTopLevelFramingError, "segment 1 marker"):
            frame_levelscript_first_record_35_0e_00_anonymous_body(bytes(bad_marker))

        bad_suffix = bytearray(self._anonymous_35_0e_00_body())
        bad_suffix[97] = 1
        with self.assertRaisesRegex(LevelScriptTopLevelFramingError, "fixed suffix"):
            frame_levelscript_first_record_35_0e_00_anonymous_body(bytes(bad_suffix))


if __name__ == "__main__":
    unittest.main()
