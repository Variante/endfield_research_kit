"""Bounds-checked primitives shared by the focused MemoryPack decoders."""

from __future__ import annotations

import struct
from typing import Any

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
