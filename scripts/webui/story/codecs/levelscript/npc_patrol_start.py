"""Exact current-build ``NpcPatrolStart`` action payload decoder."""

from __future__ import annotations

import struct
from typing import Any


_ACTION_SEMANTIC_KEY = (0x031E, 0x0C)
_PARAM_TAIL = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"


def decode_npc_patrol_start_action(
    payload: bytes,
    semantic_key: tuple[int, int],
) -> dict[str, Any]:
    """Decode the action's exact four-field formatter shape."""
    if semantic_key != _ACTION_SEMANTIC_KEY:
        return {}

    cursor = 0

    def read_bool_param() -> bool | None:
        nonlocal cursor
        if (
            cursor + 14 > len(payload)
            or payload[cursor] != 0x04
            or payload[cursor + 1] not in (0, 1)
            or payload[cursor + 2 : cursor + 14] != _PARAM_TAIL
        ):
            return None
        value = bool(payload[cursor + 1])
        cursor += 14
        return value

    def read_i32_param() -> int | None:
        nonlocal cursor
        if (
            cursor + 17 > len(payload)
            or payload[cursor] != 0x04
            or payload[cursor + 5 : cursor + 17] != _PARAM_TAIL
        ):
            return None
        value = struct.unpack_from("<i", payload, cursor + 1)[0]
        cursor += 17
        return value

    start_from_beginning = read_bool_param()
    patrol_id = read_i32_param()
    force_idle = read_bool_param()
    if (
        start_from_beginning is None
        or patrol_id is None
        or force_idle is None
        or patrol_id <= 0
        or cursor + 27 > len(payload)
        or payload[cursor : cursor + 2] != b"\x04\x03"
    ):
        return {}
    logic_id = struct.unpack_from("<Q", payload, cursor + 2)[0]
    slot_id = struct.unpack_from("<I", payload, cursor + 10)[0]
    use_slot_id = payload[cursor + 14]
    id_ref = struct.unpack_from("<i", payload, cursor + 15)[0]
    param_source = struct.unpack_from("<i", payload, cursor + 19)[0]
    path_size = struct.unpack_from("<i", payload, cursor + 23)[0]
    cursor += 27
    if (
        use_slot_id not in (0, 1)
        or path_size <= 0
        or path_size > 256
        or cursor + path_size != len(payload)
    ):
        return {}
    try:
        target_path = payload[cursor : cursor + path_size].decode("utf-8")
    except UnicodeDecodeError:
        return {}
    if not target_path or any(ord(char) < 0x20 for char in target_path):
        return {}
    return {
        "action": "NpcPatrolStart",
        "startFromBeginning": start_from_beginning,
        "patrolId": patrol_id,
        "forceIdle": force_idle,
        "targetNpc": {
            "logicId": logic_id,
            "slotId": slot_id,
            "useSlotId": bool(use_slot_id),
            "idRef": id_ref,
            "paramSource": param_source,
            "path": target_path,
        },
        "payloadShape": "npc-patrol-start-four-field-exact-eof",
        "consumedBytes": len(payload),
    }
