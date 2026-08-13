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
from story_builder.mission_recovery import (  # noqa: E402
    TARGET_MISSION_PREFIXES,
    mission_id_matches_target_prefix,
)
from story_builder.mission_assets import select_complete_mission_runtime_root  # noqa: E402


ORDER_KINDS = {"dlg", "sns", "cutscene", "black", "remotecomm", "radio", "video"}
TABLE_ROOT = EXPORT_ROOT / "structured" / "StreamingAssets" / "Table"
DATA_JSON_ROOT = EXPORT_ROOT / "structured" / "StreamingAssets" / "Data" / "Json"
PERSISTENT_JSON_ROOT = EXPORT_ROOT / "structured" / "Persistent" / "Data" / "Json"
MRA_DIR = select_complete_mission_runtime_root(
    DATA_JSON_ROOT / "MissionRuntimeAsset",
    PERSISTENT_JSON_ROOT / "MissionRuntimeAsset",
)
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
RADIO_CONTINUATION_REPORT_PATH = (
    ROOT / "reports" / "mission_order" / "radio_continuation_CN.json"
)
READING_POPUP_TABLE_PATH = TABLE_ROOT / "ReadingPopUpTable.json"
PRTS_MULTIMEDIA_TABLE_PATH = TABLE_ROOT / "PrtsMultimedia.json"
PRTS_ALL_ITEM_TABLE_PATH = TABLE_ROOT / "PrtsAllItem.json"
STORY_REF_RE = re.compile(
    r"\b(?:dlg|radio|remotecomm|sns|cutscene|f_cutscene|m_cutscene|fm_cutscene|cs_video)_[A-Za-z0-9_]{2,120}"
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


def is_story_ref_byte_boundary(raw: bytes, start: int, end: int) -> bool:
    """Return true when a byte hit is not embedded in a longer story id."""
    story_ref_chars = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_"
    before_ok = start <= 0 or raw[start - 1] not in story_ref_chars
    after_ok = end >= len(raw) or raw[end] not in story_ref_chars
    return before_ok and after_ok


def normalize_story_ref(raw: str) -> str:
    value = safe_key(raw)
    for prefix in ("f_", "m_", "fm_"):
        if value.startswith(prefix + "cutscene_"):
            value = value[len(prefix):]
            break
    if value.startswith("cs_video_"):
        value = "cutscene_" + value[len("cs_video_"):]
    if value.startswith("dlg_"):
        parts = value.removeprefix("dlg_").split("_")
        if len(parts) >= 3 and parts[-1].isdigit() and len(parts[-1]) >= 3:
            parts = parts[:-1]
            if len(parts) >= 3 and parts[-1].isdigit():
                parts = parts[:-1]
        value = "dlg_" + "_".join(parts)
    elif value.startswith("radio_"):
        parts = value.removeprefix("radio_").split("_")
        if len(parts) >= 3 and parts[-1].isdigit() and len(parts[-1]) >= 3:
            parts = parts[:-1]
        value = "radio_" + "_".join(parts)
    elif value.startswith("remotecomm_"):
        parts = value.removeprefix("remotecomm_").split("_")
        if len(parts) >= 3 and parts[-1].isdigit() and len(parts[-1]) >= 3:
            parts = parts[:-1]
        value = "remotecomm_" + "_".join(parts)
    return value


def story_content_suffix(key: str) -> str:
    value = safe_key(key)
    if value.startswith("misc_"):
        value = value[5:]
    for prefix in ("dlg_", "radio_", "black_", "remotecomm_", "sns_", "cutscene_", "text_"):
        if value.startswith(prefix):
            return value[len(prefix):]
    return value


def walk_string_hits(
    node: Any,
    needles: dict[str, list[str]],
    *,
    path: str = "$",
    limit_per_key: int = 10,
) -> tuple[Counter[str], dict[str, list[dict[str, Any]]]]:
    hits: dict[str, list[dict[str, Any]]] = defaultdict(list)
    counts: Counter[str] = Counter()

    def alias_in_text(alias: str, text: str) -> bool:
        """Match full story ids while still allowing line/audio suffixes.

        A scene id such as `dlg_c6m1_1` should match `dlg_c6m1_1_001`,
        but not the distinct scene id `dlg_c6m1_17`.
        """
        if not alias:
            return False
        start = text.find(alias)
        while start >= 0:
            after = start + len(alias)
            if after >= len(text) or not text[after].isalnum():
                return True
            start = text.find(alias, start + 1)
        return False

    def add(text: str, where: str) -> None:
        if not text:
            return
        for key, aliases in needles.items():
            if any(alias_in_text(alias, text) for alias in aliases):
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
                    "mapId": unwrap_const(
                        value.get(
                            "_mapId",
                            value.get(
                                "mapId",
                                value.get(
                                    "_levelId",
                                    value.get(
                                        "levelId",
                                        value.get("_sceneId", value.get("sceneId")),
                                    ),
                                ),
                            ),
                        )
                    ),
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


def collect_story_refs(node: Any) -> list[str]:
    refs: list[str] = []

    def add_text(text: str) -> None:
        for match in STORY_REF_RE.finditer(text):
            ref = normalize_story_ref(match.group(0))
            if ref and ref not in refs:
                refs.append(ref)

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                add_text(str(key))
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
        elif isinstance(value, str):
            add_text(value)

    walk(node)
    return refs


def collect_leveldata_quest_ownership(leveldata_files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    quest_ids = unique_preserve(
        hit.get("questId")
        for item in leveldata_files
        for hit in (item.get("matchedSequence") or [])
        if hit.get("questId")
    )
    owners: list[dict[str, Any]] = []
    for quest_id in quest_ids:
        mission_hint = quest_id.split("_q#", 1)[0] if "_q#" in quest_id else ""
        candidate_paths: list[Path] = []
        if mission_hint:
            candidate = MRA_DIR / f"{mission_hint}.json"
            if candidate.exists():
                candidate_paths.append(candidate)
        if not candidate_paths:
            candidate_paths = sorted(MRA_DIR.glob("*.json"))
        found = False
        for path in candidate_paths:
            payload = read_json(path, {})
            quest_dic = payload.get("questDic") or {}
            quest = quest_dic.get(quest_id)
            if not quest:
                continue
            found = True
            child_ids = [
                child.get("questId") or child_id
                for child_id, child in quest_dic.items()
                if quest_id in (child.get("prevQuestIdList") or [])
            ]
            owners.append({
                "questId": quest_id,
                "mission": payload.get("missionId") or path.stem,
                "levelId": payload.get("levelId") or "",
                "file": rel_path(path),
                "flowIndex": quest.get("flowIndex"),
                "prevQuestIds": list(quest.get("prevQuestIdList") or []),
                "childQuestIds": child_ids,
                "storyRefs": collect_story_refs(quest),
            })
            break
        if not found:
            owners.append({"questId": quest_id, "missingMissionRuntimeOwner": True})
    return owners


def collect_reading_prts_links(keys: list[str]) -> dict[str, dict[str, Any]]:
    reading_rows = read_json(READING_POPUP_TABLE_PATH, {})
    prts_tables = [
        ("PrtsMultimedia", read_json(PRTS_MULTIMEDIA_TABLE_PATH, {})),
        ("PrtsAllItem", read_json(PRTS_ALL_ITEM_TABLE_PATH, {})),
    ]
    by_key: dict[str, dict[str, Any]] = {}
    for key in keys:
        suffix = story_content_suffix(key)
        normalized_key = key[5:] if key.startswith("misc_") else key
        exact_candidates = {key, normalized_key}
        cross_reference_candidates: set[str] = set()
        allow_row_suffix = False
        if normalized_key.startswith("text_"):
            allow_row_suffix = True
        elif normalized_key.startswith(("dlg_", "black_")):
            cross_reference_candidates.add(f"text_{suffix}")
            allow_row_suffix = True
        elif normalized_key.startswith("remotecomm_"):
            cross_reference_candidates.add(f"text_{suffix}")
        elif normalized_key.startswith("sns_"):
            exact_candidates.add(normalized_key)
        reading_matches: list[dict[str, Any]] = []
        cross_references: list[dict[str, Any]] = []
        for row_id, row in (reading_rows or {}).items():
            content_id = safe_key((row or {}).get("contentId"))
            row_id_text = safe_key(row_id)
            result = {
                "table": "ReadingPopUp",
                "id": row_id_text,
                "contentId": content_id,
                "bgType": row.get("bgType"),
                "iconType": row.get("iconType"),
            }
            if content_id in exact_candidates:
                result["matchType"] = "exact_content_id"
                reading_matches.append({
                    key: value
                    for key, value in result.items()
                    if key != "table"
                })
            elif (
                content_id in cross_reference_candidates
                or (allow_row_suffix and row_id_text.endswith(suffix))
            ):
                result["matchType"] = "suffix_cross_reference"
                cross_references.append(result)
        prts_matches: list[dict[str, Any]] = []
        for table_name, table in prts_tables:
            for row_id, row in (table or {}).items():
                content_id = safe_key((row or {}).get("contentId"))
                row_id_text = safe_key(row_id)
                result = {
                    "table": table_name,
                    "id": row_id_text,
                    "contentId": content_id,
                    "firstLvId": row.get("firstLvId"),
                    "order": row.get("order"),
                    "type": row.get("type"),
                }
                if content_id in exact_candidates:
                    result["matchType"] = "exact_content_id"
                    prts_matches.append({
                        key: value
                        for key, value in result.items()
                    })
                elif (
                    content_id in cross_reference_candidates
                    or (allow_row_suffix and row_id_text.endswith(suffix))
                ):
                    result["matchType"] = "suffix_cross_reference"
                    cross_references.append(result)
        if reading_matches or prts_matches or cross_references:
            by_key[key] = {
                "readingPopups": reading_matches[:8],
                "prtsItems": prts_matches[:8],
                "crossReferences": cross_references[:8],
                "note": (
                    "Only exact contentId matches are links. Same-suffix "
                    "Reading/PRTS rows are retained as fallible cross-reference "
                    "and are not ownership, playback, or chronology evidence."
                ),
            }
    return by_key


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


def leveldata_context(raw: bytes, index: int, length: int) -> dict[str, Any]:
    snippet = text_snippet(raw, index, length, radius=220)
    entity_matches = list(re.finditer(r"\bint_[A-Za-z0-9_]+", snippet))
    quest_matches = list(re.finditer(r"\b[A-Za-z0-9]+(?:[A-Za-z0-9_]*?)_q#\d+\b", snippet))
    rp_matches = list(re.finditer(r"\brp_(?:text|radio)_[A-Za-z0-9_]+", snippet))
    prts_matches = list(re.finditer(r"\bnar_(?:paper|media|digital)_[A-Za-z0-9_]+", snippet))
    out: dict[str, Any] = {"snippet": snippet}
    if entity_matches:
        out["entity"] = entity_matches[-1].group(0)
    if quest_matches:
        out["questId"] = quest_matches[-1].group(0)
    if rp_matches:
        out["readingPopupId"] = rp_matches[-1].group(0)
    if prts_matches:
        out["prtsId"] = prts_matches[-1].group(0)
    return out


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
                        if not is_story_ref_byte_boundary(raw, index, index + len(alias_raw)):
                            continue
                        key_hits += 1
                        context = leveldata_context(raw, index, len(alias_raw))
                        if len(examples[key]) < 4:
                            examples[key].append({
                                "levelId": level_id,
                                "file": rel_path(path),
                                "offset": index,
                                "text": context["snippet"],
                                **{
                                    k: v
                                    for k, v in context.items()
                                    if k != "snippet"
                                },
                            })
                        if len([item for item in matched if item.get("key") == key]) < 4:
                            matched.append({
                                "offset": index,
                                "key": key,
                                "alias": alias,
                                "text": context["snippet"],
                                **{
                                    k: v
                                    for k, v in context.items()
                                    if k != "snippet"
                                },
                            })
                if key_hits:
                    counts[key] += key_hits
            if matched or raw_mission_count:
                matched_sequence = sorted(matched, key=lambda item: item.get("offset") or 0)
                ordered_unique = unique_preserve(item["key"] for item in matched_sequence)
                files.append({
                    "levelId": level_id,
                    "file": rel_path(path),
                    "matchedSequence": matched_sequence,
                    "matchedUniqueKeys": ordered_unique,
                    "matchedPairCount": max(0, len(ordered_unique) - 1),
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


def collect_radio_continuation_hits(
    mission: str,
    entry_report: dict[str, dict[str, Any]],
    report_path: Path = RADIO_CONTINUATION_REPORT_PATH,
) -> int:
    """Add `hits.radioContinuation` from the radio-continuation audit.

    Returns the number of audit entries that gained a continuation predecessor.
    Silent no-op when the continuation report has not been generated yet.
    """
    if not report_path.exists():
        return 0
    try:
        report = read_json(report_path, {})
    except Exception:  # noqa: BLE001
        return 0
    mission_results = [
        item for item in (report.get("results") or []) if item.get("mission") == mission
    ]
    if not mission_results:
        return 0
    candidates_by_radio: dict[str, list[dict[str, Any]]] = {}
    for result in mission_results:
        for cand in result.get("candidates") or []:
            radio = cand.get("radio") or ""
            if radio:
                candidates_by_radio.setdefault(radio, []).append(cand)
    anchored = 0
    for key, info in entry_report.items():
        normalized = key[5:] if key.startswith("misc_") else key
        cands = candidates_by_radio.get(normalized)
        if not cands:
            continue
        info["hits"]["radioContinuation"] = {
            "matchCount": len(cands),
            "candidates": [
                {
                    "match": cand.get("match"),
                    "predecessor": cand.get("predecessor"),
                    "levelId": cand.get("levelId"),
                    "file": cand.get("file"),
                }
                for cand in cands[:6]
            ],
            "sourceReport": str(report_path.relative_to(ROOT)).replace("\\", "/"),
        }
        anchored += 1
    return anchored


def collect_variant_mission_runtime_hits(
    webui_mission: dict[str, Any],
    entry_report: dict[str, dict[str, Any]],
) -> int:
    flow = webui_mission.get("flow") if isinstance(webui_mission.get("flow"), dict) else {}
    variant_missions = set(flow.get("sceneGraphVariantMissions") or [])
    if not variant_missions:
        return 0
    scene_graph = flow.get("sceneGraph") if isinstance(flow.get("sceneGraph"), dict) else {}
    for edge in scene_graph.get("edges") or []:
        if not isinstance(edge, dict):
            continue
        quest_ids = [
            safe_key(quest_id)
            for quest_id in edge.get("questIds") or []
            if safe_key(quest_id).split("_q#", 1)[0] in variant_missions
        ]
        if not quest_ids:
            continue
        edge_ref = {
            "kind": safe_key(edge.get("kind")),
            "from": safe_key(edge.get("from")),
            "to": safe_key(edge.get("to")),
            "questIds": quest_ids,
            "variantMissions": sorted({quest_id.split("_q#", 1)[0] for quest_id in quest_ids}),
        }
        for key in (edge_ref["from"], edge_ref["to"]):
            if key not in entry_report:
                continue
            hit = entry_report[key]["hits"].setdefault(
                "variantMissionRuntime",
                {"count": 0, "variants": [], "edges": []},
            )
            hit["count"] += 1
            for variant_mission in edge_ref["variantMissions"]:
                if variant_mission not in hit["variants"]:
                    hit["variants"].append(variant_mission)
            if len(hit["edges"]) < 8:
                hit["edges"].append(edge_ref)
    return sum(1 for info in entry_report.values() if info["hits"].get("variantMissionRuntime"))


def collect_npc_proxy_dialog_hits(
    webui_mission: dict[str, Any],
    entry_report: dict[str, dict[str, Any]],
) -> int:
    alias_to_key: dict[str, str] = {}
    for key in entry_report:
        for alias in aliases_for_key(key):
            alias_to_key.setdefault(alias, key)
        alias_to_key.setdefault(normalize_story_ref(key), key)
        if key.startswith("misc_dlg_"):
            alias_to_key.setdefault("dlg_" + key[len("misc_dlg_"):], key)

    flow = webui_mission.get("flow") if isinstance(webui_mission.get("flow"), dict) else {}
    for quest in flow.get("quests") or []:
        quest_id = safe_key(quest.get("id"))
        for proxy_ref in quest.get("proxyDialogs") or []:
            if not isinstance(proxy_ref, dict):
                continue
            dialog_id = safe_key(proxy_ref.get("dialogId"))
            key = (
                alias_to_key.get(dialog_id)
                or alias_to_key.get(normalize_story_ref(dialog_id))
            )
            if not key:
                continue
            hit = entry_report[key]["hits"].setdefault(
                "npcProxyDialog",
                {"count": 0, "quests": []},
            )
            hit["count"] += 1
            if len(hit["quests"]) < 8:
                hit["quests"].append({
                    "questId": quest_id,
                    "npcProxyId": safe_key(proxy_ref.get("npcProxyId")),
                    "dialogId": dialog_id,
                    "source": safe_key(proxy_ref.get("source")),
                })

    for connection in flow.get("missionStoryConnections") or []:
        if not (
            isinstance(connection, dict)
            and connection.get("relation") == "npc_proxy_ex_mission_context"
        ):
            continue
        dialog_id = safe_key(connection.get("key"))
        key = (
            alias_to_key.get(dialog_id)
            or alias_to_key.get(normalize_story_ref(dialog_id))
        )
        if not key:
            continue
        hit = entry_report[key]["hits"].setdefault(
            "npcProxyDialog",
            {"count": 0, "quests": []},
        )
        hit["count"] += 1
        mission_contexts = hit.setdefault("missionContexts", [])
        if len(mission_contexts) < 8:
            mission_contexts.append({
                "npcProxyId": safe_key(connection.get("npcProxyId")),
                "dialogId": dialog_id,
                "missionId": safe_key(connection.get("npcProxyMissionId")),
                "storyOwnerMission": safe_key(
                    connection.get("storyOwnerMission")
                ),
                "source": safe_key(connection.get("source")),
                "selectionOrderStatus": safe_key(
                    connection.get("selectionOrderStatus")
                ),
                "nativeMappingId": safe_key(
                    connection.get("nativeMappingId")
                ),
                "gameAssemblySha256": safe_key(
                    connection.get("gameAssemblySha256")
                ),
            })
    return sum(1 for info in entry_report.values() if info["hits"].get("npcProxyDialog"))


def build_report(
    mission: str,
    *,
    language: str,
    reports_dir: Path,
    include_asset_map: bool,
) -> dict[str, Any]:
    index_path = ROOT / "webui" / "data" / "lang" / language / "index.json"
    webui_mission_path = ROOT / "webui" / "data" / "lang" / language / "mission" / f"{mission}.json"
    mission_runtime_path = MRA_DIR / f"{mission}.json"
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
    leveldata_pair_count = sum(item.get("matchedPairCount") or 0 for item in leveldata_files)
    leveldata_quest_owners = collect_leveldata_quest_ownership(leveldata_files)
    for key, count in leveldata_counts.items():
        entry_report[key]["hits"]["levelData"] = {
            "count": count,
            "examples": leveldata_examples[key],
            "note": "Byte-string hit in LevelData; useful trigger/spatial context, not chronology alone.",
        }

    collect_audio_hits(mission, keys, needles, entry_report)
    reading_prts_links = collect_reading_prts_links(keys)
    reading_prts_exact_linked_count = sum(
        1
        for links in reading_prts_links.values()
        if (links.get("readingPopups") or links.get("prtsItems"))
    )
    reading_prts_cross_reference_count = sum(
        1
        for links in reading_prts_links.values()
        if links.get("crossReferences")
    )
    for key, links in reading_prts_links.items():
        entry_report[key]["hits"]["readingPrts"] = links
    map_table_hits = collect_map_hits(mission, level_ids)
    if include_asset_map:
        collect_asset_map_counts(keys, entry_report, asset_map=ASSET_MAP)
    radio_continuation_anchored = collect_radio_continuation_hits(mission, entry_report)
    variant_mission_runtime_anchored = collect_variant_mission_runtime_hits(
        webui_mission,
        entry_report,
    )
    npc_proxy_dialog_anchored = collect_npc_proxy_dialog_hits(webui_mission, entry_report)

    status_counts = Counter(value["status"] for value in entry_report.values())
    weak_or_unknown = [key for key, value in entry_report.items() if value["status"] != "strong"]
    no_mission_or_levelscript = [
        key
        for key in weak_or_unknown
        if not (
            entry_report[key]["hits"].get("missionRuntime")
            or entry_report[key]["hits"].get("npcProxyDialog")
            or entry_report[key]["hits"].get("variantMissionRuntime")
            or entry_report[key]["hits"].get("levelScriptData")
        )
    ]
    weak_or_unknown_anchored_by_radio_cont = [
        key
        for key in weak_or_unknown
        if entry_report[key]["hits"].get("radioContinuation")
    ]
    chunks = (mission_timeline or {}).get("chunks") or []
    levelscript_spatial = (mission_timeline or {}).get("levelscriptSpatialProximity") or []
    chunk_strength_counter: Counter = Counter()
    chunk_isolated_count = 0
    chunk_max_scene_count = 0
    subchunk_count = 0
    chunk_with_subchunks_count = 0
    for chunk in chunks:
        chunk_strength_counter[str(chunk.get("strength") or "unanchored")] += 1
        if chunk.get("isolated"):
            chunk_isolated_count += 1
        size = int(chunk.get("sceneCount") or 0)
        if size > chunk_max_scene_count:
            chunk_max_scene_count = size
        subchunks = chunk.get("subchunks") or []
        if subchunks:
            chunk_with_subchunks_count += 1
            subchunk_count += len(subchunks)
    chunk_order_data = (mission_timeline or {}).get("chunkOrder") or {}
    chunk_order_edges = chunk_order_data.get("edges") or []
    chunk_order_parallel = chunk_order_data.get("parallel") or []
    chunk_order_incomparable = chunk_order_data.get("incomparable") or []
    chunk_order_unattached = chunk_order_data.get("unattachedChunkIds") or []

    return {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "language": language,
        "mission": mission,
        "sourceFiles": {
            "webuiIndex": rel_path(index_path),
            "webuiMission": rel_path(webui_mission_path),
            "missionRuntime": rel_path(mission_runtime_path),
            "missionTimelineRecovery": rel_path(mission_timeline_path),
            "npcProxyEx": rel_path(DATA_JSON_ROOT / "GameplayConfig" / "NpcProxyExDataTable.json"),
            "radioTable": rel_path(TABLE_ROOT / "RadioTable.json"),
            "audioDialog": rel_path(TABLE_ROOT / "AudioDialog.json"),
            "readingPopupTable": rel_path(READING_POPUP_TABLE_PATH),
            "prtsMultimedia": rel_path(PRTS_MULTIMEDIA_TABLE_PATH),
            "prtsAllItem": rel_path(PRTS_ALL_ITEM_TABLE_PATH),
            "assetMap": rel_path(ASSET_MAP),
        },
        "summary": {
            "entryCount": len(entries),
            "statusCounts": dict(status_counts),
            "levelIdsInspected": level_ids,
            "missionRuntimeScriptConditionCount": len(runtime_script_conditions),
            "levelScriptFilesWithMissionHits": len(levelscript_files),
            "levelDataFilesWithMissionHits": len(leveldata_files),
            "levelDataSequentialPairCount": leveldata_pair_count,
            "levelDataQuestOwnerCount": len(leveldata_quest_owners),
            "readingPrtsLinkedEntryCount": reading_prts_exact_linked_count,
            "readingPrtsSuffixCrossReferenceEntryCount": (
                reading_prts_cross_reference_count
            ),
            "weakOrUnknownCount": len(weak_or_unknown),
            "weakOrUnknownWithNoMissionOrLevelScriptHits": no_mission_or_levelscript,
            "weakOrUnknownWithNoMissionLevelScriptOrLevelDataHits": [
                key
                for key in no_mission_or_levelscript
                if not entry_report[key]["hits"].get("levelData")
            ],
            "npcProxyDialogAnchoredCount": npc_proxy_dialog_anchored,
            "radioContinuationAnchoredCount": radio_continuation_anchored,
            "weakOrUnknownGainingRadioContinuationAnchor": weak_or_unknown_anchored_by_radio_cont,
            "variantMissionRuntimeAnchoredCount": variant_mission_runtime_anchored,
            "variantMissionRuntimeMissions": (webui_mission.get("flow") or {}).get("sceneGraphVariantMissions") or [],
            "chunkCount": len(chunks),
            "chunkStrongCount": chunk_strength_counter.get("strong", 0),
            "chunkWeakCount": chunk_strength_counter.get("weak", 0),
            "chunkUnanchoredCount": chunk_strength_counter.get("unanchored", 0),
            "chunkIsolatedCount": chunk_isolated_count,
            "chunkMaxSceneCount": chunk_max_scene_count,
            "chunkWithSubchunksCount": chunk_with_subchunks_count,
            "subchunkCount": subchunk_count,
            "chunkOrderEdgeCount": len(chunk_order_edges),
            "chunkOrderParallelPairCount": len(chunk_order_parallel),
            "chunkOrderIncomparablePairCount": len(chunk_order_incomparable),
            "chunkOrderUnattachedChunkCount": len(chunk_order_unattached),
            "levelscriptSpatialProximityCount": len(levelscript_spatial),
        },
        "missionTimeline": {
            "propertyModel": (mission_timeline or {}).get("propertyModel"),
            "questEdges": (mission_timeline or {}).get("questEdges") or [],
            "questTree": (mission_timeline or {}).get("questTree") or {},
            "sourceBackedSceneEdges": (mission_timeline or {}).get("sourceBackedSceneEdges") or [],
            "sourceBackedSceneSequences": (mission_timeline or {}).get("sourceBackedSceneSequences") or [],
            "sourceBackedHashTerminals": (mission_timeline or {}).get("sourceBackedHashTerminals") or [],
            "chunks": (mission_timeline or {}).get("chunks") or [],
            "chunkOrder": (mission_timeline or {}).get("chunkOrder") or {},
            "questSpatialTrack": (mission_timeline or {}).get("questSpatialTrack") or [],
            "levelscriptSpatialProximity": levelscript_spatial,
            "scenePlacement": (mission_timeline or {}).get("scenePlacement") or {},
            "scriptConditionAttachments": (mission_timeline or {}).get("scriptConditionAttachments") or [],
            "unresolved": (mission_timeline or {}).get("unresolved") or [],
        },
        "missionRuntimeScriptConditions": runtime_script_conditions,
        "levelScriptFiles": levelscript_files,
        "levelDataFiles": leveldata_files,
        "levelDataQuestOwners": leveldata_quest_owners,
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
        f"- Entries with NPC proxy dialog evidence: {summary.get('npcProxyDialogAnchoredCount', 0)}",
        "- Entries with variant MissionRuntime scene-graph evidence: "
        f"{summary.get('variantMissionRuntimeAnchoredCount', 0)}"
        + (
            " ("
            + ", ".join(summary.get("variantMissionRuntimeMissions") or [])
            + ")"
            if summary.get("variantMissionRuntimeMissions")
            else ""
        ),
        f"- LevelScript files with mission hits: {summary['levelScriptFilesWithMissionHits']}",
        f"- LevelData files with mission hits: {summary['levelDataFilesWithMissionHits']}",
        f"- LevelData adjacent story pairs: {summary.get('levelDataSequentialPairCount', 0)}",
        f"- LevelData quest owners: {summary.get('levelDataQuestOwnerCount', 0)}",
        "- Entries with exact Reading/PRTS content links: "
        f"{summary.get('readingPrtsLinkedEntryCount', 0)}",
        "- Entries with suffix-only Reading/PRTS cross-reference: "
        f"{summary.get('readingPrtsSuffixCrossReferenceEntryCount', 0)}",
        "- Weak/unknown entries with no MissionRuntime/proxy/variant/LevelScript hits: "
        f"{len(summary['weakOrUnknownWithNoMissionOrLevelScriptHits'])}",
        "- Weak/unknown entries with no MissionRuntime/proxy/variant/LevelScript/LevelData hits: "
        f"{len(summary['weakOrUnknownWithNoMissionLevelScriptOrLevelDataHits'])}",
        "- Entries with radio-continuation anchor: "
        f"{summary.get('radioContinuationAnchoredCount', 0)} "
        f"(weak/unknown newly anchored: "
        f"{len(summary.get('weakOrUnknownGainingRadioContinuationAnchor', []))})",
        f"- Scene chunks: {summary.get('chunkCount', 0)} "
        f"(strong={summary.get('chunkStrongCount', 0)}, "
        f"weak={summary.get('chunkWeakCount', 0)}, "
        f"isolated={summary.get('chunkIsolatedCount', 0)}; "
        f"max scenes/chunk {summary.get('chunkMaxSceneCount', 0)})",
        f"- Chunk order: {summary.get('chunkOrderEdgeCount', 0)} questDag edges, "
        f"{summary.get('chunkOrderParallelPairCount', 0)} parallel pairs, "
        f"{summary.get('chunkOrderIncomparablePairCount', 0)} incomparable pairs, "
        f"{summary.get('chunkOrderUnattachedChunkCount', 0)} chunks with no quest attach",
        "",
        "## Entry Evidence",
        "",
        "| key | status | chunk | go | fallback | MissionRuntime | ProxyDlg | VariantMR | LevelScript | LevelData | Radio | Audio | Read/PRTS | AssetMap | RadioCont |",
        "| --- | --- | --- | ---: | --- | ---: | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- |",
    ]
    scene_placement_index = (payload.get("missionTimeline") or {}).get("scenePlacement") or {}
    for key, info in payload["entries"].items():
        hits = info["hits"]
        radio = hits.get("radioTable")
        radio_text = ""
        if radio:
            radio_text = f"p{radio.get('priority')}/t{radio.get('radioType')}/n{radio.get('lineCount')}"
        radio_cont = hits.get("radioContinuation")
        radio_cont_text = ""
        if radio_cont:
            first = (radio_cont.get("candidates") or [{}])[0]
            radio_cont_text = (
                f"{first.get('match', '?')} <- "
                f"{first.get('predecessor', '')}"
            )
            if radio_cont.get("matchCount", 0) > 1:
                radio_cont_text += f" (+{radio_cont['matchCount'] - 1})"
        proxy_dialog = hits.get("npcProxyDialog")
        proxy_dialog_text = ""
        if proxy_dialog:
            quest_rows = proxy_dialog.get("quests") or []
            mission_contexts = proxy_dialog.get("missionContexts") or []
            first = (quest_rows or mission_contexts or [{}])[0]
            owner = (
                first.get("questId")
                or first.get("missionId")
                or "mission config"
            )
            proxy_dialog_text = f"{first.get('npcProxyId', '')} <- {owner}"
            if proxy_dialog.get("count", 0) > 1:
                proxy_dialog_text += f" (+{proxy_dialog['count'] - 1})"
        graph_order = info.get("graphOrder")
        chunk_id = (scene_placement_index.get(key) or {}).get("chunkId") or ""
        reading_prts = hits.get("readingPrts", {})
        reading_prts_exact_count = (
            len(reading_prts.get("readingPopups") or [])
            + len(reading_prts.get("prtsItems") or [])
        )
        reading_prts_cross_reference_count = len(
            reading_prts.get("crossReferences") or []
        )
        reading_prts_text = str(reading_prts_exact_count)
        if reading_prts_cross_reference_count:
            reading_prts_text += f" / xref {reading_prts_cross_reference_count}"
        lines.append(
            "| "
            f"`{md_escape(key)}` "
            f"| {md_escape(info.get('status'))} "
            f"| {md_escape(chunk_id)} "
            f"| {graph_order if graph_order is not None else ''} "
            f"| {md_escape(info.get('fallbackTail'))} "
            f"| {hits.get('missionRuntime', {}).get('count', 0)} "
            f"| {md_escape(proxy_dialog_text)} "
            f"| {hits.get('variantMissionRuntime', {}).get('count', 0)} "
            f"| {hits.get('levelScriptData', {}).get('count', 0)} "
            f"| {hits.get('levelData', {}).get('count', 0)} "
            f"| {md_escape(radio_text)} "
            f"| {hits.get('audioDialog', {}).get('count', 0)} "
            f"| {md_escape(reading_prts_text)} "
            f"| {hits.get('assetMapString', {}).get('count', 0)} "
            f"| {md_escape(radio_cont_text)} |"
        )

    chunks = (payload.get("missionTimeline") or {}).get("chunks") or []
    lines.extend(["", "## Scene Chunks", ""])
    if chunks:
        chunk_counts = Counter(chunk.get("strength") or "unanchored" for chunk in chunks)
        chunk_counts_text = ", ".join(
            f"{name}={chunk_counts[name]}" for name in sorted(chunk_counts)
        )
        lines.append(
            f"- {len(chunks)} chunks "
            f"({chunk_counts_text}) — "
            "connected components in source-backed scene edges, levelscript "
            "chains, and shared Timelines. Order within a chunk is preserved "
            "by its edges; inter-chunk order is recovered separately."
        )
        lines.append("")
        lines.append("| chunk | strength | scenes | quests | subchunks | spatial candidates | source scripts | kinds | edge kinds | scene keys |")
        lines.append("| --- | --- | ---: | --- | --- | --- | --- | --- | --- | --- |")
        for chunk in chunks:
            scene_keys = chunk.get("sceneKeys") or []
            scene_kinds = ", ".join(chunk.get("sceneKinds") or []) or "—"
            edge_kinds = ", ".join(chunk.get("edgeKinds") or []) or "_(isolated)_"
            scene_keys_text = ", ".join(f"`{md_escape(scene_key)}`" for scene_key in scene_keys[:12])
            if len(scene_keys) > 12:
                scene_keys_text += f", _… (+{len(scene_keys) - 12})_"
            quest_ids = chunk.get("questIds") or []
            quest_text = ", ".join(f"`{md_escape(quest_id)}`" for quest_id in quest_ids) or "-"
            source_scripts = chunk.get("sourceScripts") or []
            script_texts = [
                f"`{md_escape((script.get('levelId') or script.get('mapId') or '?') + '/' + str(script.get('scriptId') or '?'))}`"
                for script in source_scripts[:6]
                if isinstance(script, dict)
            ]
            if len(source_scripts) > 6:
                script_texts.append(f"_+{len(source_scripts) - 6}_")
            span = chunk.get("sourceFileOrderSpan") or {}
            if isinstance(span, dict) and span.get("first") and span.get("last"):
                first = span.get("first") or {}
                last = span.get("last") or {}
                script_texts.append(
                    "_span "
                    f"{md_escape(str(first.get('scriptId') or '?'))}"
                    ".."
                    f"{md_escape(str(last.get('scriptId') or '?'))}_"
                )
            source_script_text = ", ".join(script_texts) or "-"
            spatial_candidates = chunk.get("spatialQuestCandidates") or []
            spatial_texts = []
            for candidate in spatial_candidates[:4]:
                if not isinstance(candidate, dict):
                    continue
                label = str(candidate.get("questId") or "?")
                if candidate.get("distanceXZ") is not None:
                    label += f" @{candidate.get('distanceXZ')}m"
                if candidate.get("scriptId"):
                    label += f" via {candidate.get('scriptId')}"
                spatial_texts.append(f"`{md_escape(label)}`")
            if len(spatial_candidates) > 4:
                spatial_texts.append(f"_+{len(spatial_candidates) - 4}_")
            spatial_text = ", ".join(spatial_texts) or "-"
            subchunk_texts = []
            for subchunk in (chunk.get("subchunks") or [])[:6]:
                if not isinstance(subchunk, dict):
                    continue
                hint = subchunk.get("questOrderHint") or {}
                label = str(hint.get("questId") or subchunk.get("basis") or "subchunk")
                subchunk_texts.append(
                    f"`{md_escape(subchunk.get('id'))}` {md_escape(label)} ({subchunk.get('sceneCount', 0)})"
                )
            if len(chunk.get("subchunks") or []) > 6:
                subchunk_texts.append(f"_+{len(chunk.get('subchunks') or []) - 6}_")
            subchunk_text = ", ".join(subchunk_texts) or "-"
            lines.append(
                "| "
                f"`{md_escape(chunk.get('id'))}` "
                f"| {md_escape(chunk.get('strength'))} "
                f"| {chunk.get('sceneCount', 0)} "
                f"| {quest_text} "
                f"| {subchunk_text} "
                f"| {spatial_text} "
                f"| {source_script_text} "
                f"| {md_escape(scene_kinds)} "
                f"| {md_escape(edge_kinds)} "
                f"| {scene_keys_text} |"
            )
    else:
        lines.append("- _(none)_")

    subchunk_rows = [
        (chunk, subchunk)
        for chunk in chunks
        for subchunk in (chunk.get("subchunks") or [])
        if isinstance(subchunk, dict)
    ]
    lines.extend(["", "## Scene Subchunks", ""])
    if subchunk_rows:
        lines.append(
            "Diagnostic weak splits inside a chunk, usually from contiguous "
            "LevelScript spatial-candidate runs. They do not create quest "
            "attachments or chunk-order edges."
        )
        lines.append("")
        lines.append("| parent | subchunk | hint | scenes | spatial candidates | source scripts | scene keys |")
        lines.append("| --- | --- | --- | ---: | --- | --- | --- |")
        for chunk, subchunk in subchunk_rows:
            scene_keys = subchunk.get("sceneKeys") or []
            scene_keys_text = ", ".join(f"`{md_escape(scene_key)}`" for scene_key in scene_keys[:12])
            if len(scene_keys) > 12:
                scene_keys_text += f", _... (+{len(scene_keys) - 12})_"
            hint = subchunk.get("questOrderHint") or {}
            hint_text = "-"
            if hint:
                hint_text = str(hint.get("questId") or hint.get("kind") or "-")
                if hint.get("distanceXZ") is not None:
                    hint_text += f" @{hint.get('distanceXZ')}m"
                if hint.get("scriptId"):
                    hint_text += f" via {hint.get('scriptId')}"
                hint_text = f"`{md_escape(hint_text)}`"
            spatial_texts = []
            for candidate in (subchunk.get("spatialQuestCandidates") or [])[:4]:
                if not isinstance(candidate, dict):
                    continue
                label = str(candidate.get("questId") or "?")
                if candidate.get("distanceXZ") is not None:
                    label += f" @{candidate.get('distanceXZ')}m"
                if candidate.get("scriptId"):
                    label += f" via {candidate.get('scriptId')}"
                spatial_texts.append(f"`{md_escape(label)}`")
            if len(subchunk.get("spatialQuestCandidates") or []) > 4:
                spatial_texts.append(f"_+{len(subchunk.get('spatialQuestCandidates') or []) - 4}_")
            spatial_text = ", ".join(spatial_texts) or "-"
            script_texts = [
                f"`{md_escape((script.get('levelId') or script.get('mapId') or '?') + '/' + str(script.get('scriptId') or '?'))}`"
                for script in (subchunk.get("sourceScripts") or [])[:6]
                if isinstance(script, dict)
            ]
            if len(subchunk.get("sourceScripts") or []) > 6:
                script_texts.append(f"_+{len(subchunk.get('sourceScripts') or []) - 6}_")
            script_text = ", ".join(script_texts) or "-"
            lines.append(
                "| "
                f"`{md_escape(chunk.get('id'))}` "
                f"| `{md_escape(subchunk.get('id'))}` "
                f"| {hint_text} "
                f"| {subchunk.get('sceneCount', 0)} "
                f"| {spatial_text} "
                f"| {script_text} "
                f"| {scene_keys_text} |"
            )
    else:
        lines.append("- _(none)_")

    quest_tree = (payload.get("missionTimeline") or {}).get("questTree") or {}
    unattached_quest_chunks = quest_tree.get("unattachedToQuestChunkIds") or []
    attachment_summary = quest_tree.get("chunkAttachmentSummary") or {}
    lines.extend(["", "## Task Tree", ""])
    if quest_tree.get("roots") or quest_tree.get("unrootedRoots"):
        lines.append(
            f"- attached chunks: `{attachment_summary.get('attachedChunkCount', 0)}` "
            f"across `{attachment_summary.get('questsWithChunkCount', 0)}` quests; "
            f"unattached chunks: `{attachment_summary.get('unattachedChunkCount', 0)}`"
        )
        hint_summary = quest_tree.get("sourceScriptHintSummary") or {}
        if hint_summary:
            lines.append(
                f"- source-script hints: `{hint_summary.get('hintCount', 0)}` "
                f"across `{hint_summary.get('questCount', 0)}` quests"
            )
        lines.append("")

        def render_tree_lines(nodes: list[dict], depth: int = 0) -> None:
            for node in nodes or []:
                if not isinstance(node, dict):
                    continue
                quest_id = node.get("questId") or ""
                indent = "  " * depth
                attached = node.get("attachedChunkIds") or []
                chunks_text = (
                    " — " + ", ".join(f"`{md_escape(cid)}`" for cid in attached)
                    if attached
                    else ""
                )
                source_hints = node.get("sourceScriptHints") or []
                source_texts = []
                for hint in source_hints[:4]:
                    if not isinstance(hint, dict):
                        continue
                    label_parts = []
                    if hint.get("subchunkId") or hint.get("chunkId"):
                        label_parts.append(str(hint.get("subchunkId") or hint.get("chunkId")))
                    if hint.get("sceneKey"):
                        label_parts.append(str(hint.get("sceneKey")))
                    if not label_parts:
                        script_label = "/".join(
                            str(value)
                            for value in (hint.get("mapId") or hint.get("levelId"), hint.get("scriptId"))
                            if value
                        )
                        label_parts.append(script_label or str(hint.get("kind") or "source"))
                    label = " ".join(label_parts)
                    if hint.get("scriptId") and not label.endswith(str(hint.get("scriptId"))):
                        label += f"/{hint.get('scriptId')}"
                    if hint.get("distanceXZ") is not None:
                        label += f" @{hint.get('distanceXZ')}m"
                    source_texts.append(f"`{md_escape(label)}`")
                if len(source_hints) > 4:
                    source_texts.append(f"_+{len(source_hints) - 4}_")
                sources_text = (
                    " sources " + ", ".join(source_texts)
                    if source_texts
                    else ""
                )
                tags = []
                if node.get("loop"):
                    tags.append("loop")
                if node.get("reused"):
                    tags.append("reused")
                tag_text = f" _({', '.join(tags)})_" if tags else ""
                lines.append(f"{indent}- `{md_escape(quest_id)}`{tag_text}{chunks_text}{sources_text}")
                if not node.get("reused"):
                    render_tree_lines(node.get("children") or [], depth + 1)

        if quest_tree.get("roots"):
            render_tree_lines(quest_tree["roots"])
        if quest_tree.get("unrootedRoots"):
            lines.append("")
            lines.append("Unrooted (no explicit empty prevQuestIdList):")
            lines.append("")
            render_tree_lines(quest_tree["unrootedRoots"])
        if unattached_quest_chunks:
            lines.append("")
            lines.append(
                "Chunks not attached to any quest (no storyRef or script-condition match): "
                + ", ".join(f"`{md_escape(cid)}`" for cid in unattached_quest_chunks)
            )
    else:
        lines.append("- _(no quest tree)_")

    quest_track = (payload.get("missionTimeline") or {}).get("questSpatialTrack") or []
    lines.extend(["", "## Quest Map Track", ""])
    if quest_track:
        lines.append(
            "Map pins, resources, and script conditions are diagnostic placement hints; "
            "they are not promoted to chronology without an explicit quest/story edge."
        )
        lines.append("")
        lines.append("| quest | flow | prev | chunks | spatial matches | pins | scripts | resources | dist |")
        lines.append("| --- | ---: | --- | --- | --- | --- | --- | --- | ---: |")

        def pin_label(pin: dict[str, Any]) -> str:
            name = (
                safe_key(pin.get("missionAreaId"))
                or safe_key(pin.get("npcProxyId"))
                or safe_key(pin.get("scene"))
                or safe_key(pin.get("trackingType"))
                or "pin"
            )
            pos = pin.get("position") or {}
            if isinstance(pos, dict) and {"x", "z"} <= set(pos):
                label = (
                    f"{name}@"
                    f"{float(pos.get('x', 0.0)):.1f},"
                    f"{float(pos.get('z', 0.0)):.1f}"
                )
            else:
                label = name
            parent_raw = pin.get("subDataParentId") or pin.get("levelDataParentId")
            parent = str(parent_raw) if parent_raw not in (None, "", [], {}) else ""
            if parent:
                label += f" parent {parent}"
            return label

        for item in quest_track:
            if not isinstance(item, dict):
                continue
            chunks_text = ", ".join(f"`{md_escape(cid)}`" for cid in item.get("attachedChunkIds") or []) or "-"
            spatial_matches = item.get("spatialSourceMatches") or []
            spatial_texts = []
            for match in spatial_matches[:4]:
                if not isinstance(match, dict):
                    continue
                label_parts = []
                if match.get("subchunkId") or match.get("chunkId"):
                    label_parts.append(str(match.get("subchunkId") or match.get("chunkId")))
                if match.get("sceneKey"):
                    label_parts.append(str(match.get("sceneKey")))
                label = " ".join(label_parts) or "?"
                if match.get("scriptId"):
                    label += f"/{match.get('scriptId')}"
                if match.get("distanceXZ") is not None:
                    label += f" @{match.get('distanceXZ')}m"
                spatial_texts.append(f"`{md_escape(label)}`")
            if len(spatial_matches) > 4:
                spatial_texts.append(f"_+{len(spatial_matches) - 4}_")
            spatial_text = ", ".join(spatial_texts) or "-"
            pins = item.get("pins") or []
            pins_text = ", ".join(md_escape(pin_label(pin)) for pin in pins[:4] if isinstance(pin, dict)) or "-"
            if len(pins) > 4:
                pins_text += f", _+{len(pins) - 4}_"
            scripts = item.get("scriptRefs") or []
            script_texts = []
            for script in scripts[:4]:
                if not isinstance(script, dict):
                    continue
                label = (
                    f"{script.get('mapId') or script.get('levelId') or '?'}/"
                    f"{script.get('scriptId') or '?'}"
                )
                if script.get("key"):
                    label += f":{script.get('key')}"
                script_texts.append(f"`{md_escape(label)}`")
            if len(scripts) > 4:
                script_texts.append(f"_+{len(scripts) - 4}_")
            scripts_text = ", ".join(script_texts) or "-"
            resources = item.get("resources") or []
            resource_texts = [
                f"`{md_escape((resource.get('kind') or 'ref') + ':' + (resource.get('key') or ''))}`"
                for resource in resources[:5]
                if isinstance(resource, dict) and resource.get("key")
            ]
            if len(resources) > 5:
                resource_texts.append(f"_+{len(resources) - 5}_")
            resources_text = ", ".join(resource_texts) or "-"
            lines.append(
                "| "
                f"`{md_escape(item.get('questId'))}` "
                f"| {item.get('flowIndex', '')} "
                f"| {md_escape(', '.join(item.get('prevQuestIds') or []) or '-')} "
                f"| {chunks_text} "
                f"| {spatial_text} "
                f"| {pins_text} "
                f"| {scripts_text} "
                f"| {resources_text} "
                f"| {item.get('distanceFromPrevious', '')} |"
            )
    else:
        lines.append("- _(none)_")

    spatial_matches = (payload.get("missionTimeline") or {}).get("levelscriptSpatialProximity") or []
    lines.extend(["", "## LevelScript Spatial Proximity", ""])
    if spatial_matches:
        lines.append(
            "Weak matches from raw LevelScript float triples to quest map pins. "
            "These are diagnostic placement hints and are not quest-DAG edges."
        )
        lines.append("")
        lines.append("| scene | quest | chunk | script | offset | vector | pin | xz dist | y delta |")
        lines.append("| --- | --- | --- | --- | ---: | --- | --- | ---: | ---: |")
        scene_placement = (payload.get("missionTimeline") or {}).get("scenePlacement") or {}

        def pos_label(pos: Any) -> str:
            if not isinstance(pos, dict):
                return "-"
            try:
                return (
                    f"{float(pos.get('x', 0.0)):.1f},"
                    f"{float(pos.get('y', 0.0)):.1f},"
                    f"{float(pos.get('z', 0.0)):.1f}"
                )
            except (TypeError, ValueError):
                return "-"

        for match in spatial_matches[:80]:
            if not isinstance(match, dict):
                continue
            scene_key = safe_key(match.get("sceneKey"))
            placement = scene_placement.get(scene_key) or {}
            pin = match.get("pin") if isinstance(match.get("pin"), dict) else {}
            pin_name = safe_key(pin.get("label")) or safe_key(pin.get("missionAreaId")) or safe_key(pin.get("trackingType")) or "-"
            parent_raw = pin.get("subDataParentId") or pin.get("levelDataParentId")
            if parent_raw not in (None, "", [], {}):
                pin_name += f" parent {parent_raw}"
            script_label = f"{match.get('mapId') or match.get('levelId') or '?'}/{match.get('scriptId') or '?'}"
            lines.append(
                "| "
                f"`{md_escape(scene_key)}` "
                f"| `{md_escape(match.get('questId'))}` "
                f"| `{md_escape(placement.get('chunkId') or '-')}` "
                f"| `{md_escape(script_label)}` "
                f"| {match.get('offset', '')} "
                f"| {md_escape(pos_label(match.get('position')))} "
                f"| {md_escape(pin_name + '@' + pos_label(pin.get('position')))} "
                f"| {match.get('distanceXZ', '')} "
                f"| {match.get('yDelta', '')} |"
            )
        if len(spatial_matches) > 80:
            lines.append(f"- _... +{len(spatial_matches) - 80} more matches_")
    else:
        lines.append("- _(none)_")

    chunk_order = (payload.get("missionTimeline") or {}).get("chunkOrder") or {}
    co_edges = chunk_order.get("edges") or []
    co_parallel = chunk_order.get("parallel") or []
    co_incomparable = chunk_order.get("incomparable") or []
    co_unattached = chunk_order.get("unattachedChunkIds") or []
    lines.extend(["", "## Chunk Order (questDag)", ""])
    if co_edges or co_parallel or co_incomparable or co_unattached:
        if co_edges:
            lines.append("Directed edges:")
            lines.append("")
            for edge in co_edges:
                from_q = ", ".join(f"`{md_escape(q)}`" for q in edge.get("fromQuests") or [])
                to_q = ", ".join(f"`{md_escape(q)}`" for q in edge.get("toQuests") or [])
                lines.append(
                    f"- `{md_escape(edge.get('from'))}` → `{md_escape(edge.get('to'))}` "
                    f"(from {from_q} → to {to_q})"
                )
            lines.append("")
        if co_parallel:
            lines.append("Parallel pairs (share at least one quest, not orderable by questDag):")
            for pair in co_parallel:
                lines.append(f"- `{md_escape(pair[0])}` ‖ `{md_escape(pair[1])}`")
            lines.append("")
        if co_incomparable:
            lines.append(
                "Incomparable pairs (disjoint quest attachments, no provable order):"
            )
            for pair in co_incomparable:
                lines.append(f"- `{md_escape(pair[0])}` ⊥ `{md_escape(pair[1])}`")
            lines.append("")
        if co_unattached:
            unattached_text = ", ".join(f"`{md_escape(cid)}`" for cid in co_unattached)
            lines.append(
                f"Chunks with no quest attachments: {unattached_text}"
            )
            lines.append("")
    else:
        lines.append("- _(no chunk-order evidence)_")

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

    lines.extend(["", "## LevelData Interaction Order Diagnostics", ""])
    wrote_leveldata_sequence = False
    for item in payload["levelDataFiles"]:
        sequence = item.get("matchedSequence") or []
        unique_keys = item.get("matchedUniqueKeys") or []
        if len(unique_keys) < 2:
            continue
        wrote_leveldata_sequence = True
        text = " -> ".join(md_escape(key) for key in unique_keys)
        lines.append(f"- `{md_escape(item.get('levelId'))}` `{md_escape(item.get('file'))}`: {text}")
        for hit in sequence[:20]:
            context = []
            if hit.get("entity"):
                context.append(f"entity={hit.get('entity')}")
            if hit.get("questId"):
                context.append(f"quest={hit.get('questId')}")
            if hit.get("readingPopupId"):
                context.append(f"rp={hit.get('readingPopupId')}")
            if hit.get("prtsId"):
                context.append(f"prts={hit.get('prtsId')}")
            detail = "; ".join(context)
            lines.append(
                f"  - `{md_escape(hit.get('key'))}` offset `{hit.get('offset')}`"
                + (f" ({md_escape(detail)})" if detail else "")
            )
    if not wrote_leveldata_sequence:
        lines.append("- _(none)_")

    lines.extend(["", "## Reading/PRTS Exact Links and Cross-References", ""])
    wrote_reading_prts = False
    for key, info in payload["entries"].items():
        links = info["hits"].get("readingPrts")
        if not links:
            continue
        wrote_reading_prts = True
        lines.append(f"- `{md_escape(key)}`")
        for row in links.get("readingPopups") or []:
            lines.append(
                "  - exact ReadingPopUp "
                f"`{md_escape(row.get('id'))}` content=`{md_escape(row.get('contentId'))}` "
                f"bg={row.get('bgType')} icon={row.get('iconType')}"
            )
        for row in links.get("prtsItems") or []:
            lines.append(
                "  - exact "
                f"{md_escape(row.get('table'))} `{md_escape(row.get('id'))}` "
                f"content=`{md_escape(row.get('contentId'))}` "
                f"firstLv=`{md_escape(row.get('firstLvId'))}` "
                f"order={row.get('order')} type=`{md_escape(row.get('type'))}`"
            )
        for row in links.get("crossReferences") or []:
            lines.append(
                "  - suffix cross-reference only (not evidence): "
                f"{md_escape(row.get('table'))} `{md_escape(row.get('id'))}` "
                f"content=`{md_escape(row.get('contentId'))}`"
            )
    if not wrote_reading_prts:
        lines.append("- _(none)_")

    lines.extend(["", "## LevelData Quest Ownership", ""])
    if payload.get("levelDataQuestOwners"):
        lines.append("| quest | owner mission | level | flow | prev | child quests | story refs |")
        lines.append("| --- | --- | --- | ---: | --- | --- | --- |")
        for owner in payload["levelDataQuestOwners"]:
            if owner.get("missingMissionRuntimeOwner"):
                lines.append(
                    "| "
                    f"`{md_escape(owner.get('questId'))}` "
                    "| _(missing)_ |  |  |  |  |  |"
                )
                continue
            story_refs = ", ".join(f"`{md_escape(ref)}`" for ref in (owner.get("storyRefs") or [])[:8])
            if len(owner.get("storyRefs") or []) > 8:
                story_refs += ", ..."
            lines.append(
                "| "
                f"`{md_escape(owner.get('questId'))}` "
                f"| `{md_escape(owner.get('mission'))}` "
                f"| `{md_escape(owner.get('levelId'))}` "
                f"| {owner.get('flowIndex') if owner.get('flowIndex') is not None else ''} "
                f"| {md_escape(', '.join(owner.get('prevQuestIds') or []))} "
                f"| {md_escape(', '.join(owner.get('childQuestIds') or []))} "
                f"| {story_refs} |"
            )
    else:
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
        "- Quest-attached NPC proxy evidence can anchor a dialog to that quest. Mission-level NpcProxyEx context proves only that the original runtime can select that mission-scoped dialog row; the server-selected one-based active row is not mission activation or cross-row chronology.",
        "- LevelScript string offset order is weak until record types or trigger ownership are decoded.",
        "- LevelData byte-string hits can expose trigger state and spatial context, but are weak until decoded.",
        "- Exact Reading/PRTS contentId links can expose authored collection membership. Same-number/suffix matches across Story kinds are cross-reference only and are not ownership, playback, or chronology evidence.",
        "- Radio/Audio and AssetMap hits validate file families and line membership, but do not prove inter-file chronology alone.",
        "- Map and spatial data should be used as tie-break or diagnostic evidence unless an explicit quest reference links the same target.",
    ])
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", default="CN")
    parser.add_argument(
        "--mission",
        action="append",
        default=[],
        help="Mission id, comma-list accepted. Required unless --all-target-prefixes is set.",
    )
    parser.add_argument(
        "--all-target-prefixes",
        action="store_true",
        help=(
            "Audit every mission in mission_timeline_recovery whose id starts "
            f"with one of {', '.join(TARGET_MISSION_PREFIXES)} "
            "(authored story missions; excludes db/dm/hidden/map*)."
        ),
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=ROOT / "reports",
        help="Report root for mission-order audit outputs.",
    )
    parser.add_argument(
        "--story-reports-dir",
        type=Path,
        default=ROOT / "reports" / "story" / "build",
        help="Story build report directory containing mission_timeline_recovery_<LANG>.json.",
    )
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


def collect_target_prefix_missions(language: str, reports_dir: Path) -> list[str]:
    timeline_path = reports_dir / f"mission_timeline_recovery_{language}.json"
    payload = read_json(timeline_path, {})
    out: list[str] = []
    for entry in payload.get("missions") or []:
        mission_id = entry.get("mission") or ""
        if mission_id and mission_id_matches_target_prefix(mission_id):
            out.append(mission_id)
    return unique_preserve(out)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_dir = args.reports_dir / "mission_order"
    out_dir.mkdir(parents=True, exist_ok=True)
    missions = split_missions(args.mission)
    if args.all_target_prefixes:
        missions.extend(collect_target_prefix_missions(args.language, args.story_reports_dir))
        missions = unique_preserve(missions)
    if not missions:
        print(
            "error: pass --mission ... or --all-target-prefixes",
            file=sys.stderr,
        )
        return 2
    for mission in missions:
        payload = build_report(
            mission,
            language=args.language,
            reports_dir=args.story_reports_dir,
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
            "MissionRuntime/proxy/variant/LevelScript hits."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
