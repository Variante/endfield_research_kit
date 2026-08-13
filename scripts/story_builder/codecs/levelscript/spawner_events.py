"""Exact current-build spawner event field decoders."""

from __future__ import annotations

import struct
from typing import Any


_PARAM_TAIL = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"
_GROUP_BEGIN = "LevelEvent_OnSpawnerGroupBegin"
_WAVE_BEGIN = "LevelEvent_OnSpawnerWaveBegin"
_COMPLETE = "LevelEvent_OnSpawnerComplete"
_ENTITY_SPAWN = "LevelEvent_OnSpawnerEntitySpawn"


def _read_string_param(
    payload: bytes,
    cursor: int,
) -> tuple[str, int] | None:
    if cursor + 5 > len(payload) or payload[cursor] != 0x04:
        return None
    size = struct.unpack_from("<i", payload, cursor + 1)[0]
    cursor += 5
    if size < 0 or size > 256 or cursor + size + 12 > len(payload):
        return None
    raw = payload[cursor : cursor + size]
    cursor += size
    if payload[cursor : cursor + 12] != _PARAM_TAIL:
        return None
    try:
        value = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return value, cursor + 12


def _read_u64_param(
    payload: bytes,
    cursor: int,
) -> tuple[int, int] | None:
    if cursor + 21 > len(payload) or payload[cursor] != 0x04:
        return None
    value = struct.unpack_from("<Q", payload, cursor + 1)[0]
    if payload[cursor + 9 : cursor + 21] != _PARAM_TAIL:
        return None
    return value, cursor + 21


def _read_i32_param(
    payload: bytes,
    cursor: int,
) -> tuple[int, int] | None:
    if cursor + 17 > len(payload) or payload[cursor] != 0x04:
        return None
    value = struct.unpack_from("<i", payload, cursor + 1)[0]
    if payload[cursor + 5 : cursor + 17] != _PARAM_TAIL:
        return None
    return value, cursor + 17


def _read_output(
    payload: bytes,
    cursor: int,
) -> tuple[str, int] | None:
    if cursor + 9 > len(payload) or payload[cursor] != 0x02:
        return None
    source = struct.unpack_from("<i", payload, cursor + 1)[0]
    size = struct.unpack_from("<i", payload, cursor + 5)[0]
    cursor += 9
    if source != 0 or size <= 0 or size > 256 or cursor + size > len(payload):
        return None
    try:
        value = payload[cursor : cursor + size].decode("utf-8")
    except UnicodeDecodeError:
        return None
    return value, cursor + size


def _decode_begin(payload: bytes, *, wave: bool) -> dict[str, Any]:
    """Decode exact constant spawner group/wave filters and null outputs."""
    if len(payload) < 31 or payload[17:31] != b"\x04\x01" + _PARAM_TAIL:
        return {}
    cursor = 31

    if wave:
        spawner_result = _read_u64_param(payload, cursor)
        if spawner_result is None:
            return {}
        spawner_id, cursor = spawner_result
        if cursor >= len(payload) or payload[cursor] != 0xFF:
            return {}
        key_result = _read_string_param(payload, cursor + 1)
        if key_result is None:
            return {}
        key, cursor = key_result
        if cursor >= len(payload) or payload[cursor] != 0xFF:
            return {}
        cursor += 1
        if cursor != len(payload):
            return {}
        return {
            "spawnerFilterId": spawner_id,
            "spawnerOutputPresent": False,
            "waveKeyFilter": key,
            "waveKeyOutputPresent": False,
            "payloadShape": "constant-spawner-and-wave-key-null-outputs-exact-eof",
        }

    key_result = _read_string_param(payload, cursor)
    if key_result is None:
        return {}
    key, cursor = key_result
    if cursor >= len(payload) or payload[cursor] != 0xFF:
        return {}
    spawner_result = _read_u64_param(payload, cursor + 1)
    if spawner_result is None:
        return {}
    spawner_id, cursor = spawner_result
    if cursor >= len(payload) or payload[cursor] != 0xFF:
        return {}
    cursor += 1
    if cursor != len(payload):
        return {}
    return {
        "groupKeyFilter": key,
        "groupKeyOutputPresent": False,
        "spawnerFilterId": spawner_id,
        "spawnerOutputPresent": False,
        "payloadShape": "constant-group-key-and-spawner-null-outputs-exact-eof",
    }


def _decode_complete(payload: bytes) -> dict[str, Any]:
    if (
        len(payload) != 53
        or payload[17:31] != b"\x04\x01" + _PARAM_TAIL
        or payload[31] != 0x04
        or payload[40:52] != _PARAM_TAIL
        or payload[52] != 0xFF
    ):
        return {}
    return {
        "spawnerFilterId": struct.unpack_from("<Q", payload, 32)[0],
        "spawnerOutputPresent": False,
        "payloadShape": "constant-spawner-null-output-exact-eof",
    }


def _decode_entity_spawn(payload: bytes) -> dict[str, Any]:
    if len(payload) < 90 or payload[17:31] != b"\x04\x01" + _PARAM_TAIL:
        return {}
    cursor = 31
    entity_output_result = _read_output(payload, cursor)
    if entity_output_result is None:
        return {}
    entity_output, cursor = entity_output_result
    template_result = _read_i32_param(payload, cursor)
    if template_result is None:
        return {}
    entity_template_filter, cursor = template_result
    group_result = _read_string_param(payload, cursor)
    if group_result is None:
        return {}
    group_key, cursor = group_result
    group_output_result = _read_output(payload, cursor)
    if group_output_result is None:
        return {}
    group_output, cursor = group_output_result
    spawner_result = _read_u64_param(payload, cursor)
    if spawner_result is None:
        return {}
    spawner_id, cursor = spawner_result
    if cursor >= len(payload) or payload[cursor] != 0xFF:
        return {}
    wave_output_result = _read_output(payload, cursor + 1)
    if wave_output_result is None:
        return {}
    wave_output, cursor = wave_output_result
    if not entity_output or not group_key or not group_output or not wave_output:
        return {}
    if cursor != len(payload):
        return {}
    return {
        "entityOutputRef": entity_output,
        "entityTemplateIdFilter": entity_template_filter,
        "groupKeyFilter": group_key,
        "groupKeyOutputRef": group_output,
        "spawnerFilterId": spawner_id,
        "spawnerOutputPresent": False,
        "waveKeyOutputRef": wave_output,
        "payloadShape": "constant-spawner-group-and-template-exact-eof",
    }


def decode_spawner_event_fields(
    payload: bytes,
    native_header_name: str,
) -> dict[str, Any]:
    """Decode one exact spawner event family member selected by its owner name."""
    if native_header_name == _GROUP_BEGIN:
        return _decode_begin(payload, wave=False)
    if native_header_name == _WAVE_BEGIN:
        return _decode_begin(payload, wave=True)
    if native_header_name == _COMPLETE:
        return _decode_complete(payload)
    if native_header_name == _ENTITY_SPAWN:
        return _decode_entity_spawn(payload)
    return {}
