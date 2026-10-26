"""Selected stored ActionHeader cursor for OnEncounterIntroPartEnd."""

from __future__ import annotations

from typing import Any

from scripts.game_data.memorypack.core import memorypack_union_header

from .action_map import ActionMapCodecError, _Cursor


_TYPE = "Beyond.Gameplay.Actions.LevelEvent.OnEncounterIntroPartEnd"
def decode_on_encounter_intro_part_end_header(
    data: bytes, offset: int, route: dict[str, Any], *, game_root=None, strings: Any=None,
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
        or type(tag) is not int or not 0 <= tag <= 0xFFFF
        or any(not isinstance(row, list) or len(row) != 2 for row in fields)
    ):
        raise ActionMapCodecError("onEncounterIntroPartEnd:invalid-route")
    header = memorypack_union_header(route["tag"], route["serializedMemberCount"])
    if offset < 0 or data[offset:offset + len(header)] != header:
        raise ActionMapCodecError(f"onEncounterIntroPartEnd:invalid-header,offset={offset}")
    cursor = _Cursor(data, offset + len(header), game_root=game_root, strings=strings)
    values: dict[str, Any] = {}
    spans: dict[str, list[int]] = {}
    for name, kind in fields:
        start = cursor.offset
        values[name] = cursor.node_string(f"onEncounterIntroPartEnd.{name}",{**route,"nativeGate":"levelscript_on_encounter_intro_part_end_native"},name) if kind=="string" else cursor.value(kind,f"onEncounterIntroPartEnd.{name}")
        spans[name] = [start, cursor.offset]
    return {
        "sourceOffset": offset, "endOffset": cursor.offset,
        "unionTag": tag, "memberCount": count,
        "wrapperName": route["wrapperName"],
        "fields": values, "fieldSpans": spans,
    }, cursor.offset
