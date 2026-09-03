import gzip
import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path

from scripts.game_data.extend_data_binary import (
    BinaryFormatError,
    _join_outer_ledger,
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
    # Two lookup slots end at 24. Their two 16-byte bucket records tile
    # [20, 52), while the aligned two-row unit table occupies [32, 64).
    # These overlapping views mirror the exact current FacBoneTRS layout.
    data = bytearray(216)
    struct.pack_into("<II", data, 0, 52, 2)
    struct.pack_into("<II", data, 8, 36, 1)
    struct.pack_into("<II", data, 16, 20, 1)
    struct.pack_into("<IQI", data, 20, 1, 0x1111, 1)
    struct.pack_into("<IQI", data, 36, 56, 0xAAAA, 1)
    # Unit 0 starts at 32 through the lookup overlap. Unit 1 starts at 48.
    struct.pack_into("<IIQ", data, 48, 1, 72, 0x101)
    # Bone 0 starts eight bytes before the unit table ends and shares its hash.
    struct.pack_into("<QII", data, 56, 0x101, 1, 88)
    struct.pack_into("<QII", data, 72, 0x202, 1, 152)
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
        result = parse_fac_bone_trs(_fac_fixture(), source="fixture")
        self.assertEqual(result.lookup_slot_count, 2)
        self.assertEqual(result.lookup_bucket_count, 2)
        self.assertEqual(result.unit_record_count, 2)
        self.assertEqual(result.bone_count, 2)
        self.assertEqual(result.trs_bytes, 128)
        self.assertEqual(result.max_trs_end, 216)
        self.assertEqual(result.unaccounted_ranges, ())

    def test_header_supplies_unit_count_and_lookup_boundary(self) -> None:
        data = bytearray(_fac_fixture())
        struct.pack_into("<I", data, 0, 48)
        with self.assertRaisesRegex(BinaryFormatError, "lookup end"):
            parse_fac_bone_trs(bytes(data), source="bad-header")

    def test_lookup_bucket_count_must_match_unit_count(self) -> None:
        data = bytearray(_fac_fixture())
        struct.pack_into("<II", data, 8, 0, 0)
        with self.assertRaisesRegex(BinaryFormatError, "lookup bucket count"):
            parse_fac_bone_trs(bytes(data), source="lookup-count")

    def test_lookup_bucket_ranges_must_not_overlap(self) -> None:
        data = bytearray(_fac_fixture())
        struct.pack_into("<I", data, 8, 28)
        with self.assertRaisesRegex(BinaryFormatError, "overlap"):
            parse_fac_bone_trs(bytes(data), source="lookup-overlap")

    def test_bone_list_bounds_are_required(self) -> None:
        data = bytearray(_fac_fixture())
        struct.pack_into("<I", data, 32, 1000)
        with self.assertRaises(BinaryFormatError):
            parse_fac_bone_trs(bytes(data), source="bad-bones")

    def test_bone_pool_requires_observed_eight_byte_overlap(self) -> None:
        data = bytearray(_fac_fixture())
        struct.pack_into("<I", data, 36, 64)
        struct.pack_into("<I", data, 52, 80)
        with self.assertRaisesRegex(BinaryFormatError, "bone pool starts"):
            parse_fac_bone_trs(bytes(data), source="missing-bone-overlap")

    def test_bone_pool_must_not_contain_gaps(self) -> None:
        data = bytearray(_fac_fixture())
        struct.pack_into("<I", data, 52, 80)
        with self.assertRaisesRegex(BinaryFormatError, "bone-list ranges contain gaps"):
            parse_fac_bone_trs(bytes(data), source="bone-gap")

    def test_trs_range_bounds_are_required(self) -> None:
        data = bytearray(_fac_fixture())
        struct.pack_into("<I", data, 56 + 8, 3)
        with self.assertRaises(BinaryFormatError):
            parse_fac_bone_trs(bytes(data), source="bad-trs")

    def test_trs_ranges_must_not_overlap(self) -> None:
        data = bytearray(_fac_fixture())
        struct.pack_into("<I", data, 72 + 12, 120)
        with self.assertRaises(BinaryFormatError):
            parse_fac_bone_trs(bytes(data), source="overlapping-trs")

    def test_trs_pool_must_start_at_bone_pool_end(self) -> None:
        data = bytearray(_fac_fixture() + b"\0" * 8)
        struct.pack_into("<I", data, 68, 96)
        struct.pack_into("<I", data, 84, 160)
        with self.assertRaisesRegex(BinaryFormatError, "TRS pool starts"):
            parse_fac_bone_trs(bytes(data), source="trs-start-gap")

    def test_trs_pool_must_not_contain_gaps(self) -> None:
        data = bytearray(_fac_fixture() + b"\0" * 8)
        struct.pack_into("<I", data, 84, 160)
        with self.assertRaisesRegex(BinaryFormatError, "TRS ranges contain gaps"):
            parse_fac_bone_trs(bytes(data), source="trs-gap")

    def test_final_trs_end_must_consume_source(self) -> None:
        with self.assertRaises(BinaryFormatError):
            parse_fac_bone_trs(_fac_fixture() + b"x", source="trailing")


class OuterLedgerJoinTests(unittest.TestCase):
    @staticmethod
    def _write_ledger(path: Path, *rows: dict) -> None:
        with gzip.open(path, "wt", encoding="utf-8") as stream:
            for row in rows:
                stream.write(json.dumps(row) + "\n")

    def test_exact_identity_join_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            physical = root / "source.chk"
            physical.write_bytes(b"payload")
            digest = hashlib.md5(b"payload").hexdigest()
            ledger = root / "ledger.jsonl.gz"
            header = {
                "recordType": "audit_header",
                "schemaVersion": 1,
                "inputSetSha256": "A" * 64,
                "sourceFingerprints": [],
            }
            row = {
                "recordType": "file",
                "inputSetSha256": "A" * 64,
                "status": "verified",
                "boundaryStatus": "boundary_verified",
                "virtualPath": "Data/Test.bin",
                "offset": 0,
                "length": 7,
                "actualBytesRead": 7,
                "recomputedFileDataMd5": digest,
                "physicalChunkPath": str(physical),
            }
            self._write_ledger(ledger, header, row)

            joined = _join_outer_ledger(
                ledger,
                "A" * 64,
                {
                    "Data/Test.bin": {
                        "offset": 0,
                        "length": 7,
                        "md5": digest,
                        "physical_chunk_path": physical,
                    }
                },
            )
            self.assertTrue(joined["complete"])
            self.assertEqual(1, len(joined["rows"]))

            row["recomputedFileDataMd5"] = "0" * 32
            self._write_ledger(ledger, header, row)
            with self.assertRaisesRegex(BinaryFormatError, "MD5 mismatch"):
                _join_outer_ledger(
                    ledger,
                    "A" * 64,
                    {
                        "Data/Test.bin": {
                            "offset": 0,
                            "length": 7,
                            "md5": digest,
                            "physical_chunk_path": physical,
                        }
                    },
                )

    def test_audit_header_is_mandatory_unique_and_identity_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            physical = root / "source.chk"
            physical.write_bytes(b"payload")
            digest = hashlib.md5(b"payload").hexdigest()
            ledger = root / "ledger.jsonl.gz"
            expected = {
                "Data/Test.bin": {
                    "offset": 0,
                    "length": 7,
                    "md5": digest,
                    "physical_chunk_path": physical,
                }
            }
            row = {
                "recordType": "file",
                "inputSetSha256": "A" * 64,
                "status": "verified",
                "boundaryStatus": "boundary_verified",
                "virtualPath": "Data/Test.bin",
                "offset": 0,
                "length": 7,
                "actualBytesRead": 7,
                "recomputedFileDataMd5": digest,
                "physicalChunkPath": str(physical),
            }
            header = {
                "recordType": "audit_header",
                "schemaVersion": 1,
                "inputSetSha256": "A" * 64,
            }

            self._write_ledger(ledger, row)
            with self.assertRaisesRegex(BinaryFormatError, "exactly one audit_header"):
                _join_outer_ledger(ledger, "A" * 64, expected)

            mismatched_header = header | {"inputSetSha256": "B" * 64}
            self._write_ledger(ledger, mismatched_header, row)
            with self.assertRaisesRegex(BinaryFormatError, "audit_header input-set"):
                _join_outer_ledger(ledger, "A" * 64, expected)

            self._write_ledger(ledger, header, header, row)
            with self.assertRaisesRegex(BinaryFormatError, "exactly one audit_header"):
                _join_outer_ledger(ledger, "A" * 64, expected)

            unsupported_header = header | {"schemaVersion": 2}
            self._write_ledger(ledger, unsupported_header, row)
            with self.assertRaisesRegex(BinaryFormatError, "unsupported audit_header"):
                _join_outer_ledger(ledger, "A" * 64, expected)

            non_file_row = row | {"recordType": "block"}
            self._write_ledger(ledger, header, non_file_row)
            with self.assertRaisesRegex(BinaryFormatError, "expected 'file'"):
                _join_outer_ledger(ledger, "A" * 64, expected)


if __name__ == "__main__":
    unittest.main()
