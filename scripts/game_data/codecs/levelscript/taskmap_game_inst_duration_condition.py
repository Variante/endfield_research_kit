"""Selected stored CheckGameInstStartDuration task condition cursor."""

from __future__ import annotations

from typing import Any

from .condition_params import _decode_string_param
from .framing_common import _offset_hex
from .params import decode_i32_param, decode_levelscript_ptr_param
from .task_conditions import _decode_task_condition_common, _decode_task_condition_union_header
from scripts.game_data.levelscript_check_game_inst_start_duration_native import (
    SCHEMA, validated_check_game_inst_start_duration_route,
)


_PARAM_READERS = {
    "Param<CompareOperator>": decode_i32_param,
    "Param<int>": decode_i32_param,
    "Param<string>": _decode_string_param,
    "Param<LevelScriptPtr>": decode_levelscript_ptr_param,
}


def decode_game_inst_duration_condition(
    data: bytes, offset: int, limit: int, route: dict[str, Any],
) -> tuple[dict[str, Any], int] | None:
    """Advance the native route's five parameters from an exact condition tag."""
    fields = route.get("fields") or []
    if (
        not 0 <= offset < limit <= len(data)
        or route.get("family") != "GameCondition"
        or route.get("typeName") != "Beyond.Gameplay.CheckGameInstStartDuration"
        or route.get("serializedMemberCount") != 9
        or fields[:4] != [
            ["scopeMask", "enum32"], ["uniqueId", "string"],
            ["useCurrentScope", "bool"], ["useGraphScope", "bool"],
        ]
        or fields[4:] != [
            ["compareOperator", "Param<CompareOperator>"],
            ["progressToCompare", "Param<int>"],
            ["levelId", "Param<string>"],
            ["scriptId", "Param<LevelScriptPtr>"],
            ["subGameId", "Param<string>"],
        ]
    ):
        return None
    header = _decode_task_condition_union_header(data, offset, limit)
    if header is None:
        return None
    tag, count, encoding, cursor = header
    if (tag, count) != (route.get("tag"), route["serializedMemberCount"]):
        return None
    common = _decode_task_condition_common(data, cursor, limit)
    if common is None:
        return None
    values, cursor = common
    for name, kind in fields[4:]:
        decoded = _PARAM_READERS[kind](data, cursor)
        if decoded is None or decoded[1] > limit:
            return None
        values[name], cursor = decoded
    return {
        "type": "CheckGameInstStartDuration",
        "conditionUnionTag": f"0x{tag:04x}",
        "conditionUnionTagEncoding": encoding,
        "serializedMemberCount": count,
        "conditionOffset": offset,
        "conditionOffsetHex": _offset_hex(offset),
        "conditionEndOffset": cursor,
        "conditionEndOffsetHex": _offset_hex(cursor),
        **values,
    }, cursor


def decode_selected_game_inst_duration_condition(
    data: bytes, offset: int, limit: int,
) -> tuple[dict[str, Any], int] | None:
    """Admit the condition only while its selected native route validates."""
    route = validated_check_game_inst_start_duration_route()
    if route is None:
        return None
    decoded = decode_game_inst_duration_condition(data, offset, limit, route)
    if decoded is None:
        return None
    detail, end = decoded
    return {**detail, "nativeMappingId": SCHEMA}, end
