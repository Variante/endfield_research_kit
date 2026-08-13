"""Pure projections for dialog Timeline warnings and debug evidence."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable


def build_duplicate_timestamp_warning(
    payload: dict,
    timeline_seconds_formatter: Callable[[float], str],
) -> dict | None:
    buckets: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for line in payload.get("lines") or []:
        if not isinstance(line, dict):
            continue
        ts = line.get("ts")
        if not isinstance(ts, (int, float)):
            continue
        debug = line.get("_debug") if isinstance(line.get("_debug"), dict) else {}
        timing_debug = debug.get("timelineTiming") if isinstance(debug, dict) else {}
        timeline = str(timing_debug.get("timeline") or "") if isinstance(timing_debug, dict) else ""
        buckets[(timeline, timeline_seconds_formatter(ts))].append(line)
    groups: list[dict] = []
    for (timeline, label), lines_for_ts in sorted(
        buckets.items(),
        key=lambda item: min(float(line.get("ts") or 0.0) for line in item[1]),
    ):
        if len(lines_for_ts) < 2:
            continue
        group = {
            "timestamp": label,
            "lineIds": [str(line.get("id") or "") for line in lines_for_ts if line.get("id")],
            "lines": [
                {
                    "id": str(line.get("id") or ""),
                    "actor": str(line.get("actor") or line.get("aid") or ""),
                    "ts": line.get("ts"),
                    "dur": line.get("dur"),
                }
                for line in lines_for_ts
                if line.get("id")
            ],
        }
        if timeline:
            group["timeline"] = timeline
        groups.append(group)
    if not groups:
        return None
    line_ids: list[str] = []
    for group in groups:
        for line_id in group["lineIds"]:
            if line_id not in line_ids:
                line_ids.append(line_id)
    return {
        "code": "duplicateTimestamps",
        "reason": "duplicateDisplayTimestamp",
        "detail": "two or more lines share the same WebUI timeline timestamp label within one timeline segment",
        "groups": groups,
        "lineIds": line_ids,
    }


def attach_duplicate_timestamp_warning(
    payload: dict,
    timeline_seconds_formatter: Callable[[float], str],
) -> None:
    warning = build_duplicate_timestamp_warning(payload, timeline_seconds_formatter)
    existing_warnings = [
        existing
        for existing in (payload.get("warnings") or [])
        if isinstance(existing, dict) and existing.get("code") != "duplicateTimestamps"
    ]
    if warning is None:
        if existing_warnings:
            payload["warnings"] = existing_warnings
        else:
            payload.pop("warnings", None)
        return
    payload["warnings"] = [*existing_warnings, warning]


def build_timeline_timestamp_regression_warning(
    payload: dict,
    timeline_seconds_formatter: Callable[[float], str],
) -> dict | None:
    timed_lines: list[dict] = []
    for idx, line in enumerate(payload.get("lines") or []):
        if not isinstance(line, dict):
            continue
        ts = line.get("ts")
        if not isinstance(ts, (int, float)):
            continue
        debug = line.get("_debug") if isinstance(line.get("_debug"), dict) else {}
        timing_debug = debug.get("timelineTiming") if isinstance(debug, dict) else {}
        timeline = str(timing_debug.get("timeline") or "") if isinstance(timing_debug, dict) else ""
        timed_lines.append({
            "index": idx,
            "id": str(line.get("id") or ""),
            "ts": float(ts),
            "timeline": timeline,
        })
    regressions: list[dict] = []
    for prev, cur in zip(timed_lines, timed_lines[1:]):
        if cur["ts"] + 1e-6 >= prev["ts"]:
            continue
        regressions.append({
            "prevLineId": prev["id"],
            "prevTimestamp": timeline_seconds_formatter(prev["ts"]),
            "prevTimeline": prev["timeline"],
            "lineId": cur["id"],
            "timestamp": timeline_seconds_formatter(cur["ts"]),
            "timeline": cur["timeline"],
        })
    if not regressions:
        return None
    line_ids: list[str] = []
    for row in regressions:
        for line_id in (row.get("prevLineId"), row.get("lineId")):
            if line_id and line_id not in line_ids:
                line_ids.append(line_id)
    timelines = sorted({row["timeline"] for row in timed_lines if row.get("timeline")})
    return {
        "code": "timelineTimestampRegression",
        "reason": "timelineTimestampsMoveBackward",
        "detail": "recovered Timeline timestamps move backward in rendered line order; secondary timelines may be local stitch evidence rather than absolute scene time",
        "lineIds": line_ids,
        "regressions": regressions,
        "timelines": timelines,
    }


def attach_timeline_timestamp_regression_warning(
    payload: dict,
    timeline_seconds_formatter: Callable[[float], str],
) -> None:
    warning = build_timeline_timestamp_regression_warning(payload, timeline_seconds_formatter)
    existing_warnings = [
        existing
        for existing in (payload.get("warnings") or [])
        if isinstance(existing, dict) and existing.get("code") != "timelineTimestampRegression"
    ]
    if warning is None:
        if existing_warnings:
            payload["warnings"] = existing_warnings
        else:
            payload.pop("warnings", None)
        return
    payload["warnings"] = [*existing_warnings, warning]


def attach_timeline_action_evidence(
    payload: dict,
    evidence_key: str,
    original_line_ids: list[str],
    current_line_ids: list[str],
    conversation_action_debug_builder: Callable[[str, list[str], list[str]], dict | None],
) -> None:
    action_debug = conversation_action_debug_builder(
        evidence_key,
        original_line_ids,
        current_line_ids,
    )
    if not action_debug:
        return
    debug = payload.setdefault("_debug", {})
    if not isinstance(debug, dict):
        debug = {}
        payload["_debug"] = debug
    debug["timelineActions"] = action_debug
    line_actions_by_id = {
        str(row.get("lineId") or ""): row
        for row in (action_debug.get("lineActions") or [])
        if isinstance(row, dict) and row.get("lineId")
    }
    if not line_actions_by_id:
        return
    for line in payload.get("lines") or []:
        if not isinstance(line, dict):
            continue
        line_id = str(line.get("id") or "")
        line_actions = line_actions_by_id.get(line_id)
        if not line_actions:
            continue
        line.setdefault("_debug", {})["timelineActions"] = line_actions


__all__ = [
    "attach_duplicate_timestamp_warning",
    "attach_timeline_action_evidence",
    "attach_timeline_timestamp_regression_warning",
    "build_duplicate_timestamp_warning",
    "build_timeline_timestamp_regression_warning",
]
