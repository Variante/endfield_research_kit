"""Exact current MemoryPack reader for teleport-validation tables."""

from __future__ import annotations

import math
import struct
from typing import Any


class TeleportValidationDecodeError(ValueError):
    """Raised when a teleport-validation table changes shape."""


def _need(data: bytes, offset: int, size: int, field: str) -> None:
    if offset < 0 or size < 0 or offset + size > len(data):
        raise TeleportValidationDecodeError(f"{field}: truncated")


def _i32(data: bytes, offset: int, field: str) -> tuple[int, int]:
    _need(data, offset, 4, field)
    return struct.unpack_from("<i", data, offset)[0], offset + 4


def _string(data: bytes, offset: int, field: str) -> tuple[str | None, int]:
    length, offset = _i32(data, offset, f"{field}.length")
    if length == -1:
        return None, offset
    if length < 0 or length > 4096:
        raise TeleportValidationDecodeError(f"{field}: invalid length {length}")
    _need(data, offset, length, field)
    try:
        value = data[offset : offset + length].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TeleportValidationDecodeError(f"{field}: invalid UTF-8") from exc
    return value, offset + length


def decode_teleport_validation_table(data: bytes) -> dict[str, Any]:
    if not data or data[0] != 1:
        raise TeleportValidationDecodeError("table member count changed")
    count, offset = _i32(data, 1, "teleportValidationDatas.count")
    if count < 0 or count > 100_000:
        raise TeleportValidationDecodeError(f"invalid row count {count}")
    rows = []
    seen: set[str] = set()
    for index in range(count):
        key, offset = _string(data, offset, f"rows[{index}].key")
        if not key or key in seen:
            raise TeleportValidationDecodeError(f"rows[{index}]: invalid or duplicate key")
        seen.add(key)
        _need(data, offset, 1, f"rows[{index}].memberCount")
        if data[offset] != 10:
            raise TeleportValidationDecodeError(f"rows[{index}]: member count changed")
        offset += 1
        _need(data, offset, 4, f"rows[{index}].deviation")
        deviation = struct.unpack_from("<f", data, offset)[0]
        offset += 4
        if not math.isfinite(deviation):
            raise TeleportValidationDecodeError(f"rows[{index}].deviation: non-finite")
        row_id, offset = _string(data, offset, f"rows[{index}].id")
        _need(data, offset, 2, f"rows[{index}].flags")
        if data[offset] not in (0, 1) or data[offset + 1] not in (0, 1):
            raise TeleportValidationDecodeError(f"rows[{index}]: invalid bool")
        keep_anim, keep_cam = bool(data[offset]), bool(data[offset + 1])
        offset += 2
        _need(data, offset, 24, f"rows[{index}].transforms")
        position = list(struct.unpack_from("<3f", data, offset))
        rotation = list(struct.unpack_from("<3f", data, offset + 12))
        if not all(math.isfinite(value) for value in (*position, *rotation)):
            raise TeleportValidationDecodeError(f"rows[{index}]: non-finite transform")
        offset += 24
        scene_id, offset = _string(data, offset, f"rows[{index}].sceneId")
        _need(data, offset, 16, f"rows[{index}].tail")
        sub_data_parent_id = struct.unpack_from("<Q", data, offset)[0]
        teleport_reason, ui_type_out = struct.unpack_from("<ii", data, offset + 8)
        offset += 16
        rows.append({
            "key": key, "deviation": deviation, "id": row_id,
            "keepAnim": keep_anim, "keepCam": keep_cam,
            "position": position, "rotationEuler": rotation, "sceneId": scene_id,
            "subDataParentId": str(sub_data_parent_id),
            "teleportReason": teleport_reason, "uiTypeOut": ui_type_out,
        })
    if offset != len(data):
        raise TeleportValidationDecodeError(f"trailing bytes: {len(data) - offset}")
    return {"status": "exact_current_schema", "schemaStatus": "exact",
            "bytesConsumed": offset, "rowCount": count, "rows": rows}
