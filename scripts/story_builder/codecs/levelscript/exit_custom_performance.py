"""Exact ExitLevelCustomPerformance action payload decoder."""

from __future__ import annotations

import struct
from typing import Any


ACTION_SEMANTIC_KEY = (0x00B9, 0x09)


def decode_exit_level_custom_performance_action(
    payload: bytes,
    semantic_key: tuple[int, int],
) -> dict[str, Any]:
    """Decode the action's sole authored ``Param<uint>`` handle."""
    if (
        semantic_key != ACTION_SEMANTIC_KEY
        or len(payload) != 17
        or payload[0] != 0x04
        or payload[5:17] != b"\xff" * 12
    ):
        return {}
    return {
        "payloadShape": "uint-handle-with-unset-param-tail-exact-eof",
        "handle": {
            "serializedConstValue": struct.unpack_from("<I", payload, 1)[0],
            "idRef": -1,
            "paramSource": -1,
            "path": None,
        },
        "consumedBytes": len(payload),
    }
