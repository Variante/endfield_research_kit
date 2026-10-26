"""Selected stored ActionBase cursor for ResumeSpawner."""

from __future__ import annotations

from typing import Any
from scripts.game_data.memorypack.core import memorypack_union_header

from .action_map import ActionMapCodecError, _Cursor


_TYPE = "Beyond.Gameplay.Actions.ResumeSpawner"
_FIELDS = [
    ["dontLogWarning", "bool"], ["ID", "int32"],
    ["releaseWhenExecutionFinished", "bool"], ["uid", "string"],
    ["scopeMask", "int32"], ["useCurrentScope", "bool"],
    ["useGraphScope", "bool"], ["nextID", "int32"],
    ["pauseKey", "Param<string>"], ["spawnerPtr", "Param<SpawnerPtr>"],
]


def decode_resume_spawner_action(
    data: bytes, offset: int, route: dict[str, Any],
    *, game_root: Any = None, strings: Any = None,
) -> tuple[dict[str, Any], int]:
    """Read one selected action from its authenticated member order."""
    if (
        route.get("family") != "ActionBase"
        or route.get("typeName") != _TYPE
        or type(route.get("tag")) is not int or not 0 <= route["tag"] <= 0xFFFF
        or route.get("serializedMemberCount") != 10
        or route.get("fields") != _FIELDS
    ):
        raise ActionMapCodecError("resumeSpawner:invalid-route")
    header = memorypack_union_header(route["tag"], route["serializedMemberCount"])
    if offset < 0 or data[offset:offset + len(header)] != header:
        raise ActionMapCodecError(f"resumeSpawner:invalid-header,offset={offset}")
    cursor = _Cursor(data, offset + len(header), game_root=game_root, strings=strings, route=route)
    values: dict[str, Any] = {}
    spans: dict[str, list[int]] = {}
    for name, kind in _FIELDS:
        start = cursor.offset
        values[name] = cursor.value(kind, f"resumeSpawner.{name}")
        spans[name] = [start, cursor.offset]
    return {
        "sourceOffset": offset, "endOffset": cursor.offset,
        "unionTag": route["tag"], "memberCount": 10,
        "wrapperName": route["wrapperName"],
        "fields": values, "fieldSpans": spans,
    }, cursor.offset
