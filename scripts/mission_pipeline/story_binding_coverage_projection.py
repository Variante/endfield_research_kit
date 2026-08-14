"""Project frozen Story binding evidence into the coverage report schema.

All native/evidence classification is completed by the caller. This module only
normalizes the supplied frozen collections and audit payloads for publication.
"""

from __future__ import annotations

from typing import Any


def build_report(
    *,
    ACTIONBASE_FORMATTER_NAME_AUDIT: Any,
    CALLSERVER_CALLBACK_AUDIT_JSON: Any,
    DEFAULT_LEVEL_SEQUENCE_TEXTASSET_ROOT: Any,
    action_name_summary: Any,
    callback_audit_summary: Any,
    cinematic_report: Any,
    compact_callback_audit: Any,
    composed_root_playback_alias_rows: Any,
    connected_by_mission: Any,
    connected_cross_owner_keys: Any,
    connected_keys: Any,
    connected_keys_by_evidence_tier: Any,
    context_only_trigger_route_count: Any,
    context_only_trigger_route_files: Any,
    definition_only_class_counts: Any,
    definition_only_classification: Any,
    definition_only_interactive_config_keys: Any,
    dynamic_scene_identity: Any,
    evidence_row_count: Any,
    evidence_tier_counts: Any,
    kind_counts: Any,
    language: Any,
    level_sequence_asset_summary: Any,
    lua_playback_evidence: Any,
    mission_ids: Any,
    mission_sidecar_root: Any,
    mission_state_dependency_cross_owner_keys: Any,
    mission_state_dependency_keys: Any,
    mission_state_dependency_placements: Any,
    mission_state_dependency_rows: Any,
    missionless_nodes: Any,
    missionless_runtime_nodes: Any,
    missionless_runtime_story_keys: Any,
    missionless_runtime_story_placements: Any,
    missionless_story_keys: Any,
    missionless_story_placements: Any,
    native_playback_event_keys: Any,
    native_playback_unscoped: Any,
    native_playback_without_named_event: Any,
    natural_quest_key: Any,
    pipeline_index_path: Any,
    post_playback_action_name_audit: Any,
    post_playback_callserver_summary: Any,
    post_playback_level_sequence_asset_audit: Any,
    post_playback_variable_bridge_audit: Any,
    rejected_playback_by_key: Any,
    relation_counts: Any,
    repo_path: Any,
    root_playback_alias_rows: Any,
    sidecars_read: Any,
    story_files_with_trigger_routes: Any,
    story_index_path: Any,
    story_rows: Any,
    story_trigger_manifest: Any,
    time: Any,
    tracked_proxy_branch_context_count: Any,
    tracked_proxy_topology_class_counts: Any,
    tracked_proxy_topology_failures: Any,
    tracked_proxy_topology_route_count: Any,
    tracked_proxy_topology_rows: Any,
    trigger_route_count: Any,
    unlinked: Any,
    unlinked_definition_only: Any,
    unlinked_dialog_tree_containment: Any,
    unlinked_dialog_tree_left_subtitle: Any,
    unlinked_files_with_trigger_routes: Any,
    unlinked_non_mission_content: Any,
    unresolved_dialog_tree_containment: Any,
    unresolved_dialog_tree_left_subtitle: Any,
    unresolved_dialog_tree_story_playback: Any,
    unresolved_timeline_containment: Any,
    variable_bridge_summary: Any,
) -> dict[str, Any]:
    report = {
        "schemaVersion": 19,
        "generated": int(time.time()),
        "language": language,
        "policy": (
            "Original exported game data and current-build native serialization only; "
            "OCR, manual overrides, and gameplay observations do not promote a connection. "
            "Story rows whose nominal owner is not a pipeline mission enter the denominator "
            "only when an accepted generated pipeline edge connects them."
        ),
        "sources": {
            "pipelineIndex": repo_path(pipeline_index_path),
            "storyIndex": repo_path(story_index_path),
            "missionSidecars": repo_path(mission_sidecar_root),
            "definitionOnlyAudioMetadata": definition_only_classification["source"],
            "luaPlaybackAudit": lua_playback_evidence["auditReport"],
            "luaPlaybackAuditSha256": lua_playback_evidence["auditSha256"],
            "cinematicQueueRuntimeAudit": cinematic_report,
            "levelSequenceTextAssets": repo_path(
                DEFAULT_LEVEL_SEQUENCE_TEXTASSET_ROOT
            ),
            "actionBaseFormatterTable": str(
                ACTIONBASE_FORMATTER_NAME_AUDIT.get("sourceFile") or ""
            ),
            "callServerCallbackAudit": repo_path(
                CALLSERVER_CALLBACK_AUDIT_JSON
            ),
        },
        "counts": {
            "pipelineMissions": len(mission_ids),
            "missionSidecarsRead": sidecars_read,
            "uniqueStoryFiles": len(story_rows),
            "connectedUniqueStoryFiles": len(connected_keys),
            "connectedCrossOwnerStoryFiles": len(connected_cross_owner_keys),
            "unlinkedUniqueStoryFiles": len(unlinked),
            "connectedMissionPlacements": sum(len(keys) for keys in connected_by_mission.values()),
            "connectionEvidenceRows": evidence_row_count,
            "storyTriggerRoutes": trigger_route_count,
            "storyFilesWithTriggerRoutes": story_files_with_trigger_routes,
            "trackedProxyCandidateTopologyContexts": len(
                tracked_proxy_topology_rows
            ),
            "trackedProxyCandidateTopologyRoutes": (
                tracked_proxy_topology_route_count
            ),
            "trackedProxyCandidateTopologyBranchContexts": (
                tracked_proxy_branch_context_count
            ),
            "trackedProxyCandidateTopologyForkSpanningContexts": sum(
                bool(row.get("spansAuthoredForkArms"))
                for row in tracked_proxy_topology_rows
            ),
            "trackedProxyCandidateTopologyMergeContexts": sum(
                bool(row.get("intersectsAuthoredMerge"))
                for row in tracked_proxy_topology_rows
            ),
            "trackedProxyCandidateTopologyFailures": len(
                tracked_proxy_topology_failures
            ),
            "nativeCinematicProducerStoryFiles": sum(
                any(route.get("nativeCinematicProducerRoutes") for route in row.get("routes") or [])
                for row in story_trigger_manifest.values()
            ),
            "nativeCinematicProducerRouteAttachments": sum(
                len(route.get("nativeCinematicProducerRoutes") or [])
                for row in story_trigger_manifest.values()
                for route in row.get("routes") or []
            ),
            "contextOnlyTriggerRouteFiles":
                context_only_trigger_route_files,
            "contextOnlyTriggerRoutes": context_only_trigger_route_count,
            "definitionOnlyInteractiveConfigFiles": len({
                key
                for key in definition_only_interactive_config_keys
                if key in story_trigger_manifest
            }),
            "definitionOnlyInteractiveConfigRoutes": sum(
                len(story_trigger_manifest[key].get("routes") or [])
                for key in definition_only_interactive_config_keys
                if key in story_trigger_manifest
            ),
            "unlinkedStoryFilesWithTriggerRoutes": unlinked_files_with_trigger_routes,
            "rootPlaybackAliasFiles": len({
                row["playableAssetStoryKey"]
                for row in root_playback_alias_rows
            }),
            "rootPlaybackAliasRows": len(root_playback_alias_rows),
            "composedRootPlaybackAliasFiles": len({
                row["playableAssetStoryKey"]
                for row in composed_root_playback_alias_rows
            }),
            "composedRootPlaybackAliasRows":
                len(composed_root_playback_alias_rows),
            "rejectedStoryPlaybackCandidates": sum(
                len(rows)
                for key, rows in rejected_playback_by_key.items()
                if key in story_rows
            ),
            "scannedLuaStoryPlaybackCalls":
                lua_playback_evidence["scannedPlaybackCalls"],
            "acceptedLuaExactPlaybackCalls": len(
                lua_playback_evidence["acceptedExactPlaybackCalls"]
            ),
            "acceptedLuaTableCarrierCalls":
                lua_playback_evidence["acceptedTableCarrierCalls"],
            "rejectedLuaCaseMismatchCalls": len(
                lua_playback_evidence["rejectedCaseMismatchCalls"]
            ),
            "runtimeLuaHandleDispatcherCalls":
                lua_playback_evidence["runtimeHandleDispatcherCallCount"],
            "runtimeLuaHandleDispatcherFamilies":
                lua_playback_evidence["runtimeHandleDispatcherFamilyCount"],
            "unresolvedLuaAuthoredPlaybackCalls":
                lua_playback_evidence["unresolvedPlaybackCalls"],
            "missionStateDependencyStoryFiles": len(
                mission_state_dependency_keys
            ),
            "missionStateDependencyCrossOwnerStoryFiles": len(
                mission_state_dependency_cross_owner_keys
            ),
            "missionStateDependencyPlacements": len(
                mission_state_dependency_placements
            ),
            "unlinkedNativePlaybackFiles": len(native_playback_unscoped),
            "unlinkedNativePlaybackWithoutNamedEvent": len(native_playback_without_named_event),
            "unresolvedTimelineContainmentFiles": len(unresolved_timeline_containment),
            "unresolvedDialogTreeNarrativeFiles": len(unresolved_dialog_tree_containment),
            "unlinkedDialogTreeNarrativeFiles": len(unlinked_dialog_tree_containment),
            "unresolvedDialogTreeLeftSubtitleFiles": len(
                unresolved_dialog_tree_left_subtitle
            ),
            "unlinkedDialogTreeLeftSubtitleFiles": len(
                unlinked_dialog_tree_left_subtitle
            ),
            "unresolvedDialogTreeStoryPlaybackFiles": len(
                unresolved_dialog_tree_story_playback
            ),
            "unlinkedDefinitionOnlyFiles": len(unlinked_definition_only),
            "nonMissionContentFiles": len(unlinked_non_mission_content),
            "unlinkedDefinitionOnlyAudioMetadataFiles": definition_only_class_counts.get(
                "original_audio_metadata_without_playback_consumer",
                0,
            ),
            "unlinkedDefinitionOnlyEmptyAudioLikelyLegacyFiles": definition_only_class_counts.get(
                "explicit_empty_audio_metadata_likely_legacy_definition",
                0,
            ),
            "unlinkedDefinitionOnlyWithoutAudioMetadataFiles": definition_only_class_counts.get(
                "no_audio_metadata_or_playback_consumer_recovered",
                0,
            ),
            "missionlessSubGameRows": len(missionless_nodes),
            "missionlessSubGameStoryFiles": len(missionless_story_keys),
            "missionlessSubGameStoryPlacements": missionless_story_placements,
            "missionlessNativeRuntimeRows": len(missionless_runtime_nodes),
            "missionlessNativeRuntimeStoryFiles": len(missionless_runtime_story_keys),
            "missionlessNativeRuntimeStoryPlacements": missionless_runtime_story_placements,
            "missionlessNativeRuntimeProducerRoutes": sum(
                len(node.get("localProducerRoutes") or [])
                for node in missionless_runtime_nodes
            ),
            "missionlessNativeRuntimePlaybackGates": sum(
                len(node.get("playbackGates") or [])
                for node in missionless_runtime_nodes
            ),
            "missionlessNativeRuntimePlaybackGateStoryFiles": len({
                story["key"]
                for node in missionless_runtime_nodes
                if node.get("playbackGates")
                for story in node.get("storyFiles") or []
            }),
            "missionlessNativeRuntimePostPlaybackControls": sum(
                len(node.get("postPlaybackControls") or [])
                for node in missionless_runtime_nodes
            ),
            "missionlessNativeRuntimePostPlaybackBranchPoints": sum(
                len(control.get("branchPointLocalIds") or [])
                for node in missionless_runtime_nodes
                for control in node.get("postPlaybackControls") or []
            ),
            "missionlessNativeRuntimePostPlaybackServerHandoffs": sum(
                len(control.get("serverHandoffs") or [])
                for node in missionless_runtime_nodes
                for control in node.get("postPlaybackControls") or []
            ),
            "missionlessNativeRuntimePostPlaybackCallbackHeaderUids": sum(
                len(handoff.get("possibleCallbackHeaderUIDs") or [])
                for node in missionless_runtime_nodes
                for control in node.get("postPlaybackControls") or []
                for handoff in control.get("serverHandoffs") or []
            ),
            "callServerActions": callback_audit_summary.get(
                "callServerActions", 0
            ),
            "callServerCallbackOutputUids": callback_audit_summary.get(
                "callbackOutputUids", 0
            ),
            "callServerExactCallbackHeaders": callback_audit_summary.get(
                "exactCallbackHeaders", 0
            ),
            "callServerCallbackHeadersReachingStory": callback_audit_summary.get(
                "callbackHeadersReachingStory", 0
            ),
            "callServerUnresolvedCallbackOutputs": callback_audit_summary.get(
                "unresolvedCallbackOutputs", 0
            ),
            "postPlaybackCallServerExactContracts": (
                post_playback_callserver_summary.get("exactContracts", 0)
            ),
            "postPlaybackCallServerUnresolvedContracts": (
                post_playback_callserver_summary.get("unresolvedContracts", 0)
            ),
            "postPlaybackLevelSequenceActions": level_sequence_asset_summary.get(
                "typedActionPlacements", 0
            ),
            "postPlaybackLevelSequenceIds": level_sequence_asset_summary.get(
                "serializedLevelSequenceIds", 0
            ),
            "postPlaybackLevelSequenceExactAssets": level_sequence_asset_summary.get(
                "exactResolvedLevelSequenceIds", 0
            ),
            "postPlaybackLevelSequenceUnresolvedIds": level_sequence_asset_summary.get(
                "unresolvedLevelSequenceIds", 0
            ),
            "postPlaybackLevelSequenceRelatedOriginalFiles": (
                level_sequence_asset_summary.get("relatedOriginalFiles", 0)
            ),
            "postPlaybackActionPlacements": action_name_summary.get(
                "actionPlacements", 0
            ),
            "postPlaybackFormatterNamedActions": action_name_summary.get(
                "formatterNamedActionPlacements", 0
            ),
            "postPlaybackFallbackNamedActions": action_name_summary.get(
                "fallbackNamedActionPlacements", 0
            ),
            "postPlaybackUnresolvedActionShapes": action_name_summary.get(
                "unresolvedOutsideActionBaseShapes", 0
            ),
            "postPlaybackVariableSetters": variable_bridge_summary.get(
                "postPlaybackVariableSetters", 0
            ),
            "postPlaybackVariableExactListenerMatches": (
                variable_bridge_summary.get("exactSetterListenerMatches", 0)
            ),
            "postPlaybackVariableCrossStoryListenerMatches": (
                variable_bridge_summary.get(
                    "crossStorySetterListenerMatches", 0
                )
            ),
            "partiallyConnectedDialogTreeNarrativeFiles": len(
                unresolved_dialog_tree_containment & connected_keys
            ),
        },
        "byKind": kind_counts,
        "relationEvidenceRows": dict(sorted(relation_counts.items())),
        "evidenceTierRows": dict(sorted(evidence_tier_counts.items())),
        "evidenceTierUniqueStoryFiles": {
            tier: len(keys)
            for tier, keys in sorted(connected_keys_by_evidence_tier.items())
        },
        "missionStateStoryDependencies": sorted(
            mission_state_dependency_rows,
            key=lambda row: (
                natural_quest_key(str(row.get("missionId") or "")),
                natural_quest_key(str(row.get("key") or "")),
            ),
        ),
        "storyTriggerManifest": story_trigger_manifest,
        "trackedProxyCandidateTopology": {
            "schema": "trackedProxyCandidateQuestTopologyAudit.v1",
            "status": (
                "validation_failed"
                if tracked_proxy_topology_failures
                else "validated"
            ),
            "counts": {
                "contexts": len(tracked_proxy_topology_rows),
                "routes": tracked_proxy_topology_route_count,
                "branchContexts": tracked_proxy_branch_context_count,
                "forkSpanningContexts": sum(
                    bool(row.get("spansAuthoredForkArms"))
                    for row in tracked_proxy_topology_rows
                ),
                "mergeContexts": sum(
                    bool(row.get("intersectsAuthoredMerge"))
                    for row in tracked_proxy_topology_rows
                ),
                "topologyClasses": dict(sorted(
                    tracked_proxy_topology_class_counts.items()
                )),
                "validationFailures": len(
                    tracked_proxy_topology_failures
                ),
            },
            "rows": tracked_proxy_topology_rows,
            "validationFailures": tracked_proxy_topology_failures[:100],
            "evidenceBoundary": (
                "This audit classifies candidate quests in original "
                "MissionRuntime topology. The original binary keeps proxy "
                "active-row selection and quest state application separate, "
                "so no dialog is assigned to a quest arm and no Story order "
                "edge is added."
            ),
        },
        "postPlaybackActionNameAudit": post_playback_action_name_audit,
        "callServerCallbackAudit": compact_callback_audit,
        "postPlaybackLevelSequenceAssetAudit": (
            post_playback_level_sequence_asset_audit
        ),
        "luaStoryPlaybackEvidence": lua_playback_evidence,
        "rootPlaybackAliases": root_playback_alias_rows,
        "composedRootPlaybackAliases":
            composed_root_playback_alias_rows,
        "missionStateDependencyCrossOwnerStoryKeys": sorted(
            mission_state_dependency_cross_owner_keys,
            key=natural_quest_key,
        ),
        "nativePlaybackEventFamilies": {
            event_name: len(keys)
            for event_name, keys in sorted(native_playback_event_keys.items())
        },
        "nativePlaybackEventFamilyKeys": {
            event_name: sorted(keys, key=natural_quest_key)
            for event_name, keys in sorted(native_playback_event_keys.items())
        },
        "unlinkedNativePlaybackWithoutNamedEventKeys": sorted(
            native_playback_without_named_event,
            key=natural_quest_key,
        ),
        "unlinked": unlinked,
        "connectedCrossOwnerStoryKeys": sorted(
            connected_cross_owner_keys,
            key=natural_quest_key,
        ),
        "unlinkedNativePlaybackKeys": sorted(native_playback_unscoped, key=natural_quest_key),
        "unresolvedTimelineContainmentKeys": sorted(unresolved_timeline_containment, key=natural_quest_key),
        "unresolvedDialogTreeNarrativeKeys": sorted(
            unresolved_dialog_tree_containment,
            key=natural_quest_key,
        ),
        "unlinkedDialogTreeNarrativeKeys": sorted(
            unlinked_dialog_tree_containment,
            key=natural_quest_key,
        ),
        "unresolvedDialogTreeLeftSubtitleKeys": sorted(
            unresolved_dialog_tree_left_subtitle,
            key=natural_quest_key,
        ),
        "unlinkedDialogTreeLeftSubtitleKeys": sorted(
            unlinked_dialog_tree_left_subtitle,
            key=natural_quest_key,
        ),
        "unresolvedDialogTreeStoryPlaybackKeys": sorted(
            unresolved_dialog_tree_story_playback,
            key=natural_quest_key,
        ),
        "unlinkedDefinitionOnlyKeys": sorted(
            unlinked_definition_only,
            key=natural_quest_key,
        ),
        "definitionOnlyNegativeConsumerClassification": definition_only_classification,
        "nonMissionContentKeys": [
            {"key": key, **unlinked_non_mission_content[key]}
            for key in sorted(unlinked_non_mission_content, key=natural_quest_key)
        ],
        "missionlessSubGamePlaybackNodes": missionless_nodes,
        "missionlessNativeRuntimeNodes": missionless_runtime_nodes,
        "postPlaybackVariableBridgeAudit": (
            post_playback_variable_bridge_audit
        ),
        "dynamicSceneIdentityCrossReferences": dynamic_scene_identity,
        "partiallyConnectedDialogTreeNarrativeKeys": sorted(
            unresolved_dialog_tree_containment & connected_keys,
            key=natural_quest_key,
        ),
    }
    return report

