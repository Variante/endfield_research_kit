"""Strict framing for the current Endfield IrradianceVolume region files.

This module intentionally stops at the proven region envelope.  The 16-byte
records are retained as opaque bytes: their internal fields and ordering have
not been established by this parser.
"""

from __future__ import annotations

import io
import math
import struct
from dataclasses import dataclass
from typing import BinaryIO


REGION_HEADER_SIZE = 44
REGION_RECORD_SIZE = 16
REGION_HEADER_WORD0 = 4096
MAX_DIMENSION = 1_000_000


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
