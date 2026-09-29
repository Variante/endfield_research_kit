"""Selected stored ActionHeader cursor for OnPhysicalInfliction.

The signed PhysicalInflictionType values come from a validated native contract.
"""

from __future__ import annotations

from collections.abc import Collection
from typing import Any

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
    enum_values: Collection[int] | None,
) -> tuple[dict[str, Any], int]:
    """Read one native-gated header without accepting unreviewed enum values."""
    fields = route.get("fields") or []
    tag = route.get("tag")
    members = route.get("serializedMemberCount")
    if (
        route.get("family") != "ActionHeader"
        or route.get("typeName") != _TYPE
        or tag != 0x0030 or members != 21
        or fields[:14] != _INHERITED or fields[14:] != _OWN
    ):
        raise ActionMapCodecError("onPhysicalInflictionHeader:invalid-route")
    if (
        not enum_values
        or any(type(value) is not int for value in enum_values)
        or len(set(enum_values)) != len(enum_values)
    ):
        raise ActionMapCodecError("onPhysicalInflictionHeader:enum-native-gate")
    if offset < 0 or data[offset:offset + 2] != bytes((tag, members)):
        raise ActionMapCodecError(f"onPhysicalInflictionHeader:invalid-header,offset={offset}")
    cursor = _Cursor(data, offset + 2)
    values: dict[str, Any] = {}
    spans: dict[str, list[int]] = {}
    for name, kind in fields:
        start = cursor.offset
        read_kind = "Param<int>" if kind == "Param<PhysicalInflictionType>" else kind
        value = cursor.value(read_kind, "onPhysicalInflictionHeader." + name)
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
