using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Diagnostic-only actor/effect composition capture for Li Zhiyan.
    ///
    /// This deliberately remains separate from the existing static-effect
    /// combined harness.  It uses the recovered actor prefab and source
    /// CharInfo camera fields, but does not claim the retail animation ABI,
    /// renderer identity, event origin, or pixel equality with the retail
    /// video oracle.
    /// </summary>
    public static class EndfieldLiZhiyanActorComposedVisualCaptureHarness
    {
        private const string ActorPrefabPath =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Lizhiyan/" +
            "Prefabs/Lizhiyan.prefab";
        private const string ActorClipPath =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Lizhiyan/" +
            "Animations/A_actor_lizhiyan_ui_overview_start_01.anim";
        private const string ProfilePath =
            "Assets/EndfieldGraphShaderLab/Generated/CharInfoPlayableProfiles/Profiles/Lizhiyan.asset";
        private const string Start01PrefabPath =
            "Assets/EndfieldGraphShaderLab/Generated/Diagnostics/LiZhiyanStart01/" +
            "Prefabs/P_fxui_lizhiyan_overview_start_01_DIAGNOSTIC.prefab";
        private const string Start02PrefabPath =
            "Assets/EndfieldGraphShaderLab/Generated/Diagnostics/LiZhiyanStart02/" +
            "Prefabs/P_fxui_lizhiyan_overview_start_02_DIAGNOSTIC.prefab";
        private const string Start03PrefabPath =
            "Assets/EndfieldGraphShaderLab/Generated/Diagnostics/LiZhiyanStart03/" +
            "Prefabs/P_fxui_lizhiyan_overview_start_03_DIAGNOSTIC.prefab";
        private const string FingerEffectPrefabPath =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Lizhiyan/" +
            "Effects/OverviewFinger/P_fxui_lizhiyan_overview_trails_Bip001_R_Finger2Nub.prefab";
        private const string FingerEffectContractPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/" +
            "lizhiyan_overview_finger_effect.json";
        private const string FingerMountHierarchy = "Bip001_R_Finger2Nub";
        private const float FingerEffectDelaySeconds = 0.83333f;
        private const float FingerEffectDurationSeconds = 2.33333f;
        private const string SpecPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/ShaderEvidence/" +
            "LiZhiyanOverviewFinger/lizhiyan_visual_capture_spec.json";
        private const string RetailOraclePath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/ShaderEvidence/" +
            "LiZhiyanOverviewFinger/lizhiyan_retail_visual_oracle.json";
        private const string BaselineManifestRelativePath =
            "scratch/character_recovery/" +
            "lizhiyan_start01_start02_start03_capture/" +
            "lizhiyan_start01_start02_start03_capture_manifest.json";
        private const string OutputDirectoryRelativePath =
            "scratch/character_recovery/lizhiyan_actor_composed_capture";
        private const string ManifestFileName =
            "lizhiyan_actor_composed_capture_manifest.json";
        private const string ExpectedSpecSchema =
            "endfield.lizhiyan-visual-capture-spec.v1";
        private const string ExpectedOracleSchema =
            "endfield.lizhiyan-retail-visual-oracle.v1";
        private const string ExpectedManifestSchema =
            "endfield.lizhiyan-actor-composed-diagnostic-capture.v4";
        private const long SharedClipPathId = 7360398354216100382L;
        private const string SharedClipName = "A_fxui__lizhiyan_overview_start_01";
        private const float SharedClipStopTime = 6.366667f;
        private const float ExpectedActorClipLength = 10.7f;
        private const int CandidateRestartPts = 37967;
        private const int Width = 960;
        private const int Height = 540;
        private const int DiagnosticCaptureRenderQueue = 3704;
        private const float ActiveEndpointEpsilon = 0.000001f;
        private const byte CoverageAlphaThreshold = 8;
        private const byte CoverageColorThreshold = 8;
        private const string ExpectedTealPredicate =
            "g>=80 && b>=80 && g-r>=20 && b-r>=10";

        private static readonly RootDefinition[] Roots =
        {
            new RootDefinition
            {
                key = "start_01",
                effectRoot = "P_fxui_lizhiyan_overview_start_01",
                prefabPath = Start01PrefabPath,
                durationSeconds = 2.2f,
            },
            new RootDefinition
            {
                key = "start_02",
                effectRoot = "P_fxui_lizhiyan_overview_start_02",
                prefabPath = Start02PrefabPath,
                durationSeconds = 5.0f,
            },
            new RootDefinition
            {
                key = "start_03",
                effectRoot = "P_fxui_lizhiyan_overview_start_03",
                prefabPath = Start03PrefabPath,
                durationSeconds = 7.0f,
            },
        };

        private static readonly string[] PeakEffectRoots =
        {
            "P_fxui_lizhiyan_overview_start_04",
            "P_fxui_lizhiyan_overview_start_04_1",
            "P_fxui_lizhiyan_overview_start_04_2",
        };

        private static readonly CaptureAnchor[] Anchors =
        {
            Anchor(37967, "candidate_restart"),
            Anchor(38000, "lizhiyan_transition_visible_pre_distinct_teal"),
            Anchor(38167, "start_01_first_dynamic_key_candidate"),
            Anchor(38183, "start_01_first_unambiguous_teal_slab"),
            Anchor(39367, "start_03_first_dynamic_key_path_1"),
            Anchor(39934, "start_01_last_dynamic_key_candidate"),
            Anchor(40000, "broad_teal_peak"),
            Anchor(40167, "start_01_lifetime_end"),
            Anchor(40834, "start_02_first_dynamic_key_path_3"),
            Anchor(40867, "start_02_first_dynamic_key_paths_0_1"),
            Anchor(41434, "start_02_first_nonzero_alpha_candidate"),
            Anchor(41967, "start_02_last_dynamic_key"),
            Anchor(42000, "broad_effect_late"),
            Anchor(42467, "start_03_next_material_wave"),
            Anchor(42967, "start_02_lifetime_end"),
            Anchor(43000, "compact_teal_trail"),
            Anchor(43200, "start_03_first_nonzero_alpha_candidate"),
            Anchor(43600, "start_03_main_material_dynamic_key"),
            Anchor(43867, "start_03_alpha_fade_candidate"),
            Anchor(43900, "start_03_tail_dynamic_key"),
            Anchor(44000, "trail_decay"),
            Anchor(44334, "shared_material_clip_end_nearest_frame"),
            Anchor(44967, "start_03_lifetime_end"),
            Anchor(46000, "settled_no_substantial_teal"),
        };

        [MenuItem("Endfield/Character Recovery Lab/Capture Li Zhiyan Actor-Composed Visual Spec")]
        public static void BuildAndCapture()
        {
            Require(SystemInfo.graphicsDeviceType != GraphicsDeviceType.Null,
                "Li Zhiyan actor-composed capture requires a real graphics backend; " +
                "do not run Unity with -nographics");

            string outputDirectory = RepositoryAbsolute(OutputDirectoryRelativePath);
            string manifestPath = Path.Combine(outputDirectory, ManifestFileName);
            string baselinePath = RepositoryAbsolute(BaselineManifestRelativePath);
            string baselineHash = ReadRequiredHash(baselinePath, "baseline manifest");
            try
            {
                ValidateSourceSpec();
                RetailOracle oracle = LoadRetailOracle();
                GameObject actorPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(ActorPrefabPath);
                Require(actorPrefab != null, "Li Zhiyan actor prefab is missing: " + ActorPrefabPath);
                GameObject[] effectPrefabs = LoadEffectPrefabs();
                GameObject[] peakEffectPrefabs = LoadPeakEffectPrefabs();
                GameObject fingerEffectPrefab = LoadFingerEffectPrefab();
                AnimationClip actorClip = AssetDatabase.LoadAssetAtPath<AnimationClip>(ActorClipPath);
                Require(actorClip != null, "Li Zhiyan actor clip is missing: " + ActorClipPath);
                CharacterRecoveryPresentationProfile profile =
                    AssetDatabase.LoadAssetAtPath<CharacterRecoveryPresentationProfile>(ProfilePath);
                ValidateActorClipAndProfile(actorClip, profile);

                Directory.CreateDirectory(outputDirectory);
                DeletePreviousCaptureFiles(outputDirectory);

                Scene previousScene = SceneManager.GetActiveScene();
                Scene captureScene = EditorSceneManager.NewScene(
                    NewSceneSetup.EmptyScene, NewSceneMode.Single);
                ActorBundle bundle = null;
                GameObject cameraObject = null;
                RenderTexture target = null;
                Texture2D readback = null;
                float priorSceneMvReady =
                    Shader.GetGlobalFloat("_EndfieldSceneMVMRTReady");
                float priorVfxGlobalsReady =
                    Shader.GetGlobalFloat("_EndfieldRecoveredVFXGlobalsReady");
                float priorVfxSoftDepthReady =
                    Shader.GetGlobalFloat("_EndfieldRecoveredVFXSoftDepthReady");
                Vector4 priorExposureParams = Shader.GetGlobalVector("_ExposureParams");
                try
                {
                    Shader.SetGlobalFloat("_EndfieldSceneMVMRTReady", 1f);
                    Shader.SetGlobalFloat("_EndfieldRecoveredVFXGlobalsReady", 1f);
                    // Start each diagnostic camera render fail-closed; the
                    // HGCompat source-depth route replaces this with 1 only
                    // after binding the real primary scene-depth SRV.
                    Shader.SetGlobalFloat("_EndfieldRecoveredVFXSoftDepthReady", 0f);
                    Shader.SetGlobalVector(
                        "_ExposureParams", new Vector4(1f, 0f, 0f, 0f));
                    bundle = InstantiateBundle(
                        actorPrefab, effectPrefabs, peakEffectPrefabs, fingerEffectPrefab,
                        actorClip, captureScene);
                    ValidateEffectContracts(bundle);
                    Camera camera = CreateSourceCamera(bundle.actor.transform, profile, out cameraObject);
                    target = CreateTarget();
                    readback = new Texture2D(
                        Width, Height, TextureFormat.RGBA32, false, false);

                    ActorComposedManifest manifest = new ActorComposedManifest
                    {
                        schema = ExpectedManifestSchema,
                        status = "diagnostic_only",
                        visibleAdmission = false,
                        eventOriginProven = false,
                        nativeRendererIdentityProven = false,
                        rendererFingerprintWitnessBoundary =
                            "single_capture_session_before_camera_render_sharedmaterials_only; actor_hierarchy_runtime_ids_and_skinned_palette_hash; static_effect_source_pathids_and_runtime_ids; peak_source_pathids_source_particle_ids_and_runtime_proxy_ids; finger_source_pathids_source_particle_ids_and_runtime_proxy_ids; no_retail_hgmesh_identity_or_draw_proof",
                        captureInvocationSerialBoundary =
                            "harness_monotonic_serial_one_per_camera_render; 168_invocations_for_24_anchors_times_7_lanes; independent_of_unity_frame_count; no_native_frame_or_command_buffer_identity",
                        actorAnimationRetailAbiEquivalent = false,
                        comparesRetailPixels = false,
                        retailHashEquality = false,
                        sourceActorPrefab = ActorPrefabPath,
                        sourceActorClip = ActorClipPath,
                        sourceProfile = ProfilePath,
                        sourceEffectPrefabs = new[]
                        {
                            Start01PrefabPath, Start02PrefabPath, Start03PrefabPath,
                        },
                        sourcePeakParticleContract =
                            EndfieldLiZhiyanOverviewPeakParticleEffectImporter.ContractPath,
                        sourcePeakParticleContractSha256 = Sha256File(ProjectAbsolute(
                            EndfieldLiZhiyanOverviewPeakParticleEffectImporter.ContractPath)),
                        sourcePeakParticlePrefabs = PeakEffectRoots.Select(
                            EndfieldLiZhiyanOverviewPeakParticleEffectImporter.PrefabPath).ToArray(),
                        sourceFingerEffectContract = FingerEffectContractPath,
                        sourceFingerEffectContractSha256 = Sha256File(ProjectAbsolute(FingerEffectContractPath)),
                        sourceFingerEffectPrefab = FingerEffectPrefabPath,
                        fingerEffectMount = FingerMountHierarchy,
                        fingerEffectDelaySeconds = FingerEffectDelaySeconds,
                        fingerEffectDurationSeconds = FingerEffectDurationSeconds,
                        manualPeakParticleSimulation = true,
                        peakParticleSimulationMode =
                            "each_particle_system_simulate_local_time_with_children_false_restart_true_fixed_time_then_play_without_time_advance_for_renderer_submission",
                        peakParticleMaterialMode =
                            "diagnostic_vfxbasev2_sample_stack_source_queue_soft_blend_disabled",
                        fingerParticleSimulationMode =
                            "exact_source_effect_delay_duration_under_Bip001_R_Finger2Nub; each_particle_system_simulate_effect_local_time_with_children_false_restart_true_fixed_time_then_play_without_time_advance_for_renderer_submission",
                        fingerParticleMaterialMode =
                            "transient_vfxbasev2_sample_stack_with_contract_payload_and_converted_pngs_source_queue_3700_soft_blend_authored_state_preserved_source_scene_depth_gate; generated_finger_materials_remain_fail_closed",
                        peakParticleBatchmodeTransport =
                            "unity_particle_renderer_paused_buffer_bakemesh_billboard_proxy",
                        sourceSpec = SpecPath,
                        sourceSpecSha256 = Sha256File(ProjectAbsolute(SpecPath)),
                        retailOracle = RetailOraclePath,
                        retailOracleSha256 = Sha256File(ProjectAbsolute(RetailOraclePath)),
                        baselineManifest = BaselineManifestRelativePath,
                        baselineManifestSha256 = baselineHash,
                        baselinePreserved = true,
                        outputDirectory = OutputDirectoryRelativePath,
                        width = Width,
                        height = Height,
                        backgroundRgba = new[] { 0, 0, 0, 0 },
                        backgroundMeasurement =
                            "closest_pair_of_four_frame_corners_actor_safe",
                        graphicsDeviceType = SystemInfo.graphicsDeviceType.ToString(),
                        graphicsDeviceName = SystemInfo.graphicsDeviceName,
                        cameraMode = "source_recovered_profile_position_lookat_fields",
                        cameraRotationMode =
                            "hierarchy_derived_look_rotation_inferred_runtime_gyro_missing",
                        cameraPosition = ToArray(profile.cameraPosition),
                        lookAtPosition = ToArray(profile.lookAtPosition),
                        fieldOfView = profile.fieldOfView,
                        nearClip = profile.nearClip,
                        farClip = profile.farClip,
                        referenceAspect = profile.referenceAspect,
                        authoredOverviewRotation = ToArray(profile.authoredOverviewRotation),
                        diagnosticCaptureRenderQueue = DiagnosticCaptureRenderQueue,
                        sourceMaterialRenderQueue = DiagnosticCaptureRenderQueue,
                        renderQueueOverrideReason = "diagnostic_queue_3704_preserved_from_effect_contract",
                        softBlendOverride = "disabled_no_retail_scene_depth",
                        effectAttachment = "actor_root_local_identity_source_root_mounted",
                        retailComparison = "predicate_roi_metrics_only_no_pixel_equality",
                        retailRestartCandidatePts = CandidateRestartPts,
                        localTimeMapping = "localSeconds=(retailPts-37967)/1000",
                        actorClipName = actorClip.name,
                        actorClipLengthSeconds = actorClip.length,
                        sharedClipName = SharedClipName,
                        sharedClipPathId = SharedClipPathId,
                        sharedClipStopTimeSeconds = SharedClipStopTime,
                        materialCurveSampling =
                            "AnimationUtility.GetEditorCurve classID23 material.*; " +
                            "SampleAnimation MPB preserved; evaluated values mirrored " +
                            "to cloned diagnostic Materials and MPBs; no AnimationMode; " +
                            "renderer-ID sidecar geometry remains source-static ownership",
                        roots = BuildRootManifestRows(),
                        captures = new ActorComposedCaptureRecord[Anchors.Length],
                    };

                    long nextCaptureInvocationSerial = 1;
                    for (int anchorIndex = 0; anchorIndex < Anchors.Length; anchorIndex++)
                    {
                        CaptureAnchor anchor = Anchors[anchorIndex];
                        float localSeconds = anchor.localSeconds;
                        SampleBundle(bundle, camera, localSeconds);
                        RetailSample oracleSample = FindOracleSample(oracle, anchor.retailPts);
                        ActorComposedCaptureRecord capture = new ActorComposedCaptureRecord
                        {
                            retailPts = anchor.retailPts,
                            timeBase = "1/1000",
                            localSeconds = localSeconds,
                            phase = anchor.phase,
                            actorActive = IsActorActive(bundle, localSeconds),
                            actorClipSampleSeconds = ActorClipSampleTime(bundle, localSeconds),
                            actorClipClampedAfterEnd = localSeconds > actorClip.length,
                            effectsAllInactive = !AnyEffectActive(localSeconds),
                            peakParticleAliveCount = CountPeakParticles(bundle),
                            peakParticleColorSamples =
                                BuildPeakParticleColorSamples(bundle, localSeconds),
                        };

                        ConfigureVisibility(bundle, localSeconds, true, -1);
                        capture.rendererFingerprintWitness =
                            CaptureRendererFingerprintWitness(bundle);
                        capture.composite = CaptureNamedFrame(
                            camera, target, readback, outputDirectory,
                            "composite_" + Pts(anchor.retailPts) + ".png", oracleSample,
                            ref nextCaptureInvocationSerial);
                        ConfigureVisibility(bundle, localSeconds, false, -2);
                        capture.actorOnly = CaptureNamedFrame(
                            camera, target, readback, outputDirectory,
                            "actor_only_" + Pts(anchor.retailPts) + ".png", oracleSample,
                            ref nextCaptureInvocationSerial);
                        ConfigureVisibility(bundle, localSeconds, false, -3);
                        capture.effectsOnly = CaptureNamedFrame(
                            camera, target, readback, outputDirectory,
                            "effects_only_" + Pts(anchor.retailPts) + ".png", oracleSample,
                            ref nextCaptureInvocationSerial);
                        ConfigureVisibility(bundle, localSeconds, false, -4);
                        capture.peakParticlesOnly = CaptureNamedFrame(
                            camera, target, readback, outputDirectory,
                            "peak_particles_only_" + Pts(anchor.retailPts) + ".png", oracleSample,
                            ref nextCaptureInvocationSerial);

                        capture.roots = new RootCaptureRecord[Roots.Length];
                        for (int rootIndex = 0; rootIndex < Roots.Length; rootIndex++)
                        {
                            ConfigureVisibility(bundle, localSeconds, false, rootIndex);
                            bool rootActive = IsEffectActive(Roots[rootIndex], localSeconds);
                            MaterialCurveSample materialCurveSample = rootActive
                                ? bundle.materialCurveSamples[rootIndex]
                                : MaterialCurveSample.Inactive(
                                    bundle.materialCurveSamplers[rootIndex].BindingCount);
                            string fileName = Roots[rootIndex].key + "_only_" +
                                Pts(anchor.retailPts) + ".png";
                            capture.roots[rootIndex] = new RootCaptureRecord
                            {
                                key = Roots[rootIndex].key,
                                effectRoot = Roots[rootIndex].effectRoot,
                                effectActive = rootActive,
                                effectState = StateFor(Roots[rootIndex], localSeconds),
                                clipSampleSeconds = ClipSampleTime(localSeconds),
                                clipClampedAfterEnd = localSeconds > SharedClipStopTime,
                                materialCurveSample = materialCurveSample,
                                frame = CaptureNamedFrame(
                                    camera, target, readback, outputDirectory,
                                    fileName, oracleSample,
                                    ref nextCaptureInvocationSerial),
                            };
                        }

                        capture.roiComparisons = BuildRoiComparisons(
                            oracleSample, capture.composite, capture.actorOnly,
                            capture.effectsOnly);
                        manifest.captures[anchorIndex] = capture;
                    }

                    File.WriteAllText(
                        manifestPath,
                        JsonUtility.ToJson(manifest, true) + Environment.NewLine,
                        new UTF8Encoding(false));
                }
                finally
                {
                    Shader.SetGlobalFloat(
                        "_EndfieldSceneMVMRTReady", priorSceneMvReady);
                    Shader.SetGlobalFloat(
                        "_EndfieldRecoveredVFXGlobalsReady", priorVfxGlobalsReady);
                    Shader.SetGlobalFloat(
                        "_EndfieldRecoveredVFXSoftDepthReady", priorVfxSoftDepthReady);
                    Shader.SetGlobalVector("_ExposureParams", priorExposureParams);
                    Release(readback);
                    Release(target);
                    if (cameraObject != null)
                        UnityEngine.Object.DestroyImmediate(cameraObject);
                    if (bundle != null)
                        bundle.Release();
                    if (captureScene.IsValid())
                        EditorSceneManager.CloseScene(captureScene, true);
                    if (previousScene.IsValid())
                        SceneManager.SetActiveScene(previousScene);
                }

                Require(ReadRequiredHash(baselinePath, "baseline manifest") == baselineHash,
                    "Baseline manifest changed during actor-composed capture");
                ValidateManifest(manifestPath);
                Debug.Log(
                    "[Endfield Li Zhiyan] actor-composed diagnostic capture complete: " +
                    manifestPath + "; visibleAdmission=false; comparesRetailPixels=false.");
            }
            catch (Exception exception)
            {
                Debug.LogError("[Endfield Li Zhiyan] actor-composed capture failed: " + exception);
                throw;
            }
        }

        [MenuItem("Endfield/Character Recovery Lab/Validate Li Zhiyan Actor-Composed Visual Capture")]
        public static void ValidateCommandLine()
        {
            ValidateSourceSpec();
            LoadRetailOracle();
            ValidateManifest(Path.Combine(
                RepositoryAbsolute(OutputDirectoryRelativePath), ManifestFileName));
            Debug.Log(
                "[Endfield Li Zhiyan] actor-composed manifest validated; " +
                "visibleAdmission=false; comparesRetailPixels=false.");
        }

        private static ActorBundle InstantiateBundle(
            GameObject actorPrefab,
            GameObject[] effectPrefabs,
            GameObject[] peakEffectPrefabs,
            GameObject fingerEffectPrefab,
            AnimationClip actorClip,
            Scene captureScene)
        {
            GameObject actor = PrefabUtility.InstantiatePrefab(actorPrefab, captureScene) as GameObject;
            Require(actor != null, "Could not instantiate Li Zhiyan actor prefab");
            actor.name = "LiZhiyanActorComposedDiagnosticCaptureActor";
            actor.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
            actor.transform.localScale = Vector3.one;

            Animation animation = actor.GetComponent<Animation>();
            if (animation == null)
                animation = actor.GetComponentInChildren<Animation>(true);
            Require(animation != null, "Lizhiyan.prefab has no legacy Animation component");
            animation.Stop();
            animation.enabled = false;

            Renderer[] actorRenderers = actor.GetComponentsInChildren<Renderer>(true);
            Require(actorRenderers.Length > 0, "Lizhiyan actor has no renderers");
            Require(actor.transform.Find("Root/Bip001") != null,
                "Lizhiyan actor hierarchy is missing Root/Bip001");

            ActorBundle bundle = new ActorBundle
            {
                actor = actor,
                actorClip = actorClip,
                actorRenderers = actorRenderers,
                effects = new GameObject[Roots.Length],
                markers = new EndfieldRecoveredStaticMeshEffectSource[Roots.Length],
                materialCurveSamplers = new EndfieldLiZhiyanMaterialCurveSampler[Roots.Length],
                materialCurveSamples = new MaterialCurveSample[Roots.Length],
                peakEffects = new GameObject[PeakEffectRoots.Length],
                peakMarkers = new EndfieldRecoveredParticleEffectSource[PeakEffectRoots.Length],
                peakBakeProxies = new List<PeakBakeProxy>(),
                fingerBakeProxies = new List<FingerBakeProxy>(),
                fingerDiagnosticMaterials = new List<Material>(),
                fingerDiagnosticTextures = new List<Texture2D>(),
            };

            for (int index = 0; index < Roots.Length; index++)
            {
                GameObject effect = PrefabUtility.InstantiatePrefab(
                    effectPrefabs[index], captureScene) as GameObject;
                Require(effect != null, "Could not instantiate effect prefab: " +
                    Roots[index].prefabPath);
                effect.name = "LiZhiyan" + Roots[index].key + "ActorComposedEffect";
                effect.transform.SetParent(actor.transform, false);
                effect.transform.localPosition = Vector3.zero;
                effect.transform.localRotation = Quaternion.identity;
                effect.transform.localScale = Vector3.one;
                EndfieldRecoveredStaticMeshEffectSource marker =
                    effect.GetComponent<EndfieldRecoveredStaticMeshEffectSource>();
                Require(marker != null, "Effect marker is missing: " + Roots[index].key);
                bundle.effects[index] = effect;
                bundle.markers[index] = marker;
                DisableAutonomousPlayback(effect);
                CloneDiagnosticMaterials(effect, Roots[index]);
                bundle.materialCurveSamplers[index] =
                    EndfieldLiZhiyanMaterialCurveSampler.Build(
                        effect, marker.sourceStartAnimationClip);
                Require(bundle.materialCurveSamplers[index].BindingCount > 0,
                    "No material AnimationClip curves resolved for " + Roots[index].key);
            }
            for (int index = 0; index < PeakEffectRoots.Length; index++)
            {
                GameObject effect = PrefabUtility.InstantiatePrefab(
                    peakEffectPrefabs[index], captureScene) as GameObject;
                Require(effect != null, "Could not instantiate peak particle prefab: " +
                    PeakEffectRoots[index]);
                effect.name = PeakEffectRoots[index];
                effect.transform.SetParent(actor.transform, false);
                effect.transform.localPosition = Vector3.zero;
                effect.transform.localRotation = Quaternion.identity;
                effect.transform.localScale = Vector3.one;
                EndfieldRecoveredParticleEffectSource marker =
                    effect.GetComponent<EndfieldRecoveredParticleEffectSource>();
                Require(marker != null && marker.effectRoot == PeakEffectRoots[index],
                    "Peak particle marker identity drifted");
                DisablePeakAutonomousPlayback(effect);
                ApplyPeakDiagnosticMaterials(effect, marker);
                bundle.peakEffects[index] = effect;
                bundle.peakMarkers[index] = marker;
                foreach (ParticleSystemRenderer sourceRenderer in
                    effect.GetComponentsInChildren<ParticleSystemRenderer>(true))
                {
                    EndfieldRecoveredParticleNodeSource sourceNode =
                        marker.particleNodes.Single(node =>
                            FindHierarchy(effect.transform, node.hierarchy) ==
                            sourceRenderer.transform);
                    GameObject proxyObject = new GameObject(
                        sourceRenderer.gameObject.name + ".PeakBatchmodeBakeProxy");
                    SceneManager.MoveGameObjectToScene(proxyObject, captureScene);
                    MeshFilter filter = proxyObject.AddComponent<MeshFilter>();
                    MeshRenderer proxyRenderer = proxyObject.AddComponent<MeshRenderer>();
                    Mesh mesh = new Mesh
                    {
                        name = sourceRenderer.gameObject.name + ".PeakBakedParticles",
                    };
                    filter.sharedMesh = mesh;
                    proxyRenderer.sharedMaterials = sourceRenderer.sharedMaterials;
                    proxyRenderer.enabled = false;
                    sourceRenderer.enabled = false;
                    bundle.peakBakeProxies.Add(new PeakBakeProxy
                    {
                        rootIndex = index,
                        system = sourceRenderer.GetComponent<ParticleSystem>(),
                        sourceRenderer = sourceRenderer,
                        sourceNode = sourceNode,
                        proxyObject = proxyObject,
                        proxyRenderer = proxyRenderer,
                        mesh = mesh,
                    });
                }
            }
            bundle.fingerEffect = PrefabUtility.InstantiatePrefab(
                fingerEffectPrefab, captureScene) as GameObject;
            Require(bundle.fingerEffect != null,
                "Could not instantiate exact finger effect prefab: " + FingerEffectPrefabPath);
            Transform[] fingerMounts = actor.GetComponentsInChildren<Transform>(true)
                .Where(value => value.name == FingerMountHierarchy).ToArray();
            Require(fingerMounts.Length == 1,
                "Li Zhiyan actor exact finger mount census drifted: " + fingerMounts.Length);
            Transform fingerMount = fingerMounts[0];
            Require(fingerMount != null, "Li Zhiyan actor is missing exact finger mount: " +
                FingerMountHierarchy);
            bundle.fingerEffect.transform.SetParent(fingerMount, false);
            bundle.fingerEffect.transform.localPosition = Vector3.zero;
            bundle.fingerEffect.transform.localRotation = Quaternion.identity;
            bundle.fingerEffect.transform.localScale = Vector3.one;
            bundle.fingerMarker = bundle.fingerEffect.GetComponent<EndfieldRecoveredParticleEffectSource>();
            Require(bundle.fingerMarker != null &&
                bundle.fingerMarker.effectRoot == "P_fxui_lizhiyan_overview_trails_Bip001_R_Finger2Nub" &&
                bundle.fingerMarker.particleNodes != null &&
                bundle.fingerMarker.particleNodes.Length == 7 &&
                Mathf.Abs(bundle.fingerMarker.sourceEffectDelay - FingerEffectDelaySeconds) < 0.00001f &&
                Mathf.Abs(bundle.fingerMarker.sourceEffectDuration - FingerEffectDurationSeconds) < 0.00001f,
                "Exact finger effect source contract drifted");
            DisablePeakAutonomousPlayback(bundle.fingerEffect);
            ApplyFingerDiagnosticMaterials(bundle);
            foreach (ParticleSystemRenderer sourceRenderer in
                bundle.fingerEffect.GetComponentsInChildren<ParticleSystemRenderer>(true))
            {
                EndfieldRecoveredParticleNodeSource sourceNode = bundle.fingerMarker.particleNodes.Single(
                    node => FindHierarchy(bundle.fingerEffect.transform, node.hierarchy) ==
                        sourceRenderer.transform);
                GameObject proxyObject = new GameObject(
                    sourceRenderer.gameObject.name + ".FingerBatchmodeBakeProxy");
                SceneManager.MoveGameObjectToScene(proxyObject, captureScene);
                MeshFilter filter = proxyObject.AddComponent<MeshFilter>();
                MeshRenderer proxyRenderer = proxyObject.AddComponent<MeshRenderer>();
                Mesh mesh = new Mesh
                {
                    name = sourceRenderer.gameObject.name + ".FingerBakedParticles",
                };
                filter.sharedMesh = mesh;
                proxyRenderer.sharedMaterials = sourceRenderer.sharedMaterials;
                proxyRenderer.enabled = false;
                sourceRenderer.enabled = false;
                bundle.fingerBakeProxies.Add(new FingerBakeProxy
                {
                    system = sourceRenderer.GetComponent<ParticleSystem>(),
                    sourceRenderer = sourceRenderer,
                    sourceNode = sourceNode,
                    proxyObject = proxyObject,
                    proxyRenderer = proxyRenderer,
                    mesh = mesh,
                });
            }
            return bundle;
        }

        private static void DisablePeakAutonomousPlayback(GameObject root)
        {
            foreach (ParticleSystem system in root.GetComponentsInChildren<ParticleSystem>(true))
            {
                ParticleSystem.MainModule main = system.main;
                main.playOnAwake = false;
                system.Stop(false, ParticleSystemStopBehavior.StopEmittingAndClear);
            }
        }

        private static void ApplyPeakDiagnosticMaterials(
            GameObject root,
            EndfieldRecoveredParticleEffectSource marker)
        {
            foreach (EndfieldRecoveredParticleNodeSource node in marker.particleNodes)
            {
                Transform host = FindHierarchy(root.transform, node.hierarchy);
                Require(host != null, "Peak particle hierarchy is missing: " + node.hierarchy);
                ParticleSystemRenderer renderer = host.GetComponent<ParticleSystemRenderer>();
                Require(renderer != null && renderer.sharedMaterials.Length == node.materialPathIds.Length,
                    "Peak particle material census drifted: " + node.hierarchy);
                Material[] replacements = new Material[node.materialPathIds.Length];
                for (int index = 0; index < replacements.Length; index++)
                {
                    Material source = renderer.sharedMaterials[index];
                    string path = EndfieldLiZhiyanOverviewPeakParticleEffectImporter.DiagnosticMaterialPath(
                        source.name, node.materialPathIds[index]);
                    replacements[index] = AssetDatabase.LoadAssetAtPath<Material>(path);
                    Require(replacements[index] != null,
                        "Peak diagnostic material is missing: " + path);
                }
                renderer.sharedMaterials = replacements;
            }
        }

        private static void ApplyFingerDiagnosticMaterials(ActorBundle bundle)
        {
            string absoluteContract = ProjectAbsolute(FingerEffectContractPath);
            Require(File.Exists(absoluteContract), "Exact finger effect contract is missing: " +
                absoluteContract);
            Dictionary<string, object> contract = AsDictionary(ManifestMiniJson.Deserialize(
                File.ReadAllText(absoluteContract, Encoding.UTF8)), "finger contract");
            Dictionary<string, object> dependency = AsDictionary(
                contract["textureDependencyBoundary"], "finger texture dependency boundary");
            var context = new EndfieldZhuangfyParticleEffectImporter.Context();
            foreach (object item in AsList(dependency["textures"], "finger textures"))
            {
                Dictionary<string, object> row = AsDictionary(item, "finger texture row");
                long pathId = AsLong(row["pathID"]);
                Dictionary<string, object> converted = AsDictionary(
                    row["convertedPng"], "finger converted texture " + pathId);
                string repositoryPath = RepositoryAbsolute(AsString(converted["path"]));
                Require(File.Exists(repositoryPath), "Exact finger texture PNG is missing: " +
                    repositoryPath);
                Texture2D texture = new Texture2D(2, 2, TextureFormat.RGBA32, false, false)
                {
                    name = AsString(row["name"]) + ".TransientDiagnostic",
                    hideFlags = HideFlags.HideAndDontSave,
                };
                Require(texture.LoadImage(File.ReadAllBytes(repositoryPath), true),
                    "Could not decode exact finger texture: " + repositoryPath);
                context.textures[pathId] = texture;
                bundle.fingerDiagnosticTextures.Add(texture);
            }
            Shader diagnosticShader = Shader.Find("Endfield/Recovered/VFXBaseV2SampleStack");
            Require(diagnosticShader != null, "Missing diagnostic VFXBaseV2 SampleStack shader");
            var materials = new Dictionary<long, Material>();
            foreach (object item in AsList(contract["materials"], "finger materials"))
            {
                Dictionary<string, object> row = AsDictionary(item, "finger material row");
                long pathId = AsLong(row["pathID"]);
                Material material = new Material(diagnosticShader)
                {
                    name = AsString(row["name"]) + ".DiagnosticSampleStack",
                    renderQueue = AsInt(row["customRenderQueue"]),
                    hideFlags = HideFlags.HideAndDontSave,
                };
                EndfieldZhuangfyParticleEffectImporter.ApplyRecoveredMaterialPayload(
                    material, AsDictionary(row["payload"], "finger material payload"), context);
                material.renderQueue = AsInt(row["customRenderQueue"]);
                materials.Add(pathId, material);
                bundle.fingerDiagnosticMaterials.Add(material);
            }
            foreach (EndfieldRecoveredParticleNodeSource node in bundle.fingerMarker.particleNodes)
            {
                Transform host = FindHierarchy(bundle.fingerEffect.transform, node.hierarchy);
                Require(host != null, "Exact finger particle hierarchy is missing: " + node.hierarchy);
                ParticleSystemRenderer renderer = host.GetComponent<ParticleSystemRenderer>();
                Require(renderer != null && renderer.sharedMaterials.Length == node.materialPathIds.Length,
                    "Exact finger material census drifted: " + node.hierarchy);
                Material[] replacements = new Material[node.materialPathIds.Length];
                for (int index = 0; index < replacements.Length; index++)
                {
                    Require(materials.TryGetValue(node.materialPathIds[index], out Material material),
                        "Exact finger material PathID is unresolved: " + node.materialPathIds[index]);
                    replacements[index] = material;
                }
                renderer.sharedMaterials = replacements;
            }
        }

        private static Dictionary<string, object> AsDictionary(object value, string context)
        {
            var result = value as Dictionary<string, object>;
            Require(result != null, "Expected JSON object for " + context);
            return result;
        }

        private static IList AsList(object value, string context)
        {
            var result = value as IList;
            Require(result != null, "Expected JSON array for " + context);
            return result;
        }

        private static long AsLong(object value)
        {
            return Convert.ToInt64(value, CultureInfo.InvariantCulture);
        }

        private static int AsInt(object value)
        {
            return Convert.ToInt32(value, CultureInfo.InvariantCulture);
        }

        private static string AsString(object value)
        {
            return Convert.ToString(value, CultureInfo.InvariantCulture);
        }

        private static Transform FindHierarchy(Transform root, string hierarchy)
        {
            string[] parts = hierarchy.Split('/');
            Require(parts.Length > 0 && parts[0] == root.name,
                "Peak hierarchy root drifted: " + hierarchy);
            Transform cursor = root;
            for (int index = 1; index < parts.Length && cursor != null; index++)
                cursor = cursor.Find(parts[index]);
            return cursor;
        }

        private static void DisableAutonomousPlayback(GameObject root)
        {
            Animation[] animations = root.GetComponentsInChildren<Animation>(true);
            for (int index = 0; index < animations.Length; index++)
            {
                animations[index].Stop();
                animations[index].enabled = false;
            }
            EndfieldLiZhiyanBehavioralAnimationSimulation simulation =
                root.GetComponent<EndfieldLiZhiyanBehavioralAnimationSimulation>();
            if (simulation != null)
                simulation.enabled = false;
            ParticleSystem[] particles = root.GetComponentsInChildren<ParticleSystem>(true);
            Require(particles.Length == 0,
                "Static Li Zhiyan effect unexpectedly contains ParticleSystems: " + root.name);
        }

        private static void CloneDiagnosticMaterials(GameObject root, RootDefinition definition)
        {
            MeshRenderer[] renderers = root.GetComponentsInChildren<MeshRenderer>(true);
            Require(renderers.Length > 0, "Effect has no MeshRenderer: " + definition.effectRoot);
            for (int rendererIndex = 0; rendererIndex < renderers.Length; rendererIndex++)
            {
                Material[] source = renderers[rendererIndex].sharedMaterials;
                Material[] instances = new Material[source.Length];
                for (int materialIndex = 0; materialIndex < source.Length; materialIndex++)
                {
                    Require(source[materialIndex] != null,
                        "Effect has a missing material: " + definition.effectRoot);
                    instances[materialIndex] = new Material(source[materialIndex])
                    {
                        name = source[materialIndex].name + ".LiZhiyanActorComposedInstance",
                        renderQueue = DiagnosticCaptureRenderQueue,
                    };
                    if (instances[materialIndex].HasProperty("_UseSoftBlend"))
                        instances[materialIndex].SetFloat("_UseSoftBlend", 0f);
                }
                renderers[rendererIndex].sharedMaterials = instances;
            }
        }

        private static void SampleBundle(
            ActorBundle bundle, Camera camera, float localSeconds)
        {
            bool actorActive = IsActorActive(bundle, localSeconds);
            bundle.actor.SetActive(actorActive);
            for (int index = 0; index < Roots.Length; index++)
            {
                bool active = actorActive && IsEffectActive(Roots[index], localSeconds);
                bundle.effects[index].SetActive(active);
            }
            if (!actorActive)
                return;

            bundle.actorClip.SampleAnimation(
                bundle.actor, ActorClipSampleTime(bundle, localSeconds));
            for (int index = 0; index < Roots.Length; index++)
            {
                if (!IsEffectActive(Roots[index], localSeconds))
                {
                    bundle.materialCurveSamples[index] = null;
                    continue;
                }
                bundle.markers[index].sourceStartAnimationClip.SampleAnimation(
                    bundle.effects[index], ClipSampleTime(localSeconds));
                bundle.materialCurveSamples[index] =
                    bundle.materialCurveSamplers[index].Apply(
                        ClipSampleTime(localSeconds));
            }
            for (int rootIndex = 0; rootIndex < bundle.peakEffects.Length; rootIndex++)
            {
                GameObject peak = bundle.peakEffects[rootIndex];
                EndfieldRecoveredParticleEffectSource marker =
                    bundle.peakMarkers[rootIndex];
                bool peakActive = actorActive && IsPeakEffectActive(marker, localSeconds);
                float peakLocalSeconds = localSeconds - marker.sourceEffectDelay;
                peak.SetActive(peakActive);
                foreach (ParticleSystem system in peak.GetComponentsInChildren<ParticleSystem>(true))
                {
                    system.Stop(false, ParticleSystemStopBehavior.StopEmittingAndClear);
                    if (peakActive)
                        system.Simulate(Mathf.Max(0f, peakLocalSeconds), false, true, true);
                    if (peakActive && system.particleCount > 0)
                        system.Play(false);
                }
            }
            bool fingerActive = actorActive && IsFingerEffectActive(localSeconds);
            bundle.fingerEffect.SetActive(fingerActive);
            foreach (Transform child in bundle.fingerEffect.GetComponentsInChildren<Transform>(true))
                if (child != bundle.fingerEffect.transform)
                    child.gameObject.SetActive(fingerActive);
            float fingerLocalSeconds = localSeconds - FingerEffectDelaySeconds;
            foreach (ParticleSystem system in
                bundle.fingerEffect.GetComponentsInChildren<ParticleSystem>(true))
            {
                system.Stop(false, ParticleSystemStopBehavior.StopEmittingAndClear);
                if (fingerActive)
                    system.Simulate(Mathf.Max(0f, fingerLocalSeconds), false, true, true);
                if (fingerActive && system.particleCount > 0)
                    system.Play(false);
            }
            foreach (PeakBakeProxy proxy in bundle.peakBakeProxies)
            {
                proxy.mesh.Clear();
                bool peakActive = actorActive && IsPeakEffectActive(
                    bundle.peakMarkers[proxy.rootIndex], localSeconds);
                if (peakActive && proxy.system.particleCount > 0)
                {
                    proxy.sourceRenderer.BakeMesh(
                        proxy.mesh,
                        camera,
                        ParticleSystemBakeMeshOptions.BakePosition |
                            ParticleSystemBakeMeshOptions.BakeRotationAndScale);
                }
                proxy.hasGeometry = proxy.mesh.vertexCount > 0;
            }
            foreach (FingerBakeProxy proxy in bundle.fingerBakeProxies)
            {
                proxy.mesh.Clear();
                if (fingerActive && proxy.system.particleCount > 0)
                {
                    proxy.sourceRenderer.BakeMesh(
                        proxy.mesh,
                        camera,
                        ParticleSystemBakeMeshOptions.BakePosition |
                            ParticleSystemBakeMeshOptions.BakeRotationAndScale);
                }
                proxy.hasGeometry = proxy.mesh.vertexCount > 0;
            }
        }

        private static void ConfigureVisibility(
            ActorBundle bundle,
            float localSeconds,
            bool composite,
            int effectSelection)
        {
            bool actorActive = IsActorActive(bundle, localSeconds);
            bundle.actor.SetActive(actorActive);
            SetActorRenderersEnabled(bundle.actorRenderers, actorActive &&
                (composite || effectSelection == -2));
            for (int index = 0; index < Roots.Length; index++)
            {
                bool active = actorActive && IsEffectActive(Roots[index], localSeconds);
                if (effectSelection >= 0)
                    active &= effectSelection == index;
                else if (effectSelection == -2)
                    active = false;
                else if (effectSelection == -4)
                    active = false;
                bundle.effects[index].SetActive(active);
            }
            for (int index = 0; index < bundle.peakEffects.Length; index++)
            {
                bool active = actorActive &&
                    IsPeakEffectActive(bundle.peakMarkers[index], localSeconds) &&
                    (composite || effectSelection == -3 || effectSelection == -4);
                bundle.peakEffects[index].SetActive(active);
            }
            foreach (PeakBakeProxy proxy in bundle.peakBakeProxies)
            {
                bool peakVisible = actorActive && IsPeakEffectActive(
                    bundle.peakMarkers[proxy.rootIndex], localSeconds) &&
                    (composite || effectSelection == -3 || effectSelection == -4);
                proxy.proxyRenderer.enabled = peakVisible && proxy.hasGeometry;
            }
            bool fingerVisible = actorActive && IsFingerEffectActive(localSeconds) &&
                (composite || effectSelection == -3);
            bundle.fingerEffect.SetActive(fingerVisible);
            foreach (FingerBakeProxy proxy in bundle.fingerBakeProxies)
                proxy.proxyRenderer.enabled = fingerVisible && proxy.hasGeometry;
        }

        private static bool IsFingerEffectActive(float localSeconds)
        {
            float fingerLocalSeconds = localSeconds - FingerEffectDelaySeconds;
            return fingerLocalSeconds >= -ActiveEndpointEpsilon &&
                fingerLocalSeconds <= FingerEffectDurationSeconds + ActiveEndpointEpsilon;
        }

        private static bool IsPeakEffectActive(
            EndfieldRecoveredParticleEffectSource marker,
            float localSeconds)
        {
            Require(marker != null, "Peak particle marker is missing");
            float peakLocalSeconds = localSeconds - marker.sourceEffectDelay;
            return peakLocalSeconds >= -ActiveEndpointEpsilon &&
                peakLocalSeconds <= marker.sourceEffectDuration + ActiveEndpointEpsilon;
        }

        private static PeakParticleColorSampleRecord[] BuildPeakParticleColorSamples(
            ActorBundle bundle,
            float localSeconds)
        {
            var rows = new List<PeakParticleColorSampleRecord>();
            foreach (PeakBakeProxy proxy in bundle.peakBakeProxies)
            {
                Color[] colors = proxy.mesh.colors;
                float alphaMin = 0f;
                float alphaMax = 0f;
                float alphaMean = 0f;
                if (colors.Length > 0)
                {
                    alphaMin = 1f;
                    double alphaSum = 0.0;
                    for (int index = 0; index < colors.Length; index++)
                    {
                        float alpha = colors[index].a;
                        alphaMin = Mathf.Min(alphaMin, alpha);
                        alphaMax = Mathf.Max(alphaMax, alpha);
                        alphaSum += alpha;
                    }
                    alphaMean = (float)(alphaSum / colors.Length);
                }
                EndfieldRecoveredParticleEffectSource marker =
                    bundle.peakMarkers[proxy.rootIndex];
                rows.Add(new PeakParticleColorSampleRecord
                {
                    effectRoot = marker.effectRoot,
                    sourceEffectDelay = marker.sourceEffectDelay,
                    sourceEffectDuration = marker.sourceEffectDuration,
                    effectLocalSeconds = localSeconds - marker.sourceEffectDelay,
                    effectActive = IsPeakEffectActive(marker, localSeconds),
                    hierarchy = proxy.sourceNode.hierarchy,
                    particleSystemPathId = proxy.sourceNode.particleSystemPathId,
                    particleRendererPathId = proxy.sourceNode.particleRendererPathId,
                    particleCount = proxy.system.particleCount,
                    bakedVertexCount = proxy.mesh.vertexCount,
                    bakedColorCount = colors.Length,
                    colorAlphaMin = alphaMin,
                    colorAlphaMax = alphaMax,
                    colorAlphaMean = alphaMean,
                });
            }
            return rows.ToArray();
        }

        private static int CountPeakParticles(ActorBundle bundle)
        {
            int count = 0;
            foreach (GameObject root in bundle.peakEffects)
                foreach (ParticleSystem system in root.GetComponentsInChildren<ParticleSystem>(true))
                    count += system.particleCount;
            return count;
        }

        private static RendererFingerprintRecord[] CaptureRendererFingerprintWitness(
            ActorBundle bundle)
        {
            var rows = new List<RendererFingerprintRecord>();
            for (int actorIndex = 0; actorIndex < bundle.actorRenderers.Length; actorIndex++)
            {
                Renderer renderer = bundle.actorRenderers[actorIndex];
                Mesh mesh = RendererMesh(renderer);
                RendererFingerprintRecord row = BuildRendererFingerprint(
                    "actor", "actor", RelativeHierarchy(bundle.actor.transform,
                        renderer.transform), 0L, Array.Empty<long>(), Array.Empty<long>(), renderer,
                    mesh, 0, 0);
                row.identityKey += ":" + actorIndex.ToString(
                    CultureInfo.InvariantCulture);
                rows.Add(row);
            }
            for (int rootIndex = 0; rootIndex < bundle.markers.Length; rootIndex++)
            {
                foreach (EndfieldRecoveredStaticMeshNodeSource node in
                    bundle.markers[rootIndex].staticMeshNodes)
                {
                    rows.Add(BuildRendererFingerprint(
                        "static_effect", Roots[rootIndex].key, node.hierarchy,
                        node.meshRendererPathId, new[] { node.meshPathId },
                        node.materialPathIds, node.generatedMeshRenderer,
                        RequiredStaticMesh(node), 0, 0));
                }
            }
            foreach (PeakBakeProxy proxy in bundle.peakBakeProxies)
            {
                Require(proxy != null && proxy.sourceNode != null &&
                    proxy.sourceRenderer != null && proxy.system != null &&
                    proxy.proxyRenderer != null && proxy.mesh != null,
                    "Peak fingerprint proxy source is incomplete");
                rows.Add(BuildRendererFingerprint(
                    "peak_particle_proxy", PeakEffectRoots[proxy.rootIndex],
                    proxy.sourceNode.hierarchy,
                    proxy.sourceNode.particleRendererPathId,
                    proxy.sourceNode.meshPathIds,
                    proxy.sourceNode.materialPathIds, proxy.proxyRenderer, proxy.mesh,
                    proxy.sourceRenderer.GetInstanceID(), proxy.system.GetInstanceID()));
            }
            foreach (FingerBakeProxy proxy in bundle.fingerBakeProxies)
            {
                Require(proxy != null && proxy.sourceNode != null &&
                    proxy.sourceRenderer != null && proxy.system != null &&
                    proxy.proxyRenderer != null && proxy.mesh != null,
                    "Exact finger fingerprint proxy source is incomplete");
                rows.Add(BuildRendererFingerprint(
                    "finger_particle_proxy", bundle.fingerMarker.effectRoot,
                    proxy.sourceNode.hierarchy,
                    proxy.sourceNode.particleRendererPathId,
                    proxy.sourceNode.meshPathIds,
                    proxy.sourceNode.materialPathIds, proxy.proxyRenderer, proxy.mesh,
                    proxy.sourceRenderer.GetInstanceID(), proxy.system.GetInstanceID()));
            }
            return rows.OrderBy(row => row.identityKey, StringComparer.Ordinal).ToArray();
        }

        private static RendererFingerprintRecord BuildRendererFingerprint(
            string role,
            string sourceRoot,
            string hierarchy,
            long sourceRendererPathId,
            long[] sourceMeshPathIds,
            long[] sourceMaterialPathIds,
            Renderer renderer,
            Mesh mesh,
            int sourceRendererInstanceId,
            int sourceParticleSystemInstanceId)
        {
            Require(renderer != null, "Fingerprint renderer is missing: " + hierarchy);
            Material[] materials = renderer.sharedMaterials;
            Require(role == "actor" || sourceMaterialPathIds != null &&
                sourceMaterialPathIds.Length == materials.Length,
                "Fingerprint source material census drifted: " + hierarchy);
            long[] normalizedSourceMaterialPathIds = sourceMaterialPathIds != null &&
                sourceMaterialPathIds.Length == materials.Length
                ? (long[])sourceMaterialPathIds.Clone()
                : new long[materials.Length];
            var materialRows = new MaterialFingerprintRecord[materials.Length];
            int skinnedBoneCount;
            string skinnedPoseSha256 = SkinnedPoseSha256(
                renderer as SkinnedMeshRenderer, out skinnedBoneCount);
            for (int index = 0; index < materials.Length; index++)
            {
                Material material = materials[index];
                Require(material != null, "Fingerprint material is missing: " + hierarchy);
                materialRows[index] = new MaterialFingerprintRecord
                {
                    slot = index,
                    sourceMaterialPathId = normalizedSourceMaterialPathIds[index],
                    unityMaterialInstanceId = material.GetInstanceID(),
                    name = material.name,
                    shaderName = material.shader != null ? material.shader.name : string.Empty,
                    renderQueue = material.renderQueue,
                };
            }
            return new RendererFingerprintRecord
            {
                identityKey = role + ":" + sourceRoot + ":" + hierarchy,
                role = role,
                sourceRoot = sourceRoot,
                hierarchy = hierarchy,
                sourceRendererPathId = sourceRendererPathId,
                sourceMeshPathIds = sourceMeshPathIds ?? Array.Empty<long>(),
                sourceMaterialPathIds = normalizedSourceMaterialPathIds,
                unityRendererInstanceId = renderer.GetInstanceID(),
                sourceRendererInstanceId = sourceRendererInstanceId,
                sourceParticleSystemInstanceId = sourceParticleSystemInstanceId,
                unityMeshInstanceId = mesh != null ? mesh.GetInstanceID() : 0,
                activeInHierarchy = renderer.gameObject.activeInHierarchy,
                rendererEnabled = renderer.enabled,
                meshVertexCount = mesh != null ? mesh.vertexCount : 0,
                meshSubMeshCount = mesh != null ? mesh.subMeshCount : 0,
                meshIndexCount = MeshIndexCount(mesh),
                localToWorldStateSha256 = MatrixSha256(renderer.localToWorldMatrix),
                skinnedBoneCount = skinnedBoneCount,
                skinnedPoseSha256 = skinnedPoseSha256,
                materials = materialRows,
            };
        }

        private static Mesh RendererMesh(Renderer renderer)
        {
            SkinnedMeshRenderer skinned = renderer as SkinnedMeshRenderer;
            if (skinned != null)
                return skinned.sharedMesh;
            MeshFilter filter = renderer.GetComponent<MeshFilter>();
            return filter != null ? filter.sharedMesh : null;
        }

        private static Mesh RequiredStaticMesh(EndfieldRecoveredStaticMeshNodeSource node)
        {
            Require(node != null && node.generatedMeshFilter != null &&
                node.generatedMeshRenderer != null &&
                node.generatedMeshFilter.sharedMesh != null,
                "Static fingerprint source is incomplete");
            return node.generatedMeshFilter.sharedMesh;
        }

        private static long MeshIndexCount(Mesh mesh)
        {
            if (mesh == null)
                return 0L;
            long total = 0L;
            for (int index = 0; index < mesh.subMeshCount; index++)
                total += mesh.GetIndexCount(index);
            return total;
        }

        private static string MatrixSha256(Matrix4x4 matrix)
        {
            byte[] bytes = new byte[16 * sizeof(float)];
            int offset = 0;
            for (int row = 0; row < 4; row++)
            {
                for (int column = 0; column < 4; column++)
                {
                    byte[] value = BitConverter.GetBytes(matrix[row, column]);
                    Buffer.BlockCopy(value, 0, bytes, offset, value.Length);
                    offset += value.Length;
                }
            }
            using (SHA256 digest = SHA256.Create())
            {
                return string.Concat(digest.ComputeHash(bytes).Select(
                    value => value.ToString("x2", CultureInfo.InvariantCulture)));
            }
        }

        private static string SkinnedPoseSha256(
            SkinnedMeshRenderer renderer,
            out int boneCount)
        {
            boneCount = 0;
            if (renderer == null || renderer.sharedMesh == null)
                return string.Empty;
            Transform[] bones = renderer.bones;
            Matrix4x4[] bindposes = renderer.sharedMesh.bindposes;
            Require(bones != null && bindposes != null &&
                bones.Length == bindposes.Length && bones.All(bone => bone != null),
                "Skinned fingerprint bone/bindpose census drifted: " + renderer.name);
            boneCount = bones.Length;
            byte[] bytes = new byte[boneCount * 16 * sizeof(float)];
            int offset = 0;
            Matrix4x4 worldToRenderer = renderer.transform.worldToLocalMatrix;
            for (int boneIndex = 0; boneIndex < boneCount; boneIndex++)
            {
                Matrix4x4 skinMatrix = worldToRenderer *
                    bones[boneIndex].localToWorldMatrix * bindposes[boneIndex];
                for (int row = 0; row < 4; row++)
                {
                    for (int column = 0; column < 4; column++)
                    {
                        byte[] value = BitConverter.GetBytes(skinMatrix[row, column]);
                        Buffer.BlockCopy(value, 0, bytes, offset, value.Length);
                        offset += value.Length;
                    }
                }
            }
            using (SHA256 digest = SHA256.Create())
            {
                return string.Concat(digest.ComputeHash(bytes).Select(
                    value => value.ToString("x2", CultureInfo.InvariantCulture)));
            }
        }

        private static string RelativeHierarchy(Transform root, Transform target)
        {
            if (target == root)
                return root.name;
            var parts = new List<string>();
            Transform cursor = target;
            while (cursor != null && cursor != root)
            {
                parts.Add(cursor.name);
                cursor = cursor.parent;
            }
            Require(cursor == root, "Fingerprint renderer is outside source root");
            parts.Reverse();
            return parts.Count == 0 ? "<root>" : string.Join("/", parts);
        }

        private static void SetActorRenderersEnabled(Renderer[] renderers, bool enabled)
        {
            for (int index = 0; index < renderers.Length; index++)
                renderers[index].enabled = enabled;
        }

        private static Camera CreateSourceCamera(
            Transform actorRoot,
            CharacterRecoveryPresentationProfile profile,
            out GameObject cameraObject)
        {
            cameraObject = new GameObject("LiZhiyanActorComposedDiagnosticCaptureCamera");
            Camera camera = cameraObject.AddComponent<Camera>();
            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = new Color(0f, 0f, 0f, 0f);
            camera.aspect = profile.referenceAspect;
            camera.fieldOfView = profile.fieldOfView;
            camera.nearClipPlane = profile.nearClip;
            camera.farClipPlane = profile.farClip;
            Vector3 position = actorRoot.TransformPoint(profile.cameraPosition);
            Vector3 lookAt = actorRoot.TransformPoint(profile.lookAtPosition);
            Vector3 direction = lookAt - position;
            Require(direction.sqrMagnitude > 0.000001f,
                "Source profile camera position and look-at are coincident");
            camera.transform.SetPositionAndRotation(
                position, Quaternion.LookRotation(direction.normalized, actorRoot.up));
            return camera;
        }

        private static RenderTexture CreateTarget()
        {
            RenderTexture target = new RenderTexture(
                Width, Height, 24, RenderTextureFormat.ARGB32)
            {
                name = "Li Zhiyan actor-composed diagnostic capture target",
                useMipMap = false,
                autoGenerateMips = false,
                antiAliasing = 1,
            };
            target.Create();
            Require(target.IsCreated(), "Could not create actor-composed capture RenderTexture");
            return target;
        }

        private static FrameRecord CaptureNamedFrame(
            Camera camera,
            RenderTexture target,
            Texture2D readback,
            string outputDirectory,
            string fileName,
            RetailSample oracleSample,
            ref long nextCaptureInvocationSerial)
        {
            string outputPath = Path.Combine(outputDirectory, fileName);
            long captureInvocationSerial = nextCaptureInvocationSerial++;
            RenderTexture previousTarget = camera.targetTexture;
            RenderTexture previousActive = RenderTexture.active;
            try
            {
                camera.targetTexture = target;
                RenderTexture.active = target;
                EndfieldRecoveredRendererIdSidecarCaptureBridge.Begin(
                    captureInvocationSerial);
                try
                {
                    camera.Render();
                }
                finally
                {
                    EndfieldRecoveredRendererIdSidecarCaptureBridge.End();
                }
                EndfieldRecoveredRendererIdSidecarCaptureBridge.WaitForReadback();
                readback.ReadPixels(new Rect(0, 0, Width, Height), 0, 0, false);
                readback.Apply(false, false);
                File.WriteAllBytes(outputPath, readback.EncodeToPNG());
            }
            finally
            {
                camera.targetTexture = previousTarget;
                RenderTexture.active = previousActive;
            }

            Color32[] pixels = readback.GetPixels32();
            Color32 background = SelectCornerConsensusBackground(pixels);
            int alphaPixels = 0;
            int nonBackgroundPixels = 0;
            for (int index = 0; index < pixels.Length; index++)
            {
                Color32 pixel = pixels[index];
                if (pixel.a > CoverageAlphaThreshold)
                    alphaPixels++;
                if (Mathf.Abs(pixel.r - background.r) > CoverageColorThreshold ||
                    Mathf.Abs(pixel.g - background.g) > CoverageColorThreshold ||
                    Mathf.Abs(pixel.b - background.b) > CoverageColorThreshold ||
                    Mathf.Abs(pixel.a - background.a) > CoverageAlphaThreshold)
                    nonBackgroundPixels++;
            }

            EndfieldRendererIdSidecarCapture sidecarCapture;
            bool sidecarAvailable =
                EndfieldRecoveredRendererIdSidecarCaptureBridge.TryTake(
                    captureInvocationSerial,
                    out sidecarCapture) &&
                sidecarCapture != null && sidecarCapture.available &&
                sidecarCapture.rgba != null;
            string sidecarRawPath = string.Empty;
            string sidecarDictionaryPath = string.Empty;
            long sidecarNonZeroPixelCount = 0;
            string sidecarFailure = sidecarCapture == null
                ? "no renderer-ID sidecar capture was published"
                : sidecarCapture.failure ?? string.Empty;
            long validatedSidecarNonZeroPixelCount = 0;
            RendererIdPixelSummary[] validatedSidecarPixelSummaries =
                Array.Empty<RendererIdPixelSummary>();
            if (sidecarAvailable)
            {
                string sidecarValidationFailure;
                if (!TryValidateRendererIdSidecarCapture(
                        sidecarCapture,
                        captureInvocationSerial,
                        out validatedSidecarNonZeroPixelCount,
                        out validatedSidecarPixelSummaries,
                        out sidecarValidationFailure))
                {
                    sidecarAvailable = false;
                    sidecarFailure = sidecarValidationFailure;
                }
            }
            if (sidecarAvailable)
            {
                string sidecarStem = Path.GetFileNameWithoutExtension(fileName) +
                    "_renderer_ids";
                sidecarRawPath = Path.Combine(outputDirectory, sidecarStem + ".raw");
                sidecarDictionaryPath = Path.Combine(
                    outputDirectory,
                    sidecarStem + ".json");
                byte[] sidecarBytes = new byte[
                    sidecarCapture.rgba.Length * sizeof(float)];
                Buffer.BlockCopy(
                    sidecarCapture.rgba,
                    0,
                    sidecarBytes,
                    0,
                    sidecarBytes.Length);
                File.WriteAllBytes(sidecarRawPath, sidecarBytes);
                File.WriteAllText(
                    sidecarDictionaryPath,
                    JsonUtility.ToJson(
                        new EndfieldRendererIdSidecarDictionary
                        {
                            redChannelIdScope =
                                EndfieldRecoveredRendererIdSidecarCaptureBridge
                                    .RedChannelIdScope,
                            entries = sidecarCapture.entries ??
                                Array.Empty<EndfieldRendererIdSidecarEntry>()
                        },
                        true),
                    new UTF8Encoding(false));
                sidecarNonZeroPixelCount = validatedSidecarNonZeroPixelCount;
                sidecarFailure = string.Empty;
            }

            return new FrameRecord
            {
                captureInvocationSerial = captureInvocationSerial,
                png = OutputDirectoryRelativePath + "/" + fileName,
                pngBytes = new FileInfo(outputPath).Length,
                pngSha256 = Sha256File(outputPath),
                width = Width,
                height = Height,
                alphaPixelCount = alphaPixels,
                alphaCoverage = (float)alphaPixels / pixels.Length,
                nonBackgroundPixelCount = nonBackgroundPixels,
                nonBackgroundCoverage = (float)nonBackgroundPixels / pixels.Length,
                measuredBackgroundRgba = new[]
                {
                    (int)background.r, (int)background.g,
                    (int)background.b, (int)background.a,
                },
                roiMeasurements = MeasureRois(pixels, oracleSample),
                rendererIdSidecarRedChannelIdScope =
                    EndfieldRecoveredRendererIdSidecarCaptureBridge.RedChannelIdScope,
                rendererIdSidecarAvailable = sidecarAvailable,
                rendererIdSidecarRaw = RelativeOutputPath(sidecarRawPath),
                rendererIdSidecarDictionary = RelativeOutputPath(sidecarDictionaryPath),
                rendererIdSidecarWidth = sidecarAvailable ? sidecarCapture.width : 0,
                rendererIdSidecarHeight = sidecarAvailable ? sidecarCapture.height : 0,
                rendererIdSidecarNonZeroPixelCount = sidecarNonZeroPixelCount,
                rendererIdSidecarPixelSummaries = sidecarAvailable
                    ? validatedSidecarPixelSummaries
                    : Array.Empty<RendererIdPixelSummary>(),
                rendererIdSidecarFailure = sidecarFailure,
            };
        }

        private static string RelativeOutputPath(string path)
        {
            return string.IsNullOrEmpty(path)
                ? string.Empty
                : OutputDirectoryRelativePath + "/" +
                    Path.GetFileName(path);
        }

        private static bool TryValidateRendererIdSidecarCapture(
            EndfieldRendererIdSidecarCapture capture,
            long expectedSerial,
            out long nonZeroPixelCount,
            out RendererIdPixelSummary[] pixelSummaries,
            out string failure)
        {
            nonZeroPixelCount = 0;
            pixelSummaries = Array.Empty<RendererIdPixelSummary>();
            failure = string.Empty;
            if (capture.captureInvocationSerial != expectedSerial)
            {
                failure = "renderer-ID sidecar capture serial does not match the PNG";
                return false;
            }
            if (!string.Equals(
                    capture.redChannelIdScope,
                    EndfieldRecoveredRendererIdSidecarCaptureBridge.RedChannelIdScope,
                    StringComparison.Ordinal))
            {
                failure =
                    "renderer-ID sidecar red-channel IDs are not explicitly " +
                    "captureInvocationSerial-local";
                return false;
            }
            if (capture.width <= 0 || capture.height <= 0)
            {
                failure = "renderer-ID sidecar dimensions are invalid";
                return false;
            }
            int expectedFloatCount = checked(capture.width * capture.height * 4);
            if (capture.rgba == null || capture.rgba.Length != expectedFloatCount)
            {
                failure = "renderer-ID sidecar RGBA32F raw length is not width*height*4";
                return false;
            }
            EndfieldRendererIdSidecarEntry[] entries = capture.entries ??
                Array.Empty<EndfieldRendererIdSidecarEntry>();
            var ids = new HashSet<int>();
            var entriesById = new Dictionary<int, EndfieldRendererIdSidecarEntry>();
            var stableRendererKeys = new HashSet<string>(StringComparer.Ordinal);
            for (int entryIndex = 0; entryIndex < entries.Length; entryIndex++)
            {
                EndfieldRendererIdSidecarEntry entry = entries[entryIndex];
                if (entry == null || entry.id != entryIndex + 1 ||
                    entry.id <= 0 || entry.id >= (1 << 24) ||
                    entry.rendererInstanceId == 0 ||
                    string.IsNullOrEmpty(entry.rendererPath) ||
                    string.IsNullOrEmpty(entry.rendererOrdinalPath) ||
                    entry.materialIndex < 0 ||
                    string.IsNullOrEmpty(entry.materialName) ||
                    string.IsNullOrEmpty(entry.stableRendererKey) ||
                    !string.Equals(
                        entry.stableRendererKey,
                        EndfieldRecoveredRendererIdSidecarCaptureBridge
                            .BuildStableRendererKey(
                                entry.rendererOrdinalPath,
                                entry.materialIndex,
                                entry.materialName),
                        StringComparison.Ordinal) ||
                    !ids.Add(entry.id) ||
                    !stableRendererKeys.Add(entry.stableRendererKey))
                {
                    failure =
                        "renderer-ID sidecar dictionary IDs/stableRendererKey values " +
                        "are not valid, unique, and capture-local";
                    return false;
                }
                entriesById.Add(entry.id, entry);
            }
            var summariesById = new Dictionary<int, RendererIdPixelSummary>();
            for (int pixel = 0; pixel < capture.rgba.Length; pixel += 4)
            {
                float idValue = capture.rgba[pixel];
                for (int channel = 0; channel < 4; channel++)
                {
                    if (float.IsNaN(capture.rgba[pixel + channel]) ||
                        float.IsInfinity(capture.rgba[pixel + channel]))
                    {
                        failure = "renderer-ID sidecar contains a non-finite value";
                        return false;
                    }
                }
                if (idValue <= 0.5f)
                    continue;
                float rounded = Mathf.Round(idValue);
                if (Mathf.Abs(idValue - rounded) > 1.0e-4f ||
                    rounded <= 0.0f || rounded >= (1 << 24) ||
                    !ids.Contains((int)rounded))
                {
                    failure =
                        "renderer-ID sidecar contains a non-integral, out-of-range, " +
                        "or unmapped pixel ID";
                    return false;
                }
                int id = (int)rounded;
                int pixelIndex = pixel / 4;
                int x = pixelIndex % capture.width;
                int y = pixelIndex / capture.width;
                RendererIdPixelSummary summary;
                if (!summariesById.TryGetValue(id, out summary))
                {
                    EndfieldRendererIdSidecarEntry entry = entriesById[id];
                    summary = new RendererIdPixelSummary
                    {
                        id = id,
                        stableRendererKey = entry.stableRendererKey,
                        rendererPath = entry.rendererPath,
                        rendererOrdinalPath = entry.rendererOrdinalPath,
                        materialIndex = entry.materialIndex,
                        materialName = entry.materialName,
                        shaderName = entry.shaderName,
                        renderQueue = entry.renderQueue,
                        pixelCount = 0,
                        internalMinX = x,
                        internalMinY = y,
                        internalMaxX = x,
                        internalMaxY = y,
                    };
                }
                summary.pixelCount++;
                summary.internalMinX = Mathf.Min(summary.internalMinX, x);
                summary.internalMinY = Mathf.Min(summary.internalMinY, y);
                summary.internalMaxX = Mathf.Max(summary.internalMaxX, x);
                summary.internalMaxY = Mathf.Max(summary.internalMaxY, y);
                summariesById[id] = summary;
                nonZeroPixelCount++;
            }
            long summaryPixelCount = 0;
            var orderedSummaries = new List<RendererIdPixelSummary>();
            for (int entryIndex = 0; entryIndex < entries.Length; entryIndex++)
            {
                RendererIdPixelSummary summary;
                if (!summariesById.TryGetValue(entries[entryIndex].id, out summary))
                    continue;
                if (summary.pixelCount <= 0 ||
                    summary.internalMinX < 0 || summary.internalMinX >= capture.width ||
                    summary.internalMinY < 0 || summary.internalMinY >= capture.height ||
                    summary.internalMaxX < summary.internalMinX ||
                    summary.internalMaxX >= capture.width ||
                    summary.internalMaxY < summary.internalMinY ||
                    summary.internalMaxY >= capture.height)
                {
                    failure =
                        "renderer-ID sidecar pixel summary has invalid inclusive bounds";
                    return false;
                }
                summary.pngMinX = ScaleInclusiveMin(
                    summary.internalMinX, Width, capture.width);
                summary.pngMinY = ScaleInclusiveMin(
                    summary.internalMinY, Height, capture.height);
                summary.pngMaxX = ScaleInclusiveMax(
                    summary.internalMaxX, Width, capture.width);
                summary.pngMaxY = ScaleInclusiveMax(
                    summary.internalMaxY, Height, capture.height);
                if (summary.pngMinX < 0 || summary.pngMinX > summary.pngMaxX ||
                    summary.pngMaxX >= Width || summary.pngMinY < 0 ||
                    summary.pngMinY > summary.pngMaxY || summary.pngMaxY >= Height)
                {
                    failure =
                        "renderer-ID sidecar PNG-scaled pixel bounds are invalid";
                    return false;
                }
                summaryPixelCount += summary.pixelCount;
                orderedSummaries.Add(summary);
            }
            if (summaryPixelCount != nonZeroPixelCount)
            {
                failure =
                    "renderer-ID sidecar pixel-summary total does not equal " +
                    "the nonzero pixel count";
                return false;
            }
            pixelSummaries = orderedSummaries.ToArray();
            return true;
        }

        private static int ScaleInclusiveMin(int value, int outputExtent, int inputExtent)
        {
            return Mathf.Clamp(
                (int)((long)value * outputExtent / inputExtent),
                0,
                outputExtent - 1);
        }

        private static int ScaleInclusiveMax(int value, int outputExtent, int inputExtent)
        {
            long exclusive = ((long)value + 1L) * outputExtent;
            int scaled = (int)((exclusive + inputExtent - 1L) / inputExtent - 1L);
            return Mathf.Clamp(scaled, 0, outputExtent - 1);
        }

        private static Color32 SelectCornerConsensusBackground(Color32[] pixels)
        {
            Require(pixels != null && pixels.Length == Width * Height,
                "Actor-composed readback size drifted before background measurement");
            Color32[] corners =
            {
                pixels[0],
                pixels[Width - 1],
                pixels[(Height - 1) * Width],
                pixels[pixels.Length - 1],
            };
            int bestA = 0;
            int bestB = 1;
            int bestDistance = int.MaxValue;
            for (int a = 0; a < corners.Length; a++)
            {
                for (int b = a + 1; b < corners.Length; b++)
                {
                    int distance = ColorDistanceSquared(corners[a], corners[b]);
                    if (distance >= bestDistance)
                        continue;
                    bestDistance = distance;
                    bestA = a;
                    bestB = b;
                }
            }
            Require(bestDistance <= 16,
                "No stable two-corner background consensus; closest squared RGBA " +
                "distance was " + bestDistance);
            return new Color32(
                (byte)((corners[bestA].r + corners[bestB].r) / 2),
                (byte)((corners[bestA].g + corners[bestB].g) / 2),
                (byte)((corners[bestA].b + corners[bestB].b) / 2),
                (byte)((corners[bestA].a + corners[bestB].a) / 2));
        }

        private static int ColorDistanceSquared(Color32 a, Color32 b)
        {
            int red = a.r - b.r;
            int green = a.g - b.g;
            int blue = a.b - b.b;
            int alpha = a.a - b.a;
            return red * red + green * green + blue * blue + alpha * alpha;
        }

        private static RoiMeasurement[] MeasureRois(Color32[] pixels, RetailSample oracleSample)
        {
            if (oracleSample == null || oracleSample.rois == null)
                return Array.Empty<RoiMeasurement>();
            return new[]
            {
                MeasureRoi("actorBody", oracleSample.rois.actorBody, pixels),
                MeasureRoi("broadTeal", oracleSample.rois.broadTeal, pixels),
                MeasureRoi("raisedHand", oracleSample.rois.raisedHand, pixels),
                MeasureRoi("lowerLeftRibbon", oracleSample.rois.lowerLeftRibbon, pixels),
            };
        }

        private static RoiMeasurement MeasureRoi(
            string name, RetailRoi roi, Color32[] pixels)
        {
            Require(roi != null && roi.scaledBoundsXyxy != null &&
                roi.scaledBoundsXyxy.Length == 4,
                "Retail oracle ROI is malformed: " + name);
            int x0 = Mathf.Clamp(roi.scaledBoundsXyxy[0], 0, Width);
            int x1 = Mathf.Clamp(roi.scaledBoundsXyxy[2], 0, Width);
            int top = Mathf.Clamp(roi.scaledBoundsXyxy[1], 0, Height);
            int bottom = Mathf.Clamp(roi.scaledBoundsXyxy[3], 0, Height);
            int y0 = Height - bottom;
            int y1 = Height - top;
            int pixelCount = 0;
            int tealCount = 0;
            int alphaCount = 0;
            for (int y = y0; y < y1; y++)
            {
                for (int x = x0; x < x1; x++)
                {
                    Color32 pixel = pixels[y * Width + x];
                    pixelCount++;
                    if (pixel.a > CoverageAlphaThreshold)
                        alphaCount++;
                    if (IsTeal(pixel))
                        tealCount++;
                }
            }
            return new RoiMeasurement
            {
                roi = name,
                pixelCount = pixelCount,
                tealPixelCount = tealCount,
                tealCoverage = pixelCount == 0 ? 0f : (float)tealCount / pixelCount,
                alphaPixelCount = alphaCount,
                alphaCoverage = pixelCount == 0 ? 0f : (float)alphaCount / pixelCount,
                coordinateConvention = "oracle_scaled_top_left_flipped_for_unity_readback",
            };
        }

        private static bool IsTeal(Color32 pixel)
        {
            return pixel.g >= 80 && pixel.b >= 80 &&
                pixel.g - pixel.r >= 20 && pixel.b - pixel.r >= 10;
        }

        private static RetailRoiComparison[] BuildRoiComparisons(
            RetailSample oracleSample,
            FrameRecord composite,
            FrameRecord actorOnly,
            FrameRecord effectsOnly)
        {
            if (oracleSample == null || composite == null ||
                composite.roiMeasurements == null)
                return Array.Empty<RetailRoiComparison>();
            RetailRoi[] oracleRois =
            {
                oracleSample.rois.actorBody,
                oracleSample.rois.broadTeal,
                oracleSample.rois.raisedHand,
                oracleSample.rois.lowerLeftRibbon,
            };
            string[] names = { "actorBody", "broadTeal", "raisedHand", "lowerLeftRibbon" };
            RetailRoiComparison[] result = new RetailRoiComparison[names.Length];
            for (int index = 0; index < names.Length; index++)
            {
                RoiMeasurement compositeMetric = FindMeasurement(composite, names[index]);
                RoiMeasurement actorMetric = FindMeasurement(actorOnly, names[index]);
                RoiMeasurement effectsMetric = FindMeasurement(effectsOnly, names[index]);
                result[index] = new RetailRoiComparison
                {
                    roi = names[index],
                    retailTealCoverage = oracleRois[index].tealCoverage,
                    compositeTealCoverage = compositeMetric.tealCoverage,
                    actorOnlyTealCoverage = actorMetric.tealCoverage,
                    effectsOnlyTealCoverage = effectsMetric.tealCoverage,
                    compositeCoverageDelta = compositeMetric.tealCoverage -
                        oracleRois[index].tealCoverage,
                    comparisonKind = "predicate_coverage_only_not_pixel_equality",
                };
            }
            return result;
        }

        private static RoiMeasurement FindMeasurement(FrameRecord frame, string name)
        {
            if (frame == null || frame.roiMeasurements == null)
                return new RoiMeasurement();
            for (int index = 0; index < frame.roiMeasurements.Length; index++)
            {
                if (frame.roiMeasurements[index].roi == name)
                    return frame.roiMeasurements[index];
            }
            return new RoiMeasurement();
        }

        private static void ValidateSourceSpec()
        {
            string path = ProjectAbsolute(SpecPath);
            Require(File.Exists(path), "Capture spec is missing: " + path);
            CaptureSpec spec = JsonUtility.FromJson<CaptureSpec>(
                File.ReadAllText(path, Encoding.UTF8));
            Require(spec != null && spec.schema == ExpectedSpecSchema,
                "Capture spec schema drifted");
            Require(spec.status == "diagnostic_only" && spec.comparisonOnly &&
                !spec.eventOriginProven && !spec.visibleAdmission,
                "Capture spec admission/event-origin flags are not fail-closed");
            Require(spec.clock != null && spec.clock.retailTimeBase == "1/1000" &&
                spec.clock.restartCandidatePts == CandidateRestartPts &&
                spec.clock.localTimeMapping == "localSeconds=(retailPts-37967)/1000",
                "Capture spec candidate clock drifted");
            Require(spec.sharedMaterialClip != null &&
                spec.sharedMaterialClip.name == SharedClipName &&
                Mathf.Abs(spec.sharedMaterialClip.lengthSeconds - SharedClipStopTime) < 0.00001f,
                "Capture spec shared clip identity drifted");
            Require(spec.effectLifetimes != null && spec.effectLifetimes.Length == Roots.Length,
                "Capture spec effect lifetime census drifted");
            for (int index = 0; index < Roots.Length; index++)
            {
                EffectLifetime row = FindLifetime(spec, Roots[index].effectRoot);
                Require(row != null &&
                    Mathf.Abs(row.durationSeconds - Roots[index].durationSeconds) < 0.00001f &&
                    row.startRetailPts == CandidateRestartPts,
                    "Capture spec lifetime drifted for " + Roots[index].effectRoot);
            }
        }

        private static EffectLifetime FindLifetime(CaptureSpec spec, string effectRoot)
        {
            for (int index = 0; index < spec.effectLifetimes.Length; index++)
            {
                if (spec.effectLifetimes[index] != null &&
                    spec.effectLifetimes[index].effectRoot == effectRoot)
                    return spec.effectLifetimes[index];
            }
            return null;
        }

        private static RetailOracle LoadRetailOracle()
        {
            string path = ProjectAbsolute(RetailOraclePath);
            Require(File.Exists(path), "Retail visual oracle is missing: " + path);
            RetailOracle oracle = JsonUtility.FromJson<RetailOracle>(
                File.ReadAllText(path, Encoding.UTF8));
            Require(oracle != null && oracle.schema == ExpectedOracleSchema &&
                oracle.status == "diagnostic_only" && !oracle.visibleAdmission &&
                oracle.tealPredicateRgb24 == ExpectedTealPredicate,
                "Retail visual oracle admission or predicate drifted");
            Require(oracle.samples != null && oracle.samples.Length > 0,
                "Retail visual oracle has no samples");
            return oracle;
        }

        private static RetailSample FindOracleSample(RetailOracle oracle, int pts)
        {
            for (int index = 0; index < oracle.samples.Length; index++)
            {
                if (oracle.samples[index] != null && oracle.samples[index].pts == pts)
                    return oracle.samples[index];
            }
            return null;
        }

        private static void ValidateActorClipAndProfile(
            AnimationClip actorClip,
            CharacterRecoveryPresentationProfile profile)
        {
            Require(actorClip.name == "A_actor_lizhiyan_ui_overview_start_01",
                "Actor clip name drifted");
            Require(actorClip.legacy, "Actor clip is no longer the recovered legacy clip");
            Require(Mathf.Abs(actorClip.length - ExpectedActorClipLength) < 0.0001f,
                "Actor clip length drifted: " + actorClip.length.ToString("R"));
            Require(profile != null && profile.sourceRecovered &&
                profile.characterId == "chr_0032_lizhiyan",
                "Lizhiyan source-recovered presentation profile is missing");
            Require(Mathf.Abs(profile.cameraPosition.x - -0.177f) < 0.00001f &&
                Mathf.Abs(profile.cameraPosition.y - 0.998f) < 0.00001f &&
                Mathf.Abs(profile.cameraPosition.z - 3.5f) < 0.00001f &&
                Mathf.Abs(profile.lookAtPosition.x - 0.022f) < 0.00001f &&
                Mathf.Abs(profile.lookAtPosition.y - 1.225f) < 0.00001f &&
                Mathf.Abs(profile.lookAtPosition.z) < 0.00001f &&
                Mathf.Abs(profile.fieldOfView - 20.007383f) < 0.0001f &&
                Mathf.Abs(profile.nearClip - 0.1f) < 0.00001f &&
                Mathf.Abs(profile.farClip - 50f) < 0.0001f,
                "Source-backed Li Zhiyan camera fields drifted");
        }

        private static GameObject[] LoadEffectPrefabs()
        {
            GameObject[] prefabs = new GameObject[Roots.Length];
            for (int index = 0; index < Roots.Length; index++)
            {
                prefabs[index] = AssetDatabase.LoadAssetAtPath<GameObject>(
                    Roots[index].prefabPath);
                Require(prefabs[index] != null,
                    "Diagnostic effect prefab is missing: " + Roots[index].prefabPath);
            }
            return prefabs;
        }

        private static GameObject[] LoadPeakEffectPrefabs()
        {
            GameObject[] prefabs = new GameObject[PeakEffectRoots.Length];
            for (int index = 0; index < PeakEffectRoots.Length; index++)
            {
                string path = EndfieldLiZhiyanOverviewPeakParticleEffectImporter.PrefabPath(
                    PeakEffectRoots[index]);
                prefabs[index] = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                Require(prefabs[index] != null,
                    "Peak particle prefab is missing: " + path);
            }
            return prefabs;
        }

        private static GameObject LoadFingerEffectPrefab()
        {
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(FingerEffectPrefabPath);
            Require(prefab != null, "Exact finger effect prefab is missing: " + FingerEffectPrefabPath);
            return prefab;
        }

        private static void ValidateEffectContracts(ActorBundle bundle)
        {
            AnimationClip sharedClip = null;
            for (int index = 0; index < Roots.Length; index++)
            {
                EndfieldRecoveredStaticMeshEffectSource marker = bundle.markers[index];
                Require(marker.effectRoot == Roots[index].effectRoot &&
                    marker.sourceStartAnimationClip != null &&
                    marker.sourceStartAnimationClipPathId == SharedClipPathId &&
                    marker.sourceStartAnimationClipName == SharedClipName &&
                    Mathf.Abs(marker.sourceStartAnimationStopTime - SharedClipStopTime) < 0.00001f &&
                    Mathf.Abs(marker.sourceEffectDuration - Roots[index].durationSeconds) < 0.00001f &&
                    !marker.visibleAdmission,
                    "Effect source contract drifted: " + Roots[index].key);
                if (sharedClip == null)
                    sharedClip = marker.sourceStartAnimationClip;
                Require(sharedClip.GetInstanceID() ==
                    marker.sourceStartAnimationClip.GetInstanceID(),
                    "Effect roots do not share one AnimationClip instance");
            }
            Require(sharedClip != null && Mathf.Abs(sharedClip.length - SharedClipStopTime) < 0.0001f,
                "Resolved effect AnimationClip stop time drifted");
        }

        private static bool IsActorActive(ActorBundle bundle, float localSeconds)
        {
            return localSeconds >= -ActiveEndpointEpsilon &&
                localSeconds <= bundle.actorClip.length + ActiveEndpointEpsilon;
        }

        private static float ActorClipSampleTime(ActorBundle bundle, float localSeconds)
        {
            return Mathf.Clamp(localSeconds, 0f, bundle.actorClip.length);
        }

        private static bool IsEffectActive(RootDefinition root, float localSeconds)
        {
            return localSeconds >= -ActiveEndpointEpsilon &&
                localSeconds <= root.durationSeconds + ActiveEndpointEpsilon;
        }

        private static bool AnyEffectActive(float localSeconds)
        {
            for (int index = 0; index < Roots.Length; index++)
            {
                if (IsEffectActive(Roots[index], localSeconds))
                    return true;
            }
            return false;
        }

        private static string StateFor(RootDefinition root, float localSeconds)
        {
            if (localSeconds < -ActiveEndpointEpsilon)
                return "not_started_before_candidate_restart";
            if (localSeconds > root.durationSeconds + ActiveEndpointEpsilon)
                return "inactive_after_effect_setting_lifetime";
            if (localSeconds > SharedClipStopTime + ActiveEndpointEpsilon)
                return "active_holding_shared_clip_endpoint";
            if (Mathf.Abs(localSeconds - root.durationSeconds) <= ActiveEndpointEpsilon)
                return "active_through_effect_setting_endpoint";
            return "active_sampling_shared_clip";
        }

        private static float ClipSampleTime(float localSeconds)
        {
            return Mathf.Clamp(localSeconds, 0f, SharedClipStopTime);
        }

        private static int ExpectedMaterialCurveBindingCount(int rootIndex)
        {
            // The shared clip has 21 start_01, 15 start_02, and 17 start_03
            // classID 23 material.* bindings.  Keep this census explicit so a
            // missing path or silently unsupported shader property cannot make
            // a capture look successful while sampling only a subset.
            switch (rootIndex)
            {
                case 0: return 21;
                case 1: return 15;
                case 2: return 17;
                default: throw new ArgumentOutOfRangeException(nameof(rootIndex));
            }
        }

        private static RootManifestRow[] BuildRootManifestRows()
        {
            RootManifestRow[] rows = new RootManifestRow[Roots.Length];
            for (int index = 0; index < Roots.Length; index++)
            {
                rows[index] = new RootManifestRow
                {
                    key = Roots[index].key,
                    effectRoot = Roots[index].effectRoot,
                    prefabPath = Roots[index].prefabPath,
                    durationSeconds = Roots[index].durationSeconds,
                    startRetailPts = CandidateRestartPts,
                    endRetailPts = CandidateRestartPts +
                        Mathf.RoundToInt(Roots[index].durationSeconds * 1000f),
                    sourceMaterialRenderQueue = DiagnosticCaptureRenderQueue,
                };
            }
            return rows;
        }

        private static void ValidateManifest(string manifestPath)
        {
            Require(File.Exists(manifestPath), "Actor-composed manifest is missing: " + manifestPath);
            ActorComposedManifest manifest = JsonUtility.FromJson<ActorComposedManifest>(
                File.ReadAllText(manifestPath, Encoding.UTF8));
            Require(manifest != null && manifest.schema == ExpectedManifestSchema,
                "Actor-composed manifest schema drifted");
            Require(manifest.status == "diagnostic_only" && !manifest.visibleAdmission &&
                !manifest.eventOriginProven && !manifest.nativeRendererIdentityProven &&
                !manifest.actorAnimationRetailAbiEquivalent &&
                !manifest.comparesRetailPixels && !manifest.retailHashEquality,
                "Actor-composed manifest flags are not fail-closed");
            Require(manifest.rendererFingerprintWitnessBoundary ==
                "single_capture_session_before_camera_render_sharedmaterials_only; actor_hierarchy_runtime_ids_and_skinned_palette_hash; static_effect_source_pathids_and_runtime_ids; peak_source_pathids_source_particle_ids_and_runtime_proxy_ids; finger_source_pathids_source_particle_ids_and_runtime_proxy_ids; no_retail_hgmesh_identity_or_draw_proof" &&
                manifest.captureInvocationSerialBoundary ==
                "harness_monotonic_serial_one_per_camera_render; 168_invocations_for_24_anchors_times_7_lanes; independent_of_unity_frame_count; no_native_frame_or_command_buffer_identity",
                "Actor-composed renderer fingerprint boundary drifted");
            Require(manifest.width == Width && manifest.height == Height &&
                manifest.captures != null && manifest.captures.Length == Anchors.Length &&
                manifest.graphicsDeviceType != GraphicsDeviceType.Null.ToString() &&
                manifest.backgroundMeasurement ==
                    "closest_pair_of_four_frame_corners_actor_safe",
                "Actor-composed manifest dimensions/backend/anchor count drifted");
            Require(manifest.materialCurveSampling != null &&
                manifest.materialCurveSampling.Contains("AnimationUtility.GetEditorCurve") &&
                manifest.materialCurveSampling.Contains("no AnimationMode"),
                "Actor-composed material curve sampling provenance drifted");
            Require(string.Equals(manifest.sourceSpecSha256,
                Sha256File(ProjectAbsolute(SpecPath)), StringComparison.OrdinalIgnoreCase),
                "Actor-composed source spec hash drifted");
            Require(string.Equals(manifest.retailOracleSha256,
                Sha256File(ProjectAbsolute(RetailOraclePath)), StringComparison.OrdinalIgnoreCase),
                "Actor-composed retail oracle hash drifted");
            Require(manifest.manualPeakParticleSimulation &&
                manifest.sourcePeakParticlePrefabs != null &&
                manifest.sourcePeakParticlePrefabs.Length == PeakEffectRoots.Length &&
                string.Equals(manifest.sourcePeakParticleContractSha256,
                    Sha256File(ProjectAbsolute(
                        EndfieldLiZhiyanOverviewPeakParticleEffectImporter.ContractPath)),
                    StringComparison.OrdinalIgnoreCase),
                "Actor-composed peak-particle source/gate drifted");
            Require(manifest.sourceFingerEffectContract == FingerEffectContractPath &&
                string.Equals(manifest.sourceFingerEffectContractSha256,
                    Sha256File(ProjectAbsolute(FingerEffectContractPath)),
                    StringComparison.OrdinalIgnoreCase) &&
                manifest.sourceFingerEffectPrefab == FingerEffectPrefabPath &&
                manifest.fingerEffectMount == FingerMountHierarchy &&
                Mathf.Abs(manifest.fingerEffectDelaySeconds - FingerEffectDelaySeconds) < 0.00001f &&
                Mathf.Abs(manifest.fingerEffectDurationSeconds - FingerEffectDurationSeconds) < 0.00001f &&
                manifest.fingerParticleSimulationMode != null &&
                manifest.fingerParticleMaterialMode != null,
                "Actor-composed exact finger source/gate drifted");

            string baselinePath = RepositoryAbsolute(BaselineManifestRelativePath);
            Require(manifest.baselinePreserved &&
                string.Equals(manifest.baselineManifestSha256,
                    ReadRequiredHash(baselinePath, "baseline manifest"),
                    StringComparison.OrdinalIgnoreCase),
                "Actor-composed baseline preservation gate failed");

            string outputDirectory = RepositoryAbsolute(OutputDirectoryRelativePath);
            bool[] foundVisibleRoot = new bool[Roots.Length];
            bool foundVisibleActor = false;
            bool foundVisiblePeakParticles = false;
            bool foundPeakBeforeDelay = false;
            bool foundPeakInsideWindow = false;
            bool foundPeakAfterDuration = false;
            var materialCurveStateHashes = new HashSet<string>[Roots.Length];
            var rootPngHashes = new HashSet<string>[Roots.Length];
            for (int index = 0; index < Roots.Length; index++)
            {
                materialCurveStateHashes[index] = new HashSet<string>(StringComparer.Ordinal);
                rootPngHashes[index] = new HashSet<string>(StringComparer.Ordinal);
            }
            Dictionary<string, string> stableRendererFingerprints = null;
            var actorPoseHashes = new Dictionary<string, HashSet<string>>(
                StringComparer.Ordinal);
            long expectedCaptureInvocationSerial = 1;
            for (int anchorIndex = 0; anchorIndex < Anchors.Length; anchorIndex++)
            {
                CaptureAnchor expected = Anchors[anchorIndex];
                ActorComposedCaptureRecord capture = manifest.captures[anchorIndex];
                Require(capture != null && capture.retailPts == expected.retailPts &&
                    Mathf.Abs(capture.localSeconds - expected.localSeconds) < 0.00001f &&
                    capture.composite != null && capture.actorOnly != null &&
                    capture.effectsOnly != null && capture.peakParticlesOnly != null &&
                    capture.peakParticleAliveCount >= 0 && capture.roots != null &&
                    capture.roots.Length == Roots.Length &&
                    capture.rendererFingerprintWitness != null &&
                    capture.peakParticleColorSamples != null &&
                    capture.peakParticleColorSamples.Length == 14,
                    "Actor-composed capture timing/shape drifted at PTS " + expected.retailPts);
                int sampledPeakParticleCount = 0;
                for (int sampleIndex = 0;
                    sampleIndex < capture.peakParticleColorSamples.Length;
                    sampleIndex++)
                {
                    PeakParticleColorSampleRecord sample =
                        capture.peakParticleColorSamples[sampleIndex];
                    Require(sample != null && !string.IsNullOrEmpty(sample.effectRoot) &&
                        !string.IsNullOrEmpty(sample.hierarchy) &&
                        sample.particleSystemPathId != 0 &&
                        sample.particleRendererPathId != 0 &&
                        sample.sourceEffectDelay >= 0f &&
                        sample.sourceEffectDuration > 0f &&
                        Mathf.Abs(sample.effectLocalSeconds -
                            (capture.localSeconds - sample.sourceEffectDelay)) < 0.00001f,
                        "Peak particle COLOR0 identity/timing drifted at PTS " +
                        expected.retailPts);
                    bool expectedPeakActive = sample.effectLocalSeconds >=
                        -ActiveEndpointEpsilon && sample.effectLocalSeconds <=
                        sample.sourceEffectDuration + ActiveEndpointEpsilon;
                    Require(sample.effectActive == expectedPeakActive &&
                        sample.particleCount >= 0 && sample.bakedVertexCount >= 0 &&
                        sample.bakedColorCount == sample.bakedVertexCount &&
                        float.IsFinite(sample.colorAlphaMin) &&
                        float.IsFinite(sample.colorAlphaMax) &&
                        float.IsFinite(sample.colorAlphaMean) &&
                        sample.colorAlphaMin >= 0f && sample.colorAlphaMax <= 1f &&
                        sample.colorAlphaMin <= sample.colorAlphaMean &&
                        sample.colorAlphaMean <= sample.colorAlphaMax,
                        "Peak particle COLOR0 payload drifted at PTS " +
                        expected.retailPts);
                    if (!expectedPeakActive)
                    {
                        Require(sample.particleCount == 0 &&
                            sample.bakedColorCount == 0,
                            "Inactive peak particle retained payload at PTS " +
                            expected.retailPts);
                    }
                    sampledPeakParticleCount += sample.particleCount;
                    foundPeakBeforeDelay |= sample.effectLocalSeconds < 0f &&
                        !sample.effectActive && sample.particleCount == 0;
                    foundPeakInsideWindow |= sample.effectActive &&
                        sample.particleCount > 0 && sample.bakedColorCount > 0;
                    foundPeakAfterDuration |= sample.effectLocalSeconds >
                        sample.sourceEffectDuration && !sample.effectActive &&
                        sample.particleCount == 0;
                }
                Require(sampledPeakParticleCount == capture.peakParticleAliveCount,
                    "Peak particle COLOR0 rows do not match aggregate count at PTS " +
                    expected.retailPts);
                ValidateRendererFingerprintWitness(
                    capture, ref stableRendererFingerprints, actorPoseHashes);
                ValidateFrame(capture.composite, outputDirectory, expected.retailPts, "composite",
                    expectedCaptureInvocationSerial++);
                ValidateFrame(capture.actorOnly, outputDirectory, expected.retailPts, "actor_only",
                    expectedCaptureInvocationSerial++);
                ValidateFrame(capture.effectsOnly, outputDirectory, expected.retailPts, "effects_only",
                    expectedCaptureInvocationSerial++);
                ValidateFrame(capture.peakParticlesOnly, outputDirectory, expected.retailPts,
                    "peak_particles_only", expectedCaptureInvocationSerial++);
                foundVisibleActor |= capture.actorOnly.nonBackgroundCoverage > 0f;
                foundVisiblePeakParticles |= capture.peakParticleAliveCount > 0 &&
                    capture.peakParticlesOnly.nonBackgroundCoverage > 0f;

                for (int rootIndex = 0; rootIndex < Roots.Length; rootIndex++)
                {
                    RootCaptureRecord root = capture.roots[rootIndex];
                    bool expectedActive = IsEffectActive(Roots[rootIndex], expected.localSeconds);
                    Require(root.key == Roots[rootIndex].key &&
                        root.effectRoot == Roots[rootIndex].effectRoot &&
                        root.effectActive == expectedActive && root.frame != null,
                        "Actor-composed root lifecycle drifted for " + Roots[rootIndex].key +
                        " at PTS " + expected.retailPts);
                    int expectedMaterialCurveCount =
                        ExpectedMaterialCurveBindingCount(rootIndex);
                    Require(root.materialCurveSample != null &&
                        root.materialCurveSample.sourceBindingCount ==
                            expectedMaterialCurveCount,
                        "Material curve source census drifted for " +
                        Roots[rootIndex].key + " at PTS " + expected.retailPts);
                    if (expectedActive)
                    {
                        Require(root.materialCurveSample.appliedBindingCount ==
                            expectedMaterialCurveCount &&
                            root.materialCurveSample.values != null &&
                            root.materialCurveSample.values.Length ==
                                expectedMaterialCurveCount &&
                            !string.IsNullOrEmpty(root.materialCurveSample.stateSha256) &&
                            root.materialCurveSample.stateSha256 != "inactive",
                            "Active material curves were not fully applied for " +
                            Roots[rootIndex].key + " at PTS " + expected.retailPts);
                        materialCurveStateHashes[rootIndex].Add(
                            root.materialCurveSample.stateSha256);
                        rootPngHashes[rootIndex].Add(root.frame.pngSha256);
                    }
                    else
                    {
                        Require(root.materialCurveSample.appliedBindingCount == 0 &&
                            root.materialCurveSample.values != null &&
                            root.materialCurveSample.values.Length == 0 &&
                            root.materialCurveSample.stateSha256 == "inactive",
                            "Inactive material curve state is not fail-closed for " +
                            Roots[rootIndex].key);
                    }
                    ValidateFrame(root.frame, outputDirectory, expected.retailPts,
                        Roots[rootIndex].key + "_only", expectedCaptureInvocationSerial++);
                    if (!expectedActive)
                        Require(root.frame.nonBackgroundCoverage == 0f,
                            "Inactive root is not blank: " + Roots[rootIndex].key +
                            " at PTS " + expected.retailPts);
                    else
                    {
                        Require(root.frame.rendererIdSidecarAvailable &&
                            root.frame.rendererIdSidecarNonZeroPixelCount > 0 &&
                            root.frame.rendererIdSidecarPixelSummaries != null &&
                            root.frame.rendererIdSidecarPixelSummaries.Length > 0,
                            "Active root has no renderer-ID sidecar ownership: " +
                            Roots[rootIndex].key + " at PTS " + expected.retailPts +
                            "; failure=" + root.frame.rendererIdSidecarFailure);
                        foundVisibleRoot[rootIndex] |= root.frame.nonBackgroundCoverage > 0f;
                    }
                }

                if (capture.effectsAllInactive)
                    Require(capture.effectsOnly.nonBackgroundCoverage == 0f,
                        "All-inactive effects-only frame is not blank at PTS " +
                        expected.retailPts);
                RetailSample oracleSample = FindOracleSample(LoadRetailOracle(), expected.retailPts);
                if (oracleSample != null)
                    Require(capture.roiComparisons != null &&
                        capture.roiComparisons.Length == 4,
                        "Retail ROI comparison rows missing at PTS " + expected.retailPts);
            }
            Require(foundVisibleActor, "No actor-only capture produced visible pixels");
            Require(foundVisiblePeakParticles,
                "No live peak-particle capture produced visible pixels");
            Require(foundPeakBeforeDelay && foundPeakInsideWindow &&
                foundPeakAfterDuration,
                "Peak particle corrected delay/duration/COLOR0 witnesses are incomplete");
            for (int index = 0; index < Roots.Length; index++)
                Require(foundVisibleRoot[index],
                    "No root-only capture produced visible pixels for " + Roots[index].key);
            for (int index = 0; index < Roots.Length; index++)
                Require(materialCurveStateHashes[index].Count > 1,
                    "Material curve state did not change across active anchors for " +
                    Roots[index].key);
            for (int index = 0; index < Roots.Length; index++)
                Require(rootPngHashes[index].Count > 1,
                    "Rendered root PNG did not change across active anchors for " +
                    Roots[index].key + "; material curves changed but visual output did not");
            Require(MaterialCurveStateDiffersAtAnchors(
                    manifest, 0, 38167, 38183) &&
                MaterialCurveStateDiffersAtAnchors(
                    manifest, 1, 40834, 40867) &&
                MaterialCurveStateDiffersAtAnchors(
                    manifest, 2, 43200, 43600),
                "Material curve state did not change at the expected dynamic anchors");
            Require(actorPoseHashes.Count > 0 &&
                actorPoseHashes.Values.Any(values => values.Count > 1),
                "Actor skinned-pose witness did not change across capture anchors");
            Require(expectedCaptureInvocationSerial ==
                1L + Anchors.Length * (4 + Roots.Length),
                "Actor-composed capture invocation serial census drifted");
        }

        private static bool MaterialCurveStateDiffersAtAnchors(
            ActorComposedManifest manifest,
            int rootIndex,
            int firstPts,
            int secondPts)
        {
            ActorComposedCaptureRecord first = manifest.captures.Single(
                value => value != null && value.retailPts == firstPts);
            ActorComposedCaptureRecord second = manifest.captures.Single(
                value => value != null && value.retailPts == secondPts);
            return first.roots[rootIndex].effectActive &&
                second.roots[rootIndex].effectActive &&
                first.roots[rootIndex].materialCurveSample != null &&
                second.roots[rootIndex].materialCurveSample != null &&
                first.roots[rootIndex].materialCurveSample.stateSha256 !=
                    second.roots[rootIndex].materialCurveSample.stateSha256;
        }

        private static void ValidateRendererFingerprintWitness(
            ActorComposedCaptureRecord capture,
            ref Dictionary<string, string> stableFingerprints,
            Dictionary<string, HashSet<string>> actorPoseHashes)
        {
            RendererFingerprintRecord[] rows = capture.rendererFingerprintWitness;
            int pts = capture.retailPts;
            int expectedActorRows = 0;
            int expectedStaticRows = 0;
            int expectedPeakRows = 0;
            int expectedFingerRows = 0;
            var current = new Dictionary<string, string>(StringComparer.Ordinal);
            foreach (RendererFingerprintRecord row in rows)
            {
                Require(row != null && !string.IsNullOrEmpty(row.identityKey) &&
                    !current.ContainsKey(row.identityKey) &&
                    row.unityRendererInstanceId != 0 &&
                    row.materials != null && row.localToWorldStateSha256 != null &&
                    row.localToWorldStateSha256.Length == 64,
                    "Renderer fingerprint identity drifted at PTS " + pts);
                if (row.role == "static_effect")
                {
                    expectedStaticRows++;
                    Require(row.sourceRendererPathId != 0 &&
                        row.sourceMeshPathIds != null &&
                        row.sourceMeshPathIds.Length == 1 &&
                        row.sourceMeshPathIds[0] != 0,
                        "Static-effect source identity is incomplete at PTS " + pts);
                    RootDefinition root = Roots.Single(value => value.key == row.sourceRoot);
                    Require(row.activeInHierarchy ==
                        (capture.actorActive && IsEffectActive(root, capture.localSeconds)),
                        "Static-effect witness lifecycle drifted at PTS " + pts);
                }
                else if (row.role == "peak_particle_proxy")
                {
                    expectedPeakRows++;
                    Require(row.sourceRendererPathId != 0 &&
                        row.sourceRendererInstanceId != 0 &&
                        row.sourceParticleSystemInstanceId != 0 &&
                        row.unityMeshInstanceId != 0,
                        "Peak proxy identity is incomplete at PTS " + pts);
                    Require(row.activeInHierarchy && row.rendererEnabled ==
                        (capture.actorActive && row.meshVertexCount > 0),
                        "Peak proxy witness lifecycle drifted at PTS " + pts);
                }
                else if (row.role == "finger_particle_proxy")
                {
                    expectedFingerRows++;
                    Require(row.sourceRendererPathId != 0 &&
                        row.sourceRendererInstanceId != 0 &&
                        row.sourceParticleSystemInstanceId != 0 &&
                        row.unityMeshInstanceId != 0,
                        "Exact finger proxy identity is incomplete at PTS " + pts);
                    Require(row.activeInHierarchy && row.rendererEnabled ==
                        (capture.actorActive && IsFingerEffectActive(capture.localSeconds) &&
                            row.meshVertexCount > 0),
                        "Exact finger proxy witness lifecycle drifted at PTS " + pts);
                }
                else
                {
                    Require(row.role == "actor",
                        "Unknown renderer fingerprint role at PTS " + pts);
                    expectedActorRows++;
                    Require(row.activeInHierarchy == capture.actorActive,
                        "Actor witness lifecycle drifted at PTS " + pts);
                    if (row.skinnedBoneCount > 0)
                    {
                        Require(row.skinnedPoseSha256 != null &&
                            row.skinnedPoseSha256.Length == 64,
                            "Actor skinned-pose hash drifted at PTS " + pts);
                        if (!actorPoseHashes.TryGetValue(row.identityKey,
                            out HashSet<string> hashes))
                        {
                            hashes = new HashSet<string>(StringComparer.Ordinal);
                            actorPoseHashes.Add(row.identityKey, hashes);
                        }
                        hashes.Add(row.skinnedPoseSha256);
                    }
                    else
                    {
                        Require(string.IsNullOrEmpty(row.skinnedPoseSha256),
                            "Non-skinned actor renderer has a pose hash at PTS " + pts);
                    }
                }
                Require(row.sourceMaterialPathIds != null &&
                    row.materials.Length == row.sourceMaterialPathIds.Length,
                    "Renderer material/source slot census drifted at PTS " + pts);
                string materialIdentity = string.Join(",", row.materials.Select(material =>
                {
                    Require(material != null && material.unityMaterialInstanceId != 0,
                        "Renderer material instance ID is zero at PTS " + pts);
                    return material.sourceMaterialPathId.ToString(CultureInfo.InvariantCulture) +
                        "/" + material.unityMaterialInstanceId.ToString(
                            CultureInfo.InvariantCulture) + "/" + material.shaderName +
                        "/" + material.renderQueue.ToString(CultureInfo.InvariantCulture);
                }));
                current.Add(row.identityKey,
                    row.sourceRendererPathId.ToString(CultureInfo.InvariantCulture) + ":" +
                    string.Join(",", row.sourceMeshPathIds.Select(value =>
                        value.ToString(CultureInfo.InvariantCulture))) + ":" +
                    row.unityRendererInstanceId.ToString(CultureInfo.InvariantCulture) + ":" +
                    row.unityMeshInstanceId.ToString(CultureInfo.InvariantCulture) + ":" +
                    row.sourceRendererInstanceId.ToString(CultureInfo.InvariantCulture) + ":" +
                    row.sourceParticleSystemInstanceId.ToString(CultureInfo.InvariantCulture) + ":" +
                    (row.role == "peak_particle_proxy" || row.role == "finger_particle_proxy" ? "dynamic_geometry" :
                        row.meshVertexCount.ToString(CultureInfo.InvariantCulture) + "/" +
                        row.meshSubMeshCount.ToString(CultureInfo.InvariantCulture) + "/" +
                        row.meshIndexCount.ToString(CultureInfo.InvariantCulture) + "/" +
                        row.skinnedBoneCount.ToString(CultureInfo.InvariantCulture)) + ":" +
                    materialIdentity);
            }
            Require(expectedActorRows == 21 && expectedStaticRows == 10 &&
                expectedPeakRows == 14 && expectedFingerRows == 7,
                "Renderer fingerprint source census drifted at PTS " + pts);
            if (stableFingerprints == null)
            {
                stableFingerprints = current;
                return;
            }
            Require(stableFingerprints.Count == current.Count &&
                stableFingerprints.All(pair => current.TryGetValue(pair.Key, out string value) &&
                    value == pair.Value),
                "Renderer/mesh/material instance IDs changed between anchors at PTS " + pts);
        }

        private static void ValidateFrame(
            FrameRecord frame, string outputDirectory, int pts, string label,
            long expectedCaptureInvocationSerial)
        {
            Require(frame.captureInvocationSerial == expectedCaptureInvocationSerial &&
                frame.width == Width && frame.height == Height &&
                frame.alphaCoverage >= 0f && frame.alphaCoverage <= 1f &&
                frame.nonBackgroundCoverage >= 0f && frame.nonBackgroundCoverage <= 1f,
                "Frame coverage/dimensions drifted for " + label + " at PTS " + pts);
            Require(string.Equals(
                    frame.rendererIdSidecarRedChannelIdScope,
                    EndfieldRecoveredRendererIdSidecarCaptureBridge.RedChannelIdScope,
                    StringComparison.Ordinal),
                "Renderer-ID sidecar red-channel scope is not explicitly " +
                "captureInvocationSerial-local for " + label + " at PTS " + pts);
            string path = Path.Combine(outputDirectory, Path.GetFileName(frame.png));
            Require(File.Exists(path), "Frame PNG is missing: " + path);
            Require(frame.pngBytes == new FileInfo(path).Length &&
                string.Equals(frame.pngSha256, Sha256File(path),
                    StringComparison.OrdinalIgnoreCase),
                "Frame hash/size drifted for " + label + " at PTS " + pts);
            if (frame.rendererIdSidecarAvailable)
            {
                string sidecarRaw = Path.Combine(
                    outputDirectory,
                    Path.GetFileName(frame.rendererIdSidecarRaw));
                string sidecarDictionary = Path.Combine(
                    outputDirectory,
                    Path.GetFileName(frame.rendererIdSidecarDictionary));
                Require(File.Exists(sidecarRaw) && File.Exists(sidecarDictionary),
                    "Renderer-ID sidecar files are missing for " + label +
                    " at PTS " + pts);
                Require(new FileInfo(sidecarRaw).Length ==
                    (long)frame.rendererIdSidecarWidth *
                        frame.rendererIdSidecarHeight * 4 * sizeof(float) &&
                    frame.rendererIdSidecarNonZeroPixelCount >= 0 &&
                    frame.rendererIdSidecarNonZeroPixelCount <=
                        (long)Width * Height,
                    "Renderer-ID sidecar dimensions/count drifted for " + label +
                        " at PTS " + pts);
                RendererIdPixelSummary[] summaries =
                    frame.rendererIdSidecarPixelSummaries ??
                    Array.Empty<RendererIdPixelSummary>();
                Require(frame.rendererIdSidecarWidth > 0 &&
                    frame.rendererIdSidecarHeight > 0,
                    "Renderer-ID sidecar extent is missing for " + label +
                    " at PTS " + pts);
                long summaryPixelCount = 0;
                var summaryIds = new HashSet<int>();
                var summaryKeys = new HashSet<string>(StringComparer.Ordinal);
                for (int summaryIndex = 0;
                     summaryIndex < summaries.Length;
                     summaryIndex++)
                {
                    RendererIdPixelSummary summary = summaries[summaryIndex];
                    Require(summary != null && summary.id > 0 &&
                        summary.id < (1 << 24) &&
                        summary.pixelCount > 0 &&
                        summary.internalMinX >= 0 &&
                        summary.internalMinX <= summary.internalMaxX &&
                        summary.internalMaxX < frame.rendererIdSidecarWidth &&
                        summary.internalMinY >= 0 &&
                        summary.internalMinY <= summary.internalMaxY &&
                        summary.internalMaxY < frame.rendererIdSidecarHeight &&
                        summary.pngMinX >= 0 && summary.pngMinX <= summary.pngMaxX &&
                        summary.pngMaxX < Width && summary.pngMinY >= 0 &&
                        summary.pngMinY <= summary.pngMaxY && summary.pngMaxY < Height &&
                        !string.IsNullOrEmpty(summary.stableRendererKey) &&
                        !string.IsNullOrEmpty(summary.rendererPath) &&
                        !string.IsNullOrEmpty(summary.materialName) &&
                        summary.renderQueue >= 3660 &&
                        summary.renderQueue <= 3740 &&
                        summaryIds.Add(summary.id) &&
                        summaryKeys.Add(summary.stableRendererKey),
                        "Renderer-ID sidecar pixel summary identity/bounds drifted for " +
                        label + " at PTS " + pts);
                    summaryPixelCount += summary.pixelCount;
                }
                Require(summaryPixelCount == frame.rendererIdSidecarNonZeroPixelCount,
                    "Renderer-ID sidecar pixel-summary total drifted for " + label +
                    " at PTS " + pts);
            }
            else
            {
                Require(!string.IsNullOrEmpty(frame.rendererIdSidecarFailure),
                    "Renderer-ID sidecar failed without a diagnostic for " +
                    label + " at PTS " + pts);
            }
        }

        private static void DeletePreviousCaptureFiles(string directory)
        {
            if (!Directory.Exists(directory))
                return;
            string[] patterns =
            {
                "composite_*.png", "actor_only_*.png", "effects_only_*.png",
                "peak_particles_only_*.png",
                "start_01_only_*.png", "start_02_only_*.png", "start_03_only_*.png",
                "*_renderer_ids.raw", "*_renderer_ids.json",
            };
            for (int patternIndex = 0; patternIndex < patterns.Length; patternIndex++)
            {
                string[] files = Directory.GetFiles(directory, patterns[patternIndex]);
                for (int fileIndex = 0; fileIndex < files.Length; fileIndex++)
                    File.Delete(files[fileIndex]);
            }
            string manifest = Path.Combine(directory, ManifestFileName);
            if (File.Exists(manifest))
                File.Delete(manifest);
        }

        private static CaptureAnchor Anchor(int pts, string phase)
        {
            return new CaptureAnchor
            {
                retailPts = pts,
                timeBase = "1/1000",
                localSeconds = (pts - CandidateRestartPts) / 1000f,
                phase = phase,
            };
        }

        private static string Pts(int pts)
        {
            return pts.ToString("D5", CultureInfo.InvariantCulture);
        }

        private static float[] ToArray(Vector3 value)
        {
            return new[] { value.x, value.y, value.z };
        }

        private static float[] ToArray(Quaternion value)
        {
            return new[] { value.x, value.y, value.z, value.w };
        }

        private static string ProjectAbsolute(string projectRelativePath)
        {
            return Path.GetFullPath(Path.Combine(
                Directory.GetCurrentDirectory(),
                projectRelativePath.Replace('/', Path.DirectorySeparatorChar)));
        }

        private static string RepositoryAbsolute(string repositoryRelativePath)
        {
            return Path.GetFullPath(Path.Combine(
                Directory.GetCurrentDirectory(), "..",
                repositoryRelativePath.Replace('/', Path.DirectorySeparatorChar)));
        }

        private static string ReadRequiredHash(string path, string label)
        {
            Require(File.Exists(path), label + " is missing: " + path);
            return Sha256File(path);
        }

        private static string Sha256File(string path)
        {
            using (SHA256 digest = SHA256.Create())
            using (FileStream stream = File.OpenRead(path))
            {
                byte[] bytes = digest.ComputeHash(stream);
                StringBuilder builder = new StringBuilder(bytes.Length * 2);
                for (int index = 0; index < bytes.Length; index++)
                    builder.Append(bytes[index].ToString("x2", CultureInfo.InvariantCulture));
                return builder.ToString();
            }
        }

        private static void Release(UnityEngine.Object value)
        {
            if (value != null)
                UnityEngine.Object.DestroyImmediate(value);
        }

        private static void Require(bool condition, string message)
        {
            if (!condition)
                throw new InvalidOperationException(message);
        }

        [Serializable]
        private sealed class ActorBundle
        {
            public GameObject actor;
            public AnimationClip actorClip;
            public Renderer[] actorRenderers;
            public GameObject[] effects;
            public EndfieldRecoveredStaticMeshEffectSource[] markers;
            public EndfieldLiZhiyanMaterialCurveSampler[] materialCurveSamplers;
            public MaterialCurveSample[] materialCurveSamples;
            public GameObject[] peakEffects;
            public EndfieldRecoveredParticleEffectSource[] peakMarkers;
            public List<PeakBakeProxy> peakBakeProxies;
            public GameObject fingerEffect;
            public EndfieldRecoveredParticleEffectSource fingerMarker;
            public List<FingerBakeProxy> fingerBakeProxies;
            public List<Material> fingerDiagnosticMaterials;
            public List<Texture2D> fingerDiagnosticTextures;

            public void Release()
            {
                if (effects != null)
                {
                    for (int index = 0; index < effects.Length; index++)
                        if (effects[index] != null)
                            UnityEngine.Object.DestroyImmediate(effects[index]);
                }
                if (peakEffects != null)
                {
                    for (int index = 0; index < peakEffects.Length; index++)
                        if (peakEffects[index] != null)
                            UnityEngine.Object.DestroyImmediate(peakEffects[index]);
                }
                if (peakBakeProxies != null)
                {
                    foreach (PeakBakeProxy proxy in peakBakeProxies)
                    {
                        if (proxy.proxyObject != null)
                            UnityEngine.Object.DestroyImmediate(proxy.proxyObject);
                        if (proxy.mesh != null)
                            UnityEngine.Object.DestroyImmediate(proxy.mesh);
                    }
                }
                if (fingerBakeProxies != null)
                {
                    foreach (FingerBakeProxy proxy in fingerBakeProxies)
                    {
                        if (proxy.proxyObject != null)
                            UnityEngine.Object.DestroyImmediate(proxy.proxyObject);
                        if (proxy.mesh != null)
                            UnityEngine.Object.DestroyImmediate(proxy.mesh);
                    }
                }
                if (fingerEffect != null)
                    UnityEngine.Object.DestroyImmediate(fingerEffect);
                if (fingerDiagnosticMaterials != null)
                {
                    foreach (Material material in fingerDiagnosticMaterials)
                        if (material != null)
                            UnityEngine.Object.DestroyImmediate(material);
                }
                if (fingerDiagnosticTextures != null)
                {
                    foreach (Texture2D texture in fingerDiagnosticTextures)
                        if (texture != null)
                            UnityEngine.Object.DestroyImmediate(texture);
                }
                if (actor != null)
                    UnityEngine.Object.DestroyImmediate(actor);
            }
        }

        private sealed class PeakBakeProxy
        {
            public int rootIndex;
            public ParticleSystem system;
            public ParticleSystemRenderer sourceRenderer;
            public EndfieldRecoveredParticleNodeSource sourceNode;
            public GameObject proxyObject;
            public MeshRenderer proxyRenderer;
            public Mesh mesh;
            public bool hasGeometry;
        }

        private sealed class FingerBakeProxy
        {
            public ParticleSystem system;
            public ParticleSystemRenderer sourceRenderer;
            public EndfieldRecoveredParticleNodeSource sourceNode;
            public GameObject proxyObject;
            public MeshRenderer proxyRenderer;
            public Mesh mesh;
            public bool hasGeometry;
        }

        [Serializable]
        private sealed class RootDefinition
        {
            public string key;
            public string effectRoot;
            public string prefabPath;
            public float durationSeconds;
        }

        [Serializable]
        private sealed class CaptureSpec
        {
            public string schema;
            public string status;
            public bool comparisonOnly;
            public bool eventOriginProven;
            public bool visibleAdmission;
            public CaptureClock clock;
            public EffectLifetime[] effectLifetimes;
            public SharedMaterialClip sharedMaterialClip;
        }

        [Serializable]
        private sealed class CaptureClock
        {
            public string retailTimeBase;
            public int restartCandidatePts;
            public string localTimeMapping;
        }

        [Serializable]
        private sealed class SharedMaterialClip
        {
            public string name;
            public float lengthSeconds;
        }

        [Serializable]
        private sealed class EffectLifetime
        {
            public string effectRoot;
            public float durationSeconds;
            public int startRetailPts;
        }

        [Serializable]
        private sealed class CaptureAnchor
        {
            public int retailPts;
            public string timeBase;
            public float localSeconds;
            public string phase;
        }

        [Serializable]
        private sealed class RetailOracle
        {
            public string schema;
            public string status;
            public bool visibleAdmission;
            public string tealPredicateRgb24;
            public RetailSample[] samples;
        }

        [Serializable]
        private sealed class RetailSample
        {
            public int pts;
            public string phase;
            public RetailRoiSet rois;
        }

        [Serializable]
        private sealed class RetailRoiSet
        {
            public RetailRoi actorBody;
            public RetailRoi broadTeal;
            public RetailRoi raisedHand;
            public RetailRoi lowerLeftRibbon;
        }

        [Serializable]
        private sealed class RetailRoi
        {
            public int[] scaledBoundsXyxy;
            public int pixelCount;
            public int tealPixelCount;
            public float tealCoverage;
        }

        [Serializable]
        private sealed class ActorComposedManifest
        {
            public string schema;
            public string status;
            public bool visibleAdmission;
            public bool eventOriginProven;
            public bool nativeRendererIdentityProven;
            public string rendererFingerprintWitnessBoundary;
            public string captureInvocationSerialBoundary;
            public bool actorAnimationRetailAbiEquivalent;
            public bool comparesRetailPixels;
            public bool retailHashEquality;
            public string sourceActorPrefab;
            public string sourceActorClip;
            public string sourceProfile;
            public string[] sourceEffectPrefabs;
            public string sourcePeakParticleContract;
            public string sourcePeakParticleContractSha256;
            public string[] sourcePeakParticlePrefabs;
            public string sourceFingerEffectContract;
            public string sourceFingerEffectContractSha256;
            public string sourceFingerEffectPrefab;
            public string fingerEffectMount;
            public float fingerEffectDelaySeconds;
            public float fingerEffectDurationSeconds;
            public bool manualPeakParticleSimulation;
            public string peakParticleSimulationMode;
            public string peakParticleBatchmodeTransport;
            public string peakParticleMaterialMode;
            public string fingerParticleSimulationMode;
            public string fingerParticleMaterialMode;
            public string sourceSpec;
            public string sourceSpecSha256;
            public string retailOracle;
            public string retailOracleSha256;
            public string baselineManifest;
            public string baselineManifestSha256;
            public bool baselinePreserved;
            public string outputDirectory;
            public int width;
            public int height;
            public int[] backgroundRgba;
            public string backgroundMeasurement;
            public string graphicsDeviceType;
            public string graphicsDeviceName;
            public string cameraMode;
            public string cameraRotationMode;
            public float[] cameraPosition;
            public float[] lookAtPosition;
            public float fieldOfView;
            public float nearClip;
            public float farClip;
            public float referenceAspect;
            public float[] authoredOverviewRotation;
            public int diagnosticCaptureRenderQueue;
            public int sourceMaterialRenderQueue;
            public string renderQueueOverrideReason;
            public string softBlendOverride;
            public string effectAttachment;
            public string retailComparison;
            public int retailRestartCandidatePts;
            public string localTimeMapping;
            public string actorClipName;
            public float actorClipLengthSeconds;
            public string sharedClipName;
            public long sharedClipPathId;
            public float sharedClipStopTimeSeconds;
            public string materialCurveSampling;
            public RootManifestRow[] roots;
            public ActorComposedCaptureRecord[] captures;
        }

        [Serializable]
        private sealed class RootManifestRow
        {
            public string key;
            public string effectRoot;
            public string prefabPath;
            public float durationSeconds;
            public int startRetailPts;
            public int endRetailPts;
            public int sourceMaterialRenderQueue;
        }

        [Serializable]
        private sealed class ActorComposedCaptureRecord
        {
            public int retailPts;
            public string timeBase;
            public float localSeconds;
            public string phase;
            public bool actorActive;
            public float actorClipSampleSeconds;
            public bool actorClipClampedAfterEnd;
            public bool effectsAllInactive;
            public int peakParticleAliveCount;
            public PeakParticleColorSampleRecord[] peakParticleColorSamples;
            public RendererFingerprintRecord[] rendererFingerprintWitness;
            public FrameRecord composite;
            public FrameRecord actorOnly;
            public FrameRecord effectsOnly;
            public FrameRecord peakParticlesOnly;
            public RootCaptureRecord[] roots;
            public RetailRoiComparison[] roiComparisons;
        }

        [Serializable]
        private sealed class PeakParticleColorSampleRecord
        {
            public string effectRoot;
            public float sourceEffectDelay;
            public float sourceEffectDuration;
            public float effectLocalSeconds;
            public bool effectActive;
            public string hierarchy;
            public long particleSystemPathId;
            public long particleRendererPathId;
            public int particleCount;
            public int bakedVertexCount;
            public int bakedColorCount;
            public float colorAlphaMin;
            public float colorAlphaMax;
            public float colorAlphaMean;
        }

        [Serializable]
        private sealed class RendererFingerprintRecord
        {
            public string identityKey;
            public string role;
            public string sourceRoot;
            public string hierarchy;
            public long sourceRendererPathId;
            public long[] sourceMeshPathIds;
            public long[] sourceMaterialPathIds;
            public int unityRendererInstanceId;
            public int sourceRendererInstanceId;
            public int sourceParticleSystemInstanceId;
            public int unityMeshInstanceId;
            public bool activeInHierarchy;
            public bool rendererEnabled;
            public int meshVertexCount;
            public int meshSubMeshCount;
            public long meshIndexCount;
            public string localToWorldStateSha256;
            public int skinnedBoneCount;
            public string skinnedPoseSha256;
            public MaterialFingerprintRecord[] materials;
        }

        [Serializable]
        private sealed class MaterialFingerprintRecord
        {
            public int slot;
            public long sourceMaterialPathId;
            public int unityMaterialInstanceId;
            public string name;
            public string shaderName;
            public int renderQueue;
        }

        [Serializable]
        private sealed class RootCaptureRecord
        {
            public string key;
            public string effectRoot;
            public bool effectActive;
            public string effectState;
            public float clipSampleSeconds;
            public bool clipClampedAfterEnd;
            public MaterialCurveSample materialCurveSample;
            public FrameRecord frame;
        }

        [Serializable]
        private sealed class FrameRecord
        {
            public long captureInvocationSerial;
            public string png;
            public long pngBytes;
            public string pngSha256;
            public int width;
            public int height;
            public int alphaPixelCount;
            public float alphaCoverage;
            public int nonBackgroundPixelCount;
            public float nonBackgroundCoverage;
            public int[] measuredBackgroundRgba;
            public RoiMeasurement[] roiMeasurements;
            public string rendererIdSidecarRedChannelIdScope;
            public bool rendererIdSidecarAvailable;
            public string rendererIdSidecarRaw;
            public string rendererIdSidecarDictionary;
            public int rendererIdSidecarWidth;
            public int rendererIdSidecarHeight;
            public long rendererIdSidecarNonZeroPixelCount;
            public RendererIdPixelSummary[] rendererIdSidecarPixelSummaries;
            public string rendererIdSidecarFailure;
        }

        [Serializable]
        private sealed class RendererIdPixelSummary
        {
            public int id;
            public string stableRendererKey;
            public string rendererPath;
            public string rendererOrdinalPath;
            public int materialIndex;
            public string materialName;
            public string shaderName;
            public int renderQueue;
            public long pixelCount;
            public int internalMinX;
            public int internalMinY;
            public int internalMaxX;
            public int internalMaxY;
            public int pngMinX;
            public int pngMinY;
            public int pngMaxX;
            public int pngMaxY;
        }

        [Serializable]
        private sealed class RoiMeasurement
        {
            public string roi;
            public int pixelCount;
            public int tealPixelCount;
            public float tealCoverage;
            public int alphaPixelCount;
            public float alphaCoverage;
            public string coordinateConvention;
        }

        [Serializable]
        private sealed class RetailRoiComparison
        {
            public string roi;
            public float retailTealCoverage;
            public float compositeTealCoverage;
            public float actorOnlyTealCoverage;
            public float effectsOnlyTealCoverage;
            public float compositeCoverageDelta;
            public string comparisonKind;
        }
    }
}
