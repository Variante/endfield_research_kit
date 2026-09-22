"""Exact current-wrapper codec for LevelData dynamic occlusion areas."""

from __future__ import annotations

from typing import Any

from .function_area import LevelFunctionAreaCodecError, decode_condition_runtime
from .memorypack import read_count, read_i32


def decode_dynamic_occlude_area_list(data: bytes, offset: int) -> dict[str, Any] | None:
    start = offset
    decoded = read_count(data, offset, max_count=100_000)
    if decoded is None:
        return None
    count, cursor = decoded
    rows: list[dict[str, Any] | None] = []
    grid_total = line_total = 0
    for index in range(max(0, count)):
        row_start = cursor
        if cursor >= len(data): return None
        if data[cursor] == 0xFF:
            rows.append(None); cursor += 1; continue
        if data[cursor] != 3: return None
        cursor += 1
        area = read_i32(data, cursor)
        if area is None: return None
        area_id, cursor = area
        if cursor >= len(data): return None
        if data[cursor] == 0xFF:
            condition = None; cursor += 1
        else:
            try:
                condition, cursor = decode_condition_runtime(
                    data, cursor, f"dynamicOccludeAreas[{index}].condition"
                )
            except LevelFunctionAreaCodecError:
                return None
        grids_start = cursor
        grids_decoded = read_count(data, cursor, max_count=100_000)
        if grids_decoded is None: return None
        grid_count, cursor = grids_decoded
        grids: list[dict[str, Any] | None] = []
        for grid_index in range(max(0, grid_count)):
            grid_start = cursor
            if cursor >= len(data): return None
            if data[cursor] == 0xFF:
                grids.append(None); cursor += 1; continue
            if data[cursor] != 3: return None
            cursor += 1
            height_decoded = read_i32(data, cursor)
            if height_decoded is None: return None
            height, cursor = height_decoded
            lines_start = cursor
            lines_decoded = read_count(data, cursor, max_count=1_000_000)
            if lines_decoded is None: return None
            line_count, cursor = lines_decoded
            lines: list[dict[str, Any]] = []
            for line_index in range(max(0, line_count)):
                line_start = cursor
                if cursor >= len(data) or data[cursor] != 2: return None
                cursor += 1
                length_decoded = read_i32(data, cursor)
                x_decoded = read_i32(data, length_decoded[1]) if length_decoded else None
                y_decoded = read_i32(data, x_decoded[1]) if x_decoded else None
                if length_decoded is None or x_decoded is None or y_decoded is None:
                    return None
                length, _ = length_decoded; x, _ = x_decoded; y, cursor = y_decoded
                lines.append({"indexInCollection": line_index,
                              "startOffset": line_start, "endOffset": cursor,
                              "memberCount": 2, "length": length,
                              "startPos": [x, y]})
                line_total += 1
            y_pos_decoded = read_i32(data, cursor)
            if y_pos_decoded is None: return None
            y_pos, cursor = y_pos_decoded
            grids.append({"indexInCollection": grid_index,
                          "startOffset": grid_start, "endOffset": cursor,
                          "memberCount": 3, "height": height,
                          "lineList": {"startOffset": lines_start,
                                       "count": line_count,
                                       "value": None if line_count == -1 else lines},
                          "yPos": y_pos})
            grid_total += 1
        rows.append({"indexInCollection": index, "startOffset": row_start,
                     "endOffset": cursor, "memberCount": 3,
                     "areaId": area_id, "condition": condition,
                     "gridData": {"startOffset": grids_start,
                                  "count": grid_count,
                                  "value": None if grid_count == -1 else grids}})
    return {"startOffset": start, "endOffset": cursor, "count": count,
            "value": None if count == -1 else rows,
            "gridCount": grid_total, "lineCount": line_total,
            "itemFieldOrder": ["areaId", "condition", "gridData"],
            "fieldOrderSource": "current generated LevelDynamicOccludeAreaDataForMemoryPack wrapper"}
