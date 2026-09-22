"""Exact codec for LevelScript script-pointer reference payloads.

Moved verbatim out of ``scripts/game_data/levelscript_binary.py``.
"""

from __future__ import annotations

import struct

from scripts.game_data.codecs.levelscript.framing_common import SCRIPT_POINTER_REF_RECORDS
from scripts.game_data.codecs.levelscript.framing_common import _drop_empty
from scripts.game_data.codecs.levelscript.framing_common import _is_plausible_levelscript_id
from typing import Any

def decode_script_pointer_payload(
    data: bytes,
    record: dict[str, Any] | None,
    *,
    target_offset: int | None = None,
) -> dict[str, Any]:
    """Decode the compact script-pointer payload found in LevelScript records.

    This decodes bytes only. The flag byte is not yet mapped to start/end
    semantics, so callers must keep it diagnostic.
    """
    if not data or not record:
        return {}
    code = record.get("code")
    kind = record.get("kind")
    if not isinstance(code, int) or not isinstance(kind, int):
        return {}
    if (code, kind) not in SCRIPT_POINTER_REF_RECORDS:
        return {}
    payload_start = int(record.get("payloadStart", record.get("start", 0)) or 0)
    if payload_start < 0 or payload_start + 9 > len(data):
        return {}
    if data[payload_start] != 0x04:
        return {}

    pointer_script = struct.unpack_from("<Q", data, payload_start + 1)[0]
    if not _is_plausible_levelscript_id(pointer_script):
        return {}
    pointer_offset = payload_start + 1
    flag_offset: int | None = None
    pointer_flag: int | None = None
    if payload_start + 23 <= len(data) and data[payload_start + 21] == 0x04:
        raw_flag = data[payload_start + 22]
        if raw_flag in (0, 1):
            pointer_flag = raw_flag
            flag_offset = payload_start + 22

    sentinel_shape = False
    if payload_start + 35 <= len(data):
        sentinel_shape = (
            data[payload_start + 9 : payload_start + 21]
            == b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"
            and data[payload_start + 23 : payload_start + 35]
            == b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"
        )

    return _drop_empty(
        {
            "pointerScript": str(pointer_script),
            "pointerScriptOffset": pointer_offset,
            "pointerPayloadStart": payload_start,
            "pointerTargetMatches": (
                target_offset is None or int(target_offset) == pointer_offset
            ),
            "pointerFlag": pointer_flag,
            "pointerFlagOffset": flag_offset,
            "pointerPayloadShape": (
                "tagged-u64+tagged-flag+sentinels"
                if sentinel_shape and pointer_flag is not None
                else "tagged-u64"
            ),
        }
    )
