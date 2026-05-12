#!/usr/bin/env python3
"""Audit unresolved option responses against Timeline track/binding layout.

The option-flow audit checks raw clip fields. This one asks a different
question: do remaining inferred option responses separate cleanly by Timeline
track, track binding, actor binding, or option-clip placement?
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import build_option_playable_semantics_audit as semantics


ROOT = Path(__file__).resolve().parents[2]


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


def as_int(value: Any) -> int | None:
    return semantics.as_int(value)


def as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def md_escape(value: Any) -> str:
    return safe_key(value).replace("|", "\\|").replace("\n", " ")


def unique_preserve(values: list[Any]) -> list[Any]:
    out: list[Any] = []
    seen: set[Any] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def compact_float(value: Any) -> float | None:
    numeric = as_float(value)
    return round(numeric, 3) if numeric is not None else None


def compact_timeline_line(line_id: str, line: dict[str, Any] | None, position: int | None) -> dict[str, Any]:
    line = line or {}
    out = {
        "id": line_id,
        "position": position,
        "start": compact_float(line.get("start")),
        "duration": compact_float(line.get("duration")),
        "trackName": safe_key(line.get("trackName")),
        "trackPathId": line.get("trackPathId"),
        "track": safe_key(line.get("track")),
        "binding": safe_key(line.get("binding")),
        "actor": safe_key(line.get("actor")),
        "assetName": safe_key(line.get("assetName")),
        "assetPathId": line.get("assetPathId"),
        "assetTrack": safe_key(line.get("assetTrack")),
        "clipOptionIndex": line.get("clipOptionIndex"),
        "sourceFile": safe_key(line.get("sourceFile")),
    }
    return {key: value for key, value in out.items() if value not in (None, "", [], {})}


def compact_option_row(row: dict[str, Any]) -> dict[str, Any]:
    out = {
        "id": safe_key(row.get("id")),
        "start": compact_float(row.get("start")),
        "duration": compact_float(row.get("duration")),
        "groupKey": safe_key(row.get("groupKey")),
        "index": row.get("index"),
        "optionIndex": row.get("optionIndex"),
        "clipOptionIndex": row.get("clipOptionIndex"),
        "logicId": row.get("logicId"),
        "anchorMode": safe_key(row.get("anchorMode")),
        "anchorLineId": safe_key(row.get("anchorLineId")),
        "trackName": safe_key(row.get("trackName")),
        "trackPathId": row.get("trackPathId"),
        "track": safe_key(row.get("track")),
        "assetName": safe_key(row.get("assetName")),
        "assetPathId": row.get("assetPathId"),
        "assetTrack": safe_key(row.get("assetTrack")),
        "sourceFile": safe_key(row.get("sourceFile")),
    }
    return {key: value for key, value in out.items() if value not in (None, "", [], {})}


def track_key(row: dict[str, Any]) -> str:
    path_id = row.get("trackPathId")
    if path_id not in (None, ""):
        return f"path:{path_id}"
    track = safe_key(row.get("track"))
    if track:
        return f"file:{track}"
    name = safe_key(row.get("trackName"))
    return f"name:{name}" if name else ""


def binding_key(row: dict[str, Any]) -> str:
    binding = safe_key(row.get("binding"))
    if binding:
        return f"binding:{binding}"
    actor = safe_key(row.get("actor"))
    if actor:
        return f"actor:{actor}"
    return ""


def option_track_index(row: dict[str, Any]) -> int | None:
    name = safe_key(row.get("trackName"))
    prefix = "Option "
    if not name.startswith(prefix):
        return None
    return as_int(name[len(prefix):])


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
    markers = [line_id for line_id in [*candidates, common] if line_id in line_order]
    if markers:
        end_index = max(line_order.index(line_id) for line_id in markers) + 1
        if common in line_order:
            end_index = max(end_index, line_order.index(common) + 1)
    return line_order[start_index:end_index]


def classify_group(
    option_entries: list[dict[str, Any]],
    candidate_lines: list[dict[str, Any]],
    window_lines: list[dict[str, Any]],
) -> tuple[str, str]:
    candidate_track_keys = [track_key(line) for line in candidate_lines if track_key(line)]
    candidate_binding_keys = [binding_key(line) for line in candidate_lines if binding_key(line)]
    unique_candidate_tracks = unique_preserve(candidate_track_keys)
    unique_candidate_bindings = unique_preserve(candidate_binding_keys)
    candidate_option_track_indices = [option_track_index(line) for line in candidate_lines]
    option_indices = [
        as_int((entry.get("bestRow") or {}).get("optionIndex"))
        for entry in option_entries
    ]

    timeline_option_track_sets: list[set[str]] = []
    for entry in option_entries:
        timeline_rows = [
            row for row in entry.get("allRows") or []
            if row.get("anchorMode") == "timelineClip"
        ]
        timeline_option_track_sets.append({track_key(row) for row in timeline_rows if track_key(row)})

    if (
        candidate_lines
        and len(candidate_lines) == len(option_entries)
        and all(value is not None for value in candidate_option_track_indices)
        and all(value is not None for value in option_indices)
        and set(candidate_option_track_indices) == set(option_indices)
        and len(set(candidate_option_track_indices)) == len(candidate_option_track_indices)
    ):
        return "candidateOptionNamedTrackMapping", "supportsOptionTrackRoute"

    if candidate_lines and len(unique_candidate_tracks) > 1:
        aligned = (
            len(candidate_lines) == len(option_entries)
            and all(
                track_key(candidate_lines[index]) in timeline_option_track_sets[index]
                for index in range(len(option_entries))
                if index < len(candidate_lines)
            )
        )
        if aligned:
            return "optionTimelineTrackMatchesCandidateTrack", "inspectAsPotentialTrackRoute"
        return "candidateTrackSplit", "inspectTrackSeparatedBranches"

    if candidate_lines and len(unique_candidate_bindings) > 1:
        return "candidateBindingSplit", "inspectBindingSeparatedBranches"

    option_tracks = [
        next(iter(track_set))
        for track_set in timeline_option_track_sets
        if len(track_set) == 1
    ]
    if len(option_tracks) == len(option_entries) and len(set(option_tracks)) > 1:
        return "optionClipTrackSplit", "decodeOptionClipTrackSemantics"

    if any(timeline_option_track_sets):
        candidate_track_set = set(candidate_track_keys)
        option_track_set = set().union(*timeline_option_track_sets)
        if candidate_track_set and option_track_set and not candidate_track_set.intersection(option_track_set):
            return "optionClipTrackDifferentFromCandidates", "avoidTrackBasedPromotion"
        if len({track_key(line) for line in window_lines if track_key(line)}) > 1:
            return "mixedWindowTracks", "inspectTimelineWindowTrackLayout"

    if candidate_lines:
        return "singleTrunkTrackOnly", "noBindingSignal"
    return "missingTimelineLineRows", "refreshTimelineExtraction"


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
    semantic_rows = semantics.collect_rows(
        language,
        conv_dir,
        timeline_orders_path,
        story_filters=story_filters,
        group_filters=group_filters,
        only_interesting=False,
    )
    rows: list[dict[str, Any]] = []

    for semantic_row in semantic_rows:
        story_key = safe_key(semantic_row.get("storyKey"))
        option_ids = [safe_key(option.get("optionId")) for option in semantic_row.get("options") or []]
        candidate_ids = [
            safe_key(value)
            for value in semantic_row.get("candidateLineIds") or []
            if safe_key(value)
        ]
        after_id = safe_key(semantic_row.get("after"))
        common_id = safe_key(semantic_row.get("commonContinuationLineId"))
        entry = semantics.timeline_entry_for_story(
            timeline_orders,
            story_key,
            option_ids=option_ids,
            line_ids=[after_id, common_id, *candidate_ids],
        )
        line_order = [safe_key(line_id) for line_id in entry.get("lineIds") or [] if safe_key(line_id)]
        line_positions = {line_id: index for index, line_id in enumerate(line_order)}
        line_map = {
            safe_key(line.get("id")): line
            for line in entry.get("lines") or []
            if isinstance(line, dict) and safe_key(line.get("id"))
        }
        option_rows_by_id = semantics.option_rows_by_id(entry)
        candidate_lines = [
            compact_timeline_line(line_id, line_map.get(line_id), line_positions.get(line_id))
            for line_id in candidate_ids
        ]
        window_ids = timeline_window(
            line_order,
            after=after_id,
            candidates=candidate_ids,
            common=common_id,
        )
        window_lines = [
            compact_timeline_line(line_id, line_map.get(line_id), line_positions.get(line_id))
            for line_id in window_ids
        ]
        option_entries: list[dict[str, Any]] = []
        for index, option_id in enumerate(option_ids):
            rows_for_option = sorted(
                option_rows_by_id.get(option_id) or [],
                key=semantics.option_row_rank,
            )
            compact_rows = [compact_option_row(row) for row in rows_for_option]
            option_entries.append({
                "optionId": option_id,
                "candidateLineId": candidate_ids[index] if index < len(candidate_ids) else "",
                "bestRow": compact_rows[0] if compact_rows else {},
                "allRows": compact_rows,
                "timelineClipTracks": unique_preserve([
                    track_key(row)
                    for row in compact_rows
                    if row.get("anchorMode") == "timelineClip" and track_key(row)
                ]),
                "trunkBindingTracks": unique_preserve([
                    track_key(row)
                    for row in compact_rows
                    if row.get("anchorMode") == "trunkBinding" and track_key(row)
                ]),
            })

        classification, recommendation = classify_group(option_entries, candidate_lines, window_lines)
        if only_interesting and recommendation in {"noBindingSignal", "avoidTrackBasedPromotion"}:
            continue

        row = {
            "language": language,
            "storyKey": story_key,
            "mission": semantic_row.get("mission"),
            "group": semantic_row.get("group"),
            "timeline": entry.get("timeline") or semantic_row.get("timeline") or "",
            "after": after_id,
            "candidateLineIds": candidate_ids,
            "commonContinuationLineId": common_id,
            "classification": classification,
            "recommendation": recommendation,
            "semanticClassification": semantic_row.get("classification"),
            "semanticRecommendation": semantic_row.get("recommendation"),
            "candidateTrackKeys": unique_preserve([track_key(line) for line in candidate_lines if track_key(line)]),
            "candidateOptionTrackIndices": [
                option_track_index(line)
                for line in candidate_lines
                if option_track_index(line) is not None
            ],
            "candidateBindingKeys": unique_preserve([binding_key(line) for line in candidate_lines if binding_key(line)]),
            "windowTrackKeys": unique_preserve([track_key(line) for line in window_lines if track_key(line)]),
            "options": option_entries,
            "candidateLines": candidate_lines,
            "windowLineIds": window_ids,
            "windowLines": window_lines,
        }
        rows.append(row)

    rows.sort(key=lambda item: (item.get("mission") or "", item.get("storyKey") or "", item.get("group") or 0))
    return rows


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
    groups_with_candidate_track_split = sum(
        1 for row in rows
        if len(row.get("candidateTrackKeys") or []) > 1
    )
    groups_with_option_named_track_mapping = sum(
        1 for row in rows
        if row.get("classification") == "candidateOptionNamedTrackMapping"
    )
    groups_with_candidate_binding_split = sum(
        1 for row in rows
        if len(row.get("candidateBindingKeys") or []) > 1
    )
    groups_with_mixed_window_tracks = sum(
        1 for row in rows
        if len(row.get("windowTrackKeys") or []) > 1
    )
    groups_with_option_timeline_clips = sum(
        1 for row in rows
        if any(option.get("timelineClipTracks") for option in row.get("options") or [])
    )
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
        "groupsWithCandidateTrackSplit": groups_with_candidate_track_split,
        "groupsWithOptionNamedTrackMapping": groups_with_option_named_track_mapping,
        "groupsWithCandidateBindingSplit": groups_with_candidate_binding_split,
        "groupsWithMixedWindowTracks": groups_with_mixed_window_tracks,
        "groupsWithOptionTimelineClips": groups_with_option_timeline_clips,
    }


def option_track_summary(row: dict[str, Any]) -> str:
    parts: list[str] = []
    candidates = row.get("candidateLines") or []
    for index, option in enumerate(row.get("options") or []):
        candidate = candidates[index] if index < len(candidates) else {}
        timeline_tracks = option.get("timelineClipTracks") or []
        fields = [
            f"candidateTrack={track_key(candidate) or '?'}",
            f"timelineClipTracks={','.join(timeline_tracks) if timeline_tracks else '-'}",
        ]
        if candidate.get("binding"):
            fields.append(f"binding={candidate.get('binding')}")
        parts.append(f"{option.get('optionId')} -> {candidate.get('id') or option.get('candidateLineId')} ({'; '.join(fields)})")
    return "; ".join(parts)


def render_markdown(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = [
        f"# Timeline Binding Audit - {summary['language']}",
        "",
        f"- Inferred response groups audited: `{summary['inferredResponseGroupCount']}`",
        f"- Groups with candidate track split: `{summary['groupsWithCandidateTrackSplit']}`",
        f"- Groups with option-named track mapping: `{summary['groupsWithOptionNamedTrackMapping']}`",
        f"- Groups with candidate binding split: `{summary['groupsWithCandidateBindingSplit']}`",
        f"- Groups with mixed window tracks: `{summary['groupsWithMixedWindowTracks']}`",
        f"- Groups with option timeline clips: `{summary['groupsWithOptionTimelineClips']}`",
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
        "| Scene | Group | After | Candidates | Common | Class | Recommendation | Track evidence |",
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
            f"| {md_escape(option_track_summary(row))} |"
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
    out_json = reports_dir / f"timeline_binding_audit_{language}{suffix}.json"
    out_md = reports_dir / f"timeline_binding_audit_{language}{suffix}.md"
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
        help="Keep only groups with non-default track/binding diagnostics.",
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
    print(f"Timeline binding audit: {result['markdown']}")
    print(f"Timeline binding data:  {result['json']}")
    print(
        "Audited "
        f"{result['summary']['inferredResponseGroupCount']} inferred response groups; "
        f"{result['summary']['groupsWithOptionNamedTrackMapping']} option-named track mappings."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
