"""Exact current codecs for high-coverage LevelScript module values."""

from __future__ import annotations

import math
import struct
from typing import Any, Callable

from scripts.game_data import levelscript_union_tags as union_tags


class LevelScriptModuleCodecError(ValueError):
    """Raised when a declared module value cannot advance exactly."""


_MAX_COUNT = 16_384
_MAX_STRING_BYTES = 1 << 20

# Module types with a reviewed codec. Each tag is resolved from the
# LevelScriptModuleData union by type name, never written down.
_MODULE_TYPES = (
    "EncounterData",
    "FogNestControllerData",
    "GhostWallModuleData",
    "GuideButterflyModuleData",
    "SpecialSightControllerData",
    "SuperPressureBoardGroupData",
    "TyphoeaArcheryUnitData",
    "WaterProgressSyncData",
)
MODULE_TAG_NAMES = {
    union_tags.pair("LevelScriptModuleData", name)[0]: name for name in _MODULE_TYPES
}


def _need(data: bytes, cursor: int, size: int, field: str) -> None:
    if cursor < 0 or size < 0 or cursor + size > len(data):
        raise LevelScriptModuleCodecError(
            f"truncated {field}: offset={cursor} size={size} length={len(data)}"
        )


def _i32(data: bytes, cursor: int, field: str) -> tuple[int, int]:
    _need(data, cursor, 4, field)
    return struct.unpack_from("<i", data, cursor)[0], cursor + 4


def _u32(data: bytes, cursor: int, field: str) -> tuple[int, int]:
    _need(data, cursor, 4, field)
    return struct.unpack_from("<I", data, cursor)[0], cursor + 4


def _u64(data: bytes, cursor: int, field: str) -> tuple[int, int]:
    _need(data, cursor, 8, field)
    return struct.unpack_from("<Q", data, cursor)[0], cursor + 8


def _bool(data: bytes, cursor: int, field: str) -> tuple[bool, int]:
    _need(data, cursor, 1, field)
    raw = data[cursor]
    if raw not in (0, 1):
        raise LevelScriptModuleCodecError(
            f"invalid bool {field}: offset={cursor} value={raw}"
        )
    return bool(raw), cursor + 1


def _f32(data: bytes, cursor: int, field: str) -> tuple[float, int]:
    _need(data, cursor, 4, field)
    value = struct.unpack_from("<f", data, cursor)[0]
    if not math.isfinite(value):
        raise LevelScriptModuleCodecError(
            f"non-finite {field}: offset={cursor} value={value!r}"
        )
    return value, cursor + 4


def _string(data: bytes, cursor: int, field: str) -> tuple[str | None, int]:
    size, cursor = _i32(data, cursor, f"{field}.length")
    if size == -1:
        return None, cursor
    if size < 0 or size > _MAX_STRING_BYTES:
        raise LevelScriptModuleCodecError(
            f"invalid string length {field}: offset={cursor - 4} value={size}"
        )
    _need(data, cursor, size, field)
    try:
        return data[cursor : cursor + size].decode("utf-8"), cursor + size
    except UnicodeDecodeError as error:
        raise LevelScriptModuleCodecError(
            f"invalid UTF-8 {field}: offset={cursor} size={size}"
        ) from error


def _count(data: bytes, cursor: int, field: str) -> tuple[int | None, int]:
    value, cursor = _i32(data, cursor, f"{field}.count")
    if value == -1:
        return None, cursor
    if value < 0 or value > _MAX_COUNT:
        raise LevelScriptModuleCodecError(
            f"invalid collection count {field}: offset={cursor - 4} value={value}"
        )
    return value, cursor


def _list(
    data: bytes,
    cursor: int,
    field: str,
    decoder: Callable[[bytes, int, str], tuple[Any, int]],
) -> tuple[dict[str, Any], int]:
    count, cursor = _count(data, cursor, field)
    if count is None:
        return {"status": "null", "count": None, "values": None}, cursor
    values = []
    for index in range(count):
        value, cursor = decoder(data, cursor, f"{field}[{index}]")
        values.append(value)
    return {"status": "present", "count": count, "values": values}, cursor


def _entity_ptr(data: bytes, cursor: int, field: str) -> tuple[dict[str, Any], int]:
    _need(data, cursor, 1, f"{field}.memberCount")
    if data[cursor] != 3:
        raise LevelScriptModuleCodecError(
            f"invalid EntityPtr member count: offset={cursor} value={data[cursor]}"
        )
    cursor += 1
    logic_id, cursor = _u64(data, cursor, f"{field}.logicId")
    slot_id, cursor = _u32(data, cursor, f"{field}.slotId")
    use_slot_id, cursor = _bool(data, cursor, f"{field}.useSlotId")
    return {
        "logicId": str(logic_id),
        "slotId": slot_id,
        "useSlotId": use_slot_id,
    }, cursor


def _i32_item(data: bytes, cursor: int, field: str) -> tuple[int, int]:
    return _i32(data, cursor, field)


def _f32_item(data: bytes, cursor: int, field: str) -> tuple[float, int]:
    return _f32(data, cursor, field)


def _parse_ghost_wall(
    data: bytes, cursor: int, field: str
) -> tuple[dict[str, Any], int]:
    out: dict[str, Any] = {}
    out["customInDangerZone"], cursor = _bool(data, cursor, f"{field}.customInDangerZone")
    out["enterInnerScreenEffectName"], cursor = _string(data, cursor, f"{field}.enterInnerScreenEffectName")
    out["forbidCameraBeforeTeleport"], cursor = _bool(data, cursor, f"{field}.forbidCameraBeforeTeleport")
    out["inDangerTriggerVolumeId"], cursor = _u32(data, cursor, f"{field}.inDangerTriggerVolumeId")
    out["innerTriggerVolumeId"], cursor = _u32(data, cursor, f"{field}.innerTriggerVolumeId")
    for name in ("isCorrectGhostWall", "keepRotation", "keepStationaryInTeleport"):
        out[name], cursor = _bool(data, cursor, f"{field}.{name}")
    out["keepWalkTimeAfterTeleport"], cursor = _f32(data, cursor, f"{field}.keepWalkTimeAfterTeleport")
    out["moveGait"], cursor = _i32(data, cursor, f"{field}.moveGait")
    if out["moveGait"] not in (0, 1, 2):
        raise LevelScriptModuleCodecError(
            f"invalid GroundedMoveGait {field}: value={out['moveGait']}"
        )
    for name in ("moveTargetPositionA", "moveTargetPositionB"):
        values = []
        for axis in "xyz":
            value, cursor = _f32(data, cursor, f"{field}.{name}.{axis}")
            values.append(value)
        out[name] = dict(zip("xyz", values))
    out["moveToTargetBeforeTeleport"], cursor = _bool(data, cursor, f"{field}.moveToTargetBeforeTeleport")
    out["outerEffectDecoId"], cursor = _u64(data, cursor, f"{field}.outerEffectDecoId")
    out["outerTriggerVolumeId"], cursor = _u32(data, cursor, f"{field}.outerTriggerVolumeId")
    for name in (
        "overrideRecenterDuration", "overrideSendLevelEventDelay",
        "recenterCameraBeforeTeleport",
    ):
        out[name], cursor = _bool(data, cursor, f"{field}.{name}")
    for name in (
        "recenterCameraDuration", "recenterCameraThreshold",
        "screenFadeInWhiteTime", "sendLevelEventDaleyAfterTeleport",
    ):
        out[name], cursor = _f32(data, cursor, f"{field}.{name}")
    out["teleportId"], cursor = _string(data, cursor, f"{field}.teleportId")
    for name in ("teleportTargetPosition", "teleportTargetRotation"):
        values = []
        for axis in "xyz":
            value, cursor = _f32(data, cursor, f"{field}.{name}.{axis}")
            values.append(value)
        out[name] = dict(zip("xyz", values))
    return out, cursor


def _parse_water_progress(
    data: bytes, cursor: int, field: str
) -> tuple[dict[str, Any], int]:
    decrease_cd, cursor = _f32(data, cursor, f"{field}.decreaseCD")
    decrease_at_max, cursor = _bool(data, cursor, f"{field}.decreaseIfReachMax")
    decrease_ratio, cursor = _f32(data, cursor, f"{field}.decreaseRatio")
    entity_ptrs, cursor = _list(data, cursor, f"{field}.entityPtrList", _entity_ptr)
    max_cd, cursor = _f32(data, cursor, f"{field}.reachMaxDecreaseCD")
    return {
        "decreaseCD": decrease_cd,
        "decreaseIfReachMax": decrease_at_max,
        "decreaseRatio": decrease_ratio,
        "entityPtrList": entity_ptrs,
        "reachMaxDecreaseCD": max_cd,
    }, cursor


def _parse_special_sight(
    data: bytes, cursor: int, field: str
) -> tuple[dict[str, Any], int]:
    pointer, cursor = _entity_ptr(data, cursor, f"{field}.specialSight")
    slot_id, cursor = _u32(data, cursor, f"{field}.viewTriggerSlotId")
    return {"specialSight": pointer, "viewTriggerSlotId": slot_id}, cursor


def _parse_pressure_group(
    data: bytes, cursor: int, field: str
) -> tuple[dict[str, Any], int]:
    delay, cursor = _f32(data, cursor, f"{field}.demonstrationStartDelayTime")
    entities, cursor = _list(data, cursor, f"{field}.entityPtrList", _entity_ptr)
    game_type, cursor = _i32(data, cursor, f"{field}.gameType")
    initial_states, cursor = _list(data, cursor, f"{field}.initialEntityStates", _i32_item)
    group_state, cursor = _i32(data, cursor, f"{field}.initialGroupState")
    if game_type not in (0, 1, 2):
        raise LevelScriptModuleCodecError(
            f"invalid SuperPressureBoardGroupGameType {field}: value={game_type}"
        )
    if group_state not in (0, 1, 2, 3, 4) or any(
        value not in (0, 1, 2, 3, 4)
        for value in (initial_states.get("values") or [])
    ):
        raise LevelScriptModuleCodecError(
            f"invalid SuperPressureBoardState {field}"
        )
    switch, cursor = _entity_ptr(data, cursor, f"{field}.switchEntityPtr")
    order, cursor = _list(data, cursor, f"{field}.waitActiveEntityOrderList", _i32_item)
    return {
        "demonstrationStartDelayTime": delay,
        "entityPtrList": entities,
        "gameType": game_type,
        "initialEntityStates": initial_states,
        "initialGroupState": group_state,
        "switchEntityPtr": switch,
        "waitActiveEntityOrderList": order,
    }, cursor


def _parse_butterfly_scatter(
    data: bytes, cursor: int, field: str
) -> tuple[dict[str, Any], int]:
    _need(data, cursor, 1, f"{field}.memberCount")
    if data[cursor] != 3:
        raise LevelScriptModuleCodecError(
            f"invalid ButterflyScatterSerializeInfo member count: "
            f"offset={cursor} value={data[cursor]}"
        )
    cursor += 1
    curve_index, cursor = _i32(data, cursor, f"{field}.curveMoveIndex")
    entities, cursor = _list(
        data, cursor, f"{field}.smallButterflyEntityList", _entity_ptr
    )
    trigger_id, cursor = _u32(data, cursor, f"{field}.triggerVolumeId")
    return {
        "curveMoveIndex": curve_index,
        "smallButterflyEntityList": entities,
        "triggerVolumeId": trigger_id,
    }, cursor


def _parse_guide_butterfly(
    data: bytes, cursor: int, field: str
) -> tuple[dict[str, Any], int]:
    reset_time, cursor = _f32(data, cursor, f"{field}.butterflyResetTime")
    gather_speed, cursor = _f32(data, cursor, f"{field}.gatherTailEffectSpeed")
    leader, cursor = _entity_ptr(data, cursor, f"{field}.leaderButterflyEntityPtr")
    scatter_speed, cursor = _f32(data, cursor, f"{field}.scatterTailEffectSpeed")
    gather_fx, cursor = _string(data, cursor, f"{field}.smallButterflyGatherFx")
    scatter_fx, cursor = _string(data, cursor, f"{field}.smallButterflyScatterFx")
    scatter_rows, cursor = _list(
        data,
        cursor,
        f"{field}.smallButterflyScatterInfoList",
        _parse_butterfly_scatter,
    )
    return {
        "butterflyResetTime": reset_time,
        "gatherTailEffectSpeed": gather_speed,
        "leaderButterflyEntityPtr": leader,
        "scatterTailEffectSpeed": scatter_speed,
        "smallButterflyGatherFx": gather_fx,
        "smallButterflyScatterFx": scatter_fx,
        "smallButterflyScatterInfoList": scatter_rows,
    }, cursor


def _lsm_ptr(data: bytes, cursor: int, field: str) -> tuple[dict[str, Any], int]:
    _need(data, cursor, 1, f"{field}.memberCount")
    if data[cursor] != 1:
        raise LevelScriptModuleCodecError(
            f"invalid LsmPtr member count: offset={cursor} value={data[cursor]}"
        )
    value, cursor = _u64(data, cursor + 1, f"{field}.id")
    return {"id": str(value)}, cursor


def _fog_effect(
    data: bytes, cursor: int, field: str
) -> tuple[dict[str, Any], int]:
    _need(data, cursor, 1, f"{field}.memberCount")
    if data[cursor] != 5:
        raise LevelScriptModuleCodecError(
            f"invalid FogNest EffectInfo member count: "
            f"offset={cursor} value={data[cursor]}"
        )
    cursor += 1
    delay, cursor = _f32(data, cursor, f"{field}.delayToHide")
    key, cursor = _string(data, cursor, f"{field}.effectKey")
    vectors: dict[str, dict[str, float]] = {}
    for name in ("eulerAngles", "position", "scale"):
        values = []
        for axis in "xyz":
            component, cursor = _f32(data, cursor, f"{field}.{name}.{axis}")
            values.append(component)
        vectors[name] = dict(zip("xyz", values))
    return {"delayToHide": delay, "effectKey": key, **vectors}, cursor


def _parse_fog_nest(
    data: bytes, cursor: int, field: str
) -> tuple[dict[str, Any], int]:
    air_walls, cursor = _list(data, cursor, f"{field}.airWallIdList", _entity_ptr)
    effects, cursor = _list(data, cursor, f"{field}.effectList", _fog_effect)
    fog_nest, cursor = _entity_ptr(data, cursor, f"{field}.fogNest")
    is_large, cursor = _bool(data, cursor, f"{field}.isLargeController")
    small_nests, cursor = _list(data, cursor, f"{field}.smallFogNestList", _lsm_ptr)
    return {
        "airWallIdList": air_walls,
        "effectList": effects,
        "fogNest": fog_nest,
        "isLargeController": is_large,
        "smallFogNestList": small_nests,
    }, cursor


def _nullable_member(
    data: bytes,
    cursor: int,
    field: str,
    expected_count: int,
    parser: Callable[[bytes, int, str], tuple[Any, int]],
) -> tuple[Any, int]:
    _need(data, cursor, 1, f"{field}.memberCount")
    if data[cursor] == 0xFF:
        return None, cursor + 1
    if data[cursor] != expected_count:
        raise LevelScriptModuleCodecError(
            f"invalid {field} member count: offset={cursor} "
            f"value={data[cursor]} expected={expected_count}"
        )
    return parser(data, cursor + 1, field)


def _typhoea_extra_battle(
    data: bytes, cursor: int, field: str
) -> tuple[dict[str, Any], int]:
    count, cursor = _i32(data, cursor, f"{field}.initialStickBombCount")
    return {"initialStickBombCount": count}, cursor


def _typhoea_movement(
    data: bytes, cursor: int, field: str
) -> tuple[dict[str, Any], int]:
    curve_time, cursor = _list(data, cursor, f"{field}.curveTime", _f32_item)
    level_id, cursor = _string(data, cursor, f"{field}.levelId")
    move_mode, cursor = _i32(data, cursor, f"{field}.moveMode")
    if move_mode not in (0, 1, 2):
        raise LevelScriptModuleCodecError(
            f"invalid ESplineMoveMode {field}: value={move_mode}"
        )
    stay_time, cursor = _list(data, cursor, f"{field}.pointStayTime", _f32_item)
    spline_id, cursor = _i32(data, cursor, f"{field}.splineId")
    start_index, cursor = _i32(data, cursor, f"{field}.startPointIndex")
    return {
        "curveTime": curve_time,
        "levelId": level_id,
        "moveMode": move_mode,
        "pointStayTime": stay_time,
        "splineId": spline_id,
        "startPointIndex": start_index,
    }, cursor


def _typhoea_scale(
    data: bytes, cursor: int, field: str
) -> tuple[dict[str, Any], int]:
    out = {}
    for name in (
        "scaleDurationSec",
        "scaleIdleDurationSec",
        "scalePreDelayDurationSec",
    ):
        out[name], cursor = _f32(data, cursor, f"{field}.{name}")
    return out, cursor


def _typhoea_target(
    data: bytes, cursor: int, field: str
) -> tuple[dict[str, Any], int]:
    _need(data, cursor, 1, f"{field}.memberCount")
    if data[cursor] != 12:
        raise LevelScriptModuleCodecError(
            f"invalid TyphoeaArcheryTargetData member count: "
            f"offset={cursor} value={data[cursor]}"
        )
    cursor += 1
    out: dict[str, Any] = {}
    out["alwaysFaceMainChar"], cursor = _bool(data, cursor, f"{field}.alwaysFaceMainChar")
    out["extraBattleInfo"], cursor = _nullable_member(
        data, cursor, f"{field}.extraBattleInfo", 1, _typhoea_extra_battle
    )
    out["hp"], cursor = _i32(data, cursor, f"{field}.hp")
    out["lockTimeRatio"], cursor = _f32(data, cursor, f"{field}.lockTimeRatio")
    out["movementData"], cursor = _nullable_member(
        data, cursor, f"{field}.movementData", 6, _typhoea_movement
    )
    out["mvscScaleData"], cursor = _nullable_member(
        data, cursor, f"{field}.mvscScaleData", 3, _typhoea_scale
    )
    out["postModelId"], cursor = _string(data, cursor, f"{field}.postModelId")
    out["recoverTime"], cursor = _f32(data, cursor, f"{field}.recoverTime")
    out["shield"], cursor = _i32(data, cursor, f"{field}.shield")
    vectors = {}
    for name, axes in (("spawnPoint", "xyz"), ("spawnRotation", "xyzw")):
        values = []
        for axis in axes:
            component, cursor = _f32(data, cursor, f"{field}.{name}.{axis}")
            values.append(component)
        vectors[name] = dict(zip(axes, values))
    out.update(vectors)
    out["spawnWaitTime"], cursor = _f32(data, cursor, f"{field}.spawnWaitTime")
    return out, cursor


def _parse_typhoea_archery(
    data: bytes, cursor: int, field: str
) -> tuple[dict[str, Any], int]:
    need_connection, cursor = _bool(data, cursor, f"{field}.needVfxConnection")
    self_motivated, cursor = _bool(data, cursor, f"{field}.selfMotivated")
    targets, cursor = _list(data, cursor, f"{field}.targetsData", _typhoea_target)
    connection_id, cursor = _string(data, cursor, f"{field}.vfxConnectionId")
    left, cursor = _list(data, cursor, f"{field}.vfxConnectionLeft", _i32_item)
    right, cursor = _list(data, cursor, f"{field}.vfxConnectionRight", _i32_item)
    return {
        "needVfxConnection": need_connection,
        "selfMotivated": self_motivated,
        "targetsData": targets,
        "vfxConnectionId": connection_id,
        "vfxConnectionLeft": left,
        "vfxConnectionRight": right,
    }, cursor


def _u64_item(data: bytes, cursor: int, field: str) -> tuple[int, int]:
    return _u64(data, cursor, field)


def _enum(
    data: bytes,
    cursor: int,
    field: str,
    accepted: set[int],
) -> tuple[int, int]:
    value, cursor = _i32(data, cursor, field)
    if value not in accepted:
        raise LevelScriptModuleCodecError(f"invalid {field}: value={value}")
    return value, cursor


def _encounter_opera_segments(
    data: bytes, cursor: int, field: str
) -> tuple[dict[str, Any], int]:
    count, cursor = _count(data, cursor, field)
    if count is None:
        return {"status": "null", "count": None, "values": None}, cursor
    if count:
        raise LevelScriptModuleCodecError(
            f"unsupported positive {field} count={count}"
        )
    return {"status": "present", "count": 0, "values": []}, cursor


def _encounter_pos_rot(
    data: bytes, cursor: int, field: str
) -> tuple[dict[str, Any], int]:
    out = {}
    for name in ("eulerAngles", "position"):
        values = []
        for axis in "xyz":
            component, cursor = _f32(data, cursor, f"{field}.{name}.{axis}")
            values.append(component)
        out[name] = dict(zip("xyz", values))
    return out, cursor


def _encounter_battle(
    data: bytes, cursor: int, field: str
) -> tuple[dict[str, Any], int]:
    delay, cursor = _f32(data, cursor, f"{field}.completeDelay")
    delay_mode, cursor = _enum(
        data, cursor, f"{field}.completeDelayMode", {0, 1, 2, 3}
    )
    delay_param, cursor = _string(data, cursor, f"{field}.completeDelayStrParam")
    complete_mode, cursor = _enum(
        data, cursor, f"{field}.completeMode", {0, 1}
    )
    dont_hide, cursor = _bool(
        data, cursor, f"{field}.dontHideDeadEnemyWhenComplete"
    )
    exit_slot, cursor = _u32(data, cursor, f"{field}.exitTriggerSlotId")
    keep_hatred, cursor = _bool(data, cursor, f"{field}.keepHatred")
    protect, cursor = _bool(
        data, cursor, f"{field}.protectEnemyBeforeBattlePart"
    )
    return {
        "completeDelay": delay,
        "completeDelayMode": delay_mode,
        "completeDelayStrParam": delay_param,
        "completeMode": complete_mode,
        "dontHideDeadEnemyWhenComplete": dont_hide,
        "exitTriggerSlotId": exit_slot,
        "keepHatred": keep_hatred,
        "protectEnemyBeforeBattlePart": protect,
    }, cursor


def _encounter_intro(
    data: bytes, cursor: int, field: str
) -> tuple[dict[str, Any], int]:
    air_wall_timing, cursor = _enum(
        data, cursor, f"{field}.airWallShowTiming", {0, 2, 4, 6}
    )
    enemy_timing, cursor = _enum(
        data, cursor, f"{field}.enemySpawnTiming", {0, 1, 2, 4, 6}
    )
    fade_in, cursor = _f32(data, cursor, f"{field}.fadeInDuration")
    fade_out, cursor = _f32(data, cursor, f"{field}.fadeOutDuration")
    has_in, cursor = _bool(data, cursor, f"{field}.hasFadeIn")
    has_out, cursor = _bool(data, cursor, f"{field}.hasFadeOut")
    opera, cursor = _encounter_opera_segments(data, cursor, f"{field}.operaSegments")
    teleport_mode, cursor = _enum(
        data, cursor, f"{field}.teleportMode", {0, 1, 2, 3}
    )
    slots = []
    for index in range(4):
        value, cursor = _encounter_pos_rot(
            data, cursor, f"{field}.teleportSlot{index}"
        )
        slots.append(value)
    teleport_timing, cursor = _enum(
        data, cursor, f"{field}.teleportTiming", {0, 4, 6}
    )
    return {
        "airWallShowTiming": air_wall_timing,
        "enemySpawnTiming": enemy_timing,
        "fadeInDuration": fade_in,
        "fadeOutDuration": fade_out,
        "hasFadeIn": has_in,
        "hasFadeOut": has_out,
        "operaSegments": opera,
        "teleportMode": teleport_mode,
        "teleportSlots": slots,
        "teleportTiming": teleport_timing,
    }, cursor


def _encounter_tail(
    data: bytes, cursor: int, field: str
) -> tuple[dict[str, Any], int]:
    fade_in, cursor = _f32(data, cursor, f"{field}.fadeInDuration")
    fade_out, cursor = _f32(data, cursor, f"{field}.fadeOutDuration")
    has_in, cursor = _bool(data, cursor, f"{field}.hasFadeIn")
    has_out, cursor = _bool(data, cursor, f"{field}.hasFadeOut")
    opera, cursor = _encounter_opera_segments(data, cursor, f"{field}.operaSegments")
    return {
        "fadeInDuration": fade_in,
        "fadeOutDuration": fade_out,
        "hasFadeIn": has_in,
        "hasFadeOut": has_out,
        "operaSegments": opera,
    }, cursor


def _parse_encounter(
    data: bytes, cursor: int, field: str
) -> tuple[dict[str, Any], int]:
    activate_mode, cursor = _enum(data, cursor, f"{field}.activateMode", {0, 1, 2})
    activate_mode_alter, cursor = _enum(
        data, cursor, f"{field}.activateModeAlter", {0, 1, 2}
    )
    activate_slot, cursor = _u32(data, cursor, f"{field}.activateTriggerSlotId")
    activate_slot_alter, cursor = _u32(
        data, cursor, f"{field}.activateTriggerSlotIdAlter"
    )
    air_walls, cursor = _list(data, cursor, f"{field}.airWallList", _u64_item)
    air_wall_ptrs, cursor = _list(
        data, cursor, f"{field}.airWallPtrList", _entity_ptr
    )
    battle, cursor = _nullable_member(
        data, cursor, f"{field}.battlePart", 8, _encounter_battle
    )
    enemies, cursor = _list(data, cursor, f"{field}.enemyList", _entity_ptr)
    intro, cursor = _nullable_member(
        data, cursor, f"{field}.introPart", 13, _encounter_intro
    )
    intro_alter, cursor = _nullable_member(
        data, cursor, f"{field}.introPartAlter", 13, _encounter_intro
    )
    intro_mode, cursor = _enum(data, cursor, f"{field}.introPartMode", {0, 1, 2})
    spawner_id, cursor = _u64(data, cursor, f"{field}.spawnerId")
    tail, cursor = _nullable_member(
        data, cursor, f"{field}.tailPart", 5, _encounter_tail
    )
    tail_mode, cursor = _enum(data, cursor, f"{field}.tailPartMode", {0, 1})
    return {
        "activateMode": activate_mode,
        "activateModeAlter": activate_mode_alter,
        "activateTriggerSlotId": activate_slot,
        "activateTriggerSlotIdAlter": activate_slot_alter,
        "airWallList": air_walls,
        "airWallPtrList": air_wall_ptrs,
        "battlePart": battle,
        "enemyList": enemies,
        "introPart": intro,
        "introPartAlter": intro_alter,
        "introPartMode": intro_mode,
        "spawnerId": str(spawner_id),
        "tailPart": tail,
        "tailPartMode": tail_mode,
    }, cursor


_PARSERS = {
    "EncounterData": (16, _parse_encounter),
    "FogNestControllerData": (7, _parse_fog_nest),
    "GhostWallModuleData": (27, _parse_ghost_wall),
    "GuideButterflyModuleData": (9, _parse_guide_butterfly),
    "SpecialSightControllerData": (4, _parse_special_sight),
    "SuperPressureBoardGroupData": (9, _parse_pressure_group),
    "TyphoeaArcheryUnitData": (8, _parse_typhoea_archery),
    "WaterProgressSyncData": (7, _parse_water_progress),
}
_SUPPORTED = {tag: _PARSERS[name] for tag, name in MODULE_TAG_NAMES.items()}


def _union_header(data: bytes, cursor: int, field: str) -> tuple[int, int, int]:
    _need(data, cursor, 1, f"{field}.tag")
    lead = data[cursor]
    if lead < 0xFA:
        return lead, cursor + 1, 1
    if lead == 0xFA:
        _need(data, cursor + 1, 2, f"{field}.wideTag")
        return struct.unpack_from("<H", data, cursor + 1)[0], cursor + 3, 3
    raise LevelScriptModuleCodecError(
        f"unsupported module union marker: offset={cursor} value=0x{lead:02x}"
    )


def decode_module_dictionary(
    data: bytes, cursor: int
) -> tuple[dict[str, Any] | None, int]:
    """Decode current supported module values or return ``None`` at the count."""
    start = cursor
    count, cursor = _count(data, cursor, "modules")
    if count is None:
        return {"status": "null", "count": None, "entries": None}, cursor
    entries = []
    seen: set[int] = set()
    for index in range(count):
        key, cursor = _u64(data, cursor, f"modules[{index}].key")
        if key in seen:
            raise LevelScriptModuleCodecError(f"duplicate module key: {key}")
        seen.add(key)
        tag, cursor, tag_width = _union_header(data, cursor, f"modules[{index}].value")
        supported = _SUPPORTED.get(tag)
        if supported is None:
            return None, start
        expected_count, parser = supported
        _need(data, cursor, 1, f"modules[{index}].value.memberCount")
        if data[cursor] != expected_count:
            raise LevelScriptModuleCodecError(
                f"invalid {MODULE_TAG_NAMES[tag]} member count: "
                f"offset={cursor} value={data[cursor]} expected={expected_count}"
            )
        cursor += 1
        disable, cursor = _bool(data, cursor, f"modules[{index}].value.disableWhenCompleted")
        module_id, cursor = _u64(data, cursor, f"modules[{index}].value.id")
        body, cursor = parser(data, cursor, f"modules[{index}].value")
        entries.append({
            "key": str(key),
            "tag": f"0x{tag:04x}",
            "tagWidth": tag_width,
            "type": MODULE_TAG_NAMES[tag],
            "serializedMemberCount": expected_count,
            "disableWhenCompleted": disable,
            "id": str(module_id),
            "fields": body,
        })
    return {
        "status": "present",
        "count": count,
        "entries": entries,
        "startOffset": start,
        "endOffset": cursor,
    }, cursor
