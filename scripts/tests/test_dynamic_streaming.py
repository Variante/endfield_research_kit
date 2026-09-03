import struct
import unittest

from scripts.dynamic_streaming import (
    OBSERVED_CHUNK_VERSION,
    OBSERVED_STREAMING_VERSION,
    REJECTED_DATA_MASK_PRESENCE_CANDIDATE,
    decode_length_prefixed_inverted_lz4,
    parse_dynamic_file,
    parse_dynamic_chunk_framing,
)


def _literal_only_inverted_lz4(data: bytes) -> bytes:
    length = len(data)
    tokens = bytearray()
    token = 0x33 if length >= 15 else length
    tokens.append(token)
    if length >= 15:
        remaining = length - 15
        while remaining >= 255:
            tokens.append(255)
            remaining -= 255
        tokens.append(remaining)
    tokens.extend(data)
    return bytes(tokens)


def _chunk_fixture() -> bytes:
    data = bytearray(332)
    struct.pack_into("<I", data, 0, 32)
    struct.pack_into("<H", data, 8, 14)
    struct.pack_into("<H", data, 10, 28)
    for index, relative in enumerate((4, 12, 16, 20, 24)):
        struct.pack_into("<H", data, 12 + index * 2, relative)
    struct.pack_into("<i", data, 32, 24)
    struct.pack_into("<Q", data, 36, OBSERVED_CHUNK_VERSION)
    struct.pack_into("<i", data, 44, OBSERVED_STREAMING_VERSION)
    struct.pack_into("<I", data, 48, 123)
    struct.pack_into("<I", data, 52, 12)
    struct.pack_into("<I", data, 56, 204)
    struct.pack_into("<I", data, 64, 1)
    struct.pack_into("<I", data, 68, 232)
    struct.pack_into("<I", data, 174, 126)
    struct.pack_into("<H", data, 176, 32)
    # The SingleGrid vtable starts at 174, so its first field entry is at
    # vtable + 4 (178).  Keep the unknown vector fields absent in this focused
    # fixture; a missing FlatBuffer vector is the canonical empty value.
    for index, relative in ((0, 4), (60, 12)):
        struct.pack_into("<H", data, 178 + index * 2, relative)
    struct.pack_into("<I", data, 260, 0)
    struct.pack_into("<i", data, 300, 126)
    return bytes(data)


def _root_fixture(field_count: int, object_size: int) -> bytes:
    """Small exact-shape table fixture; auxiliary fields remain unnamed."""

    data = bytearray(96)
    root = 32
    vtable = 4
    struct.pack_into("<I", data, 0, root)
    struct.pack_into("<HH", data, vtable, 4 + field_count * 2, object_size)
    struct.pack_into("<i", data, root, root - vtable)
    for index in range(field_count):
        struct.pack_into("<H", data, vtable + 4 + index * 2, 4 + index * 4)
    return bytes(data[: root + object_size])


class DynamicStreamingTests(unittest.TestCase):
    def test_decodes_exact_length_prefixed_envelope(self):
        clear = _chunk_fixture()
        packed = struct.pack("<I", len(clear)) + _literal_only_inverted_lz4(clear)
        self.assertEqual(decode_length_prefixed_inverted_lz4(packed), clear)

    def test_parses_observed_chunk_root_and_grid_shape(self):
        parsed = parse_dynamic_chunk_framing(_chunk_fixture())
        self.assertEqual(parsed["Version"], OBSERVED_CHUNK_VERSION)
        self.assertEqual(parsed["StreamingVersion"], OBSERVED_STREAMING_VERSION)
        self.assertEqual(parsed["GridsLength"], 1)
        self.assertEqual(parsed["SingleGridFieldCount"], 61)
        self.assertEqual(parsed["DataMaskInference"]["status"], "rejected")
        self.assertEqual(parsed["DataMaskInference"]["candidate"], REJECTED_DATA_MASK_PRESENCE_CANDIDATE)

    def test_rejects_truncated_envelope(self):
        with self.assertRaisesRegex(ValueError, "lacks size"):
            decode_length_prefixed_inverted_lz4(b"\x01\x00\x00\x00")

    def test_rejects_wrong_grid_field_count(self):
        data = bytearray(_chunk_fixture())
        struct.pack_into("<H", data, 174, 8)
        with self.assertRaisesRegex(ValueError, "SingleGrid"):
            parse_dynamic_chunk_framing(bytes(data))

    def test_rejects_unobserved_chunk_version(self):
        data = bytearray(_chunk_fixture())
        struct.pack_into("<Q", data, 36, OBSERVED_CHUNK_VERSION + 1)
        with self.assertRaisesRegex(ValueError, "unsupported dynamic chunk Version"):
            parse_dynamic_chunk_framing(bytes(data))

    def test_rejects_unobserved_streaming_version(self):
        data = bytearray(_chunk_fixture())
        struct.pack_into("<i", data, 44, OBSERVED_STREAMING_VERSION + 1)
        with self.assertRaisesRegex(ValueError, "unsupported dynamic chunk StreamingVersion"):
            parse_dynamic_chunk_framing(bytes(data))

    def test_validates_total_string_payloads(self):
        data = bytearray(_chunk_fixture())
        data.extend(b"\x00" * 24)
        struct.pack_into("<I", data, 56, 284)
        struct.pack_into("<I", data, 340, 1)
        struct.pack_into("<I", data, 344, 4)
        struct.pack_into("<I", data, 348, 2)
        data[352:355] = b"ok\x00"
        self.assertEqual(parse_dynamic_chunk_framing(bytes(data))["TotalStrLength"], 1)

        data[354] = 1
        with self.assertRaisesRegex(ValueError, "NUL terminator"):
            parse_dynamic_chunk_framing(bytes(data))

    def test_parses_all_five_observed_dynamic_file_kinds(self):
        compressed = struct.pack("<I", 72) + _literal_only_inverted_lz4(_root_fixture(8, 40))
        for kind in ("init", "streaming"):
            parsed = parse_dynamic_file(kind, compressed)
            self.assertEqual(parsed["kind"], kind)
            self.assertEqual(parsed["root"]["fieldCount"], 8)
            self.assertEqual(parsed["decodedBytes"], 72)

        for kind, fields, size in (("stream_area", 7, 52), ("version", 3, 16)):
            parsed = parse_dynamic_file(kind, _root_fixture(fields, size))
            self.assertEqual(parsed["root"]["fieldCount"], fields)
            self.assertEqual(parsed["root"]["objectSize"], size)

        parsed = parse_dynamic_file("main", _chunk_fixture())
        self.assertEqual(parsed["Version"], OBSERVED_CHUNK_VERSION)

    def test_rejects_compression_for_raw_auxiliary_kind(self):
        packed = struct.pack("<I", 72) + _literal_only_inverted_lz4(_root_fixture(3, 16))
        with self.assertRaisesRegex(ValueError, "root offset"):
            parse_dynamic_file("version", packed)

    def test_rejects_auxiliary_root_shape_mismatch(self):
        with self.assertRaisesRegex(ValueError, "stream_area root has"):
            parse_dynamic_file("stream_area", _root_fixture(3, 16))

    def test_rejects_total_string_invalid_utf8(self):
        data = bytearray(_chunk_fixture())
        data.extend(b"\x00" * 24)
        struct.pack_into("<I", data, 56, 284)
        struct.pack_into("<I", data, 340, 1)
        struct.pack_into("<I", data, 344, 4)
        struct.pack_into("<I", data, 348, 2)
        data[352:355] = b"\xff\x00\x00"
        with self.assertRaisesRegex(ValueError, "strict UTF-8"):
            parse_dynamic_chunk_framing(bytes(data))


if __name__ == "__main__":
    unittest.main()
