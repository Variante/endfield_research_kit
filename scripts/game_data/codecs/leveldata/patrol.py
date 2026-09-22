"""Exact current-wrapper codecs for authored LevelData NPC patrols."""

from __future__ import annotations

from typing import Any, Callable

from .memorypack import (
    read_bool,
    read_count,
    read_f32,
    read_f64,
    read_i32,
    read_string,
    read_u32,
)


PATROL_SUB_ACTION_TYPE_NAMES = {
    0: "None",
    1: "Wait",
    2: "TurnTo",
    3: "PlayAnimation",
    4: "Rest",
    5: "PlayEnvTalk",
    6: "PlayRadio",
    7: "EventToLevel",
    8: "ConfigMovement",
    9: "PlayRadioInRange",
    10: "PlayRadioAtTime",
    11: "PlayAudio",
    12: "EnemyPatrolEvent",
}


def _read_vector3(data: bytes, offset: int) -> tuple[list[float], int] | None:
    values: list[float] = []
    for _ in range(3):
        decoded = read_f32(data, offset)
        if decoded is None:
            return None
        value, offset = decoded
        values.append(value)
    return values, offset


def _read_fields(
    data: bytes,
    offset: int,
    readers: tuple[tuple[str, Callable[[bytes, int], tuple[Any, int] | None]], ...],
) -> tuple[dict[str, Any], int] | None:
    values: dict[str, Any] = {}
    for name, reader in readers:
        decoded = reader(data, offset)
        if decoded is None:
            return None
        values[name], offset = decoded
    return values, offset


def _read_blackboard_pairs(data: bytes, offset: int) -> tuple[dict[str, Any], int] | None:
    """Read ``List<Beyond.Blackboard.DataPair>`` in generated member order."""

    start = offset
    count_decoded = read_count(data, offset, max_count=256)
    if count_decoded is None:
        return None
    count, offset = count_decoded
    rows: list[dict[str, Any]] = []
    for index in range(max(0, count)):
        row_start = offset
        if offset >= len(data) or data[offset] != 4:
            return None
        offset += 1
        decoded = _read_fields(data, offset, (
            ("isDynamic", read_bool),
            ("key", read_string),
            ("valueDouble", read_f64),
            ("valueStr", read_string),
        ))
        if decoded is None:
            return None
        values, offset = decoded
        rows.append({
            "indexInCollection": index,
            "startOffset": row_start,
            "endOffset": offset,
            "memberCount": 4,
            **values,
        })
    return {
        "startOffset": start,
        "endOffset": offset,
        "count": count,
        "value": None if count == -1 else rows,
    }, offset


def _read_sub_action_data(data: bytes, offset: int) -> tuple[dict[str, Any] | None, int] | None:
    """Read the current two-route ``PatrolSubActionData`` MemoryPack union."""

    start = offset
    if offset >= len(data):
        return None
    tag = data[offset]
    offset += 1
    if tag == 0xFF:
        return None, offset
    if tag == 0:
        if offset >= len(data) or data[offset] != 3:
            return None
        offset += 1
        decoded = _read_fields(data, offset, (
            ("envTalkId", read_string),
            ("npcId", read_string),
            ("overrideNpc", read_bool),
        ))
        if decoded is None:
            return None
        values, offset = decoded
        return {
            "startOffset": start,
            "endOffset": offset,
            "unionTag": tag,
            "memberCount": 3,
            "typeName": "PatrolSubActionEnvTalkData",
            **values,
        }, offset
    if tag == 1:
        if offset >= len(data) or data[offset] != 1:
            return None
        offset += 1
        audio_id = read_u32(data, offset)
        if audio_id is None:
            return None
        audio_id_value, offset = audio_id
        return {
            "startOffset": start,
            "endOffset": offset,
            "unionTag": tag,
            "memberCount": 1,
            "typeName": "PatrolSubPlayAudioData",
            "audioEventId": audio_id_value,
        }, offset
    return None


def _read_patrol_sub_action(data: bytes, offset: int) -> tuple[dict[str, Any], int] | None:
    start = offset
    if offset >= len(data) or data[offset] != 26:
        return None
    offset += 1
    decoded = _read_fields(data, offset, (
        ("actionEndTypeRaw", read_i32),
        ("animKeyTagId", read_i32),
        ("animMaskTypeRaw", read_i32),
        ("animName", read_string),
        ("configMovementStyle", read_bool),
        ("configSnap", read_bool),
        ("duration", read_f32),
    ))
    if decoded is None:
        return None
    values, offset = decoded
    pairs = _read_blackboard_pairs(data, offset)
    if pairs is None:
        return None
    values["eventBBDataPairs"], offset = pairs
    decoded = _read_fields(data, offset, (
        ("eventKey", read_string),
        ("eventToLevelTypeRaw", read_i32),
        ("ignoreAnimDis", read_f32),
        ("movementStyleRaw", read_i32),
        ("npcPlayAnimationTimeEndForceToIdle", read_bool),
        ("overrideSpeed", read_bool),
        ("overrideSpeedValue", read_f32),
        ("radioId", read_string),
        ("radioWaitTime", read_f32),
        ("radius", read_f32),
        ("repeatAnim", read_bool),
        ("rootMotion", read_bool),
        ("rotationOffset", read_f32),
        ("rotationY", read_f32),
        ("snapToGroundRaw", read_i32),
    ))
    if decoded is None:
        return None
    trailing, offset = decoded
    values.update(trailing)
    sub_action_data = _read_sub_action_data(data, offset)
    if sub_action_data is None:
        return None
    values["subActionData"], offset = sub_action_data
    decoded = _read_fields(data, offset, (
        ("typeRaw", read_i32),
        ("waitTime", read_f32),
    ))
    if decoded is None:
        return None
    trailing, offset = decoded
    values.update(trailing)
    type_raw = values["typeRaw"]
    values["typeName"] = PATROL_SUB_ACTION_TYPE_NAMES.get(type_raw, "")
    return {
        "startOffset": start,
        "endOffset": offset,
        "memberCount": 26,
        **values,
    }, offset


def _read_vector3_list(data: bytes, offset: int) -> tuple[dict[str, Any], int] | None:
    start = offset
    decoded = read_count(data, offset, max_count=100_000)
    if decoded is None:
        return None
    count, offset = decoded
    rows: list[list[float]] = []
    for _ in range(max(0, count)):
        value = _read_vector3(data, offset)
        if value is None:
            return None
        point, offset = value
        rows.append(point)
    return {
        "startOffset": start,
        "endOffset": offset,
        "count": count,
        "value": None if count == -1 else rows,
    }, offset


def _read_patrol_action(data: bytes, offset: int) -> tuple[dict[str, Any], int] | None:
    start = offset
    if offset >= len(data) or data[offset] != 4:
        return None
    offset += 1
    action_type = read_i32(data, offset)
    if action_type is None:
        return None
    action_type_value, offset = action_type
    position = _read_vector3(data, offset)
    if position is None:
        return None
    position_value, offset = position
    subactions_start = offset
    subaction_count_decoded = read_count(data, offset, max_count=100_000)
    if subaction_count_decoded is None:
        return None
    subaction_count, offset = subaction_count_decoded
    subactions: list[dict[str, Any]] = []
    for _ in range(max(0, subaction_count)):
        decoded = _read_patrol_sub_action(data, offset)
        if decoded is None:
            return None
        value, offset = decoded
        subactions.append(value)
    subactions_end = offset
    subpositions = _read_vector3_list(data, offset)
    if subpositions is None:
        return None
    subpositions_value, offset = subpositions
    return {
        "startOffset": start,
        "endOffset": offset,
        "memberCount": 4,
        "actionTypeRaw": action_type_value,
        "position": position_value,
        "subActions": {
            "startOffset": subactions_start,
            "endOffset": subactions_end,
            "count": subaction_count,
            "value": None if subaction_count == -1 else subactions,
        },
        "subPositions": subpositions_value,
    }, offset


def decode_patrol_list(data: bytes, offset: int) -> dict[str, Any] | None:
    """Decode the generated ``List<PatrolData>`` used by LevelData."""

    start = offset
    decoded = read_count(data, offset, max_count=100_000)
    if decoded is None:
        return None
    count, cursor = decoded
    rows: list[dict[str, Any]] = []
    for index in range(max(0, count)):
        row_start = cursor
        if cursor >= len(data) or data[cursor] != 39:
            return None
        cursor += 1
        actions_start = cursor
        action_count_decoded = read_count(data, cursor, max_count=100_000)
        if action_count_decoded is None:
            return None
        action_count, cursor = action_count_decoded
        actions: list[dict[str, Any]] = []
        for _ in range(max(0, action_count)):
            action = _read_patrol_action(data, cursor)
            if action is None:
                return None
            action_value, cursor = action
            actions.append(action_value)
        actions_end = cursor
        values_decoded = _read_fields(data, cursor, (
            ("addBornPositionAsCheckpoint", read_bool),
            ("bornMoveStyleRaw", read_i32),
            ("bornOverrideSpeed", read_f32),
            ("bornPositionWaitDuration", read_f32),
            ("changePlayerMoveStyle", read_bool),
            ("coolDownBetweenWalkAndStop", read_f32),
            ("enableBornAction", read_bool),
            ("enableBornSpeedOverride", read_bool),
            ("forbidNpcInteract", read_bool),
            ("forcePlayerMoveStyleRaw", read_i32),
            ("id", read_i32),
            ("inLocalSpace", read_bool),
            ("isLimitPlayerActionWhenGaitLimit", read_bool),
            ("isStopDistance", read_bool),
            ("isUseCatmull", read_bool),
            ("limitPlayerActionTypeRaw", read_i32),
            ("loopRaw", read_i32),
            ("motionEnterDis", read_f32),
            ("motionTypeRaw", read_i32),
            ("moveStyleWithoutLeadRaw", read_i32),
            ("pauseActionWhenPatrolDisabled", read_bool),
            ("playerChangeLimitDelayTime", read_f32),
            ("runAheadRadius", read_f32),
            ("runBehindRadius", read_f32),
            ("snapRaw", read_i32),
            ("sprintAheadRadius", read_f32),
            ("sprintBehindRadius", read_f32),
            ("stop2WalkBufferTime", read_f32),
            ("stopWalkInplace", read_bool),
            ("turnCheck", read_bool),
            ("turnCheckAngle", read_f32),
            ("turnCheckDis", read_f32),
            ("turnCheckTime", read_f32),
            ("turnRadio", read_f32),
            ("usePatrolPointEnterGaitAsLimitGait", read_bool),
            ("useWorldOffset", read_bool),
            ("waitDistance", read_f32),
        ))
        if values_decoded is None:
            return None
        values, cursor = values_decoded
        world_offset = _read_vector3(data, cursor)
        if world_offset is None:
            return None
        world_offset_value, cursor = world_offset
        rows.append({
            "indexInCollection": index,
            "startOffset": row_start,
            "endOffset": cursor,
            "memberCount": 39,
            "actions": {
                "startOffset": actions_start,
                "endOffset": actions_end,
                "count": action_count,
                "value": None if action_count == -1 else actions,
            },
            **values,
            "worldOffset": world_offset_value,
        })
    return {
        "startOffset": start,
        "endOffset": cursor,
        "count": count,
        "value": None if count == -1 else rows,
        "rows": rows,
        "evidenceBoundary": (
            "exact current generated PatrolData member-39 and PatrolAction member-4 "
            "wrappers; nested PatrolSubActionData retains its maintained union gate"
        ),
        "fieldOrderSource": "current generated MemoryPack wrappers",
    }


def decode_npc_patrol_list(data: bytes, offset: int) -> dict[str, Any] | None:
    """Decode ``List<NpcPatrolData>`` including current subaction union routes."""

    start = offset
    count_decoded = read_count(data, offset, max_count=100_000)
    if count_decoded is None:
        return None
    count, cursor = count_decoded
    rows: list[dict[str, Any]] = []
    action_count_total = 0
    subtype_counts: dict[str, int] = {}
    for index in range(max(0, count)):
        row_start = cursor
        if cursor >= len(data) or data[cursor] != 10:
            return None
        cursor += 1
        decoded = _read_fields(data, cursor, (
            ("bornMoveStyleRaw", read_i32),
            ("bornOverrideSpeed", read_f32),
            ("enableBornAction", read_bool),
            ("enableBornSpeedOverride", read_bool),
            ("forbidNpcInteract", read_bool),
            ("leadConfigSoName", read_string),
            ("loopRaw", read_i32),
            ("patrolId", read_i32),
            ("pauseActionWhenPatrolDisabled", read_bool),
        ))
        if decoded is None:
            return None
        values, cursor = decoded
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
            if action_count_decoded is None:
                return None
            action_count, cursor = action_count_decoded
            actions: list[dict[str, Any]] = []
            for _ in range(max(0, action_count)):
                action = _read_patrol_sub_action(data, cursor)
                if action is None:
                    return None
                action_value, cursor = action
                actions.append(action_value)
                action_count_total += 1
                subtype = action_value["typeName"] or f"raw:{action_value['typeRaw']}"
                subtype_counts[subtype] = subtype_counts.get(subtype, 0) + 1
            actions_end = cursor
            enter_gait = read_i32(data, cursor)
            if enter_gait is None:
                return None
            enter_gait_value, cursor = enter_gait
            position = _read_vector3(data, cursor)
            if position is None:
                return None
            position_value, cursor = position
            points.append({
                "indexInCollection": point_index,
                "startOffset": point_start,
                "endOffset": cursor,
                "memberCount": 3,
                "actions": {
                    "startOffset": actions_start,
                    "endOffset": actions_end,
                    "count": action_count,
                    "value": None if action_count == -1 else actions,
                },
                "enterGaitRaw": enter_gait_value,
                "position": position_value,
            })
        rows.append({
            "indexInCollection": index,
            "startOffset": row_start,
            "endOffset": cursor,
            "memberCount": 10,
            **values,
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
        "value": None if count == -1 else rows,
        "rows": rows,
        "actionCount": action_count_total,
        "actionTypeCounts": subtype_counts,
        "itemFieldOrder": [
            "bornMoveStyle", "bornOverrideSpeed", "enableBornAction",
            "enableBornSpeedOverride", "forbidNpcInteract", "leadConfigSoName",
            "loop", "patrolId", "pauseActionWhenPatrolDisabled", "points",
        ],
        "pointFieldOrder": ["actions", "enterGait", "position"],
        "actionFieldOrder": [
            "actionEndType", "animKeyTag", "animMaskType", "animName",
            "configMovementStyle", "configSnap", "duration", "eventBBDataPairs",
            "eventKey", "eventToLevelType", "ignoreAnimDis", "movementStyle",
            "npcPlayAnimationTimeEndForceToIdle", "overrideSpeed",
            "overrideSpeedValue", "radioId", "radioWaitTime", "radius",
            "repeatAnim", "rootMotion", "rotationOffset", "rotationY",
            "snapToGround", "subActionData", "type", "waitTime",
        ],
        "evidenceBoundary": (
            "exact current generated wrappers; PatrolSubActionData accepts only null, "
            "tag-0 EnvTalk member-3, and tag-1 PlayAudio member-1 routes"
        ),
        "fieldOrderSource": "current generated MemoryPack wrappers",
    }
