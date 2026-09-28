"""Exact stored-field reader for selected TyphoeaArcherySetChipId actions."""

from __future__ import annotations

from typing import Any

from .action_map import ActionMapCodecError, _Cursor


def decode_typhoea_chip_id_action(
    data: bytes, offset: int, route: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    fields = route["fields"]
    if (
        route.get("family") != "ActionBase"
        or route.get("tag") != 0x04FA
        or route.get("memberCount") != 10
        or len(fields) != 10
        or [row[:2] for row in fields[8:]]
        != [["mainChipId", "Param<string>"], ["subChipId", "Param<string>"]]
        or offset < 0 or data[offset:offset+4] != b"\xfa\xfa\x04\x0a"
    ):
        raise ActionMapCodecError(f"typhoeaChipId:invalid-route-or-header,offset={offset}")
    cursor = _Cursor(data, offset + 4)
    values: dict[str, Any] = {}
    spans: dict[str, list[int]] = {}
    for name, kind, *_ in fields:
        start = cursor.offset
        values[name] = cursor.value(kind, f"typhoeaChipId.{name}")
        spans[name] = [start, cursor.offset]
    return {
        "family": "ActionBase", "unionTag": 0x04FA, "memberCount": 10,
        "sourceOffset": offset, "endOffset": cursor.offset,
        "fields": values, "fieldSpans": spans,
    }, cursor.offset
