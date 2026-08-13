"""Exact LevelScript manual-start/manual-end action payload decoder."""

from __future__ import annotations

import struct
from typing import Any


MANUAL_CONTROL_MAPPING_ID = "levelscript-actionbase-manual-control-opcodes-v1"
MANUAL_CONTROL_ACTIONS = {
    (0x0308, 0x0A): ("manual-start", "ManualStartLevelScript"),
    (0x0302, 0x0A): ("manual-end", "ManualEndLevelScript"),
}


def _drop_empty(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in row.items()
        if value not in (None, "", [], {})
    }


def _is_plausible_levelscript_id(value: int) -> bool:
    return 1_000_000 <= value <= 999_999_999_999


def decode_manual_levelscript_control(
    payload: bytes,
    semantic_key: tuple[int, int],
) -> dict[str, Any]:
    """Decode stable diagnostics for an exact manual-control action identity."""
    identity = MANUAL_CONTROL_ACTIONS.get(semantic_key)
    if identity is None or len(payload) < 46:
        return {}
    role, action = identity
    script_id_candidate: int | None = None
    if payload[17] == 0x04 and len(payload) >= 26:
        raw_script_id = struct.unpack_from("<Q", payload, 18)[0]
        if _is_plausible_levelscript_id(raw_script_id):
            script_id_candidate = raw_script_id
    marker_values: list[int] = []
    for offset in range(0, len(payload) - 3):
        value = struct.unpack_from("<I", payload, offset)[0]
        if 900 <= value <= 1100 and value not in marker_values:
            marker_values.append(value)
    canonical_prefix = (
        payload[0] == 0x04
        and payload[1:9] == b"\xff" * 8
        and payload[13:17] == b"\xff" * 4
        and payload[17] == 0x04
        and payload[18:34] == b"\x00" * 16
        and payload[34:38] == b"\xff" * 4
        and payload[42:46] == b"\xff" * 4
    )
    out = {
        "action": action,
        "role": role,
        "payloadShape": (
            "manual-levelscript-default-operands"
            if canonical_prefix
            else "manual-levelscript-unknown"
        ),
        "memberCountByte": payload[0],
        "markerU32s": marker_values,
        "hasLiteralLevelId": False,
        "hasLiteralScriptId": script_id_candidate is not None,
        "scriptIdCandidate": (
            str(script_id_candidate) if script_id_candidate is not None else ""
        ),
        "constantTargetStatus": (
            "script-id-only" if script_id_candidate is not None else "absent"
        ),
    }
    if canonical_prefix:
        # Current MemoryPack metadata establishes the two Param<T> operands as
        # levelId then scriptId. Their enum names remain contract-owned.
        out["parameterSources"] = {
            "levelId": struct.unpack_from("<i", payload, 9)[0],
            "scriptId": struct.unpack_from("<i", payload, 38)[0],
        }
    if script_id_candidate is not None:
        out["payloadShape"] = "manual-levelscript-script-id-operand"
    if len(payload) > 46 and canonical_prefix:
        out["trailingBytesAfterCanonicalPrefix"] = payload[46:].hex(" ")
    return _drop_empty(out)
