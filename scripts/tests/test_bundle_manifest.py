import brotli
import struct
import unittest

from scripts.game_data.bundle_manifest import (
    BinaryFormatError,
    HEAD1,
    HEAD2,
    parse_bundle_manifest,
    parse_decompressed_bundle_manifest,
)


def _fixture(*, count1=2, count2=2, tail=b"opaque"):
    text1 = "a" * 36
    text2 = "b" * 32
    out = bytearray()
    out += struct.pack("<I", HEAD1)
    out += struct.pack("<I", len(text1))
    out += text1.encode("utf-16-le")
    out += struct.pack("<I", HEAD2)
    out += struct.pack("<I", len(text2))
    out += text2.encode("utf-16-le")
    assert len(out) == 152
    out += b"\0\0\0\0"
    out += struct.pack("<I", 4 + count1 * 32)
    # The first row's first word is the observed table-1 count witness.
    out += struct.pack("<I", count1) + bytes((count1 * 32 - 4))
    out += struct.pack("<I", 0)
    out += struct.pack("<I", 4 + count2 * 56)
    out += struct.pack("<I", count2)
    out += bytes((count2 * 56 - 12))
    rows3 = bytearray(count2 * 48)
    struct.pack_into("<I", rows3, 16, count2)
    out += rows3
    out += tail
    return bytes(out)


class BundleManifestTests(unittest.TestCase):
    def test_real_framing_and_exact_consumption(self):
        decoded = _fixture(count1=2, count2=3, tail=b"tail bytes")
        result = parse_decompressed_bundle_manifest(decoded, source="fixture")
        self.assertEqual(result.consumed_bytes, len(decoded))
        self.assertEqual(result.tables[0].row_count, 2)
        self.assertEqual(result.tables[1].row_count, 3)
        self.assertEqual(result.tables[2].row_count, 3)
        self.assertEqual(result.opaque_tail_offset + 10, len(decoded))
        self.assertEqual(result.opaque_tail_length, 10)
        self.assertEqual(result.tables[0].to_dict()["fieldStatus"], "opaque")

    def test_compressed_input_records_hashes(self):
        decoded = _fixture()
        compressed = brotli.compress(decoded)
        result = parse_bundle_manifest(compressed, source="fixture.hgmmap")
        self.assertEqual(result.compressed_length, len(compressed))
        self.assertEqual(result.decompressed_length, len(decoded))
        self.assertEqual(result.consumed_bytes, len(decoded))

    def test_rejects_truncated_table(self):
        decoded = _fixture(count1=2, count2=2, tail=b"")
        with self.assertRaises(BinaryFormatError):
            parse_decompressed_bundle_manifest(decoded[:-1], source="truncated")

    def test_rejects_count_witness_mutation(self):
        decoded = bytearray(_fixture())
        struct.pack_into("<I", decoded, 160, 99)
        with self.assertRaises(BinaryFormatError):
            parse_decompressed_bundle_manifest(decoded, source="mutated")

    def test_rejects_brotli_trailing_bytes(self):
        compressed = brotli.compress(_fixture()) + b"trailing"
        with self.assertRaises(BinaryFormatError):
            parse_bundle_manifest(compressed, source="trailing")


if __name__ == "__main__":
    unittest.main()
