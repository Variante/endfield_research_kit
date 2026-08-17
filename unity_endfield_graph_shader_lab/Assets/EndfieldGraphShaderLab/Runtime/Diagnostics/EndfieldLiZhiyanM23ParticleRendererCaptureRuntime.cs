using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
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
        public sealed class CaptureReport
        {
            public string schema = "endfield.lizhiyan-m23-particle-renderer-capture.v1";
            public string status;
            public string failure;
            public string mode;
            public string unityVersion;
            public string graphicsDeviceType;
            public bool applicationIsBatchMode;
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
            public bool recoveredSceneMVRequested;
            public string recoveredSceneMVRequestFailure;
            public bool recoveredSceneMVDescriptorCreated;
            public bool recoveredAfterPostExecuted;
            public bool targetRendererMeshMode;
            public bool targetUsesDiagnosticMaterial;
            public bool targetHasMeshFilter;
            public bool targetHasMeshRenderer;
            public int particleCount;
            public int[] activeVertexStreamIds;
            public string[] activeVertexStreams;
            public bool controlCreated;
            public bool controlGameObjectActive;
            public bool controlRendererEnabled;
            public bool controlRendererVisible;
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
            public bool controlHasMeshFilter;
            public bool controlHasMeshRenderer;
            public string controlContract;
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
        }

        public void ConfigureCompatibilityMaterial(Material material)
        {
            compatibilityMaterial = material;
        }

        private void Awake()
        {
            sourceMarker = GetComponent<EndfieldRecoveredParticleEffectSource>();
        }

        private void Start()
        {
            string[] arguments = Environment.GetCommandLineArgs();
            if (!HasArgument(arguments, ActivationArgument))
                return;

            Application.targetFrameRate = 60;
            QualitySettings.vSyncCount = 0;
            Shader.SetGlobalFloat("_EndfieldSceneMVMRTReady", 1.0f);
            Shader.SetGlobalFloat("_EndfieldRecoveredVFXGlobalsReady", 1.0f);
            Shader.SetGlobalFloat("_EndfieldRecoveredVFXSoftDepthReady", 0.0f);
            Shader.SetGlobalVector("_ExposureParams", new Vector4(1.0f, 0.0f, 0.0f, 0.0f));

            mode = NormalizeMode(ReadArgument(arguments, ModeArgument));
            quitAfterCapture = HasArgument(arguments, QuitArgument);
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
                targetIdentity = IdentityFor(captureMode);
                BuildSourceMaps();
                ConfigureRenderers(captureMode);
                Require(targetRenderer != null && targetSystem != null,
                    "The selected M23 ParticleSystemRenderer target is missing.");
                Require(targetRenderer.GetComponent<MeshFilter>() == null &&
                    targetRenderer.GetComponent<MeshRenderer>() == null,
                    "The target hierarchy unexpectedly contains a mesh proxy component.");
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
                if (captureMode == CaptureMode.NaturalPlayback)
                {
                    simulationSeconds = 0.0f;
                    ResetAndPlayNaturally(targetSystem);
                }
                else if (captureMode != CaptureMode.TargetDisabled)
                    ResetAndSimulate(targetSystem, simulationSeconds);
                else
                    setupPassed = true;
                CreatePositiveControl();
                ConfigureCaptureCamera();
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
            yield return new WaitForEndOfFrame();

            try
            {
                FillReport(report, captureMode);
                report.status = EvaluateStatus(report, captureMode) ? "pass" : "fail";
                if (report.status != "pass")
                    report.failure = "Runtime source-renderer acceptance gate failed.";
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

        private void CreatePositiveControl()
        {
            Require(compatibilityMaterial != null &&
                compatibilityMaterial.shader != null &&
                compatibilityMaterial.shader.isSupported,
                "The positive-control compatibility material is missing or unsupported.");

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
            controlRenderer.sharedMaterial = compatibilityMaterial;
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

        private void FillReport(CaptureReport report, CaptureMode captureMode)
        {
            report.mode = mode;
            report.frameCountAtCapture = Time.frameCount;
            report.framesAfterSetup = framesAfterSetup;
            report.sourceEffectDelay = sourceMarker.sourceEffectDelay;
            report.targetLocalSeconds = simulationSeconds;
            report.targetGameObjectActive = targetSystem.gameObject.activeInHierarchy;
            report.targetRendererEnabled = targetRenderer.enabled;
            report.targetRendererVisible = targetRenderer.isVisible;
            Camera captureCamera = Camera.main;
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
                captureMode == CaptureMode.CompatibilityMaterial;
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
            EndfieldRecoveredSceneMVDiagnosticState sceneMV =
                HDRenderPipeline.LastRecoveredSceneMVDiagnostic;
            report.recoveredSceneMVRequested = sceneMV.requested;
            report.recoveredSceneMVRequestFailure = sceneMV.requestFailure;
            report.recoveredSceneMVDescriptorCreated = sceneMV.descriptorCreated;
            report.recoveredAfterPostExecuted =
                sceneMV.afterPostSceneMVLoadStoreNoClear;
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
            FillControlReport(report, captureCamera);
        }

        private void FillControlReport(CaptureReport report, Camera captureCamera)
        {
            report.controlCreated = controlObject != null && controlSystem != null &&
                controlRenderer != null;
            report.controlGameObjectActive = controlObject != null &&
                controlObject.activeInHierarchy;
            report.controlRendererEnabled = controlRenderer != null && controlRenderer.enabled;
            report.controlRendererVisible = controlRenderer != null && controlRenderer.isVisible;
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
            report.controlHasMeshFilter = controlObject != null &&
                controlObject.GetComponent<MeshFilter>() != null;
            report.controlHasMeshRenderer = controlObject != null &&
                controlObject.GetComponent<MeshRenderer>() != null;
            report.controlContract =
                "runtime ParticleSystemRenderer; Emit(1); known-good compatibility material; " +
                "no BakeMesh; no MeshRenderer/MeshFilter proxy; source target untouched";
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
            if (captureMode == CaptureMode.Positive ||
                captureMode == CaptureMode.SortingFudgeZero ||
                captureMode == CaptureMode.GpuInstancingOff ||
                captureMode == CaptureMode.RendererOcclusionOff ||
                captureMode == CaptureMode.CameraOcclusionOff ||
                captureMode == CaptureMode.BillboardRenderMode ||
                captureMode == CaptureMode.CompatibilityMaterial ||
                captureMode == CaptureMode.BasicVertexStreams ||
                captureMode == CaptureMode.NaturalPlayback ||
                captureMode == CaptureMode.DefaultLayer)
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
                default: return CaptureMode.Positive;
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
