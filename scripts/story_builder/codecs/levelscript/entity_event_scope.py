"""Exact current-build inherited ``EntityEventHeader`` scope decoder."""

from __future__ import annotations

import struct
from typing import Any


def decode_entity_event_header_scope(payload: bytes) -> dict[str, Any]:
    """Decode the serialized receiver selector without inferring ownership."""
    cursor = 17
    if cursor + 14 > len(payload) or payload[cursor] != 0x04:
        return {}
    validate_value = payload[cursor + 1]
    if validate_value not in (0, 1):
        return {}
    validate_id_ref = struct.unpack_from("<i", payload, cursor + 2)[0]
    validate_source = struct.unpack_from("<i", payload, cursor + 6)[0]
    validate_path_size = struct.unpack_from("<i", payload, cursor + 10)[0]
    cursor += 14
    if validate_path_size == -1:
        validate_path = None
    elif 0 <= validate_path_size <= 512 and cursor + validate_path_size <= len(payload):
        try:
            validate_path = payload[cursor : cursor + validate_path_size].decode("utf-8")
        except UnicodeDecodeError:
            return {}
        cursor += validate_path_size
    else:
        return {}
    if cursor + 27 > len(payload) or payload[cursor : cursor + 2] != b"\x04\x03":
        return {}
    logic_id = struct.unpack_from("<Q", payload, cursor + 2)[0]
    slot_id = struct.unpack_from("<I", payload, cursor + 10)[0]
    use_slot_id = payload[cursor + 14]
    if use_slot_id not in (0, 1):
        return {}
    cursor += 15
    if cursor + 12 > len(payload):
        return {}
    target_id_ref = struct.unpack_from("<i", payload, cursor)[0]
    target_source = struct.unpack_from("<i", payload, cursor + 4)[0]
    target_path_size = struct.unpack_from("<i", payload, cursor + 8)[0]
    cursor += 12
    if target_path_size == -1:
        target_path = None
    elif 0 <= target_path_size <= 512 and cursor + target_path_size <= len(payload):
        try:
            target_path = payload[cursor : cursor + target_path_size].decode("utf-8")
        except UnicodeDecodeError:
            return {}
        cursor += target_path_size
    else:
        return {}
    if payload[cursor : cursor + 17] != b"\x04" + b"\xff" * 8 + b"\x00" * 4 + b"\xff" * 4:
        return {}
    cursor += 17
    target_list_output_present = False
    target_list_output_encoding = "omitted-null"
    if cursor < len(payload) and payload[cursor] == 0xFF:
        cursor += 1
        target_list_output_encoding = "explicit-null"
    if cursor + 4 > len(payload):
        return {}
    trigger_target = struct.unpack_from("<i", payload, cursor)[0]
    cursor += 4
    if trigger_target != 1:
        return {}
    return {
        "validateParam": {
            "constValue": bool(validate_value),
            "idRef": validate_id_ref,
            "paramSource": validate_source,
            "path": validate_path,
        },
        "entityEventScope": "specified-entity",
        "triggerTarget": "SPECIFY_ENTITY",
        "targetEntity": {
            "logicId": logic_id,
            "slotId": slot_id,
            "useSlotId": bool(use_slot_id),
        },
        "targetEntityParam": {
            "idRef": target_id_ref,
            "paramSource": target_source,
            "path": target_path,
        },
        "targetEntityListPresent": False,
        "targetEntityListOutputPresent": target_list_output_present,
        "targetEntityListOutputEncoding": target_list_output_encoding,
        "_subtypeOffset": cursor,
    }
