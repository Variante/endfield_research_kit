"""Bounds-checked codec for authored LevelScript active shapes."""

from __future__ import annotations

import math
import struct
from typing import Any


SHAPE_TYPE_NAMES = {
    0: "None",
    1: "BOX",
    2: "SPHERE",
}

END_TYPE_NAMES = {
    0: "Auto",
    1: "ByExitStartShape",
    2: "Manual",
    3: "SameWithDeactive",
    4: "Never",
}


def _u32(data: bytes, offset: int) -> int | None:
    if offset < 0 or offset + 4 > len(data):
        return None
    return struct.unpack_from("<I", data, offset)[0]


def _f32(data: bytes, offset: int) -> float | None:
    if offset < 0 or offset + 4 > len(data):
        return None
    return struct.unpack_from("<f", data, offset)[0]


def _offset_hex(offset: int | None) -> str:
    return f"0x{offset:x}" if isinstance(offset, int) and offset >= 0 else ""


def _drop_empty(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if value not in (None, "", [], {})}


def _read_vector3(data: bytes, offset: int) -> tuple[dict[str, float] | None, int | None]:
    if offset < 0 or offset + 12 > len(data):
        return None, None
    return (
        {
            "x": round(_f32(data, offset), 3),
            "y": round(_f32(data, offset + 4), 3),
            "z": round(_f32(data, offset + 8), 3),
        },
        offset + 12,
    )


def _decode_shape(data: bytes, offset: int) -> tuple[dict[str, Any] | None, int | None]:
    """Decode the exact five-member ``Beyond.Gameplay.Core.LevelScriptShape``."""
    if offset < 0 or offset + 45 > len(data):
        return None, None
    member_count = data[offset]
    cursor = offset + 1
    euler_angles, cursor = _read_vector3(data, cursor)
    if cursor is None:
        return None, None
    shape_offset, cursor = _read_vector3(data, cursor)
    if cursor is None:
        return None, None
    radius = _f32(data, cursor)
    cursor += 4
    size, cursor = _read_vector3(data, cursor)
    if cursor is None:
        return None, None
    shape_type_raw = _u32(data, cursor)
    cursor += 4
    return (
        _drop_empty({
            "offset": _offset_hex(offset),
            "memberCount": member_count,
            "typeRaw": shape_type_raw,
            "type": SHAPE_TYPE_NAMES.get(
                shape_type_raw if shape_type_raw is not None else -1,
                "",
            ),
            "position": shape_offset,
            "eulerAngles": euler_angles,
            "size": size,
            "radius": round(radius, 3) if radius is not None else None,
        }),
        cursor,
    )


def decode_shape_list(
    data: bytes,
    offset: int,
    *,
    max_count: int = 64,
) -> tuple[dict[str, Any], int | None]:
    """Decode a nullable MemoryPack list of exact five-member shapes."""
    raw_count = _u32(data, offset)
    if raw_count is None:
        status, count = "missing", None
    elif raw_count == 0xFFFFFFFF:
        status, count = "null", None
    elif raw_count <= 64:
        status, count = "present", raw_count
    else:
        status, count = "unknown", raw_count
    cursor = offset + 4
    out: dict[str, Any] = {
        "offset": _offset_hex(offset),
        "status": status,
        "count": count,
    }
    if status != "present" or count is None or count == 0:
        out["endOffset"] = _offset_hex(cursor)
        return _drop_empty(out), cursor
    if count > max_count:
        out["parseStatus"] = "count-too-large"
        return _drop_empty(out), None

    shapes: list[dict[str, Any]] = []
    for _ in range(count):
        shape, cursor = _decode_shape(data, cursor)
        if shape is None or cursor is None:
            out["parseStatus"] = "truncated"
            out["shapes"] = shapes
            return _drop_empty(out), None
        shapes.append(shape)
    out["parseStatus"] = "decoded"
    out["shapes"] = shapes
    out["endOffset"] = _offset_hex(cursor)
    return _drop_empty(out), cursor


def _valid_active_shape(shape: dict[str, Any]) -> bool:
    if (
        shape.get("memberCount") != 5
        or shape.get("typeRaw") not in SHAPE_TYPE_NAMES
        or shape.get("typeRaw") == 0
    ):
        return False
    values: list[Any] = [shape.get("radius")]
    for field_name in ("position", "eulerAngles", "size"):
        field = shape.get(field_name)
        if not isinstance(field, dict) or set(field) != {"x", "y", "z"}:
            return False
        values.extend(field.values())
    return all(
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and abs(value) < 10_000_000
        for value in values
    )


def find_active_shape_candidates(
    data: bytes,
    search_start: int,
    search_end: int,
) -> list[dict[str, Any]]:
    """Find exact shape lists followed by the four generated scalar members."""
    lower = max(0, int(search_start))
    upper = min(len(data), max(lower, int(search_end)))
    candidates: list[dict[str, Any]] = []
    for offset in range(lower, upper):
        shape_list, cursor = decode_shape_list(data, offset)
        if (
            cursor is None
            or shape_list.get("status") != "present"
            or not isinstance(shape_list.get("count"), int)
            or int(shape_list["count"]) <= 0
            or shape_list.get("parseStatus") != "decoded"
            or not all(
                isinstance(shape, dict) and _valid_active_shape(shape)
                for shape in shape_list.get("shapes") or []
            )
            or len(shape_list.get("shapes") or []) != int(shape_list["count"])
            or cursor + 7 > upper
        ):
            continue
        scalar_flags = list(data[cursor : cursor + 3])
        end_type_raw = _u32(data, cursor + 3)
        if (
            any(value not in (0, 1) for value in scalar_flags)
            or end_type_raw not in END_TYPE_NAMES
        ):
            continue
        candidates.append({
            "offset": offset,
            "offsetHex": _offset_hex(offset),
            "endOffset": cursor,
            "endOffsetHex": _offset_hex(cursor),
            "shapeList": shape_list,
            "followingFields": {
                "allowStartOnTravelPole": bool(scalar_flags[0]),
                "allowTick": bool(scalar_flags[1]),
                "enablePreload": bool(scalar_flags[2]),
                "endTypeRaw": end_type_raw,
                "endTypeName": END_TYPE_NAMES[end_type_raw],
            },
        })
    return candidates
