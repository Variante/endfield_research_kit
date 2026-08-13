"""Exact current-build ``LevelScriptTriggerVolumeData`` codec."""

from __future__ import annotations

import struct
from typing import Any


# ``LevelScriptTriggerVolumeData`` is a MemoryPack union. The current
# installed formatter assigns tag 1 to the no-extra-field Leader subtype; its
# payload then serializes the eight base members in generated setter order.
# Other subtype bodies stay rejected until their layouts are proven.
UNION_TAG_NAMES = {
    1: "Leader",
}
SCHEMA_MAPPING_ID = "current-global-metadata-levelscript-trigger-volume-data-fields"
BASE_FIELDS = [
    "isImportant",
    "waitSrvRes",
    "enterCheckOnGround",
    "triggerOnPole",
    "slotId",
    "triggerCountLimit",
    "exitShapeStartIndex",
    "shapeList",
]
SERIALIZED_FIELDS = [
    "enterCheckOnGround",
    "exitShapeStartIndex",
    "isImportant",
    "shapeList",
    "slotId",
    "triggerCountLimit",
    "triggerOnPole",
    "waitSrvRes",
]
SHAPE_TYPE_NAMES = {
    0: "None",
    1: "Box",
    2: "Sphere",
    3: "PolyLine",
    4: "Infinite",
}
WRAPPER_PROLOGUE = bytes.fromhex(
    "00 00 00 00 00 00 00 00 00 00 00 00 00 "
    "ff ff ff ff ea 03 00 00 ff ff ff ff "
    "01 00 00 00 00 00 00 00 00 00"
)


def _u32(data: bytes, offset: int) -> int | None:
    if offset < 0 or offset + 4 > len(data):
        return None
    return struct.unpack_from("<I", data, offset)[0]


def _i32(data: bytes, offset: int) -> int | None:
    if offset < 0 or offset + 4 > len(data):
        return None
    return struct.unpack_from("<i", data, offset)[0]


def _f32(data: bytes, offset: int) -> float | None:
    if offset < 0 or offset + 4 > len(data):
        return None
    return struct.unpack_from("<f", data, offset)[0]


def _list_status(raw_count: int | None) -> tuple[str, int | None]:
    if raw_count is None:
        return "missing", None
    if raw_count == 0xFFFFFFFF:
        return "null", None
    if raw_count <= 64:
        return "present", raw_count
    return "unknown", raw_count


def _drop_empty(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if value not in (None, "", [], {})}


def _offset_hex(offset: int | None) -> str:
    return f"0x{offset:x}" if isinstance(offset, int) and offset >= 0 else ""


def _read_vector2(data: bytes, offset: int) -> tuple[dict[str, float] | None, int | None]:
    if offset < 0 or offset + 8 > len(data):
        return None, None
    return (
        {
            "x": round(struct.unpack_from("<f", data, offset)[0], 3),
            "y": round(struct.unpack_from("<f", data, offset + 4)[0], 3),
        },
        offset + 8,
    )


def _read_vector3(data: bytes, offset: int) -> tuple[dict[str, float] | None, int | None]:
    if offset < 0 or offset + 12 > len(data):
        return None, None
    return (
        {
            "x": round(struct.unpack_from("<f", data, offset)[0], 3),
            "y": round(struct.unpack_from("<f", data, offset + 4)[0], 3),
            "z": round(struct.unpack_from("<f", data, offset + 8)[0], 3),
        },
        offset + 12,
    )


def _decode_vector2_list(
    data: bytes,
    offset: int,
    *,
    max_count: int = 128,
) -> tuple[dict[str, Any], int | None]:
    raw_count = _u32(data, offset)
    status, count = _list_status(raw_count)
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

    points: list[dict[str, float]] = []
    for _ in range(count):
        point, cursor = _read_vector2(data, cursor)
        if point is None or cursor is None:
            out["parseStatus"] = "truncated"
            out["points"] = points
            return _drop_empty(out), None
        points.append(point)
    out["parseStatus"] = "decoded"
    out["points"] = points
    out["endOffset"] = _offset_hex(cursor)
    return _drop_empty(out), cursor


def _decode_shape(data: bytes, offset: int) -> tuple[dict[str, Any] | None, int | None]:
    """Decode ``Beyond.Gameplay.LevelScriptTriggerVolumeShapeData``."""
    if offset < 0 or offset + 1 > len(data):
        return None, None
    member_count = data[offset]
    cursor = offset + 1
    poly_line_points, cursor = _decode_vector2_list(data, cursor)
    if cursor is None:
        return None, None
    position, cursor = _read_vector3(data, cursor)
    if position is None or cursor is None:
        return None, None
    radius = _f32(data, cursor)
    cursor += 4
    rotation, cursor = _read_vector3(data, cursor)
    if rotation is None or cursor is None:
        return None, None
    shape_type_raw = _u32(data, cursor)
    cursor += 4
    size, cursor = _read_vector3(data, cursor)
    if size is None or cursor is None:
        return None, None
    return (
        _drop_empty({
            "offset": _offset_hex(offset),
            "memberCount": member_count,
            "shapeTypeRaw": shape_type_raw,
            "shapeType": SHAPE_TYPE_NAMES.get(
                shape_type_raw if shape_type_raw is not None else -1,
                "",
            ),
            "position": position,
            "radius": round(radius, 3) if radius is not None else None,
            "rotation": rotation,
            "size": size,
            "polyLinePoints": poly_line_points,
        }),
        cursor,
    )


def _decode_shape_list(
    data: bytes,
    offset: int,
    *,
    max_count: int = 128,
) -> tuple[dict[str, Any], int | None]:
    raw_count = _u32(data, offset)
    status, count = _list_status(raw_count)
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


def _decode_entry(data: bytes, offset: int) -> tuple[dict[str, Any] | None, int | None]:
    """Decode one keyed ``LevelScriptTriggerVolumeData`` map entry."""
    if offset < 0 or offset + 6 > len(data):
        return None, None
    key_slot_id = _u32(data, offset)
    union_tag = data[offset + 4]
    member_count = data[offset + 5]
    if union_tag not in UNION_TAG_NAMES or member_count != 8:
        return None, None
    cursor = offset + 6
    if cursor + 6 > len(data):
        return None, None
    enter_check_on_ground = bool(data[cursor])
    cursor += 1
    exit_shape_start_index = _i32(data, cursor)
    cursor += 4
    is_important = bool(data[cursor])
    cursor += 1
    shape_list, cursor = _decode_shape_list(data, cursor)
    if cursor is None or cursor + 10 > len(data):
        return None, None
    slot_id = _u32(data, cursor)
    cursor += 4
    trigger_count_limit = _i32(data, cursor)
    cursor += 4
    trigger_on_pole = bool(data[cursor])
    cursor += 1
    wait_srv_res = bool(data[cursor])
    cursor += 1
    if (
        key_slot_id != slot_id
        or key_slot_id is None
        or not 80_000 <= key_slot_id <= 89_999
        or trigger_count_limit is None
        or trigger_count_limit < -1
    ):
        return None, None
    return (
        _drop_empty({
            "offset": _offset_hex(offset),
            "keySlotId": key_slot_id,
            "unionTag": union_tag,
            "triggerVolumeType": UNION_TAG_NAMES.get(union_tag, ""),
            "memberCount": member_count,
            "enterCheckOnGround": enter_check_on_ground,
            "exitShapeStartIndex": exit_shape_start_index,
            "isImportant": is_important,
            "shapeList": shape_list,
            "slotId": slot_id,
            "triggerCountLimit": trigger_count_limit,
            "triggerOnPole": trigger_on_pole,
            "waitSrvRes": wait_srv_res,
        }),
        cursor,
    )


def decode_trigger_volume_map(
    data: bytes,
    offset: int,
    *,
    max_count: int = 128,
) -> tuple[dict[str, Any], int | None]:
    """Decode the exact nullable trigger-volume map, including its wrapper."""
    raw_count = _u32(data, offset)
    status, count = _list_status(raw_count)
    cursor = offset + 4
    out: dict[str, Any] = {
        "offset": _offset_hex(offset),
        "status": status,
        "count": count,
    }
    wrapper_end = offset + 4 + len(WRAPPER_PROLOGUE)
    if (
        raw_count == 4
        and wrapper_end + 4 <= len(data)
        and data[offset + 4:wrapper_end] == WRAPPER_PROLOGUE
    ):
        inner, inner_cursor = decode_trigger_volume_map(
            data,
            wrapper_end,
            max_count=max_count,
        )
        if inner_cursor == len(data) and inner.get("status") == "present":
            wrapped = dict(inner)
            wrapped.update({
                "offset": _offset_hex(offset),
                "encoding": "wrapped-trigger-volume-map",
                "wrapperOffset": _offset_hex(offset),
                "wrapperBytes": 4 + len(WRAPPER_PROLOGUE),
                "wrapperOuterCount": raw_count,
                "wrapperPrologueBytes": len(WRAPPER_PROLOGUE),
                "innerMapOffset": _offset_hex(wrapper_end),
                "endOffset": _offset_hex(inner_cursor),
            })
            wrapped.setdefault("parseStatus", "decoded")
            return _drop_empty(wrapped), inner_cursor

    if status != "present" or count is None or count == 0:
        out["endOffset"] = _offset_hex(cursor)
        return _drop_empty(out), cursor
    if count > max_count:
        out["parseStatus"] = "count-too-large"
        return _drop_empty(out), None
    min_entry_bytes = 25
    minimum_bytes_required = count * min_entry_bytes
    remaining_bytes = max(0, len(data) - cursor)
    if minimum_bytes_required > remaining_bytes:
        out["parseStatus"] = "count-exceeds-remaining"
        out["remainingBytes"] = remaining_bytes
        out["minimumBytesRequired"] = minimum_bytes_required
        return _drop_empty(out), None

    volumes: list[dict[str, Any]] = []
    for _ in range(count):
        volume, cursor = _decode_entry(data, cursor)
        if volume is None or cursor is None:
            out["parseStatus"] = "truncated"
            out["volumes"] = volumes
            return _drop_empty(out), None
        volumes.append(volume)
    out["parseStatus"] = "decoded"
    out["slotIds"] = [row.get("slotId") for row in volumes if row.get("slotId") is not None]
    out["volumes"] = volumes
    out["endOffset"] = _offset_hex(cursor)
    return _drop_empty(out), cursor


def find_final_trigger_volume_map(
    data: bytes,
    *,
    search_start: int,
    max_scan_bytes: int = 1_048_576,
) -> tuple[int | None, dict[str, Any], int | None]:
    """Find the strict final trigger-volume dictionary after a task map.

    ``triggerVolumes`` is the final generated MemoryPack member of
    ``LevelScriptData``. The bounded scan accepts only an exact null/empty
    dictionary at EOF or a current-build Leader map whose decoded cursor lands
    at EOF. Entry decoding validates key/slot equality, subtype tag, member
    count, shape bodies, and field ranges.
    """
    if not data:
        return None, {}, None
    lower = max(0, int(search_start), len(data) - max_scan_bytes)
    for offset in range(len(data) - 4, lower - 1, -1):
        raw_count = _u32(data, offset)
        if raw_count is None or not 1 <= raw_count <= 128:
            continue
        decoded, cursor = decode_trigger_volume_map(data, offset)
        if (
            cursor == len(data)
            and decoded.get("status") == "present"
            and decoded.get("parseStatus") == "decoded"
            and len(decoded.get("volumes") or []) == raw_count
        ):
            return offset, decoded, cursor
    empty_offset = len(data) - 4
    if empty_offset >= lower:
        decoded, cursor = decode_trigger_volume_map(data, empty_offset)
        if (
            cursor == len(data)
            and decoded.get("status") in {"null", "present"}
            and not decoded.get("volumes")
            and decoded.get("count") in {None, 0}
        ):
            decoded["parseStatus"] = "decoded"
            return empty_offset, decoded, cursor
    return None, {}, None
