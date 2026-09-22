"""Fail-closed structural framing for current SkillData MemoryPack payloads.

This module deliberately does not assign authored field names to the terminal
members.  The selected-build metadata proves the wrapper's member count and
declared setter surface, but does not expose the formatter body/cursor order.
The byte shapes below are therefore structural claims only.
"""

from __future__ import annotations

import struct
from typing import Any

from scripts.game_data.memorypack.core import MEMORYPACK_NULL_COUNT, read_memorypack_utf8_string
from scripts.game_data.memorypack.buff import (
    consume_buff_sequence_action_data,
    read_buff_find_settings_exact,
    read_buff_gameplay_tag_query_exact,
    read_buff_target_settings_full,
    read_skill_bool_field,
    read_skill_buff_input_data,
)
from scripts.game_data.memorypack.schemas import MEMORYPACK_FIELD_SCHEMAS, SKILL_MEMBER_COUNT
from scripts.game_data.memorypack.skill_terminal import TerminalError, frame_skill_terminal_at


SKILL_TERMINAL_SHAPE_NOTE = (
    "EOF-anchored candidate within supported structural grammar; member names and serialized field "
    "ownership remain unresolved without a current formatter cursor"
)


SKILL_COMMON_PREFIX_MAX_RECORDS = 256


def _skill_require_room(data: bytes, offset: int, width: int, limit: int, field_name: str) -> None:
    if offset < 0 or width < 0 or offset + width > limit or limit > len(data):
        raise ValueError(
            f"{field_name}:truncated offset={offset} width={width} limit={limit} length={len(data)}"
        )


def _skill_read_u32(data: bytes, offset: int, limit: int, field_name: str) -> tuple[int, int]:
    _skill_require_room(data, offset, 4, limit, field_name)
    return struct.unpack_from("<I", data, offset)[0], offset + 4


def _skill_read_i32(data: bytes, offset: int, limit: int, field_name: str) -> tuple[int, int]:
    _skill_require_room(data, offset, 4, limit, field_name)
    return struct.unpack_from("<i", data, offset)[0], offset + 4


def _skill_read_f32(data: bytes, offset: int, limit: int, field_name: str) -> tuple[float, int]:
    _skill_require_room(data, offset, 4, limit, field_name)
    return struct.unpack_from("<f", data, offset)[0], offset + 4


def _skill_read_f64(data: bytes, offset: int, limit: int, field_name: str) -> tuple[float, int]:
    _skill_require_room(data, offset, 8, limit, field_name)
    return struct.unpack_from("<d", data, offset)[0], offset + 8


def _skill_read_bool(data: bytes, offset: int, limit: int, field_name: str) -> tuple[bool, int]:
    _skill_require_room(data, offset, 1, limit, field_name)
    return read_skill_bool_field(data, offset, field_name)


def _skill_read_string(data: bytes, offset: int, limit: int, field_name: str) -> tuple[str | None, int]:
    _skill_require_room(data, offset, 4, limit, field_name)
    value, end, error = read_memorypack_utf8_string(data, offset, max_length=16_384)
    if error:
        raise ValueError(f"{field_name}:{error}")
    if end > limit:
        raise ValueError(f"{field_name}:past-limit end={end} limit={limit}")
    return value, end


def _skill_read_count(data: bytes, offset: int, limit: int, field_name: str, *, maximum: int = 512) -> tuple[int, int]:
    raw, end = _skill_read_u32(data, offset, limit, field_name)
    if raw == MEMORYPACK_NULL_COUNT:
        return -1, end
    if raw > maximum:
        raise ValueError(f"{field_name}:count={raw} max={maximum}")
    return raw, end


def _skill_read_blackboard_float(data: bytes, offset: int, limit: int, field_name: str) -> int:
    _skill_require_room(data, offset, 1, limit, field_name)
    if data[offset] != 3:
        raise ValueError(f"{field_name}:member-count={data[offset]}")
    offset += 1
    _value, offset = _skill_read_string(data, offset, limit, f"{field_name}.blackboardKey")
    _value, offset = _skill_read_bool(data, offset, limit, f"{field_name}.useBlackboardKey")
    _value, offset = _skill_read_f32(data, offset, limit, f"{field_name}.value")
    return offset


def _skill_read_blackboard_pairs(data: bytes, offset: int, limit: int) -> int:
    count, offset = _skill_read_count(data, offset, limit, "blackboard.count", maximum=256)
    for index in range(max(count, 0)):
        _skill_require_room(data, offset, 1, limit, f"blackboard[{index}]")
        if data[offset] != 4:
            raise ValueError(f"blackboard[{index}]:member-count={data[offset]}")
        offset += 1
        _value, offset = _skill_read_bool(data, offset, limit, f"blackboard[{index}].isDynamic")
        _value, offset = _skill_read_string(data, offset, limit, f"blackboard[{index}].key")
        _value, offset = _skill_read_f64(data, offset, limit, f"blackboard[{index}].valueDouble")
        _value, offset = _skill_read_string(data, offset, limit, f"blackboard[{index}].valueStr")
    return offset


def _skill_read_buff_inputs(data: bytes, offset: int, limit: int, field_name: str) -> int:
    count, offset = _skill_read_count(data, offset, limit, f"{field_name}.count", maximum=256)
    for index in range(max(count, 0)):
        _decoded, offset = read_skill_buff_input_data(data, offset, index, field_name)
        if offset > limit:
            raise ValueError(f"{field_name}[{index}]:past-limit end={offset} limit={limit}")
    return offset


def _skill_read_attribute_modifier(data: bytes, offset: int, limit: int) -> int:
    _skill_require_room(data, offset, 1, limit, "cardAttributeModifier")
    if data[offset] == 0xFF:
        return offset + 1
    if data[offset] != 2:
        raise ValueError(f"cardAttributeModifier:member-count={data[offset]}")
    offset += 1
    count, offset = _skill_read_count(
        data, offset, limit, "cardAttributeModifier.attributeModifiers.count", maximum=256
    )
    for index in range(max(count, 0)):
        name = f"cardAttributeModifier.attributeModifiers[{index}]"
        _skill_require_room(data, offset, 1, limit, name)
        if data[offset] != 4:
            raise ValueError(f"{name}:member-count={data[offset]}")
        offset += 1
        for child in ("attributeType", "formulaItem", "modifyAttributeType"):
            _value, offset = _skill_read_i32(data, offset, limit, f"{name}.{child}")
        offset = _skill_read_blackboard_float(data, offset, limit, f"{name}.param")
    _value, offset = _skill_read_bool(data, offset, limit, "cardAttributeModifier.isConvertedAttribute")
    return offset


def _skill_read_cast_data(data: bytes, offset: int, limit: int) -> int:
    _skill_require_room(data, offset, 1, limit, "castData")
    if data[offset] == 0xFF:
        return offset + 1
    if data[offset] != 11:
        raise ValueError(f"castData:member-count={data[offset]}")
    offset += 1
    _value, offset = _skill_read_f32(data, offset, limit, "castData.castAngle")
    offset = _skill_read_blackboard_float(data, offset, limit, "castData.castDistance")
    _value, offset = _skill_read_i32(data, offset, limit, "castData.checkCastDistanceType")
    _value, offset = _skill_read_bool(data, offset, limit, "castData.checkHeightDiff")
    _value, offset = _skill_read_f32(data, offset, limit, "castData.cooldownTime")
    _skill_require_room(data, offset, 1, limit, "castData.costData")
    if data[offset] == 0xFF:
        offset += 1
    else:
        if data[offset] != 3:
            raise ValueError(f"castData.costData:member-count={data[offset]}")
        offset += 1
        _value, offset = _skill_read_f32(data, offset, limit, "castData.costData.atbValueThreshold")
        _value, offset = _skill_read_i32(data, offset, limit, "castData.costData.costType")
        _value, offset = _skill_read_f32(data, offset, limit, "castData.costData.costValue")
    offset = _skill_read_blackboard_float(data, offset, limit, "castData.heightDiffLimit")
    for child in ("maxChargeTime", "rotateType", "startCdFrame"):
        _value, offset = _skill_read_i32(data, offset, limit, f"castData.{child}")
    _value, offset = _skill_read_bool(data, offset, limit, "castData.useCustomCastDistance")
    return offset


def _skill_read_sequence(data: bytes, offset: int, limit: int, field_name: str) -> int:
    _skill_require_room(data, offset, 1, limit, field_name)
    if data[offset] == 0xFF:
        return offset + 1
    _decoded, end = consume_buff_sequence_action_data(data, offset, limit, field_name, 0)
    if end > limit:
        raise ValueError(f"{field_name}:past-limit end={end} limit={limit}")
    return end


def _skill_read_gameplay_tag_list(data: bytes, offset: int, limit: int, field_name: str) -> int:
    _skill_require_room(data, offset, 1, limit, field_name)
    if data[offset] == 0xFF:
        return offset + 1
    if data[offset] != 1:
        raise ValueError(f"{field_name}:member-count={data[offset]}")
    offset += 1
    count, offset = _skill_read_count(data, offset, limit, f"{field_name}.predefinedTag.count", maximum=256)
    for index in range(max(count, 0)):
        name = f"{field_name}.predefinedTag[{index}]"
        _skill_require_room(data, offset, 5, limit, name)
        if data[offset] != 1:
            raise ValueError(f"{name}:member-count={data[offset]}")
        offset += 5
    return offset


def _skill_read_buff_id_list(data: bytes, offset: int, limit: int) -> int:
    count, offset = _skill_read_count(data, offset, limit, "smartTargetBuffIds.count", maximum=256)
    for index in range(max(count, 0)):
        name = f"smartTargetBuffIds[{index}]"
        _skill_require_room(data, offset, 1, limit, name)
        if data[offset] != 1:
            raise ValueError(f"{name}:member-count={data[offset]}")
        offset += 1
        _value, offset = _skill_read_string(data, offset, limit, f"{name}.buffId")
    return offset


def _skill_read_switch_to_buff_config(data: bytes, offset: int, limit: int) -> int:
    _skill_require_room(data, offset, 1, limit, "switchToBuffConfig")
    if data[offset] == 0xFF:
        return offset + 1
    if data[offset] != 5:
        raise ValueError(f"switchToBuffConfig:member-count={data[offset]}")
    offset += 1
    _value, offset = _skill_read_bool(data, offset, limit, "switchToBuffConfig.asSkillCast")
    offset = _skill_read_buff_inputs(data, offset, limit, "switchToBuffConfig.buffs")
    _decoded, offset = read_buff_target_settings_full(
        data, offset, limit, "switchToBuffConfig.buffSource", 0
    )
    if offset > limit:
        raise ValueError(f"switchToBuffConfig.buffSource:past-limit end={offset} limit={limit}")
    offset = _skill_read_sequence(data, offset, limit, "switchToBuffConfig.condition")
    _decoded, offset = read_buff_target_settings_full(
        data, offset, limit, "switchToBuffConfig.targets", 0
    )
    if offset > limit:
        raise ValueError(f"switchToBuffConfig.targets:past-limit end={offset} limit={limit}")
    return offset


def _frame_skill_after_exact_action_group_profile(
    data: bytes,
    limit: int,
    *,
    action_group_end: int,
    action_group_kind: str,
) -> dict[str, Any]:
    """Advance fields 1..42 after an independently exact field-0 endpoint."""
    names = MEMORYPACK_FIELD_SCHEMAS["SkillData"]
    fields: list[dict[str, Any]] = []
    if (
        type(action_group_end) is not int
        or action_group_end <= 1
        or limit <= action_group_end
        or limit > len(data)
    ):
        return {"status": "not-applicable", "namedFields": fields, "parserCursor": 0}

    def add(index: int, start: int, end: int, kind: str) -> None:
        if not 0 <= start < end <= limit:
            raise ValueError(f"field-{index}:invalid-range {start}:{end} limit={limit}")
        fields.append({
            "fieldIndex": index,
            "fieldName": names[index],
            "start": start,
            "end": end,
            "kind": kind,
            "evidence": "current-wrapper-type-driven-candidate",
        })

    add(0, 1, action_group_end, action_group_kind)
    offset = action_group_end
    current_index = 1
    try:
        for current_index, kind, reader in (
            (1, "int32", lambda o: _skill_read_i32(data, o, limit, names[1])[1]),
            (2, "enum-int32", lambda o: _skill_read_i32(data, o, limit, names[2])[1]),
            (3, "List<Blackboard.DataPair>", lambda o: _skill_read_blackboard_pairs(data, o, limit)),
            (4, "BuffInputBase.null-union", lambda o: o + 1 if data[o] == 0xFF else (_ for _ in ()).throw(ValueError(f"{names[4]}:non-null-union"))),
            (5, "List<BuffInput>", lambda o: _skill_read_buff_inputs(data, o, limit, names[5])),
        ):
            start = offset
            offset = reader(offset)
            add(current_index, start, offset, kind)
        for current_index in range(6, 10):
            start = offset
            _value, offset = _skill_read_bool(data, offset, limit, names[current_index])
            add(current_index, start, offset, "bool")
        start = offset
        offset = _skill_read_attribute_modifier(data, offset, limit)
        add(10, start, offset, "AttributeModifierData")
        start = offset
        offset = _skill_read_cast_data(data, offset, limit)
        add(11, start, offset, "CastData")
        scalar_kinds = {
            12: "enum-int32", 13: "bool", 14: "string", 15: "string", 16: "bool",
            17: "Vector3", 18: "int32", 19: "int32", 20: "float32", 21: "enum-int32",
            22: "string", 23: "int32", 24: "bool", 25: "bool", 26: "int32",
            27: "bool", 28: "bool", 29: "enum-int32", 30: "bool", 31: "enum-int32",
            32: "bool",
        }
        for current_index in range(12, 33):
            start = offset
            kind = scalar_kinds[current_index]
            if kind in ("int32", "enum-int32"):
                _value, offset = _skill_read_i32(data, offset, limit, names[current_index])
            elif kind == "float32":
                _value, offset = _skill_read_f32(data, offset, limit, names[current_index])
            elif kind == "bool":
                _value, offset = _skill_read_bool(data, offset, limit, names[current_index])
            elif kind == "string":
                _value, offset = _skill_read_string(data, offset, limit, names[current_index])
            elif kind == "Vector3":
                _skill_require_room(data, offset, 12, limit, names[current_index])
                offset += 12
            add(current_index, start, offset, kind)
        start = offset
        offset = _skill_read_sequence(data, offset, limit, names[33])
        add(33, start, offset, "SequenceActionData")
        for current_index, kind in ((34, "string"), (35, "string"), (36, "enum-int32")):
            start = offset
            if kind == "string":
                _value, offset = _skill_read_string(data, offset, limit, names[current_index])
            else:
                _value, offset = _skill_read_i32(data, offset, limit, names[current_index])
            add(current_index, start, offset, kind)
        start = offset
        offset = _skill_read_gameplay_tag_list(data, offset, limit, names[37])
        add(37, start, offset, "GameplayTagList")
        start = offset
        _decoded, offset = read_buff_find_settings_exact(data, offset, limit, names[38])
        add(38, start, offset, "BuffFindSettings")
        start = offset
        offset = _skill_read_buff_id_list(data, offset, limit)
        add(39, start, offset, "List<BuffId>")
        start = offset
        _value, offset = _skill_read_i32(data, offset, limit, names[40])
        add(40, start, offset, "enum-int32")
        start = offset
        _decoded, offset = read_buff_gameplay_tag_query_exact(data, offset, limit, names[41])
        add(41, start, offset, "GameplayTagQuery")
        current_index = 42
        start = offset
        offset = _skill_read_switch_to_buff_config(data, offset, limit)
        add(42, start, offset, "SwitchToBuffConfig")
    except (IndexError, KeyError, UnicodeDecodeError, ValueError, struct.error) as exc:
        return {
            "status": "stopped-at-unsupported-top-level-field",
            "namedFields": fields,
            "parserCursor": offset,
            "completeThroughFieldIndex": fields[-1]["fieldIndex"] if fields else -1,
            "stopFieldIndex": current_index,
            "stopFieldName": names[current_index],
            "stopReason": str(exc),
            "hardLimit": limit,
            "wholeSchemaExact": False,
        }
    return {
        "status": "exact-through-field-42" if offset == limit else "stopped-before-terminal-start",
        "namedFields": fields,
        "parserCursor": offset,
        "completeThroughFieldIndex": 42,
        "hardLimit": limit,
        "wholeSchemaExact": False,
    }


def frame_skill_empty_action_group_profile(data: bytes, limit: int) -> dict[str, Any]:
    """Advance after the receipt-authenticated empty field-0 representation."""
    if limit <= 10 or limit > len(data):
        return {"status": "not-applicable", "namedFields": [], "parserCursor": 0}
    if data[:10] != bytes((SKILL_MEMBER_COUNT, 2)) + bytes(8):
        return {"status": "not-applicable", "namedFields": [], "parserCursor": 0}
    return _frame_skill_after_exact_action_group_profile(
        data,
        limit,
        action_group_end=10,
        action_group_kind="ActionGroupData.empty-two-list-object",
    )


def frame_skill_exact_timeline_action_group_profile(
    data: bytes,
    limit: int,
    *,
    action_group_end: int,
) -> dict[str, Any]:
    """Advance after an exactly closed one-record ``timelineActions`` field.

    The caller owns the nested TimelineActionData proof.  This entry point
    rechecks only the enclosing SkillData/ActionGroupData headers and the
    empty-passive, one-timeline list counts before using that exact endpoint.
    """
    if (
        limit <= action_group_end
        or action_group_end <= 10
        or limit > len(data)
        or len(data) < 10
        or data[0] != SKILL_MEMBER_COUNT
        or data[1] != 2
        or struct.unpack_from("<i", data, 2)[0] != 0
        or struct.unpack_from("<i", data, 6)[0] != 1
    ):
        return {"status": "not-applicable", "namedFields": [], "parserCursor": 0}
    return _frame_skill_after_exact_action_group_profile(
        data,
        limit,
        action_group_end=action_group_end,
        action_group_kind="ActionGroupData.exact-one-timeline-action-object",
    )


def _read_prefix_u32(data: bytes, offset: int, label: str) -> tuple[int, int]:
    if offset + 4 > len(data):
        raise ValueError(
            f"SkillData.commonPrefix:{label}:truncated-u32 offset={offset} "
            f"expected=4 actual={max(0, len(data) - offset)}"
        )
    return struct.unpack_from("<I", data, offset)[0], offset + 4


def _check_prefix_count(data: bytes, count: int, cursor: int, index: int) -> None:
    # Only one member-count byte per record is known here. Do not infer a
    # fixed record width from the first record or the managed declaration.
    if count > len(data) - cursor:
        raise ValueError(
            f"SkillData.commonPrefix:record-list-{index}-count offset={cursor - 4} "
            f"expected<=remaining-marker-bytes:{len(data) - cursor} actual={count}"
        )


def frame_skill_common_prefix(data: bytes) -> dict[str, Any]:
    """Consume only the anonymous SkillData prefix before its first record body.

    Supported bytes expose a 48-member top-level envelope followed by a
    two-member anonymous envelope.  Its members begin as counted record lists.
    We consume counts in their actual byte order, validate the first record's
    member-count byte when non-empty, and stop before that variable record
    body.  No declaration/setter order or authored field name is used.
    """

    if not data:
        raise ValueError("SkillData.commonPrefix:truncated-member-count")
    if data[0] != SKILL_MEMBER_COUNT:
        raise ValueError(
            "SkillData.commonPrefix:top-member-count "
            f"expected={SKILL_MEMBER_COUNT} actual={data[0]}"
        )
    if len(data) < 2:
        raise ValueError("SkillData.commonPrefix:truncated-nested-envelope")
    nested_member_count = data[1]
    if nested_member_count != 2:
        raise ValueError(
            "SkillData.commonPrefix:nested-member-count "
            f"expected=2 actual={nested_member_count}"
        )

    first_count, cursor = _read_prefix_u32(data, 2, "record-list-0-count")
    if first_count > SKILL_COMMON_PREFIX_MAX_RECORDS:
        raise ValueError(
            "SkillData.commonPrefix:record-list-0-count "
            f"max={SKILL_COMMON_PREFIX_MAX_RECORDS} actual={first_count}"
        )
    lists = [{"index": 0, "count": first_count, "countOffset": "0x2"}]
    if first_count:
        if cursor >= len(data):
            raise ValueError("SkillData.commonPrefix:record-list-0:truncated-first-record")
        _check_prefix_count(data, first_count, cursor, 0)
        first_record_member_count = data[cursor]
        if first_record_member_count != 2:
            raise ValueError(
                "SkillData.commonPrefix:record-list-0:first-record-member-count "
                f"expected=2 actual={first_record_member_count}"
            )
        lists[0]["firstRecordMemberCount"] = first_record_member_count
        return {
            "status": "stopped-at-first-opaque-record-body",
            "topLevelMemberCount": SKILL_MEMBER_COUNT,
            "anonymousEnvelopeMemberCount": nested_member_count,
            "recordLists": lists,
            "cursorOffset": _format_offset(cursor),
            "provenPrefixByteLength": cursor,
            "stopListIndex": 0,
            "stopReason": "first non-empty anonymous record body; nested union cursor unavailable",
            "wholeSchemaExact": False,
        }

    second_count, cursor = _read_prefix_u32(data, cursor, "record-list-1-count")
    if second_count > SKILL_COMMON_PREFIX_MAX_RECORDS:
        raise ValueError(
            "SkillData.commonPrefix:record-list-1-count "
            f"max={SKILL_COMMON_PREFIX_MAX_RECORDS} actual={second_count}"
        )
    lists.append({"index": 1, "count": second_count, "countOffset": "0x6"})
    result = {
        "status": "anonymous-envelope-count-prefix-consumed",
        "topLevelMemberCount": SKILL_MEMBER_COUNT,
        "anonymousEnvelopeMemberCount": nested_member_count,
        "recordLists": lists,
        "cursorOffset": _format_offset(cursor),
        "provenPrefixByteLength": cursor,
        "wholeSchemaExact": False,
    }
    if second_count:
        if cursor >= len(data):
            raise ValueError("SkillData.commonPrefix:record-list-1:truncated-first-record")
        _check_prefix_count(data, second_count, cursor, 1)
        first_record_member_count = data[cursor]
        if first_record_member_count != 4:
            raise ValueError(
                "SkillData.commonPrefix:record-list-1:first-record-member-count "
                f"expected=4 actual={first_record_member_count}"
            )
        lists[1]["firstRecordMemberCount"] = first_record_member_count
        result.update({
            "status": "stopped-at-first-opaque-record-body",
            "stopListIndex": 1,
            "stopReason": "first non-empty anonymous record body; nested union cursor unavailable",
        })
    else:
        result["stopReason"] = "two-member anonymous envelope consumed; later top-level bytes remain opaque"
    return result


def _format_offset(offset: int) -> str:
    return f"0x{offset:x}"


def _terminal_candidates(data: bytes, start: int, source: str) -> list[dict[str, Any]]:
    """Adapt all supported branch parses without choosing a preferred encoding."""
    try:
        parsed = frame_skill_terminal_at(data, start, source=source)
    except TerminalError:
        return []
    result = []
    for candidate in parsed["candidates"]:
        members = [
            {**member, "type": member["kind"]}
            for member in candidate["members"]
        ]
        result.append({
            "status": "exact-eof-anchored-terminal-shape",
            "startOffset": _format_offset(start),
            "endOffset": _format_offset(len(data)),
            "byteLength": len(data) - start,
            "exactToEof": True,
            "encoding": candidate["encoding"],
            "shape": [
                "bool", "counted-member-record-list",
                "counted-nested-object-list-a", "counted-nested-object-list-b", "bool",
            ],
            "members": members,
            "semanticFieldNamesStatus": "unresolved",
            "evidenceBoundary": SKILL_TERMINAL_SHAPE_NOTE,
        })
    return result


def frame_skill_memorypack(data: bytes, *, source: str = "SkillData") -> dict[str, Any]:
    """Frame the SkillData envelope and every exact terminal-shape candidate.

    A unique candidate is unique only within the supported grammar, not proof
    of the actual preceding cursor. Multiple starts or branches remain
    ambiguous. The bytes before each candidate remain explicitly opaque.
    """

    if not data:
        raise ValueError(f"{source}:truncated-member-count offset=0 expected=1 actual=0")
    member_count = data[0]
    if member_count != SKILL_MEMBER_COUNT:
        raise ValueError(
            f"{source}:member-count expected={SKILL_MEMBER_COUNT} actual={member_count} offset=0"
        )
    if len(data) < 2:
        raise ValueError(f"{source}:truncated-payload offset=1 expected>=1 actual=0")

    candidates: list[dict[str, Any]] = []
    # The terminal shape begins with a strict MemoryPack bool.  Filtering on
    # that byte avoids invoking nested readers at impossible offsets while
    # retaining all structurally valid candidates.
    for start in range(1, len(data)):
        if data[start] not in (0, 1):
            continue
        for candidate in _terminal_candidates(data, start, source):
            candidate["opaquePrefix"] = {
                "startOffset": "0x1",
                "endOffset": _format_offset(start),
                "byteLength": start - 1,
            }
            candidates.append(candidate)

    if len(candidates) == 1:
        status = "unique-exact-terminal-shape"
    elif candidates:
        status = "ambiguous-exact-terminal-shape"
    else:
        status = "terminal-shape-unresolved"

    ambiguity: dict[str, Any] | None = None
    if len(candidates) == 2:
        early, late = candidates
        early_start = int(early["startOffset"], 0)
        late_start = int(late["startOffset"], 0)
        early_members = early["members"]
        late_members = late["members"]
        shared_counts_early = [early_members[index].get("count") for index in (1, 2, 3)]
        shared_counts_late = [late_members[index].get("count") for index in (1, 2, 3)]
        if (
            late_start == early_start + 1
            and early_members[0].get("value") is False
            and late_members[0].get("value") is True
            and early_members[1].get("encoding") == "one-member-wrapper"
            and late_members[1].get("encoding") == "counted"
            and shared_counts_early == shared_counts_late
            and early_members[4].get("value") == late_members[4].get("value")
        ):
            ambiguity = {
                "kind": "one-byte-bool-vs-counted-wrapper-collision",
                "candidateStartOffsets": [early["startOffset"], late["startOffset"]],
                "sharedCountedRecordCounts": shared_counts_early,
                "resolutionStatus": "unresolved-both-exact-to-eof",
                "minimumMissingEvidence": (
                    "an independently proven end cursor for the immediately preceding "
                    "anonymous structure, or the current formatter read cursor"
                ),
            }

    result = {
        "status": status,
        "memberCount": member_count,
        "envelope": {
            "startOffset": "0x0",
            "payloadStartOffset": "0x1",
            "endOffset": _format_offset(len(data)),
            "byteLength": len(data),
        },
        "candidateCount": len(candidates),
        "candidates": candidates,
        "wholeSchemaExact": False,
        "serializedFieldOrderStatus": "unresolved",
        "evidenceBoundary": (
            "48-member outer envelope plus EOF-anchored terminal byte shape; "
            "opaque prefix, semantic field ownership, and complete nested union "
            "cursor remain unresolved"
        ),
    }
    if ambiguity is not None:
        result["ambiguity"] = ambiguity
    return result


if __name__ == "__main__":
    raise SystemExit(
        "Historical census rebinding is not supported. Run "
        "python -m scripts.game_data.memorypack.skill_corpus against the current VFS ledger."
    )
