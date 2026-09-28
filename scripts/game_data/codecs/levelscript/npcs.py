"""Sequential current LevelScript NPC dictionary over shared NPC proxy rows."""

from __future__ import annotations

import struct
from typing import Any

from scripts.game_data.codecs.leveldata.npc_runtime import (
    LevelNpcCodecError,
    decode_npc_runtime_proxy_at,
)


class LevelScriptNpcCodecError(ValueError):
    """Malformed dictionary framing before a named NPC row."""


_MAX_NPCS = 100_000


def decode_npc_dictionary(
    data: bytes, offset: int
) -> tuple[dict[str, Any] | None, int]:
    """Advance a uint-keyed NPC dictionary or stop at unsupported row data.

    A row failure leaves the dictionary unread. No later byte is assigned to a
    field until every entry has advanced with the shared 118-member reader.
    """
    if offset < 0 or offset + 4 > len(data):
        raise LevelScriptNpcCodecError(f"truncated npcs count: offset={offset}")
    count = struct.unpack_from("<i", data, offset)[0]
    if count == -1:
        return {
            "status": "null", "count": None, "entries": None,
            "startOffset": offset, "endOffset": offset + 4,
        }, offset + 4
    if count < 0 or count > _MAX_NPCS:
        raise LevelScriptNpcCodecError(
            f"invalid npcs count: offset={offset} value={count}"
        )
    cursor = offset + 4
    entries: list[dict[str, Any]] = []
    seen: set[int] = set()
    for index in range(count):
        if cursor + 4 > len(data):
            raise LevelScriptNpcCodecError(
                f"truncated npcs[{index}].key: offset={cursor}"
            )
        key = struct.unpack_from("<I", data, cursor)[0]
        cursor += 4
        if key in seen:
            raise LevelScriptNpcCodecError(f"duplicate npcs key: value={key}")
        seen.add(key)
        try:
            row, cursor = decode_npc_runtime_proxy_at(data, cursor, index)
        except LevelNpcCodecError:
            return None, offset
        entries.append({"key": key, "value": row})
    return {
        "status": "present", "count": count, "entries": entries,
        "startOffset": offset, "endOffset": cursor,
    }, cursor
