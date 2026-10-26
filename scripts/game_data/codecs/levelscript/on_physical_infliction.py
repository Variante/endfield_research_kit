"""Selected stored ActionHeader cursor for OnPhysicalInfliction.

The signed PhysicalInflictionType values come from a validated native contract.
"""

from __future__ import annotations

from collections.abc import Collection
from typing import Any

from scripts.game_data.memorypack.core import memorypack_union_header

from .action_map import ActionMapCodecError, _Cursor


_TYPE = "Beyond.Gameplay.Actions.EntityEvent.OnPhysicalInfliction"
_INHERITED = [
    ["dontLogWarning", "bool"], ["ID", "int32"],
    ["releaseWhenExecutionFinished", "bool"], ["uid", "string"],
    ["scopeMask", "int32"], ["useCurrentScope", "bool"],
    ["useGraphScope", "bool"], ["filterLevel", "int32"],
    ["filterMask", "int32"], ["filterMode", "bool"],
    ["nextID", "int32"], ["priority", "int32"],
    ["triggerActiveDuring", "int32"], ["validate", "Param<bool>"],
]
_OWN = [
    ["entityFilter", "Param<EntityPtr>"],
    ["entityOutput", "ParamOutput<EntityPtr>"],
    ["inflictionTypeFilter", "Param<PhysicalInflictionType>"],
    ["inflictionTypeOutput", "ParamOutput<int>"],
    ["sourceOutput", "ParamOutput<EntityPtr>"],
    ["useEntityFilter", "Param<bool>"],
    ["useInflictionTypeFilter", "Param<bool>"],
]


def decode_on_physical_infliction_header(
    data: bytes, offset: int, route: dict[str, Any], *,
    enum_values: Collection[int] | None, game_root=None, strings: Any=None,
) -> tuple[dict[str, Any], int]:
    """Read one native-gated header without accepting unreviewed enum values."""
    fields = route.get("fields") or []
    tag = route.get("tag")
    members = route.get("serializedMemberCount")
    if (
        route.get("family") != "ActionHeader"
        or route.get("typeName") != _TYPE
        or type(tag) is not int or not 0 <= tag <= 0xFFFF or members != 21
        or fields[:14] != _INHERITED or fields[14:] != _OWN
    ):
        raise ActionMapCodecError("onPhysicalInflictionHeader:invalid-route")
    if (
        not enum_values
        or any(type(value) is not int for value in enum_values)
        or len(set(enum_values)) != len(enum_values)
    ):
        raise ActionMapCodecError("onPhysicalInflictionHeader:enum-native-gate")
    header = memorypack_union_header(route["tag"], route["serializedMemberCount"])
    if offset < 0 or data[offset:offset + len(header)] != header:
        raise ActionMapCodecError(f"onPhysicalInflictionHeader:invalid-header,offset={offset}")
    cursor = _Cursor(data, offset + len(header), game_root=game_root, strings=strings)
    values: dict[str, Any] = {}
    spans: dict[str, list[int]] = {}
    for name, kind in fields:
        start = cursor.offset
        value = cursor.node_string("onPhysicalInflictionHeader."+name,{**route,"nativeGate":"levelscript_on_physical_infliction_native"},name) if kind=="string" else cursor.value(kind,"onPhysicalInflictionHeader."+name)
        if (
            kind == "Param<PhysicalInflictionType>"
            and value is not None
            and value["value"] not in enum_values
        ):
            raise ActionMapCodecError(
                f"onPhysicalInflictionHeader:unsupported-enum={value['value']},offset={start}"
            )
        values[name] = value
        spans[name] = [start, cursor.offset]
    return {
        "sourceOffset": offset,
        "endOffset": cursor.offset,
        "unionTag": tag,
        "memberCount": members,
        "wrapperName": route["wrapperName"],
        "fields": values,
        "fieldSpans": spans,
    }, cursor.offset
