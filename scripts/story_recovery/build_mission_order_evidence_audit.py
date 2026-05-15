#!/usr/bin/env python3
"""Audit original-data clues for in-mission story file ordering."""
from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
import re
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (_REPO_ROOT / "scripts",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from common import (  # noqa: E402
    EXPORT_ROOT,
    ROOT,
    md_escape,
    read_json,
    rel_path,
    safe_key,
    unique_preserve,
    write_report_json,
    write_text_if_changed,
)
from story_builder.level_bindings import _load_levelscript_binding_data  # noqa: E402


ORDER_KINDS = {"dlg", "sns", "cutscene", "black", "remotecomm", "radio", "video"}
TABLE_ROOT = EXPORT_ROOT / "structured" / "StreamingAssets" / "Table"
DATA_JSON_ROOT = EXPORT_ROOT / "structured" / "StreamingAssets" / "Data" / "Json"
ASSET_MAP = (
    EXPORT_ROOT
    / "recovered"
    / "AnimeStudio-cli"
    / "StreamingAssets"
    / "maps"
    / "endfield_streamingassets_assets.json"
)
MAP_TABLES = (
    TABLE_ROOT / "MapMarkInsTable.json",
    TABLE_ROOT / "MapMarkTempTable.json",
    TABLE_ROOT / "TrackMapPointTable.json",
    TABLE_ROOT / "TrackMapLinkTable.json",
    TABLE_ROOT / "SceneAreaTable.json",
    TABLE_ROOT / "SceneCollectableItemTable.json",
)
PLAYABLE_DIRECTOR_BRIDGE_PATH = (
    ROOT / "reports" / "playable_director" / "playable_director_bridge.json"
)


def status_for(entry: dict[str, Any]) -> str:
    if entry.get("goStrong"):
        return "strong"
    if entry.get("goWeak"):
        return "weak"
    return "unknown"


def entry_index_tail(entry: dict[str, Any]) -> str:
    key = safe_key(entry.get("k"))
    normalized = key[5:] if key.startswith("misc_") else key
    mission = safe_key(entry.get("m"))
    if mission:
        marker = f"_{mission}_".lower()
        index = normalized.lower().rfind(marker)
        if index >= 0:
            return normalized[index + len(marker) :]
    parts = [part for part in normalized.split("_") if part]
    return parts[-1] if parts else normalized


def entry_index_number(entry: dict[str, Any]) -> float:
    tail = entry_index_tail(entry)

    def parse(match: re.Match[str] | None) -> float | None:
        if not match:
            return None
        whole = int(match.group(1))
        decimal = int(match.group(2) or "0")
        return whole + decimal / 1_000_000

    value = parse(re.match(r"^(\d+)(?:d(\d+))?", tail, re.I))
    if value is not None:
        return value
    matches = list(re.finditer(r"(\d+)(?:d(\d+))?", tail, re.I))
    value = parse(matches[-1]) if matches else None
    return value if value is not None else 10**9


def entry_sort_key(entry: dict[str, Any]) -> tuple[float, float, str]:
    status = status_for(entry)
    graph_order = entry.get("go")
    if status != "unknown" and isinstance(graph_order, (int, float)):
        return (0, float(graph_order), safe_key(entry.get("k")))
    return (1, entry_index_number(entry), safe_key(entry.get("k")))


def aliases_for_key(key: str) -> list[str]:
    aliases = {key}
    if key.startswith("misc_"):
        aliases.add(key[5:])
    return sorted(aliases, key=len, reverse=True)


def walk_string_hits(
    node: Any,
    needles: dict[str, list[str]],
    *,
    path: str = "$",
    limit_per_key: int = 10,
) -> tuple[Counter[str], dict[str, list[dict[str, Any]]]]:
    hits: dict[str, list[dict[str, Any]]] = defaultdict(list)
    counts: Counter[str] = Counter()

    def add(text: str, where: str) -> None:
        if not text:
            return
        for key, aliases in needles.items():
            if any(alias and alias in text for alias in aliases):
                counts[key] += 1
                if len(hits[key]) < limit_per_key:
                    hits[key].append({"path": where, "text": text[:240]})

    def walk(value: Any, where: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{where}.{key}" if where else str(key)
                add(str(key), child_path + ".__key__")
                walk(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{where}[{index}]")
        elif isinstance(value, str):
            add(value, where)

    walk(node, path)
    return counts, hits


def mission_report_entry(mission: str, language: str, reports_dir: Path) -> dict[str, Any] | None:
    path = reports_dir / f"mission_timeline_recovery_{language}.json"
    payload = read_json(path, {})
    for entry in payload.get("missions") or []:
        if entry.get("mission") == mission:
            return entry
    return None


def add_level(level_ids: list[str], value: Any) -> None:
    level_id = safe_key(value)
    if level_id and level_id not in level_ids:
        level_ids.append(level_id)


def collect_level_ids(
    mission: str,
    mission_runtime: dict[str, Any],
    webui_mission: dict[str, Any],
    mission_timeline: dict[str, Any] | None,
) -> list[str]:
    level_ids: list[str] = []
    add_level(level_ids, mission_runtime.get("levelId"))
    for quest in webui_mission.get("flow", {}).get("quests") or []:
        for scene in quest.get("scenes") or []:
            add_level(level_ids, scene)
    if mission_timeline:
        for scene in mission_timeline.get("referencedScenes") or []:
            add_level(level_ids, scene)
    for path in (DATA_JSON_ROOT / "LevelData").glob(f"*/*{mission}*"):
        add_level(level_ids, path.parent.name)
    return level_ids


def unwrap_const(value: Any) -> Any:
    if isinstance(value, dict) and "constValue" in value:
        return value.get("constValue")
    return value


def collect_mission_runtime_script_conditions(node: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    def walk(value: Any, path: str, quest_id: str = "") -> None:
        if isinstance(value, dict):
            next_quest_id = quest_id
            if isinstance(value.get("questId"), str):
                next_quest_id = value["questId"]
            type_name = safe_key(value.get("$type"))
            has_script_id = "_scriptId" in value
            if "LevelScript" in type_name or has_script_id:
                script_value = unwrap_const(value.get("_scriptId", value.get("scriptId")))
                if isinstance(script_value, dict):
                    script_id = script_value.get("scriptId")
                else:
                    script_id = script_value
                condition = {
                    "path": path,
                    "questId": next_quest_id,
                    "type": type_name,
                    "uniqueId": safe_key(value.get("uniqueId")),
                    "mapId": unwrap_const(value.get("_mapId", value.get("mapId"))),
                    "scriptId": script_id,
                    "key": unwrap_const(value.get("_key", value.get("key"))),
                    "value": unwrap_const(value.get("_value", value.get("value"))),
                    "comparer": unwrap_const(value.get("_comparer", value.get("comparer"))),
                }
                out.append({key: val for key, val in condition.items() if val not in (None, "", {})})
            for key, child in value.items():
                walk(child, f"{path}.{key}", next_quest_id)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]", quest_id)

    walk(node, "$")
    return out


def collect_levelscript_hits(
    mission: str,
    level_ids: list[str],
    needles: dict[str, list[str]],
) -> tuple[list[dict[str, Any]], Counter[str], dict[str, list[dict[str, Any]]]]:
    files: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    examples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for level_id in level_ids:
        try:
            info = _load_levelscript_binding_data(level_id)
        except Exception as exc:  # pragma: no cover - defensive report path
            files.append({"levelId": level_id, "error": str(exc)})
            continue
        for file_info in info.get("files") or []:
            matched: list[dict[str, Any]] = []
            raw_mission_hits: list[dict[str, Any]] = []
            for hit in file_info.get("stringHits") or []:
                text = safe_key(hit.get("text"))
                if mission in text:
                    raw_mission_hits.append({"offset": hit.get("offset"), "text": text})
                matched_key = ""
                for key, aliases in needles.items():
                    if text in aliases:
                        matched_key = key
                        break
                if not matched_key:
                    continue
                matched.append({"offset": hit.get("offset"), "key": matched_key, "text": text})
                counts[matched_key] += 1
                if len(examples[matched_key]) < 6:
                    examples[matched_key].append({
                        "levelId": level_id,
                        "file": file_info.get("file"),
                        "offset": hit.get("offset"),
                        "text": text,
                    })
            if matched or raw_mission_hits:
                files.append({
                    "levelId": level_id,
                    "file": file_info.get("file"),
                    "matchedSequence": matched,
                    "matchedUniqueKeys": unique_preserve(item["key"] for item in matched),
                    "rawMissionHitCount": len(raw_mission_hits),
                    "rawMissionHits": raw_mission_hits[:40],
                })
    return files, counts, examples


def text_snippet(raw: bytes, index: int, length: int, radius: int = 48) -> str:
    start = max(0, index - radius)
    end = min(len(raw), index + length + radius)
    return raw[start:end].decode("utf-8", errors="ignore").replace("\x00", "")


def collect_leveldata_hits(
    mission: str,
    level_ids: list[str],
    needles: dict[str, list[str]],
) -> tuple[list[dict[str, Any]], Counter[str], dict[str, list[dict[str, Any]]]]:
    files: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    examples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    root = DATA_JSON_ROOT / "LevelData"
    for level_id in level_ids:
        level_dir = root / level_id
        if not level_dir.exists():
            continue
        for path in sorted(item for item in level_dir.rglob("*") if item.is_file()):
            try:
                raw = path.read_bytes()
            except OSError:
                continue
            raw_mission_count = raw.count(mission.encode("utf-8"))
            matched: list[dict[str, Any]] = []
            for key, aliases in needles.items():
                key_hits = 0
                for alias in aliases:
                    alias_raw = alias.encode("utf-8")
                    search_from = 0
                    while True:
                        index = raw.find(alias_raw, search_from)
                        if index < 0:
                            break
                        search_from = index + max(1, len(alias_raw))
                        key_hits += 1
                        if len(examples[key]) < 4:
                            examples[key].append({
                                "levelId": level_id,
                                "file": rel_path(path),
                                "offset": index,
                                "text": text_snippet(raw, index, len(alias_raw)),
                            })
                        if len([item for item in matched if item.get("key") == key]) < 4:
                            matched.append({
                                "offset": index,
                                "key": key,
                                "alias": alias,
                                "text": text_snippet(raw, index, len(alias_raw)),
                            })
                if key_hits:
                    counts[key] += key_hits
            if matched or raw_mission_count:
                files.append({
                    "levelId": level_id,
                    "file": rel_path(path),
                    "matchedSequence": sorted(matched, key=lambda item: item.get("offset") or 0),
                    "matchedUniqueKeys": unique_preserve(item["key"] for item in matched),
                    "rawMissionHitCount": raw_mission_count,
                })
    return files, counts, examples


def collect_audio_hits(
    mission: str,
    keys: list[str],
    needles: dict[str, list[str]],
    entry_report: dict[str, dict[str, Any]],
) -> None:
    radio_data = read_json(TABLE_ROOT / "RadioTable.json", {})
    for key in keys:
        if not key.startswith("radio_") or key not in radio_data:
            continue
        row = radio_data[key]
        lines = row.get("radioSingleDataList") or []
        entry_report[key]["hits"]["radioTable"] = {
            "priority": row.get("priority"),
            "radioType": row.get("radioType"),
            "continueAfterDialog": row.get("continueAfterDialog"),
            "continueAfterRadio": row.get("continueAfterRadio"),
            "lineCount": len(lines),
            "indexes": [line.get("index") for line in lines[:12]],
            "audioOverrides": [
                line.get("audioOverride") for line in lines[:6] if line.get("audioOverride")
            ],
        }

    audio_data = read_json(TABLE_ROOT / "AudioDialog.json", {})
    audio_counts: Counter[str] = Counter()
    audio_examples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for audio_key, row in audio_data.items():
        path = safe_key(row.get("path"))
        if mission not in path:
            continue
        for key, aliases in needles.items():
            if any(alias and alias in path for alias in aliases):
                audio_counts[key] += 1
                if len(audio_examples[key]) < 6:
                    audio_examples[key].append({
                        "audioTableKey": audio_key,
                        "path": path,
                        "speakerChannel": row.get("speakerChannel"),
                        "wavDuration": row.get("wavDuration"),
                    })
    for key, count in audio_counts.items():
        entry_report[key]["hits"]["audioDialog"] = {
            "count": count,
            "examples": audio_examples[key],
        }

    sequence_data = read_json(TABLE_ROOT / "AudioSequenceDialog.json", {})
    seq_counts, seq_hits = walk_string_hits(
        sequence_data,
        needles,
        path=rel_path(TABLE_ROOT / "AudioSequenceDialog.json"),
        limit_per_key=4,
    )
    for key, count in seq_counts.items():
        entry_report[key]["hits"]["audioSequenceDialog"] = {
            "count": count,
            "examples": seq_hits[key],
        }


def collect_map_hits(mission: str, level_ids: list[str]) -> list[dict[str, Any]]:
    needles = {mission: [mission], **{level_id: [level_id] for level_id in level_ids}}
    out: list[dict[str, Any]] = []
    for path in MAP_TABLES:
        if not path.exists():
            continue
        counts, hits = walk_string_hits(
            read_json(path, {}),
            needles,
            path=rel_path(path),
            limit_per_key=5,
        )
        if sum(counts.values()):
            out.append({
                "file": rel_path(path),
                "counts": dict(counts),
                "examples": {key: value for key, value in hits.items() if value},
            })
    return out


def collect_asset_map_counts(
    keys: list[str],
    entry_report: dict[str, dict[str, Any]],
    *,
    asset_map: Path,
    chunk_size: int = 1024 * 1024,
) -> None:
    if not asset_map.exists():
        return
    scan_keys = [key for key in keys if entry_report[key]["status"] != "strong"]
    encoded = {key: key.encode("utf-8") for key in scan_keys}
    max_len = max((len(value) for value in encoded.values()), default=0)
    counts: Counter[str] = Counter()
    carry = b""
    with asset_map.open("rb") as stream:
        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            data = carry + chunk
            for key, raw in encoded.items():
                count = data.count(raw)
                if count:
                    counts[key] += count
            carry = data[-max_len:] if max_len else b""
    for key, count in counts.items():
        entry_report[key]["hits"]["assetMapString"] = {
            "count": count,
            "source": rel_path(asset_map),
            "note": "String occurrence in AssetMap; validates asset family, not chronology.",
        }


def collect_playable_director_hits(
    mission: str,
    entry_report: dict[str, dict[str, Any]],
    bridge_path: Path = PLAYABLE_DIRECTOR_BRIDGE_PATH,
) -> int:
    """Add `hits.playableDirector` from the PlayableDirector bridge report.

    Returns the number of entries that gained a PlayableDirector anchor.
    Silent no-op when the bridge report has not been generated yet.
    """
    if not bridge_path.exists():
        return 0
    try:
        bridge = read_json(bridge_path, {})
    except Exception:  # noqa: BLE001 - defensive against partial writes
        return 0
    stories = bridge.get("stories") or []
    by_lower_name: dict[str, dict[str, Any]] = {}
    for story in stories:
        name = (story.get("storyName") or "").lower()
        if not name:
            continue
        # Restrict to this mission so the audit is bounded.
        if (story.get("mission") or "") != mission:
            continue
        by_lower_name[name] = story
    if not by_lower_name:
        return 0
    anchored = 0
    for key, info in entry_report.items():
        normalized = key[5:] if key.startswith("misc_") else key
        story = by_lower_name.get(normalized.lower())
        if not story:
            continue
        info["hits"]["playableDirector"] = {
            "matchedStoryName": story.get("storyName"),
            "directorCount": story.get("playableDirectorCount"),
            "totalBindings": story.get("totalBindings"),
            "timelineNames": (story.get("timelineNames") or [])[:3],
            "trackTypeCounts": story.get("trackTypeCounts") or {},
            "sourceReport": str(bridge_path.relative_to(ROOT)).replace("\\", "/"),
        }
        anchored += 1
    return anchored


def build_report(
    mission: str,
    *,
    language: str,
    reports_dir: Path,
    include_asset_map: bool,
) -> dict[str, Any]:
    index_path = ROOT / "webui" / "data" / "lang" / language / "index.json"
    webui_mission_path = ROOT / "webui" / "data" / "lang" / language / "mission" / f"{mission}.json"
    mission_runtime_path = DATA_JSON_ROOT / "MissionRuntimeAsset" / f"{mission}.json"
    mission_timeline_path = reports_dir / f"mission_timeline_recovery_{language}.json"

    index_payload = read_json(index_path, {})
    entries = [
        entry
        for entry in index_payload.get("entries", [])
        if entry.get("m") == mission and entry.get("d") in ORDER_KINDS
    ]
    entries.sort(key=entry_sort_key)
    keys = [entry["k"] for entry in entries]
    needles = {key: aliases_for_key(key) for key in keys}

    entry_report: dict[str, dict[str, Any]] = {}
    for entry in entries:
        key = entry["k"]
        entry_report[key] = {
            "kind": entry.get("d"),
            "status": status_for(entry),
            "graphOrder": entry.get("go"),
            "fallbackTail": entry_index_tail(entry),
            "fallbackNumber": entry_index_number(entry),
            "hits": {},
        }

    mission_runtime = read_json(mission_runtime_path, {})
    runtime_script_conditions = collect_mission_runtime_script_conditions(mission_runtime)
    mission_counts, mission_hits = walk_string_hits(
        mission_runtime,
        needles,
        path=rel_path(mission_runtime_path),
    )
    for key, count in mission_counts.items():
        entry_report[key]["hits"]["missionRuntime"] = {
            "count": count,
            "examples": mission_hits[key],
        }

    mission_timeline = mission_report_entry(mission, language, reports_dir)
    webui_mission = read_json(webui_mission_path, {})
    level_ids = collect_level_ids(mission, mission_runtime, webui_mission, mission_timeline)
    levelscript_files, levelscript_counts, levelscript_examples = collect_levelscript_hits(
        mission,
        level_ids,
        needles,
    )
    levelscript_by_level_script: dict[tuple[str, str], dict[str, Any]] = {}
    for item in levelscript_files:
        level_id = safe_key(item.get("levelId"))
        file_name = Path(safe_key(item.get("file"))).stem
        if level_id and file_name:
            levelscript_by_level_script[(level_id, file_name)] = item
    for condition in runtime_script_conditions:
        level_id = safe_key(condition.get("mapId"))
        script_id = safe_key(condition.get("scriptId"))
        file_info = levelscript_by_level_script.get((level_id, script_id))
        if file_info:
            condition["matchedLevelScriptFile"] = file_info.get("file")
            condition["matchedStoryKeys"] = file_info.get("matchedUniqueKeys") or []
    for key, count in levelscript_counts.items():
        entry_report[key]["hits"]["levelScriptData"] = {
            "count": count,
            "examples": levelscript_examples[key],
        }

    leveldata_files, leveldata_counts, leveldata_examples = collect_leveldata_hits(
        mission,
        level_ids,
        needles,
    )
    for key, count in leveldata_counts.items():
        entry_report[key]["hits"]["levelData"] = {
            "count": count,
            "examples": leveldata_examples[key],
            "note": "Byte-string hit in LevelData; useful trigger/spatial context, not chronology alone.",
        }

    collect_audio_hits(mission, keys, needles, entry_report)
    map_table_hits = collect_map_hits(mission, level_ids)
    if include_asset_map:
        collect_asset_map_counts(keys, entry_report, asset_map=ASSET_MAP)
    playable_director_anchored = collect_playable_director_hits(mission, entry_report)

    status_counts = Counter(value["status"] for value in entry_report.values())
    weak_or_unknown = [key for key, value in entry_report.items() if value["status"] != "strong"]
    no_mission_or_levelscript = [
        key
        for key in weak_or_unknown
        if not (
            entry_report[key]["hits"].get("missionRuntime")
            or entry_report[key]["hits"].get("levelScriptData")
        )
    ]
    weak_or_unknown_anchored_by_pd = [
        key
        for key in weak_or_unknown
        if entry_report[key]["hits"].get("playableDirector")
    ]

    return {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "language": language,
        "mission": mission,
        "sourceFiles": {
            "webuiIndex": rel_path(index_path),
            "webuiMission": rel_path(webui_mission_path),
            "missionRuntime": rel_path(mission_runtime_path),
            "missionTimelineRecovery": rel_path(mission_timeline_path),
            "radioTable": rel_path(TABLE_ROOT / "RadioTable.json"),
            "audioDialog": rel_path(TABLE_ROOT / "AudioDialog.json"),
            "assetMap": rel_path(ASSET_MAP),
        },
        "summary": {
            "entryCount": len(entries),
            "statusCounts": dict(status_counts),
            "levelIdsInspected": level_ids,
            "missionRuntimeScriptConditionCount": len(runtime_script_conditions),
            "levelScriptFilesWithMissionHits": len(levelscript_files),
            "levelDataFilesWithMissionHits": len(leveldata_files),
            "weakOrUnknownCount": len(weak_or_unknown),
            "weakOrUnknownWithNoMissionOrLevelScriptHits": no_mission_or_levelscript,
            "weakOrUnknownWithNoMissionLevelScriptOrLevelDataHits": [
                key
                for key in no_mission_or_levelscript
                if not entry_report[key]["hits"].get("levelData")
            ],
            "playableDirectorAnchoredCount": playable_director_anchored,
            "weakOrUnknownGainingPlayableDirectorAnchor": weak_or_unknown_anchored_by_pd,
        },
        "missionTimeline": {
            "propertyModel": (mission_timeline or {}).get("propertyModel"),
            "questEdges": (mission_timeline or {}).get("questEdges") or [],
            "sourceBackedSceneEdges": (mission_timeline or {}).get("sourceBackedSceneEdges") or [],
            "sourceBackedSceneSequences": (mission_timeline or {}).get("sourceBackedSceneSequences") or [],
            "sourceBackedHashTerminals": (mission_timeline or {}).get("sourceBackedHashTerminals") or [],
            "unresolved": (mission_timeline or {}).get("unresolved") or [],
        },
        "missionRuntimeScriptConditions": runtime_script_conditions,
        "levelScriptFiles": levelscript_files,
        "levelDataFiles": leveldata_files,
        "mapTableHits": map_table_hits,
        "entries": entry_report,
    }


def markdown_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        f"# {payload['mission']} Mission Order Evidence Audit",
        "",
        f"Generated: {payload['generated']}",
        "",
        "## Summary",
        "",
        f"- Entries: {summary['entryCount']}",
        "- Status counts: "
        + ", ".join(f"{key}={value}" for key, value in sorted(summary["statusCounts"].items())),
        "- Level ids inspected: " + ", ".join(summary["levelIdsInspected"]),
        f"- MissionRuntime script conditions: {summary['missionRuntimeScriptConditionCount']}",
        f"- LevelScript files with mission hits: {summary['levelScriptFilesWithMissionHits']}",
        f"- LevelData files with mission hits: {summary['levelDataFilesWithMissionHits']}",
        "- Weak/unknown entries with no MissionRuntime/LevelScript hits: "
        f"{len(summary['weakOrUnknownWithNoMissionOrLevelScriptHits'])}",
        "- Weak/unknown entries with no MissionRuntime/LevelScript/LevelData hits: "
        f"{len(summary['weakOrUnknownWithNoMissionLevelScriptOrLevelDataHits'])}",
        "- Entries with PlayableDirector anchor: "
        f"{summary.get('playableDirectorAnchoredCount', 0)} "
        f"(weak/unknown newly anchored: "
        f"{len(summary.get('weakOrUnknownGainingPlayableDirectorAnchor', []))})",
        "",
        "## Entry Evidence",
        "",
        "| key | status | go | fallback | MissionRuntime | LevelScript | LevelData | Radio | Audio | AssetMap | PlayDir |",
        "| --- | --- | ---: | --- | ---: | ---: | ---: | --- | ---: | ---: | --- |",
    ]
    for key, info in payload["entries"].items():
        hits = info["hits"]
        radio = hits.get("radioTable")
        radio_text = ""
        if radio:
            radio_text = f"p{radio.get('priority')}/t{radio.get('radioType')}/n{radio.get('lineCount')}"
        play_dir = hits.get("playableDirector")
        play_dir_text = ""
        if play_dir:
            play_dir_text = (
                f"d{play_dir.get('directorCount', 0)}"
                f"/b{play_dir.get('totalBindings', 0)}"
            )
        graph_order = info.get("graphOrder")
        lines.append(
            "| "
            f"`{md_escape(key)}` "
            f"| {md_escape(info.get('status'))} "
            f"| {graph_order if graph_order is not None else ''} "
            f"| {md_escape(info.get('fallbackTail'))} "
            f"| {hits.get('missionRuntime', {}).get('count', 0)} "
            f"| {hits.get('levelScriptData', {}).get('count', 0)} "
            f"| {hits.get('levelData', {}).get('count', 0)} "
            f"| {md_escape(radio_text)} "
            f"| {hits.get('audioDialog', {}).get('count', 0)} "
            f"| {hits.get('assetMapString', {}).get('count', 0)} "
            f"| {md_escape(play_dir_text)} |"
        )

    lines.extend(["", "## LevelScript Sequences", ""])
    wrote_sequence = False
    for item in payload["levelScriptFiles"]:
        sequence = item.get("matchedSequence") or []
        if not sequence:
            continue
        wrote_sequence = True
        text = " -> ".join(md_escape(hit.get("key")) for hit in sequence)
        lines.append(f"- `{md_escape(item.get('levelId'))}` `{md_escape(item.get('file'))}`: {text}")
    if not wrote_sequence:
        lines.append("- _(none)_")

    lines.extend(["", "## MissionRuntime Script Conditions", ""])
    if payload.get("missionRuntimeScriptConditions"):
        lines.append("| quest | type | map | script | key | value | matched story keys |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")
        for item in payload["missionRuntimeScriptConditions"]:
            lines.append(
                "| "
                f"`{md_escape(item.get('questId'))}` "
                f"| `{md_escape(item.get('type'))}` "
                f"| `{md_escape(item.get('mapId'))}` "
                f"| `{md_escape(item.get('scriptId'))}` "
                f"| `{md_escape(item.get('key'))}` "
                f"| `{md_escape(item.get('value'))}` "
                f"| {md_escape(' -> '.join(item.get('matchedStoryKeys') or []))} |"
            )
    else:
        lines.append("- _(none)_")

    lines.extend([
        "",
        "## Interpretation Notes",
        "",
        "- MissionRuntime and UID/control-flow LevelScript evidence can become strong order evidence.",
        "- LevelScript string offset order is weak until record types or trigger ownership are decoded.",
        "- LevelData byte-string hits can expose trigger state and spatial context, but are weak until decoded.",
        "- Radio/Audio and AssetMap hits validate file families and line membership, but do not prove inter-file chronology alone.",
        "- Map and spatial data should be used as tie-break or diagnostic evidence unless an explicit quest reference links the same target.",
    ])
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", default="CN")
    parser.add_argument("--mission", action="append", required=True, help="Mission id, comma-list accepted.")
    parser.add_argument("--reports-dir", type=Path, default=ROOT / "reports")
    parser.add_argument("--skip-asset-map", action="store_true", help="Skip the large AssetMap string-count pass.")
    return parser.parse_args(argv)


def split_missions(values: list[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        for part in str(value).split(","):
            mission = part.strip()
            if mission:
                out.append(mission)
    return unique_preserve(out)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_dir = args.reports_dir / "mission_order"
    out_dir.mkdir(parents=True, exist_ok=True)
    missions = split_missions(args.mission)
    for mission in missions:
        payload = build_report(
            mission,
            language=args.language,
            reports_dir=args.reports_dir,
            include_asset_map=not args.skip_asset_map,
        )
        json_path = out_dir / f"{mission}_evidence_audit.json"
        md_path = out_dir / f"{mission}_evidence_audit.md"
        write_report_json(json_path, payload)
        write_text_if_changed(md_path, markdown_report(payload))
        summary = payload["summary"]
        print(f"Mission order audit: {rel_path(md_path)}")
        print(f"Mission order data:  {rel_path(json_path)}")
        print(
            f"{mission}: {summary['entryCount']} entries; "
            f"status={summary['statusCounts']}; "
            f"{len(summary['weakOrUnknownWithNoMissionOrLevelScriptHits'])} weak/unknown without "
            "MissionRuntime/LevelScript hits."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
