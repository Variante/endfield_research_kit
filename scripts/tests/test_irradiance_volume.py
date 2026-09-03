import io
import struct
import unittest

from scripts.game_data.irradiance_volume import (
    IrradianceFormatError,
    INDEX_MAGIC_LEGACY_GACHA,
    INDEX_MAGIC_V3_SCENE,
    REGION_HEADER_SIZE,
    REGION_RECORD_SIZE,
    parse_index_bytes,
    parse_region_bytes,
    validate_region_stream,
)


def fixture(shape=(2, 3, 4), header_word0=4096, header_size=44):
    header = struct.pack(
        "<II6f3I",
        header_word0,
        header_size,
        1.0,
        -2.0,
        3.5,
        4.0,
        5.0,
        6.0,
        *shape,
    )
    body = bytes((i * 17) & 0xFF for i in range(shape[0] * shape[1] * shape[2] * REGION_RECORD_SIZE))
    return header + body


def index_fixture(
    names=("iv_0_0.bytes",),
    magic=INDEX_MAGIC_V3_SCENE,
    opaque=b"opaque-index-tail",
):
    data = bytearray(b"\x00" * 24)
    struct.pack_into("<I", data, 0, magic)
    struct.pack_into("<I", data, 20, len(names))
    for name in names:
        encoded = name.encode("utf-16le")
        data.extend(struct.pack("<I", len(encoded)))
        data.extend(encoded)
    data.extend(opaque)
    return bytes(data)


class IrradianceVolumeTests(unittest.TestCase):
    def test_exact_region_envelope(self):
        data = fixture()
        header = parse_region_bytes(data)
        self.assertEqual(header.header_word0, 4096)
        self.assertEqual(header.header_size, REGION_HEADER_SIZE)
        self.assertEqual(header.shape, (2, 3, 4))
        self.assertEqual(header.record_count, 24)
        self.assertEqual(header.record_bytes, 24 * REGION_RECORD_SIZE)

    def test_streaming_validator_does_not_need_payload_retention(self):
        data = fixture((3, 2, 1))
        header = validate_region_stream(io.BytesIO(data))
        self.assertEqual(header.shape, (3, 2, 1))

    def test_rejects_header_word(self):
        with self.assertRaisesRegex(IrradianceFormatError, "header_word0 mismatch"):
            parse_region_bytes(fixture(header_word0=4097))

    def test_rejects_header_size(self):
        with self.assertRaisesRegex(IrradianceFormatError, "header_size mismatch"):
            parse_region_bytes(fixture(header_size=48))

    def test_rejects_non_finite_header_float(self):
        data = bytearray(fixture())
        struct.pack_into("<f", data, 8, float("nan"))
        with self.assertRaisesRegex(IrradianceFormatError, "non-finite"):
            parse_region_bytes(bytes(data))

    def test_rejects_zero_shape(self):
        with self.assertRaisesRegex(IrradianceFormatError, "shape.x"):
            parse_region_bytes(fixture((0, 2, 1)))

    def test_rejects_dimension_bound(self):
        with self.assertRaisesRegex(IrradianceFormatError, "exceeds bound"):
            parse_region_bytes(fixture((1_000_001, 1, 1)))

    def test_rejects_truncated_header(self):
        with self.assertRaisesRegex(IrradianceFormatError, "short read"):
            parse_region_bytes(b"\x00" * (REGION_HEADER_SIZE - 1))

    def test_rejects_short_records(self):
        with self.assertRaisesRegex(IrradianceFormatError, "short read"):
            parse_region_bytes(fixture()[:-1])

    def test_rejects_trailing_records(self):
        with self.assertRaisesRegex(IrradianceFormatError, "trailing bytes"):
            parse_region_bytes(fixture() + b"x")

    def test_index_filename_table_and_opaque_remainder(self):
        parsed = parse_index_bytes(
            index_fixture(("iv_0_0.bytes", "iv_12_0.bytes"))
        )
        self.assertEqual(parsed.magic, INDEX_MAGIC_V3_SCENE)
        self.assertEqual(parsed.table_offset, 20)
        self.assertEqual(parsed.filename_count, 2)
        self.assertEqual(parsed.filenames, ("iv_0_0.bytes", "iv_12_0.bytes"))
        self.assertEqual(
            parsed.opaque_remainder_length,
            len(b"opaque-index-tail"),
        )

    def test_index_preserves_legacy_magic(self):
        parsed = parse_index_bytes(
            index_fixture(("iv_0_0_0.bytes",), INDEX_MAGIC_LEGACY_GACHA)
        )
        self.assertEqual(parsed.magic, INDEX_MAGIC_LEGACY_GACHA)

    def test_index_rejects_count_overflow(self):
        data = bytearray(index_fixture())
        struct.pack_into("<I", data, 20, 0xFFFFFFFF)
        with self.assertRaisesRegex(IrradianceFormatError, "count overflow"):
            parse_index_bytes(bytes(data))

    def test_index_rejects_truncated_filename(self):
        data = bytearray(b"\x00" * 28)
        struct.pack_into("<I", data, 0, INDEX_MAGIC_V3_SCENE)
        struct.pack_into("<II", data, 20, 1, 24)
        data.extend(b"i\x00v\x00")
        with self.assertRaisesRegex(IrradianceFormatError, "string truncated"):
            parse_index_bytes(bytes(data))

    def test_index_rejects_invalid_utf16(self):
        data = bytearray(b"\x00" * 32)
        struct.pack_into("<I", data, 0, INDEX_MAGIC_V3_SCENE)
        struct.pack_into("<III", data, 20, 1, 2, 0xD800)
        with self.assertRaisesRegex(IrradianceFormatError, "invalid UTF-16LE"):
            parse_index_bytes(bytes(data))

    def test_index_rejects_invalid_filename(self):
        with self.assertRaisesRegex(IrradianceFormatError, "invalid filename"):
            parse_index_bytes(index_fixture(("../evil.bytes",)))

    def test_index_rejects_ambiguous_table_boundary(self):
        first = index_fixture(opaque=b"")
        second = index_fixture(("iv_1_0.bytes",), opaque=b"")
        with self.assertRaisesRegex(IrradianceFormatError, "boundary ambiguous"):
            parse_index_bytes(first + second[20:])


if __name__ == "__main__":
    unittest.main()
