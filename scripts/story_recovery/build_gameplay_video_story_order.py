#!/usr/bin/env python3
"""Match gameplay-video OCR/audio evidence to Story entries and update story order lists.

This is a conservative promotion pipeline:

1. Optionally run the OCR sampler.
2. Match completed OCR segments against known WebUI Story text.
3. Match decoded Story audio templates against gameplay-video audio.
4. Collapse timestamped matches into observed per-mission scene sequences.
5. Apply those sequences to the full per-mission story-order list format.

The active order file is ``webui/overrides/story_order.json``. Each
``missions.<mission>.order`` value is a complete ordered list of the mission's
Story file keys. The OCR pass seeds only from that active file and moves
observed keys into the observed order while preserving unobserved mission files
in their current relative order.
"""
from __future__ import annotations

import argparse
from array import array
import hashlib
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
import wave
from collections import Counter, defaultdict
from dataclasses import dataclass
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
MATCH_REPORT_PATH = OCR_REPORT_DIR / "story_order_ocr_matches.json"
MATCH_MD_PATH = OCR_REPORT_DIR / "story_order_ocr_matches.md"
PROPOSED_STORY_ORDER_PATH = OCR_REPORT_DIR / "story_order_ocr_proposed_story_order.json"
OCR_SCRIPT_PATH = ROOT / "scripts" / "story_recovery" / "build_gameplay_video_ocr_audit.py"
AUDIO_CACHE_ROOT = ROOT / "tmp" / "gameplay_video_ocr" / "audio"
MIN_OCR_TOOL_VERSION = 6
DEFAULT_THRESHOLD_SWEEP = (0.98, 0.95, 0.90, 0.86, 0.80, 0.75, 0.70, 0.65, 0.60, 0.50)
LINE_LIKE_SOURCES = {"line", "summary"}
MAP_DIALOG_COMPANION_SOURCE = "map-dialog-companion"
AUDIO_TEMPLATE_SOURCE = "audio-template"
DEFAULT_RANSAC_TOLERANCE = 3.5
DEFAULT_AUDIO_SAMPLE_RATE = 8000
DEFAULT_AUDIO_FRAME_SECONDS = 0.10
DEFAULT_AUDIO_FILTER = "highpass=f=180,lowpass=f=3600"
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
INDEXED_SUFFIX_RE = re.compile(r"^(\d+)(?:d(\d+))?(?:_(\d+))?$")
NATURAL_SORT_RE = re.compile(r"\d+|\D+")
AUDIO_CACHE_SAFE_RE = re.compile(r"[^A-Za-z0-9_.-]+")


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
class IndexedStoryKey:
    key: str
    family: str
    number: float
    has_decimal: bool
    order_index: int


@dataclass(frozen=True)
class MissionTitleCandidate:
    mission: str
    title: str
    norm: str
    loose_norm: str


@dataclass(frozen=True)
class AudioStoryTemplate:
    key: str
    mission: str
    actual_mission: str
    link_reason: str
    kind: str
    scene: int | None
    line_id: str
    source: str
    text: str
    audio_id: str
    audio_src: str
    audio_path: Path
    duration_seconds: float | None


@dataclass
class AudioFingerprint:
    energy: list[float]
    delta: list[float]
    frame_seconds: float
    duration_seconds: float
    source: str


@dataclass
class AudioWindowHit:
    start_index: int
    score: float
    energy_score: float
    delta_score: float


@dataclass
class AudioSearchIndex:
    fingerprint: AudioFingerprint
    energy_prefix: list[float]
    energy_sq_prefix: list[float]
    delta_prefix: list[float]
    delta_sq_prefix: list[float]


@dataclass(frozen=True)
class AudioLandmark:
    offset: int
    value: float


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


def load_mission_title_candidates(
    path: Path,
    story_order: dict[str, Any],
) -> list[MissionTitleCandidate]:
    payload = read_json(path, {})
    names = payload.get("missionNames") if isinstance(payload, dict) else {}
    if not isinstance(names, dict):
        names = {}
    story_orders = story_orders_by_mission(story_order)
    out: list[MissionTitleCandidate] = []
    seen: set[tuple[str, str]] = set()
    for mission in sorted(story_orders):
        for title in mission_title_variants(names.get(mission)):
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
        return {"status": "unmatched", "candidates": []}

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


def parse_indexed_story_key(key: str, mission: str, order_index: int) -> IndexedStoryKey | None:
    key = safe_key(key)
    mission = safe_key(mission)
    marker = f"_{mission}_"
    marker_index = key.find(marker)
    if not key or not mission or marker_index < 0:
        return None
    suffix = key[marker_index + len(marker) :]
    match = INDEXED_SUFFIX_RE.fullmatch(suffix)
    if not match:
        return None
    number = float(int(match.group(1)))
    decimal = match.group(2)
    variant = match.group(3)
    if decimal is not None:
        number += int(decimal) / (10 ** len(decimal))
    elif variant is not None:
        number += int(variant) / 1000.0
    return IndexedStoryKey(
        key=key,
        family=key[: marker_index + len(marker)],
        number=number,
        has_decimal=decimal is not None,
        order_index=order_index,
    )


def iter_text_rows(payload: dict[str, Any]) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    title = safe_key(payload.get("title"))
    if title:
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
) -> list[CorpusLine]:
    story_orders = story_orders_by_mission(story_order)
    story_mission_by_key: dict[str, str] = {}
    for mission_id, order in story_orders.items():
        for key in order:
            story_mission_by_key.setdefault(key, mission_id)
    allowed_keys = {key for order in story_orders.values() for key in order}
    out: list[CorpusLine] = []
    for path in sorted(conv_root.glob("*.json")):
        key = path.stem
        payload = read_json(path, {})
        if not isinstance(payload, dict):
            continue
        archive_entry = is_archive_story_entry(key, payload)
        if allowed_keys and key not in allowed_keys and not key.startswith("dlg_map") and not archive_entry:
            continue
        native_mission = safe_key(payload.get("mission"))
        mission = story_mission_by_key.get(key) or native_mission
        if not mission:
            for mission_id, order in story_orders.items():
                if key in order:
                    mission = mission_id
                    break
        if not mission:
            continue
        kind = story_kind(key, payload)
        scene = int_or_none(payload.get("scene"))
        for line_id, source, text in iter_text_rows(payload):
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


def resolve_story_audio_path(src: Any) -> Path | None:
    text = safe_key(src).replace("\\", "/")
    if not text:
        return None
    if text.startswith("/"):
        return ROOT / text.lstrip("/")
    path = Path(text)
    if path.is_absolute():
        return path
    return ROOT / path


def resolve_video_source_path(source: dict[str, Any]) -> Path | None:
    for field in ("path", "name"):
        text = safe_key(source.get(field))
        if not text:
            continue
        path = Path(text)
        candidates = [path]
        if not path.is_absolute():
            candidates = [ROOT / path, ROOT / "videos" / text]
        for candidate in candidates:
            if candidate.is_file():
                return candidate
    return None


def audio_duration_hint(entry: dict[str, Any] | None, fallback: Any = None) -> float | None:
    if isinstance(entry, dict):
        for value in (
            entry.get("duration"),
            entry.get("durationSeconds"),
            (entry.get("meta") or {}).get("duration") if isinstance(entry.get("meta"), dict) else None,
            (entry.get("audioMeta") or {}).get("duration") if isinstance(entry.get("audioMeta"), dict) else None,
        ):
            duration = float_value(value, -1.0)
            if duration > 0:
                return duration
    duration = float_value(fallback, -1.0)
    return duration if duration > 0 else None


def wav_duration_seconds(path: Path) -> float | None:
    try:
        with wave.open(str(path), "rb") as handle:
            rate = handle.getframerate()
            frames = handle.getnframes()
            if rate > 0 and frames >= 0:
                return frames / rate
    except (OSError, EOFError, wave.Error):
        return None
    return None


def story_audio_id(raw_id: Any, path: Path | None) -> str:
    audio_id = safe_key(raw_id)
    if audio_id:
        return audio_id
    return path.stem if path else ""


def should_skip_audio_template(audio_id: str, *, include_music: bool) -> bool:
    if include_music:
        return False
    return audio_id.lower().startswith("au_music")


def load_audio_templates(
    *,
    conv_root: Path,
    story_order: dict[str, Any],
    min_duration: float,
    max_duration: float,
    include_music: bool,
) -> list[AudioStoryTemplate]:
    story_orders = story_orders_by_mission(story_order)
    story_mission_by_key: dict[str, str] = {}
    for mission_id, order in story_orders.items():
        for key in order:
            story_mission_by_key.setdefault(key, mission_id)
    allowed_keys = {key for order in story_orders.values() for key in order}

    templates: list[AudioStoryTemplate] = []
    seen: set[tuple[str, str, str, str]] = set()

    def add_template(
        *,
        payload: dict[str, Any],
        key: str,
        mission: str,
        native_mission: str,
        kind: str,
        scene: int | None,
        line_id: str,
        source: str,
        text: str,
        entry: dict[str, Any],
        fallback_duration: Any = None,
    ) -> None:
        src = safe_key(entry.get("src"))
        path = resolve_story_audio_path(src)
        if path is None or not path.is_file():
            return
        audio_id = story_audio_id(entry.get("id") or payload.get("audio") or payload.get("voice"), path)
        if should_skip_audio_template(audio_id, include_music=include_music):
            return
        duration = audio_duration_hint(entry, fallback=fallback_duration)
        if duration is None and path.suffix.lower() == ".wav":
            duration = wav_duration_seconds(path)
        if duration is not None:
            if duration < min_duration or duration > max_duration:
                return
        dedupe_key = (key, line_id, audio_id, str(path).lower())
        if dedupe_key in seen:
            return
        seen.add(dedupe_key)
        templates.append(AudioStoryTemplate(
            key=key,
            mission=mission,
            actual_mission=native_mission or mission,
            link_reason="native" if mission == (native_mission or mission) else "story-order",
            kind=kind,
            scene=scene,
            line_id=line_id,
            source=source,
            text=text,
            audio_id=audio_id,
            audio_src=src,
            audio_path=path,
            duration_seconds=duration,
        ))

    for path in sorted(conv_root.glob("*.json")):
        key = path.stem
        payload = read_json(path, {})
        if not isinstance(payload, dict):
            continue
        archive_entry = is_archive_story_entry(key, payload)
        if allowed_keys and key not in allowed_keys and not key.startswith("dlg_map") and not archive_entry:
            continue
        native_mission = safe_key(payload.get("mission"))
        mission = story_mission_by_key.get(key) or native_mission
        if not mission:
            continue
        kind = story_kind(key, payload)
        scene = int_or_none(payload.get("scene"))
        title = safe_key(payload.get("title"))

        for line in payload.get("lines") or []:
            if not isinstance(line, dict):
                continue
            line_id = safe_key(line.get("id"))
            text = safe_key(line.get("text"))
            if line.get("audioSrc"):
                entry = {
                    "id": line.get("audio") or line.get("voice"),
                    "src": line.get("audioSrc"),
                    "audioMeta": line.get("audioMeta") if isinstance(line.get("audioMeta"), dict) else {},
                }
                add_template(
                    payload=line,
                    key=key,
                    mission=mission,
                    native_mission=native_mission,
                    kind=kind,
                    scene=scene,
                    line_id=line_id,
                    source="audio-line",
                    text=text,
                    entry=entry,
                    fallback_duration=line.get("dur"),
                )
            variants = line.get("audioVariants")
            if isinstance(variants, dict):
                for gender, variant in variants.items():
                    if not isinstance(variant, dict):
                        continue
                    add_template(
                        payload=line,
                        key=key,
                        mission=mission,
                        native_mission=native_mission,
                        kind=kind,
                        scene=scene,
                        line_id=line_id,
                        source=f"audio-line-{safe_key(gender) or 'variant'}",
                        text=text,
                        entry=variant,
                        fallback_duration=(variant.get("meta") or {}).get("duration")
                        if isinstance(variant.get("meta"), dict) else line.get("dur"),
                    )

        for source, entries in (
            ("audio-cutscene", payload.get("audioFiles")),
            ("audio-cutscene", (payload.get("cutscene") or {}).get("audioFiles")
             if isinstance(payload.get("cutscene"), dict) else None),
        ):
            if not isinstance(entries, list):
                continue
            for index, entry in enumerate(entries):
                if not isinstance(entry, dict):
                    continue
                add_template(
                    payload=payload,
                    key=key,
                    mission=mission,
                    native_mission=native_mission,
                    kind=kind,
                    scene=scene,
                    line_id=f"{source}:{index}",
                    source=source,
                    text=title or key,
                    entry=entry,
                )
    return templates


def retarget_audio_template(template: AudioStoryTemplate, mission: str, reason: str) -> AudioStoryTemplate:
    if template.mission == mission and template.link_reason == "native":
        return template
    return AudioStoryTemplate(
        key=template.key,
        mission=mission,
        actual_mission=template.actual_mission,
        link_reason=reason,
        kind=template.kind,
        scene=template.scene,
        line_id=template.line_id,
        source=template.source,
        text=template.text,
        audio_id=template.audio_id,
        audio_src=template.audio_src,
        audio_path=template.audio_path,
        duration_seconds=template.duration_seconds,
    )


def audio_templates_for_video_mission(
    target_mission: str,
    *,
    audio_templates_by_mission: dict[str, list[AudioStoryTemplate]],
    related_missions_by_mission: dict[str, list[dict[str, str]]],
) -> tuple[list[AudioStoryTemplate], list[dict[str, Any]]]:
    out: list[AudioStoryTemplate] = []
    related_rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()

    def add_templates(
        templates: list[AudioStoryTemplate],
        *,
        as_mission: str,
        reason: str,
        supplemental_only_map_dialogs: bool = False,
    ) -> int:
        added = 0
        for template in templates:
            if supplemental_only_map_dialogs and not (
                template.key.startswith("dlg_map") or template.key.startswith(ARCHIVE_KEY_PREFIXES)
            ):
                continue
            dedupe_key = (template.key, template.line_id, template.audio_id, reason)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            out.append(retarget_audio_template(template, as_mission, reason))
            added += 1
        return added

    add_templates(
        audio_templates_by_mission.get(target_mission) or [],
        as_mission=target_mission,
        reason="native",
    )
    for related in related_missions_by_mission.get(target_mission) or []:
        related_mission = safe_key(related.get("mission"))
        if not related_mission:
            continue
        reason = safe_key(related.get("reason")) or "related-mission"
        count = add_templates(
            audio_templates_by_mission.get(related_mission) or [],
            as_mission=target_mission,
            reason=reason,
            supplemental_only_map_dialogs=True,
        )
        if count:
            related_rows.append({"mission": related_mission, "reason": reason, "templates": count})
    return out, related_rows


def resolve_audio_executable(explicit: str | None = None) -> str | None:
    if explicit:
        path = Path(explicit)
        if path.is_file():
            return str(path)
        return explicit
    return shutil.which("ffmpeg")


def audio_source_fingerprint(path: Path) -> dict[str, Any]:
    try:
        stat = path.stat()
    except OSError:
        return {"path": str(path), "missing": True}
    return {
        "path": rel_path(path) if path.is_relative_to(ROOT) else str(path),
        "size": stat.st_size,
        "mtimeNs": stat.st_mtime_ns,
    }


def audio_cache_path(path: Path, *, prefix: str, params: dict[str, Any]) -> Path:
    source = str(path.resolve()).lower()
    digest = hashlib.sha1(
        json.dumps({"source": source, "params": params}, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]
    stem = AUDIO_CACHE_SAFE_RE.sub("_", path.stem).strip("._")[:96] or "audio"
    return AUDIO_CACHE_ROOT / prefix / f"{stem}_{digest}.json"


def write_audio_cache(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    write_text_if_changed(path, text)


def decode_audio_pcm(
    path: Path,
    *,
    ffmpeg: str,
    sample_rate: int,
    audio_filter: str,
) -> bytes:
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(path),
        "-vn",
        "-map",
        "0:a:0",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
    ]
    if safe_key(audio_filter):
        command.extend(["-af", audio_filter])
    command.extend(["-f", "s16le", "-"])
    proc = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(detail or f"ffmpeg audio decode failed for {path}")
    return proc.stdout


def pcm16le_to_fingerprint(
    pcm: bytes,
    *,
    sample_rate: int,
    frame_seconds: float,
    source: str,
) -> AudioFingerprint:
    if len(pcm) < 2:
        return AudioFingerprint([], [], frame_seconds, 0.0, source)
    if len(pcm) % 2:
        pcm = pcm[:-1]
    samples = array("h")
    samples.frombytes(pcm)
    if sys.byteorder != "little":
        samples.byteswap()
    frame_samples = max(1, int(round(sample_rate * frame_seconds)))
    min_tail = max(64, frame_samples // 2)
    energy: list[float] = []
    sample_count = len(samples)
    for start in range(0, sample_count, frame_samples):
        end = min(sample_count, start + frame_samples)
        count = end - start
        if count < min_tail:
            continue
        total = 0.0
        for index in range(start, end):
            value = samples[index]
            total += value * value
        rms = math.sqrt(total / count) / 32768.0 if count else 0.0
        # The ffmpeg prefilter keeps the speech band; log RMS plus first
        # differences gives a compact fingerprint that is less sensitive to
        # steady BGM than raw waveform correlation.
        energy.append(round(math.log1p(rms * 64.0), 6))
    delta = [0.0]
    for left, right in zip(energy, energy[1:]):
        delta.append(round(right - left, 6))
    if not energy:
        delta = []
    return AudioFingerprint(
        energy=energy,
        delta=delta,
        frame_seconds=frame_seconds,
        duration_seconds=sample_count / sample_rate if sample_rate > 0 else 0.0,
        source=source,
    )


def load_audio_fingerprint(
    path: Path,
    *,
    ffmpeg: str,
    sample_rate: int,
    frame_seconds: float,
    audio_filter: str,
    cache_prefix: str,
    memory_cache: dict[tuple[str, int, float, str], AudioFingerprint] | None = None,
) -> AudioFingerprint:
    cache_key = (str(path.resolve()).lower(), sample_rate, frame_seconds, audio_filter)
    if memory_cache is not None and cache_key in memory_cache:
        return memory_cache[cache_key]
    params = {
        "schema": "audioFingerprint.v1",
        "sampleRate": sample_rate,
        "frameSeconds": frame_seconds,
        "ffmpegFilter": audio_filter,
    }
    fingerprint = audio_source_fingerprint(path)
    cache_path = audio_cache_path(path, prefix=cache_prefix, params=params)
    cached = read_json(cache_path, {})
    if (
        isinstance(cached, dict)
        and cached.get("params") == params
        and cached.get("sourceFingerprint") == fingerprint
    ):
        raw = cached.get("fingerprint") if isinstance(cached.get("fingerprint"), dict) else {}
        energy = raw.get("energy") if isinstance(raw.get("energy"), list) else []
        delta = raw.get("delta") if isinstance(raw.get("delta"), list) else []
        fp = AudioFingerprint(
            energy=[float_value(value) for value in energy],
            delta=[float_value(value) for value in delta],
            frame_seconds=float_value(raw.get("frameSeconds"), frame_seconds),
            duration_seconds=float_value(raw.get("durationSeconds")),
            source=safe_key(raw.get("source")),
        )
        if memory_cache is not None:
            memory_cache[cache_key] = fp
        return fp

    pcm = decode_audio_pcm(path, ffmpeg=ffmpeg, sample_rate=sample_rate, audio_filter=audio_filter)
    fp = pcm16le_to_fingerprint(
        pcm,
        sample_rate=sample_rate,
        frame_seconds=frame_seconds,
        source=rel_path(path) if path.is_relative_to(ROOT) else str(path),
    )
    write_audio_cache(cache_path, {
        "params": params,
        "sourceFingerprint": fingerprint,
        "fingerprint": {
            "source": fp.source,
            "durationSeconds": round(fp.duration_seconds, 4),
            "frameSeconds": fp.frame_seconds,
            "energy": fp.energy,
            "delta": fp.delta,
        },
    })
    if memory_cache is not None:
        memory_cache[cache_key] = fp
    return fp


def prefix_sums(values: list[float]) -> tuple[list[float], list[float]]:
    sums = [0.0]
    squares = [0.0]
    total = 0.0
    square_total = 0.0
    for value in values:
        total += value
        square_total += value * value
        sums.append(total)
        squares.append(square_total)
    return sums, squares


def build_audio_search_index(fingerprint: AudioFingerprint) -> AudioSearchIndex:
    energy_prefix, energy_sq_prefix = prefix_sums(fingerprint.energy)
    delta_prefix, delta_sq_prefix = prefix_sums(fingerprint.delta)
    return AudioSearchIndex(
        fingerprint=fingerprint,
        energy_prefix=energy_prefix,
        energy_sq_prefix=energy_sq_prefix,
        delta_prefix=delta_prefix,
        delta_sq_prefix=delta_sq_prefix,
    )


def normalize_template_series(values: list[float]) -> list[float]:
    if len(values) < 3:
        return []
    mean = sum(values) / len(values)
    centered = [value - mean for value in values]
    norm = math.sqrt(sum(value * value for value in centered))
    if norm <= 1e-8:
        return []
    return [value / norm for value in centered]


def window_norm(prefix: list[float], square_prefix: list[float], start: int, length: int) -> float:
    end = start + length
    total = prefix[end] - prefix[start]
    square_total = square_prefix[end] - square_prefix[start]
    centered = max(0.0, square_total - (total * total / length))
    return math.sqrt(centered)


def normalized_window_score(
    template: list[float],
    values: list[float],
    prefix: list[float],
    square_prefix: list[float],
    start: int,
) -> float | None:
    length = len(template)
    norm = window_norm(prefix, square_prefix, start, length)
    if norm <= 1e-8:
        return None
    dot = 0.0
    for offset, template_value in enumerate(template):
        dot += template_value * values[start + offset]
    return max(-1.0, min(1.0, dot / norm))


def audio_window_score(
    search: AudioSearchIndex,
    *,
    start: int,
    energy_template: list[float],
    delta_template: list[float],
) -> AudioWindowHit | None:
    energy_score = normalized_window_score(
        energy_template,
        search.fingerprint.energy,
        search.energy_prefix,
        search.energy_sq_prefix,
        start,
    ) if energy_template else None
    delta_score = normalized_window_score(
        delta_template,
        search.fingerprint.delta,
        search.delta_prefix,
        search.delta_sq_prefix,
        start,
    ) if delta_template else None
    if energy_score is None and delta_score is None:
        return None
    if energy_score is None:
        score = float(delta_score)
        energy_value = 0.0
        delta_value = float(delta_score)
    elif delta_score is None:
        score = float(energy_score)
        energy_value = float(energy_score)
        delta_value = 0.0
    else:
        energy_value = float(energy_score)
        delta_value = float(delta_score)
        score = 0.62 * energy_value + 0.38 * delta_value
    return AudioWindowHit(
        start_index=start,
        score=max(-1.0, min(1.0, score)),
        energy_score=energy_value,
        delta_score=delta_value,
    )


def template_landmarks(values: list[float], limit: int) -> list[AudioLandmark]:
    if limit <= 0 or not values:
        return []
    ranked = sorted(
        enumerate(values),
        key=lambda item: (-abs(item[1]), item[0]),
    )
    return [AudioLandmark(offset=index, value=value) for index, value in ranked[:limit]]


def landmark_score(
    values: list[float],
    prefix: list[float],
    square_prefix: list[float],
    *,
    start: int,
    length: int,
    landmarks: list[AudioLandmark],
) -> float | None:
    if not landmarks:
        return None
    end = start + length
    if start < 0 or end > len(values):
        return None
    window_total = prefix[end] - prefix[start]
    mean = window_total / length
    dot = 0.0
    template_square = 0.0
    window_square = 0.0
    for landmark in landmarks:
        centered = values[start + landmark.offset] - mean
        dot += landmark.value * centered
        template_square += landmark.value * landmark.value
        window_square += centered * centered
    if template_square <= 1e-10 or window_square <= 1e-10:
        return None
    return max(-1.0, min(1.0, dot / math.sqrt(template_square * window_square)))


def audio_landmark_candidate_starts(
    search: AudioSearchIndex,
    *,
    length: int,
    energy_template: list[float],
    delta_template: list[float],
    search_step: int,
    max_candidates: int,
    landmarks_per_series: int,
    neighbor_steps: int,
) -> tuple[list[int], int]:
    step = max(1, search_step)
    max_start = len(search.fingerprint.energy) - length
    if max_start < 0:
        return [], 0
    starts = list(range(0, max_start + 1, step))
    if max_candidates <= 0 or len(starts) <= max_candidates:
        return starts, len(starts)

    energy_landmarks = template_landmarks(energy_template, landmarks_per_series)
    delta_landmarks = template_landmarks(delta_template, landmarks_per_series)
    if not energy_landmarks and not delta_landmarks:
        return starts, len(starts)

    scored: list[tuple[float, int]] = []
    for start in starts:
        energy_score = landmark_score(
            search.fingerprint.energy,
            search.energy_prefix,
            search.energy_sq_prefix,
            start=start,
            length=length,
            landmarks=energy_landmarks,
        ) if energy_landmarks else None
        delta_score = landmark_score(
            search.fingerprint.delta,
            search.delta_prefix,
            search.delta_sq_prefix,
            start=start,
            length=length,
            landmarks=delta_landmarks,
        ) if delta_landmarks else None
        if energy_score is None and delta_score is None:
            continue
        if energy_score is None:
            score = float(delta_score)
        elif delta_score is None:
            score = float(energy_score)
        else:
            score = 0.62 * float(energy_score) + 0.38 * float(delta_score)
        scored.append((score, start))

    if not scored:
        return starts, len(starts)

    scored.sort(key=lambda row: (-row[0], row[1]))
    selected: set[int] = set()
    for _score, start in scored[:max_candidates]:
        for offset in range(-neighbor_steps, neighbor_steps + 1):
            candidate = start + (offset * step)
            if 0 <= candidate <= max_start:
                selected.add(candidate)
    if not selected:
        return starts, len(starts)
    return sorted(selected), len(starts)


def add_separated_audio_hit(hits: list[AudioWindowHit], hit: AudioWindowHit, *, separation: int) -> None:
    remaining: list[AudioWindowHit] = []
    for old in hits:
        if abs(old.start_index - hit.start_index) < separation:
            if old.score >= hit.score:
                return
            continue
        remaining.append(old)
    remaining.append(hit)
    remaining.sort(key=lambda row: (-row.score, row.start_index))
    del remaining[8:]
    hits[:] = remaining


def match_audio_template(
    search: AudioSearchIndex,
    template_fingerprint: AudioFingerprint,
    *,
    search_step: int,
    second_gap_seconds: float,
    prefilter_candidates: int,
    prefilter_landmarks: int,
    prefilter_neighbor_steps: int,
) -> tuple[AudioWindowHit | None, AudioWindowHit | None, dict[str, int]]:
    length = len(template_fingerprint.energy)
    if length < 3 or len(search.fingerprint.energy) < length:
        return None, None, {"windowsScanned": 0, "candidateWindowsScanned": 0, "prefilterInputWindows": 0}
    energy_template = normalize_template_series(template_fingerprint.energy)
    delta_template = normalize_template_series(template_fingerprint.delta)
    if not energy_template and not delta_template:
        return None, None, {"windowsScanned": 0, "candidateWindowsScanned": 0, "prefilterInputWindows": 0}
    separation = max(length, int(round(second_gap_seconds / search.fingerprint.frame_seconds)))
    hits: list[AudioWindowHit] = []
    candidate_starts, prefilter_input_windows = audio_landmark_candidate_starts(
        search,
        length=length,
        energy_template=energy_template,
        delta_template=delta_template,
        search_step=search_step,
        max_candidates=prefilter_candidates,
        landmarks_per_series=prefilter_landmarks,
        neighbor_steps=prefilter_neighbor_steps,
    )
    scanned = 0
    for start in candidate_starts:
        hit = audio_window_score(
            search,
            start=start,
            energy_template=energy_template,
            delta_template=delta_template,
        )
        scanned += 1
        if hit is not None:
            add_separated_audio_hit(hits, hit, separation=separation)
    best = hits[0] if hits else None
    second = hits[1] if len(hits) > 1 else None
    return best, second, {
        "windowsScanned": scanned,
        "candidateWindowsScanned": len(candidate_starts),
        "prefilterInputWindows": prefilter_input_windows,
    }


def audio_match_row(
    *,
    template: AudioStoryTemplate,
    template_fingerprint: AudioFingerprint,
    hit: AudioWindowHit,
    second: AudioWindowHit | None,
    min_score: float,
    min_margin: float,
) -> dict[str, Any] | None:
    score = max(0.0, hit.score)
    second_score = max(0.0, second.score) if second else 0.0
    margin = score - second_score if second else score
    if score < min_score or margin < min_margin:
        return None
    start_seconds = hit.start_index * template_fingerprint.frame_seconds
    duration = len(template_fingerprint.energy) * template_fingerprint.frame_seconds
    end_seconds = start_seconds + duration
    return {
        "segment": {
            "startTime": seconds_to_clock(start_seconds),
            "startTimeSeconds": round(start_seconds, 4),
            "endTime": seconds_to_clock(end_seconds),
            "endTimeSeconds": round(end_seconds, 4),
            "sampleCount": len(template_fingerprint.energy),
            "text": template.text,
            "audioDurationSeconds": round(template_fingerprint.duration_seconds, 4),
        },
        "best": {
            "score": round(score, 4),
            "mission": template.mission,
            "actualMission": template.actual_mission,
            "linkReason": template.link_reason,
            "key": template.key,
            "lineId": template.line_id,
            "source": AUDIO_TEMPLATE_SOURCE,
            "audioSource": template.source,
            "text": template.text,
            "audioId": template.audio_id,
            "audioSrc": template.audio_src,
            "audioPath": rel_path(template.audio_path) if template.audio_path.is_relative_to(ROOT) else str(template.audio_path),
        },
        "margin": round(margin, 4),
        "top": [
            {
                "startTime": seconds_to_clock(hit.start_index * template_fingerprint.frame_seconds),
                "startTimeSeconds": round(hit.start_index * template_fingerprint.frame_seconds, 4),
                "score": round(max(0.0, hit.score), 4),
                "energyScore": round(hit.energy_score, 4),
                "deltaScore": round(hit.delta_score, 4),
            },
            *([
                {
                    "startTime": seconds_to_clock(second.start_index * template_fingerprint.frame_seconds),
                    "startTimeSeconds": round(second.start_index * template_fingerprint.frame_seconds, 4),
                    "score": round(max(0.0, second.score), 4),
                    "energyScore": round(second.energy_score, 4),
                    "deltaScore": round(second.delta_score, 4),
                }
            ] if second else []),
        ],
        "accepted": True,
        "synthetic": True,
        "evidence": "audio-template",
        "audioThresholds": {
            "minScore": min_score,
            "minMargin": min_margin,
        },
    }


def build_audio_template_matches(
    *,
    video_path: Path,
    templates: list[AudioStoryTemplate],
    ffmpeg: str,
    args: argparse.Namespace,
    memory_cache: dict[tuple[str, int, float, str], AudioFingerprint],
    label: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    stats: Counter[str] = Counter()
    stats["candidateTemplates"] = len(templates)
    if not templates:
        return [], dict(stats)
    started = time.monotonic()
    try:
        video_fingerprint = load_audio_fingerprint(
            video_path,
            ffmpeg=ffmpeg,
            sample_rate=args.audio_sample_rate,
            frame_seconds=args.audio_frame_seconds,
            audio_filter=args.audio_ffmpeg_filter,
            cache_prefix="videos",
            memory_cache=memory_cache,
        )
    except RuntimeError as error:
        stats["videoDecodeErrors"] += 1
        stats["error"] = str(error)[:500]
        return [], dict(stats)
    if not video_fingerprint.energy:
        stats["emptyVideoFingerprint"] += 1
        return [], dict(stats)
    search = build_audio_search_index(video_fingerprint)
    matches: list[dict[str, Any]] = []
    for index, template in enumerate(templates):
        try:
            template_fingerprint = load_audio_fingerprint(
                template.audio_path,
                ffmpeg=ffmpeg,
                sample_rate=args.audio_sample_rate,
                frame_seconds=args.audio_frame_seconds,
                audio_filter=args.audio_ffmpeg_filter,
                cache_prefix="templates",
                memory_cache=memory_cache,
            )
        except RuntimeError:
            stats["templateDecodeErrors"] += 1
            continue
        duration = template_fingerprint.duration_seconds
        if duration < args.audio_min_duration:
            stats["skipTooShort"] += 1
            continue
        if duration > args.audio_max_duration:
            stats["skipTooLong"] += 1
            continue
        best, second, scan_stats = match_audio_template(
            search,
            template_fingerprint,
            search_step=args.audio_search_step,
            second_gap_seconds=args.audio_second_gap,
            prefilter_candidates=args.audio_prefilter_candidates,
            prefilter_landmarks=args.audio_prefilter_landmarks,
            prefilter_neighbor_steps=args.audio_prefilter_neighbor_steps,
        )
        stats["windowsScanned"] += int(scan_stats.get("windowsScanned") or 0)
        stats["candidateWindowsScanned"] += int(scan_stats.get("candidateWindowsScanned") or 0)
        stats["prefilterInputWindows"] += int(scan_stats.get("prefilterInputWindows") or 0)
        stats["templatesScanned"] += 1
        if best is None:
            stats["skipNoUsableFingerprint"] += 1
            continue
        row = audio_match_row(
            template=template,
            template_fingerprint=template_fingerprint,
            hit=best,
            second=second,
            min_score=args.audio_min_score,
            min_margin=args.audio_min_margin,
        )
        if row is None:
            stats["rejected"] += 1
            if not args.no_progress:
                progress_bar(
                    f"[{label}] audio",
                    index + 1,
                    len(templates),
                    started=started,
                    force=(index + 1 == len(templates)),
                )
            continue
        matches.append(row)
        stats["accepted"] += 1
        if not args.no_progress:
            progress_bar(
                f"[{label}] audio",
                index + 1,
                len(templates),
                started=started,
                force=(index + 1 == len(templates)),
            )

    if args.audio_max_matches_per_video > 0 and len(matches) > args.audio_max_matches_per_video:
        matches = sorted(
            matches,
            key=lambda row: (-float_value(row.get("best", {}).get("score")), match_start_seconds(row)),
        )[: args.audio_max_matches_per_video]
        stats["capped"] = len(matches)
    matches.sort(key=match_start_seconds)
    stats["elapsedSeconds"] = round(time.monotonic() - started, 3)
    return matches, dict(stats)


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
            for dialog in dialogs:
                if dialog.key == archive.key:
                    continue
                same_scene = archive.scene is not None and archive.scene == dialog.scene
                shared = sorted((archive.grams & dialog.grams & rare_grams) - COMPANION_STOP_BIGRAMS)
                title_shared = sorted((archive.title_grams & dialog.grams & rare_grams) - COMPANION_STOP_BIGRAMS)
                if not same_scene and (len(shared) < 2 or not title_shared):
                    continue
                reason = "same-scene" if same_scene else "archive-title-overlap"
                if same_scene and title_shared:
                    reason = f"{reason}+title-overlap"
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
            out.append({
                "segment": companion_segment,
                "best": companion_best,
                "margin": 0.995,
                "top": [companion_best],
                "accepted": True,
                "synthetic": True,
            })
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


def is_audio_template_match(match: dict[str, Any]) -> bool:
    best = match.get("best") if isinstance(match.get("best"), dict) else {}
    return safe_key(best.get("source")) == AUDIO_TEMPLATE_SOURCE or safe_key(match.get("evidence")) == "audio-template"


def copy_matches_for_threshold(
    *,
    ocr_matches: list[dict[str, Any]],
    audio_matches: list[dict[str, Any]],
    min_score: float,
    min_margin: float,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for match in ocr_matches:
        row = dict(match)
        row["accepted"] = is_accept(row, min_score=min_score, min_margin=min_margin)
        out.append(row)
    for match in audio_matches:
        row = dict(match)
        row["accepted"] = bool(row.get("accepted"))
        out.append(row)
    return out


def float_value(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def source_quality(source: Any) -> int:
    source_key = safe_key(source)
    if source_key == AUDIO_TEMPLATE_SOURCE or source_key.startswith("audio-"):
        return 3
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
    elif source == AUDIO_TEMPLATE_SOURCE or source.startswith("audio-"):
        span["audioMatches"] = int(span.get("audioMatches") or 0) + 1
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
        "audioMatches": 0,
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
        strong_matches = int(span.get("lineLikeMatches") or 0) + int(span.get("audioMatches") or 0)
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
        "audioMatches": span.get("audioMatches"),
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

        audio_like = [span for span in choices if int(span.get("audioMatches") or 0) > 0]
        line_like = [span for span in choices if int(span.get("lineLikeMatches") or 0) > 0]
        candidate_choices = audio_like or line_like or choices

        def sort_key(span: dict[str, Any]) -> tuple[float, int, int, int, float, float]:
            residual = span.get("ransacResidual")
            residual_value = float_value(residual, 1_000_000.0) if model else 0.0
            return (
                residual_value,
                -int(span.get("audioMatches") or 0),
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
        if audio_like and len(audio_like) != len(choices):
            reason = "audio-evidence-over-ocr"
        elif line_like and len(line_like) != len(choices):
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
            if (
                bool(match.get("accepted")) if is_audio_template_match(match)
                else is_accept(match, min_score=threshold, min_margin=min_margin)
            )
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
        if params.get("limitFrames") is not None and not include_smoke:
            stats["skip_smoke"] += 1
            continue
        payload["_reportPath"] = rel_path(path)
        reports.append(payload)
        stats["loaded"] += 1
    return reports, stats


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
) -> tuple[Counter[str], dict[str, list[dict[str, Any]]], dict[str, dict[str, Any]]]:
    accepted_missions = Counter(
        safe_key(match.get("best", {}).get("mission"))
        for match in matches
        if match.get("accepted") and safe_key(match.get("best", {}).get("mission"))
    )
    observed_sequences: dict[str, list[dict[str, Any]]] = {}
    sequence_diagnostics: dict[str, dict[str, Any]] = {}
    for mission, count in accepted_missions.items():
        if count < min_video_matches:
            continue
        sequence, diagnostics = collapse_observed_sequence(
            matches,
            mission,
            current_order=base_story_orders.get(mission) or [],
            use_ransac=use_ransac,
            ransac_tolerance=ransac_tolerance,
        )
        if len(sequence) >= min_sequence_keys:
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
        audio_matches=[],
        min_score=min_score,
        min_margin=min_margin,
    )
    audio_matches = [
        {**match, "accepted": bool(match.get("accepted"))}
        for match in (record.get("audioMatches") or [])
    ]
    map_dialog_companion_matches = build_map_dialog_companion_matches(ocr_matches, map_dialog_companion_index)
    matches = ocr_matches + map_dialog_companion_matches + audio_matches
    accepted_missions, observed_sequences, sequence_diagnostics = observed_sequences_from_matches(
        matches,
        base_story_orders=base_story_orders,
        min_video_matches=min_video_matches,
        min_sequence_keys=min_sequence_keys,
        use_ransac=use_ransac,
        ransac_tolerance=ransac_tolerance,
    )
    accepted_count = sum(1 for match in matches if match.get("accepted"))
    result = {
        "matches": matches,
        "matchedSegments": len(matches),
        "acceptedMatches": accepted_count,
        "mapDialogCompanionMatches": len(map_dialog_companion_matches),
        "audioTemplateMatches": len(audio_matches),
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
            "audioTemplateMatches": len(audio_matches),
            "missions": result["missions"],
            "observedSequences": observed_sequences,
            "sequenceDiagnostics": sequence_diagnostics,
            "matches": sorted(matches, key=match_start_seconds)[:200],
        })
    return result


def locked_sequence_mismatch_details(
    sequence: list[dict[str, Any]],
    locked_order: list[str],
    *,
    video: str,
    mission: str,
) -> dict[str, Any]:
    positions = {key: index for index, key in enumerate(locked_order)}
    checked: list[tuple[str, int, dict[str, Any]]] = []
    missing_keys: list[str] = []
    for item in sequence:
        key = safe_key(item.get("key"))
        if not key:
            continue
        position = positions.get(key)
        if position is None:
            missing_keys.append(key)
            continue
        checked.append((key, position, item))

    adjacent: list[dict[str, Any]] = []
    for left, right in zip(checked, checked[1:]):
        left_key, left_position, left_item = left
        right_key, right_position, right_item = right
        if right_position < left_position:
            adjacent.append({
                "video": video,
                "mission": mission,
                "prevKey": left_key,
                "prevOrderIndex": left_position,
                "prevTime": left_item.get("firstTime"),
                "key": right_key,
                "orderIndex": right_position,
                "time": right_item.get("firstTime"),
            })

    inversions = 0
    for left_index, (_left_key, left_position, _left_item) in enumerate(checked):
        for _right_key, right_position, _right_item in checked[left_index + 1:]:
            if right_position < left_position:
                inversions += 1

    return {
        "checkedKeys": len(checked),
        "missingKeys": len(missing_keys),
        "mismatches": len(adjacent),
        "inversions": inversions,
        "samples": adjacent[:8],
    }


def validate_locked_order_sequences(
    videos: list[dict[str, Any]],
    *,
    locked_orders: dict[str, list[str]],
) -> dict[str, Any]:
    by_mission: dict[str, dict[str, Any]] = {}
    for video in videos:
        video_name = safe_key(video.get("video"))
        sequences = video.get("observedSequences") if isinstance(video.get("observedSequences"), dict) else {}
        for mission, sequence in sequences.items():
            mission_key = safe_key(mission)
            locked_order = locked_orders.get(mission_key)
            if not locked_order or not isinstance(sequence, list):
                continue
            row = by_mission.setdefault(mission_key, {
                "mission": mission_key,
                "videos": [],
                "observedKeys": 0,
                "checkedKeys": 0,
                "missingKeys": 0,
                "mismatches": 0,
                "inversions": 0,
                "samples": [],
            })
            details = locked_sequence_mismatch_details(
                sequence,
                locked_order,
                video=video_name,
                mission=mission_key,
            )
            row["videos"].append(video_name)
            row["observedKeys"] += len(sequence)
            row["checkedKeys"] += int(details["checkedKeys"])
            row["missingKeys"] += int(details["missingKeys"])
            row["mismatches"] += int(details["mismatches"])
            row["inversions"] += int(details["inversions"])
            row["samples"].extend(details["samples"])
            del row["samples"][8:]

    rows = sorted(
        by_mission.values(),
        key=lambda row: (-int(row.get("mismatches") or 0), -int(row.get("inversions") or 0), row["mission"]),
    )
    for row in rows:
        row["videos"] = sorted(set(row.get("videos") or []))
        checked = int(row.get("checkedKeys") or 0)
        mismatches = int(row.get("mismatches") or 0)
        row["mismatchRate"] = round(mismatches / checked, 6) if checked else 0.0
    return {
        "summary": {
            "lockedMissionsWithEvidence": len(rows),
            "checkedKeys": sum(int(row.get("checkedKeys") or 0) for row in rows),
            "missingKeys": sum(int(row.get("missingKeys") or 0) for row in rows),
            "mismatches": sum(int(row.get("mismatches") or 0) for row in rows),
            "inversions": sum(int(row.get("inversions") or 0) for row in rows),
        },
        "missions": rows,
    }


def build_locked_threshold_sweep(
    records: list[dict[str, Any]],
    *,
    locked_orders: dict[str, list[str]],
    map_dialog_companion_index: dict[str, list[dict[str, Any]]],
    base_story_orders: dict[str, list[str]],
    min_margin: float,
    current_min_score: float,
    min_video_matches: int,
    min_sequence_keys: int,
    use_ransac: bool,
    ransac_tolerance: float,
) -> list[dict[str, Any]]:
    if not locked_orders or not records:
        return []
    thresholds = sorted({round(value, 4) for value in (*DEFAULT_THRESHOLD_SWEEP, current_min_score)}, reverse=True)
    rows: list[dict[str, Any]] = []
    for threshold in thresholds:
        videos: list[dict[str, Any]] = []
        accepted = 0
        matched = 0
        for record in records:
            result = finalize_video_match_record(
                record,
                min_score=threshold,
                min_margin=min_margin,
                map_dialog_companion_index=map_dialog_companion_index,
                base_story_orders=base_story_orders,
                min_video_matches=min_video_matches,
                min_sequence_keys=min_sequence_keys,
                use_ransac=use_ransac,
                ransac_tolerance=ransac_tolerance,
                update_video=False,
            )
            matched += int(result.get("matchedSegments") or 0)
            accepted += int(result.get("acceptedMatches") or 0)
            videos.append({"video": safe_key(record.get("videoName")), "observedSequences": result["observedSequences"]})
        validation = validate_locked_order_sequences(videos, locked_orders=locked_orders)
        summary = validation["summary"]
        checked = int(summary.get("checkedKeys") or 0)
        mismatches = int(summary.get("mismatches") or 0)
        rows.append({
            "minScore": threshold,
            "matchedSegments": matched,
            "acceptedMatches": accepted,
            "lockedMissionsWithEvidence": summary.get("lockedMissionsWithEvidence", 0),
            "checkedKeys": checked,
            "missingKeys": summary.get("missingKeys", 0),
            "mismatches": mismatches,
            "inversions": summary.get("inversions", 0),
            "mismatchRate": round(mismatches / checked, 6) if checked else 0.0,
        })
    return rows


def choose_locked_threshold(rows: list[dict[str, Any]], current_min_score: float) -> dict[str, Any]:
    usable = [row for row in rows if int(row.get("checkedKeys") or 0) > 0]
    if not usable:
        return {"minScore": current_min_score, "reason": "no-locked-evidence"}
    max_checked = max(int(row.get("checkedKeys") or 0) for row in usable)
    coverage_floor = max(1, int(math.ceil(max_checked * 0.80)))
    covered = [row for row in usable if int(row.get("checkedKeys") or 0) >= coverage_floor]
    best = min(
        covered or usable,
        key=lambda row: (
            int(row.get("mismatches") or 0),
            float_value(row.get("mismatchRate")),
            -int(row.get("checkedKeys") or 0),
            float_value(row.get("minScore")),
        ),
    )
    return {
        "minScore": float_value(best.get("minScore"), current_min_score),
        "reason": "locked-order-sweep",
        "coverageFloor": coverage_floor,
        "maxCheckedKeys": max_checked,
        "mismatches": int(best.get("mismatches") or 0),
        "checkedKeys": int(best.get("checkedKeys") or 0),
    }


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
    """Read the OCR-managed full-list story-order format."""
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


def current_story_orders(active_story_order: dict[str, Any]) -> tuple[dict[str, list[str]], set[str]]:
    stored_orders = story_orders_by_mission(active_story_order)
    return {mission: list(order) for mission, order in stored_orders.items()}, set(stored_orders)


def story_order_storage_payload(
    orders_by_mission: dict[str, list[str]],
    story_order: dict[str, Any],
    active_story_order: dict[str, Any],
) -> dict[str, Any]:
    base_orders = story_orders_by_mission(story_order)
    story_missions = story_order.get("missions") if isinstance(story_order, dict) else {}
    active_missions = active_story_order.get("missions") if isinstance(active_story_order, dict) else {}
    active_missions = active_missions if isinstance(active_missions, dict) else {}
    mission_positions = {mission: index for index, mission in enumerate(base_orders)}

    def mission_token(mission: str) -> tuple[Any, ...]:
        return (mission_positions.get(mission, len(mission_positions)), natural_sort_token(mission))

    missions: dict[str, Any] = {}
    for mission in sorted(orders_by_mission, key=mission_token):
        order = orders_by_mission.get(mission)
        if not order:
            continue
        raw_mission = story_missions.get(mission) if isinstance(story_missions, dict) else {}
        active_mission = active_missions.get(mission)
        locked = isinstance(active_mission, dict) and active_mission.get("locked") is True
        if locked:
            missions[mission] = active_mission
            continue
        out: dict[str, Any] = {"order": order}
        if isinstance(raw_mission, dict):
            level = safe_key(active_mission.get("level")) if isinstance(active_mission, dict) else ""
            if not level:
                level = safe_key(raw_mission.get("level"))
            levels = clean_order_list(active_mission.get("levels")) if isinstance(active_mission, dict) else []
            if not levels:
                levels = clean_order_list(raw_mission.get("levels"))
            if level:
                out["level"] = level
            if levels:
                out["levels"] = levels
        missions[mission] = out

    return {
        "_schema": "storyOrder.fullOrder.v1",
        "_note": (
            "Editable Story file order. Each missions.<mission>.order array is "
            "the complete ordered list of story file keys for that mission. "
            "Set missions.<mission>.locked to true to preserve that mission's "
            "order across OCR and browser writes; the WebUI can toggle it per mission."
        ),
        "missions": missions,
    }


def apply_observed_sequence_to_full_order(
    current_order: list[str],
    observed_keys: list[str],
) -> list[str]:
    sequence = clean_order_list(observed_keys)
    if len(sequence) < 2:
        return list(current_order)
    if not current_order:
        return sequence

    moving = set(sequence)
    current_positions = {key: index for index, key in enumerate(current_order)}
    first_present_index: int | None = None
    for key in sequence:
        if key in current_positions:
            first_present_index = current_positions[key]
            break
    remaining = [key for key in current_order if key not in moving]
    if first_present_index is None:
        insert_at = len(remaining)
    else:
        removed_before = sum(
            1
            for index, key in enumerate(current_order)
            if index < first_present_index and key in moving
        )
        insert_at = max(0, first_present_index - removed_before)
    return remaining[:insert_at] + sequence + remaining[insert_at:]


def add_indexed_gap_keys(
    *,
    mission: str,
    observed_keys: list[str],
    current_order: list[str],
) -> tuple[list[str], list[dict[str, Any]]]:
    """Insert conservative unobserved indexed keys near observed siblings.

    Example: if OCR sees ``radio_e1m3_3`` and later ``radio_e1m3_4``, then a
    known key such as ``radio_e1m3_3d5`` has enough filename-index evidence to
    sit between those two observed positions even if OCR missed its text.

    For radio tutorials, also allow the immediately preceding integer key when
    OCR starts at ``radio_*_N`` after an observed non-radio scene. These are
    often short instruction barks that happen during UI overlays.
    """
    if len(observed_keys) < 2 or not current_order:
        return observed_keys, []

    indexed_by_key: dict[str, IndexedStoryKey] = {}
    decimal_candidates_by_family: dict[str, list[IndexedStoryKey]] = defaultdict(list)
    all_candidates_by_family: dict[str, list[IndexedStoryKey]] = defaultdict(list)
    observed_set = set(observed_keys)
    current_positions = {key: index for index, key in enumerate(current_order)}
    for order_index, key in enumerate(current_order):
        indexed = parse_indexed_story_key(key, mission, order_index)
        if not indexed:
            continue
        indexed_by_key[indexed.key] = indexed
        if indexed.key not in observed_set:
            all_candidates_by_family[indexed.family].append(indexed)
            if indexed.has_decimal:
                decimal_candidates_by_family[indexed.family].append(indexed)

    if not all_candidates_by_family:
        return observed_keys, []

    for candidates in all_candidates_by_family.values():
        candidates.sort(key=lambda row: (row.number, row.order_index, row.key))
    for candidates in decimal_candidates_by_family.values():
        candidates.sort(key=lambda row: (row.number, row.order_index, row.key))

    observed_by_family: dict[str, list[tuple[int, IndexedStoryKey]]] = defaultdict(list)
    for sequence_index, key in enumerate(observed_keys):
        indexed = indexed_by_key.get(key)
        if indexed:
            observed_by_family[indexed.family].append((sequence_index, indexed))

    insert_before: dict[int, list[IndexedStoryKey]] = defaultdict(list)
    inferred: list[dict[str, Any]] = []
    used: set[str] = set()
    for family, bounds in observed_by_family.items():
        if len(bounds) < 2:
            continue
        for (left_index, left), (right_index, right) in zip(bounds, bounds[1:]):
            if left.number >= right.number:
                continue
            between = [
                candidate
                for candidate in decimal_candidates_by_family.get(family, [])
                if left.number < candidate.number < right.number and candidate.key not in used
            ]
            if not between:
                continue
            for candidate in between:
                used.add(candidate.key)
                insert_before[right_index].append(candidate)
                inferred.append({
                    "key": candidate.key,
                    "after": left.key,
                    "before": right.key,
                    "number": round(candidate.number, 6),
                    "reason": "bracketed-decimal",
                })

    for family, bounds in observed_by_family.items():
        family_kind = family.split("_", 1)[0]
        if family_kind != "radio" or not bounds:
            continue
        first_index, first = bounds[0]
        if first_index <= 0:
            continue
        previous_key = observed_keys[first_index - 1]
        previous_position = current_positions.get(previous_key)
        candidates = [
            candidate
            for candidate in all_candidates_by_family.get(family, [])
            if (
                not candidate.has_decimal
                and candidate.key not in used
                and candidate.order_index < first.order_index
                and candidate.number < first.number
                and first.number - candidate.number <= 1.000001
                and (previous_position is None or candidate.order_index > previous_position)
            )
        ]
        if not candidates:
            continue
        candidate = max(candidates, key=lambda row: (row.number, row.order_index, row.key))
        used.add(candidate.key)
        insert_before[first_index].append(candidate)
        inferred.append({
            "key": candidate.key,
            "after": previous_key,
            "before": first.key,
            "number": round(candidate.number, 6),
            "reason": "nearest-radio-predecessor",
        })

    if not insert_before:
        return observed_keys, []

    enriched: list[str] = []
    for sequence_index, key in enumerate(observed_keys):
        for candidate in sorted(
            insert_before.get(sequence_index) or [],
            key=lambda row: (row.number, row.order_index, row.key),
        ):
            enriched.append(candidate.key)
        enriched.append(key)
    return enriched, inferred


def natural_sort_token(value: Any) -> tuple[tuple[int, Any], ...]:
    parts: list[tuple[int, Any]] = []
    for part in NATURAL_SORT_RE.findall(safe_key(value).lower()):
        if part.isdigit():
            parts.append((0, int(part)))
        else:
            parts.append((1, part))
    return tuple(parts)


def sort_indexed_key_runs(
    *,
    mission: str,
    keys: list[str],
    current_order: list[str],
) -> list[str]:
    if len(keys) < 2:
        return keys

    current_positions = {key: index for index, key in enumerate(current_order)}
    fallback_start = len(current_order)

    def indexed_key(key: str, sequence_index: int) -> IndexedStoryKey | None:
        return parse_indexed_story_key(
            key,
            mission,
            current_positions.get(key, fallback_start + sequence_index),
        )

    out: list[str] = []
    run: list[tuple[str, IndexedStoryKey]] = []
    run_family = ""

    def flush_run() -> None:
        nonlocal run, run_family
        if len(run) > 1:
            run.sort(key=lambda row: (row[1].number, row[1].order_index, row[0]))
        out.extend(key for key, _indexed in run)
        run = []
        run_family = ""

    for sequence_index, key in enumerate(keys):
        indexed = indexed_key(key, sequence_index)
        if not indexed:
            flush_run()
            out.append(key)
            continue
        if run and indexed.family != run_family:
            flush_run()
        run.append((key, indexed))
        run_family = indexed.family
    flush_run()
    return out


def build_proposed_story_order(
    *,
    active_story_order: dict[str, Any],
    story_order: dict[str, Any],
    video_summaries: list[dict[str, Any]],
    min_sequence_keys: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    base_orders = story_orders_by_mission(story_order)
    next_orders, active_missions = current_story_orders(active_story_order)
    locked_missions = story_order_locked_missions(active_story_order)
    proposal_rows: list[dict[str, Any]] = []

    by_mission: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for video in video_summaries:
        for mission, sequence in (video.get("observedSequences") or {}).items():
            if len(sequence) >= min_sequence_keys:
                by_mission[mission].append({
                    "video": video.get("video"),
                    "sequence": sequence,
                })

    for mission, rows in sorted(by_mission.items()):
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
                        "linkReason": link_reason or "related-mission",
                        "firstTime": item.get("firstTime"),
                    })
        # Dedupe repeated observations across videos while preserving first
        # observed position.
        deduped: list[str] = []
        seen: set[str] = set()
        for key in observed_keys:
            if key in seen:
                continue
            seen.add(key)
            deduped.append(key)
        current_order = next_orders.get(mission) or base_orders.get(mission) or []
        if mission in locked_missions:
            proposal_rows.append({
                "mission": mission,
                "existingActiveOrder": mission in active_missions,
                "locked": True,
                "observedKeys": deduped,
                "proposalKeys": [],
                "linkedEntries": [],
                "indexedInferences": [],
                "changed": False,
                "skipReason": "locked",
                "changedKeys": [],
                "insertedKeys": [],
                "orderLength": len(current_order),
                "videos": [row["video"] for row in rows],
            })
            continue
        index_sorted = sort_indexed_key_runs(
            mission=mission,
            keys=deduped,
            current_order=current_order,
        )

        proposal_keys, indexed_inferences = add_indexed_gap_keys(
            mission=mission,
            observed_keys=index_sorted,
            current_order=current_order,
        )
        proposal_keys = sort_indexed_key_runs(
            mission=mission,
            keys=proposal_keys,
            current_order=current_order,
        )
        updated_order = apply_observed_sequence_to_full_order(current_order, proposal_keys)
        before_positions = {key: index for index, key in enumerate(current_order)}
        after_positions = {key: index for index, key in enumerate(updated_order)}
        changed_keys = [
            key
            for key in proposal_keys
            if before_positions.get(key) != after_positions.get(key)
        ]
        inserted_keys = [
            key
            for key in proposal_keys
            if key not in before_positions and key in after_positions
        ]
        changed = updated_order != current_order
        if changed:
            next_orders[mission] = updated_order

        proposal_rows.append({
            "mission": mission,
            "existingActiveOrder": mission in active_missions,
            "locked": False,
            "observedKeys": deduped,
            "proposalKeys": proposal_keys,
            "linkedEntries": [
                linked_entries_by_key[key]
                for key in proposal_keys
                if key in linked_entries_by_key
            ],
            "indexedInferences": indexed_inferences,
            "changed": changed,
            "changedKeys": changed_keys,
            "insertedKeys": inserted_keys,
            "orderLength": len(updated_order),
            "videos": [row["video"] for row in rows],
        })

    return story_order_storage_payload(next_orders, story_order, active_story_order), proposal_rows


def write_match_markdown(payload: dict[str, Any]) -> None:
    histogram = payload.get("scoreHistogram") or []
    max_histogram_count = max((int(row.get("segments") or 0) for row in histogram), default=0)
    lines = [
        "# Gameplay Video OCR/Audio Story-Order Matching",
        "",
        f"- OCR reports used: `{payload['summary']['ocrReportsUsed']}`",
        f"- Corpus lines: `{payload['summary']['corpusLines']}`",
        f"- Accepted segment matches: `{payload['summary']['acceptedMatches']}`",
        f"- Map-dialog companion matches: `{payload['summary'].get('mapDialogCompanionMatches', 0)}`",
        f"- Audio templates: `{payload['summary'].get('audioTemplates', 0)}`",
        f"- Audio template matches: `{payload['summary'].get('audioTemplateMatches', 0)}`",
        f"- Indexed gap inferences: `{payload['summary'].get('indexedInferences', 0)}`",
        f"- Linked map-dialog entries: `{payload['summary'].get('linkedEntries', 0)}`",
        f"- RANSAC models: `{payload['summary'].get('ransacModels', 0)}`",
        f"- RANSAC adjusted repeated keys: `{payload['summary'].get('ransacAdjustedKeys', 0)}`",
        f"- Ignored repeated spans: `{payload['summary'].get('ignoredRepeatedSpans', 0)}`",
        f"- Effective OCR min score: `{payload.get('thresholds', {}).get('effectiveMinScore', payload.get('thresholds', {}).get('minScore'))}`",
        f"- Locked-order mismatches: `{(payload['summary'].get('lockedValidation') or {}).get('mismatches', 0)}`",
        f"- Video mission title matches: `{payload['summary'].get('videoMissionMatches', {})}`",
        f"- Proposed story order: `{payload['outputs']['proposedStoryOrder']}`",
        "",
    ]
    if payload["summary"].get("activeOrderWarning"):
        lines.extend([
            f"> Warning: {md_escape(payload['summary']['activeOrderWarning'])}",
            "",
        ])
    if payload.get("lockedThresholdSweep"):
        choice = payload["summary"].get("lockedThresholdChoice") or {}
        lines.extend([
            "## Locked Threshold Calibration",
            "",
            f"- Selected min score: `{choice.get('minScore')}`",
            f"- Reason: `{md_escape(choice.get('reason'))}`",
            "",
            "| min score | accepted | locked checked | mismatches | inversions | mismatch rate |",
            "|---:|---:|---:|---:|---:|---:|",
        ])
        for row in payload["lockedThresholdSweep"]:
            lines.append(
                f"| {float(row.get('minScore') or 0):.2f} "
                f"| {int(row.get('acceptedMatches') or 0)} "
                f"| {int(row.get('checkedKeys') or 0)} "
                f"| {int(row.get('mismatches') or 0)} "
                f"| {int(row.get('inversions') or 0)} "
                f"| {float(row.get('mismatchRate') or 0):.4f} |"
            )
    locked_validation = payload.get("lockedValidation") if isinstance(payload.get("lockedValidation"), dict) else {}
    locked_rows = locked_validation.get("missions") if isinstance(locked_validation.get("missions"), list) else []
    if locked_rows:
        lines.extend([
            "",
            "## Locked Mismatches",
            "",
            "| mission | videos | observed | checked | missing | mismatches | inversions | mismatch rate |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ])
        for row in locked_rows:
            lines.append(
                f"| `{md_escape(row.get('mission'))}` "
                f"| {len(row.get('videos') or [])} "
                f"| {int(row.get('observedKeys') or 0)} "
                f"| {int(row.get('checkedKeys') or 0)} "
                f"| {int(row.get('missingKeys') or 0)} "
                f"| {int(row.get('mismatches') or 0)} "
                f"| {int(row.get('inversions') or 0)} "
                f"| {float(row.get('mismatchRate') or 0):.4f} |"
            )
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
            "## Proposals",
            "",
            "| mission | status | active | changed | observed | proposal | inferred/linked | moved/inserted | order size | videos |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
        ])
        for row in payload["proposals"]:
            indexed = len(row.get("indexedInferences") or [])
            linked = len(row.get("linkedEntries") or [])
            moved = len(row.get("changedKeys") or [])
            inserted = len(row.get("insertedKeys") or [])
            status = safe_key(row.get("skipReason")) or ("changed" if row.get("changed") else "unchanged")
            lines.append(
                f"| `{md_escape(row.get('mission'))}` "
                f"| `{md_escape(status)}` "
                f"| `{str(bool(row.get('existingActiveOrder'))).lower()}` "
                f"| `{str(bool(row.get('changed'))).lower()}` "
                f"| {len(row.get('observedKeys') or [])} "
                f"| {len(row.get('proposalKeys') or [])} "
                f"| {indexed + linked} "
                f"| {moved}/{inserted} "
                f"| {int(row.get('orderLength') or 0)} "
                f"| `{md_escape(', '.join(row.get('videos') or []))}` |"
            )
    if payload.get("videos"):
        lines.extend([
            "",
            "## Videos",
            "",
            "| video | target mission | report | accepted | companions | audio | matched missions | observed sequences |",
            "|---|---|---|---:|---:|---:|---|---:|",
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
            lines.append(
                f"| `{md_escape(video.get('video'))}` "
                f"| `{md_escape(target_label)}` "
                f"| `{md_escape(video.get('report'))}` "
                f"| {video.get('acceptedMatches', 0)} "
                f"| {video.get('mapDialogCompanionMatches', 0)} "
                f"| {video.get('audioTemplateMatches', 0)} "
                f"| `{md_escape(', '.join(video.get('missions') or []))}` "
                f"| {seq_count} |"
            )
    write_text_if_changed(MATCH_MD_PATH, "\n".join(lines) + "\n")


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
        "--frame-step",
        str(args.frame_step),
        "--crop",
        args.ocr_crop,
        "--prefilter-max-duplicate-skip",
        str(args.prefilter_max_duplicate_skip),
    ]
    if args.force_ocr:
        command.append("--force")
    if args.ocr_limit is not None:
        command.extend(["--limit", str(args.ocr_limit)])
    if args.ocr_limit_frames is not None:
        command.extend(["--limit-frames", str(args.ocr_limit_frames)])
    if args.easyocr_cpu:
        command.append("--easyocr-cpu")
    if args.ocr_low_memory:
        command.append("--low-memory")
    if args.disable_archive_box_ocr:
        command.append("--disable-archive-box-ocr")
    if args.no_progress:
        command.append("--no-progress")
    print(
        "Running OCR sampler: "
        f"frame_step={args.frame_step}, crop={args.ocr_crop}, "
        f"low_memory={args.ocr_low_memory}, fast_profile={args.frame_step >= 60}, "
        f"archive_box_ocr={not args.disable_archive_box_ocr}, "
        f"prefilter_max_duplicate_skip={args.prefilter_max_duplicate_skip}, "
        f"limit={args.ocr_limit if args.ocr_limit is not None else 'all'}, "
        f"limit_frames={args.ocr_limit_frames if args.ocr_limit_frames is not None else 'full'}"
    )
    run_subprocess(command)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-ocr", action="store_true", help="run OCR before matching")
    parser.add_argument("--frame-step", type=int, default=45, help="OCR frame step when --run-ocr is used")
    parser.add_argument("--ocr-crop", choices=["lower-half", "lower-third", "full"], default="lower-half")
    parser.add_argument("--force-ocr", action="store_true")
    parser.add_argument("--ocr-limit", type=int, default=None)
    parser.add_argument("--ocr-limit-frames", type=int, default=None)
    parser.add_argument("--easyocr-cpu", action="store_true")
    parser.add_argument("--ocr-low-memory", action="store_true", help="Cap EasyOCR batches at 8 and clean up after every OCR batch")
    parser.add_argument("--disable-archive-box-ocr", action="store_true", help="Disable the second-pass archive reading-panel OCR sampler")
    parser.add_argument("--prefilter-max-duplicate-skip", type=int, default=2, help="Max consecutive duplicate-looking sampled frames to skip before forcing OCR")
    parser.add_argument("--include-smoke", action="store_true", help="include OCR reports produced with --limit-frames")
    parser.add_argument("--include-stale-ocr", action="store_true", help="include OCR reports generated by older filter versions")
    parser.add_argument("--min-chars", type=int, default=4)
    parser.add_argument("--min-score", type=float, default=0.75)
    parser.add_argument("--min-margin", type=float, default=0.06)
    parser.add_argument("--topn", type=int, default=5)
    parser.add_argument("--min-video-matches", type=int, default=2)
    parser.add_argument("--min-sequence-keys", type=int, default=2)
    parser.add_argument("--no-ransac", action="store_true", help="disable RANSAC-assisted selection of repeated OCR spans")
    parser.add_argument(
        "--ransac-tolerance",
        type=float,
        default=DEFAULT_RANSAC_TOLERANCE,
        help="Story-order index residual tolerated by the timeline RANSAC model",
    )
    parser.add_argument("--disable-audio-match", action="store_true", help="Do not add decoded-audio template evidence")
    parser.add_argument("--audio-ffmpeg", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--audio-ffmpeg-filter", default=DEFAULT_AUDIO_FILTER, help=argparse.SUPPRESS)
    parser.add_argument("--audio-sample-rate", type=int, default=DEFAULT_AUDIO_SAMPLE_RATE, help=argparse.SUPPRESS)
    parser.add_argument("--audio-frame-seconds", type=float, default=DEFAULT_AUDIO_FRAME_SECONDS, help=argparse.SUPPRESS)
    parser.add_argument("--audio-search-step", type=int, default=2, help=argparse.SUPPRESS)
    parser.add_argument("--audio-prefilter-candidates", type=int, default=128, help=argparse.SUPPRESS)
    parser.add_argument("--audio-prefilter-landmarks", type=int, default=8, help=argparse.SUPPRESS)
    parser.add_argument("--audio-prefilter-neighbor-steps", type=int, default=1, help=argparse.SUPPRESS)
    parser.add_argument("--audio-second-gap", type=float, default=8.0, help=argparse.SUPPRESS)
    parser.add_argument("--audio-min-duration", type=float, default=0.8, help=argparse.SUPPRESS)
    parser.add_argument("--audio-max-duration", type=float, default=18.0, help=argparse.SUPPRESS)
    parser.add_argument("--audio-min-score", type=float, default=0.62, help=argparse.SUPPRESS)
    parser.add_argument("--audio-min-margin", type=float, default=0.08, help=argparse.SUPPRESS)
    parser.add_argument("--audio-max-matches-per-video", type=int, default=0, help=argparse.SUPPRESS)
    parser.add_argument("--audio-include-music", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--disable-locked-threshold", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--no-progress", action="store_true", help="Disable terminal progress bars")
    parser.add_argument("--apply", action="store_true", help="write proposed full story order to webui/overrides/story_order.json")
    args = parser.parse_args()
    if args.frame_step <= 0:
        parser.error("--frame-step must be greater than zero")
    if args.prefilter_max_duplicate_skip < 0:
        parser.error("--prefilter-max-duplicate-skip must be non-negative")
    if args.ransac_tolerance <= 0:
        parser.error("--ransac-tolerance must be greater than zero")
    if args.audio_sample_rate <= 0:
        parser.error("--audio-sample-rate must be greater than zero")
    if args.audio_frame_seconds <= 0:
        parser.error("--audio-frame-seconds must be greater than zero")
    if args.audio_search_step <= 0:
        parser.error("--audio-search-step must be greater than zero")
    if args.audio_prefilter_candidates < 0:
        parser.error("--audio-prefilter-candidates must be non-negative")
    if args.audio_prefilter_landmarks < 0:
        parser.error("--audio-prefilter-landmarks must be non-negative")
    if args.audio_prefilter_neighbor_steps < 0:
        parser.error("--audio-prefilter-neighbor-steps must be non-negative")
    if args.audio_second_gap < 0:
        parser.error("--audio-second-gap must be non-negative")
    if args.audio_min_duration <= 0:
        parser.error("--audio-min-duration must be greater than zero")
    if args.audio_max_duration < args.audio_min_duration:
        parser.error("--audio-max-duration must be >= --audio-min-duration")
    if not (0 <= args.audio_min_score <= 1):
        parser.error("--audio-min-score must be between 0 and 1")
    if args.audio_min_margin < 0:
        parser.error("--audio-min-margin must be non-negative")
    if args.audio_max_matches_per_video < 0:
        parser.error("--audio-max-matches-per-video must be non-negative")
    return args


def main() -> int:
    args = parse_args()
    if args.run_ocr:
        run_ocr(args)

    active_story_order, active_story_order_warning = read_active_story_order(ACTIVE_STORY_ORDER_PATH)
    if active_story_order_warning:
        print(
            f"WARNING: {active_story_order_warning}; "
            "treating active story order as empty for report generation."
        )
        if args.apply:
            raise SystemExit("refusing --apply until the active story-order JSON is valid")
    story_order = active_story_order

    print(f"Loading Story corpus from {rel_path(CONV_ROOT)}...")
    corpus = load_corpus(conv_root=CONV_ROOT, story_order=story_order, min_chars=args.min_chars)
    print(f"Loaded {len(corpus)} searchable Story text row(s).")
    map_dialog_companion_index = build_map_dialog_companion_index(corpus)
    map_dialog_companion_count = sum(len(rows) for rows in map_dialog_companion_index.values())
    print(f"Prepared {map_dialog_companion_count} archive-to-map-dialog companion matcher(s).")
    base_story_orders = story_orders_by_mission(story_order)
    related_missions_by_mission = related_corpus_missions_for_story_mission(story_order)
    mission_title_candidates = load_mission_title_candidates(MISSIONS_PATH, story_order)
    print(f"Loaded {len(mission_title_candidates)} mission title matcher(s) from {rel_path(MISSIONS_PATH)}.")
    corpus_by_mission: dict[str, list[CorpusLine]] = defaultdict(list)
    for line in corpus:
        corpus_by_mission[line.mission].append(line)
    gram_index_by_mission: dict[str, dict[str, list[int]]] = {}
    audio_match_enabled = not args.disable_audio_match
    audio_ffmpeg = resolve_audio_executable(args.audio_ffmpeg) if audio_match_enabled else None
    audio_templates_by_mission: dict[str, list[AudioStoryTemplate]] = defaultdict(list)
    audio_template_count = 0
    audio_fingerprint_cache: dict[tuple[str, int, float, str], AudioFingerprint] = {}
    if audio_match_enabled and not audio_ffmpeg:
        print("Audio template matching disabled: ffmpeg was not found on PATH.")
        audio_match_enabled = False
    if audio_match_enabled and audio_ffmpeg:
        print(
            "Loading decoded Story audio templates "
            f"(duration {args.audio_min_duration:g}-{args.audio_max_duration:g}s, "
            f"music={'included' if args.audio_include_music else 'skipped'})..."
        )
        audio_templates = load_audio_templates(
            conv_root=CONV_ROOT,
            story_order=story_order,
            min_duration=args.audio_min_duration,
            max_duration=args.audio_max_duration,
            include_music=args.audio_include_music,
        )
        for template in audio_templates:
            audio_templates_by_mission[template.mission].append(template)
        audio_template_count = len(audio_templates)
        print(
            f"Prepared {audio_template_count} audio template(s) across "
            f"{len(audio_templates_by_mission)} mission bucket(s)."
        )
    min_ocr_tool_version = 0 if args.include_stale_ocr else MIN_OCR_TOOL_VERSION
    ocr_reports, ocr_load_stats = load_ocr_reports(
        OCR_REPORT_DIR,
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
        f"Loaded {len(ocr_reports)} completed OCR report(s) from {rel_path(OCR_REPORT_DIR)} "
        f"({'including' if args.include_smoke else 'excluding'} smoke reports{stale_note})."
    )
    if ocr_reports:
        print("OCR reports to match:")
        for index, report in enumerate(ocr_reports, start=1):
            source = report.get("source") if isinstance(report.get("source"), dict) else {}
            stats = report.get("stats") if isinstance(report.get("stats"), dict) else {}
            name = safe_key(source.get("name")) or safe_key(source.get("path")) or safe_key(report.get("_reportPath"))
            print(
                f"  {index:03d}/{len(ocr_reports):03d} {name} "
                f"segments={stats.get('segments', 0)} kept={stats.get('nonEmptyFrames', 0)}"
            )

    videos: list[dict[str, Any]] = []
    all_matches_for_stats: list[dict[str, Any]] = []
    total_matches = 0
    total_accepted = 0
    total_map_dialog_companion_matches = 0
    total_audio_template_matches = 0
    video_mission_stats: Counter[str] = Counter()
    video_match_records: list[dict[str, Any]] = []
    for report in ocr_reports:
        matches: list[dict[str, Any]] = []
        source = report.get("source") if isinstance(report.get("source"), dict) else {}
        video_name = safe_key(source.get("name")) or safe_key(source.get("path")) or safe_key(report.get("_reportPath"))
        segments = [segment for segment in (report.get("segments") or []) if isinstance(segment, dict)]
        mission_match = infer_video_mission(video_name, mission_title_candidates)
        target_mission = safe_key(mission_match.get("mission"))
        target_title = safe_key(mission_match.get("title"))
        target_match_kind = safe_key(mission_match.get("match"))
        if not target_mission:
            status = safe_key(mission_match.get("status")) or "unmatched"
            video_mission_stats[f"skip_{status}"] += 1
            print(f"[{video_name}] skipped: {status} mission title match")
            videos.append({
                "video": safe_key(source.get("name")) or safe_key(source.get("path")),
                "report": report.get("_reportPath"),
                "targetMission": "",
                "targetMissionTitle": "",
                "targetMissionMatch": status,
                "missionTitleCandidates": mission_match.get("candidates") or [],
                "relatedCorpus": [],
                "relatedAudio": [],
                "acceptedMatches": 0,
                "matchedSegments": 0,
                "mapDialogCompanionMatches": 0,
                "audioTemplateMatches": 0,
                "audioMatchStats": {},
                "missions": [],
                "observedSequences": {},
                "sequenceDiagnostics": {},
                "matches": [],
            })
            continue

        video_corpus, related_corpus_rows = corpus_for_video_mission(
            target_mission,
            corpus_by_mission=corpus_by_mission,
            related_missions_by_mission=related_missions_by_mission,
        )
        if not video_corpus:
            video_mission_stats["skip_no_corpus"] += 1
            print(f"[{video_name}] skipped: inferred mission {target_mission} has no searchable corpus")
            videos.append({
                "video": safe_key(source.get("name")) or safe_key(source.get("path")),
                "report": report.get("_reportPath"),
                "targetMission": target_mission,
                "targetMissionTitle": target_title,
                "targetMissionMatch": target_match_kind,
                "missionTitleCandidates": mission_match.get("candidates") or [],
                "relatedCorpus": [],
                "relatedAudio": [],
                "acceptedMatches": 0,
                "matchedSegments": 0,
                "mapDialogCompanionMatches": 0,
                "audioTemplateMatches": 0,
                "audioMatchStats": {},
                "missions": [],
                "observedSequences": {},
                "sequenceDiagnostics": {},
                "matches": [],
            })
            continue

        video_mission_stats["matched"] += 1
        gram_index = gram_index_by_mission.get(target_mission)
        if gram_index is None:
            gram_index = build_gram_index(video_corpus)
            gram_index_by_mission[target_mission] = gram_index
        print(
            f"[{video_name}] target={target_mission}"
            f"{f' ({target_title})' if target_title else ''} "
            f"via {target_match_kind}; matching {len(segments)} OCR segment(s) "
            f"against {len(video_corpus)} row(s)"
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
        map_dialog_companion_matches = build_map_dialog_companion_matches(matches, map_dialog_companion_index)
        if map_dialog_companion_matches:
            matches.extend(map_dialog_companion_matches)
            all_matches_for_stats.extend(map_dialog_companion_matches)
            total_matches += len(map_dialog_companion_matches)
            total_accepted += len(map_dialog_companion_matches)
            total_map_dialog_companion_matches += len(map_dialog_companion_matches)

        audio_matches: list[dict[str, Any]] = []
        audio_match_stats: dict[str, Any] = {}
        related_audio_rows: list[dict[str, Any]] = []
        if audio_match_enabled and audio_ffmpeg:
            video_audio_templates, related_audio_rows = audio_templates_for_video_mission(
                target_mission,
                audio_templates_by_mission=audio_templates_by_mission,
                related_missions_by_mission=related_missions_by_mission,
            )
            video_path = resolve_video_source_path(source)
            if not video_path:
                audio_match_stats = {
                    "candidateTemplates": len(video_audio_templates),
                    "skipReason": "missing-video-file",
                }
            elif video_audio_templates:
                print(
                    f"[{video_name}] audio matching {len(video_audio_templates)} template(s) "
                    f"against {rel_path(video_path)}..."
                )
                audio_matches, audio_match_stats = build_audio_template_matches(
                    video_path=video_path,
                    templates=video_audio_templates,
                    ffmpeg=audio_ffmpeg,
                    args=args,
                    memory_cache=audio_fingerprint_cache,
                    label=video_name,
                )
                if audio_matches:
                    matches.extend(audio_matches)
                    all_matches_for_stats.extend(audio_matches)
                    total_matches += len(audio_matches)
                    total_accepted += len(audio_matches)
                    total_audio_template_matches += len(audio_matches)
            else:
                audio_match_stats = {"candidateTemplates": 0, "skipReason": "no-mission-audio-templates"}

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
                use_ransac=not args.no_ransac,
                ransac_tolerance=args.ransac_tolerance,
            )
            if len(sequence) >= args.min_sequence_keys:
                observed_sequences[mission] = sequence
                sequence_diagnostics[mission] = diagnostics

        print(
            f"[{video_name}] matched={len(matches)} accepted="
            f"{sum(1 for match in matches if match.get('accepted'))} "
            f"companions={len(map_dialog_companion_matches)} "
            f"audio={len(audio_matches)} "
            f"target={target_mission} "
            f"missions={','.join(mission for mission, _count in accepted_missions.most_common()) or '-'}"
        )
        video_summary = {
            "video": safe_key(source.get("name")) or safe_key(source.get("path")),
            "report": report.get("_reportPath"),
            "targetMission": target_mission,
            "targetMissionTitle": target_title,
            "targetMissionMatch": target_match_kind,
            "missionTitleCandidates": mission_match.get("candidates") or [],
            "relatedCorpus": related_corpus_rows,
            "relatedAudio": related_audio_rows,
            "acceptedMatches": sum(1 for match in matches if match.get("accepted")),
            "matchedSegments": len(matches),
            "mapDialogCompanionMatches": len(map_dialog_companion_matches),
            "audioTemplateMatches": len(audio_matches),
            "audioMatchStats": audio_match_stats,
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
            "audioMatches": audio_matches,
        })

    current_orders, active_order_missions = current_story_orders(active_story_order)
    locked_order_missions = story_order_locked_missions(active_story_order)
    locked_orders = {
        mission: current_orders.get(mission) or []
        for mission in locked_order_missions
        if current_orders.get(mission)
    }
    locked_threshold_sweep = build_locked_threshold_sweep(
        video_match_records,
        locked_orders=locked_orders,
        map_dialog_companion_index=map_dialog_companion_index,
        base_story_orders=base_story_orders,
        min_margin=args.min_margin,
        current_min_score=args.min_score,
        min_video_matches=args.min_video_matches,
        min_sequence_keys=args.min_sequence_keys,
        use_ransac=not args.no_ransac,
        ransac_tolerance=args.ransac_tolerance,
    )
    locked_threshold_choice = choose_locked_threshold(locked_threshold_sweep, args.min_score)
    effective_min_score = args.min_score
    if locked_threshold_sweep and not args.disable_locked_threshold:
        effective_min_score = float_value(locked_threshold_choice.get("minScore"), args.min_score)
        if abs(effective_min_score - args.min_score) > 1e-9:
            print(
                "Locked-order threshold calibration: "
                f"minScore {args.min_score:g} -> {effective_min_score:g} "
                f"(checked={locked_threshold_choice.get('checkedKeys', 0)}, "
                f"mismatches={locked_threshold_choice.get('mismatches', 0)})"
            )
    else:
        locked_threshold_choice = {
            **locked_threshold_choice,
            "disabled": bool(args.disable_locked_threshold),
        }

    all_matches_for_stats = []
    total_matches = 0
    total_accepted = 0
    total_map_dialog_companion_matches = 0
    total_audio_template_matches = 0
    for record in video_match_records:
        result = finalize_video_match_record(
            record,
            min_score=effective_min_score,
            min_margin=args.min_margin,
            map_dialog_companion_index=map_dialog_companion_index,
            base_story_orders=base_story_orders,
            min_video_matches=args.min_video_matches,
            min_sequence_keys=args.min_sequence_keys,
            use_ransac=not args.no_ransac,
            ransac_tolerance=args.ransac_tolerance,
            update_video=True,
        )
        final_matches = result.get("matches") or []
        all_matches_for_stats.extend(final_matches)
        total_matches += int(result.get("matchedSegments") or 0)
        total_accepted += int(result.get("acceptedMatches") or 0)
        total_map_dialog_companion_matches += int(result.get("mapDialogCompanionMatches") or 0)
        total_audio_template_matches += int(result.get("audioTemplateMatches") or 0)

    locked_validation = validate_locked_order_sequences(videos, locked_orders=locked_orders)
    proposed, proposal_rows = build_proposed_story_order(
        active_story_order=active_story_order,
        story_order=story_order,
        video_summaries=videos,
        min_sequence_keys=args.min_sequence_keys,
    )
    skipped_locked_mission_count = sum(1 for row in proposal_rows if row.get("skipReason") == "locked")
    changed_mission_count = sum(1 for row in proposal_rows if row.get("changed"))
    inserted_key_count = sum(len(row.get("insertedKeys") or []) for row in proposal_rows)
    changed_key_count = sum(len(row.get("changedKeys") or []) for row in proposal_rows)
    sequence_diagnostics = [
        diagnostics
        for video in videos
        for diagnostics in (video.get("sequenceDiagnostics") or {}).values()
        if isinstance(diagnostics, dict)
    ]
    print(
        "OCR story-order update: "
        f"activeMissions={len(active_order_missions)}, "
        f"lockedMissions={len(locked_order_missions)}, "
        f"skippedLockedMissions={skipped_locked_mission_count}, "
        f"seededMissions={len(current_orders)}, "
        f"changedMissions={changed_mission_count}, "
        f"changedKeys={changed_key_count}, "
        f"insertedKeys={inserted_key_count}, "
        f"mapDialogCompanions={total_map_dialog_companion_matches}, "
        f"audioTemplateMatches={total_audio_template_matches}"
    )
    write_report_json(PROPOSED_STORY_ORDER_PATH, proposed)

    if args.apply:
        write_report_json(ACTIVE_STORY_ORDER_PATH, proposed)

    payload = {
        "schema": "gameplayVideoStoryOrderMatch.v2",
        "summary": {
            "corpusLines": len(corpus),
            "audioTemplates": audio_template_count,
            "ocrReportsUsed": len(ocr_reports),
            "matchedSegments": total_matches,
            "acceptedMatches": total_accepted,
            "mapDialogCompanionMatches": total_map_dialog_companion_matches,
            "audioTemplateMatches": total_audio_template_matches,
            "indexedInferences": sum(len(row.get("indexedInferences") or []) for row in proposal_rows),
            "linkedEntries": sum(len(row.get("linkedEntries") or []) for row in proposal_rows),
            "ransacModels": sum(1 for row in sequence_diagnostics if row.get("ransacModel")),
            "ransacAdjustedKeys": sum(int(row.get("adjustedRepeatedKeys") or 0) for row in sequence_diagnostics),
            "ignoredRepeatedSpans": sum(int(row.get("ignoredRepeatedSpans") or 0) for row in sequence_diagnostics),
            "orderUpdateMode": "full-list-observed-block",
            "activeOrderMissions": len(active_order_missions),
            "lockedOrderMissions": len(locked_order_missions),
            "skippedLockedOrderMissions": skipped_locked_mission_count,
            "seededOrderMissions": len(current_orders),
            "changedOrderMissions": changed_mission_count,
            "changedOrderKeys": changed_key_count,
            "insertedOrderKeys": inserted_key_count,
            "videoMissionMatches": dict(sorted(video_mission_stats.items())),
            "lockedValidation": locked_validation.get("summary") or {},
            "lockedThresholdChoice": locked_threshold_choice,
            "activeOrderWarning": active_story_order_warning,
            "applied": bool(args.apply),
        },
        "thresholds": {
            "minChars": args.min_chars,
            "minScore": args.min_score,
            "effectiveMinScore": effective_min_score,
            "minMargin": args.min_margin,
            "minVideoMatches": args.min_video_matches,
            "minSequenceKeys": args.min_sequence_keys,
            "ransacTolerance": None if args.no_ransac else args.ransac_tolerance,
            "audioMatch": None if not audio_match_enabled else {
                "sampleRate": args.audio_sample_rate,
                "frameSeconds": args.audio_frame_seconds,
                "ffmpegFilter": args.audio_ffmpeg_filter,
                "searchStep": args.audio_search_step,
                "prefilterCandidates": args.audio_prefilter_candidates,
                "prefilterLandmarks": args.audio_prefilter_landmarks,
                "prefilterNeighborSteps": args.audio_prefilter_neighbor_steps,
                "secondGapSeconds": args.audio_second_gap,
                "minDuration": args.audio_min_duration,
                "maxDuration": args.audio_max_duration,
                "minScore": args.audio_min_score,
                "minMargin": args.audio_min_margin,
                "includeMusic": bool(args.audio_include_music),
            },
        },
        "outputs": {
            "proposedStoryOrder": rel_path(PROPOSED_STORY_ORDER_PATH),
            "activeStoryOrder": rel_path(ACTIVE_STORY_ORDER_PATH) if args.apply else "",
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
    write_report_json(MATCH_REPORT_PATH, payload)
    write_match_markdown(payload)

    print(f"Matched {total_accepted}/{total_matches} OCR/audio segment(s) from {len(ocr_reports)} OCR report(s).")
    print(f"Wrote {rel_path(MATCH_REPORT_PATH)}")
    print(f"Review matching summary at {rel_path(MATCH_MD_PATH)}")
    print(f"Wrote {rel_path(PROPOSED_STORY_ORDER_PATH)}")
    if args.apply:
        print(f"Applied to {rel_path(ACTIVE_STORY_ORDER_PATH)}")
    locked_rows = locked_validation.get("missions") or []
    if locked_rows:
        print("Locked-order mismatch validation:")
        for row in locked_rows:
            print(
                f"  {row['mission']}: mismatches={row.get('mismatches', 0)}, "
                f"inversions={row.get('inversions', 0)}, "
                f"checked={row.get('checkedKeys', 0)}, "
                f"missing={row.get('missingKeys', 0)}"
            )
    else:
        print("Locked-order mismatch validation: no locked mission evidence in matched videos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
