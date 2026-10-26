"""Selected stored ActionHeader cursor for OnEntityCastSkill."""

from __future__ import annotations

from typing import Any

from scripts.game_data.memorypack.core import memorypack_union_header

from .action_map import ActionMapCodecError, _Cursor


_TYPE = "Beyond.Gameplay.Actions.LevelEvent.OnEntityCastSkill"
_BASE_FIELDS = [
    ["dontLogWarning", "bool"], ["ID", "int32"],
    ["releaseWhenExecutionFinished", "bool"], ["uid", "string"],
    ["scopeMask", "int32"], ["useCurrentScope", "bool"],
    ["useGraphScope", "bool"], ["filterLevel", "int32"],
    ["filterMask", "int32"], ["filterMode", "bool"],
    ["nextID", "int32"], ["priority", "int32"],
    ["triggerActiveDuring", "int32"], ["validate", "Param<bool>"],
]
_OWN_FIELDS = [
    ["entity", "ParamOutput<EntityPtr>"],
    ["entityTemplateId", "ParamOutput<string>"],
    ["firstTargetId", "ParamOutput<ulong>"],
    ["isCharacter", "Param<bool>"],
    ["skillId", "ParamOutput<string>"],
    ["skillTypeFilter", "Param<SkillTypeMask>"],
]


def decode_on_entity_cast_skill_header(
    data: bytes, offset: int, route: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    """Read one selected header from the native route's exact member order."""
    fields = route.get("fields") or []
    tag = route.get("tag")
    members = route.get("serializedMemberCount")
    if (
        route.get("family") != "ActionHeader"
        or route.get("typeName") != _TYPE
        or type(tag) is not int or not 0 <= tag <= 0xFFFF
        or members != len(fields) or members != 20
        or fields[:14] != _BASE_FIELDS
        or fields[14:] != _OWN_FIELDS
    ):
        raise ActionMapCodecError("onEntityCastSkillHeader:invalid-route")
    header = memorypack_union_header(route["tag"], route["serializedMemberCount"])
    if offset < 0 or data[offset:offset + len(header)] != header:
        raise ActionMapCodecError(f"onEntityCastSkillHeader:invalid-header,offset={offset}")
    cursor = _Cursor(data, offset + len(header))
    values: dict[str, Any] = {}
    spans: dict[str, list[int]] = {}
    for name, kind in fields:
        start = cursor.offset
        read_kind = "Param<int>" if kind == "Param<SkillTypeMask>" else kind
        values[name] = cursor.value(read_kind, f"onEntityCastSkillHeader.{name}")
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
