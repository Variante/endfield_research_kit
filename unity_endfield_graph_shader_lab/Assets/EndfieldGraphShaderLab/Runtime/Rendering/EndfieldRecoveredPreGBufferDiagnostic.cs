using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Default-off, offscreen reconstruction of the source-backed character
    /// PreGBuffer producer boundary. It does not feed lighting or the screen
    /// shadow resolve. Its resources exist only for RenderDoc inspection and a
    /// one-shot deterministic GPU readback/value audit.
    /// </summary>
    internal sealed class EndfieldRecoveredPreGBufferDiagnostic : IDisposable
    {
        internal const string EnvironmentVariable =
            "ENDFIELD_RECOVERED_PREGBUFFER_DIAGNOSTIC";
        internal const string CommandLineArgument =
            "-endfield-recovered-pregbuffer-diagnostic";
        internal const string OutputEnvironmentVariable =
            "ENDFIELD_RECOVERED_PREGBUFFER_DIAGNOSTIC_OUTPUT";
        internal const string OutputCommandLineArgument =
            "-endfield-recovered-pregbuffer-diagnostic-output";

        private const string CharacterPassName =
            "RECOVERED_PREGBUFFER_DIAGNOSTIC";
        private const string DepthOnlyShaderName =
            "Hidden/Endfield/HGRPCompat/RecoveredPreGBufferDepthOnly";
        private const string UtilityShaderName =
            "Hidden/Endfield/HGRPCompat/RecoveredPreGBufferUtility";
        private const int MaximumCharacterCount = 15;
        private const int ValidationWarmupFrames = 2;
        private const int ExactFloatIntegerLimit = 1 << 24;

        private static readonly GraphicsFormat OriginalDepthStencilIntent =
            GraphicsFormat.D32_SFloat_S8_UInt;
        private static readonly GraphicsFormat ExactGBufferFormat =
            GraphicsFormat.A2B10G10R10_UNormPack32;
        private static readonly GraphicsFormat ExactGBufferCFormat =
            GraphicsFormat.R8G8B8A8_SRGB;
        private static readonly GraphicsFormat ExactDepthCopyFormat =
            GraphicsFormat.R32_SFloat;
        private static readonly GraphicsFormat StencilMaskFormat =
            GraphicsFormat.R8_UNorm;
        private static readonly GraphicsFormat SameOwnerFormat =
            GraphicsFormat.R32G32B32A32_SFloat;

        private static readonly int DepthStencilId =
            Shader.PropertyToID("_EndfieldRecoveredPreGBufferDepthStencil");
        private static readonly int DepthCopyId =
            Shader.PropertyToID("_EndfieldRecoveredPreGBufferDepthCopy");
        private static readonly int GBufferAId =
            Shader.PropertyToID("_EndfieldRecoveredPreGBufferA");
        private static readonly int GBufferBId =
            Shader.PropertyToID("_EndfieldRecoveredPreGBufferB");
        private static readonly int GBufferCId =
            Shader.PropertyToID("_EndfieldRecoveredPreGBufferC");
        private static readonly int SameOwnerId =
            Shader.PropertyToID("_EndfieldRecoveredPreGBufferOwner");
        private static readonly int StencilMaskId =
            Shader.PropertyToID("_EndfieldRecoveredPreGBufferStencilMask");
        private static readonly int ReadyId =
            Shader.PropertyToID("_EndfieldRecoveredPreGBufferReady");
        private static readonly int TexelSizeId =
            Shader.PropertyToID("_EndfieldRecoveredPreGBufferTexelSize");
        private static readonly int SelectorBitsId =
            Shader.PropertyToID("_EndfieldRecoveredPreGBufferSelectorBits");
        private static readonly int LogicalDrawId =
            Shader.PropertyToID("_EndfieldRecoveredLogicalDrawId");

        private static readonly Dictionary<string, int> SupportedFamilyCodes =
            new Dictionary<string, int>(StringComparer.Ordinal)
            {
                { "Endfield/Recovered/CharacterCloth", 0 },
                { "Endfield/Recovered/CharacterSkin", 1 },
                { "Endfield/Recovered/CharacterEye", 2 },
                { "Endfield/Recovered/CharacterHair", 3 }
            };

        private readonly bool standaloneRequested;
        private readonly bool producerRequired;
        private readonly bool sameOwnerRequired;
        private readonly bool stencilSamplingRequired;
        private readonly string outputDirectory;
        private readonly Dictionary<Camera, CameraResources> cameraResources =
            new Dictionary<Camera, CameraResources>();
        private Material depthOnlyMaterial;
        private Material utilityMaterial;
        private bool loggedActive;
        private bool loggedFailure;
        private bool disposed;

        /// <summary>
        /// Immutable, non-owning view of one completed sidecar frame. The
        /// textures remain owned by this diagnostic and are valid only until
        /// the same camera is rendered again or the producer is disposed.
        /// </summary>
        internal readonly struct LogicalDrawInfo
        {
            internal readonly Renderer renderer;
            internal readonly Material material;
            internal readonly int submesh;
            internal readonly uint logicalDrawId;
            internal readonly int familyCode;
            internal readonly int renderQueue;
            internal readonly bool preGEligible;
            internal readonly int preGPass;
            internal readonly int forwardPass;
            internal readonly string stableKey;
            internal readonly string rendererPath;
            internal readonly string shaderName;
            internal readonly string materialName;

            internal LogicalDrawInfo(
                Renderer renderer,
                Material material,
                int submesh,
                uint logicalDrawId,
                int familyCode,
                int renderQueue,
                bool preGEligible,
                int preGPass,
                int forwardPass,
                string stableKey)
            {
                this.renderer = renderer;
                this.material = material;
                this.submesh = submesh;
                this.logicalDrawId = logicalDrawId;
                this.familyCode = familyCode;
                this.renderQueue = renderQueue;
                this.preGEligible = preGEligible;
                this.preGPass = preGPass;
                this.forwardPass = forwardPass;
                this.stableKey = stableKey ?? string.Empty;
                rendererPath = renderer == null
                    ? string.Empty
                    : BuildTransformPath(renderer.transform);
                shaderName = material == null || material.shader == null
                    ? string.Empty
                    : material.shader.name;
                materialName = material == null ? string.Empty : material.name;
            }
        }

        internal readonly struct Frame
        {
            internal readonly bool ready;
            internal readonly string failure;
            internal readonly int cameraInstanceId;
            internal readonly int width;
            internal readonly int height;
            internal readonly RenderTexture depthStencil;
            internal readonly RenderTexture depthCopy;
            internal readonly RenderTexture gBufferA;
            internal readonly RenderTexture gBufferB;
            internal readonly RenderTexture gBufferC;
            internal readonly RenderTexture sameOwner;
            internal readonly RenderTexture stencilValidationMask;
            internal readonly bool sameOwnerReady;
            internal readonly LogicalDrawInfo[] logicalDraws;
            internal readonly GraphicsFormat depthStencilFormat;
            internal readonly bool exactDepthStencilFormat;
            internal readonly Matrix4x4 inverseGpuViewProjection;
            internal readonly int characterActorCount;
            internal readonly int slot0ActorRootInstanceId;
            internal readonly string slot0ActorRootPath;
            internal readonly uint slot0SelectorBits;
            internal readonly int characterDrawCount;
            internal readonly string[] blockedMaterialPasses;

            internal Frame(
                bool ready,
                string failure,
                int cameraInstanceId,
                int width,
                int height,
                RenderTexture depthStencil,
                RenderTexture depthCopy,
                RenderTexture gBufferA,
                RenderTexture gBufferB,
                RenderTexture gBufferC,
                RenderTexture sameOwner,
                RenderTexture stencilValidationMask,
                GraphicsFormat depthStencilFormat,
                Matrix4x4 inverseGpuViewProjection,
                int characterActorCount,
                int slot0ActorRootInstanceId,
                string slot0ActorRootPath,
                uint slot0SelectorBits,
                int characterDrawCount,
                string[] blockedMaterialPasses,
                bool sameOwnerReady,
                LogicalDrawInfo[] logicalDraws)
            {
                this.ready = ready;
                this.failure = failure ?? string.Empty;
                this.cameraInstanceId = cameraInstanceId;
                this.width = width;
                this.height = height;
                this.depthStencil = depthStencil;
                this.depthCopy = depthCopy;
                this.gBufferA = gBufferA;
                this.gBufferB = gBufferB;
                this.gBufferC = gBufferC;
                this.sameOwner = sameOwner;
                this.stencilValidationMask = stencilValidationMask;
                this.sameOwnerReady = sameOwnerReady;
                this.logicalDraws = logicalDraws ?? Array.Empty<LogicalDrawInfo>();
                this.depthStencilFormat = depthStencilFormat;
                exactDepthStencilFormat =
                    depthStencilFormat == OriginalDepthStencilIntent;
                this.inverseGpuViewProjection = inverseGpuViewProjection;
                this.characterActorCount = characterActorCount;
                this.slot0ActorRootInstanceId = slot0ActorRootInstanceId;
                this.slot0ActorRootPath = slot0ActorRootPath ?? string.Empty;
                this.slot0SelectorBits = slot0SelectorBits;
                this.characterDrawCount = characterDrawCount;
                this.blockedMaterialPasses =
                    blockedMaterialPasses ?? Array.Empty<string>();
            }

            internal static Frame Unavailable(string failure)
            {
                return new Frame(
                    false,
                    failure,
                    0,
                    0,
                    0,
                    null,
                    null,
                    null,
                    null,
                    null,
                    null,
                    null,
                    GraphicsFormat.None,
                    Matrix4x4.identity,
                    0,
                    0,
                    string.Empty,
                    0u,
                    0,
                    Array.Empty<string>(),
                    false,
                    Array.Empty<LogicalDrawInfo>());
            }
        }

        private sealed class CameraResources : IDisposable
        {
            internal int width;
            internal int height;
            internal GraphicsFormat depthStencilFormat;
            internal RenderTexture depthStencil;
            internal RenderTexture depthCopy;
            internal RenderTexture gBufferA;
            internal RenderTexture gBufferB;
            internal RenderTexture gBufferC;
            internal RenderTexture sameOwner;
            internal RenderTexture stencilMask;
            internal int renderedFrames;
            internal bool readbackPending;
            internal bool validationComplete;
            internal bool disposed;

            public void Dispose()
            {
                disposed = true;
                Release(ref depthStencil);
                Release(ref depthCopy);
                Release(ref gBufferA);
                Release(ref gBufferB);
                Release(ref gBufferC);
                Release(ref sameOwner);
                Release(ref stencilMask);
            }

            private static void Release(ref RenderTexture texture)
            {
                if (texture == null)
                    return;
                texture.Release();
                if (Application.isPlaying)
                    UnityEngine.Object.Destroy(texture);
                else
                    UnityEngine.Object.DestroyImmediate(texture);
                texture = null;
            }
        }

        private sealed class CharacterDraw
        {
            internal Renderer renderer;
            internal Material material;
            internal int submesh;
            internal int pass;
            internal int familyCode;
            internal Transform actorRoot;
            internal int renderQueue;
            internal float cameraDistanceSquared;
            internal string stableKey;
            internal uint logicalDrawId;
            internal bool preGEligible;
            internal int forwardPass;
        }

        private sealed class GenericDepthDraw
        {
            internal Renderer renderer;
            internal int submesh;
            internal string stableKey;
        }

        private sealed class DrawSummary
        {
            internal readonly HashSet<uint> expectedSelectorBits =
                new HashSet<uint>();
            internal readonly HashSet<int> expectedFamilyCodes =
                new HashSet<int>();
            internal readonly SortedSet<string> blockedMaterialPasses =
                new SortedSet<string>(StringComparer.Ordinal);
            internal int characterDrawCount;
            internal int genericOpaqueDepthDrawCount;
            internal int characterActorCount;
            internal int slot0ActorRootInstanceId;
            internal string slot0ActorRootPath = string.Empty;
            internal uint slot0SelectorBits;
            internal Matrix4x4 inverseGpuViewProjection;
            internal LogicalDrawInfo[] logicalDraws = Array.Empty<LogicalDrawInfo>();
        }

        private sealed class PendingReadback
        {
            internal CameraResources resources;
            internal string cameraName;
            internal int width;
            internal int height;
            internal int frame;
            internal GraphicsFormat depthStencilFormat;
            internal uint[] selector;
            internal uint[] normal;
            internal float[] depth;
            internal byte[] stencil;
            internal byte[] material;
            internal int remaining = 5;
            internal readonly List<string> readbackFailures = new List<string>();
            internal uint[] expectedSelectorBits;
            internal int[] expectedFamilyCodes;
            internal string[] blockedMaterialPasses;
            internal int characterDrawCount;
            internal int genericOpaqueDepthDrawCount;
        }

        [Serializable]
        private sealed class ValidationReport
        {
            public string schema = "endfield-recovered-pregbuffer-diagnostic-v1";
            public string camera;
            public int frame;
            public int width;
            public int height;
            public bool valid;
            public string originalDepthStencilIntent;
            public string actualDepthStencilFormat;
            public bool originalDepthStencilFormatExact;
            public string gBufferAFormat;
            public string gBufferBFormat;
            public string gBufferCFormat;
            public string depthCopyFormat;
            public string stencilMaskFormat;
            public string selectorCarrier;
            public string selectorCpuRule;
            public string selectorResolveRule;
            public string normalContract;
            public string familyTagContract;
            public string stencilContract;
            public bool screenSpaceShadowMaskEnabled;
            public int characterDrawCount;
            public int genericOpaqueDepthDrawCount;
            public int characterPixelCount;
            public int sceneDepthPixelCount;
            public int stencilCharacterPixelCount;
            public int selectorMismatchCount;
            public int selectorDecodeMismatchCount;
            public int normalReservedLaneMismatchCount;
            public int familyMismatchCount;
            public int stencilMismatchCount;
            public int materialColorNonzeroByteCount;
            public int characterClearDepthMismatchCount;
            public int invalidDepthCount;
            public int[] familyPixelCounts;
            public string[] expectedSelectorBits;
            public int[] expectedFamilyCodes;
            public string[] blockedMaterialPasses;
            public string[] limitations;
            public string[] failures;
        }

        internal bool Requested => standaloneRequested;
        internal bool ProducerRequired => producerRequired;
        internal bool SameOwnerRequired => sameOwnerRequired;

        internal EndfieldRecoveredPreGBufferDiagnostic(
            bool requiredByDownstreamProducer = false,
            bool sameOwnerAuditRequired = false,
            bool requireStencilSampling = false)
        {
            standaloneRequested = IsRequested();
            sameOwnerRequired = sameOwnerAuditRequired;
            stencilSamplingRequired = requireStencilSampling;
            producerRequired =
                standaloneRequested || requiredByDownstreamProducer ||
                sameOwnerRequired || stencilSamplingRequired;
            outputDirectory = standaloneRequested
                ? ReadOutputDirectory()
                : string.Empty;
            if (!producerRequired)
                return;

            Shader depthOnlyShader = Shader.Find(DepthOnlyShaderName);
            Shader utilityShader = Shader.Find(UtilityShaderName);
            if (depthOnlyShader != null && depthOnlyShader.isSupported)
            {
                depthOnlyMaterial = new Material(depthOnlyShader)
                {
                    hideFlags = HideFlags.HideAndDontSave,
                    name = "Recovered PreGBuffer Generic Depth Diagnostic"
                };
            }
            if (utilityShader != null && utilityShader.isSupported)
            {
                utilityMaterial = new Material(utilityShader)
                {
                    hideFlags = HideFlags.HideAndDontSave,
                    name = "Recovered PreGBuffer Copy/Stencil Diagnostic"
                };
            }
        }

        public void Dispose()
        {
            if (disposed)
                return;
            disposed = true;
            Shader.DisableKeyword(
                EndfieldRecoveredScreenDirectAudit.SameOwnerKeyword);
            foreach (CameraResources resources in cameraResources.Values)
                resources.Dispose();
            cameraResources.Clear();
            DestroyMaterial(ref depthOnlyMaterial);
            DestroyMaterial(ref utilityMaterial);
        }

        /// <summary>
        /// Builds the same lexical renderer/material-slot dictionary used by
        /// RenderSidecar without issuing graphics commands. The screen/direct
        /// audit calls this before ScriptableRenderContext.Cull so Unity can
        /// synchronize its diagnostic MaterialPropertyBlocks into the current
        /// frame's render-node data.
        /// </summary>
        internal LogicalDrawInfo[] CollectLogicalDrawsForSameOwner(Camera camera)
        {
            if (disposed)
                throw new ObjectDisposedException(nameof(EndfieldRecoveredPreGBufferDiagnostic));
            if (!sameOwnerRequired || camera == null)
                return Array.Empty<LogicalDrawInfo>();

            Renderer[] renderers = UnityEngine.Object.FindObjectsOfType<Renderer>();
            Array.Sort(renderers, CompareRenderers);
            Plane[] frustumPlanes = GeometryUtility.CalculateFrustumPlanes(camera);
            var collected = new List<LogicalDrawInfo>();
            foreach (Renderer renderer in renderers)
            {
                if (!IsRendererVisibleToCamera(renderer, camera, frustumPlanes))
                    continue;
                Material[] materials = renderer.sharedMaterials;
                for (int submesh = 0; submesh < materials.Length; submesh++)
                {
                    Material material = materials[submesh];
                    if (material == null || material.shader == null)
                        continue;
                    int familyCode;
                    if (!SupportedFamilyCodes.TryGetValue(
                            material.shader.name,
                            out familyCode))
                    {
                        continue;
                    }

                    bool preGEligible =
                        material.renderQueue <= (int)RenderQueue.GeometryLast;
                    int preGPass = preGEligible
                        ? material.FindPass(CharacterPassName)
                        : -1;
                    string stableKey = BuildRendererKey(renderer) + "/" +
                        submesh.ToString("D4", CultureInfo.InvariantCulture) + "/" +
                        material.name;
                    collected.Add(
                        new LogicalDrawInfo(
                            renderer,
                            material,
                            submesh,
                            0u,
                            familyCode,
                            material.renderQueue,
                            preGEligible,
                            preGPass,
                            material.FindPass("FORWARD"),
                            stableKey));
                }
            }

            collected.Sort(
                (left, right) => string.CompareOrdinal(
                    left.stableKey,
                    right.stableKey));
            bool logicalIdsFitExactFloat =
                collected.Count < ExactFloatIntegerLimit;
            var result = new LogicalDrawInfo[collected.Count];
            for (int i = 0; i < collected.Count; i++)
            {
                LogicalDrawInfo draw = collected[i];
                result[i] = new LogicalDrawInfo(
                    draw.renderer,
                    draw.material,
                    draw.submesh,
                    logicalIdsFitExactFloat ? (uint)(i + 1) : 0u,
                    draw.familyCode,
                    draw.renderQueue,
                    draw.preGEligible,
                    draw.preGPass,
                    draw.forwardPass,
                    draw.stableKey);
            }
            return result;
        }

        internal Frame Render(
            ScriptableRenderContext context,
            Camera camera,
            int width,
            int height,
            RenderTargetIdentifier restoreTarget)
        {
            if (disposed)
                throw new ObjectDisposedException(nameof(EndfieldRecoveredPreGBufferDiagnostic));
            if (!producerRequired)
                return Frame.Unavailable("neither standalone validation nor a downstream producer requested the sidecar");
            if (camera == null)
                throw new ArgumentNullException(nameof(camera));

            string failure;
            CameraResources resources;
            if (!TryPrepare(camera, width, height, out resources, out failure))
            {
                BindDisabled(context);
                if (!loggedFailure)
                {
                    Debug.LogWarning(
                        "Recovered PreGBuffer diagnostic was requested but remains " +
                        $"inactive: {failure}. Canonical HGCompat rendering is unchanged.");
                    loggedFailure = true;
                }
                return Frame.Unavailable(failure);
            }

            CommandBuffer commandBuffer = new CommandBuffer
            {
                name = "Recovered PreGBuffer sidecar diagnostic"
            };
            DrawSummary summary;
            try
            {
                summary = RenderSidecar(
                    commandBuffer,
                    camera,
                    resources,
                    restoreTarget);
                resources.renderedFrames++;
                if (standaloneRequested &&
                    !resources.readbackPending && !resources.validationComplete &&
                    resources.renderedFrames >= ValidationWarmupFrames)
                {
                    EnqueueReadback(commandBuffer, resources, camera, summary);
                }
                context.ExecuteCommandBuffer(commandBuffer);
            }
            finally
            {
                commandBuffer.Release();
            }

            if (standaloneRequested && !loggedActive)
            {
                string fallback = resources.depthStencilFormat == OriginalDepthStencilIntent
                    ? "exact D32_SFloat_S8_UInt"
                    : $"supported stencil-bearing fallback {resources.depthStencilFormat}";
                Debug.Log(
                    "Recovered PreGBuffer sidecar diagnostic active (default-off): " +
                    $"{fallback}, exact R32_SFloat depth copy, exact " +
                    "A2B10G10R10_UNormPack32 A/B plus R8G8B8A8_SRGB C material " +
                    "payload, CPU selector rule " +
                    "1u<<((index+8)&31), Y-up oct normal, exact family tags, and " +
                    "low-three-bit stencil validation. It is offscreen and does not " +
                    "enable or feed the screen-space shadow mask.");
                loggedActive = true;
            }
            return new Frame(
                true,
                string.Empty,
                camera.GetInstanceID(),
                resources.width,
                resources.height,
                resources.depthStencil,
                resources.depthCopy,
                resources.gBufferA,
                resources.gBufferB,
                resources.gBufferC,
                resources.sameOwner,
                resources.stencilMask,
                resources.depthStencilFormat,
                summary.inverseGpuViewProjection,
                summary.characterActorCount,
                summary.slot0ActorRootInstanceId,
                summary.slot0ActorRootPath,
                summary.slot0SelectorBits,
                summary.characterDrawCount,
                ToArray(summary.blockedMaterialPasses),
                sameOwnerRequired && resources.sameOwner != null,
                summary.logicalDraws);
        }

        private bool TryPrepare(
            Camera camera,
            int width,
            int height,
            out CameraResources resources,
            out string failure)
        {
            resources = null;
            failure = string.Empty;
            if (depthOnlyMaterial == null || utilityMaterial == null)
            {
                failure = $"required shaders '{DepthOnlyShaderName}' and/or '{UtilityShaderName}' are missing or unsupported";
                return false;
            }
            if (!SystemInfo.supportsAsyncGPUReadback)
            {
                failure = "the active graphics device does not support AsyncGPUReadback";
                return false;
            }
            if (!SystemInfo.IsFormatSupported(ExactGBufferFormat, FormatUsage.Render))
            {
                failure = $"exact {ExactGBufferFormat} render-target support is unavailable";
                return false;
            }
            if (!SystemInfo.IsFormatSupported(ExactDepthCopyFormat, FormatUsage.Render))
            {
                failure = $"exact {ExactDepthCopyFormat} render-target support is unavailable";
                return false;
            }
            if (!SystemInfo.IsFormatSupported(StencilMaskFormat, FormatUsage.Render))
            {
                failure = $"{StencilMaskFormat} stencil-mask validation target support is unavailable";
                return false;
            }
            int requiredColorTargets = sameOwnerRequired ? 4 : 3;
            if (SystemInfo.supportedRenderTargetCount < requiredColorTargets)
            {
                failure =
                    "PreGBuffer selector, normal, material, and optional owner " +
                    $"targets need {requiredColorTargets} simultaneous color targets";
                return false;
            }
            GraphicsFormat depthStencilFormat;
            if (!TryChooseDepthStencilFormat(out depthStencilFormat))
            {
                failure = "neither D32_SFloat_S8_UInt nor D24_UNorm_S8_UInt is renderable";
                return false;
            }

            CameraResources existing;
            cameraResources.TryGetValue(camera, out existing);
            if (existing != null && existing.width == width && existing.height == height &&
                existing.depthStencilFormat == depthStencilFormat &&
                ResourcesAreCreated(existing))
            {
                resources = existing;
                return true;
            }
            if (existing != null && existing.readbackPending)
            {
                failure = "camera dimensions changed while the one-shot GPU readback is pending";
                return false;
            }
            if (existing != null)
            {
                existing.Dispose();
                cameraResources.Remove(camera);
            }

            resources = new CameraResources
            {
                width = Mathf.Max(width, 1),
                height = Mathf.Max(height, 1),
                depthStencilFormat = depthStencilFormat
            };
            if (!CreateResources(resources, out failure))
            {
                resources.Dispose();
                resources = null;
                return false;
            }
            cameraResources.Add(camera, resources);
            return true;
        }

        private DrawSummary RenderSidecar(
            CommandBuffer commandBuffer,
            Camera camera,
            CameraResources resources,
            RenderTargetIdentifier restoreTarget)
        {
            // CommandBuffer.ClearRenderTarget takes API-agnostic depth (0 near,
            // 1 far) and performs the platform conversion itself. Texture.Load
            // below observes the API-native sample, which is 0 at far on D3D's
            // reversed-Z path. Keep those two domains explicitly separate.
            const float farClearDepth = 1.0f;
            float farDepthSample = SystemInfo.usesReversedZBuffer ? 0.0f : 1.0f;
            if (sameOwnerRequired)
            {
                commandBuffer.EnableShaderKeyword(
                    EndfieldRecoveredScreenDirectAudit.SameOwnerKeyword);
            }
            commandBuffer.SetRenderTarget(resources.depthStencil);
            commandBuffer.ClearRenderTarget(
                RTClearFlags.Depth | RTClearFlags.Stencil,
                Color.clear,
                farClearDepth,
                0u);

            Renderer[] renderers = UnityEngine.Object.FindObjectsOfType<Renderer>();
            Array.Sort(renderers, CompareRenderers);
            Plane[] frustumPlanes = GeometryUtility.CalculateFrustumPlanes(camera);
            var characterDraws = new List<CharacterDraw>();
            var logicalDraws = new List<CharacterDraw>();
            var genericDepthDraws = new List<GenericDepthDraw>();
            var summary = new DrawSummary();

            foreach (Renderer renderer in renderers)
            {
                if (!IsRendererVisibleToCamera(renderer, camera, frustumPlanes))
                    continue;
                Material[] materials = renderer.sharedMaterials;
                for (int submesh = 0; submesh < materials.Length; submesh++)
                {
                    Material material = materials[submesh];
                    if (material == null || material.shader == null)
                        continue;
                    int familyCode;
                    if (SupportedFamilyCodes.TryGetValue(material.shader.name, out familyCode))
                    {
                        string stableKey = BuildRendererKey(renderer) + "/" +
                            submesh.ToString("D4", CultureInfo.InvariantCulture) + "/" +
                            material.name;
                        // The original CharacterPrePass renderer list is opaque.
                        // Exact Wulfa/Zhuangfy material dumps place the eligible
                        // Skin/Cloth/Eye/Hair rows at queues 2000 or 2015; queue
                        // 2985 hair shells and queue 3000 character layers stay
                        // in transparent Forward and must not own PreG depth,
                        // selector, normal, family, or stencil pixels.
                        bool preGEligible =
                            material.renderQueue <= (int)RenderQueue.GeometryLast;
                        int pass = preGEligible
                            ? material.FindPass(CharacterPassName)
                            : -1;
                        var logicalDraw = new CharacterDraw
                        {
                            renderer = renderer,
                            material = material,
                            submesh = submesh,
                            pass = pass,
                            familyCode = familyCode,
                            actorRoot = ResolveActorRoot(renderer),
                            renderQueue = material.renderQueue,
                            cameraDistanceSquared =
                                (renderer.bounds.center - camera.transform.position).sqrMagnitude,
                            stableKey = stableKey,
                            preGEligible = preGEligible,
                            forwardPass = material.FindPass("FORWARD")
                        };
                        logicalDraws.Add(logicalDraw);

                        if (!preGEligible)
                            continue;
                        if (pass < 0)
                        {
                            summary.blockedMaterialPasses.Add(
                                material.shader.name + "/" + material.name + ": missing " + CharacterPassName);
                            continue;
                        }
                        if (string.Equals(
                                material.shader.name,
                                "Endfield/Recovered/CharacterCloth",
                                StringComparison.Ordinal) &&
                            material.HasProperty("_UseParallax") &&
                            material.GetFloat("_UseParallax") > 0.5f)
                        {
                            summary.blockedMaterialPasses.Add(
                                material.shader.name + "/" + material.name +
                                ": partial coverage; active parallax-shifted PreGBuffer UV is not recovered");
                        }
                        characterDraws.Add(logicalDraw);
                        continue;
                    }

                    // These three renderers are source-backed CharInfo scene
                    // passes, not recovered character families.  Their source
                    // materials deliberately disable DepthOnly: the floor's
                    // HGBuffer draw belongs to the ordinary deferred list
                    // after CharacterPrePass, the wall is a later opaque
                    // ForwardOnly draw, and the far grid is queue-2950
                    // transparent.  Treating them as generic pre-depth would
                    // move them before CharacterPrePass; treating their
                    // Endfield/Recovered prefix as a missing character family
                    // would incorrectly block strict character coverage.
                    // Keep the identity/queue gate exact so any other
                    // recovered shader, or any mutated presentation material,
                    // remains a hard blocker.
                    if (IsSourceBackedCharInfoPassAfterCharacterPreG(
                            renderer,
                            material))
                    {
                        continue;
                    }

                    if (material.shader.name.StartsWith(
                            "Endfield/Recovered/",
                            StringComparison.Ordinal))
                    {
                        if (!material.shader.name.Contains("OverlayShadow"))
                        {
                            summary.blockedMaterialPasses.Add(
                                material.shader.name + "/" + material.name + ": unsupported recovered family");
                        }
                        continue;
                    }

                    if (material.renderQueue <= (int)RenderQueue.GeometryLast)
                    {
                        genericDepthDraws.Add(new GenericDepthDraw
                        {
                            renderer = renderer,
                            submesh = submesh,
                            stableKey = BuildRendererKey(renderer) + "/" +
                                submesh.ToString("D4", CultureInfo.InvariantCulture) + "/" + material.name
                        });
                    }
                }
            }

            logicalDraws.Sort(
                (left, right) => string.CompareOrdinal(left.stableKey, right.stableKey));
            bool logicalIdsFitExactFloat =
                logicalDraws.Count < ExactFloatIntegerLimit;
            if (sameOwnerRequired && !logicalIdsFitExactFloat)
            {
                summary.blockedMaterialPasses.Add(
                    "logical draw count exceeds the exact binary32 integer range [1,2^24)");
            }
            summary.logicalDraws = new LogicalDrawInfo[logicalDraws.Count];
            for (int i = 0; i < logicalDraws.Count; i++)
            {
                CharacterDraw draw = logicalDraws[i];
                draw.logicalDrawId = logicalIdsFitExactFloat
                    ? (uint)(i + 1)
                    : 0u;
                summary.logicalDraws[i] = new LogicalDrawInfo(
                    draw.renderer,
                    draw.material,
                    draw.submesh,
                    draw.logicalDrawId,
                    draw.familyCode,
                    draw.renderQueue,
                    draw.preGEligible,
                    draw.pass,
                    draw.forwardPass,
                    draw.stableKey);
            }

            characterDraws.Sort(CompareCharacterDraws);
            genericDepthDraws.Sort(
                (left, right) => string.CompareOrdinal(left.stableKey, right.stableKey));
            int actorCount;
            Dictionary<Transform, int> actorIndices =
                BuildActorIndices(characterDraws, out actorCount);
            summary.characterActorCount = actorCount;
            foreach (KeyValuePair<Transform, int> actorSlot in actorIndices)
            {
                if (actorSlot.Value != 0 || actorSlot.Key == null)
                    continue;
                summary.slot0ActorRootInstanceId = actorSlot.Key.GetInstanceID();
                summary.slot0ActorRootPath = BuildTransformPath(actorSlot.Key);
                summary.slot0SelectorBits = CharacterSelectorBits(0);
                break;
            }
            Matrix4x4 gpuViewProjection =
                GL.GetGPUProjectionMatrix(camera.projectionMatrix, true) *
                camera.worldToCameraMatrix;
            summary.inverseGpuViewProjection = gpuViewProjection.inverse;
            RenderTargetIdentifier[] mrt = sameOwnerRequired
                ? new[]
                {
                    new RenderTargetIdentifier(resources.gBufferA),
                    new RenderTargetIdentifier(resources.gBufferB),
                    new RenderTargetIdentifier(resources.gBufferC),
                    new RenderTargetIdentifier(resources.sameOwner)
                }
                : new[]
                {
                    new RenderTargetIdentifier(resources.gBufferA),
                    new RenderTargetIdentifier(resources.gBufferB),
                    new RenderTargetIdentifier(resources.gBufferC)
                };
            commandBuffer.SetRenderTarget(mrt, resources.depthStencil);
            commandBuffer.ClearRenderTarget(false, true, Color.clear);

            // Shipped CharInfo defaults to DefaultDeferred. Its earlier
            // DepthPrepass draws deferred/forward ECS PreZ and the ordinary
            // opaque renderer list into sceneDepth; DefaultDeferred GBuffer
            // later draws characterPrePass ECS/outline/SRP lists against that
            // same sceneDepth. This sidecar cannot reproduce the ECS/SRP split,
            // but its conservative generic helper must establish shared depth
            // ownership before the recovered character PreGBuffer draws.
            foreach (GenericDepthDraw draw in genericDepthDraws)
            {
                commandBuffer.DrawRenderer(
                    draw.renderer,
                    depthOnlyMaterial,
                    draw.submesh,
                    0);
                summary.genericOpaqueDepthDrawCount++;
            }

            foreach (CharacterDraw draw in characterDraws)
            {
                int characterIndex;
                if (draw.actorRoot == null ||
                    !actorIndices.TryGetValue(draw.actorRoot, out characterIndex) ||
                    characterIndex < 0 || characterIndex >= MaximumCharacterCount)
                {
                    summary.blockedMaterialPasses.Add(
                        draw.stableKey + ": no deterministic character slot in [0,14]");
                    continue;
                }

                uint selectorBits = CharacterSelectorBits(characterIndex);
                commandBuffer.SetGlobalInt(SelectorBitsId, unchecked((int)selectorBits));
                if (sameOwnerRequired)
                {
                    commandBuffer.SetGlobalInt(
                        LogicalDrawId,
                        unchecked((int)draw.logicalDrawId));
                }
                commandBuffer.DrawRenderer(
                    draw.renderer,
                    draw.material,
                    draw.submesh,
                    draw.pass);
                summary.expectedSelectorBits.Add(selectorBits);
                summary.expectedFamilyCodes.Add(draw.familyCode);
                summary.characterDrawCount++;
            }

            commandBuffer.SetGlobalTexture(DepthStencilId, resources.depthStencil);
            commandBuffer.SetRenderTarget(resources.depthCopy);
            commandBuffer.ClearRenderTarget(
                false,
                true,
                new Color(farDepthSample, 0.0f, 0.0f, 0.0f));
            commandBuffer.DrawProcedural(
                Matrix4x4.identity,
                utilityMaterial,
                0,
                MeshTopology.Triangles,
                3,
                1);

            commandBuffer.SetRenderTarget(resources.stencilMask, resources.depthStencil);
            commandBuffer.ClearRenderTarget(false, true, Color.clear);
            commandBuffer.DrawProcedural(
                Matrix4x4.identity,
                utilityMaterial,
                1,
                MeshTopology.Triangles,
                3,
                1);

            commandBuffer.SetGlobalTexture(DepthStencilId, resources.depthStencil);
            commandBuffer.SetGlobalTexture(DepthCopyId, resources.depthCopy);
            commandBuffer.SetGlobalTexture(GBufferAId, resources.gBufferA);
            commandBuffer.SetGlobalTexture(GBufferBId, resources.gBufferB);
            commandBuffer.SetGlobalTexture(GBufferCId, resources.gBufferC);
            if (sameOwnerRequired)
                commandBuffer.SetGlobalTexture(SameOwnerId, resources.sameOwner);
            commandBuffer.SetGlobalTexture(StencilMaskId, resources.stencilMask);
            commandBuffer.SetGlobalVector(
                TexelSizeId,
                new Vector4(
                    1.0f / resources.width,
                    1.0f / resources.height,
                    resources.width,
                    resources.height));
            commandBuffer.SetGlobalFloat(ReadyId, 1.0f);
            if (sameOwnerRequired)
            {
                commandBuffer.DisableShaderKeyword(
                    EndfieldRecoveredScreenDirectAudit.SameOwnerKeyword);
            }
            commandBuffer.SetRenderTarget(restoreTarget);
            return summary;
        }

        private void EnqueueReadback(
            CommandBuffer commandBuffer,
            CameraResources resources,
            Camera camera,
            DrawSummary summary)
        {
            var pending = new PendingReadback
            {
                resources = resources,
                cameraName = camera.name,
                width = resources.width,
                height = resources.height,
                frame = Time.frameCount,
                depthStencilFormat = resources.depthStencilFormat,
                expectedSelectorBits = SortedArray(summary.expectedSelectorBits),
                expectedFamilyCodes = SortedArray(summary.expectedFamilyCodes),
                blockedMaterialPasses = ToArray(summary.blockedMaterialPasses),
                characterDrawCount = summary.characterDrawCount,
                genericOpaqueDepthDrawCount = summary.genericOpaqueDepthDrawCount
            };
            resources.readbackPending = true;

            commandBuffer.RequestAsyncReadback(
                resources.gBufferA,
                0,
                request => CompleteUIntReadback(pending, request, true));
            commandBuffer.RequestAsyncReadback(
                resources.gBufferB,
                0,
                request => CompleteUIntReadback(pending, request, false));
            commandBuffer.RequestAsyncReadback(
                resources.gBufferC,
                0,
                request => CompleteMaterialReadback(pending, request));
            commandBuffer.RequestAsyncReadback(
                resources.depthCopy,
                0,
                request => CompleteFloatReadback(pending, request));
            commandBuffer.RequestAsyncReadback(
                resources.stencilMask,
                0,
                request => CompleteByteReadback(pending, request));
        }

        private void CompleteUIntReadback(
            PendingReadback pending,
            AsyncGPUReadbackRequest request,
            bool selector)
        {
            try
            {
                if (request.hasError)
                {
                    pending.readbackFailures.Add(
                        selector ? "GBuffer A readback failed" : "GBuffer B readback failed");
                }
                else
                {
                    var data = request.GetData<uint>();
                    uint[] copy = new uint[data.Length];
                    for (int i = 0; i < data.Length; i++)
                        copy[i] = data[i];
                    if (selector)
                        pending.selector = copy;
                    else
                        pending.normal = copy;
                }
            }
            catch (Exception exception)
            {
                pending.readbackFailures.Add(
                    (selector ? "GBuffer A" : "GBuffer B") +
                    " readback exception: " + exception.Message);
            }
            CompleteOne(pending);
        }

        private void CompleteFloatReadback(
            PendingReadback pending,
            AsyncGPUReadbackRequest request)
        {
            try
            {
                if (request.hasError)
                {
                    pending.readbackFailures.Add("R32 depth-copy readback failed");
                }
                else
                {
                    var data = request.GetData<float>();
                    pending.depth = new float[data.Length];
                    for (int i = 0; i < data.Length; i++)
                        pending.depth[i] = data[i];
                }
            }
            catch (Exception exception)
            {
                pending.readbackFailures.Add(
                    "R32 depth-copy readback exception: " + exception.Message);
            }
            CompleteOne(pending);
        }

        private void CompleteByteReadback(
            PendingReadback pending,
            AsyncGPUReadbackRequest request)
        {
            try
            {
                if (request.hasError)
                {
                    pending.readbackFailures.Add("R8 stencil-mask readback failed");
                }
                else
                {
                    var data = request.GetData<byte>();
                    pending.stencil = new byte[data.Length];
                    for (int i = 0; i < data.Length; i++)
                        pending.stencil[i] = data[i];
                }
            }
            catch (Exception exception)
            {
                pending.readbackFailures.Add(
                    "R8 stencil-mask readback exception: " + exception.Message);
            }
            CompleteOne(pending);
        }

        private void CompleteMaterialReadback(
            PendingReadback pending,
            AsyncGPUReadbackRequest request)
        {
            try
            {
                if (request.hasError)
                {
                    pending.readbackFailures.Add(
                        "GBuffer C material-color readback failed");
                }
                else
                {
                    var data = request.GetData<byte>();
                    pending.material = new byte[data.Length];
                    for (int i = 0; i < data.Length; i++)
                        pending.material[i] = data[i];
                }
            }
            catch (Exception exception)
            {
                pending.readbackFailures.Add(
                    "GBuffer C material-color readback exception: " +
                    exception.Message);
            }
            CompleteOne(pending);
        }

        private void CompleteOne(PendingReadback pending)
        {
            pending.remaining--;
            if (pending.remaining > 0)
                return;
            pending.resources.readbackPending = false;
            pending.resources.validationComplete = true;
            ValidateAndReport(pending);
        }

        private void ValidateAndReport(PendingReadback pending)
        {
            int expectedPixels = pending.width * pending.height;
            var failures = new List<string>(pending.readbackFailures);
            ValidateLength(pending.selector, expectedPixels, "GBuffer A", failures);
            ValidateLength(pending.normal, expectedPixels, "GBuffer B", failures);
            ValidateLength(
                pending.material,
                expectedPixels * 4,
                "GBuffer C material color",
                failures);
            ValidateLength(pending.depth, expectedPixels, "R32 depth copy", failures);
            ValidateLength(pending.stencil, expectedPixels, "R8 stencil mask", failures);

            var report = new ValidationReport
            {
                camera = pending.cameraName,
                frame = pending.frame,
                width = pending.width,
                height = pending.height,
                originalDepthStencilIntent = OriginalDepthStencilIntent.ToString(),
                actualDepthStencilFormat = pending.depthStencilFormat.ToString(),
                originalDepthStencilFormatExact =
                    pending.depthStencilFormat == OriginalDepthStencilIntent,
                gBufferAFormat = ExactGBufferFormat.ToString(),
                gBufferBFormat = ExactGBufferFormat.ToString(),
                gBufferCFormat = ExactGBufferCFormat.ToString(),
                depthCopyFormat = ExactDepthCopyFormat.ToString(),
                stencilMaskFormat = StencilMaskFormat.ToString(),
                selectorCarrier =
                    "CPU-computed uint global; stock Unity cannot populate the original modified-engine unity_WorldTransformParams.z as-float ABI",
                selectorCpuRule = "index < 0 ? 0u : 1u << ((index + 8) & 31), diagnostic slots limited to 0..14",
                selectorResolveRule = "log2(packUnorm4x10(GBufferA)) - 8",
                normalContract = "GBufferB.xy = Y-up oct normal, GBufferB.z = 0",
                familyTagContract = "CharacterNPR=0, Skin=0.4, Eye=0.7, Hair=1.0 (A2 quantizes to codes 0..3)",
                stencilContract = "character pixels must satisfy Ref=4, ReadMask=7, Comp=Equal",
                screenSpaceShadowMaskEnabled = false,
                characterDrawCount = pending.characterDrawCount,
                genericOpaqueDepthDrawCount = pending.genericOpaqueDepthDrawCount,
                familyPixelCounts = new int[4],
                expectedSelectorBits = FormatSelectorBits(pending.expectedSelectorBits),
                expectedFamilyCodes = pending.expectedFamilyCodes,
                blockedMaterialPasses = pending.blockedMaterialPasses,
                limitations = new[]
                {
                    "The original unity_WorldTransformParams.z selector carrier is unavailable in stock Unity; only its exact uint payload and packed render-target value are reproduced.",
                    "Non-recovered opaque shaders use a CullBack, non-alpha-clipped override depth pass; material-specific displacement, alpha clipping, and custom culling are not claimed.",
                    "The sidecar has no decal or GPU-particle stage, so its R32 copy is full-scene for the lab opaque coverage, not a claim of retail second-copy chronology parity.",
                    "The diagnostic still does not publish motion vectors; its new GBuffer C target is a source-shaped material/color sidecar and is not consumed by the retail resolver.",
                    "Character draws are deterministically sorted by queue, camera distance, and hierarchy path; the retail DepthCharacterOnly DrawECS list ordering and equal-depth hair overlap order remain runtime-only unknowns.",
                    "Dither, dissolve, UV2-color, and unselected alpha-test keyword variants are not represented by the current recovered material shaders.",
                    "No CSM, ASM, contact-shadow, cloud-shadow, or screen-space shadow-mask consumer is enabled by this tranche."
                }
            };

            if (pending.material != null)
            {
                for (int i = 0; i < pending.material.Length; i++)
                {
                    if (pending.material[i] != 0)
                        report.materialColorNonzeroByteCount++;
                }
            }

            if (failures.Count == 0)
            {
                var expectedSelectors = new HashSet<uint>(pending.expectedSelectorBits);
                var expectedFamilies = new HashSet<int>(pending.expectedFamilyCodes);
                float farDepth = SystemInfo.usesReversedZBuffer ? 0.0f : 1.0f;
                for (int i = 0; i < expectedPixels; i++)
                {
                    float depth = pending.depth[i];
                    if (!IsFinite(depth) || depth < -1.0e-5f || depth > 1.00001f)
                    {
                        report.invalidDepthCount++;
                    }
                    else if (Mathf.Abs(depth - farDepth) > 1.0e-6f)
                    {
                        report.sceneDepthPixelCount++;
                    }

                    uint selector = pending.selector[i];
                    bool stencilCharacter = pending.stencil[i] >= 128;
                    if (stencilCharacter)
                        report.stencilCharacterPixelCount++;
                    if (selector == 0u)
                    {
                        if (stencilCharacter)
                            report.stencilMismatchCount++;
                        continue;
                    }

                    report.characterPixelCount++;
                    if (!expectedSelectors.Contains(selector))
                        report.selectorMismatchCount++;
                    if (!TryDecodeCharacterIndex(selector, out _))
                        report.selectorDecodeMismatchCount++;
                    if (!stencilCharacter)
                        report.stencilMismatchCount++;
                    if (Mathf.Abs(depth - farDepth) <= 1.0e-6f)
                        report.characterClearDepthMismatchCount++;

                    uint packedNormal = pending.normal[i];
                    if (((packedNormal >> 20) & 1023u) != 0u)
                        report.normalReservedLaneMismatchCount++;
                    int family = (int)((packedNormal >> 30) & 3u);
                    if (family >= 0 && family < report.familyPixelCounts.Length)
                        report.familyPixelCounts[family]++;
                    if (!expectedFamilies.Contains(family))
                        report.familyMismatchCount++;
                }

                if (report.characterDrawCount <= 0)
                    failures.Add("no supported recovered character PreGBuffer draw was scheduled");
                if (report.characterPixelCount <= 0)
                    failures.Add("GBuffer A contains no character selector pixels");
                if (report.sceneDepthPixelCount <= 0)
                    failures.Add("R32 depth copy contains no non-clear scene depth");
                AddMismatchFailure(report.selectorMismatchCount, "selector payload", failures);
                AddMismatchFailure(report.selectorDecodeMismatchCount, "selector log2 decode", failures);
                AddMismatchFailure(report.normalReservedLaneMismatchCount, "GBuffer B reserved lane", failures);
                AddMismatchFailure(report.familyMismatchCount, "material-family tag", failures);
                AddMismatchFailure(report.stencilMismatchCount, "low-three-bit stencil ownership", failures);
                AddMismatchFailure(report.characterClearDepthMismatchCount, "character copied depth", failures);
                AddMismatchFailure(report.invalidDepthCount, "R32 depth range/finite", failures);
            }

            report.failures = failures.ToArray();
            report.valid = failures.Count == 0;
            string json = JsonUtility.ToJson(report, true);
            Debug.Log(
                "Recovered PreGBuffer diagnostic validation " +
                (report.valid ? "PASS" : "FAIL") + ":\n" + json);
            if (!string.IsNullOrWhiteSpace(outputDirectory))
                WriteCapture(outputDirectory, pending, report, json);
        }

        private static void WriteCapture(
            string root,
            PendingReadback pending,
            ValidationReport report,
            string json)
        {
            try
            {
                string cameraDirectory = Path.Combine(root, SanitizeFileName(pending.cameraName));
                Directory.CreateDirectory(cameraDirectory);
                File.WriteAllText(
                    Path.Combine(cameraDirectory, "pregbuffer_validation.json"),
                    json,
                    new UTF8Encoding(false));

                if (pending.selector != null && pending.normal != null &&
                    pending.depth != null && pending.stencil != null)
                {
                    WritePng(
                        Path.Combine(cameraDirectory, "pregbuffer_selector.png"),
                        BuildSelectorPixels(pending),
                        pending.width,
                        pending.height);
                    WritePng(
                        Path.Combine(cameraDirectory, "pregbuffer_oct_normal.png"),
                        BuildNormalPixels(pending),
                        pending.width,
                        pending.height);
                    WritePng(
                        Path.Combine(cameraDirectory, "pregbuffer_depth_r32.png"),
                        BuildDepthPixels(pending),
                        pending.width,
                        pending.height);
                    WritePng(
                        Path.Combine(cameraDirectory, "pregbuffer_stencil_low3_eq4.png"),
                        BuildStencilPixels(pending),
                        pending.width,
                        pending.height);
                }
                Debug.Log(
                    $"Recovered PreGBuffer diagnostic capture written to '{cameraDirectory}'.");
            }
            catch (Exception exception)
            {
                Debug.LogWarning(
                    "Recovered PreGBuffer diagnostic could not write its optional capture: " +
                    exception.Message);
            }
        }

        private static Color32[] BuildSelectorPixels(PendingReadback pending)
        {
            Color32[] pixels = new Color32[pending.selector.Length];
            for (int i = 0; i < pixels.Length; i++)
            {
                uint selector = pending.selector[i];
                int index;
                if (!TryDecodeCharacterIndex(selector, out index))
                {
                    pixels[i] = selector == 0u
                        ? new Color32(0, 0, 0, 255)
                        : new Color32(255, 0, 255, 255);
                    continue;
                }
                pixels[i] = IndexColor(index);
            }
            return FlipRows(pixels, pending.width, pending.height);
        }

        private static Color32[] BuildNormalPixels(PendingReadback pending)
        {
            Color32[] pixels = new Color32[pending.normal.Length];
            for (int i = 0; i < pixels.Length; i++)
            {
                if (pending.selector[i] == 0u)
                {
                    pixels[i] = new Color32(0, 0, 0, 255);
                    continue;
                }
                uint packed = pending.normal[i];
                float octX = ((packed & 1023u) / 1023.0f) * 2.0f - 1.0f;
                float octZ = (((packed >> 10) & 1023u) / 1023.0f) * 2.0f - 1.0f;
                Vector3 normal = DecodeYUpOct(octX, octZ);
                pixels[i] = new Color32(
                    ToByte(normal.x * 0.5f + 0.5f),
                    ToByte(normal.y * 0.5f + 0.5f),
                    ToByte(normal.z * 0.5f + 0.5f),
                    255);
            }
            return FlipRows(pixels, pending.width, pending.height);
        }

        private static Color32[] BuildDepthPixels(PendingReadback pending)
        {
            Color32[] pixels = new Color32[pending.depth.Length];
            for (int i = 0; i < pixels.Length; i++)
            {
                byte value = ToByte(Mathf.Clamp01(pending.depth[i]));
                pixels[i] = new Color32(value, value, value, 255);
            }
            return FlipRows(pixels, pending.width, pending.height);
        }

        private static Color32[] BuildStencilPixels(PendingReadback pending)
        {
            Color32[] pixels = new Color32[pending.stencil.Length];
            for (int i = 0; i < pixels.Length; i++)
            {
                byte value = pending.stencil[i] >= 128 ? (byte)255 : (byte)0;
                pixels[i] = new Color32(value, value, value, 255);
            }
            return FlipRows(pixels, pending.width, pending.height);
        }

        private static void WritePng(string path, Color32[] pixels, int width, int height)
        {
            Texture2D texture = new Texture2D(width, height, TextureFormat.RGBA32, false, true)
            {
                hideFlags = HideFlags.HideAndDontSave
            };
            try
            {
                texture.SetPixels32(pixels);
                texture.Apply(false, false);
                File.WriteAllBytes(path, texture.EncodeToPNG());
            }
            finally
            {
                if (Application.isPlaying)
                    UnityEngine.Object.Destroy(texture);
                else
                    UnityEngine.Object.DestroyImmediate(texture);
            }
        }

        private bool CreateResources(
            CameraResources resources,
            out string failure)
        {
            failure = string.Empty;
            resources.depthStencil = CreateDepthStencil(
                resources.width,
                resources.height,
                resources.depthStencilFormat,
                "Recovered PreGBuffer DepthStencil",
                stencilSamplingRequired);
            resources.depthCopy = CreateColorTarget(
                resources.width,
                resources.height,
                ExactDepthCopyFormat,
                "Recovered PreGBuffer Depth Copy R32");
            resources.gBufferA = CreateColorTarget(
                resources.width,
                resources.height,
                ExactGBufferFormat,
                "Recovered PreGBuffer A Selector");
            resources.gBufferB = CreateColorTarget(
                resources.width,
                resources.height,
                ExactGBufferFormat,
                "Recovered PreGBuffer B OctNormalFamily");
            resources.gBufferC = CreateColorTarget(
                resources.width,
                resources.height,
                ExactGBufferCFormat,
                "Recovered PreGBuffer C MaterialColor");
            if (sameOwnerRequired)
            {
                resources.sameOwner = CreateColorTarget(
                    resources.width,
                    resources.height,
                    SameOwnerFormat,
                    "Recovered PreGBuffer Owner and Tangent Normal RGBA32");
            }
            resources.stencilMask = CreateColorTarget(
                resources.width,
                resources.height,
                StencilMaskFormat,
                "Recovered PreGBuffer Stencil Low3 Eq4");

            if (!ResourcesAreCreated(resources))
            {
                failure = "one or more sidecar render textures could not be created";
                return false;
            }
            if (resources.depthStencil.depthStencilFormat != resources.depthStencilFormat)
            {
                failure =
                    $"depth/stencil allocation was silently substituted with {resources.depthStencil.depthStencilFormat}";
                return false;
            }
            if (stencilSamplingRequired &&
                resources.depthStencil.stencilFormat !=
                    GraphicsFormat.R8_UInt)
            {
                failure =
                    "the exact D32/S8 owner did not expose the requested R8_UInt stencil shader view";
                return false;
            }
            if (resources.depthCopy.graphicsFormat != ExactDepthCopyFormat ||
                resources.gBufferA.graphicsFormat != ExactGBufferFormat ||
                resources.gBufferB.graphicsFormat != ExactGBufferFormat ||
                resources.gBufferC.graphicsFormat != ExactGBufferCFormat ||
                (sameOwnerRequired &&
                 resources.sameOwner.graphicsFormat != SameOwnerFormat) ||
                resources.stencilMask.graphicsFormat != StencilMaskFormat)
            {
                failure =
                    "one or more exact color formats were silently substituted: " +
                    $"depthCopy={resources.depthCopy.graphicsFormat} (expected {ExactDepthCopyFormat}), " +
                    $"gBufferA={resources.gBufferA.graphicsFormat} (expected {ExactGBufferFormat}), " +
                    $"gBufferB={resources.gBufferB.graphicsFormat} (expected {ExactGBufferFormat}), " +
                    $"gBufferC={resources.gBufferC.graphicsFormat} (expected {ExactGBufferCFormat}), " +
                    $"stencilMask={resources.stencilMask.graphicsFormat} (expected {StencilMaskFormat})" +
                    (sameOwnerRequired
                        ? $", sameOwner={resources.sameOwner.graphicsFormat} (expected {SameOwnerFormat})"
                        : string.Empty);
                return false;
            }
            return true;
        }

        private static RenderTexture CreateDepthStencil(
            int width,
            int height,
            GraphicsFormat format,
            string name,
            bool exposeStencilShaderView)
        {
            var descriptor = new RenderTextureDescriptor(width, height)
            {
                graphicsFormat = GraphicsFormat.None,
                depthBufferBits = 0,
                dimension = TextureDimension.Tex2D,
                volumeDepth = 1,
                msaaSamples = 1,
                bindMS = false,
                useMipMap = false,
                autoGenerateMips = false,
                enableRandomWrite = false,
                sRGB = false,
                shadowSamplingMode = ShadowSamplingMode.RawDepth,
                useDynamicScale = false
            };
            descriptor.depthStencilFormat = format;
            if (exposeStencilShaderView)
                descriptor.stencilFormat = GraphicsFormat.R8_UInt;
            var texture = new RenderTexture(descriptor)
            {
                name = name,
                filterMode = FilterMode.Point,
                wrapMode = TextureWrapMode.Clamp,
                anisoLevel = 0,
                hideFlags = HideFlags.HideAndDontSave
            };
            texture.Create();
            return texture;
        }

        private static RenderTexture CreateColorTarget(
            int width,
            int height,
            GraphicsFormat format,
            string name)
        {
            var descriptor = new RenderTextureDescriptor(width, height)
            {
                graphicsFormat = format,
                depthStencilFormat = GraphicsFormat.None,
                depthBufferBits = 0,
                dimension = TextureDimension.Tex2D,
                volumeDepth = 1,
                msaaSamples = 1,
                bindMS = false,
                useMipMap = false,
                autoGenerateMips = false,
                enableRandomWrite = false,
                sRGB = GraphicsFormatUtility.IsSRGBFormat(format),
                useDynamicScale = false
            };
            var texture = new RenderTexture(descriptor)
            {
                name = name,
                filterMode = FilterMode.Point,
                wrapMode = TextureWrapMode.Clamp,
                anisoLevel = 0,
                hideFlags = HideFlags.HideAndDontSave
            };
            texture.Create();
            return texture;
        }

        private bool ResourcesAreCreated(CameraResources resources)
        {
            return resources != null &&
                   resources.depthStencil != null && resources.depthStencil.IsCreated() &&
                   resources.depthCopy != null && resources.depthCopy.IsCreated() &&
                   resources.gBufferA != null && resources.gBufferA.IsCreated() &&
                   resources.gBufferB != null && resources.gBufferB.IsCreated() &&
                   resources.gBufferC != null && resources.gBufferC.IsCreated() &&
                   (!sameOwnerRequired ||
                    (resources.sameOwner != null && resources.sameOwner.IsCreated())) &&
                   resources.stencilMask != null && resources.stencilMask.IsCreated();
        }

        private static bool TryChooseDepthStencilFormat(out GraphicsFormat format)
        {
            if (SystemInfo.IsFormatSupported(
                    GraphicsFormat.D32_SFloat_S8_UInt,
                    FormatUsage.Render))
            {
                format = GraphicsFormat.D32_SFloat_S8_UInt;
                return true;
            }
            if (SystemInfo.IsFormatSupported(
                    GraphicsFormat.D24_UNorm_S8_UInt,
                    FormatUsage.Render))
            {
                format = GraphicsFormat.D24_UNorm_S8_UInt;
                return true;
            }
            format = GraphicsFormat.None;
            return false;
        }

        private static Dictionary<Transform, int> BuildActorIndices(
            List<CharacterDraw> draws,
            out int actorCount)
        {
            var roots = new List<Transform>();
            var seen = new HashSet<Transform>();
            foreach (CharacterDraw draw in draws)
            {
                if (draw.actorRoot != null && seen.Add(draw.actorRoot))
                    roots.Add(draw.actorRoot);
            }
            roots.Sort((left, right) =>
                string.CompareOrdinal(BuildTransformPath(left), BuildTransformPath(right)));
            actorCount = roots.Count;
            var result = new Dictionary<Transform, int>();
            for (int i = 0; i < roots.Count && i < MaximumCharacterCount; i++)
                result.Add(roots[i], i);
            return result;
        }

        private static Transform ResolveActorRoot(Renderer renderer)
        {
            CharacterRecoveryRig rig = renderer.GetComponentInParent<CharacterRecoveryRig>();
            if (rig != null)
                return rig.transform;

            Transform current = renderer.transform;
            while (current != null)
            {
                if (string.Equals(current.name, "Wulfa", StringComparison.OrdinalIgnoreCase) ||
                    string.Equals(current.name, "Zhuangfy", StringComparison.OrdinalIgnoreCase) ||
                    string.Equals(current.name, "Mifu", StringComparison.OrdinalIgnoreCase))
                {
                    return current;
                }
                if (current.parent != null &&
                    string.Equals(current.parent.name, "Characters", StringComparison.OrdinalIgnoreCase))
                {
                    return current;
                }
                current = current.parent;
            }
            return renderer.transform.root;
        }

        private static bool IsSourceBackedCharInfoPassAfterCharacterPreG(
            Renderer renderer,
            Material material)
        {
            if (IsSourceBackedCharInfoBackgroundPortraitPass(renderer, material))
                return true;

            if (renderer == null || material == null || material.shader == null ||
                renderer.gameObject.layer != 13)
            {
                return false;
            }

            EndfieldRecoveredCharInfoPresentation presentation =
                renderer.GetComponentInParent<
                    EndfieldRecoveredCharInfoPresentation>();
            if (presentation == null)
                return false;

            string shaderName = material.shader.name;
            if (renderer == presentation.floorRenderer)
            {
                return material.renderQueue == (int)RenderQueue.Geometry &&
                       string.Equals(
                           shaderName,
                           EndfieldRecoveredCharInfoPresentation.FloorShaderName,
                           StringComparison.Ordinal);
            }

            if (renderer == presentation.wallRenderer)
            {
                return material.renderQueue == (int)RenderQueue.Geometry &&
                       string.Equals(
                           shaderName,
                           EndfieldRecoveredCharInfoPresentation.WallShaderName,
                           StringComparison.Ordinal);
            }

            if (renderer == presentation.farGridRenderer)
            {
                return material.renderQueue == 2950 &&
                       string.Equals(
                           shaderName,
                           EndfieldRecoveredCharInfoPresentation.GridShaderName,
                           StringComparison.Ordinal);
            }

            return false;
        }

        private static bool IsSourceBackedCharInfoBackgroundPortraitPass(
            Renderer renderer,
            Material material)
        {
            const int SourceCharInfoBackgroundPortraitLayer = 16;
            if (renderer == null || material == null || material.shader == null ||
                renderer.gameObject.layer != SourceCharInfoBackgroundPortraitLayer ||
                material.renderQueue != (int)RenderQueue.Transparent ||
                !string.Equals(
                    material.shader.name,
                    EndfieldRecoveredCharInfoBackgroundPortrait.ShaderName,
                    StringComparison.Ordinal))
            {
                return false;
            }

            EndfieldRecoveredCharInfoBackgroundPortrait portrait =
                renderer.GetComponent<EndfieldRecoveredCharInfoBackgroundPortrait>();
            return portrait != null && portrait.portraitRenderer == renderer;
        }

        private static bool IsRendererVisibleToCamera(
            Renderer renderer,
            Camera camera,
            Plane[] frustumPlanes)
        {
            return renderer != null && renderer.enabled && renderer.gameObject.activeInHierarchy &&
                   (camera.cullingMask & (1 << renderer.gameObject.layer)) != 0 &&
                   GeometryUtility.TestPlanesAABB(frustumPlanes, renderer.bounds);
        }

        private static int CompareRenderers(Renderer left, Renderer right)
        {
            return string.CompareOrdinal(BuildRendererKey(left), BuildRendererKey(right));
        }

        private static int CompareCharacterDraws(CharacterDraw left, CharacterDraw right)
        {
            int queue = left.renderQueue.CompareTo(right.renderQueue);
            if (queue != 0)
                return queue;
            int distance = left.cameraDistanceSquared.CompareTo(right.cameraDistanceSquared);
            if (distance != 0)
                return distance;
            return string.CompareOrdinal(left.stableKey, right.stableKey);
        }

        private static string BuildRendererKey(Renderer renderer)
        {
            if (renderer == null)
                return string.Empty;
            return BuildTransformPath(renderer.transform) + "/" + renderer.GetType().Name;
        }

        private static string BuildTransformPath(Transform transform)
        {
            if (transform == null)
                return string.Empty;
            var names = new Stack<string>();
            Transform current = transform;
            while (current != null)
            {
                names.Push(current.name);
                current = current.parent;
            }
            return string.Join("/", names.ToArray());
        }

        private static uint CharacterSelectorBits(int index)
        {
            return index < 0 ? 0u : 1u << ((index + 8) & 31);
        }

        private static bool TryDecodeCharacterIndex(uint selector, out int index)
        {
            index = -1;
            if (selector == 0u || (selector & (selector - 1u)) != 0u)
                return false;
            int bit = 0;
            uint value = selector;
            while ((value >>= 1) != 0u)
                bit++;
            index = bit - 8;
            return index >= 0 && index < MaximumCharacterCount;
        }

        private static Vector3 DecodeYUpOct(float octX, float octZ)
        {
            Vector3 normal = new Vector3(
                octX,
                1.0f - Mathf.Abs(octX) - Mathf.Abs(octZ),
                octZ);
            if (normal.y < 0.0f)
            {
                float oldX = normal.x;
                normal.x = (1.0f - Mathf.Abs(normal.z)) * Mathf.Sign(oldX);
                normal.z = (1.0f - Mathf.Abs(oldX)) * Mathf.Sign(normal.z);
            }
            return normal.normalized;
        }

        private static void BindDisabled(ScriptableRenderContext context)
        {
            CommandBuffer commandBuffer = new CommandBuffer
            {
                name = "Disable recovered PreGBuffer diagnostic"
            };
            commandBuffer.SetGlobalFloat(ReadyId, 0.0f);
            commandBuffer.SetGlobalTexture(DepthStencilId, Texture2D.blackTexture);
            commandBuffer.SetGlobalTexture(DepthCopyId, Texture2D.blackTexture);
            commandBuffer.SetGlobalTexture(GBufferAId, Texture2D.blackTexture);
            commandBuffer.SetGlobalTexture(GBufferBId, Texture2D.blackTexture);
            commandBuffer.SetGlobalTexture(GBufferCId, Texture2D.blackTexture);
            commandBuffer.SetGlobalTexture(SameOwnerId, Texture2D.blackTexture);
            commandBuffer.SetGlobalTexture(StencilMaskId, Texture2D.blackTexture);
            context.ExecuteCommandBuffer(commandBuffer);
            commandBuffer.Release();
        }

        private static void DestroyMaterial(ref Material material)
        {
            if (material == null)
                return;
            if (Application.isPlaying)
                UnityEngine.Object.Destroy(material);
            else
                UnityEngine.Object.DestroyImmediate(material);
            material = null;
        }

        private static bool IsRequested()
        {
            bool enabled = IsEnabledSelectorValue(
                Environment.GetEnvironmentVariable(EnvironmentVariable));
            string[] arguments = Environment.GetCommandLineArgs();
            for (int i = 0; i < arguments.Length; i++)
            {
                string argument = arguments[i];
                if (string.Equals(
                        argument,
                        CommandLineArgument,
                        StringComparison.OrdinalIgnoreCase))
                {
                    enabled = true;
                    continue;
                }
                string prefix = CommandLineArgument + "=";
                if (argument.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                    enabled = IsEnabledSelectorValue(argument.Substring(prefix.Length));
            }
            return enabled;
        }

        private static string ReadOutputDirectory()
        {
            string output = Environment.GetEnvironmentVariable(OutputEnvironmentVariable);
            string[] arguments = Environment.GetCommandLineArgs();
            for (int i = 0; i < arguments.Length; i++)
            {
                string argument = arguments[i];
                string prefix = OutputCommandLineArgument + "=";
                if (argument.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                {
                    output = argument.Substring(prefix.Length).Trim('"');
                    continue;
                }
                if (string.Equals(
                        argument,
                        OutputCommandLineArgument,
                        StringComparison.OrdinalIgnoreCase) &&
                    i + 1 < arguments.Length)
                {
                    output = arguments[++i];
                }
            }
            if (string.IsNullOrWhiteSpace(output))
                return string.Empty;
            try
            {
                return Path.GetFullPath(output);
            }
            catch (Exception exception)
            {
                Debug.LogWarning(
                    "Recovered PreGBuffer diagnostic output path is invalid: " +
                    exception.Message);
                return string.Empty;
            }
        }

        private static bool IsEnabledSelectorValue(string rawValue)
        {
            if (string.IsNullOrWhiteSpace(rawValue))
                return false;
            string normalized = rawValue.Trim();
            return string.Equals(normalized, "1", StringComparison.OrdinalIgnoreCase) ||
                   string.Equals(normalized, "true", StringComparison.OrdinalIgnoreCase) ||
                   string.Equals(normalized, "yes", StringComparison.OrdinalIgnoreCase) ||
                   string.Equals(normalized, "on", StringComparison.OrdinalIgnoreCase);
        }

        private static void ValidateLength<T>(
            T[] data,
            int expected,
            string label,
            List<string> failures)
        {
            if (data == null)
                failures.Add(label + " returned no data");
            else if (data.Length != expected)
                failures.Add(label + $" returned {data.Length} values; expected {expected}");
        }

        private static void AddMismatchFailure(
            int count,
            string label,
            List<string> failures)
        {
            if (count > 0)
                failures.Add(label + $" validation found {count} mismatched pixel(s)");
        }

        private static bool IsFinite(float value)
        {
            return !float.IsNaN(value) && !float.IsInfinity(value);
        }

        private static uint[] SortedArray(HashSet<uint> values)
        {
            uint[] result = new uint[values.Count];
            values.CopyTo(result);
            Array.Sort(result);
            return result;
        }

        private static int[] SortedArray(HashSet<int> values)
        {
            int[] result = new int[values.Count];
            values.CopyTo(result);
            Array.Sort(result);
            return result;
        }

        private static string[] ToArray(SortedSet<string> values)
        {
            string[] result = new string[values.Count];
            values.CopyTo(result);
            return result;
        }

        private static string[] FormatSelectorBits(uint[] values)
        {
            string[] result = new string[values.Length];
            for (int i = 0; i < values.Length; i++)
                result[i] = "0x" + values[i].ToString("X8", CultureInfo.InvariantCulture);
            return result;
        }

        private static Color32 IndexColor(int index)
        {
            uint value = unchecked((uint)(index + 1) * 2654435761u);
            return new Color32(
                (byte)(64 + (value & 127u)),
                (byte)(64 + ((value >> 8) & 127u)),
                (byte)(64 + ((value >> 16) & 127u)),
                255);
        }

        private static byte ToByte(float value)
        {
            return (byte)Mathf.Clamp(Mathf.RoundToInt(value * 255.0f), 0, 255);
        }

        private static Color32[] FlipRows(Color32[] source, int width, int height)
        {
            Color32[] result = new Color32[source.Length];
            for (int y = 0; y < height; y++)
            {
                int sourceOffset = y * width;
                int targetOffset = (height - 1 - y) * width;
                Array.Copy(source, sourceOffset, result, targetOffset, width);
            }
            return result;
        }

        private static string SanitizeFileName(string value)
        {
            if (string.IsNullOrWhiteSpace(value))
                return "camera";
            char[] invalid = Path.GetInvalidFileNameChars();
            var builder = new StringBuilder(value.Length);
            foreach (char character in value)
                builder.Append(Array.IndexOf(invalid, character) >= 0 ? '_' : character);
            return builder.ToString();
        }
    }
}
