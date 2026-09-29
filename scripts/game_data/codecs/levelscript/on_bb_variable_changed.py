"""Selected stored ActionHeader cursor for OnBBVariableChanged."""

from __future__ import annotations

from typing import Any

from .action_map import ActionMapCodecError, _Cursor


_TYPE = "Beyond.Gameplay.Actions.ScriptEvent.OnBBVariableChanged"
_FIELDS = [
    ["dontLogWarning", "bool"], ["ID", "int32"],
    ["releaseWhenExecutionFinished", "bool"], ["uid", "string"],
    ["scopeMask", "int32"], ["useCurrentScope", "bool"],
    ["useGraphScope", "bool"], ["filterLevel", "int32"],
    ["filterMask", "int32"], ["filterMode", "bool"],
    ["nextID", "int32"], ["priority", "int32"],
    ["triggerActiveDuring", "int32"], ["validate", "Param<bool>"],
    ["targetScript", "Param<LevelScriptPtr>"],
    ["triggerTarget", "int32"],
    ["key", "Param<string>"],
    ["oldValue", "ParamOutput<object>"],
    ["value", "ParamOutput<object>"],
]


def decode_on_bb_variable_changed_header(
    data: bytes, offset: int, route: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    """Read one header from the authenticated nineteen-member order."""
    if (
        route.get("family") != "ActionHeader"
        or route.get("typeName") != _TYPE
        or route.get("tag") != 0x00BA
        or route.get("serializedMemberCount") != 19
        or route.get("fields") != _FIELDS
    ):
        raise ActionMapCodecError("onBBVariableChanged:invalid-route")
    if offset < 0 or data[offset:offset + 2] != b"\xba\x13":
        raise ActionMapCodecError(f"onBBVariableChanged:invalid-header,offset={offset}")
    cursor = _Cursor(data, offset + 2)
    values: dict[str, Any] = {}
    spans: dict[str, list[int]] = {}
    for name, kind in _FIELDS:
        start = cursor.offset
        values[name] = cursor.value(kind, f"onBBVariableChanged.{name}")
        spans[name] = [start, cursor.offset]
    return {
        "sourceOffset": offset,
        "endOffset": cursor.offset,
        "unionTag": 0x00BA,
        "memberCount": 19,
        "wrapperName": route["wrapperName"],
        "fields": values,
        "fieldSpans": spans,
    }, cursor.offset
