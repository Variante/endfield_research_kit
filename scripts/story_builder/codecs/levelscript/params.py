"""Shared exact primitives for serialized LevelScript ``Param`` values."""

from __future__ import annotations

import struct
from typing import Any


DEFAULT_PARAM_TAIL = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"


def decode_param_tail(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode the shared idRef/source/path tail of an authored Param value."""
    if cursor + 12 > len(payload):
        return None
    id_ref, param_source, path_size = struct.unpack_from("<iii", payload, cursor)
    cursor += 12
    if id_ref < -1 or param_source < 0 or param_source > 0x10000:
        return None
    if path_size == -1:
        path = None
    elif 0 <= path_size <= 1024 and cursor + path_size <= len(payload):
        try:
            path = payload[cursor : cursor + path_size].decode("utf-8")
        except UnicodeDecodeError:
            return None
        cursor += path_size
    else:
        return None
    return {"idRef": id_ref, "paramSource": param_source, "path": path}, cursor


def decode_constant_string_param(
    payload: bytes,
    cursor: int,
) -> tuple[str, int] | None:
    """Decode one constant ``Param<string>`` with the installed default tail."""
    if cursor + 5 > len(payload) or payload[cursor] != 0x04:
        return None
    size = struct.unpack_from("<i", payload, cursor + 1)[0]
    cursor += 5
    if size <= 0 or size > 256 or cursor + size + 12 > len(payload):
        return None
    try:
        value = payload[cursor : cursor + size].decode("utf-8")
    except UnicodeDecodeError:
        return None
    cursor += size
    if payload[cursor : cursor + 12] != DEFAULT_PARAM_TAIL:
        return None
    return value, cursor + 12


def decode_i32_param(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    if cursor + 5 > len(payload) or payload[cursor] != 0x04:
        return None
    value = struct.unpack_from("<i", payload, cursor + 1)[0]
    tail = decode_param_tail(payload, cursor + 5)
    if tail is None:
        return None
    detail, end = tail
    return {"value": value, **detail}, end


def decode_bool_param(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    if (
        cursor + 2 > len(payload)
        or payload[cursor] != 0x04
        or payload[cursor + 1] not in (0, 1)
    ):
        return None
    tail = decode_param_tail(payload, cursor + 2)
    if tail is None:
        return None
    detail, end = tail
    return {"value": bool(payload[cursor + 1]), **detail}, end
