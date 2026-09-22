"""Exact current-wrapper codec for placed ``NpcRuntimeProxyData`` rows."""

from __future__ import annotations

from typing import Any, Callable

from scripts.game_data.atmospheric_npc_binary import (
    AtmosphericNpcFramingError,
    decode_level_entity_data,
)

from .memorypack import (
    read_bool,
    read_count,
    read_f32,
    read_f64,
    read_i32,
    read_i64,
    read_string,
    read_u32,
    read_u64,
)


class LevelNpcCodecError(ValueError):
    """Raised at the first unsupported or malformed NPC member."""


def _need(decoded: tuple[Any, int] | None, field: str) -> tuple[Any, int]:
    if decoded is None:
        raise LevelNpcCodecError(f"{field}: invalid or truncated value")
    return decoded


def _member(data: bytes, cursor: int, expected: int, field: str) -> int:
    if cursor >= len(data) or data[cursor] != expected:
        actual = data[cursor] if cursor < len(data) else None
        raise LevelNpcCodecError(
            f"{field}: member count mismatch expected={expected} actual={actual} offset={cursor}"
        )
    return cursor + 1


def _nullable_object(
    data: bytes,
    cursor: int,
    expected: int,
    field: str,
    body: Callable[[bytes, int, str], tuple[Any, int]],
) -> tuple[Any, int]:
    if cursor >= len(data):
        raise LevelNpcCodecError(f"{field}: truncated object marker")
    if data[cursor] == 0xFF:
        return None, cursor + 1
    cursor = _member(data, cursor, expected, field)
    return body(data, cursor, field)


def _list(
    data: bytes,
    cursor: int,
    field: str,
    item: Callable[[bytes, int, str], tuple[Any, int]],
) -> tuple[dict[str, Any], int]:
    start = cursor
    count, cursor = _need(read_count(data, cursor, max_count=100_000), field)
    values: list[Any] = []
    for index in range(max(0, count)):
        value, cursor = item(data, cursor, f"{field}[{index}]")
        values.append(value)
    return {
        "startOffset": start,
        "endOffset": cursor,
        "count": count,
        "value": None if count == -1 else values,
    }, cursor


def _string(data: bytes, cursor: int, field: str) -> tuple[str, int]:
    return _need(read_string(data, cursor, max_length=16_384), field)


def _i32(data: bytes, cursor: int, field: str) -> tuple[int, int]:
    return _need(read_i32(data, cursor), field)


def _i64(data: bytes, cursor: int, field: str) -> tuple[int, int]:
    return _need(read_i64(data, cursor), field)


def _u32(data: bytes, cursor: int, field: str) -> tuple[int, int]:
    return _need(read_u32(data, cursor), field)


def _u64(data: bytes, cursor: int, field: str) -> tuple[int, int]:
    value, cursor = _need(read_u64(data, cursor), field)
    return str(value), cursor


def _bool(data: bytes, cursor: int, field: str) -> tuple[bool, int]:
    return _need(read_bool(data, cursor), field)


def _f32(data: bytes, cursor: int, field: str) -> tuple[float, int]:
    return _need(read_f32(data, cursor), field)


def _vector3(data: bytes, cursor: int, field: str) -> tuple[list[float], int]:
    values: list[float] = []
    for axis in "xyz":
        value, cursor = _f32(data, cursor, f"{field}.{axis}")
        values.append(value)
    return values, cursor


def _gameplay_tag(data: bytes, cursor: int, field: str) -> tuple[int, int]:
    return _i32(data, cursor, field)


def _gameplay_tag_item(data: bytes, cursor: int, field: str) -> tuple[int, int]:
    cursor = _member(data, cursor, 1, field)
    return _i32(data, cursor, f"{field}.tagId")


def _lang_key(data: bytes, cursor: int, field: str) -> tuple[Any, int]:
    def body(blob: bytes, at: int, owner: str) -> tuple[Any, int]:
        key, at = _string(blob, at, f"{owner}.key")
        return {"key": key}, at
    return _nullable_object(data, cursor, 1, field, body)


def _string_item(data: bytes, cursor: int, field: str) -> tuple[str, int]:
    return _string(data, cursor, field)


def _i32_item(data: bytes, cursor: int, field: str) -> tuple[int, int]:
    return _i32(data, cursor, field)


def _u64_item(data: bytes, cursor: int, field: str) -> tuple[str, int]:
    return _u64(data, cursor, field)


def _collider_shape(data: bytes, cursor: int, field: str) -> tuple[dict[str, Any], int]:
    cursor = _member(data, cursor, 16, field)
    value: dict[str, Any] = {}
    value["center"], cursor = _vector3(data, cursor, f"{field}.center")
    for name in ("centerXKey", "centerYKey", "centerZKey"):
        value[name], cursor = _string(data, cursor, f"{field}.{name}")
    value["extent"], cursor = _vector3(data, cursor, f"{field}.extent")
    for name in ("extentXKey", "extentYKey", "extentZKey"):
        value[name], cursor = _string(data, cursor, f"{field}.{name}")
    value["height"], cursor = _f32(data, cursor, f"{field}.height")
    value["heightKey"], cursor = _string(data, cursor, f"{field}.heightKey")
    value["radius"], cursor = _f32(data, cursor, f"{field}.radius")
    value["radiusKey"], cursor = _string(data, cursor, f"{field}.radiusKey")
    value["rotationOffset"], cursor = _vector3(data, cursor, f"{field}.rotationOffset")
    value["shapeRaw"], cursor = _i32(data, cursor, f"{field}.shape")
    value["useCenterKey"], cursor = _bool(data, cursor, f"{field}.useCenterKey")
    value["useExtentKey"], cursor = _bool(data, cursor, f"{field}.useExtentKey")
    return {"memberCount": 16, **value}, cursor


def _blackboard_pair(data: bytes, cursor: int, field: str) -> tuple[dict[str, Any], int]:
    cursor = _member(data, cursor, 4, field)
    dynamic, cursor = _bool(data, cursor, f"{field}.isDynamic")
    key, cursor = _string(data, cursor, f"{field}.key")
    value_double, cursor = _need(read_f64(data, cursor), f"{field}.valueDouble")
    value_str, cursor = _string(data, cursor, f"{field}.valueStr")
    return {"isDynamic": dynamic, "key": key, "valueDouble": value_double, "valueStr": value_str}, cursor


def _skill_bb(data: bytes, cursor: int, field: str) -> tuple[dict[str, Any], int]:
    cursor = _member(data, cursor, 2, field)
    blackboard, cursor = _list(data, cursor, f"{field}.blackboard", _blackboard_pair)
    skill_id, cursor = _string(data, cursor, f"{field}.skillId")
    return {"blackboard": blackboard, "skillId": skill_id}, cursor


def _npc_battle_data_body(data: bytes, cursor: int, field: str) -> tuple[dict[str, Any], int]:
    active, cursor = _list(data, cursor, f"{field}.activeSkillId", _string_item)
    shape, cursor = _collider_shape(data, cursor, f"{field}.battleShapeData")
    blackboard, cursor = _list(data, cursor, f"{field}.blackboard", _skill_bb)
    passive, cursor = _list(data, cursor, f"{field}.passiveSkillId", _string_item)
    return {"activeSkillId": active, "battleShapeData": shape, "blackboard": blackboard, "passiveSkillId": passive}, cursor


def _entity_attract_body(data: bytes, cursor: int, field: str) -> tuple[dict[str, Any], int]:
    uuids, cursor = _list(data, cursor, f"{field}.attractPointUuids", _u64_item)
    find_next, cursor = _i32(data, cursor, f"{field}.findNextMethod")
    handle, cursor = _i32(data, cursor, f"{field}.handleExceptionMethod")
    linked, cursor = _u64(data, cursor, f"{field}.linkedAttractPoint")
    return {"attractPointUuids": uuids, "findNextMethodRaw": find_next, "handleExceptionMethodRaw": handle, "linkedAttractPoint": linked}, cursor


def _hit_data_body(data: bytes, cursor: int, field: str) -> tuple[dict[str, Any], int]:
    can_hit, cursor = _bool(data, cursor, f"{field}.canBeHit")
    center, cursor = _vector3(data, cursor, f"{field}.center")
    direction, cursor = _i32(data, cursor, f"{field}.direction")
    extent, cursor = _vector3(data, cursor, f"{field}.extent")
    height, cursor = _f32(data, cursor, f"{field}.height")
    effect, cursor = _string(data, cursor, f"{field}.hitEffect")
    radius, cursor = _f32(data, cursor, f"{field}.radius")
    shape, cursor = _i32(data, cursor, f"{field}.shape")
    return {"canBeHit": can_hit, "center": center, "directionRaw": direction, "extent": extent, "height": height, "hitEffect": effect, "radius": radius, "shapeRaw": shape}, cursor


def _ability_data_body(data: bytes, cursor: int, field: str) -> tuple[dict[str, Any], int]:
    enabled, cursor = _bool(data, cursor, f"{field}.enableAbilityOverride")
    look_ahead, cursor = _f32(data, cursor, f"{field}.lookAheadTime")
    reaction, cursor = _f32(data, cursor, f"{field}.reactionTime")
    return {"enableAbilityOverride": enabled, "lookAheadTime": look_ahead, "reactionTime": reaction}, cursor


def _env_talk_body(data: bytes, cursor: int, field: str) -> tuple[dict[str, Any], int]:
    ids, cursor = _list(data, cursor, f"{field}.envTalkIds", _string_item)
    odds, cursor = _list(data, cursor, f"{field}.envTalkOdd", _i32_item)
    override, cursor = _bool(data, cursor, f"{field}.envTalkOverrideNpc")
    return {"envTalkIds": ids, "envTalkOdd": odds, "envTalkOverrideNpc": override}, cursor


def _proxy_info_body(data: bytes, cursor: int, field: str) -> tuple[dict[str, Any], int]:
    values = {}
    for name in ("mapId", "npcId", "npcNameId"):
        values[name], cursor = _string(data, cursor, f"{field}.{name}")
    values["npcProxyTypeRaw"], cursor = _i32(data, cursor, f"{field}.npcProxyType")
    return values, cursor


def _runtime_data_body(data: bytes, cursor: int, field: str) -> tuple[dict[str, Any], int]:
    values = {}
    for name in ("enableMagicaCloth", "enableMorph"):
        values[name], cursor = _bool(data, cursor, f"{field}.{name}")
    values["headIcon"], cursor = _string(data, cursor, f"{field}.headIcon")
    values["interactRangeTypeRaw"], cursor = _i32(data, cursor, f"{field}.interactRangeType")
    for name in ("npcEntityId", "npcNameId", "templateID"):
        values[name], cursor = _string(data, cursor, f"{field}.{name}")
    return values, cursor


def _ai_instance_body(data: bytes, cursor: int, field: str) -> tuple[dict[str, Any], int]:
    value = {}
    value["floatValue"], cursor = _f32(data, cursor, f"{field}.floatValue")
    value["key"], cursor = _string(data, cursor, f"{field}.key")
    value["longValue"], cursor = _i64(data, cursor, f"{field}.longValue")
    value["stringValue"], cursor = _string(data, cursor, f"{field}.stringValue")
    value["valueTypeRaw"], cursor = _i32(data, cursor, f"{field}.valueType")
    value["vector3Value"], cursor = _vector3(data, cursor, f"{field}.vector3Value")
    return value, cursor


def _ai_dictionary(data: bytes, cursor: int, field: str) -> tuple[dict[str, Any], int]:
    start = cursor
    if cursor >= len(data):
        raise LevelNpcCodecError(f"{field}: truncated wrapper marker")
    if data[cursor] == 0xFF:
        return {"startOffset": start, "endOffset": cursor + 1, "count": -1, "value": None}, cursor + 1
    cursor = _member(data, cursor, 1, field)
    count, cursor = _need(read_count(data, cursor, max_count=100_000), field)
    rows = []
    keys = set()
    for index in range(max(0, count)):
        key, cursor = _string(data, cursor, f"{field}[{index}].key")
        if key in keys:
            raise LevelNpcCodecError(f"{field}: duplicate key {key!r}")
        keys.add(key)
        value, cursor = _nullable_object(data, cursor, 6, f"{field}[{index}].value", _ai_instance_body)
        rows.append({"key": key, "value": value})
    return {"startOffset": start, "endOffset": cursor, "count": count, "value": None if count == -1 else rows}, cursor


def _decode_level_npc_members(data: bytes, cursor: int, field: str) -> tuple[dict[str, Any], int]:
    value: dict[str, Any] = {}
    value["aiCfg"], cursor = _string(data, cursor, f"{field}.aiCfg")
    for name in ("atmosphereStimulateCanMove", "autoPreloadMontages"):
        value[name], cursor = _bool(data, cursor, f"{field}.{name}")
    value["battleAnim"], cursor = _gameplay_tag(data, cursor, f"{field}.battleAnim")
    value["battleData"], cursor = _nullable_object(data, cursor, 4, f"{field}.battleData", _npc_battle_data_body)
    value["battleDataOverride"], cursor = _bool(data, cursor, f"{field}.battleDataOverride")
    value["belongStoryZoneId"], cursor = _u64(data, cursor, f"{field}.belongStoryZoneId")
    value["blurPriority"], cursor = _i32(data, cursor, f"{field}.blurPriority")
    value["collisionEnable"], cursor = _bool(data, cursor, f"{field}.collisionEnable")
    value["confrontAnim"], cursor = _gameplay_tag(data, cursor, f"{field}.confrontAnim")
    for name in ("controlByLevelScript", "defaultActivePatrol"):
        value[name], cursor = _bool(data, cursor, f"{field}.{name}")
    for name in ("defaultEmotion", "defaultFacialAnim"):
        value[name], cursor = _gameplay_tag(data, cursor, f"{field}.{name}")
    value["defaultInteractText"], cursor = _lang_key(data, cursor, f"{field}.defaultInteractText")
    value["defaultMontage"], cursor = _gameplay_tag(data, cursor, f"{field}.defaultMontage")
    value["defaultMontageMaskTypeRaw"], cursor = _i32(data, cursor, f"{field}.defaultMontageMaskType")
    for name in (
        "disableDowngrade", "disableEmotion", "doPatrol", "doStim", "enableCloth",
        "enableDialogLookAtCapability", "enableDownGradeSpIdle", "enableMorph",
    ):
        value[name], cursor = _bool(data, cursor, f"{field}.{name}")
    value["entityAttractData"], cursor = _nullable_object(data, cursor, 4, f"{field}.entityAttractData", _entity_attract_body)
    value["envTalkIds"], cursor = _list(data, cursor, f"{field}.envTalkIds", _string_item)
    value["envTalkOdd"], cursor = _list(data, cursor, f"{field}.envTalkOdd", _i32_item)
    value["envTalkOverrideNpc"], cursor = _bool(data, cursor, f"{field}.envTalkOverrideNpc")
    value["envTalkTriggerDistance"], cursor = _f32(data, cursor, f"{field}.envTalkTriggerDistance")
    for name in ("hideHeadLabel", "hideHeadName"):
        value[name], cursor = _bool(data, cursor, f"{field}.{name}")
    value["hitData"], cursor = _nullable_object(data, cursor, 8, f"{field}.hitData", _hit_data_body)
    value["idleBreakTags"], cursor = _list(data, cursor, f"{field}.idleBreakTags", _gameplay_tag_item)
    for name in ("ifOverrideFaction", "ifOverrideNpcName", "ifOverrideTitle", "ignoreBattleReturn"):
        value[name], cursor = _bool(data, cursor, f"{field}.{name}")
    value["initPatrolIndex"], cursor = _i32(data, cursor, f"{field}.initPatrolIndex")
    value["interactionIcon"], cursor = _string(data, cursor, f"{field}.interactionIcon")
    value["interactRangeTypeRaw"], cursor = _i32(data, cursor, f"{field}.interactRangeType")
    value["isOverriderBlur"], cursor = _bool(data, cursor, f"{field}.isOverriderBlur")
    value["linkedChairId"], cursor = _u64(data, cursor, f"{field}.linkedChairId")
    value["lookAt"], cursor = _bool(data, cursor, f"{field}.lookAt")
    value["montageStateRaw"], cursor = _i32(data, cursor, f"{field}.montageState")
    for name in ("needBattleRot", "needBlurCheck", "needConfrontRot"):
        value[name], cursor = _bool(data, cursor, f"{field}.{name}")
    value["normalIdle2SpidleTime"], cursor = _f32(data, cursor, f"{field}.normalIdle2SpidleTime")
    value["notifyInteractEvent"], cursor = _bool(data, cursor, f"{field}.notifyInteractEvent")
    value["npcAbility"], cursor = _nullable_object(data, cursor, 3, f"{field}.npcAbility", _ability_data_body)
    for name in ("npcFaction", "npcGroupId", "npcId", "npcName"):
        value[name], cursor = _string(data, cursor, f"{field}.{name}")
    value["npcPatrolGroupId"], cursor = _u64(data, cursor, f"{field}.npcPatrolGroupId")
    value["npcTitle"], cursor = _string(data, cursor, f"{field}.npcTitle")
    for name in (
        "overrideBattleRot", "overrideConfrontRot", "overrideDefaultInteractIcon",
        "overrideDefaultInteractText",
    ):
        value[name], cursor = _bool(data, cursor, f"{field}.{name}")
    value["overrideHeadLabel"], cursor = _string(data, cursor, f"{field}.overrideHeadLabel")
    for name in ("overrideInteractRange", "overrideMontageState"):
        value[name], cursor = _bool(data, cursor, f"{field}.{name}")
    for name in ("overrideNpcFactionId", "overrideNpcNameId", "overrideNpcTitleId"):
        value[name], cursor = _lang_key(data, cursor, f"{field}.{name}")
    value["overrideSpIdleConfig"], cursor = _bool(data, cursor, f"{field}.overrideSpIdleConfig")
    value["patrolCfgTypeRaw"], cursor = _i32(data, cursor, f"{field}.patrolCfgType")
    value["patrolIdNew"], cursor = _i32(data, cursor, f"{field}.patrolId_New")
    value["preloadMontages"], cursor = _list(data, cursor, f"{field}.preloadMontages", _gameplay_tag_item)
    for name in ("spIdle2normalIdleTime", "spIdleRandomWaitTimeMax", "spIdleRandomWaitTimeMin"):
        value[name], cursor = _f32(data, cursor, f"{field}.{name}")
    for name in ("stimulateKey", "templateDataId"):
        value[name], cursor = _string(data, cursor, f"{field}.{name}")
    value["typeRaw"], cursor = _i32(data, cursor, f"{field}.type")
    return value, cursor


def _ex_data_item(data: bytes, cursor: int, field: str) -> tuple[Any, int]:
    if cursor >= len(data) or data[cursor] == 0xFF:
        if cursor < len(data):
            return None, cursor + 1
        raise LevelNpcCodecError(f"{field}: truncated")
    raise LevelNpcCodecError(f"{field}: positive NpcRuntimeProxyExData is not yet supported")


def _decode_runtime_members(data: bytes, cursor: int, field: str) -> tuple[dict[str, Any], int]:
    value: dict[str, Any] = {}
    value["clusterId"], cursor = _string(data, cursor, f"{field}.clusterId")
    value["exDatas"], cursor = _list(data, cursor, f"{field}.exDatas", _ex_data_item)
    for name in ("hideBubble", "hidePopupExpression", "ifOverrideHeadIcon", "lazyDestroy"):
        value[name], cursor = _bool(data, cursor, f"{field}.{name}")
    value["lazyDestroyEnvTalkData"], cursor = _nullable_object(data, cursor, 3, f"{field}.lazyDestroyEnvTalkData", _env_talk_body)
    value["lazyDestroyOverrideDialogId"], cursor = _string(data, cursor, f"{field}.lazyDestroyOverrideDialogId")
    value["lazyDestroyPatrolId"], cursor = _i32(data, cursor, f"{field}.lazyDestroyPatrolId")
    value["lazyDestroyStartPatrol"], cursor = _bool(data, cursor, f"{field}.lazyDestroyStartPatrol")
    value["levelId"], cursor = _string(data, cursor, f"{field}.levelId")
    value["needWayPoint"], cursor = _bool(data, cursor, f"{field}.needWayPoint")
    value["npcGamePlayDataKeyList"], cursor = _list(data, cursor, f"{field}.npcGamePlayDataKeyList", _string_item)
    value["npcInfoData"], cursor = _nullable_object(data, cursor, 4, f"{field}.npcInfoData", _proxy_info_body)
    value["npcRuntimeData"], cursor = _nullable_object(data, cursor, 7, f"{field}.npcRuntimeData", _runtime_data_body)
    value["overrideAbilitySo"], cursor = _string(data, cursor, f"{field}.overrideAbilitySo")
    value["overrideAIBehaviorDataDictionary"], cursor = _ai_dictionary(data, cursor, f"{field}.overrideAIBehaviorDataDictionary")
    for name in ("overrideAudio", "overrideGamePlayData"):
        value[name], cursor = _bool(data, cursor, f"{field}.{name}")
    value["overrideHeadIcon"], cursor = _string(data, cursor, f"{field}.overrideHeadIcon")
    value["overrideInitAudioId"], cursor = _u32(data, cursor, f"{field}.overrideInitAudioId")
    for name in ("overrideLabel", "overrideTemplateAi", "overrideTemplateAI"):
        value[name], cursor = _bool(data, cursor, f"{field}.{name}")
    value["proxyId"], cursor = _string(data, cursor, f"{field}.proxyId")
    value["sameShapeGroupId"], cursor = _u64(data, cursor, f"{field}.sameShapeGroupId")
    value["subDataParentId"], cursor = _u64(data, cursor, f"{field}.subDataParentId")
    return value, cursor


def _decode_npc_runtime_proxy_row(
    data: bytes, cursor: int, index: int
) -> tuple[dict[str, Any], int]:
    row_start = cursor
    try:
        cursor = _member(data, cursor, 118, f"npcs[{index}]")
        entity = decode_level_entity_data(data, cursor, len(data))
        cursor = int(entity["endOffset"])
        level_npc, cursor = _decode_level_npc_members(data, cursor, f"npcs[{index}]")
        runtime, cursor = _decode_runtime_members(data, cursor, f"npcs[{index}]")
    except AtmosphericNpcFramingError as exc:
        raise LevelNpcCodecError(str(exc)) from exc
    return ({
        "indexInCollection": index,
        "startOffset": row_start,
        "endOffset": cursor,
        "memberCount": 118,
        "levelEntityData": entity,
        "levelNpcData": level_npc,
        "npcRuntimeProxyData": runtime,
    }, cursor)


def decode_npc_runtime_proxy_row(data: bytes) -> dict[str, Any]:
    """Decode one exact ``NpcRuntimeProxyData`` value through physical EOF."""
    row, cursor = _decode_npc_runtime_proxy_row(data, 0, 0)
    if cursor != len(data):
        raise LevelNpcCodecError(
            f"npc runtime proxy row has trailing bytes: consumed={cursor} length={len(data)}"
        )
    row["fieldOrderSource"] = (
        "current generated MemoryPack wrapper inheritance and setter order"
    )
    row["evidenceBoundary"] = (
        "exact sequential 118-member NpcRuntimeProxyData row through physical EOF; "
        "unsupported positive nested variants fail closed"
    )
    return row


def decode_npc_runtime_proxy_list(data: bytes, offset: int) -> dict[str, Any] | None:
    """Decode ``List<NpcRuntimeProxyData>`` in its 118-member flattened order."""
    start = offset
    count_decoded = read_count(data, offset, max_count=100_000)
    if count_decoded is None:
        return None
    count, cursor = count_decoded
    rows = []
    for index in range(max(0, count)):
        row, cursor = _decode_npc_runtime_proxy_row(data, cursor, index)
        rows.append(row)
    return {
        "startOffset": start,
        "endOffset": cursor,
        "count": count,
        "value": None if count == -1 else rows,
        "rows": rows,
        "memberPartition": [14, 77, 27],
        "fieldOrderSource": "current generated MemoryPack wrapper inheritance and setter order",
        "evidenceBoundary": "exact sequential 118-member NpcRuntimeProxyData rows; unsupported positive nested variants fail closed",
    }
