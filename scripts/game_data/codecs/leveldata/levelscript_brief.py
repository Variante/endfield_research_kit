"""Exact MemoryPack codec for LevelData member 22 LevelScriptBriefData."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from .memorypack import read_count, read_i32, read_string, read_u64


def decode_levelscript_brief_data_entry(
    data: bytes,
    offset: int,
    *,
    expected_script_id: int | None = None,
) -> dict[str, Any] | None:
    key_decoded = read_u64(data, offset)
    if key_decoded is None:
        return None
    key, cursor = key_decoded
    if expected_script_id is not None and key != expected_script_id:
        return None
    if cursor >= len(data) or data[cursor] != 8:
        return None
    cursor += 1

    data_path_decoded = read_u64(data, cursor)
    type_decoded = read_i32(data, data_path_decoded[1]) if data_path_decoded else None
    max_stage_decoded = read_i32(data, type_decoded[1]) if type_decoded else None
    parent_decoded = read_u64(data, max_stage_decoded[1]) if max_stage_decoded else None
    if None in (data_path_decoded, type_decoded, max_stage_decoded, parent_decoded):
        return None
    data_path_hash, _ = data_path_decoded
    level_script_type, _ = type_decoded
    max_stage, _ = max_stage_decoded
    parent_script_id, cursor = parent_decoded
    if not 0 <= level_script_type <= 5 or not 0 <= max_stage <= 1_000_000:
        return None

    properties_decoded = read_count(data, cursor, max_count=100_000)
    if properties_decoded is None:
        return None
    property_count, cursor = properties_decoded
    properties: list[dict[str, Any]] = []
    for _ in range(max(0, property_count)):
        if cursor >= len(data) or data[cursor] not in (2, 0xFF):
            return None
        property_header = data[cursor]
        cursor += 1
        if property_header == 0xFF:
            properties.append({"value": None})
            continue
        name_decoded = read_string(data, cursor, max_length=512)
        if name_decoded is None:
            return None
        property_name, cursor = name_decoded
        if cursor >= len(data) or data[cursor] not in (2, 0xFF):
            return None
        value_header = data[cursor]
        cursor += 1
        if value_header == 0xFF:
            properties.append({"name": property_name, "value": None})
            continue
        value_type_decoded = read_i32(data, cursor)
        if value_type_decoded is None:
            return None
        value_type, cursor = value_type_decoded
        atoms_decoded = read_count(data, cursor, max_count=100_000)
        if atoms_decoded is None:
            return None
        atom_count, cursor = atoms_decoded
        atoms: list[dict[str, Any] | None] = []
        for _ in range(max(0, atom_count)):
            if cursor >= len(data) or data[cursor] not in (2, 0xFF):
                return None
            atom_header = data[cursor]
            cursor += 1
            if atom_header == 0xFF:
                atoms.append(None)
                continue
            bits_decoded = read_u64(data, cursor)
            if bits_decoded is None:
                return None
            value_bit64, cursor = bits_decoded
            text_decoded = read_string(data, cursor, max_length=4096)
            if text_decoded is None:
                return None
            atom_text, cursor = text_decoded
            atoms.append({"valueBit64": value_bit64, "text": atom_text})
        properties.append({
            "name": property_name,
            "value": {
                "valueType": value_type,
                "atomCount": max(0, atom_count),
                "atoms": atoms,
            },
        })

    property_map_decoded = read_count(data, cursor, max_count=100_000)
    if property_map_decoded is None:
        return None
    property_map_count, cursor = property_map_decoded
    property_id_to_key: dict[str, str] = {}
    for _ in range(max(0, property_map_count)):
        property_id_decoded = read_i32(data, cursor)
        if property_id_decoded is None:
            return None
        property_id, cursor = property_id_decoded
        key_decoded = read_string(data, cursor, max_length=4096)
        if key_decoded is None:
            return None
        property_key, cursor = key_decoded
        property_id_to_key[str(property_id)] = property_key

    world_refs_decoded = read_count(data, cursor, max_count=100_000)
    if world_refs_decoded is None:
        return None
    world_ref_count, cursor = world_refs_decoded
    world_entity_ids: list[str] = []
    for _ in range(max(0, world_ref_count)):
        world_ref_decoded = read_u64(data, cursor)
        if world_ref_decoded is None:
            return None
        world_entity_id, cursor = world_ref_decoded
        world_entity_ids.append(str(world_entity_id))

    final_script_decoded = read_u64(data, cursor)
    if final_script_decoded is None:
        return None
    final_script_id, cursor = final_script_decoded
    if final_script_id != key:
        return None
    return {
        "keyOffset": offset,
        "endOffset": cursor,
        "scriptId": str(key),
        "dataPathHash": str(data_path_hash),
        "levelScriptType": level_script_type,
        "maxStage": max_stage,
        "parentLevelScriptId": str(parent_script_id),
        "propertyCount": max(0, property_count),
        "properties": properties,
        "propertyMapCount": max(0, property_map_count),
        "propertyIdToKeyMap": property_id_to_key,
        "refWorldEntityCount": max(0, world_ref_count),
        "refWorldEntityIds": world_entity_ids,
    }


def decode_levelscript_brief_dictionary_at(
    data: bytes,
    offset: int,
) -> dict[str, Any] | None:
    decoded = read_count(data, offset, max_count=100_000)
    if decoded is None:
        return None
    count, cursor = decoded
    if count < 0:
        return {
            "startOffset": offset,
            "endOffset": cursor,
            "count": count,
            "entries": [],
            "value": None,
        }
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for _ in range(count):
        entry = decode_levelscript_brief_data_entry(data, cursor)
        if entry is None or entry["scriptId"] in seen:
            return None
        seen.add(entry["scriptId"])
        entries.append(entry)
        cursor = int(entry["endOffset"])
    return {
        "startOffset": offset,
        "endOffset": cursor,
        "count": count,
        "entries": entries,
    }


def _find_offsets(data: bytes, needle: bytes) -> list[int]:
    offsets: list[int] = []
    start = 0
    while True:
        offset = data.find(needle, start)
        if offset < 0:
            return offsets
        offsets.append(offset)
        start = offset + 1


def find_levelscript_brief_data_entries(data: bytes, script_id: int) -> list[dict[str, Any]]:
    if not data or data[0] != 0x2B:
        return []
    return [
        entry
        for offset in _find_offsets(data, script_id.to_bytes(8, "little", signed=False))
        if (entry := decode_levelscript_brief_data_entry(
            data, offset, expected_script_id=script_id
        )) is not None
    ]


@lru_cache(maxsize=None)
def _parse_cached(data: bytes, candidate_script_ids: tuple[int, ...]) -> dict[int, dict]:
    entries: list[dict[str, Any]] = []
    for script_id in candidate_script_ids:
        entries.extend(find_levelscript_brief_data_entries(data, script_id))
    entries.sort(key=lambda entry: int(entry["keyOffset"]))
    if not entries or len({int(row["keyOffset"]) for row in entries}) != len(entries):
        return {}
    if any(
        int(previous["endOffset"]) != int(current["keyOffset"])
        for previous, current in zip(entries, entries[1:])
    ):
        return {}
    count_offset = int(entries[0]["keyOffset"]) - 4
    count_decoded = read_i32(data, count_offset)
    if count_decoded is None or count_decoded[0] != len(entries):
        return {}
    result: dict[int, dict] = {}
    for entry in entries:
        script_id = int(entry["scriptId"])
        if script_id in result:
            return {}
        result[script_id] = {
            **entry,
            "dictionaryCountOffset": count_offset,
            "dictionaryEntryCount": len(entries),
        }
    return result


def parse_leveldata_levelscript_brief_dictionary(
    data: bytes,
    candidate_script_ids: set[int],
) -> dict[int, dict]:
    return _parse_cached(data, tuple(sorted(candidate_script_ids)))
