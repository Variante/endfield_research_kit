"""Fail-closed readers for current Endfield ``SpawnerConfig`` MemoryPack data.

Only the final ``waveMap`` field is decoded here.  The current generated
formatters serialize ``SpawnerConfig`` as five fields with ``waveMap`` last,
``SpawnerWaveData`` as eleven fields, and ``SpawnerGroupData`` as twelve
fields.  Action maps in the middle of group rows remain opaque: the decoder
accepts a file only when one unique, complete wave/group parse reaches the
physical end of the file.
"""
from __future__ import annotations

import math
import struct
from functools import lru_cache
from typing import Any


NULL_COUNT = 0xFFFFFFFF
SPAWNER_CONFIG_MEMBER_COUNT = 5
SPAWNER_WAVE_MEMBER_COUNT = 11
SPAWNER_GROUP_MEMBER_COUNT = 12
MAX_WAVE_COUNT = 256
MAX_GROUP_COUNT = 1_024
MAX_STRING_BYTES = 256

SPAWNER_WAVE_SCHEMA_MAPPING_ID = (
    "gameassembly-2026-07-23-memorypack-spawner-wave-group-v2"
)
SPAWNER_WAVE_RUNTIME_MAPPING_ID = (
    "gameassembly-2026-07-23-cr-0x18b9217d0-spawner-wave-group-runtime-v2"
)


class SpawnerWaveDecodeError(ValueError):
    """Raised when a SpawnerConfig wave map is absent, changed, or ambiguous."""


def _read_string(data: bytes, offset: int) -> tuple[str | None, int]:
    if offset + 4 > len(data):
        raise SpawnerWaveDecodeError("truncated string length")
    length = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    if length == NULL_COUNT:
        return None, offset
    if length > MAX_STRING_BYTES or offset + length > len(data):
        raise SpawnerWaveDecodeError("invalid string length")
    try:
        value = data[offset:offset + length].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SpawnerWaveDecodeError("invalid UTF-8 string") from exc
    if any(ord(character) < 0x20 for character in value):
        raise SpawnerWaveDecodeError("control character in string")
    return value, offset + length


def _read_wave_tail(data: bytes, offset: int) -> tuple[dict[str, Any], int]:
    """Read fields after the opaque ``groupMap`` in one SpawnerWaveData row."""
    start = offset
    if offset + 11 > len(data):
        raise SpawnerWaveDecodeError("truncated wave tail")
    flags = data[offset:offset + 3]
    if any(value not in (0, 1) for value in flags):
        raise SpawnerWaveDecodeError("invalid wave bool")
    has_deadline, is_hidden, repeatable = (bool(value) for value in flags)
    offset += 3
    timestamp = struct.unpack_from("<f", data, offset)[0]
    offset += 4
    wave_id = struct.unpack_from("<i", data, offset)[0]
    offset += 4
    wave_key, offset = _read_string(data, offset)
    if offset + 8 > len(data):
        raise SpawnerWaveDecodeError("truncated wave mode")
    wave_mode, kill_count = struct.unpack_from("<ii", data, offset)
    offset += 8
    target_key, offset = _read_string(data, offset)

    if (
        not math.isfinite(timestamp)
        or not -100_000.0 <= timestamp <= 10_000_000.0
        or not 0 <= wave_id <= 1_000_000
        or not wave_key
        or wave_mode not in (0, 1, 2)
        or not 0 <= kill_count <= 1_000_000
    ):
        raise SpawnerWaveDecodeError("implausible wave tail")
    return {
        "tailOffset": start,
        "hasDeadlineBegin": has_deadline,
        "isHidden": is_hidden,
        "repeatable": repeatable,
        "timestamp": timestamp,
        "waveId": wave_id,
        "waveKey": wave_key,
        "waveMode": wave_mode,
        "waveModeKillCount": kill_count,
        "waveModeTargetKey": target_key or "",
    }, offset


def _read_group_tail(data: bytes, offset: int) -> tuple[dict[str, Any], int]:
    """Read fields after the opaque ``actionMap`` in one SpawnerGroupData row."""
    start = offset
    if offset + 12 > len(data):
        raise SpawnerWaveDecodeError("truncated group tail")
    deadline_begin_delta_time = struct.unpack_from("<f", data, offset)[0]
    backup_count, group_id = struct.unpack_from("<ii", data, offset + 4)
    offset += 12
    group_key, offset = _read_string(data, offset)
    if offset + 12 > len(data):
        raise SpawnerWaveDecodeError("truncated group mode")
    max_count, group_mode, kill_count = struct.unpack_from("<iii", data, offset)
    offset += 12
    target_key, offset = _read_string(data, offset)
    if offset + 6 > len(data):
        raise SpawnerWaveDecodeError("truncated group flags")
    flags = data[offset:offset + 2]
    if any(value not in (0, 1) for value in flags):
        raise SpawnerWaveDecodeError("invalid group bool")
    has_deadline, limit_max_count = (bool(value) for value in flags)
    timestamp = struct.unpack_from("<f", data, offset + 2)[0]
    offset += 6

    if (
        not math.isfinite(deadline_begin_delta_time)
        or not -100_000.0 <= deadline_begin_delta_time <= 10_000_000.0
        or not 0 <= backup_count <= 1_000_000
        or not 0 <= group_id <= 1_000_000
        or max_count < -1
        or max_count > 1_000_000
        or group_mode not in (0, 1, 2)
        or not 0 <= kill_count <= 1_000_000
        or not math.isfinite(timestamp)
        or not -100_000.0 <= timestamp <= 10_000_000.0
    ):
        raise SpawnerWaveDecodeError("implausible group tail")
    return {
        "tailOffset": start,
        "deadlineBeginDeltaTime": deadline_begin_delta_time,
        "groupBackUpCount": backup_count,
        "groupId": group_id,
        "groupKey": group_key or "",
        "groupMaxCount": max_count,
        "groupMode": group_mode,
        "groupModeKillCount": kill_count,
        "groupModeTargetKey": target_key or "",
        "hasDeadlineBegin": has_deadline,
        "limitGroupMaxCount": limit_max_count,
        "timestamp": timestamp,
    }, offset


def _decode_group_map(
    data: bytes,
    offset: int,
    end_offset: int,
) -> tuple[dict[str, Any], ...]:
    """Decode one group map whose exact end is the containing wave tail."""
    if offset + 4 > end_offset:
        raise SpawnerWaveDecodeError("truncated groupMap count")
    group_count = struct.unpack_from("<I", data, offset)[0]
    if group_count > MAX_GROUP_COUNT:
        raise SpawnerWaveDecodeError("implausible groupMap count")

    tail_candidates: list[tuple[dict[str, Any], int]] = []
    for candidate_offset in range(offset + 4, max(offset + 4, end_offset - 5)):
        try:
            row, row_end = _read_group_tail(data, candidate_offset)
        except SpawnerWaveDecodeError:
            continue
        if row_end > end_offset:
            continue
        tail_candidates.append((row, row_end))

    @lru_cache(maxsize=None)
    def parse_entries(
        entry_offset: int,
        remaining: int,
    ) -> tuple[tuple[dict[str, Any], ...], ...]:
        if remaining == 0:
            return ((),) if entry_offset == end_offset else ()
        if entry_offset + 5 > end_offset:
            return ()
        map_key = struct.unpack_from("<i", data, entry_offset)[0]
        value_start = entry_offset + 4
        if (
            not 0 <= map_key <= 1_000_000
            or data[value_start] != SPAWNER_GROUP_MEMBER_COUNT
        ):
            return ()

        solutions: list[tuple[dict[str, Any], ...]] = []
        for candidate, next_offset in tail_candidates:
            if candidate["tailOffset"] <= value_start + 4:
                continue
            row = {
                **candidate,
                "mapKey": map_key,
                "entryOffset": entry_offset,
                "valueOffset": value_start,
            }
            for suffix in parse_entries(next_offset, remaining - 1):
                solutions.append((row, *suffix))
                if len(solutions) > 1:
                    return tuple(solutions)
        return tuple(solutions)

    solutions = parse_entries(offset + 4, group_count)
    if len(solutions) != 1:
        raise SpawnerWaveDecodeError("no unique complete groupMap")
    rows = solutions[0]
    if [row["mapKey"] for row in rows] != list(range(1, group_count + 1)):
        raise SpawnerWaveDecodeError("changed groupMap index keys")
    named_keys = [row["groupKey"] for row in rows if row["groupKey"]]
    if len(set(named_keys)) != len(named_keys):
        raise SpawnerWaveDecodeError("duplicate groupKey")
    return rows


def decode_spawner_wave_map(data: bytes) -> dict[str, Any]:
    """Decode one uniquely delimited current-build SpawnerConfig wave map.

    The dictionary key is accepted only when its decimal representation equals
    the serialized ``waveKey``.  That deliberately narrow guard covers the
    current authored configs used by Story wave events and rejects other or
    changed shapes rather than guessing.
    """
    if not data or data[0] != SPAWNER_CONFIG_MEMBER_COUNT:
        raise SpawnerWaveDecodeError("SpawnerConfig member count changed")
    config_id, config_id_end = _read_string(data, 1)
    if not config_id:
        raise SpawnerWaveDecodeError("missing configId")

    tail_candidates: dict[str, list[tuple[dict[str, Any], int]]] = {}
    for offset in range(config_id_end, max(config_id_end, len(data) - 10)):
        try:
            row, end = _read_wave_tail(data, offset)
        except SpawnerWaveDecodeError:
            continue
        tail_candidates.setdefault(row["waveKey"], []).append((row, end))

    @lru_cache(maxsize=None)
    def parse_entries(offset: int, remaining: int) -> tuple[tuple[dict[str, Any], ...], ...]:
        if remaining == 0:
            return ((),) if offset == len(data) else ()
        if offset + 5 > len(data):
            return ()
        map_key = struct.unpack_from("<i", data, offset)[0]
        value_start = offset + 4
        if (
            not 0 <= map_key <= 1_000_000
            or data[value_start] != SPAWNER_WAVE_MEMBER_COUNT
        ):
            return ()

        solutions: list[tuple[dict[str, Any], ...]] = []
        for candidate, next_offset in tail_candidates.get(str(map_key), ()):
            if candidate["tailOffset"] <= value_start + 5:
                continue
            try:
                groups = _decode_group_map(
                    data,
                    value_start + 5,
                    candidate["tailOffset"],
                )
            except SpawnerWaveDecodeError:
                continue
            row = {
                **candidate,
                "entryOffset": offset,
                "valueOffset": value_start,
                "groupMapOffset": value_start + 5,
                "groupCount": len(groups),
                "groups": list(groups),
            }
            if remaining == 1:
                if next_offset == len(data):
                    solutions.append((row,))
                continue
            for suffix in parse_entries(next_offset, remaining - 1):
                solutions.append((row, *suffix))
                if len(solutions) > 1:
                    return tuple(solutions)
        return tuple(solutions)

    solutions: list[tuple[int, tuple[dict[str, Any], ...]]] = []
    for offset in range(config_id_end, max(config_id_end, len(data) - 8)):
        wave_count = struct.unpack_from("<I", data, offset)[0]
        if not 1 <= wave_count <= MAX_WAVE_COUNT:
            continue
        rows = parse_entries(offset + 4, wave_count)
        for row_set in rows:
            solutions.append((offset, row_set))
            if len(solutions) > 1:
                raise SpawnerWaveDecodeError("ambiguous complete waveMap")

    if len(solutions) != 1:
        raise SpawnerWaveDecodeError("no unique complete waveMap")
    wave_map_offset, rows = solutions[0]
    if len({row["waveKey"] for row in rows}) != len(rows):
        raise SpawnerWaveDecodeError("duplicate waveKey")
    return {
        "configId": config_id,
        "waveMapOffset": wave_map_offset,
        "waveCount": len(rows),
        "waves": list(rows),
        "schemaMappingId": SPAWNER_WAVE_SCHEMA_MAPPING_ID,
        "runtimeMappingId": SPAWNER_WAVE_RUNTIME_MAPPING_ID,
    }
