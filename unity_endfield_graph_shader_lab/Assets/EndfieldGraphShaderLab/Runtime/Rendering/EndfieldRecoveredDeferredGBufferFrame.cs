using System;
using System.Collections.Generic;
using System.Linq;
using System.Security.Cryptography;
using Unity.Collections;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Default-off, non-presented same-camera replay of the source-closed
    /// SphereOutside HGBuffer producer. This owns the exact five logical color
    /// attachments and D32S8 depth/stencil sidecar but deliberately does not run
    /// or approximate the still-incomplete deferred-lighting consumer.
    /// </summary>
    internal sealed class EndfieldRecoveredDeferredGBufferFrame : IDisposable
    {
        internal const string EnvironmentVariable =
            "ENDFIELD_RECOVERED_DEFERRED_GBUFFER_FRAME";
        internal const string CommandLineArgument =
            "-endfield-recovered-deferred-gbuffer-frame";

        internal const string ShaderName =
            "Hidden/Endfield/Recovered/CharInfo/HGRPLitUnavailable";
        internal const string PassName =
            "RecoveredSphereOutsideHGBufferFrame";

        internal static readonly int ReadyId =
            Shader.PropertyToID("_EndfieldRecoveredDeferredGBufferFrameReady");
        internal static readonly int SceneColorId =
            Shader.PropertyToID("_EndfieldRecoveredDeferredSceneColor");
        internal static readonly int SceneMVId =
            Shader.PropertyToID("_EndfieldRecoveredDeferredSceneMV");
        internal static readonly int GBufferAId =
            Shader.PropertyToID("_EndfieldRecoveredDeferredGBufferA");
        internal static readonly int GBufferBId =
            Shader.PropertyToID("_EndfieldRecoveredDeferredGBufferB");
        internal static readonly int GBufferCId =
            Shader.PropertyToID("_EndfieldRecoveredDeferredGBufferC");
        // The selected original D3D11 resolver consumes the GBuffer in its
        // backend register order C/B/A (t23/t24/t25), not the producer's
        // logical A/B/C naming. Keep these aliases explicit so a future
        // resolver consumer cannot silently swap the base-color and MRO
        // attachments while the production pass remains disabled.
        internal static readonly int ResolverGBufferT23Id =
            Shader.PropertyToID("_EndfieldRecoveredDeferredResolverT23");
        internal static readonly int ResolverGBufferT24Id =
            Shader.PropertyToID("_EndfieldRecoveredDeferredResolverT24");
        internal static readonly int ResolverGBufferT25Id =
            Shader.PropertyToID("_EndfieldRecoveredDeferredResolverT25");
        // The selected original SPIR-V/HLSL resolver names the same source
        // textures _62 (t23/C), _61 (t24/B), and _60 (t25/A). Publish these
        // exact identifiers alongside the lab-prefixed aliases so a future
        // binding-compatible resolver can consume the source names directly.
        internal static readonly int ResolverSourceTextureT23Id =
            Shader.PropertyToID("_62");
        internal static readonly int ResolverSourceTextureT24Id =
            Shader.PropertyToID("_61");
        internal static readonly int ResolverSourceTextureT25Id =
            Shader.PropertyToID("_60");
        private static readonly int GpuViewProjectionId =
            Shader.PropertyToID(
                "_EndfieldRecoveredDeferredGpuViewProjection");

        private static readonly Color SceneColorClear =
            new Color(0.025f, 0.07f, 0.19f, 0.0f);
        private static readonly Color SceneMVClear =
            new Color(0.5f, 0.5f, 0.0f, 0.0f);

        private readonly bool requested;
        private RenderTexture sceneColor;
        private RenderTexture sceneMV;
        private RenderTexture gBufferA;
        private RenderTexture gBufferB;
        private RenderTexture gBufferC;
        private RenderTexture depthStencil;
        private int allocatedWidth;
        private int allocatedHeight;
        private bool activationLogged;
        private bool failureLogged;
        private bool readbackRequested;

        internal bool Requested => requested;

        internal EndfieldRecoveredDeferredGBufferFrame()
        {
            requested =
                ReadBooleanEnvironment(EnvironmentVariable) ||
                HasCommandLineArgument(CommandLineArgument);
            Shader.SetGlobalFloat(ReadyId, 0.0f);
            PublishBlackFallbacks();
        }

        public void Dispose()
        {
            ReleaseResources();
            Shader.SetGlobalFloat(ReadyId, 0.0f);
            PublishBlackFallbacks();
        }

        internal bool Render(
            ScriptableRenderContext context,
            Camera camera,
            int width,
            int height,
            bool canonicalFrameResourcesReady,
            RenderTargetIdentifier canonicalColorTarget,
            RenderTargetIdentifier canonicalDepthTarget)
        {
            if (!requested)
                return false;

            string failure;
            Renderer renderer;
            Material material;
            int passIndex;
            if (!canonicalFrameResourcesReady)
            {
                failure = "canonical binning/reflection/VisibilitySHConstData prerequisites are not ready";
                FailClosed(context, failure);
                return false;
            }
            if (!TryResolveSource(camera, out renderer, out material, out passIndex, out failure))
            {
                FailClosed(context, failure);
                return false;
            }
            if (!TryEnsureResources(width, height, out failure))
            {
                FailClosed(context, failure);
                return false;
            }

            var command = new CommandBuffer
            {
                name = "Recovered same-frame SphereOutside HGBuffer sidecar"
            };
            try
            {
                command.SetRenderTarget(sceneColor);
                command.ClearRenderTarget(false, true, SceneColorClear);
                command.SetRenderTarget(sceneMV);
                command.ClearRenderTarget(false, true, SceneMVClear);
                command.SetRenderTarget(gBufferA);
                command.ClearRenderTarget(false, true, Color.clear);
                command.SetRenderTarget(gBufferB);
                command.ClearRenderTarget(false, true, Color.clear);
                command.SetRenderTarget(gBufferC);
                command.ClearRenderTarget(false, true, Color.clear);
                command.SetRenderTarget(depthStencil);
                // Unity's command-buffer clear depth is expressed in its
                // logical 0..1 convention; the backend performs the reversed-Z
                // mapping for D3D11/D3D12. The installed render-graph clear is
                // depth 1, stencil 0.
                command.ClearRenderTarget(
                    RTClearFlags.Depth | RTClearFlags.Stencil,
                    Color.clear,
                    1.0f,
                    0u);

                var colorTargets = new[]
                {
                    new RenderTargetIdentifier(sceneColor),
                    new RenderTargetIdentifier(sceneMV),
                    new RenderTargetIdentifier(gBufferA),
                    new RenderTargetIdentifier(gBufferB),
                    new RenderTargetIdentifier(gBufferC),
                };
                command.SetRenderTarget(
                    colorTargets,
                    new RenderTargetIdentifier(depthStencil));
                command.SetViewport(new Rect(0.0f, 0.0f, width, height));
                command.SetGlobalMatrix(
                    GpuViewProjectionId,
                    GL.GetGPUProjectionMatrix(camera.projectionMatrix, true) *
                    camera.worldToCameraMatrix);
                command.DrawRenderer(renderer, material, 0, passIndex);

                command.SetGlobalTexture(SceneColorId, sceneColor);
                command.SetGlobalTexture(SceneMVId, sceneMV);
                command.SetGlobalTexture(GBufferAId, gBufferA);
                command.SetGlobalTexture(GBufferBId, gBufferB);
                command.SetGlobalTexture(GBufferCId, gBufferC);
                // Source-closed selected pass-0 bridge: t23=C, t24=B,
                // t25=A. These are diagnostic aliases only; no production
                // resolver draw is enabled by this publication.
                command.SetGlobalTexture(ResolverGBufferT23Id, gBufferC);
                command.SetGlobalTexture(ResolverGBufferT24Id, gBufferB);
                command.SetGlobalTexture(ResolverGBufferT25Id, gBufferA);
                command.SetGlobalTexture(ResolverSourceTextureT23Id, gBufferC);
                command.SetGlobalTexture(ResolverSourceTextureT24Id, gBufferB);
                command.SetGlobalTexture(ResolverSourceTextureT25Id, gBufferA);
                command.SetGlobalFloat(ReadyId, 1.0f);
                RequestReadbacks(command, camera.name);
                // This producer is a non-presented sidecar. Restore the exact
                // camera-owned color/depth pair before any later producer or
                // ordinary renderer can inherit the private MRT binding.
                command.SetRenderTarget(
                    canonicalColorTarget,
                    canonicalDepthTarget);
                command.SetViewport(new Rect(0.0f, 0.0f, width, height));
                context.ExecuteCommandBuffer(command);
            }
            finally
            {
                command.Release();
            }

            if (!activationLogged)
            {
                Debug.Log(
                    "Recovered SphereOutside same-frame HGBuffer sidecar active: " +
                    $"camera={camera.name}, size={width}x{height}, " +
                    "attachments=B10G11R11/A2B10G10R10/A2B10G10R10/" +
                    "A2B10G10R10/R8G8B8A8_SRGB+D32S8, " +
                    "sourceRendererDisabled=" + (!renderer.enabled) + ", " +
                    "resolverGBufferBindings=t23:C,t24:B,t25:A, " +
                    "resolverSourceIdentifiers=t23:_62,t24:_61,t25:_60, " +
                    "pass0ConsumerEnabled=false.");
                activationLogged = true;
            }
            failureLogged = false;
            return true;
        }

        private void FailClosed(
            ScriptableRenderContext context,
            string failure)
        {
            var command = new CommandBuffer
            {
                name = "Fail-closed recovered deferred HGBuffer sidecar"
            };
            command.SetGlobalFloat(ReadyId, 0.0f);
            command.SetGlobalTexture(SceneColorId, Texture2D.blackTexture);
            command.SetGlobalTexture(SceneMVId, Texture2D.blackTexture);
            command.SetGlobalTexture(GBufferAId, Texture2D.blackTexture);
            command.SetGlobalTexture(GBufferBId, Texture2D.blackTexture);
            command.SetGlobalTexture(GBufferCId, Texture2D.blackTexture);
            command.SetGlobalTexture(ResolverGBufferT23Id, Texture2D.blackTexture);
            command.SetGlobalTexture(ResolverGBufferT24Id, Texture2D.blackTexture);
            command.SetGlobalTexture(ResolverGBufferT25Id, Texture2D.blackTexture);
            command.SetGlobalTexture(ResolverSourceTextureT23Id, Texture2D.blackTexture);
            command.SetGlobalTexture(ResolverSourceTextureT24Id, Texture2D.blackTexture);
            command.SetGlobalTexture(ResolverSourceTextureT25Id, Texture2D.blackTexture);
            context.ExecuteCommandBuffer(command);
            command.Release();
            if (!failureLogged)
            {
                Debug.LogWarning(
                    "Recovered SphereOutside same-frame HGBuffer sidecar failed closed: " +
                    failure + ".");
                failureLogged = true;
            }
        }

        private static bool TryResolveSource(
            Camera camera,
            out Renderer renderer,
            out Material material,
            out int passIndex,
            out string failure)
        {
            renderer = null;
            material = null;
            passIndex = -1;
            failure = string.Empty;

            EndfieldRecoveredCharInfoPresentation[] candidates =
                Resources.FindObjectsOfTypeAll<EndfieldRecoveredCharInfoPresentation>();
            List<EndfieldRecoveredCharInfoPresentation> matching = candidates
                .Where(value =>
                    value != null &&
                    value.gameObject.scene.IsValid() &&
                    value.gameObject.scene == camera.gameObject.scene &&
                    value.sphereOutsideRenderer != null)
                .ToList();
            if (matching.Count != 1)
            {
                failure =
                    "expected one scene-local recovered CharInfo presentation with " +
                    $"SphereOutside; found {matching.Count}";
                return false;
            }

            EndfieldRecoveredCharInfoPresentation presentation = matching[0];
            renderer = presentation.sphereOutsideRenderer;
            if (presentation.sourceContent == null ||
                !presentation.sourceContent.activeInHierarchy)
            {
                failure = "the recovered CharInfo source hierarchy is not active";
                return false;
            }
            if (renderer.enabled)
            {
                failure =
                    "SphereOutside is enabled in the ordinary renderer; the sidecar " +
                    "requires the ready-subset fail-closed allow-list";
                return false;
            }
            if ((camera.cullingMask & (1 << renderer.gameObject.layer)) == 0)
            {
                failure = "the camera culling mask excludes SphereOutside";
                return false;
            }

            Material[] materials = renderer.sharedMaterials;
            if (materials == null || materials.Length != 1 || materials[0] == null)
            {
                failure = "SphereOutside does not have exactly one source material";
                return false;
            }
            material = materials[0];
            if (material.shader == null || material.shader.name != ShaderName)
            {
                failure =
                    "SphereOutside retained an unexpected shader: " +
                    (material.shader != null ? material.shader.name : "<null>");
                return false;
            }
            passIndex = material.FindPass(PassName);
            if (passIndex < 0)
            {
                failure = "the source-backed camera HGBuffer pass is unavailable";
                return false;
            }
            if (!Approximately(material.GetFloat("_CullMode"), 0.0f) ||
                !Approximately(material.GetFloat("_ZTestGBuffer"), 4.0f) ||
                !Approximately(material.GetFloat("_ZWriteGBuffer"), 1.0f) ||
                !Approximately(material.GetFloat("_StencilRef"), 0.0f) ||
                !Approximately(material.GetFloat("_StencilOpGBuffer"), 2.0f))
            {
                failure =
                    "SphereOutside material render state drifted from Cull Off, " +
                    "ZTest LEqual, ZWrite On, stencil ref 0/Replace";
                return false;
            }
            return true;
        }

        private bool TryEnsureResources(
            int width,
            int height,
            out string failure)
        {
            failure = string.Empty;
            if (width <= 0 || height <= 0)
            {
                failure = $"invalid camera extent {width}x{height}";
                return false;
            }
            if (sceneColor != null &&
                allocatedWidth == width &&
                allocatedHeight == height)
            {
                return true;
            }

            ReleaseResources();
            GraphicsFormat[] formats =
            {
                GraphicsFormat.B10G11R11_UFloatPack32,
                GraphicsFormat.A2B10G10R10_UNormPack32,
                GraphicsFormat.R8G8B8A8_SRGB,
                GraphicsFormat.D32_SFloat_S8_UInt,
            };
            foreach (GraphicsFormat format in formats)
            {
                if (!SystemInfo.IsFormatSupported(format, FormatUsage.Render))
                {
                    failure = format + " render support is unavailable";
                    return false;
                }
            }
            if (SystemInfo.supportedRenderTargetCount < 5)
            {
                failure =
                    "fewer than five simultaneous color targets are supported";
                return false;
            }

            try
            {
                sceneColor = CreateColor(
                    width,
                    height,
                    GraphicsFormat.B10G11R11_UFloatPack32,
                    "Recovered Deferred SceneColor");
                sceneMV = CreateColor(
                    width,
                    height,
                    GraphicsFormat.A2B10G10R10_UNormPack32,
                    "Recovered Deferred SceneMV");
                gBufferA = CreateColor(
                    width,
                    height,
                    GraphicsFormat.A2B10G10R10_UNormPack32,
                    "Recovered Deferred GBufferA");
                gBufferB = CreateColor(
                    width,
                    height,
                    GraphicsFormat.A2B10G10R10_UNormPack32,
                    "Recovered Deferred GBufferB");
                gBufferC = CreateColor(
                    width,
                    height,
                    GraphicsFormat.R8G8B8A8_SRGB,
                    "Recovered Deferred GBufferC");
                depthStencil = CreateDepth(width, height);
            }
            catch (Exception exception)
            {
                ReleaseResources();
                failure = "attachment allocation failed: " + exception.Message;
                return false;
            }
            allocatedWidth = width;
            allocatedHeight = height;
            return true;
        }

        private static RenderTexture CreateColor(
            int width,
            int height,
            GraphicsFormat format,
            string name)
        {
            var descriptor = new RenderTextureDescriptor(width, height)
            {
                graphicsFormat = format,
                depthStencilFormat = GraphicsFormat.None,
                msaaSamples = 1,
                bindMS = false,
                volumeDepth = 1,
                dimension = TextureDimension.Tex2D,
                useMipMap = false,
                autoGenerateMips = false,
                enableRandomWrite = false,
                sRGB = GraphicsFormatUtility.IsSRGBFormat(format),
                useDynamicScale = false,
            };
            var texture = new RenderTexture(descriptor)
            {
                name = name,
                filterMode = FilterMode.Point,
                wrapMode = TextureWrapMode.Clamp,
                anisoLevel = 0,
                hideFlags = HideFlags.HideAndDontSave,
            };
            if (!texture.Create() || texture.graphicsFormat != format)
            {
                GraphicsFormat actual = texture.graphicsFormat;
                ReleaseTexture(texture);
                throw new InvalidOperationException(
                    $"{name} could not retain {format}; actual={actual}");
            }
            return texture;
        }

        private static RenderTexture CreateDepth(int width, int height)
        {
            var descriptor = new RenderTextureDescriptor(width, height)
            {
                graphicsFormat = GraphicsFormat.None,
                depthStencilFormat = GraphicsFormat.D32_SFloat_S8_UInt,
                msaaSamples = 1,
                bindMS = false,
                volumeDepth = 1,
                dimension = TextureDimension.Tex2D,
                useMipMap = false,
                autoGenerateMips = false,
                enableRandomWrite = false,
                sRGB = false,
                shadowSamplingMode = ShadowSamplingMode.RawDepth,
                useDynamicScale = false,
            };
            var texture = new RenderTexture(descriptor)
            {
                name = "Recovered Deferred SceneDepth",
                filterMode = FilterMode.Point,
                wrapMode = TextureWrapMode.Clamp,
                anisoLevel = 0,
                hideFlags = HideFlags.HideAndDontSave,
            };
            if (!texture.Create() ||
                texture.depthStencilFormat != GraphicsFormat.D32_SFloat_S8_UInt)
            {
                GraphicsFormat actual = texture.depthStencilFormat;
                ReleaseTexture(texture);
                throw new InvalidOperationException(
                    "Recovered Deferred SceneDepth could not retain D32S8; actual=" +
                    actual);
            }
            return texture;
        }

        private void RequestReadbacks(
            CommandBuffer command,
            string cameraName)
        {
            if (readbackRequested ||
                command == null ||
                !SystemInfo.supportsAsyncGPUReadback)
                return;
            readbackRequested = true;
            RequestReadback(command, "SceneColor", sceneColor, cameraName);
            RequestReadback(command, "SceneMV", sceneMV, cameraName);
            RequestReadback(command, "GBufferA", gBufferA, cameraName);
            RequestReadback(command, "GBufferB", gBufferB, cameraName);
            RequestReadback(command, "GBufferC", gBufferC, cameraName);
        }

        private static void RequestReadback(
            CommandBuffer command,
            string role,
            RenderTexture texture,
            string cameraName)
        {
            int width = texture.width;
            int height = texture.height;
            GraphicsFormat format = texture.graphicsFormat;
            command.RequestAsyncReadback(texture, 0, request =>
            {
                if (request.hasError)
                {
                    Debug.LogWarning(
                        "Recovered deferred HGBuffer GPU readback failed: role=" +
                        role + ".");
                    return;
                }
                NativeArray<byte> data = request.GetData<byte>();
                byte[] raw = data.ToArray();
                int nonzeroBytes = 0;
                for (int i = 0; i < raw.Length; i++)
                {
                    if (raw[i] != 0)
                        nonzeroBytes++;
                }
                string hash;
                using (SHA256 sha = SHA256.Create())
                {
                    hash = BitConverter.ToString(sha.ComputeHash(raw))
                        .Replace("-", string.Empty)
                        .ToLowerInvariant();
                }
                Debug.Log(
                    "Recovered deferred HGBuffer GPU readback: " +
                    $"role={role}, camera={cameraName}, size={width}x{height}, " +
                    $"format={format}, bytes={raw.Length}, " +
                    $"nonzeroBytes={nonzeroBytes}, sha256={hash}.");
            });
        }

        private void ReleaseResources()
        {
            ReleaseTexture(sceneColor);
            ReleaseTexture(sceneMV);
            ReleaseTexture(gBufferA);
            ReleaseTexture(gBufferB);
            ReleaseTexture(gBufferC);
            ReleaseTexture(depthStencil);
            sceneColor = null;
            sceneMV = null;
            gBufferA = null;
            gBufferB = null;
            gBufferC = null;
            depthStencil = null;
            allocatedWidth = 0;
            allocatedHeight = 0;
        }

        private static void ReleaseTexture(RenderTexture texture)
        {
            if (texture == null)
                return;
            if (texture.IsCreated())
                texture.Release();
            if (Application.isPlaying)
                UnityEngine.Object.Destroy(texture);
            else
                UnityEngine.Object.DestroyImmediate(texture);
        }

        private static void PublishBlackFallbacks()
        {
            Shader.SetGlobalTexture(SceneColorId, Texture2D.blackTexture);
            Shader.SetGlobalTexture(SceneMVId, Texture2D.blackTexture);
            Shader.SetGlobalTexture(GBufferAId, Texture2D.blackTexture);
            Shader.SetGlobalTexture(GBufferBId, Texture2D.blackTexture);
            Shader.SetGlobalTexture(GBufferCId, Texture2D.blackTexture);
            Shader.SetGlobalTexture(ResolverGBufferT23Id, Texture2D.blackTexture);
            Shader.SetGlobalTexture(ResolverGBufferT24Id, Texture2D.blackTexture);
            Shader.SetGlobalTexture(ResolverGBufferT25Id, Texture2D.blackTexture);
            Shader.SetGlobalTexture(ResolverSourceTextureT23Id, Texture2D.blackTexture);
            Shader.SetGlobalTexture(ResolverSourceTextureT24Id, Texture2D.blackTexture);
            Shader.SetGlobalTexture(ResolverSourceTextureT25Id, Texture2D.blackTexture);
        }

        private static bool Approximately(float actual, float expected)
        {
            return Mathf.Abs(actual - expected) <= 1.0e-6f;
        }

        private static bool ReadBooleanEnvironment(string name)
        {
            string value = Environment.GetEnvironmentVariable(name);
            return IsEnabledSelectorValue(value);
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

        private static bool IsEnabledSelectorValue(string value)
        {
            if (string.IsNullOrWhiteSpace(value))
                return false;
            value = value.Trim();
            return value == "1" ||
                   value.Equals("true", StringComparison.OrdinalIgnoreCase) ||
                   value.Equals("yes", StringComparison.OrdinalIgnoreCase) ||
                   value.Equals("on", StringComparison.OrdinalIgnoreCase);
        }
    }
}
