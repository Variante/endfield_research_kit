from __future__ import annotations

import struct
import unittest

from scripts.game_data.memorypack.npc_montage import (
    NPC_MONTAGE_CLIP_INFO_MEMBER_COUNT,
    NPC_MONTAGE_DATA_MEMBER_COUNT,
    NPC_MONTAGE_MEMBER3_INNER_RECORD_MEMBER_COUNT,
    NPC_MONTAGE_MEMBER3_NESTED_OBJECT_MEMBER_COUNT,
    NPC_MONTAGE_MEMBER3_RECORD_MEMBER_COUNT,
    NPC_MONTAGE_MEMBER18_RECORD_MEMBER_COUNT,
    NPC_MONTAGE_ROOT_MEMBER_COUNT,
    NpcMontageFramingError,
    decode_npc_montage_memorypack,
    frame_npc_montage,
)


def _utf8(value: str | None) -> bytes:
    if value is None:
        return struct.pack("<I", 0xFFFFFFFF)
    raw = value.encode("utf-8")
    return struct.pack("<I", len(raw)) + raw


def _member3_inner_record(
    value_a: str = "P_fixture",
    value_b: str = "",
    value_c: str = "Root/fixture",
) -> bytes:
    return b"".join(
        [
            bytes([NPC_MONTAGE_MEMBER3_INNER_RECORD_MEMBER_COUNT]),
            _utf8(value_a),
            b"\x00" * 20,
            _utf8(value_b),
            _utf8(value_c),
        ]
    )


def _member3_record(
    value_a: str = "",
    value_b: str = "",
    inner_records: list[bytes] | None = None,
) -> bytes:
    nested = inner_records or []
    return b"".join(
        [
            bytes([NPC_MONTAGE_MEMBER3_RECORD_MEMBER_COUNT]),
            _utf8(value_a),
            b"\x00" * 10,
            bytes([NPC_MONTAGE_MEMBER3_NESTED_OBJECT_MEMBER_COUNT]),
            b"\x00" * 9,
            _utf8(value_b),
            struct.pack("<I", len(nested)),
            *nested,
            b"\x00" * 38,
        ]
    )


def _fixture(
    clip_name: str | None = "A_actor_fixture_idle_loop",
    member3_records: list[bytes] | None = None,
    member18_records: list[tuple[int, int, float, float, float]] | None = None,
) -> bytes:
    out = bytearray([NPC_MONTAGE_ROOT_MEMBER_COUNT])
    out.extend(struct.pack("<i", 1))
    out.append(NPC_MONTAGE_DATA_MEMBER_COUNT)
    out.extend(b"\x00\x00")
    if clip_name is None:
        out.append(0xFF)
    else:
        raw = clip_name.encode("utf-8")
        out.append(NPC_MONTAGE_CLIP_INFO_MEMBER_COUNT)
        out.extend(struct.pack("<fiq", 0.0, 0, 0))
        out.extend(b"\x00" * 16)
        out.extend(struct.pack("<I", len(raw)))
        out.extend(raw)
        out.extend(struct.pack("<ff", 0.0, 0.0))
    dynamic_records = member3_records or []
    out.extend(struct.pack("<I", len(dynamic_records)))
    for record in dynamic_records:
        out.extend(record)
    out.extend(b"\x00\x00")
    out.extend(b"\x00" * 36)
    out.append(0)
    out.extend(struct.pack("<ffii", 0.3, 0.15, 100, 10))
    out.extend(b"\x00" * (8 + 16))
    out.extend(struct.pack("<f", 100.0))
    out.extend(b"\x00" * 36)
    out.extend(struct.pack("<i", 0))
    out.extend(b"\x00" * 32)
    records = member18_records or []
    out.extend(struct.pack("<I", len(records)))
    for record in records:
        out.append(NPC_MONTAGE_MEMBER18_RECORD_MEMBER_COUNT)
        out.extend(struct.pack("<IIfff", *record))
    out.extend(struct.pack("<if", 1, 0.0))
    out.extend(b"\x00" * (36 + 16 + 8))
    out.extend(struct.pack("<i", 1494188745))
    return bytes(out)


def _member3_count_offset(clip_name: str = "A_actor_fixture_idle_loop") -> int:
    return 45 + len(clip_name.encode("utf-8")) + 8


class NpcMontageMemoryPackTests(unittest.TestCase):
    def test_anonymous_utf8_shape_consumes_exactly_to_eof(self) -> None:
        payload = _fixture()
        decoded = frame_npc_montage(payload)

        self.assertEqual(
            "exact_current_npc_montage_empty_collection_frame",
            decoded["status"],
        )
        self.assertEqual(len(payload), decoded["bytesConsumed"])
        self.assertEqual(
            "A_actor_fixture_idle_loop", decoded["clipInfo"]["anonymousUtf8"]
        )
        self.assertEqual(3, decoded["serializedMemberCount"])
        self.assertEqual(24, decoded["nestedDataMemberCount"])

    def test_null_clip_shape_also_consumes_exactly_to_eof(self) -> None:
        payload = _fixture(None)
        decoded = frame_npc_montage(payload)

        self.assertEqual(len(payload), decoded["bytesConsumed"])
        self.assertTrue(decoded["clipInfo"]["isNull"])
        self.assertIsNone(decoded["clipInfo"]["anonymousUtf8"])

    def test_route_is_scoped_to_npc_montage_new(self) -> None:
        payload = _fixture()
        path = "Data/Json/NPC/MontageJson/MontageNew/Generic/test.json"
        routed = decode_npc_montage_memorypack(path, payload, len(payload))

        self.assertIsNotNone(routed)
        self.assertEqual("NPCMontageJson", routed["subtype"])
        self.assertIsNone(
            decode_npc_montage_memorypack("Data/Json/SkillData/test.json", payload)
        )
        self.assertIsNone(
            decode_npc_montage_memorypack(
                "prefixData/Json/NPC/MontageJson/MontageNew/test.json", payload
            )
        )

    def test_truncated_and_trailing_payloads_fail_closed(self) -> None:
        payload = _fixture()
        with self.assertRaisesRegex(NpcMontageFramingError, "truncated"):
            frame_npc_montage(payload[:-1])
        with self.assertRaisesRegex(NpcMontageFramingError, "trailing-bytes"):
            frame_npc_montage(payload + b"\x00")

    def test_member_count_drift_fails_closed(self) -> None:
        payload = bytearray(_fixture())
        payload[5] = NPC_MONTAGE_DATA_MEMBER_COUNT - 1
        with self.assertRaisesRegex(NpcMontageFramingError, "memberCount"):
            frame_npc_montage(bytes(payload))

    def test_member3_counted_records_consume_exactly_to_eof(self) -> None:
        records = [
            _member3_record(
                "P_fixture",
                "spark",
                [_member3_inner_record()],
            ),
            _member3_record("P_second", "smoke"),
            _member3_record("", ""),
            _member3_record("P_fourth", "trail"),
        ]
        for count in (1, 2, 3, 4):
            with self.subTest(count=count):
                payload = _fixture(member3_records=records[:count])
                decoded = frame_npc_montage(payload)
                self.assertEqual(
                    "exact_current_npc_montage_member3_counted_frame",
                    decoded["status"],
                )
                self.assertEqual(len(payload), decoded["bytesConsumed"])
                self.assertEqual(count, len(decoded["member3Records"]))
                self.assertTrue(
                    all(
                        record["memberCount"]
                        == NPC_MONTAGE_MEMBER3_RECORD_MEMBER_COUNT
                        for record in decoded["member3Records"]
                    )
                )
        first = frame_npc_montage(
            _fixture(member3_records=records[:1])
        )["member3Records"][0]
        self.assertEqual(
            NPC_MONTAGE_MEMBER3_NESTED_OBJECT_MEMBER_COUNT,
            first["nestedObjectMemberCount"],
        )
        self.assertEqual(1, len(first["innerRecords"]))
        self.assertEqual(
            NPC_MONTAGE_MEMBER3_INNER_RECORD_MEMBER_COUNT,
            first["innerRecords"][0]["memberCount"],
        )

    def test_member3_malformed_markers_and_counts_fail_closed(self) -> None:
        payload = _fixture(
            member3_records=[
                _member3_record(
                    "P_fixture",
                    "spark",
                    [_member3_inner_record()],
                )
            ]
        )
        decoded = frame_npc_montage(payload)
        record = decoded["member3Records"][0]
        count_offset = _member3_count_offset()

        malformed = bytearray(payload)
        malformed[record["startOffset"]] = NPC_MONTAGE_MEMBER3_RECORD_MEMBER_COUNT - 1
        with self.assertRaisesRegex(NpcMontageFramingError, "memberCount"):
            frame_npc_montage(bytes(malformed))

        malformed = bytearray(payload)
        nested_marker_offset = record["anonymousFixedRanges"][0]["endOffset"]
        malformed[nested_marker_offset] = (
            NPC_MONTAGE_MEMBER3_NESTED_OBJECT_MEMBER_COUNT - 1
        )
        with self.assertRaisesRegex(NpcMontageFramingError, "nestedObject.memberCount"):
            frame_npc_montage(bytes(malformed))

        malformed = bytearray(payload)
        malformed[record["innerCountOffset"] + 4] = (
            NPC_MONTAGE_MEMBER3_INNER_RECORD_MEMBER_COUNT - 1
        )
        with self.assertRaisesRegex(NpcMontageFramingError, "inner.*memberCount"):
            frame_npc_montage(bytes(malformed))

        wrong_count = bytearray(payload)
        struct.pack_into("<I", wrong_count, count_offset, 100)
        with self.assertRaisesRegex(NpcMontageFramingError, "count-envelope"):
            frame_npc_montage(bytes(wrong_count))

        inner_overrun = bytearray(payload)
        struct.pack_into("<I", inner_overrun, record["innerCountOffset"], 0xFFFFFFFF)
        with self.assertRaisesRegex(NpcMontageFramingError, "count-overrun"):
            frame_npc_montage(bytes(inner_overrun))

    def test_member3_invalid_utf8_and_truncation_fail_closed(self) -> None:
        payload = _fixture(member3_records=[_member3_record("X", "")])
        decoded = frame_npc_montage(payload)
        record = decoded["member3Records"][0]

        malformed = bytearray(payload)
        malformed[record["startOffset"] + 5] = 0xFF
        with self.assertRaisesRegex(NpcMontageFramingError, "invalid-utf8"):
            frame_npc_montage(bytes(malformed))

        truncated = payload[: record["endOffset"] - 1]
        with self.assertRaisesRegex(NpcMontageFramingError, "truncated"):
            frame_npc_montage(truncated)

    def test_member18_counted_records_consume_exactly_to_eof(self) -> None:
        records = [
            (0xA6E99673, 0xDB923E88, 0.0, 0.25, 0.85),
            (0xA785FD3A, 0xA6E99673, 0.0, 0.25, 0.85),
            (0xF75C5933, 0xA785FD3A, 0.0, 0.25, 0.85),
            (0xA785FD3A, 0xF75C5933, 0.0, 0.25, 0.85),
        ]
        for count in (1, 2, 4):
            with self.subTest(count=count):
                payload = _fixture(member18_records=records[:count])
                decoded = frame_npc_montage(payload)
                self.assertEqual(
                    "exact_current_npc_montage_member18_counted_frame",
                    decoded["status"],
                )
                self.assertEqual(len(payload), decoded["bytesConsumed"])
                self.assertEqual(count, len(decoded["member18Records"]))
                self.assertTrue(
                    all(
                        record["memberCount"]
                        == NPC_MONTAGE_MEMBER18_RECORD_MEMBER_COUNT
                        for record in decoded["member18Records"]
                    )
                )

    def test_member3_and_member18_can_both_be_nonempty(self) -> None:
        payload = _fixture(
            member3_records=[_member3_record("P_fixture", "spark")],
            member18_records=[(0xA6E99673, 0xDB923E88, 0.0, 0.25, 0.85)],
        )
        decoded = frame_npc_montage(payload)

        self.assertEqual(len(payload), decoded["bytesConsumed"])
        self.assertEqual(1, len(decoded["member3Records"]))
        self.assertEqual(1, len(decoded["member18Records"]))

    def test_member18_truncated_trailing_and_malformed_records_fail_closed(self) -> None:
        records = [(0xA6E99673, 0xDB923E88, 0.0, 0.25, 0.85)]
        payload = _fixture(member18_records=records)
        record_offset = len(payload) - (21 + 72)

        with self.assertRaisesRegex(NpcMontageFramingError, "truncated"):
            frame_npc_montage(payload[: record_offset + 20])
        with self.assertRaisesRegex(NpcMontageFramingError, "trailing-bytes"):
            frame_npc_montage(payload + b"\x00")

        malformed = bytearray(payload)
        malformed[record_offset] = NPC_MONTAGE_MEMBER18_RECORD_MEMBER_COUNT - 1
        with self.assertRaisesRegex(NpcMontageFramingError, "memberCount"):
            frame_npc_montage(bytes(malformed))

        wrong_count = bytearray(payload)
        struct.pack_into("<I", wrong_count, record_offset - 4, 2)
        with self.assertRaisesRegex(NpcMontageFramingError, "count-envelope"):
            frame_npc_montage(bytes(wrong_count))

    def test_clip_record_drift_and_unobserved_string_prefix_fail_closed(self) -> None:
        payload = bytearray(_fixture())
        payload[8] = NPC_MONTAGE_CLIP_INFO_MEMBER_COUNT - 1
        with self.assertRaisesRegex(NpcMontageFramingError, "memberCount"):
            frame_npc_montage(bytes(payload))

        payload = bytearray(_fixture("not-an-animation-id"))
        with self.assertRaisesRegex(NpcMontageFramingError, "unexpected-current-prefix"):
            frame_npc_montage(bytes(payload))

    def test_invalid_boolean_fails_closed(self) -> None:
        payload = bytearray(_fixture())
        payload[6] = 2
        with self.assertRaisesRegex(NpcMontageFramingError, "invalid-bool"):
            frame_npc_montage(bytes(payload))

    def test_outer_size_mismatch_fails_closed(self) -> None:
        payload = _fixture()
        with self.assertRaisesRegex(NpcMontageFramingError, "outer-size-mismatch"):
            decode_npc_montage_memorypack(
                "Data/Json/NPC/MontageJson/MontageNew/test.json",
                payload,
                len(payload) + 1,
            )


if __name__ == "__main__":
    unittest.main()
