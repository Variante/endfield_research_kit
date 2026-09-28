"""Selected stored ActionHeader cursor for OnEntityCastSkill."""

from __future__ import annotations

from typing import Any

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
        or tag != 0x0069
        or members != len(fields) or members != 20
        or fields[:14] != _BASE_FIELDS
        or fields[14:] != _OWN_FIELDS
    ):
        raise ActionMapCodecError("onEntityCastSkillHeader:invalid-route")
    if offset < 0 or data[offset:offset + 2] != bytes((tag, members)):
        raise ActionMapCodecError(f"onEntityCastSkillHeader:invalid-header,offset={offset}")
    cursor = _Cursor(data, offset + 2)
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
