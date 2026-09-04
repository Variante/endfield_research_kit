import unittest

from scripts.terrain_tret import FIXED_BODY_PREFIX_SIZE, parse_tret_record


def _literal_only_inverted_lz4(data: bytes) -> bytes:
    length = len(data)
    if length < 15:
        return bytes([length]) + data
    remaining = length - 15
    extension = bytearray()
    while remaining >= 255:
        extension.append(255)
        remaining -= 255
    extension.append(remaining)
    return bytes([0x33]) + bytes(extension) + data


class TerrainTretTests(unittest.TestCase):
    def test_parses_only_observed_framing(self):
        opaque = b"\x5a" * 2312
        words = (34, 34, 1, 6, len(opaque), 0)
        body_prefix = b"TRET" + (1).to_bytes(4, "little") + b"".join(
            value.to_bytes(2, "little") for value in words
        )
        raw = body_prefix + opaque

        parsed = parse_tret_record(raw)

        self.assertEqual(parsed.storage_mode, "raw")
        self.assertIsNone(parsed.declared_decoded_length)
        self.assertEqual(parsed.encoded_prefix, b"")
        self.assertEqual(parsed.decoded_length, len(raw))
        self.assertEqual(parsed.body_version_u32le, 1)
        self.assertEqual(parsed.body_u16le_offsets_8_18, words)
        self.assertEqual(parsed.body_payload_length_u32le, len(opaque))
        self.assertEqual(parsed.body_fixed_prefix, body_prefix[:FIXED_BODY_PREFIX_SIZE])
        self.assertEqual(parsed.opaque_payload, opaque)
        self.assertEqual("exact_anonymous_record_tiling", parsed.anonymous_tiling_status)
        self.assertEqual(1, len(parsed.anonymous_record_ranges))
        record_range = parsed.anonymous_record_ranges[0]
        self.assertEqual((20, 2332), (
            record_range.start_offset,
            record_range.end_offset,
        ))
        self.assertEqual(1156, record_range.record_count)
        self.assertEqual(2, record_range.record_stride)

    def test_decodes_compressed_envelope_before_parsing(self):
        opaque = b"\x5a" * 2312
        words = (34, 34, 1, 6, len(opaque), 0)
        clear = b"TRET" + (1).to_bytes(4, "little") + b"".join(
            value.to_bytes(2, "little") for value in words
        ) + opaque
        packed = len(clear).to_bytes(4, "little") + _literal_only_inverted_lz4(clear)

        parsed = parse_tret_record(packed)

        self.assertEqual(parsed.storage_mode, "inverted_lz4")
        self.assertEqual(parsed.declared_decoded_length, len(clear))
        self.assertEqual(parsed.encoded_prefix, len(clear).to_bytes(4, "little"))
        self.assertEqual(parsed.decoded_length, len(clear))
        self.assertEqual(parsed.body_u16le_offsets_8_18, words)
        self.assertEqual(parsed.body_payload_length_u32le, len(opaque))
        self.assertEqual(parsed.opaque_payload, opaque)

    def test_tiles_exact_multi_range_shape(self):
        payload_length = 1398101
        words = (
            1024,
            1024,
            11,
            5,
            payload_length & 0xFFFF,
            payload_length >> 16,
        )
        body = (
            b"TRET"
            + (1).to_bytes(4, "little")
            + b"".join(value.to_bytes(2, "little") for value in words)
            + b"\x00" * payload_length
        )
        parsed = parse_tret_record(body)
        ranges = parsed.anonymous_record_ranges
        self.assertEqual("exact_anonymous_record_tiling", parsed.anonymous_tiling_status)
        self.assertEqual(11, len(ranges))
        self.assertEqual([4, 1], [item.record_count for item in ranges[-2:]])
        self.assertEqual(len(body), ranges[-1].end_offset)

    def test_tiles_exact_block_grouped_multi_range_shape(self):
        payload_length = 1398128
        words = (
            1024,
            1024,
            11,
            108,
            payload_length & 0xFFFF,
            payload_length >> 16,
        )
        body = (
            b"TRET"
            + (1).to_bytes(4, "little")
            + b"".join(value.to_bytes(2, "little") for value in words)
            + b"\x5a" * payload_length
        )
        parsed = parse_tret_record(body)
        ranges = parsed.anonymous_record_ranges
        self.assertEqual("exact_anonymous_record_tiling", parsed.anonymous_tiling_status)
        self.assertEqual(11, len(ranges))
        self.assertEqual(
            (20, 20 + 1_048_576, 256, 256, 4, 65_536, 16),
            (
                ranges[0].start_offset,
                ranges[0].end_offset,
                ranges[0].axis0_units,
                ranges[0].axis1_units,
                ranges[0].axis_grouping_divisor,
                ranges[0].record_count,
                ranges[0].record_stride,
            ),
        )
        self.assertEqual((2, 2), (
            ranges[-2].source_axis0_units,
            ranges[-2].source_axis1_units,
        ))
        self.assertEqual((1, 1), (
            ranges[-1].source_axis0_units,
            ranges[-1].source_axis1_units,
        ))
        self.assertEqual([16, 16], [
            item.end_offset - item.start_offset for item in ranges[-2:]
        ])
        self.assertEqual(len(body), ranges[-1].end_offset)

    def test_tiles_second_block_grouped_layout_word(self):
        payload_length = 1_398_128
        words = (1024, 1024, 11, 109, payload_length & 0xFFFF, payload_length >> 16)
        body = (
            b"TRET"
            + (1).to_bytes(4, "little")
            + b"".join(value.to_bytes(2, "little") for value in words)
            + b"\x5a" * payload_length
        )
        parsed = parse_tret_record(body)
        self.assertEqual(11, len(parsed.anonymous_record_ranges))
        self.assertEqual(
            payload_length,
            sum(
                item.end_offset - item.start_offset
                for item in parsed.anonymous_record_ranges
            ),
        )

    def test_block_grouped_single_range_uses_block_units(self):
        payload_length = 17_424
        words = (132, 132, 1, 100, payload_length, 0)
        body = (
            b"TRET"
            + (1).to_bytes(4, "little")
            + b"".join(value.to_bytes(2, "little") for value in words)
            + b"\x5a" * payload_length
        )
        record_range = parse_tret_record(body).anonymous_record_ranges[0]
        self.assertEqual((33, 33, 1_089, 16), (
            record_range.axis0_units,
            record_range.axis1_units,
            record_range.record_count,
            record_range.record_stride,
        ))

    def test_rejects_decoded_payload_without_magic(self):
        clear = b"not-a-terrain-record" + b"\x00"
        packed = len(clear).to_bytes(4, "little") + _literal_only_inverted_lz4(clear)
        with self.assertRaisesRegex(ValueError, "does not begin with TRET"):
            parse_tret_record(packed)

    def test_rejects_compressed_source_with_trailing_bytes(self):
        clear = b"TRET" + (1).to_bytes(4, "little") + b"\x00" * 12
        packed = len(clear).to_bytes(4, "little") + _literal_only_inverted_lz4(clear) + b"trailing"
        with self.assertRaises(ValueError):
            parse_tret_record(packed)

    def test_rejects_missing_magic(self):
        with self.assertRaises(ValueError):
            parse_tret_record(b"not-a-terrain-record")

    def test_rejects_short_body(self):
        with self.assertRaisesRegex(ValueError, "too short"):
            parse_tret_record(b"TRET" + b"\x00" * (FIXED_BODY_PREFIX_SIZE - 5))

    def test_rejects_unobserved_version(self):
        body = b"TRET" + (2).to_bytes(4, "little") + b"\x00" * 12
        with self.assertRaisesRegex(ValueError, "unsupported TRET body version"):
            parse_tret_record(body)

    def test_rejects_truncated_opaque_body(self):
        prefix = (
            b"TRET"
            + (1).to_bytes(4, "little")
            + b"\x00" * 8
            + (7).to_bytes(4, "little")
        )
        with self.assertRaisesRegex(
            ValueError, "payload length mismatch: declared 7, actual 6"
        ):
            parse_tret_record(prefix + b"opaque")

    def test_rejects_trailing_opaque_body(self):
        prefix = (
            b"TRET"
            + (1).to_bytes(4, "little")
            + b"\x00" * 8
            + (5).to_bytes(4, "little")
        )
        with self.assertRaisesRegex(
            ValueError, "payload length mismatch: declared 5, actual 6"
        ):
            parse_tret_record(prefix + b"opaque")

    def test_rejects_malformed_oversized_body_length(self):
        prefix = (
            b"TRET"
            + (1).to_bytes(4, "little")
            + b"\x00" * 8
            + (0xFFFFFFFF).to_bytes(4, "little")
        )
        with self.assertRaisesRegex(
            ValueError, "payload length mismatch: declared 4294967295, actual 0"
        ):
            parse_tret_record(prefix)

    def test_rejects_truncated_anonymous_tiling_with_valid_outer_length(self):
        opaque = b"\x00" * 2311
        words = (34, 34, 1, 6, len(opaque), 0)
        body = (
            b"TRET"
            + (1).to_bytes(4, "little")
            + b"".join(value.to_bytes(2, "little") for value in words)
            + opaque
        )
        with self.assertRaisesRegex(ValueError, "range 0 exceeds decoded body"):
            parse_tret_record(body)

    def test_rejects_trailing_anonymous_tiling_with_valid_outer_length(self):
        opaque = b"\x00" * 2313
        words = (34, 34, 1, 6, len(opaque), 0)
        body = (
            b"TRET"
            + (1).to_bytes(4, "little")
            + b"".join(value.to_bytes(2, "little") for value in words)
            + opaque
        )
        with self.assertRaisesRegex(ValueError, "ranges end at 2332.*ends at 2333"):
            parse_tret_record(body)

    def test_rejects_malformed_anonymous_layout_words_and_axes(self):
        def body(words: tuple[int, int, int, int, int, int]) -> bytes:
            return (
                b"TRET"
                + (1).to_bytes(4, "little")
                + b"".join(value.to_bytes(2, "little") for value in words)
            )

        with self.assertRaisesRegex(ValueError, "axes must be positive"):
            parse_tret_record(body((0, 1, 1, 6, 0, 0)))
        with self.assertRaisesRegex(ValueError, "unsupported TRET anonymous layout"):
            parse_tret_record(body((34, 34, 2, 6, 0, 0)))

    def test_rejects_truncated_block_grouped_layout_with_valid_outer_length(self):
        payload_length = 1398127
        words = (
            1024,
            1024,
            11,
            108,
            payload_length & 0xFFFF,
            payload_length >> 16,
        )
        body = (
            b"TRET"
            + (1).to_bytes(4, "little")
            + b"".join(value.to_bytes(2, "little") for value in words)
            + b"\x00" * payload_length
        )
        with self.assertRaisesRegex(ValueError, "anonymous range 10 exceeds decoded body"):
            parse_tret_record(body)


if __name__ == "__main__":
    unittest.main()
