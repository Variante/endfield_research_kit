"""Exact current ``Dictionary<uint, LevelInteractiveData>`` codec."""

from __future__ import annotations

import math
import struct
from typing import Any, Callable


class LevelInteractiveCodecError(ValueError):
    """Raised when a declared interactive value cannot advance exactly."""


_AOI_RADIUS_VALUES = {-1, 0, 1, 2, 3}
_CREATE_STATE_VALUES = {-1, 0, 1, 2, 3}
_OBJECT_TYPE_INTERACTIVE = 32
_PARAM_REAL_TYPE_VALUES = set(range(75))
_MAX_COLLECTION_COUNT = 16_384
_MAX_STRING_BYTES = 1 << 20


def _need(data: bytes, cursor: int, size: int, field: str) -> None:
    if cursor < 0 or size < 0 or cursor + size > len(data):
        raise LevelInteractiveCodecError(
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
        raise LevelInteractiveCodecError(
            f"invalid bool {field}: offset={cursor} value={raw}"
        )
    return bool(raw), cursor + 1


def _f32(data: bytes, cursor: int, field: str) -> tuple[float, int]:
    _need(data, cursor, 4, field)
    value = struct.unpack_from("<f", data, cursor)[0]
    if not math.isfinite(value):
        raise LevelInteractiveCodecError(
            f"non-finite {field}: offset={cursor} value={value!r}"
        )
    return value, cursor + 4


def _string(data: bytes, cursor: int, field: str) -> tuple[str | None, int]:
    size, cursor = _i32(data, cursor, f"{field}.length")
    if size == -1:
        return None, cursor
    if size < 0 or size > _MAX_STRING_BYTES:
        raise LevelInteractiveCodecError(
            f"invalid string length {field}: offset={cursor - 4} value={size}"
        )
    _need(data, cursor, size, field)
    try:
        return data[cursor : cursor + size].decode("utf-8"), cursor + size
    except UnicodeDecodeError as error:
        raise LevelInteractiveCodecError(
            f"invalid UTF-8 {field}: offset={cursor} size={size}"
        ) from error


def _count(data: bytes, cursor: int, field: str) -> tuple[int | None, int]:
    value, cursor = _i32(data, cursor, f"{field}.count")
    if value == -1:
        return None, cursor
    if value < 0 or value > _MAX_COLLECTION_COUNT:
        raise LevelInteractiveCodecError(
            f"invalid collection count {field}: offset={cursor - 4} value={value}"
        )
    return value, cursor


def _list(
    data: bytes,
    cursor: int,
    field: str,
    decode_item: Callable[[bytes, int, str], tuple[Any, int]],
) -> tuple[dict[str, Any], int]:
    start = cursor
    count, cursor = _count(data, cursor, field)
    if count is None:
        return {"status": "null", "count": None, "values": None}, cursor
    values = []
    for index in range(count):
        value, cursor = decode_item(data, cursor, f"{field}[{index}]")
        values.append(value)
    return {
        "status": "present",
        "count": count,
        "values": values,
        "startOffset": start,
        "endOffset": cursor,
    }, cursor


def _decode_i32_item(data: bytes, cursor: int, field: str) -> tuple[int, int]:
    return _i32(data, cursor, field)


def _decode_param_value_atom(
    data: bytes, cursor: int, field: str
) -> tuple[dict[str, Any], int]:
    _need(data, cursor, 1, f"{field}.memberCount")
    if data[cursor] != 2:
        raise LevelInteractiveCodecError(
            f"invalid ParamValueAtom member count: offset={cursor} value={data[cursor]}"
        )
    cursor += 1
    _need(data, cursor, 8, f"{field}.valueBit64")
    value_bit64 = struct.unpack_from("<q", data, cursor)[0]
    cursor += 8
    value_string, cursor = _string(data, cursor, f"{field}.valueString")
    return {"valueBit64": value_bit64, "valueString": value_string}, cursor


def _decode_param_value(
    data: bytes, cursor: int, field: str
) -> tuple[dict[str, Any], int]:
    _need(data, cursor, 1, f"{field}.memberCount")
    if data[cursor] != 2:
        raise LevelInteractiveCodecError(
            f"invalid ParamValue member count: offset={cursor} value={data[cursor]}"
        )
    cursor += 1
    value_type, cursor = _i32(data, cursor, f"{field}.type")
    if value_type not in _PARAM_REAL_TYPE_VALUES:
        raise LevelInteractiveCodecError(
            f"invalid ParamRealType {field}: value={value_type}"
        )
    values, cursor = _list(
        data, cursor, f"{field}.valueArray", _decode_param_value_atom
    )
    return {"typeRaw": value_type, "valueArray": values}, cursor


def _decode_param_key_value(
    data: bytes, cursor: int, field: str
) -> tuple[dict[str, Any], int]:
    _need(data, cursor, 1, f"{field}.memberCount")
    if data[cursor] != 2:
        raise LevelInteractiveCodecError(
            f"invalid ParamKeyValue member count: offset={cursor} value={data[cursor]}"
        )
    cursor += 1
    key, cursor = _string(data, cursor, f"{field}.key")
    value, cursor = _decode_param_value(data, cursor, f"{field}.value")
    return {"key": key, "value": value}, cursor


def _decode_param_list(
    data: bytes, cursor: int, field: str
) -> tuple[dict[str, Any], int]:
    return _list(data, cursor, field, _decode_param_key_value)


def decode_param_key_value_list(
    data: bytes,
    cursor: int,
    field: str = "paramKeyValues",
) -> tuple[dict[str, Any], int]:
    """Advance one exact generated ``List<ParamKeyValue>`` value."""

    return _decode_param_list(data, cursor, field)


def _decode_component_properties(
    data: bytes, cursor: int, field: str
) -> tuple[dict[str, Any], int]:
    count, cursor = _count(data, cursor, field)
    if count is None:
        return {"status": "null", "count": None, "entries": None}, cursor
    entries = []
    seen: set[int] = set()
    for index in range(count):
        component_type, cursor = _i32(
            data, cursor, f"{field}[{index}].componentType"
        )
        # This is an Int32-backed enum dictionary key, not a union tag. Every
        # value has the same List<ParamKeyValue> codec; the key never selects a
        # payload shape. Preserve its raw integer without a corpus-derived
        # whitelist, while still rejecting duplicate dictionary keys.
        if component_type in seen:
            raise LevelInteractiveCodecError(
                f"duplicate component type {field}: value={component_type}"
            )
        seen.add(component_type)
        properties, cursor = _decode_param_list(
            data, cursor, f"{field}[{index}].properties"
        )
        entries.append({"componentTypeRaw": component_type, "properties": properties})
    return {"status": "present", "count": count, "entries": entries}, cursor


def _decode_progress_lock_condition(
    data: bytes,
    cursor: int,
    field: str,
    *,
    depth: int = 0,
) -> tuple[dict[str, Any], int]:
    if depth > 8:
        raise LevelInteractiveCodecError(f"{field}: condition nesting exceeds 8")
    start = cursor
    _need(data, cursor, 2, field)
    union_tag = data[cursor]
    member_count = data[cursor + 1]
    cursor += 2
    if union_tag in (0x0C, 0x10, 0x11) and member_count == 3:
        compare_operator, cursor = _i32(data, cursor, f"{field}.compareOperator")
        compare_target, cursor = _i32(data, cursor, f"{field}.compareTarget")
        owner_id, cursor = _string(data, cursor, f"{field}.ownerId")
        if compare_operator not in (0, 1) or not 0 <= compare_target <= 5 or not owner_id:
            raise LevelInteractiveCodecError(
                f"invalid state condition {field}: operator={compare_operator} "
                f"target={compare_target} owner={owner_id!r}"
            )
        return {
            "unionTag": union_tag,
            "serializedMemberCount": member_count,
            "conditionType": (
                "SimpleConditionCheckMissionState"
                if union_tag == 0x0C
                else "SimpleConditionCheckQuestState"
            ),
            "compareOperator": compare_operator,
            "compareTarget": compare_target,
            "ownerId": owner_id,
            "startOffset": start,
            "endOffset": cursor,
        }, cursor
    if union_tag == 0 and member_count == 3:
        condition_operator, cursor = _i32(
            data, cursor, f"{field}.conditionOperator"
        )
        runtime_flag, cursor = _bool(data, cursor, f"{field}.runtimeFlag")
        count, cursor = _count(data, cursor, f"{field}.conditions")
        if condition_operator not in (0, 1) or count is None or count <= 0 or count > 64:
            raise LevelInteractiveCodecError(
                f"invalid combined condition {field}: operator={condition_operator} count={count}"
            )
        conditions = []
        for index in range(count):
            condition, cursor = _decode_progress_lock_condition(
                data,
                cursor,
                f"{field}.conditions[{index}]",
                depth=depth + 1,
            )
            conditions.append(condition)
        return {
            "unionTag": union_tag,
            "serializedMemberCount": member_count,
            "conditionType": "CombinedConditionRuntime",
            "conditionOperator": condition_operator,
            "serializedRuntimeFlag": runtime_flag,
            "conditions": conditions,
            "startOffset": start,
            "endOffset": cursor,
        }, cursor
    raise LevelInteractiveCodecError(
        f"unsupported non-null progressLockCondition: offset={start} "
        f"tag={union_tag} memberCount={member_count}"
    )


def _decode_interactive(
    data: bytes, cursor: int, field: str
) -> tuple[dict[str, Any], int]:
    start = cursor
    _need(data, cursor, 1, f"{field}.memberCount")
    if data[cursor] != 25:
        raise LevelInteractiveCodecError(
            f"invalid LevelInteractiveData member count: offset={cursor} value={data[cursor]}"
        )
    cursor += 1
    aoi_radius, cursor = _i32(data, cursor, f"{field}.aoiRadiusType")
    belong_id, cursor = _u64(data, cursor, f"{field}.belongLevelScriptId")
    create_state, cursor = _i32(data, cursor, f"{field}.createState")
    dependency_id, cursor = _u64(data, cursor, f"{field}.dependencyGroupId")
    data_id, cursor = _string(data, cursor, f"{field}.entityDataIdKey")
    entity_type, cursor = _i32(data, cursor, f"{field}.entityType")
    if aoi_radius not in _AOI_RADIUS_VALUES:
        raise LevelInteractiveCodecError(f"invalid AoiRadiusEnum: value={aoi_radius}")
    if create_state not in _CREATE_STATE_VALUES:
        raise LevelInteractiveCodecError(f"invalid CreateState: value={create_state}")
    if entity_type != _OBJECT_TYPE_INTERACTIVE:
        raise LevelInteractiveCodecError(f"invalid interactive ObjectType: value={entity_type}")
    force_load, cursor = _bool(data, cursor, f"{field}.forceLoad")
    keep_cross_map, cursor = _bool(data, cursor, f"{field}.keepCrossMap")
    logic_id, cursor = _u64(data, cursor, f"{field}.levelLogicId")
    override_die, cursor = _bool(data, cursor, f"{field}.overrideSendDieEvent")
    vectors = {}
    for name in ("position", "rotation", "scale"):
        values = []
        for axis in "xyz":
            value, cursor = _f32(data, cursor, f"{field}.{name}.{axis}")
            values.append(value)
        vectors[name] = dict(zip("xyz", values))
    send_die, cursor = _bool(data, cursor, f"{field}.sendDieEvent")
    component_properties, cursor = _decode_component_properties(
        data, cursor, f"{field}.componentProperties"
    )
    global_int_keys, cursor = _list(
        data, cursor, f"{field}.globalIntKeyList", _decode_i32_item
    )
    global_properties, cursor = _decode_param_list(
        data, cursor, f"{field}.globalProperties"
    )
    hide_in_dialog, cursor = _bool(data, cursor, f"{field}.hideInDialog")
    is_client_only, cursor = _bool(data, cursor, f"{field}.isClientOnly")
    is_locked, cursor = _bool(data, cursor, f"{field}.isLocked")
    map_int_keys, cursor = _list(
        data, cursor, f"{field}.mapIntKeyList", _decode_i32_item
    )
    map_properties, cursor = _decode_param_list(
        data, cursor, f"{field}.mapProperties"
    )
    model_scale, cursor = _f32(data, cursor, f"{field}.modelScale")
    _need(data, cursor, 1, f"{field}.progressLockCondition")
    if data[cursor] == 0xFF:
        progress_lock_condition = None
        cursor += 1
    else:
        progress_lock_condition, cursor = _decode_progress_lock_condition(
            data,
            cursor,
            f"{field}.progressLockCondition",
        )
    properties, cursor = _decode_param_list(data, cursor, f"{field}.properties")
    return {
        "serializedMemberCount": 25,
        "startOffset": start,
        "endOffset": cursor,
        "aoiRadiusTypeRaw": aoi_radius,
        "belongLevelScriptId": str(belong_id),
        "createStateRaw": create_state,
        "dependencyGroupId": str(dependency_id),
        "entityDataIdKey": data_id,
        "entityTypeRaw": entity_type,
        "forceLoad": force_load,
        "keepCrossMap": keep_cross_map,
        "levelLogicId": str(logic_id),
        "overrideSendDieEvent": override_die,
        **vectors,
        "sendDieEvent": send_die,
        "componentProperties": component_properties,
        "globalIntKeyList": global_int_keys,
        "globalProperties": global_properties,
        "hideInDialog": hide_in_dialog,
        "isClientOnly": is_client_only,
        "isLocked": is_locked,
        "mapIntKeyList": map_int_keys,
        "mapProperties": map_properties,
        "modelScale": model_scale,
        "progressLockCondition": progress_lock_condition,
        "properties": properties,
    }, cursor


def decode_interactive_dictionary(
    data: bytes, cursor: int
) -> tuple[dict[str, Any], int]:
    """Decode the full current LevelScript interactive dictionary."""
    start = cursor
    count, cursor = _count(data, cursor, "interactives")
    if count is None:
        return {"status": "null", "count": None, "entries": None}, cursor
    entries = []
    seen: set[int] = set()
    for index in range(count):
        key, cursor = _u32(data, cursor, f"interactives[{index}].key")
        if key in seen:
            raise LevelInteractiveCodecError(f"duplicate interactive key: {key}")
        seen.add(key)
        value, cursor = _decode_interactive(
            data, cursor, f"interactives[{index}].value"
        )
        entries.append({"key": key, "value": value})
    return {
        "status": "present",
        "count": count,
        "entries": entries,
        "startOffset": start,
        "endOffset": cursor,
    }, cursor


def decode_interactive_list(
    data: bytes, cursor: int
) -> tuple[dict[str, Any], int]:
    """Decode the full current ``List<LevelInteractiveData>`` shape.

    LevelData owns the same 25-member values as the LevelScript dictionary,
    but its collection has no leading uint key per item.  Keeping both owners
    on this codec prevents their nested property/condition boundaries from
    drifting apart.
    """
    start = cursor
    count, cursor = _count(data, cursor, "interactives")
    if count is None:
        return {"status": "null", "count": None, "values": None}, cursor
    values = []
    for index in range(count):
        value, cursor = _decode_interactive(
            data, cursor, f"interactives[{index}]"
        )
        values.append(value)
    return {
        "status": "present",
        "count": count,
        "values": values,
        "startOffset": start,
        "endOffset": cursor,
    }, cursor
