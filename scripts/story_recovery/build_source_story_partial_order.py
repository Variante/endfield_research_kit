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
import hashlib
import json
import os
import re
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
from story_builder.level_bindings import (  # noqa: E402
    LEVELSCRIPT_NATIVE_CONTROL_RUNTIME_MAPPINGS,
    LEVELSCRIPT_NATIVE_EXACT_CONTROL_PATH_STATUSES,
    build_levelscript_action_story_occurrences,
    decode_levelscript_native_action_topology,
)
from story_builder.anime_assets import (  # noqa: E402
    recover_dialog_tree_narrative_mask_actions,
    recover_dialog_tree_open_ui_content_actions,
)
from story_builder.spawner_binary import (  # noqa: E402
    SPAWNER_WAVE_RUNTIME_MAPPING_ID,
    SpawnerWaveDecodeError,
    decode_spawner_wave_map,
)


SCHEMA = "sourceStoryPartialOrder.v37"
BRANCH_SEQUENCE_RUNTIME = LEVELSCRIPT_NATIVE_CONTROL_RUNTIME_MAPPINGS[
    (0x002D, 0x09)
]
BRANCH_SEQUENCE_GAME_ASSEMBLY_SHA256 = (
    "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE"
)
_NATIVE_ACTION_TOPOLOGY_CACHE: dict[str, tuple[dict, dict | None]] = {}
NATIVE_LEVELSCRIPT_ROOTS = (
    ROOT / "export_full" / "structured" / "StreamingAssets"
    / "Data" / "Json" / "LevelScriptData",
    ROOT / "export_full" / "structured" / "Persistent"
    / "Data" / "Json" / "LevelScriptData",
)
NATIVE_SERIALIZED_BRANCH_INVENTORY_SCHEMA = (
    "nativeSerializedBranchInventory.v5"
)
READING_POPUP_TABLE_PATH = (
    ROOT / "export_full" / "structured" / "StreamingAssets"
    / "Table" / "ReadingPopUpTable.json"
)
PROTOCOL_REGISTRY_AUDIT_PATH = (
    ROOT / "reports" / "story" / "recovery" / "protocol_registry_audit.json"
)
VARIANT_FLOW_LIST_FIELDS = (
    "missionStoryConnections",
    "missionStateStoryDependencies",
    "quests",
    "unlinkedNativePlayback",
    "unlinkedDefinitionOnly",
    "unresolvedDialogTreeNarrativeActions",
    "unlinkedDialogTreeNarrativeActions",
)
VARIANT_TIMELINE_LIST_FIELDS = (
    "branchPoints",
    "questEdges",
    "quests",
    "sourceBackedStoryCallContexts",
    "unresolved",
)
VARIANT_TIMELINE_DICT_FIELDS = (
    "scenePlacement",
)
SPAWNER_CONFIG_ROOTS = (
    ROOT / "export_full" / "structured" / "StreamingAssets"
    / "Data" / "Json" / "SpawnerConfig",
    ROOT / "export_full" / "structured" / "Persistent"
    / "Data" / "Json" / "SpawnerConfig",
)

# These relations are original-data topology, but not strict chronology.
#
# ``questSequence`` is assembled by the Story builder from heterogeneous
# quest-local reference collections.  The installed QuestInfo/MissionRuntime
# binary contract exposes ``prevQuestIdList`` and BuildConnectionBetweenLayers,
# but no playback-order contract for that concatenated collection.
#
# ``questFailGuard`` is an authored branch-closing dependency, not proof that
# both referenced Story files execute in one order. ``authoredMenu`` preserves
# DialogTree menu/submenu reachability and can be cyclic by design.
#
# ``levelscriptSceneChain`` follows generic Story-looking payloads through the
# legacy UID/nextId chain view. The installed ActionBase formatter table proves
# that these payloads also occur on preload, remove, override, and stop actions;
# the old chain view can also cross physical ActionSerializedMap list roots.
# Preserve the relation as control/configuration topology, but require the
# typed native playback/control-path decoder for chronology.
#
# ``radioContinuation`` combines an authored continuation flag with file-offset
# adjacency. Preserve all four as source evidence without letting them create a
# proven order relation.
SUPPORTED_ORDER_EDGE_KINDS = frozenset({
    "authoredMenu",
    "levelscriptSceneChain",
    "questFailGuard",
    "questSequence",
    "radioContinuation",
})
PROVEN_ORDER_EDGE_KINDS = (
    frozenset(STRONG_ORDER_EDGE_KINDS) - SUPPORTED_ORDER_EDGE_KINDS
) | frozenset({
    "dialogTreeCrossStoryConditionalBranch",
    "dialogTreeCrossStoryTrunkContinuation",
    "levelscriptNativeControlPath",
    "levelscriptNativeOrderedSequence",
    "levelscriptQuestStateActionPath",
    "questSucceedLifecycle",
    "spawnerWaveGroupPartKilled",
    "spawnerWavePartKilled",
})

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
    "event",
    "events",
    "sourceScript",
    "headerLocalId",
    "targetLocalId",
    "sourceLocalId",
    "actionPathLocalIds",
    "questState",
    "spawnerId",
    "waveKey",
    "targetWaveKey",
    "waveId",
    "waveMode",
    "waveModeKillCount",
    "groupKey",
    "targetGroupKey",
    "spawnerDependencyPath",
    "runtimeMappingId",
    "schemaMappingId",
    "fromActions",
    "toActions",
    "fromActionClasses",
    "toActionClasses",
    "condition",
    "conditionTrueConnectionIndex",
    "conditionFalseConnectionIndex",
    "parentArmLineIds",
    "childArmLineIds",
    "nativeConsumers",
    "gameAssemblySha256",
)


# Current-build declarations are deliberately narrow and hash locked.  They
# turn an exact serialized DialogTree branch into chronology only after both
# the carrier paths and the current GameAssembly branch-selection contract
# have been audited.  A mismatch emits an actionable warning and no edge.
DIALOG_TREE_CONDITIONAL_BRANCH_DECLARATIONS = {
    ("gm02m14", "dlg_gm02m14_1", "dlg_gm02m14_3"): {
        "sourceFile": (
            "export_full/recovered/AnimeStudio-cli/StreamingAssets/"
            "json_by_type/TextAsset/"
            "dlg_gm02m14_1_p4C5228BE5CCE25DA.json"
        ),
        "sourceSha256": (
            "018DFF862D1EBDA9B0336EDF81F1D862DC2E71271EE0C7695248F507261A00D1"
        ),
        "nativeMappingId": "dialog-tree-reachable-story-playback-native-v1",
        "optionId": "option_dlg_gm02m14_1_2_001",
        "optionAfterLineId": "dlg_gm02m14_1_005",
        "branchAfterLineId": "dlg_gm02m14_1_006",
        "branchNodeId": "9",
        "parentLineIds": tuple(
            f"dlg_gm02m14_1_{number:03d}" for number in range(1, 10)
        ),
        "parentArmLineIds": (
            "dlg_gm02m14_1_007",
            "dlg_gm02m14_1_008",
            "dlg_gm02m14_1_009",
        ),
        "childArmLineIds": (
            "dlg_gm02m14_3_001",
            "dlg_gm02m14_3_002",
            "dlg_gm02m14_3_003",
        ),
        "carrierNodePaths": {
            "dlg_gm02m14_3_001": ("8", "9", "14"),
            "dlg_gm02m14_3_002": ("8", "9", "14", "15"),
            "dlg_gm02m14_3_003": ("8", "9", "14", "15", "16", "17"),
        },
        "carrierConnectionIndexes": {
            "dlg_gm02m14_3_001": (10, 12),
            "dlg_gm02m14_3_002": (10, 12, 16),
            "dlg_gm02m14_3_003": (10, 12, 16, 17, 18),
        },
        "condition": {
            "type": "Beyond.Gameplay.CheckLevelScriptPropertyBool",
            "mapId": "map02_lv005",
            "scriptId": 90002,
            "key": "canskip",
            "value": True,
        },
        "conditionTrueConnectionIndex": 1,
        "conditionFalseConnectionIndex": 0,
        "conditionTrueTargetNodeId": "14",
        "conditionFalseTargetNodeId": "10",
        "gameAssemblySha256": (
            "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE"
        ),
        "nativeConsumers": (
            {
                "method": "DialogTreeIfNode.GetNextIndex",
                "token": "0x06003be3",
                "address": "0x1872a51f8",
                "contract": (
                    "returns outgoing index 1 exactly when "
                    "GameCondition.result equals 1"
                ),
            },
            {
                "method": "GameCondition.Activate",
                "token": "0x0600489f",
                "address": "0x18332c000",
            },
            {
                "method": "GameCondition.get_result",
                "token": "0x06004884",
                "address": "0x183a8ad10",
            },
        ),
    },
}


def _configured_game_assembly_path() -> Path:
    game_root = os.environ.get("ENDFIELD_GAME_ROOT", "").strip()
    if not game_root:
        paths_file = ROOT / "endfield_paths.bat"
        text = paths_file.read_text(encoding="utf-8", errors="replace")
        match = re.search(
            r'^set\s+"ENDFIELD_GAME_ROOT=([^"\r\n]+)"',
            text,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        game_root = match.group(1).strip() if match else ""
    return (
        Path(game_root).parent / "GameAssembly.dll"
        if game_root else Path()
    )


def load_mission_payload_with_variants(
    mission_dir: Path,
    mission: str,
) -> dict[str, Any]:
    """Load one generated mission bundle plus its declared graph variants.

    The Story index groups variant-prefixed Story keys under the base mission,
    and the base bundle's ``sceneGraph`` already records which exact variant
    mission bundles contributed to that combined graph. Preserve the base
    graph, but merge only the evidence collections consumed by this audit so
    native routes and quest diagnostics from those declared variants are not
    silently dropped.
    """
    mission_path = mission_dir / f"{mission}.json"
    payload = read_json(mission_path, {}) if mission_path.is_file() else {}
    if not isinstance(payload, dict):
        return {}
    base_flow = payload.get("flow")
    base_flow = base_flow if isinstance(base_flow, dict) else {}
    variant_ids = sorted({
        safe_key(value)
        for value in base_flow.get("sceneGraphVariantMissions") or []
        if safe_key(value) and safe_key(value) != mission
    }, key=natural_key)
    if not variant_ids:
        return payload

    merged_payload = dict(payload)
    merged_flow = dict(base_flow)
    for field in VARIANT_FLOW_LIST_FIELDS:
        merged_flow[field] = list(base_flow.get(field) or [])
    base_timeline = payload.get("timelineRecovery")
    base_timeline = base_timeline if isinstance(base_timeline, dict) else {}
    merged_timeline = dict(base_timeline)
    for field in VARIANT_TIMELINE_LIST_FIELDS:
        merged_timeline[field] = list(base_timeline.get(field) or [])
    for field in VARIANT_TIMELINE_DICT_FIELDS:
        value = base_timeline.get(field)
        merged_timeline[field] = dict(value) if isinstance(value, dict) else {}

    accepted_variants: list[str] = []
    accepted_files: list[str] = []
    for variant_id in variant_ids:
        variant_path = mission_dir / f"{variant_id}.json"
        variant_payload = (
            read_json(variant_path, {}) if variant_path.is_file() else {}
        )
        if (
            not isinstance(variant_payload, dict)
            or safe_key(variant_payload.get("mission")) != variant_id
        ):
            continue
        variant_flow = variant_payload.get("flow")
        variant_flow = variant_flow if isinstance(variant_flow, dict) else {}
        for field in VARIANT_FLOW_LIST_FIELDS:
            merged_flow[field].extend(variant_flow.get(field) or [])
        variant_timeline = variant_payload.get("timelineRecovery")
        variant_timeline = (
            variant_timeline if isinstance(variant_timeline, dict) else {}
        )
        for field in VARIANT_TIMELINE_LIST_FIELDS:
            merged_timeline[field].extend(variant_timeline.get(field) or [])
        for field in VARIANT_TIMELINE_DICT_FIELDS:
            value = variant_timeline.get(field)
            if isinstance(value, dict):
                merged_timeline[field].update(value)
        accepted_variants.append(variant_id)
        accepted_files.append(variant_path.as_posix())

    if not accepted_variants:
        return payload
    merged_flow["_sourceVariantMissionIds"] = accepted_variants
    merged_payload["flow"] = merged_flow
    merged_payload["timelineRecovery"] = merged_timeline
    merged_payload["_sourceMissionVariantFiles"] = accepted_files
    return merged_payload

DEFINITION_ONLY_SOURCE_RECORD_CLASSES = frozenset({
    "preload_cutscene",
})

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
        "index-backed nominal Story scene membership",
        "cross-owner Story context only when an indexed Story card, exact typed LevelScript final-playback occurrence, and mission scene-chain source file all agree",
        "cross-owner Story context only when an exact serialized native control path strictly prefixes or extends an index-backed scene path under the same event header",
        "MissionRuntimeAsset questPrev edges backed by prevQuestIdList",
        "DialogTree authoredDirect option routes",
        "DialogTree/DialogTreeFragment option-to-line branchLines verified against sceneGraphLinks",
        "Dialog Timeline Runtime Jump routes with the exact timelineRouteBranches/runtimeJumpTrack signature",
        "Dialog Timeline branch clips with complete distinct positive runtime optionIndex coverage and convergent post-response jumps",
        "LevelScript LevelEvent_OnDialogExit action-chain edges",
        "exact serialized LevelScript event-to-action strict path-prefix edges",
        "exact Branch._idList Story order only when installed Branch.Execute semantics and distinct serialized sequence slots agree",
        "exact LevelEvent_OnQuestStateChanged typed playback action paths",
        "same-quest objective Story completion before a typed succeed client Story action, gated by the current installed SucceedQuest binary contract",
        "exact SpawnerConfig PartKilled target-wave dependencies joined to typed LevelEvent_OnSpawnerWaveBegin playback",
        "exact SpawnerConfig wave/group nesting and PartKilled gates joined to typed wave/group-begin playback",
        "exact same-script RaiseCustomScriptEvent relays from typed spawner callbacks to typed Story playback listeners",
        "MissionRuntimeAsset quest branch and merge records",
    ],
    "keepsButDoesNotOrder": [
        "quest-local Story reference collection order (questSequence)",
        "MissionRuntimeAsset failed-condition topology (questFailGuard)",
        "DialogTree menu/submenu reachability (authoredMenu)",
        "generic LevelScript scene-reference nextId chains (levelscriptSceneChain)",
        "SpawnerConfig Sequence/Parallel modes and HP-threshold callbacks without an exact named target-wave dependency",
        "reciprocal questPrev projections between reusable Story file nodes",
        "radioContinuation pending evidence-policy reconciliation",
        "LevelScript file/cross-file order and untyped chain membership",
        "LevelData quest references and PRTS collection order",
        "related LevelScript action graphs attached through exact Story paths but not promoted wholesale to mission order",
        "divergent Split/IfElseAction/SwitchInt/SwitchString Story arms as topology only",
        "authored quest-start Story actions when the complete current AOT dispatcher census has no slot-1 producer",
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


def _demote_reciprocal_quest_projections(edges: list[dict[str, Any]]) -> None:
    """Keep occurrence-ambiguous quest projections out of the strict DAG.

    ``prevQuestIdList`` orders quest instances. Once multiple quest instances
    are projected onto the same Story file node, opposite file-level edges can
    both appear even though the quest DAG itself is directed. That proves
    attachment/topology, not one global order between the two reusable files.
    """
    quest_pairs = {
        (safe_key(edge.get("from")), safe_key(edge.get("to")))
        for edge in edges
        if safe_key(edge.get("kind")) == "questPrev"
    }
    reciprocal_pairs = {
        pair
        for pair in quest_pairs
        if (pair[1], pair[0]) in quest_pairs
    }
    for edge in edges:
        pair = (safe_key(edge.get("from")), safe_key(edge.get("to")))
        if safe_key(edge.get("kind")) != "questPrev" or pair not in reciprocal_pairs:
            continue
        edge["tier"] = "supported"
        edge["demotionReason"] = "reciprocalQuestProjection"


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
        "commonContinuationLineIds",
        "directContinuationOptionIds",
        "terminatingOptionIds",
        "optionIndex",
        "optionStartTimes",
        "optionAnchors",
        "foreignOptionIds",
        "timeline",
        "finishNums",
        "targetFinishNums",
        "candidateLineClipOptionIndex",
        "optionIndexPattern",
        "candidateLineClipOptionIndexPattern",
        "candidateMapping",
        "assetTracks",
        "optionNodeLayouts",
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


def _dialog_tree_non_line_outcomes(
    conv: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Index exact authored option outcomes that do not target local lines."""
    story_key = safe_key(conv.get("key"))
    outcomes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for link in conv.get("sceneGraphLinks") or []:
        if not isinstance(link, dict):
            continue
        source_key = safe_key(link.get("sourceKey"))
        source_debug = (link.get("_debug") or {}).get("source") or {}
        source_file = safe_key(link.get("file")) or safe_key(source_debug.get("file"))
        if not source_file:
            continue
        provenance_kind = (
            "DialogTree"
            if not source_key or source_key == story_key
            else "DialogTreeFragment"
        )
        for raw in link.get("options") or []:
            if not isinstance(raw, dict):
                continue
            option_id = safe_key(raw.get("optionId"))
            if not option_id:
                continue
            path_line_ids = _string_list(raw.get("pathLineIds"))
            has_non_line_outcome = bool(
                safe_key(raw.get("terminal"))
                or safe_key(raw.get("outcomeKind"))
                or safe_key(raw.get("firstSceneKey"))
                or _string_list(raw.get("submenuSceneKeys"))
                or isinstance(raw.get("conditionalOutcomes"), list)
                or isinstance(raw.get("loop"), dict)
            )
            if not has_non_line_outcome:
                continue
            outcome = {
                "kind": provenance_kind,
                "sourceKey": source_key,
                "sourceFile": source_file,
                "after": safe_key(link.get("after")),
                "firstLineId": safe_key(raw.get("firstLineId")),
                "firstSceneKey": safe_key(raw.get("firstSceneKey")),
                "pathLineIds": path_line_ids,
                "sceneKeys": _string_list(raw.get("sceneKeys")),
                "submenuSceneKeys": _string_list(raw.get("submenuSceneKeys")),
                "outcomeKind": safe_key(raw.get("outcomeKind")),
                "terminal": safe_key(raw.get("terminal")),
            }
            if isinstance(raw.get("conditionalOutcomes"), list):
                outcome["conditionalOutcomes"] = raw[
                    "conditionalOutcomes"
                ]
            loop = raw.get("loop")
            if isinstance(loop, dict) and loop:
                outcome["loop"] = loop
            outcomes[option_id].append({
                key: value
                for key, value in outcome.items()
                if value not in (None, "", [], {})
            })
    return outcomes


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


def _is_timeline_clip_option_index_branch_risk(risk: dict[str, Any]) -> bool:
    return (
        safe_key(risk.get("code")) == "timelineClipOptionIndexBranches"
        and safe_key(risk.get("reason")) == "runtimeClipOptionIndex"
        and safe_key(risk.get("source")) == "dialogTimeline"
        and safe_key(risk.get("candidateMapping")) == "trunkClipOptionIndex"
        and isinstance(risk.get("branchLineIdsByOption"), dict)
        and bool(risk.get("branchLineIdsByOption"))
    )


def collect_dialog_line_option_branches(
    conv: dict[str, Any],
    conversation_file: str,
) -> dict[str, list[dict[str, Any]]]:
    """Collect strictly source-backed intra-dialog option-to-line routes.

    Allowed routes are direct DialogTree paths that exactly cover the emitted
    ``branchLines`` without inferred/manual risk, exact Runtime Jump routes, or
    complete distinct positive Timeline clip optionIndex routes. Everything
    else remains explicit in an exclusion or no-route bucket.
    """
    story_key = safe_key(conv.get("key"))
    direct_routes = _dialog_tree_routes(conv)
    non_line_outcomes = _dialog_tree_non_line_outcomes(conv)
    runtime_registry = (
        (conv.get("_debug") or {}).get("runtimeRegistry")
        if isinstance(conv.get("_debug"), dict)
        and isinstance((conv.get("_debug") or {}).get("runtimeRegistry"), dict)
        else {}
    )
    unregistered_scene = runtime_registry.get("registered") is False
    compact_runtime_registry = {
        key: runtime_registry[key]
        for key in (
            "registered",
            "sceneKey",
            "reason",
            "hasSummary",
            "summaryKey",
            "summaryNote",
        )
        if runtime_registry.get(key) not in (None, "")
    }
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

        if (
            _is_timeline_clip_option_index_branch_risk(risk)
            and not has_manual
            and not risk_tagged_options
        ):
            branch_map = risk.get("branchLineIdsByOption") or {}
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
                })
            if complete and runtime_options:
                allowed.append({
                    **base,
                    "provenance": {
                        "kind": "DialogTimelineClipOptionIndex",
                        "code": "timelineClipOptionIndexBranches",
                        "reason": "runtimeClipOptionIndex",
                        "source": "dialogTimeline",
                        "assetTracks": _string_list(
                            risk.get("assetTracks")
                        ),
                        "optionIndex": risk.get("optionIndex") or [],
                        "candidateMapping": "trunkClipOptionIndex",
                    },
                    "options": runtime_options,
                    "commonContinuationLineId": safe_key(
                        risk.get("commonContinuationLineId")
                    ),
                })
                continue
            excluded.append({
                **base,
                "optionIds": option_ids,
                "exclusionReason": "incompleteTimelineClipOptionIndexMapping",
                "riskEvidence": _compact_option_risk(risk),
            })
            continue

        if _is_runtime_jump_branch_risk(risk) and not has_manual and not risk_tagged_options:
            branch_map = risk.get("branchLineIdsByOption") or {}
            skipped_map = risk.get("skippedLineIdsByOption") or {}
            common_continuation = safe_key(risk.get("commonContinuationLineId"))
            direct_continuation_ids = set(
                _string_list(risk.get("directContinuationOptionIds"))
            )
            runtime_options: list[dict[str, Any]] = []
            complete = True
            for option in options:
                option_id = safe_key(option.get("id"))
                branch_lines = _string_list(branch_map.get(option_id))
                is_direct_continuation = (
                    option_id in direct_continuation_ids
                    and bool(common_continuation)
                )
                if not option_id or (not branch_lines and not is_direct_continuation):
                    complete = False
                    break
                runtime_option = {
                    **_compact_dialog_option(option),
                    "branchLineIds": branch_lines,
                    "skippedLineIds": _string_list(skipped_map.get(option_id)),
                }
                if is_direct_continuation:
                    runtime_option["directContinuation"] = True
                    runtime_option["continuationLineId"] = common_continuation
                runtime_options.append(runtime_option)
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
                    "directContinuationOptionIds": sorted(
                        direct_continuation_ids,
                        key=natural_key,
                    ),
                    "commonContinuationLineId": common_continuation,
                })
                continue
            excluded.append({
                **base,
                "optionIds": option_ids,
                "exclusionReason": "incompleteRuntimeJumpMapping",
                "riskEvidence": _compact_option_risk(risk),
            })
            continue

        if (
            unregistered_scene
            and (
                has_manual
                or risk_tagged_options
                or (
                    risk
                    and risk_code not in {"dialogTreeBranchConvergence"}
                )
            )
        ):
            excluded.append({
                **base,
                "optionIds": option_ids,
                "exclusionReason":
                    "unregisteredSceneWithoutAuthoredOptionConsumer",
                "runtimeRegistry": compact_runtime_registry,
                "retainedRiskEvidence": _compact_option_risk(risk),
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
            if risk_code in {
                "sequentialTimelineOptionPrompts",
                "terminalTimelineOptionSlot",
                "foreignTimelineOptionDefinitions",
            }:
                exclusion_reason = "closedTimelineOptionLayout"
            elif risk_code in {
                "separateDialogTreeOptionNodes",
                "orphanDialogTreeOptionDefinitions",
            }:
                exclusion_reason = "closedDialogTreeOptionLayout"
            elif risk_code in {
                "sharedTimelineContinuation",
                "defaultTimelineContinuation",
            }:
                exclusion_reason = "sharedOrDefaultCandidates"
            else:
                exclusion_reason = "inferredOrUnsupportedRisk"
            excluded.append({
                **base,
                "optionIds": option_ids,
                "exclusionReason": exclusion_reason,
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
                debug = (
                    option.get("_debug")
                    if isinstance(option.get("_debug"), dict)
                    else {}
                )
                authored_sources = [
                    source
                    for source in (debug.get("branchLineSources") or [])
                    if (
                        isinstance(source, dict)
                        and safe_key(source.get("kind"))
                        in {"DialogTree", "DialogTreeFragment"}
                        and safe_key(source.get("file"))
                    )
                ]
                if authored_sources:
                    source = authored_sources[0]
                    matching_route = {
                        "kind": safe_key(source.get("kind")),
                        "sourceKey": safe_key(source.get("sourceKey")),
                        "sourceFile": safe_key(source.get("file")),
                        "after": after,
                        "firstLineId": branch_lines[0],
                        "pathLineIds": branch_lines,
                        "outcomeKind": "sameScenePath",
                    }
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

        group_debug = (
            group.get("_debug")
            if isinstance(group.get("_debug"), dict)
            else {}
        )
        partial_coverage = (
            group_debug.get("partialAuthoredOptionCoverage")
            if isinstance(
                group_debug.get("partialAuthoredOptionCoverage"),
                dict,
            )
            else {}
        )
        definition_only_option_ids = set(
            _string_list(partial_coverage.get("definitionOnlyOptionIds"))
        )
        definition_only_failures = [
            row
            for row in direct_failures
            if row.get("optionId") in definition_only_option_ids
        ]
        direct_failures = [
            row
            for row in direct_failures
            if row.get("optionId") not in definition_only_option_ids
        ]
        if definition_only_failures:
            excluded.append({
                **base,
                "optionIds": [
                    row["optionId"] for row in definition_only_failures
                ],
                "exclusionReason": "branchLinesForDefinitionOnlyRows",
                "definitionOnlyOptionIds": sorted(
                    definition_only_option_ids,
                    key=natural_key,
                ),
                "options": definition_only_failures,
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
            outcomes_by_option = {
                option_id: non_line_outcomes.get(option_id) or []
                for option_id in option_ids
            }
            covered_option_ids = [
                option_id
                for option_id, outcomes in outcomes_by_option.items()
                if outcomes
            ]
            if option_ids and len(covered_option_ids) == len(option_ids):
                excluded.append({
                    **base,
                    "optionIds": option_ids,
                    "exclusionReason": "authoredNonLineOptionOutcomes",
                    "outcomesByOption": outcomes_by_option,
                })
                continue
            if covered_option_ids:
                authored_option_ids = set(
                    _string_list(partial_coverage.get("authoredOptionIds"))
                )
                definition_only_option_ids = set(
                    _string_list(
                        partial_coverage.get("definitionOnlyOptionIds")
                    )
                )
                uncovered_option_ids = set(option_ids) - set(
                    covered_option_ids
                )
                if (
                    set(covered_option_ids).issubset(authored_option_ids)
                    and uncovered_option_ids
                    and uncovered_option_ids == definition_only_option_ids
                ):
                    excluded.append({
                        **base,
                        "optionIds": option_ids,
                        "exclusionReason":
                            "authoredOutcomesWithDefinitionOnlyRows",
                        "coveredOptionIds": covered_option_ids,
                        "definitionOnlyOptionIds": sorted(
                            definition_only_option_ids,
                            key=natural_key,
                        ),
                        "outcomesByOption": {
                            option_id: outcomes
                            for option_id, outcomes
                            in outcomes_by_option.items()
                            if outcomes
                        },
                    })
                    continue
                excluded.append({
                    **base,
                    "optionIds": option_ids,
                    "exclusionReason":
                        "incompleteAuthoredNonLineOptionOutcomes",
                    "coveredOptionIds": covered_option_ids,
                    "outcomesByOption": {
                        option_id: outcomes
                        for option_id, outcomes in outcomes_by_option.items()
                        if outcomes
                    },
                })
                continue
            compact_options = [
                _compact_dialog_option(option)
                for option in options
            ]
            if unregistered_scene:
                excluded.append({
                    **base,
                    "optionIds": option_ids,
                    "options": compact_options,
                    "exclusionReason":
                        "unregisteredSceneWithoutAuthoredOptionConsumer",
                    "runtimeRegistry": compact_runtime_registry,
                })
            else:
                no_route.append({
                    **base,
                    "options": compact_options,
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


def _typed_story_selector_groups(
    flow: dict[str, Any], candidate_keys: set[str]
) -> list[dict[str, Any]]:
    """Expose exact typed selector alternatives without manufacturing edges."""
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    invalid_groups: set[tuple[str, str]] = set()
    for row in _story_connection_rows(flow):
        if (
            safe_key(row.get("selectorKind")) != "typed_table_story_selector"
            or safe_key(row.get("graphEffect")) != "none"
        ):
            continue
        group_id = safe_key(row.get("selectorGroupId"))
        mission_id = safe_key(row.get("missionId"))
        alternatives = [
            {"role": safe_key(item.get("role")), "key": safe_key(item.get("key"))}
            for item in row.get("selectorAlternatives") or []
            if isinstance(item, dict)
            and safe_key(item.get("role"))
            and safe_key(item.get("key")) in candidate_keys
        ]
        if not group_id or len(alternatives) < 2:
            continue
        signature = (mission_id, group_id)
        if signature in invalid_groups:
            continue
        current = groups.setdefault(signature, {
            "selectorKind": "typed_table_story_selector",
            "missionId": mission_id,
            "selectorGroupId": group_id,
            "alternatives": alternatives,
            "sourceFiles": _string_list(row.get("sourceFiles")),
            "nativeMappingId": safe_key(row.get("nativeMappingId")),
            "graphEffect": "none",
            "orderBoundary": safe_key(row.get("orderBoundary")),
        })
        if current["alternatives"] != alternatives:
            groups.pop(signature, None)
            invalid_groups.add(signature)
    return sorted(
        groups.values(),
        key=lambda row: (natural_key(row["missionId"]), natural_key(row["selectorGroupId"])),
    )


NATIVE_OCCURRENCE_FIELDS = (
    "occurrences",
    "levelScriptOccurrences",
    "nativeOccurrences",
    "nativeBlackActionOccurrences",
    "parentDialogNativeOccurrences",
    "preloadOccurrences",
)


def _story_connection_rows(
    flow: dict[str, Any],
    *,
    include_mission_state_dependencies: bool = False,
) -> Iterable[dict[str, Any]]:
    for row in flow.get("missionStoryConnections") or []:
        if isinstance(row, dict):
            yield row
    for quest in flow.get("quests") or []:
        if not isinstance(quest, dict):
            continue
        for row in quest.get("storyConnections") or []:
            if isinstance(row, dict):
                yield row
    for field in ("unlinkedNativePlayback", "unlinkedDefinitionOnly"):
        for row in flow.get(field) or []:
            if isinstance(row, dict):
                yield row
    if include_mission_state_dependencies:
        for row in flow.get("missionStateStoryDependencies") or []:
            if isinstance(row, dict):
                yield row


def _dialog_tree_narrative_containments(
    mission: str,
    flow: dict[str, Any],
    candidate_keys: set[str],
    original_occurrences: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return exact nested black-screen placements without creating file order.

    A narrative action between two parent trunks proves line-level containment.
    It does not prove how the parent DialogTree is activated, nor does it order
    the complete child Story file before or after the complete parent file.
    """
    rows = (
        flow.get("unresolvedDialogTreeNarrativeActions")
        if "unresolvedDialogTreeNarrativeActions" in flow
        else flow.get("unlinkedDialogTreeNarrativeActions")
    )
    containments: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    seen: set[tuple[str, str, tuple[str, ...], tuple[str, ...]]] = set()
    candidate_black_keys = sorted(
        (key for key in candidate_keys if key.startswith("black_")),
        key=lambda key: (-len(key), natural_key(key)),
    )
    source_rows = [row for row in rows or [] if isinstance(row, dict)]
    for occurrence in original_occurrences or []:
        if not isinstance(occurrence, dict):
            continue
        text_id = safe_key(occurrence.get("textId"))
        matching_children = [
            key for key in candidate_black_keys
            if text_id.startswith(f"{key}_")
        ]
        if len(matching_children) != 1:
            continue
        source_rows.append({
            "key": matching_children[0],
            "parentStoryKey": safe_key(occurrence.get("dialogKey")),
            "relation": "dialog_tree_narrative_action_unscoped",
            "confidence": "native_exact_containment_unscoped",
            "dialogTreeNarrativeActions": [occurrence],
        })
    for row in source_rows:
        if not isinstance(row, dict):
            continue
        child_key = safe_key(row.get("key"))
        parent_key = safe_key(row.get("parentStoryKey"))
        occurrences = [
            occurrence
            for occurrence in row.get("dialogTreeNarrativeActions") or []
            if isinstance(occurrence, dict)
        ]
        if (
            safe_key(row.get("relation"))
            != "dialog_tree_narrative_action_unscoped"
            or child_key not in candidate_keys
        ):
            continue
        header_valid = bool(
            parent_key in candidate_keys
            and child_key != parent_key
            and safe_key(row.get("confidence"))
            == "native_exact_containment_unscoped"
            and occurrences
        )
        after_ids = sorted({
            safe_key(line_id)
            for occurrence in occurrences
            if safe_key(occurrence.get("nativeMappingId"))
            == "dialog-tree-narrative-mask-connection-native-v1"
            and safe_key(occurrence.get("dialogKey")) == parent_key
            and safe_key(occurrence.get("dialogTreeConnectionPlacementStatus"))
            == "exact_unique_adjacent_parent_trunks"
            for line_id in occurrence.get("embeddedAfterLineIds") or []
            if safe_key(line_id)
        }, key=natural_key)
        before_ids = sorted({
            safe_key(line_id)
            for occurrence in occurrences
            if safe_key(occurrence.get("nativeMappingId"))
            == "dialog-tree-narrative-mask-connection-native-v1"
            and safe_key(occurrence.get("dialogKey")) == parent_key
            and safe_key(occurrence.get("dialogTreeConnectionPlacementStatus"))
            == "exact_unique_adjacent_parent_trunks"
            for line_id in occurrence.get("embeddedBeforeLineIds") or []
            if safe_key(line_id)
        }, key=natural_key)
        valid_occurrences = [
            occurrence
            for occurrence in occurrences
            if safe_key(occurrence.get("nativeMappingId"))
            == "dialog-tree-narrative-mask-connection-native-v1"
            and safe_key(occurrence.get("dialogKey")) == parent_key
            and safe_key(occurrence.get("dialogTreeConnectionPlacementStatus"))
            == "exact_unique_adjacent_parent_trunks"
            and occurrence.get("reachableFromPrimeNode") is True
            and occurrence.get("embeddedAfterLineIds")
            and occurrence.get("embeddedBeforeLineIds")
        ]
        if (
            not header_valid
            or len(valid_occurrences) != len(occurrences)
            or not after_ids
            or not before_ids
        ):
            warnings.append({
                "validator": "dialogTreeNarrativeContainment",
                "check": "exact_unique_adjacent_parent_trunks",
                "mission": mission,
                "storyKey": child_key,
                "parentStoryKey": parent_key,
                "sourcePaths": sorted({
                    safe_key(occurrence.get("sourceFile"))
                    for occurrence in occurrences
                    if safe_key(occurrence.get("sourceFile"))
                }),
                "expected": {
                    "confidence": "native_exact_containment_unscoped",
                    "mappingId":
                        "dialog-tree-narrative-mask-connection-native-v1",
                    "placementStatus":
                        "exact_unique_adjacent_parent_trunks",
                    "reachableFromPrimeNode": True,
                    "candidateParent": True,
                    "nonemptyAdjacentLineIds": True,
                },
                "actual": {
                    "confidence": safe_key(row.get("confidence")),
                    "occurrenceCount": len(occurrences),
                    "validOccurrenceCount": len(valid_occurrences),
                    "candidateParent": parent_key in candidate_keys,
                    "embeddedAfterLineIds": after_ids,
                    "embeddedBeforeLineIds": before_ids,
                },
            })
            continue
        signature = (child_key, parent_key, tuple(after_ids), tuple(before_ids))
        if signature in seen:
            continue
        seen.add(signature)
        containments.append({
            "child": child_key,
            "parent": parent_key,
            "kind": "dialogTreeNarrativeMask",
            "relation": "dialog_tree_narrative_action_containment",
            "tier": "native_direct_containment",
            "embeddedAfterLineIds": after_ids,
            "embeddedBeforeLineIds": before_ids,
            "textIds": sorted({
                safe_key(occurrence.get("textId"))
                for occurrence in valid_occurrences
                if safe_key(occurrence.get("textId"))
            }, key=natural_key),
            "sourceFiles": sorted({
                safe_key(occurrence.get("sourceFile"))
                for occurrence in valid_occurrences
                if safe_key(occurrence.get("sourceFile"))
            }),
            "nativeMappingId":
                "dialog-tree-narrative-mask-connection-native-v1",
            "orderBoundary": (
                "exact line-level placement inside the parent DialogTree; "
                "not a complete Story-file edge and not parent activation evidence"
            ),
        })
    containments.sort(key=lambda row: (
        natural_key(row["parent"]),
        natural_key(row["child"]),
    ))
    return containments, warnings


def _dialog_tree_open_ui_containments(
    mission: str,
    candidate_keys: set[str],
    occurrences: list[dict[str, Any]] | None,
    reading_popup_rows: dict[str, Any] | None,
    *,
    reading_popup_source: str = "",
    reading_popup_sha256: str = "",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Resolve exact DialogTree OpenUI popup consumers to Story content.

    The typed DialogTree node proves containment in its parent dialog. The
    ReadingPopUpTable join proves which ``text_*`` Story payload is opened.
    Neither relationship proves how the parent dialog itself is activated.
    """
    popup_rows = reading_popup_rows if isinstance(reading_popup_rows, dict) else {}
    containments: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    allowed_placements = {
        "exact_between_adjacent_parent_trunks",
        "exact_after_parent_trunk_at_finish",
        "exact_prime_entry_before_parent_trunk",
    }
    for occurrence in occurrences or []:
        if not isinstance(occurrence, dict):
            continue
        popup_id = safe_key(occurrence.get("readingPopupId"))
        popup_row = popup_rows.get(popup_id)
        child_key = (
            safe_key(popup_row.get("contentId"))
            if isinstance(popup_row, dict) else ""
        )
        parent_key = safe_key(occurrence.get("dialogKey"))
        if child_key not in candidate_keys:
            continue
        after_ids = [
            safe_key(value)
            for value in occurrence.get("embeddedAfterLineIds") or []
            if safe_key(value)
        ]
        before_ids = [
            safe_key(value)
            for value in occurrence.get("embeddedBeforeLineIds") or []
            if safe_key(value)
        ]
        placement = safe_key(
            occurrence.get("dialogTreeConnectionPlacementStatus")
        )
        expected_popup_row = {
            "bgType": popup_row.get("bgType") if isinstance(popup_row, dict) else None,
            "contentId": child_key,
            "iconType": popup_row.get("iconType") if isinstance(popup_row, dict) else None,
            "id": popup_id,
            "overrideRadioId": "",
            "title": {"id": 0, "text": ""},
        }
        boundary_valid = (
            (placement == "exact_between_adjacent_parent_trunks" and after_ids and before_ids)
            or (placement == "exact_after_parent_trunk_at_finish" and after_ids and not before_ids)
            or (placement == "exact_prime_entry_before_parent_trunk" and not after_ids and before_ids)
        )
        valid = bool(
            parent_key
            and parent_key != child_key
            and child_key.startswith("text_")
            and popup_id
            and popup_row == expected_popup_row
            and occurrence.get("paramData") == {"id": popup_id}
            and occurrence.get("panelType") == 17
            and occurrence.get("actionEnum") == 57
            and safe_key(occurrence.get("nativeMappingId"))
            == "dialog-tree-open-ui-reading-popup-connection-native-v1"
            and placement in allowed_placements
            and occurrence.get("reachableFromPrimeNode") is True
            and boundary_valid
        )
        if not valid:
            warnings.append({
                "validator": "dialogTreeOpenUIContainment",
                "check": "exact_typed_open_ui_reading_popup_boundary",
                "mission": mission,
                "storyKey": child_key,
                "parentStoryKey": parent_key,
                "sourcePaths": sorted(filter(None, {
                    safe_key(occurrence.get("sourceFile")),
                    reading_popup_source,
                })),
                "sourceSha256": {
                    safe_key(occurrence.get("sourceFile")):
                        safe_key(occurrence.get("sourceSha256")),
                    reading_popup_source: reading_popup_sha256,
                },
                "expected": {
                    "popupRow": expected_popup_row,
                    "paramData": {"id": popup_id},
                    "panelType": 17,
                    "actionEnum": 57,
                    "mappingId":
                        "dialog-tree-open-ui-reading-popup-connection-native-v1",
                    "placementStatus": sorted(allowed_placements),
                    "reachableFromPrimeNode": True,
                    "typedParentCarrier": True,
                },
                "actual": {
                    "popupRow": popup_row,
                    "paramData": occurrence.get("paramData"),
                    "panelType": occurrence.get("panelType"),
                    "actionEnum": occurrence.get("actionEnum"),
                    "mappingId": safe_key(occurrence.get("nativeMappingId")),
                    "placementStatus": placement,
                    "reachableFromPrimeNode":
                        occurrence.get("reachableFromPrimeNode"),
                    "typedParentCarrier": bool(parent_key),
                    "embeddedAfterLineIds": after_ids,
                    "embeddedBeforeLineIds": before_ids,
                },
            })
            continue
        signature = (
            parent_key,
            child_key,
            safe_key(occurrence.get("nodeId")),
        )
        if signature in seen:
            continue
        seen.add(signature)
        containments.append({
            "child": child_key,
            "parent": parent_key,
            "parentStoryCandidate": parent_key in candidate_keys,
            "kind": "dialogTreeOpenUIReadingPopup",
            "relation": "dialog_tree_open_ui_reading_popup_containment",
            "tier": "native_direct_containment",
            "boundaryPlacement": placement,
            "embeddedAfterLineIds": after_ids,
            "embeddedBeforeLineIds": before_ids,
            "readingPopupId": popup_id,
            "panelType": 17,
            "actionEnum": 57,
            "sourceFiles": sorted(filter(None, {
                safe_key(occurrence.get("sourceFile")),
                reading_popup_source,
            })),
            "sourceSha256": {
                safe_key(occurrence.get("sourceFile")):
                    safe_key(occurrence.get("sourceSha256")),
                reading_popup_source: reading_popup_sha256,
            },
            "nativeMappingId":
                "dialog-tree-open-ui-reading-popup-connection-native-v1",
            "orderBoundary": (
                "exact popup placement inside the parent DialogTree; not a "
                "complete Story-file edge and not parent activation evidence"
            ),
        })
    containments.sort(key=lambda row: (
        natural_key(row["parent"]),
        natural_key(row["child"]),
    ))
    return containments, warnings


def _dialog_tree_cross_story_trunk_edges(
    flow: dict[str, Any],
    candidate_keys: set[str],
    dialog_payloads: list[tuple[str, dict[str, Any]]] | None,
) -> list[dict[str, Any]]:
    """Recover a scene edge when one complete dialog continues as another.

    A different Story prefix inside one DialogTree is not enough. The exact
    carrier chain must directly follow a parent trunk, cover every line of the
    child Story file, and its current-parent closure must cover every line of
    the parent Story file. This rejects embedded files when the parent has
    content on both sides.
    """
    line_ids_by_story = {
        safe_key(payload.get("key")): {
            safe_key(line.get("id"))
            for line in payload.get("lines") or []
            if isinstance(line, dict) and safe_key(line.get("id"))
        }
        for _path, payload in dialog_payloads or []
        if isinstance(payload, dict) and safe_key(payload.get("key"))
    }
    edges: list[dict[str, Any]] = []
    for row in _story_connection_rows(flow):
        child_key = safe_key(row.get("key"))
        parent_key = safe_key(row.get("parentStoryKey"))
        carriers = [
            carrier
            for carrier in row.get("dialogTreeStoryPlaybackCarriers") or []
            if isinstance(carrier, dict)
        ]
        if (
            child_key not in candidate_keys
            or parent_key not in candidate_keys
            or child_key == parent_key
            or safe_key(row.get("relation"))
            != "dialog_tree_reachable_story_playback"
            or safe_key(row.get("confidence"))
            != "native_derived_exact_parent_shell"
            or safe_key(row.get("nativeMappingId"))
            != "dialog-tree-reachable-story-playback-native-v1"
            or safe_key(row.get("certainty")) != "authored_reachable"
            or not carriers
        ):
            continue
        parent_line_ids = line_ids_by_story.get(parent_key) or set()
        child_line_ids = line_ids_by_story.get(child_key) or set()
        carrier_line_ids = {
            safe_key(carrier.get("carrierValue"))
            for carrier in carriers
            if (
                safe_key(carrier.get("carrierKind")) == "trunk"
                and safe_key(carrier.get("storyKey")) == child_key
                and carrier.get("reachableFromCurrentParentTrunk") is True
                and safe_key(carrier.get("entryProof"))
                == "exact_registered_dialog_tree_current_parent_anchor"
            )
        }
        current_parent_line_ids = {
            safe_key(value)
            for carrier in carriers
            for value in carrier.get("currentParentTrunkIds") or []
            if safe_key(value)
        }
        if (
            not parent_line_ids
            or not child_line_ids
            or carrier_line_ids != child_line_ids
            or current_parent_line_ids != parent_line_ids
            or set(_string_list(row.get("trunkIds"))) != child_line_ids
        ):
            continue
        ordered_carriers = sorted(
            carriers,
            key=lambda carrier: (
                len(carrier.get("nodePath") or []),
                natural_key(safe_key(carrier.get("carrierValue"))),
            ),
        )
        first = ordered_carriers[0]
        first_path = _string_list(first.get("nodePath"))
        if (
            len(first_path) != 2
            or safe_key(first.get("parentTrunkId")) not in parent_line_ids
            or len(first.get("connectionPath") or []) != 1
        ):
            continue
        chain_valid = True
        for index, carrier in enumerate(ordered_carriers, start=1):
            node_path = _string_list(carrier.get("nodePath"))
            connection_path = [
                connection
                for connection in carrier.get("connectionPath") or []
                if isinstance(connection, dict)
            ]
            if (
                len(node_path) != index + 1
                or node_path[:len(first_path)] != first_path
                or len(connection_path) != len(node_path) - 1
                or safe_key(carrier.get("nodeId")) != node_path[-1]
            ):
                chain_valid = False
                break
        if not chain_valid:
            continue
        edges.append({
            "from": parent_key,
            "to": child_key,
            "kind": "dialogTreeCrossStoryTrunkContinuation",
            "tier": "strong",
            "source":
                "complete exact registered DialogTree parent-to-child trunk continuation",
            "sourceFiles": _string_list(row.get("sourceFiles")),
            "nativeMappingId": safe_key(row.get("nativeMappingId")),
            "parentLastLineId": safe_key(first.get("parentTrunkId")),
            "childFirstLineId": safe_key(first.get("carrierValue")),
            "childLineIds": sorted(child_line_ids, key=natural_key),
            "runtimeReplacementPossible": bool(
                row.get("runtimeReplacementPossible")
            ),
        })
    return edges


def _dialog_tree_cross_story_conditional_edges(
    mission: str,
    flow: dict[str, Any],
    candidate_keys: set[str],
    dialog_payloads: list[tuple[str, dict[str, Any]]] | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Validate hash-locked cross-file DialogTree conditional branches."""
    payloads_by_key = {
        safe_key(payload.get("key")): payload
        for _path, payload in dialog_payloads or []
        if isinstance(payload, dict) and safe_key(payload.get("key"))
    }
    rows_by_pair = {
        (
            safe_key(row.get("parentStoryKey")),
            safe_key(row.get("key")),
        ): row
        for row in _story_connection_rows(flow)
        if isinstance(row, dict)
    }
    edges: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for (declared_mission, parent_key, child_key), declaration in (
        DIALOG_TREE_CONDITIONAL_BRANCH_DECLARATIONS.items()
    ):
        if declared_mission != mission:
            continue
        source_file = declaration["sourceFile"]
        source_path = ROOT / source_file
        game_assembly_path = _configured_game_assembly_path()
        source_sha256 = (
            hashlib.sha256(source_path.read_bytes()).hexdigest().upper()
            if source_path.is_file() else ""
        )
        game_assembly_sha256 = (
            hashlib.sha256(game_assembly_path.read_bytes()).hexdigest().upper()
            if game_assembly_path.is_file() else ""
        )
        row = rows_by_pair.get((parent_key, child_key)) or {}
        parent_payload = payloads_by_key.get(parent_key) or {}
        child_payload = payloads_by_key.get(child_key) or {}
        parent_line_ids = {
            safe_key(line.get("id"))
            for line in parent_payload.get("lines") or []
            if isinstance(line, dict) and safe_key(line.get("id"))
        }
        child_line_ids = {
            safe_key(line.get("id"))
            for line in child_payload.get("lines") or []
            if isinstance(line, dict) and safe_key(line.get("id"))
        }
        carriers = {
            safe_key(carrier.get("carrierValue")): carrier
            for carrier in row.get("dialogTreeStoryPlaybackCarriers") or []
            if isinstance(carrier, dict)
            and safe_key(carrier.get("carrierValue"))
        }
        actual_carrier_paths = {
            line_id: tuple(_string_list(carrier.get("nodePath")))
            for line_id, carrier in carriers.items()
        }
        actual_connection_indexes = {
            line_id: tuple(
                int(connection.get("index"))
                for connection in carrier.get("connectionPath") or []
                if isinstance(connection, dict)
                and isinstance(connection.get("index"), int)
            )
            for line_id, carrier in carriers.items()
        }
        conditional_routes = []
        for link in parent_payload.get("sceneGraphLinks") or []:
            if not isinstance(link, dict):
                continue
            for option in link.get("options") or []:
                if (
                    isinstance(option, dict)
                    and safe_key(option.get("optionId"))
                    == declaration["optionId"]
                ):
                    conditional_routes.append((link, option))
        route_link, route = (
            conditional_routes[0]
            if len(conditional_routes) == 1 else ({}, {})
        )
        outcomes = route.get("conditionalOutcomes") or []
        actual_outcomes = {
            safe_key(outcome.get("targetNodeId")): tuple(
                _string_list(outcome.get("pathLineIds"))
            )
            for outcome in outcomes
            if isinstance(outcome, dict)
            and safe_key(outcome.get("targetNodeId"))
        }
        expected_child_lines = set(declaration["childArmLineIds"])
        current_parent_lines = {
            safe_key(line_id)
            for carrier in carriers.values()
            for line_id in carrier.get("currentParentTrunkIds") or []
            if safe_key(line_id)
        }
        expected = {
            "sourceSha256": declaration["sourceSha256"],
            "gameAssemblySha256": declaration["gameAssemblySha256"],
            "candidateKeysPresent": True,
            "relation": "dialog_tree_reachable_story_playback",
            "confidence": "native_exact_parent_mission_context",
            "certainty": "authored_reachable",
            "nativeMappingId": declaration["nativeMappingId"],
            "parentLineIds": sorted(
                declaration["parentLineIds"], key=natural_key
            ),
            "childLineIds": sorted(expected_child_lines, key=natural_key),
            "carrierNodePaths": declaration["carrierNodePaths"],
            "carrierConnectionIndexes": declaration[
                "carrierConnectionIndexes"
            ],
            "optionAfterLineId": declaration["optionAfterLineId"],
            "branchAfterLineId": declaration["branchAfterLineId"],
            "branchNodeId": declaration["branchNodeId"],
            "outcomeKind": "authoredConditionalBranch",
            "parentOutcome": tuple(declaration["parentArmLineIds"]),
            # The emitted route stops at the child option node; the exact
            # carrier closure above proves the terminal third child line.
            "childOutcomePrefix": tuple(declaration["childArmLineIds"][:2]),
        }
        actual = {
            "sourceSha256": source_sha256,
            "gameAssemblySha256": game_assembly_sha256,
            "candidateKeysPresent": {
                parent_key, child_key
            } <= candidate_keys,
            "relation": safe_key(row.get("relation")),
            "confidence": safe_key(row.get("confidence")),
            "certainty": safe_key(row.get("certainty")),
            "nativeMappingId": safe_key(row.get("nativeMappingId")),
            "parentLineIds": sorted(current_parent_lines, key=natural_key),
            "childLineIds": sorted(child_line_ids, key=natural_key),
            "carrierNodePaths": actual_carrier_paths,
            "carrierConnectionIndexes": actual_connection_indexes,
            "optionAfterLineId": safe_key(route_link.get("after")),
            "branchAfterLineId": safe_key(route.get("firstLineId")),
            "branchNodeId": safe_key((route.get("_debug") or {}).get(
                "endNodeId"
            )),
            "outcomeKind": safe_key(route.get("outcomeKind")),
            "parentOutcome": actual_outcomes.get(
                declaration["conditionFalseTargetNodeId"], ()
            ),
            "childOutcomePrefix": actual_outcomes.get(
                declaration["conditionTrueTargetNodeId"], ()
            ),
        }
        if actual != expected or parent_line_ids != set(
            declaration["parentLineIds"]
        ):
            warnings.append({
                "validator": "dialogTreeCrossStoryConditionalBranch",
                "gate": "exactSerializedBranchCarrierAndNativePolarity",
                "mission": mission,
                "storyKeys": [parent_key, child_key],
                "sourcePaths": [str(source_path), str(game_assembly_path)],
                "sourceSha256": {
                    source_file: source_sha256,
                    "GameAssembly.dll": game_assembly_sha256,
                },
                "expected": expected,
                "actual": actual,
            })
            continue
        edges.append({
            "from": parent_key,
            "to": child_key,
            "kind": "dialogTreeCrossStoryConditionalBranch",
            "tier": "strong",
            "source": (
                "exact serialized DialogTree conditional arm plus current "
                "GameAssembly outgoing-index polarity"
            ),
            "sourceFiles": [source_file],
            "sourceSha256": {source_file: source_sha256},
            "nativeMappingId": declaration["nativeMappingId"],
            "optionId": declaration["optionId"],
            "optionAfterLineId": declaration["optionAfterLineId"],
            "branchAfterLineId": declaration["branchAfterLineId"],
            "branchNodeId": declaration["branchNodeId"],
            "parentArmLineIds": list(declaration["parentArmLineIds"]),
            "childArmLineIds": list(declaration["childArmLineIds"]),
            "condition": declaration["condition"],
            "conditionTrueConnectionIndex": declaration[
                "conditionTrueConnectionIndex"
            ],
            "conditionFalseConnectionIndex": declaration[
                "conditionFalseConnectionIndex"
            ],
            "gameAssemblySha256": declaration["gameAssemblySha256"],
            "nativeConsumers": list(declaration["nativeConsumers"]),
            "runtimeReplacementPossible": bool(
                row.get("runtimeReplacementPossible")
            ),
        })
    return edges, warnings


def _connection_native_occurrences(row: dict[str, Any]) -> list[dict[str, Any]]:
    occurrences: list[dict[str, Any]] = []
    for field in NATIVE_OCCURRENCE_FIELDS:
        occurrences.extend(
            occurrence
            for occurrence in row.get(field) or []
            if isinstance(occurrence, dict)
        )
    for gate_path in row.get("missionStateGatePaths") or []:
        if not isinstance(gate_path, dict):
            continue
        control_path = gate_path.get("controlPath")
        if not isinstance(control_path, dict):
            continue
        occurrences.append({
            "levelId": gate_path.get("levelId"),
            "scriptId": gate_path.get("scriptId"),
            "sourceFile": gate_path.get("sourceFile"),
            "nativeEventOwners": [control_path],
        })
    if not occurrences and isinstance(row.get("nativeEventOwners"), list):
        occurrences.append({
            "levelId": next(iter(row.get("levelIds") or []), ""),
            "scriptId": next(iter(row.get("scriptIds") or []), ""),
            "sourceFile": next(iter(row.get("sourceFiles") or []), ""),
            "sourceFiles": row.get("sourceFiles") or [],
            "nativeEventOwners": row.get("nativeEventOwners") or [],
        })
    return occurrences


def _native_event_story_paths(
    flow: dict[str, Any],
    candidate_keys: set[str] | None,
    *,
    include_mission_state_dependencies: bool = False,
) -> dict[
    tuple[str, str, int, str],
    set[tuple[str, tuple[tuple[Any, ...], ...], tuple[str, ...], str, str]],
]:
    event_paths: dict[
        tuple[str, str, int, str],
        set[tuple[str, tuple[tuple[Any, ...], ...], tuple[str, ...], str, str]],
    ] = defaultdict(set)
    for row in _story_connection_rows(
        flow,
        include_mission_state_dependencies=include_mission_state_dependencies,
    ):
        story_key = safe_key(row.get("key"))
        if candidate_keys is not None and story_key not in candidate_keys:
            continue
        for occurrence in _connection_native_occurrences(row):
            level_id = safe_key(occurrence.get("levelId"))
            script_id = safe_key(occurrence.get("scriptId"))
            source_file = safe_key(occurrence.get("sourceFile"))
            source_files = tuple(sorted({
                source_file,
                *[
                    safe_key(value)
                    for value in occurrence.get("sourceFiles") or []
                ],
            } - {""}, key=natural_key))
            for owner in occurrence.get("nativeEventOwners") or []:
                if (
                    not isinstance(owner, dict)
                    or owner.get("status")
                    not in LEVELSCRIPT_NATIVE_EXACT_CONTROL_PATH_STATUSES
                    or not isinstance(owner.get("headerLocalId"), int)
                ):
                    continue
                path = tuple(
                    (
                        int(step["localId"]),
                        safe_key(step.get("edge")),
                        safe_key(step.get("actionName")),
                        safe_key(step.get("recordClass")),
                        json.dumps(
                            step.get("branchPredicate") or {},
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                        ),
                    )
                    for step in owner.get("path") or []
                    if isinstance(step, dict) and isinstance(step.get("localId"), int)
                )
                if not path:
                    continue
                signature = (
                    level_id,
                    script_id,
                    int(owner["headerLocalId"]),
                    safe_key(owner.get("headerName")),
                )
                event_paths[signature].add((
                    story_key,
                    path,
                    source_files,
                    json.dumps(
                        owner.get("eventDetail") or {},
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    json.dumps(
                        owner.get("downstreamControlPaths") or [],
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                ))
    return event_paths


def _strict_native_path_prefix(
    source_path: tuple[tuple[Any, ...], ...],
    target_path: tuple[tuple[Any, ...], ...],
) -> bool:
    # WhileAction can execute its body repeatedly. A path through doAction is
    # exact reachability evidence, but collapsing repeated Story files into
    # one node would make a prefix look like a false global chronology edge.
    if any(
        step[1] == "WhileAction.doAction"
        for path in (source_path, target_path)
        for step in path
    ):
        return False
    source_ids = tuple(step[0] for step in source_path)
    target_ids = tuple(step[0] for step in target_path)
    return (
        len(source_ids) < len(target_ids)
        and target_ids[:len(source_ids)] == source_ids
    )


def _parallel_action_names(
    extra_thread_scheduler_contract: dict[str, Any] | None,
) -> set[str]:
    """Project structurally admitted binary writers to action class names."""
    names: set[str] = set()
    for row in (extra_thread_scheduler_contract or {}).get(
        "extraThreadExecuteMethods", []
    ):
        if not isinstance(row, dict) or row.get("writerShape") not in {
            "direct_scheduler_calls_from_typed_fields",
            "inline_list_add_from_typed_collection",
        }:
            continue
        symbol = safe_key(row.get("symbol"))
        if symbol.endswith(".Execute"):
            names.add(symbol.removesuffix(".Execute").rsplit(".", 1)[-1])
    return names


def load_current_parallel_fanout_authority(
    audit_path: Path = PROTOCOL_REGISTRY_AUDIT_PATH,
) -> dict[str, Any]:
    """Fail closed unless the scheduler contract matches its original inputs."""
    validator = "parallel_fanout_authority"
    audit = read_json(audit_path, {})
    if audit.get("_schema") != "endfieldProtocolRegistryAudit.v20":
        raise RuntimeError(
            f"validator={validator} gate=auditSchema "
            "expected='endfieldProtocolRegistryAudit.v20' "
            f"actual={audit.get('_schema')!r} source={audit_path}"
        )
    contract = dict(audit.get("actionExtraThreadSchedulerCensus") or {})
    validation = contract.get("validation") or {}
    if validation.get("status") != "validated":
        failure = (validation.get("failures") or [{}])[0]
        raise RuntimeError(
            f"validator={validator} "
            f"gate={failure.get('gate') or 'upstreamValidation'} "
            f"message={failure.get('message')} expected={failure.get('expected')!r} "
            f"actual={failure.get('actual')!r} "
            f"source={failure.get('sourceFile') or audit_path}"
        )
    source = audit.get("source") or {}
    related_files: list[dict[str, Any]] = []
    for path_key, hash_key, kind in (
        ("gameAssembly", "gameAssemblySha256", "original_game_binary"),
        ("metadata", "metadataSha256", "original_game_metadata"),
    ):
        source_path = Path(str(source.get(path_key) or ""))
        expected = str(source.get(hash_key) or "").lower()
        if not source_path.is_file():
            raise RuntimeError(
                f"validator={validator} gate=sourceExists expected=file "
                f"actual=missing source={source_path or path_key}"
            )
        digest = hashlib.sha256()
        with source_path.open("rb") as source_handle:
            for chunk in iter(lambda: source_handle.read(1024 * 1024), b""):
                digest.update(chunk)
        actual = digest.hexdigest()
        if actual != expected:
            raise RuntimeError(
                f"validator={validator} gate=sourceHash expected={expected!r} "
                f"actual={actual!r} source={source_path}"
            )
        related_files.append({
            "kind": kind,
            "sourceFile": str(source_path.resolve()),
            "sha256": actual,
            "relationship": "native_action_extra_thread_scheduler_authority",
        })
    contract["source"] = (
        audit_path.relative_to(ROOT).as_posix()
        if audit_path.is_relative_to(ROOT)
        else audit_path.as_posix()
    )
    contract["relatedOriginalFiles"] = related_files
    return contract


def _native_transition_kind(
    edge: str,
    source_action_name: str,
    parallel_action_names: set[str] | None = None,
) -> str:
    """Classify one exact typed successor without interpreting identifiers."""
    if (
        source_action_name in (parallel_action_names or set())
        and re.search(r"\.actions\[[0-9]+\]$", edge)
    ):
        return "parallelFanout"
    if edge in {"IfElseAction.trueAction", "IfElseAction.falseAction"}:
        return "conditionalBranch"
    if (
        edge.startswith("SwitchInt.case[")
        or edge == "SwitchInt.default"
        or edge.startswith("SwitchString.case[")
        or edge == "SwitchString.default"
    ):
        return "conditionalBranch"
    if edge in {
        "WaitForSecondsInTriggerVolume.successAction",
        "WaitForSecondsInTriggerVolume.failAction",
    }:
        return "outcomeBranch"
    if edge.startswith("Branch.sequence["):
        return "orderedSequence"
    if edge == "ActionBase.nextId" and source_action_name == "Branch":
        return "orderedSequenceExit"
    return "linear"


def _native_story_transition_steps(
    source_path: tuple[tuple[Any, ...], ...],
    target_path: tuple[tuple[Any, ...], ...],
    extra_thread_scheduler_contract: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return the exact typed suffix between two prefix-comparable Story actions.

    Each path tuple is already admitted by the current runtime's serialized
    action-slot and successor-field contract.  This projection keeps edge
    labels, action identities, and any predicate on the controlling source
    action so the UI can distinguish linear continuation, parallel fan-out,
    conditional selection, ordered Branch iteration, and outcome branches.
    """
    if not _strict_native_path_prefix(source_path, target_path):
        return []
    parallel_action_names = _parallel_action_names(
        extra_thread_scheduler_contract
    )
    steps: list[dict[str, Any]] = []
    for index in range(len(source_path), len(target_path)):
        source_step = target_path[index - 1]
        target_step = target_path[index]
        edge = safe_key(target_step[1])
        source_action_name = safe_key(source_step[2])
        predicate_json = safe_key(source_step[4])
        predicate = (
            json.loads(predicate_json)
            if predicate_json not in {"", "{}"}
            else {}
        )
        transition_kind = _native_transition_kind(
            edge,
            source_action_name,
            parallel_action_names,
        )
        step = {
            key: value
            for key, value in {
                "sourceLocalId": int(source_step[0]),
                "targetLocalId": int(target_step[0]),
                "edge": edge,
                "transitionKind": transition_kind,
                "sourceActionName": source_action_name,
                "sourceActionClass": safe_key(source_step[3]),
                "targetActionName": safe_key(target_step[2]),
                "targetActionClass": safe_key(target_step[3]),
                "predicate": predicate,
            }.items()
            if value not in ("", None, [], {})
        }
        if transition_kind == "parallelFanout":
            step.update({
                "runtimeSemantics": "binary_proven_extra_thread_launch",
                "siblingOrderEvidence": False,
                "runtimeAuthoritySource": safe_key(
                    (extra_thread_scheduler_contract or {}).get("source")
                ),
            })
        steps.append(step)
    return steps


def _expand_native_control_path_candidates(
    flow: dict[str, Any],
    candidate_kinds: dict[str, str],
) -> tuple[dict[str, str], set[str]]:
    """Admit only exact native-path neighbors of index-backed mission scenes.

    A Story filename's nominal owner is not a reliable mission boundary. Keep
    the index set as the anchor, then admit an external Story key only when its
    exact serialized event-to-action path is prefix-comparable with an anchored
    scene under the same level/script/event header. Equal and divergent paths,
    generic scene-graph edges, file order, and stand-alone exact occurrences do
    not expand mission membership.
    """
    expanded = dict(candidate_kinds)
    anchor_keys = set(candidate_kinds)
    admitted: set[str] = set()
    if not anchor_keys:
        return expanded, admitted

    for rows in _native_event_story_paths(flow, None).values():
        rows = list(rows)
        for anchor_key, anchor_path, _source_files, _event_detail, _downstream in rows:
            if anchor_key not in anchor_keys:
                continue
            for external_key, external_path, _target_files, _target_detail, _target_downstream in rows:
                if external_key in anchor_keys or external_key == anchor_key:
                    continue
                if not (
                    _strict_native_path_prefix(anchor_path, external_path)
                    or _strict_native_path_prefix(external_path, anchor_path)
                ):
                    continue
                external_kind = scene_order_infer_kind(external_key, "")
                if external_kind not in SOURCE_STORY_NODE_KINDS:
                    continue
                expanded.setdefault(external_key, external_kind)
                admitted.add(external_key)
    return expanded, admitted


def _native_control_path_story_edges(
    flow: dict[str, Any],
    candidate_keys: set[str],
    extra_thread_scheduler_contract: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Recover strict Story order when one native control path prefixes another."""
    event_paths = _native_event_story_paths(flow, candidate_keys)

    evidence_by_pair: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for signature, rows in event_paths.items():
        for source_key, source_path, source_files, source_event_detail, _source_downstream in rows:
            for target_key, target_path, target_files, target_event_detail, _target_downstream in rows:
                if (
                    source_key == target_key
                    or not _strict_native_path_prefix(source_path, target_path)
                ):
                    continue
                source_path_ids = tuple(step[0] for step in source_path)
                target_path_ids = tuple(step[0] for step in target_path)
                transition_steps = _native_story_transition_steps(
                    source_path,
                    target_path,
                    extra_thread_scheduler_contract,
                )
                if not transition_steps:
                    continue
                evidence_by_pair[(source_key, target_key)].append({
                    "levelId": signature[0],
                    "scriptId": signature[1],
                    "headerLocalId": signature[2],
                    "eventName": signature[3],
                    "eventDetails": [
                        json.loads(value)
                        for value in sorted({
                            source_event_detail,
                            target_event_detail,
                        })
                    ],
                    "sourcePath": list(source_path_ids),
                    "targetPath": list(target_path_ids),
                    "transitionSteps": transition_steps,
                    "transitionKinds": sorted({
                        step["transitionKind"]
                        for step in transition_steps
                    }),
                    "sourceFiles": sorted(
                        {*source_files, *target_files},
                        key=natural_key,
                    ),
                })

    conflicts = {
        pair
        for pair in evidence_by_pair
        if (pair[1], pair[0]) in evidence_by_pair
    }
    edges: list[dict[str, Any]] = []
    for pair, evidence_rows in sorted(
        evidence_by_pair.items(),
        key=lambda item: (natural_key(item[0][0]), natural_key(item[0][1])),
    ):
        if pair in conflicts:
            continue
        transition_kinds = sorted({
            kind
            for evidence in evidence_rows
            for kind in evidence.get("transitionKinds") or []
        })
        edges.append({
            "from": pair[0],
            "to": pair[1],
            "kind": "levelscriptNativeControlPath",
            "tier": "strong",
            "source": "exact serialized event-to-action local-id path prefix",
            "transitionKinds": transition_kinds,
            "branchingTransition": any(
                kind != "linear" for kind in transition_kinds
            ),
            "sourceFiles": sorted({
                source_file
                for evidence in evidence_rows
                for source_file in evidence.get("sourceFiles") or []
            }),
            "levelIds": sorted({
                str(evidence.get("levelId") or "")
                for evidence in evidence_rows
                if evidence.get("levelId")
            }),
            "events": evidence_rows,
        })
    return edges


def _quest_state_action_path_story_edges(
    flow: dict[str, Any],
    candidate_keys: set[str],
) -> list[dict[str, Any]]:
    """Recover typed Story order from one exact quest-state action chain."""
    grouped: dict[tuple[Any, ...], dict[int, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    metadata: dict[tuple[Any, ...], dict[str, Any]] = {}
    for quest in flow.get("quests") or []:
        if not isinstance(quest, dict):
            continue
        quest_id = safe_key(quest.get("id") or quest.get("questId"))
        for row in quest.get("storyConnections") or []:
            if not isinstance(row, dict):
                continue
            story_key = safe_key(row.get("key"))
            relation = safe_key(row.get("relation"))
            action_path = tuple(
                int(local_id)
                for local_id in row.get("actionPathLocalIds") or []
                if isinstance(local_id, int)
            )
            path_index = row.get("actionPathIndex")
            action_local_id = row.get("actionLocalId")
            if (
                story_key not in candidate_keys
                or relation not in {
                    "levelscript_quest_completed_action",
                    "levelscript_quest_processing_action",
                }
                or safe_key(row.get("confidence")) != "native_typed_direct"
                or safe_key(row.get("event")) != "LevelEvent_OnQuestStateChanged"
                or not safe_key(row.get("nativeMappingId")).startswith("gameassembly-")
                or not isinstance(path_index, int)
                or not isinstance(action_local_id, int)
                or path_index < 0
                or path_index >= len(action_path)
                or action_path[path_index] != action_local_id
            ):
                continue
            signature = (
                quest_id,
                relation,
                row.get("questState"),
                safe_key(row.get("levelId")),
                safe_key(row.get("scriptId")),
                row.get("headerLocalId"),
                safe_key(row.get("sourceFile")),
                action_path,
            )
            grouped[signature][path_index].add(story_key)
            metadata[signature] = {
                "questId": quest_id,
                "levelId": safe_key(row.get("levelId")),
                "scriptId": safe_key(row.get("scriptId")),
                "sourceFile": safe_key(row.get("sourceFile")),
                "headerLocalId": row.get("headerLocalId"),
                "questState": row.get("questState"),
                "actionPathLocalIds": list(action_path),
            }

    evidence_by_pair: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for signature, keys_by_index in grouped.items():
        ordered_indexes = sorted(keys_by_index)
        for source_index, target_index in zip(ordered_indexes, ordered_indexes[1:]):
            for source_key in sorted(keys_by_index[source_index], key=natural_key):
                for target_key in sorted(keys_by_index[target_index], key=natural_key):
                    if source_key == target_key:
                        continue
                    item = metadata[signature]
                    evidence_by_pair[(source_key, target_key)].append({
                        "questId": item["questId"],
                        "levelId": item["levelId"],
                        "scriptId": item["scriptId"],
                        "sourceFile": item["sourceFile"],
                        "headerLocalId": item["headerLocalId"],
                        "sourceLocalId": item["actionPathLocalIds"][source_index],
                        "targetLocalId": item["actionPathLocalIds"][target_index],
                        "questState": item["questState"],
                        "actionPathLocalIds": item["actionPathLocalIds"],
                    })

    edges: list[dict[str, Any]] = []
    for pair, evidence_rows in sorted(
        evidence_by_pair.items(),
        key=lambda item: (natural_key(item[0][0]), natural_key(item[0][1])),
    ):
        edges.append({
            "from": pair[0],
            "to": pair[1],
            "kind": "levelscriptQuestStateActionPath",
            "tier": "strong",
            "source": (
                "exact LevelEvent_OnQuestStateChanged ActionHeader.nextId/"
                "ActionBase.nextId typed playback path"
            ),
            "sourceFiles": sorted({
                row["sourceFile"] for row in evidence_rows if row["sourceFile"]
            }),
            "levelIds": sorted({
                row["levelId"] for row in evidence_rows if row["levelId"]
            }),
            "questIds": sorted({
                row["questId"] for row in evidence_rows if row["questId"]
            }),
            "events": evidence_rows,
        })
    return edges


def _quest_succeed_lifecycle_story_edges(
    flow: dict[str, Any],
    candidate_keys: set[str],
    lifecycle_contract: dict[str, Any] | None,
    mission_source: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Join authored objective and succeed-action Story rows by exact quest identity."""
    if lifecycle_contract is None:
        return [], []
    contract = lifecycle_contract or {}
    matched_rows: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    for quest in flow.get("quests") or []:
        if not isinstance(quest, dict):
            continue
        quest_id = safe_key(quest.get("id") or quest.get("questId"))
        rows = [
            row for row in quest.get("storyConnections") or []
            if isinstance(row, dict)
        ]
        objective_rows = [
            row for row in rows
            if safe_key(row.get("key")) in candidate_keys
            and safe_key(row.get("relation")) == "objective_condition"
            and safe_key(row.get("direction")) == "story_to_quest"
            and safe_key(row.get("phase")) == "progress"
        ]
        succeed_rows = [
            row for row in rows
            if safe_key(row.get("key")) in candidate_keys
            and safe_key(row.get("relation")) == "client_action_succeed"
            and safe_key(row.get("direction")) == "quest_to_story"
            and safe_key(row.get("phase")) == "succeed"
            and safe_key(row.get("confidence")) == "native_typed_direct"
        ]
        matched_rows.extend(
            (quest_id, source_row, target_row)
            for source_row in objective_rows
            for target_row in succeed_rows
            if safe_key(source_row.get("key"))
            and safe_key(target_row.get("key"))
            and safe_key(source_row.get("key"))
            != safe_key(target_row.get("key"))
        )
    if not matched_rows:
        return [], []

    validation = contract.get("validation") or {}
    if validation.get("status") != "validated":
        return [], [{
            "validator": "questSucceedLifecycle",
            "check": "validatedInstalledBinaryContract",
            "expected": "validated",
            "actual": validation.get("status"),
            "sourcePaths": [mission_source] if mission_source else [],
        }]

    mission_path = ROOT / mission_source if mission_source else Path()
    if not mission_source or not mission_path.is_file():
        return [], [{
            "validator": "questSucceedLifecycle",
            "check": "missionRuntimeSourceExists",
            "expected": "file",
            "actual": "missing",
            "sourcePaths": [mission_source] if mission_source else [],
        }]
    mission_sha256 = hashlib.sha256(mission_path.read_bytes()).hexdigest().upper()
    related_original_files = [
        {
            "kind": "original_mission_runtime",
            "sourceFile": mission_source,
            "sha256": mission_sha256,
            "relationship": "authored_quest_objective_and_succeed_action",
        },
        *[
            dict(row)
            for row in contract.get("relatedOriginalFiles") or []
            if isinstance(row, dict)
        ],
    ]

    def compact(row: dict[str, Any]) -> dict[str, Any]:
        fields = (
            "key", "kind", "relation", "direction", "phase", "confidence",
            "source", "objectiveIndex", "conditionType", "finishId",
            "actionSlot", "actionId", "actionType",
        )
        return {name: row[name] for name in fields if name in row}

    edges: list[dict[str, Any]] = []
    for quest_id, source_row, target_row in matched_rows:
        source_key = safe_key(source_row.get("key"))
        target_key = safe_key(target_row.get("key"))
        edges.append({
            "from": source_key,
            "to": target_key,
            "kind": "questSucceedLifecycle",
            "tier": "strong",
            "source": (
                "MissionRuntime objective completion -> server quest-success "
                "state -> binary-proven OnSucceedClientAction dispatch"
            ),
            "questIds": [quest_id] if quest_id else [],
            "sourceFiles": [mission_source],
            "sourceSha256": {mission_source: mission_sha256},
            "objectiveStoryRelation": compact(source_row),
            "succeedStoryRelation": compact(target_row),
            "nativeLifecycleContract": {
                "schema": contract.get("schema"),
                "classification": contract.get("classification"),
                "succeedQuest": contract.get("succeedQuest") or {},
                "succeedActionCalls": contract.get("succeedActionCalls") or [],
                "finding": contract.get("finding") or "",
                "boundary": contract.get("boundary") or "",
            },
            "relatedOriginalFiles": related_original_files,
        })
    unique: dict[tuple[str, str, tuple[str, ...]], dict[str, Any]] = {}
    for edge in edges:
        signature = (edge["from"], edge["to"], tuple(edge["questIds"]))
        unique[signature] = edge
    return sorted(unique.values(), key=_edge_sort_key), []


def _quest_lifecycle_definition_rows(
    flow: dict[str, Any],
    candidate_keys: set[str],
    lifecycle_contract: dict[str, Any] | None,
    mission_source: str,
) -> list[dict[str, Any]]:
    """Expose authored lifecycle definitions whose binary dispatcher is absent.

    These are evidence-bearing rows, never order edges. The rule is applied to
    the entire mission corpus and is admitted only after the binary contract
    validates that the corresponding current-build AOT dispatcher set is empty.
    """
    contract = lifecycle_contract or {}
    if (
        (contract.get("validation") or {}).get("status") != "validated"
        or contract.get("startActionDispatchers")
    ):
        return []
    mission_path = ROOT / mission_source if mission_source else Path()
    if not mission_source or not mission_path.is_file():
        return []
    mission_sha256 = hashlib.sha256(mission_path.read_bytes()).hexdigest().upper()
    related_original_files = [{
        "kind": "original_mission_runtime",
        "sourceFile": mission_source,
        "sha256": mission_sha256,
        "relationship": "authored_quest_lifecycle_definition",
    }, *[
        dict(row)
        for row in contract.get("relatedOriginalFiles") or []
        if isinstance(row, dict)
    ]]
    rows: list[dict[str, Any]] = []
    for quest in flow.get("quests") or []:
        if not isinstance(quest, dict):
            continue
        quest_id = safe_key(quest.get("id") or quest.get("questId"))
        for relation in quest.get("storyConnections") or []:
            if not isinstance(relation, dict):
                continue
            story_key = safe_key(relation.get("key"))
            if (
                story_key not in candidate_keys
                or safe_key(relation.get("relation")) != "client_action_start"
                or safe_key(relation.get("direction")) != "quest_to_story"
                or safe_key(relation.get("phase")) != "start"
                or safe_key(relation.get("confidence")) != "native_typed_direct"
            ):
                continue
            rows.append({
                "kind": "questLifecycleDefinition",
                "questId": quest_id,
                "storyKey": story_key,
                "actionSlot": relation.get("actionSlot"),
                "actionId": relation.get("actionId"),
                "actionType": relation.get("actionType"),
                "runtimeDispatchStatus": (
                    "authored_definition_no_current_aot_dispatch"
                ),
                "source": contract.get("source") or "",
                "boundary": contract.get("boundary") or "",
                "relatedOriginalFiles": related_original_files,
            })
    unique = {
        (row["questId"], row["storyKey"], row.get("actionId")): row
        for row in rows
    }
    return sorted(
        unique.values(),
        key=lambda row: (
            natural_key(row["questId"]),
            natural_key(row["storyKey"]),
            int(row.get("actionId") or -1),
        ),
    )


def _repo_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _find_spawner_config(
    level_id: str,
    spawner_id: int,
    roots: Iterable[Path],
) -> Path | None:
    for root in roots:
        candidates = sorted({
            path
            for path in (root / level_id).glob(f"*_{spawner_id}.json")
            if path.is_file()
        }, key=lambda path: path.as_posix().lower())
        if candidates:
            return candidates[0] if len(candidates) == 1 else None
    return None


def _event_source_files(event: dict[str, Any]) -> set[str]:
    return {
        source_file
        for source_file in (
            safe_key(event.get("sourceFile")),
            *[
                safe_key(value)
                for value in event.get("sourceFiles") or []
            ],
            *[
                safe_key(value)
                for value in event.get("listenerSourceFiles") or []
            ],
        )
        if source_file
    }


def _spawner_story_event_routes(
    flow: dict[str, Any],
    candidate_keys: set[str],
) -> Iterable[tuple[str, str, dict[str, Any], dict[str, Any]]]:
    """Yield exact direct or local-relayed Story routes from spawner callbacks.

    A Story action may sit directly under a typed spawner event header, or a
    spawner callback may raise a same-script custom event whose exact listener
    reaches the Story action.  The latter is accepted only when the generated
    native evidence preserves the producer control path, exact receiver, exact
    listener event key, and at least one exact listener route.  Merely matching
    event-key strings is insufficient.
    """
    for row in _story_connection_rows(flow):
        story_key = safe_key(row.get("key"))
        if (
            story_key not in candidate_keys
            or safe_key(row.get("confidence")) not in {
                "native_typed_direct",
                "native_typed_direct_unscoped",
            }
            or not safe_key(row.get("nativeMappingId")).startswith("gameassembly-")
        ):
            continue

        for occurrence in _connection_native_occurrences(row):
            if (
                story_key not in {
                    safe_key(value)
                    for value in occurrence.get("allStoryKeysInRecord") or []
                }
                or not safe_key(occurrence.get("recordClass")).startswith("play_")
            ):
                continue
            level_id = safe_key(occurrence.get("levelId"))
            source_file = safe_key(occurrence.get("sourceFile"))
            for owner in occurrence.get("nativeEventOwners") or []:
                if not isinstance(owner, dict):
                    continue
                yield story_key, level_id, owner, {
                    "storyKey": story_key,
                    "sourceFile": source_file,
                    "scriptId": safe_key(occurrence.get("scriptId")),
                    "headerLocalId": owner.get("headerLocalId"),
                    "actionLocalId": occurrence.get("localId"),
                    "actionName": safe_key(occurrence.get("actionName")),
                    "eventDetail": owner.get("eventDetail"),
                    "routeMode": "directPlayback",
                }

        for producer in row.get("nativeEventProducerRoutes") or []:
            if not isinstance(producer, dict):
                continue
            producer_script_id = safe_key(producer.get("producerScriptId"))
            target_script_id = safe_key(producer.get("targetScriptId"))
            raised_event_key = safe_key(producer.get("raisedEventKey"))
            listener_script_ids = {
                safe_key(value)
                for value in producer.get("listenerScriptIds") or []
                if safe_key(value)
            }
            listener_routes = [
                route
                for route in producer.get("listenerRoutes") or []
                if isinstance(route, dict)
                and safe_key(route.get("listenerScriptId"))
                == target_script_id
                and isinstance(route.get("listenerEventOwner"), dict)
                and route["listenerEventOwner"].get("status")
                == "exact_serialized_control_path"
                and safe_key(
                    (route["listenerEventOwner"].get("eventDetail") or {}).get(
                        "type"
                    )
                )
                == "ScriptEvent_OnCustomEvent"
                and safe_key(
                    (route["listenerEventOwner"].get("eventDetail") or {}).get(
                        "eventKey"
                    )
                )
                == raised_event_key
            ]
            if (
                producer.get("status") != "exact_serialized_local_producer"
                or safe_key(producer.get("storyKey")) != story_key
                or safe_key(producer.get("producerAction"))
                != "RaiseCustomScriptEvent"
                or safe_key(producer.get("receiverMode")) != "current_script"
                or not producer_script_id
                or target_script_id != producer_script_id
                or listener_script_ids != {target_script_id}
                or not raised_event_key
                or not listener_routes
                or not safe_key(producer.get("nativeMappingId")).startswith(
                    "gameassembly-"
                )
                or producer.get("serverExchange") is not False
            ):
                continue
            listener_source_files = sorted({
                safe_key(route.get("listenerSourceFile"))
                for route in listener_routes
                if safe_key(route.get("listenerSourceFile"))
            })
            producer_source_file = safe_key(producer.get("producerSourceFile"))
            for owner in producer.get("producerControlPaths") or []:
                if not isinstance(owner, dict):
                    continue
                detail = (
                    owner.get("eventDetail")
                    if isinstance(owner.get("eventDetail"), dict)
                    else {}
                )
                level_id = safe_key(detail.get("levelId")) or safe_key(
                    producer.get("levelId")
                )
                yield story_key, level_id, owner, {
                    "storyKey": story_key,
                    "sourceFile": producer_source_file,
                    "sourceFiles": sorted({
                        producer_source_file,
                        *listener_source_files,
                    } - {""}),
                    "listenerSourceFiles": listener_source_files,
                    "scriptId": producer_script_id,
                    "headerLocalId": owner.get("headerLocalId"),
                    "actionLocalId": producer.get("producerActionLocalId"),
                    "actionName": "RaiseCustomScriptEvent",
                    "eventDetail": detail,
                    "routeMode": "sameScriptCustomEventRelay",
                    "raisedEventKey": raised_event_key,
                    "targetScriptId": target_script_id,
                    "listenerRoutes": listener_routes,
                }


def _spawner_wave_part_killed_story_edges(
    flow: dict[str, Any],
    candidate_keys: set[str],
    *,
    spawner_roots: Iterable[Path] | None = None,
) -> list[dict[str, Any]]:
    """Join typed wave-begin playback through one named PartKilled dependency.

    Current ``TimelineWaveBlock.OnInit`` resolves mode 2's serialized
    ``waveModeTargetKey`` with ``Timeline.TryGetWaveBlock`` and stores the
    returned block as ``previousWaveBlock``. ``AllowToSendStart`` then requires
    that exact block's killed count before the dependent wave can start.
    Parallel/Sequence modes and unnamed HP callbacks are intentionally ignored.
    """
    routes: dict[
        tuple[str, int],
        dict[str, dict[str, list[dict[str, Any]]]],
    ] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for story_key, level_id, owner, event in _spawner_story_event_routes(
        flow,
        candidate_keys,
    ):
        detail = owner.get("eventDetail") if isinstance(owner, dict) else None
        if (
            owner.get("status") != "exact_serialized_control_path"
            or safe_key(owner.get("headerName"))
            != "LevelEvent_OnSpawnerWaveBegin"
            or not isinstance(detail, dict)
            or safe_key(detail.get("type"))
            != "LevelEvent_OnSpawnerWaveBegin"
            or safe_key(detail.get("payloadSchemaStatus"))
            != "exact_current_build_memorypack_fields"
            or not safe_key(detail.get("payloadSchemaMappingId")).startswith(
                "gameassembly-"
            )
            or not isinstance(detail.get("spawnerFilterId"), int)
            or not safe_key(detail.get("waveKeyFilter"))
            or not level_id
        ):
            continue
        spawner_id = int(detail["spawnerFilterId"])
        wave_key = safe_key(detail.get("waveKeyFilter"))
        routes[(level_id, spawner_id)][wave_key][story_key].append(event)

    roots = tuple(spawner_roots or SPAWNER_CONFIG_ROOTS)
    evidence_by_pair: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for (level_id, spawner_id), story_by_wave in sorted(routes.items()):
        config_path = _find_spawner_config(level_id, spawner_id, roots)
        if config_path is None:
            continue
        try:
            decoded = decode_spawner_wave_map(config_path.read_bytes())
        except (OSError, SpawnerWaveDecodeError):
            continue
        if safe_key(decoded.get("configId")) != config_path.stem:
            continue
        config_source = _repo_path(config_path)
        for wave in decoded.get("waves") or []:
            if (
                not isinstance(wave, dict)
                or wave.get("waveMode") != 2
                or not safe_key(wave.get("waveModeTargetKey"))
            ):
                continue
            wave_key = safe_key(wave.get("waveKey"))
            target_wave_key = safe_key(wave.get("waveModeTargetKey"))
            parent_rows = story_by_wave.get(target_wave_key) or {}
            child_rows = story_by_wave.get(wave_key) or {}
            for parent_key in sorted(parent_rows, key=natural_key):
                for child_key in sorted(child_rows, key=natural_key):
                    if parent_key == child_key:
                        continue
                    event_sources = sorted({
                        source_file
                        for event in (
                            parent_rows[parent_key] + child_rows[child_key]
                        )
                        for source_file in _event_source_files(event)
                    })
                    evidence_by_pair[(parent_key, child_key)].append({
                        "levelId": level_id,
                        "spawnerId": spawner_id,
                        "waveId": wave.get("waveId"),
                        "waveKey": wave_key,
                        "targetWaveKey": target_wave_key,
                        "waveMode": "PartKilled",
                        "waveModeKillCount": wave.get("waveModeKillCount"),
                        "sourceFiles": [config_source, *event_sources],
                        "schemaMappingId": safe_key(decoded.get("schemaMappingId")),
                        "runtimeMappingId": SPAWNER_WAVE_RUNTIME_MAPPING_ID,
                        "parentEvents": parent_rows[parent_key],
                        "childEvents": child_rows[child_key],
                    })

    edges: list[dict[str, Any]] = []
    for pair, evidence_rows in sorted(
        evidence_by_pair.items(),
        key=lambda item: (natural_key(item[0][0]), natural_key(item[0][1])),
    ):
        uses_custom_relay = any(
            event.get("routeMode") == "sameScriptCustomEventRelay"
            for evidence in evidence_rows
            for field in ("parentEvents", "childEvents")
            for event in evidence.get(field) or []
        )
        edges.append({
            "from": pair[0],
            "to": pair[1],
            "kind": "spawnerWavePartKilled",
            "tier": "strong",
            "source": (
                "exact SpawnerConfig waveMode=PartKilled target key + exact "
                "LevelEvent_OnSpawnerWaveBegin typed playback"
                + (
                    " through an exact same-script custom-event relay"
                    if uses_custom_relay
                    else ""
                )
            ),
            "sourceFiles": sorted({
                source_file
                for evidence in evidence_rows
                for source_file in evidence.get("sourceFiles") or []
            }),
            "levelIds": sorted({
                safe_key(evidence.get("levelId"))
                for evidence in evidence_rows
                if safe_key(evidence.get("levelId"))
            }),
            "spawnerId": evidence_rows[0]["spawnerId"],
            "waveId": evidence_rows[0]["waveId"],
            "waveKey": evidence_rows[0]["waveKey"],
            "targetWaveKey": evidence_rows[0]["targetWaveKey"],
            "waveMode": "PartKilled",
            "waveModeKillCount": evidence_rows[0]["waveModeKillCount"],
            "schemaMappingId": evidence_rows[0]["schemaMappingId"],
            "runtimeMappingId": evidence_rows[0]["runtimeMappingId"],
            "events": evidence_rows,
        })
    return edges


def _wave_kill_dominating_group_key(wave: dict[str, Any]) -> str:
    """Return the group whose begin event dominates all spawns in this wave.

    The installed runtime gives group mode 1 (``Sequence``) the immediately
    preceding ``groupList`` block and mode 2 (``PartKilled``) its named target
    block.  A mode-0 (``Parallel``) group is independent.  Since
    ``TimelineWaveBlock.InitWave`` appends group blocks in
    the decoded ``groupMap`` enumeration order, the first named group dominates
    every group only when each later block resolves through one of those two
    predecessor forms back to it.
    """
    groups = [
        group
        for group in wave.get("groups") or []
        if isinstance(group, dict)
    ]
    if not groups:
        return ""
    root_key = safe_key(groups[0].get("groupKey"))
    if not root_key or groups[0].get("groupMode") not in (0, 1):
        return ""

    key_to_index = {
        safe_key(group.get("groupKey")): index
        for index, group in enumerate(groups)
        if safe_key(group.get("groupKey"))
    }
    dominated = [True]
    for index, group in enumerate(groups[1:], 1):
        mode = group.get("groupMode")
        if mode == 1:
            dominated.append(dominated[index - 1])
        elif mode == 2:
            target_index = key_to_index.get(
                safe_key(group.get("groupModeTargetKey"))
            )
            dominated.append(
                target_index is not None
                and target_index < index
                and dominated[target_index]
            )
        else:
            dominated.append(False)
    return root_key if all(dominated) else ""


def _spawner_wave_group_part_killed_story_edges(
    flow: dict[str, Any],
    candidate_keys: set[str],
    *,
    spawner_roots: Iterable[Path] | None = None,
) -> list[dict[str, Any]]:
    """Recover cross-wave order where exact group and wave callbacks meet.

    ``StartWave`` raises wave begin before ``Tick`` can start a group, and
    ``StartGroup`` raises group begin before ticking that group's actions.
    A dependent mode-2 wave cannot start until the named prior wave reaches
    its serialized kill threshold.  The domination check above additionally
    requires every possible spawning group in that prior wave to descend from
    one exact group-begin event.
    """
    routes: dict[tuple[str, int], dict[str, Any]] = defaultdict(
        lambda: {
            "wave": defaultdict(lambda: defaultdict(list)),
            "group": defaultdict(lambda: defaultdict(list)),
        }
    )
    for story_key, level_id, owner, event in _spawner_story_event_routes(
        flow,
        candidate_keys,
    ):
        detail = owner.get("eventDetail") if isinstance(owner, dict) else None
        header_name = safe_key(owner.get("headerName"))
        if (
            owner.get("status") != "exact_serialized_control_path"
            or header_name not in {
                "LevelEvent_OnSpawnerWaveBegin",
                "LevelEvent_OnSpawnerGroupBegin",
            }
            or not isinstance(detail, dict)
            or safe_key(detail.get("type")) != header_name
            or safe_key(detail.get("payloadSchemaStatus"))
            != "exact_current_build_memorypack_fields"
            or not safe_key(detail.get("payloadSchemaMappingId")).startswith(
                "gameassembly-"
            )
            or not isinstance(detail.get("spawnerFilterId"), int)
            or not level_id
        ):
            continue
        route_kind = (
            "wave"
            if header_name == "LevelEvent_OnSpawnerWaveBegin"
            else "group"
        )
        selector_key = safe_key(
            detail.get(
                "waveKeyFilter"
                if route_kind == "wave"
                else "groupKeyFilter"
            )
        )
        if not selector_key:
            continue
        routes[(level_id, int(detail["spawnerFilterId"]))][route_kind][
            selector_key
        ][story_key].append(event)

    roots = tuple(spawner_roots or SPAWNER_CONFIG_ROOTS)
    evidence_by_pair: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for (level_id, spawner_id), route_sets in sorted(routes.items()):
        config_path = _find_spawner_config(level_id, spawner_id, roots)
        if config_path is None:
            continue
        try:
            decoded = decode_spawner_wave_map(config_path.read_bytes())
        except (OSError, SpawnerWaveDecodeError):
            continue
        if safe_key(decoded.get("configId")) != config_path.stem:
            continue
        config_source = _repo_path(config_path)
        wave_by_key = {
            safe_key(wave.get("waveKey")): wave
            for wave in decoded.get("waves") or []
            if isinstance(wave, dict) and safe_key(wave.get("waveKey"))
        }
        group_to_wave: dict[str, str] = {}
        duplicate_group_keys: set[str] = set()
        for wave_key, wave in wave_by_key.items():
            for group in wave.get("groups") or []:
                group_key = (
                    safe_key(group.get("groupKey"))
                    if isinstance(group, dict)
                    else ""
                )
                if group_key:
                    if group_key in group_to_wave:
                        duplicate_group_keys.add(group_key)
                    else:
                        group_to_wave[group_key] = wave_key
        for group_key in duplicate_group_keys:
            group_to_wave.pop(group_key, None)

        def add_pairs(
            parents: dict[str, list[dict[str, Any]]],
            children: dict[str, list[dict[str, Any]]],
            *,
            parent_wave_key: str,
            child_wave_key: str,
            parent_group_key: str = "",
            child_group_key: str = "",
            path: str,
        ) -> None:
            for parent_key in sorted(parents, key=natural_key):
                for child_key in sorted(children, key=natural_key):
                    if parent_key == child_key:
                        continue
                    source_files = sorted({
                        config_source,
                        *[
                            source_file
                            for event in (
                                parents[parent_key] + children[child_key]
                            )
                            for source_file in _event_source_files(event)
                        ],
                    })
                    evidence_by_pair[(parent_key, child_key)].append({
                        "levelId": level_id,
                        "spawnerId": spawner_id,
                        "waveKey": child_wave_key,
                        "targetWaveKey": parent_wave_key,
                        "groupKey": child_group_key,
                        "targetGroupKey": parent_group_key,
                        "waveMode": "PartKilled",
                        "waveModeKillCount":
                            wave_by_key[child_wave_key].get("waveModeKillCount"),
                        "spawnerDependencyPath": path,
                        "sourceFiles": source_files,
                        "schemaMappingId": safe_key(
                            decoded.get("schemaMappingId")
                        ),
                        "runtimeMappingId": SPAWNER_WAVE_RUNTIME_MAPPING_ID,
                        "parentEvents": parents[parent_key],
                        "childEvents": children[child_key],
                    })

        for child_wave_key, child_wave in wave_by_key.items():
            parent_wave_key = safe_key(child_wave.get("waveModeTargetKey"))
            if (
                child_wave.get("waveMode") != 2
                or parent_wave_key not in wave_by_key
            ):
                continue
            parent_wave_routes = route_sets["wave"].get(parent_wave_key) or {}
            for group_key, child_group_routes in route_sets["group"].items():
                if group_to_wave.get(group_key) != child_wave_key:
                    continue
                add_pairs(
                    parent_wave_routes,
                    child_group_routes,
                    parent_wave_key=parent_wave_key,
                    child_wave_key=child_wave_key,
                    child_group_key=group_key,
                    path="parentWaveBegin_to_dependentGroupBegin",
                )

            root_group_key = _wave_kill_dominating_group_key(
                wave_by_key[parent_wave_key]
            )
            if root_group_key in duplicate_group_keys:
                root_group_key = ""
            parent_group_routes = (
                route_sets["group"].get(root_group_key) or {}
                if root_group_key
                else {}
            )
            child_wave_routes = route_sets["wave"].get(child_wave_key) or {}
            add_pairs(
                parent_group_routes,
                child_wave_routes,
                parent_wave_key=parent_wave_key,
                child_wave_key=child_wave_key,
                parent_group_key=root_group_key,
                path="dominatingGroupBegin_to_dependentWaveBegin",
            )
            for group_key, child_group_routes in route_sets["group"].items():
                if group_to_wave.get(group_key) != child_wave_key:
                    continue
                add_pairs(
                    parent_group_routes,
                    child_group_routes,
                    parent_wave_key=parent_wave_key,
                    child_wave_key=child_wave_key,
                    parent_group_key=root_group_key,
                    child_group_key=group_key,
                    path="dominatingGroupBegin_to_dependentGroupBegin",
                )

    edges: list[dict[str, Any]] = []
    for pair, evidence_rows in sorted(
        evidence_by_pair.items(),
        key=lambda item: (natural_key(item[0][0]), natural_key(item[0][1])),
    ):
        uses_custom_relay = any(
            event.get("routeMode") == "sameScriptCustomEventRelay"
            for evidence in evidence_rows
            for field in ("parentEvents", "childEvents")
            for event in evidence.get(field) or []
        )
        edges.append({
            "from": pair[0],
            "to": pair[1],
            "kind": "spawnerWaveGroupPartKilled",
            "tier": "strong",
            "source": (
                "exact SpawnerConfig wave/group nesting + PartKilled gate + "
                "installed StartWave/StartGroup callback order"
                + (
                    " + exact same-script custom-event relay"
                    if uses_custom_relay
                    else ""
                )
            ),
            "sourceFiles": sorted({
                source_file
                for evidence in evidence_rows
                for source_file in evidence.get("sourceFiles") or []
            }),
            "levelIds": sorted({
                safe_key(evidence.get("levelId"))
                for evidence in evidence_rows
                if safe_key(evidence.get("levelId"))
            }),
            "spawnerId": evidence_rows[0]["spawnerId"],
            "waveKey": evidence_rows[0]["waveKey"],
            "targetWaveKey": evidence_rows[0]["targetWaveKey"],
            "groupKey": evidence_rows[0]["groupKey"],
            "targetGroupKey": evidence_rows[0]["targetGroupKey"],
            "waveMode": "PartKilled",
            "waveModeKillCount": evidence_rows[0]["waveModeKillCount"],
            "spawnerDependencyPath":
                evidence_rows[0]["spawnerDependencyPath"],
            "schemaMappingId": evidence_rows[0]["schemaMappingId"],
            "runtimeMappingId": evidence_rows[0]["runtimeMappingId"],
            "events": evidence_rows,
        })
    return edges


def _native_ordered_sequence_contexts(
    topology: dict[str, Any],
    routes: Iterable[tuple[tuple[str, str, int, str], str, tuple[tuple[Any, ...], ...]]],
) -> list[dict[str, Any]]:
    """Project exact Story-path coverage onto serialized Branch sequence slots.

    ``decode_levelscript_native_action_topology`` already recovers the complete
    runtime action map from the original LevelScript.  This helper only joins
    that map to paths that independently reached a Story playback record.  It
    never treats an unvisited sibling arm as a Story placement and never emits
    order edges; the separate ``_native_ordered_branch_sequences`` gate owns
    that stricter admission.
    """
    action_by_local = {
        int(action.get("localId")): action
        for action in topology.get("actions") or []
        if isinstance(action, dict) and isinstance(action.get("localId"), int)
    }
    grouped: dict[
        tuple[int, tuple[int, ...]],
        dict[str, Any],
    ] = {}
    sequence_pattern = re.compile(r"Branch\.sequence\[(\d+)\]")
    for signature, story_key, path in routes:
        for index, step in enumerate(path):
            if (
                not isinstance(step, tuple)
                or len(step) < 3
                or safe_key(step[2]) != "Branch"
                or index + 1 >= len(path)
            ):
                continue
            branch_local_id = step[0]
            if not isinstance(branch_local_id, int):
                continue
            action = action_by_local.get(branch_local_id)
            if not action or safe_key(action.get("actionName")) != "Branch":
                continue
            next_step = path[index + 1]
            edge = safe_key(next_step[1])
            match = sequence_pattern.fullmatch(edge)
            sequence_index: int | None = int(match.group(1)) if match else None
            is_exit = edge == "ActionBase.nextId"
            if sequence_index is None and not is_exit:
                continue
            prefix = tuple(
                int(prefix_step[0])
                for prefix_step in path[:index]
                if isinstance(prefix_step, tuple)
                and isinstance(prefix_step[0], int)
            )
            group = grouped.setdefault(
                (branch_local_id, prefix),
                {
                    "action": action,
                    "routesByIndex": defaultdict(set),
                    "routePathsByIndex": defaultdict(set),
                    "eventSelectors": set(),
                },
            )
            ordinal_key = sequence_index if sequence_index is not None else None
            group["routesByIndex"][ordinal_key].add(story_key)
            group["routePathsByIndex"][ordinal_key].add(tuple(
                int(path_step[0])
                for path_step in path
                if isinstance(path_step, tuple)
                and isinstance(path_step[0], int)
            ))
            group["eventSelectors"].add(signature)

    contexts: list[dict[str, Any]] = []
    for (branch_local_id, prefix), group in sorted(
        grouped.items(),
        key=lambda item: (item[0][0], item[0][1]),
    ):
        action = group["action"]
        detail = action.get("controlDetail") or {}
        serialized_refs = [
            value
            for value in detail.get("branchSequenceActionLocalIds") or []
            if isinstance(value, int)
        ]
        routes_by_index = group["routesByIndex"]
        arm_rows = []
        for sequence_index, entry_local_id in enumerate(serialized_refs):
            story_keys = sorted(
                routes_by_index.get(sequence_index) or set(),
                key=natural_key,
            )
            arm_rows.append({
                "edge": f"Branch.sequence[{sequence_index}]",
                "sequenceIndex": sequence_index,
                "entryLocalId": entry_local_id,
                "storyKeys": story_keys,
                "observedRouteCount": len(
                    group["routePathsByIndex"].get(sequence_index) or set()
                ),
            })
        exit_story_keys = sorted(
            routes_by_index.get(None) or set(),
            key=natural_key,
        )
        if exit_story_keys:
            arm_rows.append({
                "edge": "ActionBase.nextId (after sequence)",
                "sequenceIndex": None,
                "entryLocalId": action.get("nextActionLocalId"),
                "storyKeys": exit_story_keys,
                "observedRouteCount": len(
                    group["routePathsByIndex"].get(None) or set()
                ),
            })
        story_bearing_arm_count = sum(
            bool(row["storyKeys"])
            for row in arm_rows
            if row.get("sequenceIndex") is not None
        )
        observed_arm_count = sum(
            bool(group["routesByIndex"].get(index))
            for index in range(len(serialized_refs))
        )
        admission_reason = (
            "one_or_zero_story_bearing_sequence_arms"
            if story_bearing_arm_count < 2
            else "multiple_story_bearing_arms_require_global_conflict_check"
        )
        contexts.append({
            "kind": "orderedSequenceContext",
            "branchLocalId": branch_local_id,
            "branchPath": list(prefix),
            "actionName": "Branch",
            "controlKind": safe_key(action.get("controlKind")),
            "nativeMappingId": safe_key(action.get("controlRuntimeMappingId")),
            "serializedArmCount": len(serialized_refs),
            "observedSequenceArmCount": observed_arm_count,
            "storyBearingArmCount": story_bearing_arm_count,
            "arms": arm_rows,
            "storyOrderAdmission": "not_admitted",
            "admissionReason": admission_reason,
            "eventSelectors": [
                {
                    "levelId": signature[0],
                    "scriptId": signature[1],
                    "headerLocalId": signature[2],
                    "eventName": signature[3],
                }
                for signature in sorted(
                    group["eventSelectors"],
                    key=lambda value: tuple(natural_key(str(item)) for item in value),
                )
            ],
            "runtimeMappingId": BRANCH_SEQUENCE_RUNTIME["mappingId"],
            "gameAssemblySha256": BRANCH_SEQUENCE_GAME_ASSEMBLY_SHA256,
            "nativeConsumers": [{
                "method": "Beyond.Gameplay.Actions.Branch.Execute",
                "address": "0x18764d990",
                "contract": (
                    "dispatches _idList[m_index], reserves Branch for the next "
                    "item, then resumes ActionBase.nextId after the list"
                ),
            }],
            "evidenceBoundary": (
                "The original serialized Branch slots and exact Story playback "
                "paths identify which sequence arms are observed. A missing Story "
                "in a sibling arm is not proof that the arm is empty at runtime; "
                "this context therefore does not create Story order or ownership."
            ),
        })
    return contexts


def _native_related_action_topologies(
    flow: dict[str, Any],
    candidate_keys: set[str],
    *,
    mission: str = "",
    original_binary_contract: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Attach compact graphs only for exact Story-bearing native paths.

    The join starts from an already validated event-to-Story control path. A
    LevelScript filename, level co-location, or action registration alone can
    never admit a file into a mission.
    """
    related: dict[str, dict[str, set[Any]]] = defaultdict(
        lambda: {"storyKeys": set(), "events": set(), "routes": set()}
    )
    for signature, routes in _native_event_story_paths(flow, candidate_keys).items():
        for story_key, path, source_files, _detail, _downstream in routes:
            for source_file in source_files:
                if "LevelScriptData" not in source_file:
                    continue
                related[source_file]["storyKeys"].add(story_key)
                related[source_file]["events"].add(signature)
                related[source_file]["routes"].add((signature, story_key, path))

    rows: list[dict[str, Any]] = []
    for source_file, context in sorted(
        related.items(),
        key=lambda item: natural_key(item[0]),
    ):
        source_path = Path(source_file)
        if not source_path.is_absolute():
            source_path = ROOT / source_path
        if not source_path.is_file():
            continue
        cache_key = source_path.resolve().as_posix()
        if cache_key not in _NATIVE_ACTION_TOPOLOGY_CACHE:
            try:
                _NATIVE_ACTION_TOPOLOGY_CACHE[cache_key] = (
                    decode_levelscript_native_action_topology(source_path.read_bytes())
                )
            except OSError:
                continue
        topology, diagnostic = _NATIVE_ACTION_TOPOLOGY_CACHE[cache_key]
        route_contexts = _native_ordered_sequence_contexts(
            topology,
            context["routes"],
        )
        selected_header_ids = {
            int(signature[2])
            for signature in context["events"]
            if signature[2] is not None
        }
        selected_event_roots = [
            {
                key: event[key]
                for key in (
                    "localId",
                    "headerName",
                    "nextActionLocalId",
                    "priority",
                    "triggerActiveDuring",
                    "filterMode",
                    "filterMask",
                    "filterLevel",
                    "runtimeShadowedRecordOffsets",
                    "runtimeDuplicateSignatureStatus",
                    "runtimeHeaderSlotMappingId",
                )
                if event.get(key) not in (None, "", [], {})
            }
            for event in topology.get("eventRoots") or []
            if int(event.get("localId") or 0) in selected_header_ids
        ]
        control_actions = [
            {
                key: action[key]
                for key in (
                    "localId",
                    "actionName",
                    "controlKind",
                    "controlRuntimeMappingId",
                    "controlDetail",
                    "nextActionLocalId",
                    "runtimeShadowedRecordOffsets",
                    "runtimeDuplicateSignatureStatus",
                    "runtimeActionSlotMappingId",
                )
                if action.get(key) not in (None, "", [], {})
            }
            for action in topology.get("actions") or []
            if action.get("controlKind")
        ]
        rows.append({
            "schema": topology.get("schema"),
            "status": topology.get("status"),
            "sourceFile": source_file,
            "relatedStoryKeys": sorted(context["storyKeys"], key=natural_key),
            "orderedSequenceContexts": route_contexts,
            "relatedOriginalFiles": _related_original_branch_files(
                mission,
                [source_file],
                original_binary_contract,
                level_relationship="exact_native_story_path_related_levelscript",
                mission_relationship="exact_native_story_path_mission_context",
                binary_relationship="native_action_topology_binary_authority",
            ),
            "eventSelectors": [
                {
                    "levelId": signature[0],
                    "scriptId": signature[1],
                    "headerLocalId": signature[2],
                    "eventName": signature[3],
                }
                for signature in sorted(context["events"], key=lambda value: tuple(
                    natural_key(str(item)) for item in value
                ))
            ],
            "actionNodeCount": int(topology.get("actionNodeCount") or 0),
            "eventRootCount": int(topology.get("eventRootCount") or 0),
            "physicalHeaderRecordCount": int(
                topology.get("physicalHeaderRecordCount") or 0
            ),
            "edgeCount": int(topology.get("edgeCount") or 0),
            "runtimeShadowedActionRecordCount": int(
                topology.get("runtimeShadowedActionRecordCount") or 0
            ),
            "runtimeShadowedActionLocalIdCount": int(
                topology.get("runtimeShadowedActionLocalIdCount") or 0
            ),
            "runtimeShadowedHeaderRecordCount": int(
                topology.get("runtimeShadowedHeaderRecordCount") or 0
            ),
            "runtimeShadowedHeaderLocalIdCount": int(
                topology.get("runtimeShadowedHeaderLocalIdCount") or 0
            ),
            "runtimeShadowedGetterRecordCount": int(
                topology.get("runtimeShadowedGetterRecordCount") or 0
            ),
            "runtimeShadowedGetterLocalIdCount": int(
                topology.get("runtimeShadowedGetterLocalIdCount") or 0
            ),
            "runtimeShadowedIndexedRecordCount": int(
                topology.get("runtimeShadowedIndexedRecordCount") or 0
            ),
            "runtimeShadowedIndexedLocalIdCount": int(
                topology.get("runtimeShadowedIndexedLocalIdCount") or 0
            ),
            "runtimeTerminalTargetCount": int(
                topology.get("runtimeTerminalTargetCount") or 0
            ),
            "runtimeTerminalTargets": list(
                topology.get("runtimeTerminalTargets") or []
            ),
            "orderedSequenceNodeCount": int(
                topology.get("orderedSequenceNodeCount") or 0
            ),
            "parallelFanoutNodeCount": int(
                topology.get("parallelFanoutNodeCount") or 0
            ),
            "conditionalBranchNodeCount": int(
                topology.get("conditionalBranchNodeCount") or 0
            ),
            "loopNodeCount": int(topology.get("loopNodeCount") or 0),
            "selectedEventRoots": selected_event_roots,
            "controlActions": control_actions,
            "validatorDiagnostic": diagnostic,
            "nativeActionMappingId": topology.get("nativeActionMappingId"),
            "runtimeActionSlotMappingId": topology.get(
                "runtimeActionSlotMappingId"
            ),
            "runtimeHeaderSlotMappingId": topology.get(
                "runtimeHeaderSlotMappingId"
            ),
            "runtimeGetterSlotMappingId": topology.get(
                "runtimeGetterSlotMappingId"
            ),
            "eventRootRuntimeMode": topology.get("eventRootRuntimeMode"),
            "runtimeMissingActionTerminalMappingId": topology.get(
                "runtimeMissingActionTerminalMappingId"
            ),
            "relationshipBoundary": (
                "attached through an exact serialized event-to-Story control path; "
                "the rest of the file is file-local topology, not additional mission order"
            ),
        })
    return rows


def _native_ordered_branch_sequences(
    flow: dict[str, Any],
    candidate_keys: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Recover Branch._idList order from the installed Branch.Execute loop.

    Branch reserves itself, dispatches one ``_idList[m_index]`` action, then
    advances ``m_index``. After the last list item it resumes ActionBase.nextId.
    Consequently different sequence indexes have strict order, while Story
    files reached inside the same item remain unordered here.
    """
    route_type = tuple[
        str,
        tuple[tuple[Any, ...], ...],
        tuple[str, ...],
        str,
        str,
    ]
    sequences: list[dict[str, Any]] = []
    evidence_by_pair: dict[tuple[str, str], list[dict[str, Any]]] = (
        defaultdict(list)
    )
    for signature, routes in _native_event_story_paths(flow, candidate_keys).items():
        groups: dict[tuple[tuple[int, ...], int], dict[int, set[route_type]]] = (
            defaultdict(lambda: defaultdict(set))
        )
        labels: dict[tuple[tuple[int, ...], int], dict[int, str]] = defaultdict(dict)
        for route in routes:
            _story_key, path, _source_files, _event_detail, _downstream = route
            for index, step in enumerate(path):
                if index == 0 or path[index - 1][2] != "Branch":
                    continue
                match = re.fullmatch(r"Branch\.sequence\[(\d+)\]", step[1])
                if match:
                    ordinal = int(match.group(1))
                    label = step[1]
                elif step[1] == "ActionBase.nextId":
                    ordinal = 1_000_000_000
                    label = "ActionBase.nextId (after sequence)"
                else:
                    continue
                branch_local_id = int(path[index - 1][0])
                prefix = tuple(int(value[0]) for value in path[:index])
                group_key = (prefix, branch_local_id)
                groups[group_key][ordinal].add(route)
                labels[group_key][ordinal] = label

        for (prefix, branch_local_id), routes_by_ordinal in groups.items():
            sequence_ordinals = sorted(
                ordinal for ordinal in routes_by_ordinal if ordinal < 1_000_000_000
            )
            if not sequence_ordinals or len(routes_by_ordinal) < 2:
                continue
            ordered_ordinals = sorted(routes_by_ordinal)
            arm_rows: list[dict[str, Any]] = []
            for ordinal in ordered_ordinals:
                arm_routes = routes_by_ordinal[ordinal]
                arm_rows.append({
                    "edge": labels[(prefix, branch_local_id)][ordinal],
                    "sequenceIndex": (
                        ordinal if ordinal < 1_000_000_000 else None
                    ),
                    "storyKeys": sorted(
                        {route[0] for route in arm_routes}, key=natural_key
                    ),
                })
            all_routes = {
                route
                for ordinal in ordered_ordinals
                for route in routes_by_ordinal[ordinal]
            }
            source_files = sorted({
                source_file
                for route in all_routes
                for source_file in route[2]
                if source_file
            }, key=natural_key)
            sequence_row = {
                "kind": "orderedSequence",
                "levelId": signature[0],
                "scriptId": signature[1],
                "headerLocalId": signature[2],
                "eventName": signature[3],
                "branchLocalId": branch_local_id,
                "branchPath": list(prefix),
                "arms": arm_rows,
                "sourceFiles": source_files,
                "runtimeMappingId": BRANCH_SEQUENCE_RUNTIME["mappingId"],
                "gameAssemblySha256": BRANCH_SEQUENCE_GAME_ASSEMBLY_SHA256,
                "nativeConsumers": [{
                    "method": "Beyond.Gameplay.Actions.Branch.Execute",
                    "address": "0x18764d990",
                    "contract": (
                        "dispatches _idList[m_index], reserves Branch for the next "
                        "item, then resumes ActionBase.nextId after the list"
                    ),
                }],
            }
            sequences.append(sequence_row)
            for source_position, source_ordinal in enumerate(ordered_ordinals):
                for target_ordinal in ordered_ordinals[source_position + 1:]:
                    for source_route in routes_by_ordinal[source_ordinal]:
                        for target_route in routes_by_ordinal[target_ordinal]:
                            if source_route[0] == target_route[0]:
                                continue
                            evidence_by_pair[(source_route[0], target_route[0])].append({
                                "levelId": signature[0],
                                "scriptId": signature[1],
                                "headerLocalId": signature[2],
                                "eventName": signature[3],
                                "branchLocalId": branch_local_id,
                                "sourceSequenceEdge": labels[
                                    (prefix, branch_local_id)
                                ][source_ordinal],
                                "targetSequenceEdge": labels[
                                    (prefix, branch_local_id)
                                ][target_ordinal],
                                "sourceFiles": source_files,
                                "runtimeMappingId": BRANCH_SEQUENCE_RUNTIME[
                                    "mappingId"
                                ],
                                "gameAssemblySha256": BRANCH_SEQUENCE_GAME_ASSEMBLY_SHA256,
                                "nativeConsumers": sequence_row["nativeConsumers"],
                            })

    conflicts = {
        pair for pair in evidence_by_pair if (pair[1], pair[0]) in evidence_by_pair
    }
    edges: list[dict[str, Any]] = []
    for pair, evidence_rows in sorted(
        evidence_by_pair.items(),
        key=lambda item: (natural_key(item[0][0]), natural_key(item[0][1])),
    ):
        if pair in conflicts:
            continue
        edges.append({
            "from": pair[0],
            "to": pair[1],
            "kind": "levelscriptNativeOrderedSequence",
            "tier": "strong",
            "source": (
                "exact serialized Branch._idList order + installed "
                "Branch.Execute iterator"
            ),
            "sourceFiles": sorted({
                source_file
                for evidence in evidence_rows
                for source_file in evidence["sourceFiles"]
            }, key=natural_key),
            "runtimeMappingId": BRANCH_SEQUENCE_RUNTIME["mappingId"],
            "gameAssemblySha256": BRANCH_SEQUENCE_GAME_ASSEMBLY_SHA256,
            "nativeConsumers": evidence_rows[0]["nativeConsumers"],
            "events": evidence_rows,
        })
    return edges, sequences


def _native_branch_kind(edge: str) -> str:
    if edge.startswith("Split.actions["):
        return "splitFanout"
    if edge in {"IfElseAction.trueAction", "IfElseAction.falseAction"}:
        return "ifElse"
    if edge.startswith("SwitchInt.case[") or edge == "SwitchInt.default":
        return "switch"
    if edge.startswith("SwitchString.case[") or edge == "SwitchString.default":
        return "switch"
    return ""


def _native_branch_runtime_mapping(
    branch_kind: str,
    arms: list[dict[str, Any]],
) -> dict[str, Any]:
    """Resolve a typed branch family to its installed-binary runtime mapping."""
    pair: tuple[int, int] | None = None
    if branch_kind == "splitFanout":
        pair = (0x0495, 0x09)
    elif branch_kind == "ifElse":
        pair = (0x00FF, 0x0B)
    elif branch_kind == "switch":
        edges = {
            safe_key(arm.get("edge"))
            for arm in arms
            if isinstance(arm, dict)
        }
        if edges and all(edge.startswith("SwitchInt.") for edge in edges):
            pair = (0x04BD, 0x0C)
        elif edges and all(edge.startswith("SwitchString.") for edge in edges):
            pair = (0x04BF, 0x0C)
    return dict(LEVELSCRIPT_NATIVE_CONTROL_RUNTIME_MAPPINGS.get(pair) or {})


def _serialized_native_control_arm_slots(
    action: dict[str, Any],
) -> list[dict[str, Any]]:
    """Project every configured arm from a decoded typed control action.

    This is deliberately family/schema driven.  Object ids and mission names
    never participate, and non-positive targets remain visible as inactive
    serialized slots instead of silently disappearing from the branch shape.
    """
    detail = action.get("controlDetail") or {}
    action_name = safe_key(action.get("actionName"))
    slots: list[dict[str, Any]] = []
    if action_name == "Split":
        slots.extend({
            "edge": f"Split.actions[{index}]",
            "entryLocalId": local_id,
            "serializedIndex": index,
        } for index, local_id in enumerate(detail.get("splitActionLocalIds") or []))
    elif action_name == "IfElseAction":
        slots.extend({
            "edge": edge,
            "entryLocalId": detail.get(field),
            "serializedField": field,
            "serializedFieldPresent": field in detail,
        } for field, edge in (
            ("trueActionLocalId", "IfElseAction.trueAction"),
            ("falseActionLocalId", "IfElseAction.falseAction"),
        ))
    elif action_name in {"SwitchInt", "SwitchString"}:
        prefix = "switch" if action_name == "SwitchInt" else "switchString"
        case_ids = detail.get(f"{prefix}CaseActionLocalIds") or []
        case_values = detail.get(f"{prefix}CaseValues") or []
        slots.extend({
            "edge": f"{action_name}.case[{index}]={case_value}",
            "entryLocalId": local_id,
            "serializedIndex": index,
            "caseValue": case_value,
        } for index, (case_value, local_id) in enumerate(zip(case_values, case_ids)))
        slots.append({
            "edge": f"{action_name}.default",
            "entryLocalId": detail.get(f"{prefix}DefaultActionLocalId"),
            "serializedField": f"{prefix}DefaultActionLocalId",
            "serializedFieldPresent": f"{prefix}DefaultActionLocalId" in detail,
        })
    return slots


def _compact_native_action(action: dict[str, Any]) -> dict[str, Any]:
    return {
        key: action[key]
        for key in (
            "localId",
            "actionName",
            "recordClass",
            "unionTag",
            "serializedMemberCount",
            "texts",
            "nextActionLocalId",
            "controlKind",
            "controlRuntimeMappingId",
        )
        if action.get(key) not in (None, "", [], {})
    }


def _native_serialized_branch_arm_projection(
    topology: dict[str, Any],
    action: dict[str, Any],
    playback_by_local: dict[int, set[str]] | None = None,
    control_predicates_by_local: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Project one serialized ``Branch._idList`` without inferring ownership.

    The projection is intentionally independent of mission names and filename
    order.  It follows only the decoded action adjacency and joins exact
    playback records supplied by ``build_levelscript_action_story_occurrences``.
    This makes it reusable for the complete original LevelScript corpus and
    keeps sibling arms visible even when no Story record is reachable from an
    arm. When an exact Story path supplies a decoded predicate, that predicate
    is attached to the nested control without promoting it to ownership/order.
    """
    playback_by_local = playback_by_local or {}
    control_predicates_by_local = control_predicates_by_local or {}
    branch_local_id = action.get("localId")
    detail = action.get("controlDetail") or {}
    serialized_refs = detail.get("branchSequenceActionLocalIds")
    if not isinstance(serialized_refs, list):
        serialized_refs = []
    action_by_local = {
        int(row.get("localId")): row
        for row in topology.get("actions") or []
        if isinstance(row, dict) and isinstance(row.get("localId"), int)
    }
    action_edges = [
        row for row in topology.get("edges") or []
        if isinstance(row, dict) and row.get("sourceKind") == "action"
    ]
    adjacency: dict[int, set[int]] = defaultdict(set)
    for edge in action_edges:
        source = edge.get("sourceLocalId")
        target = edge.get("targetActionLocalId")
        if isinstance(source, int) and isinstance(target, int):
            adjacency[source].add(target)
    active_edge_keys = {
        (
            edge.get("sourceLocalId"),
            safe_key(edge.get("relation")),
            edge.get("targetActionLocalId"),
        )
        for edge in action_edges
        if isinstance(edge.get("sourceLocalId"), int)
        and isinstance(edge.get("targetActionLocalId"), int)
    }
    terminal_edge_keys = {
        (
            edge.get("sourceLocalId"),
            safe_key(edge.get("relation")),
            edge.get("targetActionLocalId"),
        ): edge
        for edge in topology.get("runtimeTerminalTargets") or []
        if isinstance(edge, dict)
        and isinstance(edge.get("sourceLocalId"), int)
    }
    branch_targets = {
        (
            safe_key(edge.get("relation")),
            edge.get("targetActionLocalId"),
        ): edge
        for edge in action_edges
        if edge.get("sourceLocalId") == branch_local_id
    }
    branch_terminals = {
        (
            safe_key(edge.get("relation")),
            edge.get("targetActionLocalId"),
        ): edge
        for edge in topology.get("runtimeTerminalTargets") or []
        if isinstance(edge, dict)
        and edge.get("sourceKind") == "action"
        and edge.get("sourceLocalId") == branch_local_id
    }

    def target_status(
        source_local_id: Any,
        relation: str,
        target: Any,
    ) -> tuple[str, dict[str, Any] | None]:
        if not isinstance(target, int) or target <= 0:
            return "inactive_serialized_target", None
        key = (source_local_id, relation, target)
        if key in active_edge_keys and target in action_by_local:
            return "exact_active_action", None
        if key in terminal_edge_keys:
            return "missing_runtime_action_slot", terminal_edge_keys[key]
        return "unavailable_fail_closed", None

    def root_target_status(
        relation: str,
        target: Any,
    ) -> tuple[str, dict[str, Any] | None]:
        """Resolve a serialized root Branch edge against exact decoded links."""
        key = (relation, target)
        if key in branch_targets and target in action_by_local:
            return "exact_active_action", None
        if key in branch_terminals:
            return "missing_runtime_action_slot", branch_terminals[key]
        return target_status(branch_local_id, relation, target)

    def downstream(target: Any) -> set[int]:
        if not isinstance(target, int) or target <= 0:
            return set()
        pending = [target]
        reached: set[int] = set()
        while pending:
            current = pending.pop()
            if current in reached or current == branch_local_id:
                continue
            reached.add(current)
            pending.extend(adjacency.get(current) or [])
        return reached

    def reachable_semantics(local_ids: set[int]) -> tuple[list[str], list[str]]:
        """Return exact native names/classes for an arm's decoded action set.

        These labels come from the original action-map decoder.  They are a
        bounded semantic summary of the sibling arm, not an inferred Story
        relationship or a filename/order hint.
        """
        action_names = sorted({
            safe_key(action_by_local[local_id].get("actionName"))
            for local_id in local_ids
            if local_id in action_by_local
            and safe_key(action_by_local[local_id].get("actionName"))
        }, key=natural_key)
        record_classes = sorted({
            safe_key(action_by_local[local_id].get("recordClass"))
            for local_id in local_ids
            if local_id in action_by_local
            and safe_key(action_by_local[local_id].get("recordClass"))
        }, key=natural_key)
        return action_names, record_classes

    def playback_projection(local_ids: set[int]) -> tuple[list[int], list[str]]:
        playback_local_ids = sorted(
            local_id for local_id in local_ids if local_id in playback_by_local
        )
        playback_keys = sorted({
            story_key
            for local_id in playback_local_ids
            for story_key in playback_by_local.get(local_id) or set()
            if safe_key(story_key)
        }, key=natural_key)
        return playback_local_ids, playback_keys

    def nested_controls(local_ids: set[int]) -> list[dict[str, Any]]:
        """Expose typed controls nested inside one ordered Branch arm."""
        controls: list[dict[str, Any]] = []
        for local_id in sorted(local_ids):
            nested = action_by_local.get(local_id) or {}
            if safe_key(nested.get("actionName")) not in {
                "Split",
                "IfElseAction",
                "SwitchInt",
                "SwitchString",
            }:
                continue
            slots = _serialized_native_control_arm_slots(nested)
            if not slots:
                continue
            control = _compact_native_action(nested)
            detail = nested.get("controlDetail") or {}
            if isinstance(detail, dict):
                control["controlDetail"] = dict(detail)
            predicate = control_predicates_by_local.get(local_id)
            if isinstance(predicate, dict):
                control["predicate"] = dict(predicate)
            control["arms"] = []
            for slot in slots:
                relation = safe_key(slot.get("edge"))
                target = slot.get("entryLocalId")
                status, terminal = target_status(local_id, relation, target)
                reached = downstream(target)
                action_names, record_classes = reachable_semantics(reached)
                playback_local_ids, playback_keys = playback_projection(reached)
                nested_arm = dict(slot)
                nested_arm.update({
                    "targetStatus": status,
                    "reachableActionCount": len(reached),
                    "reachableActionNames": action_names,
                    "reachableRecordClasses": record_classes,
                    "playbackActionLocalIds": playback_local_ids,
                    "playbackStoryKeys": playback_keys,
                })
                if terminal:
                    nested_arm["runtimeTerminal"] = terminal
                control["arms"].append(nested_arm)
            control["serializedArmCount"] = len(control["arms"])
            control["playbackArmCount"] = sum(
                bool(nested_arm.get("playbackStoryKeys"))
                for nested_arm in control["arms"]
            )
            control["playbackStoryKeys"] = sorted({
                story_key
                for nested_arm in control["arms"]
                for story_key in nested_arm.get("playbackStoryKeys") or []
                if safe_key(story_key)
            }, key=natural_key)
            control["branchingStatus"] = (
                "multi_playback_arms"
                if control["playbackArmCount"] >= 2
                else "single_playback_arm"
                if control["playbackArmCount"] == 1
                else "no_playback"
            )
            controls.append(control)
        return controls

    arms: list[dict[str, Any]] = []
    for sequence_index, entry_local_id in enumerate(serialized_refs):
        relation = f"Branch.sequence[{sequence_index}]"
        status, terminal = root_target_status(relation, entry_local_id)
        reached = downstream(entry_local_id)
        reachable_action_names, reachable_record_classes = reachable_semantics(reached)
        playback_local_ids, playback_keys = playback_projection(reached)
        row: dict[str, Any] = {
            "edge": relation,
            "sequenceIndex": sequence_index,
            "entryLocalId": entry_local_id,
            "targetStatus": status,
            "reachableActionCount": len(reached),
            "reachableActionNames": reachable_action_names,
            "reachableRecordClasses": reachable_record_classes,
            "nestedControls": nested_controls(reached),
            "playbackActionLocalIds": playback_local_ids,
            "playbackStoryKeys": playback_keys,
        }
        if status == "exact_active_action" and entry_local_id in action_by_local:
            row["entryAction"] = _compact_native_action(
                action_by_local[entry_local_id]
            )
        if terminal:
            row["runtimeTerminal"] = terminal
        arms.append(row)

    exit_target = action.get("nextActionLocalId")
    exit_status, exit_terminal = root_target_status("ActionBase.nextId", exit_target)
    exit_row: dict[str, Any] = {
        "edge": "ActionBase.nextId (after sequence)",
        "entryLocalId": exit_target,
        "targetStatus": exit_status,
    }
    if exit_status == "exact_active_action" and exit_target in action_by_local:
        exit_row["entryAction"] = _compact_native_action(
            action_by_local[exit_target]
        )
    if exit_terminal:
        exit_row["runtimeTerminal"] = exit_terminal

    return {
        "branchLocalId": branch_local_id,
        "runtimeMappingId": safe_key(action.get("controlRuntimeMappingId")),
        "serializedArmCount": len(arms),
        "arms": arms,
        "exit": exit_row,
        "playbackArmCount": sum(
            bool(row.get("playbackStoryKeys")) for row in arms
        ),
        "playbackStoryKeys": sorted({
            story_key
            for row in arms
            for story_key in row.get("playbackStoryKeys") or []
        }, key=natural_key),
    }


def _full_native_branch_arm_context(
    mission: str,
    branches: list[dict[str, Any]],
    original_binary_contract: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Validate and attach the complete serialized shape of Story branches.

    Story paths anchor the branch to a mission card.  The original LevelScript
    then supplies *all* configured arms, including non-Story actions and
    inactive targets.  The installed binary mapping validates semantics; no
    extra Story ownership or chronology is inferred from sibling topology.
    """
    annotated: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    for source_branch in branches:
        branch = dict(source_branch)
        level_sources = []
        for source_file in branch.get("sourceFiles") or []:
            if "LevelScriptData" not in source_file:
                continue
            source_path = Path(source_file)
            if not source_path.is_absolute():
                source_path = ROOT / source_path
            if source_path.is_file():
                level_sources.append((source_file, source_path))
        # Synthetic/unit fixtures and old degraded inputs retain the existing
        # Story-only view.  Present original files are always validated.
        if not level_sources:
            annotated.append(branch)
            continue

        matches: list[tuple[str, Path, dict[str, Any], dict[str, Any]]] = []
        source_failures: list[dict[str, Any]] = []
        for source_file, source_path in level_sources:
            cache_key = source_path.resolve().as_posix()
            if cache_key not in _NATIVE_ACTION_TOPOLOGY_CACHE:
                try:
                    _NATIVE_ACTION_TOPOLOGY_CACHE[cache_key] = (
                        decode_levelscript_native_action_topology(
                            source_path.read_bytes()
                        )
                    )
                except OSError as error:
                    source_failures.append({
                        "sourceFile": source_file,
                        "error": type(error).__name__,
                    })
                    continue
            topology, topology_diagnostic = _NATIVE_ACTION_TOPOLOGY_CACHE[cache_key]
            if topology_diagnostic or not str(topology.get("status") or "").startswith(
                "exact_complete_action_map"
            ):
                source_failures.append({
                    "sourceFile": source_file,
                    "topologyStatus": topology.get("status"),
                    "topologyDiagnostic": topology_diagnostic,
                })
                continue
            for action in topology.get("actions") or []:
                if (
                    action.get("localId") == branch.get("branchLocalId")
                    and action.get("controlRuntimeMappingId")
                    == branch.get("nativeMappingId")
                ):
                    matches.append((source_file, source_path, topology, action))

        if len(matches) != 1:
            diagnostic = {
                "validator": "nativeBranchFullArmCoverage",
                "gate": "uniqueRuntimeMappedControlAction",
                "mission": mission,
                "branchLocalId": branch.get("branchLocalId"),
                "expected": {
                    "matchingActionCount": 1,
                    "nativeMappingId": branch.get("nativeMappingId"),
                },
                "actual": {
                    "matchingActionCount": len(matches),
                    "sourceFailures": source_failures[:8],
                },
                "sourcePaths": [row[0] for row in level_sources],
                "sourceSha256": {
                    source_file: hashlib.sha256(source_path.read_bytes()).hexdigest()
                    for source_file, source_path in level_sources
                },
            }
            diagnostics.append(diagnostic)
            branch["fullArmCoverageStatus"] = "unavailable_fail_closed"
            branch["fullArmValidatorDiagnostic"] = diagnostic
            annotated.append(branch)
            continue

        source_file, source_path, topology, action = matches[0]
        slots = _serialized_native_control_arm_slots(action)
        detail = action.get("controlDetail") or {}
        action_name = safe_key(action.get("actionName"))
        slot_schema_failures: list[dict[str, Any]] = []
        if action_name == "Split" and "splitActionLocalIds" not in detail:
            slot_schema_failures.append({
                "check": "splitActionListPresent",
                "expected": True,
                "actual": False,
            })
        if action_name == "IfElseAction":
            missing_fields = [
                field
                for field in ("trueActionLocalId", "falseActionLocalId")
                if field not in detail
            ]
            if missing_fields:
                slot_schema_failures.append({
                    "check": "ifElseArmFieldsPresent",
                    "expected": ["trueActionLocalId", "falseActionLocalId"],
                    "actualMissing": missing_fields,
                })
        if action_name in {"SwitchInt", "SwitchString"}:
            prefix = "switch" if action_name == "SwitchInt" else "switchString"
            case_values = detail.get(f"{prefix}CaseValues") or []
            case_ids = detail.get(f"{prefix}CaseActionLocalIds") or []
            if len(case_values) != len(case_ids):
                slot_schema_failures.append({
                    "check": "switchCaseValueTargetCardinality",
                    "expected": len(case_values),
                    "actual": len(case_ids),
                })
            default_field = f"{prefix}DefaultActionLocalId"
            if default_field not in detail:
                slot_schema_failures.append({
                    "check": "switchDefaultFieldPresent",
                    "expected": True,
                    "actual": False,
                })
        story_arms = {
            (safe_key(row.get("edge")), row.get("entryLocalId")): row
            for row in branch.get("arms") or []
        }
        edge_rows = {
            (safe_key(row.get("relation")), row.get("targetActionLocalId")): row
            for row in topology.get("edges") or []
            if row.get("sourceKind") == "action"
            and row.get("sourceLocalId") == branch.get("branchLocalId")
        }
        terminal_rows = {
            (safe_key(row.get("relation")), row.get("targetActionLocalId")): row
            for row in topology.get("runtimeTerminalTargets") or []
            if row.get("sourceKind") == "action"
            and row.get("sourceLocalId") == branch.get("branchLocalId")
        }
        action_by_id = {
            row.get("localId"): row
            for row in topology.get("actions") or []
            if isinstance(row.get("localId"), int)
        }
        adjacency: dict[int, set[int]] = defaultdict(set)
        for row in topology.get("edges") or []:
            if row.get("sourceKind") != "action":
                continue
            src = row.get("sourceLocalId")
            dst = row.get("targetActionLocalId")
            if isinstance(src, int) and isinstance(dst, int):
                adjacency[src].add(dst)

        positive_slots = [
            (safe_key(slot.get("edge")), slot.get("entryLocalId"))
            for slot in slots
            if isinstance(slot.get("entryLocalId"), int)
            and slot.get("entryLocalId") > 0
        ]
        reachable_by_slot: dict[tuple[str, Any], set[int]] = {}
        for slot_key in positive_slots:
            target = slot_key[1]
            pending = [target]
            reached: set[int] = set()
            while pending:
                current = pending.pop()
                if current in reached or current == branch.get("branchLocalId"):
                    continue
                reached.add(current)
                pending.extend(adjacency.get(current) or [])
            reachable_by_slot[slot_key] = reached
        reach_frequency = Counter(
            local_id
            for reached in reachable_by_slot.values()
            for local_id in reached
        )

        full_arms: list[dict[str, Any]] = []
        invalid_slots: list[dict[str, Any]] = []
        for slot in slots:
            edge = safe_key(slot.get("edge"))
            target = slot.get("entryLocalId")
            key = (edge, target)
            story_arm = story_arms.get(key) or {}
            full_arm = {**slot, "storyKeys": list(story_arm.get("storyKeys") or [])}
            if slot.get("serializedFieldPresent") is False:
                full_arm["targetStatus"] = "unavailable_fail_closed"
                invalid_slots.append({"edge": edge, "entryLocalId": target})
            elif not isinstance(target, int) or target <= 0:
                full_arm["targetStatus"] = "inactive_serialized_target"
            elif key in edge_rows and target in action_by_id:
                full_arm["targetStatus"] = "exact_active_action"
                full_arm["entryAction"] = _compact_native_action(action_by_id[target])
                exclusive = sorted(
                    local_id
                    for local_id in reachable_by_slot.get(key) or set()
                    if reach_frequency[local_id] == 1
                )
                full_arm["exclusiveActionCount"] = len(exclusive)
                full_arm["exclusiveActions"] = [
                    _compact_native_action(action_by_id[local_id])
                    for local_id in exclusive
                    if local_id in action_by_id
                ]
            elif key in terminal_rows:
                full_arm["targetStatus"] = "missing_runtime_action_slot"
                full_arm["runtimeTerminal"] = terminal_rows[key]
            else:
                full_arm["targetStatus"] = "unavailable_fail_closed"
                invalid_slots.append({"edge": edge, "entryLocalId": target})
            full_arms.append(full_arm)

        if not slots or slot_schema_failures or invalid_slots or not set(story_arms).issubset({
            (safe_key(row.get("edge")), row.get("entryLocalId"))
            for row in slots
        }):
            diagnostic = {
                "validator": "nativeBranchFullArmCoverage",
                "gate": "allStoryAndSerializedArmsMatchActiveActionMap",
                "mission": mission,
                "branchLocalId": branch.get("branchLocalId"),
                "expected": {
                    "storyArmKeys": [list(value) for value in sorted(story_arms)],
                    "invalidSerializedSlots": [],
                    "slotSchemaFailures": [],
                },
                "actual": {
                    "serializedArmKeys": [
                        [safe_key(row.get("edge")), row.get("entryLocalId")]
                        for row in slots
                    ],
                    "invalidSerializedSlots": invalid_slots,
                    "slotSchemaFailures": slot_schema_failures,
                },
                "sourcePaths": [source_file],
                "sourceSha256": {
                    source_file: hashlib.sha256(source_path.read_bytes()).hexdigest()
                },
            }
            diagnostics.append(diagnostic)
            branch["fullArmCoverageStatus"] = "unavailable_fail_closed"
            branch["fullArmValidatorDiagnostic"] = diagnostic
            annotated.append(branch)
            continue

        branch.update({
            "fullArmCoverageStatus": "exact_complete_active_action_map",
            "serializedArmCount": len(full_arms),
            "storyBearingArmCount": sum(bool(row["storyKeys"]) for row in full_arms),
            "nonStoryArmCount": sum(
                row["targetStatus"] == "exact_active_action" and not row["storyKeys"]
                for row in full_arms
            ),
            "inactiveTargetArmCount": sum(
                row["targetStatus"] == "inactive_serialized_target"
                for row in full_arms
            ),
            "runtimeTerminalArmCount": sum(
                row["targetStatus"] == "missing_runtime_action_slot"
                for row in full_arms
            ),
            "sharedDownstreamActionLocalIds": sorted(
                local_id for local_id, count in reach_frequency.items() if count > 1
            ),
            "fullArms": full_arms,
            "relatedOriginalFiles": _related_original_branch_files(
                mission,
                [source_file],
                original_binary_contract,
                level_relationship="complete_serialized_native_branch_arms",
                mission_relationship="mission_story_branch_anchor_context",
                binary_relationship="native_branch_runtime_semantics_authority",
            ),
            "fullArmEvidenceBoundary": (
                "Every configured slot comes from the original LevelScript's runtime-active "
                "action map and is checked against the installed native control mapping. "
                "Non-Story arms describe sibling action topology only; they do not add Story "
                "ownership, chronology, or mission membership."
            ),
        })
        annotated.append(branch)
    return annotated, diagnostics


def _native_control_branches_and_merges(
    flow: dict[str, Any],
    candidate_keys: set[str] | None,
    *,
    include_mission_state_dependencies: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Expose exact serialized native branch arms and observed convergence."""
    branches: list[dict[str, Any]] = []
    merges: list[dict[str, Any]] = []
    for signature, routes in _native_event_story_paths(
        flow,
        None,
        include_mission_state_dependencies=include_mission_state_dependencies,
    ).items():
        groups: dict[
            tuple[tuple[int, ...], str],
            dict[
                tuple[int, str],
                set[
                    tuple[
                        str,
                        tuple[tuple[Any, ...], ...],
                        tuple[str, ...],
                        str,
                        str,
                    ]
                ],
            ],
        ] = defaultdict(lambda: defaultdict(set))
        for story_key, path, source_file, event_detail, downstream in routes:
            for index, step in enumerate(path):
                branch_kind = _native_branch_kind(step[1])
                if not branch_kind:
                    continue
                prefix = tuple(path_step[0] for path_step in path[:index])
                groups[(prefix, branch_kind)][(step[0], step[1])].add(
                    (story_key, path, source_file, event_detail, downstream)
                )

        for (prefix, branch_kind), arms_by_key in groups.items():
            if len(arms_by_key) < 2:
                continue
            arm_rows: list[dict[str, Any]] = []
            all_routes: list[
                tuple[
                    str,
                    tuple[tuple[Any, ...], ...],
                    tuple[str, ...],
                    str,
                    str,
                ]
            ] = []
            for (entry_local_id, edge), arm_routes in sorted(
                arms_by_key.items(),
                key=lambda item: (natural_key(item[0][1]), item[0][0]),
            ):
                all_routes.extend(arm_routes)
                arm_rows.append({
                    "edge": edge,
                    "entryLocalId": entry_local_id,
                    "storyKeys": sorted({route[0] for route in arm_routes}, key=natural_key),
                })
            source_files = sorted({
                source_file
                for route in all_routes
                for source_file in route[2]
                if source_file
            }, key=natural_key)
            predicate_json_rows = {
                route[1][len(prefix) - 1][4]
                for route in all_routes
                if prefix
                and len(route[1]) >= len(prefix)
                and len(route[1][len(prefix) - 1]) > 4
                and route[1][len(prefix) - 1][4] not in {"", "{}"}
            }
            predicates = [json.loads(value) for value in sorted(predicate_json_rows)]
            event_details = [
                json.loads(value)
                for value in sorted({route[3] for route in all_routes})
            ]
            all_story_keys = sorted(
                {route[0] for route in all_routes},
                key=natural_key,
            )
            if candidate_keys is not None and not (
                set(all_story_keys) & candidate_keys
            ):
                continue
            runtime_mapping = _native_branch_runtime_mapping(
                branch_kind,
                arm_rows,
            )
            branch = {
                "kind": branch_kind,
                "levelId": signature[0],
                "scriptId": signature[1],
                "headerLocalId": signature[2],
                "eventName": signature[3],
                "branchLocalId": prefix[-1] if prefix else None,
                "branchPath": list(prefix),
                "arms": arm_rows,
                "sourceFiles": source_files,
            }
            if runtime_mapping:
                branch["runtimeSemantics"] = runtime_mapping.get("kind")
                branch["nativeMappingId"] = runtime_mapping.get("mappingId")
            if candidate_keys is not None:
                branch["missionStoryKeys"] = [
                    key for key in all_story_keys if key in candidate_keys
                ]
                branch["externalStoryKeys"] = [
                    key for key in all_story_keys if key not in candidate_keys
                ]
            if len(event_details) == 1:
                branch["eventDetail"] = event_details[0]
            elif event_details:
                branch["eventDetails"] = event_details
            if len(predicates) == 1:
                branch["predicate"] = predicates[0]
            elif predicates:
                branch["predicates"] = predicates
            branches.append(branch)

            common_ids: set[int] | None = None
            route_positions: list[dict[int, int]] = []
            branch_depth = len(prefix) + 1
            for _story_key, path, _source_files, _event_detail, _downstream in all_routes:
                positions = {
                    step[0]: index
                    for index, step in enumerate(path)
                    if index >= branch_depth
                }
                route_positions.append(positions)
                common_ids = set(positions) if common_ids is None else common_ids & set(positions)
            merge_paths: list[list[int]] = []
            if not common_ids:
                common_ids = None
                downstream_positions: list[dict[int, int]] = []
                for route in all_routes:
                    paths = json.loads(route[4])
                    positions: dict[int, int] = {}
                    for control_path in paths if isinstance(paths, list) else []:
                        if not isinstance(control_path, list):
                            continue
                        local_ids = [
                            step.get("localId")
                            for step in control_path
                            if isinstance(step, dict)
                            and isinstance(step.get("localId"), int)
                        ]
                        for index, local_id in enumerate(local_ids):
                            positions[local_id] = min(
                                positions.get(local_id, index),
                                index,
                            )
                    downstream_positions.append(positions)
                    common_ids = (
                        set(positions)
                        if common_ids is None
                        else common_ids & set(positions)
                    )
                if common_ids:
                    route_positions = downstream_positions
            if common_ids and route_positions:
                merge_local_id = min(
                    common_ids,
                    key=lambda local_id: (
                        max(positions[local_id] for positions in route_positions),
                        sum(positions[local_id] for positions in route_positions),
                        local_id,
                    ),
                )
                for route in all_routes:
                    paths = json.loads(route[4])
                    candidates = [
                        [
                            step.get("localId")
                            for step in control_path
                            if isinstance(step, dict)
                            and isinstance(step.get("localId"), int)
                        ]
                        for control_path in paths
                        if isinstance(control_path, list)
                        and any(
                            isinstance(step, dict)
                            and step.get("localId") == merge_local_id
                            for step in control_path
                        )
                    ]
                    if candidates:
                        merge_paths.append(min(candidates, key=len))
                merges.append({
                    **branch,
                    "mergeLocalId": merge_local_id,
                    "convergenceStatus": (
                        "exact_serialized_downstream_control_convergence"
                        if merge_paths
                        else "exact_observed_story_path_convergence"
                    ),
                    "mergePaths": merge_paths,
                    "downstreamStoryKeys": sorted(
                        {route[0] for route in all_routes}, key=natural_key
                    ),
                })

    sort_key = lambda row: (  # noqa: E731 - shared compact sort key
        natural_key(safe_key(row.get("levelId"))),
        natural_key(safe_key(row.get("scriptId"))),
        int(row.get("headerLocalId") or -1),
        tuple(row.get("branchPath") or []),
    )
    branches.sort(key=sort_key)
    merges.sort(key=sort_key)
    return branches, merges


def _native_mission_state_story_branches(
    mission: str,
    flow: dict[str, Any],
    candidate_keys: set[str],
    original_binary_contract: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Project complete exact mission-state alternatives without ordering them.

    Mission bundles group Story files nominally, while one serialized branch can
    choose files from several such groups.  Read every exact dependency row for
    the bundle, then retain only branches controlled by this mission's constant
    GetMissionState id and the current installed-build native mapping.
    """
    mapping_id = "gameassembly-2026-07-11-puregetter-mission-state"
    all_branches, _all_merges = _native_control_branches_and_merges(
        flow,
        None,
        include_mission_state_dependencies=True,
    )
    projected: list[dict[str, Any]] = []
    for branch in all_branches:
        predicate = branch.get("predicate") or {}
        compare = predicate.get("compareMissionState") or {}
        state_getter = (
            (predicate.get("sourceGetter") or {}).get("getMissionState") or {}
        )
        if not (
            branch.get("kind") == "ifElse"
            and predicate.get("status") == "exact_unique_getter"
            and predicate.get("getterName") == "CompareMissionState"
            and predicate.get("getterUnionTag") == "0x001f"
            and predicate.get("getterSerializedMemberCount") == 10
            and compare.get("nativeMappingId") == mapping_id
            and compare.get("pureGetterUnionTag") == "0x001f"
            and compare.get("serializedMemberCount") == 10
            and state_getter.get("nativeMappingId") == mapping_id
            and state_getter.get("pureGetterUnionTag") == "0x013a"
            and state_getter.get("serializedMemberCount") == 8
            and safe_key(state_getter.get("missionId")) == mission
        ):
            continue

        related_original_files = _related_original_branch_files(
            mission,
            list(branch.get("sourceFiles") or []),
            original_binary_contract,
            level_relationship="serialized_mission_state_story_branch",
            mission_relationship="mission_state_identity_context",
            binary_relationship="native_mission_state_branch_authority",
        )

        all_story_keys = sorted({
            safe_key(story_key)
            for arm in branch.get("arms") or []
            for story_key in arm.get("storyKeys") or []
            if safe_key(story_key)
        }, key=natural_key)
        projected.append({
            **branch,
            "missionStateId": mission,
            "missionStoryKeys": [
                key for key in all_story_keys if key in candidate_keys
            ],
            "externalStoryKeys": [
                key for key in all_story_keys if key not in candidate_keys
            ],
            "selectionSemantics": "alternative_client_story_selection",
            "ownership": False,
            "orderEvidence": False,
            "relatedOriginalFiles": related_original_files,
            "evidenceBoundary": (
                "The serialized LevelScript and installed native getter/comparer "
                "mapping prove client-side alternative selection from synchronized "
                "mission state. They do not prove Story ownership, quest identity, "
                "server transition timing, or order among alternative arms."
            ),
        })
    return projected


def _related_original_branch_files(
    mission: str,
    source_files: list[str],
    original_binary_contract: dict[str, Any] | None,
    *,
    level_relationship: str,
    mission_relationship: str,
    binary_relationship: str,
) -> list[dict[str, Any]]:
    """Attach hash-addressed original branch inputs without identity guessing."""
    related: list[dict[str, Any]] = []
    for source_file in source_files:
        source_path = ROOT / source_file
        if source_path.is_file():
            related.append({
                "kind": "original_level_script",
                "sourceFile": source_file,
                "sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
                "relationship": level_relationship,
            })
    for root_name in ("Persistent", "StreamingAssets"):
        mission_source = (
            ROOT / "export_full" / "structured" / root_name / "Data"
            / "Json" / "MissionRuntimeAsset" / f"{mission}.json"
        )
        if mission_source.is_file():
            related.append({
                "kind": "original_mission_runtime",
                "sourceFile": mission_source.relative_to(ROOT).as_posix(),
                "sha256": hashlib.sha256(mission_source.read_bytes()).hexdigest(),
                "relationship": mission_relationship,
            })
            break
    related.extend({
        **dict(row),
        "relationship": binary_relationship,
    } for row in (original_binary_contract or {}).get("relatedOriginalFiles") or [])
    return related


def _native_serialized_branch_inventory_not_requested() -> dict[str, Any]:
    return {
        "schema": NATIVE_SERIALIZED_BRANCH_INVENTORY_SCHEMA,
        "status": "not_requested",
        "summary": {
            "sourcePathCount": 0,
            "uniqueContentFileCount": 0,
            "duplicatePathCount": 0,
            "serializedBranchGroupCount": 0,
            "serializedBranchArmCount": 0,
            "playbackArmCount": 0,
            "multiPlaybackBranchCount": 0,
            "nestedControlCount": 0,
            "nestedPlaybackArmCount": 0,
            "nestedMultiPlaybackControlCount": 0,
            "controlPredicateConflictCount": 0,
            "validationFailureCount": 0,
        },
        "rows": [],
        "validationFailures": [],
        "evidenceBoundary": (
            "The complete original LevelScript corpus is scanned only for a full "
            "report build; a mission-filtered report keeps this inventory absent "
            "rather than presenting a partial census as complete."
        ),
    }


def _native_serialized_branch_inventory(
    *,
    original_binary_contract: dict[str, Any] | None = None,
    playback_occurrences_by_root: dict[Path, dict[str, list[dict]]] | None = None,
) -> dict[str, Any]:
    """Audit every serialized Branch in both original LevelScript roots.

    StreamingAssets and Persistent are treated as source copies, not separate
    gameplay instances. Branch groups are deduplicated by original file hash
    and local action id, while every source path remains attached for audit.
    Playback is joined only from the exact action-class decoder; arbitrary text
    identifiers never participate.
    """
    failures: list[dict[str, Any]] = []
    file_rows: list[dict[str, Any]] = []
    hash_to_paths: dict[str, set[str]] = defaultdict(set)
    path_to_hash: dict[str, str] = {}
    topology_by_hash: dict[str, tuple[dict, dict | None]] = {}
    for root in NATIVE_LEVELSCRIPT_ROOTS:
        root_rel = root.relative_to(ROOT).as_posix()
        if not root.is_dir():
            failures.append({
                "validator": "nativeSerializedBranchInventory",
                "gate": "sourceRootExists",
                "sourceRoot": root_rel,
                "expected": "directory",
                "actual": "missing",
            })
            continue
        for path in sorted(
            root.rglob("*.json"),
            key=lambda item: natural_key(item.relative_to(root).as_posix()),
        ):
            try:
                blob = path.read_bytes()
            except OSError as error:
                failures.append({
                    "validator": "nativeSerializedBranchInventory",
                    "gate": "sourceFileReadable",
                    "sourceFile": path.relative_to(ROOT).as_posix(),
                    "expected": "readable",
                    "actual": type(error).__name__,
                })
                continue
            source_file = path.relative_to(ROOT).as_posix()
            digest = hashlib.sha256(blob).hexdigest()
            resolved_key = path.resolve().as_posix().lower()
            path_to_hash[resolved_key] = digest
            hash_to_paths[digest].add(source_file)
            relative_parts = path.relative_to(root).parts
            file_rows.append({
                "path": path,
                "sourceFile": source_file,
                "sha256": digest,
                "levelId": relative_parts[0] if len(relative_parts) > 1 else "",
                "scriptId": path.stem,
            })
            if digest not in topology_by_hash:
                topology_by_hash[digest] = (
                    decode_levelscript_native_action_topology(blob)
                )

    playback_by_hash_local: dict[tuple[str, int], set[str]] = defaultdict(set)
    control_predicate_variants: dict[tuple[str, int], set[str]] = defaultdict(set)
    playback_join_misses = 0
    occurrence_roots = dict(playback_occurrences_by_root or {})
    for root in NATIVE_LEVELSCRIPT_ROOTS:
        if root not in occurrence_roots:
            occurrence_roots[root] = build_levelscript_action_story_occurrences(root)
        for story_key, occurrences in occurrence_roots[root].items():
            for occurrence in occurrences or []:
                if (
                    not isinstance(occurrence, dict)
                    or not safe_key(occurrence.get("recordClass")).startswith("play_")
                    or not isinstance(occurrence.get("localId"), int)
                ):
                    continue
                source_file = safe_key(occurrence.get("sourceFile"))
                if not source_file:
                    continue
                source_path = Path(source_file)
                if not source_path.is_absolute():
                    source_path = ROOT / source_path
                digest = path_to_hash.get(
                    source_path.resolve().as_posix().lower()
                )
                if not digest:
                    playback_join_misses += 1
                    continue
                playback_by_hash_local[
                    (digest, occurrence["localId"])
                ].add(safe_key(story_key))
                for owner in occurrence.get("nativeEventOwners") or []:
                    if not isinstance(owner, dict):
                        continue
                    for path_row in owner.get("path") or []:
                        if not isinstance(path_row, dict):
                            continue
                        local_id = path_row.get("localId")
                        predicate = path_row.get("branchPredicate")
                        if not isinstance(local_id, int) or not isinstance(predicate, dict):
                            continue
                        try:
                            control_predicate_variants[(digest, local_id)].add(
                                json.dumps(
                                    predicate,
                                    ensure_ascii=False,
                                    sort_keys=True,
                                    separators=(",", ":"),
                                )
                            )
                        except (TypeError, ValueError):
                            continue

    control_predicates_by_hash_local: dict[tuple[str, int], dict[str, Any]] = {}
    predicate_conflict_keys: list[tuple[str, int]] = []
    for key, variants in control_predicate_variants.items():
        if len(variants) != 1:
            predicate_conflict_keys.append(key)
            continue
        try:
            predicate = json.loads(next(iter(variants)))
        except (TypeError, ValueError, json.JSONDecodeError):
            predicate = None
        if isinstance(predicate, dict):
            control_predicates_by_hash_local[key] = predicate
    for digest, local_id in sorted(predicate_conflict_keys, key=lambda item: (natural_key(item[0]), item[1]))[:32]:
        failures.append({
            "validator": "nativeSerializedBranchInventory",
            "gate": "uniqueControlPredicate",
            "sourceFiles": sorted(hash_to_paths.get(digest) or [], key=natural_key),
            "sourceSha256": digest,
            "localId": local_id,
            "expected": "one exact branch predicate per action slot",
            "actual": {"variantCount": len(control_predicate_variants[(digest, local_id)])},
        })

    grouped: dict[tuple[str, int], dict[str, Any]] = {}
    reported_topology_failures: set[str] = set()
    for file_row in file_rows:
        digest = file_row["sha256"]
        topology, diagnostic = topology_by_hash[digest]
        status = safe_key(topology.get("status"))
        exact_empty_status = status in {
            "exact_empty_action_map",
            "exact_no_action_map",
        }
        if diagnostic or (
            not status.startswith("exact_complete_action_map")
            and not exact_empty_status
        ):
            if digest not in reported_topology_failures:
                failures.append({
                    "validator": "nativeSerializedBranchInventory",
                    "gate": "completeSerializedActionEventGraph",
                    "sourceFiles": sorted(
                        hash_to_paths[digest], key=natural_key
                    ),
                    "sourceSha256": digest,
                    "expected": "exact_complete_action_map",
                    "actual": {
                        "status": status,
                        "diagnostic": diagnostic,
                    },
                })
                reported_topology_failures.add(digest)
            continue
        for action in topology.get("actions") or []:
            if (
                not isinstance(action, dict)
                or safe_key(action.get("actionName")) != "Branch"
            ):
                continue
            branch_local_id = action.get("localId")
            if not isinstance(branch_local_id, int):
                failures.append({
                    "validator": "nativeSerializedBranchInventory",
                    "gate": "branchLocalIdIsInteger",
                    "sourceFiles": sorted(
                        hash_to_paths[digest], key=natural_key
                    ),
                    "sourceSha256": digest,
                    "expected": "integer",
                    "actual": branch_local_id,
                })
                continue
            key = (digest, branch_local_id)
            group = grouped.setdefault(key, {
                "sha256": digest,
                "sourceFiles": set(),
                "sourceContexts": set(),
                "topology": topology,
                "action": action,
            })
            group["sourceFiles"].add(file_row["sourceFile"])
            group["sourceContexts"].add((
                file_row["levelId"],
                file_row["scriptId"],
            ))

    rows: list[dict[str, Any]] = []
    for (_digest, _branch_local_id), group in sorted(
        grouped.items(),
        key=lambda item: (
            natural_key(item[1]["sha256"]),
            int(item[1]["action"].get("localId") or 0),
        ),
    ):
        topology = group["topology"]
        action = group["action"]
        digest = group["sha256"]
        playback_by_local = {
            local_id: set(story_keys)
            for (row_digest, local_id), story_keys
            in playback_by_hash_local.items()
            if row_digest == digest
        }
        control_predicates_by_local = {
            local_id: predicate
            for (row_digest, local_id), predicate
            in control_predicates_by_hash_local.items()
            if row_digest == digest
        }
        projection = _native_serialized_branch_arm_projection(
            topology,
            action,
            playback_by_local,
            control_predicates_by_local,
        )
        branch_local_id = action.get("localId")
        adjacency: dict[int, set[int]] = defaultdict(set)
        for edge in topology.get("edges") or []:
            if edge.get("sourceKind") != "action":
                continue
            source = edge.get("sourceLocalId")
            target = edge.get("targetActionLocalId")
            if isinstance(source, int) and isinstance(target, int):
                adjacency[source].add(target)
        event_roots: list[dict[str, Any]] = []
        for event in topology.get("eventRoots") or []:
            if (
                not isinstance(event, dict)
                or not isinstance(event.get("nextActionLocalId"), int)
            ):
                continue
            pending = [event["nextActionLocalId"]]
            visited: set[int] = set()
            reaches_branch = False
            while pending:
                current = pending.pop()
                if current in visited:
                    continue
                visited.add(current)
                if current == branch_local_id:
                    reaches_branch = True
                    break
                pending.extend(adjacency.get(current) or [])
            if reaches_branch:
                event_roots.append({
                    key: event[key]
                    for key in (
                        "localId",
                        "headerName",
                        "nextActionLocalId",
                        "priority",
                        "triggerActiveDuring",
                        "filterMode",
                        "filterMask",
                        "filterLevel",
                        "runtimeHeaderSlotMappingId",
                    )
                    if event.get(key) not in (None, "", [], {})
                })
        source_files = sorted(group["sourceFiles"], key=natural_key)
        context_values = sorted(
            group["sourceContexts"],
            key=lambda value: (
                natural_key(value[0]),
                natural_key(value[1]),
            ),
        )
        rows.append({
            "kind": "serializedBranchInventory",
            "status": safe_key(topology.get("status")),
            "levelId": next(
                (value[0] for value in context_values if value[0]),
                "",
            ),
            "scriptId": next(
                (value[1] for value in context_values if value[1]),
                "",
            ),
            "sourceContexts": [
                {"levelId": level_id, "scriptId": script_id}
                for level_id, script_id in context_values
            ],
            "sourceFiles": source_files,
            "sha256": digest,
            "branchLocalId": branch_local_id,
            "actionName": safe_key(action.get("actionName")),
            "runtimeMappingId": safe_key(
                action.get("controlRuntimeMappingId")
            ),
            "serializedArmCount": projection["serializedArmCount"],
            "arms": projection["arms"],
            "exit": projection["exit"],
            "eventRoots": event_roots,
            "playbackArmCount": projection["playbackArmCount"],
            "playbackStoryKeys": projection["playbackStoryKeys"],
            "relatedOriginalFiles": _related_original_branch_files(
                "",
                source_files,
                original_binary_contract,
                level_relationship="serialized_branch_inventory_source",
                mission_relationship="serialized_branch_inventory_no_mission_owner",
                binary_relationship="native_branch_runtime_semantics_authority",
            ),
            "ownership": False,
            "orderEvidence": False,
            "evidenceBoundary": (
                "This row is a corpus-wide serialized Branch reachability "
                "context. The original LevelScript action map and exact "
                "playback action-class join identify reachable Story records, "
                "but do not prove mission ownership, activation, arm "
                "exclusivity, or Story file order."
            ),
        })

    summary = {
        "sourcePathCount": len(file_rows),
        "uniqueContentFileCount": len(hash_to_paths),
        "duplicatePathCount": len(file_rows) - len(hash_to_paths),
        "serializedBranchGroupCount": len(rows),
        "serializedBranchArmCount": sum(
            int(row.get("serializedArmCount") or 0) for row in rows
        ),
        "playbackArmCount": sum(
            int(row.get("playbackArmCount") or 0) for row in rows
        ),
        "multiPlaybackBranchCount": sum(
            int(row.get("playbackArmCount") or 0) >= 2 for row in rows
        ),
        "nestedControlCount": sum(
            len(arm.get("nestedControls") or [])
            for row in rows
            for arm in row.get("arms") or []
        ),
        "nestedPlaybackArmCount": sum(
            int(control.get("playbackArmCount") or 0)
            for row in rows
            for arm in row.get("arms") or []
            for control in arm.get("nestedControls") or []
        ),
        "nestedMultiPlaybackControlCount": sum(
            int(control.get("playbackArmCount") or 0) >= 2
            for row in rows
            for arm in row.get("arms") or []
            for control in arm.get("nestedControls") or []
        ),
        "uniquePlaybackStoryKeyCount": len({
            story_key
            for row in rows
            for story_key in row.get("playbackStoryKeys") or []
        }),
        "playbackOccurrenceJoinMissCount": playback_join_misses,
        "controlPredicateConflictCount": len(predicate_conflict_keys),
        "validationFailureCount": len(failures),
    }
    return {
        "schema": NATIVE_SERIALIZED_BRANCH_INVENTORY_SCHEMA,
        "status": (
            "validated_complete_corpus"
            if not failures
            else "unavailable_fail_closed"
        ),
        "sourceRoots": [
            root.relative_to(ROOT).as_posix()
            for root in NATIVE_LEVELSCRIPT_ROOTS
        ],
        "summary": summary,
        "rows": rows,
        "validationFailures": failures[:32],
        "relatedOriginalFiles": [
            dict(row)
            for row in (
                (original_binary_contract or {}).get("relatedOriginalFiles")
                or []
            )
        ],
        "evidenceBoundary": (
            "The census scans both original LevelScript roots, hashes every "
            "file, deduplicates identical source copies, and joins only exact "
            "playback action records. It remains context-only: no inventory "
            "row creates mission ownership or Story order."
        ),
    }


def _attach_cross_boundary_native_branch_context(
    mission: str,
    branches: list[dict[str, Any]],
    original_binary_contract: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Annotate full native branch groups that cross nominal mission grouping."""
    parallel_names = _parallel_action_names(original_binary_contract)
    annotated: list[dict[str, Any]] = []
    for source_branch in branches:
        branch = dict(source_branch)
        external_story_keys = list(branch.get("externalStoryKeys") or [])
        if not external_story_keys:
            annotated.append(branch)
            continue
        runtime_semantics = safe_key(branch.get("runtimeSemantics"))
        is_parallel = (
            branch.get("kind") == "splitFanout"
            and runtime_semantics == "parallel_fanout"
            and "Split" in parallel_names
        )
        branch.update({
            "crossBoundary": True,
            "ownership": False,
            "orderEvidence": False,
            "branchSemantics": (
                "binary_validated_parallel_story_fanout"
                if is_parallel
                else "binary_mapped_conditional_story_alternatives"
            ),
            "relatedOriginalFiles": _related_original_branch_files(
                mission,
                list(branch.get("sourceFiles") or []),
                original_binary_contract,
                level_relationship="serialized_cross_boundary_story_branch",
                mission_relationship="mission_candidate_anchor_context",
                binary_relationship="native_cross_boundary_branch_authority",
            ),
            "evidenceBoundary": (
                "The exact serialized paths and installed Split scheduler prove "
                "Story-bearing sibling fan-out from one event. Nominal mission "
                "grouping does not prove ownership, and sibling slots are not "
                "chronological order."
                if is_parallel
                else
                "The exact serialized cases and installed native control mapping "
                "prove alternative Story-bearing arms from one event. Nominal "
                "mission grouping does not prove ownership or order among arms."
            ),
        })
        annotated.append(branch)
    return annotated


def build_mission_partial_order(
    mission: str,
    candidate_kinds: dict[str, str],
    mission_payload: dict[str, Any] | None,
    dialog_payloads: list[tuple[str, dict[str, Any]]] | None = None,
    exact_playback_source_keys: set[str] | None = None,
    exact_levelscript_playback_context_keys: set[str] | None = None,
    exact_native_control_path_context_keys: set[str] | None = None,
    dialog_tree_narrative_occurrences: list[dict[str, Any]] | None = None,
    dialog_tree_open_ui_occurrences: list[dict[str, Any]] | None = None,
    reading_popup_rows: dict[str, Any] | None = None,
    reading_popup_source: str = "",
    reading_popup_sha256: str = "",
    quest_succeed_lifecycle_contract: dict[str, Any] | None = None,
    extra_thread_scheduler_contract: dict[str, Any] | None = None,
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
    if exact_native_control_path_context_keys is None:
        candidate_kinds, native_context_scene_keys = (
            _expand_native_control_path_candidates(flow, candidate_kinds)
        )
    else:
        candidate_kinds = dict(candidate_kinds)
        native_context_scene_keys = set(
            exact_native_control_path_context_keys
        )
    candidate_keys = set(candidate_kinds)
    exact_playback_source_keys = exact_playback_source_keys or set()
    exact_levelscript_playback_context_keys = (
        exact_levelscript_playback_context_keys or set()
    )
    graph_node_kinds = {
        safe_key(node.get("key")): safe_key(node.get("kind"))
        for node in scene_graph.get("nodes") or []
        if isinstance(node, dict) and safe_key(node.get("key"))
    }

    direct_edges: list[dict[str, Any]] = []
    unresolved_nodes: dict[str, set[str]] = defaultdict(set)
    definition_only_nodes: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: {
            "incidentEdgeKinds": set(),
            "recordClasses": set(),
            "sourceFiles": set(),
            "levelIds": set(),
        }
    )
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
        for endpoint, key in (("from", src), ("to", dst)):
            if key in candidate_keys or not key:
                continue
            if graph_node_kinds.get(key) in SOURCE_STORY_NODE_KINDS:
                endpoint_classes = {
                    safe_key(value)
                    for value in source_edge.get(
                        f"{endpoint}ActionClasses"
                    ) or []
                    if safe_key(value)
                }
                if (
                    kind == "levelscriptSceneChain"
                    and endpoint_classes
                    and endpoint_classes
                    <= DEFINITION_ONLY_SOURCE_RECORD_CLASSES
                    and key not in exact_playback_source_keys
                ):
                    definition_only_nodes[key][
                        "incidentEdgeKinds"
                    ].add(kind)
                    definition_only_nodes[key][
                        "recordClasses"
                    ].update(endpoint_classes)
                    definition_only_nodes[key]["sourceFiles"].update(
                        safe_key(value)
                        for value in source_edge.get("sourceFiles") or []
                        if safe_key(value)
                    )
                    definition_only_nodes[key]["levelIds"].update(
                        safe_key(value)
                        for value in source_edge.get("levelIds") or []
                        if safe_key(value)
                    )
                else:
                    unresolved_nodes[key].add(kind)

    for key in unresolved_nodes:
        definition_only_nodes.pop(key, None)

    direct_edges.extend(_native_control_path_story_edges(
        flow,
        candidate_keys,
        extra_thread_scheduler_contract,
    ))
    native_ordered_sequence_edges, native_ordered_sequences = (
        _native_ordered_branch_sequences(flow, candidate_keys)
    )
    direct_edges.extend(native_ordered_sequence_edges)
    direct_edges.extend(_quest_state_action_path_story_edges(flow, candidate_keys))
    direct_edges.extend(_spawner_wave_part_killed_story_edges(flow, candidate_keys))
    direct_edges.extend(
        _spawner_wave_group_part_killed_story_edges(flow, candidate_keys)
    )
    direct_edges.extend(
        _dialog_tree_cross_story_trunk_edges(
            flow,
            candidate_keys,
            dialog_payloads,
        )
    )
    (
        dialog_tree_conditional_edges,
        dialog_tree_conditional_warnings,
    ) = _dialog_tree_cross_story_conditional_edges(
        mission,
        flow,
        candidate_keys,
        dialog_payloads,
    )
    direct_edges.extend(dialog_tree_conditional_edges)
    mission_source = safe_key(
        (((timeline.get("metadata") or {}).get("source") or {}).get("file"))
    )
    lifecycle_edges, lifecycle_warnings = _quest_succeed_lifecycle_story_edges(
        flow,
        candidate_keys,
        quest_succeed_lifecycle_contract,
        mission_source,
    )
    lifecycle_definition_rows = _quest_lifecycle_definition_rows(
        flow,
        candidate_keys,
        quest_succeed_lifecycle_contract,
        mission_source,
    )
    existing_strong_pairs = {
        (safe_key(edge.get("from")), safe_key(edge.get("to")))
        for edge in direct_edges
        if safe_key(edge.get("tier")) == "strong"
    }
    admitted_lifecycle_edges: list[dict[str, Any]] = []
    for edge in lifecycle_edges:
        reverse = (edge["to"], edge["from"])
        if reverse in existing_strong_pairs:
            lifecycle_warnings.append({
                "validator": "questSucceedLifecycle",
                "check": "noReverseStrongOrderConflict",
                "mission": mission,
                "expected": [],
                "actual": [edge["from"], edge["to"]],
                "sourcePaths": edge.get("sourceFiles") or [],
            })
            continue
        admitted_lifecycle_edges.append(edge)
        existing_strong_pairs.add((edge["from"], edge["to"]))
    direct_edges.extend(admitted_lifecycle_edges)
    narrative_containments, narrative_containment_warnings = (
        _dialog_tree_narrative_containments(
            mission,
            flow,
            candidate_keys,
            dialog_tree_narrative_occurrences,
        )
    )
    open_ui_containments, open_ui_containment_warnings = (
        _dialog_tree_open_ui_containments(
            mission,
            candidate_keys,
            dialog_tree_open_ui_occurrences,
            reading_popup_rows,
            reading_popup_source=reading_popup_source,
            reading_popup_sha256=reading_popup_sha256,
        )
    )
    all_containments = [*narrative_containments, *open_ui_containments]
    all_containments.sort(key=lambda row: (
        natural_key(row["parent"]),
        natural_key(row["child"]),
    ))
    embedded_scene_keys = {
        row["child"] for row in all_containments
    }
    _demote_reciprocal_quest_projections(direct_edges)

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
        elif scene_key in embedded_scene_keys:
            status = "embedded"
        else:
            status = "isolated"
            isolated.append(scene_key)
            unknown.append(scene_key)
        nodes.append({
            "key": scene_key,
            "kind": candidate_kinds.get(scene_key) or "unknown",
            "membership": (
                "exactNativeControlPathContext"
                if scene_key in native_context_scene_keys
                else (
                    "exactLevelScriptPlaybackContext"
                    if scene_key
                    in exact_levelscript_playback_context_keys
                    else "index"
                )
            ),
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
    typed_story_selector_groups = _typed_story_selector_groups(flow, candidate_keys)
    native_control_branches, native_control_merges = _native_control_branches_and_merges(
        flow, candidate_keys
    )
    (
        native_control_branches,
        native_branch_arm_coverage_diagnostics,
    ) = _full_native_branch_arm_context(
        mission,
        native_control_branches,
        extra_thread_scheduler_contract,
    )
    native_control_branches = _attach_cross_boundary_native_branch_context(
        mission,
        native_control_branches,
        extra_thread_scheduler_contract,
    )
    native_mission_state_branches = _native_mission_state_story_branches(
        mission,
        flow,
        candidate_keys,
        extra_thread_scheduler_contract,
    )
    native_related_action_topologies = _native_related_action_topologies(
        flow,
        candidate_keys,
        mission=mission,
        original_binary_contract=extra_thread_scheduler_contract,
    )
    native_named_predicates = sum(
        1
        for row in native_control_branches
        if safe_key((row.get("predicate") or {}).get("getterName"))
    )
    native_inline_predicates = sum(
        1
        for row in native_control_branches
        if safe_key((row.get("predicate") or {}).get("status")) == "exact_inline_param"
    )
    native_semantic_predicates = sum(
        1
        for row in native_control_branches
        if row.get("kind") != "splitFanout"
        and (
            safe_key((row.get("predicate") or {}).get("status"))
            == "exact_inline_param"
            or bool((row.get("predicate") or {}).get("detail"))
            or bool((row.get("predicate") or {}).get("compareMissionState"))
        )
    )
    native_class_only_predicates = sum(
        1
        for row in native_control_branches
        if row.get("kind") != "splitFanout"
        and safe_key((row.get("predicate") or {}).get("getterName"))
        and not (row.get("predicate") or {}).get("detail")
        and not (row.get("predicate") or {}).get("compareMissionState")
    )
    native_unresolved_predicates = sum(
        1
        for row in native_control_branches
        if row.get("kind") != "splitFanout"
        and not safe_key((row.get("predicate") or {}).get("getterName"))
        and safe_key((row.get("predicate") or {}).get("status")) != "exact_inline_param"
    )
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
    single_option_no_explicit_route_groups = [
        row
        for row in no_explicit_route_groups
        if len(row.get("options") or []) == 1
    ]
    branching_no_explicit_route_groups = [
        row
        for row in no_explicit_route_groups
        if len(row.get("options") or []) > 1
    ]
    closed_excluded_dialog_line_options = [
        row
        for row in excluded_dialog_line_options
        if row.get("exclusionReason")
        in {
            "sharedOrDefaultCandidates",
            "authoredNonLineOptionOutcomes",
            "authoredOutcomesWithDefinitionOnlyRows",
            "branchLinesForDefinitionOnlyRows",
            "closedDialogTreeOptionLayout",
            "closedTimelineOptionLayout",
            "unregisteredSceneWithoutAuthoredOptionConsumer",
        }
        or (
            row.get("exclusionReason") == "inferredOrUnsupportedRisk"
            and safe_key((row.get("riskEvidence") or {}).get("code"))
            == "cosmeticChoice"
        )
    ]
    closed_excluded_ids = {
        (safe_key(row.get("storyKey")), row.get("group"))
        for row in closed_excluded_dialog_line_options
    }
    actionable_excluded_dialog_line_options = [
        row
        for row in excluded_dialog_line_options
        if (safe_key(row.get("storyKey")), row.get("group"))
        not in closed_excluded_ids
    ]
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
    branching_no_explicit_route_option_count = sum(
        len(row.get("options") or [])
        for row in branching_no_explicit_route_groups
    )
    cycles = [component for component in components if component["cyclic"]]
    tier_counts = Counter(edge["tier"] for edge in direct_edges)
    kind_counts = Counter(edge["kind"] for edge in direct_edges)
    native_transition_edges = [
        edge
        for edge in direct_edges
        if edge.get("kind") == "levelscriptNativeControlPath"
    ]
    native_transition_kind_counts = Counter(
        kind
        for edge in native_transition_edges
        for kind in edge.get("transitionKinds") or []
    )
    native_transition_steps = [
        step
        for edge in native_transition_edges
        for event in edge.get("events") or []
        if isinstance(event, dict)
        for step in event.get("transitionSteps") or []
        if isinstance(step, dict)
    ]
    native_transition_named_endpoints = sum(
        bool(step.get(field))
        for step in native_transition_steps
        for field in ("sourceActionName", "targetActionName")
    )
    warnings: list[str] = []
    if not mission_payload:
        warnings.append("missingMissionBundle")
    if cycles:
        warnings.append("sourceEdgeCycle")

    return {
        "mission": mission,
        "summary": {
            "sceneCount": len(candidate_keys),
            "nativeControlPathContextSceneCount": len(native_context_scene_keys),
            "exactLevelScriptPlaybackContextSceneCount":
                len(exact_levelscript_playback_context_keys),
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
            "definitionOnlySourceNodeCount": len(definition_only_nodes),
            "embeddedContainmentCount": len(all_containments),
            "embeddedSceneCount": len(embedded_scene_keys),
            "totalScenePairs": total_pairs,
            "comparableScenePairs": comparable_pairs,
            "unorderedScenePairs": total_pairs - comparable_pairs,
            "cyclicInternalPairs": cyclic_internal_pairs,
            "sceneGraphOptionGroupCount": len(scene_graph_option_branches),
            "nativeControlBranchCount": len(native_control_branches),
            "nativeControlFullArmBranchCount": sum(
                row.get("fullArmCoverageStatus")
                == "exact_complete_active_action_map"
                for row in native_control_branches
            ),
            "nativeControlSerializedArmCount": sum(
                int(row.get("serializedArmCount") or 0)
                for row in native_control_branches
            ),
            "nativeControlNonStoryArmCount": sum(
                int(row.get("nonStoryArmCount") or 0)
                for row in native_control_branches
            ),
            "nativeControlInactiveTargetArmCount": sum(
                int(row.get("inactiveTargetArmCount") or 0)
                for row in native_control_branches
            ),
            "nativeControlRuntimeTerminalArmCount": sum(
                int(row.get("runtimeTerminalArmCount") or 0)
                for row in native_control_branches
            ),
            "nativeControlFullArmValidationFailureCount": len(
                native_branch_arm_coverage_diagnostics
            ),
            "nativeControlCrossBoundaryBranchCount": sum(
                bool(row.get("crossBoundary"))
                for row in native_control_branches
            ),
            "nativeControlCrossBoundaryExternalStoryCount": len({
                key
                for row in native_control_branches
                for key in row.get("externalStoryKeys") or []
            }),
            "nativeMissionStateBranchCount": len(native_mission_state_branches),
            "nativeMissionStateBranchExternalStoryCount": len({
                key
                for row in native_mission_state_branches
                for key in row.get("externalStoryKeys") or []
            }),
            "nativeControlMergeCount": len(native_control_merges),
            "nativeControlPathTransitionEdgeCount": len(
                native_transition_edges
            ),
            "nativeControlPathBranchingTransitionEdgeCount": sum(
                bool(edge.get("branchingTransition"))
                for edge in native_transition_edges
            ),
            "nativeControlPathTransitionKinds": dict(
                sorted(native_transition_kind_counts.items())
            ),
            "nativeControlPathTransitionStepCount": len(
                native_transition_steps
            ),
            "nativeControlPathTransitionActionEndpointCount": (
                len(native_transition_steps) * 2
            ),
            "nativeControlPathNamedActionEndpointCount": (
                native_transition_named_endpoints
            ),
            "nativeControlPathUnresolvedActionEndpointCount": (
                len(native_transition_steps) * 2
                - native_transition_named_endpoints
            ),
            "nativeOrderedSequenceCount": len(native_ordered_sequences),
            "nativeOrderedSequenceEdgeCount": len(native_ordered_sequence_edges),
            "nativeOrderedSequenceContextCount": sum(
                len(row.get("orderedSequenceContexts") or [])
                for row in native_related_action_topologies
            ),
            "questSucceedLifecycleEdgeCount": len(admitted_lifecycle_edges),
            "questSucceedLifecycleQuestCount": len({
                quest_id
                for edge in admitted_lifecycle_edges
                for quest_id in edge.get("questIds") or []
            }),
            "questStartActionDefinitionCount": len(lifecycle_definition_rows),
            "questStartActionDefinitionStoryCount": len({
                row["storyKey"] for row in lifecycle_definition_rows
            }),
            "questStartActionDefinitionQuestCount": len({
                row["questId"] for row in lifecycle_definition_rows
            }),
            "nativeRelatedActionTopologyCount": len(
                native_related_action_topologies
            ),
            "nativeNamedPredicateCount": native_named_predicates,
            "nativeInlinePredicateCount": native_inline_predicates,
            "nativeSemanticPredicateCount": native_semantic_predicates,
            "nativeClassOnlyPredicateCount": native_class_only_predicates,
            "nativeUnresolvedPredicateCount": native_unresolved_predicates,
            "questForkCount": len(quest_branches),
            "questMergeCount": len(quest_merges),
            "typedStorySelectorGroupCount": len(typed_story_selector_groups),
            "dialogLineOptionGroupCount": len(dialog_line_options),
            "dialogLineOptionRouteCount": dialog_line_route_count,
            "dialogLineOptionLineCount": dialog_line_count,
            "excludedDialogLineOptionGroupCount": len(excluded_dialog_line_options),
            "excludedDialogLineOptionCount": excluded_dialog_line_option_count,
            "actionableExcludedDialogLineOptionGroupCount":
                len(actionable_excluded_dialog_line_options),
            "closedExcludedDialogLineOptionGroupCount":
                len(closed_excluded_dialog_line_options),
            "noExplicitRouteGroupCount": len(no_explicit_route_groups),
            "noExplicitRouteOptionCount": no_explicit_route_option_count,
            "branchingNoExplicitRouteGroupCount":
                len(branching_no_explicit_route_groups),
            "branchingNoExplicitRouteOptionCount":
                branching_no_explicit_route_option_count,
            "singleOptionNoExplicitRouteGroupCount":
                len(single_option_no_explicit_route_groups),
            "dialogLineOptionProvenance": dict(sorted(dialog_line_provenance_counts.items())),
            "edgeKinds": dict(sorted(kind_counts.items())),
        },
        "nodes": nodes,
        "components": components,
        "componentEdges": component_edges,
        "reducedComponentEdges": reduced_component_edges,
        "topologicalLayers": layers,
        "directEdges": direct_edges,
        "questLifecycleDefinitions": lifecycle_definition_rows,
        "containments": all_containments,
        "cycles": cycles,
        "branches": {
            "sceneGraphOptions": scene_graph_option_branches,
            "nativeControlBranches": native_control_branches,
            "nativeMissionStateBranches": native_mission_state_branches,
            "nativeControlMerges": native_control_merges,
            "nativeOrderedSequences": native_ordered_sequences,
            "nativeRelatedActionTopologies": native_related_action_topologies,
            "dialogLineOptions": dialog_line_options,
            "excludedDialogLineOptions": excluded_dialog_line_options,
            "actionableExcludedDialogLineOptions":
                actionable_excluded_dialog_line_options,
            "closedExcludedDialogLineOptions":
                closed_excluded_dialog_line_options,
            "noExplicitRouteGroups": no_explicit_route_groups,
            "branchingNoExplicitRouteGroups":
                branching_no_explicit_route_groups,
            "singleOptionNoExplicitRouteGroups":
                single_option_no_explicit_route_groups,
            "questForks": quest_branches,
            "questMerges": quest_merges,
            "typedStorySelectorGroups": typed_story_selector_groups,
        },
        "isolatedSceneKeys": isolated,
        "weakOnlySceneKeys": weak_only,
        "unknownSceneKeys": unknown,
        "nativeControlPathContextSceneKeys": sorted(
            native_context_scene_keys,
            key=natural_key,
        ),
        "unresolvedSourceNodes": [
            {
                "key": key,
                "kind": graph_node_kinds.get(key) or "unknown",
                "incidentEdgeKinds": sorted(kinds),
            }
            for key, kinds in sorted(unresolved_nodes.items(), key=lambda item: natural_key(item[0]))
        ],
        "definitionOnlySourceNodes": [
            {
                "key": key,
                "kind": graph_node_kinds.get(key) or "unknown",
                "incidentEdgeKinds": sorted(
                    evidence["incidentEdgeKinds"]
                ),
                "recordClasses": sorted(evidence["recordClasses"]),
                "sourceFiles": sorted(evidence["sourceFiles"]),
                "levelIds": sorted(evidence["levelIds"]),
            }
            for key, evidence in sorted(
                definition_only_nodes.items(),
                key=lambda item: natural_key(item[0]),
            )
        ],
        "warnings": [
            *warnings,
            *dialog_tree_conditional_warnings,
            *narrative_containment_warnings,
            *open_ui_containment_warnings,
            *lifecycle_warnings,
            *native_branch_arm_coverage_diagnostics,
        ],
    }


def _split_missions(values: list[str]) -> set[str]:
    return {
        mission.strip()
        for value in values
        for mission in str(value).split(",")
        if mission.strip()
    }


def _expand_levelscript_playback_context_candidates(
    candidate_kinds: dict[str, str],
    mission_payload: dict[str, Any],
    index_kind_by_key: dict[str, str],
    playback_source_files_by_key: dict[str, set[str]],
) -> tuple[dict[str, str], set[str]]:
    """Add exact cross-owner playback cards as context, not ownership."""
    expanded = dict(candidate_kinds)
    context_keys: set[str] = set()
    flow = (
        mission_payload.get("flow")
        if isinstance(mission_payload.get("flow"), dict)
        else {}
    )
    scene_graph = (
        flow.get("sceneGraph")
        if isinstance(flow.get("sceneGraph"), dict)
        else {}
    )
    for edge in scene_graph.get("edges") or []:
        if (
            not isinstance(edge, dict)
            or safe_key(edge.get("kind")) != "levelscriptSceneChain"
        ):
            continue
        edge_source_files = {
            safe_key(value)
            for value in edge.get("sourceFiles") or []
            if safe_key(value)
        }
        if not edge_source_files:
            continue
        for endpoint in ("from", "to"):
            story_key = safe_key(edge.get(endpoint))
            if (
                not story_key
                or story_key in expanded
                or story_key not in index_kind_by_key
                or not (
                    edge_source_files
                    & playback_source_files_by_key.get(story_key, set())
                )
            ):
                continue
            expanded[story_key] = index_kind_by_key[story_key]
            context_keys.add(story_key)
    return expanded, context_keys


def build_report(
    language: str,
    selected_missions: set[str] | None = None,
    story_data_root: Path | None = None,
    quest_succeed_lifecycle_contract: dict[str, Any] | None = None,
    extra_thread_scheduler_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    lang_root = (story_data_root or (ROOT / "webui" / "data" / "lang")) / language
    index_path = lang_root / "index.json"
    mission_dir = lang_root / "mission"
    conversation_dir = lang_root / "conv"
    index_payload = read_json(index_path, {})
    index_entries = index_payload.get("entries") if isinstance(index_payload, dict) else []
    index_entries = index_entries if isinstance(index_entries, list) else []
    index_kind_by_key = {
        safe_key(entry.get("k")): safe_key(entry.get("d")) or "unknown"
        for entry in index_entries
        if isinstance(entry, dict) and safe_key(entry.get("k"))
    }
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

    story_occurrences = build_levelscript_action_story_occurrences()
    playback_source_files_by_key: dict[str, set[str]] = defaultdict(set)
    for story_key, occurrences in story_occurrences.items():
        for occurrence in occurrences:
            if (
                not isinstance(occurrence, dict)
                or not safe_key(
                    occurrence.get("recordClass")
                ).startswith("play_")
            ):
                continue
            source_file = safe_key(occurrence.get("sourceFile"))
            if source_file:
                playback_source_files_by_key[story_key].add(source_file)
    exact_playback_source_keys = set(playback_source_files_by_key)
    dialog_tree_narrative_occurrences = (
        recover_dialog_tree_narrative_mask_actions()
    )
    dialog_tree_open_ui_occurrences = (
        recover_dialog_tree_open_ui_content_actions()
    )
    reading_popup_rows = read_json(READING_POPUP_TABLE_PATH, {})
    reading_popup_source = READING_POPUP_TABLE_PATH.relative_to(ROOT).as_posix()
    reading_popup_sha256 = (
        hashlib.sha256(READING_POPUP_TABLE_PATH.read_bytes()).hexdigest().upper()
        if READING_POPUP_TABLE_PATH.is_file() else ""
    )
    rows: list[dict[str, Any]] = []
    totals: Counter[str] = Counter()
    edge_kind_totals: Counter[str] = Counter()
    native_transition_kind_totals: Counter[str] = Counter()
    for mission in missions:
        candidate_kinds = build_scene_order_candidate_kinds(index_entries, mission, None)
        if not candidate_kinds:
            continue
        mission_path = mission_dir / f"{mission}.json"
        mission_payload = load_mission_payload_with_variants(
            mission_dir,
            mission,
        )
        mission_flow = (
            mission_payload.get("flow")
            if isinstance(mission_payload.get("flow"), dict)
            else {}
        )
        candidate_kinds, exact_native_control_path_context_keys = (
            _expand_native_control_path_candidates(
                mission_flow,
                candidate_kinds,
            )
        )
        candidate_kinds, exact_levelscript_playback_context_keys = (
            _expand_levelscript_playback_context_candidates(
                candidate_kinds,
                mission_payload,
                index_kind_by_key,
                playback_source_files_by_key,
            )
        )
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
            exact_playback_source_keys,
            exact_levelscript_playback_context_keys,
            exact_native_control_path_context_keys,
            dialog_tree_narrative_occurrences,
            dialog_tree_open_ui_occurrences,
            reading_popup_rows,
            reading_popup_source,
            reading_popup_sha256,
            quest_succeed_lifecycle_contract,
            extra_thread_scheduler_contract,
        )
        row["missionData"] = (
            mission_path.relative_to(ROOT).as_posix() if mission_path.is_file() else ""
        )
        row["missionDataVariants"] = [
            (
                Path(path).relative_to(ROOT).as_posix()
                if Path(path).is_relative_to(ROOT)
                else Path(path).as_posix()
            )
            for path in mission_payload.get("_sourceMissionVariantFiles") or []
        ]
        rows.append(row)
        summary = row["summary"]
        totals["missions"] += 1
        totals["scenes"] += summary["sceneCount"]
        totals["nativeControlPathContextScenes"] += summary[
            "nativeControlPathContextSceneCount"
        ]
        totals["exactLevelScriptPlaybackContextScenes"] += summary[
            "exactLevelScriptPlaybackContextSceneCount"
        ]
        totals["directEdges"] += summary["directEdgeCount"]
        totals["questStartActionDefinitions"] += summary[
            "questStartActionDefinitionCount"
        ]
        totals["questStartActionDefinitionStories"] += summary[
            "questStartActionDefinitionStoryCount"
        ]
        totals["questStartActionDefinitionQuests"] += summary[
            "questStartActionDefinitionQuestCount"
        ]
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
        totals["definitionOnlySourceNodes"] += summary[
            "definitionOnlySourceNodeCount"
        ]
        totals["embeddedContainments"] += summary["embeddedContainmentCount"]
        totals["embeddedScenes"] += summary["embeddedSceneCount"]
        totals["totalScenePairs"] += summary["totalScenePairs"]
        totals["comparableScenePairs"] += summary["comparableScenePairs"]
        totals["unorderedScenePairs"] += summary["unorderedScenePairs"]
        totals["sceneGraphOptionGroups"] += summary["sceneGraphOptionGroupCount"]
        totals["nativeControlBranches"] += summary["nativeControlBranchCount"]
        totals["nativeControlFullArmBranches"] += summary[
            "nativeControlFullArmBranchCount"
        ]
        totals["nativeControlSerializedArms"] += summary[
            "nativeControlSerializedArmCount"
        ]
        totals["nativeControlNonStoryArms"] += summary[
            "nativeControlNonStoryArmCount"
        ]
        totals["nativeControlInactiveTargetArms"] += summary[
            "nativeControlInactiveTargetArmCount"
        ]
        totals["nativeControlRuntimeTerminalArms"] += summary[
            "nativeControlRuntimeTerminalArmCount"
        ]
        totals["nativeControlFullArmValidationFailures"] += summary[
            "nativeControlFullArmValidationFailureCount"
        ]
        totals["nativeControlCrossBoundaryBranches"] += summary[
            "nativeControlCrossBoundaryBranchCount"
        ]
        totals["nativeControlCrossBoundaryExternalStories"] += summary[
            "nativeControlCrossBoundaryExternalStoryCount"
        ]
        totals["nativeMissionStateBranches"] += summary[
            "nativeMissionStateBranchCount"
        ]
        totals["nativeMissionStateBranchExternalStories"] += summary[
            "nativeMissionStateBranchExternalStoryCount"
        ]
        totals["nativeControlMerges"] += summary["nativeControlMergeCount"]
        totals["nativeControlPathTransitionEdges"] += summary[
            "nativeControlPathTransitionEdgeCount"
        ]
        totals["nativeControlPathBranchingTransitionEdges"] += summary[
            "nativeControlPathBranchingTransitionEdgeCount"
        ]
        totals["nativeControlPathTransitionSteps"] += summary[
            "nativeControlPathTransitionStepCount"
        ]
        totals["nativeControlPathTransitionActionEndpoints"] += summary[
            "nativeControlPathTransitionActionEndpointCount"
        ]
        totals["nativeControlPathNamedActionEndpoints"] += summary[
            "nativeControlPathNamedActionEndpointCount"
        ]
        totals["nativeControlPathUnresolvedActionEndpoints"] += summary[
            "nativeControlPathUnresolvedActionEndpointCount"
        ]
        native_transition_kind_totals.update(
            summary["nativeControlPathTransitionKinds"]
        )
        totals["nativeOrderedSequences"] += summary["nativeOrderedSequenceCount"]
        totals["nativeOrderedSequenceEdges"] += summary[
            "nativeOrderedSequenceEdgeCount"
        ]
        totals["nativeOrderedSequenceContexts"] += summary[
            "nativeOrderedSequenceContextCount"
        ]
        totals["questSucceedLifecycleEdges"] += summary[
            "questSucceedLifecycleEdgeCount"
        ]
        totals["questSucceedLifecycleQuests"] += summary[
            "questSucceedLifecycleQuestCount"
        ]
        totals["questSucceedLifecycleMissions"] += int(
            summary["questSucceedLifecycleEdgeCount"] > 0
        )
        totals["nativeRelatedActionTopologies"] += summary[
            "nativeRelatedActionTopologyCount"
        ]
        totals["nativeNamedPredicates"] += summary["nativeNamedPredicateCount"]
        totals["nativeInlinePredicates"] += summary["nativeInlinePredicateCount"]
        totals["nativeSemanticPredicates"] += summary["nativeSemanticPredicateCount"]
        totals["nativeClassOnlyPredicates"] += summary["nativeClassOnlyPredicateCount"]
        totals["nativeUnresolvedPredicates"] += summary["nativeUnresolvedPredicateCount"]
        totals["questForks"] += summary["questForkCount"]
        totals["questMerges"] += summary["questMergeCount"]
        totals["dialogLineOptionGroups"] += summary["dialogLineOptionGroupCount"]
        totals["dialogLineOptionRoutes"] += summary["dialogLineOptionRouteCount"]
        totals["dialogLineOptionLines"] += summary["dialogLineOptionLineCount"]
        totals["excludedDialogLineOptionGroups"] += summary["excludedDialogLineOptionGroupCount"]
        totals["excludedDialogLineOptions"] += summary["excludedDialogLineOptionCount"]
        totals["actionableExcludedDialogLineOptionGroups"] += (
            summary["actionableExcludedDialogLineOptionGroupCount"]
        )
        totals["closedExcludedDialogLineOptionGroups"] += (
            summary["closedExcludedDialogLineOptionGroupCount"]
        )
        totals["noExplicitRouteGroups"] += summary["noExplicitRouteGroupCount"]
        totals["noExplicitRouteOptions"] += summary["noExplicitRouteOptionCount"]
        totals["branchingNoExplicitRouteGroups"] += (
            summary["branchingNoExplicitRouteGroupCount"]
        )
        totals["branchingNoExplicitRouteOptions"] += (
            summary["branchingNoExplicitRouteOptionCount"]
        )
        totals["singleOptionNoExplicitRouteGroups"] += (
            summary["singleOptionNoExplicitRouteGroupCount"]
        )
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
    summary_payload["nativeControlPathTransitionKinds"] = dict(
        sorted(native_transition_kind_totals.items())
    )
    summary_payload["binaryValidatedParallelFanoutTransitions"] = (
        native_transition_kind_totals.get("parallelFanout", 0)
    )
    summary_payload["binaryValidatedParallelFanoutEvidenceRows"] = sum(
        1
        for mission_row in rows
        for edge in mission_row.get("directEdges") or []
        if edge.get("kind") == "levelscriptNativeControlPath"
        for event in edge.get("events") or []
        for step in event.get("transitionSteps") or []
        if step.get("runtimeSemantics")
        == "binary_proven_extra_thread_launch"
    )
    summary_payload["binaryValidatedParallelFanoutBranchGroups"] = sum(
        1
        for mission_row in rows
        for branch in (
            (mission_row.get("branches") or {}).get("nativeControlBranches")
            or []
        )
        if branch.get("kind") == "splitFanout"
    )
    summary_payload["dialogLineOptionProvenance"] = dict(sorted(dialog_provenance_totals.items()))
    native_serialized_branch_inventory = (
        _native_serialized_branch_inventory(
            original_binary_contract=extra_thread_scheduler_contract,
            playback_occurrences_by_root={
                NATIVE_LEVELSCRIPT_ROOTS[0]: story_occurrences,
            },
        )
        if not selected_missions
        else _native_serialized_branch_inventory_not_requested()
    )
    inventory_summary = native_serialized_branch_inventory.get("summary") or {}
    summary_payload.update({
        "nativeSerializedBranchGroupCount": int(
            inventory_summary.get("serializedBranchGroupCount") or 0
        ),
        "nativeSerializedBranchArmCount": int(
            inventory_summary.get("serializedBranchArmCount") or 0
        ),
        "nativeSerializedPlaybackArmCount": int(
            inventory_summary.get("playbackArmCount") or 0
        ),
        "nativeSerializedMultiPlaybackBranchCount": int(
            inventory_summary.get("multiPlaybackBranchCount") or 0
        ),
        "nativeSerializedNestedControlCount": int(
            inventory_summary.get("nestedControlCount") or 0
        ),
        "nativeSerializedNestedPlaybackArmCount": int(
            inventory_summary.get("nestedPlaybackArmCount") or 0
        ),
        "nativeSerializedNestedMultiPlaybackControlCount": int(
            inventory_summary.get("nestedMultiPlaybackControlCount") or 0
        ),
        "nativeSerializedBranchPredicateConflictCount": int(
            inventory_summary.get("controlPredicateConflictCount") or 0
        ),
        "nativeSerializedBranchValidationFailureCount": int(
            inventory_summary.get("validationFailureCount") or 0
        ),
    })
    return {
        "_schema": SCHEMA,
        "_generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "language": language,
        "inputs": {
            "index": index_path.relative_to(ROOT).as_posix() if index_path.is_relative_to(ROOT) else index_path.as_posix(),
            "missionDir": mission_dir.relative_to(ROOT).as_posix() if mission_dir.is_relative_to(ROOT) else mission_dir.as_posix(),
            "conversationDir": conversation_dir.relative_to(ROOT).as_posix() if conversation_dir.is_relative_to(ROOT) else conversation_dir.as_posix(),
        },
        "evidencePolicy": EVIDENCE_POLICY,
        "parallelFanoutAuthority": {
            key: value
            for key, value in {
                "schema": (extra_thread_scheduler_contract or {}).get("schema"),
                "classification": (extra_thread_scheduler_contract or {}).get(
                    "classification"
                ),
                "source": (extra_thread_scheduler_contract or {}).get("source"),
                "finding": (extra_thread_scheduler_contract or {}).get("finding"),
                "boundary": (extra_thread_scheduler_contract or {}).get("boundary"),
                "writerMethods": (extra_thread_scheduler_contract or {}).get(
                    "extraThreadExecuteMethods", []
                ),
                "relatedOriginalFiles": (
                    extra_thread_scheduler_contract or {}
                ).get("relatedOriginalFiles", []),
                "validation": (extra_thread_scheduler_contract or {}).get(
                    "validation"
                ),
            }.items()
            if value not in (None, "", [], {})
        },
        "summary": summary_payload,
        "missions": rows,
        "nativeSerializedBranchInventory": native_serialized_branch_inventory,
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
        f"- candidate scene placements: `{summary.get('scenes', 0)}` "
        f"(`{summary.get('nativeControlPathContextScenes', 0)}` admitted only by an "
        "exact native path to an index-backed mission scene)",
        f"- direct evidence edges: `{summary.get('directEdges', 0)}` "
        f"(`{summary.get('strongEdges', 0)}` strong, `{summary.get('supportedEdges', 0)}` supported, "
        f"`{summary.get('weakEdges', 0)}` weak)",
        f"- binary-proven quest-success lifecycle: "
        f"`{summary.get('questSucceedLifecycleEdges', 0)}` exact Story edges across "
        f"`{summary.get('questSucceedLifecycleQuests', 0)}` quests in "
        f"`{summary.get('questSucceedLifecycleMissions', 0)}` missions",
        f"- reduced component edges: `{summary.get('reducedComponentEdges', 0)}`",
        f"- cyclic components: `{summary.get('cycles', 0)}` across "
        f"`{summary.get('missionsWithCycles', 0)}` missions",
        f"- isolated scenes: `{summary.get('isolatedScenes', 0)}`",
        f"- exact nested DialogTree containments: "
        f"`{summary.get('embeddedContainments', 0)}` across "
        f"`{summary.get('embeddedScenes', 0)}` child scenes",
        f"- weak-only scenes: `{summary.get('weakOnlyScenes', 0)}`",
        f"- comparable source-proven pairs: `{summary.get('comparableScenePairs', 0)}` / "
        f"`{summary.get('totalScenePairs', 0)}` (`{summary.get('comparablePairRate', 0.0):.2%}`)",
        f"- strict intra-dialog option routes: `{summary.get('dialogLineOptionRoutes', 0)}` options "
        f"in `{summary.get('dialogLineOptionGroups', 0)}` groups, covering "
        f"`{summary.get('dialogLineOptionLines', 0)}` branch lines",
        f"- mission-level branches: `{summary.get('questForks', 0)}` quest forks, "
        f"`{summary.get('questMerges', 0)}` quest merges, and "
        f"`{summary.get('sceneGraphOptionGroups', 0)}` authored cross-scene option groups",
        f"- native control topology: `{summary.get('nativeControlBranches', 0)}` exact "
        f"Split/IfElse/Switch Story fan-outs and `{summary.get('nativeControlMerges', 0)}` "
        "observed convergences",
        f"- complete native branch arms: "
        f"`{summary.get('nativeControlFullArmBranches', 0)}` branch placements expose "
        f"`{summary.get('nativeControlSerializedArms', 0)}` serialized slots, including "
        f"`{summary.get('nativeControlNonStoryArms', 0)}` active non-Story arms, "
        f"`{summary.get('nativeControlInactiveTargetArms', 0)}` inactive slots, and "
        f"`{summary.get('nativeControlRuntimeTerminalArms', 0)}` runtime terminals; "
        f"`{summary.get('nativeControlFullArmValidationFailures', 0)}` validation failures",
        f"- complete cross-boundary native topology: "
        f"`{summary.get('nativeControlCrossBoundaryBranches', 0)}` branch groups retain "
        f"`{summary.get('nativeControlCrossBoundaryExternalStories', 0)}` exact Story "
        "references outside nominal mission grouping (never ownership or order)",
        f"- native mission-state alternatives: "
        f"`{summary.get('nativeMissionStateBranches', 0)}` exact branch groups exposing "
        f"`{summary.get('nativeMissionStateBranchExternalStories', 0)}` cross-mission "
        "Story references (selection evidence only, never chronology)",
        f"- exact native Story transitions: "
        f"`{summary.get('nativeControlPathTransitionEdges', 0)}` typed path-prefix edges, "
        f"including `{summary.get('nativeControlPathBranchingTransitionEdges', 0)}` "
        "whose source-to-target suffix traverses a typed branch or ordered fan-out",
        f"- exact native transition action names: "
        f"`{summary.get('nativeControlPathNamedActionEndpoints', 0)}` / "
        f"`{summary.get('nativeControlPathTransitionActionEndpoints', 0)}` step endpoints "
        f"across `{summary.get('nativeControlPathTransitionSteps', 0)}` steps; "
        f"`{summary.get('nativeControlPathUnresolvedActionEndpoints', 0)}` unresolved",
        f"- native ordered topology: `{summary.get('nativeOrderedSequences', 0)}` exact "
        f"Branch iterators creating `{summary.get('nativeOrderedSequenceEdges', 0)}` "
        "Story-order edges",
        f"- native ordered sequence contexts: `{summary.get('nativeOrderedSequenceContexts', 0)}` "
        "exact serialized Branch arm projections attached to Story paths; these "
        "remain context-only unless the global multi-arm order gate admits an edge",
        f"- corpus serialized Branch inventory: `{summary.get('nativeSerializedBranchGroupCount', 0)}` "
        f"unique original groups / `{summary.get('nativeSerializedBranchArmCount', 0)}` "
        f"serialized slots / `{summary.get('nativeSerializedPlaybackArmCount', 0)}` "
        f"exact playback-bearing arms; `{summary.get('nativeSerializedMultiPlaybackBranchCount', 0)}` "
        "groups have playback on multiple arms, so this census admits no order or ownership",
        f"- nested corpus Branch controls: `{summary.get('nativeSerializedNestedControlCount', 0)}` "
        f"typed control contexts / `{summary.get('nativeSerializedNestedPlaybackArmCount', 0)}` "
        f"nested playback arms / `{summary.get('nativeSerializedNestedMultiPlaybackControlCount', 0)}` "
        f"multi-playback controls; `{summary.get('nativeSerializedBranchPredicateConflictCount', 0)}` "
        "predicate-join conflicts (conflicts fail closed)",
        f"- related native action graphs: `{summary.get('nativeRelatedActionTopologies', 0)}` "
        "original LevelScript files attached only through exact Story control paths",
        f"- conditional predicates: `{summary.get('nativeSemanticPredicates', 0)}` exact "
        f"operand decodes, `{summary.get('nativeClassOnlyPredicates', 0)}` exact class-only, "
        f"and `{summary.get('nativeUnresolvedPredicates', 0)}` unresolved",
        f"- excluded option evidence: `{summary.get('excludedDialogLineOptions', 0)}` options "
        f"in `{summary.get('excludedDialogLineOptionGroups', 0)}` groups "
        f"(`{summary.get('actionableExcludedDialogLineOptionGroups', 0)}` still "
        f"actionable, `{summary.get('closedExcludedDialogLineOptionGroups', 0)}` "
        "closed shared/cosmetic)",
        f"- option groups with no explicit route: `{summary.get('noExplicitRouteGroups', 0)}` "
        f"(`{summary.get('noExplicitRouteOptions', 0)}` options); "
        f"`{summary.get('branchingNoExplicitRouteGroups', 0)}` are multi-choice "
        f"groups and `{summary.get('singleOptionNoExplicitRouteGroups', 0)}` are "
        "single-option acknowledgements",
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
    report = build_report(
        args.language,
        _split_missions(args.mission) or None,
        extra_thread_scheduler_contract=(
            load_current_parallel_fanout_authority()
        ),
    )
    out_json = args.reports_dir / f"source_story_partial_order_{args.language}.json"
    out_md = args.reports_dir / f"source_story_partial_order_{args.language}.md"
    write_report_json(out_json, report)
    write_text_if_changed(out_md, render_markdown(report))
    summary = report["summary"]
    print(f"Source-only partial order: {_repo_path(out_md)}")
    print(f"Source-only partial-order data: {_repo_path(out_json)}")
    print(
        f"{summary.get('missions', 0)} missions; {summary.get('scenes', 0)} scenes; "
        f"{summary.get('strongEdges', 0)} strong edges; "
        f"{summary.get('comparablePairRate', 0.0):.2%} comparable pairs"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
