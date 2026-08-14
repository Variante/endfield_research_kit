"""Decoder for the compact ``0x0a03`` property-condition gate schema."""

from __future__ import annotations

import struct
from typing import Any


_NULL_SENTINEL = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"


def _offset_hex(offset: int | None) -> str:
    return f"0x{offset:x}" if isinstance(offset, int) and offset >= 0 else ""


def _drop_empty(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if value not in (None, "", [], {})}


def _read_compact_string(
    payload: bytes,
    offset: int,
) -> tuple[str | None, int | None]:
    if offset < 0 or offset + 4 > len(payload):
        return None, None
    size = struct.unpack_from("<I", payload, offset)[0]
    if size > 120 or offset + 4 + size > len(payload):
        return None, None
    raw = payload[offset + 4 : offset + 4 + size]
    if any(value < 0x20 or value > 0x7E for value in raw):
        return None, None
    return raw.decode("ascii"), offset + 4 + size


def _append_small_i32_tail(
    payload: bytes,
    cursor: int,
    out: dict[str, Any],
) -> None:
    if cursor < 0 or cursor >= len(payload):
        return
    remaining = len(payload) - cursor
    if remaining != 4:
        if 0 < remaining <= 16:
            out["tailBytes"] = payload[cursor:].hex(" ")
        return
    value = struct.unpack_from("<i", payload, cursor)[0]
    out["tailLocalRef"] = value
    if 0 <= value <= 0x1000:
        out["gateLocalRefs"] = [value]


def _decode_post_flag_and_tail(
    payload: bytes,
    cursor: int,
    out: dict[str, Any],
) -> None:
    if cursor + 14 > len(payload) or payload[cursor] != 0x04:
        _append_small_i32_tail(payload, cursor, out)
        return
    out["postFlag"] = payload[cursor + 1]
    out["postFlagOffset"] = _offset_hex(cursor + 1)
    out["postSentinel"] = payload[cursor + 2 : cursor + 14] == _NULL_SENTINEL
    _append_small_i32_tail(payload, cursor + 14, out)


def decode_compact_property_gate(payload: bytes) -> dict[str, Any]:
    """Decode one fail-closed compact property gate payload.

    The current unnamed runtime class has a sentinel-headed condition with
    either one keyed operand, two keyed operand slots, or two local/scalar
    slots. A trailing small integer is retained only as a local gate reference.
    """
    if len(payload) < 15:
        return {}
    out: dict[str, Any] = {
        "payloadShape": "compact-condition-gate",
        "headByte": payload[0],
        "headSentinel": payload[1:13] == _NULL_SENTINEL,
        "firstTag": payload[13],
        "firstFlag": payload[14],
    }
    if not out["headSentinel"] or payload[13] != 0x04:
        return _drop_empty(out)

    # 00 <sentinel> 04 00 ff ff ff ff <typeCode> <len> <key>
    if len(payload) >= 27 and payload[15:19] == b"\xff\xff\xff\xff":
        type_code = struct.unpack_from("<I", payload, 19)[0]
        key_text, cursor = _read_compact_string(payload, 23)
        if key_text is not None and cursor is not None:
            out.update({
                "schema": "single-key",
                "typeCode": type_code,
                "propertyKey": key_text,
                "propertyKeyOffset": _offset_hex(27),
            })
            _decode_post_flag_and_tail(payload, cursor, out)
            return _drop_empty(out)

    # 00 <sentinel> 04 01 <sentinel> 04 00 ff ff ff ff <typeCode> <len> <key>
    if (
        len(payload) >= 41
        and payload[15:27] == _NULL_SENTINEL
        and payload[27] == 0x04
    ):
        type_code = struct.unpack_from("<I", payload, 33)[0]
        key_text, cursor = _read_compact_string(payload, 37)
        if key_text is not None and cursor is not None:
            out.update({
                "schema": "two-slot-key",
                "secondTag": payload[27],
                "secondFlag": payload[28],
                "typeCode": type_code,
                "propertyKey": key_text,
                "propertyKeyOffset": _offset_hex(41),
            })
            _decode_post_flag_and_tail(payload, cursor, out)
            return _drop_empty(out)

    # No-key form compares a local/scalar slot and carries no property name.
    if (
        len(payload) >= 41
        and payload[19:27] == b"\xff\xff\xff\xff\xff\xff\xff\xff"
        and payload[27] == 0x04
    ):
        out.update({
            "schema": "local-ref",
            "firstLocalRef": struct.unpack_from("<i", payload, 15)[0],
            "secondTag": payload[27],
            "secondFlag": payload[28],
            "secondSentinel": payload[29:41] == _NULL_SENTINEL,
        })
        _append_small_i32_tail(payload, 41, out)
        return _drop_empty(out)

    return _drop_empty(out)
