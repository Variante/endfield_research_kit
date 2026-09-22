"""Exact MemoryPack codecs for ``LevelFunctionAreaData`` nested collections."""

from __future__ import annotations

from typing import Any, Callable

from scripts.game_data.codecs.leveldata.memorypack import (
    read_bool,
    read_count,
    read_f32,
    read_i32,
    read_string,
    read_u32,
    read_u64,
)


class LevelFunctionAreaCodecError(ValueError):
    """Raised when a function-area wrapper cannot be advanced exactly."""


def _decoded(value: Any, field: str, offset: int) -> tuple[Any, int]:
    if value is None:
        raise LevelFunctionAreaCodecError(f"{field}: invalid value at offset={offset}")
    return value


def _member(data: bytes, cursor: int, expected: int, field: str) -> int:
    if cursor >= len(data) or data[cursor] != expected:
        actual = data[cursor] if cursor < len(data) else None
        raise LevelFunctionAreaCodecError(
            f"{field}: member count mismatch at offset={cursor}: expected={expected} actual={actual}"
        )
    return cursor + 1


def _i32(data: bytes, cursor: int, field: str) -> tuple[int, int]:
    return _decoded(read_i32(data, cursor), field, cursor)


def _u32(data: bytes, cursor: int, field: str) -> tuple[int, int]:
    return _decoded(read_u32(data, cursor), field, cursor)


def _u64(data: bytes, cursor: int, field: str) -> tuple[int, int]:
    return _decoded(read_u64(data, cursor), field, cursor)


def _f32(data: bytes, cursor: int, field: str) -> tuple[float, int]:
    return _decoded(read_f32(data, cursor), field, cursor)


def _bool(data: bytes, cursor: int, field: str) -> tuple[bool, int]:
    return _decoded(read_bool(data, cursor), field, cursor)


def _string(data: bytes, cursor: int, field: str) -> tuple[str, int]:
    return _decoded(read_string(data, cursor, max_length=16_384), field, cursor)


def _count(data: bytes, cursor: int, field: str) -> tuple[int | None, int]:
    count, cursor = _decoded(read_count(data, cursor, max_count=100_000), field, cursor)
    return (None if count == -1 else count), cursor


def _vector3(data: bytes, cursor: int, field: str) -> tuple[list[float], int]:
    values = []
    for axis in "xyz":
        value, cursor = _f32(data, cursor, f"{field}.{axis}")
        values.append(value)
    return values, cursor


def _list(
    data: bytes,
    cursor: int,
    field: str,
    item_decoder: Callable[[bytes, int, str], tuple[Any, int]],
) -> tuple[dict[str, Any], int]:
    start = cursor
    count, cursor = _count(data, cursor, field)
    if count is None:
        return {"startOffset": start, "endOffset": cursor, "count": -1, "value": None}, cursor
    rows = []
    for index in range(count):
        value, cursor = item_decoder(data, cursor, f"{field}[{index}]")
        rows.append(value)
    return {"startOffset": start, "endOffset": cursor, "count": count, "rows": rows}, cursor


def _string_item(data: bytes, cursor: int, field: str) -> tuple[str, int]:
    return _string(data, cursor, field)


def _u64_item(data: bytes, cursor: int, field: str) -> tuple[str, int]:
    value, cursor = _u64(data, cursor, field)
    return str(value), cursor


def _vector3_item(data: bytes, cursor: int, field: str) -> tuple[list[float], int]:
    return _vector3(data, cursor, field)


def _lang_key(data: bytes, cursor: int, field: str) -> tuple[dict[str, Any] | None, int]:
    start = cursor
    if cursor >= len(data):
        raise LevelFunctionAreaCodecError(f"{field}: truncated marker at offset={cursor}")
    if data[cursor] == 0xFF:
        return None, cursor + 1
    cursor = _member(data, cursor, 1, field)
    key, cursor = _string(data, cursor, f"{field}.key")
    return {"startOffset": start, "endOffset": cursor, "key": key}, cursor


def decode_condition_runtime(
    data: bytes, cursor: int, field: str, *, depth: int = 0
) -> tuple[dict[str, Any], int]:
    """Decode the current condition tags reached by function-area records."""

    if depth > 16:
        raise LevelFunctionAreaCodecError(f"{field}: condition nesting exceeds 16")
    start = cursor
    if cursor + 2 > len(data):
        raise LevelFunctionAreaCodecError(f"{field}: truncated union header at offset={cursor}")
    tag = data[cursor]
    member_count = data[cursor + 1]
    cursor += 2
    if tag == 0 and member_count == 3:
        operator, cursor = _i32(data, cursor, f"{field}.conditionOperator")
        reverse, cursor = _bool(data, cursor, f"{field}.reverse")
        sub_conditions, cursor = _list(
            data,
            cursor,
            f"{field}.subConditions",
            lambda body, offset, name: decode_condition_runtime(
                body, offset, name, depth=depth + 1
            ),
        )
        if sub_conditions["count"] in (-1, 0):
            raise LevelFunctionAreaCodecError(f"{field}: combined condition has no subconditions")
        return {
            "startOffset": start,
            "endOffset": cursor,
            "unionTag": tag,
            "conditionType": "CombinedConditionRuntime",
            "serializedMemberCount": member_count,
            "conditionOperator": operator,
            "reverse": reverse,
            "subConditions": sub_conditions,
        }, cursor
    if tag == 11 and member_count == 1:
        mission_id, cursor = _string(data, cursor, f"{field}.missionId")
        return {
            "startOffset": start,
            "endOffset": cursor,
            "unionTag": tag,
            "conditionType": "SimpleConditionCheckMissionNotPaused",
            "serializedMemberCount": member_count,
            "missionId": mission_id,
        }, cursor
    if tag == 8 and member_count == 3:
        compare_operator, cursor = _i32(data, cursor, f"{field}.compareOperator")
        compare_target, cursor = _i32(data, cursor, f"{field}.compareTarget")
        global_var_name, cursor = _string(data, cursor, f"{field}.globalVarName")
        return {
            "startOffset": start,
            "endOffset": cursor,
            "unionTag": tag,
            "conditionType": "SimpleConditionCheckGlobalVar",
            "serializedMemberCount": member_count,
            "compareOperator": compare_operator,
            "compareTarget": compare_target,
            "globalVarName": global_var_name,
        }, cursor
    if tag in (12, 17) and member_count == 3:
        compare_operator, cursor = _i32(data, cursor, f"{field}.compareOperator")
        compare_target, cursor = _i32(data, cursor, f"{field}.compareTarget")
        owner_id, cursor = _string(data, cursor, f"{field}.ownerId")
        return {
            "startOffset": start,
            "endOffset": cursor,
            "unionTag": tag,
            "conditionType": (
                "SimpleConditionCheckMissionState"
                if tag == 12
                else "SimpleConditionCheckQuestState"
            ),
            "serializedMemberCount": member_count,
            "compareOperator": compare_operator,
            "compareTarget": compare_target,
            "ownerId": owner_id,
        }, cursor
    raise LevelFunctionAreaCodecError(
        f"{field}: unsupported condition at offset={start}: tag={tag} memberCount={member_count}"
    )


def _condition_data(data: bytes, cursor: int, field: str) -> tuple[dict[str, Any], int]:
    start = cursor
    cursor = _member(data, cursor, 2, field)
    condition, cursor = decode_condition_runtime(data, cursor, f"{field}.conditionRuntimeBase")
    unique_id, cursor = _u64(data, cursor, f"{field}.uniqueId")
    return {
        "startOffset": start,
        "endOffset": cursor,
        "serializedMemberCount": 2,
        "conditionRuntimeBase": condition,
        "uniqueId": str(unique_id),
    }, cursor


def decode_function_area_condition_list(data: bytes, cursor: int) -> dict[str, Any]:
    """Decode one exact ``List<LevelFunctionAreaData.ConditionData>``."""

    value, _ = _list(data, cursor, "functionAreaConditions", _condition_data)
    return value


def _scene_toast_runtime_entry(
    data: bytes, cursor: int, field: str
) -> tuple[dict[str, Any], int]:
    start = cursor
    cursor = _member(data, cursor, 6, field)
    condition, cursor = decode_condition_runtime(data, cursor, f"{field}.condition")
    depth_text, cursor = _lang_key(data, cursor, f"{field}.depthText")
    entry_local_id, cursor = _i32(data, cursor, f"{field}.entryLocalId")
    main_title, cursor = _lang_key(data, cursor, f"{field}.mainTitle")
    save_id, cursor = _i32(data, cursor, f"{field}.saveId")
    sub_title, cursor = _lang_key(data, cursor, f"{field}.subTitle")
    return {
        "startOffset": start,
        "endOffset": cursor,
        "serializedMemberCount": 6,
        "condition": condition,
        "depthText": depth_text,
        "entryLocalId": entry_local_id,
        "mainTitle": main_title,
        "saveId": save_id,
        "subTitle": sub_title,
    }, cursor


def _specific_data(data: bytes, cursor: int, field: str) -> tuple[dict[str, Any], int]:
    start = cursor
    if cursor + 2 > len(data):
        raise LevelFunctionAreaCodecError(f"{field}: truncated union header at offset={cursor}")
    tag = data[cursor]
    member_count = data[cursor + 1]
    cursor += 2
    result: dict[str, Any] = {
        "startOffset": start,
        "unionTag": tag,
        "serializedMemberCount": member_count,
    }

    if tag == 0 and member_count == 20:
        result["specificDataType"] = "AmbienceCameraData"
        for name, kind in (
            ("blendInStyle", "i32"), ("blendInTime", "f32"),
            ("blendOutStyle", "i32"), ("blendOutTime", "f32"),
            ("duration", "f32"), ("enableHorizontalLimit", "bool"),
            ("enableVerticalLimit", "bool"), ("enableZoomLimit", "bool"),
            ("initialHorizontalAngle", "f32"), ("initialVerticalValue", "f32"),
            ("maxHorizontalAngle", "f32"), ("maxVerticalValue", "f32"),
            ("maxZoom", "f32"), ("minHorizontalAngle", "f32"),
            ("minVerticalValue", "f32"), ("minZoom", "f32"),
            ("screenX", "f32"), ("screenY", "f32"),
            ("useInitialParam", "bool"), ("useLocalRotation", "bool"),
        ):
            result[name], cursor = {"i32": _i32, "f32": _f32, "bool": _bool}[kind](
                data, cursor, f"{field}.{name}"
            )
    elif tag == 1 and member_count == 1:
        result["specificDataType"] = "BlightMiasmaAreaData"
        result["areaLevel"], cursor = _i32(data, cursor, f"{field}.areaLevel")
    elif tag == 2 and member_count == 1:
        result["specificDataType"] = "BlockAIBarkData"
        result["defaultOn"], cursor = _bool(data, cursor, f"{field}.defaultOn")
    elif tag == 3 and member_count == 11:
        result["specificDataType"] = "CameraAddControlStateData"
        for name, kind in (
            ("blendInStyle", "i32"), ("blendInTime", "f32"),
            ("blendOutStyle", "i32"), ("blendOutTime", "f32"),
            ("multipleCCS", "bool"), ("overrideBlendIn", "bool"),
            ("overrideBlendOut", "bool"), ("state2CheckAngle", "f32"),
            ("state2Config", "string"), ("stateCheckAngle", "f32"),
            ("stateConfig", "string"),
        ):
            result[name], cursor = {
                "i32": _i32, "f32": _f32, "bool": _bool, "string": _string
            }[kind](data, cursor, f"{field}.{name}")
    elif tag == 4 and member_count == 13:
        result["specificDataType"] = "CameraLookAtData"
        for name, kind in (
            ("blendInStyle", "i32"), ("blendInTime", "f32"),
            ("blendOutStyle", "i32"), ("blendOutTime", "f32"),
            ("duration", "f32"), ("horizontalSpeedFactor", "f32"),
            ("lookAtRotationPitch", "f32"), ("lookAtRotationYaw", "f32"),
            ("useLocalRotation", "bool"), ("useVerticalValue", "bool"),
            ("verticalSpeedFactor", "f32"), ("verticalValue", "f32"),
            ("zoomScale", "f32"),
        ):
            result[name], cursor = {"i32": _i32, "f32": _f32, "bool": _bool}[kind](
                data, cursor, f"{field}.{name}"
            )
    elif tag == 5 and member_count == 12:
        result["specificDataType"] = "CameraVolumeData"
        result["blendStyle"], cursor = _i32(data, cursor, f"{field}.blendStyle")
        result["duration"], cursor = _f32(data, cursor, f"{field}.duration")
        result["fov"], cursor = _f32(data, cursor, f"{field}.fov")
        value, cursor = _u64(data, cursor, f"{field}.id")
        result["id"] = str(value)
        result["needInterruptMainHudAction"], cursor = _bool(data, cursor, f"{field}.needInterruptMainHudAction")
        result["overrideBlend"], cursor = _bool(data, cursor, f"{field}.overrideBlend")
        result["pos"], cursor = _vector3(data, cursor, f"{field}.pos")
        result["rot"], cursor = _vector3(data, cursor, f"{field}.rot")
        result["tweenTime"], cursor = _f32(data, cursor, f"{field}.tweenTime")
        result["useBlackScreen"], cursor = _bool(data, cursor, f"{field}.useBlackScreen")
        result["useOnce"], cursor = _bool(data, cursor, f"{field}.useOnce")
        result["useYawCheck"], cursor = _bool(data, cursor, f"{field}.useYawCheck")
    elif tag == 6 and member_count == 1:
        result["specificDataType"] = "CarryTagZoneData"
        result["zoneTag"], cursor = _u32(data, cursor, f"{field}.zoneTag")
    elif tag == 7 and member_count == 2:
        result["specificDataType"] = "DitherFactoryZoneData"
        result["center"], cursor = _vector3(data, cursor, f"{field}.center")
        result["size"], cursor = _vector3(data, cursor, f"{field}.size")
    elif tag == 9 and member_count == 4:
        result["specificDataType"] = "HideEntityByTypeParams"
        result["entityTypes"], cursor = _i32(data, cursor, f"{field}.entityTypes")
        result["logicIdWhitelist"], cursor = _list(data, cursor, f"{field}.logicIdWhitelist", _u64_item)
        result["npcTypes"], cursor = _i32(data, cursor, f"{field}.npcTypes")
        result["proxyWhitelist"], cursor = _list(data, cursor, f"{field}.proxyWhitelist", _string_item)
    elif tag == 10 and member_count == 7:
        result["specificDataType"] = "RadioTriggerZoneData"
        for name in ("hideAfterMissionId", "hideBeforeMissionId", "hideCompleteMissionId", "prtsId", "radioId"):
            result[name], cursor = _string(data, cursor, f"{field}.{name}")
        value, cursor = _u64(data, cursor, f"{field}.triggerId")
        result["triggerId"] = str(value)
        result["useRadioTriggerOnce"], cursor = _bool(data, cursor, f"{field}.useRadioTriggerOnce")
    elif tag == 11 and member_count == 2:
        result["specificDataType"] = "RepatriateZoneData"
        result["lifeRatio"], cursor = _f32(data, cursor, f"{field}.lifeRatio")
        result["useRepatriateZoneType"], cursor = _bool(data, cursor, f"{field}.useRepatriateZoneType")
    elif tag == 13 and member_count == 6:
        result["specificDataType"] = "SceneToastUIData"
        result["conditionalEntries"], cursor = _list(
            data, cursor, f"{field}.conditionalEntries", _scene_toast_runtime_entry
        )
        result["depthText"], cursor = _lang_key(data, cursor, f"{field}.depthText")
        result["mainTitle"], cursor = _lang_key(data, cursor, f"{field}.mainTitle")
        result["priority"], cursor = _i32(data, cursor, f"{field}.priority")
        result["saveId"], cursor = _i32(data, cursor, f"{field}.saveId")
        result["subTitle"], cursor = _lang_key(data, cursor, f"{field}.subTitle")
    elif tag == 14 and member_count == 6:
        result["specificDataType"] = "StopTeammateFollowZoneData"
        result["enterSummonRadius"], cursor = _f32(data, cursor, f"{field}.enterSummonRadius")
        result["inOutZoneTolerance"], cursor = _f32(data, cursor, f"{field}.inOutZoneTolerance")
        result["specifyTeammatePositions"], cursor = _bool(data, cursor, f"{field}.specifyTeammatePositions")
        result["specifyTeammateRotations"], cursor = _bool(data, cursor, f"{field}.specifyTeammateRotations")
        result["teammateLookAtPoints"], cursor = _list(data, cursor, f"{field}.teammateLookAtPoints", _vector3_item)
        result["teammatePositions"], cursor = _list(data, cursor, f"{field}.teammatePositions", _vector3_item)
    elif tag == 15 and member_count == 4:
        result["specificDataType"] = "StorySafeZone"
        result["defaultOn"], cursor = _bool(data, cursor, f"{field}.defaultOn")
        result["npcProxyIds"], cursor = _list(data, cursor, f"{field}.npcProxyIds", _string_item)
        result["showEnterToast"], cursor = _bool(data, cursor, f"{field}.showEnterToast")
        result["showLeaveToast"], cursor = _bool(data, cursor, f"{field}.showLeaveToast")
    elif tag == 16 and member_count == 1:
        result["specificDataType"] = "VisitLocStatData"
        result["saveId"], cursor = _i32(data, cursor, f"{field}.saveId")
    else:
        raise LevelFunctionAreaCodecError(
            f"{field}: unsupported specific-data wrapper at offset={start}: "
            f"tag={tag} memberCount={member_count}"
        )
    result["endOffset"] = cursor
    return result, cursor


def decode_function_area_specific_data_list(data: bytes, cursor: int) -> dict[str, Any]:
    """Decode one exact polymorphic ``FunctionAreaSpecificData`` list."""

    value, _ = _list(data, cursor, "specificDatas", _specific_data)
    return value
