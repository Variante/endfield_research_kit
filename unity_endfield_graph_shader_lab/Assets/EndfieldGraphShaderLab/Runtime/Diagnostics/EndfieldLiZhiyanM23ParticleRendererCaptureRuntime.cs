using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using Process = System.Diagnostics.Process;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Runtime-only source ParticleSystemRenderer probe for the Li Zhiyan M23
    /// source prefab.  This deliberately uses the real renderer in a normal
    /// standalone player.  It does not call BakeMesh, add a MeshRenderer proxy,
    /// issue plugin events, or replace a D3D11 context.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class EndfieldLiZhiyanM23ParticleRendererCaptureRuntime : MonoBehaviour
    {
        public const string ActivationArgument = "-endfield-m23-particle-renderer-capture";
        public const string OutputArgument = "-endfield-m23-particle-renderer-output";
        public const string ModeArgument = "-endfield-m23-particle-renderer-mode";
        public const string QuitArgument = "-endfield-m23-particle-renderer-quit";
        public const string ForegroundWindowArgument =
            "-endfield-m23-particle-renderer-foreground-window";

        private const string ExpectedSchema = "endfield.lizhiyan-overview-peak-particle-effects.v1";
        private const string ExpectedRoot = "P_fxui_lizhiyan_overview_start_04_2";
        private const int RetailPts = 40000;
        private const int RetailClockOriginPts = 37967;
        private const int RetailClockUnitsPerSecond = 1000;
        private const float ExpectedEffectDelay = 1.833333f;
        private const float TargetLocalSeconds =
            (RetailPts - RetailClockOriginPts) / (float)RetailClockUnitsPerSecond -
            ExpectedEffectDelay;
        private const int DefaultFramesAfterSetup = 1;
        private const int MaximumFramesAfterSetup = 30;

        private static readonly int[] ExpectedStreams = { 0, 1, 3, 4, 5, 34 };

        [Serializable]
        public sealed class RendererIdentity
        {
            public string hierarchy;
            public long particleSystemPathId;
            public long particleRendererPathId;
            public long meshPathId;
            public long materialPathId;
        }

        [Serializable]
        public sealed class SourceFieldParticleSnapshot
        {
            public int index;
            public Vector3 position;
            public Vector3 velocity;
            public Vector3 animatedVelocity;
            public Vector3 axisOfRotation;
            public float rotation;
            public Vector3 rotation3D;
            public float angularVelocity;
            public Vector3 angularVelocity3D;
            public float startSize;
            public Vector3 startSize3D;
            public Color startColor;
            public float remainingLifetime;
            public float startLifetime;
            public uint randomSeed;
            public Vector4 custom1;
        }

        [Serializable]
        public sealed class CaptureReport
        {
            public string schema = "endfield.lizhiyan-m23-particle-renderer-capture.v1";
            public string status;
            public string failure;
            public string mode;
            public string unityVersion;
            public string graphicsDeviceType;
            public bool applicationIsBatchMode;
            public bool applicationRunsInBackground;
            public bool noBakeMeshContract;
            public bool noProxyContract;
            public bool sourceRendererSubmissionPath;
            public bool exactIdentityClosed;
            public bool deterministicResetClosed;
            public uint serializedRandomSeed;
            public uint randomSeedAfterReset;
            public bool fixedTimeStep;
            public string simulationContract;
            public string prefab;
            public string effectRoot;
            public int retailPts;
            public int retailClockOriginPts;
            public float sourceEffectDelay;
            public float targetLocalSeconds;
            public int frameCountAtCapture;
            public int framesAfterSetup;
            public bool targetGameObjectActive;
            public bool targetRendererEnabled;
            public bool targetRendererVisible;
            public string serializedSortingFudge;
            public string sortingFudgeAtCapture;
            public bool diagnosticSortingFudgeZeroOverride;
            public bool serializedGpuInstancing;
            public bool gpuInstancingAtCapture;
            public bool diagnosticGpuInstancingOffOverride;
            public bool rendererAllowsDynamicOcclusion;
            public bool cameraUsesOcclusionCulling;
            public bool diagnosticRendererOcclusionOffOverride;
            public bool diagnosticCameraOcclusionOffOverride;
            public bool diagnosticBillboardRenderModeOverride;
            public bool diagnosticCompatibilityMaterialOverride;
            public bool diagnosticBasicVertexStreamsOverride;
            public bool diagnosticNaturalPlaybackOverride;
            public bool diagnosticDefaultLayerOverride;
            public Vector3 targetBoundsCenter;
            public Vector3 targetBoundsExtents;
            public Vector3 captureCameraPosition;
            public float captureCameraOrthographicSize;
            public int captureCameraCullingMask;
            public int targetLayer;
            public bool publicFrustumIntersectsBounds;
            public bool materialShaderSupported;
            public int materialPassCount;
            public int materialRenderQueue;
            public string materialName;
            public string materialShaderName;
            public string materialMrtAdmissionTag;
            public string currentRenderPipelineType;
            public string pipelineBeforeOverride;
            public bool builtinPipelineOverride;
            public bool foregroundWindowRequested;
            public bool foregroundWindowPlatformSupported;
            public long foregroundWindowHandle;
            public bool foregroundWindowHandleNonZero;
            public bool foregroundWindowIsWindow;
            public bool foregroundWindowShowWindowCalled;
            public bool foregroundWindowShowWindowResult;
            public bool foregroundWindowSetForegroundWindowCalled;
            public bool foregroundWindowSetForegroundWindowResult;
            public string foregroundWindowFailure;
            public bool explicitCameraRenderMode;
            public bool explicitCameraRenderRequested;
            public bool explicitCameraRenderExecuted;
            public int explicitCameraRenderCallCount;
            public string explicitCameraRenderFailure;
            public bool directCameraMainGameObjectActive;
            public bool directCameraMainEnabled;
            public bool directCameraMainActiveAndEnabled;
            public int directCameraMainPixelWidth;
            public int directCameraMainPixelHeight;
            public int directCameraMainCullingMask;
            public bool directCameraMainHasTargetTexture;
            public int directCameraMainAllCamerasCount;
            public bool recoveredSceneMVRequested;
            public string recoveredSceneMVRequestFailure;
            public bool recoveredSceneMVDescriptorCreated;
            public bool recoveredAfterPostExecuted;
            public int cameraOnPreCullCount;
            public int cameraOnPreRenderCount;
            public int cameraOnPostRenderCount;
            public int beginCameraRenderingCount;
            public int endCameraRenderingCount;
            public int lastCameraCallbackFrame;
            public string lastCameraCallbackPhase;
            public string lastCameraCallbackName;
            public int lastCameraCallbackInstanceId;
            public string lastCameraCallbackScene;
            public bool lastCameraCallbackGameObjectActive;
            public bool lastCameraCallbackEnabled;
            public bool lastCameraCallbackActiveAndEnabled;
            public int lastCameraCallbackPixelWidth;
            public int lastCameraCallbackPixelHeight;
            public int lastCameraCallbackCullingMask;
            public bool lastCameraCallbackHasTargetTexture;
            public int lastCameraCallbackAllCamerasCount;
            public bool targetRendererMeshMode;
            public bool targetUsesDiagnosticMaterial;
            public bool targetHasMeshFilter;
            public bool targetHasMeshRenderer;
            public bool sourceManualParticleOverride;
            public string sourceManualParticleComponentIdentity;
            public int sourceManualParticleCount;
            public Vector3 sourceManualParticlePosition;
            public Color sourceManualParticleStartColor;
            public float sourceManualParticleStartLifetime;
            public float sourceManualParticleRemainingLifetime;
            public bool sourceManualParticleAtLocalOrigin;
            public bool sourceManualParticleWhite;
            public bool sourceManualParticleMeshExactTargetMesh;
            public string sourceManualParticleMeshName;
            public string sourceManualParticleRenderMode;
            public string sourceManualParticleMaterialName;
            public string sourceManualParticleMaterialShaderName;
            public bool sourceManualParticleVisible;
            public bool sourceManualParticleAdmission;
            public string sourceManualParticleContract;
            public string sourceFieldFamily;
            public bool sourceFieldOriginalCaptured;
            public bool sourceFieldAfterCaptured;
            public bool sourceFieldRequestedFamilyChanged;
            public bool sourceFieldChangedOnlyRequestedFamily;
            public int sourceFieldOriginalParticleCount;
            public int sourceFieldAfterParticleCount;
            public SourceFieldParticleSnapshot[] sourceFieldBefore;
            public SourceFieldParticleSnapshot[] sourceFieldAfter;
            public Vector4[] sourceFieldCustom1Before;
            public Vector4[] sourceFieldCustom1After;
            public bool sourceFieldAdmission;
            public string sourceFieldContract;
            public bool sourceRepublishIdenticalMode;
            public bool sourceRepublishOriginalCaptured;
            public bool sourceRepublishAfterCaptured;
            public bool sourceRepublishParticleValuesEqual;
            public bool sourceRepublishCustom1Equal;
            public bool sourceRepublishNoFieldChanges;
            public bool sourceRepublishAdmission;
            public string sourceRepublishContract;
            public int particleCount;
            public int[] activeVertexStreamIds;
            public string[] activeVertexStreams;
            public bool controlCreated;
            public bool controlSerializedPreExisting;
            public bool controlRuntimeCreated;
            public bool controlGameObjectActive;
            public bool controlRendererEnabled;
            public bool controlRendererVisible;
            public bool controlRendererDisabledOverride;
            public bool controlMeshModeOverride;
            public bool controlSharedMeshExactTargetMesh;
            public string controlRenderMode;
            public string controlMeshName;
            public string controlTargetMeshName;
            public int controlMeshInstanceId;
            public int controlTargetMeshInstanceId;
            public int controlParticleCount;
            public Vector3 controlBoundsCenter;
            public Vector3 controlBoundsExtents;
            public bool controlBoundsFinite;
            public bool controlFrustumIntersectsBounds;
            public bool controlMaterialShaderSupported;
            public int controlMaterialPassCount;
            public int controlMaterialRenderQueue;
            public string controlMaterialName;
            public string controlMaterialShaderName;
            public string controlMaterialPurpose;
            public bool controlHasMeshFilter;
            public bool controlHasMeshRenderer;
            public bool controlAdmission;
            public string controlContract;
            public bool sentinelSerializedPreExisting;
            public bool sentinelEnabled;
            public bool sentinelVisible;
            public bool sentinelDisabledOverride;
            public Vector3 sentinelBoundsCenter;
            public Vector3 sentinelBoundsExtents;
            public bool sentinelBoundsFinite;
            public bool sentinelFrustumIntersectsBounds;
            public bool sentinelMaterialShaderSupported;
            public int sentinelMaterialPassCount;
            public int sentinelMaterialRenderQueue;
            public string sentinelMaterialName;
            public string sentinelMaterialShaderName;
            public string sentinelMeshName;
            public string sentinelIdentity;
            public string sentinelContract;
            public bool sentinelAdmission;
            public RendererIdentity identity;
            public string negativeControlExpectation;
        }

        private readonly Dictionary<string, ParticleSystemRenderer> renderersByHierarchy =
            new Dictionary<string, ParticleSystemRenderer>(StringComparer.Ordinal);
        private readonly Dictionary<string, ParticleSystem> systemsByHierarchy =
            new Dictionary<string, ParticleSystem>(StringComparer.Ordinal);

        private string outputPath;
        private string mode;
        private bool quitAfterCapture;
        private int framesAfterSetup;
        private float simulationSeconds;
        private RendererIdentity targetIdentity;
        private ParticleSystem targetSystem;
        private ParticleSystemRenderer targetRenderer;
        private Mesh sourceMeshBeforeOverride;
        private ParticleSystem.Particle sourceManualParticle;
        private bool sourceManualParticlePublished;
        private ParticleSystem.Particle[] sourceFieldOriginalParticles;
        private List<Vector4> sourceFieldOriginalCustom1;
        private int sourceFieldOriginalParticleCount;
        private bool sourceFieldOriginalCaptured;
        private SourceFieldFamily sourceFieldFamily;
        private const int MaximumSourceFieldParticles = 64;
        private EndfieldRecoveredParticleEffectSource sourceMarker;
        private bool setupPassed;
        private bool reportWritten;
        private uint serializedRandomSeed;
        private float serializedSortingFudge;
        private bool serializedGpuInstancing;
        private GameObject controlObject;
        private ParticleSystem controlSystem;
        private ParticleSystemRenderer controlRenderer;
        [SerializeField] private Material compatibilityMaterial;
        [SerializeField] private Material builtinCompatibilityMaterial;
        [SerializeField] private ParticleSystem serializedControlSystem;
        [SerializeField] private ParticleSystemRenderer serializedControlRenderer;
        [SerializeField] private MeshFilter serializedSentinelFilter;
        [SerializeField] private MeshRenderer serializedSentinelRenderer;
        private string pipelineBeforeOverride;
        private CaptureMode controlCaptureMode;
        private bool controlWasSerialized;
        private bool lifecycleCallbacksSubscribed;
        private int cameraOnPreCullCount;
        private int cameraOnPreRenderCount;
        private int cameraOnPostRenderCount;
        private int beginCameraRenderingCount;
        private int endCameraRenderingCount;
        private int lastCameraCallbackFrame;
        private string lastCameraCallbackPhase = string.Empty;
        private string lastCameraCallbackName = string.Empty;
        private int lastCameraCallbackInstanceId;
        private string lastCameraCallbackScene = string.Empty;
        private bool lastCameraCallbackGameObjectActive;
        private bool lastCameraCallbackEnabled;
        private bool lastCameraCallbackActiveAndEnabled;
        private int lastCameraCallbackPixelWidth;
        private int lastCameraCallbackPixelHeight;
        private int lastCameraCallbackCullingMask;
        private bool lastCameraCallbackHasTargetTexture;
        private int lastCameraCallbackAllCamerasCount;
        private bool explicitCameraRenderRequested;
        private bool explicitCameraRenderExecuted;
        private int explicitCameraRenderCallCount;
        private string explicitCameraRenderFailure = string.Empty;
        private bool foregroundWindowRequested;
        private bool foregroundWindowPlatformSupported;
        private long foregroundWindowHandle;
        private bool foregroundWindowHandleNonZero;
        private bool foregroundWindowIsWindow;
        private bool foregroundWindowShowWindowCalled;
        private bool foregroundWindowShowWindowResult;
        private bool foregroundWindowSetForegroundWindowCalled;
        private bool foregroundWindowSetForegroundWindowResult;
        private string foregroundWindowFailure = string.Empty;
        private Camera explicitRenderCamera;

#if UNITY_STANDALONE_WIN
        private const int ShowWindowRestore = 9;

        [DllImport("user32.dll", SetLastError = true)]
        private static extern bool IsWindow(IntPtr handle);

        [DllImport("user32.dll")]
        private static extern IntPtr GetActiveWindow();

        [DllImport("user32.dll")]
        private static extern bool ShowWindow(IntPtr handle, int command);

        [DllImport("user32.dll", SetLastError = true)]
        private static extern bool SetForegroundWindow(IntPtr handle);
#endif

        private const string ControlObjectName =
            "M23ParticleRendererAdmissionControl";

        private enum CaptureMode
        {
            Positive,
            TargetDisabled,
            PreDelay,
            EmptyTarget,
            SortingFudgeZero,
            GpuInstancingOff,
            RendererOcclusionOff,
            CameraOcclusionOff,
            BillboardRenderMode,
            CompatibilityMaterial,
            BasicVertexStreams,
            NaturalPlayback,
            DefaultLayer,
            BuiltinPipeline,
            ControlDisabled,
            SerializedControl,
            SerializedControlDisabled,
            SentinelEnabled,
            SentinelDisabled,
            ExplicitCameraRender,
            MeshControl,
            SourceManualParticle,
            SourceFieldLifetime,
            SourceFieldSize,
            SourceFieldColor,
            SourceFieldRotation,
            SourceFieldVelocity,
            SourceFieldCustom1,
            SourceRepublishIdentical,
        }

        private enum SourceFieldFamily
        {
            None,
            Lifetime,
            Size,
            Color,
            Rotation,
            Velocity,
            Custom1,
        }

        public void ConfigureCompatibilityMaterial(Material material)
        {
            compatibilityMaterial = material;
        }

        public void ConfigureBuiltinCompatibilityMaterial(Material material)
        {
            builtinCompatibilityMaterial = material;
        }

        public void ConfigureSerializedControl(
            ParticleSystem system, ParticleSystemRenderer renderer)
        {
            serializedControlSystem = system;
            serializedControlRenderer = renderer;
        }

        public void ConfigureSerializedSentinel(
            MeshFilter filter, MeshRenderer renderer)
        {
            serializedSentinelFilter = filter;
            serializedSentinelRenderer = renderer;
        }

        private void Awake()
        {
            sourceMarker = GetComponent<EndfieldRecoveredParticleEffectSource>();
            SubscribeLifecycleCallbacks();
        }

        private void OnDisable()
        {
            UnsubscribeLifecycleCallbacks();
        }

        private void OnDestroy()
        {
            UnsubscribeLifecycleCallbacks();
        }

        private void SubscribeLifecycleCallbacks()
        {
            if (lifecycleCallbacksSubscribed)
                return;
            Camera.onPreCull += OnCameraPreCull;
            Camera.onPreRender += OnCameraPreRender;
            Camera.onPostRender += OnCameraPostRender;
            RenderPipelineManager.beginCameraRendering += OnBeginCameraRendering;
            RenderPipelineManager.endCameraRendering += OnEndCameraRendering;
            lifecycleCallbacksSubscribed = true;
        }

        private void UnsubscribeLifecycleCallbacks()
        {
            if (!lifecycleCallbacksSubscribed)
                return;
            Camera.onPreCull -= OnCameraPreCull;
            Camera.onPreRender -= OnCameraPreRender;
            Camera.onPostRender -= OnCameraPostRender;
            RenderPipelineManager.beginCameraRendering -= OnBeginCameraRendering;
            RenderPipelineManager.endCameraRendering -= OnEndCameraRendering;
            lifecycleCallbacksSubscribed = false;
        }

        private void OnCameraPreCull(Camera camera)
        {
            cameraOnPreCullCount++;
            RecordCameraCallback("Camera.onPreCull", camera);
        }

        private void OnCameraPreRender(Camera camera)
        {
            cameraOnPreRenderCount++;
            RecordCameraCallback("Camera.onPreRender", camera);
        }

        private void OnCameraPostRender(Camera camera)
        {
            cameraOnPostRenderCount++;
            RecordCameraCallback("Camera.onPostRender", camera);
        }

        private void OnBeginCameraRendering(
            ScriptableRenderContext context, Camera camera)
        {
            beginCameraRenderingCount++;
            RecordCameraCallback("RenderPipeline.beginCameraRendering", camera);
        }

        private void OnEndCameraRendering(
            ScriptableRenderContext context, Camera camera)
        {
            endCameraRenderingCount++;
            RecordCameraCallback("RenderPipeline.endCameraRendering", camera);
        }

        private void RecordCameraCallback(string phase, Camera camera)
        {
            if (camera == null)
                return;
            lastCameraCallbackFrame = Time.frameCount;
            lastCameraCallbackPhase = phase;
            lastCameraCallbackName = camera.name;
            lastCameraCallbackInstanceId = camera.GetInstanceID();
            lastCameraCallbackScene = camera.gameObject.scene.name;
            lastCameraCallbackGameObjectActive = camera.gameObject.activeInHierarchy;
            lastCameraCallbackEnabled = camera.enabled;
            lastCameraCallbackActiveAndEnabled = camera.isActiveAndEnabled;
            lastCameraCallbackPixelWidth = camera.pixelWidth;
            lastCameraCallbackPixelHeight = camera.pixelHeight;
            lastCameraCallbackCullingMask = camera.cullingMask;
            lastCameraCallbackHasTargetTexture = camera.targetTexture != null;
            lastCameraCallbackAllCamerasCount = Camera.allCamerasCount;
        }

        private void Start()
        {
            string[] arguments = Environment.GetCommandLineArgs();
            if (!HasArgument(arguments, ActivationArgument))
                return;

            Application.targetFrameRate = 60;
            Application.runInBackground = true;
            QualitySettings.vSyncCount = 0;
            Shader.SetGlobalFloat("_EndfieldSceneMVMRTReady", 1.0f);
            Shader.SetGlobalFloat("_EndfieldRecoveredVFXGlobalsReady", 1.0f);
            Shader.SetGlobalFloat("_EndfieldRecoveredVFXSoftDepthReady", 0.0f);
            Shader.SetGlobalVector("_ExposureParams", new Vector4(1.0f, 0.0f, 0.0f, 0.0f));

            mode = NormalizeMode(ReadArgument(arguments, ModeArgument));
            quitAfterCapture = HasArgument(arguments, QuitArgument);
            foregroundWindowRequested = HasArgument(arguments, ForegroundWindowArgument);
            RequestForegroundWindowIfRequested();
            framesAfterSetup = ReadBoundedInteger(
                ReadArgument(arguments, "-endfield-m23-particle-renderer-frames"),
                DefaultFramesAfterSetup, MaximumFramesAfterSetup);
            outputPath = ReadArgument(arguments, OutputArgument);
            if (string.IsNullOrWhiteSpace(outputPath))
                outputPath = Path.Combine(
                    Application.persistentDataPath,
                    "lizhiyan_m23_particle_renderer_capture.json");

            StartCoroutine(RunCapture(arguments));
        }

        private IEnumerator RunCapture(string[] arguments)
        {
            CaptureReport report = NewReport();
            CaptureMode captureMode = CaptureMode.Positive;
            try
            {
                PrepareOutputPath();
                Require(!Application.isBatchMode,
                    "The source ParticleSystemRenderer probe requires a normal player; " +
                    "batchmode uses Unity's paused-buffer boundary.");
                Require(SystemInfo.graphicsDeviceType == GraphicsDeviceType.Direct3D11,
                    "Expected Direct3D11, actual=" + SystemInfo.graphicsDeviceType + ".");
                Require(sourceMarker != null && sourceMarker.contractSchema == ExpectedSchema,
                    "The generated M23 source marker is missing or has drifted.");
                Require(sourceMarker.effectRoot == ExpectedRoot &&
                    Mathf.Abs(sourceMarker.sourceEffectDelay - ExpectedEffectDelay) < 0.00001f,
                    "The generated M23 source effect identity or delay drifted.");

                captureMode = ParseMode(mode);
                if (captureMode == CaptureMode.BuiltinPipeline ||
                    captureMode == CaptureMode.ExplicitCameraRender)
                {
                    pipelineBeforeOverride = GraphicsSettings.currentRenderPipeline != null
                        ? GraphicsSettings.currentRenderPipeline.GetType().FullName
                        : string.Empty;
                    GraphicsSettings.renderPipelineAsset = null;
                    QualitySettings.renderPipeline = null;
                }
                targetIdentity = IdentityFor(captureMode);
                BuildSourceMaps();
                ConfigureRenderers(captureMode);
                Require(targetRenderer != null && targetSystem != null,
                    "The selected M23 ParticleSystemRenderer target is missing.");
                Require(targetRenderer.GetComponent<MeshFilter>() == null &&
                    targetRenderer.GetComponent<MeshRenderer>() == null,
                    "The target hierarchy unexpectedly contains a mesh proxy component.");
                sourceMeshBeforeOverride = targetRenderer.mesh;
                serializedSortingFudge = targetRenderer.sortingFudge;
                serializedGpuInstancing = targetRenderer.enableGPUInstancing;
                if (captureMode == CaptureMode.SortingFudgeZero)
                    targetRenderer.sortingFudge = 0.0f;
                if (captureMode == CaptureMode.GpuInstancingOff)
                    targetRenderer.enableGPUInstancing = false;
                if (captureMode == CaptureMode.RendererOcclusionOff)
                    targetRenderer.allowOcclusionWhenDynamic = false;
                if (captureMode == CaptureMode.CameraOcclusionOff)
                {
                    Camera captureCamera = Camera.main;
                    Require(captureCamera != null, "The capture camera is missing.");
                    captureCamera.useOcclusionCulling = false;
                }
                if (captureMode == CaptureMode.BillboardRenderMode)
                    targetRenderer.renderMode = ParticleSystemRenderMode.Billboard;
                if (captureMode == CaptureMode.CompatibilityMaterial)
                {
                    Require(compatibilityMaterial != null &&
                        compatibilityMaterial.shader != null &&
                        compatibilityMaterial.shader.isSupported,
                        "The compatibility material is missing or unsupported.");
                    targetRenderer.sharedMaterial = compatibilityMaterial;
                }
                if (captureMode == CaptureMode.BasicVertexStreams)
                {
                    targetRenderer.SetActiveVertexStreams(
                        new List<ParticleSystemVertexStream>
                        {
                            ParticleSystemVertexStream.Position,
                            ParticleSystemVertexStream.Normal,
                            ParticleSystemVertexStream.Color,
                            ParticleSystemVertexStream.UV,
                        });
                }
                if (captureMode == CaptureMode.DefaultLayer)
                {
                    targetRenderer.gameObject.layer = 0;
                    Camera captureCamera = Camera.main;
                    Require(captureCamera != null, "The capture camera is missing.");
                    captureCamera.cullingMask = -1;
                }

                simulationSeconds = captureMode == CaptureMode.PreDelay
                    ? 0.0f
                    : TargetLocalSeconds;
                serializedRandomSeed = targetSystem.randomSeed;
                if (captureMode == CaptureMode.SourceRepublishIdentical)
                {
                    PrepareSourceFieldRenderer();
                    ResetAndSimulate(targetSystem, simulationSeconds);
                    CaptureOriginalSourceFieldParticles();
                    RepublishOriginalSourceParticles();
                }
                else if (IsSourceFieldAblationMode(captureMode))
                {
                    PrepareSourceFieldRenderer();
                    ResetAndSimulate(targetSystem, simulationSeconds);
                    CaptureOriginalSourceFieldParticles();
                    ApplySourceFieldAblation(captureMode);
                }
                else if (captureMode == CaptureMode.SourceManualParticle)
                {
                    simulationSeconds = 0.0f;
                    PrepareSourceManualParticle();
                }
                else if (captureMode == CaptureMode.NaturalPlayback)
                {
                    simulationSeconds = 0.0f;
                    ResetAndPlayNaturally(targetSystem);
                }
                else if (captureMode != CaptureMode.TargetDisabled)
                    ResetAndSimulate(targetSystem, simulationSeconds);
                else
                    setupPassed = true;
                if (captureMode == CaptureMode.SourceRepublishIdentical ||
                    IsSourceFieldAblationMode(captureMode) ||
                    captureMode == CaptureMode.SourceManualParticle)
                {
                    controlWasSerialized = false;
                    controlObject = null;
                    controlSystem = null;
                    controlRenderer = null;
                }
                else if (captureMode == CaptureMode.SerializedControl ||
                    captureMode == CaptureMode.SerializedControlDisabled)
                    PrepareSerializedControl(captureMode);
                else
                    CreatePositiveControl(captureMode);
                if (captureMode == CaptureMode.ControlDisabled ||
                    captureMode == CaptureMode.SerializedControlDisabled)
                    controlRenderer.enabled = false;
                PrepareSerializedSentinel(captureMode);
                ConfigureCaptureCamera();
                if (captureMode == CaptureMode.ExplicitCameraRender)
                {
                    explicitRenderCamera = Camera.main;
                    Require(explicitRenderCamera != null,
                        "The explicit Camera.Render diagnostic camera is missing.");
                    explicitRenderCamera.enabled = false;
                }
                setupPassed = true;

            }
            catch (Exception exception)
            {
                report.status = "failed";
                report.failure = exception.GetType().FullName + ": " + exception.Message;
                WriteReport(report);
                if (quitAfterCapture)
                    Application.Quit(7);
                yield break;
            }

            // Do not pause after Play(false): the renderer must be submitted by
            // the ordinary player loop. WaitForEndOfFrame places the report after
            // the camera has rendered the current frame.
            for (int frame = 0; frame < framesAfterSetup; frame++)
                yield return null;
            if (captureMode == CaptureMode.ExplicitCameraRender)
            {
                explicitCameraRenderRequested = true;
                Camera captureCamera = explicitRenderCamera;
                if (captureCamera == null)
                {
                    explicitCameraRenderFailure =
                        "The configured camera reference was null at the explicit render boundary.";
                }
                else
                {
                    explicitCameraRenderCallCount++;
                    try
                    {
                        captureCamera.Render();
                        explicitCameraRenderExecuted = true;
                    }
                    catch (Exception exception)
                    {
                        explicitCameraRenderFailure = exception.GetType().FullName +
                            ": " + exception.Message;
                    }
                }
            }
            else
            {
                yield return new WaitForEndOfFrame();
            }

            try
            {
                FillReport(report, captureMode);
                report.status = EvaluateStatus(report, captureMode) ? "pass" : "fail";
                if (report.status != "pass")
                    report.failure = captureMode == CaptureMode.BuiltinPipeline
                        ? "Built-in differential control admission gate failed; source shader parity is not claimed."
                        : captureMode == CaptureMode.ExplicitCameraRender
                            ? "Explicit Camera.Render differential gate failed; source shader parity is not claimed."
                        : "Runtime source-renderer acceptance gate failed.";
            }
            catch (Exception exception)
            {
                report.status = "failed";
                report.failure = exception.GetType().FullName + ": " + exception.Message;
            }

            WriteReport(report);
            if (quitAfterCapture)
                Application.Quit(report.status == "pass" ? 0 : 7);
        }

        private CaptureReport NewReport()
        {
            return new CaptureReport
            {
                status = "failed",
                failure = "not_started",
                mode = mode,
                unityVersion = Application.unityVersion,
                graphicsDeviceType = SystemInfo.graphicsDeviceType.ToString(),
                applicationIsBatchMode = Application.isBatchMode,
                noBakeMeshContract = true,
                noProxyContract = true,
                sourceRendererSubmissionPath = true,
                fixedTimeStep = false,
                simulationContract =
                    "Stop(true, StopEmittingAndClear); Clear(true); restore randomSeed; " +
                    "Simulate(seconds, withChildren:false, restart:true, fixedTimeStep:false); Play(false)",
                prefab =
                    "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Lizhiyan/" +
                    "Effects/OverviewPeakParticles/P_fxui_lizhiyan_overview_start_04_2.prefab",
                effectRoot = ExpectedRoot,
                retailPts = RetailPts,
                retailClockOriginPts = RetailClockOriginPts,
                sourceEffectDelay = sourceMarker != null ? sourceMarker.sourceEffectDelay : 0.0f,
                targetLocalSeconds = TargetLocalSeconds,
                negativeControlExpectation = NegativeExpectation(mode),
            };
        }

        private void BuildSourceMaps()
        {
            renderersByHierarchy.Clear();
            systemsByHierarchy.Clear();
            Require(sourceMarker.particleNodes != null && sourceMarker.particleNodes.Length == 6,
                "M23 source marker particle-node census drifted.");
            foreach (EndfieldRecoveredParticleNodeSource node in sourceMarker.particleNodes)
            {
                Transform host = FindHierarchy(transform, node.hierarchy);
                Require(host != null, "M23 source hierarchy is missing: " + node.hierarchy);
                ParticleSystem system = host.GetComponent<ParticleSystem>();
                ParticleSystemRenderer renderer = host.GetComponent<ParticleSystemRenderer>();
                Require(system != null && renderer != null,
                    "M23 source ParticleSystem/Renderer is missing: " + node.hierarchy);
                renderersByHierarchy.Add(node.hierarchy, renderer);
                systemsByHierarchy.Add(node.hierarchy, system);
            }
        }

        private void ConfigureRenderers(CaptureMode captureMode)
        {
            foreach (string rendererHierarchy in renderersByHierarchy.Keys.ToArray())
            {
                ParticleSystem system = systemsByHierarchy[rendererHierarchy];
                ParticleSystemRenderer renderer = renderersByHierarchy[rendererHierarchy];
                ParticleSystem.MainModule main = system.main;
                main.playOnAwake = false;
                system.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
                system.Clear(true);
                renderer.enabled = false;
            }

            string hierarchy = targetIdentity.hierarchy;
            targetSystem = systemsByHierarchy[hierarchy];
            targetRenderer = renderersByHierarchy[hierarchy];
            targetRenderer.enabled = captureMode != CaptureMode.TargetDisabled;
            gameObject.SetActive(true);
            targetSystem.gameObject.SetActive(true);
        }

        private void ResetAndSimulate(ParticleSystem system, float seconds)
        {
            serializedRandomSeed = system.randomSeed;
            system.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            system.Clear(true);
            system.randomSeed = serializedRandomSeed;
            Require(system.randomSeed == serializedRandomSeed,
                "M23 serialized randomSeed could not be restored.");
            system.Simulate(seconds, false, true, false);
            system.Play(false);
            Require(system.randomSeed == serializedRandomSeed,
                "M23 randomSeed changed while publishing the runtime renderer state.");
        }

        private void ResetAndPlayNaturally(ParticleSystem system)
        {
            serializedRandomSeed = system.randomSeed;
            system.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            system.Clear(true);
            system.randomSeed = serializedRandomSeed;
            system.Play(false);
            setupPassed = system.randomSeed == serializedRandomSeed;
        }

        private void ConfigureCaptureCamera()
        {
            Camera camera = Camera.main;
            Require(camera != null, "The M23 source-renderer capture camera is missing.");
            Bounds bounds = targetRenderer.bounds;
            Require(IsFinite(bounds.center) && IsFinite(bounds.extents),
                "The M23 source renderer published non-finite bounds.");
            float radius = Mathf.Max(0.25f, bounds.extents.magnitude);
            camera.orthographic = true;
            camera.orthographicSize = Mathf.Max(0.5f, radius * 1.5f);
            camera.transform.SetPositionAndRotation(
                bounds.center - Vector3.forward * Mathf.Max(2.0f, radius * 4.0f),
                Quaternion.identity);
            camera.nearClipPlane = 0.01f;
            camera.farClipPlane = Mathf.Max(100.0f, radius * 10.0f);
        }

        private void PrepareSourceFieldRenderer()
        {
            Require(targetSystem != null && targetRenderer != null,
                "The source field-ablation target components are missing.");
            Require(compatibilityMaterial != null && compatibilityMaterial.shader != null &&
                compatibilityMaterial.shader.isSupported,
                "The source field-ablation compatibility material is missing or unsupported.");
            targetRenderer.enabled = true;
            targetRenderer.sharedMaterial = compatibilityMaterial;
            targetRenderer.enableGPUInstancing = false;
            targetRenderer.SetActiveVertexStreams(
                new List<ParticleSystemVertexStream>
                {
                    ParticleSystemVertexStream.Position,
                    ParticleSystemVertexStream.Normal,
                    ParticleSystemVertexStream.Color,
                    ParticleSystemVertexStream.UV,
                });
        }

        private void CaptureOriginalSourceFieldParticles()
        {
            int count = targetSystem.particleCount;
            Require(count > 0 && count <= MaximumSourceFieldParticles,
                "The original source particle count is outside the bounded field-ablation range: " +
                count.ToString(CultureInfo.InvariantCulture));
            sourceFieldOriginalParticles = new ParticleSystem.Particle[count];
            int retrieved = targetSystem.GetParticles(sourceFieldOriginalParticles);
            Require(retrieved == count,
                "The source field-ablation particle retrieval count drifted: expected=" +
                count.ToString(CultureInfo.InvariantCulture) + ", actual=" +
                retrieved.ToString(CultureInfo.InvariantCulture));
            sourceFieldOriginalCustom1 = new List<Vector4>(count);
            int customCount = targetSystem.GetCustomParticleData(
                sourceFieldOriginalCustom1, ParticleSystemCustomData.Custom1);
            Require(customCount == 0 || customCount == count,
                "The source Custom1 count is not one-to-one with particles: " +
                customCount.ToString(CultureInfo.InvariantCulture));
            sourceFieldOriginalParticleCount = count;
            sourceFieldOriginalCaptured = true;
        }

        private void ApplySourceFieldAblation(CaptureMode captureMode)
        {
            Require(sourceFieldOriginalCaptured && sourceFieldOriginalParticles != null,
                "The source field-ablation baseline was not captured.");
            sourceFieldFamily = SourceFieldFamilyForMode(captureMode);
            Require(sourceFieldFamily != SourceFieldFamily.None,
                "The source field-ablation mode is not mapped to a field family.");

            ParticleSystem.Particle[] particles = new ParticleSystem.Particle[
                sourceFieldOriginalParticleCount];
            Array.Copy(sourceFieldOriginalParticles, particles, particles.Length);
            List<Vector4> custom1 = null;
            if (sourceFieldFamily == SourceFieldFamily.Custom1)
            {
                custom1 = new List<Vector4>(sourceFieldOriginalParticleCount);
                for (int index = 0; index < sourceFieldOriginalParticleCount; index++)
                    custom1.Add(Vector4.one);
            }

            for (int index = 0; index < particles.Length; index++)
            {
                ParticleSystem.Particle particle = particles[index];
                switch (sourceFieldFamily)
                {
                    case SourceFieldFamily.Lifetime:
                        particle.startLifetime = 10.0f;
                        particle.remainingLifetime = 10.0f;
                        break;
                    case SourceFieldFamily.Size:
                        particle.startSize = 1.0f;
                        particle.startSize3D = Vector3.one;
                        break;
                    case SourceFieldFamily.Color:
                        particle.startColor = new Color32(255, 255, 255, 255);
                        break;
                    case SourceFieldFamily.Rotation:
                        particle.axisOfRotation = Vector3.zero;
                        particle.rotation = 0.0f;
                        particle.rotation3D = Vector3.zero;
                        particle.angularVelocity = 0.0f;
                        particle.angularVelocity3D = Vector3.zero;
                        break;
                    case SourceFieldFamily.Velocity:
                        particle.velocity = Vector3.zero;
                        break;
                }
                particles[index] = particle;
            }

            targetSystem.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            targetSystem.Clear(true);
            targetSystem.SetParticles(particles, particles.Length);
            if (sourceFieldFamily == SourceFieldFamily.Custom1)
            {
                targetSystem.SetCustomParticleData(custom1, ParticleSystemCustomData.Custom1);
            }
            else if (sourceFieldOriginalCustom1 != null &&
                sourceFieldOriginalCustom1.Count == sourceFieldOriginalParticleCount)
            {
                targetSystem.SetCustomParticleData(
                    new List<Vector4>(sourceFieldOriginalCustom1),
                    ParticleSystemCustomData.Custom1);
            }
            targetSystem.Play(false);
            targetSystem.Pause(false);
        }

        private void RepublishOriginalSourceParticles()
        {
            Require(sourceFieldOriginalCaptured && sourceFieldOriginalParticles != null,
                "The source republish baseline was not captured.");
            targetSystem.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            targetSystem.Clear(true);
            targetSystem.SetParticles(
                sourceFieldOriginalParticles, sourceFieldOriginalParticles.Length);
            targetSystem.SetCustomParticleData(
                sourceFieldOriginalCustom1 != null
                    ? new List<Vector4>(sourceFieldOriginalCustom1)
                    : new List<Vector4>(),
                ParticleSystemCustomData.Custom1);
            targetSystem.Play(false);
            targetSystem.Pause(false);
        }

        private void PrepareSourceManualParticle()
        {
            Require(targetSystem != null && targetRenderer != null,
                "The source manual-particle target components are missing.");
            Require(sourceMeshBeforeOverride != null,
                "The source manual-particle target mesh is missing.");
            Require(compatibilityMaterial != null && compatibilityMaterial.shader != null &&
                compatibilityMaterial.shader.isSupported,
                "The source manual-particle compatibility material is missing or unsupported.");

            ParticleSystem.MainModule main = targetSystem.main;
            main.playOnAwake = false;
            main.loop = false;
            main.startDelay = 0.0f;
            main.startLifetime = 10.0f;
            main.startSpeed = 0.0f;
            main.startSize = 1.0f;
            main.maxParticles = 1;
            main.simulationSpace = ParticleSystemSimulationSpace.Local;
            targetRenderer.enabled = true;
            targetRenderer.sharedMaterial = compatibilityMaterial;
            targetRenderer.enableGPUInstancing = false;
            targetRenderer.SetActiveVertexStreams(
                new List<ParticleSystemVertexStream>
                {
                    ParticleSystemVertexStream.Position,
                    ParticleSystemVertexStream.Normal,
                    ParticleSystemVertexStream.Color,
                    ParticleSystemVertexStream.UV,
                });

            targetSystem.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            targetSystem.Clear(true);
            sourceManualParticle = new ParticleSystem.Particle
            {
                position = Vector3.zero,
                velocity = Vector3.zero,
                remainingLifetime = 10.0f,
                startLifetime = 10.0f,
                startColor = new Color32(255, 255, 255, 255),
                startSize = 1.0f,
                randomSeed = 1u,
            };
            targetSystem.SetParticles(new[] { sourceManualParticle }, 1);
            targetSystem.Play(false);
            sourceManualParticlePublished = targetSystem.particleCount == 1;
            Require(sourceManualParticlePublished,
                "The source manual-particle target did not retain one explicit particle.");
        }

        private void CreatePositiveControl(CaptureMode captureMode)
        {
            controlWasSerialized = false;
            controlCaptureMode = captureMode;
            bool builtin = captureMode == CaptureMode.BuiltinPipeline ||
                captureMode == CaptureMode.ExplicitCameraRender;
            Material controlMaterial = builtin
                ? builtinCompatibilityMaterial
                : compatibilityMaterial;
            Require(controlMaterial != null && controlMaterial.shader != null &&
                controlMaterial.shader.isSupported,
                builtin
                    ? "The built-in compatibility material is missing or unsupported."
                    : "The positive-control compatibility material is missing or unsupported.");

            controlObject = new GameObject(ControlObjectName);
            SceneManager.MoveGameObjectToScene(controlObject, gameObject.scene);
            controlObject.layer = targetRenderer.gameObject.layer;
            controlObject.transform.SetPositionAndRotation(
                targetRenderer.bounds.center + Vector3.forward * 0.5f,
                Quaternion.identity);

            controlSystem = controlObject.AddComponent<ParticleSystem>();
            controlRenderer = controlObject.GetComponent<ParticleSystemRenderer>();
            Require(controlRenderer != null, "Could not create the control ParticleSystemRenderer.");

            ParticleSystem.MainModule main = controlSystem.main;
            main.playOnAwake = false;
            main.loop = false;
            main.startDelay = 0.0f;
            main.startLifetime = 10.0f;
            main.startSpeed = 0.0f;
            main.startSize = 1.0f;
            main.maxParticles = 1;
            main.simulationSpace = ParticleSystemSimulationSpace.World;

            ParticleSystem.EmissionModule emission = controlSystem.emission;
            emission.enabled = false;
            controlRenderer.renderMode = ParticleSystemRenderMode.Billboard;
            if (captureMode == CaptureMode.MeshControl)
            {
                Mesh targetMesh = targetRenderer.mesh;
                Require(targetMesh != null,
                    "The M23 source renderer has no mesh for the mesh-control diagnostic.");
                controlRenderer.renderMode = ParticleSystemRenderMode.Mesh;
                controlRenderer.mesh = targetMesh;
            }
            controlRenderer.sharedMaterial = controlMaterial;
            controlRenderer.enableGPUInstancing = false;
            controlRenderer.allowOcclusionWhenDynamic = false;
            controlRenderer.sortingFudge = 0.0f;

            controlSystem.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            controlSystem.Clear(true);
            controlSystem.Emit(1);
            controlSystem.Play(false);
            Require(controlSystem.particleCount > 0,
                "The positive-control ParticleSystem emitted no particles.");
        }

        private void PrepareSerializedControl(CaptureMode captureMode)
        {
            Require(serializedControlSystem != null && serializedControlRenderer != null,
                "The serialized ParticleSystemRenderer control reference is missing.");
            Require(serializedControlSystem.gameObject.scene == gameObject.scene &&
                serializedControlRenderer.gameObject.scene == gameObject.scene,
                "The serialized ParticleSystemRenderer control is not in the capture scene.");
            controlCaptureMode = captureMode;
            controlWasSerialized = true;
            controlSystem = serializedControlSystem;
            controlRenderer = serializedControlRenderer;
            controlObject = controlRenderer.gameObject;
            controlObject.layer = targetRenderer.gameObject.layer;
            controlObject.transform.SetPositionAndRotation(
                targetRenderer.bounds.center + Vector3.forward * 0.5f,
                Quaternion.identity);
            controlRenderer.enabled = true;
            controlSystem.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            controlSystem.Clear(true);
            controlSystem.Emit(1);
            controlSystem.Play(false);
            Require(controlSystem.particleCount > 0,
                "The serialized ParticleSystemRenderer control emitted no particles.");
        }

        private void PrepareSerializedSentinel(CaptureMode captureMode)
        {
            Require(serializedSentinelFilter != null && serializedSentinelRenderer != null,
                "The serialized MeshRenderer camera/culling sentinel reference is missing.");
            Require(serializedSentinelFilter.gameObject == serializedSentinelRenderer.gameObject &&
                serializedSentinelRenderer.gameObject.scene == gameObject.scene,
                "The serialized MeshRenderer sentinel is not a same-scene MeshFilter pair.");
            serializedSentinelRenderer.enabled = captureMode != CaptureMode.SentinelDisabled;
            serializedSentinelRenderer.sharedMaterial =
                (captureMode == CaptureMode.BuiltinPipeline ||
                 captureMode == CaptureMode.ExplicitCameraRender)
                ? builtinCompatibilityMaterial
                : compatibilityMaterial;
        }

        private void FillReport(CaptureReport report, CaptureMode captureMode)
        {
            report.mode = mode;
            report.applicationRunsInBackground = Application.runInBackground;
            report.frameCountAtCapture = Time.frameCount;
            report.framesAfterSetup = framesAfterSetup;
            report.sourceEffectDelay = sourceMarker.sourceEffectDelay;
            report.targetLocalSeconds = simulationSeconds;
            report.targetGameObjectActive = targetSystem.gameObject.activeInHierarchy;
            report.targetRendererEnabled = targetRenderer.enabled;
            report.targetRendererVisible = targetRenderer.isVisible;
            Camera captureCamera = explicitRenderCamera != null
                ? explicitRenderCamera
                : Camera.main;
            report.serializedSortingFudge = FormatFloat(serializedSortingFudge);
            report.sortingFudgeAtCapture = FormatFloat(targetRenderer.sortingFudge);
            report.diagnosticSortingFudgeZeroOverride =
                captureMode == CaptureMode.SortingFudgeZero;
            report.serializedGpuInstancing = serializedGpuInstancing;
            report.gpuInstancingAtCapture = targetRenderer.enableGPUInstancing;
            report.diagnosticGpuInstancingOffOverride =
                captureMode == CaptureMode.GpuInstancingOff;
            report.rendererAllowsDynamicOcclusion =
                targetRenderer.allowOcclusionWhenDynamic;
            report.cameraUsesOcclusionCulling = captureCamera != null &&
                captureCamera.useOcclusionCulling;
            report.diagnosticRendererOcclusionOffOverride =
                captureMode == CaptureMode.RendererOcclusionOff;
            report.diagnosticCameraOcclusionOffOverride =
                captureMode == CaptureMode.CameraOcclusionOff;
            report.diagnosticBillboardRenderModeOverride =
                captureMode == CaptureMode.BillboardRenderMode;
            report.diagnosticCompatibilityMaterialOverride =
                captureMode == CaptureMode.CompatibilityMaterial ||
                captureMode == CaptureMode.SourceManualParticle ||
                captureMode == CaptureMode.SourceRepublishIdentical ||
                IsSourceFieldAblationMode(captureMode);
            report.diagnosticBasicVertexStreamsOverride =
                captureMode == CaptureMode.BasicVertexStreams;
            report.diagnosticNaturalPlaybackOverride =
                captureMode == CaptureMode.NaturalPlayback;
            report.diagnosticDefaultLayerOverride =
                captureMode == CaptureMode.DefaultLayer;
            report.targetBoundsCenter = targetRenderer.bounds.center;
            report.targetBoundsExtents = targetRenderer.bounds.extents;
            report.captureCameraPosition = captureCamera != null
                ? captureCamera.transform.position
                : Vector3.zero;
            report.captureCameraOrthographicSize = captureCamera != null
                ? captureCamera.orthographicSize
                : 0.0f;
            report.captureCameraCullingMask = captureCamera != null
                ? captureCamera.cullingMask
                : 0;
            report.targetLayer = targetRenderer.gameObject.layer;
            report.publicFrustumIntersectsBounds = captureCamera != null &&
                GeometryUtility.TestPlanesAABB(
                    GeometryUtility.CalculateFrustumPlanes(captureCamera),
                    targetRenderer.bounds);
            Material captureMaterial = targetRenderer.sharedMaterial;
            report.materialShaderSupported = captureMaterial != null &&
                captureMaterial.shader != null && captureMaterial.shader.isSupported;
            report.materialPassCount = captureMaterial != null
                ? captureMaterial.passCount
                : 0;
            report.materialRenderQueue = captureMaterial != null
                ? captureMaterial.renderQueue
                : -1;
            report.materialName = captureMaterial != null
                ? captureMaterial.name
                : string.Empty;
            report.materialShaderName = captureMaterial != null &&
                captureMaterial.shader != null
                ? captureMaterial.shader.name
                : string.Empty;
            report.materialMrtAdmissionTag = captureMaterial != null
                ? captureMaterial.GetTag("EndfieldSceneMVMRT", false, string.Empty)
                : string.Empty;
            report.currentRenderPipelineType =
                GraphicsSettings.currentRenderPipeline != null
                    ? GraphicsSettings.currentRenderPipeline.GetType().FullName
                    : string.Empty;
            report.pipelineBeforeOverride = pipelineBeforeOverride ?? string.Empty;
            report.builtinPipelineOverride = captureMode == CaptureMode.BuiltinPipeline ||
                captureMode == CaptureMode.ExplicitCameraRender;
            report.foregroundWindowRequested = foregroundWindowRequested;
            report.foregroundWindowPlatformSupported = foregroundWindowPlatformSupported;
            report.foregroundWindowHandle = foregroundWindowHandle;
            report.foregroundWindowHandleNonZero = foregroundWindowHandleNonZero;
            report.foregroundWindowIsWindow = foregroundWindowIsWindow;
            report.foregroundWindowShowWindowCalled = foregroundWindowShowWindowCalled;
            report.foregroundWindowShowWindowResult = foregroundWindowShowWindowResult;
            report.foregroundWindowSetForegroundWindowCalled =
                foregroundWindowSetForegroundWindowCalled;
            report.foregroundWindowSetForegroundWindowResult =
                foregroundWindowSetForegroundWindowResult;
            report.foregroundWindowFailure = foregroundWindowFailure;
            report.explicitCameraRenderMode =
                captureMode == CaptureMode.ExplicitCameraRender;
            report.explicitCameraRenderRequested = explicitCameraRenderRequested;
            report.explicitCameraRenderExecuted = explicitCameraRenderExecuted;
            report.explicitCameraRenderCallCount = explicitCameraRenderCallCount;
            report.explicitCameraRenderFailure = explicitCameraRenderFailure;
            FillDirectCameraReport(report, captureCamera);
            EndfieldRecoveredSceneMVDiagnosticState sceneMV =
                HDRenderPipeline.LastRecoveredSceneMVDiagnostic;
            report.recoveredSceneMVRequested = sceneMV.requested;
            report.recoveredSceneMVRequestFailure = sceneMV.requestFailure;
            report.recoveredSceneMVDescriptorCreated = sceneMV.descriptorCreated;
            report.recoveredAfterPostExecuted =
                sceneMV.afterPostSceneMVLoadStoreNoClear;
            report.cameraOnPreCullCount = cameraOnPreCullCount;
            report.cameraOnPreRenderCount = cameraOnPreRenderCount;
            report.cameraOnPostRenderCount = cameraOnPostRenderCount;
            report.beginCameraRenderingCount = beginCameraRenderingCount;
            report.endCameraRenderingCount = endCameraRenderingCount;
            report.lastCameraCallbackFrame = lastCameraCallbackFrame;
            report.lastCameraCallbackPhase = lastCameraCallbackPhase;
            report.lastCameraCallbackName = lastCameraCallbackName;
            report.lastCameraCallbackInstanceId = lastCameraCallbackInstanceId;
            report.lastCameraCallbackScene = lastCameraCallbackScene;
            report.lastCameraCallbackGameObjectActive = lastCameraCallbackGameObjectActive;
            report.lastCameraCallbackEnabled = lastCameraCallbackEnabled;
            report.lastCameraCallbackActiveAndEnabled = lastCameraCallbackActiveAndEnabled;
            report.lastCameraCallbackPixelWidth = lastCameraCallbackPixelWidth;
            report.lastCameraCallbackPixelHeight = lastCameraCallbackPixelHeight;
            report.lastCameraCallbackCullingMask = lastCameraCallbackCullingMask;
            report.lastCameraCallbackHasTargetTexture = lastCameraCallbackHasTargetTexture;
            report.lastCameraCallbackAllCamerasCount = lastCameraCallbackAllCamerasCount;
            report.targetRendererMeshMode = targetRenderer.renderMode == ParticleSystemRenderMode.Mesh;
            report.targetHasMeshFilter = targetRenderer.GetComponent<MeshFilter>() != null;
            report.targetHasMeshRenderer = targetRenderer.GetComponent<MeshRenderer>() != null;
            report.particleCount = targetSystem.particleCount;
            var streams = new List<ParticleSystemVertexStream>();
            targetRenderer.GetActiveVertexStreams(streams);
            report.activeVertexStreamIds = streams.Select(value => (int)value).ToArray();
            report.activeVertexStreams = streams.Select(value => value.ToString()).ToArray();
            report.identity = targetIdentity;
            report.exactIdentityClosed = IdentityMatchesMarker(targetIdentity);
            report.deterministicResetClosed = setupPassed && !float.IsNaN(simulationSeconds) &&
                targetSystem.randomSeed == serializedRandomSeed;
            report.serializedRandomSeed = serializedRandomSeed;
            report.randomSeedAfterReset = targetSystem.randomSeed;
            report.targetUsesDiagnosticMaterial = UsesDiagnosticMaterial(targetRenderer);
            FillSourceManualParticleReport(report, captureMode);
            FillSourceFieldReport(report, captureMode);
            FillControlReport(report, captureCamera, captureMode);
        }

        private void FillSourceFieldReport(CaptureReport report, CaptureMode captureMode)
        {
            bool republish = captureMode == CaptureMode.SourceRepublishIdentical;
            bool active = IsSourceFieldAblationMode(captureMode) || republish;
            report.sourceFieldFamily = republish
                ? "republish-identical"
                : active ? SourceFieldFamilyName(SourceFieldFamilyForMode(captureMode)) : string.Empty;
            report.sourceRepublishIdenticalMode = republish;
            report.sourceFieldContract =
                "exact source ParticleSystem/ParticleSystemRenderer/mesh; original simulated " +
                (republish
                    ? "particles captured before identical public-API republish; "
                    : "particles captured before one-family public-API ablation; ") +
                "compatibility material; " +
                "GPU instancing off; basic Position/Normal/Color/UV streams; bounded to " +
                MaximumSourceFieldParticles.ToString(CultureInfo.InvariantCulture) +
                " particles; fail closed on unrelated field changes";
            if (!active)
                return;

            report.sourceFieldOriginalCaptured = sourceFieldOriginalCaptured;
            report.sourceFieldOriginalParticleCount = sourceFieldOriginalParticleCount;
            report.sourceFieldBefore = BuildSourceFieldSnapshots(
                sourceFieldOriginalParticles, sourceFieldOriginalCustom1);
            report.sourceFieldCustom1Before = NormalizeCustomData(
                sourceFieldOriginalCustom1, sourceFieldOriginalParticleCount);
            Require(sourceFieldOriginalCaptured && sourceFieldOriginalParticles != null,
                "The source field-ablation baseline is missing at report time.");

            ParticleSystem.Particle[] after = new ParticleSystem.Particle[
                MaximumSourceFieldParticles];
            int afterCount = targetSystem.GetParticles(after);
            Require(afterCount >= 0 && afterCount <= MaximumSourceFieldParticles,
                "The source field-ablation after-count exceeded the bound.");
            Array.Resize(ref after, afterCount);
            List<Vector4> afterCustom1 = new List<Vector4>(afterCount);
            int afterCustomCount = targetSystem.GetCustomParticleData(
                afterCustom1, ParticleSystemCustomData.Custom1);
            Require(afterCustomCount == 0 || afterCustomCount == afterCount,
                "The source field-ablation after Custom1 count is not one-to-one.");
            report.sourceFieldAfterParticleCount = afterCount;
            report.sourceFieldAfterCaptured = afterCount == sourceFieldOriginalParticleCount &&
                (afterCustomCount == 0 || afterCustomCount == afterCount);
            report.sourceFieldAfter = BuildSourceFieldSnapshots(after, afterCustom1);
            report.sourceFieldCustom1After = NormalizeCustomData(afterCustom1, afterCount);
            report.sourceFieldRequestedFamilyChanged = SourceFieldFamilyChanged(
                report.sourceFieldBefore,
                report.sourceFieldAfter,
                report.sourceFieldCustom1Before,
                report.sourceFieldCustom1After,
                SourceFieldFamilyForMode(captureMode));
            report.sourceFieldChangedOnlyRequestedFamily =
                SourceFieldChangedOnlyRequestedFamily(
                    report.sourceFieldBefore,
                    report.sourceFieldAfter,
                    report.sourceFieldCustom1Before,
                    report.sourceFieldCustom1After,
                    republish ? SourceFieldFamily.None : SourceFieldFamilyForMode(captureMode));
            if (republish)
            {
                report.sourceRepublishOriginalCaptured = report.sourceFieldOriginalCaptured;
                report.sourceRepublishAfterCaptured = report.sourceFieldAfterCaptured;
                report.sourceRepublishParticleValuesEqual =
                    ParticleSnapshotsExactlyEqual(
                        report.sourceFieldBefore, report.sourceFieldAfter);
                report.sourceRepublishCustom1Equal =
                    CustomDataExactlyEqual(
                        report.sourceFieldCustom1Before, report.sourceFieldCustom1After);
                report.sourceRepublishNoFieldChanges =
                    report.sourceRepublishParticleValuesEqual &&
                    report.sourceRepublishCustom1Equal;
                report.sourceRepublishContract =
                    "Clear; SetParticles(original rows); SetCustomParticleData(original Custom1); " +
                    "no public particle field mutation; exact component/mesh/material/stream admission";
            }
            report.sourceFieldAdmission = report.sourceFieldOriginalCaptured &&
                !republish &&
                report.sourceFieldAfterCaptured && report.sourceFieldRequestedFamilyChanged &&
                report.sourceFieldChangedOnlyRequestedFamily && report.exactIdentityClosed &&
                report.noBakeMeshContract && report.noProxyContract &&
                !report.targetHasMeshFilter && !report.targetHasMeshRenderer &&
                report.targetGameObjectActive && report.targetRendererEnabled &&
                report.particleCount == sourceFieldOriginalParticleCount &&
                sourceMeshBeforeOverride != null &&
                targetRenderer.mesh == sourceMeshBeforeOverride &&
                report.diagnosticCompatibilityMaterialOverride &&
                report.materialShaderSupported && report.materialPassCount > 0 &&
                !targetRenderer.enableGPUInstancing &&
                report.activeVertexStreamIds.SequenceEqual(new[] { 0, 1, 3, 4 }) &&
                IsFinite(report.targetBoundsCenter) && IsFinite(report.targetBoundsExtents) &&
                report.publicFrustumIntersectsBounds && report.targetRendererVisible;
            report.sourceRepublishAdmission = republish &&
                report.sourceRepublishOriginalCaptured && report.sourceRepublishAfterCaptured &&
                report.sourceRepublishNoFieldChanges && report.exactIdentityClosed &&
                report.noBakeMeshContract && report.noProxyContract &&
                !report.targetHasMeshFilter && !report.targetHasMeshRenderer &&
                report.targetGameObjectActive && report.targetRendererEnabled &&
                report.particleCount == sourceFieldOriginalParticleCount &&
                sourceMeshBeforeOverride != null && targetRenderer.mesh == sourceMeshBeforeOverride &&
                report.diagnosticCompatibilityMaterialOverride &&
                report.materialShaderSupported && report.materialPassCount > 0 &&
                !targetRenderer.enableGPUInstancing &&
                report.activeVertexStreamIds.SequenceEqual(new[] { 0, 1, 3, 4 }) &&
                IsFinite(report.targetBoundsCenter) && IsFinite(report.targetBoundsExtents) &&
                report.publicFrustumIntersectsBounds && report.targetRendererVisible;
        }

        private SourceFieldParticleSnapshot[] BuildSourceFieldSnapshots(
            ParticleSystem.Particle[] particles, List<Vector4> custom1)
        {
            if (particles == null)
                return new SourceFieldParticleSnapshot[0];
            SourceFieldParticleSnapshot[] snapshots =
                new SourceFieldParticleSnapshot[particles.Length];
            for (int index = 0; index < particles.Length; index++)
            {
                ParticleSystem.Particle particle = particles[index];
                Color32 color = particle.startColor;
                snapshots[index] = new SourceFieldParticleSnapshot
                {
                    index = index,
                    position = particle.position,
                    velocity = particle.velocity,
                    animatedVelocity = particle.animatedVelocity,
                    axisOfRotation = particle.axisOfRotation,
                    rotation = particle.rotation,
                    rotation3D = particle.rotation3D,
                    angularVelocity = particle.angularVelocity,
                    angularVelocity3D = particle.angularVelocity3D,
                    startSize = particle.startSize,
                    startSize3D = particle.startSize3D,
                    startColor = new Color(
                        color.r / 255.0f,
                        color.g / 255.0f,
                        color.b / 255.0f,
                        color.a / 255.0f),
                    remainingLifetime = particle.remainingLifetime,
                    startLifetime = particle.startLifetime,
                    randomSeed = particle.randomSeed,
                    custom1 = custom1 != null && custom1.Count == particles.Length
                        ? custom1[index]
                        : Vector4.zero,
                };
            }
            return snapshots;
        }

        private static Vector4[] NormalizeCustomData(List<Vector4> values, int count)
        {
            Vector4[] normalized = new Vector4[Mathf.Max(0, count)];
            if (values != null && values.Count == count)
                values.CopyTo(normalized);
            return normalized;
        }

        private static bool SourceFieldChangedOnlyRequestedFamily(
            SourceFieldParticleSnapshot[] before,
            SourceFieldParticleSnapshot[] after,
            Vector4[] customBefore,
            Vector4[] customAfter,
            SourceFieldFamily family)
        {
            if (before == null || after == null || before.Length != after.Length ||
                customBefore == null || customAfter == null || customBefore.Length != customAfter.Length)
                return false;
            for (int index = 0; index < before.Length; index++)
            {
                if (!ParticleSnapshotsEqualExceptFamily(before[index], after[index], family))
                    return false;
                if (family != SourceFieldFamily.Custom1 &&
                    !Approximately(customBefore[index], customAfter[index]))
                    return false;
            }
            return true;
        }

        private static bool ParticleSnapshotsExactlyEqual(
            SourceFieldParticleSnapshot[] before,
            SourceFieldParticleSnapshot[] after)
        {
            if (before == null || after == null || before.Length != after.Length)
                return false;
            for (int index = 0; index < before.Length; index++)
            {
                SourceFieldParticleSnapshot left = before[index];
                SourceFieldParticleSnapshot right = after[index];
                if (left.index != right.index ||
                    !Exactly(left.position, right.position) ||
                    !Exactly(left.velocity, right.velocity) ||
                    !Exactly(left.animatedVelocity, right.animatedVelocity) ||
                    !Exactly(left.axisOfRotation, right.axisOfRotation) ||
                    !Exactly(left.rotation, right.rotation) ||
                    !Exactly(left.rotation3D, right.rotation3D) ||
                    !Exactly(left.angularVelocity, right.angularVelocity) ||
                    !Exactly(left.angularVelocity3D, right.angularVelocity3D) ||
                    !Exactly(left.startSize, right.startSize) ||
                    !Exactly(left.startSize3D, right.startSize3D) ||
                    !Exactly(left.startColor, right.startColor) ||
                    !Exactly(left.remainingLifetime, right.remainingLifetime) ||
                    !Exactly(left.startLifetime, right.startLifetime) ||
                    left.randomSeed != right.randomSeed)
                    return false;
            }
            return true;
        }

        private static bool CustomDataExactlyEqual(Vector4[] before, Vector4[] after)
        {
            if (before == null || after == null || before.Length != after.Length)
                return false;
            for (int index = 0; index < before.Length; index++)
            {
                if (!Exactly(before[index], after[index]))
                    return false;
            }
            return true;
        }

        private static bool Exactly(Vector3 left, Vector3 right)
        {
            return left.x == right.x && left.y == right.y && left.z == right.z;
        }

        private static bool Exactly(Vector4 left, Vector4 right)
        {
            return left.x == right.x && left.y == right.y &&
                left.z == right.z && left.w == right.w;
        }

        private static bool Exactly(Color left, Color right)
        {
            return left.r == right.r && left.g == right.g &&
                left.b == right.b && left.a == right.a;
        }

        private static bool Exactly(float left, float right)
        {
            return left == right;
        }

        private static bool SourceFieldFamilyChanged(
            SourceFieldParticleSnapshot[] before,
            SourceFieldParticleSnapshot[] after,
            Vector4[] customBefore,
            Vector4[] customAfter,
            SourceFieldFamily family)
        {
            if (before == null || after == null || before.Length != after.Length ||
                customBefore == null || customAfter == null || customBefore.Length != customAfter.Length)
                return false;
            for (int index = 0; index < before.Length; index++)
            {
                if (!ParticleSnapshotsEqualExceptFamily(before[index], after[index], family))
                    return false;
                if (family == SourceFieldFamily.Custom1)
                {
                    if (!Approximately(customBefore[index], customAfter[index]))
                        return true;
                }
                else if (!ParticleSnapshotsEqualForFamily(before[index], after[index], family))
                {
                    return true;
                }
            }
            return false;
        }

        private static bool ParticleSnapshotsEqualExceptFamily(
            SourceFieldParticleSnapshot before,
            SourceFieldParticleSnapshot after,
            SourceFieldFamily family)
        {
            if (!Approximately(before.position, after.position) ||
                !Approximately(before.randomSeed, after.randomSeed))
                return false;
            if (family != SourceFieldFamily.Velocity &&
                (!Approximately(before.velocity, after.velocity) ||
                 !Approximately(before.animatedVelocity, after.animatedVelocity)))
                return false;
            if (family != SourceFieldFamily.Rotation &&
                (!Approximately(before.axisOfRotation, after.axisOfRotation) ||
                 !Approximately(before.rotation, after.rotation) ||
                 !Approximately(before.rotation3D, after.rotation3D) ||
                 !Approximately(before.angularVelocity, after.angularVelocity) ||
                 !Approximately(before.angularVelocity3D, after.angularVelocity3D)))
                return false;
            if (family != SourceFieldFamily.Size &&
                (!Approximately(before.startSize, after.startSize) ||
                 !Approximately(before.startSize3D, after.startSize3D)))
                return false;
            if (family != SourceFieldFamily.Color &&
                !Approximately(before.startColor, after.startColor))
                return false;
            if (family != SourceFieldFamily.Lifetime &&
                (!Approximately(before.remainingLifetime, after.remainingLifetime) ||
                 !Approximately(before.startLifetime, after.startLifetime)))
                return false;
            return true;
        }

        private static bool ParticleSnapshotsEqualForFamily(
            SourceFieldParticleSnapshot before,
            SourceFieldParticleSnapshot after,
            SourceFieldFamily family)
        {
            switch (family)
            {
                case SourceFieldFamily.Lifetime:
                    return Approximately(before.remainingLifetime, after.remainingLifetime) &&
                        Approximately(before.startLifetime, after.startLifetime);
                case SourceFieldFamily.Size:
                    return Approximately(before.startSize, after.startSize) &&
                        Approximately(before.startSize3D, after.startSize3D);
                case SourceFieldFamily.Color:
                    return Approximately(before.startColor, after.startColor);
                case SourceFieldFamily.Rotation:
                    return Approximately(before.axisOfRotation, after.axisOfRotation) &&
                        Approximately(before.rotation, after.rotation) &&
                        Approximately(before.rotation3D, after.rotation3D) &&
                        Approximately(before.angularVelocity, after.angularVelocity) &&
                        Approximately(before.angularVelocity3D, after.angularVelocity3D);
                case SourceFieldFamily.Velocity:
                    return Approximately(before.velocity, after.velocity) &&
                        Approximately(before.animatedVelocity, after.animatedVelocity);
                default:
                    return true;
            }
        }

        private static bool Approximately(Vector3 left, Vector3 right)
        {
            return (left - right).sqrMagnitude <= 0.000001f;
        }

        private static bool Approximately(Vector4 left, Vector4 right)
        {
            return (left - right).sqrMagnitude <= 0.000001f;
        }

        private static bool Approximately(Color left, Color right)
        {
            return Approximately((Vector4)left, (Vector4)right);
        }

        private static bool Approximately(float left, float right)
        {
            return Mathf.Abs(left - right) <= 0.000001f;
        }

        private static bool Approximately(uint left, uint right)
        {
            return left == right;
        }

        private void FillSourceManualParticleReport(
            CaptureReport report, CaptureMode captureMode)
        {
            report.sourceManualParticleOverride =
                captureMode == CaptureMode.SourceManualParticle;
            report.sourceManualParticleComponentIdentity = targetIdentity == null
                ? string.Empty
                : targetIdentity.hierarchy +
                    ";ParticleSystemPathID=" + targetIdentity.particleSystemPathId.ToString(
                        CultureInfo.InvariantCulture) +
                    ";ParticleSystemRendererPathID=" + targetIdentity.particleRendererPathId.ToString(
                        CultureInfo.InvariantCulture) +
                    ";MeshPathID=" + targetIdentity.meshPathId.ToString(
                        CultureInfo.InvariantCulture) +
                    ";MaterialPathID=" + targetIdentity.materialPathId.ToString(
                        CultureInfo.InvariantCulture);
            report.sourceManualParticleRenderMode = targetRenderer != null
                ? targetRenderer.renderMode.ToString()
                : string.Empty;
            Material material = targetRenderer != null ? targetRenderer.sharedMaterial : null;
            report.sourceManualParticleMaterialName = material != null
                ? material.name
                : string.Empty;
            report.sourceManualParticleMaterialShaderName = material != null &&
                material.shader != null
                ? material.shader.name
                : string.Empty;
            report.sourceManualParticleMeshExactTargetMesh = targetRenderer != null &&
                sourceMeshBeforeOverride != null && targetRenderer.mesh == sourceMeshBeforeOverride;
            report.sourceManualParticleMeshName = targetRenderer != null && targetRenderer.mesh != null
                ? targetRenderer.mesh.name
                : string.Empty;
            report.sourceManualParticleVisible = report.sourceManualParticleOverride &&
                targetRenderer != null && targetRenderer.isVisible;
            report.sourceManualParticleContract =
                "exact source ParticleSystem + ParticleSystemRenderer; one explicit white " +
                "local-origin particle; compatibility material; basic Position/Normal/Color/UV " +
                "streams; no BakeMesh; no MeshRenderer proxy; source visual parity not claimed";

            if (!report.sourceManualParticleOverride || targetSystem == null)
                return;

            ParticleSystem.Particle[] particles = new ParticleSystem.Particle[1];
            int count = targetSystem.GetParticles(particles);
            report.sourceManualParticleCount = count;
            if (count <= 0)
            {
                report.sourceManualParticleAdmission = false;
                return;
            }

            ParticleSystem.Particle particle = particles[0];
            Color32 startColor = particle.startColor;
            report.sourceManualParticlePosition = particle.position;
            report.sourceManualParticleStartColor = new Color(
                startColor.r / 255.0f,
                startColor.g / 255.0f,
                startColor.b / 255.0f,
                startColor.a / 255.0f);
            report.sourceManualParticleStartLifetime = particle.startLifetime;
            report.sourceManualParticleRemainingLifetime = particle.remainingLifetime;
            report.sourceManualParticleAtLocalOrigin = particle.position == Vector3.zero;
            report.sourceManualParticleWhite = startColor.r == 255 && startColor.g == 255 &&
                startColor.b == 255 && startColor.a == 255;
            report.sourceManualParticleAdmission =
                report.sourceManualParticleOverride && report.exactIdentityClosed &&
                report.noBakeMeshContract && report.noProxyContract &&
                !report.targetHasMeshFilter && !report.targetHasMeshRenderer &&
                report.targetGameObjectActive && report.targetRendererEnabled &&
                sourceManualParticlePublished && report.sourceManualParticleCount == 1 &&
                report.sourceManualParticleAtLocalOrigin && report.sourceManualParticleWhite &&
                report.sourceManualParticleStartLifetime > 0.0f &&
                report.sourceManualParticleRemainingLifetime > 0.0f &&
                report.sourceManualParticleMeshExactTargetMesh && report.targetRendererMeshMode &&
                report.diagnosticCompatibilityMaterialOverride &&
                report.materialShaderSupported && report.materialPassCount > 0 &&
                report.activeVertexStreamIds.SequenceEqual(new[] { 0, 1, 3, 4 }) &&
                IsFinite(report.targetBoundsCenter) && IsFinite(report.targetBoundsExtents) &&
                report.publicFrustumIntersectsBounds && report.sourceManualParticleVisible;
        }

        private static void FillDirectCameraReport(
            CaptureReport report, Camera camera)
        {
            report.directCameraMainGameObjectActive = camera != null &&
                camera.gameObject.activeInHierarchy;
            report.directCameraMainEnabled = camera != null && camera.enabled;
            report.directCameraMainActiveAndEnabled = camera != null &&
                camera.isActiveAndEnabled;
            report.directCameraMainPixelWidth = camera != null ? camera.pixelWidth : 0;
            report.directCameraMainPixelHeight = camera != null ? camera.pixelHeight : 0;
            report.directCameraMainCullingMask = camera != null ? camera.cullingMask : 0;
            report.directCameraMainHasTargetTexture = camera != null &&
                camera.targetTexture != null;
            report.directCameraMainAllCamerasCount = Camera.allCamerasCount;
        }

        private void RequestForegroundWindowIfRequested()
        {
            if (!foregroundWindowRequested)
                return;

#if UNITY_STANDALONE_WIN
            foregroundWindowPlatformSupported = true;
            try
            {
                IntPtr handle;
                using (Process process = Process.GetCurrentProcess())
                    handle = process.MainWindowHandle;
                if (handle == IntPtr.Zero)
                    handle = GetActiveWindow();

                foregroundWindowHandle = handle.ToInt64();
                foregroundWindowHandleNonZero = handle != IntPtr.Zero;
                if (!foregroundWindowHandleNonZero)
                {
                    foregroundWindowFailure =
                        "The standalone player HWND was zero (MainWindowHandle/GetActiveWindow).";
                    return;
                }

                foregroundWindowIsWindow = IsWindow(handle);
                if (!foregroundWindowIsWindow)
                {
                    foregroundWindowFailure = "The obtained player HWND is not a live window.";
                    return;
                }

                foregroundWindowShowWindowCalled = true;
                foregroundWindowShowWindowResult = ShowWindow(handle, ShowWindowRestore);
                foregroundWindowSetForegroundWindowCalled = true;
                foregroundWindowSetForegroundWindowResult = SetForegroundWindow(handle);
                if (!foregroundWindowSetForegroundWindowResult)
                {
                    foregroundWindowFailure =
                        "SetForegroundWindow returned false; Win32Error=" +
                        Marshal.GetLastWin32Error().ToString(CultureInfo.InvariantCulture) + ".";
                }
            }
            catch (Exception exception)
            {
                foregroundWindowFailure = exception.GetType().FullName + ": " + exception.Message;
            }
#else
            foregroundWindowFailure =
                "The foreground-window diagnostic is supported only in a Windows standalone player.";
#endif
        }

        private void FillControlReport(
            CaptureReport report, Camera captureCamera, CaptureMode captureMode)
        {
            report.controlCreated = controlObject != null && controlSystem != null &&
                controlRenderer != null;
            report.controlSerializedPreExisting = controlWasSerialized;
            report.controlRuntimeCreated = !controlWasSerialized && report.controlCreated;
            report.controlGameObjectActive = controlObject != null &&
                controlObject.activeInHierarchy;
            report.controlRendererEnabled = controlRenderer != null && controlRenderer.enabled;
            report.controlRendererVisible = controlRenderer != null && controlRenderer.isVisible;
            report.controlRendererDisabledOverride =
                controlCaptureMode == CaptureMode.ControlDisabled ||
                controlCaptureMode == CaptureMode.SerializedControlDisabled;
            report.controlMeshModeOverride = controlCaptureMode == CaptureMode.MeshControl;
            report.controlRenderMode = controlRenderer != null
                ? controlRenderer.renderMode.ToString()
                : string.Empty;
            Mesh controlMesh = controlRenderer != null ? controlRenderer.mesh : null;
            Mesh targetMesh = targetRenderer != null ? targetRenderer.mesh : null;
            report.controlSharedMeshExactTargetMesh = controlMesh != null &&
                targetMesh != null && controlMesh == targetMesh;
            report.controlMeshName = controlMesh != null ? controlMesh.name : string.Empty;
            report.controlTargetMeshName = targetMesh != null ? targetMesh.name : string.Empty;
            report.controlMeshInstanceId = controlMesh != null ? controlMesh.GetInstanceID() : 0;
            report.controlTargetMeshInstanceId = targetMesh != null
                ? targetMesh.GetInstanceID()
                : 0;
            report.controlParticleCount = controlSystem != null ? controlSystem.particleCount : 0;
            Bounds bounds = controlRenderer != null ? controlRenderer.bounds : new Bounds();
            report.controlBoundsCenter = bounds.center;
            report.controlBoundsExtents = bounds.extents;
            report.controlBoundsFinite = controlRenderer != null &&
                IsFinite(bounds.center) && IsFinite(bounds.extents);
            report.controlFrustumIntersectsBounds = captureCamera != null &&
                report.controlBoundsFinite && GeometryUtility.TestPlanesAABB(
                    GeometryUtility.CalculateFrustumPlanes(captureCamera), bounds);
            Material material = controlRenderer != null ? controlRenderer.sharedMaterial : null;
            report.controlMaterialShaderSupported = material != null &&
                material.shader != null && material.shader.isSupported;
            report.controlMaterialPassCount = material != null ? material.passCount : 0;
            report.controlMaterialRenderQueue = material != null ? material.renderQueue : -1;
            report.controlMaterialName = material != null ? material.name : string.Empty;
            report.controlMaterialShaderName = material != null && material.shader != null
                ? material.shader.name : string.Empty;
            report.controlMaterialPurpose = controlCaptureMode == CaptureMode.BuiltinPipeline ||
                controlCaptureMode == CaptureMode.ExplicitCameraRender
                ? "built-in differential only; shader parity not claimed"
                : "HG SRP compatibility control";
            report.controlHasMeshFilter = controlObject != null &&
                controlObject.GetComponent<MeshFilter>() != null;
            report.controlHasMeshRenderer = controlObject != null &&
                controlObject.GetComponent<MeshRenderer>() != null;
            report.controlContract = (controlWasSerialized
                ? "serialized ParticleSystemRenderer; "
                : "runtime ParticleSystemRenderer; ") +
                (controlCaptureMode == CaptureMode.MeshControl
                    ? "Mesh mode using the exact source target mesh; "
                    : "Billboard mode; ") +
                "Emit(1); known-good compatibility material; " +
                "no BakeMesh; no MeshRenderer/MeshFilter proxy; source target untouched";
            report.controlAdmission = report.controlCreated && report.controlGameObjectActive &&
                report.controlRendererEnabled && report.controlRendererVisible &&
                report.controlParticleCount > 0 && report.controlBoundsFinite &&
                report.controlFrustumIntersectsBounds && report.controlMaterialShaderSupported &&
                report.controlMaterialPassCount > 0 && !report.controlHasMeshFilter &&
                !report.controlHasMeshRenderer;
            FillSentinelReport(report, captureCamera, captureMode);
        }

        private void FillSentinelReport(
            CaptureReport report, Camera captureCamera, CaptureMode captureMode)
        {
            report.sentinelSerializedPreExisting = serializedSentinelFilter != null &&
                serializedSentinelRenderer != null;
            report.sentinelEnabled = serializedSentinelRenderer != null &&
                serializedSentinelRenderer.enabled;
            report.sentinelVisible = serializedSentinelRenderer != null &&
                serializedSentinelRenderer.isVisible;
            report.sentinelDisabledOverride = captureMode == CaptureMode.SentinelDisabled;
            Bounds bounds = serializedSentinelRenderer != null
                ? serializedSentinelRenderer.bounds
                : new Bounds();
            report.sentinelBoundsCenter = bounds.center;
            report.sentinelBoundsExtents = bounds.extents;
            report.sentinelBoundsFinite = serializedSentinelRenderer != null &&
                IsFinite(bounds.center) && IsFinite(bounds.extents);
            report.sentinelFrustumIntersectsBounds = captureCamera != null &&
                report.sentinelBoundsFinite && GeometryUtility.TestPlanesAABB(
                    GeometryUtility.CalculateFrustumPlanes(captureCamera), bounds);
            Material material = serializedSentinelRenderer != null
                ? serializedSentinelRenderer.sharedMaterial
                : null;
            report.sentinelMaterialShaderSupported = material != null &&
                material.shader != null && material.shader.isSupported;
            report.sentinelMaterialPassCount = material != null ? material.passCount : 0;
            report.sentinelMaterialRenderQueue = material != null ? material.renderQueue : -1;
            report.sentinelMaterialName = material != null ? material.name : string.Empty;
            report.sentinelMaterialShaderName = material != null && material.shader != null
                ? material.shader.name : string.Empty;
            report.sentinelMeshName = serializedSentinelFilter != null &&
                serializedSentinelFilter.sharedMesh != null
                ? serializedSentinelFilter.sharedMesh.name : string.Empty;
            report.sentinelIdentity = serializedSentinelRenderer != null
                ? serializedSentinelRenderer.gameObject.name + "/" +
                    report.sentinelMeshName + "/MeshFilter+MeshRenderer"
                : string.Empty;
            report.sentinelContract =
                "serialized MeshFilter+MeshRenderer camera/culling sentinel only; " +
                "not a substitute for the source ParticleSystemRenderer";
            report.sentinelAdmission = report.sentinelSerializedPreExisting &&
                report.sentinelEnabled && report.sentinelVisible &&
                report.sentinelBoundsFinite && report.sentinelFrustumIntersectsBounds &&
                report.sentinelMaterialShaderSupported &&
                report.sentinelMaterialPassCount > 0;
        }

        private bool EvaluateStatus(CaptureReport report, CaptureMode captureMode)
        {
            bool expectedRenderMode = captureMode == CaptureMode.BillboardRenderMode
                ? !report.targetRendererMeshMode
                : report.targetRendererMeshMode;
            bool expectedStreams = captureMode == CaptureMode.BasicVertexStreams
                ? report.activeVertexStreamIds.SequenceEqual(new[] { 0, 1, 3, 4 })
                : report.activeVertexStreamIds.SequenceEqual(ExpectedStreams);
            bool identity = report.exactIdentityClosed && expectedRenderMode &&
                expectedStreams;
            bool noProxy = report.noBakeMeshContract && report.noProxyContract &&
                !report.targetHasMeshFilter && !report.targetHasMeshRenderer;
            if (captureMode == CaptureMode.ControlDisabled)
            {
                return report.graphicsDeviceType == GraphicsDeviceType.Direct3D11.ToString() &&
                    !report.applicationIsBatchMode && identity && noProxy &&
                    report.controlCreated && report.controlGameObjectActive &&
                    report.controlRendererDisabledOverride &&
                    !report.controlRendererEnabled && !report.controlRendererVisible &&
                    report.controlParticleCount > 0 && report.controlBoundsFinite &&
                    report.controlFrustumIntersectsBounds &&
                    report.controlMaterialShaderSupported && report.controlMaterialPassCount > 0 &&
                    !report.controlHasMeshFilter && !report.controlHasMeshRenderer;
            }
            if (captureMode == CaptureMode.SerializedControl)
            {
                return report.graphicsDeviceType == GraphicsDeviceType.Direct3D11.ToString() &&
                    !report.applicationIsBatchMode && identity && noProxy &&
                    report.controlSerializedPreExisting && report.controlAdmission;
            }
            if (captureMode == CaptureMode.SerializedControlDisabled)
            {
                return report.graphicsDeviceType == GraphicsDeviceType.Direct3D11.ToString() &&
                    !report.applicationIsBatchMode && identity && noProxy &&
                    report.controlSerializedPreExisting &&
                    report.controlRendererDisabledOverride &&
                    !report.controlRendererEnabled && !report.controlRendererVisible &&
                    report.controlParticleCount > 0 && report.controlBoundsFinite &&
                    report.controlFrustumIntersectsBounds &&
                    report.controlMaterialShaderSupported && report.controlMaterialPassCount > 0 &&
                    !report.controlHasMeshFilter && !report.controlHasMeshRenderer;
            }
            if (captureMode == CaptureMode.BuiltinPipeline)
            {
                return report.graphicsDeviceType == GraphicsDeviceType.Direct3D11.ToString() &&
                    !report.applicationIsBatchMode && identity && noProxy &&
                    report.controlAdmission &&
                    string.IsNullOrEmpty(report.currentRenderPipelineType);
            }
            if (captureMode == CaptureMode.ExplicitCameraRender)
            {
                return report.graphicsDeviceType == GraphicsDeviceType.Direct3D11.ToString() &&
                    !report.applicationIsBatchMode && identity && noProxy &&
                    report.explicitCameraRenderMode &&
                    report.explicitCameraRenderRequested &&
                    report.explicitCameraRenderExecuted &&
                    report.explicitCameraRenderCallCount == 1 &&
                    string.IsNullOrEmpty(report.explicitCameraRenderFailure) &&
                    !report.directCameraMainEnabled &&
                    report.controlAdmission && report.sentinelAdmission &&
                    string.IsNullOrEmpty(report.currentRenderPipelineType);
            }
            if (captureMode == CaptureMode.MeshControl)
            {
                return report.graphicsDeviceType == GraphicsDeviceType.Direct3D11.ToString() &&
                    !report.applicationIsBatchMode && noProxy &&
                    report.controlMeshModeOverride &&
                    report.controlRenderMode == ParticleSystemRenderMode.Mesh.ToString() &&
                    report.controlSharedMeshExactTargetMesh &&
                    report.controlMeshInstanceId != 0 &&
                    report.controlMeshInstanceId == report.controlTargetMeshInstanceId &&
                    !string.IsNullOrEmpty(report.controlMeshName) &&
                    report.controlMeshName == report.controlTargetMeshName &&
                    report.controlAdmission;
            }
            if (captureMode == CaptureMode.SourceManualParticle)
                return report.graphicsDeviceType == GraphicsDeviceType.Direct3D11.ToString() &&
                    !report.applicationIsBatchMode && report.sourceManualParticleAdmission;
            if (IsSourceFieldAblationMode(captureMode))
                return report.graphicsDeviceType == GraphicsDeviceType.Direct3D11.ToString() &&
                    !report.applicationIsBatchMode && report.sourceFieldAdmission;
            if (captureMode == CaptureMode.SourceRepublishIdentical)
                return report.graphicsDeviceType == GraphicsDeviceType.Direct3D11.ToString() &&
                    !report.applicationIsBatchMode && report.sourceRepublishAdmission;
            if (captureMode == CaptureMode.Positive ||
                captureMode == CaptureMode.SortingFudgeZero ||
                captureMode == CaptureMode.GpuInstancingOff ||
                captureMode == CaptureMode.RendererOcclusionOff ||
                captureMode == CaptureMode.CameraOcclusionOff ||
                captureMode == CaptureMode.BillboardRenderMode ||
                captureMode == CaptureMode.CompatibilityMaterial ||
                captureMode == CaptureMode.BasicVertexStreams ||
                captureMode == CaptureMode.NaturalPlayback ||
                captureMode == CaptureMode.DefaultLayer ||
                captureMode == CaptureMode.SentinelEnabled ||
                captureMode == CaptureMode.SentinelDisabled)
            {
                bool expectedMaterial = captureMode == CaptureMode.CompatibilityMaterial
                    ? report.diagnosticCompatibilityMaterialOverride &&
                        report.materialShaderSupported
                    : report.targetUsesDiagnosticMaterial;
                return report.graphicsDeviceType == GraphicsDeviceType.Direct3D11.ToString() &&
                    !report.applicationIsBatchMode && identity && noProxy &&
                    report.targetRendererEnabled && report.targetRendererVisible &&
                    report.particleCount > 0 && expectedMaterial &&
                    report.sourceRendererSubmissionPath;
            }
            if (captureMode == CaptureMode.TargetDisabled)
                return identity && noProxy && !report.targetRendererEnabled &&
                    report.particleCount == 0;
            return identity && noProxy && report.particleCount == 0;
        }

        private bool IdentityMatchesMarker(RendererIdentity identity)
        {
            EndfieldRecoveredParticleNodeSource node = sourceMarker.particleNodes.SingleOrDefault(
                value => value.hierarchy == identity.hierarchy);
            return node != null && node.particleSystemPathId == identity.particleSystemPathId &&
                node.particleRendererPathId == identity.particleRendererPathId &&
                node.meshPathIds != null && node.meshPathIds.Length == 1 &&
                node.meshPathIds[0] == identity.meshPathId &&
                node.materialPathIds != null && node.materialPathIds.Length == 1 &&
                node.materialPathIds[0] == identity.materialPathId;
        }

        private bool UsesDiagnosticMaterial(ParticleSystemRenderer renderer)
        {
            Material[] materials = renderer.sharedMaterials;
            return materials != null && materials.Length == 1 && materials[0] != null &&
                materials[0].name.IndexOf("Diagnostic", StringComparison.OrdinalIgnoreCase) >= 0;
        }

        private RendererIdentity IdentityFor(CaptureMode captureMode)
        {
            if (captureMode == CaptureMode.EmptyTarget)
                return new RendererIdentity
                {
                    hierarchy = ExpectedRoot + "/xuanzhuan04",
                    particleSystemPathId = 8348750931752523296L,
                    particleRendererPathId = 6551385765768926752L,
                    meshPathId = 5776537116290261507L,
                    materialPathId = -430604955415889784L,
                };
            return new RendererIdentity
            {
                hierarchy = ExpectedRoot + "/xuanzhuan03",
                particleSystemPathId = 2171212438583907872L,
                particleRendererPathId = 37981486576571936L,
                meshPathId = 5776537116290261507L,
                materialPathId = -430604955415889784L,
            };
        }

        private static Transform FindHierarchy(Transform root, string hierarchy)
        {
            string prefix = root.name + "/";
            string relative = hierarchy.StartsWith(prefix, StringComparison.Ordinal)
                ? hierarchy.Substring(prefix.Length)
                : hierarchy;
            return root.Find(relative);
        }

        private void PrepareOutputPath()
        {
            outputPath = Path.GetFullPath(outputPath);
            string directory = Path.GetDirectoryName(outputPath);
            if (!string.IsNullOrEmpty(directory))
                Directory.CreateDirectory(directory);
        }

        private void WriteReport(CaptureReport report)
        {
            if (reportWritten)
                return;
            reportWritten = true;
            try
            {
                File.WriteAllText(outputPath, JsonUtility.ToJson(report, true));
            }
            catch (Exception exception)
            {
                Debug.LogError("Li Zhiyan M23 ParticleSystemRenderer report write failed: " +
                    exception.GetType().FullName + ": " + exception.Message);
            }
            Debug.Log("Li Zhiyan M23 ParticleSystemRenderer capture: " +
                report.status + "; mode=" + report.mode + "; report=" + outputPath);
        }

        private static CaptureMode ParseMode(string value)
        {
            switch (NormalizeMode(value))
            {
                case "target-disabled": return CaptureMode.TargetDisabled;
                case "pre-delay": return CaptureMode.PreDelay;
                case "empty-target": return CaptureMode.EmptyTarget;
                case "sorting-fudge-zero": return CaptureMode.SortingFudgeZero;
                case "gpu-instancing-off": return CaptureMode.GpuInstancingOff;
                case "renderer-occlusion-off": return CaptureMode.RendererOcclusionOff;
                case "camera-occlusion-off": return CaptureMode.CameraOcclusionOff;
                case "billboard-render-mode": return CaptureMode.BillboardRenderMode;
                case "compatibility-material": return CaptureMode.CompatibilityMaterial;
                case "basic-vertex-streams": return CaptureMode.BasicVertexStreams;
                case "natural-playback": return CaptureMode.NaturalPlayback;
                case "default-layer": return CaptureMode.DefaultLayer;
                case "builtin-pipeline": return CaptureMode.BuiltinPipeline;
                case "control-disabled": return CaptureMode.ControlDisabled;
                case "serialized-control": return CaptureMode.SerializedControl;
                case "serialized-control-disabled": return CaptureMode.SerializedControlDisabled;
                case "sentinel-enabled": return CaptureMode.SentinelEnabled;
                case "sentinel-disabled": return CaptureMode.SentinelDisabled;
                case "explicit-camera-render": return CaptureMode.ExplicitCameraRender;
                case "mesh-control": return CaptureMode.MeshControl;
                case "source-manual-particle": return CaptureMode.SourceManualParticle;
                case "source-field-lifetime": return CaptureMode.SourceFieldLifetime;
                case "source-field-size": return CaptureMode.SourceFieldSize;
                case "source-field-color": return CaptureMode.SourceFieldColor;
                case "source-field-rotation": return CaptureMode.SourceFieldRotation;
                case "source-field-velocity": return CaptureMode.SourceFieldVelocity;
                case "source-field-custom1": return CaptureMode.SourceFieldCustom1;
                case "source-republish-identical": return CaptureMode.SourceRepublishIdentical;
                default: return CaptureMode.Positive;
            }
        }

        private static bool IsSourceFieldAblationMode(CaptureMode captureMode)
        {
            return captureMode == CaptureMode.SourceFieldLifetime ||
                captureMode == CaptureMode.SourceFieldSize ||
                captureMode == CaptureMode.SourceFieldColor ||
                captureMode == CaptureMode.SourceFieldRotation ||
                captureMode == CaptureMode.SourceFieldVelocity ||
                captureMode == CaptureMode.SourceFieldCustom1;
        }

        private static SourceFieldFamily SourceFieldFamilyForMode(CaptureMode captureMode)
        {
            switch (captureMode)
            {
                case CaptureMode.SourceFieldLifetime: return SourceFieldFamily.Lifetime;
                case CaptureMode.SourceFieldSize: return SourceFieldFamily.Size;
                case CaptureMode.SourceFieldColor: return SourceFieldFamily.Color;
                case CaptureMode.SourceFieldRotation: return SourceFieldFamily.Rotation;
                case CaptureMode.SourceFieldVelocity: return SourceFieldFamily.Velocity;
                case CaptureMode.SourceFieldCustom1: return SourceFieldFamily.Custom1;
                default: return SourceFieldFamily.None;
            }
        }

        private static string SourceFieldFamilyName(SourceFieldFamily family)
        {
            switch (family)
            {
                case SourceFieldFamily.Lifetime: return "lifetime";
                case SourceFieldFamily.Size: return "size";
                case SourceFieldFamily.Color: return "color";
                case SourceFieldFamily.Rotation: return "rotation-axis";
                case SourceFieldFamily.Velocity: return "velocity";
                case SourceFieldFamily.Custom1: return "custom1";
                default: return string.Empty;
            }
        }

        private static string NormalizeMode(string value)
        {
            return string.IsNullOrWhiteSpace(value) ? "positive" : value.Trim().ToLowerInvariant();
        }

        private static string NegativeExpectation(string value)
        {
            switch (NormalizeMode(value))
            {
                case "target-disabled": return "target renderer disabled: zero target particles/draws";
                case "pre-delay": return "before source effect delay: zero target particles/draws";
                case "empty-target": return "xuanzhuan04 at PTS 40000: zero target particles/draws";
                case "sorting-fudge-zero": return "causal diagnostic: zero sorting fudge permits the target draw";
                case "gpu-instancing-off": return "causal diagnostic: disabling source GPU instancing permits the target draw";
                case "renderer-occlusion-off": return "causal diagnostic: dynamic renderer occlusion disabled";
                case "camera-occlusion-off": return "causal diagnostic: camera occlusion culling disabled";
                case "billboard-render-mode": return "causal diagnostic: source Mesh mode replaced by Billboard";
                case "compatibility-material": return "causal diagnostic: source material replaced by known-good SRP unlit";
                case "basic-vertex-streams": return "causal diagnostic: active streams reduced to Position/Normal/Color/UV";
                case "natural-playback": return "causal diagnostic: ordinary Play without manual Simulate";
                case "default-layer": return "causal diagnostic: target on layer 0 with full camera mask";
                case "builtin-pipeline": return "differential only: built-in control draw; source shader parity not claimed";
                case "control-disabled": return "negative control: identical runtime control renderer disabled; zero control draw expected";
                case "serialized-control": return "serialized control: pre-existing ParticleSystemRenderer must be admitted";
                case "serialized-control-disabled": return "serialized negative control: pre-existing renderer disabled; zero control draw expected";
                case "sentinel-enabled": return "camera/culling sentinel enabled; particle controls unchanged";
                case "sentinel-disabled": return "camera/culling sentinel disabled; particle controls unchanged";
                case "explicit-camera-render": return "built-in differential: automatic camera disabled; Camera.Render called exactly once; source shader parity not claimed";
                case "mesh-control": return "control-only diagnostic: runtime ParticleSystemRenderer Mesh mode using the exact source mesh; source parity not claimed";
                case "source-manual-particle": return "component-admission diagnostic: exact source ParticleSystemRenderer with one explicit white local-origin particle; source visual parity not claimed";
                case "source-field-lifetime": return "bounded source-field ablation: only lifetime fields replaced after original particle capture";
                case "source-field-size": return "bounded source-field ablation: only size fields replaced after original particle capture";
                case "source-field-color": return "bounded source-field ablation: only color fields replaced after original particle capture";
                case "source-field-rotation": return "bounded source-field ablation: only rotation/axis/angular-velocity fields replaced after original particle capture";
                case "source-field-velocity": return "bounded source-field ablation: only velocity fields replaced after original particle capture";
                case "source-field-custom1": return "bounded source-field ablation: only Custom1 data replaced after original particle capture";
                case "source-republish-identical": return "component-admission differential: original particle rows and Custom1 republished without field changes";
                default: return "positive: target renderer must be visible with particles";
            }
        }

        private static int ReadBoundedInteger(string value, int fallback, int maximum)
        {
            int parsed;
            return int.TryParse(value, NumberStyles.Integer, CultureInfo.InvariantCulture, out parsed)
                ? Mathf.Clamp(parsed, 0, maximum)
                : fallback;
        }

        private static bool IsFinite(Vector3 value)
        {
            return !float.IsNaN(value.x) && !float.IsInfinity(value.x) &&
                !float.IsNaN(value.y) && !float.IsInfinity(value.y) &&
                !float.IsNaN(value.z) && !float.IsInfinity(value.z);
        }

        private static string FormatFloat(float value)
        {
            if (float.IsNaN(value))
                return "NaN";
            if (float.IsPositiveInfinity(value))
                return "+Infinity";
            if (float.IsNegativeInfinity(value))
                return "-Infinity";
            return value.ToString("R", CultureInfo.InvariantCulture);
        }

        private static bool HasArgument(string[] arguments, string name)
        {
            return arguments.Any(value => string.Equals(value, name, StringComparison.OrdinalIgnoreCase));
        }

        private static string ReadArgument(string[] arguments, string name)
        {
            string prefix = name + "=";
            for (int index = 0; index < arguments.Length; index++)
            {
                if (arguments[index].StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                    return arguments[index].Substring(prefix.Length);
                if (string.Equals(arguments[index], name, StringComparison.OrdinalIgnoreCase) &&
                    index + 1 < arguments.Length)
                    return arguments[index + 1];
            }
            return null;
        }

        private static void Require(bool condition, string message)
        {
            if (!condition)
                throw new InvalidOperationException(message);
        }
    }
}
