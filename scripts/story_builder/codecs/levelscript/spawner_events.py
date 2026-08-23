"""Exact current-build spawner event field decoders."""

from __future__ import annotations

import struct
from typing import Any


_PARAM_TAIL = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"
_GROUP_BEGIN = "LevelEvent_OnSpawnerGroupBegin"
_WAVE_BEGIN = "LevelEvent_OnSpawnerWaveBegin"
_COMPLETE = "LevelEvent_OnSpawnerComplete"
_ENTITY_SPAWN = "LevelEvent_OnSpawnerEntitySpawn"
_ENTITY_LIFECYCLE_EVENTS = {
    "LevelEvent_OnSpawnerEntityDie",
    "LevelEvent_OnSpawnerEntityDieStart",
    "LevelEvent_OnSpawnerEntityDieEnd",
}


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
    decoded = _read_output_param(payload, cursor)
    if decoded is None:
        return None
    detail, cursor = decoded
    value = detail.get("path")
    if detail.get("paramSource") != 0 or not isinstance(value, str):
        return None
    return value, cursor


def _read_output_param(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode a present ``ParamOutput``, retaining a nullable property path."""
    if cursor + 9 > len(payload) or payload[cursor] != 0x02:
        return None
    source = struct.unpack_from("<i", payload, cursor + 1)[0]
    size = struct.unpack_from("<i", payload, cursor + 5)[0]
    cursor += 9
    if source < 0 or source > 0x10000:
        return None
    if size == -1:
        return {"paramSource": source, "path": None}, cursor
    if size <= 0 or size > 256 or cursor + size > len(payload):
        return None
    try:
        value = payload[cursor : cursor + size].decode("utf-8")
    except UnicodeDecodeError:
        return None
    return {"paramSource": source, "path": value}, cursor + size


def _read_i32_param_detail(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    if cursor + 17 > len(payload) or payload[cursor] != 0x04:
        return None
    value = struct.unpack_from("<i", payload, cursor + 1)[0]
    id_ref, source, path_size = struct.unpack_from("<iii", payload, cursor + 5)
    cursor += 17
    if id_ref < -1 or source < 0 or source > 0x10000:
        return None
    if path_size == -1:
        path = None
    elif 0 <= path_size <= 1024 and cursor + path_size <= len(payload):
        try:
            path = payload[cursor : cursor + path_size].decode("utf-8")
        except UnicodeDecodeError:
            return None
        cursor += path_size
    else:
        return None
    return {"value": value, "idRef": id_ref, "paramSource": source, "path": path}, cursor


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
    if cursor >= len(payload):
        return {}
    if payload[cursor] == 0xFF:
        group_key = None
        cursor += 1
    else:
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
    if cursor >= len(payload):
        return {}
    if payload[cursor] == 0xFF:
        wave_key = None
        cursor += 1
    else:
        wave_result = _read_string_param(payload, cursor)
        if wave_result is None:
            return {}
        wave_key, cursor = wave_result
    wave_output_result = _read_output(payload, cursor)
    if wave_output_result is None:
        return {}
    wave_output, cursor = wave_output_result
    if not entity_output or not group_output or not wave_output:
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
        "waveKeyFilter": wave_key,
        "waveKeyOutputRef": wave_output,
        "subtypeConsumedBytes": cursor,
        "payloadShape": "constant-spawner-optional-group-wave-and-template-exact-eof",
    }


def _decode_entity_lifecycle(payload: bytes) -> dict[str, Any]:
    """Decode the exact spawn-entity die/start/end filters and outputs."""
    if len(payload) < 31 or payload[17:31] != b"\x04\x01" + _PARAM_TAIL:
        return {}
    cursor = 31

    entity_output = _read_output_param(payload, cursor)
    if entity_output is None:
        return {}
    entity_output_detail, cursor = entity_output

    filter_type = _read_i32_param_detail(payload, cursor)
    if filter_type is None:
        return {}
    filter_type_detail, cursor = filter_type

    def read_optional_string() -> tuple[bool, str | None]:
        nonlocal cursor
        if cursor >= len(payload):
            return False, None
        if payload[cursor] == 0xFF:
            cursor += 1
            return True, None
        decoded = _read_string_param(payload, cursor)
        if decoded is None:
            return False, None
        value, cursor = decoded
        return True, value

    group_valid, group_key = read_optional_string()
    if not group_valid:
        return {}

    group_output = _read_output_param(payload, cursor)
    if group_output is None:
        return {}
    group_output_detail, cursor = group_output

    if cursor + 21 > len(payload) or payload[cursor] != 0x04:
        return {}
    spawner_id = struct.unpack_from("<Q", payload, cursor + 1)[0]
    if payload[cursor + 9 : cursor + 21] != _PARAM_TAIL:
        return {}
    cursor += 21

    wave_valid, wave_key = read_optional_string()
    if not wave_valid:
        return {}

    wave_output = _read_output_param(payload, cursor)
    if wave_output is None:
        return {}
    wave_output_detail, cursor = wave_output
    return {
        "entityOutputParam": entity_output_detail,
        "filterType": filter_type_detail,
        "groupKeyFilter": group_key,
        "groupKeyOutputParam": group_output_detail,
        "spawnerFilterId": spawner_id,
        "waveKeyFilter": wave_key,
        "waveKeyOutputParam": wave_output_detail,
        "subtypeConsumedBytes": cursor,
        "payloadShape": (
            "spawner-entity-lifecycle-filters-and-outputs-exact-eof"
            if cursor == len(payload)
            else "spawner-entity-lifecycle-filters-and-outputs-exact-prefix"
        ),
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
    if native_header_name in _ENTITY_LIFECYCLE_EVENTS:
        return _decode_entity_lifecycle(payload)
    return {}
