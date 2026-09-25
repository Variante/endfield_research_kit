"""Fail-closed readers for current Endfield ``SpawnerConfig`` MemoryPack data.

The leading ``enemyLibrary`` and final ``waveMap`` fields are decoded here.
The current generated formatters serialize ``SpawnerConfig`` as five fields,
``SpawnerEnemyLibraryItem`` as thirteen fields, ``SpawnerWaveData`` as eleven
fields, and ``SpawnerGroupData`` as twelve fields.  Action maps in the middle
of group rows remain opaque: the wave decoder accepts a file only when one
unique, complete wave/group parse reaches the physical end of the file.
"""
from __future__ import annotations

import math
import struct
from functools import lru_cache
from typing import Any


NULL_COUNT = 0xFFFFFFFF
SPAWNER_CONFIG_MEMBER_COUNT = 5
SPAWNER_ENEMY_LIBRARY_ITEM_MEMBER_COUNT = 13
SPAWNER_ENEMY_BORN_BEHAVIOR_MEMBER_COUNT = 18
SPAWNER_BUFF_ITEM_MEMBER_COUNT = 2
SPAWNER_BLACKBOARD_ITEM_MEMBER_COUNT = 4
SPAWNER_WAVE_MEMBER_COUNT = 11
SPAWNER_GROUP_MEMBER_COUNT = 12
MAX_ENEMY_COUNT = 10_000
MAX_BUFF_COUNT = 256
MAX_BLACKBOARD_COUNT = 256
MAX_WAVE_COUNT = 256
MAX_GROUP_COUNT = 1_024
MAX_STRING_BYTES = 256

SPAWNER_ENEMY_LIBRARY_SCHEMA_MAPPING_ID = (
    "gameassembly-0c557367-memorypack-spawner-enemy-library-item-v14"
)

SPAWNER_WAVE_SCHEMA_MAPPING_ID = (
    "gameassembly-2026-07-23-memorypack-spawner-wave-group-v2"
)
SPAWNER_WAVE_RUNTIME_MAPPING_ID = (
    "gameassembly-2026-07-23-cr-0x18b9217d0-spawner-wave-group-runtime-v2"
)


class SpawnerWaveDecodeError(ValueError):
    """Raised when a SpawnerConfig wave map is absent, changed, or ambiguous."""


class SpawnerEnemyLibraryDecodeError(ValueError):
    """Raised when the current SpawnerConfig enemy-library prefix changes."""


def _enemy_read_u32(data: bytes, offset: int, field: str) -> tuple[int, int]:
    if offset + 4 > len(data):
        raise SpawnerEnemyLibraryDecodeError(f"{field}: truncated uint32")
    return struct.unpack_from("<I", data, offset)[0], offset + 4


def _enemy_read_i32(data: bytes, offset: int, field: str) -> tuple[int, int]:
    if offset + 4 > len(data):
        raise SpawnerEnemyLibraryDecodeError(f"{field}: truncated int32")
    return struct.unpack_from("<i", data, offset)[0], offset + 4


def _enemy_read_f32(data: bytes, offset: int, field: str) -> tuple[float, int]:
    if offset + 4 > len(data):
        raise SpawnerEnemyLibraryDecodeError(f"{field}: truncated float32")
    value = struct.unpack_from("<f", data, offset)[0]
    if not math.isfinite(value):
        raise SpawnerEnemyLibraryDecodeError(f"{field}: non-finite float32")
    return value, offset + 4


def _enemy_read_bool(data: bytes, offset: int, field: str) -> tuple[bool, int]:
    if offset >= len(data) or data[offset] not in (0, 1):
        raise SpawnerEnemyLibraryDecodeError(f"{field}: invalid bool")
    return bool(data[offset]), offset + 1


def _enemy_read_optional_vector3(
    data: bytes, offset: int, field: str
) -> tuple[list[float] | None, int]:
    """Read the 16-byte nullable Vector3 value, including its ABI padding."""
    if offset + 16 > len(data):
        raise SpawnerEnemyLibraryDecodeError(f"{field}: truncated Optional<Vector3>")
    present, cursor = _enemy_read_bool(data, offset, f"{field}.hasValue")
    if data[cursor:cursor + 3] != b"\x00\x00\x00":
        raise SpawnerEnemyLibraryDecodeError(f"{field}: nonzero Optional<Vector3> padding")
    cursor += 3
    vector: list[float] = []
    for axis in range(3):
        value, cursor = _enemy_read_f32(data, cursor, f"{field}[{axis}]")
        vector.append(value)
    return (vector if present else None), cursor


def _enemy_read_string(
    data: bytes,
    offset: int,
    field: str,
    *,
    max_bytes: int = 512,
) -> tuple[str | None, int]:
    length, offset = _enemy_read_u32(data, offset, f"{field}.length")
    if length == NULL_COUNT:
        return None, offset
    if length > max_bytes or offset + length > len(data):
        raise SpawnerEnemyLibraryDecodeError(f"{field}: invalid string length {length}")
    try:
        value = data[offset:offset + length].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SpawnerEnemyLibraryDecodeError(f"{field}: invalid UTF-8") from exc
    if any(ord(character) < 0x20 for character in value):
        raise SpawnerEnemyLibraryDecodeError(f"{field}: control character")
    return value, offset + length


def _enemy_read_count(
    data: bytes,
    offset: int,
    field: str,
    max_count: int,
) -> tuple[int, int]:
    count, offset = _enemy_read_u32(data, offset, field)
    if count == NULL_COUNT:
        return 0, offset
    if count > max_count:
        raise SpawnerEnemyLibraryDecodeError(f"{field}: implausible count {count}")
    return count, offset


def _decode_spawner_buff_item(data: bytes, offset: int, index: int) -> tuple[dict[str, Any], int]:
    start = offset
    if offset >= len(data) or data[offset] != SPAWNER_BUFF_ITEM_MEMBER_COUNT:
        raise SpawnerEnemyLibraryDecodeError(f"bornBuffList[{index}]: member count changed")
    offset += 1
    blackboard_count, offset = _enemy_read_count(
        data,
        offset,
        f"bornBuffList[{index}].blackboards",
        MAX_BLACKBOARD_COUNT,
    )
    blackboards: list[dict[str, Any]] = []
    for blackboard_index in range(blackboard_count):
        if offset >= len(data) or data[offset] != SPAWNER_BLACKBOARD_ITEM_MEMBER_COUNT:
            raise SpawnerEnemyLibraryDecodeError(
                f"bornBuffList[{index}].blackboards[{blackboard_index}]: member count changed"
            )
        offset += 1
        key, offset = _enemy_read_string(
            data,
            offset,
            f"bornBuffList[{index}].blackboards[{blackboard_index}].key",
        )
        use_string, offset = _enemy_read_bool(
            data,
            offset,
            f"bornBuffList[{index}].blackboards[{blackboard_index}].useString",
        )
        value_float, offset = _enemy_read_f32(
            data,
            offset,
            f"bornBuffList[{index}].blackboards[{blackboard_index}].valueFloat",
        )
        value_string, offset = _enemy_read_string(
            data,
            offset,
            f"bornBuffList[{index}].blackboards[{blackboard_index}].valueString",
        )
        blackboards.append({
            "key": key or "",
            "useString": use_string,
            "valueFloat": value_float,
            "valueString": value_string or "",
        })
    buff_id, offset = _enemy_read_string(data, offset, f"bornBuffList[{index}].buffId")
    return {
        "sourceOffset": start,
        "blackboards": blackboards,
        "buffId": buff_id or "",
    }, offset


def decode_spawner_enemy_library(data: bytes) -> dict[str, Any]:
    """Decode the exact current-build ``SpawnerEnemyLibraryItem`` prefix.

    ``bornBehaviorData`` is nullable and every row in the current exported
    corpus uses the null marker.  A future non-null member-18 payload is
    rejected rather than skipped: its field names are known from metadata but
    its serialized value layout has no current authored fixture.
    """
    if not data or data[0] != SPAWNER_CONFIG_MEMBER_COUNT:
        raise SpawnerEnemyLibraryDecodeError("SpawnerConfig member count changed")
    config_id, offset = _enemy_read_string(data, 1, "configId")
    if not config_id:
        raise SpawnerEnemyLibraryDecodeError("missing configId")
    enemy_count, offset = _enemy_read_count(data, offset, "enemyLibrary", MAX_ENEMY_COUNT)
    enemy_library_offset = offset - 4
    enemies: list[dict[str, Any]] = []
    for index in range(enemy_count):
        start = offset
        if offset >= len(data) or data[offset] != SPAWNER_ENEMY_LIBRARY_ITEM_MEMBER_COUNT:
            raise SpawnerEnemyLibraryDecodeError(f"enemyLibrary[{index}]: member count changed")
        offset += 1

        if offset >= len(data):
            raise SpawnerEnemyLibraryDecodeError(f"enemyLibrary[{index}].bornBehaviorData: truncated")
        born_behavior_marker = data[offset]
        if born_behavior_marker != 0xFF:
            if born_behavior_marker == SPAWNER_ENEMY_BORN_BEHAVIOR_MEMBER_COUNT:
                detail = "non-null member-18 layout has no current authored fixture"
            else:
                detail = f"unexpected marker {born_behavior_marker}"
            raise SpawnerEnemyLibraryDecodeError(
                f"enemyLibrary[{index}].bornBehaviorData: {detail}"
            )
        offset += 1

        buff_count, offset = _enemy_read_count(
            data,
            offset,
            f"enemyLibrary[{index}].bornBuffList",
            MAX_BUFF_COUNT,
        )
        buffs: list[dict[str, Any]] = []
        for buff_index in range(buff_count):
            buff, offset = _decode_spawner_buff_item(data, offset, buff_index)
            buffs.append(buff)

        born_template_id, offset = _enemy_read_string(
            data, offset, f"enemyLibrary[{index}].bornTemplateId"
        )
        enemy_id, offset = _enemy_read_string(data, offset, f"enemyLibrary[{index}].enemyId")
        enemy_level, offset = _enemy_read_i32(data, offset, f"enemyLibrary[{index}].enemyLevel")
        force_to_battle, offset = _enemy_read_bool(
            data, offset, f"enemyLibrary[{index}].forceToBattle"
        )
        key, offset = _enemy_read_string(data, offset, f"enemyLibrary[{index}].key")
        override_ai_config, offset = _enemy_read_string(
            data, offset, f"enemyLibrary[{index}].overrideAIConfig"
        )
        patrol_gait, offset = _enemy_read_i32(data, offset, f"enemyLibrary[{index}].patrolGait")
        pre_warn_audio_event_key, offset = _enemy_read_string(
            data, offset, f"enemyLibrary[{index}].preWarnAudioEventKey"
        )
        pre_warn_effect_fixed_rotation, offset = _enemy_read_optional_vector3(
            data, offset, f"enemyLibrary[{index}].preWarnEffectFixedRotation"
        )
        pre_warn_effect_key, offset = _enemy_read_string(
            data, offset, f"enemyLibrary[{index}].preWarnEffectKey"
        )
        pre_warn_time, offset = _enemy_read_f32(
            data, offset, f"enemyLibrary[{index}].preWarnTime"
        )
        enemies.append({
            "index": index,
            "sourceOffset": start,
            "endOffset": offset,
            "bornBehaviorData": None,
            "bornBuffList": buffs,
            "bornTemplateId": born_template_id or "",
            "enemyId": enemy_id or "",
            "enemyLevel": enemy_level,
            "forceToBattle": force_to_battle,
            "key": key or "",
            "overrideAIConfig": override_ai_config or "",
            "patrolGait": patrol_gait,
            "preWarnAudioEventKey": pre_warn_audio_event_key or "",
            "preWarnEffectFixedRotation": pre_warn_effect_fixed_rotation,
            "preWarnEffectKey": pre_warn_effect_key or "",
            "preWarnTime": pre_warn_time,
        })
    return {
        "configId": config_id,
        "enemyLibraryOffset": enemy_library_offset,
        "enemyLibraryEndOffset": offset,
        "enemyLibraryCount": len(enemies),
        "enemyLibrary": enemies,
        "schemaMappingId": SPAWNER_ENEMY_LIBRARY_SCHEMA_MAPPING_ID,
        "schemaStatus": "exact-current-null-born-behavior",
    }


def _decode_patrol_sub_action(
    data: bytes,
    offset: int,
    field: str,
) -> tuple[dict[str, Any], int]:
    """Decode the authored member-26 ``PatrolSubAction`` profile.

    The current corpus has 97 rows.  Their blackboard-pair lists are empty and
    their polymorphic ``subActionData`` values are null; both boundaries stay
    fail-closed until an authored positive fixture exists.
    """

    start = offset
    if offset >= len(data) or data[offset] != 26:
        raise SpawnerEnemyLibraryDecodeError(f"{field}: PatrolSubAction member count changed")
    offset += 1
    values: dict[str, Any] = {}
    for name in ("actionEndType", "animKeyTag", "animMaskType"):
        values[name], offset = _enemy_read_i32(data, offset, f"{field}.{name}")
    values["animName"], offset = _enemy_read_string(data, offset, f"{field}.animName")
    for name in ("configMovementStyle", "configSnap"):
        values[name], offset = _enemy_read_bool(data, offset, f"{field}.{name}")
    values["duration"], offset = _enemy_read_f32(data, offset, f"{field}.duration")
    pair_count, offset = _enemy_read_count(
        data, offset, f"{field}.eventBBDataPairs", MAX_BLACKBOARD_COUNT
    )
    if pair_count:
        raise SpawnerEnemyLibraryDecodeError(
            f"{field}.eventBBDataPairs: positive list count {pair_count} has no current fixture"
        )
    values["eventBBDataPairs"] = []
    values["eventKey"], offset = _enemy_read_string(data, offset, f"{field}.eventKey")
    values["eventToLevelType"], offset = _enemy_read_i32(
        data, offset, f"{field}.eventToLevelType"
    )
    values["ignoreAnimDis"], offset = _enemy_read_f32(data, offset, f"{field}.ignoreAnimDis")
    values["movementStyle"], offset = _enemy_read_i32(data, offset, f"{field}.movementStyle")
    for name in ("npcPlayAnimationTimeEndForceToIdle", "overrideSpeed"):
        values[name], offset = _enemy_read_bool(data, offset, f"{field}.{name}")
    values["overrideSpeedValue"], offset = _enemy_read_f32(
        data, offset, f"{field}.overrideSpeedValue"
    )
    values["radioId"], offset = _enemy_read_string(data, offset, f"{field}.radioId")
    for name in ("radioWaitTime", "radius"):
        values[name], offset = _enemy_read_f32(data, offset, f"{field}.{name}")
    for name in ("repeatAnim", "rootMotion"):
        values[name], offset = _enemy_read_bool(data, offset, f"{field}.{name}")
    for name in ("rotationOffset", "rotationY"):
        values[name], offset = _enemy_read_f32(data, offset, f"{field}.{name}")
    values["snapToGround"], offset = _enemy_read_i32(data, offset, f"{field}.snapToGround")
    if offset >= len(data) or data[offset] != 0xFF:
        marker = data[offset] if offset < len(data) else None
        raise SpawnerEnemyLibraryDecodeError(
            f"{field}.subActionData: expected current null marker, got {marker}"
        )
    offset += 1
    values["subActionData"] = None
    values["type"], offset = _enemy_read_i32(data, offset, f"{field}.type")
    values["waitTime"], offset = _enemy_read_f32(data, offset, f"{field}.waitTime")
    return {"sourceOffset": start, "endOffset": offset, "memberCount": 26, **values}, offset


def _decode_patrol_action(
    data: bytes,
    offset: int,
    field: str,
) -> tuple[dict[str, Any], int]:
    start = offset
    if offset >= len(data) or data[offset] != 4:
        raise SpawnerEnemyLibraryDecodeError(f"{field}: PatrolAction member count changed")
    offset += 1
    action_type, offset = _enemy_read_i32(data, offset, f"{field}.actionType")
    position: list[float] = []
    for axis in range(3):
        value, offset = _enemy_read_f32(data, offset, f"{field}.position[{axis}]")
        position.append(value)
    sub_action_count, offset = _enemy_read_count(
        data, offset, f"{field}.subActions", MAX_GROUP_COUNT
    )
    sub_actions: list[dict[str, Any]] = []
    for index in range(sub_action_count):
        row, offset = _decode_patrol_sub_action(data, offset, f"{field}.subActions[{index}]")
        sub_actions.append(row)
    sub_position_count, offset = _enemy_read_count(
        data, offset, f"{field}.subPositions", MAX_GROUP_COUNT
    )
    sub_positions: list[list[float]] = []
    for index in range(sub_position_count):
        vector: list[float] = []
        for axis in range(3):
            value, offset = _enemy_read_f32(
                data, offset, f"{field}.subPositions[{index}][{axis}]"
            )
            vector.append(value)
        sub_positions.append(vector)
    return {
        "sourceOffset": start,
        "endOffset": offset,
        "memberCount": 4,
        "actionType": action_type,
        "position": position,
        "subActions": sub_actions,
        "subPositions": sub_positions,
    }, offset


def _decode_patrol_data(
    data: bytes,
    offset: int,
    field: str,
) -> tuple[dict[str, Any], int]:
    """Decode the generated 39-member patrol profile and its authored actions."""

    start = offset
    if offset >= len(data) or data[offset] != 39:
        raise SpawnerEnemyLibraryDecodeError(f"{field}: PatrolData member count changed")
    offset += 1
    raw_action_count, offset = _enemy_read_u32(data, offset, f"{field}.actions")
    action_count = 0 if raw_action_count == NULL_COUNT else raw_action_count
    if action_count > MAX_GROUP_COUNT:
        raise SpawnerEnemyLibraryDecodeError(
            f"{field}.actions: implausible count {action_count}"
        )
    actions: list[dict[str, Any]] = []
    for index in range(action_count):
        action, offset = _decode_patrol_action(data, offset, f"{field}.actions[{index}]")
        actions.append(action)
    values: dict[str, Any] = {
        "actions": None if raw_action_count == NULL_COUNT else actions,
    }
    readers = (
        ("addBornPositionAsCheckpoint", _enemy_read_bool),
        ("bornMoveStyle", _enemy_read_i32),
        ("bornOverrideSpeed", _enemy_read_f32),
        ("bornPositionWaitDuration", _enemy_read_f32),
        ("changePlayerMoveStyle", _enemy_read_bool),
        ("coolDownBetweenWalkAndStop", _enemy_read_f32),
        ("enableBornAction", _enemy_read_bool),
        ("enableBornSpeedOverride", _enemy_read_bool),
        ("forbidNpcInteract", _enemy_read_bool),
        ("forcePlayerMoveStyle", _enemy_read_i32),
        ("id", _enemy_read_i32),
        ("inLocalSpace", _enemy_read_bool),
        ("isLimitPlayerActionWhenGaitLimit", _enemy_read_bool),
        ("isStopDistance", _enemy_read_bool),
        ("isUseCatmull", _enemy_read_bool),
        ("limitPlayerActionType", _enemy_read_i32),
        ("loop", _enemy_read_i32),
        ("motionEnterDis", _enemy_read_f32),
        ("motionType", _enemy_read_i32),
        ("moveStyleWithoutLead", _enemy_read_i32),
        ("pauseActionWhenPatrolDisabled", _enemy_read_bool),
        ("playerChangeLimitDelayTime", _enemy_read_f32),
        ("runAheadRadius", _enemy_read_f32),
        ("runBehindRadius", _enemy_read_f32),
        ("snap", _enemy_read_i32),
        ("sprintAheadRadius", _enemy_read_f32),
        ("sprintBehindRadius", _enemy_read_f32),
        ("stop2WalkBufferTime", _enemy_read_f32),
        ("stopWalkInplace", _enemy_read_bool),
        ("turnCheck", _enemy_read_bool),
        ("turnCheckAngle", _enemy_read_f32),
        ("turnCheckDis", _enemy_read_f32),
        ("turnCheckTime", _enemy_read_f32),
        ("turnRadio", _enemy_read_f32),
        ("usePatrolPointEnterGaitAsLimitGait", _enemy_read_bool),
        ("useWorldOffset", _enemy_read_bool),
        ("waitDistance", _enemy_read_f32),
    )
    for name, reader in readers:
        values[name], offset = reader(data, offset, f"{field}.{name}")
    world_offset: list[float] = []
    for axis in range(3):
        value, offset = _enemy_read_f32(data, offset, f"{field}.worldOffset[{axis}]")
        world_offset.append(value)
    values["worldOffset"] = world_offset
    return {
        "sourceOffset": start,
        "endOffset": offset,
        "memberCount": 39,
        **values,
    }, offset


def decode_spawner_named_prefix(data: bytes) -> dict[str, Any]:
    """Decode configId, enemyLibrary, routeMap and settings at one cursor.

    Route patrols are accepted only for the current profile whose polymorphic
    action list is null or empty. The returned ``waveMapOffset`` is therefore
    an exact generated-order cursor, not a byte-pattern candidate.
    """

    enemy_prefix = decode_spawner_enemy_library(data)
    offset = int(enemy_prefix["enemyLibraryEndOffset"])
    raw_route_count, offset = _enemy_read_u32(data, offset, "routeMap.count")
    route_count = 0 if raw_route_count == NULL_COUNT else raw_route_count
    if route_count > MAX_GROUP_COUNT:
        raise SpawnerEnemyLibraryDecodeError(f"routeMap: implausible count {route_count}")
    routes: list[dict[str, Any]] = []
    for index in range(route_count):
        entry_start = offset
        map_key, offset = _enemy_read_i32(data, offset, f"routeMap[{index}].key")
        if offset >= len(data) or data[offset] != 2:
            raise SpawnerEnemyLibraryDecodeError(
                f"routeMap[{index}]: SpawnerRouteData member count changed"
            )
        offset += 1
        patrol, offset = _decode_patrol_data(
            data, offset, f"routeMap[{index}].patrolData"
        )
        route_id, offset = _enemy_read_i32(data, offset, f"routeMap[{index}].routeId")
        routes.append({
            "sourceOffset": entry_start,
            "endOffset": offset,
            "mapKey": map_key,
            "patrolData": patrol,
            "routeId": route_id,
        })

    settings_start = offset
    if offset >= len(data) or data[offset] != 6:
        raise SpawnerEnemyLibraryDecodeError("settings: SpawnerSettings member count changed")
    offset += 1
    settings: dict[str, Any] = {"sourceOffset": settings_start, "memberCount": 6}
    for name in (
        "autoComplete", "enemyLevelUseLevelGrade", "forbidDrop", "noNavmeshMove",
    ):
        settings[name], offset = _enemy_read_bool(data, offset, f"settings.{name}")
    raw_effect_count, offset = _enemy_read_u32(data, offset, "settings.preloadEffectKeyList")
    effect_count = 0 if raw_effect_count == NULL_COUNT else raw_effect_count
    if effect_count > MAX_BUFF_COUNT:
        raise SpawnerEnemyLibraryDecodeError(
            f"settings.preloadEffectKeyList: implausible count {effect_count}"
        )
    effects: list[str] = []
    for index in range(effect_count):
        value, offset = _enemy_read_string(
            data, offset, f"settings.preloadEffectKeyList[{index}]", max_bytes=4096
        )
        effects.append(value or "")
    settings["preloadEffectKeyList"] = (
        None if raw_effect_count == NULL_COUNT else effects
    )
    settings["stopExploreMusic"], offset = _enemy_read_bool(
        data, offset, "settings.stopExploreMusic"
    )
    settings["endOffset"] = offset
    return {
        **enemy_prefix,
        "routeMapOffset": enemy_prefix["enemyLibraryEndOffset"],
        "routeMapCount": route_count,
        "routeMap": routes,
        "settings": settings,
        "waveMapOffset": offset,
        "schemaStatus": "exact-prefix-through-settings-current-route-actions",
    }


def _read_string(data: bytes, offset: int) -> tuple[str | None, int]:
    if offset + 4 > len(data):
        raise SpawnerWaveDecodeError("truncated string length")
    length = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    if length == NULL_COUNT:
        return None, offset
    if length > MAX_STRING_BYTES or offset + length > len(data):
        raise SpawnerWaveDecodeError("invalid string length")
    try:
        value = data[offset:offset + length].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SpawnerWaveDecodeError("invalid UTF-8 string") from exc
    if any(ord(character) < 0x20 for character in value):
        raise SpawnerWaveDecodeError("control character in string")
    return value, offset + length


def _read_wave_tail(data: bytes, offset: int) -> tuple[dict[str, Any], int]:
    """Read fields after the opaque ``groupMap`` in one SpawnerWaveData row."""
    start = offset
    if offset + 11 > len(data):
        raise SpawnerWaveDecodeError("truncated wave tail")
    flags = data[offset:offset + 3]
    if any(value not in (0, 1) for value in flags):
        raise SpawnerWaveDecodeError("invalid wave bool")
    has_deadline, is_hidden, repeatable = (bool(value) for value in flags)
    offset += 3
    timestamp = struct.unpack_from("<f", data, offset)[0]
    offset += 4
    wave_id = struct.unpack_from("<i", data, offset)[0]
    offset += 4
    wave_key, offset = _read_string(data, offset)
    if offset + 8 > len(data):
        raise SpawnerWaveDecodeError("truncated wave mode")
    wave_mode, kill_count = struct.unpack_from("<ii", data, offset)
    offset += 8
    target_key, offset = _read_string(data, offset)

    if (
        not math.isfinite(timestamp)
        or not -100_000.0 <= timestamp <= 10_000_000.0
        or not 0 <= wave_id <= 1_000_000
        or not wave_key
        or wave_mode not in (0, 1, 2)
        or not 0 <= kill_count <= 1_000_000
    ):
        raise SpawnerWaveDecodeError("implausible wave tail")
    return {
        "tailOffset": start,
        "hasDeadlineBegin": has_deadline,
        "isHidden": is_hidden,
        "repeatable": repeatable,
        "timestamp": timestamp,
        "waveId": wave_id,
        "waveKey": wave_key,
        "waveMode": wave_mode,
        "waveModeKillCount": kill_count,
        "waveModeTargetKey": target_key or "",
    }, offset


def _read_group_tail(data: bytes, offset: int) -> tuple[dict[str, Any], int]:
    """Read fields after the opaque ``actionMap`` in one SpawnerGroupData row."""
    start = offset
    if offset + 12 > len(data):
        raise SpawnerWaveDecodeError("truncated group tail")
    deadline_begin_delta_time = struct.unpack_from("<f", data, offset)[0]
    backup_count, group_id = struct.unpack_from("<ii", data, offset + 4)
    offset += 12
    group_key, offset = _read_string(data, offset)
    if offset + 12 > len(data):
        raise SpawnerWaveDecodeError("truncated group mode")
    max_count, group_mode, kill_count = struct.unpack_from("<iii", data, offset)
    offset += 12
    target_key, offset = _read_string(data, offset)
    if offset + 6 > len(data):
        raise SpawnerWaveDecodeError("truncated group flags")
    flags = data[offset:offset + 2]
    if any(value not in (0, 1) for value in flags):
        raise SpawnerWaveDecodeError("invalid group bool")
    has_deadline, limit_max_count = (bool(value) for value in flags)
    timestamp = struct.unpack_from("<f", data, offset + 2)[0]
    offset += 6

    if (
        not math.isfinite(deadline_begin_delta_time)
        or not -100_000.0 <= deadline_begin_delta_time <= 10_000_000.0
        or not 0 <= backup_count <= 1_000_000
        or not 0 <= group_id <= 1_000_000
        or max_count < -1
        or max_count > 1_000_000
        or group_mode not in (0, 1, 2)
        or not 0 <= kill_count <= 1_000_000
        or not math.isfinite(timestamp)
        or not -100_000.0 <= timestamp <= 10_000_000.0
    ):
        raise SpawnerWaveDecodeError("implausible group tail")
    return {
        "tailOffset": start,
        "deadlineBeginDeltaTime": deadline_begin_delta_time,
        "groupBackUpCount": backup_count,
        "groupId": group_id,
        "groupKey": group_key or "",
        "groupMaxCount": max_count,
        "groupMode": group_mode,
        "groupModeKillCount": kill_count,
        "groupModeTargetKey": target_key or "",
        "hasDeadlineBegin": has_deadline,
        "limitGroupMaxCount": limit_max_count,
        "timestamp": timestamp,
    }, offset


def _decode_group_map(
    data: bytes,
    offset: int,
    end_offset: int,
) -> tuple[dict[str, Any], ...]:
    """Decode one group map whose exact end is the containing wave tail."""
    if offset + 4 > end_offset:
        raise SpawnerWaveDecodeError("truncated groupMap count")
    group_count = struct.unpack_from("<I", data, offset)[0]
    if group_count > MAX_GROUP_COUNT:
        raise SpawnerWaveDecodeError("implausible groupMap count")

    tail_candidates: list[tuple[dict[str, Any], int]] = []
    for candidate_offset in range(offset + 4, max(offset + 4, end_offset - 5)):
        try:
            row, row_end = _read_group_tail(data, candidate_offset)
        except SpawnerWaveDecodeError:
            continue
        if row_end > end_offset:
            continue
        tail_candidates.append((row, row_end))

    @lru_cache(maxsize=None)
    def parse_entries(
        entry_offset: int,
        remaining: int,
    ) -> tuple[tuple[dict[str, Any], ...], ...]:
        if remaining == 0:
            return ((),) if entry_offset == end_offset else ()
        if entry_offset + 5 > end_offset:
            return ()
        map_key = struct.unpack_from("<i", data, entry_offset)[0]
        value_start = entry_offset + 4
        if (
            not 0 <= map_key <= 1_000_000
            or data[value_start] != SPAWNER_GROUP_MEMBER_COUNT
        ):
            return ()

        solutions: list[tuple[dict[str, Any], ...]] = []
        for candidate, next_offset in tail_candidates:
            if candidate["tailOffset"] <= value_start + 4:
                continue
            row = {
                **candidate,
                "mapKey": map_key,
                "entryOffset": entry_offset,
                "valueOffset": value_start,
            }
            for suffix in parse_entries(next_offset, remaining - 1):
                solutions.append((row, *suffix))
                if len(solutions) > 1:
                    return tuple(solutions)
        return tuple(solutions)

    solutions = parse_entries(offset + 4, group_count)
    if len(solutions) != 1:
        raise SpawnerWaveDecodeError("no unique complete groupMap")
    rows = solutions[0]
    if [row["mapKey"] for row in rows] != list(range(1, group_count + 1)):
        raise SpawnerWaveDecodeError("changed groupMap index keys")
    named_keys = [row["groupKey"] for row in rows if row["groupKey"]]
    if len(set(named_keys)) != len(named_keys):
        raise SpawnerWaveDecodeError("duplicate groupKey")
    return rows


def decode_spawner_wave_map(
    data: bytes,
    *,
    wave_map_offset: int | None = None,
) -> dict[str, Any]:
    """Decode one uniquely delimited current-build SpawnerConfig wave map.

    The MemoryPack dictionary key and the serialized ``waveKey`` are separate
    fields.  Current authored rows commonly use keys such as ``1``/``2`` with
    values such as ``w1``/``w2``.  Both are retained, and a frame is accepted
    only when exactly one complete wave/group parse reaches physical EOF.
    """
    if not data or data[0] != SPAWNER_CONFIG_MEMBER_COUNT:
        raise SpawnerWaveDecodeError("SpawnerConfig member count changed")
    config_id, config_id_end = _read_string(data, 1)
    if not config_id:
        raise SpawnerWaveDecodeError("missing configId")

    tail_candidates: list[tuple[dict[str, Any], int]] = []
    for offset in range(config_id_end, max(config_id_end, len(data) - 10)):
        try:
            row, end = _read_wave_tail(data, offset)
        except SpawnerWaveDecodeError:
            continue
        tail_candidates.append((row, end))

    @lru_cache(maxsize=None)
    def parse_entries(offset: int, remaining: int) -> tuple[tuple[dict[str, Any], ...], ...]:
        if remaining == 0:
            return ((),) if offset == len(data) else ()
        if offset + 5 > len(data):
            return ()
        map_key = struct.unpack_from("<i", data, offset)[0]
        value_start = offset + 4
        if (
            not 0 <= map_key <= 1_000_000
            or data[value_start] != SPAWNER_WAVE_MEMBER_COUNT
        ):
            return ()

        solutions: list[tuple[dict[str, Any], ...]] = []
        for candidate, next_offset in tail_candidates:
            if candidate["tailOffset"] <= value_start + 5:
                continue
            try:
                groups = _decode_group_map(
                    data,
                    value_start + 5,
                    candidate["tailOffset"],
                )
            except SpawnerWaveDecodeError:
                continue
            row = {
                **candidate,
                "mapKey": map_key,
                "entryOffset": offset,
                "valueOffset": value_start,
                "groupMapOffset": value_start + 5,
                "groupCount": len(groups),
                "groups": list(groups),
            }
            if remaining == 1:
                if next_offset == len(data):
                    solutions.append((row,))
                continue
            for suffix in parse_entries(next_offset, remaining - 1):
                solutions.append((row, *suffix))
                if len(solutions) > 1:
                    return tuple(solutions)
        return tuple(solutions)

    if wave_map_offset is not None and not config_id_end <= wave_map_offset <= len(data) - 4:
        raise SpawnerWaveDecodeError("waveMap exact cursor is outside the payload")
    candidate_offsets = (
        (wave_map_offset,)
        if wave_map_offset is not None
        else range(config_id_end, max(config_id_end, len(data) - 8))
    )
    solutions: list[tuple[int, tuple[dict[str, Any], ...]]] = []
    for offset in candidate_offsets:
        assert offset is not None
        wave_count = struct.unpack_from("<I", data, offset)[0]
        if not 1 <= wave_count <= MAX_WAVE_COUNT:
            continue
        rows = parse_entries(offset + 4, wave_count)
        for row_set in rows:
            solutions.append((offset, row_set))
            if len(solutions) > 1:
                raise SpawnerWaveDecodeError("ambiguous complete waveMap")

    if len(solutions) != 1:
        raise SpawnerWaveDecodeError("no unique complete waveMap")
    wave_map_offset, rows = solutions[0]
    if len({row["mapKey"] for row in rows}) != len(rows):
        raise SpawnerWaveDecodeError("duplicate wave map key")
    if len({row["waveKey"] for row in rows}) != len(rows):
        raise SpawnerWaveDecodeError("duplicate waveKey")
    return {
        "configId": config_id,
        "waveMapOffset": wave_map_offset,
        "waveCount": len(rows),
        "waves": list(rows),
        "schemaMappingId": SPAWNER_WAVE_SCHEMA_MAPPING_ID,
        "runtimeMappingId": SPAWNER_WAVE_RUNTIME_MAPPING_ID,
        "waveMapOffsetBoundary": "exact" if wave_map_offset is not None else "searched-unique",
    }


def _exact_f32(data: bytes, offset: int, field: str) -> tuple[float, int]:
    if offset + 4 > len(data):
        raise SpawnerWaveDecodeError(f"{field}: truncated float32")
    value = struct.unpack_from("<f", data, offset)[0]
    if not math.isfinite(value):
        raise SpawnerWaveDecodeError(f"{field}: non-finite float32")
    return value, offset + 4


def _exact_i32(data: bytes, offset: int, field: str) -> tuple[int, int]:
    if offset + 4 > len(data):
        raise SpawnerWaveDecodeError(f"{field}: truncated int32")
    return struct.unpack_from("<i", data, offset)[0], offset + 4


def _exact_u32(data: bytes, offset: int, field: str) -> tuple[int, int]:
    if offset + 4 > len(data):
        raise SpawnerWaveDecodeError(f"{field}: truncated uint32")
    return struct.unpack_from("<I", data, offset)[0], offset + 4


def _exact_bool(data: bytes, offset: int, field: str) -> tuple[bool, int]:
    if offset >= len(data) or data[offset] not in (0, 1):
        raise SpawnerWaveDecodeError(f"{field}: invalid bool")
    return bool(data[offset]), offset + 1


def _exact_vector3(data: bytes, offset: int, field: str) -> tuple[list[float], int]:
    values: list[float] = []
    for axis in range(3):
        value, offset = _exact_f32(data, offset, f"{field}[{axis}]")
        values.append(value)
    return values, offset


def _decode_current_spawner_action(
    data: bytes,
    offset: int,
    field: str,
) -> tuple[dict[str, Any], int]:
    """Decode current union tags observed in authenticated SpawnerConfig rows."""

    start = offset
    if offset >= len(data):
        raise SpawnerWaveDecodeError(f"{field}: truncated union tag")
    tag = data[offset]
    offset += 1
    if tag == 5:
        if offset >= len(data) or data[offset] != 12:
            raise SpawnerWaveDecodeError(f"{field}: tag 5 member count changed")
        offset += 1
        action_id, offset = _exact_i32(data, offset, f"{field}.actionId")
        timestamp, offset = _exact_f32(data, offset, f"{field}.timestamp")
        face_main, offset = _exact_bool(data, offset, f"{field}.faceMainCharacter")
        library_key, offset = _read_string(data, offset)
        position, offset = _exact_vector3(data, offset, f"{field}.position")
        random_end, offset = _exact_f32(data, offset, f"{field}.randomizeEndPointRadius")
        random_radius, offset = _exact_f32(data, offset, f"{field}.randomizeRadius")
        rotation, offset = _exact_vector3(data, offset, f"{field}.rotation")
        route_id, offset = _exact_i32(data, offset, f"{field}.routeId")
        spawn_count, offset = _exact_i32(data, offset, f"{field}.spawnCount")
        spawn_interval, offset = _exact_f32(data, offset, f"{field}.spawnInterval")
        start_invalid, offset = _exact_bool(data, offset, f"{field}.startPointInvalid")
        return {
            "sourceOffset": start,
            "endOffset": offset,
            "unionTag": tag,
            "memberCount": 12,
            "concreteType": "SpawnerActions.SpawnMonsterFromTemplateV2",
            "actionId": action_id,
            "timestamp": timestamp,
            "faceMainCharacter": face_main,
            "libraryKey": library_key or "",
            "position": position,
            "randomizeEndPointRadius": random_end,
            "randomizeRadius": random_radius,
            "rotation": rotation,
            "routeId": route_id,
            "spawnCount": spawn_count,
            "spawnInterval": spawn_interval,
            "startPointInvalid": start_invalid,
        }, offset
    if tag == 0:
        if offset >= len(data) or data[offset] != 3:
            raise SpawnerWaveDecodeError(f"{field}: tag 0 member count changed")
        offset += 1
        action_id, offset = _exact_i32(data, offset, f"{field}.actionId")
        timestamp, offset = _exact_f32(data, offset, f"{field}.timestamp")
        string_value, offset = _read_string(data, offset)
        return {
            "sourceOffset": start,
            "endOffset": offset,
            "unionTag": tag,
            "memberCount": 3,
            "concreteType": "SpawnerActions.Pause",
            "actionId": action_id,
            "timestamp": timestamp,
            "pauseKey": string_value,
        }, offset
    if tag == 1:
        if offset >= len(data) or data[offset] != 3:
            raise SpawnerWaveDecodeError(f"{field}: tag 1 member count changed")
        offset += 1
        action_id, offset = _exact_i32(data, offset, f"{field}.actionId")
        timestamp, offset = _exact_f32(data, offset, f"{field}.timestamp")
        audio_id, offset = _read_string(data, offset)
        return {
            "sourceOffset": start,
            "endOffset": offset,
            "unionTag": tag,
            "memberCount": 3,
            "concreteType": "SpawnerActions.PlayAudio",
            "actionId": action_id,
            "timestamp": timestamp,
            "audioId": audio_id or "",
        }, offset
    if tag == 2:
        if offset >= len(data) or data[offset] != 7:
            raise SpawnerWaveDecodeError(f"{field}: tag 2 member count changed")
        offset += 1
        action_id, offset = _exact_i32(data, offset, f"{field}.actionId")
        timestamp, offset = _exact_f32(data, offset, f"{field}.timestamp")
        duration, offset = _exact_f32(data, offset, f"{field}.duration")
        hide_full, offset = _exact_bool(data, offset, f"{field}.hideInFullPreview")
        position, offset = _exact_vector3(data, offset, f"{field}.position")
        route_id, offset = _exact_i32(data, offset, f"{field}.routeId")
        start_invalid, offset = _exact_bool(data, offset, f"{field}.startPointInvalid")
        return {
            "sourceOffset": start,
            "endOffset": offset,
            "unionTag": tag,
            "memberCount": 7,
            "concreteType": "SpawnerActions.PreviewRoute",
            "actionId": action_id,
            "timestamp": timestamp,
            "duration": duration,
            "hideInFullPreview": hide_full,
            "position": position,
            "routeId": route_id,
            "startPointInvalid": start_invalid,
        }, offset
    if tag == 3:
        if offset >= len(data) or data[offset] != 3:
            raise SpawnerWaveDecodeError(f"{field}: tag 3 member count changed")
        offset += 1
        action_id, offset = _exact_i32(data, offset, f"{field}.actionId")
        timestamp, offset = _exact_f32(data, offset, f"{field}.timestamp")
        key, offset = _read_string(data, offset)
        return {
            "sourceOffset": start,
            "endOffset": offset,
            "unionTag": tag,
            "memberCount": 3,
            "concreteType": "SpawnerActions.RaiseEvent",
            "actionId": action_id,
            "timestamp": timestamp,
            "key": key or "",
        }, offset
    raise SpawnerWaveDecodeError(f"{field}: unsupported union tag {tag}")


def decode_spawner_wave_map_sequential(
    data: bytes,
    *,
    wave_map_offset: int,
) -> dict[str, Any]:
    """Decode wave/group/action maps sequentially from an exact owner cursor."""

    offset = wave_map_offset
    raw_wave_count, offset = _exact_u32(data, offset, "waveMap.count")
    if raw_wave_count == NULL_COUNT:
        wave_count = 0
    elif raw_wave_count <= MAX_WAVE_COUNT:
        wave_count = raw_wave_count
    else:
        raise SpawnerWaveDecodeError(f"waveMap: implausible count {raw_wave_count}")
    waves: list[dict[str, Any]] = []
    unresolved_union = False
    for wave_index in range(wave_count):
        wave_start = offset
        map_key, offset = _exact_i32(data, offset, f"waveMap[{wave_index}].key")
        if offset >= len(data) or data[offset] != SPAWNER_WAVE_MEMBER_COUNT:
            raise SpawnerWaveDecodeError(f"waveMap[{wave_index}]: member count changed")
        offset += 1
        deadline, offset = _exact_f32(
            data, offset, f"waveMap[{wave_index}].deadlineBeginDeltaTime"
        )
        raw_group_count, offset = _exact_u32(data, offset, f"waveMap[{wave_index}].groupMap")
        group_count = 0 if raw_group_count == NULL_COUNT else raw_group_count
        if group_count > MAX_GROUP_COUNT:
            raise SpawnerWaveDecodeError(
                f"waveMap[{wave_index}].groupMap: implausible count {group_count}"
            )
        groups: list[dict[str, Any]] = []
        for group_index in range(group_count):
            group_start = offset
            group_map_key, offset = _exact_i32(
                data, offset, f"waveMap[{wave_index}].groupMap[{group_index}].key"
            )
            if offset >= len(data) or data[offset] != SPAWNER_GROUP_MEMBER_COUNT:
                raise SpawnerWaveDecodeError(
                    f"waveMap[{wave_index}].groupMap[{group_index}]: member count changed"
                )
            offset += 1
            raw_action_count, offset = _exact_u32(
                data, offset, f"waveMap[{wave_index}].groupMap[{group_index}].actionMap"
            )
            action_count = 0 if raw_action_count == NULL_COUNT else raw_action_count
            if action_count > MAX_GROUP_COUNT:
                raise SpawnerWaveDecodeError("implausible actionMap count")
            actions: list[dict[str, Any]] = []
            for action_index in range(action_count):
                action_map_key, offset = _exact_i32(
                    data, offset,
                    f"waveMap[{wave_index}].groupMap[{group_index}].actionMap[{action_index}].key",
                )
                action, offset = _decode_current_spawner_action(
                    data, offset,
                    f"waveMap[{wave_index}].groupMap[{group_index}].actionMap[{action_index}]",
                )
                unresolved_union |= action.get("concreteType") is None
                actions.append({"mapKey": action_map_key, **action})
            group_deadline, offset = _exact_f32(data, offset, "group.deadlineBeginDeltaTime")
            backup_count, offset = _exact_i32(data, offset, "group.groupBackUpCount")
            group_id, offset = _exact_i32(data, offset, "group.groupId")
            group_key, offset = _read_string(data, offset)
            max_count, offset = _exact_i32(data, offset, "group.groupMaxCount")
            group_mode, offset = _exact_i32(data, offset, "group.groupMode")
            kill_count, offset = _exact_i32(data, offset, "group.groupModeKillCount")
            target_key, offset = _read_string(data, offset)
            has_deadline, offset = _exact_bool(data, offset, "group.hasDeadlineBegin")
            limit_max, offset = _exact_bool(data, offset, "group.limitGroupMaxCount")
            group_timestamp, offset = _exact_f32(data, offset, "group.timestamp")
            groups.append({
                "sourceOffset": group_start,
                "endOffset": offset,
                "mapKey": group_map_key,
                "actionMap": actions,
                "deadlineBeginDeltaTime": group_deadline,
                "groupBackUpCount": backup_count,
                "groupId": group_id,
                "groupKey": group_key or "",
                "groupMaxCount": max_count,
                "groupMode": group_mode,
                "groupModeKillCount": kill_count,
                "groupModeTargetKey": target_key or "",
                "hasDeadlineBegin": has_deadline,
                "limitGroupMaxCount": limit_max,
                "timestamp": group_timestamp,
            })
        has_deadline, offset = _exact_bool(data, offset, "wave.hasDeadlineBegin")
        is_hidden, offset = _exact_bool(data, offset, "wave.isHidden")
        repeatable, offset = _exact_bool(data, offset, "wave.repeatable")
        timestamp, offset = _exact_f32(data, offset, "wave.timestamp")
        wave_id, offset = _exact_i32(data, offset, "wave.waveId")
        wave_key, offset = _read_string(data, offset)
        wave_mode, offset = _exact_i32(data, offset, "wave.waveMode")
        kill_count, offset = _exact_i32(data, offset, "wave.waveModeKillCount")
        target_key, offset = _read_string(data, offset)
        waves.append({
            "sourceOffset": wave_start,
            "endOffset": offset,
            "mapKey": map_key,
            "deadlineBeginDeltaTime": deadline,
            "groupMap": groups,
            "hasDeadlineBegin": has_deadline,
            "isHidden": is_hidden,
            "repeatable": repeatable,
            "timestamp": timestamp,
            "waveId": wave_id,
            "waveKey": wave_key or "",
            "waveMode": wave_mode,
            "waveModeKillCount": kill_count,
            "waveModeTargetKey": target_key or "",
        })
    if offset != len(data):
        raise SpawnerWaveDecodeError(
            f"waveMap: trailing bytes after sequential decode: {len(data) - offset}"
        )
    return {
        "waveMapOffset": wave_map_offset,
        "bytesConsumed": offset,
        "waveCount": wave_count,
        "waves": waves,
        "hasUnresolvedActionUnion": unresolved_union,
        "schemaStatus": (
            "exact-outer-frame-unresolved-tag-0"
            if unresolved_union else "named-exact"
        ),
    }
