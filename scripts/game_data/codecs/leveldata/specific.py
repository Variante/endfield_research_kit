"""Exact current MemoryPack codec for LevelData's polymorphic specific data."""

from __future__ import annotations

from typing import Any, Callable

from .memorypack import read_count, read_f32, read_string, read_u64


def _vector3(data: bytes, offset: int) -> tuple[list[float], int] | None:
    values: list[float] = []
    for _ in range(3):
        decoded = read_f32(data, offset)
        if decoded is None:
            return None
        value, offset = decoded
        values.append(value)
    return values, offset


def _list(
    data: bytes,
    offset: int,
    reader: Callable[[bytes, int], tuple[Any, int] | None],
) -> tuple[dict[str, Any], int] | None:
    start = offset
    decoded = read_count(data, offset, max_count=100_000)
    if decoded is None:
        return None
    count, offset = decoded
    rows: list[Any] = []
    for _ in range(max(0, count)):
        item = reader(data, offset)
        if item is None:
            return None
        value, offset = item
        rows.append(value)
    return {
        "startOffset": start,
        "endOffset": offset,
        "count": count,
        "value": None if count == -1 else rows,
    }, offset


def _cabin_slot(data: bytes, offset: int) -> tuple[dict[str, Any], int] | None:
    start = offset
    if offset >= len(data) or data[offset] != 4:
        return None
    offset += 1
    bound_size = _vector3(data, offset)
    if bound_size is None:
        return None
    bound_size_value, offset = bound_size
    logic_id = read_u64(data, offset)
    if logic_id is None:
        return None
    logic_id_value, offset = logic_id
    position = _vector3(data, offset)
    if position is None:
        return None
    position_value, offset = position
    rotation = _vector3(data, offset)
    if rotation is None:
        return None
    rotation_value, offset = rotation
    return {
        "startOffset": start,
        "endOffset": offset,
        "memberCount": 4,
        "boundSize": bound_size_value,
        "logicId": str(logic_id_value),
        "position": position_value,
        "rotation": rotation_value,
    }, offset


def _u64(data: bytes, offset: int) -> tuple[str, int] | None:
    decoded = read_u64(data, offset)
    if decoded is None:
        return None
    value, offset = decoded
    return str(value), offset


def _vector_pair(data: bytes, offset: int) -> tuple[dict[str, Any], int] | None:
    position = _vector3(data, offset)
    if position is None:
        return None
    position_value, offset = position
    rotation = _vector3(data, offset)
    if rotation is None:
        return None
    rotation_value, offset = rotation
    return {"position": position_value, "rotation": rotation_value}, offset


def decode_level_specific_data(data: bytes, offset: int) -> dict[str, Any] | None:
    """Decode null or current tag-0 ``SpaceShipSpecificData`` exactly."""

    start = offset
    if offset >= len(data):
        return None
    tag = data[offset]
    offset += 1
    if tag == 0xFF:
        return {
            "startOffset": start,
            "endOffset": offset,
            "value": None,
            "unionTag": None,
        }
    if tag != 0 or offset >= len(data) or data[offset] != 8:
        return None
    offset += 1

    cabin_start = offset
    decoded = read_count(data, offset, max_count=100_000)
    if decoded is None:
        return None
    cabin_count, offset = decoded
    cabins: list[dict[str, Any]] = []
    cabin_keys: set[str] = set()
    for _ in range(max(0, cabin_count)):
        key_decoded = read_string(data, offset)
        if key_decoded is None:
            return None
        key, offset = key_decoded
        if key is None or key in cabin_keys:
            return None
        cabin_keys.add(key)
        value_decoded = _cabin_slot(data, offset)
        if value_decoded is None:
            return None
        value, offset = value_decoded
        cabins.append({"key": key, "value": value})

    grow_boxes = _list(data, offset, _u64)
    if grow_boxes is None:
        return None
    grow_box_value, offset = grow_boxes

    machines_start = offset
    decoded = read_count(data, offset, max_count=100_000)
    if decoded is None:
        return None
    machine_count, offset = decoded
    machines: list[dict[str, str]] = []
    machine_keys: set[str] = set()
    for _ in range(max(0, machine_count)):
        key_decoded = read_string(data, offset)
        if key_decoded is None:
            return None
        key, offset = key_decoded
        value_decoded = _u64(data, offset)
        if key is None or value_decoded is None or key in machine_keys:
            return None
        machine_keys.add(key)
        value, offset = value_decoded
        machines.append({"key": key, "value": value})

    showcase_root = _vector3(data, offset)
    if showcase_root is None:
        return None
    showcase_root_value, offset = showcase_root
    bind_list = _list(data, offset, _u64)
    if bind_list is None:
        return None
    bind_value, offset = bind_list
    local_positions = _list(data, offset, _vector_pair)
    if local_positions is None:
        return None
    local_position_value, offset = local_positions
    spawn_pos = _vector3(data, offset)
    if spawn_pos is None:
        return None
    spawn_pos_value, offset = spawn_pos
    spawn_rot = _vector3(data, offset)
    if spawn_rot is None:
        return None
    spawn_rot_value, offset = spawn_rot

    return {
        "startOffset": start,
        "endOffset": offset,
        "unionTag": 0,
        "specificDataType": "SpaceShipSpecificData",
        "memberCount": 8,
        "cabinSlotInfoLut": {
            "startOffset": cabin_start,
            "count": cabin_count,
            "value": None if cabin_count == -1 else cabins,
        },
        "growBoxSceneObjectId": grow_box_value,
        "manufacturingRoomMachine": {
            "startOffset": machines_start,
            "count": machine_count,
            "value": None if machine_count == -1 else machines,
        },
        "showcaseRootPos": showcase_root_value,
        "showcaseSlotBindAPList": bind_value,
        "showcaseSlotLocalPosInfoList": local_position_value,
        "spawnPos": spawn_pos_value,
        "spawnRot": spawn_rot_value,
        "evidenceBoundary": "exact current tag-0 generated SpaceShipSpecificData wrapper",
    }
