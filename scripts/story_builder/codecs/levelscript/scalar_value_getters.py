"""Exact current-build scalar PureGetter codecs."""

from __future__ import annotations

import struct
from typing import Any

from . import params


FLOAT_NEW_COMPARE = (0x0049, 0x0A)
GETTER_INT = (0x0184, 0x08)
GETTER_STRING = (0x01A5, 0x08)
INT_COMPARE = (0x01AA, 0x0A)
INT_EQUAL = (0x01AC, 0x09)
INT_RANDOM = (0x01BA, 0x09)
IS_ENDMIN_GENDER = (0x01C2, 0x08)


def _decode_i32_operand(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    getter_ref = params.decode_local_getter_ref(payload, cursor)
    if getter_ref is not None:
        return {
            "operandKind": "localGetterRef",
            "getterLocalId": getter_ref[0],
        }, getter_ref[1]
    return params.decode_i32_param(payload, cursor)


def _decode_int_equal(payload: bytes) -> dict[str, Any]:
    value_a = _decode_i32_operand(payload, 0)
    if value_a is None:
        return {}
    value_b = _decode_i32_operand(payload, value_a[1])
    if value_b is None:
        return {}
    has_getter_ref = any(
        operand.get("operandKind") == "localGetterRef"
        for operand in (value_a[0], value_b[0])
    )
    detail = {
        "operation": "Equal",
        "valueA": value_a[0],
        "valueB": value_b[0],
        "payloadShape": (
            "two-int-operands-exact-eof"
            if has_getter_ref
            else "two-int-params-exact-eof"
        ),
    }
    for label, operand in (("valueA", value_a[0]), ("valueB", value_b[0])):
        getter_local_id = operand.get("getterLocalId")
        if isinstance(getter_local_id, int):
            detail[f"{label}GetterLocalId"] = getter_local_id
    return params.finish_getter_fields(payload, value_b[1], detail)


def _decode_int_random(payload: bytes) -> dict[str, Any]:
    # Generated setter order is _max, then _min.
    maximum = params.decode_i32_param(payload, 0)
    if maximum is None:
        return {}
    minimum = params.decode_i32_param(payload, maximum[1])
    if minimum is None:
        return {}
    return params.finish_getter_fields(payload, minimum[1], {
        "minimum": minimum[0],
        "maximum": maximum[0],
        "payloadShape": "max-then-min-int-params-exact-fields",
    })


def _decode_number_compare(payload: bytes, *, floating: bool) -> dict[str, Any]:
    comparer = params.decode_i32_param(payload, 0)
    if comparer is None:
        return {}
    value_a = params.decode_local_getter_ref(payload, comparer[1])
    if value_a is None:
        return {}
    decoder = params.decode_float_param if floating else params.decode_i32_param
    value_b = decoder(payload, value_a[1])
    if value_b is None:
        return {}
    comparer_raw = comparer[0]["value"]
    return params.finish_getter_fields(payload, value_b[1], {
        "comparerRaw": comparer_raw,
        "comparerName": {
            0: "Equal",
            1: "NotEqual",
            2: "GreaterThan",
            3: "GreaterEqual",
            4: "LessThan",
            5: "LessEqual",
        }.get(comparer_raw, ""),
        "valueAGetterLocalId": value_a[0],
        "valueB": value_b[0],
        "valueType": "float" if floating else "int",
        "payloadShape": "number-comparer-getter-ref-constant-exact-eof",
    })


def _decode_getter_int(payload: bytes) -> dict[str, Any]:
    value = params.decode_i32_param(payload, 0)
    if value is None:
        return {}
    return params.finish_getter_fields(payload, value[1], {
        "value": value[0],
        "payloadShape": "one-int-param-exact-eof",
    })


def _decode_getter_string(payload: bytes) -> dict[str, Any]:
    if len(payload) < 17 or payload[0] != 0x04:
        return {}
    value_size, id_ref, param_source, path_size = struct.unpack_from(
        "<iiii", payload, 1
    )
    if (
        value_size != -1
        or id_ref != -1
        or param_source < 0
        or param_source > 0x10000
        or path_size <= 0
        or path_size > 1024
        or 17 + path_size != len(payload)
    ):
        return {}
    try:
        path = payload[17:].decode("utf-8")
    except UnicodeDecodeError:
        return {}
    return {
        "value": None,
        "idRef": id_ref,
        "paramSource": param_source,
        "path": path,
        "payloadShape": "nullable-string-property-path-exact-eof",
    }


def _decode_is_endmin_gender(payload: bytes) -> dict[str, Any]:
    gender = params.decode_i32_param(payload, 0)
    if gender is None:
        return {}
    raw = gender[0]["value"]
    return params.finish_getter_fields(payload, gender[1], {
        "gender": gender[0],
        "genderName": {0: "Male", 1: "Female"}.get(raw, ""),
        "payloadShape": "gender-param-exact-fields",
    })


def decode_scalar_value_getter(
    payload: bytes,
    semantic_key: tuple[int, int],
) -> tuple[str, dict[str, Any]]:
    if semantic_key in {FLOAT_NEW_COMPARE, INT_COMPARE}:
        detail = _decode_number_compare(
            payload,
            floating=semantic_key == FLOAT_NEW_COMPARE,
        )
        field_name = (
            "floatNewCompare"
            if semantic_key == FLOAT_NEW_COMPARE
            else "intCompare"
        )
        return field_name, detail
    decoders = {
        GETTER_INT: ("getterInt", _decode_getter_int),
        GETTER_STRING: ("getterString", _decode_getter_string),
        INT_EQUAL: ("intEqual", _decode_int_equal),
        INT_RANDOM: ("intRandom", _decode_int_random),
        IS_ENDMIN_GENDER: ("isEndminGender", _decode_is_endmin_gender),
    }
    field_name, decoder = decoders.get(semantic_key, ("", None))
    return (field_name, decoder(payload)) if decoder is not None else ("", {})
