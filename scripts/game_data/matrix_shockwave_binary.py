"""Exact MemoryPack reader for MatrixShockWaveBeatConfigTable."""

from __future__ import annotations

import math
import struct
from typing import Any


class MatrixShockWaveDecodeError(ValueError):
    pass


def _need(data: bytes, offset: int, size: int, field: str) -> None:
    if offset + size > len(data):
        raise MatrixShockWaveDecodeError(f"{field}: truncated")


def _u32(data: bytes, offset: int, field: str) -> tuple[int, int]:
    _need(data, offset, 4, field)
    return struct.unpack_from("<I", data, offset)[0], offset + 4


def _i32(data: bytes, offset: int, field: str) -> tuple[int, int]:
    _need(data, offset, 4, field)
    return struct.unpack_from("<i", data, offset)[0], offset + 4


def _f32(data: bytes, offset: int, field: str) -> tuple[float, int]:
    _need(data, offset, 4, field)
    value = struct.unpack_from("<f", data, offset)[0]
    if not math.isfinite(value):
        raise MatrixShockWaveDecodeError(f"{field}: non-finite")
    return value, offset + 4


def _string(data: bytes, offset: int, field: str) -> tuple[str, int]:
    length, offset = _u32(data, offset, f"{field}.length")
    if length > 4096:
        raise MatrixShockWaveDecodeError(f"{field}: invalid length {length}")
    _need(data, offset, length, field)
    try:
        return data[offset:offset + length].decode("utf-8"), offset + length
    except UnicodeDecodeError as exc:
        raise MatrixShockWaveDecodeError(f"{field}: invalid UTF-8") from exc


def decode_matrix_shockwave_table(data: bytes) -> dict[str, Any]:
    if not data or data[0] != 2:
        raise MatrixShockWaveDecodeError("root member count is not 2")
    offset = 1
    # MatrixShockWaveBeatBasic is an unmanaged value type and is emitted raw in
    # declaration order, unlike the generated class wrappers below.
    basic: dict[str, Any] = {}
    basic["moveUpEase"], offset = _i32(data, offset, "basic.moveUpEase")
    basic["moveUpDuration"], offset = _f32(data, offset, "basic.moveUpDuration")
    basic["moveDownEase"], offset = _i32(data, offset, "basic.moveDownEase")
    basic["moveDownDuration"], offset = _f32(data, offset, "basic.moveDownDuration")
    basic["skillPreDelay"], offset = _f32(data, offset, "basic.skillPreDelay")
    count, offset = _u32(data, offset, "configDict.count")
    if count > 4096:
        raise MatrixShockWaveDecodeError(f"configDict: invalid count {count}")
    keys: list[str] = []
    bar_count = 0
    for row_index in range(count):
        key, offset = _string(data, offset, f"configDict[{row_index}].key")
        if key in keys:
            raise MatrixShockWaveDecodeError(f"configDict[{row_index}]: duplicate key")
        keys.append(key)
        if offset >= len(data) or data[offset] != 2:
            raise MatrixShockWaveDecodeError(f"configDict[{row_index}]: member count is not 2")
        offset += 1
        bars, offset = _u32(data, offset, f"configDict[{row_index}].barList.count")
        if bars > 4096:
            raise MatrixShockWaveDecodeError(f"configDict[{row_index}]: invalid bar count {bars}")
        bar_count += bars
        for bar_index in range(bars):
            if offset >= len(data) or data[offset] != 3:
                raise MatrixShockWaveDecodeError(
                    f"configDict[{row_index}].barList[{bar_index}]: member count is not 3"
                )
            offset += 1
            _, offset = _i32(data, offset, "bar.type")
            _, offset = _f32(data, offset, "bar.timestamp")
            _, offset = _f32(data, offset, "bar.moveSpeed")
        _, offset = _f32(data, offset, f"configDict[{row_index}].period")
    if offset != len(data):
        raise MatrixShockWaveDecodeError(f"trailing bytes: {len(data) - offset}")
    return {
        "status": "exact",
        "schemaStatus": "named_exact",
        "bytesConsumed": offset,
        "entryCount": count,
        "barCount": bar_count,
        "keys": keys,
        "basic": basic,
    }
