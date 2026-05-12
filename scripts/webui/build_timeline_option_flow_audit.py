#!/usr/bin/env python3
"""Audit unresolved option responses against raw Timeline clip layout.

This follows `build_dialog_tree_option_route_audit.py`: most remaining
`inferredOptionResponse` groups are cinematic DialogTree wrappers that launch a
`dlgtl_*` Timeline. The question here is whether the Timeline clips themselves
carry route hints, especially raw trunk-clip `optionIndex` values that are not
currently surfaced in `timeline_line_orders.json`.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import build_option_playable_semantics_audit as semantics


ROOT = Path(__file__).resolve().parents[2]
EPSILON = 0.001


def read_json(path: Path, default: Any = None) -> Any:
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            return json.load(handle)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return default


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def safe_key(value: Any) -> str:
    return str(value if value is not None else "").strip()


def as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("-") and text[1:].isdigit():
            return int(text)
        if text.isdigit():
            return int(text)
    return None


def md_escape(value: Any) -> str:
    return safe_key(value).replace("|", "\\|").replace("\n", " ")


def path_from_export(value: Any) -> Path:
    text = safe_key(value)
    if not text:
        return Path()
    path = Path(text)
    if path.is_absolute():
        return path
    return ROOT / path


class TrackCache:
    def __init__(self) -> None:
        self._cache: dict[str, dict[str, Any]] = {}

    def load(self, path_value: Any) -> dict[str, Any]:
        path = path_from_export(path_value)
        key = str(path)
        if key not in self._cache:
            payload = read_json(path, {})
            self._cache[key] = payload if isinstance(payload, dict) else {}
        return self._cache[key]


def approx_equal(left: Any, right: Any) -> bool:
    left_float = as_float(left)
    right_float = as_float(right)
    if left_float is None or right_float is None:
        return False
    return abs(left_float - right_float) <= EPSILON


def raw_clip_for_line(line: dict[str, Any], track_cache: TrackCache) -> dict[str, Any]:
    track = track_cache.load(line.get("track"))
    asset_path_id = line.get("assetPathId")
    matches: list[dict[str, Any]] = []
    for clip in track.get("m_Clips") or []:
        if not isinstance(clip, dict):
            continue
        clip_asset = clip.get("m_Asset") if isinstance(clip.get("m_Asset"), dict) else {}
        if clip_asset.get("m_PathID") != asset_path_id:
            continue
        if line.get("start") is not None and not approx_equal(clip.get("m_Start"), line.get("start")):
            continue
        matches.append({
            "start": clip.get("m_Start"),
            "duration": clip.get("m_Duration"),
            "optionIndex": clip.get("optionIndex"),
            "displayName": safe_key(clip.get("m_DisplayName")),
        })
    if not matches:
        return {}
    matches.sort(key=lambda item: (as_float(item.get("start")) or 0.0, as_float(item.get("duration")) or 0.0))
    return {key: value for key, value in matches[0].items() if value not in (None, "", [], {})}


def line_detail(
    line_id: str,
    line_map: dict[str, dict[str, Any]],
    line_positions: dict[str, int],
    track_cache: TrackCache,
) -> dict[str, Any]:
    line = line_map.get(line_id) or {}
    out: dict[str, Any] = {
        "id": line_id,
        "position": line_positions.get(line_id),
        "start": line.get("start"),
        "duration": line.get("duration"),
        "trackName": line.get("trackName"),
        "trackPathId": line.get("trackPathId"),
        "assetPathId": line.get("assetPathId"),
        "assetTrack": line.get("assetTrack"),
    }
    raw_clip = raw_clip_for_line(line, track_cache) if line else {}
    if raw_clip:
        out["rawClip"] = raw_clip
    return {key: value for key, value in out.items() if value not in (None, "", [], {})}


def timeline_window(
    line_order: list[str],
    *,
    after: str,
    candidates: list[str],
    common: str,
) -> list[str]:
    if not line_order:
        return []
    start_index = line_order.index(after) + 1 if after in line_order else 0
    end_index = len(line_order)
    end_markers = [line_id for line_id in [common, *candidates] if line_id in line_order]
    if end_markers:
        end_index = max(line_order.index(line_id) for line_id in end_markers) + 1
        if common in line_order:
            end_index = max(end_index, line_order.index(common) + 1)
    return line_order[start_index:end_index]


def option_values(option: dict[str, Any]) -> set[int]:
    values: set[int] = set()
    best = option.get("bestRow") or {}
    for field in ("optionIndex", "clipOptionIndex", "index", "logicId"):
        value = as_int(best.get(field))
        if value is not None:
            values.add(value)
    return values


def classify_group(row: dict[str, Any], candidate_details: list[dict[str, Any]], window_ids: list[str]) -> tuple[str, str]:
    raw_values = [
        as_int((detail.get("rawClip") or {}).get("optionIndex"))
        for detail in candidate_details
        if detail.get("rawClip")
    ]
    raw_values = [value for value in raw_values if value is not None]
    option_value_sets = [option_values(option) for option in row.get("options") or []]
    option_indices = [
        as_int((option.get("bestRow") or {}).get("optionIndex"))
        for option in row.get("options") or []
    ]
    candidate_ids = [safe_key(detail.get("id")) for detail in candidate_details]
    all_candidate_raw_matches = bool(raw_values) and len(raw_values) == len(option_value_sets) and all(
        raw_value in option_values
        for raw_value, option_values in zip(raw_values, option_value_sets)
    )
    all_candidate_raw_maps = (
        bool(raw_values)
        and len(raw_values) == len(option_indices)
        and all(value is not None for value in option_indices)
        and len(set(raw_values)) == len(raw_values)
        and set(raw_values) == set(option_indices)
    )
    nonzero_raw_values = [value for value in raw_values if value != 0]
    candidate_contiguous = bool(candidate_ids) and candidate_ids == [
        line_id for line_id in window_ids if line_id in set(candidate_ids)
    ]
    candidates_are_window_start = bool(candidate_ids) and window_ids[: len(candidate_ids)] == candidate_ids
    tracks = {safe_key(detail.get("trackPathId")) for detail in candidate_details if safe_key(detail.get("trackPathId"))}

    if all_candidate_raw_matches and len(set(raw_values)) > 1 and nonzero_raw_values:
        return "trunkClipOptionIndexRoute", "promoteRawTrunkClipOptionIndex"
    if all_candidate_raw_maps and nonzero_raw_values:
        return "trunkClipOptionIndexMapping", "promoteRawTrunkClipOptionIndexMapping"
    if raw_values and not nonzero_raw_values:
        if candidates_are_window_start:
            return "rawTrunkClipOptionIndexDefaultAdjacent", "doNotPromoteWithoutRuntimeRule"
        return "rawTrunkClipOptionIndexDefault", "needsRuntimeMethodBody"
    if len(tracks) > 1:
        return "multiTrackCandidateLayout", "inspectPlayableDirectorTrackBinding"
    if candidate_contiguous:
        return "linearCandidateWindow", "adjacencyOnly"
    return "timelineLayoutUnresolved", "needsRuntimeMethodBody"


def collect_rows(
    language: str,
    conv_dir: Path,
    timeline_orders_path: Path,
    *,
    story_filters: list[str] | None = None,
    group_filters: set[int] | None = None,
    only_interesting: bool = False,
) -> list[dict[str, Any]]:
    timeline_orders = read_json(timeline_orders_path, {}) or {}
    semantics_rows = semantics.collect_rows(
        language,
        conv_dir,
        timeline_orders_path,
        story_filters=story_filters,
        group_filters=group_filters,
        only_interesting=only_interesting,
    )
    track_cache = TrackCache()
    out: list[dict[str, Any]] = []
    for row in semantics_rows:
        story_key = safe_key(row.get("storyKey"))
        option_ids = [safe_key(option.get("optionId")) for option in row.get("options") or []]
        line_ids = [
            safe_key(value)
            for value in [
                row.get("after"),
                row.get("commonContinuationLineId"),
                *(row.get("candidateLineIds") or []),
            ]
            if safe_key(value)
        ]
        entry = semantics.timeline_entry_for_story(
            timeline_orders,
            story_key,
            option_ids=option_ids,
            line_ids=line_ids,
        )
        line_order = [safe_key(line_id) for line_id in entry.get("lineIds") or [] if safe_key(line_id)]
        line_map = {
            safe_key(line.get("id")): line
            for line in entry.get("lines") or []
            if isinstance(line, dict) and safe_key(line.get("id"))
        }
        line_positions = {line_id: index for index, line_id in enumerate(line_order)}
        candidate_ids = [safe_key(value) for value in row.get("candidateLineIds") or [] if safe_key(value)]
        common_id = safe_key(row.get("commonContinuationLineId"))
        after_id = safe_key(row.get("after"))
        candidate_details = [
            line_detail(line_id, line_map, line_positions, track_cache)
            for line_id in candidate_ids
        ]
        window_ids = timeline_window(line_order, after=after_id, candidates=candidate_ids, common=common_id)
        window_details = [
            line_detail(line_id, line_map, line_positions, track_cache)
            for line_id in window_ids
        ]
        classification, recommendation = classify_group(row, candidate_details, window_ids)
        option_rows: list[dict[str, Any]] = []
        for option in row.get("options") or []:
            best = option.get("bestRow") or {}
            option_rows.append({
                "optionId": option.get("optionId"),
                "candidateLineId": option.get("candidateLineId"),
                "optionIndex": best.get("optionIndex"),
                "clipOptionIndex": best.get("clipOptionIndex"),
                "index": best.get("index"),
                "logicId": best.get("logicId"),
                "start": best.get("start"),
                "duration": best.get("duration"),
                "trackName": best.get("trackName"),
                "trackPathId": best.get("trackPathId"),
                "anchorMode": best.get("anchorMode"),
                "anchorLineId": best.get("anchorLineId"),
                "assetTrack": best.get("assetTrack"),
            })
        out.append({
            "language": language,
            "storyKey": story_key,
            "mission": row.get("mission"),
            "group": row.get("group"),
            "timeline": entry.get("timeline") or row.get("timeline") or "",
            "after": after_id,
            "candidateLineIds": candidate_ids,
            "commonContinuationLineId": common_id,
            "classification": classification,
            "recommendation": recommendation,
            "semanticsClassification": row.get("classification"),
            "semanticsRecommendation": row.get("recommendation"),
            "options": option_rows,
            "candidateLines": candidate_details,
            "windowLineIds": window_ids,
            "windowLines": window_details,
        })
    out.sort(key=lambda item: (item.get("mission") or "", item.get("storyKey") or "", item.get("group") or 0))
    return out


def summarize_rows(
    language: str,
    rows: list[dict[str, Any]],
    *,
    story_filters: list[str] | None = None,
    group_filters: set[int] | None = None,
    only_interesting: bool = False,
) -> dict[str, Any]:
    classifications = Counter(row.get("classification") or "" for row in rows)
    recommendations = Counter(row.get("recommendation") or "" for row in rows)
    raw_option_index_values: Counter[str] = Counter()
    groups_with_nonzero_candidate_raw = 0
    for row in rows:
        has_nonzero = False
        for detail in row.get("candidateLines") or []:
            raw_value = as_int((detail.get("rawClip") or {}).get("optionIndex"))
            if raw_value is None:
                continue
            raw_option_index_values[str(raw_value)] += 1
            if raw_value:
                has_nonzero = True
        if has_nonzero:
            groups_with_nonzero_candidate_raw += 1
    return {
        "language": language,
        "filters": {
            "stories": story_filters or [],
            "groups": sorted(group_filters or set()),
            "onlyInteresting": bool(only_interesting),
        },
        "inferredResponseGroupCount": len(rows),
        "classificationCounts": dict(classifications),
        "recommendationCounts": dict(recommendations),
        "candidateRawClipOptionIndexCounts": dict(sorted(raw_option_index_values.items())),
        "groupsWithNonzeroCandidateRawClipOptionIndex": groups_with_nonzero_candidate_raw,
    }


def option_summary(row: dict[str, Any]) -> str:
    parts: list[str] = []
    for option, candidate in zip(row.get("options") or [], row.get("candidateLines") or []):
        raw_clip = candidate.get("rawClip") or {}
        fields = [
            f"optIdx={option.get('optionIndex')}",
            f"clipIdx={option.get('clipOptionIndex')}",
            f"rawLineIdx={raw_clip.get('optionIndex')}",
        ]
        if option.get("logicId") not in (None, "", 0):
            fields.append(f"logicId={option.get('logicId')}")
        parts.append(f"{option.get('optionId')} -> {candidate.get('id')} ({', '.join(fields)})")
    return "; ".join(parts)


def render_markdown(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = [
        f"# Timeline Option Flow Audit - {summary['language']}",
        "",
        f"- Inferred response groups audited: `{summary['inferredResponseGroupCount']}`",
        f"- Groups with nonzero candidate trunk raw `optionIndex`: `{summary['groupsWithNonzeroCandidateRawClipOptionIndex']}`",
        f"- Candidate trunk raw `optionIndex` counts: `{summary['candidateRawClipOptionIndexCounts']}`",
        "",
        "## Classification Counts",
        "",
    ]
    for key, count in summary.get("classificationCounts", {}).items():
        lines.append(f"- `{key}`: {count}")
    lines.extend(["", "## Recommendation Counts", ""])
    for key, count in summary.get("recommendationCounts", {}).items():
        lines.append(f"- `{key}`: {count}")
    lines.extend([
        "",
        "## Groups",
        "",
        "| Scene | Group | After | Candidates | Common | Class | Recommendation | Clip evidence |",
        "| --- | ---: | --- | --- | --- | --- | --- | --- |",
    ])
    for row in rows:
        lines.append(
            "| "
            f"`{md_escape(row.get('storyKey'))}` "
            f"| {md_escape(row.get('group'))} "
            f"| `{md_escape(row.get('after'))}` "
            f"| `{md_escape(', '.join(row.get('candidateLineIds') or []))}` "
            f"| `{md_escape(row.get('commonContinuationLineId'))}` "
            f"| `{md_escape(row.get('classification'))}` "
            f"| `{md_escape(row.get('recommendation'))}` "
            f"| {md_escape(option_summary(row))} |"
        )
    if not rows:
        lines.append("| _(none)_ |  |  |  |  |  |  |  |")
    return "\n".join(lines)


def build_report(
    language: str,
    conv_dir: Path,
    timeline_orders_path: Path,
    reports_dir: Path,
    *,
    story_filters: list[str] | None = None,
    group_filters: set[int] | None = None,
    only_interesting: bool = False,
) -> dict[str, Any]:
    rows = collect_rows(
        language,
        conv_dir,
        timeline_orders_path,
        story_filters=story_filters,
        group_filters=group_filters,
        only_interesting=only_interesting,
    )
    summary = summarize_rows(
        language,
        rows,
        story_filters=story_filters,
        group_filters=group_filters,
        only_interesting=only_interesting,
    )
    payload = {
        "summary": summary,
        "groups": rows,
    }
    reports_dir.mkdir(parents=True, exist_ok=True)
    suffix = semantics.safe_report_suffix(story_filters or [], group_filters or set(), only_interesting)
    out_json = reports_dir / f"timeline_option_flow_audit_{language}{suffix}.json"
    out_md = reports_dir / f"timeline_option_flow_audit_{language}{suffix}.md"
    write_json(out_json, payload)
    out_md.write_text(render_markdown(summary, rows) + "\n", encoding="utf-8")
    return {"summary": summary, "json": out_json, "markdown": out_md}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", default="CN")
    parser.add_argument("--conv-dir", type=Path)
    parser.add_argument(
        "--timeline-orders",
        type=Path,
        default=ROOT / "export_full" / "recovered" / "AnimeStudio-cli" / "timeline_line_orders.json",
    )
    parser.add_argument("--reports-dir", type=Path, default=ROOT / "reports")
    parser.add_argument("--story", action="append", help="Story key, substring, glob, or comma-list to audit.")
    parser.add_argument("--group", action="append", help="Option group number or comma-list to audit.")
    parser.add_argument(
        "--only-interesting",
        action="store_true",
        help="Reuse the playable-semantics audit's high-signal subset.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    language = args.language
    conv_dir = args.conv_dir or ROOT / "webui" / "data" / "lang" / language / "conv"
    story_filters = semantics.split_csv_values(args.story)
    try:
        group_filters = semantics.parse_group_filters(args.group)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    result = build_report(
        language,
        conv_dir,
        args.timeline_orders,
        args.reports_dir,
        story_filters=story_filters,
        group_filters=group_filters,
        only_interesting=args.only_interesting,
    )
    summary = result["summary"]
    print(f"Timeline option flow audit: {result['markdown']}")
    print(f"Timeline option flow data:  {result['json']}")
    print(
        "Audited "
        f"{summary['inferredResponseGroupCount']} inferred response groups; "
        f"{summary['groupsWithNonzeroCandidateRawClipOptionIndex']} groups have nonzero candidate trunk raw optionIndex."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
