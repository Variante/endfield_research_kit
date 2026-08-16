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
    /// Captures the three serialized Li Zhiyan static-mesh overview roots in
    /// one candidate retail epoch. This is deliberately separate from the
    /// start_01 harness: it is a deterministic visual diagnostic, not a
    /// retail event, renderer-list, or visible-admission implementation.
    /// </summary>
    public static class EndfieldLiZhiyanCombinedVisualCaptureHarness
    {
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
        private const string OutputDirectoryRelativePath =
            "scratch/character_recovery/lizhiyan_start01_start02_start03_capture";
        private const string ManifestFileName =
            "lizhiyan_start01_start02_start03_capture_manifest.json";
        private const string ExpectedSpecSchema =
            "endfield.lizhiyan-visual-capture-spec.v1";
        private const string ExpectedManifestSchema =
            "endfield.lizhiyan-start01-start02-start03-combined-diagnostic-capture.v1";
        private const long SharedClipPathId = 7360398354216100382L;
        private const string SharedClipName = "A_fxui__lizhiyan_overview_start_01";
        private const float SharedClipStopTime = 6.366667f;
        private const int CandidateRestartPts = 37967;
        private const int Width = 960;
        private const int Height = 540;
        private const int DiagnosticCaptureRenderQueue = 3704;
        private const float ActiveEndpointEpsilon = 0.000001f;
        private const byte CoverageAlphaThreshold = 8;
        private const byte CoverageColorThreshold = 8;

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

        // The existing 19 source anchors plus five curve-boundary anchors:
        // start_03's first dynamic key, start_02's first non-zero alpha, and
        // the start_03 material-wave/fade boundaries.
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

        [MenuItem("Endfield/Character Recovery Lab/Capture Li Zhiyan start_01+02+03 Visual Spec")]
        public static void BuildAndCapture()
        {
            string outputDirectory = RepositoryAbsolute(OutputDirectoryRelativePath);
            string manifestPath = Path.Combine(outputDirectory, ManifestFileName);
            try
            {
                Require(SystemInfo.graphicsDeviceType != GraphicsDeviceType.Null,
                    "Li Zhiyan combined visual capture requires a real graphics backend; " +
                    "do not run Unity with -nographics");
                ValidateSourceSpec();
                GameObject[] prefabs = LoadPrefabs();

                Directory.CreateDirectory(outputDirectory);
                DeletePreviousCaptureFiles(outputDirectory);

                Scene previousScene = SceneManager.GetActiveScene();
                Scene captureScene = EditorSceneManager.NewScene(
                    NewSceneSetup.EmptyScene,
                    NewSceneMode.Single);
                GameObject[] actors = new GameObject[Roots.Length];
                GameObject cameraObject = null;
                RenderTexture target = null;
                Texture2D readback = null;
                try
                {
                    for (int index = 0; index < Roots.Length; index++)
                    {
                        actors[index] = PrefabUtility.InstantiatePrefab(
                            prefabs[index], captureScene) as GameObject;
                        Require(actors[index] != null,
                            "Could not instantiate diagnostic prefab: " +
                            Roots[index].prefabPath);
                        actors[index].name = "LiZhiyan" + Roots[index].key +
                            "CombinedDiagnosticCaptureActor";
                        actors[index].transform.SetPositionAndRotation(
                            Vector3.zero,
                            Quaternion.identity);
                        actors[index].transform.localScale = Vector3.one;
                        PrepareDiagnosticActor(actors[index], Roots[index]);
                    }

                    ValidateSharedClipIdentity(actors);
                    Bounds bounds = CalculateBounds(actors);
                    Camera camera = CreateAutoFramedCamera(bounds, out cameraObject);
                    target = CreateTarget();
                    readback = new Texture2D(
                        Width,
                        Height,
                        TextureFormat.RGBA32,
                        false,
                        false);

                    CombinedCaptureManifest manifest = new CombinedCaptureManifest
                    {
                        schema = ExpectedManifestSchema,
                        status = "diagnostic_only",
                        visibleAdmission = false,
                        eventOriginProven = false,
                        comparesRetailPixels = false,
                        sourcePrefabs = new[]
                        {
                            Start01PrefabPath,
                            Start02PrefabPath,
                            Start03PrefabPath,
                        },
                        sourceSpec = SpecPath,
                        sourceSpecSha256 = Sha256File(ProjectAbsolute(SpecPath)),
                        outputDirectory = OutputDirectoryRelativePath,
                        width = Width,
                        height = Height,
                        backgroundRgba = new[] { 0, 0, 0, 0 },
                        cameraMode = "deterministic_shared_auto_framed_perspective",
                        graphicsDeviceType = SystemInfo.graphicsDeviceType.ToString(),
                        graphicsDeviceName = SystemInfo.graphicsDeviceName,
                        diagnosticCaptureRenderQueue = DiagnosticCaptureRenderQueue,
                        sourceMaterialRenderQueue = DiagnosticCaptureRenderQueue,
                        renderQueueOverrideReason = "none_source_queue_preserved",
                        softBlendOverride = "disabled_no_retail_scene_depth",
                        retailRestartCandidatePts = CandidateRestartPts,
                        localTimeMapping = "localSeconds=(retailPts-37967)/1000",
                        sharedClipName = SharedClipName,
                        sharedClipPathId = SharedClipPathId,
                        sharedClipStopTimeSeconds = SharedClipStopTime,
                        roots = BuildRootManifestRows(),
                        captures = new CombinedCaptureRecord[Anchors.Length],
                    };

                    for (int anchorIndex = 0; anchorIndex < Anchors.Length; anchorIndex++)
                    {
                        CaptureAnchor anchor = Anchors[anchorIndex];
                        float localSeconds = (anchor.retailPts - CandidateRestartPts) / 1000f;
                        SampleActors(actors, localSeconds);

                        CombinedCaptureRecord combined = new CombinedCaptureRecord
                        {
                            retailPts = anchor.retailPts,
                            timeBase = "1/1000",
                            localSeconds = localSeconds,
                            phase = anchor.phase,
                            roots = new RootCaptureRecord[Roots.Length],
                        };

                        string compositeName = "composite_frame_" +
                            anchor.retailPts.ToString("D5", CultureInfo.InvariantCulture) +
                            ".png";
                        string compositePath = Path.Combine(outputDirectory, compositeName);
                        combined.composite = CaptureFrame(
                            camera,
                            target,
                            readback,
                            compositeName,
                            compositePath);

                        for (int rootIndex = 0; rootIndex < Roots.Length; rootIndex++)
                        {
                            // Capture each root against the same camera and
                            // target while the other two are hidden. This
                            // keeps per-root and composite coverage comparable.
                            SetActorVisibility(actors, rootIndex, localSeconds);
                            string rootName = Roots[rootIndex].key + "_frame_" +
                                anchor.retailPts.ToString("D5", CultureInfo.InvariantCulture) +
                                ".png";
                            string rootPath = Path.Combine(outputDirectory, rootName);
                            RootCaptureRecord rootRecord = new RootCaptureRecord
                            {
                                effectRoot = Roots[rootIndex].effectRoot,
                                effectActive = IsActive(Roots[rootIndex], localSeconds),
                                effectState = StateFor(Roots[rootIndex], localSeconds),
                                clipSampleSeconds = ClipSampleTime(localSeconds),
                                clipClampedAfterEnd = localSeconds > SharedClipStopTime,
                                frame = CaptureFrame(
                                    camera,
                                    target,
                                    readback,
                                    rootName,
                                    rootPath),
                            };
                            combined.roots[rootIndex] = rootRecord;
                        }

                        // Restore all roots for the next combined sample.
                        SetAllActorVisibility(actors, localSeconds);
                        manifest.captures[anchorIndex] = combined;
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
                    for (int index = 0; index < actors.Length; index++)
                        Release(actors[index]);
                    if (captureScene.IsValid())
                        EditorSceneManager.CloseScene(captureScene, true);
                    if (previousScene.IsValid())
                        SceneManager.SetActiveScene(previousScene);
                }

                ValidateManifest(manifestPath);
                Debug.Log(
                    "[Endfield Li Zhiyan] combined start_01+02+03 diagnostic visual " +
                    "capture complete: " + manifestPath + "; anchors=" + Anchors.Length +
                    "; visibleAdmission=false; comparesRetailPixels=false.");
            }
            catch (Exception exception)
            {
                Debug.LogError(
                    "[Endfield Li Zhiyan] combined diagnostic visual capture failed: " +
                    exception);
                throw;
            }
        }

        [MenuItem("Endfield/Character Recovery Lab/Validate Li Zhiyan start_01+02+03 Visual Capture")]
        public static void ValidateCommandLine()
        {
            ValidateSourceSpec();
            ValidateManifest(Path.Combine(
                RepositoryAbsolute(OutputDirectoryRelativePath),
                ManifestFileName));
            Debug.Log(
                "[Endfield Li Zhiyan] combined diagnostic visual capture manifest " +
                "validated; visibleAdmission=false; comparesRetailPixels=false.");
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
            Require(spec.clock != null &&
                spec.clock.retailTimeBase == "1/1000" &&
                spec.clock.restartCandidatePts == CandidateRestartPts &&
                spec.clock.localTimeMapping ==
                "localSeconds=(retailPts-37967)/1000",
                "Capture spec candidate clock drifted");
            Require(spec.sharedMaterialClip != null &&
                spec.sharedMaterialClip.name == SharedClipName &&
                Math.Abs(spec.sharedMaterialClip.lengthSeconds - SharedClipStopTime) <
                0.00001f,
                "Capture spec shared clip identity drifted");
            Require(spec.effectLifetimes != null && spec.effectLifetimes.Length == 3,
                "Capture spec effect lifetime census drifted");
            for (int rootIndex = 0; rootIndex < Roots.Length; rootIndex++)
            {
                EffectLifetime row = FindLifetime(spec, Roots[rootIndex].effectRoot);
                Require(row != null &&
                    Math.Abs(row.durationSeconds - Roots[rootIndex].durationSeconds) <
                    0.00001f &&
                    row.startRetailPts == CandidateRestartPts,
                    "Capture spec lifetime drifted for " + Roots[rootIndex].effectRoot);
            }
        }

        private static EffectLifetime FindLifetime(
            CaptureSpec spec,
            string effectRoot)
        {
            for (int index = 0; index < spec.effectLifetimes.Length; index++)
            {
                EffectLifetime row = spec.effectLifetimes[index];
                if (row != null && row.effectRoot == effectRoot)
                    return row;
            }
            return null;
        }

        private static GameObject[] LoadPrefabs()
        {
            GameObject[] prefabs = new GameObject[Roots.Length];
            for (int index = 0; index < Roots.Length; index++)
            {
                prefabs[index] = AssetDatabase.LoadAssetAtPath<GameObject>(
                    Roots[index].prefabPath);
                Require(prefabs[index] != null,
                    "Diagnostic prefab is missing: " + Roots[index].prefabPath);
            }
            return prefabs;
        }

        private static void ValidateSharedClipIdentity(GameObject[] actors)
        {
            AnimationClip sharedClip = null;
            for (int index = 0; index < actors.Length; index++)
            {
                EndfieldRecoveredStaticMeshEffectSource marker = actors[index]
                    .GetComponent<EndfieldRecoveredStaticMeshEffectSource>();
                Require(marker != null && marker.sourceStartAnimationClip != null,
                    "Diagnostic root has no source animation clip: " + Roots[index].key);
                Require(marker.effectRoot == Roots[index].effectRoot &&
                    marker.sourceStartAnimationClipPathId == SharedClipPathId &&
                    marker.sourceStartAnimationClipName == SharedClipName &&
                    Math.Abs(marker.sourceStartAnimationStopTime - SharedClipStopTime) <
                    0.00001f &&
                    Math.Abs(marker.sourceEffectDuration - Roots[index].durationSeconds) <
                    0.00001f &&
                    !marker.visibleAdmission,
                    "Diagnostic root source contract drifted: " + Roots[index].key);
                if (sharedClip == null)
                    sharedClip = marker.sourceStartAnimationClip;
                Require(sharedClip.GetInstanceID() ==
                    marker.sourceStartAnimationClip.GetInstanceID(),
                    "Sibling roots do not share one resolved AnimationClip instance");
            }
            Require(sharedClip != null && Math.Abs(sharedClip.length - SharedClipStopTime) <
                0.0001f,
                "Resolved shared AnimationClip stop time drifted");
        }

        private static void PrepareDiagnosticActor(
            GameObject actor,
            RootDefinition root)
        {
            Animator animator = actor.GetComponent<Animator>();
            if (animator != null)
                animator.enabled = false;
            EndfieldLiZhiyanBehavioralAnimationSimulation simulation =
                actor.GetComponent<EndfieldLiZhiyanBehavioralAnimationSimulation>();
            if (simulation != null)
                simulation.enabled = false;

            MeshRenderer[] renderers = actor.GetComponentsInChildren<MeshRenderer>(true);
            Require(renderers.Length > 0,
                "Diagnostic root has no MeshRenderer: " + root.effectRoot);
            for (int rendererIndex = 0; rendererIndex < renderers.Length; rendererIndex++)
            {
                MeshRenderer renderer = renderers[rendererIndex];
                Material[] source = renderer.sharedMaterials;
                Material[] instances = new Material[source.Length];
                for (int materialIndex = 0; materialIndex < source.Length; materialIndex++)
                {
                    Require(source[materialIndex] != null,
                        "Diagnostic renderer has a missing material at index " +
                        materialIndex + ": " + root.effectRoot);
                    instances[materialIndex] = new Material(source[materialIndex])
                    {
                        name = source[materialIndex].name + ".LiZhiyanCombinedCaptureInstance",
                        renderQueue = DiagnosticCaptureRenderQueue,
                    };
                    if (instances[materialIndex].HasProperty("_UseSoftBlend"))
                        instances[materialIndex].SetFloat("_UseSoftBlend", 0f);
                }
                renderer.sharedMaterials = instances;
            }
        }

        private static void SampleActors(GameObject[] actors, float localSeconds)
        {
            for (int index = 0; index < actors.Length; index++)
            {
                bool active = IsActive(Roots[index], localSeconds);
                actors[index].SetActive(active);
                if (!active)
                    continue;
                EndfieldRecoveredStaticMeshEffectSource marker = actors[index]
                    .GetComponent<EndfieldRecoveredStaticMeshEffectSource>();
                marker.sourceStartAnimationClip.SampleAnimation(
                    actors[index],
                    ClipSampleTime(localSeconds));
            }
        }

        private static bool IsActive(RootDefinition root, float localSeconds)
        {
            return localSeconds >= -ActiveEndpointEpsilon &&
                localSeconds <= root.durationSeconds + ActiveEndpointEpsilon;
        }

        private static string StateFor(RootDefinition root, float localSeconds)
        {
            if (localSeconds < -ActiveEndpointEpsilon)
                return "not_started_before_candidate_restart";
            if (localSeconds > root.durationSeconds + ActiveEndpointEpsilon)
                return "inactive_after_effect_setting_lifetime";
            if (localSeconds > SharedClipStopTime + ActiveEndpointEpsilon)
                return "active_holding_shared_clip_endpoint";
            if (Math.Abs(localSeconds - root.durationSeconds) <= ActiveEndpointEpsilon)
                return "active_through_effect_setting_endpoint";
            return "active_sampling_shared_clip";
        }

        private static float ClipSampleTime(float localSeconds)
        {
            return Mathf.Clamp(localSeconds, 0f, SharedClipStopTime);
        }

        private static void SetActorVisibility(
            GameObject[] actors,
            int visibleIndex,
            float localSeconds)
        {
            for (int index = 0; index < actors.Length; index++)
                actors[index].SetActive(index == visibleIndex &&
                    IsActive(Roots[index], localSeconds));
        }

        private static void SetAllActorVisibility(GameObject[] actors, float localSeconds)
        {
            SampleActors(actors, localSeconds);
        }

        private static Bounds CalculateBounds(GameObject[] actors)
        {
            Renderer[] firstRenderers = actors[0].GetComponentsInChildren<Renderer>(true);
            Require(firstRenderers.Length > 0, "Diagnostic roots have no renderers");
            Bounds bounds = new Bounds(
                firstRenderers[0].bounds.center,
                firstRenderers[0].bounds.size);
            for (int actorIndex = 0; actorIndex < actors.Length; actorIndex++)
            {
                Renderer[] renderers = actors[actorIndex]
                    .GetComponentsInChildren<Renderer>(true);
                for (int rendererIndex = 0; rendererIndex < renderers.Length; rendererIndex++)
                    bounds.Encapsulate(renderers[rendererIndex].bounds);
            }
            Require(bounds.size.x > 0.0001f && bounds.size.y > 0.0001f,
                "Diagnostic roots have trivial renderer bounds");
            return bounds;
        }

        private static Camera CreateAutoFramedCamera(
            Bounds bounds,
            out GameObject cameraObject)
        {
            cameraObject = new GameObject("LiZhiyanCombinedDiagnosticCaptureCamera");
            Camera camera = cameraObject.AddComponent<Camera>();
            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = new Color(0f, 0f, 0f, 0f);
            camera.fieldOfView = 35f;
            camera.aspect = (float)Width / Height;
            camera.nearClipPlane = 0.01f;
            camera.farClipPlane = 100f;

            float verticalHalfFov = camera.fieldOfView * Mathf.Deg2Rad * 0.5f;
            float horizontalHalfFov = Mathf.Atan(
                Mathf.Tan(verticalHalfFov) * camera.aspect);
            float verticalDistance = bounds.extents.y / Mathf.Tan(verticalHalfFov);
            float horizontalDistance = bounds.extents.x / Mathf.Tan(horizontalHalfFov);
            float distance = Mathf.Max(verticalDistance, horizontalDistance) * 1.15f +
                bounds.extents.z + 0.05f;
            distance = Mathf.Max(distance, 0.5f);
            camera.transform.position = bounds.center + Vector3.back * distance;
            camera.transform.rotation = Quaternion.LookRotation(
                bounds.center - camera.transform.position,
                Vector3.up);
            camera.nearClipPlane = Mathf.Max(
                0.01f,
                distance - bounds.extents.magnitude * 2f);
            camera.farClipPlane = distance + bounds.extents.magnitude * 2f + 1f;
            return camera;
        }

        private static RenderTexture CreateTarget()
        {
            RenderTexture target = new RenderTexture(
                Width,
                Height,
                24,
                RenderTextureFormat.ARGB32)
            {
                name = "Li Zhiyan combined diagnostic capture target",
                useMipMap = false,
                autoGenerateMips = false,
                antiAliasing = 1,
            };
            Require(target.Create(), "Could not create combined capture RenderTexture");
            return target;
        }

        private static FrameRecord CaptureFrame(
            Camera camera,
            RenderTexture target,
            Texture2D readback,
            string fileName,
            string outputPath)
        {
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
            Color32 measuredBackground = pixels[0];
            int alphaPixels = 0;
            int nonBackgroundPixels = 0;
            for (int index = 0; index < pixels.Length; index++)
            {
                Color32 pixel = pixels[index];
                if (pixel.a > CoverageAlphaThreshold)
                    alphaPixels++;
                if (Mathf.Abs(pixel.r - measuredBackground.r) > CoverageColorThreshold ||
                    Mathf.Abs(pixel.g - measuredBackground.g) > CoverageColorThreshold ||
                    Mathf.Abs(pixel.b - measuredBackground.b) > CoverageColorThreshold ||
                    Mathf.Abs(pixel.a - measuredBackground.a) > CoverageAlphaThreshold)
                    nonBackgroundPixels++;
            }

            return new FrameRecord
            {
                png = OutputDirectoryRelativePath + "/" + fileName,
                pngBytes = new FileInfo(outputPath).Length,
                pngSha256 = Sha256File(outputPath),
                width = readback.width,
                height = readback.height,
                alphaPixelCount = alphaPixels,
                alphaCoverage = (float)alphaPixels / pixels.Length,
                nonBackgroundPixelCount = nonBackgroundPixels,
                nonBackgroundCoverage = (float)nonBackgroundPixels / pixels.Length,
                measuredBackgroundRgba = new[]
                {
                    (int)measuredBackground.r,
                    (int)measuredBackground.g,
                    (int)measuredBackground.b,
                    (int)measuredBackground.a,
                },
            };
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
            Require(File.Exists(manifestPath), "Combined capture manifest is missing: " + manifestPath);
            CombinedCaptureManifest manifest = JsonUtility.FromJson<CombinedCaptureManifest>(
                File.ReadAllText(manifestPath, Encoding.UTF8));
            Require(manifest != null && manifest.schema == ExpectedManifestSchema,
                "Combined capture manifest schema drifted");
            Require(manifest.status == "diagnostic_only" &&
                !manifest.visibleAdmission && !manifest.eventOriginProven &&
                !manifest.comparesRetailPixels,
                "Combined capture manifest flags are not fail-closed");
            Require(manifest.width == Width && manifest.height == Height &&
                manifest.captures != null && manifest.captures.Length == Anchors.Length,
                "Combined capture manifest dimensions or anchor count drifted");
            Require(manifest.graphicsDeviceType != GraphicsDeviceType.Null.ToString(),
                "Combined capture manifest was produced without a real graphics backend");
            Require(string.Equals(
                manifest.sourceSpecSha256,
                Sha256File(ProjectAbsolute(SpecPath)),
                StringComparison.OrdinalIgnoreCase),
                "Combined capture source spec hash drifted");

            string outputDirectory = RepositoryAbsolute(OutputDirectoryRelativePath);
            bool[] foundVisibleRoot = new bool[Roots.Length];
            for (int anchorIndex = 0; anchorIndex < Anchors.Length; anchorIndex++)
            {
                CombinedCaptureRecord capture = manifest.captures[anchorIndex];
                CaptureAnchor expected = Anchors[anchorIndex];
                Require(capture != null && capture.retailPts == expected.retailPts &&
                    Math.Abs(capture.localSeconds - expected.localSeconds) < 0.00001f &&
                    capture.roots != null && capture.roots.Length == Roots.Length &&
                    capture.composite != null,
                    "Combined capture timing/shape drifted at PTS " + expected.retailPts);
                ValidateFrame(capture.composite, outputDirectory, expected.retailPts, "composite");
                bool anyActive = false;
                for (int rootIndex = 0; rootIndex < Roots.Length; rootIndex++)
                {
                    RootCaptureRecord root = capture.roots[rootIndex];
                    bool expectedActive = IsActive(Roots[rootIndex], expected.localSeconds);
                    anyActive |= expectedActive;
                    Require(root.effectRoot == Roots[rootIndex].effectRoot &&
                        root.effectActive == expectedActive && root.frame != null,
                        "Combined lifecycle drifted for " + Roots[rootIndex].key +
                        " at PTS " + expected.retailPts);
                    ValidateFrame(
                        root.frame,
                        outputDirectory,
                        expected.retailPts,
                        Roots[rootIndex].key);
                    if (!expectedActive)
                        Require(root.frame.nonBackgroundCoverage == 0f,
                            "Inactive root is not blank: " + Roots[rootIndex].key +
                            " at PTS " + expected.retailPts);
                    else
                        foundVisibleRoot[rootIndex] |=
                            root.frame.nonBackgroundCoverage > 0f;
                }
                if (!anyActive)
                    Require(capture.composite.nonBackgroundCoverage == 0f,
                        "All-inactive composite is not blank at PTS " +
                        expected.retailPts);
            }
            for (int rootIndex = 0; rootIndex < Roots.Length; rootIndex++)
                Require(foundVisibleRoot[rootIndex],
                    "No active capture produced visible pixels for " +
                    Roots[rootIndex].key);
        }

        private static void ValidateFrame(
            FrameRecord frame,
            string outputDirectory,
            int pts,
            string label)
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
                "composite_frame_*.png",
                "start_01_frame_*.png",
                "start_02_frame_*.png",
                "start_03_frame_*.png",
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

        private static string ProjectAbsolute(string projectRelativePath)
        {
            return Path.GetFullPath(Path.Combine(
                Directory.GetCurrentDirectory(),
                projectRelativePath.Replace('/', Path.DirectorySeparatorChar)));
        }

        private static string RepositoryAbsolute(string repositoryRelativePath)
        {
            return Path.GetFullPath(Path.Combine(
                Directory.GetCurrentDirectory(),
                "..",
                repositoryRelativePath.Replace('/', Path.DirectorySeparatorChar)));
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
        private sealed class CombinedCaptureManifest
        {
            public string schema;
            public string status;
            public bool visibleAdmission;
            public bool eventOriginProven;
            public bool comparesRetailPixels;
            public string[] sourcePrefabs;
            public string sourceSpec;
            public string sourceSpecSha256;
            public string outputDirectory;
            public int width;
            public int height;
            public int[] backgroundRgba;
            public string cameraMode;
            public string graphicsDeviceType;
            public string graphicsDeviceName;
            public int diagnosticCaptureRenderQueue;
            public int sourceMaterialRenderQueue;
            public string renderQueueOverrideReason;
            public string softBlendOverride;
            public int retailRestartCandidatePts;
            public string localTimeMapping;
            public string sharedClipName;
            public long sharedClipPathId;
            public float sharedClipStopTimeSeconds;
            public RootManifestRow[] roots;
            public CombinedCaptureRecord[] captures;
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
        private sealed class CombinedCaptureRecord
        {
            public int retailPts;
            public string timeBase;
            public float localSeconds;
            public string phase;
            public RootCaptureRecord[] roots;
            public FrameRecord composite;
        }

        [Serializable]
        private sealed class RootCaptureRecord
        {
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
        }
    }
}
