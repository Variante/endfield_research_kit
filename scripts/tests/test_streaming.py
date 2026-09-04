import unittest

from scripts.game_data.streaming import _nested_reference_ranges, parse_streaming_file


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
    size = 256 if populated else 96
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
    for field_index, target in zip(range(2, 6), (size - 4, 68, 72, 76)):
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
    data[size - 4 : size] = (0).to_bytes(4, "little")
    return bytes(data)


def _parallel_data_root() -> bytes:
    """Two field-5 rows share both a vtable and one field-0 target."""

    data = bytearray(172)
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

    targets = (168, 68, 80, 88, 104, 108)
    for slot, target in zip((40, 44, 48, 52, 56, 60), targets):
        data[slot : slot + 4] = (target - slot).to_bytes(4, "little")
    data[68:80] = (2).to_bytes(4, "little") + (7).to_bytes(
        4, "little"
    ) + (9).to_bytes(4, "little")
    data[80:86] = (2).to_bytes(4, "little") + bytes((1, 2))
    data[88:100] = (2).to_bytes(4, "little") + (28).to_bytes(
        4, "little"
    ) + (40).to_bytes(4, "little")
    data[104:108] = (0).to_bytes(4, "little")
    data[108:112] = (0).to_bytes(4, "little")

    data[112:118] = (6).to_bytes(2, "little") + (8).to_bytes(
        2, "little"
    ) + (4).to_bytes(2, "little")
    data[120:124] = (8).to_bytes(4, "little", signed=True)
    data[124:128] = (160 - 124).to_bytes(4, "little")
    data[136:140] = (24).to_bytes(4, "little", signed=True)
    data[140:144] = (160 - 140).to_bytes(4, "little")
    data[160:168] = (3).to_bytes(4, "little") + b"abc\0"
    data[168:172] = (0).to_bytes(4, "little")
    return bytes(data)


def _parallel_nested_data_root() -> bytes:
    """One six-field row closes an empty vector and nested parallel vectors."""

    data = bytearray(300)
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
    for slot, target in zip(
        (40, 44, 48, 52, 56, 60),
        (296, 68, 80, 88, 104, 112),
    ):
        data[slot : slot + 4] = (target - slot).to_bytes(4, "little")
    data[68:76] = (1).to_bytes(4, "little") + (7).to_bytes(4, "little")
    data[80:85] = (1).to_bytes(4, "little") + b"\x02"
    data[88:96] = (1).to_bytes(4, "little") + (144 - 92).to_bytes(
        4, "little"
    )
    data[104:108] = (0).to_bytes(4, "little")
    data[112:116] = (0).to_bytes(4, "little")
    data[296:300] = (0).to_bytes(4, "little")

    data[128:144] = (16).to_bytes(2, "little") + (40).to_bytes(
        2, "little"
    ) + b"".join(value.to_bytes(2, "little") for value in (4, 8, 12, 16, 20, 36))
    data[144:148] = (16).to_bytes(4, "little", signed=True)
    data[148:152] = (260 - 148).to_bytes(4, "little")
    data[152:156] = (5).to_bytes(4, "little")
    data[156:160] = (6).to_bytes(4, "little")
    data[160:164] = (200 - 160).to_bytes(4, "little")
    data[164:180] = bytes(16)
    data[180:184] = (272 - 180).to_bytes(4, "little")

    data[184:200] = (16).to_bytes(2, "little") + (16).to_bytes(
        2, "little"
    ) + b"".join(value.to_bytes(2, "little") for value in (0, 0, 0, 4, 8, 12))
    data[200:204] = (16).to_bytes(4, "little", signed=True)
    data[204:208] = (220 - 204).to_bytes(4, "little")
    data[208:212] = (232 - 208).to_bytes(4, "little")
    data[212:216] = (240 - 212).to_bytes(4, "little")
    data[220:232] = (2).to_bytes(4, "little") + (11).to_bytes(
        4, "little"
    ) + (13).to_bytes(4, "little")
    data[232:238] = (2).to_bytes(4, "little") + b"\x01\x00"
    data[240:252] = (2).to_bytes(4, "little") + bytes(8)
    data[260:268] = (3).to_bytes(4, "little") + b"abc\0"
    data[272:276] = (0).to_bytes(4, "little")
    return bytes(data)


def _parallel_target_data_root() -> bytes:
    data = bytearray(_parallel_nested_data_root() + bytes(84))
    def word(offset, value, width=4):
        data[offset:offset + width] = value.to_bytes(width, "little")
    word(40, 380 - 40)
    data[236:238] = bytes((16, 17))
    word(244, 300 - 244)
    word(248, 332 - 248)
    for table, vtable, target in ((300, 288, 308), (332, 326, 348), (348, 342, 356)):
        word(vtable, 6, 2)
        word(vtable + 2, 8, 2)
        word(vtable + 4, 4, 2)
        word(table, table - vtable)
        word(table + 4, target - table - 4)
    word(308, 3)
    data[312:316] = b"abc\0"
    word(356, 4)
    data[360:364] = b"\xff\x00\x01\x02"
    return bytes(data)


def _field2_streaming_root() -> bytes:
    """One field-2 row and its terminal anonymous width-4 vector."""

    data = bytearray(_data_root() + bytes(76))
    data[40:44] = (96 - 40).to_bytes(4, "little")
    data[96:100] = (1).to_bytes(4, "little")
    data[100:104] = (120 - 100).to_bytes(4, "little")
    data[104:120] = (16).to_bytes(2, "little") + (40).to_bytes(
        2, "little"
    ) + b"".join(value.to_bytes(2, "little") for value in (0, 0, 0, 4, 12, 36))
    data[120:124] = (16).to_bytes(4, "little", signed=True)
    data[124:132] = bytes(range(8))
    data[132:156] = bytes(range(24))
    data[156:160] = (4).to_bytes(4, "little")
    data[160:172] = (2).to_bytes(4, "little") + bytes(range(8))
    return bytes(data)


def _field2_streaming_shared_vtable_root() -> bytes:
    """Two terminal rows reuse one vtable between their child vectors."""

    data = bytearray(_data_root() + bytes(132))
    data[40:44] = (96 - 40).to_bytes(4, "little")
    data[96:100] = (2).to_bytes(4, "little")
    data[100:104] = (108 - 100).to_bytes(4, "little")
    data[104:108] = (176 - 104).to_bytes(4, "little")
    data[108:112] = (-52).to_bytes(4, "little", signed=True)
    data[144:148] = (4).to_bytes(4, "little")
    data[148:160] = (2).to_bytes(4, "little") + bytes(range(8))
    data[160:176] = (16).to_bytes(2, "little") + (40).to_bytes(
        2, "little"
    ) + b"".join(value.to_bytes(2, "little") for value in (0, 0, 0, 4, 12, 36))
    data[176:180] = (16).to_bytes(4, "little", signed=True)
    data[212:216] = (4).to_bytes(4, "little")
    data[216:228] = (2).to_bytes(4, "little") + bytes(range(8, 16))
    return bytes(data)


def _field2_streaming_full_layout_root() -> bytes:
    """The seventh corpus layout has all six anonymous fields present."""

    data = bytearray(_data_root() + bytes(88))
    data[40:44] = (96 - 40).to_bytes(4, "little")
    data[96:100] = (1).to_bytes(4, "little")
    data[100:104] = (120 - 100).to_bytes(4, "little")
    data[104:108] = (16).to_bytes(2, "little") + (52).to_bytes(2, "little")
    data[108:120] = b"".join(
        value.to_bytes(2, "little") for value in (4, 8, 12, 16, 24, 48)
    )
    data[120:124] = (16).to_bytes(4, "little", signed=True)
    data[124:168] = bytes(range(44))
    data[168:172] = (4).to_bytes(4, "little")
    data[172:184] = (2).to_bytes(4, "little") + bytes(range(8))
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
        field2 = result["anonymousField2TerminalSubgraph"]
        self.assertEqual(field2["status"], "exact_anonymous_eof_subgraph")
        self.assertEqual(field2["rowCount"], 0)
        self.assertTrue(field2["vectorEndsAtEof"])

    def test_streaming_field2_terminal_rows_have_exact_anonymous_representations(self):
        result = parse_streaming_file(
            "streaming",
            _packed(_field2_streaming_root()),
            native_layout_validated=True,
        )
        field2 = result["anonymousField2TerminalSubgraph"]
        self.assertEqual(field2["status"], "exact_anonymous_eof_subgraph")
        self.assertEqual(field2["rowCount"], 1)
        self.assertEqual(
            field2["field5Status"],
            "exact-anonymous-native-consumed-scalar32-vector",
        )
        self.assertEqual(
            field2["field5ValuesStatus"],
            "exact-anonymous-selected-build-native-scalar32-keys",
        )
        self.assertEqual(field2["field5ElementWidth"], 4)
        self.assertEqual(field2["field5VectorCount"], 1)
        self.assertEqual(field2["field5ValueCount"], 2)
        self.assertEqual(field2["structuralRange"], [96, 172])
        self.assertEqual(
            field2["rowObjectPartitionStatus"],
            "exact-anonymous-slot-spans",
        )
        self.assertEqual(field2["rowObjectPrefixBytes"], 4)
        self.assertEqual(
            field2["rowSlotSpans"],
            [
                {
                    "fieldIndex": 0,
                    "slotToNextBoundaryBytes": 4,
                    "presentCount": 0,
                    "absentCount": 1,
                    "totalSpanBytes": 0,
                    "status": "exact-native-consumed-representation",
                },
                {
                    "fieldIndex": 1,
                    "slotToNextBoundaryBytes": 4,
                    "presentCount": 0,
                    "absentCount": 1,
                    "totalSpanBytes": 0,
                    "status": "exact-native-consumed-representation",
                },
                {
                    "fieldIndex": 2,
                    "slotToNextBoundaryBytes": 4,
                    "presentCount": 0,
                    "absentCount": 1,
                    "totalSpanBytes": 0,
                    "status": "exact-native-consumed-representation",
                },
                {
                    "fieldIndex": 3,
                    "slotToNextBoundaryBytes": 8,
                    "presentCount": 1,
                    "absentCount": 0,
                    "totalSpanBytes": 8,
                    "status": "exact-native-consumed-representation",
                },
                {
                    "fieldIndex": 4,
                    "slotToNextBoundaryBytes": 24,
                    "presentCount": 1,
                    "absentCount": 0,
                    "totalSpanBytes": 24,
                    "status": "exact-native-consumed-representation",
                },
                {
                    "fieldIndex": 5,
                    "slotToNextBoundaryBytes": 4,
                    "presentCount": 1,
                    "absentCount": 0,
                    "totalSpanBytes": 4,
                    "status": "exact-vector-uoffset-slot",
                },
            ],
        )
        self.assertEqual(
            field2["rowFields0To4Status"],
            "exact-anonymous-native-consumed-layout",
        )
        self.assertEqual(
            field2["rowFields0To4RepresentationStatus"],
            "exact-selected-build-native-loads",
        )
        self.assertEqual(
            field2["rowFields0To5Status"],
            "exact-anonymous-native-consumed-layout",
        )
        self.assertEqual(
            field2["rowFields0To5RepresentationStatus"],
            "exact-selected-build-native-loads",
        )
        self.assertEqual(field2["rowSlotSpansMayContainPadding"], [])
        self.assertEqual(
            [item["representation"] for item in field2["rowFieldRepresentations"]],
            [
                "little-endian-scalar32",
                "little-endian-scalar32",
                "little-endian-scalar32",
                "little-endian-int32[2]",
                "little-endian-float32[6]",
                "count-prefixed-little-endian-scalar32[]",
            ],
        )
        self.assertEqual(
            field2["rowValueRecords"],
            [
                {
                    "rowIndex": 0,
                    "field0Scalar32Bits": None,
                    "field1Scalar32Bits": None,
                    "field2Scalar32Bits": None,
                    "field3Int32Lanes": [50462976, 117835012],
                    "field4Float32Bits": [
                        50462976,
                        117835012,
                        185207048,
                        252579084,
                        319951120,
                        387323156,
                    ],
                    "field5Scalar32Bits": [50462976, 117835012],
                }
            ],
        )
        self.assertEqual(
            field2["rowLayouts"],
            [
                {
                    "fieldCount": 6,
                    "objectSize": 40,
                    "presentFields": [3, 4, 5],
                    "fieldOffsets": [0, 0, 0, 4, 12, 36],
                    "count": 1,
                }
            ],
        )
        self.assertEqual(field2["wholeFileStatus"], "partial")

    def test_streaming_field2_representation_fails_closed_without_native_gate(self):
        field2 = parse_streaming_file(
            "streaming", _packed(_field2_streaming_root())
        )["anonymousField2TerminalSubgraph"]
        self.assertEqual(
            "unvalidated-native-contract",
            field2["rowFields0To4RepresentationStatus"],
        )
        self.assertEqual(
            "unvalidated-native-contract",
            field2["rowFields0To5RepresentationStatus"],
        )
        self.assertEqual(
            "unvalidated-native-contract",
            field2["field5ValuesStatus"],
        )
        self.assertEqual([], field2["rowFieldRepresentations"])
        self.assertEqual([], field2["rowValueRecords"])
        self.assertEqual([0, 1, 2, 3, 4], field2["rowSlotSpansMayContainPadding"])

    def test_field2_counts_offsets_and_layouts_fail_closed(self):
        clear = bytearray(_field2_streaming_root())
        clear[40:44] = (0).to_bytes(4, "little")
        with self.assertRaisesRegex(ValueError, "field 2 table slots vector target 40"):
            parse_streaming_file("streaming", _packed(bytes(clear)))

        clear = bytearray(_field2_streaming_root())
        clear[40:44] = (0xFFFF_FFF0).to_bytes(4, "little")
        with self.assertRaisesRegex(ValueError, "field 2 table slots vector target"):
            parse_streaming_file("streaming", _packed(bytes(clear)))

        clear = bytearray(_field2_streaming_root())
        clear[96:100] = (0xFFFF_FFFF).to_bytes(4, "little")
        with self.assertRaisesRegex(ValueError, "count 4294967295 .* exceeds payload"):
            parse_streaming_file("streaming", _packed(bytes(clear)))

        clear = bytearray(_field2_streaming_root())
        clear[100:104] = (0).to_bytes(4, "little")
        with self.assertRaisesRegex(ValueError, "row 0 table target 100"):
            parse_streaming_file("streaming", _packed(bytes(clear)))

        clear = bytearray(_field2_streaming_root())
        clear[100:104] = (0xFFFF_FFF0).to_bytes(4, "little")
        with self.assertRaisesRegex(ValueError, "row 0 table target .* outside payload"):
            parse_streaming_file("streaming", _packed(bytes(clear)))

        clear = bytearray(_field2_streaming_root())
        clear[120:124] = (0).to_bytes(4, "little", signed=True)
        with self.assertRaisesRegex(ValueError, "zero vtable displacement at 120"):
            parse_streaming_file("streaming", _packed(bytes(clear)))

        clear = bytearray(_field2_streaming_root())
        clear[104:106] = (3).to_bytes(2, "little")
        with self.assertRaisesRegex(ValueError, "vtable size 3 is invalid at 104"):
            parse_streaming_file("streaming", _packed(bytes(clear)))

        clear = bytearray(_field2_streaming_root())
        clear[106:108] = (200).to_bytes(2, "little")
        with self.assertRaisesRegex(ValueError, "object size 200 exceeds payload at 120"):
            parse_streaming_file("streaming", _packed(bytes(clear)))

        clear = bytearray(_field2_streaming_root())
        clear[104:106] = (14).to_bytes(2, "little")
        with self.assertRaisesRegex(ValueError, "shape .* is unsupported"):
            parse_streaming_file("streaming", _packed(bytes(clear)))

        clear = bytearray(_field2_streaming_root())
        clear[114:116] = (8).to_bytes(2, "little")
        with self.assertRaisesRegex(ValueError, "field offsets .* expected"):
            parse_streaming_file("streaming", _packed(bytes(clear)))

    def test_field2_field5_vector_fails_closed(self):
        clear = bytearray(_field2_streaming_root())
        clear[156:160] = (0).to_bytes(4, "little")
        with self.assertRaisesRegex(ValueError, "field 5 vector target 156"):
            parse_streaming_file("streaming", _packed(bytes(clear)))

        clear = bytearray(_field2_streaming_root())
        clear[156:160] = (0xFFFF_FFF0).to_bytes(4, "little")
        with self.assertRaisesRegex(ValueError, "field 5 vector target .* outside payload"):
            parse_streaming_file("streaming", _packed(bytes(clear)))

        clear = bytearray(_field2_streaming_root())
        clear[156:160] = (8).to_bytes(4, "little")
        clear[164:168] = (0).to_bytes(4, "little")
        with self.assertRaisesRegex(
            ValueError, "field 5 vector target 164, expected table end 160"
        ):
            parse_streaming_file("streaming", _packed(bytes(clear)))

        clear = bytearray(_field2_streaming_root())
        clear[160:164] = (0xFFFF_FFFF).to_bytes(4, "little")
        with self.assertRaisesRegex(ValueError, "field 5 count 4294967295 .* exceeds payload"):
            parse_streaming_file("streaming", _packed(bytes(clear)))

    def test_field2_truncation_overlap_and_trailing_bytes(self):
        with self.assertRaisesRegex(ValueError, "field 5 count 2 .* exceeds payload"):
            parse_streaming_file(
                "streaming", _packed(_field2_streaming_root()[:-1])
            )

        clear = bytearray(_data_root() + bytes(68))
        clear[40:44] = (96 - 40).to_bytes(4, "little")
        clear[96:100] = (1).to_bytes(4, "little")
        clear[100:104] = (4).to_bytes(4, "little")
        clear[104:108] = (-44).to_bytes(4, "little", signed=True)
        clear[140:144] = (4).to_bytes(4, "little")
        clear[144:148] = (2).to_bytes(4, "little")
        clear[148:164] = (16).to_bytes(2, "little") + (40).to_bytes(
            2, "little"
        ) + b"".join(
            value.to_bytes(2, "little") for value in (0, 0, 0, 4, 12, 36)
        )
        with self.assertRaisesRegex(ValueError, "terminal structural ranges overlap"):
            parse_streaming_file("streaming", _packed(bytes(clear)))

        with self.assertRaisesRegex(ValueError, "empty vector expected EOF 96, actual 97"):
            parse_streaming_file("init", _packed(_data_root() + b"\0"))

        for trailing in (b"\0", b"\x7f"):
            with self.subTest(trailing=trailing):
                with self.assertRaisesRegex(
                    ValueError, "terminal structural ranges end at 172, expected EOF 173"
                ):
                    parse_streaming_file(
                        "streaming", _packed(_field2_streaming_root() + trailing)
                    )

    def test_field2_shared_vtable_is_an_exact_reference(self):
        result = parse_streaming_file(
            "streaming", _packed(_field2_streaming_shared_vtable_root())
        )
        field2 = result["anonymousField2TerminalSubgraph"]
        self.assertEqual(field2["rowCount"], 2)
        self.assertEqual(field2["reusedReferences"], 1)
        self.assertEqual(field2["field5ReusedReferences"], 0)

    def test_field2_full_six_field_layout(self):
        result = parse_streaming_file(
            "streaming", _packed(_field2_streaming_full_layout_root())
        )
        self.assertEqual(
            result["anonymousField2TerminalSubgraph"]["rowLayouts"],
            [
                {
                    "fieldCount": 6,
                    "objectSize": 52,
                    "presentFields": [0, 1, 2, 3, 4, 5],
                    "fieldOffsets": [4, 8, 12, 16, 24, 48],
                    "count": 1,
                }
            ],
        )
        spans = result["anonymousField2TerminalSubgraph"]["rowSlotSpans"]
        self.assertEqual([item["presentCount"] for item in spans], [1] * 6)
        self.assertEqual(
            [item["slotToNextBoundaryBytes"] for item in spans],
            [4, 4, 4, 8, 24, 4],
        )

    def test_init_anonymous_group_subgraph(self):
        result = parse_streaming_file("init", _packed(_data_root(populated=True)))
        subgraph = result["anonymousGroupSubgraph"]
        self.assertEqual(subgraph["pairedGroupCount"], 1)
        self.assertEqual(subgraph["valueCount"], 2)
        self.assertEqual(subgraph["descriptorCount"], 1)
        self.assertEqual(subgraph["blobBytes"], 8)
        self.assertGreaterEqual(subgraph["reusedVtableReferences"], 1)
        self.assertEqual(subgraph["wholeFileStatus"], "partial")

    def test_anonymous_parallel_subgraph_and_ambiguity(self):
        for family in ("init", "streaming"):
            with self.subTest(family=family):
                result = parse_streaming_file(
                    family, _packed(_parallel_data_root())
                )
                subgraph = result["anonymousParallelSubgraph"]
                self.assertEqual(subgraph["status"], "exact_anonymous_subgraph")
                self.assertEqual(subgraph["parallelCount"], 2)
                self.assertEqual(
                    subgraph["fieldWidths"], {"3": 4, "4": 1, "5": 4}
                )
                self.assertEqual(subgraph["field4ByteValueCounts"], {1: 1, 2: 1})
                self.assertEqual(subgraph["field5RowCount"], 2)
                self.assertEqual(subgraph["field5Field0ReferenceCount"], 2)
                self.assertEqual(subgraph["field5Field0ReferencedBytes"], 6)
                self.assertEqual(subgraph["field5Field0Representation"], "ambiguous")
                self.assertEqual(
                    subgraph["field5Field0RepresentationCandidates"],
                    ["flatbuffer-string", "byte-vector-with-following-zero"],
                )
                self.assertEqual(subgraph["reusedReferences"], 2)
                self.assertEqual(subgraph["wholeFileStatus"], "partial")

    def test_parallel_nested_vectors_are_exact_but_elements_remain_opaque(self):
        result = parse_streaming_file(
            "streaming", _packed(_parallel_nested_data_root())
        )
        subgraph = result["anonymousParallelSubgraph"]
        self.assertEqual(subgraph["field5Field5VectorCount"], 1)
        self.assertEqual(subgraph["field5Field5ValueCount"], 0)
        self.assertEqual(subgraph["field5Field3NestedTableCount"], 1)
        self.assertEqual(
            subgraph["field5Field3NestedParallelWidths"],
            {"3": 4, "4": 1, "5": 4},
        )
        self.assertEqual(subgraph["field5Field3NestedParallelCount"], 2)
        self.assertEqual(
            subgraph["field5Field3NestedFieldValueCounts"],
            {"3": 2, "4": 2, "5": 2},
        )
        self.assertEqual(
            subgraph["field5Field3NestedElementStatus"], "partial-marker17-anonymous-framing"
        )

    def test_nested_marker_targets_frame_without_promoting_types(self):
        result = parse_streaming_file("streaming", _packed(_parallel_target_data_root()))
        graph = result["anonymousParallelSubgraph"]
        self.assertEqual(graph["nestedElementFramedCounts"], {17: 1})
        self.assertEqual(graph["nestedElementByteCounts"], {17: 4})
        self.assertEqual(graph["nestedElementOpaqueCount"], 1)
        self.assertEqual(graph["wholeFileStatus"], "partial")

    def test_nested_marker_targets_negative_fixtures(self):
        for offset, value, message in (
            (248, 0, "forward bounded target"),
            (248, 0xFFFFFFFF, "forward bounded target"),
            (356, 0xFFFFFFFF, "count"),
            (352, 0, "target"),
            (272, 1, "element width unresolved"),
        ):
            with self.subTest(offset=offset):
                data = bytearray(_parallel_target_data_root())
                data[offset:offset+4] = value.to_bytes(4, "little")
                with self.assertRaisesRegex(ValueError, message):
                    parse_streaming_file("streaming", _packed(bytes(data)))
        for offset, value, message in ((330, 6, "single field"), (346, 6, "single field")):
            with self.subTest(offset=offset):
                data = bytearray(_parallel_target_data_root())
                data[offset] = value
                with self.assertRaisesRegex(ValueError, message):
                    parse_streaming_file("streaming", _packed(bytes(data)))

    def test_nested_marker_truncated_and_trailing_fixtures(self):
        data = _parallel_target_data_root()
        for broken in (data[:363], data[:-1], data + b"\0"):
            with self.subTest(length=len(broken)):
                with self.assertRaises(ValueError):
                    parse_streaming_file("streaming", _packed(broken))
        with self.assertRaisesRegex(ValueError, "count"):
            _nested_reference_ranges(data[:363], 248, 17, "truncated-byte-body")

    def test_nested_wrapper_forward_vtable_and_ten_byte_shape(self):
        data = bytearray(_parallel_target_data_root())
        data[332:336] = (-10).to_bytes(4, "little", signed=True)
        result = parse_streaming_file("streaming", _packed(bytes(data)))
        self.assertEqual(result["anonymousParallelSubgraph"]["nestedElementFramedCounts"], {17: 1})
        data = bytearray(_parallel_target_data_root())
        data[328:330] = (10).to_bytes(2, "little")
        result = parse_streaming_file("streaming", _packed(bytes(data)))
        self.assertEqual(result["anonymousParallelSubgraph"]["nestedElementByteCounts"], {17: 4})

    def test_nested_marker_ranges_reject_nonidentical_overlap(self):
        data = bytearray(_parallel_target_data_root())
        data[148:152] = (364 - 148).to_bytes(4, "little")
        data[364:372] = (3).to_bytes(4, "little") + b"abc\0"
        data[356:360] = (8).to_bytes(4, "little")
        with self.assertRaisesRegex(ValueError, "overlap"):
            parse_streaming_file("streaming", _packed(bytes(data)))

    def test_unknown_nested_marker_stays_opaque_not_candidate_searched(self):
        data = bytearray(_parallel_target_data_root())
        data[236] = 255
        result = parse_streaming_file("streaming", _packed(bytes(data)))
        graph = result["anonymousParallelSubgraph"]
        self.assertEqual(graph["nestedElementFramedCounts"], {17: 1})
        self.assertEqual(graph["nestedElementOpaqueCount"], 1)

    def test_parallel_nested_offsets_and_counts_fail_closed(self):
        clear = bytearray(_parallel_nested_data_root())
        clear[160:164] = (0).to_bytes(4, "little")
        with self.assertRaisesRegex(ValueError, "field 3 table target"):
            parse_streaming_file("streaming", _packed(bytes(clear)))

        clear = bytearray(_parallel_nested_data_root())
        clear[232:236] = (1).to_bytes(4, "little")
        with self.assertRaisesRegex(ValueError, "nested parallel count mismatch"):
            parse_streaming_file("streaming", _packed(bytes(clear)))

        clear = bytearray(_parallel_nested_data_root())
        clear[240:244] = (0xFFFF_FFFF).to_bytes(4, "little")
        with self.assertRaisesRegex(ValueError, "count 4294967295"):
            parse_streaming_file("streaming", _packed(bytes(clear)))

    def test_parallel_subgraph_counts_and_offsets_fail_closed(self):
        clear = bytearray(_parallel_data_root())
        clear[68:72] = (1).to_bytes(4, "little")
        with self.assertRaisesRegex(ValueError, "parallel root count mismatch"):
            parse_streaming_file("init", _packed(bytes(clear)))

        clear = bytearray(_parallel_data_root())
        clear[92:96] = (0).to_bytes(4, "little")
        with self.assertRaisesRegex(ValueError, "invalid table target"):
            parse_streaming_file("init", _packed(bytes(clear)))

        clear = bytearray(_parallel_data_root())
        clear[88:92] = (0xFFFF_FFFF).to_bytes(4, "little")
        with self.assertRaisesRegex(ValueError, "count .* exceeds payload"):
            parse_streaming_file("init", _packed(bytes(clear)))

        clear = bytearray(_parallel_data_root())
        clear[80:84] = (1).to_bytes(4, "little")
        with self.assertRaisesRegex(ValueError, "field 4=1"):
            parse_streaming_file("init", _packed(bytes(clear)))

        clear = bytearray(_parallel_data_root())
        clear[48:52] = (0).to_bytes(4, "little")
        with self.assertRaisesRegex(ValueError, "field 4 vector target 48"):
            parse_streaming_file("init", _packed(bytes(clear)))

    def test_parallel_subgraph_truncation_and_terminator_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "actual EOF"):
            parse_streaming_file("init", _packed(_parallel_data_root()[:167]))

        clear = bytearray(_parallel_data_root())
        clear[167] = 1
        with self.assertRaisesRegex(ValueError, "expected following zero"):
            parse_streaming_file("init", _packed(bytes(clear)))

        clear = bytearray(_parallel_data_root())
        clear[124:128] = (0).to_bytes(4, "little")
        with self.assertRaisesRegex(ValueError, "target 124 from slot 124"):
            parse_streaming_file("init", _packed(bytes(clear)))

        clear = bytearray(_parallel_data_root())
        clear[160:164] = (0xFFFF_FFFF).to_bytes(4, "little")
        with self.assertRaisesRegex(ValueError, "length 4294967295"):
            parse_streaming_file("init", _packed(bytes(clear)))

    def test_parallel_subgraph_nonidentical_overlap_fails_closed(self):
        clear = bytearray(_parallel_data_root())
        clear[44:48] = (88 - 44).to_bytes(4, "little")
        with self.assertRaisesRegex(ValueError, "structural ranges overlap"):
            parse_streaming_file("init", _packed(bytes(clear)))

    def test_parallel_subgraph_remains_explicitly_partial(self):
        result = parse_streaming_file(
            "streaming", _packed(_field2_streaming_root())
        )
        self.assertEqual(
            result["anonymousParallelSubgraph"]["wholeFileStatus"], "partial"
        )

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

        clear = _data_root(populated=True)[:251]
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
