"""Selected stored ActionHeader cursor for OnSpellInfliction."""

from __future__ import annotations

from typing import Any

from scripts.game_data.memorypack.core import memorypack_union_header

from .action_map import ActionMapCodecError, _Cursor


_TYPE = "Beyond.Gameplay.Actions.LevelEvent.OnSpellInfliction"


def decode_on_spell_infliction_header(
    data: bytes, offset: int, route: dict[str, Any],
    *, game_root: Any = None, strings: Any = None,
) -> tuple[dict[str, Any], int]:
    """Read one selected header from the native route's exact member order."""
    fields = route.get("fields") or []
    tag = route.get("tag")
    members = route.get("serializedMemberCount")
    if (
        route.get("family") != "ActionHeader"
        or route.get("typeName") != _TYPE
        or type(tag) is not int or not 0 <= tag <= 0xFFFF
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
    header = memorypack_union_header(route["tag"], route["serializedMemberCount"])
    if offset < 0 or data[offset:offset + len(header)] != header:
        raise ActionMapCodecError(f"onSpellInflictionHeader:invalid-header,offset={offset}")
    cursor = _Cursor(data, offset + len(header), game_root=game_root, strings=strings, route=route)
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
