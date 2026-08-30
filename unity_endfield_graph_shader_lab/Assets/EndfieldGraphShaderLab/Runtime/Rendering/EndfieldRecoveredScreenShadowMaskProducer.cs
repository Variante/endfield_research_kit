using System;
using System.Collections.Generic;
using System.Security.Cryptography;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Default-off current-installed screen-shadow attachment diagnostic.
    /// The retail producer creates a full-camera R8G8_UNorm target, performs
    /// two fullscreen writes, and publishes it as _ScreenSpaceShadowMask before
    /// ForwardOpaque. This lab now attaches the recovered CharInfo-specialized
    /// directional scene-R route using lab-prefixed CSM and low-resolution
    /// inputs. The character pass follows the original binary's G route:
    /// same-frame PreGBuffer selector/normal lanes, character shadow atlas,
    /// light-facing bias, and 16 GatherRed depth taps. It still does not own
    /// every producer of retail R, so the result is never reported as
    /// content-valid and never activates Eye-R/Skin-RG.
    /// </summary>
    internal sealed class EndfieldRecoveredScreenShadowMaskProducer : IDisposable
    {
        internal const string EnvironmentVariable =
            "ENDFIELD_RECOVERED_SCREEN_SHADOW_R_ATTACHMENT_DIAGNOSTIC";
        internal const string CommandLineArgument =
            "-endfield-recovered-screen-shadow-r-attachment-diagnostic";
        internal const string EyeConsumerKeyword =
            "ENDFIELD_RECOVERED_EYE_SCREEN_SHADOW_MASK_R";
        internal const string SkinConsumerKeyword =
            "ENDFIELD_RECOVERED_SKIN_SCREEN_SHADOW_MASK_RG";

        private const string ShaderName =
            "Hidden/Endfield/HGRPCompat/RecoveredScreenShadowResolve";

        private static readonly GraphicsFormat MaskFormat =
            GraphicsFormat.R8G8_UNorm;
        private static readonly int ScreenSpaceShadowMaskId =
            Shader.PropertyToID("_ScreenSpaceShadowMask");
        private static readonly int ReadyId =
            Shader.PropertyToID("_EndfieldRecoveredScreenSpaceShadowMaskReady");
        private static readonly int DepthTextureId =
            Shader.PropertyToID(
                "_EndfieldRecoveredScreenShadowCameraDepthTexture");
        private static readonly int InverseViewProjectionId =
            Shader.PropertyToID(
                "_EndfieldRecoveredScreenShadowInverseGpuViewProjection");
        private static readonly int CameraDepthTexelSizeId =
            Shader.PropertyToID(
                "_EndfieldRecoveredScreenShadowCameraDepthTexelSize");
        private static readonly int CameraWorldPositionId =
            Shader.PropertyToID(
                "_EndfieldRecoveredScreenShadowCameraWorldPosition");
        private static readonly int PreGBufferAId =
            Shader.PropertyToID("_EndfieldRecoveredPreGBufferA");
        private static readonly int PreGBufferBId =
            Shader.PropertyToID("_EndfieldRecoveredPreGBufferB");

        private readonly Dictionary<Camera, CameraResources> cameraResources =
            new Dictionary<Camera, CameraResources>();
        private readonly bool requested;
        private Material material;
        private bool readbackRequested;
        private bool loggedActive;
        private string loggedFailure = string.Empty;
        private bool publicationValid;
        private int publicationCameraInstanceId;
        private int publicationFrame;
        private int publicationWidth;
        private int publicationHeight;
        private bool publicationContentValid;
        private bool disposed;

        internal bool Requested => requested;

        private sealed class CameraResources : IDisposable
        {
            internal int width;
            internal int height;
            internal RenderTexture mask;

            public void Dispose()
            {
                if (mask == null)
                    return;
                mask.Release();
                if (Application.isPlaying)
                    UnityEngine.Object.Destroy(mask);
                else
                    UnityEngine.Object.DestroyImmediate(mask);
                mask = null;
            }
        }

        internal EndfieldRecoveredScreenShadowMaskProducer()
        {
            requested = IsRequested(
                EnvironmentVariable,
                CommandLineArgument);
            Shader.DisableKeyword(EyeConsumerKeyword);
            Shader.DisableKeyword(SkinConsumerKeyword);
            Shader.SetGlobalFloat(ReadyId, 0.0f);
            Shader.SetGlobalTexture(
                ScreenSpaceShadowMaskId,
                Texture2D.whiteTexture);

            if (!requested)
                return;

            Shader shader = Shader.Find(ShaderName);
            if (shader != null && shader.isSupported)
            {
                material = new Material(shader)
                {
                    hideFlags = HideFlags.HideAndDontSave,
                    name = "Recovered RG8 screen-shadow attachment diagnostic"
                };
            }
        }

        public void Dispose()
        {
            if (disposed)
                return;
            disposed = true;
            publicationValid = false;
            publicationContentValid = false;
            Shader.DisableKeyword(EyeConsumerKeyword);
            Shader.DisableKeyword(SkinConsumerKeyword);
            Shader.SetGlobalFloat(ReadyId, 0.0f);
            Shader.SetGlobalTexture(
                ScreenSpaceShadowMaskId,
                Texture2D.whiteTexture);
            foreach (CameraResources resources in cameraResources.Values)
                resources.Dispose();
            cameraResources.Clear();
            if (material == null)
                return;
            if (Application.isPlaying)
                UnityEngine.Object.Destroy(material);
            else
                UnityEngine.Object.DestroyImmediate(material);
            material = null;
        }

        internal bool Render(
            ScriptableRenderContext context,
            Camera camera,
            int width,
            int height,
            RenderTargetIdentifier restoreColor,
            RenderTargetIdentifier sceneDepth,
            EndfieldRecoveredPreGBufferDiagnostic.Frame preGBufferFrame,
            EndfieldRecoveredCharacterShadowFrame characterShadowFrame,
            bool lowResDirectionalReady,
            bool contactShadowReady)
        {
            if (disposed)
                throw new ObjectDisposedException(
                    nameof(EndfieldRecoveredScreenShadowMaskProducer));

            if (!requested)
                return false;

            publicationValid = false;
            publicationContentValid = false;


            string failure;
            if (!lowResDirectionalReady)
            {
                BindDisabled(context);
                LogFailureOnce(
                    "the recovered low-resolution directional producer was not ready");
                return false;
            }
            if (!preGBufferFrame.ready ||
                preGBufferFrame.depthCopy == null ||
                !preGBufferFrame.depthCopy.IsCreated() ||
                preGBufferFrame.gBufferA == null ||
                !preGBufferFrame.gBufferA.IsCreated() ||
                preGBufferFrame.gBufferB == null ||
                !preGBufferFrame.gBufferB.IsCreated())
            {
                BindDisabled(context);
                LogFailureOnce(
                    string.IsNullOrEmpty(preGBufferFrame.failure)
                        ? "the recovered PreGBuffer depth/GBuffer lanes were not ready"
                        : "the recovered PreGBuffer depth/GBuffer lanes were not ready: " +
                          preGBufferFrame.failure);
                return false;
            }
            if (camera == null ||
                preGBufferFrame.cameraInstanceId != camera.GetInstanceID())
            {
                BindDisabled(context);
                LogFailureOnce(
                    "the recovered PreGBuffer frame does not belong to the active camera");
                return false;
            }
            if (!characterShadowFrame.ready ||
                characterShadowFrame.cameraInstanceId != camera.GetInstanceID() ||
                characterShadowFrame.atlasIdentifier == 0)
            {
                BindDisabled(context);
                LogFailureOnce(
                    string.IsNullOrEmpty(characterShadowFrame.failure)
                        ? "the same-frame character shadow atlas was not ready"
                        : "the same-frame character shadow atlas was not ready: " +
                          characterShadowFrame.failure);
                return false;
            }
            CameraResources resources;
            if (!TryPrepareResources(
                    camera,
                    width,
                    height,
                    out resources,
                    out failure))
            {
                BindDisabled(context);
                LogFailureOnce(failure);
                return false;
            }

            var commandBuffer = new CommandBuffer
            {
                name = "Recovered RG8 screen-shadow attachment diagnostic"
            };
            // Publication validity and content validity are intentionally
            // independent. This diagnostic owns a physical same-frame target,
            // but the remaining retail scene-R producers are not yet closed.
            bool contentValid = false;
            try
            {
                commandBuffer.SetGlobalFloat(ReadyId, 0.0f);
                commandBuffer.SetGlobalTexture(
                    DepthTextureId,
                    preGBufferFrame.depthCopy);
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
                Vector3 cameraPosition = camera.transform.position;
                commandBuffer.SetGlobalVector(
                    CameraWorldPositionId,
                    new Vector4(
                        cameraPosition.x,
                        cameraPosition.y,
                        cameraPosition.z,
                        1.0f));
                commandBuffer.SetGlobalTexture(
                    PreGBufferAId,
                    preGBufferFrame.gBufferA);
                commandBuffer.SetGlobalTexture(
                    PreGBufferBId,
                    preGBufferFrame.gBufferB);
                commandBuffer.SetRenderTarget(resources.mask, sceneDepth);

                // Retail uses attachment load/store DontCare and relies on two
                // fullscreen draws rather than an explicit clear. Preserve that
                // ownership: this pass writes every RG pixel and never clears.
                commandBuffer.DrawProcedural(
                    Matrix4x4.identity,
                    material,
                    0,
                    MeshTopology.Triangles,
                    3,
                    1);
                commandBuffer.DrawProcedural(
                    Matrix4x4.identity,
                    material,
                    1,
                    MeshTopology.Triangles,
                    3,
                    1);
                RequestOneShotReadback(
                    commandBuffer,
                    resources.mask,
                    camera.name,
                    resources.width,
                    resources.height);
                commandBuffer.SetGlobalTexture(
                    ScreenSpaceShadowMaskId,
                    resources.mask);
                // Both pass equations are source-shaped, including the
                // character G producer. Keep publication content-invalid until
                // all retail scene-R producers and exact caster ownership are
                // live.
                commandBuffer.SetGlobalFloat(
                    ReadyId,
                    contentValid ? 1.0f : 0.0f);
                if (contentValid)
                {
                    commandBuffer.EnableShaderKeyword(EyeConsumerKeyword);
                    commandBuffer.EnableShaderKeyword(SkinConsumerKeyword);
                }
                else
                {
                    commandBuffer.DisableShaderKeyword(EyeConsumerKeyword);
                    commandBuffer.DisableShaderKeyword(SkinConsumerKeyword);
                }
                commandBuffer.SetRenderTarget(restoreColor, sceneDepth);
                context.ExecuteCommandBuffer(commandBuffer);
            }
            finally
            {
                commandBuffer.Release();
            }

            publicationValid = true;
            publicationCameraInstanceId = camera.GetInstanceID();
            publicationFrame = Time.frameCount;
            publicationWidth = width;
            publicationHeight = height;
            publicationContentValid = contentValid;

            if (!loggedActive)
            {
                Debug.Log(
                    "Recovered screen-shadow R attachment diagnostic active " +
                    "(default-off, content-invalid): " +
                    "full-camera R8G8_UNorm, bilinear/clamp, two un-cleared fullscreen " +
                    "writes with recovered CharInfo directional scene R and character " +
                    "atlas G (selector/normal GBuffer, light-facing bias, 16 GatherRed taps), " +
                    (contactShadowReady
                        ? "the separately gated ContactShadowCS RG displacement applied " +
                          "before both low/full-resolution CSM projections, "
                        : "the exact black contact/no-offset fallback, ") +
                    "then _ScreenSpaceShadowMask global before opaque forward. The Eye " +
                    "integer Load().x consumer remains disabled; exact complete retail " +
                    "scene-R ownership and canonical publication remain open.");
                loggedActive = true;
            }
            return false;
        }

        internal bool TryGetCurrentPublication(
            Camera camera,
            int width,
            int height,
            out RenderTexture publishedTexture,
            out bool contentValid)
        {
            publishedTexture = null;
            contentValid = false;
            if (!publicationValid ||
                camera == null ||
                publicationCameraInstanceId != camera.GetInstanceID() ||
                publicationFrame != Time.frameCount ||
                publicationWidth != width ||
                publicationHeight != height ||
                !cameraResources.TryGetValue(
                    camera,
                    out CameraResources resources) ||
                resources == null ||
                resources.mask == null ||
                !resources.mask.IsCreated())
            {
                return false;
            }
            publishedTexture = resources.mask;
            contentValid = publicationContentValid;
            return true;
        }

        private void RequestOneShotReadback(
            CommandBuffer commandBuffer,
            RenderTexture texture,
            string cameraName,
            int width,
            int height)
        {
            if (readbackRequested ||
                !SystemInfo.supportsAsyncGPUReadback ||
                texture == null ||
                !texture.IsCreated())
            {
                return;
            }
            readbackRequested = true;
            commandBuffer.RequestAsyncReadback(texture, 0, request =>
            {
                if (request.hasError)
                {
                    Debug.LogWarning(
                        "Recovered full-resolution screen-shadow RG8 readback failed.");
                    return;
                }
                var source = request.GetData<byte>();
                int expected = width * height * 2;
                if (source.Length != expected)
                {
                    Debug.LogWarning(
                        "Recovered full-resolution screen-shadow RG8 readback " +
                        $"returned {source.Length} bytes; expected {expected}.");
                    return;
                }
                byte[] bytes = new byte[source.Length];
                int minimum = 255;
                int maximum = 0;
                int zero = 0;
                int one = 0;
                int intermediate = 0;
                int nonNeutralG = 0;
                for (int i = 0; i < source.Length; i++)
                    bytes[i] = source[i];
                for (int pixel = 0; pixel < width * height; pixel++)
                {
                    int r = bytes[pixel * 2];
                    int g = bytes[pixel * 2 + 1];
                    minimum = Mathf.Min(minimum, r);
                    maximum = Mathf.Max(maximum, r);
                    if (r == 0)
                        zero++;
                    else if (r == 255)
                        one++;
                    else
                        intermediate++;
                    if (g != 255)
                        nonNeutralG++;
                }
                string digest;
                using (SHA256 sha = SHA256.Create())
                {
                    digest = BitConverter.ToString(
                            sha.ComputeHash(bytes))
                        .Replace("-", string.Empty)
                        .ToLowerInvariant();
                }
                Debug.Log(
                    "Recovered full-resolution screen-shadow RG8 GPU readback: " +
                    $"camera={cameraName}, size={width}x{height}, " +
                    $"rByteRange={minimum}..{maximum}, rZero={zero}, " +
                    $"rIntermediate={intermediate}, rOne={one}, " +
                    $"nonNeutralG={nonNeutralG}, sha256={digest}. " +
                    "This is default-off directional scene-R attachment evidence; " +
                    "contentValid remains false and Eye R/Skin RG remain disabled.");
            });
        }

        internal void ResetAfterForward(ScriptableRenderContext context)
        {
            if (!requested)
                return;
            var commandBuffer = new CommandBuffer
            {
                name = "Reset recovered screen-shadow attachment diagnostic"
            };
            commandBuffer.DisableShaderKeyword(EyeConsumerKeyword);
            commandBuffer.DisableShaderKeyword(SkinConsumerKeyword);
            commandBuffer.SetGlobalFloat(ReadyId, 0.0f);
            commandBuffer.SetGlobalTexture(
                ScreenSpaceShadowMaskId,
                Texture2D.whiteTexture);
            context.ExecuteCommandBuffer(commandBuffer);
            commandBuffer.Release();
        }

        private bool TryPrepareResources(
            Camera camera,
            int width,
            int height,
            out CameraResources resources,
            out string failure)
        {
            resources = null;
            failure = string.Empty;
            if (camera == null)
            {
                failure = "camera is null";
                return false;
            }
            if (material == null)
            {
                failure = ShaderName + " is missing or unsupported";
                return false;
            }
            if (material.passCount < 2)
            {
                failure = ShaderName + " does not expose both retail-shaped resolve passes";
                return false;
            }
            if (!SystemInfo.IsFormatSupported(
                    MaskFormat,
                    FormatUsage.Render))
            {
                failure = MaskFormat + " is not render-target supported";
                return false;
            }

            width = Mathf.Max(width, 1);
            height = Mathf.Max(height, 1);
            if (!cameraResources.TryGetValue(camera, out resources))
            {
                resources = new CameraResources();
                cameraResources.Add(camera, resources);
            }
            if (resources.mask != null &&
                resources.width == width &&
                resources.height == height &&
                resources.mask.IsCreated())
            {
                return true;
            }

            resources.Dispose();
            var descriptor = new RenderTextureDescriptor(width, height)
            {
                graphicsFormat = MaskFormat,
                depthBufferBits = 0,
                msaaSamples = 1,
                volumeDepth = 1,
                dimension = TextureDimension.Tex2D,
                sRGB = false,
                useMipMap = false,
                autoGenerateMips = false,
                enableRandomWrite = false
            };
            resources.mask = new RenderTexture(descriptor)
            {
                hideFlags = HideFlags.HideAndDontSave,
                name = "Recovered _ScreenSpaceShadowMask RG8",
                filterMode = FilterMode.Bilinear,
                wrapMode = TextureWrapMode.Clamp
            };
            resources.width = width;
            resources.height = height;
            if (!resources.mask.Create())
            {
                resources.Dispose();
                failure = "R8G8_UNorm screen-shadow target creation failed";
                return false;
            }
            return true;
        }

        private static void BindDisabled(ScriptableRenderContext context)
        {
            var commandBuffer = new CommandBuffer
            {
                name = "Disable recovered screen-shadow attachment diagnostic"
            };
            commandBuffer.DisableShaderKeyword(EyeConsumerKeyword);
            commandBuffer.DisableShaderKeyword(SkinConsumerKeyword);
            commandBuffer.SetGlobalFloat(ReadyId, 0.0f);
            commandBuffer.SetGlobalTexture(
                ScreenSpaceShadowMaskId,
                Texture2D.whiteTexture);
            context.ExecuteCommandBuffer(commandBuffer);
            commandBuffer.Release();
        }

        private void LogFailureOnce(string failure)
        {
            if (string.Equals(
                    loggedFailure,
                    failure,
                    StringComparison.Ordinal))
            {
                return;
            }
            loggedFailure = failure;
            Debug.LogWarning(
                "Recovered screen-shadow attachment diagnostic failed closed: " +
                failure + ". Eye retains the compatibility fallback.");
        }

        private static bool IsRequested(
            string environmentVariable,
            string commandLineArgument)
        {
            bool enabled = IsEnabledSelectorValue(
                Environment.GetEnvironmentVariable(environmentVariable));
            string[] arguments = Environment.GetCommandLineArgs();
            for (int i = 0; i < arguments.Length; i++)
            {
                string argument = arguments[i];
                if (string.Equals(
                        argument,
                        commandLineArgument,
                        StringComparison.OrdinalIgnoreCase))
                {
                    enabled = true;
                    continue;
                }
                string prefix = commandLineArgument + "=";
                if (argument.StartsWith(
                        prefix,
                        StringComparison.OrdinalIgnoreCase))
                {
                    enabled = IsEnabledSelectorValue(
                        argument.Substring(prefix.Length));
                }
            }
            return enabled;
        }

        private static bool IsEnabledSelectorValue(string rawValue)
        {
            if (string.IsNullOrWhiteSpace(rawValue))
                return false;
            string value = rawValue.Trim();
            return string.Equals(value, "1", StringComparison.OrdinalIgnoreCase) ||
                   string.Equals(value, "true", StringComparison.OrdinalIgnoreCase) ||
                   string.Equals(value, "yes", StringComparison.OrdinalIgnoreCase) ||
                   string.Equals(value, "on", StringComparison.OrdinalIgnoreCase);
        }
    }
}
