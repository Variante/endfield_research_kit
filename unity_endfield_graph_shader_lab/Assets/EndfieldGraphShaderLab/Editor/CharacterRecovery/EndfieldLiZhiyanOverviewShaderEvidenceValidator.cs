using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEngine;
using L = EndfieldGraphShaderLabEditor.EndfieldLastRiteOverviewHeadEffectImporter;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Validates exact material-to-DXBC evidence without admitting a visible shader.
    /// Live descriptor tables, PSO overrides, attachments, and draw ownership are
    /// deliberately outside this offline contract.
    /// </summary>
    public static class EndfieldLiZhiyanOverviewShaderEvidenceValidator
    {
        private const string ContractPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/ShaderEvidence/" +
            "LiZhiyanOverviewFinger/lizhiyan_overview_vfxbasev2_variants.json";
        private const string NativeContractPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/ShaderEvidence/" +
            "LiZhiyanOverviewFinger/lizhiyan_after_dof_native_abi.json";
        private const string RetailDrawObservationPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/ShaderEvidence/" +
            "LiZhiyanOverviewFinger/lizhiyan_retail_draw_observation.json";
        private const string RetailVisualOraclePath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/ShaderEvidence/" +
            "LiZhiyanOverviewFinger/lizhiyan_retail_visual_oracle.json";
        private const string TimingAlignmentPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/ShaderEvidence/" +
            "LiZhiyanOverviewFinger/lizhiyan_overview_timing_alignment.json";
        private const string Start01ContractPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/" +
            "lizhiyan_overview_start_01_effect.json";
        private const string Start01ResolvedAnimationPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/" +
            "A_fxui__lizhiyan_overview_start_01.anim";
        private const string StaticSiblingContractPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/" +
            "lizhiyan_overview_start_02_03_effects.json";
        private const string PlayableTopologyContractPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/ShaderEvidence/" +
            "LiZhiyanOverviewFinger/lizhiyan_effect_animation_playable_topology.json";
        private const string Schema = "endfield.lizhiyan-overview-vfxbasev2-variants.v1";
        private const long ShaderPathId = -1430105248647086886L;

        [MenuItem("Endfield/Character Recovery Lab/Validate Li Zhiyan Overview Shader Evidence")]
        public static void ValidateMenu()
        {
            Dictionary<string, object> effect = L.Dict(
                ManifestMiniJson.Deserialize(File.ReadAllText(
                    L.ProjectAbsolute(
                        "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/" +
                        "lizhiyan_overview_finger_effect.json"), Encoding.UTF8)));
            Validate(effect);
            Debug.Log("Li Zhiyan shader evidence validated: 6 materials, 3 exact DXBC pairs, visible admission=false.");
        }

        public static void Validate(Dictionary<string, object> effect)
        {
            Dictionary<string, object> contract = L.Dict(
                ManifestMiniJson.Deserialize(File.ReadAllText(
                    L.ProjectAbsolute(ContractPath), Encoding.UTF8)));
            L.Require(L.Str(contract, "schema") == Schema &&
                L.Str(contract, "status") ==
                    "material_to_compiled_variant_closed_live_draw_and_descriptor_table_pending",
                "Li Zhiyan shader-evidence identity drifted");
            Dictionary<string, object> shader = L.Dict(contract["shader"]);
            L.Require(L.Str(shader, "name") == "HGRP/Effect/VFXBaseV2" &&
                L.Long(shader, "pathID") == ShaderPathId &&
                L.Str(shader, "pass") == "ForwardOnly" &&
                L.Long(shader, "gpuProgramID") == 59433,
                "Li Zhiyan shader identity drifted");
            Dictionary<string, object> summary = L.Dict(contract["summary"]);
            L.Require(L.Long(summary, "materials") == 6 &&
                L.Long(summary, "compiledKeywordSignatures") == 1360 &&
                L.Long(summary, "materialKeywordSignatures") == 3 &&
                L.Long(summary, "exactNonInstancedDxbcPairs") == 3 &&
                L.Long(summary, "verifiedInstancedDxbcPairs") == 3,
                "Li Zhiyan compiled-shader census drifted");
            Dictionary<string, object> scheduling = L.Dict(contract["renderScheduling"]);
            Dictionary<string, object> queueRange = L.Dict(scheduling["queueRange"]);
            Dictionary<string, object> attachments = L.Dict(scheduling["attachments"]);
            L.Require(L.Long(scheduling, "materialQueue") == 3700 &&
                L.Long(queueRange, "first") == 3660 &&
                L.Long(queueRange, "last") == 3740 &&
                L.Str(scheduling, "pass") == "ForwardOnly in Forward Transparent After DOF" &&
                L.Str(attachments, "color0") == "new sceneColor clone, store" &&
                L.Str(attachments, "color1") == "incoming sceneMV when valid, load/store" &&
                L.Str(attachments, "depth") == "incoming sceneDepth, read" &&
                L.List(scheduling["sourceArtifacts"]).Count == 3,
                "Li Zhiyan after-DOF scheduling contract drifted");

            Dictionary<string, object> selectedGates =
                L.Dict(contract["selectedMaterialGates"]);
            Dictionary<string, object> selectedGateValues =
                L.Dict(selectedGates["values"]);
            L.Require(!L.Bool(selectedGates, "vfxParams1Required") &&
                !L.Bool(selectedGates, "transformHistoryRequired") &&
                L.Float(selectedGateValues, "_RenderTransparentAfterDOF") == 1.0f &&
                L.Float(selectedGateValues, "_EnableTransparentMV") == 0.0f &&
                L.Float(selectedGateValues, "_IsSceneEffect") == 0.0f,
                "Li Zhiyan selected-material global/history gate drifted");

            var expectedMaterials = L.List(effect["materials"]).Cast<object>()
                .Select(L.Dict).ToDictionary(
                    row => L.Str(row, "name"),
                    row => new
                    {
                        PathId = L.Long(row, "pathID"),
                        Signature = Signature(L.List(row["validKeywords"]) .Cast<object>()
                            .Select(value => Convert.ToString(value))),
                        Floats = L.Dict(L.Dict(L.Dict(row["payload"])["m_SavedProperties"])["m_Floats"])
                    });
            L.Require(expectedMaterials.Count == 6, "Li Zhiyan source material census drifted");
            foreach (var expected in expectedMaterials.Values)
            {
                L.Require(L.Float(expected.Floats, "_RenderTransparentAfterDOF") == 1.0f &&
                    L.Float(expected.Floats, "_EnableTransparentMV") == 0.0f &&
                    L.Float(expected.Floats, "_IsSceneEffect") == 0.0f &&
                    L.Float(expected.Floats, "_IgnorePostExposure") == 1.0f &&
                    L.Float(expected.Floats, "_Responsive") == 1.0f &&
                    L.Float(expected.Floats, "_InParticle") == 1.0f,
                    "Li Zhiyan selected material escaped the fail-closed global/history gate");
            }

            var seen = new HashSet<string>(StringComparer.Ordinal);
            IList variants = L.List(contract["variants"]);
            L.Require(variants.Count == 3, "Li Zhiyan compiled-variant census drifted");
            foreach (object item in variants)
            {
                Dictionary<string, object> variant = L.Dict(item);
                string signature = Signature(L.List(variant["materialKeywords"]).Cast<object>()
                    .Select(value => Convert.ToString(value)));
                IList runtimeKeywords = L.List(variant["nonInstancedCompiledKeywords"]);
                L.Require(runtimeKeywords.Cast<object>().Any(value =>
                    Convert.ToString(value) == "HG_ENABLE_MV"),
                    "Li Zhiyan runtime variant lost HG_ENABLE_MV");
                foreach (object materialItem in L.List(variant["materials"]))
                {
                    Dictionary<string, object> material = L.Dict(materialItem);
                    string name = L.Str(material, "name");
                    L.Require(expectedMaterials.TryGetValue(name, out var expected) &&
                        expected.PathId == L.Long(material, "pathID") &&
                        expected.Signature == signature && seen.Add(name),
                        "Li Zhiyan material-to-DXBC mapping drifted: " + name);
                }
                Dictionary<string, object> stages = L.Dict(variant["stages"]);
                ValidateStage(L.Dict(stages["vertex"]), "vertex", false, signature);
                ValidateStage(L.Dict(stages["fragment"]), "fragment", true, signature);
            }
            L.Require(seen.SetEquals(expectedMaterials.Keys),
                "Li Zhiyan shader evidence does not cover all six materials");
            ValidateNativeAbi();
            ValidateRetailDrawObservation();
            ValidateRetailVisualOracle();
            ValidateOverviewTimingAlignment();
            ValidateOverviewStart01Contract();
            ValidateOverviewStaticSiblingContracts();
            ValidateEffectAnimationPlayableTopology();
        }

        private static void ValidateEffectAnimationPlayableTopology()
        {
            Dictionary<string, object> contract = L.Dict(
                ManifestMiniJson.Deserialize(File.ReadAllText(
                    L.ProjectAbsolute(PlayableTopologyContractPath), Encoding.UTF8)));
            Dictionary<string, object> sources = L.Dict(contract["sources"]);
            foreach (object value in sources.Values)
                ValidateRepositoryArtifact(L.Dict(value));
            Dictionary<string, object> topology =
                L.Dict(contract["retailEffectAnimationTopology"]);
            Dictionary<string, object> create = L.Dict(topology["createPlayableGraph"]);
            Dictionary<string, object> mixer = L.Dict(topology["mixer"]);
            Dictionary<string, object> mixerComparison =
                L.Dict(mixer["stockAnimationMixerComparison"]);
            Dictionary<string, object> stateMachine =
                L.Dict(topology["playAnimationStateMachine"]);
            Dictionary<string, object> startOnly =
                L.Dict(topology["liZhiyanStartOnlyEffectiveRoute"]);
            Dictionary<string, object> advancedApplicability =
                L.Dict(topology["liZhiyanAdvancedApplicability"]);
            Dictionary<string, object> controlAbi =
                L.Dict(contract["effectAnimationControlAbi"]);
            Dictionary<string, object> controlMethods = L.Dict(controlAbi["methods"]);
            Dictionary<string, object> installedPatch =
                L.Dict(controlAbi["installedPatchState"]);
            Dictionary<string, object> manualEvaluate =
                L.Dict(controlMethods["ManualEvaluate"]);
            Dictionary<string, object> syncProgress =
                L.Dict(controlMethods["SyncProgress"]);
            Dictionary<string, object> setManual = L.Dict(controlMethods["SetManual"]);
            Dictionary<string, object> instanceRoutes =
                L.Dict(controlAbi["effectInstanceCallerRoutes"]);
            Dictionary<string, object> manualUpdate =
                L.Dict(instanceRoutes["ManualUpdateAnimation"]);
            Dictionary<string, object> lab = L.Dict(contract["labBoundary"]);
            Dictionary<string, object> behavioralSimulation =
                L.Dict(lab["behavioralSimulation"]);
            Dictionary<string, object> nativeMixer =
                L.Dict(contract["retailAdvancedMixerNative"]);
            Dictionary<string, object> handleLayout = L.Dict(nativeMixer["handleLayout"]);
            Dictionary<string, object> sharedInputs =
                L.Dict(nativeMixer["sharedInputOperations"]);
            Dictionary<string, object> mixerInitializers =
                L.Dict(nativeMixer["initializers"]);
            Dictionary<string, object> advancedSlots =
                L.Dict(nativeMixer["advancedOnlyStateSlots"]);
            Dictionary<string, object> advancedStateFields =
                L.Dict(advancedSlots["stateFields"]);
            Dictionary<string, object> advancedSlot3 = L.Dict(advancedSlots["slot3"]);
            Dictionary<string, object> runtimeCallbacks =
                L.Dict(advancedSlots["runtimeCallbacks"]);
            Dictionary<string, object> runtimeUpdate =
                L.Dict(runtimeCallbacks["update"]);
            Dictionary<string, object> lodOwnership =
                L.Dict(contract["effectLodRendererOwnership"]);
            Dictionary<string, object> lodField = L.Dict(lodOwnership["managedField"]);
            Dictionary<string, object> ordinaryRenderer =
                L.Dict(lodOwnership["ordinaryRendererNativeIdentity"]);
            Dictionary<string, object> ordinaryResourceRoute =
                L.Dict(ordinaryRenderer["persistentResourceRoute"]);
            Dictionary<string, object> hgRenderer =
                L.Dict(lodOwnership["hgMeshRendererComparison"]);
            IList lodBindings = L.List(lodOwnership["serializedBindings"]);
            Type retailMixer = Type.GetType(
                "UnityEngine.Animations.AdvancedAnimationMixerPlayable, UnityEngine.AnimationModule",
                false);
            L.Require(
                L.Str(contract, "schema") ==
                    "endfield.lizhiyan-effect-animation-playable-topology.v1" &&
                L.Str(contract, "status") ==
                    "retail_topology_and_installed_fallback_closed_editor_advanced_mixer_unavailable_visible_fail_closed" &&
                !L.Bool(contract, "visibleAdmission") &&
                L.Str(topology, "updateMode") == "GameTime" &&
                Mathf.Abs(L.Float(topology, "timeScale") - 1.0f) < 0.000001f &&
                !L.Bool(topology, "manualEvaluation") &&
                L.Str(create, "token") == "0x060059D0" &&
                L.Str(create, "va") == "0x183437F90" &&
                L.Str(mixer, "type") ==
                    "UnityEngine.Animations.AdvancedAnimationMixerPlayable" &&
                L.Str(mixer, "typeToken") == "0x02000053" &&
                L.Long(mixer, "inputCount") == 3 &&
                !L.Bool(mixerComparison, "behavioralEquivalenceProven") &&
                L.Bool(mixerComparison, "stockCreateHasNormalizeWeightsParameter") &&
                !L.Bool(mixerComparison, "advancedCreateHasNormalizeWeightsParameter") &&
                L.List(mixer["unresolvedSemantics"]).Count == 3 &&
                L.Long(nativeMixer, "tableIndex") == 501 &&
                L.Str(nativeMixer, "nativeTargetVA") == "0x180158B30" &&
                L.Str(nativeMixer, "advancedNodeTypeId") == "0x178" &&
                L.Str(nativeMixer, "stockNodeTypeId") == "0x170" &&
                L.Long(handleLayout, "meaningfulBytes") == 12 &&
                L.Bool(sharedInputs, "advancedAndStockShareVirtualTargets") &&
                L.Long(sharedInputs, "slotStrideBytes") == 16 &&
                L.Str(sharedInputs, "defaultPlayable") == "null" &&
                Mathf.Abs(L.Float(sharedInputs, "defaultWeight")) < 0.000001f &&
                !L.Bool(sharedInputs, "automaticNormalization") &&
                L.Str(mixerInitializers, "advancedExtraWordValue") == "0x0101" &&
                L.Str(advancedSlot3, "va") == "0x180AD5230" &&
                L.Str(advancedSlot3, "firstHandshakeVA") == "0x180A5A680" &&
                L.Str(advancedSlot3, "subsequentRuntimeVA") == "0x180A634D0" &&
                L.Long(L.Dict(advancedStateFields["state170"]), "initialValue") == 1 &&
                L.Long(L.Dict(advancedStateFields["state171"]), "initialValue") == 1 &&
                L.Str(L.Dict(runtimeCallbacks["reset"]), "va") == "0x180A5A680" &&
                L.Str(runtimeUpdate, "stageProcessorVA") == "0x180AC4A90" &&
                L.Long(runtimeUpdate, "stageRecordStrideBytes") == 28 &&
                !L.Bool(runtimeCallbacks, "publicPlayableApiEquivalent") &&
                L.Bool(advancedSlots, "stockImplementationsDiffer") &&
                !L.Bool(advancedSlots, "restrictedStartOnlyStockEquivalenceProven") &&
                L.Str(advancedSlots, "classification") ==
                    "advanced_runtime_state_gate_not_reproducible_with_stock_mixer" &&
                L.Str(nativeMixer, "classification") ==
                    "native_create_and_shared_input_semantics_closed_advanced_slots_pending" &&
                L.List(topology["clipSlots"]).Count == 3 &&
                L.List(stateMachine["operations"]).Count == 5 &&
                L.Str(stateMachine, "weightMode") == "one_hot_no_cross_fade" &&
                Mathf.Abs(L.Float(stateMachine, "validClipTimeResetSeconds")) < 0.000001f &&
                L.List(startOnly["connectedInputs"]).Count == 1 &&
                L.List(startOnly["weightsOnStart"]).Count == 3 &&
                Mathf.Abs(Convert.ToSingle(L.List(startOnly["weightsOnStart"])[0]) - 1.0f) < 0.000001f &&
                !L.Bool(startOnly, "crossFade") &&
                L.Str(startOnly, "classification") == "retail_start_only_graph_control_closed" &&
                L.Str(advancedApplicability, "advancedMixerCreation") == "proven_applicable" &&
                L.Str(advancedApplicability, "customStageTimelineLiActivation") ==
                    "not_proven_fail_closed" &&
                L.Str(advancedApplicability, "serializedStageProducer") ==
                    "not_found_in_start01_start02_start03_effect_roots" &&
                !L.Bool(advancedApplicability, "visibleAdmission") &&
                L.Str(manualEvaluate, "token") == "0x060059D2" &&
                L.Str(manualEvaluate, "va") == "0x187431CB0" &&
                L.List(manualEvaluate["parameters"]).Count == 1 &&
                L.Str(syncProgress, "token") == "0x060059D3" &&
                L.List(syncProgress["parameters"]).Count == 1 &&
                L.List(setManual["ifFixDispatchIds"]).Count == 1 &&
                L.Str(manualUpdate, "token") == "0x06005ADC" &&
                L.Dict(manualUpdate["calls"]).Count == 1 &&
                L.List(controlAbi["fallbackBodyFacts"]).Count == 7 &&
                L.Long(installedPatch, "patchBytes") == 86926 &&
                L.Long(installedPatch, "targetCount") == 32 &&
                L.List(installedPatch["matchingTargets"]).Count == 0 &&
                L.Str(installedPatch, "classification") ==
                    "current_installed_persistent_patch_does_not_replace_effect_animation_chain" &&
                L.Str(controlAbi, "effectiveBodyForInstalledSnapshot") ==
                    "decoded_il2cpp_fallback_body" &&
                L.Str(controlAbi, "liZhiyanCallerStatus") ==
                    "no_asset_specific_caller_proven_for_optional_time_controls" &&
                L.Str(lodField, "fieldToken") == "0x04004F24" &&
                L.Str(lodField, "fieldType") == "UnityEngine.Renderer" &&
                lodBindings.Count == 3 &&
                L.List(L.Dict(lodBindings[0])["rendererPathIDs"]).Count == 4 &&
                L.List(L.Dict(lodBindings[1])["rendererPathIDs"]).Count == 3 &&
                L.List(L.Dict(lodBindings[2])["rendererPathIDs"]).Count == 3 &&
                L.Str(lodOwnership, "nativeJoinStatus") ==
                    "managed_renderer_to_hgtree_survivor_record_unresolved_fail_closed" &&
                L.Long(ordinaryRenderer, "tableIndex") == 1278 &&
                L.Str(ordinaryRenderer, "nativeTargetVA") == "0x1800E6C40" &&
                L.Str(ordinaryRenderer, "nativeEntityIdOffset") == "0x268" &&
                L.Long(ordinaryRenderer, "directManagedCallersInGameAssemblyText") == 0 &&
                L.Str(ordinaryRenderer, "consumerClassification") ==
                    "no_static_managed_consumer_or_hgtree_join" &&
                L.Str(ordinaryResourceRoute, "rendererCache") ==
                    "native_renderer+0x140+index*0x10" &&
                L.Str(ordinaryResourceRoute, "componentKeyOffset") == "0x268" &&
                L.Str(ordinaryResourceRoute, "componentValidityOffset") == "0x26C" &&
                L.Str(ordinaryResourceRoute, "resolverVA") == "0x1804255F0" &&
                L.Str(ordinaryResourceRoute, "resourceDestination") ==
                    "resolved_resource+0xB0+index*0x10" &&
                L.Long(ordinaryResourceRoute, "characterParamsIndex") == 2 &&
                L.Str(ordinaryResourceRoute, "characterParamsRendererOffset") == "0x160" &&
                L.Str(ordinaryResourceRoute, "characterParamsResourceOffset") == "0xD0" &&
                !L.Bool(ordinaryResourceRoute, "hgtreeContextArrayEquivalent") &&
                !L.Bool(ordinaryResourceRoute, "resourceToDescriptorUploadProven") &&
                L.Str(hgRenderer, "nativeEntityOffset") == "0x50" &&
                !L.Bool(hgRenderer, "ordinaryRendererEquivalent") &&
                retailMixer == null &&
                typeof(UnityEngine.Animations.AnimationMixerPlayable) != null &&
                !L.Bool(lab, "retailAdvancedMixerTypeExpectedInEditor") &&
                !L.Bool(lab, "standardAnimationMixerPlayableIsExactSubstitute") &&
                L.Str(lab, "driverStatus") ==
                    "exact_retail_mixer_type_unavailable_do_not_start_graph" &&
                L.Str(behavioralSimulation, "mode") == "behavioral_simulation" &&
                L.Str(behavioralSimulation, "backend") ==
                    "stock AnimationMixerPlayable" &&
                !L.Bool(behavioralSimulation, "retailAbiEquivalent") &&
                !L.Bool(behavioralSimulation, "nativeRendererMappingClaimed") &&
                !L.Bool(behavioralSimulation, "visibleAdmission") &&
                L.List(lab["blockedBy"]).Count == 4 &&
                L.List(contract["nonClaims"]).Count == 3,
                "Li Zhiyan retail EffectAnimation playable topology drifted");
        }

        private static void ValidateOverviewStaticSiblingContracts()
        {
            Dictionary<string, object> contract = L.Dict(
                ManifestMiniJson.Deserialize(File.ReadAllText(
                    L.ProjectAbsolute(StaticSiblingContractPath), Encoding.UTF8)));
            Dictionary<string, object> summary = L.Dict(contract["summary"]);
            Dictionary<string, object> sharedAnimation = L.Dict(contract["sharedAnimation"]);
            ValidateArtifact(L.Dict(sharedAnimation["resolvedUnityAnim"]));
            var effects = L.List(contract["effects"]).Cast<object>().Select(L.Dict)
                .ToDictionary(row => L.Str(row, "effectName"), StringComparer.Ordinal);
            L.Require(
                L.Str(contract, "schema") ==
                    "endfield.lizhiyan-overview-static-sibling-effects.v1" &&
                L.Str(contract, "status") ==
                    "start02_start03_serialized_sources_closed_visible_fail_closed" &&
                L.Long(summary, "effects") == 2 &&
                L.Long(summary, "staticMeshNodes") == 6 &&
                L.Long(summary, "uniqueTextureReferences") == 8 &&
                L.Str(summary, "sourceAggregateSha256") ==
                    "AB587FDA1E0AEC1761A10F334959541FA0217347E595D18415850791AE33545B" &&
                L.Long(sharedAnimation, "pathID") == 7360398354216100382L &&
                L.Str(sharedAnimation, "bindingStatus") ==
                    "all_hashes_resolved_shared_start01_start02_start03_clip" &&
                L.List(contract["textureDependencies"]).Count == 8 &&
                effects.Count == 2,
                "Li Zhiyan start_02/_03 contract identity drifted");
            ValidateStaticSiblingEffect(
                effects["P_fxui_lizhiyan_overview_start_02"],
                5.0f,
                new long[] { 7032717393607757449L },
                new long[] { -481371258366057841L, 2540816063756981481L,
                    -2434886401441015548L });
            ValidateStaticSiblingEffect(
                effects["P_fxui_lizhiyan_overview_start_03"],
                7.0f,
                new long[] { -4003364140602261775L, 3893791131891476371L },
                new long[] { -7438264461631060117L, 9120706159938786131L,
                    -6772801081383272744L });
        }

        private static void ValidateStaticSiblingEffect(
            Dictionary<string, object> effect,
            float expectedDuration,
            IEnumerable<long> expectedMeshes,
            IEnumerable<long> expectedMaterials)
        {
            Dictionary<string, object> summary = L.Dict(effect["summary"]);
            Dictionary<string, object> timing =
                L.Dict(L.Dict(effect["effectSetting"])["timing"]);
            Dictionary<string, object> animation = L.Dict(effect["animation"]);
            Dictionary<string, object> startClip = L.Dict(animation["startAnimationClip"]);
            Dictionary<string, object> execution = L.Dict(effect["executionBoundary"]);
            var meshIds = new HashSet<long>(L.List(effect["meshDependencies"])
                .Cast<object>().Select(row => L.Long(L.Dict(row), "pathID")));
            var materialIds = new HashSet<long>(L.List(effect["materials"])
                .Cast<object>().Select(row => L.Long(L.Dict(row), "pathID")));
            L.Require(
                L.Str(effect, "mountPoint") == string.Empty &&
                L.Long(summary, "hierarchyNodes") == 4 &&
                L.Long(summary, "staticMeshNodes") == 3 &&
                L.Long(summary, "particleSystems") == 0 &&
                L.Long(summary, "materials") == 3 &&
                Mathf.Abs(L.Float(timing, "duration") - expectedDuration) < 0.000001f &&
                Mathf.Abs(L.Float(timing, "delay")) < 0.000001f &&
                L.Long(startClip, "pathID") == 7360398354216100382L &&
                meshIds.SetEquals(expectedMeshes) && materialIds.SetEquals(expectedMaterials) &&
                L.Str(execution, "bindingKind") == "static_mesh_animated" &&
                !L.Bool(execution, "sourcePayloadApplied") &&
                !L.Bool(execution, "sourceAnimationPayloadApplied") &&
                L.Bool(execution, "rendererFailClosedForUnrecoveredShader") &&
                !L.Bool(execution, "visibleAdmission") &&
                L.List(execution["blockedBy"]).Count == 4,
                "Li Zhiyan static sibling effect drifted: " +
                    L.Str(effect, "effectName"));
        }

        private static void ValidateOverviewStart01Contract()
        {
            Dictionary<string, object> contract = L.Dict(
                ManifestMiniJson.Deserialize(File.ReadAllText(
                    L.ProjectAbsolute(Start01ContractPath), Encoding.UTF8)));
            Dictionary<string, object> summary = L.Dict(contract["summary"]);
            Dictionary<string, object> timing =
                L.Dict(L.Dict(contract["effectSetting"])["timing"]);
            Dictionary<string, object> animation = L.Dict(contract["animation"]);
            Dictionary<string, object> startClip = L.Dict(animation["startAnimationClip"]);
            Dictionary<string, object> curveBindings =
                L.Dict(startClip["floatCurveBindings"]);
            Dictionary<string, object> mesh = L.Dict(contract["meshDependency"]);
            Dictionary<string, object> execution = L.Dict(contract["executionBoundary"]);
            IList nodes = L.List(contract["staticMeshNodes"]);
            ValidateArtifact(L.Dict(startClip["resolvedUnityAnim"]));
            AnimationClip resolvedClip =
                AssetDatabase.LoadAssetAtPath<AnimationClip>(Start01ResolvedAnimationPath);
            EditorCurveBinding[] importedBindings = resolvedClip == null
                ? Array.Empty<EditorCurveBinding>()
                : AnimationUtility.GetCurveBindings(resolvedClip);
            var importedPaths = new HashSet<string>(
                importedBindings.Select(value => value.path), StringComparer.Ordinal);
            var importedProperties = new HashSet<string>(
                importedBindings.Select(value => value.propertyName), StringComparer.Ordinal);
            var expectedPaths = new HashSet<string>(new[] {
                "S_fx_shoutiaodai_01", "S_fx_lzy_fenweiqiliu_02",
                "S_fx_lzy_tiaodaifenwei_01 (4)", "S_fx_shoutiaodai_01 (1)",
                "S_fx_lzy_tiaodaifenwei_01 (5)", "S_fx_lzy_tiaodaifenwei_01 (7)",
                "S_fx_lzy_tiaodaifenwei_01 (6)", "S_fx_lzy_fenweiqiliu_02 (1)",
                "S_fx_tuoweidisan_01", "S_fx_lzy_fenweiqiliu_02 (3)" },
                StringComparer.Ordinal);
            var expectedProperties = new HashSet<string>(new[] {
                "material._MainTex_ST.x", "material._MainTex_ST.y",
                "material._MainTex_ST.z", "material._MainTex_ST.w",
                "material._DisturbUIntensity1", "material._TintColorAlpha",
                "material._DissolveScheduleOffset" }, StringComparer.Ordinal);
            var materialIds = new HashSet<long>();
            foreach (object item in nodes)
            {
                Dictionary<string, object> node = L.Dict(item);
                IList materials = L.List(node["materials"]);
                L.Require(materials.Count == 1 &&
                    L.Long(L.Dict(node["mesh"]), "pathID") == -6840663686705882004L,
                    "Li Zhiyan start_01 static node dependency drifted");
                materialIds.Add(L.Long(L.Dict(materials[0]), "pathID"));
            }
            L.Require(
                L.Str(contract, "schema") == "endfield.lizhiyan-overview-start01-effect.v1" &&
                L.Str(contract, "status") ==
                    "static_mesh_animation_and_texture_sources_closed_visible_fail_closed" &&
                L.Str(contract, "effectName") == "P_fxui_lizhiyan_overview_start_01" &&
                L.Str(contract, "mountPoint") == string.Empty &&
                L.Long(summary, "hierarchyNodes") == 5 &&
                L.Long(summary, "staticMeshNodes") == 4 &&
                L.Long(summary, "particleSystems") == 0 &&
                L.Long(summary, "materials") == 3 &&
                L.Long(summary, "uniqueTextureReferences") == 8 &&
                L.Str(summary, "sourceAggregateSha256") ==
                    "5B83D031736E9CE864F1D2BE021C0E1A04BCA29D11291A506AD9740ADC047511" &&
                Mathf.Abs(L.Float(timing, "duration") - 2.2f) < 0.000001f &&
                Mathf.Abs(L.Float(timing, "delay")) < 0.000001f &&
                L.Long(startClip, "fileID") == 3 &&
                L.Long(startClip, "pathID") == 7360398354216100382L &&
                L.Str(startClip, "status") == "converted_source_payload_closed" &&
                L.Str(startClip, "name") == "A_fxui__lizhiyan_overview_start_01" &&
                Mathf.Abs(L.Float(startClip, "sampleRate") - 30.0f) < 0.000001f &&
                Mathf.Abs(L.Float(startClip, "stopTime") - 6.366667f) < 0.000001f &&
                L.List(startClip["events"]).Count == 0 &&
                L.Long(curveBindings, "count") == 53 &&
                L.Long(curveBindings, "targetClassID") == 23 &&
                L.List(curveBindings["targetPathHashes"]).Count == 10 &&
                L.List(curveBindings["materialPropertyHashes"]).Count == 7 &&
                L.Long(curveBindings, "currentEffectTargetPaths") == 4 &&
                L.Long(curveBindings, "siblingEffectTargetPaths") == 6 &&
                L.Str(curveBindings, "status") ==
                    "all_hashes_resolved_shared_start01_start02_start03_clip" &&
                importedBindings.Length == 53 &&
                importedBindings.All(value => value.type == typeof(MeshRenderer)) &&
                importedPaths.SetEquals(expectedPaths) &&
                importedProperties.SetEquals(expectedProperties) &&
                L.List(contract["textureDependencies"]).Count == 8 &&
                L.Long(mesh, "pathID") == -6840663686705882004L &&
                materialIds.SetEquals(new long[] {
                    -6912999194325832649L, 2993445828574428557L, 3282333668994552481L }) &&
                L.Str(execution, "bindingKind") == "static_mesh_animated" &&
                !L.Bool(execution, "sourcePayloadApplied") &&
                !L.Bool(execution, "sourceAnimationPayloadApplied") &&
                L.Bool(execution, "rendererFailClosedForUnrecoveredShader") &&
                !L.Bool(execution, "visibleAdmission") &&
                L.List(execution["blockedBy"]).Count == 4,
                "Li Zhiyan start_01 static-mesh fail-closed contract drifted");
        }

        private static void ValidateOverviewTimingAlignment()
        {
            Dictionary<string, object> alignment = L.Dict(
                ManifestMiniJson.Deserialize(File.ReadAllText(
                    L.ProjectAbsolute(TimingAlignmentPath), Encoding.UTF8)));
            Dictionary<string, object> controller =
                L.Dict(alignment["sourceClosedControllerTiming"]);
            Dictionary<string, object> effect =
                L.Dict(alignment["sourceClosedEffectLocalTiming"]);
            Dictionary<string, object> compatibility =
                L.Dict(alignment["labCompatibilityChronology"]);
            Dictionary<string, object> staticChronology =
                L.Dict(alignment["sourceClosedStaticEffectMaterialChronology"]);
            Dictionary<string, object> staticLifetimes =
                L.Dict(staticChronology["effectLifetimesSeconds"]);
            var staticWindows = L.List(staticChronology["targetWindows"])
                .Cast<object>().Select(L.Dict)
                .ToDictionary(row => L.Str(row, "targetPath"), StringComparer.Ordinal);
            Dictionary<string, object> retail = L.Dict(alignment["retailVisualAlignment"]);
            IList mapped = L.List(retail["mappedSamples"]);
            L.Require(
                L.Str(alignment, "schema") == "endfield.lizhiyan-overview-timing-alignment.v1" &&
                L.Str(alignment, "status") ==
                    "source_timing_closed_retail_request_epoch_pending" &&
                !L.Bool(alignment, "visibleAdmission") &&
                L.Str(controller, "startClip") == "A_actor_lizhiyan_ui_overview_start_01" &&
                Mathf.Abs(L.Float(controller, "startClipLengthSeconds") - 10.7f) < 0.000001f &&
                L.List(controller["animationEvents"]).Count == 0 &&
                Mathf.Abs(L.Float(controller, "entryClipLocalSeconds") - 0.062452073f) < 0.000001f &&
                Mathf.Abs(L.Float(controller, "exitClipLocalSeconds") - 10.68547903f) < 0.000001f &&
                Mathf.Abs(L.Float(controller, "transitionDurationSeconds") - 0.014519697f) < 0.000001f &&
                L.Str(effect, "effect") ==
                    "P_fxui_lizhiyan_overview_trails_Bip001_R_Finger2Nub" &&
                L.Str(effect, "mount") == "Bip001_R_Finger2Nub" &&
                Mathf.Abs(L.Float(effect, "delaySeconds") - 0.83333f) < 0.000001f &&
                Mathf.Abs(L.Float(effect, "durationSeconds") - 2.33333f) < 0.000001f &&
                L.Str(compatibility, "evidenceClass") ==
                    "current_lab_policy_not_original_request_chronology" &&
                Mathf.Abs(L.Float(compatibility, "effectCreateClipLocalSeconds") - 0.895782073f) < 0.000001f &&
                Mathf.Abs(L.Float(compatibility, "effectDestroyClipLocalSeconds") - 3.229112073f) < 0.000001f &&
                L.Str(staticChronology, "sharedClip") ==
                    "A_fxui__lizhiyan_overview_start_01" &&
                L.Long(staticChronology, "curveCount") == 53 &&
                Mathf.Abs(L.Float(staticLifetimes,
                    "P_fxui_lizhiyan_overview_start_01") - 2.2f) < 0.000001f &&
                Mathf.Abs(L.Float(staticLifetimes,
                    "P_fxui_lizhiyan_overview_start_02") - 5.0f) < 0.000001f &&
                Mathf.Abs(L.Float(staticLifetimes,
                    "P_fxui_lizhiyan_overview_start_03") - 7.0f) < 0.000001f &&
                staticWindows.Count == 10 &&
                Convert.ToInt64(L.List(staticWindows[
                    "S_fx_lzy_tiaodaifenwei_01 (7)"]["candidateDynamicWindowPts"])[0]) == 38167 &&
                Convert.ToInt64(L.List(staticWindows[
                    "S_fx_lzy_fenweiqiliu_02 (3)"]["candidateDynamicWindowPts"])[0]) == 40834 &&
                Convert.ToInt64(L.List(staticWindows[
                    "S_fx_tuoweidisan_01"]["candidateDynamicWindowPts"])[0]) == 42467 &&
                !L.Bool(staticChronology, "visibleAdmission") &&
                L.Str(retail, "evidenceClass") == "candidate_only" &&
                L.Long(retail, "candidateRestartPts") == 37967 &&
                L.Str(retail, "diagnosticMismatch").Contains("PTS 42000") &&
                mapped.Count == 6 &&
                L.Str(L.Dict(mapped[1]), "compatibilityFingerEffectWindow") == "active" &&
                L.Str(L.Dict(mapped[2]), "compatibilityFingerEffectWindow") == "inactive" &&
                L.List(alignment["remainingEvidence"]).Count == 4 &&
                L.List(alignment["nonClaims"]).Count == 3,
                "Li Zhiyan Overview source/video timing alignment drifted");
        }

        private static void ValidateRetailVisualOracle()
        {
            Dictionary<string, object> oracle = L.Dict(
                ManifestMiniJson.Deserialize(File.ReadAllText(
                    L.ProjectAbsolute(RetailVisualOraclePath), Encoding.UTF8)));
            Dictionary<string, object> source = L.Dict(oracle["source"]);
            Dictionary<string, object> decode = L.Dict(oracle["decode"]);
            Dictionary<string, object> transition = L.Dict(oracle["transitionBoundary"]);
            IList anchors = L.List(oracle["transitionAnchors"]);
            IList samples = L.List(oracle["samples"]);
            long[] expectedPts = { 38000, 40000, 42000, 43000, 44000, 46000 };
            string[] expectedHashes =
            {
                "C17C726C803E335013E9FFFAD596F6A1B4F76D47DA528F78F5860F7008530BEC",
                "8880B3DA3072178F599B5111A533F2F0C55862867E56FFADFB7285E1444E2AD5",
                "F4B3ABD86689977F0A4DBE7700E9B0BD8E03B674FD5699473933D6A7BF226DB4",
                "7C9E40EC2AE58A15CD9C127CFF2AA1AAFCB581BC6189E220662C81B0252BCC71",
                "4773EAD0EB3B40EA358C0B1AA00763107DEB6DACAF9DA4A44F1325C7B862CA1D",
                "993A496929A7D819DDDE16337DB140DA0926829007FDE51D769CE9F7A6B05161",
            };
            L.Require(
                L.Str(oracle, "schema") == "endfield.lizhiyan-retail-visual-oracle.v1" &&
                L.Str(oracle, "status") == "diagnostic_only" &&
                !L.Bool(oracle, "visibleAdmission") &&
                L.Long(source, "bytes") == 1678613397L &&
                L.Str(source, "sha256") ==
                    "2F542A3BE7CE3332295D3A841FD8613C62707E084F9E33A0F156DA8A06EBF5E7" &&
                L.Str(source, "timeBase") == "1/1000" &&
                L.Str(decode, "pixelFormat") == "rgb24" &&
                L.Bool(decode, "exactInputPts") &&
                L.Long(transition, "lastPriorActorStablePts") == 37667 &&
                L.Long(transition, "firstPriorActorFadePts") == 37683 &&
                L.Long(transition, "firstBlankPts") == 37700 &&
                L.Long(transition, "lastBlankPts") == 37950 &&
                L.Long(transition, "firstLiZhiyanRecognizablePts") == 37967 &&
                L.Long(transition, "firstTealEdgeCandidatePts") == 38167 &&
                L.Long(transition, "firstUnambiguousTealSlabPts") == 38183 &&
                L.Str(transition, "candidateRestartStatus") ==
                    "visual_alignment_candidate_not_original_event_proof" &&
                anchors.Count == 7 &&
                samples.Count == expectedPts.Length &&
                L.List(oracle["nonClaims"]).Count == 3,
                "Li Zhiyan retail visual-oracle boundary drifted");
            for (int index = 0; index < samples.Count; index++)
            {
                Dictionary<string, object> sample = L.Dict(samples[index]);
                L.Require(
                    L.Long(sample, "pts") == expectedPts[index] &&
                    L.Str(sample, "timeBase") == "1/1000" &&
                    L.Str(sample, "scaledRgb24Sha256") == expectedHashes[index] &&
                    L.List(sample["scaledDimensions"]).Count == 2 &&
                    L.Dict(sample["rois"]).Count == 4,
                    "Li Zhiyan retail visual-oracle sample drifted: " + index);
            }
            Dictionary<string, object> peakRois = L.Dict(L.Dict(samples[1])["rois"]);
            Dictionary<string, object> settledRois = L.Dict(L.Dict(samples[5])["rois"]);
            L.Require(
                L.Float(L.Dict(peakRois["broadTeal"]), "tealCoverage") > 0.20f &&
                L.Float(L.Dict(settledRois["broadTeal"]), "tealCoverage") < 0.01f,
                "Li Zhiyan retail visual-oracle teal phase separation drifted");
        }

        private static void ValidateRetailDrawObservation()
        {
            Dictionary<string, object> observation = L.Dict(
                ManifestMiniJson.Deserialize(File.ReadAllText(
                    L.ProjectAbsolute(RetailDrawObservationPath), Encoding.UTF8)));
            Dictionary<string, object> importer = L.Dict(observation["importerBoundary"]);
            Dictionary<string, object> sources = L.Dict(observation["sources"]);
            Dictionary<string, object> abi = L.Dict(sources["abiContract"]);
            Dictionary<string, object> video = L.Dict(sources["video"]);
            L.Require(
                L.Str(observation, "schema") == "endfield.lizhiyan-retail-draw-observation.v1" &&
                L.Str(observation, "status") == "proof_pending" &&
                !L.Bool(observation, "visibleAdmission") &&
                L.Bool(importer, "offlineOnly") &&
                !L.Bool(importer, "launchedRetailClient") &&
                !L.Bool(importer, "attachedToRetailClient") &&
                !L.Bool(importer, "injectedIntoRetailClient") &&
                L.Bool(importer, "captureRequiresSeparateExplicitAuthorization") &&
                L.Str(abi, "sha256") ==
                    "1215E6EB3A721FBA3A3B095B8860A493CA7600EF4FDD3C81DAA3BAF8FDDF1F1B" &&
                L.Long(video, "bytes") == 1678613397L &&
                L.Str(video, "sha256") ==
                    "2F542A3BE7CE3332295D3A841FD8613C62707E084F9E33A0F156DA8A06EBF5E7" &&
                L.Long(video, "streamIndex") == 0 &&
                L.Str(video, "codec") == "h264" &&
                L.Str(video, "profile") == "High" &&
                L.Str(video, "pixelFormat") == "yuv420p" &&
                L.Str(video, "colorRange") == "tv" &&
                L.Str(video, "colorSpace") == "bt709" &&
                L.Str(video, "timeBase") == "1/1000" &&
                L.Str(video, "ptsRule").Contains("never derive timecode") &&
                L.List(sources["traces"]).Count == 0 &&
                observation["positiveJoin"] == null &&
                observation["negativeControl"] == null &&
                L.List(observation["requirements"]).Count == 11 &&
                L.List(observation["blockedBy"]).Count == 2 &&
                L.List(observation["nonClaims"]).Count == 4,
                "Li Zhiyan retail draw/video observation boundary drifted");
        }

        private static void ValidateNativeAbi()
        {
            Dictionary<string, object> native = L.Dict(
                ManifestMiniJson.Deserialize(File.ReadAllText(
                    L.ProjectAbsolute(NativeContractPath), Encoding.UTF8)));
            L.Require(L.Str(native, "schema") ==
                    "endfield.lizhiyan-after-dof-native-abi.v1" &&
                L.Str(native, "status") ==
                    "current_build_native_schedule_and_static_shader_abi_closed_live_draw_pending" &&
                L.List(native["methods"]).Count == 24 &&
                L.List(native["decisiveCalls"]).Count == 15,
                "Li Zhiyan native after-DOF contract identity drifted");
            var expectedMethods = new Dictionary<long, string>
            {
                { 286728, "00ACC65F4685738CB190BF536900D5AE7B421F4A2CAEDC25C3D2D0B7E2EB3162" },
                { 286732, "56CC43CF0F18122D3DE44731D2680F6951F48104A5A2986B9F35161CC883EC7F" },
                { 286733, "ECD06129C7B75CF85A127A5D5E543C956CC9FA4B23C1846A893CAE9464A3AD3E" },
                { 286724, "0D5928FA5F343C7F072A857C5B0FE6CA8943506877C71FA9A6257EF5F2983B7E" },
                { 286739, "B5A2AB43A40014751793CA227CD2F535AEF7470A1F3E71A93B24297ED9C40FCC" },
                { 286740, "525783A3D1731620269FBA6F156031EFDE5068FFA4ACC3FAFD1B4EFD0EA0948F" },
                { 286741, "88DFB9FB0D8B0B867A507E41AB2123C6E2830262290A1AB10616FD3A55DA2421" },
                { 284150, "DA8AB25AC903EEAE24FED48535F016BEA19C3BE7A21A7628C67BED63C7C83922" },
                { 284093, "B0D85048FC518253694C8BD1FC9B9F40C7F14DAA87B95EB180419233B28DD59D" },
                { 284103, "BD2E3852A86737D9F2732283AF677FA2A0F4209DD3FFB3F9476C957C67125A10" },
                { 284106, "08CA0296209FB21E02AFC9E2F5B02B06F0CA86A699A26BCD9951099D93F6926A" },
                { 284111, "6EFA8CEFFB982A2B6E4944B79DDDEBD5853166DC3B7CD0A10E8188048E27A6E0" },
                { 286702, "8C1488DC4A09BEB9F142B4EA2DD5CB7B98770D5DE48DA545E94655EE3538B329" },
                { 287999, "E1E497BAD2F5AA44B25F7E6D0F7ECA208CD81F4C49AE8D64070A4FB1D0E6187A" },
                { 478062, "8C8113556AB580A5337118F93A8B5E7A38BD79A8F656128FE768CF22B727261F" },
                { 288027, "C0D8BACD8084FAA9D608A95C2F56076A9FBC3FB57AB450AA8A2F403614C11E98" },
                { 288006, "499191DAF06A7B6985A8684B1435D6CC8DA7ECEA1A3C0623CFBAF8EC671ABCD5" },
                { 287274, "319799A95260B1717084D16AA8C2E0CCAD668CEDF3E52E9465B99A31EC44A5E0" },
                { 287316, "D54DCF38AC17E6062573C476BF988FF8CBEE70E89F2B02FB341E5588DA3612CC" },
                { 288038, "4695B2B6C39CB3522C067976FCC2F2677BC94692382C5611EF9E2EA743F145C5" },
                { 287324, "D49C4DE691A7B65184532D8C9E46E1209F35AF2A76C0E23FA82B8E35593011CC" },
                { 288225, "76DC5D1B4730F4A5BB937F3776A776DE2A8E960B4BB4A47B983BA5F264555879" },
                { 288226, "BBA699B59C1081CDF6870E95B3B17469DD0D8791234E166D1D403D85786E6F42" },
                { 288241, "08E90A05982967C1F0AA45950FDF24F069FA6B639238EE3F6429FEF2DE697163" },
            };
            foreach (object item in L.List(native["methods"]))
            {
                Dictionary<string, object> method = L.Dict(item);
                long index = L.Long(method, "methodIndex");
                L.Require(expectedMethods.TryGetValue(index, out string bodyHash) &&
                    L.Str(method, "functionSha256") == bodyHash,
                    "Li Zhiyan native method body identity drifted: " + index);
            }
            var unityNativeMethods = L.List(native["unityPlayerNativeMethods"])
                .Cast<object>().Select(L.Dict).ToDictionary(
                    row => L.Str(row, "label"), StringComparer.Ordinal);
            L.Require(
                unityNativeMethods.TryGetValue(
                    "HGMesh survivor worker with inherited publication tables",
                    out Dictionary<string, object> survivorWorker) &&
                L.Str(survivorWorker, "va") == "0x180ff8020" &&
                L.Str(survivorWorker, "functionEnd") == "0x180ff8702" &&
                L.Long(survivorWorker, "functionBytes") == 1762 &&
                L.Str(survivorWorker, "functionSha256") ==
                    "E80AF9084ED30D59CA2B65A4B925CBE31EB31FBF6F617792E89BB271948DF49E" &&
                unityNativeMethods.TryGetValue(
                    "HGMesh temporary group-to-index-vector map insertion",
                    out Dictionary<string, object> groupMap) &&
                L.Str(groupMap, "va") == "0x1810442f0" &&
                L.Str(groupMap, "functionEnd") == "0x181044592" &&
                L.Long(groupMap, "functionBytes") == 674 &&
                L.Str(groupMap, "functionSha256") ==
                    "79BEA9E2FEE0A5188F3F900744D2FBCC7B645D2EE00587C79E088A0706CAD6AB",
                "Li Zhiyan HGMesh upstream worker/group-map identity drifted");
            L.Require(
                unityNativeMethods.TryGetValue(
                    "HGMesh survivor job descriptor initializer",
                    out Dictionary<string, object> jobInitializer) &&
                L.Str(jobInitializer, "functionSha256") ==
                    "FF3DEB0F1031611C32924BA99FF3F00A3C9B70BA62CCD477B2EAD6FD79D181BB" &&
                unityNativeMethods.TryGetValue(
                    "HGMesh survivor job construction and scheduling owner",
                    out Dictionary<string, object> jobOwner) &&
                L.Str(jobOwner, "va") == "0x18104ef90" &&
                L.Str(jobOwner, "functionEnd") == "0x18104f16c" &&
                L.Long(jobOwner, "functionBytes") == 476 &&
                L.Str(jobOwner, "functionSha256") ==
                    "2797231E1B3801B780D526E513E27CADCA54834A6D49C90C3BCA64189CCAC728" &&
                unityNativeMethods.TryGetValue(
                    "HGMesh CreateRendererListFromEntities icall adapter",
                    out Dictionary<string, object> entityAdapter) &&
                L.Str(entityAdapter, "va") == "0x1801f20f0" &&
                L.Str(entityAdapter, "functionSha256") ==
                    "CA97F2AD6D958078B68FEC88EDB666A64CCEA3F8E3F2155414384E175B842619",
                "Li Zhiyan HGMesh survivor-job construction identity drifted");
            IList unityCalls = L.List(native["unityPlayerDecisiveCalls"]);
            L.Require(unityCalls.Count == 41 &&
                unityCalls.Cast<object>().Select(L.Dict).Any(row =>
                    L.Str(row, "callsite") == "0x180ff82b5" &&
                    L.Str(row, "target") == "0x1810442f0") &&
                unityCalls.Cast<object>().Select(L.Dict).Any(row =>
                    L.Str(row, "callsite") == "0x180ff856c" &&
                    L.Str(row, "target") == "0x181043bd0") &&
                unityCalls.Cast<object>().Select(L.Dict).Any(row =>
                    L.Str(row, "callsite") == "0x180ff8592" &&
                    L.Str(row, "target") == "0x181039e90") &&
                unityCalls.Cast<object>().Select(L.Dict).Any(row =>
                    L.Str(row, "callsite") == "0x18104efd6" &&
                    L.Str(row, "target") == "0x1802fd650") &&
                unityCalls.Cast<object>().Select(L.Dict).Any(row =>
                    L.Str(row, "callsite") == "0x18104efe3" &&
                    L.Str(row, "target") == "0x181045590") &&
                unityCalls.Cast<object>().Select(L.Dict).Any(row =>
                    L.Str(row, "callsite") == "0x18104f121" &&
                    L.Str(row, "target") == "0x180555d30") &&
                unityCalls.Cast<object>().Select(L.Dict).Any(row =>
                    L.Str(row, "callsite") == "0x1810463a0" &&
                    L.Str(row, "target") == "0x18104ef90") &&
                unityCalls.Cast<object>().Select(L.Dict).Any(row =>
                    L.Str(row, "callsite") == "0x18104ef33" &&
                    L.Str(row, "target") == "0x18104ef90") &&
                unityCalls.Cast<object>().Select(L.Dict).Any(row =>
                    L.Str(row, "callsite") == "0x1801f2163" &&
                    L.Str(row, "target") == "0x18104ec20") &&
                unityCalls.Cast<object>().Select(L.Dict).Any(row =>
                    L.Str(row, "callsite") == "0x180fc724e" &&
                    L.Str(row, "target") == "0x1810afc80") &&
                unityCalls.Cast<object>().Select(L.Dict).Any(row =>
                    L.Str(row, "callsite") == "0x180fc72c0" &&
                    L.Str(row, "target") == "0x181091dc0") &&
                unityCalls.Cast<object>().Select(L.Dict).Any(row =>
                    L.Str(row, "callsite") == "0x180fc7487" &&
                    L.Str(row, "target") == "0x1810454c0") &&
                unityCalls.Cast<object>().Select(L.Dict).Any(row =>
                    L.Str(row, "callsite") == "0x1810afccc" &&
                    L.Str(row, "target") == "0x1810aeea0") &&
                unityCalls.Cast<object>().Select(L.Dict).Any(row =>
                    L.Str(row, "callsite") == "0x181091e02" &&
                    L.Str(row, "target") == "0x1810914a0") &&
                unityCalls.Cast<object>().Select(L.Dict).Any(row =>
                    L.Str(row, "callsite") == "0x1801ee46a" &&
                    L.Str(row, "target") == "0x1810c2ff0") &&
                unityCalls.Cast<object>().Select(L.Dict).Any(row =>
                    L.Str(row, "callsite") == "0x1810b9c5c" &&
                    L.Str(row, "target") == "0x18109c9d0") &&
                unityCalls.Cast<object>().Select(L.Dict).Any(row =>
                    L.Str(row, "callsite") == "0x1811e1a24" &&
                    L.Str(row, "target") == "0x1810b9990") &&
                unityCalls.Cast<object>().Select(L.Dict).Any(row =>
                    L.Str(row, "callsite") == "0x18131b76b" &&
                    L.Str(row, "target") == "0x1810b9990") &&
                unityCalls.Cast<object>().Select(L.Dict).Any(row =>
                    L.Str(row, "callsite") == "0x18109441e" &&
                    L.Str(row, "target") == "0x18108b1c0") &&
                unityCalls.Cast<object>().Select(L.Dict).Any(row =>
                    L.Str(row, "callsite") == "0x181097fd6" &&
                    L.Str(row, "target") == "0x18108b560") &&
                unityCalls.Cast<object>().Select(L.Dict).Any(row =>
                    L.Str(row, "callsite") == "0x181098c71" &&
                    L.Str(row, "target") == "0x18108b8f0") &&
                unityCalls.Cast<object>().Select(L.Dict).Any(row =>
                    L.Str(row, "callsite") == "0x1805caf78" &&
                    L.Str(row, "target") == "0x1806198f0") &&
                unityCalls.Cast<object>().Select(L.Dict).Any(row =>
                    L.Str(row, "callsite") == "0x1805cb225" &&
                    L.Str(row, "target") == "0x1806198f0") &&
                unityCalls.Cast<object>().Select(L.Dict).Any(row =>
                    L.Str(row, "callsite") == "0x18059f395" &&
                    L.Str(row, "target") == "0x1805a3790") &&
                unityCalls.Cast<object>().Select(L.Dict).Any(row =>
                    L.Str(row, "callsite") == "0x1810b9c3e" &&
                    L.Str(row, "target") == "0x180600820") &&
                unityCalls.Cast<object>().Select(L.Dict).Any(row =>
                    L.Str(row, "callsite") == "0x180619915" &&
                    L.Str(row, "target") == "0x1806230b0") &&
                unityCalls.Cast<object>().Select(L.Dict).Any(row =>
                    L.Str(row, "callsite") == "0x1801ee287" &&
                    L.Str(row, "target") == "0x1801f7410") &&
                unityCalls.Cast<object>().Select(L.Dict).Any(row =>
                    L.Str(row, "callsite") == "0x1801ee587" &&
                    L.Str(row, "target") == "0x1801f7410") &&
                unityCalls.Cast<object>().Select(L.Dict).Any(row =>
                    L.Str(row, "callsite") == "0x181088f20" &&
                    L.Str(row, "target") == "0x1801f7410") &&
                unityCalls.Cast<object>().Select(L.Dict).Any(row =>
                    L.Str(row, "callsite") == "0x181088fb8" &&
                    L.Str(row, "target") == "0x1801f7410") &&
                unityCalls.Cast<object>().Select(L.Dict).Any(row =>
                    L.Str(row, "callsite") == "0x181089036" &&
                    L.Str(row, "target") == "0x1801f7410") &&
                unityCalls.Cast<object>().Select(L.Dict).Any(row =>
                    L.Str(row, "callsite") == "0x1800ba94f" &&
                    L.Str(row, "target") == "0x18052cf70") &&
                unityCalls.Cast<object>().Select(L.Dict).Any(row =>
                    L.Str(row, "callsite") == "0x1800629ac" &&
                    L.Str(row, "target") == "0x1804c9230") &&
                unityCalls.Cast<object>().Select(L.Dict).Any(row =>
                    L.Str(row, "callsite") == "0x1800b6f87" &&
                    L.Str(row, "target") == "0x18052d730"),
                "Li Zhiyan HGMesh upstream call graph drifted");
            Dictionary<string, object> boundary = L.Dict(native["nativeBoundary"]);
            Dictionary<string, object> decision = L.Dict(native["unityDecision"]);
            Dictionary<string, object> rendererList = L.Dict(native["rendererList"]);
            Dictionary<string, object> stateBlock = L.Dict(rendererList["stateBlock"]);
            Dictionary<string, object> consumers = L.Dict(native["rendererConsumers"]);
            Dictionary<string, object> perObjectData = L.Dict(rendererList["perObjectData"]);
            Dictionary<string, object> screenCulling = L.Dict(rendererList["screenCulling"]);
            Dictionary<string, object> screenDefaults = L.Dict(screenCulling["constructorDefaults"]);
            Dictionary<string, object> passInputOffsets = L.Dict(rendererList["passInputOffsets"]);
            Dictionary<string, object> ecsProducer = L.Dict(rendererList["ecsRendererListProducer"]);
            Dictionary<string, object> nativeAdapter = L.Dict(ecsProducer["nativeAdapter"]);
            Dictionary<string, object> handleTable = L.Dict(nativeAdapter["handleTable"]);
            Dictionary<string, object> contextOwnership = L.Dict(handleTable["contextOwnership"]);
            Dictionary<string, object> commandConsumer = L.Dict(nativeAdapter["commandConsumer"]);
            Dictionary<string, object> survivorSort = L.Dict(nativeAdapter["survivorSortPublication"]);
            Dictionary<string, object> upstreamWorker =
                L.Dict(survivorSort["upstreamWorkerBoundary"]);
            Dictionary<string, object> jobConstruction =
                L.Dict(upstreamWorker["jobConstruction"]);
            Dictionary<string, object> rootSubsystemTables =
                L.Dict(jobConstruction["rootSubsystemTables"]);
            Dictionary<string, object> workerKeyLayouts = L.Dict(survivorSort["workerKeyLayouts"]);
            Dictionary<string, object> backendBoundary = L.Dict(survivorSort["backendBoundary"]);
            Dictionary<string, object> descriptorMode =
                L.Dict(backendBoundary["descriptorMode"]);
            Dictionary<string, object> observedBackend = L.Dict(backendBoundary["observedRuntimeBackend"]);
            Dictionary<string, object> observedBackendSession = L.Dict(observedBackend["session"]);
            Dictionary<string, object> graphicsFront = L.Dict(backendBoundary["graphicsFront"]);
            Dictionary<string, object> commandInterpreter = L.Dict(backendBoundary["commandInterpreter"]);
            Dictionary<string, object> backendSelection = L.Dict(backendBoundary["backendSelection"]);
            Dictionary<string, object> vulkanExecution = L.Dict(backendBoundary["vulkanExecution"]);
            Dictionary<string, object> captureBoundary = L.Dict(nativeAdapter["runtimeCaptureBoundary"]);
            L.Require(L.Str(boundary, "callbackConstantBufferPublication") == "not_present" &&
                L.Str(boundary, "callbackGlobalVectorAndTexturePublication") == "present" &&
                !L.Bool(boundary, "serializedBindingsAreD3D12RootParameters") &&
                L.Long(rendererList, "sortingCriteria") == 87 &&
                L.Str(rendererList, "sortingSemantic") ==
                    "CommonTransparent | OptimizeStateChanges | RendererPriority" &&
                L.Str(rendererList, "layerMask") ==
                    "RemoveWorldUILayer(camera.cullingMask)" &&
                !L.Bool(stateBlock, "hasValue") &&
                rendererList["overrideMaterial"] == null &&
                !L.Bool(rendererList, "excludeObjectMotionVectors") &&
                L.Long(perObjectData, "bakedLightingConfig") == 15 &&
                L.Long(perObjectData, "motionVectorConfigForNonNullHGCamera") == 32 &&
                L.Long(perObjectData, "combined") == 47 &&
                L.Float(screenDefaults, "ratio") == 0.005f &&
                L.Float(screenDefaults, "distance") == 30.0f &&
                L.List(screenCulling["layerNames"]).Count == 17 &&
                L.Str(screenCulling, "ratioDistanceWriters").Contains("ctor only") &&
                L.List(screenCulling["layerMaskWriters"]).Count == 4 &&
                L.Str(screenCulling, "runtimeInstanceValues").Contains("runtime-mutated") &&
                L.Long(passInputOffsets, "bytes") == 160 &&
                L.Str(passInputOffsets, "forwardTransparentAfterDOFECSList") == "0x04" &&
                L.Str(passInputOffsets, "screenCullingLayerMask") == "0x08" &&
                L.Str(passInputOffsets, "hgrp") == "0x98" &&
                L.Str(ecsProducer, "owner") == "HGRenderPathDeferred.OnPreRendering" &&
                L.Str(ecsProducer, "fieldOffset") == "0x1388" &&
                L.Str(ecsProducer, "handleType") == "System.UInt32" &&
                L.Long(ecsProducer, "invalidSentinel") == 4294967295L &&
                L.Str(ecsProducer, "constructorSentinelWriteVA") == "0x182ed9507" &&
                L.Str(ecsProducer, "phase1ReadVA") == "0x189c00568" &&
                L.Str(ecsProducer, "renderFlagsMask") ==
                    "0x4400 (TransparentAfterPP | ShadowOnly)" &&
                L.Str(ecsProducer, "renderFlagsValue") ==
                    "0x4000 (TransparentAfterPP)" &&
                L.Bool(ecsProducer, "multiDraw") &&
                L.Bool(ecsProducer, "transparentSorting") &&
                !L.Bool(ecsProducer, "noAlphaTest") &&
                !L.Bool(ecsProducer, "excludeGPUDriven") &&
                L.Str(ecsProducer, "forwardPath").Contains("never writes 0x1388") &&
                L.Long(nativeAdapter, "registrationIndex") == 395 &&
                L.Str(nativeAdapter, "unityPlayerVA") == "0x1801f1e40" &&
                L.Long(nativeAdapter, "functionBytes") == 206 &&
                L.Str(nativeAdapter, "requestPackerVA") == "0x18104e7a0" &&
                L.Str(nativeAdapter, "registrationCoreVA") == "0x18104e300" &&
                L.Str(nativeAdapter, "resourceRecordBuilderVA") == "0x18104e920" &&
                L.Str(nativeAdapter, "behavior").Contains("contains no entity iteration") &&
                L.Str(handleTable, "registrationLifecycle") ==
                    "reads the old count as the handle, grows through 0x1802ed7d0 -> 0x180662870 when required, increments count, zeroes the new slot, allocates a 0x30-byte state through 0x1802fd650, and stores it at slot +0x08" &&
                L.Str(handleTable, "consumerMutation") ==
                    "opcode 0x4e consumer 0x181005c10 reads slot +0x08 but does not modify the manager vector or count" &&
                L.Str(handleTable, "resetAudit").Contains("external context replacement") &&
                L.Str(contextOwnership, "slotAccessorVA") == "0x180fc5e60" &&
                L.Str(contextOwnership, "contextPointerCellVA") == "0x1821688a0" &&
                L.Str(contextOwnership, "managerOffset") == "0xb0" &&
                L.Str(contextOwnership, "parallelHGTreeOffset") == "0xc0" &&
                L.Str(contextOwnership, "genericSetterVA") == "0x18030f5b0" &&
                L.Str(contextOwnership, "bulkRegistrarVA") == "0x180319e60" &&
                L.Str(contextOwnership, "globalTeardownVA") == "0x18058cc20" &&
                L.Str(contextOwnership, "genericCleanupVA") == "0x18031aec0" &&
                L.Str(contextOwnership, "nestedCleanupVA") == "0x18031af80" &&
                L.Str(contextOwnership, "contextVtableVA") == "0x181e1c328" &&
                L.Str(contextOwnership, "contextDestructorVA") == "0x180fc2e00" &&
                L.Str(contextOwnership, "contextConstructorVA") == "0x180fc21d0" &&
                L.Str(contextOwnership, "contextInitializationVA") == "0x180fc3500" &&
                L.Str(contextOwnership, "managerAllocation").Contains("0x70 bytes") &&
                L.Str(contextOwnership, "managerAllocation").Contains("0xb5") &&
                L.Str(contextOwnership, "managerResetVA") == "0x181060330" &&
                L.Str(contextOwnership, "managerDestructionVA") == "0x1810459f0" &&
                L.Str(contextOwnership, "managerNestedEntryDestructionVA") == "0x18105fe30" &&
                L.Str(contextOwnership, "registryFactoryPath").Contains("[descriptor+0x08]") &&
                L.Str(contextOwnership, "registryFactoryBoundary").Contains("initialized dynamically") &&
                L.Str(contextOwnership, "provenBoundary").Contains("allocator callback identity") &&
                L.Str(commandConsumer, "opcode") == "0x4e" &&
                L.Str(commandConsumer, "managerSingletonOffset") == "0xb0" &&
                L.Long(commandConsumer, "slotStride") == 16 &&
                L.Str(commandConsumer, "consumerVA") == "0x181005c10" &&
                L.Str(commandConsumer, "excludedParallelFamily").Contains("HGTree") &&
                L.Long(survivorSort, "recordStride") == 64 &&
                L.Long(survivorSort, "comparatorKeyBytes") == 16 &&
                L.Str(survivorSort, "sortVA") == "0x181043bd0" &&
                L.Str(survivorSort, "comparator") ==
                    "unsigned-byte lexicographic order over record bytes 0x00..0x0f" &&
                L.Str(survivorSort, "recordAppendVA") == "0x18105e400" &&
                L.Str(survivorSort, "keyConstructionScope").Contains("worker-family-dependent") &&
                StringListEquals(workerKeyLayouts["alternateFamily"],
                    "dword 0 packs a masked 20-bit source, another source shifted by 20, and a byte flag",
                    "dword 1 combines source +0x08, a byte selector, and a 16-bit source value",
                    "dword 2 combines source +0x0c, selector bits, and a conditional 0x01000000 marker",
                    "dword 3 combines context byte state, source +0x22 u16, and ((~asuint(float)) >> 17) & 0x3fff") &&
                StringListEquals(workerKeyLayouts["standardFamily"],
                    "dword 0 combines ((asuint(float) >> 15) & 0xffff) with a selector shifted by 16",
                    "dword 1 packs a masked 20-bit source, another selector shifted by 20, then a byte lane",
                    "dword 2 packs context/resource state plus a conditional 0x01000000 marker",
                    "dword 3 packs type/context/index selectors") &&
                L.Str(survivorSort, "semanticKey") ==
                    "opaque packed renderer-state key; byte/bit construction is proven but field names remain unresolved" &&
                StringListEquals(survivorSort["commonAcceptanceGates"],
                    "(source[0x10:0x20] & context[0x40:0x50]) == 0",
                    "(source+0x10 qword & context+0x50 qword) != 0",
                    "source+0x10 has at least one 0x60000 bit",
                    "source+0x10 has at least one 0x7f00 bit",
                    "(source+0x10 & 0xc0) == 0xc0",
                    "context+0x34 & viewMask[index] != 0",
                    "source bit 45 is clear") &&
                L.Str(survivorSort, "variantGate") ==
                    "four resource-state worker variants additionally require signed dword source+0x2c > 0 in the source+0x18 bit-15 path" &&
                L.Str(survivorSort, "workerSelectionFields") ==
                    "request +0x28 multiDraw, +0x29 transparentSorting, +0x30 noAlphaTest plus live resource presence; excludeGPUDriven is request +0x40 and is not independently reread as a worker-local Boolean" &&
                L.Str(survivorSort, "invalidRecordGate") ==
                    "publication skips record +0x20 == 0xffffffff" &&
                L.Str(survivorSort, "provenPipeline") ==
                    "post-filter 64-byte records -> in-place key sort -> invalid-record skip -> ID/resource resolve -> pointer-vector publication" &&
                L.Str(upstreamWorker, "workerVA") == "0x180ff8020" &&
                L.Str(upstreamWorker, "workerEndVA") == "0x180ff8702" &&
                L.Long(upstreamWorker, "sourceRecordStride") == 576 &&
                L.Long(upstreamWorker, "temporaryGroupEntryStride") == 48 &&
                L.Str(upstreamWorker, "temporaryGroupValue") ==
                    "owned vector of 4-byte source indices" &&
                L.Str(upstreamWorker, "temporaryGroupMapBoundary").Contains(
                    "does not populate M0's 0x60-byte entry") &&
                L.Str(upstreamWorker, "remainingProducerBoundary").Contains(
                    "population of those already-existing tables") &&
                L.Str(jobConstruction, "ownerVA") == "0x18104ef90" &&
                L.Str(jobConstruction, "ownerEndVA") == "0x18104f16c" &&
                L.Str(jobConstruction, "allocation").Contains("0xf0 bytes") &&
                L.Str(jobConstruction, "argumentStores").Contains(
                    "arg2/rdx -> descriptor+0x00 (M0)") &&
                L.Str(jobConstruction, "workerReference").Contains(
                    "sole confirmed code reference") &&
                L.Str(jobConstruction, "schedulerRoute").Contains(
                    "0x180555d30 -> 0x1805573d0 -> 0x180559520") &&
                L.Str(jobConstruction, "explicitEntityCaller").Contains(
                    "CreateRendererListFromEntities_Injected") &&
                L.Str(jobConstruction, "identityBoundary").Contains(
                    "M0 material entry population is separately closed") &&
                L.Str(rootSubsystemTables, "m0Identity").Contains(
                    "HGShadingStateSystem") &&
                L.Str(rootSubsystemTables, "m0Table").Contains(
                    "0x60-byte entries") &&
                L.Str(rootSubsystemTables, "m1Identity").Contains(
                    "HGGeometrySystem") &&
                L.Str(rootSubsystemTables, "m1Table").Contains(
                    "0x38-byte entries") &&
                L.Str(rootSubsystemTables, "managerInjection").Contains(
                    "manager+0x50/+0x58") &&
                L.Str(rootSubsystemTables, "explicitEntityFlow").Contains(
                    "0x181039e90 M0/M1") &&
                L.Str(rootSubsystemTables, "materialInsertion").Contains(
                    "0x1810b9990") &&
                L.Str(rootSubsystemTables, "descriptorDWriter").Contains(
                    "0x18109ca2f") &&
                L.Str(rootSubsystemTables, "descriptorDWriter").Contains(
                    "entry+0x28") &&
                L.Str(rootSubsystemTables, "materialInsertionCallers").Contains(
                    "0x1811e1a24") &&
                L.Str(rootSubsystemTables, "descriptorDIdentity").Contains(
                    "PPtr<HGSubsurfaceProfile>") &&
                L.Str(rootSubsystemTables, "descriptorDIdentity").Contains(
                    "0x181d87ef0") &&
                L.Str(rootSubsystemTables, "descriptorDIdentity").Contains(
                    "wrapper+0x140") &&
                L.Str(rootSubsystemTables, "descriptorDIdentity").Contains(
                    "not the wrapper itself") &&
                L.Str(rootSubsystemTables, "managedMaterialApi").Contains(
                    "GetMaterialHandle(int instanceId)") &&
                L.Str(rootSubsystemTables, "managedMaterialApi").Contains(
                    "does not override") &&
                L.Str(rootSubsystemTables, "unityObjectOrigin").Contains(
                    "0x1811e170a") &&
                L.Str(rootSubsystemTables, "unityObjectOrigin").Contains(
                    "not Li-specific identity") &&
                L.Str(rootSubsystemTables, "ordinaryMaterialBoundary").Contains(
                    "no direct Li Zhiyan") &&
                L.Str(rootSubsystemTables, "liStaticAssetBoundary").Contains(
                    "75 SkinnedMeshRenderer") &&
                L.Str(rootSubsystemTables, "liStaticAssetBoundary").Contains(
                    "no serialized HGMeshRenderer") &&
                L.Str(rootSubsystemTables, "runtimeIdBoundary").Contains(
                    "cannot derive retail Material.GetInstanceID()") &&
                L.Str(rootSubsystemTables, "requiredLiHandleJoin").Contains(
                    "GetMaterialHandle/GetGeometryHandle") &&
                L.Str(rootSubsystemTables, "perMaterialCbBoundary").Contains(
                    "downstream per-material-CB consumer") &&
                L.Str(rootSubsystemTables, "geometryInsertion").Contains(
                    "0x18137284a") &&
                L.Str(rootSubsystemTables, "geometryInsertion").Contains(
                    "0x18109441e") &&
                L.Str(rootSubsystemTables, "geometryEntryWriter").Contains(
                    "entry+0x18") &&
                L.Str(rootSubsystemTables, "geometryEntryWriter").Contains(
                    "entry+0x28/+0x30") &&
                L.Str(rootSubsystemTables, "geometryEntryLifecycle").Contains(
                    "0x18108b560") &&
                L.Str(rootSubsystemTables, "geometryEntryLifecycle").Contains(
                    "increments generation") &&
                L.Str(rootSubsystemTables, "geometryIdentity").Contains(
                    "0x18012be60") &&
                L.Str(rootSubsystemTables, "remainingPopulationBoundary").Contains(
                    "Li-specific profile handle/resource") &&
                StringListEquals(survivorSort["notYetProven"],
                    "semantic names of packed key fields",
                    "HGMesh-derived descriptor state reaching one specific Vulkan draw/submit and visible pixel",
                    "slot-0x14 registry factory identity") &&
                L.Str(backendBoundary, "resultCallbackThunkVA") == "0x180feaea0" &&
                L.Str(backendBoundary, "frontEndHandoffVA") == "0x1810484e0" &&
                L.Str(backendBoundary, "behavior").Contains("descriptor-mode-conditional path") &&
                L.Str(descriptorMode, "ownerPopulationBoundary").Contains(
                    "0x1810b9990 -> 0x18109c9d0") &&
                L.Str(descriptorMode, "ownerPopulationBoundary").Contains(
                    "entry+0x28") &&
                L.Str(descriptorMode, "exactModeConstructor").Contains(
                    "0x180619952") &&
                L.Str(descriptorMode, "exactModeConstructor").Contains(
                    "mode 2") &&
                L.Str(descriptorMode, "exactModeConstructor").Contains(
                    "mode 0") &&
                L.Str(descriptorMode, "aliasBoundary").Contains(
                    "PPtr<HGSubsurfaceProfile>") &&
                L.Str(graphicsFront, "vtableVA") == "0x181dcb360" &&
                L.Str(graphicsFront, "resourceAppendSlot").Contains("opcode 0x2748") &&
                L.Str(graphicsFront, "descriptorUpdateSlot").Contains("opcode 0x2730") &&
                L.Str(graphicsFront, "executeSlot").Contains("opcode 0x2731") &&
                L.Str(graphicsFront, "beginRecordingSlot").Contains("+0x2711") &&
                L.Str(graphicsFront, "endRecordingSlot").Contains("0x27cb") &&
                L.Str(commandInterpreter, "interpreterVA") == "0x1813aee90" &&
                L.Str(commandInterpreter, "dispatchTableVA") == "0x1813bb574" &&
                L.Str(commandInterpreter, "opcode2748CaseVA") == "0x1813b1624" &&
                L.Str(commandInterpreter, "opcode2748Route").Contains("mode 1") &&
                L.Str(commandInterpreter, "opcode274aCaseVA") == "0x1813b16f0" &&
                L.Str(commandInterpreter, "opcode274aRoute").Contains("mode 0") &&
                L.Str(commandInterpreter, "api2ResourceCollection").Contains("+0x2e48") &&
                L.Str(commandInterpreter, "sharedRecorder").Contains("append order equals invocation order") &&
                L.Str(commandInterpreter, "opcode2730Layout").Contains("seven u64") &&
                L.Str(commandInterpreter, "opcode2731Layout").Contains("no payload") &&
                L.Str(commandInterpreter, "batchBoundary").Contains("0x1813aea00") &&
                L.Str(commandInterpreter, "sequenceBoundary").Contains("no static producer edge proves") &&
                L.Str(commandInterpreter, "handoffWriterOrder").Contains("0x181048848") &&
                L.Str(commandInterpreter, "handoffWriterOrder").Contains("0x1810488dc") &&
                L.Str(commandInterpreter, "handoffExcludedWriter").Contains("no direct front +0x3e8") &&
                L.Str(commandInterpreter, "executeProducerCandidates").Contains("no static edge") &&
                L.Str(commandInterpreter, "executeBracket").Contains("0x18059f2f0") &&
                L.Str(commandInterpreter, "executeBracket").Contains("0x2731") &&
                L.Str(commandInterpreter, "executeOwnerBoundary").Contains("runtime-populated") &&
                L.Str(commandInterpreter, "executeOwnerBoundary").Contains("no static call") &&
                L.Str(commandInterpreter, "resourceToBindingState").Contains("original pointer unchanged") &&
                L.Str(commandInterpreter, "resourceToBindingState").Contains("S+0x2a0") &&
                L.Str(commandInterpreter, "provenBoundary").Contains("not draw opcodes") &&
                L.Str(backendSelection, "api2TableVA") == "0x181dbc098" &&
                L.Str(backendSelection, "api2Meaning").Contains("not Unity's public") &&
                L.Str(backendSelection, "vulkanDrawFlush").Contains("0x180843d60") &&
                L.Str(backendSelection, "vulkanCommandCells").Contains("vkQueueSubmit") &&
                L.Str(vulkanExecution, "descriptorUpdateRoute").Contains("vkUpdateDescriptorSetWithTemplate") &&
                L.Str(vulkanExecution, "descriptorIdentityBoundary").Contains("conditionally reaches the generic 0x2730 producer") &&
                L.Str(vulkanExecution, "callbackListBuilders").Contains("+0xda8") &&
                L.Str(vulkanExecution, "resourceBindingNode").Contains("index format") &&
                L.Str(vulkanExecution, "pipelineDescriptorNode").Contains("descriptor-set") &&
                L.Str(vulkanExecution, "indirectDrawNode").Contains("draw count 1") &&
                L.Str(vulkanExecution, "hgmeshAttributionBoundary").Contains("must not be attributed") &&
                L.Str(vulkanExecution, "masterList").Contains("+0x2b50") &&
                L.Str(vulkanExecution, "resourceBinding").Contains("index and vertex") &&
                L.Str(vulkanExecution, "indirectDraw").Contains("vkCmdDrawIndexedIndirect") &&
                L.Str(vulkanExecution, "directDraw").Contains("vkCmdDraw(3,1,0,0)") &&
                L.List(vulkanExecution["queueSubmitCallsites"]).Count == 2 &&
                L.Str(vulkanExecution, "remainingIdentityEdge").Contains("particular HGMesh draw record") &&
                L.Str(backendBoundary, "d3d12StaticBoundary").Contains("D3D12 support not compiled in!") &&
                L.Str(observedBackend, "classification") == "observed_runtime_log" &&
                L.Str(observedBackendSession, "graphicsBackend") == "Vulkan" &&
                L.Str(observedBackendSession, "engineVersion") == "2021.3.34f5 (0)" &&
                L.Str(observedBackendSession, "physicalDevice") == "NVIDIA GeForce RTX 5080" &&
                L.List(observedBackend["nonClaims"]).Count == 3 &&
                L.Str(backendBoundary, "activeBackend").StartsWith("Vulkan is proven") &&
                L.Str(captureBoundary, "authorization").Contains("separate explicit authorization") &&
                L.List(captureBoundary["observationOnlyHooks"]).Count == 8 &&
                L.List(captureBoundary["boundedFields"]).Count == 4 &&
                L.Str(captureBoundary, "requiredPositiveJoin").Contains("specific Vulkan draw/submit") &&
                L.Str(captureBoundary, "negativeControl").Contains("Wulfa") &&
                L.Str(captureBoundary, "stopRule").Contains("never retry through evasion") &&
                !L.Bool(consumers, "opaqueArgument") &&
                L.Str(consumers, "frameSettingsGate") == "TransparentObjects" &&
                L.Str(consumers, "classicNativeHandle").Contains("16-byte opaque") &&
                L.Str(consumers, "classicCommand").Contains("opcode 0x4d") &&
                L.Str(consumers, "classicBackendBoundary").Contains("no static Li renderer ID") &&
                L.Str(consumers, "liClassicEligibility").Contains("strongest source-backed route") &&
                L.Str(consumers, "survivorIdentity") ==
                    "runtime renderer-list and ECS handles pending" &&
                !L.Bool(decision, "visibleAdmission") &&
                !L.Bool(decision, "vfxParams1PublicationRequiredForSelectedMaterials") &&
                !L.Bool(decision, "transformHistoryRequiredForSelectedMaterials"),
                "Li Zhiyan native-to-Unity fail-closed decision drifted");
        }

        private static bool StringListEquals(object value, params string[] expected)
        {
            IList actual = L.List(value);
            return actual.Count == expected.Length && actual.Cast<object>()
                .Select(item => Convert.ToString(item))
                .SequenceEqual(expected);
        }

        private static void ValidateStage(
            Dictionary<string, object> stage,
            string expectedStage,
            bool fragment,
            string materialSignature)
        {
            L.Require(L.Str(stage, "decodedProgramStage") == expectedStage &&
                L.Str(stage, "sourcePass") == "ForwardOnly",
                "Li Zhiyan DXBC stage/pass drifted");
            ValidateArtifact(L.Dict(stage["dxbc"]));
            ValidateArtifact(L.Dict(stage["metadata"]));
            Dictionary<string, object> assembly = L.Dict(stage["exactAssembly"]);
            ValidateArtifact(L.Dict(assembly["artifact"]));
            if (!fragment)
                return;
            ValidateArtifact(L.Dict(stage["ruriHlsl"]));
            Dictionary<string, object> registers = L.Dict(stage["registerSignature"]);
            var outputs = new HashSet<string>(
                L.List(registers["outputs"]).Cast<object>()
                    .Select(value => Convert.ToString(value)), StringComparer.Ordinal);
            L.Require(outputs.SetEquals(new[] { "SV_Target", "SV_Target_1" }) &&
                L.List(registers["resources"]).Count >= 2 &&
                L.List(registers["constantBuffers"]).Count >= 3,
                "Li Zhiyan fragment register/MRT signature drifted");
            Dictionary<string, object> lengths =
                L.Dict(assembly["constantBufferFloat4Lengths"]);
            long expectedMaterialLength = materialSignature == "" ? 21 :
                materialSignature == "_USE_SOFTBLEND" ? 22 : 28;
            L.Require(L.Str(assembly, "shaderModel") == "ps_5_0" &&
                L.Long(lengths, "0") == 28 && L.Long(lengths, "1") == 105 &&
                L.Long(lengths, "2") == 5 && L.Long(lengths, "3") == expectedMaterialLength,
                "Li Zhiyan exact DXBC constant-buffer ABI drifted");
            Dictionary<string, object> semantics =
                L.Dict(stage["staticResourceSemantics"]);
            int expectedPairs = materialSignature == "" ? 1 :
                materialSignature == "_USE_SOFTBLEND" ? 2 : 3;
            L.Require(L.Str(semantics, "status") ==
                    "variant_delta_and_coordinate_use_closed_live_descriptor_identity_pending" &&
                L.List(semantics["texturesAndSamplers"]).Count == expectedPairs &&
                L.List(assembly["textureSamplerPairs"]).Count == expectedPairs,
                "Li Zhiyan texture/sampler ABI drifted");
        }

        private static void ValidateArtifact(Dictionary<string, object> artifact)
        {
            const string projectPrefix = "unity_endfield_graph_shader_lab/";
            string relative = L.Str(artifact, "path").Replace('\\', '/');
            L.Require(relative.StartsWith(projectPrefix, StringComparison.Ordinal),
                "Li Zhiyan shader artifact escaped the Unity project");
            string path = L.ProjectAbsolute(relative.Substring(projectPrefix.Length));
            L.Require(File.Exists(path) && new FileInfo(path).Length == L.Long(artifact, "bytes") &&
                Sha256(path) == L.Str(artifact, "sha256").ToUpperInvariant(),
                "Li Zhiyan shader artifact drifted: " + path);
        }

        private static void ValidateRepositoryArtifact(Dictionary<string, object> artifact)
        {
            string relative = L.Str(artifact, "path").Replace('\\', '/');
            string repositoryRoot = Path.GetFullPath(
                Path.Combine(Application.dataPath, "..", ".."));
            string path = Path.GetFullPath(Path.Combine(
                repositoryRoot,
                relative.Replace('/', Path.DirectorySeparatorChar)));
            L.Require(path.StartsWith(repositoryRoot + Path.DirectorySeparatorChar,
                    StringComparison.OrdinalIgnoreCase) &&
                File.Exists(path) && new FileInfo(path).Length == L.Long(artifact, "bytes") &&
                Sha256(path) == L.Str(artifact, "sha256").ToUpperInvariant(),
                "Li Zhiyan repository evidence artifact drifted: " + path);
        }

        private static string Signature(IEnumerable<string> values)
        {
            return string.Join("+", values.Where(value => !string.IsNullOrEmpty(value))
                .OrderBy(value => value, StringComparer.Ordinal));
        }

        private static string Sha256(string path)
        {
            using (SHA256 hash = SHA256.Create())
            using (FileStream stream = File.OpenRead(path))
                return BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", string.Empty);
        }
    }
}
