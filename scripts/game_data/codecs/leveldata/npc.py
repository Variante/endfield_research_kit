"""Exact generated-wrapper codecs for LevelData NPC placement records."""

from __future__ import annotations

from typing import Any, Callable

from .memorypack import (
    read_bool,
    read_count,
    read_f32,
    read_i32,
    read_string,
    read_u32,
    read_u64,
)


def _read_vector(data: bytes, offset: int, size: int) -> tuple[list[float], int] | None:
    values: list[float] = []
    for _ in range(size):
        decoded = read_f32(data, offset)
        if decoded is None:
            return None
        value, offset = decoded
        values.append(value)
    return values, offset


def _read_list(
    data: bytes,
    offset: int,
    reader: Callable[[bytes, int], tuple[Any, int] | None],
) -> tuple[dict[str, Any], int] | None:
    start = offset
    count_decoded = read_count(data, offset, max_count=100_000)
    if count_decoded is None:
        return None
    count, offset = count_decoded
    values: list[Any] = []
    for _ in range(max(0, count)):
        decoded = reader(data, offset)
        if decoded is None:
            return None
        value, offset = decoded
        values.append(value)
    return {
        "startOffset": start,
        "endOffset": offset,
        "count": count,
        "value": None if count == -1 else values,
    }, offset


def _read_string_item(data: bytes, offset: int) -> tuple[str, int] | None:
    return read_string(data, offset, max_length=4096)


def _read_u64_string(data: bytes, offset: int) -> tuple[str, int] | None:
    decoded = read_u64(data, offset)
    if decoded is None:
        return None
    value, offset = decoded
    return str(value), offset


def decode_npc_attract_point_list(data: bytes, offset: int) -> dict[str, Any] | None:
    """Decode ``List<AttractPointInEditorData>`` in generated wrapper order."""

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
        if cursor >= len(data) or data[cursor] != 34:
            return None
        cursor += 1
        row: dict[str, Any] = {
            "indexInCollection": index,
            "startOffset": row_start,
            "memberCount": 34,
        }

        for name in ("actionEndTypeRaw", "actionTypeRaw"):
            decoded = read_i32(data, cursor)
            if decoded is None:
                return None
            row[name], cursor = decoded
        decoded_bool = read_bool(data, cursor)
        if decoded_bool is None:
            return None
        row["activeLookAt"], cursor = decoded_bool
        for name in (
            "animMaskTypeRaw", "animNameTagId", "animVirtualTagId",
            "attractObjectTypeRaw",
        ):
            decoded = read_i32(data, cursor)
            if decoded is None:
                return None
            row[name], cursor = decoded
        decoded_f32 = read_f32(data, cursor)
        if decoded_f32 is None:
            return None
        row["chairCheckDistance"], cursor = decoded_f32
        decoded_u64 = read_u64(data, cursor)
        if decoded_u64 is None:
            return None
        row["chairID"], cursor = str(decoded_u64[0]), decoded_u64[1]
        decoded_bool = read_bool(data, cursor)
        if decoded_bool is None:
            return None
        row["enableAtInit"], cursor = decoded_bool
        decoded_string = read_string(data, cursor, max_length=4096)
        if decoded_string is None:
            return None
        row["envTalkString"], cursor = decoded_string
        decoded_bool = read_bool(data, cursor)
        if decoded_bool is None:
            return None
        row["isPoiPoint"], cursor = decoded_bool
        decoded_i32 = read_i32(data, cursor)
        if decoded_i32 is None:
            return None
        row["level"], cursor = decoded_i32

        for name in ("linkedAttractPoints", "linkedWayPoints"):
            decoded_list = _read_list(data, cursor, _read_u64_string)
            if decoded_list is None:
                return None
            row[name], cursor = decoded_list

        decoded_u64 = read_u64(data, cursor)
        if decoded_u64 is None:
            return None
        row["mainId"], cursor = str(decoded_u64[0]), decoded_u64[1]
        for name in ("movementStyleTypeRaw", "moveToMethodRaw"):
            decoded_i32 = read_i32(data, cursor)
            if decoded_i32 is None:
                return None
            row[name], cursor = decoded_i32
        decoded_string = read_string(data, cursor, max_length=4096)
        if decoded_string is None:
            return None
        row["ownerRoomId"], cursor = decoded_string
        decoded_vector = _read_vector(data, cursor, 3)
        if decoded_vector is None:
            return None
        row["position"], cursor = decoded_vector
        decoded_vector = _read_vector(data, cursor, 4)
        if decoded_vector is None:
            return None
        row["rotation"], cursor = decoded_vector
        decoded_string = read_string(data, cursor, max_length=4096)
        if decoded_string is None:
            return None
        row["searchName"], cursor = decoded_string
        decoded_i32 = read_i32(data, cursor)
        if decoded_i32 is None:
            return None
        row["spaceshipBehaviorTypeRaw"], cursor = decoded_i32
        decoded_string = read_string(data, cursor, max_length=4096)
        if decoded_string is None:
            return None
        row["spaceshipDetailAnimType"], cursor = decoded_string
        decoded_i32 = read_i32(data, cursor)
        if decoded_i32 is None:
            return None
        row["spaceshipGeneralAnimTypeRaw"], cursor = decoded_i32
        decoded_list = _read_list(data, cursor, _read_string_item)
        if decoded_list is None:
            return None
        row["spaceshipTag"], cursor = decoded_list
        decoded_f32 = read_f32(data, cursor)
        if decoded_f32 is None:
            return None
        row["startDelay"], cursor = decoded_f32
        decoded_bool = read_bool(data, cursor)
        if decoded_bool is None:
            return None
        row["useEmoji"], cursor = decoded_bool
        decoded_u64 = read_u64(data, cursor)
        if decoded_u64 is None:
            return None
        row["uuid"], cursor = str(decoded_u64[0]), decoded_u64[1]
        decoded_f32 = read_f32(data, cursor)
        if decoded_f32 is None:
            return None
        row["waitTime"], cursor = decoded_f32
        decoded_i32 = read_i32(data, cursor)
        if decoded_i32 is None:
            return None
        row["wayLineHash"], cursor = decoded_i32
        decoded_u64 = read_u64(data, cursor)
        if decoded_u64 is None:
            return None
        row["wayPointEndUuid"], cursor = str(decoded_u64[0]), decoded_u64[1]
        decoded_f32 = read_f32(data, cursor)
        if decoded_f32 is None:
            return None
        row["wayPointRate"], cursor = decoded_f32
        decoded_u64 = read_u64(data, cursor)
        if decoded_u64 is None:
            return None
        row["wayPointStartUuid"], cursor = str(decoded_u64[0]), decoded_u64[1]
        row["endOffset"] = cursor
        rows.append(row)

    return {
        "startOffset": start,
        "endOffset": cursor,
        "count": count,
        "rows": rows,
        "itemFieldOrder": [
            "actionEndType", "actionType", "activeLookAt", "animMaskType",
            "animNameTag", "animVirtualTag", "attractObjectType",
            "chairCheckDistance", "chairID", "enableAtInit", "envTalkString",
            "isPoiPoint", "level", "linkedAttractPoints", "linkedWayPoints",
            "mainId", "movementStyleType", "moveToMethod", "ownerRoomId",
            "position", "rotation", "searchName", "spaceshipBehaviorType",
            "spaceshipDetailAnimType", "spaceshipGeneralAnimType", "spaceshipTag",
            "startDelay", "useEmoji", "uuid", "waitTime", "wayLineHash",
            "wayPointEndUuid", "wayPointRate", "wayPointStartUuid",
        ],
        "fieldOrderSource": "current generated AttractPointInEditorDataForMemoryPack wrapper",
    }


def _read_way_lane(data: bytes, offset: int) -> tuple[dict[str, Any], int] | None:
    start = offset
    if offset >= len(data) or data[offset] != 2:
        return None
    offset += 1
    lane_dir = _read_list(data, offset, read_u32)
    if lane_dir is None:
        return None
    lane_values, offset = lane_dir
    total_lane = read_i32(data, offset)
    if total_lane is None:
        return None
    total_lane_value, offset = total_lane
    return {
        "startOffset": start,
        "endOffset": offset,
        "memberCount": 2,
        "laneDir": lane_values,
        "totalLane": total_lane_value,
    }, offset


def decode_world_waypoint_list(data: bytes, offset: int) -> dict[str, Any] | None:
    """Decode ``List<WayPointInEditorData>`` and nested ``WayLane`` values."""

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
        if cursor >= len(data) or data[cursor] != 9:
            return None
        cursor += 1
        gate_lane_count = read_i32(data, cursor)
        if gate_lane_count is None:
            return None
        gate_lane_count_value, cursor = gate_lane_count
        is_gate = read_bool(data, cursor)
        if is_gate is None:
            return None
        is_gate_value, cursor = is_gate
        is_poi = read_bool(data, cursor)
        if is_poi is None:
            return None
        is_poi_value, cursor = is_poi
        level = read_i32(data, cursor)
        if level is None:
            return None
        level_value, cursor = level
        link_lane = _read_list(data, cursor, _read_way_lane)
        if link_lane is None:
            return None
        link_lane_value, cursor = link_lane
        link_to = _read_list(data, cursor, _read_u64_string)
        if link_to is None:
            return None
        link_to_value, cursor = link_to
        main_id = read_u64(data, cursor)
        if main_id is None:
            return None
        main_id_value, cursor = main_id
        position = _read_vector(data, cursor, 3)
        if position is None:
            return None
        position_value, cursor = position
        uuid = read_u64(data, cursor)
        if uuid is None:
            return None
        uuid_value, cursor = uuid
        rows.append({
            "indexInCollection": index,
            "startOffset": row_start,
            "endOffset": cursor,
            "memberCount": 9,
            "gateLaneCount": gate_lane_count_value,
            "isGate": is_gate_value,
            "isPoiPoint": is_poi_value,
            "level": level_value,
            "linkLane": link_lane_value,
            "linkTo": link_to_value,
            "mainId": str(main_id_value),
            "position": position_value,
            "uuid": str(uuid_value),
        })
    return {
        "startOffset": start,
        "endOffset": cursor,
        "count": count,
        "rows": rows,
        "itemFieldOrder": [
            "gateLaneCount", "isGate", "isPoiPoint", "level", "linkLane",
            "linkTo", "mainId", "position", "uuid",
        ],
        "fieldOrderSource": "current generated WayPointInEditorDataForMemoryPack wrapper",
    }


def decode_npc_patrol_list_empty_actions(data: bytes, offset: int) -> dict[str, Any] | None:
    """Decode NPC patrols whose point-action lists are null or empty.

    ``PatrolSubAction`` is polymorphic. A positive action count therefore fails
    closed at the collection boundary instead of guessing a union route.
    """

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
        if cursor >= len(data) or data[cursor] != 10:
            return None
        cursor += 1
        born_move = read_i32(data, cursor)
        if born_move is None:
            return None
        born_move_value, cursor = born_move
        born_speed = read_f32(data, cursor)
        if born_speed is None:
            return None
        born_speed_value, cursor = born_speed
        flags: dict[str, bool] = {}
        for name in ("enableBornAction", "enableBornSpeedOverride", "forbidNpcInteract"):
            decoded = read_bool(data, cursor)
            if decoded is None:
                return None
            flags[name], cursor = decoded
        lead_name = read_string(data, cursor, max_length=4096)
        if lead_name is None:
            return None
        lead_name_value, cursor = lead_name
        loop = read_i32(data, cursor)
        if loop is None:
            return None
        loop_value, cursor = loop
        patrol_id = read_i32(data, cursor)
        if patrol_id is None:
            return None
        patrol_id_value, cursor = patrol_id
        pause = read_bool(data, cursor)
        if pause is None:
            return None
        pause_value, cursor = pause
        points_start = cursor
        point_count_decoded = read_count(data, cursor, max_count=100_000)
        if point_count_decoded is None:
            return None
        point_count, cursor = point_count_decoded
        points: list[dict[str, Any]] = []
        for point_index in range(max(0, point_count)):
            point_start = cursor
            if cursor >= len(data) or data[cursor] != 3:
                return None
            cursor += 1
            actions_start = cursor
            action_count_decoded = read_count(data, cursor, max_count=100_000)
            if action_count_decoded is None or action_count_decoded[0] not in (-1, 0):
                return None
            action_count, cursor = action_count_decoded
            actions = {
                "startOffset": actions_start,
                "endOffset": cursor,
                "count": action_count,
                "value": None if action_count == -1 else [],
            }
            enter_gait = read_i32(data, cursor)
            if enter_gait is None:
                return None
            enter_gait_value, cursor = enter_gait
            position = _read_vector(data, cursor, 3)
            if position is None:
                return None
            position_value, cursor = position
            points.append({
                "indexInCollection": point_index,
                "startOffset": point_start,
                "endOffset": cursor,
                "memberCount": 3,
                "actions": actions,
                "enterGaitRaw": enter_gait_value,
                "position": position_value,
            })
        rows.append({
            "indexInCollection": index,
            "startOffset": row_start,
            "endOffset": cursor,
            "memberCount": 10,
            "bornMoveStyleRaw": born_move_value,
            "bornOverrideSpeed": born_speed_value,
            **flags,
            "leadConfigSoName": lead_name_value,
            "loopRaw": loop_value,
            "patrolId": patrol_id_value,
            "pauseActionWhenPatrolDisabled": pause_value,
            "points": {
                "startOffset": points_start,
                "endOffset": cursor,
                "count": point_count,
                "value": None if point_count == -1 else points,
            },
        })
    return {
        "startOffset": start,
        "endOffset": cursor,
        "count": count,
        "rows": rows,
        "itemFieldOrder": [
            "bornMoveStyle", "bornOverrideSpeed", "enableBornAction",
            "enableBornSpeedOverride", "forbidNpcInteract", "leadConfigSoName",
            "loop", "patrolId", "pauseActionWhenPatrolDisabled", "points",
        ],
        "pointFieldOrder": ["actions", "enterGait", "position"],
        "evidenceBoundary": "conditional: every point action list is null or empty",
        "fieldOrderSource": "current generated NpcPatrolDataForMemoryPack wrappers",
    }
