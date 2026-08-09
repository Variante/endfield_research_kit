#!/usr/bin/env python3
"""Audit unresolved option responses against authored DialogTree route evidence.

`story_builder/build.py` already decodes a lot of AnimeStudio DialogTree structure.
This report asks whether remaining `inferredOptionResponse` groups are missing
because source files are absent, because the tree parser sees only anchors, or
because the authored tree contains route evidence the WebUI has not promoted.
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
import story_builder as story
from common import (
    ROOT,
    compact_dict,
    md_escape,
    parse_group_filters,
    read_json,
    rel_path,
    safe_key,
    safe_report_suffix,
    split_csv_values,
    unique_preserve,
    write_report_json as write_json,
)
from scene_order_gap_shared import (
    load_dialog_id_registry,
    registry_lines_by_trunk,
    registry_options_by_group,
    runtime_dialog_scene_key,
)


def compact_cinematic_anchor(anchor: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(anchor, dict):
        return {}
    return compact_dict({
        "sourceKey": safe_key(anchor.get("sourceKey")),
        "file": safe_key(anchor.get("file")),
        "timeline": safe_key(anchor.get("timeline")),
        "nodeId": safe_key(anchor.get("nodeId")),
        "after": safe_key(anchor.get("after")),
        "before": safe_key(anchor.get("before")),
        "targetNodeIds": [safe_key(value) for value in anchor.get("targetNodeIds") or [] if safe_key(value)],
        "targetCount": anchor.get("targetCount"),
    })


def compact_cinematic_finish_group(group: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(group, dict):
        return {}
    return compact_dict({
        "sourceKey": safe_key(group.get("sourceKey")),
        "file": safe_key(group.get("file")),
        "timeline": safe_key(group.get("timeline")),
        "nodeId": safe_key(group.get("nodeId")),
        "after": safe_key(group.get("after")),
        "finishNums": list(group.get("finishNums") or []),
        "targetNodeIds": [safe_key(value) for value in group.get("targetNodeIds") or [] if safe_key(value)],
        "targetCount": group.get("targetCount"),
    })


def compact_action_asset_names(value: Any, limit: int = 12) -> list[str]:
    names: list[str] = []
    if isinstance(value, dict):
        for key in value:
            key_text = safe_key(key)
            if key_text:
                names.append(key_text)
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                text = safe_key(item.get("name") or item.get("timeline") or item.get("sourceKey"))
            else:
                text = safe_key(item)
            if text:
                names.append(text)
    return unique_preserve(names)[:limit]


def compact_source(meta: dict[str, Any] | None, kind: str) -> dict[str, Any] | None:
    if not isinstance(meta, dict):
        return None

    def signal_count(value: Any) -> int:
        if isinstance(value, (dict, list, tuple, set)):
            return len(value)
        if safe_key(value):
            return 1
        return 0

    out = {
        "kind": kind,
        "sourceKey": safe_key(meta.get("sourceKey")),
        "file": safe_key(meta.get("file")),
        "lineCount": len(meta.get("lineIds") or []),
        "optionCount": len(meta.get("optionIds") or []),
    }
    signal_counts = {
        "terminal": sum((meta.get("terminalCounts") or {}).values()),
        "after": signal_count(meta.get("after")),
        "branches": signal_count(meta.get("branches")),
        "merge": signal_count(meta.get("merge")),
        "converge": signal_count(meta.get("converge")),
        "pre": signal_count(meta.get("pre")),
        "actionAssets": len(meta.get("actionAssets") or {}),
        "cinematicTimelineAnchors": len(meta.get("cinematicTimelineAnchors") or {}),
        "sceneLinks": len(meta.get("sceneLinks") or []),
        "targetFragments": len(meta.get("targetFragments") or []),
        "cinematicFinishGroups": len(meta.get("cinematicFinishGroups") or []),
    }
    route_recovery = meta.get("optionRouteRecovery") or {}
    route_counts = route_recovery.get("counts") or {}
    for key in (
        "validatedNormalOptionRoutes",
        "rejectedNormalOptionRoutes",
        "runtimeDefaultConnectionIndexes",
        "explicitConnectionIndexes",
        "connectionCountMismatchNodes",
        "extraOptionNodes",
        "unreferencedOptionDefinitionNodes",
        "linkedOptionNodesWithoutOutgoingConnections",
        "linkedOptionNodesWithPartialIndexCoverage",
        "serializedConnectionIndexesOutOfBounds",
    ):
        if route_counts.get(key):
            signal_counts[key] = route_counts[key]
    out["signalCounts"] = {key: value for key, value in signal_counts.items() if value}
    if action_assets := compact_action_asset_names(meta.get("actionAssets")):
        out["actionAssets"] = action_assets
    anchors = [
        compact
        for anchor in (meta.get("cinematicTimelineAnchors") or [])
        if (compact := compact_cinematic_anchor(anchor))
    ]
    if anchors:
        out["cinematicTimelineAnchors"] = anchors[:8]
        if len(anchors) > 8:
            out["cinematicTimelineAnchorsOmitted"] = len(anchors) - 8
    finish_groups = [
        compact
        for group in (meta.get("cinematicFinishGroups") or [])
        if (compact := compact_cinematic_finish_group(group))
    ]
    if finish_groups:
        out["cinematicFinishGroups"] = finish_groups[:8]
        if len(finish_groups) > 8:
            out["cinematicFinishGroupsOmitted"] = len(finish_groups) - 8
    if meta.get("cinematicOnly"):
        out["cinematicOnly"] = True
    return out


def load_conv_line_ids(conv_dir: Path, story_key: str) -> list[str]:
    conv = read_json(conv_dir / f"{story_key}.json", {})
    if not isinstance(conv, dict):
        return []
    return [
        safe_key(line.get("id"))
        for line in conv.get("lines") or []
        if isinstance(line, dict) and safe_key(line.get("id"))
    ]


def tree_sources_for_group(
    story_key: str,
    line_ids: list[str],
) -> tuple[list[dict[str, Any]], dict[str, Any] | None, list[dict[str, Any]], list[dict[str, Any]]]:
    direct = story._load_dialog_tree_file(story_key)
    related = story._load_related_dialog_tree_files(story_key, line_ids)
    fragments = story.load_dialog_tree_fragments(story_key)
    scene_links = story.load_dialog_tree_scene_links(story_key)
    sources: list[dict[str, Any]] = []
    if direct_source := compact_source(direct, "direct"):
        sources.append(direct_source)
    for meta in related:
        if source := compact_source(meta, "related"):
            sources.append(source)
    for fragment in fragments:
        if source := compact_source(fragment, "fragment"):
            sources.append(source)
    for link in scene_links:
        if source := compact_source(link, "sceneLink"):
            source["optionCount"] = len(link.get("options") or [])
            sources.append(source)
    return sources, direct, fragments, scene_links


def option_ids_in_fragment_groups(fragment: dict[str, Any], option_id: str) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for group in fragment.get("optionGroups") or []:
        if not isinstance(group, dict):
            continue
        if option_id not in (group.get("optionIds") or []):
            continue
        entry: dict[str, Any] = {
            "sourceKey": safe_key(fragment.get("sourceKey")),
            "file": safe_key(fragment.get("file")),
            "mode": safe_key(group.get("mode")),
            "after": safe_key(group.get("after")),
            "position": safe_key(group.get("position")),
        }
        if group.get("branches"):
            entry["branches"] = group.get("branches")
        if group.get("merge"):
            entry["merge"] = group.get("merge")
        matches.append({key: value for key, value in entry.items() if value not in ("", [], {})})
    return matches


def option_scene_link_matches(scene_links: list[dict[str, Any]], option_id: str) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for link in scene_links:
        for option in link.get("options") or []:
            if not isinstance(option, dict) or option.get("optionId") != option_id:
                continue
            entry: dict[str, Any] = {
                "sourceKey": safe_key(link.get("sourceKey")),
                "file": safe_key(link.get("file")),
                "after": safe_key(link.get("after")),
                "outcomeKind": safe_key(option.get("outcomeKind")),
                "firstLineId": safe_key(option.get("firstLineId")),
                "firstSceneKey": safe_key(option.get("firstSceneKey")),
                "terminal": safe_key(option.get("terminal")),
            }
            for field in ("pathLineIds", "sceneKeys", "submenuSceneKeys"):
                if option.get(field):
                    entry[field] = option.get(field)
            if option.get("loop"):
                entry["loop"] = option.get("loop")
            if option.get("routeEvidence"):
                entry["routeEvidence"] = option.get("routeEvidence")
            matches.append({key: value for key, value in entry.items() if value not in ("", [], {})})
    return matches


def option_evidence(
    option: dict[str, Any],
    tree_meta: dict[str, Any] | None,
    fragments: list[dict[str, Any]],
    scene_links: list[dict[str, Any]],
) -> dict[str, Any]:
    option_id = safe_key(option.get("optionId"))
    tree_meta = tree_meta or {}
    branches = (tree_meta.get("branches") or {}).get(option_id) or []
    merge = safe_key((tree_meta.get("merge") or {}).get(option_id))
    converge = safe_key((tree_meta.get("converge") or {}).get(option_id))
    after = safe_key((tree_meta.get("after") or {}).get(option_id))
    pre = option_id in (tree_meta.get("pre") or [])
    fragment_matches: list[dict[str, Any]] = []
    for fragment in fragments:
        fragment_matches.extend(option_ids_in_fragment_groups(fragment, option_id))
    scene_link_matches = option_scene_link_matches(scene_links, option_id)
    out: dict[str, Any] = {
        "optionId": option_id,
        "candidateLineId": safe_key(option.get("candidateLineId")),
        "treeAfter": after,
        "treeBranches": branches,
        "treeMerge": merge,
        "treeConverge": converge,
        "treePre": pre,
        "treeAfterSources": (tree_meta.get("afterSources") or {}).get(option_id) or [],
        "treePreSources": (tree_meta.get("preSources") or {}).get(option_id) or [],
        "fragmentMatches": fragment_matches,
        "sceneLinkMatches": scene_link_matches,
        "timelineRoute": option.get("route") or {},
        "bestTimelineRow": option.get("bestRow") or {},
    }
    return compact_dict(out, empty_values=("", [], {}, False))


def candidate_match_count(option_details: list[dict[str, Any]]) -> int:
    matches = 0
    for detail in option_details:
        candidate = safe_key(detail.get("candidateLineId"))
        if not candidate:
            continue
        if any(candidate in signature for signature in option_route_signatures(detail)):
            matches += 1
    return matches


def option_route_signatures(detail: dict[str, Any]) -> set[tuple[str, ...]]:
    signatures: set[tuple[str, ...]] = set()
    branches = tuple(safe_key(value) for value in detail.get("treeBranches") or [] if safe_key(value))
    if branches:
        signatures.add(branches)
    for match in detail.get("sceneLinkMatches") or []:
        path = tuple(safe_key(value) for value in match.get("pathLineIds") or [] if safe_key(value))
        if path:
            signatures.add(path)
            continue
        if first_line_id := safe_key(match.get("firstLineId")):
            signatures.add((first_line_id,))
        elif terminal := safe_key(match.get("terminal")):
            signatures.add((f"terminal:{terminal}",))
    return signatures


def option_route_signature_sets(option_details: list[dict[str, Any]]) -> list[set[tuple[str, ...]]]:
    return [option_route_signatures(detail) for detail in option_details]


def has_shared_route(option_details: list[dict[str, Any]]) -> bool:
    signature_sets = option_route_signature_sets(option_details)
    if len(signature_sets) < 2 or not all(signature_sets):
        return False
    union: set[tuple[str, ...]] = set()
    for signatures in signature_sets:
        union.update(signatures)
    return len(union) == 1


def as_report_int(value: Any) -> int | None:
    return semantics.as_int(value)


def best_timeline_field_values(option_details: list[dict[str, Any]], field: str) -> list[int]:
    values: list[int] = []
    for detail in option_details:
        best_row = detail.get("bestTimelineRow") or {}
        value = as_report_int(best_row.get(field))
        if value is not None:
            values.append(value)
    return values


def option_field_matrix(option_details: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = (
        "optionIndex",
        "clipOptionIndex",
        "index",
        "logicId",
        "conditionRid",
        "changeFinishNum",
        "targetFinishNum",
        "anchorMode",
        "start",
        "duration",
        "trackName",
    )
    rows: list[dict[str, Any]] = []
    for detail in option_details:
        best_row = detail.get("bestTimelineRow") or {}
        row = {
            "optionId": safe_key(detail.get("optionId")),
            "candidateLineId": safe_key(detail.get("candidateLineId")),
        }
        for field in fields:
            if best_row.get(field) not in (None, "", [], {}):
                row[field] = best_row.get(field)
        rows.append(compact_dict(row))
    return rows


def cinematic_diagnostics(
    row: dict[str, Any],
    tree_sources: list[dict[str, Any]],
    option_details: list[dict[str, Any]],
) -> dict[str, Any]:
    anchors: list[dict[str, Any]] = []
    finish_groups: list[dict[str, Any]] = []
    for source in tree_sources:
        anchors.extend(source.get("cinematicTimelineAnchors") or [])
        finish_groups.extend(source.get("cinematicFinishGroups") or [])

    finish_nums_by_group: list[list[int]] = []
    for group in finish_groups:
        values = [
            value
            for value in (as_report_int(raw) for raw in group.get("finishNums") or [])
            if value is not None
        ]
        if values:
            finish_nums_by_group.append(values)

    field_values = {
        field: best_timeline_field_values(option_details, field)
        for field in (
            "optionIndex",
            "clipOptionIndex",
            "index",
            "logicId",
            "conditionRid",
            "changeFinishNum",
            "targetFinishNum",
        )
    }
    option_finish_signal = [
        {
            "optionId": safe_key(detail.get("optionId")),
            "changeFinishNum": (detail.get("bestTimelineRow") or {}).get("changeFinishNum"),
            "targetFinishNum": (detail.get("bestTimelineRow") or {}).get("targetFinishNum"),
        }
        for detail in option_details
        if (detail.get("bestTimelineRow") or {}).get("changeFinishNum") not in (None, "", 0)
        or (detail.get("bestTimelineRow") or {}).get("targetFinishNum") not in (None, "", 0, -1)
    ]

    finish_matches: list[dict[str, Any]] = []
    all_finish_nums = {value for values in finish_nums_by_group for value in values}
    if all_finish_nums:
        for field, values in field_values.items():
            value_set = set(values)
            exact = sorted(value_set & all_finish_nums)
            plus_one = sorted({value for value in value_set if value + 1 in all_finish_nums})
            minus_one = sorted({value for value in value_set if value - 1 in all_finish_nums})
            if exact or plus_one or minus_one:
                finish_matches.append(compact_dict({
                    "field": field,
                    "exact": exact,
                    "valuePlusOne": plus_one,
                    "valueMinusOne": minus_one,
                }))

    timeline = safe_key(row.get("timeline"))
    timeline_matches = [
        safe_key(group.get("timeline"))
        for group in finish_groups
        if timeline and safe_key(group.get("timeline")) == timeline
    ]

    return compact_dict({
        "timeline": timeline,
        "timelineAnchorCount": len(anchors),
        "finishGroupCount": len(finish_groups),
        "cinematicTimelines": unique_preserve([
            safe_key(item.get("timeline"))
            for item in [*anchors, *finish_groups]
            if safe_key(item.get("timeline"))
        ]),
        "timelineMatches": unique_preserve(timeline_matches),
        "finishNums": finish_nums_by_group,
        "finishNumberFieldMatches": finish_matches,
        "optionFinishSignals": option_finish_signal,
        "optionFields": option_field_matrix(option_details),
        "anchors": anchors[:4],
        "finishGroups": finish_groups[:4],
    })


def runtime_registry_evidence(story_key: str, dialog_id_registry: dict[str, Any]) -> dict[str, Any] | None:
    scene_key = runtime_dialog_scene_key(story_key)
    if not scene_key or not scene_key.startswith("dlg_"):
        return None
    info = dialog_id_registry.get(scene_key)
    if not isinstance(info, dict):
        return {
            "registered": False,
            "sceneKey": scene_key,
        }
    lines_by_trunk = registry_lines_by_trunk(info)
    options_by_group = registry_options_by_group(info)
    out: dict[str, Any] = {
        "registered": True,
        "sceneKey": scene_key,
        "trunkCount": info.get("trunkCount", 0),
        "trunkIndices": info.get("trunkIndices", []),
        "lineCount": info.get("lineCount", 0),
    }
    if lines_by_trunk:
        out["linesByTrunk"] = lines_by_trunk
    if options_by_group:
        out["optionGroupCount"] = len(options_by_group)
        out["optionCount"] = sum(len(values) for values in options_by_group.values())
        out["optionsByGroup"] = options_by_group
    return out


def classify_group(
    row: dict[str, Any],
    tree_sources: list[dict[str, Any]],
    option_details: list[dict[str, Any]],
    runtime_registry: dict[str, Any] | None = None,
) -> tuple[str, str]:
    has_tree_source = bool(tree_sources)
    option_count = len(row.get("options") or [])
    branch_count = sum(1 for detail in option_details if detail.get("treeBranches"))
    scene_route_count = sum(
        1
        for detail in option_details
        if any(
            match.get("firstLineId") or match.get("pathLineIds") or match.get("terminal") or match.get("loop")
            for match in detail.get("sceneLinkMatches") or []
        )
    )
    convergence_values = {
        safe_key(detail.get("treeConverge"))
        for detail in option_details
        if safe_key(detail.get("treeConverge"))
    }
    anchor_count = sum(1 for detail in option_details if detail.get("treeAfter") or detail.get("treePre"))
    fragment_signal_count = sum(1 for detail in option_details if detail.get("fragmentMatches"))
    route_match_count = candidate_match_count(option_details)

    if has_shared_route(option_details):
        return "treeSharedRoute", "avoidPerOptionInferenceOrCollapseToSharedRoute"
    if option_count and route_match_count == option_count:
        return "explicitTreeRoute", "promoteDialogTreeRoute"
    if branch_count or scene_route_count:
        if route_match_count:
            return "treeRoutePartialMatch", "inspectParserOrCandidateMapping"
        return "treeRouteCandidateMismatch", "inspectParserOrCandidateMapping"
    if convergence_values and len(convergence_values) == 1:
        common = safe_key(row.get("commonContinuationLineId"))
        recommendation = "treatAsCosmeticOrConverged" if common in convergence_values else "inspectConvergenceMapping"
        return "treeConvergence", recommendation
    if anchor_count:
        return "treeAnchorOnly", "needsRuntimeMethodBodyOrOptionNodeTargetDecode"
    if fragment_signal_count:
        return "treeFragmentOnly", "inspectFragmentPromotion"
    if has_tree_source:
        only_cinematic_sources = all(
            bool(source.get("cinematicOnly"))
            or (
                not source.get("optionCount")
                and not (source.get("signalCounts") or {}).get("branches")
                and not (source.get("signalCounts") or {}).get("after")
                and bool((source.get("signalCounts") or {}).get("actionAssets"))
            )
            for source in tree_sources
        )
        if only_cinematic_sources and any(option.get("bestTimelineRow") for option in option_details):
            return "cinematicTreeTimelineOnly", "needsRuntimeMethodBodyOrTimelineTargetDecode"
        mentioned_options = sum(
            1
            for detail in option_details
            if detail.get("treeAfter")
            or detail.get("treeBranches")
            or detail.get("treeMerge")
            or detail.get("treeConverge")
            or detail.get("treePre")
            or detail.get("sceneLinkMatches")
            or detail.get("fragmentMatches")
        )
        if mentioned_options:
            return "treePresentNoRouteDecoded", "patchDialogTreeDecoder"
        if option_count:
            if runtime_registry and runtime_registry.get("linesByTrunk"):
                return "treePresentRuntimeTrunkOnly", "decodeRuntimeTrunkOptionMapping"
            return "treePresentOptionMissing", "recoverMissingTreeOrOptionIds"
        return "treePresentNoOptionGroup", "inspectWarningSource"
    if any(option.get("bestTimelineRow") for option in option_details):
        return "timelineOnlyNoTree", "needsRuntimeMethodBodyOrTimelineTargetDecode"
    return "sourceMissing", "findAdditionalGameDataSource"


def collect_rows(
    language: str,
    conv_dir: Path,
    timeline_orders_path: Path,
    *,
    story_filters: list[str] | None = None,
    group_filters: set[int] | None = None,
    only_interesting: bool = False,
) -> list[dict[str, Any]]:
    semantics_rows = semantics.collect_rows(
        language,
        conv_dir,
        timeline_orders_path,
        story_filters=story_filters,
        group_filters=group_filters,
        only_interesting=only_interesting,
    )
    rows: list[dict[str, Any]] = []
    dialog_id_registry = load_dialog_id_registry()
    for row in semantics_rows:
        story_key = safe_key(row.get("storyKey"))
        line_ids = load_conv_line_ids(conv_dir, story_key)
        tree_sources, _direct, fragments, scene_links = tree_sources_for_group(story_key, line_ids)
        tree_meta = story.load_dialog_tree(story_key) or {}
        option_details = [
            option_evidence(option, tree_meta, fragments, scene_links)
            for option in row.get("options") or []
        ]
        runtime_registry = runtime_registry_evidence(story_key, dialog_id_registry)
        classification, recommendation = classify_group(
            row, tree_sources, option_details, runtime_registry
        )
        cinematic = cinematic_diagnostics(row, tree_sources, option_details)
        rows.append({
            "language": language,
            "storyKey": story_key,
            "mission": row.get("mission"),
            "group": row.get("group"),
            "timeline": row.get("timeline"),
            "after": row.get("after"),
            "candidateLineIds": row.get("candidateLineIds") or [],
            "commonContinuationLineId": row.get("commonContinuationLineId"),
            "semanticsClassification": row.get("classification"),
            "semanticsRecommendation": row.get("recommendation"),
            "classification": classification,
            "recommendation": recommendation,
            "treeSources": tree_sources,
            "treeSourceKeys": unique_preserve([source.get("sourceKey") for source in tree_sources if source.get("sourceKey")]),
            "optionDetails": option_details,
            "cinematicDiagnostics": cinematic,
            "runtimeRegistry": runtime_registry,
        })
    rows.sort(key=lambda item: (item.get("mission") or "", item.get("storyKey") or "", item.get("group") or 0))
    return rows


def runtime_option_ids_for_group(row: dict[str, Any]) -> list[str]:
    registry = row.get("runtimeRegistry") or {}
    if not isinstance(registry, dict):
        return []
    options_by_group = registry.get("optionsByGroup") or {}
    if not isinstance(options_by_group, dict):
        return []
    group = safe_key(row.get("group"))
    values = options_by_group.get(group) or []
    if not isinstance(values, list):
        return []
    return [safe_key(value) for value in values if safe_key(value)]


def runtime_group_contains_all_options(row: dict[str, Any]) -> bool:
    runtime_ids = set(runtime_option_ids_for_group(row))
    option_ids = {
        safe_key(detail.get("optionId"))
        for detail in row.get("optionDetails") or []
        if safe_key(detail.get("optionId"))
    }
    return bool(option_ids) and option_ids.issubset(runtime_ids)


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
    semantic_classifications = Counter(row.get("semanticsClassification") or "" for row in rows)
    source_kinds = Counter(
        source.get("kind") or ""
        for row in rows
        for source in row.get("treeSources") or []
    )
    route_candidate_hit_groups = sum(1 for row in rows if candidate_match_count(row.get("optionDetails") or []))
    runtime_registry_line_groups = sum(
        1 for row in rows if (row.get("runtimeRegistry") or {}).get("linesByTrunk")
    )
    runtime_registry_option_groups = sum(1 for row in rows if runtime_option_ids_for_group(row))
    runtime_registry_complete_option_groups = sum(1 for row in rows if runtime_group_contains_all_options(row))
    cinematic_anchor_groups = sum(
        1 for row in rows if (row.get("cinematicDiagnostics") or {}).get("timelineAnchorCount")
    )
    cinematic_finish_groups = sum(
        1 for row in rows if (row.get("cinematicDiagnostics") or {}).get("finishGroupCount")
    )
    option_finish_signal_groups = sum(
        1 for row in rows if (row.get("cinematicDiagnostics") or {}).get("optionFinishSignals")
    )
    finish_number_match_groups = sum(
        1 for row in rows if (row.get("cinematicDiagnostics") or {}).get("finishNumberFieldMatches")
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
        "semanticsClassificationCounts": dict(semantic_classifications),
        "sourceKindCounts": dict(source_kinds),
        "routeCandidateHitGroupCount": route_candidate_hit_groups,
        "explicitPerOptionRouteGroupCount": classifications.get("explicitTreeRoute", 0),
        "sharedRouteGroupCount": classifications.get("treeSharedRoute", 0),
        "runtimeRegistryLineGroupCount": runtime_registry_line_groups,
        "runtimeRegistryOptionGroupCount": runtime_registry_option_groups,
        "runtimeRegistryCompleteOptionGroupCount": runtime_registry_complete_option_groups,
        "cinematicTimelineAnchorGroupCount": cinematic_anchor_groups,
        "cinematicFinishGroupCount": cinematic_finish_groups,
        "optionFinishSignalGroupCount": option_finish_signal_groups,
        "finishNumberFieldMatchGroupCount": finish_number_match_groups,
    }


def option_summary(row: dict[str, Any]) -> str:
    parts: list[str] = []
    for detail in row.get("optionDetails") or []:
        fields: list[str] = []
        if detail.get("treeBranches"):
            fields.append("branches=" + ",".join(safe_key(value) for value in detail.get("treeBranches") or []))
        if detail.get("treeConverge"):
            fields.append(f"converge={detail.get('treeConverge')}")
        if detail.get("treeAfter"):
            fields.append(f"after={detail.get('treeAfter')}")
        if detail.get("sceneLinkMatches"):
            firsts = [
                safe_key(match.get("firstLineId") or match.get("terminal") or match.get("outcomeKind"))
                for match in detail.get("sceneLinkMatches") or []
            ]
            fields.append("sceneLink=" + ",".join(value for value in firsts if value))
        if detail.get("fragmentMatches"):
            fields.append(f"fragments={len(detail.get('fragmentMatches') or [])}")
        best_row = detail.get("bestTimelineRow") or {}
        if best_row.get("logicId") not in (None, "", 0):
            fields.append(f"logicId={best_row.get('logicId')}")
        if best_row.get("conditionRid") not in (None, "", -2):
            fields.append(f"conditionRid={best_row.get('conditionRid')}")
        if best_row.get("changeFinishNum") not in (None, "", 0):
            fields.append(f"changeFinishNum={best_row.get('changeFinishNum')}")
        if best_row.get("targetFinishNum") not in (None, "", 0, -1):
            fields.append(f"targetFinishNum={best_row.get('targetFinishNum')}")
        parts.append(
            f"{detail.get('optionId')} -> {detail.get('candidateLineId')} "
            f"({'; '.join(fields) or 'no tree route'})"
        )
    return "; ".join(parts)


def runtime_summary(row: dict[str, Any]) -> str:
    registry = row.get("runtimeRegistry") or {}
    if not isinstance(registry, dict):
        return ""
    if registry.get("registered") is False:
        return "unregistered"
    lines_by_trunk = registry.get("linesByTrunk") or {}
    parts: list[str] = []
    if isinstance(lines_by_trunk, dict):
        for trunk, line_ids in lines_by_trunk.items():
            values = [safe_key(value) for value in line_ids or [] if safe_key(value)]
            if values:
                parts.append(f"trunk {trunk}: " + ",".join(values))
    runtime_option_ids = runtime_option_ids_for_group(row)
    if runtime_option_ids:
        group = safe_key(row.get("group"))
        parts.append(f"options {group}: " + ",".join(runtime_option_ids))
    if parts:
        return "; ".join(parts)
    if registry.get("registered") is True:
        return "registered"
    return ""


def cinematic_summary(row: dict[str, Any]) -> str:
    diagnostics = row.get("cinematicDiagnostics") or {}
    if not isinstance(diagnostics, dict):
        return ""
    parts: list[str] = []
    if diagnostics.get("timelineAnchorCount"):
        parts.append(f"anchors={diagnostics.get('timelineAnchorCount')}")
    if diagnostics.get("finishGroupCount"):
        parts.append(f"finishGroups={diagnostics.get('finishGroupCount')}")
    if diagnostics.get("cinematicTimelines"):
        parts.append("timelines=" + ",".join(diagnostics.get("cinematicTimelines") or []))
    if diagnostics.get("finishNums"):
        finish_sets = [
            "/".join(str(value) for value in values)
            for values in diagnostics.get("finishNums") or []
        ]
        parts.append("finishNums=" + ",".join(finish_sets[:4]))
    if diagnostics.get("finishNumberFieldMatches"):
        matches = [
            safe_key(match.get("field"))
            for match in diagnostics.get("finishNumberFieldMatches") or []
            if safe_key(match.get("field"))
        ]
        parts.append("matches=" + ",".join(matches))
    if diagnostics.get("optionFinishSignals"):
        parts.append(f"optionFinishSignals={len(diagnostics.get('optionFinishSignals') or [])}")
    return "; ".join(parts)


def render_markdown(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = [
        f"# DialogTree Option Route Audit - {summary['language']}",
        "",
        f"- Inferred response groups audited: `{summary['inferredResponseGroupCount']}`",
        f"- Authored route candidate-hit groups: `{summary['routeCandidateHitGroupCount']}`",
        f"- Explicit per-option authored routes: `{summary['explicitPerOptionRouteGroupCount']}`",
        f"- Shared authored routes: `{summary['sharedRouteGroupCount']}`",
        f"- Groups with DialogIdTable trunk line refs: `{summary['runtimeRegistryLineGroupCount']}`",
        f"- Groups with DialogIdTable option refs for the current group: `{summary['runtimeRegistryOptionGroupCount']}`",
        f"- Groups whose current WebUI options are all present in DialogIdTable: `{summary['runtimeRegistryCompleteOptionGroupCount']}`",
        f"- Groups with cinematic Timeline anchors: `{summary['cinematicTimelineAnchorGroupCount']}`",
        f"- Groups with cinematic finish-number branches: `{summary['cinematicFinishGroupCount']}`",
        f"- Groups with option finish-number fields: `{summary['optionFinishSignalGroupCount']}`",
        f"- Groups where finish-number fields match cinematic finish nums: `{summary['finishNumberFieldMatchGroupCount']}`",
        "",
        "## Classification Counts",
        "",
    ]
    for key, count in summary.get("classificationCounts", {}).items():
        lines.append(f"- `{key}`: {count}")
    lines.extend(["", "## Recommendation Counts", ""])
    for key, count in summary.get("recommendationCounts", {}).items():
        lines.append(f"- `{key}`: {count}")
    lines.extend(["", "## Source Kind Counts", ""])
    for key, count in summary.get("sourceKindCounts", {}).items():
        lines.append(f"- `{key}`: {count}")
    lines.extend([
        "",
        "## Groups",
        "",
        "| Scene | Group | After | Candidates | Common | Class | Recommendation | Sources | Runtime | Cinematic | Evidence |",
        "| --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in rows:
        sources = ", ".join(row.get("treeSourceKeys") or [])
        lines.append(
            "| "
            f"`{md_escape(row.get('storyKey'))}` "
            f"| {md_escape(row.get('group'))} "
            f"| `{md_escape(row.get('after'))}` "
            f"| `{md_escape(', '.join(row.get('candidateLineIds') or []))}` "
            f"| `{md_escape(row.get('commonContinuationLineId'))}` "
            f"| `{md_escape(row.get('classification'))}` "
            f"| `{md_escape(row.get('recommendation'))}` "
            f"| `{md_escape(sources)}` "
            f"| `{md_escape(runtime_summary(row))}` "
            f"| `{md_escape(cinematic_summary(row))}` "
            f"| {md_escape(option_summary(row))} |"
        )
    if not rows:
        lines.append("| _(none)_ |  |  |  |  |  |  |  |  |  |  |")
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
    out_json = reports_dir / f"dialog_tree_option_route_audit_{language}{suffix}.json"
    out_md = reports_dir / f"dialog_tree_option_route_audit_{language}{suffix}.md"
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
    )
    summary = result["summary"]
    print(f"DialogTree option route audit: {result['markdown']}")
    print(f"DialogTree option route data:  {result['json']}")
    print(
        "Audited "
        f"{summary['inferredResponseGroupCount']} inferred response groups; "
        f"{summary['routeCandidateHitGroupCount']} groups have authored route candidate hits; "
        f"{summary['explicitPerOptionRouteGroupCount']} are explicit per-option routes."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
