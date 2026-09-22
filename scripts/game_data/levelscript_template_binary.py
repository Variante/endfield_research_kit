"""Partial exact-range reader for ``LevelScriptTemplateData`` payloads."""

from __future__ import annotations

import struct
from typing import Any

from scripts.game_data.codecs.levelscript.action_map import (
    ActionMapCodecError,
    decode_action_serialized_map,
)
from scripts.game_data.codecs.levelscript.interactives import (
    LevelInteractiveCodecError,
    decode_param_key_value_list,
)
from scripts.game_data.levelscript_binary import (
    LevelScriptTopLevelFramingError,
    decode_levelscript_task_map_exact,
    frame_levelscript_action_map_named_prefix,
)
from scripts.game_data.native_contracts.levelscript_param_list import (
    load_param_list_for_graph_contract,
)


ROOT_MEMBER_COUNT = 6
MAX_TEMPLATE_ID_BYTES = 512
NULL_COUNT = 0xFFFFFFFF
ROOT_FIELDS = (
    "actionMap",
    "maxStage",
    "properties",
    "propertyIdToKeyMap",
    "taskMap",
    "templateId",
)


class LevelScriptTemplateFramingError(ValueError):
    """Raised when the template root endpoints cannot be framed uniquely."""


def _read_i32_string(data: bytes, offset: int, field: str) -> tuple[str | None, int]:
    if offset + 4 > len(data):
        raise LevelScriptTemplateFramingError(f"{field}: truncated string length")
    length = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    if length == NULL_COUNT:
        return None, offset
    if length > 1 << 20 or offset + length > len(data):
        raise LevelScriptTemplateFramingError(f"{field}: invalid string length {length}")
    try:
        value = data[offset:offset + length].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LevelScriptTemplateFramingError(f"{field}: invalid UTF-8") from exc
    return value, offset + length


def _decode_property_id_map(data: bytes, offset: int) -> tuple[dict[int, str] | None, int]:
    if offset + 4 > len(data):
        raise LevelScriptTemplateFramingError("propertyIdToKeyMap: truncated count")
    count = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    if count == NULL_COUNT:
        return None, offset
    if count > 16_384:
        raise LevelScriptTemplateFramingError(
            f"propertyIdToKeyMap: implausible count {count}"
        )
    result: dict[int, str] = {}
    for index in range(count):
        if offset + 4 > len(data):
            raise LevelScriptTemplateFramingError(
                f"propertyIdToKeyMap[{index}]: truncated key"
            )
        key = struct.unpack_from("<i", data, offset)[0]
        offset += 4
        value, offset = _read_i32_string(data, offset, f"propertyIdToKeyMap[{index}].value")
        if value is None or key in result:
            raise LevelScriptTemplateFramingError(
                f"propertyIdToKeyMap[{index}]: null value or duplicate key {key}"
            )
        result[key] = value
    return result, offset


def _decode_action_map_exact(data: bytes) -> tuple[dict[str, Any], int]:
    """Consume the two-member template ActionMap at its declared cursor."""
    if len(data) < 3 or data[1] != 2:
        actual = data[1] if len(data) > 1 else None
        raise LevelScriptTemplateFramingError(
            f"actionMap member count mismatch: expected=2 actual={actual}"
        )
    try:
        data_map, cursor = decode_action_serialized_map(data, 2)
    except ActionMapCodecError as exc:
        raise LevelScriptTemplateFramingError(str(exc)) from exc
    if data_map is None:
        raise LevelScriptTemplateFramingError("actionMap.dataMap is null")
    if cursor + 5 > len(data) or data[cursor] != 1:
        actual = data[cursor:cursor + 5].hex(" ")
        raise LevelScriptTemplateFramingError(
            "actionMap.paramBlackboard header mismatch: "
            f"expected memberCount=1 actual={actual}"
        )
    value_count = struct.unpack_from("<i", data, cursor + 1)[0]
    if value_count != 0:
        layout, audit = load_param_list_for_graph_contract()
        if layout is None:
            raise LevelScriptTemplateFramingError(
                "actionMap.paramBlackboard.nativeContract: "
                f"status={audit['status']}, count={value_count}, "
                f"detail={audit.get('detail', '')}"
            )
    try:
        values, end = decode_param_key_value_list(
            data, cursor + 1, "actionMap.paramBlackboard.value"
        )
    except LevelInteractiveCodecError as exc:
        raise LevelScriptTemplateFramingError(str(exc)) from exc
    fields = {
        "dataMap": {
            "memberCount": data_map["memberCount"],
            "rawListCounts": data_map["rawListCounts"],
            "actionList": data_map.get("actions", []),
            "getterList": data_map.get("getters", []),
            "headerList": data_map.get("headers", []),
        },
        "paramBlackboard": {"value": values["values"]},
    }
    return {
        "startOffset": 1,
        "endOffset": end,
        "status": "exact_named_action_map",
        "fields": fields,
    }, end


def frame_levelscript_template(data: bytes) -> dict[str, Any]:
    """Frame the actionMap endpoint and final templateId through EOF.

    The four intervening top-level members and any unclosed action-map bytes
    remain one opaque range. The final UTF-8 field is selected only when its
    signed length prefix closes at physical EOF and the candidate is unique.
    """
    if not data or data[0] != ROOT_MEMBER_COUNT:
        actual = data[0] if data else None
        raise LevelScriptTemplateFramingError(
            f"template member count mismatch: expected={ROOT_MEMBER_COUNT} actual={actual}"
        )
    try:
        action_map, prefix_end = _decode_action_map_exact(data)
    except LevelScriptTemplateFramingError as exact_error:
        try:
            prefix = frame_levelscript_action_map_named_prefix(
                data, expected_member_count=ROOT_MEMBER_COUNT
            )
        except LevelScriptTopLevelFramingError as exc:
            raise LevelScriptTemplateFramingError(str(exc)) from exc
        prefix_end = int(prefix["bytesConsumed"])
        action_map = {
            "startOffset": 1,
            "endOffset": prefix_end,
            "status": prefix["status"],
            "ranges": prefix.get("ranges"),
            "unresolvedReason": str(exact_error),
        }

    candidates: list[tuple[int, str]] = []
    for offset in range(max(prefix_end, len(data) - MAX_TEMPLATE_ID_BYTES - 4), len(data) - 3):
        length = struct.unpack_from("<i", data, offset)[0]
        if length <= 0 or length > MAX_TEMPLATE_ID_BYTES or offset + 4 + length != len(data):
            continue
        try:
            value = data[offset + 4 :].decode("utf-8")
        except UnicodeDecodeError:
            continue
        if any(ord(character) < 0x20 for character in value):
            continue
        candidates.append((offset, value))
    if len(candidates) != 1:
        raise LevelScriptTemplateFramingError(
            f"templateId EOF field is not unique: candidates={len(candidates)}"
        )
    template_offset, template_id = candidates[0]
    if template_offset < prefix_end:
        raise LevelScriptTemplateFramingError("templateId overlaps the action-map prefix")
    result = {
        "status": "exact_endpoint_ranges_with_opaque_middle",
        "schemaStatus": "partial",
        "serializedMemberCount": ROOT_MEMBER_COUNT,
        "bytesConsumed": len(data),
        "actionMap": action_map,
        "opaqueMiddle": {
            "startOffset": prefix_end,
            "endOffset": template_offset,
            "length": template_offset - prefix_end,
        },
        "templateId": {
            "startOffset": template_offset,
            "endOffset": len(data),
            "value": template_id,
        },
        "evidenceBoundary": (
            "The six-member root, action-map prefix, and final templateId field close exact "
            "ranges through EOF. The intervening properties, maps, and any remaining action-map "
            "payload stay opaque."
        ),
    }
    if action_map["status"] == "exact_named_action_map":
        try:
            if prefix_end + 4 > template_offset:
                raise LevelScriptTemplateFramingError("maxStage: truncated int32")
            max_stage = struct.unpack_from("<i", data, prefix_end)[0]
            cursor = prefix_end + 4
            properties, cursor = decode_param_key_value_list(data, cursor, "properties")
            property_map, cursor = _decode_property_id_map(data, cursor)
            if cursor + 4 > template_offset:
                raise LevelScriptTemplateFramingError("taskMap: truncated count")
            task_count = struct.unpack_from("<I", data, cursor)[0]
            cursor += 4
        except (LevelInteractiveCodecError, LevelScriptTemplateFramingError):
            pass
        else:
            result["namedPrefix"] = {
                "maxStage": max_stage,
                "properties": properties,
                "propertyIdToKeyMap": property_map,
                "taskMapCount": None if task_count == NULL_COUNT else task_count,
                "endOffset": cursor,
            }
            if task_count == NULL_COUNT and cursor == template_offset:
                property_entries = properties.get("values")
                result.update({
                    "status": "exact_named_action_map_null_task_template",
                    "schemaStatus": "named_exact",
                    "fieldOrder": list(ROOT_FIELDS),
                    "fields": {
                        "actionMap": action_map["fields"],
                        "maxStage": max_stage,
                        "properties": property_entries,
                        "propertyIdToKeyMap": property_map,
                        "taskMap": None,
                        "templateId": template_id,
                    },
                    "opaqueMiddle": None,
                    "evidenceBoundary": (
                        "All six generated wrapper fields are named and exactly consumed "
                        "for a reviewed action map and null task map."
                    ),
                })
            elif task_count <= 128:
                try:
                    tasks, task_end = decode_levelscript_task_map_exact(
                        data, cursor, task_count, template_offset
                    )
                except LevelScriptTopLevelFramingError:
                    pass
                else:
                    result.update({
                        "status": "exact_named_action_map_task_template",
                        "schemaStatus": "named_exact",
                        "fieldOrder": list(ROOT_FIELDS),
                        "fields": {
                        "actionMap": action_map["fields"],
                            "maxStage": max_stage,
                            "properties": properties.get("values"),
                            "propertyIdToKeyMap": property_map,
                            "taskMap": tasks,
                            "templateId": template_id,
                        },
                        "opaqueMiddle": None,
                        "namedPrefix": {
                            **result["namedPrefix"],
                            "endOffset": task_end,
                        },
                        "evidenceBoundary": (
                            "All six generated wrapper fields are named and exactly consumed; "
                            "the counted task map closes at the terminal templateId boundary."
                        ),
                    })
    return result
