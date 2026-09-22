"""Exact codecs for the named LevelScript getter and check payloads.

Moved verbatim out of ``scripts/game_data/levelscript_binary.py``.
"""

from __future__ import annotations

import re
import struct

from scripts.game_data.codecs.levelscript import params as levelscript_params
from scripts.game_data.codecs.levelscript import script_event_scope as levelscript_script_event_scope
from scripts.game_data.codecs.levelscript.condition_params import _decode_levelscript_ptr_param
from scripts.game_data.codecs.levelscript.params import DEFAULT_PARAM_TAIL as _DEFAULT_PARAM_TAIL
from scripts.game_data.codecs.levelscript.params import decode_bool_param as _decode_bool_param
from scripts.game_data.codecs.levelscript.params import decode_constant_string_param as _decode_constant_string_param
from scripts.game_data.codecs.levelscript.params import decode_i32_param as _decode_i32_param
from scripts.game_data.codecs.levelscript.params import decode_param_tail as _decode_param_tail
from scripts.game_data.codecs.levelscript.task_conditions import _decode_levelscript_task_condition
from typing import Any

def _decode_interactive_check_state_getter(payload: bytes) -> dict[str, Any]:
    """Decode comparer, ScriptEntityPtr target, and expected state exactly."""
    comparer = _decode_i32_param(payload, 0)
    if comparer is None:
        return {}
    target = levelscript_params.decode_constant_entity_ptr_param(payload, comparer[1])
    if target is None:
        return {}
    value = _decode_i32_param(payload, target[1])
    if value is None:
        return {}
    comparer_raw = comparer[0]["value"]
    return levelscript_params.finish_getter_fields(payload, value[1], {
        "type": "InteractiveCheckState",
        "comparer": comparer[0],
        "comparerName": {
            0: "Equal",
            1: "NotEqual",
            2: "GreaterThan",
            3: "GreaterEqual",
            4: "LessThan",
            5: "LessEqual",
        }.get(comparer_raw, ""),
        "target": target[0],
        "value": value[0],
        "payloadShape": "comparer-entity-ptr-state-exact-fields",
        "nativeMappingId": "gameassembly-2026-08-02-interactive-check-state",
    })


def _decode_get_lsm_is_completed_getter(payload: bytes) -> dict[str, Any]:
    """Decode the two formatter fields used by ``GetLsmIsCompleted``.

    The first field is the current fixed-width ``Param<LsmPtr>`` value.  Its
    inner eight-byte value is retained losslessly because the pointer's bit
    allocation is not needed to establish the predicate.  The second field is
    the already-proven ``Param<LevelScriptPtr>`` representation.
    """
    if len(payload) < 21 or payload[:2] != b"\x04\x03":
        return {}
    lsm_tail = _decode_param_tail(payload, 9)
    if lsm_tail is None or lsm_tail[1] != 21:
        return {}
    script_ptr = _decode_levelscript_ptr_param(payload, 21)
    if script_ptr is None:
        return {}
    return levelscript_params.finish_getter_fields(payload, script_ptr[1], {
        "type": "GetLsmIsCompleted",
        "lsmPtr": {
            "rawValueHex": payload[1:9].hex(),
            **lsm_tail[0],
        },
        "scriptPtr": script_ptr[0],
        "resultField": "LevelScriptModule.isCompleted",
        "payloadShape": "lsm-ptr-and-level-script-ptr-exact-fields",
        "nativeMappingId": "gameassembly-2026-08-02-get-lsm-is-completed",
    })


def _decode_get_condition_result_getter(payload: bytes) -> dict[str, Any]:
    """Decode the embedded root ``GameCondition`` union used by this getter."""
    decoded = _decode_levelscript_task_condition(payload, 0, len(payload))
    if decoded is None:
        return {}
    condition, end = decoded
    return levelscript_params.finish_getter_fields(payload, end, {
        "condition": condition,
        "payloadShape": "root-game-condition-union-exact-fields",
    })


def _decode_start_dialog_action(payload: bytes) -> dict[str, Any]:
    """Decode the exact dynamic dialog getter reference in StartDialogAction."""
    if len(payload) < 17 or payload[0] != 0x04:
        return {}
    constant_size, getter_local_id, param_source, path_size = struct.unpack_from(
        "<iiii", payload, 1
    )
    if not (
        constant_size == -1
        and 0 <= getter_local_id <= 0x10000
        and param_source == -1
        and path_size == -1
    ):
        return {}
    return {
        "dialogGetterLocalId": getter_local_id,
        "constantDialogId": None,
        "paramSource": param_source,
        "path": None,
        "payloadShape": "null-dialog-value-local-getter-ref-exact-prefix",
    }


def _decode_get_levelscript_stage_getter(payload: bytes) -> dict[str, Any]:
    script_ptr = _decode_levelscript_ptr_param(payload, 0)
    if script_ptr is None:
        return {}
    return levelscript_params.finish_getter_fields(payload, script_ptr[1], {
        "scriptPtr": script_ptr[0],
        "payloadShape": "level-script-ptr-param-exact-fields",
    })


def _decode_levelscript_property_bool_getter(payload: bytes) -> dict[str, Any]:
    property_key = _decode_constant_string_param(payload, 0)
    if property_key is None:
        return {}
    target = _decode_levelscript_ptr_param(payload, property_key[1])
    if target is None:
        return {}
    return levelscript_params.finish_getter_fields(payload, target[1], {
        "propertyKey": property_key[0],
        "targetScript": target[0],
        "payloadShape": "property-key-and-level-script-target-exact-fields",
    })


def _decode_get_mission_state_getter(payload: bytes) -> dict[str, Any]:
    """Decode the exact current-build ``GetMissionState._missionId`` field."""
    mission_param = _decode_constant_string_param(payload, 0)
    if mission_param is None or mission_param[1] != len(payload):
        return {}
    mission_id = mission_param[0]
    if not mission_id or not re.fullmatch(r"[A-Za-z0-9_#-]+", mission_id):
        return {}
    return {
        "type": "GetMissionState",
        "missionId": mission_id,
        "payloadShape": "constant-mission-id-exact-eof",
        "serializedMemberCount": 8,
        "pureGetterUnionTag": "0x013a",
        "nativeMappingId": (
            "gameassembly-2026-07-11-puregetter-mission-state"
        ),
        "executionSide": "client",
        "networkRole": "reads_synchronized_local_mission_state",
        "serverExchange": False,
    }


def _decode_compare_mission_state_getter(payload: bytes) -> dict[str, Any]:
    """Decode exact comparer/getter/state operands for ``CompareMissionState``."""
    if len(payload) != 51:
        return {}
    comparer = levelscript_params.decode_constant_i32_param(payload, 0)
    expected_state = levelscript_params.decode_constant_i32_param(payload, 34)
    if comparer is None or comparer[1] != 17 or expected_state is None:
        return {}
    if expected_state[1] != len(payload):
        return {}
    value_a = payload[17:34]
    if (
        value_a[:5] != b"\x04\x00\x00\x00\x00"
        or value_a[9:] != b"\xff" * 8
    ):
        return {}
    source_getter_local_id = struct.unpack_from("<i", value_a, 5)[0]
    if source_getter_local_id < 0 or source_getter_local_id > 0x10000:
        return {}
    return {
        "type": "CompareMissionState",
        "comparerRaw": comparer[0],
        "comparerName": {
            0: "Equal",
            1: "NotEqual",
        }.get(comparer[0], ""),
        "valueAGetterLocalId": source_getter_local_id,
        "valueBStateRaw": expected_state[0],
        "valueBStateName": {
            0: "None",
            1: "Available",
            2: "Processing",
            3: "Completed",
            4: "Failed",
            5: "Disabled",
        }.get(expected_state[0], ""),
        "payloadShape": "comparer-getter-ref-state-constant-exact-eof",
        "serializedMemberCount": 10,
        "pureGetterUnionTag": "0x001f",
        "nativeMappingId": (
            "gameassembly-2026-07-11-puregetter-mission-state"
        ),
    }


def _decode_check_levelscript_stage_getter(payload: bytes) -> dict[str, Any]:
    """Decode the current generic LevelScript-stage comparison getter.

    Current metadata names the runtime fields ``_scriptPtr``, ``_comparer``,
    and ``_value``.  The generated MemoryPack setter order is comparer,
    scriptPtr, value; the native ``GetResult`` body resolves the script, reads
    its stage, and passes the operands to ``ComparerExtensions.DoCompare``.
    """
    comparer = _decode_i32_param(payload, 0)
    if comparer is None:
        return {}
    script_ptr = _decode_levelscript_ptr_param(payload, comparer[1])
    if script_ptr is None:
        return {}
    expected_stage = _decode_i32_param(payload, script_ptr[1])
    if expected_stage is None:
        return {}
    comparer_raw = comparer[0]["value"]
    return levelscript_params.finish_getter_fields(payload, expected_stage[1], {
        "type": "CheckLevelScriptStage",
        "scriptPtr": script_ptr[0],
        "comparer": comparer[0],
        "comparerName": {
            0: "Equal",
            1: "NotEqual",
            2: "GreaterThan",
            3: "GreaterEqual",
            4: "LessThan",
            5: "LessEqual",
        }.get(comparer_raw, ""),
        "expectedStage": expected_stage[0],
        "payloadShape": "comparer-level-script-ptr-stage-exact-fields",
        "serializedMemberCount": 10,
        "pureGetterUnionTag": "0x0013",
        "nativeMappingId": "gameassembly-2026-08-02-check-levelscript-stage",
        "executionSide": "client",
        "serverExchange": False,
    })


def _decode_check_mission_or_quest_complete_getter(
    payload: bytes,
) -> dict[str, Any]:
    """Decode the current mission/quest completion predicate.

    The generated formatter writes ``_isQuest`` followed by ``_missionId``.
    The native ``GetResult`` body selects MissionSystem.GetQuestState when the
    flag is true and GetMissionData otherwise, and accepts state value 3 in
    both paths.
    """
    is_quest = _decode_bool_param(payload, 0)
    if is_quest is None:
        return {}
    identity = _decode_constant_string_param(payload, is_quest[1])
    if identity is None:
        return {}
    mission_or_quest_id = identity[0]
    if not re.fullmatch(r"[A-Za-z0-9_#-]+", mission_or_quest_id):
        return {}
    target_kind = "quest" if is_quest[0]["value"] else "mission"
    return levelscript_params.finish_getter_fields(payload, identity[1], {
        "type": "CheckMissionOrQuestIsComplete",
        "isQuest": is_quest[0],
        "targetKind": target_kind,
        "missionOrQuestId": mission_or_quest_id,
        "completedStateRaw": 3,
        "completedStateName": "Completed",
        "payloadShape": "is-quest-and-identity-exact-fields",
        "serializedMemberCount": 9,
        "pureGetterUnionTag": "0x0016",
        "nativeMappingId": "gameassembly-2026-08-02-check-mission-or-quest-complete",
        "executionSide": "client",
        "networkRole": "reads_synchronized_local_mission_or_quest_state",
        "serverExchange": False,
    })


def _decode_script_variable_changed_fields(
    payload: bytes,
    *,
    blackboard: bool,
) -> dict[str, Any]:
    """Decode exact SELF/specified-script variable-listener operands.

    The generated current-build formatters order the subtype members as
    ``key, oldValue, value`` for BB variables and ``oldValue, propertyKey,
    value`` for LevelScript properties.  Requiring exact EOF prevents strings
    in later action records from being mistaken for listener keys.
    """
    scope = levelscript_script_event_scope.decode_script_event_header_scope(payload)
    cursor = scope.pop("_subtypeOffset", None)
    if not scope or not isinstance(cursor, int):
        return {}

    if blackboard:
        key_param = _decode_constant_string_param(payload, cursor)
        if key_param is None:
            return {}
        key, cursor = key_param
        old_output = levelscript_params.decode_param_output_ref(payload, cursor)
        if old_output is None:
            return {}
        old_ref, cursor = old_output
    else:
        old_output = levelscript_params.decode_param_output_ref(payload, cursor)
        if old_output is None:
            return {}
        old_ref, cursor = old_output
        key_param = _decode_constant_string_param(payload, cursor)
        if key_param is None:
            return {}
        key, cursor = key_param

    value_output = levelscript_params.decode_param_output_ref(payload, cursor)
    if value_output is None:
        return {}
    value_ref, cursor = value_output
    if cursor != len(payload):
        return {}
    return {
        **scope,
        ("blackboardKeyFilter" if blackboard else "propertyKeyFilter"): key,
        "oldValueOutputRef": old_ref,
        "valueOutputRef": value_ref,
        "payloadShape": (
            "constant-blackboard-key-and-output-refs-exact-eof"
            if blackboard
            else "constant-property-key-and-output-refs-exact-eof"
        ),
    }


def _decode_leader_trigger_volume_fields(payload: bytes) -> dict[str, Any]:
    """Decode the exact ScriptEvent trigger-slot selector prefix.

    Some records are followed by serialized trigger-volume configuration before
    the next UID record.  Only the inherited scope and first subtype parameters
    belong to the receiver, so this intentionally validates that prefix rather
    than scanning every integer in the wider record window.
    """
    scope = levelscript_script_event_scope.decode_script_event_header_scope(payload)
    cursor = scope.pop("_subtypeOffset", None)
    if not scope or not isinstance(cursor, int):
        return {}
    subtype_offset = cursor
    slot_param = levelscript_params.decode_constant_i32_param(payload, cursor)
    if slot_param is None:
        return {}
    slot_id, cursor = slot_param
    output_ref: str | None = None
    output_param: dict[str, Any] | None = None
    if cursor < len(payload) and payload[cursor] == 0xFF:
        cursor += 1
    else:
        output = levelscript_params.decode_param_output(payload, cursor)
        if output is None:
            return {}
        output_param, cursor = output
        candidate_ref = output_param.get("path")
        if (
            output_param.get("paramSource") == 0
            and isinstance(candidate_ref, str)
            and levelscript_params.PROPERTY_OUTPUT_PATH_RE.match(candidate_ref)
        ):
            output_ref = candidate_ref
    return {
        **scope,
        "triggerSlotIdFilter": slot_id,
        "triggerSlotIdOutputRef": output_ref,
        "triggerSlotIdOutputParam": output_param,
        "subtypeConsumedBytes": cursor - subtype_offset,
        "payloadShape": "constant-trigger-slot-selector-prefix",
    }


def _decode_leader_trigger_volume_list_fields(payload: bytes) -> dict[str, Any]:
    """Decode the complete constant ``_triggerSlotIds`` Param<List<int>>.

    Only the exact constant tag, bounded list, and complete ordinary Param
    tail are accepted. Bytes after that tail belong to the surrounding
    LevelScriptData container and are deliberately not scanned.
    """
    scope = levelscript_script_event_scope.decode_script_event_header_scope(payload)
    cursor = scope.pop("_subtypeOffset", None)
    if not scope or not isinstance(cursor, int) or cursor + 17 > len(payload):
        return {}
    subtype_offset = cursor
    if payload[cursor] != 0x04:
        return {}
    cursor += 1
    count = struct.unpack_from("<i", payload, cursor)[0]
    cursor += 4
    if count <= 0 or count > 1024 or cursor + count * 4 + 12 > len(payload):
        return {}
    slot_ids = list(struct.unpack_from(f"<{count}i", payload, cursor))
    cursor += count * 4
    if (
        any(slot_id <= 0 for slot_id in slot_ids)
        or len(set(slot_ids)) != len(slot_ids)
        or payload[cursor:cursor + 12] != _DEFAULT_PARAM_TAIL
    ):
        return {}
    cursor += 12
    return {
        **scope,
        "triggerSlotIdFilters": slot_ids,
        "triggerSlotIdFilterCount": count,
        "subtypeConsumedBytes": cursor - subtype_offset,
        "payloadShape": "constant-trigger-slot-list-selector-prefix",
    }


def _decode_encounter_lsm_fields(payload: bytes) -> dict[str, Any]:
    """Decode the exact constant ``LsmPtr`` filter and null output prefix."""
    if (
        len(payload) < 53
        or payload[17:31] != b"\x04\x01" + _DEFAULT_PARAM_TAIL
        or payload[31] != 0x04
        or payload[40:52] != _DEFAULT_PARAM_TAIL
        or payload[52] != 0xFF
    ):
        return {}
    # Param<LsmPtr> is tag 0x04, a uint64 module pointer, the ordinary Param
    # tail, then a null ParamOutput<LsmPtr>. The wider record window can also
    # contain LevelScriptData members, so only the exact subtype prefix is
    # consumed and no later integer is scanned.
    return {
        "lsmPtrFilter": struct.unpack_from("<Q", payload, 32)[0],
        "lsmPtrOutputPresent": False,
        "subtypeConsumedBytes": 22,
        "payloadShape": "constant-lsm-pointer-null-output-exact-prefix",
    }


def _decode_scripted_char_patrol_fields(payload: bytes) -> dict[str, Any]:
    """Decode the exact patrol-event key selector and output references."""
    if len(payload) < 31 or payload[17:31] != b"\x04\x01" + _DEFAULT_PARAM_TAIL:
        return {}
    entity_output = levelscript_params.decode_param_output_ref(payload, 31)
    if entity_output is None:
        return {}
    entity_ref, cursor = entity_output
    key_param = _decode_constant_string_param(payload, cursor)
    if key_param is None:
        return {}
    key_filter, cursor = key_param
    if cursor >= len(payload) or payload[cursor] != 0xFF:
        return {}
    cursor += 1
    patrol_output = levelscript_params.decode_param_output_ref(payload, cursor)
    if patrol_output is None:
        return {}
    patrol_ref, cursor = patrol_output
    if cursor != len(payload):
        return {}
    return {
        "scriptedCharEventKeyFilter": key_filter,
        "keyOutputPresent": False,
        "entityOutputRef": entity_ref,
        "patrolIdOutputRef": patrol_ref,
        "payloadShape": "constant-patrol-key-and-output-refs-exact-eof",
    }


def _decode_npc_patrol_checkpoint_fields(payload: bytes) -> dict[str, Any]:
    """Decode the exact dynamic-NPC patrol/checkpoint listener fields."""
    param_tail = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"
    if len(payload) < 100 or payload[17:31] != b"\x04\x01" + param_tail:
        return {}
    cursor = 31
    if cursor + 27 > len(payload) or payload[cursor : cursor + 2] != b"\x04\x03":
        return {}
    logic_id = struct.unpack_from("<Q", payload, cursor + 2)[0]
    slot_id = struct.unpack_from("<I", payload, cursor + 10)[0]
    use_slot_id = payload[cursor + 14]
    target_id_ref = struct.unpack_from("<i", payload, cursor + 15)[0]
    target_source = struct.unpack_from("<i", payload, cursor + 19)[0]
    path_size = struct.unpack_from("<i", payload, cursor + 23)[0]
    cursor += 27
    if use_slot_id not in (0, 1) or path_size <= 0 or path_size > 256:
        return {}
    if cursor + path_size > len(payload):
        return {}
    try:
        target_path = payload[cursor : cursor + path_size].decode("utf-8")
    except UnicodeDecodeError:
        return {}
    cursor += path_size

    def read_i32_param() -> dict[str, Any] | None:
        nonlocal cursor
        decoded = levelscript_params.decode_i32_param(payload, cursor)
        if decoded is None:
            return None
        detail, cursor = decoded
        return detail

    patrol_id = read_i32_param()
    checkpoint_index = read_i32_param()
    if patrol_id is None or checkpoint_index is None:
        return {}
    if (
        patrol_id.get("idRef") == -1
        and patrol_id.get("paramSource") == 0
        and patrol_id.get("path") is None
        and checkpoint_index.get("idRef") == -1
        and checkpoint_index.get("paramSource") == 0
        and checkpoint_index.get("path") is None
    ):
        return {
            "npcEntityFilter": {
                "logicId": logic_id,
                "slotId": slot_id,
                "useSlotId": bool(use_slot_id),
                "idRef": target_id_ref,
                "paramSource": target_source,
                "path": target_path,
            },
            "patrolIdFilter": patrol_id["value"],
            "checkpointIndexFilter": checkpoint_index["value"],
            "payloadShape": "dynamic-npc-patrol-checkpoint-fields",
        }

    outputs: list[dict[str, Any]] = []
    for field_name in ("npcEntity", "npcPosition", "patrolId", "pointIndex"):
        decoded = levelscript_params.decode_param_output(payload, cursor)
        if decoded is None:
            return {}
        output, cursor = decoded
        outputs.append({"field": field_name, **output})
    if cursor != len(payload):
        return {}
    return {
        "npcEntityFilter": {
            "logicId": logic_id,
            "slotId": slot_id,
            "useSlotId": bool(use_slot_id),
            "idRef": target_id_ref,
            "paramSource": target_source,
            "path": target_path,
        },
        "patrolIdFilterParam": patrol_id,
        "checkpointIndexFilterParam": checkpoint_index,
        "eventOutputs": outputs,
        "payloadShape": "dynamic-blackboard-npc-patrol-checkpoint-and-outputs-exact-eof",
    }


def _decode_entity_compare_getter(payload: bytes, property_outputs: list[dict]) -> dict[str, Any]:
    """Decode the exact current-build EntityCompare ScriptEntityPtr operand.

    PureGetter tag 0x28/member-count 10 compares one property-output operand
    with a typed ScriptEntityPtr constant. The latter is encoded as tag 04/03,
    logic id u64, slot id u32, and a one-byte use-slot flag at the guarded tail
    offsets below. Other operand variants deliberately remain unsupported.
    """
    if (
        len(payload) != 84
        or payload[0x39:0x3B] != b"\x04\x03"
        or payload[0x47] not in (0, 1)
        or not property_outputs
    ):
        return {}
    return {
        "type": "EntityCompare",
        "propertyOutputRefs": property_outputs,
        "scriptEntity": {
            "logicId": struct.unpack_from("<Q", payload, 0x3B)[0],
            "slotId": struct.unpack_from("<I", payload, 0x43)[0],
            "useSlotId": bool(payload[0x47]),
        },
        "payloadShape": "property-output-vs-script-entity-ptr",
    }
