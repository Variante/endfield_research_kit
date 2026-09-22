"""Exact current codec for LevelData's nested level-wide configuration map."""

from __future__ import annotations

from typing import Any

from .function_area import LevelFunctionAreaCodecError, decode_condition_runtime
from .memorypack import read_count, read_i32, read_string, read_u64


def _lang_key(data: bytes, offset: int) -> tuple[dict[str, Any] | None, int] | None:
    start = offset
    if offset >= len(data):
        return None
    if data[offset] == 0xFF:
        return None, offset + 1
    if data[offset] != 1:
        return None
    offset += 1
    decoded = read_string(data, offset)
    if decoded is None:
        return None
    key, offset = decoded
    if key is None:
        return None
    return {"startOffset": start, "endOffset": offset, "key": key}, offset


def _dock_info(data: bytes, offset: int) -> tuple[dict[str, Any], int] | None:
    start = offset
    if offset >= len(data) or data[offset] != 4:
        return None
    offset += 1
    logic_id = read_u64(data, offset)
    if logic_id is None:
        return None
    logic_id_value, offset = logic_id
    dock_name = _lang_key(data, offset)
    if dock_name is None:
        return None
    dock_name_value, offset = dock_name
    if offset < len(data) and data[offset] == 0xFF:
        condition = None
        offset += 1
    else:
        try:
            condition, offset = decode_condition_runtime(data, offset, "filterCondition")
        except LevelFunctionAreaCodecError:
            return None
    node_index = read_i32(data, offset)
    if node_index is None:
        return None
    node_index_value, offset = node_index
    return {
        "startOffset": start,
        "endOffset": offset,
        "memberCount": 4,
        "bambooRaftDockLogicId": str(logic_id_value),
        "dockName": dock_name_value,
        "filterCondition": condition,
        "nodeIndex": node_index_value,
    }, offset


def _level_wide_value(data: bytes, offset: int) -> tuple[dict[str, Any], int] | None:
    start = offset
    if offset + 2 > len(data):
        return None
    tag = data[offset]
    member_count = data[offset + 1]
    offset += 2
    config_key = read_string(data, offset)
    if config_key is None:
        return None
    config_key_value, offset = config_key
    if tag == 0 and member_count == 2:
        dock_list_start = offset
        decoded = read_count(data, offset, max_count=100_000)
        if decoded is None:
            return None
        count, offset = decoded
        docks: list[dict[str, Any]] = []
        for _ in range(max(0, count)):
            dock = _dock_info(data, offset)
            if dock is None:
                return None
            value, offset = dock
            docks.append(value)
        return {
            "startOffset": start,
            "endOffset": offset,
            "unionTag": tag,
            "memberCount": member_count,
            "configType": "BambooRaftDockWideConfig",
            "configKey": config_key_value,
            "bambooRaftDockInfo": {
                "startOffset": dock_list_start,
                "endOffset": offset,
                "count": count,
                "value": None if count == -1 else docks,
            },
        }, offset
    if tag == 1 and member_count == 3:
        logic_id = read_u64(data, offset)
        if logic_id is None:
            return None
        logic_id_value, offset = logic_id
        spline_id = read_i32(data, offset)
        if spline_id is None:
            return None
        spline_id_value, offset = spline_id
        return {
            "startOffset": start,
            "endOffset": offset,
            "unionTag": tag,
            "memberCount": member_count,
            "configType": "BambooRaftWideConfig",
            "configKey": config_key_value,
            "bambooRaftLogicId": str(logic_id_value),
            "movingSplineId": spline_id_value,
        }, offset
    return None


def decode_level_wide_configs(data: bytes, offset: int) -> dict[str, Any] | None:
    """Decode ``Dictionary<LevelWideConfigType, Dictionary<string, LevelWideConfig>>``."""

    start = offset
    decoded = read_count(data, offset, max_count=100_000)
    if decoded is None:
        return None
    count, cursor = decoded
    rows: list[dict[str, Any]] = []
    outer_keys: set[int] = set()
    for _ in range(max(0, count)):
        key_decoded = read_i32(data, cursor)
        if key_decoded is None:
            return None
        key, cursor = key_decoded
        if key in outer_keys:
            return None
        outer_keys.add(key)
        inner_start = cursor
        inner_decoded = read_count(data, cursor, max_count=100_000)
        if inner_decoded is None:
            return None
        inner_count, cursor = inner_decoded
        values: list[dict[str, Any]] = []
        inner_keys: set[str] = set()
        for _ in range(max(0, inner_count)):
            string_decoded = read_string(data, cursor)
            if string_decoded is None:
                return None
            inner_key, cursor = string_decoded
            if inner_key is None or inner_key in inner_keys:
                return None
            inner_keys.add(inner_key)
            value_decoded = _level_wide_value(data, cursor)
            if value_decoded is None:
                return None
            value, cursor = value_decoded
            values.append({"key": inner_key, "value": value})
        rows.append({
            "keyRaw": key,
            "value": {
                "startOffset": inner_start,
                "endOffset": cursor,
                "count": inner_count,
                "value": None if inner_count == -1 else values,
            },
        })
    return {
        "startOffset": start,
        "endOffset": cursor,
        "count": count,
        "value": None if count == -1 else rows,
        "rows": rows,
        "evidenceBoundary": (
            "exact current nested dictionary with tag-0 BambooRaftDockWideConfig "
            "and tag-1 BambooRaftWideConfig generated wrappers"
        ),
    }
