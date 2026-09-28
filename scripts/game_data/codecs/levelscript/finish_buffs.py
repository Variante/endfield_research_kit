"""Exact reached null-list reader for selected FinishBuffs actions.

The native contract establishes ``Param<List<BuffPtr>>`` as the ninth stored
member. Current source cursors carry only a null list with a parameter path;
positive list elements remain outside this reader's boundary.
"""

from __future__ import annotations

import struct
from typing import Any

from . import params
from .action_map import ActionMapCodecError, _Cursor


def decode_null_buff_list_param(data: bytes, offset: int) -> tuple[dict[str, Any], int]:
    if (
        offset < 0 or offset + 5 > len(data) or data[offset] != 0x04
        or struct.unpack_from("<i", data, offset + 1)[0] != -1
    ):
        raise ActionMapCodecError(f"finishBuffs.buffs:unsupported-positive-or-invalid-list,offset={offset}")
    tail = params.decode_param_tail(data, offset + 5)
    if tail is None:
        raise ActionMapCodecError(f"finishBuffs.buffs:invalid-param-tail,offset={offset}")
    detail, end = tail
    return {"value": None, **detail}, end


def decode_finish_buffs_action(
    data: bytes, offset: int, route: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    fields = route["fields"]
    if (
        route.get("family") != "ActionBase"
        or route.get("tag") != 0x00E6
        or route.get("memberCount") != 9
        or len(fields) != 9
        or fields[8][:2] != ["buffs", "Param<List<BuffPtr>>"]
        or offset < 0 or data[offset:offset+2] != b"\xe6\x09"
    ):
        raise ActionMapCodecError(f"finishBuffs:invalid-route-or-header,offset={offset}")
    cursor = _Cursor(data, offset + 2)
    values: dict[str, Any] = {}
    spans: dict[str, list[int]] = {}
    for name, kind, *_ in fields:
        start = cursor.offset
        if name == "buffs":
            values[name], cursor.offset = decode_null_buff_list_param(data, start)
        else:
            values[name] = cursor.value(kind, f"finishBuffs.{name}")
        spans[name] = [start, cursor.offset]
    return {
        "family": "ActionBase", "unionTag": 0x00E6, "memberCount": 9,
        "sourceOffset": offset, "endOffset": cursor.offset,
        "fields": values, "fieldSpans": spans,
    }, cursor.offset
