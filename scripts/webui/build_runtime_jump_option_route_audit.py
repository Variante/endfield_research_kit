#!/usr/bin/env python3
"""Audit inferred dialog option branches against Runtime Jump Track clips.

The story builder can already promote unambiguous Runtime Jump Track skip
windows into `timelineRouteBranches`. This report looks at the remaining
`inferredFollowingLines` groups and records whether nearby Runtime Jump evidence
is strong enough to justify another recovery rule.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from common import (
    ROOT,
    filtered_json_paths as filtered_conv_paths,
    md_escape,
    parse_group_filters,
    read_json,
    safe_key,
    safe_report_suffix,
    split_csv_values,
    story_matches,
    write_report_json as write_json,
)


SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from recover_timeline_line_orders import (  # noqa: E402
    as_float,
    as_int,
    line_stem,
    load_monobehaviour_records,
    runtime_jump_clip_rows,
)


ROUTE_EPSILON = 0.001
NEARBY_PADDING_SECONDS = 1.0


def slash(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix().replace("\\", "/")


def resolve_repo_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def time_range_overlaps(start: float, end: float, window_start: float, window_end: float) -> bool:
    return end >= window_start - ROUTE_EPSILON and start <= window_end + ROUTE_EPSILON


def is_forward_jump(clip: dict[str, Any]) -> bool:
    if as_int(clip.get("isReverseJump")):
        return False
    return "<" not in str(clip.get("displayName") or "")


def compact_jump(clip: dict[str, Any]) -> dict[str, Any]:
    out = {
        "optionIndex": clip.get("optionIndex"),
        "start": clip.get("start"),
        "end": clip.get("end"),
        "duration": clip.get("duration"),
        "track": clip.get("track") or "",
        "trackName": clip.get("trackName") or "",
        "assetTrack": clip.get("assetTrack") or "",
        "displayName": clip.get("displayName") or "",
        "isForwardJump": is_forward_jump(clip),
    }
    for field in (
        "isReverseJump",
        "needChangeOptionAfterJump",
        "optionIndexAfterJump",
        "isJumpFirst",
        "crossFadeDurationAfterJump",
    ):
        if field in clip:
            out[field] = clip[field]
    return out


def line_time(line: dict[str, Any] | None) -> tuple[float | None, float | None]:
    if not line:
        return None, None
    start = as_float(line.get("ts"))
    duration = as_float(line.get("dur"))
    return start, start + duration


def best_timeline_option_rows(entry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for row in entry.get("options") or []:
        if not isinstance(row, dict):
            continue
        option_id = safe_key(row.get("id"))
        if not option_id:
            continue
        rank = (
            0 if row.get("anchorMode") == "trunkBinding" else 1,
            as_float(row.get("start")),
            as_int(row.get("optionIndex")) if as_int(row.get("optionIndex")) is not None else 10**9,
            safe_key(row.get("track")),
        )
        previous = best.get(option_id)
        if previous is None:
            best[option_id] = row
            continue
        previous_rank = (
            0 if previous.get("anchorMode") == "trunkBinding" else 1,
            as_float(previous.get("start")),
            as_int(previous.get("optionIndex")) if as_int(previous.get("optionIndex")) is not None else 10**9,
            safe_key(previous.get("track")),
        )
        if rank < previous_rank:
            best[option_id] = row
    return best


def timeline_option_row(
    option_id: str,
    index: int,
    risk: dict[str, Any],
    timeline_rows: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    row = dict(timeline_rows.get(option_id) or {})
    if row:
        return row
    option_indices = risk.get("optionIndex") or []
    option_index = option_indices[index] if index < len(option_indices) else None
    return {
        "id": option_id,
        "optionIndex": option_index,
    }


class RuntimeJumpCache:
    def __init__(self) -> None:
        self._mono_dirs: dict[Path, dict[str, Any]] = {}

    def load(self, mono_dir: Path) -> dict[str, Any]:
        mono_dir = mono_dir.resolve()
        cached = self._mono_dirs.get(mono_dir)
        if cached is not None:
            return cached

        records_by_key, _children_by_parent, _timeline_roots = load_monobehaviour_records(mono_dir)
        records = list(records_by_key.values())
        records_by_path = {slash(record["path"]): record for record in records}
        runtime_jumps = runtime_jump_clip_rows("", records, records_by_key)
        cached = {
            "recordsByPath": records_by_path,
            "runtimeJumps": runtime_jumps,
        }
        self._mono_dirs[mono_dir] = cached
        return cached

    def source_files_for_asset_tracks(self, asset_tracks: list[str]) -> tuple[set[str], list[dict[str, Any]], list[str]]:
        source_files: set[str] = set()
        jump_pool: list[dict[str, Any]] = []
        missing_tracks: list[str] = []
        seen_mono_dirs: set[Path] = set()

        for asset_track in asset_tracks:
            if not asset_track:
                continue
            asset_path = resolve_repo_path(asset_track)
            mono_dir = asset_path.parent
            if not mono_dir.is_dir():
                missing_tracks.append(asset_track)
                continue
            cached = self.load(mono_dir)
            record = cached["recordsByPath"].get(slash(asset_path))
            if record:
                source_files.add(safe_key(record.get("sourceFile")))
            else:
                missing_tracks.append(asset_track)
            if mono_dir.resolve() not in seen_mono_dirs:
                seen_mono_dirs.add(mono_dir.resolve())
                jump_pool.extend(cached["runtimeJumps"])

        return {value for value in source_files if value}, jump_pool, missing_tracks


def option_time_window(option_rows: list[dict[str, Any]]) -> tuple[float | None, float | None]:
    starts: list[float] = []
    ends: list[float] = []
    for row in option_rows:
        if "start" not in row:
            continue
        start = as_float(row.get("start"))
        duration = as_float(row.get("duration"))
        starts.append(start)
        ends.append(start + duration)
    if not starts or not ends:
        return None, None
    return min(starts), max(ends)


def infer_route_paths(
    conv: dict[str, Any],
    option_rows: list[dict[str, Any]],
    option_ids: list[str],
    candidate_line_ids: list[str],
    common_line_id: str,
    nearby_jumps: list[dict[str, Any]],
) -> tuple[dict[str, list[str]], dict[str, list[str]], dict[str, dict[str, Any]], bool]:
    _option_start, option_end = option_time_window(option_rows)
    if option_end is None:
        return {}, {}, {}, False

    line_rows = [line for line in conv.get("lines") or [] if isinstance(line, dict)]
    common_start = None
    for line in line_rows:
        if safe_key(line.get("id")) == common_line_id:
            common_start = as_float(line.get("ts"))
            break
    if common_start is None:
        candidate_ends = [
            line_time(line)[1]
            for line in line_rows
            if safe_key(line.get("id")) in set(candidate_line_ids)
        ]
        candidate_ends = [value for value in candidate_ends if value is not None]
        common_start = max(candidate_ends) if candidate_ends else option_end
    if common_start <= option_end:
        return {}, {}, {}, False

    scene_key = safe_key(conv.get("key"))
    route_lines = [
        line
        for line in line_rows
        if line_stem(safe_key(line.get("id"))) == scene_key
        and as_float(line.get("ts")) >= option_end - ROUTE_EPSILON
        and as_float(line.get("ts")) < common_start - ROUTE_EPSILON
    ]
    if not route_lines:
        return {}, {}, {}, False

    by_option: dict[str, list[str]] = {}
    jump_effects_by_option: dict[str, dict[str, Any]] = {}
    for option_id, row in zip(option_ids, option_rows):
        option_index = as_int(row.get("optionIndex"))
        if option_index is None:
            continue
        related_jumps = [
            clip
            for clip in nearby_jumps
            if clip.get("optionIndex") == option_index
        ]
        skips = [
            clip
            for clip in related_jumps
            if is_forward_jump(clip)
        ]
        path_line_ids: list[str] = []
        forward_skipped_line_ids: list[str] = []
        reverse_range_line_ids: list[str] = []
        for line in route_lines:
            line_id = safe_key(line.get("id"))
            line_start = as_float(line.get("ts"))
            in_forward_skip = any(
                line_start >= as_float(skip.get("start")) - ROUTE_EPSILON
                and line_start < as_float(skip.get("end")) - ROUTE_EPSILON
                for skip in skips
            )
            if in_forward_skip:
                if line_id:
                    forward_skipped_line_ids.append(line_id)
                continue
            if line_id:
                path_line_ids.append(line_id)
            if any(
                not is_forward_jump(jump)
                and line_start >= as_float(jump.get("start")) - ROUTE_EPSILON
                and line_start < as_float(jump.get("end")) - ROUTE_EPSILON
                for jump in related_jumps
            ) and line_id:
                reverse_range_line_ids.append(line_id)
        if skips:
            by_option[option_id] = path_line_ids
        option_change_jumps = [
            {
                "start": jump.get("start"),
                "end": jump.get("end"),
                "optionIndexAfterJump": jump.get("optionIndexAfterJump"),
                "isForwardJump": is_forward_jump(jump),
                "displayName": jump.get("displayName") or "",
                "assetTrack": jump.get("assetTrack") or "",
            }
            for jump in related_jumps
            if as_int(jump.get("needChangeOptionAfterJump"))
        ]
        if forward_skipped_line_ids or reverse_range_line_ids or option_change_jumps:
            jump_effects_by_option[option_id] = {
                "optionIndex": option_index,
                "forwardSkippedLineIds": forward_skipped_line_ids,
                "reverseRangeLineIds": reverse_range_line_ids,
                "optionChangeJumps": option_change_jumps,
            }

    expected = {
        option_id: [candidate_line_ids[index]]
        for index, option_id in enumerate(option_ids)
        if index < len(candidate_line_ids) and candidate_line_ids[index]
    }
    paths_match_candidates = bool(expected) and all(by_option.get(option_id) == expected[option_id] for option_id in expected)
    return by_option, expected, jump_effects_by_option, paths_match_candidates


def runtime_path_diagnostics(
    inferred_paths: dict[str, list[str]],
    expected_paths: dict[str, list[str]],
    jump_effects_by_option: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    runtime_first_by_option = {
        option_id: path[0]
        for option_id, path in inferred_paths.items()
        if path
    }
    expected_first_by_option = {
        option_id: path[0]
        for option_id, path in expected_paths.items()
        if path
    }
    candidate_owner_by_line = {
        line_id: option_id
        for option_id, line_id in expected_first_by_option.items()
    }
    conflicts: list[dict[str, Any]] = []
    for option_id, runtime_first in runtime_first_by_option.items():
        expected_first = expected_first_by_option.get(option_id)
        if expected_first and runtime_first != expected_first:
            conflicts.append({
                "optionId": option_id,
                "expectedFirstLineId": expected_first,
                "runtimeFirstLineId": runtime_first,
                "runtimeFirstLineCandidateOwner": candidate_owner_by_line.get(runtime_first),
            })
    directional_first_by_option = dict(runtime_first_by_option)
    for option_id, effects in jump_effects_by_option.items():
        reverse_lines = effects.get("reverseRangeLineIds") or []
        if reverse_lines:
            directional_first_by_option[option_id] = reverse_lines[0]
    directional_conflicts: list[dict[str, Any]] = []
    for option_id, directional_first in directional_first_by_option.items():
        expected_first = expected_first_by_option.get(option_id)
        if expected_first and directional_first != expected_first:
            directional_conflicts.append({
                "optionId": option_id,
                "expectedFirstLineId": expected_first,
                "directionalFirstLineId": directional_first,
                "directionalFirstLineCandidateOwner": candidate_owner_by_line.get(directional_first),
            })
    expected_first_set = {value for value in expected_first_by_option.values() if value}
    directional_first_set = {value for value in directional_first_by_option.values() if value}
    directional_covers_candidates = (
        bool(expected_first_set)
        and expected_first_set == directional_first_set
        and len(directional_first_by_option) >= len(expected_first_by_option)
    )
    return {
        "expectedFirstLineByOption": expected_first_by_option,
        "runtimeFirstLineByOption": runtime_first_by_option,
        "directionalFirstLineByOption": directional_first_by_option,
        "directionalFirstLinesCoverCandidates": directional_covers_candidates,
        "runtimePathConflicts": conflicts,
        "runtimePathConflictCount": len(conflicts),
        "directionalFirstLineConflicts": directional_conflicts,
        "directionalFirstLineConflictCount": len(directional_conflicts),
    }


def audit_group(
    conv: dict[str, Any],
    group: dict[str, Any],
    risk: dict[str, Any],
    timeline_rows: dict[str, dict[str, Any]],
    jump_cache: RuntimeJumpCache,
) -> dict[str, Any]:
    option_ids = [safe_key(value) for value in risk.get("optionIds") or [] if safe_key(value)]
    if not option_ids:
        option_ids = [safe_key(option.get("id")) for option in group.get("options") or [] if safe_key(option.get("id"))]
    candidate_line_ids = [safe_key(value) for value in risk.get("candidateLineIds") or [] if safe_key(value)]
    common_line_id = safe_key(risk.get("commonContinuationLineId"))
    option_rows = [
        timeline_option_row(option_id, index, risk, timeline_rows)
        for index, option_id in enumerate(option_ids)
    ]
    option_indices = [as_int(row.get("optionIndex")) for row in option_rows]

    line_by_id = {
        safe_key(line.get("id")): line
        for line in conv.get("lines") or []
        if isinstance(line, dict) and safe_key(line.get("id"))
    }
    after_start, after_end = line_time(line_by_id.get(safe_key(risk.get("after") or group.get("after"))))
    option_start, option_end = option_time_window(option_rows)
    candidate_times = [
        value
        for line_id in candidate_line_ids + ([common_line_id] if common_line_id else [])
        for value in line_time(line_by_id.get(line_id))
        if value is not None
    ]
    starts = [value for value in (after_end, option_start) if value is not None] + candidate_times[:1]
    ends = [value for value in (option_end,) if value is not None] + candidate_times
    window_start = min(starts) - NEARBY_PADDING_SECONDS if starts else 0.0
    window_end = max(ends) + NEARBY_PADDING_SECONDS if ends else window_start

    asset_tracks = [safe_key(value) for value in risk.get("assetTracks") or [] if safe_key(value)]
    source_files, jump_pool, missing_tracks = jump_cache.source_files_for_asset_tracks(asset_tracks)
    option_index_set = {value for value in option_indices if value is not None}
    nearby_jumps = [
        clip
        for clip in jump_pool
        if (not source_files or safe_key(clip.get("sourceFile")) in source_files)
        and time_range_overlaps(as_float(clip.get("start")), as_float(clip.get("end")), window_start, window_end)
    ]
    nearby_jumps.sort(key=lambda clip: (as_float(clip.get("start")), as_int(clip.get("optionIndex")) or -1, safe_key(clip.get("track"))))

    forward_jump_indices = {
        as_int(clip.get("optionIndex"))
        for clip in nearby_jumps
        if as_int(clip.get("optionIndex")) is not None and is_forward_jump(clip)
    }
    complete_forward_coverage = bool(option_index_set) and option_index_set.issubset(forward_jump_indices)
    reverse_or_direction_markers = any(not is_forward_jump(clip) for clip in nearby_jumps)
    pre_option_jump = False
    if option_end is not None:
        pre_option_jump = any(
            as_float(clip.get("start")) < option_end - ROUTE_EPSILON
            for clip in nearby_jumps
            if as_int(clip.get("optionIndex")) in option_index_set
        )
    mismatched_jump_indices = sorted(
        value
        for value in {
            as_int(clip.get("optionIndex"))
            for clip in nearby_jumps
            if as_int(clip.get("optionIndex")) is not None
        }
        if value not in option_index_set
    )
    inferred_paths, expected_paths, jump_effects_by_option, paths_match_candidates = infer_route_paths(
        conv,
        option_rows,
        option_ids,
        candidate_line_ids,
        common_line_id,
        nearby_jumps,
    )
    path_diagnostics = runtime_path_diagnostics(inferred_paths, expected_paths, jump_effects_by_option)
    distinct_paths = {tuple(path) for path in inferred_paths.values() if path}
    passes_narrow_route_rule = (
        complete_forward_coverage
        and not reverse_or_direction_markers
        and not pre_option_jump
        and paths_match_candidates
        and len(distinct_paths) >= 2
    )

    if passes_narrow_route_rule:
        recommendation = "promoteableRouteRuleCandidate"
    elif not nearby_jumps:
        recommendation = "noNearbyRuntimeJump"
    elif path_diagnostics["directionalFirstLinesCoverCandidates"] and path_diagnostics["directionalFirstLineConflictCount"]:
        recommendation = "reviewDirectionalRuntimeJumpMapping"
    elif path_diagnostics["runtimePathConflictCount"]:
        recommendation = "nearbyRuntimeJumpContradictsInferredPath"
    elif not complete_forward_coverage:
        recommendation = "nearbyRuntimeJumpIncompleteOptionCoverage"
    elif reverse_or_direction_markers or pre_option_jump:
        recommendation = "nearbyRuntimeJumpAmbiguousTiming"
    elif not paths_match_candidates:
        recommendation = "nearbyRuntimeJumpPathMismatch"
    else:
        recommendation = "manualReview"

    return {
        "sceneKey": conv.get("key"),
        "mission": conv.get("mission") or "",
        "group": group.get("g"),
        "after": risk.get("after") or group.get("after"),
        "optionIds": option_ids,
        "optionIndex": option_indices,
        "candidateLineIds": candidate_line_ids,
        "commonContinuationLineId": common_line_id,
        "assetTracks": asset_tracks,
        "sourceFiles": sorted(source_files),
        "missingAssetTracks": missing_tracks,
        "timeWindow": {
            "start": round(window_start, 3),
            "end": round(window_end, 3),
            "afterStart": round(after_start, 3) if after_start is not None else None,
            "afterEnd": round(after_end, 3) if after_end is not None else None,
            "optionStart": round(option_start, 3) if option_start is not None else None,
            "optionEnd": round(option_end, 3) if option_end is not None else None,
        },
        "nearbyRuntimeJumps": [compact_jump(clip) for clip in nearby_jumps],
        "checks": {
            "completeForwardCoverage": complete_forward_coverage,
            "reverseOrDirectionMarkers": reverse_or_direction_markers,
            "preOptionJump": pre_option_jump,
            "mismatchedJumpIndices": mismatched_jump_indices,
            "inferredPathsByOption": inferred_paths,
            "expectedPathsByOption": expected_paths,
            "runtimeJumpEffectsByOption": jump_effects_by_option,
            "pathsMatchCandidates": paths_match_candidates,
            **path_diagnostics,
            "passesNarrowRouteRule": passes_narrow_route_rule,
        },
        "recommendation": recommendation,
    }


def collect_audit_rows(
    language: str,
    conv_dir: Path,
    timeline_orders_path: Path,
    *,
    story_filters: list[str] | None = None,
    group_filters: set[int] | None = None,
    only_nearby_jumps: bool = False,
) -> list[dict[str, Any]]:
    timeline_orders = read_json(timeline_orders_path, {}) or {}
    jump_cache = RuntimeJumpCache()
    rows: list[dict[str, Any]] = []
    story_filters = story_filters or []
    group_filters = group_filters or set()

    for conv_path in filtered_conv_paths(conv_dir, story_filters):
        conv = read_json(conv_path, {})
        if not isinstance(conv, dict) or conv.get("kind") != "dlg":
            continue
        scene_key = safe_key(conv.get("key") or conv_path.stem)
        if not story_matches(scene_key, story_filters):
            continue
        timeline_rows = best_timeline_option_rows(timeline_orders.get(scene_key) or {})
        for group in conv.get("optionGroups") or []:
            if not isinstance(group, dict):
                continue
            group_index = as_int(group.get("g"))
            if group_filters and group_index not in group_filters:
                continue
            risk = group.get("optionBranchRisk") or {}
            if not isinstance(risk, dict) or risk.get("code") != "inferredFollowingLines":
                continue
            row = audit_group(conv, group, risk, timeline_rows, jump_cache)
            if only_nearby_jumps and not row.get("nearbyRuntimeJumps"):
                continue
            rows.append(row)

    rows.sort(key=lambda row: (row.get("mission") or "", row.get("sceneKey") or "", row.get("group") or 0))
    return rows


def summarize_rows(
    language: str,
    rows: list[dict[str, Any]],
    *,
    story_filters: list[str] | None = None,
    group_filters: set[int] | None = None,
    only_nearby_jumps: bool = False,
) -> dict[str, Any]:
    recommendations = Counter(row.get("recommendation") or "" for row in rows)
    return {
        "language": language,
        "filters": {
            "stories": story_filters or [],
            "groups": sorted(group_filters or []),
            "onlyNearbyJumps": only_nearby_jumps,
        },
        "inferredFollowingLineGroupCount": len(rows),
        "groupsWithNearbyRuntimeJumps": sum(1 for row in rows if row.get("nearbyRuntimeJumps")),
        "groupsWithCompleteForwardCoverage": sum(
            1 for row in rows if row.get("checks", {}).get("completeForwardCoverage")
        ),
        "groupsWithReverseOrDirectionMarkers": sum(
            1 for row in rows if row.get("checks", {}).get("reverseOrDirectionMarkers")
        ),
        "groupsWithPreOptionJumps": sum(1 for row in rows if row.get("checks", {}).get("preOptionJump")),
        "groupsWithRuntimePathEvidence": sum(
            1 for row in rows if row.get("checks", {}).get("runtimeFirstLineByOption")
        ),
        "groupsWithRuntimePathConflicts": sum(
            1 for row in rows if row.get("checks", {}).get("runtimePathConflictCount")
        ),
        "groupsWithDirectionalCandidateCoverage": sum(
            1 for row in rows if row.get("checks", {}).get("directionalFirstLinesCoverCandidates")
        ),
        "groupsWithDirectionalMappingConflicts": sum(
            1 for row in rows if row.get("checks", {}).get("directionalFirstLineConflictCount")
        ),
        "groupsWithReverseRangeLineEvidence": sum(
            1
            for row in rows
            if any(
                effects.get("reverseRangeLineIds")
                for effects in (row.get("checks", {}).get("runtimeJumpEffectsByOption") or {}).values()
                if isinstance(effects, dict)
            )
        ),
        "groupsWithOptionChangeJumps": sum(
            1
            for row in rows
            if any(
                effects.get("optionChangeJumps")
                for effects in (row.get("checks", {}).get("runtimeJumpEffectsByOption") or {}).values()
                if isinstance(effects, dict)
            )
        ),
        "groupsPassingNarrowRouteRule": sum(
            1 for row in rows if row.get("checks", {}).get("passesNarrowRouteRule")
        ),
        "recommendationCounts": dict(sorted(recommendations.items())),
    }


def jump_summary(row: dict[str, Any]) -> str:
    parts: list[str] = []
    for clip in row.get("nearbyRuntimeJumps") or []:
        direction = "forward" if clip.get("isForwardJump") else "reverse/marked"
        parts.append(
            f"opt {clip.get('optionIndex')} {clip.get('start')}-{clip.get('end')} {direction}"
        )
    return "; ".join(parts)


def runtime_path_summary(row: dict[str, Any]) -> str:
    checks = row.get("checks") or {}
    first_by_option = checks.get("directionalFirstLineByOption") or checks.get("runtimeFirstLineByOption") or {}
    if not isinstance(first_by_option, dict) or not first_by_option:
        return ""
    parts = []
    for option_id, line_id in first_by_option.items():
        expected = (checks.get("expectedFirstLineByOption") or {}).get(option_id)
        marker = "" if not expected or expected == line_id else f" != {expected}"
        parts.append(f"{option_id} -> {line_id}{marker}")
    return "; ".join(parts)


def jump_effect_summary(row: dict[str, Any]) -> str:
    effects_by_option = (row.get("checks") or {}).get("runtimeJumpEffectsByOption") or {}
    if not isinstance(effects_by_option, dict):
        return ""
    parts: list[str] = []
    for option_id, effects in effects_by_option.items():
        if not isinstance(effects, dict):
            continue
        details: list[str] = []
        if effects.get("forwardSkippedLineIds"):
            details.append("skip " + ",".join(effects["forwardSkippedLineIds"]))
        if effects.get("reverseRangeLineIds"):
            details.append("reverse " + ",".join(effects["reverseRangeLineIds"]))
        change_targets = [
            str(item.get("optionIndexAfterJump"))
            for item in effects.get("optionChangeJumps") or []
            if item.get("optionIndexAfterJump") is not None
        ]
        if change_targets:
            details.append("change->" + ",".join(change_targets))
        if details:
            parts.append(f"{option_id}: {'; '.join(details)}")
    return " | ".join(parts)


def render_markdown(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = [
        f"# Runtime Jump Option Route Audit - {summary['language']}",
        "",
        f"- Inferred option groups audited: `{summary['inferredFollowingLineGroupCount']}`",
        f"- Groups with nearby Runtime Jump Track clips: `{summary['groupsWithNearbyRuntimeJumps']}`",
        f"- Groups with complete forward optionIndex coverage: `{summary['groupsWithCompleteForwardCoverage']}`",
        f"- Groups with reverse/direction markers: `{summary['groupsWithReverseOrDirectionMarkers']}`",
        f"- Groups with pre-option jump timing: `{summary['groupsWithPreOptionJumps']}`",
        f"- Groups with Runtime Jump path evidence: `{summary['groupsWithRuntimePathEvidence']}`",
        f"- Groups where Runtime Jump path evidence contradicts the current inferred first line: `{summary['groupsWithRuntimePathConflicts']}`",
        f"- Groups where directional Runtime Jump effects cover all current candidate first lines: `{summary['groupsWithDirectionalCandidateCoverage']}`",
        f"- Groups where directional Runtime Jump mapping disagrees with current inferred first lines: `{summary['groupsWithDirectionalMappingConflicts']}`",
        f"- Groups with reverse-jump line-range evidence: `{summary['groupsWithReverseRangeLineEvidence']}`",
        f"- Groups with `needChangeOptionAfterJump` clips: `{summary['groupsWithOptionChangeJumps']}`",
        f"- Groups passing the strict second-rule check: `{summary['groupsPassingNarrowRouteRule']}`",
        "",
        "## Recommendation Counts",
        "",
    ]
    for key, count in summary.get("recommendationCounts", {}).items():
        lines.append(f"- `{key}`: {count}")

    lines.extend([
        "",
        "## Rule Decision",
        "",
    ])
    if summary["groupsPassingNarrowRouteRule"]:
        lines.append(
            "At least one group passes the strict diagnostic check. Review these rows before promoting a second automatic route rule."
        )
    else:
        lines.append(
            "No remaining inferred group passes the strict check for automatic promotion. Nearby Runtime Jump clips exist, but the evidence is incomplete, uses reverse/direction-marked jumps, fires before the option window, or does not reproduce the candidate branch lines."
        )

    nearby_rows = [row for row in rows if row.get("nearbyRuntimeJumps")]
    lines.extend([
        "",
        "## Groups With Nearby Runtime Jump Clips",
        "",
        "| Scene | Group | After | Options | Candidates | Common | Nearby jumps | Runtime line effects | Runtime path check | Recommendation |",
        "| --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in nearby_rows:
        lines.append(
            "| "
            f"`{md_escape(row.get('sceneKey'))}` "
            f"| {md_escape(row.get('group'))} "
            f"| `{md_escape(row.get('after'))}` "
            f"| `{md_escape(', '.join(row.get('optionIds') or []))}` "
            f"| `{md_escape(', '.join(row.get('candidateLineIds') or []))}` "
            f"| `{md_escape(row.get('commonContinuationLineId'))}` "
            f"| {md_escape(jump_summary(row))} "
            f"| {md_escape(jump_effect_summary(row))} "
            f"| {md_escape(runtime_path_summary(row))} "
            f"| `{md_escape(row.get('recommendation'))}` |"
        )
    if not nearby_rows:
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
    only_nearby_jumps: bool = False,
) -> dict[str, Any]:
    rows = collect_audit_rows(
        language,
        conv_dir,
        timeline_orders_path,
        story_filters=story_filters,
        group_filters=group_filters,
        only_nearby_jumps=only_nearby_jumps,
    )
    summary = summarize_rows(
        language,
        rows,
        story_filters=story_filters,
        group_filters=group_filters,
        only_nearby_jumps=only_nearby_jumps,
    )
    payload = {
        "summary": summary,
        "groups": rows,
    }

    reports_dir.mkdir(parents=True, exist_ok=True)
    suffix = safe_report_suffix(
        story_filters or [],
        group_filters or set(),
        only_nearby_jumps,
        flag_label="nearby",
    )
    out_json = reports_dir / f"runtime_jump_option_route_audit_{language}{suffix}.json"
    out_md = reports_dir / f"runtime_jump_option_route_audit_{language}{suffix}.md"
    write_json(out_json, payload)
    out_md.write_text(render_markdown(summary, rows) + "\n", encoding="utf-8")
    return {
        "summary": summary,
        "json": out_json,
        "markdown": out_md,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", default="CN")
    parser.add_argument("--conv-dir", type=Path)
    parser.add_argument("--timeline-orders", type=Path, default=ROOT / "export_full" / "recovered" / "AnimeStudio-cli" / "timeline_line_orders.json")
    parser.add_argument("--reports-dir", type=Path, default=ROOT / "reports")
    parser.add_argument("--story", action="append", help="Story key, substring, glob, or comma-list to audit.")
    parser.add_argument("--group", action="append", help="Option group number or comma-list to audit.")
    parser.add_argument("--only-nearby-jumps", action="store_true", help="Emit only audited groups that have nearby Runtime Jump Track clips.")
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
        only_nearby_jumps=args.only_nearby_jumps,
    )
    summary = result["summary"]
    print(f"Runtime jump option route audit: {result['markdown']}")
    print(f"Runtime jump option route data:  {result['json']}")
    print(
        "Audited "
        f"{summary['inferredFollowingLineGroupCount']} inferred groups; "
        f"{summary['groupsWithNearbyRuntimeJumps']} have nearby jumps; "
        f"{summary['groupsPassingNarrowRouteRule']} pass strict promotion."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
