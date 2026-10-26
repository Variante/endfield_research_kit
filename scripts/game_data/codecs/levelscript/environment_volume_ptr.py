"""Stored `Param<EnvironmentVolumePtr>` framing for LevelScript actions."""

from __future__ import annotations

import struct
from typing import Any

from scripts.game_data.codecs.levelscript.params import decode_pooled_param_tail


def decode_environment_volume_ptr_param(
    payload: bytes, cursor: int, *, strings: Any = None,
) -> tuple[dict[str, Any], int] | None:
    """Read a present four-member Param containing an unsigned 64-bit ID."""
    if cursor < 0 or cursor + 21 > len(payload) or payload[cursor] != 4:
        return None
    value = struct.unpack_from("<Q", payload, cursor + 1)[0]
    tail = decode_pooled_param_tail(payload, cursor + 9, strings=strings)
    if tail is None:
        return None
    detail, end = tail
    return {"value": {"id": value}, **detail}, end
