import io
import struct
import unittest

from scripts.game_data.irradiance_volume import (
    IrradianceFormatError,
    REGION_HEADER_SIZE,
    REGION_RECORD_SIZE,
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


if __name__ == "__main__":
    unittest.main()
