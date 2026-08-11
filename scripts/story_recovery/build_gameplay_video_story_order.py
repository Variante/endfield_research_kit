#!/usr/bin/env python3
"""Match gameplay-video OCR evidence to Story entries and write OCR-only order lists.

This is a conservative promotion pipeline:

1. Optionally run the OCR sampler.
2. Match completed OCR segments against known WebUI Story text.
3. Collapse timestamped matches into observed per-mission scene sequences.
4. Write those observed sequences as a read-only OCR proposal.

The OCR pass intentionally does not seed, merge, calibrate, or lock against the
active order override (``webui/overrides/story_order.json``). The generated
reports and ``webui/data/story_order_ocr.json`` are OCR-only comparison
evidence; users combine OCR, static recovery, and manual evidence separately.
"""
from __future__ import annotations

import argparse
import html
import json
import math
import os
import re
import subprocess
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "scripts", ROOT / "scripts" / "story_recovery"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from common import (  # noqa: E402
    REPORTS_DIR,
    md_escape,
    read_json,
    rel_path,
    safe_key,
    write_report_json,
    write_text_if_changed,
)

CONV_ROOT = ROOT / "webui" / "data" / "lang" / "CN" / "conv"
ACTIVE_STORY_ORDER_PATH = ROOT / "webui" / "overrides" / "story_order.json"
MISSIONS_PATH = ROOT / "webui" / "data" / "lang" / "CN" / "missions.json"
OCR_REPORT_DIR = REPORTS_DIR / "gameplay_video_ocr"
OCR_SCRIPT_PATH = ROOT / "scripts" / "story_recovery" / "build_gameplay_video_ocr_audit.py"
MIN_OCR_TOOL_VERSION = 17
ARCHIVE_BOX_CROP_MODE = "fixed-dark-roi"
DEFAULT_THRESHOLD_SWEEP = (0.98, 0.95, 0.90, 0.86, 0.80, 0.75, 0.70, 0.65, 0.60, 0.50)
LINE_LIKE_SOURCES = {"line", "summary"}
MAP_DIALOG_COMPANION_SOURCE = "map-dialog-companion"
DEFAULT_RANSAC_TOLERANCE = 3.5
ARCHIVE_KINDS = {"prts"}
ARCHIVE_KEY_PREFIXES = ("nar_",)
COMPANION_STOP_BIGRAMS = {
    "一个",
    "一些",
    "不会",
    "不是",
    "不能",
    "不要",
    "他们",
    "你们",
    "我们",
    "但是",
    "到了",
    "前面",
    "后面",
    "因为",
    "大家",
    "如果",
    "已经",
    "时候",
    "是什么",
    "是不是",
    "有人",
    "没有",
    "的事",
    "的是",
    "的人",
    "的地",
    "的记",
    "的纸",
    "看见",
    "看到",
    "自己",
    "虽然",
    "裂地",
    "这里",
    "这个",
    "这些",
    "这边",
    "那个",
    "那些",
    "还是",
    "遇到",
    "里面",
}

BR_TAG_RE = re.compile(r"<\s*br\s*/?\s*>", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")
ASCII_WORD_RE = re.compile(r"^[a-z0-9_:\-.]+$")
STORY_KIND_RE = re.compile(r"^(?:misc_)?([a-z]+)")
NATURAL_SORT_RE = re.compile(r"\d+|\D+")
GAMEPLAY_VIDEO_PART_RE = re.compile(r"(?:^|_)P(\d+)(?:_|$)", re.IGNORECASE)
GAMEPLAY_VIDEO_BVID_RE = re.compile(r"(BV[0-9A-Za-z]+)", re.IGNORECASE)

# These only choose which generated Story mission corpus a video is searched
# against. They do not seed OCR result keys, order, locks, or inferred entries.
VIDEO_SEARCH_SCOPE_OVERRIDES = {
    ("bv1jdzmbseuc", 1): {"missionPrefix": "e0", "title": "e0*"},
    ("bv1gczqbrehj", 15): {"mission": "c31m1", "title": "c31m1"},
    ("bv1gczqbrehj", 16): {"mission": "c31m2", "title": "c31m2"},
    ("bv1gczqbrehj", 17): {"mission": "c31m3", "title": "c31m3"},
}


@dataclass(frozen=True)
class CorpusLine:
    key: str
    mission: str
    actual_mission: str
    link_reason: str
    kind: str
    scene: int | None
    line_id: str
    source: str
    text: str
    norm: str


@dataclass(frozen=True)
class StoryTextRecord:
    key: str
    mission: str
    kind: str
    scene: int | None
    first_line_id: str
    first_text: str
    title_norm: str
    norm: str
    grams: set[str]
    title_grams: set[str]


@dataclass(frozen=True)
class MissionTitleCandidate:
    mission: str
    title: str
    norm: str
    loose_norm: str


def normalize_text(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = TAG_RE.sub("", text)
    text = unicodedata.normalize("NFKC", text).lower()
    out: list[str] = []
    for ch in text:
        code = ord(ch)
        if "\u4e00" <= ch <= "\u9fff" or "\u3400" <= ch <= "\u4dbf":
            out.append(ch)
        elif "a" <= ch <= "z" or "0" <= ch <= "9":
            out.append(ch)
    return "".join(out)


def useful_norm(norm: str, *, min_chars: int) -> bool:
    if len(norm) < min_chars:
        return False
    cjk = sum(1 for ch in norm if "\u3400" <= ch <= "\u9fff")
    alpha = sum(1 for ch in norm if "a" <= ch <= "z")
    if cjk >= 2:
        return True
    return alpha >= max(4, min_chars)


def int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def companion_grams(norm: str) -> set[str]:
    if len(norm) < 2:
        return set()
    return {
        norm[index : index + 2]
        for index in range(len(norm) - 1)
        if norm[index : index + 2] not in COMPANION_STOP_BIGRAMS
    }


def mission_title_loose_norm(norm: str) -> str:
    return norm.replace("的", "").replace("侯", "候")


def mission_title_variants(value: Any) -> list[str]:
    text = safe_key(value)
    if not text:
        return []
    variants = [part.strip() for part in re.split(r"\s*[\/／]\s*", text) if part.strip()]
    return variants or [text]


def gameplay_video_part_number(video_name: Any) -> int | None:
    match = GAMEPLAY_VIDEO_PART_RE.search(video_file_basename(video_name))
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def gameplay_video_series_key(video_name: Any) -> str:
    basename = video_file_basename(video_name)
    bvid_match = GAMEPLAY_VIDEO_BVID_RE.search(basename)
    if bvid_match:
        return bvid_match.group(1).lower()
    stem = Path(basename).stem
    part_match = GAMEPLAY_VIDEO_PART_RE.search(stem)
    if part_match:
        return stem[: part_match.start()].lower()
    return stem.lower()


def video_search_scope_override(
    video_name: str,
    candidates: list[MissionTitleCandidate],
) -> dict[str, Any] | None:
    part = gameplay_video_part_number(video_name)
    if part is None:
        return None
    rule = VIDEO_SEARCH_SCOPE_OVERRIDES.get((gameplay_video_series_key(video_name), part))
    if not rule:
        return None

    mission = safe_key(rule.get("mission"))
    title = safe_key(rule.get("title")) or mission
    if mission:
        return {
            "status": "matched",
            "mission": mission,
            "title": title,
            "match": "video-scope-override",
            "searchMissions": [mission],
            "candidates": [{"mission": mission, "title": title, "match": "video-scope-override"}],
        }

    prefix = safe_key(rule.get("missionPrefix")).lower()
    if not prefix:
        return None
    search_missions: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        candidate_mission = safe_key(candidate.mission)
        if not candidate_mission or not candidate_mission.lower().startswith(prefix):
            continue
        if candidate_mission in seen:
            continue
        seen.add(candidate_mission)
        search_missions.append(candidate_mission)
    search_missions.sort(key=natural_sort_token)
    label = title or f"{prefix}*"
    return {
        "status": "matched" if search_missions else "unmatched",
        "mission": label,
        "title": label,
        "match": "video-scope-override-prefix",
        "searchMissions": search_missions,
        "candidates": [
            {"mission": mission_key, "title": label, "match": "video-scope-override-prefix"}
            for mission_key in search_missions[:8]
        ],
    }


def load_mission_title_candidates(
    path: Path,
    story_order: dict[str, Any] | None = None,
) -> list[MissionTitleCandidate]:
    payload = read_json(path, {})
    names = payload.get("missionNames") if isinstance(payload, dict) else {}
    if not isinstance(names, dict):
        names = {}
    story_orders = story_orders_by_mission(story_order or {})
    if story_orders:
        missions = sorted(story_orders, key=natural_sort_token)
    else:
        missions = sorted(
            {safe_key(mission) for mission in names if safe_key(mission)},
            key=natural_sort_token,
        )
    out: list[MissionTitleCandidate] = []
    seen: set[tuple[str, str]] = set()
    for mission in missions:
        titles = mission_title_variants(names.get(mission))
        if mission not in titles:
            titles.append(mission)
        for title in titles:
            norm = normalize_text(title)
            if len(norm) < 2:
                continue
            key = (mission, norm)
            if key in seen:
                continue
            seen.add(key)
            out.append(MissionTitleCandidate(
                mission=mission,
                title=title,
                norm=norm,
                loose_norm=mission_title_loose_norm(norm),
            ))
    return out


def infer_video_mission(
    video_name: str,
    candidates: list[MissionTitleCandidate],
) -> dict[str, Any]:
    video_norm = normalize_text(video_name)
    video_loose_norm = mission_title_loose_norm(video_norm)
    hits: list[dict[str, Any]] = []
    for candidate in candidates:
        exact_index = video_norm.find(candidate.norm)
        if exact_index >= 0:
            hits.append({
                "mission": candidate.mission,
                "title": candidate.title,
                "match": "exact",
                "start": exact_index,
                "length": len(candidate.norm),
            })
        loose_index = video_loose_norm.find(candidate.loose_norm)
        if loose_index >= 0 and not (
            exact_index == loose_index
            and candidate.loose_norm == candidate.norm
            and video_loose_norm == video_norm
        ):
            hits.append({
                "mission": candidate.mission,
                "title": candidate.title,
                "match": "loose",
                "start": loose_index,
                "length": len(candidate.loose_norm),
            })

    if not hits:
        return {
            "status": "unmatched",
            "candidates": [],
        }

    best_by_mission: dict[str, dict[str, Any]] = {}
    for hit in sorted(hits, key=lambda row: (row["start"], -row["length"], row["match"] != "exact", row["mission"])):
        old = best_by_mission.get(hit["mission"])
        if old is None:
            best_by_mission[hit["mission"]] = hit

    ranked = sorted(
        best_by_mission.values(),
        key=lambda row: (row["start"], -row["length"], row["match"] != "exact", row["mission"]),
    )
    best = ranked[0]
    tied = [
        row for row in ranked
        if row["mission"] != best["mission"]
        and row["start"] == best["start"]
        and row["length"] == best["length"]
    ]
    if tied:
        return {
            "status": "ambiguous",
            "candidates": ranked[:8],
        }
    return {
        "status": "matched",
        "mission": best["mission"],
        "title": best["title"],
        "match": best["match"],
        "candidates": ranked[:8],
    }


def html_to_match_text(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = BR_TAG_RE.sub("\n", text)
    text = TAG_RE.sub("", text)
    text = unicodedata.normalize("NFKC", text)
    return text.replace("\r\n", "\n").replace("\r", "\n")


def clean_ocr_text_for_matching(value: Any) -> str:
    return html_to_match_text(value)


def grams(norm: str, size: int = 3) -> set[str]:
    if len(norm) <= size:
        return {norm} if norm else set()
    return {norm[index : index + size] for index in range(len(norm) - size + 1)}


def story_kind(key: str, payload: dict[str, Any]) -> str:
    kind = safe_key(payload.get("kind"))
    if kind:
        return kind
    stripped = key[5:] if key.startswith("misc_") else key
    match = STORY_KIND_RE.match(stripped)
    return match.group(1) if match else ""


def is_archive_story_entry(key: str, payload: dict[str, Any]) -> bool:
    kind = story_kind(key, payload)
    if kind in ARCHIVE_KINDS:
        return True
    return any(key.startswith(prefix) for prefix in ARCHIVE_KEY_PREFIXES)


def is_archive_corpus_line(line: CorpusLine) -> bool:
    if safe_key(line.kind) in ARCHIVE_KINDS:
        return True
    return any(line.key.startswith(prefix) for prefix in ARCHIVE_KEY_PREFIXES)


def iter_text_rows(
    payload: dict[str, Any],
    *,
    include_titles: bool = False,
) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    title = safe_key(payload.get("title")) if include_titles else ""
    if include_titles and title:
        rows.append(("title", "title", title))
    for line in payload.get("lines") or []:
        if isinstance(line, dict):
            rows.append((safe_key(line.get("id")), "line", safe_key(line.get("text"))))
    for index, summary in enumerate(payload.get("summary") or []):
        if isinstance(summary, dict):
            rows.append((f"summary:{index}", "summary", safe_key(summary.get("text"))))
    for group in payload.get("optionGroups") or []:
        if not isinstance(group, dict):
            continue
        group_id = safe_key(group.get("g"))
        for option in group.get("options") or []:
            if isinstance(option, dict):
                rows.append((
                    safe_key(option.get("id")) or f"option:{group_id}",
                    "option",
                    safe_key(option.get("text")),
                ))
    return rows


def load_corpus(
    *,
    conv_root: Path,
    story_order: dict[str, Any],
    min_chars: int,
    include_titles: bool = False,
    restrict_to_story_order: bool = True,
) -> list[CorpusLine]:
    story_orders = story_orders_by_mission(story_order)
    story_mission_by_key: dict[str, str] = {}
    for mission_id, order in story_orders.items():
        for key in order:
            story_mission_by_key.setdefault(key, mission_id)
    allowed_keys = {key for order in story_orders.values() for key in order} if restrict_to_story_order else set()
    out: list[CorpusLine] = []
    for path in sorted(conv_root.glob("*.json")):
        key = path.stem
        payload = read_json(path, {})
        if not isinstance(payload, dict):
            continue
        archive_entry = is_archive_story_entry(key, payload)
        if restrict_to_story_order and allowed_keys and key not in allowed_keys and not key.startswith("dlg_map") and not archive_entry:
            continue
        native_mission = safe_key(payload.get("mission"))
        mission = story_mission_by_key.get(key) if restrict_to_story_order else ""
        if not mission:
            mission = native_mission
        if not mission:
            for mission_id, order in story_orders.items():
                if key in order:
                    mission = mission_id
                    break
        if not mission:
            continue
        kind = story_kind(key, payload)
        scene = int_or_none(payload.get("scene"))
        for line_id, source, text in iter_text_rows(payload, include_titles=include_titles):
            norm = normalize_text(text)
            if not useful_norm(norm, min_chars=min_chars):
                continue
            out.append(CorpusLine(
                key=key,
                mission=mission,
                actual_mission=native_mission or mission,
                link_reason="native" if mission == (native_mission or mission) else "story-order",
                kind=kind,
                scene=scene,
                line_id=line_id,
                source=source,
                text=text,
                norm=norm,
            ))
    return out


def related_corpus_missions_for_story_mission(
    story_order: dict[str, Any],
) -> dict[str, list[dict[str, str]]]:
    missions = story_order.get("missions") if isinstance(story_order, dict) else {}
    if not isinstance(missions, dict):
        return {}

    out: dict[str, list[dict[str, str]]] = {}
    for mission_id, mission_payload in missions.items():
        mission = safe_key(mission_id)
        if not mission or not isinstance(mission_payload, dict):
            continue
        related: list[dict[str, str]] = []
        seen = {mission}

        def add_related(value: Any, reason: str) -> None:
            key = safe_key(value)
            if not key or key in seen:
                return
            seen.add(key)
            related.append({"mission": key, "reason": reason})

        level = safe_key(mission_payload.get("level"))
        if level:
            add_related(level, "mission-level")
            add_related(f"{level}_env", "mission-level-env")
        levels = mission_payload.get("levels")
        if isinstance(levels, list):
            for raw_level in levels:
                level_key = safe_key(raw_level)
                if not level_key:
                    continue
                add_related(level_key, "mission-level")
                add_related(f"{level_key}_env", "mission-level-env")
        out[mission] = related
    return out


def retarget_corpus_line(line: CorpusLine, mission: str, reason: str) -> CorpusLine:
    if line.mission == mission and line.link_reason == "native":
        return line
    return CorpusLine(
        key=line.key,
        mission=mission,
        actual_mission=line.actual_mission,
        link_reason=reason,
        kind=line.kind,
        scene=line.scene,
        line_id=line.line_id,
        source=line.source,
        text=line.text,
        norm=line.norm,
    )


def corpus_for_video_mission(
    target_mission: str,
    *,
    corpus_by_mission: dict[str, list[CorpusLine]],
    related_missions_by_mission: dict[str, list[dict[str, str]]],
) -> tuple[list[CorpusLine], list[dict[str, Any]]]:
    out: list[CorpusLine] = []
    related_rows: list[dict[str, Any]] = []
    seen_lines: set[tuple[str, str, str]] = set()

    def add_lines(
        lines: list[CorpusLine],
        *,
        as_mission: str,
        reason: str,
        supplemental_only_map_dialogs: bool = False,
    ) -> int:
        added = 0
        for line in lines:
            if supplemental_only_map_dialogs and not (
                line.key.startswith("dlg_map") or is_archive_corpus_line(line)
            ):
                continue
            key = (line.key, line.line_id, reason)
            if key in seen_lines:
                continue
            seen_lines.add(key)
            out.append(retarget_corpus_line(line, as_mission, reason))
            added += 1
        return added

    add_lines(corpus_by_mission.get(target_mission) or [], as_mission=target_mission, reason="native")
    for related in related_missions_by_mission.get(target_mission) or []:
        related_mission = safe_key(related.get("mission"))
        if not related_mission:
            continue
        count = add_lines(
            corpus_by_mission.get(related_mission) or [],
            as_mission=target_mission,
            reason=safe_key(related.get("reason")) or "related-mission",
            supplemental_only_map_dialogs=True,
        )
        if count:
            related_rows.append({
                "mission": related_mission,
                "reason": safe_key(related.get("reason")) or "related-mission",
                "rows": count,
            })
    return out, related_rows


def corpus_for_search_missions(
    search_missions: list[dict[str, Any]],
    *,
    corpus_by_mission: dict[str, list[CorpusLine]],
    related_missions_by_mission: dict[str, list[dict[str, str]]],
) -> tuple[list[CorpusLine], list[dict[str, Any]]]:
    out: list[CorpusLine] = []
    related_rows: list[dict[str, Any]] = []
    seen_lines: set[tuple[str, str, str, str]] = set()
    for search_row in search_missions:
        mission = safe_key(search_row.get("mission"))
        if not mission:
            continue
        mission_corpus, mission_related = corpus_for_video_mission(
            mission,
            corpus_by_mission=corpus_by_mission,
            related_missions_by_mission=related_missions_by_mission,
        )
        added = 0
        for line in mission_corpus:
            key = (line.key, line.line_id, line.mission, line.link_reason)
            if key in seen_lines:
                continue
            seen_lines.add(key)
            out.append(line)
            added += 1
        if added:
            related_rows.append({
                "mission": mission,
                "reason": safe_key(search_row.get("reason")) or "target-video",
                "video": safe_key(search_row.get("video")),
                "part": search_row.get("part"),
                "offset": int_or_none(search_row.get("offset")),
                "rows": added,
            })
        for related in mission_related:
            related_rows.append({
                **related,
                "searchMission": mission,
                "searchReason": safe_key(search_row.get("reason")) or "target-video",
                "searchVideo": safe_key(search_row.get("video")),
                "searchPart": search_row.get("part"),
                "searchOffset": int_or_none(search_row.get("offset")),
            })
    return out, related_rows


def seconds_to_clock(seconds: float | None) -> str:
    if seconds is None or not math.isfinite(seconds):
        return ""
    total_ms = max(0, int(round(seconds * 1000)))
    ms = total_ms % 1000
    total_seconds = total_ms // 1000
    sec = total_seconds % 60
    total_minutes = total_seconds // 60
    minute = total_minutes % 60
    hour = total_minutes // 60
    return f"{hour:02d}:{minute:02d}:{sec:02d}.{ms:03d}"


def clock_to_seconds(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        seconds = float(value)
        return seconds if math.isfinite(seconds) and seconds >= 0 else None
    text = safe_key(value)
    if not text:
        return None
    pieces = text.split(":")
    try:
        if len(pieces) == 1:
            seconds = float(pieces[0])
        elif len(pieces) == 2:
            seconds = int(pieces[0]) * 60 + float(pieces[1])
        elif len(pieces) == 3:
            seconds = int(pieces[0]) * 3600 + int(pieces[1]) * 60 + float(pieces[2])
        else:
            return None
    except ValueError:
        return None
    return seconds if math.isfinite(seconds) and seconds >= 0 else None


def build_story_text_records(corpus: list[CorpusLine]) -> list[StoryTextRecord]:
    rows: dict[str, dict[str, Any]] = {}
    norms_by_key: dict[str, list[str]] = defaultdict(list)
    title_norms_by_key: dict[str, list[str]] = defaultdict(list)
    for line in corpus:
        key = safe_key(line.key)
        if not key:
            continue
        row = rows.get(key)
        if row is None:
            row = {
                "mission": line.actual_mission or line.mission,
                "kind": line.kind,
                "scene": line.scene,
                "first_line_id": "",
                "first_text": "",
            }
            rows[key] = row
        norms_by_key[key].append(line.norm)
        if line.source == "title":
            title_norms_by_key[key].append(line.norm)
        if line.source in LINE_LIKE_SOURCES and not row["first_line_id"]:
            row["first_line_id"] = line.line_id
            row["first_text"] = line.text
        elif not row["first_text"]:
            row["first_line_id"] = line.line_id
            row["first_text"] = line.text

    records: list[StoryTextRecord] = []
    for key, row in rows.items():
        norm = "".join(norms_by_key.get(key) or [])
        title_norm = "".join(title_norms_by_key.get(key) or [])
        records.append(StoryTextRecord(
            key=key,
            mission=safe_key(row.get("mission")),
            kind=safe_key(row.get("kind")),
            scene=row.get("scene") if isinstance(row.get("scene"), int) else None,
            first_line_id=safe_key(row.get("first_line_id")),
            first_text=safe_key(row.get("first_text")),
            title_norm=title_norm,
            norm=norm,
            grams=companion_grams(norm),
            title_grams=companion_grams(title_norm),
        ))
    return records


def build_map_dialog_companion_index(corpus: list[CorpusLine]) -> dict[str, list[dict[str, Any]]]:
    records = build_story_text_records(corpus)
    records_by_mission: dict[str, list[StoryTextRecord]] = defaultdict(list)
    for record in records:
        if record.mission:
            records_by_mission[record.mission].append(record)

    companion_index: dict[str, list[dict[str, Any]]] = {}
    for mission, mission_records in records_by_mission.items():
        dialogs = [
            record
            for record in mission_records
            if record.key.startswith("dlg_map") and record.grams
        ]
        archives = [
            record
            for record in mission_records
            if record.grams
            and (
                safe_key(record.kind) in ARCHIVE_KINDS
                or any(record.key.startswith(prefix) for prefix in ARCHIVE_KEY_PREFIXES)
            )
        ]
        if not dialogs or not archives:
            continue

        gram_doc_counts: Counter[str] = Counter()
        for record in mission_records:
            gram_doc_counts.update(record.grams)
        rare_limit = max(3, int(len(mission_records) * 0.2))
        rare_grams = {
            gram
            for gram, count in gram_doc_counts.items()
            if count <= rare_limit and gram not in COMPANION_STOP_BIGRAMS
        }

        for archive in archives:
            companions: list[dict[str, Any]] = []
            candidate_dialogs = (
                [dialog for dialog in dialogs if dialog.scene == archive.scene]
                if archive.scene is not None
                else dialogs
            )
            for dialog in candidate_dialogs:
                if dialog.key == archive.key:
                    continue
                same_scene = archive.scene is not None and archive.scene == dialog.scene
                shared = sorted((archive.grams & dialog.grams & rare_grams) - COMPANION_STOP_BIGRAMS)
                title_shared = sorted((archive.title_grams & dialog.grams & rare_grams) - COMPANION_STOP_BIGRAMS)
                if len(shared) < 2 or not title_shared:
                    continue
                reason = "archive-title-overlap"
                if same_scene:
                    reason = "same-scene-filter+archive-title-overlap"
                companions.append({
                    "key": dialog.key,
                    "mission": mission,
                    "kind": dialog.kind,
                    "scene": dialog.scene,
                    "lineId": dialog.first_line_id,
                    "text": dialog.first_text,
                    "reason": reason,
                    "sharedGrams": shared[:8],
                    "titleSharedGrams": title_shared[:8],
                })
            if companions:
                deduped: dict[str, dict[str, Any]] = {}
                for companion in sorted(
                    companions,
                    key=lambda row: (
                        row.get("scene") is None,
                        int(row.get("scene") or 1_000_000),
                        safe_key(row.get("key")),
                    ),
                ):
                    deduped.setdefault(safe_key(companion.get("key")), companion)
                companion_index[archive.key] = list(deduped.values())
    return companion_index


def shifted_companion_segment(segment: dict[str, Any], offset_seconds: float) -> dict[str, Any]:
    shifted = dict(segment)
    start_seconds = float_value(shifted.get("startTimeSeconds"))
    end_seconds = float_value(shifted.get("endTimeSeconds"), start_seconds)
    shifted_start = max(0.0, start_seconds + offset_seconds)
    shifted_end = max(shifted_start, end_seconds + offset_seconds)
    shifted["startTimeSeconds"] = round(shifted_start, 4)
    shifted["endTimeSeconds"] = round(shifted_end, 4)
    shifted["companionTimeOffsetSeconds"] = round(offset_seconds, 4)
    return shifted


def build_map_dialog_companion_matches(
    matches: list[dict[str, Any]],
    companion_index: dict[str, list[dict[str, Any]]],
    *,
    min_score: float,
    min_margin: float,
) -> list[dict[str, Any]]:
    if not companion_index:
        return []
    accepted_real_keys = {
        safe_key(match.get("best", {}).get("key"))
        for match in matches
        if match.get("accepted") and not match.get("synthetic")
    }
    out: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()
    for match in matches:
        if not match.get("accepted"):
            continue
        best = match.get("best") if isinstance(match.get("best"), dict) else {}
        archive_key = safe_key(best.get("key"))
        companions = companion_index.get(archive_key) or []
        if not archive_key or not companions:
            continue
        segment = match.get("segment") if isinstance(match.get("segment"), dict) else {}
        for companion_index_value, companion in enumerate(companions):
            companion_key = safe_key(companion.get("key"))
            if not companion_key or companion_key in accepted_real_keys:
                continue
            pair = (archive_key, companion_key)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            offset_seconds = -0.05 + companion_index_value * 0.001
            companion_segment = shifted_companion_segment(segment, offset_seconds)
            companion_segment["companionOf"] = archive_key
            companion_segment["companionReason"] = safe_key(companion.get("reason"))
            companion_best = {
                "score": min(0.995, float_value(best.get("score"), 0.995)),
                "fragment": safe_key(segment.get("text")),
                "key": companion_key,
                "mission": safe_key(best.get("mission")),
                "actualMission": safe_key(companion.get("mission")),
                "linkReason": "archive-context-map-dialog",
                "kind": safe_key(companion.get("kind")) or "dlg",
                "lineId": safe_key(companion.get("lineId")),
                "source": MAP_DIALOG_COMPANION_SOURCE,
                "text": safe_key(companion.get("text")),
                "companionOf": archive_key,
                "companionReason": safe_key(companion.get("reason")),
                "sharedGrams": companion.get("sharedGrams") or [],
                "titleSharedGrams": companion.get("titleSharedGrams") or [],
            }
            companion_match = {
                "segment": companion_segment,
                "best": companion_best,
                "margin": float_value(match.get("margin")),
                "top": [companion_best],
                "synthetic": True,
            }
            companion_match["accepted"] = is_accept(
                companion_match,
                min_score=min_score,
                min_margin=min_margin,
            )
            if companion_match["accepted"]:
                out.append(companion_match)
    return out


def build_gram_index(corpus: list[CorpusLine]) -> dict[str, list[int]]:
    index: dict[str, list[int]] = defaultdict(list)
    for line_index, line in enumerate(corpus):
        for gram in grams(line.norm):
            index[gram].append(line_index)
    return index


def fragment_texts(text: str, *, min_chars: int) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    raw_fragments = [text]
    raw_fragments.extend(str(text or "").splitlines())
    for raw in raw_fragments:
        stripped = raw.strip()
        if not stripped:
            continue
        # Pure OCR overlay tokens such as "UID: 1550644300" rarely help.
        if ASCII_WORD_RE.match(stripped.lower()) and not any("\u4e00" <= ch <= "\u9fff" for ch in stripped):
            continue
        norm = normalize_text(stripped)
        if norm in seen or not useful_norm(norm, min_chars=min_chars):
            continue
        seen.add(norm)
        out.append((stripped, norm))
    return out


def candidate_score(fragment_norm: str, line_norm: str) -> float:
    if not fragment_norm or not line_norm:
        return 0.0
    if line_norm in fragment_norm:
        return 1.0
    if fragment_norm in line_norm:
        return min(0.96, 0.72 + 0.24 * (len(fragment_norm) / max(1, len(line_norm))))
    matcher = SequenceMatcher(None, fragment_norm, line_norm, autojunk=False)
    ratio = matcher.ratio()
    longest = matcher.find_longest_match(0, len(fragment_norm), 0, len(line_norm)).size
    coverage = longest / max(1, len(line_norm))
    return max(ratio, coverage * 0.92)


def match_fragment(
    fragment_raw: str,
    fragment_norm: str,
    *,
    corpus: list[CorpusLine],
    gram_index: dict[str, list[int]],
    topn: int,
) -> list[dict[str, Any]]:
    counts: Counter[int] = Counter()
    for gram in grams(fragment_norm):
        counts.update(gram_index.get(gram) or [])
    if not counts:
        return []
    rows: list[dict[str, Any]] = []
    for line_index, _count in counts.most_common(120):
        line = corpus[line_index]
        score = candidate_score(fragment_norm, line.norm)
        if score <= 0:
            continue
        rows.append({
            "score": round(score, 4),
            "fragment": fragment_raw,
            "key": line.key,
            "mission": line.mission,
            "actualMission": line.actual_mission,
            "linkReason": line.link_reason,
            "kind": line.kind,
            "lineId": line.line_id,
            "source": line.source,
            "text": line.text,
        })
    rows.sort(key=lambda row: (-float(row["score"]), row["mission"], row["key"], row["lineId"]))
    return rows[:topn]


def aggregate_segment_match(
    segment: dict[str, Any],
    *,
    corpus: list[CorpusLine],
    gram_index: dict[str, list[int]],
    min_chars: int,
    topn: int,
) -> dict[str, Any] | None:
    raw_text = safe_key(segment.get("text"))
    text = clean_ocr_text_for_matching(raw_text)
    candidates: list[dict[str, Any]] = []
    for raw, norm in fragment_texts(text, min_chars=min_chars):
        candidates.extend(match_fragment(raw, norm, corpus=corpus, gram_index=gram_index, topn=topn))
    if not candidates:
        return None

    best_by_line: dict[tuple[str, str], dict[str, Any]] = {}
    for candidate in candidates:
        key = (safe_key(candidate.get("key")), safe_key(candidate.get("lineId")))
        old = best_by_line.get(key)
        if old is None or float(candidate["score"]) > float(old["score"]):
            best_by_line[key] = candidate
    ranked_lines = sorted(
        best_by_line.values(),
        key=lambda row: (-float(row["score"]), row["mission"], row["key"], row["lineId"]),
    )

    best_by_story: dict[str, dict[str, Any]] = {}
    for row in ranked_lines:
        story_key = safe_key(row.get("key"))
        old = best_by_story.get(story_key)
        if old is None or float(row["score"]) > float(old["score"]):
            best_by_story[story_key] = row
    ranked_story = sorted(
        best_by_story.values(),
        key=lambda row: (-float(row["score"]), row["mission"], row["key"]),
    )
    best = ranked_story[0]
    next_different = ranked_story[1] if len(ranked_story) > 1 else None
    margin = float(best["score"]) - float(next_different["score"]) if next_different else float(best["score"])
    segment_payload = {
        "startTime": segment.get("startTime"),
        "startTimeSeconds": segment.get("startTimeSeconds"),
        "endTime": segment.get("endTime"),
        "endTimeSeconds": segment.get("endTimeSeconds"),
        "sampleCount": segment.get("sampleCount"),
        "text": text,
    }
    for field in ("startFrame", "endFrame", "startSample", "endSample", "ocrCrops", "ocrPasses"):
        if segment.get(field) is not None:
            segment_payload[field] = segment.get(field)
    if text != raw_text:
        segment_payload["rawText"] = raw_text
    return {
        "segment": segment_payload,
        "best": best,
        "margin": round(margin, 4),
        "top": ranked_story[:topn],
    }


def is_accept(match: dict[str, Any], *, min_score: float, min_margin: float) -> bool:
    best = match.get("best") if isinstance(match.get("best"), dict) else {}
    score = float(best.get("score") or 0)
    margin = float(match.get("margin") or 0)
    if score >= 0.98:
        return margin >= min_margin / 2
    return score >= min_score and margin >= min_margin


def copy_matches_for_threshold(
    *,
    ocr_matches: list[dict[str, Any]],
    min_score: float,
    min_margin: float,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for match in ocr_matches:
        row = dict(match)
        row["accepted"] = is_accept(row, min_score=min_score, min_margin=min_margin)
        out.append(row)
    return out


def float_value(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def source_quality(source: Any) -> int:
    source_key = safe_key(source)
    if source_key in LINE_LIKE_SOURCES:
        return 2
    if source_key == MAP_DIALOG_COMPANION_SOURCE:
        return 1
    if source_key == "option":
        return 1
    return 0


def match_start_seconds(row: dict[str, Any]) -> float:
    segment = row.get("segment") if isinstance(row.get("segment"), dict) else {}
    return float_value(segment.get("startTimeSeconds"))


def match_end_seconds(row: dict[str, Any]) -> float:
    segment = row.get("segment") if isinstance(row.get("segment"), dict) else {}
    return float_value(segment.get("endTimeSeconds"), match_start_seconds(row))


def add_match_to_span(span: dict[str, Any], row: dict[str, Any]) -> None:
    segment = row.get("segment") if isinstance(row.get("segment"), dict) else {}
    best = row.get("best") if isinstance(row.get("best"), dict) else {}
    score = float_value(best.get("score"))
    source = safe_key(best.get("source"))
    source_counts = span.setdefault("sourceCounts", {})
    if isinstance(source_counts, dict):
        source_counts[source or "unknown"] = int(source_counts.get(source or "unknown") or 0) + 1
    actual_mission = safe_key(best.get("actualMission")) or safe_key(best.get("mission"))
    link_reason = safe_key(best.get("linkReason")) or "native"
    mission_links = span.setdefault("missionLinks", {})
    if isinstance(mission_links, dict):
        link_key = f"{actual_mission}:{link_reason}"
        mission_links[link_key] = int(mission_links.get(link_key) or 0) + 1

    span["lastTime"] = segment.get("endTime") or segment.get("startTime") or span.get("lastTime")
    span["lastTimeSeconds"] = match_end_seconds(row)
    span["matchCount"] = int(span.get("matchCount") or 0) + 1
    span["_scoreTotal"] = float_value(span.get("_scoreTotal")) + score
    if source in LINE_LIKE_SOURCES:
        span["lineLikeMatches"] = int(span.get("lineLikeMatches") or 0) + 1
    elif source == "option":
        span["optionMatches"] = int(span.get("optionMatches") or 0) + 1

    old_score = float_value(span.get("score"), -1.0)
    old_quality = source_quality(span.get("source"))
    new_quality = source_quality(source)
    if new_quality > old_quality or (new_quality == old_quality and score > old_score):
        span["score"] = best.get("score")
        span["lineId"] = best.get("lineId")
        span["source"] = source
        span["text"] = best.get("text")
        span["actualMission"] = actual_mission
        span["linkReason"] = link_reason
    span["maxScore"] = round(max(float_value(span.get("maxScore")), score), 4)


def make_observation_span(row: dict[str, Any]) -> dict[str, Any]:
    segment = row.get("segment") if isinstance(row.get("segment"), dict) else {}
    best = row.get("best") if isinstance(row.get("best"), dict) else {}
    span = {
        "key": safe_key(best.get("key")),
        "firstTime": segment.get("startTime"),
        "firstTimeSeconds": match_start_seconds(row),
        "lastTime": segment.get("endTime") or segment.get("startTime"),
        "lastTimeSeconds": match_end_seconds(row),
        "score": 0.0,
        "maxScore": 0.0,
        "lineId": "",
        "source": "",
        "actualMission": "",
        "linkReason": "",
        "text": "",
        "matchCount": 0,
        "lineLikeMatches": 0,
        "optionMatches": 0,
        "sourceCounts": {},
        "missionLinks": {},
        "_scoreTotal": 0.0,
    }
    add_match_to_span(span, row)
    return span


def finalize_observation_span(span: dict[str, Any]) -> dict[str, Any]:
    count = max(1, int(span.get("matchCount") or 0))
    score_total = float_value(span.pop("_scoreTotal", 0.0))
    span["avgScore"] = round(score_total / count, 4)
    source_counts = span.get("sourceCounts")
    if isinstance(source_counts, dict):
        span["sourceCounts"] = dict(sorted(source_counts.items()))
    mission_links = span.get("missionLinks")
    if isinstance(mission_links, dict):
        span["missionLinks"] = dict(sorted(mission_links.items()))
    return span


def build_observation_spans(matches: list[dict[str, Any]], mission: str) -> list[dict[str, Any]]:
    rows = [
        row for row in matches
        if row.get("accepted") and row.get("best", {}).get("mission") == mission
    ]
    rows.sort(key=match_start_seconds)
    spans: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for row in rows:
        best = row.get("best") if isinstance(row.get("best"), dict) else {}
        key = safe_key(best.get("key"))
        if not key:
            continue
        if current is not None and current.get("key") == key:
            add_match_to_span(current, row)
            continue
        if current is not None:
            spans.append(finalize_observation_span(current))
        current = make_observation_span(row)
    if current is not None:
        spans.append(finalize_observation_span(current))
    return spans


def span_ransac_point(span: dict[str, Any], positions: dict[str, int]) -> tuple[float, float] | None:
    key = safe_key(span.get("key"))
    if key not in positions:
        return None
    return (float_value(span.get("firstTimeSeconds")), float(positions[key]))


def fit_time_order_ransac(
    spans: list[dict[str, Any]],
    positions: dict[str, int],
    *,
    tolerance: float,
) -> dict[str, Any]:
    points: list[tuple[float, float, str]] = []
    for span in spans:
        point = span_ransac_point(span, positions)
        if point is None:
            continue
        strong_matches = int(span.get("lineLikeMatches") or 0)
        if strong_matches <= 0 and int(span.get("matchCount") or 0) < 2:
            continue
        points.append((point[0], point[1], safe_key(span.get("key"))))
    if len(points) < 2:
        for span in spans:
            point = span_ransac_point(span, positions)
            if point is not None:
                points.append((point[0], point[1], safe_key(span.get("key"))))
    if len(points) < 2:
        return {}

    best: dict[str, Any] = {}
    best_key: tuple[int, float, float] | None = None
    for left_index, left in enumerate(points):
        for right in points[left_index + 1:]:
            left_time, left_order, _left_key = left
            right_time, right_order, _right_key = right
            delta_time = right_time - left_time
            if abs(delta_time) < 1e-6:
                continue
            slope = (right_order - left_order) / delta_time
            if slope <= 0:
                continue
            intercept = left_order - slope * left_time
            residuals = [abs((slope * time_value + intercept) - order_value) for time_value, order_value, _key in points]
            inlier_residuals = [value for value in residuals if value <= tolerance]
            if not inlier_residuals:
                continue
            inlier_residuals.sort()
            median = inlier_residuals[len(inlier_residuals) // 2]
            total = sum(inlier_residuals)
            candidate_key = (len(inlier_residuals), -median, -total)
            if best_key is None or candidate_key > best_key:
                best_key = candidate_key
                best = {
                    "slope": slope,
                    "intercept": intercept,
                    "inliers": len(inlier_residuals),
                    "points": len(points),
                    "medianResidual": round(median, 4),
                    "tolerance": tolerance,
                }
    return best


def span_ransac_residual(
    span: dict[str, Any],
    positions: dict[str, int],
    model: dict[str, Any],
) -> float | None:
    point = span_ransac_point(span, positions)
    if point is None or not model:
        return None
    slope = float_value(model.get("slope"))
    intercept = float_value(model.get("intercept"))
    predicted = slope * point[0] + intercept
    return abs(predicted - point[1])


def summarize_span(span: dict[str, Any]) -> dict[str, Any]:
    out = {
        "key": safe_key(span.get("key")),
        "firstTime": span.get("firstTime"),
        "lastTime": span.get("lastTime"),
        "score": span.get("score"),
        "maxScore": span.get("maxScore"),
        "avgScore": span.get("avgScore"),
        "lineId": span.get("lineId"),
        "source": span.get("source"),
        "actualMission": span.get("actualMission"),
        "linkReason": span.get("linkReason"),
        "sourceCounts": span.get("sourceCounts"),
        "missionLinks": span.get("missionLinks"),
        "matchCount": span.get("matchCount"),
        "lineLikeMatches": span.get("lineLikeMatches"),
        "optionMatches": span.get("optionMatches"),
    }
    if span.get("ransacResidual") is not None:
        out["ransacResidual"] = span.get("ransacResidual")
    return out


def choose_representative_spans(
    spans: list[dict[str, Any]],
    current_order: list[str],
    *,
    use_ransac: bool,
    ransac_tolerance: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    positions = {key: index for index, key in enumerate(current_order)}
    model = fit_time_order_ransac(spans, positions, tolerance=ransac_tolerance) if use_ransac else {}
    for span in spans:
        residual = span_ransac_residual(span, positions, model)
        span["ransacResidual"] = round(residual, 4) if residual is not None else None
        if safe_key(span.get("key")) in positions:
            span["orderIndex"] = positions[safe_key(span.get("key"))]

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for span in spans:
        grouped[safe_key(span.get("key"))].append(span)

    selected: list[dict[str, Any]] = []
    adjusted = 0
    ignored = 0
    for key, choices in grouped.items():
        if len(choices) == 1:
            choice = dict(choices[0])
            choice["selectionReason"] = "only-span"
            selected.append(choice)
            continue

        line_like = [span for span in choices if int(span.get("lineLikeMatches") or 0) > 0]
        candidate_choices = line_like or choices

        def sort_key(span: dict[str, Any]) -> tuple[float, int, int, float, float]:
            residual = span.get("ransacResidual")
            residual_value = float_value(residual, 1_000_000.0) if model else 0.0
            return (
                residual_value,
                -int(span.get("lineLikeMatches") or 0),
                -int(span.get("matchCount") or 0),
                -float_value(span.get("maxScore")),
                float_value(span.get("firstTimeSeconds")),
            )

        chosen = min(candidate_choices, key=sort_key)
        chosen_index = choices.index(chosen)
        adjusted += 1 if chosen_index != 0 else 0
        ignored += len(choices) - 1
        choice = dict(chosen)
        if line_like and len(line_like) != len(choices):
            reason = "line-evidence-over-option"
        elif model:
            reason = "ransac"
        else:
            reason = "strongest-span"
        choice["selectionReason"] = reason
        choice["alternativeSpans"] = [summarize_span(span) for span in choices if span is not chosen]
        selected.append(choice)

    selected.sort(key=lambda span: float_value(span.get("firstTimeSeconds")))
    diagnostics = {
        "rawSpans": len(spans),
        "selectedSpans": len(selected),
        "repeatedKeys": sum(1 for choices in grouped.values() if len(choices) > 1),
        "adjustedRepeatedKeys": adjusted,
        "ignoredRepeatedSpans": ignored,
        "ransacModel": {
            **{key: value for key, value in model.items() if key not in {"slope", "intercept"}},
            "slope": round(float_value(model.get("slope")), 6),
            "intercept": round(float_value(model.get("intercept")), 4),
        } if model else {},
    }
    return selected, diagnostics


def score_bucket_label(bucket: int, *, bucket_count: int) -> str:
    lower = bucket / bucket_count
    upper = (bucket + 1) / bucket_count
    if bucket == bucket_count - 1:
        upper = 1.0
    return f"{lower:.2f}-{upper:.2f}"


def build_score_histogram(matches: list[dict[str, Any]], *, bucket_count: int = 20) -> list[dict[str, Any]]:
    counts = [0 for _ in range(bucket_count)]
    for match in matches:
        best = match.get("best") if isinstance(match.get("best"), dict) else {}
        score = max(0.0, min(1.0, float(best.get("score") or 0.0)))
        bucket = min(bucket_count - 1, int(score * bucket_count))
        counts[bucket] += 1
    return [
        {
            "range": score_bucket_label(bucket, bucket_count=bucket_count),
            "segments": count,
        }
        for bucket, count in enumerate(counts)
        if count
    ]


def build_threshold_sweep(
    matches: list[dict[str, Any]],
    *,
    min_margin: float,
    current_min_score: float,
) -> list[dict[str, Any]]:
    thresholds = sorted({round(value, 4) for value in (*DEFAULT_THRESHOLD_SWEEP, current_min_score)}, reverse=True)
    rows: list[dict[str, Any]] = []
    for threshold in thresholds:
        accepted = [
            match
            for match in matches
            if is_accept(match, min_score=threshold, min_margin=min_margin)
        ]
        story_keys = {
            safe_key(match.get("best", {}).get("key"))
            for match in accepted
            if safe_key(match.get("best", {}).get("key"))
        }
        line_ids = {
            (
                safe_key(match.get("best", {}).get("key")),
                safe_key(match.get("best", {}).get("lineId")),
            )
            for match in accepted
            if safe_key(match.get("best", {}).get("key")) and safe_key(match.get("best", {}).get("lineId"))
        }
        missions = {
            safe_key(match.get("best", {}).get("mission"))
            for match in accepted
            if safe_key(match.get("best", {}).get("mission"))
        }
        rows.append({
            "minScore": threshold,
            "acceptedSegments": len(accepted),
            "uniqueStoryKeys": len(story_keys),
            "uniqueLines": len(line_ids),
            "uniqueMissions": len(missions),
        })
    return rows


def load_ocr_reports(
    report_dir: Path,
    *,
    include_smoke: bool,
    min_tool_version: int,
    require_archive_box_ocr: bool,
) -> tuple[list[dict[str, Any]], Counter[str]]:
    reports: list[dict[str, Any]] = []
    stats: Counter[str] = Counter()
    for path in sorted(report_dir.glob("*_ocr.json")):
        if path.name == "gameplay_video_ocr_index.json":
            continue
        stats["seen"] += 1
        payload = read_json(path, {})
        if not isinstance(payload, dict) or payload.get("status") != "complete":
            stats[f"skip_status:{safe_key(payload.get('status')) or 'invalid'}"] += 1
            continue
        params = payload.get("parameters") if isinstance(payload.get("parameters"), dict) else {}
        try:
            tool_version = int(params.get("toolVersion") or 0)
        except (TypeError, ValueError):
            tool_version = 0
        if min_tool_version and tool_version < min_tool_version:
            stats["skip_stale_tool_version"] += 1
            continue
        if require_archive_box_ocr and params.get("archiveBoxOcr") is not True:
            stats["skip_stale_archive_box_ocr"] += 1
            continue
        if require_archive_box_ocr and params.get("archiveBoxCropMode") != ARCHIVE_BOX_CROP_MODE:
            stats["skip_stale_archive_box_crop"] += 1
            continue
        if params.get("limitFrames") is not None and not include_smoke:
            stats["skip_smoke"] += 1
            continue
        payload["_reportPath"] = rel_path(path)
        reports.append(payload)
        stats["loaded"] += 1
    return reports, stats


def video_file_basename(value: Any) -> str:
    text = safe_key(value)
    if not text:
        return ""
    return Path(text.replace("\\", "/")).name


def report_video_name(report: dict[str, Any]) -> str:
    source = report.get("source") if isinstance(report.get("source"), dict) else {}
    return safe_key(source.get("name")) or safe_key(source.get("path")) or safe_key(report.get("_reportPath"))


def add_unique_search_mission(
    rows: list[dict[str, Any]],
    seen: set[str],
    *,
    mission: Any,
    reason: str,
    video: Any,
    part: int | None,
    offset: int,
) -> None:
    mission_key = safe_key(mission)
    if not mission_key or mission_key in seen:
        return
    seen.add(mission_key)
    rows.append({
        "mission": mission_key,
        "reason": reason,
        "video": safe_key(video),
        "part": part,
        "offset": offset,
    })


def build_video_search_contexts(
    ocr_reports: list[dict[str, Any]],
    mission_title_candidates: list[MissionTitleCandidate],
) -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []
    by_series_part: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for report in ocr_reports:
        video_name = report_video_name(report)
        part = gameplay_video_part_number(video_name)
        series = gameplay_video_series_key(video_name)
        context = {
            "video": video_name,
            "part": part,
            "series": series,
            "missionMatch": (
                video_search_scope_override(video_name, mission_title_candidates)
                or infer_video_mission(video_name, mission_title_candidates)
            ),
            "searchMissions": [],
        }
        contexts.append(context)
        if series and part is not None:
            by_series_part[(series, part)].append(context)

    for context in contexts:
        search_missions: list[dict[str, Any]] = []
        seen: set[str] = set()
        mission_match = context.get("missionMatch") if isinstance(context.get("missionMatch"), dict) else {}
        target_missions = (
            mission_match.get("searchMissions")
            if isinstance(mission_match.get("searchMissions"), list)
            else [mission_match.get("mission")]
        ) if isinstance(mission_match, dict) else []
        for target_mission in target_missions:
            add_unique_search_mission(
                search_missions,
                seen,
                mission=target_mission,
                reason="target-video",
                video=context.get("video"),
                part=context.get("part"),
                offset=0,
            )
        series = safe_key(context.get("series"))
        part = context.get("part") if isinstance(context.get("part"), int) else None
        if series and part is not None:
            for offset in (-1, 1):
                for adjacent in by_series_part.get((series, part + offset), []):
                    adjacent_match = (
                        adjacent.get("missionMatch")
                        if isinstance(adjacent.get("missionMatch"), dict)
                        else {}
                    )
                    adjacent_missions = (
                        adjacent_match.get("searchMissions")
                        if isinstance(adjacent_match.get("searchMissions"), list)
                        else [adjacent_match.get("mission")]
                    ) if isinstance(adjacent_match, dict) else []
                    for adjacent_mission in adjacent_missions:
                        add_unique_search_mission(
                            search_missions,
                            seen,
                            mission=adjacent_mission,
                            reason="adjacent-video",
                            video=adjacent.get("video"),
                            part=adjacent.get("part") if isinstance(adjacent.get("part"), int) else None,
                            offset=offset,
                        )
        context["searchMissions"] = search_missions
    return contexts


def collapse_observed_sequence(
    matches: list[dict[str, Any]],
    mission: str,
    *,
    current_order: list[str],
    use_ransac: bool,
    ransac_tolerance: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    spans = build_observation_spans(matches, mission)
    selected, diagnostics = choose_representative_spans(
        spans,
        current_order,
        use_ransac=use_ransac,
        ransac_tolerance=ransac_tolerance,
    )
    return selected, diagnostics


def observed_sequences_from_matches(
    matches: list[dict[str, Any]],
    *,
    base_story_orders: dict[str, list[str]],
    min_video_matches: int,
    min_sequence_keys: int,
    use_ransac: bool,
    ransac_tolerance: float,
    keep_partial_sequences: bool = False,
) -> tuple[Counter[str], dict[str, list[dict[str, Any]]], dict[str, dict[str, Any]]]:
    accepted_missions = Counter(
        safe_key(match.get("best", {}).get("mission"))
        for match in matches
        if match.get("accepted") and safe_key(match.get("best", {}).get("mission"))
    )
    observed_sequences: dict[str, list[dict[str, Any]]] = {}
    sequence_diagnostics: dict[str, dict[str, Any]] = {}
    required_matches = 1 if keep_partial_sequences else min_video_matches
    for mission, count in accepted_missions.items():
        if count < required_matches:
            continue
        sequence, diagnostics = collapse_observed_sequence(
            matches,
            mission,
            current_order=base_story_orders.get(mission) or [],
            use_ransac=use_ransac,
            ransac_tolerance=ransac_tolerance,
        )
        if len(sequence) >= min_sequence_keys or (keep_partial_sequences and sequence):
            observed_sequences[mission] = sequence
            sequence_diagnostics[mission] = diagnostics
    return accepted_missions, observed_sequences, sequence_diagnostics


def finalize_video_match_record(
    record: dict[str, Any],
    *,
    min_score: float,
    min_margin: float,
    map_dialog_companion_index: dict[str, list[dict[str, Any]]],
    base_story_orders: dict[str, list[str]],
    min_video_matches: int,
    min_sequence_keys: int,
    use_ransac: bool,
    ransac_tolerance: float,
    update_video: bool,
) -> dict[str, Any]:
    ocr_matches = copy_matches_for_threshold(
        ocr_matches=record.get("ocrMatches") or [],
        min_score=min_score,
        min_margin=min_margin,
    )
    map_dialog_companion_matches = build_map_dialog_companion_matches(
        ocr_matches,
        map_dialog_companion_index,
        min_score=min_score,
        min_margin=min_margin,
    )
    matches = ocr_matches + map_dialog_companion_matches
    accepted_missions, observed_sequences, sequence_diagnostics = observed_sequences_from_matches(
        matches,
        base_story_orders=base_story_orders,
        min_video_matches=min_video_matches,
        min_sequence_keys=min_sequence_keys,
        use_ransac=use_ransac,
        ransac_tolerance=ransac_tolerance,
        keep_partial_sequences=update_video,
    )
    accepted_count = sum(1 for match in matches if match.get("accepted"))
    result = {
        "matches": matches,
        "matchedSegments": len(matches),
        "acceptedMatches": accepted_count,
        "mapDialogCompanionMatches": len(map_dialog_companion_matches),
        "missions": [mission for mission, _count in accepted_missions.most_common()],
        "observedSequences": observed_sequences,
        "sequenceDiagnostics": sequence_diagnostics,
    }
    if update_video and isinstance(record.get("video"), dict):
        video = record["video"]
        video.update({
            "acceptedMatches": accepted_count,
            "matchedSegments": len(matches),
            "mapDialogCompanionMatches": len(map_dialog_companion_matches),
            "missions": result["missions"],
            "observedSequences": observed_sequences,
            "sequenceDiagnostics": sequence_diagnostics,
            "matches": sorted(matches, key=match_start_seconds)[:200],
        })
    return result


def clean_order_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = safe_key(value)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def story_orders_by_mission(payload: Any) -> dict[str, list[str]]:
    """Read the full-list story-order format."""
    missions = payload.get("missions") if isinstance(payload, dict) else None
    if not isinstance(missions, dict):
        return {}

    out: dict[str, list[str]] = {}
    for mission_id, raw_mission in missions.items():
        mission = safe_key(mission_id)
        if not mission:
            continue
        if isinstance(raw_mission, list):
            order = clean_order_list(raw_mission)
        elif isinstance(raw_mission, dict):
            order = clean_order_list(raw_mission.get("order"))
        else:
            order = []
        if order:
            out[mission] = order
    return out


def story_order_locked_missions(payload: Any) -> set[str]:
    missions = payload.get("missions") if isinstance(payload, dict) else None
    if not isinstance(missions, dict):
        return set()
    out: set[str] = set()
    for mission_id, raw_mission in missions.items():
        mission = safe_key(mission_id)
        if mission and isinstance(raw_mission, dict) and raw_mission.get("locked") is True:
            out.add(mission)
    return out


def natural_sort_token(value: Any) -> tuple[tuple[int, Any], ...]:
    parts: list[tuple[int, Any]] = []
    for part in NATURAL_SORT_RE.findall(safe_key(value).lower()):
        if part.isdigit():
            parts.append((0, int(part)))
        else:
            parts.append((1, part))
    return tuple(parts)


def build_proposed_story_order(
    *,
    video_summaries: list[dict[str, Any]],
    min_sequence_keys: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Build a proposal from accepted OCR-observed keys only.

    This intentionally does not seed from, compare against, or preserve any
    existing story-order override. It also avoids filename-index gap filling,
    narrative-video attachment, locked-mission handling, and other non-OCR
    additions.
    """
    proposal_rows: list[dict[str, Any]] = []
    missions: dict[str, Any] = {}

    by_mission: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for video in video_summaries:
        for mission, sequence in (video.get("observedSequences") or {}).items():
            if sequence:
                by_mission[safe_key(mission)].append({
                    "video": video.get("video"),
                    "sequence": sequence,
                })

    for mission in sorted((key for key in by_mission if key), key=natural_sort_token):
        rows = by_mission[mission]
        observed_keys: list[str] = []
        linked_entries_by_key: dict[str, dict[str, Any]] = {}
        for row in rows:
            for item in row["sequence"]:
                key = safe_key(item.get("key"))
                if key and (not observed_keys or observed_keys[-1] != key):
                    observed_keys.append(key)
                actual_mission = safe_key(item.get("actualMission"))
                link_reason = safe_key(item.get("linkReason"))
                if key and actual_mission and actual_mission != mission:
                    linked_entries_by_key.setdefault(key, {
                        "key": key,
                        "actualMission": actual_mission,
                        "linkReason": link_reason or "ocr-match",
                        "firstTime": item.get("firstTime"),
                    })

        deduped: list[str] = []
        seen: set[str] = set()
        for key in observed_keys:
            if key in seen:
                continue
            seen.add(key)
            deduped.append(key)

        videos = [row["video"] for row in rows]
        if len(deduped) < min_sequence_keys:
            proposal_rows.append({
                "mission": mission,
                "existingActiveOrder": False,
                "locked": False,
                "observedKeys": deduped,
                "detectedKeys": deduped,
                "proposalKeys": [],
                "linkedEntries": [],
                "videoRefLinks": [],
                "indexedInferences": [],
                "possiblyUnusedKeys": [],
                "changed": False,
                "included": False,
                "skipReason": "insufficient-ocr-evidence",
                "changedKeys": [],
                "insertedKeys": [],
                "orderLength": 0,
                "videos": videos,
            })
            continue

        missions[mission] = {"order": deduped}
        proposal_rows.append({
            "mission": mission,
            "existingActiveOrder": False,
            "locked": False,
            "observedKeys": deduped,
            "detectedKeys": deduped,
            "proposalKeys": deduped,
            "linkedEntries": [
                linked_entries_by_key[key]
                for key in deduped
                if key in linked_entries_by_key
            ],
            "videoRefLinks": [],
            "indexedInferences": [],
            "possiblyUnusedKeys": [],
            "changed": False,
            "included": True,
            "changedKeys": [],
            "insertedKeys": [],
            "orderLength": len(deduped),
            "videos": videos,
        })

    return {
        "_schema": "storyOrder.ocrObserved.v1",
        "_note": (
            "OCR-observed per-mission Story file order. Each missions.<mission>.order "
            "array contains only keys directly accepted from gameplay-video OCR text "
            "matching. This file is not seeded from overrides/story_order.json and "
            "does not include locked/manual/static/inferred order entries."
        ),
        "missions": missions,
    }, proposal_rows


def write_match_markdown(payload: dict[str, Any], output_path: Path) -> None:
    histogram = payload.get("scoreHistogram") or []
    max_histogram_count = max((int(row.get("segments") or 0) for row in histogram), default=0)
    lines = [
        "# Gameplay Video OCR Story-Order Matching",
        "",
        f"- Generated at: `{payload.get('generatedAt', '')}`",
        f"- OCR reports used: `{payload['summary']['ocrReportsUsed']}`",
        f"- Corpus lines: `{payload['summary']['corpusLines']}`",
        f"- Accepted OCR segment matches: `{payload['summary']['acceptedMatches']}`",
        f"- OCR proposal missions: `{payload['summary'].get('ocrProposalMissions', 0)}`",
        f"- OCR proposal keys: `{payload['summary'].get('ocrProposalKeys', 0)}`",
        f"- Ignored repeated spans: `{payload['summary'].get('ignoredRepeatedSpans', 0)}`",
        f"- Effective OCR min score: `{payload.get('thresholds', {}).get('effectiveMinScore', payload.get('thresholds', {}).get('minScore'))}`",
        f"- Video mission title matches: `{payload['summary'].get('videoMissionMatches', {})}`",
        f"- Proposed story order: `{payload['outputs']['proposedStoryOrder']}`",
        f"- WebUI OCR order: `{payload['outputs'].get('webuiOcrOrder', '')}`",
        "",
    ]
    if payload.get("thresholdSweep"):
        lines.extend([
            "## Threshold Sweep",
            "",
            "| min score | accepted segments | unique story keys | unique lines | unique missions |",
            "|---:|---:|---:|---:|---:|",
        ])
        for row in payload["thresholdSweep"]:
            lines.append(
                f"| {float(row.get('minScore') or 0):.2f} "
                f"| {int(row.get('acceptedSegments') or 0)} "
                f"| {int(row.get('uniqueStoryKeys') or 0)} "
                f"| {int(row.get('uniqueLines') or 0)} "
                f"| {int(row.get('uniqueMissions') or 0)} |"
            )
    if histogram:
        lines.extend([
            "",
            "## Score Histogram",
            "",
            "| best score | matched segments | bar |",
            "|---:|---:|---|",
        ])
        for row in reversed(histogram):
            count = int(row.get("segments") or 0)
            width = int(round((count / max_histogram_count) * 32)) if max_histogram_count else 0
            lines.append(
                f"| `{md_escape(row.get('range'))}` "
                f"| {count} "
                f"| `{'#' * width}` |"
            )
    if payload.get("proposals"):
        lines.extend([
            "",
            "## OCR Proposals",
            "",
            "| mission | status | observed keys | proposal keys | linked OCR matches | order size | videos |",
            "|---|---|---:|---:|---:|---:|---|",
        ])
        for row in payload["proposals"]:
            status = safe_key(row.get("skipReason")) or ("included" if row.get("included") else "skipped")
            linked = len(row.get("linkedEntries") or [])
            lines.append(
                f"| `{md_escape(row.get('mission'))}` "
                f"| `{md_escape(status)}` "
                f"| {len(row.get('observedKeys') or [])} "
                f"| {len(row.get('proposalKeys') or [])} "
                f"| {linked} "
                f"| {int(row.get('orderLength') or 0)} "
                f"| `{md_escape(', '.join(row.get('videos') or []))}` |"
            )
    if payload.get("videos"):
        lines.extend([
            "",
            "## Videos",
            "",
            "| video | target mission | search missions | report | accepted | matched missions | observed sequences |",
            "|---|---|---|---|---:|---|---:|",
        ])
        for video in payload["videos"]:
            seq_count = sum(len(seq) for seq in (video.get("observedSequences") or {}).values())
            target = safe_key(video.get("targetMission"))
            target_title = safe_key(video.get("targetMissionTitle"))
            target_match = safe_key(video.get("targetMissionMatch"))
            target_label = target
            if target_title:
                target_label = f"{target} {target_title}"
            if target_match and not target:
                target_label = target_match
            search_label = ", ".join(
                safe_key(row.get("mission"))
                for row in (video.get("searchMissions") or [])
                if isinstance(row, dict) and safe_key(row.get("mission"))
            )
            lines.append(
                f"| `{md_escape(video.get('video'))}` "
                f"| `{md_escape(target_label)}` "
                f"| `{md_escape(search_label)}` "
                f"| `{md_escape(video.get('report'))}` "
                f"| {video.get('acceptedMatches', 0)} "
                f"| `{md_escape(', '.join(video.get('missions') or []))}` "
                f"| {seq_count} |"
            )
    write_text_if_changed(output_path, "\n".join(lines) + "\n")


def short_duration(seconds: float | None) -> str:
    if seconds is None:
        return "?"
    seconds = max(0.0, seconds)
    if seconds < 60:
        return f"{seconds:.0f}s"
    minutes, secs = divmod(int(seconds), 60)
    if minutes < 60:
        return f"{minutes}m{secs:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h{minutes:02d}m"


def progress_bar(
    label: str,
    current: int,
    total: int,
    *,
    started: float,
    force: bool = False,
    width: int = 28,
) -> None:
    if total <= 0:
        return
    now = time.monotonic()
    if not force and now - getattr(progress_bar, "_last", 0.0) < 1.0:
        return
    progress_bar._last = now  # type: ignore[attr-defined]
    current = min(max(current, 0), total)
    ratio = current / total
    filled = int(round(width * ratio))
    elapsed = now - started
    eta = (elapsed / current * (total - current)) if current else None
    line = (
        f"\r{label} [{('#' * filled).ljust(width, '-')}] "
        f"{current}/{total} {ratio * 100:5.1f}% "
        f"elapsed {short_duration(elapsed)} eta {short_duration(eta)}"
    )
    sys.stdout.write(line)
    if force or current >= total:
        sys.stdout.write("\n")
    sys.stdout.flush()


def run_subprocess(command: list[str]) -> None:
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env.setdefault("PYTHONIOENCODING", "utf-8:replace")
    proc = subprocess.Popen(
        command,
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        safe_console_write(line, sys.stdout)
    returncode = proc.wait()
    if returncode != 0:
        raise RuntimeError(f"command failed with exit code {returncode}: {' '.join(command)}")


def safe_console_write(text: str, stream) -> None:
    encoding = getattr(stream, "encoding", None) or "utf-8"
    stream.write(text.encode(encoding, errors="replace").decode(encoding, errors="replace"))


def read_active_story_order(path: Path) -> tuple[dict[str, Any], str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return {"missions": {}}, ""
    except OSError as exc:
        return {"missions": {}}, f"could not read {rel_path(path)}: {exc}"
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {"missions": {}}, f"invalid JSON in {rel_path(path)}: {exc}"
    if not isinstance(payload, dict):
        return {"missions": {}}, f"{rel_path(path)} does not contain a JSON object"
    return payload, ""


def run_ocr(args: argparse.Namespace) -> None:
    command = [
        sys.executable,
        str(OCR_SCRIPT_PATH),
        "--ocr-engine",
        args.ocr_engine,
        "--paddleocr-frame-batch-size",
        str(args.paddleocr_frame_batch_size),
        "--frame-step",
        str(args.frame_step),
        "--crop",
        args.ocr_crop,
        "--report-dir",
        str(args.ocr_report_dir.resolve()),
    ]
    if args.force_ocr:
        command.append("--force")
    if args.ocr_limit is not None:
        command.extend(["--limit", str(args.ocr_limit)])
    if args.ocr_limit_frames is not None:
        command.extend(["--limit-frames", str(args.ocr_limit_frames)])
    if args.easyocr_cpu:
        command.append("--easyocr-cpu")
    if args.disable_archive_box_ocr:
        command.append("--disable-archive-box-ocr")
    if args.disable_ocr_dictionary:
        command.append("--disable-ocr-dictionary")
    if args.no_progress:
        command.append("--no-progress")
    print(
        "Running OCR sampler: "
        f"frame_step={args.frame_step}, crop={args.ocr_crop}, "
        "paragraph=True, "
        f"archive_box_ocr={not args.disable_archive_box_ocr}, "
        f"archive_box_crop={ARCHIVE_BOX_CROP_MODE}, "
        f"ocr_dictionary={not args.disable_ocr_dictionary}, "
        f"limit={args.ocr_limit if args.ocr_limit is not None else 'all'}, "
        f"limit_frames={args.ocr_limit_frames if args.ocr_limit_frames is not None else 'full'}"
    )
    run_subprocess(command)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-ocr", action="store_true", help="run OCR before matching")
    parser.add_argument(
        "--ocr-report-dir",
        type=Path,
        default=OCR_REPORT_DIR,
        help="Directory containing completed per-video OCR reports",
    )
    parser.add_argument("--frame-step", type=int, default=10, help="OCR frame step when --run-ocr is used")
    parser.add_argument("--ocr-crop", choices=["subtitle", "lower-half", "lower-third", "full"], default="subtitle")
    parser.add_argument(
        "--ocr-engine",
        choices=["paddleocr", "easyocr"],
        default="paddleocr",
        help="OCR engine for --run-ocr (default: paddleocr / PP-OCRv5)",
    )
    parser.add_argument(
        "--paddleocr-frame-batch-size",
        type=int,
        default=40,
        help="PaddleOCR frame batch size for --run-ocr (default: 40, tuned for PP-OCRv5 server on RTX 5080)",
    )
    parser.add_argument("--force-ocr", action="store_true")
    parser.add_argument("--ocr-limit", type=int, default=None)
    parser.add_argument("--ocr-limit-frames", type=int, default=None)
    parser.add_argument("--easyocr-cpu", action="store_true")
    parser.add_argument("--disable-archive-box-ocr", action="store_true", help="Disable the second-pass archive reading-panel OCR sampler")
    parser.add_argument("--disable-ocr-dictionary", action="store_true", help="Disable the Story-derived EasyOCR character dictionary")
    parser.add_argument("--include-smoke", action="store_true", help="include OCR reports produced with --limit-frames")
    parser.add_argument("--include-stale-ocr", action="store_true", help="include OCR reports generated by older filter versions")
    parser.add_argument("--min-chars", type=int, default=4)
    parser.add_argument("--min-score", type=float, default=0.75)
    parser.add_argument("--min-margin", type=float, default=0.06)
    parser.add_argument("--topn", type=int, default=5)
    parser.add_argument("--min-video-matches", type=int, default=2)
    parser.add_argument("--min-sequence-keys", type=int, default=2)
    parser.add_argument("--include-title-matches", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--no-ransac", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "--ransac-tolerance",
        type=float,
        default=DEFAULT_RANSAC_TOLERANCE,
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--disable-locked-threshold", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--no-progress", action="store_true", help="Disable terminal progress bars")
    args = parser.parse_args()
    if args.frame_step <= 0:
        parser.error("--frame-step must be greater than zero")
    if args.ransac_tolerance <= 0:
        parser.error("--ransac-tolerance must be greater than zero")
    return args


def main() -> int:
    args = parse_args()
    match_report_path = args.ocr_report_dir / "story_order_ocr_matches.json"
    match_md_path = args.ocr_report_dir / "story_order_ocr_matches.md"
    proposed_story_order_path = args.ocr_report_dir / "story_order_ocr_proposed_story_order.json"
    if args.run_ocr:
        run_ocr(args)

    story_order: dict[str, Any] = {}
    active_story_order_warning = ""
    print("Active story-order override is not used for OCR matching or proposal generation.")

    print(f"Loading Story corpus from {rel_path(CONV_ROOT)}...")
    corpus = load_corpus(
        conv_root=CONV_ROOT,
        story_order=story_order,
        min_chars=args.min_chars,
        include_titles=args.include_title_matches,
        restrict_to_story_order=False,
    )
    print(
        f"Loaded {len(corpus)} searchable Story text row(s) "
        "from generated native mission data; active story order is ignored."
    )
    map_dialog_companion_index: dict[str, list[dict[str, Any]]] = {}
    map_dialog_companion_count = 0
    print("Archive-to-map-dialog companion inference disabled for OCR-only matching.")
    base_story_orders: dict[str, list[str]] = {}
    related_missions_by_mission: dict[str, list[dict[str, str]]] = {}
    mission_title_candidates = load_mission_title_candidates(MISSIONS_PATH)
    print(f"Loaded {len(mission_title_candidates)} mission title matcher(s) from {rel_path(MISSIONS_PATH)}.")
    corpus_by_mission: dict[str, list[CorpusLine]] = defaultdict(list)
    for line in corpus:
        corpus_by_mission[line.mission].append(line)
    gram_index_by_scope: dict[tuple[str, ...], dict[str, list[int]]] = {}
    min_ocr_tool_version = 0 if args.include_stale_ocr else MIN_OCR_TOOL_VERSION
    ocr_reports, ocr_load_stats = load_ocr_reports(
        args.ocr_report_dir,
        include_smoke=args.include_smoke,
        min_tool_version=min_ocr_tool_version,
        require_archive_box_ocr=not args.include_stale_ocr and not args.disable_archive_box_ocr,
    )
    if ocr_load_stats:
        print(
            "OCR report scan: "
            + ", ".join(f"{key}={value}" for key, value in sorted(ocr_load_stats.items()))
        )
    if args.include_stale_ocr:
        stale_note = ", including stale OCR"
    else:
        archive_note = "" if args.disable_archive_box_ocr else ", archive-box OCR enabled"
        stale_note = f", toolVersion >= {MIN_OCR_TOOL_VERSION}{archive_note} only"
    print(
        f"Loaded {len(ocr_reports)} completed OCR report(s) from {rel_path(args.ocr_report_dir)} "
        f"({'including' if args.include_smoke else 'excluding'} smoke reports{stale_note})."
    )
    if ocr_reports:
        print("OCR reports to match:")
        for index, report in enumerate(ocr_reports, start=1):
            stats = report.get("stats") if isinstance(report.get("stats"), dict) else {}
            name = report_video_name(report)
            print(
                f"  {index:03d}/{len(ocr_reports):03d} {name} "
                f"segments={stats.get('segments', 0)} kept={stats.get('nonEmptyFrames', 0)}"
            )
    video_search_contexts = build_video_search_contexts(ocr_reports, mission_title_candidates)

    videos: list[dict[str, Any]] = []
    all_matches_for_stats: list[dict[str, Any]] = []
    total_matches = 0
    total_accepted = 0
    total_map_dialog_companion_matches = 0
    video_mission_stats: Counter[str] = Counter()
    video_match_records: list[dict[str, Any]] = []
    # RANSAC uses existing story-order positions as a prior, so OCR-only mode keeps it off.
    sequence_use_ransac = False
    for report, search_context in zip(ocr_reports, video_search_contexts):
        matches: list[dict[str, Any]] = []
        video_name = report_video_name(report)
        segments = [segment for segment in (report.get("segments") or []) if isinstance(segment, dict)]
        mission_match = (
            search_context.get("missionMatch")
            if isinstance(search_context.get("missionMatch"), dict)
            else {}
        )
        target_mission = safe_key(mission_match.get("mission"))
        target_title = safe_key(mission_match.get("title"))
        target_match_kind = safe_key(mission_match.get("match")) or safe_key(mission_match.get("status"))
        search_mission_rows = [
            row for row in (search_context.get("searchMissions") or [])
            if isinstance(row, dict) and safe_key(row.get("mission"))
        ]
        if not search_mission_rows:
            status = safe_key(mission_match.get("status")) or "unmatched"
            video_mission_stats[f"skip_{status}"] += 1
            print(f"[{video_name}] skipped: {status} mission title match")
            videos.append({
                "video": video_name,
                "report": report.get("_reportPath"),
                "targetMission": "",
                "targetMissionTitle": "",
                "targetMissionMatch": status,
                "missionTitleCandidates": mission_match.get("candidates") or [],
                "searchMissions": [],
                "relatedCorpus": [],
                "acceptedMatches": 0,
                "matchedSegments": 0,
                "mapDialogCompanionMatches": 0,
                "missions": [],
                "observedSequences": {},
                "sequenceDiagnostics": {},
                "matches": [],
            })
            continue

        video_corpus, related_corpus_rows = corpus_for_search_missions(
            search_mission_rows,
            corpus_by_mission=corpus_by_mission,
            related_missions_by_mission=related_missions_by_mission,
        )
        if not video_corpus:
            video_mission_stats["skip_no_corpus"] += 1
            print(
                f"[{video_name}] skipped: search missions "
                f"{','.join(safe_key(row.get('mission')) for row in search_mission_rows) or '-'} "
                "have no searchable corpus"
            )
            videos.append({
                "video": video_name,
                "report": report.get("_reportPath"),
                "targetMission": target_mission,
                "targetMissionTitle": target_title,
                "targetMissionMatch": target_match_kind,
                "missionTitleCandidates": mission_match.get("candidates") or [],
                "searchMissions": search_mission_rows,
                "relatedCorpus": [],
                "acceptedMatches": 0,
                "matchedSegments": 0,
                "mapDialogCompanionMatches": 0,
                "missions": [],
                "observedSequences": {},
                "sequenceDiagnostics": {},
                "matches": [],
            })
            continue

        video_mission_stats["matched"] += 1
        if not target_mission:
            video_mission_stats["matched_adjacent_only"] += 1
        search_scope_key = tuple(safe_key(row.get("mission")) for row in search_mission_rows)
        gram_index = gram_index_by_scope.get(search_scope_key)
        if gram_index is None:
            gram_index = build_gram_index(video_corpus)
            gram_index_by_scope[search_scope_key] = gram_index
        search_label = ",".join(
            (
                safe_key(row.get("mission"))
                + (f":P{row.get('part')}" if row.get("part") is not None else "")
                + ("*" if int_or_none(row.get("offset")) == 0 else "")
            )
            for row in search_mission_rows
        )
        print(
            f"[{video_name}] target={target_mission or '-'}"
            f"{f' ({target_title})' if target_title else ''} "
            f"via {target_match_kind}; "
            f"matching {len(segments)} OCR segment(s) "
            f"against {len(video_corpus)} row(s)"
            f" across {search_label or '-'}"
            f"{f' ({len(related_corpus_rows)} linked mission corpus set(s))' if related_corpus_rows else ''}..."
        )
        match_started = time.monotonic()
        for segment_index, segment in enumerate(segments):
            if not isinstance(segment, dict):
                continue
            match = aggregate_segment_match(
                segment,
                corpus=video_corpus,
                gram_index=gram_index,
                min_chars=args.min_chars,
                topn=args.topn,
            )
            if not match:
                continue
            match["video"] = video_name
            accepted = is_accept(match, min_score=args.min_score, min_margin=args.min_margin)
            match["accepted"] = accepted
            matches.append(match)
            all_matches_for_stats.append(match)
            total_matches += 1
            total_accepted += 1 if accepted else 0
            if not args.no_progress:
                progress_bar(
                    f"[{video_name}] match",
                    segment_index + 1,
                    len(segments),
                    started=match_started,
                    force=(segment_index + 1 == len(segments)),
                )
        if segments and args.no_progress:
            print(
                f"[{video_name}] matching pass finished in "
                f"{time.monotonic() - match_started:.1f}s"
            )

        ocr_matches = list(matches)
        map_dialog_companion_matches = build_map_dialog_companion_matches(
            matches,
            map_dialog_companion_index,
            min_score=args.min_score,
            min_margin=args.min_margin,
        )
        if map_dialog_companion_matches:
            matches.extend(map_dialog_companion_matches)
            all_matches_for_stats.extend(map_dialog_companion_matches)
            total_matches += len(map_dialog_companion_matches)
            total_accepted += len(map_dialog_companion_matches)
            total_map_dialog_companion_matches += len(map_dialog_companion_matches)

        accepted_missions = Counter(
            safe_key(match.get("best", {}).get("mission"))
            for match in matches
            if match.get("accepted") and safe_key(match.get("best", {}).get("mission"))
        )
        observed_sequences: dict[str, list[dict[str, Any]]] = {}
        sequence_diagnostics: dict[str, dict[str, Any]] = {}
        for mission, count in accepted_missions.items():
            if count < args.min_video_matches:
                continue
            sequence, diagnostics = collapse_observed_sequence(
                matches,
                mission,
                current_order=base_story_orders.get(mission) or [],
                use_ransac=sequence_use_ransac,
                ransac_tolerance=args.ransac_tolerance,
            )
            if len(sequence) >= args.min_sequence_keys:
                observed_sequences[mission] = sequence
                sequence_diagnostics[mission] = diagnostics

        print(
            f"[{video_name}] matched={len(matches)} accepted="
            f"{sum(1 for match in matches if match.get('accepted'))} "
            f"companions={len(map_dialog_companion_matches)} "
            f"target={target_mission or '-'} "
            f"search={','.join(safe_key(row.get('mission')) for row in search_mission_rows) or '-'} "
            f"missions={','.join(mission for mission, _count in accepted_missions.most_common()) or '-'}"
        )
        video_summary = {
            "video": video_name,
            "report": report.get("_reportPath"),
            "targetMission": target_mission,
            "targetMissionTitle": target_title,
            "targetMissionMatch": target_match_kind,
            "missionTitleCandidates": mission_match.get("candidates") or [],
            "searchMissions": search_mission_rows,
            "relatedCorpus": related_corpus_rows,
            "acceptedMatches": sum(1 for match in matches if match.get("accepted")),
            "matchedSegments": len(matches),
            "mapDialogCompanionMatches": len(map_dialog_companion_matches),
            "missions": [mission for mission, _count in accepted_missions.most_common()],
            "observedSequences": observed_sequences,
            "sequenceDiagnostics": sequence_diagnostics,
            "matches": sorted(matches, key=match_start_seconds)[:200],
        }
        videos.append(video_summary)
        video_match_records.append({
            "video": video_summary,
            "videoName": video_summary["video"],
            "ocrMatches": ocr_matches,
        })

    current_orders: dict[str, list[str]] = {}
    active_order_missions: set[str] = set()
    locked_order_missions: set[str] = set()
    locked_threshold_sweep: list[dict[str, Any]] = []
    locked_threshold_choice = {
        "minScore": args.min_score,
        "reason": "ocr-only-no-prior",
        "disabled": True,
    }
    effective_min_score = args.min_score
    locked_validation = {
        "summary": {
            "lockedMissionsWithEvidence": 0,
            "checkedKeys": 0,
            "missingKeys": 0,
            "mismatches": 0,
            "inversions": 0,
        },
        "missions": [],
    }
    proposed, proposal_rows = build_proposed_story_order(
        video_summaries=videos,
        min_sequence_keys=args.min_sequence_keys,
    )
    skipped_locked_mission_count = 0
    included_proposal_rows = [row for row in proposal_rows if row.get("included")]
    changed_mission_count = 0
    inserted_key_count = sum(len(row.get("proposalKeys") or []) for row in included_proposal_rows)
    changed_key_count = 0
    marked_possibly_unused_key_count = 0
    insufficient_ocr_mission_count = sum(
        1 for row in proposal_rows if row.get("skipReason") == "insufficient-ocr-evidence"
    )
    sequence_diagnostics = [
        diagnostics
        for video in videos
        for diagnostics in (video.get("sequenceDiagnostics") or {}).values()
        if isinstance(diagnostics, dict)
    ]
    print(
        "OCR story-order proposal: "
        f"ocrMissions={len(included_proposal_rows)}, "
        f"insufficientOcrMissions={insufficient_ocr_mission_count}, "
        f"ocrKeys={inserted_key_count}, "
        f"mapDialogCompanions={total_map_dialog_companion_matches}"
    )
    write_report_json(proposed_story_order_path, proposed)

    # Distill the OCR order into a small WebUI-served reference so the story
    # debug mode can compare it against the static recovery order/override.
    from build_webui_ocr_order import build_webui_ocr_order  # noqa: E402

    webui_ocr_path = build_webui_ocr_order(proposed_story_order_path)
    print(f"Wrote {rel_path(webui_ocr_path)} (WebUI OCR order reference)")

    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    payload = {
        "schema": "gameplayVideoStoryOrderMatch.v2",
        "generatedAt": generated_at,
        "summary": {
            "corpusLines": len(corpus),
            "ocrReportsUsed": len(ocr_reports),
            "matchedSegments": total_matches,
            "acceptedMatches": total_accepted,
            "mapDialogCompanionMatches": total_map_dialog_companion_matches,
            "mapDialogCompanionEnabled": False,
            "ocrProposalMissions": len(included_proposal_rows),
            "ocrProposalKeys": inserted_key_count,
            "insufficientOcrEvidenceMissions": insufficient_ocr_mission_count,
            "indexedInferences": 0,
            "linkedEntries": sum(len(row.get("linkedEntries") or []) for row in proposal_rows),
            "videoRefLinks": 0,
            "ransacModels": sum(1 for row in sequence_diagnostics if row.get("ransacModel")),
            "ransacAdjustedKeys": sum(int(row.get("adjustedRepeatedKeys") or 0) for row in sequence_diagnostics),
            "ignoredRepeatedSpans": sum(int(row.get("ignoredRepeatedSpans") or 0) for row in sequence_diagnostics),
            "orderUpdateMode": "ocr-match-only",
            "recognizedFirstOnly": True,
            "videoScope": "all",
            "activeOrderMissions": len(active_order_missions),
            "lockedOrderMissions": len(locked_order_missions),
            "skippedLockedOrderMissions": skipped_locked_mission_count,
            "seededOrderMissions": len(current_orders),
            "changedOrderMissions": changed_mission_count,
            "changedOrderKeys": changed_key_count,
            "insertedOrderKeys": inserted_key_count,
            "markedPossiblyUnusedKeys": marked_possibly_unused_key_count,
            "videoMissionMatches": dict(sorted(video_mission_stats.items())),
            "titleMatchesIncluded": bool(args.include_title_matches),
            "lockedValidation": locked_validation.get("summary") or {},
            "lockedThresholdChoice": locked_threshold_choice,
            "activeOrderWarning": active_story_order_warning,
            "applied": False,
        },
        "thresholds": {
            "minChars": args.min_chars,
            "minScore": args.min_score,
            "effectiveMinScore": effective_min_score,
            "minMargin": args.min_margin,
            "minVideoMatches": args.min_video_matches,
            "minSequenceKeys": args.min_sequence_keys,
            "ransacEnabled": False,
            "ransacTolerance": None,
            "includeTitleMatches": bool(args.include_title_matches),
        },
        "outputs": {
            "proposedStoryOrder": rel_path(proposed_story_order_path),
            "webuiOcrOrder": rel_path(webui_ocr_path),
            "activeStoryOrder": "",
        },
        "thresholdSweep": build_threshold_sweep(
            all_matches_for_stats,
            min_margin=args.min_margin,
            current_min_score=effective_min_score,
        ),
        "lockedThresholdSweep": locked_threshold_sweep,
        "lockedValidation": locked_validation,
        "scoreHistogram": build_score_histogram(all_matches_for_stats),
        "proposals": proposal_rows,
        "videos": videos,
    }
    write_report_json(match_report_path, payload)
    write_match_markdown(payload, match_md_path)

    print(f"Matched {total_accepted}/{total_matches} OCR segment(s) from {len(ocr_reports)} OCR report(s).")
    print(f"Wrote {rel_path(match_report_path)}")
    print(f"Review matching summary at {rel_path(match_md_path)}")
    print(f"Wrote {rel_path(proposed_story_order_path)}")
    print(f"Active override left unchanged: {rel_path(ACTIVE_STORY_ORDER_PATH)}")
    print("Locked-order mismatch validation skipped: OCR-only mode does not use active order priors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
