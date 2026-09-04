import io
import struct
import unittest

from scripts.game_data.irradiance_volume import (
    IrradianceFormatError,
    INDEX_MAGIC_LEGACY_GACHA,
    INDEX_MAGIC_V3_GACHA,
    INDEX_MAGIC_V3_SCENE,
    INDEXED_PAYLOAD_OPAQUE_PREFIX_SIZE,
    INDEXED_PAYLOAD_RECORD_SIZE,
    INDEXED_PAYLOAD_SCENE_RECORD_SIZE,
    LEGACY_INDEXED_PAYLOAD_RECORD_SIZE,
    REGION_HEADER_SIZE,
    REGION_RECORD_SIZE,
    parse_index_bytes,
    parse_grouped_indexed_payload_bytes,
    parse_grouped_indexed_payload_framing,
    parse_indexed_payload_bytes,
    parse_indexed_payload_framing,
    parse_legacy_grouped_indexed_payload_bytes,
    parse_legacy_grouped_indexed_payload_framing,
    parse_region_bytes,
    validate_indexed_payload_stream,
    validate_grouped_indexed_payload_streams,
    validate_legacy_grouped_indexed_payload_streams,
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


def indexed_payload_fixture(
    ranges=((0, 5), (5, 7)),
    names=("iv_0_0.bytes",),
    magic=INDEX_MAGIC_V3_GACHA,
    opaque=None,
):
    if opaque is None:
        opaque = bytes(INDEXED_PAYLOAD_OPAQUE_PREFIX_SIZE)
    directory = bytearray(struct.pack("<I", len(ranges)))
    for index, (offset, length) in enumerate(ranges):
        directory.extend(
            struct.pack(
                "<8I",
                0x10000000 + index,
                0x20000000 + index,
                offset,
                length,
                0x40000000 + index,
                0x50000000 + index,
                0x60000000 + index,
                0x70000000 + index,
            )
        )
    return index_fixture(names, magic, opaque + directory)


def scene_indexed_payload_fixture(
    ranges=((0, 4), (4, 6)),
    opaque_prefix=b"opaque-prefix---",
    opaque_suffix=b"opaque-suffix",
):
    directory = bytearray(struct.pack("<I", len(ranges)))
    for index, (offset, length) in enumerate(ranges):
        directory.extend(
            struct.pack(
                "<9I",
                0x11000000 + index,
                0x22000000 + index,
                offset,
                length,
                0x44000000 + index,
                0x55000000 + index,
                0x66000000 + index,
                0x77000000 + index,
                0x88000000 + index,
            )
        )
    return index_fixture(
        ("iv_0_0.bytes",),
        INDEX_MAGIC_V3_SCENE,
        opaque_prefix + directory + opaque_suffix,
    )


def grouped_scene_indexed_payload_fixture(
    groups=(((0, 3), (3, 2)), ((0, 4), (4, 3))),
    names=("iv_0_0.bytes", "iv_0_1.bytes"),
    opaque_prefix=b"pref",
    opaque_suffix=b"suffix--",
):
    ranges = [item for group in groups for item in group]
    directory = bytearray(struct.pack("<I", len(ranges)))
    for index, (offset, length) in enumerate(ranges):
        directory.extend(
            struct.pack(
                "<9I",
                0x11000000 + index,
                0x22000000 + index,
                offset,
                length,
                0x44000000 + index,
                0x55000000 + index,
                0x66000000 + index,
                0x77000000 + index,
                0x88000000 + index,
            )
        )
    return index_fixture(
        names,
        INDEX_MAGIC_V3_SCENE,
        opaque_prefix + directory + opaque_suffix,
    )


def legacy_grouped_indexed_payload_fixture(
    groups=(((0, 3), (7, 3), (3, 4)), ((4, 3), (0, 4)), ((0, 5),)),
    names=("iv_0_0_0.bytes", "iv_1_0_0.bytes", "iv_3_0_0.bytes"),
    opaque_prefix=b"",
):
    ranges = [item for group in groups for item in group]
    directory = bytearray(struct.pack("<I", len(ranges)))
    for index, (offset, length) in enumerate(ranges):
        directory.extend(
            struct.pack(
                "<9I",
                0x11000000 + index,
                0x22000000 + index,
                0x33000000 + index,
                0x44000000 + index,
                0x55000000 + index,
                0x66000000 + index,
                0x77000000 + index,
                offset,
                length,
            )
        )
    return index_fixture(
        names,
        INDEX_MAGIC_LEGACY_GACHA,
        opaque_prefix + directory,
    )


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

    def test_indexed_payload_exact_directory_and_payload(self):
        index_data = indexed_payload_fixture()
        framing = parse_indexed_payload_bytes(index_data, b"hello" + b"payload")
        self.assertEqual(framing.schema_version, 1)
        self.assertEqual(framing.magic, INDEX_MAGIC_V3_GACHA)
        self.assertEqual(framing.payload_filename, "iv_0_0.bytes")
        self.assertEqual(
            framing.opaque_prefix_end - framing.opaque_prefix_start,
            INDEXED_PAYLOAD_OPAQUE_PREFIX_SIZE,
        )
        self.assertEqual(framing.record_count, 2)
        self.assertEqual(framing.record_size, INDEXED_PAYLOAD_RECORD_SIZE)
        self.assertEqual(
            [(record.offset, record.length, record.end) for record in framing.records],
            [(0, 5, 5), (5, 7, 12)],
        )
        self.assertEqual(framing.payload_length, 12)
        self.assertEqual(framing.directory_end, len(index_data))
        self.assertEqual(framing.opaque_suffix_start, len(index_data))
        self.assertEqual(framing.opaque_suffix_end, len(index_data))

    def test_scene_indexed_payload_unique_directory_and_opaque_ranges(self):
        index_data = scene_indexed_payload_fixture()
        framing = parse_indexed_payload_bytes(index_data, b"0123456789")
        parsed_index = parse_index_bytes(index_data)
        self.assertEqual(framing.magic, INDEX_MAGIC_V3_SCENE)
        self.assertEqual(framing.record_count, 2)
        self.assertEqual(framing.record_size, INDEXED_PAYLOAD_SCENE_RECORD_SIZE)
        self.assertEqual(len(framing.records[0].words), 9)
        self.assertEqual(
            (framing.opaque_prefix_start, framing.opaque_prefix_end),
            (parsed_index.table_end, parsed_index.table_end + len(b"opaque-prefix---")),
        )
        self.assertEqual(
            (framing.opaque_suffix_start, framing.opaque_suffix_end),
            (len(index_data) - len(b"opaque-suffix"), len(index_data)),
        )
        self.assertEqual(framing.payload_length, 10)

    def test_scene_indexed_payload_requires_authenticated_length(self):
        with self.assertRaisesRegex(IrradianceFormatError, "authenticated payload length"):
            parse_indexed_payload_framing(scene_indexed_payload_fixture())

    def test_scene_indexed_payload_rejects_no_matching_directory(self):
        with self.assertRaisesRegex(IrradianceFormatError, "0 candidates"):
            parse_indexed_payload_framing(scene_indexed_payload_fixture(), 11)

    def test_scene_indexed_payload_rejects_ambiguous_directory(self):
        base = parse_index_bytes(scene_indexed_payload_fixture())
        one = scene_indexed_payload_fixture(opaque_prefix=b"", opaque_suffix=b"")
        directory = one[base.table_end:]
        data = index_fixture(
            ("iv_0_0.bytes",),
            INDEX_MAGIC_V3_SCENE,
            b"pref" + directory + b"mid-" + directory + b"suffix--",
        )
        with self.assertRaisesRegex(IrradianceFormatError, "2 candidates"):
            parse_indexed_payload_framing(data, 10)

    def test_grouped_scene_payload_directory_and_filename_groups(self):
        index_data = grouped_scene_indexed_payload_fixture()
        framing = parse_grouped_indexed_payload_bytes(
            index_data,
            {
                "iv_0_0.bytes": b"abcde",
                "iv_0_1.bytes": b"1234567",
            },
        )
        parsed_index = parse_index_bytes(index_data)
        self.assertEqual(framing.schema_version, 1)
        self.assertEqual(framing.directory_alignment, "absolute_4_byte")
        self.assertEqual(framing.payload_filenames, parsed_index.filenames)
        self.assertEqual(framing.record_count, 4)
        self.assertEqual(framing.record_size, INDEXED_PAYLOAD_SCENE_RECORD_SIZE)
        self.assertEqual(
            [
                (
                    group.payload_filename,
                    group.first_record_index,
                    group.payload_length,
                    [(record.offset, record.length) for record in group.records],
                )
                for group in framing.groups
            ],
            [
                ("iv_0_0.bytes", 0, 5, [(0, 3), (3, 2)]),
                ("iv_0_1.bytes", 2, 7, [(0, 4), (4, 3)]),
            ],
        )
        self.assertEqual(
            (framing.opaque_prefix_start, framing.opaque_prefix_end),
            (parsed_index.table_end, parsed_index.table_end + 4),
        )
        self.assertEqual(
            (framing.opaque_suffix_start, framing.opaque_suffix_end),
            (len(index_data) - 8, len(index_data)),
        )

    def test_grouped_scene_payload_rejects_filename_set_mismatch(self):
        with self.assertRaisesRegex(IrradianceFormatError, "filenames mismatch"):
            parse_grouped_indexed_payload_framing(
                grouped_scene_indexed_payload_fixture(),
                {"iv_0_0.bytes": 5, "iv_wrong.bytes": 7},
            )

    def test_grouped_scene_payload_rejects_filename_group_order_mismatch(self):
        with self.assertRaisesRegex(IrradianceFormatError, "0 candidates"):
            parse_grouped_indexed_payload_framing(
                grouped_scene_indexed_payload_fixture(),
                {"iv_0_0.bytes": 7, "iv_0_1.bytes": 5},
            )

    def test_grouped_scene_payload_rejects_missing_offset_restart(self):
        data = grouped_scene_indexed_payload_fixture(
            groups=(((0, 3), (3, 2)), ((5, 4), (9, 3)))
        )
        with self.assertRaisesRegex(IrradianceFormatError, "0 candidates"):
            parse_grouped_indexed_payload_framing(
                data, {"iv_0_0.bytes": 5, "iv_0_1.bytes": 12}
            )

    def test_grouped_scene_payload_rejects_group_gap(self):
        data = grouped_scene_indexed_payload_fixture(
            groups=(((0, 3), (4, 2)), ((0, 4), (4, 3)))
        )
        with self.assertRaisesRegex(IrradianceFormatError, "0 candidates"):
            parse_grouped_indexed_payload_framing(
                data, {"iv_0_0.bytes": 6, "iv_0_1.bytes": 7}
            )

    def test_grouped_scene_payload_rejects_group_overlap(self):
        data = grouped_scene_indexed_payload_fixture(
            groups=(((0, 3), (2, 2)), ((0, 4), (4, 3)))
        )
        with self.assertRaisesRegex(IrradianceFormatError, "0 candidates"):
            parse_grouped_indexed_payload_framing(
                data, {"iv_0_0.bytes": 4, "iv_0_1.bytes": 7}
            )

    def test_grouped_scene_payload_rejects_ambiguous_directory(self):
        one = grouped_scene_indexed_payload_fixture(
            opaque_prefix=b"", opaque_suffix=b""
        )
        parsed = parse_index_bytes(one)
        directory = one[parsed.table_end:]
        data = index_fixture(
            parsed.filenames,
            INDEX_MAGIC_V3_SCENE,
            b"pref" + directory + b"mid-" + directory + b"suffix--",
        )
        with self.assertRaisesRegex(IrradianceFormatError, "2 candidates"):
            parse_grouped_indexed_payload_framing(
                data, {"iv_0_0.bytes": 5, "iv_0_1.bytes": 7}
            )

    def test_grouped_scene_payload_accepts_filename_table_relative_alignment(self):
        data = grouped_scene_indexed_payload_fixture(
            names=("iv_10_0.bytes", "iv_0_1.bytes"),
            opaque_prefix=b"",
        )
        framing = parse_grouped_indexed_payload_framing(
            data, {"iv_10_0.bytes": 5, "iv_0_1.bytes": 7}
        )
        parsed = parse_index_bytes(data)
        self.assertEqual(framing.schema_version, 2)
        self.assertEqual(
            framing.directory_alignment, "filename_table_end_relative_4_byte"
        )
        self.assertEqual(framing.directory_offset % 4, 2)
        self.assertEqual((framing.directory_offset - parsed.table_end) % 4, 0)

    def test_grouped_scene_payload_rejects_directory_outside_both_alignments(self):
        data = grouped_scene_indexed_payload_fixture(
            names=("iv_10_0.bytes", "iv_0_1.bytes"),
            opaque_prefix=b"x",
        )
        with self.assertRaisesRegex(IrradianceFormatError, "0 candidates"):
            parse_grouped_indexed_payload_framing(
                data, {"iv_10_0.bytes": 5, "iv_0_1.bytes": 7}
            )

    def test_grouped_scene_payload_rejects_cross_alignment_ambiguity(self):
        one = grouped_scene_indexed_payload_fixture(
            names=("iv_10_0.bytes", "iv_0_1.bytes"),
            opaque_prefix=b"",
            opaque_suffix=b"",
        )
        parsed = parse_index_bytes(one)
        directory = one[parsed.table_end:]
        data = index_fixture(
            parsed.filenames,
            INDEX_MAGIC_V3_SCENE,
            directory + b"xx" + directory,
        )
        with self.assertRaisesRegex(IrradianceFormatError, "2 candidates"):
            parse_grouped_indexed_payload_framing(
                data, {"iv_10_0.bytes": 5, "iv_0_1.bytes": 7}
            )

    def test_grouped_scene_payload_rejects_short_named_stream(self):
        with self.assertRaisesRegex(IrradianceFormatError, "iv_0_1.bytes.*short read"):
            validate_grouped_indexed_payload_streams(
                grouped_scene_indexed_payload_fixture(),
                {
                    "iv_0_0.bytes": io.BytesIO(b"abcde"),
                    "iv_0_1.bytes": io.BytesIO(b"short"),
                },
                {"iv_0_0.bytes": 5, "iv_0_1.bytes": 7},
            )

    def test_grouped_scene_payload_rejects_trailing_named_stream(self):
        with self.assertRaisesRegex(IrradianceFormatError, "iv_0_1.bytes.*trailing bytes"):
            validate_grouped_indexed_payload_streams(
                grouped_scene_indexed_payload_fixture(),
                {
                    "iv_0_0.bytes": io.BytesIO(b"abcde"),
                    "iv_0_1.bytes": io.BytesIO(b"1234567x"),
                },
                {"iv_0_0.bytes": 5, "iv_0_1.bytes": 7},
            )

    def test_legacy_grouped_payload_exact_directory_and_sorted_intervals(self):
        index_data = legacy_grouped_indexed_payload_fixture()
        framing = parse_legacy_grouped_indexed_payload_bytes(
            index_data,
            {
                "iv_0_0_0.bytes": b"a" * 10,
                "iv_1_0_0.bytes": b"b" * 7,
                "iv_3_0_0.bytes": b"c" * 5,
            },
        )
        parsed = parse_index_bytes(index_data)
        self.assertEqual(framing.schema_version, 1)
        self.assertEqual(framing.record_size, LEGACY_INDEXED_PAYLOAD_RECORD_SIZE)
        self.assertEqual(framing.record_count, 6)
        self.assertEqual(framing.directory_offset, parsed.table_end)
        self.assertEqual(framing.directory_end, len(index_data))
        self.assertEqual(
            [
                (
                    group.payload_filename,
                    group.first_record_index,
                    group.payload_length,
                    sorted((record.offset, record.length) for record in group.records),
                )
                for group in framing.groups
            ],
            [
                (
                    "iv_0_0_0.bytes",
                    0,
                    10,
                    [(0, 3), (3, 4), (7, 3)],
                ),
                ("iv_1_0_0.bytes", 3, 7, [(0, 4), (4, 3)]),
                ("iv_3_0_0.bytes", 5, 5, [(0, 5)]),
            ],
        )

    def test_legacy_grouped_payload_accepts_unique_unaligned_boundary(self):
        data = legacy_grouped_indexed_payload_fixture(opaque_prefix=b"x")
        framing = parse_legacy_grouped_indexed_payload_framing(
            data,
            {
                "iv_0_0_0.bytes": 10,
                "iv_1_0_0.bytes": 7,
                "iv_3_0_0.bytes": 5,
            },
        )
        self.assertEqual(framing.directory_offset, framing.filename_table_end + 1)

    def test_legacy_grouped_payload_rejects_filename_set_mismatch(self):
        with self.assertRaisesRegex(IrradianceFormatError, "filenames mismatch"):
            parse_legacy_grouped_indexed_payload_framing(
                legacy_grouped_indexed_payload_fixture(),
                {
                    "iv_0_0_0.bytes": 10,
                    "iv_1_0_0.bytes": 7,
                    "iv_wrong.bytes": 5,
                },
            )

    def test_legacy_grouped_payload_rejects_gap(self):
        data = legacy_grouped_indexed_payload_fixture(
            groups=(((0, 3), (8, 3), (3, 4)), ((4, 3), (0, 4)), ((0, 5),))
        )
        with self.assertRaisesRegex(IrradianceFormatError, "0 candidates"):
            parse_legacy_grouped_indexed_payload_framing(
                data,
                {
                    "iv_0_0_0.bytes": 10,
                    "iv_1_0_0.bytes": 7,
                    "iv_3_0_0.bytes": 5,
                },
            )

    def test_legacy_grouped_payload_rejects_overlap(self):
        data = legacy_grouped_indexed_payload_fixture(
            groups=(((0, 3), (6, 3), (3, 4)), ((4, 3), (0, 4)), ((0, 5),))
        )
        with self.assertRaisesRegex(IrradianceFormatError, "0 candidates"):
            parse_legacy_grouped_indexed_payload_framing(
                data,
                {
                    "iv_0_0_0.bytes": 10,
                    "iv_1_0_0.bytes": 7,
                    "iv_3_0_0.bytes": 5,
                },
            )

    def test_legacy_grouped_payload_rejects_index_trailing_byte(self):
        with self.assertRaisesRegex(IrradianceFormatError, "0 candidates"):
            parse_legacy_grouped_indexed_payload_framing(
                legacy_grouped_indexed_payload_fixture() + b"x",
                {
                    "iv_0_0_0.bytes": 10,
                    "iv_1_0_0.bytes": 7,
                    "iv_3_0_0.bytes": 5,
                },
            )

    def test_legacy_grouped_payload_rejects_short_named_stream(self):
        with self.assertRaisesRegex(
            IrradianceFormatError, "iv_1_0_0.bytes.*short read"
        ):
            validate_legacy_grouped_indexed_payload_streams(
                legacy_grouped_indexed_payload_fixture(),
                {
                    "iv_0_0_0.bytes": io.BytesIO(b"a" * 10),
                    "iv_1_0_0.bytes": io.BytesIO(b"b" * 6),
                    "iv_3_0_0.bytes": io.BytesIO(b"c" * 5),
                },
                {
                    "iv_0_0_0.bytes": 10,
                    "iv_1_0_0.bytes": 7,
                    "iv_3_0_0.bytes": 5,
                },
            )

    def test_legacy_grouped_payload_rejects_trailing_named_stream(self):
        with self.assertRaisesRegex(
            IrradianceFormatError, "iv_3_0_0.bytes.*trailing bytes"
        ):
            validate_legacy_grouped_indexed_payload_streams(
                legacy_grouped_indexed_payload_fixture(),
                {
                    "iv_0_0_0.bytes": io.BytesIO(b"a" * 10),
                    "iv_1_0_0.bytes": io.BytesIO(b"b" * 7),
                    "iv_3_0_0.bytes": io.BytesIO(b"c" * 6),
                },
                {
                    "iv_0_0_0.bytes": 10,
                    "iv_1_0_0.bytes": 7,
                    "iv_3_0_0.bytes": 5,
                },
            )

    def test_legacy_grouped_payload_rejects_scene_magic(self):
        with self.assertRaisesRegex(IrradianceFormatError, "unsupported.*0x03000003"):
            parse_legacy_grouped_indexed_payload_framing(
                grouped_scene_indexed_payload_fixture(),
                {"iv_0_0.bytes": 5, "iv_0_1.bytes": 7},
            )

    def test_indexed_payload_streaming_validator(self):
        framing = validate_indexed_payload_stream(
            indexed_payload_fixture(((0, 3), (3, 2))), io.BytesIO(b"abcde")
        )
        self.assertEqual(framing.payload_length, 5)

    def test_indexed_payload_rejects_other_numeric_magic(self):
        with self.assertRaisesRegex(IrradianceFormatError, "unsupported.*0x01000043"):
            parse_indexed_payload_framing(
                indexed_payload_fixture(magic=INDEX_MAGIC_LEGACY_GACHA)
            )

    def test_indexed_payload_rejects_multiple_filenames(self):
        with self.assertRaisesRegex(IrradianceFormatError, "exactly one filename"):
            parse_indexed_payload_framing(
                indexed_payload_fixture(names=("iv_0_0.bytes", "iv_1_0.bytes"))
            )

    def test_indexed_payload_rejects_short_opaque_prefix(self):
        with self.assertRaisesRegex(IrradianceFormatError, "directory count: short read"):
            parse_indexed_payload_framing(indexed_payload_fixture(opaque=b"short"))

    def test_indexed_payload_rejects_count_bound(self):
        data = bytearray(indexed_payload_fixture())
        directory_offset = len(data) - 2 * INDEXED_PAYLOAD_RECORD_SIZE - 4
        struct.pack_into("<I", data, directory_offset, 0xFFFFFFFF)
        with self.assertRaisesRegex(IrradianceFormatError, "count .* exceeds bound"):
            parse_indexed_payload_framing(bytes(data))

    def test_indexed_payload_rejects_truncated_directory(self):
        with self.assertRaisesRegex(IrradianceFormatError, "directory truncated"):
            parse_indexed_payload_framing(indexed_payload_fixture()[:-1])

    def test_indexed_payload_rejects_directory_trailing_bytes(self):
        with self.assertRaisesRegex(IrradianceFormatError, "directory trailing bytes"):
            parse_indexed_payload_framing(indexed_payload_fixture() + b"x")

    def test_indexed_payload_rejects_zero_record_length(self):
        with self.assertRaisesRegex(IrradianceFormatError, "zero byte length"):
            parse_indexed_payload_framing(indexed_payload_fixture(((0, 0),)))

    def test_indexed_payload_rejects_gap(self):
        with self.assertRaisesRegex(IrradianceFormatError, "gap"):
            parse_indexed_payload_framing(indexed_payload_fixture(((0, 5), (6, 2))))

    def test_indexed_payload_rejects_overlap(self):
        with self.assertRaisesRegex(IrradianceFormatError, "overlap"):
            parse_indexed_payload_framing(indexed_payload_fixture(((0, 5), (4, 2))))

    def test_indexed_payload_rejects_uint32_end_overflow(self):
        with self.assertRaisesRegex(IrradianceFormatError, "exceeds uint32 range"):
            parse_indexed_payload_framing(
                indexed_payload_fixture(((0, 0xFFFFFFFF), (0xFFFFFFFF, 2)))
            )

    def test_indexed_payload_rejects_short_payload(self):
        with self.assertRaisesRegex(IrradianceFormatError, "short read"):
            parse_indexed_payload_bytes(indexed_payload_fixture(), b"short")

    def test_indexed_payload_rejects_payload_trailing_bytes(self):
        with self.assertRaisesRegex(IrradianceFormatError, "payload: trailing bytes"):
            parse_indexed_payload_bytes(
                indexed_payload_fixture(), b"hellopayload" + b"x"
            )


if __name__ == "__main__":
    unittest.main()
