import hashlib
import struct
import unittest

from scripts.game_data.ifix_patch import (
    BinaryFormatError,
    OPAQUE_PREFIX_SIZE,
    PATCH_MAGIC,
    parse_ifix_patch,
)


def _string(value: str) -> bytes:
    raw = value.encode("utf-8")
    assert len(raw) < 0x80
    return bytes((len(raw),)) + raw


def _signature(name: str) -> bytes:
    # non-generic method descriptor: bool, declaring type, name, zero params
    return b"\0" + struct.pack("<i", 0) + _string(name) + struct.pack("<i", 0)


def _fixture() -> bytes:
    out = bytearray(b"opaque-prefix".ljust(OPAQUE_PREFIX_SIZE, b"P"))
    out += struct.pack("<Q", PATCH_MAGIC)
    out += _string("IFix.ILFixInterfaceBridge, Test")
    out += struct.pack("<i", 1) + _string("Test.Type")  # extern types
    out += struct.pack("<i", 1)  # one method
    out += struct.pack("<i", 1) + (b"\x01\x02\x03\x04\x05\x06\x07\x08")
    out += struct.pack("<i", 0)  # exception count
    out += struct.pack("<i", 1) + _signature("External")
    out += struct.pack("<i", 1) + _string("interned")
    out += struct.pack("<i", 1)  # field infos
    out += b"\1" + struct.pack("<i", 0) + _string("field") + struct.pack("<ii", 0, 3)
    out += struct.pack("<i", 0)  # static field types
    out += struct.pack("<i", 0)  # anonymous storeys
    out += _string("Wrappers") + _string("Test")
    out += struct.pack("<i", 1) + _signature("Fixed") + struct.pack("<i", 7)
    out += struct.pack("<i", 0)  # new classes
    return bytes(out)


class IFixPatchTests(unittest.TestCase):
    def test_fixture_is_fully_consumed_and_keeps_opaque_body(self):
        data = _fixture()
        result = parse_ifix_patch(data, source="fixture")
        self.assertEqual(result["consumedBytes"], len(data))
        self.assertEqual(result["input"]["sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(result["methods"]["records"][0]["codeSize"], 1)
        self.assertEqual(result["methods"]["records"][0]["code"]["fieldStatus"], "opaque")
        self.assertEqual(result["methods"]["records"][0]["code"]["unitCount"], 1)
        self.assertEqual(result["methods"]["records"][0]["code"]["unitSize"], 8)
        self.assertEqual(result["methods"]["records"][0]["exceptions"]["unitSize"], 24)
        self.assertEqual(result["fixRecords"]["records"][0]["activationStatus"], "not-established-by-file-framing")

    def test_rejects_magic_mutation(self):
        data = bytearray(_fixture())
        data[OPAQUE_PREFIX_SIZE] ^= 0x01
        with self.assertRaises(BinaryFormatError):
            parse_ifix_patch(data, source="bad-magic")

    def test_rejects_truncated_method_body(self):
        with self.assertRaises(BinaryFormatError):
            parse_ifix_patch(_fixture()[:-1], source="truncated")

    def test_rejects_trailing_bytes(self):
        with self.assertRaises(BinaryFormatError):
            parse_ifix_patch(_fixture() + b"x", source="trailing")

    def test_rejects_invalid_boolean(self):
        data = bytearray(_fixture())
        # Locate the field's is-new byte from the fixture's deterministic
        # framing rather than relying on a production offset.
        marker = b"\1\0\0\0\0\x05field"
        offset = data.index(marker)
        data[offset] = 2
        with self.assertRaises(BinaryFormatError):
            parse_ifix_patch(data, source="bad-bool")

    def test_rejects_noncanonical_string_length(self):
        data = bytearray(_fixture())
        length_offset = OPAQUE_PREFIX_SIZE + 8
        length = data[length_offset]
        self.assertLess(length, 0x80)
        data[length_offset : length_offset + 1] = bytes((length | 0x80, 0))
        with self.assertRaises(BinaryFormatError):
            parse_ifix_patch(data, source="overlong-string-length")


if __name__ == "__main__":
    unittest.main()
