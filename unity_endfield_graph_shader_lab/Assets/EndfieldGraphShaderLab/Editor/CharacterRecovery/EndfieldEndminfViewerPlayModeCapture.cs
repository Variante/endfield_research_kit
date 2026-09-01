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
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>Captures the actual Viewer Play-mode path, including SelectModel and runtime-spawned VFX.</summary>
    public static class EndfieldEndminfViewerPlayModeCapture
    {
        private const string Scene = "Assets/EndfieldGraphShaderLab/Generated/Characters/Scenes/CharacterRecoveryViewer.unity";
        private const int DefaultWidth = 1920;
        private const int DefaultHeight = 1080;
        private const string CaptureWidthEnvironment =
            "ENDFIELD_ENDMINF_CAPTURE_WIDTH";
        private const string CaptureHeightEnvironment =
            "ENDFIELD_ENDMINF_CAPTURE_HEIGHT";
        // The requested deliverable retains the CharInfo grey background and
        // actor-specific background portrait, but never the foreground UI
        // controls, labels, icons, or cursor overlay. Exact-consumer captures
        // additionally require the physical SphereOutside presentation.
        private const bool IncludeCharInfoBackground = true;
        private const bool IncludeBackgroundPortrait = true;
        // Keep the default verifier output at 1920x1080 and the Play-mode
        // simulation on the retail 60 Hz clock. A paired width/height override
        // is reserved for focused native-resolution presentation probes; it
        // does not alter the canonical comparison dimensions or timing. Only
        // thin written PNGs to 4 fps. Driving Time.captureDeltaTime at 4 fps changed particle
        // integration, AnimationEvent stepping, and every temporal producer,
        // so the old side-by-side frames were not equivalent observations.
        private const float SimulationFps = 60f;
        private const float Fps = 4f;
        // Match the complete no-frame-generation retail segment through the
        // sustained loop tail, rather than stopping at the former 10 s export.
        private const int VideoFrameCount = 770;
        private const int BackgroundProofEdgePixels = 128;
        private const float MinimumBackgroundProofMeanLuma = 100.0f;
        private const int MinimumBackgroundProofPixelLuma = 80;
        private static readonly Color CanonicalSolidBackgroundColor =
            new Color(0.70f, 0.71f, 0.70f, 1.0f);
        private static readonly float[] CanonicalBackgroundProofTimes =
        {
            0.65f,
            4.4333334f,
            6.65f,
        };
        // Direct UI-free registration of the retained retail Uber output places
        // the August 24 no-frame-generation pulse on the authored body clock.
        // The older August 21 route's 0.15-second offset remains available as
        // an explicit environment override, but is not this capture's default.
        private const string RecordingVisualPostPreRollSeconds = "0";
        // RestartOverviewFromSelection is invoked on an editor update edge;
        // the body Animation has advanced by two 60-Hz simulation ticks before
        // the first renderable sample. The ordinary/video sequences therefore
        // use an internal threshold two ticks before their authored target.
        // The initial clamped thresholds can drain over several editor updates,
        // so reports must keep target, threshold, and actual clocks distinct.
        private const float PlayModeClipLeadSeconds = 2f / SimulationFps;
        // The recovered entrance is almost six seconds long. Capture far
        // enough past its handoff to prove that the actual viewer reaches and
        // sustains overview_loop instead of stopping on the entrance pose.
        private const int FrameCount = 41;
        private const string LitEffectCompatibilityShader =
            "Hidden/Endfield/Compatibility/Endminf/LitEffectParallax";
        private const string ExactRefractShader =
            "Hidden/Endfield/Recovered/Zhuangfy/VFXRefractMRT";
        private const string ExactSuikuai1MaterialName =
            "M_fx_common_teleport_03";
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
        private const string CapturedSecondaryDynamicsReplayEnvironment =
            "ENDFIELD_ENDMINF_CAPTURE_ENABLE_CAPTURED_SECONDARY_REPLAY";
        private const string RetainedSkinningDiagnosticEnvironment =
            "ENDFIELD_ENDMINF_CAPTURE_RETAINED_SKINNING";
        private const string EndminfM21ExactEnvironment =
            "ENDFIELD_RECOVERED_ENDMINF_M21_PEAK_EXACT";
        private const string SphereOutsidePresentationEnvironment =
            "ENDFIELD_RECOVERED_SPHERE_OUTSIDE_PRESENTATION";
        // Source-backed owners are promoted here only after their exact path is
        // presentation-ready. Keep this list empty while SphereOutside still
        // lacks a content-valid retail t11 producer; explicit diagnostics use
        // dedicated entry points outside canonical-video policy.
        private static readonly string[] CanonicalVideoDefaultFlags =
        {
            // SphereOutside remains an explicit fail-closed probe until the
            // retail t11 screen-shadow producer/content boundary is recovered.
            // Captured opening-strip, M13, and M21 draw packets remain useful
            // ABI diagnostics, but they freeze one or a few observed particle
            // states. The maintained reproduction must keep the authored
            // ParticleSystem/material timeline until the generating runtime
            // behavior is recovered; do not promote packet snapshots based on
            // a local frame comparison.
            // The captured Uber packet validates its native draw, but its
            // current SceneColor/input chronology is not source-closed and it
            // regresses every aligned effect sample versus the exact-off
            // control. Keep it available as an explicit diagnostic only.
        };
        private static readonly string[] CanonicalVideoForcedOffFlags =
        {
            // Canonical export must not inherit bounded packet replays,
            // measured-reference effects, or incomplete deferred consumers
            // from a parent shell. Dedicated diagnostic entry points remain
            // available and do not use the canonical-video policy.
            "ENDFIELD_ENDMINF_MEASURED_OPENING_STRIP_DIAGNOSTIC",
            "ENDFIELD_ENDMINF_M28_VISUAL_COMPAT",
            "ENDFIELD_ENDMINF_OPENING_STRIP_SCENEMV",
            "ENDFIELD_RECOVERED_ENDMINF_OPENING_STRIP_EXACT",
            "ENDFIELD_RECOVERED_ENDMINF_M13_EXACT",
            "ENDFIELD_RECOVERED_ENDMINF_M14_EXACT",
            "ENDFIELD_RECOVERED_ENDMINF_M18_PEAK_EXACT",
            "ENDFIELD_RECOVERED_ENDMINF_M20_PEAK_EXACT",
            "ENDFIELD_RECOVERED_ENDMINF_M21_PEAK_EXACT",
            "ENDFIELD_RECOVERED_ENDMINF_M28_PEAK_EXACT",
            "ENDFIELD_RECOVERED_ENDMINF_M29_EXACT",
            "ENDFIELD_RECOVERED_ENDMINF_M30_EXACT",
            "ENDFIELD_RECOVERED_ENDMINF_M31_PEAK_EXACT",
            "ENDFIELD_RECOVERED_ENDMINF_VFXBASEV2_PEAK_COHORT_EXACT",
            "ENDFIELD_RECOVERED_ENDMINF_UBER_EXACT",
            "ENDFIELD_RECOVERED_ENDMINF_UBER_EARLY_DIAGNOSTIC",
            "ENDFIELD_RECOVERED_ENDMINF_M27_EXACT_DXBC",
            "ENDFIELD_RECOVERED_ENDMINF_M27_GENERATIVE_EXACT_DXBC",
            "ENDFIELD_RECOVERED_ENDMINF_M27_PRESENTATION",
            "ENDFIELD_RECOVERED_ENDMINF_M27_HGBUFFER",
            "ENDFIELD_RECOVERED_ENDMINF_LITEFFECT_HGBUFFER",
            "ENDFIELD_RECOVERED_DEFERRED_EXACT_CONSUMER",
            // These selectors cover the known content-invalid paths that
            // produced body-shaped resolves over the portrait.
            "ENDFIELD_RECOVERED_SCREEN_SHADOW_R_ATTACHMENT_DIAGNOSTIC",
            SphereOutsidePresentationEnvironment,
            // This causality probe replaces the source primary depth with a
            // compatibility-Uber footprint and can create another body-shaped
            // portrait cutout. It is never canonical presentation policy.
            "ENDFIELD_DIAGNOSTIC_SYNC_POST_UBER_PORTRAIT_DEPTH",
        };
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
        private static float[] targetTimes;
        private static string captureGyroscopeMode;
        private static string captureGyroscopeInputProvider;
        private static string captureGyroscopeInputX;
        private static string captureGyroscopeInputY;
        private static string captureGyroscopeEntryOffsetX;
        private static string captureGyroscopeEntryOffsetY;
        private static float captureFps = Fps;
        private static int captureWidth = DefaultWidth;
        private static int captureHeight = DefaultHeight;
        private static string captureFailure;
        private static bool capturePrePostHdr;
        private static bool capturePostStages;
        private static bool captureSecondaryDynamics;
        private static bool captureRetainedSkinningDiagnostic;
        private static bool captureCanonicalSolidColorBackground;
        private static bool enableSecondaryDynamicsSolver;
        private static bool enableCapturedSecondaryDynamicsReplay;
        private static string prePostHdrCohort;
        private static string prePostHdrOutput;
        private static string postStagesCohort;
        private static string postStagesOutput;
        private static readonly List<FrameRow> Frames = new List<FrameRow>();

        [Serializable]
        private sealed class Report
        {
            public string schema = "endfield.endminf-viewer-playmode-sequence.v23";
            public string status = "ok";
            public int width = captureWidth;
            public int height = captureHeight;
            public float fps;
            public string graphicsDeviceType;
            public string scene = Scene;
            public string selectionPath = "CharacterRecoveryViewerUI.SelectModel(Endminf)";
            public bool actorOnlyCapture =
                !IncludeCharInfoBackground && !IncludeBackgroundPortrait;
            public bool charInfoBackgroundRequested = IncludeCharInfoBackground;
            public bool endminfSourceBackgroundRequested;
            public bool canonicalSolidColorBackgroundRequested;
            public bool backgroundPortraitRequested = IncludeBackgroundPortrait;
            public bool charInfoBackgroundIncluded;
            public bool endminfSourceBackgroundIncluded;
            public bool canonicalSourceSphereFloorGridBackgroundIncluded;
            public bool canonicalSolidColorBackgroundIncluded;
            public bool fittedCompatibilityPlateActive;
            public bool backgroundPortraitIncluded;
            public float[] canonicalSolidColorBackgroundProofTimes;
            public int[] canonicalSolidColorBackgroundProofFrameIndices;
            public float minimumCanonicalBackgroundProofLumaMean;
            public int minimumCanonicalBackgroundProofLuma;
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
            public bool observedOverview01AuthenticatedSourceSeed;
            public int overview01SourceSeededAnimationCount;
            public float overview01SourceSeedSeconds;
            public string overview01SourceSeedFailure;
            public bool observedRotationOnlyRootMotion;
            public bool observedPrimaryRockCompatibilityBinding;
            public bool observedDeferredLightDataReady;
            public bool observedDeferredShadowDataReady;
            public bool observedDeferredPass0InputSubsetReady;
            public bool observedDeferredGBufferFrameReady;
            public bool observedEndminfM27HGBufferReady;
            public bool endminfM27PresentationRequested;
            public bool observedEndminfM27PresentationReady;
            public bool observedSphereOutsidePresentationReady;
            public bool observedEndminfPostSourceRgba16;
            public bool observedEndminfBloomR11;
            public bool exactEndminfUberRequested;
            public bool observedExactEndminfUberSubmitted;
            public bool observedExactEndminfUberValidated;
            public string exactEndminfUberFailure;
            public bool observedExactEndminfLutProfileMatched;
            public bool observedExactEndminfLutGpuValidated;
            public bool observedCompatibilityExactEndminfLutBound;
            public string exactEndminfLutSha256;
            public string exactEndminfLutFailure;
            public bool observedOpeningStripCompatibilityBeforeTemporal;
            public bool observedOpeningStripSceneMVBeforeTemporal;
            public bool endminfOpeningStripExactRequested;
            public bool observedEndminfOpeningStripExactActive;
            public bool observedEndminfOpeningStripExactSubmitted;
            public bool observedEndminfOpeningStripExactValidated;
            public string endminfOpeningStripExactFailure;
            public bool unityPublicNgxProxyRequested;
            public bool observedUnityPublicNgxProxySubmitted;
            public bool observedUnityPublicNgxProxyValidated;
            public string unityPublicNgxProxyFailure;
            public bool endminfM31ExactRequested;
            public bool observedEndminfM31ExactSubmitted;
            public bool observedEndminfM31ExactValidated;
            public string endminfM31ExactFailure;
            public bool observedPreGBufferDepthOwnerReady;
            public bool observedCanonicalCharacterPreGBufferReady;
            public bool deferredExactConsumerRequested;
            public bool observedDeferredExactConsumerReady;
            public bool observedLightCookieDataReady;
            public string gyroscopeMode;
            public string gyroscopeInputProvider;
            public string gyroscopeInputX;
            public string gyroscopeInputY;
            public string gyroscopeEntryOffsetX;
            public string gyroscopeEntryOffsetY;
            public float visualPostPreRollSeconds;
            public bool retainedSkinningDiagnostic;
            public FrameRow[] frames;
        }

        [Serializable]
        private sealed class FrameRow
        {
            public int index;
            public float targetSeconds;
            public float requestedSeconds;
            public float actualSeconds;
            public float phaseErrorSeconds;
            public bool endminfPostEvaluated;
            public float endminfPostSeconds;
            public float endminfPostChromaticIntensity;
            public float endminfPostRadialIntensity;
            public float endminfPostEffectivePower;
            public int endminfPostMode;
            public Vector2 endminfPostCenterViewport;
            public string endminfPostSourceGraphicsFormat;
            public string endminfBloomGraphicsFormat;
            public int endminfBloomWidth;
            public int endminfBloomHeight;
            public bool exactEndminfUberRequested;
            public bool exactEndminfUberSubmitted;
            public bool exactEndminfUberValidated;
            public string exactEndminfUberVariant;
            public string exactEndminfUberFailure;
            public bool exactEndminfLutProfileMatched;
            public bool exactEndminfLutGpuValidationPending;
            public bool exactEndminfLutGpuValidated;
            public bool compatibilityExactEndminfLutBound;
            public string exactEndminfLutSha256;
            public string exactEndminfLutFailure;
            public bool openingStripCompatibilityBeforeTemporal;
            public bool openingStripSceneMVBeforeTemporal;
            public bool unityPublicNgxProxyRequested;
            public bool unityPublicNgxProxySubmitted;
            public bool unityPublicNgxProxyValidated;
            public string unityPublicNgxProxyFailure;
            public Vector2 unityPublicNgxProxyJitterOffset;
            public int unityPublicNgxProxyJitterPhase;
            public int unityPublicNgxProxyIndicatorInvertAxisX;
            public int unityPublicNgxProxyIndicatorInvertAxisY;
            public bool endminfOpeningStripExactRequested;
            public bool endminfOpeningStripExactActive;
            public bool endminfOpeningStripExactSubmitted;
            public bool endminfOpeningStripExactValidated;
            public int endminfOpeningStripExactPacket;
            public int endminfOpeningStripExactSourceFrame;
            public string endminfOpeningStripExactFailure;
            public bool endminfM18ExactRequested;
            public bool endminfM18ExactActive;
            public bool endminfM18ExactSubmitted;
            public bool endminfM18ExactValidated;
            public string endminfM18ExactFailure;
            public bool endminfM21ExactRequested;
            public bool endminfM21ExactActive;
            public bool endminfM21ExactSubmitted;
            public bool endminfM21ExactValidated;
            public string endminfM21ExactFailure;
            public bool endminfM20ExactRequested;
            public bool endminfM20ExactActive;
            public bool endminfM20ExactSubmitted;
            public bool endminfM20ExactValidated;
            public string endminfM20ExactFailure;
            public bool endminfM28ExactRequested;
            public bool endminfM28ExactActive;
            public bool endminfM28ExactSubmitted;
            public bool endminfM28ExactValidated;
            public string endminfM28ExactFailure;
            public bool endminfM31ExactRequested;
            public bool endminfM31ExactExpected;
            public bool endminfM31ExactActive;
            public bool endminfM31ExactSubmitted;
            public bool endminfM31ExactValidated;
            public int endminfM31ExactPacket;
            public int endminfM31ExactSourceFrame;
            public string endminfM31ExactFailure;
            public string file;
            public int effectRootCount;
            public int admittedRenderers;
            public int activeAdmittedRenderers;
            public int admittedAliveParticles;
            public bool overview01SourceClockAuthenticated;
            public int overview01SourceSeededAnimationCount;
            public float overview01SourceSeedSeconds;
            public string overview01SourceSeedFailure;
            public bool sharedCharEffectActive;
            public int sharedCharEffectAliveParticles;
            public int sharedCharEffectTrailAliveParticles;
            public Vector3 sharedCharEffectTrailPositionMin;
            public Vector3 sharedCharEffectTrailPositionMax;
            public Vector3 sharedCharEffectTrailFirstSize;
            public Vector3 sharedCharEffectTrailFirstVelocity;
            public Vector3 sharedCharEffectTrailRendererBoundsCenter;
            public Vector3 sharedCharEffectTrailRendererBoundsExtents;
            public bool sharedCharEffectTrailRendererEnabled;
            public bool sharedCharEffectTrailRendererActive;
            public string sharedCharEffectTrailShader;
            public int sharedCharEffectTrailPassCount;
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
            public bool farGridEnabled;
            public bool farGridActive;
            public bool farGridInCameraFrustum;
            public Vector3 farGridBoundsCenter;
            public Vector3 farGridBoundsExtents;
            public int farGridLayer;
            public int farGridRenderQueue;
            public int cameraCullingMask;
            public bool deferredLightDataReady;
            public bool deferredShadowDataReady;
            public bool deferredPass0InputSubsetReady;
            public bool deferredGBufferFrameReady;
            public bool endminfM27HGBufferReady;
            public bool endminfM27PresentationReady;
            public bool sphereOutsidePresentationReady;
            public bool preGBufferDepthOwnerReady;
            public bool canonicalCharacterPreGBufferReady;
            public bool deferredExactConsumerReady;
            public bool lightCookieDataReady;
            public Vector4 exposureWithMiscParams;
            public string[] effectRoots;
            public ParticleRow[] liveRenderers;
            public ParticleRow[] handFamily;
            public ParticleRow[] primaryRockFamily;
            public int litEffectBindingRowCount;
            public bool exactSuikuai1BindingReady;
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
            public bool capturedSecondaryReplayPoseAppliedThisFrame;
            public EndfieldEndminfRetainedSkinningDiagnostic.RendererRow[]
                retainedSkinningRenderers;
            public string[] blockedRendererIdentities;
            public float topLeftBackgroundLumaMean;
            public int topLeftBackgroundLumaMin;
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
            public Vector3 rendererBoundsCenter;
            public Vector3 rendererBoundsExtents;
            public Vector3 rendererViewportCenter;
            public string mesh;
            public Vector3 meshBoundsCenter;
            public Vector3 meshBoundsExtents;
            public Vector3 firstParticlePosition;
            public Vector3 firstParticleWorldPosition;
            public Vector3 firstParticleSize3D;
            public Vector3 firstParticleRotation3D;
            public Vector4 firstParticleColor;
            public float firstParticleRemainingLifetime;
            public float firstParticleStartLifetime;
            public uint firstParticleRandomSeed;
            public Vector4 firstParticleCustom1;
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
            PrepareDeferredExactConsumerRuntimeVariantIfRequested();
            if (SystemInfo.graphicsDeviceType != GraphicsDeviceType.Direct3D11)
                throw new InvalidOperationException(
                    "Endminf Viewer capture requires the project's authoritative " +
                    "Direct3D11 backend; actual=" +
                    SystemInfo.graphicsDeviceType + ".");
            captureWidth = ParseCaptureDimension(
                CaptureWidthEnvironment,
                DefaultWidth);
            captureHeight = ParseCaptureDimension(
                CaptureHeightEnvironment,
                DefaultHeight);
            bool widthOverridden = !string.IsNullOrWhiteSpace(
                Environment.GetEnvironmentVariable(CaptureWidthEnvironment));
            bool heightOverridden = !string.IsNullOrWhiteSpace(
                Environment.GetEnvironmentVariable(CaptureHeightEnvironment));
            if (widthOverridden != heightOverridden)
            {
                throw new InvalidOperationException(
                    CaptureWidthEnvironment + " and " +
                    CaptureHeightEnvironment +
                    " must be supplied together.");
            }
            // Exercise the same explicit reproduction profile as
            // open_character_recovery_lab.bat. Batch validation must not
            // silently fall back to the preserved gacha-room presentation
            // merely because its parent shell lacks these process variables.
            bool videoExportRequested = Environment.GetEnvironmentVariable(
                "ENDFIELD_ENDMINF_CAPTURE_VIDEO_EXPORT") == "1";
            string sourceBackgroundSelection =
                Environment.GetEnvironmentVariable(
                    EndfieldRecoveredCharInfoPresentation
                        .EndminfSourceBackgroundEnvironmentVariable);
            if (videoExportRequested &&
                string.IsNullOrWhiteSpace(sourceBackgroundSelection))
            {
                sourceBackgroundSelection = "0";
                Environment.SetEnvironmentVariable(
                    EndfieldRecoveredCharInfoPresentation
                        .EndminfSourceBackgroundEnvironmentVariable,
                    sourceBackgroundSelection);
            }
            bool sourceBackgroundExplicitlyDisabled = string.Equals(
                sourceBackgroundSelection,
                "0",
                StringComparison.Ordinal);
            // Canonical video retains the neutral preview clear until the
            // source SphereOutside -> floor -> Far composite passes the v22
            // exact-consumer and presented-pixel gate. Explicit source=1 is a
            // controlled fail-closed diagnostic.
            captureCanonicalSolidColorBackground =
                sourceBackgroundExplicitlyDisabled;
            if (videoExportRequested)
            {
                if (!sourceBackgroundExplicitlyDisabled)
                {
                    foreach (string flag in CanonicalVideoDefaultFlags)
                    {
                        if (string.IsNullOrWhiteSpace(
                                Environment.GetEnvironmentVariable(flag)))
                            Environment.SetEnvironmentVariable(flag, "1");
                    }
                }
                foreach (string flag in CanonicalVideoForcedOffFlags)
                    Environment.SetEnvironmentVariable(flag, "0");
            }
            bool isolatedEndminfLitEffect =
                Environment.GetEnvironmentVariable(
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
                    "1");
            if (string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(
                    EndfieldEndminfVisualCompatibilityClock.SourcePostEnvironmentVariable)))
            {
                Environment.SetEnvironmentVariable(
                    EndfieldEndminfVisualCompatibilityClock.SourcePostEnvironmentVariable,
                    "1");
            }
            // Exact HGBuffer publication replaces only the identity-gated M27
            // hand-crystal row. The ten source-identified M01/M38 primary-rock
            // renderers remain separate ForwardOnly owners; disabling the
            // whole compatibility binding removed those stones from the shot.
            if (captureCanonicalSolidColorBackground)
            {
                Environment.SetEnvironmentVariable(
                    EndfieldRecoveredCharInfoPresentation
                        .EndminfSourceBackgroundEnvironmentVariable,
                    "0");
                Environment.SetEnvironmentVariable(
                    EndfieldRecoveredCharInfoSky
                        .MaterialOnlyDiagnosticEnvironmentVariable,
                    "1");
            }
            else if (string.IsNullOrWhiteSpace(sourceBackgroundSelection))
            {
                Environment.SetEnvironmentVariable(
                    EndfieldRecoveredCharInfoPresentation
                        .EndminfSourceBackgroundEnvironmentVariable,
                    "1");
            }
            // Canonical capture admits the bounded source-owned background.
            // Hold the unrelated physical sky off: SphereOutside owns the
            // opaque room and its failed presentation must remain visibly
            // fail-closed instead of being replaced by another background.
            Environment.SetEnvironmentVariable(
                EndfieldRecoveredCharInfoSky
                    .MaterialOnlyDiagnosticEnvironmentVariable,
                "1");
            // Neither fitted compatibility path may become a hidden fallback.
            Environment.SetEnvironmentVariable(
                EndfieldRecoveredCharInfoPresentation
                    .EndminfBackdropVisualCompatibilityEnvironmentVariable,
                "0");
            Environment.SetEnvironmentVariable(
                EndfieldRecoveredCharInfoPresentation
                    .ReadySubsetEnvironmentVariable,
                "0");
            Environment.SetEnvironmentVariable(
                "ENDFIELD_RECOVERED_CHARINFO_BACKGROUND_PORTRAIT",
                IncludeBackgroundPortrait ? "1" : "0");
            EndfieldRecoveredCharInfoPresentation.RefreshStandaloneSelection();
            // Character refreshes can replace the generated actor and effect
            // bindings. Canonical and targeted captures must rebuild all four
            // roots from the fingerprint-gated source stage; never preserve a
            // stale generated prefab when that source is missing or drifted.
            EndfieldEndminfOverviewEffectImporter.BuildAndValidate();
            EndfieldEndminfOverviewEffectBindingBuilder.BuildAndValidate();
            // The rebuild may refresh serialized presentation state. Restore
            // the canonical/explicitly-disabled process selector after that
            // mutation, then invalidate the already-running editor cache
            // before opening the Play-mode scene.
            if (captureCanonicalSolidColorBackground)
            {
                Environment.SetEnvironmentVariable(
                    EndfieldRecoveredCharInfoPresentation
                        .EndminfSourceBackgroundEnvironmentVariable,
                    "0");
                EndfieldRecoveredCharInfoPresentation
                    .RefreshStandaloneSelection();
            }
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
                    "serialized-entry");
            }
            ConfigureDeterministicGyroscopeCapture();
            EditorSceneManager.OpenScene(Scene, OpenSceneMode.Single);
            if (isolatedEndminfLitEffect)
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
            bool videoExport = videoExportRequested;
            string requestedTimesText = Environment.GetEnvironmentVariable(
                RequestedTimesEnvironment);
            bool targetedTimes = !string.IsNullOrWhiteSpace(requestedTimesText);
            capturePrePostHdr = Environment.GetEnvironmentVariable(
                "ENDFIELD_ENDMINF_CAPTURE_PREPOST_HDR") == "1";
            capturePostStages = Environment.GetEnvironmentVariable(
                "ENDFIELD_ENDMINF_CAPTURE_POST_STAGES") == "1";
            captureSecondaryDynamics = Environment.GetEnvironmentVariable(
                SecondaryDynamicsEnvironment) == "1";
            captureRetainedSkinningDiagnostic =
                Environment.GetEnvironmentVariable(
                    RetainedSkinningDiagnosticEnvironment) == "1";
            enableSecondaryDynamicsSolver = Environment.GetEnvironmentVariable(
                SecondaryDynamicsSolverEnvironment) == "1";
            enableCapturedSecondaryDynamicsReplay =
                Environment.GetEnvironmentVariable(
                    CapturedSecondaryDynamicsReplayEnvironment) == "1";
            if (videoExport && enableSecondaryDynamicsSolver)
            {
                throw new InvalidOperationException(
                    "Canonical Endminf video export cannot use the unverified " +
                    "secondary-dynamics solver; unset " +
                    SecondaryDynamicsSolverEnvironment + ".");
            }
            if (videoExport && enableCapturedSecondaryDynamicsReplay)
            {
                throw new InvalidOperationException(
                    "Canonical Endminf video export cannot use a captured hair/cape " +
                    "trajectory as its animation implementation; unset " +
                    CapturedSecondaryDynamicsReplayEnvironment + ".");
            }
            if (enableSecondaryDynamicsSolver &&
                enableCapturedSecondaryDynamicsReplay)
            {
                throw new InvalidOperationException(
                    "The secondary-dynamics solver and captured-trajectory diagnostic " +
                    "cannot own the same hair/cape bones.");
            }
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
            targetTimes = targetedTimes
                ? ParseRequestedTimes(requestedTimesText)
                : capturePostStages
                ? new[] { 4.40f, 4.4333334f, 4.4666667f, 4.50f, 4.55f }
                : capturePrePostHdr
                ? Enumerable.Range(0, 19).Select(value => value / Fps).ToArray()
                : videoExport
                ? Enumerable.Range(0, VideoFrameCount).Select(value =>
                    value / SimulationFps).ToArray()
                : fineWindow
                ? Enumerable.Range(0, 25).Select(value => 4.30f + value / 60f).ToArray()
                : Enumerable.Range(0, FrameCount).Select(value => value / Fps).ToArray();
            requestedTimes = capturePrePostHdr || videoExport ||
                (!targetedTimes && !capturePostStages && !fineWindow)
                ? targetTimes.Select(value =>
                    Mathf.Max(0f, value - PlayModeClipLeadSeconds)).ToArray()
                : targetTimes.ToArray();
            Directory.CreateDirectory(output);
            EditorApplication.playModeStateChanged += State;
            EditorApplication.EnterPlaymode();
        }

        public static void RunRetainedSkinningDiagnostic()
        {
            if (string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(
                    RequestedTimesEnvironment)))
            {
                throw new InvalidOperationException(
                    "Retained skinning diagnostic requires explicit requested " +
                    "times in " + RequestedTimesEnvironment + ".");
            }
            Environment.SetEnvironmentVariable(
                RetainedSkinningDiagnosticEnvironment,
                "1");
            Environment.SetEnvironmentVariable(
                SecondaryDynamicsEnvironment,
                "1");
            Run();
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
            string[] enabled = {
                "ENDFIELD_RECOVERED_DEFERRED_EXACT_CONSUMER",
                "ENDFIELD_RECOVERED_ENDMINF_M18_PEAK_EXACT",
                "ENDFIELD_RECOVERED_ENDMINF_M28_PEAK_EXACT",
                "ENDFIELD_RECOVERED_ENDMINF_M21_PEAK_EXACT",
                "ENDFIELD_RECOVERED_ENDMINF_M13_EXACT",
                "ENDFIELD_RECOVERED_ENDMINF_M14_EXACT",
                "ENDFIELD_RECOVERED_ENDMINF_M27_PRESENTATION",
                "ENDFIELD_RECOVERED_ENDMINF_M27_HGBUFFER",
                "ENDFIELD_RECOVERED_CLUSTERED_NPR_LIGHT_LOOP",
                "ENDFIELD_RECOVERED_LIGHT_BINNING_MEMBERSHIP",
                "ENDFIELD_RECOVERED_ISOLATED_PUNCTUAL_SOFT_SHADOWS",
                "ENDFIELD_RECOVERED_CANONICAL_BINNING_BUFFER",
                "ENDFIELD_RECOVERED_SEPARATE_CHARACTER_SHADOW",
                "ENDFIELD_RECOVERED_LOW_RES_DIRECTIONAL_SHADOW",
                "ENDFIELD_RECOVERED_SCREEN_SHADOW_R_ATTACHMENT_DIAGNOSTIC"
            };
            foreach (string flag in enabled)
                Environment.SetEnvironmentVariable(flag, "1");
            string[] excluded = {
                "ENDFIELD_ENDMINF_DEFERRED_B31_PROBE",
                "ENDFIELD_RECOVERED_DEFERRED_RESOLVER_RESOURCE_PROBE",
                // The SphereOutside and M27 producers may share the resolver
                // ABI, but their presentation ownership is not interchangeable.
                // M27 must not inherit SphereOutside depth/GBuffer pixels.
                "ENDFIELD_RECOVERED_DEFERRED_GBUFFER_FRAME",
                SphereOutsidePresentationEnvironment
            };
            foreach (string flag in excluded)
                Environment.SetEnvironmentVariable(flag, null);
            Run();
        }

        private static void PrepareDeferredExactConsumerRuntimeVariantIfRequested()
        {
            bool exactConsumerRequested =
                Environment.GetEnvironmentVariable(
                    "ENDFIELD_RECOVERED_DEFERRED_EXACT_CONSUMER") == "1" ||
                Environment.GetEnvironmentVariable(
                    "ENDFIELD_RECOVERED_ENDMINF_M27_PRESENTATION") == "1";
            bool generativeM27Requested =
                Environment.GetEnvironmentVariable(
                    "ENDFIELD_RECOVERED_ENDMINF_M27_GENERATIVE_EXACT_DXBC") ==
                "1";
            bool packetM27Requested =
                Environment.GetEnvironmentVariable(
                    "ENDFIELD_RECOVERED_ENDMINF_M27_EXACT_DXBC") == "1";
            if (!generativeM27Requested &&
                (!exactConsumerRequested || !packetM27Requested))
                return;

            if (generativeM27Requested)
            {
                // The named-binding shell hashes are independently pinned,
                // but the retained PSR draw remains source-incomplete. Keep
                // ordinary play-mode preparation unarmed until TryBindDraw's
                // explicit source/publisher gates can be supplied as ready.
                EndfieldM27ShellHashCapture
                    .PrepareGenerativeRawRuntimeVariant();
                return;
            }

            if (Environment.GetEnvironmentVariable(
                    "ENDFIELD_M27_FORCE_RAW_SHELL") == "1")
                EndfieldM27ShellHashCapture.PrepareRawRuntimeVariant();
            else
                EndfieldM27ShellHashCapture.PreparePinnedRuntimeVariant();
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
                if (CharacterRecoveryViewerUI.TryGetSelectedActorRoot(
                        out Transform selectedDynamicsActor))
                {
                    EndfieldCapturedSecondaryDynamicsReplay selectedReplay =
                        selectedDynamicsActor.GetComponent<
                            EndfieldCapturedSecondaryDynamicsReplay>();
                    if (selectedReplay != null)
                    {
                        // Existing generated prefabs may still carry the
                        // diagnostic component. Apply capture policy before
                        // the first selected-actor LateUpdate so an ordinary
                        // or canonical run can never inherit fixed samples.
                        selectedReplay.enabled = false;
                        selectedReplay.useCapturedReplay =
                            enableCapturedSecondaryDynamicsReplay;
                        selectedReplay.enabled = true;
                        if (enableCapturedSecondaryDynamicsReplay &&
                            !selectedReplay.TryBind())
                        {
                            throw new InvalidOperationException(
                                "Captured secondary-dynamics diagnostic failed to bind: " +
                                selectedReplay.BindingFailure);
                        }
                    }
                    else if (enableCapturedSecondaryDynamicsReplay)
                    {
                        throw new InvalidOperationException(
                            "Captured secondary-dynamics diagnostic was explicitly " +
                            "requested, but the selected Endminf actor has no replay component.");
                    }
                }
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
                if (selectionSettleFrames == 1 && camera != null)
                {
                    // Queue and synchronize the exact-LUT GPU sentinel readback
                    // before capture time zero. The following settle edge
                    // restarts Overview again, so this validation render cannot
                    // advance the published animation or particle timeline.
                    Render(camera);
                }
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
            float target = targetTimes[next];
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
            MeasureTopLeftBackground(
                pixels,
                out float topLeftBackgroundLumaMean,
                out int topLeftBackgroundLumaMin);
            // ReadPixels in Render synchronizes this focused D3D11 capture, so
            // the render-thread plugin callback must be observable here. Do
            // not accept a submitted event as proof that an exact packet drew.
            if (HGCompatRenderPipeline.LastRecoveredEndminfExactUberRequested &&
                HGCompatRenderPipeline.LastRecoveredEndminfExactUberSubmitted &&
                !HGCompatRenderPipeline
                    .ValidateRecoveredEndminfExactUberAfterSynchronizedRender(
                        out string exactUberValidationFailure))
            {
                throw new InvalidOperationException(
                    "Exact Endminf Uber synchronized validation failed: " +
                    exactUberValidationFailure);
            }
            if (HGCompatRenderPipeline
                    .LastRecoveredUnityPublicNgxProxyRequested)
            {
                if (!HGCompatRenderPipeline
                        .LastRecoveredUnityPublicNgxProxySubmitted)
                {
                    throw new InvalidOperationException(
                        "UnityPublicNgxProxy submission failed: " +
                        HGCompatRenderPipeline
                            .LastRecoveredUnityPublicNgxProxyFailure);
                }
                if (!HGCompatRenderPipeline
                        .ValidateRecoveredUnityPublicNgxProxyAfterSynchronizedRender(
                            out string ngxValidationFailure))
                {
                    throw new InvalidOperationException(
                        "UnityPublicNgxProxy synchronized validation failed: " +
                        ngxValidationFailure);
                }
            }
            if (EndfieldRecoveredEndminfM18PeakExactRuntime.Requested &&
                EndfieldRecoveredEndminfM18PeakExactRuntime.HasPendingValidation &&
                !EndfieldRecoveredEndminfM18PeakExactRuntime
                    .ValidatePendingAfterSynchronizedRender(
                        out string m18PeakValidationFailure))
            {
                throw new InvalidOperationException(
                    "Exact Endminf M18 peak callback validation failed: " +
                    m18PeakValidationFailure);
            }
            if (EndfieldRecoveredEndminfOpeningStripExactRuntime.Requested &&
                EndfieldRecoveredEndminfOpeningStripExactRuntime
                    .HasPendingValidation &&
                !EndfieldRecoveredEndminfOpeningStripExactRuntime
                    .ValidatePendingAfterSynchronizedRender(
                        out string openingStripValidationFailure))
            {
                throw new InvalidOperationException(
                    "Exact Endminf opening-strip callback validation failed: " +
                    openingStripValidationFailure);
            }
            if (EndfieldRecoveredEndminfM28PeakExactRuntime.Requested &&
                EndfieldRecoveredEndminfM28PeakExactRuntime
                    .HasPendingValidation &&
                !EndfieldRecoveredEndminfM28PeakExactRuntime
                    .ValidatePendingAfterSynchronizedRender(
                        out string m28PeakValidationFailure))
            {
                throw new InvalidOperationException(
                    "Exact Endminf M28 peak callback validation failed: " +
                    m28PeakValidationFailure);
            }
            if (EndfieldRecoveredEndminfM21PeakExactRuntime.Requested &&
                EndfieldRecoveredEndminfM21PeakExactRuntime.HasPendingValidation &&
                !EndfieldRecoveredEndminfM21PeakExactRuntime
                    .ValidatePendingAfterSynchronizedRender(
                        out string m21PeakValidationFailure))
            {
                throw new InvalidOperationException(
                    "Exact Endminf M21 peak callback validation failed: " +
                    m21PeakValidationFailure);
            }
            if (EndfieldRecoveredEndminfM20PeakExactRuntime.Requested &&
                EndfieldRecoveredEndminfM20PeakExactRuntime.HasPendingValidation &&
                !EndfieldRecoveredEndminfM20PeakExactRuntime
                    .ValidatePendingAfterSynchronizedRender(
                        out string m20PeakValidationFailure))
            {
                throw new InvalidOperationException(
                    "Exact Endminf M20 peak callback validation failed: " +
                    m20PeakValidationFailure);
            }
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
            if (EndfieldRecoveredEndminfM29ExactRuntime.Requested &&
                EndfieldRecoveredEndminfM29ExactRuntime.HasPendingValidation &&
                !EndfieldRecoveredEndminfM29ExactRuntime
                    .ValidatePendingAfterSynchronizedRender(
                        out string m29ValidationFailure))
            {
                throw new InvalidOperationException(
                    "Exact Endminf M29 callback validation failed: " +
                    m29ValidationFailure);
            }
            if (EndfieldRecoveredEndminfM31PeakExactRuntime.Requested &&
                EndfieldRecoveredEndminfM31PeakExactRuntime.HasPendingValidation &&
                !EndfieldRecoveredEndminfM31PeakExactRuntime
                    .ValidatePendingAfterSynchronizedRender(
                        out string m31PeakValidationFailure))
            {
                throw new InvalidOperationException(
                    "Exact Endminf M31 peak callback validation failed: " +
                    m31PeakValidationFailure);
            }
            if (EndfieldRecoveredEndminfVFXBaseV2PeakCohortRuntime.Requested &&
                EndfieldRecoveredEndminfVFXBaseV2PeakCohortRuntime
                    .HasPendingValidation &&
                !EndfieldRecoveredEndminfVFXBaseV2PeakCohortRuntime
                    .ValidatePendingAfterSynchronizedRender(
                        out string vfxPeakValidationFailure))
            {
                throw new InvalidOperationException(
                    "Exact Endminf VFXBaseV2 peak cohort callback validation " +
                    "failed: " + vfxPeakValidationFailure);
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
            bool endminfPostEvaluated =
                EndfieldEndminfVisualCompatibilityClock.TryEvaluateRecoveredPost(
                    camera,
                    out EndfieldEndminfVisualCompatibilityClock.RecoveredPostState
                        endminfPostState);
            float endminfPostSeconds = endminfPostEvaluated
                ? endminfPostState.elapsed
                : 0.0f;
            EndfieldRecoveredCharInfoPresentation charInfoPresentation =
                UnityEngine.Object.FindObjectOfType<EndfieldRecoveredCharInfoPresentation>(true);
            Renderer shadowPlane = charInfoPresentation == null
                ? null
                : charInfoPresentation.shadowPlaneRenderer;
            bool shadowPlaneInFrustum = shadowPlane != null &&
                GeometryUtility.TestPlanesAABB(
                    GeometryUtility.CalculateFrustumPlanes(camera),
                    shadowPlane.bounds);
            Renderer farGrid = charInfoPresentation == null
                ? null
                : charInfoPresentation.farGridRenderer;
            bool farGridInFrustum = farGrid != null &&
                GeometryUtility.TestPlanesAABB(
                    GeometryUtility.CalculateFrustumPlanes(camera),
                    farGrid.bounds);
            EndfieldSecondaryDynamicsRuntime secondaryDynamics = actor
                .GetComponent<EndfieldSecondaryDynamicsRuntime>();
            EndfieldCapturedSecondaryDynamicsReplay capturedReplay = actor
                .GetComponent<EndfieldCapturedSecondaryDynamicsReplay>();
            GameObject sharedCharEffect = UnityEngine.Object
                .FindObjectsOfType<GameObject>(true)
                .FirstOrDefault(value =>
                    value.name == "CharEffect__CharacterInfoRuntime");
            ParticleSystem[] sharedCharEffectSystems = sharedCharEffect == null
                ? Array.Empty<ParticleSystem>()
                : sharedCharEffect.GetComponentsInChildren<ParticleSystem>(true);
            ParticleSystem sharedCharEffectTrail = sharedCharEffectSystems
                .FirstOrDefault(value => value.gameObject.name == "trail");
            ParticleSystemRenderer sharedCharEffectTrailRenderer =
                sharedCharEffectTrail == null
                    ? null
                    : sharedCharEffectTrail.GetComponent<ParticleSystemRenderer>();
            int sharedTrailCount = sharedCharEffectTrail == null
                ? 0
                : sharedCharEffectTrail.particleCount;
            ParticleSystem.Particle[] sharedTrailParticles =
                sharedTrailCount == 0
                    ? Array.Empty<ParticleSystem.Particle>()
                    : new ParticleSystem.Particle[sharedTrailCount];
            if (sharedCharEffectTrail != null && sharedTrailCount != 0)
                sharedTrailCount = sharedCharEffectTrail.GetParticles(
                    sharedTrailParticles);
            EndfieldRecoveredCharEffectSpawner effectSpawner = actor
                .GetComponentInChildren<EndfieldRecoveredCharEffectSpawner>(true);
            bool overview01SourceClockAuthenticated = false;
            int overview01SourceSeededAnimationCount = 0;
            float overview01SourceSeedSeconds = 0f;
            string overview01SourceSeedFailure = string.Empty;
            effectSpawner?.TryGetSourceSeedTelemetry(
                "P_fxui_endminm003_overview_01",
                out overview01SourceClockAuthenticated,
                out overview01SourceSeededAnimationCount,
                out overview01SourceSeedSeconds,
                out overview01SourceSeedFailure);
            Vector3 sharedTrailPositionMin = Vector3.zero;
            Vector3 sharedTrailPositionMax = Vector3.zero;
            if (sharedTrailCount != 0)
            {
                sharedTrailPositionMin = sharedTrailParticles[0].position;
                sharedTrailPositionMax = sharedTrailParticles[0].position;
                for (int index = 1; index < sharedTrailCount; index++)
                {
                    sharedTrailPositionMin = Vector3.Min(
                        sharedTrailPositionMin,
                        sharedTrailParticles[index].position);
                    sharedTrailPositionMax = Vector3.Max(
                        sharedTrailPositionMax,
                        sharedTrailParticles[index].position);
                }
            }
            Frames.Add(new FrameRow {
                index = next,
                targetSeconds = target,
                requestedSeconds = requested,
                actualSeconds = elapsed,
                phaseErrorSeconds = elapsed - target,
                file = file,
                endminfPostEvaluated = endminfPostEvaluated,
                endminfPostSeconds = endminfPostSeconds,
                endminfPostChromaticIntensity =
                    endminfPostState.chromaticIntensity,
                endminfPostRadialIntensity = endminfPostState.radialIntensity,
                endminfPostEffectivePower = endminfPostState.effectivePower,
                endminfPostMode = endminfPostState.mode,
                endminfPostCenterViewport = endminfPostState.centerViewport,
                endminfPostSourceGraphicsFormat =
                    HGCompatRenderPipeline
                        .LastRecoveredEndminfPostSourceGraphicsFormat.ToString(),
                endminfBloomGraphicsFormat =
                    HGCompatRenderPipeline
                        .LastRecoveredEndminfBloomGraphicsFormat.ToString(),
                endminfBloomWidth = HGCompatRenderPipeline
                    .LastRecoveredEndminfBloomWidth,
                endminfBloomHeight = HGCompatRenderPipeline
                    .LastRecoveredEndminfBloomHeight,
                exactEndminfUberRequested = HGCompatRenderPipeline
                    .LastRecoveredEndminfExactUberRequested,
                exactEndminfUberSubmitted = HGCompatRenderPipeline
                    .LastRecoveredEndminfExactUberSubmitted,
                exactEndminfUberValidated = HGCompatRenderPipeline
                    .LastRecoveredEndminfExactUberValidated,
                exactEndminfUberVariant = HGCompatRenderPipeline
                    .LastRecoveredEndminfExactUberVariant,
                exactEndminfUberFailure = HGCompatRenderPipeline
                    .LastRecoveredEndminfExactUberFailure,
                exactEndminfLutProfileMatched = HGCompatRenderPipeline
                    .LastRecoveredEndminfExactLutProfileMatched,
                exactEndminfLutGpuValidationPending = HGCompatRenderPipeline
                    .LastRecoveredEndminfExactLutGpuValidationPending,
                exactEndminfLutGpuValidated = HGCompatRenderPipeline
                    .LastRecoveredEndminfExactLutGpuValidated,
                compatibilityExactEndminfLutBound = HGCompatRenderPipeline
                    .LastRecoveredEndminfCompatibilityExactLutBound,
                exactEndminfLutSha256 = HGCompatRenderPipeline
                    .LastRecoveredEndminfExactLutSha256,
                exactEndminfLutFailure = HGCompatRenderPipeline
                    .LastRecoveredEndminfExactLutFailure,
                openingStripCompatibilityBeforeTemporal = HGCompatRenderPipeline
                    .LastRecoveredEndminfOpeningStripCompatibilityApplied,
                openingStripSceneMVBeforeTemporal = HGCompatRenderPipeline
                    .LastRecoveredEndminfOpeningStripSceneMVApplied,
                unityPublicNgxProxyRequested = HGCompatRenderPipeline
                    .LastRecoveredUnityPublicNgxProxyRequested,
                unityPublicNgxProxySubmitted = HGCompatRenderPipeline
                    .LastRecoveredUnityPublicNgxProxySubmitted,
                unityPublicNgxProxyValidated = HGCompatRenderPipeline
                    .LastRecoveredUnityPublicNgxProxyValidated,
                unityPublicNgxProxyFailure = HGCompatRenderPipeline
                    .LastRecoveredUnityPublicNgxProxyFailure,
                unityPublicNgxProxyJitterOffset = HGCompatRenderPipeline
                    .LastRecoveredUnityPublicNgxProxyJitterOffset,
                unityPublicNgxProxyJitterPhase = HGCompatRenderPipeline
                    .LastRecoveredUnityPublicNgxProxyJitterPhase,
                unityPublicNgxProxyIndicatorInvertAxisX = HGCompatRenderPipeline
                    .LastRecoveredUnityPublicNgxProxyIndicatorInvertAxisX,
                unityPublicNgxProxyIndicatorInvertAxisY = HGCompatRenderPipeline
                    .LastRecoveredUnityPublicNgxProxyIndicatorInvertAxisY,
                endminfOpeningStripExactRequested =
                    EndfieldRecoveredEndminfOpeningStripExactRuntime.Requested,
                endminfOpeningStripExactActive =
                    EndfieldRecoveredEndminfOpeningStripExactRuntime.ActiveThisFrame,
                endminfOpeningStripExactSubmitted =
                    EndfieldRecoveredEndminfOpeningStripExactRuntime.SubmittedThisFrame,
                endminfOpeningStripExactValidated =
                    EndfieldRecoveredEndminfOpeningStripExactRuntime.ValidatedThisFrame,
                endminfOpeningStripExactPacket =
                    EndfieldRecoveredEndminfOpeningStripExactRuntime
                        .SelectedPacketThisFrame,
                endminfOpeningStripExactSourceFrame =
                    EndfieldRecoveredEndminfOpeningStripExactRuntime
                        .SourceFrameThisFrame,
                endminfOpeningStripExactFailure =
                    EndfieldRecoveredEndminfOpeningStripExactRuntime.Failure,
                endminfM18ExactRequested =
                    EndfieldRecoveredEndminfM18PeakExactRuntime.Requested,
                endminfM18ExactActive =
                    EndfieldRecoveredEndminfM18PeakExactRuntime.ActiveThisFrame,
                endminfM18ExactSubmitted =
                    EndfieldRecoveredEndminfM18PeakExactRuntime.SubmittedThisFrame,
                endminfM18ExactValidated =
                    EndfieldRecoveredEndminfM18PeakExactRuntime.ValidatedThisFrame,
                endminfM18ExactFailure =
                    EndfieldRecoveredEndminfM18PeakExactRuntime.Failure,
                endminfM21ExactRequested =
                    EndfieldRecoveredEndminfM21PeakExactRuntime.Requested,
                endminfM21ExactActive =
                    EndfieldRecoveredEndminfM21PeakExactRuntime.ActiveThisFrame,
                endminfM21ExactSubmitted =
                    EndfieldRecoveredEndminfM21PeakExactRuntime.SubmittedThisFrame,
                endminfM21ExactValidated =
                    EndfieldRecoveredEndminfM21PeakExactRuntime.ValidatedThisFrame,
                endminfM21ExactFailure =
                    EndfieldRecoveredEndminfM21PeakExactRuntime.Failure,
                endminfM20ExactRequested =
                    EndfieldRecoveredEndminfM20PeakExactRuntime.Requested,
                endminfM20ExactActive =
                    EndfieldRecoveredEndminfM20PeakExactRuntime.ActiveThisFrame,
                endminfM20ExactSubmitted =
                    EndfieldRecoveredEndminfM20PeakExactRuntime.SubmittedThisFrame,
                endminfM20ExactValidated =
                    EndfieldRecoveredEndminfM20PeakExactRuntime.ValidatedThisFrame,
                endminfM20ExactFailure =
                    EndfieldRecoveredEndminfM20PeakExactRuntime.Failure,
                endminfM28ExactRequested =
                    EndfieldRecoveredEndminfM28PeakExactRuntime.Requested,
                endminfM28ExactActive =
                    EndfieldRecoveredEndminfM28PeakExactRuntime.ActiveThisFrame,
                endminfM28ExactSubmitted =
                    EndfieldRecoveredEndminfM28PeakExactRuntime.SubmittedThisFrame,
                endminfM28ExactValidated =
                    EndfieldRecoveredEndminfM28PeakExactRuntime.ValidatedThisFrame,
                endminfM28ExactFailure =
                    EndfieldRecoveredEndminfM28PeakExactRuntime.CurrentFailure,
                endminfM31ExactRequested =
                    EndfieldRecoveredEndminfM31PeakExactRuntime.Requested,
                endminfM31ExactExpected =
                    EndfieldRecoveredEndminfM31PeakExactRuntime
                        .IsCapturedPhase(activeBodyClipTime),
                endminfM31ExactActive =
                    EndfieldRecoveredEndminfM31PeakExactRuntime.ActiveThisFrame,
                endminfM31ExactSubmitted =
                    EndfieldRecoveredEndminfM31PeakExactRuntime.SubmittedThisFrame,
                endminfM31ExactValidated =
                    EndfieldRecoveredEndminfM31PeakExactRuntime.ValidatedThisFrame,
                endminfM31ExactPacket =
                    EndfieldRecoveredEndminfM31PeakExactRuntime
                        .SelectedPacketThisFrame,
                endminfM31ExactSourceFrame =
                    EndfieldRecoveredEndminfM31PeakExactRuntime
                        .SourceFrameThisFrame,
                endminfM31ExactFailure =
                    EndfieldRecoveredEndminfM31PeakExactRuntime.Failure,
                effectRootCount = roots.Length, admittedRenderers = renderers.Count(value => value.enabled),
                activeAdmittedRenderers = renderers.Count(value => value.enabled && value.gameObject.activeInHierarchy),
                admittedAliveParticles = renderers.Where(value => value.enabled && value.gameObject.activeInHierarchy)
                    .Sum(value => value.GetComponent<ParticleSystem>().particleCount),
                overview01SourceClockAuthenticated =
                    overview01SourceClockAuthenticated,
                overview01SourceSeededAnimationCount =
                    overview01SourceSeededAnimationCount,
                overview01SourceSeedSeconds = overview01SourceSeedSeconds,
                overview01SourceSeedFailure = overview01SourceSeedFailure,
                sharedCharEffectActive = sharedCharEffect != null &&
                    sharedCharEffect.activeInHierarchy,
                sharedCharEffectAliveParticles = sharedCharEffectSystems
                    .Sum(value => value.particleCount),
                sharedCharEffectTrailAliveParticles =
                    sharedTrailCount,
                sharedCharEffectTrailPositionMin = sharedTrailPositionMin,
                sharedCharEffectTrailPositionMax = sharedTrailPositionMax,
                sharedCharEffectTrailFirstSize = sharedTrailCount == 0
                    ? Vector3.zero
                    : sharedTrailParticles[0].GetCurrentSize3D(
                        sharedCharEffectTrail),
                sharedCharEffectTrailFirstVelocity = sharedTrailCount == 0
                    ? Vector3.zero
                    : sharedTrailParticles[0].velocity,
                sharedCharEffectTrailRendererBoundsCenter =
                    sharedCharEffectTrailRenderer == null
                        ? Vector3.zero
                        : sharedCharEffectTrailRenderer.bounds.center,
                sharedCharEffectTrailRendererBoundsExtents =
                    sharedCharEffectTrailRenderer == null
                        ? Vector3.zero
                        : sharedCharEffectTrailRenderer.bounds.extents,
                sharedCharEffectTrailRendererEnabled =
                    sharedCharEffectTrailRenderer != null &&
                    sharedCharEffectTrailRenderer.enabled,
                sharedCharEffectTrailRendererActive =
                    sharedCharEffectTrailRenderer != null &&
                    sharedCharEffectTrailRenderer.gameObject.activeInHierarchy,
                sharedCharEffectTrailShader =
                    sharedCharEffectTrailRenderer == null ||
                    sharedCharEffectTrailRenderer.sharedMaterial == null ||
                    sharedCharEffectTrailRenderer.sharedMaterial.shader == null
                        ? string.Empty
                        : sharedCharEffectTrailRenderer.sharedMaterial.shader.name,
                sharedCharEffectTrailPassCount =
                    sharedCharEffectTrailRenderer == null ||
                    sharedCharEffectTrailRenderer.sharedMaterial == null
                        ? 0
                        : sharedCharEffectTrailRenderer.sharedMaterial.passCount,
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
                farGridEnabled = farGrid != null && farGrid.enabled,
                farGridActive = farGrid != null && farGrid.gameObject.activeInHierarchy,
                farGridInCameraFrustum = farGridInFrustum,
                farGridBoundsCenter = farGrid == null ? Vector3.zero : farGrid.bounds.center,
                farGridBoundsExtents = farGrid == null ? Vector3.zero : farGrid.bounds.extents,
                farGridLayer = farGrid == null ? -1 : farGrid.gameObject.layer,
                farGridRenderQueue = farGrid == null || farGrid.sharedMaterial == null
                    ? -1
                    : farGrid.sharedMaterial.renderQueue,
                cameraCullingMask = camera == null ? 0 : camera.cullingMask,
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
                sphereOutsidePresentationReady = Shader.GetGlobalFloat(
                    "_EndfieldRecoveredSphereOutsidePresentationReady") > 0.5f,
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
                primaryRockFamily = roots
                    .SelectMany(value => value.GetComponentsInChildren<
                        EndfieldEndminfLitEffectCompatibilityBinding>(true))
                    .SelectMany(value => value.rows ?? Array.Empty<
                        EndfieldEndminfLitEffectCompatibilityBinding.Row>())
                    .Where(value => value != null && value.renderer != null)
                    .Select(value => Particle(value.renderer))
                    .OrderBy(value => value.path, StringComparer.Ordinal)
                    .ToArray(),
                litEffectBindingRowCount = roots
                    .SelectMany(value => value.GetComponentsInChildren<
                        EndfieldEndminfLitEffectCompatibilityBinding>(true))
                    .Sum(value => (value.rows ?? Array.Empty<
                        EndfieldEndminfLitEffectCompatibilityBinding.Row>())
                        .Count(row => row != null && row.renderer != null &&
                            row.material != null && row.mesh != null)),
                exactSuikuai1BindingReady = renderers.Count(value =>
                    IsExactSuikuai1BindingReady(value)) == 1,
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
                capturedSecondaryReplayPoseAppliedThisFrame =
                    capturedReplay != null && capturedReplay.PoseAppliedThisFrame,
                retainedSkinningRenderers = captureRetainedSkinningDiagnostic
                    ? EndfieldEndminfRetainedSkinningDiagnostic.Capture(actor)
                    : Array.Empty<
                        EndfieldEndminfRetainedSkinningDiagnostic.RendererRow>(),
                blockedRendererIdentities = renderers.Where(value => !value.enabled)
                    .Select(value => Hierarchy(value.transform) + " | " +
                        string.Join(", ", value.sharedMaterials.Select(material =>
                            material == null ? "<null>" : material.name + " -> " +
                                (material.shader == null ? "<null shader>" : material.shader.name))))
                    .OrderBy(value => value, StringComparer.Ordinal).ToArray(),
                topLeftBackgroundLumaMean = topLeftBackgroundLumaMean,
                topLeftBackgroundLumaMin = topLeftBackgroundLumaMin,
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
            FrameRow overview01SourceSeedFrame = Frames.FirstOrDefault(value =>
                value.overview01SourceClockAuthenticated &&
                value.overview01SourceSeededAnimationCount == 2 &&
                value.overview01SourceSeedSeconds > 0f &&
                string.IsNullOrEmpty(value.overview01SourceSeedFailure));
            bool observedOverview01AuthenticatedSourceSeed =
                overview01SourceSeedFrame != null;
            bool observedRotationOnlyRootMotion =
                Frames.Any(value => value.rootMotionCallbackCount > 0) &&
                Frames.All(value => value.rootMotionPositionDelta.sqrMagnitude <= 1.0e-10f);
            FrameRow firstEntranceFrame = Frames.FirstOrDefault(value =>
                value.effectRootCount == 4);
            int litEffectM01Count = firstEntranceFrame == null ||
                firstEntranceFrame.primaryRockFamily == null
                ? 0
                : firstEntranceFrame.primaryRockFamily.Count(value =>
                    value.materials != null &&
                    value.materials.SequenceEqual(new[] {
                        "M_fx_endminm_gfx_01" }));
            int litEffectM38Count = firstEntranceFrame == null ||
                firstEntranceFrame.primaryRockFamily == null
                ? 0
                : firstEntranceFrame.primaryRockFamily.Count(value =>
                    value.materials != null &&
                    value.materials.SequenceEqual(new[] {
                        "M_fx_endminm_gfx_38" }));
            int litEffectM27Count = firstEntranceFrame == null ||
                firstEntranceFrame.primaryRockFamily == null
                ? 0
                : firstEntranceFrame.primaryRockFamily.Count(value =>
                    value.materials != null &&
                    value.materials.SequenceEqual(new[] {
                        "M_fx_endminm_gfx_27" }));
            bool observedPrimaryRockCompatibilityBinding =
                firstEntranceFrame != null &&
                firstEntranceFrame.admittedRenderers == 68 &&
                firstEntranceFrame.litEffectBindingRowCount == 11 &&
                firstEntranceFrame.primaryRockFamily != null &&
                firstEntranceFrame.primaryRockFamily.Length == 11 &&
                litEffectM01Count == 7 && litEffectM38Count == 3 &&
                litEffectM27Count == 1 &&
                firstEntranceFrame.exactSuikuai1BindingReady &&
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
            bool observedSphereOutsidePresentationReady = Frames.Count > 0 &&
                Frames.All(value => value.sphereOutsidePresentationReady);
            bool observedPreGBufferDepthOwnerReady = Frames.All(value =>
                value.preGBufferDepthOwnerReady);
            bool observedCanonicalCharacterPreGBufferReady = Frames.All(value =>
                value.canonicalCharacterPreGBufferReady);
            bool observedDeferredExactConsumerReady = Frames.Any(value =>
                value.deferredExactConsumerReady);
            bool observedLightCookieDataReady = Frames.All(value =>
                value.lightCookieDataReady);
            bool endminfM27PresentationRequested = string.Equals(
                Environment.GetEnvironmentVariable(
                    "ENDFIELD_RECOVERED_ENDMINF_M27_PRESENTATION"),
                "1",
                StringComparison.Ordinal);
            bool deferredExactConsumerRequested =
                endminfM27PresentationRequested || string.Equals(
                    Environment.GetEnvironmentVariable(
                        "ENDFIELD_RECOVERED_DEFERRED_EXACT_CONSUMER"),
                    "1",
                    StringComparison.Ordinal);
            bool observedCanonicalSecondaryDynamicsOwnership =
                Environment.GetEnvironmentVariable(
                    "ENDFIELD_ENDMINF_CAPTURE_VIDEO_EXPORT") != "1" ||
                (Frames.Count > 0 && Frames.All(value =>
                    !value.secondaryDynamicsSolverWriteback &&
                    !value.capturedSecondaryReplayEnabled &&
                    !value.capturedSecondaryReplayPoseAppliedThisFrame));
            var missingObservations = new List<string>();
            if (!observedAnimatorContract) missingObservations.Add("Animator contract");
            if (!observedTransition) missingObservations.Add("start-to-loop transition");
            if (!observedSettledLoop) missingObservations.Add("settled loop");
            if (!observedEntranceVfx) missingObservations.Add("entrance VFX");
            if (!observedEntranceVfxCleanup) missingObservations.Add("entrance VFX cleanup");
            if (!observedOverview01AuthenticatedSourceSeed)
                missingObservations.Add(
                    "overview_01 authenticated one-shot source seed on two automatic Legacy Animation children");
            if (!observedRotationOnlyRootMotion)
                missingObservations.Add("rotation-only root motion with invariant position");
            if (!observedPrimaryRockCompatibilityBinding)
                missingObservations.Add(
                    "eleven-row LitEffect crystal compatibility plus exact suikuai (1) " +
                    "binding with two separate blocked effects " +
                    $"(rows={firstEntranceFrame?.litEffectBindingRowCount ?? 0}/11, " +
                    $"M01={litEffectM01Count}/7, M38={litEffectM38Count}/3, " +
                    $"M27={litEffectM27Count}/1, " +
                    $"suikuai={firstEntranceFrame?.exactSuikuai1BindingReady ?? false}, " +
                    $"admitted={firstEntranceFrame?.admittedRenderers ?? 0}/68, " +
                    $"blocked={firstEntranceFrame?.blockedRendererIdentities?.Length ?? 0}/2)");
            if (!observedCanonicalSecondaryDynamicsOwnership)
                missingObservations.Add(
                    "source-code secondary-dynamics ownership with both unverified solver " +
                    "writeback and captured-trajectory replay disabled");
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
            if (deferredExactConsumerRequested)
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
                if (endminfM27PresentationRequested &&
                    !observedEndminfM27PresentationReady)
                {
                    missingObservations.Add(
                        "exact M27 deferred presentation readiness");
                }
                if (IncludeCharInfoBackground &&
                    string.Equals(
                        Environment.GetEnvironmentVariable(
                            SphereOutsidePresentationEnvironment),
                        "1",
                        StringComparison.Ordinal) &&
                    !observedSphereOutsidePresentationReady)
                {
                    missingObservations.Add(
                        "physical SphereOutside deferred presentation readiness");
                }
                if (!observedLightCookieDataReady)
                    missingObservations.Add("exact-consumer LightCookieData readiness");
            }
            bool endminfSourceBackgroundIncluded =
                !IncludeCharInfoBackground || IsEndminfSourceBackgroundActive();
            bool fittedCompatibilityPlateActive =
                IsFittedCompatibilityPlateActive();
            FrameRow[] canonicalBackgroundProofFrames =
                SelectCanonicalBackgroundProofFrames();
            float minimumCanonicalBackgroundProofLumaMean =
                canonicalBackgroundProofFrames.Length == 0
                ? 0.0f
                : canonicalBackgroundProofFrames.Min(
                    value => value.topLeftBackgroundLumaMean);
            int minimumCanonicalBackgroundProofLuma =
                canonicalBackgroundProofFrames.Length == 0
                ? 0
                : canonicalBackgroundProofFrames.Min(
                    value => value.topLeftBackgroundLumaMin);
            bool canonicalSolidColorBackgroundIncluded =
                !IncludeCharInfoBackground ||
                (captureCanonicalSolidColorBackground &&
                 !endminfSourceBackgroundIncluded &&
                 !fittedCompatibilityPlateActive &&
                 IsCanonicalSolidColorBackgroundCamera(camera) &&
                 canonicalBackgroundProofFrames.Length ==
                    CanonicalBackgroundProofTimes.Length &&
                 minimumCanonicalBackgroundProofLumaMean >=
                    MinimumBackgroundProofMeanLuma &&
                  minimumCanonicalBackgroundProofLuma >=
                     MinimumBackgroundProofPixelLuma);
            bool canonicalSourceSphereFloorGridBackgroundIncluded =
                !IncludeCharInfoBackground ||
                (!captureCanonicalSolidColorBackground &&
                 endminfSourceBackgroundIncluded &&
                 observedSphereOutsidePresentationReady &&
                 Frames.Count > 0 &&
                 Frames.All(value => value.deferredExactConsumerReady) &&
                 !fittedCompatibilityPlateActive &&
                 IsCanonicalSolidColorBackgroundCamera(camera) &&
                 canonicalBackgroundProofFrames.Length ==
                    CanonicalBackgroundProofTimes.Length &&
                 minimumCanonicalBackgroundProofLumaMean >=
                    MinimumBackgroundProofMeanLuma &&
                 minimumCanonicalBackgroundProofLuma >=
                    MinimumBackgroundProofPixelLuma);
            bool charInfoBackgroundIncluded =
                canonicalSourceSphereFloorGridBackgroundIncluded ||
                canonicalSolidColorBackgroundIncluded;
            bool backgroundPortraitIncluded =
                !IncludeBackgroundPortrait || IsBackgroundPortraitActive();
            if (!charInfoBackgroundIncluded)
                missingObservations.Add(
                    "canonical Endminf background: expected the source " +
                    "SphereOutside deferred resolve plus CharFloorEffect/Far " +
                    "allow-list (or an explicitly requested neutral-clear A/B), " +
                    "camera RGBA(0.70,0.71,0.70,1), fitted route off, and " +
                    "0.65/4.4333334/6.65 s top-left 128x128 luma " +
                    "mean/min >= " +
                    MinimumBackgroundProofMeanLuma.ToString(
                        "0.0", CultureInfo.InvariantCulture) + "/" +
                    MinimumBackgroundProofPixelLuma + "; actual source=" +
                    endminfSourceBackgroundIncluded + ", sphereAll=" +
                    observedSphereOutsidePresentationReady + ", exactAll=" +
                    (Frames.Count > 0 && Frames.All(value =>
                        value.deferredExactConsumerReady)) + ", fitted=" +
                    fittedCompatibilityPlateActive + ", camera=" +
                    camera.clearFlags + " " +
                    camera.backgroundColor.ToString("F5") + ", mean/min=" +
                    minimumCanonicalBackgroundProofLumaMean.ToString(
                        "0.00", CultureInfo.InvariantCulture) + "/" +
                    minimumCanonicalBackgroundProofLuma + ", proofFrames=" +
                    string.Join(
                        ",",
                        canonicalBackgroundProofFrames.Select(
                            value => value.index.ToString(
                                CultureInfo.InvariantCulture)).ToArray()));
            if (fittedCompatibilityPlateActive)
                missingObservations.Add(
                    "fitted Endminf compatibility plate remained active");
            if (!backgroundPortraitIncluded)
                missingObservations.Add("active Endminf background portrait");
            bool observedEndminfSourcePostClock =
                Frames.Any(value => value.endminfPostEvaluated);
            if (EndfieldEndminfVisualCompatibilityClock.SourcePostRequested &&
                !observedEndminfSourcePostClock)
            {
                missingObservations.Add(
                    "authenticated Endminf overview_01 source-post clock");
            }
            bool observedEndminfPostSourceRgba16 =
                Frames.Count > 0 && Frames.All(value => string.Equals(
                    value.endminfPostSourceGraphicsFormat,
                    GraphicsFormat.R16G16B16A16_SFloat.ToString(),
                    StringComparison.Ordinal));
            if (EndfieldEndminfVisualCompatibilityClock.Requested &&
                !observedEndminfPostSourceRgba16)
            {
                missingObservations.Add(
                    "retail R16G16B16A16_FLOAT Uber source handoff");
            }
            bool observedEndminfBloomR11 =
                Frames.Count > 0 && Frames.All(value => string.Equals(
                    value.endminfBloomGraphicsFormat,
                    GraphicsFormat.B10G11R11_UFloatPack32.ToString(),
                    StringComparison.Ordinal));
            if (EndfieldEndminfVisualCompatibilityClock.Requested &&
                !observedEndminfBloomR11)
            {
                missingObservations.Add(
                    "retail R11G11B10_FLOAT Uber bloom handoff");
            }
            bool observedEndminfBloomDimensions =
                Frames.Count > 0 && Frames.All(value =>
                    value.endminfBloomWidth == Mathf.Max(captureWidth / 2, 1) &&
                    value.endminfBloomHeight == Mathf.Max(captureHeight / 2, 1));
            if (EndfieldEndminfVisualCompatibilityClock.Requested &&
                !observedEndminfBloomDimensions)
            {
                missingObservations.Add(
                    "half-source Endminf Uber bloom dimensions");
            }
            bool exactEndminfUberRequested = Frames.Any(
                value => value.exactEndminfUberRequested);
            bool observedExactEndminfUberSubmitted =
                Frames.Count > 0 && Frames.Any(
                    value => value.exactEndminfUberSubmitted);
            bool observedExactEndminfUberValidated =
                Frames.Count > 0 && Frames.Any(
                    value => value.exactEndminfUberValidated);
            // Capture 20260827T183054Z frame 1818 is the sole certified Uber
            // packet. Its body/reference frame maps to 4.350000 s, but retained
            // c0.z/c25.y solve the authenticated source-effect curves to
            // 4.4333334 s. The runtime assembly keeps its transport internal,
            // so mirror only the source-effect evidence constant here.
            const float capturedUberPhaseSeconds = 4.4333334f;
            bool capturedUberPhaseIncluded = Frames.Any(value =>
                value.endminfPostEvaluated && Mathf.Abs(
                    value.endminfPostSeconds -
                    capturedUberPhaseSeconds) <= 1.0f / 120.0f);
            bool exactEndminfUberRequirementReady =
                !exactEndminfUberRequested ||
                !capturedUberPhaseIncluded ||
                (observedExactEndminfUberSubmitted &&
                 observedExactEndminfUberValidated);
            string exactEndminfUberFailure = Frames
                .Select(value => value.exactEndminfUberFailure)
                .FirstOrDefault(value => !string.IsNullOrWhiteSpace(value)) ??
                string.Empty;
            bool observedExactEndminfLutProfileMatched =
                Frames.Count > 0 && Frames.All(value =>
                    value.exactEndminfLutProfileMatched);
            bool observedExactEndminfLutGpuValidated =
                Frames.Count > 0 && Frames.All(value =>
                    value.exactEndminfLutGpuValidated &&
                    !value.exactEndminfLutGpuValidationPending);
            bool observedCompatibilityExactEndminfLutBound =
                Frames.Count > 0 && Frames.All(value =>
                    value.compatibilityExactEndminfLutBound);
            string exactEndminfLutSha256 = Frames
                .Select(value => value.exactEndminfLutSha256)
                .FirstOrDefault(value => !string.IsNullOrWhiteSpace(value)) ??
                string.Empty;
            string exactEndminfLutFailure = Frames
                .Select(value => value.exactEndminfLutFailure)
                .FirstOrDefault(value => !string.IsNullOrWhiteSpace(value)) ??
                string.Empty;
            bool exactEndminfLutRequirementReady =
                observedExactEndminfLutProfileMatched &&
                observedExactEndminfLutGpuValidated &&
                observedCompatibilityExactEndminfLutBound &&
                string.Equals(
                    exactEndminfLutSha256,
                    "717c1d483662c00abe55e1c56a9d024f45e5c84c430ed9dd2854cb386f372482",
                    StringComparison.Ordinal);
            if (!exactEndminfLutRequirementReady)
            {
                missingObservations.Add(
                    "D3D11-validated exact Endminf CharInfo LUT compatibility binding" +
                    (string.IsNullOrWhiteSpace(exactEndminfLutFailure)
                        ? string.Empty
                        : " (" + exactEndminfLutFailure + ")"));
            }
            bool observedOpeningStripCompatibilityBeforeTemporal = Frames.Any(
                value => value.openingStripCompatibilityBeforeTemporal);
            bool observedOpeningStripSceneMVBeforeTemporal = Frames.Any(
                value => value.openingStripSceneMVBeforeTemporal);
            bool endminfOpeningStripExactRequested = Frames.Any(
                value => value.endminfOpeningStripExactRequested);
            FrameRow[] expectedEndminfOpeningStripExactFrames = Frames.Where(
                value => value.endminfOpeningStripExactRequested &&
                    value.endminfOpeningStripExactActive).ToArray();
            bool observedEndminfOpeningStripExactActive =
                expectedEndminfOpeningStripExactFrames.Length > 0;
            bool observedEndminfOpeningStripExactSubmitted =
                observedEndminfOpeningStripExactActive &&
                expectedEndminfOpeningStripExactFrames.All(value =>
                    value.endminfOpeningStripExactSubmitted);
            bool observedEndminfOpeningStripExactValidated =
                observedEndminfOpeningStripExactActive &&
                expectedEndminfOpeningStripExactFrames.All(value =>
                    value.endminfOpeningStripExactValidated);
            string endminfOpeningStripExactFailure = Frames
                .Select(value => value.endminfOpeningStripExactFailure)
                .FirstOrDefault(value => !string.IsNullOrWhiteSpace(value)) ??
                string.Empty;
            // The exact retained packet range is 0.1500 through 0.2500 s.
            // Mirror only its endpoints here so a full/video capture cannot
            // pass merely because a clock or selection defect activated no
            // packet. Focused captures wholly outside that range remain valid.
            bool endminfOpeningStripExactRangeIncluded =
                Frames.Any(value => value.targetSeconds <= 0.15001f) &&
                Frames.Any(value => value.targetSeconds >= 0.24999f);
            bool endminfOpeningStripExactRequirementReady =
                !endminfOpeningStripExactRequested ||
                !endminfOpeningStripExactRangeIncluded ||
                (observedEndminfOpeningStripExactActive &&
                 observedEndminfOpeningStripExactSubmitted &&
                 observedEndminfOpeningStripExactValidated);
            if (!endminfOpeningStripExactRequirementReady)
            {
                missingObservations.Add(
                    "exact Endminf opening-strip submission and synchronized validation" +
                    (string.IsNullOrWhiteSpace(endminfOpeningStripExactFailure)
                        ? string.Empty
                        : " (" + endminfOpeningStripExactFailure + ")"));
            }
            if (!exactEndminfUberRequirementReady)
            {
                missingObservations.Add(
                    "exact Endminf Uber native submission and synchronized validation" +
                    (string.IsNullOrWhiteSpace(exactEndminfUberFailure)
                        ? string.Empty
                        : " (" + exactEndminfUberFailure + ")"));
            }
            bool endminfM31ExactRequested = Frames.Any(
                value => value.endminfM31ExactRequested);
            FrameRow[] expectedEndminfM31Frames = Frames.Where(value =>
                value.endminfM31ExactRequested &&
                value.endminfM31ExactExpected).ToArray();
            bool observedEndminfM31ExactSubmitted =
                expectedEndminfM31Frames.Length > 0 &&
                expectedEndminfM31Frames.All(value =>
                    value.endminfM31ExactActive &&
                    value.endminfM31ExactSubmitted);
            bool observedEndminfM31ExactValidated =
                expectedEndminfM31Frames.Length > 0 &&
                expectedEndminfM31Frames.All(value =>
                    value.endminfM31ExactValidated);
            string endminfM31ExactFailure = Frames
                .Select(value => value.endminfM31ExactFailure)
                .FirstOrDefault(value => !string.IsNullOrWhiteSpace(value)) ??
                string.Empty;
            bool endminfM31ExactRequirementReady =
                !endminfM31ExactRequested ||
                expectedEndminfM31Frames.Length == 0 ||
                (observedEndminfM31ExactSubmitted &&
                 observedEndminfM31ExactValidated);
            if (!endminfM31ExactRequirementReady)
            {
                missingObservations.Add(
                    "exact Endminf M31 split submission and synchronized validation" +
                    (string.IsNullOrWhiteSpace(endminfM31ExactFailure)
                        ? string.Empty
                        : " (" + endminfM31ExactFailure + ")"));
            }
            bool unityPublicNgxProxyRequested = Frames.Any(
                value => value.unityPublicNgxProxyRequested);
            bool observedUnityPublicNgxProxySubmitted =
                unityPublicNgxProxyRequested && Frames
                    .Where(value => value.unityPublicNgxProxyRequested)
                    .All(value => value.unityPublicNgxProxySubmitted);
            bool observedUnityPublicNgxProxyValidated =
                unityPublicNgxProxyRequested && Frames
                    .Where(value => value.unityPublicNgxProxyRequested)
                    .All(value => value.unityPublicNgxProxyValidated);
            string unityPublicNgxProxyFailure = Frames
                .Select(value => value.unityPublicNgxProxyFailure)
                .FirstOrDefault(value => !string.IsNullOrWhiteSpace(value)) ??
                string.Empty;
            bool unityPublicNgxProxyRequirementReady =
                !unityPublicNgxProxyRequested ||
                (observedUnityPublicNgxProxySubmitted &&
                 observedUnityPublicNgxProxyValidated);
            if (!unityPublicNgxProxyRequirementReady)
            {
                missingObservations.Add(
                    "UnityPublicNgxProxy submission and post-execution debug validation" +
                    (string.IsNullOrWhiteSpace(unityPublicNgxProxyFailure)
                        ? string.Empty
                        : " (" + unityPublicNgxProxyFailure + ")"));
            }
            bool requiredCaptureContractReady =
                charInfoBackgroundIncluded &&
                backgroundPortraitIncluded &&
                observedEndminfPostSourceRgba16 &&
                observedEndminfBloomR11 &&
                exactEndminfLutRequirementReady &&
                exactEndminfUberRequirementReady &&
                endminfOpeningStripExactRequirementReady &&
                endminfM31ExactRequirementReady &&
                unityPublicNgxProxyRequirementReady;
            bool targetedTimes = !string.IsNullOrWhiteSpace(
                Environment.GetEnvironmentVariable(RequestedTimesEnvironment));
            // Targeted exact probes deliberately permit a content-invalid t11
            // diagnostic to withhold the final resolver presentation. They may
            // not, however, pass when the source scene itself has lost the four
            // entrance roots, eleven LitEffect rows, or exact b31/b34/GBuffer
            // prerequisites that make the diagnostic meaningful.
            bool exactConsumerSourceFixtureReady =
                !deferredExactConsumerRequested ||
                (observedEntranceVfx &&
                 observedPrimaryRockCompatibilityBinding &&
                 observedDeferredLightDataReady &&
                 observedDeferredShadowDataReady &&
                 observedDeferredPass0InputSubsetReady &&
                 observedDeferredGBufferFrameReady &&
                 observedEndminfM27HGBufferReady);
            if (!exactConsumerSourceFixtureReady)
            {
                missingObservations.Add(
                    "exact-consumer source fixture with four entrance roots, " +
                    "eleven LitEffect rows, b31/b34, and five-MRT M27 GBuffer");
            }
            requiredCaptureContractReady =
                requiredCaptureContractReady &&
                exactConsumerSourceFixtureReady;
            Report report = new Report {
                status = !requiredCaptureContractReady
                    ? "failed: missing " + string.Join(", ", missingObservations.ToArray())
                    : targetedTimes && capturePostStages
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
                charInfoBackgroundIncluded = charInfoBackgroundIncluded,
                endminfSourceBackgroundRequested = string.Equals(
                    Environment.GetEnvironmentVariable(
                        EndfieldRecoveredCharInfoPresentation
                            .EndminfSourceBackgroundEnvironmentVariable),
                    "1",
                    StringComparison.Ordinal),
                canonicalSolidColorBackgroundRequested =
                    captureCanonicalSolidColorBackground,
                endminfSourceBackgroundIncluded =
                    endminfSourceBackgroundIncluded,
                canonicalSourceSphereFloorGridBackgroundIncluded =
                    canonicalSourceSphereFloorGridBackgroundIncluded,
                canonicalSolidColorBackgroundIncluded =
                    canonicalSolidColorBackgroundIncluded,
                fittedCompatibilityPlateActive =
                    fittedCompatibilityPlateActive,
                backgroundPortraitIncluded = backgroundPortraitIncluded,
                canonicalSolidColorBackgroundProofTimes =
                    CanonicalBackgroundProofTimes.ToArray(),
                canonicalSolidColorBackgroundProofFrameIndices =
                    canonicalBackgroundProofFrames.Select(
                        value => value.index).ToArray(),
                minimumCanonicalBackgroundProofLumaMean =
                    minimumCanonicalBackgroundProofLumaMean,
                minimumCanonicalBackgroundProofLuma =
                    minimumCanonicalBackgroundProofLuma,
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
                observedOverview01AuthenticatedSourceSeed =
                    observedOverview01AuthenticatedSourceSeed,
                overview01SourceSeededAnimationCount =
                    overview01SourceSeedFrame?.overview01SourceSeededAnimationCount ?? 0,
                overview01SourceSeedSeconds =
                    overview01SourceSeedFrame?.overview01SourceSeedSeconds ?? 0f,
                overview01SourceSeedFailure = Frames
                    .Select(value => value.overview01SourceSeedFailure)
                    .FirstOrDefault(value => !string.IsNullOrEmpty(value)) ??
                    string.Empty,
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
                endminfM27PresentationRequested =
                    endminfM27PresentationRequested,
                observedEndminfM27PresentationReady =
                    observedEndminfM27PresentationReady,
                observedSphereOutsidePresentationReady =
                    observedSphereOutsidePresentationReady,
                observedEndminfPostSourceRgba16 =
                    observedEndminfPostSourceRgba16,
                observedEndminfBloomR11 = observedEndminfBloomR11,
                exactEndminfUberRequested = exactEndminfUberRequested,
                observedExactEndminfUberSubmitted =
                    observedExactEndminfUberSubmitted,
                observedExactEndminfUberValidated =
                    observedExactEndminfUberValidated,
                exactEndminfUberFailure = exactEndminfUberFailure,
                observedExactEndminfLutProfileMatched =
                    observedExactEndminfLutProfileMatched,
                observedExactEndminfLutGpuValidated =
                    observedExactEndminfLutGpuValidated,
                observedCompatibilityExactEndminfLutBound =
                    observedCompatibilityExactEndminfLutBound,
                exactEndminfLutSha256 = exactEndminfLutSha256,
                exactEndminfLutFailure = exactEndminfLutFailure,
                observedOpeningStripCompatibilityBeforeTemporal =
                    observedOpeningStripCompatibilityBeforeTemporal,
                observedOpeningStripSceneMVBeforeTemporal =
                    observedOpeningStripSceneMVBeforeTemporal,
                endminfOpeningStripExactRequested =
                    endminfOpeningStripExactRequested,
                observedEndminfOpeningStripExactActive =
                    observedEndminfOpeningStripExactActive,
                observedEndminfOpeningStripExactSubmitted =
                    observedEndminfOpeningStripExactSubmitted,
                observedEndminfOpeningStripExactValidated =
                    observedEndminfOpeningStripExactValidated,
                endminfOpeningStripExactFailure =
                    endminfOpeningStripExactFailure,
                endminfM31ExactRequested = endminfM31ExactRequested,
                observedEndminfM31ExactSubmitted =
                    observedEndminfM31ExactSubmitted,
                observedEndminfM31ExactValidated =
                    observedEndminfM31ExactValidated,
                endminfM31ExactFailure = endminfM31ExactFailure,
                unityPublicNgxProxyRequested = unityPublicNgxProxyRequested,
                observedUnityPublicNgxProxySubmitted =
                    observedUnityPublicNgxProxySubmitted,
                observedUnityPublicNgxProxyValidated =
                    observedUnityPublicNgxProxyValidated,
                unityPublicNgxProxyFailure = unityPublicNgxProxyFailure,
                observedPreGBufferDepthOwnerReady =
                    observedPreGBufferDepthOwnerReady,
                observedCanonicalCharacterPreGBufferReady =
                    observedCanonicalCharacterPreGBufferReady,
                deferredExactConsumerRequested =
                    deferredExactConsumerRequested,
                observedDeferredExactConsumerReady =
                    observedDeferredExactConsumerReady,
                observedLightCookieDataReady = observedLightCookieDataReady,
                gyroscopeMode = captureGyroscopeMode,
                gyroscopeInputProvider = captureGyroscopeInputProvider,
                gyroscopeInputX = captureGyroscopeInputX,
                gyroscopeInputY = captureGyroscopeInputY,
                gyroscopeEntryOffsetX = captureGyroscopeEntryOffsetX,
                gyroscopeEntryOffsetY = captureGyroscopeEntryOffsetY,
                // The _01 source-post owner is destroyed before the full sequence report
                // is published, which deliberately clears the live clock.
                // Preserve the observed first-frame phase difference instead.
                visualPostPreRollSeconds = Frames.Count > 0 &&
                    Frames[0].endminfPostEvaluated
                    ? Mathf.Max(
                        0.0f,
                        Frames[0].endminfPostSeconds - Frames[0].actualSeconds)
                    : 0.0f,
                retainedSkinningDiagnostic = captureRetainedSkinningDiagnostic,
                frames = Frames.ToArray()
            };
            File.WriteAllText(Path.Combine(output, "report.json"), JsonUtility.ToJson(report, true));
            bool fineWindow = Environment.GetEnvironmentVariable(
                "ENDFIELD_ENDMINF_CAPTURE_FINE_WINDOW") == "1";
            bool videoExport = Environment.GetEnvironmentVariable(
                "ENDFIELD_ENDMINF_CAPTURE_VIDEO_EXPORT") == "1";
            EditorApplication.update -= Tick;
            if (!requiredCaptureContractReady)
            {
                captureFailure =
                    "Endminf Viewer capture is missing its required UI-free " +
                    "composition or retail post-source handoff: " +
                    string.Join(", ", missingObservations.ToArray());
                Debug.LogError(captureFailure);
                EditorApplication.ExitPlaymode();
                return;
            }
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
                    BuildSideBySideComparison(
                        "endminf_overview_clean_2026-08-26",
                        "endminf_overview_start_and_loop_clean",
                        "reference_clean_vs_unity_4fps.png",
                        "reference_clean_comparison.json");
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

        private static bool IsEndminfSourceBackgroundActive()
        {
            return UnityEngine.Object
                .FindObjectsOfType<EndfieldRecoveredCharInfoPresentation>(true)
                .Any(value =>
                    value != null &&
                    value.enabled &&
                    value.gameObject.activeInHierarchy &&
                    value.EndminfSourceBackgroundActive &&
                    value.sourceContent != null &&
                    value.sourceContent.activeInHierarchy &&
                    value.farGridRenderer != null &&
                    value.farGridRenderer.enabled &&
                    value.farGridRenderer.gameObject.activeInHierarchy &&
                    value.sphereOutsideRenderer != null &&
                    !value.sphereOutsideRenderer.enabled &&
                    value.floorRenderer != null &&
                    value.floorRenderer.enabled &&
                    value.wallRenderer != null &&
                    !value.wallRenderer.enabled &&
                    value.shadowPlaneRenderer != null &&
                    !value.shadowPlaneRenderer.enabled &&
                    (value.compatibilityBackdropRenderer == null ||
                     !value.compatibilityBackdropRenderer.enabled));
        }

        private static bool IsFittedCompatibilityPlateActive()
        {
            return UnityEngine.Object
                .FindObjectsOfType<EndfieldRecoveredCharInfoPresentation>(true)
                .Any(value =>
                    value != null &&
                    value.enabled &&
                    value.gameObject.activeInHierarchy &&
                    value.compatibilityBackdropRenderer != null &&
                    value.compatibilityBackdropRenderer.enabled &&
                    value.compatibilityBackdropRenderer.gameObject.activeInHierarchy);
        }

        private static bool IsCanonicalSolidColorBackgroundCamera(Camera value)
        {
            if (value == null || value.clearFlags != CameraClearFlags.SolidColor)
                return false;
            Color actual = value.backgroundColor;
            return Mathf.Abs(actual.r - CanonicalSolidBackgroundColor.r) <= 1.0e-4f &&
                Mathf.Abs(actual.g - CanonicalSolidBackgroundColor.g) <= 1.0e-4f &&
                Mathf.Abs(actual.b - CanonicalSolidBackgroundColor.b) <= 1.0e-4f &&
                Mathf.Abs(actual.a - CanonicalSolidBackgroundColor.a) <= 1.0e-4f;
        }

        private static FrameRow[] SelectCanonicalBackgroundProofFrames()
        {
            if (Frames.Count == 0)
                return Array.Empty<FrameRow>();
            var selected = new List<FrameRow>(
                CanonicalBackgroundProofTimes.Length);
            float maximumPhaseError = 1.0f / (2.0f * SimulationFps) + 1.0e-5f;
            foreach (float target in CanonicalBackgroundProofTimes)
            {
                FrameRow nearest = Frames
                    .OrderBy(value => Mathf.Abs(value.requestedSeconds - target))
                    .FirstOrDefault();
                if (nearest == null || Mathf.Abs(
                        nearest.requestedSeconds - target) > maximumPhaseError)
                {
                    return Array.Empty<FrameRow>();
                }
                selected.Add(nearest);
            }
            return selected.ToArray();
        }

        private static bool IsBackgroundPortraitActive()
        {
            return UnityEngine.Object
                .FindObjectsOfType<EndfieldRecoveredCharInfoBackgroundPortrait>(true)
                .Any(value =>
                {
                    if (value == null ||
                        !value.enabled ||
                        !value.gameObject.activeInHierarchy ||
                        !value.RecoveredPortraitRequested)
                    {
                        return false;
                    }

                    Renderer renderer = value.portraitRenderer != null
                        ? value.portraitRenderer
                        : value.GetComponent<Renderer>();
                    MeshFilter filter = value.portraitMeshFilter != null
                        ? value.portraitMeshFilter
                        : value.GetComponent<MeshFilter>();
                    Material material = renderer != null
                        ? renderer.sharedMaterial
                        : null;
                    return renderer != null &&
                           renderer.enabled &&
                           renderer.gameObject.activeInHierarchy &&
                           filter != null &&
                           filter.sharedMesh != null &&
                           material != null &&
                           material.shader != null &&
                           string.Equals(
                               material.shader.name,
                               EndfieldRecoveredCharInfoBackgroundPortrait.ShaderName,
                               StringComparison.Ordinal);
                });
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
            var particles = new ParticleSystem.Particle[Mathf.Max(1, system.particleCount)];
            int particleCount = system.GetParticles(particles);
            ParticleSystem.Particle first = particleCount > 0
                ? particles[0]
                : default;
            Vector3 firstWorld = first.position;
            if (particleCount > 0 && main.simulationSpace == ParticleSystemSimulationSpace.Local)
                firstWorld = system.transform.TransformPoint(first.position);
            else if (particleCount > 0 &&
                     main.simulationSpace == ParticleSystemSimulationSpace.Custom &&
                     main.customSimulationSpace != null)
                firstWorld = main.customSimulationSpace.TransformPoint(first.position);
            var custom1 = new List<Vector4>();
            system.GetCustomParticleData(
                custom1,
                ParticleSystemCustomData.Custom1);
            Mesh mesh = renderer.mesh;
            Bounds bounds = renderer.bounds;
            Color32 firstColor = first.GetCurrentColor(system);
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
                alive = system.particleCount,
                rendererBoundsCenter = bounds.center,
                rendererBoundsExtents = bounds.extents,
                rendererViewportCenter = camera != null
                    ? camera.WorldToViewportPoint(bounds.center)
                    : Vector3.zero,
                mesh = mesh != null ? mesh.name : string.Empty,
                meshBoundsCenter = mesh != null ? mesh.bounds.center : Vector3.zero,
                meshBoundsExtents = mesh != null ? mesh.bounds.extents : Vector3.zero,
                firstParticlePosition = first.position,
                firstParticleWorldPosition = firstWorld,
                firstParticleSize3D = first.GetCurrentSize3D(system),
                firstParticleRotation3D = first.rotation3D,
                firstParticleColor = new Vector4(
                    firstColor.r / 255f,
                    firstColor.g / 255f,
                    firstColor.b / 255f,
                    firstColor.a / 255f),
                firstParticleRemainingLifetime = first.remainingLifetime,
                firstParticleStartLifetime = first.startLifetime,
                firstParticleRandomSeed = first.randomSeed,
                firstParticleCustom1 = custom1.Count > 0 ? custom1[0] : Vector4.zero,
            };
        }

        private static bool IsExactSuikuai1BindingReady(
            ParticleSystemRenderer renderer)
        {
            if (renderer == null || !renderer.enabled ||
                renderer.transform.parent == null ||
                renderer.gameObject.name != "suikuai (1)" ||
                renderer.transform.parent.gameObject.name != "all" ||
                renderer.renderMode != ParticleSystemRenderMode.Mesh ||
                !renderer.enableGPUInstancing || renderer.meshCount != 4)
                return false;

            Material[] materials = renderer.sharedMaterials;
            Material material = materials != null && materials.Length == 1
                ? materials[0]
                : null;
            return material != null &&
                material.name == ExactSuikuai1MaterialName &&
                material.shader != null &&
                material.shader.name == ExactRefractShader;
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
                captureWidth,
                captureHeight,
                24,
                exactFinalTarget ? RenderTextureFormat.ARGB32 : RenderTextureFormat.ARGBHalf,
                RenderTextureReadWrite.Linear);
            rt.Create(); RenderTexture old = RenderTexture.active; value.targetTexture = rt; value.Render();
            RenderTexture.active = rt;
            var texture = new Texture2D(
                captureWidth,
                captureHeight,
                TextureFormat.RGBA32,
                false,
                false);
            texture.ReadPixels(
                new Rect(0, 0, captureWidth, captureHeight),
                0,
                0);
            texture.Apply();
            Color32[] pixels = texture.GetPixels32();
            value.targetTexture = null; RenderTexture.active = old; UnityEngine.Object.Destroy(texture); rt.Release(); UnityEngine.Object.Destroy(rt);
            return pixels;
        }

        private static void MeasureTopLeftBackground(
            Color32[] pixels,
            out float meanLuma,
            out int minimumLuma)
        {
            if (pixels == null || pixels.Length != captureWidth * captureHeight)
            {
                throw new InvalidDataException(
                    "Endminf background proof requires one complete presented " +
                    "frame; expected " + (captureWidth * captureHeight) +
                    " pixels, actual " + (pixels == null ? 0 : pixels.Length) + ".");
            }
            int width = Math.Min(BackgroundProofEdgePixels, captureWidth);
            int height = Math.Min(BackgroundProofEdgePixels, captureHeight);
            long lumaSum = 0;
            minimumLuma = 255;
            // Texture2D.GetPixels32 uses bottom-left ordering. Start at the
            // highest rows to prove the unobscured top-left carrier after the
            // complete render pipeline, not merely the camera configuration.
            for (int y = captureHeight - height; y < captureHeight; y++)
            {
                int row = y * captureWidth;
                for (int x = 0; x < width; x++)
                {
                    Color32 pixel = pixels[row + x];
                    int luma = (54 * pixel.r + 183 * pixel.g +
                        19 * pixel.b + 128) >> 8;
                    lumaSum += luma;
                    minimumLuma = Math.Min(minimumLuma, luma);
                }
            }
            meanLuma = lumaSum / (float)(width * height);
        }

        private static Color32[] Read(string path)
        {
            var texture = new Texture2D(2, 2, TextureFormat.RGBA32, false, false);
            texture.LoadImage(File.ReadAllBytes(path));
            Color32[] pixels = texture.GetPixels32();
            UnityEngine.Object.Destroy(texture);
            return pixels;
        }

        private static void ConfigureDeterministicGyroscopeCapture()
        {
            CharacterRecoveryPresentationProfile profile =
                EndfieldPlayableCharInfoProfileBuilder.LoadProfile("Endminf");
            if (profile == null || !profile.sourceRecovered)
            {
                throw new InvalidOperationException(
                    "Canonical/batch gyroscope capture requires the " +
                    "source-recovered Endminf presentation profile.");
            }
            captureGyroscopeEntryOffsetX =
                profile.gyroscopeEntryOffsets.x.ToString(
                    "R",
                    CultureInfo.InvariantCulture);
            captureGyroscopeEntryOffsetY =
                profile.gyroscopeEntryOffsets.y.ToString(
                    "R",
                    CultureInfo.InvariantCulture);
            EndfieldRecoveredCharInfoGyroscopeCameraState.RecoveryMode mode =
                EndfieldRecoveredCharInfoGyroscopeCameraState.ResolveMode();
            if (mode == EndfieldRecoveredCharInfoGyroscopeCameraState
                    .RecoveryMode.LiveInput)
            {
                throw new InvalidOperationException(
                    "Canonical/batch Endminf capture rejects live-input gyroscope " +
                    "mode because UnityEngine.Input.mousePosition is external, " +
                    "non-deterministic state. Use the interactive launcher for live " +
                    "input, or select a source-auditable deterministic mode.");
            }

            captureGyroscopeMode =
                EndfieldRecoveredCharInfoGyroscopeCameraState.ModeName(mode);
            captureGyroscopeInputX = string.Empty;
            captureGyroscopeInputY = string.Empty;
            switch (mode)
            {
                case EndfieldRecoveredCharInfoGyroscopeCameraState
                        .RecoveryMode.SerializedEntry:
                    captureGyroscopeInputProvider =
                        "presentation-profile.gyroscopeEntryOffsets";
                    break;
                case EndfieldRecoveredCharInfoGyroscopeCameraState
                        .RecoveryMode.NeutralCenteredInput:
                    captureGyroscopeInputProvider =
                        "source-curves.normalized-zero";
                    captureGyroscopeInputX = "0";
                    captureGyroscopeInputY = "0";
                    break;
                case EndfieldRecoveredCharInfoGyroscopeCameraState
                        .RecoveryMode.RecordedInputEndpoint:
                    if (!EndfieldRecoveredCharInfoGyroscopeCameraState
                            .TryGetRecordedNormalizedInput(
                                out Vector2 recordedInput))
                    {
                        throw new InvalidOperationException(
                            "recorded-input-endpoint capture requires explicit " +
                            "normalized X/Y selectors in [-1,1].");
                    }
                    captureGyroscopeInputProvider =
                        "explicit-normalized-input-selector";
                    captureGyroscopeInputX = recordedInput.x.ToString(
                        "R",
                        CultureInfo.InvariantCulture);
                    captureGyroscopeInputY = recordedInput.y.ToString(
                        "R",
                        CultureInfo.InvariantCulture);
                    break;
                case EndfieldRecoveredCharInfoGyroscopeCameraState
                        .RecoveryMode.Off:
                    captureGyroscopeInputProvider = "disabled";
                    break;
                default:
                    throw new InvalidOperationException(
                        $"Unsupported batch gyroscope mode: {mode}.");
            }
        }

        private static int ParseCaptureDimension(string environment, int fallback)
        {
            string value = Environment.GetEnvironmentVariable(environment);
            if (string.IsNullOrWhiteSpace(value))
                return fallback;
            if (!int.TryParse(
                    value.Trim(),
                    NumberStyles.Integer,
                    CultureInfo.InvariantCulture,
                    out int dimension) ||
                dimension < 64 || dimension > 8192)
            {
                throw new InvalidOperationException(
                    environment + " must be an integer from 64 through 8192.");
            }
            return dimension;
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
            var texture = new Texture2D(
                captureWidth,
                captureHeight,
                TextureFormat.RGBA32,
                false,
                false);
            // ReadPixels/GetPixels32 and SetPixels32 share Texture2D's
            // bottom-left pixel order. Flipping here produced vertically
            // inverted PNGs and required a second compensating flip in Read.
            texture.SetPixels32(pixels);
            texture.Apply();
            File.WriteAllBytes(path, texture.EncodeToPNG());
            UnityEngine.Object.Destroy(texture);
        }
    }
}
