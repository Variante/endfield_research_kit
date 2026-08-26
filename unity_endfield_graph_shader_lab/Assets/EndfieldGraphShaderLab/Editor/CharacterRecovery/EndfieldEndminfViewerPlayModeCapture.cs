using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
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
        // The requested deliverable retains the CharInfo grey background and
        // actor-specific background portrait, but never the foreground UI
        // controls, labels, icons, or cursor overlay. The grey carrier remains
        // visibly tagged as compatibility until SphereOutside's physical
        // presentation is source-complete.
        private const bool IncludeCharInfoBackground = true;
        private const bool IncludeBackgroundPortrait = true;
        // The pinned retail recording is 1920x1080 at exactly 60 fps. Keep the
        // Play-mode simulation on that clock and only thin the written PNGs
        // to 4 fps. Driving Time.captureDeltaTime at 4 fps changed particle
        // integration, AnimationEvent stepping, and every temporal producer,
        // so the old side-by-side frames were not equivalent observations.
        private const float SimulationFps = 60f;
        private const float Fps = 4f;
        // Match the complete no-frame-generation retail segment through the
        // sustained loop tail, rather than stopping at the former 10 s export.
        private const int VideoFrameCount = 770;
        // The supplied retail recording keeps the pointer at the lower-right
        // during Endminf's entrance. These normalized coordinates are measured
        // from that 1920x1080 capture and select the already recovered live
        // cursor-input path; they are not static game-data defaults.
        private const string RecordingGyroscopeInputX = "0.989";
        private const string RecordingGyroscopeInputY = "-0.874";
        // Wolfgd remains visible through source frame 1099, while Endminf's
        // first compared body frame is 1110. The recovered _02 post owner is
        // created on the intervening selection edge, nine simulation ticks
        // before the first local render sample. This explicit recording-only
        // pre-roll prevents both short source pulses from being shifted onto
        // comparison frames 0 and 18.
        private const string RecordingVisualPostPreRollSeconds = "0.15";
        // RestartOverviewFromSelection is invoked on an editor update edge;
        // the body Animation has advanced by two 60-Hz simulation ticks before
        // the first renderable sample. Offset later requested timestamps so
        // saved frame N observes clip phase N/Fps instead of N/Fps + 2/60.
        private const float PlayModeClipLeadSeconds = 2f / SimulationFps;
        // The recovered entrance is almost six seconds long. Capture far
        // enough past its handoff to prove that the actual viewer reaches and
        // sustains overview_loop instead of stopping on the entrance pose.
        private const int FrameCount = 41;
        private const string LitEffectCompatibilityShader =
            "Hidden/Endfield/Compatibility/Endminf/LitEffectParallax";
        private const string Suikuai1DiagnosticEnvironment =
            "ENDFIELD_ENDMINF_CAPTURE_ADMIT_SUIKUAI1";
        private const string OutputEnvironment =
            "ENDFIELD_ENDMINF_CAPTURE_OUTPUT";
        // Comma/semicolon-separated internal requested timestamps. This keeps
        // targeted retail phase matching on the exact 60 Hz simulation clock
        // without writing the 600-frame video-export sequence.
        private const string RequestedTimesEnvironment =
            "ENDFIELD_ENDMINF_CAPTURE_REQUESTED_TIMES";
        private const string SecondaryDynamicsEnvironment =
            "ENDFIELD_ENDMINF_CAPTURE_SECONDARY_DYNAMICS";
        private const string SecondaryDynamicsSolverEnvironment =
            "ENDFIELD_ENDMINF_CAPTURE_ENABLE_SECONDARY_DYNAMICS_SOLVER";
        private const string Suikuai1Material =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Effects/Overview/Materials/M_fx_common_teleport_03_p19E6A2A7AE736DA5.mat";
        private static readonly string[] ExpectedRemainingBlockedEffects = {
            "/all/Particle System (9) | ",
            "/all/glow/Particle System (10) | ",
        };
        private static float started;
        private static bool selected;
        private static int selectionSettleFrames;
        private static int next;
        private static Camera camera;
        private static string output;
        private static float[] requestedTimes;
        private static float captureFps = Fps;
        private static string captureFailure;
        private static bool capturePrePostHdr;
        private static bool capturePostStages;
        private static bool captureSecondaryDynamics;
        private static bool enableSecondaryDynamicsSolver;
        private static string prePostHdrCohort;
        private static string prePostHdrOutput;
        private static string postStagesCohort;
        private static string postStagesOutput;
        private static readonly List<FrameRow> Frames = new List<FrameRow>();

        [Serializable]
        private sealed class Report
        {
            public string schema = "endfield.endminf-viewer-playmode-sequence.v4";
            public string status = "ok";
            public int width = Width;
            public int height = Height;
            public float fps;
            public string graphicsDeviceType;
            public string scene = Scene;
            public string selectionPath = "CharacterRecoveryViewerUI.SelectModel(Endminf)";
            public bool actorOnlyCapture =
                !IncludeCharInfoBackground && !IncludeBackgroundPortrait;
            public bool charInfoBackgroundIncluded = IncludeCharInfoBackground;
            public bool backgroundPortraitIncluded = IncludeBackgroundPortrait;
            public bool foregroundUiOverlayIncluded = false;
            public bool postProcessingExplicitlyDisabled = false;
            public bool prePostHdrDiagnostic;
            public bool postStageDiagnostic;
            public string excludedMaterial;
            public string diagnosticAdmittedRenderer;
            public bool recoveredLinearUnormFinalTargetRequested;
            public string renderPipeline;
            public string cameraClearFlags;
            public string cameraBackground;
            public int enabledVolumeCount;
            public string expectedSequence = "overview_start -> overview_loop";
            public bool observedTransition;
            public bool observedSettledLoop;
            public bool observedAnimatorContract;
            public bool observedEntranceVfx;
            public bool observedEntranceVfxCleanup;
            public bool observedRotationOnlyRootMotion;
            public bool observedPrimaryRockCompatibilityBinding;
            public bool observedDeferredLightDataReady;
            public bool observedDeferredShadowDataReady;
            public bool observedDeferredPass0InputSubsetReady;
            public bool observedDeferredGBufferFrameReady;
            public bool observedEndminfM27HGBufferReady;
            public bool observedEndminfM27PresentationReady;
            public bool observedPreGBufferDepthOwnerReady;
            public bool observedCanonicalCharacterPreGBufferReady;
            public bool observedDeferredExactConsumerReady;
            public bool observedLightCookieDataReady;
            public string gyroscopeMode;
            public string gyroscopeInputX;
            public string gyroscopeInputY;
            public float visualPostPreRollSeconds;
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
            public bool animatorContractActive;
            public int currentAnimatorStateHash;
            public int nextAnimatorStateHash;
            public float animatorTransitionNormalizedTime;
            public int rootMotionCallbackCount;
            public float appliedRootDeltaRotationDegrees;
            public Vector3 rootMotionPositionDelta;
            public bool shadowPlaneEnabled;
            public bool shadowPlaneActive;
            public bool shadowPlaneInCameraFrustum;
            public Vector3 shadowPlaneBoundsCenter;
            public Vector3 shadowPlaneBoundsExtents;
            public bool deferredLightDataReady;
            public bool deferredShadowDataReady;
            public bool deferredPass0InputSubsetReady;
            public bool deferredGBufferFrameReady;
            public bool endminfM27HGBufferReady;
            public bool endminfM27PresentationReady;
            public bool preGBufferDepthOwnerReady;
            public bool canonicalCharacterPreGBufferReady;
            public bool deferredExactConsumerReady;
            public bool lightCookieDataReady;
            public Vector4 exposureWithMiscParams;
            public string[] effectRoots;
            public ParticleRow[] liveRenderers;
            public ParticleRow[] handFamily;
            public SecondaryDynamicsBoneRow[] secondaryDynamicsBones;
            public bool secondaryDynamicsSolverWriteback;
            public string secondaryDynamicsBindingFailure;
            public bool capturedSecondaryReplayEnabled;
            public bool capturedSecondaryReplayBindingValid;
            public string capturedSecondaryReplayBindingFailure;
            public float capturedSecondaryReplaySeconds;
            public int capturedSecondaryReplayLowerSample;
            public int capturedSecondaryReplayUpperSample;
            public float capturedSecondaryReplayBlend;
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

        [Serializable]
        private sealed class SecondaryDynamicsBoneRow
        {
            public string path;
            public Vector4 rootSpaceRow0;
            public Vector4 rootSpaceRow1;
            public Vector4 rootSpaceRow2;
        }

        [Serializable]
        private sealed class ReferenceSequenceSidecar
        {
            public string schema;
            public string recordingId;
            public ReferenceSegment segment;
            public ReferenceSource source;
            public ReferenceOutput output;
        }

        [Serializable]
        private sealed class ReferenceSegment
        {
            public string id;
            public int startFrame;
            public ReferenceComparison comparison;
        }

        [Serializable]
        private sealed class ReferenceComparison
        {
            public int bodyClipStartSourceFrame;
            public float bodyClipPhaseSeconds;
            public int firstVisibleSourceFrame;
            public int anchorUncertaintyFrames;
            public int unmaskedBodyStartSourceFrame;
            public int comparisonWidth;
            public int comparisonHeight;
            public string resamplingFilter;
            public int sampleCount;
            public int tileColumns;
        }

        [Serializable]
        private sealed class ReferenceSource
        {
            public float fps;
            public string sha256;
        }

        [Serializable]
        private sealed class ReferenceOutput
        {
            public float fps;
            public int frameCount;
            public int firstSourceFrame;
        }

        [Serializable]
        private sealed class ReferenceComparisonReport
        {
            public string schema = "endfield.endminf-reference-comparison.v1";
            public string recordingId;
            public string segmentId;
            public string sourceSha256;
            public int extractedStartSourceFrame;
            public int bodyClipStartSourceFrame;
            public float sourceFps;
            public float unityAnchorBodyClipPhaseSeconds;
            public string comparisonBoundary;
            public int firstVisibleSourceFrame;
            public int anchorUncertaintyFrames;
            public int unmaskedBodyStartSourceFrame;
            public int comparisonWidth;
            public int comparisonHeight;
            public string resamplingFilter;
            public float phaseErrorSpreadFrames;
            public ReferenceComparisonRow[] rows;
        }

        [Serializable]
        private sealed class ReferenceComparisonRow
        {
            public int unityFrameIndex;
            public float unitySequenceSeconds;
            public float activeBodyClipSeconds;
            public int sourceFrame;
            public int minimumSourceFrame;
            public int maximumSourceFrame;
            public int extractedFrame;
            public float phaseErrorFrames;
            public bool crystalContaminated;
        }

        public static void Run()
        {
            if (SystemInfo.graphicsDeviceType != GraphicsDeviceType.Direct3D11)
                throw new InvalidOperationException(
                    "Endminf Viewer capture requires the project's authoritative " +
                    "Direct3D11 backend; actual=" +
                    SystemInfo.graphicsDeviceType + ".");
            // Exercise the same explicit reproduction profile as
            // open_character_recovery_lab.bat. Batch validation must not
            // silently fall back to the preserved gacha-room presentation
            // merely because its parent shell lacks these process variables.
            bool exactEndminfM27 = Environment.GetEnvironmentVariable(
                "ENDFIELD_RECOVERED_ENDMINF_M27_HGBUFFER") == "1";
            string[] reproductionFlags = {
                "ENDFIELD_ENDMINF_VISUAL_COMPATIBILITY",
                "ENDFIELD_ENDMINF_LITEFFECT_VISUAL_COMPAT",
                "ENDFIELD_RECOVERED_SOURCE_ENERGY_CORE",
                "ENDFIELD_RECOVERED_VISIBILITY_SH",
                "ENDFIELD_RECOVERED_PREGBUFFER_DEPTH_OWNER",
                "ENDFIELD_RECOVERED_LINEAR_UNORM_FINAL_TARGET"
            };
            foreach (string flag in reproductionFlags)
                Environment.SetEnvironmentVariable(
                    flag,
                    exactEndminfM27 &&
                    flag == "ENDFIELD_ENDMINF_LITEFFECT_VISUAL_COMPAT"
                        ? "0"
                        : "1");
            if (exactEndminfM27)
            {
                // The exact five-target publisher owns M27 exclusively.
                // Disable the ForwardOnly compatibility renderer so the test
                // cannot accidentally admit a double publication.
                Environment.SetEnvironmentVariable(
                    "ENDFIELD_ENDMINF_LITEFFECT_VISUAL_COMPAT", "0");
            }
            Environment.SetEnvironmentVariable(
                "ENDFIELD_ENDMINF_BACKDROP_VISUAL_COMPATIBILITY",
                IncludeCharInfoBackground ? "1" : "0");
            Environment.SetEnvironmentVariable(
                "ENDFIELD_RECOVERED_CHARINFO_READY_SUBSET_DIAGNOSTIC",
                IncludeCharInfoBackground ? "1" : "0");
            Environment.SetEnvironmentVariable(
                "ENDFIELD_RECOVERED_CHARINFO_BACKGROUND_PORTRAIT",
                IncludeBackgroundPortrait ? "1" : "0");
            EndfieldRecoveredCharInfoPresentation.RefreshStandaloneSelection();
            // Character refreshes rebuild the source actor prefab and can
            // remove its generated overview-effect requests/spawner. Restore
            // the complete source-retained entrance-effect contract before the
            // scene instantiates the actor. The exact source stage is
            // disposable and may be absent between recovery batches, so the
            // binding builder preserves the existing effect prefabs and then
            // repairs the ten certified primary-rock material rows from their
            // pinned PathIDs and direct tracked assets. This remains opt-in and
            // does not broaden the four separately blocked non-primary rows.
            EndfieldEndminfOverviewEffectBindingBuilder.BuildAndValidate();
            // The overview rebuild refreshes transient source prefabs. Restore
            // the direct LitEffect rows afterward so both compatibility and
            // exact M27 owners receive the same hash-validated references.
            EndfieldEndminfLitEffectCompatibilityBindingBuilder
                .BuildAndValidate();
            if (string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(
                    EndfieldEndminfVisualCompatibilityClock.PreRollSecondsEnvironmentVariable)))
            {
                Environment.SetEnvironmentVariable(
                    EndfieldEndminfVisualCompatibilityClock.PreRollSecondsEnvironmentVariable,
                    RecordingVisualPostPreRollSeconds);
            }
            if (string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(
                    EndfieldRecoveredCharInfoGyroscopeCameraState.ModeEnvironmentVariable)))
            {
                Environment.SetEnvironmentVariable(
                    EndfieldRecoveredCharInfoGyroscopeCameraState.ModeEnvironmentVariable,
                    "recorded-input");
            }
            if (string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(
                    EndfieldRecoveredCharInfoGyroscopeCameraState.InputXEnvironmentVariable)))
            {
                Environment.SetEnvironmentVariable(
                    EndfieldRecoveredCharInfoGyroscopeCameraState.InputXEnvironmentVariable,
                    RecordingGyroscopeInputX);
            }
            if (string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(
                    EndfieldRecoveredCharInfoGyroscopeCameraState.InputYEnvironmentVariable)))
            {
                Environment.SetEnvironmentVariable(
                    EndfieldRecoveredCharInfoGyroscopeCameraState.InputYEnvironmentVariable,
                    RecordingGyroscopeInputY);
            }
            EditorSceneManager.OpenScene(Scene, OpenSceneMode.Single);
            if (exactEndminfM27)
            {
                int exactM27LayerMask = 1 << 31;
                foreach (Camera sceneCamera in
                    UnityEngine.Object.FindObjectsOfType<Camera>(true))
                    sceneCamera.cullingMask &= ~exactM27LayerMask;
            }
            Frames.Clear();
            captureFailure = null;
            next = 0;
            selected = false;
            selectionSettleFrames = 0;
            bool fineWindow = Environment.GetEnvironmentVariable(
                "ENDFIELD_ENDMINF_CAPTURE_FINE_WINDOW") == "1";
            bool videoExport = Environment.GetEnvironmentVariable(
                "ENDFIELD_ENDMINF_CAPTURE_VIDEO_EXPORT") == "1";
            string requestedTimesText = Environment.GetEnvironmentVariable(
                RequestedTimesEnvironment);
            bool targetedTimes = !string.IsNullOrWhiteSpace(requestedTimesText);
            capturePrePostHdr = Environment.GetEnvironmentVariable(
                "ENDFIELD_ENDMINF_CAPTURE_PREPOST_HDR") == "1";
            capturePostStages = Environment.GetEnvironmentVariable(
                "ENDFIELD_ENDMINF_CAPTURE_POST_STAGES") == "1";
            captureSecondaryDynamics = Environment.GetEnvironmentVariable(
                SecondaryDynamicsEnvironment) == "1";
            enableSecondaryDynamicsSolver = Environment.GetEnvironmentVariable(
                SecondaryDynamicsSolverEnvironment) == "1";
            if (capturePrePostHdr && capturePostStages)
                throw new InvalidOperationException(
                    "Pre-post HDR and five-stage post diagnostics are mutually exclusive.");
            if (targetedTimes && (fineWindow || videoExport || capturePrePostHdr))
            {
                throw new InvalidOperationException(
                    RequestedTimesEnvironment +
                    " is mutually exclusive with fixed-window, video, and pre-post HDR diagnostics.");
            }
            string excludedMaterial = Environment.GetEnvironmentVariable(
                "ENDFIELD_ENDMINF_CAPTURE_EXCLUDE_MATERIAL");
            prePostHdrCohort = string.IsNullOrWhiteSpace(excludedMaterial)
                ? "full"
                : "exclude_material=" + excludedMaterial;
            postStagesCohort = prePostHdrCohort;
            string prePostHdrRun = Environment.GetEnvironmentVariable(
                "ENDFIELD_ENDMINF_CAPTURE_PREPOST_HDR_RUN");
            if (string.IsNullOrWhiteSpace(prePostHdrRun))
                prePostHdrRun = string.IsNullOrWhiteSpace(excludedMaterial)
                    ? "full"
                    : "excluded_" + excludedMaterial;
            string postStagesRun = Environment.GetEnvironmentVariable(
                "ENDFIELD_ENDMINF_CAPTURE_POST_STAGES_RUN");
            if (string.IsNullOrWhiteSpace(postStagesRun))
                postStagesRun = string.IsNullOrWhiteSpace(excludedMaterial)
                    ? "full"
                    : "excluded_" + excludedMaterial;
            captureFps = videoExport || targetedTimes ? SimulationFps : Fps;
            string requestedOutput = Environment.GetEnvironmentVariable(
                OutputEnvironment);
            output = string.IsNullOrWhiteSpace(requestedOutput)
                ? Path.GetFullPath(Path.Combine(Application.dataPath,
                    capturePrePostHdr
                    ? "../scratch/character_recovery/endminf_viewer_prepost_hdr/" +
                        SafePathComponent(prePostHdrRun)
                    : capturePostStages
                    ? "../scratch/character_recovery/endminf_viewer_post_stages/" +
                        SafePathComponent(postStagesRun)
                    : videoExport
                    ? "../exports/endminf_overview/frames"
                    : targetedTimes
                        ? "../scratch/character_recovery/endminf_viewer_targeted_times"
                    : fineWindow
                        ? "../scratch/character_recovery/endminf_viewer_playmode_fine_window"
                        : "../scratch/character_recovery/endminf_viewer_playmode_sequence"))
                : Path.GetFullPath(requestedOutput);
            requestedTimes = targetedTimes
                ? ParseRequestedTimes(requestedTimesText)
                : capturePostStages
                ? new[] { 4.40f, 4.4333334f, 4.4666667f, 4.50f, 4.55f }
                : capturePrePostHdr
                ? Enumerable.Range(0, 19).Select(value =>
                    Mathf.Max(0f, value / Fps - PlayModeClipLeadSeconds)).ToArray()
                : videoExport
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

        public static void RunDeferredB31Probe()
        {
            string[] enabled = {
                "ENDFIELD_ENDMINF_DEFERRED_B31_PROBE",
                "ENDFIELD_RECOVERED_DEFERRED_TRANSFORM_VARIABLES",
                "ENDFIELD_RECOVERED_DEFERRED_LIGHT_DATA",
                "ENDFIELD_RECOVERED_LIGHT_COOKIE_DATA",
                "ENDFIELD_RECOVERED_CANONICAL_BINNING_BUFFER"
            };
            foreach (string flag in enabled)
                Environment.SetEnvironmentVariable(flag, "1");
            string[] excluded = {
                "ENDFIELD_RECOVERED_DEFERRED_RESOLVER_INPUT_PROBE",
                "ENDFIELD_RECOVERED_DEFERRED_RESOLVER_RESOURCE_PROBE",
                "ENDFIELD_RECOVERED_DEFERRED_EXACT_CONSUMER",
                "ENDFIELD_RECOVERED_DEFERRED_SHADOW_DATA"
            };
            foreach (string flag in excluded)
                Environment.SetEnvironmentVariable(flag, null);
            Run();
        }

        public static void RunDeferredExactConsumerProbe()
        {
            if (Environment.GetEnvironmentVariable(
                    "ENDFIELD_RECOVERED_ENDMINF_M27_EXACT_DXBC") == "1")
            {
                if (Environment.GetEnvironmentVariable(
                        "ENDFIELD_M27_FORCE_RAW_SHELL") == "1")
                    EndfieldM27ShellHashCapture.PrepareRawRuntimeVariant();
                else
                    EndfieldM27ShellHashCapture.PreparePinnedRuntimeVariant();
            }
            string[] enabled = {
                "ENDFIELD_RECOVERED_DEFERRED_EXACT_CONSUMER",
                "ENDFIELD_RECOVERED_ENDMINF_M27_PRESENTATION",
                "ENDFIELD_RECOVERED_CANONICAL_BINNING_BUFFER",
                "ENDFIELD_RECOVERED_SEPARATE_CHARACTER_SHADOW",
                "ENDFIELD_RECOVERED_LOW_RES_DIRECTIONAL_SHADOW",
                "ENDFIELD_RECOVERED_SCREEN_SHADOW_R_ATTACHMENT_DIAGNOSTIC"
            };
            foreach (string flag in enabled)
                Environment.SetEnvironmentVariable(flag, "1");
            string[] excluded = {
                "ENDFIELD_ENDMINF_DEFERRED_B31_PROBE",
                "ENDFIELD_RECOVERED_DEFERRED_RESOLVER_RESOURCE_PROBE"
            };
            foreach (string flag in excluded)
                Environment.SetEnvironmentVariable(flag, null);
            Run();
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
                EditorApplication.Exit(string.IsNullOrEmpty(captureFailure) ? 0 : 1);
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
                camera = Camera.main ?? UnityEngine.Object.FindObjectOfType<Camera>();
                select.Invoke(viewer, new object[] { -1 });
                // Source frame 1109 is the blank model-swap frame immediately
                // before Endminf first appears at 1110. Render that boundary
                // through the real pipeline so camera temporal history does
                // not self-seed from the first visible Endminf frame.
                if (camera != null)
                    Render(camera);
                select.Invoke(viewer, new object[] { index });
                if (enableSecondaryDynamicsSolver &&
                    CharacterRecoveryViewerUI.TryGetSelectedActorRoot(
                        out Transform dynamicsActor))
                {
                    EndfieldSecondaryDynamicsRuntime dynamics = dynamicsActor
                        .GetComponent<EndfieldSecondaryDynamicsRuntime>();
                    if (dynamics == null)
                        throw new InvalidOperationException(
                            "Endminf secondary-dynamics runtime is missing.");
                    dynamics.enabled = false;
                    dynamics.enableUnverifiedSolverWriteback = true;
                    dynamics.enabled = true;
                    if (!dynamics.SolverWritebackEnabled)
                    {
                        captureFailure =
                            "Endminf secondary-dynamics solver failed to initialize: " +
                            dynamics.BindingFailure;
                        selected = true;
                        Debug.LogError(captureFailure);
                        EditorApplication.update -= Tick;
                        EditorApplication.ExitPlaymode();
                        return;
                    }
                }
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

            if (requestedTimes == null || next >= requestedTimes.Length)
                return;
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
            string activeBodyClip = activeBodyState == null ? "" : activeBodyState.name;
            float activeBodyClipTime = activeBodyState == null ? 0f : activeBodyState.time;
            if (overview != null && overview.AnimatorContractActive &&
                overview.animatorSource != null)
            {
                Animator animator = overview.animatorSource;
                bool animatorTransition = animator.IsInTransition(0);
                AnimatorClipInfo[] currentClips = animator.GetCurrentAnimatorClipInfo(0);
                AnimatorClipInfo[] nextClips = animatorTransition
                    ? animator.GetNextAnimatorClipInfo(0)
                    : Array.Empty<AnimatorClipInfo>();
                AnimatorClipInfo selectedClip = currentClips
                    .Concat(nextClips)
                    .OrderByDescending(value => value.weight)
                    .FirstOrDefault();
                if (selectedClip.clip != null)
                {
                    activeBodyClip = selectedClip.clip.name;
                    AnimatorStateInfo selectedState = nextClips.Contains(selectedClip)
                        ? animator.GetNextAnimatorStateInfo(0)
                        : animator.GetCurrentAnimatorStateInfo(0);
                    activeBodyClipTime = Mathf.Repeat(
                        selectedState.normalizedTime,
                        1f) * selectedClip.clip.length;
                }
            }
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
                HashSet<string> excludedMaterials = new HashSet<string>(
                    excludedMaterial.Split(new[] { ';' },
                        StringSplitOptions.RemoveEmptyEntries)
                        .Select(value => value.Trim())
                        .Where(value => value.Length > 0),
                    StringComparer.Ordinal);
                if (excludedMaterials.Count == 0)
                    throw new InvalidOperationException(
                        "The Endminf excluded-material set is empty.");
                foreach (ParticleSystemRenderer renderer in renderers.Where(value =>
                    value.enabled && value.sharedMaterials.Any(material => material != null &&
                        excludedMaterials.Contains(material.name))))
                {
                    renderer.enabled = false;
                }
            }
            bool admitSuikuai1 = string.Equals(
                Environment.GetEnvironmentVariable(Suikuai1DiagnosticEnvironment),
                "1",
                StringComparison.Ordinal);
            if (admitSuikuai1)
            {
                ParticleSystemRenderer[] candidates = renderers.Where(value =>
                    value.transform.parent != null &&
                    value.transform.parent.name == "all" &&
                    value.name == "suikuai (1)").ToArray();
                Material material = AssetDatabase.LoadAssetAtPath<Material>(
                    Suikuai1Material);
                if (candidates.Length != 1 || material == null ||
                    material.shader == null ||
                    material.shader.name !=
                        "Hidden/Endfield/Recovered/Zhuangfy/VFXRefractMRT" ||
                    candidates[0].meshCount != 4)
                {
                    throw new InvalidOperationException(
                        "Focused suikuai (1) diagnostic source binding drifted.");
                }
                candidates[0].sharedMaterial = material;
                candidates[0].enabled = true;
            }
            if (capturePrePostHdr && next == 18)
            {
                prePostHdrOutput = Path.Combine(output, "prepost_hdr");
                Directory.CreateDirectory(prePostHdrOutput);
                EndfieldRecoveredPrePostHdrDiagnostic.Arm(
                    prePostHdrOutput,
                    "frame_000018",
                    prePostHdrCohort,
                    requested);
            }
            if (capturePostStages)
            {
                postStagesOutput = Path.Combine(output, "post_stages");
                Directory.CreateDirectory(postStagesOutput);
                EndfieldRecoveredPostStageDiagnostic.Arm(
                    postStagesOutput,
                    "frame_" + next.ToString("D6"),
                    postStagesCohort,
                    requested);
            }
            Color32[] pixels = Render(camera);
            // ReadPixels in Render synchronizes this focused D3D11 capture, so
            // the render-thread plugin callback must be observable here. Do
            // not accept a submitted event as proof that the exact M13 packet
            // actually drew.
            if (EndfieldRecoveredEndminfM13ExactRuntime.Requested &&
                EndfieldRecoveredEndminfM13ExactRuntime.HasPendingValidation &&
                !EndfieldRecoveredEndminfM13ExactRuntime
                    .ValidatePendingAfterSynchronizedRender(
                        out string m13ValidationFailure))
            {
                throw new InvalidOperationException(
                    "Exact Endminf M13 callback validation failed: " +
                    m13ValidationFailure);
            }
            if (EndfieldRecoveredEndminfM14ExactRuntime.Requested &&
                EndfieldRecoveredEndminfM14ExactRuntime.HasPendingValidation &&
                !EndfieldRecoveredEndminfM14ExactRuntime
                    .ValidatePendingAfterSynchronizedRender(
                        out string m14ValidationFailure))
            {
                throw new InvalidOperationException(
                    "Exact Endminf M14 callback validation failed: " +
                    m14ValidationFailure);
            }
            if (EndfieldRecoveredEndminfM27ExactRuntime.Requested &&
                EndfieldRecoveredEndminfM27ExactRuntime.HasPendingValidation &&
                !EndfieldRecoveredEndminfM27ExactRuntime
                    .ValidatePendingAfterSynchronizedRender(
                        out string m27ValidationFailure))
            {
                throw new InvalidOperationException(
                    "Exact Endminf M27 callback validation failed: " +
                    m27ValidationFailure);
            }
            if (capturePrePostHdr && next == 18)
                EndfieldRecoveredPrePostHdrDiagnostic.WaitForPending();
            if (capturePostStages)
                EndfieldRecoveredPostStageDiagnostic.WaitForPending();
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
            EndfieldSecondaryDynamicsRuntime secondaryDynamics = actor
                .GetComponent<EndfieldSecondaryDynamicsRuntime>();
            EndfieldCapturedSecondaryDynamicsReplay capturedReplay = actor
                .GetComponent<EndfieldCapturedSecondaryDynamicsReplay>();
            Frames.Add(new FrameRow {
                index = next, requestedSeconds = requested, actualSeconds = elapsed, file = file,
                endminfPostSeconds = endminfPostSeconds,
                effectRootCount = roots.Length, admittedRenderers = renderers.Count(value => value.enabled),
                activeAdmittedRenderers = renderers.Count(value => value.enabled && value.gameObject.activeInHierarchy),
                admittedAliveParticles = renderers.Where(value => value.enabled && value.gameObject.activeInHierarchy)
                    .Sum(value => value.GetComponent<ParticleSystem>().particleCount),
                activeBodyClip = activeBodyClip,
                activeBodyClipTime = activeBodyClipTime,
                overviewTransitioning = overview != null && overview.IsTransitioning,
                overviewLooping = overview != null && overview.IsLooping,
                animatorContractActive = overview != null && overview.AnimatorContractActive,
                currentAnimatorStateHash = overview != null ? overview.CurrentAnimatorStateHash : 0,
                nextAnimatorStateHash = overview != null ? overview.NextAnimatorStateHash : 0,
                animatorTransitionNormalizedTime = overview != null
                    ? overview.AnimatorTransitionNormalizedTime
                    : 0f,
                rootMotionCallbackCount = overview != null
                    ? overview.RootMotionCallbackCount
                    : 0,
                appliedRootDeltaRotationDegrees = overview != null
                    ? overview.AppliedRootDeltaRotationDegrees
                    : 0f,
                rootMotionPositionDelta = overview != null
                    ? overview.RootMotionPositionDelta
                    : Vector3.zero,
                shadowPlaneEnabled = shadowPlane != null && shadowPlane.enabled,
                shadowPlaneActive = shadowPlane != null && shadowPlane.gameObject.activeInHierarchy,
                shadowPlaneInCameraFrustum = shadowPlaneInFrustum,
                shadowPlaneBoundsCenter = shadowPlane == null ? Vector3.zero : shadowPlane.bounds.center,
                shadowPlaneBoundsExtents = shadowPlane == null ? Vector3.zero : shadowPlane.bounds.extents,
                deferredLightDataReady = Shader.GetGlobalFloat(
                    "_EndfieldRecoveredDeferredLightDataReady") > 0.5f,
                deferredShadowDataReady = Shader.GetGlobalFloat(
                    "_EndfieldRecoveredDeferredShadowDataReady") > 0.5f,
                deferredPass0InputSubsetReady = Shader.GetGlobalFloat(
                    "_EndfieldRecoveredDeferredPass0InputSubsetReady") > 0.5f,
                deferredGBufferFrameReady = Shader.GetGlobalFloat(
                    "_EndfieldRecoveredDeferredGBufferFrameReady") > 0.5f,
                endminfM27HGBufferReady = Shader.GetGlobalFloat(
                    "_EndfieldRecoveredEndminfM27HGBufferReady") > 0.5f,
                endminfM27PresentationReady = Shader.GetGlobalFloat(
                    "_EndfieldRecoveredEndminfM27PresentationReady") > 0.5f,
                preGBufferDepthOwnerReady = Shader.GetGlobalFloat(
                    "_EndfieldRecoveredPreGBufferDepthOwnerReady") > 0.5f,
                canonicalCharacterPreGBufferReady = Shader.GetGlobalFloat(
                    "_EndfieldRecoveredCanonicalCharacterPreGBufferReady") > 0.5f,
                deferredExactConsumerReady = Shader.GetGlobalFloat(
                    "_EndfieldRecoveredDeferredExactConsumerReady") > 0.5f,
                lightCookieDataReady = Shader.GetGlobalFloat(
                    "_EndfieldRecoveredLightCookieDataReady") > 0.5f,
                exposureWithMiscParams = Shader.GetGlobalVector(
                    "_ExposureWithMiscParams"),
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
                secondaryDynamicsBones = captureSecondaryDynamics
                    ? CaptureSecondaryDynamicsBones(actor)
                    : Array.Empty<SecondaryDynamicsBoneRow>(),
                secondaryDynamicsSolverWriteback = secondaryDynamics != null &&
                    secondaryDynamics.SolverWritebackEnabled,
                secondaryDynamicsBindingFailure = secondaryDynamics == null
                    ? "runtime missing"
                    : secondaryDynamics.BindingFailure,
                capturedSecondaryReplayEnabled = capturedReplay != null &&
                    capturedReplay.useCapturedReplay,
                capturedSecondaryReplayBindingValid = capturedReplay != null &&
                    capturedReplay.BindingValid,
                capturedSecondaryReplayBindingFailure = capturedReplay == null
                    ? "runtime missing"
                    : capturedReplay.BindingFailure,
                capturedSecondaryReplaySeconds = capturedReplay != null
                    ? capturedReplay.PlaybackSeconds
                    : 0f,
                capturedSecondaryReplayLowerSample = capturedReplay != null
                    ? capturedReplay.LowerSampleIndex
                    : -1,
                capturedSecondaryReplayUpperSample = capturedReplay != null
                    ? capturedReplay.UpperSampleIndex
                    : -1,
                capturedSecondaryReplayBlend = capturedReplay != null
                    ? capturedReplay.SampleBlend
                    : 0f,
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
            bool observedAnimatorContract = Frames.Any(value => value.animatorContractActive);
            bool observedEntranceVfx = Frames.Any(value =>
                value.activeBodyClip.IndexOf("overview_start", StringComparison.OrdinalIgnoreCase) >= 0 &&
                value.effectRootCount == 4 && value.admittedRenderers > 0 &&
                value.activeAdmittedRenderers > 0 && value.admittedAliveParticles > 0);
            bool observedEntranceVfxCleanup = Frames.Any(value =>
                value.overviewLooping && !value.overviewTransitioning && value.effectRootCount == 0);
            bool observedRotationOnlyRootMotion =
                Frames.Any(value => value.rootMotionCallbackCount > 0) &&
                Frames.All(value => value.rootMotionPositionDelta.sqrMagnitude <= 1.0e-10f);
            FrameRow firstEntranceFrame = Frames.FirstOrDefault(value =>
                value.effectRootCount == 4);
            bool observedPrimaryRockCompatibilityBinding =
                firstEntranceFrame != null &&
                firstEntranceFrame.admittedRenderers == 68 &&
                firstEntranceFrame.blockedRendererIdentities != null &&
                firstEntranceFrame.blockedRendererIdentities.Length ==
                    ExpectedRemainingBlockedEffects.Length &&
                ExpectedRemainingBlockedEffects.All(expected =>
                    firstEntranceFrame.blockedRendererIdentities.Count(value =>
                        value.Contains(expected)) == 1) &&
                Frames.Any(frame => frame.liveRenderers != null &&
                    frame.liveRenderers.Any(renderer =>
                        renderer.shaders != null &&
                        renderer.shaders.Contains(LitEffectCompatibilityShader)));
            bool exactEndminfM27Requested = string.Equals(
                Environment.GetEnvironmentVariable(
                    "ENDFIELD_RECOVERED_ENDMINF_M27_HGBUFFER"),
                "1",
                StringComparison.Ordinal);
            bool observedDeferredLightDataReady = Frames.All(value =>
                value.deferredLightDataReady);
            bool observedDeferredShadowDataReady = Frames.All(value =>
                value.deferredShadowDataReady);
            bool observedDeferredPass0InputSubsetReady = Frames.All(value =>
                value.deferredPass0InputSubsetReady);
            // M27 owns this exact sidecar only inside its retained temporal
            // packet envelope. No sidecar publication before or after that
            // envelope is the correct no-M27 state, not a readiness failure.
            float firstActorClock = Frames.Count > 0
                ? Frames[0].activeBodyClipTime
                : 0.0f;
            float firstSequenceClock = Frames.Count > 0
                ? Frames[0].actualSeconds
                : 0.0f;
            FrameRow[] requiredDeferredGBufferFrames = exactEndminfM27Requested
                ? Frames.Where(value =>
                    EndfieldRecoveredEndminfM27ExactRuntime.IsCapturedPhase(
                        firstActorClock + value.actualSeconds -
                        firstSequenceClock)).ToArray()
                : Frames.ToArray();
            bool observedDeferredGBufferFrameReady =
                requiredDeferredGBufferFrames.Length > 0 &&
                requiredDeferredGBufferFrames.All(value =>
                    value.deferredGBufferFrameReady);
            bool observedEndminfM27HGBufferReady = Frames.Any(value =>
                value.endminfM27HGBufferReady);
            bool observedEndminfM27PresentationReady = Frames.Any(value =>
                value.endminfM27PresentationReady);
            bool observedPreGBufferDepthOwnerReady = Frames.All(value =>
                value.preGBufferDepthOwnerReady);
            bool observedCanonicalCharacterPreGBufferReady = Frames.All(value =>
                value.canonicalCharacterPreGBufferReady);
            bool observedDeferredExactConsumerReady = Frames.Any(value =>
                value.deferredExactConsumerReady);
            bool observedLightCookieDataReady = Frames.All(value =>
                value.lightCookieDataReady);
            var missingObservations = new List<string>();
            if (!observedAnimatorContract) missingObservations.Add("Animator contract");
            if (!observedTransition) missingObservations.Add("start-to-loop transition");
            if (!observedSettledLoop) missingObservations.Add("settled loop");
            if (!observedEntranceVfx) missingObservations.Add("entrance VFX");
            if (!observedEntranceVfxCleanup) missingObservations.Add("entrance VFX cleanup");
            if (!observedRotationOnlyRootMotion)
                missingObservations.Add("rotation-only root motion with invariant position");
            if (!exactEndminfM27Requested &&
                !observedPrimaryRockCompatibilityBinding)
                missingObservations.Add(
                    "eleven-row LitEffect crystal compatibility plus exact suikuai (1) " +
                    "binding with two separate blocked effects");
            if (exactEndminfM27Requested && !observedEndminfM27HGBufferReady)
                missingObservations.Add(
                    "exact Endminf M27 five-MRT HGBuffer publication");
            if (!observedPreGBufferDepthOwnerReady)
                missingObservations.Add(
                    "canonical CharacterPrePass depth/stencil ownership");
            if (!observedCanonicalCharacterPreGBufferReady)
                missingObservations.Add(
                    "canonical five-MRT CharacterNPR A/B/C publication");
            if (string.Equals(
                    Environment.GetEnvironmentVariable(
                        "ENDFIELD_ENDMINF_DEFERRED_B31_PROBE"),
                    "1",
                    StringComparison.Ordinal))
            {
                if (!observedDeferredLightDataReady)
                    missingObservations.Add("Endminf deferred b31 LightData readiness");
                if (!observedLightCookieDataReady)
                    missingObservations.Add("Endminf zero-cookie LightCookieData readiness");
                if (Frames.Any(value => value.deferredShadowDataReady ||
                        value.deferredPass0InputSubsetReady))
                    missingObservations.Add(
                        "Endminf b31-only probe unexpectedly admitted unresolved b34/pass-0 readiness");
            }
            if (string.Equals(
                    Environment.GetEnvironmentVariable(
                        "ENDFIELD_RECOVERED_DEFERRED_EXACT_CONSUMER"),
                    "1",
                    StringComparison.Ordinal))
            {
                if (!observedDeferredLightDataReady)
                    missingObservations.Add("exact-consumer deferred b31 readiness");
                if (!observedDeferredShadowDataReady)
                    missingObservations.Add("exact-consumer deferred b34 readiness");
                if (!observedDeferredPass0InputSubsetReady)
                    missingObservations.Add("exact-consumer pass-0 input subset readiness");
                if (!observedDeferredGBufferFrameReady)
                    missingObservations.Add("exact-consumer five-MRT GBuffer readiness");
                if (!observedDeferredExactConsumerReady)
                    missingObservations.Add("exact-consumer submitted output");
                if (string.Equals(
                        Environment.GetEnvironmentVariable(
                            "ENDFIELD_RECOVERED_ENDMINF_M27_PRESENTATION"),
                        "1",
                        StringComparison.Ordinal) &&
                    !observedEndminfM27PresentationReady)
                {
                    missingObservations.Add(
                        "exact M27 deferred presentation readiness");
                }
                if (!observedLightCookieDataReady)
                    missingObservations.Add("exact-consumer LightCookieData readiness");
            }
            bool targetedTimes = !string.IsNullOrWhiteSpace(
                Environment.GetEnvironmentVariable(RequestedTimesEnvironment));
            Report report = new Report {
                status = targetedTimes && capturePostStages
                    ? "targeted_diagnostic_ok"
                    : targetedTimes
                    ? "targeted_ok"
                    : capturePrePostHdr || capturePostStages
                    ? "diagnostic_ok"
                    : missingObservations.Count == 0
                    ? "ok"
                    : "failed: missing " + string.Join(", ", missingObservations.ToArray()),
                prePostHdrDiagnostic = capturePrePostHdr,
                postStageDiagnostic = capturePostStages,
                excludedMaterial = Environment.GetEnvironmentVariable(
                    "ENDFIELD_ENDMINF_CAPTURE_EXCLUDE_MATERIAL") ?? string.Empty,
                diagnosticAdmittedRenderer = Environment.GetEnvironmentVariable(
                    Suikuai1DiagnosticEnvironment) == "1"
                    ? "overview_02/all/suikuai (1)"
                    : string.Empty,
                fps = captureFps,
                graphicsDeviceType = SystemInfo.graphicsDeviceType.ToString(),
                recoveredLinearUnormFinalTargetRequested =
                    HDRenderPipeline.IsRecoveredLinearUnormFinalTargetRequested(),
                renderPipeline = GraphicsSettings.currentRenderPipeline == null ? "BuiltIn" : GraphicsSettings.currentRenderPipeline.GetType().FullName,
                cameraClearFlags = camera.clearFlags.ToString(), cameraBackground = camera.backgroundColor.ToString("F5"),
                enabledVolumeCount = UnityEngine.Object.FindObjectsOfType<MonoBehaviour>(true).Count(value =>
                    value.enabled && value.gameObject.activeInHierarchy &&
                    value.GetType().Name.IndexOf("Volume", StringComparison.OrdinalIgnoreCase) >= 0),
                observedTransition = observedTransition,
                observedSettledLoop = observedSettledLoop,
                observedAnimatorContract = observedAnimatorContract,
                observedEntranceVfx = observedEntranceVfx,
                observedEntranceVfxCleanup = observedEntranceVfxCleanup,
                observedRotationOnlyRootMotion = observedRotationOnlyRootMotion,
                observedPrimaryRockCompatibilityBinding =
                    observedPrimaryRockCompatibilityBinding,
                observedDeferredLightDataReady = observedDeferredLightDataReady,
                observedDeferredShadowDataReady = observedDeferredShadowDataReady,
                observedDeferredPass0InputSubsetReady =
                    observedDeferredPass0InputSubsetReady,
                observedDeferredGBufferFrameReady =
                    observedDeferredGBufferFrameReady,
                observedEndminfM27HGBufferReady =
                    observedEndminfM27HGBufferReady,
                observedEndminfM27PresentationReady =
                    observedEndminfM27PresentationReady,
                observedPreGBufferDepthOwnerReady =
                    observedPreGBufferDepthOwnerReady,
                observedCanonicalCharacterPreGBufferReady =
                    observedCanonicalCharacterPreGBufferReady,
                observedDeferredExactConsumerReady =
                    observedDeferredExactConsumerReady,
                observedLightCookieDataReady = observedLightCookieDataReady,
                gyroscopeMode = Environment.GetEnvironmentVariable(
                    EndfieldRecoveredCharInfoGyroscopeCameraState.ModeEnvironmentVariable),
                gyroscopeInputX = Environment.GetEnvironmentVariable(
                    EndfieldRecoveredCharInfoGyroscopeCameraState.InputXEnvironmentVariable),
                gyroscopeInputY = Environment.GetEnvironmentVariable(
                    EndfieldRecoveredCharInfoGyroscopeCameraState.InputYEnvironmentVariable),
                // The _02 owner is destroyed before the full sequence report
                // is published, which deliberately clears the live clock.
                // Preserve the observed first-frame phase difference instead.
                visualPostPreRollSeconds = Frames.Count > 0
                    ? Mathf.Max(
                        0.0f,
                        Frames[0].endminfPostSeconds - Frames[0].actualSeconds)
                    : 0.0f,
                frames = Frames.ToArray()
            };
            File.WriteAllText(Path.Combine(output, "report.json"), JsonUtility.ToJson(report, true));
            bool fineWindow = Environment.GetEnvironmentVariable(
                "ENDFIELD_ENDMINF_CAPTURE_FINE_WINDOW") == "1";
            bool videoExport = Environment.GetEnvironmentVariable(
                "ENDFIELD_ENDMINF_CAPTURE_VIDEO_EXPORT") == "1";
            EditorApplication.update -= Tick;
            if (!capturePrePostHdr && !capturePostStages && !fineWindow &&
                !targetedTimes &&
                missingObservations.Count > 0)
            {
                captureFailure =
                    "Endminf Viewer capture did not observe: " +
                    string.Join(", ", missingObservations.ToArray());
                Debug.LogError(captureFailure);
                EditorApplication.ExitPlaymode();
                return;
            }
            if (!capturePrePostHdr && !capturePostStages && !fineWindow &&
                !videoExport && !targetedTimes)
            {
                try
                {
                    BuildSideBySideComparison(
                        "endminf_overview_2026-08-21",
                        "endminf_overview_start_and_loop",
                        "reference_vs_unity_4fps.png",
                        "reference_comparison.json");
                    BuildSideBySideComparison(
                        "endminf_overview_no_framegen_2026-08-24",
                        "endminf_overview_start_and_loop_no_framegen",
                        "reference_no_framegen_vs_unity_4fps.png",
                        "reference_no_framegen_comparison.json");
                }
                catch (Exception error)
                {
                    captureFailure =
                        "Endminf reference comparison failed closed: " + error.Message;
                    Debug.LogException(error);
                    EditorApplication.ExitPlaymode();
                    return;
                }
            }
            Debug.Log((capturePostStages
                    ? "PASS Endminf Viewer five-stage post diagnostic"
                    : capturePrePostHdr
                    ? "PASS Endminf Viewer pre-post HDR diagnostic"
                    : "PASS Endminf actual Viewer Play-mode sequence") +
                ": roots=" + Frames.Last().effectRootCount +
                " admitted=" + Frames.Last().admittedRenderers + " output=" + output);
            EditorApplication.ExitPlaymode();
        }


        private static void BuildSideBySideComparison(
            string recordingId,
            string segmentId,
            string sheetName,
            string reportName)
        {
            string lab = Directory.GetParent(Application.dataPath).FullName;
            ValidateReferenceSequence(lab, recordingId, segmentId);
            string sequence = Path.Combine(lab, "scratch", "character_recovery",
                "reference_sequences", recordingId, "endminf", segmentId);
            string sidecarPath = Path.Combine(sequence, "sequence.json");
            if (!File.Exists(sidecarPath))
                throw new FileNotFoundException(
                    "Validated Endminf reference sidecar is missing", sidecarPath);
            ReferenceSequenceSidecar sidecar = JsonUtility.FromJson<ReferenceSequenceSidecar>(
                File.ReadAllText(sidecarPath));
            if (sidecar == null ||
                sidecar.schema != "endfield.character-reference-sequence.v1" ||
                sidecar.recordingId != recordingId || sidecar.segment == null ||
                sidecar.segment.id != segmentId || sidecar.segment.comparison == null ||
                sidecar.source == null || sidecar.output == null)
                throw new InvalidDataException(
                    "Endminf reference sidecar lost its maintained comparison contract");
            ReferenceComparison comparison = sidecar.segment.comparison;
            if (sidecar.segment.startFrame != sidecar.output.firstSourceFrame ||
                Mathf.Abs(sidecar.source.fps - SimulationFps) > 0.0001f ||
                Mathf.Abs(sidecar.output.fps - SimulationFps) > 0.0001f ||
                comparison.bodyClipStartSourceFrame < sidecar.segment.startFrame ||
                comparison.bodyClipPhaseSeconds <= 0.0f ||
                comparison.anchorUncertaintyFrames < 0 ||
                comparison.sampleCount <= 0 || comparison.sampleCount > Frames.Count ||
                comparison.tileColumns <= 0)
                throw new InvalidDataException(
                    "Endminf reference comparison timing contract drifted");

            var rows = new List<ReferenceComparisonRow>();
            int previousSourceFrame = -1;
            float firstSequenceElapsed = Frames[0].actualSeconds;
            float firstStartClipPhase = Frames[0].activeBodyClipTime;
            float firstReferenceEffectSeconds =
                (comparison.bodyClipStartSourceFrame - sidecar.segment.startFrame) /
                sidecar.source.fps;
            bool diagnosticAnchor = comparison.anchorUncertaintyFrames > 0;
            if (Mathf.Abs(
                    firstStartClipPhase - comparison.bodyClipPhaseSeconds) > 0.00001f ||
                (!diagnosticAnchor &&
                 Mathf.Abs(firstSequenceElapsed - firstReferenceEffectSeconds) > 0.00001f))
                throw new InvalidDataException(
                    "Endminf reference absolute body/effect phase anchor drifted");
            if (diagnosticAnchor &&
                (comparison.firstVisibleSourceFrame < sidecar.segment.startFrame ||
                 comparison.bodyClipStartSourceFrame < comparison.firstVisibleSourceFrame ||
                 comparison.unmaskedBodyStartSourceFrame <=
                    comparison.bodyClipStartSourceFrame ||
                 comparison.comparisonWidth != 1920 ||
                 comparison.comparisonHeight != 1080 ||
                 comparison.resamplingFilter != "lanczos"))
                throw new InvalidDataException(
                    "Endminf diagnostic comparison boundary drifted");
            for (int index = 0; index < comparison.sampleCount; index++)
            {
                FrameRow unity = Frames[index];
                // bodyClipStartSourceFrame is the first visible decoded body
                // frame, not source clip time zero. Frames[0] is the first
                // saved Unity image and is therefore anchored directly to
                // that decoded frame. Adding its already-advanced Animator
                // phase here used to shift every pair three source frames
                // late while preserving a deceptively perfect phase residue.
                float sequenceSeconds = unity.actualSeconds - firstSequenceElapsed;
                float exactOffsetFrames = sequenceSeconds * sidecar.source.fps;
                int roundedOffsetFrames = Mathf.FloorToInt(exactOffsetFrames + 0.5f);
                int sourceFrame = comparison.bodyClipStartSourceFrame + roundedOffsetFrames;
                int extractedFrame = sourceFrame - sidecar.output.firstSourceFrame + 1;
                float referenceEffectSeconds = firstReferenceEffectSeconds +
                    exactOffsetFrames / sidecar.source.fps;
                bool startClipCrossCheck = unity.overviewTransitioning ||
                    unity.overviewLooping ||
                    Mathf.Abs(
                        unity.activeBodyClipTime - firstStartClipPhase -
                        sequenceSeconds) <= 0.002f;
                if (sourceFrame <= previousSourceFrame || extractedFrame < 1 ||
                    extractedFrame > sidecar.output.frameCount ||
                    Mathf.Abs(exactOffsetFrames - roundedOffsetFrames) > 0.075f ||
                    (!diagnosticAnchor &&
                     Mathf.Abs(referenceEffectSeconds - unity.actualSeconds) > 0.00001f) ||
                    !startClipCrossCheck)
                    throw new InvalidDataException(
                        "Endminf reference phase match is not a unique 60-Hz source sample: " +
                        "unityFrame=" + index + " sequence=" + sequenceSeconds +
                        " clip=" + unity.activeBodyClipTime +
                        " sourceFrame=" + sourceFrame);
                previousSourceFrame = sourceFrame;
                rows.Add(new ReferenceComparisonRow {
                    unityFrameIndex = unity.index,
                    unitySequenceSeconds = sequenceSeconds,
                    activeBodyClipSeconds = unity.activeBodyClipTime,
                    sourceFrame = sourceFrame,
                    minimumSourceFrame = sourceFrame - comparison.anchorUncertaintyFrames,
                    maximumSourceFrame = sourceFrame + comparison.anchorUncertaintyFrames,
                    extractedFrame = extractedFrame,
                    phaseErrorFrames = exactOffsetFrames - roundedOffsetFrames,
                    crystalContaminated = diagnosticAnchor &&
                        sourceFrame - comparison.anchorUncertaintyFrames <
                            comparison.unmaskedBodyStartSourceFrame
                });
            }
            float phaseErrorSpreadFrames = rows.Max(row => row.phaseErrorFrames) -
                rows.Min(row => row.phaseErrorFrames);
            if (phaseErrorSpreadFrames > 0.001f)
                throw new InvalidDataException(
                    "Endminf reference phase residue drifted across the comparison window: " +
                    phaseErrorSpreadFrames + " source frames");

            string sideBySide = Path.Combine(output, sheetName);
            string selectedFrames = string.Join("+", rows.Select(row =>
                "eq(n\\," + (row.extractedFrame - 1) + ")").ToArray());
            int tileRows = Mathf.CeilToInt(
                comparison.sampleCount / (float)comparison.tileColumns);
            RunFfmpeg("-y -v error -framerate 60 -start_number 1 -i " +
                Quote(Path.Combine(sequence, "frame_%06d.png")) +
                " -framerate 4 -start_number 0 -i " +
                Quote(Path.Combine(output, "frame_%06d.png")) +
                " -filter_complex \"[0:v]select='" + selectedFrames +
                "',setpts=N/(4*TB),scale=1920:1080:flags=lanczos," +
                "scale=384:-1:flags=lanczos[reference];" +
                "[1:v]trim=end_frame=" + comparison.sampleCount +
                ",setpts=N/(4*TB),scale=384:-1:flags=lanczos[unity];" +
                "[reference][unity]hstack=inputs=2,tile=" +
                comparison.tileColumns + "x" + tileRows +
                "\" -frames:v 1 " + Quote(sideBySide));

            if (diagnosticAnchor)
            {
                ReferenceComparisonRow[] cleanRows = rows
                    .Where(row => !row.crystalContaminated)
                    .ToArray();
                if (cleanRows.Length == 0)
                    throw new InvalidDataException(
                        "Endminf diagnostic comparison has no crystal-clean rows");
                string cleanReferenceFrames = string.Join("+", cleanRows.Select(row =>
                    "eq(n\\," + (row.extractedFrame - 1) + ")").ToArray());
                string cleanUnityFrames = string.Join("+", cleanRows.Select(row =>
                    "eq(n\\," + row.unityFrameIndex + ")").ToArray());
                int cleanColumns = Mathf.Min(2, cleanRows.Length);
                int cleanTileRows = Mathf.CeilToInt(
                    cleanRows.Length / (float)cleanColumns);
                string cleanSheet = Path.Combine(output,
                    Path.GetFileNameWithoutExtension(sheetName) +
                    "_clean_body.png");
                RunFfmpeg("-y -v error -framerate 60 -start_number 1 -i " +
                    Quote(Path.Combine(sequence, "frame_%06d.png")) +
                    " -framerate 4 -start_number 0 -i " +
                    Quote(Path.Combine(output, "frame_%06d.png")) +
                    " -filter_complex \"[0:v]select='" + cleanReferenceFrames +
                    "',setpts=N/(4*TB),scale=1920:1080:flags=lanczos," +
                    "scale=384:-1:flags=lanczos[reference];" +
                    "[1:v]select='" + cleanUnityFrames +
                    "',setpts=N/(4*TB),scale=384:-1:flags=lanczos[unity];" +
                    "[reference][unity]hstack=inputs=2,tile=" +
                    cleanColumns + "x" + cleanTileRows +
                    "\" -frames:v 1 " + Quote(cleanSheet));
            }

            var report = new ReferenceComparisonReport {
                recordingId = recordingId,
                segmentId = segmentId,
                sourceSha256 = sidecar.source.sha256,
                extractedStartSourceFrame = sidecar.output.firstSourceFrame,
                bodyClipStartSourceFrame = comparison.bodyClipStartSourceFrame,
                sourceFps = sidecar.source.fps,
                unityAnchorBodyClipPhaseSeconds = firstStartClipPhase,
                comparisonBoundary = diagnosticAnchor
                    ? "diagnostic_cross_capture_bounded_phase_crystal_excluded"
                    : "exact_60hz_source_sample",
                firstVisibleSourceFrame = comparison.firstVisibleSourceFrame,
                anchorUncertaintyFrames = comparison.anchorUncertaintyFrames,
                unmaskedBodyStartSourceFrame = comparison.unmaskedBodyStartSourceFrame,
                comparisonWidth = diagnosticAnchor ? comparison.comparisonWidth : 1920,
                comparisonHeight = diagnosticAnchor ? comparison.comparisonHeight : 1080,
                resamplingFilter = diagnosticAnchor
                    ? comparison.resamplingFilter
                    : "lanczos",
                phaseErrorSpreadFrames = phaseErrorSpreadFrames,
                rows = rows.ToArray()
            };
            File.WriteAllText(Path.Combine(output, reportName),
                JsonUtility.ToJson(report, true));
        }

        private static void ValidateReferenceSequence(
            string lab, string recordingId, string segmentId)
        {
            string script = Path.Combine(lab, "tools", "reference_video_sequences.py");
            if (!File.Exists(script))
                throw new FileNotFoundException(
                    "Maintained reference-sequence validator is missing", script);
            string arguments = Quote(script) + " --check --recording " + recordingId +
                " --segment " + segmentId;
            var start = new System.Diagnostics.ProcessStartInfo("python", arguments)
            {
                UseShellExecute = false,
                CreateNoWindow = true,
                WorkingDirectory = lab,
                RedirectStandardOutput = true,
                RedirectStandardError = true
            };
            using (System.Diagnostics.Process process =
                   System.Diagnostics.Process.Start(start))
            {
                string stdout = process.StandardOutput.ReadToEnd();
                string stderr = process.StandardError.ReadToEnd();
                process.WaitForExit();
                if (process.ExitCode != 0)
                    throw new InvalidDataException(
                        "Endminf reference sequence is stale; regenerate it with " +
                        "scripts\\reference_video\\extract_reference_sequences.bat " +
                        "--recording " + recordingId + " --force.\n" +
                        stdout + stderr);
            }
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

        private static SecondaryDynamicsBoneRow[] CaptureSecondaryDynamicsBones(
            Transform actor)
        {
            EndfieldSecondaryDynamicsRuntime runtime = actor == null
                ? null
                : actor.GetComponent<EndfieldSecondaryDynamicsRuntime>();
            EndfieldSecondaryDynamicsData data = runtime == null ? null : runtime.data;
            if (data == null || data.owners == null || data.owners.Length != 4)
                throw new InvalidOperationException(
                    "Endminf secondary-dynamics capture requires four source owners.");

            Matrix4x4 worldToRoot = actor.worldToLocalMatrix;
            return data.owners
                .SelectMany(value => value.proxyTransformPaths ?? Array.Empty<string>())
                .Where(value => !string.IsNullOrWhiteSpace(value))
                .Distinct(StringComparer.Ordinal)
                .OrderBy(value => value, StringComparer.Ordinal)
                .Select(path =>
                {
                    Transform target = actor.Find(path);
                    if (target == null)
                        throw new InvalidOperationException(
                            "Endminf secondary-dynamics transform is missing: " + path);
                    Matrix4x4 matrix = worldToRoot * target.localToWorldMatrix;
                    return new SecondaryDynamicsBoneRow {
                        path = path,
                        rootSpaceRow0 = matrix.GetRow(0),
                        rootSpaceRow1 = matrix.GetRow(1),
                        rootSpaceRow2 = matrix.GetRow(2),
                    };
                }).ToArray();
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

        private static float[] ParseRequestedTimes(string value)
        {
            string[] tokens = (value ?? string.Empty).Split(
                new[] { ',', ';' },
                StringSplitOptions.RemoveEmptyEntries);
            if (tokens.Length == 0)
                throw new InvalidOperationException(
                    RequestedTimesEnvironment + " contains no timestamps.");
            var result = new List<float>(tokens.Length);
            foreach (string token in tokens)
            {
                if (!float.TryParse(
                    token.Trim(),
                    NumberStyles.Float,
                    CultureInfo.InvariantCulture,
                    out float timestamp) ||
                    !float.IsFinite(timestamp) || timestamp < 0f)
                {
                    throw new InvalidOperationException(
                        RequestedTimesEnvironment +
                        " contains an invalid non-negative timestamp: " + token.Trim());
                }
                if (result.Count > 0 && timestamp <= result[result.Count - 1])
                {
                    throw new InvalidOperationException(
                        RequestedTimesEnvironment +
                        " timestamps must be strictly increasing.");
                }
                result.Add(timestamp);
            }
            return result.ToArray();
        }

        private static string SafePathComponent(string value)
        {
            char[] invalid = Path.GetInvalidFileNameChars();
            return new string(value.Select(character =>
                Array.IndexOf(invalid, character) >= 0 ? '_' : character).ToArray());
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
