"""Exact current ``Dictionary<uint, LevelEnemyData>`` codec."""

from __future__ import annotations

import math
import struct
from typing import Any

from scripts.game_data.codecs.levelscript import interactives as primitive


class LevelEnemyCodecError(ValueError):
    """Raised when a declared enemy value cannot advance exactly."""


_PLAY_MODES = {-1: "None", 0: "Default", 1: "Anim", 2: "Skill"}
_PATROL_CONFIG_TYPES = {0: "Patrol", 1: "DoAction", 3: "ActionSequenceId"}


def _call(function, data: bytes, cursor: int, field: str):
    try:
        return function(data, cursor, field)
    except primitive.LevelInteractiveCodecError as error:
        raise LevelEnemyCodecError(str(error)) from error


def _count(data: bytes, cursor: int, field: str):
    return _call(primitive._count, data, cursor, field)


def _i32(data: bytes, cursor: int, field: str):
    return _call(primitive._i32, data, cursor, field)


def _u32(data: bytes, cursor: int, field: str):
    return _call(primitive._u32, data, cursor, field)


def _u64(data: bytes, cursor: int, field: str):
    return _call(primitive._u64, data, cursor, field)


def _bool(data: bytes, cursor: int, field: str):
    return _call(primitive._bool, data, cursor, field)


def _f32(data: bytes, cursor: int, field: str):
    return _call(primitive._f32, data, cursor, field)


def _string(data: bytes, cursor: int, field: str):
    return _call(primitive._string, data, cursor, field)


def _member(data: bytes, cursor: int, expected: int, field: str) -> int:
    if cursor >= len(data):
        raise LevelEnemyCodecError(f"truncated {field}.memberCount: offset={cursor}")
    actual = data[cursor]
    if actual != expected:
        raise LevelEnemyCodecError(
            f"invalid {field} member count: offset={cursor} value={actual} expected={expected}"
        )
    return cursor + 1


def _string_list(data: bytes, cursor: int, field: str) -> tuple[dict[str, Any], int]:
    count, cursor = _count(data, cursor, field)
    if count is None:
        return {"status": "null", "count": None, "values": None}, cursor
    values = []
    for index in range(count):
        value, cursor = _string(data, cursor, f"{field}[{index}]")
        values.append(value)
    return {"status": "present", "count": count, "values": values}, cursor


def _born_behavior(data: bytes, cursor: int, field: str) -> tuple[Any, int]:
    if cursor >= len(data):
        raise LevelEnemyCodecError(f"truncated {field}: offset={cursor}")
    if data[cursor] == 0xFF:
        return None, cursor + 1
    cursor = _member(data, cursor, 18, field)
    value: dict[str, Any] = {}
    value["bornCanInterrupt"], cursor = _bool(data, cursor, f"{field}.bornCanInterrupt")
    value["canInterruptTime"], cursor = _f32(data, cursor, f"{field}.canInterruptTime")
    value["desc"], cursor = _string(data, cursor, f"{field}.desc")
    value["enterAnimId"], cursor = _string(data, cursor, f"{field}.enterAnimId")
    value["enterAnimSpeed"], cursor = _f32(data, cursor, f"{field}.enterAnimSpeed")
    value["enterBuffId"], cursor = _string(data, cursor, f"{field}.enterBuffId")
    for name in ("enterMode",):
        raw, cursor = _i32(data, cursor, f"{field}.{name}")
        if raw not in _PLAY_MODES:
            raise LevelEnemyCodecError(f"invalid {field}.{name}: value={raw}")
        value[name] = {"raw": raw, "name": _PLAY_MODES[raw]}
    value["enterRepeat"], cursor = _bool(data, cursor, f"{field}.enterRepeat")
    value["enterRootMotion"], cursor = _bool(data, cursor, f"{field}.enterRootMotion")
    value["enterSkillId"], cursor = _string(data, cursor, f"{field}.enterSkillId")
    value["exitAnimId"], cursor = _string(data, cursor, f"{field}.exitAnimId")
    value["exitAnimSpeed"], cursor = _f32(data, cursor, f"{field}.exitAnimSpeed")
    value["exitBuffId"], cursor = _string(data, cursor, f"{field}.exitBuffId")
    raw, cursor = _i32(data, cursor, f"{field}.exitMode")
    if raw not in _PLAY_MODES:
        raise LevelEnemyCodecError(f"invalid {field}.exitMode: value={raw}")
    value["exitMode"] = {"raw": raw, "name": _PLAY_MODES[raw]}
    value["exitRootMotion"], cursor = _bool(data, cursor, f"{field}.exitRootMotion")
    value["exitSkillId"], cursor = _string(data, cursor, f"{field}.exitSkillId")
    value["randomExitAnimId"], cursor = _bool(data, cursor, f"{field}.randomExitAnimId")
    value["randomExitAnimIds"], cursor = _string_list(
        data, cursor, f"{field}.randomExitAnimIds"
    )
    return value, cursor


def _blackboard_pair(data: bytes, cursor: int, field: str) -> tuple[dict[str, Any], int]:
    cursor = _member(data, cursor, 4, field)
    value: dict[str, Any] = {}
    value["key"], cursor = _string(data, cursor, f"{field}.key")
    value["useString"], cursor = _bool(data, cursor, f"{field}.useString")
    value["valueFloat"], cursor = _f32(data, cursor, f"{field}.valueFloat")
    value["valueString"], cursor = _string(data, cursor, f"{field}.valueString")
    return value, cursor


def _buff(data: bytes, cursor: int, field: str) -> tuple[dict[str, Any], int]:
    cursor = _member(data, cursor, 2, field)
    pair_count, cursor = _count(data, cursor, f"{field}.blackboard")
    pairs = None
    if pair_count is not None:
        pairs = []
        for index in range(pair_count):
            pair, cursor = _blackboard_pair(
                data, cursor, f"{field}.blackboard[{index}]"
            )
            pairs.append(pair)
    buff_id, cursor = _string(data, cursor, f"{field}.buffId")
    return {
        "blackboard": {"count": pair_count, "values": pairs},
        "buffId": buff_id,
    }, cursor


def _buff_list(data: bytes, cursor: int, field: str) -> tuple[dict[str, Any], int]:
    count, cursor = _count(data, cursor, field)
    if count is None:
        return {"status": "null", "count": None, "values": None}, cursor
    values = []
    for index in range(count):
        value, cursor = _buff(data, cursor, f"{field}[{index}]")
        values.append(value)
    return {"status": "present", "count": count, "values": values}, cursor


def _nullable_float(data: bytes, cursor: int, field: str) -> tuple[float | None, int]:
    # The selected current formatter reads the eight-byte native Nullable<float>
    # representation in one cursor operation: float, hasValue, then three padding bytes.
    if cursor + 8 > len(data):
        raise LevelEnemyCodecError(f"truncated {field}: offset={cursor} size=8")
    value = struct.unpack_from("<f", data, cursor)[0]
    has_value = data[cursor + 4]
    padding = data[cursor + 5 : cursor + 8]
    if has_value not in (0, 1) or padding != b"\0\0\0":
        raise LevelEnemyCodecError(
            f"invalid {field} nullable layout: offset={cursor} hasValue={has_value} padding={padding.hex()}"
        )
    if has_value and not math.isfinite(value):
        raise LevelEnemyCodecError(f"non-finite {field}: offset={cursor} value={value!r}")
    return value if has_value else None, cursor + 8


def _override_attr(data: bytes, cursor: int, field: str) -> tuple[Any, int]:
    if cursor >= len(data):
        raise LevelEnemyCodecError(f"truncated {field}: offset={cursor}")
    if data[cursor] == 0xFF:
        return None, cursor + 1
    cursor = _member(data, cursor, 3, field)
    value = {}
    for name in ("innerCircleRange", "longSightRange", "shortSightRange"):
        value[name], cursor = _f32(data, cursor, f"{field}.{name}")
    return value, cursor


def _enemy(data: bytes, cursor: int, field: str) -> tuple[dict[str, Any], int]:
    cursor = _member(data, cursor, 30, field)
    value: dict[str, Any] = {}
    value["aoiRadiusLevel"], cursor = _i32(data, cursor, f"{field}.aoiRadiusLevel")
    value["belongToLevelScriptId"], cursor = _u64(data, cursor, f"{field}.belongToLevelScriptId")
    value["createState"], cursor = _i32(data, cursor, f"{field}.createState")
    value["dependencyLevelScriptId"], cursor = _u64(data, cursor, f"{field}.dependencyLevelScriptId")
    value["entityDataIdKey"], cursor = _string(data, cursor, f"{field}.entityDataIdKey")
    value["entityType"], cursor = _i32(data, cursor, f"{field}.entityType")
    value["forceLoad"], cursor = _bool(data, cursor, f"{field}.forceLoad")
    value["keepOnLevelReload"], cursor = _bool(data, cursor, f"{field}.keepOnLevelReload")
    value["levelLogicId"], cursor = _u64(data, cursor, f"{field}.levelLogicId")
    value["overrideSendDieEvent"], cursor = _bool(data, cursor, f"{field}.overrideSendDieEvent")
    transform = {}
    for group in ("position", "rotation", "scale"):
        transform[group] = []
        for axis in "xyz":
            component, cursor = _f32(data, cursor, f"{field}.{group}.{axis}")
            transform[group].append(component)
    value["transform"] = transform
    value["sendDieEvent"], cursor = _bool(data, cursor, f"{field}.sendDieEvent")

    ai_count, cursor = _count(data, cursor, f"{field}.aiBlackboard")
    if ai_count is not None:
        raise LevelEnemyCodecError(
            f"unsupported positive {field}.aiBlackboard count={ai_count}"
        )
    value["aiBlackboard"] = None
    value["bornBehaviorData"], cursor = _born_behavior(
        data, cursor, f"{field}.bornBehaviorData"
    )
    value["bornTemplateId"], cursor = _string(data, cursor, f"{field}.bornTemplateId")
    value["buffs"], cursor = _buff_list(data, cursor, f"{field}.buffs")
    action_type, cursor = _i32(data, cursor, f"{field}.enemyDefaultActionType")
    if action_type != 0:
        raise LevelEnemyCodecError(
            f"invalid {field}.enemyDefaultActionType: value={action_type}"
        )
    value["enemyDefaultActionType"] = {"raw": 0, "name": "Patrol"}
    value["enemyGroupId"], cursor = _i32(data, cursor, f"{field}.enemyGroupId")
    value["enemyPatrolId"], cursor = _u64(data, cursor, f"{field}.enemyPatrolId")
    value["extraDelayToRecycleTime"], cursor = _nullable_float(
        data, cursor, f"{field}.extraDelayToRecycleTime"
    )
    value["idleBreakAnimations"], cursor = _string_list(
        data, cursor, f"{field}.idleBreakAnimations"
    )
    value["isDangerousEnemy"], cursor = _bool(data, cursor, f"{field}.isDangerousEnemy")
    value["level"], cursor = _i32(data, cursor, f"{field}.level")
    value["overrideAIAttrData"], cursor = _override_attr(
        data, cursor, f"{field}.overrideAIAttrData"
    )
    value["overrideAIConfig"], cursor = _string(data, cursor, f"{field}.overrideAIConfig")
    value["overrideIdleBreak"], cursor = _bool(data, cursor, f"{field}.overrideIdleBreak")
    patrol_type, cursor = _i32(data, cursor, f"{field}.patrolCfgType")
    if patrol_type not in _PATROL_CONFIG_TYPES:
        raise LevelEnemyCodecError(f"invalid {field}.patrolCfgType: value={patrol_type}")
    value["patrolCfgType"] = {
        "raw": patrol_type,
        "name": _PATROL_CONFIG_TYPES[patrol_type],
    }
    value["respawnable"], cursor = _bool(data, cursor, f"{field}.respawnable")
    return value, cursor


def decode_enemy_dictionary(
    data: bytes, cursor: int
) -> tuple[dict[str, Any] | None, int]:
    """Decode the current enemy dictionary and return its exact next cursor."""
    start = cursor
    count, cursor = _count(data, cursor, "enemies")
    if count is None:
        return {"status": "null", "count": None, "entries": None}, cursor
    if count and (cursor + 5 > len(data) or data[cursor + 4] != 30):
        return None, start
    entries = []
    seen: set[int] = set()
    for index in range(count):
        key, cursor = _u32(data, cursor, f"enemies[{index}].key")
        if key in seen:
            raise LevelEnemyCodecError(f"duplicate enemies key: {key}")
        seen.add(key)
        value, cursor = _enemy(data, cursor, f"enemies[{key}]")
        entries.append({"key": key, "value": value})
    return {
        "status": "present",
        "count": count,
        "entries": entries,
        "startOffset": start,
        "endOffset": cursor,
    }, cursor


def decode_enemy_list(
    data: bytes, cursor: int
) -> tuple[dict[str, Any] | None, int]:
    """Decode the current ``List<LevelEnemyData>`` representation.

    LevelScript stores the same generated 30-member value behind dictionary
    keys, while LevelData stores it directly in its ``enemies`` list.  Keeping
    the value codec shared prevents the two owners from acquiring subtly
    different field orders.
    """
    start = cursor
    count, cursor = _count(data, cursor, "enemies")
    if count is None:
        return {"status": "null", "count": None, "values": None,
                "startOffset": start, "endOffset": cursor}, cursor
    values: list[dict[str, Any] | None] = []
    for index in range(count):
        if cursor >= len(data):
            raise LevelEnemyCodecError(
                f"truncated enemies[{index}]: offset={cursor}"
            )
        if data[cursor] == 0xFF:
            values.append(None)
            cursor += 1
            continue
        value, cursor = _enemy(data, cursor, f"enemies[{index}]")
        values.append(value)
    return {
        "status": "present",
        "count": count,
        "values": values,
        "startOffset": start,
        "endOffset": cursor,
        "itemFieldOrder": [
            "aoiRadiusLevel", "belongToLevelScriptId", "createState",
            "dependencyLevelScriptId", "entityDataIdKey", "entityType",
            "forceLoad", "keepOnLevelReload", "levelLogicId",
            "overrideSendDieEvent", "position", "rotation", "scale",
            "sendDieEvent", "aiBlackboard", "bornBehaviorData",
            "bornTemplateId", "buffs", "enemyDefaultActionType",
            "enemyGroupId", "enemyPatrolId", "extraDelayToRecycleTime",
            "idleBreakAnimations", "isDangerousEnemy", "level",
            "overrideAIAttrData", "overrideAIConfig", "overrideIdleBreak",
            "patrolCfgType", "respawnable",
        ],
        "fieldOrderSource": "current generated LevelEnemyData wrapper",
    }, cursor
