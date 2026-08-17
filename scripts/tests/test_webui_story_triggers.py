from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "webui" / "src" / "features" / "story_triggers.js"
APP = ROOT / "webui" / "app.js"
APP_TREE = ROOT / "webui" / "app_tree.js"
MISSION_PIPELINE = ROOT / "webui" / "src" / "features" / "mission_pipeline" / "index.js"


@unittest.skipUnless(shutil.which("node"), "Node.js is required for WebUI JavaScript tests")
class StoryTriggerWebUiTests(unittest.TestCase):
    def run_node(self, source: str) -> None:
        completed = subprocess.run(
            ["node", "-e", source],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            completed.returncode,
            0,
            msg=f"Node test failed:\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}",
        )

    def test_exact_native_path_is_the_primary_playback_trigger(self) -> None:
        self.run_node(
            f"""
const assert = require("node:assert/strict");
const triggers = require({str(MODULE)!r});
const manifest = {{
  dlg_test_1: {{
    routes: [
      {{
        storyKey: "dlg_test_1",
        causality: "condition",
        missionId: "test",
        steps: [{{kind: "story", id: "dlg_test_1"}}, {{kind: "quest", id: "test_q1"}}],
      }},
      {{
        storyKey: "dlg_test_1",
        causality: "context",
        missionId: "test",
        nativePaths: [{{
          eventName: "ScriptEvent_OnLeaderEnterTriggerVolume",
          eventSummary: "leader enters trigger slot 7",
          steps: [{{actionName: "StartDialogAction"}}],
        }}],
      }},
    ],
  }},
}};
const view = triggers.triggerView(manifest, "dlg_test_1");
assert.equal(view.category, "native_playback");
assert.equal(view.hasProvenPlayback, true);
assert.equal(view.routes[0].causality, "context");
assert.deepEqual(triggers.compactTrigger(view), {{
  category: "native_playback",
  event: "leader enters trigger slot 7",
  eventName: "ScriptEvent_OnLeaderEnterTriggerVolume",
  actions: ["StartDialogAction"],
  owner: "test",
  pathCount: 1,
}});
"""
        )

    def test_non_playback_relations_remain_explicitly_non_playback(self) -> None:
        self.run_node(
            f"""
const assert = require("node:assert/strict");
const triggers = require({str(MODULE)!r});
const manifest = {{
  condition: {{routes: [{{storyKey: "condition", causality: "condition"}}]}},
  context: {{routes: [{{storyKey: "context", causality: "context"}}]}},
  unresolvedContext: {{routes: [{{storyKey: "unresolvedContext", causality: "context_owner_unresolved"}}]}},
  dependency: {{routes: [{{storyKey: "dependency", causality: "dependency"}}]}},
  definition: {{attachmentStatus: "definition_only_no_consumer", routes: []}},
  exhausted: {{
    attachmentStatus: "unlinked_no_trigger_route",
    offlineRecovery: {{graphEffect: "none", evidenceKind: "fixture_boundary"}},
    routes: [],
  }},
  mismatch: {{routes: [{{storyKey: "somewhere_else", causality: "playback"}}]}},
}};
for (const [key, category] of [
  ["condition", "condition"],
  ["context", "context"],
  ["unresolvedContext", "context_owner_unresolved"],
  ["dependency", "dependency"],
  ["definition", "definition_only"],
  ["exhausted", "offline_exhausted"],
  ["mismatch", "unknown"],
  ["missing", "unknown"],
]) {{
  const view = triggers.triggerView(manifest, key);
  assert.equal(view.category, category, key);
  assert.equal(view.hasProvenPlayback, false, key);
}}
"""
        )

    def test_trigger_manifest_and_surfaces_are_debug_only(self) -> None:
        app_source = APP.read_text(encoding="utf-8")
        app_tree_source = APP_TREE.read_text(encoding="utf-8")
        language_switch = app_source.split(
            "async function switchLanguage(",
            1,
        )[1].split("\nfunction ", 1)[0]

        self.assertNotIn("loadStoryTriggerManifest(", language_switch)
        self.assertNotIn(
            "ensureStoryTriggerManifestForDebug(",
            language_switch,
        )
        self.assertIn(
            "coverage.offlineRecoveryEvidence.storyTriggerManifestOverlay",
            app_source,
        )
        self.assertIn(
            "const triggerSummary = STATE.showDebug "
            "? storyTriggerCompactText(e.k) : null;",
            app_source,
        )
        self.assertIn(
            "if (!STATE.showDebug) {\n"
            "    slot.hidden = true;\n"
            "    return;\n"
            "  }",
            app_source,
        )
        self.assertIn(
            "if (next && typeof ensureStoryTriggerManifestForDebug",
            app_tree_source,
        )
        self.assertIn(
            "if (typeof rebuildTree === \"function\") "
            "rebuildTree({ resetScroll: false });",
            app_tree_source,
        )

    def test_mission_pipeline_surfaces_native_producer_and_attached_files(self) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn("route.nativeCinematicProducerRoutes", source)
        self.assertIn('t("cinematicProducer")', source)
        self.assertIn("nativeCinematicProducerRouteAttachments", source)
        self.assertIn("route.sourceFiles", source)

    def test_mission_pipeline_labels_nearest_quest_as_spatial_context(self) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn(
            'cluster.sourceKind !== "exact_world_entity_interaction_trigger"',
            source,
        )
        self.assertIn("Math.sqrt(dx * dx + dy * dy + dz * dz)", source)
        self.assertIn('t("spatialNearestQuest")', source)
        self.assertIn('t("spatialProximityOnly")', source)
        self.assertIn(
            "spatial context only; not quest ownership or Story order",
            source,
        )

    def test_mission_pipeline_folds_and_separates_weak_spatial_evidence(self) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn("track.inheritedSpatialSourceMatches", source)
        self.assertIn('sourceKind: "direct_levelscript_spatial_proximity"', source)
        self.assertIn("rows.slice(1)", source)
        self.assertIn('t("spatialAlternateWeakPositionsHint")', source)
        self.assertIn('t("spatialInheritedWeakPositionsHint")', source)
        self.assertIn("for (const key of exactPositionedKeys) cluster.files.delete(key)", source)

    def test_mission_pipeline_labels_pattern_discovered_dialog_definitions(
        self,
    ) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn(
            "Auto-discovered DialogTree definition - no activator on "
            "current original-data surfaces",
            source,
        )
        self.assertIn(
            "registered_dialog_tree_definition_binary_consumer_surface_exhausted",
            source,
        )
        self.assertIn('id="mp-definition-recovery"', source)
        self.assertIn(
            "Per-object filename, line, option, and branch declarations are "
            "not required",
            source,
        )

    def test_mission_pipeline_surfaces_hash_validated_story_connection_files(self) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn("storyConnectionOriginalFilesHtml", source)
        self.assertIn("relatedOriginalFilesValidation", source)
        self.assertIn('t("storyConnectionOriginalFiles")', source)
        self.assertIn("file.sha256", source)
        self.assertIn("storyConnectionProvenanceSummary", source)
        self.assertIn("storyConnectionNonPath", source)

    def test_mission_pipeline_surfaces_generic_receiver_story_context(self) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn("nativeReceiverStoryContextIndex", source)
        self.assertIn("nativeReceiverStoryContextHtml", source)
        self.assertIn('t("nativeReceiverStoryContext")', source)
        self.assertIn("context.relatedOriginalFiles", source)
        self.assertIn("nativeReceiverStoryContextHint", source)

    def test_mission_pipeline_surfaces_per_story_trigger_zone_confirmations(self) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn("activation.triggerZoneConfirmations", source)
        self.assertIn("observation.decodedShape", source)
        self.assertIn("observation.triggerSlotIdFilter", source)
        self.assertIn("observation.sourceSha256", source)
        self.assertIn("not mission ownership, event firing, branch choice, or Story order", source)

    def test_mission_pipeline_surfaces_timeline_runtime_and_exact_activation_boundary(self) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn("timelineEmbeddedStoryRuntimeAudit", source)
        self.assertIn("timelineRuntimeHtml", source)
        self.assertIn('t("timelineEmbeddedRuntimeChain")', source)
        self.assertIn("controlRuntimeContract", source)
        self.assertIn("row.directorHosts", source)
        self.assertIn("control.exposedReferenceKey", source)
        self.assertIn("control.parentTimelineIdentity", source)
        self.assertIn('t("timelineEmbeddedDirectorBoundary")', source)
        self.assertIn("file.rawDataSha256", source)
        self.assertIn("timelineActivationRoutesById", source)
        self.assertIn("row.parentDialogActivationRouteIds", source)
        self.assertIn('t("timelineEmbeddedActivationRoute")', source)
        self.assertIn("route.missionShellIds", source)
        self.assertIn("route.actionChain", source)
        self.assertIn("route.controlDecisions", source)
        self.assertIn("missionTimelineActivationHtml", source)
        self.assertIn("route?.missionShellOwnership", source)
        self.assertIn("route.localTriggerVolumeContext", source)
        self.assertIn('t("timelineEmbeddedTriggerVolume")', source)
        self.assertIn("volume.waitSrvRes", source)
        self.assertIn("timelineQuestSpatialContextsHtml", source)
        self.assertIn("route?.questSpatialContexts", source)
        self.assertIn('t("timelineEmbeddedQuestSpatialBoundary")', source)
        self.assertIn("row.containmentMethod", source)
        self.assertIn("route.relatedOriginalFiles", source)
        self.assertIn("timelineConfigurationContextsById", source)
        self.assertIn("row.parentDialogConfigurationContextIds", source)
        self.assertIn("missionTimelineConfigurationHtml", source)
        self.assertIn('t("timelineEmbeddedConfigurationRoute")', source)
        self.assertIn("context.questNavigationContext", source)
        self.assertIn("context.relatedOriginalFiles", source)
        self.assertIn(
            "This is configuration/navigation context, not proof of parent playback, quest activation, branch selection, or Story order.",
            source,
        )
        self.assertIn(
            "A conditional path proves the authored route, not that its case was selected at runtime; parallel siblings remain unordered.",
            source,
        )

    def test_mission_pipeline_surfaces_fixed_point_carrier_closure(self) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn("metadata?.maximumShortestPathDepth", source)
        self.assertIn('t("fixedPointTraversal")', source)
        self.assertIn("nestedCarrierCensus.runtimeEntityHubClosure", source)
        self.assertIn("nestedCarrierCensus.sharedRuntimeAggregateClosure", source)
        self.assertIn("nestedCarrierCensus.relatedOriginalFiles", source)
        self.assertIn('t("exactSerializedInstances")', source)
        self.assertIn("exactIndexedTypeLabels", source)
        self.assertIn("objectsWithTruncatedScalars", source)

    def test_mission_pipeline_surfaces_complete_mission_state_alternatives(self) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn("branches.nativeMissionStateBranches", source)
        self.assertIn("row.externalStoryKeys", source)
        self.assertIn('data-mission-state-branch=', source)
        self.assertIn("row.relatedOriginalFiles", source)
        self.assertIn("alternatives, not Story order or ownership", source)

    def test_mission_pipeline_marks_complete_cross_boundary_native_branches(self) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn("row.externalStoryKeys", source)
        self.assertIn("row.crossBoundary", source)
        self.assertIn("nativeCrossBoundaryExternal", source)
        self.assertIn("nativeCrossBoundaryParallelHint", source)
        self.assertIn("summary.nativeControlCrossBoundaryBranchCount", source)

    def test_mission_pipeline_surfaces_complete_serialized_native_arms(self) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn("row.fullArms || row.arms", source)
        self.assertIn("exact_complete_active_action_map", source)
        self.assertIn("arm.entryAction", source)
        self.assertIn("arm.exclusiveActions", source)
        self.assertIn("row.sharedDownstreamActionLocalIds", source)
        self.assertIn("nativeInactiveArm", source)
        self.assertIn("summary.nativeControlNonStoryArmCount", source)
        self.assertIn("Non-Story sibling actions do not establish", source)

    def test_mission_pipeline_surfaces_property_contract_as_non_ordering_context(self) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn("activation.authoredPropertyContract", source)
        self.assertIn('t("missionObservedProperty")', source)
        self.assertIn("consumer.propertyKeys", source)
        self.assertIn("They do not identify the writer, Story owner, or scene-file order.", source)

    def test_mission_pipeline_surfaces_mission_observed_levelscript_context(self) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn("order.missionObservedLevelScriptContexts", source)
        self.assertIn('t("missionObservedScriptContexts")', source)
        self.assertIn('t("propertyWriterUnresolved")', source)
        self.assertIn("row.relatedOriginalFiles", source)

    def test_mission_pipeline_surfaces_mission_named_leveldata_receiver_context(self) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn("order.missionNamedLevelDataReceiverContexts", source)
        self.assertIn('t("missionNamedLevelDataReceiverContexts")', source)
        self.assertIn('t("missionNamedLevelDataReceiverBoundary")', source)
        self.assertIn("row.levelDataHost", source)
        self.assertIn("mp-leveldata-receiver-context", source)

    def test_mission_pipeline_surfaces_typed_mission_area_leveldata_shells(self) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn("order.missionAreaLevelDataReceiverContexts", source)
        self.assertIn(
            't("missionAreaLevelDataReceiverContexts")',
            source,
        )
        self.assertIn("row.scopeStatus", source)
        self.assertIn("row.hostMissionIds", source)
        self.assertIn("row.levelNums", source)
        self.assertIn(
            "activation.missionAreaLevelDataShellContext",
            source,
        )

    def test_mission_pipeline_surfaces_exact_active_phase_receivers(self) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn("activation.activePhaseReceiverControl", source)
        self.assertIn('t("binaryActivePhaseReceiver")', source)
        self.assertIn("Setup → ActiveBegin → Active(", source)
        self.assertIn("not who selected public Active", source)

    def test_mission_pipeline_surfaces_teleport_finish_correlation_boundary(self) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn("receiver.teleportFinishCorrelations", source)
        self.assertIn('t("teleportFinishCorrelation")', source)
        self.assertIn("item.actionIdFilter", source)
        self.assertIn("item.externalSerializedOccurrenceCount", source)
        self.assertIn("runtime_only_no_serialized_levelscript_producer", source)
        self.assertIn('t("teleportFinishCorpusFiles")', source)
        self.assertIn("item.carrierAudit", source)
        self.assertIn('t("teleportCarrierAudit")', source)
        self.assertIn("carrier.signatureMethodCount", source)
        self.assertIn("carrier.containerPathCount", source)
        self.assertIn("carrier.directCallsiteCount", source)
        self.assertIn("initializerStates.zero", source)

    def test_mission_pipeline_surfaces_exact_client_active_request_selector(self) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn("activation.clientActiveRequestControl", source)
        self.assertIn('t("binaryClientActiveRequest")', source)
        self.assertIn("clientActiveRequestControl.runtimePath", source)
        self.assertIn("server-side selection rule remains unavailable", source)
        self.assertIn('t("binaryActiveVolume")', source)
        self.assertIn("clientActiveRequestControl.activeShapeList?.shapes", source)
        self.assertIn("validated_runtime_position_dependent", source)
        self.assertIn("shape.position", source)
        self.assertIn("shape.eulerAngles", source)

    def test_mission_pipeline_distinguishes_public_state_server_carriers(self) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn("publicStateControl.publicStateSourceFlow", source)
        self.assertIn("publicStateControl.selfSceneInfoMessageId", source)
        self.assertIn("levelScripts[] → ServerSync", source)
        self.assertIn("They prove that Enabled is server-supplied", source)

    def test_mission_pipeline_surfaces_fork_arm_story_and_original_files(self) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn("arm.siblingExclusiveQuestIds", source)
        self.assertIn("arm.storyEvidence", source)
        self.assertIn("arm.authoredSourceEvidence", source)
        self.assertIn("arm.relatedOriginalFiles", source)
        self.assertIn('t("questForkArmCorridor")', source)
        self.assertIn('t("questForkArmStoryEvidence")', source)
        self.assertIn('t("questForkArmSourceEvidence")', source)
        self.assertIn("row.conditionTypes", source)
        self.assertIn("row.clientActionTypes", source)
        self.assertIn("row.trackingTypes", source)
        self.assertIn("They do not prove that the server selected the arm", source)

    def test_mission_pipeline_surfaces_static_port_and_detached_controls(self) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn("branches.dialogTreeStaticPortControls", source)
        self.assertIn("row.portContractStatus", source)
        self.assertIn("arm.outcomeLabel", source)
        self.assertIn("arm.runtimeProducerStatus", source)
        self.assertIn("arm.runtimeProducerEvidence", source)
        self.assertIn("arm.runtimeDynamicProducerEvidence", source)
        self.assertIn("row.runtimeDynamicProducerArmCount", source)
        self.assertIn("row.nativeMethods", source)
        self.assertIn('t("dialogTreeStaticPortExternal")', source)
        self.assertIn('t("dialogTreeStaticPortDynamicProducer")', source)
        self.assertIn("external-result control", source)
        self.assertIn('row.executionStatus === "detached_serialized_control"', source)
        self.assertIn('t("dialogTreeDetachedBoundary")', source)
        self.assertIn("which UI result occurred", source)

    def test_mission_pipeline_surfaces_shared_proxy_candidate_topology(self) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn("route.candidateQuestTopology", source)
        self.assertIn("trackedProxyCandidateTopologyHtml", source)
        self.assertIn("topology.topologyClass", source)
        self.assertIn("fork.sharedDownstreamCandidateQuestIds", source)
        self.assertIn("merge.predecessorQuestIds", source)
        self.assertIn("topology.relatedOriginalFiles", source)
        self.assertIn("activeCondIndex", source)
        self.assertIn('t("trackedProxyNoAssignment")', source)
        self.assertIn("missionTrackedProxyCandidateTopologyHtml", source)
        self.assertIn("context.configuredDialogIds", source)
        self.assertIn("storyCoverage?.trackedProxyCandidateTopology", source)

    def test_mission_pipeline_surfaces_exact_empty_levelscript_boundaries(self) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn("objective.levelScriptSources", source)
        self.assertIn('row.actionMapStatus === "exact_empty_action_map"', source)
        self.assertIn('t("levelScriptExactEmptyMap")', source)
        self.assertIn("row.serializedTailRecordCount", source)
        self.assertIn("row.relatedOriginalFiles", source)

    def test_mission_pipeline_surfaces_generic_binary_levelscript_controls(self) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn("row.nativeControlEvidence", source)
        self.assertIn("nativeLevelScriptControlAttachments", source)
        self.assertIn("control.serializedOutgoingEdges", source)
        self.assertIn("control.controlDetail", source)
        self.assertIn('t("levelScriptNativeControls")', source)
        self.assertIn("does not prove Story ownership", source)

    def test_mission_pipeline_surfaces_binary_proven_quest_success_order(self) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn('row.kind === "questSucceedLifecycle"', source)
        self.assertIn("row.objectiveStoryRelation", source)
        self.assertIn("row.succeedStoryRelation", source)
        self.assertIn("row.relatedOriginalFiles", source)
        self.assertIn('t("questSucceedLifecyclePath")', source)
        self.assertIn("does not prove that the quest succeeds", source)

    def test_mission_pipeline_exposes_undispatched_start_definitions(self) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn("order.questLifecycleDefinitions", source)
        self.assertIn("questStartActionDefinitionCount", source)
        self.assertIn("authored_definition_no_current_aot_dispatch", source)
        self.assertIn('t("questActionStartNoDispatch")', source)
        self.assertIn("row.relatedOriginalFiles", source)

    def test_mission_pipeline_names_binary_quest_semantic_fields(self) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn("?.questTopologyFieldConsumers?.questSemanticFields", source)
        self.assertIn("semanticFields.questType?.values", source)
        self.assertIn("semanticFields.showMode?.values", source)
        self.assertIn('t("questForkQuestType")', source)
        self.assertIn('t("questForkShowMode")', source)
        self.assertIn("postLifecycleConsumerCount", source)
        self.assertIn("blockNotificationConsumerCount", source)
        self.assertIn("semanticFields?.optionalObjectiveFlag", source)
        self.assertIn("structuredIdentityCarrierCensus", source)
        self.assertIn("structuredIdentityCensusCounts", source)
        self.assertIn("optionalObservation.optionalFieldWrite?.text", source)
        self.assertIn("post_lifecycle_block_notification", source)
        self.assertIn("They do not select a successor arm", source)

    def test_mission_pipeline_surfaces_binary_parallel_scheduler_authority(self) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn("contract.actionExtraThreadSchedulerAudit", source)
        self.assertIn("extraThreadExecuteMethods", source)
        self.assertIn("binary_proven_extra_thread_launch", source)
        self.assertIn("step.siblingOrderEvidence", source)
        self.assertIn('t("extraThreadScheduler")', source)
        self.assertIn('t("extraThreadSiblingBoundary")', source)
        self.assertIn("extraThreadScheduler.relatedOriginalFiles", source)

    def test_mission_pipeline_surfaces_generic_task_lifecycle_and_carriers(self) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn("levelScriptTaskLifecycleAudit", source)
        self.assertIn("serverStateApplicationChain", source)
        self.assertIn("processingConditionCallCount", source)
        self.assertIn("dialogFinishTaskDefinitionHtml", source)
        self.assertIn("definition.taskTypeName", source)
        self.assertIn("definition.conditionTypeCounts", source)
        self.assertIn("externalTaskIdentityCarriers", source)
        self.assertIn('t("dialogFinishTaskUncarried")', source)
        self.assertIn("levelScriptTaskExactCompleteMapConsumers", source)
        self.assertIn("levelScriptTaskExactBoundedFragmentConsumers", source)
        self.assertIn("levelScriptTaskCarrierActiveLogicalFiles", source)
        self.assertIn("levelScriptTaskCarrierTypedJsonFiles", source)
        self.assertIn("levelScriptTaskCarrierTypedJsonCandidates", source)
        self.assertIn("levelScriptTaskCarrierNonJsonFiles", source)
        self.assertIn('t("dialogFinishTaskCarrierScope")', source)
        self.assertIn("levelScriptTaskLevelDataProgressCarriers", source)
        self.assertIn("levelScriptTaskLevelDataUniqueMissionShellIdentities", source)
        self.assertIn("levelScriptTaskNpcProxyMatchedScripts", source)
        self.assertIn("levelScriptTaskNpcProxyUniqueMissionShellScripts", source)
        self.assertIn("npc_proxy_segment_script_mission_shell", source)
        self.assertIn("MissionRuntime NpcProxy + NpcProxyEx + registry segment", source)
        self.assertIn("dialogFinishAuthoredTaskShellDependenciesHtml", source)
        self.assertIn("state.mission?.dialogFinishAuthoredTaskShellDependencies", source)
        self.assertNotIn("recoveryCounts.levelScriptTaskSharedConsumerCompleteMaps", source)
        self.assertNotIn("recoveryCounts.levelScriptTaskSharedConsumerFragments", source)
        self.assertIn("does not identify a mission owner or Story-file order", source)

    def test_mission_pipeline_labels_declared_story_variant_aggregates(self) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn("mission.storyAggregateShell === true", source)
        self.assertIn("mission.variantMissionIds", source)
        self.assertIn("mission.relatedOriginalFiles", source)
        self.assertIn('t("storyAggregateVariants")', source)
        self.assertIn('t("storyAggregateOriginals")', source)
        self.assertIn("does not establish mission ownership", source)

    def test_mission_pipeline_shows_composed_npc_proxy_dialog_branches(self) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn("Auto-discovered DialogTree + native NPC-proxy consumer", source)
        self.assertIn("Auto-discovered from complete active MissionRuntime corpus", source)
        self.assertIn("row.missionNpcProxyTrackingContexts", source)
        self.assertIn("missionTracking.sourceSha256?.[sourceFile]", source)
        self.assertIn("row.optionRouteRecovery?.nodes", source)
        self.assertIn("route.connectionIndexSource", source)
        self.assertIn("...(row.consumerSourceFiles || [])", source)
        self.assertIn("${recoveredOptionRoutes}", source)

    def test_mission_pipeline_maps_exact_world_entity_event_positions(self) -> None:
        source = MISSION_PIPELINE.read_text(encoding="utf-8")
        self.assertIn("manifest[key]?.runtimeContextRecovery", source)
        self.assertIn("overlay[key]?.runtimeContextRecovery", source)
        self.assertIn("connection.producerEntities", source)
        self.assertIn(
            "exact_unique_world_entity_registry_script_slot",
            source,
        )
        self.assertIn("exact_world_entity_event_trigger", source)
        self.assertIn('t("spatialExactWorldEntityTrigger")', source)
