"""Selected stored ActionHeader cursor for OnEncounterIntroPartEnd."""

from __future__ import annotations

from typing import Any

from .action_map import ActionMapCodecError, _Cursor


_TYPE = "Beyond.Gameplay.Actions.LevelEvent.OnEncounterIntroPartEnd"
def decode_on_encounter_intro_part_end_header(
    data: bytes, offset: int, route: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    """Read one selected event header from its authenticated member order."""
    fields = route.get("fields")
    count = route.get("serializedMemberCount")
    tag = route.get("tag")
    if (
        route.get("family") != "ActionHeader"
        or route.get("typeName") != _TYPE
        or not isinstance(fields, list) or not fields
        or type(count) is not int or count != len(fields) or not 0 <= count <= 255
        or type(tag) is not int or not 0 <= tag < 0xFA
        or any(not isinstance(row, list) or len(row) != 2 for row in fields)
    ):
        raise ActionMapCodecError("onEncounterIntroPartEnd:invalid-route")
    if offset < 0 or data[offset:offset + 2] != bytes((tag, count)):
        raise ActionMapCodecError(f"onEncounterIntroPartEnd:invalid-header,offset={offset}")
    cursor = _Cursor(data, offset + 2)
    values: dict[str, Any] = {}
    spans: dict[str, list[int]] = {}
    for name, kind in fields:
        start = cursor.offset
        values[name] = cursor.value(kind, f"onEncounterIntroPartEnd.{name}")
        spans[name] = [start, cursor.offset]
    return {
        "sourceOffset": offset, "endOffset": cursor.offset,
        "unionTag": tag, "memberCount": count,
        "wrapperName": route["wrapperName"],
        "fields": values, "fieldSpans": spans,
    }, cursor.offset
