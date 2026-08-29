using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.NVIDIA;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Explicitly opt-in visual experiment for the subset of Endfield's
    /// Streamline DLAA packet representable by Unity's public NGX wrapper.
    /// This is not an exact Streamline consumer and must never become a
    /// canonical or silent fallback path.
    /// </summary>
    internal sealed class EndfieldRecoveredUnityPublicNgxProxy : IDisposable
    {
        internal static readonly int OutputTextureId =
            Shader.PropertyToID("_EndfieldUnityPublicNgxProxyOutput");
        internal const string EnvironmentVariable =
            "ENDFIELD_RECOVERED_UNITY_PUBLIC_NGX_PROXY";
        internal const string ApplicationDirectoryEnvironmentVariable =
            "ENDFIELD_RECOVERED_UNITY_PUBLIC_NGX_APP_DIR";

        private const string ExpectedNvngxDlssSha256 =
            "a8f23de8116727a160a196f9f43604284cd973d801a62bb68c19c828f78e5f3b";

        // All 2,146 readable slSetConstants packets in capture
        // 20260829T115328Z repeat this exact pixel-space sequence. The
        // capture begins on the first row below, but does not establish a
        // global phase relative to Character Info entry. This opt-in proxy
        // therefore restarts the observed order whenever its resources are
        // recreated; that local phase is experiment telemetry, not parity.
        private static readonly Vector2[] CapturedPixelJitterCycle =
        {
            new Vector2(-0.25f, 0.388888896f),
            new Vector2(0.375f, 0.0555555522f),
            new Vector2(-0.125f, -0.277777791f),
            new Vector2(0.125f, 0.277777791f),
            new Vector2(-0.375f, -0.055555582f),
            new Vector2(0.4375f, -0.388888896f),
            new Vector2(0.0f, 0.166666657f),
            new Vector2(0.25f, -0.166666687f)
        };

        internal const int CapturedIndicatorInvertAxisX = 0;
        internal const int CapturedIndicatorInvertAxisY = 1;
        internal const int CapturedPixelJitterSampleCount = 8;

        private readonly EndfieldRecoveredCombinedVelocityProducer
            combinedVelocityProducer;
        private GraphicsDevice device;
        private DLSSContext context;
        private GraphicsDeviceDebugView debugView;
        private RenderTexture inputColor;
        private RenderTexture outputColor;
        private RenderTexture combinedVelocity;
        private int width;
        private int height;
        private int jitterSampleIndex;
        private bool firstFrame = true;
        private bool pendingExecutionValidation;
        private bool initializationAttempted;
        private bool loggedActive;
        private string initializationFailure = string.Empty;
        private string failure = string.Empty;

        internal bool HasPendingValidation => pendingExecutionValidation;
        internal Vector2 LastJitterOffset { get; private set; }
        internal int LastJitterPhase { get; private set; } = -1;

        internal EndfieldRecoveredUnityPublicNgxProxy(
            EndfieldRecoveredCombinedVelocityProducer combinedVelocityProducer)
        {
            this.combinedVelocityProducer = combinedVelocityProducer;
        }

        internal bool Requested => string.Equals(
            System.Environment.GetEnvironmentVariable(EnvironmentVariable),
            "1",
            StringComparison.Ordinal);

        internal string Failure => failure;

        internal bool TryGetOutputDescriptor(
            out RenderTextureDescriptor descriptor)
        {
            descriptor = default;
            if (!ValidateTexture(
                    outputColor,
                    width,
                    height,
                    GraphicsFormat.R16G16B16A16_SFloat,
                    true,
                    out _))
            {
                return false;
            }
            descriptor = outputColor.descriptor;
            descriptor.depthStencilFormat = GraphicsFormat.None;
            return true;
        }

        internal bool TryEnqueue(
            CommandBuffer commandBuffer,
            RenderTargetIdentifier sourceColor,
            RenderTexture sceneDepth,
            RenderTexture packedSceneMV,
            int requestedWidth,
            int requestedHeight)
        {
            failure = string.Empty;
            if (!Requested)
                return false;
            if (commandBuffer == null)
                return Fail("command buffer is missing");
            if (SystemInfo.graphicsDeviceType != GraphicsDeviceType.Direct3D11)
                return Fail("the measured Endfield packet requires Direct3D11");
            if (sceneDepth == null || !sceneDepth.IsCreated())
                return Fail("reverse-Z scene depth is unavailable");
            if (sceneDepth.width != requestedWidth ||
                sceneDepth.height != requestedHeight ||
                sceneDepth.depthStencilFormat !=
                    GraphicsFormat.D32_SFloat_S8_UInt ||
                sceneDepth.antiAliasing != 1)
            {
                return Fail(
                    "reverse-Z scene depth is " +
                    $"{sceneDepth.width}x{sceneDepth.height} " +
                    $"{sceneDepth.depthStencilFormat}, msaa=" +
                    sceneDepth.antiAliasing + "; expected " +
                    $"{requestedWidth}x{requestedHeight} " +
                    "D32_SFloat_S8_UInt, msaa=1");
            }
            if (packedSceneMV == null || !packedSceneMV.IsCreated())
                return Fail("packed SceneMV is unavailable");
            if (combinedVelocityProducer == null)
                return Fail("exact combined-velocity producer is unavailable");
            if (!EnsureDevice())
                return false;
            if (pendingExecutionValidation && !ValidatePendingExecution())
                return false;
            if (!EnsureResources(
                    commandBuffer,
                    requestedWidth,
                    requestedHeight))
            {
                return false;
            }
            commandBuffer.Blit(sourceColor, inputColor);
            if (!combinedVelocityProducer.TryEnqueue(
                    commandBuffer,
                    packedSceneMV,
                    requestedWidth,
                    requestedHeight,
                    combinedVelocity,
                    out string velocityFailure))
            {
                return Fail("combined velocity failed: " + velocityFailure);
            }

            ref DLSSCommandExecutionData executeData = ref context.executeData;
            int jitterPhase = jitterSampleIndex % CapturedPixelJitterCycle.Length;
            Vector2 jitterOffset = CapturedPixelJitterCycle[jitterPhase];
            executeData.reset = firstFrame ? 1 : 0;
            executeData.sharpness = 0.0f;
            executeData.mvScaleX = 1.0f;
            executeData.mvScaleY = 1.0f;
            executeData.jitterOffsetX = jitterOffset.x;
            executeData.jitterOffsetY = jitterOffset.y;
            executeData.preExposure = 1.0f;
            executeData.subrectOffsetX = 0;
            executeData.subrectOffsetY = 0;
            executeData.subrectWidth = (uint)requestedWidth;
            executeData.subrectHeight = (uint)requestedHeight;
            executeData.invertXAxis = CapturedIndicatorInvertAxisX;
            executeData.invertYAxis = CapturedIndicatorInvertAxisY;

            var textures = new DLSSTextureTable
            {
                colorInput = inputColor,
                colorOutput = outputColor,
                depth = sceneDepth,
                motionVectors = combinedVelocity,
                transparencyMask = null,
                exposureTexture = null,
                biasColorMask = null
            };
            device.ExecuteDLSS(commandBuffer, context, in textures);
            commandBuffer.SetGlobalTexture(OutputTextureId, outputColor);
            pendingExecutionValidation = true;
            firstFrame = false;
            LastJitterOffset = jitterOffset;
            LastJitterPhase = jitterPhase;
            jitterSampleIndex = (jitterPhase + 1) %
                CapturedPixelJitterCycle.Length;

            if (!loggedActive)
            {
                Debug.Log(
                    "UnityPublicNgxProxy active as an opt-in Endminf visual " +
                    $"experiment at {requestedWidth}x{requestedHeight}: " +
                    "R11G11B10 HDR input, RGBA16F output, reverse depth, " +
                    "exact R16G16 combined velocity, " +
                    "captured 8-sample pixel jitter, zero sharpness, unit " +
                    "motion scale, indicator axes X=0/Y=1, and no masks. " +
                    "This public MaximumQuality wrapper is not Streamline " +
                    "DLAA mode 6 and is not parity evidence.");
                loggedActive = true;
            }
            return true;
        }

        private bool EnsureDevice()
        {
            if (device != null && debugView != null)
                return true;
            if (initializationAttempted)
                return Fail(string.IsNullOrEmpty(initializationFailure)
                    ? "Unity's public DLSS device initialization was rejected"
                    : initializationFailure);
            initializationAttempted = true;
            if (GraphicsDevice.device != null)
            {
                return FailInitialization(
                    "Unity's NVIDIA GraphicsDevice was already initialized; " +
                    "the pinned application-directory contract cannot be established");
            }
            string applicationDirectory = System.Environment.GetEnvironmentVariable(
                ApplicationDirectoryEnvironmentVariable);
            if (string.IsNullOrWhiteSpace(applicationDirectory))
            {
                return FailInitialization(
                    ApplicationDirectoryEnvironmentVariable +
                    " must name the exact installed game directory");
            }
            applicationDirectory = Path.GetFullPath(applicationDirectory);
            string dlssPath = Path.Combine(applicationDirectory, "nvngx_dlss.dll");
            if (!File.Exists(dlssPath))
                return FailInitialization(
                    "nvngx_dlss.dll is missing from " + applicationDirectory);
            if (!string.Equals(
                    ComputeSha256(dlssPath),
                    ExpectedNvngxDlssSha256,
                    StringComparison.OrdinalIgnoreCase))
            {
                return FailInitialization(
                    "installed nvngx_dlss.dll does not match the pinned client");
            }
            if (!NVUnityPlugin.Load())
                return FailInitialization("Unity NVUnityPlugin failed to load");
            device = GraphicsDevice.CreateGraphicsDevice(
                "endfield-graph-shader-lab",
                applicationDirectory);
            if (device == null ||
                !device.IsFeatureAvailable(GraphicsDeviceFeature.DLSS))
            {
                return FailInitialization(
                    "Unity's public DLSS feature is unavailable");
            }
            debugView = device.CreateDebugView();
            if (debugView == null)
            {
                return FailInitialization(
                    "Unity's public DLSS debug view is unavailable");
            }
            return true;
        }

        internal bool ValidatePendingAfterSynchronizedRender(
            out string validationFailure)
        {
            validationFailure = string.Empty;
            if (!Requested)
                return true;
            if (!pendingExecutionValidation)
            {
                validationFailure =
                    "no public DLSS execution is pending validation";
                return false;
            }
            bool valid = ValidatePendingExecution();
            validationFailure = valid ? string.Empty : failure;
            return valid;
        }

        private bool ValidatePendingExecution()
        {
            if (device == null || debugView == null)
                return Fail("DLSS debug validation state is unavailable");
            device.UpdateDebugView(debugView);
            DLSSDebugFeatureInfos[] infos =
                debugView.dlssFeatureInfos?.ToArray();
            if (infos == null || infos.Length != 1)
            {
                return Fail(
                    "post-execution debug view contains " +
                    (infos == null ? 0 : infos.Length) +
                    " feature rows; expected exactly one");
            }
            if (!infos[0].validFeature)
                return Fail("the pending public DLSS execution was invalid");
            pendingExecutionValidation = false;
            return true;
        }

        private bool EnsureResources(
            CommandBuffer commandBuffer,
            int requestedWidth,
            int requestedHeight)
        {
            bool resourcesExact =
                context != null &&
                ValidateTexture(
                    inputColor,
                    requestedWidth,
                    requestedHeight,
                    GraphicsFormat.B10G11R11_UFloatPack32,
                    false,
                    out _) &&
                ValidateTexture(
                    outputColor,
                    requestedWidth,
                    requestedHeight,
                    GraphicsFormat.R16G16B16A16_SFloat,
                    true,
                    out _) &&
                ValidateTexture(
                    combinedVelocity,
                    requestedWidth,
                    requestedHeight,
                    EndfieldRecoveredCombinedVelocityProducer.OutputFormat,
                    true,
                    out _);
            if (resourcesExact && width == requestedWidth &&
                height == requestedHeight)
            {
                return true;
            }
            if (requestedWidth <= 0 || requestedHeight <= 0)
                return Fail("requested extent is invalid");

            ReleaseFeatureAndTextures();
            width = requestedWidth;
            height = requestedHeight;
            inputColor = CreateColorTexture(
                "Endfield UnityPublicNgxProxy Input",
                requestedWidth,
                requestedHeight,
                GraphicsFormat.B10G11R11_UFloatPack32,
                false);
            outputColor = CreateColorTexture(
                "Endfield UnityPublicNgxProxy Output",
                requestedWidth,
                requestedHeight,
                GraphicsFormat.R16G16B16A16_SFloat,
                true);
            combinedVelocity = CreateTexture(
                "Endfield UnityPublicNgxProxy Combined Velocity",
                requestedWidth,
                requestedHeight,
                EndfieldRecoveredCombinedVelocityProducer.OutputFormat,
                true,
                FilterMode.Point);
            bool inputExact = ValidateTexture(
                inputColor,
                requestedWidth,
                requestedHeight,
                GraphicsFormat.B10G11R11_UFloatPack32,
                false,
                out string inputFailure);
            bool outputExact = ValidateTexture(
                outputColor,
                requestedWidth,
                requestedHeight,
                GraphicsFormat.R16G16B16A16_SFloat,
                true,
                out string outputFailure);
            bool velocityExact = ValidateTexture(
                combinedVelocity,
                requestedWidth,
                requestedHeight,
                EndfieldRecoveredCombinedVelocityProducer.OutputFormat,
                true,
                out string velocityFailure);
            if (!inputExact || !outputExact || !velocityExact)
            {
                ReleaseFeatureAndTextures();
                return Fail(
                    "native-scale proxy texture validation failed: " +
                    string.Join(
                        "; ",
                        new[] { inputFailure, outputFailure, velocityFailure }
                            .Where(value => !string.IsNullOrEmpty(value))));
            }

            var initializationData = new DLSSCommandInitializationData
            {
                inputRTWidth = (uint)requestedWidth,
                inputRTHeight = (uint)requestedHeight,
                outputRTWidth = (uint)requestedWidth,
                outputRTHeight = (uint)requestedHeight,
                quality = DLSSQuality.MaximumQuality,
                featureFlags = DLSSFeatureFlags.IsHDR |
                    DLSSFeatureFlags.DepthInverted
            };
            context = device.CreateFeature(commandBuffer, in initializationData);
            if (context == null)
            {
                ReleaseFeatureAndTextures();
                return Fail("Unity's public DLSS context creation was rejected");
            }
            firstFrame = true;
            return true;
        }

        private static bool ValidateTexture(
            RenderTexture texture,
            int expectedWidth,
            int expectedHeight,
            GraphicsFormat expectedFormat,
            bool expectedRandomWrite,
            out string validationFailure)
        {
            validationFailure = string.Empty;
            if (texture == null || !texture.IsCreated())
            {
                validationFailure = "texture is unavailable";
                return false;
            }
            if (texture.width != expectedWidth ||
                texture.height != expectedHeight ||
                texture.graphicsFormat != expectedFormat ||
                texture.enableRandomWrite != expectedRandomWrite ||
                texture.antiAliasing != 1)
            {
                validationFailure =
                    $"{texture.name} is {texture.width}x{texture.height} " +
                    $"{texture.graphicsFormat}, randomWrite=" +
                    texture.enableRandomWrite + ", msaa=" +
                    texture.antiAliasing + "; expected " +
                    $"{expectedWidth}x{expectedHeight} {expectedFormat}, " +
                    $"randomWrite={expectedRandomWrite}, msaa=1";
                return false;
            }
            return true;
        }

        private static RenderTexture CreateColorTexture(
            string name,
            int width,
            int height,
            GraphicsFormat format,
            bool randomWrite)
        {
            return CreateTexture(
                name,
                width,
                height,
                format,
                randomWrite,
                FilterMode.Bilinear);
        }

        private static RenderTexture CreateTexture(
            string name,
            int width,
            int height,
            GraphicsFormat format,
            bool randomWrite,
            FilterMode filterMode)
        {
            var descriptor = new RenderTextureDescriptor(width, height)
            {
                graphicsFormat = format,
                depthStencilFormat = GraphicsFormat.None,
                msaaSamples = 1,
                volumeDepth = 1,
                dimension = TextureDimension.Tex2D,
                sRGB = false,
                useMipMap = false,
                autoGenerateMips = false,
                enableRandomWrite = randomWrite
            };
            var texture = new RenderTexture(descriptor)
            {
                name = name,
                filterMode = filterMode,
                wrapMode = TextureWrapMode.Clamp,
                hideFlags = HideFlags.HideAndDontSave
            };
            texture.Create();
            return texture;
        }

        private bool Fail(string reason)
        {
            failure = reason ?? string.Empty;
            return false;
        }

        private bool FailInitialization(string reason)
        {
            initializationFailure = reason ?? string.Empty;
            return Fail(initializationFailure);
        }

        private static string ComputeSha256(string path)
        {
            using (FileStream stream = File.OpenRead(path))
            using (SHA256 sha256 = SHA256.Create())
                return BitConverter.ToString(sha256.ComputeHash(stream))
                    .Replace("-", string.Empty)
                    .ToLowerInvariant();
        }

        public void Dispose()
        {
            ReleaseFeatureAndTextures();
            if (device != null && debugView != null)
                device.DeleteDebugView(debugView);
            debugView = null;
            device = null;
        }

        private void ReleaseFeatureAndTextures()
        {
            if (device != null && context != null)
            {
                var commandBuffer = new CommandBuffer
                {
                    name = "Release Endfield UnityPublicNgxProxy"
                };
                device.DestroyFeature(commandBuffer, context);
                Graphics.ExecuteCommandBuffer(commandBuffer);
                commandBuffer.Release();
            }
            context = null;
            DestroyTexture(ref inputColor);
            DestroyTexture(ref outputColor);
            DestroyTexture(ref combinedVelocity);
            width = 0;
            height = 0;
            jitterSampleIndex = 0;
            LastJitterOffset = Vector2.zero;
            LastJitterPhase = -1;
            firstFrame = true;
            pendingExecutionValidation = false;
        }

        private static void DestroyTexture(ref RenderTexture texture)
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
}
