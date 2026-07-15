#!/usr/bin/env python3
"""Audit unresolved option responses against DialogOptionPlayableAsset fields.

The remaining `inferredOptionResponse` warnings usually have Timeline option
clips but no explicit branch route. This report keeps those cases together with
decoded option-playable fields such as `logicId`, `trunkId`, `dialogId`,
`conditionRid`, `changeFinishNum`, and `targetFinishNum`.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (_REPO_ROOT / "scripts",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))
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
    unique_preserve,
    write_report_json as write_json,
)


KNOWN_OPTION_PAYLOAD_FIELDS = {
    "$animestudio",
    "_optionId",
    "index",
    "optionIndex",
    "trunkId",
    "dialogId",
    "overrideOptionIconType",
    "logicId",
    "selectedFlag",
    "setGreyed",
    "main",
    "isChat",
    "changeFinishNum",
    "targetFinishNum",
    "useExOptionColor",
    "overrideOptionIcon",
    "optionIconColor",
    "conditionData",
}

REFERENCE_KEYS = {
    "fileID",
    "guid",
    "m_FileID",
    "m_Guid",
    "m_PathID",
    "pathID",
    "pathId",
    "rid",
    "type",
}


def as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if re_match_int(text):
            return int(text)
    return None


def re_match_int(text: str) -> bool:
    if text.startswith("-"):
        return text[1:].isdigit()
    return text.isdigit()


def line_suffix_int(line_id: str) -> int | None:
    suffix = safe_key(line_id).rsplit("_", 1)[-1]
    return as_int(suffix)


def line_stem_from_id(line_id: str) -> str:
    text = safe_key(line_id)
    prefix, sep, suffix = text.rpartition("_")
    if sep and suffix.isdigit() and prefix:
        return prefix
    return ""


def option_scene_key(option_id: str) -> str:
    text = safe_key(option_id)
    if text.startswith("option_"):
        text = text[len("option_") :]
    prefix, sep, _index = text.rpartition("_")
    if not sep:
        return ""
    scene_key, sep, _group = prefix.rpartition("_")
    return scene_key if sep else ""


def timeline_order_aliases(
    story_key: str,
    *,
    option_ids: list[str] | None = None,
    line_ids: list[str] | None = None,
) -> list[str]:
    aliases: list[str] = []

    def add(value: str) -> None:
        value = safe_key(value)
        if value and value not in aliases:
            aliases.append(value)

    add(story_key)
    if story_key.startswith("misc_"):
        add(story_key[len("misc_") :])
    for option_id in option_ids or []:
        add(option_scene_key(option_id))
    for line_id in line_ids or []:
        add(line_stem_from_id(line_id))
    return aliases


def timeline_entry_for_story(
    timeline_orders: dict[str, Any],
    story_key: str,
    *,
    option_ids: list[str] | None = None,
    line_ids: list[str] | None = None,
) -> dict[str, Any]:
    if not isinstance(timeline_orders, dict):
        return {}
    for alias in timeline_order_aliases(story_key, option_ids=option_ids, line_ids=line_ids):
        entry = timeline_orders.get(alias)
        if isinstance(entry, dict):
            return entry
    return {}


def line_lookup_from_conv(conv: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        safe_key(line.get("id")): line
        for line in conv.get("lines") or []
        if isinstance(line, dict) and safe_key(line.get("id"))
    }


def line_lookup_from_timeline(entry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        safe_key(line.get("id")): line
        for line in entry.get("lines") or []
        if isinstance(line, dict) and safe_key(line.get("id"))
    }


def option_texts_from_conv(conv: dict[str, Any]) -> dict[str, str]:
    texts: dict[str, str] = {}
    for group in conv.get("optionGroups") or []:
        if not isinstance(group, dict):
            continue
        for option in group.get("options") or []:
            if not isinstance(option, dict):
                continue
            option_id = safe_key(option.get("id"))
            if option_id:
                texts[option_id] = safe_key(option.get("text"))
    return texts


def option_rows_by_id(entry: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in entry.get("options") or []:
        if not isinstance(row, dict):
            continue
        option_id = safe_key(row.get("id"))
        if option_id:
            rows[option_id].append(row)
    return dict(rows)


def option_row_rank(row: dict[str, Any]) -> tuple[int, float, int, str]:
    return (
        0 if row.get("anchorMode") == "trunkBinding" else 1,
        as_float(row.get("start")),
        as_int(row.get("optionIndex")) if as_int(row.get("optionIndex")) is not None else 10**9,
        safe_key(row.get("assetTrack") or row.get("track")),
    )


def compact_option_row(row: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "id",
        "start",
        "duration",
        "groupKey",
        "index",
        "optionIndex",
        "clipOptionIndex",
        "anchorMode",
        "anchorLineId",
        "trunkId",
        "dialogId",
        "logicId",
        "selectedFlag",
        "setGreyed",
        "main",
        "isChat",
        "conditionRid",
        "changeFinishNum",
        "targetFinishNum",
        "useExOptionColor",
        "overrideOptionIcon",
        "overrideOptionIconType",
        "assetName",
        "assetPathId",
        "assetTrack",
        "trackName",
        "trackPathId",
        "track",
        "sourceFile",
    )
    return {field: row.get(field) for field in fields if row.get(field) not in (None, "", [], {})}


def raw_asset_path(asset_track: str) -> Path | None:
    text = safe_key(asset_track)
    if not text:
        return None
    path = Path(text)
    if not path.is_absolute():
        path = ROOT / path
    return path if path.is_file() else None


def option_payload_from_asset(asset_track: str, option_id: str, cache: dict[str, Any]) -> dict[str, Any]:
    option_id = safe_key(option_id)
    if not option_id:
        return {}
    asset_track = safe_key(asset_track)
    if asset_track not in cache:
        path = raw_asset_path(asset_track)
        cache[asset_track] = read_json(path, {}) if path else {}
    payload = cache.get(asset_track)
    if not isinstance(payload, dict):
        return {}

    def visit(node: Any) -> dict[str, Any]:
        if isinstance(node, dict):
            if safe_key(node.get("_optionId")) == option_id:
                return node
            for value in node.values():
                found = visit(value)
                if found:
                    return found
        elif isinstance(node, list):
            for value in node:
                found = visit(value)
                if found:
                    return found
        return {}

    return visit(payload)


def compact_scalar(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, str):
        text = value.strip()
        if len(text) <= 160:
            return text
    return None


def compact_reference(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    out = {}
    for key in sorted(REFERENCE_KEYS):
        if key in value and value.get(key) not in (None, "", [], {}):
            out[key] = value.get(key)
    return out


def raw_payload_diagnostics(row: dict[str, Any], cache: dict[str, Any]) -> dict[str, Any]:
    payload = option_payload_from_asset(
        safe_key(row.get("assetTrack")),
        safe_key(row.get("id")),
        cache,
    )
    if not payload:
        return {}
    raw_keys = sorted(key for key in payload if key != "$animestudio")
    extra_scalars: dict[str, Any] = {}
    extra_refs: dict[str, Any] = {}
    nested_scalar_keys: dict[str, list[str]] = {}
    for key, value in payload.items():
        if key in KNOWN_OPTION_PAYLOAD_FIELDS or key.startswith("$"):
            continue
        scalar = compact_scalar(value)
        if scalar not in (None, "", [], {}):
            extra_scalars[key] = scalar
            continue
        ref = compact_reference(value)
        if ref:
            extra_refs[key] = ref
            continue
        if isinstance(value, dict):
            child_scalars = []
            child_refs = {}
            for child_key, child_value in value.items():
                scalar = compact_scalar(child_value)
                if scalar not in (None, "", [], {}):
                    child_scalars.append(child_key)
                ref = compact_reference(child_value)
                if ref:
                    child_refs[child_key] = ref
            if child_scalars:
                nested_scalar_keys[key] = sorted(child_scalars)
            if child_refs:
                extra_refs[key] = child_refs
    out = {"rawPayloadKeys": raw_keys}
    if extra_scalars:
        out["rawExtraScalars"] = extra_scalars
    if extra_refs:
        out["rawExtraRefs"] = extra_refs
    if nested_scalar_keys:
        out["rawNestedScalarKeys"] = nested_scalar_keys
    return out


def compact_option_rows_with_raw_payload(
    option_rows: list[dict[str, Any]],
    cache: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = []
    for row in option_rows:
        compact = compact_option_row(row)
        compact.update(raw_payload_diagnostics(compact, cache))
        rows.append(compact)
    return rows


def compact_line(line_id: str, conv_lines: dict[str, dict[str, Any]], timeline_lines: dict[str, dict[str, Any]]) -> dict[str, Any]:
    conv_line = conv_lines.get(line_id) or {}
    timeline_line = timeline_lines.get(line_id) or {}
    out: dict[str, Any] = {"id": line_id}
    if conv_line.get("text"):
        out["text"] = conv_line.get("text")
    if conv_line.get("audio"):
        out["audio"] = conv_line.get("audio")
    for field, source in (
        ("ts", conv_line),
        ("dur", conv_line),
        ("start", timeline_line),
        ("duration", timeline_line),
        ("trackName", timeline_line),
        ("assetTrack", timeline_line),
    ):
        if source.get(field) not in (None, "", [], {}):
            out[field] = source.get(field)
    return out


def nearby_line_ids(entry: dict[str, Any], anchor: str, candidates: list[str], common: str, radius: int = 3) -> list[str]:
    line_ids = [safe_key(line_id) for line_id in entry.get("lineIds") or [] if safe_key(line_id)]
    focus = [anchor, *candidates, common]
    indexes = [line_ids.index(line_id) for line_id in focus if line_id in line_ids]
    if not indexes:
        return []
    start = max(min(indexes) - radius, 0)
    end = min(max(indexes) + radius + 1, len(line_ids))
    return line_ids[start:end]


def classify_group(option_entries: list[dict[str, Any]], routes: dict[str, Any]) -> str:
    all_rows = [row for entry in option_entries for row in entry.get("allRows") or []]
    if any(row.get("trunkId") or row.get("dialogId") for row in all_rows):
        return "explicitTargetField"
    if any(routes.get(entry["optionId"]) for entry in option_entries):
        return "hasRouteEvidence"
    finish_values = [
        row.get("targetFinishNum")
        for row in all_rows
        if row.get("targetFinishNum") not in (None, "", -1, 0)
    ]
    change_values = [
        row.get("changeFinishNum")
        for row in all_rows
        if row.get("changeFinishNum") not in (None, "", 0)
    ]
    if finish_values or change_values:
        return "finishNumberField"
    if any(row.get("logicId") not in (None, "", 0) for row in all_rows):
        return "logicIdOnly"
    if all_rows:
        return "defaultOptionFieldsOnly"
    return "clipPlacementOnly"


def recommendation_for_classification(classification: str) -> str:
    if classification == "explicitTargetField":
        return "promoteAfterManualCheck"
    if classification == "hasRouteEvidence":
        return "preferExistingRouteRecovery"
    if classification == "finishNumberField":
        return "investigateFinishNumberMapping"
    if classification == "logicIdOnly":
        return "investigateLogicIdMapping"
    if classification == "defaultOptionFieldsOnly":
        return "noDecodedTargetSignal"
    return "noNewSignal"


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
    story_filters = story_filters or []
    group_filters = group_filters or set()
    raw_asset_cache: dict[str, Any] = {}
    rows: list[dict[str, Any]] = []

    for conv_path in filtered_conv_paths(conv_dir, story_filters):
        conv = read_json(conv_path, {})
        if not isinstance(conv, dict) or conv.get("kind") != "dlg":
            continue
        story_key = safe_key(conv.get("key") or conv_path.stem)
        if not story_matches(story_key, story_filters):
            continue
        conv_lines = line_lookup_from_conv(conv)
        timeline_entry = timeline_entry_for_story(
            timeline_orders,
            story_key,
            line_ids=list(conv_lines),
        )
        timeline_lines = line_lookup_from_timeline(timeline_entry)
        option_texts = option_texts_from_conv(conv)
        rows_by_option = option_rows_by_id(timeline_entry)
        routes = timeline_entry.get("optionRoutes") if isinstance(timeline_entry.get("optionRoutes"), dict) else {}

        warnings = [
            warning
            for warning in conv.get("warnings") or []
            if isinstance(warning, dict) and warning.get("code") == "inferredOptionResponse"
        ]
        for warning in warnings:
            for group_warning in warning.get("groups") or []:
                if not isinstance(group_warning, dict):
                    continue
                group_id = as_int(group_warning.get("group"))
                if group_filters and group_id not in group_filters:
                    continue
                option_ids = [safe_key(value) for value in group_warning.get("optionIds") or [] if safe_key(value)]
                candidate_line_ids = [
                    safe_key(value)
                    for value in group_warning.get("candidateLineIds") or []
                    if safe_key(value)
                ]
                common_line_id = safe_key(group_warning.get("commonContinuationLineId"))
                option_entries: list[dict[str, Any]] = []
                for index, option_id in enumerate(option_ids):
                    option_rows = sorted(rows_by_option.get(option_id) or [], key=option_row_rank)
                    compact_rows = compact_option_rows_with_raw_payload(option_rows, raw_asset_cache)
                    best_row = compact_rows[0] if compact_rows else {}
                    candidate_line_id = candidate_line_ids[index] if index < len(candidate_line_ids) else ""
                    option_entries.append({
                        "optionId": option_id,
                        "text": option_texts.get(option_id, ""),
                        "candidateLineId": candidate_line_id,
                        "candidateLine": compact_line(candidate_line_id, conv_lines, timeline_lines) if candidate_line_id else {},
                        "bestRow": best_row,
                        "allRows": compact_rows,
                        "route": routes.get(option_id) or {},
                    })

                classification = classify_group(option_entries, routes)
                recommendation = recommendation_for_classification(classification)
                if only_interesting and recommendation in {"noDecodedTargetSignal", "noNewSignal"}:
                    continue
                nearby_ids = nearby_line_ids(
                    timeline_entry,
                    safe_key(group_warning.get("after")),
                    candidate_line_ids,
                    common_line_id,
                )
                rows.append({
                    "language": language,
                    "storyKey": story_key,
                    "mission": conv.get("mission"),
                    "group": group_id,
                    "after": safe_key(group_warning.get("after")),
                    "candidateLineIds": candidate_line_ids,
                    "commonContinuationLineId": common_line_id,
                    "optionIndex": group_warning.get("optionIndex") or [],
                    "assetTracks": group_warning.get("assetTracks") or [],
                    "timeline": timeline_entry.get("timeline") or "",
                    "timelineLineCount": len(timeline_entry.get("lineIds") or []),
                    "nearbyTimelineLines": [
                        compact_line(line_id, conv_lines, timeline_lines)
                        for line_id in nearby_ids
                    ],
                    "options": option_entries,
                    "classification": classification,
                    "recommendation": recommendation,
                })

    rows.sort(key=lambda row: (row.get("mission") or "", row.get("storyKey") or "", row.get("group") or 0))
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
    logic_ids: Counter[str] = Counter()
    finish_values: Counter[str] = Counter()
    condition_rids: Counter[str] = Counter()
    raw_payload_keys: Counter[str] = Counter()
    raw_extra_scalar_keys: Counter[str] = Counter()
    raw_extra_ref_keys: Counter[str] = Counter()
    raw_nested_scalar_keys: Counter[str] = Counter()
    logic_candidate_map: dict[tuple[str, int], set[str]] = defaultdict(set)
    logic_option_row_count = 0
    logic_equals_candidate_suffix_count = 0
    contiguous_logic_group_count = 0
    explicit_targets = 0
    for row in rows:
        group_logic_ids: list[int] = []
        for option in row.get("options") or []:
            candidate_line_id = safe_key(option.get("candidateLineId"))
            best_row = option.get("bestRow") or {}
            best_logic_id = best_row.get("logicId")
            if isinstance(best_logic_id, int) and best_logic_id:
                group_logic_ids.append(best_logic_id)
                logic_option_row_count += 1
                logic_candidate_map[(safe_key(row.get("storyKey")), best_logic_id)].add(candidate_line_id)
                if line_suffix_int(candidate_line_id) == best_logic_id:
                    logic_equals_candidate_suffix_count += 1
            for option_row in option.get("allRows") or []:
                for key in option_row.get("rawPayloadKeys") or []:
                    raw_payload_keys[safe_key(key)] += 1
                for key in (option_row.get("rawExtraScalars") or {}).keys():
                    raw_extra_scalar_keys[safe_key(key)] += 1
                for key in (option_row.get("rawExtraRefs") or {}).keys():
                    raw_extra_ref_keys[safe_key(key)] += 1
                for key, child_keys in (option_row.get("rawNestedScalarKeys") or {}).items():
                    for child_key in child_keys or []:
                        raw_nested_scalar_keys[f"{key}.{child_key}"] += 1
                if option_row.get("logicId") is not None:
                    logic_ids[str(option_row["logicId"])] += 1
                if option_row.get("targetFinishNum") is not None:
                    finish_values[str(option_row["targetFinishNum"])] += 1
                if option_row.get("conditionRid") is not None:
                    condition_rids[str(option_row["conditionRid"])] += 1
                if option_row.get("trunkId") or option_row.get("dialogId"):
                    explicit_targets += 1
        if (
            len(group_logic_ids) > 1
            and all(
                group_logic_ids[index] + 1 == group_logic_ids[index + 1]
                for index in range(len(group_logic_ids) - 1)
            )
        ):
            contiguous_logic_group_count += 1
    repeated_conflicts = [
        {
            "storyKey": story_key,
            "logicId": logic_id,
            "candidateLineIds": sorted(candidate_line_ids),
        }
        for (story_key, logic_id), candidate_line_ids in sorted(logic_candidate_map.items())
        if len(candidate_line_ids) > 1
    ]
    return {
        "language": language,
        "filters": {
            "stories": story_filters or [],
            "groups": sorted(group_filters or []),
            "onlyInteresting": only_interesting,
        },
        "inferredResponseGroupCount": len(rows),
        "classificationCounts": dict(sorted(classifications.items())),
        "recommendationCounts": dict(sorted(recommendations.items())),
        "explicitTargetFieldCount": explicit_targets,
        "topLogicIds": logic_ids.most_common(20),
        "logicIdOptionRowCount": logic_option_row_count,
        "contiguousLogicIdGroupCount": contiguous_logic_group_count,
        "logicIdEqualsCandidateSuffixCount": logic_equals_candidate_suffix_count,
        "repeatedStoryLogicIdConflictCount": len(repeated_conflicts),
        "repeatedStoryLogicIdCandidateConflicts": repeated_conflicts[:30],
        "targetFinishNumCounts": dict(sorted(finish_values.items())),
        "conditionRidCounts": dict(sorted(condition_rids.items())),
        "rawPayloadKeyCounts": dict(sorted(raw_payload_keys.items())),
        "rawExtraScalarKeyCounts": dict(sorted(raw_extra_scalar_keys.items())),
        "rawExtraRefKeyCounts": dict(sorted(raw_extra_ref_keys.items())),
        "rawNestedScalarKeyCounts": dict(sorted(raw_nested_scalar_keys.items())),
    }


def option_summary(row: dict[str, Any]) -> str:
    parts: list[str] = []
    for option in row.get("options") or []:
        best = option.get("bestRow") or {}
        fields = []
        for field in ("logicId", "targetFinishNum", "changeFinishNum", "conditionRid", "trunkId", "dialogId"):
            if best.get(field) not in (None, "", [], {}):
                fields.append(f"{field}={best[field]}")
        extra_scalars = sorted((best.get("rawExtraScalars") or {}).keys())
        extra_refs = sorted((best.get("rawExtraRefs") or {}).keys())
        nested_scalars = sorted((best.get("rawNestedScalarKeys") or {}).keys())
        if extra_scalars:
            fields.append("extraScalars=" + ",".join(extra_scalars))
        if extra_refs:
            fields.append("extraRefs=" + ",".join(extra_refs))
        if nested_scalars:
            fields.append("nestedScalars=" + ",".join(nested_scalars))
        parts.append(f"{option.get('optionId')} -> {option.get('candidateLineId')} ({', '.join(fields) or 'no fields'})")
    return "; ".join(parts)


def render_markdown(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = [
        f"# Option Playable Semantics Audit - {summary['language']}",
        "",
        f"- Inferred response groups audited: `{summary['inferredResponseGroupCount']}`",
        f"- Explicit target fields: `{summary['explicitTargetFieldCount']}`",
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
        "## Field Counts",
        "",
        f"- `logicId` top values: `{summary.get('topLogicIds', [])}`",
        f"- `targetFinishNum`: `{summary.get('targetFinishNumCounts', {})}`",
        f"- `conditionRid`: `{summary.get('conditionRidCounts', {})}`",
        f"- Raw option payload keys: `{summary.get('rawPayloadKeyCounts', {})}`",
        f"- Raw extra scalar keys not carried by timeline orders: `{summary.get('rawExtraScalarKeyCounts', {})}`",
        f"- Raw extra reference keys not carried by timeline orders: `{summary.get('rawExtraRefKeyCounts', {})}`",
        f"- Raw nested scalar keys not carried by timeline orders: `{summary.get('rawNestedScalarKeyCounts', {})}`",
        "",
        "## LogicId Diagnostics",
        "",
        f"- Nonzero best-row `logicId` options: `{summary.get('logicIdOptionRowCount', 0)}`",
        f"- Groups with contiguous nonzero best-row `logicId`s: `{summary.get('contiguousLogicIdGroupCount', 0)}`",
        f"- Nonzero best-row `logicId` equals candidate line suffix: `{summary.get('logicIdEqualsCandidateSuffixCount', 0)}`",
        f"- Repeated story `logicId`s with different candidate lines: `{summary.get('repeatedStoryLogicIdConflictCount', 0)}`",
        "",
        "## Repeated LogicId Conflicts",
        "",
        "| Scene | LogicId | Candidate Lines |",
        "| --- | ---: | --- |",
    ])
    for conflict in summary.get("repeatedStoryLogicIdCandidateConflicts", []):
        lines.append(
            "| "
            f"`{md_escape(conflict.get('storyKey'))}` "
            f"| {md_escape(conflict.get('logicId'))} "
            f"| `{md_escape(', '.join(conflict.get('candidateLineIds') or []))}` |"
        )
    if not summary.get("repeatedStoryLogicIdCandidateConflicts"):
        lines.append("| _(none)_ |  |  |")
    lines.extend([
        "",
        "## Groups",
        "",
        "| Scene | Group | After | Candidates | Common | Classification | Recommendation | Option fields |",
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
    suffix = safe_report_suffix(story_filters or [], group_filters or set(), only_interesting)
    out_json = reports_dir / f"option_playable_semantics_audit_{language}{suffix}.json"
    out_md = reports_dir / f"option_playable_semantics_audit_{language}{suffix}.md"
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
    parser.add_argument("--story", action="append", help="Story key, substring, glob, or comma-list to audit.")
    parser.add_argument("--group", action="append", help="Option group number or comma-list to audit.")
    parser.add_argument(
        "--only-interesting",
        action="store_true",
        help="Skip rows that have only default fields or no decoded semantic signal.",
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
    )
    summary = result["summary"]
    print(f"Option playable semantics audit: {result['markdown']}")
    print(f"Option playable semantics data:  {result['json']}")
    print(
        "Audited "
        f"{summary['inferredResponseGroupCount']} inferred response groups; "
        f"{summary['explicitTargetFieldCount']} decoded rows have explicit target fields."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
