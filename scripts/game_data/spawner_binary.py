"""Sequential readers for current SpawnerConfigData and its nested records.

The root has six members, waves twelve and groups thirteen. Strings are signed
indices into the caller-selected pool; missing pages never select inline text.
Positive preprocess lists and non-null born behaviors remain explicit stops.
Only the complete generated-order cursor can establish whole-file closure.
Stored settings and action routes do not establish runtime spawn behavior.
"""
from __future__ import annotations

import math
import struct
from typing import Any

from scripts.game_data import levelscript_union_tags as union_tags
from scripts.game_data.string_pool import StringPool, resolve_string_pool_index
from scripts.game_data.spawner_records_native import check_spawner_records_native_inputs


NULL_COUNT = 0xFFFFFFFF
SPAWNER_CONFIG_MEMBER_COUNT = 6
SPAWNER_ENEMY_LIBRARY_ITEM_MEMBER_COUNT = 13
SPAWNER_ENEMY_BORN_BEHAVIOR_MEMBER_COUNT = 18
SPAWNER_BUFF_ITEM_MEMBER_COUNT = 2
SPAWNER_BLACKBOARD_ITEM_MEMBER_COUNT = 4
SPAWNER_WAVE_MEMBER_COUNT = 12
SPAWNER_GROUP_MEMBER_COUNT = 13
MAX_ENEMY_COUNT = 10_000
MAX_BUFF_COUNT = 256
MAX_BLACKBOARD_COUNT = 256
MAX_WAVE_COUNT = 256
MAX_GROUP_COUNT = 1_024
MAX_STRING_BYTES = 4096

SPAWNER_ENEMY_LIBRARY_SCHEMA_MAPPING_ID = "endfield.spawner-enemy-library.pooled.v1"

SPAWNER_WAVE_RUNTIME_MAPPING_ID = (
    "levelscript-union-tags-spawner-wave-group-runtime-v2"
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


def _enemy_read_string(data: bytes, offset: int, field: str, *,
                       strings: StringPool | None = None, max_bytes: int = 512) -> tuple[str | None, int]:
    index, end = _enemy_read_i32(data, offset, f"{field}.poolIndex")
    try:
        value = resolve_string_pool_index(index, strings, field)
    except ValueError as exc:
        raise SpawnerEnemyLibraryDecodeError(str(exc)) from exc
    if value is not None and (len(value.encode("utf-8")) > max_bytes or any(ord(ch) < 0x20 for ch in value)):
        raise SpawnerEnemyLibraryDecodeError(f"{field}: invalid pooled string")
    return value, end


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


def _decode_spawner_buff_item(data: bytes, offset: int, index: int, *, strings: StringPool | None = None) -> tuple[dict[str, Any], int]:
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
            f"bornBuffList[{index}].blackboards[{blackboard_index}].key", strings=strings
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
            f"bornBuffList[{index}].blackboards[{blackboard_index}].valueString", strings=strings
        )
        blackboards.append({
            "key": key or "",
            "useString": use_string,
            "valueFloat": value_float,
            "valueString": value_string or "",
        })
    buff_id, offset = _enemy_read_string(data, offset, f"bornBuffList[{index}].buffId", strings=strings)
    return {
        "sourceOffset": start,
        "blackboards": blackboards,
        "buffId": buff_id or "",
    }, offset


def decode_spawner_enemy_library(data: bytes, *, strings: StringPool | None = None) -> dict[str, Any]:
    """Decode the exact current-build ``SpawnerEnemyLibraryItem`` prefix.

    ``bornBehaviorData`` is nullable and every row in the current exported
    corpus uses the null marker.  A future non-null member-18 payload is
    rejected rather than skipped: its field names are known from metadata but
    its serialized value layout has no current authored fixture.
    """
    if not data or data[0] != SPAWNER_CONFIG_MEMBER_COUNT:
        raise SpawnerEnemyLibraryDecodeError("SpawnerConfig member count changed")
    config_id, offset = _enemy_read_string(data, 1, "configId", strings=strings)
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
            buff, offset = _decode_spawner_buff_item(data, offset, buff_index, strings=strings)
            buffs.append(buff)

        born_template_id, offset = _enemy_read_string(
            data, offset, f"enemyLibrary[{index}].bornTemplateId", strings=strings
        )
        enemy_id, offset = _enemy_read_string(data, offset, f"enemyLibrary[{index}].enemyId", strings=strings)
        enemy_level, offset = _enemy_read_i32(data, offset, f"enemyLibrary[{index}].enemyLevel")
        force_to_battle, offset = _enemy_read_bool(
            data, offset, f"enemyLibrary[{index}].forceToBattle"
        )
        key, offset = _enemy_read_string(data, offset, f"enemyLibrary[{index}].key", strings=strings)
        override_ai_config, offset = _enemy_read_string(
            data, offset, f"enemyLibrary[{index}].overrideAIConfig", strings=strings
        )
        patrol_gait, offset = _enemy_read_i32(data, offset, f"enemyLibrary[{index}].patrolGait")
        pre_warn_audio_event_key, offset = _enemy_read_string(
            data, offset, f"enemyLibrary[{index}].preWarnAudioEventKey", strings=strings
        )
        pre_warn_effect_fixed_rotation, offset = _enemy_read_optional_vector3(
            data, offset, f"enemyLibrary[{index}].preWarnEffectFixedRotation"
        )
        pre_warn_effect_key, offset = _enemy_read_string(
            data, offset, f"enemyLibrary[{index}].preWarnEffectKey", strings=strings
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
        "schemaStatus": "exact-pooled-null-born-behavior",
    }


def _decode_patrol_sub_action(
    data: bytes,
    offset: int,
    field: str,
    *,
    strings: StringPool | None = None,
) -> tuple[dict[str, Any], int]:
    """Decode the authored member-26 ``PatrolSubAction`` profile.

    In the current corpus the blackboard-pair lists are empty and the
    polymorphic ``subActionData`` values are null; both boundaries stay
    fail-closed until an authored positive fixture exists.
    """

    start = offset
    if offset >= len(data) or data[offset] != 26:
        raise SpawnerEnemyLibraryDecodeError(f"{field}: PatrolSubAction member count changed")
    offset += 1
    values: dict[str, Any] = {}
    for name in ("actionEndType", "animKeyTag", "animMaskType"):
        values[name], offset = _enemy_read_i32(data, offset, f"{field}.{name}")
    values["animName"], offset = _enemy_read_string(data, offset, f"{field}.animName", strings=strings)
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
    values["eventKey"], offset = _enemy_read_string(data, offset, f"{field}.eventKey", strings=strings)
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
    values["radioId"], offset = _enemy_read_string(data, offset, f"{field}.radioId", strings=strings)
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
    *,
    strings: StringPool | None = None,
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
        row, offset = _decode_patrol_sub_action(data, offset, f"{field}.subActions[{index}]", strings=strings)
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
    *,
    strings: StringPool | None = None,
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
        action, offset = _decode_patrol_action(data, offset, f"{field}.actions[{index}]", strings=strings)
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


def decode_spawner_named_prefix(data: bytes, *, strings: StringPool | None = None) -> dict[str, Any]:
    """Decode configId, enemyLibrary, routeMap and settings at one cursor.

    Route patrols are accepted only for the current profile: positive
    ``PatrolAction`` lists are read exactly, but each subaction's
    blackboard-pair list must be empty and its polymorphic ``subActionData``
    null. The returned ``waveMapOffset`` is therefore an exact
    generated-order cursor, not a byte-pattern candidate.
    """

    enemy_prefix = decode_spawner_enemy_library(data, strings=strings)
    offset = int(enemy_prefix["enemyLibraryEndOffset"])
    preprocess_start = offset
    preprocess_count, offset = _enemy_read_u32(data, offset, "preprocessList.count")
    if preprocess_count not in (0, NULL_COUNT):
        raise SpawnerEnemyLibraryDecodeError(f"preprocessList: unsupported positive count {preprocess_count}")
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
            data, offset, f"routeMap[{index}].patrolData", strings=strings
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
            data, offset, f"settings.preloadEffectKeyList[{index}]", max_bytes=4096, strings=strings
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
        "preprocessList": None if preprocess_count == NULL_COUNT else [],
        "preprocessListOffset": preprocess_start,
        "routeMapOffset": preprocess_start + 4,
        "routeMapCount": route_count,
        "routeMap": routes,
        "settings": settings,
        "waveMapOffset": offset,
        "schemaStatus": "exact-pooled-prefix-through-settings",
    }


def _read_string(data: bytes, offset: int, *, strings: StringPool | None = None) -> tuple[str | None, int]:
    try:
        return _enemy_read_string(data, offset, "wave.string", strings=strings, max_bytes=MAX_STRING_BYTES)
    except SpawnerEnemyLibraryDecodeError as exc:
        raise SpawnerWaveDecodeError(str(exc)) from exc


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


# ``SpawnerActionData`` layouts read here, with the member count each reads.
# Every action opens with the ``SpawnerActionBase`` members ``actionId``,
# ``defaultDisable`` and ``timestamp`` (``_read_action_base``).
# Tags are resolved by type name per build; never write one here.
_SPAWNER_ACTION_LAYOUTS = {
    "SpawnerActions_SpawnMonsterFromTemplateV2": 13,
    "SpawnerActions_Pause": 4,
    "SpawnerActions_PlayAudio": 4,
    "SpawnerActions_PreviewRoute": 8,
    "SpawnerActions_RaiseEvent": 4,
}


def _read_action_base(
    data: bytes, offset: int, field: str
) -> tuple[dict[str, Any], int]:
    action_id, offset = _exact_i32(data, offset, f"{field}.actionId")
    default_disable, offset = _exact_bool(data, offset, f"{field}.defaultDisable")
    timestamp, offset = _exact_f32(data, offset, f"{field}.timestamp")
    return {
        "actionId": action_id,
        "defaultDisable": default_disable,
        "timestamp": timestamp,
    }, offset


def _spawner_action_routes() -> dict[tuple[int, int], str]:
    return union_tags.routes("SpawnerActionData", _SPAWNER_ACTION_LAYOUTS)


def _decode_current_spawner_action(
    data: bytes,
    offset: int,
    field: str,
    *,
    strings: StringPool | None = None,
    routes: dict[int, tuple[str, int]] | None = None,
) -> tuple[dict[str, Any], int]:
    """Decode the reviewed ``SpawnerActionData`` routes, resolved by type name."""

    start = offset
    if offset >= len(data):
        raise SpawnerWaveDecodeError(f"{field}: truncated union tag")
    tag = data[offset]
    offset += 1
    if routes is None:
        routes = {key[0]: (name, key[1]) for key, name in _spawner_action_routes().items()}
    if tag not in routes:
        raise SpawnerWaveDecodeError(
            f"{field}: unsupported union tag {tag}{union_tags.unavailable_note()}"
        )
    action, member_count = routes[tag]
    if offset >= len(data) or data[offset] != member_count:
        raise SpawnerWaveDecodeError(f"{field}: tag {tag} member count changed")
    offset += 1
    if action == "SpawnerActions_SpawnMonsterFromTemplateV2":
        base, offset = _read_action_base(data, offset, field)
        face_main, offset = _exact_bool(data, offset, f"{field}.faceMainCharacter")
        library_key, offset = _read_string(data, offset, strings=strings)
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
            "memberCount": member_count,
            "concreteType": "SpawnerActions.SpawnMonsterFromTemplateV2",
            **base,
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
    if action == "SpawnerActions_Pause":
        base, offset = _read_action_base(data, offset, field)
        string_value, offset = _read_string(data, offset, strings=strings)
        return {
            "sourceOffset": start,
            "endOffset": offset,
            "unionTag": tag,
            "memberCount": member_count,
            "concreteType": "SpawnerActions.Pause",
            **base,
            "pauseKey": string_value,
        }, offset
    if action == "SpawnerActions_PlayAudio":
        base, offset = _read_action_base(data, offset, field)
        audio_id, offset = _read_string(data, offset, strings=strings)
        return {
            "sourceOffset": start,
            "endOffset": offset,
            "unionTag": tag,
            "memberCount": member_count,
            "concreteType": "SpawnerActions.PlayAudio",
            **base,
            "audioId": audio_id or "",
        }, offset
    if action == "SpawnerActions_PreviewRoute":
        base, offset = _read_action_base(data, offset, field)
        duration, offset = _exact_f32(data, offset, f"{field}.duration")
        hide_full, offset = _exact_bool(data, offset, f"{field}.hideInFullPreview")
        position, offset = _exact_vector3(data, offset, f"{field}.position")
        route_id, offset = _exact_i32(data, offset, f"{field}.routeId")
        start_invalid, offset = _exact_bool(data, offset, f"{field}.startPointInvalid")
        return {
            "sourceOffset": start,
            "endOffset": offset,
            "unionTag": tag,
            "memberCount": member_count,
            "concreteType": "SpawnerActions.PreviewRoute",
            **base,
            "duration": duration,
            "hideInFullPreview": hide_full,
            "position": position,
            "routeId": route_id,
            "startPointInvalid": start_invalid,
        }, offset
    if action == "SpawnerActions_RaiseEvent":
        base, offset = _read_action_base(data, offset, field)
        key, offset = _read_string(data, offset, strings=strings)
        return {
            "sourceOffset": start,
            "endOffset": offset,
            "unionTag": tag,
            "memberCount": member_count,
            "concreteType": "SpawnerActions.RaiseEvent",
            **base,
            "key": key or "",
        }, offset
    raise SpawnerWaveDecodeError(f"{field}: unsupported union tag {tag}")


def decode_spawner_wave_map_sequential(
    data: bytes,
    *,
    wave_map_offset: int,
    strings: StringPool | None = None,
) -> dict[str, Any]:
    """Decode wave/group/action maps sequentially from an exact owner cursor."""

    selected_routes = _spawner_action_routes()
    routes = {key[0]: (name, key[1]) for key, name in selected_routes.items()}
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
        wave_disabled, offset = _exact_bool(data, offset, "wave.defaultDisable")
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
                    f"waveMap[{wave_index}].groupMap[{group_index}].actionMap[{action_index}]", strings=strings, routes=routes
                )
                unresolved_union |= action.get("concreteType") is None
                actions.append({"mapKey": action_map_key, **action})
            group_deadline, offset = _exact_f32(data, offset, "group.deadlineBeginDeltaTime")
            group_disabled, offset = _exact_bool(data, offset, "group.defaultDisable")
            backup_count, offset = _exact_i32(data, offset, "group.groupBackUpCount")
            group_id, offset = _exact_i32(data, offset, "group.groupId")
            group_key, offset = _read_string(data, offset, strings=strings)
            max_count, offset = _exact_i32(data, offset, "group.groupMaxCount")
            group_mode, offset = _exact_i32(data, offset, "group.groupMode")
            kill_count, offset = _exact_i32(data, offset, "group.groupModeKillCount")
            target_key, offset = _read_string(data, offset, strings=strings)
            has_deadline, offset = _exact_bool(data, offset, "group.hasDeadlineBegin")
            limit_max, offset = _exact_bool(data, offset, "group.limitGroupMaxCount")
            group_timestamp, offset = _exact_f32(data, offset, "group.timestamp")
            groups.append({
                "sourceOffset": group_start,
                "endOffset": offset,
                "mapKey": group_map_key,
                "actionMap": actions,
                "deadlineBeginDeltaTime": group_deadline,
                "defaultDisable": group_disabled,
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
        wave_key, offset = _read_string(data, offset, strings=strings)
        wave_mode, offset = _exact_i32(data, offset, "wave.waveMode")
        kill_count, offset = _exact_i32(data, offset, "wave.waveModeKillCount")
        target_key, offset = _read_string(data, offset, strings=strings)
        waves.append({
            "sourceOffset": wave_start,
            "endOffset": offset,
            "mapKey": map_key,
            "deadlineBeginDeltaTime": deadline,
            "groupMap": groups,
            "defaultDisable": wave_disabled,
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
    if _spawner_action_routes() != selected_routes:
        raise SpawnerWaveDecodeError("waveMap: native union routes changed during decode")
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


def frame_spawner_named(data: bytes, *, strings: StringPool | None = None) -> dict[str, Any]:
    """Read one named SpawnerConfig cursor, retaining its proved prefix on refusal.

    A suffix match cannot close an unknown prefix. The whole-file status is
    admitted only by the sequential wave reader at physical EOF; unsupported
    route or action variants keep the earlier fields and an explicit open range.
    """
    gate = check_spawner_records_native_inputs()
    if gate.status != "validated":
        raise SpawnerEnemyLibraryDecodeError(f"spawnerRecords.native:{gate.status}:{gate.detail}")
    boundary = (
        "exact: stored SpawnerConfig fields and admitted nested routes at their "
        "sequential cursor; authored settings, positions and actions do not "
        "establish runtime spawning, execution, or ownership."
    )
    try:
        prefix = decode_spawner_named_prefix(data, strings=strings)
    except SpawnerEnemyLibraryDecodeError as exc:
        # The independent enemy-library reader owns this earlier boundary.
        prefix = decode_spawner_enemy_library(data, strings=strings)
        reached = int(prefix["enemyLibraryEndOffset"])
        return {
            **prefix, "schemaStatus": "bounded_partial",
            "serializedMemberCount": SPAWNER_CONFIG_MEMBER_COUNT,
            "closedFields": ["configId", "enemyLibrary"],
            "bytesConsumed": reached,
            "openField": {"name": "preprocessList", "startOffset": reached},
            "opaqueRemainder": {"startOffset": reached, "byteLength": len(data) - reached},
            "diagnostic": str(exc), "evidenceBoundary": boundary,
        }
    reached = int(prefix["waveMapOffset"])
    closed = ["configId", "enemyLibrary", "preprocessList", "routeMap", "settings"]
    try:
        waves = decode_spawner_wave_map_sequential(data, wave_map_offset=reached, strings=strings)
    except SpawnerWaveDecodeError as exc:
        return {
            **prefix, "schemaStatus": "bounded_partial",
            "serializedMemberCount": SPAWNER_CONFIG_MEMBER_COUNT, "closedFields": closed,
            "bytesConsumed": reached,
            "openField": {"name": "waveMap", "startOffset": reached},
            "opaqueRemainder": {"startOffset": reached, "byteLength": len(data) - reached},
            "diagnostic": str(exc), "evidenceBoundary": boundary,
        }
    return {
        **prefix, **waves, "serializedMemberCount": SPAWNER_CONFIG_MEMBER_COUNT,
        "schemaStatus": (
            "named_exact" if waves["schemaStatus"] == "named-exact"
            else waves["schemaStatus"]
        ),
        "closedFields": [*closed, "waveMap"],
        "openField": None, "evidenceBoundary": boundary,
    }
