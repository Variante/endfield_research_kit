"""Exact byte reader for the selected EnterDollyTrackCamera action body.

The caller must authenticate the selected native contract before publishing a
decoded record. The parser consumes one declared ActionBase node at its given
cursor; it never searches for a plausible tag or guesses a record end.
"""

from __future__ import annotations

from typing import Any

from . import params
from .action_map import ActionMapCodecError, _Cursor


def decode_move_state_param(
    data: bytes, offset: int, enum_values: dict[int, str],
) -> tuple[dict[str, Any] | None, int]:
    """Decode the finite enum Param at an already established field cursor."""
    if not 0 <= offset < len(data):
        raise ActionMapCodecError(f"trackCamera.moveWay:truncated,offset={offset}")
    if data[offset] == 0xFF:
        return None, offset + 1
    decoded = params.decode_i32_param(data, offset)
    if decoded is None:
        raise ActionMapCodecError(f"trackCamera.moveWay:invalid-param,offset={offset}")
    detail, end = decoded
    value = detail["value"]
    if value not in enum_values:
        raise ActionMapCodecError(f"trackCamera.moveWay:unknown-enum={value},offset={offset}")
    return {**detail, "enumName": enum_values[value]}, end


def decode_track_camera_action(
    data: bytes, offset: int, route: dict[str, Any], enum_values: dict[int, str],
) -> tuple[dict[str, Any], int]:
    """Read all selected fields, returning their exact source spans.

    ``route`` and ``enum_values`` must come from a successfully validated
    selected native contract. The caller owns that gate and source hash join.
    """
    fields = route["fields"]
    tag = route["tag"]
    member_count = route["memberCount"]
    move_fields = [name for name, kind, *_ in fields if name == "moveWay" and
                   kind.startswith("Param<") and kind.endswith("TrackCameraMoveState>")]
    if (
        route.get("family") != "ActionBase"
        or not 0 <= tag < 0xFA
        or not 0 < member_count < 0xFF
        or len(fields) != member_count
        or move_fields != ["moveWay"]
        or offset < 0 or offset + 2 > len(data)
        or data[offset : offset + 2] != bytes((tag, member_count))
    ):
        raise ActionMapCodecError(f"trackCamera:invalid-route-or-header,offset={offset}")
    cursor = _Cursor(data, offset + 2)
    values: dict[str, Any] = {}
    spans: dict[str, list[int]] = {}
    for name, kind, *_ in fields:
        start = cursor.offset
        if name == "moveWay":
            values[name], cursor.offset = decode_move_state_param(data, start, enum_values)
        else:
            values[name] = cursor.value(kind, f"trackCamera.{name}")
        spans[name] = [start, cursor.offset]
    return {
        "family": "ActionBase", "unionTag": tag, "memberCount": member_count,
        "sourceOffset": offset, "endOffset": cursor.offset,
        "fields": values, "fieldSpans": spans,
    }, cursor.offset
