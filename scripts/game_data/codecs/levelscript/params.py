"""Shared exact primitives for serialized LevelScript ``Param`` values."""

from __future__ import annotations

import re
import struct
from typing import Any
from scripts.game_data.string_pool import resolve_string_pool_index


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
    # This bounded codec currently admits only the proved getter-reference
    # marker among negative source selectors; other negative declarations
    # require independent route/child evidence. The admitted form carries no
    # path. Its id may be absent, spelled -1 exactly as the default
    # tail spells an absent id -- so the id is bounded above and left open
    # below, where ``id_ref < -1`` already refuses anything further out.
    getter_reference = param_source == -1 and id_ref <= 0x10000 and path_size == -1
    if id_ref < -1 or param_source > 0x10000 or (param_source < 0 and not getter_reference):
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


def decode_pooled_param_tail(payload: bytes, cursor: int, *, strings: Any = None) -> tuple[dict[str, Any], int] | None:
    """Read a separately native-proved pool-present Param tail, without inline fallback."""
    if type(cursor) is not int or cursor < 0 or cursor+12 > len(payload):return None
    id_ref,source,index=struct.unpack_from('<iii',payload,cursor)
    if id_ref < -1 or source > 0x10000 or source < -1 or index < -2 or (source==-1 and (id_ref>0x10000 or index not in (-2,-1))):return None
    path=resolve_string_pool_index(index,strings,'path')
    return {'idRef':id_ref,'paramSource':source,'path':path},cursor+12


def decode_string_param(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode a present ``Param<string>``, including null/empty values."""
    if cursor < 0 or cursor + 5 > len(payload) or payload[cursor] != 0x04:
        return None
    size = struct.unpack_from("<i", payload, cursor + 1)[0]
    cursor += 5
    if size == -1:
        value = None
    elif 0 <= size <= 1 << 20 and cursor + size <= len(payload):
        try:
            value = payload[cursor : cursor + size].decode("utf-8")
        except UnicodeDecodeError:
            return None
        cursor += size
    else:
        return None
    tail = decode_param_tail(payload, cursor)
    if tail is None:
        return None
    detail, end = tail
    return {"value": value, **detail}, end


def decode_levelscript_ptr_param(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    """Refuse until the current raw16 constant and pooled tail are authenticated."""
    return None


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


def decode_float_param(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    if cursor + 5 > len(payload) or payload[cursor] != 0x04:
        return None
    value = round(struct.unpack_from("<f", payload, cursor + 1)[0], 3)
    tail = decode_param_tail(payload, cursor + 5)
    if tail is None:
        return None
    detail, end = tail
    return {"value": value, **detail}, end


def decode_local_getter_ref(payload: bytes, cursor: int) -> tuple[int, int] | None:
    if (
        cursor + 17 > len(payload)
        or payload[cursor : cursor + 5] != b"\x04\x00\x00\x00\x00"
        or payload[cursor + 9 : cursor + 17] != b"\xff" * 8
    ):
        return None
    local_id = struct.unpack_from("<i", payload, cursor + 5)[0]
    if local_id < 0 or local_id > 0x10000:
        return None
    return local_id, cursor + 17


def finish_getter_fields(
    payload: bytes,
    end: int,
    detail: dict[str, Any],
) -> dict[str, Any]:
    """Accept exact subtype EOF or one proven outer-list u32 trailer."""
    if end == len(payload):
        return detail
    if end + 4 != len(payload):
        return {}
    return {
        **detail,
        "trailingActionMapFramingU32": struct.unpack_from("<I", payload, end)[0],
    }


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
    """Refuse until the current positive/array composition is authenticated."""
    return None


def decode_entity_ptr_getter_ref_array(
    payload: bytes,
    cursor: int,
) -> tuple[list[dict[str, Any]] | None, int] | None:
    """Refuse until the current positive/array composition is authenticated."""
    return None
