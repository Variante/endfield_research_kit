"""Shared exact primitives for serialized LevelScript ``Param`` values."""

from __future__ import annotations

import re
import struct
from typing import Any


DEFAULT_PARAM_TAIL = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"
PROPERTY_OUTPUT_PATH_RE = re.compile(
    r"^\$(?P<local>\d+)@_(?P<name>"
    r"oldValue|value|result|floatValue|entityOutput|instKeyOutput|"
    r"eventArgsPtr|triggerSlotIdOutput|guideId|groupKeyOutput|"
    r"spawnerOutput|waveKeyOutput|dialogId|finishId|isSkipped|newStageOutput|"
    r"optionIndex|npcPosition|entity|entityTemplateId|firstTargetId|skillId|"
    r"lsvPtrOutput|keyOutput|patrolIdOutput|inFight"
    r")$"
)


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


def decode_param_output(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode a present ``ParamOutput``, retaining nullable paths."""
    if cursor + 9 > len(payload) or payload[cursor] != 0x02:
        return None
    source = struct.unpack_from("<i", payload, cursor + 1)[0]
    size = struct.unpack_from("<i", payload, cursor + 5)[0]
    cursor += 9
    if source < 0 or source > 0x10000:
        return None
    if size == -1:
        return {"paramSource": source, "path": None}, cursor
    if size <= 0 or size > 256 or cursor + size > len(payload):
        return None
    try:
        value = payload[cursor : cursor + size].decode("utf-8")
    except UnicodeDecodeError:
        return None
    return {"paramSource": source, "path": value}, cursor + size


def decode_param_output_ref(payload: bytes, cursor: int) -> tuple[str, int] | None:
    """Decode the exact local-property-reference ``ParamOutput`` form."""
    decoded = decode_param_output(payload, cursor)
    if decoded is None:
        return None
    detail, cursor = decoded
    value = detail.get("path")
    if (
        detail.get("paramSource") != 0
        or not isinstance(value, str)
        or not PROPERTY_OUTPUT_PATH_RE.match(value)
    ):
        return None
    return value, cursor


def decode_constant_i32_param(payload: bytes, cursor: int) -> tuple[int, int] | None:
    if (
        cursor + 17 > len(payload)
        or payload[cursor] != 0x04
        or payload[cursor + 5 : cursor + 17] != DEFAULT_PARAM_TAIL
    ):
        return None
    return struct.unpack_from("<i", payload, cursor + 1)[0], cursor + 17


def decode_constant_bool_param(payload: bytes, cursor: int) -> tuple[bool, int] | None:
    if (
        cursor + 14 > len(payload)
        or payload[cursor] != 0x04
        or payload[cursor + 1] not in (0, 1)
        or payload[cursor + 2 : cursor + 14] != DEFAULT_PARAM_TAIL
    ):
        return None
    return bool(payload[cursor + 1]), cursor + 14


def decode_constant_entity_ptr_param(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode the installed constant ``Param<ScriptEntityPtr>`` form."""
    if cursor + 27 > len(payload) or payload[cursor : cursor + 2] != b"\x04\x03":
        return None
    logic_id = struct.unpack_from("<Q", payload, cursor + 2)[0]
    slot_id = struct.unpack_from("<I", payload, cursor + 10)[0]
    use_slot_id = payload[cursor + 14]
    if use_slot_id not in (0, 1):
        return None
    id_ref = struct.unpack_from("<i", payload, cursor + 15)[0]
    param_source = struct.unpack_from("<i", payload, cursor + 19)[0]
    path_size = struct.unpack_from("<i", payload, cursor + 23)[0]
    cursor += 27
    if path_size == -1:
        path = None
    elif 0 <= path_size <= 256 and cursor + path_size <= len(payload):
        try:
            path = payload[cursor : cursor + path_size].decode("utf-8")
        except UnicodeDecodeError:
            return None
        cursor += path_size
    else:
        return None
    return {
        "logicId": logic_id,
        "slotId": slot_id,
        "useSlotId": bool(use_slot_id),
        "idRef": id_ref,
        "paramSource": param_source,
        "path": path,
    }, cursor
