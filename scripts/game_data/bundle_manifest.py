"""Conservative framing reader for Endfield ``manifest.hgmmap`` files.

The installed build provides unusually strong evidence for this family: the
outer file is one Brotli stream and the decompressed bytes have two fixed
headers, three fixed-width row regions, and one trailing region.  This module
only certifies those boundaries.  The row fields and trailing bytes are kept
opaque because the available native metadata does not establish their
field-to-byte mapping or the postfix format.

``parse_bundle_manifest`` accepts the compressed ``.hgmmap`` bytes.  Use
``parse_decompressed_bundle_manifest`` only when a caller has already checked
the Brotli envelope itself.  Both APIs require complete consumption and
raise :class:`BinaryFormatError` with a bounded diagnostic on malformed data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


HEAD1 = 0xFF11FF11
HEAD2 = 0xF1F2F3F4
HEADER_SIZE = 156
TABLE1_OFFSET = 156
TABLE1_ROW_OFFSET = 160
TABLE1_ROW_SIZE = 32
TABLE2_ROW_SIZE = 56
TABLE3_ROW_SIZE = 48


class BinaryFormatError(ValueError):
    """Raised when a manifest cannot be consumed using observed framing."""


def _need(data: bytes, offset: int, size: int, label: str) -> None:
    if offset < 0 or size < 0 or offset > len(data) or size > len(data) - offset:
        raise BinaryFormatError(
            f"{label} range [{offset}, {offset + size}) is outside source "
            f"length {len(data)}"
        )


def _u32(data: bytes, offset: int, label: str) -> int:
    _need(data, offset, 4, label)
    return struct.unpack_from("<I", data, offset)[0]


def _utf16(data: bytes, offset: int, char_count: int, label: str) -> str:
    if char_count <= 0 or char_count > 1024:
        raise BinaryFormatError(f"{label} length {char_count} is outside 1..1024")
    byte_count = char_count * 2
    _need(data, offset, byte_count, label)
    try:
        return data[offset : offset + byte_count].decode("utf-16-le", errors="strict")
    except UnicodeDecodeError as exc:
        raise BinaryFormatError(f"{label} is not strict UTF-16LE: {exc}") from exc


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class OpaqueTable:
    """One fixed-width table whose individual fields are deliberately opaque."""

    name: str
    offset: int
    row_count: int
    row_size: int
    byte_length: int
    sha256: str
    first_row_hex: str
    last_row_hex: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "offset": self.offset,
            "rowCount": self.row_count,
            "rowSize": self.row_size,
            "byteLength": self.byte_length,
            "sha256": self.sha256,
            "firstRowHex": self.first_row_hex,
            "lastRowHex": self.last_row_hex,
            "fieldStatus": "opaque",
        }


@dataclass(frozen=True)
class BundleManifestSummary:
    """Exact framing summary for one compressed manifest."""

    source: str
    compressed_length: int
    compressed_sha256: str
    compressed_md5: str
    decompressed_length: int
    decompressed_sha256: str
    head1: int
    head1_text: str
    head2: int
    head2_text: str
    tables: tuple[OpaqueTable, ...]
    opaque_tail_offset: int
    opaque_tail_length: int
    opaque_tail_sha256: str
    opaque_tail_prefix_hex: str
    opaque_tail_suffix_hex: str
    consumed_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "endfield-bundle-manifest-hgmmap-v1",
            "source": self.source,
            "compressed": {
                "length": self.compressed_length,
                "sha256": self.compressed_sha256,
                "md5": self.compressed_md5,
            },
            "decompressed": {
                "length": self.decompressed_length,
                "sha256": self.decompressed_sha256,
            },
            "header": {
                "head1": f"0x{self.head1:08x}",
                "head1Text": self.head1_text,
                "head2": f"0x{self.head2:08x}",
                "head2Text": self.head2_text,
                "byteLength": HEADER_SIZE,
            },
            "tables": [table.to_dict() for table in self.tables],
            "opaqueTail": {
                "offset": self.opaque_tail_offset,
                "length": self.opaque_tail_length,
                "sha256": self.opaque_tail_sha256,
                "prefixHex": self.opaque_tail_prefix_hex,
                "suffixHex": self.opaque_tail_suffix_hex,
                "fieldStatus": "opaque",
            },
            "consumedBytes": self.consumed_bytes,
            "status": "format_framed_bounded_opaque",
        }


def _table(data: bytes, name: str, offset: int, row_count: int, row_size: int) -> OpaqueTable:
    if row_count <= 0:
        raise BinaryFormatError(f"{name} row count {row_count} is not positive")
    if row_count > (len(data) - offset) // row_size:
        raise BinaryFormatError(
            f"{name} row count {row_count} exceeds source bounds at offset {offset}"
        )
    byte_length = row_count * row_size
    _need(data, offset, byte_length, f"{name} rows")
    rows = data[offset : offset + byte_length]
    return OpaqueTable(
        name=name,
        offset=offset,
        row_count=row_count,
        row_size=row_size,
        byte_length=byte_length,
        sha256=_digest(rows),
        first_row_hex=rows[:row_size].hex(),
        last_row_hex=rows[-row_size:].hex(),
    )


def parse_decompressed_bundle_manifest(
    data: bytes, *, source: str = "<decompressed>"
) -> BundleManifestSummary:
    """Parse the observed decompressed layout with exact table boundaries.

    The first 32-bit value at offset 156 is a section-size witness equal to
    ``4 + table1_count * 32``.  The first row of table 1 repeats the count at
    offset 160.  Table 2's first row carries equivalent size/count witnesses at
    offsets +4/+8, and table 3 repeats its row count at +16.  These are kept as
    structural witnesses rather than assigned field names or meanings.
    """

    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError("data must be bytes-like")
    data = bytes(data)
    _need(data, 0, HEADER_SIZE, f"{source} header")
    head1 = _u32(data, 0, f"{source} HEAD1")
    if head1 != HEAD1:
        raise BinaryFormatError(f"{source}: HEAD1 0x{head1:08x} != 0x{HEAD1:08x}")
    head1_len = _u32(data, 4, f"{source} HEAD1 text length")
    head1_text = _utf16(data, 8, head1_len, f"{source} HEAD1 text")
    if head1_len != 36:
        raise BinaryFormatError(f"{source}: HEAD1 text length {head1_len} != observed 36")
    head2_offset = 8 + head1_len * 2
    head2 = _u32(data, head2_offset, f"{source} HEAD2")
    if head2 != HEAD2:
        raise BinaryFormatError(f"{source}: HEAD2 0x{head2:08x} != 0x{HEAD2:08x}")
    head2_len = _u32(data, head2_offset + 4, f"{source} HEAD2 text length")
    head2_text = _utf16(data, head2_offset + 8, head2_len, f"{source} HEAD2 text")
    if head2_len != 32:
        raise BinaryFormatError(f"{source}: HEAD2 text length {head2_len} != observed 32")
    if head2_offset + 8 + head2_len * 2 + 4 != HEADER_SIZE:
        raise BinaryFormatError(
            f"{source}: header arithmetic ends at "
            f"{head2_offset + 8 + head2_len * 2 + 4}, expected {HEADER_SIZE}"
        )
    if _u32(data, 152, f"{source} header padding") != 0:
        raise BinaryFormatError(f"{source}: non-zero 4-byte header padding")

    table1_section_size = _u32(data, TABLE1_OFFSET, f"{source} table1 size witness")
    if table1_section_size < 4 or (table1_section_size - 4) % TABLE1_ROW_SIZE:
        raise BinaryFormatError(
            f"{source}: table1 size witness {table1_section_size} is not 4 + N*32"
        )
    table1_count = (table1_section_size - 4) // TABLE1_ROW_SIZE
    if _u32(data, TABLE1_ROW_OFFSET, f"{source} table1 count witness") != table1_count:
        raise BinaryFormatError(f"{source}: table1 count witness disagrees with size witness")
    table1 = _table(data, "asset-like-32", TABLE1_ROW_OFFSET, table1_count, TABLE1_ROW_SIZE)

    table2_offset = TABLE1_OFFSET + table1_section_size
    _need(data, table2_offset, 12, f"{source} table2 witnesses")
    table2_size_witness = _u32(data, table2_offset + 4, f"{source} table2 size witness")
    table2_count = _u32(data, table2_offset + 8, f"{source} table2 count witness")
    if table2_size_witness != 4 + table2_count * TABLE2_ROW_SIZE:
        raise BinaryFormatError(
            f"{source}: table2 size witness {table2_size_witness} != "
            f"4 + count*56 ({4 + table2_count * TABLE2_ROW_SIZE})"
        )
    table2 = _table(data, "bundle-like-56", table2_offset, table2_count, TABLE2_ROW_SIZE)

    table3_offset = table2_offset + table2.byte_length
    table3_count = _u32(data, table3_offset + 16, f"{source} table3 count witness")
    if table3_count != table2_count:
        raise BinaryFormatError(
            f"{source}: table3 count witness {table3_count} != table2 count {table2_count}"
        )
    table3 = _table(data, "bundle-info-like-48", table3_offset, table3_count, TABLE3_ROW_SIZE)

    tail_offset = table3_offset + table3.byte_length
    _need(data, tail_offset, 0, f"{source} opaque tail")
    tail = data[tail_offset:]
    return BundleManifestSummary(
        source=source,
        compressed_length=0,
        compressed_sha256="",
        compressed_md5="",
        decompressed_length=len(data),
        decompressed_sha256=_digest(data),
        head1=head1,
        head1_text=head1_text,
        head2=head2,
        head2_text=head2_text,
        tables=(table1, table2, table3),
        opaque_tail_offset=tail_offset,
        opaque_tail_length=len(tail),
        opaque_tail_sha256=_digest(tail),
        opaque_tail_prefix_hex=tail[:32].hex(),
        opaque_tail_suffix_hex=tail[-32:].hex() if tail else "",
        consumed_bytes=len(data),
    )


def _brotli_decompress(data: bytes, source: str) -> bytes:
    try:
        import brotli
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise BinaryFormatError(
            f"{source}: Python 'brotli' package is required for .hgmmap input"
        ) from exc
    try:
        decoded = brotli.decompress(data)
    except Exception as exc:
        raise BinaryFormatError(f"{source}: Brotli stream is invalid: {exc}") from exc
    if not decoded:
        raise BinaryFormatError(f"{source}: Brotli stream produced an empty payload")
    return decoded


def parse_bundle_manifest(data: bytes, *, source: str = "<compressed>") -> BundleManifestSummary:
    """Decompress and parse one complete ``.hgmmap`` byte stream."""

    compressed = bytes(data)
    decoded = _brotli_decompress(compressed, source)
    parsed = parse_decompressed_bundle_manifest(decoded, source=f"{source} (decompressed)")
    assert isinstance(parsed, BundleManifestSummary)
    return BundleManifestSummary(
        source=source,
        compressed_length=len(compressed),
        compressed_sha256=_digest(compressed),
        compressed_md5=hashlib.md5(compressed).hexdigest(),
        decompressed_length=parsed.decompressed_length,
        decompressed_sha256=parsed.decompressed_sha256,
        head1=parsed.head1,
        head1_text=parsed.head1_text,
        head2=parsed.head2,
        head2_text=parsed.head2_text,
        tables=parsed.tables,
        opaque_tail_offset=parsed.opaque_tail_offset,
        opaque_tail_length=parsed.opaque_tail_length,
        opaque_tail_sha256=parsed.opaque_tail_sha256,
        opaque_tail_prefix_hex=parsed.opaque_tail_prefix_hex,
        opaque_tail_suffix_hex=parsed.opaque_tail_suffix_hex,
        consumed_bytes=parsed.consumed_bytes,
    )


def sweep(paths: Iterable[Path]) -> dict[str, Any]:
    """Parse a bounded set of files and retain deterministic failures."""

    results: list[dict[str, Any]] = []
    for path in paths:
        try:
            results.append(parse_bundle_manifest(path.read_bytes(), source=str(path)).to_dict())
        except (OSError, BinaryFormatError, TypeError, ValueError) as exc:
            results.append({"source": str(path), "status": "failed", "error": str(exc)})
    return {
        "format": "endfield-bundle-manifest-sweep-v1",
        "fileCount": len(results),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = sweep(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    failures = [row for row in report["results"] if row.get("status") == "failed"]
    print(f"BundleManifest sweep: {len(report['results']) - len(failures)}/{len(report['results'])} parsed")
    if failures:
        for row in failures:
            print(f"  FAIL {row['source']}: {row['error']}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
