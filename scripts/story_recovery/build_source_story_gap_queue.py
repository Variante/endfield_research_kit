#!/usr/bin/env python3
"""Rank source-only Story recovery gaps without inventing scene order.

The queue reuses the strict partial-order builder, then measures where original
game data could still improve coverage: isolated/weak scenes, source cycles,
untyped multi-scene LevelScript contexts, quests without strict Story
attachment, unresolved source nodes, and unverified option groups.  Main-story
(``e``) missions sort before the other established priority buckets.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    combined_non_mission_content_keys,
    md_escape,
    non_mission_content_keys,
    read_json,
    safe_key,
    write_report_json,
    write_text_if_changed,
)
from build_priority_story_order_audit import priority_bucket  # noqa: E402
from build_source_story_partial_order import build_report as build_partial_order_report  # noqa: E402
from story_builder.mission_recovery import natural_key  # noqa: E402


SCHEMA = "sourceStoryGapQueue.v14"
LEVELSCRIPT_INTERACTIVE_NARRATIVE_MAPPING_ID = (
    "levelscript-interactive-narrative-config-v1"
)
LEVELDATA_INTERACTIVE_NARRATIVE_MAPPING_ID = (
    "leveldata-interactive-narrative-config-v1"
)
BUCKET_ORDER = ("main", "event", "major", "character", "other")

# The score is a triage aid, not recovered chronology. Every contribution is
# emitted per mission so a reviewer can change the policy without losing facts.
SCORE_WEIGHTS = {
    "missingMissionBundle": 100,
    "sourceCycles": 20,
    "cycleScenes": 8,
    "untypedMultiSceneLevelscriptContexts": 10,
    "actionableCoreIsolatedScenes": 5,
    "actionableWeakOnlyScenes": 4,
    "unresolvedSourceNodes": 4,
    "questIdsWithoutStrictStoryAttachment": 3,
    "actionableNoExplicitOptionRouteGroups": 2,
    "actionableExcludedOptionEvidenceGroups": 2,
}

CORE_STORY_NODE_KINDS = frozenset({
    "black",
    "cutscene",
    "dlg",
    "misc",
    "radio",
    "remotecomm",
    "runtimeDialog",
    "sns",
    "text",
})

FRONTIER_ORDER = (
    "missing-mission-runtime-bundle",
    "levelscript-control-flow",
    "source-cycle-review",
    "quest-scene-attachment",
    "dialog-option-runtime",
    "unresolved-source-node",
    "isolated-scene-source-link",
)

# Exact current-build ActionBase formatter classifications that are useful to
# this queue but deliberately excluded from the playback-oriented mapping in
# ``story_builder.level_bindings``.  These tags carry Story-looking ids while
# configuring, removing, overriding, or stopping presentation; they cannot
# establish that the referenced Story file plays at that point.
KNOWN_NON_PLAYBACK_ACTIONS = {
    ("0x0344", "0x0a"): ("OverrideNPCDialog", "override_dialog"),
    ("0x0377", "0x0b"): ("PreloadDialogAction", "preload_dialog"),
    ("0x0389", "0x0a"): ("RemoveNPCDialog", "remove_dialog"),
    ("0x04b5", "0x09"): ("StopRadio", "stop_radio"),
}
KNOWN_NON_PLAYBACK_MAPPING_ID = (
    "gameassembly-2026-07-11-cr-0x18b9217d0-actionbase-formatter-table"
)
NPC_PROXY_DIALOG_SELECTION_MAPPING_ID = (
    "npc-proxy-dialog-selection-native-v1"
)
NPC_PROXY_DIALOG_SELECTION_GAMEASSEMBLY_SHA256 = (
    "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE"
)
DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID = (
    "dialog-tree-narrative-mask-connection-native-v1"
)


def _bucket(mission: str) -> str:
    return priority_bucket(mission) or "other"


def _string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    out: list[str] = []
    for value in values:
        text = safe_key(value)
        if text and text not in out:
            out.append(text)
    return out


def _timeline(mission_payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(mission_payload, dict):
        return {}
    value = mission_payload.get("timelineRecovery")
    return value if isinstance(value, dict) else {}


def _flow(mission_payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(mission_payload, dict):
        return {}
    value = mission_payload.get("flow")
    return value if isinstance(value, dict) else {}


def _strict_quest_attachments(partial_row: dict[str, Any]) -> tuple[set[str], set[str]]:
    quest_ids: set[str] = set()
    scene_keys: set[str] = set()
    for edge in partial_row.get("directEdges") or []:
        if not isinstance(edge, dict) or safe_key(edge.get("tier")) != "strong":
            continue
        edge_quest_ids = _string_list(edge.get("questIds"))
        if not edge_quest_ids:
            continue
        quest_ids.update(edge_quest_ids)
        for field in ("from", "to"):
            scene_key = safe_key(edge.get(field))
            if scene_key:
                scene_keys.add(scene_key)
    return quest_ids, scene_keys


def _diagnostic_quest_attachments(
    timeline: dict[str, Any],
    candidate_scene_keys: set[str],
) -> tuple[set[str], set[str], Counter[str]]:
    quest_ids: set[str] = set()
    scene_keys: set[str] = set()
    source_counts: Counter[str] = Counter()
    placements = timeline.get("scenePlacement")
    if not isinstance(placements, dict):
        return quest_ids, scene_keys, source_counts
    for placement in placements.values():
        if not isinstance(placement, dict):
            continue
        scene_key = safe_key(placement.get("sceneKey"))
        if scene_key not in candidate_scene_keys:
            continue
        attached_ids = _string_list(placement.get("questIds"))
        if not attached_ids:
            continue
        quest_ids.update(attached_ids)
        scene_keys.add(scene_key)
        for source in placement.get("questAttachSources") or []:
            if isinstance(source, dict):
                source_counts[safe_key(source.get("source")) or "unknown"] += 1
    return quest_ids, scene_keys, source_counts


def _levelscript_context_gaps(
    timeline: dict[str, Any],
    flow: dict[str, Any],
    native_playback_index: dict[str, list[dict[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
    """Return multi-scene contexts missing exact typed playback records.

    ``sourceBackedSceneSequences`` is intentionally not used here. Those
    generic UID/nextId chains include preload, remove, override, and stop
    actions and can cross physical ActionSerializedMap roots. A scene counts as
    typed only when the current-build formatter mapping resolves an actionList
    record to an actual playback class in this exact source file.
    """
    typed_by_file: dict[str, set[str]] = defaultdict(set)
    connections = list(flow.get("missionStoryConnections") or [])
    connections.extend(
        connection
        for quest in flow.get("quests") or []
        if isinstance(quest, dict)
        for connection in quest.get("storyConnections") or []
    )
    connections.extend(
        connection
        for connection in flow.get("unlinkedNativePlayback") or []
        if isinstance(connection, dict)
    )
    for connection in connections:
        if not isinstance(connection, dict):
            continue
        scene_key = safe_key(connection.get("key"))
        if not scene_key:
            continue
        exact_native_connection = (
            safe_key(connection.get("confidence"))
            in {"native_typed_direct", "native_typed_direct_unscoped"}
            and safe_key(connection.get("nativeMappingId")).startswith("gameassembly-")
        )
        occurrences = list(connection.get("levelScriptOccurrences") or [])
        if exact_native_connection:
            for field in ("occurrences", "nativeOccurrences", "nativeBlackActionOccurrences"):
                occurrences.extend(connection.get(field) or [])
        for occurrence in occurrences:
            if not isinstance(occurrence, dict):
                continue
            source_file = safe_key(occurrence.get("sourceFile"))
            action_map_role = safe_key(occurrence.get("actionMapRole"))
            record_class = safe_key(occurrence.get("recordClass"))
            if (
                source_file
                and action_map_role.startswith("actionList#")
                and record_class.startswith("play_")
                and safe_key(occurrence.get("actionName"))
            ):
                typed_by_file[source_file].add(scene_key)
        if (
            safe_key(connection.get("relation"))
            in {
                "levelscript_quest_completed_action",
                "levelscript_quest_processing_action",
            }
            and safe_key(connection.get("confidence")) == "native_typed_direct"
            and safe_key(connection.get("event")) == "LevelEvent_OnQuestStateChanged"
            and safe_key(connection.get("nativeMappingId")).startswith("gameassembly-")
            and safe_key(connection.get("actionName"))
            and safe_key(connection.get("sourceFile"))
        ):
            typed_by_file[safe_key(connection.get("sourceFile"))].add(scene_key)
        # Some exact native playback rows are represented by a stronger
        # mission-context relation rather than by the lower-level occurrence
        # list. Accept that form only when one exact LevelScript source file and
        # one typed playback step are both explicit.
        levelscript_source_files = [
            source_file
            for source_file in _string_list(connection.get("sourceFiles"))
            if "/LevelScriptData/" in ("/" + source_file.replace("\\", "/"))
        ]
        native_actions = set(_string_list(connection.get("nativeActions")))
        exact_playback_actions = {
            safe_key(step.get("actionName"))
            for owner in connection.get("nativeEventOwners") or []
            if (
                isinstance(owner, dict)
                and safe_key(owner.get("status")).startswith(
                    "exact_serialized_control_path"
                )
            )
            for step in owner.get("path") or []
            if (
                isinstance(step, dict)
                and safe_key(step.get("recordClass")).startswith("play_")
                and safe_key(step.get("actionName"))
            )
        }
        if (
            len(levelscript_source_files) == 1
            and native_actions & exact_playback_actions
        ):
            typed_by_file[levelscript_source_files[0]].add(scene_key)

    # A weaker mission/quest context can cause the Story bundle assembler to
    # omit a redundant unlinked-native row.  That omission must not make the
    # recovery queue call an already decoded ActionBase playback record
    # "untyped."  Consult the current-build binary index directly, while still
    # requiring the exact source file, actionList membership, playback class,
    # Story identity, and GameAssembly mapping.  This proves record type only;
    # it creates neither mission ownership nor chronology.
    for scene_key, occurrences in (native_playback_index or {}).items():
        for occurrence in occurrences or []:
            if not isinstance(occurrence, dict):
                continue
            source_file = safe_key(occurrence.get("sourceFile"))
            if (
                source_file
                and safe_key(occurrence.get("actionMapRole")).startswith(
                    "actionList#"
                )
                and safe_key(occurrence.get("recordClass")).startswith("play_")
                and safe_key(occurrence.get("actionName"))
                and safe_key(occurrence.get("nativeMappingId")).startswith(
                    "gameassembly-"
                )
                and scene_key in {
                    safe_key(value)
                    for value in occurrence.get("allStoryKeysInRecord") or []
                }
            ):
                typed_by_file[source_file].add(scene_key)

    rows: list[dict[str, Any]] = []
    for context in timeline.get("sourceBackedStoryCallContexts") or []:
        if not isinstance(context, dict):
            continue
        scene_keys = _string_list(context.get("sceneKeys"))
        if len(scene_keys) < 2:
            continue
        source_file = safe_key(context.get("sourceFile"))
        typed_scene_keys = typed_by_file.get(source_file, set())
        unresolved = [key for key in scene_keys if key not in typed_scene_keys]
        if len(typed_scene_keys & set(scene_keys)) >= len(scene_keys):
            continue
        rows.append({
            "sourceFile": source_file,
            "levelId": safe_key(context.get("levelId")),
            "sceneKeys": scene_keys,
            "typedSceneKeys": sorted(typed_scene_keys & set(scene_keys), key=natural_key),
            "unresolvedSceneKeys": unresolved,
        })
    rows.sort(key=lambda row: (natural_key(row["sourceFile"]), natural_key(row["sceneKeys"][0])))
    return rows


def _classify_levelscript_context_gaps(
    context_gaps: list[dict[str, Any]],
    action_story_occurrences: dict[str, list[dict[str, Any]]] | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Separate actionable ActionBase gaps from exact binary-negative rows.

    ``None`` means that no exhaustive action occurrence scan was supplied, so
    every row stays actionable.  An explicit mapping is treated as the complete
    current-build actionList census.  A Story key with no same-file actionList
    occurrence is therefore a non-action serialized reference for this
    context, while a fully mapped preload/override/remove/stop occurrence is a
    known non-playback action.  Both remain visible, but neither is a missing
    typed-playback decoder.
    """
    if action_story_occurrences is None:
        return context_gaps, []

    actionable: list[dict[str, Any]] = []
    closed: list[dict[str, Any]] = []
    closed_statuses = {
        "known_non_playback_action_only",
        "non_action_story_reference",
    }
    for raw_context in context_gaps:
        context = dict(raw_context)
        source_file = safe_key(context.get("sourceFile"))
        classifications: list[dict[str, Any]] = []
        for scene_key in _string_list(context.get("unresolvedSceneKeys")):
            occurrences = [
                occurrence
                for occurrence in action_story_occurrences.get(scene_key, [])
                if (
                    isinstance(occurrence, dict)
                    and safe_key(occurrence.get("sourceFile")) == source_file
                    and safe_key(occurrence.get("actionMapRole")).startswith(
                        "actionList#"
                    )
                )
            ]
            evidence: list[dict[str, Any]] = []
            has_unmapped_action = False
            for occurrence in occurrences:
                action_code = safe_key(occurrence.get("actionCode")).lower()
                action_kind = safe_key(occurrence.get("actionKind")).lower()
                action_name = safe_key(occurrence.get("actionName"))
                record_class = safe_key(occurrence.get("recordClass"))
                mapping_id = safe_key(occurrence.get("nativeMappingId"))
                if not action_name or not record_class:
                    mapped = KNOWN_NON_PLAYBACK_ACTIONS.get(
                        (action_code, action_kind)
                    )
                    if mapped:
                        action_name, record_class = mapped
                        mapping_id = KNOWN_NON_PLAYBACK_MAPPING_ID
                    else:
                        has_unmapped_action = True
                evidence.append({
                    key: value
                    for key, value in {
                        "actionCode": action_code,
                        "actionKind": action_kind,
                        "actionName": action_name,
                        "recordClass": record_class,
                        "actionMapRole": safe_key(
                            occurrence.get("actionMapRole")
                        ),
                        "localId": occurrence.get("localId"),
                        "recordOffset": occurrence.get("recordOffset"),
                        "nativeMappingId": mapping_id,
                    }.items()
                    if value not in ("", None)
                })

            if not occurrences:
                status = "non_action_story_reference"
            elif (
                not has_unmapped_action
                and evidence
                and all(
                    safe_key(row.get("recordClass"))
                    and not safe_key(row.get("recordClass")).startswith("play_")
                    for row in evidence
                )
            ):
                status = "known_non_playback_action_only"
            else:
                status = "unmapped_action_record"
            classifications.append({
                "sceneKey": scene_key,
                "status": status,
                "actionOccurrences": evidence,
            })

        context["unresolvedBinaryClassifications"] = classifications
        context["recoveryStatus"] = (
            "closed_no_typed_playback_order_evidence"
            if classifications
            and all(row["status"] in closed_statuses for row in classifications)
            else "actionable_typed_playback_decoder_gap"
        )
        if context["recoveryStatus"].startswith("closed_"):
            closed.append(context)
        else:
            actionable.append(context)
    return actionable, closed


def _frontier_contributions(metrics: dict[str, int]) -> dict[str, int]:
    return {
        "missing-mission-runtime-bundle": metrics["missingMissionBundle"] * 100,
        "levelscript-control-flow": (
            metrics["untypedMultiSceneLevelscriptContexts"] * 10
            + metrics["actionableWeakOnlyScenes"] * 4
        ),
        "source-cycle-review": metrics["sourceCycles"] * 20 + metrics["cycleScenes"] * 8,
        "quest-scene-attachment": metrics["questIdsWithoutStrictStoryAttachment"] * 3,
        "dialog-option-runtime": (
            metrics["actionableNoExplicitOptionRouteGroups"] * 2
            + metrics["actionableExcludedOptionEvidenceGroups"] * 2
        ),
        "unresolved-source-node": metrics["unresolvedSourceNodes"] * 4,
        "isolated-scene-source-link":
            metrics["actionableCoreIsolatedScenes"] * 5,
    }


def _flow_story_connections(flow: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        row
        for row in flow.get("missionStoryConnections") or []
        if isinstance(row, dict)
    ]
    rows.extend(
        row
        for quest in flow.get("quests") or []
        if isinstance(quest, dict)
        for row in quest.get("storyConnections") or []
        if isinstance(row, dict)
    )
    for field in ("unlinkedNativePlayback", "unlinkedDefinitionOnly"):
        rows.extend(
            row
            for row in flow.get(field) or []
            if isinstance(row, dict)
        )
    return rows


def _closed_exact_native_unordered_scenes(
    flow: dict[str, Any],
    weak_only_scene_keys: set[str],
    native_playback_index: dict[str, list[dict[str, Any]]] | None = None,
    incident_levelscript_files: dict[str, set[str]] | None = None,
) -> tuple[list[dict[str, Any]], set[str]]:
    """Return unordered scenes whose native playback route is already exact.

    These rows do not lack LevelScript control-flow recovery. Their typed
    playback action is reached by a complete serialized event-to-action path,
    but that event supplies no prefix-comparable second Story action. File
    order, trigger-slot numbers, and OCR cannot fill that absence.
    """
    occurrence_fields = (
        "levelScriptOccurrences",
        "nativeOccurrences",
        "occurrences",
        "nativeBlackActionOccurrences",
        "parentDialogNativeOccurrences",
    )
    occurrences_by_scene: dict[str, dict[tuple[Any, ...], dict[str, Any]]] = (
        defaultdict(dict)
    )
    exact_stub_scopes: dict[str, set[tuple[str, str, str]]] = defaultdict(set)
    exact_control_path_statuses = {
        "exact_serialized_control_path",
        "exact_serialized_control_path_equivalent_duplicates",
    }
    for connection in _flow_story_connections(flow):
        scene_key = safe_key(connection.get("key"))
        if scene_key not in weak_only_scene_keys:
            continue
        for field in occurrence_fields:
            for occurrence in connection.get(field) or []:
                if not isinstance(occurrence, dict):
                    continue
                level_id = safe_key(occurrence.get("levelId"))
                script_id = safe_key(occurrence.get("scriptId"))
                source_file = safe_key(occurrence.get("sourceFile"))
                if any(
                    isinstance(owner, dict)
                    and owner.get("status") in exact_control_path_statuses
                    for owner in occurrence.get("nativeEventOwners") or []
                ):
                    exact_stub_scopes[scene_key].add(
                        (level_id, script_id, source_file)
                    )
                if (
                    not safe_key(occurrence.get("actionMapRole")).startswith(
                        "actionList#"
                    )
                    or not safe_key(occurrence.get("recordClass")).startswith(
                        "play_"
                    )
                    or not safe_key(occurrence.get("actionName"))
                ):
                    continue
                record_story_keys = _string_list(
                    occurrence.get("allStoryKeysInRecord")
                )
                if record_story_keys and scene_key not in record_story_keys:
                    continue
                signature = (
                    level_id,
                    script_id,
                    source_file,
                    occurrence.get("recordOffset"),
                    occurrence.get("localId"),
                )
                occurrences_by_scene[scene_key][signature] = occurrence

    incident_levelscript_files = incident_levelscript_files or {}
    for scene_key in weak_only_scene_keys:
        accepted_files = incident_levelscript_files.get(scene_key) or set()
        accepted_scopes = exact_stub_scopes.get(scene_key) or set()
        for occurrence in (native_playback_index or {}).get(scene_key) or []:
            if not isinstance(occurrence, dict):
                continue
            scope = (
                safe_key(occurrence.get("levelId")),
                safe_key(occurrence.get("scriptId")),
                safe_key(occurrence.get("sourceFile")),
            )
            if scope not in accepted_scopes and scope[2] not in accepted_files:
                continue
            signature = (
                *scope,
                occurrence.get("recordOffset"),
                occurrence.get("localId"),
            )
            occurrences_by_scene[scene_key][signature] = occurrence

    closed: list[dict[str, Any]] = []
    incomplete: set[str] = set()
    for scene_key in sorted(weak_only_scene_keys, key=natural_key):
        occurrences = list(occurrences_by_scene.get(scene_key, {}).values())
        if not occurrences:
            continue
        evidence: list[dict[str, Any]] = []
        complete = True
        for occurrence in occurrences:
            action_local_id = occurrence.get("localId")
            exact_owners = []
            for owner in occurrence.get("nativeEventOwners") or []:
                if (
                    not isinstance(owner, dict)
                    or owner.get("status") not in exact_control_path_statuses
                    or not isinstance(owner.get("headerLocalId"), int)
                ):
                    continue
                path_local_ids = [
                    step.get("localId")
                    for step in owner.get("path") or []
                    if isinstance(step, dict)
                    and isinstance(step.get("localId"), int)
                ]
                if (
                    not path_local_ids
                    or not isinstance(action_local_id, int)
                    or action_local_id not in path_local_ids
                ):
                    continue
                exact_owners.append((owner, path_local_ids))
            if not exact_owners:
                complete = False
                incomplete.add(scene_key)
                break
            for owner, path_local_ids in exact_owners:
                event_detail = (
                    owner.get("eventDetail")
                    if isinstance(owner.get("eventDetail"), dict)
                    else {}
                )
                evidence.append({
                    "levelId": safe_key(occurrence.get("levelId")),
                    "scriptId": safe_key(occurrence.get("scriptId")),
                    "sourceFile": safe_key(occurrence.get("sourceFile")),
                    "headerName": safe_key(owner.get("headerName")),
                    "headerLocalId": owner.get("headerLocalId"),
                    "controlPathStatus": safe_key(owner.get("status")),
                    "eventSummary": safe_key(event_detail.get("summary")),
                    "actionName": safe_key(occurrence.get("actionName")),
                    "actionLocalId": action_local_id,
                    "pathLocalIds": path_local_ids,
                })
        if complete and evidence:
            closed.append({
                "sceneKey": scene_key,
                "recoveryStatus":
                    "closed_exact_native_event_path_no_relative_order",
                "nativeEventPaths": evidence,
            })
            incomplete.discard(scene_key)
    return closed, incomplete


def _closed_non_mission_content_isolated_scenes(
    isolated_scene_keys: set[str],
    non_mission_content: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Keep exact authored non-mission content out of the narrative queue."""
    closed: list[dict[str, Any]] = []
    for scene_key in sorted(isolated_scene_keys, key=natural_key):
        row = non_mission_content.get(scene_key)
        if row is None:
            continue
        if row.get("evidenceKind") == "guide_runtime_asset":
            closed.append({
                "sceneKey": scene_key,
                "recoveryStatus":
                    "closed_exact_guide_runtime_non_mission_content",
                "evidenceKind": "guide_runtime_asset",
                "contentClass": row.get("content"),
                "assetType": row.get("assetType"),
                "consumerClass": row.get("consumerClass"),
                "assetCount": row.get("assetCount"),
                "actionCount": row.get("actionCount"),
                "assetNames": row.get("assetNames") or [],
                "guideLevelIds": row.get("guideLevelIds") or [],
                "nativeMappingId": row.get("nativeMappingId"),
                "nativeMethod": row.get("nativeMethod") or {},
                "orderBoundary": row.get("orderBoundary"),
                "evidenceReport": row.get("evidenceReport"),
            })
        else:
            closed.append({
                "sceneKey": scene_key,
                "recoveryStatus": "closed_table_backed_non_mission_content",
                "evidenceKind": "authored_table",
                "definitionTable": row["table"],
                "definitionField": row["field"],
                "tableKeyedBy": row["keyedBy"],
                "contentClass": row["content"],
            })
    return closed


def _closed_definition_only_isolated_scenes(
    flow: dict[str, Any],
    isolated_scene_keys: set[str],
) -> list[dict[str, Any]]:
    """Keep exact current-build no-consumer classifications out of the queue."""
    closed: list[dict[str, Any]] = []
    for row in flow.get("unlinkedDefinitionOnly") or []:
        if not isinstance(row, dict):
            continue
        scene_key = safe_key(row.get("key"))
        if (
            scene_key not in isolated_scene_keys
            or safe_key(row.get("relation"))
            != "original_text_definition_without_consumer"
            or safe_key(row.get("phase")) != "definition_only"
            or safe_key(row.get("confidence"))
            != "current_build_no_consumer"
            or safe_key(row.get("consumerSearchStatus"))
            != "no_current_original_game_consumer_recovered"
            or safe_key(row.get("bindingStatus"))
            != "definition_only_unlinked"
        ):
            continue
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus":
                "closed_current_build_definition_without_consumer",
            "source": safe_key(row.get("source")),
            "searchedConsumerKinds": _string_list(
                row.get("searchedConsumerKinds")
            ),
            "serverEvidenceStatus": safe_key(
                row.get("serverEvidenceStatus")
            ),
        })
    return sorted(closed, key=lambda row: natural_key(row["sceneKey"]))


def _closed_exact_dialog_tree_embedded_isolated_scenes(
    flow: dict[str, Any],
    isolated_scene_keys: set[str],
    owner_mission: str,
) -> list[dict[str, Any]]:
    """Close exact nested DialogTree text placement without a file edge.

    A narrative-mask Story file can be embedded between two trunk lines of
    its parent DialogTree. The typed serialized connection edges establish
    that line-level placement, but the parent file contains content both
    before and after the nested file. Treating that as ``parent -> child`` or
    ``child -> parent`` would therefore be false at scene-file granularity.
    """
    allowed_confidences = {
        "native_exact_parent_quest",
        "native_derived_exact_parent_quest",
        "native_derived_exact_parent_mission_area_shell",
        "native_derived_exact_parent_shell",
        "native_exact_parent_context",
    }
    allowed_evidence_tiers = {
        "native_direct",
        "derived_exact_quest",
        "derived_exact_shell",
        "native_direct_mission_context",
    }
    rows_by_scene: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _flow_story_connections(flow):
        scene_key = safe_key(row.get("key"))
        if (
            scene_key in isolated_scene_keys
            and safe_key(row.get("relation"))
            == "dialog_tree_narrative_action"
        ):
            rows_by_scene[scene_key].append(row)

    closed: list[dict[str, Any]] = []
    for scene_key, rows in rows_by_scene.items():
        exact_rows: list[dict[str, Any]] = []
        complete = True
        for row in rows:
            parent_story_key = safe_key(row.get("parentStoryKey"))
            occurrence_rows = [
                occurrence
                for occurrence in row.get("dialogTreeNarrativeActions") or []
                if isinstance(occurrence, dict)
            ]
            all_parent_story_keys = set(
                _string_list(row.get("allParentStoryKeys"))
            )
            if (
                not parent_story_key
                or safe_key(row.get("storyOwnerMission")) != owner_mission
                or safe_key(row.get("confidence")) not in allowed_confidences
                or safe_key(row.get("evidenceTier"))
                not in allowed_evidence_tiers
                or safe_key(row.get("scopeCompleteness")) != "complete"
                or row.get("unscopedParentStoryKeys")
                or parent_story_key not in all_parent_story_keys
                or safe_key(row.get("embeddedLinePlacementStatus"))
                != "exact_complete_connection_neighbors"
                or safe_key(row.get("nativeMappingId"))
                != DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID
                or not _string_list(row.get("embeddedAfterLineIds"))
                or not _string_list(row.get("embeddedBeforeLineIds"))
                or not occurrence_rows
                or int(row.get("occurrenceCount") or 0)
                != len(occurrence_rows)
            ):
                complete = False
                break
            for occurrence in occurrence_rows:
                if (
                    safe_key(occurrence.get("dialogKey"))
                    != parent_story_key
                    or safe_key(
                        occurrence.get(
                            "dialogTreeConnectionPlacementStatus"
                        )
                    )
                    != "exact_unique_adjacent_parent_trunks"
                    or safe_key(occurrence.get("nativeMappingId"))
                    != DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID
                    or occurrence.get("reachableFromPrimeNode") is not True
                    or not _string_list(
                        occurrence.get("primeToActionNodePath")
                    )
                    or not safe_key(occurrence.get("textId"))
                    or not safe_key(occurrence.get("actionPath"))
                    or not safe_key(occurrence.get("nodeId"))
                    or not safe_key(occurrence.get("sourceFile"))
                    or not _string_list(
                        occurrence.get("embeddedAfterLineIds")
                    )
                    or not _string_list(
                        occurrence.get("embeddedBeforeLineIds")
                    )
                ):
                    complete = False
                    break
            if not complete:
                break
            exact_rows.append(row)
        if not complete or not exact_rows:
            continue
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus":
                "closed_exact_native_embedded_line_context_no_file_order",
            "relation": "dialog_tree_narrative_action",
            "parentStoryKeys": sorted({
                safe_key(row.get("parentStoryKey"))
                for row in exact_rows
                if safe_key(row.get("parentStoryKey"))
            }, key=natural_key),
            "embeddedAfterLineIds": sorted({
                line_id
                for row in exact_rows
                for line_id in _string_list(
                    row.get("embeddedAfterLineIds")
                )
            }, key=natural_key),
            "embeddedBeforeLineIds": sorted({
                line_id
                for row in exact_rows
                for line_id in _string_list(
                    row.get("embeddedBeforeLineIds")
                )
            }, key=natural_key),
            "sourceFiles": sorted({
                source_file
                for row in exact_rows
                for source_file in _string_list(row.get("sourceFiles"))
            }),
            "sourcePathIds": sorted({
                path_id
                for row in exact_rows
                for path_id in _string_list(row.get("sourcePathIds"))
            }),
            "nativeMappingId":
                DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID,
            "orderBoundary": (
                "exact serialized line neighbors are retained, but the "
                "parent Story file has content on both sides and cannot be "
                "placed wholly before or after the nested file"
            ),
        })
    return sorted(closed, key=lambda row: natural_key(row["sceneKey"]))


def _closed_exact_dialog_tree_embedded_context_isolated_scenes(
    flow: dict[str, Any],
    isolated_scene_keys: set[str],
    owner_mission: str,
) -> list[dict[str, Any]]:
    """Close an exact nested playback consumer with unresolved line position.

    This is narrower than a recovered embedded line placement. Every serialized
    narrative action, source object, prime-node path, and parent Story scope
    must be exact and complete, but one or both adjacent parent trunk lines are
    still unavailable. That resolves the source-link/consumer gap only. It does
    not create a Story-file edge or claim an exact line position.
    """
    allowed_confidences = {
        "native_exact_parent_quest",
        "native_derived_exact_parent_quest",
        "native_derived_exact_parent_mission_area_shell",
        "native_derived_exact_parent_shell",
        "native_exact_parent_context",
    }
    allowed_evidence_tiers = {
        "native_direct",
        "derived_exact_quest",
        "derived_exact_shell",
        "native_direct_mission_context",
    }
    allowed_action_types = {
        "Beyond.Gameplay.DialogComplexNarrativeMaskActionData",
        "Beyond.Gameplay.DialogNarrativeMaskActionData",
    }
    allowed_action_kinds = {"complex_narrative", "narrative"}
    allowed_occurrence_placements = {
        "exact_unique_adjacent_parent_trunks",
        "no_exact_unique_adjacent_parent_trunks",
    }
    allowed_row_placements = {
        "exact_complete_connection_neighbors",
        "not_exact_complete_connection_neighbors",
    }
    rows_by_scene: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _flow_story_connections(flow):
        scene_key = safe_key(row.get("key"))
        if (
            scene_key in isolated_scene_keys
            and safe_key(row.get("relation"))
            == "dialog_tree_narrative_action"
        ):
            rows_by_scene[scene_key].append(row)

    closed: list[dict[str, Any]] = []
    for scene_key, rows in rows_by_scene.items():
        exact_rows: list[dict[str, Any]] = []
        unresolved_placements: list[dict[str, Any]] = []
        complete = True
        saw_unresolved_placement = False
        for row in rows:
            parent_story_key = safe_key(row.get("parentStoryKey"))
            occurrence_rows = [
                occurrence
                for occurrence in row.get("dialogTreeNarrativeActions") or []
                if isinstance(occurrence, dict)
            ]
            all_parent_story_keys = set(
                _string_list(row.get("allParentStoryKeys"))
            )
            row_placement = safe_key(
                row.get("embeddedLinePlacementStatus")
            )
            if (
                not parent_story_key
                or safe_key(row.get("storyOwnerMission")) != owner_mission
                or safe_key(row.get("confidence")) not in allowed_confidences
                or safe_key(row.get("evidenceTier"))
                not in allowed_evidence_tiers
                or safe_key(row.get("scopeCompleteness")) != "complete"
                or row.get("unscopedParentStoryKeys")
                or parent_story_key not in all_parent_story_keys
                or row_placement not in allowed_row_placements
                or safe_key(row.get("nativeMappingId"))
                != DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID
                or not _string_list(row.get("sourceFiles"))
                or not _string_list(row.get("sourcePathIds"))
                or not occurrence_rows
                or int(row.get("occurrenceCount") or 0)
                != len(occurrence_rows)
            ):
                complete = False
                break
            if row_placement == "not_exact_complete_connection_neighbors":
                saw_unresolved_placement = True
            for occurrence in occurrence_rows:
                placement = safe_key(
                    occurrence.get(
                        "dialogTreeConnectionPlacementStatus"
                    )
                )
                if (
                    safe_key(occurrence.get("dialogKey"))
                    != parent_story_key
                    or safe_key(occurrence.get("actionType"))
                    not in allowed_action_types
                    or safe_key(occurrence.get("actionKind"))
                    not in allowed_action_kinds
                    or placement not in allowed_occurrence_placements
                    or safe_key(occurrence.get("nativeMappingId"))
                    != DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID
                    or occurrence.get("reachableFromPrimeNode") is not True
                    or not _string_list(
                        occurrence.get("primeToActionNodePath")
                    )
                    or not safe_key(occurrence.get("textId"))
                    or not safe_key(occurrence.get("actionPath"))
                    or not safe_key(occurrence.get("nodeId"))
                    or not safe_key(occurrence.get("sourceFile"))
                    or not safe_key(occurrence.get("sourcePathId"))
                ):
                    complete = False
                    break
                if placement == "no_exact_unique_adjacent_parent_trunks":
                    saw_unresolved_placement = True
                    unresolved_placements.append({
                        "parentStoryKey": parent_story_key,
                        "textId": safe_key(occurrence.get("textId")),
                        "actionType": safe_key(
                            occurrence.get("actionType")
                        ),
                        "actionPath": safe_key(
                            occurrence.get("actionPath")
                        ),
                        "nodeId": safe_key(occurrence.get("nodeId")),
                        "incomingNodeIds": _string_list(
                            occurrence.get("incomingNodeIds")
                        ),
                        "outgoingNodeIds": _string_list(
                            occurrence.get("outgoingNodeIds")
                        ),
                        "immediatelyPrecedingTrunkIds": _string_list(
                            occurrence.get(
                                "immediatelyPrecedingTrunkIds"
                            )
                        ),
                        "immediatelyFollowingTrunkIds": _string_list(
                            occurrence.get(
                                "immediatelyFollowingTrunkIds"
                            )
                        ),
                        "sourceFile": safe_key(
                            occurrence.get("sourceFile")
                        ),
                        "sourcePathId": safe_key(
                            occurrence.get("sourcePathId")
                        ),
                        "placementStatus": placement,
                    })
            if not complete:
                break
            exact_rows.append(row)
        if (
            not complete
            or not exact_rows
            or not saw_unresolved_placement
            or not unresolved_placements
        ):
            continue
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus": (
                "closed_exact_native_embedded_playback_context_"
                "line_position_unresolved_no_file_order"
            ),
            "relation": "dialog_tree_narrative_action",
            "parentStoryKeys": sorted({
                safe_key(row.get("parentStoryKey"))
                for row in exact_rows
                if safe_key(row.get("parentStoryKey"))
            }, key=natural_key),
            "sourceFiles": sorted({
                source_file
                for row in exact_rows
                for source_file in _string_list(row.get("sourceFiles"))
            }),
            "sourcePathIds": sorted({
                path_id
                for row in exact_rows
                for path_id in _string_list(row.get("sourcePathIds"))
            }),
            "unresolvedLinePlacements": sorted(
                unresolved_placements,
                key=lambda row: (
                    natural_key(row["parentStoryKey"]),
                    natural_key(row["textId"]),
                    natural_key(row["nodeId"]),
                ),
            ),
            "nativeMappingId":
                DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID,
            "linePlacementStatus":
                "exact_parent_playback_line_position_unresolved",
            "orderBoundary": (
                "the exact typed serialized playback consumer, source "
                "object, prime-node path, and parent Story scope are "
                "recovered; one or both adjacent parent trunk lines remain "
                "unknown, and no Story-file edge is emitted"
            ),
        })
    return sorted(closed, key=lambda row: natural_key(row["sceneKey"]))


def _closed_exact_runtime_config_isolated_scenes(
    flow: dict[str, Any],
    isolated_scene_keys: set[str],
    owner_mission: str,
) -> list[dict[str, Any]]:
    """Close exact executable Story configs that encode no chronology.

    ``NpcProxyEx`` rows are executable configuration, not loose name matches:
    the installed client selects ``exDatas[activeCondIndex - 1]`` and
    ``NpcInteractComponent`` reads that row's ``dialogId``.  The adjacent
    ``missionId`` is consumed separately by the paused-mission deactivation
    guard.  This establishes a mission-scoped, selectable interaction dialog,
    but the server-selected row index and proxy/table ordering do not establish
    relative Story order.

    Counted LevelScript interactive maps are similarly exact: a typed
    ``LevelInteractiveData`` record's component-94 ``type_id`` selects one
    dialog or ReadingPopUp Story file. This recovers the source script and
    interactive identity, but neither map/local-id order nor object placement
    establishes activation timing or relative Story order.
    """
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _flow_story_connections(flow):
        scene_key = safe_key(row.get("key"))
        mission_id = safe_key(row.get("npcProxyMissionId"))
        if (
            scene_key not in isolated_scene_keys
            or safe_key(row.get("relation"))
            != "npc_proxy_ex_mission_context"
            or safe_key(row.get("confidence")) != "direct_mission_scope"
            or safe_key(row.get("source"))
            != "NpcProxyExDataTable.data[*].missionId + dialogId"
            or not safe_key(row.get("npcProxyId"))
            or not mission_id
            or mission_id != owner_mission
            or safe_key(row.get("storyOwnerMission")) != mission_id
            or safe_key(row.get("nativeMappingId"))
            != NPC_PROXY_DIALOG_SELECTION_MAPPING_ID
            or safe_key(row.get("gameAssemblySha256"))
            != NPC_PROXY_DIALOG_SELECTION_GAMEASSEMBLY_SHA256
            or safe_key(row.get("selectionOrderStatus"))
            != (
                "one_based_active_row_selection_only_no_cross_row_"
                "chronology"
            )
        ):
            continue
        grouped[scene_key].append(row)

    closed: list[dict[str, Any]] = []
    for scene_key, rows in grouped.items():
        mission_ids = {
            safe_key(row.get("npcProxyMissionId"))
            for row in rows
            if safe_key(row.get("npcProxyMissionId"))
        }
        mapping_ids = {
            safe_key(row.get("nativeMappingId"))
            for row in rows
            if safe_key(row.get("nativeMappingId"))
        }
        hashes = {
            safe_key(row.get("gameAssemblySha256"))
            for row in rows
            if safe_key(row.get("gameAssemblySha256"))
        }
        if (
            len(mission_ids) != 1
            or mapping_ids != {NPC_PROXY_DIALOG_SELECTION_MAPPING_ID}
            or hashes
            != {NPC_PROXY_DIALOG_SELECTION_GAMEASSEMBLY_SHA256}
        ):
            continue
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus":
                "closed_exact_runtime_config_no_relative_order",
            "relation": "npc_proxy_ex_mission_context",
            "missionId": next(iter(mission_ids)),
            "npcProxyIds": sorted({
                safe_key(row.get("npcProxyId"))
                for row in rows
                if safe_key(row.get("npcProxyId"))
            }, key=natural_key),
            "selectionSemantics":
                "exDatas[activeCondIndex - 1].dialogId",
            "orderBoundary": (
                "activeCondIndex selects one proxy row; neither row index, "
                "proxy suffix, table order, nor adjacent missionId orders "
                "Story files"
            ),
            "upstreamServerStateSources": [
                "SC_NPC_ENTER_MAP_RESYNC",
                "SC_NPC_ACTIVE_CHANGE_NTF",
            ],
            "serverFields": [
                "proxyNumId",
                "metaKvs",
                "activeCondIndex",
            ],
            "nativeConsumers": [{
                "method":
                    "NpcInteractComponent._TryGetNpcProxyInteractDialogId",
                "token": "0x06011381",
                "address": "0x183564080",
            }, {
                "method": "NpcProxy._IsMissionConflict",
                "token": "0x060131f4",
                "address": "0x18706ac74",
            }],
            "nativeMappingId": next(iter(mapping_ids)),
            "gameAssemblySha256": next(iter(hashes)),
        })
    already_closed = {row["sceneKey"] for row in closed}
    interactive_grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    expected_source = (
        "exact counted LevelScriptData interactive map -> 25-member "
        "LevelInteractiveData -> componentProperties[94].type_id; "
        "ReadingPopUpTable is joined only when TYPE_ID names a popup row"
    )
    expected_order_boundary = (
        "interactive-map order, local interactive id, object position, "
        "and Story suffix do not establish relative Story chronology"
    )
    for row in _flow_story_connections(flow):
        scene_key = safe_key(row.get("key"))
        level_ids = _string_list(row.get("levelIds"))
        script_ids = _string_list(row.get("scriptIds"))
        entity_details = _string_list(row.get("entityDetailIds"))
        template_ids = _string_list(row.get("entityTemplateIds"))
        local_id = row.get("localInteractiveId")
        if (
            scene_key in already_closed
            or scene_key not in isolated_scene_keys
            or safe_key(row.get("relation"))
            != "levelscript_interactive_narrative_config"
            or safe_key(row.get("confidence"))
            != "native_exact_serialized_config"
            or safe_key(row.get("source")) != expected_source
            or safe_key(row.get("storyOwnerMission")) != owner_mission
            or row.get("storyBinding") is not True
            or row.get("ownership") is not False
            or safe_key(row.get("nativeMappingId"))
            != LEVELSCRIPT_INTERACTIVE_NARRATIVE_MAPPING_ID
            or safe_key(row.get("orderBoundary"))
            != expected_order_boundary
            or len(level_ids) != 1
            or len(script_ids) != 1
            or len(entity_details) != 1
            or len(template_ids) != 1
            or not template_ids[0].startswith("int_narrative")
            or not isinstance(local_id, int)
            or isinstance(local_id, bool)
            or local_id <= 0
            or row.get("narrativeComponentKey") != 94
            or not isinstance(row.get("interactiveMapCount"), int)
            or int(row.get("interactiveMapCount") or 0) <= 0
        ):
            continue
        interactive_grouped[scene_key].append(row)

    for scene_key, rows in interactive_grouped.items():
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus":
                "closed_exact_runtime_config_no_relative_order",
            "relation": "levelscript_interactive_narrative_config",
            "missionId": owner_mission,
            "levelIds": sorted({
                level_id
                for row in rows
                for level_id in _string_list(row.get("levelIds"))
            }, key=natural_key),
            "scriptIds": sorted({
                script_id
                for row in rows
                for script_id in _string_list(row.get("scriptIds"))
            }, key=natural_key),
            "localInteractiveIds": sorted({
                int(row["localInteractiveId"])
                for row in rows
            }),
            "entityDetailIds": sorted({
                detail
                for row in rows
                for detail in _string_list(row.get("entityDetailIds"))
            }, key=natural_key),
            "entityTemplateIds": sorted({
                template
                for row in rows
                for template in _string_list(row.get("entityTemplateIds"))
            }, key=natural_key),
            "rawTypeIds": sorted({
                safe_key(row.get("rawTypeId"))
                for row in rows
                if safe_key(row.get("rawTypeId"))
            }, key=natural_key),
            "storyKeyResolutions": sorted({
                safe_key(row.get("storyKeyResolution"))
                for row in rows
                if safe_key(row.get("storyKeyResolution"))
            }),
            "questContextIds": sorted({
                quest_id
                for row in rows
                for quest_id in _string_list(row.get("questContextIds"))
            }, key=natural_key),
            "sourceFiles": sorted({
                source_file
                for row in rows
                for source_file in _string_list(row.get("sourceFiles"))
            }),
            "nativeConsumer": (
                "NarrativeComponent.ClientCollectNarrative -> "
                "_CollectNarrative -> dialog/reading-popup dispatch"
            ),
            "nativeMappingId":
                LEVELSCRIPT_INTERACTIVE_NARRATIVE_MAPPING_ID,
            "activationBoundary": (
                "the source LevelScript and local interactive are exact; "
                "serialized data does not establish when the script becomes "
                "active or when the player performs the interaction"
            ),
            "orderBoundary": expected_order_boundary,
        })
    already_closed.update(row["sceneKey"] for row in closed)
    leveldata_grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    leveldata_source = (
        "exact counted LevelData interactive list -> next-record-bounded "
        "25-member LevelInteractiveData -> "
        "componentProperties[94].type_id; the final unbounded list item is "
        "excluded"
    )
    leveldata_order_boundary = (
        "interactive-list order, record index, entity logic id, object "
        "position, and Story suffix do not establish relative Story chronology"
    )
    for row in _flow_story_connections(flow):
        scene_key = safe_key(row.get("key"))
        level_ids = _string_list(row.get("levelIds"))
        asset_ids = _string_list(row.get("levelDataAssets"))
        entity_details = _string_list(row.get("entityDetailIds"))
        template_ids = _string_list(row.get("entityTemplateIds"))
        record_index = row.get("interactiveRecordIndex")
        record_offset = row.get("interactiveRecordOffset")
        record_end = row.get("interactiveRecordEndOffset")
        list_count = row.get("interactiveListCount")
        entity_logic_id = row.get("entityLogicId")
        if (
            scene_key in already_closed
            or scene_key not in isolated_scene_keys
            or safe_key(row.get("relation"))
            != "leveldata_interactive_narrative_config"
            or safe_key(row.get("confidence"))
            != "native_exact_serialized_config"
            or safe_key(row.get("source")) != leveldata_source
            or safe_key(row.get("storyOwnerMission")) != owner_mission
            or row.get("storyBinding") is not True
            or row.get("ownership") is not False
            or safe_key(row.get("nativeMappingId"))
            != LEVELDATA_INTERACTIVE_NARRATIVE_MAPPING_ID
            or safe_key(row.get("orderBoundary"))
            != leveldata_order_boundary
            or len(level_ids) != 1
            or len(asset_ids) != 1
            or len(entity_details) != 1
            or len(template_ids) != 1
            or not template_ids[0].startswith("int_narrative")
            or not isinstance(record_index, int)
            or isinstance(record_index, bool)
            or record_index < 0
            or not isinstance(list_count, int)
            or isinstance(list_count, bool)
            or list_count <= record_index + 1
            or not isinstance(record_offset, int)
            or not isinstance(record_end, int)
            or record_offset < 0
            or record_end <= record_offset
            or not isinstance(entity_logic_id, int)
            or isinstance(entity_logic_id, bool)
            or entity_logic_id <= 0
            or row.get("narrativeComponentKey") != 94
        ):
            continue
        leveldata_grouped[scene_key].append(row)

    for scene_key, rows in leveldata_grouped.items():
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus":
                "closed_exact_runtime_config_no_relative_order",
            "relation": "leveldata_interactive_narrative_config",
            "missionId": owner_mission,
            "levelIds": sorted({
                value
                for row in rows
                for value in _string_list(row.get("levelIds"))
            }, key=natural_key),
            "levelDataAssets": sorted({
                value
                for row in rows
                for value in _string_list(row.get("levelDataAssets"))
            }, key=natural_key),
            "interactiveRecordIndexes": sorted({
                int(row["interactiveRecordIndex"])
                for row in rows
            }),
            "entityLogicIds": sorted({
                int(row["entityLogicId"])
                for row in rows
            }),
            "entityDetailIds": sorted({
                value
                for row in rows
                for value in _string_list(row.get("entityDetailIds"))
            }, key=natural_key),
            "entityTemplateIds": sorted({
                value
                for row in rows
                for value in _string_list(row.get("entityTemplateIds"))
            }, key=natural_key),
            "rawTypeIds": sorted({
                safe_key(row.get("rawTypeId"))
                for row in rows
                if safe_key(row.get("rawTypeId"))
            }, key=natural_key),
            "storyKeyResolutions": sorted({
                safe_key(row.get("storyKeyResolution"))
                for row in rows
                if safe_key(row.get("storyKeyResolution"))
            }),
            "sourceFiles": sorted({
                source_file
                for row in rows
                for source_file in _string_list(row.get("sourceFiles"))
            }),
            "nativeConsumer": (
                "NarrativeComponent.ClientCollectNarrative -> "
                "_CollectNarrative -> dialog/reading-popup dispatch"
            ),
            "nativeMappingId":
                LEVELDATA_INTERACTIVE_NARRATIVE_MAPPING_ID,
            "activationBoundary": (
                "the LevelData asset and narrative interactive are exact; "
                "serialized data does not establish availability, player "
                "interaction timing, or mission/quest activation"
            ),
            "orderBoundary": leveldata_order_boundary,
        })
    return sorted(closed, key=lambda row: natural_key(row["sceneKey"]))


def build_gap_row(
    partial_row: dict[str, Any],
    mission_payload: dict[str, Any] | None,
    *,
    mission_bundle_exists: bool,
    native_playback_index: dict[str, list[dict[str, Any]]] | None = None,
    action_story_occurrences: dict[str, list[dict[str, Any]]] | None = None,
    non_mission_content: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    non_mission_content = non_mission_content or {}
    mission = safe_key(partial_row.get("mission"))
    summary = partial_row.get("summary") if isinstance(partial_row.get("summary"), dict) else {}
    timeline = _timeline(mission_payload)
    flow = _flow(mission_payload)
    candidate_scene_keys = {
        safe_key(node.get("key"))
        for node in partial_row.get("nodes") or []
        if isinstance(node, dict) and safe_key(node.get("key"))
    }

    quest_ids = {
        safe_key(row.get("questId"))
        for row in timeline.get("quests") or []
        if isinstance(row, dict) and safe_key(row.get("questId"))
    }
    strict_quest_ids, strict_quest_scenes = _strict_quest_attachments(partial_row)
    diagnostic_quest_ids, diagnostic_quest_scenes, diagnostic_source_counts = (
        _diagnostic_quest_attachments(timeline, candidate_scene_keys)
    )
    missing_strict_quest_ids = sorted(
        (quest_ids & diagnostic_quest_ids) - strict_quest_ids,
        key=natural_key,
    )
    quest_ids_without_story_evidence = sorted(
        quest_ids - strict_quest_ids - diagnostic_quest_ids,
        key=natural_key,
    )
    raw_context_gaps = _levelscript_context_gaps(
        timeline,
        flow,
        native_playback_index,
    )
    context_gaps, closed_context_gaps = _classify_levelscript_context_gaps(
        raw_context_gaps,
        action_story_occurrences,
    )
    cycle_scenes = sorted({
        scene_key
        for cycle in partial_row.get("cycles") or []
        if isinstance(cycle, dict)
        for scene_key in _string_list(cycle.get("sceneKeys"))
    }, key=natural_key)
    unresolved_kinds = Counter(
        safe_key(row.get("kind")) or "unknown"
        for row in timeline.get("unresolved") or []
        if isinstance(row, dict)
    )
    node_kind_by_key = {
        safe_key(node.get("key")): safe_key(node.get("kind")) or "unknown"
        for node in partial_row.get("nodes") or []
        if isinstance(node, dict) and safe_key(node.get("key"))
    }
    isolated_scene_keys = _string_list(partial_row.get("isolatedSceneKeys"))
    if not isolated_scene_keys:
        isolated_scene_keys = [
            safe_key(node.get("key"))
            for node in partial_row.get("nodes") or []
            if isinstance(node, dict) and safe_key(node.get("relationStatus")) == "isolated"
        ]
    isolated_kinds = Counter(node_kind_by_key.get(key, "unknown") for key in isolated_scene_keys)
    core_isolated_scene_keys = [
        key
        for key in isolated_scene_keys
        if node_kind_by_key.get(key, "unknown") in CORE_STORY_NODE_KINDS
    ]
    (
        closed_exact_native_isolated,
        _incomplete_native_isolated_keys,
    ) = _closed_exact_native_unordered_scenes(
        flow,
        set(isolated_scene_keys),
        native_playback_index,
    )
    closed_exact_native_isolated_by_key = {
        row["sceneKey"]: row
        for row in closed_exact_native_isolated
    }
    for row in _closed_exact_dialog_tree_embedded_isolated_scenes(
        flow,
        set(isolated_scene_keys),
        safe_key(partial_row.get("mission")),
    ):
        closed_exact_native_isolated_by_key.setdefault(
            row["sceneKey"],
            row,
        )
    for row in _closed_exact_dialog_tree_embedded_context_isolated_scenes(
        flow,
        set(isolated_scene_keys),
        safe_key(partial_row.get("mission")),
    ):
        closed_exact_native_isolated_by_key.setdefault(
            row["sceneKey"],
            row,
        )
    closed_exact_native_isolated = sorted(
        closed_exact_native_isolated_by_key.values(),
        key=lambda row: natural_key(row["sceneKey"]),
    )
    closed_exact_native_isolated_keys = {
        row["sceneKey"]
        for row in closed_exact_native_isolated
    }
    closed_exact_runtime_config_isolated = (
        _closed_exact_runtime_config_isolated_scenes(
            flow,
            set(isolated_scene_keys),
            safe_key(partial_row.get("mission")),
        )
    )
    closed_exact_runtime_config_isolated_keys = {
        row["sceneKey"]
        for row in closed_exact_runtime_config_isolated
    }
    closed_definition_only_isolated = (
        _closed_definition_only_isolated_scenes(
            flow,
            set(isolated_scene_keys),
        )
    )
    closed_definition_only_isolated_keys = {
        row["sceneKey"]
        for row in closed_definition_only_isolated
    }
    closed_non_mission_content_isolated = (
        _closed_non_mission_content_isolated_scenes(
            set(isolated_scene_keys),
            non_mission_content,
        )
    )
    closed_non_mission_content_isolated_keys = {
        row["sceneKey"]
        for row in closed_non_mission_content_isolated
    }
    actionable_core_isolated_scene_keys = [
        key
        for key in core_isolated_scene_keys
        if key not in closed_exact_native_isolated_keys
        and key not in closed_exact_runtime_config_isolated_keys
        and key not in closed_definition_only_isolated_keys
        and key not in closed_non_mission_content_isolated_keys
    ]
    weak_only_scene_keys = set(
        _string_list(partial_row.get("weakOnlySceneKeys"))
    )
    incident_levelscript_files: dict[str, set[str]] = defaultdict(set)
    for edge in partial_row.get("directEdges") or []:
        if (
            not isinstance(edge, dict)
            or not safe_key(edge.get("kind")).startswith("levelscript")
        ):
            continue
        source_files = set(_string_list(edge.get("sourceFiles")))
        for field in ("from", "to"):
            scene_key = safe_key(edge.get(field))
            if scene_key in weak_only_scene_keys:
                incident_levelscript_files[scene_key].update(source_files)
    (
        closed_exact_native_weak_only,
        incomplete_native_weak_only_keys,
    ) = _closed_exact_native_unordered_scenes(
        flow,
        weak_only_scene_keys,
        native_playback_index,
        incident_levelscript_files,
    )
    closed_exact_native_weak_only_keys = {
        row["sceneKey"]
        for row in closed_exact_native_weak_only
    }
    actionable_weak_only_keys = set(incomplete_native_weak_only_keys)
    for scene_key in weak_only_scene_keys - closed_exact_native_weak_only_keys:
        accepted_files = incident_levelscript_files.get(scene_key) or set()
        for occurrence in (action_story_occurrences or {}).get(scene_key) or []:
            if not isinstance(occurrence, dict):
                continue
            source_file = safe_key(occurrence.get("sourceFile"))
            if not accepted_files or source_file not in accepted_files:
                continue
            if not safe_key(occurrence.get("actionMapRole")).startswith(
                "actionList#"
            ):
                continue
            record_class = safe_key(occurrence.get("recordClass"))
            action_name = safe_key(occurrence.get("actionName"))
            if not record_class or not action_name:
                mapped = KNOWN_NON_PLAYBACK_ACTIONS.get((
                    safe_key(occurrence.get("actionCode")).lower(),
                    safe_key(occurrence.get("actionKind")).lower(),
                ))
                if mapped:
                    action_name, record_class = mapped
            if record_class and action_name and not record_class.startswith(
                "play_"
            ):
                continue
            actionable_weak_only_keys.add(scene_key)
            break
    actionable_weak_only_scene_keys = sorted(
        actionable_weak_only_keys,
        key=natural_key,
    )
    non_actionable_weak_only_scene_keys = sorted(
        weak_only_scene_keys
        - closed_exact_native_weak_only_keys
        - actionable_weak_only_keys,
        key=natural_key,
    )

    metrics = {
        "missingMissionBundle": 0 if mission_bundle_exists else 1,
        "sceneCount": int(summary.get("sceneCount") or 0),
        "strongEdgeCount": int(summary.get("strongEdgeCount") or 0),
        "reducedComponentEdgeCount": int(summary.get("reducedComponentEdgeCount") or 0),
        "comparableScenePairs": int(summary.get("comparableScenePairs") or 0),
        "totalScenePairs": int(summary.get("totalScenePairs") or 0),
        "isolatedScenes": int(summary.get("isolatedSceneCount") or 0),
        "coreIsolatedScenes": len(core_isolated_scene_keys),
        "actionableCoreIsolatedScenes": len(
            actionable_core_isolated_scene_keys
        ),
        "closedExactNativeIsolatedScenes": len(
            closed_exact_native_isolated_keys
        ),
        "closedExactRuntimeConfigIsolatedScenes": len(
            closed_exact_runtime_config_isolated_keys
        ),
        "closedDefinitionOnlyIsolatedScenes": len(
            closed_definition_only_isolated_keys
        ),
        "closedNonMissionContentIsolatedScenes": len(
            closed_non_mission_content_isolated_keys
        ),
        "weakOnlyScenes": int(summary.get("weakOnlySceneCount") or 0),
        "actionableWeakOnlyScenes": len(actionable_weak_only_scene_keys),
        "closedExactNativeWeakOnlyScenes": len(
            closed_exact_native_weak_only_keys
        ),
        "nonActionableWeakOnlyScenes": len(
            non_actionable_weak_only_scene_keys
        ),
        "sourceCycles": int(summary.get("cycleCount") or 0),
        "cycleScenes": len(cycle_scenes),
        "unresolvedSourceNodes": len(partial_row.get("unresolvedSourceNodes") or []),
        "untypedMultiSceneLevelscriptContexts": len(context_gaps),
        "closedNonPlaybackLevelscriptContexts": len(closed_context_gaps),
        "questCount": len(quest_ids),
        "strictQuestAttachedSceneCount": len(strict_quest_scenes),
        "strictQuestIdsWithStoryAttachment": len(quest_ids & strict_quest_ids),
        "questIdsWithoutStrictStoryAttachment": len(missing_strict_quest_ids),
        "questIdsWithoutAnyStoryEvidence": len(quest_ids_without_story_evidence),
        "diagnosticQuestAttachedSceneCount": len(diagnostic_quest_scenes),
        "diagnosticQuestIdsWithStoryAttachment": len(quest_ids & diagnostic_quest_ids),
        "questForks": int(summary.get("questForkCount") or 0),
        "questMerges": int(summary.get("questMergeCount") or 0),
        "strictDialogOptionGroups": int(summary.get("dialogLineOptionGroupCount") or 0),
        "noExplicitOptionRouteGroups": int(
            summary.get("noExplicitRouteGroupCount") or 0
        ),
        "actionableNoExplicitOptionRouteGroups": int(
            summary.get(
                "branchingNoExplicitRouteGroupCount",
                summary.get("noExplicitRouteGroupCount"),
            )
            or 0
        ),
        "singleOptionNoExplicitRouteGroups": int(
            summary.get("singleOptionNoExplicitRouteGroupCount") or 0
        ),
        "excludedOptionEvidenceGroups": int(
            summary.get("excludedDialogLineOptionGroupCount") or 0
        ),
        "actionableExcludedOptionEvidenceGroups": int(
            summary.get(
                "actionableExcludedDialogLineOptionGroupCount",
                summary.get("excludedDialogLineOptionGroupCount"),
            )
            or 0
        ),
        "closedExcludedOptionEvidenceGroups": int(
            summary.get("closedExcludedDialogLineOptionGroupCount") or 0
        ),
        "timelineUnresolvedRecords": sum(unresolved_kinds.values()),
    }
    score_contributions = {
        key: metrics[key] * weight
        for key, weight in SCORE_WEIGHTS.items()
    }
    frontier_contributions = _frontier_contributions(metrics)
    active_frontiers = [
        frontier
        for frontier in FRONTIER_ORDER
        if frontier_contributions.get(frontier, 0) > 0
    ]
    primary_frontier = min(
        active_frontiers,
        key=lambda frontier: (
            -frontier_contributions[frontier],
            FRONTIER_ORDER.index(frontier),
        ),
        default="none",
    )

    return {
        "mission": mission,
        "bucket": _bucket(mission),
        "score": sum(score_contributions.values()),
        "scoreContributions": score_contributions,
        "frontierContributions": frontier_contributions,
        "primaryFrontier": primary_frontier,
        "activeFrontiers": active_frontiers,
        "metrics": metrics,
        "cycleSceneKeys": cycle_scenes,
        "coreIsolatedSceneKeys": core_isolated_scene_keys,
        "actionableCoreIsolatedSceneKeys":
            actionable_core_isolated_scene_keys,
        "closedExactNativeIsolatedScenes":
            closed_exact_native_isolated,
        "closedExactRuntimeConfigIsolatedScenes":
            closed_exact_runtime_config_isolated,
        "closedDefinitionOnlyIsolatedScenes":
            closed_definition_only_isolated,
        "closedNonMissionContentIsolatedScenes":
            closed_non_mission_content_isolated,
        "actionableWeakOnlySceneKeys": actionable_weak_only_scene_keys,
        "closedExactNativeWeakOnlyScenes": closed_exact_native_weak_only,
        "nonActionableWeakOnlySceneKeys":
            non_actionable_weak_only_scene_keys,
        "isolatedSceneKinds": dict(sorted(isolated_kinds.items())),
        "questIdsWithoutStrictStoryAttachment": missing_strict_quest_ids,
        "questIdsWithoutAnyStoryEvidence": quest_ids_without_story_evidence,
        "untypedMultiSceneLevelscriptContexts": context_gaps,
        "closedNonPlaybackLevelscriptContexts": closed_context_gaps,
        "timelineUnresolvedKinds": dict(sorted(unresolved_kinds.items())),
        "diagnosticQuestAttachmentSources": dict(sorted(diagnostic_source_counts.items())),
        "unresolvedSourceNodes": partial_row.get("unresolvedSourceNodes") or [],
    }


def build_gap_report(
    partial_report: dict[str, Any],
    mission_payloads: dict[str, dict[str, Any]],
    mission_bundle_presence: set[str],
    native_playback_index: dict[str, list[dict[str, Any]]] | None = None,
    action_story_occurrences: dict[str, list[dict[str, Any]]] | None = None,
    table_root: Path | None = None,
) -> dict[str, Any]:
    non_mission_content = (
        combined_non_mission_content_keys(table_root)
        if table_root is not None
        else {}
    )
    rows = [
        build_gap_row(
            row,
            mission_payloads.get(safe_key(row.get("mission"))),
            mission_bundle_exists=safe_key(row.get("mission")) in mission_bundle_presence,
            native_playback_index=native_playback_index,
            action_story_occurrences=action_story_occurrences,
            non_mission_content=non_mission_content,
        )
        for row in partial_report.get("missions") or []
        if isinstance(row, dict)
    ]
    rows.sort(key=lambda row: (
        BUCKET_ORDER.index(row["bucket"]),
        -row["score"],
        -row["metrics"]["sceneCount"],
        natural_key(row["mission"]),
    ))
    bucket_ranks: Counter[str] = Counter()
    for global_rank, row in enumerate(rows, start=1):
        bucket_ranks[row["bucket"]] += 1
        row["rank"] = global_rank
        row["bucketRank"] = bucket_ranks[row["bucket"]]

    bucket_totals: dict[str, Counter[str]] = {bucket: Counter() for bucket in BUCKET_ORDER}
    frontier_totals: dict[str, Counter[str]] = {bucket: Counter() for bucket in BUCKET_ORDER}
    for row in rows:
        bucket = row["bucket"]
        bucket_totals[bucket]["missions"] += 1
        bucket_totals[bucket]["score"] += row["score"]
        for key, value in row["metrics"].items():
            bucket_totals[bucket][key] += int(value)
        frontier_totals[bucket].update(row["frontierContributions"])

    return {
        "_schema": SCHEMA,
        "_generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "language": partial_report.get("language") or "",
        "sourcePartialOrderSchema": partial_report.get("_schema") or "",
        "rankingPolicy": {
            "bucketOrder": list(BUCKET_ORDER),
            "scoreWeights": SCORE_WEIGHTS,
            "frontierOrder": list(FRONTIER_ORDER),
            "note": "Triage score only; it does not assert scene chronology or evidence strength.",
        },
        "summary": {
            "missions": len(rows),
            "buckets": [
                {"bucket": bucket, **dict(bucket_totals[bucket])}
                for bucket in BUCKET_ORDER
            ],
            "frontierContributionsByBucket": {
                bucket: dict(frontier_totals[bucket])
                for bucket in BUCKET_ORDER
            },
        },
        "missions": rows,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Source-only Story Recovery Gap Queue",
        "",
        f"Generated: `{report['_generatedAt']}`",
        "",
        "This is a recovery-work queue, not a proposed Story order. Main-story (`e`)",
        "missions sort first. Every score contribution is preserved in the JSON.",
        "",
        "## Ranking Policy",
        "",
        "Bucket order: " + ", ".join(f"`{bucket}`" for bucket in BUCKET_ORDER) + ".",
        "",
        "Score weights: " + ", ".join(
            f"`{key}` x {weight}" for key, weight in SCORE_WEIGHTS.items()
        ) + ".",
        "",
        "## Bucket Summary",
        "",
        "| bucket | missions | score | scenes | isolated (core: actionable / native-closed / runtime-config-closed / definition-closed / non-mission-closed) | weak-only (actionable / exact-closed) | cycles | actionable LS gaps | closed LS negatives | actionable quest gaps | option gaps |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in report["summary"]["buckets"]:
        option_gaps = int(
            row.get("actionableNoExplicitOptionRouteGroups") or 0
        ) + int(
            row.get("actionableExcludedOptionEvidenceGroups") or 0
        )
        lines.append(
            f"| `{row['bucket']}` | {row.get('missions', 0)} | {row.get('score', 0)} | "
            f"{row.get('sceneCount', 0)} | {row.get('isolatedScenes', 0)} "
            f"({row.get('actionableCoreIsolatedScenes', 0)} / "
            f"{row.get('closedExactNativeIsolatedScenes', 0)} / "
            f"{row.get('closedExactRuntimeConfigIsolatedScenes', 0)} / "
            f"{row.get('closedDefinitionOnlyIsolatedScenes', 0)} / "
            f"{row.get('closedNonMissionContentIsolatedScenes', 0)}) | "
            f"{row.get('weakOnlyScenes', 0)} "
            f"({row.get('actionableWeakOnlyScenes', 0)} / "
            f"{row.get('closedExactNativeWeakOnlyScenes', 0)}) | "
            f"{row.get('sourceCycles', 0)} | "
            f"{row.get('untypedMultiSceneLevelscriptContexts', 0)} | "
            f"{row.get('closedNonPlaybackLevelscriptContexts', 0)} | "
            f"{row.get('questIdsWithoutStrictStoryAttachment', 0)} | {option_gaps} |"
        )

    lines.extend([
        "",
        "## Ranked Missions",
        "",
        "| rank | mission | bucket rank | score | scenes | isolated (core: actionable / native-closed / runtime-config-closed / definition-closed / non-mission-closed) | weak-only (actionable / exact-closed) | cycles | LS gaps | quest gaps | option gaps | primary frontier |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ])
    for row in report["missions"][:100]:
        metrics = row["metrics"]
        option_gaps = (
            metrics["actionableNoExplicitOptionRouteGroups"]
            + metrics["actionableExcludedOptionEvidenceGroups"]
        )
        lines.append(
            f"| {row['rank']} | `{md_escape(row['mission'])}` | {row['bucketRank']} | {row['score']} | "
            f"{metrics['sceneCount']} | {metrics['isolatedScenes']} "
            f"({metrics['actionableCoreIsolatedScenes']} / "
            f"{metrics['closedExactNativeIsolatedScenes']} / "
            f"{metrics['closedExactRuntimeConfigIsolatedScenes']} / "
            f"{metrics['closedDefinitionOnlyIsolatedScenes']} / "
            f"{metrics['closedNonMissionContentIsolatedScenes']}) | "
            f"{metrics['weakOnlyScenes']} "
            f"({metrics['actionableWeakOnlyScenes']} / "
            f"{metrics['closedExactNativeWeakOnlyScenes']}) | "
            f"{metrics['sourceCycles']} | {metrics['untypedMultiSceneLevelscriptContexts']} | "
            f"{metrics['questIdsWithoutStrictStoryAttachment']} | {option_gaps} | "
            f"`{row['primaryFrontier']}` |"
        )

    main_rows = [row for row in report["missions"] if row["bucket"] == "main"][:25]
    lines.extend([
        "",
        "## Main-story Frontier Detail",
        "",
    ])
    for row in main_rows:
        metrics = row["metrics"]
        lines.extend([
            f"### {row['bucketRank']}. `{md_escape(row['mission'])}`",
            "",
            f"Score `{row['score']}`; primary frontier `{row['primaryFrontier']}`. "
            f"Scenes `{metrics['sceneCount']}`, isolated `{metrics['isolatedScenes']}` "
            f"(`{metrics['actionableCoreIsolatedScenes']}` actionable core, "
            f"`{metrics['closedExactNativeIsolatedScenes']}` exact-native closed, "
            f"`{metrics['closedExactRuntimeConfigIsolatedScenes']}` "
            "exact runtime-config closed, "
            f"`{metrics['closedDefinitionOnlyIsolatedScenes']}` definition-only closed, "
            f"`{metrics['closedNonMissionContentIsolatedScenes']}` non-mission content closed), "
            f"weak-only `{metrics['weakOnlyScenes']}` "
            f"(`{metrics['actionableWeakOnlyScenes']}` actionable, "
            f"`{metrics['closedExactNativeWeakOnlyScenes']}` exact-native closed), "
            f"cycles `{metrics['sourceCycles']}`.",
            "",
            f"Quest ids without strict Story attachment: "
            f"`{metrics['questIdsWithoutStrictStoryAttachment']}`; untyped multi-scene "
            f"LevelScript contexts: `{metrics['untypedMultiSceneLevelscriptContexts']}`; "
            f"closed binary-negative contexts: "
            f"`{metrics['closedNonPlaybackLevelscriptContexts']}`; "
            f"actionable option gap groups: "
            f"`{metrics['actionableNoExplicitOptionRouteGroups'] + metrics['actionableExcludedOptionEvidenceGroups']}` "
            f"(`{metrics['singleOptionNoExplicitRouteGroups']}` single-option "
            f"acknowledgements and `{metrics['closedExcludedOptionEvidenceGroups']}` "
            "shared/cosmetic exclusions are retained but not scored).",
            "",
        ])
        contexts = row.get("untypedMultiSceneLevelscriptContexts") or []
        if contexts:
            lines.append("Top untyped LevelScript contexts:")
            lines.append("")
            for context in contexts[:5]:
                scenes = ", ".join(f"`{md_escape(key)}`" for key in context["sceneKeys"])
                lines.append(f"- `{md_escape(context['sourceFile'])}`: {scenes}")
            lines.append("")
        closed_contexts = row.get("closedNonPlaybackLevelscriptContexts") or []
        if closed_contexts:
            lines.append("Closed binary-negative LevelScript contexts:")
            lines.append("")
            for context in closed_contexts[:5]:
                classifications = ", ".join(
                    f"`{md_escape(item['sceneKey'])}` "
                    f"({md_escape(item['status'])})"
                    for item in context.get("unresolvedBinaryClassifications") or []
                )
                lines.append(
                    f"- `{md_escape(context['sourceFile'])}`: {classifications}"
                )
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", default="CN")
    parser.add_argument("--reports-dir", type=Path, default=ROOT / "reports" / "mission_order")
    parser.add_argument(
        "--table-root",
        type=Path,
        default=ROOT / "export_full" / "structured" / "StreamingAssets" / "Table",
        help="Authored table directory used to classify non-mission content "
             "keys out of the narrative queue.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    partial_report = build_partial_order_report(args.language)
    from story_builder.level_bindings import (  # noqa: PLC0415
        build_levelscript_action_story_occurrences,
        build_levelscript_native_story_playback_index,
    )

    action_story_occurrences = build_levelscript_action_story_occurrences()
    native_playback_index = build_levelscript_native_story_playback_index()
    mission_dir = ROOT / "webui" / "data" / "lang" / args.language / "mission"
    mission_payloads: dict[str, dict[str, Any]] = {}
    mission_bundle_presence: set[str] = set()
    for partial_row in partial_report.get("missions") or []:
        mission = safe_key(partial_row.get("mission"))
        path = mission_dir / f"{mission}.json"
        if not path.is_file():
            continue
        payload = read_json(path, {})
        mission_payloads[mission] = payload if isinstance(payload, dict) else {}
        mission_bundle_presence.add(mission)

    report = build_gap_report(
        partial_report,
        mission_payloads,
        mission_bundle_presence,
        native_playback_index,
        action_story_occurrences,
        table_root=args.table_root,
    )
    out_json = args.reports_dir / f"source_story_gap_queue_{args.language}.json"
    out_md = args.reports_dir / f"source_story_gap_queue_{args.language}.md"
    write_report_json(out_json, report)
    write_text_if_changed(out_md, render_markdown(report))
    main_rows = [row for row in report["missions"] if row["bucket"] == "main"]
    print(f"Source-only Story gap queue: {out_md.relative_to(ROOT)}")
    print(f"Source-only Story gap data: {out_json.relative_to(ROOT)}")
    if main_rows:
        print(
            f"Top main-story mission: {main_rows[0]['mission']} "
            f"score={main_rows[0]['score']} frontier={main_rows[0]['primaryFrontier']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
