#!/usr/bin/env python3
"""Match gameplay-video OCR text to Story entries and update story order lists.

This is a conservative promotion pipeline:

1. Optionally run the OCR sampler.
2. Match completed OCR segments against known WebUI Story text.
3. Collapse timestamped matches into observed per-mission scene sequences.
4. Apply those sequences to the full per-mission story-order list format.

The active order file is ``webui/overrides/story_order.json``. Each
``missions.<mission>.order`` value is a complete ordered list of the mission's
Story file keys. The OCR pass seeds from that active file when available, falls
back to ``webui/data/assets/story_order.json``, and moves observed keys into
the observed order while preserving unobserved mission files in their current
relative order.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
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
STORY_ORDER_PATH = ROOT / "webui" / "data" / "assets" / "story_order.json"
ACTIVE_STORY_ORDER_PATH = ROOT / "webui" / "overrides" / "story_order.json"
MISSIONS_PATH = ROOT / "webui" / "data" / "lang" / "CN" / "missions.json"
OCR_REPORT_DIR = REPORTS_DIR / "gameplay_video_ocr"
MATCH_REPORT_PATH = OCR_REPORT_DIR / "story_order_ocr_matches.json"
MATCH_MD_PATH = OCR_REPORT_DIR / "story_order_ocr_matches.md"
PROPOSED_STORY_ORDER_PATH = OCR_REPORT_DIR / "story_order_ocr_proposed_story_order.json"
OCR_SCRIPT_PATH = ROOT / "scripts" / "story_recovery" / "build_gameplay_video_ocr_audit.py"
MIN_OCR_TOOL_VERSION = 5
DEFAULT_THRESHOLD_SWEEP = (0.98, 0.95, 0.90, 0.86, 0.80, 0.75, 0.70, 0.65, 0.60, 0.50)
LINE_LIKE_SOURCES = {"line", "summary"}
DEFAULT_RANSAC_TOLERANCE = 3.5
ARCHIVE_KINDS = {"prts"}
ARCHIVE_KEY_PREFIXES = ("nar_",)

BR_TAG_RE = re.compile(r"<\s*br\s*/?\s*>", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")
ASCII_WORD_RE = re.compile(r"^[a-z0-9_:\-.]+$")
STORY_KIND_RE = re.compile(r"^(?:misc_)?([a-z]+)")
INDEXED_SUFFIX_RE = re.compile(r"^(\d+)(?:d(\d+))?(?:_(\d+))?$")
NATURAL_SORT_RE = re.compile(r"\d+|\D+")


@dataclass(frozen=True)
class CorpusLine:
    key: str
    mission: str
    actual_mission: str
    link_reason: str
    kind: str
    line_id: str
    source: str
    text: str
    norm: str


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
        mission = safe_key(payload.get("mission"))
        if not mission:
            for mission_id, order in story_orders.items():
                if key in order:
                    mission = mission_id
                    break
        if not mission:
            continue
        kind = story_kind(key, payload)
        for line_id, source, text in iter_text_rows(payload):
            norm = normalize_text(text)
            if not useful_norm(norm, min_chars=min_chars):
                continue
            out.append(CorpusLine(
                key=key,
                mission=mission,
                actual_mission=mission,
                link_reason="native",
                kind=kind,
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


def float_value(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def source_quality(source: Any) -> int:
    source_key = safe_key(source)
    if source_key in LINE_LIKE_SOURCES:
        return 2
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
        if int(span.get("lineLikeMatches") or 0) <= 0 and int(span.get("matchCount") or 0) < 2:
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
    """Read the full-list story-order format, plus generated order payloads."""
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


def merge_stored_order_with_base(stored_order: list[str], base_order: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for key in stored_order:
        if key and key not in seen:
            out.append(key)
            seen.add(key)
    for key in base_order:
        if key and key not in seen:
            out.append(key)
            seen.add(key)
    return out


def current_story_orders(
    story_order: dict[str, Any],
    active_story_order: dict[str, Any],
) -> tuple[dict[str, list[str]], set[str]]:
    base_orders = story_orders_by_mission(story_order)
    stored_orders = story_orders_by_mission(active_story_order)
    locked_missions = story_order_locked_missions(active_story_order)
    out: dict[str, list[str]] = {}

    for mission, base_order in base_orders.items():
        stored_order = stored_orders.get(mission)
        if mission in locked_missions and stored_order is not None:
            out[mission] = list(stored_order)
        else:
            out[mission] = merge_stored_order_with_base(stored_order or [], base_order)
    for mission, stored_order in stored_orders.items():
        if mission not in out:
            if mission in locked_missions:
                out[mission] = list(stored_order)
            else:
                out[mission] = merge_stored_order_with_base(stored_order, [])
    return out, set(stored_orders)


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
            "order across builder and OCR writes; the WebUI can toggle it per mission."
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
    next_orders, active_missions = current_story_orders(story_order, active_story_order)
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
        "# Gameplay Video OCR Story-Order Matching",
        "",
        f"- OCR reports used: `{payload['summary']['ocrReportsUsed']}`",
        f"- Corpus lines: `{payload['summary']['corpusLines']}`",
        f"- Accepted segment matches: `{payload['summary']['acceptedMatches']}`",
        f"- Indexed gap inferences: `{payload['summary'].get('indexedInferences', 0)}`",
        f"- Linked map-dialog entries: `{payload['summary'].get('linkedEntries', 0)}`",
        f"- RANSAC models: `{payload['summary'].get('ransacModels', 0)}`",
        f"- RANSAC adjusted repeated keys: `{payload['summary'].get('ransacAdjustedKeys', 0)}`",
        f"- Ignored repeated spans: `{payload['summary'].get('ignoredRepeatedSpans', 0)}`",
        f"- Video mission title matches: `{payload['summary'].get('videoMissionMatches', {})}`",
        f"- Proposed story order: `{payload['outputs']['proposedStoryOrder']}`",
        "",
    ]
    if payload["summary"].get("activeOrderWarning"):
        lines.extend([
            f"> Warning: {md_escape(payload['summary']['activeOrderWarning'])}",
            "",
        ])
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
            "| video | target mission | report | accepted | matched missions | observed sequences |",
            "|---|---|---|---:|---|---:|",
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
    parser.add_argument("--no-progress", action="store_true", help="Disable terminal progress bars")
    parser.add_argument("--apply", action="store_true", help="write proposed full story order to webui/overrides/story_order.json")
    args = parser.parse_args()
    if args.frame_step <= 0:
        parser.error("--frame-step must be greater than zero")
    if args.prefilter_max_duplicate_skip < 0:
        parser.error("--prefilter-max-duplicate-skip must be non-negative")
    if args.ransac_tolerance <= 0:
        parser.error("--ransac-tolerance must be greater than zero")
    return args


def main() -> int:
    args = parse_args()
    if args.run_ocr:
        run_ocr(args)

    story_order = read_json(STORY_ORDER_PATH, {})
    active_story_order, active_story_order_warning = read_active_story_order(ACTIVE_STORY_ORDER_PATH)
    if not isinstance(story_order, dict):
        raise SystemExit(f"missing or invalid {STORY_ORDER_PATH}")
    if active_story_order_warning:
        print(
            f"WARNING: {active_story_order_warning}; "
            "treating active story order as empty for report generation."
        )
        if args.apply:
            raise SystemExit("refusing --apply until the active story-order JSON is valid")

    print(f"Loading Story corpus from {rel_path(CONV_ROOT)}...")
    corpus = load_corpus(conv_root=CONV_ROOT, story_order=story_order, min_chars=args.min_chars)
    print(f"Loaded {len(corpus)} searchable Story text row(s).")
    base_story_orders = story_orders_by_mission(story_order)
    related_missions_by_mission = related_corpus_missions_for_story_mission(story_order)
    mission_title_candidates = load_mission_title_candidates(MISSIONS_PATH, story_order)
    print(f"Loaded {len(mission_title_candidates)} mission title matcher(s) from {rel_path(MISSIONS_PATH)}.")
    corpus_by_mission: dict[str, list[CorpusLine]] = defaultdict(list)
    for line in corpus:
        corpus_by_mission[line.mission].append(line)
    gram_index_by_mission: dict[str, dict[str, list[int]]] = {}
    min_ocr_tool_version = 0 if args.include_stale_ocr else MIN_OCR_TOOL_VERSION
    ocr_reports, ocr_load_stats = load_ocr_reports(
        OCR_REPORT_DIR,
        include_smoke=args.include_smoke,
        min_tool_version=min_ocr_tool_version,
    )
    if ocr_load_stats:
        print(
            "OCR report scan: "
            + ", ".join(f"{key}={value}" for key, value in sorted(ocr_load_stats.items()))
        )
    print(
        f"Loaded {len(ocr_reports)} completed OCR report(s) from {rel_path(OCR_REPORT_DIR)} "
        f"({'including' if args.include_smoke else 'excluding'} smoke reports"
        f"{', including stale OCR' if args.include_stale_ocr else f', toolVersion >= {MIN_OCR_TOOL_VERSION} only'})."
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
    video_mission_stats: Counter[str] = Counter()
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
                "acceptedMatches": 0,
                "matchedSegments": 0,
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
                "acceptedMatches": 0,
                "matchedSegments": 0,
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
            f"target={target_mission} "
            f"missions={','.join(mission for mission, _count in accepted_missions.most_common()) or '-'}"
        )
        videos.append({
            "video": safe_key(source.get("name")) or safe_key(source.get("path")),
            "report": report.get("_reportPath"),
            "targetMission": target_mission,
            "targetMissionTitle": target_title,
            "targetMissionMatch": target_match_kind,
            "missionTitleCandidates": mission_match.get("candidates") or [],
            "relatedCorpus": related_corpus_rows,
            "acceptedMatches": sum(1 for match in matches if match.get("accepted")),
            "matchedSegments": len(matches),
            "missions": [mission for mission, _count in accepted_missions.most_common()],
            "observedSequences": observed_sequences,
            "sequenceDiagnostics": sequence_diagnostics,
            "matches": matches[:200],
        })

    proposed, proposal_rows = build_proposed_story_order(
        active_story_order=active_story_order,
        story_order=story_order,
        video_summaries=videos,
        min_sequence_keys=args.min_sequence_keys,
    )
    current_orders, active_order_missions = current_story_orders(story_order, active_story_order)
    locked_order_missions = story_order_locked_missions(active_story_order)
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
        f"insertedKeys={inserted_key_count}"
    )
    write_report_json(PROPOSED_STORY_ORDER_PATH, proposed)

    if args.apply:
        write_report_json(ACTIVE_STORY_ORDER_PATH, proposed)

    payload = {
        "schema": "gameplayVideoStoryOrderMatch.v1",
        "summary": {
            "corpusLines": len(corpus),
            "ocrReportsUsed": len(ocr_reports),
            "matchedSegments": total_matches,
            "acceptedMatches": total_accepted,
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
            "activeOrderWarning": active_story_order_warning,
            "applied": bool(args.apply),
        },
        "thresholds": {
            "minChars": args.min_chars,
            "minScore": args.min_score,
            "minMargin": args.min_margin,
            "minVideoMatches": args.min_video_matches,
            "minSequenceKeys": args.min_sequence_keys,
            "ransacTolerance": None if args.no_ransac else args.ransac_tolerance,
        },
        "outputs": {
            "proposedStoryOrder": rel_path(PROPOSED_STORY_ORDER_PATH),
            "activeStoryOrder": rel_path(ACTIVE_STORY_ORDER_PATH) if args.apply else "",
        },
        "thresholdSweep": build_threshold_sweep(
            all_matches_for_stats,
            min_margin=args.min_margin,
            current_min_score=args.min_score,
        ),
        "scoreHistogram": build_score_histogram(all_matches_for_stats),
        "proposals": proposal_rows,
        "videos": videos,
    }
    write_report_json(MATCH_REPORT_PATH, payload)
    write_match_markdown(payload)

    print(f"Matched {total_accepted}/{total_matches} segment(s) from {len(ocr_reports)} OCR report(s).")
    print(f"Wrote {rel_path(MATCH_REPORT_PATH)}")
    print(f"Review matching summary at {rel_path(MATCH_MD_PATH)}")
    print(f"Wrote {rel_path(PROPOSED_STORY_ORDER_PATH)}")
    if args.apply:
        print(f"Applied to {rel_path(ACTIVE_STORY_ORDER_PATH)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
