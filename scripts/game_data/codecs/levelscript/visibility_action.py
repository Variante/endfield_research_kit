"""Exact stored-byte reader for the selected SetEntitiesVisibility action.

The caller must authenticate the selected native contract before publishing a
decoded action. This reads the declared fields at the supplied cursor only.
"""

from __future__ import annotations

from typing import Any

from . import params
from .action_map import ActionMapCodecError, _Cursor


def decode_visible_source_param(
    data: bytes, offset: int, enum_values: dict[int, str],
) -> tuple[dict[str, Any] | None, int]:
    """Decode a finite Int32 ModelVisibleType Param at an established cursor."""
    if offset < 0 or offset >= len(data):
        raise ActionMapCodecError(f"visibilityAction.visibleSource:truncated,offset={offset}")
    if data[offset] == 0xFF:
        return None, offset + 1
    decoded = params.decode_i32_param(data, offset)
    if decoded is None:
        raise ActionMapCodecError(f"visibilityAction.visibleSource:invalid-param,offset={offset}")
    detail, end = decoded
    value = detail["value"]
    if value not in enum_values:
        raise ActionMapCodecError(f"visibilityAction.visibleSource:unknown-enum={value},offset={offset}")
    return {**detail, "enumName": enum_values[value]}, end


def decode_visibility_action(
    data: bytes, offset: int, route: dict[str, Any], enum_values: dict[int, str],
) -> tuple[dict[str, Any], int]:
    fields = route["fields"]
    tag = route["tag"]
    count = route["memberCount"]
    if (
        route.get("family") != "ActionBase"
        or tag != 0x0406
        or count != 12
        or len(fields) != count
        or fields[-1][:2] != ["visibleSource", "Param<ModelVisibleType>"]
        or offset < 0 or offset + 4 > len(data)
        or data[offset:offset + 4] != b"\xfa\x06\x04\x0c"
    ):
        raise ActionMapCodecError(f"visibilityAction:invalid-route-or-header,offset={offset}")
    cursor = _Cursor(data, offset + 4)
    values: dict[str, Any] = {}
    spans: dict[str, list[int]] = {}
    for name, kind, *_ in fields:
        start = cursor.offset
        if name == "visibleSource":
            values[name], cursor.offset = decode_visible_source_param(data, start, enum_values)
        else:
            values[name] = cursor.value(kind, f"visibilityAction.{name}")
        spans[name] = [start, cursor.offset]
    return {
        "family": "ActionBase", "unionTag": tag, "memberCount": count,
        "sourceOffset": offset, "endOffset": cursor.offset,
        "fields": values, "fieldSpans": spans,
    }, cursor.offset
