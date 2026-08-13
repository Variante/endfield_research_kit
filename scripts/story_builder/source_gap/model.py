"""Gap closure classification, scoring, and report model construction."""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
from .foundation import (
    combined_non_mission_content_keys,
    read_json,
    safe_key,
)
from .contracts import (
    BUCKET_ORDER,
    FRONTIER_ORDER,
    LEVELDATA_INTERACTIVE_HORN_MAPPING_ID,
    LEVELDATA_INTERACTIVE_HORN_NATIVE_MAPPING_ID,
    LEVELDATA_INTERACTIVE_HORN_TEMPLATE_SHA256,
    LEVELDATA_INTERACTIVE_NARRATIVE_MAPPING_ID,
    LEVELSCRIPT_INTERACTIVE_NARRATIVE_MAPPING_ID,
    SCHEMA,
    SCORE_WEIGHTS,
    priority_bucket,
)
from ..level_bindings import (
    LEVELSCRIPT_NATIVE_ACTION_MAPPING_ID,
    LEVELSCRIPT_NATIVE_EXACT_CONTROL_PATH_STATUSES,
)
from ..anime_assets import (
    recover_dialog_tree_definition_evidence,
    recover_dialog_tree_prime_reachable_carriers_for_parent,
)
from ..mission_recovery import natural_key


from .data import (
    CORE_STORY_NODE_KINDS,
    KNOWN_NON_PLAYBACK_ACTIONS,
    KNOWN_NON_PLAYBACK_MAPPING_ID,
    NPC_PROXY_DIALOG_SELECTION_MAPPING_ID,
    NPC_PROXY_DIALOG_SELECTION_GAMEASSEMBLY_SHA256,
    DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID,
    OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256,
)

from .providers import (
    _build_mission_npc_proxy_tracking_index,
    _configured_game_assembly_path,
    _diagnostic_quest_attachments,
    _flow,
    _flow_story_connections,
    _generic_mission_npc_proxy_tracking_contexts,
    _generic_registered_dialog_tree_definition_facts,
    _merge_exact_interaction_trigger_with_native_playback,
    _repo_source_path,
    _sha256_file,
    _strict_quest_attachments,
    _string_list,
    _timeline,
)

@lru_cache(maxsize=1)
def _current_tracked_proxy_dialog_sources() -> dict[str, Any]:
    gameplay_root = (
        ROOT
        / "export_full"
        / "structured"
        / "StreamingAssets"
        / "Data"
        / "Json"
        / "GameplayConfig"
    )
    dialog_index_path = (
        ROOT / "export_full" / "recovered" / "dialog_id_table_index.json"
    )
    return {
        "trackingCorpus": _build_mission_npc_proxy_tracking_index(
            gameplay_root.parent / "MissionRuntimeAsset",
            ROOT
            / "export_full"
            / "structured"
            / "Persistent"
            / "Data"
            / "Json"
            / "MissionRuntimeAsset",
        ),
        "npcProxyTablePath": gameplay_root / "NpcProxyTable.json",
        "npcProxyTable": read_json(
            gameplay_root / "NpcProxyTable.json", {}
        ),
        "npcProxyExPath": gameplay_root / "NpcProxyExDataTable.json",
        "npcProxyEx": read_json(
            gameplay_root / "NpcProxyExDataTable.json", {}
        ),
        "dialogIdIndexPath": dialog_index_path,
        "dialogIdIndex": read_json(dialog_index_path, {}),
    }

def _validate_general_tracked_proxy_flow_context(
    row: Any,
    owner_mission: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Revalidate a generated shared-proxy relation against current sources."""
    story_key = safe_key(row.get("key")) if isinstance(row, dict) else ""
    proxy_id = safe_key(row.get("npcProxyId")) if isinstance(row, dict) else ""
    level_ids = _string_list(row.get("levelIds")) if isinstance(row, dict) else []
    sources = _current_tracked_proxy_dialog_sources()
    facts = {
        "npcProxyConsumers": [{
            "npcProxyId": proxy_id,
            "levelId": level_ids[0] if len(level_ids) == 1 else "",
        }],
    }
    contexts, tracking_failures = _generic_mission_npc_proxy_tracking_contexts(
        story_key,
        owner_mission,
        facts,
        sources["trackingCorpus"],
    )
    context = contexts[0] if len(contexts) == 1 else None
    proxy_rows = (sources["npcProxyTable"] or {}).get("dataTable") or {}
    ex_rows_by_proxy = (sources["npcProxyEx"] or {}).get("data") or {}
    current_proxy_row = proxy_rows.get(proxy_id)
    current_ex_rows = ex_rows_by_proxy.get(proxy_id)
    configured_dialog_ids = [
        safe_key(ex_row.get("dialogId"))
        for ex_row in (current_ex_rows or [])
        if isinstance(ex_row, dict) and safe_key(ex_row.get("dialogId"))
    ]
    active_row_index = row.get("activeRowIndex") if isinstance(row, dict) else None
    selected_dialog_id = ""
    if (
        isinstance(active_row_index, int)
        and not isinstance(active_row_index, bool)
        and isinstance(current_ex_rows, list)
        and 1 <= active_row_index <= len(current_ex_rows)
        and isinstance(current_ex_rows[active_row_index - 1], dict)
    ):
        selected_dialog_id = safe_key(
            current_ex_rows[active_row_index - 1].get("dialogId")
        )
    dialog_registry = sources["dialogIdIndex"]
    registrations_valid = bool(configured_dialog_ids) and all(
        isinstance(dialog_registry.get(dialog_id), dict)
        and dialog_registry[dialog_id].get("registered") is True
        and dialog_registry[dialog_id].get("memoryPackRecordKey") is True
        for dialog_id in configured_dialog_ids
    )
    expected_source_files = sorted({
        *(context.get("sourceFiles") or [] if context else []),
        _repo_source_path(sources["npcProxyTablePath"]),
        _repo_source_path(sources["npcProxyExPath"]),
        _repo_source_path(sources["dialogIdIndexPath"]),
    })
    source_files = sorted(_string_list(row.get("sourceFiles"))) if isinstance(row, dict) else []
    valid = (
        isinstance(row, dict)
        and safe_key(row.get("relation"))
        == "unique_mission_tracked_npc_proxy_dialog_context"
        and safe_key(row.get("direction")) == "context"
        and safe_key(row.get("phase")) == "server_selected_proxy_state"
        and safe_key(row.get("confidence")) == "native_exact_mission_context"
        and safe_key(row.get("evidenceTier")) == "derived_exact_mission"
        and safe_key(row.get("storyOwnerMission")) == owner_mission
        and context is not None
        and context.get("nominalMissionId") == owner_mission
        and _string_list(row.get("candidateQuestIds")) == context.get("questIds")
        and _string_list(row.get("configuredDialogIds")) == configured_dialog_ids
        and selected_dialog_id == story_key
        and isinstance(current_proxy_row, dict)
        and safe_key(current_proxy_row.get("proxyId")) == proxy_id
        and safe_key(current_proxy_row.get("levelId")) == context.get("levelId")
        and row.get("npcProxyTableRow") == {
            "proxyId": proxy_id,
            "levelId": context.get("levelId"),
            "subDataParentId": current_proxy_row.get("subDataParentId"),
        }
        and row.get("npcProxyExRows") == current_ex_rows
        and registrations_valid
        and source_files == expected_source_files
        and all((ROOT / source_file).is_file() for source_file in source_files)
        and row.get("storyBinding") is True
        and row.get("ownership") is False
        and row.get("questActivation") is False
        and row.get("questPlayback") is False
        and row.get("questCompletion") is False
        and safe_key(row.get("nativeMappingId"))
        == NPC_PROXY_DIALOG_SELECTION_MAPPING_ID
        and safe_key(row.get("gameAssemblySha256"))
        == NPC_PROXY_DIALOG_SELECTION_GAMEASSEMBLY_SHA256
    )
    if not valid:
        return None, {
            "validator": "generalTrackedNpcProxyDialogFlowContext",
            "gate": "exactCurrentSourceComposition",
            "mission": owner_mission,
            "storyKey": story_key,
            "npcProxyId": proxy_id,
            "sourcePaths": source_files or expected_source_files,
            "sourceSha256": {
                source_file: _sha256_file(ROOT / source_file)
                for source_file in source_files or expected_source_files
            },
            "expected": {
                "trackingContext": context,
                "configuredDialogIds": configured_dialog_ids,
                "selectedDialogId": story_key,
                "sourceFiles": expected_source_files,
                "registeredDialogRoots": True,
            },
            "actual": {
                "trackingFailures": tracking_failures,
                "trackingContext": context,
                "relation": safe_key(row.get("relation"))
                if isinstance(row, dict) else "",
                "direction": safe_key(row.get("direction"))
                if isinstance(row, dict) else "",
                "phase": safe_key(row.get("phase"))
                if isinstance(row, dict) else "",
                "storyOwnerMission": safe_key(row.get("storyOwnerMission"))
                if isinstance(row, dict) else "",
                "candidateQuestIds": _string_list(row.get("candidateQuestIds"))
                if isinstance(row, dict) else [],
                "configuredDialogIds": _string_list(row.get("configuredDialogIds"))
                if isinstance(row, dict) else [],
                "selectedDialogId": selected_dialog_id,
                "registeredDialogRoots": registrations_valid,
                "sourceFiles": source_files,
            },
        }
    return {
        **context,
        "storyKey": story_key,
        "activeRowIndex": active_row_index,
        "configuredDialogIds": configured_dialog_ids,
        "sourceFiles": source_files,
        "sourceSha256": {
            source_file: _sha256_file(ROOT / source_file)
            for source_file in source_files
        },
    }, None

def _bucket(mission: str) -> str:
    return priority_bucket(mission) or "other"

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

def _registered_parent_playback_routes_match(
    scene_key: str,
    owner_mission: str,
    evidence: dict[str, Any],
    routed_rows: list[dict[str, Any]],
) -> bool:
    """Accept only the flow aliases reproduced by exact parent playback.

    Story bundling may expose a played registered parent DialogTree under the
    emitted aggregate key whose table rows it carries. That positive alias is
    compatible with a graph-neutral trunk-group result, but only when every
    routed occurrence resolves back to the exact typed parent playback already
    validated from the bound SubGame LevelScript.
    """
    if safe_key(evidence.get("evidenceKind")) not in {
        "registered_dialog_tree_trunk_group_exact_line_partition",
        "partial_registered_dialog_tree_rows_without_current_consumer",
    }:
        return False
    expected_sources_by_parent: dict[str, set[str]] = defaultdict(set)
    for context in evidence.get("parentLevelContexts") or []:
        if not isinstance(context, dict):
            continue
        runtime = context.get("subGameRuntime")
        if not isinstance(runtime, dict):
            continue
        for playback in runtime.get("parentDialogPlayback") or []:
            if not isinstance(playback, dict):
                continue
            parent_key = safe_key(playback.get("parentDialogTreeId"))
            source_file = safe_key(playback.get("sourceFile"))
            if parent_key and source_file:
                expected_sources_by_parent[parent_key].add(source_file)
    observed: dict[str, set[str]] = defaultdict(set)
    if not routed_rows or not expected_sources_by_parent:
        return False
    for row in routed_rows:
        if (
            safe_key(row.get("key")) != scene_key
            or safe_key(row.get("relation"))
            != "native_story_playback_unscoped"
            or safe_key(row.get("confidence"))
            != "native_typed_direct_unscoped"
            or safe_key(row.get("storyOwnerMission")) != owner_mission
            or safe_key(row.get("questTriggerStatus")) != "unresolved"
        ):
            return False
        occurrences = [
            occurrence
            for occurrence in row.get("occurrences") or []
            if isinstance(occurrence, dict)
        ]
        if not occurrences:
            return False
        for occurrence in occurrences:
            parent_key = safe_key(occurrence.get("authoredStoryKey"))
            source_file = safe_key(occurrence.get("sourceFile"))
            if (
                parent_key not in expected_sources_by_parent
                or source_file not in expected_sources_by_parent[parent_key]
                or safe_key(occurrence.get("actionName"))
                != "StartDialogAction"
                or safe_key(occurrence.get("recordClass")) != "play_dialog"
            ):
                return False
            observed[parent_key].add(source_file)
    return observed == expected_sources_by_parent

def _connection_native_occurrences(
    connection: dict[str, Any],
    scene_key: str,
    occurrence_fields: tuple[str, ...],
) -> list[dict[str, Any]]:
    occurrences = [
        occurrence
        for field in occurrence_fields
        for occurrence in connection.get(field) or []
        if isinstance(occurrence, dict)
    ]
    if occurrences:
        return occurrences

    # Some stronger context rows compact one exact native path directly onto
    # the connection instead of repeating its lower-level occurrence record.
    # Reconstruct only the minimum occurrence shape needed by the closure
    # classifier, and only when the playback step itself carries this exact
    # Story key.
    level_ids = _string_list(connection.get("levelIds"))
    script_ids = _string_list(connection.get("scriptIds"))
    source_files = [
        source_file
        for source_file in _string_list(connection.get("sourceFiles"))
        if "/LevelScriptData/" in ("/" + source_file.replace("\\", "/"))
    ]
    if len(level_ids) != 1 or len(script_ids) != 1 or len(source_files) != 1:
        return []
    synthetic: list[dict[str, Any]] = []
    for owner in connection.get("nativeEventOwners") or []:
        if not isinstance(owner, dict):
            continue
        for step in owner.get("path") or []:
            if (
                not isinstance(step, dict)
                or not safe_key(step.get("recordClass")).startswith("play_")
                or not safe_key(step.get("actionName"))
                or scene_key not in _string_list(step.get("texts"))
                or not isinstance(step.get("localId"), int)
            ):
                continue
            synthetic.append({
                "levelId": level_ids[0],
                "scriptId": script_ids[0],
                "sourceFile": source_files[0],
                "actionMapRole": "actionList#exact-native-owner-path",
                "allStoryKeysInRecord": [scene_key],
                "localId": step["localId"],
                "actionName": safe_key(step.get("actionName")),
                "recordClass": safe_key(step.get("recordClass")),
                "nativeEventOwners": [owner],
            })
    return synthetic

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
    exact_control_path_statuses = LEVELSCRIPT_NATIVE_EXACT_CONTROL_PATH_STATUSES
    for connection in _flow_story_connections(flow):
        scene_key = safe_key(connection.get("key"))
        if scene_key not in weak_only_scene_keys:
            continue
        for occurrence in _connection_native_occurrences(
            connection,
            scene_key,
            occurrence_fields,
        ):
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

def _closed_exact_native_context_isolated_scenes(
    flow: dict[str, Any],
    isolated_scene_keys: set[str],
    owner_mission: str,
) -> list[dict[str, Any]]:
    """Close exact playback contexts that deliberately provide no chronology."""
    closed: list[dict[str, Any]] = []
    for connection in _flow_story_connections(flow):
        scene_key = safe_key(connection.get("key"))
        relation = safe_key(connection.get("relation"))
        if (
            scene_key not in isolated_scene_keys
            or safe_key(connection.get("storyOwnerMission")) != owner_mission
            or safe_key(connection.get("direction")) != "context"
        ):
            continue
        if relation == "cross_owner_levelscript_quest_playback_context":
            context_mission = safe_key(
                connection.get("contextMissionBundle")
            )
            context_quest = safe_key(connection.get("contextQuestId"))
            original = {
                **connection,
                "relation": safe_key(connection.get("originalRelation")),
                "direction": safe_key(connection.get("originalDirection")),
                "phase": safe_key(connection.get("originalPhase")),
            }
            valid, _failure = _exact_cross_owner_levelscript_quest_playback(
                original,
                owner_mission,
                context_mission,
                context_quest,
            )
            if not valid or connection.get("graphEffect") != "none":
                continue
            closed.append({
                "sceneKey": scene_key,
                "recoveryStatus":
                    "closed_exact_cross_mission_quest_playback_context_no_relative_order",
                "relation": relation,
                "originalRelation": safe_key(
                    connection.get("originalRelation")
                ),
                "nominalStoryMissionId": owner_mission,
                "contextMissionId": context_mission,
                "contextQuestId": context_quest,
                "questState": connection.get("questState"),
                "questStateName": safe_key(
                    connection.get("questStateName")
                ),
                "levelId": safe_key(connection.get("levelId")),
                "scriptId": safe_key(connection.get("scriptId")),
                "actionName": safe_key(connection.get("actionName")),
                "nativeMappingId": safe_key(
                    connection.get("nativeMappingId")
                ),
                "sourceFiles": _string_list(
                    connection.get("sourceFiles")
                ),
                "sourceSha256": connection.get("sourceSha256") or {},
                "orderBoundary": safe_key(connection.get("orderBoundary")),
            })
            continue
        if relation == "leveldata_levelscript_mission_context":
            context_mission = (
                safe_key(connection.get("contextMissionBundle"))
                or safe_key(connection.get("levelDataHostMissionId"))
            )
            if not _exact_leveldata_story_context(
                connection,
                owner_mission,
                context_mission,
            ):
                continue
            context_mismatch = context_mission != owner_mission
            closed.append({
                "sceneKey": scene_key,
                "recoveryStatus":
                    (
                        "closed_exact_cross_mission_leveldata_playback_"
                        "context_no_relative_order"
                        if context_mismatch
                        else "closed_exact_same_mission_leveldata_playback_"
                        "context_no_relative_order"
                    ),
                "relation": relation,
                "nominalStoryMissionId": owner_mission,
                "contextMissionId": context_mission,
                "contextMissionMismatch": context_mismatch,
                "levelIds": _string_list(connection.get("levelIds")),
                "scriptIds": _string_list(connection.get("scriptIds")),
                "sourceFiles": sorted(set(
                    _string_list(connection.get("sourceFiles"))
                    + _string_list(connection.get("levelDataFiles"))
                ), key=natural_key),
                "levelScriptOccurrences": list(
                    connection.get("levelScriptOccurrences") or []
                ),
                "activationBoundary": (
                    "the exact local native event reaches the typed playback "
                    "action and the validated LevelData dictionary scopes that "
                    f"script to the {context_mission} mission asset shell; the "
                    "event serializes no mission/quest id or server exchange"
                ),
                "orderBoundary": (
                    "mission-shell containment identifies the related original "
                    "files and exact local playback but does not identify a "
                    "quest trigger or establish relative Story chronology"
                ),
            })
            continue
        if relation == "authoritative_scope_leveldata_mission_context":
            context_mission = safe_key(
                connection.get("levelDataHostMissionId")
            )
            occurrences = [
                row for row in connection.get("levelScriptOccurrences") or []
                if isinstance(row, dict)
            ]
            exact_paths = []
            occurrence_hosts_valid = bool(occurrences)
            for occurrence in occurrences:
                owners = [
                    row for row in occurrence.get("nativeEventOwners") or []
                    if isinstance(row, dict)
                ]
                hosts = [
                    row for row in occurrence.get(
                        "authoritativeScopeLevelDataHosts"
                    ) or []
                    if isinstance(row, dict)
                ]
                exact_paths.extend(owners)
                if (
                    safe_key(occurrence.get("actionName")) != "PlayRadio"
                    or safe_key(occurrence.get("recordClass")) != "play_radio"
                    or scene_key not in _string_list(
                        occurrence.get("allStoryKeysInRecord")
                    )
                    or not owners
                    or any(
                        safe_key(owner.get("status"))
                        != "exact_serialized_control_path"
                        or safe_key(owner.get("headerName"))
                        != "EntityEvent_OnInteractiveStateChanged"
                        or not isinstance(owner.get("eventDetail"), dict)
                        or owner.get("eventDetail", {}).get(
                            "serializedMissionOrQuestId"
                        ) is not False
                        or owner.get("eventDetail", {}).get(
                            "serverExchange"
                        ) is not False
                        or not any(
                            isinstance(step, dict)
                            and safe_key(step.get("actionName")) == "PlayRadio"
                            and scene_key in _string_list(step.get("texts"))
                            for step in owner.get("path") or []
                        )
                        for owner in owners
                    )
                    or len(hosts) != 1
                    or hosts[0].get("status") != "unique"
                    or _string_list(hosts[0].get("hostMissionIds"))
                    != [context_mission]
                    or safe_key(hosts[0].get("levelDataFile"))
                    not in _string_list(connection.get("levelDataFiles"))
                    or hosts[0].get("dictionaryEntryCount")
                    not in (connection.get(
                        "levelDataDictionaryEntryCounts"
                    ) or [])
                    or safe_key(hosts[0].get(
                        "nativeSchema"
                    )) != (
                        "LevelData/43.member22:Dictionary<u64,"
                        "LevelScriptBriefData/8>"
                    )
                ):
                    occurrence_hosts_valid = False
                    break
            scope_references = [
                row for row in connection.get(
                    "authoritativeScopeReferences"
                ) or []
                if isinstance(row, dict)
            ]
            recognized_scope_kinds = {
                "typed_mission_runtime_script_condition",
                "typed_entity_tracking_registry_script",
            }
            if (
                safe_key(connection.get("phase")) != "runtime_playback"
                or safe_key(connection.get("confidence"))
                != "native_exact_validated_leveldata_shell"
                or safe_key(connection.get("evidenceTier"))
                != "derived_exact_shell"
                or not context_mission
                or context_mission == owner_mission
                or safe_key(connection.get("questTriggerStatus"))
                != "sibling_script_shell_context_not_playback"
                or safe_key(connection.get("executionSide")) != "client"
                or safe_key(connection.get("networkRole"))
                != "local_asset_shell_context"
                or connection.get("serverExchange") is not False
                or connection.get("occurrenceCount") != len(occurrences)
                or connection.get("allOccurrenceCount") != len(occurrences)
                or connection.get(
                    "hasUnscopedOrOtherMissionOccurrences"
                ) is not False
                or _string_list(connection.get("nativeActions"))
                != ["PlayRadio"]
                or not occurrence_hosts_valid
                or not exact_paths
                or not _string_list(connection.get("levelIds"))
                or not _string_list(connection.get("scriptIds"))
                or not _string_list(connection.get("sourceFiles"))
                or not _string_list(connection.get("levelDataFiles"))
                or not _string_list(connection.get("anchorQuestIds"))
                or any(
                    not quest_id.startswith(f"{context_mission}_q#")
                    for quest_id in _string_list(
                        connection.get("anchorQuestIds")
                    )
                )
                or not scope_references
                or set(_string_list(
                    connection.get("authoritativeScopeKinds")
                )) != recognized_scope_kinds
                or any(
                    safe_key(reference.get("missionId"))
                    != context_mission
                    or safe_key(reference.get("scopeKind"))
                    not in recognized_scope_kinds
                    or not safe_key(reference.get("sourceFile"))
                    for reference in scope_references
                )
            ):
                continue
            closed.append({
                "sceneKey": scene_key,
                "recoveryStatus":
                    "closed_exact_cross_mission_leveldata_shell_playback_context_no_relative_order",
                "relation": relation,
                "nominalStoryMissionId": owner_mission,
                "contextMissionId": context_mission,
                "contextMissionMismatch": True,
                "anchorQuestIds": _string_list(
                    connection.get("anchorQuestIds")
                ),
                "levelIds": _string_list(connection.get("levelIds")),
                "scriptIds": _string_list(connection.get("scriptIds")),
                "sourceFiles": sorted(set(
                    _string_list(connection.get("sourceFiles"))
                    + _string_list(connection.get("levelDataFiles"))
                ), key=natural_key),
                "nativeEventPaths": exact_paths,
                "activationBoundary": (
                    "the exact local entity-property event plays this radio, "
                    "while the validated LevelData dictionary scopes its "
                    f"script as a sibling in the {context_mission} runtime shell"
                ),
                "orderBoundary": (
                    "sibling containment and the shell's typed quest anchors "
                    "do not transfer Story ownership, identify a quest "
                    "trigger, or place this radio relative to other mission files"
                ),
            })
            continue
        if relation == "npc_proxy_segment_levelscript_mission_context":
            context_mission = (
                safe_key(connection.get("contextMissionBundle"))
                or owner_mission
            )
            native_owners = [
                row for row in connection.get("nativeEventOwners") or []
                if isinstance(row, dict)
            ]
            exact_paths = [
                row for row in native_owners
                if safe_key(row.get("status"))
                == "exact_serialized_control_path"
                and safe_key(row.get("headerName"))
                == "ScriptEvent_OnLeaderEnterTriggerVolume"
                and any(
                    isinstance(step, dict)
                    and safe_key(step.get("recordClass")).startswith("play_")
                    and scene_key in (
                        {
                            safe_key(text_id).rsplit("_", 1)[0]
                            for text_id in step.get("texts") or []
                            if safe_key(text_id)
                        }
                        if safe_key(step.get("recordClass")) == "play_black"
                        else set(_string_list(step.get("texts")))
                    )
                    for step in row.get("path") or []
                )
            ]
            if (
                safe_key(connection.get("confidence"))
                != "native_exact_npc_proxy_segment_shell"
                or safe_key(connection.get("evidenceTier"))
                != "derived_exact_shell"
                or safe_key(connection.get("questTriggerStatus"))
                != "same_authored_npc_proxy_segment_not_quest_playback"
                or safe_key(connection.get("executionSide")) != "client"
                or connection.get("serverExchange") is not False
                or not _string_list(connection.get("npcProxyIds"))
                or not _string_list(connection.get("segmentIdsGlobal"))
                or not _string_list(connection.get("candidateQuestIds"))
                or any(
                    not quest_id.startswith(f"{context_mission}_q#")
                    for quest_id in _string_list(
                        connection.get("candidateQuestIds")
                    )
                )
                or len(exact_paths) != len(native_owners)
                or not exact_paths
                or not _string_list(connection.get("sourceFiles"))
            ):
                continue
            closed.append({
                "sceneKey": scene_key,
                "recoveryStatus":
                    "closed_exact_npc_proxy_segment_playback_context_no_relative_order",
                "relation": relation,
                "nominalStoryMissionId": owner_mission,
                "contextMissionId": context_mission,
                "contextMissionMismatch": context_mission != owner_mission,
                "npcProxyIds": _string_list(connection.get("npcProxyIds")),
                "segmentIdsGlobal": _string_list(
                    connection.get("segmentIdsGlobal")
                ),
                "candidateQuestIds": _string_list(
                    connection.get("candidateQuestIds")
                ),
                "nativeEventPaths": exact_paths,
                "sourceFiles": _string_list(connection.get("sourceFiles")),
                "orderBoundary": (
                    "the exact tracked NpcProxy segment and serialized native "
                    "event path establish mission-shell playback context; they "
                    "do not identify one quest trigger or relative Story order"
                ),
            })
            continue
        if (
            connection.get("storyBinding") is not True
            or connection.get("ownership") is not False
        ):
            continue
        if relation == "radio_trigger_zone_mission_state_playback_context":
            gate_roles = set(_string_list(
                connection.get("missionStateGateRoles")
            ))
            roles_by_id = connection.get("missionStateRolesById")
            recognized_roles = {
                "hideAfterMissionId",
                "hideBeforeMissionId",
                "hideCompleteMissionId",
            }
            if (
                safe_key(connection.get("phase"))
                != "mission_state_trigger_zone"
                or safe_key(connection.get("confidence"))
                != "native_exact_serialized_co_carrier"
                or safe_key(connection.get("evidenceTier")) != "direct"
                or safe_key(connection.get("missionStateId"))
                != owner_mission
                or not gate_roles
                or not gate_roles.issubset(recognized_roles)
                or not isinstance(roles_by_id, dict)
                or set(_string_list(roles_by_id.get(owner_mission)))
                != gate_roles
                or any(
                    not safe_key(mission_id)
                    or not set(_string_list(roles)).issubset(
                        recognized_roles
                    )
                    or not _string_list(roles)
                    for mission_id, roles in roles_by_id.items()
                )
                or not safe_key(connection.get("nativeMappingId"))
                or "PlayRadio" not in safe_key(
                    connection.get("nativeConsumer")
                )
                or connection.get("unionTag") != 9
                or connection.get("serializedMemberCount") != 7
                or connection.get("specificDataListCount") != 1
                or not _string_list(connection.get("levelIds"))
                or not _string_list(connection.get("sourceFiles"))
                or not isinstance(connection.get("recordOffset"), int)
                or not isinstance(connection.get("recordEndOffset"), int)
            ):
                continue
            closed.append({
                "sceneKey": scene_key,
                "recoveryStatus":
                    "closed_exact_native_playback_context_no_relative_order",
                "relation": relation,
                "missionStateId": owner_mission,
                "missionStateGateRoles": sorted(
                    _string_list(connection.get("missionStateGateRoles")),
                    key=natural_key,
                ),
                "levelIds": _string_list(connection.get("levelIds")),
                "sourceFiles": _string_list(connection.get("sourceFiles")),
                "nativeMappingId": safe_key(
                    connection.get("nativeMappingId")
                ),
                "orderBoundary": (
                    "the exact radio trigger-zone row and mission-state "
                    "gates establish playback context, but entering the "
                    "world trigger supplies no relative Story order"
                ),
            })
            continue
        if relation == "npc_patrol_action_radio_playback_context":
            patrol_offset = connection.get("patrolRecordOffset")
            action_offset = connection.get("radioActionRecordOffset")
            action_end = connection.get("radioActionRecordEndOffset")
            next_patrol_offset = connection.get("nextPatrolRecordOffset")
            if (
                safe_key(connection.get("phase")) != "npc_patrol_action"
                or safe_key(connection.get("confidence"))
                != "native_exact_serialized_patrol_action"
                or safe_key(connection.get("evidenceTier")) != "direct"
                or connection.get("questActivation") is not False
                or connection.get("questPlayback") is not False
                or connection.get("questCompletion") is not False
                or safe_key(connection.get("patrolEnvelopeStatus")) not in {
                    "exact_full_patrol_record_consume",
                    "exact_typed_neighbor_boundaries_partial_point_decode",
                }
                or not isinstance(connection.get("patrolId"), int)
                or connection.get("patrolId") <= 0
                or connection.get("patrolActionType") != 9
                or connection.get("serializedMemberCount") != 26
                or safe_key(connection.get("patrolSubActionDataStatus"))
                != "null"
                or not safe_key(connection.get("nativeMappingId"))
                or "PlayRadio" not in safe_key(
                    connection.get("nativeConsumer")
                )
                or not _string_list(connection.get("levelIds"))
                or not _string_list(connection.get("sourceFiles"))
                or not all(isinstance(value, int) for value in (
                    patrol_offset,
                    action_offset,
                    action_end,
                    next_patrol_offset,
                ))
                or not (
                    patrol_offset < action_offset < action_end
                    <= next_patrol_offset
                )
            ):
                continue
            closed.append({
                "sceneKey": scene_key,
                "recoveryStatus":
                    "closed_exact_native_patrol_playback_context_no_relative_order",
                "relation": relation,
                "patrolId": connection.get("patrolId"),
                "patrolPointIndex": connection.get("patrolPointIndex"),
                "patrolEnvelopeStatus": safe_key(
                    connection.get("patrolEnvelopeStatus")
                ),
                "levelIds": _string_list(connection.get("levelIds")),
                "sourceFiles": _string_list(connection.get("sourceFiles")),
                "nativeMappingId": safe_key(
                    connection.get("nativeMappingId")
                ),
                "orderBoundary": (
                    "the exact typed patrol action establishes native radio "
                    "playback context; the patrol payload serializes no "
                    "mission/quest identity or relative Story order"
                ),
            })
            continue
        if relation != "mission_tracked_world_entity_levelscript_context":
            continue
        native_rows = connection.get("worldEntityLevelScriptEvidence") or []
        candidate_quest_ids = _string_list(
            connection.get("candidateQuestIds")
        )
        tracking_rows = connection.get("trackingRows") or []
        native_rows_valid = bool(native_rows)
        for row in native_rows:
            listener = row.get("listener") if isinstance(row, dict) else None
            path = (
                listener.get("path")
                if isinstance(listener, dict)
                else None
            )
            if (
                not isinstance(row, dict)
                or safe_key(row.get("nativeAction")) != "PlayRadio"
                or not isinstance(row.get("playbackRecordOffset"), int)
                or not isinstance(listener, dict)
                or safe_key(listener.get("status"))
                != "exact_serialized_control_path"
                or not isinstance(path, list)
                or not any(
                    isinstance(step, dict)
                    and safe_key(step.get("actionName")) == "PlayRadio"
                    and safe_key(step.get("recordClass")) == "play_radio"
                    and scene_key in _string_list(step.get("texts"))
                    for step in path
                )
            ):
                native_rows_valid = False
                break
        if (
            safe_key(connection.get("phase"))
            != "local_leader_trigger_world_entity_context"
            or safe_key(connection.get("confidence"))
            != "native_exact_mission_navigation_context"
            or safe_key(connection.get("evidenceTier"))
            != "derived_exact_foreign_key"
            or connection.get("questActivation") is not False
            or connection.get("questPlayback") is not False
            or connection.get("questCompletion") is not False
            or not candidate_quest_ids
            or any(
                not quest_id.startswith(f"{owner_mission}_q#")
                for quest_id in candidate_quest_ids
            )
            or not tracking_rows
            or any(
                not isinstance(row, dict)
                or safe_key(row.get("missionId")) != owner_mission
                or safe_key(row.get("questId")) not in candidate_quest_ids
                for row in tracking_rows
            )
            or not native_rows_valid
        ):
            continue
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus":
                "closed_exact_native_playback_context_no_relative_order",
            "relation": relation,
            "candidateQuestIds": candidate_quest_ids,
            "worldEntityIds": _string_list(
                connection.get("worldEntityIds")
            ),
            "levelIds": _string_list(connection.get("levelIds")),
            "scriptIds": _string_list(connection.get("scriptIds")),
            "sourceFiles": _string_list(connection.get("sourceFiles")),
            "nativeEventPathCount": len(native_rows),
            "orderBoundary": (
                "the exact local leader-trigger playback path and typed "
                "MissionRuntime world-entity tracking join establish mission "
                "context, but tracking is not activation, playback, "
                "completion, ownership, or relative Story order"
            ),
        })
    return sorted(closed, key=lambda row: natural_key(row["sceneKey"]))

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
        if row.get("evidenceKind") == "project_authored_story_content":
            closed.append({
                "sceneKey": scene_key,
                "recoveryStatus": "excluded_project_authored_story_content",
                "evidenceKind": "project_authored_story_content",
                "contentClass": row.get("content"),
                "storyKind": row.get("storyKind"),
                "sourceScope": row.get("sourceScope"),
                "producer": row.get("producer"),
                "sourceFiles": row.get("sourceFiles") or [],
                "sourceSha256": row.get("sourceSha256") or {},
                "gameDataEvidence": False,
                "consumerBoundary": (
                    "the generated Story entry and conversation carry matching "
                    "project-authored provenance; this row is not original game "
                    "content and cannot enter game consumer recovery"
                ),
                "orderBoundary": (
                    "project-authored display placement creates no mission, "
                    "playback, branch, ownership, or Story-order evidence"
                ),
                "reopenWhen": (
                    "the entry is replaced by an exact original-game definition "
                    "with independently recovered consumer evidence"
                ),
                "graphEffect": "none",
            })
        elif row.get("evidenceKind") == "guide_runtime_asset":
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
        elif row.get("evidenceKind") in {
            "spaceship_dialog_tree",
            "character_profile_voice",
            "spaceship_dialog_definition_without_tree_carrier",
        }:
            definition_gap = (
                row.get("evidenceKind")
                == "spaceship_dialog_definition_without_tree_carrier"
            )
            closed.append({
                "sceneKey": scene_key,
                "recoveryStatus": (
                    "deferred_current_build_spaceship_dialog_definition_"
                    "without_tree_carrier"
                    if definition_gap else
                    "closed_exact_spaceship_runtime_non_mission_content"
                ),
                "evidenceKind": row.get("evidenceKind"),
                "contentClass": row.get("content"),
                "lineIds": row.get("lineIds") or [],
                "dialogTreeRoots": row.get("dialogTreeRoots") or [],
                "consumerClasses": row.get("consumerClasses") or [],
                "characterIds": row.get("characterIds") or [],
                "profileVoiceIds": row.get("profileVoiceIds") or [],
                "dialogFamily": row.get("dialogFamily"),
                "actorId": row.get("actorId"),
                "carrierStatus": row.get("carrierStatus"),
                "consumerBoundary": row.get("consumerBoundary"),
                "sourceFiles": row.get("sourceFiles") or [],
                "nativeMappingId": row.get("nativeMappingId"),
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

def _deferred_offline_exhausted_isolated_scenes(
    flow: dict[str, Any],
    isolated_scene_keys: set[str],
    owner_mission: str,
    offline_exhaustion_index: dict[str, dict[str, Any]],
    native_playback_index: dict[str, list[dict[str, Any]]] | None = None,
    cross_owner_story_connections: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Defer exact-build exhausted rows without asserting a graph fact."""
    routed_rows_by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _flow_story_connections(flow):
        if isinstance(row, dict) and safe_key(row.get("key")):
            routed_rows_by_key[safe_key(row.get("key"))].append(row)
    deferred: list[dict[str, Any]] = []
    for scene_key in sorted(isolated_scene_keys, key=natural_key):
        evidence = offline_exhaustion_index.get(scene_key)
        routed_rows = routed_rows_by_key.get(scene_key, [])
        generic_guarded_recovery = (
            isinstance(evidence, dict)
            and safe_key(evidence.get("evidenceKind")) in {
                "radio_definition_binary_consumer_surface_exhausted",
                "missionless_npc_proxy_dialog_native_consumer",
                "sns_definition_binary_consumer_surface_exhausted",
            }
        )
        cross_owner_rows = [
            row
            for row in cross_owner_story_connections or []
            if isinstance(row, dict) and safe_key(row.get("key")) == scene_key
        ]
        exact_native_playback_rows = [
            row
            for row in (native_playback_index or {}).get(scene_key) or []
            if isinstance(row, dict)
        ]
        allowed_route = (
            evidence.get("allowedNonOwningRoute")
            if isinstance(evidence, dict)
            else None
        )
        routed_rows_valid = not routed_rows
        if routed_rows and isinstance(allowed_route, dict):
            routed_rows_valid = all(
                all(row.get(field) == value for field, value in allowed_route.items())
                for row in routed_rows
            )
            context = evidence.get("nonOwningContext") or {}
            quest_id = safe_key(context.get("questId"))
            if quest_id:
                expected_distance = context.get("distance")
                quest_rows = [
                    quest
                    for quest in flow.get("quests") or []
                    if isinstance(quest, dict)
                    if safe_key(quest.get("id")) == quest_id
                ]
                level_data_refs = [
                    ref
                    for quest in quest_rows
                    for ref in quest.get("levelDataStoryRefs") or []
                    if isinstance(ref, dict)
                    and safe_key(ref.get("storyRef")) == scene_key
                ]
                routed_rows_valid = (
                    routed_rows_valid
                    and len(quest_rows) == 1
                    and len(level_data_refs) == 1
                    and level_data_refs[0].get("distance")
                    == expected_distance
                    and safe_key(level_data_refs[0].get("file"))
                    == safe_key(allowed_route.get("file"))
                )
            elif context.get("candidateQuestIds"):
                expected_quests = sorted(
                    [
                        safe_key(value)
                        for value in context.get("candidateQuestIds") or []
                        if safe_key(value)
                    ],
                    key=natural_key,
                )
                route = routed_rows[0] if len(routed_rows) == 1 else {}
                carrier_context = (
                    route.get("carrierQuestStateContext") or {}
                    if isinstance(route, dict)
                    else {}
                )
                branch_contexts = carrier_context.get(
                    "questStateBranchContexts"
                ) or []
                routed_rows_valid = (
                    routed_rows_valid
                    and len(routed_rows) == 1
                    and sorted(
                        _string_list(carrier_context.get("candidateQuestIds")),
                        key=natural_key,
                    ) == expected_quests
                    and safe_key(context.get("parentStoryKey"))
                    == safe_key(route.get("parentStoryKey"))
                    and safe_key(context.get("sourceFile"))
                    in _string_list(route.get("sourceFiles"))
                    and bool(branch_contexts)
                    and all(
                        sorted(
                            _string_list(branch.get("questIds")),
                            key=natural_key,
                        ) == expected_quests
                        and safe_key(branch.get("conditionEvalString"))
                        == safe_key(context.get("conditionEvalString"))
                        and branch.get("noBypass") is True
                        and {
                            condition.get("targetQuestState")
                            for condition in branch.get("conditions") or []
                            if isinstance(condition, dict)
                        } == {context.get("targetQuestState")}
                        for branch in branch_contexts
                        if isinstance(branch, dict)
                    )
                )
        if (
            isinstance(evidence, dict)
            and _registered_parent_playback_routes_match(
                scene_key,
                owner_mission,
                evidence,
                routed_rows,
            )
        ):
            routed_rows_valid = True
        if (
            not isinstance(evidence, dict)
            or safe_key(evidence.get("missionId")) != owner_mission
            or not routed_rows_valid
            or (generic_guarded_recovery and exact_native_playback_rows)
            or (generic_guarded_recovery and cross_owner_rows)
            or evidence.get("graphEffect") != "none"
            or evidence.get("recoveryStatus") not in {
                "deferred_current_build_offline_surface_exhausted",
                "deferred_exact_native_playback_without_mission_bridge",
                "exact_current_build_interaction_trigger_recovered",
            }
        ):
            continue
        deferred.append(dict(evidence))
    return deferred

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

def _closed_exact_disconnected_dialog_tree_context_isolated_scenes(
    flow: dict[str, Any],
    isolated_scene_keys: set[str],
    owner_mission: str,
) -> list[dict[str, Any]]:
    """Close exact authored DialogTree actions disconnected from the prime path."""
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
    closed: list[dict[str, Any]] = []
    for row in _flow_story_connections(flow):
        scene_key = safe_key(row.get("key"))
        parent_story_key = safe_key(row.get("parentStoryKey"))
        occurrences = [
            occurrence
            for occurrence in row.get("dialogTreeNarrativeActions") or []
            if isinstance(occurrence, dict)
        ]
        if (
            scene_key not in isolated_scene_keys
            or safe_key(row.get("relation"))
            != "dialog_tree_narrative_action"
            or safe_key(row.get("storyOwnerMission")) != owner_mission
            or not parent_story_key
            or safe_key(row.get("confidence")) not in allowed_confidences
            or safe_key(row.get("evidenceTier"))
            not in allowed_evidence_tiers
            or safe_key(row.get("scopeCompleteness")) != "complete"
            or row.get("unscopedParentStoryKeys")
            or parent_story_key
            not in set(_string_list(row.get("allParentStoryKeys")))
            or safe_key(row.get("nativeMappingId"))
            != DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID
            or not _string_list(row.get("sourceFiles"))
            or not _string_list(row.get("sourcePathIds"))
            or not occurrences
            or int(row.get("occurrenceCount") or 0) != len(occurrences)
            or any(
                safe_key(occurrence.get("dialogKey"))
                != parent_story_key
                or safe_key(occurrence.get("actionType"))
                not in allowed_action_types
                or safe_key(occurrence.get("nativeMappingId"))
                != DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID
                or occurrence.get("reachableFromPrimeNode") is not False
                or _string_list(occurrence.get("primeToActionNodePath"))
                or _string_list(
                    occurrence.get("primeToActionConnectionPath")
                )
                or not (
                    _string_list(occurrence.get("incomingNodeIds"))
                    or _string_list(occurrence.get("outgoingNodeIds"))
                )
                or not safe_key(occurrence.get("textId"))
                or not safe_key(occurrence.get("actionPath"))
                or not safe_key(occurrence.get("nodeId"))
                or not safe_key(occurrence.get("sourceFile"))
                or not safe_key(occurrence.get("sourcePathId"))
                for occurrence in occurrences
            )
        ):
            continue
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus":
                "closed_exact_native_disconnected_dialog_tree_context_no_file_order",
            "relation": "dialog_tree_narrative_action",
            "parentStoryKey": parent_story_key,
            "textIds": sorted({
                safe_key(occurrence.get("textId"))
                for occurrence in occurrences
            }, key=natural_key),
            "nodeIds": sorted({
                safe_key(occurrence.get("nodeId"))
                for occurrence in occurrences
            }, key=natural_key),
            "sourceFiles": _string_list(row.get("sourceFiles")),
            "sourcePathIds": _string_list(row.get("sourcePathIds")),
            "nativeMappingId":
                DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID,
            "activationBoundary": (
                "the exact narrative action and parent DialogTree are "
                "authored, but the action node has no serialized path from "
                "the tree's prime node; an unknown external activation "
                "mechanism is not inferred"
            ),
            "orderBoundary": (
                "disconnected local node adjacency supplies neither runtime "
                "playback nor a Story-file order edge"
            ),
        })
    return sorted(closed, key=lambda row: natural_key(row["sceneKey"]))

def _closed_exact_timeline_dialog_embedded_isolated_scenes(
    flow: dict[str, Any],
    isolated_scene_keys: set[str],
    mission: str,
) -> list[dict[str, Any]]:
    """Close exact Timeline-embedded Story playback with content on both sides."""
    accepted_host_missions = {
        mission,
        *_string_list(flow.get("_sourceVariantMissionIds")),
    }
    closed: list[dict[str, Any]] = []
    for row in _flow_story_connections(flow):
        scene_key = safe_key(row.get("key"))
        parent_story_key = safe_key(row.get("parentStoryKey"))
        text_ids = set(_string_list(row.get("textIds")))
        timeline_ids = set(_string_list(row.get("timelines")))
        source_files = set(_string_list(row.get("sourceFiles")))
        attachments = [
            attachment
            for attachment in row.get("timelineAttachments") or []
            if isinstance(attachment, dict)
        ]
        parent_occurrences = [
            occurrence
            for occurrence in row.get("parentDialogNativeOccurrences") or []
            if isinstance(occurrence, dict)
        ]
        if (
            scene_key not in isolated_scene_keys
            or safe_key(row.get("relation"))
            != "timeline_dialog_contains_black"
            or safe_key(row.get("confidence")) != "native_exact_host"
            or safe_key(row.get("storyOwnerMission")) != mission
            or not parent_story_key
            or not text_ids
            or not timeline_ids
            or not source_files
            or len(attachments) != len(text_ids)
            or int(row.get("occurrenceCount") or 0) != len(text_ids)
            or not parent_occurrences
        ):
            continue
        if any(
            safe_key(attachment.get("key")) != scene_key
            or safe_key(attachment.get("textId")) not in text_ids
            or safe_key(attachment.get("dialogKey")) != parent_story_key
            or safe_key(attachment.get("timeline")) not in timeline_ids
            or safe_key(attachment.get("sourceFile")) not in source_files
            or safe_key(attachment.get("dialogJoin"))
            != "dialog_id_table_used_timeline"
            or not safe_key(attachment.get("assetPath"))
            or not safe_key(attachment.get("trackPath"))
            or not safe_key(attachment.get("rootPath"))
            for attachment in attachments
        ):
            continue
        native_paths: list[dict[str, Any]] = []
        valid = True
        for occurrence in parent_occurrences:
            action_local_id = occurrence.get("localId")
            if (
                safe_key(occurrence.get("recordClass")) != "play_dialog"
                or not safe_key(occurrence.get("actionName"))
                or parent_story_key
                not in _string_list(occurrence.get("allStoryKeysInRecord"))
                or not isinstance(action_local_id, int)
            ):
                valid = False
                break
            level_data_hosts = [
                host
                for host in occurrence.get("levelDataHosts") or []
                if isinstance(host, dict)
            ]
            if (
                not level_data_hosts
                or any(
                    safe_key(host.get("missionId"))
                    not in accepted_host_missions
                    or not safe_key(host.get("levelDataFile"))
                    for host in level_data_hosts
                )
            ):
                valid = False
                break
            exact_owners = [
                owner
                for owner in occurrence.get("nativeEventOwners") or []
                if (
                    isinstance(owner, dict)
                    and safe_key(owner.get("status"))
                    in LEVELSCRIPT_NATIVE_EXACT_CONTROL_PATH_STATUSES
                    and action_local_id
                    in {
                        step.get("localId")
                        for step in owner.get("path") or []
                        if isinstance(step, dict)
                    }
                )
            ]
            if not exact_owners:
                valid = False
                break
            native_paths.extend({
                "levelId": safe_key(occurrence.get("levelId")),
                "scriptId": safe_key(occurrence.get("scriptId")),
                "sourceFile": safe_key(occurrence.get("sourceFile")),
                "headerName": safe_key(owner.get("headerName")),
                "headerLocalId": owner.get("headerLocalId"),
                "actionName": safe_key(occurrence.get("actionName")),
                "actionLocalId": action_local_id,
            } for owner in exact_owners)
        if not valid:
            continue
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus":
                "closed_exact_native_timeline_embedded_playback_context_"
                "no_file_order",
            "relation": "timeline_dialog_contains_black",
            "parentStoryKey": parent_story_key,
            "timelineIds": sorted(timeline_ids, key=natural_key),
            "textIds": sorted(text_ids, key=natural_key),
            "nativeEventPaths": native_paths,
            "placementBoundary": (
                "the exact parent playback path and Timeline clips establish "
                "embedded playback; parent dialog content occurs on both "
                "sides, so no scene-file edge is created"
            ),
            "graphEffect": "none",
        })
    return sorted(closed, key=lambda row: natural_key(row["sceneKey"]))

def _closed_exact_timeline_foreign_dialog_isolated_scenes(
    flow: dict[str, Any],
    isolated_scene_keys: set[str],
    mission: str,
) -> list[dict[str, Any]]:
    """Close exact foreign-dialog Timeline blocks with parent playback scope."""
    accepted_host_missions = {
        mission,
        *_string_list(flow.get("_sourceVariantMissionIds")),
    }
    exact_owner_statuses = LEVELSCRIPT_NATIVE_EXACT_CONTROL_PATH_STATUSES
    closed: list[dict[str, Any]] = []
    for row in _flow_story_connections(flow):
        scene_key = safe_key(row.get("key"))
        parent_story_key = safe_key(row.get("parentStoryKey"))
        text_ids = set(_string_list(row.get("textIds")))
        option_ids = set(_string_list(row.get("optionIds")))
        timeline_ids = set(_string_list(row.get("timelines")))
        source_files = set(_string_list(row.get("sourceFiles")))
        containments = [
            containment
            for containment in row.get(
                "timelineDialogContainments"
            ) or []
            if isinstance(containment, dict)
        ]
        parent_occurrences = [
            occurrence
            for occurrence in row.get(
                "parentDialogNativeOccurrences"
            ) or []
            if isinstance(occurrence, dict)
        ]
        if (
            scene_key not in isolated_scene_keys
            or safe_key(row.get("relation"))
            != "timeline_dialog_contains_foreign_dialog"
            or safe_key(row.get("confidence")) != "native_exact_host"
            or safe_key(row.get("storyOwnerMission")) != mission
            or safe_key(row.get("graphEffect")) != "none"
            or not parent_story_key
            or not text_ids
            or not timeline_ids
            or not source_files
            or len(containments) != int(row.get("occurrenceCount") or 0)
            or not containments
            or not parent_occurrences
        ):
            continue
        if any(
            safe_key(containment.get("key")) != scene_key
            or scene_key not in {
                safe_key(containment.get("rawDialogKey")),
                "misc_"
                + safe_key(containment.get("rawDialogKey")),
            }
            or safe_key(containment.get("dialogKey"))
            != parent_story_key
            or safe_key(containment.get("timeline"))
            not in timeline_ids
            or safe_key(containment.get("sourceFile"))
            not in source_files
            or set(_string_list(containment.get("lineIds")))
            != text_ids
            or not set(_string_list(containment.get("optionIds")))
            <= option_ids
            or safe_key(containment.get("dialogJoin"))
            != "dialog_id_table_used_timeline"
            or safe_key(containment.get("placementStatus"))
            != (
                "exact_contiguous_foreign_dialog_lines_"
                "with_parent_on_both_sides"
            )
            or not safe_key(
                containment.get("beforeParentLineId")
            ).startswith(f"{parent_story_key}_")
            or not safe_key(
                containment.get("afterParentLineId")
            ).startswith(f"{parent_story_key}_")
            or safe_key(containment.get("graphEffect")) != "none"
            for containment in containments
        ):
            continue

        native_paths: list[dict[str, Any]] = []
        valid = True
        for occurrence in parent_occurrences:
            action_local_id = occurrence.get("localId")
            if (
                safe_key(occurrence.get("recordClass"))
                != "play_dialog"
                or not safe_key(occurrence.get("actionName"))
                or parent_story_key
                not in _string_list(
                    occurrence.get("allStoryKeysInRecord")
                )
                or not isinstance(action_local_id, int)
                or isinstance(action_local_id, bool)
            ):
                valid = False
                break
            level_data_hosts = [
                host
                for host in occurrence.get("levelDataHosts") or []
                if isinstance(host, dict)
            ]
            if (
                not level_data_hosts
                or any(
                    safe_key(host.get("missionId"))
                    not in accepted_host_missions
                    or not safe_key(host.get("levelDataFile"))
                    for host in level_data_hosts
                )
            ):
                valid = False
                break
            exact_owners = [
                owner
                for owner in occurrence.get("nativeEventOwners") or []
                if (
                    isinstance(owner, dict)
                    and safe_key(owner.get("status"))
                    in exact_owner_statuses
                    and action_local_id
                    in {
                        step.get("localId")
                        for step in owner.get("path") or []
                        if isinstance(step, dict)
                    }
                )
            ]
            if not exact_owners:
                valid = False
                break
            native_paths.extend({
                "levelId": safe_key(occurrence.get("levelId")),
                "scriptId": safe_key(occurrence.get("scriptId")),
                "sourceFile": safe_key(occurrence.get("sourceFile")),
                "headerName": safe_key(owner.get("headerName")),
                "headerLocalId": owner.get("headerLocalId"),
                "actionName": safe_key(occurrence.get("actionName")),
                "actionLocalId": action_local_id,
            } for owner in exact_owners)
        if not valid:
            continue
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus":
                "closed_exact_native_timeline_foreign_dialog_playback_"
                "context_no_file_order",
            "relation":
                "timeline_dialog_contains_foreign_dialog",
            "parentStoryKey": parent_story_key,
            "timelineIds": sorted(timeline_ids, key=natural_key),
            "textIds": sorted(text_ids, key=natural_key),
            "optionIds": sorted(option_ids, key=natural_key),
            "beforeParentLineIds": sorted({
                safe_key(containment.get("beforeParentLineId"))
                for containment in containments
            }, key=natural_key),
            "afterParentLineIds": sorted({
                safe_key(containment.get("afterParentLineId"))
                for containment in containments
            }, key=natural_key),
            "nativeEventPaths": native_paths,
            "placementBoundary": (
                "the exact registered parent Timeline and native parent "
                "playback path establish nested playback; parent dialog "
                "content occurs on both sides, so no Story-file edge is "
                "created"
            ),
            "graphEffect": "none",
        })
    return sorted(closed, key=lambda row: natural_key(row["sceneKey"]))

def _closed_exact_black_carrier_context_isolated_scenes(
    flow: dict[str, Any],
    isolated_scene_keys: set[str],
    owner_mission: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Close exact black-screen carriers without inventing file chronology.

    This validator is carrier-shaped rather than key-shaped. It accepts three
    original-data patterns: a typed DialogTree narrative action, a registered
    Timeline black-text playable, or a typed LevelScript black action. Mission
    and quest scope may remain unresolved; every serialized consumer and
    related file still has to pass its pattern-specific exactness gates.
    """
    validator = "exact_black_carrier_context_v1"
    candidate_relations = {
        "dialog_tree_narrative_action",
        "dialog_tree_narrative_action_unscoped",
        "timeline_dialog_contains_black",
        "levelscript_native_black_action",
    }
    rows_by_scene: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _flow_story_connections(flow):
        scene_key = safe_key(row.get("key"))
        if (
            scene_key in isolated_scene_keys
            and safe_key(row.get("storyOwnerMission")) == owner_mission
            and safe_key(row.get("relation")) in candidate_relations
        ):
            rows_by_scene[scene_key].append(row)

    closed: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    def reject(
        scene_key: str,
        gate: str,
        expected: Any,
        actual: Any,
        rows: list[dict[str, Any]],
    ) -> None:
        failures.append({
            "validator": validator,
            "gate": gate,
            "missionId": owner_mission,
            "sceneKey": scene_key,
            "expected": expected,
            "actual": actual,
            "sourceFiles": sorted({
                source
                for row in rows
                for source in (
                    _string_list(row.get("sourceFiles"))
                    + _string_list(row.get("assetPaths"))
                    + _string_list(row.get("trackPaths"))
                    + _string_list(row.get("rootPaths"))
                )
            })[:16],
        })

    for scene_key, scene_rows in sorted(
        rows_by_scene.items(),
        key=lambda item: natural_key(item[0]),
    ):
        native_rows = [
            row for row in scene_rows
            if safe_key(row.get("relation"))
            == "levelscript_native_black_action"
        ]
        if native_rows:
            native_valid = True
            native_paths: list[dict[str, Any]] = []
            context_missions: set[str] = set()
            related_files: set[str] = set()
            for row in native_rows:
                occurrences = [
                    occurrence
                    for occurrence in row.get(
                        "nativeBlackActionOccurrences"
                    ) or []
                    if isinstance(occurrence, dict)
                ]
                context_mission = (
                    safe_key(row.get("levelDataHostMissionId"))
                    or safe_key(row.get("contextMissionBundle"))
                )
                if (
                    safe_key(row.get("direction")) != "context"
                    or safe_key(row.get("phase")) != "runtime_playback"
                    or safe_key(row.get("confidence"))
                    != "native_exact_host"
                    or safe_key(row.get("nativeMappingId"))
                    != LEVELSCRIPT_NATIVE_ACTION_MAPPING_ID
                    or safe_key(row.get("questTriggerStatus"))
                    != "unresolved"
                    or _string_list(row.get("nativeActions"))
                    != ["NarrativeBlackScreenAction"]
                    or not context_mission
                    or not occurrences
                    or row.get("occurrenceCount") != len(occurrences)
                    or row.get("allOccurrenceCount") != len(occurrences)
                ):
                    native_valid = False
                    break
                context_missions.add(context_mission)
                for occurrence in occurrences:
                    action_local_id = occurrence.get("localId")
                    line_ids = set(_string_list(occurrence.get("lineIds")))
                    owners = [
                        owner
                        for owner in occurrence.get("nativeEventOwners") or []
                        if isinstance(owner, dict)
                    ]
                    hosts = [
                        host
                        for host in occurrence.get("levelDataHosts") or []
                        if isinstance(host, dict)
                    ]
                    if (
                        safe_key(occurrence.get("key")) != scene_key
                        or safe_key(occurrence.get("actionName"))
                        != "NarrativeBlackScreenAction"
                        or safe_key(occurrence.get("recordClass"))
                        != "play_black"
                        or safe_key(occurrence.get("unionTag")) != "0x0310"
                        or occurrence.get("serializedMemberCount") != 20
                        or safe_key(occurrence.get("nativeMappingId"))
                        != LEVELSCRIPT_NATIVE_ACTION_MAPPING_ID
                        or not isinstance(action_local_id, int)
                        or isinstance(action_local_id, bool)
                        or not line_ids
                        or any(
                            not line_id.startswith(f"{scene_key}_")
                            for line_id in line_ids
                        )
                        or not safe_key(occurrence.get("sourceFile"))
                        or not owners
                        or any(
                            safe_key(owner.get("status"))
                            != "exact_serialized_control_path"
                            or action_local_id not in {
                                step.get("localId")
                                for step in owner.get("path") or []
                                if isinstance(step, dict)
                            }
                            for owner in owners
                        )
                        or not hosts
                        or any(
                            safe_key(host.get("missionId"))
                            != context_mission
                            or not safe_key(host.get("levelDataFile"))
                            or safe_key(host.get("nativeSchema"))
                            != (
                                "LevelData/43.member22:Dictionary<u64,"
                                "LevelScriptBriefData/8>"
                            )
                            for host in hosts
                        )
                    ):
                        native_valid = False
                        break
                    related_files.add(safe_key(occurrence.get("sourceFile")))
                    related_files.update(
                        safe_key(host.get("levelDataFile")) for host in hosts
                    )
                    native_paths.extend({
                        "levelId": safe_key(occurrence.get("levelId")),
                        "scriptId": safe_key(occurrence.get("scriptId")),
                        "sourceFile": safe_key(occurrence.get("sourceFile")),
                        "headerName": safe_key(owner.get("headerName")),
                        "headerLocalId": owner.get("headerLocalId"),
                        "actionName": "NarrativeBlackScreenAction",
                        "actionLocalId": action_local_id,
                    } for owner in owners)
                if not native_valid:
                    break
            if native_valid:
                closed.append({
                    "sceneKey": scene_key,
                    "recoveryStatus": (
                        "closed_exact_native_black_playback_context_"
                        "no_relative_order"
                    ),
                    "relation": "levelscript_native_black_action",
                    "nominalStoryMissionId": owner_mission,
                    "contextMissionIds": sorted(
                        context_missions,
                        key=natural_key,
                    ),
                    "contextMissionMismatch": any(
                        mission != owner_mission
                        for mission in context_missions
                    ),
                    "nativeEventPaths": native_paths,
                    "sourceFiles": sorted(
                        {path for path in related_files if path}
                    ),
                    "activationBoundary": (
                        "the typed native black action and exact event path "
                        "prove local playback; no quest trigger is serialized"
                    ),
                    "orderBoundary": (
                        "the runtime shell does not transfer Story ownership "
                        "or place the black file relative to mission files"
                    ),
                    "graphEffect": "none",
                })
                continue
            reject(
                scene_key,
                "native_black_exact_playback_contract",
                (
                    "typed NarrativeBlackScreenAction with exact event path, "
                    "line ownership, and unique LevelData host"
                ),
                {
                    "rowCount": len(native_rows),
                    "relations": sorted({
                        safe_key(row.get("relation")) for row in native_rows
                    }),
                },
                native_rows,
            )
            continue

        timeline_rows = [
            row for row in scene_rows
            if safe_key(row.get("relation"))
            == "timeline_dialog_contains_black"
        ]
        if timeline_rows:
            timeline_valid = True
            parent_keys: set[str] = set()
            timeline_ids: set[str] = set()
            text_ids: set[str] = set()
            related_files: set[str] = set()
            confidences: set[str] = set()
            for row in timeline_rows:
                confidence = safe_key(row.get("confidence"))
                parent_key = safe_key(row.get("parentStoryKey"))
                attachments = [
                    attachment
                    for attachment in row.get("timelineAttachments") or []
                    if isinstance(attachment, dict)
                ]
                row_text_ids = set(_string_list(row.get("textIds")))
                row_timeline_ids = set(_string_list(row.get("timelines")))
                if (
                    confidence not in {
                        "native_exact_parent_context",
                        "native_exact_parent_unscoped",
                    }
                    or not parent_key
                    or not row_text_ids
                    or not row_timeline_ids
                    or not attachments
                    or row.get("occurrenceCount") != len(attachments)
                    or len(attachments) != len(row_text_ids)
                    or (
                        confidence == "native_exact_parent_context"
                        and (
                            not _string_list(row.get("parentScopeRelations"))
                            or safe_key(row.get("questTriggerStatus"))
                            != "unresolved_parent_has_no_unique_quest"
                        )
                    )
                    or (
                        confidence == "native_exact_parent_unscoped"
                        and (
                            safe_key(row.get("questTriggerStatus"))
                            != "unresolved_parent_scope"
                            or not safe_key(row.get("scopeBoundary"))
                        )
                    )
                ):
                    timeline_valid = False
                    break
                if any(
                    safe_key(attachment.get("key")) != scene_key
                    or safe_key(attachment.get("textId")) not in row_text_ids
                    or safe_key(attachment.get("dialogKey")) != parent_key
                    or safe_key(attachment.get("timeline"))
                    not in row_timeline_ids
                    or safe_key(attachment.get("dialogJoin"))
                    != "dialog_id_table_used_timeline"
                    or not safe_key(attachment.get("sourceFile"))
                    or not safe_key(attachment.get("assetPath"))
                    or not safe_key(attachment.get("trackPath"))
                    or not safe_key(attachment.get("rootPath"))
                    for attachment in attachments
                ):
                    timeline_valid = False
                    break
                confidences.add(confidence)
                parent_keys.add(parent_key)
                text_ids.update(row_text_ids)
                timeline_ids.update(row_timeline_ids)
                related_files.update(
                    safe_key(attachment.get(field))
                    for attachment in attachments
                    for field in (
                        "sourceFile",
                        "assetPath",
                        "trackPath",
                        "rootPath",
                    )
                )
            if timeline_valid:
                closed.append({
                    "sceneKey": scene_key,
                    "recoveryStatus": (
                        "closed_exact_timeline_black_carrier_context_"
                        "owner_or_order_unresolved"
                    ),
                    "relation": "timeline_dialog_contains_black",
                    "nominalStoryMissionId": owner_mission,
                    "parentStoryKeys": sorted(parent_keys, key=natural_key),
                    "timelineIds": sorted(timeline_ids, key=natural_key),
                    "textIds": sorted(text_ids, key=natural_key),
                    "confidenceKinds": sorted(confidences),
                    "sourceFiles": sorted(
                        {path for path in related_files if path}
                    ),
                    "activationBoundary": (
                        "the serialized Timeline carrier and registered parent "
                        "dialog are exact; parent mission/quest activation may "
                        "remain unresolved"
                    ),
                    "orderBoundary": (
                        "Timeline containment supplies no Story-file edge or "
                        "relative mission chronology"
                    ),
                    "graphEffect": "none",
                })
                continue
            reject(
                scene_key,
                "timeline_black_exact_carrier_contract",
                (
                    "exact playable/track/root containment with registered "
                    "DialogIdTable parent"
                ),
                {
                    "rowCount": len(timeline_rows),
                    "confidences": sorted({
                        safe_key(row.get("confidence"))
                        for row in timeline_rows
                    }),
                },
                timeline_rows,
            )
            continue

        dialog_rows = [
            row for row in scene_rows
            if safe_key(row.get("relation")) in {
                "dialog_tree_narrative_action",
                "dialog_tree_narrative_action_unscoped",
            }
        ]
        if not dialog_rows:
            continue
        dialog_valid = True
        parent_keys: set[str] = set()
        declared_parent_keys: set[str] = set()
        source_files: set[str] = set()
        source_path_ids: set[str] = set()
        placements: set[str] = set()
        for row in dialog_rows:
            parent_key = safe_key(row.get("parentStoryKey"))
            occurrences = [
                occurrence
                for occurrence in row.get("dialogTreeNarrativeActions") or []
                if isinstance(occurrence, dict)
            ]
            declared_parent_keys.update(
                _string_list(row.get("allParentStoryKeys"))
            )
            if (
                not parent_key
                or safe_key(row.get("nativeMappingId"))
                != DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID
                or not occurrences
                or row.get("occurrenceCount") != len(occurrences)
            ):
                dialog_valid = False
                break
            parent_keys.add(parent_key)
            for occurrence in occurrences:
                reachable = occurrence.get("reachableFromPrimeNode")
                prime_path = _string_list(
                    occurrence.get("primeToActionNodePath")
                )
                incoming = _string_list(occurrence.get("incomingNodeIds"))
                outgoing = _string_list(occurrence.get("outgoingNodeIds"))
                placement = safe_key(
                    occurrence.get("dialogTreeConnectionPlacementStatus")
                )
                if (
                    safe_key(occurrence.get("dialogKey")) != parent_key
                    or safe_key(occurrence.get("actionType")) not in {
                        "Beyond.Gameplay.DialogComplexNarrativeMaskActionData",
                        "Beyond.Gameplay.DialogNarrativeMaskActionData",
                    }
                    or safe_key(occurrence.get("actionKind"))
                    not in {"complex_narrative", "narrative"}
                    or safe_key(occurrence.get("nativeMappingId"))
                    != DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID
                    or safe_key(occurrence.get("textId"))
                    == ""
                    or not safe_key(occurrence.get("textId")).startswith(
                        f"{scene_key}_"
                    )
                    or not safe_key(occurrence.get("actionPath"))
                    or not safe_key(occurrence.get("nodeId"))
                    or not safe_key(occurrence.get("sourceFile"))
                    or not safe_key(occurrence.get("sourcePathId"))
                    or placement not in {
                        "exact_unique_adjacent_parent_trunks",
                        "no_exact_unique_adjacent_parent_trunks",
                    }
                    or not isinstance(reachable, bool)
                    or (reachable and not prime_path)
                    or (
                        not reachable
                        and (
                            prime_path
                            or not (incoming or outgoing)
                        )
                    )
                ):
                    dialog_valid = False
                    break
                placements.add(placement)
                source_files.add(safe_key(occurrence.get("sourceFile")))
                source_path_ids.add(safe_key(occurrence.get("sourcePathId")))
            if not dialog_valid:
                break
        if declared_parent_keys and parent_keys != declared_parent_keys:
            dialog_valid = False
        if dialog_valid and parent_keys and source_files and source_path_ids:
            closed.append({
                "sceneKey": scene_key,
                "recoveryStatus": (
                    "closed_exact_dialog_tree_black_carrier_context_"
                    "no_file_order"
                ),
                "relation": "dialog_tree_narrative_action",
                "nominalStoryMissionId": owner_mission,
                "parentStoryKeys": sorted(parent_keys, key=natural_key),
                "sourceFiles": sorted(source_files),
                "sourcePathIds": sorted(source_path_ids),
                "placementStatuses": sorted(placements),
                "activationBoundary": (
                    "every typed narrative action and serialized DialogTree "
                    "node path is exact; parent mission/quest ownership may "
                    "remain partial or cross-mission"
                ),
                "orderBoundary": (
                    "nested or disconnected DialogTree action context does "
                    "not create a Story-file precedence edge"
                ),
                "graphEffect": "none",
            })
            continue
        reject(
            scene_key,
            "dialog_tree_exact_carrier_coverage",
            {
                "allDeclaredParentsRepresented": True,
                "typedActionsAndNodePathsExact": True,
            },
            {
                "declaredParentStoryKeys": sorted(
                    declared_parent_keys,
                    key=natural_key,
                ),
                "representedParentStoryKeys": sorted(
                    parent_keys,
                    key=natural_key,
                ),
                "rowCount": len(dialog_rows),
            },
            dialog_rows,
        )

    return (
        sorted(closed, key=lambda row: natural_key(row["sceneKey"])),
        sorted(
            failures,
            key=lambda row: (
                natural_key(row["missionId"]),
                natural_key(row["sceneKey"]),
                row["gate"],
            ),
        ),
    )

def _closed_exact_lua_controller_playback_isolated_scenes(
    story_trigger_manifest: dict[str, Any],
    isolated_scene_keys: set[str],
    owner_mission: str,
    validation_failures: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Close exact shipped-Lua playback with deliberately unresolved owner."""
    closed: list[dict[str, Any]] = []
    for scene_key in sorted(isolated_scene_keys, key=natural_key):
        row = story_trigger_manifest.get(scene_key)
        if not isinstance(row, dict):
            continue
        if safe_key(row.get("attachmentStatus")) != "trigger_known_owner_unresolved":
            continue
        routes = [
            route
            for route in row.get("routes") or []
            if (
                isinstance(route, dict)
                and safe_key(route.get("relation"))
                == "lua_controller_playback"
            )
        ]
        if not routes:
            continue
        route = routes[0] if len(routes) == 1 else {}
        lua_file = safe_key(route.get("luaFile"))
        phase = safe_key(route.get("phase"))
        lua_call = safe_key(route.get("luaCall"))
        lua_symbol = safe_key(route.get("luaSymbol"))
        lua_line = route.get("luaLine")
        lua_source_path = safe_key(route.get("luaSourcePath"))
        lua_source_sha256 = safe_key(route.get("luaSourceSha256")).lower()
        audit_report = safe_key(route.get("auditReport"))
        audit_sha256 = safe_key(route.get("auditSha256")).lower()
        method_match = re.fullmatch(r"GameAction\.([A-Za-z][A-Za-z0-9_]*)", lua_call)
        native_entry = (
            f"Beyond.Gameplay.Actions.GameAction::{method_match.group(1)}"
            if method_match else ""
        )
        expected_steps = [
            {
                "id": lua_file,
                "kind": "luaController",
                "phase": phase,
                "summaries": [
                    f"line {lua_line}",
                    f"SHA-256 {lua_source_sha256}",
                ],
            },
            {
                "id": native_entry,
                "kind": "nativePlayback",
            },
        ]
        valid = (
            len(routes) == 1
            and safe_key(row.get("key")) == scene_key
            and safe_key(row.get("nominalMissionId")) == owner_mission
            and safe_key(route.get("storyKey")) == scene_key
            and safe_key(route.get("relation")) == "lua_controller_playback"
            and safe_key(route.get("direction")) == "playback"
            and safe_key(route.get("causality")) == "playback_owner_unresolved"
            and safe_key(route.get("confidence"))
            == "corpus_scanned_shipped_lua_literal_plus_native_entry"
            and safe_key(route.get("evidenceTier")) == "direct"
            and safe_key(route.get("ownerStatus")) == "unresolved"
            and route.get("missionId") is None
            and route.get("questId") is None
            and safe_key(route.get("questTriggerStatus"))
            == "no_mission_or_quest_identity_serialized"
            and safe_key(route.get("scope")) == "phase"
            and bool(phase)
            and bool(method_match)
            and bool(lua_symbol)
            and safe_key(route.get("nativeEntry")) == native_entry
            and bool(lua_file)
            and bool(lua_source_path)
            and isinstance(lua_line, int)
            and not isinstance(lua_line, bool)
            and lua_line > 0
            and bool(re.fullmatch(r"[0-9a-f]{64}", lua_source_sha256))
            and bool(audit_report)
            and bool(re.fullmatch(r"[0-9a-f]{64}", audit_sha256))
            and _string_list(route.get("sourceFiles"))
            == [lua_file, audit_report]
            and route.get("serverExchange") is False
            and route.get("steps") == expected_steps
        )
        if not valid:
            if validation_failures is not None:
                validation_failures.append({
                    "validator": "exact_lua_controller_playback_closure_v2",
                    "gate": "route_contract",
                    "missionId": owner_mission,
                    "storyKey": scene_key,
                    "sourcePaths": _string_list(route.get("sourceFiles")),
                    "sourceSha256": {
                        lua_source_path: lua_source_sha256,
                        audit_report: audit_sha256,
                    },
                    "expected": {
                        "manifestKey": scene_key,
                        "nominalMissionId": owner_mission,
                        "routeCount": 1,
                        "relation": "lua_controller_playback",
                        "confidence": (
                            "corpus_scanned_shipped_lua_literal_plus_native_entry"
                        ),
                        "luaCallPattern": "GameAction.<method>",
                        "nativeEntryPattern": (
                            "Beyond.Gameplay.Actions.GameAction::<method>"
                        ),
                        "exactSourceHashes": True,
                    },
                    "actual": {
                        "manifestKey": safe_key(row.get("key")),
                        "nominalMissionId": safe_key(row.get("nominalMissionId")),
                        "routeCount": len(routes),
                        "relation": safe_key(route.get("relation")),
                        "confidence": safe_key(route.get("confidence")),
                        "luaCall": lua_call,
                        "nativeEntry": safe_key(route.get("nativeEntry")),
                        "sourceFileCount": len(_string_list(route.get("sourceFiles"))),
                    },
                })
            continue
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus":
                "closed_exact_lua_controller_playback_"
                "no_mission_owner_or_relative_order",
            "relation": "lua_controller_playback",
            "phase": phase,
            "luaFile": lua_file,
            "luaSymbol": lua_symbol,
            "luaCall": lua_call,
            "luaLine": lua_line,
            "luaSourcePath": lua_source_path,
            "luaSourceSha256": lua_source_sha256,
            "auditReport": audit_report,
            "auditSha256": audit_sha256,
            "nativeEntry": native_entry,
            "sourceFiles": _string_list(route.get("sourceFiles")),
            "ownerStatus": "unresolved",
            "playbackBoundary": (
                "the shipped phase controller proves exact cutscene playback; "
                "it serializes no mission or quest identity and therefore "
                "establishes neither mission ownership nor relative Story order"
            ),
            "graphEffect": "none",
        })
    return closed

def _closed_exact_composed_root_playback_isolated_scenes(
    story_trigger_manifest: dict[str, Any],
    isolated_scene_keys: set[str],
    owner_mission: str,
    validation_failures: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Close exact owned CutsceneRoot aliases without inventing chronology.

    A standalone ``CutsceneRoot._director`` PPtr proves playback only.  It is
    admitted here only when the current trigger manifest has already composed
    that serialized alias with an independently connected native route ending
    at the root Story key.  The route shape and evidence files are revalidated
    so a stale or partially populated manifest fails closed.
    """
    closed: list[dict[str, Any]] = []
    for scene_key in sorted(isolated_scene_keys, key=natural_key):
        manifest_row = story_trigger_manifest.get(scene_key)
        if not isinstance(manifest_row, dict):
            continue
        if safe_key(manifest_row.get("attachmentStatus")) != "connected":
            continue
        composed_routes = [
            route
            for route in manifest_row.get("routes") or []
            if isinstance(route, dict)
            and safe_key(route.get("relation"))
            == "cutscene_root_playback_alias_composed"
        ]
        alias_routes = [
            route
            for route in manifest_row.get("routes") or []
            if isinstance(route, dict)
            and safe_key(route.get("relation"))
            == "cutscene_root_playback_alias"
        ]
        if not composed_routes and not alias_routes:
            continue
        validated: list[dict[str, Any]] = []
        for route in composed_routes:
            root_key = safe_key(route.get("rootStoryKey"))
            steps = route.get("steps")
            source_files = _string_list(route.get("sourceFiles"))
            audit_report = safe_key(route.get("auditReport"))
            native_paths = [
                row
                for row in route.get("nativePaths") or []
                if isinstance(row, dict)
            ]
            quest_id = safe_key(route.get("questId"))
            matching_aliases = []
            for alias_route in alias_routes:
                alias_sources = _string_list(alias_route.get("sourceFiles"))
                if (
                    safe_key(alias_route.get("storyKey")) == scene_key
                    and safe_key(alias_route.get("rootStoryKey")) == root_key
                    and safe_key(alias_route.get("direction")) == "playback"
                    and safe_key(alias_route.get("causality"))
                    == "playback_alias_owner_unresolved"
                    and safe_key(alias_route.get("confidence"))
                    == "exact_serialized_root_director_plus_native_playback"
                    and safe_key(alias_route.get("evidenceTier")) == "direct"
                    and safe_key(alias_route.get("ownerStatus")) == "unresolved"
                    and alias_route.get("missionId") is None
                    and alias_route.get("questId") is None
                    and safe_key(alias_route.get("questTriggerStatus"))
                    == "no_mission_or_quest_selector_recovered"
                    and safe_key(alias_route.get("scope")) == "cutscene_root"
                    and alias_route.get("serverExchange") is False
                    and safe_key(alias_route.get("nativeMappingId"))
                    == safe_key(route.get("nativeMappingId"))
                    and safe_key(alias_route.get("auditReport")) == audit_report
                    and alias_sources
                    and audit_report in alias_sources
                    and set(alias_sources).issubset(source_files)
                    and alias_route.get("steps") == [
                        {"id": root_key, "kind": "story_root"},
                        {
                            "id": (
                                "CutsceneRoot._director -> "
                                "TimelineHandle.Play"
                            ),
                            "kind": "native_action",
                        },
                        {"id": scene_key, "kind": "story"},
                    ]
                ):
                    matching_aliases.append(alias_route)
            if (
                safe_key(route.get("storyKey")) != scene_key
                or safe_key(route.get("missionId")) != owner_mission
                or safe_key(route.get("direction")) != "context"
                or safe_key(route.get("causality"))
                != "playback_alias_owner_connected"
                or safe_key(route.get("confidence"))
                != (
                    "exact_connected_root_playback_plus_"
                    "serialized_director_alias"
                )
                or safe_key(route.get("evidenceTier"))
                != "native_serialized_composed_exact"
                or safe_key(route.get("ownerStatus")) != "connected"
                or safe_key(route.get("scope")) != "mission"
                or safe_key(route.get("questTriggerStatus"))
                != (
                    "connected_root_native_playback_composed_"
                    "with_exact_alias"
                )
                or route.get("serverExchange") is not False
                or not root_key
                or root_key == scene_key
                or not safe_key(route.get("rootBaseRelation"))
                or not safe_key(route.get("rootBaseCausality"))
                or safe_key(route.get("aliasRelation"))
                != "cutscene_root_director_playable_asset"
                or not safe_key(route.get("nativeMappingId"))
                or not audit_report
                or audit_report not in source_files
                or not native_paths
                or len(matching_aliases) != 1
                or any(
                    not safe_key(path.get("sourceFile"))
                    or safe_key(path.get("sourceFile")) not in source_files
                    or not any(
                        isinstance(step, dict)
                        and safe_key(step.get("actionName")).startswith("Play")
                        for step in path.get("steps") or []
                    )
                    for path in native_paths
                )
                or (quest_id and not quest_id.startswith(f"{owner_mission}_q#"))
                or not isinstance(steps, list)
                or len(steps) < 5
                or not isinstance(steps[0], dict)
                or safe_key(steps[0].get("kind")) != "mission"
                or safe_key(steps[0].get("id")) != owner_mission
                or not any(
                    isinstance(step, dict)
                    and safe_key(step.get("kind")) == "native_action"
                    for step in steps[:-3]
                )
                or steps[-3] != {"id": root_key, "kind": "story_root"}
                or steps[-2] != {
                    "id": "CutsceneRoot._director -> TimelineHandle.Play",
                    "kind": "native_action",
                }
                or steps[-1] != {"id": scene_key, "kind": "story"}
            ):
                validated = []
                break
            validated.append(route)
        manifest_shape_valid = (
            safe_key(manifest_row.get("key")) == scene_key
            and safe_key(manifest_row.get("nominalMissionId")) == owner_mission
            and bool(composed_routes)
            and bool(alias_routes)
            and len(validated) == len(composed_routes)
        )
        if not manifest_shape_valid:
            if validation_failures is not None:
                source_files = sorted({
                    source_file
                    for route in [*composed_routes, *alias_routes]
                    for source_file in _string_list(route.get("sourceFiles"))
                }, key=natural_key)
                validation_failures.append({
                    "validator": "exact_composed_root_playback_closure_v2",
                    "gate": "route_contract",
                    "missionId": owner_mission,
                    "storyKey": scene_key,
                    "sourcePaths": source_files,
                    "sourceSha256": {
                        source_file: _sha256_file(ROOT / source_file)
                        for source_file in source_files
                        if (ROOT / source_file).is_file()
                    },
                    "expected": {
                        "manifestKey": scene_key,
                        "nominalMissionId": owner_mission,
                        "composedRouteCountAtLeast": 1,
                        "aliasRouteCountAtLeast": 1,
                        "allComposedRoutesValidated": True,
                    },
                    "actual": {
                        "manifestKey": safe_key(manifest_row.get("key")),
                        "nominalMissionId": safe_key(
                            manifest_row.get("nominalMissionId")
                        ),
                        "composedRouteCount": len(composed_routes),
                        "aliasRouteCount": len(alias_routes),
                        "validatedComposedRouteCount": len(validated),
                    },
                })
            continue
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus": (
                "closed_exact_composed_root_playback_context_"
                "no_relative_order"
            ),
            "relation": "cutscene_root_playback_alias_composed",
            "missionId": owner_mission,
            "rootStoryKeys": sorted({
                safe_key(route.get("rootStoryKey"))
                for route in validated
            }, key=natural_key),
            "rootBaseRelations": sorted({
                safe_key(route.get("rootBaseRelation"))
                for route in validated
            }, key=natural_key),
            "nativeMappingIds": sorted({
                safe_key(route.get("nativeMappingId"))
                for route in validated
            }, key=natural_key),
            "sourceFiles": sorted({
                source_file
                for route in validated
                for source_file in _string_list(route.get("sourceFiles"))
            }, key=natural_key),
            "nativePaths": [
                path
                for route in validated
                for path in route.get("nativePaths") or []
                if isinstance(path, dict)
            ],
            "playbackBoundary": (
                "the independently connected native route reaches the exact "
                "CutsceneRoot, whose serialized _director PPtr identifies the "
                "TimelineAsset executed by TimelineHandle.Play"
            ),
            "orderBoundary": (
                "the composed playback alias transfers mission context only; "
                "it supplies no relative Story-file edge"
            ),
            "graphEffect": "none",
        })
    return closed

def _closed_exact_connected_context_isolated_scenes(
    story_trigger_manifest: dict[str, Any],
    isolated_scene_keys: set[str],
    owner_mission: str,
    validation_failures: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Close exact connected context routes without asserting chronology.

    This validator deliberately supports route *shapes*, not named Story
    objects.  Each admitted relation has a separate fail-closed contract so a
    generic ``connected`` label can never become evidence by itself.
    """
    closed: list[dict[str, Any]] = []
    for scene_key in sorted(isolated_scene_keys, key=natural_key):
        manifest_row = story_trigger_manifest.get(scene_key)
        if not isinstance(manifest_row, dict):
            continue
        eligible_routes = [
            route
            for route in manifest_row.get("routes") or []
            if isinstance(route, dict)
            and (
                safe_key(route.get("relation"))
                == "levelscript_quest_state_gate"
                or (
                    safe_key(route.get("relation"))
                    == "dialog_tree_reachable_story_playback"
                    and safe_key(route.get("questTriggerStatus"))
                    == "exact_parent_quest_context_not_independent_trigger"
                )
            )
        ]
        if not eligible_routes:
            continue

        source_files = sorted({
            source_file
            for route in eligible_routes
            for source_file in _string_list(route.get("sourceFiles"))
        }, key=natural_key)
        source_hashes = {
            source_file: _sha256_file(ROOT / source_file)
            for source_file in source_files
            if (ROOT / source_file).is_file()
        }
        route = eligible_routes[0] if len(eligible_routes) == 1 else {}
        relation = safe_key(route.get("relation"))
        quest_id = safe_key(route.get("questId"))
        steps = route.get("steps")
        common_valid = (
            len(eligible_routes) == 1
            and safe_key(manifest_row.get("key")) == scene_key
            and safe_key(manifest_row.get("nominalMissionId")) == owner_mission
            and safe_key(manifest_row.get("attachmentStatus")) == "connected"
            and safe_key(route.get("storyKey")) == scene_key
            and safe_key(route.get("missionId")) == owner_mission
            and quest_id.startswith(f"{owner_mission}_q#")
            and safe_key(route.get("scope")) == "quest"
            and safe_key(route.get("ownerStatus")) == "connected"
            and safe_key(route.get("direction")) == "context"
            and source_files
            and len(source_hashes) == len(source_files)
            and isinstance(steps, list)
            and len(steps) >= 2
            and steps[0] == {
                "kind": "quest",
                "id": quest_id,
                "phase": safe_key(route.get("phase")),
            }
            and steps[-1] == {"kind": "story", "id": scene_key}
        )

        if relation == "dialog_tree_reachable_story_playback":
            path_ids = _string_list(route.get("sourcePathIds"))
            parent_story_key = safe_key(route.get("parentStoryKey"))
            relation_valid = (
                common_valid
                and safe_key(route.get("phase")) == "dialog_tree_story_playback"
                and safe_key(route.get("causality")) == "dependency"
                and safe_key(route.get("confidence")) == "native_exact_parent_quest"
                and safe_key(route.get("evidenceTier")) == "native_direct"
                and safe_key(route.get("certainty")) == "authored_reachable"
                and safe_key(route.get("nativeMappingId"))
                == "dialog-tree-reachable-story-playback-native-v1"
                and parent_story_key
                and parent_story_key != scene_key
                and safe_key(route.get("questTriggerStatus"))
                == "exact_parent_quest_context_not_independent_trigger"
                and route.get("serverExchange") is False
                and route.get("clientRequest") is False
                and route.get("expectedClientReply") is False
                and route.get("runtimeReplacementPossible") is True
                and route.get("occurrenceCount") == 1
                and bool(_string_list(route.get("carrierKinds")))
                and set(_string_list(route.get("carrierKinds")))
                <= {"trunk", "dialog"}
                and bool(_string_list(route.get("parentScopeRelations")))
                and len(path_ids) == 1
                and bool(re.fullmatch(r"[0-9A-Fa-f]{16}", path_ids[0]))
                and len(source_files) == 1
                and source_files[0].lower().endswith(
                    f"_p{path_ids[0].lower()}.json"
                )
                and len(steps) == 2
            )
            recovery_status = (
                "closed_exact_connected_dialog_tree_playback_context_"
                "no_relative_order"
            )
            closure = {
                "sceneKey": scene_key,
                "recoveryStatus": recovery_status,
                "relation": relation,
                "missionId": owner_mission,
                "questId": quest_id,
                "parentStoryKey": parent_story_key,
                "carrierKinds": _string_list(route.get("carrierKinds")),
                "sourcePathIds": path_ids,
                "nativeMappingId": safe_key(route.get("nativeMappingId")),
                "sourceFiles": source_files,
                "sourceSha256": source_hashes,
                "playbackBoundary": (
                    "the installed-game DialogTree contains one exact typed "
                    "carrier reachable from the registered quest-owned parent"
                ),
                "orderBoundary": (
                    "the carrier proves quest context and local playback only; "
                    "it supplies no relative Story-file edge"
                ),
                "graphEffect": "none",
            }
        elif relation == "levelscript_quest_state_gate":
            expected_source_suffix = (
                f"/{safe_key(route.get('levelId'))}/"
                f"{safe_key((route.get('scriptIds') or [''])[0])}.json"
            ).replace("\\", "/")
            relation_valid = (
                common_valid
                and safe_key(route.get("phase")) == "processing_gate"
                and safe_key(route.get("causality")) == "context"
                and safe_key(route.get("confidence")) == "native_typed_gate"
                and safe_key(route.get("nativeMappingId"))
                == LEVELSCRIPT_NATIVE_ACTION_MAPPING_ID
                and _string_list(route.get("eventNames"))
                == ["ScriptEvent_OnLeaderEnterTriggerVolume"]
                and len(_string_list(route.get("scriptIds"))) == 1
                and len(_string_list(route.get("actionNames"))) == 1
                and _string_list(route.get("actionNames"))[0].startswith("Play")
                and safe_key(route.get("conditionType")) == "CheckQuestState"
                and safe_key(route.get("conditionComparer")) == "Equal"
                and route.get("conditionQuestState") == 2
                and all(
                    isinstance(route.get(field), int)
                    and not isinstance(route.get(field), bool)
                    and route.get(field) > 0
                    for field in (
                        "headerLocalId",
                        "gateActionLocalId",
                        "actionLocalId",
                    )
                )
                and bool(re.fullmatch(r"0x[0-9a-fA-F]{4}", safe_key(route.get("actionCode"))))
                and bool(re.fullmatch(r"0x[0-9a-fA-F]{2}", safe_key(route.get("actionKind"))))
                and len(source_files) == 1
                and source_files[0].replace("\\", "/").endswith(
                    expected_source_suffix
                )
                and [step.get("kind") for step in steps]
                == ["quest", "native_event", "levelscript", "native_action", "story"]
            )
            recovery_status = (
                "closed_exact_quest_state_gated_playback_context_"
                "no_relative_order"
            )
            closure = {
                "sceneKey": scene_key,
                "recoveryStatus": recovery_status,
                "relation": relation,
                "missionId": owner_mission,
                "questId": quest_id,
                "levelId": safe_key(route.get("levelId")),
                "scriptIds": _string_list(route.get("scriptIds")),
                "eventNames": _string_list(route.get("eventNames")),
                "actionNames": _string_list(route.get("actionNames")),
                "conditionType": safe_key(route.get("conditionType")),
                "conditionComparer": safe_key(route.get("conditionComparer")),
                "conditionQuestState": route.get("conditionQuestState"),
                "nativeMappingId": safe_key(route.get("nativeMappingId")),
                "sourceFiles": source_files,
                "sourceSha256": source_hashes,
                "playbackBoundary": (
                    "the installed-game LevelScript enters the trigger volume, "
                    "waits for this quest to equal Processing, then executes "
                    "the typed Story playback action"
                ),
                "orderBoundary": (
                    "the quest-state gate proves activation context only; it "
                    "does not order this Story file against other mission files"
                ),
                "graphEffect": "none",
            }
        else:
            relation_valid = False
            recovery_status = ""
            closure = {}

        if relation_valid:
            closed.append(closure)
            continue
        if validation_failures is not None:
            validation_failures.append({
                "validator": "exact_connected_story_context_v1",
                "gate": f"{relation or 'eligible_route_count'}_contract",
                "missionId": owner_mission,
                "storyKey": scene_key,
                "sourcePaths": source_files,
                "sourceSha256": source_hashes,
                "expected": {
                    "eligibleRouteCount": 1,
                    "attachmentStatus": "connected",
                    "missionId": owner_mission,
                    "questIdPrefix": f"{owner_mission}_q#",
                    "relation": relation or "one supported exact relation",
                    "sourceFilesExist": True,
                    "graphEffect": "none",
                },
                "actual": {
                    "eligibleRouteCount": len(eligible_routes),
                    "attachmentStatus": safe_key(
                        manifest_row.get("attachmentStatus")
                    ),
                    "missionId": safe_key(route.get("missionId")),
                    "questId": quest_id,
                    "relation": relation,
                    "phase": safe_key(route.get("phase")),
                    "causality": safe_key(route.get("causality")),
                    "confidence": safe_key(route.get("confidence")),
                    "evidenceTier": safe_key(route.get("evidenceTier")),
                    "nativeMappingId": safe_key(route.get("nativeMappingId")),
                    "questTriggerStatus": safe_key(
                        route.get("questTriggerStatus")
                    ),
                    "condition": {
                        "type": safe_key(route.get("conditionType")),
                        "comparer": safe_key(route.get("conditionComparer")),
                        "questState": route.get("conditionQuestState"),
                    },
                    "sourceFileCount": len(source_files),
                    "existingSourceFileCount": len(source_hashes),
                },
            })
    return closed

def _exact_typed_mission_state_transition_checks(
    story_key: str,
    mission_state_id: str,
    value: Any,
) -> tuple[list[dict[str, Any]] | None, dict[str, Any] | None]:
    """Validate authored AirWall mission-state transition predicates."""
    checks = value if isinstance(value, list) else []
    shape_valid = (
        bool(checks)
        and all(
            isinstance(check, dict)
            and safe_key(check.get("id")) == mission_state_id
            and safe_key(check.get("targetMissionId")) == mission_state_id
            and safe_key(check.get("transition")) in {"rise", "down"}
            and safe_key(check.get("comparison")) in {"equal", "not_equal"}
            and isinstance(check.get("isQuest"), bool)
            and isinstance(check.get("detailState"), int)
            and not isinstance(check.get("detailState"), bool)
            for check in checks
        )
    )
    if not shape_valid:
        return None, {
            "validator": "exactAirWallMissionStateRadioContext",
            "gate": "typedMissionStateTransitionPredicates",
            "storyKey": story_key,
            "missionStateId": mission_state_id,
            "expected": {
                "nonempty": True,
                "transitions": ["rise", "down"],
                "comparisons": ["equal", "not_equal"],
                "idAndTargetMissionId": mission_state_id,
                "booleanIsQuest": True,
                "integerDetailState": True,
            },
            "actual": value,
        }
    return list(checks), None

def _closed_exact_system_selector_isolated_scenes(
    flow: dict[str, Any],
    isolated_scene_keys: set[str],
    owner_mission: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Close exact typed selector members while preserving zero graph effect."""
    closed: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for row in _flow_story_connections(flow):
        scene_key = safe_key(row.get("key"))
        if (
            scene_key not in isolated_scene_keys
            or safe_key(row.get("selectorKind"))
            != "typed_table_story_selector"
        ):
            continue
        alternatives = [
            {"role": safe_key(item.get("role")), "key": safe_key(item.get("key"))}
            for item in row.get("selectorAlternatives") or []
            if isinstance(item, dict)
        ]
        roles = [item["role"] for item in alternatives]
        keys = [item["key"] for item in alternatives]
        checks = {
            "missionMatches": safe_key(row.get("missionId")) == owner_mission,
            "graphNeutral": safe_key(row.get("graphEffect")) == "none",
            "groupPresent": bool(safe_key(row.get("selectorGroupId"))),
            "roleMatches": safe_key(row.get("selectorRole")) in roles,
            "sceneIsAlternative": scene_key in keys,
            "roleKeyMatches": any(
                item["role"] == safe_key(row.get("selectorRole"))
                and item["key"] == scene_key
                for item in alternatives
            ),
            "distinctRoles": len(roles) >= 2 and len(set(roles)) == len(roles),
            "distinctKeys": len(keys) >= 2 and len(set(keys)) == len(keys),
            "sourceFilesPresent": bool(_string_list(row.get("sourceFiles"))),
            "nativeMappingPresent": bool(safe_key(row.get("nativeMappingId"))),
            "nativeConsumersPresent": bool(row.get("nativeConsumers")),
            "orderBoundaryPresent": bool(safe_key(row.get("orderBoundary"))),
        }
        failed_checks = sorted(name for name, passed in checks.items() if not passed)
        if failed_checks:
            failures.append({
                "validator": "exact_typed_story_selector",
                "failedChecks": failed_checks,
                "missionId": owner_mission,
                "sceneKey": scene_key,
                "selectorGroupId": safe_key(row.get("selectorGroupId")),
                "expected": {
                    "missionId": owner_mission,
                    "graphEffect": "none",
                    "minimumDistinctAlternatives": 2,
                },
                "actual": {
                    "missionId": safe_key(row.get("missionId")),
                    "graphEffect": safe_key(row.get("graphEffect")),
                    "roles": roles,
                    "keys": keys,
                },
                "sourceFiles": _string_list(row.get("sourceFiles")),
            })
            continue
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus":
                "closed_exact_typed_story_selector_no_relative_order",
            "relation": safe_key(row.get("relation")),
            "missionId": owner_mission,
            "selectorKind": "typed_table_story_selector",
            "selectorGroupId": safe_key(row.get("selectorGroupId")),
            "selectorRole": safe_key(row.get("selectorRole")),
            "selectorAlternatives": alternatives,
            "sourceFiles": _string_list(row.get("sourceFiles")),
            "nativeMappingId": safe_key(row.get("nativeMappingId")),
            "nativeConsumers": row.get("nativeConsumers"),
            "orderBoundary": safe_key(row.get("orderBoundary")),
            "graphEffect": "none",
        })
    return closed, failures

@lru_cache(maxsize=1)
def _current_dialog_id_index_for_validation() -> dict[str, Any]:
    value = read_json(
        ROOT / "export_full" / "recovered" / "dialog_id_table_index.json",
        {},
    )
    return value if isinstance(value, dict) else {}

def _generic_prime_reachable_dialog_dependency_facts(
    row: Any,
    scene_key: str,
    owner_mission: str,
    quest_id: str,
    *,
    dialog_id_index: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Validate a typed parent-DialogTree carrier without an object catalog."""
    validator = "genericPrimeReachableDialogDependency"
    required_route = {
        "key": scene_key,
        "relation": "dialog_tree_prime_reachable_story_playback_dependency",
        "direction": "context",
        "phase": "dialog_tree_prime_reachable_story_playback",
        "confidence": "native_exact_prime_reachable_parent_quest_dependency",
        "evidenceTier": "native_exact_context",
        "storyOwnerMission": owner_mission,
        "storyBinding": True,
        "ownership": False,
        "dependencyOnly": True,
        "questActivation": False,
        "questPlayback": False,
        "questCompletion": False,
        "questTriggerStatus": (
            "exact_parent_dialog_completion_context_not_quest_playback_trigger"
        ),
        "nativeMappingId": (
            "dialog-tree-prime-reachable-completion-dependency-native-v1"
        ),
    }
    if not isinstance(row, dict) or any(
        row.get(field) != expected
        for field, expected in required_route.items()
    ):
        actual = {
            field: row.get(field)
            for field in required_route
        } if isinstance(row, dict) else {
            "type": type(row).__name__,
        }
        return None, {
            "validator": validator,
            "gate": "exactNonOwningQuestDependencyEnvelope",
            "missionId": owner_mission,
            "questId": quest_id,
            "storyKey": scene_key,
            "expected": required_route,
            "actual": actual,
        }
    parent_story_key = safe_key(row.get("parentStoryKey"))
    carriers = [
        carrier
        for carrier in row.get("dialogTreePrimeStoryPlaybackCarriers") or []
        if isinstance(carrier, dict)
    ]
    trunk_ids = _string_list(row.get("trunkIds"))
    dialog_ids = _string_list(row.get("dialogIds"))
    source_files = _string_list(row.get("sourceFiles"))
    source_path_ids = _string_list(row.get("sourcePathIds"))
    if (
        not parent_story_key
        or not carriers
        or len(source_files) != 1
        or len(source_path_ids) != 1
        or bool(trunk_ids) == bool(dialog_ids)
    ):
        return None, {
            "validator": validator,
            "gate": "boundedTypedCarrierSet",
            "missionId": owner_mission,
            "questId": quest_id,
            "storyKey": scene_key,
            "expected": {
                "oneParentStoryKey": True,
                "positiveCarrierCount": True,
                "sourceFileCount": 1,
                "sourcePathIdCount": 1,
                "exactlyOneCarrierIdKind": True,
            },
            "actual": {
                "parentStoryKey": parent_story_key,
                "carrierCount": len(carriers),
                "sourceFiles": source_files,
                "sourcePathIds": source_path_ids,
                "trunkIds": trunk_ids,
                "dialogIds": dialog_ids,
            },
        }
    current_registry = (
        dialog_id_index
        if isinstance(dialog_id_index, dict)
        else _current_dialog_id_index_for_validation()
    )
    current_carriers = (
        recover_dialog_tree_prime_reachable_carriers_for_parent(
            current_registry,
            parent_story_key,
            {scene_key},
            set(trunk_ids),
        )
    )
    if carriers != current_carriers:
        return None, {
            "validator": validator,
            "gate": "freshSerializedPrimeReachability",
            "missionId": owner_mission,
            "questId": quest_id,
            "storyKey": scene_key,
            "sourcePath": source_files[0],
            "expected": {
                "carrierCount": len(current_carriers),
                "carrierValues": [
                    safe_key(carrier.get("carrierValue"))
                    for carrier in current_carriers
                ],
                "sourceFiles": sorted({
                    safe_key(carrier.get("sourceFile"))
                    for carrier in current_carriers
                }),
                "sourcePathIds": sorted({
                    safe_key(carrier.get("sourcePathId"))
                    for carrier in current_carriers
                }),
            },
            "actual": {
                "carrierCount": len(carriers),
                "carrierValues": [
                    safe_key(carrier.get("carrierValue"))
                    for carrier in carriers
                ],
                "sourceFiles": source_files,
                "sourcePathIds": source_path_ids,
            },
        }
    current_trunk_ids = [
        safe_key(carrier.get("carrierValue"))
        for carrier in current_carriers
        if safe_key(carrier.get("carrierKind")) == "trunk"
    ]
    current_dialog_ids = [
        safe_key(carrier.get("carrierValue"))
        for carrier in current_carriers
        if safe_key(carrier.get("carrierKind")) == "dialog"
    ]
    if (
        source_files
        != sorted({
            safe_key(carrier.get("sourceFile"))
            for carrier in current_carriers
        })
        or source_path_ids
        != sorted({
            safe_key(carrier.get("sourcePathId"))
            for carrier in current_carriers
        })
        or trunk_ids != current_trunk_ids
        or dialog_ids != current_dialog_ids
    ):
        return None, {
            "validator": validator,
            "gate": "exactCarrierProjection",
            "missionId": owner_mission,
            "questId": quest_id,
            "storyKey": scene_key,
            "sourcePath": source_files[0],
            "expected": {
                "sourceFiles": sorted({
                    safe_key(carrier.get("sourceFile"))
                    for carrier in current_carriers
                }),
                "sourcePathIds": sorted({
                    safe_key(carrier.get("sourcePathId"))
                    for carrier in current_carriers
                }),
                "trunkIds": current_trunk_ids,
                "dialogIds": current_dialog_ids,
            },
            "actual": {
                "sourceFiles": source_files,
                "sourcePathIds": source_path_ids,
                "trunkIds": trunk_ids,
                "dialogIds": dialog_ids,
            },
        }
    source_path = ROOT / source_files[0]
    source_valid = (
        source_path.is_file()
        and source_path.parent.name == "TextAsset"
        and source_path.name.startswith(
            f"{parent_story_key}_p{source_path_ids[0]}"
        )
    )
    if not source_valid:
        return None, {
            "validator": validator,
            "gate": "exactCurrentParentSource",
            "missionId": owner_mission,
            "questId": quest_id,
            "storyKey": scene_key,
            "sourcePath": source_files[0],
            "expected": {
                "exists": True,
                "parentDirectory": "TextAsset",
                "filenamePrefix": (
                    f"{parent_story_key}_p{source_path_ids[0]}"
                ),
            },
            "actual": {
                "exists": source_path.is_file(),
                "parentDirectory": source_path.parent.name,
                "filename": source_path.name,
            },
        }
    return {
        "sceneKey": scene_key,
        "recoveryStatus": (
            "closed_exact_parent_dialog_dependency_no_relative_order"
        ),
        "relation": required_route["relation"],
        "missionId": owner_mission,
        "questId": quest_id,
        "parentStoryKey": parent_story_key,
        "carrierKinds": sorted({
            safe_key(carrier.get("carrierKind"))
            for carrier in current_carriers
        }),
        "trunkIds": trunk_ids,
        "dialogIds": dialog_ids,
        "dialogTreePrimeStoryPlaybackCarriers": current_carriers,
        "sourceFiles": source_files,
        "sourcePathIds": source_path_ids,
        "sourceSha256": {
            source_files[0]: _sha256_file(source_path),
        },
        "nativeMappingId": required_route["nativeMappingId"],
        "gameAssemblySha256": OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256,
        "playbackSemantics": (
            "the current registered parent DialogTree's exact prime-node "
            "paths reach every typed Story carrier retained for this file"
        ),
        "activationBoundary": (
            "MissionRuntime observes completion of the parent dialog; it "
            "does not identify the activator of either dialog"
        ),
        "orderBoundary": (
            "prime-node reachability orders nodes inside the parent "
            "DialogTree only; it creates no inter-file chronology"
        ),
    }, None

@lru_cache(maxsize=1)
def _current_game_assembly_sha256_for_validation() -> str:
    path = _configured_game_assembly_path()
    return _sha256_file(path).upper() if path.is_file() else ""

def _generic_registered_dialog_non_owning_context_facts(
    row: Any,
    scene_key: str,
    owner_mission: str,
    quest_id: str,
    *,
    dialog_id_index: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str | None]:
    """Compose a registered DialogTree with one exact non-owning context."""
    validator = "genericRegisteredDialogNonOwningContext"
    relation = safe_key(row.get("relation")) if isinstance(row, dict) else ""
    contracts = {
        "npc_proxy_tracking_dialog_navigation_context": {
            "phase": "tracking",
            "confidence": "native_exact_quest_navigation_context",
            "evidenceTier": "derived_exact_quest",
            "questTriggerStatus": (
                "tracked_proxy_navigation_context_not_quest_playback"
            ),
            "nativeMappingId": (
                "npc-proxy-tracking-dialog-navigation-context-native-v1"
            ),
            "serverExchange": False,
            "minimumSourceFiles": 5,
        },
        "npc_proxy_lazy_destroy_dialog_context": {
            "phase": "server_proxy_deactivation",
            "confidence": "native_exact_quest_navigation_context",
            "evidenceTier": "derived_exact_quest",
            "questTriggerStatus": (
                "tracked_proxy_navigation_and_dialog_configuration_context_"
                "not_quest_deactivation_or_playback"
            ),
            "nativeMappingId": (
                "npc-proxy-lazy-destroy-dialog-context-native-v1"
            ),
            "serverExchange": True,
            "minimumSourceFiles": 2,
        },
    }
    contract = contracts.get(relation)
    if contract is None:
        return None, None, "unsupportedRelation"
    required_route = {
        "key": scene_key,
        "relation": relation,
        "direction": "context",
        "phase": contract["phase"],
        "confidence": contract["confidence"],
        "evidenceTier": contract["evidenceTier"],
        "storyOwnerMission": owner_mission,
        "storyBinding": True,
        "ownership": False,
        "possibleAuthoredRoute": True,
        "questPlayback": False,
        "questCompletion": False,
        "questTriggerStatus": contract["questTriggerStatus"],
        "nativeMappingId": contract["nativeMappingId"],
        "serverExchange": contract["serverExchange"],
        "clientRequest": False,
        "expectedClientReply": False,
    }
    if not isinstance(row, dict) or any(
        row.get(field) != expected
        for field, expected in required_route.items()
    ):
        actual = {
            field: row.get(field)
            for field in required_route
        } if isinstance(row, dict) else {
            "type": type(row).__name__,
        }
        return None, {
            "validator": validator,
            "gate": "exactNonOwningContextEnvelope",
            "missionId": owner_mission,
            "questId": quest_id,
            "storyKey": scene_key,
            "expected": required_route,
            "actual": actual,
        }, None
    source_files = _string_list(row.get("sourceFiles"))
    source_paths = [ROOT / value for value in source_files]
    if (
        len(source_files) < int(contract["minimumSourceFiles"])
        or len(source_files) != len(set(source_files))
        or not all(path.is_file() for path in source_paths)
    ):
        return None, {
            "validator": validator,
            "gate": "exactCurrentContextSources",
            "missionId": owner_mission,
            "questId": quest_id,
            "storyKey": scene_key,
            "expected": {
                "minimumSourceFiles": contract["minimumSourceFiles"],
                "allUnique": True,
                "allExist": True,
            },
            "actual": {
                "sourceFiles": source_files,
                "sourceExists": {
                    value: path.is_file()
                    for value, path in zip(source_files, source_paths)
                },
            },
        }, None
    if relation == "npc_proxy_lazy_destroy_dialog_context":
        proxy_row = row.get("npcProxyTableRow")
        relation_valid = (
            safe_key(row.get("dialogId")) == scene_key
            and isinstance(proxy_row, dict)
            and proxy_row.get("lazyDestroy") is True
            and safe_key(proxy_row.get("lazyDestroyOverrideDialogId"))
            == scene_key
        )
        relation_actual = {
            "dialogId": row.get("dialogId"),
            "lazyDestroy": (
                proxy_row.get("lazyDestroy")
                if isinstance(proxy_row, dict) else None
            ),
            "lazyDestroyOverrideDialogId": (
                proxy_row.get("lazyDestroyOverrideDialogId")
                if isinstance(proxy_row, dict) else None
            ),
        }
    else:
        child_story_keys = _string_list(row.get("childStoryKeys"))
        child_routes = [
            route
            for route in row.get("dialogTreeChildRoutes") or []
            if isinstance(route, dict)
        ]
        route_child_keys = sorted({
            safe_key(route.get("childStoryKey"))
            for route in child_routes
            if safe_key(route.get("childStoryKey"))
        }, key=natural_key)
        relation_valid = (
            bool(safe_key(row.get("npcProxyId")))
            and safe_key(row.get("trackingVisibilityRole"))
            == "navigation_marker_visibility_only_not_dialog_activation"
            and bool(child_story_keys)
            and route_child_keys == sorted(child_story_keys, key=natural_key)
            and all(route.get("occurrences") for route in child_routes)
        )
        relation_actual = {
            "npcProxyId": row.get("npcProxyId"),
            "trackingVisibilityRole": row.get("trackingVisibilityRole"),
            "childStoryKeys": child_story_keys,
            "routeChildStoryKeys": route_child_keys,
            "childRouteCount": len(child_routes),
        }
    if not relation_valid:
        return None, {
            "validator": validator,
            "gate": "exactTypedRelationPayload",
            "missionId": owner_mission,
            "questId": quest_id,
            "storyKey": scene_key,
            "expected": {
                "relation": relation,
                "typedPayloadMatchesStory": True,
            },
            "actual": relation_actual,
        }, None
    current_registry = (
        dialog_id_index
        if isinstance(dialog_id_index, dict)
        else _current_dialog_id_index_for_validation()
    )
    definition = recover_dialog_tree_definition_evidence(scene_key)
    definition_facts, definition_failure = (
        _generic_registered_dialog_tree_definition_facts(
            scene_key,
            current_registry.get(scene_key),
            definition,
            require_control_flow=False,
        )
    )
    if definition_failure is not None:
        definition_failure.update({
            "validator": validator,
            "gate": "exactCurrentRegisteredDialogDefinition",
            "missionId": owner_mission,
            "questId": quest_id,
            "storyKey": scene_key,
        })
        return None, definition_failure, None
    current_binary_hash = _current_game_assembly_sha256_for_validation()
    if current_binary_hash != OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256:
        return None, {
            "validator": validator,
            "gate": "currentGameAssembly",
            "missionId": owner_mission,
            "questId": quest_id,
            "storyKey": scene_key,
            "sourcePath": str(_configured_game_assembly_path()),
            "expected": OFFLINE_EXHAUSTION_GAMEASSEMBLY_SHA256,
            "actual": current_binary_hash,
        }, None
    definition_source = safe_key(definition_facts.get("sourceFile"))
    all_source_files = sorted(
        set(source_files) | ({definition_source} if definition_source else set()),
        key=natural_key,
    )
    return {
        "sceneKey": scene_key,
        "recoveryStatus": (
            "closed_exact_non_owning_dialog_context_no_relative_order"
        ),
        "relation": relation,
        "missionId": owner_mission,
        "questId": quest_id,
        "npcProxyId": safe_key(row.get("npcProxyId")),
        "levelIds": _string_list(row.get("levelIds")),
        "childStoryKeys": _string_list(row.get("childStoryKeys")),
        "dialogTreeDefinition": definition_facts,
        "contextRoute": {
            key: row.get(key)
            for key in (
                "relation",
                "phase",
                "confidence",
                "evidenceTier",
                "questTriggerStatus",
                "networkRole",
                "serverExchange",
                "upstreamServerStateSources",
                "serverFields",
                "nativeConsumers",
                "nativeMappingId",
            )
        },
        "sourceFiles": all_source_files,
        "sourceSha256": {
            value: _sha256_file(ROOT / value)
            for value in all_source_files
        },
        "originalBinaryFiles": [
            _configured_game_assembly_path().as_posix(),
        ],
        "gameAssemblySha256": current_binary_hash,
        "activationBoundary": safe_key(row.get("questTriggerStatus")),
        "orderBoundary": (
            "the typed proxy context and the DialogTree's internal graph do "
            "not place this file against another Story file or prove which "
            "quest transition activates interaction"
        ),
        "graphEffect": "none",
    }, None, None

def _closed_exact_runtime_config_isolated_scenes(
    flow: dict[str, Any],
    isolated_scene_keys: set[str],
    owner_mission: str,
    offline_exhaustion_index: dict[str, dict[str, Any]] | None = None,
    validation_failures: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Close exact executable Story configs that encode no chronology.

    ``NpcProxyEx`` rows are executable configuration, not loose name matches:
    the installed client selects ``exDatas[activeCondIndex - 1]`` and
    ``NpcInteractComponent`` reads that row's ``dialogId``.  The adjacent
    ``missionId`` is consumed separately by the paused-mission deactivation
    guard.  This establishes a mission-scoped, selectable interaction dialog,
    but the server-selected row index and proxy/table ordering do not establish
    relative Story order.

    ``CheckTalkOptionFinish`` objective conditions are exact Story-to-quest
    completion dependencies. They prove that one quest consumes the dialog's
    synchronized finish state, but not which mission or quest starts playback.

    Counted LevelScript interactive maps are similarly exact: a typed
    ``LevelInteractiveData`` record's component-94 ``type_id`` selects one
    dialog or ReadingPopUp Story file. This recovers the source script and
    interactive identity, but neither map/local-id order nor object placement
    establishes activation timing or relative Story order.
    """
    closed: list[dict[str, Any]] = []
    offline_exhaustion_index = offline_exhaustion_index or {}
    for row in _flow_story_connections(flow):
        scene_key = safe_key(row.get("key"))
        definition = offline_exhaustion_index.get(scene_key)
        content_ids = _string_list(row.get("snsContentIds"))
        if (
            scene_key not in isolated_scene_keys
            or safe_key(row.get("relation")) != "sns_authored_mission_link"
            or safe_key(row.get("direction")) != "context"
            or safe_key(row.get("phase")) != "mission_link"
            or safe_key(row.get("confidence")) != "authored_direct"
            or safe_key(row.get("storyOwnerMission")) != owner_mission
            or safe_key(row.get("snsDialogId")) != scene_key
            or safe_key(row.get("snsMissionId")) != owner_mission
            or row.get("snsContentType") != 12
            or not content_ids
            or not isinstance(definition, dict)
            or safe_key(definition.get("missionId")) != owner_mission
            or safe_key(definition.get("relatedMissionId")) != owner_mission
            or definition.get("definitionTables") != [
                "SNSDialogTable",
                "SNSDialogOptionTable",
            ]
            or any(
                safe_key(
                    (definition.get("linkMissionIdsByContentId") or {}).get(
                        content_id
                    )
                ) != owner_mission
                or owner_mission not in (
                    definition.get("contentParamsByContentId") or {}
                ).get(content_id, [])
                for content_id in content_ids
            )
        ):
            continue
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus":
                "closed_exact_authored_sns_mission_link_no_relative_order",
            "relation": "sns_authored_mission_link",
            "missionId": owner_mission,
            "snsContentIds": content_ids,
            "snsContentType": 12,
            "sourceFiles": [
                "export_full/structured/StreamingAssets/Table/"
                "SNSDialogTable.json",
                "export_full/structured/StreamingAssets/Table/"
                "SNSDialogOptionTable.json",
                "export_full/structured/StreamingAssets/Table/"
                "SNSChatTable.json",
            ],
            "activationBoundary": (
                "the exact SNSDialogTable relatedMissionId and terminal "
                "mission-link content node attach this SNS file to the mission"
            ),
            "orderBoundary": (
                "the authored mission link is context, not a playback "
                "activator; the internal SNS message chain orders only this "
                "file's messages and does not place it among mission scenes"
            ),
        })
    for quest in flow.get("quests") or []:
        if not isinstance(quest, dict):
            continue
        quest_id = safe_key(quest.get("id"))
        for row in quest.get("storyConnections") or []:
            if not isinstance(row, dict):
                continue
            scene_key = safe_key(row.get("key"))
            objective_index = row.get("objectiveIndex")
            tracking_index = row.get("trackingIndex")
            if (
                scene_key not in isolated_scene_keys
                or not quest_id.startswith(f"{owner_mission}_q#")
                or safe_key(row.get("kind")) != "sns"
                or safe_key(row.get("relation"))
                != "objective_tracking_story_reference"
                or safe_key(row.get("direction")) != "context"
                or safe_key(row.get("phase")) != "tracking"
                or safe_key(row.get("confidence"))
                != "native_typed_context"
                or safe_key(row.get("trackingType")) != "SnsTrackingInfo"
                or row.get("playback") is not False
                or safe_key(row.get("attachmentBoundary"))
                != (
                    "authored objective tracking attachment only; "
                    "SnsTrackingInfo.Execute is not SNS playback"
                )
                or safe_key(row.get("orderBoundary"))
                != (
                    "tracking configuration establishes no activation time "
                    "or relative Story order"
                )
                or not re.fullmatch(
                    r"MissionRuntimeAsset\.questDic\[\*\]\.objectiveList"
                    r"\[\d+\]\.trackingInfoList\[\d+\]\.snsDialogId",
                    safe_key(row.get("source")),
                )
                or not isinstance(objective_index, int)
                or isinstance(objective_index, bool)
                or objective_index <= 0
                or not isinstance(tracking_index, int)
                or isinstance(tracking_index, bool)
                or tracking_index < 0
            ):
                continue
            closed.append({
                "sceneKey": scene_key,
                "recoveryStatus":
                    "closed_exact_mission_tracking_context_no_relative_order",
                "relation": "objective_tracking_story_reference",
                "missionId": owner_mission,
                "questId": quest_id,
                "objectiveIndex": objective_index,
                "trackingIndex": tracking_index,
                "trackingType": "SnsTrackingInfo",
                "activationBoundary": (
                    "the exact MissionRuntime objective config attaches this "
                    "SNS conversation to client tracking; the native tracking "
                    "type does not start SNS playback"
                ),
                "orderBoundary": (
                    "quest attachment establishes mission context but no "
                    "activation time or relative Story order"
                ),
                "sourceFile": (
                    "export_full/structured/Persistent/Data/Json/"
                    f"MissionRuntimeAsset/{owner_mission}.json"
                ),
            })

    for row in flow.get("missionStoryConnections") or []:
        if not isinstance(row, dict):
            continue
        scene_key = safe_key(row.get("key"))
        accept_mode = row.get("acceptMode")
        finish_id = row.get("finishId")
        if (
            scene_key not in isolated_scene_keys
            or safe_key(row.get("kind")) != "dialog"
            or safe_key(row.get("relation")) != "mission_accept_dialog"
            or safe_key(row.get("direction")) != "story_to_mission"
            or safe_key(row.get("phase")) != "accept"
            or safe_key(row.get("confidence")) != "native_typed_direct"
            or safe_key(row.get("source"))
            != (
                f"MissionRuntimeAsset/{owner_mission}_meta.json."
                "acceptMode.modeInfo.dialogId"
            )
            or not isinstance(accept_mode, int)
            or isinstance(accept_mode, bool)
            or accept_mode < 0
            or safe_key(row.get("acceptModeType"))
            != "MissionAcceptMode+NPCInfo"
            or not safe_key(row.get("npcProxyId"))
            or not safe_key(row.get("levelId"))
            or not isinstance(finish_id, int)
            or isinstance(finish_id, bool)
        ):
            continue
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus":
                "closed_exact_mission_accept_dialog_no_relative_order",
            "relation": "mission_accept_dialog",
            "missionId": owner_mission,
            "phase": "accept",
            "acceptMode": accept_mode,
            "acceptModeType": "MissionAcceptMode+NPCInfo",
            "npcProxyId": safe_key(row.get("npcProxyId")),
            "levelId": safe_key(row.get("levelId")),
            "finishId": finish_id,
            "attachmentSemantics": (
                "the exact typed MissionRuntime meta asset selects this "
                "dialog for the mission-accept interaction"
            ),
            "orderBoundary": (
                "the accept phase proves mission ownership and lifecycle "
                "placement, but does not create a relative edge to another "
                "Story file"
            ),
            "sourceFile": (
                "export_full/structured/Persistent/Data/Json/"
                f"MissionRuntimeAsset/{owner_mission}_meta.json"
            ),
        })

    already_closed = {row["sceneKey"] for row in closed}
    for quest in flow.get("quests") or []:
        if not isinstance(quest, dict):
            continue
        quest_id = safe_key(quest.get("id"))
        for row in quest.get("storyConnections") or []:
            if not isinstance(row, dict):
                continue
            scene_key = safe_key(row.get("key"))
            if (
                scene_key in already_closed
                or scene_key not in isolated_scene_keys
                or safe_key(row.get("relation"))
                != "dialog_tree_prime_reachable_story_playback_dependency"
            ):
                continue
            facts, failure = (
                _generic_prime_reachable_dialog_dependency_facts(
                    row,
                    scene_key,
                    owner_mission,
                    quest_id,
                )
            )
            if failure is not None:
                if validation_failures is not None:
                    validation_failures.append(failure)
                continue
            if facts is not None:
                closed.append(facts)

    already_closed = {row["sceneKey"] for row in closed}
    non_owning_dialog_contexts: dict[
        str,
        list[tuple[str, dict[str, Any]]],
    ] = defaultdict(list)
    for quest in flow.get("quests") or []:
        if not isinstance(quest, dict):
            continue
        quest_id = safe_key(quest.get("id"))
        for row in quest.get("storyConnections") or []:
            if not isinstance(row, dict):
                continue
            scene_key = safe_key(row.get("key"))
            if (
                scene_key in already_closed
                or scene_key not in isolated_scene_keys
                or safe_key(row.get("relation")) not in {
                    "npc_proxy_tracking_dialog_navigation_context",
                    "npc_proxy_lazy_destroy_dialog_context",
                }
            ):
                continue
            non_owning_dialog_contexts[scene_key].append((quest_id, row))
    for scene_key, candidates in sorted(
        non_owning_dialog_contexts.items(),
        key=lambda item: natural_key(item[0]),
    ):
        candidate_facts: list[dict[str, Any]] = []
        candidate_failed = False
        for quest_id, row in candidates:
            facts, failure, _ = (
                _generic_registered_dialog_non_owning_context_facts(
                    row,
                    scene_key,
                    owner_mission,
                    quest_id,
                )
            )
            if failure is not None:
                candidate_failed = True
                if validation_failures is not None:
                    validation_failures.append(failure)
                continue
            if facts is not None:
                candidate_facts.append(facts)
        if candidate_failed or len(candidate_facts) != len(candidates):
            continue
        merged = dict(candidate_facts[0])
        merged["questIds"] = sorted({
            safe_key(facts.get("questId"))
            for facts in candidate_facts
            if safe_key(facts.get("questId"))
        }, key=natural_key)
        merged["relations"] = sorted({
            safe_key(facts.get("relation"))
            for facts in candidate_facts
            if safe_key(facts.get("relation"))
        }, key=natural_key)
        merged["contextRoutes"] = [
            {
                "questId": safe_key(facts.get("questId")),
                **(facts.get("contextRoute") or {}),
            }
            for facts in candidate_facts
        ]
        merged["sourceFiles"] = sorted({
            source_file
            for facts in candidate_facts
            for source_file in _string_list(facts.get("sourceFiles"))
        }, key=natural_key)
        merged["sourceSha256"] = {
            source_file: _sha256_file(ROOT / source_file)
            for source_file in merged["sourceFiles"]
        }
        closed.append(merged)

    for row in _flow_story_connections(flow):
        scene_key = safe_key(row.get("key"))
        if (
            scene_key not in isolated_scene_keys
            or safe_key(row.get("relation"))
            != "focus_mode_interact_locked_radio"
            or safe_key(row.get("direction")) != "context"
            or safe_key(row.get("phase")) != "interact_locked"
            or safe_key(row.get("confidence")) != "direct_mission_scope"
            or safe_key(row.get("storyOwnerMission")) != owner_mission
            or safe_key(row.get("focusModeField"))
            != "radioIdInteractLocked"
            or not safe_key(row.get("focusModeId"))
            or not safe_key(row.get("focusModeMissionId"))
            or not isinstance(row.get("subDataParentId"), int)
            or isinstance(row.get("subDataParentId"), bool)
        ):
            continue
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus":
                "closed_exact_runtime_config_no_relative_order",
            "relation": "focus_mode_interact_locked_radio",
            "focusModeId": safe_key(row.get("focusModeId")),
            "focusModeMissionId": safe_key(
                row.get("focusModeMissionId")
            ),
            "focusModeField": "radioIdInteractLocked",
            "subDataParentId": row["subDataParentId"],
            "activationBoundary": (
                "the exact FocusModeInstanceTable field selects the radio "
                "when interaction is locked, but does not establish when "
                "that focus-mode state is entered"
            ),
            "orderBoundary": (
                "table row order, focus-mode naming, and parent id do not "
                "establish relative Story chronology"
            ),
        })
    for row in _flow_story_connections(flow):
        scene_key = safe_key(row.get("key"))
        mission_state_id = safe_key(row.get("missionStateId"))
        target_checks, target_check_failure = (
            _exact_typed_mission_state_transition_checks(
                scene_key,
                mission_state_id,
                row.get("targetMissionStateChecks"),
            )
        )
        is_target_airwall_row = (
            scene_key in isolated_scene_keys
            and safe_key(row.get("relation"))
            == "airwall_mission_state_radio_playback_context"
            and safe_key(row.get("storyOwnerMission")) == owner_mission
        )
        if (
            is_target_airwall_row
            and target_check_failure is not None
            and validation_failures is not None
        ):
            failure = dict(target_check_failure)
            failure["sourceFiles"] = _string_list(row.get("sourceFiles"))
            validation_failures.append(failure)
        if (
            scene_key not in isolated_scene_keys
            or safe_key(row.get("relation"))
            != "airwall_mission_state_radio_playback_context"
            or safe_key(row.get("direction")) != "context"
            or safe_key(row.get("phase"))
            != "airwall_mission_state_gate"
            or safe_key(row.get("confidence"))
            != "native_exact_serialized_co_carrier"
            or safe_key(row.get("evidenceTier")) != "direct"
            or safe_key(row.get("storyOwnerMission")) != owner_mission
            or not mission_state_id
            or row.get("storyBinding") is not True
            or row.get("ownership") is not False
            or row.get("dependencyOnly") is not False
            or row.get("questActivation") is not False
            or row.get("questPlayback") is not False
            or row.get("questCompletion") is not False
            or safe_key(row.get("nativeMappingId"))
            != "leveldata-airwall-mission-radio-memorypack-v1d4"
            or "GameAction.PlayRadio" not in safe_key(
                row.get("nativeConsumer")
            )
            or not _string_list(row.get("levelIds"))
            or not _string_list(row.get("sourceFiles"))
            or not safe_key(row.get("sourcePath"))
            or not isinstance(row.get("recordOffset"), int)
            or isinstance(row.get("recordOffset"), bool)
            or not isinstance(row.get("recordEndOffset"), int)
            or isinstance(row.get("recordEndOffset"), bool)
            or row["recordEndOffset"] <= row["recordOffset"]
            or row.get("serializedMemberCount") != 8
            or not safe_key(row.get("airWallGroupId"))
            or not isinstance(row.get("airWallSlotId"), int)
            or isinstance(row.get("airWallSlotId"), bool)
            or not isinstance(row.get("airWallDefaultOn"), bool)
            or target_checks is None
        ):
            continue
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus":
                "closed_exact_native_playback_context_no_relative_order",
            "relation": "airwall_mission_state_radio_playback_context",
            "missionStateId": mission_state_id,
            "targetMissionStateChecks": target_checks,
            "levelIds": _string_list(row.get("levelIds")),
            "sourceFiles": _string_list(row.get("sourceFiles")),
            "sourcePath": safe_key(row.get("sourcePath")),
            "recordOffset": row["recordOffset"],
            "recordEndOffset": row["recordEndOffset"],
            "airWallGroupId": safe_key(row.get("airWallGroupId")),
            "nativeMappingId": safe_key(row.get("nativeMappingId")),
            "activationBoundary": (
                "the exact AirWall row gates wall state on synchronized "
                "mission/quest state and the later pushback callback plays "
                "this radio; it does not prove a mission transition trigger "
                "or quest-owned playback"
            ),
            "orderBoundary": (
                "wall state, row order, and a later local pushback event do "
                "not establish relative Story chronology"
            ),
        })
    for row in _flow_story_connections(flow):
        scene_key = safe_key(row.get("key"))
        candidate_quest_ids = _string_list(row.get("candidateQuestIds"))
        if (
            scene_key not in isolated_scene_keys
            or safe_key(row.get("relation"))
            != "entity_tracking_interactive_story_target"
            or safe_key(row.get("direction")) != "context"
            or safe_key(row.get("phase")) != "tracking"
            or safe_key(row.get("confidence"))
            != "native_exact_tracked_interactive_property"
            or safe_key(row.get("evidenceTier")) != "native_exact_context"
            or safe_key(row.get("storyOwnerMission")) != owner_mission
            or safe_key(row.get("trackingMissionId")) != owner_mission
            or safe_key(row.get("questTriggerStatus"))
            != "navigation_target_configured_story_not_playback"
            or safe_key(row.get("executionSide")) != "client"
            or safe_key(row.get("networkRole"))
            != "local_navigation_context"
            or row.get("clientNavigationOnly") is not True
            or row.get("serverExchange") is not False
            or not candidate_quest_ids
            or any(
                not quest_id.startswith(f"{owner_mission}_q#")
                for quest_id in candidate_quest_ids
            )
            or not _string_list(row.get("levelIds"))
            or not _string_list(row.get("scriptIds"))
            or not _string_list(row.get("localScriptIds"))
            or not _string_list(row.get("entitySlotIds"))
            or not _string_list(row.get("entityDetailIds"))
            or not _string_list(row.get("entityTemplateIds"))
            or not _string_list(row.get("entityTemplatePaths"))
            or not _string_list(row.get("registrySourceFiles"))
            or not _string_list(row.get("interactiveTableSourceFiles"))
            or not _string_list(row.get("sourceFiles"))
            or safe_key(row.get("interactivePropertyKey")) != "type_id"
            or not isinstance(row.get("trackingObjectiveIndex"), int)
            or isinstance(row.get("trackingObjectiveIndex"), bool)
            or not isinstance(row.get("trackingIndex"), int)
            or isinstance(row.get("trackingIndex"), bool)
            or not isinstance(row.get("interactiveEntryOffset"), int)
            or isinstance(row.get("interactiveEntryOffset"), bool)
            or not isinstance(row.get("interactivePropertyOffset"), int)
            or isinstance(row.get("interactivePropertyOffset"), bool)
            or not isinstance(row.get("interactiveStoryOffset"), int)
            or isinstance(row.get("interactiveStoryOffset"), bool)
            or not (
                row["interactiveEntryOffset"]
                < row["interactivePropertyOffset"]
                < row["interactiveStoryOffset"]
            )
        ):
            continue
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus":
                "closed_exact_tracked_interactive_context_no_relative_order",
            "relation": "entity_tracking_interactive_story_target",
            "missionId": owner_mission,
            "candidateQuestIds": candidate_quest_ids,
            "trackingObjectiveIndex": row["trackingObjectiveIndex"],
            "trackingIndex": row["trackingIndex"],
            "levelIds": _string_list(row.get("levelIds")),
            "scriptIds": _string_list(row.get("scriptIds")),
            "localScriptIds": _string_list(row.get("localScriptIds")),
            "entitySlotIds": _string_list(row.get("entitySlotIds")),
            "entityDetailIds": _string_list(row.get("entityDetailIds")),
            "entityTemplateIds": _string_list(row.get("entityTemplateIds")),
            "interactivePropertyKey": "type_id",
            "interactiveEntryOffset": row["interactiveEntryOffset"],
            "interactivePropertyOffset": row["interactivePropertyOffset"],
            "interactiveStoryOffset": row["interactiveStoryOffset"],
            "sourceFiles": _string_list(row.get("sourceFiles")),
            "activationBoundary": (
                "the exact MissionRuntime EntityTrackingInfo target resolves "
                "through the registry to an interactive whose serialized "
                "type_id is this Story key; this is client navigation "
                "configuration, not playback or quest completion"
            ),
            "orderBoundary": (
                "tracking index, entity slot, serialized offsets, and world "
                "placement do not establish activation time or relative "
                "Story chronology"
            ),
        })
    completion_grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _flow_story_connections(flow):
        scene_key = safe_key(row.get("key"))
        context_mission = safe_key(row.get("contextMissionBundle"))
        context_quest = safe_key(row.get("contextQuestId"))
        source = safe_key(row.get("source"))
        objective_index = row.get("objectiveIndex")
        finish_id = row.get("finishId")
        if (
            scene_key not in isolated_scene_keys
            or safe_key(row.get("relation")) != "objective_condition"
            or safe_key(row.get("direction")) != "story_to_quest"
            or safe_key(row.get("phase")) != "progress"
            or safe_key(row.get("confidence")) != "direct"
            or safe_key(row.get("conditionType"))
            != "CheckTalkOptionFinish"
            or not re.fullmatch(
                r"MissionRuntimeAsset\.questDic\[\*\]\.objectiveList"
                r"\[\d+\]\.condition\._dialogId",
                source,
            )
            or not context_mission
            or not context_quest
            or not isinstance(objective_index, int)
            or isinstance(objective_index, bool)
            or objective_index <= 0
            or not isinstance(finish_id, int)
            or isinstance(finish_id, bool)
        ):
            continue
        completion_grouped[scene_key].append(row)

    for scene_key, rows in completion_grouped.items():
        targets = {
            (
                safe_key(row.get("contextMissionBundle")),
                safe_key(row.get("contextQuestId")),
                int(row["objectiveIndex"]),
                int(row["finishId"]),
            )
            for row in rows
        }
        if not targets:
            continue
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus":
                "closed_exact_mission_dialog_finish_dependency_no_relative_order",
            "relation": "objective_condition",
            "nominalStoryMissionId": owner_mission,
            "dependentMissionIds": sorted({
                mission_id
                for mission_id, _quest_id, _objective_index, _finish_id
                in targets
            }, key=natural_key),
            "dependentQuestIds": sorted({
                quest_id
                for _mission_id, quest_id, _objective_index, _finish_id
                in targets
            }, key=natural_key),
            "objectiveIndexes": sorted({
                objective_index
                for _mission_id, _quest_id, objective_index, _finish_id
                in targets
            }),
            "finishIds": sorted({
                finish_id
                for _mission_id, _quest_id, _objective_index, finish_id
                in targets
            }),
            "dependencySemantics": (
                "the quest objective reads the exact dialog's synchronized "
                "completion state through CheckTalkOptionFinish"
            ),
            "activationBoundary": (
                "the objective observes completion only; it does not prove "
                "which mission, quest, NPC interaction, or other runtime path "
                "starts the dialog"
            ),
            "orderBoundary": (
                "the dependency places quest completion after dialog finish "
                "but creates no relative edge between Story files"
            ),
            "sourceFiles": sorted({
                safe_key(row.get("sourceFile"))
                for row in rows
                if safe_key(row.get("sourceFile"))
            }),
        })

    quest_action_grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    expected_quest_actions = {
        "client_action_start": (1, "start"),
        "client_action_succeed": (2, "succeed"),
        "client_action_failed": (4, "failed"),
    }

    def append_exact_quest_action(
        raw_row: dict[str, Any],
        quest_id: str,
    ) -> None:
        scene_key = safe_key(raw_row.get("key"))
        relation = safe_key(raw_row.get("relation"))
        expected = expected_quest_actions.get(relation)
        if (
            scene_key not in isolated_scene_keys
            or not quest_id
            or not expected
            or safe_key(raw_row.get("direction")) != "quest_to_story"
            or safe_key(raw_row.get("phase")) != expected[1]
            or safe_key(raw_row.get("confidence")) != "native_typed_direct"
            or raw_row.get("actionSlot") != expected[0]
            or not isinstance(raw_row.get("actionId"), int)
            or isinstance(raw_row.get("actionId"), bool)
            or int(raw_row["actionId"]) < 0
            or not safe_key(raw_row.get("actionType"))
            or not re.fullmatch(
                r"MissionRuntimeAsset\.clientActionMapKey\[\d+\] -> "
                r"actionMapRaw\.actionList\[\d+\]\._[A-Za-z]+Id",
                safe_key(raw_row.get("source")),
            )
        ):
            return
        quest_action_grouped[scene_key].append({
            **raw_row,
            "contextQuestId": quest_id,
        })

    for quest in flow.get("quests") or []:
        if not isinstance(quest, dict):
            continue
        quest_id = safe_key(quest.get("id"))
        if not quest_id:
            continue
        for raw_row in quest.get("storyConnections") or []:
            if isinstance(raw_row, dict):
                append_exact_quest_action(raw_row, quest_id)
    for raw_row in flow.get("missionStoryConnections") or []:
        if (
            isinstance(raw_row, dict)
            and safe_key(raw_row.get("contextMissionBundle"))
            and safe_key(raw_row.get("contextMissionBundle")) != owner_mission
        ):
            append_exact_quest_action(
                raw_row,
                safe_key(raw_row.get("contextQuestId")),
            )
    for scene_key, rows in quest_action_grouped.items():
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus":
                "closed_exact_mission_quest_client_action_no_relative_order",
            "relation": safe_key(rows[0].get("relation")),
            "missionId": owner_mission,
            "contextMissionIds": sorted({
                safe_key(row.get("contextMissionBundle")) or owner_mission
                for row in rows
            }, key=natural_key),
            "contextMissionMismatch": any(
                safe_key(row.get("contextMissionBundle"))
                and safe_key(row.get("contextMissionBundle")) != owner_mission
                for row in rows
            ),
            "questIds": sorted({
                safe_key(row.get("contextQuestId"))
                for row in rows
                if safe_key(row.get("contextQuestId"))
            }, key=natural_key),
            "phases": sorted({
                safe_key(row.get("phase"))
                for row in rows
                if safe_key(row.get("phase"))
            }),
            "actionSlots": sorted({
                int(row["actionSlot"])
                for row in rows
            }),
            "actionIds": sorted({
                int(row["actionId"])
                for row in rows
            }),
            "actionTypes": sorted({
                safe_key(row.get("actionType"))
                for row in rows
                if safe_key(row.get("actionType"))
            }),
            "playbackSemantics": (
                "the exact typed MissionRuntime client action plays this "
                "Story id at the named quest lifecycle phase"
            ),
            "orderBoundary": (
                "quest lifecycle placement proves mission/quest playback "
                "context but creates no relative edge between Story files"
            ),
            "sourceFiles": sorted({
                safe_key(row.get("sourceFile"))
                or (
                    "export_full/structured/Persistent/Data/Json/"
                    f"MissionRuntimeAsset/{owner_mission}.json"
                )
                for row in rows
            }),
        })

    already_closed = {row["sceneKey"] for row in closed}
    tracked_proxy_grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    tracked_proxy_context_by_scene: dict[str, dict[str, Any]] = {}
    for row in _flow_story_connections(flow):
        scene_key = safe_key(row.get("key"))
        if (
            scene_key in already_closed
            or scene_key not in isolated_scene_keys
            or safe_key(row.get("relation"))
            != "unique_mission_tracked_npc_proxy_dialog_context"
        ):
            continue
        context, failure = _validate_general_tracked_proxy_flow_context(
            row,
            owner_mission,
        )
        if failure is not None:
            if validation_failures is not None:
                validation_failures.append(failure)
            continue
        tracked_proxy_grouped[scene_key].append(row)
        tracked_proxy_context_by_scene[scene_key] = context

    for scene_key, rows in tracked_proxy_grouped.items():
        if len(rows) != 1:
            continue
        row = rows[0]
        context = tracked_proxy_context_by_scene[scene_key]
        cross_mission_context = context.get("crossMission") is True
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus":
                (
                    "closed_exact_cross_mission_runtime_config_"
                    "no_relative_order"
                    if cross_mission_context
                    else "closed_exact_runtime_config_no_relative_order"
                ),
            "relation":
                "unique_mission_tracked_npc_proxy_dialog_context",
            "missionId": context["missionId"],
            "nominalStoryMissionId": owner_mission,
            "contextMissionMismatch": cross_mission_context,
            "npcProxyId": context["proxyId"],
            "levelId": context["levelId"],
            "candidateQuestIds": context["questIds"],
            "configuredDialogIds": context["configuredDialogIds"],
            "activeRowIndex": context["activeRowIndex"],
            "selectionSemantics":
                "exDatas[activeCondIndex - 1].dialogId",
            "contextBoundary": (
                "all exact typed tracking consumers for this same-level NPC "
                "proxy agree on one mission; the tracking quests observe the "
                "shared proxy but do not select or play this dialog"
            ),
            "orderBoundary": (
                "activeCondIndex selects one proxy row; row index, table "
                "order, dialog suffix, and quest topology do not order the "
                "configured dialogs"
            ),
            "recoveryMethod": "complete_mission_runtime_proxy_census",
            "sourceFiles": context["sourceFiles"],
            "sourceSha256": context["sourceSha256"],
        })

    already_closed = {row["sceneKey"] for row in closed}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _flow_story_connections(flow):
        scene_key = safe_key(row.get("key"))
        mission_id = safe_key(row.get("npcProxyMissionId"))
        context_mission_bundle = safe_key(
            row.get("contextMissionBundle")
        )
        if (
            scene_key in already_closed
            or scene_key not in isolated_scene_keys
            or safe_key(row.get("relation"))
            != "npc_proxy_ex_mission_context"
            or safe_key(row.get("confidence")) != "direct_mission_scope"
            or safe_key(row.get("source"))
            != "NpcProxyExDataTable.data[*].missionId + dialogId"
            or not safe_key(row.get("npcProxyId"))
            or not mission_id
            or safe_key(row.get("storyOwnerMission")) != owner_mission
            or (
                mission_id != owner_mission
                and context_mission_bundle != mission_id
            )
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
            not mission_ids
            or mapping_ids != {NPC_PROXY_DIALOG_SELECTION_MAPPING_ID}
            or hashes
            != {NPC_PROXY_DIALOG_SELECTION_GAMEASSEMBLY_SHA256}
        ):
            continue
        context_missions = sorted(mission_ids, key=natural_key)
        context_mission = (
            owner_mission
            if owner_mission in mission_ids
            else context_missions[0]
        )
        cross_mission_context = any(
            mission_id != owner_mission
            for mission_id in mission_ids
        )
        multi_mission_context = len(mission_ids) > 1
        npc_proxy_ex_sources = [
            value
            for value in (
                "export_full/structured/StreamingAssets/Data/Json/"
                "GameplayConfig/NpcProxyExDataTable.json",
                "export_full/structured/Persistent/Data/Json/"
                "GameplayConfig/NpcProxyExDataTable.json",
            )
            if (ROOT / value).is_file()
        ]
        closed.append({
            "sceneKey": scene_key,
            "recoveryStatus":
                (
                    "closed_exact_multi_mission_runtime_config_"
                    "no_relative_order"
                    if multi_mission_context else
                    "closed_exact_cross_mission_runtime_config_"
                    "no_relative_order"
                    if cross_mission_context
                    else "closed_exact_runtime_config_no_relative_order"
                ),
            "relation": "npc_proxy_ex_mission_context",
            "missionId": context_mission,
            "contextMissionIds": context_missions,
            "nominalStoryMissionId": owner_mission,
            "contextMissionMismatch": cross_mission_context,
            "contextMissionBundles": sorted({
                safe_key(row.get("contextMissionBundle"))
                for row in rows
                if safe_key(row.get("contextMissionBundle"))
            }, key=natural_key),
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
            "contextBoundary": (
                "the exact proxy row makes this nominal Story file selectable "
                "under the authored mission context set "
                f"{', '.join(context_missions)}; it does not choose between "
                "those contexts, move the file into another chronology, or "
                "establish a relative Story edge"
            ),
            "sourceFiles": npc_proxy_ex_sources,
            "sourceSha256": {
                value: _sha256_file(ROOT / value)
                for value in npc_proxy_ex_sources
            },
            "originalBinaryFiles": [
                _configured_game_assembly_path().as_posix(),
            ],
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
    leveldata_component_source = (
        "exact counted LevelData interactive list -> 25-member "
        "LevelInteractiveData bounded by the next record or validated "
        "member-21 suffix (nonempty BriefData dictionary or complete "
        "empty-script suffix), including an exact null or decoded "
        "mission/quest-state progress lock -> "
        "componentProperties[94].type_id"
    )
    leveldata_horn_source = (
        "exact counted LevelData interactive list -> 25-member "
        "LevelInteractiveData bounded by the next record or validated "
        "member-21 suffix (nonempty BriefData dictionary or complete "
        "empty-script suffix), including an exact null or decoded "
        "mission/quest-state progress lock -> "
        "int_horn.properties.dialog_id; the byte-identical authored "
        "Horn template and current native Horn flow validate the "
        "dialog consumer"
    )
    leveldata_order_boundary = (
        "interactive-list order, record index, entity logic id, object "
        "position, and Story suffix do not establish relative Story chronology"
    )

    def progress_tree_leaves(
        node: object,
        depth: int = 0,
    ) -> list[dict[str, Any]] | None:
        if not isinstance(node, dict) or depth > 8:
            return None
        condition_type = safe_key(node.get("conditionType"))
        if condition_type == "CombinedConditionRuntime":
            children = node.get("conditions")
            if (
                node.get("unionTag") != 0
                or node.get("serializedMemberCount") != 3
                or node.get("conditionOperator") not in (0, 1)
                or not isinstance(node.get("serializedRuntimeFlag"), bool)
                or not isinstance(children, list)
                or not 1 <= len(children) <= 64
            ):
                return None
            leaves: list[dict[str, Any]] = []
            for child in children:
                child_leaves = progress_tree_leaves(child, depth + 1)
                if child_leaves is None:
                    return None
                leaves.extend(child_leaves)
            return leaves
        if (
            condition_type not in {
                "SimpleConditionCheckMissionState",
                "SimpleConditionCheckQuestState",
            }
            or node.get("unionTag") not in (0x0C, 0x10)
            or node.get("serializedMemberCount") != 3
            or safe_key(node.get("ownerKind")) not in {"mission", "quest"}
            or not safe_key(node.get("ownerId"))
            or node.get("compareOperator") not in (0, 1)
            or not isinstance(node.get("compareTarget"), int)
            or isinstance(node.get("compareTarget"), bool)
            or not 0 <= int(node.get("compareTarget")) <= 5
        ):
            return None
        return [node]

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
        consumer_kind = safe_key(
            row.get("narrativeConsumerKind")
        ) or "narrative_component"
        if consumer_kind == "horn_dialog_property":
            exact_consumer_valid = (
                safe_key(row.get("source")) == leveldata_horn_source
                and safe_key(row.get("nativeMappingId"))
                == LEVELDATA_INTERACTIVE_HORN_MAPPING_ID
                and entity_details == ["int_horn"]
                and template_ids == ["int_horn"]
                and safe_key(row.get("interactiveHornNativeMappingId"))
                == LEVELDATA_INTERACTIVE_HORN_NATIVE_MAPPING_ID
                and safe_key(row.get("interactiveHornTemplateSha256"))
                == LEVELDATA_INTERACTIVE_HORN_TEMPLATE_SHA256
                and isinstance(row.get("dialogIdEntryOffset"), int)
                and not isinstance(row.get("dialogIdEntryOffset"), bool)
                and isinstance(record_offset, int)
                and row.get("dialogIdEntryOffset") > record_offset
                and isinstance(record_end, int)
                and row.get("dialogIdEntryOffset") < record_end
                and row.get("narrativeComponentKey") is None
            )
        else:
            exact_consumer_valid = (
                consumer_kind == "narrative_component"
                and safe_key(row.get("source"))
                == leveldata_component_source
                and safe_key(row.get("nativeMappingId"))
                == LEVELDATA_INTERACTIVE_NARRATIVE_MAPPING_ID
                and template_ids[0].startswith("int_narrative")
                if len(template_ids) == 1
                else False
            )
        boundary_source = safe_key(
            row.get("interactiveRecordBoundarySource")
        )
        final_record = (
            isinstance(record_index, int)
            and not isinstance(record_index, bool)
            and isinstance(list_count, int)
            and not isinstance(list_count, bool)
            and record_index == list_count - 1
        )
        nonempty_final_boundary_valid = (
            final_record
            and boundary_source == "leveldata_member21_start"
            and isinstance(record_end, int)
            and not isinstance(record_end, bool)
            and row.get("levelDataMember21Offset") == record_end
            and row.get("levelScriptBriefDictionaryCountOffset")
            == record_end + 4
            and isinstance(row.get("levelIdNum"), int)
            and not isinstance(row.get("levelIdNum"), bool)
            and int(row.get("levelIdNum")) >= 0
            and isinstance(
                row.get("levelScriptBriefDictionaryCount"),
                int,
            )
            and not isinstance(
                row.get("levelScriptBriefDictionaryCount"),
                bool,
            )
            and int(row.get("levelScriptBriefDictionaryCount")) > 0
            and safe_key(row.get("levelDataFinalBoundaryValidation"))
            == "nonempty_levelscript_brief_dictionary"
        )
        empty_final_boundary_valid = (
            final_record
            and boundary_source == "leveldata_member21_start"
            and isinstance(record_end, int)
            and row.get("levelDataMember21Offset") == record_end
            and row.get("levelScriptBriefDictionaryCountOffset")
            == record_end + 4
            and row.get("levelScriptBriefDictionaryCount") == 0
            and row.get("levelScriptDataPathDictionaryCountOffset")
            == record_end + 8
            and row.get("levelScriptDataPathDictionaryCount") == 0
            and row.get("levelDataSafeZoneOffset") == record_end + 60
            and safe_key(row.get("levelDataSceneId"))
            == next(iter(level_ids), "")
            and isinstance(row.get("levelDataSpecificDataOffset"), int)
            and row.get("levelDataSpecificDataOffset")
            > row.get("levelDataSafeZoneOffset")
            and isinstance(row.get("levelDataEmptySuffixEndOffset"), int)
            and row.get("levelDataEmptySuffixEndOffset")
            > row.get("levelDataSpecificDataOffset")
            and safe_key(row.get("levelDataFinalBoundaryValidation"))
            == "complete_empty_script_suffix_to_eof"
        )
        nonfinal_boundary_valid = (
            isinstance(record_index, int)
            and not isinstance(record_index, bool)
            and isinstance(list_count, int)
            and not isinstance(list_count, bool)
            and 0 <= record_index < list_count - 1
            and boundary_source == "next_record"
        )
        progress_status = safe_key(
            row.get("progressLockConditionStatus")
        )
        progress_conditions = row.get("progressLockConditions")
        tree_leaves = progress_tree_leaves(
            row.get("progressLockConditionTree")
        )
        decoded_progress_valid = (
            progress_status == "decoded"
            and safe_key(row.get("progressLockConditionType")) in {
                "CombinedConditionRuntime",
                "SimpleConditionCheckMissionState",
                "SimpleConditionCheckQuestState",
            }
            and isinstance(progress_conditions, list)
            and bool(progress_conditions)
            and all(
                isinstance(condition, dict)
                and condition.get("serializedMemberCount") == 3
                and condition.get("unionTag") in (0x0C, 0x10)
                and safe_key(condition.get("conditionType")) in {
                    "SimpleConditionCheckMissionState",
                    "SimpleConditionCheckQuestState",
                }
                and safe_key(condition.get("ownerKind"))
                in {"mission", "quest"}
                and bool(safe_key(condition.get("ownerId")))
                and condition.get("compareOperator") in (0, 1)
                and isinstance(condition.get("compareTarget"), int)
                and not isinstance(condition.get("compareTarget"), bool)
                and 0 <= int(condition.get("compareTarget")) <= 5
                for condition in progress_conditions
            )
            and tree_leaves is not None
            and len(tree_leaves) == len(progress_conditions)
            and all(
                (
                    safe_key(tree.get("conditionType")),
                    safe_key(tree.get("ownerKind")),
                    safe_key(tree.get("ownerId")),
                    tree.get("compareOperator"),
                    tree.get("compareTarget"),
                ) == (
                    safe_key(flat.get("conditionType")),
                    safe_key(flat.get("ownerKind")),
                    safe_key(flat.get("ownerId")),
                    flat.get("compareOperator"),
                    flat.get("compareTarget"),
                )
                for tree, flat in zip(tree_leaves, progress_conditions)
            )
        )
        progress_type = safe_key(row.get("progressLockConditionType"))
        if progress_type == "CombinedConditionRuntime":
            decoded_progress_valid = (
                decoded_progress_valid
                and row.get("progressLockConditionUnionTag") == 0
                and row.get(
                    "progressLockConditionSerializedMemberCount"
                ) == 3
                and row.get("progressLockConditionOperator") in (0, 1)
                and isinstance(
                    row.get("progressLockSerializedRuntimeFlag"),
                    bool,
                )
            )
        elif progress_type in {
            "SimpleConditionCheckMissionState",
            "SimpleConditionCheckQuestState",
        }:
            decoded_progress_valid = (
                decoded_progress_valid
                and row.get("progressLockConditionUnionTag") in (0x0C, 0x10)
                and row.get(
                    "progressLockConditionSerializedMemberCount"
                ) == 3
                and len(progress_conditions) == 1
                and progress_conditions[0].get("unionTag")
                == row.get("progressLockConditionUnionTag")
                and progress_conditions[0].get("conditionType")
                == row.get("progressLockConditionType")
            )
        progress_lock_valid = (
            (
                progress_status == "null"
                and not progress_conditions
            )
            or decoded_progress_valid
        )
        if (
            scene_key in already_closed
            or scene_key not in isolated_scene_keys
            or safe_key(row.get("relation"))
            != "leveldata_interactive_narrative_config"
            or safe_key(row.get("confidence"))
            != "native_exact_serialized_config"
            or not exact_consumer_valid
            or safe_key(row.get("storyOwnerMission")) != owner_mission
            or row.get("storyBinding") is not True
            or row.get("ownership") is not False
            or safe_key(row.get("orderBoundary"))
            != leveldata_order_boundary
            or len(level_ids) != 1
            or len(asset_ids) != 1
            or len(entity_details) != 1
            or len(template_ids) != 1
            or not isinstance(record_index, int)
            or isinstance(record_index, bool)
            or record_index < 0
            or not isinstance(list_count, int)
            or isinstance(list_count, bool)
            or not (
                nonfinal_boundary_valid
                or nonempty_final_boundary_valid
                or empty_final_boundary_valid
            )
            or not progress_lock_valid
            or not isinstance(record_offset, int)
            or not isinstance(record_end, int)
            or record_offset < 0
            or record_end <= record_offset
            or not isinstance(entity_logic_id, int)
            or isinstance(entity_logic_id, bool)
            or entity_logic_id <= 0
            or (
                consumer_kind == "narrative_component"
                and row.get("narrativeComponentKey") != 94
            )
        ):
            continue
        leveldata_grouped[scene_key].append(row)

    for scene_key, rows in leveldata_grouped.items():
        progress_locks = []
        for row in rows:
            progress_locks.append({
                "levelDataAsset": next(
                    iter(_string_list(row.get("levelDataAssets"))),
                    "",
                ),
                "interactiveRecordIndex":
                    row.get("interactiveRecordIndex"),
                "status": safe_key(
                    row.get("progressLockConditionStatus")
                ),
                "conditionType": safe_key(
                    row.get("progressLockConditionType")
                ),
                "conditionOperator":
                    row.get("progressLockConditionOperator"),
                "serializedRuntimeFlag":
                    row.get("progressLockSerializedRuntimeFlag"),
                "conditionTree":
                    row.get("progressLockConditionTree"),
                "conditions": [{
                    key: condition.get(key)
                    for key in (
                        "unionTag",
                        "serializedMemberCount",
                        "conditionType",
                        "ownerKind",
                        "ownerId",
                        "compareOperator",
                        "compareTarget",
                    )
                } for condition in row.get("progressLockConditions") or []],
            })
        progress_locks.sort(key=lambda row: (
            natural_key(safe_key(row.get("levelDataAsset"))),
            int(row.get("interactiveRecordIndex") or 0),
        ))
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
            "interactiveRecordBoundarySources": sorted({
                safe_key(row.get("interactiveRecordBoundarySource"))
                for row in rows
                if safe_key(row.get("interactiveRecordBoundarySource"))
            }),
            "levelDataFinalBoundaryValidations": sorted({
                safe_key(row.get("levelDataFinalBoundaryValidation"))
                for row in rows
                if safe_key(row.get("levelDataFinalBoundaryValidation"))
            }),
            "levelDataSceneIds": sorted({
                safe_key(row.get("levelDataSceneId"))
                for row in rows
                if safe_key(row.get("levelDataSceneId"))
            }, key=natural_key),
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
            "narrativeConsumerKinds": sorted({
                safe_key(row.get("narrativeConsumerKind"))
                or "narrative_component"
                for row in rows
            }),
            "progressLocks": progress_locks,
            "sourceFiles": sorted({
                source_file
                for row in rows
                for source_file in _string_list(row.get("sourceFiles"))
            }),
            "nativeConsumers": sorted({
                safe_key(row.get("nativeConsumer"))
                for row in rows
                if safe_key(row.get("nativeConsumer"))
            }),
            "nativeMappingIds": sorted({
                safe_key(row.get("nativeMappingId"))
                for row in rows
                if safe_key(row.get("nativeMappingId"))
            }),
            "activationBoundary": (
                "the LevelData asset and narrative interactive are exact; "
                "an exact progress lock constrains interactive availability "
                "when present, but does not establish object instantiation, "
                "player interaction timing, Story ownership, or chronology"
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
    offline_exhaustion_index: dict[str, dict[str, Any]] | None = None,
    quest_attachment_diagnostic_index:
        dict[str, dict[str, Any]] | None = None,
    cross_owner_story_connections: list[dict[str, Any]] | None = None,
    story_trigger_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    non_mission_content = non_mission_content or {}
    offline_exhaustion_index = offline_exhaustion_index or {}
    quest_attachment_diagnostic_index = (
        quest_attachment_diagnostic_index or {}
    )
    story_trigger_manifest = story_trigger_manifest or {}
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
    strict_quest_ids, strict_quest_scenes = _strict_quest_attachments(
        partial_row,
        flow,
    )
    diagnostic_quest_ids, diagnostic_quest_scenes, diagnostic_source_counts = (
        _diagnostic_quest_attachments(timeline, candidate_scene_keys)
    )
    raw_missing_strict_quest_ids = sorted(
        (quest_ids & diagnostic_quest_ids) - strict_quest_ids,
        key=natural_key,
    )
    closed_quest_attachment_diagnostics = [
        quest_attachment_diagnostic_index[quest_id]
        for quest_id in raw_missing_strict_quest_ids
        if (
            quest_id in quest_attachment_diagnostic_index
            and safe_key(
                quest_attachment_diagnostic_index[quest_id].get("missionId")
            ) == mission
            and quest_attachment_diagnostic_index[quest_id].get(
                "graphEffect"
            ) == "none"
        )
    ]
    closed_quest_attachment_ids = {
        safe_key(row.get("questId"))
        for row in closed_quest_attachment_diagnostics
    }
    missing_strict_quest_ids = [
        quest_id
        for quest_id in raw_missing_strict_quest_ids
        if quest_id not in closed_quest_attachment_ids
    ]
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
    cross_owner_flow = flow
    if cross_owner_story_connections:
        cross_owner_flow = dict(flow)
        cross_owner_flow["missionStoryConnections"] = [
            *(
                flow.get("missionStoryConnections")
                if isinstance(flow.get("missionStoryConnections"), list)
                else []
            ),
            *cross_owner_story_connections,
        ]
    (
        closed_exact_native_isolated,
        _incomplete_native_isolated_keys,
    ) = _closed_exact_native_unordered_scenes(
        cross_owner_flow,
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
    for row in (
        _closed_exact_disconnected_dialog_tree_context_isolated_scenes(
            flow,
            set(isolated_scene_keys),
            safe_key(partial_row.get("mission")),
        )
    ):
        closed_exact_native_isolated_by_key.setdefault(
            row["sceneKey"],
            row,
        )
    for row in _closed_exact_timeline_dialog_embedded_isolated_scenes(
        flow,
        set(isolated_scene_keys),
        safe_key(partial_row.get("mission")),
    ):
        closed_exact_native_isolated_by_key.setdefault(
            row["sceneKey"],
            row,
        )
    for row in _closed_exact_timeline_foreign_dialog_isolated_scenes(
        flow,
        set(isolated_scene_keys),
        safe_key(partial_row.get("mission")),
    ):
        closed_exact_native_isolated_by_key.setdefault(
            row["sceneKey"],
            row,
        )
    for row in _closed_exact_native_context_isolated_scenes(
        cross_owner_flow,
        set(isolated_scene_keys),
        safe_key(partial_row.get("mission")),
    ):
        if (
            row.get("contextMissionMismatch") is True
            or row["sceneKey"] not in closed_exact_native_isolated_by_key
        ):
            closed_exact_native_isolated_by_key[row["sceneKey"]] = row
    (
        exact_black_carrier_closures,
        exact_black_carrier_validation_failures,
    ) = _closed_exact_black_carrier_context_isolated_scenes(
        cross_owner_flow,
        set(isolated_scene_keys)
        - set(closed_exact_native_isolated_by_key),
        safe_key(partial_row.get("mission")),
    )
    for row in exact_black_carrier_closures:
        closed_exact_native_isolated_by_key.setdefault(
            row["sceneKey"],
            row,
        )
    story_trigger_manifest_validation_failures: list[dict[str, Any]] = []
    for row in _closed_exact_lua_controller_playback_isolated_scenes(
        story_trigger_manifest,
        set(isolated_scene_keys),
        safe_key(partial_row.get("mission")),
        story_trigger_manifest_validation_failures,
    ):
        closed_exact_native_isolated_by_key.setdefault(
            row["sceneKey"],
            row,
        )
    for row in _closed_exact_composed_root_playback_isolated_scenes(
        story_trigger_manifest,
        set(isolated_scene_keys),
        safe_key(partial_row.get("mission")),
        story_trigger_manifest_validation_failures,
    ):
        closed_exact_native_isolated_by_key.setdefault(
            row["sceneKey"],
            row,
        )
    for row in _closed_exact_connected_context_isolated_scenes(
        story_trigger_manifest,
        set(isolated_scene_keys),
        safe_key(partial_row.get("mission")),
        story_trigger_manifest_validation_failures,
    ):
        closed_exact_native_isolated_by_key.setdefault(
            row["sceneKey"],
            row,
        )
    for scene_key, row in list(closed_exact_native_isolated_by_key.items()):
        merged, interaction_merged = (
            _merge_exact_interaction_trigger_with_native_playback(
                offline_exhaustion_index.get(scene_key),
                row,
            )
        )
        if interaction_merged:
            closed_exact_native_isolated_by_key[scene_key] = merged
    closed_exact_native_isolated = sorted(
        closed_exact_native_isolated_by_key.values(),
        key=lambda row: natural_key(row["sceneKey"]),
    )
    closed_exact_native_isolated_keys = {
        row["sceneKey"]
        for row in closed_exact_native_isolated
    }
    (
        closed_exact_system_selector_isolated,
        exact_system_selector_validation_failures,
    ) = _closed_exact_system_selector_isolated_scenes(
        cross_owner_flow,
        set(isolated_scene_keys),
        safe_key(partial_row.get("mission")),
    )
    closed_exact_system_selector_isolated_keys = {
        row["sceneKey"] for row in closed_exact_system_selector_isolated
    }
    exact_runtime_config_validation_failures: list[dict[str, Any]] = []
    closed_exact_runtime_config_isolated = (
        _closed_exact_runtime_config_isolated_scenes(
            cross_owner_flow,
            set(isolated_scene_keys),
            safe_key(partial_row.get("mission")),
            offline_exhaustion_index,
            exact_runtime_config_validation_failures,
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
    deferred_offline_exhausted_isolated = (
        _deferred_offline_exhausted_isolated_scenes(
            flow,
            set(isolated_scene_keys),
            safe_key(partial_row.get("mission")),
            offline_exhaustion_index,
            native_playback_index,
            cross_owner_story_connections,
        )
    )
    # Positive playback/runtime/definition evidence has precedence over a
    # negative consumer-surface exhaustion result. Keep the offline index
    # reusable and corpus-wide, but never expose the same scene as both
    # positively closed and negatively deferred in the mission queue.
    positive_closure_keys = (
        closed_exact_native_isolated_keys
        | closed_exact_system_selector_isolated_keys
        | closed_exact_runtime_config_isolated_keys
        | closed_definition_only_isolated_keys
        | closed_non_mission_content_isolated_keys
    )
    deferred_offline_exhausted_isolated = [
        row
        for row in deferred_offline_exhausted_isolated
        if safe_key(row.get("sceneKey")) not in positive_closure_keys
    ]
    deferred_offline_exhausted_isolated_keys = {
        row["sceneKey"]
        for row in deferred_offline_exhausted_isolated
    }
    partial_registered_dialog_tree_carriers = sorted(
        (
            recovery
            for scene_key in isolated_scene_keys
            if isinstance(
                recovery := offline_exhaustion_index.get(scene_key),
                dict,
            )
            and recovery.get("recoveryStatus")
            == "actionable_partial_registered_dialog_tree_partition"
            and safe_key(recovery.get("missionId")) == mission
            and recovery.get("graphEffect") == "none"
        ),
        key=lambda row: natural_key(safe_key(row.get("sceneKey"))),
    )
    deferred_offline_option_route_groups: list[dict[str, Any]] = []
    for group_row in (
        ((partial_row.get("branches") or {}).get(
            "branchingNoExplicitRouteGroups"
        ) or [])
    ):
        if not isinstance(group_row, dict):
            continue
        story_key = safe_key(group_row.get("storyKey"))
        recovery = offline_exhaustion_index.get(story_key)
        if (
            story_key not in deferred_offline_exhausted_isolated_keys
            or not isinstance(recovery, dict)
            or recovery.get("optionRouteStatus")
            != "definitions_present_route_unresolved"
        ):
            continue
        group = int(group_row.get("group") or 0)
        option_ids = tuple(sorted(
            safe_key(option.get("optionId"))
            for option in group_row.get("options") or []
            if isinstance(option, dict) and safe_key(option.get("optionId"))
        ))
        expected_option_ids = tuple(sorted(
            option_id
            for option_id in _string_list(recovery.get("optionIds"))
            if option_id.startswith(f"option_{story_key}_{group}_")
        ))
        if not option_ids or option_ids != expected_option_ids:
            continue
        deferred_offline_option_route_groups.append({
            "storyKey": story_key,
            "group": group,
            "optionIds": list(option_ids),
            "recoveryStatus":
                "deferred_current_build_offline_route_surface_exhausted",
            "evidenceKind": recovery.get("evidenceKind"),
            "consumerBoundary": recovery.get("consumerBoundary"),
            "routeBoundary": (
                "the exact option definitions survive, but the current "
                "registered table-only dialog has no DialogTree, Timeline, "
                "typed runtime consumer, native token, or object-index "
                "carrier from which an option destination could be recovered"
            ),
            "graphEffect": "none",
        })
    actionable_core_isolated_scene_keys = [
        key
        for key in core_isolated_scene_keys
        if key not in closed_exact_native_isolated_keys
        and key not in closed_exact_system_selector_isolated_keys
        and key not in closed_exact_runtime_config_isolated_keys
        and key not in closed_definition_only_isolated_keys
        and key not in closed_non_mission_content_isolated_keys
        and key not in deferred_offline_exhausted_isolated_keys
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
        "closedExactSystemSelectorIsolatedScenes": len(
            closed_exact_system_selector_isolated_keys
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
        "deferredOfflineExhaustedIsolatedScenes": len(
            deferred_offline_exhausted_isolated_keys
        ),
        "partialRegisteredDialogTreeCarrierScenes": len(
            partial_registered_dialog_tree_carriers
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
        "exactBlackCarrierValidationFailures": len(
            exact_black_carrier_validation_failures
        ),
        "exactRuntimeConfigValidationFailures": len(
            exact_runtime_config_validation_failures
        ),
        "exactSystemSelectorValidationFailures": len(
            exact_system_selector_validation_failures
        ),
        "questCount": len(quest_ids),
        "strictQuestAttachedSceneCount": len(strict_quest_scenes),
        "strictQuestIdsWithStoryAttachment": len(quest_ids & strict_quest_ids),
        "questIdsWithoutStrictStoryAttachment": len(missing_strict_quest_ids),
        "closedQuestAttachmentDiagnostics": len(
            closed_quest_attachment_diagnostics
        ),
        "questIdsWithoutAnyStoryEvidence": len(quest_ids_without_story_evidence),
        "diagnosticQuestAttachedSceneCount": len(diagnostic_quest_scenes),
        "diagnosticQuestIdsWithStoryAttachment": len(quest_ids & diagnostic_quest_ids),
        "questForks": int(summary.get("questForkCount") or 0),
        "questMerges": int(summary.get("questMergeCount") or 0),
        "strictDialogOptionGroups": int(summary.get("dialogLineOptionGroupCount") or 0),
        "noExplicitOptionRouteGroups": int(
            summary.get("noExplicitRouteGroupCount") or 0
        ),
        "actionableNoExplicitOptionRouteGroups": max(
            0,
            int(
                summary.get(
                    "branchingNoExplicitRouteGroupCount",
                    summary.get("noExplicitRouteGroupCount"),
                )
                or 0
            ) - len(deferred_offline_option_route_groups),
        ),
        "deferredOfflineExhaustedOptionRouteGroups": len(
            deferred_offline_option_route_groups
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
        "closedExactSystemSelectorIsolatedScenes":
            closed_exact_system_selector_isolated,
        "closedExactRuntimeConfigIsolatedScenes":
            closed_exact_runtime_config_isolated,
        "closedDefinitionOnlyIsolatedScenes":
            closed_definition_only_isolated,
        "closedNonMissionContentIsolatedScenes":
            closed_non_mission_content_isolated,
        "deferredOfflineExhaustedIsolatedScenes":
            deferred_offline_exhausted_isolated,
        "partialRegisteredDialogTreeCarriers":
            partial_registered_dialog_tree_carriers,
        "deferredOfflineExhaustedOptionRouteGroups":
            deferred_offline_option_route_groups,
        "actionableWeakOnlySceneKeys": actionable_weak_only_scene_keys,
        "closedExactNativeWeakOnlyScenes": closed_exact_native_weak_only,
        "nonActionableWeakOnlySceneKeys":
            non_actionable_weak_only_scene_keys,
        "isolatedSceneKinds": dict(sorted(isolated_kinds.items())),
        "questIdsWithoutStrictStoryAttachment": missing_strict_quest_ids,
        "closedQuestAttachmentDiagnostics":
            closed_quest_attachment_diagnostics,
        "questIdsWithoutAnyStoryEvidence": quest_ids_without_story_evidence,
        "untypedMultiSceneLevelscriptContexts": context_gaps,
        "closedNonPlaybackLevelscriptContexts": closed_context_gaps,
        "exactBlackCarrierValidationFailures":
            exact_black_carrier_validation_failures,
        "exactRuntimeConfigValidationFailures":
            exact_runtime_config_validation_failures,
        "exactSystemSelectorValidationFailures":
            exact_system_selector_validation_failures,
        "storyTriggerManifestValidationFailures":
            story_trigger_manifest_validation_failures,
        "timelineUnresolvedKinds": dict(sorted(unresolved_kinds.items())),
        "diagnosticQuestAttachmentSources": dict(sorted(diagnostic_source_counts.items())),
        "unresolvedSourceNodes": partial_row.get("unresolvedSourceNodes") or [],
    }

def _exact_leveldata_story_context(
    connection: dict[str, Any],
    owner_mission: str,
    context_mission: str,
) -> bool:
    """Validate an exact LevelData-hosted LevelScript playback route.

    The same source shape is valid whether the LevelData shell matches the
    Story's nominal mission or belongs to a foreign mission.  Ownership
    equality affects the interpretation of the resulting boundary, not the
    binary validation gates.
    """
    story_key = safe_key(connection.get("key"))
    occurrences = connection.get("levelScriptOccurrences") or []
    if (
        not story_key
        or safe_key(connection.get("relation"))
        != "leveldata_levelscript_mission_context"
        or safe_key(connection.get("direction")) != "context"
        or safe_key(connection.get("phase")) != "context"
        or safe_key(connection.get("confidence")) != "native_exact_host"
        or safe_key(connection.get("storyOwnerMission")) != owner_mission
        or safe_key(connection.get("levelDataHostMissionId"))
        != context_mission
        or safe_key(connection.get("questTriggerStatus")) != "unresolved"
        or connection.get("hasUnscopedOrOtherMissionOccurrences") is not False
        or not isinstance(occurrences, list)
        or not occurrences
        or connection.get("occurrenceCount") != len(occurrences)
        or connection.get("allOccurrenceCount") != len(occurrences)
    ):
        return False

    occurrence_actions: set[str] = set()
    occurrence_opcodes: set[str] = set()
    occurrence_level_ids: set[str] = set()
    occurrence_script_ids: set[str] = set()
    occurrence_source_files: set[str] = set()
    occurrence_level_data_files: set[str] = set()
    has_playback = False
    for occurrence in occurrences:
        if not isinstance(occurrence, dict):
            return False
        action_name = safe_key(occurrence.get("actionName"))
        action_code = safe_key(occurrence.get("actionCode"))
        action_kind = safe_key(occurrence.get("actionKind"))
        level_id = safe_key(occurrence.get("levelId"))
        script_id = safe_key(occurrence.get("scriptId"))
        source_file = safe_key(occurrence.get("sourceFile"))
        record_class = safe_key(occurrence.get("recordClass"))
        authored_story_key = (
            safe_key(occurrence.get("authoredStoryKey")) or story_key
        )
        alias_valid = (
            authored_story_key == story_key
            or (
                story_key.startswith("misc_dlg_")
                and authored_story_key == story_key.removeprefix("misc_")
            )
        )
        action_local_id = occurrence.get("localId")
        owners = occurrence.get("nativeEventOwners") or []
        level_data_hosts = occurrence.get("levelDataHosts") or []
        if (
            not action_name
            or not action_code
            or not action_kind
            or not level_id
            or not script_id
            or not source_file
            or not isinstance(action_local_id, int)
            or not safe_key(occurrence.get("actionMapRole")).startswith(
                "actionList#"
            )
            or not (
                record_class.startswith("play_")
                or record_class.startswith("preload_")
            )
            or not safe_key(occurrence.get("nativeMappingId")).startswith(
                "gameassembly-"
            )
            or not alias_valid
            or set(_string_list(occurrence.get("allStoryKeysInRecord")))
            != {authored_story_key}
            or safe_key(occurrence.get("nativeEventOwnerStatus"))
            != "exact_serialized_control_path"
            or not owners
            or not any(
                isinstance(owner, dict)
                and safe_key(owner.get("status"))
                == "exact_serialized_control_path"
                and isinstance(owner.get("headerLocalId"), int)
                and action_local_id in {
                    step.get("localId")
                    for step in owner.get("path") or []
                    if isinstance(step, dict)
                }
                for owner in owners
            )
            or not level_data_hosts
            or any(
                not isinstance(host, dict)
                or safe_key(host.get("missionId")) != context_mission
                or safe_key(host.get("levelId")) != level_id
                or safe_key(host.get("scriptId")) != script_id
                or not safe_key(host.get("levelDataFile"))
                or safe_key(host.get("encoding"))
                != "leveldata_member22_levelscriptbriefdata"
                or safe_key(host.get("nativeSchema"))
                != (
                    "LevelData/43.member22:"
                    "Dictionary<u64,LevelScriptBriefData/8>"
                )
                or not isinstance(host.get("briefData"), list)
                or not host["briefData"]
                or any(
                    not isinstance(brief, dict)
                    or safe_key(brief.get("scriptId")) != script_id
                    for brief in host["briefData"]
                )
                for host in level_data_hosts
            )
            or set(_string_list(occurrence.get("scopeEvidenceKinds")))
            != {
                "mission_leveldata_member22_contains_validated_"
                "levelscript_brief"
            }
        ):
            return False
        has_playback = has_playback or record_class.startswith("play_")
        occurrence_actions.add(action_name)
        occurrence_opcodes.add(f"{action_code}/{action_kind}")
        occurrence_level_ids.add(level_id)
        occurrence_script_ids.add(script_id)
        occurrence_source_files.add(source_file)
        occurrence_level_data_files.update(
            safe_key(host.get("levelDataFile"))
            for host in level_data_hosts
        )

    return (
        has_playback
        and set(_string_list(connection.get("nativeActions")))
        == occurrence_actions
        and set(_string_list(connection.get("opcodes")))
        == occurrence_opcodes
        and set(_string_list(connection.get("levelIds")))
        == occurrence_level_ids
        and set(_string_list(connection.get("scriptIds")))
        == occurrence_script_ids
        and set(_string_list(connection.get("sourceFiles")))
        == occurrence_source_files
        and set(_string_list(connection.get("levelDataFiles")))
        == occurrence_level_data_files
    )

def _exact_cross_owner_mission_condition_story_context(
    connection: dict[str, Any],
    owner_mission: str,
    context_mission: str,
) -> bool:
    """Validate a foreign playback route scoped by a typed mission condition."""
    story_key = safe_key(connection.get("key"))
    occurrences = connection.get("levelScriptOccurrences") or []
    if (
        not story_key
        or safe_key(connection.get("relation"))
        != "levelscript_mission_context"
        or safe_key(connection.get("direction")) != "context"
        or safe_key(connection.get("phase")) != "context"
        or safe_key(connection.get("confidence")) != "scoped_script"
        or safe_key(connection.get("storyOwnerMission")) != owner_mission
        or safe_key(connection.get("levelScriptMissionId"))
        != context_mission
        or owner_mission == context_mission
        or connection.get("hasUnscopedOrOtherMissionOccurrences") is not False
        or set(_string_list(connection.get("scopeEvidenceKinds")))
        != {"mission_condition_checks_script"}
        or not isinstance(occurrences, list)
        or not occurrences
        or connection.get("occurrenceCount") != len(occurrences)
        or connection.get("allOccurrenceCount") != len(occurrences)
    ):
        return False

    has_playback = False
    for occurrence in occurrences:
        if not isinstance(occurrence, dict):
            return False
        action_local_id = occurrence.get("localId")
        record_class = safe_key(occurrence.get("recordClass"))
        owners = occurrence.get("nativeEventOwners") or []
        mission_conditions = occurrence.get("missionConditions") or []
        if (
            not safe_key(occurrence.get("levelId"))
            or not safe_key(occurrence.get("scriptId"))
            or not safe_key(occurrence.get("sourceFile"))
            or not isinstance(action_local_id, int)
            or not safe_key(occurrence.get("actionMapRole")).startswith(
                "actionList#"
            )
            or not (
                record_class.startswith("play_")
                or record_class.startswith("preload_")
            )
            or not safe_key(occurrence.get("actionName"))
            or not safe_key(occurrence.get("nativeMappingId")).startswith(
                "gameassembly-"
            )
            or set(_string_list(occurrence.get("allStoryKeysInRecord")))
            != {story_key}
            or safe_key(occurrence.get("nativeEventOwnerStatus"))
            != "exact_serialized_control_path"
            or not owners
            or not any(
                isinstance(owner, dict)
                and safe_key(owner.get("status"))
                == "exact_serialized_control_path"
                and isinstance(owner.get("headerLocalId"), int)
                and action_local_id in {
                    step.get("localId")
                    for step in owner.get("path") or []
                    if isinstance(step, dict)
                }
                for owner in owners
            )
            or set(_string_list(occurrence.get("scopeEvidenceKinds")))
            != {"mission_condition_checks_script"}
            or not mission_conditions
            or any(
                not isinstance(condition, dict)
                or safe_key(condition.get("missionId")) != context_mission
                or not safe_key(condition.get("questId")).startswith(
                    f"{context_mission}_q#"
                )
                or not safe_key(condition.get("conditionType")).startswith(
                    "CheckLevelScript"
                )
                or not safe_key(condition.get("sourceFile"))
                for condition in mission_conditions
            )
        ):
            return False
        has_playback = has_playback or record_class.startswith("play_")
    return has_playback

def _exact_cross_owner_npc_proxy_segment_story_context(
    connection: dict[str, Any],
    owner_mission: str,
    context_mission: str,
) -> bool:
    """Validate a foreign Story playback path in one exact NpcProxy shell."""
    story_key = safe_key(connection.get("key"))
    proxy_ids = set(_string_list(connection.get("npcProxyIds")))
    segment_ids = set(_string_list(connection.get("segmentIdsGlobal")))
    candidate_quests = set(_string_list(connection.get("candidateQuestIds")))
    native_owners = connection.get("nativeEventOwners") or []
    tracking_rows = connection.get("npcProxyTrackingRows") or []
    registry_rows = connection.get("npcProxyRegistryRows") or []
    proxy_ex_rows = connection.get("npcProxyExRows") or []
    if (
        not story_key
        or safe_key(connection.get("relation"))
        != "npc_proxy_segment_levelscript_mission_context"
        or safe_key(connection.get("direction")) != "context"
        or safe_key(connection.get("phase")) != "runtime_playback"
        or safe_key(connection.get("confidence"))
        != "native_exact_npc_proxy_segment_shell"
        or safe_key(connection.get("evidenceTier")) != "derived_exact_shell"
        or safe_key(connection.get("storyOwnerMission")) != owner_mission
        or owner_mission == context_mission
        or safe_key(connection.get("questTriggerStatus"))
        != "same_authored_npc_proxy_segment_not_quest_playback"
        or safe_key(connection.get("executionSide")) != "client"
        or connection.get("serverExchange") is not False
        or not proxy_ids
        or not segment_ids
        or not candidate_quests
        or any(
            not quest_id.startswith(f"{context_mission}_q#")
            for quest_id in candidate_quests
        )
        or set(_string_list(connection.get("scriptIds"))) != segment_ids
        or not native_owners
        or not tracking_rows
        or not registry_rows
        or not proxy_ex_rows
        or not _string_list(connection.get("sourceFiles"))
    ):
        return False
    if any(
        not isinstance(row, dict)
        or safe_key(row.get("missionId")) != context_mission
        or safe_key(row.get("questId")) not in candidate_quests
        or not safe_key(row.get("sourceFile"))
        for row in tracking_rows
    ):
        return False
    if any(
        not isinstance(row, dict)
        or safe_key(row.get("proxyId")) not in proxy_ids
        or safe_key(row.get("dictionaryKey")) not in segment_ids
        or safe_key(row.get("segmentIdGlobal")) not in segment_ids
        or not safe_key(row.get("sourceFile"))
        for row in registry_rows
    ):
        return False
    if any(
        not isinstance(row, dict)
        or safe_key(row.get("proxyId")) not in proxy_ids
        or safe_key(row.get("missionId")) != context_mission
        or not isinstance(row.get("rowIndex"), int)
        or isinstance(row.get("rowIndex"), bool)
        or not safe_key(row.get("sourceFile"))
        for row in proxy_ex_rows
    ):
        return False
    for owner in native_owners:
        if (
            not isinstance(owner, dict)
            or safe_key(owner.get("status"))
            != "exact_serialized_control_path"
            or safe_key(owner.get("headerName"))
            != "ScriptEvent_OnLeaderEnterTriggerVolume"
        ):
            return False
        playback_found = False
        for step in owner.get("path") or []:
            if not isinstance(step, dict):
                continue
            record_class = safe_key(step.get("recordClass"))
            texts = _string_list(step.get("texts"))
            step_story_keys = (
                {text.rsplit("_", 1)[0] for text in texts}
                if record_class == "play_black"
                else set(texts)
            )
            if record_class.startswith("play_") and story_key in step_story_keys:
                playback_found = True
                break
        if not playback_found:
            return False
    return True

def _exact_cross_owner_levelscript_quest_playback(
    connection: dict[str, Any],
    owner_mission: str,
    context_mission: str,
    context_quest: str,
) -> tuple[bool, dict[str, Any] | None]:
    """Validate one foreign quest's exact binary-typed LevelScript playback."""
    relation = safe_key(connection.get("relation"))
    expected_state = {
        "levelscript_quest_processing_action": (2, "Processing", "start"),
        "levelscript_quest_completed_action": (3, "Completed", "succeed"),
    }.get(relation)
    story_key = safe_key(connection.get("key"))
    source_file = safe_key(connection.get("sourceFile"))
    source_path = ROOT / source_file if source_file else None
    actual = {
        "relation": relation,
        "direction": safe_key(connection.get("direction")),
        "phase": safe_key(connection.get("phase")),
        "confidence": safe_key(connection.get("confidence")),
        "event": safe_key(connection.get("event")),
        "questState": connection.get("questState"),
        "questStateName": safe_key(connection.get("questStateName")),
        "levelId": safe_key(connection.get("levelId")),
        "scriptId": safe_key(connection.get("scriptId")),
        "sourceFile": source_file,
        "headerLocalId": connection.get("headerLocalId"),
        "actionLocalId": connection.get("actionLocalId"),
        "actionPathLocalIds": connection.get("actionPathLocalIds"),
        "actionName": safe_key(connection.get("actionName")),
        "nativeMappingId": safe_key(connection.get("nativeMappingId")),
    }
    valid = bool(
        story_key
        and owner_mission
        and owner_mission != context_mission
        and context_quest.startswith(f"{context_mission}_q#")
        and expected_state is not None
        and actual["direction"] == "quest_to_story"
        and actual["phase"] == expected_state[2]
        and actual["confidence"] == "native_typed_direct"
        and actual["event"] == "LevelEvent_OnQuestStateChanged"
        and actual["questState"] == expected_state[0]
        and actual["questStateName"] == expected_state[1]
        and actual["levelId"]
        and actual["scriptId"]
        and source_file
        and source_file.endswith(
            f"/LevelScriptData/{actual['levelId']}/{actual['scriptId']}.json"
        )
        and source_path is not None
        and source_path.is_file()
        and isinstance(actual["headerLocalId"], int)
        and not isinstance(actual["headerLocalId"], bool)
        and isinstance(actual["actionLocalId"], int)
        and not isinstance(actual["actionLocalId"], bool)
        and isinstance(actual["actionPathLocalIds"], list)
        and actual["actionPathLocalIds"]
        and actual["actionLocalId"] in actual["actionPathLocalIds"]
        and actual["actionName"]
        and actual["nativeMappingId"].startswith("gameassembly-")
    )
    if valid:
        return True, None
    return False, {
        "validator": "crossOwnerLevelScriptQuestPlayback",
        "gate": "exactTypedQuestStatePlaybackPath",
        "missionId": owner_mission,
        "contextMissionBundle": context_mission,
        "contextQuestId": context_quest,
        "storyKey": story_key,
        "sourcePaths": [source_file] if source_file else [],
        "sourceSha256": (
            {source_file: _sha256_file(source_path)}
            if source_path is not None and source_path.is_file()
            else {}
        ),
        "expected": {
            "relationStatePhase": expected_state,
            "direction": "quest_to_story",
            "confidence": "native_typed_direct",
            "event": "LevelEvent_OnQuestStateChanged",
            "sourcePathMatchesLevelAndScript": True,
            "typedActionPathEndsAtActionLocalId": True,
            "nativeMappingPrefix": "gameassembly-",
        },
        "actual": actual,
    }

def _exact_cross_owner_dialog_tree_narrative_context(
    connection: dict[str, Any],
    owner_mission: str,
    context_mission: str,
) -> tuple[bool, dict[str, Any] | None]:
    """Validate a typed nested narrative action plus its exact foreign shell."""
    occurrences = [
        row
        for row in connection.get("dialogTreeNarrativeActions") or []
        if isinstance(row, dict)
    ]
    parent_contexts = [
        row
        for row in connection.get("parentScopeContexts") or []
        if isinstance(row, dict)
    ]
    parent_key = safe_key(connection.get("parentStoryKey"))
    story_key = safe_key(connection.get("key"))
    advertised_parent_relations = set(
        _string_list(connection.get("parentScopeRelations"))
    )
    if (
        safe_key(connection.get("confidence"))
        != "native_derived_exact_parent_shell"
        or "leveldata_levelscript_mission_context"
        not in advertised_parent_relations
    ):
        return False, None
    parent_relations = {
            safe_key(row.get("relation"))
            for row in parent_contexts
            if safe_key(row.get("relation"))
    }
    occurrence_rows_valid = all(
        safe_key(row.get("dialogKey")) == parent_key
        and safe_key(row.get("textId")).startswith(f"{story_key}_")
        and safe_key(row.get("actionType")) in {
            "Beyond.Gameplay.DialogComplexNarrativeMaskActionData",
            "Beyond.Gameplay.DialogNarrativeMaskActionData",
        }
        and safe_key(row.get("nativeMappingId"))
        == DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID
        and safe_key(row.get("sourceFile"))
        and safe_key(row.get("sourcePathId"))
        for row in occurrences
    )
    parent_contexts_valid = all(
        _exact_leveldata_story_context(
            row,
            safe_key(row.get("storyOwnerMission")),
            context_mission,
        )
        for row in parent_contexts
    )
    valid = bool(
        story_key
        and parent_key
        and owner_mission != context_mission
        and safe_key(connection.get("storyOwnerMission")) == owner_mission
        and safe_key(connection.get("relation"))
        == "dialog_tree_narrative_action"
        and safe_key(connection.get("direction")) == "context"
        and safe_key(connection.get("confidence"))
        == "native_derived_exact_parent_shell"
        and safe_key(connection.get("evidenceTier")) == "derived_exact_shell"
        and safe_key(connection.get("contextMissionId")) == context_mission
        and safe_key(connection.get("nativeMappingId"))
        == DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID
        and connection.get("graphEffect") == "none"
        and occurrences
        and connection.get("occurrenceCount") == len(occurrences)
        and parent_contexts
        and advertised_parent_relations == parent_relations
        and occurrence_rows_valid
        and parent_contexts_valid
    )
    if valid:
        return True, None
    source_paths = sorted({
        source_file
        for source_file in (
            *_string_list(connection.get("sourceFiles")),
            *(
                safe_key(row.get("sourceFile"))
                for row in occurrences
            ),
            *(
                source_file
                for row in parent_contexts
                for source_file in (
                    *_string_list(row.get("sourceFiles")),
                    *_string_list(row.get("levelDataFiles")),
                )
            ),
        )
        if source_file
    })
    return False, {
        "validator": "crossOwnerDialogTreeNarrativeContext",
        "gate": "typedNarrativeActionWithExactParentPlaybackShell",
        "missionId": owner_mission,
        "contextMissionId": context_mission,
        "storyKey": story_key,
        "parentStoryKey": parent_key,
        "sourcePaths": source_paths,
        "sourceSha256": {
            source_file: _sha256_file(ROOT / source_file)
            for source_file in source_paths
            if (ROOT / source_file).is_file()
        },
        "expected": {
            "relation": "dialog_tree_narrative_action",
            "direction": "context",
            "confidence": "native_derived_exact_parent_shell",
            "evidenceTier": "derived_exact_shell",
            "nativeMappingId": DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID,
            "graphEffect": "none",
            "completeTypedOccurrences": True,
            "completeExactParentLevelDataContexts": True,
        },
        "actual": {
            "relation": safe_key(connection.get("relation")),
            "direction": safe_key(connection.get("direction")),
            "confidence": safe_key(connection.get("confidence")),
            "evidenceTier": safe_key(connection.get("evidenceTier")),
            "nativeMappingId": safe_key(connection.get("nativeMappingId")),
            "graphEffect": connection.get("graphEffect"),
            "occurrenceCount": connection.get("occurrenceCount"),
            "retainedOccurrenceCount": len(occurrences),
            "occurrenceRowsValid": occurrence_rows_valid,
            "parentContextCount": len(parent_contexts),
            "parentContextsValid": parent_contexts_valid,
            "parentScopeRelations": _string_list(
                connection.get("parentScopeRelations")
            ),
            "retainedParentRelations": sorted(parent_relations),
        },
    }

def build_gap_report(
    partial_report: dict[str, Any],
    mission_payloads: dict[str, dict[str, Any]],
    mission_bundle_presence: set[str],
    native_playback_index: dict[str, list[dict[str, Any]]] | None = None,
    action_story_occurrences: dict[str, list[dict[str, Any]]] | None = None,
    table_root: Path | None = None,
    offline_exhaustion_index: dict[str, dict[str, Any]] | None = None,
    offline_exhaustion_status: dict[str, Any] | None = None,
    quest_attachment_diagnostic_index:
        dict[str, dict[str, Any]] | None = None,
    quest_attachment_diagnostic_status: dict[str, Any] | None = None,
    story_trigger_manifest: dict[str, Any] | None = None,
    story_trigger_manifest_status: dict[str, Any] | None = None,
    project_authored_content: dict[str, dict[str, Any]] | None = None,
    project_authored_status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    non_mission_content = (
        combined_non_mission_content_keys(table_root)
        if table_root is not None
        else {}
    )
    non_mission_content.update(project_authored_content or {})
    cross_owner_connections: dict[str, list[dict[str, Any]]] = defaultdict(
        list
    )
    cross_owner_levelscript_validation_failures: list[dict[str, Any]] = []
    cross_owner_dialog_tree_validation_failures: list[dict[str, Any]] = []
    story_owners: dict[str, set[str]] = defaultdict(set)
    for partial_row in partial_report.get("missions") or []:
        if not isinstance(partial_row, dict):
            continue
        owner_mission = safe_key(partial_row.get("mission"))
        if not owner_mission:
            continue
        for node in partial_row.get("nodes") or []:
            if not isinstance(node, dict):
                continue
            story_key = safe_key(node.get("key"))
            if story_key:
                story_owners[story_key].add(owner_mission)
    for context_mission, payload in mission_payloads.items():
        flow = _flow(payload)
        for connection in _flow_story_connections(flow):
            owner_mission = safe_key(connection.get("storyOwnerMission"))
            proxy_mission = safe_key(connection.get("npcProxyMissionId"))
            relation = safe_key(connection.get("relation"))
            if (
                not owner_mission
                or owner_mission == context_mission
                or owner_mission not in mission_payloads
            ):
                continue
            if relation == "npc_proxy_ex_mission_context":
                if proxy_mission != context_mission:
                    continue
            elif relation == "npc_proxy_segment_levelscript_mission_context":
                if not _exact_cross_owner_npc_proxy_segment_story_context(
                    connection,
                    owner_mission,
                    context_mission,
                ):
                    continue
            elif relation == "leveldata_levelscript_mission_context":
                if not _exact_leveldata_story_context(
                    connection,
                    owner_mission,
                    context_mission,
                ):
                    continue
            elif relation == "levelscript_mission_context":
                if not _exact_cross_owner_mission_condition_story_context(
                    connection,
                    owner_mission,
                    context_mission,
                ):
                    continue
            elif relation == "authoritative_scope_leveldata_mission_context":
                if (
                    safe_key(connection.get("levelDataHostMissionId"))
                    != context_mission
                    or safe_key(connection.get("direction")) != "context"
                    or safe_key(connection.get("confidence"))
                    != "native_exact_validated_leveldata_shell"
                    or safe_key(connection.get("evidenceTier"))
                    != "derived_exact_shell"
                ):
                    continue
            elif relation == "dialog_tree_narrative_action":
                (
                    exact_retained_parent_shell,
                    dialog_tree_failure,
                ) = (
                    _exact_cross_owner_dialog_tree_narrative_context(
                        connection,
                        owner_mission,
                        context_mission,
                    )
                )
                legacy_leveldata_host = (
                    safe_key(connection.get("levelDataHostMissionId"))
                    == context_mission
                    and safe_key(connection.get("direction")) == "context"
                    and safe_key(connection.get("confidence")) in {
                        "native_exact_parent_quest",
                        "native_derived_exact_parent_quest",
                        "native_derived_exact_parent_mission_area_shell",
                        "native_derived_exact_parent_shell",
                        "native_exact_parent_context",
                    }
                    and safe_key(connection.get("nativeMappingId"))
                    == DIALOG_TREE_NARRATIVE_CONNECTION_MAPPING_ID
                )
                if (
                    dialog_tree_failure is not None
                    and not legacy_leveldata_host
                ):
                    cross_owner_dialog_tree_validation_failures.append(
                        dialog_tree_failure
                    )
                if not exact_retained_parent_shell and not legacy_leveldata_host:
                    continue
            elif relation == "levelscript_native_black_action":
                if (
                    safe_key(connection.get("levelDataHostMissionId"))
                    != context_mission
                    or safe_key(connection.get("direction")) != "context"
                    or safe_key(connection.get("phase"))
                    != "runtime_playback"
                    or safe_key(connection.get("confidence"))
                    != "native_exact_host"
                    or safe_key(connection.get("nativeMappingId"))
                    != LEVELSCRIPT_NATIVE_ACTION_MAPPING_ID
                ):
                    continue
            elif relation not in {
                "airwall_mission_state_radio_playback_context",
                "focus_mode_interact_locked_radio",
            }:
                continue
            cross_owner_connections[owner_mission].append({
                **connection,
                "contextMissionBundle": context_mission,
            })
        for quest in flow.get("quests") or []:
            if not isinstance(quest, dict):
                continue
            context_quest = safe_key(quest.get("id"))
            if not context_quest:
                continue
            for connection in quest.get("storyConnections") or []:
                if not isinstance(connection, dict):
                    continue
                story_key = safe_key(connection.get("key"))
                owners = story_owners.get(story_key) or set()
                if len(owners) != 1:
                    continue
                relation = safe_key(connection.get("relation"))
                exact_dialog_finish = (
                    relation == "objective_condition"
                    and safe_key(connection.get("conditionType"))
                    == "CheckTalkOptionFinish"
                    and safe_key(connection.get("direction"))
                    == "story_to_quest"
                    and safe_key(connection.get("confidence")) == "direct"
                )
                expected_action = {
                    "client_action_start": (1, "start"),
                    "client_action_succeed": (2, "succeed"),
                    "client_action_failed": (4, "failed"),
                }.get(relation)
                exact_client_action = (
                    expected_action is not None
                    and safe_key(connection.get("direction"))
                    == "quest_to_story"
                    and safe_key(connection.get("phase"))
                    == expected_action[1]
                    and safe_key(connection.get("confidence"))
                    == "native_typed_direct"
                    and connection.get("actionSlot") == expected_action[0]
                    and isinstance(connection.get("actionId"), int)
                    and not isinstance(connection.get("actionId"), bool)
                    and int(connection["actionId"]) >= 0
                    and bool(safe_key(connection.get("actionType")))
                    and bool(re.fullmatch(
                        r"MissionRuntimeAsset\.clientActionMapKey\[\d+\] -> "
                        r"actionMapRaw\.actionList\[\d+\]\._[A-Za-z]+Id",
                        safe_key(connection.get("source")),
                    ))
                )
                owner_mission = next(iter(owners))
                exact_levelscript_playback = False
                if (
                    owner_mission != context_mission
                    and relation in {
                        "levelscript_quest_processing_action",
                        "levelscript_quest_completed_action",
                    }
                ):
                    (
                        exact_levelscript_playback,
                        levelscript_failure,
                    ) = _exact_cross_owner_levelscript_quest_playback(
                        connection,
                        owner_mission,
                        context_mission,
                        context_quest,
                    )
                    if levelscript_failure is not None:
                        cross_owner_levelscript_validation_failures.append(
                            levelscript_failure
                        )
                if (
                    not exact_dialog_finish
                    and not exact_client_action
                    and not exact_levelscript_playback
                ):
                    continue
                if owner_mission not in mission_payloads:
                    continue
                mission_runtime_source = (
                    "export_full/structured/Persistent/Data/Json/"
                    f"MissionRuntimeAsset/{context_mission}.json"
                )
                levelscript_source = safe_key(connection.get("sourceFile"))
                source_files = sorted({
                    source_file
                    for source_file in (
                        levelscript_source,
                        mission_runtime_source,
                    )
                    if source_file
                })
                source_sha256 = {
                    source_file: _sha256_file(ROOT / source_file)
                    for source_file in source_files
                    if (ROOT / source_file).is_file()
                }
                companion = {
                    **connection,
                    "contextMissionBundle": context_mission,
                    "contextQuestId": context_quest,
                    "sourceFiles": source_files,
                    "sourceSha256": source_sha256,
                }
                if exact_levelscript_playback:
                    companion.update({
                        "relation":
                            "cross_owner_levelscript_quest_playback_context",
                        "originalRelation": relation,
                        "originalDirection": safe_key(
                            connection.get("direction")
                        ),
                        "originalPhase": safe_key(connection.get("phase")),
                        "direction": "context",
                        "graphEffect": "none",
                        "storyOwnerMission": owner_mission,
                        "ownership": False,
                        "relativeStoryOrder": False,
                        "orderBoundary": (
                            "the exact foreign quest state proves this Story "
                            "playback lifecycle context, but does not reassign "
                            "nominal Story ownership or order it against another "
                            "Story file"
                        ),
                    })
                else:
                    companion["sourceFile"] = mission_runtime_source
                cross_owner_connections[owner_mission].append(companion)
    for mission in cross_owner_connections:
        cross_owner_connections[mission].sort(key=lambda row: (
            natural_key(safe_key(row.get("key"))),
            natural_key(safe_key(row.get("npcProxyMissionId"))),
            natural_key(safe_key(row.get("npcProxyId"))),
        ))
    rows = [
        build_gap_row(
            row,
            mission_payloads.get(safe_key(row.get("mission"))),
            mission_bundle_exists=safe_key(row.get("mission")) in mission_bundle_presence,
            native_playback_index=native_playback_index,
            action_story_occurrences=action_story_occurrences,
            non_mission_content=non_mission_content,
            offline_exhaustion_index=offline_exhaustion_index,
            quest_attachment_diagnostic_index=(
                quest_attachment_diagnostic_index
            ),
            cross_owner_story_connections=cross_owner_connections.get(
                safe_key(row.get("mission"))
            ),
            story_trigger_manifest=story_trigger_manifest,
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

    exact_black_carrier_validation_failures = [
        failure
        for row in rows
        for failure in row.get(
            "exactBlackCarrierValidationFailures"
        ) or []
        if isinstance(failure, dict)
    ]
    exact_runtime_config_validation_failures = [
        failure
        for row in rows
        for failure in row.get(
            "exactRuntimeConfigValidationFailures"
        ) or []
        if isinstance(failure, dict)
    ]
    story_trigger_manifest_validation_failures = [
        failure
        for row in rows
        for failure in row.get(
            "storyTriggerManifestValidationFailures"
        ) or []
        if isinstance(failure, dict)
    ]

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
        "offlineExhaustionEvidence": offline_exhaustion_status or {
            "status": "not_supplied",
            "graphEffect": "none",
        },
        "questAttachmentDiagnosticEvidence": (
            quest_attachment_diagnostic_status
            or {
                "status": "not_supplied",
                "graphEffect": "none",
            }
        ),
        "storyTriggerManifestEvidence": story_trigger_manifest_status or {
            "status": "not_supplied",
            "graphEffect": "none",
        },
        "projectAuthoredStoryEvidence": project_authored_status or {
            "status": "not_supplied",
            "graphEffect": "none",
        },
        "storyTriggerClosureValidation": {
            "validator": "story_trigger_closure_contracts_v2",
            "status": (
                "validation_failed"
                if story_trigger_manifest_validation_failures
                else "validated"
            ),
            "validationFailures":
                story_trigger_manifest_validation_failures,
            "graphEffect": "none",
        },
        "exactBlackCarrierValidation": {
            "validator": "exact_black_carrier_context_v1",
            "status": (
                "validation_failed"
                if exact_black_carrier_validation_failures
                else "validated"
            ),
            "validationFailures":
                exact_black_carrier_validation_failures,
            "graphEffect": "none",
        },
        "exactRuntimeConfigValidation": {
            "validator": "exact_runtime_config_context_v2",
            "status": (
                "validation_failed"
                if exact_runtime_config_validation_failures
                else "validated"
            ),
            "validationFailures":
                exact_runtime_config_validation_failures,
            "graphEffect": "none",
        },
        "crossOwnerLevelScriptQuestPlaybackValidation": {
            "validator": "cross_owner_levelscript_quest_playback_v1",
            "status": (
                "validation_failed"
                if cross_owner_levelscript_validation_failures
                else "validated"
            ),
            "validationFailures": cross_owner_levelscript_validation_failures,
            "graphEffect": "none",
        },
        "crossOwnerDialogTreeNarrativeValidation": {
            "validator": "cross_owner_dialog_tree_narrative_context_v1",
            "status": (
                "validation_failed"
                if cross_owner_dialog_tree_validation_failures
                else "validated"
            ),
            "validationFailures": cross_owner_dialog_tree_validation_failures,
            "graphEffect": "none",
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
