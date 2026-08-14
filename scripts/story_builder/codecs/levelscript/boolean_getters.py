"""Exact current-build Boolean PureGetter combinator codecs."""

from __future__ import annotations

import struct
from typing import Any

from .params import decode_bool_param, decode_i32_param


def _decode_pure_bool_getter_ref(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode one exact ``PureGetter<bool>`` local-reference envelope."""
    if (
        cursor + 14 > len(payload)
        or payload[cursor : cursor + 2] != b"\x04\x00"
        or payload[cursor + 6 : cursor + 14] != b"\xff" * 8
    ):
        return None
    local_id = struct.unpack_from("<i", payload, cursor + 2)[0]
    if local_id < 0 or local_id > 0x10000:
        return None
    return {
        "operandKind": "localGetterRef",
        "getterLocalId": local_id,
    }, cursor + 14


def _decode_bool_operand(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    getter_ref = _decode_pure_bool_getter_ref(payload, cursor)
    if getter_ref is not None:
        return getter_ref
    return decode_bool_param(payload, cursor)


def _finish_getter_fields(
    payload: bytes,
    end: int,
    detail: dict[str, Any],
) -> dict[str, Any]:
    """Accept exact subtype EOF or one proven outer-list u32 trailer."""
    if end == len(payload):
        return detail
    if end + 4 != len(payload):
        return {}
    return {
        **detail,
        "trailingActionMapFramingU32": struct.unpack_from("<I", payload, end)[0],
    }


def decode_boolean_compare(payload: bytes) -> dict[str, Any]:
    comparer = decode_i32_param(payload, 0)
    if comparer is None:
        return {}
    value_a = _decode_bool_operand(payload, comparer[1])
    if value_a is None:
        return {}
    value_b = _decode_bool_operand(payload, value_a[1])
    if value_b is None:
        return {}
    comparer_raw = comparer[0]["value"]
    return _finish_getter_fields(payload, value_b[1], {
        "comparerRaw": comparer_raw,
        "comparerName": {0: "Equal", 1: "NotEqual"}.get(comparer_raw, ""),
        "valueA": value_a[0],
        "valueB": value_b[0],
        "payloadShape": "bool-comparer-two-polymorphic-bool-operands-exact-fields",
    })


def decode_binary(payload: bytes, operation: str) -> dict[str, Any]:
    value_a = _decode_pure_bool_getter_ref(payload, 0)
    if value_a is None:
        return {}
    value_b = _decode_pure_bool_getter_ref(payload, value_a[1])
    if value_b is None:
        return {}
    return _finish_getter_fields(payload, value_b[1], {
        "operation": operation,
        "valueA": value_a[0],
        "valueB": value_b[0],
        "payloadShape": "two-pure-bool-getter-refs-exact-fields",
    })


def decode_invert(payload: bytes) -> dict[str, Any]:
    value = _decode_pure_bool_getter_ref(payload, 0)
    if value is None:
        return {}
    return _finish_getter_fields(payload, value[1], {
        "operation": "Not",
        "value": value[0],
        "payloadShape": "one-pure-bool-getter-ref-exact-fields",
    })


def decode_multi_and(payload: bytes) -> dict[str, Any]:
    if len(payload) < 4:
        return {}
    count = struct.unpack_from("<I", payload, 0)[0]
    if count == 0 or count > 256:
        return {}
    cursor = 4
    values: list[dict[str, Any]] = []
    for _index in range(count):
        value = _decode_pure_bool_getter_ref(payload, cursor)
        if value is None:
            return {}
        values.append(value[0])
        cursor = value[1]
    return _finish_getter_fields(payload, cursor, {
        "operation": "All",
        "values": values,
        "payloadShape": "counted-pure-bool-getter-refs-exact-fields",
    })


def decode_getter_bool(payload: bytes) -> dict[str, Any]:
    value = decode_bool_param(payload, 0)
    if value is None:
        return {}
    return _finish_getter_fields(payload, value[1], {
        "value": value[0],
        "payloadShape": "one-bool-param-exact-fields",
    })


def decode_boolean_getter_fields(
    payload: bytes,
    semantic_key: tuple[int, int],
) -> tuple[str, dict[str, Any]]:
    """Decode the Boolean getter selected by its current formatter identity."""
    if semantic_key == (0x0004, 0x0A):
        return "booleanCompare", decode_boolean_compare(payload)
    if semantic_key == (0x0006, 0x09):
        return "boolGetterAnd", decode_binary(payload, "And")
    if semantic_key == (0x000A, 0x08):
        return "boolGetterInvert", decode_invert(payload)
    if semantic_key == (0x000B, 0x08):
        return "boolGetterMultiAnd", decode_multi_and(payload)
    if semantic_key == (0x000D, 0x09):
        return "boolGetterOr", decode_binary(payload, "Or")
    if semantic_key == (0x017C, 0x08):
        return "getterBool", decode_getter_bool(payload)
    return "", {}
