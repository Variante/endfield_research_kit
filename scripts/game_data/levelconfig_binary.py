"""Exact current-format reader for JsonData ``LevelConfig`` payloads."""

from __future__ import annotations

import math
import struct
from typing import Any


ROOT_MEMBER_COUNT = 18
STATE_MEMBER_COUNT = 3
MAX_STRING_BYTES = 4096
MAX_LIST_COUNT = 65536


class LevelConfigDecodeError(ValueError):
    """Raised when a LevelConfig payload changes shape or fails exact framing."""


def _require(data: bytes, offset: int, size: int, field: str) -> None:
    if offset < 0 or size < 0 or offset + size > len(data):
        raise LevelConfigDecodeError(f"{field}: truncated at {offset}")


def _read_i32(data: bytes, offset: int, field: str) -> tuple[int, int]:
    _require(data, offset, 4, field)
    return struct.unpack_from("<i", data, offset)[0], offset + 4


def _read_i64(data: bytes, offset: int, field: str) -> tuple[int, int]:
    _require(data, offset, 8, field)
    return struct.unpack_from("<q", data, offset)[0], offset + 8


def _read_bool(data: bytes, offset: int, field: str) -> tuple[bool, int]:
    _require(data, offset, 1, field)
    if data[offset] not in (0, 1):
        raise LevelConfigDecodeError(f"{field}: invalid bool {data[offset]}")
    return bool(data[offset]), offset + 1


def _read_string(data: bytes, offset: int, field: str) -> tuple[str | None, int]:
    length, offset = _read_i32(data, offset, f"{field}.length")
    if length == -1:
        return None, offset
    if length < 0 or length > MAX_STRING_BYTES:
        raise LevelConfigDecodeError(f"{field}: invalid length {length}")
    _require(data, offset, length, field)
    try:
        value = data[offset : offset + length].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LevelConfigDecodeError(f"{field}: invalid UTF-8") from exc
    return value, offset + length


def _read_count(data: bytes, offset: int, field: str) -> tuple[int | None, int]:
    count, offset = _read_i32(data, offset, field)
    if count == -1:
        return None, offset
    if count < 0 or count > MAX_LIST_COUNT:
        raise LevelConfigDecodeError(f"{field}: invalid count {count}")
    return count, offset


def _read_floats(data: bytes, offset: int, count: int, field: str) -> tuple[list[float], int]:
    size = count * 4
    _require(data, offset, size, field)
    values = list(struct.unpack_from(f"<{count}f", data, offset))
    if not all(math.isfinite(value) for value in values):
        raise LevelConfigDecodeError(f"{field}: non-finite component")
    return values, offset + size


def decode_level_config(data: bytes) -> dict[str, Any]:
    """Decode all 18 ordered members and require physical EOF."""
    if not data or data[0] != ROOT_MEMBER_COUNT:
        actual = data[0] if data else None
        raise LevelConfigDecodeError(
            f"LevelConfig member count mismatch: expected={ROOT_MEMBER_COUNT} actual={actual}"
        )
    offset = 1
    if offset >= len(data) or data[offset] != STATE_MEMBER_COUNT:
        actual = data[offset] if offset < len(data) else None
        raise LevelConfigDecodeError(
            f"defaultState member count mismatch: expected={STATE_MEMBER_COUNT} actual={actual}"
        )
    offset += 1
    exported_scene_config_path, offset = _read_string(
        data, offset, "defaultState.exportedSceneConfigPath"
    )
    state_name, offset = _read_string(data, offset, "defaultState.name")
    source_scene_name, offset = _read_string(data, offset, "defaultState.sourceSceneName")
    dimension_source_level_id, offset = _read_string(data, offset, "dimensionSourceLevelId")
    enable_snow, offset = _read_bool(data, offset, "enableFactoryBuildingSnowCoverage")
    level_id, offset = _read_string(data, offset, "id")
    if not level_id:
        raise LevelConfigDecodeError("id: empty or null")
    level_id_num, offset = _read_i32(data, offset, "idNum")
    is_dimension_level, offset = _read_bool(data, offset, "isDimensionLevel")
    is_seamless, offset = _read_bool(data, offset, "isSeamless")

    path_count, offset = _read_count(data, offset, "levelDataPaths.count")
    level_data_path_hashes: list[int] | None = None
    if path_count is not None:
        level_data_path_hashes = []
        for index in range(path_count):
            value, offset = _read_i64(data, offset, f"levelDataPaths[{index}]")
            level_data_path_hashes.append(value)

    grid_count, offset = _read_count(data, offset, "levelGrids.count")
    level_grids: list[list[int]] | None = None
    if grid_count is not None:
        level_grids = []
        for index in range(grid_count):
            x, offset = _read_i32(data, offset, f"levelGrids[{index}].x")
            y, offset = _read_i32(data, offset, f"levelGrids[{index}].y")
            level_grids.append([x, y])

    map_id, offset = _read_string(data, offset, "mapIdStr")
    player_init_pos, offset = _read_floats(data, offset, 3, "playerInitPos")
    player_init_rot, offset = _read_floats(data, offset, 3, "playerInitRot")
    rect_left_bottom, offset = _read_floats(data, offset, 2, "rectLeftBottom")
    rect_right_top, offset = _read_floats(data, offset, 2, "rectRightTop")
    scope, offset = _read_i32(data, offset, "scope")
    start_pos, offset = _read_floats(data, offset, 3, "startPos")
    water_start_audio, offset = _read_string(data, offset, "waterStartAudio")
    water_stop_audio, offset = _read_string(data, offset, "waterStopAudio")
    if offset != len(data):
        raise LevelConfigDecodeError(
            f"LevelConfig trailing bytes: cursor={offset} length={len(data)}"
        )
    return {
        "status": "exact_current_schema",
        "schemaStatus": "exact",
        "serializedMemberCount": ROOT_MEMBER_COUNT,
        "bytesConsumed": offset,
        "defaultState": {
            "exportedSceneConfigPath": exported_scene_config_path,
            "name": state_name,
            "sourceSceneName": source_scene_name,
        },
        "dimensionSourceLevelId": dimension_source_level_id,
        "enableFactoryBuildingSnowCoverage": enable_snow,
        "id": level_id,
        "idNum": level_id_num,
        "isDimensionLevel": is_dimension_level,
        "isSeamless": is_seamless,
        "levelDataPathHashes": level_data_path_hashes,
        "levelGrids": level_grids,
        "mapIdStr": map_id,
        "playerInitPos": player_init_pos,
        "playerInitRot": player_init_rot,
        "rectLeftBottom": rect_left_bottom,
        "rectRightTop": rect_right_top,
        "scope": scope,
        "startPos": start_pos,
        "waterStartAudio": water_start_audio,
        "waterStopAudio": water_stop_audio,
        "evidenceBoundary": (
            "Current wrapper member order and nested State order decode through physical EOF. "
            "StringPathHash values remain serialized int64 identities until joined to a path table."
        ),
    }
