"""Fail-closed framing for current ``AnimationConfig`` payloads."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import struct
from typing import Any

from scripts.game_data.memorypack.core import MEMORYPACK_NULL_COUNT


FIXED_72_PREFIX = bytes.fromhex(
    "0f ff 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00"
)
FIXED_72_SUFFIX = bytes.fromhex(
    "ff 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 "
    "00 00 00 00 00 00 00 00 00 00 01 00 00 00 00 01 00 00 00 00 00 00"
)

ANIMATION_CONFIG_FIELDS = (
    "_fallbackMontages",
    "avatarBlendProfilePath",
    "bakedBindingPath",
    "boneWeightMasks",
    "controllerPath",
    "extraData",
    "montages",
    "npcMontages",
    "optControllerPath",
    "retargetAnimConfigPath",
    "syncGroupAnimationCurves",
    "syncGroupCurves",
    "timeRefCurves",
    "useRotateDirection",
    "useStateVariables",
)
ANIMATION_CONFIG_PREFIX_FIELDS = ANIMATION_CONFIG_FIELDS[:5]
BONE_WEIGHT_MASK_FIELDS = ("layerName", "maskPath")
ANIMATION_CONFIG_EXTRA_DATA_FIELDS = (
    "animatedShaderPropertyCfg",
    "animationEventPlayEffectCfg",
    "animationEventRendererVisibilityCfg",
    "enableAnimatedShaderProperty",
    "enableAnimationEventPlayEffect",
    "enableAnimationEventRendererVisibility",
)
CHARACTER_ANIM_EXTRA_DATA_FIELDS = (
    *ANIMATION_CONFIG_EXTRA_DATA_FIELDS,
    "_strafeAngleHorizontalThresholdDeg",
    "_strafeAngleSmoothSpeed",
    "_strafeAngleThresholdDeg",
    "_strafeMagnitudeSmoothSpeed",
    "characterBlackboardType",
    "clothIKDirectionNormalizeAngleDeg",
    "clothIKLegAdaptAngleDeg",
    "dashDuration",
    "duringTransitionClothFrontScale",
    "hasSpDash",
    "hurtAnimConfigs",
    "ikReverseAffectSkirtPhysicsFactor",
    "isHoldBombWithBothHands",
    "jumpStartBlendInTime",
    "magicaClothWeightDecreaseSpeed",
    "magicaClothWeightIncreaseSpeed",
    "moveAdditiveAnims",
    "overrideDashDuration",
    "overridePerformDict",
    "runSpLoopCount",
    "spDashConfig",
    "spIdleConfig",
    "statePerformEntries",
    "walkSpLoopCount",
)
UPPER_BODY_FIGHT_EXTRA_DATA_FIELDS = (
    *CHARACTER_ANIM_EXTRA_DATA_FIELDS,
    "upperBodyFightTimeout",
    "upperBodyLayerName",
)
ENEMY_ANIM_EXTRA_DATA_FIELDS = (
    *ANIMATION_CONFIG_EXTRA_DATA_FIELDS,
    "alertAnimTime",
    "blackboardType",
    "blowOffConfig",
    "exitVigilanceTime",
    "getUpAnimLength",
    "getUpTime",
    "hurtAnimData",
    "idleSPCount",
    "idleToFightIdleTime",
    "isPatrolTurnRight",
    "lieDownAnimLength",
    "lieDownTime",
    "turnStartData",
    "walkStopTime",
)

_MAX_BONE_WEIGHT_MASKS = 128
_MAX_LAYER_NAME_BYTES = 4_096
_MAX_CURVE_COUNT = 4_096
_MAX_KEYFRAME_COUNT = 1_000_000

CURVE_CONTRACT_SCHEMA = "endfield.animation-curve-native-contract.v1"
CURVE_CONTRACT_SHA256 = "6cd01647d099ca52a8398f9ddb6eab1753634d4ca7333c693d8eecf3b7be1428"


def _load_curve_contract() -> tuple[tuple[str, ...], str, tuple[str, ...]]:
    path = Path(__file__).with_name("animation_curve_native.json")
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != CURVE_CONTRACT_SHA256:
        raise RuntimeError(
            f"{path}: contract SHA256 {digest} does not match {CURVE_CONTRACT_SHA256}"
        )
    payload = json.loads(raw)
    if (
        payload.get("schema") != CURVE_CONTRACT_SCHEMA
        or payload.get("status") != "validated"
    ):
        raise RuntimeError(f"{path}: unsupported or unvalidated contract")

    keyframe = payload.get("fKeyframe") or {}
    wrapper_rows = keyframe.get("standaloneWrapperReadOrder") or []
    wrapper_fields = tuple(str(row.get("field") or "") for row in wrapper_rows)
    wrapper_types = tuple(str(row.get("wireType") or "") for row in wrapper_rows)
    destination_offsets = tuple(row.get("destinationOffset") for row in wrapper_rows)
    expected_wrapper_fields = (
        "inTangent", "inWeight", "outTangent", "outWeight",
        "tangentMode", "time", "value", "weightedMode",
    )
    expected_wrapper_types = (
        "float32", "float32", "float32", "float32",
        "int32", "float32", "float32", "int32",
    )
    expected_offsets = (8, 24, 12, 28, 16, 0, 4, 20)
    if (
        wrapper_fields != expected_wrapper_fields
        or wrapper_types != expected_wrapper_types
        or destination_offsets != expected_offsets
    ):
        raise RuntimeError(f"{path}: unexpected FKeyframe read/store contract")

    bulk_rows = keyframe.get("bulkArrayElementWireLayout") or []
    fields = tuple(str(row.get("field") or "") for row in bulk_rows)
    wire_types = tuple(str(row.get("wireType") or "") for row in bulk_rows)
    native_offsets = tuple(row.get("nativeOffset") for row in bulk_rows)
    expected_fields = (
        "time", "value", "inTangent", "outTangent",
        "tangentMode", "weightedMode", "inWeight", "outWeight",
    )
    expected_wire_types = (
        "float32", "float32", "float32", "float32",
        "int32", "int32", "float32", "float32",
    )
    if (
        fields != expected_fields
        or wire_types != expected_wire_types
        or native_offsets != tuple(range(0, 32, 4))
    ):
        raise RuntimeError(f"{path}: unexpected FKeyframe bulk-array layout")

    curve = payload.get("fAnimationCurve") or {}
    curve_fields = tuple(str(value) for value in curve.get("serializedReadOrder") or [])
    if curve_fields != ("keys", "postWrapMode", "preWrapMode"):
        raise RuntimeError(f"{path}: unexpected FAnimationCurve read order")
    keys_representation = curve.get("keysRepresentation") or {}
    if (
        keys_representation.get("elementLayoutSource")
        != "fKeyframe.bulkArrayElementWireLayout"
        or keys_representation.get("elementSize") != 32
        or keys_representation.get("countScale") != "count << 5"
    ):
        raise RuntimeError(f"{path}: unexpected FAnimationCurve keys representation")
    wire_format = "<" + "".join(
        "f" if wire_type == "float32" else "i" for wire_type in wire_types
    )
    return fields, wire_format, curve_fields


FKEYFRAME_SERIALIZED_FIELDS, FKEYFRAME_WIRE_FORMAT, FANIMATION_CURVE_SERIALIZED_FIELDS = (
    _load_curve_contract()
)


class AnimationConfigFramingError(ValueError):
    """Raised when the current-corpus prefix cannot be authenticated."""


def _require(data: bytes, offset: int, size: int, field: str) -> int:
    if size < 0 or offset < 0 or offset + size > len(data):
        raise AnimationConfigFramingError(
            f"{field}:truncated offset={offset} need={size} "
            f"remaining={max(0, len(data) - offset)}"
        )
    return offset + size


def _read_i64(data: bytes, offset: int, field: str) -> tuple[int, int]:
    end = _require(data, offset, 8, field)
    return struct.unpack_from("<q", data, offset)[0], end


def _read_u32(data: bytes, offset: int, field: str) -> tuple[int, int]:
    end = _require(data, offset, 4, field)
    return struct.unpack_from("<I", data, offset)[0], end


def _read_string(
    data: bytes,
    offset: int,
    field: str,
) -> tuple[str | None, int]:
    length, cursor = _read_u32(data, offset, f"{field}.length")
    if length == MEMORYPACK_NULL_COUNT:
        return None, cursor
    if length > _MAX_LAYER_NAME_BYTES:
        raise AnimationConfigFramingError(f"{field}:invalid-length={length}")
    end = _require(data, cursor, length, f"{field}.bytes")
    try:
        value = data[cursor:end].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AnimationConfigFramingError(f"{field}:invalid-utf8") from exc
    return value, end


def _decode_named_prefix(data: bytes) -> dict[str, Any]:
    """Decode the generated wrapper's first five members at a real cursor."""
    if len(data) < 30:
        raise AnimationConfigFramingError(
            f"truncated AnimationConfig named prefix: expected>=30 actual={len(data)}"
        )
    if data[1] != 0xFF:
        raise AnimationConfigFramingError(
            "AnimationConfig _fallbackMontages supports only the current null variant: "
            f"actual={data[1]}"
        )

    avatar_blend_profile_path, cursor = _read_i64(
        data, 2, "avatarBlendProfilePath"
    )
    baked_binding_path, cursor = _read_i64(data, cursor, "bakedBindingPath")
    raw_count, cursor = _read_u32(data, cursor, "boneWeightMasks.count")
    if raw_count == MEMORYPACK_NULL_COUNT:
        mask_count: int | None = None
    elif raw_count <= _MAX_BONE_WEIGHT_MASKS:
        mask_count = raw_count
    else:
        raise AnimationConfigFramingError(
            f"boneWeightMasks:invalid-count={raw_count}"
        )

    masks: list[dict[str, Any]] = []
    for index in range(mask_count or 0):
        start = cursor
        cursor = _require(data, cursor, 1, f"boneWeightMasks[{index}].memberCount")
        member_count = data[start]
        if member_count != 2:
            raise AnimationConfigFramingError(
                f"boneWeightMasks[{index}].memberCount:expected=2 actual={member_count}"
            )
        layer_name, cursor = _read_string(
            data, cursor, f"boneWeightMasks[{index}].layerName"
        )
        mask_path, cursor = _read_i64(
            data, cursor, f"boneWeightMasks[{index}].maskPath"
        )
        masks.append({
            "memberCount": member_count,
            "fieldOrder": list(BONE_WEIGHT_MASK_FIELDS),
            "layerName": layer_name,
            "maskPath": mask_path,
            "startOffset": start,
            "endOffset": cursor,
        })

    controller_path, cursor = _read_i64(data, cursor, "controllerPath")
    return {
        "startOffset": 1,
        "endOffset": cursor,
        "fieldOrder": list(ANIMATION_CONFIG_PREFIX_FIELDS),
        "fields": {
            "_fallbackMontages": None,
            "avatarBlendProfilePath": avatar_blend_profile_path,
            "bakedBindingPath": baked_binding_path,
            "boneWeightMasks": {
                "status": "null" if mask_count is None else "present",
                "count": mask_count,
                "rows": masks,
            },
            "controllerPath": controller_path,
        },
    }


def _decode_extra_data_header(data: bytes, offset: int) -> dict[str, Any]:
    """Advance the polymorphic ``AnimationConfigExtraData`` header.

    The root field is null as one ``0xff`` byte.  A present value first carries
    the current union tag (0 character, 1 enemy, 2 upper-body fight), followed
    by the concrete generated wrapper's object header. Treating a union tag as
    an empty object places the montage boundary before the concrete payload.
    """
    end = _require(data, offset, 1, "extraData.memberCount")
    marker = data[offset]
    if marker == 0xFF:
        status = "null"
        member_count: int | None = None
        closed = True
        subtype = None
        field_order = list(ANIMATION_CONFIG_EXTRA_DATA_FIELDS)
    elif marker in (0, 1, 2):
        subtype = (
            "CharacterAnimExtraData" if marker == 0
            else "EnemyAnimExtraData" if marker == 1
            else "UpperBodyFightExtraData"
        )
        object_end = _require(data, end, 1, f"extraData.{subtype}.memberCount")
        member_count = data[end]
        expected = 30 if marker == 0 else 20 if marker == 1 else 32
        if member_count != expected:
            raise AnimationConfigFramingError(
                f"extraData.{subtype}.memberCount:expected={expected} actual={member_count}"
            )
        status = (
            "character_header" if marker == 0
            else "enemy_header" if marker == 1
            else "upper_body_fight_header"
        )
        closed = False
        end = object_end
        field_order = list(
            CHARACTER_ANIM_EXTRA_DATA_FIELDS
            if marker == 0 else ENEMY_ANIM_EXTRA_DATA_FIELDS
            if marker == 1 else UPPER_BODY_FIGHT_EXTRA_DATA_FIELDS
        )
    else:
        raise AnimationConfigFramingError(
            "extraData.unionTag:expected=null-or-0..2 "
            f"actual={marker}"
        )
    return {
        "startOffset": offset,
        "headerEndOffset": end,
        "endOffset": end if closed else None,
        "status": status,
        "closed": closed,
        "subtypeTag": marker if marker != 0xFF else None,
        "subtype": subtype,
        "memberCount": member_count,
        "fieldOrder": field_order,
    }


def _read_count(data: bytes, offset: int, field: str, *, maximum: int) -> tuple[int | None, int]:
    raw, cursor = _read_u32(data, offset, f"{field}.count")
    if raw == MEMORYPACK_NULL_COUNT:
        return None, cursor
    if raw > maximum:
        raise AnimationConfigFramingError(f"{field}:invalid-count={raw}")
    return raw, cursor


def _read_fanimation_curve(data: bytes, offset: int, field: str) -> tuple[dict[str, Any] | None, int]:
    end = _require(data, offset, 1, f"{field}.memberCount")
    member_count = data[offset]
    if member_count == 0xFF:
        return None, end
    if member_count != 3:
        raise AnimationConfigFramingError(
            f"{field}.memberCount:expected=3 actual={member_count}"
        )
    count, cursor = _read_count(
        data, end, f"{field}.keys", maximum=_MAX_KEYFRAME_COUNT
    )
    if count is None:
        key_rows = None
    else:
        key_rows = []
        for index in range(count):
            row_end = _require(data, cursor, 32, f"{field}.keys[{index}]")
            values = struct.unpack_from(FKEYFRAME_WIRE_FORMAT, data, cursor)
            if any(math.isnan(value) for value in values if isinstance(value, float)):
                raise AnimationConfigFramingError(f"{field}.keys[{index}]:nan")
            key_rows.append({
                "startOffset": cursor,
                "endOffset": row_end,
                "fieldOrder": list(FKEYFRAME_SERIALIZED_FIELDS),
                "fields": dict(zip(FKEYFRAME_SERIALIZED_FIELDS, values, strict=True)),
            })
            cursor = row_end
    post_wrap, cursor = _read_u32(data, cursor, f"{field}.postWrapMode")
    pre_wrap, cursor = _read_u32(data, cursor, f"{field}.preWrapMode")
    return {
        "memberCount": member_count,
        "fieldOrder": list(FANIMATION_CURVE_SERIALIZED_FIELDS),
        "keys": key_rows,
        "postWrapMode": post_wrap,
        "preWrapMode": pre_wrap,
        "endOffset": cursor,
    }, cursor


def _read_curve_dictionary(
    data: bytes,
    offset: int,
    field: str,
    *,
    string_keys: bool,
) -> tuple[dict[str, Any], int]:
    end = _require(data, offset, 1, f"{field}.memberCount")
    member_count = data[offset]
    if member_count == 0xFF:
        return {"status": "null", "count": None, "rows": [], "endOffset": end}, end
    if member_count != 1:
        raise AnimationConfigFramingError(
            f"{field}.memberCount:expected=1 actual={member_count}"
        )
    count, cursor = _read_count(data, end, field, maximum=_MAX_CURVE_COUNT)
    if count is None:
        raise AnimationConfigFramingError(f"{field}:null inner dictionary")
    rows = []
    for index in range(count):
        start = cursor
        if string_keys:
            key, cursor = _read_string(data, cursor, f"{field}[{index}].key")
            if key is None:
                raise AnimationConfigFramingError(f"{field}[{index}].key:null")
        else:
            key, cursor = _read_u32(data, cursor, f"{field}[{index}].key")
        curve, cursor = _read_fanimation_curve(
            data, cursor, f"{field}[{index}].value"
        )
        rows.append({"key": key, "value": curve, "startOffset": start, "endOffset": cursor})
    return {
        "status": "present",
        "memberCount": member_count,
        "count": count,
        "rows": rows,
        "endOffset": cursor,
    }, cursor


def _read_strict_bool(data: bytes, offset: int, field: str) -> tuple[bool, int]:
    end = _require(data, offset, 1, field)
    value = data[offset]
    if value not in (0, 1):
        raise AnimationConfigFramingError(f"{field}:expected=0-or-1 actual={value}")
    return bool(value), end


def _read_f32(data: bytes, offset: int, field: str) -> tuple[float, int]:
    end = _require(data, offset, 4, field)
    value = struct.unpack_from("<f", data, offset)[0]
    if not math.isfinite(value):
        raise AnimationConfigFramingError(f"{field}:non-finite")
    return value, end


def _read_i32(data: bytes, offset: int, field: str) -> tuple[int, int]:
    end = _require(data, offset, 4, field)
    return struct.unpack_from("<i", data, offset)[0], end


def _read_shader_property_config(
    data: bytes, offset: int, field: str,
) -> tuple[dict[str, Any] | None, int]:
    end = _require(data, offset, 1, f"{field}.memberCount")
    marker = data[offset]
    if marker == 0xFF:
        return None, end
    if marker != 1:
        raise AnimationConfigFramingError(
            f"{field}.memberCount:expected=null-or-1 actual={marker}"
        )
    count, cursor = _read_count(data, end, f"{field}.shaderProps", maximum=4096)
    if count is None:
        raise AnimationConfigFramingError(f"{field}.shaderProps:null")
    rows = []
    for index in range(count):
        start = cursor
        cursor = _require(data, cursor, 1, f"{field}.shaderProps[{index}].memberCount")
        if data[start] != 4:
            raise AnimationConfigFramingError(
                f"{field}.shaderProps[{index}].memberCount:expected=4 actual={data[start]}"
            )
        mask, cursor = _read_i32(data, cursor, f"{field}.shaderProps[{index}].mask")
        kind, cursor = _read_i32(data, cursor, f"{field}.shaderProps[{index}].type")
        name, cursor = _read_string(data, cursor, f"{field}.shaderProps[{index}].name")
        if name is None:
            raise AnimationConfigFramingError(f"{field}.shaderProps[{index}].name:null")
        blend_mode, cursor = _read_i32(
            data, cursor, f"{field}.shaderProps[{index}].blendMode"
        )
        rows.append({
            "mask": mask, "type": kind, "name": name, "blendMode": blend_mode,
            "startOffset": start, "endOffset": cursor,
        })
    return {"memberCount": marker, "shaderProps": rows}, cursor


def _read_play_effect_config(
    data: bytes, offset: int, field: str,
) -> tuple[dict[str, Any] | None, int]:
    end = _require(data, offset, 1, f"{field}.memberCount")
    marker = data[offset]
    if marker == 0xFF:
        return None, end
    if marker != 1:
        raise AnimationConfigFramingError(
            f"{field}.memberCount:expected=null-or-1 actual={marker}"
        )
    count, cursor = _read_count(data, end, f"{field}.entries", maximum=4096)
    if count is None:
        raise AnimationConfigFramingError(f"{field}.entries:null")
    rows = []
    for index in range(count):
        start = cursor
        cursor = _require(data, cursor, 1, f"{field}.entries[{index}].memberCount")
        if data[start] != 6:
            raise AnimationConfigFramingError(
                f"{field}.entries[{index}].memberCount:expected=6 actual={data[start]}"
            )
        values: dict[str, Any] = {}
        # Current generated setter order, rather than source declaration order.
        for name in ("effectName", "eventName"):
            values[name], cursor = _read_string(
                data, cursor, f"{field}.entries[{index}].{name}"
            )
        for name in ("followPosition", "followRotation", "stopWithState"):
            values[name], cursor = _read_strict_bool(
                data, cursor, f"{field}.entries[{index}].{name}"
            )
        values["targetBonePath"], cursor = _read_string(
            data, cursor, f"{field}.entries[{index}].targetBonePath"
        )
        rows.append({**values, "startOffset": start, "endOffset": cursor})
    return {"memberCount": marker, "entries": rows}, cursor


def _read_renderer_visibility_config(
    data: bytes, offset: int, field: str,
) -> tuple[dict[str, Any] | None, int]:
    end = _require(data, offset, 1, f"{field}.memberCount")
    marker = data[offset]
    if marker == 0xFF:
        return None, end
    if marker != 1:
        raise AnimationConfigFramingError(
            f"{field}.memberCount:expected=null-or-1 actual={marker}"
        )
    count, cursor = _read_count(data, end, f"{field}.entries", maximum=4096)
    if count is None:
        raise AnimationConfigFramingError(f"{field}.entries:null")
    rows = []
    for index in range(count):
        start = cursor
        cursor = _require(data, cursor, 1, f"{field}.entries[{index}].memberCount")
        if data[start] != 1:
            raise AnimationConfigFramingError(
                f"{field}.entries[{index}].memberCount:expected=1 actual={data[start]}"
            )
        prefix_count, cursor = _read_count(
            data, cursor, f"{field}.entries[{index}].rendererNamePrefixes", maximum=4096
        )
        prefixes = None if prefix_count is None else []
        for prefix_index in range(prefix_count or 0):
            value, cursor = _read_string(
                data, cursor,
                f"{field}.entries[{index}].rendererNamePrefixes[{prefix_index}]",
            )
            prefixes.append(value)
        rows.append({
            "rendererNamePrefixes": prefixes,
            "startOffset": start, "endOffset": cursor,
        })
    return {"memberCount": marker, "entries": rows}, cursor


def _read_sk_morph_play_setting(
    data: bytes, offset: int, field: str,
) -> tuple[dict[str, Any], int]:
    end = _require(data, offset, 1, f"{field}.memberCount")
    if data[offset] != 5:
        raise AnimationConfigFramingError(
            f"{field}.memberCount:expected=5 actual={data[offset]}"
        )
    path_hash, cursor = _read_i64(data, end, f"{field}.motionAssetPathHash")
    motion_tag, cursor = _read_u32(data, cursor, f"{field}.motionTag")
    motion_type, cursor = _read_i32(data, cursor, f"{field}.motionType")
    duration, cursor = _read_f32(data, cursor, f"{field}.transitionInfo.fixedTransitionDuration")
    transition_type, cursor = _read_i32(
        data, cursor, f"{field}.transitionInfo.fixedTransitionType"
    )
    direct, cursor = _read_strict_bool(data, cursor, f"{field}.useAssetDirectly")
    return {
        "memberCount": 5,
        "motionAssetPathHash": path_hash,
        "motionTag": motion_tag,
        "motionType": motion_type,
        "transitionInfo": {
            "fixedTransitionDuration": duration,
            "fixedTransitionType": transition_type,
        },
        "useAssetDirectly": direct,
    }, cursor


def _read_move_additive_anims(
    data: bytes, offset: int, field: str,
) -> tuple[dict[str, Any], int]:
    end = _require(data, offset, 1, f"{field}.memberCount")
    marker = data[offset]
    if marker == 0xFF:
        return {"status": "null", "count": None, "rows": []}, end
    count, cursor = _read_count(data, end, field, maximum=256)
    if count is None:
        raise AnimationConfigFramingError(f"{field}:null inner dictionary")
    rows = []
    for index in range(count):
        start = cursor
        key, cursor = _read_string(data, cursor, f"{field}[{index}].key")
        if key is None:
            raise AnimationConfigFramingError(f"{field}[{index}].key:null")
        value_end = _require(data, cursor, 1, f"{field}[{index}].value.memberCount")
        if data[cursor] != 5:
            raise AnimationConfigFramingError(
                f"{field}[{index}].value.memberCount:expected=5 actual={data[cursor]}"
            )
        values: dict[str, Any] = {}
        values["idleClipInfo"], cursor = _read_animation_clip_async_info(
            data, value_end, f"{field}[{index}].value.idleClipInfo"
        )
        values["runClipInfo"], cursor = _read_animation_clip_async_info(
            data, cursor, f"{field}[{index}].value.runClipInfo"
        )
        values["skMorphMotionSetting"], cursor = _read_sk_morph_play_setting(
            data, cursor, f"{field}[{index}].value.skMorphMotionSetting"
        )
        values["sprintClipInfo"], cursor = _read_animation_clip_async_info(
            data, cursor, f"{field}[{index}].value.sprintClipInfo"
        )
        values["walkClipInfo"], cursor = _read_animation_clip_async_info(
            data, cursor, f"{field}[{index}].value.walkClipInfo"
        )
        rows.append({"key": key, "value": values, "startOffset": start, "endOffset": cursor})
    return {"status": "present", "memberCount": marker, "count": count, "rows": rows}, cursor


def _read_char_hurt_configs(
    data: bytes, offset: int, field: str,
) -> tuple[dict[str, Any], int]:
    end = _require(data, offset, 1, f"{field}.memberCount")
    if data[offset] == 0xFF:
        return {"status": "null", "count": None, "rows": []}, end
    count, cursor = _read_count(data, end, field, maximum=256)
    if count is None:
        raise AnimationConfigFramingError(f"{field}:null inner dictionary")
    rows = []
    for index in range(count):
        start = cursor
        key, cursor = _read_i32(data, cursor, f"{field}[{index}].key")
        marker_end = _require(data, cursor, 1, f"{field}[{index}].value.memberCount")
        if data[cursor] != 3:
            raise AnimationConfigFramingError(
                f"{field}[{index}].value.memberCount:expected=3 actual={data[cursor]}"
            )
        curve, cursor = _read_fanimation_curve(
            data, marker_end, f"{field}[{index}].value.rootMotionCurve"
        )
        scaled_x, cursor = _read_f32(
            data, cursor, f"{field}[{index}].value.rootMotionScaledTime.x"
        )
        scaled_y, cursor = _read_f32(
            data, cursor, f"{field}[{index}].value.rootMotionScaledTime.y"
        )
        morph, cursor = _read_sk_morph_play_setting(
            data, cursor, f"{field}[{index}].value.skMorphMotionSetting"
        )
        rows.append({
            "key": key,
            "value": {
                "memberCount": 3,
                "rootMotionCurve": curve,
                "rootMotionScaledTime": [scaled_x, scaled_y],
                "skMorphMotionSetting": morph,
            },
            "startOffset": start, "endOffset": cursor,
        })
    return {"status": "present", "count": count, "rows": rows}, cursor


def _read_empty_dictionary(
    data: bytes, offset: int, field: str,
) -> tuple[dict[str, Any], int]:
    end = _require(data, offset, 1, f"{field}.memberCount")
    marker = data[offset]
    if marker == 0xFF:
        return {"status": "null", "count": None}, end
    count, cursor = _read_count(data, end, field, maximum=0)
    if count != 0:
        raise AnimationConfigFramingError(f"{field}:expected-empty actual={count}")
    return {"status": "present", "memberCount": marker, "count": 0}, cursor


def _read_string_list(data: bytes, offset: int, field: str) -> tuple[list[str] | None, int]:
    count, cursor = _read_count(data, offset, field, maximum=4096)
    if count is None:
        return None, cursor
    rows = []
    for index in range(count):
        value, cursor = _read_string(data, cursor, f"{field}[{index}]")
        if value is None:
            raise AnimationConfigFramingError(f"{field}[{index}]:null")
        rows.append(value)
    return rows, cursor


def _read_i32_list(data: bytes, offset: int, field: str) -> tuple[list[int] | None, int]:
    count, cursor = _read_count(data, offset, field, maximum=4096)
    if count is None:
        return None, cursor
    end = _require(data, cursor, count * 4, field)
    return list(struct.unpack_from("<" + "i" * count, data, cursor)), end


def _read_special_idle_condition(
    data: bytes, offset: int, field: str,
) -> tuple[dict[str, Any], int]:
    end = _require(data, offset, 2, f"{field}.union")
    tag = data[offset]
    member_count = data[offset + 1]
    cursor = end
    expected = {0: 6, 1: 4, 2: 1, 3: 2, 4: 1, 5: 2}.get(tag)
    if expected is None or member_count != expected:
        raise AnimationConfigFramingError(
            f"{field}:unsupported-tag-or-member-count tag={tag} memberCount={member_count}"
        )
    fields: dict[str, Any] = {}
    type_name = {
        0: "CameraPropertyCondition",
        1: "FloorBumpCondition",
        2: "IdleTimeCondition",
        3: "IKCastCondition",
        4: "LODScreenSizeCondition",
        5: "TransformInSightCondition",
    }[tag]
    if tag == 0:
        fields["enableForSquadMember"], cursor = _read_strict_bool(data, cursor, field + ".enableForSquadMember")
        fields["invertRange"], cursor = _read_strict_bool(data, cursor, field + ".invertRange")
        lo, cursor = _read_f32(data, cursor, field + ".relativeAngleDegreeRange.x")
        hi, cursor = _read_f32(data, cursor, field + ".relativeAngleDegreeRange.y")
        fields["relativeAngleDegreeRange"] = [lo, hi]
        fields["useRelativeAngle"], cursor = _read_strict_bool(data, cursor, field + ".useRelativeAngle")
        fields["useVerticalValue"], cursor = _read_strict_bool(data, cursor, field + ".useVerticalValue")
        lo, cursor = _read_f32(data, cursor, field + ".verticalValueRange.x")
        hi, cursor = _read_f32(data, cursor, field + ".verticalValueRange.y")
        fields["verticalValueRange"] = [lo, hi]
    elif tag == 1:
        for name in ("bumpThreshold", "radius", "stepUp"):
            fields[name], cursor = _read_f32(data, cursor, f"{field}.{name}")
        fields["checkComplex"], cursor = _read_strict_bool(data, cursor, field + ".checkComplex")
    elif tag == 2:
        fields["minIdleTime"], cursor = _read_f32(data, cursor, field + ".minIdleTime")
    elif tag == 3:
        fields["maxOffsetAngle"], cursor = _read_f32(data, cursor, field + ".maxOffsetAngle")
        fields["maxSlopeAngle"], cursor = _read_f32(data, cursor, field + ".maxSlopeAngle")
    elif tag == 4:
        lo, cursor = _read_f32(data, cursor, field + ".screenRelativeSizeRange.x")
        hi, cursor = _read_f32(data, cursor, field + ".screenRelativeSizeRange.y")
        fields["screenRelativeSizeRange"] = [lo, hi]
    else:
        fields["targetPaths"], cursor = _read_string_list(data, cursor, field + ".targetPaths")
        fields["threshold"], cursor = _read_f32(data, cursor, field + ".threshold")
    return {"tag": tag, "type": type_name, "memberCount": member_count, "fields": fields}, cursor


def _read_special_dash_config(
    data: bytes, offset: int, field: str,
) -> tuple[dict[str, Any] | None, int]:
    end = _require(data, offset, 1, f"{field}.memberCount")
    marker = data[offset]
    if marker == 0xFF:
        return None, end
    if marker != 3:
        raise AnimationConfigFramingError(f"{field}.memberCount:expected=null-or-3 actual={marker}")
    count, cursor = _read_count(data, end, f"{field}.entries", maximum=4096)
    if count is None:
        raise AnimationConfigFramingError(f"{field}.entries:null")
    entries = []
    for index in range(count):
        start = cursor
        cursor = _require(data, cursor, 1, f"{field}.entries[{index}].memberCount")
        if data[start] != 2:
            raise AnimationConfigFramingError(f"{field}.entries[{index}].memberCount:expected=2 actual={data[start]}")
        memo, cursor = _read_string(data, cursor, f"{field}.entries[{index}].memo")
        indexes, cursor = _read_i32_list(data, cursor, f"{field}.entries[{index}].performSpDashIndexes")
        entries.append({"memo": memo, "performSpDashIndexes": indexes})
    forbid, cursor = _read_strict_bool(data, cursor, field + ".forbidPivotAndTurnStart")
    dashes, cursor = _read_string_list(data, cursor, field + ".spDashes")
    return {"memberCount": marker, "entries": entries, "forbidPivotAndTurnStart": forbid, "spDashes": dashes}, cursor


def _read_special_idle_config(
    data: bytes, offset: int, field: str,
) -> tuple[dict[str, Any] | None, int]:
    end = _require(data, offset, 1, f"{field}.memberCount")
    marker = data[offset]
    if marker == 0xFF:
        return None, end
    if marker != 2:
        raise AnimationConfigFramingError(f"{field}.memberCount:expected=null-or-2 actual={marker}")
    count, cursor = _read_count(data, end, f"{field}.entries", maximum=4096)
    if count is None:
        raise AnimationConfigFramingError(f"{field}.entries:null")
    entries = []
    for index in range(count):
        start = cursor
        cursor = _require(data, cursor, 1, f"{field}.entries[{index}].memberCount")
        if data[start] != 4:
            raise AnimationConfigFramingError(f"{field}.entries[{index}].memberCount:expected=4 actual={data[start]}")
        condition_count, cursor = _read_count(data, cursor, f"{field}.entries[{index}].conditions", maximum=128)
        if condition_count is None:
            conditions = None
        else:
            conditions = []
            for condition_index in range(condition_count):
                condition, cursor = _read_special_idle_condition(
                    data, cursor, f"{field}.entries[{index}].conditions[{condition_index}]"
                )
                conditions.append(condition)
        memo, cursor = _read_string(data, cursor, f"{field}.entries[{index}].memo")
        indexes, cursor = _read_i32_list(data, cursor, f"{field}.entries[{index}].performSpIdleIndexes")
        trigger_once, cursor = _read_strict_bool(data, cursor, f"{field}.entries[{index}].triggerOnce")
        entries.append({"conditions": conditions, "memo": memo, "performSpIdleIndexes": indexes, "triggerOnce": trigger_once})
    idles, cursor = _read_string_list(data, cursor, field + ".spIdles")
    return {"memberCount": marker, "entries": entries, "spIdles": idles}, cursor


def _read_state_perform_entries(
    data: bytes, offset: int, field: str,
) -> tuple[list[dict[str, Any]] | None, int]:
    count, cursor = _read_count(data, offset, field, maximum=4096)
    if count is None:
        return None, cursor
    rows = []
    for index in range(count):
        start = cursor
        cursor = _require(data, cursor, 1, f"{field}[{index}].memberCount")
        if data[start] != 3:
            raise AnimationConfigFramingError(f"{field}[{index}].memberCount:expected=3 actual={data[start]}")
        state_hash, cursor = _read_u32(data, cursor, f"{field}[{index}].stateHash")
        perform_id, cursor = _read_string(data, cursor, f"{field}[{index}].performId")
        interrupt_type, cursor = _read_i32(data, cursor, f"{field}[{index}].interruptType")
        rows.append({"stateHash": state_hash, "performId": perform_id, "interruptType": interrupt_type})
    return rows, cursor


def _read_i32_values(
    data: bytes, offset: int, field: str, *, maximum: int = 256,
) -> tuple[list[int] | None, int]:
    count, cursor = _read_count(data, offset, field, maximum=maximum)
    if count is None:
        return None, cursor
    values = []
    for index in range(count):
        value, cursor = _read_i32(data, cursor, f"{field}[{index}]")
        values.append(value)
    return values, cursor


def _read_enemy_blow_off_config(
    data: bytes, offset: int, field: str,
) -> tuple[dict[str, Any] | None, int]:
    end = _require(data, offset, 1, f"{field}.memberCount")
    marker = data[offset]
    if marker == 0xFF:
        return None, end
    if marker != 3:
        raise AnimationConfigFramingError(
            f"{field}.memberCount:expected=null-or-3 actual={marker}"
        )
    total, cursor = _read_f32(data, end, field + ".animTotalTime")
    curve_y, cursor = _read_fanimation_curve(data, cursor, field + ".rootMotionCurvePosY")
    curve_z, cursor = _read_fanimation_curve(data, cursor, field + ".rootMotionCurvePosZ")
    return {
        "memberCount": marker,
        "animTotalTime": total,
        "rootMotionCurvePosY": curve_y,
        "rootMotionCurvePosZ": curve_z,
    }, cursor


def _read_enemy_hurt_entry(
    data: bytes, offset: int, field: str,
) -> tuple[dict[str, Any], int]:
    end = _require(data, offset, 1, f"{field}.memberCount")
    if data[offset] != 7:
        raise AnimationConfigFramingError(
            f"{field}.memberCount:expected=7 actual={data[offset]}"
        )
    values: dict[str, Any] = {"memberCount": 7}
    for name in ("customDeadAnimOffset", "customDeadDelay", "immobilizedTime"):
        values[name], end = _read_f32(data, end, f"{field}.{name}")
    values["overrideDeadDelay"], end = _read_strict_bool(data, end, field + ".overrideDeadDelay")
    values["rootMotionCurve"], end = _read_fanimation_curve(data, end, field + ".rootMotionCurve")
    end2 = _require(data, end, 8, field + ".rootMotionScaledTime")
    values["rootMotionScaledTime"] = list(struct.unpack_from("<ff", data, end))
    values["unmovableTime"], end = _read_f32(data, end2, field + ".unmovableTime")
    return values, end


def _read_enemy_hurt_configs(
    data: bytes, offset: int, field: str,
) -> tuple[dict[str, Any], int]:
    end = _require(data, offset, 1, f"{field}.memberCount")
    marker = data[offset]
    if marker == 0xFF:
        return {"status": "null", "count": None, "rows": []}, end
    count, cursor = _read_count(data, end, field, maximum=256)
    if count is None:
        raise AnimationConfigFramingError(f"{field}:null inner dictionary")
    rows = []
    for index in range(count):
        key, cursor = _read_i32(data, cursor, f"{field}[{index}].key")
        value, cursor = _read_enemy_hurt_entry(data, cursor, f"{field}[{index}].value")
        rows.append({"key": key, "value": value})
    return {"status": "present", "memberCount": marker, "count": count, "rows": rows}, cursor


def _read_enemy_shake_configs(
    data: bytes, offset: int, field: str,
) -> tuple[dict[str, Any], int]:
    end = _require(data, offset, 1, f"{field}.memberCount")
    marker = data[offset]
    if marker == 0xFF:
        return {"status": "null", "count": None, "rows": []}, end
    count, cursor = _read_count(data, end, field, maximum=256)
    if count is None:
        raise AnimationConfigFramingError(f"{field}:null inner dictionary")
    rows = []
    for index in range(count):
        key_end = _require(data, cursor, 1, f"{field}[{index}].key")
        key = data[cursor]
        cursor = key_end
        value_end = _require(data, cursor, 9, f"{field}[{index}].value")
        if data[cursor] != 2:
            raise AnimationConfigFramingError(
                f"{field}[{index}].value.memberCount:expected=2 actual={data[cursor]}"
            )
        speed, weight = struct.unpack_from("<ff", data, cursor + 1)
        if not math.isfinite(speed) or not math.isfinite(weight):
            raise AnimationConfigFramingError(f"{field}[{index}].value:non-finite")
        cursor = value_end
        rows.append({"key": key, "value": {"animationSpeed": speed, "animationWeight": weight}})
    return {"status": "present", "memberCount": marker, "count": count, "rows": rows}, cursor


def _read_enemy_hurt_data(
    data: bytes, offset: int, field: str,
) -> tuple[dict[str, Any] | None, int]:
    end = _require(data, offset, 1, f"{field}.memberCount")
    marker = data[offset]
    if marker == 0xFF:
        return None, end
    if marker != 10:
        raise AnimationConfigFramingError(
            f"{field}.memberCount:expected=null-or-10 actual={marker}"
        )
    values: dict[str, Any] = {"memberCount": marker}
    values["additiveHurtClipValid"], end = _read_strict_bool(data, end, field + ".additiveHurtClipValid")
    values["forceFullHurtWhenPoiseBroken"], end = _read_strict_bool(data, end, field + ".forceFullHurtWhenPoiseBroken")
    values["fullBodyTurnList"], end = _read_i32_values(data, end, field + ".fullBodyTurnList")
    values["hurtAnimConfigs"], end = _read_enemy_hurt_configs(data, end, field + ".hurtAnimConfigs")
    values["hurtAnimValidMask"], end = _read_i32(data, end, field + ".hurtAnimValidMask")
    values["hurtShakeAnimConfigs"], end = _read_enemy_shake_configs(data, end, field + ".hurtShakeAnimConfigs")
    values["hurtShakeClipDuration"], end = _read_f32(data, end, field + ".hurtShakeClipDuration")
    values["staggerTurnList"], end = _read_i32_values(data, end, field + ".staggerTurnList")
    values["supportedHurtAnimMask"], end = _read_i32(data, end, field + ".supportedHurtAnimMask")
    values["useMeshSpaceFullBodyAdd"], end = _read_strict_bool(data, end, field + ".useMeshSpaceFullBodyAdd")
    return values, end


def _read_enemy_turn_start_data(
    data: bytes, offset: int, field: str,
) -> tuple[dict[str, Any] | None, int]:
    end = _require(data, offset, 1, f"{field}.memberCount")
    marker = data[offset]
    if marker == 0xFF:
        return None, end
    if marker != 2:
        raise AnimationConfigFramingError(
            f"{field}.memberCount:expected=null-or-2 actual={marker}"
        )
    duration, end = _read_f32(data, end, field + ".duration")
    yaw, end = _read_f32(data, end, field + ".totalYawRotationDegrees")
    return {"memberCount": marker, "duration": duration, "totalYawRotationDegrees": yaw}, end


def _read_alpha_blend(data: bytes, offset: int, field: str) -> tuple[dict[str, Any], int]:
    end = _require(data, offset, 1, f"{field}.memberCount")
    if data[offset] != 3:
        raise AnimationConfigFramingError(f"{field}.memberCount:expected=3 actual={data[offset]}")
    blend_option, cursor = _read_i32(data, end, f"{field}.blendOption")
    blend_time, cursor = _read_f32(data, cursor, f"{field}.blendTime")
    custom_curve, cursor = _read_fanimation_curve(data, cursor, f"{field}.customCurve")
    return {
        "memberCount": 3,
        "blendOption": blend_option,
        "blendTime": blend_time,
        "customCurve": custom_curve,
    }, cursor


def _read_animation_clip_async_info(
    data: bytes, offset: int, field: str,
) -> tuple[dict[str, Any], int]:
    end = _require(data, offset, 36, field)
    path_hash = struct.unpack_from("<q", data, offset)[0]
    length, framerate = struct.unpack_from("<ff", data, offset + 8)
    average_speed = list(struct.unpack_from("<fff", data, offset + 16))
    angular_speed = struct.unpack_from("<f", data, offset + 28)[0]
    humanoid, looping = data[offset + 32:offset + 34]
    padding = data[offset + 34:offset + 36]
    if (
        not all(math.isfinite(v) for v in (length, framerate, *average_speed, angular_speed))
        or humanoid not in (0, 1)
        or looping not in (0, 1)
        or padding != b"\x00\x00"
    ):
        raise AnimationConfigFramingError(f"{field}:invalid-fixed-36-byte-value")
    return {
        "montagePathHash": path_hash,
        "length": length,
        "framerate": framerate,
        "averageSpeed": average_speed,
        "averageAngularSpeed": angular_speed,
        "isHumanoid": bool(humanoid),
        "isLooping": bool(looping),
        "paddingHex": padding.hex(),
    }, end


def _read_anim_montage_base(
    data: bytes, offset: int, field: str,
) -> tuple[dict[str, Any], int]:
    fields: dict[str, Any] = {}
    cursor = offset
    fields["_autoBlendOut"], cursor = _read_strict_bool(data, cursor, field + "._autoBlendOut")
    fields["_autoBlendOutTargetHash"], cursor = _read_i32(data, cursor, field + "._autoBlendOutTargetHash")
    fields["_bFixedDuration"], cursor = _read_strict_bool(data, cursor, field + "._bFixedDuration")
    fields["_blendOut"], cursor = _read_alpha_blend(data, cursor, field + "._blendOut")
    fields["_blink"], cursor = _read_strict_bool(data, cursor, field + "._blink")
    fields["_emotionUsePath"], cursor = _read_strict_bool(data, cursor, field + "._emotionUsePath")
    cursor = _require(data, cursor, 2, field + ".layerIndexes")
    fields["_layerIndex"] = struct.unpack_from("<b", data, cursor - 2)[0]
    fields["_layerIndexOpt"] = struct.unpack_from("<b", data, cursor - 1)[0]
    fields["_morphMotionPathHash"], cursor = _read_i64(data, cursor, field + "._morphMotionPathHash")
    fields["_morphMotionTag"], cursor = _read_u32(data, cursor, field + "._morphMotionTag")
    fields["_morphType"], cursor = _read_i32(data, cursor, field + "._morphType")
    fields["_morphWeight"], cursor = _read_f32(data, cursor, field + "._morphWeight")
    fields["_playMorph"], cursor = _read_strict_bool(data, cursor, field + "._playMorph")
    fields["_transitionDuration"], cursor = _read_f32(data, cursor, field + "._transitionDuration")
    fields["_transitionOffset"], cursor = _read_f32(data, cursor, field + "._transitionOffset")
    fields["preloadClips"], cursor = _read_strict_bool(data, cursor, field + ".preloadClips")
    fields["skipPreload"], cursor = _read_strict_bool(data, cursor, field + ".skipPreload")
    return fields, cursor


def _read_anim_montage(
    data: bytes, offset: int, field: str,
) -> tuple[dict[str, Any], int]:
    union_end = _require(data, offset, 2, field + ".union")
    tag = data[offset]
    member_count = data[offset + 1]
    if (tag, member_count) not in ((0, 26), (1, 20)):
        raise AnimationConfigFramingError(
            f"{field}:unsupported-union tag={tag} memberCount={member_count}"
        )
    fields, cursor = _read_anim_montage_base(data, union_end, field)
    if tag == 0:
        fields["clipInfo"], cursor = _read_animation_clip_async_info(data, cursor, field + ".clipInfo")
        fields["isUseRootMotionRot"], cursor = _read_strict_bool(data, cursor, field + ".isUseRootMotionRot")
        for name in (
            "rootMotionCurvePosX", "rootMotionCurvePosY", "rootMotionCurvePosZ",
            "rootMotionCurveRotW", "rootMotionCurveRotX", "rootMotionCurveRotY",
            "rootMotionCurveRotZ",
        ):
            fields[name], cursor = _read_fanimation_curve(data, cursor, f"{field}.{name}")
        type_name = "ClipMontageData"
    else:
        for name in ("endClipInfo", "loopClipInfo", "startClipInfo"):
            fields[name], cursor = _read_animation_clip_async_info(data, cursor, f"{field}.{name}")
        type_name = "SequenceMontageData"
    return {
        "tag": tag,
        "type": type_name,
        "memberCount": member_count,
        "fields": fields,
    }, cursor


def _read_montage_dictionary(
    data: bytes, offset: int, field: str,
) -> tuple[dict[str, Any], int]:
    end = _require(data, offset, 1, f"{field}.memberCount")
    marker = data[offset]
    if marker == 0xFF:
        return {"status": "null", "count": None, "rows": []}, end
    count, cursor = _read_count(data, end, field, maximum=4096)
    if count is None:
        raise AnimationConfigFramingError(f"{field}:null inner dictionary")
    rows = []
    for index in range(count):
        start = cursor
        key, cursor = _read_string(data, cursor, f"{field}[{index}].key")
        if key is None:
            raise AnimationConfigFramingError(f"{field}[{index}].key:null")
        value, cursor = _read_anim_montage(data, cursor, f"{field}[{index}].value")
        rows.append({"key": key, "value": value, "startOffset": start, "endOffset": cursor})
    return {
        "status": "present",
        "memberCount": marker,
        "count": count,
        "rows": rows,
    }, cursor


def _decode_extra_data_prefix(data: bytes, header: dict[str, Any]) -> dict[str, Any]:
    """Decode the current common base and bounded subtype prefix."""
    if header["closed"]:
        return {"endOffset": header["headerEndOffset"], "fields": {}}
    cursor = header["headerEndOffset"]
    fields: dict[str, Any] = {}
    fields["animatedShaderPropertyCfg"], cursor = _read_shader_property_config(
        data, cursor, "extraData.animatedShaderPropertyCfg"
    )
    fields["animationEventPlayEffectCfg"], cursor = _read_play_effect_config(
        data, cursor, "extraData.animationEventPlayEffectCfg"
    )
    fields["animationEventRendererVisibilityCfg"], cursor = _read_renderer_visibility_config(
        data, cursor, "extraData.animationEventRendererVisibilityCfg"
    )
    for name in (
        "enableAnimatedShaderProperty",
        "enableAnimationEventPlayEffect",
        "enableAnimationEventRendererVisibility",
    ):
        fields[name], cursor = _read_strict_bool(data, cursor, f"extraData.{name}")

    if header["subtype"] == "EnemyAnimExtraData":
        fields["alertAnimTime"], cursor = _read_f32(data, cursor, "extraData.alertAnimTime")
        fields["blackboardType"], cursor = _read_i32(data, cursor, "extraData.blackboardType")
        fields["blowOffConfig"], cursor = _read_enemy_blow_off_config(
            data, cursor, "extraData.blowOffConfig"
        )
        for name in ("exitVigilanceTime", "getUpAnimLength", "getUpTime"):
            fields[name], cursor = _read_f32(data, cursor, f"extraData.{name}")
        fields["hurtAnimData"], cursor = _read_enemy_hurt_data(
            data, cursor, "extraData.hurtAnimData"
        )
        fields["idleSPCount"], cursor = _read_i32(data, cursor, "extraData.idleSPCount")
        fields["idleToFightIdleTime"], cursor = _read_f32(
            data, cursor, "extraData.idleToFightIdleTime"
        )
        fields["isPatrolTurnRight"], cursor = _read_strict_bool(
            data, cursor, "extraData.isPatrolTurnRight"
        )
        for name in ("lieDownAnimLength", "lieDownTime"):
            fields[name], cursor = _read_f32(data, cursor, f"extraData.{name}")
        fields["turnStartData"], cursor = _read_enemy_turn_start_data(
            data, cursor, "extraData.turnStartData"
        )
        fields["walkStopTime"], cursor = _read_f32(data, cursor, "extraData.walkStopTime")
        return {"endOffset": cursor, "fields": fields, "closed": True}

    scalar_fields = (
        ("_strafeAngleHorizontalThresholdDeg", "f32"),
        ("_strafeAngleSmoothSpeed", "f32"),
        ("_strafeAngleThresholdDeg", "f32"),
        ("_strafeMagnitudeSmoothSpeed", "f32"),
        ("characterBlackboardType", "i32"),
        ("clothIKDirectionNormalizeAngleDeg", "f32"),
        ("clothIKLegAdaptAngleDeg", "f32"),
        ("dashDuration", "f32"),
        ("duringTransitionClothFrontScale", "f32"),
    )
    for name, kind in scalar_fields:
        reader = _read_i32 if kind == "i32" else _read_f32
        fields[name], cursor = reader(data, cursor, f"extraData.{name}")
    fields["hasSpDash"], cursor = _read_strict_bool(data, cursor, "extraData.hasSpDash")
    fields["hurtAnimConfigs"], cursor = _read_char_hurt_configs(
        data, cursor, "extraData.hurtAnimConfigs"
    )
    fields["ikReverseAffectSkirtPhysicsFactor"], cursor = _read_f32(
        data, cursor, "extraData.ikReverseAffectSkirtPhysicsFactor"
    )
    fields["isHoldBombWithBothHands"], cursor = _read_strict_bool(
        data, cursor, "extraData.isHoldBombWithBothHands"
    )
    for name in (
        "jumpStartBlendInTime",
        "magicaClothWeightDecreaseSpeed",
        "magicaClothWeightIncreaseSpeed",
    ):
        fields[name], cursor = _read_f32(data, cursor, f"extraData.{name}")
    fields["moveAdditiveAnims"], cursor = _read_move_additive_anims(
        data, cursor, "extraData.moveAdditiveAnims"
    )
    fields["overrideDashDuration"], cursor = _read_strict_bool(
        data, cursor, "extraData.overrideDashDuration"
    )
    fields["overridePerformDict"], cursor = _read_empty_dictionary(
        data, cursor, "extraData.overridePerformDict"
    )
    fields["runSpLoopCount"], cursor = _read_i32(data, cursor, "extraData.runSpLoopCount")
    fields["spDashConfig"], cursor = _read_special_dash_config(
        data, cursor, "extraData.spDashConfig"
    )
    fields["spIdleConfig"], cursor = _read_special_idle_config(
        data, cursor, "extraData.spIdleConfig"
    )
    fields["statePerformEntries"], cursor = _read_state_perform_entries(
        data, cursor, "extraData.statePerformEntries"
    )
    fields["walkSpLoopCount"], cursor = _read_i32(
        data, cursor, "extraData.walkSpLoopCount"
    )
    if header["subtype"] == "UpperBodyFightExtraData":
        fields["upperBodyFightTimeout"], cursor = _read_f32(
            data, cursor, "extraData.upperBodyFightTimeout"
        )
        fields["upperBodyLayerName"], cursor = _read_string(
            data, cursor, "extraData.upperBodyLayerName"
        )
        if fields["upperBodyLayerName"] is None:
            raise AnimationConfigFramingError("extraData.upperBodyLayerName:null")
    return {"endOffset": cursor, "fields": fields, "closed": True}


def _decode_montages_tail(data: bytes, offset: int) -> dict[str, Any]:
    """Close the exact root tail for supported montage values."""
    start = offset
    montages, cursor = _read_montage_dictionary(data, offset, "montages")
    npc_count, cursor = _read_count(data, cursor, "npcMontages", maximum=_MAX_CURVE_COUNT)
    npc_montages = []
    for index in range(npc_count or 0):
        tag_end = _require(data, cursor, 1, f"npcMontages[{index}].memberCount")
        if data[cursor] != 1:
            raise AnimationConfigFramingError(
                f"npcMontages[{index}].memberCount:expected=1 actual={data[cursor]}"
            )
        tag, cursor = _read_u32(data, tag_end, f"npcMontages[{index}].value")
        npc_montages.append({"memberCount": 1, "value": tag})
    opt_controller_path, cursor = _read_i64(data, cursor, "optControllerPath")
    retarget_path, cursor = _read_i64(data, cursor, "retargetAnimConfigPath")
    animation_curve_count, cursor = _read_count(
        data, cursor, "syncGroupAnimationCurves", maximum=0
    )
    if animation_curve_count != 0:
        raise AnimationConfigFramingError(
            "syncGroupAnimationCurves:only empty current variant is supported"
        )
    sync_curves, cursor = _read_curve_dictionary(
        data, cursor, "syncGroupCurves", string_keys=True
    )
    time_curves, cursor = _read_curve_dictionary(
        data, cursor, "timeRefCurves", string_keys=False
    )
    cursor = _require(data, cursor, 2, "AnimationConfig booleans")
    rotate, state_variables = data[cursor - 2:cursor]
    if rotate not in (0, 1) or state_variables not in (0, 1):
        raise AnimationConfigFramingError(
            "AnimationConfig booleans:expected strict 0/1"
        )
    if cursor != len(data):
        raise AnimationConfigFramingError(
            f"AnimationConfig trailing bytes: consumed={cursor} size={len(data)}"
        )
    return {
        "startOffset": start,
        "endOffset": cursor,
        "fields": {
            "montages": montages,
            "npcMontages": npc_montages,
            "optControllerPath": opt_controller_path,
            "retargetAnimConfigPath": retarget_path,
            "syncGroupAnimationCurves": {},
            "syncGroupCurves": sync_curves,
            "timeRefCurves": time_curves,
            "useRotateDirection": bool(rotate),
            "useStateVariables": bool(state_variables),
        },
    }


def frame_animation_config(data: bytes) -> dict[str, Any]:
    """Frame the proven prefix and one exact named 72-byte variant.

    The generated wrapper setter metadata fixes the first five members and the
    two-member ``BoneWeightMaskJsonEntry`` order. The reader advances those
    values at a real cursor, then preserves ``extraData`` and all later members
    as one opaque remainder. The current 72-byte variant is separately decoded:
    it contains no bone masks, montage rows, NPC montage tags, curves, or extra
    data, and consumes exactly to EOF.
    """
    if not data:
        raise AnimationConfigFramingError(
            "truncated AnimationConfig: empty payload"
        )
    if data[0] != 15:
        raise AnimationConfigFramingError(
            "AnimationConfig member count mismatch: "
            f"expected=15 actual={data[0]}"
        )
    named_prefix = _decode_named_prefix(data)
    extra_data = _decode_extra_data_header(data, named_prefix["endOffset"])
    proven_end = extra_data["headerEndOffset"]
    if not extra_data["closed"]:
        try:
            decoded_extra_prefix = _decode_extra_data_prefix(data, extra_data)
        except AnimationConfigFramingError as exc:
            extra_data["prefixError"] = str(exc)
        else:
            proven_end = decoded_extra_prefix["endOffset"]
            extra_data["prefix"] = decoded_extra_prefix
            extra_data["endOffset"] = proven_end

    base: dict[str, Any] = {
        "schemaStatus": "partial",
        "serializedMemberCount": 15,
        "bytesConsumed": proven_end,
        "prefix": named_prefix,
        "extraData": extra_data,
    }

    extra_prefix = extra_data.get("prefix") or {}
    if extra_data["closed"] or extra_prefix.get("closed"):
        try:
            tail = _decode_montages_tail(data, proven_end)
        except AnimationConfigFramingError:
            tail = None
        if tail is not None:
            fields = dict(named_prefix["fields"])
            fields["extraData"] = (
                None if extra_data["status"] == "null" else extra_prefix.get("fields", {})
            )
            fields.update(tail["fields"])
            base.update({
                "status": "exact_named_animation_config_frame",
                "schemaStatus": "named_exact",
                "bytesConsumed": len(data),
                "fieldOrder": list(ANIMATION_CONFIG_FIELDS),
                "fields": fields,
                "ranges": [
                    {"startOffset": 0, "endOffset": proven_end,
                     "fields": list(ANIMATION_CONFIG_FIELDS[:6])},
                    {"startOffset": proven_end, "endOffset": len(data),
                     "fields": list(ANIMATION_CONFIG_FIELDS[6:])},
                ],
                "opaqueRanges": [],
                "evidenceBoundary": (
                    "All bytes are assigned to the current generated 15-field wrapper. "
                    "The montage dictionary accepts only the authenticated current "
                    "ClipMontageData and SequenceMontageData variants; path hashes and "
                    "GameplayTag values remain numeric identities."
                ),
            })
            return base

    if (
        len(data) == 72
        and data[:22] == FIXED_72_PREFIX
        and data[30:] == FIXED_72_SUFFIX
    ):
        controller_path = int.from_bytes(data[22:30], "little", signed=True)
        base.update({
            "status": "exact_named_72_byte_frame",
            "schemaStatus": "named_exact",
            "bytesConsumed": len(data),
            "fieldOrder": list(ANIMATION_CONFIG_FIELDS),
            "fields": {
                "_fallbackMontages": None,
                "avatarBlendProfilePath": 0,
                "bakedBindingPath": 0,
                "boneWeightMasks": [],
                "controllerPath": controller_path,
                "extraData": None,
                "montages": {},
                "npcMontages": [],
                "optControllerPath": 0,
                "retargetAnimConfigPath": 0,
                "syncGroupAnimationCurves": {},
                "syncGroupCurves": {},
                "timeRefCurves": {},
                "useRotateDirection": False,
                "useStateVariables": False,
            },
            "ranges": [
                {
                    "startOffset": 0,
                    "endOffset": 1,
                    "field": "$memberCount",
                    "value": 15,
                },
                {
                    "startOffset": 1,
                    "endOffset": 2,
                    "field": "_fallbackMontages",
                    "value": None,
                },
                {
                    "startOffset": 2,
                    "endOffset": 30,
                    "fields": [
                        "avatarBlendProfilePath",
                        "bakedBindingPath",
                        "boneWeightMasks",
                        "controllerPath",
                    ],
                },
                {
                    "startOffset": 30,
                    "endOffset": 31,
                    "field": "extraData",
                    "value": None,
                },
                {
                    "startOffset": 31,
                    "endOffset": 72,
                    "fields": list(ANIMATION_CONFIG_FIELDS[6:]),
                },
            ],
            "opaqueRanges": [],
            "evidenceBoundary": (
                "All 72 bytes are assigned to the current generated wrapper's "
                "15-field read order and exactly consumed. StringPathHash values "
                "remain numeric identities; this does not resolve their source paths."
            ),
        })
        return base

    base.update({
        "status": "exact_named_prefix_with_opaque_remainder",
        "ranges": [
            {
                "startOffset": 0,
                "endOffset": 1,
                "field": "$memberCount",
                "value": 15,
            },
            {
                "startOffset": 1,
                "endOffset": named_prefix["endOffset"],
                "fields": list(ANIMATION_CONFIG_PREFIX_FIELDS),
                "status": "exact_named_generated_wrapper_prefix",
            },
            {
                "startOffset": named_prefix["endOffset"],
                "endOffset": proven_end,
                "field": "extraData",
                "status": (
                    "exact_closed_object"
                    if extra_data["closed"] or extra_prefix.get("closed")
                    else "exact_object_header"
                ),
            },
            {
                "startOffset": proven_end,
                "endOffset": len(data),
                "status": "opaque_unassigned_payload",
            },
        ],
        "opaqueRanges": [{
            "startOffset": proven_end,
            "endOffset": len(data),
            "length": len(data) - proven_end,
        }],
        "evidenceBoundary": (
                "The generated wrapper setter order and nested two-member mask rows "
                "name the first five members through controllerPath at an exact "
                "cursor. The following AnimationConfigExtraData union tag and concrete "
                "object header are exact. Supported character prefixes additionally "
                "name the common shader/event configuration, subtype scalars, hurt "
                "curves, move-additive values, special dash/idle conditions and state "
                "performs through walkSpLoopCount; supported enemy values close their "
                "20-member wrapper including blow-off, hurt and turn-start data. "
                "Unsupported subtype members, montage union variants, "
                "curves, and booleans remain unassigned."
            ),
    })
    return base
