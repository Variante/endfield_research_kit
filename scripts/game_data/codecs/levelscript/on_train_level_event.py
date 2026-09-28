"""Selected stored ActionHeader cursor for OnTrainLevelEvent."""

from __future__ import annotations

from typing import Any

from .action_map import ActionMapCodecError, _Cursor


_TYPE = "Beyond.Gameplay.Actions.LevelEvent.OnTrainLevelEvent"


def decode_on_train_level_event_header(
    data: bytes, offset: int, route: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    """Read one selected header from the native route's exact member order."""
    fields = route.get("fields") or []
    tag = route.get("tag")
    members = route.get("serializedMemberCount")
    if (
        route.get("family") != "ActionHeader"
        or route.get("typeName") != _TYPE
        or tag != 0x00AD
        or members != len(fields) or members != 16
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
        raise ActionMapCodecError("onTrainLevelEventHeader:invalid-route")
    if fields[14:] != [["eventKey", "Param<string>"], ["value", "ParamOutput<object>"]]:
        raise ActionMapCodecError("onTrainLevelEventHeader:invalid-own-fields")
    header = bytes((tag, members))
    if offset < 0 or data[offset:offset + 2] != header:
        raise ActionMapCodecError(f"onTrainLevelEventHeader:invalid-header,offset={offset}")
    cursor = _Cursor(data, offset + 2)
    values: dict[str, Any] = {}
    spans: dict[str, list[int]] = {}
    for name, kind in fields:
        start = cursor.offset
        values[name] = cursor.value(kind, f"onTrainLevelEventHeader.{name}")
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
