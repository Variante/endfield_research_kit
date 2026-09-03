import unittest

from scripts.game_data.streaming import parse_streaming_file


def _root(kind: str, devonly_info: bool = False) -> bytes:
    if kind == "info":
        return _info_root(devonly_info)
    if kind in {"init", "streaming"}:
        return _data_root()
    root, vtable_size, object_size = 24, 20, 40
    fields = [4, 8, 16, 20, 24, 28, 32, 36]
    size = 80
    data = bytearray(size)
    data[0:4] = root.to_bytes(4, "little")
    vtable = 4
    data[vtable : vtable + 2] = vtable_size.to_bytes(2, "little")
    data[vtable + 2 : vtable + 4] = object_size.to_bytes(2, "little")
    data[root : root + 4] = (root - vtable).to_bytes(4, "little", signed=True)
    for index, value in enumerate(fields):
        data[vtable + 4 + index * 2 : vtable + 6 + index * 2] = value.to_bytes(2, "little")
    return bytes(data)


def _data_root(*, populated: bool = False) -> bytes:
    size = 252 if populated else 92
    data = bytearray(size)
    root, root_vtable = 24, 4
    data[0:4] = root.to_bytes(4, "little")
    data[root_vtable : root_vtable + 2] = (20).to_bytes(2, "little")
    data[root_vtable + 2 : root_vtable + 4] = (40).to_bytes(2, "little")
    for index, value in enumerate((4, 8, 16, 20, 24, 28, 32, 36)):
        data[root_vtable + 4 + index * 2 : root_vtable + 6 + index * 2] = (
            value.to_bytes(2, "little")
        )
    data[root : root + 4] = (root - root_vtable).to_bytes(
        4, "little", signed=True
    )
    for field_index, target in zip(range(2, 6), range(64, 80, 4)):
        slot = root + (16, 20, 24, 28)[field_index - 2]
        data[slot : slot + 4] = (target - slot).to_bytes(4, "little")
        data[target : target + 4] = (0).to_bytes(4, "little")
    field6_slot, field7_slot = root + 32, root + 36
    data[field6_slot : field6_slot + 4] = (80 - field6_slot).to_bytes(4, "little")
    data[field7_slot : field7_slot + 4] = (88 - field7_slot).to_bytes(4, "little")
    if not populated:
        data[80:84] = (0).to_bytes(4, "little")
        data[88:92] = (0).to_bytes(4, "little")
        return bytes(data)

    # The two root vectors each contain one table offset. The one-field
    # wrappers deliberately reuse a vtable which is forward of the first
    # wrapper and backward from the second wrapper.
    data[80:84] = (1).to_bytes(4, "little")
    data[84:88] = (112 - 84).to_bytes(4, "little")
    data[88:92] = (1).to_bytes(4, "little")
    data[92:96] = (160 - 92).to_bytes(4, "little")

    data[112:116] = (-20).to_bytes(4, "little", signed=True)
    data[116:120] = (120 - 116).to_bytes(4, "little")
    data[120:132] = (2).to_bytes(4, "little") + (10).to_bytes(
        4, "little"
    ) + (20).to_bytes(4, "little")
    data[132:138] = (6).to_bytes(2, "little") + (8).to_bytes(
        2, "little"
    ) + (4).to_bytes(2, "little")

    data[140:154] = (14).to_bytes(2, "little") + (56).to_bytes(
        2, "little"
    ) + b"".join(value.to_bytes(2, "little") for value in (4, 8, 12, 16, 20))
    data[160:164] = (20).to_bytes(4, "little", signed=True)
    data[168:172] = (2).to_bytes(4, "little")
    data[176:180] = (216 - 176).to_bytes(4, "little")
    data[180:184] = (232 - 180).to_bytes(4, "little")
    data[216:228] = (1).to_bytes(4, "little") + (7).to_bytes(
        2, "little"
    ) + (4).to_bytes(2, "little") + (0).to_bytes(4, "little")

    data[232:236] = (100).to_bytes(4, "little", signed=True)
    data[236:240] = (240 - 236).to_bytes(4, "little")
    data[240:252] = (8).to_bytes(4, "little") + bytes(range(8))
    return bytes(data)


def _info_root(devonly: bool = False) -> bytes:
    if devonly:
        data = bytearray(104)
        root, root_vtable = 16, 4
        data[0:4] = root.to_bytes(4, "little")
        data[4:6] = (10).to_bytes(2, "little")
        data[6:8] = (16).to_bytes(2, "little")
        for index, value in enumerate((4, 8, 12)):
            data[8 + index * 2 : 10 + index * 2] = value.to_bytes(2, "little")
        data[root : root + 4] = (root - root_vtable).to_bytes(4, "little", signed=True)
        data[20:24] = (76).to_bytes(4, "little")  # scalar field 0
        data[24:28] = (64).to_bytes(4, "little")  # 12-byte vector at 88
        data[28:32] = (4).to_bytes(4, "little")   # table vector at 32
        data[32:36] = (1).to_bytes(4, "little")
        data[36:40] = (16).to_bytes(4, "little")  # row table at 52
        data[40:42] = (10).to_bytes(2, "little")
        data[42:44] = (20).to_bytes(2, "little")
        for index, value in enumerate((4, 12, 16)):
            data[44 + index * 2 : 46 + index * 2] = value.to_bytes(2, "little")
        data[52:56] = (12).to_bytes(4, "little", signed=True)
        data[56:64] = (0x8000000000000000).to_bytes(8, "little")
        data[64:68] = (16).to_bytes(4, "little")  # vector at 80
        data[68:72] = (4).to_bytes(4, "little")   # vector at 72
        data[72:80] = (1).to_bytes(4, "little") + (7).to_bytes(4, "little")
        data[80:88] = (1).to_bytes(4, "little") + (9).to_bytes(4, "little")
        data[88:104] = (1).to_bytes(4, "little") + bytes(range(12))
        return bytes(data)

    data = bytearray(96)
    root, root_vtable = 16, 4
    data[0:4] = root.to_bytes(4, "little")
    data[4:6] = (12).to_bytes(2, "little")
    data[6:8] = (20).to_bytes(2, "little")
    for index, value in enumerate((4, 8, 12, 16)):
        data[8 + index * 2 : 10 + index * 2] = value.to_bytes(2, "little")
    data[root : root + 4] = (root - root_vtable).to_bytes(4, "little", signed=True)
    data[20:24] = (1).to_bytes(4, "little")
    data[24:28] = (64).to_bytes(4, "little")  # vector at 88
    data[28:32] = (52).to_bytes(4, "little")  # vector at 80
    data[32:36] = (4).to_bytes(4, "little")   # table vector at 36
    data[36:40] = (1).to_bytes(4, "little")
    data[40:44] = (12).to_bytes(4, "little")  # row table at 52
    data[44:46] = (8).to_bytes(2, "little")
    data[46:48] = (16).to_bytes(2, "little")
    data[48:50] = (4).to_bytes(2, "little")
    data[50:52] = (12).to_bytes(2, "little")
    data[52:56] = (8).to_bytes(4, "little", signed=True)
    data[56:64] = (0x8000000000000000).to_bytes(8, "little")
    data[64:68] = (4).to_bytes(4, "little")  # vector at 68
    data[68:80] = (1).to_bytes(4, "little") + bytes(range(8))
    data[80:88] = (1).to_bytes(4, "little") + (7).to_bytes(4, "little")
    data[88:96] = (1).to_bytes(4, "little") + (9).to_bytes(4, "little")
    return bytes(data)


def _literal_only(data: bytes) -> bytes:
    length = len(data)
    if length < 15:
        # token 0x10 maps to a literal length of four; search the tiny
        # inverse table so this fixture remains independent of the codec.
        for token in range(256):
            mapped = (token & 3) | ((token & 0x33) >> 2)
            if mapped == length:
                return bytes([token]) + data
        raise AssertionError(length)
    remaining = length - 15
    extension = bytearray()
    while remaining >= 255:
        extension.append(255)
        remaining -= 255
    extension.append(remaining)
    return bytes([0x33]) + bytes(extension) + data


def _packed(data: bytes) -> bytes:
    return len(data).to_bytes(4, "little") + _literal_only(data)


class StreamingTests(unittest.TestCase):
    def test_compressed_init_exact_root(self):
        clear = _root("init")
        result = parse_streaming_file("init", _packed(clear))
        self.assertEqual(result["encoding"], "inverted_lz4")
        self.assertEqual(result["decodedBytes"], len(clear))
        self.assertEqual(
            result["anonymousGroupSubgraph"]["status"],
            "exact_anonymous_subgraph",
        )
        self.assertEqual(result["anonymousGroupSubgraph"]["pairedGroupCount"], 0)

    def test_init_anonymous_group_subgraph(self):
        result = parse_streaming_file("init", _packed(_data_root(populated=True)))
        subgraph = result["anonymousGroupSubgraph"]
        self.assertEqual(subgraph["pairedGroupCount"], 1)
        self.assertEqual(subgraph["valueCount"], 2)
        self.assertEqual(subgraph["descriptorCount"], 1)
        self.assertEqual(subgraph["blobBytes"], 8)
        self.assertGreaterEqual(subgraph["reusedVtableReferences"], 1)
        self.assertEqual(subgraph["wholeFileStatus"], "partial")

    def test_init_group_count_and_descriptor_fail_closed(self):
        clear = bytearray(_data_root(populated=True))
        clear[88:92] = (0).to_bytes(4, "little")
        with self.assertRaisesRegex(ValueError, "paired group count mismatch"):
            parse_streaming_file("init", _packed(bytes(clear)))

        clear = bytearray(_data_root(populated=True))
        clear[168:172] = (1).to_bytes(4, "little")
        with self.assertRaisesRegex(ValueError, "value count mismatch"):
            parse_streaming_file("init", _packed(bytes(clear)))

        clear = bytearray(_data_root(populated=True))
        clear[224:228] = (1).to_bytes(4, "little")
        with self.assertRaisesRegex(ValueError, "reserved value"):
            parse_streaming_file("init", _packed(bytes(clear)))

        clear = bytearray(_data_root(populated=True))
        clear[222:224] = (0).to_bytes(2, "little")
        with self.assertRaisesRegex(ValueError, "zero stride"):
            parse_streaming_file("init", _packed(bytes(clear)))

    def test_init_blob_length_and_subgraph_overlap_fail_closed(self):
        clear = bytearray(_data_root(populated=True))
        clear[240:244] = (7).to_bytes(4, "little")
        with self.assertRaisesRegex(ValueError, "blob length mismatch"):
            parse_streaming_file("init", _packed(bytes(clear)))

        clear = bytearray(_data_root(populated=True) + b"\0" * 4)
        clear[120:124] = (3).to_bytes(4, "little")
        clear[168:172] = (3).to_bytes(4, "little")
        clear[240:244] = (12).to_bytes(4, "little")
        with self.assertRaisesRegex(ValueError, "structural ranges overlap"):
            parse_streaming_file("init", _packed(bytes(clear)))

    def test_init_malformed_group_offset_and_truncation_fail_closed(self):
        clear = bytearray(_data_root(populated=True))
        clear[92:96] = (0).to_bytes(4, "little")
        with self.assertRaisesRegex(ValueError, "invalid table target"):
            parse_streaming_file("init", _packed(bytes(clear)))

        clear = bytearray(_data_root(populated=True))
        clear[152:154] = (54).to_bytes(2, "little")
        with self.assertRaisesRegex(ValueError, "wrapper slot exceeds table object"):
            parse_streaming_file("init", _packed(bytes(clear)))

        clear = _data_root(populated=True)[:-1]
        with self.assertRaisesRegex(ValueError, "exceeds payload"):
            parse_streaming_file("init", _packed(clear))

    def test_init_wrapper_group_shapes_and_descriptor_count_fail_closed(self):
        clear = bytearray(_data_root(populated=True))
        clear[134:136] = (12).to_bytes(2, "little")
        with self.assertRaisesRegex(ValueError, "field 6 row 0 shape"):
            parse_streaming_file("init", _packed(bytes(clear)))

        clear = bytearray(_data_root(populated=True))
        clear[142:144] = (52).to_bytes(2, "little")
        with self.assertRaisesRegex(ValueError, "field 7 row 0 shape"):
            parse_streaming_file("init", _packed(bytes(clear)))

        clear = bytearray(_data_root(populated=True))
        clear[216:220] = (0xFFFF_FFFF).to_bytes(4, "little")
        with self.assertRaisesRegex(ValueError, "descriptors count"):
            parse_streaming_file("init", _packed(bytes(clear)))

    def test_raw_devonly_streaming_root(self):
        result = parse_streaming_file("streaming", _root("streaming"), allow_raw=True)
        self.assertEqual(result["encoding"], "raw_flatbuffer")
        self.assertEqual(
            result["anonymousGroupSubgraph"]["status"],
            "exact_anonymous_subgraph",
        )

    def test_streaming_anonymous_group_subgraph(self):
        result = parse_streaming_file(
            "streaming", _packed(_data_root(populated=True))
        )
        subgraph = result["anonymousGroupSubgraph"]
        self.assertEqual(subgraph["pairedGroupCount"], 1)
        self.assertEqual(subgraph["valueCount"], 2)
        self.assertEqual(subgraph["blobBytes"], 8)
        self.assertEqual(subgraph["wholeFileStatus"], "partial")

    def test_raw_info_root(self):
        result = parse_streaming_file("info", _root("info"))
        self.assertEqual(result["root"]["fieldCount"], 4)
        self.assertEqual(result["anonymousInner"]["status"], "exact_anonymous")
        self.assertEqual(result["anonymousInner"]["rowCount"], 1)
        self.assertEqual(result["anonymousInner"]["structuralEnd"], 96)

    def test_raw_devonly_info_root(self):
        result = parse_streaming_file("info", _root("info", devonly_info=True))
        self.assertEqual(result["root"]["fieldCount"], 3)
        self.assertEqual(result["anonymousInner"]["zeroAlignmentBytes"], 4)

    def test_info_truncated_nested_vector_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "count 1 .* exceeds payload"):
            parse_streaming_file("info", _root("info")[:-1])

    def test_info_malformed_nested_table_offset_fails_closed(self):
        data = bytearray(_root("info"))
        data[40:44] = (0xFFFF_FFFF).to_bytes(4, "little")
        with self.assertRaisesRegex(ValueError, "table vtable|outside payload"):
            parse_streaming_file("info", bytes(data))

    def test_info_nonzero_and_zero_trailing_bytes_fail_closed(self):
        for suffix in (b"\x00", b"\x7f"):
            with self.subTest(suffix=suffix), self.assertRaisesRegex(
                ValueError, "structural ranges end"
            ):
                parse_streaming_file("info", _root("info") + suffix)

    def test_info_unowned_nonzero_alignment_byte_fails_closed(self):
        data = bytearray(_root("info", devonly_info=True))
        data[50] = 1
        with self.assertRaisesRegex(ValueError, "nonzero byte outside"):
            parse_streaming_file("info", bytes(data))

    def test_info_overlapping_vector_ranges_fail_closed(self):
        data = bytearray(_root("info"))
        data[64:68] = (16).to_bytes(4, "little")  # Alias the root field-2 vector.
        with self.assertRaisesRegex(ValueError, "structural ranges overlap"):
            parse_streaming_file("info", bytes(data))

    def test_truncated_compressed_fails_closed(self):
        clear = _root("init")
        packed = len(clear).to_bytes(4, "little") + _literal_only(clear[:-1])
        with self.assertRaisesRegex(ValueError, "compressed envelope failed"):
            parse_streaming_file("init", packed)

    def test_wrong_root_shape_fails_closed(self):
        clear = bytearray(_root("init"))
        clear[4:6] = (12).to_bytes(2, "little")
        with self.assertRaisesRegex(ValueError, "expected 8"):
            parse_streaming_file("init", bytes(clear), allow_raw=True)

    def test_unknown_family_and_empty_payload_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "unknown Streaming family"):
            parse_streaming_file("other", b"x")
        with self.assertRaisesRegex(ValueError, "payload is empty"):
            parse_streaming_file("info", b"")

    def test_raw_data_family_requires_explicit_exception(self):
        with self.assertRaisesRegex(ValueError, "compressed envelope failed"):
            parse_streaming_file("streaming", _root("streaming"))

    def test_zero_decoded_size_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "decoded size is not positive"):
            parse_streaming_file("init", b"\x00\x00\x00\x00x")

    def test_invalid_root_and_vtable_offsets_fail_closed(self):
        clear = bytearray(_root("info"))
        clear[0:4] = len(clear).to_bytes(4, "little")
        with self.assertRaisesRegex(ValueError, "root offset"):
            parse_streaming_file("info", bytes(clear))

        clear = bytearray(_root("info"))
        root = int.from_bytes(clear[0:4], "little")
        clear[root : root + 4] = (root + 1).to_bytes(4, "little", signed=True)
        with self.assertRaisesRegex(ValueError, "vtable back offset"):
            parse_streaming_file("info", bytes(clear))


if __name__ == "__main__":
    unittest.main()
