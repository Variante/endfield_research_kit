"""Exact current-wrapper codec for authored LevelData character patrols."""

from __future__ import annotations

from typing import Any, Callable

from .memorypack import read_bool, read_count, read_f32, read_i32, read_string, read_u32, read_u64


def _fields(data: bytes, offset: int, readers: tuple[tuple[str, Callable], ...]):
    values: dict[str, Any] = {}
    for name, reader in readers:
        decoded = reader(data, offset)
        if decoded is None:
            return None
        values[name], offset = decoded
    return values, offset


def _vector3(data: bytes, offset: int):
    values = []
    for _ in range(3):
        decoded = read_f32(data, offset)
        if decoded is None:
            return None
        value, offset = decoded
        values.append(value)
    return values, offset


def _action(data: bytes, offset: int):
    start = offset
    if offset >= len(data) or data[offset] != 18:
        return None
    offset += 1
    decoded = _fields(data, offset, (
        ("actionEndTypeRaw", read_i32), ("angle", read_f32),
        ("animName", read_string), ("autoBlendOut", read_bool),
        ("blendInTime", read_f32), ("blendOutTime", read_f32),
        ("duration", read_f32), ("envTalkId", read_string),
        ("eventKey", read_string), ("fixedTimeOffset", read_f32),
        ("npcMontageTagId", read_u32), ("playRate", read_f32),
        ("radioId", read_string), ("repeatAnim", read_bool),
        ("rootMotion", read_bool), ("templateId", read_string),
        ("typeRaw", read_i32), ("waitTime", read_f32),
    ))
    if decoded is None:
        return None
    values, offset = decoded
    return {"startOffset": start, "endOffset": offset, "memberCount": 18,
            **values}, offset


def decode_character_patrol_list(data: bytes, offset: int) -> dict[str, Any] | None:
    """Decode current CharacterPatrolData owners, points, and fixed actions."""
    start = offset
    decoded = read_count(data, offset, max_count=100_000)
    if decoded is None:
        return None
    count, cursor = decoded
    rows: list[dict[str, Any] | None] = []
    point_total = action_total = 0
    for index in range(max(0, count)):
        row_start = cursor
        if cursor >= len(data):
            return None
        if data[cursor] == 0xFF:
            rows.append(None); cursor += 1; continue
        if data[cursor] != 3:
            return None
        cursor += 1
        loop = read_i32(data, cursor)
        if loop is None: return None
        loop_type, cursor = loop
        patrol = read_u64(data, cursor)
        if patrol is None: return None
        patrol_id, cursor = patrol
        points_start = cursor
        points_decoded = read_count(data, cursor, max_count=100_000)
        if points_decoded is None: return None
        point_count, cursor = points_decoded
        points: list[dict[str, Any] | None] = []
        for point_index in range(max(0, point_count)):
            point_start = cursor
            if cursor >= len(data): return None
            if data[cursor] == 0xFF:
                points.append(None); cursor += 1; continue
            if data[cursor] != 3: return None
            cursor += 1
            actions_start = cursor
            actions_decoded = read_count(data, cursor, max_count=100_000)
            if actions_decoded is None: return None
            action_count, cursor = actions_decoded
            actions: list[dict[str, Any] | None] = []
            for _ in range(max(0, action_count)):
                if cursor < len(data) and data[cursor] == 0xFF:
                    actions.append(None); cursor += 1; continue
                action = _action(data, cursor)
                if action is None: return None
                value, cursor = action
                actions.append(value); action_total += 1
            gait = read_i32(data, cursor)
            if gait is None: return None
            gait_raw, cursor = gait
            position = _vector3(data, cursor)
            if position is None: return None
            position_value, cursor = position
            points.append({"indexInCollection": point_index,
                           "startOffset": point_start, "endOffset": cursor,
                           "memberCount": 3,
                           "actions": {"startOffset": actions_start,
                                       "count": action_count,
                                       "value": None if action_count == -1 else actions},
                           "patrolGaitRaw": gait_raw,
                           "position": position_value})
            point_total += 1
        rows.append({"indexInCollection": index, "startOffset": row_start,
                     "endOffset": cursor, "memberCount": 3,
                     "charPatrolLoopTypeRaw": loop_type, "patrolId": patrol_id,
                     "points": {"startOffset": points_start,
                                "count": point_count,
                                "value": None if point_count == -1 else points}})
    return {"startOffset": start, "endOffset": cursor, "count": count,
            "value": None if count == -1 else rows,
            "pointCount": point_total, "actionCount": action_total,
            "itemFieldOrder": ["charPatrolLoopType", "patrolId", "points"],
            "fieldOrderSource": "current generated CharacterPatrolDataForMemoryPack wrapper"}
