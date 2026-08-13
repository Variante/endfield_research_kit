"""Exact top-level tail decoder for current-build ``LevelScriptData``."""

from __future__ import annotations

import struct
from typing import Any

from . import active_shapes
from . import trigger_volumes


START_TYPE_NAMES = {
    0: "ByEnterStartShape",
    1: "Manual",
    2: "SameWithActive",
    3: "Never",
}


def _u32(data: bytes, offset: int | None) -> int | None:
    if offset is None or offset < 0 or offset + 4 > len(data):
        return None
    return struct.unpack_from("<I", data, offset)[0]


def _list_status(raw_count: int | None) -> tuple[str, int | None]:
    if raw_count is None:
        return "missing", None
    if raw_count == 0xFFFFFFFF:
        return "null", None
    if raw_count <= 64:
        return "present", raw_count
    return "unknown", raw_count


def _offset_hex(offset: int | None) -> str:
    return f"0x{offset:x}" if isinstance(offset, int) and offset >= 0 else ""


def decode_tail_candidate(data: bytes, script_id_offset: int) -> dict[str, Any]:
    """Decode and score one exact top-level tail beginning at ``scriptId``."""
    start_shape_offset = script_id_offset + 8
    start_shape, start_shape_end = active_shapes.decode_shape_list(
        data,
        start_shape_offset,
    )
    start_shape_status = str(start_shape.get("status") or "missing")
    start_shape_count = start_shape.get("count")
    start_type_offset: int | None = None
    if start_shape_status in {"null", "present"} and start_shape_end is not None:
        start_type_offset = start_shape_end

    start_type_raw = _u32(data, start_type_offset)
    start_type_valid = start_type_raw in START_TYPE_NAMES
    task_map_offset = (
        start_type_offset + 4
        if start_type_valid and start_type_offset is not None
        else None
    )
    task_map_raw = _u32(data, task_map_offset)
    task_map_status, task_map_count = _list_status(task_map_raw)
    task_map_end: int | None = None
    if task_map_offset is not None and task_map_status == "null":
        task_map_end = task_map_offset + 4
    elif (
        task_map_offset is not None
        and task_map_status == "present"
        and task_map_count == 0
    ):
        # Empty dictionaries have no records, so the final member begins
        # immediately after the count. Never scan from an inferred later byte.
        task_map_end = task_map_offset + 4

    trigger_volume_offset = task_map_end
    trigger_volume: dict[str, Any] = {}
    trigger_volume_end: int | None = None
    if trigger_volume_offset is not None:
        trigger_volume, trigger_volume_end = trigger_volumes.decode_trigger_volume_map(
            data,
            trigger_volume_offset,
        )
    elif task_map_offset is not None and task_map_status == "present":
        (
            trigger_volume_offset,
            trigger_volume,
            trigger_volume_end,
        ) = trigger_volumes.find_final_trigger_volume_map(
            data,
            search_start=task_map_offset + 4,
        )
    trigger_volume_status = str(trigger_volume.get("status") or "missing")
    trigger_volume_count = trigger_volume.get("count")

    score = script_id_offset
    if start_type_valid:
        score += 1_000_000
    if start_shape_status == "null":
        score += 100_000
    elif start_shape_count == 0:
        score += 50_000
    if task_map_status in {"null", "present"}:
        score += 10_000
    if (
        trigger_volume_status in {"null", "present"}
        and trigger_volume.get("parseStatus") != "truncated"
        and trigger_volume_end == len(data)
    ):
        score += 250_000

    return {
        "scriptIdOffset": script_id_offset,
        "scriptIdOffsetHex": f"0x{script_id_offset:x}",
        "startShapeListOffset": start_shape_offset,
        "startShapeListStatus": start_shape_status,
        "startShapeListCount": start_shape_count,
        "startShapeList": start_shape,
        "startTypeOffset": start_type_offset,
        "startTypeOffsetHex": _offset_hex(start_type_offset),
        "startTypeRaw": start_type_raw if start_type_valid else None,
        "startTypeName": START_TYPE_NAMES.get(
            start_type_raw if start_type_raw is not None else -1,
            "",
        ),
        "taskMapOffset": task_map_offset,
        "taskMapOffsetHex": _offset_hex(task_map_offset),
        "taskMapStatus": task_map_status,
        "taskMapCount": task_map_count,
        "triggerVolumesOffset": trigger_volume_offset,
        "triggerVolumesOffsetHex": _offset_hex(trigger_volume_offset),
        "triggerVolumesStatus": trigger_volume_status,
        "triggerVolumesCount": trigger_volume_count,
        "triggerVolumes": trigger_volume,
        "score": score,
    }
