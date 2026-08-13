"""Exact current-build ``Play3DRadio`` action payload decoder."""

from __future__ import annotations

import struct
from typing import Any


ACTION_SEMANTIC_KEY = (0x034A, 0x14)
PARAM_SENTINEL = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"


def decode_play3d_radio_action(
    payload: bytes,
    semantic_key: tuple[int, int],
) -> dict[str, Any]:
    """Decode the action's exact 12-field native formatter sequence.

    A minority of records have serialized list framing after the action. They
    remain unsupported until that outer framing is independently decoded.
    """
    if semantic_key != ACTION_SEMANTIC_KEY:
        return {}

    cursor = 0
    values: dict[str, Any] = {}
    offsets: dict[str, str] = {}
    encodings: dict[str, str] = {}

    class DecodeError(ValueError):
        pass

    def expect_tag(name: str) -> None:
        nonlocal cursor
        if cursor >= len(payload) or payload[cursor] != 0x04:
            raise DecodeError(f"{name}: missing object-present tag")
        offsets[name] = f"0x{cursor:x}"
        cursor += 1

    def expect_sentinel(name: str) -> None:
        nonlocal cursor
        if payload[cursor : cursor + 12] != PARAM_SENTINEL:
            raise DecodeError(f"{name}: invalid Param tail")
        cursor += 12

    def scalar(name: str, fmt: str, size: int) -> None:
        nonlocal cursor
        expect_tag(name)
        if cursor + size > len(payload):
            raise DecodeError(f"{name}: truncated scalar")
        values[name] = struct.unpack_from(fmt, payload, cursor)[0]
        cursor += size
        expect_sentinel(name)

    def boolean(name: str) -> None:
        nonlocal cursor
        expect_tag(name)
        if cursor >= len(payload) or payload[cursor] not in (0, 1):
            raise DecodeError(f"{name}: invalid bool")
        values[name] = bool(payload[cursor])
        cursor += 1
        expect_sentinel(name)

    def string(name: str, *, nullable: bool = False) -> None:
        nonlocal cursor
        offsets[name] = f"0x{cursor:x}"
        if nullable and payload[cursor : cursor + 1] == b"\xff":
            values[name] = ""
            encodings[name] = "bare-null"
            cursor += 1
            return
        expect_tag(name)
        if cursor + 4 > len(payload):
            raise DecodeError(f"{name}: truncated length")
        size = struct.unpack_from("<I", payload, cursor)[0]
        cursor += 4
        if nullable and size == 0xFFFFFFFF:
            values[name] = ""
            encodings[name] = "tagged-null"
            expect_sentinel(name)
            return
        if size > 512 or cursor + size > len(payload):
            raise DecodeError(f"{name}: invalid length")
        try:
            values[name] = payload[cursor : cursor + size].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise DecodeError(f"{name}: invalid UTF-8") from exc
        cursor += size
        encodings[name] = "tagged-string"
        expect_sentinel(name)

    try:
        scalar("attenuationType", "<I", 4)
        boolean("enableAdvancedOptions")
        expect_tag("entityPtr")
        entity_raw = payload[cursor : cursor + 26]
        if len(entity_raw) != 26:
            raise DecodeError("entityPtr: truncated")
        if entity_raw[14:26] == PARAM_SENTINEL:
            encodings["entityPtr"] = "default14+sentinel12"
        elif entity_raw[18:26] == b"\xff" * 8:
            encodings["entityPtr"] = "bound18+null8"
        else:
            raise DecodeError("entityPtr: unsupported shape")
        cursor += 26
        boolean("fromBegin")
        scalar("index", "<i", 4)
        boolean("noFlushAfterLoading")
        string("npcProxyId", nullable=True)
        boolean("onlyOnce")
        string("radioId")
        scalar("reverbOffset", "<f", 4)
        boolean("useNpcProxy")
        scalar("voOffset", "<f", 4)
    except (DecodeError, struct.error):
        return {}
    if cursor != len(payload):
        return {}
    return {
        "payloadShape": "play3d-radio-native-12-field-exact-eof",
        "radioId": str(values.get("radioId") or ""),
        "npcProxyId": str(values.get("npcProxyId") or ""),
        "useNpcProxy": bool(values.get("useNpcProxy")),
        "fields": values,
        "fieldOffsets": offsets,
        "fieldEncodings": encodings,
        "consumedBytes": cursor,
    }
