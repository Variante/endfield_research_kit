"""Selected stored ActionHeader cursor for OnSpellAbnormalStart.

The caller must provide enum values from a validated native contract. This
reader does not infer SpellAbnormalType width or allow arbitrary int values.
"""

from __future__ import annotations

from collections.abc import Collection
from typing import Any

from .action_map import ActionMapCodecError, _Cursor


_TYPE = "Beyond.Gameplay.Actions.LevelEvent.OnSpellAbnormalStart"
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
    ["sourceOutput", "ParamOutput<EntityPtr>"],
    ["typeFilter", "Param<SpellAbnormalType>"],
    ["typeOutput", "ParamOutput<int>"],
    ["useEntityFilter", "Param<bool>"],
]


def decode_on_spell_abnormal_start_header(
    data: bytes, offset: int, route: dict[str, Any], *,
    enum_values: Collection[int] | None,
) -> tuple[dict[str, Any], int]:
    """Read exactly one native-gated header and its signed enum parameter."""
    fields = route.get("fields") or []
    tag = route.get("tag")
    members = route.get("serializedMemberCount")
    if (
        route.get("family") != "ActionHeader"
        or route.get("typeName") != _TYPE
        or type(tag) is not int or not 0 <= tag < 0xFA
        or members != len(fields) or members != 20
        or fields[:14] != _INHERITED or fields[14:] != _OWN
    ):
        raise ActionMapCodecError("onSpellAbnormalStartHeader:invalid-route")
    if (
        not enum_values
        or any(type(value) is not int for value in enum_values)
        or len(set(enum_values)) != len(enum_values)
    ):
        raise ActionMapCodecError("onSpellAbnormalStartHeader:enum-native-gate")
    header = bytes((tag, members))
    if offset < 0 or data[offset:offset + 2] != header:
        raise ActionMapCodecError(f"onSpellAbnormalStartHeader:invalid-header,offset={offset}")
    cursor = _Cursor(data, offset + 2)
    values: dict[str, Any] = {}
    spans: dict[str, list[int]] = {}
    for name, kind in fields:
        start = cursor.offset
        read_kind = "Param<int>" if kind == "Param<SpellAbnormalType>" else kind
        value = cursor.value(read_kind, "onSpellAbnormalStartHeader." + name)
        if (
            kind == "Param<SpellAbnormalType>"
            and value is not None
            and value["value"] not in enum_values
        ):
            raise ActionMapCodecError(
                f"onSpellAbnormalStartHeader:unsupported-enum={value['value']},offset={start}"
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
