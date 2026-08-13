"""Exact current-build integer and string Switch action decoders."""

from __future__ import annotations

import struct
from typing import Any


_INTEGER_SWITCH_CONFIG = {
    (0x04BD, 0x0C): ("switch", "typed-switch-int-actions"),
    (0x04BE, 0x0C): (
        "switchIntLarger",
        "typed-switch-int-larger-actions",
    ),
}
_STRING_SWITCH_SEMANTIC_KEY = (0x04BF, 0x0C)


def _read_i32_list(
    payload: bytes,
    cursor: int,
) -> tuple[list[int], int] | None:
    """Read one bounded MemoryPack i32 list without consuming outer framing."""
    if cursor + 4 > len(payload):
        return None
    count = struct.unpack_from("<I", payload, cursor)[0]
    cursor += 4
    if count > 64 or cursor + count * 4 > len(payload):
        return None
    values = [
        struct.unpack_from("<i", payload, cursor + index * 4)[0]
        for index in range(count)
    ]
    return values, cursor + count * 4


def _read_string_list(
    payload: bytes,
    cursor: int,
) -> tuple[list[str | None], int] | None:
    if cursor + 4 > len(payload):
        return None
    count = struct.unpack_from("<I", payload, cursor)[0]
    cursor += 4
    if count > 64:
        return None
    values: list[str | None] = []
    for _ in range(count):
        if cursor + 4 > len(payload):
            return None
        size = struct.unpack_from("<i", payload, cursor)[0]
        cursor += 4
        if size == -1:
            values.append(None)
            continue
        if size < 0 or size > 1024 or cursor + size > len(payload):
            return None
        try:
            value = payload[cursor : cursor + size].decode("utf-8")
        except UnicodeDecodeError:
            return None
        if any(ord(char) < 0x20 or ord(char) == 0x7F for char in value):
            return None
        values.append(value)
        cursor += size
    return values, cursor


def _decode_param_tail(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    if cursor + 12 > len(payload):
        return None
    id_ref, param_source, path_size = struct.unpack_from("<iii", payload, cursor)
    cursor += 12
    if id_ref < -1 or param_source < 0 or param_source > 0x10000:
        return None
    if path_size == -1:
        path = None
    elif 0 <= path_size <= 1024 and cursor + path_size <= len(payload):
        try:
            path = payload[cursor : cursor + path_size].decode("utf-8")
        except UnicodeDecodeError:
            return None
        cursor += path_size
    else:
        return None
    return {"idRef": id_ref, "paramSource": param_source, "path": path}, cursor


def _decode_i32_param(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    if cursor + 5 > len(payload) or payload[cursor] != 0x04:
        return None
    value = struct.unpack_from("<i", payload, cursor + 1)[0]
    tail = _decode_param_tail(payload, cursor + 5)
    if tail is None:
        return None
    detail, end = tail
    return {"value": value, **detail}, end


def _decode_string_param(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    if cursor + 5 > len(payload) or payload[cursor] != 0x04:
        return None
    size = struct.unpack_from("<i", payload, cursor + 1)[0]
    cursor += 5
    if size == -1:
        value = None
    elif 0 <= size <= 1024 and cursor + size <= len(payload):
        try:
            value = payload[cursor : cursor + size].decode("utf-8")
        except UnicodeDecodeError:
            return None
        cursor += size
    else:
        return None
    tail = _decode_param_tail(payload, cursor)
    if tail is None:
        return None
    detail, end = tail
    return {"value": value, **detail}, end


def _decode_integer_switch(
    payload: bytes,
    field_prefix: str,
    branch_role: str,
) -> dict[str, Any]:
    """Decode the shared ``SwitchInt``/``SwitchIntLarger`` formatter shape."""
    case_ids_result = _read_i32_list(payload, 0)
    if case_ids_result is None:
        return {}
    case_ids, cursor = case_ids_result
    case_values_result = _read_i32_list(payload, cursor)
    if case_values_result is None:
        return {}
    case_values, cursor = case_values_result
    if len(case_ids) != len(case_values) or cursor + 4 > len(payload):
        return {}
    default_id = struct.unpack_from("<i", payload, cursor)[0]
    cursor += 4
    value_getter = payload[cursor:]

    # The formatter's final polymorphic PureGetter<int> must consume the full
    # tail; scalar prefixes alone are not evidence of a branch table.
    if len(value_getter) < 14 or value_getter[0] != 0x04:
        return {}
    if any(ref < -1 or ref > 0x10000 for ref in [*case_ids, default_id]):
        return {}

    branch_refs = list(dict.fromkeys(
        ref for ref in [*case_ids, default_id] if ref > 0
    ))
    out: dict[str, Any] = {
        f"{field_prefix}CaseActionLocalIds": case_ids,
        f"{field_prefix}CaseValues": case_values,
        f"{field_prefix}Cases": [
            {"value": value, "actionLocalId": action_id}
            for value, action_id in zip(case_values, case_ids)
        ],
        f"{field_prefix}DefaultActionLocalId": default_id,
        f"{field_prefix}ValueGetterPayloadLength": len(value_getter),
        f"{field_prefix}ValueGetterHexPrefix": value_getter[:32].hex(" "),
        "branchLocalRefs": branch_refs,
        "branchRole": branch_role,
    }
    getter_field = f"{field_prefix}ValueGetterLocalId"
    if (
        len(value_getter) == 17
        and value_getter[:5] == b"\x04\x00\x00\x00\x00"
        and value_getter[9:] == b"\xff" * 8
    ):
        getter_id = struct.unpack_from("<i", value_getter, 5)[0]
        if 0 <= getter_id <= 0x10000:
            out[getter_field] = getter_id
    if getter_field not in out:
        inline_value = _decode_i32_param(value_getter, 0)
        if inline_value is not None and inline_value[1] == len(value_getter):
            out[f"{field_prefix}ValueParam"] = inline_value[0]
    return out


def _decode_string_switch(payload: bytes) -> dict[str, Any]:
    """Decode the current-build ``SwitchString`` branch table exactly."""
    case_ids_result = _read_i32_list(payload, 0)
    if case_ids_result is None:
        return {}
    case_ids, cursor = case_ids_result
    case_values_result = _read_string_list(payload, cursor)
    if case_values_result is None:
        return {}
    case_values, cursor = case_values_result
    if len(case_ids) != len(case_values) or cursor + 4 > len(payload):
        return {}
    default_id = struct.unpack_from("<i", payload, cursor)[0]
    cursor += 4
    if any(ref < -1 or ref > 0x10000 for ref in [*case_ids, default_id]):
        return {}

    value_param = _decode_string_param(payload, cursor)
    value_getter_local_id: int | None = None
    if value_param is not None and value_param[1] == len(payload):
        value_detail = value_param[0]
    elif (
        cursor + 17 == len(payload)
        and payload[cursor] == 0x04
        and payload[cursor + 1 : cursor + 5] == b"\xff" * 4
        and payload[cursor + 9 : cursor + 17] == b"\xff" * 8
    ):
        value_getter_local_id = struct.unpack_from("<i", payload, cursor + 5)[0]
        if value_getter_local_id <= 0 or value_getter_local_id > 0x10000:
            return {}
        value_detail = {
            "value": None,
            "idRef": value_getter_local_id,
            "paramSource": -1,
            "path": None,
        }
    else:
        return {}

    branch_refs = list(dict.fromkeys(
        ref for ref in [*case_ids, default_id] if ref > 0
    ))
    out: dict[str, Any] = {
        "switchStringCaseActionLocalIds": case_ids,
        "switchStringCaseValues": case_values,
        "switchStringCases": [
            {"value": value, "actionLocalId": action_id}
            for value, action_id in zip(case_values, case_ids)
        ],
        "switchStringDefaultActionLocalId": default_id,
        "switchStringValueParam": value_detail,
        "branchLocalRefs": branch_refs,
        "branchRole": "typed-switch-string-actions",
        "payloadShape": "switch-string-four-fields-exact-eof",
        "consumedBytes": len(payload),
    }
    if value_getter_local_id is not None:
        out["switchStringValueGetterLocalId"] = value_getter_local_id
    return out


def decode_switch_action(
    payload: bytes,
    semantic_key: tuple[int, int],
) -> dict[str, Any]:
    """Decode one exact Switch family member selected by its formatter key."""
    integer_config = _INTEGER_SWITCH_CONFIG.get(semantic_key)
    if integer_config is not None:
        return _decode_integer_switch(payload, *integer_config)
    if semantic_key == _STRING_SWITCH_SEMANTIC_KEY:
        return _decode_string_switch(payload)
    return {}
