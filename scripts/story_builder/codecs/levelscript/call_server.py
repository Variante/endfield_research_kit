"""Exact current-build ``CallServer`` action prefix decoder."""

from __future__ import annotations

import struct
from typing import Any

from .params import decode_constant_string_param, decode_param_tail

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
    event_args_tail = decode_param_tail(payload, cursor + event_args_size)
    if event_args_tail is None:
        return {}
    event_args_detail, cursor = event_args_tail
    event_name = decode_constant_string_param(payload, cursor)
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
