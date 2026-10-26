"""Exact MemoryPack codecs for ``LevelFunctionAreaData`` nested collections.

This module owns the current 15-member base rows, their seven-member factory
hide description, the two polymorphic collections and the shared condition
union. ``ThreeDimRange`` remains in ``scripts.game_data.leveldata_binary``.

- ``ConditionData`` reads ``conditionRuntimeBase`` before ``uniqueId``.
- ``decode_condition_runtime`` is the shared ``ConditionRuntimeBase`` codec
  (also used by top-level ``buildableCondition``). It admits only the
  reviewed routes: ``CombinedConditionRuntime`` (recursive, three members),
  ``SimpleConditionCheckGlobalVar`` (``compareOperator``, ``compareTarget``,
  ``globalVarName``; reached by bamboo-raft dock filters),
  ``SimpleConditionCheckMissionNotPaused``, and the mission-state and
  quest-state checks.
- ``FunctionAreaSpecificData`` covers ambience camera, blight miasma,
  block-AI bark, camera control/look-at/volume, carry tags, dither factory
  bounds, entity-hiding filters, radio triggers, repatriation, scene toast
  keys, teammate-follow bounds, Story safe zones, and ``VisitLocStatData`` (a
  one-member wrapper holding the signed ``saveId``). Each concrete value uses
  its generated setter order and member count, including nested LangKey,
  string/identity lists and finite Vector3 values.

Both unions are dispatched by type name: each reviewed layout names its type
and the member count it reads, and the build's tag is resolved by type name
per build through ``levelscript_union_tags``. An unknown tag, a changed member
count or an unvalidated build stops at the nested union instead of shifting
later LevelData fields. Evidence tier: exact stored layout; the stored
conditions and area settings do not prove runtime evaluation or activation.
"""

from __future__ import annotations

from typing import Any, Callable

from scripts.game_data import levelscript_union_tags as union_tags
from scripts.game_data.leveldata_function_area_native import CONTRACT as FUNCTION_AREA_CONTRACT, check_function_area_native_inputs
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


# Reviewed layouts, by type name and the member count each reads. Tags are
# resolved by type name per build; never write one here.
_CONDITION_LAYOUTS = {
    "CombinedConditionRuntime": 3,
    "SimpleConditionCheckMissionNotPaused": 1,
    "SimpleConditionCheckGlobalVar": 3,
    "SimpleConditionCheckMissionState": 3,
    "SimpleConditionCheckQuestState": 3,
}
_SPECIFIC_DATA_LAYOUTS = {
    "AmbienceCameraData": 20,
    "BlightMiasmaAreaData": 1,
    "BlockAIBarkData": 1,
    "CameraAddControlStateData": 11,
    "CameraLookAtData": 13,
    "CameraVolumeData": 12,
    "CarryTagZoneData": 1,
    "DitherFactoryZoneData": 2,
    "HideEntityByTypeParams": 4,
    "RadioTriggerZoneData": 7,
    "RepatriateZoneData": 2,
    "SceneToastUIData": 6,
    "StopTeammateFollowZoneData": 6,
    "StorySafeZone": 4,
    "VisitLocStatData": 1,
}
# Nested ``LevelFunctionAreaData`` types carry their owner in the union name.
_SPECIFIC_DATA_OWNER = "LevelFunctionAreaData_"


def _condition_routes() -> dict[tuple[int, int], str]:
    return union_tags.routes("ConditionRuntimeBase", _CONDITION_LAYOUTS)


def _specific_data_routes() -> dict[tuple[int, int], str]:
    found = union_tags.routes(
        "FunctionAreaSpecificData",
        {_SPECIFIC_DATA_OWNER + name: count for name, count in _SPECIFIC_DATA_LAYOUTS.items()},
    )
    return {key: name.removeprefix(_SPECIFIC_DATA_OWNER) for key, name in found.items()}


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
    condition_type = _condition_routes().get((tag, member_count))
    if condition_type == "CombinedConditionRuntime":
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
    if condition_type == "SimpleConditionCheckMissionNotPaused":
        mission_id, cursor = _string(data, cursor, f"{field}.missionId")
        return {
            "startOffset": start,
            "endOffset": cursor,
            "unionTag": tag,
            "conditionType": "SimpleConditionCheckMissionNotPaused",
            "serializedMemberCount": member_count,
            "missionId": mission_id,
        }, cursor
    if condition_type == "SimpleConditionCheckGlobalVar":
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
    if condition_type in ("SimpleConditionCheckMissionState", "SimpleConditionCheckQuestState"):
        compare_operator, cursor = _i32(data, cursor, f"{field}.compareOperator")
        compare_target, cursor = _i32(data, cursor, f"{field}.compareTarget")
        owner_id, cursor = _string(data, cursor, f"{field}.ownerId")
        return {
            "startOffset": start,
            "endOffset": cursor,
            "unionTag": tag,
            "conditionType": condition_type,
            "serializedMemberCount": member_count,
            "compareOperator": compare_operator,
            "compareTarget": compare_target,
            "ownerId": owner_id,
        }, cursor
    raise LevelFunctionAreaCodecError(
        f"{field}: unsupported condition at offset={start}: tag={tag} memberCount={member_count}"
        f"{union_tags.unavailable_note()}"
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
    specific_type = _specific_data_routes().get((tag, member_count))

    if specific_type == "AmbienceCameraData":
        result["specificDataType"] = specific_type
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
    elif specific_type == "BlightMiasmaAreaData":
        result["specificDataType"] = specific_type
        result["areaLevel"], cursor = _i32(data, cursor, f"{field}.areaLevel")
    elif specific_type == "BlockAIBarkData":
        result["specificDataType"] = specific_type
        result["defaultOn"], cursor = _bool(data, cursor, f"{field}.defaultOn")
    elif specific_type == "CameraAddControlStateData":
        result["specificDataType"] = specific_type
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
    elif specific_type == "CameraLookAtData":
        result["specificDataType"] = specific_type
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
    elif specific_type == "CameraVolumeData":
        result["specificDataType"] = specific_type
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
    elif specific_type == "CarryTagZoneData":
        result["specificDataType"] = specific_type
        result["zoneTag"], cursor = _u32(data, cursor, f"{field}.zoneTag")
    elif specific_type == "DitherFactoryZoneData":
        result["specificDataType"] = specific_type
        result["center"], cursor = _vector3(data, cursor, f"{field}.center")
        result["size"], cursor = _vector3(data, cursor, f"{field}.size")
    elif specific_type == "HideEntityByTypeParams":
        result["specificDataType"] = specific_type
        result["entityTypes"], cursor = _i32(data, cursor, f"{field}.entityTypes")
        result["logicIdWhitelist"], cursor = _list(data, cursor, f"{field}.logicIdWhitelist", _u64_item)
        result["npcTypes"], cursor = _i32(data, cursor, f"{field}.npcTypes")
        result["proxyWhitelist"], cursor = _list(data, cursor, f"{field}.proxyWhitelist", _string_item)
    elif specific_type == "RadioTriggerZoneData":
        result["specificDataType"] = specific_type
        for name in ("hideAfterMissionId", "hideBeforeMissionId", "hideCompleteMissionId", "prtsId", "radioId"):
            result[name], cursor = _string(data, cursor, f"{field}.{name}")
        value, cursor = _u64(data, cursor, f"{field}.triggerId")
        result["triggerId"] = str(value)
        result["useRadioTriggerOnce"], cursor = _bool(data, cursor, f"{field}.useRadioTriggerOnce")
    elif specific_type == "RepatriateZoneData":
        result["specificDataType"] = specific_type
        result["lifeRatio"], cursor = _f32(data, cursor, f"{field}.lifeRatio")
        result["useRepatriateZoneType"], cursor = _bool(data, cursor, f"{field}.useRepatriateZoneType")
    elif specific_type == "SceneToastUIData":
        result["specificDataType"] = specific_type
        result["conditionalEntries"], cursor = _list(
            data, cursor, f"{field}.conditionalEntries", _scene_toast_runtime_entry
        )
        result["depthText"], cursor = _lang_key(data, cursor, f"{field}.depthText")
        result["mainTitle"], cursor = _lang_key(data, cursor, f"{field}.mainTitle")
        result["priority"], cursor = _i32(data, cursor, f"{field}.priority")
        result["saveId"], cursor = _i32(data, cursor, f"{field}.saveId")
        result["subTitle"], cursor = _lang_key(data, cursor, f"{field}.subTitle")
    elif specific_type == "StopTeammateFollowZoneData":
        result["specificDataType"] = specific_type
        result["enterSummonRadius"], cursor = _f32(data, cursor, f"{field}.enterSummonRadius")
        result["inOutZoneTolerance"], cursor = _f32(data, cursor, f"{field}.inOutZoneTolerance")
        result["specifyTeammatePositions"], cursor = _bool(data, cursor, f"{field}.specifyTeammatePositions")
        result["specifyTeammateRotations"], cursor = _bool(data, cursor, f"{field}.specifyTeammateRotations")
        result["teammateLookAtPoints"], cursor = _list(data, cursor, f"{field}.teammateLookAtPoints", _vector3_item)
        result["teammatePositions"], cursor = _list(data, cursor, f"{field}.teammatePositions", _vector3_item)
    elif specific_type == "StorySafeZone":
        result["specificDataType"] = specific_type
        result["defaultOn"], cursor = _bool(data, cursor, f"{field}.defaultOn")
        result["npcProxyIds"], cursor = _list(data, cursor, f"{field}.npcProxyIds", _string_item)
        result["showEnterToast"], cursor = _bool(data, cursor, f"{field}.showEnterToast")
        result["showLeaveToast"], cursor = _bool(data, cursor, f"{field}.showLeaveToast")
    elif specific_type == "VisitLocStatData":
        result["specificDataType"] = specific_type
        result["saveId"], cursor = _i32(data, cursor, f"{field}.saveId")
    else:
        raise LevelFunctionAreaCodecError(
            f"{field}: unsupported specific-data wrapper at offset={start}: "
            f"tag={tag} memberCount={member_count}{union_tags.unavailable_note()}"
        )
    result["endOffset"] = cursor
    return result, cursor


def decode_function_area_specific_data_list(data: bytes, cursor: int) -> dict[str, Any]:
    """Decode one exact polymorphic ``FunctionAreaSpecificData`` list."""

    value, _ = _list(data, cursor, "specificDatas", _specific_data)
    return value


def _factory_hide_description(data, cursor, diagnostics):
    def fail(gate, at, expected, actual):
        if diagnostics is not None:
            diagnostics.append({"validator":"functionAreaBase","gate":gate,"offset":at,"expected":expected,"actual":actual})
        return None
    start = cursor
    if cursor >= len(data):return fail("factory-hide-member-count",cursor,"7/null","EOF")
    marker = data[cursor];cursor += 1
    if marker == 0xFF:return None,cursor
    if marker != 7:return fail("factory-hide-member-count",start,7,marker)
    values = {"sourceOffset":start,"memberCount":7}
    for name in ("hideAllBuildingUI","hideFacBuilding","hideFacBuildingAll","hideFacFence","hideSocialFac"):
        decoded = read_bool(data,cursor)
        if decoded is None:return fail("factoryHideDesc."+name,cursor,"bool 0/1",data[cursor] if cursor<len(data) else "EOF")
        values[name],cursor = decoded
    decoded = read_i32(data,cursor)
    if decoded is None:return fail("factory-hide-owner",cursor,"Int32",len(data)-cursor)
    values["hideSocialFacOwner"],cursor = decoded
    count = read_count(data,cursor,max_count=100000)
    if count is None:return fail("factory-hide-count",cursor,"count -1..100000",data[cursor:cursor+4].hex())
    if count[0] not in (-1,0):return fail("positive-building-types",cursor,"null/empty list",count[0])
    values["showFacBuildingTypes"] = None if count[0] == -1 else []
    values["endOffset"] = count[1]
    return values,count[1]


def decode_function_area_base_data_list(
    data: bytes,
    offset: int,
    *,
    diagnostics: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    start = offset
    decoded = read_count(data, offset, max_count=100_000)
    if decoded is None:
        return None
    count, cursor = decoded
    if count == -1:
        return {"startOffset": start, "endOffset": cursor, "count": count, "value": None}
    if count > 0:
        gate = check_function_area_native_inputs()
        if gate.status != "validated":
            if diagnostics is not None:
                diagnostics.append({"validator":"functionAreaBase","gate":"selected-native-inputs",
                                    "source":str(FUNCTION_AREA_CONTRACT),"status":gate.status,"detail":gate.detail})
            return None
    rows: list[dict[str, Any]] = []
    for index in range(count):
        row_start = cursor
        if cursor >= len(data):
            return None
        if data[cursor] == 0xFF:
            rows.append({
                "indexInCollection": index,
                "startOffset": row_start,
                "endOffset": row_start + 1,
                "value": None,
            })
            cursor += 1
            continue
        if data[cursor] != 15:
            if diagnostics is not None:
                diagnostics.append({"validator":"functionAreaBase","gate":"member-count","offset":cursor,"expected":15,"actual":data[cursor]})
            return None
        cursor += 1

        buffer_distance_decoded = read_f32(data, cursor)
        if buffer_distance_decoded is None:
            return None
        buffer_distance, cursor = buffer_distance_decoded
        default_off_decoded = read_bool(data, cursor)
        if default_off_decoded is None:
            return None
        default_off, cursor = default_off_decoded
        enable_decoded = read_bool(data,cursor)
        if enable_decoded is None:
            if diagnostics is not None:
                diagnostics.append({"validator":"functionAreaBase","gate":"enableFactoryHide","offset":cursor,"expected":"bool 0/1","actual":data[cursor] if cursor<len(data) else "EOF"})
            return None
        enable_factory_hide,cursor = enable_decoded

        vectors: dict[str, list[float]] = {}
        for vector_name in ("euler",):
            values: list[float] = []
            for _ in range(3):
                value_decoded = read_f32(data, cursor)
                if value_decoded is None:
                    return None
                value, cursor = value_decoded
                values.append(value)
            vectors[vector_name] = values

        hide_decoded = _factory_hide_description(data,cursor,diagnostics)
        if hide_decoded is None:return None
        factory_hide_desc,cursor = hide_decoded
        function_type_decoded = read_i32(data, cursor)
        if function_type_decoded is None:
            return None
        function_type, cursor = function_type_decoded
        has_condition_decoded = read_bool(data, cursor)
        if has_condition_decoded is None:
            return None
        has_condition, cursor = has_condition_decoded
        index_decoded = read_i32(data, cursor)
        if index_decoded is None:
            return None
        row_index, cursor = index_decoded

        for vector_name in ("offset",):
            values = []
            for _ in range(3):
                value_decoded = read_f32(data, cursor)
                if value_decoded is None:
                    return None
                value, cursor = value_decoded
                values.append(value)
            vectors[vector_name] = values

        pos_count_decoded = read_count(data, cursor, max_count=100_000)
        if pos_count_decoded is None:
            return None
        pos_count, cursor = pos_count_decoded
        positions: list[list[float]] | None = None if pos_count == -1 else []
        for _ in range(max(0, pos_count)):
            position: list[float] = []
            # Generated ``FunctionAreaBaseData.posList`` is ``List<Vector2>``.
            for _ in range(2):
                value_decoded = read_f32(data, cursor)
                if value_decoded is None:
                    return None
                value, cursor = value_decoded
                position.append(value)
            assert positions is not None
            positions.append(position)

        for vector_name in ("postion",):
            values = []
            for _ in range(3):
                value_decoded = read_f32(data, cursor)
                if value_decoded is None:
                    return None
                value, cursor = value_decoded
                values.append(value)
            vectors[vector_name] = values

        radius_decoded = read_f32(data, cursor)
        shape_type_decoded = read_i32(data, radius_decoded[1]) if radius_decoded else None
        if radius_decoded is None or shape_type_decoded is None:
            return None
        radius, _ = radius_decoded
        shape_type, cursor = shape_type_decoded

        size: list[float] = []
        for _ in range(3):
            value_decoded = read_f32(data, cursor)
            if value_decoded is None:
                return None
            value, cursor = value_decoded
            size.append(value)
        unique_id_decoded = read_u64(data, cursor)
        if unique_id_decoded is None:
            return None
        unique_id, cursor = unique_id_decoded
        rows.append({
            "indexInCollection": index,
            "startOffset": row_start,
            "endOffset": cursor,
            "memberCount": 15,
            "bufferDistance": buffer_distance,
            "defaultOff": default_off,
            "enableFactoryHide": enable_factory_hide,
            "factoryHideDesc": factory_hide_desc,
            "euler": vectors["euler"],
            "functionType": function_type,
            "hasCondition": has_condition,
            "index": row_index,
            "offset": vectors["offset"],
            "posList": positions,
            "postion": vectors["postion"],
            "radius": radius,
            "shapeType": shape_type,
            "size": size,
            "uniqueId": str(unique_id),
        })
    return {"startOffset": start, "endOffset": cursor, "count": count, "rows": rows}
