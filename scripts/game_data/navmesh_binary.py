"""Exact MemoryPack readers for current JsonData NavMesh payloads."""

from __future__ import annotations

import math
import struct
from typing import Any, Callable

MAX_COUNT = 1_000_000


class NavMeshDecodeError(ValueError):
    """Raised when a NavMesh payload changes shape or fails exact framing."""


def _need(data: bytes, offset: int, size: int, field: str) -> None:
    if offset < 0 or size < 0 or offset + size > len(data):
        raise NavMeshDecodeError(f"{field}: truncated at {offset}")


def _i32(data: bytes, offset: int, field: str) -> tuple[int, int]:
    _need(data, offset, 4, field)
    return struct.unpack_from("<i", data, offset)[0], offset + 4


def _u32(data: bytes, offset: int, field: str) -> tuple[int, int]:
    _need(data, offset, 4, field)
    return struct.unpack_from("<I", data, offset)[0], offset + 4


def _u64(data: bytes, offset: int, field: str) -> tuple[int, int]:
    _need(data, offset, 8, field)
    return struct.unpack_from("<Q", data, offset)[0], offset + 8


def _f32(data: bytes, offset: int, field: str) -> tuple[float, int]:
    _need(data, offset, 4, field)
    value = struct.unpack_from("<f", data, offset)[0]
    if not math.isfinite(value):
        raise NavMeshDecodeError(f"{field}: non-finite float")
    return value, offset + 4


def _count(data: bytes, offset: int, field: str) -> tuple[int | None, int]:
    value, offset = _i32(data, offset, field)
    if value == -1:
        return None, offset
    if value < 0 or value > MAX_COUNT:
        raise NavMeshDecodeError(f"{field}: invalid count {value}")
    return value, offset


def _vector3(data: bytes, offset: int, field: str) -> tuple[list[float], int]:
    values = []
    for axis in "xyz":
        value, offset = _f32(data, offset, f"{field}.{axis}")
        values.append(value)
    return values, offset


def decode_luna_area(data: bytes) -> dict[str, Any]:
    if not data or data[0] != 1:
        raise NavMeshDecodeError("LunaNavMeshAreaContainer member count changed")
    count, offset = _count(data, 1, "areas.count")
    rows = None
    if count is not None:
        rows = []
        for index in range(count):
            if offset >= len(data) or data[offset] != 6:
                raise NavMeshDecodeError(f"areas[{index}]: member count changed")
            offset += 1
            area, offset = _i32(data, offset, f"areas[{index}].area")
            g_max, offset = _f32(data, offset, f"areas[{index}].gMax")
            g_min, offset = _f32(data, offset, f"areas[{index}].gMin")
            vertex_count, offset = _count(data, offset, f"areas[{index}].gVerts.count")
            vertices = None
            if vertex_count is not None:
                vertices = []
                for vertex_index in range(vertex_count):
                    vertex, offset = _vector3(data, offset, f"areas[{index}].gVerts[{vertex_index}]")
                    vertices.append(vertex)
            luna_id, offset = _u64(data, offset, f"areas[{index}].lunaId")
            modify_type, offset = _i32(data, offset, f"areas[{index}].modifyType")
            rows.append({"area": area, "gMax": g_max, "gMin": g_min, "gVerts": vertices,
                         "lunaId": str(luna_id), "modifyType": modify_type})
    if offset != len(data):
        raise NavMeshDecodeError(f"LunaArea trailing bytes: {len(data) - offset}")
    return {"status": "exact_current_schema", "schemaStatus": "exact",
            "bytesConsumed": offset, "areaCount": count, "areas": rows}


def _dictionary(data: bytes, offset: int, field: str,
                read_key: Callable[[bytes, int, str], tuple[Any, int]],
                read_value: Callable[[bytes, int, str], tuple[Any, int]]) -> tuple[list[dict[str, Any]] | None, int]:
    count, offset = _count(data, offset, f"{field}.count")
    if count is None:
        return None, offset
    rows = []
    for index in range(count):
        key, offset = read_key(data, offset, f"{field}[{index}].key")
        value, offset = read_value(data, offset, f"{field}[{index}].value")
        rows.append({"key": str(key), "value": value})
    return rows, offset


def _vector3_array(data: bytes, offset: int, field: str) -> tuple[list[list[float]] | None, int]:
    count, offset = _count(data, offset, f"{field}.count")
    if count is None:
        return None, offset
    values = []
    for index in range(count):
        value, offset = _vector3(data, offset, f"{field}[{index}]")
        values.append(value)
    return values, offset


def _u64_list(data: bytes, offset: int, field: str) -> tuple[list[str] | None, int]:
    count, offset = _count(data, offset, f"{field}.count")
    if count is None:
        return None, offset
    values = []
    for index in range(count):
        value, offset = _u64(data, offset, f"{field}[{index}]")
        values.append(str(value))
    return values, offset


def _u32_set(data: bytes, offset: int, field: str) -> tuple[list[int] | None, int]:
    count, offset = _count(data, offset, f"{field}.count")
    if count is None:
        return None, offset
    values = []
    for index in range(count):
        value, offset = _u32(data, offset, f"{field}[{index}]")
        values.append(value)
    return values, offset


def _scene_state_buckets(data: bytes, offset: int, field: str) -> tuple[list[str], int]:
    values = []
    for index in range(8):
        value, offset = _u64(data, offset, f"{field}.bucket{index}")
        values.append(str(value))
    return values, offset


def _wrapped_scene_state_buckets(data: bytes, offset: int, field: str) -> tuple[list[str], int]:
    _need(data, offset, 1, field)
    if data[offset] != 8:
        raise NavMeshDecodeError(f"{field}: member count changed: {data[offset]}")
    return _scene_state_buckets(data, offset + 1, field)


def _scene_state_bucket_set(data: bytes, offset: int, field: str) -> tuple[list[list[str]] | None, int]:
    count, offset = _count(data, offset, f"{field}.count")
    if count is None:
        return None, offset
    values = []
    for index in range(count):
        value, offset = _wrapped_scene_state_buckets(data, offset, f"{field}[{index}]")
        values.append(value)
    return values, offset


def _i32_u64_list_map(data: bytes, offset: int, field: str) -> tuple[list[dict[str, Any]] | None, int]:
    return _dictionary(data, offset, field, _i32, _u64_list)


def _u64_nested_map(data: bytes, offset: int, field: str) -> tuple[list[dict[str, Any]] | None, int]:
    return _dictionary(data, offset, field, _u64, _i32_u64_list_map)


def _u64_vector3_map(data: bytes, offset: int, field: str) -> tuple[list[dict[str, Any]] | None, int]:
    return _dictionary(data, offset, field, _u64, _vector3_array)


def _u64_u32_padded(data: bytes, offset: int, field: str) -> tuple[int, int]:
    """A `uint` value in a `KeyValuePair<ulong,uint>`, with its tail padding.

    The pair is an unmanaged struct written as raw memory, so the four-byte
    value is followed by four bytes that align the next pair to the eight-byte
    key. This is the same layout proved on LevelScript's
    `Dictionary<ulong,int>`, and it is corroborated here from the other side:
    the sibling maps whose value is already eight-aligned need no padding and
    do decode.

    **This path is unexercised by the current corpus.** Both maps that use it,
    `surfTileIDToSceneStateMask` and `surfTileIDToSceneStateSet`, are empty in
    all twelve files, so no entry has ever been read. The padding is therefore
    applied by rule rather than by measurement, and it is required to be zero
    so that a build which populates these maps fails loudly if the rule does
    not hold rather than returning quietly shifted values.
    """

    value, offset = _u32(data, offset, field)
    _need(data, offset, 4, f"{field}.padding")
    if any(data[offset:offset + 4]):
        raise NavMeshDecodeError(f"{field}: non-zero pair padding at {offset}")
    return value, offset + 4


def _u64_u32_map(data: bytes, offset: int, field: str) -> tuple[list[dict[str, Any]] | None, int]:
    return _dictionary(data, offset, field, _u64, _u64_u32_padded)


def _u64_u32_set_map(data: bytes, offset: int, field: str) -> tuple[list[dict[str, Any]] | None, int]:
    return _dictionary(data, offset, field, _u64, _u32_set)


def _u64_bucket_map(data: bytes, offset: int, field: str) -> tuple[list[dict[str, Any]] | None, int]:
    return _dictionary(data, offset, field, _u64, _scene_state_buckets)


def _u64_bucket_set_map(data: bytes, offset: int, field: str) -> tuple[list[dict[str, Any]] | None, int]:
    return _dictionary(data, offset, field, _u64, _scene_state_bucket_set)


def decode_navmesh_state_container(data: bytes) -> dict[str, Any]:
    if not data or data[0] != 8:
        raise NavMeshDecodeError("NavMeshStateContainer member count changed")
    offset = 1
    readers = (
        ("cropBounds", _u64_vector3_map), ("factoryBounds", _u64_vector3_map),
        ("poiToSurfTileID", _u64_nested_map), ("strongholdToSurfTileID", _u64_nested_map),
        ("surfTileIDToSceneStateBucketsMask", _u64_bucket_map),
        ("surfTileIDToSceneStateBucketsSet", _u64_bucket_set_map),
        ("surfTileIDToSceneStateMask", _u64_u32_map),
        ("surfTileIDToSceneStateSet", _u64_u32_set_map),
    )
    fields: dict[str, Any] = {}
    counts: dict[str, int | None] = {}
    for field, reader in readers:
        value, offset = reader(data, offset, field)
        fields[field] = value
        counts[field] = None if value is None else len(value)
    if offset != len(data):
        raise NavMeshDecodeError(f"NavMeshStateContainer trailing bytes: {len(data) - offset}")
    return {"status": "exact_current_schema", "schemaStatus": "exact",
            "bytesConsumed": offset, "counts": counts, "fields": fields}
