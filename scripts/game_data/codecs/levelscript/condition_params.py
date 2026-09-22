"""Param readers shared by the task-condition and action codecs.

Moved verbatim out of ``scripts/game_data/levelscript_binary.py``.
"""

from __future__ import annotations

import math
import re
import struct

from scripts.game_data.codecs.levelscript import params as levelscript_params
from scripts.game_data.codecs.levelscript.framing_common import _round_float
from scripts.game_data.codecs.levelscript.params import decode_param_tail as _decode_param_tail
from typing import Any

def _decode_levelscript_ptr_param(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode the shared exact ``Param<LevelScriptPtr>`` representation."""
    return levelscript_params.decode_levelscript_ptr_param(payload, cursor)


def _decode_levelscript_task_ptr_param(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode the current ``Param<LevelScriptTaskPtr>`` key shape."""
    if cursor + 2 > len(payload) or payload[cursor] != 0x04:
        return None
    pointer_mode = payload[cursor + 1]
    if pointer_mode not in (0, 1):
        return None
    decoded_key = _decode_nullable_string_value(payload, cursor + 2)
    if decoded_key is None:
        return None
    task_key = decoded_key[0]["value"]
    if task_key is not None and not re.fullmatch(r"[0-9a-f]{8}", task_key):
        return None
    tail = _decode_param_tail(payload, decoded_key[1])
    if tail is None:
        return None
    detail, end = tail
    return {
        "pointerMode": pointer_mode,
        "taskKey": task_key,
        **detail,
    }, end


def _decode_string_param(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode an authored ``Param<string>`` including a null constant value."""
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


def _decode_nullable_string_value(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode a raw MemoryPack nullable string without a ``Param`` tail."""
    if cursor + 4 > len(payload):
        return None
    size = struct.unpack_from("<i", payload, cursor)[0]
    cursor += 4
    if size == -1:
        return {"value": None}, cursor
    if size < 0 or size > 1024 or cursor + size > len(payload):
        return None
    try:
        value = payload[cursor : cursor + size].decode("utf-8")
    except UnicodeDecodeError:
        return None
    return {"value": value}, cursor + size


def _decode_u64_param(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode an authored eight-byte integer Param value."""
    if cursor + 9 > len(payload) or payload[cursor] != 0x04:
        return None
    value = struct.unpack_from("<Q", payload, cursor + 1)[0]
    tail = _decode_param_tail(payload, cursor + 9)
    if tail is None:
        return None
    detail, end = tail
    return {"value": str(value), **detail}, end


def _decode_entity_ptr_list_param(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode the current constant ``Param<List<ScriptEntityPtr>>`` shape."""
    if cursor + 5 > len(payload) or payload[cursor] != 0x04:
        return None
    count = struct.unpack_from("<i", payload, cursor + 1)[0]
    cursor += 5
    if count == -1:
        values = None
    elif 0 <= count <= 1024:
        values = []
        for _ in range(count):
            if cursor + 14 > len(payload) or payload[cursor] != 0x03:
                return None
            logic_id = struct.unpack_from("<Q", payload, cursor + 1)[0]
            slot_id = struct.unpack_from("<I", payload, cursor + 9)[0]
            use_slot_id = payload[cursor + 13]
            if use_slot_id not in (0, 1):
                return None
            values.append({
                "logicId": str(logic_id),
                "slotId": slot_id,
                "useSlotId": bool(use_slot_id),
            })
            cursor += 14
    else:
        return None
    tail = _decode_param_tail(payload, cursor)
    if tail is None:
        return None
    detail, end = tail
    return {"values": values, **detail}, end


def _decode_string_collection_param(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode the shared constant ``Param<collection<string>>`` wire shape."""
    if cursor + 5 > len(payload) or payload[cursor] != 0x04:
        return None
    count = struct.unpack_from("<i", payload, cursor + 1)[0]
    cursor += 5
    if count == -1:
        values = None
    elif 0 <= count <= 1024:
        values = []
        for _ in range(count):
            decoded = _decode_nullable_string_value(payload, cursor)
            if decoded is None:
                return None
            value, cursor = decoded
            values.append(value.get("value"))
    else:
        return None
    tail = _decode_param_tail(payload, cursor)
    if tail is None:
        return None
    detail, end = tail
    return {"values": values, **detail}, end


def _decode_u32_collection_param(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode the generated constant ``Param<List<uint>>`` wire shape."""
    if cursor + 5 > len(payload) or payload[cursor] != 0x04:
        return None
    count = struct.unpack_from("<i", payload, cursor + 1)[0]
    cursor += 5
    if count == -1:
        values = None
    elif 0 <= count <= 1024 and cursor + count * 4 <= len(payload):
        values = list(struct.unpack_from(f"<{count}I", payload, cursor))
        cursor += count * 4
    else:
        return None
    tail = _decode_param_tail(payload, cursor)
    if tail is None:
        return None
    detail, end = tail
    return {"values": values, **detail}, end


def _getter_subtype_payload(
    data: bytes,
    record: dict[str, Any],
    next_start: int | None,
) -> bytes:
    """Return subtype fields after the current PureGetter base shell."""
    start = int(record.get("start") or 0)
    prefix_size = 28 if record.get("layout") == "fa" else 26
    end = next_start if isinstance(next_start, int) else len(data)
    if start < 0 or end <= start + prefix_size or end > len(data):
        return b""
    return data[start + prefix_size : end]


def _decode_vector3_param(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode one authored ``Param<Vector3>`` and its binding tail."""
    if cursor + 13 > len(payload) or payload[cursor] != 0x04:
        return None
    raw = struct.unpack_from("<fff", payload, cursor + 1)
    if not all(math.isfinite(value) for value in raw):
        return None
    tail = _decode_audio_param_tail(payload, cursor + 13)
    if tail is None:
        return None
    detail, end = tail
    return {
        "value": {
            "x": _round_float(raw[0]),
            "y": _round_float(raw[1]),
            "z": _round_float(raw[2]),
        },
        **detail,
    }, end


def _decode_quaternion_param(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode one authored ``Param<Quaternion>`` and its binding tail."""
    if cursor + 17 > len(payload) or payload[cursor] != 0x04:
        return None
    raw = struct.unpack_from("<ffff", payload, cursor + 1)
    if not all(math.isfinite(value) for value in raw):
        return None
    tail = _decode_audio_param_tail(payload, cursor + 17)
    if tail is None:
        return None
    detail, end = tail
    return {
        "value": {
            "x": _round_float(raw[0]),
            "y": _round_float(raw[1]),
            "z": _round_float(raw[2]),
            "w": _round_float(raw[3]),
        },
        **detail,
    }, end


def _decode_audio_param_tail(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode the audio-action Param tail, including getter source ``-1``."""
    if cursor + 12 > len(payload):
        return None
    id_ref, param_source, path_size = struct.unpack_from("<iii", payload, cursor)
    cursor += 12
    if id_ref < -1 or param_source < -1 or param_source > 0x10000:
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
