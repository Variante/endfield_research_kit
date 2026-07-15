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
import sys
from collections import Counter
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (_REPO_ROOT / "scripts",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))
from typing import Any

import build_option_playable_semantics_audit as semantics
from common import (
    ROOT,
    compact_dict,
    md_escape,
    parse_group_filters,
    read_json,
    safe_key,
    safe_report_suffix,
    split_csv_values,
    write_report_json as write_json,
)


EPSILON = 0.001
DEFAULT_IL2CPP_REPORT = (
    ROOT / "reports" / "story" / "recovery" / "options" / "option_flow_body_targets_gameassembly.json"
)


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
    return compact_dict(matches[0])


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
        "clipOptionIndex": line.get("clipOptionIndex"),
        "trackName": line.get("trackName"),
        "trackPathId": line.get("trackPathId"),
        "assetPathId": line.get("assetPathId"),
        "assetTrack": line.get("assetTrack"),
    }
    raw_clip = raw_clip_for_line(line, track_cache) if line else {}
    if raw_clip:
        out["rawClip"] = raw_clip
    return compact_dict(out)


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
    known_option_indices = [value for value in option_indices if value is not None]
    option_index_is_mixed = (
        bool(known_option_indices)
        and any(value == 0 for value in known_option_indices)
        and any(value != 0 for value in known_option_indices)
    )
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
    if option_index_is_mixed and raw_values and not nonzero_raw_values:
        return "mixedOptionIndexDefaultCandidateWindow", "doNotPromoteWithoutNonzeroTimelineClipOrJump"
    if raw_values and not nonzero_raw_values:
        if candidates_are_window_start:
            return "rawTrunkClipOptionIndexDefaultAdjacent", "doNotPromoteWithoutRuntimeRule"
        return "rawTrunkClipOptionIndexDefault", "needsRuntimeMethodBody"
    if len(tracks) > 1:
        return "multiTrackCandidateLayout", "inspectPlayableDirectorTrackBinding"
    if candidate_contiguous:
        return "linearCandidateWindow", "adjacencyOnly"
    return "timelineLayoutUnresolved", "needsRuntimeMethodBody"


def field_values_by_option(options: list[dict[str, Any]], field: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for option in options:
        option_id = safe_key(option.get("optionId"))
        value = as_int(option.get(field))
        if option_id and value is not None:
            out[option_id] = value
    return out


def candidate_raw_option_index_by_line(candidate_details: list[dict[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for detail in candidate_details:
        line_id = safe_key(detail.get("id"))
        value = as_int((detail.get("rawClip") or {}).get("optionIndex"))
        if line_id and value is not None:
            out[line_id] = value
    return out


def line_clip_option_index_by_line(line_details: list[dict[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for detail in line_details:
        line_id = safe_key(detail.get("id"))
        value = as_int(detail.get("clipOptionIndex"))
        if line_id and value is not None:
            out[line_id] = value
    return out


def integer_pattern(values: list[Any], *, expected_count: int | None = None) -> str:
    ints = [as_int(value) for value in values]
    ints = [value for value in ints if value is not None]
    if not ints:
        return "missing"
    if expected_count is not None and len(ints) < expected_count:
        return "partialMissing"
    has_zero = any(value == 0 for value in ints)
    has_nonzero = any(value != 0 for value in ints)
    if has_zero and has_nonzero:
        return "mixedZeroNonzero"
    if has_zero:
        return "allZero"
    if has_nonzero:
        return "strictNonzero"
    return "other"


def line_ids_by_index(line_ids: list[str], values_by_line: dict[str, int]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for line_id in line_ids:
        value = values_by_line.get(line_id)
        if value is None:
            continue
        out.setdefault(str(value), []).append(line_id)
    return out


def nonzero_coverage(nonzero_values: list[int], values_by_line: dict[str, int]) -> bool:
    if not nonzero_values:
        return False
    present = set(values_by_line.values())
    return all(value in present for value in nonzero_values)


def compact_runtime_route(route: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(route, dict) or not route:
        return {}
    out = {
        "source": route.get("source"),
        "groupKey": route.get("groupKey"),
        "optionIndex": route.get("optionIndex"),
        "start": route.get("start"),
        "end": route.get("end"),
        "pathLineIds": route.get("pathLineIds") or [],
        "skippedLineIds": route.get("skippedLineIds") or [],
        "reverseRangeLineIds": route.get("reverseRangeLineIds") or [],
        "continuationGroupKey": route.get("continuationGroupKey"),
        "continuationOptionIds": route.get("continuationOptionIds") or [],
        "skipRanges": route.get("skipRanges") or [],
        "reverseRanges": route.get("reverseRanges") or [],
    }
    return compact_dict(out, empty_values=(None, "", [], {}))


def compact_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_il2cpp_option_flow_facts(report_path: Path | None) -> dict[str, Any]:
    if not report_path:
        return {}
    path = report_path
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        return {
            "source": compact_path(path),
            "missing": True,
            "factCount": 0,
            "factKindCounts": {},
            "facts": [],
        }
    payload = read_json(path, {}) or {}
    facts: list[dict[str, Any]] = []
    for target in payload.get("bodyTargets") or []:
        if not isinstance(target, dict):
            continue
        body_summary = target.get("methodBodySummary")
        if not isinstance(body_summary, dict):
            continue
        for fact in body_summary.get("optionFlowFacts") or []:
            if not isinstance(fact, dict):
                continue
            facts.append(compact_dict({
                "type": target.get("type"),
                "method": target.get("method"),
                "kind": fact.get("kind"),
                "summary": fact.get("summary"),
            }))
    kind_counts = Counter(safe_key(fact.get("kind")) or "unknown" for fact in facts)
    return {
        "source": compact_path(path),
        "missing": False,
        "factCount": len(facts),
        "factKindCounts": dict(sorted(kind_counts.items())),
        "facts": facts,
    }


def runtime_value_by_line(
    line_ids: list[str],
    raw_by_line: dict[str, int],
    clip_by_line: dict[str, int],
) -> dict[str, int]:
    out: dict[str, int] = {}
    for line_id in line_ids:
        if line_id in raw_by_line:
            out[line_id] = raw_by_line[line_id]
        elif line_id in clip_by_line:
            out[line_id] = clip_by_line[line_id]
    return out


def line_ids_with_nonzero(values_by_line: dict[str, int]) -> list[str]:
    return [line_id for line_id, value in values_by_line.items() if value != 0]


def option_clip_timing(option_rows: list[dict[str, Any]], candidate_details: list[dict[str, Any]]) -> dict[str, Any]:
    option_starts: list[float] = []
    option_ends: list[float] = []
    for row in option_rows:
        start = as_float(row.get("start"))
        duration = as_float(row.get("duration")) or 0.0
        if start is None:
            continue
        option_starts.append(start)
        option_ends.append(start + duration)
    candidate_starts = [
        start
        for detail in candidate_details
        if (start := as_float(detail.get("start"))) is not None
    ]
    option_start = min(option_starts) if option_starts else None
    option_end = max(option_ends) if option_ends else None
    first_candidate_start = min(candidate_starts) if candidate_starts else None
    gap = None
    if option_end is not None and first_candidate_start is not None:
        gap = first_candidate_start - option_end
    return compact_dict({
        "optionClipStart": round(option_start, 6) if option_start is not None else None,
        "optionClipEnd": round(option_end, 6) if option_end is not None else None,
        "firstCandidateStart": round(first_candidate_start, 6) if first_candidate_start is not None else None,
        "optionClipToFirstCandidateGap": round(gap, 6) if gap is not None else None,
    }, empty_values=(None, "", [], {}))


def compact_timeline_option_context_row(row: dict[str, Any]) -> dict[str, Any]:
    return compact_dict({
        "optionId": row.get("id"),
        "groupKey": row.get("groupKey"),
        "optionIndex": row.get("optionIndex"),
        "clipOptionIndex": row.get("clipOptionIndex"),
        "index": row.get("index"),
        "anchorMode": row.get("anchorMode"),
        "anchorLineId": row.get("anchorLineId"),
        "start": row.get("start"),
        "duration": row.get("duration"),
        "trackName": row.get("trackName"),
        "trackPathId": row.get("trackPathId"),
        "assetTrack": row.get("assetTrack"),
    }, empty_values=(None, "", [], {}))


def dedupe_context_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        key = (
            row.get("optionId"),
            row.get("groupKey"),
            row.get("optionIndex"),
            row.get("anchorMode"),
            row.get("anchorLineId"),
            row.get("start"),
            row.get("assetTrack"),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def window_other_option_context(
    timeline_option_rows: list[dict[str, Any]],
    current_option_ids: list[str],
    candidate_ids: list[str],
    common_id: str,
    window_ids: list[str],
    window_runtime_by_line: dict[str, int],
) -> dict[str, Any]:
    current_option_set = set(current_option_ids)
    candidate_set = set(candidate_ids)
    window_set = set(window_ids)
    other_rows = [
        row
        for row in timeline_option_rows
        if isinstance(row, dict)
        and safe_key(row.get("id"))
        and safe_key(row.get("id")) not in current_option_set
    ]
    anchor_rows_by_line: dict[str, list[dict[str, Any]]] = {}
    for row in other_rows:
        anchor_line_id = safe_key(row.get("anchorLineId"))
        if anchor_line_id in window_set:
            anchor_rows_by_line.setdefault(anchor_line_id, []).append(
                compact_timeline_option_context_row(row)
            )
    runtime_rows_by_line: dict[str, list[dict[str, Any]]] = {}
    for line_id in window_ids:
        value = window_runtime_by_line.get(line_id)
        if value in (None, 0):
            continue
        for row in other_rows:
            if as_int(row.get("optionIndex")) == value:
                runtime_rows_by_line.setdefault(line_id, []).append(
                    compact_timeline_option_context_row(row)
                )
    anchor_rows_by_line = {
        line_id: dedupe_context_rows(rows)
        for line_id, rows in anchor_rows_by_line.items()
        if rows
    }
    runtime_rows_by_line = {
        line_id: dedupe_context_rows(rows)
        for line_id, rows in runtime_rows_by_line.items()
        if rows
    }
    candidate_anchor_line_ids = [
        line_id for line_id in candidate_ids if line_id in anchor_rows_by_line
    ]
    common_runtime_rows = runtime_rows_by_line.get(common_id) or []
    if not candidate_anchor_line_ids and not anchor_rows_by_line and not runtime_rows_by_line:
        return {}
    out = {
        "candidateLineIdsUsedAsOtherOptionAnchors": candidate_anchor_line_ids,
        "anchorRowsByWindowLine": anchor_rows_by_line,
        "runtimeOptionRowsByWindowLine": runtime_rows_by_line,
        "commonContinuationRuntimeOptionRows": common_runtime_rows,
    }
    if common_runtime_rows:
        out["commonContinuationRuntimeMatchesOtherOptionRows"] = True
    if runtime_rows_by_line:
        out["windowRuntimeFieldExplainedByOtherOptionRows"] = True
    return compact_dict(out, empty_values=(None, "", [], {}))


def runtime_gate_evidence(
    option_rows: list[dict[str, Any]],
    candidate_ids: list[str],
    window_ids: list[str],
    candidate_details: list[dict[str, Any]],
    raw_by_line: dict[str, int],
    raw_by_window_line: dict[str, int],
    clip_by_line: dict[str, int],
    clip_by_window_line: dict[str, int],
) -> dict[str, Any]:
    option_indices = field_values_by_option(option_rows, "optionIndex")
    option_index_values = list(option_indices.values())
    option_pattern = integer_pattern(option_index_values, expected_count=len(option_rows))
    candidate_runtime = runtime_value_by_line(candidate_ids, raw_by_line, clip_by_line)
    window_runtime = runtime_value_by_line(window_ids, raw_by_window_line, clip_by_window_line)
    candidate_runtime_values = [candidate_runtime[line_id] for line_id in candidate_ids if line_id in candidate_runtime]
    window_runtime_values = [window_runtime[line_id] for line_id in window_ids if line_id in window_runtime]
    candidate_runtime_pattern = integer_pattern(candidate_runtime_values, expected_count=len(candidate_ids))
    window_runtime_pattern = integer_pattern(window_runtime_values)
    nonzero_candidate_ids = line_ids_with_nonzero(candidate_runtime)
    nonzero_window_ids = line_ids_with_nonzero(window_runtime)
    candidate_set = set(candidate_ids)
    nonzero_window_outside_candidates = [
        line_id for line_id in nonzero_window_ids if line_id not in candidate_set
    ]
    candidate_all_zero = bool(candidate_runtime_values) and candidate_runtime_pattern == "allZero"
    candidate_nonzero_matches = (
        bool(candidate_runtime_values)
        and len(candidate_runtime_values) == len(option_index_values)
        and set(candidate_runtime_values) == set(option_index_values)
        and any(value != 0 for value in candidate_runtime_values)
    )

    if candidate_nonzero_matches:
        verdict = "candidateRuntimeFieldMapsOptions"
    elif option_pattern == "strictNonzero" and candidate_all_zero:
        verdict = "strictOptionRowsButAllZeroCandidateRuntimeField"
    elif option_pattern == "mixedZeroNonzero" and candidate_all_zero:
        verdict = "mixedOptionRowsWithAllZeroCandidateRuntimeField"
    elif option_pattern == "allZero" and candidate_all_zero:
        verdict = "allZeroSharedContinuationCandidate"
    elif candidate_runtime_pattern == "missing":
        verdict = "missingCandidateRuntimeField"
    elif nonzero_candidate_ids:
        verdict = "candidateRuntimeFieldHasNonzeroButNoCompleteMap"
    else:
        verdict = "candidateRuntimeFieldUnresolved"

    return compact_dict({
        "source": "IL2CPP optionFlowFacts: selected option +0x98 becomes runtime +0x18; active branch clips require positive +0x18",
        "verdict": verdict,
        "optionIndexPattern": option_pattern,
        "candidateRuntimeFieldPattern": candidate_runtime_pattern,
        "windowRuntimeFieldPattern": window_runtime_pattern,
        "candidateRuntimeFieldByLine": candidate_runtime,
        "windowRuntimeFieldByLine": window_runtime,
        "nonzeroCandidateLineIds": nonzero_candidate_ids,
        "nonzeroWindowLineIds": nonzero_window_ids,
        "nonzeroWindowLineIdsOutsideCandidates": nonzero_window_outside_candidates,
        "candidateRuntimeFieldAllZero": candidate_all_zero,
        "candidateRuntimeFieldMapsOptionIndices": candidate_nonzero_matches,
        "timing": option_clip_timing(option_rows, candidate_details),
    }, empty_values=(None, "", [], {}))


def window_pattern(
    option_rows: list[dict[str, Any]],
    candidate_details: list[dict[str, Any]],
    window_details: list[dict[str, Any]],
    window_ids: list[str],
    common_id: str,
    timeline_option_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    candidate_ids = [safe_key(detail.get("id")) for detail in candidate_details if safe_key(detail.get("id"))]
    candidate_set = set(candidate_ids)
    candidate_positions = {
        line_id: window_ids.index(line_id)
        for line_id in candidate_ids
        if line_id in window_ids
    }
    candidate_offsets_by_option: dict[str, int] = {}
    for option, candidate_id in zip(option_rows, candidate_ids):
        option_id = safe_key(option.get("optionId"))
        if option_id and candidate_id in candidate_positions:
            candidate_offsets_by_option[option_id] = candidate_positions[candidate_id]
    raw_by_line = candidate_raw_option_index_by_line(candidate_details)
    raw_by_window_line = candidate_raw_option_index_by_line(window_details)
    clip_by_line = line_clip_option_index_by_line(candidate_details)
    clip_by_window_line = line_clip_option_index_by_line(window_details)
    window_runtime_by_line = runtime_value_by_line(window_ids, raw_by_window_line, clip_by_window_line)
    runtime_gate = runtime_gate_evidence(
        option_rows,
        candidate_ids,
        window_ids,
        candidate_details,
        raw_by_line,
        raw_by_window_line,
        clip_by_line,
        clip_by_window_line,
    )
    other_option_context = window_other_option_context(
        timeline_option_rows,
        [safe_key(row.get("optionId")) for row in option_rows if safe_key(row.get("optionId"))],
        candidate_ids,
        common_id,
        window_ids,
        window_runtime_by_line,
    )
    raw_by_option: dict[str, int] = {}
    for option, candidate_id in zip(option_rows, candidate_ids):
        option_id = safe_key(option.get("optionId"))
        if option_id and candidate_id in raw_by_line:
            raw_by_option[option_id] = raw_by_line[candidate_id]

    candidate_contiguous = bool(candidate_ids) and candidate_ids == [
        line_id for line_id in window_ids if line_id in candidate_set
    ]
    candidates_at_window_start = bool(candidate_ids) and window_ids[: len(candidate_ids)] == candidate_ids
    option_indices = field_values_by_option(option_rows, "optionIndex")
    clip_indices = field_values_by_option(option_rows, "clipOptionIndex")
    logic_ids = field_values_by_option(option_rows, "logicId")
    option_index_values = list(option_indices.values())
    nonzero_option_index_values = sorted({value for value in option_index_values if value != 0})
    zero_option_ids = [
        safe_key(option.get("optionId"))
        for option in option_rows
        if safe_key(option.get("optionId")) and as_int(option.get("optionIndex")) == 0
    ]
    nonzero_option_ids = [
        safe_key(option.get("optionId"))
        for option in option_rows
        if safe_key(option.get("optionId")) and (as_int(option.get("optionIndex")) or 0) != 0
    ]
    option_run_line_ids_by_option: dict[str, list[str]] = {}
    for option in option_rows:
        option_id = safe_key(option.get("optionId"))
        option_index = as_int(option.get("optionIndex"))
        if not option_id or option_index in (None, 0):
            continue
        for line_id in window_ids:
            if line_id == common_id:
                break
            if raw_by_window_line.get(line_id) == option_index:
                option_run_line_ids_by_option.setdefault(option_id, []).append(line_id)
    extended_option_runs = any(len(line_ids) > 1 for line_ids in option_run_line_ids_by_option.values())
    raw_index_matches_option_index = (
        bool(raw_by_option)
        and len(raw_by_option) == len(option_indices)
        and set(raw_by_option.values()) == set(option_indices.values())
    )
    raw_index_has_nonzero = any(value != 0 for value in raw_by_option.values())
    logic_values = list(logic_ids.values())
    logic_id_contiguous = (
        len(logic_values) > 1
        and all(logic_values[index] + 1 == logic_values[index + 1] for index in range(len(logic_values) - 1))
    )

    return compact_dict({
        "windowLength": len(window_ids),
        "candidateContiguous": candidate_contiguous,
        "candidatesAtWindowStart": candidates_at_window_start,
        "commonOffset": window_ids.index(common_id) if common_id in window_ids else None,
        "candidateOffsetsByOption": candidate_offsets_by_option,
        "rawClipOptionIndexByLine": raw_by_line,
        "rawClipOptionIndexByWindowLine": raw_by_window_line,
        "rawClipOptionIndexByOption": raw_by_option,
        "clipOptionIndexByLine": clip_by_line,
        "clipOptionIndexByWindowLine": clip_by_window_line,
        "rawClipOptionIndexLineIdsByIndex": line_ids_by_index(candidate_ids, raw_by_line),
        "rawClipOptionIndexWindowLineIdsByIndex": line_ids_by_index(window_ids, raw_by_window_line),
        "clipOptionIndexLineIdsByIndex": line_ids_by_index(candidate_ids, clip_by_line),
        "clipOptionIndexWindowLineIdsByIndex": line_ids_by_index(window_ids, clip_by_window_line),
        "runtimeGate": runtime_gate,
        "otherOptionContext": other_option_context,
        "rawIndexMatchesOptionIndexSet": raw_index_matches_option_index,
        "nonzeroRawIndexMatchesOptionIndexSet": raw_index_matches_option_index and raw_index_has_nonzero,
        "optionRunLineIdsByOption": option_run_line_ids_by_option,
        "extendedOptionRuns": extended_option_runs,
        "optionIndexByOption": option_indices,
        "clipOptionIndexByOption": clip_indices,
        "logicIdByOption": logic_ids,
        "logicIdContiguous": logic_id_contiguous,
        "optionIndexPattern": integer_pattern(option_index_values, expected_count=len(option_rows)),
        "candidateRawClipOptionIndexPattern": integer_pattern(
            list(raw_by_line.values()),
            expected_count=len(candidate_ids),
        ),
        "windowRawClipOptionIndexPattern": integer_pattern(list(raw_by_window_line.values())),
        "candidateClipOptionIndexPattern": integer_pattern(
            list(clip_by_line.values()),
            expected_count=len(candidate_ids),
        ),
        "windowClipOptionIndexPattern": integer_pattern(list(clip_by_window_line.values())),
        "zeroOptionIds": zero_option_ids,
        "nonzeroOptionIds": nonzero_option_ids,
        "nonzeroOptionIndexValues": nonzero_option_index_values,
        "nonzeroOptionIndexCoveredByCandidateRawClip": nonzero_coverage(nonzero_option_index_values, raw_by_line),
        "nonzeroOptionIndexCoveredByWindowRawClip": nonzero_coverage(nonzero_option_index_values, raw_by_window_line),
        "nonzeroOptionIndexCoveredByCandidateClip": nonzero_coverage(nonzero_option_index_values, clip_by_line),
        "nonzeroOptionIndexCoveredByWindowClip": nonzero_coverage(nonzero_option_index_values, clip_by_window_line),
        "candidateTrackNames": sorted({
            safe_key(detail.get("trackName"))
            for detail in candidate_details
            if safe_key(detail.get("trackName"))
        }),
        "candidateTrackPathIds": sorted({
            safe_key(detail.get("trackPathId"))
            for detail in candidate_details
            if safe_key(detail.get("trackPathId"))
        }),
    }, empty_values=(None, "", [], {}))


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
        pattern = window_pattern(
            option_rows,
            candidate_details,
            window_details,
            window_ids,
            common_id,
            entry.get("options") if isinstance(entry.get("options"), list) else [],
        )
        routes = entry.get("optionRoutes") if isinstance(entry.get("optionRoutes"), dict) else {}
        nearby_runtime_routes = {
            option_id: route
            for option_id in option_ids
            if (route := compact_runtime_route(routes.get(option_id) or {}))
        }
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
            "windowPattern": pattern,
            "windowLineIds": window_ids,
            "windowLines": window_details,
            "nearbyRuntimeRoutes": nearby_runtime_routes,
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
    groups_with_candidate_contiguous = 0
    groups_with_candidates_at_window_start = 0
    groups_with_raw_option_index_mapping = 0
    groups_with_nonzero_raw_option_index_mapping = 0
    groups_with_extended_option_runs = 0
    groups_with_contiguous_logic_ids = 0
    option_index_patterns: Counter[str] = Counter()
    candidate_raw_patterns: Counter[str] = Counter()
    window_raw_patterns: Counter[str] = Counter()
    candidate_clip_patterns: Counter[str] = Counter()
    window_clip_patterns: Counter[str] = Counter()
    groups_with_mixed_option_index = 0
    mixed_groups_with_nonzero_candidate_raw_coverage = 0
    mixed_groups_with_nonzero_window_raw_coverage = 0
    mixed_groups_with_nonzero_candidate_clip_coverage = 0
    mixed_groups_with_nonzero_window_clip_coverage = 0
    mixed_groups_with_runtime_route = 0
    runtime_gate_verdicts: Counter[str] = Counter()
    groups_with_candidate_runtime_all_zero = 0
    groups_with_candidate_runtime_mapping = 0
    groups_with_nonzero_window_runtime_outside_candidates = 0
    groups_with_candidate_line_used_as_other_option_anchor = 0
    groups_with_common_runtime_matching_other_option = 0
    groups_with_window_runtime_explained_by_other_option = 0
    for row in rows:
        pattern = row.get("windowPattern") or {}
        option_pattern = safe_key(pattern.get("optionIndexPattern")) or "missing"
        candidate_raw_pattern = safe_key(pattern.get("candidateRawClipOptionIndexPattern")) or "missing"
        window_raw_pattern = safe_key(pattern.get("windowRawClipOptionIndexPattern")) or "missing"
        candidate_clip_pattern = safe_key(pattern.get("candidateClipOptionIndexPattern")) or "missing"
        window_clip_pattern = safe_key(pattern.get("windowClipOptionIndexPattern")) or "missing"
        runtime_gate = pattern.get("runtimeGate") if isinstance(pattern.get("runtimeGate"), dict) else {}
        runtime_gate_verdict = safe_key(runtime_gate.get("verdict")) or "missing"
        runtime_gate_verdicts[runtime_gate_verdict] += 1
        if runtime_gate.get("candidateRuntimeFieldAllZero"):
            groups_with_candidate_runtime_all_zero += 1
        if runtime_gate.get("candidateRuntimeFieldMapsOptionIndices"):
            groups_with_candidate_runtime_mapping += 1
        if runtime_gate.get("nonzeroWindowLineIdsOutsideCandidates"):
            groups_with_nonzero_window_runtime_outside_candidates += 1
        other_option_context = (
            pattern.get("otherOptionContext")
            if isinstance(pattern.get("otherOptionContext"), dict)
            else {}
        )
        if other_option_context.get("candidateLineIdsUsedAsOtherOptionAnchors"):
            groups_with_candidate_line_used_as_other_option_anchor += 1
        if other_option_context.get("commonContinuationRuntimeMatchesOtherOptionRows"):
            groups_with_common_runtime_matching_other_option += 1
        if other_option_context.get("windowRuntimeFieldExplainedByOtherOptionRows"):
            groups_with_window_runtime_explained_by_other_option += 1
        option_index_patterns[option_pattern] += 1
        candidate_raw_patterns[candidate_raw_pattern] += 1
        window_raw_patterns[window_raw_pattern] += 1
        candidate_clip_patterns[candidate_clip_pattern] += 1
        window_clip_patterns[window_clip_pattern] += 1
        if option_pattern == "mixedZeroNonzero":
            groups_with_mixed_option_index += 1
            if pattern.get("nonzeroOptionIndexCoveredByCandidateRawClip"):
                mixed_groups_with_nonzero_candidate_raw_coverage += 1
            if pattern.get("nonzeroOptionIndexCoveredByWindowRawClip"):
                mixed_groups_with_nonzero_window_raw_coverage += 1
            if pattern.get("nonzeroOptionIndexCoveredByCandidateClip"):
                mixed_groups_with_nonzero_candidate_clip_coverage += 1
            if pattern.get("nonzeroOptionIndexCoveredByWindowClip"):
                mixed_groups_with_nonzero_window_clip_coverage += 1
            if row.get("nearbyRuntimeRoutes"):
                mixed_groups_with_runtime_route += 1
        if pattern.get("candidateContiguous"):
            groups_with_candidate_contiguous += 1
        if pattern.get("candidatesAtWindowStart"):
            groups_with_candidates_at_window_start += 1
        if pattern.get("rawIndexMatchesOptionIndexSet"):
            groups_with_raw_option_index_mapping += 1
        if pattern.get("nonzeroRawIndexMatchesOptionIndexSet"):
            groups_with_nonzero_raw_option_index_mapping += 1
        if pattern.get("extendedOptionRuns"):
            groups_with_extended_option_runs += 1
        if pattern.get("logicIdContiguous"):
            groups_with_contiguous_logic_ids += 1
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
        "groupsWithCandidateContiguousWindow": groups_with_candidate_contiguous,
        "groupsWithCandidatesAtWindowStart": groups_with_candidates_at_window_start,
        "groupsWithRawOptionIndexMapping": groups_with_raw_option_index_mapping,
        "groupsWithNonzeroRawOptionIndexMapping": groups_with_nonzero_raw_option_index_mapping,
        "groupsWithExtendedOptionRuns": groups_with_extended_option_runs,
        "groupsWithContiguousLogicIds": groups_with_contiguous_logic_ids,
        "optionIndexPatternCounts": dict(sorted(option_index_patterns.items())),
        "candidateRawClipOptionIndexPatternCounts": dict(sorted(candidate_raw_patterns.items())),
        "windowRawClipOptionIndexPatternCounts": dict(sorted(window_raw_patterns.items())),
        "candidateClipOptionIndexPatternCounts": dict(sorted(candidate_clip_patterns.items())),
        "windowClipOptionIndexPatternCounts": dict(sorted(window_clip_patterns.items())),
        "groupsWithMixedZeroNonzeroOptionIndex": groups_with_mixed_option_index,
        "mixedGroupsWithNonzeroCandidateRawCoverage": mixed_groups_with_nonzero_candidate_raw_coverage,
        "mixedGroupsWithNonzeroWindowRawCoverage": mixed_groups_with_nonzero_window_raw_coverage,
        "mixedGroupsWithNonzeroCandidateClipCoverage": mixed_groups_with_nonzero_candidate_clip_coverage,
        "mixedGroupsWithNonzeroWindowClipCoverage": mixed_groups_with_nonzero_window_clip_coverage,
        "mixedGroupsWithRuntimeRoute": mixed_groups_with_runtime_route,
        "runtimeGateVerdictCounts": dict(sorted(runtime_gate_verdicts.items())),
        "groupsWithCandidateRuntimeFieldAllZero": groups_with_candidate_runtime_all_zero,
        "groupsWithCandidateRuntimeFieldMapping": groups_with_candidate_runtime_mapping,
        "groupsWithNonzeroWindowRuntimeFieldOutsideCandidates": groups_with_nonzero_window_runtime_outside_candidates,
        "groupsWithCandidateLineUsedAsOtherOptionAnchor": groups_with_candidate_line_used_as_other_option_anchor,
        "groupsWithCommonRuntimeMatchingOtherOption": groups_with_common_runtime_matching_other_option,
        "groupsWithWindowRuntimeExplainedByOtherOption": groups_with_window_runtime_explained_by_other_option,
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


def window_summary(row: dict[str, Any]) -> str:
    pattern = row.get("windowPattern") or {}
    if not isinstance(pattern, dict):
        return ""
    parts: list[str] = []
    if pattern.get("windowLength") is not None:
        parts.append(f"window={pattern.get('windowLength')}")
    if pattern.get("candidateContiguous"):
        parts.append("contiguous")
    if pattern.get("candidatesAtWindowStart"):
        parts.append("startsWindow")
    if pattern.get("commonOffset") is not None:
        parts.append(f"common@{pattern.get('commonOffset')}")
    if pattern.get("optionIndexPattern"):
        parts.append(f"optPattern={pattern.get('optionIndexPattern')}")
    if pattern.get("candidateClipOptionIndexPattern"):
        parts.append(f"candClip={pattern.get('candidateClipOptionIndexPattern')}")
    if pattern.get("windowClipOptionIndexPattern"):
        parts.append(f"winClip={pattern.get('windowClipOptionIndexPattern')}")
    if pattern.get("candidateRawClipOptionIndexPattern"):
        parts.append(f"candRaw={pattern.get('candidateRawClipOptionIndexPattern')}")
    if pattern.get("windowRawClipOptionIndexPattern"):
        parts.append(f"winRaw={pattern.get('windowRawClipOptionIndexPattern')}")
    runtime_gate = pattern.get("runtimeGate") if isinstance(pattern.get("runtimeGate"), dict) else {}
    if runtime_gate.get("verdict"):
        parts.append(f"runtimeGate={runtime_gate.get('verdict')}")
    outside_ids = runtime_gate.get("nonzeroWindowLineIdsOutsideCandidates") or []
    if outside_ids:
        parts.append("nonzeroOutside=" + ",".join(outside_ids))
    other_option_context = (
        pattern.get("otherOptionContext")
        if isinstance(pattern.get("otherOptionContext"), dict)
        else {}
    )
    candidate_anchor_ids = other_option_context.get("candidateLineIdsUsedAsOtherOptionAnchors") or []
    if candidate_anchor_ids:
        parts.append("candidateAnchorsOtherOption=" + ",".join(candidate_anchor_ids))
    runtime_rows_by_line = other_option_context.get("runtimeOptionRowsByWindowLine") or {}
    if runtime_rows_by_line:
        runtime_bits: list[str] = []
        for line_id, rows in runtime_rows_by_line.items():
            option_ids = [
                safe_key(row.get("optionId"))
                for row in rows
                if isinstance(row, dict) and safe_key(row.get("optionId"))
            ]
            option_ids = list(dict.fromkeys(option_ids))
            if option_ids:
                runtime_bits.append(f"{line_id}->{'/'.join(option_ids)}")
        if runtime_bits:
            parts.append("runtimeMatchesOtherOption=" + ",".join(runtime_bits))
    if pattern.get("nonzeroOptionIndexCoveredByCandidateClip"):
        parts.append("nonzeroCandClipCovered")
    if pattern.get("nonzeroOptionIndexCoveredByWindowClip"):
        parts.append("nonzeroWinClipCovered")
    if pattern.get("nonzeroOptionIndexCoveredByCandidateRawClip"):
        parts.append("nonzeroCandRawCovered")
    if pattern.get("nonzeroOptionIndexCoveredByWindowRawClip"):
        parts.append("nonzeroWinRawCovered")
    offsets = pattern.get("candidateOffsetsByOption") or {}
    if offsets:
        parts.append(
            "offsets="
            + ",".join(f"{option_id}:{offset}" for option_id, offset in offsets.items())
        )
    raw_by_option = pattern.get("rawClipOptionIndexByOption") or {}
    if raw_by_option:
        parts.append(
            "raw="
            + ",".join(f"{option_id}:{value}" for option_id, value in raw_by_option.items())
        )
    if pattern.get("rawIndexMatchesOptionIndexSet"):
        parts.append("rawMatchesOptIdx")
    if pattern.get("nonzeroRawIndexMatchesOptionIndexSet"):
        parts.append("nonzeroRawMatch")
    option_runs = pattern.get("optionRunLineIdsByOption") or {}
    if option_runs:
        parts.append(
            "runs="
            + ",".join(
                f"{option_id}:{'/'.join(line_ids)}"
                for option_id, line_ids in option_runs.items()
            )
        )
    if pattern.get("extendedOptionRuns"):
        parts.append("extendedRuns")
    if pattern.get("logicIdContiguous"):
        parts.append("logicContiguous")
    return "; ".join(parts)


def runtime_route_summary(row: dict[str, Any]) -> str:
    routes = row.get("nearbyRuntimeRoutes") if isinstance(row.get("nearbyRuntimeRoutes"), dict) else {}
    if not routes:
        return "none"
    parts: list[str] = []
    for option_id, route in routes.items():
        path_ids = route.get("pathLineIds") or []
        skipped_ids = route.get("skippedLineIds") or []
        route_parts = [
            f"idx={route.get('optionIndex')}",
            f"path={','.join(path_ids[:4])}",
        ]
        if len(path_ids) > 4:
            route_parts.append(f"+{len(path_ids) - 4}")
        if skipped_ids:
            route_parts.append(f"skip={','.join(skipped_ids[:4])}")
            if len(skipped_ids) > 4:
                route_parts.append(f"+{len(skipped_ids) - 4}")
        parts.append(f"{option_id} ({'; '.join(route_parts)})")
    return "; ".join(parts)


def render_markdown(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = [
        f"# Timeline Option Flow Audit - {summary['language']}",
        "",
        f"- Inferred response groups audited: `{summary['inferredResponseGroupCount']}`",
        f"- Groups with nonzero candidate trunk raw `optionIndex`: `{summary['groupsWithNonzeroCandidateRawClipOptionIndex']}`",
        f"- Candidate trunk raw `optionIndex` counts: `{summary['candidateRawClipOptionIndexCounts']}`",
        f"- Groups with candidate lines contiguous in the audited window: `{summary['groupsWithCandidateContiguousWindow']}`",
        f"- Groups where candidate lines start the audited window: `{summary['groupsWithCandidatesAtWindowStart']}`",
        f"- Groups where raw candidate `optionIndex` set matches option rows: `{summary['groupsWithRawOptionIndexMapping']}`",
        f"- Groups where nonzero raw candidate `optionIndex` matches option rows: `{summary['groupsWithNonzeroRawOptionIndexMapping']}`",
        f"- Groups with extended same-index option runs: `{summary['groupsWithExtendedOptionRuns']}`",
        f"- Groups with contiguous best-row `logicId` values: `{summary['groupsWithContiguousLogicIds']}`",
        f"- Option row `optionIndex` patterns: `{summary.get('optionIndexPatternCounts', {})}`",
        f"- Candidate line raw `optionIndex` patterns: `{summary.get('candidateRawClipOptionIndexPatternCounts', {})}`",
        f"- Window line raw `optionIndex` patterns: `{summary.get('windowRawClipOptionIndexPatternCounts', {})}`",
        f"- Candidate line `clipOptionIndex` patterns: `{summary.get('candidateClipOptionIndexPatternCounts', {})}`",
        f"- Window line `clipOptionIndex` patterns: `{summary.get('windowClipOptionIndexPatternCounts', {})}`",
        f"- Mixed `[0, nonzero]` option groups: `{summary.get('groupsWithMixedZeroNonzeroOptionIndex', 0)}`",
        f"- Mixed groups with nonzero candidate/window raw coverage: "
        f"`{summary.get('mixedGroupsWithNonzeroCandidateRawCoverage', 0)}` / "
        f"`{summary.get('mixedGroupsWithNonzeroWindowRawCoverage', 0)}`",
        f"- Mixed groups with nonzero candidate/window clip coverage: "
        f"`{summary.get('mixedGroupsWithNonzeroCandidateClipCoverage', 0)}` / "
        f"`{summary.get('mixedGroupsWithNonzeroWindowClipCoverage', 0)}`",
        f"- Mixed groups with recovered Runtime Jump routes: `{summary.get('mixedGroupsWithRuntimeRoute', 0)}`",
        f"- Runtime gate verdicts: `{summary.get('runtimeGateVerdictCounts', {})}`",
        f"- Groups with all-zero candidate runtime fields: "
        f"`{summary.get('groupsWithCandidateRuntimeFieldAllZero', 0)}`",
        f"- Groups with nonzero window runtime fields outside candidate lines: "
        f"`{summary.get('groupsWithNonzeroWindowRuntimeFieldOutsideCandidates', 0)}`",
        f"- Groups where candidate lines anchor another option group: "
        f"`{summary.get('groupsWithCandidateLineUsedAsOtherOptionAnchor', 0)}`",
        f"- Groups where common continuation runtime field matches another option row: "
        f"`{summary.get('groupsWithCommonRuntimeMatchingOtherOption', 0)}`",
        f"- Groups where nonzero window runtime fields are explained by another option row: "
        f"`{summary.get('groupsWithWindowRuntimeExplainedByOtherOption', 0)}`",
        "",
        "## Classification Counts",
        "",
    ]
    for key, count in summary.get("classificationCounts", {}).items():
        lines.append(f"- `{key}`: {count}")
    lines.extend(["", "## Recommendation Counts", ""])
    for key, count in summary.get("recommendationCounts", {}).items():
        lines.append(f"- `{key}`: {count}")
    il2cpp_summary = summary.get("il2cppOptionFlow") if isinstance(summary.get("il2cppOptionFlow"), dict) else {}
    if il2cpp_summary:
        lines.extend(["", "## IL2CPP Option Flow Facts", ""])
        lines.append(
            f"- Source: `{md_escape(il2cpp_summary.get('source'))}`; "
            f"facts: `{il2cpp_summary.get('factCount', 0)}`; "
            f"kinds: `{il2cpp_summary.get('factKindCounts', {})}`"
        )
        if il2cpp_summary.get("missing"):
            lines.append("- IL2CPP report is missing; runtime gate verdicts use the built-in field interpretation only.")
        for fact in il2cpp_summary.get("facts") or []:
            lines.append(
                f"- `{md_escape(fact.get('type'))}.{md_escape(fact.get('method'))}` "
                f"`{md_escape(fact.get('kind'))}`: {md_escape(fact.get('summary'))}"
            )
    lines.extend([
        "",
        "## Groups",
        "",
        "| Scene | Group | After | Candidates | Common | Class | Recommendation | Window | Runtime routes | Clip evidence |",
        "| --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- |",
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
            f"| `{md_escape(window_summary(row))}` "
            f"| {md_escape(runtime_route_summary(row))} "
            f"| {md_escape(option_summary(row))} |"
        )
    if not rows:
        lines.append("| _(none)_ |  |  |  |  |  |  |  |  |  |")
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
    il2cpp_report_path: Path | None = DEFAULT_IL2CPP_REPORT,
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
    summary["il2cppOptionFlow"] = load_il2cpp_option_flow_facts(il2cpp_report_path)
    payload = {
        "summary": summary,
        "groups": rows,
    }
    reports_dir.mkdir(parents=True, exist_ok=True)
    suffix = safe_report_suffix(story_filters or [], group_filters or set(), only_interesting)
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
    parser.add_argument("--reports-dir", type=Path, default=ROOT / "reports" / "story" / "recovery" / "options")
    parser.add_argument(
        "--il2cpp-report",
        type=Path,
        default=DEFAULT_IL2CPP_REPORT,
        help="Optional GameAssembly option-flow report to summarize beside the timeline evidence.",
    )
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
    story_filters = split_csv_values(args.story)
    try:
        group_filters = parse_group_filters(args.group)
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
        il2cpp_report_path=args.il2cpp_report,
    )
    summary = result["summary"]
    print(f"Timeline option flow audit: {result['markdown']}")
    print(f"Timeline option flow data:  {result['json']}")
    print(
        "Audited "
        f"{summary['inferredResponseGroupCount']} inferred response groups; "
        f"{summary['groupsWithNonzeroCandidateRawClipOptionIndex']} groups have nonzero candidate trunk raw optionIndex; "
        f"{summary.get('groupsWithCandidateRuntimeFieldAllZero', 0)} groups have all-zero candidate runtime fields."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
