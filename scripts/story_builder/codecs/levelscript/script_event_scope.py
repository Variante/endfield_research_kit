"""Exact current-build inherited ``ScriptEventHeader`` scope decoder."""

from __future__ import annotations

import struct
from typing import Any


def decode_script_event_header_scope(payload: bytes) -> dict[str, Any]:
    """Replay inherited validate, target-script, and trigger-target fields.

    Values in ``ActionHeader._validate`` are validation-node references, not
    script ids. Only the following ``ScriptEventHeader._targetScript`` can
    carry an explicit LevelScript id; it never establishes mission ownership.
    """
    cursor = 17

    def read_string() -> tuple[str | None, int] | None:
        nonlocal cursor
        if cursor + 4 > len(payload):
            return None
        size = struct.unpack_from("<i", payload, cursor)[0]
        cursor += 4
        if size == -1:
            return None, cursor
        if size < 0 or size > 512 or cursor + size > len(payload):
            return None
        raw = payload[cursor : cursor + size]
        cursor += size
        try:
            return raw.decode("utf-8"), cursor
        except UnicodeDecodeError:
            return None

    if cursor >= len(payload) or payload[cursor] != 0x04:
        return {}
    cursor += 1
    if cursor + 9 > len(payload) or payload[cursor] not in (0, 1):
        return {}
    validate_value = bool(payload[cursor])
    cursor += 1
    validate_id_ref = struct.unpack_from("<i", payload, cursor)[0]
    cursor += 4
    validate_source = struct.unpack_from("<i", payload, cursor)[0]
    cursor += 4
    validate_path_result = read_string()
    if validate_path_result is None:
        return {}
    validate_path = validate_path_result[0]

    target_script: dict[str, Any] | None = None
    if cursor >= len(payload):
        return {}
    if payload[cursor] == 0xFF:
        cursor += 1
    else:
        if payload[cursor] != 0x04:
            return {}
        cursor += 1
        if cursor >= len(payload) or payload[cursor] != 0x01:
            return {}
        cursor += 1
        if cursor + 16 > len(payload):
            return {}
        script_id = struct.unpack_from("<Q", payload, cursor)[0]
        cursor += 8
        target_id_ref = struct.unpack_from("<i", payload, cursor)[0]
        cursor += 4
        target_source = struct.unpack_from("<i", payload, cursor)[0]
        cursor += 4
        target_path_result = read_string()
        if target_path_result is None:
            return {}
        target_script = {
            "scriptId": script_id,
            "idRef": target_id_ref,
            "paramSource": target_source,
            "path": target_path_result[0],
        }

    if cursor + 4 > len(payload):
        return {}
    trigger_target = struct.unpack_from("<i", payload, cursor)[0]
    cursor += 4
    if trigger_target not in (0, 1):
        return {}

    out: dict[str, Any] = {
        "scriptEventScope": (
            "owning-level-script" if trigger_target == 0 else "specified-level-script"
        ),
        "triggerTarget": "SELF" if trigger_target == 0 else "SPECIFY_SCRIPT",
        "targetScriptPresent": target_script is not None,
        "validateParam": {
            "constValue": validate_value,
            "idRef": validate_id_ref,
            "paramSource": validate_source,
            "path": validate_path,
        },
        "_subtypeOffset": cursor,
    }
    if target_script is not None:
        out["targetScriptParam"] = target_script
        if (
            trigger_target == 1
            and target_script["scriptId"]
            and target_script["idRef"] == -1
            and target_script["paramSource"] == 0
            and not target_script["path"]
        ):
            out["specifiedTargetScriptId"] = target_script["scriptId"]
    return out
