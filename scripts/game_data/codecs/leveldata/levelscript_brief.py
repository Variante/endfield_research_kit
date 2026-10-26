"""Exact MemoryPack codec for LevelData member 22 LevelScriptBriefData.

Member 22 is the complete ``Dictionary<ulong, LevelScriptBriefData>``; each
value closes its nine current fields in generated order. Positive risk and
property children stop until their independent source codecs are proved.
``decode_levelscript_brief_dictionary_at`` is the exact sequential entry
used by ``leveldata_binary``. The search helpers
(``find_levelscript_brief_data_entries``,
``parse_leveldata_levelscript_brief_dictionary``) serve Story ownership
lookups and are not framing evidence by themselves.
"""

from __future__ import annotations

from typing import Any

from .memorypack import read_count, read_i32, read_u64
from scripts.game_data.serialization_roots_native import check_root_native_inputs


def decode_levelscript_brief_data_entry(
    data: bytes,
    offset: int,
    *,
    expected_script_id: int | None = None,
    diagnostics: list[dict] | None = None,
) -> dict[str, Any] | None:
    def empty(field, at):
        decoded = read_count(data, at)
        if decoded is None or decoded[0] > 0:
            if diagnostics is not None:
                diagnostics.append({"validator":"levelScriptBrief", "gate":field,
                    "sourceOffset":at, "expected":"null/empty until current child source/codec is proved",
                    "actual":decoded[0] if decoded else "truncated/invalid count"})
            return None
        return decoded

    key_decoded = read_u64(data, offset)
    if key_decoded is None:
        return None
    key, cursor = key_decoded
    if expected_script_id is not None and key != expected_script_id:
        return None
    if cursor >= len(data) or data[cursor] != 9:
        return None
    cursor += 1

    data_path_decoded = read_u64(data, cursor)
    risk_decoded = empty("interactiveActiveRiskEntityIdList", data_path_decoded[1]) if data_path_decoded else None
    type_decoded = read_i32(data, risk_decoded[1]) if risk_decoded else None
    max_stage_decoded = read_i32(data, type_decoded[1]) if type_decoded else None
    parent_decoded = read_u64(data, max_stage_decoded[1]) if max_stage_decoded else None
    if None in (data_path_decoded, risk_decoded, type_decoded, max_stage_decoded, parent_decoded):
        return None
    data_path_hash, _ = data_path_decoded
    level_script_type, _ = type_decoded
    max_stage, _ = max_stage_decoded
    parent_script_id, cursor = parent_decoded
    if not 0 <= level_script_type <= 5 or not 0 <= max_stage <= 1_000_000:
        return None

    properties_decoded = empty("properties", cursor)
    if properties_decoded is None:
        return None
    property_count, cursor = properties_decoded
    property_map_decoded = empty("propertyIdToKeyMap", cursor)
    if property_map_decoded is None:
        return None
    property_map_count, cursor = property_map_decoded

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
        "interactiveActiveRiskEntityIdList": None if risk_decoded[0] < 0 else [],
        "levelScriptType": level_script_type,
        "maxStage": max_stage,
        "parentLevelScriptId": str(parent_script_id),
        "propertyCount": max(0, property_count),
        "properties": [],
        "propertyMapCount": max(0, property_map_count),
        "propertyIdToKeyMap": {},
        "refWorldEntityCount": max(0, world_ref_count),
        "refWorldEntityIds": world_entity_ids,
    }


def decode_levelscript_brief_dictionary_at(
    data: bytes,
    offset: int,
    *, diagnostics: list[dict] | None = None,
) -> dict[str, Any] | None:
    gate = check_root_native_inputs()
    if gate.status != "validated":
        if diagnostics is not None:
            diagnostics.append({"validator":"levelScriptBrief", "gate":"selected-native-inputs",
                "sourceOffset":offset, "expected":"validated", "actual":gate.status, "detail":gate.detail})
        return None
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
        entry = decode_levelscript_brief_data_entry(data, cursor, diagnostics=diagnostics)
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
    if not data or data[0] != 0x2B or check_root_native_inputs().status != "validated":
        return []
    return [
        entry
        for offset in _find_offsets(data, script_id.to_bytes(8, "little", signed=False))
        if (entry := decode_levelscript_brief_data_entry(
            data, offset, expected_script_id=script_id
        )) is not None
    ]


def parse_leveldata_levelscript_brief_dictionary(
    data: bytes, candidate_script_ids: set[int],
) -> dict[int, dict]:
    entries: list[dict[str, Any]] = []
    for script_id in sorted(candidate_script_ids):
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
