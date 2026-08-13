"""Exact current-build ``CallServer`` action prefix decoder."""

from __future__ import annotations

import struct
from typing import Any


def _decode_param_tail(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode the exact idRef/source/path tail of an authored Param value."""
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


def _decode_constant_string_param(
    payload: bytes,
    cursor: int,
) -> tuple[str, int] | None:
    """Decode one constant ``Param<string>`` with its exact default tail."""
    if cursor + 5 > len(payload) or payload[cursor] != 0x04:
        return None
    size = struct.unpack_from("<i", payload, cursor + 1)[0]
    cursor += 5
    if size <= 0 or size > 256 or cursor + size > len(payload):
        return None
    try:
        value = payload[cursor : cursor + size].decode("utf-8")
    except UnicodeDecodeError:
        return None
    tail = _decode_param_tail(payload, cursor + size)
    if tail is None:
        return None
    detail, end = tail
    if detail != {"idRef": -1, "paramSource": 0, "path": None}:
        return None
    return value, end


def decode_call_server_action(payload: bytes) -> dict[str, Any]:
    """Decode the six generated fields in the current ``CallServer`` prefix.

    The decoder consumes the variable-length callback UID list followed by
    event-args, event-name and three boolean members. It deliberately reports
    remaining container bytes instead of treating them as another schema.
    """
    if len(payload) < 4:
        return {}

    output_count = struct.unpack_from("<i", payload, 0)[0]
    if output_count < -1 or output_count > 4096:
        return {}
    cursor = 4
    call_client_output_uids: list[str] | None = None
    if output_count >= 0:
        call_client_output_uids = []
        for _index in range(output_count):
            if cursor + 4 > len(payload):
                return {}
            value_size = struct.unpack_from("<i", payload, cursor)[0]
            cursor += 4
            if value_size < 0 or cursor + value_size > len(payload):
                return {}
            try:
                value = payload[cursor : cursor + value_size].decode("utf-8")
            except UnicodeDecodeError:
                return {}
            cursor += value_size
            call_client_output_uids.append(value)

    if cursor + 6 > len(payload) or payload[cursor : cursor + 2] != b"\x04\x01":
        return {}
    event_args_size = struct.unpack_from("<i", payload, cursor + 2)[0]
    cursor += 6
    if event_args_size <= 0 or cursor + event_args_size > len(payload):
        return {}
    try:
        event_args_path = payload[cursor : cursor + event_args_size].decode("utf-8")
    except UnicodeDecodeError:
        return {}
    event_args_tail = _decode_param_tail(payload, cursor + event_args_size)
    if event_args_tail is None:
        return {}
    event_args_detail, cursor = event_args_tail
    event_name = _decode_constant_string_param(payload, cursor)
    if event_name is None:
        return {}
    event_name_value, cursor = event_name
    if cursor + 3 > len(payload) or any(
        value not in (0, 1)
        for value in payload[cursor : cursor + 3]
    ):
        return {}
    use_custom_event, wait_for_callback, with_event_args = (
        bool(value) for value in payload[cursor:cursor + 3]
    )
    cursor += 3
    return {
        "payloadShape": "six-call-server-fields-exact-prefix",
        "callClientOutputUIDs": call_client_output_uids,
        "eventArgsPtr": {
            "pathValue": event_args_path,
            **event_args_detail,
        },
        "eventName": event_name_value,
        "useCustomEvent": use_custom_event,
        "waitForCallback": wait_for_callback,
        "withEventArgs": with_event_args,
        "consumedBytes": cursor,
        "trailingBytes": len(payload) - cursor,
    }
