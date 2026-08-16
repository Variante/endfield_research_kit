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
    /// Captures the generated Li Zhiyan start_01 diagnostic prefab at the
    /// exact local times in lizhiyan_visual_capture_spec.json.  This is an
    /// isolated editor diagnostic: it deliberately does not register a normal
    /// effect binding, compare retail pixels, or raise visible admission.
    /// </summary>
    public static class EndfieldLiZhiyanVisualCaptureHarness
    {
        private const string PrefabPath =
            "Assets/EndfieldGraphShaderLab/Generated/Diagnostics/LiZhiyanStart01/" +
            "Prefabs/P_fxui_lizhiyan_overview_start_01_DIAGNOSTIC.prefab";
        private const string SpecPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/ShaderEvidence/" +
            "LiZhiyanOverviewFinger/lizhiyan_visual_capture_spec.json";
        private const string OutputDirectoryRelativePath =
            "scratch/character_recovery/lizhiyan_start01_capture";
        private const string ManifestFileName =
            "lizhiyan_start01_capture_manifest.json";
        private const string ExpectedSpecSchema =
            "endfield.lizhiyan-visual-capture-spec.v1";
        private const string ExpectedManifestSchema =
            "endfield.lizhiyan-start01-diagnostic-capture.v1";
        private const int Width = 960;
        private const int Height = 540;
        private const int DiagnosticCaptureRenderQueue = 3704;
        private const float Start01LifetimeSeconds = 2.2f;
        private const float ActiveEndpointEpsilon = 0.000001f;
        private const byte CoverageAlphaThreshold = 8;
        private const byte CoverageColorThreshold = 8;

        [MenuItem("Endfield/Character Recovery Lab/Capture Li Zhiyan start_01 Visual Spec")]
        public static void BuildAndCapture()
        {
            string outputDirectory = RepositoryAbsolute(OutputDirectoryRelativePath);
            string manifestPath = Path.Combine(outputDirectory, ManifestFileName);
            try
            {
                Require(SystemInfo.graphicsDeviceType != GraphicsDeviceType.Null,
                    "Li Zhiyan visual capture requires a real graphics backend; " +
                    "do not run Unity with -nographics");
                CaptureSpec spec = LoadAndValidateSpec();
                GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
                Require(prefab != null, "Diagnostic Li Zhiyan start_01 prefab is missing: " + PrefabPath);

                Directory.CreateDirectory(outputDirectory);
                DeletePreviousCaptureFiles(outputDirectory);

                Scene previousScene = SceneManager.GetActiveScene();
                Scene captureScene = EditorSceneManager.NewScene(
                    NewSceneSetup.EmptyScene,
                    NewSceneMode.Single);
                GameObject actor = null;
                GameObject cameraObject = null;
                RenderTexture target = null;
                Texture2D readback = null;
                try
                {
                    actor = PrefabUtility.InstantiatePrefab(prefab, captureScene) as GameObject;
                    Require(actor != null, "Could not instantiate diagnostic Li Zhiyan prefab");
                    actor.name = "LiZhiyanStart01DiagnosticCaptureActor";
                    actor.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
                    actor.transform.localScale = Vector3.one;
                    PrepareDiagnosticActor(actor);

                    Camera camera = CreateAutoFramedCamera(actor, out cameraObject);
                    LogRenderState(actor, camera, "prepared");
                    target = CreateTarget();
                    readback = new Texture2D(Width, Height, TextureFormat.RGBA32, false, false);

                    var manifest = new CaptureManifest
                    {
                        schema = ExpectedManifestSchema,
                        status = "diagnostic_only",
                        visibleAdmission = false,
                        eventOriginProven = false,
                        comparesRetailPixels = false,
                        sourcePrefab = PrefabPath,
                        sourceSpec = SpecPath,
                        sourceSpecSha256 = Sha256File(ProjectAbsolute(SpecPath)),
                        outputDirectory = OutputDirectoryRelativePath,
                        width = Width,
                        height = Height,
                        backgroundRgba = new[] { 0, 0, 0, 0 },
                        cameraMode = "deterministic_auto_framed_perspective",
                        graphicsDeviceType = SystemInfo.graphicsDeviceType.ToString(),
                        graphicsDeviceName = SystemInfo.graphicsDeviceName,
                        diagnosticCaptureRenderQueue = DiagnosticCaptureRenderQueue,
                        sourceMaterialRenderQueue = 3704,
                        renderQueueOverrideReason = "none_source_queue_preserved",
                        softBlendOverride = "disabled_no_retail_scene_depth",
                        effectRoot = "P_fxui_lizhiyan_overview_start_01",
                        effectLifetimeSeconds = Start01LifetimeSeconds,
                        retailRestartCandidatePts = spec.clock.restartCandidatePts,
                        localTimeMapping = spec.clock.localTimeMapping,
                        captures = new CaptureRecord[spec.captures.Length],
                    };

                    for (int index = 0; index < spec.captures.Length; index++)
                    {
                        CaptureAnchor anchor = spec.captures[index];
                        bool effectActive = anchor.localSeconds <=
                            Start01LifetimeSeconds + ActiveEndpointEpsilon;
                        string pngName = string.Format(
                            CultureInfo.InvariantCulture,
                            "frame_{0:D5}.png",
                            anchor.retailPts);
                        string pngPath = Path.Combine(outputDirectory, pngName);

                        actor.SetActive(effectActive);
                        if (effectActive)
                        {
                            AnimationClip clip = GetStartClip(actor);
                            clip.SampleAnimation(
                                actor,
                                Mathf.Clamp(anchor.localSeconds, 0f, clip.length));
                        }
                        if (index == 0 || index == spec.captures.Length - 1)
                            LogRenderState(actor, camera, "sample_" + anchor.retailPts);

                        CaptureFrame(camera, target, readback, pngPath);
                        manifest.captures[index] = BuildCaptureRecord(
                            anchor,
                            pngName,
                            pngPath,
                            effectActive,
                            camera,
                            readback);
                    }

                    actor.SetActive(false);
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
                    if (actor != null)
                        UnityEngine.Object.DestroyImmediate(actor);
                    if (captureScene.IsValid())
                        EditorSceneManager.CloseScene(captureScene, true);
                    if (previousScene.IsValid())
                        SceneManager.SetActiveScene(previousScene);
                }

                ValidateManifest(manifestPath, spec);
                Debug.Log(
                    "[Endfield Li Zhiyan] start_01 diagnostic visual capture complete: " +
                    manifestPath + "; captures=" + spec.captures.Length +
                    "; visibleAdmission=false; comparesRetailPixels=false.");
            }
            catch (Exception exception)
            {
                Debug.LogError(
                    "[Endfield Li Zhiyan] start_01 diagnostic visual capture failed: " +
                    exception);
                throw;
            }
        }

        [MenuItem("Endfield/Character Recovery Lab/Validate Li Zhiyan start_01 Visual Capture")]
        public static void ValidateCommandLine()
        {
            CaptureSpec spec = LoadAndValidateSpec();
            ValidateManifest(
                Path.Combine(RepositoryAbsolute(OutputDirectoryRelativePath), ManifestFileName),
                spec);
            Debug.Log(
                "[Endfield Li Zhiyan] start_01 diagnostic visual capture manifest validated; " +
                "visibleAdmission=false; comparesRetailPixels=false.");
        }

        private static CaptureSpec LoadAndValidateSpec()
        {
            string absolutePath = ProjectAbsolute(SpecPath);
            Require(File.Exists(absolutePath), "Capture spec is missing: " + absolutePath);
            CaptureSpec spec = JsonUtility.FromJson<CaptureSpec>(
                File.ReadAllText(absolutePath, Encoding.UTF8));
            Require(spec != null, "Capture spec JSON could not be parsed");
            Require(spec.schema == ExpectedSpecSchema,
                "Capture spec schema drifted: " + spec.schema);
            Require(spec.status == "diagnostic_only" && spec.comparisonOnly,
                "Capture spec is not diagnostic-only/comparison-only");
            Require(!spec.eventOriginProven && !spec.visibleAdmission,
                "Capture spec admission/event-origin flags are not fail-closed");
            Require(spec.clock != null &&
                spec.clock.retailTimeBase == "1/1000" &&
                spec.clock.restartCandidatePts == 37967 &&
                spec.clock.localTimeMapping ==
                "localSeconds=(retailPts-37967)/1000",
                "Capture spec clock contract drifted");
            Require(spec.captures != null && spec.captures.Length == 19,
                "Capture spec must contain exactly 19 anchors");
            Require(spec.effectLifetimes != null && spec.effectLifetimes.Length == 3,
                "Capture spec effect lifetime census drifted");
            bool foundStart01 = false;
            for (int index = 0; index < spec.effectLifetimes.Length; index++)
            {
                EffectLifetime lifetime = spec.effectLifetimes[index];
                if (lifetime == null || lifetime.effectRoot !=
                    "P_fxui_lizhiyan_overview_start_01")
                    continue;
                foundStart01 = true;
                Require(Math.Abs(lifetime.durationSeconds - Start01LifetimeSeconds) < 0.00001f &&
                    lifetime.startRetailPts == 37967 && lifetime.endRetailPts == 40167 &&
                    Math.Abs(lifetime.startLocalSeconds) < 0.00001f &&
                    Math.Abs(lifetime.endLocalSeconds - Start01LifetimeSeconds) < 0.00001f,
                    "Capture spec start_01 lifetime endpoint drifted");
            }
            Require(foundStart01, "Capture spec has no start_01 lifetime row");
            Require(spec.sharedMaterialClip != null &&
                Math.Abs(spec.sharedMaterialClip.lengthSeconds - 6.366667f) < 0.00001f &&
                spec.sharedMaterialClip.nearestCapturePts == 44334,
                "Capture spec shared material clip endpoint drifted");

            int[] expectedPts =
            {
                37967, 38000, 38167, 38183, 39934, 40000, 40167,
                40834, 40867, 41967, 42000, 42467, 42967, 43000,
                43900, 44000, 44334, 44967, 46000,
            };
            for (int index = 0; index < expectedPts.Length; index++)
            {
                CaptureAnchor anchor = spec.captures[index];
                Require(anchor != null && anchor.retailPts == expectedPts[index],
                    "Capture spec PTS anchor drifted at index " + index);
                Require(anchor.timeBase == "1/1000",
                    "Capture spec time base drifted at PTS " + expectedPts[index]);
                float expectedLocal = (expectedPts[index] - 37967) / 1000f;
                Require(Math.Abs(anchor.localSeconds - expectedLocal) < 0.00001f,
                    "Capture spec local time drifted at PTS " + expectedPts[index]);
                Require(!string.IsNullOrEmpty(anchor.phase),
                    "Capture spec phase is empty at PTS " + expectedPts[index]);
            }
            return spec;
        }

        private static void PrepareDiagnosticActor(GameObject actor)
        {
            Animator animator = actor.GetComponent<Animator>();
            if (animator != null)
                animator.enabled = false;
            EndfieldLiZhiyanBehavioralAnimationSimulation simulation =
                actor.GetComponent<EndfieldLiZhiyanBehavioralAnimationSimulation>();
            if (simulation != null)
                simulation.enabled = false;

            // Material curves are sampled onto transient instance materials so
            // this diagnostic never mutates generated material assets.
            MeshRenderer[] renderers = actor.GetComponentsInChildren<MeshRenderer>(true);
            for (int index = 0; index < renderers.Length; index++)
            {
                MeshRenderer renderer = renderers[index];
                Material[] source = renderer.sharedMaterials;
                Material[] instances = new Material[source.Length];
                for (int materialIndex = 0; materialIndex < source.Length; materialIndex++)
                {
                    Require(source[materialIndex] != null,
                        "Diagnostic renderer has a missing material at index " + materialIndex);
                    instances[materialIndex] = new Material(source[materialIndex])
                    {
                        name = source[materialIndex].name + ".LiZhiyanCaptureInstance",
                        // Preserve the serialized source queue. This Li-only
                        // shader does not request the exact scene-MV compositor,
                        // so the ordinary transparent owner accepts queue 3704.
                        renderQueue = DiagnosticCaptureRenderQueue,
                    };
                    if (instances[materialIndex].HasProperty("_UseSoftBlend"))
                        instances[materialIndex].SetFloat("_UseSoftBlend", 0f);
                }
                renderer.sharedMaterials = instances;
            }
        }

        private static AnimationClip GetStartClip(GameObject actor)
        {
            EndfieldRecoveredStaticMeshEffectSource marker =
                actor.GetComponent<EndfieldRecoveredStaticMeshEffectSource>();
            Require(marker != null && marker.sourceStartAnimationClip != null,
                "Diagnostic prefab has no source start animation clip");
            Require(marker.sourceStartAnimationClipName ==
                "A_fxui__lizhiyan_overview_start_01" &&
                marker.sourceStartAnimationClipPathId == 7360398354216100382L,
                "Diagnostic start animation identity drifted");
            return marker.sourceStartAnimationClip;
        }

        private static Camera CreateAutoFramedCamera(GameObject actor, out GameObject cameraObject)
        {
            Bounds bounds = CalculateBounds(actor);
            cameraObject = new GameObject("LiZhiyanStart01DiagnosticCaptureCamera");
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

        private static void LogRenderState(GameObject actor, Camera camera, string phase)
        {
            MeshRenderer[] renderers = actor.GetComponentsInChildren<MeshRenderer>(true);
            for (int rendererIndex = 0; rendererIndex < renderers.Length; rendererIndex++)
            {
                MeshRenderer renderer = renderers[rendererIndex];
                Material material = renderer.sharedMaterial;
                Debug.Log(
                    "[Endfield Li Zhiyan capture state] " + phase +
                    "; renderer=" + renderer.name +
                    "; active=" + renderer.gameObject.activeInHierarchy +
                    "; enabled=" + renderer.enabled +
                    "; bounds=" + renderer.bounds +
                    "; viewportCenter=" + camera.WorldToViewportPoint(renderer.bounds.center) +
                    "; shader=" + (material != null && material.shader != null
                        ? material.shader.name : "null") +
                    "; shaderSupported=" + (material != null && material.shader != null &&
                        material.shader.isSupported) +
                    "; passCount=" + (material != null ? material.passCount : -1) +
                    "; queue=" + (material != null ? material.renderQueue : -1) +
                    "; tintAlpha=" + GetFloatOrNaN(material, "_TintColorAlpha") +
                    "; tintIntensity=" + GetFloatOrNaN(material, "_TintColorIntensity") +
                    "; procedureAlpha=" + GetFloatOrNaN(material, "_ProcedureAlpha") +
                    "; dissolve=" + GetFloatOrNaN(material, "_UseDissolve") +
                    "; dissolveSchedule=" + GetFloatOrNaN(material, "_DissolveScheduleOffset") +
                    "; softBlend=" + GetFloatOrNaN(material, "_UseSoftBlend"));
            }
        }

        private static float GetFloatOrNaN(Material material, string propertyName)
        {
            return material != null && material.HasProperty(propertyName)
                ? material.GetFloat(propertyName)
                : float.NaN;
        }

        private static Bounds CalculateBounds(GameObject actor)
        {
            Renderer[] renderers = actor.GetComponentsInChildren<Renderer>(true);
            Require(renderers.Length > 0, "Diagnostic prefab has no renderers");
            Bounds bounds = new Bounds(renderers[0].bounds.center, renderers[0].bounds.size);
            for (int index = 1; index < renderers.Length; index++)
                bounds.Encapsulate(renderers[index].bounds);
            Require(bounds.size.x > 0.0001f && bounds.size.y > 0.0001f,
                "Diagnostic prefab renderer bounds are trivial");
            return bounds;
        }

        private static RenderTexture CreateTarget()
        {
            var target = new RenderTexture(Width, Height, 24, RenderTextureFormat.ARGB32)
            {
                name = "Li Zhiyan start_01 diagnostic capture target",
                useMipMap = false,
                autoGenerateMips = false,
                antiAliasing = 1,
            };
            Require(target.Create(), "Could not create diagnostic capture RenderTexture");
            return target;
        }

        private static void CaptureFrame(
            Camera camera,
            RenderTexture target,
            Texture2D readback,
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
        }

        private static CaptureRecord BuildCaptureRecord(
            CaptureAnchor anchor,
            string pngName,
            string pngPath,
            bool effectActive,
            Camera camera,
            Texture2D readback)
        {
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
                {
                    nonBackgroundPixels++;
                }
            }

            return new CaptureRecord
            {
                retailPts = anchor.retailPts,
                timeBase = "1/1000",
                localSeconds = anchor.localSeconds,
                phase = anchor.phase,
                effectActive = effectActive,
                effectState = effectActive
                    ? "active_through_start01_endpoint"
                    : "inactive_after_start01_lifetime",
                png = OutputDirectoryRelativePath + "/" + pngName,
                pngBytes = new FileInfo(pngPath).Length,
                pngSha256 = Sha256File(pngPath),
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
                cameraTransform = TransformRecord.From(camera.transform),
            };
        }

        private static void ValidateManifest(string manifestPath, CaptureSpec spec)
        {
            Require(File.Exists(manifestPath), "Capture manifest is missing: " + manifestPath);
            CaptureManifest manifest = JsonUtility.FromJson<CaptureManifest>(
                File.ReadAllText(manifestPath, Encoding.UTF8));
            Require(manifest != null && manifest.schema == ExpectedManifestSchema,
                "Capture manifest schema drifted");
            Require(manifest.status == "diagnostic_only" &&
                !manifest.visibleAdmission &&
                !manifest.eventOriginProven &&
                !manifest.comparesRetailPixels,
                "Capture manifest admission/comparison flags are not fail-closed");
            Require(manifest.width == Width && manifest.height == Height,
                "Capture manifest dimensions drifted");
            Require(!string.IsNullOrEmpty(manifest.graphicsDeviceType) &&
                manifest.graphicsDeviceType != GraphicsDeviceType.Null.ToString(),
                "Capture manifest was produced without a real graphics backend");
            Require(string.Equals(
                    manifest.sourceSpecSha256,
                    Sha256File(ProjectAbsolute(SpecPath)),
                    StringComparison.OrdinalIgnoreCase),
                "Capture manifest source spec hash drifted");
            Require(manifest.captures != null &&
                manifest.captures.Length == spec.captures.Length,
                "Capture manifest anchor count drifted");
            string outputDirectory = RepositoryAbsolute(OutputDirectoryRelativePath);
            bool foundVisibleActiveCapture = false;
            for (int index = 0; index < spec.captures.Length; index++)
            {
                CaptureAnchor expected = spec.captures[index];
                CaptureRecord actual = manifest.captures[index];
                Require(actual != null && actual.retailPts == expected.retailPts &&
                    Math.Abs(actual.localSeconds - expected.localSeconds) < 0.00001f,
                    "Capture manifest timing drifted at index " + index);
                bool expectedActive = expected.localSeconds <=
                    Start01LifetimeSeconds + ActiveEndpointEpsilon;
                Require(actual.effectActive == expectedActive,
                    "Capture manifest lifetime state drifted at PTS " + expected.retailPts);
                string expectedPng = OutputDirectoryRelativePath + "/frame_" +
                    expected.retailPts.ToString("D5", CultureInfo.InvariantCulture) + ".png";
                Require(actual.png == expectedPng,
                    "Capture manifest PNG path drifted at PTS " + expected.retailPts);
                string pngPath = Path.Combine(outputDirectory, Path.GetFileName(expectedPng));
                Require(File.Exists(pngPath), "Capture PNG is missing: " + pngPath);
                Require(actual.pngBytes == new FileInfo(pngPath).Length,
                    "Capture PNG byte count drifted at PTS " + expected.retailPts);
                Require(string.Equals(actual.pngSha256, Sha256File(pngPath),
                    StringComparison.OrdinalIgnoreCase),
                    "Capture PNG SHA-256 drifted at PTS " + expected.retailPts);
                Require(actual.width == Width && actual.height == Height,
                    "Capture PNG dimensions drifted at PTS " + expected.retailPts);
                Require(actual.alphaCoverage >= 0f && actual.alphaCoverage <= 1f &&
                    actual.nonBackgroundCoverage >= 0f && actual.nonBackgroundCoverage <= 1f,
                    "Capture coverage is out of range at PTS " + expected.retailPts);
                foundVisibleActiveCapture |= actual.effectActive &&
                    actual.nonBackgroundCoverage > 0f;
                Require(actual.effectActive || actual.nonBackgroundCoverage == 0f,
                    "Inactive start_01 capture is not blank at PTS " + expected.retailPts);
                Require(actual.cameraTransform != null &&
                    IsFinite(actual.cameraTransform.position) &&
                    IsFinite(actual.cameraTransform.rotation),
                    "Capture camera transform is invalid at PTS " + expected.retailPts);
            }
            Require(foundVisibleActiveCapture,
                "No active start_01 capture produced visible pixels");
        }

        private static bool IsFinite(float[] values)
        {
            if (values == null)
                return false;
            for (int index = 0; index < values.Length; index++)
            {
                if (float.IsNaN(values[index]) || float.IsInfinity(values[index]))
                    return false;
            }
            return true;
        }

        private static void DeletePreviousCaptureFiles(string directory)
        {
            if (!Directory.Exists(directory))
                return;
            string[] files = Directory.GetFiles(directory, "frame_*.png");
            for (int index = 0; index < files.Length; index++)
                File.Delete(files[index]);
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
                var builder = new StringBuilder(bytes.Length * 2);
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
            public CaptureAnchor[] captures;
        }

        [Serializable]
        private sealed class CaptureClock
        {
            public string retailTimeBase;
            public int restartCandidatePts;
            public string localTimeMapping;
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
        private sealed class EffectLifetime
        {
            public string effectRoot;
            public float durationSeconds;
            public int startRetailPts;
            public int endRetailPts;
            public float startLocalSeconds;
            public float endLocalSeconds;
        }

        [Serializable]
        private sealed class SharedMaterialClip
        {
            public string name;
            public float sampleRate;
            public float lengthSeconds;
            public float endRetailPts;
            public int nearestCapturePts;
        }

        [Serializable]
        private sealed class CaptureManifest
        {
            public string schema;
            public string status;
            public bool visibleAdmission;
            public bool eventOriginProven;
            public bool comparesRetailPixels;
            public string sourcePrefab;
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
            public string effectRoot;
            public float effectLifetimeSeconds;
            public int retailRestartCandidatePts;
            public string localTimeMapping;
            public CaptureRecord[] captures;
        }

        [Serializable]
        private sealed class CaptureRecord
        {
            public int retailPts;
            public string timeBase;
            public float localSeconds;
            public string phase;
            public bool effectActive;
            public string effectState;
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
            public TransformRecord cameraTransform;
        }

        [Serializable]
        private sealed class TransformRecord
        {
            public float[] position;
            public float[] rotation;

            public static TransformRecord From(Transform transform)
            {
                Quaternion rotation = transform.rotation;
                return new TransformRecord
                {
                    position = new[]
                    {
                        transform.position.x,
                        transform.position.y,
                        transform.position.z,
                    },
                    rotation = new[]
                    {
                        rotation.x,
                        rotation.y,
                        rotation.z,
                        rotation.w,
                    },
                };
            }
        }
    }
}
