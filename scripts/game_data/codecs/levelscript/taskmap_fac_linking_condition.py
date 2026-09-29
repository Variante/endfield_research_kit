"""Selected stored facility-linking GameCondition in a LevelScript task map."""

from __future__ import annotations

from typing import Any

from .framing_common import _offset_hex
from .params import decode_bool_param, decode_i32_param
from .task_conditions import _decode_task_condition_common, _decode_task_condition_union_header
from scripts.game_data.levelscript_check_fac_linking_mode_native import (
    SCHEMA, validated_check_fac_linking_mode_route,
)


def decode_fac_linking_mode_condition(
    data: bytes, offset: int, limit: int, route: dict[str, Any], enum: dict[str, Any],
) -> tuple[dict[str, Any], int] | None:
    """Consume exactly six reviewed members with a bounded LinkType value."""
    fields = route.get("fields") or []
    if (
        not 0 <= offset < limit <= len(data)
        or route.get("family") != "GameCondition"
        or route.get("typeName") != "Beyond.Gameplay.Conditions.CheckIsInFacLinkingMode"
        or route.get("serializedMemberCount") != 6
        or fields != [
            ["scopeMask", "enum32"], ["uniqueId", "string"],
            ["useCurrentScope", "bool"], ["useGraphScope", "bool"],
            ["isInFacLinkingMode", "Param<bool>"],
            ["targetFacLinkingModeType", "Param<LinkType>"],
        ]
        or enum.get("typeName") != "Beyond.Gameplay.Core.GameMech.LinkWireBrain+LinkType"
        or enum.get("underlyingType") != "int"
    ):
        return None
    header = _decode_task_condition_union_header(data, offset, limit)
    if header is None:
        return None
    tag, count, encoding, cursor = header
    if (tag, count) != (route.get("tag"), 6):
        return None
    common = _decode_task_condition_common(data, cursor, limit)
    if common is None:
        return None
    values, cursor = common
    enabled = decode_bool_param(data, cursor)
    if enabled is None or enabled[1] > limit:
        return None
    link = decode_i32_param(data, enabled[1])
    if link is None or link[1] > limit:
        return None
    enum_names = {row["id"]: row["name"] for row in enum.get("members", [])}
    link_id = link[0]["value"]
    if link_id not in enum_names:
        return None
    cursor = link[1]
    return {
        "type": "Conditions.CheckIsInFacLinkingMode",
        "conditionUnionTag": f"0x{tag:04x}",
        "conditionUnionTagEncoding": encoding,
        "serializedMemberCount": count,
        "conditionOffset": offset,
        "conditionOffsetHex": _offset_hex(offset),
        "conditionEndOffset": cursor,
        "conditionEndOffsetHex": _offset_hex(cursor),
        **values,
        "isInFacLinkingMode": enabled[0],
        "targetFacLinkingModeType": {**link[0], "name": enum_names[link_id]},
    }, cursor


def decode_selected_fac_linking_mode_condition(
    data: bytes, offset: int, limit: int,
) -> tuple[dict[str, Any], int] | None:
    """Admit the condition only when its selected native build validates."""
    selected = validated_check_fac_linking_mode_route()
    if selected is None:
        return None
    route, enum = selected
    result = decode_fac_linking_mode_condition(data, offset, limit, route, enum)
    if result is None:
        return None
    detail, end = result
    return {**detail, "nativeMappingId": SCHEMA}, end
