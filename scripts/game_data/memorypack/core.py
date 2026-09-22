"""Bounds-checked primitives shared by the focused MemoryPack decoders."""

from __future__ import annotations

import struct
from typing import Any

from scripts.game_data.contracts import CONTRACTS_DIR  # noqa: F401  (re-exported for the MemoryPack readers)

MEMORYPACK_NULL_COUNT = 0xFFFFFFFF
MEMORYPACK_UNION_WIDE_TAG = 0xFA
MEMORYPACK_SCHEMA_SOURCE_NOTE = (
    "field order recovered from installed IL2CPP ForMemoryPack setter metadata"
)
STRING_SAMPLE_MAX_CHARS = 360


def format_offset(offset: int | None) -> str:
    return f"0x{offset:x}" if isinstance(offset, int) and offset >= 0 else ""


def scan_length_prefixed_utf8_string_hits(
    data: bytes,
    *,
    start: int = 0,
    max_scan_bytes: int | None = None,
    max_samples: int = 128,
    min_length: int = 2,
    max_length: int = 160,
) -> list[dict[str, Any]]:
    end = len(data) if max_scan_bytes is None else min(len(data), start + max_scan_bytes)
    hits: list[dict[str, Any]] = []
    seen: set[tuple[int, str]] = set()
    for pos in range(max(start, 0), max(start, end - 4)):
        length = struct.unpack_from("<I", data, pos)[0]
        if length < min_length or length > max_length or pos + 4 + length > end:
            continue
        raw = data[pos + 4 : pos + 4 + length]
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if any(ord(ch) < 32 for ch in text):
            continue
        if not any(ch.isalnum() for ch in text):
            continue
        key = (pos, text)
        if key in seen:
            continue
        seen.add(key)
        hits.append({"offset": format_offset(pos), "length": length, "value": text})
        if len(hits) >= max_samples:
            break
    return hits


def unique_strings(values: list[str], limit: int) -> list[str]:
    out: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in out:
            out.append(text)
            if len(out) >= limit:
                break
    return out


def read_memorypack_utf8_string(
    data: bytes,
    offset: int,
    *,
    max_length: int = 16_384,
) -> tuple[str | None, int, str | None]:
    if offset + 4 > len(data):
        return None, offset, "truncated-length"
    length = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    if length == MEMORYPACK_NULL_COUNT:
        return None, offset, None
    if length > max_length or offset + length > len(data):
        return None, offset, f"invalid-length={length}"
    raw = data[offset : offset + length]
    return raw.decode("utf-8", "replace"), offset + length, None


def read_memorypack_i32(data: bytes, offset: int) -> tuple[int, int]:
    if offset + 4 > len(data):
        raise ValueError("truncated-int32")
    return struct.unpack_from("<i", data, offset)[0], offset + 4


def read_memorypack_f32(data: bytes, offset: int) -> tuple[float, int]:
    if offset + 4 > len(data):
        raise ValueError("truncated-float32")
    return struct.unpack_from("<f", data, offset)[0], offset + 4


def read_memorypack_bool(data: bytes, offset: int) -> tuple[bool, int]:
    if offset >= len(data):
        raise ValueError("truncated-bool")
    return bool(data[offset]), offset + 1


def require_memorypack_string(
    data: bytes,
    offset: int,
    field_name: str,
) -> tuple[str | None, int]:
    value, offset, error = read_memorypack_utf8_string(data, offset)
    if error:
        raise ValueError(f"{field_name}:{error}")
    return value, offset


def read_memorypack_u32_count(
    data: bytes,
    offset: int,
    field_name: str,
    *,
    max_count: int = 50_000,
) -> tuple[int, int]:
    if offset + 4 > len(data):
        raise ValueError(f"{field_name}:truncated-count")
    count = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    if count == MEMORYPACK_NULL_COUNT:
        raise ValueError(f"{field_name}:null-count")
    if count > max_count:
        raise ValueError(f"{field_name}:invalid-count={count}")
    return count, offset


def require_memorypack_non_null_string(
    data: bytes,
    offset: int,
    field_name: str,
    *,
    max_length: int = 512,
) -> tuple[str, int]:
    value, offset, error = read_memorypack_utf8_string(data, offset, max_length=max_length)
    if error:
        raise ValueError(f"{field_name}:{error}")
    if value is None:
        raise ValueError(f"{field_name}:null-string")
    return value, offset


class LabelledReader:
    """Bounds-checked cursor over one MemoryPack payload window.

    Every read records its byte range and fails with the owning decoder's
    ``LABEL`` prefix, so a contract's diagnostics name the decoder that
    stopped.  Subclass with ``LABEL`` set; the shape is shared by the
    first-timeline SkillData decoders.
    """

    LABEL = "memorypack"

    def __init__(self, data: bytes, limit: int, start: int = 0):
        if type(limit) is not int or type(start) is not int or not 0 <= start <= limit <= len(data):
            raise ValueError(f"{self.LABEL}.reader:invalid-bounds start={start} limit={limit}")
        self.data = data
        self.limit = limit
        self.pos = start
        self.ranges: list[dict[str, Any]] = []

    def need(self, width: int, name: str) -> None:
        if width < 0 or self.pos + width > self.limit:
            raise ValueError(f"{self.LABEL}.{name}:truncated offset={self.pos} width={width}")

    def raw(self, width: int, name: str) -> bytes:
        self.need(width, name)
        start = self.pos
        self.pos += width
        if width:
            self.ranges.append({"name": name, "start": start, "end": self.pos})
        return self.data[start:self.pos]

    def header(self, expected: int, name: str) -> int:
        value = self.raw(1, name)[0]
        if value != expected:
            raise ValueError(f"{self.LABEL}.{name}:member-count={value} expected={expected}")
        return value

    def i32(self, name: str) -> int:
        return struct.unpack("<i", self.raw(4, name))[0]

    def f32(self, name: str) -> float:
        return struct.unpack("<f", self.raw(4, name))[0]

    def boolean(self, name: str) -> bool:
        value = self.raw(1, name)[0]
        if value not in (0, 1):
            raise ValueError(f"{self.LABEL}.{name}:bool={value}")
        return bool(value)

    def string(self, name: str) -> str | None:
        length = self.i32(f"{name}.length")
        if length == -1:
            return None
        if not 0 <= length <= 16_384:
            raise ValueError(f"{self.LABEL}.{name}:length={length}")
        try:
            return self.raw(length, f"{name}.bytes").decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"{self.LABEL}.{name}:utf8") from exc
