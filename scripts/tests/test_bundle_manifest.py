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


def _fixture(*, count1=2, count2=2, variable_payload=b"opaque"):
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
    out += struct.pack("<I", count1)
    out += bytes(count1 * 32)
    out += struct.pack("<I", 4 + count2 * 56)
    out += struct.pack("<I", count2)
    out += bytes(count2 * 56)
    out += struct.pack("<I", 4 + count2 * 48)
    out += struct.pack("<I", count2)
    rows3 = bytearray(count2 * 48)
    for index in range(count2):
        struct.pack_into("<I", rows3, index * 48, index)
    out += rows3
    out += struct.pack("<I", len(variable_payload))
    out += variable_payload
    out += struct.pack("<I", len(variable_payload))
    return bytes(out)


class BundleManifestTests(unittest.TestCase):
    def test_real_framing_and_exact_consumption(self):
        decoded = _fixture(count1=2, count2=3, variable_payload=b"variable bytes")
        result = parse_decompressed_bundle_manifest(decoded, source="fixture")
        self.assertEqual(result.consumed_bytes, len(decoded))
        self.assertEqual(result.tables[0].row_count, 2)
        self.assertEqual(result.tables[1].row_count, 3)
        self.assertEqual(result.tables[2].row_count, 3)
        self.assertEqual(result.tables[0].offset, result.tables[0].section_offset + 8)
        self.assertEqual(result.tables[1].offset, result.tables[1].section_offset + 8)
        self.assertEqual(result.tables[2].offset, result.tables[2].section_offset + 8)
        self.assertEqual(
            result.tables[2].to_dict()["rowSequenceWitness"]["wordOffset"], 0
        )
        self.assertEqual(result.variable_region.payload_length, len(b"variable bytes"))
        self.assertEqual(result.variable_region.end_offset, len(decoded))
        self.assertEqual(
            result.variable_region.size_witness,
            result.variable_region.footer_size_witness,
        )
        self.assertEqual(result.tables[0].to_dict()["fieldStatus"], "opaque")
        self.assertEqual(result.variable_region.to_dict()["recordStatus"], "opaque")

    def test_compressed_input_records_hashes(self):
        decoded = _fixture()
        compressed = brotli.compress(decoded)
        result = parse_bundle_manifest(compressed, source="fixture.hgmmap")
        self.assertEqual(result.compressed_length, len(compressed))
        self.assertEqual(result.decompressed_length, len(decoded))
        self.assertEqual(result.consumed_bytes, len(decoded))

    def test_rejects_truncated_variable_region_footer(self):
        decoded = _fixture(count1=2, count2=2, variable_payload=b"")
        with self.assertRaises(BinaryFormatError):
            parse_decompressed_bundle_manifest(decoded[:-1], source="truncated")

    def test_rejects_count_witness_mutation(self):
        decoded = bytearray(_fixture())
        struct.pack_into("<I", decoded, 160, 99)
        with self.assertRaises(BinaryFormatError):
            parse_decompressed_bundle_manifest(decoded, source="mutated")

    def test_rejects_variable_region_footer_mutation(self):
        decoded = bytearray(_fixture(variable_payload=b"opaque"))
        struct.pack_into("<I", decoded, len(decoded) - 4, 7)
        with self.assertRaises(BinaryFormatError):
            parse_decompressed_bundle_manifest(decoded, source="bad-footer")

    def test_rejects_row_sequence_witness_mutation(self):
        decoded = bytearray(_fixture(count2=2))
        # Locate the third section from the two preceding size envelopes.
        table2 = 156 + 4 + struct.unpack_from("<I", decoded, 156)[0]
        table3 = table2 + 4 + struct.unpack_from("<I", decoded, table2)[0]
        struct.pack_into("<I", decoded, table3 + 8 + 48, 99)
        with self.assertRaises(BinaryFormatError):
            parse_decompressed_bundle_manifest(decoded, source="bad-sequence")

    def test_rejects_decompressed_trailing_bytes(self):
        with self.assertRaises(BinaryFormatError):
            parse_decompressed_bundle_manifest(_fixture() + b"x", source="trailing")

    def test_rejects_brotli_trailing_bytes(self):
        compressed = brotli.compress(_fixture()) + b"trailing"
        with self.assertRaises(BinaryFormatError):
            parse_bundle_manifest(compressed, source="trailing")


if __name__ == "__main__":
    unittest.main()
