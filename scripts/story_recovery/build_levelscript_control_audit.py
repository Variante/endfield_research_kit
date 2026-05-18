"""Audit LevelScript control-layer evidence for one mission.

This report is intentionally diagnostic. It answers "what controls or owns
these LevelScripts?" from original/decodeable game data, without promoting
weak ownership hints into story order.

Sources:

- MissionRuntimeAsset/<mission>.json and *_meta.json
- LevelScriptData/<level>/<script>.json binary records
- LevelData/<level>/*.json script-id references and nearby strings
- optional IL2CPP metadata for runtime field/enum names

Output:
  reports/mission_order/<mission>_levelscript_control_audit.json
  reports/mission_order/<mission>_levelscript_control_audit.md
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import struct
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from story_builder.level_bindings import (  # noqa: E402
    _build_uid_record_chains,
    _extract_length_prefixed_ascii_strings,
    _extract_tagged_ascii_strings,
    _load_levelscript_binding_data,
    classify_levelscript_record,
)

DATA_JSON_ROOT = ROOT / "export_full" / "structured" / "StreamingAssets" / "Data" / "Json"
MISSION_ROOT = DATA_JSON_ROOT / "MissionRuntimeAsset"
LEVELSCRIPT_ROOT = DATA_JSON_ROOT / "LevelScriptData"
LEVELDATA_ROOT = DATA_JSON_ROOT / "LevelData"
WEBUI_MISSION_ROOT = ROOT / "webui" / "data" / "lang" / "CN" / "mission"
WEBUI_CONV_ROOT = ROOT / "webui" / "data" / "lang" / "CN" / "conv"
STORY_ORDER_PATH = ROOT / "webui" / "data" / "assets" / "story_order.json"
DEFAULT_METADATA = Path(r"D:\Program Files\Endfield Game\Endfield_Data\il2cpp_data\Metadata\global-metadata.dat")
CATALOG_HELPER = ROOT / "tools" / "endfield-il2cpp" / "catalog_option_flow_metadata.py"

MISSION_STORY_RE = re.compile(r"^(?:cutscene|radio|dlg|black|env|sns|remotecomm)_[a-z0-9]+m[0-9]+")
QUEST_RE_TEMPLATE = r"^{mission}_q#"
LT_MARKER_RE = re.compile(r"^lt:(?:p|mp):[0-9a-f]{{8}}:[0-9a-f]{{8}}$")
NOISY_CONTEXT_RE = re.compile(r"^(?:#[0-9a-f]{8}|[0-9a-f]{8})$")

PLAY_RECORD_CLASSES = {"play_levelseq", "play_cutscene", "play_radio", "play_dialog"}


def repo_rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        return str(path).replace("\\", "/")


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def write_text_if_changed(path: Path, text: str) -> None:
    if path.exists():
        try:
            if path.read_text(encoding="utf-8") == text:
                return
        except OSError:
            pass
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, payload: Any) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    write_text_if_changed(path, text)


def md_escape(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def unique_preserve(values: list[Any]) -> list[Any]:
    out: list[Any] = []
    seen: set[Any] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def unwrap_const(value: Any) -> Any:
    if isinstance(value, dict) and "constValue" in value:
        return value.get("constValue")
    return value


def payload_to_story_key(text: str, mission: str) -> str:
    if not isinstance(text, str) or not text:
        return ""
    if text.startswith(f"cutscene_{mission}_"):
        return text.split("/", 1)[0]
    if text.startswith(f"radio_{mission}_"):
        return text.split("/", 1)[0]
    if text.startswith(f"dlg_{mission}_"):
        return f"misc_{text.split('/', 1)[0]}"
    match = re.match(r"^au_special_cs_(" + re.escape(mission) + r")_(\d+)(?:_|$)", text)
    if match:
        return f"cutscene_{match.group(1)}_{match.group(2)}"
    match = re.match(r"^cs_(" + re.escape(mission) + r")_(\d+)(?:[_.].*)?$", text)
    if match:
        return f"cutscene_{match.group(1)}_{match.group(2)}"
    return ""


def mission_level_ids(mission: str, primary_level: str, language: str) -> list[str]:
    out: list[str] = []

    def add(level_id: Any) -> None:
        text = str(level_id or "")
        if text and text not in out:
            out.append(text)

    add(primary_level)

    mission_bundle = ROOT / "webui" / "data" / "lang" / language / "mission" / f"{mission}.json"
    if mission_bundle.is_file():
        payload = read_json(mission_bundle, {})
        for ref in ((payload.get("extras") or {}).get("levelRefs") or []):
            if isinstance(ref, dict):
                add(ref.get("levelId"))

    story_order = read_json(STORY_ORDER_PATH, {})
    mission_order = ((story_order.get("missions") or {}).get(mission) or {})
    for level_id in mission_order.get("levels") or []:
        add(level_id)

    for path in LEVELDATA_ROOT.glob(f"*/*{mission}*"):
        add(path.parent.name)
    return out


def quest_topo_order(quest_dic: dict[str, Any]) -> list[str]:
    prev = {qid: list((quest or {}).get("prevQuestIdList") or []) for qid, quest in quest_dic.items()}
    pending = set(quest_dic)
    placed: list[str] = []
    placed_set: set[str] = set()
    while pending:
        progressed = False
        for qid in sorted(pending):
            if all(parent in placed_set or parent not in quest_dic for parent in prev[qid]):
                placed.append(qid)
                placed_set.add(qid)
                pending.remove(qid)
                progressed = True
                break
        if not progressed:
            placed.extend(sorted(pending))
            break
    return placed


def collect_mission_runtime_conditions(mission: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def visit(obj: Any, path: str, quest_id: str = "") -> None:
        if isinstance(obj, dict):
            next_quest = str(obj.get("questId") or quest_id)
            type_name = str(obj.get("$type") or "")
            has_script_id = "_scriptId" in obj or "scriptId" in obj
            if "LevelScript" in type_name and has_script_id:
                script_value = unwrap_const(obj.get("_scriptId", obj.get("scriptId")))
                if isinstance(script_value, dict):
                    script_id = script_value.get("scriptId")
                else:
                    script_id = script_value
                row = {
                    "path": path,
                    "questId": next_quest,
                    "type": type_name,
                    "uniqueId": obj.get("uniqueId"),
                    "mapId": unwrap_const(
                        obj.get(
                            "_mapId",
                            obj.get("mapId", obj.get("_levelId", obj.get("levelId"))),
                        )
                    ),
                    "scriptId": script_id,
                    "key": unwrap_const(obj.get("_key", obj.get("key"))),
                    "value": unwrap_const(obj.get("_value", obj.get("value"))),
                    "comparer": unwrap_const(obj.get("_comparer", obj.get("comparer"))),
                }
                rows.append({k: v for k, v in row.items() if v not in (None, "", {})})
            for key, value in obj.items():
                visit(value, f"{path}.{key}", next_quest)
        elif isinstance(obj, list):
            for index, value in enumerate(obj):
                visit(value, f"{path}[{index}]", quest_id)

    visit(mission, "$")
    return rows


def extract_story_order_entries(mission: str) -> dict[str, dict[str, Any]]:
    payload = read_json(STORY_ORDER_PATH, {})
    mission_payload = ((payload.get("missions") or {}).get(mission) or {})
    out: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(mission_payload.get("entries") or []):
        if isinstance(entry, dict) and entry.get("key"):
            item = dict(entry)
            item["orderIndex"] = index
            out[str(entry["key"])] = item
    return out


def tagged_and_plain_strings(data: bytes) -> list[dict[str, Any]]:
    tagged: list[dict[str, Any]] = []
    for tag in (0x02, 0x04):
        for hit in _extract_tagged_ascii_strings(data, tag):
            row = dict(hit)
            row["tag"] = f"0x{tag:02x}"
            tagged.append(row)
    tagged_offsets = {int(hit["offset"]) for hit in tagged}
    plain = _extract_length_prefixed_ascii_strings(data, tagged_offsets=tagged_offsets)
    rows: dict[tuple[int, str], dict[str, Any]] = {}
    for hit in [*tagged, *plain]:
        text = str(hit.get("text") or "")
        if len(text) > 120:
            continue
        rows[(int(hit.get("offset") or 0), text)] = hit
    return sorted(rows.values(), key=lambda hit: int(hit.get("offset") or 0))


def context_strings(
    string_hits: list[dict[str, Any]],
    offset: int,
    *,
    radius: int = 240,
    limit: int = 10,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_text: set[str] = set()
    for hit in string_hits:
        hit_offset = int(hit.get("offset") or 0)
        if abs(hit_offset - offset) > radius:
            continue
        text = str(hit.get("text") or "")
        if not text or text in seen_text or NOISY_CONTEXT_RE.match(text):
            continue
        if not all(32 <= ord(ch) < 127 for ch in text):
            continue
        seen_text.add(text)
        rows.append({
            "offset": hit_offset,
            "delta": hit_offset - offset,
            "text": text,
            "tag": hit.get("tag", "plain"),
        })
    rows.sort(key=lambda row: (abs(int(row["delta"])), int(row["offset"])))
    return rows[:limit]


def script_id_sort_key(script_id: str) -> tuple[int, int | str]:
    try:
        return (0, int(script_id))
    except ValueError:
        return (1, script_id)


def record_for_offset(records: list[dict[str, Any]], offset: int, data_len: int) -> dict[str, Any] | None:
    for index, record in enumerate(records):
        next_start = int(records[index + 1]["start"]) if index + 1 < len(records) else data_len
        payload_start = int(record.get("payloadStart", record.get("start", 0)))
        if payload_start <= offset < next_start:
            return record
    return None


def compact_record(record: dict[str, Any] | None) -> dict[str, Any]:
    if not record:
        return {}
    return {
        "start": int(record.get("start") or 0),
        "code": f"0x{int(record.get('code') or 0):04x}",
        "kind": f"0x{int(record.get('kind') or 0):02x}",
        "localId": record.get("localId"),
        "nextId": record.get("nextId"),
        "class": classify_levelscript_record(record),
        "strings": [hit.get("text") for hit in (record.get("strings") or [])[:8]],
        "plainStrings": [hit.get("text") for hit in (record.get("plainStrings") or [])[:8]],
    }


def collect_script_files(levels: list[str]) -> dict[tuple[str, str], dict[str, Any]]:
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for level in levels:
        info = _load_levelscript_binding_data(level)
        for file_info in info.get("files") or []:
            stem = str(file_info.get("fileStem") or "")
            if not stem:
                continue
            out[(level, stem)] = dict(file_info)
    return out


def collect_script_story_events(
    file_info: dict[str, Any],
    mission: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    records = list(file_info.get("records") or [])
    for hit in sorted(file_info.get("stringHits") or [], key=lambda row: int(row.get("offset") or 0)):
        payload = str(hit.get("text") or "")
        key = payload_to_story_key(payload, mission)
        if not key:
            continue
        offset = int(hit.get("offset") or 0)
        if (key, offset) in seen:
            continue
        seen.add((key, offset))
        record = record_for_offset(records, offset, 10**18)
        out.append({
            "key": key,
            "payload": payload,
            "offset": offset,
            "record": compact_record(record),
        })
    return out


def collect_levelseq_hits(file_info: dict[str, Any], mission: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    prefix = f"levelseq_{mission}_"
    for hit in file_info.get("stringHits") or []:
        text = str(hit.get("text") or "")
        if text.startswith(prefix):
            out.append({"text": text, "offset": int(hit.get("offset") or 0)})
    return sorted(out, key=lambda row: int(row["offset"]))


def collect_quest_refs(file_info: dict[str, Any], mission: str) -> list[dict[str, Any]]:
    quest_re = re.compile(QUEST_RE_TEMPLATE.format(mission=re.escape(mission)))
    rows: list[dict[str, Any]] = []
    for hit in [*list(file_info.get("stringHits") or []), *list(file_info.get("plainStringHits") or [])]:
        text = str(hit.get("text") or "")
        if quest_re.match(text):
            rows.append({"questId": text, "offset": int(hit.get("offset") or 0)})
    return sorted(rows, key=lambda row: int(row["offset"]))


def collect_property_hits(file_info: dict[str, Any], property_keys: set[str]) -> list[dict[str, Any]]:
    if not property_keys:
        return []
    rows: list[dict[str, Any]] = []
    for hit in [*list(file_info.get("stringHits") or []), *list(file_info.get("plainStringHits") or [])]:
        text = str(hit.get("text") or "")
        if text in property_keys:
            rows.append({"key": text, "offset": int(hit.get("offset") or 0)})
    return sorted(rows, key=lambda row: int(row["offset"]))


def all_numeric_script_ids_by_level(levels: list[str]) -> dict[str, set[int]]:
    out: dict[str, set[int]] = {}
    for level in levels:
        level_dir = LEVELSCRIPT_ROOT / level
        if not level_dir.is_dir():
            continue
        ids: set[int] = set()
        for path in level_dir.glob("*.json"):
            if path.stem.isdigit():
                ids.add(int(path.stem))
        out[level] = ids
    return out


def collect_cross_script_refs(
    script_files: dict[tuple[str, str], dict[str, Any]],
    ids_by_level: dict[str, set[int]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (level, stem), file_info in script_files.items():
        if not str(stem).isdigit():
            continue
        path = ROOT / str(file_info.get("file") or "")
        try:
            data = path.read_bytes()
        except OSError:
            continue
        own_id = int(stem)
        records = list(file_info.get("records") or [])
        for target_id in sorted(ids_by_level.get(level) or []):
            if target_id == own_id:
                continue
            needle = struct.pack("<Q", target_id)
            start = 0
            while True:
                offset = data.find(needle, start)
                if offset < 0:
                    break
                start = offset + 1
                record = record_for_offset(records, offset, len(data))
                rows.append({
                    "levelId": level,
                    "sourceScript": stem,
                    "targetScript": str(target_id),
                    "offset": offset,
                    "record": compact_record(record),
                })
    return rows


def collect_leveldata_script_refs(
    levels: list[str],
    script_ids_by_level: dict[str, set[int]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for level in levels:
        level_dir = LEVELDATA_ROOT / level
        if not level_dir.is_dir():
            continue
        script_ids = sorted(script_ids_by_level.get(level) or [])
        if not script_ids:
            continue
        for path in sorted(level_dir.glob("*.json")):
            try:
                data = path.read_bytes()
            except OSError:
                continue
            strings = tagged_and_plain_strings(data)
            for script_id in script_ids:
                needle = struct.pack("<Q", script_id)
                start = 0
                while True:
                    offset = data.find(needle, start)
                    if offset < 0:
                        break
                    start = offset + 1
                    context = context_strings(strings, offset)
                    rows.append({
                        "levelId": level,
                        "file": repo_rel(path),
                        "scriptId": str(script_id),
                        "offset": offset,
                        "context": context,
                        "markers": [
                            row["text"]
                            for row in context
                            if LT_MARKER_RE.match(str(row.get("text") or ""))
                        ],
                    })
    return rows


def load_il2cpp_control_facts(metadata_path: Path | None) -> dict[str, Any]:
    metadata_path = metadata_path or DEFAULT_METADATA
    if not metadata_path.exists() or not CATALOG_HELPER.exists():
        return {
            "available": False,
            "metadataPath": str(metadata_path),
            "reason": "metadata/helper missing",
        }
    try:
        spec = importlib.util.spec_from_file_location("endfield_il2cpp_catalog", CATALOG_HELPER)
        if spec is None or spec.loader is None:
            raise RuntimeError("could not load catalog helper")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        md = module.Metadata(metadata_path)
    except Exception as exc:  # pragma: no cover - diagnostic path
        return {
            "available": False,
            "metadataPath": str(metadata_path),
            "reason": str(exc),
        }

    wanted_types = [
        "Beyond.Gameplay.LevelData",
        "Beyond.Gameplay.LevelScriptBriefData",
        "Beyond.Gameplay.LevelScriptData",
        "Beyond.Gameplay.Core.LevelScriptContainer",
        "Beyond.Gameplay.Core.LevelScriptRuntime",
        "Beyond.Gameplay.CheckLevelScriptPropertyBool",
        "Beyond.Gameplay.Actions.ManualStartLevelScript",
        "Beyond.Gameplay.Actions.ManualEndLevelScript",
        "Beyond.Gameplay.LevelScriptStartType",
        "Beyond.Gameplay.LevelScriptEndType",
    ]
    type_by_name = {md.type_full_name(type_def): type_def for type_def in md.types}
    facts: dict[str, Any] = {
        "available": True,
        "metadataPath": str(metadata_path),
        "types": {},
    }
    for name in wanted_types:
        type_def = type_by_name.get(name)
        if not type_def:
            facts["types"][name] = {"missing": True}
            continue
        fields = [
            {
                "name": md.string(field.name_index),
                "type": md.metadata_type_name(field.type_index),
            }
            for field in md.fields_for(type_def)
        ]
        methods = [
            md.string(method.name_index)
            for method in md.methods_for(type_def)
        ]
        facts["types"][name] = {
            "index": type_def.index,
            "fields": fields,
            "methods": methods,
        }
    return facts


def summarize_il2cpp_runtime_facts(facts: dict[str, Any]) -> dict[str, Any]:
    if not facts.get("available"):
        return facts
    types = facts.get("types") or {}
    out = {
        "available": True,
        "metadataPath": facts.get("metadataPath"),
        "levelDataFields": [
            row["name"]
            for row in (types.get("Beyond.Gameplay.LevelData") or {}).get("fields", [])
            if row["name"] in {"levelScripts", "levelScriptDataPathDict", "levelScriptBriefDataDict"}
        ],
        "briefFields": [
            row["name"]
            for row in (types.get("Beyond.Gameplay.LevelScriptBriefData") or {}).get("fields", [])
        ],
        "scriptDataFields": [
            row["name"]
            for row in (types.get("Beyond.Gameplay.LevelScriptData") or {}).get("fields", [])
            if row["name"] in {
                "scriptId",
                "startType",
                "endType",
                "activeShapeList",
                "startShapeList",
                "actionMap",
                "taskMap",
                "modules",
                "properties",
                "propertyIdToKeyMap",
                "triggerVolumes",
            }
        ],
        "startTypeEnum": [
            row["name"]
            for row in (types.get("Beyond.Gameplay.LevelScriptStartType") or {}).get("fields", [])
            if row["name"] != "value__"
        ],
        "endTypeEnum": [
            row["name"]
            for row in (types.get("Beyond.Gameplay.LevelScriptEndType") or {}).get("fields", [])
            if row["name"] != "value__"
        ],
        "runtimeMethods": [
            name
            for name in (types.get("Beyond.Gameplay.Core.LevelScriptRuntime") or {}).get("methods", [])
            if name
            in {
                "OnScriptActive",
                "OnScriptStart",
                "ManualStart",
                "ManualEnd",
                "Tick",
                "UpdateRuntimeState",
                "UpdateStage",
                "ServerSyncProperties",
            }
        ],
        "manualStartFields": [
            row["name"]
            for row in (types.get("Beyond.Gameplay.Actions.ManualStartLevelScript") or {}).get("fields", [])
        ],
    }
    return out


def build_report(mission_id: str, *, language: str, metadata_path: Path | None) -> dict[str, Any]:
    mission_path = MISSION_ROOT / f"{mission_id}.json"
    meta_path = MISSION_ROOT / f"{mission_id}_meta.json"
    mission = read_json(mission_path, {})
    meta = read_json(meta_path, {})
    primary_level = (
        ((meta.get("acceptMode") or {}).get("levelId"))
        or meta.get("levelId")
        or mission.get("levelId")
        or ""
    )
    levels = mission_level_ids(mission_id, str(primary_level), language)
    quest_dic = mission.get("questDic") or {}
    quest_order = quest_topo_order(quest_dic) if isinstance(quest_dic, dict) else []
    runtime_conditions = collect_mission_runtime_conditions(mission)
    condition_script_ids = {
        str(row.get("scriptId"))
        for row in runtime_conditions
        if str(row.get("scriptId") or "").isdigit()
    }
    property_keys = {
        str(row.get("key"))
        for row in runtime_conditions
        if row.get("key")
    }

    script_files = collect_script_files(levels)
    ids_by_level = all_numeric_script_ids_by_level(levels)
    story_order_entries = extract_story_order_entries(mission_id)

    script_rows: dict[tuple[str, str], dict[str, Any]] = {}
    relevant_scripts: set[tuple[str, str]] = set()

    for key, file_info in script_files.items():
        level, script_id = key
        story_events = collect_script_story_events(file_info, mission_id)
        levelseqs = collect_levelseq_hits(file_info, mission_id)
        quest_refs = collect_quest_refs(file_info, mission_id)
        property_hits = collect_property_hits(file_info, property_keys)
        if story_events or levelseqs or quest_refs or script_id in condition_script_ids:
            relevant_scripts.add(key)
        if story_events or levelseqs or quest_refs or property_hits or script_id in condition_script_ids:
            record_classes = Counter(
                classify_levelscript_record(record) or "unknown"
                for record in (file_info.get("records") or [])
            )
            chains = _build_uid_record_chains(file_info.get("records") or [])
            script_rows[key] = {
                "levelId": level,
                "scriptId": script_id,
                "file": file_info.get("file"),
                "storyEvents": story_events,
                "storyKeys": unique_preserve([event["key"] for event in story_events]),
                "levelseqs": levelseqs,
                "questRefs": quest_refs,
                "propertyHits": property_hits,
                "recordClassCounts": dict(record_classes),
                "chainCount": len(chains),
                "playChainCount": sum(
                    1
                    for chain in chains
                    if any(classify_levelscript_record(record) in PLAY_RECORD_CLASSES for record in chain)
                ),
                "storyOrderEntries": [
                    story_order_entries.get(event["key"], {})
                    for event in story_events
                    if event["key"] in story_order_entries
                ],
            }

    xrefs = collect_cross_script_refs(script_files, ids_by_level)
    relevant_ids_by_level: dict[str, set[int]] = defaultdict(set)
    for level, script_id in relevant_scripts:
        if script_id.isdigit():
            relevant_ids_by_level[level].add(int(script_id))
    for row in xrefs:
        src = (row["levelId"], row["sourceScript"])
        dst = (row["levelId"], row["targetScript"])
        if src in relevant_scripts or dst in relevant_scripts:
            if row["sourceScript"].isdigit():
                relevant_ids_by_level[row["levelId"]].add(int(row["sourceScript"]))
            if row["targetScript"].isdigit():
                relevant_ids_by_level[row["levelId"]].add(int(row["targetScript"]))
            relevant_scripts.add(src)
            relevant_scripts.add(dst)

    leveldata_refs = collect_leveldata_script_refs(levels, relevant_ids_by_level)
    for row in leveldata_refs:
        relevant_scripts.add((row["levelId"], row["scriptId"]))

    # Backfill rows for scripts that became relevant only through control refs.
    for key in sorted(relevant_scripts, key=lambda item: (item[0], script_id_sort_key(item[1]))):
        if key in script_rows:
            continue
        file_info = script_files.get(key)
        if not file_info:
            continue
        record_classes = Counter(
            classify_levelscript_record(record) or "unknown"
            for record in (file_info.get("records") or [])
        )
        script_rows[key] = {
            "levelId": key[0],
            "scriptId": key[1],
            "file": file_info.get("file"),
            "storyEvents": collect_script_story_events(file_info, mission_id),
            "storyKeys": [],
            "levelseqs": collect_levelseq_hits(file_info, mission_id),
            "questRefs": collect_quest_refs(file_info, mission_id),
            "propertyHits": collect_property_hits(file_info, property_keys),
            "recordClassCounts": dict(record_classes),
            "chainCount": len(_build_uid_record_chains(file_info.get("records") or [])),
            "playChainCount": 0,
            "storyOrderEntries": [],
        }

    outgoing: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    incoming: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in xrefs:
        src = (row["levelId"], row["sourceScript"])
        dst = (row["levelId"], row["targetScript"])
        if src in relevant_scripts or dst in relevant_scripts:
            outgoing[src].append(row)
            incoming[dst].append(row)

    leveldata_by_script: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in leveldata_refs:
        leveldata_by_script[(row["levelId"], row["scriptId"])].append(row)

    conditions_by_script: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in runtime_conditions:
        level = str(row.get("mapId") or primary_level or "")
        script_id = str(row.get("scriptId") or "")
        if level and script_id:
            conditions_by_script[(level, script_id)].append(row)

    scripts_out: list[dict[str, Any]] = []
    for key in sorted(script_rows, key=lambda item: (item[0], script_id_sort_key(item[1]))):
        row = dict(script_rows[key])
        row["missionRuntimeConditions"] = conditions_by_script.get(key, [])
        row["levelDataRefs"] = leveldata_by_script.get(key, [])
        row["outgoingScriptRefs"] = sorted(
            outgoing.get(key, []),
            key=lambda item: (script_id_sort_key(item["targetScript"]), int(item["offset"])),
        )
        row["incomingScriptRefs"] = sorted(
            incoming.get(key, []),
            key=lambda item: (script_id_sort_key(item["sourceScript"]), int(item["offset"])),
        )
        tags: list[str] = []
        if row["missionRuntimeConditions"]:
            tags.append("direct-mission-runtime-condition")
        if row["levelDataRefs"]:
            tags.append("leveldata-script-reference")
        if row["storyEvents"]:
            tags.append("plays-story-payloads")
        if row["levelseqs"]:
            tags.append("plays-levelseq")
        if row["questRefs"]:
            tags.append("embeds-quest-ref")
        if row["incomingScriptRefs"] or row["outgoingScriptRefs"]:
            tags.append("cross-script-ref")
        contexts = [
            ctx.get("text")
            for ref in row["levelDataRefs"]
            for ctx in (ref.get("context") or [])
        ]
        if "preloaded" in contexts:
            tags.append("leveldata-preload-context")
        if any("spawn" in str(text).lower() or "teleport" in str(text).lower() for text in contexts):
            tags.append("spawn-teleport-context")
        row["controlTags"] = tags
        row["startDecodeStatus"] = (
            "runtime fields confirmed by IL2CPP, but startType/endType bytes are not decoded from this binary yet"
        )
        scripts_out.append(row)

    il2cpp_facts = summarize_il2cpp_runtime_facts(load_il2cpp_control_facts(metadata_path))

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "mission": mission_id,
        "language": language,
        "levels": levels,
        "summary": {
            "questCount": len(quest_order),
            "runtimeConditionCount": len(runtime_conditions),
            "scriptCount": len(scripts_out),
            "scriptsWithStoryPayloads": sum(1 for row in scripts_out if row.get("storyEvents")),
            "scriptsWithLevelDataRefs": sum(1 for row in scripts_out if row.get("levelDataRefs")),
            "crossScriptRefCount": sum(
                len(row.get("outgoingScriptRefs") or [])
                for row in scripts_out
            ),
            "levelDataRefCount": sum(len(row.get("levelDataRefs") or []) for row in scripts_out),
        },
        "missionRuntime": {
            "file": repo_rel(mission_path),
            "metaFile": repo_rel(meta_path),
            "primaryLevel": primary_level,
            "questOrder": quest_order,
            "propertyIdToKeyMap": mission.get("propertyIdToKeyMap") or {},
            "conditions": runtime_conditions,
            "actionMapRawActionCount": len((((mission.get("actionMapRaw") or {}).get("dataMap") or {}).get("actionList") or [])),
        },
        "il2cppControlFacts": il2cpp_facts,
        "scripts": scripts_out,
    }


def short_list(values: list[Any], limit: int = 5) -> str:
    items = [str(v) for v in values if v not in (None, "")]
    if len(items) > limit:
        items = items[:limit] + [f"+{len(values) - limit} more"]
    return ", ".join(items)


def context_summary(refs: list[dict[str, Any]], limit: int = 6) -> str:
    values: list[str] = []
    for ref in refs:
        for ctx in ref.get("context") or []:
            text = str(ctx.get("text") or "")
            if text and text not in values:
                values.append(text)
    return short_list(values, limit)


def markdown_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        f"# {payload['mission']} LevelScript Control Audit",
        "",
        f"Generated: {payload['generatedAt']}",
        "",
        "## Summary",
        "",
        f"- Levels inspected: `{', '.join(payload.get('levels') or [])}`",
        f"- Quests: `{summary['questCount']}`",
        f"- MissionRuntime LevelScript conditions: `{summary['runtimeConditionCount']}`",
        f"- Relevant scripts: `{summary['scriptCount']}`",
        f"- Scripts with story payloads: `{summary['scriptsWithStoryPayloads']}`",
        f"- Scripts with LevelData refs: `{summary['scriptsWithLevelDataRefs']}`",
        f"- LevelData script-id refs: `{summary['levelDataRefCount']}`",
        f"- Cross-script refs: `{summary['crossScriptRefCount']}`",
        "",
        "This report is control evidence, not a total play-order proof. LevelData",
        "ownership and cross-script references are useful, but they stay weaker",
        "than an explicit MissionRuntime condition until start/end/action opcodes",
        "are decoded.",
        "",
        "## Runtime Facts",
        "",
    ]

    facts = payload.get("il2cppControlFacts") or {}
    if facts.get("available"):
        lines.extend([
            f"- Metadata: `{md_escape(facts.get('metadataPath'))}`",
            f"- LevelData fields: `{md_escape(', '.join(facts.get('levelDataFields') or []))}`",
            f"- LevelScriptBriefData fields: `{md_escape(', '.join((facts.get('briefFields') or [])[:8]))}`",
            f"- LevelScriptData control fields: `{md_escape(', '.join(facts.get('scriptDataFields') or []))}`",
            f"- StartType enum: `{md_escape(', '.join(facts.get('startTypeEnum') or []))}`",
            f"- EndType enum: `{md_escape(', '.join(facts.get('endTypeEnum') or []))}`",
            f"- Runtime methods: `{md_escape(', '.join(facts.get('runtimeMethods') or []))}`",
            f"- ManualStartLevelScript fields: `{md_escape(', '.join(facts.get('manualStartFields') or []))}`",
        ])
    else:
        lines.append(f"- Metadata unavailable: `{md_escape(facts.get('reason'))}`")

    mission_runtime = payload.get("missionRuntime") or {}
    lines.extend([
        "",
        "## MissionRuntime",
        "",
        f"- Primary level: `{md_escape(mission_runtime.get('primaryLevel'))}`",
        f"- actionMapRaw action count: `{mission_runtime.get('actionMapRawActionCount')}`",
        f"- Quest order: `{md_escape(' -> '.join(mission_runtime.get('questOrder') or []))}`",
        f"- propertyIdToKeyMap: `{md_escape(mission_runtime.get('propertyIdToKeyMap'))}`",
        "",
    ])
    conditions = mission_runtime.get("conditions") or []
    if conditions:
        lines.extend([
            "| quest | type | map | script | key | value |",
            "| --- | --- | --- | --- | --- | --- |",
        ])
        for row in conditions:
            lines.append(
                "| "
                f"`{md_escape(row.get('questId'))}` "
                f"| `{md_escape(row.get('type'))}` "
                f"| `{md_escape(row.get('mapId'))}` "
                f"| `{md_escape(row.get('scriptId'))}` "
                f"| `{md_escape(row.get('key'))}` "
                f"| `{md_escape(row.get('value'))}` |"
            )
    else:
        lines.append("- No MissionRuntime LevelScript conditions found.")

    lines.extend([
        "",
        "## Script Control Matrix",
        "",
        "| level | script | tags | story keys | levelseqs | MissionRuntime | LevelData context | xrefs |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in payload.get("scripts") or []:
        story_keys = short_list(row.get("storyKeys") or [event.get("key") for event in row.get("storyEvents") or []], 5)
        levelseqs = short_list([item.get("text") for item in row.get("levelseqs") or []], 4)
        conditions_text = short_list(
            [
                f"{condition.get('questId')}:{condition.get('key')}"
                for condition in row.get("missionRuntimeConditions") or []
            ],
            3,
        )
        xref_count = len(row.get("outgoingScriptRefs") or []) + len(row.get("incomingScriptRefs") or [])
        lines.append(
            "| "
            f"`{md_escape(row.get('levelId'))}` "
            f"| `{md_escape(row.get('scriptId'))}` "
            f"| `{md_escape(', '.join(row.get('controlTags') or []))}` "
            f"| {md_escape(story_keys)} "
            f"| {md_escape(levelseqs)} "
            f"| {md_escape(conditions_text)} "
            f"| {md_escape(context_summary(row.get('levelDataRefs') or []))} "
            f"| {xref_count} |"
        )

    lines.extend([
        "",
        "## LevelData References",
        "",
    ])
    wrote_leveldata = False
    for row in payload.get("scripts") or []:
        refs = row.get("levelDataRefs") or []
        if not refs:
            continue
        wrote_leveldata = True
        lines.append(f"- `{md_escape(row.get('levelId'))}/{md_escape(row.get('scriptId'))}`")
        for ref in refs[:12]:
            context = ", ".join(
                f"{ctx.get('delta'):+d}:{md_escape(ctx.get('text'))}"
                for ctx in (ref.get("context") or [])[:8]
            )
            lines.append(
                f"  - `{md_escape(ref.get('file'))}` @0x{int(ref.get('offset') or 0):x}: {context}"
            )
        if len(refs) > 12:
            lines.append(f"  - ... +{len(refs) - 12} more")
    if not wrote_leveldata:
        lines.append("- _(none)_")

    lines.extend([
        "",
        "## Cross-Script References",
        "",
    ])
    wrote_xrefs = False
    for row in payload.get("scripts") or []:
        refs = row.get("outgoingScriptRefs") or []
        if not refs:
            continue
        wrote_xrefs = True
        lines.append(f"- `{md_escape(row.get('levelId'))}/{md_escape(row.get('scriptId'))}`")
        for ref in refs[:12]:
            record = ref.get("record") or {}
            strings = short_list([*(record.get("strings") or []), *(record.get("plainStrings") or [])], 4)
            lines.append(
                "  - "
                f"-> `{md_escape(ref.get('targetScript'))}` @0x{int(ref.get('offset') or 0):x} "
                f"record `{md_escape(record.get('code'))}/{md_escape(record.get('kind'))}` "
                f"class=`{md_escape(record.get('class'))}` strings=`{md_escape(strings)}`"
            )
        if len(refs) > 12:
            lines.append(f"  - ... +{len(refs) - 12} more")
    if not wrote_xrefs:
        lines.append("- _(none)_")

    lines.extend([
        "",
        "## Story Payloads By Script",
        "",
    ])
    for row in payload.get("scripts") or []:
        events = row.get("storyEvents") or []
        if not events:
            continue
        lines.append(f"- `{md_escape(row.get('levelId'))}/{md_escape(row.get('scriptId'))}`")
        for event in events[:24]:
            record = event.get("record") or {}
            lines.append(
                "  - "
                f"@0x{int(event.get('offset') or 0):x} `{md_escape(event.get('key'))}` "
                f"payload=`{md_escape(event.get('payload'))}` "
                f"record=`{md_escape(record.get('code'))}/{md_escape(record.get('kind'))}` "
                f"class=`{md_escape(record.get('class'))}`"
            )
        if len(events) > 24:
            lines.append(f"  - ... +{len(events) - 24} more")

    lines.extend([
        "",
        "## Next Decode Targets",
        "",
        "- Decode LevelScriptData `startType` / `endType` and shape-list bytes from the tail of each binary.",
        "- Identify opcode `0x0455/0x0a` and other records that wrap script-id references.",
        "- Decode `ManualStartLevelScript` / `ManualEndLevelScript` action nodes so cross-script refs can become directed edges.",
        "- Promote only directed start/gate evidence into `story_order.json`; keep LevelData context visible but non-ordering until then.",
    ])
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mission", default="e0m0")
    parser.add_argument("--language", default="CN")
    parser.add_argument("--reports-dir", type=Path, default=ROOT / "reports" / "mission_order")
    parser.add_argument("--metadata", type=Path, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    payload = build_report(args.mission, language=args.language, metadata_path=args.metadata)
    json_path = args.reports_dir / f"{args.mission}_levelscript_control_audit.json"
    md_path = args.reports_dir / f"{args.mission}_levelscript_control_audit.md"
    write_json(json_path, payload)
    write_text_if_changed(md_path, markdown_report(payload))
    print(
        f"{args.mission}: scripts={payload['summary']['scriptCount']} "
        f"levelDataRefs={payload['summary']['levelDataRefCount']} "
        f"xrefs={payload['summary']['crossScriptRefCount']} -> {repo_rel(md_path)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
