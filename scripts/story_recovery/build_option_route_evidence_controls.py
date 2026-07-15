#!/usr/bin/env python3
"""Summarize positive and negative controls for option-route evidence.

This report is a sanity check for inferred option responses. Positive controls
come from recovered `optionRoutes` in the Timeline catalog, which are built from
original Runtime Jump Track ranges. Negative controls come from the current
runtime-jump audit of live `inferredOptionResponse` warnings.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
import re
import sys
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (_REPO_ROOT / "scripts",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from common import ROOT, md_escape, read_json, write_report_json, write_text_if_changed  # noqa: E402


PRIORITY_MISSION_TYPES = {
    "e": "main",
    "a": "event",
    "gm": "major",
    "c": "character",
}
MISSION_TYPE_RE = re.compile(r"^([a-z]+)")


def safe_text(value: Any) -> str:
    return str(value or "")


def mission_from_story_key(story_key: str) -> str:
    text = safe_text(story_key)
    if text.startswith("misc_dlg_"):
        text = text[len("misc_dlg_") :]
    elif text.startswith("dlg_"):
        text = text[len("dlg_") :]
    return text.split("_", 1)[0]


def priority_bucket(mission: str) -> str:
    match = MISSION_TYPE_RE.match(safe_text(mission).lower())
    mission_type = match.group(1) if match else ""
    return PRIORITY_MISSION_TYPES.get(mission_type, "")


def compact_line_ids(line_ids: list[Any], *, limit: int = 4) -> str:
    values = [safe_text(value) for value in line_ids if safe_text(value)]
    if not values:
        return ""
    text = ",".join(values[:limit])
    if len(values) > limit:
        text += f",+{len(values) - limit}"
    return text


def route_range_count(route: dict[str, Any]) -> int:
    return len(route.get("skipRanges") or []) + len(route.get("reverseRanges") or [])


def route_summary(option_id: str, route: dict[str, Any]) -> str:
    parts = [
        f"{option_id}:idx={route.get('optionIndex')}",
        f"path={compact_line_ids(route.get('pathLineIds') or [])}",
    ]
    skipped = compact_line_ids(route.get("skippedLineIds") or [])
    reverse = compact_line_ids(route.get("reverseRangeLineIds") or [])
    if skipped:
        parts.append(f"skip={skipped}")
    if reverse:
        parts.append(f"reverse={reverse}")
    if route.get("terminatesSlot"):
        parts.append("terminates")
    return ";".join(parts)


def route_tracks(routes: list[dict[str, Any]], *, limit: int = 3) -> list[str]:
    tracks: list[str] = []
    for route in routes:
        for range_row in (route.get("skipRanges") or []) + (route.get("reverseRanges") or []):
            track = safe_text(range_row.get("track"))
            if track and track not in tracks:
                tracks.append(track)
    return tracks[:limit]


def collect_positive_controls(timeline_orders_path: Path, *, priority_only: bool) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    timeline_orders = read_json(timeline_orders_path, {})
    if not isinstance(timeline_orders, dict):
        timeline_orders = {}

    grouped: dict[tuple[str, str], list[tuple[str, dict[str, Any]]]] = defaultdict(list)
    for story_key, entry in timeline_orders.items():
        if not isinstance(entry, dict):
            continue
        mission = mission_from_story_key(story_key)
        bucket = priority_bucket(mission)
        if priority_only and not bucket:
            continue
        routes = entry.get("optionRoutes") if isinstance(entry.get("optionRoutes"), dict) else {}
        for option_id, route in routes.items():
            if isinstance(route, dict):
                grouped[(story_key, safe_text(route.get("groupKey")))].append((safe_text(option_id), route))

    rows: list[dict[str, Any]] = []
    source_counts: Counter[str] = Counter()
    bucket_counts: Counter[str] = Counter()
    route_counts_by_bucket: Counter[str] = Counter()
    groups_with_distinct_paths = 0
    groups_with_range_evidence = 0

    for (story_key, group_key), option_routes in sorted(grouped.items()):
        mission = mission_from_story_key(story_key)
        bucket = priority_bucket(mission) or "other"
        routes = [route for _option_id, route in option_routes]
        sources = sorted({safe_text(route.get("source")) for route in routes if safe_text(route.get("source"))})
        paths = {tuple(route.get("pathLineIds") or []) for route in routes}
        has_distinct_paths = len(paths) >= 2
        has_range_evidence = all(route_range_count(route) > 0 for route in routes)
        if has_distinct_paths:
            groups_with_distinct_paths += 1
        if has_range_evidence:
            groups_with_range_evidence += 1
        for route in routes:
            source_counts[safe_text(route.get("source")) or "unknown"] += 1
        bucket_counts[bucket] += 1
        route_counts_by_bucket[bucket] += len(routes)
        rows.append({
            "storyKey": story_key,
            "mission": mission,
            "bucket": bucket,
            "group": group_key,
            "routeCount": len(routes),
            "sources": sources,
            "hasDistinctPaths": has_distinct_paths,
            "hasRangeEvidenceForEveryOption": has_range_evidence,
            "tracks": route_tracks(routes),
            "routes": [
                {
                    "optionId": option_id,
                    "source": route.get("source"),
                    "optionIndex": route.get("optionIndex"),
                    "pathLineIds": route.get("pathLineIds") or [],
                    "skippedLineIds": route.get("skippedLineIds") or [],
                    "reverseRangeLineIds": route.get("reverseRangeLineIds") or [],
                    "skipRangeCount": len(route.get("skipRanges") or []),
                    "reverseRangeCount": len(route.get("reverseRanges") or []),
                }
                for option_id, route in option_routes
            ],
            "summary": " | ".join(route_summary(option_id, route) for option_id, route in option_routes),
        })

    summary = {
        "timelineOrders": str(timeline_orders_path),
        "priorityOnly": priority_only,
        "positiveRouteGroupCount": len(rows),
        "positiveRouteEntryCount": sum(row["routeCount"] for row in rows),
        "positiveGroupsWithDistinctPaths": groups_with_distinct_paths,
        "positiveGroupsWithRangeEvidenceForEveryOption": groups_with_range_evidence,
        "positiveRouteSourceCounts": dict(sorted(source_counts.items())),
        "positiveGroupCountsByBucket": dict(sorted(bucket_counts.items())),
        "positiveRouteCountsByBucket": dict(sorted(route_counts_by_bucket.items())),
    }
    return summary, rows


def collect_negative_controls(runtime_audit_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = read_json(runtime_audit_path, {})
    if not isinstance(payload, dict):
        payload = {}
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    groups = payload.get("groups") if isinstance(payload.get("groups"), list) else []
    rows: list[dict[str, Any]] = []
    for row in groups:
        if not isinstance(row, dict):
            continue
        mission = safe_text(row.get("mission"))
        bucket = priority_bucket(mission) or "other"
        checks = row.get("checks") if isinstance(row.get("checks"), dict) else {}
        rows.append({
            "storyKey": row.get("sceneKey"),
            "mission": mission,
            "bucket": bucket,
            "group": row.get("group"),
            "recommendation": row.get("recommendation"),
            "nearbyRuntimeJumpCount": len(row.get("nearbyRuntimeJumps") or []),
            "completeForwardCoverage": bool(checks.get("completeForwardCoverage")),
            "passesNarrowRouteRule": bool(checks.get("passesNarrowRouteRule")),
            "runtimePathConflictCount": checks.get("runtimePathConflictCount") or 0,
            "optionChangeAllResetToDefault": bool(checks.get("postJumpOptionChangeAllResetToDefault")),
            "candidateLineIds": row.get("candidateLineIds") or [],
            "commonContinuationLineId": row.get("commonContinuationLineId"),
        })
    return {
        "runtimeAudit": str(runtime_audit_path),
        "runtimeAuditSummary": summary,
    }, rows


def markdown_report(payload: dict[str, Any]) -> str:
    pos = payload["positiveSummary"]
    neg = payload["negativeSummary"]["runtimeAuditSummary"]
    lines = [
        f"# Option Route Evidence Controls - {payload['language']}",
        "",
        "Scope: priority story buckets only (`e`, `a`, `gm`, `c`).",
        "",
        "## Positive Controls",
        "",
        f"- Runtime Jump route groups: `{pos['positiveRouteGroupCount']}`",
        f"- Runtime Jump route entries: `{pos['positiveRouteEntryCount']}`",
        f"- Groups with distinct per-option paths: `{pos['positiveGroupsWithDistinctPaths']}`",
        f"- Groups with skip/reverse range evidence for every option: `{pos['positiveGroupsWithRangeEvidenceForEveryOption']}`",
        f"- Route sources: `{pos['positiveRouteSourceCounts']}`",
        f"- Route groups by bucket: `{pos['positiveGroupCountsByBucket']}`",
        "",
        "| scene | bucket | group | sources | routes |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for row in payload["positiveRows"]:
        lines.append(
            "| "
            f"`{md_escape(row['storyKey'])}` "
            f"| `{md_escape(row['bucket'])}` "
            f"| {md_escape(row['group'])} "
            f"| `{md_escape(', '.join(row.get('sources') or []))}` "
            f"| {md_escape(row.get('summary'))} |"
        )
    if not payload["positiveRows"]:
        lines.append("| _(none)_ |  |  |  |  |")

    lines.extend([
        "",
        "## Negative Controls",
        "",
        f"- Live inferred-response groups audited: `{neg.get('inferredFollowingLineGroupCount', 0)}`",
        f"- Groups with nearby Runtime Jump Track clips: `{neg.get('groupsWithNearbyRuntimeJumps', 0)}`",
        f"- Groups passing the strict Runtime Jump route rule: `{neg.get('groupsPassingNarrowRouteRule', 0)}`",
        f"- Recommendations: `{neg.get('recommendationCounts', {})}`",
        "",
        "| scene | bucket | group | nearby jumps | conflict count | recommendation | candidates | common |",
        "| --- | --- | ---: | ---: | ---: | --- | --- | --- |",
    ])
    for row in payload["negativeRows"]:
        if row.get("recommendation") == "noNearbyRuntimeJump":
            continue
        lines.append(
            "| "
            f"`{md_escape(row.get('storyKey'))}` "
            f"| `{md_escape(row.get('bucket'))}` "
            f"| {md_escape(row.get('group'))} "
            f"| {row.get('nearbyRuntimeJumpCount')} "
            f"| {row.get('runtimePathConflictCount')} "
            f"| `{md_escape(row.get('recommendation'))}` "
            f"| `{md_escape(', '.join(row.get('candidateLineIds') or []))}` "
            f"| `{md_escape(row.get('commonContinuationLineId'))}` |"
        )
    if not [row for row in payload["negativeRows"] if row.get("recommendation") != "noNearbyRuntimeJump"]:
        lines.append("| _(none)_ |  |  |  |  |  |  |  |")

    lines.extend([
        "",
        "## Decision",
        "",
        "Promote only the positive-control shape: every option has authored Runtime Jump range evidence and the recovered paths are distinct. The live unresolved groups do not match that shape.",
    ])
    return "\n".join(lines) + "\n"


def build_report(
    language: str,
    timeline_orders_path: Path,
    runtime_audit_path: Path,
    reports_dir: Path,
    *,
    priority_only: bool = True,
) -> dict[str, Any]:
    positive_summary, positive_rows = collect_positive_controls(
        timeline_orders_path,
        priority_only=priority_only,
    )
    negative_summary, negative_rows = collect_negative_controls(runtime_audit_path)
    payload = {
        "language": language,
        "positiveSummary": positive_summary,
        "positiveRows": positive_rows,
        "negativeSummary": negative_summary,
        "negativeRows": negative_rows,
    }
    reports_dir.mkdir(parents=True, exist_ok=True)
    suffix = "_priority" if priority_only else ""
    out_json = reports_dir / f"option_route_evidence_controls_{language}{suffix}.json"
    out_md = reports_dir / f"option_route_evidence_controls_{language}{suffix}.md"
    write_report_json(out_json, payload)
    write_text_if_changed(out_md, markdown_report(payload))
    return {
        "summary": payload,
        "json": out_json,
        "markdown": out_md,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", default="CN")
    parser.add_argument(
        "--timeline-orders",
        type=Path,
        default=ROOT / "export_full" / "recovered" / "AnimeStudio-cli" / "timeline_line_orders.json",
    )
    parser.add_argument(
        "--runtime-audit",
        type=Path,
        default=ROOT / "reports" / "story" / "recovery" / "options" / "runtime_jump_option_route_audit_CN.json",
    )
    parser.add_argument("--reports-dir", type=Path, default=ROOT / "reports" / "story" / "recovery" / "options")
    parser.add_argument("--all-buckets", action="store_true", help="Include non-priority story buckets.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = build_report(
        args.language,
        args.timeline_orders,
        args.runtime_audit,
        args.reports_dir,
        priority_only=not args.all_buckets,
    )
    summary = result["summary"]["positiveSummary"]
    negative = result["summary"]["negativeSummary"]["runtimeAuditSummary"]
    print(f"Option route evidence controls: {result['markdown']}")
    print(f"Option route evidence data:     {result['json']}")
    print(
        "Positive controls "
        f"{summary['positiveRouteGroupCount']} groups / "
        f"{summary['positiveRouteEntryCount']} routes; "
        "negative controls "
        f"{negative.get('inferredFollowingLineGroupCount', 0)} groups / "
        f"{negative.get('groupsPassingNarrowRouteRule', 0)} strict passes."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
