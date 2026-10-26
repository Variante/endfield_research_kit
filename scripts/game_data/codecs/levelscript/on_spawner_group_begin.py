"""Selected stored ActionHeader cursor for OnSpawnerGroupBegin."""

from __future__ import annotations

from typing import Any
from scripts.game_data.memorypack.core import memorypack_union_header

from .action_map import ActionMapCodecError, _Cursor


_TYPE = "Beyond.Gameplay.Actions.LevelEvent.OnSpawnerGroupBegin"
_FIELDS = [
    ["dontLogWarning", "bool"], ["ID", "int32"],
    ["releaseWhenExecutionFinished", "bool"], ["uid", "string"],
    ["scopeMask", "int32"], ["useCurrentScope", "bool"],
    ["useGraphScope", "bool"], ["filterLevel", "int32"],
    ["filterMask", "int32"], ["filterMode", "bool"],
    ["nextID", "int32"], ["priority", "int32"],
    ["triggerActiveDuring", "int32"], ["validate", "Param<bool>"],
    ["groupKeyFilter", "Param<string>"],
    ["groupKeyOutput", "ParamOutput<string>"],
    ["spawnerFilter", "Param<SpawnerPtr>"],
    ["spawnerOutput", "ParamOutput<SpawnerPtr>"],
]


def decode_on_spawner_group_begin_header(
    data: bytes, offset: int, route: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    """Read one selected event header from its authenticated member order."""
    if (
        route.get("family") != "ActionHeader"
        or route.get("typeName") != _TYPE
        or type(route.get("tag")) is not int or not 0 <= route["tag"] <= 0xFFFF
        or route.get("serializedMemberCount") != 18
        or route.get("fields") != _FIELDS
    ):
        raise ActionMapCodecError("onSpawnerGroupBegin:invalid-route")
    header = memorypack_union_header(route["tag"], route["serializedMemberCount"])
    if offset < 0 or data[offset:offset + len(header)] != header:
        raise ActionMapCodecError(f"onSpawnerGroupBegin:invalid-header,offset={offset}")
    cursor = _Cursor(data, offset + len(header))
    values: dict[str, Any] = {}
    spans: dict[str, list[int]] = {}
    for name, kind in _FIELDS:
        start = cursor.offset
        values[name] = cursor.value(kind, f"onSpawnerGroupBegin.{name}")
        spans[name] = [start, cursor.offset]
    return {
        "sourceOffset": offset, "endOffset": cursor.offset,
        "unionTag": route["tag"], "memberCount": 18,
        "wrapperName": route["wrapperName"],
        "fields": values, "fieldSpans": spans,
    }, cursor.offset
