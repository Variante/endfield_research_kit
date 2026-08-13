"""Focused MemoryPack decoder implementation extracted from the retired Data-page builder."""

from __future__ import annotations

import hashlib
import math
import re
import struct
from collections import Counter
from pathlib import Path
from typing import Any

from .core import (
    MEMORYPACK_NULL_COUNT,
    MEMORYPACK_SCHEMA_SOURCE_NOTE,
    MEMORYPACK_UNION_WIDE_TAG,
    STRING_SAMPLE_MAX_CHARS,
    format_offset,
    read_memorypack_utf8_string,
    scan_length_prefixed_utf8_string_hits,
    unique_strings,
)
from .schemas import BUFF_MEMBER_COUNT, MEMORYPACK_FIELD_SCHEMAS


BUFF_MEMORYPACK_FIELD_TYPES = {
    "abilityEventAction": "List",
    "addingCooldown": "Beyond.Blackboard.BlackboardDouble",
    "applyTags": "Beyond.Gameplay.Core.GameplayTagList",
    "attributeModifier": "Beyond.Gameplay.AttributeModifierData.AttributeModifier",
    "blackboard": "Dictionary",
    "buffEventAction": "List",
    "damageModifier": "List",
    "dispelConfig": "Beyond.Gameplay.Core.DispelConfig",
    "duration": "Beyond.Blackboard.BlackboardDouble",
    "finishOnRepatriate": "System.Boolean",
    "globalModifier": "List",
    "hasAddingCooldown": "System.Boolean",
    "hasIcon": "System.Boolean",
    "healModifier": "List",
    "iconConfig": "Beyond.Gameplay.Core.BuffIconConfig.BuffIconStyle",
    "id": "System.String",
    "igniteEventAction": "List",
    "ignoreCooldownWhenAdding": "System.Boolean",
    "ignoreTagImmune": "System.Boolean",
    "lifeType": "Beyond.Gameplay.Core.Buff.LifeType",
    "maxTriggerCnt": "Beyond.Blackboard.BlackboardInt",
    "onlyUseSelfTimeDilation": "System.Boolean",
    "poiseModifier": "List",
    "shieldConfigs": "List",
    "stackingSettings": "Beyond.Gameplay.Core.BuffStackingSettings.IdentifierType",
    "tagsAfterTriggerExtendBuffAction": "Beyond.Gameplay.Core.GameplayTagList",
    "timelineActions": "List",
    "triggerInterval": "Beyond.Blackboard.BlackboardDouble",
    "useTimeDilationDt": "System.Boolean",
    "waitFirstTriggerInterval": "System.Boolean",
}


BUFF_VALUE_FIELD_NAMES = {
    "addingCooldown",
    "duration",
    "finishOnRepatriate",
    "hasAddingCooldown",
    "hasIcon",
    "id",
    "ignoreCooldownWhenAdding",
    "ignoreTagImmune",
    "lifeType",
    "maxTriggerCnt",
    "onlyUseSelfTimeDilation",
    "triggerInterval",
    "useTimeDilationDt",
    "waitFirstTriggerInterval",
}


BUFF_SCHEMA_SAMPLE_FIELDS = [
    "id",
    "duration",
    "lifeType",
    "triggerInterval",
    "maxTriggerCnt",
    "applyTags",
    "attributeModifier",
    "buffEventAction",
    "blackboard",
    "timelineActions",
]


SKILL_UI_RANGE_HINT_MEMBER_COUNT = 3


SKILL_HINT_SHAPE_MEMBER_COUNT = 21


SKILL_HINT_SHAPE_NAMES = {
    0: "Point",
    1: "Rectangle",
    2: "Circle",
    3: "Sector",
    4: "Arrow",
    5: "VirtualArrow",
}


def read_u32_at(data: bytes, offset: int) -> int | None:
    if offset < 0 or offset + 4 > len(data):
        return None
    return struct.unpack_from("<I", data, offset)[0]


def length_prefixed_utf8_string_marker_info(
    data: bytes,
    value: str,
    *,
    max_offsets: int = 8,
) -> tuple[int, list[int]]:
    if not value:
        return 0, []
    raw = value.encode("utf-8")
    if not raw:
        return 0, []
    marker = struct.pack("<I", len(raw)) + raw
    count = 0
    offsets: list[int] = []
    start = 0
    while True:
        pos = data.find(marker, start)
        if pos < 0:
            break
        count += 1
        if len(offsets) < max_offsets:
            offsets.append(pos)
        start = pos + 1
    return count, offsets


def format_offset_list(offsets: list[int], total_count: int | None = None) -> str:
    if not offsets:
        return ""
    values = [format_offset(offset) for offset in offsets]
    if total_count is not None and total_count > len(offsets):
        values.append("...")
    return ",".join(values)


def compact_memorypack_type_name(type_name: str) -> str:
    text = str(type_name or "").replace("+", ".").replace("&", "").strip()
    if text.startswith("System."):
        return text.rsplit(".", 1)[-1]
    if text.startswith("UnityEngine."):
        return text.rsplit(".", 1)[-1]
    if text in {"List", "Dictionary"}:
        return text
    if "." in text:
        return text.rsplit(".", 1)[-1]
    return text or "unknown"


def memorypack_schema_type_sample_parts(
    field_types: dict[str, str],
    sample_fields: list[str],
) -> list[str]:
    parts: list[str] = []
    for field_name in sample_fields:
        type_name = field_types.get(field_name, "unknown")
        parts.append(f"{field_name}:{compact_memorypack_type_name(type_name)}")
    return parts


def memorypack_schema_field_groups(
    schema: list[str],
    value_field_names: set[str],
) -> tuple[list[str], list[str]]:
    value_fields = [field for field in schema if field in value_field_names]
    complex_fields = [field for field in schema if field not in value_field_names]
    return value_fields, complex_fields


def buff_schema_type_sample_parts() -> list[str]:
    return memorypack_schema_type_sample_parts(
        BUFF_MEMORYPACK_FIELD_TYPES,
        BUFF_SCHEMA_SAMPLE_FIELDS,
    )


def buff_schema_field_groups(schema: list[str]) -> tuple[list[str], list[str]]:
    return memorypack_schema_field_groups(schema, BUFF_VALUE_FIELD_NAMES)


def is_buff_param_string(value: str) -> bool:
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]{1,48}$", value):
        return False
    if value.startswith(("buff_", "icon_", "au_", "P_")):
        return False
    return "/" not in value


def read_buff_u32_field(data: bytes, offset: int, field_name: str) -> tuple[int, int]:
    if offset + 4 > len(data):
        raise ValueError(f"{field_name}:truncated-u32")
    return struct.unpack_from("<I", data, offset)[0], offset + 4


def read_buff_bool_field(data: bytes, offset: int, field_name: str) -> tuple[bool, int]:
    if offset >= len(data):
        raise ValueError(f"{field_name}:truncated-bool")
    raw = data[offset]
    if raw not in (0, 1):
        raise ValueError(f"{field_name}:invalid-bool={raw}")
    return bool(raw), offset + 1


def read_buff_blackboard_int_field(
    data: bytes,
    offset: int,
    field_name: str,
) -> tuple[dict[str, Any], int]:
    start = offset
    if offset >= len(data):
        raise ValueError(f"{field_name}:truncated-member-count")
    member_count = data[offset]
    offset += 1
    if member_count != 3:
        raise ValueError(f"{field_name}:member-count={member_count}")
    key, offset, error = read_memorypack_utf8_string(data, offset, max_length=256)
    if error:
        raise ValueError(f"{field_name}.blackboardKey:{error}")
    use_blackboard_key, offset = read_buff_bool_field(data, offset, f"{field_name}.useBlackboardKey")
    if offset + 4 > len(data):
        raise ValueError(f"{field_name}.value:truncated-i32")
    value = struct.unpack_from("<i", data, offset)[0]
    offset += 4
    return {
        "memberCount": member_count,
        "offset": format_offset(start),
        "blackboardKey": key or "",
        "useBlackboardKey": use_blackboard_key,
        "value": value,
    }, offset


def read_buff_blackboard_float_field(
    data: bytes,
    offset: int,
    field_name: str,
) -> tuple[dict[str, Any], int]:
    start = offset
    if offset >= len(data):
        raise ValueError(f"{field_name}:truncated-member-count")
    member_count = data[offset]
    offset += 1
    if member_count != 3:
        raise ValueError(f"{field_name}:member-count={member_count}")
    key, offset, error = read_memorypack_utf8_string(data, offset, max_length=256)
    if error:
        raise ValueError(f"{field_name}.blackboardKey:{error}")
    use_blackboard_key, offset = read_buff_bool_field(data, offset, f"{field_name}.useBlackboardKey")
    if offset + 4 > len(data):
        raise ValueError(f"{field_name}.value:truncated-f32")
    value = struct.unpack_from("<f", data, offset)[0]
    offset += 4
    return {
        "memberCount": member_count,
        "offset": format_offset(start),
        "blackboardKey": key or "",
        "useBlackboardKey": use_blackboard_key,
        "serializedValueType": "System.Single",
        "value": round(value, 6),
    }, offset


def read_buff_gameplay_tag_field(
    data: bytes,
    offset: int,
    field_name: str,
) -> tuple[dict[str, Any], int]:
    start = offset
    if offset >= len(data):
        raise ValueError(f"{field_name}:truncated-member-count")
    member_count = data[offset]
    offset += 1
    if member_count not in (0, 2):
        raise ValueError(f"{field_name}:member-count={member_count}")
    tag_id, offset = read_buff_u32_field(data, offset, f"{field_name}.tagId")
    tag_name, offset, error = read_memorypack_utf8_string(data, offset, max_length=256)
    if error:
        raise ValueError(f"{field_name}.tagName:{error}")
    return {
        "memberCount": member_count,
        "offset": format_offset(start),
        "tagId": tag_id,
        "tagName": tag_name or "",
    }, offset


def read_buff_trigger_interval_bool_tail_exact(
    data: bytes,
    offset: int,
) -> tuple[dict[str, Any], bool, bool, int]:
    trigger_interval, offset = read_buff_blackboard_float_field(
        data,
        offset,
        "triggerInterval",
    )
    use_time_dilation_dt, offset = read_buff_bool_field(
        data,
        offset,
        "useTimeDilationDt",
    )
    wait_first_trigger_interval, offset = read_buff_bool_field(
        data,
        offset,
        "waitFirstTriggerInterval",
    )
    if offset != len(data):
        raise ValueError(f"tail-not-exact={format_offset(offset)}")
    return trigger_interval, use_time_dilation_dt, wait_first_trigger_interval, offset


def read_buff_member1_empty_tag_field(
    data: bytes,
    offset: int,
    field_name: str,
) -> tuple[dict[str, Any], int]:
    start = offset
    end = offset + 9
    if end > len(data):
        raise ValueError(f"{field_name}:truncated-member1-empty-payload")
    member_count = data[offset]
    if member_count != 1:
        raise ValueError(f"{field_name}:member-count={member_count}")
    if data[offset + 1:end] != b"\x00" * 8:
        raise ValueError(f"{field_name}:member1-nonzero-empty-payload")
    return {
        "memberCount": member_count,
        "offset": format_offset(start),
        "branch": "member1-empty-payload",
        "branchNote": "single observed member-count-1 tag payload carries two zero u32 values before triggerInterval",
        "tagId": 0,
        "tagName": "",
    }, end


BUFF_ABILITY_ACTION_TAG_SOURCE_NOTE = (
    "AbilityActionData union tags recovered from MemoryPack.Beyond formatter cctors with "
    "GameAssembly CodeRegistration 0x18C439740; the current table is contiguous 0x0000..0x0181. "
    "This compact map includes tags observed as first actions in current BuffData timelineActions."
)


BUFF_ABILITY_ACTION_TAG_NAMES = {
    0x0002: "Core_AbilityActions_FinishBuffAction_Data",
    0x0008: "Core_AddDynamicCcsAction_AddDynamicCcsActionData",
    0x000b: "Core_AddTagAction_Data",
    0x0015: "Core_AuraAction_Data",
    0x0019: "Core_BlowOffCharacterAction_Data",
    0x0020: "Core_CameraImpulseAction_CameraImpulseActionData",
    0x002a: "Core_ChannelingAction_Data",
    0x002f: "Core_CharHurtAnimAction_Data",
    0x0036: "Core_CheckBuffStackNumAdvanced_Data",
    0x0047: "Core_CompareFloat_Data",
    0x004f: "Core_Conditions_CheckBuffStackNum_Data",
    0x007c: "Core_ContinuousFindTargetAction_Data",
    0x007e: "Core_ConvertToTargetContext_Data",
    0x0082: "Core_CreateBuffAction_Data",
    0x0089: "Core_CustomRootMotionAction_Data",
    0x008a: "Core_DamageAction_DamageActionData",
    0x008b: "Core_DebugPrintAction_Data",
    0x0091: "Core_EffectAction_EffectActionData",
    0x009f: "Core_FindTargetAction_FindTargetActionData",
    0x00a1: "Core_FinishBuffAdvanced_Data",
    0x00a3: "Core_FinishOwnerAction_Data",
    0x00ac: "Core_GetAITransDataAction_Data",
    0x00b2: "Core_HitStopAction_Data",
    0x00b4: "Core_IfElseAction_IfElseActionData",
    0x00bf: "Core_InterruptAction_Data",
    0x00c8: "Core_LaunchProjectile_Data",
    0x00ca: "Core_LockCameraAimAction_LockCameraAimActionData",
    0x00d1: "Core_ModifyDynamicBlackboard_Data",
    0x00db: "Core_MoveToAction_Data",
    0x00e9: "Core_OverrideCameraFollowAction_OverrideCameraFollowActionData",
    0x00ef: "Core_PatrolTeleport_Data",
    0x00f8: "Core_PlayAnimationAction_PlayAnimationActionData",
    0x010d: "Core_PlaySoundAction_PlaySoundActionData",
    0x00fe: "Core_PullAction_Data",
    0x0108: "Core_RecoverFromPoiseBreak_Data",
    0x010a: "Core_RecoverPoiseAction_Data",
    0x011e: "Core_SelfRotateAction_Data",
    0x0134: "Core_SendBattleSignalToLevel_Data",
    0x0133: "Core_ShowComboRingQte_Data",
    0x0135: "Core_ShowHideActorAction_ShowHideActorData",
    0x013d: "Core_SpawnAbilityEntity_Data",
    0x013e: "Core_SpawnEnemyAction_Data",
    0x0140: "Core_SpellInfliction_Data",
    0x014d: "Core_TeleportAction_Data",
    0x0152: "Core_TickIntervalAction_Data",
    0x0154: "Core_TimeDilationAction_Data",
}


BUFF_ABILITY_ACTION_TAG_MEMBER_COUNTS = {
    0x0002: 12,
    0x0008: 49,
    0x000b: 8,
    0x0015: 23,
    0x0019: 15,
    0x0020: 12,
    0x002a: 10,
    0x002f: 15,
    0x0036: 10,
    0x0047: 7,
    0x004f: 8,
    0x007c: 19,
    0x007e: 12,
    0x0082: 17,
    0x0089: 23,
    0x008a: 11,
    0x008b: 8,
    0x0091: 15,
    0x009f: 18,
    0x00a1: 13,
    0x00a3: 6,
    0x00ac: 6,
    0x00b2: 12,
    0x00b4: 8,
    0x00bf: 8,
    0x00c8: 34,
    0x00ca: 54,
    0x00d1: 10,
    0x00db: 42,
    0x00e9: 12,
    0x00ef: 6,
    0x00f8: 12,
    0x010d: 22,
    0x00fe: 17,
    0x0108: 5,
    0x010a: 11,
    0x011e: 18,
    0x0134: 6,
    0x0133: 8,
    0x0135: 10,
    0x013d: 37,
    0x013e: 15,
    0x0140: 8,
    0x014d: 13,
    0x0152: 9,
    0x0154: 16,
}


BUFF_OPAQUE_TIMELINE_ACTION_BODY_MAX_BYTES = 256 * 1024


def read_buff_timeline_force_sync_anim_data(
    data: bytes,
    offset: int,
    limit: int,
    field_name: str,
) -> tuple[dict[str, Any], int]:
    start = offset
    if offset >= limit:
        raise ValueError(f"{field_name}:truncated-member-count")
    member_count = data[offset]
    offset += 1
    if member_count != 4:
        raise ValueError(f"{field_name}:member-count={member_count}")
    force_sync, offset = read_buff_bool_field(data, offset, f"{field_name}.forceSync")
    montage_name, offset, error = read_memorypack_utf8_string(data, offset, max_length=512)
    if error:
        raise ValueError(f"{field_name}.montageName:{error}")
    if offset + 8 > limit:
        raise ValueError(f"{field_name}:truncated-tail")
    playback_speed = struct.unpack_from("<f", data, offset)[0]
    offset += 4
    if not math.isfinite(playback_speed):
        raise ValueError(f"{field_name}.playbackSpeed:non-finite")
    target_frame = struct.unpack_from("<i", data, offset)[0]
    offset += 4
    if abs(target_frame) > 1_000_000:
        raise ValueError(f"{field_name}.targetFrame:implausible={target_frame}")
    return {
        "memberCount": member_count,
        "offset": format_offset(start),
        "bytes": offset - start,
        "forceSync": force_sync,
        "montageName": montage_name or "",
        "playbackSpeed": round(playback_speed, 6),
        "targetFrame": target_frame,
    }, offset


def read_buff_timeline_first_union_tag(
    data: bytes,
    offset: int,
    limit: int,
) -> tuple[int | None, int, str]:
    if offset >= limit:
        return None, 0, ""
    if data[offset] == MEMORYPACK_UNION_WIDE_TAG:
        if offset + 3 > limit:
            return None, 0, ""
        return struct.unpack_from("<H", data, offset + 1)[0], 3, data[offset:offset + 3].hex(" ")
    return data[offset], 1, data[offset:offset + 1].hex(" ")


BUFF_CONVERT_TO_TARGET_CONTEXT_ACTION_TAG = 0x007e


BUFF_CREATE_BUFF_ACTION_TAG = 0x0082


BUFF_MODIFY_DYNAMIC_BLACKBOARD_ACTION_TAG = 0x00d1


BUFF_DEBUG_PRINT_ACTION_TAG = 0x008b


BUFF_CAMERA_IMPULSE_ACTION_TAG = 0x0020


BUFF_EFFECT_ACTION_TAG = 0x0091


BUFF_FIND_TARGET_ACTION_TAG = 0x009f


BUFF_SEND_BATTLE_SIGNAL_TO_LEVEL_TAG = 0x0134


BUFF_PLAY_SOUND_ACTION_TAG = 0x010d


BUFF_PATROL_TELEPORT_ACTION_TAG = 0x00ef


BUFF_PLAY_ANIMATION_ACTION_TAG = 0x00f8


BUFF_COMPARE_FLOAT_ACTION_TAG = 0x0047


BUFF_GET_AI_TRANS_DATA_ACTION_TAG = 0x00ac


BUFF_IF_ELSE_ACTION_TAG = 0x00b4


BUFF_INTERRUPT_ACTION_TAG = 0x00bf


BUFF_SPELL_INFLICTION_ACTION_TAG = 0x0140


BUFF_DAMAGE_ACTION_TAG = 0x008a


BUFF_DAMAGE_UNIT_MEMBER_COUNT = 32


BUFF_DAMAGE_MAX_UNITS = 16


BUFF_DAMAGE_UNIT_MIN_OPAQUE_BYTES = 64


BUFF_DAMAGE_HIT_ENV_MAX_BYTES = 256


BUFF_DAMAGE_HIT_ENV_FIXED_PREFIX = bytes.fromhex("00 00 00 00 00 00 00 00 00 01 02 03 00")


BUFF_CAMERA_IMPULSE_OPAQUE_NESTED_MAX_BYTES = 16 * 1024


BUFF_CAMERA_IMPULSE_DEFINITION_MEMBER_COUNT = 18


BUFF_CAMERA_IMPULSE_CURVE_LENGTH_REL_OFFSET = 0x40


BUFF_CAMERA_IMPULSE_TARGET_BASE_REL_OFFSET = 0xBB


BUFF_CAMERA_IMPULSE_BOOL_TAIL_BYTES = 2


BUFF_FIND_TARGET_OPAQUE_BODY_MAX_BYTES = 16 * 1024


BUFF_TARGET_SETTINGS_ENVELOPE_TAIL_U32_CANDIDATES = (0, 1, 2, 4)


BUFF_ABILITY_ACTION_MAX_NESTED_DEPTH = 6


BUFF_SEQUENCE_ACTION_DATA_MEMBER_COUNT = 3


BUFF_PLAY_SOUND_TIME_DILATION_TAIL_BYTES = 26


BUFF_TARGET_SETTINGS_ENVELOPE_BASE_BYTES = 67


BUFF_TARGET_SETTINGS_STRING_SLOT_OFFSET = 59


BUFF_TARGET_SETTINGS_STRING_SLOT_MAX_BYTES = 128


BUFF_EFFECT_ACTION_CFG_MIN_BYTES = 256


BUFF_CREATE_BUFF_ICON_DURATION_SOURCE_BYTES = 9


BUFF_CREATE_BUFF_INPUT_TAIL_BYTES = 5


BUFF_CREATE_BUFF_MAX_BUFF_IDS = 16


BUFF_MODIFY_DYNAMIC_BLACKBOARD_OPERATION_NAMES = {
    0: "Assign",
    1: "Add",
    2: "Multiply",
    3: "Divide",
}


def read_buff_i32_field(data: bytes, offset: int, field_name: str) -> tuple[int, int]:
    if offset + 4 > len(data):
        raise ValueError(f"{field_name}:truncated-i32")
    return struct.unpack_from("<i", data, offset)[0], offset + 4


def read_buff_f32_field(data: bytes, offset: int, field_name: str) -> tuple[float, int]:
    if offset + 4 > len(data):
        raise ValueError(f"{field_name}:truncated-f32")
    value = struct.unpack_from("<f", data, offset)[0]
    if not math.isfinite(value):
        raise ValueError(f"{field_name}:non-finite")
    return value, offset + 4


def read_buff_memorypack_utf8_string_strict(
    data: bytes,
    offset: int,
    field_name: str,
    *,
    max_length: int = 512,
) -> tuple[str | None, int]:
    if offset + 4 > len(data):
        raise ValueError(f"{field_name}:truncated-length")
    length = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    if length == MEMORYPACK_NULL_COUNT:
        return None, offset
    if length > max_length or offset + length > len(data):
        raise ValueError(f"{field_name}:invalid-length={length}")
    raw = data[offset:offset + length]
    try:
        value = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{field_name}:invalid-utf8") from exc
    if any(ord(ch) < 32 for ch in value):
        raise ValueError(f"{field_name}:control-char")
    return value, offset + length


def read_buff_memorypack_utf8_string_strict_bounded(
    data: bytes,
    offset: int,
    limit: int,
    field_name: str,
    *,
    max_length: int = 512,
) -> tuple[str | None, int]:
    if offset + 4 > limit:
        raise ValueError(f"{field_name}:truncated-length")
    length = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    if length == MEMORYPACK_NULL_COUNT:
        return None, offset
    if length > max_length or offset + length > limit:
        raise ValueError(f"{field_name}:invalid-length={length}")
    raw = data[offset:offset + length]
    try:
        value = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{field_name}:invalid-utf8") from exc
    if any(ord(ch) < 32 for ch in value):
        raise ValueError(f"{field_name}:control-char")
    return value, offset + length


def read_buff_blackboard_float_raw_field_exact(
    data: bytes,
    offset: int,
    field_name: str,
) -> tuple[dict[str, Any], int]:
    start = offset
    if offset >= len(data):
        raise ValueError(f"{field_name}:truncated-member-count")
    member_count = data[offset]
    offset += 1
    if member_count != 3:
        raise ValueError(f"{field_name}:member-count={member_count}")
    key, offset = read_buff_memorypack_utf8_string_strict(
        data,
        offset,
        f"{field_name}.blackboardKey",
        max_length=256,
    )
    use_blackboard_key, offset = read_buff_bool_field(data, offset, f"{field_name}.useBlackboardKey")
    if offset + 4 > len(data):
        raise ValueError(f"{field_name}.value:truncated-f32")
    raw_u32 = struct.unpack_from("<I", data, offset)[0]
    value = struct.unpack_from("<f", data, offset)[0]
    offset += 4
    if not math.isfinite(value):
        raise ValueError(f"{field_name}.value:non-finite")
    return {
        "memberCount": member_count,
        "offset": format_offset(start),
        "blackboardKey": key or "",
        "useBlackboardKey": use_blackboard_key,
        "serializedValueType": "System.Single",
        "rawValueU32": f"0x{raw_u32:08x}",
        "value": round(value, 6),
    }, offset


def read_buff_blackboard_float_raw_field_bounded(
    data: bytes,
    offset: int,
    limit: int,
    field_name: str,
) -> tuple[dict[str, Any], int]:
    start = offset
    if offset >= limit:
        raise ValueError(f"{field_name}:truncated-member-count")
    member_count = data[offset]
    offset += 1
    if member_count != 3:
        raise ValueError(f"{field_name}:member-count={member_count}")
    key, offset = read_buff_memorypack_utf8_string_strict_bounded(
        data,
        offset,
        limit,
        f"{field_name}.blackboardKey",
        max_length=256,
    )
    use_blackboard_key, offset = read_buff_bool_field_bounded(
        data,
        offset,
        limit,
        f"{field_name}.useBlackboardKey",
    )
    if offset + 4 > limit:
        raise ValueError(f"{field_name}.value:truncated-f32")
    raw_u32 = struct.unpack_from("<I", data, offset)[0]
    value = struct.unpack_from("<f", data, offset)[0]
    offset += 4
    if not math.isfinite(value):
        raise ValueError(f"{field_name}.value:non-finite")
    return {
        "memberCount": member_count,
        "offset": format_offset(start),
        "blackboardKey": key or "",
        "useBlackboardKey": use_blackboard_key,
        "serializedValueType": "System.Single",
        "rawValueU32": f"0x{raw_u32:08x}",
        "value": round(value, 6),
    }, offset


def read_buff_blackboard_vector3_field_exact(
    data: bytes,
    offset: int,
    field_name: str,
) -> tuple[dict[str, Any], int]:
    start = offset
    if offset >= len(data):
        raise ValueError(f"{field_name}:truncated-member-count")
    member_count = data[offset]
    offset += 1
    if member_count != 3:
        raise ValueError(f"{field_name}:member-count={member_count}")
    x, offset = read_buff_blackboard_float_raw_field_exact(data, offset, f"{field_name}.x")
    y, offset = read_buff_blackboard_float_raw_field_exact(data, offset, f"{field_name}.y")
    z, offset = read_buff_blackboard_float_raw_field_exact(data, offset, f"{field_name}.z")
    return {
        "memberCount": member_count,
        "offset": format_offset(start),
        "bytes": offset - start,
        "x": x,
        "y": y,
        "z": z,
        "value": [x["value"], y["value"], z["value"]],
    }, offset


def read_buff_blackboard_string_field_exact(
    data: bytes,
    offset: int,
    field_name: str,
) -> tuple[dict[str, Any], int]:
    start = offset
    if offset >= len(data):
        raise ValueError(f"{field_name}:truncated-member-count")
    member_count = data[offset]
    offset += 1
    if member_count != 3:
        raise ValueError(f"{field_name}:member-count={member_count}")
    key, offset = read_buff_memorypack_utf8_string_strict(
        data,
        offset,
        f"{field_name}.blackboardKey",
        max_length=256,
    )
    use_blackboard_key, offset = read_buff_bool_field(data, offset, f"{field_name}.useBlackboardKey")
    value, offset = read_buff_memorypack_utf8_string_strict(
        data,
        offset,
        f"{field_name}.value",
        max_length=512,
    )
    return {
        "memberCount": member_count,
        "offset": format_offset(start),
        "blackboardKey": key or "",
        "useBlackboardKey": use_blackboard_key,
        "value": value or "",
    }, offset


def read_buff_ability_action_common_prefix_bounded(
    data: bytes,
    offset: int,
    limit: int,
    field_name: str,
) -> tuple[dict[str, Any], int]:
    start = offset
    if offset + 13 > limit:
        raise ValueError(f"{field_name}:truncated-prefix")
    is_enable, offset = read_buff_bool_field_bounded(data, offset, limit, f"{field_name}.isEnable")
    priority_level, offset = read_buff_i32_field_bounded(
        data,
        offset,
        limit,
        f"{field_name}.priorityLevel",
    )
    priority_offset, offset = read_buff_i32_field_bounded(
        data,
        offset,
        limit,
        f"{field_name}.priorityOffset",
    )
    server_action_index, offset = read_buff_i32_field_bounded(
        data,
        offset,
        limit,
        f"{field_name}.serverActionIndex",
    )
    for name, value in (
        ("priorityLevel", priority_level),
        ("priorityOffset", priority_offset),
        ("serverActionIndex", server_action_index),
    ):
        if abs(value) > 1_000_000:
            raise ValueError(f"{field_name}.{name}:implausible={value}")
    return {
        "offset": format_offset(start),
        "bytes": offset - start,
        "isEnable": is_enable,
        "priorityLevel": priority_level,
        "priorityOffset": priority_offset,
        "serverActionIndex": server_action_index,
    }, offset


def validate_buff_nonnegative_ms(value: int, field_name: str, *, max_value: int = 600_000) -> None:
    if value < 0 or value > max_value:
        raise ValueError(f"{field_name}:ms-out-of-range={value}")


def buff_target_settings_envelope_limit(
    data: bytes,
    offset: int,
    max_limit: int,
    field_name: str,
) -> int:
    base_end = offset + BUFF_TARGET_SETTINGS_ENVELOPE_BASE_BYTES
    string_length_offset = offset + BUFF_TARGET_SETTINGS_STRING_SLOT_OFFSET
    if base_end > max_limit or string_length_offset + 4 > max_limit:
        raise ValueError(f"{field_name}:truncated-envelope")
    string_length = struct.unpack_from("<I", data, string_length_offset)[0]
    if string_length > BUFF_TARGET_SETTINGS_STRING_SLOT_MAX_BYTES:
        raise ValueError(f"{field_name}:string-slot-length={string_length}")
    limit = base_end + string_length
    if limit > max_limit:
        raise ValueError(f"{field_name}:envelope-limit={format_offset(limit)} max={format_offset(max_limit)}")
    return limit


def read_buff_target_settings_partial(
    data: bytes,
    offset: int,
    limit: int,
    field_name: str,
    *,
    allowed_tail_u32s: tuple[int, ...] = BUFF_TARGET_SETTINGS_ENVELOPE_TAIL_U32_CANDIDATES,
) -> tuple[dict[str, Any], int]:
    if limit < offset:
        raise ValueError(f"{field_name}:invalid-bounds")
    expected_limit = buff_target_settings_envelope_limit(data, offset, limit, field_name)
    if expected_limit != limit:
        raise ValueError(
            f"{field_name}:unexpected-bytes={limit - offset} expected={expected_limit - offset}"
        )
    raw = data[offset:limit]
    byte_length = len(raw)
    stable_prefix = bytes.fromhex("0d 08 01 00 00 00 00 00 00 ff 00 00 00 00 ff 00")
    if not raw.startswith(stable_prefix):
        raise ValueError(f"{field_name}:unexpected-prefix={raw[:16].hex(' ')}")
    string_slot_offset = BUFF_TARGET_SETTINGS_STRING_SLOT_OFFSET
    string_length = struct.unpack_from("<I", raw, string_slot_offset)[0]
    string_start = string_slot_offset + 4
    string_end = string_start + string_length
    string_value = ""
    if string_length:
        try:
            string_value = raw[string_start:string_end].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"{field_name}:string-slot-invalid-utf8") from exc
        if any(ord(ch) < 32 for ch in string_value):
            raise ValueError(f"{field_name}:string-slot-control-char")
    string_hits = scan_length_prefixed_utf8_string_hits(
        raw,
        start=0,
        max_scan_bytes=byte_length,
        max_samples=4,
        max_length=128,
    )
    tail_u32 = struct.unpack_from("<I", raw, byte_length - 4)[0]
    if tail_u32 not in allowed_tail_u32s:
        raise ValueError(f"{field_name}:tail-u32={tail_u32}")
    return {
        "status": "partial",
        "semanticStatus": "partial-target-settings-envelope-opaque",
        "offset": format_offset(offset),
        "bytes": byte_length,
        "shape": "string-slot" if string_length else "no-string-slot",
        "memberCountCandidate": raw[0],
        "envelopeHeaderRaw": raw[:16].hex(" "),
        "stringSlotOffset": format_offset(offset + string_slot_offset),
        "stringSlotLength": string_length,
        "stringSlotValue": string_value,
        "tailU32Candidate": tail_u32,
        "allowedTailU32Candidates": list(allowed_tail_u32s),
        "tailRaw": raw[-16:].hex(" "),
        "stringHits": string_hits,
        "rawHex": raw.hex(" "),
    }, limit


def read_buff_target_settings_envelope_partial(
    data: bytes,
    offset: int,
    max_limit: int,
    field_name: str,
) -> tuple[dict[str, Any], int]:
    """Consume-style TargetSettings envelope read that derives its own end.

    The envelope byte length is data-derived (67 + string-slot length), so the
    read is deterministic inside any bound; callers that know the exact item
    end still get the identical acceptance because they verify end-of-item
    afterwards.
    """
    envelope_end = buff_target_settings_envelope_limit(data, offset, max_limit, field_name)
    return read_buff_target_settings_partial(data, offset, envelope_end, field_name)


def read_buff_effect_action_cfg_partial(
    data: bytes,
    offset: int,
    limit: int,
    field_name: str,
) -> tuple[dict[str, Any], int]:
    if limit < offset:
        raise ValueError(f"{field_name}:invalid-bounds")
    byte_length = limit - offset
    if byte_length < BUFF_EFFECT_ACTION_CFG_MIN_BYTES:
        raise ValueError(f"{field_name}:unexpected-bytes={byte_length}")
    member_count, _member_offset = read_buff_i32_field(data, offset, f"{field_name}.memberCountCandidate")
    if member_count not in (74, 76):
        raise ValueError(f"{field_name}.memberCountCandidate={member_count}")
    raw = data[offset:limit]
    string_hits = scan_length_prefixed_utf8_string_hits(
        raw,
        start=0,
        max_scan_bytes=byte_length,
        max_samples=8,
        max_length=256,
    )
    return {
        "status": "partial",
        "semanticStatus": "partial-effect-action-cfg-fields-opaque",
        "offset": format_offset(offset),
        "bytes": byte_length,
        "memberCountCandidate": member_count,
        "memberCountOffset": format_offset(offset),
        "schemaSource": (
            "EffectActionCfg MemoryPack formatter exposes many fields; current decoder preserves the "
            "bounded config blob and validates the next TargetSettings anchor instead of naming fields"
        ),
        "rawSha256": hashlib.sha256(raw).hexdigest(),
        "prefixHex": raw[:48].hex(" "),
        "tailHex": raw[-48:].hex(" "),
        "stringHits": string_hits,
    }, limit


def read_buff_create_buff_icon_duration_source_partial(
    data: bytes,
    offset: int,
    limit: int,
    field_name: str,
) -> tuple[dict[str, Any], int]:
    start = offset
    end = offset + BUFF_CREATE_BUFF_ICON_DURATION_SOURCE_BYTES
    if end > limit:
        raise ValueError(f"{field_name}:truncated")
    member_count = data[offset]
    if member_count != 2:
        raise ValueError(f"{field_name}:member-count={member_count}")
    word0 = struct.unpack_from("<I", data, offset + 1)[0]
    word1 = struct.unpack_from("<I", data, offset + 5)[0]
    raw = data[start:end]
    return {
        "status": "partial",
        "semanticStatus": "partial-buff-icon-duration-source-setting-opaque",
        "offset": format_offset(start),
        "bytes": len(raw),
        "memberCount": member_count,
        "rawU32": [word0, word1],
        "rawHex": raw.hex(" "),
    }, end


def read_buff_create_buff_input_partial(
    data: bytes,
    offset: int,
    limit: int,
    field_name: str,
) -> tuple[dict[str, Any], int]:
    start = offset
    if offset + 10 > limit:
        raise ValueError(f"{field_name}:truncated-prefix")
    member_count = data[offset]
    offset += 1
    if member_count != 5:
        raise ValueError(f"{field_name}:member-count={member_count}")
    flag_candidate, offset = read_buff_bool_field(data, offset, f"{field_name}.flagCandidate")
    reserved_u32, offset = read_buff_u32_field(data, offset, f"{field_name}.reservedU32")
    if reserved_u32 != 0:
        raise ValueError(f"{field_name}.reservedU32={reserved_u32}")
    buff_id, offset = read_buff_memorypack_utf8_string_strict_bounded(
        data,
        offset,
        limit,
        f"{field_name}.buffId",
        max_length=256,
    )
    if not buff_id or not buff_id.startswith("buff_"):
        raise ValueError(f"{field_name}.buffId:unexpected={buff_id}")
    tail_end = offset + BUFF_CREATE_BUFF_INPUT_TAIL_BYTES
    if tail_end > limit:
        raise ValueError(f"{field_name}:truncated-tail")
    tail = data[offset:tail_end]
    if tail != b"\x00" * BUFF_CREATE_BUFF_INPUT_TAIL_BYTES:
        raise ValueError(f"{field_name}:tail={tail.hex(' ')}")
    offset = tail_end
    return {
        "status": "partial",
        "semanticStatus": "partial-create-buff-input-fields-opaque",
        "offset": format_offset(start),
        "bytes": offset - start,
        "memberCount": member_count,
        "flagCandidate": flag_candidate,
        "reservedU32": reserved_u32,
        "buffId": buff_id,
        "tailRaw": tail.hex(" "),
    }, offset


def read_buff_create_buff_list_partial(
    data: bytes,
    offset: int,
    limit: int,
    field_name: str,
) -> tuple[dict[str, Any], int]:
    start = offset
    count, offset = read_buff_u32_field(data, offset, f"{field_name}.count")
    if count <= 0 or count > BUFF_CREATE_BUFF_MAX_BUFF_IDS:
        raise ValueError(f"{field_name}.count={count}")
    items: list[dict[str, Any]] = []
    for index in range(count):
        item, offset = read_buff_create_buff_input_partial(
            data,
            offset,
            limit,
            f"{field_name}[{index}]",
        )
        items.append(item)
    return {
        "status": "partial",
        "semanticStatus": "partial-create-buff-input-list-fields-opaque",
        "offset": format_offset(start),
        "bytes": offset - start,
        "count": count,
        "items": items,
    }, offset


def consume_buff_create_buff_action(
    data: bytes,
    item_start: int,
    limit: int,
    tag_width: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    tag, actual_tag_width, _raw = read_buff_timeline_first_union_tag(data, item_start, limit)
    if tag != BUFF_CREATE_BUFF_ACTION_TAG or actual_tag_width != tag_width:
        raise ValueError("createBuff:tag-mismatch")
    if tag_width != 1:
        raise ValueError(f"createBuff:tag-width={tag_width}")
    if member_count != 17:
        raise ValueError(f"createBuff:member-count={member_count}")
    offset = item_start + tag_width + 1
    prefix, offset = read_buff_ability_action_common_prefix_bounded(
        data,
        offset,
        limit,
        "createBuff.prefix",
    )
    as_child_buff, offset = read_buff_bool_field(data, offset, "createBuff.asChildBuff")
    auto_finish_by_action, offset = read_buff_bool_field(data, offset, "createBuff.autoFinishByAction")
    buff_icon_duration_source, offset = read_buff_create_buff_icon_duration_source_partial(
        data,
        offset,
        limit,
        "createBuff.buffIconDurationSource",
    )
    buffs, offset = read_buff_create_buff_list_partial(
        data,
        offset,
        limit,
        "createBuff.buffs",
    )
    buff_source_raw, offset = read_buff_u32_field(data, offset, "createBuff.buffSourceRaw")
    if buff_source_raw > 1_000_000:
        raise ValueError(f"createBuff.buffSourceRaw={buff_source_raw}")
    context_key, offset = read_buff_memorypack_utf8_string_strict_bounded(
        data,
        offset,
        limit,
        "createBuff.contextKey",
        max_length=256,
    )
    if offset + 10 > limit:
        raise ValueError("createBuff.count:truncated")
    count_candidate, offset = read_buff_blackboard_float_raw_field_exact(
        data,
        offset,
        "createBuff.count",
    )
    inherit_skill_id_count, offset = read_buff_u32_field(
        data,
        offset,
        "createBuff.inheritSkillIdList.count",
    )
    if inherit_skill_id_count != 0:
        raise ValueError(f"createBuff.inheritSkillIdList.count={inherit_skill_id_count}")
    inherit_source_skill_cast_id, offset = read_buff_bool_field(
        data,
        offset,
        "createBuff.inheritSourceSkillCastId",
    )
    inherit_source_skill_cast_info, offset = read_buff_bool_field(
        data,
        offset,
        "createBuff.inheritSourceSkillCastInfo",
    )
    is_extra, offset = read_buff_bool_field(data, offset, "createBuff.isExtra")
    override_buff_icon_duration, offset = read_buff_bool_field(
        data,
        offset,
        "createBuff.overrideBuffIconDuration",
    )
    target_settings, offset = read_buff_target_settings_envelope_partial(
        data,
        offset,
        limit,
        "createBuff.targetSettings",
    )
    return {
        "type": BUFF_ABILITY_ACTION_TAG_NAMES[BUFF_CREATE_BUFF_ACTION_TAG],
        "decodeStatus": "partial",
        "semanticStatus": "partial-create-buff-input-tail-and-target-settings-opaque",
        "schemaSource": (
            "MemoryPack setter order plus current byte evidence: AbilityActionData prefix, asChildBuff, "
            "autoFinishByAction, buffIconDurationSource, buffs, buffSource, contextKey, count, "
            "empty inheritSkillIdList, four boolean tail flags, targetSettings; buff input internals, "
            "BlackboardDouble/count semantics, and TargetSettings internals remain partial"
        ),
        "byteLength": offset - item_start,
        "prefix": prefix,
        "asChildBuff": as_child_buff,
        "autoFinishByAction": auto_finish_by_action,
        "buffIconDurationSourcePartial": buff_icon_duration_source,
        "buffsPartial": buffs,
        "buffSourceRaw": buff_source_raw,
        "contextKey": context_key or "",
        "countCandidate": count_candidate,
        "inheritSkillIdListCount": inherit_skill_id_count,
        "inheritSourceSkillCastId": inherit_source_skill_cast_id,
        "inheritSourceSkillCastInfo": inherit_source_skill_cast_info,
        "isExtra": is_extra,
        "overrideBuffIconDuration": override_buff_icon_duration,
        "targetSettingsEnvelopePartial": target_settings,
    }, offset


def decode_buff_create_buff_action(
    data: bytes,
    item_start: int,
    item_end: int,
    tag_width: int,
    member_count: int,
) -> dict[str, Any]:
    decoded, end = consume_buff_create_buff_action(data, item_start, item_end, tag_width, member_count)
    if end != item_end:
        raise ValueError(f"createBuff:tail-at={format_offset(end)} end={format_offset(item_end)}")
    return decoded


def consume_buff_modify_dynamic_blackboard_action(
    data: bytes,
    item_start: int,
    limit: int,
    tag_width: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    tag, actual_tag_width, _raw = read_buff_timeline_first_union_tag(data, item_start, limit)
    if tag != BUFF_MODIFY_DYNAMIC_BLACKBOARD_ACTION_TAG or actual_tag_width != tag_width:
        raise ValueError("modifyDynamicBlackboard:tag-mismatch")
    if tag_width != 1:
        raise ValueError(f"modifyDynamicBlackboard:tag-width={tag_width}")
    if member_count != 10:
        raise ValueError(f"modifyDynamicBlackboard:member-count={member_count}")
    offset = item_start + tag_width + 1
    prefix, offset = read_buff_ability_action_common_prefix_bounded(
        data,
        offset,
        limit,
        "modifyDynamicBlackboard.prefix",
    )
    calculate_type, offset = read_buff_i32_field(
        data,
        offset,
        "modifyDynamicBlackboard.calculateType",
    )
    if abs(calculate_type) > 1_000:
        raise ValueError(f"modifyDynamicBlackboard.calculateType={calculate_type}")
    calculation_target, offset = read_buff_target_settings_envelope_partial(
        data,
        offset,
        limit,
        "modifyDynamicBlackboard.calculationTarget",
    )
    direct_value, offset = read_buff_bool_field(data, offset, "modifyDynamicBlackboard.directValue")
    key, offset = read_buff_memorypack_utf8_string_strict_bounded(
        data,
        offset,
        limit,
        "modifyDynamicBlackboard.key",
        max_length=256,
    )
    if not key:
        raise ValueError("modifyDynamicBlackboard.key:empty")
    operation, offset = read_buff_i32_field(data, offset, "modifyDynamicBlackboard.operation")
    if operation not in BUFF_MODIFY_DYNAMIC_BLACKBOARD_OPERATION_NAMES:
        raise ValueError(f"modifyDynamicBlackboard.operation={operation}")
    value, offset = read_buff_blackboard_float_raw_field_exact(
        data,
        offset,
        "modifyDynamicBlackboard.value",
    )
    return {
        "type": BUFF_ABILITY_ACTION_TAG_NAMES[BUFF_MODIFY_DYNAMIC_BLACKBOARD_ACTION_TAG],
        "decodeStatus": "partial",
        "semanticStatus": "partial-calculation-target-settings-envelope-opaque",
        "schemaSource": (
            "MemoryPack setter order: AbilityActionData prefix, calculateType, calculationTarget, "
            "directValue, key, operation, value; TargetSettings internals and calculateType enum remain partial"
        ),
        "byteLength": offset - item_start,
        "prefix": prefix,
        "calculateType": calculate_type,
        "calculationTargetEnvelopePartial": calculation_target,
        "directValue": direct_value,
        "key": key,
        "operation": operation,
        "operationName": BUFF_MODIFY_DYNAMIC_BLACKBOARD_OPERATION_NAMES[operation],
        "value": value,
    }, offset


def decode_buff_modify_dynamic_blackboard_action(
    data: bytes,
    item_start: int,
    item_end: int,
    tag_width: int,
    member_count: int,
) -> dict[str, Any]:
    decoded, end = consume_buff_modify_dynamic_blackboard_action(
        data,
        item_start,
        item_end,
        tag_width,
        member_count,
    )
    if end != item_end:
        raise ValueError(
            f"modifyDynamicBlackboard:tail-at={format_offset(end)} end={format_offset(item_end)}"
        )
    return decoded


def decode_buff_effect_action(
    data: bytes,
    item_start: int,
    item_end: int,
    tag_width: int,
    member_count: int,
) -> dict[str, Any] | None:
    """Single-item EffectAction decode, unified onto the consume-style parser.

    2026-07-02: the previous exactly-two-anchor variant and the consume
    variant were verified to produce byte-identical decoded output for every
    currently accepted single-item EffectAction, and to keep the same two
    opaque cfg-anchor variants opaque, so the two parsers were unified. The
    cfg member-count mismatch keeps the historical return-None (opaque)
    behavior instead of surfacing a typed-decoder failure.
    """
    try:
        decoded, end = consume_buff_effect_action(data, item_start, item_end, tag_width, member_count)
    except ValueError as exc:
        if str(exc).startswith("effectAction.effectActionCfg.memberCountCandidate="):
            return None
        raise
    if end != item_end:
        raise ValueError(f"effectAction:tail-at={format_offset(end)} end={format_offset(item_end)}")
    return decoded


def consume_buff_effect_action(
    data: bytes,
    item_start: int,
    limit: int,
    tag_width: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    """Chain-mode EffectAction consumption.

    The single-item decoder proves boundaries with an exactly-two-anchor scan
    inside a known item end. Inside a multi-item payload later items can also
    contain envelope anchors, so this variant anchors the first envelope after
    the bounded EffectActionCfg blob and then requires the second envelope to
    start exactly at the parse cursor. Any mismatch raises and the whole chain
    stays opaque.
    """
    tag, actual_tag_width, _raw = read_buff_timeline_first_union_tag(data, item_start, limit)
    if tag != BUFF_EFFECT_ACTION_TAG or actual_tag_width != tag_width:
        raise ValueError("effectAction:tag-mismatch")
    if tag_width != 1:
        raise ValueError(f"effectAction:tag-width={tag_width}")
    if member_count != 15:
        raise ValueError(f"effectAction:member-count={member_count}")
    offset = item_start + tag_width + 1
    prefix, offset = read_buff_ability_action_common_prefix_bounded(
        data,
        offset,
        limit,
        "effectAction.prefix",
    )
    big_effect_name, offset = read_buff_memorypack_utf8_string_strict_bounded(
        data,
        offset,
        limit,
        "effectAction.bigEffectName",
        max_length=512,
    )
    stable_prefix = bytes.fromhex("0d 08 01 00 00 00 00 00 00 ff 00 00 00 00 ff 00")
    effect_source_start = data.find(stable_prefix, offset, limit)
    if effect_source_start < 0:
        raise ValueError("effectAction.effectSource:no-envelope-anchor")
    effect_action_cfg, offset = read_buff_effect_action_cfg_partial(
        data,
        offset,
        effect_source_start,
        "effectAction.effectActionCfg",
    )
    effect_source, offset = read_buff_target_settings_envelope_partial(
        data,
        offset,
        limit,
        "effectAction.effectSource",
    )
    bool_fields: dict[str, bool] = {}
    for field_name in (
        "forceMainBody",
        "isCreateWithSourceModelActive",
        "isMainCharacterActive",
        "isShowBigEffect",
        "isTargetMainCharacterActive",
        "playOnHittableObjects",
    ):
        bool_fields[field_name], offset = read_buff_bool_field(data, offset, f"effectAction.{field_name}")
    save_effect_id_to_blackboard, offset = read_buff_memorypack_utf8_string_strict_bounded(
        data,
        offset,
        limit,
        "effectAction.saveEffectIdToBlackboard",
        max_length=256,
    )
    anchor_end = offset + len(stable_prefix)
    if anchor_end > limit or data[offset:anchor_end] != stable_prefix:
        raise ValueError(
            f"effectAction.targetSettings:envelope-anchor-not-at-cursor={format_offset(offset)}"
        )
    target_settings, offset = read_buff_target_settings_envelope_partial(
        data,
        offset,
        limit,
        "effectAction.targetSettings",
    )
    return {
        "type": BUFF_ABILITY_ACTION_TAG_NAMES[BUFF_EFFECT_ACTION_TAG],
        "decodeStatus": "partial",
        "semanticStatus": "partial-effect-action-cfg-and-target-settings-opaque",
        "schemaSource": (
            "MemoryPack setter order: AbilityActionData prefix, bigEffectName, effectActionCfg, "
            "effectSource, six boolean flags, saveEffectIdToBlackboard, targetSettings; "
            "EffectActionCfg and TargetSettings internals remain partial"
        ),
        "byteLength": offset - item_start,
        "prefix": prefix,
        "bigEffectName": big_effect_name or "",
        "effectActionCfgPartial": effect_action_cfg,
        "effectSourceEnvelopePartial": effect_source,
        **bool_fields,
        "saveEffectIdToBlackboard": save_effect_id_to_blackboard or "",
        "targetSettingsEnvelopePartial": target_settings,
    }, offset


def consume_buff_convert_to_target_context_action(
    data: bytes,
    item_start: int,
    limit: int,
    tag_width: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    tag, actual_tag_width, _raw = read_buff_timeline_first_union_tag(data, item_start, limit)
    if tag != BUFF_CONVERT_TO_TARGET_CONTEXT_ACTION_TAG or actual_tag_width != tag_width:
        raise ValueError("convertToTargetContext:tag-mismatch")
    if tag_width != 1:
        raise ValueError(f"convertToTargetContext:tag-width={tag_width}")
    if member_count != 12:
        raise ValueError(f"convertToTargetContext:member-count={member_count}")
    offset = item_start + tag_width + 1
    prefix, offset = read_buff_ability_action_common_prefix_bounded(
        data,
        offset,
        limit,
        "convertToTargetContext.prefix",
    )
    blackboard_vector3, offset = read_buff_blackboard_vector3_field_exact(
        data,
        offset,
        "convertToTargetContext.blackboardVector3",
    )
    convert_from, offset = read_buff_target_settings_envelope_partial(
        data,
        offset,
        limit,
        "convertToTargetContext.convertFrom",
    )
    exclude_target, offset = read_buff_i32_field(data, offset, "convertToTargetContext.excludeTarget")
    operation_type, offset = read_buff_i32_field(data, offset, "convertToTargetContext.operationType")
    target_group_key, offset = read_buff_memorypack_utf8_string_strict_bounded(
        data,
        offset,
        limit,
        "convertToTargetContext.targetGroupKey",
        max_length=256,
    )
    if not target_group_key:
        raise ValueError("convertToTargetContext.targetGroupKey:empty")
    translate_operation, offset = read_buff_i32_field(
        data,
        offset,
        "convertToTargetContext.translateOperation",
    )
    translation_deg, offset = read_buff_f32_field(data, offset, "convertToTargetContext.translationDeg")
    translation_ref, offset = read_buff_i32_field(data, offset, "convertToTargetContext.translationRef")
    for field_name, value in (
        ("convertToTargetContext.excludeTarget", exclude_target),
        ("convertToTargetContext.operationType", operation_type),
        ("convertToTargetContext.translateOperation", translate_operation),
        ("convertToTargetContext.translationRef", translation_ref),
    ):
        if abs(value) > 1_000_000:
            raise ValueError(f"{field_name}:implausible={value}")
    if translation_deg < -100_000 or translation_deg > 100_000:
        raise ValueError(f"convertToTargetContext.translationDeg:out-of-range={translation_deg}")
    return {
        "type": BUFF_ABILITY_ACTION_TAG_NAMES[BUFF_CONVERT_TO_TARGET_CONTEXT_ACTION_TAG],
        "decodeStatus": "partial",
        "semanticStatus": "partial-convert-from-target-settings-envelope-opaque",
        "schemaSource": (
            "MemoryPack setter order: AbilityActionData prefix, blackboardVector3, convertFrom "
            "TargetSettings, excludeTarget, operationType, targetGroupKey, translateOperation, "
            "translationDeg, translationRef; TargetSettings targeting semantics remain partial"
        ),
        "byteLength": offset - item_start,
        "prefix": prefix,
        "blackboardVector3": blackboard_vector3,
        "convertFromTargetSettingsEnvelopePartial": convert_from,
        "excludeTarget": exclude_target,
        "operationType": operation_type,
        "targetGroupKey": target_group_key,
        "translateOperation": translate_operation,
        "translationDeg": round(translation_deg, 6),
        "translationRef": translation_ref,
    }, offset


def decode_buff_convert_to_target_context_action(
    data: bytes,
    item_start: int,
    item_end: int,
    tag_width: int,
    member_count: int,
) -> dict[str, Any]:
    decoded, end = consume_buff_convert_to_target_context_action(
        data,
        item_start,
        item_end,
        tag_width,
        member_count,
    )
    if end != item_end:
        raise ValueError(
            f"convertToTargetContext:tail-at={format_offset(end)} end={format_offset(item_end)}"
        )
    return decoded


def consume_buff_debug_print_action(
    data: bytes,
    item_start: int,
    limit: int,
    tag_width: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    tag, actual_tag_width, _raw = read_buff_timeline_first_union_tag(data, item_start, limit)
    if tag != BUFF_DEBUG_PRINT_ACTION_TAG or actual_tag_width != tag_width:
        raise ValueError("debugPrint:tag-mismatch")
    if tag_width != 1:
        raise ValueError(f"debugPrint:tag-width={tag_width}")
    if member_count != 8:
        raise ValueError(f"debugPrint:member-count={member_count}")
    offset = item_start + tag_width + 1
    prefix, offset = read_buff_ability_action_common_prefix_bounded(
        data,
        offset,
        limit,
        "debugPrint.prefix",
    )
    bb_key, offset = read_buff_memorypack_utf8_string_strict_bounded(
        data,
        offset,
        limit,
        "debugPrint.bbKey",
        max_length=256,
    )
    identifier, offset = read_buff_memorypack_utf8_string_strict_bounded(
        data,
        offset,
        limit,
        "debugPrint.identifier",
        max_length=512,
    )
    if not identifier:
        raise ValueError("debugPrint.identifier:empty")
    log_type, offset = read_buff_i32_field(data, offset, "debugPrint.logType")
    log_type_names = {0: "TargetSetting", 1: "BlackboardItem"}
    if log_type not in log_type_names:
        raise ValueError(f"debugPrint.logType={log_type}")
    target_settings, offset = read_buff_target_settings_envelope_partial(
        data,
        offset,
        limit,
        "debugPrint.target",
    )
    return {
        "type": BUFF_ABILITY_ACTION_TAG_NAMES[BUFF_DEBUG_PRINT_ACTION_TAG],
        "decodeStatus": "partial",
        "semanticStatus": "partial-target-settings-envelope-opaque",
        "schemaSource": (
            "MemoryPack setter order: AbilityActionData prefix, bbKey, identifier, logType, target; "
            "TargetSettings envelope bytes are bounded but targeting semantics and tail values remain partial"
        ),
        "byteLength": offset - item_start,
        "prefix": prefix,
        "bbKey": bb_key or "",
        "identifier": identifier,
        "logType": log_type,
        "logTypeName": log_type_names[log_type],
        "targetSettingsEnvelopePartial": target_settings,
    }, offset


def decode_buff_debug_print_action(
    data: bytes,
    item_start: int,
    item_end: int,
    tag_width: int,
    member_count: int,
) -> dict[str, Any]:
    decoded, end = consume_buff_debug_print_action(data, item_start, item_end, tag_width, member_count)
    if end != item_end:
        raise ValueError(f"debugPrint:tail-at={format_offset(end)} end={format_offset(item_end)}")
    return decoded


def consume_buff_play_animation_action(
    data: bytes,
    item_start: int,
    limit: int,
    tag_width: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    tag, actual_tag_width, _raw = read_buff_timeline_first_union_tag(data, item_start, limit)
    if tag != BUFF_PLAY_ANIMATION_ACTION_TAG or actual_tag_width != tag_width:
        raise ValueError("playAnimation:tag-mismatch")
    if tag_width != 1:
        raise ValueError(f"playAnimation:tag-width={tag_width}")
    if member_count != 12:
        raise ValueError(f"playAnimation:member-count={member_count}")
    offset = item_start + tag_width + 1
    prefix, offset = read_buff_ability_action_common_prefix_bounded(
        data,
        offset,
        limit,
        "playAnimation.prefix",
    )
    anim_name, offset = read_buff_memorypack_utf8_string_strict(
        data,
        offset,
        "playAnimation.animName",
        max_length=256,
    )
    if not anim_name:
        raise ValueError("playAnimation.animName:empty")
    blend_duration, offset = read_buff_f32_field(data, offset, "playAnimation.blendDuration")
    blend_out, offset = read_buff_f32_field(data, offset, "playAnimation.blendOut")
    blend_out_next_state_hash, offset = read_buff_i32_field(
        data,
        offset,
        "playAnimation.blendOutNextStateHash",
    )
    duration, offset = read_buff_f32_field(data, offset, "playAnimation.duration")
    exit_to_idle, offset = read_buff_bool_field(data, offset, "playAnimation.exitToIdle")
    playback_speed, offset = read_buff_f32_field(data, offset, "playAnimation.playbackSpeed")
    start_time, offset = read_buff_f32_field(data, offset, "playAnimation.startTime")
    for field_name, value in (
        ("playAnimation.blendDuration", blend_duration),
        ("playAnimation.blendOut", blend_out),
        ("playAnimation.duration", duration),
        ("playAnimation.playbackSpeed", playback_speed),
        ("playAnimation.startTime", start_time),
    ):
        if value < -10_000 or value > 100_000:
            raise ValueError(f"{field_name}:out-of-range={value}")
    return {
        "type": BUFF_ABILITY_ACTION_TAG_NAMES[BUFF_PLAY_ANIMATION_ACTION_TAG],
        "decodeStatus": "exact",
        "schemaSource": (
            "MemoryPack setter order: AbilityActionData prefix, animName, blendDuration, blendOut, "
            "blendOutNextStateHash, duration, exitToIdle, playbackSpeed, startTime"
        ),
        "byteLength": offset - item_start,
        "prefix": prefix,
        "animName": anim_name,
        "blendDuration": round(blend_duration, 6),
        "blendOut": round(blend_out, 6),
        "blendOutNextStateHash": blend_out_next_state_hash,
        "duration": round(duration, 6),
        "exitToIdle": exit_to_idle,
        "playbackSpeed": round(playback_speed, 6),
        "startTime": round(start_time, 6),
    }, offset


def decode_buff_play_animation_action(
    data: bytes,
    item_start: int,
    item_end: int,
    tag_width: int,
    member_count: int,
) -> dict[str, Any]:
    decoded, end = consume_buff_play_animation_action(data, item_start, item_end, tag_width, member_count)
    if end != item_end:
        raise ValueError(f"playAnimation:tail-at={format_offset(end)} end={format_offset(item_end)}")
    return decoded


def consume_buff_patrol_teleport_action(
    data: bytes,
    item_start: int,
    limit: int,
    tag_width: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    tag, actual_tag_width, _raw = read_buff_timeline_first_union_tag(data, item_start, limit)
    if tag != BUFF_PATROL_TELEPORT_ACTION_TAG or actual_tag_width != tag_width:
        raise ValueError("patrolTeleport:tag-mismatch")
    if tag_width != 1:
        raise ValueError(f"patrolTeleport:tag-width={tag_width}")
    if member_count != 6:
        raise ValueError(f"patrolTeleport:member-count={member_count}")
    offset = item_start + tag_width + 1
    prefix, offset = read_buff_ability_action_common_prefix_bounded(
        data,
        offset,
        limit,
        "patrolTeleport.prefix",
    )
    save_to, offset = read_buff_memorypack_utf8_string_strict_bounded(
        data,
        offset,
        limit,
        "patrolTeleport.saveTo",
        max_length=128,
    )
    if not save_to:
        raise ValueError("patrolTeleport.saveTo:empty")
    teleport_dis, offset = read_buff_f32_field(data, offset, "patrolTeleport.teleportDis")
    if teleport_dis < 0 or teleport_dis > 100_000:
        raise ValueError(f"patrolTeleport.teleportDis:out-of-range={teleport_dis}")
    return {
        "type": BUFF_ABILITY_ACTION_TAG_NAMES[BUFF_PATROL_TELEPORT_ACTION_TAG],
        "decodeStatus": "exact",
        "schemaSource": (
            "Runtime fields are teleportDis and saveTo; current MemoryPack bytes consume exactly as "
            "AbilityActionData prefix, saveTo string, then teleportDis float"
        ),
        "byteLength": offset - item_start,
        "prefix": prefix,
        "saveTo": save_to,
        "teleportDis": round(teleport_dis, 6),
    }, offset


def decode_buff_patrol_teleport_action(
    data: bytes,
    item_start: int,
    item_end: int,
    tag_width: int,
    member_count: int,
) -> dict[str, Any]:
    decoded, end = consume_buff_patrol_teleport_action(data, item_start, item_end, tag_width, member_count)
    if end != item_end:
        raise ValueError(f"patrolTeleport:tail-at={format_offset(end)} end={format_offset(item_end)}")
    return decoded


def consume_buff_play_sound_action(
    data: bytes,
    item_start: int,
    limit: int,
    tag_width: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    tag, actual_tag_width, _raw = read_buff_timeline_first_union_tag(data, item_start, limit)
    if tag != BUFF_PLAY_SOUND_ACTION_TAG or actual_tag_width != tag_width:
        raise ValueError("playSound:tag-mismatch")
    if tag_width != 3:
        raise ValueError(f"playSound:tag-width={tag_width}")
    if member_count != 22:
        raise ValueError(f"playSound:member-count={member_count}")
    if limit - item_start <= BUFF_PLAY_SOUND_TIME_DILATION_TAIL_BYTES:
        raise ValueError("playSound:truncated-tail")

    offset = item_start + tag_width + 1
    prefix, offset = read_buff_ability_action_common_prefix_bounded(
        data,
        offset,
        limit,
        "playSound.prefix",
    )
    can_interrupt_time_ms, offset = read_buff_i32_field(data, offset, "playSound.canInterruptTimeMs")
    intrpt_fade_duration_ms, offset = read_buff_i32_field(data, offset, "playSound.intrptFadeDurationMs")
    jump_to_when_play_ms, offset = read_buff_i32_field(data, offset, "playSound.jumpToWhenPlayMs")
    for field_name, value in (
        ("playSound.canInterruptTimeMs", can_interrupt_time_ms),
        ("playSound.intrptFadeDurationMs", intrpt_fade_duration_ms),
        ("playSound.jumpToWhenPlayMs", jump_to_when_play_ms),
    ):
        validate_buff_nonnegative_ms(value, field_name)

    sound_event, offset = read_buff_memorypack_utf8_string_strict_bounded(
        data,
        offset,
        limit,
        "playSound.soundEvent",
        max_length=512,
    )
    if not sound_event or re.fullmatch(
        r"(?i)(?:au|eny|chr|bark|radio|play_au)_[a-z0-9_]+",
        sound_event,
    ) is None:
        raise ValueError(f"playSound.soundEvent:unexpected={sound_event or ''}")

    stop_fade_duration_ms, offset = read_buff_i32_field(data, offset, "playSound.stopFadeDurationMs")
    validate_buff_nonnegative_ms(stop_fade_duration_ms, "playSound.stopFadeDurationMs")
    stop_on_end, offset = read_buff_bool_field(data, offset, "playSound.stopOnEnd")
    use_temp_emitter, offset = read_buff_bool_field(data, offset, "playSound.useTempEmitter")
    follow_mount_point, offset = read_buff_bool_field(data, offset, "playSound.followMountPoint")
    mount_point, offset = read_buff_memorypack_utf8_string_strict_bounded(
        data,
        offset,
        limit,
        "playSound.mountPoint",
        max_length=256,
    )

    target_settings, offset = read_buff_target_settings_full_or_partial(
        data,
        offset,
        limit,
        "playSound.targetSettings",
    )

    time_dilation_fade_in_duration_ms, offset = read_buff_i32_field(
        data,
        offset,
        "playSound.timeDilationFadeInDurationMs",
    )
    validate_buff_nonnegative_ms(
        time_dilation_fade_in_duration_ms,
        "playSound.timeDilationFadeInDurationMs",
    )
    time_dilation_fade_out_duration_ms, offset = read_buff_i32_field(
        data,
        offset,
        "playSound.timeDilationFadeOutDurationMs",
    )
    validate_buff_nonnegative_ms(
        time_dilation_fade_out_duration_ms,
        "playSound.timeDilationFadeOutDurationMs",
    )
    time_dilation_pause_threshold, offset = read_buff_f32_field(
        data,
        offset,
        "playSound.timeDilationPauseThreshold",
    )
    time_dilation_seek_threshold, offset = read_buff_f32_field(
        data,
        offset,
        "playSound.timeDilationSeekThreshold",
    )
    for field_name, value in (
        ("playSound.timeDilationPauseThreshold", time_dilation_pause_threshold),
        ("playSound.timeDilationSeekThreshold", time_dilation_seek_threshold),
    ):
        if value < 0 or value > 10:
            raise ValueError(f"{field_name}:out-of-range={value}")
    use_time_dilation_pause_and_seek, offset = read_buff_bool_field(
        data,
        offset,
        "playSound.useTimeDilationPauseAndSeek",
    )
    use_weapon_mount_point, offset = read_buff_bool_field(
        data,
        offset,
        "playSound.useWeaponMountPoint",
    )
    weapon_index, offset = read_buff_i32_field(data, offset, "playSound.weaponIndex")
    if abs(weapon_index) > 1_000_000:
        raise ValueError(f"playSound.weaponIndex:implausible={weapon_index}")
    weapon_mount_point, offset = read_buff_memorypack_utf8_string_strict_bounded(
        data,
        offset,
        limit,
        "playSound.weaponMountPoint",
        max_length=256,
    )

    return {
        "type": BUFF_ABILITY_ACTION_TAG_NAMES[BUFF_PLAY_SOUND_ACTION_TAG],
        "decodeStatus": "partial",
        "semanticStatus": "partial-target-settings-envelope-opaque",
        "schemaSource": (
            "MemoryPack formatter setter order: AbilityActionData prefix, PlaySound primitive fields, "
            "targetSettings, and time-dilation tail; TargetSettings bytes are bounded but targeting semantics remain partial"
        ),
        "byteLength": offset - item_start,
        "prefix": prefix,
        "canInterruptTimeMs": can_interrupt_time_ms,
        "intrptFadeDurationMs": intrpt_fade_duration_ms,
        "jumpToWhenPlayMs": jump_to_when_play_ms,
        "soundEvent": sound_event,
        "stopFadeDurationMs": stop_fade_duration_ms,
        "stopOnEnd": stop_on_end,
        "useTempEmitter": use_temp_emitter,
        "followMountPoint": follow_mount_point,
        "mountPoint": mount_point or "",
        "targetSettingsEnvelopePartial": target_settings,
        "timeDilationFadeInDurationMs": time_dilation_fade_in_duration_ms,
        "timeDilationFadeOutDurationMs": time_dilation_fade_out_duration_ms,
        "timeDilationPauseThreshold": round(time_dilation_pause_threshold, 6),
        "timeDilationSeekThreshold": round(time_dilation_seek_threshold, 6),
        "useTimeDilationPauseAndSeek": use_time_dilation_pause_and_seek,
        "useWeaponMountPoint": use_weapon_mount_point,
        "weaponIndex": weapon_index,
        "weaponMountPoint": weapon_mount_point or "",
    }, offset


def decode_buff_play_sound_action(
    data: bytes,
    item_start: int,
    item_end: int,
    tag_width: int,
    member_count: int,
) -> dict[str, Any]:
    decoded, end = consume_buff_play_sound_action(data, item_start, item_end, tag_width, member_count)
    if end != item_end:
        raise ValueError(f"playSound:tail-at={format_offset(end)} end={format_offset(item_end)}")
    return decoded


def consume_buff_send_battle_signal_to_level_action(
    data: bytes,
    item_start: int,
    limit: int,
    tag_width: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    tag, actual_tag_width, _raw = read_buff_timeline_first_union_tag(data, item_start, limit)
    if tag != BUFF_SEND_BATTLE_SIGNAL_TO_LEVEL_TAG or actual_tag_width != tag_width:
        raise ValueError("sendBattleSignal:tag-mismatch")
    if tag_width != 3:
        raise ValueError(f"sendBattleSignal:tag-width={tag_width}")
    if member_count != 6:
        raise ValueError(f"sendBattleSignal:member-count={member_count}")
    offset = item_start + tag_width + 1
    prefix, offset = read_buff_ability_action_common_prefix_bounded(
        data,
        offset,
        limit,
        "sendBattleSignal.prefix",
    )
    double_value, offset = read_buff_blackboard_float_raw_field_exact(
        data,
        offset,
        "sendBattleSignal.doubleValue",
    )
    signal_id, offset = read_buff_blackboard_string_field_exact(
        data,
        offset,
        "sendBattleSignal.signalId",
    )
    return {
        "type": BUFF_ABILITY_ACTION_TAG_NAMES[BUFF_SEND_BATTLE_SIGNAL_TO_LEVEL_TAG],
        "decodeStatus": "exact",
        "schemaSource": (
            "MemoryPack formatter setter order: AbilityActionData prefix, doubleValue, signalId; "
            "current BuffData bytes match setter order rather than runtime field display order"
        ),
        "byteLength": offset - item_start,
        "prefix": prefix,
        "doubleValue": double_value,
        "signalId": signal_id,
    }, offset


def decode_buff_send_battle_signal_to_level_action(
    data: bytes,
    item_start: int,
    item_end: int,
    tag_width: int,
    member_count: int,
) -> dict[str, Any]:
    decoded, end = consume_buff_send_battle_signal_to_level_action(
        data,
        item_start,
        item_end,
        tag_width,
        member_count,
    )
    if end != item_end:
        raise ValueError(f"sendBattleSignal:tail-at={format_offset(end)} end={format_offset(item_end)}")
    return decoded


def consume_buff_compare_float_action(
    data: bytes,
    item_start: int,
    limit: int,
    tag_width: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    tag, actual_tag_width, _raw = read_buff_timeline_first_union_tag(data, item_start, limit)
    if tag != BUFF_COMPARE_FLOAT_ACTION_TAG or actual_tag_width != tag_width:
        raise ValueError("compareFloat:tag-mismatch")
    if tag_width != 1:
        raise ValueError(f"compareFloat:tag-width={tag_width}")
    if member_count != 7:
        raise ValueError(f"compareFloat:member-count={member_count}")
    offset = item_start + tag_width + 1
    prefix, offset = read_buff_ability_action_common_prefix_bounded(
        data,
        offset,
        limit,
        "compareFloat.prefix",
    )
    compare, offset = read_buff_i32_field(data, offset, "compareFloat.compare")
    if compare < 0 or compare > 16:
        raise ValueError(f"compareFloat.compare={compare}")
    value_a, offset = read_buff_blackboard_float_raw_field_exact(
        data,
        offset,
        "compareFloat.valueA",
    )
    value_b, offset = read_buff_blackboard_float_raw_field_exact(
        data,
        offset,
        "compareFloat.valueB",
    )
    return {
        "type": BUFF_ABILITY_ACTION_TAG_NAMES[BUFF_COMPARE_FLOAT_ACTION_TAG],
        "decodeStatus": "exact",
        "schemaSource": (
            "MemoryPack setter order: AbilityActionData prefix, compare, valueA, valueB; "
            "valueA/valueB are member-count-3 BlackboardFloat wrappers; compare enum labels are unmapped"
        ),
        "byteLength": offset - item_start,
        "prefix": prefix,
        "compare": compare,
        "valueA": value_a,
        "valueB": value_b,
    }, offset


def consume_buff_get_ai_trans_data_action(
    data: bytes,
    item_start: int,
    limit: int,
    tag_width: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    tag, actual_tag_width, _raw = read_buff_timeline_first_union_tag(data, item_start, limit)
    if tag != BUFF_GET_AI_TRANS_DATA_ACTION_TAG or actual_tag_width != tag_width:
        raise ValueError("getAITransData:tag-mismatch")
    if tag_width != 1:
        raise ValueError(f"getAITransData:tag-width={tag_width}")
    if member_count != 6:
        raise ValueError(f"getAITransData:member-count={member_count}")
    offset = item_start + tag_width + 1
    prefix, offset = read_buff_ability_action_common_prefix_bounded(
        data,
        offset,
        limit,
        "getAITransData.prefix",
    )
    ai_trans_key, offset = read_buff_memorypack_utf8_string_strict_bounded(
        data,
        offset,
        limit,
        "getAITransData.aiTransKey",
        max_length=256,
    )
    if not ai_trans_key:
        raise ValueError("getAITransData.aiTransKey:empty")
    save_to, offset = read_buff_memorypack_utf8_string_strict_bounded(
        data,
        offset,
        limit,
        "getAITransData.saveTo",
        max_length=256,
    )
    if not save_to:
        raise ValueError("getAITransData.saveTo:empty")
    return {
        "type": BUFF_ABILITY_ACTION_TAG_NAMES[BUFF_GET_AI_TRANS_DATA_ACTION_TAG],
        "decodeStatus": "exact",
        "schemaSource": (
            "MemoryPack setter order: AbilityActionData prefix, aiTransKey, saveTo"
        ),
        "byteLength": offset - item_start,
        "prefix": prefix,
        "aiTransKey": ai_trans_key,
        "saveTo": save_to,
    }, offset


def consume_buff_interrupt_action(
    data: bytes,
    item_start: int,
    limit: int,
    tag_width: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    tag, actual_tag_width, _raw = read_buff_timeline_first_union_tag(data, item_start, limit)
    if tag != BUFF_INTERRUPT_ACTION_TAG or actual_tag_width != tag_width:
        raise ValueError("interruptAction:tag-mismatch")
    if tag_width != 1:
        raise ValueError(f"interruptAction:tag-width={tag_width}")
    if member_count != 8:
        raise ValueError(f"interruptAction:member-count={member_count}")
    offset = item_start + tag_width + 1
    prefix, offset = read_buff_ability_action_common_prefix_bounded(
        data,
        offset,
        limit,
        "interruptAction.prefix",
    )
    attacker, offset = read_buff_target_settings_envelope_partial(
        data,
        offset,
        limit,
        "interruptAction.attacker",
    )
    defender, offset = read_buff_target_settings_envelope_partial(
        data,
        offset,
        limit,
        "interruptAction.defender",
    )
    immobilized_time, offset = read_buff_f32_field(data, offset, "interruptAction.immobilizedTime")
    if immobilized_time < 0 or immobilized_time > 10_000:
        raise ValueError(f"interruptAction.immobilizedTime:out-of-range={immobilized_time}")
    override_super_armor_limit, offset = read_buff_i32_field(
        data,
        offset,
        "interruptAction.overrideSuperArmorLimit",
    )
    if override_super_armor_limit < -1 or override_super_armor_limit > 1_000_000:
        raise ValueError(
            f"interruptAction.overrideSuperArmorLimit:implausible={override_super_armor_limit}"
        )
    return {
        "type": BUFF_ABILITY_ACTION_TAG_NAMES[BUFF_INTERRUPT_ACTION_TAG],
        "decodeStatus": "partial",
        "semanticStatus": "partial-attacker-defender-target-settings-envelopes-opaque",
        "schemaSource": (
            "MemoryPack setter order: AbilityActionData prefix, attacker, defender, immobilizedTime, "
            "overrideSuperArmorLimit; both TargetSettings envelopes remain partial"
        ),
        "byteLength": offset - item_start,
        "prefix": prefix,
        "attackerEnvelopePartial": attacker,
        "defenderEnvelopePartial": defender,
        "immobilizedTime": round(immobilized_time, 6),
        "overrideSuperArmorLimit": override_super_armor_limit,
    }, offset


def consume_buff_spell_infliction_action(
    data: bytes,
    item_start: int,
    limit: int,
    tag_width: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    tag, actual_tag_width, _raw = read_buff_timeline_first_union_tag(data, item_start, limit)
    if tag != BUFF_SPELL_INFLICTION_ACTION_TAG or actual_tag_width != tag_width:
        raise ValueError("spellInfliction:tag-mismatch")
    if tag_width != 3:
        raise ValueError(f"spellInfliction:tag-width={tag_width}")
    if member_count != 8:
        raise ValueError(f"spellInfliction:member-count={member_count}")
    offset = item_start + tag_width + 1
    prefix, offset = read_buff_ability_action_common_prefix_bounded(
        data,
        offset,
        limit,
        "spellInfliction.prefix",
    )
    infliction_type, offset = read_buff_i32_field(data, offset, "spellInfliction.inflictionType")
    if infliction_type < 0 or infliction_type > 1_000:
        raise ValueError(f"spellInfliction.inflictionType={infliction_type}")
    is_extra, offset = read_buff_bool_field(data, offset, "spellInfliction.isExtra")
    source, offset = read_buff_target_settings_envelope_partial(
        data,
        offset,
        limit,
        "spellInfliction.source",
    )
    target, offset = read_buff_target_settings_envelope_partial(
        data,
        offset,
        limit,
        "spellInfliction.target",
    )
    return {
        "type": BUFF_ABILITY_ACTION_TAG_NAMES[BUFF_SPELL_INFLICTION_ACTION_TAG],
        "decodeStatus": "partial",
        "semanticStatus": "partial-source-target-settings-envelopes-opaque",
        "schemaSource": (
            "MemoryPack setter order: AbilityActionData prefix, inflictionType, isExtra, source, target; "
            "both TargetSettings envelopes remain partial and inflictionType enum labels are unmapped"
        ),
        "byteLength": offset - item_start,
        "prefix": prefix,
        "inflictionType": infliction_type,
        "isExtra": is_extra,
        "sourceEnvelopePartial": source,
        "targetEnvelopePartial": target,
    }, offset


def read_buff_bool_field_bounded(
    data: bytes,
    offset: int,
    limit: int,
    field_name: str,
) -> tuple[bool, int]:
    if offset >= limit:
        raise ValueError(f"{field_name}:truncated-bool")
    return read_buff_bool_field(data, offset, field_name)


def read_buff_i32_field_bounded(
    data: bytes,
    offset: int,
    limit: int,
    field_name: str,
) -> tuple[int, int]:
    if offset + 4 > limit:
        raise ValueError(f"{field_name}:truncated-i32")
    return struct.unpack_from("<i", data, offset)[0], offset + 4


def read_buff_u32_field_bounded(
    data: bytes,
    offset: int,
    limit: int,
    field_name: str,
) -> tuple[int, int]:
    if offset + 4 > limit:
        raise ValueError(f"{field_name}:truncated-u32")
    return struct.unpack_from("<I", data, offset)[0], offset + 4


def try_read_buff_target_settings_envelope_partial(
    data: bytes,
    offset: int,
    limit: int,
    field_name: str,
) -> tuple[dict[str, Any], int] | None:
    try:
        return read_buff_target_settings_envelope_partial(data, offset, limit, field_name)
    except (struct.error, UnicodeDecodeError, ValueError):
        return None


def consume_buff_camera_impulse_action(
    data: bytes,
    item_start: int,
    limit: int,
    tag_width: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    tag, actual_tag_width, _raw = read_buff_timeline_first_union_tag(data, item_start, limit)
    if tag != BUFF_CAMERA_IMPULSE_ACTION_TAG or actual_tag_width != tag_width:
        raise ValueError("cameraImpulse:tag-mismatch")
    if tag_width != 1:
        raise ValueError(f"cameraImpulse:tag-width={tag_width}")
    if member_count != 12:
        raise ValueError(f"cameraImpulse:member-count={member_count}")
    offset = item_start + tag_width + 1
    prefix, offset = read_buff_ability_action_common_prefix_bounded(
        data,
        offset,
        limit,
        "cameraImpulse.prefix",
    )
    bone_node, offset = read_buff_memorypack_utf8_string_strict_bounded(
        data,
        offset,
        limit,
        "cameraImpulse.boneNode",
        max_length=256,
    )
    follow_target, offset = read_buff_bool_field_bounded(
        data,
        offset,
        limit,
        "cameraImpulse.followTarget",
    )

    impulse_start = offset
    if impulse_start >= limit:
        raise ValueError("cameraImpulse.impulseDefinitionData:truncated-member-count")
    impulse_member_count = data[impulse_start]
    if impulse_member_count != BUFF_CAMERA_IMPULSE_DEFINITION_MEMBER_COUNT:
        raise ValueError(f"cameraImpulse.impulseDefinitionData.memberCount={impulse_member_count}")

    curve_length_offset = impulse_start + BUFF_CAMERA_IMPULSE_CURVE_LENGTH_REL_OFFSET
    if curve_length_offset + 4 > limit:
        raise ValueError("cameraImpulse.impulseDefinitionData.curveString:truncated-length")
    curve_length = struct.unpack_from("<I", data, curve_length_offset)[0]
    curve_start = curve_length_offset + 4
    curve_end = curve_start + curve_length
    if curve_length > 512 or curve_end > limit:
        raise ValueError(f"cameraImpulse.impulseDefinitionData.curveString.length={curve_length}")
    curve_path = ""
    if curve_length:
        try:
            curve_path = data[curve_start:curve_end].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("cameraImpulse.impulseDefinitionData.curveString:invalid-utf8") from exc
        if any(ord(ch) < 32 for ch in curve_path):
            raise ValueError("cameraImpulse.impulseDefinitionData.curveString:control-char")

    target_start = impulse_start + BUFF_CAMERA_IMPULSE_TARGET_BASE_REL_OFFSET + curve_length
    bool_start = target_start - BUFF_CAMERA_IMPULSE_BOOL_TAIL_BYTES
    if bool_start < impulse_start or target_start > limit:
        raise ValueError(f"cameraImpulse.targetSettings.computedStart={format_offset(target_start)}")
    opaque_raw = data[impulse_start:bool_start]
    if len(opaque_raw) > BUFF_CAMERA_IMPULSE_OPAQUE_NESTED_MAX_BYTES:
        raise ValueError(f"cameraImpulse.opaqueNested:bytes={len(opaque_raw)}")

    real_camera_shake_2d, bool_offset = read_buff_bool_field_bounded(
        data,
        bool_start,
        target_start,
        "cameraImpulse.realCameraShake2D",
    )
    release_when_action_ends, bool_offset = read_buff_bool_field_bounded(
        data,
        bool_offset,
        target_start,
        "cameraImpulse.releaseWhenActionEnds",
    )
    if bool_offset != target_start:
        raise ValueError(f"cameraImpulse.boolTail:tail-at={format_offset(bool_offset)}")

    target_settings, target_end = read_buff_target_settings_envelope_partial(
        data,
        target_start,
        limit,
        "cameraImpulse.targetSettings",
    )

    return {
        "type": BUFF_ABILITY_ACTION_TAG_NAMES[BUFF_CAMERA_IMPULSE_ACTION_TAG],
        "decodeStatus": "partial",
        "semanticStatus": "partial-impulse-definition-mount-position-opaque",
        "schemaSource": (
            "MemoryPack setter order: AbilityActionData prefix, boneNode, followTarget, "
            "impulseDefinitionData, mountPoint, positionOffset, realCameraShake2D, "
            "releaseWhenActionEnds, targetSettings. Nested impulse definition, mountPoint, "
            "and positionOffset bytes remain opaque; targetSettings start is computed from "
            "ImpulseDefinitionData member-count 18 and its curve/noise string length, then "
            "accepted only when the envelope lands on a valid computed item boundary."
        ),
        "byteLength": target_end - item_start,
        "prefix": prefix,
        "boneNode": bone_node or "",
        "followTarget": follow_target,
        "impulseDefinitionMountPositionOpaque": {
            "status": "partial",
            "semanticStatus": "partial-impulse-definition-mount-position-opaque",
            "offset": format_offset(impulse_start),
            "bytes": len(opaque_raw),
            "memberCountCandidate": impulse_member_count,
            "curveOrNoiseStringOffset": format_offset(curve_start),
            "curveOrNoiseStringLength": curve_length,
            "curveOrNoisePathCandidate": curve_path,
            "rawSha256": hashlib.sha256(opaque_raw).hexdigest(),
            "prefixHex": opaque_raw[:48].hex(" "),
            "tailHex": opaque_raw[-48:].hex(" "),
            "stringHits": scan_length_prefixed_utf8_string_hits(
                opaque_raw,
                start=0,
                max_scan_bytes=len(opaque_raw),
                max_samples=8,
                max_length=256,
            ),
        },
        "realCameraShake2D": real_camera_shake_2d,
        "releaseWhenActionEnds": release_when_action_ends,
        "targetSettingsEnvelopePartial": target_settings,
    }, target_end


def decode_buff_camera_impulse_action(
    data: bytes,
    item_start: int,
    item_end: int,
    tag_width: int,
    member_count: int,
) -> dict[str, Any]:
    decoded, end = consume_buff_camera_impulse_action(
        data,
        item_start,
        item_end,
        tag_width,
        member_count,
    )
    if end != item_end:
        raise ValueError(f"cameraImpulse:tail-at={format_offset(end)} end={format_offset(item_end)}")
    return decoded


def read_buff_utf8_string_ending_at(
    data: bytes,
    value_end: int,
    lower_bound: int,
    field_name: str,
    *,
    max_length: int = 512,
    allow_empty: bool = True,
) -> tuple[str, int, int]:
    candidates: list[tuple[str, int, int]] = []
    max_scan = min(max_length, max(0, value_end - lower_bound - 4))
    for length in range(max_scan + 1):
        length_offset = value_end - 4 - length
        value_start = length_offset + 4
        if length_offset < lower_bound or value_start > value_end:
            continue
        if struct.unpack_from("<I", data, length_offset)[0] != length:
            continue
        raw = data[value_start:value_end]
        try:
            value = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if not allow_empty and not value:
            continue
        if any(ord(ch) < 32 for ch in value):
            continue
        candidates.append((value, length_offset, value_start))
    if len(candidates) != 1:
        raise ValueError(f"{field_name}:ending-string-candidates={len(candidates)}")
    return candidates[0]


def read_buff_find_target_body_partial(
    data: bytes,
    body_start: int,
    body_end: int,
    field_name: str,
) -> dict[str, Any]:
    if body_end <= body_start:
        raise ValueError(f"{field_name}:empty")
    if data[body_start] != 8:
        raise ValueError(f"{field_name}.advancedSelectorDirection.memberCount={data[body_start]}")
    if body_start + 5 > body_end:
        raise ValueError(f"{field_name}.advancedSelectorDirection.directionType:truncated")
    direction_type = struct.unpack_from("<i", data, body_start + 1)[0]
    if direction_type < 0 or direction_type > 32:
        raise ValueError(f"{field_name}.advancedSelectorDirection.directionType={direction_type}")
    if body_end - body_start < 15:
        raise ValueError(f"{field_name}:too-short")
    use_advanced_direction_setting, bool_offset = read_buff_bool_field_bounded(
        data,
        body_end - 2,
        body_end,
        f"{field_name}.useAdvancedDirectionSetting",
    )
    use_center_entity_mount_point, bool_offset = read_buff_bool_field_bounded(
        data,
        bool_offset,
        body_end,
        f"{field_name}.useCenterEntityMountPoint",
    )
    if bool_offset != body_end:
        raise ValueError(f"{field_name}.tailBools:tail-at={format_offset(bool_offset)}")
    target_group_key, target_group_length_offset, _target_group_value_offset = read_buff_utf8_string_ending_at(
        data,
        body_end - 2,
        body_start + 5,
        f"{field_name}.targetGroupKey",
        max_length=256,
        allow_empty=False,
    )
    target_offset = target_group_length_offset - 4
    if target_offset < body_start + 5:
        raise ValueError(f"{field_name}.target:truncated")
    target = struct.unpack_from("<i", data, target_offset)[0]
    if target < 0 or target > 256:
        raise ValueError(f"{field_name}.target={target}")
    selector_owner_context_key, owner_context_length_offset, _owner_context_value_offset = (
        read_buff_utf8_string_ending_at(
            data,
            target_offset,
            body_start + 5,
            f"{field_name}.selectorOwnerContextKey",
            max_length=256,
            allow_empty=True,
        )
    )
    selector_owner_offset = owner_context_length_offset - 4
    if selector_owner_offset < body_start + 5:
        raise ValueError(f"{field_name}.selectorOwner:truncated")
    selector_owner = struct.unpack_from("<i", data, selector_owner_offset)[0]
    if selector_owner < 0 or selector_owner > 256:
        raise ValueError(f"{field_name}.selectorOwner={selector_owner}")
    middle_start = body_start + 5
    middle_end = selector_owner_offset
    if middle_end < middle_start:
        raise ValueError(f"{field_name}.middle:negative")
    middle_raw = data[middle_start:middle_end]
    return {
        "advancedSelectorDirectionPartial": {
            "status": "partial",
            "semanticStatus": "partial-direction-settings-fields-opaque",
            "offset": format_offset(body_start),
            "memberCountCandidate": data[body_start],
            "directionTypeRaw": direction_type,
            "schemaSource": "Beyond.Gameplay.Core.DirectionSettings starts with memberCount=8 and directionType; remaining source/target settings and mount-point fields remain opaque",
        },
        "bodyMiddleOpaque": {
            "status": "partial",
            "semanticStatus": "partial-find-target-selector-and-direction-fields-opaque",
            "offset": format_offset(middle_start),
            "bytes": len(middle_raw),
            "rawSha256": hashlib.sha256(middle_raw).hexdigest(),
            "prefixHex": middle_raw[:48].hex(" "),
            "tailHex": middle_raw[-48:].hex(" "),
            "stringHits": scan_length_prefixed_utf8_string_hits(
                middle_raw,
                start=0,
                max_scan_bytes=len(middle_raw),
                max_samples=8,
                max_length=256,
            ),
        },
        "selectorOwner": selector_owner,
        "selectorOwnerContextKey": selector_owner_context_key,
        "target": target,
        "targetGroupKey": target_group_key,
        "useAdvancedDirectionSetting": use_advanced_direction_setting,
        "useCenterEntityMountPoint": use_center_entity_mount_point,
        "tailFieldOrderSource": "byte-validated exact FindTargetAction bodies plus generated ForMemoryPack wrapper tail order",
        "tailFieldOffsets": {
            "selectorOwner": format_offset(selector_owner_offset),
            "selectorOwnerContextKeyLength": format_offset(owner_context_length_offset),
            "target": format_offset(target_offset),
            "targetGroupKeyLength": format_offset(target_group_length_offset),
            "useAdvancedDirectionSetting": format_offset(body_end - 2),
            "useCenterEntityMountPoint": format_offset(body_end - 1),
        },
    }


BUFF_SELECTOR_MAX_NESTED_DEPTH = 8


BUFF_SELECTOR_MAX_LIST_COUNT = 256


BUFF_SELECTOR_SCHEMA_SOURCE_NOTE = (
    "SelectorData layout byte-proven 2026-07-05: member-count headers, base-first "
    "alphabetical member order, selector union tags from GameAssembly formatter cctors; "
    "validated by exact end consumption on all bounded FindTargetAction samples and "
    "typed-chain landings (scratch/animestudio/selectordata_20260705)."
)


BUFF_SELECTOR_SHAPEDATA_MEMBERS = (
    ("angle", "bbparam"), ("castDirection", "i32"), ("centerOffset", "bbvector3"),
    ("dirRefMountPoint", "i32"), ("directionRef", "i32"), ("enablePreview", "bool"),
    ("eulerAngle", "bbvector3"), ("height", "bbparam"), ("hitEffectTowardsType", "i32"),
    ("limitAngle", "bool"), ("limitHeight", "bool"), ("maxHeight", "bbparam"),
    ("posRefMP", "i32"), ("positionRef", "i32"), ("radius", "bbparam"),
    ("shapeType", "i32"), ("size", "bbvector3"), ("useDirection", "bool"),
)


BUFF_SELECTOR_TARGETFINDER_MEMBERS = (
    ("autoSetTargetFaction", "bool"), ("checkAlive", "bool"),
    ("containsUnMarkable", "bool"), ("factionTarget", "i32"),
    ("targetFactionType", "i32"),
)


BUFF_SELECTOR_FINDER_SUBTYPES: dict[int, tuple[str, tuple | None]] = {
    0x00: ("AbilityEntityTargetFinder", ()),
    0x01: ("CharacterTeamFinder", ()),
    0x02: ("FixedPointFinder", (("positionOffset", "vector3"),
                                ("rotationOffset", "quaternion"),
                                ("sampleRadius", "bbparam"),
                                ("snapToNavmesh", "bool"))),
    0x03: ("GlobalContextFinder", (("targetGroupKey", "string"),)),
    0x04: ("GodEntityFinder", ()),
    0x05: ("GuardAITargetFinder", ()),
    0x06: ("HitBoxFinder", BUFF_SELECTOR_TARGETFINDER_MEMBERS + (
        ("checkIntUnSelectableTag", "bool"), ("shapeList", "shapedatalist"),
        ("targetObjectType", "i32"))),
    0x07: ("InFightEnemyFinder", ()),
    0x08: ("InteractiveShapeFinder", (("checkIntUnSelectableTag", "bool"),)),
    0x09: ("MainTargetFinder", ()),
    0x0A: ("OwnerPartsFinder", (("partQuery", "tagquery"),)),
    0x0B: ("OwnerSpawnedEntityFinder", (("spawnedObjectType", "i32"),)),
    0x0C: ("PointFinder", (("positionOffset", "bbvector3"),
                           ("rotationOffset", "bbvector3"))),
    0x0D: ("RandomPointFinder", (("angle", "bbparam"),
                                 ("localPlaneRotationEulers", "bbvector3"),
                                 ("minRadius", "bbparam"), ("pointNum", "bbparam"),
                                 ("radius", "bbparam"), ("shape", "i32"),
                                 ("snapToNavMesh", "bool"))),
    0x0E: ("ShapeFinder", None),  # shapeData (battle shape data) layout unproven
    0x0F: ("ShapeFinderData", ()),
    0x10: ("SmartTargetFinder", (("range", "bbparam"),
                                 ("selectSetting", "smarttargetselectsetting"),
                                 ("useCustomRange", "bool"))),
    0x11: ("SnapPointFinder", (("radius", "bbparam"),
                               ("snapTargetSettings", "targetsettings"))),
    0x12: ("SourceFinder", ()),
    0x13: ("TargetFinder", BUFF_SELECTOR_TARGETFINDER_MEMBERS),
}


BUFF_SELECTOR_VALIDATOR_SUBTYPES: dict[int, tuple[str, tuple | None]] = {
    0x00: ("AttributeValidator", (("attributeType", "i32"), ("checkMax", "bool"),
                                  ("checkMin", "bool"), ("maxValue", "f64"),
                                  ("minValue", "f64"))),
    0x01: ("CheckRaycastValidator", (("checkLayerMask", "i32"),
                                     ("secondCheckLayerMask", "i32"))),
    0x02: ("CurHpRatioValidator", (("compareType", "i32"), ("value", "bbparam"))),
    0x03: ("DistanceValidator", (("clampToXZ", "bool"), ("compareType", "i32"),
                                 ("value", "bbparam"))),
    0x04: ("ExcludeOwnerValidator", ()),
    0x05: ("HittableObjectValidator", ()),
    0x06: ("InteractiveKeyValidator", (("interactiveKey", "string"),)),
    0x07: ("MainCharacterValidator", ()),
    0x08: ("SkillCastIdValidator", ()),
    0x09: ("TagValidator", (("query", "tagquery"),)),
    0x0A: ("TargetContainsValidator", (("parentTargetSettings", "targetsettings"),)),
}


BUFF_SELECTOR_POSTPROCESSOR_SUBTYPES: dict[int, tuple[str, tuple | None]] = {
    0x00: ("ConvertToBoxCenterPlaneProjectionPoint", (("boxShape", "shapedatalist"),)),
    0x01: ("ConvertToPosition", ()),
    0x02: ("ConvertToSlot", ()),
    0x03: ("ExcludeTarget", (("excludedTargetSettings", "targetsettings"),)),
    0x04: ("LockOrMarkTargetFilter", ()),
    0x05: ("NavMeshPathPositionProcessor", (
        ("allowCheckMainCharPosToDestPathAvailable", "bool"),
        ("checkMaxDistance", "bool"), ("clampDirToXZ", "bool"),
        ("getNavPosInRangeRadius", "bbparam"), ("ignoreNavmeshLink", "bool"),
        ("maxDistance", "f32"), ("snapToFloor", "bool"), ("throughWall", "bool"))),
    0x06: ("PriorityFilter", None),  # buffFilterSettings layout unproven
    0x07: ("ShuffleTarget", (("targetNumLimit", "bbparam"),)),
    0x08: ("TargetPriorityFilter", (("limitMaxNum", "bool"), ("maxNum", "i32"),
                                    ("targetSettings", "targetsettings"))),
}


BUFF_FIND_TARGET_BODY_MEMBERS = (
    ("advancedSelectorDirection", "directionsettings"), ("center", "i32"),
    ("centerContextKey", "string"), ("centerMountPoint", "i32"),
    ("centerToGround", "bool"), ("contextKey", "string"),
    ("selectorData", "selectordata"), ("selectorDirection", "i32"),
    ("selectorOwner", "i32"), ("selectorOwnerContextKey", "string"),
    ("target", "i32"), ("targetGroupKey", "string"),
    ("useAdvancedDirectionSetting", "bool"), ("useCenterEntityMountPoint", "bool"),
)


class BuffSelectorSubtypeUnproven(ValueError):
    """A selector union payload uses a subtype whose layout is not byte-proven."""


def read_buff_selector_object_header(
    data: bytes,
    offset: int,
    limit: int,
    expected_member_count: int,
    field_name: str,
) -> tuple[bool, int]:
    """Read a MemoryPack object header byte. Returns (present, next_offset)."""
    if offset >= limit:
        raise ValueError(f"{field_name}:truncated-member-count")
    header = data[offset]
    offset += 1
    if header == 0xFF:
        return False, offset
    if header != expected_member_count:
        raise ValueError(
            f"{field_name}:member-count={header} expected={expected_member_count}"
        )
    return True, offset


def read_buff_selector_bool(data: bytes, offset: int, limit: int, field_name: str) -> tuple[bool, int]:
    if offset >= limit:
        raise ValueError(f"{field_name}:truncated-bool")
    value = data[offset]
    if value not in (0, 1):
        raise ValueError(f"{field_name}:bad-bool=0x{value:02x}")
    return bool(value), offset + 1


def read_buff_selector_i32(data: bytes, offset: int, limit: int, field_name: str) -> tuple[int, int]:
    if offset + 4 > limit:
        raise ValueError(f"{field_name}:truncated-i32")
    return struct.unpack_from("<i", data, offset)[0], offset + 4


def read_buff_selector_f32(data: bytes, offset: int, limit: int, field_name: str) -> tuple[float, int]:
    if offset + 4 > limit:
        raise ValueError(f"{field_name}:truncated-f32")
    return struct.unpack_from("<f", data, offset)[0], offset + 4


def read_buff_selector_f64(data: bytes, offset: int, limit: int, field_name: str) -> tuple[float, int]:
    if offset + 8 > limit:
        raise ValueError(f"{field_name}:truncated-f64")
    return struct.unpack_from("<d", data, offset)[0], offset + 8


def read_buff_selector_blackboard_param(
    data: bytes,
    offset: int,
    limit: int,
    field_name: str,
) -> tuple[dict[str, Any] | None, int]:
    present, offset = read_buff_selector_object_header(data, offset, limit, 3, field_name)
    if not present:
        return None, offset
    key, offset = read_buff_memorypack_utf8_string_strict_bounded(
        data, offset, limit, f"{field_name}.blackboardKey", max_length=256,
    )
    use_key, offset = read_buff_selector_bool(data, offset, limit, f"{field_name}.useBlackboardKey")
    if offset + 4 > limit:
        raise ValueError(f"{field_name}.value:truncated")
    value_f32 = struct.unpack_from("<f", data, offset)[0]
    value_i32 = struct.unpack_from("<i", data, offset)[0]
    offset += 4
    return {
        "blackboardKey": key,
        "useBlackboardKey": use_key,
        "valueF32": value_f32 if math.isfinite(value_f32) else None,
        "valueI32": value_i32,
    }, offset


def read_buff_selector_blackboard_vector3(
    data: bytes,
    offset: int,
    limit: int,
    field_name: str,
) -> tuple[list[Any] | None, int]:
    present, offset = read_buff_selector_object_header(data, offset, limit, 3, field_name)
    if not present:
        return None, offset
    components = []
    for axis in ("x", "y", "z"):
        component, offset = read_buff_selector_blackboard_param(
            data, offset, limit, f"{field_name}.{axis}",
        )
        components.append(component)
    return components, offset


def read_buff_selector_gameplay_tag(
    data: bytes,
    offset: int,
    limit: int,
    field_name: str,
) -> tuple[dict[str, Any] | None, int]:
    # Beyond.Gameplay.Core.GameplayTag: [tagId:int, tagName:string]
    present, offset = read_buff_selector_object_header(data, offset, limit, 2, field_name)
    if not present:
        return None, offset
    tag_id, offset = read_buff_selector_i32(data, offset, limit, f"{field_name}.tagId")
    tag_name, offset = read_buff_memorypack_utf8_string_strict_bounded(
        data, offset, limit, f"{field_name}.tagName", max_length=512,
    )
    return {"tagId": tag_id, "tagName": tag_name}, offset


def read_buff_selector_tag_query(
    data: bytes,
    offset: int,
    limit: int,
    field_name: str,
) -> tuple[dict[str, Any] | None, int]:
    # Beyond.Gameplay.Core.GameplayTagQuery: [queryType:enum, tags:List<GameplayTag>]
    present, offset = read_buff_selector_object_header(data, offset, limit, 2, field_name)
    if not present:
        return None, offset
    query_type, offset = read_buff_selector_i32(data, offset, limit, f"{field_name}.queryType")
    tags, offset = read_buff_selector_list(
        data, offset, limit, f"{field_name}.tags", read_buff_selector_gameplay_tag,
    )
    return {"queryType": query_type, "tags": tags}, offset


def read_buff_selector_buff_find_settings(
    data: bytes,
    offset: int,
    limit: int,
    field_name: str,
) -> tuple[dict[str, Any] | None, int]:
    # Beyond.Gameplay.Core.BuffFindSettings: [buffIdList:List<int>, checkType:enum,
    # tagQuery:GameplayTagQuery]
    present, offset = read_buff_selector_object_header(data, offset, limit, 3, field_name)
    if not present:
        return None, offset
    buff_ids, offset = read_buff_selector_list(
        data, offset, limit, f"{field_name}.buffIdList", read_buff_selector_list_i32_element,
    )
    check_type, offset = read_buff_selector_i32(data, offset, limit, f"{field_name}.checkType")
    tag_query, offset = read_buff_selector_tag_query(data, offset, limit, f"{field_name}.tagQuery")
    return {"buffIdList": buff_ids, "checkType": check_type, "tagQuery": tag_query}, offset


def read_buff_selector_smart_target_select_setting(
    data: bytes,
    offset: int,
    limit: int,
    field_name: str,
) -> tuple[dict[str, Any] | None, int]:
    # Beyond.Gameplay.Core.SmartTargetSelectSetting: [smartTargetBuffFindSettings,
    # smartTargetBuffIds:List<int>, smartTargetSelectStrategy:enum,
    # smartTargetTagQuery:GameplayTagQuery]
    present, offset = read_buff_selector_object_header(data, offset, limit, 4, field_name)
    if not present:
        return None, offset
    find_settings, offset = read_buff_selector_buff_find_settings(
        data, offset, limit, f"{field_name}.smartTargetBuffFindSettings",
    )
    buff_ids, offset = read_buff_selector_list(
        data, offset, limit, f"{field_name}.smartTargetBuffIds",
        read_buff_selector_list_i32_element,
    )
    strategy, offset = read_buff_selector_i32(
        data, offset, limit, f"{field_name}.smartTargetSelectStrategy",
    )
    tag_query, offset = read_buff_selector_tag_query(
        data, offset, limit, f"{field_name}.smartTargetTagQuery",
    )
    return {
        "smartTargetBuffFindSettings": find_settings,
        "smartTargetBuffIds": buff_ids,
        "smartTargetSelectStrategy": strategy,
        "smartTargetTagQuery": tag_query,
    }, offset


def read_buff_selector_list_i32_element(
    data: bytes,
    offset: int,
    limit: int,
    field_name: str,
) -> tuple[int, int]:
    return read_buff_selector_i32(data, offset, limit, field_name)


def read_buff_selector_list(
    data: bytes,
    offset: int,
    limit: int,
    field_name: str,
    element_reader,
) -> tuple[list[Any] | None, int]:
    count, offset = read_buff_u32_field_bounded(data, offset, limit, f"{field_name}.count")
    if count == MEMORYPACK_NULL_COUNT:
        return None, offset
    if count > BUFF_SELECTOR_MAX_LIST_COUNT:
        raise ValueError(f"{field_name}:list-count={count}")
    items = []
    for index in range(count):
        item, offset = element_reader(data, offset, limit, f"{field_name}[{index}]")
        items.append(item)
    return items, offset


def read_buff_selector_shape_data(
    data: bytes,
    offset: int,
    limit: int,
    field_name: str,
) -> tuple[dict[str, Any] | None, int]:
    present, offset = read_buff_selector_object_header(
        data, offset, limit, len(BUFF_SELECTOR_SHAPEDATA_MEMBERS), field_name,
    )
    if not present:
        return None, offset
    out: dict[str, Any] = {}
    for member_name, kind in BUFF_SELECTOR_SHAPEDATA_MEMBERS:
        out[member_name], offset = read_buff_selector_member(
            data, offset, limit, kind, f"{field_name}.{member_name}", 0,
        )
    return out, offset


def read_buff_selector_union(
    data: bytes,
    offset: int,
    limit: int,
    table: dict[int, tuple[str, tuple | None]],
    family: str,
    field_name: str,
    depth: int,
) -> tuple[dict[str, Any] | None, int]:
    if depth > BUFF_SELECTOR_MAX_NESTED_DEPTH:
        raise ValueError(f"{field_name}:selector-depth-exceeded")
    if offset >= limit:
        raise ValueError(f"{field_name}:truncated-union-tag")
    tag = data[offset]
    offset += 1
    if tag == 0xFF:
        return None, offset
    if tag == MEMORYPACK_UNION_WIDE_TAG:
        raise ValueError(f"{field_name}:wide-union-tag")
    entry = table.get(tag)
    if entry is None:
        raise BuffSelectorSubtypeUnproven(f"{field_name}:unknown-{family}-tag=0x{tag:02x}")
    subtype_name, members = entry
    if members is None:
        raise BuffSelectorSubtypeUnproven(
            f"{field_name}:{family}-subtype-layout-unproven={subtype_name}"
        )
    present, offset = read_buff_selector_object_header(
        data, offset, limit, len(members), f"{field_name}.{subtype_name}",
    )
    if not present:
        raise ValueError(f"{field_name}.{subtype_name}:null-payload-after-tag")
    out: dict[str, Any] = {"subtype": subtype_name}
    for member_name, kind in members:
        out[member_name], offset = read_buff_selector_member(
            data, offset, limit, kind, f"{field_name}.{subtype_name}.{member_name}", depth,
        )
    return out, offset


def read_buff_selector_data_full(
    data: bytes,
    offset: int,
    limit: int,
    field_name: str,
    depth: int,
) -> tuple[dict[str, Any] | None, int]:
    # Beyond.Gameplay.Core.Selector+SelectorData, alphabetical:
    # finderData (union), postProcessorData (list of unions), validatorData
    # (list of unions).
    if depth > BUFF_SELECTOR_MAX_NESTED_DEPTH:
        raise ValueError(f"{field_name}:selector-depth-exceeded")
    present, offset = read_buff_selector_object_header(data, offset, limit, 3, field_name)
    if not present:
        return None, offset
    finder, offset = read_buff_selector_union(
        data, offset, limit, BUFF_SELECTOR_FINDER_SUBTYPES, "finder",
        f"{field_name}.finderData", depth,
    )
    post_processors, offset = read_buff_selector_list(
        data, offset, limit, f"{field_name}.postProcessorData",
        lambda d, o, l, n: read_buff_selector_union(
            d, o, l, BUFF_SELECTOR_POSTPROCESSOR_SUBTYPES, "postProcessor", n, depth,
        ),
    )
    validators, offset = read_buff_selector_list(
        data, offset, limit, f"{field_name}.validatorData",
        lambda d, o, l, n: read_buff_selector_union(
            d, o, l, BUFF_SELECTOR_VALIDATOR_SUBTYPES, "validator", n, depth,
        ),
    )
    return {
        "finderData": finder,
        "postProcessorData": post_processors,
        "validatorData": validators,
    }, offset


def read_buff_target_settings_full(
    data: bytes,
    offset: int,
    limit: int,
    field_name: str,
    depth: int,
) -> tuple[dict[str, Any] | None, int]:
    # Beyond.Gameplay.Core.TargetSettings, 13 serialized members, alphabetical
    # (static Default excluded).
    if depth > BUFF_SELECTOR_MAX_NESTED_DEPTH:
        raise ValueError(f"{field_name}:selector-depth-exceeded")
    present, offset = read_buff_selector_object_header(data, offset, limit, 13, field_name)
    if not present:
        return None, offset
    out: dict[str, Any] = {}
    out["advancedDirection"], offset = read_buff_direction_settings_full(
        data, offset, limit, f"{field_name}.advancedDirection", depth + 1,
    )
    out["centerContextKey"], offset = read_buff_memorypack_utf8_string_strict_bounded(
        data, offset, limit, f"{field_name}.centerContextKey", max_length=256,
    )
    out["centerToGround"], offset = read_buff_selector_bool(
        data, offset, limit, f"{field_name}.centerToGround",
    )
    out["centerType"], offset = read_buff_selector_i32(
        data, offset, limit, f"{field_name}.centerType",
    )
    out["enableAdvancedDirection"], offset = read_buff_selector_bool(
        data, offset, limit, f"{field_name}.enableAdvancedDirection",
    )
    out["ownerContextKey"], offset = read_buff_memorypack_utf8_string_strict_bounded(
        data, offset, limit, f"{field_name}.ownerContextKey", max_length=256,
    )
    out["selectorData"], offset = read_buff_selector_data_full(
        data, offset, limit, f"{field_name}.selectorData", depth + 1,
    )
    out["selectorDirection"], offset = read_buff_selector_i32(
        data, offset, limit, f"{field_name}.selectorDirection",
    )
    out["selectorOwner"], offset = read_buff_selector_i32(
        data, offset, limit, f"{field_name}.selectorOwner",
    )
    out["target"], offset = read_buff_selector_i32(
        data, offset, limit, f"{field_name}.target",
    )
    out["targetContextKey"], offset = read_buff_memorypack_utf8_string_strict_bounded(
        data, offset, limit, f"{field_name}.targetContextKey", max_length=256,
    )
    out["targetGroupKey"], offset = read_buff_memorypack_utf8_string_strict_bounded(
        data, offset, limit, f"{field_name}.targetGroupKey", max_length=256,
    )
    out["targetSource"], offset = read_buff_selector_i32(
        data, offset, limit, f"{field_name}.targetSource",
    )
    return out, offset


def read_buff_target_settings_full_or_partial(
    data: bytes,
    offset: int,
    max_limit: int,
    field_name: str,
) -> tuple[dict[str, Any], int]:
    """Decode a TargetSettings object when its typed body lands exactly.

    The envelope length is independently derived from the current bounded
    MemoryPack bytes.  The typed reader is accepted only when it consumes that
    exact envelope; otherwise the pre-existing opaque representation is
    returned.  This keeps future/unknown selector subtypes fail-closed while
    exposing the proven TargetSettings fields for the current build.
    """
    envelope_end = buff_target_settings_envelope_limit(
        data, offset, max_limit, field_name,
    )
    partial, _ = read_buff_target_settings_partial(
        data, offset, envelope_end, field_name,
    )
    try:
        decoded, decoded_end = read_buff_target_settings_full(
            data, offset, envelope_end, field_name, 0,
        )
    except (IndexError, UnicodeDecodeError, ValueError, struct.error):
        return partial, envelope_end
    if decoded_end != envelope_end or decoded is None:
        return partial, envelope_end

    # Preserve the bounded raw evidence and the string/tail diagnostics from
    # the partial reader alongside the typed fields.  Consumers can therefore
    # distinguish exact field recovery from a merely recognized envelope.
    return {
        **partial,
        **decoded,
        "status": "exact",
        "semanticStatus": "exact-target-settings-selector-data",
        "schemaSource": BUFF_SELECTOR_SCHEMA_SOURCE_NOTE,
    }, envelope_end


def read_buff_direction_settings_full(
    data: bytes,
    offset: int,
    limit: int,
    field_name: str,
    depth: int,
) -> tuple[dict[str, Any] | None, int]:
    # Beyond.Gameplay.Core.DirectionSettings, 8 serialized members, alphabetical.
    if depth > BUFF_SELECTOR_MAX_NESTED_DEPTH:
        raise ValueError(f"{field_name}:selector-depth-exceeded")
    present, offset = read_buff_selector_object_header(data, offset, limit, 8, field_name)
    if not present:
        return None, offset
    out: dict[str, Any] = {}
    out["clampToXZ"], offset = read_buff_selector_bool(
        data, offset, limit, f"{field_name}.clampToXZ",
    )
    out["customSourceAndTarget"], offset = read_buff_selector_bool(
        data, offset, limit, f"{field_name}.customSourceAndTarget",
    )
    out["directionType"], offset = read_buff_selector_i32(
        data, offset, limit, f"{field_name}.directionType",
    )
    out["invertDirection"], offset = read_buff_selector_bool(
        data, offset, limit, f"{field_name}.invertDirection",
    )
    out["source"], offset = read_buff_target_settings_full(
        data, offset, limit, f"{field_name}.source", depth + 1,
    )
    out["sourceMountPoint"], offset = read_buff_selector_i32(
        data, offset, limit, f"{field_name}.sourceMountPoint",
    )
    out["target"], offset = read_buff_target_settings_full(
        data, offset, limit, f"{field_name}.target", depth + 1,
    )
    out["targetMountPoint"], offset = read_buff_selector_i32(
        data, offset, limit, f"{field_name}.targetMountPoint",
    )
    return out, offset


def read_buff_selector_member(
    data: bytes,
    offset: int,
    limit: int,
    kind: str,
    field_name: str,
    depth: int,
) -> tuple[Any, int]:
    if kind == "bool":
        return read_buff_selector_bool(data, offset, limit, field_name)
    if kind == "i32":
        return read_buff_selector_i32(data, offset, limit, field_name)
    if kind == "f32":
        return read_buff_selector_f32(data, offset, limit, field_name)
    if kind == "f64":
        return read_buff_selector_f64(data, offset, limit, field_name)
    if kind == "vector3":
        if offset + 12 > limit:
            raise ValueError(f"{field_name}:truncated-vector3")
        return list(struct.unpack_from("<fff", data, offset)), offset + 12
    if kind == "quaternion":
        if offset + 16 > limit:
            raise ValueError(f"{field_name}:truncated-quaternion")
        return list(struct.unpack_from("<ffff", data, offset)), offset + 16
    if kind == "string":
        return read_buff_memorypack_utf8_string_strict_bounded(
            data, offset, limit, field_name, max_length=512,
        )
    if kind == "bbparam":
        return read_buff_selector_blackboard_param(data, offset, limit, field_name)
    if kind == "bbvector3":
        return read_buff_selector_blackboard_vector3(data, offset, limit, field_name)
    if kind == "tagquery":
        return read_buff_selector_tag_query(data, offset, limit, field_name)
    if kind == "smarttargetselectsetting":
        return read_buff_selector_smart_target_select_setting(data, offset, limit, field_name)
    if kind == "shapedatalist":
        return read_buff_selector_list(
            data, offset, limit, field_name,
            lambda d, o, l, n: read_buff_selector_shape_data(d, o, l, n),
        )
    if kind == "targetsettings":
        return read_buff_target_settings_full(data, offset, limit, field_name, depth + 1)
    if kind == "selectordata":
        return read_buff_selector_data_full(data, offset, limit, field_name, depth + 1)
    if kind == "directionsettings":
        return read_buff_direction_settings_full(data, offset, limit, field_name, depth + 1)
    raise ValueError(f"{field_name}:unknown-member-kind={kind}")


BUFF_CONTINUOUS_FIND_TARGET_ACTION_TAG = 0x007C


BUFF_FIND_TARGET_ACTION_VARIANTS = {
    # tag -> (member count, has trailing findInterval float)
    BUFF_FIND_TARGET_ACTION_TAG: (18, False),
    BUFF_CONTINUOUS_FIND_TARGET_ACTION_TAG: (19, True),
}


def read_buff_find_target_action_item_exact_forward(
    data: bytes,
    item_start: int,
    limit: int,
    tag_width: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    """Fully parse one (Continuous)FindTargetAction item forward; self-delimiting.

    Raises on any layout violation or unproven selector subtype so callers fail
    closed (chain walkers keep records ambiguous; single-item callers fall back
    to the older partial decoder).
    """
    tag, actual_tag_width, _raw = read_buff_timeline_first_union_tag(data, item_start, limit)
    variant = BUFF_FIND_TARGET_ACTION_VARIANTS.get(tag if tag is not None else -1)
    if variant is None or actual_tag_width != tag_width:
        raise ValueError("findTargetAction:tag-mismatch")
    if tag_width != 1:
        raise ValueError(f"findTargetAction:tag-width={tag_width}")
    expected_member_count, has_find_interval = variant
    if member_count != expected_member_count:
        raise ValueError(f"findTargetAction:member-count={member_count}")
    offset = item_start + tag_width + 1
    prefix, offset = read_buff_ability_action_common_prefix_bounded(
        data, offset, limit, "findTargetAction.prefix",
    )
    body: dict[str, Any] = {}
    for field_key, kind in BUFF_FIND_TARGET_BODY_MEMBERS:
        body[field_key], offset = read_buff_selector_member(
            data, offset, limit, kind, f"findTargetAction.body.{field_key}", 0,
        )
    if has_find_interval:
        body["findInterval"], offset = read_buff_selector_f32(
            data, offset, limit, "findTargetAction.body.findInterval",
        )
    decoded = {
        "type": BUFF_ABILITY_ACTION_TAG_NAMES[tag],
        "decodeStatus": "exact",
        "semanticStatus": "exact-selector-data-full",
        "schemaSource": BUFF_SELECTOR_SCHEMA_SOURCE_NOTE,
        "byteLength": offset - item_start,
        "prefix": prefix,
        **body,
    }
    return decoded, offset


def consume_buff_find_target_action(
    data: bytes,
    item_start: int,
    limit: int,
    tag_width: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    decoded, end = read_buff_find_target_action_item_exact_forward(
        data, item_start, limit, tag_width, member_count,
    )
    if end > limit:
        raise ValueError(f"findTargetAction:consumed-past-limit={format_offset(end)}")
    return decoded, end


def decode_buff_find_target_action_item_full_or_partial(
    data: bytes,
    item_start: int,
    item_end: int,
    tag_width: int,
    member_count: int,
) -> dict[str, Any]:
    """Single-item decode: full byte-proven parse when it lands exactly on the
    proven item end, otherwise the previous fail-closed partial decoder."""
    try:
        decoded, end = read_buff_find_target_action_item_exact_forward(
            data, item_start, item_end, tag_width, member_count,
        )
    except (struct.error, UnicodeDecodeError, ValueError):
        decoded, end = None, -1
    if decoded is not None and end == item_end:
        return decoded
    return decode_buff_find_target_action_item_partial(
        data, item_start, item_end, tag_width, member_count,
    )


def decode_buff_continuous_find_target_action_item_full(
    data: bytes,
    item_start: int,
    item_end: int,
    tag_width: int,
    member_count: int,
) -> dict[str, Any] | None:
    """Single-item exact decode for ContinuousFindTargetAction; None keeps the
    item opaque when the full parse does not land exactly on the proven end."""
    try:
        decoded, end = read_buff_find_target_action_item_exact_forward(
            data, item_start, item_end, tag_width, member_count,
        )
    except (struct.error, UnicodeDecodeError, ValueError):
        return None
    if end != item_end:
        return None
    return decoded


def decode_buff_find_target_action_item_partial(
    data: bytes,
    item_start: int,
    item_end: int,
    tag_width: int,
    member_count: int,
) -> dict[str, Any]:
    tag, actual_tag_width, _raw = read_buff_timeline_first_union_tag(data, item_start, item_end)
    if tag != BUFF_FIND_TARGET_ACTION_TAG or actual_tag_width != tag_width:
        raise ValueError("findTargetAction:tag-mismatch")
    if tag_width != 1:
        raise ValueError(f"findTargetAction:tag-width={tag_width}")
    if member_count != 18:
        raise ValueError(f"findTargetAction:member-count={member_count}")
    offset = item_start + tag_width + 1
    if offset + 13 > item_end:
        raise ValueError("findTargetAction.prefix:truncated")
    prefix, offset = read_buff_ability_action_common_prefix_bounded(
        data,
        offset,
        item_end,
        "findTargetAction.prefix",
    )
    if offset > item_end:
        raise ValueError(f"findTargetAction.prefix:past-end={format_offset(offset)}")
    body_raw = data[offset:item_end]
    if not body_raw:
        raise ValueError("findTargetAction.opaqueBody:empty")
    if len(body_raw) > BUFF_FIND_TARGET_OPAQUE_BODY_MAX_BYTES:
        raise ValueError(f"findTargetAction.opaqueBody:bytes={len(body_raw)}")
    find_target_body = read_buff_find_target_body_partial(
        data,
        offset,
        item_end,
        "findTargetAction.body",
    )
    return {
        "type": BUFF_ABILITY_ACTION_TAG_NAMES[BUFF_FIND_TARGET_ACTION_TAG],
        "decodeStatus": "partial",
        "semanticStatus": "partial-find-target-direction-tail-fields",
        "schemaSource": (
            "IL2CPP field names and generated MemoryPack wrapper methods are known for "
            "FindTargetActionData, but selectorData and TargetSettings boundaries are still "
            "not self-delimiting in the current parser. Only the common AbilityActionData "
            "prefix is decoded; target settings, selectorData, selectorDirection, and "
            "target/context fields remain an opaque bounded body."
        ),
        "byteLength": item_end - item_start,
        "prefix": prefix,
        **find_target_body,
        "declaredFieldOrderSource": "Beyond.Gameplay.Core.FindTargetAction+FindTargetActionData IL2CPP field token order; wrapper type Beyond_Gameplay_Core_FindTargetAction_FindTargetActionDataForMemoryPack exists",
        "declaredFieldOrder": [
            "targetGroupKey",
            "center",
            "centerContextKey",
            "useCenterEntityMountPoint",
            "centerMountPoint",
            "centerToGround",
            "selectorOwner",
            "selectorOwnerContextKey",
            "selectorData",
            "selectorDirection",
            "target",
            "contextKey",
            "useAdvancedDirectionSetting",
            "advancedSelectorDirection",
        ],
        "opaqueBody": {
            "status": "partial",
            "semanticStatus": "partial-find-target-direction-tail-fields",
            "offset": format_offset(offset),
            "bytes": len(body_raw),
            "memberCountCandidate": body_raw[0] if body_raw else None,
            "rawSha256": hashlib.sha256(body_raw).hexdigest(),
            "prefixHex": body_raw[:64].hex(" "),
            "tailHex": body_raw[-64:].hex(" "),
            "stringHits": scan_length_prefixed_utf8_string_hits(
                body_raw,
                start=0,
                max_scan_bytes=len(body_raw),
                max_samples=12,
                max_length=256,
            ),
        },
    }


def read_buff_damage_hit_env_and_environment_partial(
    data: bytes,
    offset: int,
    limit: int,
    field_name: str,
) -> tuple[dict[str, Any], int]:
    start = offset
    if offset >= limit:
        raise ValueError(f"{field_name}:truncated-member-count")
    member_count = data[offset]
    offset += 1
    if member_count != 4:
        raise ValueError(f"{field_name}:member-count={member_count}")
    fixed_end = offset + len(BUFF_DAMAGE_HIT_ENV_FIXED_PREFIX)
    if fixed_end > limit:
        raise ValueError(f"{field_name}:truncated-fixed-prefix")
    fixed_prefix = data[offset:fixed_end]
    if fixed_prefix != BUFF_DAMAGE_HIT_ENV_FIXED_PREFIX:
        raise ValueError(f"{field_name}:fixed-prefix={fixed_prefix.hex(' ')}")
    offset = fixed_end
    value_a, offset = read_buff_blackboard_float_raw_field_bounded(
        data,
        offset,
        limit,
        f"{field_name}.blackboardFloat0",
    )
    value_b, offset = read_buff_blackboard_float_raw_field_bounded(
        data,
        offset,
        limit,
        f"{field_name}.blackboardFloat1",
    )
    hit_environment, offset = read_buff_bool_field_bounded(
        data,
        offset,
        limit,
        f"{field_name}.hitEnvironment",
    )
    if offset != limit:
        raise ValueError(f"{field_name}:tail-at={format_offset(offset)} limit={format_offset(limit)}")
    return {
        "status": "partial",
        "semanticStatus": "partial-hit-env-data-field-names-unproven",
        "offset": format_offset(start),
        "bytes": offset - start,
        "memberCount": member_count,
        "fixedPrefixRaw": fixed_prefix.hex(" "),
        "blackboardFloat0": value_a,
        "blackboardFloat1": value_b,
        "hitEnvironment": hit_environment,
    }, offset


def find_damage_action_target_tail_candidates(
    data: bytes,
    search_start: int,
    item_end: int,
    *,
    require_second_end: int | None = None,
) -> list[tuple[int, dict[str, Any], int, dict[str, Any], int, dict[str, Any], int]]:
    candidates: list[tuple[int, dict[str, Any], int, dict[str, Any], int, dict[str, Any], int]] = []
    for first_start in range(search_start, item_end):
        first = try_read_buff_target_settings_envelope_partial(
            data,
            first_start,
            item_end,
            "damageAction.effectSource",
        )
        if first is None:
            continue
        effect_source, first_end = first
        for second_start in range(first_end, item_end):
            gap_bytes = second_start - first_end
            if gap_bytes > BUFF_DAMAGE_HIT_ENV_MAX_BYTES:
                break
            try:
                hit_env, _hit_env_end = read_buff_damage_hit_env_and_environment_partial(
                    data,
                    first_end,
                    second_start,
                    "damageAction.hitEnvDataAndHitEnvironment",
                )
            except (struct.error, UnicodeDecodeError, ValueError):
                continue
            second = try_read_buff_target_settings_envelope_partial(
                data,
                second_start,
                item_end,
                "damageAction.targetSettings",
            )
            if second is None:
                continue
            target_settings, second_end = second
            if require_second_end is None or second_end == require_second_end:
                candidates.append((
                    first_start,
                    effect_source,
                    first_end,
                    hit_env,
                    second_start,
                    target_settings,
                    second_end,
                ))
                if len(candidates) > 1:
                    return candidates
    return candidates


def decode_buff_damage_action_item_partial(
    data: bytes,
    item_start: int,
    item_end: int,
    tag_width: int,
    member_count: int,
    *,
    require_exact_end: bool = True,
) -> tuple[dict[str, Any] | None, str]:
    tag, actual_tag_width, _raw = read_buff_timeline_first_union_tag(data, item_start, item_end)
    if tag != BUFF_DAMAGE_ACTION_TAG or actual_tag_width != tag_width:
        return None, "damageAction:tag-mismatch"
    if tag_width != 1:
        return None, f"damageAction:tag-width={tag_width}"
    if member_count != 11:
        return None, f"damageAction:member-count={member_count}"
    offset = item_start + tag_width + 1
    if offset + 13 > item_end:
        return None, "damageAction.prefix:truncated"
    try:
        prefix, offset = read_buff_ability_action_common_prefix_bounded(
        data,
        offset,
        item_end,
        "damageAction.prefix",
    )
        always_next, offset = read_buff_bool_field_bounded(
            data,
            offset,
            item_end,
            "damageAction.alwaysNext",
        )
        attacker, offset = read_buff_i32_field_bounded(
            data,
            offset,
            item_end,
            "damageAction.attacker",
        )
        if attacker < 0 or attacker > 256:
            return None, f"damageAction.attacker={attacker}"
        damage_unit_count, offset = read_buff_u32_field_bounded(
            data,
            offset,
            item_end,
            "damageAction.damageUnits.count",
        )
    except (struct.error, UnicodeDecodeError, ValueError) as exc:
        return None, str(exc)[:160]
    if damage_unit_count <= 0 or damage_unit_count > BUFF_DAMAGE_MAX_UNITS:
        return None, f"damageAction.damageUnits.count={damage_unit_count}"
    if offset != item_start + 0x18:
        return None, f"damageAction.damageUnits.offset={format_offset(offset)}"
    if offset >= item_end or data[offset] != BUFF_DAMAGE_UNIT_MEMBER_COUNT:
        found = "eof" if offset >= item_end else f"0x{data[offset]:02x}"
        return None, f"damageAction.damageUnits[0].memberCount={found}"

    min_tail_search = offset + damage_unit_count * BUFF_DAMAGE_UNIT_MIN_OPAQUE_BYTES
    if min_tail_search >= item_end:
        return None, "damageAction.damageUnits:too-short"
    candidates = find_damage_action_target_tail_candidates(
        data,
        min_tail_search,
        item_end,
        require_second_end=item_end if require_exact_end else None,
    )
    if not candidates:
        return None, "damageAction.targetTail:no-exact-hit-env-target-settings-chain"
    if len(candidates) != 1:
        return None, "damageAction.targetTail:ambiguous-hit-env-target-settings-chains"

    (
        effect_source_start,
        effect_source,
        _effect_source_end,
        hit_env,
        _target_start,
        target_settings,
        target_end,
    ) = candidates[0]
    damage_units_raw = data[offset:effect_source_start]
    return {
        "type": BUFF_ABILITY_ACTION_TAG_NAMES[BUFF_DAMAGE_ACTION_TAG],
        "decodeStatus": "partial",
        "semanticStatus": "partial-damage-units-opaque-hit-env-bounded",
        "schemaSource": (
            "IL2CPP field names plus byte-proven boundary: AbilityActionData prefix, alwaysNext, "
            "attacker, counted opaque DamageUnit list, effectSource TargetSettings, bounded "
            "HitEnvData/hitEnvironment span, targetSettings. DamageUnit internals remain opaque."
        ),
        "byteLength": target_end - item_start,
        "prefix": prefix,
        "alwaysNext": always_next,
        "attacker": attacker,
        "damageUnits": {
            "status": "partial",
            "semanticStatus": "partial-damage-unit-list-opaque",
            "offset": format_offset(offset),
            "bytes": len(damage_units_raw),
            "count": damage_unit_count,
            "minBytesPerDeclaredUnit": BUFF_DAMAGE_UNIT_MIN_OPAQUE_BYTES,
            "firstMemberCount": data[offset],
            "rawSha256": hashlib.sha256(damage_units_raw).hexdigest(),
            "stringHits": scan_length_prefixed_utf8_string_hits(
                damage_units_raw,
                start=0,
                max_scan_bytes=len(damage_units_raw),
                max_samples=8,
                max_length=256,
            ),
            "prefixHex": damage_units_raw[:48].hex(" "),
            "tailHex": damage_units_raw[-48:].hex(" "),
        },
        "effectSourceEnvelopePartial": effect_source,
        "hitEnvDataAndHitEnvironmentPartial": hit_env,
        "targetSettingsEnvelopePartial": target_settings,
    }, ""


def consume_buff_damage_action(
    data: bytes,
    item_start: int,
    limit: int,
    tag_width: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    decoded, probe_note = decode_buff_damage_action_item_partial(
        data,
        item_start,
        limit,
        tag_width,
        member_count,
        require_exact_end=False,
    )
    if decoded is None:
        raise ValueError(probe_note or "damageAction:decode-failed")
    byte_length = decoded.get("byteLength")
    if not isinstance(byte_length, int) or byte_length <= 0:
        raise ValueError("damageAction:missing-byte-length")
    return decoded, item_start + byte_length


def decode_buff_ability_action_item_exact(
    data: bytes,
    item_start: int,
    item_end: int,
    tag: int,
    tag_width: int,
    member_count: int,
) -> dict[str, Any] | None:
    if tag == BUFF_CAMERA_IMPULSE_ACTION_TAG:
        return decode_buff_camera_impulse_action(
            data,
            item_start,
            item_end,
            tag_width,
            member_count,
        )
    if tag == BUFF_FIND_TARGET_ACTION_TAG:
        return decode_buff_find_target_action_item_full_or_partial(
            data,
            item_start,
            item_end,
            tag_width,
            member_count,
        )
    if tag == BUFF_CONTINUOUS_FIND_TARGET_ACTION_TAG:
        return decode_buff_continuous_find_target_action_item_full(
            data,
            item_start,
            item_end,
            tag_width,
            member_count,
        )
    if tag == BUFF_CREATE_BUFF_ACTION_TAG:
        return decode_buff_create_buff_action(
            data,
            item_start,
            item_end,
            tag_width,
            member_count,
        )
    if tag == BUFF_MODIFY_DYNAMIC_BLACKBOARD_ACTION_TAG:
        return decode_buff_modify_dynamic_blackboard_action(
            data,
            item_start,
            item_end,
            tag_width,
            member_count,
        )
    if tag == BUFF_EFFECT_ACTION_TAG:
        return decode_buff_effect_action(
            data,
            item_start,
            item_end,
            tag_width,
            member_count,
        )
    if tag == BUFF_DEBUG_PRINT_ACTION_TAG:
        return decode_buff_debug_print_action(
            data,
            item_start,
            item_end,
            tag_width,
            member_count,
        )
    if tag == BUFF_CONVERT_TO_TARGET_CONTEXT_ACTION_TAG:
        return decode_buff_convert_to_target_context_action(
            data,
            item_start,
            item_end,
            tag_width,
            member_count,
        )
    if tag == BUFF_SEND_BATTLE_SIGNAL_TO_LEVEL_TAG:
        return decode_buff_send_battle_signal_to_level_action(
            data,
            item_start,
            item_end,
            tag_width,
            member_count,
        )
    if tag == BUFF_PLAY_SOUND_ACTION_TAG:
        return decode_buff_play_sound_action(
            data,
            item_start,
            item_end,
            tag_width,
            member_count,
        )
    if tag == BUFF_PATROL_TELEPORT_ACTION_TAG:
        return decode_buff_patrol_teleport_action(
            data,
            item_start,
            item_end,
            tag_width,
            member_count,
        )
    if tag == BUFF_PLAY_ANIMATION_ACTION_TAG:
        return decode_buff_play_animation_action(
            data,
            item_start,
            item_end,
            tag_width,
            member_count,
        )
    if tag in BUFF_ABILITY_ACTION_BEST_EFFORT_SINGLE_ITEM_TAGS:
        decoded, _best_effort_error = decode_buff_best_effort_single_action_item(
            data,
            item_start,
            item_end,
            tag,
            tag_width,
            member_count,
        )
        return decoded
    return None


def read_buff_ability_action_item_header(
    data: bytes,
    offset: int,
    limit: int,
) -> tuple[int, int, int] | None:
    tag, tag_width, _raw = read_buff_timeline_first_union_tag(data, offset, limit)
    if tag is None or tag not in BUFF_ABILITY_ACTION_TAG_NAMES:
        return None
    member_count_offset = offset + tag_width
    if member_count_offset >= limit:
        return None
    member_count = data[member_count_offset]
    expected_member_count = BUFF_ABILITY_ACTION_TAG_MEMBER_COUNTS.get(tag)
    if expected_member_count is None or member_count != expected_member_count:
        return None
    return tag, tag_width, member_count


def build_buff_ability_action_item_summary(
    data: bytes,
    item_start: int,
    item_end: int,
    tag: int,
    tag_width: int,
    member_count: int,
    index: int,
) -> dict[str, Any]:
    item_bytes = item_end - item_start
    string_hits = scan_length_prefixed_utf8_string_hits(
        data,
        start=item_start,
        max_scan_bytes=item_bytes,
        max_samples=4,
        max_length=128,
    )
    summary: dict[str, Any] = {
        "index": index,
        "offset": format_offset(item_start),
        "bytes": item_bytes,
        "tag": f"0x{tag:04x}",
        "name": BUFF_ABILITY_ACTION_TAG_NAMES.get(tag, ""),
        "tagBytes": tag_width,
        "memberCount": member_count,
        "bodyBytes": item_bytes - tag_width - 1,
        "decodeStatus": "opaque",
        "stringHits": string_hits,
    }
    if tag == BUFF_DAMAGE_ACTION_TAG:
        decoded, probe_note = decode_buff_damage_action_item_partial(
            data,
            item_start,
            item_end,
            tag_width,
            member_count,
        )
        if decoded is not None:
            summary["decodeStatus"] = str(decoded.get("decodeStatus") or "partial")
            summary["decoded"] = decoded
        elif probe_note:
            summary["damageActionProbeNote"] = probe_note
        return summary

    try:
        decoded = decode_buff_ability_action_item_exact(
            data,
            item_start,
            item_end,
            tag,
            tag_width,
            member_count,
        )
    except (struct.error, UnicodeDecodeError, ValueError) as exc:
        summary["decodeStatus"] = "typed-decoder-failed"
        summary["decodeError"] = str(exc)[:200]
    else:
        if decoded is not None:
            summary["decodeStatus"] = str(decoded.get("decodeStatus") or "exact")
            summary["decoded"] = decoded
        elif tag in BUFF_ABILITY_ACTION_BEST_EFFORT_SINGLE_ITEM_TAGS:
            _best_effort_decoded, best_effort_error = decode_buff_best_effort_single_action_item(
                data,
                item_start,
                item_end,
                tag,
                tag_width,
                member_count,
            )
            if best_effort_error:
                summary["bestEffortDecodeProbeNote"] = best_effort_error
    return summary


def build_buff_consumed_action_item_summary(
    data: bytes,
    item_start: int,
    item_end: int,
    tag: int,
    tag_width: int,
    member_count: int,
    index: int,
    decoded: dict[str, Any],
) -> dict[str, Any]:
    item_bytes = item_end - item_start
    string_hits = scan_length_prefixed_utf8_string_hits(
        data,
        start=item_start,
        max_scan_bytes=item_bytes,
        max_samples=4,
        max_length=128,
    )
    return {
        "index": index,
        "offset": format_offset(item_start),
        "bytes": item_bytes,
        "tag": f"0x{tag:04x}",
        "name": BUFF_ABILITY_ACTION_TAG_NAMES.get(tag, ""),
        "tagBytes": tag_width,
        "memberCount": member_count,
        "bodyBytes": item_bytes - tag_width - 1,
        "decodeStatus": str(decoded.get("decodeStatus") or "exact"),
        "boundaryProof": "typed-consumption",
        "stringHits": string_hits,
        "decoded": decoded,
    }


def consume_buff_ability_action_item(
    data: bytes,
    offset: int,
    limit: int,
    index: int = 0,
    depth: int = 0,
) -> tuple[dict[str, Any], int]:
    """Consume exactly one AbilityActionData union item with a typed decoder.

    Boundaries come from full typed consumption only: the item type must have
    a consume-style decoder that deterministically parses forward from the
    item start. Unknown tags, unknown member counts, or any typed parse
    failure raise, so callers keep the enclosing payload opaque (never
    header-only splitting).
    """
    if depth > BUFF_ABILITY_ACTION_MAX_NESTED_DEPTH:
        raise ValueError("abilityActionItem:nested-depth-exceeded")
    header = read_buff_ability_action_item_header(data, offset, limit)
    if header is None:
        tag, _tag_width, _raw = read_buff_timeline_first_union_tag(data, offset, limit)
        tag_text = "none" if tag is None else f"0x{tag:04x}"
        raise ValueError(f"abilityActionItem:unknown-header-tag={tag_text}")
    tag, tag_width, member_count = header
    consumer = BUFF_ABILITY_ACTION_CONSUME_DECODERS.get(tag)
    if consumer is None:
        name = BUFF_ABILITY_ACTION_TAG_NAMES.get(tag, f"0x{tag:04x}")
        raise ValueError(f"abilityActionItem:no-typed-consumer={name}")
    if tag == BUFF_IF_ELSE_ACTION_TAG:
        decoded, end = consumer(data, offset, limit, tag_width, member_count, depth)
    else:
        decoded, end = consumer(data, offset, limit, tag_width, member_count)
    if end > limit:
        raise ValueError(f"abilityActionItem:consumed-past-limit={format_offset(end)}")
    summary = build_buff_consumed_action_item_summary(
        data,
        offset,
        end,
        tag,
        tag_width,
        member_count,
        index,
        decoded,
    )
    return summary, end


def consume_buff_sequence_action_data(
    data: bytes,
    offset: int,
    limit: int,
    field_name: str,
    depth: int,
) -> tuple[dict[str, Any], int]:
    start = offset
    if offset >= limit or data[offset] != BUFF_SEQUENCE_ACTION_DATA_MEMBER_COUNT:
        raise ValueError(f"{field_name}:sequence-member-count")
    offset += 1
    count, offset = read_buff_u32_field(data, offset, f"{field_name}.actionDataCount")
    if count > 64:
        raise ValueError(f"{field_name}.actionDataCount={count}")
    items: list[dict[str, Any]] = []
    for index in range(count):
        summary, offset = consume_buff_ability_action_item(
            data,
            offset,
            limit,
            index,
            depth + 1,
        )
        items.append(summary)
    only_guard, offset = read_buff_bool_field(
        data,
        offset,
        f"{field_name}.onlyExecuteWhenSourceIsGuard",
    )
    only_main_char, offset = read_buff_bool_field(
        data,
        offset,
        f"{field_name}.onlyExecuteWhenSourceIsMainChar",
    )
    return {
        "memberCount": BUFF_SEQUENCE_ACTION_DATA_MEMBER_COUNT,
        "offset": format_offset(start),
        "bytes": offset - start,
        "actionDataCount": count,
        "actionDataItems": items,
        "onlyExecuteWhenSourceIsGuard": only_guard,
        "onlyExecuteWhenSourceIsMainChar": only_main_char,
    }, offset


def consume_buff_if_else_action(
    data: bytes,
    item_start: int,
    limit: int,
    tag_width: int,
    member_count: int,
    depth: int = 0,
) -> tuple[dict[str, Any], int]:
    tag, actual_tag_width, _raw = read_buff_timeline_first_union_tag(data, item_start, limit)
    if tag != BUFF_IF_ELSE_ACTION_TAG or actual_tag_width != tag_width:
        raise ValueError("ifElseAction:tag-mismatch")
    if tag_width != 1:
        raise ValueError(f"ifElseAction:tag-width={tag_width}")
    if member_count != 8:
        raise ValueError(f"ifElseAction:member-count={member_count}")
    offset = item_start + tag_width + 1
    prefix, offset = read_buff_ability_action_common_prefix_bounded(
        data,
        offset,
        limit,
        "ifElseAction.prefix",
    )
    always_next, offset = read_buff_bool_field(data, offset, "ifElseAction.alwaysNext")
    condition_action, offset = consume_buff_sequence_action_data(
        data,
        offset,
        limit,
        "ifElseAction.conditionAction",
        depth,
    )
    fail_actions, offset = consume_buff_sequence_action_data(
        data,
        offset,
        limit,
        "ifElseAction.failActions",
        depth,
    )
    succeed_actions, offset = consume_buff_sequence_action_data(
        data,
        offset,
        limit,
        "ifElseAction.succeedActions",
        depth,
    )
    return {
        "type": BUFF_ABILITY_ACTION_TAG_NAMES[BUFF_IF_ELSE_ACTION_TAG],
        "decodeStatus": "partial",
        "semanticStatus": "partial-nested-action-payloads-and-target-settings-opaque",
        "schemaSource": (
            "MemoryPack setter order: AbilityActionData prefix, alwaysNext, conditionAction, "
            "failActions, succeedActions; each branch is a SequenceActionData envelope "
            "(memberCount=3, counted AbilityActionData union items, guard/main-char bools) and "
            "splits only when every nested item is fully typed-consumed; branch-list naming "
            "follows setter order"
        ),
        "byteLength": offset - item_start,
        "prefix": prefix,
        "alwaysNext": always_next,
        "conditionAction": condition_action,
        "failActions": fail_actions,
        "succeedActions": succeed_actions,
    }, offset


BUFF_ABILITY_ACTION_CONSUME_DECODERS = {
    BUFF_COMPARE_FLOAT_ACTION_TAG: consume_buff_compare_float_action,
    BUFF_CAMERA_IMPULSE_ACTION_TAG: consume_buff_camera_impulse_action,
    BUFF_CONTINUOUS_FIND_TARGET_ACTION_TAG: consume_buff_find_target_action,
    BUFF_CONVERT_TO_TARGET_CONTEXT_ACTION_TAG: consume_buff_convert_to_target_context_action,
    BUFF_CREATE_BUFF_ACTION_TAG: consume_buff_create_buff_action,
    BUFF_DAMAGE_ACTION_TAG: consume_buff_damage_action,
    BUFF_DEBUG_PRINT_ACTION_TAG: consume_buff_debug_print_action,
    BUFF_EFFECT_ACTION_TAG: consume_buff_effect_action,
    BUFF_FIND_TARGET_ACTION_TAG: consume_buff_find_target_action,
    BUFF_GET_AI_TRANS_DATA_ACTION_TAG: consume_buff_get_ai_trans_data_action,
    BUFF_IF_ELSE_ACTION_TAG: consume_buff_if_else_action,
    BUFF_INTERRUPT_ACTION_TAG: consume_buff_interrupt_action,
    BUFF_MODIFY_DYNAMIC_BLACKBOARD_ACTION_TAG: consume_buff_modify_dynamic_blackboard_action,
    BUFF_PATROL_TELEPORT_ACTION_TAG: consume_buff_patrol_teleport_action,
    BUFF_PLAY_ANIMATION_ACTION_TAG: consume_buff_play_animation_action,
    BUFF_PLAY_SOUND_ACTION_TAG: consume_buff_play_sound_action,
    BUFF_SEND_BATTLE_SIGNAL_TO_LEVEL_TAG: consume_buff_send_battle_signal_to_level_action,
    BUFF_SPELL_INFLICTION_ACTION_TAG: consume_buff_spell_infliction_action,
}


BUFF_ABILITY_ACTION_BEST_EFFORT_SINGLE_ITEM_TAGS = frozenset(
    {
        BUFF_COMPARE_FLOAT_ACTION_TAG,
        BUFF_GET_AI_TRANS_DATA_ACTION_TAG,
        BUFF_IF_ELSE_ACTION_TAG,
        BUFF_INTERRUPT_ACTION_TAG,
        BUFF_SPELL_INFLICTION_ACTION_TAG,
    }
)


def decode_buff_best_effort_single_action_item(
    data: bytes,
    item_start: int,
    item_end: int,
    tag: int,
    tag_width: int,
    member_count: int,
) -> tuple[dict[str, Any] | None, str]:
    """Best-effort single-item decode for the newer consume families.

    Returns `(decoded, "")` on success and `(None, reason)` on failure. A
    failure keeps the item opaque (never `typed-decoder-failed`) because these
    families routinely nest items with no typed consumer yet, but the reason
    is surfaced so real consumer bugs stay distinguishable from missing
    decoders.
    """
    consumer = BUFF_ABILITY_ACTION_CONSUME_DECODERS.get(tag)
    if consumer is None:
        return None, "no-consume-decoder"
    try:
        if tag == BUFF_IF_ELSE_ACTION_TAG:
            decoded, end = consumer(data, item_start, item_end, tag_width, member_count, 0)
        else:
            decoded, end = consumer(data, item_start, item_end, tag_width, member_count)
    except (struct.error, UnicodeDecodeError, ValueError) as exc:
        return None, f"{type(exc).__name__}: {str(exc)[:160]}"
    if end != item_end:
        return None, (
            f"end-mismatch: consumed-to={format_offset(end)} item-end={format_offset(item_end)}"
        )
    return decoded, ""


def split_buff_ability_action_items_opaque(
    data: bytes,
    offset: int,
    body_end: int,
    action_data_count: int,
) -> tuple[str, list[dict[str, Any]], str]:
    if action_data_count == 0:
        return ("empty", [], "") if offset == body_end else ("failed", [], "")
    if action_data_count == 1:
        header = read_buff_ability_action_item_header(data, offset, body_end)
        if header is None:
            return "failed", [], ""
        tag, tag_width, member_count = header
        return "single-item", [
            build_buff_ability_action_item_summary(
                data,
                offset,
                body_end,
                tag,
                tag_width,
                member_count,
                0,
            )
        ], ""
    if action_data_count > 1:
        # Strict full-chain typed consumption: split only when every item is
        # consumed by a typed decoder and the chain lands exactly on the
        # proven payload end. Anything else stays opaque.
        items: list[dict[str, Any]] = []
        cursor = offset
        try:
            for index in range(action_data_count):
                summary, cursor = consume_buff_ability_action_item(
                    data,
                    cursor,
                    body_end,
                    index,
                    0,
                )
                items.append(summary)
        except (struct.error, UnicodeDecodeError, ValueError) as exc:
            return "ambiguous-union-tag-boundaries", [], str(exc)[:160]
        if cursor != body_end:
            return (
                "ambiguous-union-tag-boundaries",
                [],
                f"typed-chain-end-at={format_offset(cursor)} body-end={format_offset(body_end)}",
            )
        return "typed-chain-items", items, ""
    return "failed", [], ""


def short_counter_dict(counter: Counter[Any], limit: int = 16) -> dict[str, int]:
    return {str(key): value for key, value in counter.most_common(limit)}


def decode_buff_timeline_actions_outer(
    data: bytes,
    offset: int,
    action_count: int,
    body_end: int,
) -> dict[str, Any]:
    if action_count <= 0 or action_count > 64:
        raise ValueError(f"timelineActionsCount:unsupported-body-count={action_count}")
    if offset >= body_end or body_end > len(data):
        raise ValueError("timelineActionsBody:invalid-bounds")

    memo: dict[tuple[int, int], list[list[dict[str, Any]]]] = {}
    max_candidates = 2

    def parse_records(record_index: int, cursor: int) -> list[list[dict[str, Any]]]:
        key = (record_index, cursor)
        if key in memo:
            return memo[key]
        if record_index == action_count:
            return [[]] if cursor == body_end else []
        if cursor >= body_end or data[cursor] != 4:
            return []

        record_start = cursor
        cursor += 1
        if cursor + 4 > body_end:
            return []
        end_frame = struct.unpack_from("<i", data, cursor)[0]
        cursor += 4
        if abs(end_frame) > 1_000_000:
            return []

        sequence_start = cursor
        if cursor >= body_end or data[cursor] != 3:
            return []
        cursor += 1
        if cursor + 4 > body_end:
            return []
        action_data_count = struct.unpack_from("<I", data, cursor)[0]
        cursor += 4
        if action_data_count > 64:
            return []
        action_payload_start = cursor

        # Two sequence bools, startFrame i32, then ForceSyncAnimData:
        # memberCount, bool, MemoryPack string length, f32, i32.
        min_after_action_payload = 20
        max_payload_end = body_end - min_after_action_payload
        results: list[list[dict[str, Any]]] = []
        for payload_end in range(action_payload_start, max_payload_end + 1):
            payload_len = payload_end - action_payload_start
            if action_data_count == 0 and payload_len:
                break
            if action_data_count and payload_len <= 0:
                continue
            if data[payload_end] not in (0, 1) or data[payload_end + 1] not in (0, 1):
                continue
            only_guard = bool(data[payload_end])
            only_main_char = bool(data[payload_end + 1])
            start_frame_offset = payload_end + 2
            start_frame = struct.unpack_from("<i", data, start_frame_offset)[0]
            if abs(start_frame) > 1_000_000:
                continue
            force_sync_offset = start_frame_offset + 4
            try:
                force_sync, force_end = read_buff_timeline_force_sync_anim_data(
                    data,
                    force_sync_offset,
                    body_end,
                    f"timelineActions[{record_index}].forceSyncAnimData",
                )
            except (struct.error, UnicodeDecodeError, ValueError):
                continue
            if record_index + 1 < action_count and (force_end >= body_end or data[force_end] != 4):
                continue
            suffixes = parse_records(record_index + 1, force_end)
            if not suffixes:
                continue

            first_tag, first_tag_bytes, first_tag_raw = read_buff_timeline_first_union_tag(
                data,
                action_payload_start,
                payload_end,
            )
            string_hits = scan_length_prefixed_utf8_string_hits(
                data,
                start=action_payload_start,
                max_scan_bytes=payload_len,
                max_samples=6,
                max_length=128,
            )
            action_data_split, action_data_items, action_data_split_note = (
                split_buff_ability_action_items_opaque(
                    data,
                    action_payload_start,
                    payload_end,
                    action_data_count,
                )
            )
            record = {
                "index": record_index,
                "offset": format_offset(record_start),
                "bytes": force_end - record_start,
                "memberCount": 4,
                "startFrame": start_frame,
                "endFrame": end_frame,
                "sequenceActionData": {
                    "memberCount": 3,
                    "offset": format_offset(sequence_start),
                    "actionDataCount": action_data_count,
                    "actionDataOffset": format_offset(action_payload_start),
                    "actionDataBytes": payload_len,
                    "firstActionTag": f"0x{first_tag:04x}" if first_tag is not None else "",
                    "firstActionName": BUFF_ABILITY_ACTION_TAG_NAMES.get(first_tag, "") if first_tag is not None else "",
                    "firstActionTagBytes": first_tag_bytes,
                    "firstActionTagRaw": first_tag_raw,
                    "actionDataSplit": action_data_split,
                    "actionDataItems": action_data_items,
                    "onlyExecuteWhenSourceIsGuard": only_guard,
                    "onlyExecuteWhenSourceIsMainChar": only_main_char,
                    "stringHits": string_hits,
                },
                "forceSyncAnimData": force_sync,
            }
            if action_data_split_note:
                record["sequenceActionData"]["actionDataSplitProbeNote"] = action_data_split_note
            for suffix in suffixes:
                results.append([record, *suffix])
                if len(results) >= max_candidates:
                    memo[key] = results
                    return results

        memo[key] = results
        return results

    candidates = parse_records(0, offset)
    if len(candidates) != 1:
        raise ValueError(f"timelineActionsBody:outer-parse-candidates={len(candidates)}")

    records = candidates[0]
    action_data_count_counts = Counter(
        record["sequenceActionData"]["actionDataCount"] for record in records
    )
    first_tag_counts = Counter(
        record["sequenceActionData"]["firstActionTag"] or "none" for record in records
    )
    first_action_name_counts = Counter(
        record["sequenceActionData"]["firstActionName"] or "unknown" for record in records
    )
    action_data_split_counts = Counter(
        record["sequenceActionData"].get("actionDataSplit") or "unknown" for record in records
    )
    split_action_item_name_counts = Counter(
        item.get("name") or "unknown"
        for record in records
        for item in record["sequenceActionData"].get("actionDataItems") or []
    )
    split_action_item_decode_counts = Counter(
        item.get("decodeStatus") or "unknown"
        for record in records
        for item in record["sequenceActionData"].get("actionDataItems") or []
    )
    exact_action_item_type_counts = Counter(
        (item.get("decoded") or {}).get("type") or "unknown"
        for record in records
        for item in record["sequenceActionData"].get("actionDataItems") or []
        if item.get("decodeStatus") == "exact"
    )
    decoded_action_item_type_counts = Counter(
        (item.get("decoded") or {}).get("type") or "unknown"
        for record in records
        for item in record["sequenceActionData"].get("actionDataItems") or []
        if item.get("decoded")
    )
    return {
        "timelineActionsBodyStatus": "partial-timelineActions-opaque-actionData",
        "timelineActionsBodyShape": (
            "outer TimelineActionData list decoded as memberCount=4, endFrame, "
            "SequenceActionData(memberCount=3, opaque union actionData payloads, guard/main-char bools), "
            "startFrame, and ForceSyncAnimData(memberCount=4)"
        ),
        "timelineActionsSemanticStatus": "partial-inner-actionData-union-payloads-opaque",
        "timelineActionRecordCount": len(records),
        "timelineActionUnionTagSource": BUFF_ABILITY_ACTION_TAG_SOURCE_NOTE,
        "timelineActionDataCountCounts": short_counter_dict(action_data_count_counts),
        "timelineActionFirstTagCounts": short_counter_dict(first_tag_counts),
        "timelineActionFirstActionNameCounts": short_counter_dict(first_action_name_counts),
        "timelineActionDataSplitCounts": short_counter_dict(action_data_split_counts),
        "timelineActionSplitItemNameCounts": short_counter_dict(split_action_item_name_counts),
        "timelineActionItemDecodeStatusCounts": short_counter_dict(split_action_item_decode_counts),
        "timelineActionExactItemTypeCounts": short_counter_dict(exact_action_item_type_counts),
        "timelineActionDecodedItemTypeCounts": short_counter_dict(decoded_action_item_type_counts),
        "timelineActionRecords": records,
    }


def find_buff_timeline_actions_body_end(
    data: bytes,
    offset: int,
    action_count: int,
) -> tuple[int, int]:
    if action_count <= 0 or action_count > 64:
        raise ValueError(f"timelineActionsCount:unsupported-body-count={action_count}")
    if offset >= len(data):
        raise ValueError("timelineActionsBody:truncated")
    body_pattern = data[offset]
    if body_pattern not in (0x03, 0x04):
        raise ValueError(f"timelineActionsBody:unsupported-pattern=0x{body_pattern:02x}")

    candidates: list[int] = []
    scan_end = min(len(data), offset + BUFF_OPAQUE_TIMELINE_ACTION_BODY_MAX_BYTES)
    for candidate_end in range(offset + 1, scan_end):
        try:
            read_buff_trigger_interval_bool_tail_exact(data, candidate_end)
        except (struct.error, UnicodeDecodeError, ValueError):
            continue
        candidates.append(candidate_end)
        if len(candidates) > 1:
            break
    if len(candidates) != 1:
        raise ValueError(f"timelineActionsBody:tail-anchor-candidates={len(candidates)}")
    return candidates[0], body_pattern


BUFF_OPAQUE_STACK_EFFECT_ACTION_MAX_ACTIONS = 16


BUFF_OPAQUE_STACK_EFFECT_ACTION_NAME_MAX_BYTES = 256


BUFF_OPAQUE_STACK_EFFECT_ACTION_LAYOUTS = {
    # memberCount: (EffectActionCfg memberCount, effectName length offset,
    #               total fixed bytes excluding effectName bytes, trailing shape)
    15: (74, 37, 471, "target-settings-u32"),
    17: (85, 71, 581, "target-settings-u32-plus-guard-bool"),
}


BUFF_STACK_EFFECT_ACTION_DIAGNOSTIC_U32_OFFSETS = (1, 18, 318, 390, 467)


BUFF_STACK_EFFECT_ACTION_DIAGNOSTIC_F32X3_OFFSETS = (190,)


BUFF_STACK_EFFECT_ACTION_DIAGNOSTIC_BLOCK_OFFSETS = (128, 202, 246)


def skip_buff_stack_effects_effect_actions_body(
    data: bytes,
    offset: int,
    stack_effect_count: int,
) -> tuple[dict[str, Any], int]:
    total_action_count = 0
    action_counts: list[int] = []
    samples: list[dict[str, Any]] = []
    effect_name_counts: Counter[str] = Counter()
    action_layout_counts: Counter[int] = Counter()
    diagnostic_u32_counts: dict[int, Counter[int]] = {
        raw_offset: Counter() for raw_offset in BUFF_STACK_EFFECT_ACTION_DIAGNOSTIC_U32_OFFSETS
    }
    diagnostic_f32x3_counts: dict[int, Counter[str]] = {
        raw_offset: Counter() for raw_offset in BUFF_STACK_EFFECT_ACTION_DIAGNOSTIC_F32X3_OFFSETS
    }

    for item_index in range(stack_effect_count):
        if offset >= len(data):
            raise ValueError(f"stackEffects[{item_index}]:truncated-member-count")
        member_count = data[offset]
        offset += 1
        if member_count != 1:
            raise ValueError(f"stackEffects[{item_index}]:member-count={member_count}")

        action_count, offset = read_buff_u32_field(
            data,
            offset,
            f"stackEffects[{item_index}].effectActionsCount",
        )
        if action_count <= 0 or action_count > BUFF_OPAQUE_STACK_EFFECT_ACTION_MAX_ACTIONS:
            raise ValueError(f"stackEffects[{item_index}].effectActionsCount:unsupported-count={action_count}")
        action_counts.append(action_count)
        total_action_count += action_count

        for action_index in range(action_count):
            action_start = offset
            if action_start >= len(data):
                raise ValueError(f"stackEffects[{item_index}].effectActions[{action_index}]:truncated-body")
            member_count = data[action_start]
            layout = BUFF_OPAQUE_STACK_EFFECT_ACTION_LAYOUTS.get(member_count)
            if layout is None:
                raise ValueError(
                    f"stackEffects[{item_index}].effectActions[{action_index}]:member-count={member_count}"
                )
            cfg_member_count, name_offset, fixed_bytes, trailing_shape = layout
            if action_start + fixed_bytes > len(data):
                raise ValueError(f"stackEffects[{item_index}].effectActions[{action_index}]:truncated-body")
            discriminator = struct.unpack_from("<I", data, action_start + 1)[0]
            if discriminator != 1:
                raise ValueError(
                    f"stackEffects[{item_index}].effectActions[{action_index}]:discriminator={discriminator}"
                )
            marker = struct.unpack_from("<I", data, action_start + 18)[0]
            if marker != cfg_member_count:
                raise ValueError(f"stackEffects[{item_index}].effectActions[{action_index}]:marker={marker}")
            name_len = struct.unpack_from("<I", data, action_start + name_offset)[0]
            if name_len <= 0 or name_len > BUFF_OPAQUE_STACK_EFFECT_ACTION_NAME_MAX_BYTES:
                raise ValueError(
                    f"stackEffects[{item_index}].effectActions[{action_index}].effectName:invalid-length={name_len}"
                )
            name_start = action_start + name_offset + 4
            name_end = name_start + name_len
            action_end = action_start + fixed_bytes + name_len
            if action_end > len(data):
                raise ValueError(f"stackEffects[{item_index}].effectActions[{action_index}]:truncated-named-body")
            try:
                effect_name = data[name_start:name_end].decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError(
                    f"stackEffects[{item_index}].effectActions[{action_index}].effectName:invalid-utf8"
                ) from exc
            if not effect_name.startswith("P_"):
                raise ValueError(
                    f"stackEffects[{item_index}].effectActions[{action_index}].effectName:unexpected={effect_name[:24]}"
                )
            if member_count == 17:
                if struct.unpack_from("<I", data, name_end)[0] != 0:
                    raise ValueError(
                        f"stackEffects[{item_index}].effectActions[{action_index}]"
                        ".effectPosData:nonempty-list"
                    )
                if (
                    data[action_end - 5:action_end - 1] != b"\x04\x00\x00\x00"
                    or data[action_end - 1] not in (0, 1)
                ):
                    raise ValueError(
                        f"stackEffects[{item_index}].effectActions[{action_index}]"
                        ":missing-target-settings-tail-or-guard-bool"
                    )
            elif data[action_end - 4:action_end] != b"\x04\x00\x00\x00":
                raise ValueError(f"stackEffects[{item_index}].effectActions[{action_index}]:missing-terminal-u32")
            effect_name_counts[effect_name] += 1
            action_layout_counts[member_count] += 1
            diagnostic_u32: dict[str, int] = {}
            for raw_offset in BUFF_STACK_EFFECT_ACTION_DIAGNOSTIC_U32_OFFSETS:
                source_offset = action_start + raw_offset
                if raw_offset >= name_offset + 4:
                    source_offset += name_len
                value = struct.unpack_from("<I", data, source_offset)[0]
                diagnostic_u32_counts[raw_offset][value] += 1
                diagnostic_u32[format_offset(raw_offset)] = value
            diagnostic_f32x3: dict[str, list[float]] = {}
            for raw_offset in BUFF_STACK_EFFECT_ACTION_DIAGNOSTIC_F32X3_OFFSETS:
                source_offset = action_start + raw_offset
                if raw_offset >= name_offset + 4:
                    source_offset += name_len
                values = struct.unpack_from("<fff", data, source_offset)
                if all(math.isfinite(value) for value in values):
                    rounded = [round(value, 6) for value in values]
                    diagnostic_f32x3_counts[raw_offset][",".join(str(value) for value in rounded)] += 1
                    diagnostic_f32x3[format_offset(raw_offset)] = rounded
            diagnostic_blocks: dict[str, str] = {}
            for raw_offset in BUFF_STACK_EFFECT_ACTION_DIAGNOSTIC_BLOCK_OFFSETS:
                source_offset = action_start + raw_offset + name_len
                diagnostic_blocks[format_offset(raw_offset)] = data[source_offset:source_offset + 16].hex(" ")
            if len(samples) < 12:
                samples.append({
                    "stackEffectIndex": item_index,
                    "actionIndex": action_index,
                    "offset": format_offset(action_start),
                    "bytes": action_end - action_start,
                    "memberCount": member_count,
                    "rawDiscriminator": discriminator,
                    "effectActionCfgMemberCount": marker,
                    "trailingShape": trailing_shape,
                    "effectName": effect_name,
                    "effectNameLength": name_len,
                    "normalizedU32Fields": diagnostic_u32,
                    "scaleCandidateF32x3": diagnostic_f32x3,
                    "blackboardVector3CandidatePrefixes": diagnostic_blocks,
                })
            offset = action_end

    stacking_key_prefix_offset = offset
    if offset + 4 > len(data):
        raise ValueError("stackEffects:truncated-stacking-key-prefix")
    stacking_key_length = struct.unpack_from("<I", data, offset)[0]
    stacking_key_prefix_handling = "left-nonempty-string-for-stackingSettings"
    stacking_key_preview = ""
    if stacking_key_length == 0:
        # The compact empty-key branch historically looked like a terminal pad.
        # It is the serialized empty stackingKey string and must be consumed here
        # because the downstream compact-suffix branch begins at stackingType.
        offset += 4
        stacking_key_prefix_handling = "consumed-empty-string-prefix"
    else:
        stacking_key_preview, _key_end, key_error = read_memorypack_utf8_string(
            data,
            offset,
            max_length=256,
        )
        if key_error or not stacking_key_preview or not is_clean_skill_identifier_string(stacking_key_preview):
            raise ValueError(f"stackEffects:invalid-stacking-key-prefix={stacking_key_length}")

    return {
        "stackEffectsBodyShape": (
            "opaque EffectAction list with exact versioned byte boundaries; memberCount=15 uses "
            "EffectActionCfg memberCount=74/name@+37/fixed=471, while memberCount=17 uses "
            "EffectActionCfg memberCount=85/name@+71/fixed=581 and the added guard-source tail"
        ),
        "stackingKeyPrefixOffset": format_offset(stacking_key_prefix_offset),
        "stackingKeyPrefixHandling": stacking_key_prefix_handling,
        "stackingKeyPreview": stacking_key_preview,
        "effectActionsSemanticStatus": "partial-effectActions-unproven-field-order",
        "opaqueEffectActionCount": total_action_count,
        "effectActionsPerStackEffect": action_counts,
        "effectActionMemberCountCounts": short_counter_dict(action_layout_counts),
        "effectActionNameCounts": short_counter_dict(effect_name_counts, limit=32),
        "effectActionNormalizedU32Counts": {
            format_offset(raw_offset): short_counter_dict(counter)
            for raw_offset, counter in diagnostic_u32_counts.items()
        },
        "effectActionScaleCandidateCounts": {
            format_offset(raw_offset): short_counter_dict(counter)
            for raw_offset, counter in diagnostic_f32x3_counts.items()
        },
        "opaqueEffectActionSamples": samples,
    }, offset


BUFF_OPAQUE_IGNITE_EVENT_ACTION_BODY_MAX_BYTES = 64 * 1024


BUFF_OPAQUE_POISE_MODIFIER_BODY_MAX_BYTES = 16 * 1024


BUFF_OPAQUE_SHIELD_CONFIGS_BODY_MAX_BYTES = 16 * 1024


def buff_post_id_result_is_exact_tail(result: dict[str, Any]) -> bool:
    return result.get("status") == "parsed-through-exact-tail" and not result.get("tailParseStatus")


def read_buff_compact_empty_tag_field(
    data: bytes,
    offset: int,
    field_name: str,
) -> tuple[dict[str, Any], int]:
    end = offset + 5
    if end > len(data):
        raise ValueError(f"{field_name}:truncated-compact-empty-payload")
    if data[offset:end] != b"\x00\x00\x00\x00\x00":
        raw = data[offset] if offset < len(data) else None
        raise ValueError(f"{field_name}:not-compact-empty-member-count={raw}")
    return {
        "memberCount": 0,
        "offset": format_offset(offset),
        "branch": "compact-empty-payload",
        "branchNote": "observed empty tag payload uses five zero bytes before timelineActionsCount",
        "tagId": 0,
        "tagName": "",
    }, end


def buff_tag_name_has_control(value: str) -> bool:
    return any(ord(ch) < 32 for ch in value)


def read_buff_compact_tag_list_field(
    data: bytes,
    offset: int,
    field_name: str,
) -> tuple[dict[str, Any], int]:
    start = offset
    if offset + 5 > len(data):
        raise ValueError(f"{field_name}:truncated-compact-tag-list")
    prefix_member_count = data[offset]
    if prefix_member_count != 0:
        raise ValueError(f"{field_name}:compact-list-prefix={prefix_member_count}")
    count = struct.unpack_from("<I", data, offset + 1)[0]
    if count <= 0 or count > 16:
        raise ValueError(f"{field_name}:compact-list-count={count}")
    offset += 5
    tags: list[dict[str, Any]] = []
    for index in range(count):
        tag, offset = read_buff_gameplay_tag_field(data, offset, f"{field_name}[{index}]")
        if tag.get("memberCount") != 2:
            raise ValueError(f"{field_name}[{index}]:member-count={tag.get('memberCount')}")
        tag_name = str(tag.get("tagName") or "")
        if not is_clean_skill_tag_name(tag_name):
            raise ValueError(f"{field_name}[{index}]:unclean-tag-name")
        tags.append(tag)
    return {
        "memberCount": prefix_member_count,
        "offset": format_offset(start),
        "branch": "compact-tag-list",
        "branchNote": "observed tagsAfterTriggerExtendBuffAction list uses a zero prefix byte followed by u32 tag count",
        "count": count,
        "tags": tags,
    }, offset


def read_buff_compact_tag_id_list_field(
    data: bytes,
    offset: int,
    field_name: str,
) -> tuple[dict[str, Any], int]:
    start = offset
    if offset + 5 > len(data):
        raise ValueError(f"{field_name}:truncated-compact-tag-id-list")
    prefix_member_count = data[offset]
    if prefix_member_count != 0:
        raise ValueError(f"{field_name}:compact-id-list-prefix={prefix_member_count}")
    count = struct.unpack_from("<I", data, offset + 1)[0]
    if count <= 0 or count > 16:
        raise ValueError(f"{field_name}:compact-id-list-count={count}")
    offset += 5
    end = offset + count * 4
    if end > len(data):
        raise ValueError(f"{field_name}:truncated-compact-tag-ids")
    tag_ids = list(struct.unpack_from(f"<{count}I", data, offset))
    if any(tag_id == 0 for tag_id in tag_ids):
        raise ValueError(f"{field_name}:zero-compact-tag-id")
    return {
        "memberCount": prefix_member_count,
        "offset": format_offset(start),
        "branch": "compact-tag-id-list",
        "branchNote": (
            "observed tagsAfterTriggerExtendBuffAction list uses a zero prefix byte, "
            "u32 count, and packed u32 gameplay-tag ids without inline names"
        ),
        "count": count,
        "tagIds": [f"0x{tag_id:08x}" for tag_id in tag_ids],
    }, end


def read_buff_tags_after_trigger_field(
    data: bytes,
    offset: int,
) -> tuple[dict[str, Any], int]:
    field_name = "tagsAfterTriggerExtendBuffAction"
    try:
        tag, end = read_buff_gameplay_tag_field(data, offset, field_name)
        tag_name = str(tag.get("tagName") or "")
        if tag.get("memberCount") == 0 and tag_name:
            raise ValueError(f"{field_name}:member0-nonempty-tag")
        if buff_tag_name_has_control(tag_name):
            raise ValueError(f"{field_name}:control-tag-name")
        return tag, end
    except (struct.error, UnicodeDecodeError, ValueError):
        pass

    try:
        return read_buff_member1_empty_tag_field(data, offset, field_name)
    except (struct.error, UnicodeDecodeError, ValueError):
        pass

    try:
        return read_buff_compact_empty_tag_field(data, offset, field_name)
    except (struct.error, UnicodeDecodeError, ValueError):
        pass

    try:
        return read_buff_compact_tag_list_field(data, offset, field_name)
    except (struct.error, UnicodeDecodeError, ValueError):
        return read_buff_compact_tag_id_list_field(data, offset, field_name)


def parse_buff_tail_after_shield_configs(
    data: bytes,
    tail_offset: int,
    result: dict[str, Any],
) -> dict[str, Any]:
    try:
        stacking_settings, tail_offset = read_buff_stacking_settings_compact_id_branch(
            data,
            tail_offset,
        )
        if (
            stacking_settings.get("stackEffectsCount")
            and stacking_settings.get("stackEffectsBodyStatus")
            not in {"skipped-zero-action-items", "opaque-effectActions"}
        ):
            result["status"] = "parsed-through-stackingSettings"
            result["stackingSettings"] = stacking_settings
            result["tailParseStatus"] = "unparsed-stackEffects"
            result["tailParseOffset"] = format_offset(tail_offset)
            result["tailParseError"] = f"stackEffectsCount={stacking_settings.get('stackEffectsCount')}"
            result["endOffset"] = format_offset(tail_offset)
            return result

        tag_field_offset = tail_offset
        tags_after_trigger, tail_offset = read_buff_tags_after_trigger_field(
            data,
            tag_field_offset,
        )
        if tags_after_trigger.get("branch") == "member1-empty-payload":
            trigger_interval, use_time_dilation_dt, wait_first_trigger_interval, tail_offset = (
                read_buff_trigger_interval_bool_tail_exact(data, tail_offset)
            )
            result["status"] = "parsed-through-exact-tail"
            result["stackingSettings"] = stacking_settings
            result["tagsAfterTriggerExtendBuffAction"] = tags_after_trigger
            result["timelineActionsCount"] = 0
            result["timelineActionsEncoding"] = "omitted-empty-count-after-member1-empty-tag"
            result["triggerInterval"] = trigger_interval
            result["useTimeDilationDt"] = use_time_dilation_dt
            result["waitFirstTriggerInterval"] = wait_first_trigger_interval
            result["endOffset"] = format_offset(tail_offset)
            return result

        timeline_count_offset = tail_offset
        timeline_action_count, tail_offset = read_buff_u32_field(
            data,
            tail_offset,
            "timelineActionsCount",
        )
        if timeline_action_count > 256:
            try:
                trigger_interval, use_time_dilation_dt, wait_first_trigger_interval, tail_offset = (
                    read_buff_trigger_interval_bool_tail_exact(data, timeline_count_offset)
                )
            except (struct.error, UnicodeDecodeError, ValueError):
                raise ValueError(f"timelineActionsCount:large-count={timeline_action_count}")
            result["status"] = "parsed-through-exact-tail"
            result["stackingSettings"] = stacking_settings
            result["tagsAfterTriggerExtendBuffAction"] = tags_after_trigger
            result["timelineActionsCount"] = 0
            result["timelineActionsEncoding"] = "omitted-empty-count"
            result["triggerInterval"] = trigger_interval
            result["useTimeDilationDt"] = use_time_dilation_dt
            result["waitFirstTriggerInterval"] = wait_first_trigger_interval
            result["endOffset"] = format_offset(tail_offset)
            return result
        if timeline_action_count:
            try:
                trigger_interval, use_time_dilation_dt, wait_first_trigger_interval, tail_offset = (
                    read_buff_trigger_interval_bool_tail_exact(data, timeline_count_offset)
                )
            except (struct.error, UnicodeDecodeError, ValueError):
                try:
                    timeline_body_end, timeline_body_pattern = find_buff_timeline_actions_body_end(
                        data,
                        tail_offset,
                        timeline_action_count,
                    )
                    trigger_interval, use_time_dilation_dt, wait_first_trigger_interval, tail_offset = (
                        read_buff_trigger_interval_bool_tail_exact(data, timeline_body_end)
                    )
                except (struct.error, UnicodeDecodeError, ValueError):
                    result["status"] = "parsed-through-timelineActionsCount"
                    result["stackingSettings"] = stacking_settings
                    result["tagsAfterTriggerExtendBuffAction"] = tags_after_trigger
                    result["timelineActionsCount"] = timeline_action_count
                    result["tailParseStatus"] = "unparsed-timelineActions"
                    result["tailParseOffset"] = format_offset(tail_offset)
                    result["tailParseError"] = f"timelineActionsCount={timeline_action_count}"
                    result["endOffset"] = format_offset(tail_offset)
                    return result
                result["status"] = "parsed-through-exact-tail"
                result["stackingSettings"] = stacking_settings
                result["tagsAfterTriggerExtendBuffAction"] = tags_after_trigger
                result["timelineActionsCount"] = timeline_action_count
                try:
                    result.update(decode_buff_timeline_actions_outer(
                        data,
                        timeline_count_offset + 4,
                        timeline_action_count,
                        timeline_body_end,
                    ))
                except (struct.error, UnicodeDecodeError, ValueError) as timeline_exc:
                    result["timelineActionsBodyStatus"] = "opaque-timelineActions"
                    result["timelineActionsSemanticStatus"] = f"partial-decode-failed:{timeline_exc}"
                result["timelineActionsBodyOffset"] = format_offset(timeline_count_offset + 4)
                result["timelineActionsBodyBytes"] = timeline_body_end - (timeline_count_offset + 4)
                result["timelineActionsBodyPattern"] = f"0x{timeline_body_pattern:02x}"
                result["triggerInterval"] = trigger_interval
                result["useTimeDilationDt"] = use_time_dilation_dt
                result["waitFirstTriggerInterval"] = wait_first_trigger_interval
                result["endOffset"] = format_offset(tail_offset)
                return result
            result["status"] = "parsed-through-exact-tail"
            result["stackingSettings"] = stacking_settings
            result["tagsAfterTriggerExtendBuffAction"] = tags_after_trigger
            result["timelineActionsCount"] = 0
            result["timelineActionsEncoding"] = "omitted-empty-count"
            result["timelineActionsApparentCount"] = timeline_action_count
            result["triggerInterval"] = trigger_interval
            result["useTimeDilationDt"] = use_time_dilation_dt
            result["waitFirstTriggerInterval"] = wait_first_trigger_interval
            result["endOffset"] = format_offset(tail_offset)
            return result

        trigger_interval, use_time_dilation_dt, wait_first_trigger_interval, tail_offset = (
            read_buff_trigger_interval_bool_tail_exact(data, tail_offset)
        )
        result["status"] = "parsed-through-exact-tail"
        result["stackingSettings"] = stacking_settings
        result["tagsAfterTriggerExtendBuffAction"] = tags_after_trigger
        result["timelineActionsCount"] = timeline_action_count
        result["triggerInterval"] = trigger_interval
        result["useTimeDilationDt"] = use_time_dilation_dt
        result["waitFirstTriggerInterval"] = wait_first_trigger_interval
        result["endOffset"] = format_offset(tail_offset)
    except (struct.error, UnicodeDecodeError, ValueError) as tail_exc:
        result["tailParseStatus"] = "parse-error"
        result["tailParseOffset"] = format_offset(tail_offset)
        result["tailParseError"] = str(tail_exc)
    result.setdefault("endOffset", format_offset(tail_offset))
    return result


def summarize_buff_opaque_body_diagnostics(
    data: bytes,
    offset: int,
    body_end: int,
    field_prefix: str,
    *,
    max_head_bytes: int = 96,
    max_tail_bytes: int = 48,
    max_string_hits: int = 12,
) -> dict[str, Any]:
    if body_end < offset or body_end > len(data):
        raise ValueError(f"{field_prefix}:invalid-body-bounds")
    body_len = body_end - offset
    details: dict[str, Any] = {
        f"{field_prefix}BodyMemberCountCandidate": data[offset] if body_len else None,
        f"{field_prefix}BodyU32AtPlus1Candidate": read_u32_at(data, offset + 1) if body_len >= 5 else None,
        f"{field_prefix}BodyHeadHex": data[offset:offset + min(body_len, max_head_bytes)].hex(" "),
        f"{field_prefix}BodyTailHex": data[max(offset, body_end - min(body_len, max_tail_bytes)):body_end].hex(" "),
    }
    string_hits = scan_length_prefixed_utf8_string_hits(
        data,
        start=offset,
        max_scan_bytes=body_len,
        max_samples=max_string_hits,
        max_length=160,
    )
    if string_hits:
        details[f"{field_prefix}BodyStringHits"] = string_hits
    return {key: value for key, value in details.items() if value not in (None, "")}


def find_buff_shield_configs_body_end(
    data: bytes,
    offset: int,
    shield_config_count: int,
) -> tuple[dict[str, Any], int]:
    if shield_config_count <= 0 or shield_config_count > 16:
        raise ValueError(f"shieldConfigsCount:unsupported-body-count={shield_config_count}")
    if offset >= len(data) or data[offset] != 9:
        raw = data[offset] if offset < len(data) else None
        raise ValueError(f"shieldConfigsBody:unsupported-member-count={raw}")

    candidates: list[tuple[int, dict[str, Any]]] = []
    scan_end = min(len(data), offset + BUFF_OPAQUE_SHIELD_CONFIGS_BODY_MAX_BYTES)
    for candidate_end in range(offset + 1, scan_end):
        if data[candidate_end] != 12:
            continue
        probe_result: dict[str, Any] = {
            "status": "parsed-through-shieldConfigsCount",
            "shieldConfigsCount": shield_config_count,
        }
        parsed = parse_buff_tail_after_shield_configs(data, candidate_end, probe_result)
        if buff_post_id_result_is_exact_tail(parsed):
            candidates.append((candidate_end, parsed))
            if len(candidates) > 1:
                break
    if len(candidates) != 1:
        raise ValueError(f"shieldConfigsBody:tail-anchor-candidates={len(candidates)}")

    body_end, parsed = candidates[0]
    body_diagnostics = summarize_buff_opaque_body_diagnostics(
        data,
        offset,
        body_end,
        "shieldConfigs",
    )
    return {
        "shieldConfigsBodyShape": "opaque ShieldConfig list; boundary selected by unique downstream stackingSettings/tail parse",
        "shieldConfigsSemanticStatus": "partial-shieldConfigs-opaque-nested-fields",
        **body_diagnostics,
        "shieldConfigsBodyTailPreview": {
            key: parsed.get(key)
            for key in ("timelineActionsCount", "timelineActionsBodyStatus", "timelineActionsBodyBytes")
            if parsed.get(key) not in (None, "")
        },
    }, body_end


def read_buff_shield_configs_and_tail(
    data: bytes,
    offset: int,
    result: dict[str, Any],
) -> dict[str, Any]:
    shield_config_count, offset = read_buff_u32_field(data, offset, "shieldConfigsCount")
    if shield_config_count > 256:
        raise ValueError(f"shieldConfigsCount:large-count={shield_config_count}")
    result["shieldConfigsCount"] = shield_config_count
    result["status"] = "parsed-through-shieldConfigsCount"
    if shield_config_count:
        shield_body_offset = offset
        try:
            shield_body_details, offset = find_buff_shield_configs_body_end(
                data,
                offset,
                shield_config_count,
            )
        except (struct.error, UnicodeDecodeError, ValueError) as exc:
            result["tailParseStatus"] = "unparsed-shieldConfigs"
            result["tailParseOffset"] = format_offset(offset)
            result["tailParseError"] = f"shieldConfigsCount={shield_config_count}; {exc}"
            result["endOffset"] = format_offset(offset)
            return result
        result["shieldConfigsBodyStatus"] = "opaque-shieldConfigs"
        result["shieldConfigsBodyOffset"] = format_offset(shield_body_offset)
        result["shieldConfigsBodyBytes"] = offset - shield_body_offset
        result.update(shield_body_details)
    return parse_buff_tail_after_shield_configs(data, offset, result)


def find_buff_poise_modifier_body_end(
    data: bytes,
    offset: int,
    poise_modifier_count: int,
) -> tuple[dict[str, Any], int]:
    if poise_modifier_count <= 0 or poise_modifier_count > 16:
        raise ValueError(f"poiseModifierCount:unsupported-body-count={poise_modifier_count}")
    if offset >= len(data) or data[offset] != 3:
        raw = data[offset] if offset < len(data) else None
        raise ValueError(f"poiseModifierBody:unsupported-prefix={raw}")

    candidates: list[tuple[int, dict[str, Any]]] = []
    scan_end = min(len(data), offset + BUFF_OPAQUE_POISE_MODIFIER_BODY_MAX_BYTES)
    for candidate_end in range(offset + 1, scan_end):
        shield_count = read_u32_at(data, candidate_end)
        if shield_count is None or shield_count > 16:
            continue
        if shield_count == 0:
            if candidate_end + 4 >= len(data) or data[candidate_end + 4] != 12:
                continue
        elif candidate_end + 4 >= len(data) or data[candidate_end + 4] != 9:
            continue
        probe_result: dict[str, Any] = {
            "status": "parsed-through-poiseModifierCount",
            "poiseModifierCount": poise_modifier_count,
        }
        parsed = read_buff_shield_configs_and_tail(data, candidate_end, probe_result)
        if buff_post_id_result_is_exact_tail(parsed):
            candidates.append((candidate_end, parsed))
            if len(candidates) > 1:
                break
    if len(candidates) != 1:
        raise ValueError(f"poiseModifierBody:tail-anchor-candidates={len(candidates)}")

    body_end, parsed = candidates[0]
    body_diagnostics = summarize_buff_opaque_body_diagnostics(
        data,
        offset,
        body_end,
        "poiseModifier",
    )
    return {
        "poiseModifierBodyShape": "opaque PoiseModifier list; boundary selected by unique downstream shieldConfigs/tail parse",
        "poiseModifierSemanticStatus": "partial-poiseModifier-opaque-processors",
        **body_diagnostics,
        "poiseModifierBodyTailPreview": {
            key: parsed.get(key)
            for key in (
                "shieldConfigsCount",
                "shieldConfigsBodyStatus",
                "timelineActionsCount",
                "timelineActionsBodyStatus",
            )
            if parsed.get(key) not in (None, "")
        },
    }, body_end


def read_buff_post_ignite_suffix(
    data: bytes,
    offset: int,
    result: dict[str, Any],
) -> dict[str, Any]:
    ignore_cooldown, offset = read_buff_bool_field(
        data,
        offset,
        "ignoreCooldownWhenAdding",
    )
    ignore_tag_immune, offset = read_buff_bool_field(data, offset, "ignoreTagImmune")
    if offset >= len(data):
        raise ValueError("lifeType:truncated-u8")
    life_type = data[offset]
    offset += 1
    max_trigger_count, offset = read_buff_blackboard_int_field(
        data,
        offset,
        "maxTriggerCnt",
    )
    only_use_self_time_dilation, offset = read_buff_bool_field(
        data,
        offset,
        "onlyUseSelfTimeDilation",
    )
    poise_modifier_count, offset = read_buff_u32_field(data, offset, "poiseModifierCount")
    if poise_modifier_count > 256:
        raise ValueError(f"poiseModifierCount:large-count={poise_modifier_count}")

    result.update({
        "status": "parsed-through-poiseModifierCount",
        "ignoreCooldownWhenAdding": ignore_cooldown,
        "ignoreTagImmune": ignore_tag_immune,
        "lifeTypeRaw": life_type,
        "maxTriggerCnt": max_trigger_count,
        "onlyUseSelfTimeDilation": only_use_self_time_dilation,
        "poiseModifierCount": poise_modifier_count,
    })
    if poise_modifier_count:
        poise_body_offset = offset
        try:
            poise_body_details, offset = find_buff_poise_modifier_body_end(
                data,
                offset,
                poise_modifier_count,
            )
        except (struct.error, UnicodeDecodeError, ValueError) as exc:
            result["stopReason"] = "poiseModifier list body not skipped"
            result["tailParseStatus"] = "unparsed-poiseModifier"
            result["tailParseOffset"] = format_offset(offset)
            result["tailParseError"] = f"poiseModifierCount={poise_modifier_count}; {exc}"
            result["endOffset"] = format_offset(offset)
            return result
        result["poiseModifierBodyStatus"] = "opaque-poiseModifier"
        result["poiseModifierBodyOffset"] = format_offset(poise_body_offset)
        result["poiseModifierBodyBytes"] = offset - poise_body_offset
        result.update(poise_body_details)

    return read_buff_shield_configs_and_tail(data, offset, result)


BUFF_IGNITE_NESTED_BLOCK_START = b"\x03\x01\x00\x00\x00\x03"


BUFF_IGNITE_NESTED_BLOCK_LONG_HEADERS = (
    ("energy-shard-long-v1", b"\x03\x01\x00\x00\x00\x03\x02\x00\x00\x00\xfa\x44\x01\x08"),
    ("energy-shard-long-v2", b"\x03\x01\x00\x00\x00\x03\x02\x00\x00\x00\xfa\x5d\x01\x08"),
)


BUFF_IGNITE_NESTED_BLOCK_SHORT_HEADERS = (
    ("energy-shard-short-v1", b"\x03\x01\x00\x00\x00\x03\x01\x00\x00\x00\x82\x11\x01"),
    ("energy-shard-short-v2", b"\x03\x01\x00\x00\x00\x03\x01\x00\x00\x00\x8a\x13\x01"),
)


BUFF_IGNITE_NESTED_BLOCK_TAIL_PREFIX = b"\x04\x00\x00\x00\x00\x00\x00"


def validate_buff_ignite_nested_blocks(
    data: bytes,
    offset: int,
    body_end: int,
    ignite_count: int,
) -> dict[str, Any]:
    if ignite_count != 4:
        raise ValueError(f"igniteEventActionNestedBlocks:unsupported-count={ignite_count}")
    if body_end <= offset or body_end > len(data):
        raise ValueError("igniteEventActionNestedBlocks:invalid-body-end")
    if data[offset:offset + len(BUFF_IGNITE_NESTED_BLOCK_START)] != BUFF_IGNITE_NESTED_BLOCK_START:
        raise ValueError("igniteEventActionNestedBlocks:missing-initial-block")

    starts: list[int] = []
    probe = offset
    while probe < body_end:
        found = data.find(BUFF_IGNITE_NESTED_BLOCK_START, probe, body_end)
        if found < 0:
            break
        starts.append(found)
        probe = found + 1
    if len(starts) != ignite_count or starts[0] != offset:
        raise ValueError(f"igniteEventActionNestedBlocks:block-start-count={len(starts)}")

    tail_codes: list[int] = []
    block_summaries: list[dict[str, Any]] = []
    for index, start in enumerate(starts):
        block_end = starts[index + 1] if index + 1 < len(starts) else body_end
        if index < 3:
            header_variants = BUFF_IGNITE_NESTED_BLOCK_LONG_HEADERS
        else:
            header_variants = BUFF_IGNITE_NESTED_BLOCK_SHORT_HEADERS
        header_kind = next(
            (
                name
                for name, header in header_variants
                if data[start:start + len(header)] == header
            ),
            "",
        )
        if not header_kind:
            raise ValueError(f"igniteEventActionNestedBlocks[{index}]:header-mismatch")
        if block_end - start < 11:
            raise ValueError(f"igniteEventActionNestedBlocks[{index}]:truncated-tail")
        tail = data[block_end - 11:block_end]
        if tail[:7] != BUFF_IGNITE_NESTED_BLOCK_TAIL_PREFIX or tail[8:] != b"\x00\x00\x00":
            raise ValueError(f"igniteEventActionNestedBlocks[{index}]:tail-mismatch")
        tail_code = tail[7]
        tail_codes.append(tail_code)
        block_summary = {
            "index": index,
            "offset": format_offset(start),
            "bytes": block_end - start,
            "header": header_kind,
            "tailCode": tail_code,
        }
        string_hits = scan_length_prefixed_utf8_string_hits(
            data,
            start=start,
            max_scan_bytes=block_end - start,
            max_samples=8,
            max_length=160,
        )
        if string_hits:
            block_summary["stringHits"] = string_hits
        block_summaries.append(block_summary)
    if set(tail_codes) != {2, 3, 4, 5}:
        raise ValueError(f"igniteEventActionNestedBlocks:tail-codes={tail_codes}")

    return {
        "igniteEventActionBodyStatus": "opaque-igniteEventAction-nestedBlocks",
        "igniteEventActionBodyEncoding": "energy-shard-nested-blocks",
        "igniteEventActionSemanticStatus": "partial-igniteEventAction-nestedBlocks-opaque-actionData",
        "igniteEventActionNestedBlockCount": len(starts),
        "igniteEventActionNestedBlockTailCodes": tail_codes,
        "igniteEventActionNestedBlocks": block_summaries,
    }


def find_buff_ignite_event_action_body_end(
    data: bytes,
    offset: int,
    ignite_count: int,
) -> tuple[dict[str, Any], int]:
    if ignite_count <= 0 or ignite_count > 16:
        raise ValueError(f"igniteEventActionCount:unsupported-body-count={ignite_count}")
    if offset + 5 > len(data) or data[offset] != 3:
        raw = data[offset] if offset < len(data) else None
        raise ValueError(f"igniteEventActionBody:unsupported-prefix={raw}")
    body_count = read_u32_at(data, offset + 1)

    candidates: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
    scan_end = min(len(data), offset + BUFF_OPAQUE_IGNITE_EVENT_ACTION_BODY_MAX_BYTES)
    for candidate_end in range(offset + 5, scan_end):
        if candidate_end + 4 >= len(data):
            break
        if data[candidate_end] not in (0, 1) or data[candidate_end + 1] not in (0, 1):
            continue
        if data[candidate_end + 3] != 3:
            continue
        probe_result: dict[str, Any] = {
            "status": "parsed-through-igniteEventActionCount",
            "igniteEventActionCount": ignite_count,
        }
        try:
            parsed = read_buff_post_ignite_suffix(data, candidate_end, probe_result)
        except (struct.error, UnicodeDecodeError, ValueError):
            continue
        if buff_post_id_result_is_exact_tail(parsed):
            if body_count == ignite_count:
                body_details: dict[str, Any] = {
                    "igniteEventActionSemanticStatus": "partial-igniteEventAction-opaque-actionData",
                    "igniteEventActionBodyLocalCount": body_count,
                }
                body_details.update(summarize_buff_opaque_body_diagnostics(
                    data,
                    offset,
                    candidate_end,
                    "igniteEventAction",
                    max_string_hits=16,
                ))
            else:
                body_details = validate_buff_ignite_nested_blocks(
                    data,
                    offset,
                    candidate_end,
                    ignite_count,
                )
                body_details["igniteEventActionBodyLocalCount"] = body_count
                body_details.update(summarize_buff_opaque_body_diagnostics(
                    data,
                    offset,
                    candidate_end,
                    "igniteEventAction",
                    max_string_hits=16,
                ))
            candidates.append((candidate_end, parsed, body_details))
            if len(candidates) > 1:
                break
    if len(candidates) != 1:
        if body_count != ignite_count:
            raise ValueError(f"igniteEventActionBody:body-count={body_count}; tail-anchor-candidates={len(candidates)}")
        raise ValueError(f"igniteEventActionBody:tail-anchor-candidates={len(candidates)}")

    body_end, parsed, body_details = candidates[0]
    result = {
        "igniteEventActionBodyShape": "opaque IgniteEventAction list; boundary selected by unique downstream bool/maxTrigger/poise/tail parse",
        "igniteEventActionBodyTailPreview": {
            key: parsed.get(key)
            for key in (
                "poiseModifierCount",
                "poiseModifierBodyStatus",
                "shieldConfigsCount",
                "shieldConfigsBodyStatus",
                "timelineActionsCount",
                "timelineActionsBodyStatus",
            )
            if parsed.get(key) not in (None, "")
        },
    }
    result.update(body_details)
    return result, body_end


def read_buff_stacking_settings_compact_id_branch(
    data: bytes,
    offset: int,
) -> tuple[dict[str, Any], int]:
    start = offset
    if offset >= len(data):
        raise ValueError("stackingSettings:truncated-member-count")
    member_count = data[offset]
    offset += 1
    if member_count != 12:
        raise ValueError(f"stackingSettings:member-count={member_count}")

    identifier_type = data[offset]
    offset += 1
    if identifier_type not in (0, 1):
        raise ValueError(f"stackingSettings.identifierType:raw={identifier_type}")
    is_need_stack_effect, offset = read_buff_bool_field(
        data,
        offset,
        "stackingSettings.isNeedStackEffect",
    )
    if offset + 4 > len(data):
        raise ValueError("stackingSettings.maxStackCnt:truncated-i32")
    max_stack_count = struct.unpack_from("<i", data, offset)[0]
    offset += 4
    max_stack_count_key, offset, error = read_memorypack_utf8_string(data, offset, max_length=256)
    if error:
        raise ValueError(f"stackingSettings.maxStackCntKey:{error}")
    negate_priority, offset = read_buff_bool_field(data, offset, "stackingSettings.negatePriority")
    if offset + 4 > len(data):
        raise ValueError("stackingSettings.priority:truncated-f32")
    priority = struct.unpack_from("<f", data, offset)[0]
    offset += 4
    priority_key, offset, error = read_memorypack_utf8_string(data, offset, max_length=256)
    if error:
        raise ValueError(f"stackingSettings.priorityKey:{error}")
    stack_effect_count, offset = read_buff_u32_field(data, offset, "stackingSettings.stackEffectsCount")
    if stack_effect_count > 256:
        raise ValueError(f"stackingSettings.stackEffectsCount:large-count={stack_effect_count}")

    stack_effects_body_offset = offset
    stack_effects_body_status = ""
    stack_effects_body_bytes = 0
    stack_effects_body_details: dict[str, Any] = {}
    if stack_effect_count:
        zero_action_end = offset + stack_effect_count * 5
        zero_action_body = zero_action_end <= len(data)
        probe = offset
        for _ in range(stack_effect_count):
            if not zero_action_body or data[probe] != 1:
                zero_action_body = False
                break
            action_count = struct.unpack_from("<I", data, probe + 1)[0]
            if action_count != 0:
                zero_action_body = False
                break
            probe += 5
        if zero_action_body:
            offset = zero_action_end
            stack_effects_body_status = "skipped-zero-action-items"
            stack_effects_body_bytes = offset - stack_effects_body_offset
        else:
            try:
                stack_effects_body_details, offset = skip_buff_stack_effects_effect_actions_body(
                    data,
                    offset,
                    stack_effect_count,
                )
            except (struct.error, UnicodeDecodeError, ValueError) as exc:
                return {
                    "memberCount": member_count,
                    "offset": format_offset(start),
                    "branch": "stack-effects-body",
                    "branchNote": "nonzero stackEffects body remains opaque until EffectActionCfg layout is skipped",
                    "identifierTypeRaw": identifier_type,
                    "maxStackCnt": max_stack_count,
                    "maxStackCntKey": max_stack_count_key or "",
                    "priority": round(priority, 6),
                    "priorityKey": priority_key or "",
                    "negatePriority": negate_priority,
                    "isNeedStackEffect": is_need_stack_effect,
                    "stackEffectsCount": stack_effect_count,
                    "stackEffectsBodyStatus": "unparsed-effectActions",
                    "stackEffectsBodyOffset": format_offset(stack_effects_body_offset),
                    "stackEffectsBodyError": str(exc),
                }, stack_effects_body_offset
            stack_effects_body_status = "opaque-effectActions"
            stack_effects_body_bytes = offset - stack_effects_body_offset

    stacking_key_offset = offset
    stacking_key, stacking_key_end, stacking_key_error = read_memorypack_utf8_string(
        data,
        stacking_key_offset,
        max_length=256,
    )
    branch = "compact-id"
    branch_note = "validated rows use identifierType=Id; empty stackingKey branch consumes compact suffix bytes"
    if stacking_key_error is None and stacking_key and is_clean_skill_identifier_string(stacking_key):
        offset = stacking_key_end
        branch = "compact-stacking-key"
        branch_note = "non-empty stackingKey branch consumes the common compact suffix bytes"
    else:
        stacking_key = ""

    stacking_type = data[offset]
    offset += 1
    if stacking_type > 16:
        raise ValueError(f"stackingSettings.stackingType:raw={stacking_type}")
    use_max_stack_count_key, offset = read_buff_bool_field(
        data,
        offset,
        "stackingSettings.useMaxStackCntKey",
    )
    use_priority_key, offset = read_buff_bool_field(data, offset, "stackingSettings.usePriorityKey")

    result = {
        "memberCount": member_count,
        "offset": format_offset(start),
        "branch": branch,
        "branchNote": branch_note,
        "identifierTypeRaw": identifier_type,
        "stackingTypeRaw": stacking_type,
        "maxStackCnt": max_stack_count,
        "maxStackCntKey": max_stack_count_key or "",
        "useMaxStackCntKey": use_max_stack_count_key,
        "usePriorityKey": use_priority_key,
        "priority": round(priority, 6),
        "priorityKey": priority_key or "",
        "negatePriority": negate_priority,
        "isNeedStackEffect": is_need_stack_effect,
        "stackEffectsCount": stack_effect_count,
    }
    if stack_effects_body_status:
        result["stackEffectsBodyStatus"] = stack_effects_body_status
        result["stackEffectsBodyOffset"] = format_offset(stack_effects_body_offset)
        result["stackEffectsBodyBytes"] = stack_effects_body_bytes
        result.update(stack_effects_body_details)
    if stacking_key:
        result["stackingKey"] = stacking_key
    return result, offset


def summarize_buff_post_id_prefix_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "idMarkerOffset": candidate.get("idMarkerOffset"),
        "status": candidate.get("status"),
        "offset": candidate.get("offset"),
        "endOffset": candidate.get("endOffset"),
    }
    for key in (
        "tailParseStatus",
        "tailParseOffset",
        "error",
        "tailParseError",
        "igniteEventActionCount",
        "poiseModifierCount",
        "shieldConfigsCount",
    ):
        if key in candidate:
            summary[key] = candidate.get(key)
    return {key: value for key, value in summary.items() if value not in (None, "")}


def decode_buff_post_id_prefix_at(
    data: bytes,
    id_value: str,
    id_marker_offset: int,
) -> dict[str, Any]:
    start = id_marker_offset + 4 + len(id_value.encode("utf-8"))
    offset = start
    try:
        ignite_count, offset = read_buff_u32_field(data, offset, "igniteEventActionCount")
        if ignite_count > 256:
            raise ValueError(f"igniteEventActionCount:large-count={ignite_count}")
        result: dict[str, Any] = {
            "status": "parsed-through-igniteEventActionCount",
            "source": "anchored after exact top-level id marker; bounded opaque list bodies resume downstream tail parsing",
            "idMarkerOffset": format_offset(id_marker_offset),
            "offset": format_offset(start),
            "igniteEventActionCount": ignite_count,
        }
        if ignite_count:
            ignite_body_offset = offset
            try:
                ignite_body_details, offset = find_buff_ignite_event_action_body_end(
                    data,
                    offset,
                    ignite_count,
                )
            except (struct.error, UnicodeDecodeError, ValueError) as exc:
                result["tailParseStatus"] = "unparsed-igniteEventAction"
                result["tailParseOffset"] = format_offset(offset)
                result["tailParseError"] = f"igniteEventActionCount={ignite_count}; {exc}"
                result["endOffset"] = format_offset(offset)
                return result
            result["igniteEventActionBodyStatus"] = "opaque-igniteEventAction"
            result["igniteEventActionBodyOffset"] = format_offset(ignite_body_offset)
            result["igniteEventActionBodyBytes"] = offset - ignite_body_offset
            result.update(ignite_body_details)
        return read_buff_post_ignite_suffix(data, offset, result)
    except (struct.error, UnicodeDecodeError, ValueError) as exc:
        return {
            "status": "parse-error",
            "idMarkerOffset": format_offset(id_marker_offset),
            "offset": format_offset(offset),
            "error": str(exc),
        }


def decode_buff_post_id_prefix(
    data: bytes,
    id_value: str,
    id_marker_count: int,
    id_marker_offsets: list[int],
) -> dict[str, Any]:
    if not id_value or not id_marker_offsets:
        return {"status": "missing-id-marker"}

    candidates = [
        decode_buff_post_id_prefix_at(data, id_value, marker_offset)
        for marker_offset in id_marker_offsets
    ]
    if id_marker_count == 1:
        return candidates[0]

    exact_candidates = [
        candidate for candidate in candidates
        if candidate.get("status") == "parsed-through-exact-tail"
    ]
    if len(exact_candidates) == 1:
        result = dict(exact_candidates[0])
        result["anchorSelection"] = {
            "status": "selected-from-ambiguous-id-markers",
            "idMarkerCount": id_marker_count,
            "selectedIdMarkerOffset": result.get("idMarkerOffset"),
            "selectionCriteria": "unique BuffData id marker candidate parsed through exact tail",
            "candidateSummaries": [
                summarize_buff_post_id_prefix_candidate(candidate)
                for candidate in candidates[:12]
            ],
        }
        return result

    structured_candidates = [
        candidate for candidate in candidates
        if str(candidate.get("status") or "").startswith("parsed-through")
    ]
    if len(structured_candidates) == 1 and all(
        candidate is structured_candidates[0] or candidate.get("status") == "parse-error"
        for candidate in candidates
    ):
        result = dict(structured_candidates[0])
        result["anchorSelection"] = {
            "status": "selected-from-ambiguous-id-markers",
            "idMarkerCount": id_marker_count,
            "selectedIdMarkerOffset": result.get("idMarkerOffset"),
            "selectionCriteria": "unique BuffData id marker candidate reached a structured parser stop; all other candidates were hard parse errors",
            "candidateSummaries": [
                summarize_buff_post_id_prefix_candidate(candidate)
                for candidate in candidates[:12]
            ],
        }
        return result

    return {
        "status": "ambiguous-id-marker",
        "idMarkerCount": id_marker_count,
        "candidateCount": len(candidates),
        "idMarkerOffsets": [format_offset(offset) for offset in id_marker_offsets],
        "selectionCriteria": "requires a unique BuffData candidate that parses through exact tail",
        "candidateSummaries": [
            summarize_buff_post_id_prefix_candidate(candidate)
            for candidate in candidates[:12]
        ],
    }


def buff_post_id_prefix_sample(prefix: dict[str, Any]) -> str:
    status = str(prefix.get("status") or "")
    if not status.startswith("parsed-through"):
        return ""
    max_trigger = prefix.get("maxTriggerCnt") or {}
    if prefix.get("status") == "parsed-through-exact-tail":
        stacking = prefix.get("stackingSettings") or {}
        trigger = prefix.get("triggerInterval") or {}
        parts = [
            f"life:{prefix.get('lifeTypeRaw')}",
            f"maxTrig:{max_trigger.get('value')}",
            f"selfTime:{int(bool(prefix.get('onlyUseSelfTimeDilation')))}",
            f"stack:{stacking.get('stackingTypeRaw')}",
            f"maxStack:{stacking.get('maxStackCnt')}",
            f"trig:{trigger.get('value')}",
            f"wait:{int(bool(prefix.get('waitFirstTriggerInterval')))}",
        ]
        return ",".join(parts)

    parts = [
        f"life:{prefix.get('lifeTypeRaw')}",
        f"maxTrig:{max_trigger.get('value')}",
        f"immune:{int(bool(prefix.get('ignoreTagImmune')))}",
        f"selfTime:{int(bool(prefix.get('onlyUseSelfTimeDilation')))}",
        f"poise:{prefix.get('poiseModifierCount')}",
    ]
    if "shieldConfigsCount" in prefix:
        parts.append(f"shield:{prefix.get('shieldConfigsCount')}")
    return ",".join(parts)


def read_skill_u8_field(data: bytes, offset: int, field_name: str, *, max_value: int = 255) -> tuple[int, int]:
    if offset >= len(data):
        raise ValueError(f"{field_name}:truncated-u8")
    value = data[offset]
    if value > max_value:
        raise ValueError(f"{field_name}:raw={value}")
    return value, offset + 1


def read_skill_i32_field(data: bytes, offset: int, field_name: str) -> tuple[int, int]:
    if offset + 4 > len(data):
        raise ValueError(f"{field_name}:truncated-i32")
    return struct.unpack_from("<i", data, offset)[0], offset + 4


def read_skill_bool_field(data: bytes, offset: int, field_name: str) -> tuple[bool, int]:
    if offset >= len(data):
        raise ValueError(f"{field_name}:truncated-bool")
    value = data[offset]
    if value not in (0, 1):
        raise ValueError(f"{field_name}:byte={value}")
    return bool(value), offset + 1


def read_skill_f32_field(data: bytes, offset: int, field_name: str) -> tuple[float, int]:
    if offset + 4 > len(data):
        raise ValueError(f"{field_name}:truncated-f32")
    return struct.unpack_from("<f", data, offset)[0], offset + 4


def read_skill_vector2_field(data: bytes, offset: int, field_name: str) -> tuple[dict[str, float], int]:
    if offset + 8 > len(data):
        raise ValueError(f"{field_name}:truncated-vector2")
    x, y = struct.unpack_from("<ff", data, offset)
    return {"x": round(x, 6), "y": round(y, 6)}, offset + 8


def read_skill_clean_string_field(
    data: bytes,
    offset: int,
    field_name: str,
    *,
    max_length: int = 128,
) -> tuple[str, int]:
    value, offset, error = read_memorypack_utf8_string(data, offset, max_length=max_length)
    if error:
        raise ValueError(f"{field_name}:{error}")
    value = value or ""
    if not is_clean_skill_identifier_string(value):
        raise ValueError(f"{field_name}:not-clean len={len(value)}")
    return value, offset


def read_skill_gameplay_tag_record(data: bytes, offset: int, field_name: str, index: int) -> tuple[dict[str, Any], int]:
    if offset >= len(data):
        raise ValueError(f"{field_name}[{index}]:truncated-member-count")
    member_count = data[offset]
    offset += 1
    tag_id, offset = read_buff_u32_field(data, offset, f"{field_name}[{index}].tagId")
    if member_count == 1:
        tag_name = ""
        encoding = "member1-id-only"
    else:
        tag_name, offset, error = read_memorypack_utf8_string(data, offset, max_length=256)
        if error:
            raise ValueError(f"{field_name}[{index}].tagName:{error}")
        encoding = "member-and-id-plus-name"
    tag_name = tag_name or ""
    if tag_name and not is_clean_skill_tag_name(tag_name):
        raise ValueError(f"{field_name}[{index}].tagName:not-clean len={len(tag_name)}")
    return {
        "index": index,
        "memberCount": member_count,
        "encoding": encoding,
        "tagId": tag_id,
        "tagHash": f"0x{tag_id:08x}",
        "tagName": tag_name,
    }, offset


def read_skill_gameplay_tag_list_field(
    data: bytes,
    offset: int,
    field_name: str,
    *,
    max_items: int = 128,
) -> tuple[dict[str, Any], int]:
    start = offset
    raw_count, offset_after_u32 = read_buff_u32_field(data, offset, f"{field_name}Count")
    branch = "counted"
    prefix_member_count: int | None = None
    count = raw_count
    body_offset = offset_after_u32
    if raw_count == MEMORYPACK_NULL_COUNT:
        return {
            "offset": format_offset(start),
            "branch": branch,
            "prefixMemberCount": None,
            "count": None,
            "tags": [],
        }, body_offset
    if raw_count > max_items:
        prefix_member_count = data[start]
        if prefix_member_count != 1:
            raise ValueError(f"{field_name}:large-count={raw_count}")
        count, body_offset = read_buff_u32_field(data, start + 1, f"{field_name}.wrappedCount")
        branch = "one-member-wrapper"
    if count > max_items:
        raise ValueError(f"{field_name}:large-count={count}")
    tags: list[dict[str, Any]] = []
    for index in range(count):
        tag, body_offset = read_skill_gameplay_tag_record(data, body_offset, field_name, index)
        tags.append(tag)
    return {
        "offset": format_offset(start),
        "branch": branch,
        "prefixMemberCount": prefix_member_count,
        "count": count,
        "tags": tags[:8],
    }, body_offset


def is_clean_skill_tag_name(value: str) -> bool:
    if not value or len(value) > 180:
        return False
    if any(ord(ch) < 32 or ord(ch) == 0xFFFD for ch in value):
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9_./#:+-]+", value))


def is_clean_skill_identifier_string(value: str) -> bool:
    if value == "":
        return True
    if len(value) > 180:
        return False
    if any(ord(ch) < 32 or ord(ch) == 0xFFFD for ch in value):
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9_./#:+-]+", value))


def read_skill_hint_shape_data(data: bytes, offset: int) -> tuple[dict[str, Any], int]:
    start = offset
    if offset >= len(data):
        raise ValueError("uiRangeHint.shapeData:truncated-member-count")
    member_count = data[offset]
    offset += 1
    if member_count != SKILL_HINT_SHAPE_MEMBER_COUNT:
        raise ValueError(f"uiRangeHint.shapeData.memberCount={member_count}")

    angle, offset = read_skill_f32_field(data, offset, "uiRangeHint.shapeData.angle")
    angle_key, offset = read_skill_clean_string_field(data, offset, "uiRangeHint.shapeData.angleKey")
    center_base_is_end_point, offset = read_skill_bool_field(
        data,
        offset,
        "uiRangeHint.shapeData.centerBaseIsEndPoint",
    )
    center_offset, offset = read_skill_vector2_field(data, offset, "uiRangeHint.shapeData.centerOffset")
    center_offset_x_key, offset = read_skill_clean_string_field(
        data,
        offset,
        "uiRangeHint.shapeData.centerOffsetXKey",
    )
    center_offset_z_key, offset = read_skill_clean_string_field(
        data,
        offset,
        "uiRangeHint.shapeData.centerOffsetZKey",
    )
    extent, offset = read_skill_vector2_field(data, offset, "uiRangeHint.shapeData.extent")
    extent_x_key, offset = read_skill_clean_string_field(data, offset, "uiRangeHint.shapeData.extentXKey")
    extent_z_key, offset = read_skill_clean_string_field(data, offset, "uiRangeHint.shapeData.extentZKey")
    fixed_extent, offset = read_skill_bool_field(data, offset, "uiRangeHint.shapeData.fixedExtent")
    radius, offset = read_skill_f32_field(data, offset, "uiRangeHint.shapeData.radius")
    radius_key, offset = read_skill_clean_string_field(data, offset, "uiRangeHint.shapeData.radiusKey")
    restrict_end_point_in_range, offset = read_skill_bool_field(
        data,
        offset,
        "uiRangeHint.shapeData.restrictEndPointInRange",
    )
    shape, offset = read_skill_i32_field(data, offset, "uiRangeHint.shapeData.shape")
    if shape < 0 or shape > 16:
        raise ValueError(f"uiRangeHint.shapeData.shape={shape}")
    use_angle_key, offset = read_skill_bool_field(data, offset, "uiRangeHint.shapeData.useAngleKey")
    use_center_offset_key, offset = read_skill_bool_field(
        data,
        offset,
        "uiRangeHint.shapeData.useCenterOffsetKey",
    )
    use_extent_key, offset = read_skill_bool_field(data, offset, "uiRangeHint.shapeData.useExtentKey")
    use_radius_key, offset = read_skill_bool_field(data, offset, "uiRangeHint.shapeData.useRadiusKey")
    use_width_key, offset = read_skill_bool_field(data, offset, "uiRangeHint.shapeData.useWidthKey")
    width, offset = read_skill_f32_field(data, offset, "uiRangeHint.shapeData.width")
    width_key, offset = read_skill_clean_string_field(data, offset, "uiRangeHint.shapeData.widthKey")

    return {
        "offset": format_offset(start),
        "memberCount": member_count,
        "byteLength": offset - start,
        "angle": round(angle, 6),
        "angleKey": angle_key,
        "centerBaseIsEndPoint": center_base_is_end_point,
        "centerOffset": center_offset,
        "centerOffsetXKey": center_offset_x_key,
        "centerOffsetZKey": center_offset_z_key,
        "extent": extent,
        "extentXKey": extent_x_key,
        "extentZKey": extent_z_key,
        "fixedExtent": fixed_extent,
        "radius": round(radius, 6),
        "radiusKey": radius_key,
        "restrictEndPointInRange": restrict_end_point_in_range,
        "shapeRaw": shape,
        "shapeName": SKILL_HINT_SHAPE_NAMES.get(shape, f"shape_{shape}"),
        "useAngleKey": use_angle_key,
        "useCenterOffsetKey": use_center_offset_key,
        "useExtentKey": use_extent_key,
        "useRadiusKey": use_radius_key,
        "useWidthKey": use_width_key,
        "width": round(width, 6),
        "widthKey": width_key,
    }, offset


def read_skill_ui_range_hint_data(
    data: bytes,
    offset: int,
    index: int,
) -> tuple[dict[str, Any], int]:
    start = offset
    if offset >= len(data):
        raise ValueError(f"uiRangeHints[{index}]:truncated-member-count")
    member_count = data[offset]
    offset += 1
    if member_count != SKILL_UI_RANGE_HINT_MEMBER_COUNT:
        raise ValueError(f"uiRangeHints[{index}].memberCount={member_count}")
    select_all, offset = read_skill_bool_field(data, offset, f"uiRangeHints[{index}].selectAll")
    shape_data, offset = read_skill_hint_shape_data(data, offset)
    target_faction, offset = read_skill_i32_field(data, offset, f"uiRangeHints[{index}].targetFaction")
    if target_faction < 0 or target_faction > 16:
        raise ValueError(f"uiRangeHints[{index}].targetFaction={target_faction}")
    return {
        "index": index,
        "offset": format_offset(start),
        "memberCount": member_count,
        "byteLength": offset - start,
        "selectAll": select_all,
        "shapeData": shape_data,
        "targetFactionRaw": target_faction,
    }, offset


SKILL_COMPARE_TYPE_NAMES = {
    0: "LT",
    1: "LE",
    2: "GT",
    3: "GE",
    4: "Equals",
}


def read_skill_assign_pair_data(
    data: bytes,
    offset: int,
    field_name: str,
) -> tuple[dict[str, Any], int]:
    start = offset
    if offset >= len(data):
        raise ValueError(f"{field_name}:truncated-member-count")
    member_count = data[offset]
    offset += 1
    if member_count != 6:
        raise ValueError(f"{field_name}:member-count={member_count}")

    direct_value_type, offset = read_buff_u32_field(data, offset, f"{field_name}.directValueType")
    input_value_key, offset = read_skill_clean_string_field(
        data,
        offset,
        f"{field_name}.inputValueKey",
        max_length=256,
    )
    numeric_value, offset = read_skill_f32_field(data, offset, f"{field_name}.numericValue")
    string_value, offset = read_skill_clean_string_field(
        data,
        offset,
        f"{field_name}.stringValue",
        max_length=256,
    )
    target_key, offset = read_skill_clean_string_field(
        data,
        offset,
        f"{field_name}.targetKey",
        max_length=256,
    )
    use_direct_value, offset = read_skill_bool_field(data, offset, f"{field_name}.useDirectValue")

    return {
        "offset": format_offset(start),
        "memberCount": member_count,
        "directValueTypeRaw": direct_value_type,
        "inputValueKey": input_value_key,
        "numericValue": round(numeric_value, 6),
        "stringValue": string_value,
        "targetKey": target_key,
        "useDirectValue": use_direct_value,
        "byteLength": offset - start,
    }, offset


def read_skill_buff_input_data(
    data: bytes,
    offset: int,
    index: int,
    field_name: str = "toggleBuffs.buffs",
) -> tuple[dict[str, Any], int]:
    item_name = f"{field_name}[{index}]"
    start = offset
    if offset >= len(data):
        raise ValueError(f"{item_name}:truncated-member-count")
    member_count = data[offset]
    offset += 1
    if member_count != 3:
        raise ValueError(f"{item_name}:member-count={member_count}")

    assign_blackboard, offset = read_skill_bool_field(
        data,
        offset,
        f"{item_name}.assignBlackboard",
    )
    assign_items_count, offset = read_buff_u32_field(
        data,
        offset,
        f"{item_name}.assignItemsCount",
    )
    if assign_items_count > 32:
        raise ValueError(f"{item_name}.assignItemsCount:large-count={assign_items_count}")

    assign_items: list[dict[str, Any]] = []
    for item_index in range(assign_items_count):
        assign_item, offset = read_skill_assign_pair_data(
            data,
            offset,
            f"{item_name}.assignItems[{item_index}]",
        )
        assign_items.append(assign_item)

    buff_id, offset = read_skill_clean_string_field(
        data,
        offset,
        f"{item_name}.buffId",
        max_length=256,
    )
    if not buff_id.startswith("buff_"):
        raise ValueError(f"{item_name}.buffId:unexpected={buff_id!r}")

    return {
        "offset": format_offset(start),
        "memberCount": member_count,
        "assignBlackboard": assign_blackboard,
        "assignItemsCount": assign_items_count,
        "assignItems": assign_items[:8],
        "buffId": buff_id,
        "byteLength": offset - start,
    }, offset


def read_skill_toggle_condition_data(
    data: bytes,
    offset: int,
    index: int,
) -> tuple[dict[str, Any], int]:
    start = offset
    condition_kind, offset = read_skill_u8_field(
        data,
        offset,
        f"toggleBuffs.conditions[{index}].kind",
        max_value=16,
    )
    if condition_kind != 1:
        raise ValueError(f"toggleBuffs.conditions[{index}].kind={condition_kind}")
    member_count, offset = read_skill_u8_field(
        data,
        offset,
        f"toggleBuffs.conditions[{index}].memberCount",
        max_value=16,
    )
    if member_count != 2:
        raise ValueError(f"toggleBuffs.conditions[{index}].member-count={member_count}")

    compare_raw, offset = read_buff_u32_field(data, offset, f"toggleBuffs.conditions[{index}].compare")
    if compare_raw > 16:
        raise ValueError(f"toggleBuffs.conditions[{index}].compare:raw={compare_raw}")
    value, offset = read_buff_blackboard_float_field(
        data,
        offset,
        f"toggleBuffs.conditions[{index}].value",
    )

    return {
        "offset": format_offset(start),
        "kindRaw": condition_kind,
        "kindName": "compareBlackboardValue",
        "memberCount": member_count,
        "compareRaw": compare_raw,
        "compareName": SKILL_COMPARE_TYPE_NAMES.get(compare_raw, f"compare_{compare_raw}"),
        "value": value,
        "byteLength": offset - start,
    }, offset


def read_skill_toggle_buff_data(
    data: bytes,
    offset: int,
    index: int,
) -> tuple[dict[str, Any], int]:
    start = offset
    if offset >= len(data):
        raise ValueError(f"toggleBuffs[{index}]:truncated-member-count")
    member_count = data[offset]
    offset += 1
    if member_count != 2:
        raise ValueError(f"toggleBuffs[{index}]:member-count={member_count}")

    buffs_count, offset = read_buff_u32_field(data, offset, f"toggleBuffs[{index}].buffsCount")
    if buffs_count > 32:
        raise ValueError(f"toggleBuffs[{index}].buffsCount:large-count={buffs_count}")
    buffs: list[dict[str, Any]] = []
    for buff_index in range(buffs_count):
        buff, offset = read_skill_buff_input_data(data, offset, buff_index)
        buffs.append(buff)

    conditions_count, offset = read_buff_u32_field(data, offset, f"toggleBuffs[{index}].conditionsCount")
    if conditions_count > 32:
        raise ValueError(f"toggleBuffs[{index}].conditionsCount:large-count={conditions_count}")
    conditions: list[dict[str, Any]] = []
    for condition_index in range(conditions_count):
        condition, offset = read_skill_toggle_condition_data(data, offset, condition_index)
        conditions.append(condition)

    return {
        "offset": format_offset(start),
        "memberCount": member_count,
        "metadataFieldOrder": ["buffs", "conditions"],
        "buffsCount": buffs_count,
        "buffs": buffs[:8],
        "conditionsCount": conditions_count,
        "conditions": conditions[:8],
        "byteLength": offset - start,
    }, offset


def decode_skill_post_switch_tail_at(
    data: bytes,
    switch_end: int,
    switch_config_byte_length: int,
    boundary_status: str,
) -> dict[str, Any]:
    offset = switch_end
    try:
        if switch_end > len(data):
            raise ValueError("switch-config-boundary:truncated")
        switch_to_center, offset = read_skill_bool_field(
            data,
            offset,
            "switchToCenterBeforeCast",
        )
        tag_during_attach, offset = read_skill_gameplay_tag_list_field(
            data,
            offset,
            "tagDuringAttach",
        )
        toggle_buffs_count, offset = read_buff_u32_field(data, offset, "toggleBuffsCount")
        if toggle_buffs_count > 256:
            raise ValueError(f"toggleBuffsCount:large-count={toggle_buffs_count}")

        result: dict[str, Any] = {
            "status": "parsed-through-toggleBuffsCount",
            "source": (
                "validated SwitchToBuffConfig boundary plus final SkillData tail fields; "
                "UIRangeHintData and toggleBuffs branches require exact file-end handoff"
            ),
            "offset": format_offset(switch_end),
            "switchToBuffConfigByteLength": switch_config_byte_length,
            "switchToBuffConfigBoundaryStatus": boundary_status,
            "switchToCenterBeforeCast": switch_to_center,
            "tagDuringAttach": tag_during_attach,
            "toggleBuffsCount": toggle_buffs_count,
            "endOffset": format_offset(offset),
        }
        toggle_buffs: list[dict[str, Any]] = []
        for index in range(toggle_buffs_count):
            toggle_buff, offset = read_skill_toggle_buff_data(data, offset, index)
            toggle_buffs.append(toggle_buff)
        if toggle_buffs:
            result["toggleBuffs"] = toggle_buffs[:8]

        ui_range_hints_count, offset = read_buff_u32_field(data, offset, "uiRangeHintsCount")
        if ui_range_hints_count > 32:
            raise ValueError(f"uiRangeHintsCount:large-count={ui_range_hints_count}")
        ui_range_hints: list[dict[str, Any]] = []
        for index in range(ui_range_hints_count):
            hint, offset = read_skill_ui_range_hint_data(data, offset, index)
            ui_range_hints.append(hint)
        use_ai_exclusive_frame, offset = read_skill_bool_field(
            data,
            offset,
            "useAIExclusiveFrame",
        )
        result["status"] = "parsed-through-exact-tail"
        result["uiRangeHintsCount"] = ui_range_hints_count
        result["uiRangeHintsEncoding"] = "counted"
        result["uiRangeHints"] = ui_range_hints[:8]
        result["useAIExclusiveFrame"] = use_ai_exclusive_frame
        result["endOffset"] = format_offset(offset)
        result["exactLength"] = offset == len(data)
        if offset != len(data):
            raise ValueError(f"tail-not-exact={format_offset(offset)}")
        return result
    except (struct.error, UnicodeDecodeError, ValueError) as exc:
        return {
            "status": "parse-error",
            "offset": format_offset(offset),
            "switchToBuffConfigByteLength": switch_config_byte_length,
            "switchToBuffConfigBoundaryStatus": boundary_status,
            "error": str(exc),
        }


def decode_buff_memorypack(path: Path, data: bytes, size: int) -> dict[str, Any] | None:
    if not data or data[0] != BUFF_MEMBER_COUNT:
        return None
    schema = MEMORYPACK_FIELD_SCHEMAS.get("BuffData")
    if not schema:
        return None

    hits = scan_length_prefixed_utf8_string_hits(data, max_samples=192)
    strings = unique_strings([str(hit.get("value") or "") for hit in hits], 64)
    stem = path.stem
    id_marker_count, id_marker_offsets = length_prefixed_utf8_string_marker_info(data, stem)
    id_verified = id_marker_count > 0
    id_value = stem if id_verified else next((value for value in strings if value.startswith("buff_")), "")
    value_fields, complex_fields = buff_schema_field_groups(schema)
    post_id_prefix = decode_buff_post_id_prefix(data, id_value, id_marker_count, id_marker_offsets)

    tags = unique_strings(
        [value for value in strings if "/" in value and not value.startswith(("Assets/", "assets/"))],
        6,
    )
    params = unique_strings([value for value in strings if is_buff_param_string(value)], 8)
    refs = unique_strings(
        [
            value
            for value in strings
            if value != id_value and value.startswith(("buff_", "P_", "au_", "icon_"))
        ],
        6,
    )

    details = [
        f"id={id_value or 'unknown'}",
        "idString=verified" if id_verified else "idString=missing",
        f"strings={len(strings)}",
        f"idMarkers={id_marker_count}",
        f"typedFields={len(value_fields)}/{len(schema)}",
    ]
    if id_marker_offsets:
        details.append("idOffsets=" + format_offset_list(id_marker_offsets, id_marker_count))
    details.append("schemaTypes=" + ",".join(buff_schema_type_sample_parts()[:6]))
    post_id_sample = buff_post_id_prefix_sample(post_id_prefix)
    if post_id_sample:
        details.append("postId=" + post_id_sample)
    if tags:
        details.append("tags=" + ",".join(tags[:3]))
    if params:
        details.append("params=" + ",".join(params[:5]))
    if refs:
        details.append("refs=" + ",".join(refs[:3]))

    return {
        "kind": "memorypack-json",
        "subtype": "BuffData",
        "summary": (
            f"MemoryPack BuffData; object member count {BUFF_MEMBER_COUNT}; "
            f"id string {'verified' if id_verified else 'not found'}; "
            f"{len(strings)} sampled length-prefixed strings; "
            f"exact id markers {id_marker_count}; "
            f"field types recovered ({len(value_fields)} scalar/flag/id, "
            f"{len(complex_fields)} complex/list)"
            + (
                "; post-id tail parsed"
                if post_id_prefix.get("status") == "parsed-through-exact-tail"
                else (
                    "; post-id prefix parsed"
                    if str(post_id_prefix.get("status") or "").startswith("parsed-through")
                    else ""
                )
            )
        ),
        "rows": None,
        "keys": schema,
        "sample": "; ".join(details)[:STRING_SAMPLE_MAX_CHARS],
        "decoded": {
            "memberCount": BUFF_MEMBER_COUNT,
            "format": "memorypack",
            "schemaSource": MEMORYPACK_SCHEMA_SOURCE_NOTE,
            "decodedPreviewFields": [
                "id",
                "fieldTypes",
                "idMarkerOffsets",
                "postIdPrefix",
                "lengthPrefixedStrings",
            ],
            "id": id_value,
            "idStringVerified": id_verified,
            "idMarkerCount": id_marker_count,
            "idMarkerOffsets": [format_offset(offset) for offset in id_marker_offsets],
            "fieldTypes": BUFF_MEMORYPACK_FIELD_TYPES,
            "scalarFlagOrIdFields": value_fields,
            "complexOrListFields": complex_fields,
            "postIdPrefix": post_id_prefix,
            "stringCount": len(strings),
            "tags": tags,
            "params": params,
            "refs": refs,
            "stringHits": hits[:24],
            "exactLength": False,
        },
    }
