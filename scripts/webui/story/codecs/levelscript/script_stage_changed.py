"""Exact current-build ``OnScriptStageChanged`` event decoder."""

from __future__ import annotations

import struct
from typing import Any

from .script_event_scope import decode_script_event_header_scope


_EVENT_NAME = "ScriptEvent_OnScriptStageChanged"


def decode_script_stage_changed_fields(
    payload: bytes,
    native_header_name: str,
) -> dict[str, Any]:
    """Decode the exact inherited scope and stage filter/output prefix."""
    if native_header_name != _EVENT_NAME:
        return {}
    scope = decode_script_event_header_scope(payload)
    cursor = scope.pop("_subtypeOffset", None)
    if not scope or not isinstance(cursor, int) or cursor >= len(payload):
        return {}
    out = dict(scope)
    filter_offset = cursor
    if payload[cursor] == 0xFF:
        cursor += 1
        out["newStageFilterPresent"] = False
        out["newStageFilterOffset"] = f"0x{filter_offset:x}"
    elif payload[cursor] == 0x04 and cursor + 13 <= len(payload):
        cursor += 1
        stage_value = struct.unpack_from("<i", payload, cursor)[0]
        cursor += 4
        stage_id_ref = struct.unpack_from("<i", payload, cursor)[0]
        cursor += 4
        stage_source = struct.unpack_from("<i", payload, cursor)[0]
        cursor += 4
        if cursor + 4 > len(payload):
            return {}
        path_size = struct.unpack_from("<i", payload, cursor)[0]
        cursor += 4
        if path_size == -1:
            stage_path = None
        elif 0 <= path_size <= 512 and cursor + path_size <= len(payload):
            try:
                stage_path = payload[cursor : cursor + path_size].decode("utf-8")
            except UnicodeDecodeError:
                return {}
            cursor += path_size
        else:
            return {}
        out.update({
            "newStageFilterPresent": True,
            "newStageFilter": stage_value,
            "newStageFilterParam": {
                "constValue": stage_value,
                "idRef": stage_id_ref,
                "paramSource": stage_source,
                "path": stage_path,
            },
            "newStageFilterOffset": f"0x{filter_offset:x}",
        })
    else:
        return {}

    output_offset = cursor
    if cursor >= len(payload):
        return {}
    if payload[cursor] == 0xFF:
        cursor += 1
        out["newStageOutputPresent"] = False
    elif payload[cursor] == 0x02 and cursor + 9 <= len(payload):
        cursor += 1
        output_source = struct.unpack_from("<i", payload, cursor)[0]
        cursor += 4
        output_size = struct.unpack_from("<i", payload, cursor)[0]
        cursor += 4
        if output_size < 0 or output_size > 512 or cursor + output_size > len(payload):
            return {}
        try:
            output_path = payload[cursor : cursor + output_size].decode("utf-8")
        except UnicodeDecodeError:
            return {}
        cursor += output_size
        out.update({
            "newStageOutputPresent": True,
            "newStageOutputParam": {
                "paramSource": output_source,
                "path": output_path,
            },
        })
    else:
        return {}
    out["newStageOutputOffset"] = f"0x{output_offset:x}"
    out["subtypeConsumedBytes"] = cursor - filter_offset
    return out
