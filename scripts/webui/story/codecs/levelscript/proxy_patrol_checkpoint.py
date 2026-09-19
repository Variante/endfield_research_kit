"""Exact current-build ProxyPatrolCheckpointReach event decoder."""

from __future__ import annotations

import re
import struct
from typing import Any

from .params import (
    decode_constant_string_param,
    decode_i32_param,
    decode_param_output,
)


EVENT_NAME = "LevelEvent_OnProxyPatrolCheckpointReach"
EVENT_SEMANTIC_KEY = (0x0084, 0x15)
_OUTPUT_FIELDS = ("npcEntity", "npcPosition", "patrolId", "pointIndex")


def _has_bounded_header_validate_param(payload: bytes) -> bool:
    """Validate the compact inherited ActionHeader prefix structurally."""
    if len(payload) < 31 or payload[17] != 0x04 or payload[18] not in (0, 1):
        return False
    id_ref, source, path_size = struct.unpack_from("<iii", payload, 19)
    return id_ref >= -1 and source >= -1 and path_size == -1


def _nullable_output(
    payload: bytes,
    cursor: int,
    field_name: str,
) -> tuple[dict[str, Any] | None, int] | None:
    if cursor >= len(payload):
        return None
    if payload[cursor] == 0xFF:
        return None, cursor + 1
    decoded = decode_param_output(payload, cursor)
    if decoded is None:
        return None
    detail, end = decoded
    path = detail.get("path")
    if (
        detail.get("paramSource") != 0
        or not isinstance(path, str)
        or re.fullmatch(rf"\$\d+@_{re.escape(field_name)}", path) is None
    ):
        return None
    return detail, end


def decode_proxy_patrol_checkpoint_event(
    payload: bytes,
    semantic_key: tuple[int, int],
    *,
    header_role: bool,
) -> dict[str, Any]:
    """Decode constant patrol/checkpoint/proxy filters and four outputs.

    The physical next-UID window may include a following ActionMap container
    when this is the final header.  Member 20 is the final subtype member, so
    its complete constant ``Param<string>`` tail is the exact subtype boundary.
    """
    if (
        not header_role
        or semantic_key != EVENT_SEMANTIC_KEY
        or not _has_bounded_header_validate_param(payload)
    ):
        return {}

    patrol = decode_i32_param(payload, 31)
    if patrol is None:
        return {}
    patrol_detail, cursor = patrol
    point = decode_i32_param(payload, cursor)
    if point is None:
        return {}
    point_detail, cursor = point
    for detail in (patrol_detail, point_detail):
        if not (
            detail.get("idRef") == -1
            and detail.get("paramSource") == 0
            and detail.get("path") is None
        ):
            return {}

    outputs: dict[str, dict[str, Any] | None] = {}
    for field_name in _OUTPUT_FIELDS:
        decoded = _nullable_output(payload, cursor, field_name)
        if decoded is None:
            return {}
        outputs[field_name], cursor = decoded

    proxy = decode_constant_string_param(payload, cursor)
    if proxy is None:
        return {}
    proxy_id, cursor = proxy
    if not proxy_id or not re.fullmatch(r"[A-Za-z0-9_]+", proxy_id):
        return {}

    return {
        "patrolIdFilter": patrol_detail["value"],
        "pointIndexFilter": point_detail["value"],
        "npcEntityOutputParam": outputs["npcEntity"],
        "npcPositionOutputParam": outputs["npcPosition"],
        "patrolIdOutputParam": outputs["patrolId"],
        "pointIndexOutputParam": outputs["pointIndex"],
        "proxyIdFilter": proxy_id,
        "subtypeConsumedBytes": cursor,
        "trailingContainerBytes": len(payload) - cursor,
        "payloadShape": (
            "constant-proxy-patrol-checkpoint-and-outputs-exact-eof"
            if cursor == len(payload)
            else "constant-proxy-patrol-checkpoint-and-outputs-exact-prefix"
        ),
    }
