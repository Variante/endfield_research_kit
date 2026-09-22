"""Exact current-wrapper codec for authored LevelData guide hints."""

from __future__ import annotations

from typing import Any

from .memorypack import read_bool, read_count, read_i32, read_string


def _i32_vector(data: bytes, offset: int, width: int):
    values = []
    for _ in range(width):
        decoded = read_i32(data, offset)
        if decoded is None:
            return None
        value, offset = decoded
        values.append(value)
    return values, offset


def decode_level_guide_hint_list(data: bytes, offset: int) -> dict[str, Any] | None:
    """Decode ``List<LevelDataGuideHintConfig>`` in generated setter order."""
    start = offset
    decoded = read_count(data, offset, max_count=100_000)
    if decoded is None:
        return None
    count, cursor = decoded
    rows: list[dict[str, Any] | None] = []
    segment_total = 0
    for index in range(max(0, count)):
        row_start = cursor
        if cursor >= len(data):
            return None
        if data[cursor] == 0xFF:
            rows.append(None)
            cursor += 1
            continue
        if data[cursor] != 10:
            return None
        cursor += 1
        values: dict[str, Any] = {}
        for name, reader in (
            ("beginGuideGroupId", read_string),
            ("defaultEnable", read_bool),
            ("endGuideGroupId", read_string),
            ("fromInstKey", read_string),
            ("hintId", read_string),
        ):
            value = reader(data, cursor)
            if value is None:
                return None
            values[name], cursor = value
        segments_start = cursor
        segments_decoded = read_count(data, cursor, max_count=100_000)
        if segments_decoded is None:
            return None
        segment_count, cursor = segments_decoded
        segments = []
        for _ in range(max(0, segment_count)):
            vector = _i32_vector(data, cursor, 2)
            if vector is None:
                return None
            value, cursor = vector
            segments.append(value)
            segment_total += 1
        values["segments"] = {
            "startOffset": segments_start,
            "count": segment_count,
            "value": None if segment_count == -1 else segments,
        }
        face = read_i32(data, cursor)
        if face is None:
            return None
        values["startFace"], cursor = face
        point = _i32_vector(data, cursor, 3)
        if point is None:
            return None
        values["startPoint"], cursor = point
        to_key = read_string(data, cursor)
        if to_key is None:
            return None
        values["toInstKey"], cursor = to_key
        hint_type = read_i32(data, cursor)
        if hint_type is None:
            return None
        values["typeRaw"], cursor = hint_type
        rows.append({"indexInCollection": index, "startOffset": row_start,
                     "endOffset": cursor, "memberCount": 10, **values})
    return {
        "startOffset": start,
        "endOffset": cursor,
        "count": count,
        "value": None if count == -1 else rows,
        "segmentCount": segment_total,
        "itemFieldOrder": [
            "beginGuideGroupId", "defaultEnable", "endGuideGroupId",
            "fromInstKey", "hintId", "segments", "startFace",
            "startPoint", "toInstKey", "type",
        ],
        "fieldOrderSource": "current generated LevelDataGuideHintConfigForMemoryPack wrapper",
    }
