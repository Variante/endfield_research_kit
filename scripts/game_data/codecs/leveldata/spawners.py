"""Exact generated-wrapper codec for LevelData spawner instances."""

from __future__ import annotations

from typing import Any

from .memorypack import read_bool, read_count, read_f32, read_string, read_u64


def _read_vector3(data: bytes, offset: int) -> tuple[list[float], int] | None:
    values: list[float] = []
    for _ in range(3):
        decoded = read_f32(data, offset)
        if decoded is None:
            return None
        value, offset = decoded
        values.append(value)
    return values, offset


def decode_level_spawner_list(data: bytes, offset: int) -> dict[str, Any] | None:
    """Decode ``List<LevelSpawnerInstData>`` through all six fields.

    The item order is the current generated MemoryPack setter order. Unknown
    member counts and malformed scalar values stop without advancing the
    caller's cursor.
    """

    start = offset
    count_decoded = read_count(data, offset, max_count=100_000)
    if count_decoded is None:
        return None
    count, cursor = count_decoded
    if count == -1:
        return {
            "startOffset": start,
            "endOffset": cursor,
            "count": count,
            "value": None,
            "rows": [],
        }

    rows: list[dict[str, Any]] = []
    for index in range(count):
        row_start = cursor
        if cursor >= len(data):
            return None
        marker = data[cursor]
        cursor += 1
        if marker == 0xFF:
            rows.append({
                "indexInCollection": index,
                "startOffset": row_start,
                "endOffset": cursor,
                "value": None,
            })
            continue
        if marker != 6:
            return None

        belong_decoded = read_u64(data, cursor)
        if belong_decoded is None:
            return None
        belong_level_script_id, cursor = belong_decoded
        config_decoded = read_string(data, cursor, max_length=4096)
        if config_decoded is None:
            return None
        config_id, cursor = config_decoded
        event_decoded = read_bool(data, cursor)
        if event_decoded is None:
            return None
        enable_wave_die_event, cursor = event_decoded
        position_decoded = _read_vector3(data, cursor)
        if position_decoded is None:
            return None
        position, cursor = position_decoded
        rotation_decoded = _read_vector3(data, cursor)
        if rotation_decoded is None:
            return None
        rotation, cursor = rotation_decoded
        spawner_decoded = read_u64(data, cursor)
        if spawner_decoded is None:
            return None
        spawner_id, cursor = spawner_decoded

        rows.append({
            "indexInCollection": index,
            "startOffset": row_start,
            "endOffset": cursor,
            "memberCount": marker,
            "belongLevelScriptId": str(belong_level_script_id),
            "configId": config_id,
            "enableWaveDieEvent": enable_wave_die_event,
            "position": position,
            "rotation": rotation,
            "spawnerId": str(spawner_id),
        })

    return {
        "startOffset": start,
        "endOffset": cursor,
        "count": count,
        "rows": rows,
        "itemFieldOrder": [
            "belongLevelScriptId",
            "configId",
            "enableWaveDieEvent",
            "position",
            "rotation",
            "spawnerId",
        ],
        "fieldOrderSource": (
            "current generated LevelSpawnerInstDataForMemoryPack wrapper"
        ),
    }
