"""Selected stored ActionBase cursor for SetForbidMapTeleport."""

from __future__ import annotations

from typing import Any

from .action_map import ActionMapCodecError, _Cursor


_TYPE = "Beyond.Gameplay.Actions.SetForbidMapTeleport"
_FIELDS = [
    ["dontLogWarning", "bool"], ["ID", "int32"],
    ["releaseWhenExecutionFinished", "bool"], ["uid", "string"],
    ["scopeMask", "int32"], ["useCurrentScope", "bool"],
    ["useGraphScope", "bool"], ["nextID", "int32"],
    ["allowGetUnstuckPoint", "Param<bool>"], ["forbid", "Param<bool>"],
]


def decode_set_forbid_map_teleport_action(
    data: bytes, offset: int, route: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    """Read one selected action from its authenticated member order."""
    if (
        route.get("family") != "ActionBase"
        or route.get("typeName") != _TYPE
        or route.get("tag") != 0x041A
        or route.get("serializedMemberCount") != 10
        or route.get("fields") != _FIELDS
    ):
        raise ActionMapCodecError("setForbidMapTeleport:invalid-route")
    if offset < 0 or data[offset:offset + 4] != b"\xfa\x1a\x04\x0a":
        raise ActionMapCodecError(f"setForbidMapTeleport:invalid-header,offset={offset}")
    cursor = _Cursor(data, offset + 4)
    values: dict[str, Any] = {}
    spans: dict[str, list[int]] = {}
    for name, kind in _FIELDS:
        start = cursor.offset
        values[name] = cursor.value(kind, f"setForbidMapTeleport.{name}")
        spans[name] = [start, cursor.offset]
    return {
        "sourceOffset": offset, "endOffset": cursor.offset,
        "unionTag": 0x041A, "memberCount": 10,
        "wrapperName": route["wrapperName"],
        "fields": values, "fieldSpans": spans,
    }, cursor.offset
