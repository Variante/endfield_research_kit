"""Exact current MemoryPack reader for AetherEnergyLockConfigDataTable."""

from __future__ import annotations

import math
import struct
from collections import Counter
from typing import Any


class AetherEnergyLockDecodeError(ValueError):
    pass


NULL_COUNT = 0xFFFFFFFF


def _need(data: bytes, offset: int, size: int, field: str) -> None:
    if offset + size > len(data):
        raise AetherEnergyLockDecodeError(f"{field}: truncated")


def _count(data: bytes, offset: int, field: str, limit: int = 100_000) -> tuple[int | None, int]:
    _need(data, offset, 4, field)
    value = struct.unpack_from("<I", data, offset)[0]
    if value == NULL_COUNT:
        return None, offset + 4
    if value > limit:
        raise AetherEnergyLockDecodeError(f"{field}: invalid count {value}")
    return value, offset + 4


def _string(data: bytes, offset: int, field: str) -> tuple[str | None, int]:
    length, offset = _count(data, offset, f"{field}.length", 16_384)
    if length is None:
        return None, offset
    _need(data, offset, length, field)
    try:
        return data[offset:offset + length].decode("utf-8"), offset + length
    except UnicodeDecodeError as exc:
        raise AetherEnergyLockDecodeError(f"{field}: invalid UTF-8") from exc


def _f32(data: bytes, offset: int, field: str) -> tuple[float, int]:
    _need(data, offset, 4, field)
    value = struct.unpack_from("<f", data, offset)[0]
    if not math.isfinite(value):
        raise AetherEnergyLockDecodeError(f"{field}: non-finite")
    return value, offset + 4


def _fixed(data: bytes, offset: int, size: int, field: str) -> int:
    _need(data, offset, size, field)
    return offset + size


def _scalar_list(data: bytes, offset: int, field: str, width: int) -> tuple[int, int]:
    count, offset = _count(data, offset, f"{field}.count")
    if count is None:
        return 0, offset
    return count, _fixed(data, offset, count * width, field)


def decode_aether_energy_lock_table(data: bytes) -> dict[str, Any]:
    if not data or data[0] != 1:
        raise AetherEnergyLockDecodeError("root member count is not 1")
    config_count, offset = _count(data, 1, "configDataPlain.count", 4096)
    if config_count is None:
        raise AetherEnergyLockDecodeError("configDataPlain is null")
    env_total = vein_total = midpoint_total = interval_total = 0
    list_sizes: Counter[str] = Counter()
    for config_index in range(config_count):
        field = f"configDataPlain[{config_index}]"
        if offset >= len(data) or data[offset] != 8:
            raise AetherEnergyLockDecodeError(f"{field}: member count is not 8")
        offset += 1
        env_count, offset = _count(data, offset, f"{field}.envVFXConfigs.count", 4096)
        if env_count is None:
            env_count = 0
        env_total += env_count
        for env_index in range(env_count):
            item = f"{field}.envVFXConfigs[{env_index}]"
            if offset >= len(data) or data[offset] != 4:
                raise AetherEnergyLockDecodeError(f"{item}: member count is not 4")
            offset += 1
            offset = _fixed(data, offset, 12, f"{item}.localScale")
            _, offset = _string(data, offset, f"{item}.name")
            offset = _fixed(data, offset, 12, f"{item}.position")
            offset = _fixed(data, offset, 16, f"{item}.rotation")
        # The unmanaged identifier occupies 24 bytes in the current runtime:
        # u64 logicId, u64 parentScriptId, u32 slotId, then four padding bytes.
        offset = _fixed(data, offset, 24, f"{field}.identifier")
        offset = _fixed(data, offset, 8, f"{field}.subDataParentId")
        count, offset = _scalar_list(data, offset, f"{field}.veinAudioPointCountList", 4)
        list_sizes["audioPointCounts"] += count
        count, offset = _scalar_list(data, offset, f"{field}.veinAudioPointProgressList", 4)
        list_sizes["audioPointProgress"] += count
        vein_count, offset = _count(data, offset, f"{field}.veinConfigs.count", 4096)
        if vein_count is None:
            vein_count = 0
        vein_total += vein_count
        for vein_index in range(vein_count):
            item = f"{field}.veinConfigs[{vein_index}]"
            if offset >= len(data) or data[offset] != 6:
                raise AetherEnergyLockDecodeError(f"{item}: member count is not 6")
            offset += 1
            _, offset = _f32(data, offset, f"{item}.initProgress")
            interval_count, offset = _count(data, offset, f"{item}.intervalList.count", 4096)
            if interval_count is None:
                interval_count = 0
            interval_total += interval_count
            for interval_index in range(interval_count):
                interval = f"{item}.intervalList[{interval_index}]"
                if offset >= len(data) or data[offset] != 2:
                    raise AetherEnergyLockDecodeError(f"{interval}: member count is not 2")
                offset = _fixed(data, offset + 1, 8, interval)
            midpoint_count, offset = _count(data, offset, f"{item}.midPointConfigs.count", 4096)
            if midpoint_count is None:
                midpoint_count = 0
            midpoint_total += midpoint_count
            for midpoint_index in range(midpoint_count):
                midpoint = f"{item}.midPointConfigs[{midpoint_index}]"
                if offset >= len(data) or data[offset] != 2:
                    raise AetherEnergyLockDecodeError(f"{midpoint}: member count is not 2")
                offset = _fixed(data, offset + 1, 8, midpoint)
            offset = _fixed(data, offset, 12, f"{item}.premise/scannable/spline")
        count, offset = _scalar_list(data, offset, f"{field}.veinEffectPointCountList", 4)
        list_sizes["effectPointCounts"] += count
        count, offset = _scalar_list(data, offset, f"{field}.veinEffectPointList", 12)
        list_sizes["effectPoints"] += count
    if offset != len(data):
        raise AetherEnergyLockDecodeError(f"trailing bytes: {len(data) - offset}")
    return {
        "status": "exact",
        "schemaStatus": "named_exact",
        "bytesConsumed": offset,
        "entryCount": config_count,
        "envVfxCount": env_total,
        "veinCount": vein_total,
        "midpointCount": midpoint_total,
        "intervalCount": interval_total,
        "listElementCounts": dict(list_sizes),
    }
