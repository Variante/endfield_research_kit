"""Selected stored ActionBase cursor for ListAddValueEntityPtr."""

from __future__ import annotations

from typing import Any

from .action_map import ActionMapCodecError, _Cursor


_TYPE = "Beyond.Gameplay.Actions.ListAddValueEntityPtr"
_FIELDS = [
    ["dontLogWarning", "bool"], ["ID", "int32"],
    ["releaseWhenExecutionFinished", "bool"], ["uid", "string"],
    ["scopeMask", "int32"], ["useCurrentScope", "bool"],
    ["useGraphScope", "bool"], ["nextID", "int32"],
    ["list", "Param<List<EntityPtr>>"],
    ["value", "Param<EntityPtr>"],
]
_HEADER = b"\xfa\x70\x01\x0a"


def decode_list_add_value_entity_ptr_action(
    data: bytes, offset: int, route: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    """Read one selected action using the authenticated member order."""
    if (
        route.get("family") != "ActionBase"
        or route.get("typeName") != _TYPE
        or route.get("tag") != 0x0170
        or route.get("serializedMemberCount") != 10
        or route.get("fields") != _FIELDS
    ):
        raise ActionMapCodecError("listAddValueEntityPtr:invalid-route")
    if offset < 0 or data[offset:offset + 4] != _HEADER:
        raise ActionMapCodecError(f"listAddValueEntityPtr:invalid-header,offset={offset}")
    cursor = _Cursor(data, offset + 4)
    values: dict[str, Any] = {}
    spans: dict[str, list[int]] = {}
    for name, kind in _FIELDS:
        start = cursor.offset
        values[name] = cursor.value(kind, f"listAddValueEntityPtr.{name}")
        spans[name] = [start, cursor.offset]
    return {
        "sourceOffset": offset,
        "endOffset": cursor.offset,
        "unionTag": 0x0170,
        "memberCount": 10,
        "wrapperName": route["wrapperName"],
        "fields": values,
        "fieldSpans": spans,
    }, cursor.offset
