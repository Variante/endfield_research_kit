"""Exact stored GameCondition payloads from the followon taskMap native set.

This reader is independent of the production task dispatcher until its source
replays demonstrate a complete sequential owner boundary.
"""

from __future__ import annotations

import struct
from typing import Any

from scripts.game_data.codecs.levelscript import params as levelscript_params
from scripts.game_data.codecs.levelscript.condition_params import (
    _decode_levelscript_ptr_param, _decode_string_param, _decode_u64_param,
)
from scripts.game_data.codecs.levelscript.framing_common import _offset_hex
from scripts.game_data.codecs.levelscript.params import (
    decode_bool_param as _decode_bool_param,
    decode_i32_param as _decode_i32_param,
    decode_param_tail as _decode_param_tail,
)
from scripts.game_data.codecs.levelscript.task_conditions import (
    _decode_task_condition_common, _decode_task_condition_union_header,
)
from scripts.game_data.levelscript_taskmap_followon_native import (
    SCHEMA, validated_taskmap_followon_routes,
)


def _decode_i64_param(data: bytes, offset: int) -> tuple[dict[str, Any], int] | None:
    if offset + 9 > len(data) or data[offset] != 0x04:
        return None
    value = struct.unpack_from("<q", data, offset + 1)[0]
    tail = _decode_param_tail(data, offset + 9)
    if tail is None:
        return None
    detail, end = tail
    return {"value": value, **detail}, end


_PARAM_READERS = {
    "Param<string>": _decode_string_param,
    "Param<bool>": _decode_bool_param,
    "Param<int32>": _decode_i32_param,
    "Param<int64>": _decode_i64_param,
    "Param<CompareOperator>": _decode_i32_param,
    "Param<EntityPtr>": levelscript_params.decode_constant_entity_ptr_param,
    "Param<LsmPtr>": _decode_u64_param,
    "Param<LevelScriptPtr>": _decode_levelscript_ptr_param,
}


def decode_followon_taskmap_condition(
    data: bytes, offset: int, limit: int,
) -> tuple[dict[str, Any], int] | None:
    """Read a reviewed followon route at one exact source cursor."""
    if not 0 <= offset < limit <= len(data):
        return None
    header = _decode_task_condition_union_header(data, offset, limit)
    if header is None:
        return None
    tag, count, encoding, cursor = header
    route = validated_taskmap_followon_routes().get((tag, count))
    if route is None:
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
        value, cursor = decoded
        if kind == "Param<LsmPtr>":
            value = {**value, "value": {"id": value["value"]}}
        values[name] = value
    return {
        "type": route["typeName"].removeprefix("Beyond.Gameplay."),
        "conditionUnionTag": f"0x{tag:04x}",
        "conditionUnionTagEncoding": encoding,
        "serializedMemberCount": count,
        "conditionOffset": offset,
        "conditionOffsetHex": _offset_hex(offset),
        "conditionEndOffset": cursor,
        "conditionEndOffsetHex": _offset_hex(cursor),
        **base_fields,
        **values,
        "nativeMappingId": SCHEMA,
    }, cursor
