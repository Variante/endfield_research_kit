"""Focused MemoryPack decoder implementation extracted from the retired Data-page builder."""

from __future__ import annotations

import math
import struct
from collections import Counter
from pathlib import Path
from typing import Any

from .core import (
    MEMORYPACK_NULL_COUNT,
    MEMORYPACK_UNION_WIDE_TAG,
    STRING_SAMPLE_MAX_CHARS,
    format_offset,
    read_memorypack_bool,
    read_memorypack_f32,
    read_memorypack_i32,
    read_memorypack_u32_count,
    read_memorypack_utf8_string,
    require_memorypack_non_null_string,
)
from .schemas import MEMORYPACK_FIELD_SCHEMAS


INTERACTIVE_TEMPLATE_MEMBER_COUNT = 25


INTERACTIVE_TRIGGER_OBSERVER_COMPONENT_TAG = 0x00F3


INTERACTIVE_TRIGGER_OBSERVER_MEMBER_COUNT = 3


INTERACTIVE_COMMON_PERFORM_COMPONENT_TAG = 0x0067


INTERACTIVE_COMMON_PERFORM_MEMBER_COUNT = 3


INTERACTIVE_TRIGGER_ZONE_COMPONENT_TAG = 0x00F5


INTERACTIVE_TRIGGER_ZONE_MEMBER_COUNT = 3


INTERACTIVE_PERFORM_PROPERTY_ROW_MEMBER_COUNT = 3


INTERACTIVE_LOGIC_CONTROLLER_COMPONENT_TAG = 0x0078


INTERACTIVE_LOGIC_CONTROLLER_MEMBER_COUNT = 2


INTERACTIVE_HITTABLE_COMPONENT_TAG = 0x0055


INTERACTIVE_HITTABLE_MEMBER_COUNT = 3


INTERACTIVE_HITTABLE_COLLIDER_SHAPE_BLOB_LENGTH = 80


INTERACTIVE_AUDIO_COMPONENT_TAG = 0x005D


INTERACTIVE_AUDIO_MEMBER_COUNT = 2


INTERACTIVE_AUDIO_DATA_MEMBER_COUNT = 13


INTERACTIVE_SHOW_GUIDE_COMPONENT_TAGS = {
    0x00D2: "Core_ShowGuideComponentData",
    0x00D3: "Core_ShowGuideWithConditionComponentData",
}


INTERACTIVE_SHOW_GUIDE_MEMBER_COUNT = 5


INTERACTIVE_AUDIO_BOOL_FIELDS = [
    "openAudio",
    "useActiveStencil",
    "useAttackStencil",
    "useCollectStencil",
    "useCustomStencil",
    "useDestroyStencil",
    "useDynamicLevel",
    "useInteractStencil",
    "useRepairStencil",
    "useTiggerStencil",
    "useWorkStencil",
]


INTERACTIVE_PROPERTY_VALUE_STRING_TAIL_TYPES = {7, 8, 16, 28}


INTERACTIVE_PERFORM_PROPERTY_TYPE_NAMES = {
    0: "Int",
    1: "Float",
    2: "String",
    3: "Ulong",
    4: "Bool",
    5: "Trigger",
}


INTERACTIVE_AUDIO_TRIGGER_STATE_NAMES = {
    0: "Invalid",
    1: "EnterArea",
    2: "InArea",
    3: "LeaveArea",
    4: "StartUp",
    5: "Working",
    6: "Stop",
    7: "Idle",
    8: "Attack",
    9: "BeHit",
    10: "Broken",
    11: "Repairing",
    12: "RepairDone",
    13: "Destroy",
    14: "Collect",
    15: "CollectHit",
    16: "CollectDestroy",
    17: "Interact",
    18: "Active",
    19: "NotActive",
}


INTERACTIVE_SINGLE_PROPERTY_MAP_COMPONENT_TAGS = {
    0x0006,
    0x0019,
    0x001B,
    0x0022,
    0x0026,
    0x0027,
    0x002A,
    0x002C,
    0x002E,
    0x002F,
    0x0034,
    0x0035,
    0x003D,
    0x003F,
    0x0042,
    0x0044,
    0x0045,
    0x0049,
    0x004F,
    0x0055,
    0x0059,
    0x005A,
    0x0061,
    0x0064,
    0x0066,
    0x006B,
    0x006F,
    0x0070,
    0x0075,
    0x0077,
    0x007F,
    0x0083,
    0x0085,
    0x0086,
    0x0087,
    0x008D,
    0x008E,
    0x0092,
    0x009F,
    0x00A2,
    0x00AA,
    0x00BC,
    0x00C6,
    0x00D0,
    0x00D3,
    0x00D5,
    0x00D8,
    0x00DD,
    0x00DE,
    0x00DF,
    0x00E0,
    0x00E6,
    0x00EB,
    0x00ED,
    0x00EE,
    0x00F6,
    0x00F8,
    0x00F9,
    0x00FC,
}


INTERACTIVE_TEMPLATE_SCHEMA_SOURCE_NOTE = (
    "inherited field order recovered from IL2CPP template wrappers and byte-prefix validation"
)


BASE_COMPONENT_UNION_SOURCE_NOTE = (
    "BaseComponentData union formatter tags extracted from installed GameAssembly.dll"
)


BASE_COMPONENT_UNION_TAGS = {
    0x000C: "Core_AbilitySystemForIntData",
    0x0013: "Core_AttackTriggerComponentForIntData",
    0x0016: "Core_BaseControllerData",
    0x001B: "Core_BaseControllerData",
    0x0022: "Core_CanSetVisibleComponentData",
    0x001F: "Core_CharacterMovementComponentData",
    0x0023: "Core_ClickTriggerComponentForIntData",
    0x002C: "Core_CustomCurveMoveComponentData",
    0x0034: "Core_ElectricNodeComponentData",
    0x003D: "Core_ErosionSludgeCoreComponentData",
    0x0042: "Core_FactoryBuildingWrapperComponentData",
    0x0045: "Core_GameplayElectricityNodeComponentData",
    0x0049: "Core_HeightZeroMarkerComponentData",
    0x004A: "Core_FactoryGasComponentData",
    0x0055: "Core_HittableComponentForIntData",
    0x004F: "Core_InteractCommonTwoStateComponentData",
    0x005D: "Core_InteractiveAudioData",
    0x0059: "Core_InteractiveCommonMultiStateComponentData",
    0x005A: "Core_InteractCommonTwoStateComponentData",
    0x005B: "Core_InteractiveCoolerUnitComponentData",
    0x0061: "Core_InteractiveDoorCommonComponentData",
    0x0062: "Core_InteractiveBehitPerformComponentData",
    0x0067: "Core_InteractiveCommonPerformComponentData",
    0x0069: "Core_InteractiveCoreComponentData",
    0x006B: "Core_InteractiveManualMovePlatformComponentData",
    0x006C: "Core_InteractiveModelLevelUpComponentData",
    0x006F: "Core_InteractiveOutFallComponentData",
    0x0073: "Core_InteractiveRootComponentData",
    0x0075: "Core_InteractiveRunePointComponentData",
    0x0077: "Core_InteractiveSteamBlockerComponentData",
    0x0086: "Core_InteractiveWaterPipeComponentData",
    0x0087: "Core_InteractiveWaterSwitchComponentData",
    0x0078: "Core_InteractiveLogicControllerComponentData",
    0x0092: "Core_InteractiveVerticalRopeComponentData",
    0x009F: "Core_NavmeshDynamicBakeAreaComponentData",
    0x00A2: "Core_KeepRelativeOffsetComponentData",
    0x00AA: "Core_MovingPlatformComponentData",
    0x00D2: "Core_ShowGuideComponentData",
    0x00D3: "Core_ShowGuideWithConditionComponentData",
    0x00BD: "Core_SimpleAnimatorComponentData",
    0x00CE: "Core_StepOnTriggerComponentForIntData",
    0x00D9: "Core_SpaceshipCharacterWallData",
    0x00DB: "Core_TriggerZoneComponentForIntData",
    0x00DF: "Core_WaterProgressDriveCurveMovementComponentData",
    0x00E0: "Core_WaterVolHeightMarkerComponentData",
    0x00E6: "CraneContainerComponentData",
    0x00E7: "CraneTowerComponentData",
    0x00E9: "DungeonExitComponentData",
    0x00ED: "HiddenMarkComponentComponentData",
    0x00EE: "Core_TravelLinkEffectModelComponentData",
    0x00F3: "Core_TriggerObserverComponentData",
    0x00F5: "Core_TriggerZoneComponentForIntData",
    0x00F8: "InteractiveStainComponentData",
    0x00FC: "ScannableTraceComponentData",
    0x0108: "View_InteractiveModelComponentData",
    0x010A: "View_ModelComponentData",
    0x0126: "View_InteractiveModelComponentData",
}


def read_memorypack_union_tag(data: bytes, offset: int) -> tuple[int, int, int]:
    if offset >= len(data):
        raise ValueError("truncated-union-tag")
    first = data[offset]
    offset += 1
    if first == MEMORYPACK_UNION_WIDE_TAG:
        if offset + 2 > len(data):
            raise ValueError("truncated-wide-union-tag")
        tag = struct.unpack_from("<H", data, offset)[0]
        return tag, offset + 2, 3
    if first > MEMORYPACK_UNION_WIDE_TAG:
        raise ValueError(f"unsupported-union-tag-marker=0x{first:02x}")
    return first, offset, 1


def read_memorypack_i64(data: bytes, offset: int) -> tuple[int, int]:
    if offset + 8 > len(data):
        raise ValueError("truncated-int64")
    return struct.unpack_from("<q", data, offset)[0], offset + 8


def float_from_low_bits(value: int) -> float:
    return struct.unpack("<f", struct.pack("<I", value & 0xFFFFFFFF))[0]


def interactive_property_value_preview(
    value_type: int,
    value_bits: int,
    string_tail: str | None = None,
) -> int | float | bool | str | None:
    if value_type in INTERACTIVE_PROPERTY_VALUE_STRING_TAIL_TYPES:
        return string_tail
    if value_type == 1:
        return bool(value_bits)
    if value_type in (5, 11, 12):
        return round(float_from_low_bits(value_bits), 6)
    return value_bits


def parse_interactive_component_property_value(
    data: bytes,
    offset: int,
    field_name: str,
) -> tuple[dict[str, Any], int]:
    if offset >= len(data):
        raise ValueError(f"{field_name}.memberCount:truncated")
    member_count = data[offset]
    offset += 1
    if member_count != 2:
        raise ValueError(f"{field_name}.memberCount={member_count}")
    value_type, offset = read_memorypack_i32(data, offset)
    value_count, offset = read_memorypack_u32_count(
        data,
        offset,
        f"{field_name}.values",
        max_count=2048,
    )
    values: list[dict[str, Any]] = []
    tail_counts: Counter[int] = Counter()
    string_tail_counts: Counter[str] = Counter()
    for index in range(value_count):
        if offset >= len(data):
            raise ValueError(f"{field_name}.values[{index}].memberCount:truncated")
        item_member_count = data[offset]
        offset += 1
        if item_member_count != 2:
            raise ValueError(f"{field_name}.values[{index}].memberCount={item_member_count}")
        bits, offset = read_memorypack_i64(data, offset)
        string_tail: str | None = None
        tail: int | None = None
        if value_type in INTERACTIVE_PROPERTY_VALUE_STRING_TAIL_TYPES:
            string_tail, offset, string_error = read_memorypack_utf8_string(
                data,
                offset,
                max_length=1024,
            )
            if string_error:
                raise ValueError(f"{field_name}.values[{index}].stringTail:{string_error}")
            if string_tail is not None:
                string_tail_counts[string_tail] += 1
        else:
            tail, offset = read_memorypack_i32(data, offset)
            tail_counts[tail] += 1
        values.append({
            "valueBit64": bits,
            "floatFromLowBits": round(float_from_low_bits(bits), 6),
            "preview": interactive_property_value_preview(value_type, bits, string_tail),
            "tailInt": tail,
            "stringTail": string_tail,
        })
    return {
        "memberCount": member_count,
        "valueType": value_type,
        "valueCount": value_count,
        "values": values,
        "tailCounts": {str(key): count for key, count in tail_counts.most_common(8)},
        "stringTailCounts": dict(string_tail_counts.most_common(12)),
    }, offset


def parse_interactive_component_property_map(
    data: bytes,
    offset: int,
    field_name: str,
    *,
    max_entries: int = 4096,
    sample_limit: int = 16,
) -> tuple[dict[str, Any], int]:
    count, offset = read_memorypack_u32_count(data, offset, field_name, max_count=max_entries)
    rows: list[dict[str, Any]] = []
    key_counts: Counter[str] = Counter()
    value_type_counts: Counter[int] = Counter()
    value_count_counts: Counter[int] = Counter()
    tail_counts: Counter[int] = Counter()
    string_tail_counts: Counter[str] = Counter()
    for index in range(count):
        if offset >= len(data):
            raise ValueError(f"{field_name}[{index}].memberCount:truncated")
        member_count = data[offset]
        offset += 1
        if member_count != 2:
            raise ValueError(f"{field_name}[{index}].memberCount={member_count}")
        key, offset = require_memorypack_non_null_string(
            data,
            offset,
            f"{field_name}[{index}].key",
            max_length=256,
        )
        value, offset = parse_interactive_component_property_value(
            data,
            offset,
            f"{field_name}[{index}].value",
        )
        key_counts[key] += 1
        value_type_counts[int(value["valueType"])] += 1
        value_count_counts[int(value["valueCount"])] += 1
        for tail, tail_count in value["tailCounts"].items():
            tail_counts[int(tail)] += tail_count
        for string_tail, string_tail_count in (value.get("stringTailCounts") or {}).items():
            string_tail_counts[str(string_tail)] += int(string_tail_count)
        if len(rows) < sample_limit:
            rows.append({
                "key": key,
                "valueType": value["valueType"],
                "valueCount": value["valueCount"],
                "preview": [item["preview"] for item in value["values"][:12]],
                "values": value["values"][:12],
            })
    return {
        "count": count,
        "keys": list(key_counts),
        "keyCounts": dict(key_counts.most_common(24)),
        "valueTypeCounts": {str(key): count for key, count in value_type_counts.most_common(16)},
        "valueCountCounts": {str(key): count for key, count in value_count_counts.most_common(16)},
        "tailCounts": {str(key): count for key, count in tail_counts.most_common(16)},
        "stringTailCounts": dict(string_tail_counts.most_common(24)),
        "sampleRows": rows,
    }, offset


def interactive_property_preview_by_key(property_map: dict[str, Any]) -> dict[str, Any]:
    previews: dict[str, Any] = {}
    for row in property_map.get("sampleRows") or []:
        key = str(row.get("key") or "")
        values = row.get("preview") or []
        if not key:
            continue
        if len(values) == 1:
            previews[key] = values[0]
        else:
            previews[key] = values
    return previews


def parse_interactive_trigger_observer_component(
    data: bytes,
    offset: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    if member_count != INTERACTIVE_TRIGGER_OBSERVER_MEMBER_COUNT:
        raise ValueError(f"triggerObserver.memberCount={member_count}")
    start = offset
    maps: list[dict[str, Any]] = []
    for field_index in range(member_count):
        property_map, offset = parse_interactive_component_property_map(
            data,
            offset,
            f"triggerObserver.field{field_index}",
        )
        maps.append(property_map)
    primary = maps[0] if maps else {"sampleRows": []}
    previews = interactive_property_preview_by_key(primary)
    return {
        "type": BASE_COMPONENT_UNION_TAGS.get(INTERACTIVE_TRIGGER_OBSERVER_COMPONENT_TAG, ""),
        "memberCount": member_count,
        "byteLength": offset - start,
        "propertyMapCounts": [int(row.get("count") or 0) for row in maps],
        "primaryKeys": list((primary.get("keyCounts") or {}).keys()),
        "primaryValueTypeCounts": primary.get("valueTypeCounts") or {},
        "primaryValueCountCounts": primary.get("valueCountCounts") or {},
        "primaryTailCounts": primary.get("tailCounts") or {},
        "primaryPreviewByKey": previews,
        "sampleProperties": (primary.get("sampleRows") or [])[:12],
    }, offset


def parse_interactive_single_property_map_component(
    data: bytes,
    offset: int,
    tag: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    if member_count != 1:
        raise ValueError(f"singlePropertyMap.memberCount={member_count}")
    start = offset
    type_name = BASE_COMPONENT_UNION_TAGS.get(tag, f"tag_0x{tag:04x}")
    property_map, offset = parse_interactive_component_property_map(
        data,
        offset,
        f"{type_name}.field0",
    )
    previews = interactive_property_preview_by_key(property_map)
    return {
        "tag": f"0x{tag:04x}",
        "type": type_name,
        "memberCount": member_count,
        "byteLength": offset - start,
        "bodyShape": "singlePropertyMap",
        "schemaSource": (
            "one-member property-map body validated by exact map parse and next-union handoff "
            "across export_full InteractiveData first payloads"
        ),
        "propertyMapCount": int(property_map.get("count") or 0),
        "propertyKeys": list((property_map.get("keyCounts") or {}).keys()),
        "valueTypeCounts": property_map.get("valueTypeCounts") or {},
        "valueCountCounts": property_map.get("valueCountCounts") or {},
        "tailCounts": property_map.get("tailCounts") or {},
        "stringTailCounts": property_map.get("stringTailCounts") or {},
        "previewByKey": previews,
        "sampleProperties": (property_map.get("sampleRows") or [])[:16],
    }, offset


def parse_interactive_template_config_properties(
    data: bytes,
    offset: int,
) -> tuple[dict[str, Any], int]:
    """Decode the exact template fields through ``configProperties``.

    ``offset`` must be the proven end of the complete component list.  The
    serialized order comes from the current ForMemoryPack setters: five
    scalar lifecycle fields, two property maps, ``aoiRadiusType``, then the
    authored template config map.  Parsing every preceding field prevents a
    coincidental property-map-shaped byte range from being accepted.
    """

    start = offset
    delay_recycle_perform_time, offset = read_memorypack_f32(data, offset)
    delay_to_recycle_time, offset = read_memorypack_f32(data, offset)
    if offset >= len(data):
        raise ValueError("interactiveTemplate.enableBornFadeIn:truncated")
    enable_born_fade_in = data[offset]
    offset += 1
    if enable_born_fade_in not in (0, 1):
        raise ValueError(
            f"interactiveTemplate.enableBornFadeIn={enable_born_fade_in}"
        )
    fade_in_time, offset = read_memorypack_f32(data, offset)
    if offset >= len(data):
        raise ValueError("interactiveTemplate.sendDieEvent:truncated")
    send_die_event = data[offset]
    offset += 1
    if send_die_event not in (0, 1):
        raise ValueError(f"interactiveTemplate.sendDieEvent={send_die_event}")
    all_global, offset = parse_interactive_component_property_map(
        data, offset, "interactiveTemplate.allGlobalSaveProperties"
    )
    all_map, offset = parse_interactive_component_property_map(
        data, offset, "interactiveTemplate.allMapSaveProperties"
    )
    aoi_radius_type, offset = read_memorypack_i32(data, offset)
    config_offset = offset
    config, offset = parse_interactive_component_property_map(
        data,
        offset,
        "interactiveTemplate.configProperties",
        sample_limit=4096,
    )
    audio_rows: list[dict[str, Any]] = []
    for row in config.get("sampleRows") or []:
        values = [
            str(value.get("stringTail") or "").strip()
            for value in row.get("values") or []
            if str(value.get("stringTail") or "").strip().startswith("au_")
        ]
        if not values:
            continue
        audio_rows.append({
            "key": str(row.get("key") or ""),
            "events": values,
            "valueType": row.get("valueType"),
            "identityKind": (
                "rtpcParameter"
                if all(value.startswith("au_rtpc_") for value in values)
                else "wwiseEvent"
            ),
        })
    return {
        "byteLength": offset - start,
        "schemaSource": (
            "current InteractiveTemplateData ForMemoryPack setter order; "
            "all preceding scalar and property-map fields decoded exactly"
        ),
        "delayRecyclePerformTime": round(delay_recycle_perform_time, 6),
        "delayToRecycleTime": round(delay_to_recycle_time, 6),
        "enableBornFadeIn": bool(enable_born_fade_in),
        "fadeInTime": round(fade_in_time, 6),
        "sendDieEvent": bool(send_die_event),
        "allGlobalSavePropertyCount": int(all_global.get("count") or 0),
        "allMapSavePropertyCount": int(all_map.get("count") or 0),
        "aoiRadiusType": aoi_radius_type,
        "configPropertiesOffset": format_offset(config_offset),
        "configPropertiesEndOffset": format_offset(offset),
        "configPropertyCount": int(config.get("count") or 0),
        "configPropertyKeys": list(config.get("keys") or []),
        "audioPropertyRows": audio_rows,
    }, offset


def find_interactive_audio_property_maps(data: bytes) -> list[dict[str, Any]]:
    """Find complete typed property maps whose key explicitly denotes audio.

    This is intentionally narrower than a string scan.  A row is returned only
    when the enclosing MemoryPack property map parses completely and the
    selected key/value row contains a non-RTPC ``au_*`` identity.  The
    containing component remains unresolved unless another component decoder
    supplies it.
    """

    key_names = ("audio_key", "audio_key_start", "audio_key_loop", "audio_key_end", "hit_sound_event")
    candidate_ranges: set[tuple[int, int]] = set()
    rows: list[dict[str, Any]] = []
    for key_name in key_names:
        marker = struct.pack("<I", len(key_name)) + key_name.encode("utf-8")
        marker_offset = 0
        while True:
            marker_offset = data.find(marker, marker_offset)
            if marker_offset < 0:
                break
            search_start = max(0, marker_offset - 4096)
            matches: list[tuple[int, int, dict[str, Any]]] = []
            for property_offset in range(search_start, marker_offset + 1):
                try:
                    property_map, end = parse_interactive_component_property_map(
                        data,
                        property_offset,
                        "interactive.audioPropertyMap",
                        max_entries=256,
                    )
                except (UnicodeDecodeError, struct.error, ValueError):
                    continue
                if property_offset <= marker_offset < end and key_name in (property_map.get("keys") or []):
                    matches.append((property_offset, end, property_map))
            # A unique enclosing typed map is the fail-closed acceptance gate.
            unique = {(start, end): value for start, end, value in matches}
            if len(unique) == 1:
                (property_offset, end), property_map = next(iter(unique.items()))
                if (property_offset, end) not in candidate_ranges:
                    audio_rows: list[dict[str, Any]] = []
                    for row in property_map.get("sampleRows") or []:
                        key = str(row.get("key") or "")
                        if key not in key_names:
                            continue
                        values = [str(value) for value in (row.get("preview") or []) if value]
                        events = [
                            value for value in values
                            if value.startswith("au_") and not value.startswith("au_rtpc_")
                        ]
                        if events:
                            audio_rows.append({
                                "key": key,
                                "events": events,
                                "valueType": row.get("valueType"),
                                "identityKind": "wwiseEvent",
                            })
                    if audio_rows:
                        candidate_ranges.add((property_offset, end))
                        rows.append({
                            "propertyMapOffset": format_offset(property_offset),
                            "propertyMapEndOffset": format_offset(end),
                            "propertyMapCount": int(property_map.get("count") or 0),
                            "propertyKeys": list(property_map.get("keys") or []),
                            "audioPropertyRows": audio_rows,
                            "componentResolutionStatus": "containingComponentUnresolved",
                            "runtimePropertyConsumerStatus": "unresolved",
                            "runtimeEventPostingStatus": "notObserved",
                        })
            marker_offset += 1
    rows.sort(key=lambda row: int(str(row["propertyMapOffset"]), 16))
    return rows


def parse_interactive_trigger_zone_audio_property_component(
    data: bytes,
    offset: int,
    member_count: int,
    *,
    max_scan_bytes: int = 16_384,
) -> tuple[dict[str, Any], int]:
    """Recover the exact audio-key property map from the current 0x00f5 body.

    The generated formatter and current files establish three serialized
    members.  The first is nullable and the second is a list whose current
    rows have 20 members, but their individual field schema is still opaque.
    Do not guess that schema.  Instead, accept an audio property map only when
    it is the unique complete MemoryPack map after that prefix and its end is
    also a syntactically valid next-component union handoff.
    """

    if member_count != INTERACTIVE_TRIGGER_ZONE_MEMBER_COUNT:
        raise ValueError(f"triggerZone.memberCount={member_count}")
    start = offset
    if offset + 9 > len(data):
        raise ValueError("triggerZone.prefix:truncated")
    nullable_first = struct.unpack_from("<I", data, offset)[0]
    if nullable_first != MEMORYPACK_NULL_COUNT:
        raise ValueError(f"triggerZone.field0.count={nullable_first}")
    second_count = struct.unpack_from("<I", data, offset + 4)[0]
    if second_count == MEMORYPACK_NULL_COUNT or second_count <= 0 or second_count > 256:
        raise ValueError(f"triggerZone.field1.count={second_count}")
    if data[offset + 8] != 20:
        raise ValueError(f"triggerZone.field1.firstMemberCount={data[offset + 8]}")

    candidates: list[tuple[int, int, dict[str, Any], list[dict[str, Any]]]] = []
    scan_end = min(len(data) - 1, offset + max_scan_bytes)
    for candidate_offset in range(offset + 9, scan_end):
        try:
            property_map, end = parse_interactive_component_property_map(
                data,
                candidate_offset,
                "triggerZone.audioPropertyMap",
                max_entries=256,
            )
        except (UnicodeDecodeError, struct.error, ValueError):
            continue
        audio_rows: list[dict[str, Any]] = []
        for row in property_map.get("sampleRows") or []:
            key = str(row.get("key") or "")
            if not key.startswith("audio_key"):
                continue
            values = [str(value) for value in (row.get("preview") or []) if value]
            if not values or any(not value.startswith("au_") for value in values):
                continue
            audio_rows.append({
                "key": key,
                "events": values,
                "valueType": row.get("valueType"),
                "identityKind": (
                    "rtpcParameter"
                    if all(value.startswith("au_rtpc_") for value in values)
                    else "wwiseEvent"
                ),
            })
        if not audio_rows:
            continue
        try:
            next_tag, next_offset, _tag_width = read_memorypack_union_tag(data, end)
        except (struct.error, ValueError):
            continue
        if next_offset >= len(data):
            continue
        next_member_count = data[next_offset]
        if next_member_count > 64:
            continue
        if next_tag != 0 and next_tag not in BASE_COMPONENT_UNION_TAGS:
            continue
        candidates.append((candidate_offset, end, property_map, audio_rows))

    if len(candidates) != 1:
        raise ValueError(f"triggerZone.audioPropertyMapCandidates={len(candidates)}")
    property_offset, end, property_map, audio_rows = candidates[0]
    return {
        "tag": f"0x{INTERACTIVE_TRIGGER_ZONE_COMPONENT_TAG:04x}",
        "type": BASE_COMPONENT_UNION_TAGS.get(INTERACTIVE_TRIGGER_ZONE_COMPONENT_TAG, ""),
        "memberCount": member_count,
        "byteLength": end - start,
        "bodyShape": "opaqueNullableAndListPrefixThenExactAudioPropertyMap",
        "schemaSource": (
            "current generated MemoryPack formatter proves three members; the first two remain opaque; "
            "the audio property map is selected uniquely by a complete typed map parse and exact next-union handoff"
        ),
        "opaquePrefixByteLength": property_offset - start,
        "propertyMapOffset": format_offset(property_offset),
        "propertyMapCount": int(property_map.get("count") or 0),
        "propertyKeys": list((property_map.get("keyCounts") or {}).keys()),
        "audioPropertyRows": audio_rows,
        "runtimePropertyConsumerStatus": "unresolved",
        "runtimeEventPostingStatus": "notObserved",
    }, end


def parse_interactive_common_perform_component(
    data: bytes,
    offset: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    if member_count != INTERACTIVE_COMMON_PERFORM_MEMBER_COUNT:
        raise ValueError(f"commonPerform.memberCount={member_count}")
    start = offset
    property_map, offset = parse_interactive_component_property_map(
        data,
        offset,
        "commonPerform.dynamicPropertyMap",
    )
    previews = interactive_property_preview_by_key(property_map)

    perform_property_count, offset = read_memorypack_u32_count(
        data,
        offset,
        "commonPerform.propertyDataList",
        max_count=4096,
    )
    rows: list[dict[str, Any]] = []
    property_name_counts: Counter[str] = Counter()
    property_type_counts: Counter[int] = Counter()
    property_type_name_counts: Counter[str] = Counter()
    is_property_counts: Counter[bool] = Counter()
    for row_index in range(perform_property_count):
        if offset >= len(data):
            raise ValueError(f"commonPerform.propertyDataList[{row_index}].memberCount:truncated")
        row_member_count = data[offset]
        offset += 1
        if row_member_count != INTERACTIVE_PERFORM_PROPERTY_ROW_MEMBER_COUNT:
            raise ValueError(
                f"commonPerform.propertyDataList[{row_index}].memberCount={row_member_count}"
            )
        if offset >= len(data):
            raise ValueError(f"commonPerform.propertyDataList[{row_index}].isProperty:truncated")
        is_property_byte = data[offset]
        if is_property_byte not in (0, 1):
            raise ValueError(
                f"commonPerform.propertyDataList[{row_index}].isProperty.byte={is_property_byte}"
            )
        is_property, offset = read_memorypack_bool(data, offset)
        property_name, offset = require_memorypack_non_null_string(
            data,
            offset,
            f"commonPerform.propertyDataList[{row_index}].propertyName",
            max_length=256,
        )
        property_type, offset = read_memorypack_i32(data, offset)
        property_type_name = INTERACTIVE_PERFORM_PROPERTY_TYPE_NAMES.get(
            property_type,
            f"type_{property_type}",
        )
        property_name_counts[property_name] += 1
        property_type_counts[property_type] += 1
        property_type_name_counts[property_type_name] += 1
        is_property_counts[is_property] += 1
        if len(rows) < 24:
            rows.append({
                "memberCount": row_member_count,
                "propertyName": property_name,
                "propertyType": property_type,
                "propertyTypeName": property_type_name,
                "isProperty": is_property,
            })

    if offset >= len(data):
        raise ValueError("commonPerform.syncGameplayLock:truncated")
    sync_gameplay_lock_byte = data[offset]
    if sync_gameplay_lock_byte not in (0, 1):
        raise ValueError(f"commonPerform.syncGameplayLock.byte={sync_gameplay_lock_byte}")
    sync_gameplay_lock, offset = read_memorypack_bool(data, offset)

    return {
        "tag": f"0x{INTERACTIVE_COMMON_PERFORM_COMPONENT_TAG:04x}",
        "type": BASE_COMPONENT_UNION_TAGS.get(INTERACTIVE_COMMON_PERFORM_COMPONENT_TAG, ""),
        "memberCount": member_count,
        "byteLength": offset - start,
        "bodyShape": "dynamicPropertyMapPerformPropertyListAndLockFlag",
        "schemaSource": (
            "component fields identified from local IL2CPP metadata; custom MemoryPack row byte order "
            "validated as bool, string, int32 by exact next-component handoff across export_full InteractiveData"
        ),
        "dynamicPropertyMapCount": int(property_map.get("count") or 0),
        "dynamicPropertyKeys": list((property_map.get("keyCounts") or {}).keys()),
        "dynamicPropertyValueTypeCounts": property_map.get("valueTypeCounts") or {},
        "dynamicPropertyValueCountCounts": property_map.get("valueCountCounts") or {},
        "dynamicPropertyTailCounts": property_map.get("tailCounts") or {},
        "dynamicPropertyStringTailCounts": property_map.get("stringTailCounts") or {},
        "dynamicPreviewByKey": previews,
        "sampleDynamicProperties": (property_map.get("sampleRows") or [])[:16],
        "performPropertyCount": perform_property_count,
        "performPropertyNameCounts": dict(property_name_counts.most_common(32)),
        "performPropertyTypeCounts": {str(key): count for key, count in property_type_counts.most_common(16)},
        "performPropertyTypeNameCounts": dict(property_type_name_counts.most_common(16)),
        "performPropertyIsPropertyCounts": {str(key): count for key, count in is_property_counts.most_common(4)},
        "samplePerformProperties": rows,
        "syncGameplayLock": sync_gameplay_lock,
        "syncGameplayLockByte": sync_gameplay_lock_byte,
    }, offset


def parse_interactive_hittable_component(
    data: bytes,
    offset: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    if member_count != INTERACTIVE_HITTABLE_MEMBER_COUNT:
        raise ValueError(f"hittable.memberCount={member_count}")
    start = offset
    property_map, offset = parse_interactive_component_property_map(
        data,
        offset,
        "hittable.propertyData",
    )
    previews = interactive_property_preview_by_key(property_map)

    collider_start = offset
    collider_end = collider_start + INTERACTIVE_HITTABLE_COLLIDER_SHAPE_BLOB_LENGTH
    if collider_end + 4 > len(data):
        raise ValueError("hittable.colliderShapeData:truncated")
    collider_blob = data[collider_start:collider_end]
    collider_member_count = collider_blob[0] if collider_blob else None
    if collider_member_count != 16:
        raise ValueError(f"hittable.colliderShapeData.memberCount={collider_member_count}")
    if collider_blob.count(b"\xff\xff\xff\xff") < 4:
        raise ValueError("hittable.colliderShapeData.nullMarkersLow")
    offset = collider_end

    enable_extra_check_bytes = data[offset:offset + 4]
    offset += 4
    if enable_extra_check_bytes[:3] != b"\x00\x00\x00" or enable_extra_check_bytes[3] not in (0, 1):
        raise ValueError(f"hittable.enableExtraCheck.bytes={enable_extra_check_bytes.hex()}")
    enable_extra_check = bool(enable_extra_check_bytes[3])

    return {
        "tag": f"0x{INTERACTIVE_HITTABLE_COMPONENT_TAG:04x}",
        "type": BASE_COMPONENT_UNION_TAGS.get(INTERACTIVE_HITTABLE_COMPONENT_TAG, ""),
        "memberCount": member_count,
        "byteLength": offset - start,
        "bodyShape": "propertyMapColliderShapeAndFlag",
        "schemaSource": (
            "fields recovered from local IL2CPP metadata; shared property map, fixed-size "
            "ColliderShapeData blob, and trailing enableExtraCheck flag validated by next-component handoff"
        ),
        "propertyMapCount": int(property_map.get("count") or 0),
        "propertyKeys": list((property_map.get("keyCounts") or {}).keys()),
        "valueTypeCounts": property_map.get("valueTypeCounts") or {},
        "valueCountCounts": property_map.get("valueCountCounts") or {},
        "tailCounts": property_map.get("tailCounts") or {},
        "previewByKey": previews,
        "sampleProperties": (property_map.get("sampleRows") or [])[:16],
        "colliderShapeDataMemberCount": collider_member_count,
        "colliderShapeDataByteLength": INTERACTIVE_HITTABLE_COLLIDER_SHAPE_BLOB_LENGTH,
        "colliderShapeDataNullMarkerCount": collider_blob.count(b"\xff\xff\xff\xff"),
        "colliderShapeDataPrefixHex": collider_blob[:24].hex(),
        "enableExtraCheck": enable_extra_check,
        "enableExtraCheckBytes": enable_extra_check_bytes.hex(),
    }, offset


def parse_interactive_logic_controller_component(
    data: bytes,
    offset: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    if member_count != INTERACTIVE_LOGIC_CONTROLLER_MEMBER_COUNT:
        raise ValueError(f"logicController.memberCount={member_count}")
    start = offset
    logic_type, offset = read_memorypack_i32(data, offset)
    property_map, offset = parse_interactive_component_property_map(
        data,
        offset,
        "logicController.propertyList",
    )
    previews = interactive_property_preview_by_key(property_map)
    return {
        "tag": f"0x{INTERACTIVE_LOGIC_CONTROLLER_COMPONENT_TAG:04x}",
        "type": BASE_COMPONENT_UNION_TAGS.get(INTERACTIVE_LOGIC_CONTROLLER_COMPONENT_TAG, ""),
        "memberCount": member_count,
        "byteLength": offset - start,
        "bodyShape": "logicTypeAndPropertyMap",
        "schemaSource": (
            "field order recovered from local IL2CPP ForMemoryPack setters; "
            "propertyList body validated as the shared Interactive property-map grammar"
        ),
        "logicType": logic_type,
        "propertyMapCount": int(property_map.get("count") or 0),
        "propertyKeys": list((property_map.get("keyCounts") or {}).keys()),
        "valueTypeCounts": property_map.get("valueTypeCounts") or {},
        "valueCountCounts": property_map.get("valueCountCounts") or {},
        "tailCounts": property_map.get("tailCounts") or {},
        "previewByKey": previews,
        "sampleProperties": (property_map.get("sampleRows") or [])[:16],
    }, offset


def parse_interactive_audio_component(
    data: bytes,
    offset: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    if member_count != INTERACTIVE_AUDIO_MEMBER_COUNT:
        raise ValueError(f"interactiveAudio.memberCount={member_count}")
    start = offset
    prefix_count, offset = read_memorypack_u32_count(
        data,
        offset,
        "interactiveAudio.prefix",
        max_count=0,
    )
    if offset >= len(data):
        raise ValueError("interactiveAudio.audioData.memberCount:truncated")
    audio_data_member_count = data[offset]
    offset += 1
    if audio_data_member_count != INTERACTIVE_AUDIO_DATA_MEMBER_COUNT:
        raise ValueError(f"interactiveAudio.audioData.memberCount={audio_data_member_count}")

    audio_name_count, offset = read_memorypack_u32_count(
        data,
        offset,
        "interactiveAudio.audioNameDict",
        max_count=4096,
    )
    audio_rows: list[dict[str, Any]] = []
    state_counts: Counter[int] = Counter()
    state_name_counts: Counter[str] = Counter()
    audio_event_counts: Counter[str] = Counter()
    for row_index in range(audio_name_count):
        state, offset = read_memorypack_i32(data, offset)
        state_name = INTERACTIVE_AUDIO_TRIGGER_STATE_NAMES.get(state, f"state_{state}")
        state_counts[state] += 1
        state_name_counts[state_name] += 1
        event_count, offset = read_memorypack_u32_count(
            data,
            offset,
            f"interactiveAudio.audioNameDict[{row_index}].audio",
            max_count=4096,
        )
        events: list[str] = []
        for event_index in range(event_count):
            event, offset = require_memorypack_non_null_string(
                data,
                offset,
                f"interactiveAudio.audioNameDict[{row_index}].audio[{event_index}]",
                max_length=256,
            )
            events.append(event)
            audio_event_counts[event] += 1
        audio_rows.append({
            "state": state,
            "stateName": state_name,
            "audioCount": event_count,
            "events": events,
        })

    custom_audio_count, offset = read_memorypack_u32_count(
        data,
        offset,
        "interactiveAudio.customAudioData",
        max_count=4096,
    )
    custom_rows: list[dict[str, Any]] = []
    custom_name_counts: Counter[str] = Counter()
    custom_event_counts: Counter[str] = Counter()
    for row_index in range(custom_audio_count):
        if offset >= len(data):
            raise ValueError(f"interactiveAudio.customAudioData[{row_index}].memberCount:truncated")
        custom_member_count = data[offset]
        offset += 1
        if custom_member_count != 3:
            raise ValueError(f"interactiveAudio.customAudioData[{row_index}].memberCount={custom_member_count}")
        event, offset = require_memorypack_non_null_string(
            data,
            offset,
            f"interactiveAudio.customAudioData[{row_index}].event",
            max_length=256,
        )
        name, offset = require_memorypack_non_null_string(
            data,
            offset,
            f"interactiveAudio.customAudioData[{row_index}].name",
            max_length=256,
        )
        note, offset = require_memorypack_non_null_string(
            data,
            offset,
            f"interactiveAudio.customAudioData[{row_index}].note",
            max_length=512,
        )
        custom_name_counts[name] += 1
        custom_event_counts[event] += 1
        custom_rows.append({
            "event": event,
            "name": name,
            "note": note,
        })

    bools: dict[str, bool] = {}
    true_fields: list[str] = []
    for field_name in INTERACTIVE_AUDIO_BOOL_FIELDS:
        value, offset = read_memorypack_bool(data, offset)
        bools[field_name] = value
        if value:
            true_fields.append(field_name)

    return {
        "tag": f"0x{INTERACTIVE_AUDIO_COMPONENT_TAG:04x}",
        "type": BASE_COMPONENT_UNION_TAGS.get(INTERACTIVE_AUDIO_COMPONENT_TAG, ""),
        "memberCount": member_count,
        "byteLength": offset - start,
        "bodyShape": "audioComponentData",
        "schemaSource": (
            "field order recovered from full local IL2CPP metadata; audio dictionaries, "
            "custom audio rows, and boolean tail validated by component-list handoff"
        ),
        "prefixCount": prefix_count,
        "audioDataMemberCount": audio_data_member_count,
        "audioNameCount": audio_name_count,
        "customAudioCount": custom_audio_count,
        "stateCounts": {str(key): count for key, count in state_counts.most_common(24)},
        "stateNameCounts": dict(state_name_counts.most_common(24)),
        "audioEventCounts": dict(audio_event_counts.most_common(24)),
        "customNameCounts": dict(custom_name_counts.most_common(24)),
        "customEventCounts": dict(custom_event_counts.most_common(24)),
        "booleans": bools,
        "trueBooleanFields": true_fields,
        "audioRows": audio_rows,
        "customRows": custom_rows,
        "sampleAudioRows": audio_rows[:16],
        "sampleCustomRows": custom_rows[:16],
    }, offset


def read_memorypack_vector3_f32(data: bytes, offset: int, field_name: str) -> tuple[dict[str, float], int]:
    x, offset = read_memorypack_f32(data, offset)
    y, offset = read_memorypack_f32(data, offset)
    z, offset = read_memorypack_f32(data, offset)
    if not all(math.isfinite(value) for value in (x, y, z)):
        raise ValueError(f"{field_name}:non-finite")
    return {
        "x": round(x, 6),
        "y": round(y, 6),
        "z": round(z, 6),
    }, offset


def parse_interactive_show_guide_component(
    data: bytes,
    offset: int,
    tag: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    if tag not in INTERACTIVE_SHOW_GUIDE_COMPONENT_TAGS:
        raise ValueError(f"showGuide.tag=0x{tag:04x}")
    if member_count != INTERACTIVE_SHOW_GUIDE_MEMBER_COUNT:
        raise ValueError(f"showGuide.memberCount={member_count}")
    start = offset
    type_name = BASE_COMPONENT_UNION_TAGS.get(tag, INTERACTIVE_SHOW_GUIDE_COMPONENT_TAGS[tag])
    property_map, offset = parse_interactive_component_property_map(
        data,
        offset,
        f"{type_name}.propertyMap",
    )
    previews = interactive_property_preview_by_key(property_map)
    center, offset = read_memorypack_vector3_f32(data, offset, f"{type_name}.center")
    radius, offset = read_memorypack_f32(data, offset)
    if not math.isfinite(radius):
        raise ValueError(f"{type_name}.radius:non-finite")
    if offset >= len(data):
        raise ValueError(f"{type_name}.shape:truncated")
    shape = data[offset]
    offset += 1
    if shape not in (0, 1, 2):
        raise ValueError(f"{type_name}.shape={shape}")
    size, offset = read_memorypack_vector3_f32(data, offset, f"{type_name}.size")
    return {
        "tag": f"0x{tag:04x}",
        "type": type_name,
        "memberCount": member_count,
        "byteLength": offset - start,
        "bodyShape": "propertyMapCenterRadiusShapeAndSize",
        "schemaSource": (
            "five-member ShowGuide body inferred from local IL2CPP generated formatter metadata "
            "and validated as property map, Vector3 center, float radius, byte shape, Vector3 size "
            "by exact component-count and next-union handoffs across export_full InteractiveData"
        ),
        "propertyMapCount": int(property_map.get("count") or 0),
        "propertyKeys": list((property_map.get("keyCounts") or {}).keys()),
        "valueTypeCounts": property_map.get("valueTypeCounts") or {},
        "valueCountCounts": property_map.get("valueCountCounts") or {},
        "tailCounts": property_map.get("tailCounts") or {},
        "stringTailCounts": property_map.get("stringTailCounts") or {},
        "previewByKey": previews,
        "center": center,
        "radius": round(radius, 6),
        "shape": shape,
        "size": size,
        "sampleProperties": (property_map.get("sampleRows") or [])[:16],
    }, offset


def scan_memorypack_utf8_strings(
    data: bytes,
    offset: int,
    *,
    max_scan_bytes: int = 2048,
    max_samples: int = 8,
    max_length: int = 96,
) -> list[str]:
    end = min(len(data), offset + max_scan_bytes)
    samples: list[str] = []
    for pos in range(max(offset, 0), max(offset, end - 4)):
        length = struct.unpack_from("<I", data, pos)[0]
        if length <= 0 or length > max_length or pos + 4 + length > end:
            continue
        raw = data[pos + 4:pos + 4 + length]
        if not raw:
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if any(ord(ch) < 32 for ch in text):
            continue
        if not any(ch.isalnum() for ch in text):
            continue
        if text not in samples:
            samples.append(text)
            if len(samples) >= max_samples:
                break
    return samples


def read_memorypack_tag_list_prefix(
    data: bytes,
    offset: int,
    *,
    max_items: int = 32,
    allow_hash_only: bool = False,
) -> tuple[list[dict[str, Any]], int | None, int, str | None]:
    if offset + 4 > len(data):
        return [], None, offset, "truncated-count"
    raw_count = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    if raw_count == MEMORYPACK_NULL_COUNT:
        return [], None, offset, None
    if raw_count > max_items:
        return [], raw_count, offset, f"large-count={raw_count}"

    if allow_hash_only:
        hash_only_end = offset + raw_count * 4
        if hash_only_end + 4 <= len(data):
            following_count = struct.unpack_from("<I", data, hash_only_end)[0]
            if following_count == MEMORYPACK_NULL_COUNT or following_count <= 10_000:
                return [
                    {
                        "index": index,
                        "memberCount": None,
                        "hash": f"0x{struct.unpack_from('<I', data, offset + index * 4)[0]:08x}",
                        "tag": None,
                        "serialization": "hashOnly",
                    }
                    for index in range(raw_count)
                ], raw_count, hash_only_end, None

    tags: list[dict[str, Any]] = []
    for index in range(raw_count):
        if offset + 5 > len(data):
            return tags, raw_count, offset, "truncated-item"
        member_count = data[offset]
        offset += 1
        hash_value = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        tag, offset, err = read_memorypack_utf8_string(data, offset)
        tags.append({
            "index": index,
            "memberCount": member_count,
            "hash": f"0x{hash_value:08x}",
            "tag": tag,
        })
        if err:
            return tags, raw_count, offset, err
    return tags, raw_count, offset, None


def decode_interactive_template_memorypack(path: Path, data: bytes, size: int) -> dict[str, Any] | None:
    if not data or data[0] != INTERACTIVE_TEMPLATE_MEMBER_COUNT:
        return None

    offset = 1
    name, offset, name_error = read_memorypack_utf8_string(data, offset)
    if name_error or not name:
        return None
    if offset + 4 > len(data):
        return None
    faction_index = struct.unpack_from("<i", data, offset)[0]
    offset += 4
    object_type, offset, object_type_error = read_memorypack_utf8_string(data, offset)
    if object_type_error:
        return None

    born_tags, born_tag_count, offset, tag_error = read_memorypack_tag_list_prefix(
        data,
        offset,
        allow_hash_only=True,
    )
    component_count: int | None = None
    component_offset = offset
    first_component_tag: int | None = None
    first_component_type = ""
    first_component_member_count: int | None = None
    first_component_tag_width = 0
    first_component_end_offset: int | None = None
    second_component_tag: int | None = None
    second_component_type = ""
    second_component_member_count: int | None = None
    second_component_tag_width = 0
    second_component_end_offset: int | None = None
    model_component: dict[str, Any] | None = None
    component_prefix_rows: list[dict[str, Any]] = []
    component_prefix_parsed_count = 0
    component_prefix_end_offset: int | None = None
    first_payload_component: dict[str, Any] | None = None
    first_payload_body_end_offset: int | None = None
    trigger_observer_component: dict[str, Any] | None = None
    property_map_component: dict[str, Any] | None = None
    component_payload_parsed_count = 0
    component_payload_parsed_rows: list[dict[str, Any]] = []
    trigger_observer_components: list[dict[str, Any]] = []
    property_map_components: list[dict[str, Any]] = []
    common_perform_component: dict[str, Any] | None = None
    common_perform_components: list[dict[str, Any]] = []
    trigger_zone_audio_property_components: list[dict[str, Any]] = []
    logic_controller_component: dict[str, Any] | None = None
    logic_controller_components: list[dict[str, Any]] = []
    hittable_component: dict[str, Any] | None = None
    hittable_components: list[dict[str, Any]] = []
    audio_component: dict[str, Any] | None = None
    audio_components: list[dict[str, Any]] = []
    show_guide_component: dict[str, Any] | None = None
    show_guide_components: list[dict[str, Any]] = []
    component_stop_component: dict[str, Any] | None = None
    component_scan_offset: int | None = None
    template_config_properties: dict[str, Any] | None = None
    template_action_map_audio: dict[str, Any] | None = None
    component_string_samples: list[str] = []
    component_error: str | None = None

    def component_type_name(tag: int) -> str:
        return BASE_COMPONENT_UNION_TAGS.get(tag, f"tag_0x{tag:04x}")

    def component_row(
        index: int,
        tag: int,
        tag_width: int,
        member_count: int,
        payload_offset: int,
    ) -> dict[str, Any]:
        return {
            "index": index,
            "tag": f"0x{tag:04x}",
            "type": component_type_name(tag),
            "tagWidth": tag_width,
            "memberCount": member_count,
            "payloadOffset": format_offset(payload_offset),
        }

    if offset + 4 <= len(data):
        raw_component_count = struct.unpack_from("<I", data, offset)[0]
        if raw_component_count == MEMORYPACK_NULL_COUNT:
            component_count = None
            offset += 4
        elif raw_component_count <= 10_000:
            component_count = raw_component_count
            offset += 4
            component_cursor = offset
            if component_count:
                try:
                    first_component_tag, component_cursor, first_component_tag_width = read_memorypack_union_tag(
                        data,
                        component_cursor,
                    )
                    first_component_type = component_type_name(first_component_tag)
                    if component_cursor >= len(data):
                        raise ValueError("truncated-first-component-member-count")
                    first_component_member_count = data[component_cursor]
                    component_cursor += 1
                    first_component_end_offset = component_cursor
                    component_prefix_rows.append(
                        component_row(
                            0,
                            first_component_tag,
                            first_component_tag_width,
                            first_component_member_count,
                            component_cursor,
                        )
                    )
                    component_prefix_parsed_count = 1
                    component_prefix_end_offset = component_cursor
                    if component_count > 1:
                        second_component_tag, component_cursor, second_component_tag_width = read_memorypack_union_tag(
                            data,
                            component_cursor,
                        )
                        second_component_type = component_type_name(second_component_tag)
                        if component_cursor >= len(data):
                            raise ValueError("truncated-second-component-member-count")
                        second_component_member_count = data[component_cursor]
                        component_cursor += 1
                        if second_component_tag in (0x108, 0x10A, 0x126) and second_component_member_count == 4:
                            born_fade_in_time, component_cursor = read_memorypack_f32(data, component_cursor)
                            if component_cursor >= len(data):
                                raise ValueError("truncated-model-component-enable-born-fade-in")
                            enable_born_fade_in_byte = data[component_cursor]
                            component_cursor += 1
                            if enable_born_fade_in_byte not in (0, 1):
                                raise ValueError(
                                    f"invalid-model-component-enable-born-fade-in={enable_born_fade_in_byte}"
                                )
                            model_id, component_cursor, model_error = read_memorypack_utf8_string(
                                data,
                                component_cursor,
                                max_length=512,
                            )
                            if model_error:
                                raise ValueError(f"invalid-model-component-id={model_error}")
                            model_scale, component_cursor = read_memorypack_f32(data, component_cursor)
                            if not math.isfinite(born_fade_in_time) or not math.isfinite(model_scale):
                                raise ValueError("model-component-float-non-finite")
                            model_component = {
                                "tag": f"0x{second_component_tag:04x}",
                                "type": second_component_type,
                                "memberCount": second_component_member_count,
                                "bornFadeInTime": round(born_fade_in_time, 6),
                                "enableBornFadeIn": bool(enable_born_fade_in_byte),
                                "modelId": model_id,
                                "modelScale": round(model_scale, 6),
                            }
                            second_component_end_offset = component_cursor
                            component_prefix_rows.append({
                                **component_row(
                                    1,
                                    second_component_tag,
                                    second_component_tag_width,
                                    second_component_member_count,
                                    second_component_end_offset,
                                ),
                                "modelId": model_id,
                            })
                            component_prefix_parsed_count = 2
                            component_prefix_end_offset = component_cursor
                    if second_component_end_offset is not None:
                        component_cursor = second_component_end_offset
                        component_scan_offset = component_cursor
                        for component_index in range(2, component_count or 0):
                            tag, component_cursor, tag_width = read_memorypack_union_tag(data, component_cursor)
                            if component_cursor >= len(data):
                                raise ValueError(f"truncated-component-{component_index}-member-count")
                            member_count = data[component_cursor]
                            component_cursor += 1
                            row = component_row(component_index, tag, tag_width, member_count, component_cursor)
                            if member_count == 0:
                                row["parsedBody"] = "zero"
                                if first_payload_component is None:
                                    component_prefix_rows.append(row)
                                    component_prefix_parsed_count = component_index + 1
                                    component_prefix_end_offset = component_cursor
                                else:
                                    component_payload_parsed_count += 1
                                    component_payload_parsed_rows.append(row)
                                component_scan_offset = component_cursor
                                continue
                            if first_payload_component is None:
                                first_payload_component = row

                            parsed_body_end_offset: int | None = None
                            if (
                                tag == INTERACTIVE_TRIGGER_OBSERVER_COMPONENT_TAG
                                and member_count == INTERACTIVE_TRIGGER_OBSERVER_MEMBER_COUNT
                            ):
                                parsed_trigger_observer, parsed_body_end_offset = (
                                    parse_interactive_trigger_observer_component(
                                        data,
                                        component_cursor,
                                        member_count,
                                    )
                                )
                                row["byteLength"] = parsed_trigger_observer["byteLength"]
                                row["parsedBody"] = "propertyMaps"
                                if trigger_observer_component is None:
                                    trigger_observer_component = parsed_trigger_observer
                                trigger_observer_components.append({
                                    "index": component_index,
                                    **parsed_trigger_observer,
                                })
                            elif tag in INTERACTIVE_SINGLE_PROPERTY_MAP_COMPONENT_TAGS and member_count == 1:
                                parsed_property_map, parsed_body_end_offset = (
                                    parse_interactive_single_property_map_component(
                                        data,
                                        component_cursor,
                                        tag,
                                        member_count,
                                    )
                                )
                                row["byteLength"] = parsed_property_map["byteLength"]
                                row["parsedBody"] = "propertyMap"
                                if property_map_component is None:
                                    property_map_component = parsed_property_map
                                property_map_components.append({
                                    "index": component_index,
                                    **parsed_property_map,
                                })
                            elif (
                                tag == INTERACTIVE_COMMON_PERFORM_COMPONENT_TAG
                                and member_count == INTERACTIVE_COMMON_PERFORM_MEMBER_COUNT
                            ):
                                parsed_common_perform, parsed_body_end_offset = (
                                    parse_interactive_common_perform_component(
                                        data,
                                        component_cursor,
                                        member_count,
                                    )
                                )
                                row["byteLength"] = parsed_common_perform["byteLength"]
                                row["parsedBody"] = "commonPerformData"
                                row["performPropertyCount"] = parsed_common_perform["performPropertyCount"]
                                row["syncGameplayLock"] = parsed_common_perform["syncGameplayLock"]
                                if common_perform_component is None:
                                    common_perform_component = parsed_common_perform
                                common_perform_components.append({
                                    "index": component_index,
                                    **parsed_common_perform,
                                })
                            elif (
                                tag == INTERACTIVE_TRIGGER_ZONE_COMPONENT_TAG
                                and member_count == INTERACTIVE_TRIGGER_ZONE_MEMBER_COUNT
                            ):
                                parsed_trigger_zone, parsed_body_end_offset = (
                                    parse_interactive_trigger_zone_audio_property_component(
                                        data,
                                        component_cursor,
                                        member_count,
                                    )
                                )
                                row["byteLength"] = parsed_trigger_zone["byteLength"]
                                row["parsedBody"] = "targetedAudioPropertyMap"
                                row["audioPropertyCount"] = len(
                                    parsed_trigger_zone.get("audioPropertyRows") or []
                                )
                                trigger_zone_audio_property_components.append({
                                    "index": component_index,
                                    **parsed_trigger_zone,
                                })
                            elif (
                                tag == INTERACTIVE_HITTABLE_COMPONENT_TAG
                                and member_count == INTERACTIVE_HITTABLE_MEMBER_COUNT
                            ):
                                parsed_hittable, parsed_body_end_offset = parse_interactive_hittable_component(
                                    data,
                                    component_cursor,
                                    member_count,
                                )
                                row["byteLength"] = parsed_hittable["byteLength"]
                                row["parsedBody"] = "propertyMapColliderShapeAndFlag"
                                row["propertyMapCount"] = parsed_hittable["propertyMapCount"]
                                row["enableExtraCheck"] = parsed_hittable["enableExtraCheck"]
                                if hittable_component is None:
                                    hittable_component = parsed_hittable
                                hittable_components.append({
                                    "index": component_index,
                                    **parsed_hittable,
                                })
                            elif (
                                tag == INTERACTIVE_LOGIC_CONTROLLER_COMPONENT_TAG
                                and member_count == INTERACTIVE_LOGIC_CONTROLLER_MEMBER_COUNT
                            ):
                                parsed_logic_controller, parsed_body_end_offset = (
                                    parse_interactive_logic_controller_component(
                                        data,
                                        component_cursor,
                                        member_count,
                                    )
                                )
                                row["byteLength"] = parsed_logic_controller["byteLength"]
                                row["parsedBody"] = "logicTypeAndPropertyMap"
                                row["logicType"] = parsed_logic_controller["logicType"]
                                if logic_controller_component is None:
                                    logic_controller_component = parsed_logic_controller
                                logic_controller_components.append({
                                    "index": component_index,
                                    **parsed_logic_controller,
                                })
                            elif tag == INTERACTIVE_AUDIO_COMPONENT_TAG and member_count == INTERACTIVE_AUDIO_MEMBER_COUNT:
                                parsed_audio, parsed_body_end_offset = parse_interactive_audio_component(
                                    data,
                                    component_cursor,
                                    member_count,
                                )
                                row["byteLength"] = parsed_audio["byteLength"]
                                row["parsedBody"] = "audioComponentData"
                                row["audioNameCount"] = parsed_audio["audioNameCount"]
                                row["customAudioCount"] = parsed_audio["customAudioCount"]
                                if audio_component is None:
                                    audio_component = parsed_audio
                                audio_components.append({
                                    "index": component_index,
                                    **parsed_audio,
                                })
                            elif tag in INTERACTIVE_SHOW_GUIDE_COMPONENT_TAGS and member_count == INTERACTIVE_SHOW_GUIDE_MEMBER_COUNT:
                                parsed_show_guide, parsed_body_end_offset = parse_interactive_show_guide_component(
                                    data,
                                    component_cursor,
                                    tag,
                                    member_count,
                                )
                                row["byteLength"] = parsed_show_guide["byteLength"]
                                row["parsedBody"] = "showGuideBoundsData"
                                row["shape"] = parsed_show_guide["shape"]
                                if show_guide_component is None:
                                    show_guide_component = parsed_show_guide
                                show_guide_components.append({
                                    "index": component_index,
                                    **parsed_show_guide,
                                })
                            else:
                                component_stop_component = row
                                component_scan_offset = component_cursor
                                break

                            if parsed_body_end_offset is None:
                                raise ValueError(f"component-{component_index}-body-not-consumed")
                            if first_payload_component is row:
                                first_payload_body_end_offset = parsed_body_end_offset
                            component_payload_parsed_count += 1
                            component_payload_parsed_rows.append(row)
                            component_cursor = parsed_body_end_offset
                            component_scan_offset = component_cursor
                    if (
                        component_count is not None
                        and component_stop_component is None
                        and component_scan_offset is not None
                        and component_prefix_parsed_count + component_payload_parsed_count
                        == component_count
                    ):
                        template_config_properties, _template_config_end = (
                            parse_interactive_template_config_properties(
                                data,
                                component_scan_offset,
                            )
                        )
                        try:
                            from story_builder.levelscript_binary import (
                                decode_embedded_action_serialized_map_audio,
                            )
                        except ImportError:
                            from scripts.story_builder.levelscript_binary import (
                                decode_embedded_action_serialized_map_audio,
                            )
                        template_action_map_audio = (
                            decode_embedded_action_serialized_map_audio(
                                data,
                                _template_config_end,
                            )
                            or None
                        )
                    scan_offset = (
                        component_scan_offset
                        or first_payload_body_end_offset
                        or (
                            int(first_payload_component.get("payloadOffset", "0x0"), 16)
                            if first_payload_component
                            else component_prefix_end_offset or second_component_end_offset or first_component_end_offset or offset
                        )
                    )
                    component_string_samples = scan_memorypack_utf8_strings(data, scan_offset)
                except (UnicodeDecodeError, struct.error, ValueError) as exc:
                    component_error = str(exc)
                    component_string_samples = scan_memorypack_utf8_strings(data, offset)
        else:
            component_error = f"invalid-component-count={raw_component_count}"
    else:
        component_error = "truncated-component-count"

    category_tags = [
        str(row.get("tag") or "")
        for row in born_tags
        if str(row.get("tag") or "").startswith("Category/")
    ]
    tag_sample = [str(row.get("tag") or "") for row in born_tags[:4] if row.get("tag")]
    details = [
        f"name={name}",
        f"factionIndex={faction_index}",
        f"objectType={object_type}" if object_type else "objectType=null",
        f"bornTags={born_tag_count if born_tag_count is not None else 'null'}",
    ]
    if component_count is not None:
        details.append(f"components={component_count}")
    if first_component_type:
        details.append(f"firstComponent={first_component_type}")
    if model_component and model_component.get("modelId"):
        details.append(f"modelComponent={model_component['modelId']}")
    if component_prefix_parsed_count:
        details.append(f"componentPrefix={component_prefix_parsed_count}")
    if first_payload_component:
        details.append(
            f"nextComponent={first_payload_component['type']}:{first_payload_component['memberCount']}"
        )
    if trigger_observer_component:
        details.append(
            "triggerMaps=" + ",".join(str(value) for value in trigger_observer_component["propertyMapCounts"])
        )
        trigger_preview = trigger_observer_component.get("primaryPreviewByKey") or {}
        if "shape" in trigger_preview:
            details.append(f"triggerShape={trigger_preview['shape']}")
        if "radius" in trigger_preview:
            details.append(f"triggerRadius={trigger_preview['radius']}")
    if property_map_component:
        details.append(f"propertyMap={property_map_component['propertyMapCount']}")
        property_keys = property_map_component.get("propertyKeys") or []
        if property_keys:
            details.append("propertyKeys=" + ",".join(str(key) for key in property_keys[:3]))
    if common_perform_component:
        details.append(f"commonPerform={common_perform_component['performPropertyCount']}")
        perform_names = list((common_perform_component.get("performPropertyNameCounts") or {}).keys())
        if perform_names:
            details.append("performKeys=" + ",".join(str(key) for key in perform_names[:3]))
        if common_perform_component.get("syncGameplayLock"):
            details.append("syncGameplayLock=true")
    if logic_controller_component:
        details.append(f"logicType={logic_controller_component['logicType']}")
        logic_keys = logic_controller_component.get("propertyKeys") or []
        if logic_keys:
            details.append("logicKeys=" + ",".join(str(key) for key in logic_keys[:3]))
    if hittable_component:
        details.append(f"hittableMap={hittable_component['propertyMapCount']}")
        hittable_keys = hittable_component.get("propertyKeys") or []
        if hittable_keys:
            details.append("hittableKeys=" + ",".join(str(key) for key in hittable_keys[:3]))
        if hittable_component.get("enableExtraCheck"):
            details.append("hittableExtraCheck=true")
    if audio_component:
        details.append(f"audioStates={audio_component['audioNameCount']}")
        if audio_component.get("customAudioCount"):
            details.append(f"customAudio={audio_component['customAudioCount']}")
        audio_rows = audio_component.get("sampleAudioRows") or []
        first_events = [
            str(event)
            for row in audio_rows[:2]
            for event in (row.get("events") or [])[:1]
            if event
        ]
        if first_events:
            details.append("audio=" + ",".join(first_events[:2]))
    if show_guide_component:
        details.append(f"showGuideMap={show_guide_component['propertyMapCount']}")
        details.append(f"guideShape={show_guide_component['shape']}")
    if component_payload_parsed_count:
        details.append(f"parsedPayloads={component_payload_parsed_count}")
    if template_config_properties:
        details.append(
            f"templateConfig={template_config_properties['configPropertyCount']}"
        )
        template_audio_rows = template_config_properties.get("audioPropertyRows") or []
        if template_audio_rows:
            details.append(
                "templateAudio="
                + ",".join(
                    str(event)
                    for row in template_audio_rows[:2]
                    for event in (row.get("events") or [])[:1]
                )
            )
    if template_action_map_audio and template_action_map_audio.get("audioActions"):
        details.append(
            f"templateAudioActions={len(template_action_map_audio['audioActions'])}"
        )
    if component_stop_component and component_stop_component is not first_payload_component:
        details.append(
            f"stopComponent={component_stop_component['type']}:{component_stop_component['memberCount']}"
        )
    if category_tags:
        details.append(f"category={category_tags[0]}")
    if component_string_samples:
        details.append("componentStrings=" + ",".join(component_string_samples[:3]))
    if tag_error:
        details.append(f"tagParse={tag_error}")
    if component_error:
        details.append(f"componentParse={component_error}")

    return {
        "kind": "memorypack-json",
        "subtype": "InteractiveTemplateData",
        "summary": (
            "MemoryPack InteractiveTemplateData; 25 inherited template members; "
            "component prefix, next payload tag, and selected component bodies decoded from bytes"
        ),
        "rows": component_count,
        "keys": MEMORYPACK_FIELD_SCHEMAS["InteractiveTemplateData"],
        "sample": "; ".join(details)[:STRING_SAMPLE_MAX_CHARS],
        "decoded": {
            "memberCount": INTERACTIVE_TEMPLATE_MEMBER_COUNT,
            "format": "memorypack",
            "schemaSource": INTERACTIVE_TEMPLATE_SCHEMA_SOURCE_NOTE,
            "decodedPrefixFields": [
                "name",
                "factionIndex",
                "objectType",
                "bornTag",
                "componentList",
                "componentListFirst",
                "componentListSecondModel",
                "componentListZeroMemberPrefix",
                "componentListFirstPayloadTag",
                "componentListTriggerObserverBody",
                "componentListFirstPayloadPropertyMap",
                "componentListCommonPerformBody",
                "componentListLogicControllerBody",
                "componentListHittableBody",
                "componentListAudioBody",
                "componentListShowGuideBody",
                "componentListParsedPayloads",
                "templateConfigProperties",
                "templateActionMapAudio",
            ],
            "name": name,
            "factionIndex": faction_index,
            "objectType": object_type,
            "bornTagCount": born_tag_count,
            "bornTags": born_tags,
            "componentListCount": component_count,
            "componentListOffset": format_offset(component_offset),
            "componentListFirstTag": f"0x{first_component_tag:04x}" if first_component_tag is not None else "",
            "componentListFirstType": first_component_type,
            "componentListFirstTagWidth": first_component_tag_width,
            "componentListFirstMemberCount": first_component_member_count,
            "componentListFirstEndOffset": format_offset(first_component_end_offset),
            "componentListSecondTag": f"0x{second_component_tag:04x}" if second_component_tag is not None else "",
            "componentListSecondType": second_component_type,
            "componentListSecondTagWidth": second_component_tag_width,
            "componentListSecondMemberCount": second_component_member_count,
            "componentListSecondEndOffset": format_offset(second_component_end_offset),
            "componentModelData": model_component,
            "componentListPrefixParsedCount": component_prefix_parsed_count,
            "componentListPrefixEndOffset": format_offset(component_prefix_end_offset),
            "componentListPrefixRows": component_prefix_rows,
            "componentListFirstPayload": first_payload_component,
            "componentListFirstPayloadBodyEndOffset": format_offset(first_payload_body_end_offset),
            "componentListParsedPayloadCount": component_payload_parsed_count,
            "componentListParsedPayloadRows": component_payload_parsed_rows,
            "componentListStopPayload": component_stop_component,
            "componentListScanOffset": format_offset(component_scan_offset),
            "componentTriggerObserverData": trigger_observer_component,
            "componentTriggerObserverComponents": trigger_observer_components,
            "componentPropertyMapData": property_map_component,
            "componentPropertyMapComponents": property_map_components,
            "componentCommonPerformData": common_perform_component,
            "componentCommonPerformComponents": common_perform_components,
            "componentAudioPropertyComponents": trigger_zone_audio_property_components,
            "componentLogicControllerData": logic_controller_component,
            "componentLogicControllerComponents": logic_controller_components,
            "componentHittableData": hittable_component,
            "componentHittableComponents": hittable_components,
            "componentAudioData": audio_component,
            "componentAudioComponents": audio_components,
            "componentShowGuideData": show_guide_component,
            "componentShowGuideComponents": show_guide_components,
            "templateConfigProperties": template_config_properties,
            "templateActionMapAudio": template_action_map_audio,
            "componentStringSamples": component_string_samples,
            "componentUnionSource": BASE_COMPONENT_UNION_SOURCE_NOTE if first_component_type else "",
            "componentParseError": component_error or "",
            "exactLength": False,
        },
    }
