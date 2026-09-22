from __future__ import annotations

import re
import struct
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from scripts.game_data.codecs.levelscript import active_shapes as levelscript_active_shapes
from scripts.game_data.codecs.levelscript import action_map as levelscript_action_map
from scripts.game_data.codecs.levelscript import boolean_getters as levelscript_boolean_getters
from scripts.game_data.codecs.levelscript import call_server as levelscript_call_server
from scripts.game_data.codecs.levelscript import compact_property_gate as levelscript_property_gate
from scripts.game_data.codecs.levelscript import control_flow_actions as levelscript_control_flow
from scripts.game_data.codecs.levelscript import entity_hp_changed as levelscript_entity_hp_changed
from scripts.game_data.codecs.levelscript import exit_custom_performance as levelscript_exit_performance
from scripts.game_data.codecs.levelscript import fmv as levelscript_fmv
from scripts.game_data.codecs.levelscript import manual_control as levelscript_manual_control
from scripts.game_data.codecs.levelscript import npc_patrol_start as levelscript_npc_patrol_start
from scripts.game_data.codecs.levelscript import params as levelscript_params
from scripts.game_data.codecs.levelscript import play3d_radio as levelscript_play3d_radio
from scripts.game_data.codecs.levelscript import raise_custom_script_event as levelscript_custom_event
from scripts.game_data.codecs.levelscript import scalar_value_getters as levelscript_scalar_getters
from scripts.game_data.codecs.levelscript import switch_actions as levelscript_switch_actions
from scripts.game_data.codecs.levelscript import top_level_tail as levelscript_top_level_tail
from scripts.game_data.codecs.levelscript import trigger_volumes as levelscript_trigger_volumes
from scripts.game_data.spawnerptr_getter_native import decode_spawnerptr_getter_member

from scripts.common import read_bytes_cached
from scripts.game_data.codecs.levelscript.primitives import u32 as _u32

# Per-record byte decoding lives in the codec package; these names stay importable
# from this module because its consumers and the local test suite reach them here.
from scripts.game_data.codecs.levelscript.framing_common import (  # noqa: F401
    LevelScriptTopLevelFramingError,
    _u64_offsets,
    _is_plausible_levelscript_id,
    _drop_empty,
    _offset_hex,
    _round_float,
    _record_start,
    _is_printable_ascii,
    _read_compact_string,
    _record_payload_window,
    COMPACT_NULL_SENTINEL,
    ACTION_SERIALIZED_MAP_LIST_ORDER,
    ACTION_SERIALIZED_MAP_ORDER_EVIDENCE,
    SCRIPT_POINTER_REF_RECORDS,
    NOISY_PROPERTY_PREFIXES,
    NOISY_PROPERTY_TEXT,
)
from scripts.game_data.codecs.levelscript.record_hints import (  # noqa: F401
    LEVELSCRIPT_NATIVE_HEADER_MAPPING_ID,
    LEVELSCRIPT_NATIVE_HEADER_CONTRACT_SCHEMA,
    LEVELSCRIPT_NATIVE_HEADER_NAMES,
    LEVELSCRIPT_NATIVE_HEADER_TAG_NAMES,
    LEVELSCRIPT_NATIVE_HEADER_UNION_TAG_NAMES,
    levelscript_native_header_contract,
    summarize_levelscript_native_header_records,
    levelscript_record_semantic_key,
    levelscript_native_header_name,
    LEVELSCRIPT_RECORD_HINTS,
    LEVELSCRIPT_RECORD_TAG_HINTS,
    LEVELSCRIPT_NATIVE_EVENT_PAYLOAD_MAPPING_ID,
    LEVELSCRIPT_NATIVE_AUDIO_ACTION_MAPPING_ID,
    LEVELSCRIPT_NATIVE_LIST_GET_VALUE_STRING_MAPPING_ID,
    TRIGGER_VOLUME_RECORD_KEYS,
)
from scripts.game_data.codecs.levelscript.uid_records import (  # noqa: F401
    LEVELSCRIPT_HEX_UID_RE,
    _extract_levelscript_tagged_ascii_strings,
    _extract_levelscript_plain_ascii_strings,
    _decode_levelscript_uid_record,
    extract_levelscript_uid_records,
)
from scripts.game_data.codecs.levelscript.condition_params import (  # noqa: F401
    _decode_levelscript_ptr_param,
    _decode_levelscript_task_ptr_param,
    _decode_string_param,
    _decode_nullable_string_value,
    _decode_u64_param,
    _decode_entity_ptr_list_param,
    _decode_string_collection_param,
    _decode_u32_collection_param,
    _getter_subtype_payload,
    _decode_vector3_param,
    _decode_quaternion_param,
    _decode_audio_param_tail,
)
from scripts.game_data.codecs.levelscript.task_conditions import (  # noqa: F401
    LEVELSCRIPT_TASK_MISSION_STATE_MAPPING_ID,
    LEVELSCRIPT_TASK_CONDITION_MAPPING_ID,
    LEVELSCRIPT_TASK_CONDITION_TAGS,
    _MISSION_STATE_NAMES,
    _QUEST_STATE_NAMES,
    _MISSION_STATE_COMPARER_NAMES,
    _NUMBER_COMPARER_NAMES,
    _FACTORY_BLACK_BOX_STATE_NAMES,
    _SPACESHIP_ROOM_TYPE_NAMES,
    _DOMAIN_POI_TYPE_NAMES,
    _decode_task_condition_union_header,
    _decode_task_condition_common,
    _condition_param,
    _decode_nullable_param,
    _decode_generic_task_condition_fields,
    _decode_levelscript_task_condition,
    _decode_levelscript_check_mission_state_condition,
    _decode_levelscript_single_condition_task_mission_state,
    _looks_like_levelscript_task_entry_prefix,
    _decode_levelscript_task_entry,
    decode_levelscript_task_map_exact,
    decode_levelscript_task_conditions,
    scan_levelscript_task_condition_fragments,
    decode_levelscript_task_mission_state_dependencies,
)
from scripts.game_data.codecs.levelscript.sequential_owner import (  # noqa: F401
    _frame_levelscript_sequential_owner,
    frame_levelscript_action_map_named_prefix,
    _record_local_id,
    _small_uid_list_count,
    _levelscript_header_list_like_record,
    _levelscript_getter_list_like_record,
    _block_looks_like_header_list,
    _block_looks_like_levelscript_tail,
    _next_uid_block_relation,
)
from scripts.game_data.codecs.levelscript.condition_getters import (  # noqa: F401
    _decode_interactive_check_state_getter,
    _decode_get_lsm_is_completed_getter,
    _decode_get_condition_result_getter,
    _decode_start_dialog_action,
    _decode_get_levelscript_stage_getter,
    _decode_levelscript_property_bool_getter,
    _decode_get_mission_state_getter,
    _decode_compare_mission_state_getter,
    _decode_check_levelscript_stage_getter,
    _decode_check_mission_or_quest_complete_getter,
    _decode_script_variable_changed_fields,
    _decode_leader_trigger_volume_fields,
    _decode_leader_trigger_volume_list_fields,
    _decode_encounter_lsm_fields,
    _decode_scripted_char_patrol_fields,
    _decode_npc_patrol_checkpoint_fields,
    _decode_entity_compare_getter,
)
from scripts.game_data.codecs.levelscript.anonymous_bodies import (  # noqa: F401
    _read_anonymous_nullable_utf8,
    _read_anonymous_i32_string_collection,
    _read_anonymous_param_tail,
    frame_levelscript_first_record_35_0e_00_anonymous_body,
    _read_nullable_levelscript_param,
    _read_levelscript_node_envelope,
    frame_levelscript_single_call_server_leader_enter,
)
from scripts.game_data.codecs.levelscript.current_action_sequence import (  # noqa: F401
    _CURRENT_SEQUENTIAL_ACTION_MEMBERS,
    _read_current_action_envelope,
    _read_current_bool_param,
    _read_current_i32_param,
    _read_current_u8_param,
    _decode_current_common_mask_blend_param,
    _read_current_camera_transform_fields,
    _decode_current_air_wall_ptr_param,
    _decode_current_event_args_ptr_param,
    _read_current_action_fields,
    _CURRENT_SEQUENTIAL_GETTER_MEMBERS,
    _read_current_getter,
    _read_current_leader_enter_header,
    _read_reviewed_map_node,
    frame_levelscript_current_action_sequence_leader_enter,
)
from scripts.game_data.codecs.levelscript.native_event_detail import (  # noqa: F401
    _decode_named_native_event_detail,
    _extract_tail_local_refs,
    _decode_wait_for_seconds_in_trigger_volume_action,
    _decode_toggle_clear_screen_but_radio_action,
    _decode_main_char_move_to_action,
)
from scripts.game_data.codecs.levelscript.action_header import (  # noqa: F401
    CALLSERVER_SERIALIZED_CONTRACT_FIELDS,
    compact_callserver_serialized_contract,
    _decode_action_header_prefix,
    LEVELSCRIPT_EXACT_GETTER_FIELDS,
    _predicate_local_getter_refs,
)
from scripts.game_data.codecs.levelscript.audio_actions import (  # noqa: F401
    _decode_list_add_value_entity_ptr,
    _decode_audio_scalar_param,
    _decode_audio_string_param,
    _decode_audio_bool_param,
    _decode_audio_i32_param,
    _decode_audio_float_param,
    _decode_audio_entity_param,
    _decode_list_get_value_string,
    _decode_announce_audio_target_param,
    _decode_nullable_audio_field,
    _finish_audio_action_fields,
    _decode_audio_action,
)
from scripts.game_data.codecs.levelscript.payload_fields import (  # noqa: F401
    _payload_sentinel_size,
    _decode_tagged_payload_fields,
    _record_text_values,
    _looks_like_property_key,
    _extract_property_output_refs,
    _extract_trigger_slot_ids,
)
from scripts.game_data.codecs.levelscript.encounter_modules import (  # noqa: F401
    decode_levelscript_encounter_module_target,
)
from scripts.game_data.codecs.levelscript.script_pointer import (  # noqa: F401
    decode_script_pointer_payload,
)
from scripts.game_data.codecs.levelscript.trigger_volume_context import (  # noqa: F401
    classify_local_trigger_volume_context,
)


TRIGGER_VOLUME_RECORD_KEYS.update({(0x12BE, 0x00), (0x12C0, 0x00)})


def decode_levelscript_action_map_header(data: bytes) -> dict[str, Any]:
    """Decode the stable header of the top-level LevelScriptData actionMap.

    The first serialized member after the LevelScriptData member count is the
    actionMap. For the exported blobs seen so far, non-empty action maps start
    with `02 03 <u32 count>` followed immediately by that many `actionList`
    records. The remaining `ActionSerializedMap` list boundaries need the UID
    record index, so they are decoded by `decode_levelscript_action_map_lists`.
    """
    if not data:
        return {}
    out: dict[str, Any] = {
        "offset": "0x1",
        "serializedMemberCount": data[0],
    }
    if len(data) >= 7 and data[1] == 0x02 and data[2] == 0x03:
        count = _u32(data, 3)
        out.update({
            "status": "present",
            "recordCount": count,
            "recordStartOffset": 7,
            "recordStartOffsetHex": "0x7",
            "headerHex": data[:7].hex(" "),
        })
        return _drop_empty(out)
    if len(data) >= 3 and data[1] == 0xFF:
        out.update({
            "status": "absent-marker",
            "marker": f"0xff 0x{data[2]:02x}",
            "headerHex": data[:3].hex(" "),
        })
        return _drop_empty(out)
    out.update({
        "status": "unknown",
        "headerHex": data[: min(len(data), 8)].hex(" "),
    })
    return _drop_empty(out)


def frame_levelscript_empty_action_map_prefix(data: bytes) -> dict[str, Any]:
    """Prove the current root plus an empty serialized-map prefix.

    This reader intentionally stops after the first named member. It is the
    fallback for files whose later top-level members do not match either of the
    stronger EOF-closing readers.
    """
    if not data or data[0] != 27:
        actual = data[0] if data else None
        raise LevelScriptTopLevelFramingError(
            f"LevelScriptData member count mismatch: expected=27 actual={actual}"
        )
    if len(data) < 15 or data[1:15] != (
        b"\x02\x03" + b"\x00\x00\x00\x00" * 3
    ):
        raise LevelScriptTopLevelFramingError(
            "LevelScriptData does not have the exact empty ActionSerializedMap prefix"
        )
    complete_asset = (
        len(data) >= 20
        and data[15] == 1
        and _u32(data, 16) == 0
    )
    boundary_end = 20 if complete_asset else 15
    return {
        "status": (
            "exact_empty_action_map_asset_prefix_with_opaque_remainder"
            if complete_asset
            else "exact_empty_serialized_map_prefix_with_opaque_remainder"
        ),
        "schemaStatus": "partial",
        "serializedMemberCount": 27,
        "bytesConsumed": boundary_end,
        "actionMap": {
            "startOffset": 1,
            "endOffset": boundary_end,
            "serializedMemberCount": 2,
            "dataMap": {
                "startOffset": 2,
                "endOffset": 15,
                "serializedMemberCount": 3,
                "actionListCount": 0,
                "getterListCount": 0,
                "headerListCount": 0,
            },
            "paramBlackboard": (
                {
                    "startOffset": 15,
                    "endOffset": 20,
                    "serializedMemberCount": 1,
                    "valueCount": 0,
                }
                if complete_asset else None
            ),
            "completeAsset": complete_asset,
        },
        "opaqueRemainder": {
            "startOffset": boundary_end,
            "endOffset": len(data),
            "length": len(data) - boundary_end,
        },
        "evidenceBoundary": (
            "The 27-member root and empty three-list ActionSerializedMap are exact. "
            + (
                "The empty ParamListForGraph also closes the complete ActionMapAssetRaw; "
                if complete_asset else "The following ParamListForGraph remains opaque; "
            )
            + "all later top-level members remain one opaque remainder."
        ),
    }


def frame_levelscript_empty_action_map_sequential(data: bytes) -> dict[str, Any]:
    """Advance the current owner from an exact empty action map.

    The generated 27-member wrapper supplies the names and order.  Complex
    positive collections stop at their count word; null/empty collections and
    primitive fields advance a real cursor.  If that cursor reaches
    ``scriptId``, the terminal members are decoded positionally rather than by
    scanning for an identifier-shaped byte sequence.
    """
    action_map = frame_levelscript_empty_action_map_prefix(data)
    if not (action_map.get("actionMap") or {}).get("completeAsset"):
        raise LevelScriptTopLevelFramingError(
            "sequential owner prefix requires a complete empty ActionMapAssetRaw"
        )
    return _frame_levelscript_sequential_owner(
        data,
        action_map=action_map["actionMap"],
        owner_offset=int(action_map["bytesConsumed"]),
        action_map_boundary="complete empty action map",
        partial_status="exact_named_empty_action_map_owner_prefix",
    )


def frame_levelscript_null_action_map_sequential(data: bytes) -> dict[str, Any]:
    """Advance the current owner from an exact null ``actionMap`` union.

    The generated 27-member wrapper permits a null reference for its first
    member.  MemoryPack encodes that boundary as one ``0xff`` byte, so the
    following owner member begins physically at offset 2.  This lane shares
    the same generated-order owner and terminal codecs as the empty-map lane;
    it does not search for a suffix or reinterpret later bytes.
    """
    if not data or data[0] != 27:
        actual = data[0] if data else None
        raise LevelScriptTopLevelFramingError(
            f"LevelScriptData member count mismatch: expected=27 actual={actual}"
        )
    if len(data) < 2 or data[1] != 0xFF:
        raise LevelScriptTopLevelFramingError(
            "LevelScriptData does not have an exact null actionMap union"
        )
    return _frame_levelscript_sequential_owner(
        data,
        action_map={
            "startOffset": 1,
            "endOffset": 2,
            "value": None,
            "rawUnionTag": 0xFF,
            "unionTagEncoding": "memorypack-null-u8",
            "completeAsset": True,
        },
        owner_offset=2,
        action_map_boundary="null action map",
        partial_status="exact_named_null_action_map_owner_prefix",
    )


def decode_levelscript_action_map_lists(
    data: bytes,
    records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Decode the three `ActionSerializedMap` list boundaries.

    IL2CPP metadata names the runtime fields as `headerList`, `actionList`,
    and `getterList`. GameAssembly body recovery dispatches the generated
    wrapper setters as `actionList`, `getterList`, then `headerList`, and
    MetadataRegistration resolves those fields to `List<ActionBase>`,
    `List<PureGetter>`, and `List<ActionHeader>`. The compact LevelScript
    blobs follow the same physical order: the first count is in the actionMap
    header, and later counts sit immediately before the next UID record. Some
    two-block blobs omit an empty getter block and put a final header-shaped
    block after actionList; those are labeled as `headerList` by a conservative
    content check.
    """
    header = decode_levelscript_action_map_header(data)
    if not header:
        return {}
    out = dict(header)
    out["serializedListOrder"] = list(ACTION_SERIALIZED_MAP_LIST_ORDER)
    out["serializedListOrderEvidence"] = ACTION_SERIALIZED_MAP_ORDER_EVIDENCE
    if header.get("status") != "present":
        return _drop_empty(out)

    first_count = header.get("recordCount")
    if not isinstance(first_count, int) or first_count < 0:
        return _drop_empty(out)

    sorted_records = sorted(records or [], key=_record_start)
    record_count = len(sorted_records)
    lists: list[dict[str, Any]] = []

    def append_list(
        name: str,
        *,
        count: int | None,
        marker_offset: int | None,
        marker_value: int | None,
        start_index: int,
        source: str,
        status: str = "present",
    ) -> int:
        end_index = start_index
        if isinstance(count, int) and count >= 0:
            end_index = min(record_count, start_index + count)
        row: dict[str, Any] = {
            "name": name,
            "status": status,
            "count": count,
            "countOffset": _offset_hex(marker_offset),
            "countMarker": marker_value,
            "recordIndexStart": start_index,
            "recordIndexEnd": end_index,
            "decodedRecordCount": max(0, end_index - start_index),
            "source": source,
        }
        if isinstance(count, int) and record_count and start_index + count > record_count:
            row["status"] = "count-exceeds-decoded-records"
        lists.append(_drop_empty(row))
        return end_index

    index = append_list(
        "actionList",
        count=first_count,
        marker_offset=3,
        marker_value=first_count,
        start_index=0,
        source="actionMapHeader",
    )

    # An empty ActionSerializedMap is encoded as three consecutive zero list
    # counts immediately after the top-level ``02 03`` object marker.  This is
    # an exact corpus-wide shape in the current original export: every blob
    # whose actionList count is zero has zero getterList/headerList words at
    # offsets 7 and 11 as well.  Decode those words directly.  Looking for the
    # next UID boundary in this case can cross the action-map boundary and
    # misclassify unrelated LevelScript tail objects as executable records.
    if (
        first_count == 0
        and len(data) >= 15
        and _u32(data, 7) == 0
        and _u32(data, 11) == 0
    ):
        index = append_list(
            "getterList",
            count=0,
            marker_offset=7,
            marker_value=0,
            start_index=index,
            source="consecutiveEmptyListCount",
        )
        index = append_list(
            "headerList",
            count=0,
            marker_offset=11,
            marker_value=0,
            start_index=index,
            source="consecutiveEmptyListCount",
        )
        out["exactEmptyActionMap"] = True
        complete_asset = (
            len(data) >= 20
            and data[15] == 1
            and _u32(data, 16) == 0
        )
        out["completeEmptyActionMapAsset"] = complete_asset
        out["emptyMapBoundaryEndOffset"] = _offset_hex(20 if complete_asset else 15)
        if complete_asset:
            out["paramBlackboard"] = {
                "status": "present",
                "memberCount": 1,
                "valueCount": 0,
                "startOffset": "0xf",
                "endOffset": "0x14",
            }
        if record_count:
            lists.append({
                "name": "outsideSerializedActionMap",
                "status": "residual-uid-records-after-exact-empty-map",
                "count": record_count,
                "recordIndexStart": 0,
                "recordIndexEnd": record_count,
            })
        out["serializedLists"] = lists
        out["listCounts"] = {
            str(row.get("name")): row.get("count")
            for row in lists
            if row.get("name") in ACTION_SERIALIZED_MAP_LIST_ORDER
        }
        return _drop_empty(out)

    for name in ACTION_SERIALIZED_MAP_LIST_ORDER[1:]:
        if not sorted_records:
            lists.append({
                "name": name,
                "status": "records-not-provided",
                "recordIndexStart": index,
                "recordIndexEnd": index,
            })
            continue
        if index >= record_count:
            lists.append({
                "name": name,
                "status": "no-decoded-records-after-previous-list",
                "recordIndexStart": index,
                "recordIndexEnd": index,
            })
            continue
        marker_offset = _record_start(sorted_records[index]) - 4
        marker_value = _u32(data, marker_offset)
        remaining = record_count - index
        if marker_value == 0xFFFFFFFF:
            lists.append({
                "name": name,
                "status": "null-marker-or-unanchored",
                "countOffset": _offset_hex(marker_offset),
                "countMarker": marker_value,
                "recordIndexStart": index,
                "recordIndexEnd": index,
            })
            break
        if not _small_uid_list_count(marker_value, remaining):
            lists.append({
                "name": name,
                "status": "unknown-marker",
                "countOffset": _offset_hex(marker_offset),
                "countMarker": marker_value,
                "recordIndexStart": index,
                "recordIndexEnd": index,
            })
            break
        if (
            name == "getterList"
            and _block_looks_like_header_list(sorted_records[index : index + int(marker_value)])
            and _next_uid_block_relation(
                data,
                sorted_records,
                index + int(marker_value),
            )
            in {"none", "invalid-marker", "levelscript-tail-like"}
        ):
            lists.append({
                "name": "getterList",
                "status": "omitted-or-empty-before-headerList",
                "count": 0,
                "recordIndexStart": index,
                "recordIndexEnd": index,
                "decodedRecordCount": 0,
                "source": "inferredEmptyFromFinalHeaderLikeBlock",
            })
            index = append_list(
                "headerList",
                count=int(marker_value),
                marker_offset=marker_offset,
                marker_value=marker_value,
                start_index=index,
                source="uidBoundaryMarkerInferredHeaderList",
            )
            break
        index = append_list(
            name,
            count=int(marker_value),
            marker_offset=marker_offset,
            marker_value=marker_value,
            start_index=index,
            source="uidBoundaryMarker",
        )

    if record_count and index < record_count:
        lists.append({
            "name": "outsideSerializedActionMap",
            "status": "residual-uid-records",
            "count": record_count - index,
            "recordIndexStart": index,
            "recordIndexEnd": record_count,
        })

    out["serializedLists"] = lists
    out["listCounts"] = {
        str(row.get("name")): row.get("count")
        for row in lists
        if row.get("name") in ACTION_SERIALIZED_MAP_LIST_ORDER
    }
    return _drop_empty(out)


def frame_levelscript_empty_action_map_top_level(
    data: bytes,
) -> dict[str, Any]:
    """Frame a current ``LevelScriptData`` object with an empty action map.

    This is deliberately a *partial schema* reader.  It proves the outer
    27-member marker, the complete three-list ``ActionSerializedMap`` at the
    front, and one uniquely positioned tail that consumes through EOF.  Bytes
    between those two independently framed regions are returned as one opaque
    range; they are not assigned to fields or interpreted from setter order.

    Non-empty action maps stay unsupported until every polymorphic record can
    advance a real cursor. Candidate suffixes are found from their bounded byte
    grammar, not from a filename-derived identifier. Multiple exact candidates
    fail closed instead of selecting the highest-scoring one.
    """
    if not data:
        raise LevelScriptTopLevelFramingError("truncated LevelScriptData: empty payload")
    if data[0] != 27:
        raise LevelScriptTopLevelFramingError(
            f"LevelScriptData member count mismatch: expected=27 actual={data[0]}"
        )
    if len(data) < 15:
        raise LevelScriptTopLevelFramingError(
            "truncated ActionSerializedMap: expected at least 15 bytes"
        )

    action_map = decode_levelscript_action_map_lists(data, [])
    if action_map.get("exactEmptyActionMap") is not True:
        raise LevelScriptTopLevelFramingError(
            "unsupported non-empty or incomplete ActionSerializedMap"
        )
    action_map_end = 20 if action_map.get("completeEmptyActionMapAsset") else 15

    candidates: list[dict[str, Any]] = []
    for script_id_offset in range(
        action_map_end,
        max(action_map_end, len(data) - 19),
    ):
        candidate = levelscript_top_level_tail.decode_tail_candidate(
            data,
            script_id_offset,
        )
        trigger_volumes = candidate.get("triggerVolumes") or {}
        trigger_end = trigger_volumes.get("endOffset")
        try:
            trigger_end_int = int(str(trigger_end), 0)
        except (TypeError, ValueError):
            continue
        if (
            candidate.get("startShapeListStatus") not in {"null", "present"}
            or not candidate.get("startTypeName")
            or candidate.get("taskMapStatus") not in {"null", "present"}
            or candidate.get("taskMapCount") not in {None, 0}
            or trigger_volumes.get("status") not in {"null", "present"}
            or trigger_volumes.get("parseStatus") == "truncated"
            or trigger_end_int != len(data)
        ):
            continue
        candidates.append(candidate)

    if len(candidates) != 1:
        raise LevelScriptTopLevelFramingError(
            "LevelScriptData tail is not unique and exact: "
            f"candidates={len(candidates)} length={len(data)}"
        )

    tail = candidates[0]
    tail_start = int(tail["scriptIdOffset"])
    trigger_observation = tail.get("triggerVolumes") or {}
    opaque_ranges = []
    if tail_start > action_map_end:
        opaque_ranges.append({
            "startOffset": action_map_end,
            "endOffset": tail_start,
            "length": tail_start - action_map_end,
            "status": "opaque_unassigned_top_level_members",
        })
    return {
        "status": "exact_boundaries_with_opaque_top_level_range",
        "schemaStatus": "partial",
        "serializedMemberCount": 27,
        "bytesConsumed": len(data),
        "ranges": {
            "memberCount": {"startOffset": 0, "endOffset": 1},
            "actionSerializedMap": {
                "startOffset": 1,
                "endOffset": 15,
                "serializedMemberCount": 3,
                "rawListCounts": [0, 0, 0],
                "serializedFieldOrderStatus":
                    "unproven_for_current_native_build",
            },
            "paramBlackboard": (
                {
                    "startOffset": 15,
                    "endOffset": 20,
                    "serializedMemberCount": 1,
                    "valueCount": 0,
                }
                if action_map_end == 20 else None
            ),
            "opaqueTopLevelMembers": opaque_ranges,
            "suffixEnvelope": {
                "startOffset": tail_start,
                "endOffset": len(data),
            },
        },
        "suffixEnvelope": {
            "startOffset": tail_start,
            "endOffset": len(data),
            "anchorU64": int.from_bytes(
                data[tail_start : tail_start + 8],
                "little",
                signed=False,
            ),
            "firstCollection": tail.get("startShapeList") or {},
            "rawSelectorI32": tail.get("startTypeRaw"),
            "secondCollectionStatus": tail.get("taskMapStatus") or "",
            "secondCollectionCount": tail.get("taskMapCount"),
            "finalCollection": trigger_observation,
            "fieldIdentityStatus": "unproven_for_current_native_build",
        },
        "evidenceBoundary": (
            "Every file byte is assigned to an exact outer range, but the opaque "
            "middle is neither split into members nor given field semantics; "
            "the three zero ActionSerializedMap values are not assigned field "
            "names without a current-build formatter body."
        ),
    }


def frame_levelscript_terminal_suffix(data: bytes) -> dict[str, Any]:
    """Decode a unique named terminal suffix of ``LevelScriptData``.

    The current 27-member wrapper ends with ``scriptId``, ``startShapeList``,
    ``startType``, ``taskMap``, and ``triggerVolumes`` in that order.  This
    reader finds that sequence from its byte grammar; it never uses the source
    filename as an identifier.  Only null or empty task maps are accepted so
    every boundary advances a real cursor before the final trigger-volume map
    closes at physical EOF.
    """
    if not data or data[0] != 27:
        actual = data[0] if data else None
        raise LevelScriptTopLevelFramingError(
            f"LevelScriptData member count mismatch: expected=27 actual={actual}"
        )
    if len(data) < 25:
        raise LevelScriptTopLevelFramingError("truncated LevelScriptData terminal suffix")

    search_start = 2 if len(data) > 1 and data[1] == 0xFF else 7
    candidates: list[dict[str, Any]] = []
    for script_id_offset in range(search_start, len(data) - 19):
        script_id = int.from_bytes(
            data[script_id_offset : script_id_offset + 8], "little", signed=False
        )
        if not _is_plausible_levelscript_id(script_id):
            continue
        start_shape_offset = script_id_offset + 8
        start_shapes, cursor = levelscript_active_shapes.decode_shape_list(
            data, start_shape_offset
        )
        if cursor is None or start_shapes.get("status") not in {"null", "present"}:
            continue
        shapes = start_shapes.get("shapes") or []
        shape_count = start_shapes.get("count")
        if start_shapes.get("status") == "present" and (
            not isinstance(shape_count, int)
            or len(shapes) != shape_count
            or not all(levelscript_active_shapes._valid_active_shape(row) for row in shapes)
        ):
            continue
        start_type_offset = cursor
        start_type = _u32(data, start_type_offset)
        if start_type not in levelscript_top_level_tail.START_TYPE_NAMES:
            continue
        task_map_offset = start_type_offset + 4
        task_map_count = _u32(data, task_map_offset)
        if task_map_count not in {0, 0xFFFFFFFF}:
            continue
        trigger_offset = task_map_offset + 4
        trigger_volumes, end_offset = levelscript_trigger_volumes.decode_trigger_volume_map(
            data, trigger_offset
        )
        if (
            end_offset != len(data)
            or trigger_volumes.get("status") not in {"null", "present"}
            or trigger_volumes.get("parseStatus") == "truncated"
        ):
            continue
        candidates.append({
            "startOffset": script_id_offset,
            "scriptId": script_id,
            "scriptIdOffset": script_id_offset,
            "startShapeListOffset": start_shape_offset,
            "startShapeListEndOffset": cursor,
            "startShapeList": start_shapes,
            "startTypeOffset": start_type_offset,
            "startTypeRaw": start_type,
            "startType": levelscript_top_level_tail.START_TYPE_NAMES[start_type],
            "taskMapOffset": task_map_offset,
            "taskMapStatus": "null" if task_map_count == 0xFFFFFFFF else "empty",
            "taskMapCount": None if task_map_count == 0xFFFFFFFF else 0,
            "triggerVolumesOffset": trigger_offset,
            "triggerVolumes": trigger_volumes,
            "endOffset": end_offset,
        })

    if len(candidates) != 1:
        raise LevelScriptTopLevelFramingError(
            "LevelScriptData named terminal suffix is not unique and exact: "
            f"candidates={len(candidates)} length={len(data)}"
        )
    suffix = candidates[0]
    return {
        "status": "exact_named_terminal_suffix_with_opaque_prefix",
        "schemaStatus": "partial",
        "serializedMemberCount": 27,
        "bytesConsumed": len(data),
        "fieldOrder": [
            "scriptId", "startShapeList", "startType", "taskMap", "triggerVolumes"
        ],
        "ranges": {
            "memberCount": {"startOffset": 0, "endOffset": 1},
            "opaqueTopLevelPrefix": {
                "startOffset": 1,
                "endOffset": suffix["startOffset"],
                "length": suffix["startOffset"] - 1,
                "status": "opaque_unassigned_top_level_members",
            },
            "terminalSuffix": suffix,
        },
        "evidenceBoundary": (
            "The final five named LevelScriptData members advance an exact cursor "
            "through physical EOF without filename identity. Earlier top-level "
            "members remain one opaque range."
        ),
    }


def frame_levelscript_declared_root(
    data: bytes,
    declarations: Any,
    *,
    root: str = "LevelScriptData",
) -> dict[str, Any]:
    """Frame a whole LevelScriptData file from its derived root declaration.

    Unlike every framing above it, this one names the file rather than a part
    of it: the twenty-seven declared members are decoded in order and the
    cursor must land on physical EOF. A file that does not close is refused,
    so a partial read never reports as whole.

    This is the `direct` tier -- the declarations come from the build's
    managed image, not the native dispatcher -- but the closure is exact: no
    range is left opaque.
    """

    try:
        value, end = levelscript_action_map.decode_declared_root(
            data, 0, root, declarations
        )
    except levelscript_action_map.ActionMapCodecError as error:
        raise LevelScriptTopLevelFramingError(
            f"declared root did not decode: {error}"
        ) from error
    if end != len(data):
        raise LevelScriptTopLevelFramingError(
            f"declared root did not close at EOF: consumed={end} size={len(data)}"
        )
    return {
        "status": "exact_named_declared_root",
        "schemaStatus": "complete",
        "serializedMemberCount": value["memberCount"],
        "bytesConsumed": end,
        "ranges": {
            "memberCount": {"startOffset": 0, "endOffset": 1},
            "declaredRoot": {"startOffset": 1, "endOffset": end, "value": value},
        },
        "evidenceBoundary": (
            "Every byte is assigned to a declared member of the serialized "
            "root, with the cursor closing at physical EOF. Member identity is "
            "`direct`: read from the build's managed image, corroborated by "
            "the reviewed prefix and terminal framings agreeing with the head "
            "and tail of the declared member order."
        ),
    }


def frame_levelscript_declared_action_map(
    data: bytes,
    declarations: Any,
    *,
    expected_member_count: int = 27,
) -> dict[str, Any]:
    """Frame LevelScriptData through its complete action map.

    The prefix framing below names only the first record's envelope, because
    the reviewed layout contract covers a fraction of the unions the corpus
    uses. Given the derived declarations from
    `scripts.game_data.levelscript_union_layouts`, the whole
    ``ActionSerializedMap`` decodes instead, and the file's named region runs
    from its member count to the end of that map.

    This is the `direct` tier: the declarations are read from the build's
    managed image, not from the native dispatcher. Callers that publish an
    `exact` boundary must keep using the prefix framing.
    """

    if not data:
        raise LevelScriptTopLevelFramingError("truncated LevelScriptData: empty payload")
    if data[0] != expected_member_count:
        raise LevelScriptTopLevelFramingError(
            "root member count mismatch: "
            f"expected={expected_member_count} actual={data[0]}"
        )
    if len(data) < 2:
        raise LevelScriptTopLevelFramingError(
            "truncated ActionSerializedMap: missing raw object tag"
        )
    if data[1] == 0xFF:
        action_map, end = None, 2
    else:
        if data[1] != 0x02:
            raise LevelScriptTopLevelFramingError(
                f"unsupported ActionSerializedMap wrapper marker: {data[1]:#04x}"
            )
        try:
            action_map, end = levelscript_action_map.decode_action_serialized_map(
                data, 2, declarations=declarations
            )
        except levelscript_action_map.ActionMapCodecError as error:
            raise LevelScriptTopLevelFramingError(
                f"declared action map did not close: {error}"
            ) from error

    opaque = []
    if end < len(data):
        opaque.append({
            "startOffset": end,
            "endOffset": len(data),
            "length": len(data) - end,
            "status": "opaque_unassigned_top_level_members",
        })
    return {
        "status": "exact_named_declared_action_map",
        "schemaStatus": "partial",
        "serializedMemberCount": expected_member_count,
        "bytesConsumed": end,
        "ranges": {
            "memberCount": {"startOffset": 0, "endOffset": 1},
            "actionMap": {
                "startOffset": 1,
                "endOffset": end,
                "value": action_map,
            },
            "opaqueTopLevelMembers": opaque,
        },
        "evidenceBoundary": (
            "Every action, getter, header and condition in the map advances a "
            "real cursor through derived declarations; the later top-level "
            "members remain one opaque range. Union identity is `direct`, not "
            "read from the native dispatcher."
        ),
    }


def levelscript_action_map_membership(
    data: bytes,
    records: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[int, str]]:
    """Return serialized action-map membership labels keyed by record start."""
    action_map = decode_levelscript_action_map_lists(data, records)
    sorted_records = sorted(records or [], key=_record_start)
    memberships: dict[int, str] = {}
    for list_info in action_map.get("serializedLists") or []:
        name = str(list_info.get("name") or "")
        if name not in ACTION_SERIALIZED_MAP_LIST_ORDER:
            continue
        start_index = int(list_info.get("recordIndexStart") or 0)
        end_index = int(list_info.get("recordIndexEnd") or start_index)
        list_records = sorted_records[start_index:end_index]
        linked_starts: set[int] = set()
        if name == "actionList":
            by_local_id: dict[int, list[dict[str, Any]]] = {}
            for record in list_records:
                local_id = _record_local_id(record)
                if local_id is not None:
                    by_local_id.setdefault(local_id, []).append(record)
            unique_targets = {
                local_id: bucket[0]
                for local_id, bucket in by_local_id.items()
                if len(bucket) == 1
            }
            linked_starts = {
                _record_start(target)
                for record in list_records
                if (target := unique_targets.get(record.get("nextId"))) is not None
            }
        for rel_index, record in enumerate(list_records, start=1):
            start = _record_start(record)
            label = f"{name}#{rel_index}"
            if name == "actionList":
                role = "linked" if start in linked_starts else "root"
                label = f"{label} {role}"
            memberships[start] = label
    return action_map, memberships


def decode_levelscript_active_shape_list(
    data: bytes,
    script_id: int,
) -> dict[str, Any]:
    """Recover the authored active volume without an object-specific offset."""
    out: dict[str, Any] = {
        "schema": "levelScriptActiveShapeList.v1",
        "status": "unresolved",
        "candidateCount": 0,
    }
    if not data or data[0] != 27 or script_id <= 0:
        out["diagnostic"] = "topLevelMemberCountOrScriptId"
        return out

    records = extract_levelscript_uid_records(data)
    action_map = decode_levelscript_action_map_lists(data, records)
    sorted_records = sorted(records, key=_record_start)
    serialized_lists = [
        row
        for row in action_map.get("serializedLists") or []
        if row.get("name") in ACTION_SERIALIZED_MAP_LIST_ORDER
        and row.get("status") == "present"
        and isinstance(row.get("recordIndexEnd"), int)
    ]
    final_record_index = max(
        (int(row["recordIndexEnd"]) for row in serialized_lists),
        default=0,
    )
    if final_record_index <= 0 or final_record_index > len(sorted_records):
        out["diagnostic"] = "completeActionMapBoundaryMissing"
        return out

    tail_rows = [
        levelscript_top_level_tail.decode_tail_candidate(data, offset)
        for offset in _u64_offsets(data, script_id)
    ]
    if not tail_rows:
        out["diagnostic"] = "verifiedTopLevelScriptIdMissing"
        return out
    best_score = max(int(row.get("score") or 0) for row in tail_rows)
    best_tails = [row for row in tail_rows if int(row.get("score") or 0) == best_score]
    if len(best_tails) != 1:
        out.update({
            "diagnostic": "topLevelScriptIdBoundaryAmbiguous",
            "tailCandidateCount": len(best_tails),
        })
        return out

    final_record = sorted_records[final_record_index - 1]
    search_start = int(final_record.get("payloadStart") or final_record.get("start") or 0)
    search_end = int(best_tails[0].get("scriptIdOffset") or 0)
    candidates = levelscript_active_shapes.find_active_shape_candidates(
        data,
        search_start,
        search_end,
    )
    out.update({
        "candidateCount": len(candidates),
        "candidateOffsets": [row["offsetHex"] for row in candidates[:8]],
        "searchStartOffsetHex": _offset_hex(search_start),
        "searchEndOffsetHex": _offset_hex(search_end),
        "actionMapFinalList": str(serialized_lists[-1].get("name") or ""),
        "serializedMemberOrder": [
            "actionMap",
            "activeShapeList",
            "allowStartOnTravelPole",
            "allowTick",
            "enablePreload",
            "endType",
        ],
    })
    if len(candidates) != 1:
        out["diagnostic"] = (
            "activeShapeCandidateMissing"
            if not candidates
            else "activeShapeCandidateAmbiguous"
        )
        return out

    candidate = candidates[0]
    shape_list = candidate["shapeList"]
    out.update({
        "status": "decoded_unique",
        "offsetHex": candidate["offsetHex"],
        "endOffsetHex": candidate["endOffsetHex"],
        "count": shape_list.get("count"),
        "shapes": shape_list.get("shapes") or [],
        "followingFields": candidate["followingFields"],
        "evidenceBoundary": (
            "This recovers the authored activation geometry and exact adjacent "
            "MemoryPack fields. It does not prove the player position, runtime "
            "inside/outside classification, activation outcome, mission owner, "
            "event firing, or Story order."
        ),
    })
    return out


def decode_levelscript_action_map_details(
    data: bytes,
    *,
    sample_record_limit: int = 8,
    max_hint_records: int = 128,
) -> dict[str, Any]:
    tagged_strings = _extract_levelscript_tagged_ascii_strings(data)
    plain_strings = _extract_levelscript_plain_ascii_strings(
        data,
        tagged_offsets={int(hit.get("offset") or 0) for hit in tagged_strings},
    )
    records = extract_levelscript_uid_records(data, tagged_strings, plain_strings)
    action_map, memberships = levelscript_action_map_membership(data, records)
    list_status_counts: Counter[str] = Counter()
    for row in action_map.get("serializedLists") or []:
        name = str(row.get("name") or "")
        status = str(row.get("status") or "")
        if name or status:
            list_status_counts[f"{name}:{status}"] += 1

    membership_counts: Counter[str] = Counter()
    for label in memberships.values():
        label_text = str(label or "")
        if not label_text:
            continue
        list_name = label_text.split("#", 1)[0]
        if label_text.endswith(" root"):
            membership_counts[f"{list_name}:root"] += 1
        elif label_text.endswith(" linked"):
            membership_counts[f"{list_name}:linked"] += 1
        else:
            membership_counts[list_name] += 1

    record_code_counts: Counter[str] = Counter()
    hint_counts: Counter[str] = Counter()
    sample_rows: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        code = record.get("code")
        kind = record.get("kind")
        if isinstance(code, int) and isinstance(kind, int):
            record_code_counts[f"0x{code:04x}:0x{kind:02x}"] += 1
        next_start = _record_start(records[index + 1]) if index + 1 < len(records) else len(data)
        detail: dict[str, Any] = {}
        if index < max_hint_records:
            detail = decode_levelscript_record_payload(
                data,
                record,
                next_start=next_start,
                action_map_role=memberships.get(_record_start(record)),
            )
            label = (
                detail.get("label")
                or (detail.get("actionHeader") or {}).get("payloadShape")
                or detail.get("payloadShape")
                or ""
            )
            if label:
                hint_counts[str(label)] += 1
        if len(sample_rows) < sample_record_limit:
            sample: dict[str, Any] = {
                "offset": _offset_hex(_record_start(record)),
                "layout": record.get("layout"),
                "role": memberships.get(_record_start(record)) or "",
                "code": f"0x{code:04x}" if isinstance(code, int) else "",
                "kind": f"0x{kind:02x}" if isinstance(kind, int) else "",
                "localId": record.get("localId"),
                "nextId": record.get("nextId"),
                "uid": record.get("uid"),
                "strings": [str(hit.get("text") or "") for hit in (record.get("strings") or [])[:4]],
                "plainStrings": [str(hit.get("text") or "") for hit in (record.get("plainStrings") or [])[:4]],
            }
            label = (
                detail.get("label")
                or (detail.get("actionHeader") or {}).get("payloadShape")
                or detail.get("payloadShape")
                or ""
            )
            if label:
                sample["payloadHint"] = label
            sample_rows.append(_drop_empty(sample))

    return _drop_empty(
        {
            "actionMap": action_map,
            "uidRecordCount": len(records),
            "membershipCount": len(memberships),
            "taggedStringCount": len(tagged_strings),
            "plainStringCount": len(plain_strings),
            "listStatusCounts": dict(list_status_counts.most_common(12)),
            "membershipCounts": dict(membership_counts.most_common(12)),
            "recordCodeCounts": dict(record_code_counts.most_common(24)),
            "recordHintCounts": dict(hint_counts.most_common(24)),
            "recordHintSampledCount": min(len(records), max_hint_records),
            "sampleRecords": sample_rows,
        }
    )


def decode_embedded_action_serialized_map_audio(
    data: bytes,
    offset: int,
) -> dict[str, Any]:
    """Decode exact audio actions from an embedded ``ActionSerializedMap``.

    InteractiveTemplateData stores ``dataMap`` as the three-member
    ActionSerializedMap object directly, without LevelScriptData's outer
    object marker.  Adapt that exact boundary to the maintained LevelScript
    decoder, then accept only records proven to be physical ``actionList``
    members whose typed audio payload consumes the complete record body.
    """

    if offset < 0 or offset >= len(data) or data[offset] != 3:
        return {}
    adapted = b"\x00\x02" + data[offset:]
    tagged_strings = _extract_levelscript_tagged_ascii_strings(adapted)
    plain_strings = _extract_levelscript_plain_ascii_strings(
        adapted,
        tagged_offsets={int(hit.get("offset") or 0) for hit in tagged_strings},
    )
    records = extract_levelscript_uid_records(
        adapted,
        tagged_strings,
        plain_strings,
    )
    action_map, memberships = levelscript_action_map_membership(adapted, records)
    lists = action_map.get("serializedLists") or []
    list_rows = {
        str(row.get("name") or ""): row
        for row in lists
        if isinstance(row, dict)
    }
    action_list = list_rows.get("actionList") or {}
    if action_map.get("status") != "present" or action_list.get("status") != "present":
        return {}
    action_count = action_list.get("count")
    if not isinstance(action_count, int) or action_count < 0:
        return {}

    audio_actions: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        record_start = _record_start(record)
        role = str(memberships.get(record_start) or "")
        if not role.startswith("actionList#"):
            continue
        next_start = (
            _record_start(records[index + 1])
            if index + 1 < len(records)
            else len(adapted)
        )
        detail = decode_levelscript_record_payload(
            adapted,
            record,
            next_start=next_start,
            action_map_role=role,
        )
        audio_action = detail.get("audioAction")
        if not isinstance(audio_action, dict):
            continue
        consumed_bytes = audio_action.get("consumedBytes")
        payload_length = detail.get("payloadLength")
        exact_payload = consumed_bytes == payload_length
        if not exact_payload:
            trailing_counts = audio_action.get("trailingActionMapFramingU32s") or []
            next_role = str(memberships.get(next_start) or "")
            getter_count = (list_rows.get("getterList") or {}).get("count")
            header_count = (list_rows.get("headerList") or {}).get("count")
            exact_payload = (
                isinstance(consumed_bytes, int)
                and isinstance(payload_length, int)
                and (
                    (
                        payload_length - consumed_bytes == 4
                        and next_role.startswith("getterList#")
                        and trailing_counts == [getter_count]
                    )
                    or (
                        payload_length - consumed_bytes == 8
                        and next_role.startswith("headerList#")
                        and trailing_counts == [0, header_count]
                    )
                )
            )
        if not exact_payload:
            continue
        event_bindings = [
            dict(row)
            for row in audio_action.get("eventBindings") or []
            if isinstance(row, dict) and str(row.get("eventName") or "").strip()
        ]
        if not event_bindings:
            continue
        audio_actions.append(_drop_empty({
            "actionMapRole": role,
            "recordOffset": _offset_hex(offset + record_start - 2),
            "payloadOffset": _offset_hex(
                offset + int(record.get("payloadStart") or 0) - 2
            ),
            "unionTag": f"0x{int(record.get('code') or 0):04x}",
            "serializedMemberCount": record.get("kind"),
            "localId": record.get("localId"),
            "uid": record.get("uid"),
            "nextId": record.get("nextId"),
            "action": audio_action.get("action"),
            "fields": audio_action.get("fields") or {},
            "eventBindings": event_bindings,
            "payloadLength": detail.get("payloadLength"),
            "payloadShape": audio_action.get("payloadShape"),
            "nativeMappingId": audio_action.get("nativeMappingId"),
        }))

    return _drop_empty({
        "offset": _offset_hex(offset),
        "serializedMemberCount": 3,
        "serializedListOrder": list(ACTION_SERIALIZED_MAP_LIST_ORDER),
        "serializedListOrderEvidence": ACTION_SERIALIZED_MAP_ORDER_EVIDENCE,
        "listCounts": {
            name: row.get("count")
            for name in ACTION_SERIALIZED_MAP_LIST_ORDER
            for row in [list_rows.get(name) or {}]
            if isinstance(row.get("count"), int)
        },
        "decodedRecordCount": len(memberships),
        "audioActions": audio_actions,
        "evidence": (
            "exact embedded ActionSerializedMap boundary; physical actionList "
            "membership; complete current-build typed audio-action payload"
        ),
    })


def find_embedded_action_serialized_map_audio(
    data: bytes,
    *,
    start_offset: int = 0,
    max_action_count: int = 10_000,
) -> list[dict[str, Any]]:
    """Find uniquely claimed exact audio actions in embedded action maps.

    This is a structural scan, not a string scan: a candidate must begin with
    the three-member ActionSerializedMap header, expose a bounded action-list
    count, produce physical list membership, and consume a complete typed
    audio-action payload.  If two candidate map boundaries claim the same
    physical action record, the record is rejected as ambiguous.
    """

    claims: dict[tuple[str, int | None, str], list[dict[str, Any]]] = defaultdict(list)
    cursor = max(0, start_offset)
    while cursor + 5 <= len(data):
        candidate = data.find(b"\x03", cursor)
        if candidate < 0 or candidate + 5 > len(data):
            break
        cursor = candidate + 1
        action_count = _u32(data, candidate + 1)
        if (
            not isinstance(action_count, int)
            or action_count > max_action_count
        ):
            continue
        decoded = decode_embedded_action_serialized_map_audio(data, candidate)
        for action in decoded.get("audioActions") or []:
            if not isinstance(action, dict):
                continue
            record_offset = str(action.get("recordOffset") or "")
            local_id = action.get("localId") if isinstance(action.get("localId"), int) else None
            uid = str(action.get("uid") or "")
            if not record_offset or not uid:
                continue
            claims[(record_offset, local_id, uid)].append({
                "actionMapOffset": _offset_hex(candidate),
                "actionMapListCounts": decoded.get("listCounts") or {},
                **action,
            })
    rows: list[dict[str, Any]] = []
    for key in sorted(claims, key=lambda item: int(item[0], 16)):
        candidates = claims[key]
        if len(candidates) == 1:
            rows.append(candidates[0])
    return rows


def decode_levelscript_action_header_validation(
    data: bytes,
    header_local_id: int,
) -> dict[str, Any]:
    """Resolve one ActionHeader's exact serialized playback predicate.

    The resolver is deliberately identity-agnostic: it follows the header's
    ``_validate`` local getter reference through the decoded ActionMap and
    returns only an already exact getter family. Repeated local ids follow the
    installed ActionMapRuntime rule (the final serialized row owns the indexed
    runtime slot); unknown getter unions still fail closed.
    """
    if not data or not isinstance(header_local_id, int):
        return {}
    tagged_strings = _extract_levelscript_tagged_ascii_strings(data)
    plain_strings = _extract_levelscript_plain_ascii_strings(
        data,
        tagged_offsets={int(hit.get("offset") or 0) for hit in tagged_strings},
    )
    records = extract_levelscript_uid_records(data, tagged_strings, plain_strings)
    _action_map, memberships = levelscript_action_map_membership(data, records)
    matching_headers = [
        (index, record)
        for index, record in enumerate(records)
        if record.get("localId") == header_local_id
        and str(memberships.get(_record_start(record)) or "").startswith("headerList")
    ]
    if not matching_headers:
        return {}
    header_index, header_record = matching_headers[-1]
    header_next_start = (
        _record_start(records[header_index + 1])
        if header_index + 1 < len(records)
        else len(data)
    )
    header_detail = decode_levelscript_record_payload(
        data,
        header_record,
        next_start=header_next_start,
        action_map_role=memberships.get(_record_start(header_record)),
    )
    action_header = header_detail.get("actionHeader")
    if not isinstance(action_header, dict):
        return {}
    validate_param = action_header.get("validateParam")
    if not isinstance(validate_param, dict):
        return {}
    getter_local_id = action_header.get("validateGetterLocalId")
    if not isinstance(getter_local_id, int):
        if validate_param.get("payloadShape") != "action-header-validate-constant":
            return {}
        return {
            "status": "exact_current_build_memorypack_fields",
            "headerLocalId": header_local_id,
            "headerNextLocalId": action_header.get("nextId"),
            "validateParam": validate_param,
            "predicateType": "constant",
            "predicate": {"value": bool(validate_param.get("value"))},
        }
    getter_rows_by_id: dict[int, list[tuple[int, dict[str, Any]]]] = {}
    for index, record in enumerate(records):
        local_id = record.get("localId")
        if not isinstance(local_id, int):
            continue
        if not str(memberships.get(_record_start(record)) or "").startswith(
            "getterList"
        ):
            continue
        getter_rows_by_id.setdefault(local_id, []).append((index, record))

    def resolve_getter(
        local_id: int,
        stack: tuple[int, ...] = (),
    ) -> dict[str, Any]:
        if local_id in stack or len(stack) >= 64:
            return {}
        matching_getters = getter_rows_by_id.get(local_id) or []
        if not matching_getters:
            return {}
        getter_index, getter_record = matching_getters[-1]
        getter_next_start = (
            _record_start(records[getter_index + 1])
            if getter_index + 1 < len(records)
            else len(data)
        )
        getter_detail = decode_levelscript_record_payload(
            data,
            getter_record,
            next_start=getter_next_start,
            action_map_role=memberships.get(_record_start(getter_record)),
        )
        decoded_fields = [
            field
            for field in LEVELSCRIPT_EXACT_GETTER_FIELDS
            if isinstance(getter_detail.get(field), dict)
        ]
        if len(decoded_fields) != 1:
            return {}
        predicate_type = decoded_fields[0]
        predicate = getter_detail[predicate_type]
        children: list[dict[str, Any]] = []
        seen_refs: set[tuple[str, int]] = set()
        for ref in _predicate_local_getter_refs(predicate):
            ref_path = str(ref.get("path") or "")
            child_id = ref.get("getterLocalId")
            identity = (ref_path, child_id)
            if not isinstance(child_id, int) or identity in seen_refs:
                continue
            seen_refs.add(identity)
            child = resolve_getter(child_id, (*stack, local_id))
            if not child:
                return {}
            children.append({
                "path": ref_path,
                "getterLocalId": child_id,
                "predicate": child,
            })
        return {
            "predicateType": predicate_type,
            "predicate": predicate,
            "getterLocalId": local_id,
            "getterUnionTag": getter_detail.get("memoryPackUnionTag"),
            "getterSerializedMemberCount": getter_detail.get(
                "serializedMemberCount"
            ),
            "runtimeSlotStatus": "active-final-serialized-slot",
            "shadowedGetterRecordCount": len(matching_getters) - 1,
            "children": children,
        }

    predicate_tree = resolve_getter(getter_local_id)
    if not predicate_tree:
        return {}
    return {
        "status": "exact_current_build_memorypack_fields",
        "headerLocalId": header_local_id,
        "headerNextLocalId": action_header.get("nextId"),
        "validateParam": validate_param,
        "getterLocalId": getter_local_id,
        "getterUnionTag": predicate_tree.get("getterUnionTag"),
        "getterSerializedMemberCount": predicate_tree.get(
            "getterSerializedMemberCount"
        ),
        "runtimeSlotStatus": "active-final-serialized-slot",
        "shadowedHeaderRecordCount": len(matching_headers) - 1,
        "shadowedGetterRecordCount": predicate_tree.get(
            "shadowedGetterRecordCount", 0
        ),
        "predicateType": predicate_tree["predicateType"],
        "predicate": predicate_tree["predicate"],
        "predicateTree": predicate_tree,
    }


def decode_levelscript_record_payload(
    data: bytes,
    record: dict[str, Any] | None,
    *,
    next_start: int | None = None,
    action_map_role: str | None = None,
) -> dict[str, Any]:
    """Decode small, diagnostic LevelScript action-record payload hints.

    This deliberately stays conservative: labels are shape hints, not a full
    opcode table. ManualStart/ManualEnd are named only where ActionBase
    formatter tags prove the class; observed rows still do not serialize
    literal levelId + scriptId targets in the action payload.
    """
    if not data or not record:
        return {}
    code = record.get("code")
    kind = record.get("kind")
    if not isinstance(code, int) or not isinstance(kind, int):
        return {}
    key = (code, kind)
    semantic_key = levelscript_record_semantic_key(record)
    empty_audio_action_keys = {
        (0x00B7, 0x08),  # ExitCustomMusicMode
        (0x00E9, 0x08),  # FlushRadio
        (0x0372, 0x08),  # PostAudioStopAllEnemyVoice
    }
    record_payload_start = int(
        record.get("payloadStart", record.get("start", 0)) or 0
    )
    # An empty derived-field payload is represented by the next UID record
    # beginning exactly at payloadStart.  The general window helper expands
    # malformed/non-forward windows for diagnostic scans, so preserve this
    # exact zero-width shape before calling it.
    if (
        semantic_key in empty_audio_action_keys
        and next_start is not None
        and int(next_start) == record_payload_start
    ):
        payload_start, payload = record_payload_start, b""
    else:
        payload_start, payload = _record_payload_window(data, record, next_start)
    if not payload and semantic_key not in empty_audio_action_keys:
        return {}

    hint = dict(
        LEVELSCRIPT_RECORD_TAG_HINTS.get(semantic_key)
        or LEVELSCRIPT_RECORD_HINTS.get(key)
        or {}
    )
    action_map_role_text = str(action_map_role or "")
    header_role = action_map_role_text.startswith("headerList")
    getter_role = action_map_role_text.startswith("getterList")
    native_header_name = levelscript_native_header_name(
        record,
        allow_union_tag_fallback=header_role,
    )
    if native_header_name:
        hint.setdefault("label", native_header_name)
        hint.setdefault("confidence", "high")
        hint.setdefault(
            "note",
            "exact current-build ActionHeader formatter mapping; regenerate for other game builds",
        )
        hint.setdefault("nativeHeaderMappingId", LEVELSCRIPT_NATIVE_HEADER_MAPPING_ID)
    if (
        getter_role
        and record.get("unionTag") == 420
        and record.get("serializedMemberCount") == 8
    ):
        spawner_getter = decode_spawnerptr_getter_member(
            data,
            payload_start=record_payload_start,
            record_end=payload_start + len(payload),
        )
        if spawner_getter:
            hint["pureGetter"] = "SpawnerPtrGetter"
            hint["spawnerPtrGetter"] = spawner_getter
    fields = _decode_tagged_payload_fields(payload)
    texts = _record_text_values(record, fields)
    property_outputs = _extract_property_output_refs(texts)
    property_keys = [
        text
        for text in texts
        if _looks_like_property_key(text)
        and not levelscript_params.PROPERTY_OUTPUT_PATH_RE.match(text)
    ]
    trigger_slot_ids = (
        _extract_trigger_slot_ids(payload)
        if key in TRIGGER_VOLUME_RECORD_KEYS
        or native_header_name in {
            "ScriptEvent_OnLeaderEnterTriggerVolume",
            "ScriptEvent_OnLeaderLeaveTriggerVolume",
            "ScriptEvent_OnLeaderEnterTriggerVolumeList",
        }
        else []
    )
    out: dict[str, Any] = {
        "payloadStart": _offset_hex(payload_start),
        "payloadLength": len(payload),
        "payloadHexPrefix": payload[:48].hex(" "),
        "taggedFields": fields,
    }
    union_tag = record.get("unionTag")
    if isinstance(union_tag, int):
        out["memoryPackUnionTag"] = f"0x{union_tag:04x}"
    serialized_member_count = record.get("serializedMemberCount")
    if isinstance(serialized_member_count, int):
        out["serializedMemberCount"] = serialized_member_count
    if record.get("unionTagEncoding"):
        out["unionTagEncoding"] = record.get("unionTagEncoding")
    out.update(hint)
    action_header_code = header_role or bool(native_header_name)
    if action_header_code:
        action_header = _decode_action_header_prefix(payload)
        if action_header:
            filter_level = record.get("nextId")
            if isinstance(filter_level, int):
                action_header["filterLevel"] = filter_level
                action_header["filterLevelSource"] = "record-fixed-field"
            out["actionHeader"] = action_header
    event_detail = levelscript_entity_hp_changed.decode_entity_hp_changed_event(
        payload,
        semantic_key,
        header_role=header_role,
    )
    if event_detail:
        event_detail["payloadSchemaStatus"] = (
            "exact_current_build_memorypack_fields"
        )
        event_detail["payloadSchemaMappingId"] = (
            LEVELSCRIPT_NATIVE_EVENT_PAYLOAD_MAPPING_ID
        )
        out["nativeEventDetail"] = event_detail
    if property_outputs:
        out["propertyOutputRefs"] = property_outputs
    if header_role and "nativeEventDetail" not in out:
        event_detail = _decode_named_native_event_detail(
            native_header_name,
            payload,
            texts,
            property_outputs,
            trigger_slot_ids,
        )
        if event_detail:
            out["nativeEventDetail"] = event_detail
    if property_keys and (
        "propertyRole" in hint
        or key in {
            (0x04B8, 0x09),
            (0x104A, 0x00),
        }
    ):
        out["propertyKeys"] = property_keys[:8]
    if trigger_slot_ids:
        out["triggerSlotIds"] = trigger_slot_ids
    if semantic_key == (0x0003, 0x0A):
        gate = levelscript_property_gate.decode_compact_property_gate(payload)
        if gate:
            out["compactGate"] = gate
            gate_key = gate.get("propertyKey")
            if isinstance(gate_key, str) and gate_key and not gate_key.startswith("$"):
                property_keys = list(out.get("propertyKeys") or [])
                if gate_key not in property_keys:
                    property_keys.append(gate_key)
                out["propertyKeys"] = property_keys[:8]
            gate_refs = gate.get("gateLocalRefs") or []
            if gate_refs:
                out["gateLocalRefs"] = gate_refs
                out["gateRole"] = "conditional-local-ref"
    if semantic_key == (0x00ED, 0x0B):
        branch_refs = _extract_tail_local_refs(payload)
        if branch_refs:
            out["branchLocalRefs"] = branch_refs
            out["branchRole"] = "conditional-terminal-local-refs"
    control_flow = levelscript_control_flow.decode_control_flow_action(
        payload,
        semantic_key,
    )
    if control_flow:
        out.update(control_flow)
    switch_action = levelscript_switch_actions.decode_switch_action(
        payload,
        semantic_key,
    )
    if switch_action:
        out.update(switch_action)
    if semantic_key == (0x049E, 0x0F):
        start_dialog = _decode_start_dialog_action(payload)
        if start_dialog:
            out["startDialogAction"] = start_dialog
    if getter_role and semantic_key == (0x0347, 0x09):
        list_get_value_string = _decode_list_get_value_string(payload)
        if list_get_value_string:
            out["listGetValueString"] = list_get_value_string
    if semantic_key == (0x04F9, 0x0E):
        wait_trigger_volume = _decode_wait_for_seconds_in_trigger_volume_action(
            payload
        )
        if wait_trigger_volume:
            out.update(wait_trigger_volume)
    play3d_radio = levelscript_play3d_radio.decode_play3d_radio_action(
        payload,
        semantic_key,
    )
    if play3d_radio:
        out["play3DRadio"] = play3d_radio
    if semantic_key in {
        *levelscript_fmv.PLAY_FMV_ACTION_SEMANTIC_KEYS,
        (0x04A1, 0x10),
    }:
        fmv_action = levelscript_fmv.decode_fmv_action(
            payload,
            payload_start,
            semantic_key,
            record.get("strings") or [],
        )
        if fmv_action:
            out["fmvAction"] = fmv_action
    if semantic_key in {
        (0x0016, 0x09),
        (0x0028, 0x09),
        (0x0029, 0x09),
        (0x002A, 0x09),
        (0x0089, 0x0B),
        (0x0306, 0x09),
        (0x0307, 0x0B),
        (0x034C, 0x0C),
        (0x034E, 0x0B),
        (0x034F, 0x10),
        (0x034A, 0x14),
        (0x034B, 0x14),
        (0x0352, 0x0C),
        (0x0367, 0x11),
        (0x0368, 0x0B),
        (0x0369, 0x0A),
        (0x0363, 0x0D),
        (0x0364, 0x0D),
        (0x036B, 0x13),
        (0x036E, 0x14),
        (0x0372, 0x08),
        (0x0371, 0x0B),
        (0x0373, 0x0C),
        (0x03D5, 0x0F),
        (0x04A7, 0x0E),
        (0x04AC, 0x0A),
        (0x04B4, 0x0B),
        (0x04B5, 0x09),
        (0x04B7, 0x0A),
        (0x04BA, 0x09),
        (0x04BC, 0x0B),
        (0x04CA, 0x09),
        (0x00B7, 0x08),
        (0x00E9, 0x08),
    }:
        # Audio ActionBase formatter tags are reused by getter/header unions
        # in the same LevelScript stream (notably 0x0016/9).  The maintained
        # ActionMap membership is the exact owning-union discriminator; do
        # not promote a same-tag getter payload into an audio request.
        if action_map_role_text.startswith("actionList"):
            audio_action = _decode_audio_action(payload, semantic_key)
            if audio_action:
                out["audioAction"] = audio_action
    npc_patrol_start = levelscript_npc_patrol_start.decode_npc_patrol_start_action(
        payload,
        semantic_key,
    )
    if npc_patrol_start:
        out["npcPatrolStart"] = npc_patrol_start
    exit_custom_performance = (
        levelscript_exit_performance.decode_exit_level_custom_performance_action(
            payload,
            semantic_key,
        )
    )
    if exit_custom_performance:
        out["exitLevelCustomPerformance"] = exit_custom_performance
    if semantic_key == (0x04CA, 0x09):
        toggle_clear_screen = _decode_toggle_clear_screen_but_radio_action(
            payload
        )
        if toggle_clear_screen:
            out["toggleClearScreenButRadio"] = toggle_clear_screen
    if semantic_key == (0x02FE, 0x0A):
        main_char_move_to = _decode_main_char_move_to_action(payload)
        if main_char_move_to:
            out["mainCharMoveTo"] = main_char_move_to
    if semantic_key == (0x0034, 0x0E):
        call_server = levelscript_call_server.decode_call_server_action(payload)
        if call_server:
            record_uid = str(record.get("uid") or "").strip()
            event_name = str(call_server.get("eventName") or "").strip()
            if (
                re.fullmatch(r"[0-9a-fA-F]{8}", record_uid)
                and event_name.casefold() == f"#{record_uid}".casefold()
            ):
                call_server.update({
                    "eventNameIdentity": "record-uid-prefixed",
                    "callbackCorrelationLabel": True,
                    "storyGraphRole": "diagnostic-only",
                    "missionOwnershipEvidence": False,
                    "orderEvidence": False,
                })
            out["callServer"] = call_server
    if semantic_key == (0x0166, 0x0A):
        list_add = _decode_list_add_value_entity_ptr(payload)
        if list_add:
            out["listAddValueEntityPtr"] = list_add
    raise_custom_script_event = (
        levelscript_custom_event.decode_raise_custom_script_event_action(
            payload,
            semantic_key,
            texts,
        )
    )
    if raise_custom_script_event:
        out["raiseCustomScriptEvent"] = raise_custom_script_event
    if semantic_key == (0x0028, 0x0A):
        entity_compare = _decode_entity_compare_getter(payload, property_outputs)
        if entity_compare:
            out["entityCompare"] = entity_compare
    if getter_role and semantic_key in {
        (0x0004, 0x0A),
        (0x0006, 0x09),
        (0x000A, 0x08),
        (0x000B, 0x08),
        (0x000D, 0x09),
        (0x0013, 0x0A),
        (0x0016, 0x09),
        (0x001F, 0x0A),
        (0x004E, 0x08),
        (0x0049, 0x0A),
        (0x0100, 0x09),
        (0x012F, 0x08),
        (0x0133, 0x09),
        (0x013A, 0x08),
        (0x017C, 0x08),
        (0x0184, 0x08),
        (0x01A5, 0x08),
        (0x01AA, 0x0A),
        (0x01AC, 0x09),
        (0x01AD, 0x0A),
        (0x01BA, 0x09),
        (0x01C2, 0x08),
    }:
        getter_payload = _getter_subtype_payload(data, record, next_start)
        scalar_field, scalar_detail = (
            levelscript_scalar_getters.decode_scalar_value_getter(
                getter_payload,
                semantic_key,
            )
        )
        if scalar_field and scalar_detail:
            out[scalar_field] = scalar_detail
        elif semantic_key == (0x013A, 0x08):
            mission_state_getter = _decode_get_mission_state_getter(getter_payload)
            if mission_state_getter:
                out["getMissionState"] = mission_state_getter
        elif semantic_key == (0x0013, 0x0A):
            stage_check = _decode_check_levelscript_stage_getter(getter_payload)
            if stage_check:
                out["checkLevelScriptStage"] = stage_check
        elif semantic_key == (0x0016, 0x09):
            completion_check = _decode_check_mission_or_quest_complete_getter(
                getter_payload
            )
            if completion_check:
                out["checkMissionOrQuestIsComplete"] = completion_check
        elif semantic_key == (0x001F, 0x0A):
            mission_state_compare = _decode_compare_mission_state_getter(
                getter_payload
            )
            if mission_state_compare:
                out["compareMissionState"] = mission_state_compare
        elif semantic_key in {
            (0x0004, 0x0A),
            (0x0006, 0x09),
            (0x000A, 0x08),
            (0x000B, 0x08),
            (0x000D, 0x09),
        }:
            field_name, boolean_detail = (
                levelscript_boolean_getters.decode_boolean_getter_fields(
                    getter_payload,
                    semantic_key,
                )
            )
            if field_name and boolean_detail:
                out[field_name] = boolean_detail
        elif semantic_key == (0x004E, 0x08):
            condition_result = _decode_get_condition_result_getter(
                getter_payload
            )
            if condition_result:
                out["getConditionResult"] = condition_result
        elif semantic_key == (0x0100, 0x09):
            property_bool = _decode_levelscript_property_bool_getter(
                getter_payload
            )
            if property_bool:
                out["getLevelScriptPropertyGenericBool"] = property_bool
        elif semantic_key == (0x012F, 0x08):
            levelscript_stage = _decode_get_levelscript_stage_getter(
                getter_payload
            )
            if levelscript_stage:
                out["getLevelScriptStage"] = levelscript_stage
        elif semantic_key == (0x0133, 0x09):
            lsm_completed = _decode_get_lsm_is_completed_getter(getter_payload)
            if lsm_completed:
                out["getLsmIsCompleted"] = lsm_completed
        elif semantic_key == (0x017C, 0x08):
            field_name, boolean_detail = (
                levelscript_boolean_getters.decode_boolean_getter_fields(
                    getter_payload,
                    semantic_key,
                )
            )
            if field_name and boolean_detail:
                out[field_name] = boolean_detail
        elif semantic_key == (0x01AD, 0x0A):
            interactive_state = _decode_interactive_check_state_getter(
                getter_payload
            )
            if interactive_state:
                out["interactiveCheckState"] = interactive_state
    if key in levelscript_manual_control.MANUAL_CONTROL_ACTIONS:
        manual_control = levelscript_manual_control.decode_manual_levelscript_control(
            payload,
            key,
        )
        if manual_control:
            out["manualControl"] = manual_control

    if semantic_key == (0x04F7, 0x09) and payload[:1] == b"\x04" and len(payload) >= 5:
        out["seconds"] = _round_float(struct.unpack_from("<f", payload, 1)[0])
    elif key in SCRIPT_POINTER_REF_RECORDS:
        pointer = decode_script_pointer_payload(data, record)
        if pointer:
            out.setdefault("label", "script-ptr-scalar-ref")
            out.setdefault("confidence", "medium")
            out.setdefault("note", (
                "LevelScriptPtr plus scalar parameter; matches trigger-volume predicate/action field shape, "
                "not ManualStart/ManualEnd because no levelId string is serialized"
            ))
            out["scriptPointer"] = pointer
        else:
            out.setdefault("label", "scalar-control")
            out.setdefault("confidence", "low")
            out.setdefault("note", (
                "same opcode family as script-pointer refs, but this payload does not contain "
                "a plausible LevelScript id"
            ))
    elif key == (0x0463, 0x09) and len(payload) >= 4:
        count = struct.unpack_from("<I", payload, 0)[0]
        if count <= 64 and 4 + count * 4 <= len(payload):
            out["localRecordRefs"] = [
                struct.unpack_from("<I", payload, 4 + index * 4)[0]
                for index in range(count)
            ]
    elif semantic_key in {(0x02EE, 0x09), (0x030E, 0x09)}:
        for text in texts:
            if text.startswith("guide_") and not text.startswith("$"):
                out["guideId"] = text
                break
    elif key == (0x104A, 0x00):
        texts = [
            str(hit.get("text") or "")
            for hit in (record.get("strings") or []) + (record.get("plainStrings") or [])
            if isinstance(hit, dict) and hit.get("text")
        ]
        if texts:
            out["signalKeys"] = texts[:4]
    return _drop_empty(out)


def decode_levelscript_binary_summary(data: bytes, script_id: int) -> dict[str, Any]:
    """Decode stable top-level LevelScriptData facts from a raw blob.

    This intentionally handles only fields whose byte positions can be verified
    cheaply from the IL2CPP MemoryPack setter order. It does not parse action
    records or promote start/end semantics into order edges.
    """
    if not data or script_id <= 0:
        return {}
    action_map = decode_levelscript_action_map_header(data)
    offsets = _u64_offsets(data, script_id)
    candidates = [
        levelscript_top_level_tail.decode_tail_candidate(data, offset)
        for offset in offsets
    ]
    best = max(candidates, key=lambda item: int(item.get("score") or 0), default={})
    active_shapes = decode_levelscript_active_shape_list(data, script_id)
    return {
        "serializedMemberCount": data[0],
        "expectedMemberCount": 27,
        "actionMapStatus": action_map.get("status") or "",
        "actionMapRecordCount": action_map.get("recordCount"),
        "actionMapRecordStartOffsetHex": action_map.get("recordStartOffsetHex") or "",
        "actionMapHeader": action_map,
        "scriptId": str(script_id),
        "scriptIdOffsets": [f"0x{offset:x}" for offset in offsets],
        "scriptIdOccurrenceCount": len(offsets),
        "scriptIdVerified": bool(offsets),
        "probableScriptIdOffset": best.get("scriptIdOffset"),
        "probableScriptIdOffsetHex": best.get("scriptIdOffsetHex") or "",
        "activeShapeList": active_shapes,
        "activeShapeListStatus": active_shapes.get("status") or "",
        "activeShapeListCount": active_shapes.get("count"),
        "activeShapeListShapes": active_shapes.get("shapes") or [],
        "startShapeListStatus": best.get("startShapeListStatus") or "",
        "startShapeListCount": best.get("startShapeListCount"),
        "startShapeListDetails": best.get("startShapeList") or {},
        "startShapeListShapes": (best.get("startShapeList") or {}).get("shapes") or [],
        "startTypeOffset": best.get("startTypeOffset"),
        "startTypeOffsetHex": best.get("startTypeOffsetHex") or "",
        "startTypeRaw": best.get("startTypeRaw"),
        "startTypeName": best.get("startTypeName") or "",
        "taskMapOffsetHex": best.get("taskMapOffsetHex") or "",
        "taskMapStatus": best.get("taskMapStatus") or "",
        "taskMapCount": best.get("taskMapCount"),
        "triggerVolumesOffsetHex": best.get("triggerVolumesOffsetHex") or "",
        "triggerVolumesStatus": best.get("triggerVolumesStatus") or "",
        "triggerVolumesCount": best.get("triggerVolumesCount"),
        "triggerVolumesDetails": best.get("triggerVolumes") or {},
        "triggerVolumeSlotIds": (best.get("triggerVolumes") or {}).get("slotIds") or [],
        "note": (
            "current 27-member top-level MemoryPack plus actionMap header and "
            "unique active shape, scriptId/startType/shape-list trigger fields decoded; "
            "final current-build Leader trigger-volume maps include exact slot and geometry; "
            "action start/end opcodes are still not decoded"
        ),
    }


def decode_levelscript_binary_file(path: Path, script_id: int | str) -> dict[str, Any]:
    try:
        numeric_script_id = int(script_id)
    except (TypeError, ValueError):
        return {}
    try:
        data = read_bytes_cached(path)
    except OSError:
        return {}
    return decode_levelscript_binary_summary(data, numeric_script_id)
