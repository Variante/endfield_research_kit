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


def _anonymous_record(text: str, lists: tuple[tuple[int, ...], ...]):
    encoded = text.encode("utf-16-le")
    record = bytearray(struct.pack("<I", len(encoded)) + encoded + b"\0\0")
    pointers = [0, len(record)]
    for values in lists:
        record += struct.pack("<I", len(values))
        record += b"".join(struct.pack("<I", value) for value in values)
        record += b"\0\0"
        pointers.append(len(record))
    return bytes(record), tuple(pointers[:4])


def _fixture(*, count1=2, count2=2, opaque_prefix=b"pre!", opaque_suffix=b"suffix"):
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
    variable_payload = bytearray(opaque_prefix)
    for index in range(count2):
        struct.pack_into("<I", rows3, index * 48, index)
        record, relative_pointers = _anonymous_record(
            f"row-{index}",
            ((index,), (), (index, index + 1)),
        )
        record_start = len(variable_payload)
        for pointer_index, relative_pointer in enumerate(relative_pointers, 1):
            struct.pack_into(
                "<I",
                rows3,
                index * 48 + pointer_index * 4,
                record_start + relative_pointer,
            )
        variable_payload += record
    variable_payload += opaque_suffix
    out += rows3
    out += struct.pack("<I", len(variable_payload))
    out += variable_payload
    out += struct.pack("<I", len(variable_payload))
    return bytes(out)


class BundleManifestTests(unittest.TestCase):
    def test_real_framing_and_exact_consumption(self):
        decoded = _fixture(count1=2, count2=3)
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
        self.assertEqual(result.variable_region.indexed_record_count, 3)
        self.assertEqual(result.variable_region.opaque_prefix_length, len(b"pre!"))
        self.assertEqual(result.variable_region.opaque_suffix_length, len(b"suffix"))
        self.assertEqual(result.variable_region.indexed_integer_list_count, 9)
        self.assertEqual(result.variable_region.indexed_integer_value_count, 9)
        self.assertEqual(result.variable_region.end_offset, len(decoded))
        self.assertEqual(
            result.variable_region.size_witness,
            result.variable_region.footer_size_witness,
        )
        self.assertEqual(result.tables[0].to_dict()["fieldStatus"], "opaque")
        self.assertEqual(
            result.variable_region.to_dict()["recordStatus"],
            "partially-framed-anonymous",
        )

    def test_compressed_input_records_hashes(self):
        decoded = _fixture()
        compressed = brotli.compress(decoded)
        result = parse_bundle_manifest(compressed, source="fixture.hgmmap")
        self.assertEqual(result.compressed_length, len(compressed))
        self.assertEqual(result.decompressed_length, len(decoded))
        self.assertEqual(result.consumed_bytes, len(decoded))

    def test_rejects_truncated_variable_region_footer(self):
        decoded = _fixture(count1=2, count2=2, opaque_suffix=b"")
        with self.assertRaises(BinaryFormatError):
            parse_decompressed_bundle_manifest(decoded[:-1], source="truncated")

    def test_rejects_count_witness_mutation(self):
        decoded = bytearray(_fixture())
        struct.pack_into("<I", decoded, 160, 99)
        with self.assertRaises(BinaryFormatError):
            parse_decompressed_bundle_manifest(decoded, source="mutated")

    def test_rejects_variable_region_footer_mutation(self):
        decoded = bytearray(_fixture())
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

    def test_rejects_indexed_row_pointer_gap(self):
        decoded = bytearray(_fixture(count2=2))
        table2 = 156 + 4 + struct.unpack_from("<I", decoded, 156)[0]
        table3 = table2 + 4 + struct.unpack_from("<I", decoded, table2)[0]
        second_row_first_pointer = table3 + 8 + 48 + 4
        struct.pack_into(
            "<I",
            decoded,
            second_row_first_pointer,
            struct.unpack_from("<I", decoded, second_row_first_pointer)[0] + 2,
        )
        with self.assertRaisesRegex(BinaryFormatError, "indexed range"):
            parse_decompressed_bundle_manifest(decoded, source="pointer-gap")

    def test_rejects_indexed_nonmonotonic_pointers(self):
        decoded = bytearray(_fixture(count2=1))
        table2 = 156 + 4 + struct.unpack_from("<I", decoded, 156)[0]
        table3 = table2 + 4 + struct.unpack_from("<I", decoded, table2)[0]
        second_pointer = struct.unpack_from("<I", decoded, table3 + 8 + 8)[0]
        struct.pack_into("<I", decoded, table3 + 8 + 12, second_pointer - 1)
        with self.assertRaisesRegex(BinaryFormatError, "not monotonic"):
            parse_decompressed_bundle_manifest(decoded, source="nonmonotonic")

    def test_rejects_first_indexed_pointer_outside_payload(self):
        decoded = bytearray(_fixture(count2=1))
        table2 = 156 + 4 + struct.unpack_from("<I", decoded, 156)[0]
        table3 = table2 + 4 + struct.unpack_from("<I", decoded, table2)[0]
        variable_section = table3 + 4 + struct.unpack_from("<I", decoded, table3)[0]
        payload_length = struct.unpack_from("<I", decoded, variable_section)[0]
        struct.pack_into("<I", decoded, table3 + 8 + 4, payload_length)
        with self.assertRaisesRegex(BinaryFormatError, "first indexed offset"):
            parse_decompressed_bundle_manifest(decoded, source="outside-payload")

    def test_rejects_indexed_utf16_terminator_mutation(self):
        decoded = bytearray(_fixture(count2=1))
        parsed = parse_decompressed_bundle_manifest(decoded, source="control")
        region = parsed.variable_region
        terminator = (
            region.payload_offset
            + region.indexed_region_offset
            + 4
            + len("row-0".encode("utf-16-le"))
        )
        decoded[terminator] = 1
        with self.assertRaisesRegex(BinaryFormatError, "UTF-16 component.*terminator"):
            parse_decompressed_bundle_manifest(decoded, source="bad-utf16-terminator")

    def test_rejects_indexed_invalid_utf16(self):
        decoded = bytearray(_fixture(count2=1))
        parsed = parse_decompressed_bundle_manifest(decoded, source="control")
        string_bytes = (
            parsed.variable_region.payload_offset
            + parsed.variable_region.indexed_region_offset
            + 4
        )
        decoded[string_bytes : string_bytes + 2] = b"\0\xd8"
        with self.assertRaisesRegex(BinaryFormatError, "not strict UTF-16LE"):
            parse_decompressed_bundle_manifest(decoded, source="bad-utf16")

    def test_rejects_indexed_list_count_overrun(self):
        decoded = bytearray(_fixture(count2=1))
        table2 = 156 + 4 + struct.unpack_from("<I", decoded, 156)[0]
        table3 = table2 + 4 + struct.unpack_from("<I", decoded, table2)[0]
        payload_offset = table3 + 4 + struct.unpack_from("<I", decoded, table3)[0] + 4
        first_list = struct.unpack_from("<I", decoded, table3 + 8 + 8)[0]
        struct.pack_into("<I", decoded, payload_offset + first_list, 999)
        with self.assertRaisesRegex(BinaryFormatError, "list 1.*count 999"):
            parse_decompressed_bundle_manifest(decoded, source="bad-list-count")

    def test_rejects_indexed_list_terminator_mutation(self):
        decoded = bytearray(_fixture(count2=1))
        table2 = 156 + 4 + struct.unpack_from("<I", decoded, 156)[0]
        table3 = table2 + 4 + struct.unpack_from("<I", decoded, table2)[0]
        payload_offset = table3 + 4 + struct.unpack_from("<I", decoded, table3)[0] + 4
        first_list_end = struct.unpack_from("<I", decoded, table3 + 8 + 12)[0]
        decoded[payload_offset + first_list_end - 2] = 1
        with self.assertRaisesRegex(BinaryFormatError, "list 1.*terminator"):
            parse_decompressed_bundle_manifest(decoded, source="bad-list-terminator")

    def test_rejects_decompressed_trailing_bytes(self):
        with self.assertRaises(BinaryFormatError):
            parse_decompressed_bundle_manifest(_fixture() + b"x", source="trailing")

    def test_rejects_brotli_trailing_bytes(self):
        compressed = brotli.compress(_fixture()) + b"trailing"
        with self.assertRaises(BinaryFormatError):
            parse_bundle_manifest(compressed, source="trailing")


if __name__ == "__main__":
    unittest.main()
