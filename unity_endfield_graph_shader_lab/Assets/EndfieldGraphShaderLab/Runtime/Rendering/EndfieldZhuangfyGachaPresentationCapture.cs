using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Playables;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Scene-local, standalone-only capture coordinator for the recovered Zhuangfy
    /// gacha presentation. The authoritative disabled source Camera remains disabled;
    /// an isolated presentation Camera follows its exact sampled transform/FOV.
    /// </summary>
    [DefaultExecutionOrder(32000)]
    [DisallowMultipleComponent]
    public sealed class EndfieldZhuangfyGachaPresentationCapture : MonoBehaviour
    {
        // Installed globalgamemanagers TagManager plus the shipped
        // CameraManager.EnableGachaCullingMask route close these values.
        public const int SourceGachaLayer = 30;
        public const int SourceGachaCullingMask = 0x40010008;

        private const string OutputArgument = "-endfield-zhuangfy-gacha-capture-output";
        private const string QuitArgument = "-endfield-zhuangfy-gacha-capture-quit";
        private const string FailClosedShader =
            "Hidden/Endfield/Recovered/VFXUnavailableFailClosed";
        private static readonly int RecoveredPostSemanticsId =
            Shader.PropertyToID("_EndfieldRecoveredPostSemantics");
        private const string PrefabAssetPath =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Zhuangfy/Effects/" +
            "GachaRuntime/Zhuangfy_Gacha_Recovered.prefab";
        private const string ReferenceRelativePath =
            "ReferenceCaptures/Zhuangfy/public_3d_demo_BV1M7D1BKEbQ_25fps.mp4";
        private const string ReferenceSha256 =
            "18389E9658E524FBAF03E3605402EA8A5B9FF4C608AB4FFF97F256023D3A11C9";
        private const int CaptureWidth = 1920;
        private const int CaptureHeight = 1080;
        private const int CaptureFps = 25;
        private const int MaximumWaitFrames = 18000;
        private const double TimelineDuration = 14.033333333333333;
        private const double TimingTolerance = 0.002;
        private static readonly Color SentinelColor =
            new Color(239.0f / 255.0f, 17.0f / 255.0f, 157.0f / 255.0f, 1.0f);

        [Serializable]
        private sealed class CaptureManifest
        {
            public string schema = "endfield.zhuangfy-gacha-presentation-capture.v3";
            public string verdict;
            public string captureMode =
                "isolated standalone player; normal Update/LateUpdate/PlayableDirector chronology";
            public string editModeAudit =
                "Camera.Render in edit mode is rejected: it does not run Start/Update/LateUpdate, " +
                "the recovered 0.25s scaled start delay, or the automatic exact particle hosts.";
            public string prefabAssetPath = PrefabAssetPath;
            public string cameraContract =
                "Exact recovered actor-camera track is sampled on its disabled source Camera. " +
                "A disposable capture Camera copies only the source-closed animated world pose and " +
                "vertical FOV; its configured HG render/output fields remain unchanged.";
            public string failClosedContract =
                "The harness never enables the source Camera and never changes renderer materials. " +
                "Fail-closed material identities must remain byte-for-byte stable as a sorted census.";
            public string referencePath = ReferenceRelativePath;
            public string referenceSha256 = ReferenceSha256;
            public string referenceUse =
                "Public retail entrance reference; qualitative composition/effect/timing only.";
            public string timingQuantizationBoundary =
                "The public reference is 25 fps. Authored source times are captured on the nearest " +
                "25 fps player frame (midpoints away from zero); the Timeline terminal sample is " +
                "clamped to its exact duration. Exact-frame retail equivalence is not claimed.";
            public int width = CaptureWidth;
            public int height = CaptureHeight;
            public int framesPerSecond = CaptureFps;
            public float recoveredScaledPlayDelaySeconds;
            public float observedPlayerLoopStartDelaySeconds;
            public int observedPlayerLoopStartDelayFrames;
            public bool sourceCameraStayedDisabled;
            public int presentationCullingMask;
            public bool presentationUseOcclusionCulling;
            public int captureScopeLayer;
            public int captureScopeGameObjectCount;
            public bool everyCaptureScopeGameObjectLayerIsGacha;
            public string presentationViewport;
            public int presentationTargetDisplay;
            public string presentationClearFlags;
            public string renderPipelineAsset;
            public string renderPipelineInstance;
            public int beginCameraRenderingCount;
            public int endCameraRenderingCount;
            public string renderHandoffEvidence =
                "The custom HDRenderPipeline does not publish SRP begin/end camera callbacks. " +
                "A bright per-frame sentinel is written in LateUpdate and must be overwritten " +
                "before end-of-frame readback.";
            public bool renderTargetSentinelOverwritten;
            public bool everyFrameNonBlack;
            public bool canonicalFramesVisuallyDistinct;
            public int maximumSentinelPixelCount;
            public int minimumNonBlackPixelCount;
            public int distinctPngHashCount;
            public int failClosedMaterialCount;
            public string initialFailClosedCensusSha256;
            public string finalFailClosedCensusSha256;
            public FrameRecord[] frames = Array.Empty<FrameRecord>();
        }

        [Serializable]
        private sealed class FrameRecord
        {
            public int index;
            public string label;
            public double authoredSourceTimeSeconds;
            public double nearest25FpsTimelineTimeSeconds;
            public double capturedTimelineTimeSeconds;
            public double authoredToCapturedErrorSeconds;
            public int unityFrameCount;
            public string png;
            public long pngBytes;
            public string pngSha256;
            public int nonBlackPixelCount;
            public float nonBlackPixelFraction;
            public float meanRgbLuma;
            public int maximumRgbChannel;
            public int sentinelPixelCount;
            public float cameraVerticalFovDegrees;
            public int playingParticleSystems;
            public int aliveParticleCount;
            public int activeRenderers;
            public int activeAddedMaterialRecords;
            public int appliedAddedMaterialRecords;
            public int activeDissolveReplacementMaterials;
            public string failClosedCensusSha256;
            public ParticleSystemRecord[] particleSystems =
                Array.Empty<ParticleSystemRecord>();
        }

        [Serializable]
        private sealed class ParticleSystemRecord
        {
            public string effectRoot;
            public string hierarchy;
            public long particleSystemPathId;
            public long particleRendererPathId;
            public long[] materialPathIds = Array.Empty<long>();
            public string[] materialNames = Array.Empty<string>();
            public string[] shaderNames = Array.Empty<string>();
            public string[] activeVertexStreams = Array.Empty<string>();
            public bool gameObjectActive;
            public bool rendererEnabled;
            public bool isPlaying;
            public bool isPaused;
            public bool isStopped;
            public float simulationTime;
            public int particleCount;
            public int renderMode;
            public int renderAlignment;
            public Vector3 rendererBoundsCenter;
            public Vector3 rendererBoundsExtents;
            public ParticleRecord[] particles = Array.Empty<ParticleRecord>();
        }

        [Serializable]
        private sealed class ParticleRecord
        {
            public int index;
            public uint randomSeed;
            public Vector3 position;
            public Vector3 worldPosition;
            public Vector3 velocity;
            public Vector3 currentSize;
            public Color currentColor;
            public float remainingLifetime;
            public float startLifetime;
            public float rotation;
            public float angularVelocity;
            public Vector4 custom1;
        }

        private struct CanonicalSample
        {
            public string label;
            public double authoredTime;

            public CanonicalSample(string label, double authoredTime)
            {
                this.label = label;
                this.authoredTime = authoredTime;
            }
        }

        private static readonly CanonicalSample[] CanonicalSamples =
        {
            new CanonicalSample("timeline_start", 0.0),
            new CanonicalSample("scaled_delay_boundary", 0.25),
            new CanonicalSample("one_second", 1.0),
            new CanonicalSample("two_seconds", 2.0),
            new CanonicalSample("finger_lightning_start", 3.95),
            new CanonicalSample("piaodai_end", 4.5),
            new CanonicalSample("baofa_start", 5.4833333333),
            new CanonicalSample("baofa_early", 5.75),
            new CanonicalSample("trail_end", 6.05),
            new CanonicalSample("finger_lightning_end", 8.95),
            new CanonicalSample("baofa_end", 9.4),
            new CanonicalSample("camera_clip_end", 10.7),
            new CanonicalSample("timeline_end", TimelineDuration),
        };

        public EndfieldRecoveredZhuangfyGachaRuntime runtime;
        public EndfieldRecoveredZhuangfyExternalCameraPlayback sourceCameraPlayback;
        public Camera presentationCamera;
        public Transform captureScopeRoot;

        private bool captureArmed;
        private bool sourceCameraStayedDisabled = true;
        private double lastLateDirectorTime;
        private string outputDirectory;
        private string initialFailClosedCensus;
        private string initialFailClosedCensusSha256;
        private int initialFailClosedMaterialCount;
        private float beginScaledTime;
        private float observedPlayStartDelay = float.NaN;
        private RenderTexture captureTarget;
        private int presentationCullingMask;
        private bool presentationUseOcclusionCulling;
        private int captureScopeGameObjectCount;
        private Rect presentationViewport;
        private int presentationTargetDisplay;
        private CameraClearFlags presentationClearFlags;
        private bool presentationAllowHdr;
        private bool presentationAllowMsaa;
        private int beginCameraRenderingCount;
        private int endCameraRenderingCount;
        private int lastBeginCameraRenderingFrame = -1;
        private int lastEndCameraRenderingFrame = -1;

        private void Awake()
        {
            string[] arguments = Environment.GetCommandLineArgs();
            outputDirectory = ReadArgument(arguments, OutputArgument);
            if (string.IsNullOrWhiteSpace(outputDirectory))
            {
                enabled = false;
                return;
            }

            try
            {
                ValidateSceneContract();
                // This disposable player exists only to exercise the recovered
                // retail post path. Publish the selector before validating the
                // capture target; component OnEnable ordering must not decide
                // whether the isolated validation can arm.
                Shader.SetGlobalFloat(RecoveredPostSemanticsId, 1.0f);
                outputDirectory = Path.GetFullPath(outputDirectory);
                Directory.CreateDirectory(outputDirectory);
                RequireDirectoryHasNoCaptureArtifacts(outputDirectory);
                QualitySettings.vSyncCount = 0;
                Application.targetFrameRate = CaptureFps;
                Time.captureDeltaTime = 1.0f / CaptureFps;
                Time.maximumDeltaTime = 1.0f / CaptureFps;
                Screen.SetResolution(CaptureWidth, CaptureHeight, false);
                var captureDescriptor = new RenderTextureDescriptor(
                    CaptureWidth,
                    CaptureHeight)
                {
                    graphicsFormat = GraphicsFormat.R8G8B8A8_UNorm,
                    depthStencilFormat = GraphicsFormat.None,
                    msaaSamples = 1,
                    volumeDepth = 1,
                    dimension = UnityEngine.Rendering.TextureDimension.Tex2D,
                    useMipMap = false,
                    autoGenerateMips = false,
                    sRGB = false,
                };
                captureTarget = new RenderTexture(captureDescriptor)
                {
                    name = "Zhuangfy Gacha Presentation Capture Target",
                };
                if (!captureTarget.Create())
                    throw new InvalidOperationException(
                        "Could not create the deterministic presentation RenderTexture.");
                if (captureTarget.graphicsFormat !=
                        GraphicsFormat.R8G8B8A8_UNorm ||
                    captureTarget.sRGB ||
                    Shader.GetGlobalFloat(RecoveredPostSemanticsId) <= 0.5f ||
                    !HGCompatRenderPipeline
                        .IsRecoveredLinearUnormFinalTargetRequested())
                {
                    throw new InvalidOperationException(
                        "Capture requires the existing recovered post-semantics and " +
                        "linear-UNorm final-target selectors plus an exact non-sRGB " +
                        "R8G8B8A8_UNorm RenderTexture.");
                }
                presentationCamera.targetTexture = captureTarget;
                RenderPipelineManager.beginCameraRendering +=
                    OnBeginCameraRendering;
                RenderPipelineManager.endCameraRendering +=
                    OnEndCameraRendering;
                presentationCullingMask = presentationCamera.cullingMask;
                presentationUseOcclusionCulling =
                    presentationCamera.useOcclusionCulling;
                captureScopeGameObjectCount =
                    captureScopeRoot.GetComponentsInChildren<Transform>(true).Length;
                presentationViewport = presentationCamera.rect;
                presentationTargetDisplay = presentationCamera.targetDisplay;
                presentationClearFlags = presentationCamera.clearFlags;
                presentationAllowHdr = presentationCamera.allowHDR;
                presentationAllowMsaa = presentationCamera.allowMSAA;
                runtime.autoStartRecoveredEffect = false;
                runtime.BindSourceBackedPresentation(
                    presentationCamera.GetComponent<EndfieldHGOperatorLightRig>(),
                    presentationCamera.GetComponent<EndfieldHGRPCharacterLightingVolume>());
                captureArmed = true;
            }
            catch (Exception exception)
            {
                Fail("Initialization failed: " + exception);
            }
        }

        private IEnumerator Start()
        {
            if (!captureArmed)
                yield break;

            // Fixed resolution settling keeps ordinary captures deterministic.
            for (int resolutionSettleFrame = 0; resolutionSettleFrame < 4;
                resolutionSettleFrame++)
                yield return null;
            if (Screen.width != CaptureWidth || Screen.height != CaptureHeight)
            {
                Fail(
                    $"Player resolution is {Screen.width}x{Screen.height}; " +
                    $"required {CaptureWidth}x{CaptureHeight}.");
                yield break;
            }
            initialFailClosedCensus = BuildFailClosedCensus(
                out initialFailClosedMaterialCount);
            initialFailClosedCensusSha256 = ComputeSha256(initialFailClosedCensus);
            beginScaledTime = Time.time;
            if (!runtime.BeginRecoveredEffectStart(beginScaledTime))
            {
                Fail("Recovered BeginRecoveredEffectStart rejected the generated scene.");
                yield break;
            }

            var records = new List<FrameRecord>(CanonicalSamples.Length);
            var waitForEndOfFrame = new WaitForEndOfFrame();
            foreach (CanonicalSample sample in CanonicalSamples)
            {
                double requestedTimelineTime =
                    QuantizeToPlayerTimeline(sample.authoredTime);
                bool captured = false;
                for (int wait = 0; wait < MaximumWaitFrames; wait++)
                {
                    yield return waitForEndOfFrame;
                    double observed = lastLateDirectorTime;
                    if (observed + TimingTolerance < requestedTimelineTime)
                        continue;
                    if (observed - requestedTimelineTime > 0.021)
                    {
                        Fail(
                            $"Timeline skipped canonical sample '{sample.label}': " +
                            $"requested={Format(requestedTimelineTime)}, " +
                            $"observed={Format(observed)}.");
                        yield break;
                    }

                    FrameRecord record;
                    try
                    {
                        record = CaptureFrame(
                            records.Count,
                            sample,
                            requestedTimelineTime,
                            observed);
                    }
                    catch (Exception exception)
                    {
                        Fail($"Capture '{sample.label}' failed: {exception}");
                        yield break;
                    }
                    records.Add(record);
                    captured = true;
                    break;
                }
                if (!captured)
                {
                    Fail($"Timed out waiting for canonical sample '{sample.label}'.");
                    yield break;
                }
            }

            string finalCensus = BuildFailClosedCensus(out int finalCount);
            string finalCensusSha256 = ComputeSha256(finalCensus);
            if (!string.Equals(
                    initialFailClosedCensus,
                    finalCensus,
                    StringComparison.Ordinal))
            {
                Fail(
                    "Fail-closed material census changed during capture: " +
                    $"initial={initialFailClosedCensusSha256}, final={finalCensusSha256}.");
                yield break;
            }
            if (float.IsNaN(observedPlayStartDelay))
            {
                Fail("Recovered directors never entered normal player-loop playback.");
                yield break;
            }
            int distinctFrameHashes = records
                .Select(record => record.pngSha256)
                .Distinct(StringComparer.Ordinal)
                .Count();
            if (distinctFrameHashes < 2)
            {
                Fail(
                    "Presentation frames are visually invariant: " +
                    $"distinct PNG hashes={distinctFrameHashes}.");
                yield break;
            }

            var manifest = new CaptureManifest
            {
                verdict = "PASS_SOURCE_GATED_VISIBLE_PRESENTATION_CAPTURE",
                recoveredScaledPlayDelaySeconds = runtime.scaledPlayDelaySeconds,
                observedPlayerLoopStartDelaySeconds = observedPlayStartDelay,
                observedPlayerLoopStartDelayFrames = Mathf.RoundToInt(
                    observedPlayStartDelay * CaptureFps),
                sourceCameraStayedDisabled = sourceCameraStayedDisabled,
                presentationCullingMask = presentationCullingMask,
                presentationUseOcclusionCulling =
                    presentationUseOcclusionCulling,
                captureScopeLayer = SourceGachaLayer,
                captureScopeGameObjectCount = captureScopeGameObjectCount,
                everyCaptureScopeGameObjectLayerIsGacha =
                    EveryCaptureScopeGameObjectUsesGachaLayer(),
                presentationViewport =
                    $"{Format(presentationViewport.x)},{Format(presentationViewport.y)}," +
                    $"{Format(presentationViewport.width)},{Format(presentationViewport.height)}",
                presentationTargetDisplay = presentationTargetDisplay,
                presentationClearFlags = presentationClearFlags.ToString(),
                renderPipelineAsset =
                    GraphicsSettings.currentRenderPipeline != null
                        ? GraphicsSettings.currentRenderPipeline.GetType().FullName
                        : "null",
                renderPipelineInstance =
                    RenderPipelineManager.currentPipeline != null
                        ? RenderPipelineManager.currentPipeline.GetType().FullName
                        : "null",
                beginCameraRenderingCount = beginCameraRenderingCount,
                endCameraRenderingCount = endCameraRenderingCount,
                renderTargetSentinelOverwritten =
                    records.All(record => record.sentinelPixelCount == 0),
                everyFrameNonBlack =
                    records.All(record => record.nonBlackPixelCount >= 1024),
                canonicalFramesVisuallyDistinct =
                    distinctFrameHashes == records.Count,
                maximumSentinelPixelCount =
                    records.Max(record => record.sentinelPixelCount),
                minimumNonBlackPixelCount =
                    records.Min(record => record.nonBlackPixelCount),
                distinctPngHashCount = distinctFrameHashes,
                failClosedMaterialCount = finalCount,
                initialFailClosedCensusSha256 = initialFailClosedCensusSha256,
                finalFailClosedCensusSha256 = finalCensusSha256,
                frames = records.ToArray(),
            };
            string manifestJson = JsonUtility.ToJson(manifest, true) + Environment.NewLine;
            string manifestPath = Path.Combine(outputDirectory, "capture_manifest.json");
            File.WriteAllText(manifestPath, manifestJson, new UTF8Encoding(false));
            string manifestSha256 = ComputeFileSha256(manifestPath);
            File.WriteAllText(
                Path.Combine(outputDirectory, "capture_manifest.sha256"),
                manifestSha256 + "  capture_manifest.json" + Environment.NewLine,
                new UTF8Encoding(false));
            Debug.Log(
                "Zhuangfy gacha presentation capture PASS: " +
                $"frames={records.Count}, manifestSha256={manifestSha256}, " +
                $"output={outputDirectory}.");
            if (HasArgument(Environment.GetCommandLineArgs(), QuitArgument))
                Application.Quit(0);
        }

        private void LateUpdate()
        {
            if (!captureArmed)
                return;
            if (sourceCameraPlayback == null ||
                sourceCameraPlayback.sourceCamera == null ||
                !sourceCameraPlayback.keepSourceCameraDisabled ||
                sourceCameraPlayback.sourceCamera.enabled)
            {
                sourceCameraStayedDisabled = false;
                Fail("Exact source Camera was enabled or its fail-closed playback contract changed.");
                return;
            }

            Camera source = sourceCameraPlayback.sourceCamera;
            try
            {
                ValidatePresentationOutputContract();
            }
            catch (Exception exception)
            {
                Fail(exception.Message);
                return;
            }
            presentationCamera.transform.SetPositionAndRotation(
                source.transform.position,
                source.transform.rotation);
            presentationCamera.fieldOfView = source.fieldOfView;
            presentationCamera.targetTexture = captureTarget;
            presentationCamera.enabled = true;
            PrefillCaptureTarget();
            lastLateDirectorTime =
                runtime != null && runtime.director != null
                    ? runtime.director.time
                    : double.NaN;
            if (float.IsNaN(observedPlayStartDelay) &&
                runtime != null && runtime.director != null &&
                runtime.director.state == PlayState.Playing)
            {
                observedPlayStartDelay = Time.time - beginScaledTime;
            }
        }

        private FrameRecord CaptureFrame(
            int index,
            CanonicalSample sample,
            double nearestTimelineTime,
            double observedTimelineTime)
        {
            ValidateSceneContract();
            string census = BuildFailClosedCensus(out int failClosedCount);
            string censusSha = ComputeSha256(census);
            if (failClosedCount != initialFailClosedMaterialCount ||
                !string.Equals(census, initialFailClosedCensus, StringComparison.Ordinal))
            {
                throw new InvalidOperationException(
                    "Fail-closed material identity changed before PNG capture.");
            }

            if (captureTarget == null || !captureTarget.IsCreated())
                throw new InvalidOperationException("Presentation RenderTexture is unavailable.");
            RenderTexture previousTarget = RenderTexture.active;
            RenderTexture.active = captureTarget;
            var screenshot = new Texture2D(
                CaptureWidth,
                CaptureHeight,
                TextureFormat.RGBA32,
                false,
                false);
            screenshot.ReadPixels(
                new Rect(0, 0, CaptureWidth, CaptureHeight),
                0,
                0,
                false);
            screenshot.Apply(false, false);
            RenderTexture.active = previousTarget;
            if (screenshot.width != CaptureWidth ||
                screenshot.height != CaptureHeight)
            {
                int width = screenshot.width;
                int height = screenshot.height;
                Destroy(screenshot);
                throw new InvalidOperationException(
                    $"Screenshot size is {width}x{height}; " +
                    $"required {CaptureWidth}x{CaptureHeight}.");
            }
            Color32[] pixels = screenshot.GetPixels32();
            int nonBlackPixels = 0;
            int sentinelPixels = 0;
            int maximumRgbChannel = 0;
            double lumaTotal = 0.0;
            foreach (Color32 pixel in pixels)
            {
                int maximum = Math.Max(pixel.r, Math.Max(pixel.g, pixel.b));
                maximumRgbChannel = Math.Max(maximumRgbChannel, maximum);
                if (maximum > 2)
                    nonBlackPixels++;
                if (Math.Abs(pixel.r - 239) <= 1 &&
                    Math.Abs(pixel.g - 17) <= 1 &&
                    Math.Abs(pixel.b - 157) <= 1)
                {
                    sentinelPixels++;
                }
                lumaTotal +=
                    0.2126 * pixel.r +
                    0.7152 * pixel.g +
                    0.0722 * pixel.b;
            }
            if (nonBlackPixels < 1024 || maximumRgbChannel <= 8)
            {
                Destroy(screenshot);
                throw new InvalidOperationException(
                    "Captured RenderTexture is effectively black: " +
                    $"nonBlackPixels={nonBlackPixels}, maxRgb={maximumRgbChannel}. " +
                    BuildCameraDiagnostic());
            }
            if (RenderPipelineManager.currentPipeline == null ||
                sentinelPixels > pixels.Length * 0.99f)
            {
                Destroy(screenshot);
                throw new InvalidOperationException(
                    "Presentation Camera/target render handoff failed: " +
                    $"sentinelPixels={sentinelPixels}/{pixels.Length}. " +
                    BuildCameraDiagnostic());
            }
            byte[] png = screenshot.EncodeToPNG();
            Destroy(screenshot);
            if (png == null || png.Length == 0)
                throw new InvalidOperationException("PNG encoder returned no bytes.");

            string fileName =
                index.ToString("D2", CultureInfo.InvariantCulture) + "_" +
                sample.label + "_" +
                nearestTimelineTime.ToString("000.00", CultureInfo.InvariantCulture)
                    .Replace('.', '_') +
                ".png";
            string path = Path.Combine(outputDirectory, fileName);
            File.WriteAllBytes(path, png);

            ParticleSystem[] particleSystems =
                captureScopeRoot.GetComponentsInChildren<ParticleSystem>(true);
            Renderer[] renderers =
                captureScopeRoot.GetComponentsInChildren<Renderer>(true);
            return new FrameRecord
            {
                index = index,
                label = sample.label,
                authoredSourceTimeSeconds = sample.authoredTime,
                nearest25FpsTimelineTimeSeconds = nearestTimelineTime,
                capturedTimelineTimeSeconds = observedTimelineTime,
                authoredToCapturedErrorSeconds =
                    observedTimelineTime - sample.authoredTime,
                unityFrameCount = Time.frameCount,
                png = fileName,
                pngBytes = png.LongLength,
                pngSha256 = ComputeSha256(png),
                nonBlackPixelCount = nonBlackPixels,
                nonBlackPixelFraction =
                    (float)nonBlackPixels / pixels.Length,
                meanRgbLuma =
                    (float)(lumaTotal / (pixels.Length * 255.0)),
                maximumRgbChannel = maximumRgbChannel,
                sentinelPixelCount = sentinelPixels,
                cameraVerticalFovDegrees = presentationCamera.fieldOfView,
                playingParticleSystems = particleSystems.Count(system =>
                    system != null && system.isPlaying),
                aliveParticleCount = particleSystems.Sum(system =>
                    system != null ? system.particleCount : 0),
                activeRenderers = renderers.Count(renderer =>
                    renderer != null && renderer.enabled &&
                    renderer.gameObject.activeInHierarchy),
                activeAddedMaterialRecords = runtime.ActiveAddedMaterialRecordCount,
                appliedAddedMaterialRecords = runtime.AppliedAddedMaterialRecordCount,
                activeDissolveReplacementMaterials =
                    runtime.ActiveDissolveReplacementMaterialCount,
                failClosedCensusSha256 = censusSha,
                particleSystems =
                    index >= 6 && index <= 8
                        ? BuildParticleSystemRecords()
                        : Array.Empty<ParticleSystemRecord>(),
            };
        }

        private ParticleSystemRecord[] BuildParticleSystemRecords()
        {
            var records = new List<ParticleSystemRecord>();
            EndfieldRecoveredParticleEffectSource[] effects =
                captureScopeRoot.GetComponentsInChildren<
                    EndfieldRecoveredParticleEffectSource>(true);
            foreach (EndfieldRecoveredParticleEffectSource effect in effects
                .OrderBy(value => value.effectRoot, StringComparer.Ordinal))
            {
                if (effect == null || effect.particleNodes == null)
                    continue;
                foreach (EndfieldRecoveredParticleNodeSource node in
                    effect.particleNodes.OrderBy(value =>
                        value.particleSystemPathId))
                {
                    EndfieldRecoveredParticleHierarchyNodeSource hierarchy =
                        effect.hierarchyNodes.SingleOrDefault(value =>
                            value.transformPathId == node.transformPathId);
                    Transform target =
                        hierarchy == null
                            ? null
                            : hierarchy.generatedTransform;
                    ParticleSystem system =
                        target == null
                            ? null
                            : target.GetComponent<ParticleSystem>();
                    ParticleSystemRenderer renderer =
                        target == null
                            ? null
                            : target.GetComponent<ParticleSystemRenderer>();
                    if (system == null)
                        continue;

                    int particleCount = system.particleCount;
                    var sourceParticles =
                        new ParticleSystem.Particle[particleCount];
                    int copied = system.GetParticles(sourceParticles);
                    var custom1 = new List<Vector4>(particleCount);
                    int customCount = system.GetCustomParticleData(
                        custom1,
                        ParticleSystemCustomData.Custom1);
                    ParticleSystem.MainModule main = system.main;
                    var particles = new ParticleRecord[copied];
                    for (int index = 0; index < copied; index++)
                    {
                        ParticleSystem.Particle particle =
                            sourceParticles[index];
                        Vector3 position = particle.position;
                        Vector3 worldPosition;
                        if (main.simulationSpace ==
                            ParticleSystemSimulationSpace.World)
                        {
                            worldPosition = position;
                        }
                        else if (main.simulationSpace ==
                            ParticleSystemSimulationSpace.Custom &&
                            main.customSimulationSpace != null)
                        {
                            worldPosition =
                                main.customSimulationSpace.TransformPoint(
                                    position);
                        }
                        else
                        {
                            worldPosition =
                                system.transform.TransformPoint(position);
                        }
                        particles[index] = new ParticleRecord
                        {
                            index = index,
                            randomSeed = particle.randomSeed,
                            position = position,
                            worldPosition = worldPosition,
                            velocity = particle.velocity,
                            currentSize =
                                particle.GetCurrentSize3D(system),
                            currentColor =
                                particle.GetCurrentColor(system),
                            remainingLifetime =
                                particle.remainingLifetime,
                            startLifetime = particle.startLifetime,
                            rotation = particle.rotation,
                            angularVelocity =
                                particle.angularVelocity,
                            custom1 =
                                index < customCount
                                    ? custom1[index]
                                    : Vector4.zero,
                        };
                    }

                    var streams = new List<ParticleSystemVertexStream>();
                    if (renderer != null)
                        renderer.GetActiveVertexStreams(streams);
                    Material[] materials =
                        renderer == null
                            ? Array.Empty<Material>()
                            : renderer.sharedMaterials;
                    records.Add(new ParticleSystemRecord
                    {
                        effectRoot = effect.effectRoot,
                        hierarchy = node.hierarchy,
                        particleSystemPathId =
                            node.particleSystemPathId,
                        particleRendererPathId =
                            node.particleRendererPathId,
                        materialPathIds =
                            node.materialPathIds == null
                                ? Array.Empty<long>()
                                : (long[])node.materialPathIds.Clone(),
                        materialNames = materials.Select(value =>
                            value == null ? string.Empty : value.name)
                            .ToArray(),
                        shaderNames = materials.Select(value =>
                            value == null || value.shader == null
                                ? string.Empty
                                : value.shader.name).ToArray(),
                        activeVertexStreams = streams.Select(value =>
                            value.ToString()).ToArray(),
                        gameObjectActive =
                            system.gameObject.activeInHierarchy,
                        rendererEnabled =
                            renderer != null && renderer.enabled,
                        isPlaying = system.isPlaying,
                        isPaused = system.isPaused,
                        isStopped = system.isStopped,
                        simulationTime = system.time,
                        particleCount = copied,
                        renderMode =
                            renderer == null
                                ? -1
                                : (int)renderer.renderMode,
                        renderAlignment =
                            renderer == null
                                ? -1
                                : (int)renderer.alignment,
                        rendererBoundsCenter =
                            renderer == null
                                ? Vector3.zero
                                : renderer.bounds.center,
                        rendererBoundsExtents =
                            renderer == null
                                ? Vector3.zero
                                : renderer.bounds.extents,
                        particles = particles,
                    });
                }
            }
            return records.ToArray();
        }

        private void ValidateSceneContract()
        {
            if (runtime == null || runtime.director == null ||
                runtime.actorCameraDirector == null ||
                sourceCameraPlayback == null ||
                sourceCameraPlayback.sourceCamera == null ||
                sourceCameraPlayback.sourceClip == null ||
                !sourceCameraPlayback.sourceClip.IsSourceClosed ||
                !sourceCameraPlayback.keepSourceCameraDisabled ||
                sourceCameraPlayback.sourceCamera.enabled ||
                presentationCamera == null ||
                ReferenceEquals(presentationCamera, sourceCameraPlayback.sourceCamera) ||
                captureScopeRoot == null)
            {
                throw new InvalidOperationException(
                    "Generated Zhuangfy capture scene does not satisfy its source-gated contract.");
            }
            if (Mathf.Abs(runtime.scaledPlayDelaySeconds - 0.25f) > 1.0e-6f)
                throw new InvalidOperationException("Recovered scaled start delay changed.");
            if (runtime.director.timeUpdateMode != DirectorUpdateMode.GameTime ||
                runtime.actorCameraDirector.timeUpdateMode != DirectorUpdateMode.GameTime)
            {
                throw new InvalidOperationException(
                    "Capture requires normal player-loop GameTime directors.");
            }
            if (!float.IsNaN(observedPlayStartDelay) &&
                observedPlayStartDelay + 1.0e-6f < runtime.scaledPlayDelaySeconds)
            {
                throw new InvalidOperationException(
                    "Recovered director started before its scaled delay deadline.");
            }
        }

        private void ValidatePresentationOutputContract()
        {
            if (presentationCullingMask != SourceGachaCullingMask ||
                presentationCamera.cullingMask != SourceGachaCullingMask ||
                presentationUseOcclusionCulling ||
                presentationCamera.useOcclusionCulling ||
                !EveryCaptureScopeGameObjectUsesGachaLayer() ||
                presentationCamera.rect != presentationViewport ||
                presentationCamera.targetDisplay != presentationTargetDisplay ||
                presentationCamera.clearFlags != presentationClearFlags ||
                presentationCamera.allowHDR != presentationAllowHdr ||
                presentationCamera.allowMSAA != presentationAllowMsaa)
            {
                throw new InvalidOperationException(
                    "Configured HG presentation Camera render/output fields changed during capture.");
            }
        }

        private bool EveryCaptureScopeGameObjectUsesGachaLayer()
        {
            if (captureScopeRoot == null)
                return false;
            Transform[] transforms =
                captureScopeRoot.GetComponentsInChildren<Transform>(true);
            if (transforms.Length == 0 ||
                (captureScopeGameObjectCount != 0 &&
                 transforms.Length != captureScopeGameObjectCount))
            {
                return false;
            }
            foreach (Transform item in transforms)
            {
                if (item.gameObject.layer != SourceGachaLayer)
                    return false;
            }
            return true;
        }

        private string BuildCameraDiagnostic()
        {
            Renderer[] renderers =
                captureScopeRoot.GetComponentsInChildren<Renderer>(true);
            Plane[] planes = GeometryUtility.CalculateFrustumPlanes(
                presentationCamera);
            int enabledRendererCount = 0;
            int frustumRendererCount = 0;
            bool hasBounds = false;
            Bounds combinedBounds = default;
            foreach (Renderer renderer in renderers)
            {
                if (renderer == null || !renderer.enabled ||
                    !renderer.gameObject.activeInHierarchy)
                {
                    continue;
                }
                enabledRendererCount++;
                Bounds bounds = renderer.bounds;
                if (!hasBounds)
                {
                    combinedBounds = bounds;
                    hasBounds = true;
                }
                else
                {
                    combinedBounds.Encapsulate(bounds);
                }
                if (GeometryUtility.TestPlanesAABB(planes, bounds))
                    frustumRendererCount++;
            }
            Vector3 viewportCenter = hasBounds
                ? presentationCamera.WorldToViewportPoint(combinedBounds.center)
                : new Vector3(float.NaN, float.NaN, float.NaN);
            string cameraOrder = string.Join(
                ";",
                Camera.allCameras
                    .OrderBy(camera => camera.depth)
                    .Select(camera =>
                        $"{camera.name}:depth={Format(camera.depth)}:" +
                        $"enabled={camera.enabled}:target=" +
                        $"{(camera.targetTexture != null ? camera.targetTexture.name : "screen")}"));
            return
                $"camera='{presentationCamera.name}', tag='{presentationCamera.tag}', " +
                $"scene='{presentationCamera.gameObject.scene.name}', " +
                $"position={presentationCamera.transform.position}, " +
                $"rotation={presentationCamera.transform.rotation.eulerAngles}, " +
                $"fov={Format(presentationCamera.fieldOfView)}, " +
                $"depth={Format(presentationCamera.depth)}, " +
                $"cullingMask=0x{presentationCamera.cullingMask:X8}, " +
                $"useOcclusionCulling={presentationCamera.useOcclusionCulling}, " +
                $"captureScopeLayer={SourceGachaLayer}, " +
                $"captureScopeLayersInvariant={EveryCaptureScopeGameObjectUsesGachaLayer()}, " +
                $"rect={presentationCamera.rect}, display={presentationCamera.targetDisplay}, " +
                $"clear={presentationCamera.clearFlags}, " +
                $"target={captureTarget.graphicsFormat}/sRGB={captureTarget.sRGB}/" +
                $"{captureTarget.width}x{captureTarget.height}, " +
                $"beginCameraRendering={beginCameraRenderingCount}@" +
                $"{lastBeginCameraRenderingFrame}, " +
                $"endCameraRendering={endCameraRenderingCount}@" +
                $"{lastEndCameraRenderingFrame}, frame={Time.frameCount}, " +
                $"currentRenderPipelineAsset=" +
                $"{(GraphicsSettings.currentRenderPipeline != null ? GraphicsSettings.currentRenderPipeline.GetType().FullName : "null")}, " +
                $"currentRenderPipelineInstance=" +
                $"{(RenderPipelineManager.currentPipeline != null ? RenderPipelineManager.currentPipeline.GetType().FullName : "null")}, " +
                $"enabledRenderers={enabledRendererCount}, " +
                $"frustumRenderers={frustumRendererCount}, " +
                $"actorBounds={(hasBounds ? combinedBounds.ToString() : "none")}, " +
                $"actorCenterViewport={viewportCenter}, cameraOrder=[{cameraOrder}]";
        }

        private void PrefillCaptureTarget()
        {
            RenderTexture previous = RenderTexture.active;
            RenderTexture.active = captureTarget;
            GL.Clear(false, true, SentinelColor);
            RenderTexture.active = previous;
        }

        private void OnBeginCameraRendering(
            ScriptableRenderContext context,
            Camera camera)
        {
            if (camera != presentationCamera)
                return;
            beginCameraRenderingCount++;
            lastBeginCameraRenderingFrame = Time.frameCount;
        }

        private void OnEndCameraRendering(
            ScriptableRenderContext context,
            Camera camera)
        {
            if (camera != presentationCamera)
                return;
            endCameraRenderingCount++;
            lastEndCameraRenderingFrame = Time.frameCount;
        }

        private string BuildFailClosedCensus(out int count)
        {
            var records = new List<string>();
            Renderer[] renderers =
                captureScopeRoot.GetComponentsInChildren<Renderer>(true);
            foreach (Renderer renderer in renderers)
            {
                if (renderer == null)
                    continue;
                Material[] materials = renderer.sharedMaterials;
                for (int slot = 0; slot < materials.Length; slot++)
                {
                    Material material = materials[slot];
                    if (material == null || material.shader == null ||
                        !string.Equals(
                            material.shader.name,
                            FailClosedShader,
                            StringComparison.Ordinal))
                    {
                        continue;
                    }
                    records.Add(
                        GetPath(captureScopeRoot, renderer.transform) + "|" +
                        slot.ToString(CultureInfo.InvariantCulture) + "|" +
                        material.name + "|" + material.shader.name);
                }
            }
            records.Sort(StringComparer.Ordinal);
            count = records.Count;
            return string.Join("\n", records);
        }

        private static string GetPath(Transform root, Transform target)
        {
            var names = new List<string>();
            Transform current = target;
            while (current != null)
            {
                names.Add(current.name);
                if (current == root)
                    break;
                current = current.parent;
            }
            names.Reverse();
            return string.Join("/", names);
        }

        private static double QuantizeToPlayerTimeline(double authoredTime)
        {
            if (Math.Abs(authoredTime - TimelineDuration) <= 1.0e-9)
                return TimelineDuration;
            return Math.Round(
                authoredTime * CaptureFps,
                MidpointRounding.AwayFromZero) / CaptureFps;
        }

        private static void RequireDirectoryHasNoCaptureArtifacts(string directory)
        {
            string[] names =
            {
                "capture_manifest.json",
                "capture_manifest.sha256",
                "capture_failure.txt",
            };
            foreach (string name in names)
            {
                if (File.Exists(Path.Combine(directory, name)))
                {
                    throw new IOException(
                        $"Capture output already exists; use a fresh directory: {directory}");
                }
            }
        }

        private void Fail(string message)
        {
            if (!enabled)
                return;
            enabled = false;
            captureArmed = false;
            runtime?.EndRecoveredEffect();
            Debug.LogError("Zhuangfy gacha presentation capture FAIL: " + message);
            try
            {
                if (!string.IsNullOrWhiteSpace(outputDirectory))
                {
                    Directory.CreateDirectory(outputDirectory);
                    File.WriteAllText(
                        Path.Combine(outputDirectory, "capture_failure.txt"),
                        message + Environment.NewLine,
                        new UTF8Encoding(false));
                }
            }
            catch (Exception exception)
            {
                Debug.LogError("Could not write capture failure marker: " + exception);
            }
            if (HasArgument(Environment.GetCommandLineArgs(), QuitArgument))
                Application.Quit(2);
        }

        private void OnDestroy()
        {
            runtime?.EndRecoveredEffect();
            RenderPipelineManager.beginCameraRendering -=
                OnBeginCameraRendering;
            RenderPipelineManager.endCameraRendering -=
                OnEndCameraRendering;
            if (presentationCamera != null &&
                presentationCamera.targetTexture == captureTarget)
            {
                presentationCamera.targetTexture = null;
            }
            if (captureTarget != null)
            {
                captureTarget.Release();
                Destroy(captureTarget);
                captureTarget = null;
            }
        }

        private static string ComputeSha256(string value)
        {
            return ComputeSha256(Encoding.UTF8.GetBytes(value ?? string.Empty));
        }

        private static string ComputeFileSha256(string path)
        {
            using (FileStream stream = File.OpenRead(path))
            using (SHA256 sha256 = SHA256.Create())
                return ToHex(sha256.ComputeHash(stream));
        }

        private static string ComputeSha256(byte[] bytes)
        {
            using (SHA256 sha256 = SHA256.Create())
                return ToHex(sha256.ComputeHash(bytes));
        }

        private static string ToHex(byte[] bytes)
        {
            var builder = new StringBuilder(bytes.Length * 2);
            foreach (byte value in bytes)
                builder.Append(value.ToString("x2", CultureInfo.InvariantCulture));
            return builder.ToString();
        }

        private static string ReadArgument(string[] arguments, string name)
        {
            string prefix = name + "=";
            for (int index = 0; index < arguments.Length; index++)
            {
                string argument = arguments[index];
                if (argument.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                    return argument.Substring(prefix.Length);
                if (string.Equals(argument, name, StringComparison.OrdinalIgnoreCase) &&
                    index + 1 < arguments.Length)
                {
                    return arguments[index + 1];
                }
            }
            return null;
        }

        private static bool HasArgument(string[] arguments, string name)
        {
            return arguments.Any(argument =>
                string.Equals(argument, name, StringComparison.OrdinalIgnoreCase));
        }

        private static string Format(double value)
        {
            return value.ToString("0.#########", CultureInfo.InvariantCulture);
        }
    }
}
