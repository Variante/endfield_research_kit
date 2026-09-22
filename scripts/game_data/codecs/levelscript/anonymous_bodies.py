"""Exact codecs for the anonymous first-record and CallServer leader bodies.

Moved verbatim out of ``scripts/game_data/levelscript_binary.py``.
"""

from __future__ import annotations

import struct

from scripts.game_data.codecs.levelscript import call_server as levelscript_call_server
from scripts.game_data.codecs.levelscript import params as levelscript_params
from scripts.game_data.codecs.levelscript.framing_common import LevelScriptTopLevelFramingError
from scripts.game_data.codecs.levelscript.params import decode_bool_param as _decode_bool_param
from scripts.game_data.codecs.levelscript.params import decode_i32_param as _decode_i32_param
from scripts.game_data.codecs.levelscript.primitives import i32 as _i32
from scripts.game_data.codecs.levelscript.primitives import u32 as _u32
from scripts.game_data.codecs.levelscript.sequential_owner import _frame_levelscript_sequential_owner
from scripts.game_data.codecs.levelscript.sequential_owner import frame_levelscript_action_map_named_prefix
from typing import Any

def _read_anonymous_nullable_utf8(
    data: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int]:
    start = cursor
    if cursor + 4 > len(data):
        raise LevelScriptTopLevelFramingError(
            f"truncated anonymous UTF-8 length at offset={cursor}"
        )
    length = struct.unpack_from("<i", data, cursor)[0]
    cursor += 4
    if length == -1:
        return {"startOffset": start, "endOffset": cursor, "value": None}, cursor
    if length < 0 or length > len(data) - cursor:
        raise LevelScriptTopLevelFramingError(
            "invalid anonymous UTF-8 length: "
            f"offset={start} length={length} remaining={len(data) - cursor}"
        )
    raw = data[cursor : cursor + length]
    try:
        value = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise LevelScriptTopLevelFramingError(
            f"invalid anonymous UTF-8 payload at offset={cursor} length={length}"
        ) from error
    cursor += length
    return {
        "startOffset": start,
        "endOffset": cursor,
        "value": value,
    }, cursor


def _read_anonymous_i32_string_collection(
    data: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int]:
    start = cursor
    if cursor + 4 > len(data):
        raise LevelScriptTopLevelFramingError(
            f"truncated anonymous collection count at offset={cursor}"
        )
    count = struct.unpack_from("<i", data, cursor)[0]
    cursor += 4
    if count == -1:
        return {
            "startOffset": start,
            "endOffset": cursor,
            "rawCount": count,
            "values": None,
        }, cursor
    if count < 0 or count > (len(data) - cursor) // 4:
        raise LevelScriptTopLevelFramingError(
            "invalid anonymous collection count: "
            f"offset={start} count={count} remaining={len(data) - cursor}"
        )
    values = []
    for _ in range(count):
        value, cursor = _read_anonymous_nullable_utf8(data, cursor)
        values.append(value["value"])
    return {
        "startOffset": start,
        "endOffset": cursor,
        "rawCount": count,
        "values": values,
    }, cursor


def _read_anonymous_param_tail(
    data: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int]:
    start = cursor
    if cursor + 8 > len(data):
        raise LevelScriptTopLevelFramingError(
            f"truncated anonymous fixed-width tail at offset={cursor}"
        )
    raw_i32 = list(struct.unpack_from("<ii", data, cursor))
    cursor += 8
    trailing, cursor = _read_anonymous_nullable_utf8(data, cursor)
    return {
        "startOffset": start,
        "endOffset": cursor,
        "rawI32": raw_i32,
        "trailingNullableUtf8": trailing["value"],
    }, cursor


def frame_levelscript_first_record_35_0e_00_anonymous_body(
    data: bytes,
) -> dict[str, Any]:
    """Advance a real cursor through the most frequent first-record body.

    The selected current-corpus variant is identified only by its raw compact
    envelope bytes ``35 0e 00``.  Its body is decoded as anonymous wire
    segments; no type name, field name, setter order, later-record scan, or
    later-list boundary participates in the result.
    """
    prefix = frame_levelscript_action_map_named_prefix(data)
    if prefix.get("status") != (
        "exact_named_nonempty_action_map_first_record_prefix"
    ):
        raise LevelScriptTopLevelFramingError(
            "selected first-record body requires a non-empty action map"
        )
    envelope = (prefix.get("ranges") or {}).get("firstRecordEnvelope") or {}
    if (
        envelope.get("layout") != "plain"
        or envelope.get("rawUnionTag") != 0x35
        or envelope.get("rawSerializedMemberCount") != 0x0E
        or len(data) <= 9
        or data[9] != 0
    ):
        actual = data[7:10].hex(" ") if len(data) >= 10 else data[7:].hex(" ")
        raise LevelScriptTopLevelFramingError(
            "first polymorphic record variant mismatch: "
            f"expected=35 0e 00 actual={actual}"
        )

    body_start = int(prefix["bytesConsumed"])
    cursor = body_start
    segment0, cursor = _read_anonymous_i32_string_collection(data, cursor)

    segment1_start = cursor
    if cursor + 2 > len(data) or data[cursor] != 0x04:
        raise LevelScriptTopLevelFramingError(
            f"anonymous segment 1 marker mismatch at offset={cursor}: expected=04"
        )
    raw_count = data[cursor + 1]
    cursor += 2
    segment1_values = []
    for _ in range(raw_count):
        value, cursor = _read_anonymous_nullable_utf8(data, cursor)
        segment1_values.append(value["value"])
    segment1_tail, cursor = _read_anonymous_param_tail(data, cursor)
    segment1 = {
        "startOffset": segment1_start,
        "endOffset": cursor,
        "rawMarker": 0x04,
        "rawU8Count": raw_count,
        "values": segment1_values,
        "tail": segment1_tail,
    }

    segment2_start = cursor
    if cursor >= len(data) or data[cursor] != 0x04:
        raise LevelScriptTopLevelFramingError(
            f"anonymous segment 2 marker mismatch at offset={cursor}: expected=04"
        )
    cursor += 1
    segment2_value, cursor = _read_anonymous_nullable_utf8(data, cursor)
    segment2_tail, cursor = _read_anonymous_param_tail(data, cursor)
    segment2 = {
        "startOffset": segment2_start,
        "endOffset": cursor,
        "rawMarker": 0x04,
        "value": segment2_value["value"],
        "tail": segment2_tail,
    }

    fixed_start = cursor
    expected_fixed = b"\x00\x01\x00"
    if cursor + len(expected_fixed) > len(data):
        raise LevelScriptTopLevelFramingError(
            f"truncated anonymous fixed suffix at offset={cursor}"
        )
    actual_fixed = data[cursor : cursor + len(expected_fixed)]
    if actual_fixed != expected_fixed:
        raise LevelScriptTopLevelFramingError(
            "anonymous fixed suffix mismatch: "
            f"offset={cursor} expected=00 01 00 actual={actual_fixed.hex(' ')}"
        )
    cursor += len(expected_fixed)

    opaque_ranges = []
    if cursor < len(data):
        opaque_ranges.append({
            "startOffset": cursor,
            "endOffset": len(data),
            "length": len(data) - cursor,
            "status": "opaque_after_first_record_body",
        })
    return {
        "status": "exact_anonymous_first_record_35_0e_00_body",
        "schemaStatus": "partial",
        "serializedMemberCount": 27,
        "selectedVariant": {
            "envelopeHex": "35 0e 00",
            "unionTagEncoding": "memorypack-u8",
            "rawUnionTag": 0x35,
            "rawSerializedMemberCount": 0x0E,
            "rawThirdEnvelopeByte": 0,
        },
        "bytesConsumed": cursor,
        "bodyBytesConsumed": cursor - body_start,
        "ranges": {
            "firstRecordEnvelope": envelope,
            "firstRecordBody": {
                "startOffset": body_start,
                "endOffset": cursor,
                "anonymousSegments": [
                    segment0,
                    segment1,
                    segment2,
                    {
                        "startOffset": fixed_start,
                        "endOffset": cursor,
                        "rawHex": actual_fixed.hex(" "),
                    },
                ],
            },
            "opaqueRemainder": opaque_ranges,
        },
        "evidenceBoundary": (
            "The cursor advances deterministically from offset 37 through four "
            "anonymous body segments. Bytes after the returned end offset remain "
            "opaque and are not scanned for records or list boundaries."
        ),
    }


def _read_nullable_levelscript_param(
    data: bytes,
    cursor: int,
    decoder: Any,
    label: str,
) -> tuple[dict[str, Any], int]:
    """Read a nullable generated ``Param`` member without guessing its end."""
    if cursor >= len(data):
        raise LevelScriptTopLevelFramingError(
            f"truncated {label} at offset={cursor}"
        )
    if data[cursor] == 0xFF:
        return {"value": None, "startOffset": cursor, "endOffset": cursor + 1}, cursor + 1
    decoded = decoder(data, cursor)
    if decoded is None:
        raise LevelScriptTopLevelFramingError(
            f"unsupported {label} encoding at offset={cursor}"
        )
    value, end = decoded
    return {
        "value": value,
        "startOffset": cursor,
        "endOffset": end,
    }, end


def _read_levelscript_node_envelope(
    data: bytes,
    cursor: int,
    *,
    union_tag: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    """Read the seven generated ``NodeBase`` fields of a plain-tag record."""
    start = cursor
    if cursor + 26 > len(data):
        raise LevelScriptTopLevelFramingError(
            f"truncated NodeBase envelope at offset={cursor}"
        )
    if data[cursor] != union_tag or data[cursor + 1] != member_count:
        raise LevelScriptTopLevelFramingError(
            "polymorphic record mismatch: "
            f"expected={union_tag:02x} {member_count:02x} "
            f"actual={data[cursor:cursor + 2].hex(' ')}"
        )
    dont_log = data[cursor + 2]
    release = data[cursor + 7]
    use_current = data[cursor + 24]
    use_graph = data[cursor + 25]
    if any(value not in (0, 1) for value in (dont_log, release, use_current, use_graph)):
        raise LevelScriptTopLevelFramingError(
            f"invalid NodeBase boolean at offset={cursor}"
        )
    uid_size = _u32(data, cursor + 8)
    if uid_size != 8:
        raise LevelScriptTopLevelFramingError(
            f"NodeBase uid length mismatch at offset={cursor + 8}: actual={uid_size}"
        )
    raw_uid = data[cursor + 12 : cursor + 20]
    if not all(
        ord("0") <= value <= ord("9") or ord("a") <= value <= ord("f")
        for value in raw_uid
    ):
        raise LevelScriptTopLevelFramingError(
            f"invalid NodeBase uid at offset={cursor + 12}"
        )
    end = cursor + 26
    return {
        "startOffset": start,
        "endOffset": end,
        "unionTag": union_tag,
        "serializedMemberCount": member_count,
        "dontLogWarning": bool(dont_log),
        "id": _u32(data, cursor + 3),
        "releaseWhenExecutionFinished": bool(release),
        "uid": raw_uid.decode("ascii"),
        "scopeMask": _i32(data, cursor + 20),
        "useCurrentScope": bool(use_current),
        "useGraphScope": bool(use_graph),
    }, end


def frame_levelscript_single_call_server_leader_enter(
    data: bytes,
) -> dict[str, Any]:
    """Close the dominant one-action current-build serialized-map lane.

    The selected ActionBase tag is current-build ``CallServer`` and the header
    tag is ``ScriptEvent_OnLeaderEnterTriggerVolume``.  Both records advance a
    sequential cursor through their generated wrapper fields.  The reader
    accepts only an empty getter list and empty ``ParamListForGraph`` before
    handing the exact action-map boundary to the generated-order owner reader.
    """
    prefix = frame_levelscript_action_map_named_prefix(data)
    action_prefix = (prefix.get("ranges") or {}).get("actionMapPrefix") or {}
    envelope = (prefix.get("ranges") or {}).get("firstRecordEnvelope") or {}
    if action_prefix.get("actionListCount") != 1:
        raise LevelScriptTopLevelFramingError("selected action lane requires actionList count=1")
    if (
        envelope.get("layout") != "plain"
        or envelope.get("rawUnionTag") != 0x35
        or envelope.get("rawSerializedMemberCount") != 0x0E
    ):
        raise LevelScriptTopLevelFramingError(
            "selected action lane requires current CallServer tag/member-count 35 0e"
        )

    action_body_start = int(prefix["bytesConsumed"])
    action = levelscript_call_server.decode_call_server_action(data[action_body_start:])
    consumed = action.get("consumedBytes") if isinstance(action, dict) else None
    if not isinstance(consumed, int) or consumed <= 0:
        raise LevelScriptTopLevelFramingError("CallServer generated fields did not decode")
    cursor = action_body_start + consumed
    if cursor + 8 > len(data):
        raise LevelScriptTopLevelFramingError("truncated getter/header list counts")
    getter_count = _i32(data, cursor)
    header_count = _i32(data, cursor + 4)
    if (getter_count, header_count) != (0, 1):
        raise LevelScriptTopLevelFramingError(
            "selected action lane requires getterList/headerList counts 0/1: "
            f"actual={getter_count}/{header_count}"
        )
    cursor += 8

    header_envelope, cursor = _read_levelscript_node_envelope(
        data, cursor, union_tag=0xBF, member_count=0x12
    )
    header_fields_start = cursor
    if cursor + 21 > len(data):
        raise LevelScriptTopLevelFramingError("truncated ActionHeader generated fields")
    filter_level = _i32(data, cursor)
    filter_mask = _i32(data, cursor + 4)
    filter_mode = data[cursor + 8]
    next_id = _i32(data, cursor + 9)
    priority = _i32(data, cursor + 13)
    trigger_active_during = _i32(data, cursor + 17)
    if filter_mode not in (0, 1):
        raise LevelScriptTopLevelFramingError(
            f"invalid ActionHeader filterMode at offset={cursor + 8}"
        )
    cursor += 21
    validate, cursor = _read_nullable_levelscript_param(
        data, cursor, _decode_bool_param, "ActionHeader.validate"
    )
    # This exact lane intentionally admits only the null targetScript form.
    if cursor >= len(data) or data[cursor] != 0xFF:
        raise LevelScriptTopLevelFramingError(
            f"unsupported non-null ScriptEvent.targetScript at offset={cursor}"
        )
    target_script = {"value": None, "startOffset": cursor, "endOffset": cursor + 1}
    cursor += 1
    if cursor + 4 > len(data):
        raise LevelScriptTopLevelFramingError("truncated ScriptEvent.triggerTarget")
    trigger_target = _i32(data, cursor)
    cursor += 4
    slot_filter, cursor = _read_nullable_levelscript_param(
        data, cursor, _decode_i32_param, "triggerSlotIdFilter"
    )
    slot_output, cursor = _read_nullable_levelscript_param(
        data, cursor, levelscript_params.decode_param_output, "triggerSlotIdOutput"
    )
    header_end = cursor

    if cursor + 5 > len(data) or data[cursor] != 1:
        actual = data[cursor:cursor + 5].hex(" ")
        raise LevelScriptTopLevelFramingError(
            "ParamListForGraph header mismatch: expected memberCount=1 "
            f"actual={actual}"
        )
    param_count = _i32(data, cursor + 1)
    if param_count != 0:
        raise LevelScriptTopLevelFramingError(
            f"selected action lane requires empty ParamListForGraph: actual={param_count}"
        )
    action_map_end = cursor + 5
    action_map = {
        "startOffset": 1,
        "endOffset": action_map_end,
        "serializedMemberCount": 2,
        "completeAsset": True,
        "dataMap": {
            "startOffset": 2,
            "endOffset": header_end,
            "serializedMemberCount": 3,
            "actionListCount": 1,
            "getterListCount": 0,
            "headerListCount": 1,
            "actionList": [{
                "envelope": envelope,
                "action": "CallServer",
                "fields": action,
                "endOffset": action_body_start + consumed,
            }],
            "headerList": [{
                "envelope": header_envelope,
                "header": "ScriptEvent_OnLeaderEnterTriggerVolume",
                "startOffset": header_envelope["startOffset"],
                "endOffset": header_end,
                "fields": {
                    "filterLevel": filter_level,
                    "filterMask": filter_mask,
                    "filterMode": bool(filter_mode),
                    "nextID": next_id,
                    "priority": priority,
                    "triggerActiveDuring": trigger_active_during,
                    "validate": validate,
                    "targetScript": target_script,
                    "triggerTarget": trigger_target,
                    "triggerSlotIdFilter": slot_filter,
                    "triggerSlotIdOutput": slot_output,
                },
                "fieldsStartOffset": header_fields_start,
            }],
        },
        "paramBlackboard": {
            "startOffset": cursor,
            "endOffset": action_map_end,
            "serializedMemberCount": 1,
            "valueCount": 0,
        },
    }
    return _frame_levelscript_sequential_owner(
        data,
        action_map=action_map,
        owner_offset=action_map_end,
        action_map_boundary="single CallServer/leader-enter action map",
        partial_status="exact_named_single_call_server_leader_enter_owner_prefix",
    )
