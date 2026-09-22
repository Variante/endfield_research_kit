"""Exact generated-wrapper codecs for compact LevelData combat records."""

from __future__ import annotations

from typing import Any

from .memorypack import read_bool, read_count, read_f32, read_i32, read_string, read_u32, read_u64


def decode_level_enemy_group_list(data: bytes, offset: int) -> dict[str, Any] | None:
    """Decode ``List<LevelEnemyGroupData>`` and its slot/entity pointers."""

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
        if cursor >= len(data) or data[cursor] != 8:
            return None
        cursor += 1
        count_value_decoded = read_i32(data, cursor)
        if count_value_decoded is None:
            return None
        count_value, cursor = count_value_decoded
        group_id_decoded = read_i32(data, cursor)
        if group_id_decoded is None:
            return None
        group_id, cursor = group_id_decoded
        lock_decoded = read_bool(data, cursor)
        if lock_decoded is None:
            return None
        lock_leader_slot, cursor = lock_decoded
        patrol_decoded = read_u64(data, cursor)
        if patrol_decoded is None:
            return None
        patrol_id, cursor = patrol_decoded
        radius_decoded = read_f32(data, cursor)
        if radius_decoded is None:
            return None
        radius, cursor = radius_decoded

        slot_start = cursor
        slot_count_decoded = read_count(data, cursor, max_count=100_000)
        if slot_count_decoded is None:
            return None
        slot_count, cursor = slot_count_decoded
        slots: list[dict[str, Any]] = []
        for slot_index in range(max(0, slot_count)):
            slot_row_start = cursor
            if cursor >= len(data) or data[cursor] != 3:
                return None
            cursor += 1
            pointer_start = cursor
            if cursor >= len(data) or data[cursor] != 3:
                return None
            cursor += 1
            logic_id_decoded = read_u64(data, cursor)
            if logic_id_decoded is None:
                return None
            logic_id, cursor = logic_id_decoded
            slot_id_decoded = read_u32(data, cursor)
            if slot_id_decoded is None:
                return None
            slot_id, cursor = slot_id_decoded
            use_slot_decoded = read_bool(data, cursor)
            if use_slot_decoded is None:
                return None
            use_slot_id, cursor = use_slot_decoded
            leader_decoded = read_bool(data, cursor)
            if leader_decoded is None:
                return None
            leader, cursor = leader_decoded
            offset_values: list[float] = []
            for _ in range(2):
                component_decoded = read_f32(data, cursor)
                if component_decoded is None:
                    return None
                component, cursor = component_decoded
                offset_values.append(component)
            slots.append({
                "indexInCollection": slot_index,
                "startOffset": slot_row_start,
                "endOffset": cursor,
                "memberCount": 3,
                "entityPtr": {
                    "startOffset": pointer_start,
                    "memberCount": 3,
                    "logicId": str(logic_id),
                    "slotId": slot_id,
                    "useSlotId": use_slot_id,
                },
                "leader": leader,
                "offset": offset_values,
            })
        slot_end = cursor
        speed_decoded = read_f32(data, cursor)
        if speed_decoded is None:
            return None
        speed, cursor = speed_decoded
        template_decoded = read_string(data, cursor, max_length=4096)
        if template_decoded is None:
            return None
        template_id, cursor = template_decoded
        rows.append({
            "indexInCollection": index,
            "startOffset": row_start,
            "endOffset": cursor,
            "memberCount": 8,
            "count": count_value,
            "groupId": group_id,
            "lockLeaderSlot": lock_leader_slot,
            "patrolId": str(patrol_id),
            "radius": radius,
            "slot": {
                "startOffset": slot_start,
                "endOffset": slot_end,
                "count": slot_count,
                "value": None if slot_count == -1 else slots,
            },
            "speed": speed,
            "templateId": template_id,
        })
    return {
        "startOffset": start,
        "endOffset": cursor,
        "count": count,
        "rows": rows,
        "itemFieldOrder": [
            "count", "groupId", "lockLeaderSlot", "patrolId",
            "radius", "slot", "speed", "templateId",
        ],
        "fieldOrderSource": "current generated LevelEnemyGroupDataForMemoryPack wrapper",
    }
