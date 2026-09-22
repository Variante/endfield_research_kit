"""Fail-closed framing for current ``NPC/MontageJson/MontageNew`` payloads.

The selected build uses a compact MemoryPack object with three top-level
members and a 24-member montage record. The current generated formatter setter
order names both objects and their nested ``AnimClipInfo``, ``DynamicEntity``,
``EventInfo``, extra-effect, and transition-override records. Both variable
collections are count-framed and the complete current shape closes at EOF.
"""

from __future__ import annotations

import math
import struct
from pathlib import Path
from typing import Any

from scripts.game_data.memorypack.core import MEMORYPACK_NULL_COUNT, format_offset


NPC_MONTAGE_ROOT_MEMBER_COUNT = 3
NPC_MONTAGE_DATA_MEMBER_COUNT = 24
NPC_MONTAGE_CLIP_INFO_MEMBER_COUNT = 7
NPC_MONTAGE_MEMBER3_RECORD_MEMBER_COUNT = 12
NPC_MONTAGE_MEMBER3_NESTED_OBJECT_MEMBER_COUNT = 3
NPC_MONTAGE_MEMBER3_INNER_RECORD_MEMBER_COUNT = 4
NPC_MONTAGE_MEMBER18_RECORD_MEMBER_COUNT = 5
NPC_MONTAGE_RELATIVE_PREFIX = "Data/Json/NPC/MontageJson/MontageNew/"

NPC_MONTAGE_ROOT_FIELDS = ("animType", "data", "tag")
NPC_MONTAGE_DATA_FIELDS = (
    "bIsCloseLookAt",
    "bIsCloseSkeletalMorph",
    "clipInfo",
    "dynamicEntities",
    "enableDialogLookAt",
    "enableHitAnim",
    "endClipAsyncInfo",
    "endLookAt",
    "endLookAtBodySmoothTime",
    "endLookAtEyeSmoothTime",
    "endLookAtPercent",
    "frameRate",
    "gpuMountPointDataPathHash",
    "gpuMountPointTrackGuid",
    "interruptPercent",
    "loopClipAsyncInfo",
    "maskType",
    "montageFadeInTransition",
    "montageOverrideTransitions",
    "montageStartType",
    "rootMotionDistance",
    "startClipAsyncInfo",
    "textureGuid",
    "textureHashPath",
)
ANIM_CLIP_INFO_FIELDS = (
    "duration",
    "gpuAnimType",
    "gpuMountPointDataPathHash",
    "guid",
    "name",
    "normalizedFrameCount",
    "normalizedOffset",
)
DYNAMIC_ENTITY_FIELDS = (
    "effectPath",
    "eventHide",
    "eventShow",
    "eventStr",
    "extraEffects",
    "hideAccName",
    "isLoop",
    "mountPoint",
    "prefabGuid",
    "prefabPathHash",
    "syncAnimatorWithOwner",
    "type",
)
TRANSITION_OVERRIDE_FIELDS = (
    "from",
    "to",
    "transistionOffset",
    "transitionDuration",
    "transitionExitTime",
)

_GUID_PROXY_SIZE = 16
_ASYNC_CLIP_INFO_SIZE = 36
_TRANSITION_INFO_SIZE = 32
_MEMBER3_RECORD_FIXED_PREFIX_SIZE = 10
_MEMBER3_NESTED_OBJECT_BODY_SIZE = 9
_MEMBER3_MIN_RECORD_SIZE = 71
_MEMBER3_MIN_INNER_RECORD_SIZE = 33
_POST_MEMBER3_MIN_SUFFIX_SIZE = 231
_MEMBER18_RECORD_BODY_SIZE = 20
_MEMBER18_RECORD_SIZE = 21
_POST_MEMBER18_SUFFIX_SIZE = 72
_MAX_ANONYMOUS_UTF8_BYTES = 512


class NpcMontageFramingError(ValueError):
    """Raised when a payload is truncated, changed, or outside this exact frame."""


class _Reader:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.offset = 0

    def require(self, size: int, field: str) -> int:
        start = self.offset
        end = start + size
        if size < 0 or end > len(self.data):
            raise NpcMontageFramingError(
                f"{field}:truncated offset={format_offset(start)} "
                f"need={size} remaining={len(self.data) - start}"
            )
        self.offset = end
        return start

    def u8(self, field: str) -> int:
        return self.data[self.require(1, field)]

    def i32(self, field: str) -> int:
        return struct.unpack_from("<i", self.data, self.require(4, field))[0]

    def i64(self, field: str) -> int:
        return struct.unpack_from("<q", self.data, self.require(8, field))[0]

    def u32(self, field: str) -> int:
        return struct.unpack_from("<I", self.data, self.require(4, field))[0]

    def f32(self, field: str) -> float:
        value = struct.unpack_from("<f", self.data, self.require(4, field))[0]
        if not math.isfinite(value):
            raise NpcMontageFramingError(f"{field}:non-finite")
        return value

    def skip(self, size: int, field: str) -> dict[str, int]:
        start = self.require(size, field)
        return {"startOffset": start, "endOffset": self.offset, "length": size}

    def boolean(self, field: str) -> bool:
        value = self.u8(field)
        if value not in (0, 1):
            raise NpcMontageFramingError(f"{field}:invalid-bool={value}")
        return bool(value)


def is_npc_montage_memorypack_path(path: str | Path) -> bool:
    """Return whether ``path`` routes to the generated NPC montage family."""
    normalized = str(path).replace("\\", "/")
    folded = normalized.casefold()
    marker = NPC_MONTAGE_RELATIVE_PREFIX.casefold()
    marker_offset = folded.find(marker)
    return (
        marker_offset >= 0
        and (marker_offset == 0 or folded[marker_offset - 1] == "/")
        and folded.endswith(".json")
    )


def _read_clip_info(reader: _Reader) -> dict[str, Any]:
    start = reader.offset
    member_count = reader.u8("data.member2.memberCount")
    if member_count == 0xFF:
        return {
            "isNull": True,
            "memberCount": None,
            "startOffset": start,
            "endOffset": reader.offset,
            "name": None,
        }
    if member_count != NPC_MONTAGE_CLIP_INFO_MEMBER_COUNT:
        raise NpcMontageFramingError(
            "data.member2.memberCount:"
            f"expected={NPC_MONTAGE_CLIP_INFO_MEMBER_COUNT} actual={member_count}"
        )

    duration = reader.f32("data.clipInfo.duration")
    gpu_anim_type = reader.i32("data.clipInfo.gpuAnimType")
    gpu_mount_point_data_path_hash = reader.i64(
        "data.clipInfo.gpuMountPointDataPathHash"
    )
    guid_range = reader.skip(_GUID_PROXY_SIZE, "data.clipInfo.guid")
    string_offset = reader.offset
    length = reader.u32("data.clipInfo.name.length")
    name: str | None
    if length == MEMORYPACK_NULL_COUNT:
        name = None
    else:
        if length > _MAX_ANONYMOUS_UTF8_BYTES:
            raise NpcMontageFramingError(
                f"data.clipInfo.name:invalid-length={length}"
            )
        raw_offset = reader.require(length, "data.clipInfo.name.bytes")
        try:
            name = reader.data[raw_offset:reader.offset].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise NpcMontageFramingError(
                "data.clipInfo.name:invalid-utf8 "
                f"offset={format_offset(raw_offset)}"
            ) from exc
        if name and not name.startswith("A_"):
            raise NpcMontageFramingError(
                "data.clipInfo.name:unexpected-current-prefix="
                f"{name[:32]!r}"
            )
    normalized_frame_count = reader.f32("data.clipInfo.normalizedFrameCount")
    normalized_offset = reader.f32("data.clipInfo.normalizedOffset")
    return {
        "isNull": False,
        "memberCount": member_count,
        "startOffset": start,
        "endOffset": reader.offset,
        "fieldOrder": list(ANIM_CLIP_INFO_FIELDS),
        "duration": duration,
        "gpuAnimType": gpu_anim_type,
        "gpuMountPointDataPathHash": gpu_mount_point_data_path_hash,
        "guidRange": guid_range,
        "nameOffset": string_offset,
        "name": name,
        "normalizedFrameCount": normalized_frame_count,
        "normalizedOffset": normalized_offset,
    }


def _read_member18_records(reader: _Reader, count: int) -> list[dict[str, Any]]:
    remaining = len(reader.data) - reader.offset
    required = count * _MEMBER18_RECORD_SIZE + _POST_MEMBER18_SUFFIX_SIZE
    if required > remaining:
        raise NpcMontageFramingError(
            "data.member18:truncated-count-envelope "
            f"count={count} need={required} remaining={remaining}"
        )
    records: list[dict[str, Any]] = []
    for index in range(count):
        start = reader.offset
        member_count = reader.u8(f"data.member18[{index}].memberCount")
        if member_count != NPC_MONTAGE_MEMBER18_RECORD_MEMBER_COUNT:
            raise NpcMontageFramingError(
                f"data.member18[{index}].memberCount:"
                f"expected={NPC_MONTAGE_MEMBER18_RECORD_MEMBER_COUNT} "
                f"actual={member_count}"
            )
        from_state = reader.i32(f"data.montageOverrideTransitions[{index}].from")
        to_state = reader.i32(f"data.montageOverrideTransitions[{index}].to")
        transition_offset = reader.f32(
            f"data.montageOverrideTransitions[{index}].transistionOffset"
        )
        transition_duration = reader.f32(
            f"data.montageOverrideTransitions[{index}].transitionDuration"
        )
        transition_exit_time = reader.f32(
            f"data.montageOverrideTransitions[{index}].transitionExitTime"
        )
        records.append(
            {
                "memberCount": member_count,
                "startOffset": start,
                "endOffset": reader.offset,
                "fieldOrder": list(TRANSITION_OVERRIDE_FIELDS),
                "from": from_state,
                "to": to_state,
                "transistionOffset": transition_offset,
                "transitionDuration": transition_duration,
                "transitionExitTime": transition_exit_time,
            }
        )
    return records


def _read_anonymous_utf8(reader: _Reader, field: str) -> dict[str, Any]:
    start = reader.offset
    length = reader.u32(f"{field}.length")
    if length == MEMORYPACK_NULL_COUNT:
        return {
            "startOffset": start,
            "endOffset": reader.offset,
            "byteLength": None,
            "isNull": True,
        }
    if length > _MAX_ANONYMOUS_UTF8_BYTES:
        raise NpcMontageFramingError(f"{field}:invalid-length={length}")
    raw_offset = reader.require(length, f"{field}.bytes")
    try:
        value = reader.data[raw_offset:reader.offset].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise NpcMontageFramingError(
            f"{field}:invalid-utf8 offset={format_offset(raw_offset)}"
        ) from exc
    return {
        "startOffset": start,
        "endOffset": reader.offset,
        "byteLength": length,
        "isNull": False,
        "value": value,
    }


def _read_event_info(reader: _Reader, field: str) -> dict[str, Any]:
    start = reader.offset
    member_count = reader.u8(f"{field}.memberCount")
    if member_count != NPC_MONTAGE_MEMBER3_NESTED_OBJECT_MEMBER_COUNT:
        raise NpcMontageFramingError(
            f"{field}.memberCount:"
            f"expected={NPC_MONTAGE_MEMBER3_NESTED_OBJECT_MEMBER_COUNT} "
            f"actual={member_count}"
        )
    state_type = reader.i32(f"{field}.stateType")
    time = reader.f32(f"{field}.time")
    trigger = reader.boolean(f"{field}.trigger")
    return {
        "memberCount": member_count,
        "startOffset": start,
        "endOffset": reader.offset,
        "fieldOrder": ["stateType", "time", "trigger"],
        "stateType": state_type,
        "time": time,
        "trigger": trigger,
    }


def _read_vector3(reader: _Reader, field: str) -> dict[str, Any]:
    start = reader.offset
    values = (
        reader.f32(f"{field}.x"),
        reader.f32(f"{field}.y"),
        reader.f32(f"{field}.z"),
    )
    return {
        "startOffset": start,
        "endOffset": reader.offset,
        "x": values[0],
        "y": values[1],
        "z": values[2],
    }


def _read_animation_clip_async_info(reader: _Reader, field: str) -> dict[str, Any]:
    """Decode the fixed 36-byte current ``AnimationClipAsyncInfo`` value."""
    start = reader.require(_ASYNC_CLIP_INFO_SIZE, field)
    raw = reader.data[start:reader.offset]
    floats = struct.unpack_from("<fffff", raw, 8)
    if not all(math.isfinite(value) for value in floats):
        raise NpcMontageFramingError(f"{field}:non-finite")
    if raw[32] not in (0, 1) or raw[33] not in (0, 1):
        raise NpcMontageFramingError(f"{field}:invalid-bool")
    return {
        "startOffset": start,
        "endOffset": reader.offset,
        "montagePathHash": struct.unpack_from("<q", raw, 0)[0],
        "length": floats[0],
        "framerate": floats[1],
        "averageSpeed": {"x": floats[2], "y": floats[3], "z": floats[4]},
        "averageAngularSpeed": struct.unpack_from("<f", raw, 28)[0],
        "isHumanoid": bool(raw[32]),
        "isLooping": bool(raw[33]),
        "paddingHex": raw[34:36].hex(),
    }


def _read_transition_info(reader: _Reader, field: str) -> dict[str, Any]:
    """Decode the fixed 32-byte current ``FMontageTransitionInfo`` value."""
    start = reader.require(_TRANSITION_INFO_SIZE, field)
    raw = reader.data[start:reader.offset]
    if raw[0] not in (0, 1):
        raise NpcMontageFramingError(f"{field}:invalid-bool={raw[0]}")
    values = struct.unpack_from("<fffffff", raw, 4)
    if not all(math.isfinite(value) for value in values):
        raise NpcMontageFramingError(f"{field}:non-finite")
    return {
        "startOffset": start,
        "endOffset": reader.offset,
        "bIsFixedTransitionTime": bool(raw[0]),
        "paddingHex": raw[1:4].hex(),
        "transistionOffset": values[0],
        "transitionDuration": values[1],
        "transitionTime": values[2],
        "fixedTime": values[3],
        "fixedTransitionDuration": values[4],
        "normalizedTransitionTime": values[5],
        "exitTime": values[6],
    }


def _read_member3_records(reader: _Reader, count: int) -> list[dict[str, Any]]:
    remaining = len(reader.data) - reader.offset
    required = count * _MEMBER3_MIN_RECORD_SIZE + _POST_MEMBER3_MIN_SUFFIX_SIZE
    if required > remaining:
        raise NpcMontageFramingError(
            "data.member3:truncated-count-envelope "
            f"count={count} need-at-least={required} remaining={remaining}"
        )

    records: list[dict[str, Any]] = []
    for index in range(count):
        start = reader.offset
        member_count = reader.u8(f"data.member3[{index}].memberCount")
        if member_count != NPC_MONTAGE_MEMBER3_RECORD_MEMBER_COUNT:
            raise NpcMontageFramingError(
                f"data.member3[{index}].memberCount:"
                f"expected={NPC_MONTAGE_MEMBER3_RECORD_MEMBER_COUNT} "
                f"actual={member_count}"
            )
        effect_path = _read_anonymous_utf8(
            reader, f"data.dynamicEntities[{index}].effectPath"
        )
        event_hide = _read_event_info(
            reader, f"data.dynamicEntities[{index}].eventHide"
        )
        event_show = _read_event_info(
            reader, f"data.dynamicEntities[{index}].eventShow"
        )
        event_string = _read_anonymous_utf8(
            reader, f"data.dynamicEntities[{index}].eventStr"
        )
        inner_count_offset = reader.offset
        inner_count = reader.u32(f"data.dynamicEntities[{index}].extraEffects.count")
        if inner_count > (
            len(reader.data) - reader.offset
        ) // _MEMBER3_MIN_INNER_RECORD_SIZE:
            raise NpcMontageFramingError(
                f"data.dynamicEntities[{index}].extraEffects:count-overrun "
                f"count={inner_count} remaining={len(reader.data) - reader.offset}"
            )
        inner_records: list[dict[str, Any]] = []
        for inner_index in range(inner_count):
            inner_start = reader.offset
            inner_member_count = reader.u8(
                f"data.dynamicEntities[{index}].extraEffects[{inner_index}].memberCount"
            )
            if inner_member_count != NPC_MONTAGE_MEMBER3_INNER_RECORD_MEMBER_COUNT:
                raise NpcMontageFramingError(
                    f"data.dynamicEntities[{index}].extraEffects[{inner_index}].memberCount:"
                    f"expected={NPC_MONTAGE_MEMBER3_INNER_RECORD_MEMBER_COUNT} "
                    f"actual={inner_member_count}"
                )
            inner_effect_path = _read_anonymous_utf8(
                reader,
                f"data.dynamicEntities[{index}].extraEffects[{inner_index}].effectPath",
            )
            local_euler_angles = _read_vector3(
                reader,
                f"data.dynamicEntities[{index}].extraEffects[{inner_index}]."
                "localEulerAngles",
            )
            local_position = _read_vector3(
                reader,
                f"data.dynamicEntities[{index}].extraEffects[{inner_index}]."
                "localPosition",
            )
            mount_node_path = _read_anonymous_utf8(
                reader,
                f"data.dynamicEntities[{index}].extraEffects[{inner_index}].mountNodePath",
            )
            inner_records.append(
                {
                    "memberCount": inner_member_count,
                    "startOffset": inner_start,
                    "endOffset": reader.offset,
                    "fieldOrder": [
                        "effectPath",
                        "localEulerAngles",
                        "localPosition",
                        "mountNodePath",
                    ],
                    "effectPath": inner_effect_path,
                    "localEulerAngles": local_euler_angles,
                    "localPosition": local_position,
                    "mountNodePath": mount_node_path,
                }
            )
        hide_acc_name = _read_anonymous_utf8(
            reader, f"data.dynamicEntities[{index}].hideAccName"
        )
        is_loop = reader.boolean(f"data.dynamicEntities[{index}].isLoop")
        mount_point = reader.i32(f"data.dynamicEntities[{index}].mountPoint")
        prefab_guid = reader.skip(
            _GUID_PROXY_SIZE, f"data.dynamicEntities[{index}].prefabGuid"
        )
        prefab_path_hash = reader.i64(
            f"data.dynamicEntities[{index}].prefabPathHash"
        )
        sync_animator_with_owner = reader.boolean(
            f"data.dynamicEntities[{index}].syncAnimatorWithOwner"
        )
        entity_type = reader.i32(f"data.dynamicEntities[{index}].type")
        records.append(
            {
                "memberCount": member_count,
                "startOffset": start,
                "endOffset": reader.offset,
                "fieldOrder": list(DYNAMIC_ENTITY_FIELDS),
                "effectPath": effect_path,
                "eventHide": event_hide,
                "eventShow": event_show,
                "eventStr": event_string,
                "extraEffectsCountOffset": inner_count_offset,
                "extraEffects": inner_records,
                "hideAccName": hide_acc_name,
                "isLoop": is_loop,
                "mountPoint": mount_point,
                "prefabGuidRange": prefab_guid,
                "prefabPathHash": prefab_path_hash,
                "syncAnimatorWithOwner": sync_animator_with_owner,
                "type": entity_type,
            }
        )
    return records


def frame_npc_montage(data: bytes) -> dict[str, Any]:
    """Frame one supported current-build NPC montage through physical EOF.

    Both variable collections are consumed only through explicit counts,
    length-prefixed values, fixed anonymous extents, and per-record member-count
    markers. No suffix scanning is used.
    """
    reader = _Reader(data)
    root_count = reader.u8("root.memberCount")
    if root_count != NPC_MONTAGE_ROOT_MEMBER_COUNT:
        raise NpcMontageFramingError(
            f"root.memberCount:expected={NPC_MONTAGE_ROOT_MEMBER_COUNT} actual={root_count}"
        )

    anim_type = reader.i32("root.animType")
    data_count = reader.u8("root.member1.memberCount")
    if data_count != NPC_MONTAGE_DATA_MEMBER_COUNT:
        raise NpcMontageFramingError(
            f"root.member1.memberCount:expected={NPC_MONTAGE_DATA_MEMBER_COUNT} "
            f"actual={data_count}"
        )

    b_is_close_look_at = reader.boolean("data.bIsCloseLookAt")
    b_is_close_skeletal_morph = reader.boolean("data.bIsCloseSkeletalMorph")
    clip_info = _read_clip_info(reader)

    dynamic_count_offset = reader.offset
    dynamic_count = reader.u32("data.member3.count")
    member3_records = _read_member3_records(reader, dynamic_count)
    enable_dialog_look_at = reader.boolean("data.enableDialogLookAt")
    enable_hit_anim = reader.boolean("data.enableHitAnim")
    end_clip_async_info = _read_animation_clip_async_info(
        reader, "data.endClipAsyncInfo"
    )
    end_look_at = reader.boolean("data.endLookAt")
    end_look_at_body_smooth_time = reader.f32("data.endLookAtBodySmoothTime")
    end_look_at_eye_smooth_time = reader.f32("data.endLookAtEyeSmoothTime")
    end_look_at_percent = reader.i32("data.endLookAtPercent")
    frame_rate = reader.i32("data.frameRate")
    gpu_mount_point_data_path_hash = reader.i64("data.gpuMountPointDataPathHash")
    gpu_mount_point_track_guid = reader.skip(
        _GUID_PROXY_SIZE, "data.gpuMountPointTrackGuid"
    )
    interrupt_percent = reader.f32("data.interruptPercent")
    loop_clip_async_info = _read_animation_clip_async_info(
        reader, "data.loopClipAsyncInfo"
    )
    mask_type = reader.i32("data.maskType")
    montage_fade_in_transition = _read_transition_info(
        reader, "data.montageFadeInTransition"
    )

    override_count_offset = reader.offset
    override_count = reader.u32("data.member18.count")
    member18_records = _read_member18_records(reader, override_count)
    montage_start_type = reader.i32("data.montageStartType")
    root_motion_distance = reader.f32("data.rootMotionDistance")
    start_clip_async_info = _read_animation_clip_async_info(
        reader, "data.startClipAsyncInfo"
    )
    texture_guid = reader.skip(_GUID_PROXY_SIZE, "data.textureGuid")
    texture_hash_path = reader.i64("data.textureHashPath")

    root_member2_offset = reader.offset
    tag = reader.i32("root.tag")
    if reader.offset != len(data):
        raise NpcMontageFramingError(
            f"trailing-bytes offset={format_offset(reader.offset)} "
            f"count={len(data) - reader.offset}"
        )

    return {
        "status": (
            "exact_current_npc_montage_member3_counted_frame"
            if dynamic_count
            else (
                "exact_current_npc_montage_empty_collection_frame"
                if override_count == 0
                else "exact_current_npc_montage_member18_counted_frame"
            )
        ),
        "schemaStatus": "named_exact",
        "serializedMemberCount": root_count,
        "nestedDataMemberCount": data_count,
        "rootFieldOrder": list(NPC_MONTAGE_ROOT_FIELDS),
        "dataFieldOrder": list(NPC_MONTAGE_DATA_FIELDS),
        "bytesConsumed": reader.offset,
        "root": {"animType": anim_type, "tag": tag},
        "data": {
            "bIsCloseLookAt": b_is_close_look_at,
            "bIsCloseSkeletalMorph": b_is_close_skeletal_morph,
            "clipInfo": clip_info,
            "dynamicEntities": member3_records,
            "enableDialogLookAt": enable_dialog_look_at,
            "enableHitAnim": enable_hit_anim,
            "endClipAsyncInfo": end_clip_async_info,
            "endLookAt": end_look_at,
            "endLookAtBodySmoothTime": end_look_at_body_smooth_time,
            "endLookAtEyeSmoothTime": end_look_at_eye_smooth_time,
            "endLookAtPercent": end_look_at_percent,
            "frameRate": frame_rate,
            "gpuMountPointDataPathHash": gpu_mount_point_data_path_hash,
            "gpuMountPointTrackGuidRange": gpu_mount_point_track_guid,
            "interruptPercent": interrupt_percent,
            "loopClipAsyncInfo": loop_clip_async_info,
            "maskType": mask_type,
            "montageFadeInTransition": montage_fade_in_transition,
            "montageOverrideTransitions": member18_records,
            "montageStartType": montage_start_type,
            "rootMotionDistance": root_motion_distance,
            "startClipAsyncInfo": start_clip_async_info,
            "textureGuidRange": texture_guid,
            "textureHashPath": texture_hash_path,
        },
        "clipInfo": clip_info,
        "collectionCountOffsets": [dynamic_count_offset, override_count_offset],
        "emptyCollectionOffsets": [
            *([dynamic_count_offset] if dynamic_count == 0 else []),
            *([override_count_offset] if override_count == 0 else []),
        ],
        "member3Records": member3_records,
        "member18Records": member18_records,
        "rootNamedMembers": [
            {"index": 0, "field": "animType", "offset": 1, "value": anim_type},
            {"index": 2, "field": "tag", "offset": root_member2_offset, "value": tag},
        ],
        "evidenceBoundary": (
            "The complete supported shape is consumed through physical EOF. "
            "The current generated formatter setter order names the three root "
            "members, all 24 NPCMontageAnim members, AnimClipInfo, DynamicEntity, "
            "EventInfo, extra-effect vectors, and transition overrides. Non-empty "
            "clip names are gated to the observed A_* shape. DynamicEntity's "
            "remaining strings, booleans, GUID span, path hash, and type advance "
            "their generated field order exactly; no filename or runtime-use "
            "inference is used."
        ),
    }


def decode_npc_montage_memorypack(
    path: str | Path,
    data: bytes,
    size: int | None = None,
) -> dict[str, Any] | None:
    """Route and summarize a supported NPC montage payload."""
    if not is_npc_montage_memorypack_path(path):
        return None
    if size is not None and size != len(data):
        raise NpcMontageFramingError(
            f"outer-size-mismatch declared={size} actual={len(data)}"
        )
    framed = frame_npc_montage(data)
    clip_name = framed["clipInfo"].get("name")
    return {
        "kind": "memorypack-json",
        "subtype": "NPCMontageJson",
        "summary": (
            "MemoryPack NPCMontageJson; 3-member root; 24-member montage; "
            "named counted records; complete exact schema"
        ),
        "rows": 1,
        "keys": ["clipName", "animType", "tag"],
        "sample": (
            f"clipName={clip_name}"
            if clip_name
            else "clipName=<null-or-empty>"
        ),
        "decoded": framed,
    }
