"""Exact current wrapper for LevelData erosion-sludge records."""

from __future__ import annotations

from typing import Any

from .memorypack import read_count, read_i32, read_i64, read_string, read_u64


def decode_erosion_sludge_list(data: bytes, offset: int) -> dict[str, Any] | None:
    start = offset
    decoded = read_count(data, offset, max_count=100_000)
    if decoded is None: return None
    count, cursor = decoded
    rows: list[dict[str, Any] | None] = []
    for index in range(max(0, count)):
        row_start = cursor
        if cursor >= len(data): return None
        if data[cursor] == 0xFF:
            rows.append(None); cursor += 1; continue
        if data[cursor] != 4: return None
        cursor += 1
        values = {}
        for name, reader in (("coreId", read_u64), ("globalVarId", read_i32),
                             ("globalVarValue", read_i64), ("sludgeName", read_string)):
            value = reader(data, cursor)
            if value is None: return None
            values[name], cursor = value
        rows.append({"indexInCollection": index, "startOffset": row_start,
                     "endOffset": cursor, "memberCount": 4, **values})
    return {"startOffset": start, "endOffset": cursor, "count": count,
            "value": None if count == -1 else rows,
            "itemFieldOrder": ["coreId", "globalVarId", "globalVarValue", "sludgeName"],
            "fieldOrderSource": "current generated LevelErosionSludgeDataV2ForMemoryPack wrapper"}
