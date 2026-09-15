from __future__ import annotations

import struct
import unittest

from scripts.asset_builder.cabmap import (
    CabEntry,
    CabMapError,
    cabmap_is_closed,
    parse_cabmap,
    summarise,
)


def dotnet_string(value: str) -> bytes:
    """A .NET BinaryWriter string: 7-bit encoded length, then UTF-8."""
    raw = value.encode("utf-8")
    length = len(raw)
    out = bytearray()
    while length >= 0x80:
        out.append((length & 0x7F) | 0x80)
        length >>= 7
    out.append(length)
    return bytes(out) + raw


def build(base: str, entries, *, declared_count: int | None = None, trailing: bytes = b"") -> bytes:
    out = bytearray(dotnet_string(base))
    out += struct.pack("<i", len(entries) if declared_count is None else declared_count)
    for cab, path, offset, deps in entries:
        out += dotnet_string(cab)
        out += dotnet_string(path)
        out += struct.pack("<q", offset)
        out += struct.pack("<i", len(deps))
        for dep in deps:
            out += dotnet_string(dep)
    return bytes(out) + trailing


class CabMapTests(unittest.TestCase):
    def test_parses_the_writer_layout_exactly(self) -> None:
        data = build(
            "D:/base",
            [("CAB-a", "one.chk", 0, ()), ("CAB-b", "two.chk", 4096, ("CAB-a",))],
        )
        base, entries = parse_cabmap(data)
        self.assertEqual(base, "D:/base")
        self.assertEqual(
            entries,
            [
                CabEntry("CAB-a", "one.chk", 0, ()),
                CabEntry("CAB-b", "two.chk", 4096, ("CAB-a",)),
            ],
        )

    def test_a_long_string_uses_a_multi_byte_length(self) -> None:
        # Over 127 bytes the .NET prefix spills into a second byte; a reader that
        # assumed one byte would desynchronise for the rest of the file.
        long_name = "C" * 200
        base, entries = parse_cabmap(build("b", [(long_name, "p", 1, ())]))
        self.assertEqual(entries[0].cab, long_name)

    def test_trailing_and_truncated_bytes_both_fail(self) -> None:
        entries = [("CAB-a", "one.chk", 0, ())]
        with self.assertRaisesRegex(CabMapError, "trailing bytes"):
            parse_cabmap(build("b", entries, trailing=b"\x00"))
        truncated = build("b", entries)[:-1]
        with self.assertRaises(CabMapError):
            parse_cabmap(truncated)

    def test_impossible_counts_are_rejected_rather_than_walked(self) -> None:
        # A corrupt count must not make the reader walk the whole file hunting for
        # entries that cannot be there.
        with self.assertRaisesRegex(CabMapError, "cannot fit"):
            parse_cabmap(build("b", [("CAB-a", "one.chk", 0, ())], declared_count=1_000_000))
        with self.assertRaisesRegex(CabMapError, "negative entry count"):
            parse_cabmap(build("b", [], declared_count=-1))

    def test_negative_offsets_and_dependency_counts_are_rejected(self) -> None:
        data = bytearray(build("b", [("CAB-a", "one.chk", 0, ())]))
        offset_at = len(dotnet_string("b")) + 4 + len(dotnet_string("CAB-a")) + len(dotnet_string("one.chk"))
        struct.pack_into("<q", data, offset_at, -1)
        with self.assertRaisesRegex(CabMapError, "negative offset"):
            parse_cabmap(bytes(data))

        data = bytearray(build("b", [("CAB-a", "one.chk", 0, ())]))
        struct.pack_into("<i", data, offset_at + 8, -3)
        with self.assertRaisesRegex(CabMapError, "negative dependency count"):
            parse_cabmap(bytes(data))

    def test_a_repeated_cab_name_is_not_a_map(self) -> None:
        # Two entries with one name make every lookup ambiguous, so the summary
        # must refuse to call the file closed even though it parsed exactly.
        entries = [CabEntry("CAB-a", "one.chk", 0, ()), CabEntry("CAB-a", "two.chk", 8, ())]

        class FakePath:
            name = "fake.bin"

            def read_bytes(self):
                return b""

            def stat(self):
                class S:
                    st_size = 0

                return S()

        summary = summarise(FakePath(), "b", entries)
        self.assertEqual(summary["entries"], 2)
        self.assertEqual(summary["distinctCabNames"], 1)
        self.assertFalse(cabmap_is_closed(summary))
        self.assertFalse(cabmap_is_closed(summarise(FakePath(), "b", [])))


if __name__ == "__main__":
    unittest.main()
