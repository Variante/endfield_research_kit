from __future__ import annotations

import struct
import unittest

from scripts.game_data.memorypack.npc_montage import (
    NPC_MONTAGE_CLIP_INFO_MEMBER_COUNT,
    NPC_MONTAGE_DATA_MEMBER_COUNT,
    NPC_MONTAGE_MEMBER18_RECORD_MEMBER_COUNT,
    NPC_MONTAGE_ROOT_MEMBER_COUNT,
    NpcMontageFramingError,
    decode_npc_montage_memorypack,
    frame_npc_montage,
)


def _fixture(
    clip_name: str | None = "A_actor_fixture_idle_loop",
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
    out.extend(struct.pack("<I", 0))
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

    def test_nonempty_collection_is_explicitly_unsupported(self) -> None:
        payload = bytearray(_fixture())
        name_length = struct.unpack_from("<I", payload, 41)[0]
        dynamic_count_offset = 45 + name_length + 8
        struct.pack_into("<I", payload, dynamic_count_offset, 1)
        with self.assertRaisesRegex(
            NpcMontageFramingError,
            "unsupported-nonempty-collection",
        ):
            frame_npc_montage(bytes(payload))

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
