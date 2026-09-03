"""Conservative framing reader for Endfield ``manifest.hgmmap`` files.

The installed build provides unusually strong evidence for this family: the
outer file is one Brotli stream and the decompressed bytes have two fixed
headers, three size/count-delimited fixed-width row regions, and one
size-delimited variable region with a repeated footer witness.  This module
only certifies those boundaries.  Row fields and variable-region bytes are
kept opaque because the available native metadata does not establish their
field-to-byte mapping or the variable records' internal format.

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
TABLE1_SECTION_OFFSET = HEADER_SIZE
TABLE_SECTION_HEADER_SIZE = 8
TABLE1_ROW_SIZE = 32
TABLE2_ROW_SIZE = 56
TABLE3_ROW_SIZE = 48
VARIABLE_REGION_FOOTER_SIZE = 4


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
    section_offset: int
    section_size_witness: int
    offset: int
    row_count: int
    row_size: int
    byte_length: int
    sha256: str
    first_row_hex: str
    last_row_hex: str
    row_sequence_word_offset: int | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {
            "name": self.name,
            "sectionOffset": self.section_offset,
            "sectionSizeWitness": self.section_size_witness,
            "offset": self.offset,
            "rowCount": self.row_count,
            "rowSize": self.row_size,
            "byteLength": self.byte_length,
            "sha256": self.sha256,
            "firstRowHex": self.first_row_hex,
            "lastRowHex": self.last_row_hex,
            "fieldStatus": "opaque",
        }
        if self.row_sequence_word_offset is not None:
            result["rowSequenceWitness"] = {
                "wordOffset": self.row_sequence_word_offset,
                "first": 0,
                "last": self.row_count - 1,
                "mismatchCount": 0,
                "fieldStatus": "structural-only",
            }
        return result


@dataclass(frozen=True)
class OpaqueVariableRegion:
    """One bounded variable-width region whose internal records stay opaque."""

    section_offset: int
    size_witness: int
    payload_offset: int
    payload_length: int
    payload_sha256: str
    payload_prefix_hex: str
    payload_suffix_hex: str
    footer_offset: int
    footer_size_witness: int
    end_offset: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "sectionOffset": self.section_offset,
            "sizeWitness": self.size_witness,
            "payloadOffset": self.payload_offset,
            "payloadLength": self.payload_length,
            "payloadSha256": self.payload_sha256,
            "payloadPrefixHex": self.payload_prefix_hex,
            "payloadSuffixHex": self.payload_suffix_hex,
            "footerOffset": self.footer_offset,
            "footerSizeWitness": self.footer_size_witness,
            "endOffset": self.end_offset,
            "recordStatus": "opaque",
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
    variable_region: OpaqueVariableRegion
    consumed_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "endfield-bundle-manifest-hgmmap-v2",
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
            "opaqueVariableRegion": self.variable_region.to_dict(),
            "consumedBytes": self.consumed_bytes,
            "status": "format_framed_bounded_opaque",
        }


def _table_section(
    data: bytes,
    name: str,
    section_offset: int,
    row_size: int,
    source: str,
    *,
    row_sequence_word_offset: int | None = None,
) -> tuple[OpaqueTable, int]:
    _need(data, section_offset, TABLE_SECTION_HEADER_SIZE, f"{source} {name} section header")
    section_size = _u32(data, section_offset, f"{source} {name} size witness")
    row_count = _u32(data, section_offset + 4, f"{source} {name} count witness")
    if row_count <= 0:
        raise BinaryFormatError(f"{name} row count {row_count} is not positive")
    expected_size = 4 + row_count * row_size
    if section_size != expected_size:
        raise BinaryFormatError(
            f"{source}: {name} size witness {section_size} != "
            f"4 + count*{row_size} ({expected_size})"
        )
    row_offset = section_offset + TABLE_SECTION_HEADER_SIZE
    if row_count > (len(data) - row_offset) // row_size:
        raise BinaryFormatError(
            f"{name} row count {row_count} exceeds source bounds at offset {row_offset}"
        )
    byte_length = row_count * row_size
    _need(data, row_offset, byte_length, f"{name} rows")
    rows = data[row_offset : row_offset + byte_length]
    if row_sequence_word_offset is not None:
        if (
            row_sequence_word_offset < 0
            or row_sequence_word_offset + 4 > row_size
            or row_sequence_word_offset % 4
        ):
            raise ValueError("row sequence witness must be an aligned word inside each row")
        for index in range(row_count):
            value = struct.unpack_from(
                "<I", rows, index * row_size + row_sequence_word_offset
            )[0]
            if value != index:
                raise BinaryFormatError(
                    f"{source}: {name} row {index} sequence witness {value} != {index} "
                    f"at row byte offset {row_sequence_word_offset}"
                )
    table = OpaqueTable(
        name=name,
        section_offset=section_offset,
        section_size_witness=section_size,
        offset=row_offset,
        row_count=row_count,
        row_size=row_size,
        byte_length=byte_length,
        sha256=_digest(rows),
        first_row_hex=rows[:row_size].hex(),
        last_row_hex=rows[-row_size:].hex(),
        row_sequence_word_offset=row_sequence_word_offset,
    )
    # The size word measures the following count word plus all rows.  Returning
    # this arithmetic boundary prevents a count word from being mistaken for
    # the first row and prevents the final row bytes from leaking into the next
    # section.
    return table, section_offset + 4 + section_size


def _variable_region(data: bytes, section_offset: int, source: str) -> OpaqueVariableRegion:
    _need(data, section_offset, 8, f"{source} variable-region envelope")
    size_witness = _u32(data, section_offset, f"{source} variable-region size witness")
    payload_offset = section_offset + 4
    _need(
        data,
        payload_offset,
        size_witness + VARIABLE_REGION_FOOTER_SIZE,
        f"{source} variable-region payload and footer",
    )
    footer_offset = payload_offset + size_witness
    footer_size_witness = _u32(data, footer_offset, f"{source} variable-region footer")
    if footer_size_witness != size_witness:
        raise BinaryFormatError(
            f"{source}: variable-region footer size witness {footer_size_witness} != "
            f"leading witness {size_witness}"
        )
    end_offset = footer_offset + VARIABLE_REGION_FOOTER_SIZE
    if end_offset != len(data):
        raise BinaryFormatError(
            f"{source}: trailing bytes [{end_offset}, {len(data)}) "
            f"({len(data) - end_offset} bytes) after variable-region footer"
        )
    payload = data[payload_offset:footer_offset]
    return OpaqueVariableRegion(
        section_offset=section_offset,
        size_witness=size_witness,
        payload_offset=payload_offset,
        payload_length=len(payload),
        payload_sha256=_digest(payload),
        payload_prefix_hex=payload[:32].hex(),
        payload_suffix_hex=payload[-32:].hex() if payload else "",
        footer_offset=footer_offset,
        footer_size_witness=footer_size_witness,
        end_offset=end_offset,
    )


def parse_decompressed_bundle_manifest(
    data: bytes, *, source: str = "<decompressed>"
) -> BundleManifestSummary:
    """Parse the observed decompressed layout with exact table boundaries.

    Each fixed-width section starts with a 32-bit size witness followed by a
    32-bit row count.  The size is exactly ``4 + count * row_size`` and measures
    the count word plus rows, not its own four bytes.  The terminal variable
    region uses a leading size word, that many opaque bytes, and the same size
    word as its footer.  These are structural witnesses only.
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

    table1, table2_offset = _table_section(
        data, "fixed-width-32", TABLE1_SECTION_OFFSET, TABLE1_ROW_SIZE, source
    )
    table2, table3_offset = _table_section(
        data, "fixed-width-56", table2_offset, TABLE2_ROW_SIZE, source
    )
    table3, variable_region_offset = _table_section(
        data,
        "fixed-width-48",
        table3_offset,
        TABLE3_ROW_SIZE,
        source,
        row_sequence_word_offset=0,
    )
    if table3.row_count != table2.row_count:
        raise BinaryFormatError(
            f"{source}: fixed-width-48 count witness {table3.row_count} != "
            f"fixed-width-56 count {table2.row_count}"
        )
    variable_region = _variable_region(data, variable_region_offset, source)
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
        variable_region=variable_region,
        consumed_bytes=variable_region.end_offset,
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
        variable_region=parsed.variable_region,
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
