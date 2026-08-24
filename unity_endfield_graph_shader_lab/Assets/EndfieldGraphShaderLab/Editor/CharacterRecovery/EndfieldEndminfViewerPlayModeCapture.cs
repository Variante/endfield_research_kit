using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>Captures the actual Viewer Play-mode path, including SelectModel and runtime-spawned VFX.</summary>
    public static class EndfieldEndminfViewerPlayModeCapture
    {
        private const string Scene = "Assets/EndfieldGraphShaderLab/Generated/Characters/Scenes/CharacterRecoveryViewer.unity";
        private const int Width = 1920;
        private const int Height = 1080;
        // The pinned retail recording is 1920x1080 at exactly 60 fps. Keep the
        // Play-mode simulation on that clock and only thin the written PNGs
        // to 4 fps. Driving Time.captureDeltaTime at 4 fps changed particle
        // integration, AnimationEvent stepping, and every temporal producer,
        // so the old side-by-side frames were not equivalent observations.
        private const float SimulationFps = 60f;
        private const float Fps = 4f;
        private const int VideoFrameCount = 600;
        // RestartOverviewFromSelection is invoked on an editor update edge;
        // the body Animation has advanced by two 60-Hz simulation ticks before
        // the first renderable sample. Offset later requested timestamps so
        // saved frame N observes clip phase N/Fps instead of N/Fps + 2/60.
        private const float PlayModeClipLeadSeconds = 2f / SimulationFps;
        // The recovered entrance is almost six seconds long. Capture far
        // enough past its handoff to prove that the actual viewer reaches and
        // sustains overview_loop instead of stopping on the entrance pose.
        private const int FrameCount = 41;
        private static float started;
        private static bool selected;
        private static int selectionSettleFrames;
        private static int next;
        private static Camera camera;
        private static string output;
        private static float[] requestedTimes;
        private static float captureFps = Fps;
        private static readonly List<FrameRow> Frames = new List<FrameRow>();

        [Serializable]
        private sealed class Report
        {
            public string schema = "endfield.endminf-viewer-playmode-sequence.v2";
            public string status = "ok";
            public int width = Width;
            public int height = Height;
            public float fps;
            public string scene = Scene;
            public string selectionPath = "CharacterRecoveryViewerUI.SelectModel(Endminf)";
            public bool actorOnlyCapture = false;
            public bool postProcessingExplicitlyDisabled = false;
            public bool recoveredLinearUnormFinalTargetRequested;
            public string renderPipeline;
            public string cameraClearFlags;
            public string cameraBackground;
            public int enabledVolumeCount;
            public string expectedSequence = "overview_start -> overview_loop";
            public bool observedTransition;
            public bool observedSettledLoop;
            public bool observedEntranceVfx;
            public bool observedEntranceVfxCleanup;
            public FrameRow[] frames;
        }

        [Serializable]
        private sealed class FrameRow
        {
            public int index;
            public float requestedSeconds;
            public float actualSeconds;
            public float endminfPostSeconds;
            public string file;
            public int effectRootCount;
            public int admittedRenderers;
            public int activeAdmittedRenderers;
            public int admittedAliveParticles;
            public string activeBodyClip;
            public float activeBodyClipTime;
            public bool overviewTransitioning;
            public bool overviewLooping;
            public bool shadowPlaneEnabled;
            public bool shadowPlaneActive;
            public bool shadowPlaneInCameraFrustum;
            public Vector3 shadowPlaneBoundsCenter;
            public Vector3 shadowPlaneBoundsExtents;
            public string[] effectRoots;
            public ParticleRow[] liveRenderers;
            public ParticleRow[] handFamily;
            public string[] blockedRendererIdentities;
            public int changedPixelsFromPrevious;
            public long absoluteRgbDifferenceFromPrevious;
        }

        [Serializable]
        private sealed class ParticleRow
        {
            public string path;
            public string[] materials;
            public string[] shaders;
            public string[] vertexStreams;
            public string renderMode;
            public string renderAlignment;
            public float lengthScale;
            public float velocityScale;
            public float maxParticleSize;
            public bool allowRoll;
            public bool freeformStretching;
            public bool rotateWithStretchDirection;
            public Vector3 localScale;
            public float startDelay;
            public float duration;
            public float startLifetimeMin;
            public float startLifetimeMax;
            public int burstCount;
            public bool playOnAwake;
            public bool isPlaying;
            public bool isEmitting;
            public int alive;
        }

        public static void Run()
        {
            if (SystemInfo.graphicsDeviceType != GraphicsDeviceType.Direct3D12)
                throw new InvalidOperationException(
                    "Endminf Viewer capture requires -force-d3d12; repeated " +
                    "manual SRP Camera.Render calls crash Unity 2022.3's " +
                    "D3D11 geometry path with an outVertices assertion.");
            // Exercise the same explicit reproduction profile as
            // open_character_recovery_lab.bat. Batch validation must not
            // silently fall back to the preserved gacha-room presentation
            // merely because its parent shell lacks these process variables.
            string[] reproductionFlags = {
                "ENDFIELD_ENDMINF_VISUAL_COMPATIBILITY",
                "ENDFIELD_ENDMINF_LITEFFECT_VISUAL_COMPAT",
                "ENDFIELD_ENDMINF_BACKDROP_VISUAL_COMPATIBILITY",
                "ENDFIELD_RECOVERED_CHARINFO_READY_SUBSET_DIAGNOSTIC",
                "ENDFIELD_RECOVERED_SOURCE_ENERGY_CORE",
                "ENDFIELD_RECOVERED_VISIBILITY_SH",
                "ENDFIELD_RECOVERED_LINEAR_UNORM_FINAL_TARGET",
                "ENDFIELD_RECOVERED_CHARINFO_BACKGROUND_PORTRAIT"
            };
            foreach (string flag in reproductionFlags)
                Environment.SetEnvironmentVariable(flag, "1");
            EditorSceneManager.OpenScene(Scene, OpenSceneMode.Single);
            Frames.Clear();
            next = 0;
            selected = false;
            selectionSettleFrames = 0;
            bool fineWindow = Environment.GetEnvironmentVariable(
                "ENDFIELD_ENDMINF_CAPTURE_FINE_WINDOW") == "1";
            bool videoExport = Environment.GetEnvironmentVariable(
                "ENDFIELD_ENDMINF_CAPTURE_VIDEO_EXPORT") == "1";
            captureFps = videoExport ? SimulationFps : Fps;
            output = Path.GetFullPath(Path.Combine(Application.dataPath,
                videoExport
                    ? "../exports/endminf_overview/frames"
                    : fineWindow
                        ? "../scratch/character_recovery/endminf_viewer_playmode_fine_window"
                        : "../scratch/character_recovery/endminf_viewer_playmode_sequence"));
            requestedTimes = videoExport
                ? Enumerable.Range(0, VideoFrameCount).Select(value =>
                    Mathf.Max(0f, value / SimulationFps - PlayModeClipLeadSeconds)).ToArray()
                : fineWindow
                ? Enumerable.Range(0, 25).Select(value => 4.30f + value / 60f).ToArray()
                : Enumerable.Range(0, FrameCount).Select(value =>
                    Mathf.Max(0f, value / Fps - PlayModeClipLeadSeconds)).ToArray();
            Directory.CreateDirectory(output);
            EditorApplication.playModeStateChanged += State;
            EditorApplication.EnterPlaymode();
        }

        private static void State(PlayModeStateChange state)
        {
            if (state == PlayModeStateChange.EnteredPlayMode)
            {
                started = Time.time;
                Time.captureDeltaTime = 1f / SimulationFps;
                EditorApplication.update += Tick;
            }
            else if (state == PlayModeStateChange.EnteredEditMode)
            {
                Time.captureDeltaTime = 0f;
                EditorApplication.Exit(0);
            }
        }

        private static void Tick()
        {
            CharacterRecoveryViewerUI viewer = UnityEngine.Object.FindObjectOfType<CharacterRecoveryViewerUI>(true);
            if (viewer == null) return;
            if (!selected)
            {
                IList models = (IList)typeof(CharacterRecoveryViewerUI)
                    .GetField("models", BindingFlags.Instance | BindingFlags.NonPublic).GetValue(viewer);
                int index = -1;
                for (int i = 0; i < models.Count; i++)
                {
                    object model = models[i];
                    FieldInfo field = model.GetType().GetField("RootName",
                        BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
                    if (string.Equals((string)field.GetValue(model), "Endminf", StringComparison.OrdinalIgnoreCase))
                    { index = i; break; }
                }
                if (index < 0) return;
                MethodInfo select = typeof(CharacterRecoveryViewerUI).GetMethod("SelectModel",
                    BindingFlags.Instance | BindingFlags.NonPublic);
                // Force the same real selection edge even when editor state happened
                // to start with Endminf selected; the runtime VFX contract is owned by
                // RestartOverviewFromSelection, not by merely finding an active actor.
                select.Invoke(viewer, new object[] { -1 });
                select.Invoke(viewer, new object[] { index });
                camera = Camera.main ?? UnityEngine.Object.FindObjectOfType<Camera>();
                selected = true;
                // Enabling the actor schedules its one-frame delayed Overview
                // restart. Do not establish capture time zero until that edge
                // has drained; otherwise frame 0 precedes a body/effect reset
                // and every later reference pair is offset by roughly 0.47 s.
                selectionSettleFrames = 2;
                return;
            }

            if (selectionSettleFrames > 0)
            {
                selectionSettleFrames--;
                if (selectionSettleFrames == 0 &&
                    CharacterRecoveryViewerUI.TryGetSelectedActorRoot(
                        out Transform selectedActor))
                {
                    EndfieldOverviewPlayback selectedOverview = selectedActor
                        .GetComponentInChildren<EndfieldOverviewPlayback>(true);
                    selectedOverview?.RestartOverviewFromSelection();
                    started = Time.time;
                }
                return;
            }

            float requested = requestedTimes[next];
            float elapsed = Time.time - started;
            if (elapsed + 0.0001f < requested) return;
            CharacterRecoveryViewerUI.TryGetSelectedActorRoot(out Transform actor);
            if (actor == null || camera == null) return;
            EndfieldOverviewPlayback overview = actor.GetComponentInChildren<EndfieldOverviewPlayback>(true);
            Animation bodyAnimation = overview != null ? overview.animationSource : null;
            if (bodyAnimation == null && overview != null)
                bodyAnimation = overview.GetComponent<Animation>();
            AnimationState activeBodyState = bodyAnimation == null
                ? null
                : bodyAnimation.Cast<AnimationState>()
                    .Where(value => value.enabled && value.weight > 0.0001f)
                    .OrderByDescending(value => value.weight)
                    .FirstOrDefault();
            // Endminf's four source bindings are stationary-position effects.
            // The runtime spawner therefore instantiates them without a parent,
            // at the actor mount's world TRS.  An actor-local census silently
            // excluded the exact runtime objects even though the camera rendered
            // them.  Search loaded scene objects and retain the fail-closed schema.
            EndfieldRecoveredParticleEffectSource[] roots = UnityEngine.Object
                .FindObjectsOfType<EndfieldRecoveredParticleEffectSource>(true)
                .Where(value => value.contractSchema == EndfieldRecoveredCharEffectSpawner.EndminfOverviewContractSchema)
                .ToArray();
            ParticleSystemRenderer[] renderers = roots
                .SelectMany(value => value.GetComponentsInChildren<ParticleSystemRenderer>(true)).ToArray();
            bool disableLitEffectParallax = Environment.GetEnvironmentVariable(
                "ENDFIELD_ENDMINF_DISABLE_LITEFFECT_PARALLAX") == "1";
            foreach (Material material in renderers
                .SelectMany(value => value.sharedMaterials)
                .Where(value => value != null &&
                    value.HasProperty("_RecoveredParallaxMarchCompatibility"))
                .Distinct())
            {
                material.SetFloat(
                    "_RecoveredParallaxMarchCompatibility",
                    disableLitEffectParallax ? 0.0f : 1.0f);
            }
            string excludedMaterial = Environment.GetEnvironmentVariable(
                "ENDFIELD_ENDMINF_CAPTURE_EXCLUDE_MATERIAL");
            if (!string.IsNullOrWhiteSpace(excludedMaterial))
            {
                foreach (ParticleSystemRenderer renderer in renderers.Where(value =>
                    value.enabled && value.sharedMaterials.Any(material => material != null &&
                        string.Equals(material.name, excludedMaterial,
                            StringComparison.Ordinal))))
                {
                    renderer.enabled = false;
                }
            }
            Color32[] pixels = Render(camera);
            int changed = 0;
            long difference = 0;
            if (next > 0)
            {
                Color32[] previous = Read(Path.Combine(output, "frame_" + (next - 1).ToString("D6") + ".png"));
                for (int i = 0; i < pixels.Length; i++)
                {
                    int delta = Math.Abs(pixels[i].r - previous[i].r) +
                        Math.Abs(pixels[i].g - previous[i].g) + Math.Abs(pixels[i].b - previous[i].b);
                    difference += delta;
                    if (delta >= 6) changed++;
                }
            }
            string file = "frame_" + next.ToString("D6") + ".png";
            Write(Path.Combine(output, file), pixels);
            EndfieldEndminfVisualCompatibilityClock.TryGetElapsed(
                out float endminfPostSeconds);
            EndfieldRecoveredCharInfoPresentation charInfoPresentation =
                UnityEngine.Object.FindObjectOfType<EndfieldRecoveredCharInfoPresentation>(true);
            Renderer shadowPlane = charInfoPresentation == null
                ? null
                : charInfoPresentation.shadowPlaneRenderer;
            bool shadowPlaneInFrustum = shadowPlane != null &&
                GeometryUtility.TestPlanesAABB(
                    GeometryUtility.CalculateFrustumPlanes(camera),
                    shadowPlane.bounds);
            Frames.Add(new FrameRow {
                index = next, requestedSeconds = requested, actualSeconds = elapsed, file = file,
                endminfPostSeconds = endminfPostSeconds,
                effectRootCount = roots.Length, admittedRenderers = renderers.Count(value => value.enabled),
                activeAdmittedRenderers = renderers.Count(value => value.enabled && value.gameObject.activeInHierarchy),
                admittedAliveParticles = renderers.Where(value => value.enabled && value.gameObject.activeInHierarchy)
                    .Sum(value => value.GetComponent<ParticleSystem>().particleCount),
                activeBodyClip = activeBodyState == null ? "" : activeBodyState.name,
                activeBodyClipTime = activeBodyState == null ? 0f : activeBodyState.time,
                overviewTransitioning = overview != null && overview.IsTransitioning,
                overviewLooping = overview != null && overview.IsLooping,
                shadowPlaneEnabled = shadowPlane != null && shadowPlane.enabled,
                shadowPlaneActive = shadowPlane != null && shadowPlane.gameObject.activeInHierarchy,
                shadowPlaneInCameraFrustum = shadowPlaneInFrustum,
                shadowPlaneBoundsCenter = shadowPlane == null ? Vector3.zero : shadowPlane.bounds.center,
                shadowPlaneBoundsExtents = shadowPlane == null ? Vector3.zero : shadowPlane.bounds.extents,
                effectRoots = roots.Select(value => value.name + " @ " + Hierarchy(value.transform)).ToArray(),
                liveRenderers = renderers.Where(value => value.enabled &&
                        value.gameObject.activeInHierarchy &&
                        value.GetComponent<ParticleSystem>().particleCount > 0)
                    .Select(value => Particle(value))
                    .OrderBy(value => value.path, StringComparer.Ordinal)
                    .ToArray(),
                handFamily = renderers.Where(value =>
                    value.GetComponentInParent<EndfieldRecoveredParticleEffectSource>(true) is EndfieldRecoveredParticleEffectSource owner &&
                    (owner.name.IndexOf("_03", StringComparison.Ordinal) >= 0 || owner.name.IndexOf("_04", StringComparison.Ordinal) >= 0))
                    .Select(value => Particle(value)).ToArray(),
                blockedRendererIdentities = renderers.Where(value => !value.enabled)
                    .Select(value => Hierarchy(value.transform) + " | " +
                        string.Join(", ", value.sharedMaterials.Select(material =>
                            material == null ? "<null>" : material.name + " -> " +
                                (material.shader == null ? "<null shader>" : material.shader.name))))
                    .OrderBy(value => value, StringComparer.Ordinal).ToArray(),
                changedPixelsFromPrevious = changed, absoluteRgbDifferenceFromPrevious = difference
            });
            next++;
            if (next < requestedTimes.Length) return;

            bool observedTransition = Frames.Any(value => value.overviewTransitioning);
            bool observedSettledLoop = Frames.Any(value => value.overviewLooping &&
                value.activeBodyClip.IndexOf("overview_loop", StringComparison.OrdinalIgnoreCase) >= 0 &&
                !value.overviewTransitioning);
            bool observedEntranceVfx = Frames.Any(value =>
                value.activeBodyClip.IndexOf("overview_start", StringComparison.OrdinalIgnoreCase) >= 0 &&
                value.effectRootCount == 4 && value.admittedRenderers > 0 &&
                value.activeAdmittedRenderers > 0 && value.admittedAliveParticles > 0);
            bool observedEntranceVfxCleanup = Frames.Any(value =>
                value.overviewLooping && !value.overviewTransitioning && value.effectRootCount == 0);
            Report report = new Report {
                fps = captureFps,
                recoveredLinearUnormFinalTargetRequested =
                    HDRenderPipeline.IsRecoveredLinearUnormFinalTargetRequested(),
                renderPipeline = GraphicsSettings.currentRenderPipeline == null ? "BuiltIn" : GraphicsSettings.currentRenderPipeline.GetType().FullName,
                cameraClearFlags = camera.clearFlags.ToString(), cameraBackground = camera.backgroundColor.ToString("F5"),
                enabledVolumeCount = UnityEngine.Object.FindObjectsOfType<MonoBehaviour>(true).Count(value =>
                    value.enabled && value.gameObject.activeInHierarchy &&
                    value.GetType().Name.IndexOf("Volume", StringComparison.OrdinalIgnoreCase) >= 0),
                observedTransition = observedTransition,
                observedSettledLoop = observedSettledLoop,
                observedEntranceVfx = observedEntranceVfx,
                observedEntranceVfxCleanup = observedEntranceVfxCleanup,
                frames = Frames.ToArray()
            };
            File.WriteAllText(Path.Combine(output, "report.json"), JsonUtility.ToJson(report, true));
            bool fineWindow = Environment.GetEnvironmentVariable(
                "ENDFIELD_ENDMINF_CAPTURE_FINE_WINDOW") == "1";
            bool videoExport = Environment.GetEnvironmentVariable(
                "ENDFIELD_ENDMINF_CAPTURE_VIDEO_EXPORT") == "1";
            if (!fineWindow && (!observedTransition || !observedSettledLoop ||
                !observedEntranceVfx || !observedEntranceVfxCleanup))
                throw new InvalidOperationException(
                    "Endminf Viewer capture did not observe the complete " +
                    "overview_start + entrance VFX -> overview_loop + VFX cleanup sequence");
            if (!fineWindow && !videoExport)
                BuildSideBySideComparison();
            Debug.Log("PASS Endminf actual Viewer Play-mode sequence: roots=" + Frames.Last().effectRootCount +
                " admitted=" + Frames.Last().admittedRenderers + " output=" + output);
            EditorApplication.update -= Tick;
            EditorApplication.ExitPlaymode();
        }


        private static void BuildSideBySideComparison()
        {
            string repo = Directory.GetParent(
                Directory.GetParent(Application.dataPath).FullName).FullName;
            string reference = Path.Combine(
                repo, "videos", "2026-08-21_20-15-17.mkv");
            if (!File.Exists(reference))
                throw new FileNotFoundException(
                    "Endminf reference video is missing", reference);

            string sideBySide = Path.Combine(output, "reference_vs_unity_4fps.png");
            // The supplied recording shows Endminf from approximately 3.5 to
            // 10.5 seconds. Keep the visual sheet on that bounded interval;
            // the JSON capture still continues through ten Viewer seconds to
            // validate the settled loop independently.
            // Pair matching timestamps first, then tile those pairs. This
            // keeps every retail frame immediately beside its Unity frame
            // instead of presenting two independently tiled sequences.
            // A bounded 60-Hz sweep now pairs retail sample N with Unity sample
            // N+1: retail frame 17 at 7.89 s matches Unity frame 18 at body clip
            // 4.5009 s. Start Unity at file 1 so each tile is a matched pair,
            // rather than two independently indexed sequences.
            RunFfmpeg("-y -v error -ss 3.64 -t 7 -i " + Quote(reference) +
                " -framerate 4 -start_number 1 -t 7 -i " +
                Quote(Path.Combine(output, "frame_%06d.png")) +
                " -filter_complex \"[0:v]fps=4,scale=384:-1[reference];" +
                "[1:v]scale=384:-1[unity];[reference][unity]hstack=inputs=2," +
                "tile=4x7\" -frames:v 1 " + Quote(sideBySide));
        }

        private static void RunFfmpeg(string arguments)
        {
            var start = new System.Diagnostics.ProcessStartInfo("ffmpeg", arguments)
            {
                UseShellExecute = false,
                CreateNoWindow = true
            };
            using (System.Diagnostics.Process process =
                   System.Diagnostics.Process.Start(start))
            {
                process.WaitForExit();
                if (process.ExitCode != 0)
                    throw new InvalidOperationException(
                        "ffmpeg comparison step failed: " + arguments);
            }
        }

        private static string Quote(string value)
        {
            return "\"" + value.Replace("\"", "\\\"") + "\"";
        }

        private static ParticleRow Particle(ParticleSystemRenderer renderer)
        {
            ParticleSystem system = renderer.GetComponent<ParticleSystem>();
            ParticleSystem.MainModule main = system.main;
            ParticleSystem.EmissionModule emission = system.emission;
            var vertexStreams = new List<ParticleSystemVertexStream>();
            renderer.GetActiveVertexStreams(vertexStreams);
            return new ParticleRow {
                path = Hierarchy(renderer.transform),
                materials = renderer.sharedMaterials.Select(material =>
                    material == null ? "<null>" : material.name).ToArray(),
                shaders = renderer.sharedMaterials.Select(material =>
                    material == null || material.shader == null
                        ? "<null>"
                        : material.shader.name).ToArray(),
                vertexStreams = vertexStreams.Select(value => value.ToString()).ToArray(),
                renderMode = renderer.renderMode.ToString(),
                renderAlignment = renderer.alignment.ToString(),
                lengthScale = renderer.lengthScale,
                velocityScale = renderer.velocityScale,
                maxParticleSize = renderer.maxParticleSize,
                allowRoll = renderer.allowRoll,
                freeformStretching = renderer.freeformStretching,
                rotateWithStretchDirection = renderer.rotateWithStretchDirection,
                localScale = renderer.transform.localScale,
                startDelay = main.startDelay.constant,
                duration = main.duration,
                startLifetimeMin = main.startLifetime.constantMin,
                startLifetimeMax = main.startLifetime.constantMax,
                burstCount = emission.burstCount,
                playOnAwake = main.playOnAwake,
                isPlaying = system.isPlaying,
                isEmitting = system.isEmitting,
                alive = system.particleCount
            };
        }

        private static string Hierarchy(Transform value)
        {
            var names = new List<string>();
            while (value != null)
            {
                names.Add(value.name);
                value = value.parent;
            }
            names.Reverse();
            return string.Join("/", names);
        }

        private static Color32[] Render(Camera value)
        {
            bool exactFinalTarget = HDRenderPipeline.IsRecoveredLinearUnormFinalTargetRequested();
            var rt = new RenderTexture(
                Width,
                Height,
                24,
                exactFinalTarget ? RenderTextureFormat.ARGB32 : RenderTextureFormat.ARGBHalf,
                RenderTextureReadWrite.Linear);
            rt.Create(); RenderTexture old = RenderTexture.active; value.targetTexture = rt; value.Render();
            RenderTexture.active = rt; var texture = new Texture2D(Width, Height, TextureFormat.RGBA32, false, false);
            texture.ReadPixels(new Rect(0, 0, Width, Height), 0, 0); texture.Apply(); Color32[] pixels = texture.GetPixels32();
            value.targetTexture = null; RenderTexture.active = old; UnityEngine.Object.Destroy(texture); rt.Release(); UnityEngine.Object.Destroy(rt);
            return pixels;
        }

        private static Color32[] Read(string path)
        {
            var texture = new Texture2D(2, 2, TextureFormat.RGBA32, false, false);
            texture.LoadImage(File.ReadAllBytes(path)); Color32[] raw = texture.GetPixels32(); UnityEngine.Object.Destroy(texture);
            var pixels = new Color32[raw.Length];
            for (int y = 0; y < Height; y++) Array.Copy(raw, y * Width, pixels, (Height - 1 - y) * Width, Width);
            return pixels;
        }

        private static void Write(string path, Color32[] pixels)
        {
            var flipped = new Color32[pixels.Length];
            for (int y = 0; y < Height; y++) Array.Copy(pixels, y * Width, flipped, (Height - 1 - y) * Width, Width);
            var texture = new Texture2D(Width, Height, TextureFormat.RGBA32, false, false);
            texture.SetPixels32(flipped); texture.Apply(); File.WriteAllBytes(path, texture.EncodeToPNG()); UnityEngine.Object.Destroy(texture);
        }
    }
}
