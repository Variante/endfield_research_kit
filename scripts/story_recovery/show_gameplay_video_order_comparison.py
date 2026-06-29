#!/usr/bin/env python3
"""Show selected gameplay OCR mission-order matches beside active overrides.

The default scope is current complete P10 OCR reports. The script reuses the
same text-only Story OCR matcher as ``build_gameplay_video_story_order.py`` so
refreshed per-video OCR reports can be inspected before rerunning or applying
the full promotion pipeline.
"""
from __future__ import annotations

import argparse
import sys
import time
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (_REPO_ROOT / "scripts", _REPO_ROOT / "scripts" / "story_recovery"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from common import (  # noqa: E402
    REPORTS_DIR,
    md_escape,
    rel_path,
    safe_key,
    split_csv_values,
    write_report_json,
    write_text_if_changed,
)
import build_gameplay_video_story_order as matcher  # noqa: E402


REPORT_DIR = REPORTS_DIR / "gameplay_video_ocr"


def default_output_stem(args: argparse.Namespace) -> str:
    if args.all_parts:
        return "all_parts_story_order_comparison"
    parts = sorted(set(args.part or [10]))
    if len(parts) == 1:
        return f"p{parts[0]}_story_order_comparison"
    part_label = "_".join(f"p{part}" for part in parts)
    return f"{part_label}_story_order_comparison"


def clean_unique_keys(rows: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for row in rows:
        key = safe_key(row.get("key"))
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def selected_report(
    report: dict[str, Any],
    *,
    parts: set[int],
    selectors: list[str],
    all_parts: bool,
) -> bool:
    video_name = matcher.report_video_name(report)
    report_path = safe_key(report.get("_reportPath"))
    part = matcher.gameplay_video_part_number(video_name)
    if not all_parts and (part is None or part not in parts):
        return False
    if not selectors:
        return True
    haystack = f"{video_name}\n{report_path}".lower()
    return any(selector.lower() in haystack for selector in selectors)


def observation_details_by_key(sequence: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    details: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(sequence, start=1):
        key = safe_key(row.get("key"))
        if not key or key in details:
            continue
        details[key] = {
            "matchedIndex": index,
            "firstTime": safe_key(row.get("firstTime")),
            "lastTime": safe_key(row.get("lastTime")),
            "score": safe_float(row.get("score")),
            "avgScore": safe_float(row.get("avgScore")),
            "matchCount": safe_int(row.get("matchCount")),
            "lineId": safe_key(row.get("lineId")),
            "source": safe_key(row.get("source")),
            "linkReason": safe_key(row.get("linkReason")),
            "text": safe_key(row.get("text")),
            "selectionReason": safe_key(row.get("selectionReason")),
        }
    return details


def format_time_range(details: dict[str, Any] | None) -> str:
    if not details:
        return ""
    start = safe_key(details.get("firstTime"))
    end = safe_key(details.get("lastTime"))
    if start and end and start != end:
        return f"{start}-{end}"
    return start or end


def format_score(details: dict[str, Any] | None) -> str:
    if not details:
        return ""
    score = safe_float(details.get("score"))
    count = safe_int(details.get("matchCount"))
    if count:
        return f"{score:.3f} x{count}"
    if score:
        return f"{score:.3f}"
    return ""


def comparison_rows(
    matched_keys: list[str],
    override_subset: list[str],
    override_positions: dict[str, int],
    details_by_key: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    matcher_obj = SequenceMatcher(None, matched_keys, override_subset, autojunk=False)
    matched_positions = {key: index for index, key in enumerate(matched_keys, start=1)}
    for tag, left_start, left_end, right_start, right_end in matcher_obj.get_opcodes():
        left = matched_keys[left_start:left_end]
        right = override_subset[right_start:right_end]
        width = max(len(left), len(right))
        for index in range(width):
            matched_key = left[index] if index < len(left) else ""
            override_key = right[index] if index < len(right) else ""
            if matched_key and override_key and matched_key == override_key:
                status = "same"
            elif matched_key and not override_key:
                status = "not-in-override" if matched_key not in override_positions else "ocr-placement"
            elif override_key and not matched_key:
                status = "override-placement"
            else:
                status = "moved"
            details = details_by_key.get(matched_key) if matched_key else None
            rows.append({
                "status": status,
                "matchedIndex": matched_positions.get(matched_key),
                "matchedKey": matched_key,
                "matchedTime": format_time_range(details),
                "matchedScore": format_score(details),
                "matchedSource": safe_key(details.get("source")) if details else "",
                "matchedLineId": safe_key(details.get("lineId")) if details else "",
                "matchedText": safe_key(details.get("text")) if details else "",
                "overrideIndex": override_positions.get(override_key),
                "overrideKey": override_key,
            })
    return rows


def override_window_rows(
    override_order: list[str],
    matched_keys: list[str],
    details_by_key: dict[str, dict[str, Any]],
    *,
    context: int,
) -> list[dict[str, Any]]:
    override_positions = {key: index for index, key in enumerate(override_order, start=1)}
    positions = [override_positions[key] for key in matched_keys if key in override_positions]
    if not positions:
        return []
    start = max(1, min(positions) - context)
    end = min(len(override_order), max(positions) + context)
    matched_index_by_key = {key: index for index, key in enumerate(matched_keys, start=1)}
    rows: list[dict[str, Any]] = []
    for override_index in range(start, end + 1):
        key = override_order[override_index - 1]
        details = details_by_key.get(key)
        rows.append({
            "overrideIndex": override_index,
            "key": key,
            "matchedIndex": matched_index_by_key.get(key),
            "matchedTime": format_time_range(details),
            "matchedScore": format_score(details),
            "matchedSource": safe_key(details.get("source")) if details else "",
            "matchedLineId": safe_key(details.get("lineId")) if details else "",
            "matchedText": safe_key(details.get("text")) if details else "",
        })
    return rows


def inversion_samples(
    matched_keys: list[str],
    override_positions: dict[str, int],
    *,
    limit: int = 12,
) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    checked = [(key, override_positions[key]) for key in matched_keys if key in override_positions]
    for (left_key, left_position), (right_key, right_position) in zip(checked, checked[1:]):
        if right_position < left_position:
            samples.append({
                "prevKey": left_key,
                "prevOverrideIndex": left_position,
                "key": right_key,
                "overrideIndex": right_position,
            })
            if len(samples) >= limit:
                break
    return samples


def compare_sequence_to_override(
    *,
    video_name: str,
    mission: str,
    sequence: list[dict[str, Any]],
    override_order: list[str],
    locked: bool,
    context: int,
) -> dict[str, Any]:
    matched_keys = clean_unique_keys(sequence)
    details_by_key = observation_details_by_key(sequence)
    override_positions = {key: index for index, key in enumerate(override_order, start=1)}
    matched_keys_in_override = [key for key in matched_keys if key in override_positions]
    override_subset = [key for key in override_order if key in set(matched_keys)]
    missing_from_override = [key for key in matched_keys if key not in override_positions]
    rows = comparison_rows(matched_keys, override_subset, override_positions, details_by_key)
    inversions = inversion_samples(matched_keys, override_positions)
    return {
        "video": video_name,
        "mission": mission,
        "locked": locked,
        "matchedCount": len(matched_keys),
        "overrideCount": len(override_order),
        "matchedKeys": matched_keys,
        "overrideMatchedSubset": override_subset,
        "missingFromOverride": missing_from_override,
        "overrideOnlyCount": len([key for key in override_order if key not in set(matched_keys)]),
        "sameRelativeOrder": matched_keys_in_override == override_subset and not missing_from_override,
        "adjacentInversions": inversions,
        "comparisonRows": rows,
        "overrideWindowRows": override_window_rows(
            override_order,
            matched_keys,
            details_by_key,
            context=context,
        ),
    }


def load_selected_reports(args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Counter[str]]:
    min_tool_version = 0 if args.include_stale_ocr else matcher.MIN_OCR_TOOL_VERSION
    reports, stats = matcher.load_ocr_reports(
        REPORT_DIR,
        include_smoke=args.include_smoke,
        min_tool_version=min_tool_version,
        require_archive_box_ocr=not args.include_stale_ocr,
    )
    selectors = split_csv_values(args.video)
    parts = set(args.part or [10])
    selected = [
        report
        for report in reports
        if selected_report(report, parts=parts, selectors=selectors, all_parts=args.all_parts)
    ]
    return reports, selected, stats


def match_selected_reports(args: argparse.Namespace) -> dict[str, Any]:
    active_story_order, active_warning = matcher.read_active_story_order(matcher.ACTIVE_STORY_ORDER_PATH)
    if active_warning:
        raise SystemExit(active_warning)

    story_orders = matcher.story_orders_by_mission(active_story_order)
    locked_missions = matcher.story_order_locked_missions(active_story_order)
    all_reports, selected_reports, load_stats = load_selected_reports(args)
    if not selected_reports:
        loaded_names = [matcher.report_video_name(report) for report in all_reports]
        raise SystemExit(
            "No selected OCR reports found. "
            "Try --include-stale-ocr for older OCR outputs, --all-parts, or --video with a filename substring.\n"
            f"Loaded report count: {len(loaded_names)}"
        )

    print(f"Loading Story corpus from {rel_path(matcher.CONV_ROOT)}...")
    corpus = matcher.load_corpus(
        conv_root=matcher.CONV_ROOT,
        story_order={},
        min_chars=args.min_chars,
        include_titles=args.include_title_matches,
        restrict_to_story_order=False,
    )
    print(
        f"Loaded {len(corpus)} searchable Story text row(s) "
        "from generated native mission data; active story order is comparison-only."
    )
    corpus_by_mission: dict[str, list[matcher.CorpusLine]] = defaultdict(list)
    for line in corpus:
        corpus_by_mission[line.mission].append(line)

    related_missions_by_mission: dict[str, list[dict[str, str]]] = {}
    mission_title_candidates = matcher.load_mission_title_candidates(matcher.MISSIONS_PATH)
    search_contexts = matcher.build_video_search_contexts(all_reports, mission_title_candidates)
    context_by_report = {id(report): context for report, context in zip(all_reports, search_contexts)}
    companion_index = matcher.build_map_dialog_companion_index(corpus) if args.include_companions else {}
    gram_index_by_scope: dict[tuple[str, ...], dict[str, list[int]]] = {}
    videos: list[dict[str, Any]] = []

    for report in selected_reports:
        video_name = matcher.report_video_name(report)
        context = context_by_report.get(id(report), {})
        mission_match = context.get("missionMatch") if isinstance(context.get("missionMatch"), dict) else {}
        target_mission = safe_key(mission_match.get("mission"))
        target_title = safe_key(mission_match.get("title"))
        target_match = safe_key(mission_match.get("match")) or safe_key(mission_match.get("status"))
        search_missions = [
            row for row in (context.get("searchMissions") or [])
            if isinstance(row, dict) and safe_key(row.get("mission"))
        ]
        segments = [segment for segment in (report.get("segments") or []) if isinstance(segment, dict)]

        video_corpus, related_rows = matcher.corpus_for_search_missions(
            search_missions,
            corpus_by_mission=corpus_by_mission,
            related_missions_by_mission=related_missions_by_mission,
        )
        search_scope_key = tuple(safe_key(row.get("mission")) for row in search_missions)
        gram_index = gram_index_by_scope.get(search_scope_key)
        if gram_index is None:
            gram_index = matcher.build_gram_index(video_corpus)
            gram_index_by_scope[search_scope_key] = gram_index

        search_label = ", ".join(safe_key(row.get("mission")) for row in search_missions) or "-"
        print(
            f"[{video_name}] target={target_mission or '-'}"
            f"{f' ({target_title})' if target_title else ''} "
            f"via {target_match or '-'}; matching {len(segments)} segment(s) across {search_label}"
        )
        started = time.monotonic()
        ocr_matches: list[dict[str, Any]] = []
        for segment in segments:
            match = matcher.aggregate_segment_match(
                segment,
                corpus=video_corpus,
                gram_index=gram_index,
                min_chars=args.min_chars,
                topn=args.topn,
            )
            if not match:
                continue
            match["video"] = video_name
            match["accepted"] = matcher.is_accept(
                match,
                min_score=args.min_score,
                min_margin=args.min_margin,
            )
            ocr_matches.append(match)

        companion_matches = matcher.build_map_dialog_companion_matches(
            ocr_matches,
            companion_index,
            min_score=args.min_score,
            min_margin=args.min_margin,
        )
        matches = ocr_matches + companion_matches
        accepted_missions, observed_sequences, sequence_diagnostics = matcher.observed_sequences_from_matches(
            matches,
            base_story_orders={},
            min_video_matches=args.min_video_matches,
            min_sequence_keys=args.min_sequence_keys,
            use_ransac=False,
            ransac_tolerance=args.ransac_tolerance,
            keep_partial_sequences=True,
        )
        accepted = sum(1 for row in matches if row.get("accepted"))
        print(
            f"[{video_name}] matched={len(matches)} accepted={accepted} "
            f"missions={','.join(mission for mission, _count in accepted_missions.most_common()) or '-'} "
            f"in {time.monotonic() - started:.1f}s"
        )
        videos.append({
            "video": video_name,
            "report": report.get("_reportPath"),
            "targetMission": target_mission,
            "targetMissionTitle": target_title,
            "targetMissionMatch": target_match,
            "searchMissions": search_missions,
            "relatedCorpus": related_rows,
            "matchedSegments": len(matches),
            "acceptedMatches": accepted,
            "mapDialogCompanionMatches": len(companion_matches),
            "missions": [mission for mission, _count in accepted_missions.most_common()],
            "observedSequences": observed_sequences,
            "sequenceDiagnostics": sequence_diagnostics,
        })

    comparisons: list[dict[str, Any]] = []
    for video in videos:
        sequences = video.get("observedSequences") if isinstance(video.get("observedSequences"), dict) else {}
        for mission, sequence in sequences.items():
            mission_key = safe_key(mission)
            if args.mission and mission_key not in set(split_csv_values(args.mission)):
                continue
            if not isinstance(sequence, list):
                continue
            comparisons.append(compare_sequence_to_override(
                video_name=safe_key(video.get("video")),
                mission=mission_key,
                sequence=sequence,
                override_order=story_orders.get(mission_key) or [],
                locked=mission_key in locked_missions,
                context=args.context,
            ))

    return {
        "schema": "gameplayVideoStoryOrderComparison.v1",
        "inputs": {
            "ocrReportDir": rel_path(REPORT_DIR),
            "storyOrder": rel_path(matcher.ACTIVE_STORY_ORDER_PATH),
            "parts": [] if args.all_parts else sorted(set(args.part or [10])),
            "videoSelectors": split_csv_values(args.video),
            "includeStaleOcr": bool(args.include_stale_ocr),
            "includeSmoke": bool(args.include_smoke),
            "includeCompanions": bool(args.include_companions),
            "includeTitleMatches": bool(args.include_title_matches),
            "minScore": args.min_score,
            "minMargin": args.min_margin,
            "minChars": args.min_chars,
            "minVideoMatches": args.min_video_matches,
            "minSequenceKeys": args.min_sequence_keys,
            "ransacEnabled": False,
            "ransacTolerance": None,
        },
        "loadStats": dict(sorted(load_stats.items())),
        "summary": {
            "loadedReports": len(all_reports),
            "selectedReports": len(selected_reports),
            "videos": len(videos),
            "comparisons": len(comparisons),
            "missions": sorted({row["mission"] for row in comparisons}),
            "sameRelativeOrder": sum(1 for row in comparisons if row.get("sameRelativeOrder")),
            "withAdjacentInversions": sum(1 for row in comparisons if row.get("adjacentInversions")),
            "missingFromOverride": sum(len(row.get("missingFromOverride") or []) for row in comparisons),
        },
        "videos": videos,
        "comparisons": comparisons,
    }


def render_summary_value(value: Any) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else "-"
    return str(value)


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Gameplay Video Story-Order Comparison",
        "",
        f"- OCR report dir: `{md_escape(payload.get('inputs', {}).get('ocrReportDir'))}`",
        f"- Active override: `{md_escape(payload.get('inputs', {}).get('storyOrder'))}`",
        f"- Parts: `{md_escape(render_summary_value(payload.get('inputs', {}).get('parts')) or 'all')}`",
        f"- Video selectors: `{md_escape(render_summary_value(payload.get('inputs', {}).get('videoSelectors')) or '-')}`",
        f"- Include stale OCR: `{str(bool(payload.get('inputs', {}).get('includeStaleOcr'))).lower()}`",
        f"- Include title matches: `{str(bool(payload.get('inputs', {}).get('includeTitleMatches'))).lower()}`",
        f"- Min score/margin: `{payload.get('inputs', {}).get('minScore')}` / `{payload.get('inputs', {}).get('minMargin')}`",
        "",
        "## Summary",
        "",
        "| loaded reports | selected reports | videos | mission comparisons | same relative order | with inversions | missing from override |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    lines.append(
        f"| {summary.get('loadedReports', 0)} "
        f"| {summary.get('selectedReports', 0)} "
        f"| {summary.get('videos', 0)} "
        f"| {summary.get('comparisons', 0)} "
        f"| {summary.get('sameRelativeOrder', 0)} "
        f"| {summary.get('withAdjacentInversions', 0)} "
        f"| {summary.get('missingFromOverride', 0)} |"
    )

    for video in payload.get("videos") or []:
        lines.extend([
            "",
            f"## `{md_escape(video.get('video'))}`",
            "",
            f"- Report: `{md_escape(video.get('report'))}`",
            f"- Target mission: `{md_escape(video.get('targetMission') or '-')}`"
            + (f" `{md_escape(video.get('targetMissionTitle'))}`" if video.get("targetMissionTitle") else ""),
            f"- Search missions: `{md_escape(', '.join(safe_key(row.get('mission')) for row in (video.get('searchMissions') or [])) or '-')}`",
            f"- Matched/accepted segments: `{video.get('matchedSegments', 0)}` / `{video.get('acceptedMatches', 0)}`",
            f"- Matched missions: `{md_escape(', '.join(video.get('missions') or []) or '-')}`",
        ])
        video_comparisons = [
            row for row in payload.get("comparisons") or []
            if row.get("video") == video.get("video")
        ]
        for comparison in video_comparisons:
            status = "same" if comparison.get("sameRelativeOrder") else "diff"
            if comparison.get("missingFromOverride"):
                status += ", missing"
            if comparison.get("adjacentInversions"):
                status += ", inversion"
            lines.extend([
                "",
                f"### `{md_escape(comparison.get('mission'))}`",
                "",
                f"- Locked: `{str(bool(comparison.get('locked'))).lower()}`",
                f"- Matched keys: `{comparison.get('matchedCount', 0)}`; override keys: `{comparison.get('overrideCount', 0)}`",
                f"- Relative order status: `{md_escape(status)}`",
            ])
            if comparison.get("missingFromOverride"):
                missing = ", ".join(f"`{md_escape(key)}`" for key in comparison.get("missingFromOverride") or [])
                lines.append(f"- Missing from override: {missing}")
            if comparison.get("adjacentInversions"):
                samples = "; ".join(
                    f"{row.get('prevKey')}@{row.get('prevOverrideIndex')} -> "
                    f"{row.get('key')}@{row.get('overrideIndex')}"
                    for row in comparison.get("adjacentInversions") or []
                )
                lines.append(f"- Adjacent inversions: `{md_escape(samples)}`")
            lines.extend([
                "",
                "| OCR # | OCR key | source | time | score x hits | override # | override key | status |",
                "|---:|---|---|---|---:|---:|---|---|",
            ])
            for row in comparison.get("comparisonRows") or []:
                source = safe_key(row.get("matchedSource"))
                line_id = safe_key(row.get("matchedLineId"))
                source_label = source
                if line_id:
                    source_label = f"{source}:{line_id}" if source else line_id
                lines.append(
                    f"| {row.get('matchedIndex') or ''} "
                    f"| `{md_escape(row.get('matchedKey'))}` "
                    f"| `{md_escape(source_label)}` "
                    f"| `{md_escape(row.get('matchedTime'))}` "
                    f"| `{md_escape(row.get('matchedScore'))}` "
                    f"| {row.get('overrideIndex') or ''} "
                    f"| `{md_escape(row.get('overrideKey'))}` "
                    f"| `{md_escape(row.get('status'))}` |"
                )
            window_rows = comparison.get("overrideWindowRows") or []
            if window_rows:
                lines.extend([
                    "",
                    "Override window:",
                    "",
                    "| override # | key | OCR # | OCR source | OCR time | score x hits |",
                    "|---:|---|---:|---|---|---:|",
                ])
                for row in window_rows:
                    source = safe_key(row.get("matchedSource"))
                    line_id = safe_key(row.get("matchedLineId"))
                    source_label = source
                    if line_id:
                        source_label = f"{source}:{line_id}" if source else line_id
                    lines.append(
                        f"| {row.get('overrideIndex') or ''} "
                        f"| `{md_escape(row.get('key'))}` "
                        f"| {row.get('matchedIndex') or ''} "
                        f"| `{md_escape(source_label)}` "
                        f"| `{md_escape(row.get('matchedTime'))}` "
                        f"| `{md_escape(row.get('matchedScore'))}` |"
                    )
    return "\n".join(lines).rstrip() + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--part", type=int, action="append", help="video part to include; default: 10")
    parser.add_argument("--all-parts", action="store_true", help="do not filter by video part")
    parser.add_argument("--video", action="append", help="filename/report substring selector; repeat or comma-separate")
    parser.add_argument("--mission", action="append", help="mission id filter for output comparisons")
    parser.add_argument("--include-stale-ocr", action="store_true", help="include older OCR reports skipped by the current matcher")
    parser.add_argument("--include-smoke", action="store_true", help="include OCR reports made with --limit-frames")
    parser.add_argument("--include-companions", action="store_true", help="include synthetic archive-to-map-dialog companion matches")
    parser.add_argument("--include-title-matches", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--min-chars", type=int, default=4)
    parser.add_argument("--min-score", type=float, default=0.98)
    parser.add_argument("--min-margin", type=float, default=0.06)
    parser.add_argument("--topn", type=int, default=5)
    parser.add_argument("--min-video-matches", type=int, default=2)
    parser.add_argument("--min-sequence-keys", type=int, default=2)
    parser.add_argument("--no-ransac", action="store_true")
    parser.add_argument("--ransac-tolerance", type=float, default=matcher.DEFAULT_RANSAC_TOLERANCE)
    parser.add_argument("--context", type=int, default=2, help="override rows to show before/after the matched range")
    parser.add_argument("--json", type=Path, default=None)
    parser.add_argument("--markdown", type=Path, default=None)
    parser.add_argument("--no-write", action="store_true", help="print only; do not write report files")
    parser.add_argument("--no-stdout", action="store_true", help="write reports without printing the markdown body")
    args = parser.parse_args(argv)
    if args.min_chars <= 0:
        parser.error("--min-chars must be greater than zero")
    if args.min_video_matches <= 0:
        parser.error("--min-video-matches must be greater than zero")
    if args.min_sequence_keys <= 0:
        parser.error("--min-sequence-keys must be greater than zero")
    if args.ransac_tolerance <= 0:
        parser.error("--ransac-tolerance must be greater than zero")
    if args.context < 0:
        parser.error("--context must be zero or greater")
    stem = default_output_stem(args)
    if args.json is None:
        args.json = REPORT_DIR / f"{stem}.json"
    if args.markdown is None:
        args.markdown = REPORT_DIR / f"{stem}.md"
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = match_selected_reports(args)
    markdown = render_markdown(payload)
    if not args.no_write:
        write_report_json(args.json, payload)
        write_text_if_changed(args.markdown, markdown)
        print(f"Wrote {rel_path(args.json)}")
        print(f"Wrote {rel_path(args.markdown)}")
    if not args.no_stdout:
        print()
        print(markdown, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
