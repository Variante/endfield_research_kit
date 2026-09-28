"""Stored fields of the selected MarkTaskConditionFailed action."""

from __future__ import annotations

import struct
from typing import Any

from . import params
from .action_map import ActionMapCodecError, _Cursor


def decode_script_task_ptr_param(
    data: bytes, offset: int,
) -> tuple[dict[str, Any], int]:
    """Read the reached Param<ScriptTaskPtr> one-member key wrapper."""
    if offset < 0 or offset + 2 > len(data) or data[offset:offset + 2] != b"\x04\x01":
        raise ActionMapCodecError(f"markTaskConditionFailed.taskPtr:member-count,offset={offset}")
    cursor = _Cursor(data, offset + 2)
    key = cursor.string("markTaskConditionFailed.taskPtr.value.key")
    tail = params.decode_param_tail(data, cursor.offset)
    if tail is None:
        raise ActionMapCodecError(f"markTaskConditionFailed.taskPtr:param-tail,offset={cursor.offset}")
    detail, end = tail
    return {"value": {"key": key}, **detail}, end


def decode_mark_task_condition_failed_action(
    data: bytes, offset: int, route: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    """Advance one selected action span using the native route's field order."""
    fields = route.get("fields") or []
    tag = route.get("tag")
    members = route.get("serializedMemberCount")
    if (
        route.get("family") != "ActionBase"
        or route.get("typeName") != "Beyond.Gameplay.MarkTaskConditionFailed"
        or len(fields) != 10 or members != 10
        or fields[8:] != [["taskObjective", "Param<TaskObjectiveEnum>"],
                           ["taskPtr", "Param<ScriptTaskPtr>"]]
        or not isinstance(tag, int) or not 0 <= tag <= 0xFFFF
    ):
        raise ActionMapCodecError("markTaskConditionFailed:invalid-route")
    tag_bytes = bytes((tag,)) if tag < 0xFA else b"\xfa" + struct.pack("<H", tag)
    header = tag_bytes + bytes((members,))
    if offset < 0 or data[offset:offset + len(header)] != header:
        raise ActionMapCodecError(f"markTaskConditionFailed:invalid-header,offset={offset}")
    cursor = _Cursor(data, offset + len(header))
    values: dict[str, Any] = {}
    spans: dict[str, list[int]] = {}
    for name, kind in fields:
        start = cursor.offset
        if kind == "Param<TaskObjectiveEnum>":
            values[name] = cursor.value("Param<int>", f"markTaskConditionFailed.{name}")
        elif kind == "Param<ScriptTaskPtr>":
            values[name], cursor.offset = decode_script_task_ptr_param(data, cursor.offset)
        else:
            values[name] = cursor.value(
                "int32" if kind == "enum32" else kind,
                f"markTaskConditionFailed.{name}",
            )
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
