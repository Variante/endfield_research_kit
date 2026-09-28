"""Read the selected stored CheckTyphoeaArcheryUnitsComplete condition."""

from __future__ import annotations

import struct
from typing import Any

from scripts.game_data.codecs.levelscript.condition_params import _decode_string_param
from scripts.game_data.codecs.levelscript.framing_common import _offset_hex
from scripts.game_data.codecs.levelscript.modules import LevelScriptModuleCodecError, _lsm_ptr
from scripts.game_data.codecs.levelscript.params import (
    decode_levelscript_ptr_param, decode_param_tail,
)
from scripts.game_data.codecs.levelscript.task_conditions import (
    _decode_task_condition_common, _decode_task_condition_union_header,
)
from scripts.game_data.levelscript_taskmap_archery_native import (
    SCHEMA, validated_taskmap_archery_route,
)


def _decode_lsm_list_param(
    data: bytes, cursor: int,
) -> tuple[dict[str, Any], int] | None:
    """Advance a constant Param<List<LsmPtr>> through its stored elements."""
    if cursor < 0 or cursor + 5 > len(data) or data[cursor] != 4:
        return None
    count = struct.unpack_from("<i", data, cursor + 1)[0]
    cursor += 5
    if count == -1:
        values = None
    elif 0 <= count <= 1024:
        values = []
        try:
            for index in range(count):
                value, cursor = _lsm_ptr(data, cursor, f"lsm[{index}]")
                values.append(value)
        except LevelScriptModuleCodecError:
            return None
    else:
        return None
    tail = decode_param_tail(data, cursor)
    if tail is None:
        return None
    detail, cursor = tail
    return {"values": values, **detail}, cursor


_PARAM_READERS = {
    "Param<string>": _decode_string_param,
    "Param<List<LsmPtr>>": _decode_lsm_list_param,
    "Param<LevelScriptPtr>": decode_levelscript_ptr_param,
}


def decode_taskmap_archery_condition(
    data: bytes, offset: int, limit: int,
) -> tuple[dict[str, Any], int] | None:
    """Consume the selected route; preserve a named partial on any drift."""
    if not 0 <= offset < limit <= len(data):
        return None
    header = _decode_task_condition_union_header(data, offset, limit)
    if header is None:
        return None
    tag, count, encoding, cursor = header
    route = validated_taskmap_archery_route()
    if route is None or (tag, count) != (route["tag"], route["serializedMemberCount"]):
        return None
    common = _decode_task_condition_common(data, cursor, limit)
    if common is None:
        return None
    base_fields, cursor = common
    values: dict[str, Any] = {}
    for name, kind in route["fields"][4:]:
        decoder = _PARAM_READERS.get(kind)
        if decoder is None:
            return None
        decoded = decoder(data, cursor)
        if decoded is None or decoded[1] > limit:
            return None
        values[name], cursor = decoded
    return {
        "type": route["typeName"].removeprefix("Beyond.Gameplay."),
        "conditionUnionTag": f"0x{tag:04x}",
        "conditionUnionTagEncoding": encoding,
        "serializedMemberCount": count,
        "conditionOffset": offset,
        "conditionOffsetHex": _offset_hex(offset),
        "conditionEndOffset": cursor,
        "conditionEndOffsetHex": _offset_hex(cursor),
        **base_fields, **values,
        "nativeMappingId": SCHEMA,
    }, cursor
