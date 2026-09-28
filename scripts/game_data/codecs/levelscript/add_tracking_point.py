"""Selected stored ActionBase cursor for AddTrackingPoint."""

from __future__ import annotations

from typing import Any

from .action_map import ActionMapCodecError, _Cursor


_TYPE = "Beyond.Gameplay.Actions.AddTrackingPoint"
_FIELDS = [
    ["dontLogWarning", "bool"], ["ID", "int32"],
    ["releaseWhenExecutionFinished", "bool"], ["uid", "string"],
    ["scopeMask", "int32"], ["useCurrentScope", "bool"],
    ["useGraphScope", "bool"], ["nextID", "int32"],
    ["buildingInstKey", "Param<string>"], ["entityLogicId", "Param<ulong>"],
    ["guidingArea", "Param<float>"], ["levelId", "Param<string>"],
    ["pos", "Param<Vector3>"],
    ["styleType", "Param<CommonTrackingPointStyleType>"],
    ["trackingPointId", "Param<string>"],
    ["trackingType", "Param<CommonTrackingType>"],
]
_ENUMS = {"Param<CommonTrackingPointStyleType>", "Param<CommonTrackingType>"}


def decode_add_tracking_point_action(
    data: bytes, offset: int, route: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    """Read one selected action from its authenticated member order."""
    if (
        route.get("family") != "ActionBase"
        or route.get("typeName") != _TYPE
        or route.get("tag") != 0x0012
        or route.get("serializedMemberCount") != 16
        or route.get("fields") != _FIELDS
    ):
        raise ActionMapCodecError("addTrackingPoint:invalid-route")
    if offset < 0 or data[offset:offset + 2] != b"\x12\x10":
        raise ActionMapCodecError(f"addTrackingPoint:invalid-header,offset={offset}")
    cursor = _Cursor(data, offset + 2)
    values: dict[str, Any] = {}
    spans: dict[str, list[int]] = {}
    for name, kind in _FIELDS:
        start = cursor.offset
        values[name] = cursor.value("Param<int>" if kind in _ENUMS else kind,
                                    f"addTrackingPoint.{name}")
        spans[name] = [start, cursor.offset]
    return {
        "sourceOffset": offset, "endOffset": cursor.offset,
        "unionTag": 0x0012, "memberCount": 16,
        "wrapperName": route["wrapperName"],
        "fields": values, "fieldSpans": spans,
    }, cursor.offset
