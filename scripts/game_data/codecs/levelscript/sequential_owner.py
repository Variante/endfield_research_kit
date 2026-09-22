"""The generated-order owner walk shared by the sequential lanes.

Moved verbatim out of ``scripts/game_data/levelscript_binary.py``.
"""

from __future__ import annotations

import struct

from scripts.game_data.codecs.levelscript import active_shapes as levelscript_active_shapes
from scripts.game_data.codecs.levelscript import top_level_prefix as levelscript_top_level_prefix
from scripts.game_data.codecs.levelscript import top_level_tail as levelscript_top_level_tail
from scripts.game_data.codecs.levelscript import trigger_volumes as levelscript_trigger_volumes
from scripts.game_data.codecs.levelscript.framing_common import LevelScriptTopLevelFramingError
from scripts.game_data.codecs.levelscript.framing_common import _is_plausible_levelscript_id
from scripts.game_data.codecs.levelscript.framing_common import _record_start
from scripts.game_data.codecs.levelscript.primitives import u32 as _u32
from scripts.game_data.codecs.levelscript.task_conditions import _decode_levelscript_task_entry
from scripts.game_data.codecs.levelscript.uid_records import _decode_levelscript_uid_record
from typing import Any

def _frame_levelscript_sequential_owner(
    data: bytes,
    *,
    action_map: dict[str, Any],
    owner_offset: int,
    action_map_boundary: str,
    partial_status: str,
) -> dict[str, Any]:
    """Advance members 2..27 after an independently exact action-map boundary."""
    try:
        owner = levelscript_top_level_prefix.decode_empty_action_map_owner_prefix(
            data, owner_offset
        )
    except levelscript_top_level_prefix.LevelScriptPrefixCodecError as error:
        raise LevelScriptTopLevelFramingError(str(error)) from error

    cursor = int(owner["endOffset"])
    ranges: dict[str, Any] = {
        "memberCount": {"startOffset": 0, "endOffset": 1},
        "actionMap": action_map,
        "ownerPrefix": owner,
    }
    fields = dict(owner.get("fields") or {})
    stop_field = owner.get("stopField")
    if stop_field:
        return {
            "status": partial_status,
            "schemaStatus": "partial",
            "serializedMemberCount": 27,
            "bytesConsumed": cursor,
            "fields": fields,
            "ranges": ranges,
            "stopField": stop_field,
            "stopDetail": owner.get("stopDetail") or {},
            "opaqueRemainder": {
                "startOffset": cursor,
                "endOffset": len(data),
                "length": len(data) - cursor,
            },
            "evidenceBoundary": (
                "Generated current-wrapper order advances a sequential named cursor "
                f"from the exact {action_map_boundary} to the first unsupported positive "
                f"collection, {stop_field}. No later byte is scanned or assigned."
            ),
        }

    if cursor + 8 > len(data):
        raise LevelScriptTopLevelFramingError(
            f"truncated scriptId after exact owner prefix: offset={cursor}"
        )
    script_id = struct.unpack_from("<Q", data, cursor)[0]
    if not _is_plausible_levelscript_id(script_id):
        raise LevelScriptTopLevelFramingError(
            f"invalid positional scriptId: offset={cursor} value={script_id}"
        )
    tail = levelscript_top_level_tail.decode_tail_candidate(data, cursor)
    start_shapes = tail.get("startShapeList") or {}
    start_shape_rows = start_shapes.get("shapes") or []
    if (
        tail.get("startShapeListStatus") not in {"null", "present"}
        or not tail.get("startTypeName")
        or (
            int(tail.get("startShapeListCount") or 0) > 0
            and (
                start_shapes.get("parseStatus") != "decoded"
                or not all(
                    levelscript_active_shapes._valid_active_shape(row)
                    for row in start_shape_rows
                )
            )
        )
        or tail.get("taskMapStatus") not in {"null", "present"}
    ):
        raise LevelScriptTopLevelFramingError(
            f"invalid positional LevelScriptData terminal prefix at offset={cursor}"
        )

    task_map_offset = int(tail["taskMapOffset"])
    task_map_count = tail.get("taskMapCount")
    task_map_end = task_map_offset + 4
    fields.update({
        "scriptId": script_id,
        "startShapeList": start_shapes,
        "startType": {
            "raw": tail.get("startTypeRaw"),
            "name": tail.get("startTypeName"),
        },
        "taskMap": {
            "status": tail.get("taskMapStatus"),
            "count": task_map_count,
        },
    })
    ranges["terminalPrefix"] = {
        "startOffset": cursor,
        "endOffset": task_map_end,
        "scriptIdOffset": cursor,
        "startShapeListOffset": tail.get("startShapeListOffset"),
        "startTypeOffset": tail.get("startTypeOffset"),
        "taskMapOffset": task_map_offset,
    }

    if task_map_count not in {None, 0}:
        task_cursor = task_map_end
        tasks: list[dict[str, Any]] = []
        task_diagnostics: list[dict[str, Any]] = []
        for _ in range(int(task_map_count)):
            decoded_task = _decode_levelscript_task_entry(
                data,
                task_cursor,
                len(data),
                task_diagnostics,
            )
            if decoded_task is None:
                break
            task, task_cursor = decoded_task
            tasks.append(task)
        if len(tasks) == int(task_map_count):
            trigger_volumes, trigger_end = (
                levelscript_trigger_volumes.decode_trigger_volume_map(
                    data,
                    task_cursor,
                )
            )
            if (
                trigger_end == len(data)
                and trigger_volumes.get("status") in {"null", "present"}
                and trigger_volumes.get("parseStatus") != "truncated"
            ):
                fields["taskMap"] = {
                    "status": "present",
                    "count": int(task_map_count),
                    "entries": tasks,
                }
                fields["triggerVolumes"] = trigger_volumes
                ranges["taskMap"] = {
                    "startOffset": task_map_offset,
                    "endOffset": task_cursor,
                }
                ranges["triggerVolumes"] = {
                    "startOffset": task_cursor,
                    "endOffset": trigger_end,
                }
                return {
                    "status": "exact_named_levelscript_data",
                    "schemaStatus": "named_exact",
                    "serializedMemberCount": 27,
                    "bytesConsumed": len(data),
                    "fields": fields,
                    "ranges": ranges,
                    "evidenceBoundary": (
                        "The current generated 27-member wrapper advances one "
                        f"sequential cursor from the exact {action_map_boundary} "
                        "through every "
                        "declared task entry and the final triggerVolumes map at "
                        "physical EOF. Task conditions use their exact supported "
                        "union codecs; unsupported condition bodies fail closed."
                    ),
                }
        return {
            "status": "exact_named_action_map_owner_through_task_map_header",
            "schemaStatus": "partial",
            "serializedMemberCount": 27,
            "bytesConsumed": task_map_end,
            "fields": fields,
            "ranges": ranges,
            "stopField": "taskMap.entries",
            "opaqueRemainder": {
                "startOffset": task_map_end,
                "endOffset": len(data),
                "length": len(data) - task_map_end,
            },
            "evidenceBoundary": (
                "All owner members from actionMap through the taskMap count advance "
                "one generated-order cursor. Positive task entries and triggerVolumes "
                "remain opaque; no suffix scan contributes to the boundary."
            ),
        }

    trigger_volumes = tail.get("triggerVolumes") or {}
    if (
        trigger_volumes.get("status") not in {"null", "present"}
        or trigger_volumes.get("parseStatus") == "truncated"
        or trigger_volumes.get("endOffset") != f"0x{len(data):x}"
    ):
        raise LevelScriptTopLevelFramingError(
            "positional empty taskMap does not lead to an exact triggerVolumes EOF"
        )
    fields["triggerVolumes"] = trigger_volumes
    ranges["triggerVolumes"] = {
        "startOffset": task_map_end,
        "endOffset": len(data),
    }
    return {
        "status": "exact_named_levelscript_data",
        "schemaStatus": "named_exact",
        "serializedMemberCount": 27,
        "bytesConsumed": len(data),
        "fields": fields,
        "ranges": ranges,
        "evidenceBoundary": (
            "The current generated 27-member wrapper advances one sequential cursor "
            f"from the exact {action_map_boundary} through physical EOF. Complex owner collections are "
            "null or empty; triggerVolumes uses its exact current entry codec."
        ),
    }


def frame_levelscript_action_map_named_prefix(
    data: bytes,
    *,
    expected_member_count: int = 27,
) -> dict[str, Any]:
    """Frame the named outer prefix of a current action map.

    Generated setter order assigns the outer root member to ``actionMap``, its
    first member to ``dataMap``, and the first serialized-map member to
    ``actionList``. A raw ``0xff`` tag proves a complete null action-map
    boundary. A non-empty ``02 03 <u32>`` object proves the named action-list
    count and the fixed envelope of its first polymorphic record.
    The record payload and every later top-level byte remain one opaque range;
    finding UID-like bytes later in the file is not accepted as cursor proof.
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
        opaque_ranges = []
        if len(data) > 2:
            opaque_ranges.append({
                "startOffset": 2,
                "endOffset": len(data),
                "length": len(data) - 2,
                "status": "opaque_unassigned_top_level_members",
            })
        return {
            "status": "exact_named_null_action_map_boundary",
            "schemaStatus": "partial",
            "serializedMemberCount": expected_member_count,
            "bytesConsumed": 2,
            "ranges": {
                "memberCount": {"startOffset": 0, "endOffset": 1},
                "actionMap": {
                    "startOffset": 1,
                    "endOffset": 2,
                    "value": None,
                    "rawUnionTag": 0xFF,
                    "unionTagEncoding": "memorypack-null-u8",
                },
                "opaqueTopLevelMembers": opaque_ranges,
            },
            "evidenceBoundary": (
                "The one-byte null tag closes the named actionMap at offset 2. Bytes from "
                "offset 2 onward are not attributed to named top-level fields."
            ),
        }

    if len(data) < 7:
        raise LevelScriptTopLevelFramingError(
            "truncated non-empty ActionSerializedMap header: expected 7 bytes"
        )
    if data[1:3] != b"\x02\x03":
        raise LevelScriptTopLevelFramingError(
            "unsupported ActionSerializedMap raw object marker: "
            f"actual={data[1:3].hex(' ')}"
        )
    first_count = _u32(data, 3)
    if first_count == 0:
        raise LevelScriptTopLevelFramingError(
            "empty ActionSerializedMap requires the complete empty-map reader"
        )
    if first_count is None or first_count > len(data) - 7:
        raise LevelScriptTopLevelFramingError(
            "impossible anonymous first-list count: "
            f"count={first_count} remainingBytes={len(data) - 7}"
        )

    candidates: list[dict[str, Any]] = []
    for uid_offset in (21, 19):
        if uid_offset + 8 > len(data):
            continue
        raw_uid = data[uid_offset : uid_offset + 8]
        if not all(
            ord("0") <= value <= ord("9") or ord("a") <= value <= ord("f")
            for value in raw_uid
        ):
            continue
        record = _decode_levelscript_uid_record(
            data,
            uid_offset,
            raw_uid.decode("ascii"),
        )
        if record is not None and _record_start(record) == 7:
            candidates.append(record)
    if len(candidates) != 1:
        raise LevelScriptTopLevelFramingError(
            "first polymorphic record envelope is not unique and exact: "
            f"candidates={len(candidates)}"
        )

    record = candidates[0]
    payload_start = int(record["payloadStart"])
    if payload_start > len(data):
        raise LevelScriptTopLevelFramingError(
            "truncated first polymorphic record envelope"
        )
    layout = str(record["layout"])
    if layout == "fa":
        union_tag_encoding = "memorypack-fa-u16"
        raw_union_tag = int(record["code"])
        raw_member_count = int(record["kind"])
    elif layout == "plain":
        union_tag_encoding = "memorypack-u8"
        raw_union_tag = int(record["unionTag"])
        raw_member_count = int(record["serializedMemberCount"])
    else:
        raise LevelScriptTopLevelFramingError(
            f"unsupported first polymorphic record envelope layout: {layout}"
        )

    opaque_ranges = []
    if payload_start < len(data):
        opaque_ranges.append({
            "startOffset": payload_start,
            "endOffset": len(data),
            "length": len(data) - payload_start,
            "status": "opaque_first_record_payload_and_remaining_members",
        })
    return {
        "status": "exact_named_nonempty_action_map_first_record_prefix",
        "schemaStatus": "partial",
        "serializedMemberCount": expected_member_count,
        "bytesConsumed": payload_start,
        "ranges": {
            "memberCount": {"startOffset": 0, "endOffset": 1},
            "actionMapPrefix": {
                "startOffset": 1,
                "endOffset": payload_start,
                "rawObjectMarkerHex": data[1:3].hex(" "),
                "memberCount": 2,
                "dataMapMemberCount": 3,
                "actionListCount": first_count,
            },
            "firstRecordEnvelope": {
                "startOffset": 7,
                "endOffset": payload_start,
                "layout": layout,
                "rawUnionTag": raw_union_tag,
                "unionTagEncoding": union_tag_encoding,
                "rawSerializedMemberCount": raw_member_count,
                "uidAnchorAscii": str(record["uid"]),
            },
            "opaqueRemainder": opaque_ranges,
        },
        "evidenceBoundary": (
            "Generated setter order names actionMap.dataMap.actionList; its count "
            "and first fixed polymorphic record envelope advance a real cursor. The record payload, later "
            "list counts, and remaining top-level members are opaque."
        ),
    }


def _record_local_id(record: dict[str, Any]) -> int | None:
    value = record.get("localId")
    return value if isinstance(value, int) else None


def _small_uid_list_count(value: int | None, remaining_records: int) -> bool:
    return (
        isinstance(value, int)
        and value != 0xFFFFFFFF
        and 0 <= value <= 10_000
        and (remaining_records <= 0 or value <= remaining_records)
    )


def _levelscript_header_list_like_record(record: dict[str, Any]) -> bool:
    code = record.get("code")
    kind = record.get("kind")
    return (
        isinstance(code, int)
        and isinstance(kind, int)
        and kind == 0x00
        and 0x0E00 <= code <= 0x18FF
    )


def _levelscript_getter_list_like_record(record: dict[str, Any]) -> bool:
    code = record.get("code")
    kind = record.get("kind")
    if not isinstance(code, int) or not isinstance(kind, int):
        return False
    if (code, kind) == (0x0A03, 0x00):
        return True
    return kind in {0x07, 0x08, 0x09, 0x0A} and code <= 0x0446


def _block_looks_like_header_list(records: list[dict[str, Any]]) -> bool:
    if not records:
        return False
    getter_like = sum(1 for record in records if _levelscript_getter_list_like_record(record))
    if getter_like:
        return False
    header_like = sum(1 for record in records if _levelscript_header_list_like_record(record))
    return header_like / len(records) >= 0.75


def _block_looks_like_levelscript_tail(records: list[dict[str, Any]]) -> bool:
    if not records:
        return False
    outside_like = 0
    for record in records:
        code = record.get("code")
        kind = record.get("kind")
        if isinstance(code, int) and isinstance(kind, int) and (
            (code, kind) == (0x0000, 0x00) or code < 0x0100
        ):
            outside_like += 1
    return outside_like / len(records) >= 0.5


def _next_uid_block_relation(
    data: bytes,
    records: list[dict[str, Any]],
    index: int,
) -> str:
    record_count = len(records)
    if index >= record_count:
        return "none"
    marker_offset = _record_start(records[index]) - 4
    marker_value = _u32(data, marker_offset)
    remaining = record_count - index
    if not _small_uid_list_count(marker_value, remaining):
        return "invalid-marker"
    block = records[index : index + int(marker_value)]
    if _block_looks_like_header_list(block) or any(
        _levelscript_getter_list_like_record(record) for record in block
    ):
        return "action-map-like"
    if _block_looks_like_levelscript_tail(block):
        return "levelscript-tail-like"
    return "unknown-block"
