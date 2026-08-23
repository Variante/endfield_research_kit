"""Exact current-build entity cast-skill and death listener codecs."""

from __future__ import annotations

import struct
from typing import Any

from . import params


ENTITY_CAST_SKILL = "LevelEvent_OnEntityCastSkill"
ANY_ENTITY_DIE = "LevelEvent_OnAnyEntityDie"
SPECIFIC_ENTITY_DIE = "LevelEvent_OnSpecificEntityDie"
SPECIFIC_ENTITY_LIST_DIE = "LevelEvent_OnSpecificEntityListDie"


def _decode_entity_cast_skill(payload: bytes) -> dict[str, Any]:
    if len(payload) < 31 or payload[17:31] != b"\x04\x01" + params.DEFAULT_PARAM_TAIL:
        return {}
    cursor = 31
    outputs: dict[str, str] = {}
    for field in ("entity", "entityTemplateId", "firstTargetId"):
        output = params.decode_param_output_ref(payload, cursor)
        if output is None:
            return {}
        outputs[field], cursor = output
    character_filter = params.decode_constant_bool_param(payload, cursor)
    if character_filter is None:
        return {}
    is_character, cursor = character_filter
    skill_output = params.decode_param_output_ref(payload, cursor)
    if skill_output is None:
        return {}
    outputs["skillId"], cursor = skill_output
    skill_filter = params.decode_constant_i32_param(payload, cursor)
    if skill_filter is None:
        return {}
    skill_type, cursor = skill_filter
    trailing_container_bytes = len(payload) - cursor
    return {
        "entityOutputRef": outputs["entity"],
        "entityTemplateIdOutputRef": outputs["entityTemplateId"],
        "firstTargetIdOutputRef": outputs["firstTargetId"],
        "skillIdOutputRef": outputs["skillId"],
        "isCharacterFilter": is_character,
        "skillTypeFilter": skill_type,
        "filterModeEnabled": bool(payload[4]),
        "subtypeConsumedBytes": cursor,
        "trailingContainerBytes": trailing_container_bytes,
        "payloadShape": (
            "cast-skill-outputs-and-filter-operands-exact-eof"
            if not trailing_container_bytes
            else "cast-skill-outputs-and-filter-operands-exact-prefix"
        ),
    }


def _decode_specific_entity_die(payload: bytes) -> dict[str, Any]:
    if len(payload) < 31 or payload[17:31] != b"\x04\x01" + params.DEFAULT_PARAM_TAIL:
        return {}
    output = params.decode_param_output_ref(payload, 31)
    if output is None:
        return {}
    output_ref, cursor = output
    entity_param = params.decode_constant_entity_ptr_param(payload, cursor)
    if entity_param is None:
        return {}
    entity_filter, cursor = entity_param
    if cursor != len(payload):
        return {}
    return {
        "entityOutputRef": output_ref,
        "entityFilter": entity_filter,
        "payloadShape": "entity-output-and-constant-entity-filter-exact-eof",
    }


def _decode_any_entity_die(payload: bytes) -> dict[str, Any]:
    if len(payload) < 31 or payload[17:31] != b"\x04\x01" + params.DEFAULT_PARAM_TAIL:
        return {}
    output = params.decode_param_output_ref(payload, 31)
    if output is None:
        return {}
    output_ref, cursor = output
    if cursor + 5 > len(payload) or payload[cursor] != 0x04:
        return {}
    count = struct.unpack_from("<I", payload, cursor + 1)[0]
    cursor += 5
    if count > 64:
        return {}
    entity_filters: list[dict[str, Any]] = []
    for _ in range(count):
        if cursor + 14 > len(payload) or payload[cursor] != 0x03:
            return {}
        use_slot_id = payload[cursor + 13]
        if use_slot_id not in (0, 1):
            return {}
        entity_filters.append({
            "logicId": struct.unpack_from("<Q", payload, cursor + 1)[0],
            "slotId": struct.unpack_from("<I", payload, cursor + 9)[0],
            "useSlotId": bool(use_slot_id),
        })
        cursor += 14
    if payload[cursor : cursor + 12] != params.DEFAULT_PARAM_TAIL:
        return {}
    cursor += 12
    is_monster_param = params.decode_constant_bool_param(payload, cursor)
    if is_monster_param is None:
        return {}
    is_monster, cursor = is_monster_param
    filter_by_list_param = params.decode_constant_bool_param(payload, cursor)
    if filter_by_list_param is None:
        return {}
    filter_by_list, cursor = filter_by_list_param
    if cursor != len(payload):
        return {}
    return {
        "entityOutputRef": output_ref,
        "entityListFilter": entity_filters,
        "isMonsterFilter": is_monster,
        "filterByList": filter_by_list,
        "payloadShape": "constant-entity-list-and-bool-filters-exact-eof",
    }


def _decode_specific_entity_list_die(payload: bytes) -> dict[str, Any]:
    if len(payload) < 31 or payload[17:31] != b"\x04\x01" + params.DEFAULT_PARAM_TAIL:
        return {}
    output = params.decode_param_output_ref(payload, 31)
    if output is None:
        return {}
    output_ref, cursor = output
    if cursor + 5 > len(payload) or payload[cursor] != 0x04:
        return {}
    count = struct.unpack_from("<I", payload, cursor + 1)[0]
    cursor += 5
    if count == 0 or count > 64:
        return {}
    entity_filters: list[dict[str, Any]] = []
    for _ in range(count):
        if cursor + 14 > len(payload) or payload[cursor] != 0x03:
            return {}
        use_slot_id = payload[cursor + 13]
        if use_slot_id not in (0, 1):
            return {}
        entity_filters.append({
            "logicId": struct.unpack_from("<Q", payload, cursor + 1)[0],
            "slotId": struct.unpack_from("<I", payload, cursor + 9)[0],
            "useSlotId": bool(use_slot_id),
        })
        cursor += 14
    if payload[cursor : cursor + 12] != params.DEFAULT_PARAM_TAIL:
        return {}
    cursor += 12
    if cursor != len(payload):
        return {}
    return {
        "entityOutputRef": output_ref,
        "entityListFilter": entity_filters,
        "payloadShape": "specific-constant-entity-list-exact-eof",
    }


def decode_entity_event_fields(
    payload: bytes,
    native_header_name: str,
) -> dict[str, Any]:
    if native_header_name == ENTITY_CAST_SKILL:
        return _decode_entity_cast_skill(payload)
    if native_header_name == ANY_ENTITY_DIE:
        return _decode_any_entity_die(payload)
    if native_header_name == SPECIFIC_ENTITY_DIE:
        return _decode_specific_entity_die(payload)
    if native_header_name == SPECIFIC_ENTITY_LIST_DIE:
        return _decode_specific_entity_list_die(payload)
    return {}
