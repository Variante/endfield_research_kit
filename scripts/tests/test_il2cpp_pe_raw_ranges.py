"""Raw-file addressing must not turn virtual BSS into another section's bytes."""
from __future__ import annotations

import struct
import tempfile
import unittest
from pathlib import Path

from scripts.tests.test_il2cpp_generic_instantiations import load_helper


BASE = 0x180000000


def fixture() -> bytearray:
    data = bytearray(0x220)
    struct.pack_into("<I", data, 0x3C, 0x80)
    struct.pack_into("<I", data, 0x80, 0x4550)
    struct.pack_into("<H", data, 0x86, 2)
    struct.pack_into("<H", data, 0x94, 0xF0)
    struct.pack_into("<H", data, 0x98, 0x20B)
    struct.pack_into("<Q", data, 0xB0, BASE)
    for offset, name, va, raw in ((0x188, b".data", 0x1000, 0x200),
                                 (0x1B0, b".next", 0x2000, 0x210)):
        data[offset:offset + len(name)] = name
        struct.pack_into("<IIII", data, offset + 8, 0x40, va, 0x10, raw)
    data[0x200:0x210] = b"abc\0" + bytes(range(4, 16))
    data[0x210:0x220] = b"NEVER_BSS_BYTES\0"
    return data


class PeRawRangeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_helper()

    def load(self, data=None):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "fixture.dll"
        path.write_bytes(fixture() if data is None else data)
        return self.module.PeImage(path)

    def test_normal_raw_scalar_and_string(self):
        pe = self.load()
        self.assertEqual(pe.file_offset_for_rva(0x1000), (0x200, ".data"))
        self.assertEqual(pe.bytes_at_va(BASE + 0x1000, 16), bytes(fixture()[0x200:0x210]))
        self.assertEqual(pe.u32_at_va(BASE + 0x1000), 0x00636261)
        self.assertEqual(pe.u64_at_va(BASE + 0x2000), int.from_bytes(b"NEVER_BS", "little"))
        self.assertEqual(pe.c_string_at_va(BASE + 0x1000), "abc")

    def test_virtual_tail_is_not_next_sections_raw_bytes(self):
        pe = self.load()
        self.assertEqual(pe.file_offset_for_rva(0x1010), (None, ".data"))
        for read in (lambda: pe.bytes_at_va(BASE + 0x1010, 8),
                     lambda: pe.u64_at_va(BASE + 0x1010),
                     lambda: pe.u32_at_va(BASE + 0x1010)):
            with self.assertRaisesRegex(ValueError, "fixture.dll.*expected=.*actual=unbacked"):
                read()
        self.assertTrue(pe.c_string_at_va(BASE + 0x1010).startswith("<bad-va:"))

    def test_range_cannot_cross_raw_section_end(self):
        pe = self.load()
        with self.assertRaisesRegex(ValueError, "expected=8.*actual available=4"):
            pe.u64_at_va(BASE + 0x100C)

    def test_unterminated_string_does_not_find_next_section_nul(self):
        pe = self.load()
        with self.assertRaisesRegex(ValueError, "expected=NUL.*actual=unterminated"):
            pe.c_string_at_va(BASE + 0x1004)

    def test_truncated_raw_section(self):
        with self.assertRaisesRegex(ValueError, "fixture.dll.*file offset=528.*expected=16.*actual available=8"):
            self.load(fixture()[:-8])

    def test_truncated_header_and_malformed_section_count(self):
        with self.assertRaisesRegex(ValueError, "file offset=60.*expected=4"):
            self.load(b"MZ")
        data = fixture()
        struct.pack_into("<H", data, 0x86, 0xFFFF)
        with self.assertRaisesRegex(ValueError, "expected=2621400 raw bytes"):
            self.load(data)

    def test_malformed_raw_offset(self):
        data = fixture()
        struct.pack_into("<I", data, 0x188 + 20, 0xFFFFFFF0)
        with self.assertRaisesRegex(ValueError, "file offset=4294967280.*actual available=0"):
            self.load(data)

    def test_negative_sizes_and_file_offsets(self):
        pe = self.load()
        with self.assertRaisesRegex(ValueError, "expected=-1"):
            pe.bytes_at_va(BASE + 0x1000, -1)
        with self.assertRaisesRegex(ValueError, "file offset=-1"):
            pe.u32_at_file(-1)

    def test_ambiguous_virtual_sections(self):
        data = fixture()
        struct.pack_into("<I", data, 0x1B0 + 12, 0x1000)
        pe = self.load(data)
        with self.assertRaisesRegex(ValueError, "expected=one section actual=2"):
            pe.file_offset_for_rva(0x1000)

    def test_overlay_bytes_are_not_implicitly_addressable(self):
        pe = self.load(fixture() + b"unmapped overlay")
        self.assertEqual(pe.file_offset_for_rva(0x2040), (None, ""))
        self.assertEqual(pe.file_offset_for_rva(0x2010), (None, ".next"))


if __name__ == "__main__":
    unittest.main()
