using System;
using System.Security.Cryptography;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Default-off diagnostic reconstruction of the installed
    /// HGLowResDirectionalShadowPass receiver. It consumes only lab-prefixed
    /// PreGBuffer and directional-CSM resources and never publishes the
    /// canonical _LowResDirectionalShadow texture.
    /// </summary>
    internal sealed class EndfieldRecoveredLowResDirectionalShadowProducer :
        IDisposable
    {
        internal const string EnvironmentVariable =
            "ENDFIELD_RECOVERED_LOW_RES_DIRECTIONAL_SHADOW";
        internal const string CommandLineArgument =
            "-endfield-recovered-low-res-directional-shadow";
        internal const float ResolutionScale = 0.25f;

        private const string ShaderName =
            "Hidden/Endfield/HGRPCompat/RecoveredLowResDirectionalShadow";
        private const string BlurShaderName =
            "Hidden/Endfield/HGRPCompat/RecoveredLowResDirectionalShadowBlur";

        private static readonly GraphicsFormat OutputFormat =
            GraphicsFormat.R8_UNorm;
        private static readonly GraphicsFormat DebugFormat =
            GraphicsFormat.R32G32B32A32_SFloat;
        private static readonly int DepthTextureId =
            Shader.PropertyToID(
                "_EndfieldRecoveredLowResDirectionalCameraDepthTexture");
        private static readonly int InverseViewProjectionId =
            Shader.PropertyToID(
                "_EndfieldRecoveredLowResDirectionalInverseGpuViewProjection");
        private static readonly int CameraDepthTexelSizeId =
            Shader.PropertyToID(
                "_EndfieldRecoveredLowResDirectionalCameraDepthTexelSize");
        private static readonly int ZBufferParamsId =
            Shader.PropertyToID(
                "_EndfieldRecoveredLowResDirectionalZBufferParams");
        private static readonly int ContactShadowId =
            Shader.PropertyToID(
                "_EndfieldRecoveredLowResDirectionalContactShadow");
        private static readonly int OutputId =
            Shader.PropertyToID(
                "_EndfieldRecoveredLowResDirectionalShadow");
        private static readonly int RawOutputId =
            Shader.PropertyToID(
                "_EndfieldRecoveredLowResDirectionalShadowRaw");
        private static readonly int HorizontalOutputId =
            Shader.PropertyToID(
                "_EndfieldRecoveredLowResDirectionalShadowHorizontal");
        private static readonly int OutputReadyId =
            Shader.PropertyToID(
                "_EndfieldRecoveredLowResDirectionalShadowReady");
        private static readonly int OutputTexelSizeId =
            Shader.PropertyToID(
                "_EndfieldRecoveredLowResDirectionalShadowTexelSize");
        private static readonly int BlurInputId =
            Shader.PropertyToID(
                "_EndfieldRecoveredLowResDirectionalBlurInput");
        private static readonly int BlurRTSizeId =
            Shader.PropertyToID(
                "_EndfieldRecoveredLowResDirectionalBlurRTSize");

        private readonly bool requested;
        private Material material;
        private Material blurMaterial;
        private RenderTexture output;
        private RenderTexture horizontalBlur;
        private RenderTexture verticalBlur;
        private RenderTexture debugOutput;
        private bool readbackRequested;
        private bool blurredReadbackRequested;
        private bool debugReadbackRequested;
        private bool loggedDebugUnavailable;
        private bool loggedActive;
        private string lastFailure = string.Empty;
        private bool publicationValid;
        private int publicationCameraInstanceId;
        private int publicationFrame;
        private int publicationWidth;
        private int publicationHeight;
        private bool disposed;

        internal EndfieldRecoveredLowResDirectionalShadowProducer(
            bool requiredByDownstreamProducer = false)
        {
            requested =
                requiredByDownstreamProducer ||
                ReadBooleanEnvironment(EnvironmentVariable) ||
                HasCommandLineArgument(CommandLineArgument);
            Shader.SetGlobalTexture(OutputId, Texture2D.whiteTexture);
            Shader.SetGlobalTexture(RawOutputId, Texture2D.whiteTexture);
            Shader.SetGlobalTexture(HorizontalOutputId, Texture2D.whiteTexture);
            Shader.SetGlobalFloat(OutputReadyId, 0.0f);
            if (!requested)
                return;

            Shader shader = Shader.Find(ShaderName);
            if (shader != null && shader.isSupported)
            {
                material = new Material(shader)
                {
                    name =
                        "Recovered Low-Resolution Directional Shadow Receiver",
                    hideFlags = HideFlags.HideAndDontSave
                };
            }
            Shader blurShader = Shader.Find(BlurShaderName);
            if (blurShader != null && blurShader.isSupported)
            {
                blurMaterial = new Material(blurShader)
                {
                    name =
                        "Recovered Low-Resolution Directional Shadow Blur",
                    hideFlags = HideFlags.HideAndDontSave
                };
            }
        }

        internal bool Requested => requested;

        internal bool Render(
            ScriptableRenderContext context,
            Camera camera,
            EndfieldRecoveredPreGBufferDiagnostic.Frame preGBufferFrame,
            bool directionalCSMReady,
            RenderTexture postGBufferDepth,
            EndfieldRecoveredContactShadowProducer.Frame contactShadowFrame,
            RenderTargetIdentifier restoreTarget)
        {
            if (disposed)
            {
                throw new ObjectDisposedException(
                    nameof(
                        EndfieldRecoveredLowResDirectionalShadowProducer));
            }
            if (!requested)
                return false;
            publicationValid = false;
            if (camera == null)
                return Fail(context, restoreTarget, "the active camera is null");
            if (material == null)
            {
                return Fail(
                    context,
                    restoreTarget,
                    $"shader '{ShaderName}' is missing or unsupported");
            }
            if (blurMaterial == null)
            {
                return Fail(
                    context,
                    restoreTarget,
                    $"shader '{BlurShaderName}' is missing or unsupported");
            }
            if (!directionalCSMReady)
            {
                return Fail(
                    context,
                    restoreTarget,
                    "the recovered directional CSM producer was not ready");
            }
            if (!preGBufferFrame.ready ||
                preGBufferFrame.depthCopy == null ||
                !preGBufferFrame.depthCopy.IsCreated())
            {
                string detail = string.IsNullOrEmpty(preGBufferFrame.failure)
                    ? "the recovered PreGBuffer depth copy was not ready"
                    : "the recovered PreGBuffer depth copy was not ready: " +
                      preGBufferFrame.failure;
                return Fail(context, restoreTarget, detail);
            }
            if (preGBufferFrame.cameraInstanceId != camera.GetInstanceID())
            {
                return Fail(
                    context,
                    restoreTarget,
                    "the recovered PreGBuffer frame belongs to another camera");
            }
            if (!SystemInfo.usesReversedZBuffer)
            {
                return Fail(
                    context,
                    restoreTarget,
                    "the active backend does not expose the installed reversed-Z contract");
            }

            int width = Mathf.Max(
                1,
                Mathf.CeilToInt(
                    preGBufferFrame.width * ResolutionScale));
            int height = Mathf.Max(
                1,
                Mathf.CeilToInt(
                    preGBufferFrame.height * ResolutionScale));
            string failure;
            if (!EnsureOutput(width, height, out failure))
                return Fail(context, restoreTarget, failure);
            if (!EnsureBlurOutputs(width, height, out failure))
                return Fail(context, restoreTarget, failure);
            string debugFailure;
            bool debugOutputReady =
                EnsureDebugOutput(width, height, out debugFailure);
            if (!debugOutputReady && !loggedDebugUnavailable)
            {
                Debug.LogWarning(
                    "Recovered low-resolution directional shadow depth-" +
                    "alignment validation is unavailable: " + debugFailure +
                    ". The exact R8 receiver remains active.");
                loggedDebugUnavailable = true;
            }

            float near = camera.nearClipPlane;
            float far = camera.farClipPlane;
            if (!(near > 0.0f) ||
                !(far > near) ||
                float.IsNaN(near) ||
                float.IsNaN(far) ||
                float.IsInfinity(near) ||
                float.IsInfinity(far))
            {
                return Fail(
                    context,
                    restoreTarget,
                    $"camera near/far planes are invalid ({near:R}, {far:R})");
            }
            Vector4 zBufferParams = new Vector4(
                -1.0f + far / near,
                1.0f,
                (-1.0f + far / near) / far,
                1.0f / far);

            CommandBuffer commandBuffer = new CommandBuffer
            {
                name =
                    "Recovered installed low-resolution directional shadow"
            };
            try
            {
                // Retail builds this receiver after GBuffer, so consume the
                // canonical post-GBuffer depth when the pipeline owns a
                // physical attachment. This includes identity-gated M27
                // depth while retaining the earlier character prepass.
                commandBuffer.SetGlobalTexture(
                    DepthTextureId,
                    postGBufferDepth != null && postGBufferDepth.IsCreated()
                        ? postGBufferDepth
                        : preGBufferFrame.depthCopy);
                commandBuffer.SetGlobalMatrix(
                    InverseViewProjectionId,
                    preGBufferFrame.inverseGpuViewProjection);
                commandBuffer.SetGlobalVector(
                    CameraDepthTexelSizeId,
                    new Vector4(
                        1.0f / preGBufferFrame.width,
                        1.0f / preGBufferFrame.height,
                        preGBufferFrame.width,
                        preGBufferFrame.height));
                commandBuffer.SetGlobalVector(
                    ZBufferParamsId,
                    zBufferParams);
                // The exact source branch is retained in both states. A
                // separately requested and ready contact producer supplies the
                // retail-shaped RG displacement; otherwise black makes
                // R < 0.99999 and keeps the established directional-only
                // baseline byte-identical.
                commandBuffer.SetGlobalTexture(
                    ContactShadowId,
                    contactShadowFrame.ready &&
                    contactShadowFrame.texture != null
                        ? contactShadowFrame.texture
                        : Texture2D.blackTexture);
                commandBuffer.SetRenderTarget(output);
                commandBuffer.SetViewport(
                    new Rect(0.0f, 0.0f, width, height));
                commandBuffer.ClearRenderTarget(
                    false,
                    true,
                    Color.white);
                commandBuffer.DrawProcedural(
                    Matrix4x4.identity,
                    material,
                    0,
                    MeshTopology.Triangles,
                    3,
                    1);
                commandBuffer.SetGlobalTexture(RawOutputId, output);
                commandBuffer.SetGlobalVector(
                    BlurRTSizeId,
                    new Vector4(
                        1.0f / width,
                        1.0f / height,
                        width,
                        height));
                commandBuffer.SetGlobalTexture(BlurInputId, output);
                commandBuffer.SetRenderTarget(horizontalBlur);
                commandBuffer.SetViewport(
                    new Rect(0.0f, 0.0f, width, height));
                commandBuffer.DrawProcedural(
                    Matrix4x4.identity,
                    blurMaterial,
                    0,
                    MeshTopology.Triangles,
                    3,
                    1);
                commandBuffer.SetGlobalTexture(
                    HorizontalOutputId,
                    horizontalBlur);
                commandBuffer.SetGlobalTexture(
                    BlurInputId,
                    horizontalBlur);
                commandBuffer.SetRenderTarget(verticalBlur);
                commandBuffer.DrawProcedural(
                    Matrix4x4.identity,
                    blurMaterial,
                    1,
                    MeshTopology.Triangles,
                    3,
                    1);
                commandBuffer.SetGlobalTexture(OutputId, verticalBlur);
                commandBuffer.SetGlobalVector(
                    OutputTexelSizeId,
                    new Vector4(
                        1.0f / width,
                        1.0f / height,
                        width,
                        height));
                commandBuffer.SetGlobalFloat(OutputReadyId, 1.0f);
                if (debugOutputReady)
                {
                    commandBuffer.SetRenderTarget(debugOutput);
                    commandBuffer.SetViewport(
                        new Rect(0.0f, 0.0f, width, height));
                    commandBuffer.ClearRenderTarget(
                        false,
                        true,
                        Color.clear);
                    commandBuffer.DrawProcedural(
                        Matrix4x4.identity,
                        material,
                        0,
                        MeshTopology.Triangles,
                        3,
                        1);
                    RequestOneShotDebugReadback(
                        commandBuffer,
                        camera.name,
                        width,
                        height);
                }
                RequestOneShotReadback(
                    commandBuffer,
                    camera.name,
                    width,
                    height);
                RequestOneShotBlurredReadback(
                    commandBuffer,
                    camera.name,
                    width,
                    height);
                commandBuffer.SetRenderTarget(restoreTarget);
                context.ExecuteCommandBuffer(commandBuffer);
            }
            catch (Exception exception)
            {
                commandBuffer.Clear();
                commandBuffer.Release();
                return Fail(
                    context,
                    restoreTarget,
                    "render command construction failed: " +
                    exception.Message);
            }
            commandBuffer.Release();

            publicationValid = true;
            publicationCameraInstanceId = camera.GetInstanceID();
            publicationFrame = Time.frameCount;
            publicationWidth = width;
            publicationHeight = height;

            lastFailure = string.Empty;
            if (!loggedActive)
            {
                Debug.Log(
                    "Recovered installed low-resolution directional shadow " +
                    "active (default-off): exact ceil(camera*0.25) R8_UNorm " +
                    $"target={width}x{height}, 4x4 depth gathers, 0.1 linear-" +
                    "depth edge sentinel, split-sphere/dither cascade select, " +
                    "separate atlas vectors, 16 Poisson gathers / 64 reversed-" +
                    "Z comparisons, signed cubic output filter, and installed " +
                    "clamped 7x1 then 1x7 means. Contact displacement is " +
                    (contactShadowFrame.ready
                        ? "supplied by the separately gated recovered " +
                          "ContactShadowCS/RayTracingV2 producer. "
                        : "the exact black/no-offset fallback because its " +
                          "separate producer is disabled or unavailable. ") +
                    "Output is lab-prefixed; " +
                    "canonical _LowResDirectionalShadow remains untouched.");
                loggedActive = true;
            }
            return true;
        }

        internal bool TryGetCurrentPublication(
            Camera camera,
            int width,
            int height,
            out RenderTexture publishedTexture)
        {
            publishedTexture = null;
            if (!publicationValid ||
                camera == null ||
                publicationCameraInstanceId != camera.GetInstanceID() ||
                publicationFrame != Time.frameCount ||
                publicationWidth != Mathf.Max(
                    1,
                    Mathf.CeilToInt(width * ResolutionScale)) ||
                publicationHeight != Mathf.Max(
                    1,
                    Mathf.CeilToInt(height * ResolutionScale)) ||
                verticalBlur == null ||
                !verticalBlur.IsCreated())
            {
                return false;
            }
            publishedTexture = verticalBlur;
            return true;
        }

        private bool EnsureDebugOutput(
            int width,
            int height,
            out string failure)
        {
            failure = string.Empty;
            if (!SystemInfo.IsFormatSupported(DebugFormat, FormatUsage.Render))
            {
                failure =
                    "R32G32B32A32_SFloat render-target support is unavailable";
                return false;
            }
            if (debugOutput != null &&
                debugOutput.IsCreated() &&
                debugOutput.width == width &&
                debugOutput.height == height &&
                debugOutput.graphicsFormat == DebugFormat)
            {
                return true;
            }

            ReleaseDebugOutput();
            RenderTextureDescriptor descriptor =
                new RenderTextureDescriptor(width, height)
                {
                    graphicsFormat = DebugFormat,
                    depthStencilFormat = GraphicsFormat.None,
                    depthBufferBits = 0,
                    dimension = TextureDimension.Tex2D,
                    volumeDepth = 1,
                    msaaSamples = 1,
                    bindMS = false,
                    useMipMap = false,
                    autoGenerateMips = false,
                    enableRandomWrite = false,
                    sRGB = false,
                    shadowSamplingMode = ShadowSamplingMode.None,
                    useDynamicScale = false
                };
            debugOutput = new RenderTexture(descriptor)
            {
                name =
                    "Recovered Low-Resolution Directional Shadow Alignment",
                filterMode = FilterMode.Point,
                wrapMode = TextureWrapMode.Clamp,
                anisoLevel = 0,
                hideFlags = HideFlags.HideAndDontSave
            };
            if (!debugOutput.Create() ||
                !debugOutput.IsCreated() ||
                debugOutput.graphicsFormat != DebugFormat)
            {
                failure =
                    $"the {width}x{height} RGBA32F validation target could " +
                    "not be allocated without substitution";
                ReleaseDebugOutput();
                return false;
            }
            return true;
        }

        internal void ResetAfterForward(ScriptableRenderContext context)
        {
            if (!requested || disposed)
                return;
            CommandBuffer commandBuffer = new CommandBuffer
            {
                name =
                    "Reset recovered low-resolution directional shadow publication"
            };
            commandBuffer.SetGlobalFloat(OutputReadyId, 0.0f);
            commandBuffer.SetGlobalTexture(OutputId, Texture2D.whiteTexture);
            commandBuffer.SetGlobalTexture(
                RawOutputId,
                Texture2D.whiteTexture);
            commandBuffer.SetGlobalTexture(
                HorizontalOutputId,
                Texture2D.whiteTexture);
            context.ExecuteCommandBuffer(commandBuffer);
            commandBuffer.Release();
        }

        private bool EnsureOutput(
            int width,
            int height,
            out string failure)
        {
            failure = string.Empty;
            if (!SystemInfo.IsFormatSupported(OutputFormat, FormatUsage.Render))
            {
                failure =
                    "the active graphics backend cannot render exact R8_UNorm";
                return false;
            }
            if (output != null &&
                output.IsCreated() &&
                output.width == width &&
                output.height == height &&
                output.graphicsFormat == OutputFormat)
            {
                return true;
            }

            ReleaseOutput();
            RenderTextureDescriptor descriptor =
                new RenderTextureDescriptor(width, height)
                {
                    graphicsFormat = OutputFormat,
                    depthStencilFormat = GraphicsFormat.None,
                    depthBufferBits = 0,
                    dimension = TextureDimension.Tex2D,
                    volumeDepth = 1,
                    msaaSamples = 1,
                    bindMS = false,
                    useMipMap = false,
                    autoGenerateMips = false,
                    enableRandomWrite = false,
                    sRGB = false,
                    shadowSamplingMode = ShadowSamplingMode.None,
                    useDynamicScale = false
                };
            output = new RenderTexture(descriptor)
            {
                name =
                    "Recovered Low-Resolution Directional Shadow Diagnostic",
                filterMode = FilterMode.Bilinear,
                wrapMode = TextureWrapMode.Clamp,
                anisoLevel = 0,
                hideFlags = HideFlags.HideAndDontSave
            };
            if (!output.Create() ||
                !output.IsCreated() ||
                output.graphicsFormat != OutputFormat)
            {
                failure =
                    $"the exact {width}x{height} R8_UNorm target could not be " +
                    "allocated without substitution";
                ReleaseOutput();
                return false;
            }
            return true;
        }

        private bool EnsureBlurOutputs(
            int width,
            int height,
            out string failure)
        {
            failure = string.Empty;
            if (horizontalBlur != null &&
                horizontalBlur.IsCreated() &&
                horizontalBlur.width == width &&
                horizontalBlur.height == height &&
                horizontalBlur.graphicsFormat == OutputFormat &&
                verticalBlur != null &&
                verticalBlur.IsCreated() &&
                verticalBlur.width == width &&
                verticalBlur.height == height &&
                verticalBlur.graphicsFormat == OutputFormat)
            {
                return true;
            }

            ReleaseBlurOutputs();
            horizontalBlur = CreateBlurTarget(
                width,
                height,
                "Recovered Low-Resolution Directional Shadow Horizontal");
            verticalBlur = CreateBlurTarget(
                width,
                height,
                "Recovered Low-Resolution Directional Shadow Vertical");
            if (horizontalBlur == null || verticalBlur == null)
            {
                failure =
                    $"the two exact {width}x{height} R8_UNorm blur targets " +
                    "could not be allocated without substitution";
                ReleaseBlurOutputs();
                return false;
            }
            return true;
        }

        private static RenderTexture CreateBlurTarget(
            int width,
            int height,
            string name)
        {
            RenderTextureDescriptor descriptor =
                new RenderTextureDescriptor(width, height)
                {
                    graphicsFormat = OutputFormat,
                    depthStencilFormat = GraphicsFormat.None,
                    depthBufferBits = 0,
                    dimension = TextureDimension.Tex2D,
                    volumeDepth = 1,
                    msaaSamples = 1,
                    bindMS = false,
                    useMipMap = false,
                    autoGenerateMips = false,
                    enableRandomWrite = false,
                    sRGB = false,
                    shadowSamplingMode = ShadowSamplingMode.None,
                    useDynamicScale = false
                };
            RenderTexture texture = new RenderTexture(descriptor)
            {
                name = name,
                filterMode = FilterMode.Bilinear,
                wrapMode = TextureWrapMode.Clamp,
                anisoLevel = 0,
                hideFlags = HideFlags.HideAndDontSave
            };
            if (texture.Create() &&
                texture.IsCreated() &&
                texture.graphicsFormat == OutputFormat)
            {
                return texture;
            }
            if (texture.IsCreated())
                texture.Release();
            DestroyResource(texture);
            return null;
        }

        private void RequestOneShotReadback(
            CommandBuffer commandBuffer,
            string cameraName,
            int width,
            int height)
        {
            if (readbackRequested ||
                commandBuffer == null ||
                output == null ||
                !SystemInfo.supportsAsyncGPUReadback)
            {
                return;
            }

            readbackRequested = true;
            commandBuffer.RequestAsyncReadback(output, 0, request =>
            {
                if (request.hasError)
                {
                    Debug.LogWarning(
                        "Recovered low-resolution directional shadow R8 GPU " +
                        "readback failed; the diagnostic texture remains available.");
                    return;
                }

                byte[] raw = request.GetData<byte>().ToArray();
                int zeroSamples = 0;
                int midpointSamples = 0;
                int oneSamples = 0;
                int intermediateSamples = 0;
                byte minimum = byte.MaxValue;
                byte maximum = byte.MinValue;
                foreach (byte sample in raw)
                {
                    minimum = Math.Min(minimum, sample);
                    maximum = Math.Max(maximum, sample);
                    if (sample == 0)
                        zeroSamples++;
                    else if (sample == 127 || sample == 128)
                        midpointSamples++;
                    else if (sample == 255)
                        oneSamples++;
                    else
                        intermediateSamples++;
                }

                byte[] digest;
                using (SHA256 sha = SHA256.Create())
                    digest = sha.ComputeHash(raw);
                string sha256 = BitConverter.ToString(digest)
                    .Replace("-", string.Empty)
                    .ToLowerInvariant();
                Debug.Log(
                    "Recovered low-resolution directional shadow GPU readback: " +
                    $"camera={cameraName}, size={width}x{height}, " +
                    "format=R8_UNorm, " +
                    $"bytes={raw.Length}, minByte={minimum}, maxByte={maximum}, " +
                    $"zeroSamples={zeroSamples}, " +
                    $"midpointSamples={midpointSamples}, " +
                    $"oneSamples={oneSamples}, " +
                    $"intermediateSamples={intermediateSamples}, " +
                    $"sha256={sha256}.");
            });
        }

        private void RequestOneShotBlurredReadback(
            CommandBuffer commandBuffer,
            string cameraName,
            int width,
            int height)
        {
            if (blurredReadbackRequested ||
                commandBuffer == null ||
                verticalBlur == null ||
                !SystemInfo.supportsAsyncGPUReadback)
            {
                return;
            }

            blurredReadbackRequested = true;
            commandBuffer.RequestAsyncReadback(verticalBlur, 0, request =>
            {
                if (request.hasError)
                {
                    Debug.LogWarning(
                        "Recovered blurred low-resolution directional " +
                        "shadow R8 GPU readback failed.");
                    return;
                }

                byte[] raw = request.GetData<byte>().ToArray();
                int zeroSamples = 0;
                int midpointSamples = 0;
                int oneSamples = 0;
                int intermediateSamples = 0;
                byte minimum = byte.MaxValue;
                byte maximum = byte.MinValue;
                foreach (byte sample in raw)
                {
                    minimum = Math.Min(minimum, sample);
                    maximum = Math.Max(maximum, sample);
                    if (sample == 0)
                        zeroSamples++;
                    else if (sample == 127 || sample == 128)
                        midpointSamples++;
                    else if (sample == 255)
                        oneSamples++;
                    else
                        intermediateSamples++;
                }

                byte[] digest;
                using (SHA256 sha = SHA256.Create())
                    digest = sha.ComputeHash(raw);
                string sha256 = BitConverter.ToString(digest)
                    .Replace("-", string.Empty)
                    .ToLowerInvariant();
                Debug.Log(
                    "Recovered blurred low-resolution directional shadow " +
                    $"GPU readback: camera={cameraName}, size={width}x{height}, " +
                    "format=R8_UNorm, passes=(7x1,1x7), " +
                    $"bytes={raw.Length}, minByte={minimum}, " +
                    $"maxByte={maximum}, zeroSamples={zeroSamples}, " +
                    $"midpointSamples={midpointSamples}, " +
                    $"oneSamples={oneSamples}, " +
                    $"intermediateSamples={intermediateSamples}, " +
                    $"sha256={sha256}.");
            });
        }

        private void RequestOneShotDebugReadback(
            CommandBuffer commandBuffer,
            string cameraName,
            int width,
            int height)
        {
            if (debugReadbackRequested ||
                commandBuffer == null ||
                debugOutput == null ||
                !SystemInfo.supportsAsyncGPUReadback)
            {
                return;
            }

            debugReadbackRequested = true;
            commandBuffer.RequestAsyncReadback(debugOutput, 0, request =>
            {
                if (request.hasError)
                {
                    Debug.LogWarning(
                        "Recovered low-resolution directional shadow " +
                        "RGBA32F alignment readback failed.");
                    return;
                }

                byte[] raw = request.GetData<byte>().ToArray();
                int edgeSentinels = 0;
                int outsideSamples = 0;
                int validSamples = 0;
                int[] cascadeCounts = new int[4];
                float minimumReceiverDepth = float.PositiveInfinity;
                float maximumReceiverDepth = float.NegativeInfinity;
                float maximumCasterDepth = float.NegativeInfinity;
                float maximumCasterMinusReceiver =
                    float.NegativeInfinity;
                for (int offset = 0;
                     offset + 15 < raw.Length;
                     offset += 16)
                {
                    float receiverDepth =
                        BitConverter.ToSingle(raw, offset + 4);
                    float casterDepth =
                        BitConverter.ToSingle(raw, offset + 8);
                    float cascadeValue =
                        BitConverter.ToSingle(raw, offset + 12);
                    if (cascadeValue < -0.5f)
                    {
                        edgeSentinels++;
                        continue;
                    }
                    int cascade = Mathf.Clamp(
                        Mathf.RoundToInt(cascadeValue),
                        0,
                        3);
                    cascadeCounts[cascade]++;
                    if (casterDepth < -0.5f)
                    {
                        outsideSamples++;
                        continue;
                    }
                    validSamples++;
                    minimumReceiverDepth = Mathf.Min(
                        minimumReceiverDepth,
                        receiverDepth);
                    maximumReceiverDepth = Mathf.Max(
                        maximumReceiverDepth,
                        receiverDepth);
                    maximumCasterDepth = Mathf.Max(
                        maximumCasterDepth,
                        casterDepth);
                    maximumCasterMinusReceiver = Mathf.Max(
                        maximumCasterMinusReceiver,
                        casterDepth - receiverDepth);
                }
                if (validSamples == 0)
                {
                    minimumReceiverDepth = float.NaN;
                    maximumReceiverDepth = float.NaN;
                    maximumCasterDepth = float.NaN;
                    maximumCasterMinusReceiver = float.NaN;
                }
                Debug.Log(
                    "Recovered low-resolution directional shadow alignment " +
                    $"readback: camera={cameraName}, size={width}x{height}, " +
                    $"edgeSentinels={edgeSentinels}, " +
                    $"outsideSamples={outsideSamples}, " +
                    $"validSamples={validSamples}, " +
                    "cascadeCounts=(" +
                    $"{cascadeCounts[0]},{cascadeCounts[1]}," +
                    $"{cascadeCounts[2]},{cascadeCounts[3]}), " +
                    $"receiverDepthRange=({minimumReceiverDepth:R}," +
                    $"{maximumReceiverDepth:R}), " +
                    $"maximumCasterDepth={maximumCasterDepth:R}, " +
                    "maximumCasterMinusReceiver=" +
                    $"{maximumCasterMinusReceiver:R}.");
            });
        }

        private bool Fail(
            ScriptableRenderContext context,
            RenderTargetIdentifier restoreTarget,
            string failure)
        {
            publicationValid = false;
            CommandBuffer commandBuffer = new CommandBuffer
            {
                name =
                    "Disable recovered low-resolution directional shadow"
            };
            commandBuffer.SetGlobalFloat(OutputReadyId, 0.0f);
            commandBuffer.SetGlobalTexture(OutputId, Texture2D.whiteTexture);
            commandBuffer.SetGlobalTexture(
                RawOutputId,
                Texture2D.whiteTexture);
            commandBuffer.SetGlobalTexture(
                HorizontalOutputId,
                Texture2D.whiteTexture);
            commandBuffer.SetRenderTarget(restoreTarget);
            context.ExecuteCommandBuffer(commandBuffer);
            commandBuffer.Release();

            if (!string.Equals(
                    failure,
                    lastFailure,
                    StringComparison.Ordinal))
            {
                Debug.LogWarning(
                    "Recovered installed low-resolution directional shadow " +
                    "stayed disabled: " + failure +
                    ". Canonical _LowResDirectionalShadow remains unchanged.");
                lastFailure = failure;
                loggedActive = false;
            }
            return false;
        }

        private static bool ReadBooleanEnvironment(string name)
        {
            string value = Environment.GetEnvironmentVariable(name);
            if (string.IsNullOrWhiteSpace(value))
                return false;
            value = value.Trim();
            return value == "1" ||
                   value.Equals(
                       "true",
                       StringComparison.OrdinalIgnoreCase) ||
                   value.Equals(
                       "yes",
                       StringComparison.OrdinalIgnoreCase) ||
                   value.Equals(
                       "on",
                       StringComparison.OrdinalIgnoreCase);
        }

        private static bool HasCommandLineArgument(string argument)
        {
            foreach (string value in Environment.GetCommandLineArgs())
            {
                if (string.Equals(
                        value,
                        argument,
                        StringComparison.OrdinalIgnoreCase))
                {
                    return true;
                }
            }
            return false;
        }

        private void ReleaseOutput()
        {
            if (output == null)
                return;
            if (output.IsCreated())
                output.Release();
            DestroyResource(output);
            output = null;
        }

        private void ReleaseDebugOutput()
        {
            if (debugOutput == null)
                return;
            if (debugOutput.IsCreated())
                debugOutput.Release();
            DestroyResource(debugOutput);
            debugOutput = null;
        }

        private void ReleaseBlurOutputs()
        {
            ReleaseRenderTexture(ref horizontalBlur);
            ReleaseRenderTexture(ref verticalBlur);
        }

        private static void ReleaseRenderTexture(
            ref RenderTexture texture)
        {
            if (texture == null)
                return;
            if (texture.IsCreated())
                texture.Release();
            DestroyResource(texture);
            texture = null;
        }

        private static void DestroyResource(UnityEngine.Object resource)
        {
            if (resource == null)
                return;
            if (Application.isPlaying)
                UnityEngine.Object.Destroy(resource);
            else
                UnityEngine.Object.DestroyImmediate(resource);
        }

        public void Dispose()
        {
            if (disposed)
                return;
            disposed = true;
            publicationValid = false;
            ReleaseOutput();
            ReleaseBlurOutputs();
            ReleaseDebugOutput();
            DestroyResource(material);
            material = null;
            DestroyResource(blurMaterial);
            blurMaterial = null;
        }
    }
}
