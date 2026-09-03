"""Strict framing for current Endfield IrradianceVolume files.

This module intentionally stops at the proven region envelope.  The 16-byte
records are retained as opaque bytes: their internal fields and ordering have
not been established by this parser.  It also validates the independently
proven filename table in v3/legacy ``index.bytes`` files.  Everything after
that table remains bounded opaque bytes; no payload fields are named here.
"""

from __future__ import annotations

import io
import math
import re
import struct
from dataclasses import dataclass
from typing import BinaryIO


REGION_HEADER_SIZE = 44
REGION_RECORD_SIZE = 16
REGION_HEADER_WORD0 = 4096
MAX_DIMENSION = 1_000_000
INDEX_HEADER_SIZE = 4
INDEX_MAGIC_V3_SCENE = 0x03000003
INDEX_MAGIC_V3_GACHA = 0x03000002
INDEX_MAGIC_LEGACY_GACHA = 0x01000043
INDEX_MAGICS = frozenset(
    (INDEX_MAGIC_V3_SCENE, INDEX_MAGIC_V3_GACHA, INDEX_MAGIC_LEGACY_GACHA)
)
MAX_INDEX_SIZE = 64 * 1024 * 1024
MAX_INDEX_FILENAME_COUNT = 1_000_000
MAX_INDEX_FILENAME_BYTES = 4096
_INDEX_FILENAME_RE = re.compile(r"iv_[0-9]+(?:_[0-9]+){1,2}\.bytes\Z")


class IrradianceFormatError(ValueError):
    """Raised when a region envelope is malformed or not fully consumed."""


@dataclass(frozen=True)
class RegionIvHeader:
    header_word0: int
    header_size: int
    header_floats: tuple[float, float, float, float, float, float]
    shape: tuple[int, int, int]

    @property
    def record_count(self) -> int:
        return self.shape[0] * self.shape[1] * self.shape[2]

    @property
    def record_bytes(self) -> int:
        return self.record_count * REGION_RECORD_SIZE


@dataclass(frozen=True)
class IrradianceIndex:
    """The proven outer/index filename framing only.

    ``opaque_remainder_length`` deliberately records a length rather than
    retaining or interpreting the remainder.  ``magic`` is the original
    numeric little-endian value so the v3 scene, v3 Gacha, and legacy Gacha
    identities cannot be folded together.
    """

    magic: int
    table_offset: int
    filename_count: int
    filenames: tuple[str, ...]
    table_end: int
    opaque_remainder_length: int


def _read_exact(stream: BinaryIO, count: int, field: str) -> bytes:
    if count < 0:
        raise IrradianceFormatError(f"{field}: negative read length {count}")
    data = stream.read(count)
    if data is None or len(data) != count:
        actual = 0 if data is None else len(data)
        raise IrradianceFormatError(
            f"{field}: short read expected {count}, actual {actual}"
        )
    return data


def _checked_record_bytes(shape: tuple[int, int, int]) -> int:
    count = 1
    for axis, value in zip(("x", "y", "z"), shape):
        if value <= 0:
            raise IrradianceFormatError(f"shape.{axis}: expected positive value, got {value}")
        if value > MAX_DIMENSION:
            raise IrradianceFormatError(
                f"shape.{axis}: value {value} exceeds bound {MAX_DIMENSION}"
            )
        if count > (2**63 - 1) // value:
            raise IrradianceFormatError("shape product overflows signed 64-bit range")
        count *= value
    if count > (2**63 - 1) // REGION_RECORD_SIZE:
        raise IrradianceFormatError("record byte count overflows signed 64-bit range")
    return count * REGION_RECORD_SIZE


def read_region_header(stream: BinaryIO) -> RegionIvHeader:
    raw = _read_exact(stream, REGION_HEADER_SIZE, "region header")
    header_word0, header_size = struct.unpack_from("<II", raw, 0)
    floats = struct.unpack_from("<6f", raw, 8)
    shape = struct.unpack_from("<3I", raw, 32)
    if header_word0 != REGION_HEADER_WORD0:
        raise IrradianceFormatError(
            f"header_word0 mismatch expected {REGION_HEADER_WORD0}, actual {header_word0}"
        )
    if header_size != REGION_HEADER_SIZE:
        raise IrradianceFormatError(
            f"header_size mismatch expected {REGION_HEADER_SIZE}, actual {header_size}"
        )
    if not all(math.isfinite(value) for value in floats):
        raise IrradianceFormatError("header floats contain non-finite value")
    _checked_record_bytes(shape)
    return RegionIvHeader(header_word0, header_size, tuple(floats), tuple(shape))


def validate_region_stream(stream: BinaryIO) -> RegionIvHeader:
    """Validate a complete region file without retaining its record payload."""

    header = read_region_header(stream)
    expected = header.record_bytes
    remaining = expected
    while remaining:
        chunk = stream.read(min(1024 * 1024, remaining))
        if not chunk:
            raise IrradianceFormatError(
                f"region records: short read expected {expected}, actual {expected - remaining}"
            )
        remaining -= len(chunk)
    extra = stream.read(1)
    if extra:
        raise IrradianceFormatError(
            f"region records: trailing bytes after expected {expected}: actual at least {expected + 1}"
        )
    return header


def parse_region_bytes(data: bytes) -> RegionIvHeader:
    """Validate fixture-sized bytes with the same exact-consumption rules."""

    return validate_region_stream(io.BytesIO(data))


def _index_filename_candidate(
    data: bytes, table_offset: int
) -> tuple[IrradianceIndex | None, str | None]:
    """Try one even-aligned count offset without guessing other fields."""

    if table_offset + 4 > len(data):
        return None, "count truncated"
    count = struct.unpack_from("<I", data, table_offset)[0]
    if count > MAX_INDEX_FILENAME_COUNT:
        return None, f"count overflow {count} > {MAX_INDEX_FILENAME_COUNT}"
    if count == 0:
        return None, None

    cursor = table_offset + 4
    names: list[str] = []
    for index in range(count):
        if cursor + 4 > len(data):
            return None, f"entry {index}: length truncated"
        length = struct.unpack_from("<I", data, cursor)[0]
        if length == 0 or length % 2:
            return None, f"entry {index}: invalid UTF-16LE byte length {length}"
        if length > MAX_INDEX_FILENAME_BYTES:
            return None, (
                f"entry {index}: filename length {length} exceeds bound "
                f"{MAX_INDEX_FILENAME_BYTES}"
            )
        string_offset = cursor + 4
        string_end = string_offset + length
        if string_end > len(data):
            return None, f"entry {index}: string truncated"
        try:
            name = data[string_offset:string_end].decode("utf-16le", "strict")
        except UnicodeDecodeError as exc:
            return None, f"entry {index}: invalid UTF-16LE ({exc.reason})"
        if not _INDEX_FILENAME_RE.fullmatch(name):
            return None, f"entry {index}: invalid filename {name!r}"
        names.append(name)
        cursor = string_end

    if len(set(names)) != len(names):
        return None, "duplicate filename in table"
    return (
        IrradianceIndex(
            magic=struct.unpack_from("<I", data, 0)[0],
            table_offset=table_offset,
            filename_count=count,
            filenames=tuple(names),
            table_end=cursor,
            opaque_remainder_length=len(data) - cursor,
        ),
        None,
    )


def parse_index_bytes(data: bytes) -> IrradianceIndex:
    """Validate the proven index filename table and retain the tail as opaque.

    The table start is not fixed across current files, so every even byte
    offset after the magic is considered.  A candidate is valid only when its
    explicit count and all length-prefixed strings form the complete current
    ``iv_*.bytes`` filename convention.  Exactly one candidate is required;
    this makes table-boundary ambiguity fail closed.  Bytes after the table
    are intentionally not parsed.
    """

    if len(data) < INDEX_HEADER_SIZE:
        raise IrradianceFormatError(
            f"index header: short read expected {INDEX_HEADER_SIZE}, actual {len(data)}"
        )
    if len(data) > MAX_INDEX_SIZE:
        raise IrradianceFormatError(
            f"index size {len(data)} exceeds bound {MAX_INDEX_SIZE}"
        )
    magic = struct.unpack_from("<I", data, 0)[0]
    if magic not in INDEX_MAGICS:
        raise IrradianceFormatError(f"index magic unsupported: 0x{magic:08x}")

    candidates: list[IrradianceIndex] = []
    diagnostics: list[str] = []
    for table_offset in range(INDEX_HEADER_SIZE, len(data) - 3, 2):
        candidate, diagnostic = _index_filename_candidate(data, table_offset)
        if candidate is not None:
            candidates.append(candidate)
        elif diagnostic is not None and len(diagnostics) < 8:
            diagnostics.append(f"offset {table_offset}: {diagnostic}")

    if len(candidates) != 1:
        if len(candidates) > 1:
            offsets = ", ".join(str(item.table_offset) for item in candidates[:8])
            raise IrradianceFormatError(
                f"index filename table boundary ambiguous: "
                f"{len(candidates)} candidates ({offsets})"
            )
        detail = "; ".join(diagnostics) if diagnostics else "no candidate"
        raise IrradianceFormatError(f"index filename table not found: {detail}")
    return candidates[0]
