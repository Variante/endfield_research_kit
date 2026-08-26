using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Security.Cryptography;
using Unity.Collections;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Default-off, non-presented same-camera replay of source-closed HGBuffer
    /// producers. SphereOutside and Endminf M27 share the exact five logical
    /// color attachments and D32S8 depth/stencil sidecar while retaining
    /// separate identity gates. The selected deferred consumer is source-
    /// closed elsewhere and is not presented by this producer.
    /// </summary>
    internal sealed class EndfieldRecoveredDeferredGBufferFrame : IDisposable
    {
        internal const string EnvironmentVariable =
            "ENDFIELD_RECOVERED_DEFERRED_GBUFFER_FRAME";
        internal const string CommandLineArgument =
            "-endfield-recovered-deferred-gbuffer-frame";
        internal const string EndminfM27EnvironmentVariable =
            "ENDFIELD_RECOVERED_ENDMINF_M27_HGBUFFER";
        internal const string EndminfM27ExactDxbcEnvironmentVariable =
            "ENDFIELD_RECOVERED_ENDMINF_M27_EXACT_DXBC";
        internal const string EndminfM27CommandLineArgument =
            "-endfield-recovered-endminf-m27-hgbuffer";

        internal const string ShaderName =
            "Hidden/Endfield/Recovered/CharInfo/HGRPLitUnavailable";
        internal const string PassName =
            "RecoveredSphereOutsideHGBufferFrame";
        internal const string EndminfM27ShaderName =
            "Hidden/Endfield/Recovered/Endminf/M27LitEffectHGBuffer";
        internal const string EndminfM27PassName =
            "RecoveredEndminfM27HGBuffer";
        internal const string EndminfM27ExactShaderName =
            "Hidden/Endfield/Diagnostics/EndminfM27ExactAbiShell";
        internal const string EndminfM27ExactPassName = "M27ExactAbiShell";
        private const string EndminfM27ExactKeyword =
            "ENDFIELD_ORIGINAL_DXBC_M27_EXACT";
        private const long EndminfM27RendererPathId = 59284134265994738L;
        private const long EndminfM27MaterialPathId =
            unchecked((long)0xA531A88850690EB8UL);
        private const long EndminfM27MeshPathId =
            unchecked((long)0x8EC9950E5461C8D9UL);

        internal static readonly int ReadyId =
            Shader.PropertyToID("_EndfieldRecoveredDeferredGBufferFrameReady");
        internal static readonly int EndminfM27ReadyId =
            Shader.PropertyToID("_EndfieldRecoveredEndminfM27HGBufferReady");
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
        // The selected original D3D11 resolver consumes the GBuffer in
        // register order A/B/C (t23/t24/t25). The source SPIR-V identifiers
        // are _60/_61/_62 respectively; keep these aliases explicit so a
        // future consumer cannot silently swap the base-color and MRO
        // attachments while the production pass remains disabled.
        internal static readonly int ResolverGBufferT23Id =
            Shader.PropertyToID("_EndfieldRecoveredDeferredResolverT23");
        internal static readonly int ResolverGBufferT24Id =
            Shader.PropertyToID("_EndfieldRecoveredDeferredResolverT24");
        internal static readonly int ResolverGBufferT25Id =
            Shader.PropertyToID("_EndfieldRecoveredDeferredResolverT25");
        // The selected original SPIR-V/HLSL resolver names these source
        // textures _60 (t23/A), _61 (t24/B), and _62 (t25/C). Publish the
        // exact identifiers alongside the lab-prefixed aliases so a future
        // binding-compatible resolver can consume the source names directly.
        internal static readonly int ResolverSourceTextureT23Id =
            Shader.PropertyToID("_60");
        internal static readonly int ResolverSourceTextureT24Id =
            Shader.PropertyToID("_61");
        internal static readonly int ResolverSourceTextureT25Id =
            Shader.PropertyToID("_62");
        private static readonly int GpuViewProjectionId =
            Shader.PropertyToID(
                "_EndfieldRecoveredDeferredGpuViewProjection");
        private static readonly int PreviousGpuViewProjectionId =
            Shader.PropertyToID(
                "_EndfieldRecoveredDeferredPreviousGpuViewProjection");
        private static readonly int PreviousObjectToWorldId =
            Shader.PropertyToID(
                "_EndfieldRecoveredDeferredPreviousObjectToWorld");
        private static readonly int MotionValidId =
            Shader.PropertyToID("_EndfieldRecoveredDeferredMotionValid");
        private static readonly int MotionVectorsParamsId =
            Shader.PropertyToID(
                "_EndfieldRecoveredDeferredMotionVectorsParams");

        private static readonly Color SceneColorClear =
            new Color(0.025f, 0.07f, 0.19f, 0.0f);
        private static readonly Color SceneMVClear =
            new Color(0.5f, 0.5f, 0.0f, 0.0f);

        private readonly bool requested;
        private readonly bool sphereOutsideRequested;
        private readonly bool endminfM27Requested;
        private readonly bool endminfM27ExactDxbcRequested;
        private Material endminfM27Material;
        private Mesh endminfM27ExactExpandedMesh;
        private int endminfM27SourceMaterialId;
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
        private bool endminfM27ReadbackRequested;
        private bool endminfM27ActivationLogged;
        // Resolver inputs are a same-camera-frame publication.  Keeping the
        // stamp beside the textures prevents a later camera (or a reused
        // RenderTexture allocation) from being mistaken for the current
        // target frame by the deferred consumer probe.
        private bool publicationValid;
        private int publishedFrame = -1;
        private int publishedCameraInstanceId;
        private int publishedWidth;
        private int publishedHeight;
        private uint publicationSerial;
        private int endminfM27PublishedFrame = -1;
        private int endminfM27PublishedCameraInstanceId;
        private int endminfM27PublishedWidth;
        private int endminfM27PublishedHeight;
        // HGRP/Lit's source vertex supplies previous clip x/y/w lanes to the
        // fragment motion encoder. Keep the immediately preceding camera and
        // object transforms; a camera, renderer, or extent discontinuity
        // starts a neutral sample and never reuses unrelated history.
        private Matrix4x4 previousGpuViewProjection;
        private Matrix4x4 previousObjectToWorld;
        private bool hasPreviousGpuViewProjection;
        private int previousCameraInstanceId;
        private int previousRendererInstanceId;
        private int previousFrame = -1;
        private int previousWidth;
        private int previousHeight;

        internal bool Requested => requested;

        internal EndfieldRecoveredDeferredGBufferFrame()
        {
            endminfM27Requested =
                ReadBooleanEnvironment(EndminfM27EnvironmentVariable) ||
                HasCommandLineArgument(EndminfM27CommandLineArgument);
            endminfM27ExactDxbcRequested =
                endminfM27Requested &&
                ReadBooleanEnvironment(EndminfM27ExactDxbcEnvironmentVariable);
            // A generic deferred-resolver probe historically implied the
            // SphereOutside producer. M27 is now a complete identity-gated
            // five-target producer in its own right; requiring the inactive
            // CharInfo room hierarchy first prevents its draw from ever
            // publishing. Keep the legacy implication only when M27 is not
            // the requested producer.
            sphereOutsideRequested =
                ReadBooleanEnvironment(EnvironmentVariable) ||
                HasCommandLineArgument(CommandLineArgument) ||
                EndfieldRecoveredDeferredResolverBindingPolicy.IsRequested &&
                !endminfM27Requested;
            requested = sphereOutsideRequested || endminfM27Requested;
            Shader.SetGlobalFloat(ReadyId, 0.0f);
            Shader.SetGlobalFloat(EndminfM27ReadyId, 0.0f);
            InvalidatePublication();
            InvalidateMotionHistory();
            PublishBlackFallbacks();
        }

        public void Dispose()
        {
            InvalidatePublication();
            InvalidateMotionHistory();
            ReleaseResources();
            ReleaseObject(endminfM27Material);
            endminfM27Material = null;
            ReleaseObject(endminfM27ExactExpandedMesh);
            endminfM27ExactExpandedMesh = null;
            endminfM27SourceMaterialId = 0;
            Shader.SetGlobalFloat(ReadyId, 0.0f);
            Shader.SetGlobalFloat(EndminfM27ReadyId, 0.0f);
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

            // This signal proves that the M27 draw itself was published in
            // the current camera frame. The generic frame-ready signal also
            // covers SphereOutside and therefore cannot establish M27 alone.
            Shader.SetGlobalFloat(EndminfM27ReadyId, 0.0f);

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
            renderer = null;
            material = null;
            passIndex = -1;
            if (sphereOutsideRequested &&
                !TryResolveSource(
                    camera,
                    out renderer,
                    out material,
                    out passIndex,
                    out failure))
            {
                FailClosed(context, failure);
                return false;
            }
            if (!TryEnsureResources(width, height, out failure))
            {
                FailClosed(context, failure);
                return false;
            }
            ParticleSystemRenderer endminfM27Renderer = null;
            Material endminfM27SourceMaterial = null;
            Mesh endminfM27Mesh = null;
            int endminfM27PassIndex = -1;
            if (endminfM27Requested &&
                (!TryResolveEndminfM27Source(
                    camera,
                    out endminfM27Renderer,
                    out endminfM27SourceMaterial,
                    out endminfM27Mesh,
                    out failure) ||
                 endminfM27Renderer != null &&
                 !TryEnsureEndminfM27Material(
                    endminfM27SourceMaterial,
                    out endminfM27PassIndex,
                    out failure)))
            {
                FailClosed(context, failure);
                return false;
            }
            Renderer motionOwner = renderer != null
                ? renderer
                : endminfM27Renderer;
            if (motionOwner == null)
            {
                FailClosed(
                    context,
                    string.IsNullOrEmpty(failure)
                        ? "no requested HGBuffer producer is active"
                        : failure);
                return false;
            }

            var command = new CommandBuffer
            {
                name = "Recovered same-frame HGBuffer sidecar"
            };
            try
            {
                Matrix4x4 gpuViewProjection =
                    GL.GetGPUProjectionMatrix(
                        camera.nonJitteredProjectionMatrix,
                        true) *
                    camera.worldToCameraMatrix;
                Matrix4x4 objectToWorld = motionOwner.localToWorldMatrix;
                bool motionHistoryValid =
                    hasPreviousGpuViewProjection &&
                    previousCameraInstanceId == camera.GetInstanceID() &&
                    previousRendererInstanceId == motionOwner.GetInstanceID() &&
                    previousFrame == Time.frameCount - 1 &&
                    previousWidth == width &&
                    previousHeight == height;
                Matrix4x4 previousViewProjection = motionHistoryValid
                    ? previousGpuViewProjection
                    : gpuViewProjection;
                Matrix4x4 previousObjectTransform = motionHistoryValid
                    ? previousObjectToWorld
                    : objectToWorld;
                Vector4 motionVectorsParams =
                    GetMotionVectorsParams(motionOwner);
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
                    gpuViewProjection);
                command.SetGlobalMatrix(
                    PreviousGpuViewProjectionId,
                    previousViewProjection);
                command.SetGlobalMatrix(
                    PreviousObjectToWorldId,
                    previousObjectTransform);
                command.SetGlobalFloat(
                    MotionValidId,
                    motionHistoryValid ? 1.0f : 0.0f);
                command.SetGlobalVector(
                    MotionVectorsParamsId,
                    motionVectorsParams);
                if (renderer != null)
                    command.DrawRenderer(renderer, material, 0, passIndex);
                if (endminfM27Renderer != null)
                {
                    if (endminfM27ExactDxbcRequested)
                    {
                        if (endminfM27ExactExpandedMesh == null)
                            endminfM27ExactExpandedMesh =
                                EndfieldRecoveredM27ExactCaptureData
                                    .CreateExpandedMesh();
                        command.DrawMesh(
                            endminfM27ExactExpandedMesh,
                            Matrix4x4.identity,
                            endminfM27Material,
                            0,
                            endminfM27PassIndex);
                    }
                    else
                    {
                        if (endminfM27Renderer.mesh != endminfM27Mesh)
                        {
                            endminfM27Renderer.renderMode =
                                ParticleSystemRenderMode.Mesh;
                            endminfM27Renderer.SetMeshes(
                                new[] { endminfM27Mesh },
                                1);
                        }
                        command.DrawRenderer(
                            endminfM27Renderer,
                            endminfM27Material,
                            0,
                            endminfM27PassIndex);
                    }
                    command.SetGlobalFloat(EndminfM27ReadyId, 1.0f);
                    RequestEndminfM27Readbacks(command, camera.name);
                }

                command.SetGlobalTexture(SceneColorId, sceneColor);
                command.SetGlobalTexture(SceneMVId, sceneMV);
                command.SetGlobalTexture(GBufferAId, gBufferA);
                command.SetGlobalTexture(GBufferBId, gBufferB);
                command.SetGlobalTexture(GBufferCId, gBufferC);
                // Source-closed selected pass-0 bridge: t23=A, t24=B,
                // t25=C. These are diagnostic aliases only; no production
                // resolver draw is enabled by this publication.
                command.SetGlobalTexture(ResolverGBufferT23Id, gBufferA);
                command.SetGlobalTexture(ResolverGBufferT24Id, gBufferB);
                command.SetGlobalTexture(ResolverGBufferT25Id, gBufferC);
                command.SetGlobalTexture(ResolverSourceTextureT23Id, gBufferA);
                command.SetGlobalTexture(ResolverSourceTextureT24Id, gBufferB);
                command.SetGlobalTexture(ResolverSourceTextureT25Id, gBufferC);
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
                PublishFrame(camera, width, height);
                if (endminfM27Renderer != null)
                {
                    endminfM27PublishedFrame = Time.frameCount;
                    endminfM27PublishedCameraInstanceId = camera.GetInstanceID();
                    endminfM27PublishedWidth = width;
                    endminfM27PublishedHeight = height;
                }
                previousGpuViewProjection = gpuViewProjection;
                previousObjectToWorld = objectToWorld;
                hasPreviousGpuViewProjection = true;
                previousCameraInstanceId = camera.GetInstanceID();
                previousRendererInstanceId = motionOwner.GetInstanceID();
                previousFrame = Time.frameCount;
                previousWidth = width;
                previousHeight = height;
            }
            finally
            {
                command.Release();
            }

            if (renderer != null && !activationLogged)
            {
                Debug.Log(
                    "Recovered SphereOutside same-frame HGBuffer sidecar active: " +
                    $"camera={camera.name}, size={width}x{height}, " +
                    "attachments=B10G11R11/A2B10G10R10/A2B10G10R10/" +
                    "A2B10G10R10/R8G8B8A8_SRGB+D32S8, " +
                    "sourceRendererDisabled=" + (!renderer.enabled) + ", " +
                    "resolverGBufferBindings=t23:A,t24:B,t25:C, " +
                    "resolverSourceIdentifiers=t23:_60,t24:_61,t25:_62, " +
                    "pass0ConsumerEnabled=false.");
                activationLogged = true;
            }
            failureLogged = false;
            if (endminfM27Renderer != null && !endminfM27ActivationLogged)
            {
                string baseMapProperty = endminfM27ExactDxbcRequested
                    ? "_M27T5"
                    : "_BaseColorMap";
                Texture m27BaseMap = endminfM27Material.GetTexture(
                    baseMapProperty);
                Debug.Log(
                    "Recovered Endminf M27 five-MRT HGBuffer sidecar active: " +
                    $"camera={camera.name}, rendererPathId={EndminfM27RendererPathId}, " +
                    $"particles={endminfM27Renderer.GetComponent<ParticleSystem>().particleCount}, " +
                    $"baseMap={(m27BaseMap == null ? "<null>" : m27BaseMap.name)}, " +
                    $"baseMapSize={(m27BaseMap == null ? "0x0" : m27BaseMap.width + "x" + m27BaseMap.height)}, " +
                    $"exactDxbc={endminfM27ExactDxbcRequested}, " +
                    (endminfM27ExactDxbcRequested
                        ? "captureFrame=" +
                            EndfieldRecoveredM27ExactCaptureData.SourceFrame +
                            ", capturedExpandedVertices=" +
                            EndfieldRecoveredM27ExactCaptureData.ExpandedVertexCount +
                            ", capturedExpandedIndices=" +
                            EndfieldRecoveredM27ExactCaptureData.ExpandedIndexCount +
                            ", "
                        : $"baseColor={endminfM27Material.GetColor("_BaseColor")}, " +
                          $"baseTintCover={endminfM27Material.GetFloat("_BaseColorTintCover").ToString("R", CultureInfo.InvariantCulture)}, " +
                          $"baseBrighterScale={endminfM27Material.GetFloat("_BaseColorBrighterScale").ToString("R", CultureInfo.InvariantCulture)}, ") +
                    "geometryRendererEnabled=true, ordinaryCameraExcluded=true, " +
                    "presented=false.");
                endminfM27ActivationLogged = true;
            }
            return true;
        }

        internal bool TryGetResolverInputs(
            Camera camera,
            int width,
            int height,
            out RenderTexture resolverT23,
            out RenderTexture resolverT24,
            out RenderTexture resolverT25,
            out uint resolverPublicationSerial,
            out string failure)
        {
            resolverT23 = gBufferA;
            resolverT24 = gBufferB;
            resolverT25 = gBufferC;
            resolverPublicationSerial = publicationSerial;
            failure = string.Empty;
            if (!requested)
            {
                failure = "deferred GBuffer sidecar selector is disabled";
                return false;
            }
            if (camera == null)
            {
                failure = "resolver requested without a camera";
                return false;
            }
            if (!publicationValid)
            {
                failure =
                    "same-frame deferred GBuffer has not published resolver inputs";
                return false;
            }
            int actualCameraInstanceId = camera.GetInstanceID();
            int actualFrame = Time.frameCount;
            if (publishedFrame != actualFrame ||
                publishedCameraInstanceId != actualCameraInstanceId ||
                publishedWidth != width ||
                publishedHeight != height)
            {
                failure =
                    "resolver input publication stamp mismatch: " +
                    $"expected frame={actualFrame},camera={actualCameraInstanceId}," +
                    $"size={width}x{height}; " +
                    $"actual frame={publishedFrame},camera={publishedCameraInstanceId}," +
                    $"size={publishedWidth}x{publishedHeight}," +
                    $"serial={publicationSerial}";
                return false;
            }
            if (resolverT23 == null || !resolverT23.IsCreated() ||
                resolverT24 == null || !resolverT24.IsCreated() ||
                resolverT25 == null || !resolverT25.IsCreated())
            {
                failure =
                    "same-frame A/B/C resolver textures are unavailable " +
                    $"for publication serial {publicationSerial}";
                return false;
            }
            return true;
        }

        internal bool TryGetEndminfM27PresentationInputs(
            Camera camera,
            int width,
            int height,
            out RenderTexture sourceSceneColor,
            out RenderTexture mask,
            out RenderTexture depth,
            out string failure)
        {
            sourceSceneColor = sceneColor;
            mask = gBufferC;
            depth = depthStencil;
            failure = string.Empty;
            if (!endminfM27Requested)
            {
                failure = "Endminf M27 producer is not requested";
                return false;
            }
            if (!TryGetResolverInputs(
                    camera,
                    width,
                    height,
                    out _,
                    out _,
                    out _,
                    out _,
                    out failure))
                return false;
            if (endminfM27PublishedFrame != Time.frameCount ||
                endminfM27PublishedCameraInstanceId != camera.GetInstanceID() ||
                endminfM27PublishedWidth != width ||
                endminfM27PublishedHeight != height)
            {
                failure =
                    "Endminf M27 has no identity-specific same-frame publication";
                return false;
            }
            if (sourceSceneColor == null || !sourceSceneColor.IsCreated() ||
                mask == null || !mask.IsCreated() ||
                depth == null || !depth.IsCreated())
            {
                failure = "Endminf M27 presentation mask/depth is unavailable";
                return false;
            }
            return true;
        }

        internal bool TryGetResolverDepth(
            Camera camera,
            int width,
            int height,
            out RenderTexture resolverDepth,
            out string failure)
        {
            resolverDepth = depthStencil;
            if (!TryGetResolverInputs(
                    camera,
                    width,
                    height,
                    out _,
                    out _,
                    out _,
                    out _,
                    out failure))
                return false;
            if (resolverDepth == null || !resolverDepth.IsCreated())
            {
                failure =
                    "same-frame deferred resolver depth texture is unavailable " +
                    $"for publication serial {publicationSerial}";
                return false;
            }
            return true;
        }

        private void FailClosed(
            ScriptableRenderContext context,
            string failure)
        {
            InvalidatePublication();
            InvalidateMotionHistory();
            var command = new CommandBuffer
            {
                name = "Fail-closed recovered deferred HGBuffer sidecar"
            };
            command.SetGlobalFloat(ReadyId, 0.0f);
            command.SetGlobalFloat(EndminfM27ReadyId, 0.0f);
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
                    "Recovered same-frame HGBuffer sidecar failed closed: " +
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

        private static bool TryResolveEndminfM27Source(
            Camera camera,
            out ParticleSystemRenderer renderer,
            out Material sourceMaterial,
            out Mesh mesh,
            out string failure)
        {
            renderer = null;
            sourceMaterial = null;
            mesh = null;
            failure = string.Empty;
            if (camera == null)
            {
                failure = "the Endminf M27 owner received no camera";
                return false;
            }

            EndfieldEndminfLitEffectCompatibilityBinding[] bindings =
                Resources.FindObjectsOfTypeAll<
                    EndfieldEndminfLitEffectCompatibilityBinding>();
            List<EndfieldEndminfLitEffectCompatibilityBinding.Row> rows =
                bindings
                    .Where(binding =>
                        binding != null &&
                        binding.gameObject.scene.IsValid() &&
                        binding.gameObject.scene == camera.gameObject.scene &&
                        binding.rows != null)
                    .SelectMany(binding => binding.rows)
                    .Where(row =>
                        row != null &&
                        row.particleRendererPathId == EndminfM27RendererPathId &&
                        row.renderer != null &&
                        row.renderer.gameObject.activeInHierarchy)
                    .ToList();
            // The overview_02 root is transient. No active row is the exact
            // no-draw state before spawn and after source cleanup.
            if (rows.Count == 0)
            {
                int sceneBindingCount = bindings.Count(binding =>
                    binding != null &&
                    binding.gameObject.scene.IsValid() &&
                    binding.gameObject.scene == camera.gameObject.scene);
                failure =
                    "Endminf M27 has no active direct row (bindings=" +
                    bindings.Length + ", sameScene=" + sceneBindingCount + ")";
                return true;
            }
            if (rows.Count != 1)
            {
                failure =
                    "expected at most one active scene-local Endminf M27 row; found " +
                    rows.Count;
                return false;
            }

            EndfieldEndminfLitEffectCompatibilityBinding.Row row = rows[0];
            if (row.materialPathId != EndminfM27MaterialPathId ||
                row.meshPathId != EndminfM27MeshPathId ||
                row.material == null || row.mesh == null)
            {
                failure = "the Endminf M27 direct material/mesh identity drifted";
                return false;
            }
            if (row.renderer.enabled)
            {
                if (row.renderer.gameObject.layer !=
                        EndfieldEndminfLitEffectCompatibilityBinding.ExactM27Layer ||
                    (camera.cullingMask & (1 <<
                        EndfieldEndminfLitEffectCompatibilityBinding.ExactM27Layer)) != 0)
                {
                    failure =
                        "the exact M27 particle geometry owner is not isolated " +
                        "from the ordinary camera cull";
                    return false;
                }
            }
            else
            {
                failure =
                    "the exact M27 particle geometry owner is disabled";
                return false;
            }
            ParticleSystem particles = row.renderer.GetComponent<ParticleSystem>();
            if (particles == null)
            {
                failure = "the Endminf M27 row has no ParticleSystem";
                return false;
            }
            if (!particles.isPlaying || particles.particleCount == 0)
            {
                failure =
                    "Endminf M27 direct row is active but has no live particles";
                return true;
            }
            if (row.material.shader == null ||
                row.material.shader.name !=
                    "Hidden/Endfield/Compatibility/Endminf/LitEffectParallax")
            {
                failure = "the retained Endminf M27 source material shader drifted";
                return false;
            }

            renderer = row.renderer;
            sourceMaterial = row.material;
            mesh = row.mesh;
            return true;
        }

        private bool TryEnsureEndminfM27Material(
            Material sourceMaterial,
            out int passIndex,
            out string failure)
        {
            passIndex = -1;
            failure = string.Empty;
            if (sourceMaterial == null)
            {
                failure = "the Endminf M27 source material is absent";
                return false;
            }
            if (endminfM27ExactDxbcRequested &&
                !EndfieldRecoveredM27ExactCaptureData.ExactVertexEnvelopeClosed)
            {
                failure =
                    "the exact M27 vertex b0 envelope is incomplete: captured " +
                    EndfieldRecoveredM27ExactCaptureData.CapturedB0Float4Count +
                    " float4s, but retail projection reads through c81";
                return false;
            }
            int sourceId = sourceMaterial.GetInstanceID();
            if (endminfM27Material == null ||
                endminfM27SourceMaterialId != sourceId)
            {
                ReleaseObject(endminfM27Material);
                endminfM27Material = null;
                string shaderName = endminfM27ExactDxbcRequested
                    ? EndminfM27ExactShaderName
                    : EndminfM27ShaderName;
                Shader shader = Shader.Find(shaderName);
                if (shader == null || !shader.isSupported)
                {
                    failure =
                        "the recovered Endminf M27 five-MRT shader is unavailable: " +
                        shaderName;
                    return false;
                }
                endminfM27Material = new Material(shader)
                {
                    name = "Recovered exact-contract Endminf M27 HGBuffer",
                    hideFlags = HideFlags.HideAndDontSave,
                };
                if (endminfM27ExactDxbcRequested)
                    BindExactM27CaptureData(sourceMaterial, endminfM27Material);
                else
                    CopyExactM27SourceProperties(
                        sourceMaterial,
                        endminfM27Material);
                endminfM27SourceMaterialId = sourceId;
            }
            passIndex = endminfM27Material.FindPass(
                endminfM27ExactDxbcRequested
                    ? EndminfM27ExactPassName
                    : EndminfM27PassName);
            if (passIndex < 0)
            {
                failure = "the recovered Endminf M27 HGBuffer pass is unavailable";
                return false;
            }
            return true;
        }

        private static void BindExactM27CaptureData(
            Material source,
            Material destination)
        {
            Vector4[][] constantBuffers =
                EndfieldRecoveredM27ExactCaptureData
                    .CreateConstantBufferValues();
            for (int slot = 0; slot < constantBuffers.Length; ++slot)
            {
                destination.SetVectorArray(
                    "_M27CB" + slot,
                    constantBuffers[slot]);
            }

            destination.SetTexture("_M27T0", Texture2D.blackTexture);
            destination.SetTexture("_M27T1", Texture2D.blackTexture);
            string[] sourceTextures =
            {
                "_ParallaxMap",
                "_NormalMap",
                "_MROMap",
                "_BaseColorMap",
            };
            for (int index = 0; index < sourceTextures.Length; ++index)
            {
                Texture texture = source.HasProperty(sourceTextures[index])
                    ? source.GetTexture(sourceTextures[index])
                    : null;
                destination.SetTexture(
                    "_M27T" + (index + 2),
                    texture != null ? texture : Texture2D.blackTexture);
            }
            destination.EnableKeyword(EndminfM27ExactKeyword);
        }

        private static void CopyExactM27SourceProperties(
            Material source,
            Material destination)
        {
            // CopyPropertiesFromMaterial also copies zero-valued defaults for
            // fields absent from the narrow compatibility shader. That erased
            // captured retail b3 values such as c4.z
            // (_BaseColorBrighterScale=1) and made GBufferC entirely black.
            // Transfer only properties serialized by the retained M27 asset;
            // every other destination default is hash-pinned capture data.
            string[] textureProperties =
            {
                "_BaseColorMap",
                "_MROMap",
                "_NormalMap",
                "_ParallaxMap",
            };
            foreach (string property in textureProperties)
            {
                if (!source.HasProperty(property) ||
                    !destination.HasProperty(property))
                    continue;
                destination.SetTexture(property, source.GetTexture(property));
                destination.SetTextureScale(
                    property,
                    source.GetTextureScale(property));
                destination.SetTextureOffset(
                    property,
                    source.GetTextureOffset(property));
            }

            string[] colorProperties =
            {
                "_BaseColor",
                "_ParallaxColor",
            };
            foreach (string property in colorProperties)
            {
                if (source.HasProperty(property) &&
                    destination.HasProperty(property))
                    destination.SetColor(property, source.GetColor(property));
            }

            string[] floatProperties =
            {
                "_ParallaxIntensity",
                "_ParallaxStrength",
                "_ParallaxTilling",
                "_ParallaxMarchNum",
                "_ParallaxMinBrightness",
            };
            foreach (string property in floatProperties)
            {
                if (source.HasProperty(property) &&
                    destination.HasProperty(property))
                    destination.SetFloat(property, source.GetFloat(property));
            }
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

        private void RequestEndminfM27Readbacks(
            CommandBuffer command,
            string cameraName)
        {
            if (endminfM27ReadbackRequested ||
                command == null ||
                !SystemInfo.supportsAsyncGPUReadback)
                return;
            endminfM27ReadbackRequested = true;
            RequestReadback(command, "M27SceneColor", sceneColor, cameraName);
            RequestReadback(command, "M27SceneMV", sceneMV, cameraName);
            RequestReadback(command, "M27GBufferA", gBufferA, cameraName);
            RequestReadback(command, "M27GBufferB", gBufferB, cameraName);
            RequestReadback(command, "M27GBufferC", gBufferC, cameraName);
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
            InvalidatePublication();
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

        private void PublishFrame(Camera camera, int width, int height)
        {
            publicationSerial = publicationSerial == uint.MaxValue
                ? 1u
                : publicationSerial + 1u;
            publicationValid = true;
            publishedFrame = Time.frameCount;
            publishedCameraInstanceId = camera != null
                ? camera.GetInstanceID()
                : 0;
            publishedWidth = width;
            publishedHeight = height;
        }

        private void InvalidatePublication()
        {
            publicationValid = false;
            publishedFrame = -1;
            publishedCameraInstanceId = 0;
            publishedWidth = 0;
            publishedHeight = 0;
            endminfM27PublishedFrame = -1;
            endminfM27PublishedCameraInstanceId = 0;
            endminfM27PublishedWidth = 0;
            endminfM27PublishedHeight = 0;
        }

        private void InvalidateMotionHistory()
        {
            hasPreviousGpuViewProjection = false;
            previousGpuViewProjection = Matrix4x4.identity;
            previousObjectToWorld = Matrix4x4.identity;
            previousCameraInstanceId = 0;
            previousRendererInstanceId = 0;
            previousFrame = -1;
            previousWidth = 0;
            previousHeight = 0;
        }

        private static Vector4 GetMotionVectorsParams(Renderer renderer)
        {
            // Unity's built-in DOTS fallback and the HDRP per-draw producer
            // use (x=deformation, y=allow motion, z=z bias, w=object/camera
            // history). SphereOutside is a static MeshRenderer with the
            // serialized Object mode, so its source-closed value is
            // (0,1,0,1). Keep the other managed modes explicit so a future
            // recovered source renderer cannot silently inherit object
            // history or publish a false motion sample.
            if (renderer == null)
                return new Vector4(0.0f, 0.0f, 0.0f, 1.0f);

            switch (renderer.motionVectorGenerationMode)
            {
                case MotionVectorGenerationMode.ForceNoMotion:
                    return new Vector4(0.0f, 0.0f, 0.0f, 1.0f);
                case MotionVectorGenerationMode.Camera:
                    return new Vector4(0.0f, 1.0f, 0.0f, 0.0f);
                case MotionVectorGenerationMode.Object:
                default:
                    return new Vector4(0.0f, 1.0f, 0.0f, 1.0f);
            }
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

        private static void ReleaseObject(UnityEngine.Object value)
        {
            if (value == null)
                return;
            if (Application.isPlaying)
                UnityEngine.Object.Destroy(value);
            else
                UnityEngine.Object.DestroyImmediate(value);
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
