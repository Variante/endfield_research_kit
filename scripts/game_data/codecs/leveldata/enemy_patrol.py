"""Exact current-wrapper codec for authored LevelData enemy patrols."""

from __future__ import annotations

from typing import Any, Callable

from .memorypack import read_bool, read_count, read_f32, read_i32, read_string, read_u64


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
    if offset >= len(data) or data[offset] != 13:
        return None
    offset += 1
    decoded = _fields(data, offset, (
        ("actionEndTypeRaw", read_i32),
        ("animName", read_string),
        ("duration", read_f32),
        ("eventKey", read_string),
        ("radioId", read_string),
        ("repeatAnim", read_bool),
        ("rootMotion", read_bool),
        ("rotationY", read_f32),
        ("templateDesc", read_string),
        ("templateId", read_string),
        ("templateName", read_string),
        ("typeRaw", read_i32),
        ("waitTime", read_f32),
    ))
    if decoded is None:
        return None
    values, offset = decoded
    return {"startOffset": start, "endOffset": offset, "memberCount": 13,
            **values}, offset


def decode_enemy_patrol_list(data: bytes, offset: int) -> dict[str, Any] | None:
    """Decode the current three-field enemy-patrol owner and point wrappers."""
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
            rows.append(None)
            cursor += 1
            continue
        if data[cursor] != 3:
            return None
        cursor += 1
        loop_decoded = read_i32(data, cursor)
        if loop_decoded is None:
            return None
        loop_type, cursor = loop_decoded
        patrol_decoded = read_u64(data, cursor)
        if patrol_decoded is None:
            return None
        patrol_id, cursor = patrol_decoded
        points_start = cursor
        points_decoded = read_count(data, cursor, max_count=100_000)
        if points_decoded is None:
            return None
        point_count, cursor = points_decoded
        points: list[dict[str, Any] | None] = []
        for point_index in range(max(0, point_count)):
            point_start = cursor
            if cursor >= len(data):
                return None
            if data[cursor] == 0xFF:
                points.append(None)
                cursor += 1
                continue
            if data[cursor] != 3:
                return None
            cursor += 1
            actions_start = cursor
            actions_decoded = read_count(data, cursor, max_count=100_000)
            if actions_decoded is None:
                return None
            action_count, cursor = actions_decoded
            actions: list[dict[str, Any] | None] = []
            for _ in range(max(0, action_count)):
                if cursor < len(data) and data[cursor] == 0xFF:
                    actions.append(None)
                    cursor += 1
                    continue
                action = _action(data, cursor)
                if action is None:
                    return None
                value, cursor = action
                actions.append(value)
                action_total += 1
            gait_decoded = read_i32(data, cursor)
            if gait_decoded is None:
                return None
            gait, cursor = gait_decoded
            position_decoded = _vector3(data, cursor)
            if position_decoded is None:
                return None
            position, cursor = position_decoded
            points.append({
                "indexInCollection": point_index,
                "startOffset": point_start,
                "endOffset": cursor,
                "memberCount": 3,
                "actions": {"startOffset": actions_start, "count": action_count,
                            "value": None if action_count == -1 else actions},
                "patrolGaitRaw": gait,
                "position": position,
            })
            point_total += 1
        rows.append({
            "indexInCollection": index,
            "startOffset": row_start,
            "endOffset": cursor,
            "memberCount": 3,
            "enemyPatrolLoopTypeRaw": loop_type,
            "patrolId": patrol_id,
            "points": {"startOffset": points_start, "count": point_count,
                       "value": None if point_count == -1 else points},
        })
    return {
        "startOffset": start,
        "endOffset": cursor,
        "count": count,
        "value": None if count == -1 else rows,
        "pointCount": point_total,
        "actionCount": action_total,
        "itemFieldOrder": ["enemyPatrolLoopType", "patrolId", "points"],
        "fieldOrderSource": "current generated EnemyPatrolDataForMemoryPack wrapper",
    }
