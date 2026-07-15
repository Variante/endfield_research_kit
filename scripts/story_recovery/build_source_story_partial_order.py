#!/usr/bin/env python3
"""Build source-only per-mission Story partial-order evidence.

This audit deliberately emits a graph, not a guessed total order.  It reads the
generated Story index and mission bundles, keeps only authored/decoded order
edges, collapses cycles into strongly connected components, and transitively
reduces the resulting component DAG.

It never reads Story-order overrides, OCR proposals, numeric filename suffixes,
generated UI rank, ``sceneOrderInfo.questOrder``, or scene-graph node ``order``.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from common import (  # noqa: E402
    md_escape,
    read_json,
    safe_key,
    write_report_json,
    write_text_if_changed,
)
from story_builder.mission_recovery import (  # noqa: E402
    STRONG_ORDER_EDGE_KINDS,
    WEAK_ORDER_EDGE_KINDS,
    build_scene_order_candidate_kinds,
    natural_key,
    scene_order_infer_kind,
)


SCHEMA = "sourceStoryPartialOrder.v2"

# ``radioContinuation`` combines an authored continuation flag with file-offset
# adjacency.  The builder currently includes it in STRONG_ORDER_EDGE_KINDS,
# while the durable evidence notes still call that combination weak.  Preserve
# it as source evidence without letting it create a proven order relation until
# that policy conflict is intentionally resolved.
SUPPORTED_ORDER_EDGE_KINDS = frozenset({"radioContinuation"})
PROVEN_ORDER_EDGE_KINDS = frozenset(STRONG_ORDER_EDGE_KINDS) - SUPPORTED_ORDER_EDGE_KINDS

EDGE_EVIDENCE_FIELDS = (
    "source",
    "sourceFiles",
    "sourceKeys",
    "questIds",
    "levelIds",
    "optionIds",
    "positions",
    "continuationKinds",
    "fields",
    "entities",
    "prtsRows",
    "firstLvId",
    "fileStems",
)

SOURCE_STORY_NODE_KINDS = frozenset({
    "black",
    "cutscene",
    "dlg",
    "env",
    "misc",
    "radio",
    "remotecomm",
    "runtimeDialog",
    "sns",
    "text",
    "video",
})

EVIDENCE_POLICY = {
    "uses": [
        "index-backed Story scene membership",
        "MissionRuntimeAsset questSequence/questPrev/questFailGuard edges",
        "DialogTree authoredDirect/authoredMenu option routes",
        "DialogTree/DialogTreeFragment option-to-line branchLines verified against sceneGraphLinks",
        "Dialog Timeline Runtime Jump routes with the exact timelineRouteBranches/runtimeJumpTrack signature",
        "typed LevelScript levelscriptSceneChain edges",
        "MissionRuntimeAsset quest branch and merge records",
    ],
    "keepsButDoesNotOrder": [
        "radioContinuation pending evidence-policy reconciliation",
        "LevelScript file/cross-file order and untyped chain membership",
        "LevelData quest references and PRTS collection order",
    ],
    "rejects": [
        "webui/overrides/story_order.json",
        "webui/data/story_order_ocr.json and gameplay-video OCR",
        "sceneOrderInfo.questOrder and flowIndex",
        "sceneGraph.nodes[*].order and generated UI rank",
        "numeric filename suffixes and filesystem/VFS order",
        "manual option or narrative-video overrides",
        "inferredFollowingLines, shared/default option candidates, and option riskTags",
    ],
}


def _edge_tier(kind: str) -> str:
    if kind in PROVEN_ORDER_EDGE_KINDS:
        return "strong"
    if kind in SUPPORTED_ORDER_EDGE_KINDS:
        return "supported"
    if kind in WEAK_ORDER_EDGE_KINDS:
        return "weak"
    return "other"


def _compact_edge(edge: dict[str, Any], tier: str) -> dict[str, Any]:
    row: dict[str, Any] = {
        "from": safe_key(edge.get("from")),
        "to": safe_key(edge.get("to")),
        "kind": safe_key(edge.get("kind")) or "sourceEdge",
        "tier": tier,
    }
    for field in EDGE_EVIDENCE_FIELDS:
        value = edge.get(field)
        if value not in (None, "", [], {}):
            row[field] = value
    return row


def _edge_sort_key(edge: dict[str, Any]) -> tuple[Any, ...]:
    tier_order = {"strong": 0, "supported": 1, "weak": 2, "other": 3}
    return (
        tier_order.get(safe_key(edge.get("tier")), 9),
        natural_key(safe_key(edge.get("from"))),
        natural_key(safe_key(edge.get("to"))),
        safe_key(edge.get("kind")),
    )


def _strongly_connected_components(
    nodes: Iterable[str],
    edges: Iterable[tuple[str, str]],
) -> list[list[str]]:
    """Return deterministic Tarjan SCCs, including singleton components."""
    node_list = sorted(set(nodes), key=natural_key)
    adjacency: dict[str, set[str]] = {node: set() for node in node_list}
    for src, dst in edges:
        if src in adjacency and dst in adjacency:
            adjacency[src].add(dst)

    next_index = 0
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    components: list[list[str]] = []

    def visit(node: str) -> None:
        nonlocal next_index
        indices[node] = next_index
        lowlinks[node] = next_index
        next_index += 1
        stack.append(node)
        on_stack.add(node)

        for successor in sorted(adjacency[node], key=natural_key):
            if successor not in indices:
                visit(successor)
                lowlinks[node] = min(lowlinks[node], lowlinks[successor])
            elif successor in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[successor])

        if lowlinks[node] != indices[node]:
            return
        component: list[str] = []
        while stack:
            member = stack.pop()
            on_stack.remove(member)
            component.append(member)
            if member == node:
                break
        component.sort(key=natural_key)
        components.append(component)

    for node in node_list:
        if node not in indices:
            visit(node)
    components.sort(key=lambda component: natural_key(component[0]))
    return components


def _reachable(
    start: str,
    target: str,
    adjacency: dict[str, set[str]],
    ignored_edge: tuple[str, str] | None = None,
) -> bool:
    pending = [start]
    seen: set[str] = {start}
    while pending:
        node = pending.pop()
        for successor in adjacency.get(node, set()):
            if ignored_edge == (node, successor):
                continue
            if successor == target:
                return True
            if successor not in seen:
                seen.add(successor)
                pending.append(successor)
    return False


def _transitive_reduction(component_edges: set[tuple[str, str]]) -> set[tuple[str, str]]:
    """Reduce an acyclic component graph without relying on third-party code."""
    adjacency: dict[str, set[str]] = defaultdict(set)
    for src, dst in component_edges:
        adjacency[src].add(dst)
    reduced: set[tuple[str, str]] = set()
    for edge in sorted(component_edges, key=lambda item: (natural_key(item[0]), natural_key(item[1]))):
        if not _reachable(edge[0], edge[1], adjacency, ignored_edge=edge):
            reduced.add(edge)
    return reduced


def _topological_layers(
    component_ids: Iterable[str],
    component_edges: Iterable[tuple[str, str]],
) -> list[list[str]]:
    ids = list(component_ids)
    adjacency: dict[str, set[str]] = {component_id: set() for component_id in ids}
    indegree: dict[str, int] = {component_id: 0 for component_id in ids}
    for src, dst in component_edges:
        if dst not in adjacency[src]:
            adjacency[src].add(dst)
            indegree[dst] += 1
    ready = sorted((node for node, degree in indegree.items() if degree == 0), key=natural_key)
    layers: list[list[str]] = []
    emitted = 0
    while ready:
        layer = ready
        layers.append(layer)
        emitted += len(layer)
        next_ready: list[str] = []
        for node in layer:
            for successor in sorted(adjacency[node], key=natural_key):
                indegree[successor] -= 1
                if indegree[successor] == 0:
                    next_ready.append(successor)
        ready = sorted(next_ready, key=natural_key)
    if emitted != len(ids):
        raise ValueError("SCC condensation graph unexpectedly contains a cycle")
    return layers


def _scene_graph_option_branches(direct_edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for edge in direct_edges:
        if edge.get("kind") not in {"authoredDirect", "authoredMenu"}:
            continue
        source = safe_key(edge.get("from"))
        if not source:
            continue
        group = groups.setdefault(source, {"from": source, "sourceKeys": [], "arms": {}})
        for source_key in edge.get("sourceKeys") or []:
            source_key = safe_key(source_key)
            if source_key and source_key not in group["sourceKeys"]:
                group["sourceKeys"].append(source_key)
        option_ids = [safe_key(value) for value in edge.get("optionIds") or [] if safe_key(value)]
        arm_keys = option_ids or ["(unresolved-option)"]
        for option_id in arm_keys:
            arm = group["arms"].setdefault(
                option_id,
                {"optionId": option_id, "targets": [], "edgeKinds": [], "edgeIndexes": []},
            )
            target = safe_key(edge.get("to"))
            if target and target not in arm["targets"]:
                arm["targets"].append(target)
            kind = safe_key(edge.get("kind"))
            if kind and kind not in arm["edgeKinds"]:
                arm["edgeKinds"].append(kind)
            arm["edgeIndexes"].append(edge["edgeIndex"])

    out: list[dict[str, Any]] = []
    for source, group in sorted(groups.items(), key=lambda item: natural_key(item[0])):
        arms = sorted(group.pop("arms").values(), key=lambda arm: natural_key(arm["optionId"]))
        for arm in arms:
            arm["targets"].sort(key=natural_key)
            arm["edgeKinds"].sort()
            arm["edgeIndexes"] = sorted(set(arm["edgeIndexes"]))
        group["sourceKeys"].sort(key=natural_key)
        group["arms"] = arms
        group["isFork"] = len(arms) > 1
        out.append(group)
    return out


def _string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    out: list[str] = []
    for value in values:
        text = safe_key(value)
        if text and text not in out:
            out.append(text)
    return out


def _compact_dialog_option(option: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in {
            "optionId": safe_key(option.get("id")),
            "index": option.get("i"),
            "text": safe_key(option.get("text")),
        }.items()
        if value not in (None, "")
    }


def _compact_option_risk(risk: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "code",
        "reason",
        "detail",
        "source",
        "after",
        "optionIds",
        "candidateLineIds",
        "candidateWindowLineIds",
        "commonContinuationLineId",
        "optionIndex",
        "candidateLineClipOptionIndex",
        "optionIndexPattern",
        "candidateLineClipOptionIndexPattern",
        "candidateMapping",
        "assetTracks",
    )
    return {
        field: risk[field]
        for field in fields
        if risk.get(field) not in (None, "", [], {})
    }


def _dialog_tree_routes(conv: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Index direct DialogTree/DialogTreeFragment routes by option id."""
    story_key = safe_key(conv.get("key"))
    routes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for link in conv.get("sceneGraphLinks") or []:
        if not isinstance(link, dict):
            continue
        source_key = safe_key(link.get("sourceKey"))
        source_debug = (link.get("_debug") or {}).get("source") or {}
        source_file = safe_key(link.get("file")) or safe_key(source_debug.get("file"))
        provenance_kind = "DialogTree" if not source_key or source_key == story_key else "DialogTreeFragment"
        for option_route in link.get("options") or []:
            if not isinstance(option_route, dict):
                continue
            option_id = safe_key(option_route.get("optionId"))
            path_line_ids = _string_list(option_route.get("pathLineIds"))
            if not option_id or not path_line_ids:
                continue
            debug = option_route.get("_debug") if isinstance(option_route.get("_debug"), dict) else {}
            routes[option_id].append({
                "kind": provenance_kind,
                "sourceKey": source_key,
                "sourceFile": source_file,
                "after": safe_key(link.get("after")),
                "firstLineId": safe_key(option_route.get("firstLineId")),
                "pathLineIds": path_line_ids,
                "outcomeKind": safe_key(option_route.get("outcomeKind")),
                "terminal": safe_key(option_route.get("terminal")),
                "sourceOptionNodeId": safe_key(debug.get("sourceOptionNodeId")),
                "startNodeId": safe_key(debug.get("startNodeId")),
                "pathNodeIds": _string_list(debug.get("pathNodeIds")),
                "endNodeId": safe_key(debug.get("endNodeId")),
                "endNodeType": safe_key(debug.get("endNodeType")),
            })
    return routes


def _route_covers_branch_lines(route: dict[str, Any], branch_lines: list[str]) -> bool:
    """Require every promoted line to occur in authored route order."""
    route_lines = route.get("pathLineIds") or []
    cursor = 0
    for branch_line in branch_lines:
        try:
            cursor = route_lines.index(branch_line, cursor) + 1
        except ValueError:
            return False
    return bool(branch_lines)


def _compact_dialog_tree_provenance(route: dict[str, Any]) -> dict[str, Any]:
    return {
        key: route[key]
        for key in (
            "kind",
            "sourceKey",
            "sourceFile",
            "after",
            "firstLineId",
            "pathLineIds",
            "outcomeKind",
            "terminal",
            "sourceOptionNodeId",
            "startNodeId",
            "pathNodeIds",
            "endNodeId",
            "endNodeType",
        )
        if route.get(key) not in (None, "", [], {})
    }


def _is_runtime_jump_branch_risk(risk: dict[str, Any]) -> bool:
    return (
        safe_key(risk.get("code")) == "timelineRouteBranches"
        and safe_key(risk.get("reason")) == "runtimeJumpTrack"
        and safe_key(risk.get("source")) == "dialogTimeline"
        and isinstance(risk.get("branchLineIdsByOption"), dict)
        and bool(risk.get("branchLineIdsByOption"))
    )


def collect_dialog_line_option_branches(
    conv: dict[str, Any],
    conversation_file: str,
) -> dict[str, list[dict[str, Any]]]:
    """Collect strictly source-backed intra-dialog option-to-line routes.

    Allowed routes are either direct DialogTree paths that exactly cover the
    emitted ``branchLines`` without inferred/manual risk, or the exact Runtime
    Jump signature checked by ``_is_runtime_jump_branch_risk``. Everything else
    remains explicit in an exclusion or no-route bucket.
    """
    story_key = safe_key(conv.get("key"))
    direct_routes = _dialog_tree_routes(conv)
    allowed: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    no_route: list[dict[str, Any]] = []

    for group in conv.get("optionGroups") or []:
        if not isinstance(group, dict):
            continue
        group_id = group.get("g")
        options = [option for option in group.get("options") or [] if isinstance(option, dict)]
        option_ids = [safe_key(option.get("id")) for option in options if safe_key(option.get("id"))]
        after = safe_key(group.get("after"))
        risk = group.get("optionBranchRisk") if isinstance(group.get("optionBranchRisk"), dict) else {}
        risk_code = safe_key(risk.get("code"))
        has_manual = bool(group.get("manualOverride")) or risk_code == "manualOptionResponseOverride"
        risk_tagged_options = [
            option
            for option in options
            if isinstance(option.get("riskTags"), list) and option.get("riskTags")
        ]

        base = {
            "storyKey": story_key,
            "group": group_id,
            "after": after,
            "conversationFile": conversation_file,
        }

        if _is_runtime_jump_branch_risk(risk) and not has_manual and not risk_tagged_options:
            branch_map = risk.get("branchLineIdsByOption") or {}
            skipped_map = risk.get("skippedLineIdsByOption") or {}
            runtime_options: list[dict[str, Any]] = []
            complete = True
            for option in options:
                option_id = safe_key(option.get("id"))
                branch_lines = _string_list(branch_map.get(option_id))
                if not option_id or not branch_lines:
                    complete = False
                    break
                runtime_options.append({
                    **_compact_dialog_option(option),
                    "branchLineIds": branch_lines,
                    "skippedLineIds": _string_list(skipped_map.get(option_id)),
                })
            if complete and runtime_options:
                allowed.append({
                    **base,
                    "provenance": {
                        "kind": "DialogTimelineRuntimeJump",
                        "code": "timelineRouteBranches",
                        "reason": "runtimeJumpTrack",
                        "source": "dialogTimeline",
                        "assetTracks": _string_list(risk.get("assetTracks")),
                        "optionIndex": risk.get("optionIndex") or [],
                    },
                    "options": runtime_options,
                    "skippedLineIdsByOption": {
                        option_id: _string_list(values)
                        for option_id, values in skipped_map.items()
                        if _string_list(values)
                    },
                    "reverseRangeLineIdsByOption": {
                        option_id: _string_list(values)
                        for option_id, values in (risk.get("reverseRangeLineIdsByOption") or {}).items()
                        if _string_list(values)
                    },
                    "continuationOptionIds": _string_list(
                        risk.get("continuationOptionIds") or group.get("continuationOptionIds")
                    ),
                })
                continue
            excluded.append({
                **base,
                "optionIds": option_ids,
                "exclusionReason": "incompleteRuntimeJumpMapping",
                "riskEvidence": _compact_option_risk(risk),
            })
            continue

        if has_manual:
            excluded.append({
                **base,
                "optionIds": option_ids,
                "exclusionReason": "manualOptionEvidence",
                "riskEvidence": _compact_option_risk(risk),
            })
            continue
        if risk_tagged_options:
            excluded.append({
                **base,
                "optionIds": option_ids,
                "exclusionReason": "optionRiskTags",
                "riskEvidence": _compact_option_risk(risk),
                "riskTags": [
                    {
                        "optionId": safe_key(option.get("id")),
                        "tags": option.get("riskTags") or [],
                    }
                    for option in risk_tagged_options
                ],
            })
            continue
        if risk and risk_code not in {"dialogTreeBranchConvergence"}:
            excluded.append({
                **base,
                "optionIds": option_ids,
                "exclusionReason": (
                    "sharedOrDefaultCandidates"
                    if risk_code in {"sharedTimelineContinuation", "defaultTimelineContinuation"}
                    else "inferredOrUnsupportedRisk"
                ),
                "riskEvidence": _compact_option_risk(risk),
            })
            continue

        direct_options: list[dict[str, Any]] = []
        direct_failures: list[dict[str, Any]] = []
        any_branch_lines = False
        source_files: list[str] = []
        for option in options:
            option_id = safe_key(option.get("id"))
            branch_lines = _string_list(option.get("branchLines"))
            if not branch_lines:
                continue
            any_branch_lines = True
            matching_route = next(
                (
                    route
                    for route in direct_routes.get(option_id, [])
                    if _route_covers_branch_lines(route, branch_lines)
                ),
                None,
            )
            if not matching_route:
                direct_failures.append({
                    **_compact_dialog_option(option),
                    "branchLineIds": branch_lines,
                })
                continue
            source_file = safe_key(matching_route.get("sourceFile"))
            if source_file and source_file not in source_files:
                source_files.append(source_file)
            direct_options.append({
                **_compact_dialog_option(option),
                "branchLineIds": branch_lines,
                "provenance": _compact_dialog_tree_provenance(matching_route),
            })

        if direct_failures:
            excluded.append({
                **base,
                "optionIds": [row["optionId"] for row in direct_failures],
                "exclusionReason": "branchLinesWithoutDirectDialogTreeProvenance",
                "options": direct_failures,
            })
        if direct_options:
            allowed.append({
                **base,
                "provenance": {
                    "kind": "DialogTreeBranchLines",
                    "sourceFiles": sorted(source_files, key=natural_key),
                    **(
                        {"branchConvergence": _compact_option_risk(risk)}
                        if risk_code == "dialogTreeBranchConvergence"
                        else {}
                    ),
                },
                "options": direct_options,
            })
            continue
        if not any_branch_lines and not direct_failures:
            no_route.append({
                **base,
                "options": [_compact_dialog_option(option) for option in options],
                "reason": "noExplicitSourceRoute",
            })

    return {
        "dialogLineOptions": allowed,
        "excludedDialogLineOptions": excluded,
        "noExplicitRouteGroups": no_route,
    }


def _quest_branches_and_merges(timeline_recovery: dict[str, Any]) -> tuple[list[dict], list[dict]]:
    branches: list[dict] = []
    for row in timeline_recovery.get("branchPoints") or []:
        if not isinstance(row, dict):
            continue
        compact = {
            key: row[key]
            for key in ("questId", "successorQuestIds", "guardedSuccessors", "source")
            if row.get(key) not in (None, "", [], {})
        }
        if compact:
            branches.append(compact)
    branches.sort(key=lambda row: natural_key(safe_key(row.get("questId"))))

    predecessors: dict[str, set[str]] = defaultdict(set)
    evidence: dict[str, list[dict]] = defaultdict(list)
    for edge in timeline_recovery.get("questEdges") or []:
        if not isinstance(edge, dict) or edge.get("kind") != "questPrev":
            continue
        src = safe_key(edge.get("from"))
        dst = safe_key(edge.get("to"))
        if src and dst:
            predecessors[dst].add(src)
            evidence[dst].append(edge)
    merges = [
        {
            "questId": quest_id,
            "predecessorQuestIds": sorted(prev_ids, key=natural_key),
            "sources": [edge.get("source") for edge in evidence[quest_id] if edge.get("source")],
        }
        for quest_id, prev_ids in predecessors.items()
        if len(prev_ids) > 1
    ]
    merges.sort(key=lambda row: natural_key(row["questId"]))
    return branches, merges


def build_mission_partial_order(
    mission: str,
    candidate_kinds: dict[str, str],
    mission_payload: dict[str, Any] | None,
    dialog_payloads: list[tuple[str, dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Build one source-only mission partial order from generated source evidence."""
    mission_payload = mission_payload if isinstance(mission_payload, dict) else {}
    flow = mission_payload.get("flow") if isinstance(mission_payload.get("flow"), dict) else {}
    scene_graph = flow.get("sceneGraph") if isinstance(flow.get("sceneGraph"), dict) else {}
    timeline = (
        mission_payload.get("timelineRecovery")
        if isinstance(mission_payload.get("timelineRecovery"), dict)
        else {}
    )
    candidate_keys = set(candidate_kinds)
    graph_node_kinds = {
        safe_key(node.get("key")): safe_key(node.get("kind"))
        for node in scene_graph.get("nodes") or []
        if isinstance(node, dict) and safe_key(node.get("key"))
    }

    direct_edges: list[dict[str, Any]] = []
    unresolved_nodes: dict[str, set[str]] = defaultdict(set)
    for source_edge in scene_graph.get("edges") or []:
        if not isinstance(source_edge, dict):
            continue
        src = safe_key(source_edge.get("from"))
        dst = safe_key(source_edge.get("to"))
        kind = safe_key(source_edge.get("kind"))
        tier = _edge_tier(kind)
        if src in candidate_keys and dst in candidate_keys:
            direct_edges.append(_compact_edge(source_edge, tier))
            continue
        if tier not in {"strong", "supported"}:
            continue
        for key in (src, dst):
            if key in candidate_keys or not key:
                continue
            if graph_node_kinds.get(key) in SOURCE_STORY_NODE_KINDS:
                unresolved_nodes[key].add(kind)

    direct_edges.sort(key=_edge_sort_key)
    for edge_index, edge in enumerate(direct_edges):
        edge["edgeIndex"] = edge_index

    strong_pairs = [
        (edge["from"], edge["to"])
        for edge in direct_edges
        if edge["tier"] == "strong"
    ]
    components_raw = _strongly_connected_components(candidate_keys, strong_pairs)
    component_by_scene: dict[str, str] = {}
    for component_index, scene_keys in enumerate(components_raw, start=1):
        component_id = f"p{component_index}"
        for scene_key in scene_keys:
            component_by_scene[scene_key] = component_id

    self_loop_scenes = {src for src, dst in strong_pairs if src == dst}
    internal_edges_by_component: dict[str, list[int]] = defaultdict(list)
    evidence_by_component_pair: dict[tuple[str, str], list[int]] = defaultdict(list)
    for edge in direct_edges:
        if edge["tier"] != "strong":
            continue
        src_component = component_by_scene[edge["from"]]
        dst_component = component_by_scene[edge["to"]]
        if src_component == dst_component:
            internal_edges_by_component[src_component].append(edge["edgeIndex"])
        else:
            evidence_by_component_pair[(src_component, dst_component)].append(edge["edgeIndex"])

    component_pairs = set(evidence_by_component_pair)
    reduced_pairs = _transitive_reduction(component_pairs)
    component_ids = [f"p{index}" for index in range(1, len(components_raw) + 1)]
    layers = _topological_layers(component_ids, component_pairs)

    strong_incident: set[str] = set()
    weak_incident: set[str] = set()
    for edge in direct_edges:
        target = strong_incident if edge["tier"] == "strong" else weak_incident
        target.update((edge["from"], edge["to"]))

    components: list[dict[str, Any]] = []
    cyclic_scene_keys: set[str] = set()
    for component_index, scene_keys in enumerate(components_raw, start=1):
        component_id = f"p{component_index}"
        cyclic = len(scene_keys) > 1 or any(key in self_loop_scenes for key in scene_keys)
        if cyclic:
            cyclic_scene_keys.update(scene_keys)
        components.append({
            "id": component_id,
            "sceneKeys": scene_keys,
            "cyclic": cyclic,
            "internalEdgeIndexes": sorted(internal_edges_by_component.get(component_id, [])),
        })

    nodes: list[dict[str, Any]] = []
    isolated: list[str] = []
    weak_only: list[str] = []
    unknown: list[str] = []
    for scene_key in sorted(candidate_keys, key=natural_key):
        if scene_key in cyclic_scene_keys:
            status = "cycle"
            unknown.append(scene_key)
        elif scene_key in strong_incident:
            status = "source-ordered"
        elif scene_key in weak_incident:
            status = "weak-only"
            weak_only.append(scene_key)
            unknown.append(scene_key)
        else:
            status = "isolated"
            isolated.append(scene_key)
            unknown.append(scene_key)
        nodes.append({
            "key": scene_key,
            "kind": candidate_kinds.get(scene_key) or "unknown",
            "component": component_by_scene[scene_key],
            "relationStatus": status,
        })

    component_edges = [
        {
            "from": src,
            "to": dst,
            "evidenceEdgeIndexes": sorted(evidence_by_component_pair[(src, dst)]),
        }
        for src, dst in sorted(component_pairs, key=lambda item: (natural_key(item[0]), natural_key(item[1])))
    ]
    reduced_component_edges = [
        {
            "from": src,
            "to": dst,
            "evidenceEdgeIndexes": sorted(evidence_by_component_pair[(src, dst)]),
        }
        for src, dst in sorted(reduced_pairs, key=lambda item: (natural_key(item[0]), natural_key(item[1])))
    ]

    component_sizes = {
        f"p{index}": len(scene_keys)
        for index, scene_keys in enumerate(components_raw, start=1)
    }
    component_adjacency: dict[str, set[str]] = defaultdict(set)
    for src, dst in component_pairs:
        component_adjacency[src].add(dst)
    comparable_pairs = 0
    for component_id in component_ids:
        for other_id in component_ids:
            if component_id == other_id:
                continue
            if _reachable(component_id, other_id, component_adjacency):
                comparable_pairs += component_sizes[component_id] * component_sizes[other_id]
    total_pairs = len(candidate_keys) * (len(candidate_keys) - 1) // 2
    cyclic_internal_pairs = sum(
        len(scene_keys) * (len(scene_keys) - 1) // 2
        for scene_keys in components_raw
        if len(scene_keys) > 1
    )

    quest_branches, quest_merges = _quest_branches_and_merges(timeline)
    scene_graph_option_branches = _scene_graph_option_branches(direct_edges)
    dialog_line_options: list[dict[str, Any]] = []
    excluded_dialog_line_options: list[dict[str, Any]] = []
    no_explicit_route_groups: list[dict[str, Any]] = []
    for conversation_file, conv in dialog_payloads or []:
        if not isinstance(conv, dict):
            continue
        dialog_routes = collect_dialog_line_option_branches(conv, conversation_file)
        dialog_line_options.extend(dialog_routes["dialogLineOptions"])
        excluded_dialog_line_options.extend(dialog_routes["excludedDialogLineOptions"])
        no_explicit_route_groups.extend(dialog_routes["noExplicitRouteGroups"])
    dialog_row_sort_key = lambda row: (  # noqa: E731 - shared compact sort key
        natural_key(safe_key(row.get("storyKey"))),
        row.get("group") if isinstance(row.get("group"), int) else 10**9,
        safe_key(row.get("group")),
    )
    dialog_line_options.sort(key=dialog_row_sort_key)
    excluded_dialog_line_options.sort(key=dialog_row_sort_key)
    no_explicit_route_groups.sort(key=dialog_row_sort_key)
    dialog_line_route_count = sum(len(row.get("options") or []) for row in dialog_line_options)
    dialog_line_count = sum(
        len(option.get("branchLineIds") or [])
        for row in dialog_line_options
        for option in row.get("options") or []
        if isinstance(option, dict)
    )
    dialog_line_provenance_counts = Counter(
        safe_key((row.get("provenance") or {}).get("kind"))
        for row in dialog_line_options
        if safe_key((row.get("provenance") or {}).get("kind"))
    )
    excluded_dialog_line_option_count = sum(
        len(row.get("options") or row.get("optionIds") or [])
        for row in excluded_dialog_line_options
    )
    no_explicit_route_option_count = sum(
        len(row.get("options") or [])
        for row in no_explicit_route_groups
    )
    cycles = [component for component in components if component["cyclic"]]
    tier_counts = Counter(edge["tier"] for edge in direct_edges)
    kind_counts = Counter(edge["kind"] for edge in direct_edges)
    warnings: list[str] = []
    if not mission_payload:
        warnings.append("missingMissionBundle")
    if cycles:
        warnings.append("sourceEdgeCycle")

    return {
        "mission": mission,
        "summary": {
            "sceneCount": len(candidate_keys),
            "directEdgeCount": len(direct_edges),
            "strongEdgeCount": tier_counts.get("strong", 0),
            "supportedEdgeCount": tier_counts.get("supported", 0),
            "weakEdgeCount": tier_counts.get("weak", 0),
            "otherEdgeCount": tier_counts.get("other", 0),
            "componentCount": len(components),
            "reducedComponentEdgeCount": len(reduced_component_edges),
            "cycleCount": len(cycles),
            "isolatedSceneCount": len(isolated),
            "weakOnlySceneCount": len(weak_only),
            "unknownSceneCount": len(unknown),
            "totalScenePairs": total_pairs,
            "comparableScenePairs": comparable_pairs,
            "unorderedScenePairs": total_pairs - comparable_pairs,
            "cyclicInternalPairs": cyclic_internal_pairs,
            "sceneGraphOptionGroupCount": len(scene_graph_option_branches),
            "questForkCount": len(quest_branches),
            "questMergeCount": len(quest_merges),
            "dialogLineOptionGroupCount": len(dialog_line_options),
            "dialogLineOptionRouteCount": dialog_line_route_count,
            "dialogLineOptionLineCount": dialog_line_count,
            "excludedDialogLineOptionGroupCount": len(excluded_dialog_line_options),
            "excludedDialogLineOptionCount": excluded_dialog_line_option_count,
            "noExplicitRouteGroupCount": len(no_explicit_route_groups),
            "noExplicitRouteOptionCount": no_explicit_route_option_count,
            "dialogLineOptionProvenance": dict(sorted(dialog_line_provenance_counts.items())),
            "edgeKinds": dict(sorted(kind_counts.items())),
        },
        "nodes": nodes,
        "components": components,
        "componentEdges": component_edges,
        "reducedComponentEdges": reduced_component_edges,
        "topologicalLayers": layers,
        "directEdges": direct_edges,
        "cycles": cycles,
        "branches": {
            "sceneGraphOptions": scene_graph_option_branches,
            "dialogLineOptions": dialog_line_options,
            "excludedDialogLineOptions": excluded_dialog_line_options,
            "noExplicitRouteGroups": no_explicit_route_groups,
            "questForks": quest_branches,
            "questMerges": quest_merges,
        },
        "isolatedSceneKeys": isolated,
        "weakOnlySceneKeys": weak_only,
        "unknownSceneKeys": unknown,
        "unresolvedSourceNodes": [
            {
                "key": key,
                "kind": graph_node_kinds.get(key) or "unknown",
                "incidentEdgeKinds": sorted(kinds),
            }
            for key, kinds in sorted(unresolved_nodes.items(), key=lambda item: natural_key(item[0]))
        ],
        "warnings": warnings,
    }


def _split_missions(values: list[str]) -> set[str]:
    return {
        mission.strip()
        for value in values
        for mission in str(value).split(",")
        if mission.strip()
    }


def build_report(language: str, selected_missions: set[str] | None = None) -> dict[str, Any]:
    lang_root = ROOT / "webui" / "data" / "lang" / language
    index_path = lang_root / "index.json"
    mission_dir = lang_root / "mission"
    conversation_dir = lang_root / "conv"
    index_payload = read_json(index_path, {})
    index_entries = index_payload.get("entries") if isinstance(index_payload, dict) else []
    index_entries = index_entries if isinstance(index_entries, list) else []
    missions = sorted(
        {
            safe_key(entry.get("m"))
            for entry in index_entries
            if isinstance(entry, dict) and safe_key(entry.get("m"))
        },
        key=natural_key,
    )
    if selected_missions:
        missions = [mission for mission in missions if mission in selected_missions]

    rows: list[dict[str, Any]] = []
    totals: Counter[str] = Counter()
    edge_kind_totals: Counter[str] = Counter()
    for mission in missions:
        candidate_kinds = build_scene_order_candidate_kinds(index_entries, mission, None)
        if not candidate_kinds:
            continue
        mission_path = mission_dir / f"{mission}.json"
        mission_payload = read_json(mission_path, {}) if mission_path.is_file() else {}
        dialog_payloads: list[tuple[str, dict[str, Any]]] = []
        for story_key in sorted(candidate_kinds, key=natural_key):
            if not story_key.startswith("dlg_"):
                continue
            conversation_path = conversation_dir / f"{story_key}.json"
            if not conversation_path.is_file():
                continue
            conversation_payload = read_json(conversation_path, {})
            if isinstance(conversation_payload, dict):
                dialog_payloads.append((conversation_path.relative_to(ROOT).as_posix(), conversation_payload))
        row = build_mission_partial_order(
            mission,
            candidate_kinds,
            mission_payload,
            dialog_payloads,
        )
        row["missionData"] = (
            mission_path.relative_to(ROOT).as_posix() if mission_path.is_file() else ""
        )
        rows.append(row)
        summary = row["summary"]
        totals["missions"] += 1
        totals["scenes"] += summary["sceneCount"]
        totals["directEdges"] += summary["directEdgeCount"]
        totals["strongEdges"] += summary["strongEdgeCount"]
        totals["supportedEdges"] += summary["supportedEdgeCount"]
        totals["weakEdges"] += summary["weakEdgeCount"]
        totals["otherEdges"] += summary["otherEdgeCount"]
        totals["components"] += summary["componentCount"]
        totals["reducedComponentEdges"] += summary["reducedComponentEdgeCount"]
        totals["cycles"] += summary["cycleCount"]
        totals["isolatedScenes"] += summary["isolatedSceneCount"]
        totals["weakOnlyScenes"] += summary["weakOnlySceneCount"]
        totals["unknownScenes"] += summary["unknownSceneCount"]
        totals["totalScenePairs"] += summary["totalScenePairs"]
        totals["comparableScenePairs"] += summary["comparableScenePairs"]
        totals["unorderedScenePairs"] += summary["unorderedScenePairs"]
        totals["sceneGraphOptionGroups"] += summary["sceneGraphOptionGroupCount"]
        totals["questForks"] += summary["questForkCount"]
        totals["questMerges"] += summary["questMergeCount"]
        totals["dialogLineOptionGroups"] += summary["dialogLineOptionGroupCount"]
        totals["dialogLineOptionRoutes"] += summary["dialogLineOptionRouteCount"]
        totals["dialogLineOptionLines"] += summary["dialogLineOptionLineCount"]
        totals["excludedDialogLineOptionGroups"] += summary["excludedDialogLineOptionGroupCount"]
        totals["excludedDialogLineOptions"] += summary["excludedDialogLineOptionCount"]
        totals["noExplicitRouteGroups"] += summary["noExplicitRouteGroupCount"]
        totals["noExplicitRouteOptions"] += summary["noExplicitRouteOptionCount"]
        totals["missingMissionBundles"] += int("missingMissionBundle" in row["warnings"])
        totals["missionsWithStrongEdges"] += int(summary["strongEdgeCount"] > 0)
        totals["missionsWithCycles"] += int(summary["cycleCount"] > 0)
        edge_kind_totals.update(summary["edgeKinds"])

    dialog_provenance_totals: Counter[str] = Counter()
    for row in rows:
        dialog_provenance_totals.update(row["summary"]["dialogLineOptionProvenance"])

    total_pairs = totals["totalScenePairs"]
    summary_payload = dict(totals)
    summary_payload["comparablePairRate"] = (
        round(totals["comparableScenePairs"] / total_pairs, 6) if total_pairs else 0.0
    )
    summary_payload["edgeKinds"] = dict(sorted(edge_kind_totals.items()))
    summary_payload["dialogLineOptionProvenance"] = dict(sorted(dialog_provenance_totals.items()))
    return {
        "_schema": SCHEMA,
        "_generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "language": language,
        "inputs": {
            "index": index_path.relative_to(ROOT).as_posix(),
            "missionDir": mission_dir.relative_to(ROOT).as_posix(),
            "conversationDir": conversation_dir.relative_to(ROOT).as_posix(),
        },
        "evidencePolicy": EVIDENCE_POLICY,
        "summary": summary_payload,
        "missions": rows,
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Source-only Story Partial Order",
        "",
        f"Generated: `{report['_generatedAt']}`",
        "",
        "This report emits only source-evidence relations. It does not create or replace",
        "the canonical Story order, and it never reads manual/OCR order inputs.",
        "",
        "## Summary",
        "",
        f"- missions: `{summary.get('missions', 0)}`",
        f"- candidate scenes: `{summary.get('scenes', 0)}`",
        f"- direct evidence edges: `{summary.get('directEdges', 0)}` "
        f"(`{summary.get('strongEdges', 0)}` strong, `{summary.get('supportedEdges', 0)}` supported, "
        f"`{summary.get('weakEdges', 0)}` weak)",
        f"- reduced component edges: `{summary.get('reducedComponentEdges', 0)}`",
        f"- cyclic components: `{summary.get('cycles', 0)}` across "
        f"`{summary.get('missionsWithCycles', 0)}` missions",
        f"- isolated scenes: `{summary.get('isolatedScenes', 0)}`",
        f"- weak-only scenes: `{summary.get('weakOnlyScenes', 0)}`",
        f"- comparable source-proven pairs: `{summary.get('comparableScenePairs', 0)}` / "
        f"`{summary.get('totalScenePairs', 0)}` (`{summary.get('comparablePairRate', 0.0):.2%}`)",
        f"- strict intra-dialog option routes: `{summary.get('dialogLineOptionRoutes', 0)}` options "
        f"in `{summary.get('dialogLineOptionGroups', 0)}` groups, covering "
        f"`{summary.get('dialogLineOptionLines', 0)}` branch lines",
        f"- mission-level branches: `{summary.get('questForks', 0)}` quest forks, "
        f"`{summary.get('questMerges', 0)}` quest merges, and "
        f"`{summary.get('sceneGraphOptionGroups', 0)}` authored cross-scene option groups",
        f"- excluded option evidence: `{summary.get('excludedDialogLineOptions', 0)}` options "
        f"in `{summary.get('excludedDialogLineOptionGroups', 0)}` groups",
        f"- option groups with no explicit route: `{summary.get('noExplicitRouteGroups', 0)}` "
        f"(`{summary.get('noExplicitRouteOptions', 0)}` options)",
        "",
        "## Evidence Policy",
        "",
        "Order-bearing edge kinds: "
        + ", ".join(f"`{kind}`" for kind in sorted(PROVEN_ORDER_EDGE_KINDS))
        + ".",
        "",
        "Supported/weak evidence is retained in JSON but does not create component order.",
        "Unknown pairs and isolated scenes remain explicit; topological layers are partial-order",
        "frontiers, not a total sequence.",
        "",
        "## Missions",
        "",
        "| mission | scenes | strong edges | reduced edges | cycles | isolated | weak-only | comparable pairs |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in report["missions"]:
        item = row["summary"]
        lines.append(
            f"| `{md_escape(row['mission'])}` | {item['sceneCount']} | {item['strongEdgeCount']} | "
            f"{item['reducedComponentEdgeCount']} | {item['cycleCount']} | "
            f"{item['isolatedSceneCount']} | {item['weakOnlySceneCount']} | "
            f"{item['comparableScenePairs']} / {item['totalScenePairs']} |"
        )

    cycle_rows = [row for row in report["missions"] if row["summary"]["cycleCount"]]
    lines.extend([
        "",
        "## Source-edge Cycles",
        "",
        "Cycles are collapsed before reduction; no internal order is asserted.",
        "",
        "| mission | cyclic components | scenes in cycles |",
        "| --- | ---: | ---: |",
    ])
    if cycle_rows:
        for row in cycle_rows:
            scene_count = sum(len(cycle["sceneKeys"]) for cycle in row["cycles"])
            lines.append(f"| `{md_escape(row['mission'])}` | {len(row['cycles'])} | {scene_count} |")
    else:
        lines.append("| _(none)_ | 0 | 0 |")

    unknown_rows = sorted(
        report["missions"],
        key=lambda row: (-row["summary"]["unknownSceneCount"], natural_key(row["mission"])),
    )[:30]
    lines.extend([
        "",
        "## Largest Unknown Sets",
        "",
        "| mission | unknown | isolated | weak-only | total |",
        "| --- | ---: | ---: | ---: | ---: |",
    ])
    for row in unknown_rows:
        item = row["summary"]
        lines.append(
            f"| `{md_escape(row['mission'])}` | {item['unknownSceneCount']} | "
            f"{item['isolatedSceneCount']} | {item['weakOnlySceneCount']} | {item['sceneCount']} |"
        )
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", default="CN")
    parser.add_argument(
        "--mission",
        action="append",
        default=[],
        help="Limit to a mission id; comma-separated values and repeats are accepted.",
    )
    parser.add_argument("--reports-dir", type=Path, default=ROOT / "reports" / "mission_order")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(args.language, _split_missions(args.mission) or None)
    out_json = args.reports_dir / f"source_story_partial_order_{args.language}.json"
    out_md = args.reports_dir / f"source_story_partial_order_{args.language}.md"
    write_report_json(out_json, report)
    write_text_if_changed(out_md, render_markdown(report))
    summary = report["summary"]
    print(f"Source-only partial order: {out_md.relative_to(ROOT)}")
    print(f"Source-only partial-order data: {out_json.relative_to(ROOT)}")
    print(
        f"{summary.get('missions', 0)} missions; {summary.get('scenes', 0)} scenes; "
        f"{summary.get('strongEdges', 0)} strong edges; "
        f"{summary.get('comparablePairRate', 0.0):.2%} comparable pairs"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
