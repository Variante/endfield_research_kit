import struct
import unittest

from scripts.game_data.extend_data_binary import (
    BinaryFormatError,
    parse_fac_bone_trs,
    parse_string_path_hash,
)


def _string_path_fixture() -> bytes:
    count = 4
    str_data_offset = 8 + count * 24
    data = bytearray(str_data_offset)
    struct.pack_into("<II", data, 0, str_data_offset, count)
    # Two non-empty slots and two empty slots.  Bucket records are 16 bytes.
    struct.pack_into("<II", data, 8, 40, 1)
    struct.pack_into("<II", data, 16, 56, 1)
    struct.pack_into("<II", data, 24, 0, 0)
    struct.pack_into("<II", data, 32, 0, 0)
    struct.pack_into("<IQI", data, 40, 0, 0x1111, 0)
    # "one" starts 14 bytes after the first string-record prefix.
    struct.pack_into("<IQI", data, 56, 7, 0x2222, 14)
    for value in ("zero", "one", "two", "three"):
        encoded = value.encode("utf-16-le")
        data += struct.pack("<I", len(encoded)) + encoded + b"\0\0"
    return bytes(data)


def _fac_fixture() -> bytes:
    data = bytearray(960)
    # Physical observed layout is <bone_count, bones_offset, hash_key>.
    struct.pack_into("<IIQ", data, 768, 1, 800, 0xAAAA)
    struct.pack_into("<IIQ", data, 784, 1, 816, 0xBBBB)
    struct.pack_into("<QII", data, 800, 0x101, 1, 832)
    struct.pack_into("<QII", data, 816, 0x202, 1, 896)
    return bytes(data)


class StringPathHashTests(unittest.TestCase):
    def test_positive_fixture(self) -> None:
        result = parse_string_path_hash(_string_path_fixture(), source="fixture")
        self.assertEqual(result.count, 4)
        self.assertEqual(result.bucket_count, 2)
        self.assertEqual(result.referenced_string_count, 2)
        self.assertEqual(result.raw_key_offset_nonzero_count, 1)
        self.assertEqual(result.consumed_bytes, len(_string_path_fixture()))

    def test_header_must_match_observed_framing(self) -> None:
        data = bytearray(_string_path_fixture())
        struct.pack_into("<I", data, 0, 100)
        with self.assertRaises(BinaryFormatError):
            parse_string_path_hash(bytes(data), source="bad-header")

    def test_bucket_path_must_reference_a_string_record(self) -> None:
        data = bytearray(_string_path_fixture())
        struct.pack_into("<I", data, 40 + 12, 0xFFFF)
        with self.assertRaises(BinaryFormatError):
            parse_string_path_hash(bytes(data), source="bad-path")

    def test_bucket_ranges_must_not_overlap(self) -> None:
        data = bytearray(_string_path_fixture())
        struct.pack_into("<I", data, 16, 48)
        with self.assertRaises(BinaryFormatError):
            parse_string_path_hash(bytes(data), source="overlapping-buckets")

    def test_string_terminator_is_required(self) -> None:
        data = bytearray(_string_path_fixture())
        data[-1] = 1
        with self.assertRaises(BinaryFormatError):
            parse_string_path_hash(bytes(data), source="bad-terminator")


class FacBoneTRSTests(unittest.TestCase):
    def test_positive_fixture(self) -> None:
        result = parse_fac_bone_trs(
            _fac_fixture(), unit_record_count=2, source="fixture", allow_final_sentinel=False
        )
        self.assertEqual(result.valid_unit_count, 2)
        self.assertEqual(result.bone_count, 2)
        self.assertEqual(result.trs_bytes, 128)
        self.assertEqual(result.max_trs_end, 960)

    def test_bone_list_bounds_are_required(self) -> None:
        data = bytearray(_fac_fixture())
        struct.pack_into("<I", data, 768, 1000)
        with self.assertRaises(BinaryFormatError):
            parse_fac_bone_trs(
                bytes(data), unit_record_count=2, source="bad-bones", allow_final_sentinel=False
            )

    def test_trs_range_bounds_are_required(self) -> None:
        data = bytearray(_fac_fixture())
        struct.pack_into("<I", data, 800 + 8, 3)
        with self.assertRaises(BinaryFormatError):
            parse_fac_bone_trs(
                bytes(data), unit_record_count=2, source="bad-trs", allow_final_sentinel=False
            )

    def test_trs_ranges_must_not_overlap(self) -> None:
        data = bytearray(_fac_fixture())
        struct.pack_into("<I", data, 816 + 12, 864)
        with self.assertRaises(BinaryFormatError):
            parse_fac_bone_trs(
                bytes(data), unit_record_count=2, source="overlapping-trs", allow_final_sentinel=False
            )

    def test_final_trs_end_must_consume_source(self) -> None:
        with self.assertRaises(BinaryFormatError):
            parse_fac_bone_trs(
                _fac_fixture() + b"x",
                unit_record_count=2,
                source="trailing",
                allow_final_sentinel=False,
            )


if __name__ == "__main__":
    unittest.main()
