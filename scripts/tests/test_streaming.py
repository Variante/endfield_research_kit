import unittest

from scripts.game_data.streaming import parse_streaming_file


def _root(kind: str, devonly_info: bool = False) -> bytes:
    if kind == "info":
        if devonly_info:
            root, vtable_size, object_size, fields = 16, 10, 16, [4, 8, 12]
        else:
            root, vtable_size, object_size, fields = 16, 12, 20, [4, 8, 12, 16]
        size = 64
    else:
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


class StreamingTests(unittest.TestCase):
    def test_compressed_init_exact_root(self):
        clear = _root("init")
        packed = len(clear).to_bytes(4, "little") + _literal_only(clear)
        result = parse_streaming_file("init", packed)
        self.assertEqual(result["encoding"], "inverted_lz4")
        self.assertEqual(result["decodedBytes"], len(clear))

    def test_raw_devonly_streaming_root(self):
        result = parse_streaming_file("streaming", _root("streaming"), allow_raw=True)
        self.assertEqual(result["encoding"], "raw_flatbuffer")

    def test_raw_info_root(self):
        result = parse_streaming_file("info", _root("info"))
        self.assertEqual(result["root"]["fieldCount"], 4)

    def test_raw_devonly_info_root(self):
        result = parse_streaming_file("info", _root("info", devonly_info=True))
        self.assertEqual(result["root"]["fieldCount"], 3)

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
