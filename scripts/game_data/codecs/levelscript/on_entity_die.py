"""Selected stored ActionHeader cursor for OnEntityDie."""

from __future__ import annotations

from typing import Any

from .action_map import ActionMapCodecError, _Cursor


_TYPE = "Beyond.Gameplay.Actions.EntityEvent.OnEntityDie"
_FIELDS = [
    ["dontLogWarning", "bool"], ["ID", "int32"],
    ["releaseWhenExecutionFinished", "bool"], ["uid", "string"],
    ["scopeMask", "int32"], ["useCurrentScope", "bool"],
    ["useGraphScope", "bool"], ["filterLevel", "int32"],
    ["filterMask", "int32"], ["filterMode", "bool"],
    ["nextID", "int32"], ["priority", "int32"],
    ["triggerActiveDuring", "int32"], ["validate", "Param<bool>"],
    ["targetEntity", "Param<EntityPtr>"],
    ["targetEntityList", "Param<List<EntityPtr>>"],
    ["targetEntityListOutput", "ParamOutput<EntityPtr>"],
    ["triggerTarget", "int32"],
]


def decode_on_entity_die_header(
    data: bytes, offset: int, route: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    """Read one authenticated event header and its exact member order."""
    if (
        route.get("family") != "ActionHeader"
        or route.get("typeName") != _TYPE
        or route.get("tag") != 0x000F
        or route.get("serializedMemberCount") != 18
        or route.get("fields") != _FIELDS
    ):
        raise ActionMapCodecError("onEntityDie:invalid-route")
    if offset < 0 or data[offset:offset + 2] != b"\x0f\x12":
        raise ActionMapCodecError(f"onEntityDie:invalid-header,offset={offset}")
    cursor = _Cursor(data, offset + 2)
    values: dict[str, Any] = {}
    spans: dict[str, list[int]] = {}
    for name, kind in _FIELDS:
        start = cursor.offset
        values[name] = cursor.value(kind, f"onEntityDie.{name}")
        spans[name] = [start, cursor.offset]
    return {
        "sourceOffset": offset,
        "endOffset": cursor.offset,
        "unionTag": 0x000F,
        "memberCount": 18,
        "wrapperName": route["wrapperName"],
        "fields": values,
        "fieldSpans": spans,
    }, cursor.offset
