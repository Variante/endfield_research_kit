"""Selected stored ActionHeader cursor for OnLeaderEnterTriggerVolumeList."""

from __future__ import annotations

import struct
from typing import Any

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


def _uint_list_param(cursor: _Cursor, field: str) -> dict[str, Any]:
    marker = cursor.byte(field + ".memberCount")
    if marker != 4:
        raise ActionMapCodecError(f"{field}:unsupported-member-count={marker}")
    count = cursor.i32(field + ".value.count")
    if count == -1:
        value = None
    elif not 0 <= count <= 10_000:
        raise ActionMapCodecError(f"{field}:unsupported-count={count}")
    else:
        cursor.need(count * 4, field + ".value")
        value = list(struct.unpack_from(f"<{count}I", cursor.data, cursor.offset))
        cursor.offset += count * 4
    return cursor.param_tail(value, field)


def decode_on_leader_enter_trigger_volume_list_header(
    data: bytes, offset: int, route: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    """Read one selected event header from its authenticated member order."""
    if (
        route.get("family") != "ActionHeader"
        or route.get("typeName") != _TYPE
        or route.get("tag") != 0x00C0
        or route.get("serializedMemberCount") != 17
        or route.get("fields") != _FIELDS
    ):
        raise ActionMapCodecError("onLeaderEnterTriggerVolumeList:invalid-route")
    if offset < 0 or data[offset:offset + 2] != b"\xc0\x11":
        raise ActionMapCodecError(f"onLeaderEnterTriggerVolumeList:invalid-header,offset={offset}")
    cursor = _Cursor(data, offset + 2)
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
        "unionTag": 0x00C0,
        "memberCount": 17,
        "wrapperName": route["wrapperName"],
        "fields": values,
        "fieldSpans": spans,
    }, cursor.offset
