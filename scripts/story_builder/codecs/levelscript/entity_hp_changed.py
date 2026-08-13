"""Exact current-build ``OnEntityHpChanged`` event payload decoder."""

from __future__ import annotations

import math
import struct
from typing import Any


_EVENT_SEMANTIC_KEY = (0x006A, 0x12)
_PARAM_TAIL = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"


def decode_entity_hp_changed_event(
    payload: bytes,
    semantic_key: tuple[int, int],
    *,
    header_role: bool,
) -> dict[str, Any]:
    """Decode the exact single-entity or dynamic-list event shape."""
    if not header_role or semantic_key != _EVENT_SEMANTIC_KEY:
        return {}

    if len(payload) != 84:
        # The dynamic-list form stores a LevelScript property path in
        # ``_entityFilter`` and a null output before the ratio.
        if len(payload) < 70 or payload[35] != 0x04 or payload[36:44] != b"\xff" * 8:
            return {}
        direction = struct.unpack_from("<i", payload, 31)[0]
        source = struct.unpack_from("<i", payload, 44)[0]
        path_size = struct.unpack_from("<i", payload, 48)[0]
        path_start = 52
        path_end = path_start + path_size
        if (
            direction not in (0, 1, 2)
            or path_size <= 0
            or path_size > 256
            or path_end + 18 != len(payload)
            or payload[path_end] != 0xFF
            or payload[path_end + 1] != 0x04
            or payload[path_end + 6 : path_end + 18] != _PARAM_TAIL
        ):
            return {}
        try:
            path = payload[path_start:path_end].decode("utf-8")
        except UnicodeDecodeError:
            return {}
        hp_ratio = struct.unpack_from("<f", payload, path_end + 2)[0]
        if not math.isfinite(hp_ratio) or not 0 <= hp_ratio <= 1:
            return {}
        direction_name = ("Down", "Up", "UpAndDown")[direction]
        direction_phrase = ("falls", "rises", "crosses")[direction]
        return {
            "type": "LevelEvent_OnEntityHpChanged",
            "changedDirection": direction,
            "changedDirectionName": direction_name,
            "entityListFilter": {
                "paramSource": source,
                "path": path,
            },
            "entityOutputPresent": False,
            "hpRatio": round(hp_ratio, 6),
            "transport": "local-entity-hp-runtime-event",
            "serverExchange": False,
            "serializedMissionOrQuestId": False,
            "summary": (
                f"entity list {path} HP {direction_phrase} through "
                f"{round(hp_ratio * 100, 3):g}%"
            ),
            "payloadShape": "dynamic-entity-list-hp-ratio-event",
        }

    if not (
        payload[17] == 4
        and payload[18] in (0, 1)
        and struct.unpack_from("<i", payload, 19)[0] == -1
        and struct.unpack_from("<i", payload, 23)[0] == 0
        and struct.unpack_from("<i", payload, 27)[0] == -1
        and payload[35] == 4
        and struct.unpack_from("<i", payload, 36)[0] == 1
        and payload[40] == 3
        and payload[53] in (0, 1)
        and struct.unpack_from("<i", payload, 54)[0] == -1
        and struct.unpack_from("<i", payload, 58)[0] == 0
        and struct.unpack_from("<i", payload, 62)[0] == -1
        and payload[66] == 0xFF
        and payload[67] == 4
        and struct.unpack_from("<i", payload, 72)[0] == -1
        and struct.unpack_from("<i", payload, 76)[0] == 0
        and struct.unpack_from("<i", payload, 80)[0] == -1
    ):
        return {}
    direction = struct.unpack_from("<i", payload, 31)[0]
    logic_id = struct.unpack_from("<Q", payload, 41)[0]
    slot_id = struct.unpack_from("<I", payload, 49)[0]
    hp_ratio = struct.unpack_from("<f", payload, 68)[0]
    if direction not in (0, 1, 2) or not math.isfinite(hp_ratio) or not 0 <= hp_ratio <= 1:
        return {}
    direction_name = ("Down", "Up", "UpAndDown")[direction]
    direction_phrase = ("falls", "rises", "crosses")[direction]
    return {
        "type": "LevelEvent_OnEntityHpChanged",
        "changedDirection": direction,
        "changedDirectionName": direction_name,
        "entityFilter": [{
            "logicId": logic_id,
            "slotId": slot_id,
            "useSlotId": bool(payload[53]),
        }],
        "hpRatio": round(hp_ratio, 6),
        "transport": "local-entity-hp-runtime-event",
        "serverExchange": False,
        "serializedMissionOrQuestId": False,
        "summary": (
            f"entity slot {slot_id} HP {direction_phrase} through "
            f"{round(hp_ratio * 100, 3):g}%"
        ),
        "payloadShape": "single-entity-hp-ratio-event",
    }
