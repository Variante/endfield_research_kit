import unittest

from scripts.terrain_tret import FIXED_BODY_PREFIX_SIZE, parse_tret_record


def _literal_only_inverted_lz4(data: bytes) -> bytes:
    length = len(data)
    if length < 15:
        return bytes([length]) + data
    return bytes([0x33, length - 15]) + data


class TerrainTretTests(unittest.TestCase):
    def test_parses_only_observed_framing(self):
        words = (34, 34, 1, 6, 2312, 0)
        body_prefix = b"TRET" + (1).to_bytes(4, "little") + b"".join(
            value.to_bytes(2, "little") for value in words
        )
        raw = body_prefix + b"opaque"

        parsed = parse_tret_record(raw)

        self.assertEqual(parsed.storage_mode, "raw")
        self.assertIsNone(parsed.declared_decoded_length)
        self.assertEqual(parsed.encoded_prefix, b"")
        self.assertEqual(parsed.decoded_length, len(raw))
        self.assertEqual(parsed.body_version_u32le, 1)
        self.assertEqual(parsed.body_u16le_offsets_8_18, words)
        self.assertEqual(parsed.body_fixed_prefix, body_prefix[:FIXED_BODY_PREFIX_SIZE])
        self.assertEqual(parsed.opaque_payload, b"opaque")

    def test_decodes_compressed_envelope_before_parsing(self):
        words = (34, 34, 1, 6, 2312, 0)
        clear = b"TRET" + (1).to_bytes(4, "little") + b"".join(
            value.to_bytes(2, "little") for value in words
        ) + b"opaque"
        packed = len(clear).to_bytes(4, "little") + _literal_only_inverted_lz4(clear)

        parsed = parse_tret_record(packed)

        self.assertEqual(parsed.storage_mode, "inverted_lz4")
        self.assertEqual(parsed.declared_decoded_length, len(clear))
        self.assertEqual(parsed.encoded_prefix, len(clear).to_bytes(4, "little"))
        self.assertEqual(parsed.decoded_length, len(clear))
        self.assertEqual(parsed.body_u16le_offsets_8_18, words)
        self.assertEqual(parsed.opaque_payload, b"opaque")

    def test_rejects_decoded_payload_without_magic(self):
        clear = b"not-a-terrain-record" + b"\x00"
        packed = len(clear).to_bytes(4, "little") + _literal_only_inverted_lz4(clear)
        with self.assertRaisesRegex(ValueError, "does not begin with TRET"):
            parse_tret_record(packed)

    def test_rejects_compressed_source_with_trailing_bytes(self):
        clear = b"TRET" + b"\x00" * (FIXED_BODY_PREFIX_SIZE - 4)
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


if __name__ == "__main__":
    unittest.main()
