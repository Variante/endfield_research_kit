from __future__ import annotations

import math
import struct

from scripts.game_data.string_pool import StringPool, resolve_string_pool_index


def read_i32(data: bytes, offset: int) -> tuple[int, int] | None:
    if offset < 0 or offset + 4 > len(data):
        return None
    return int.from_bytes(data[offset : offset + 4], "little", signed=True), offset + 4


def read_u32(data: bytes, offset: int) -> tuple[int, int] | None:
    if offset < 0 or offset + 4 > len(data):
        return None
    return int.from_bytes(data[offset : offset + 4], "little", signed=False), offset + 4


def read_u64(data: bytes, offset: int) -> tuple[int, int] | None:
    if offset < 0 or offset + 8 > len(data):
        return None
    return int.from_bytes(data[offset : offset + 8], "little", signed=False), offset + 8


def read_i64(data: bytes, offset: int) -> tuple[int, int] | None:
    if offset < 0 or offset + 8 > len(data):
        return None
    return int.from_bytes(data[offset : offset + 8], "little", signed=True), offset + 8


def read_count(
    data: bytes,
    offset: int,
    *,
    max_count: int = 100_000,
) -> tuple[int, int] | None:
    decoded = read_i32(data, offset)
    if decoded is None:
        return None
    count, offset = decoded
    if count < -1 or count > max_count:
        return None
    return count, offset


def read_string(data: bytes, offset: int, *, strings: StringPool | None = None,
                max_length: int = 512) -> tuple[str | None, int] | None:
    """Bounded current pooled read; unavailable/invalid entries refuse the codec."""
    try:
        return read_pooled_string(data, offset, strings=strings, max_length=max_length)
    except ValueError:
        return None


def read_pooled_string(data: bytes, offset: int, *, strings: StringPool | None = None,
                       max_length: int = 512) -> tuple[str | None, int] | None:
    """Consume a proved signed pool index; absent pages never select inline text."""
    decoded = read_i32(data, offset)
    if decoded is None:
        return None
    index, end = decoded
    value = resolve_string_pool_index(index, strings)
    if value is not None and len(value.encode("utf-8")) > max_length:
        return None
    return value, end


def read_bool(data: bytes, offset: int) -> tuple[bool, int] | None:
    if offset < 0 or offset >= len(data) or data[offset] not in (0, 1):
        return None
    return bool(data[offset]), offset + 1


def read_f32(data: bytes, offset: int) -> tuple[float, int] | None:
    if offset < 0 or offset + 4 > len(data):
        return None
    value = struct.unpack_from("<f", data, offset)[0]
    if not math.isfinite(value):
        return None
    return value, offset + 4


def read_f64(data: bytes, offset: int) -> tuple[float, int] | None:
    if offset < 0 or offset + 8 > len(data):
        return None
    value = struct.unpack_from("<d", data, offset)[0]
    if not math.isfinite(value):
        return None
    return value, offset + 8


def skip_bytes(data: bytes, offset: int, size: int) -> int | None:
    if offset < 0 or size < 0 or offset + size > len(data):
        return None
    return offset + size
