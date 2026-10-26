"""Selected stored ActionHeader cursor for OnLeaderEnterTriggerVolumeList."""

from __future__ import annotations

from typing import Any
from scripts.game_data.memorypack.core import memorypack_union_header

from .action_map import ActionMapCodecError, _Cursor


_TYPE = "Beyond.Gameplay.Actions.ScriptEvent.OnLeaderEnterTriggerVolumeList"
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
    ["triggerSlotIds", "Param<List<uint>>"],
]


def _uint_list_param(cursor: _Cursor, field: str) -> Any:
    return cursor.value('Param<List<uint>>', field)


def decode_on_leader_enter_trigger_volume_list_header(
    data: bytes, offset: int, route: dict[str, Any],
    *, game_root: Any = None, strings: Any = None, numeric_list_params: Any = None,
) -> tuple[dict[str, Any], int]:
    """Read one selected event header from its authenticated member order."""
    if (
        route.get("family") != "ActionHeader"
        or route.get("typeName") != _TYPE
        or type(route.get("tag")) is not int or not 0 <= route["tag"] <= 0xFFFF
        or route.get("serializedMemberCount") != 17
        or route.get("fields") != _FIELDS
    ):
        raise ActionMapCodecError("onLeaderEnterTriggerVolumeList:invalid-route")
    header = memorypack_union_header(route["tag"], route["serializedMemberCount"])
    if offset < 0 or data[offset:offset + len(header)] != header:
        raise ActionMapCodecError(f"onLeaderEnterTriggerVolumeList:invalid-header,offset={offset}")
    cursor = _Cursor(data, offset + len(header), game_root=game_root, strings=strings, route=route, numeric_list_params=numeric_list_params)
    values: dict[str, Any] = {}
    spans: dict[str, list[int]] = {}
    for name, kind in _FIELDS:
        start = cursor.offset
        values[name] = (
            _uint_list_param(cursor, f"onLeaderEnterTriggerVolumeList.{name}")
            if kind == "Param<List<uint>>"
            else cursor.value(kind, f"onLeaderEnterTriggerVolumeList.{name}")
        )
        spans[name] = [start, cursor.offset]
    return {
        "sourceOffset": offset,
        "endOffset": cursor.offset,
        "unionTag": route["tag"],
        "memberCount": 17,
        "wrapperName": route["wrapperName"],
        "fields": values,
        "fieldSpans": spans,
    }, cursor.offset
