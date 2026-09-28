"""Selected stored ActionHeader cursor for OnSpellInfliction."""

from __future__ import annotations

from typing import Any

from .action_map import ActionMapCodecError, _Cursor


_TYPE = "Beyond.Gameplay.Actions.LevelEvent.OnSpellInfliction"


def decode_on_spell_infliction_header(
    data: bytes, offset: int, route: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    """Read one selected header from the native route's exact member order."""
    fields = route.get("fields") or []
    tag = route.get("tag")
    members = route.get("serializedMemberCount")
    if (
        route.get("family") != "ActionHeader"
        or route.get("typeName") != _TYPE
        or tag != 0x00A5
        or members != len(fields) or members != 21
        or fields[:14] != [
            ["dontLogWarning", "bool"], ["ID", "int32"],
            ["releaseWhenExecutionFinished", "bool"], ["uid", "string"],
            ["scopeMask", "int32"], ["useCurrentScope", "bool"],
            ["useGraphScope", "bool"], ["filterLevel", "int32"],
            ["filterMask", "int32"], ["filterMode", "bool"],
            ["nextID", "int32"], ["priority", "int32"],
            ["triggerActiveDuring", "int32"], ["validate", "Param<bool>"],
        ]
    ):
        raise ActionMapCodecError("onSpellInflictionHeader:invalid-route")
    if fields[14:] != [
        ["countOutput", "ParamOutput<int>"],
        ["entityFilter", "Param<EntityPtr>"],
        ["entityOutput", "ParamOutput<EntityPtr>"],
        ["sourceOutput", "ParamOutput<EntityPtr>"],
        ["typeFilter", "Param<EnergyShardType>"],
        ["typeOutput", "ParamOutput<int>"],
        ["useEntityFilter", "Param<bool>"],
    ]:
        raise ActionMapCodecError("onSpellInflictionHeader:invalid-own-fields")
    header = bytes((tag, members))
    if offset < 0 or data[offset:offset + 2] != header:
        raise ActionMapCodecError(f"onSpellInflictionHeader:invalid-header,offset={offset}")
    cursor = _Cursor(data, offset + 2)
    values: dict[str, Any] = {}
    spans: dict[str, list[int]] = {}
    for name, kind in fields:
        start = cursor.offset
        read_kind = "Param<int>" if kind == "Param<EnergyShardType>" else kind
        values[name] = cursor.value(read_kind, f"onSpellInflictionHeader.{name}")
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
