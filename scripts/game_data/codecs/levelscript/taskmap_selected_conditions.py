"""Exact current-build GameCondition payloads at positive LevelScript taskMap stops.

The selected native contract supplies the union tag and ordered field list.
This codec consumes only those typed fields; the enclosing task parser must
still prove its own condition key, remaining tasks, and final owner boundary.
"""

from __future__ import annotations

from typing import Any

from scripts.game_data.codecs.levelscript.condition_params import (
    _decode_string_param, _decode_u64_param,
)
from scripts.game_data.codecs.levelscript.framing_common import _offset_hex
from scripts.game_data.codecs.levelscript.task_conditions import (
    _decode_task_condition_common, _decode_task_condition_union_header,
)
from scripts.game_data.levelscript_taskmap_condition_native import (
    SCHEMA, validated_taskmap_condition_routes,
)


def decode_selected_taskmap_condition(
    data: bytes, offset: int, limit: int,
) -> tuple[dict[str, Any], int] | None:
    """Consume one selected GameCondition or return no route on any drift."""
    if not 0 <= offset < limit <= len(data):
        return None
    header = _decode_task_condition_union_header(data, offset, limit)
    if header is None:
        return None
    tag, count, encoding, cursor = header
    route = validated_taskmap_condition_routes().get((tag, count))
    if route is None:
        return None
    common = _decode_task_condition_common(data, cursor, limit)
    if common is None:
        return None
    base_fields, cursor = common
    values: dict[str, Any] = {}
    for name, kind in route["fields"][4:]:
        if kind == "Param<string>":
            decoded = _decode_string_param(data, cursor)
        elif kind == "Param<SpawnerPtr>":
            decoded = _decode_u64_param(data, cursor)
        else:
            return None
        if decoded is None or decoded[1] > limit:
            return None
        value, cursor = decoded
        if kind == "Param<SpawnerPtr>":
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
