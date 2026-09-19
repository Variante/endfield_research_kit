"""Little-endian field readers and list-status labels shared by the LevelScript codecs."""
from __future__ import annotations

import struct


def u32(data: bytes, offset: int) -> int | None:
    if offset < 0 or offset + 4 > len(data):
        return None
    return struct.unpack_from("<I", data, offset)[0]


def i32(data: bytes, offset: int) -> int | None:
    if offset < 0 or offset + 4 > len(data):
        return None
    return struct.unpack_from("<i", data, offset)[0]


def f32(data: bytes, offset: int) -> float | None:
    if offset < 0 or offset + 4 > len(data):
        return None
    return struct.unpack_from("<f", data, offset)[0]


def list_status(raw_count: int | None) -> tuple[str, int | None]:
    if raw_count is None:
        return "missing", None
    if raw_count == 0xFFFFFFFF:
        return "null", None
    if raw_count <= 64:
        return "present", raw_count
    return "unknown", raw_count
