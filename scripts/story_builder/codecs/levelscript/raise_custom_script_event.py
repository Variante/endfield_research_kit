"""Exact current-build ``RaiseCustomScriptEvent`` action decoder."""

from __future__ import annotations

import struct
from typing import Any


_ACTION_SEMANTIC_KEY = (0x0380, 0x0B)


def decode_raise_custom_script_event_action(
    payload: bytes,
    semantic_key: tuple[int, int],
    texts: list[str],
) -> dict[str, Any]:
    """Decode the exact event key and LevelScript receiver formatter fields.

    The receiver is either an explicit script id, the current LevelScript, or
    a dynamic/unresolved Param. Every other shape remains unclassified.
    """
    if semantic_key != _ACTION_SEMANTIC_KEY:
        return {}

    event_key_offset = 18
    param_tail_size = 12
    receiver_size = 29
    minimum_size = event_key_offset + 5 + param_tail_size + receiver_size
    if len(payload) < minimum_size or payload[event_key_offset] != 0x04:
        return {}
    event_key_size = struct.unpack_from("<I", payload, event_key_offset + 1)[0]
    if not 0 < event_key_size <= 512:
        return {}
    event_key_start = event_key_offset + 5
    event_key_end = event_key_start + event_key_size
    receiver_start = event_key_end + param_tail_size
    if receiver_start + receiver_size > len(payload):
        return {}
    try:
        event_key = payload[event_key_start:event_key_end].decode("utf-8")
    except UnicodeDecodeError:
        return {}
    if (
        not event_key
        or event_key.startswith("$")
        or event_key not in texts
        or any(ord(char) < 0x20 or ord(char) == 0x7F for char in event_key)
    ):
        return {}
    receiver = payload[receiver_start : receiver_start + receiver_size]
    if receiver[0] != 0x04 or receiver[1] not in (0, 1):
        return {}
    has_const_value = bool(receiver[1])
    const_script_id = struct.unpack_from("<Q", receiver, 2)[0]
    id_ref = struct.unpack_from("<i", receiver, 17)[0]
    param_source = struct.unpack_from("<i", receiver, 21)[0]
    path_length = struct.unpack_from("<i", receiver, 25)[0]
    receiver_mode = "dynamic_or_unresolved"
    target_script_id: int | None = None
    if (
        not has_const_value
        and const_script_id == 0
        and id_ref == -1
        and param_source == 1002
        and path_length == -1
    ):
        receiver_mode = "current_script"
    elif (
        has_const_value
        and 1_000_000 <= const_script_id <= 999_999_999_999
        and id_ref == -1
        and param_source == 0
        and path_length == -1
    ):
        receiver_mode = "constant_script"
        target_script_id = const_script_id
    detail = {
        "action": "RaiseCustomScriptEvent",
        "eventKey": event_key,
        "receiverMode": receiver_mode,
        "targetScriptId": target_script_id,
        "receiver": {
            "hasConstValue": has_const_value,
            "constScriptId": const_script_id,
            "idRef": id_ref,
            "paramSource": param_source,
            "pathLength": path_length,
            "payloadOffset": f"0x{receiver_start:x}",
        },
        "payloadShape": "raise-custom-script-event-exact-current-build",
    }
    return {
        key: value
        for key, value in detail.items()
        if value not in (None, "", [], {})
    }
