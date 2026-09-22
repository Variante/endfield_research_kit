"""Exact generated-wrapper codec for authored LevelData UI anchors."""

from __future__ import annotations

from typing import Any

from .memorypack import read_count, read_f32, read_string, read_u64


def _read_vector3(data: bytes, offset: int) -> tuple[list[float], int] | None:
    values: list[float] = []
    for _ in range(3):
        decoded = read_f32(data, offset)
        if decoded is None:
            return None
        value, offset = decoded
        values.append(value)
    return values, offset


def decode_level_ui_list(data: bytes, offset: int) -> dict[str, Any] | None:
    """Decode ``List<LevelUIData>`` through all six generated fields."""

    start = offset
    count_decoded = read_count(data, offset, max_count=100_000)
    if count_decoded is None:
        return None
    count, cursor = count_decoded
    if count == -1:
        return {"startOffset": start, "endOffset": cursor, "count": count, "value": None, "rows": []}
    rows: list[dict[str, Any]] = []
    for index in range(count):
        row_start = cursor
        if cursor >= len(data) or data[cursor] != 6:
            return None
        cursor += 1
        args_start = cursor
        args_count_decoded = read_count(data, cursor, max_count=100_000)
        if args_count_decoded is None:
            return None
        args_count, cursor = args_count_decoded
        args: list[str] = []
        for _ in range(max(0, args_count)):
            arg_decoded = read_string(data, cursor, max_length=4096)
            if arg_decoded is None:
                return None
            arg, cursor = arg_decoded
            args.append(arg)
        args_field = {
            "startOffset": args_start,
            "endOffset": cursor,
            "count": args_count,
            "value": None if args_count == -1 else args,
        }
        global_id_decoded = read_u64(data, cursor)
        if global_id_decoded is None:
            return None
        global_id, cursor = global_id_decoded
        vectors: dict[str, list[float]] = {}
        for name in ("position", "rotEuler", "scale"):
            decoded = _read_vector3(data, cursor)
            if decoded is None:
                return None
            vectors[name], cursor = decoded
        prefab_decoded = read_string(data, cursor, max_length=4096)
        if prefab_decoded is None:
            return None
        prefab, cursor = prefab_decoded
        rows.append({
            "indexInCollection": index,
            "startOffset": row_start,
            "endOffset": cursor,
            "memberCount": 6,
            "args": args_field,
            "globalId": str(global_id),
            **vectors,
            "uiPrefabPath": prefab,
        })
    return {
        "startOffset": start,
        "endOffset": cursor,
        "count": count,
        "rows": rows,
        "itemFieldOrder": ["args", "globalId", "position", "rotEuler", "scale", "uiPrefabPath"],
        "fieldOrderSource": "current generated LevelUIDataForMemoryPack wrapper",
    }
