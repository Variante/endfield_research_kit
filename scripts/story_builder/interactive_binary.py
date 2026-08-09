"""Fail-closed readers for current Endfield Interactive MemoryPack data.

This module is the maintained binary boundary shared by Story ownership joins
and debug Audio semantics.  It deliberately decodes only structures proven in
the current exported corpus: the exact two-member ``InteractiveTable`` and the
single-property-map ``PhysicsAudioComponentData`` union member.  A changed
member count, property order/type, value cardinality, or nested wrapper is an
error rather than a best-effort semantic claim.
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
