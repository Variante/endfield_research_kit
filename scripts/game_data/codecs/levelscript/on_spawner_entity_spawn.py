"""Selected stored ActionHeader cursor for OnSpawnerEntitySpawn."""

from __future__ import annotations

from typing import Any

from .action_map import ActionMapCodecError, _Cursor


_TYPE = "Beyond.Gameplay.Actions.LevelEvent.OnSpawnerEntitySpawn"


def decode_on_spawner_entity_spawn_header(
    data: bytes, offset: int, route: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    """Read one selected header from the native route's exact member order."""
    fields = route.get("fields") or []
    tag = route.get("tag")
    members = route.get("serializedMemberCount")
    if (
        route.get("family") != "ActionHeader"
        or route.get("typeName") != _TYPE
        or tag != 0x0095
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
        raise ActionMapCodecError("onSpawnerEntitySpawnHeader:invalid-route")
    if fields[14:] != [
        ["entityOutput", "ParamOutput<EntityPtr>"],
        ["filterType", "Param<OnSpawnerEntitySpawn.FilterType>"],
        ["groupKeyFilter", "Param<string>"],
        ["groupKeyOutput", "ParamOutput<string>"],
        ["spawnerFilter", "Param<SpawnerPtr>"],
        ["waveKeyFilter", "Param<string>"],
        ["waveKeyOutput", "ParamOutput<string>"],
    ]:
        raise ActionMapCodecError("onSpawnerEntitySpawnHeader:invalid-own-fields")
    header = bytes((tag, members))
    if offset < 0 or data[offset:offset + 2] != header:
        raise ActionMapCodecError(f"onSpawnerEntitySpawnHeader:invalid-header,offset={offset}")
    cursor = _Cursor(data, offset + 2)
    values: dict[str, Any] = {}
    spans: dict[str, list[int]] = {}
    for name, kind in fields:
        start = cursor.offset
        read_kind = "Param<int>" if kind == "Param<OnSpawnerEntitySpawn.FilterType>" else kind
        values[name] = cursor.value(read_kind, f"onSpawnerEntitySpawnHeader.{name}")
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
