"""Fail-closed readers for current Endfield Interactive MemoryPack data.

This module is the maintained binary boundary shared by Story ownership joins
and debug Audio semantics.  It deliberately decodes only structures proven in
the current exported corpus: the exact two-member ``InteractiveTable``, the
single-property-map ``PhysicsAudioComponentData`` union member, and the current
``ModelViewStateControllerData`` graph needed to reach its four audio behavior
members.  A changed member count, property order/type, value cardinality, union
tag, or nested wrapper is an error rather than a best-effort semantic claim.
"""
from __future__ import annotations

import math
import struct
from typing import Any


NULL_COUNT = 0xFFFFFFFF
INTERACTIVE_TABLE_MEMBER_COUNT = 2
PHYSICS_AUDIO_COMPONENT_TAG = 0x00BE
PHYSICS_AUDIO_COMPONENT_MEMBER_COUNT = 1
PHYSICS_AUDIO_PROPERTY_VALUE_MEMBER_COUNT = 2
PHYSICS_AUDIO_PROPERTY_ITEM_MEMBER_COUNT = 2
PHYSICS_AUDIO_SCHEMA_MAPPING_ID = (
    "gameassembly-0c557367-memorypack-physics-audio-component-v1"
)
PHYSICS_AUDIO_RUNTIME_MAPPING_ID = (
    "gameassembly-0c557367-physics-audio-apply-properties-v1"
)
INTERACTIVE_TABLE_SCHEMA_MAPPING_ID = (
    "gameassembly-0c557367-memorypack-interactive-table-v2"
)
MODEL_VIEW_STATE_SCHEMA_MAPPING_ID = (
    "gameassembly-0c557367-memorypack-model-view-state-controller-v1"
)
MODEL_VIEW_AUDIO_RUNTIME_MAPPING_ID = (
    "gameassembly-0c557367-model-view-state-audio-behaviors-v1"
)

MODEL_VIEW_STATE_MEMBER_COUNT = 7
MODEL_VIEW_AUDIO_TAGS = {1, 2, 3, 4}
MODEL_VIEW_BEHAVIOR_LAYOUTS: dict[int, tuple[int, int, str]] = {
    0: (15, 12, "aiNavigation"),
    1: (14, 1, "event"),
    2: (14, 8, "positionEvent"),
    3: (13, 9, "rtpc"),
    4: (12, 13, "spatialAudio"),
    6: (12, 14, "cameraImpulse"),
    7: (6, 10, "destructible"),
    8: (14, 11, "dither"),
    9: (17, 18, "effectAlpha"),
    10: (17, 0, "effect"),
    11: (17, 7, "effectLength"),
    12: (11, 2, "emissive"),
    13: (8, 17, "movable"),
    14: (12, 5, "nodePunch"),
    17: (8, 3, "setActive"),
    18: (10, 6, "uvAnimation"),
    19: (10, 16, "wetness"),
}

PROPERTY_BOOL = 1
PROPERTY_INT32 = 3
PROPERTY_FLOAT = 5
PROPERTY_STRING = 7
PROPERTY_TYPE_NAMES = {
    PROPERTY_BOOL: "bool",
    PROPERTY_INT32: "int32",
    PROPERTY_FLOAT: "float32",
    PROPERTY_STRING: "string",
}

# Authored spelling is preserved exactly.  In particular, two current keys do
# not spell the corresponding generated/runtime fields the same way.
PHYSICS_AUDIO_PROPERTIES: tuple[dict[str, Any], ...] = (
    {"authoredKey": "need_track_movement", "runtimeField": "needTrackMovement", "valueType": PROPERTY_BOOL},
    {"authoredKey": "on_hit_acceleration_sqr_threshold", "runtimeField": "onHitAccelerationSqrThreshold", "valueType": PROPERTY_FLOAT},
    {"authoredKey": "on_start_move_audio_event", "runtimeField": "onStartMoveAudioEvent", "valueType": PROPERTY_STRING, "eventRole": "movementStart"},
    {"authoredKey": "on_stop_move_audio_event", "runtimeField": "onStopMoveAudioEvent", "valueType": PROPERTY_STRING, "eventRole": "movementStop"},
    {"authoredKey": "on_hit_audio_event", "runtimeField": "onHitAudioEvent", "valueType": PROPERTY_STRING, "eventRole": "movementHit"},
    {"authoredKey": "on_hit_max_player_per_move", "runtimeField": "onHitMaxPlayPerMove", "valueType": PROPERTY_INT32},
    {"authoredKey": "on_hit_min_interval_time", "runtimeField": "onHitMinIntervalTime", "valueType": PROPERTY_FLOAT},
    {"authoredKey": "velocity_sqr_rtpc", "runtimeField": "velocitySqrRtpc", "valueType": PROPERTY_STRING, "rtpcRole": "movementVelocitySquared"},
    {"authoredKey": "acceleration_sqr_rtpc", "runtimeField": "accelerationSqrRtpc", "valueType": PROPERTY_STRING, "rtpcRole": "movementAccelerationSquared"},
    {"authoredKey": "need_track_rotation", "runtimeField": "needTrackRotation", "valueType": PROPERTY_BOOL},
    {"authoredKey": "on_rotation_loop_audio_event", "runtimeField": "onRotationLoopAudioEvent", "valueType": PROPERTY_STRING, "eventRole": "rotationLoop"},
    {"authoredKey": "on_rotation_loop_start_angular_velocity_sqr", "runtimeField": "onRotationLoopStartAngularVelocitySqr", "valueType": PROPERTY_FLOAT},
    {"authoredKey": "on_rotation_loop_end_angular_velocity_sqr", "runtimeField": "onRotationLoopEndAngularVelocitySqr", "valueType": PROPERTY_FLOAT},
    {"authoredKey": "on_rotation_one_shot_audio_event", "runtimeField": "onRotationOneShotAudioEvent", "valueType": PROPERTY_STRING, "eventRole": "rotationOneShot"},
    {"authoredKey": "on_rotation_one_shot_trigger_ratio", "runtimeField": "onRotationOneShotTriggerRatio", "valueType": PROPERTY_FLOAT},
    {"authoredKey": "on_rotation_ground_loop_audio_event", "runtimeField": "onRotationGroundLoopAudioEvent", "valueType": PROPERTY_STRING, "eventRole": "groundRotationLoop"},
    {"authoredKey": "on_rotation_ground_loop_start_angular_velocity_sqr", "runtimeField": "onRotationGroundLoopStartAngularVelocitySqr", "valueType": PROPERTY_FLOAT},
    {"authoredKey": "on_rotation_ground_loop_end_angular_velocity_sqr", "runtimeField": "onRotationGroundLoopEndAngularVelocitySqr", "valueType": PROPERTY_FLOAT},
    {"authoredKey": "on_rotation_ground_one_shot_audio_event", "runtimeField": "onRotationGroundOneShotAudioEvent", "valueType": PROPERTY_STRING, "eventRole": "groundRotationOneShot"},
    {"authoredKey": "on_rotation_ground_one_shot_trigger_audio_event", "runtimeField": "onRotationGroundOneShotTriggerRatio", "valueType": PROPERTY_FLOAT},
    {"authoredKey": "angular_velocity_sqr_rtpc", "runtimeField": "angularVelocitySqrRtpc", "valueType": PROPERTY_STRING, "rtpcRole": "rotationAngularVelocitySquared"},
)


class InteractiveBinaryDecodeError(ValueError):
    """Raised when a supported Interactive MemoryPack layout changes."""


def _read_u32(data: bytes, offset: int, field: str) -> tuple[int, int]:
    if offset + 4 > len(data):
        raise InteractiveBinaryDecodeError(f"{field}: truncated uint32")
    return struct.unpack_from("<I", data, offset)[0], offset + 4


def _read_i32(data: bytes, offset: int, field: str) -> tuple[int, int]:
    if offset + 4 > len(data):
        raise InteractiveBinaryDecodeError(f"{field}: truncated int32")
    return struct.unpack_from("<i", data, offset)[0], offset + 4


def _read_i64(data: bytes, offset: int, field: str) -> tuple[int, int]:
    if offset + 8 > len(data):
        raise InteractiveBinaryDecodeError(f"{field}: truncated int64")
    return struct.unpack_from("<q", data, offset)[0], offset + 8


def _read_f32(data: bytes, offset: int, field: str) -> tuple[float, int]:
    if offset + 4 > len(data):
        raise InteractiveBinaryDecodeError(f"{field}: truncated float32")
    value = struct.unpack_from("<f", data, offset)[0]
    if not math.isfinite(value):
        raise InteractiveBinaryDecodeError(f"{field}: non-finite float32")
    return value, offset + 4


def _read_bool(data: bytes, offset: int, field: str) -> tuple[bool, int]:
    if offset >= len(data):
        raise InteractiveBinaryDecodeError(f"{field}: truncated bool")
    value = data[offset]
    if value not in (0, 1):
        raise InteractiveBinaryDecodeError(f"{field}: invalid bool {value}")
    return bool(value), offset + 1


def _read_member_count(data: bytes, offset: int, field: str, expected: int) -> int:
    if offset >= len(data):
        raise InteractiveBinaryDecodeError(f"{field}: truncated member count")
    actual = data[offset]
    if actual != expected:
        raise InteractiveBinaryDecodeError(
            f"{field}: member count {actual}, expected {expected}"
        )
    return offset + 1


def _read_count(
    data: bytes,
    offset: int,
    field: str,
    *,
    maximum: int,
    allow_null: bool = False,
) -> tuple[int | None, int]:
    count, offset = _read_u32(data, offset, f"{field}.count")
    if count == NULL_COUNT:
        if allow_null:
            return None, offset
        raise InteractiveBinaryDecodeError(f"{field}: null collection")
    if count > maximum:
        raise InteractiveBinaryDecodeError(f"{field}: invalid count {count}")
    return count, offset


def _read_string(
    data: bytes,
    offset: int,
    field: str,
    *,
    max_bytes: int = 2_048,
    allow_null: bool = False,
) -> tuple[str | None, int]:
    length, offset = _read_u32(data, offset, f"{field}.length")
    if length == NULL_COUNT:
        if allow_null:
            return None, offset
        raise InteractiveBinaryDecodeError(f"{field}: null string")
    if length > max_bytes or offset + length > len(data):
        raise InteractiveBinaryDecodeError(f"{field}: invalid string length {length}")
    try:
        value = data[offset:offset + length].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InteractiveBinaryDecodeError(f"{field}: invalid UTF-8") from exc
    if any(ord(character) < 0x20 for character in value):
        raise InteractiveBinaryDecodeError(f"{field}: control character")
    return value, offset + length


def decode_interactive_table(data: bytes) -> dict[str, Any]:
    """Decode the exact current two-member ``InteractiveTable``.

    The function consumes the entire input, enforces unique keys and one-member
    template references, and rejects references without a core template.
    """
    if not data or data[0] != INTERACTIVE_TABLE_MEMBER_COUNT:
        raise InteractiveBinaryDecodeError("InteractiveTable member count changed")
    offset = 1
    core_offset = offset
    core_count, offset = _read_u32(data, offset, "coreTemplatePathDict.count")
    if core_count == NULL_COUNT or core_count > 10_000:
        raise InteractiveBinaryDecodeError(
            f"coreTemplatePathDict: invalid count {core_count}"
        )
    core_paths: dict[str, str] = {}
    for index in range(core_count):
        template_id, offset = _read_string(
            data, offset, f"coreTemplatePathDict[{index}].key", max_bytes=512
        )
        template_path, offset = _read_string(
            data, offset, f"coreTemplatePathDict[{index}].value"
        )
        if not template_id or template_id in core_paths:
            raise InteractiveBinaryDecodeError(
                f"coreTemplatePathDict[{index}]: empty or duplicate key"
            )
        core_paths[template_id] = str(template_path or "")

    interactive_offset = offset
    interactive_count, offset = _read_u32(
        data, offset, "interactiveDataDict.count"
    )
    if interactive_count == NULL_COUNT or interactive_count > 50_000:
        raise InteractiveBinaryDecodeError(
            f"interactiveDataDict: invalid count {interactive_count}"
        )
    object_to_template: dict[str, str] = {}
    for index in range(interactive_count):
        object_id, offset = _read_string(
            data, offset, f"interactiveDataDict[{index}].key", max_bytes=512
        )
        if offset >= len(data) or data[offset] != 1:
            marker = data[offset] if offset < len(data) else "truncated"
            raise InteractiveBinaryDecodeError(
                f"interactiveDataDict[{index}].value: member count {marker}"
            )
        offset += 1
        template_id, offset = _read_string(
            data,
            offset,
            f"interactiveDataDict[{index}].value.templateId",
            max_bytes=512,
        )
        if not object_id or object_id in object_to_template:
            raise InteractiveBinaryDecodeError(
                f"interactiveDataDict[{index}]: empty or duplicate key"
            )
        object_to_template[object_id] = str(template_id or "")

    if offset != len(data):
        raise InteractiveBinaryDecodeError(
            f"InteractiveTable: trailing bytes at 0x{offset:x}"
        )
    missing = sorted(set(object_to_template.values()) - set(core_paths))
    if missing:
        raise InteractiveBinaryDecodeError(
            "InteractiveTable: missing core templates " + ", ".join(missing[:4])
        )
    return {
        "memberCount": INTERACTIVE_TABLE_MEMBER_COUNT,
        "coreTemplateCount": core_count,
        "interactiveDataCount": interactive_count,
        "coreTemplatePathOffset": core_offset,
        "interactiveDataOffset": interactive_offset,
        "endOffset": offset,
        "coreTemplatePaths": core_paths,
        "objectToTemplate": object_to_template,
        "schemaMappingId": INTERACTIVE_TABLE_SCHEMA_MAPPING_ID,
        "schemaStatus": "exact-current-complete",
    }


def _decode_physics_property_value(
    data: bytes,
    offset: int,
    *,
    index: int,
    schema: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    field = f"propertyList[{index}].value"
    value_offset = offset
    if offset >= len(data) or data[offset] != PHYSICS_AUDIO_PROPERTY_VALUE_MEMBER_COUNT:
        marker = data[offset] if offset < len(data) else "truncated"
        raise InteractiveBinaryDecodeError(f"{field}: member count {marker}")
    offset += 1
    value_type, offset = _read_i32(data, offset, f"{field}.valueType")
    expected_type = int(schema["valueType"])
    if value_type != expected_type:
        raise InteractiveBinaryDecodeError(
            f"{field}: value type {value_type}, expected {expected_type}"
        )
    value_count, offset = _read_u32(data, offset, f"{field}.values.count")
    if value_count != 1:
        raise InteractiveBinaryDecodeError(
            f"{field}: value count {value_count}, expected 1"
        )
    if offset >= len(data) or data[offset] != PHYSICS_AUDIO_PROPERTY_ITEM_MEMBER_COUNT:
        marker = data[offset] if offset < len(data) else "truncated"
        raise InteractiveBinaryDecodeError(f"{field}.values[0]: member count {marker}")
    offset += 1
    value_bits, offset = _read_i64(data, offset, f"{field}.values[0].valueBit64")
    tail_int: int | None = None
    string_tail: str | None = None
    if value_type == PROPERTY_STRING:
        if value_bits != 0:
            raise InteractiveBinaryDecodeError(
                f"{field}.values[0]: string valueBit64 changed"
            )
        string_tail, offset = _read_string(
            data, offset, f"{field}.values[0].stringTail"
        )
        value: Any = string_tail
    else:
        tail_int, offset = _read_i32(data, offset, f"{field}.values[0].tailInt")
        if tail_int != -1:
            raise InteractiveBinaryDecodeError(
                f"{field}.values[0]: tail int {tail_int}, expected -1"
            )
        if value_type == PROPERTY_BOOL:
            if value_bits not in (0, 1):
                raise InteractiveBinaryDecodeError(
                    f"{field}.values[0]: invalid bool bits {value_bits}"
                )
            value = bool(value_bits)
        elif value_type == PROPERTY_INT32:
            if not -(1 << 31) <= value_bits < (1 << 31):
                raise InteractiveBinaryDecodeError(
                    f"{field}.values[0]: int32 bits out of range {value_bits}"
                )
            value = value_bits
        elif value_type == PROPERTY_FLOAT:
            if value_bits < 0 or value_bits > 0xFFFFFFFF:
                raise InteractiveBinaryDecodeError(
                    f"{field}.values[0]: float high bits changed"
                )
            value = struct.unpack("<f", struct.pack("<I", value_bits))[0]
            if not math.isfinite(value):
                raise InteractiveBinaryDecodeError(
                    f"{field}.values[0]: non-finite float"
                )
        else:  # guarded by the fixed schema, retained as a fail-closed check
            raise InteractiveBinaryDecodeError(f"{field}: unsupported value type")
    return {
        "valueSourceOffset": value_offset,
        "endOffset": offset,
        "memberCount": PHYSICS_AUDIO_PROPERTY_VALUE_MEMBER_COUNT,
        "valueType": value_type,
        "valueTypeName": PROPERTY_TYPE_NAMES[value_type],
        "valueCount": value_count,
        "valueBit64": value_bits,
        "tailInt": tail_int,
        "stringTail": string_tail,
        "value": value,
    }, offset


def decode_physics_audio_component(
    data: bytes,
    source_offset: int = 0,
) -> dict[str, Any]:
    """Decode one exact compact-tag ``PhysicsAudioComponentData`` value."""
    start = source_offset
    if source_offset + 2 > len(data):
        raise InteractiveBinaryDecodeError("PhysicsAudioComponentData: truncated header")
    if data[source_offset] != PHYSICS_AUDIO_COMPONENT_TAG:
        raise InteractiveBinaryDecodeError(
            f"PhysicsAudioComponentData: union tag 0x{data[source_offset]:02x}"
        )
    if data[source_offset + 1] != PHYSICS_AUDIO_COMPONENT_MEMBER_COUNT:
        raise InteractiveBinaryDecodeError(
            "PhysicsAudioComponentData: member count "
            f"{data[source_offset + 1]}"
        )
    offset = source_offset + 2
    property_map_offset = offset
    property_count, offset = _read_u32(data, offset, "propertyList.count")
    if property_count != len(PHYSICS_AUDIO_PROPERTIES):
        raise InteractiveBinaryDecodeError(
            f"propertyList: count {property_count}, expected {len(PHYSICS_AUDIO_PROPERTIES)}"
        )
    rows: list[dict[str, Any]] = []
    for index, schema in enumerate(PHYSICS_AUDIO_PROPERTIES):
        row_offset = offset
        if offset >= len(data) or data[offset] != 2:
            marker = data[offset] if offset < len(data) else "truncated"
            raise InteractiveBinaryDecodeError(
                f"propertyList[{index}]: member count {marker}"
            )
        offset += 1
        key, offset = _read_string(
            data, offset, f"propertyList[{index}].key", max_bytes=256
        )
        expected_key = str(schema["authoredKey"])
        if key != expected_key:
            raise InteractiveBinaryDecodeError(
                f"propertyList[{index}]: key {key!r}, expected {expected_key!r}"
            )
        decoded_value, offset = _decode_physics_property_value(
            data, offset, index=index, schema=schema
        )
        rows.append({
            "index": index,
            "propertySourceOffset": row_offset,
            "endOffset": offset,
            "authoredKey": expected_key,
            "runtimeField": str(schema["runtimeField"]),
            "eventRole": str(schema.get("eventRole") or ""),
            "rtpcRole": str(schema.get("rtpcRole") or ""),
            **decoded_value,
        })
    return {
        "sourceOffset": start,
        "propertyMapOffset": property_map_offset,
        "endOffset": offset,
        "byteLength": offset - start,
        "unionTag": PHYSICS_AUDIO_COMPONENT_TAG,
        "unionTagHex": f"0x{PHYSICS_AUDIO_COMPONENT_TAG:04x}",
        "unionTagEncoding": "memorypack-u8",
        "memberCount": PHYSICS_AUDIO_COMPONENT_MEMBER_COUNT,
        "propertyCount": property_count,
        "properties": rows,
        "schemaMappingId": PHYSICS_AUDIO_SCHEMA_MAPPING_ID,
        "runtimeMappingId": PHYSICS_AUDIO_RUNTIME_MAPPING_ID,
        "schemaStatus": "exact-current-complete-property-map",
    }


def find_physics_audio_components(data: bytes) -> list[dict[str, Any]]:
    """Find exact PhysicsAudio components without guessing other union bodies.

    The anchor includes the compact union tag and generated property-map entry
    framing around the first exact authored key, but deliberately leaves the
    component member count and property count to the strict decoder.  This
    makes current-shape drift visible instead of silently treating the
    component as absent.
    """
    first_key = str(PHYSICS_AUDIO_PROPERTIES[0]["authoredKey"]).encode("utf-8")
    first_entry_anchor = b"\x02" + struct.pack("<I", len(first_key)) + first_key
    rows: list[dict[str, Any]] = []
    cursor = 0
    while True:
        entry_offset = data.find(first_entry_anchor, cursor)
        if entry_offset < 0:
            break
        source_offset = entry_offset - 6  # compact tag + member byte + u32 map count
        cursor = entry_offset + 1
        if source_offset < 0 or data[source_offset] != PHYSICS_AUDIO_COMPONENT_TAG:
            continue
        rows.append(decode_physics_audio_component(data, source_offset))
    return rows


def _skip_bytes(data: bytes, offset: int, size: int, field: str) -> int:
    if size < 0 or offset + size > len(data):
        raise InteractiveBinaryDecodeError(f"{field}: truncated {size}-byte value")
    return offset + size


def _decode_animation_curve(data: bytes, offset: int, field: str) -> int:
    """Consume the exact current MemoryPack formatter shape for AnimationCurve."""
    if offset >= len(data):
        raise InteractiveBinaryDecodeError(f"{field}: truncated AnimationCurve")
    marker = data[offset]
    if marker == 0xFF:
        return offset + 1
    if marker != 3:
        raise InteractiveBinaryDecodeError(
            f"{field}: AnimationCurve member count {marker}, expected 3 or null"
        )
    return _skip_bytes(data, offset + 1, 12, field)


def _decode_model_view_condition_group(data: bytes, offset: int, field: str) -> int:
    if offset < len(data) and data[offset] == 0xFF:
        return offset + 1
    offset = _read_member_count(data, offset, field, 2)
    count, offset = _read_count(
        data, offset, f"{field}.conditions", maximum=1_024, allow_null=True
    )
    for index in range(count or 0):
        item = f"{field}.conditions[{index}]"
        offset = _read_member_count(data, offset, item, 4)
        _comparison, offset = _read_i32(data, offset, f"{item}.comparison")
        offset = _skip_bytes(data, offset, 16, f"{item}.conditionValue")
        _inverted, offset = _read_bool(data, offset, f"{item}.isInvert")
        _key, offset = _read_string(
            data, offset, f"{item}.key", max_bytes=512, allow_null=True
        )
    _logic, offset = _read_i32(data, offset, f"{field}.logic")
    return offset


def _decode_model_view_transition_setting(
    data: bytes, offset: int, field: str
) -> int:
    if offset < len(data) and data[offset] == 0xFF:
        return offset + 1
    offset = _read_member_count(data, offset, field, 10)
    offset = _decode_animation_curve(data, offset, f"{field}.blendCurve")
    _value, offset = _read_f32(data, offset, f"{field}.blendDuration")
    offset = _decode_animation_curve(data, offset, f"{field}.blendInCurve")
    _value, offset = _read_i32(data, offset, f"{field}.blendMode")
    offset = _decode_animation_curve(data, offset, f"{field}.blendOutCurve")
    _value, offset = _read_i32(data, offset, f"{field}.easeType")
    _value, offset = _read_f32(data, offset, f"{field}.exitTime")
    _value, offset = _read_bool(data, offset, f"{field}.hasExitTime")
    _value, offset = _read_bool(data, offset, f"{field}.isFixedDuration")
    _value, offset = _read_f32(data, offset, f"{field}.offset")
    return offset


def _decode_model_view_transitions(data: bytes, offset: int, field: str) -> int:
    count, offset = _read_count(
        data, offset, field, maximum=4_096, allow_null=True
    )
    for index in range(count or 0):
        item = f"{field}[{index}]"
        offset = _read_member_count(data, offset, item, 4)
        offset = _decode_model_view_condition_group(
            data, offset, f"{item}.conditionGroup"
        )
        _priority, offset = _read_i32(data, offset, f"{item}.priority")
        _target, offset = _read_string(
            data, offset, f"{item}.targetStateName", max_bytes=512, allow_null=True
        )
        offset = _decode_model_view_transition_setting(
            data, offset, f"{item}.transitionSetting"
        )
    return offset


def _decode_model_view_clip_segments(data: bytes, offset: int, field: str) -> int:
    count, offset = _read_count(
        data, offset, field, maximum=4_096, allow_null=True
    )
    for index in range(count or 0):
        item = f"{field}[{index}]"
        offset = _read_member_count(data, offset, item, 13)
        _name, offset = _read_string(
            data, offset, f"{item}.animationClipName", allow_null=True
        )
        for name in ("blendIn", "blendOut", "clipIn", "easeIn", "easeOut", "end"):
            _value, offset = _read_f32(data, offset, f"{item}.{name}")
        offset = _decode_animation_curve(data, offset, f"{item}.easeInCurve")
        offset = _decode_animation_curve(data, offset, f"{item}.easeOutCurve")
        _value, offset = _read_i32(data, offset, f"{item}.postExtrapolation")
        _value, offset = _read_i32(data, offset, f"{item}.preExtrapolation")
        _value, offset = _read_f32(data, offset, f"{item}.speed")
        _value, offset = _read_f32(data, offset, f"{item}.startTime")
    return offset


def _decode_model_view_impulse_definition(
    data: bytes, offset: int, field: str
) -> int:
    offset = _read_member_count(data, offset, field, 18)
    _value, offset = _read_f32(data, offset, f"{field}.amplitudeGain")
    _value, offset = _read_bool(data, offset, f"{field}.cameraShake2D")
    offset = _decode_animation_curve(data, offset, f"{field}.customImpulseShape")
    _value, offset = _read_i32(data, offset, f"{field}.directionMode")
    _value, offset = _read_f32(data, offset, f"{field}.dissipationDistance")
    _value, offset = _read_i32(data, offset, f"{field}.dissipationMode")
    for name in ("dissipationRate", "frequencyGain", "impactRadius"):
        _value, offset = _read_f32(data, offset, f"{field}.{name}")
    _value, offset = _read_i32(data, offset, f"{field}.impulseChannel")
    _value, offset = _read_f32(data, offset, f"{field}.impulseDuration")
    for name in ("impulseShape", "impulseType"):
        _value, offset = _read_i32(data, offset, f"{field}.{name}")
    _value, offset = _read_f32(data, offset, f"{field}.propagationSpeed")
    _value, offset = _read_bool(data, offset, f"{field}.randomize")
    _value, offset = _read_string(
        data, offset, f"{field}.rawSignalPath", allow_null=True
    )
    _value, offset = _read_i32(data, offset, f"{field}.repeatMode")
    envelope = f"{field}.timeEnvelope"
    offset = _read_member_count(data, offset, envelope, 7)
    offset = _decode_animation_curve(data, offset, f"{envelope}.attackShape")
    _value, offset = _read_f32(data, offset, f"{envelope}.attackTime")
    offset = _decode_animation_curve(data, offset, f"{envelope}.decayShape")
    _value, offset = _read_f32(data, offset, f"{envelope}.decayTime")
    _value, offset = _read_bool(data, offset, f"{envelope}.holdForever")
    _value, offset = _read_bool(data, offset, f"{envelope}.scaleWithImpact")
    _value, offset = _read_f32(data, offset, f"{envelope}.sustainTime")
    return offset


def _decode_model_view_behavior(
    data: bytes,
    offset: int,
    field: str,
) -> tuple[dict[str, Any] | None, int]:
    start = offset
    if offset + 2 > len(data):
        raise InteractiveBinaryDecodeError(f"{field}: truncated union header")
    tag = data[offset]
    member_count = data[offset + 1]
    offset += 2
    layout = MODEL_VIEW_BEHAVIOR_LAYOUTS.get(tag)
    if layout is None:
        raise InteractiveBinaryDecodeError(f"{field}: unsupported union tag {tag}")
    expected_members, expected_type, behavior_kind = layout
    if member_count != expected_members:
        raise InteractiveBinaryDecodeError(
            f"{field}: member count {member_count}, expected {expected_members} for tag {tag}"
        )

    can_loop_active, offset = _read_bool(data, offset, f"{field}.canLoopActive")
    need_force_execute, offset = _read_bool(data, offset, f"{field}.needForceExecute")
    normalized_time_flow, offset = _read_bool(
        data, offset, f"{field}.normalizedTimeFlowBasedActive"
    )
    behavior_time, offset = _read_f32(data, offset, f"{field}.time")
    time_flow_switch, offset = _read_i32(data, offset, f"{field}.timeFlowSwitch")
    behavior_type, offset = _read_i32(data, offset, f"{field}.type")
    if behavior_type != expected_type:
        raise InteractiveBinaryDecodeError(
            f"{field}: behavior type {behavior_type}, expected {expected_type} for tag {tag}"
        )
    row: dict[str, Any] = {
        "sourceOffset": start,
        "unionTag": tag,
        "unionTagHex": f"0x{tag:04x}",
        "unionTagEncoding": "memorypack-u8",
        "memberCount": member_count,
        "behaviorType": behavior_type,
        "behaviorKind": behavior_kind,
        "canLoopActive": can_loop_active,
        "needForceExecute": need_force_execute,
        "normalizedTimeFlowBasedActive": normalized_time_flow,
        "time": behavior_time,
        "timeFlowSwitch": time_flow_switch,
    }

    if tag in (1, 2):
        row["audioNodeName"], offset = _read_string(
            data, offset, f"{field}.audioNodeName", allow_null=True
        )
        row["customAudioId"], offset = _read_string(
            data, offset, f"{field}.customAudioId", allow_null=True
        )
        row["eAudioTriggerState"], offset = _read_i32(
            data, offset, f"{field}.eAudioTriggerState"
        )
        row["isCustom"], offset = _read_bool(data, offset, f"{field}.isCustom")
        row["isDirectlyPlay"], offset = _read_bool(
            data, offset, f"{field}.isDirectlyPlay"
        )
        row["normalAudioId"], offset = _read_i32(
            data, offset, f"{field}.normalAudioId"
        )
        row["stopOnEnd"], offset = _read_bool(data, offset, f"{field}.stopOnEnd")
        row["transitionTime"], offset = _read_i32(
            data, offset, f"{field}.transitionTime"
        )
    elif tag == 3:
        row["audioNodeName"], offset = _read_string(
            data, offset, f"{field}.audioNodeName", allow_null=True
        )
        row["audioRTPCSetValue"], offset = _read_f32(
            data, offset, f"{field}.audioRTPCSetValue"
        )
        row["audioRTPCValue"], offset = _read_string(
            data, offset, f"{field}.audioRTPCValue", allow_null=True
        )
        row["rtpcBehaviourType"], offset = _read_i32(
            data, offset, f"{field}.behaviourType"
        )
        row["continuousTick"], offset = _read_bool(
            data, offset, f"{field}.continuousTick"
        )
        row["dependBlackBoard"], offset = _read_bool(
            data, offset, f"{field}.dependBlackBoard"
        )
        row["dependFloatKey"], offset = _read_string(
            data, offset, f"{field}.dependFloatKey", allow_null=True
        )
    elif tag == 4:
        row["continuous"], offset = _read_bool(data, offset, f"{field}.continuous")
        row["dependBlackBoard"], offset = _read_bool(
            data, offset, f"{field}.dependBlackBoard"
        )
        row["dependFloatKey"], offset = _read_string(
            data, offset, f"{field}.dependFloatKey", allow_null=True
        )
        row["directSet"], offset = _read_bool(data, offset, f"{field}.directSet")
        row["targetClosePercentage"], offset = _read_f32(
            data, offset, f"{field}.targetClosePercentage"
        )
        row["totalTime"], offset = _read_f32(data, offset, f"{field}.totalTime")
    elif tag == 0:
        _value, offset = _read_i32(data, offset, f"{field}.areaMask")
        _value, offset = _read_f32(data, offset, f"{field}.agentRadius")
        _value, offset = _read_u32(data, offset, f"{field}.navMeshId")
        for name in ("position", "rotation"):
            offset = _skip_bytes(data, offset, 12, f"{field}.{name}")
        for name in ("operation", "sourceType"):
            _value, offset = _read_i32(data, offset, f"{field}.{name}")
        _value, offset = _read_f32(data, offset, f"{field}.stoppingDistance")
        offset = _skip_bytes(data, offset, 12, f"{field}.target")
    elif tag == 6:
        offset = _decode_model_view_impulse_definition(
            data, offset, f"{field}.impulseDefinition"
        )
        _value, offset = _read_string(data, offset, f"{field}.nodeName", allow_null=True)
        offset = _skip_bytes(data, offset, 12, f"{field}.positionOffset")
        _value, offset = _read_i64(data, offset, f"{field}.rawSignalHash")
        _value, offset = _read_bool(data, offset, f"{field}.realCameraShake2D")
        _value, offset = _read_bool(data, offset, f"{field}.releaseWhenActionEnds")
    elif tag == 7:
        pass
    elif tag == 8:
        _value, offset = _read_f32(data, offset, f"{field}.duration")
        _value, offset = _read_bool(data, offset, f"{field}.enable")
        _value, offset = _read_string(data, offset, f"{field}.nodeName", allow_null=True)
        _value, offset = _read_f32(data, offset, f"{field}.target")
        _value, offset = _read_bool(data, offset, f"{field}.useCurve")
        _value, offset = _read_string(data, offset, f"{field}.curveName", allow_null=True)
        _value, offset = _read_i32(data, offset, f"{field}.mode")
        _value, offset = _read_string(data, offset, f"{field}.parameter", allow_null=True)
    elif tag == 9:
        _value, offset = _read_bool(data, offset, f"{field}.active")
        _value, offset = _read_string(data, offset, f"{field}.effectName", allow_null=True)
        _value, offset = _read_f32(data, offset, f"{field}.alpha")
        _value, offset = _read_string(data, offset, f"{field}.nodeName", allow_null=True)
        _value, offset = _read_i32(data, offset, f"{field}.mode")
        _value, offset = _read_string(data, offset, f"{field}.paramName", allow_null=True)
        _value, offset = _read_i32(data, offset, f"{field}.paramType")
        for name in ("continuous", "dependBlackBoard", "directSet"):
            _value, offset = _read_bool(data, offset, f"{field}.{name}")
        _value, offset = _read_f32(data, offset, f"{field}.totalTime")
    elif tag == 10:
        for name in ("active", "follow"):
            _value, offset = _read_bool(data, offset, f"{field}.{name}")
        _value, offset = _read_i32(data, offset, f"{field}.effectId")
        for name in ("effectName", "nodeName"):
            _value, offset = _read_string(data, offset, f"{field}.{name}", allow_null=True)
        for name in ("loop", "releaseOnEnd", "usePool"):
            _value, offset = _read_bool(data, offset, f"{field}.{name}")
        _value, offset = _read_i32(data, offset, f"{field}.space")
        for name in ("visible", "worldSpace"):
            _value, offset = _read_bool(data, offset, f"{field}.{name}")
    elif tag == 11:
        _value, offset = _read_bool(data, offset, f"{field}.active")
        _value, offset = _read_string(data, offset, f"{field}.effectName", allow_null=True)
        for name in ("length", "speed"):
            _value, offset = _read_f32(data, offset, f"{field}.{name}")
        _value, offset = _read_string(data, offset, f"{field}.nodeName", allow_null=True)
        _value, offset = _read_i32(data, offset, f"{field}.mode")
        for name in ("loop", "release"):
            _value, offset = _read_bool(data, offset, f"{field}.{name}")
        _value, offset = _read_string(data, offset, f"{field}.paramName", allow_null=True)
        _value, offset = _read_bool(data, offset, f"{field}.useCurve")
        _value, offset = _read_f32(data, offset, f"{field}.totalTime")
    elif tag == 12:
        _value, offset = _read_f32(data, offset, f"{field}.emissive")
        _value, offset = _read_i64(data, offset, f"{field}.configHash")
        _value, offset = _read_string(data, offset, f"{field}.nodeName", allow_null=True)
        for name in ("continuous", "directSet"):
            _value, offset = _read_bool(data, offset, f"{field}.{name}")
    elif tag in (13, 17):
        _value, offset = _read_bool(data, offset, f"{field}.active")
        _value, offset = _read_string(data, offset, f"{field}.nodeName", allow_null=True)
    elif tag == 14:
        _value, offset = _read_f32(data, offset, f"{field}.amplitude")
        _value, offset = _read_i32(data, offset, f"{field}.axis")
        _value, offset = _read_f32(data, offset, f"{field}.duration")
        _value, offset = _read_string(data, offset, f"{field}.nodeName", allow_null=True)
        offset = _skip_bytes(data, offset, 12, f"{field}.direction")
        _value, offset = _read_i32(data, offset, f"{field}.mode")
    elif tag == 18:
        _value, offset = _read_bool(data, offset, f"{field}.active")
        for name in ("nodeName", "propertyName"):
            _value, offset = _read_string(data, offset, f"{field}.{name}", allow_null=True)
        _value, offset = _read_f32(data, offset, f"{field}.speed")
    elif tag == 19:
        for name in ("duration", "target", "totalTime"):
            _value, offset = _read_f32(data, offset, f"{field}.{name}")
        _value, offset = _read_string(data, offset, f"{field}.nodeName", allow_null=True)

    row["endOffset"] = offset
    row["byteLength"] = offset - start
    return (row if tag in MODEL_VIEW_AUDIO_TAGS else None), offset


def decode_model_view_state_controller(data: bytes) -> dict[str, Any]:
    """Decode one complete current ``ModelViewStateControllerData`` value.

    The full nested graph is consumed so audio members cannot be found by a
    false-positive byte scan. Only the four proven audio behavior subtypes are
    returned, with their exact model/layer/state/behavior owner chain.
    """
    offset = _read_member_count(
        data, 0, "ModelViewStateControllerData", MODEL_VIEW_STATE_MEMBER_COUNT
    )
    camera_count, offset = _read_count(
        data, offset, "cameraSignalSourceAssetHashes", maximum=100_000, allow_null=True
    )
    for index in range(camera_count or 0):
        _value, offset = _read_i64(data, offset, f"cameraSignalSourceAssetHashes[{index}]")

    clip_count, offset = _read_count(
        data, offset, "clipAssetInfos", maximum=100_000, allow_null=True
    )
    for index in range(clip_count or 0):
        field = f"clipAssetInfos[{index}]"
        offset = _read_member_count(data, offset, field, 2)
        _value, offset = _read_i64(data, offset, f"{field}.animationClipHash")
        _value, offset = _read_string(
            data, offset, f"{field}.animationClipName", allow_null=True
        )

    effect_count, offset = _read_count(
        data, offset, "effectIds", maximum=100_000, allow_null=True
    )
    for index in range(effect_count or 0):
        _value, offset = _read_string(
            data, offset, f"effectIds[{index}]", allow_null=True
        )

    emissive_count, offset = _read_count(
        data, offset, "emissiveConfigHashes", maximum=100_000, allow_null=True
    )
    for index in range(emissive_count or 0):
        _value, offset = _read_i64(data, offset, f"emissiveConfigHashes[{index}]")

    model_count, offset = _read_count(
        data, offset, "modelAnimatorDatas", maximum=10_000, allow_null=True
    )
    audio_behaviors: list[dict[str, Any]] = []
    behavior_count = 0
    layer_count_total = 0
    state_count_total = 0
    for model_index in range(model_count or 0):
        model_field = f"modelAnimatorDatas[{model_index}]"
        offset = _read_member_count(data, offset, model_field, 2)
        layer_count, offset = _read_count(
            data, offset, f"{model_field}.layerFsmDatas", maximum=10_000, allow_null=True
        )
        layer_rows: list[tuple[int, int, str, list[dict[str, Any]]]] = []
        for layer_index in range(layer_count or 0):
            layer_count_total += 1
            layer_field = f"{model_field}.layerFsmDatas[{layer_index}]"
            offset = _read_member_count(data, offset, layer_field, 5)
            _has_clip, offset = _read_bool(data, offset, f"{layer_field}.hasAnimClip")
            layer_fsm_index, offset = _read_i32(data, offset, f"{layer_field}.index")
            layer_name, offset = _read_string(
                data, offset, f"{layer_field}.layerName", max_bytes=512, allow_null=True
            )
            state_count, offset = _read_count(
                data, offset, f"{layer_field}.stateDatas", maximum=20_000, allow_null=True
            )
            layer_audio: list[dict[str, Any]] = []
            for state_index in range(state_count or 0):
                state_count_total += 1
                state_field = f"{layer_field}.stateDatas[{state_index}]"
                offset = _read_member_count(data, offset, state_field, 18)
                _clip_name, offset = _read_string(
                    data, offset, f"{state_field}.animationClipName", allow_null=True
                )
                _based_param, offset = _read_string(
                    data, offset, f"{state_field}.basedParamKey", allow_null=True
                )
                count, offset = _read_count(
                    data, offset, f"{state_field}.behaviors", maximum=100_000, allow_null=True
                )
                state_audio: list[dict[str, Any]] = []
                for behavior_index in range(count or 0):
                    behavior_count += 1
                    row, offset = _decode_model_view_behavior(
                        data, offset, f"{state_field}.behaviors[{behavior_index}]"
                    )
                    if row is not None:
                        row["modelAnimatorIndex"] = model_index
                        row["layerIndex"] = layer_index
                        row["layerFsmIndex"] = layer_fsm_index
                        row["layerName"] = str(layer_name or "")
                        row["stateIndex"] = state_index
                        row["behaviorIndex"] = behavior_index
                        state_audio.append(row)
                offset = _decode_model_view_clip_segments(
                    data, offset, f"{state_field}.clipSegments"
                )
                for name in (
                    "isComplexAnimation", "isEmpty", "isHaveClip", "isLoop",
                    "isSpeedBasedByParam", "isStartingNode", "isSyncedWithGlobalTime",
                ):
                    _value, offset = _read_bool(data, offset, f"{state_field}.{name}")
                _value, offset = _read_f32(data, offset, f"{state_field}.smoothTime")
                _value, offset = _read_f32(data, offset, f"{state_field}.speed")
                _value, offset = _read_string(
                    data, offset, f"{state_field}.speedBasedParamKey", allow_null=True
                )
                state_name, offset = _read_string(
                    data, offset, f"{state_field}.stateName", max_bytes=512, allow_null=True
                )
                state_type, offset = _read_i32(data, offset, f"{state_field}.stateType")
                _value, offset = _read_f32(data, offset, f"{state_field}.totalTime")
                offset = _decode_model_view_transitions(
                    data, offset, f"{state_field}.transitions"
                )
                for row in state_audio:
                    row["stateName"] = str(state_name or "")
                    row["stateType"] = state_type
                layer_audio.extend(state_audio)
            _weight, offset = _read_f32(data, offset, f"{layer_field}.weight")
            layer_rows.append((layer_index, layer_fsm_index, str(layer_name or ""), layer_audio))
        model_name, offset = _read_string(
            data, offset, f"{model_field}.modelName", max_bytes=2_048, allow_null=True
        )
        for _layer_index, _fsm_index, _layer_name, rows in layer_rows:
            for row in rows:
                row["modelAnimatorName"] = str(model_name or "")
                audio_behaviors.append(row)

    model_id, offset = _read_string(
        data, offset, "modelId", max_bytes=2_048, allow_null=True
    )
    pre_tick_animator, offset = _read_bool(data, offset, "preTickAnimator")
    if offset != len(data):
        raise InteractiveBinaryDecodeError(
            f"ModelViewStateControllerData: trailing bytes at 0x{offset:x}"
        )
    for row in audio_behaviors:
        row["modelId"] = str(model_id or "")
    return {
        "memberCount": MODEL_VIEW_STATE_MEMBER_COUNT,
        "modelId": str(model_id or ""),
        "preTickAnimator": pre_tick_animator,
        "modelAnimatorCount": model_count or 0,
        "layerCount": layer_count_total,
        "stateCount": state_count_total,
        "behaviorCount": behavior_count,
        "audioBehaviorCount": len(audio_behaviors),
        "audioBehaviors": audio_behaviors,
        "endOffset": offset,
        "schemaMappingId": MODEL_VIEW_STATE_SCHEMA_MAPPING_ID,
        "runtimeMappingId": MODEL_VIEW_AUDIO_RUNTIME_MAPPING_ID,
        "schemaStatus": "exact-current-complete",
    }
