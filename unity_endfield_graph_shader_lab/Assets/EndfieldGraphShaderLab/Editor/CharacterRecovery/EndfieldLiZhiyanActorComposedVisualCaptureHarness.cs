using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
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
            "endfield.lizhiyan-actor-composed-diagnostic-capture.v1";
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
                try
                {
                    bundle = InstantiateBundle(actorPrefab, effectPrefabs, actorClip, captureScene);
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
                        roots = BuildRootManifestRows(),
                        captures = new ActorComposedCaptureRecord[Anchors.Length],
                    };

                    for (int anchorIndex = 0; anchorIndex < Anchors.Length; anchorIndex++)
                    {
                        CaptureAnchor anchor = Anchors[anchorIndex];
                        float localSeconds = anchor.localSeconds;
                        SampleBundle(bundle, localSeconds);
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
                        };

                        ConfigureVisibility(bundle, localSeconds, true, -1);
                        capture.composite = CaptureNamedFrame(
                            camera, target, readback, outputDirectory,
                            "composite_" + Pts(anchor.retailPts) + ".png", oracleSample);
                        ConfigureVisibility(bundle, localSeconds, false, -2);
                        capture.actorOnly = CaptureNamedFrame(
                            camera, target, readback, outputDirectory,
                            "actor_only_" + Pts(anchor.retailPts) + ".png", oracleSample);
                        ConfigureVisibility(bundle, localSeconds, false, -3);
                        capture.effectsOnly = CaptureNamedFrame(
                            camera, target, readback, outputDirectory,
                            "effects_only_" + Pts(anchor.retailPts) + ".png", oracleSample);

                        capture.roots = new RootCaptureRecord[Roots.Length];
                        for (int rootIndex = 0; rootIndex < Roots.Length; rootIndex++)
                        {
                            ConfigureVisibility(bundle, localSeconds, false, rootIndex);
                            string fileName = Roots[rootIndex].key + "_only_" +
                                Pts(anchor.retailPts) + ".png";
                            capture.roots[rootIndex] = new RootCaptureRecord
                            {
                                key = Roots[rootIndex].key,
                                effectRoot = Roots[rootIndex].effectRoot,
                                effectActive = IsEffectActive(Roots[rootIndex], localSeconds),
                                effectState = StateFor(Roots[rootIndex], localSeconds),
                                clipSampleSeconds = ClipSampleTime(localSeconds),
                                clipClampedAfterEnd = localSeconds > SharedClipStopTime,
                                frame = CaptureNamedFrame(
                                    camera, target, readback, outputDirectory,
                                    fileName, oracleSample),
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
            }
            return bundle;
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

        private static void SampleBundle(ActorBundle bundle, float localSeconds)
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
                    continue;
                bundle.markers[index].sourceStartAnimationClip.SampleAnimation(
                    bundle.effects[index], ClipSampleTime(localSeconds));
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
                bundle.effects[index].SetActive(active);
            }
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
            RetailSample oracleSample)
        {
            string outputPath = Path.Combine(outputDirectory, fileName);
            RenderTexture previousTarget = camera.targetTexture;
            RenderTexture previousActive = RenderTexture.active;
            try
            {
                camera.targetTexture = target;
                RenderTexture.active = target;
                camera.Render();
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

            return new FrameRecord
            {
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
            };
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
            Require(manifest.width == Width && manifest.height == Height &&
                manifest.captures != null && manifest.captures.Length == Anchors.Length &&
                manifest.graphicsDeviceType != GraphicsDeviceType.Null.ToString() &&
                manifest.backgroundMeasurement ==
                    "closest_pair_of_four_frame_corners_actor_safe",
                "Actor-composed manifest dimensions/backend/anchor count drifted");
            Require(string.Equals(manifest.sourceSpecSha256,
                Sha256File(ProjectAbsolute(SpecPath)), StringComparison.OrdinalIgnoreCase),
                "Actor-composed source spec hash drifted");
            Require(string.Equals(manifest.retailOracleSha256,
                Sha256File(ProjectAbsolute(RetailOraclePath)), StringComparison.OrdinalIgnoreCase),
                "Actor-composed retail oracle hash drifted");

            string baselinePath = RepositoryAbsolute(BaselineManifestRelativePath);
            Require(manifest.baselinePreserved &&
                string.Equals(manifest.baselineManifestSha256,
                    ReadRequiredHash(baselinePath, "baseline manifest"),
                    StringComparison.OrdinalIgnoreCase),
                "Actor-composed baseline preservation gate failed");

            string outputDirectory = RepositoryAbsolute(OutputDirectoryRelativePath);
            bool[] foundVisibleRoot = new bool[Roots.Length];
            bool foundVisibleActor = false;
            for (int anchorIndex = 0; anchorIndex < Anchors.Length; anchorIndex++)
            {
                CaptureAnchor expected = Anchors[anchorIndex];
                ActorComposedCaptureRecord capture = manifest.captures[anchorIndex];
                Require(capture != null && capture.retailPts == expected.retailPts &&
                    Mathf.Abs(capture.localSeconds - expected.localSeconds) < 0.00001f &&
                    capture.composite != null && capture.actorOnly != null &&
                    capture.effectsOnly != null && capture.roots != null &&
                    capture.roots.Length == Roots.Length,
                    "Actor-composed capture timing/shape drifted at PTS " + expected.retailPts);
                ValidateFrame(capture.composite, outputDirectory, expected.retailPts, "composite");
                ValidateFrame(capture.actorOnly, outputDirectory, expected.retailPts, "actor_only");
                ValidateFrame(capture.effectsOnly, outputDirectory, expected.retailPts, "effects_only");
                foundVisibleActor |= capture.actorOnly.nonBackgroundCoverage > 0f;

                for (int rootIndex = 0; rootIndex < Roots.Length; rootIndex++)
                {
                    RootCaptureRecord root = capture.roots[rootIndex];
                    bool expectedActive = IsEffectActive(Roots[rootIndex], expected.localSeconds);
                    Require(root.key == Roots[rootIndex].key &&
                        root.effectRoot == Roots[rootIndex].effectRoot &&
                        root.effectActive == expectedActive && root.frame != null,
                        "Actor-composed root lifecycle drifted for " + Roots[rootIndex].key +
                        " at PTS " + expected.retailPts);
                    ValidateFrame(root.frame, outputDirectory, expected.retailPts,
                        Roots[rootIndex].key + "_only");
                    if (!expectedActive)
                        Require(root.frame.nonBackgroundCoverage == 0f,
                            "Inactive root is not blank: " + Roots[rootIndex].key +
                            " at PTS " + expected.retailPts);
                    else
                        foundVisibleRoot[rootIndex] |= root.frame.nonBackgroundCoverage > 0f;
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
            for (int index = 0; index < Roots.Length; index++)
                Require(foundVisibleRoot[index],
                    "No root-only capture produced visible pixels for " + Roots[index].key);
        }

        private static void ValidateFrame(
            FrameRecord frame, string outputDirectory, int pts, string label)
        {
            Require(frame.width == Width && frame.height == Height &&
                frame.alphaCoverage >= 0f && frame.alphaCoverage <= 1f &&
                frame.nonBackgroundCoverage >= 0f && frame.nonBackgroundCoverage <= 1f,
                "Frame coverage/dimensions drifted for " + label + " at PTS " + pts);
            string path = Path.Combine(outputDirectory, Path.GetFileName(frame.png));
            Require(File.Exists(path), "Frame PNG is missing: " + path);
            Require(frame.pngBytes == new FileInfo(path).Length &&
                string.Equals(frame.pngSha256, Sha256File(path),
                    StringComparison.OrdinalIgnoreCase),
                "Frame hash/size drifted for " + label + " at PTS " + pts);
        }

        private static void DeletePreviousCaptureFiles(string directory)
        {
            if (!Directory.Exists(directory))
                return;
            string[] patterns =
            {
                "composite_*.png", "actor_only_*.png", "effects_only_*.png",
                "start_01_only_*.png", "start_02_only_*.png", "start_03_only_*.png",
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

            public void Release()
            {
                if (effects != null)
                {
                    for (int index = 0; index < effects.Length; index++)
                        if (effects[index] != null)
                            UnityEngine.Object.DestroyImmediate(effects[index]);
                }
                if (actor != null)
                    UnityEngine.Object.DestroyImmediate(actor);
            }
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
            public bool actorAnimationRetailAbiEquivalent;
            public bool comparesRetailPixels;
            public bool retailHashEquality;
            public string sourceActorPrefab;
            public string sourceActorClip;
            public string sourceProfile;
            public string[] sourceEffectPrefabs;
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
            public FrameRecord composite;
            public FrameRecord actorOnly;
            public FrameRecord effectsOnly;
            public RootCaptureRecord[] roots;
            public RetailRoiComparison[] roiComparisons;
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
            public FrameRecord frame;
        }

        [Serializable]
        private sealed class FrameRecord
        {
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
