using System;
using UnityEngine;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Publishes the source-closed SphereOutside sidecar depth and resolved
    /// color into the physical CharInfo camera before ForwardOpaque. The path
    /// is opt-in and fails closed unless the same-frame SphereOutside producer
    /// and exact deferred resolver both completed.
    /// </summary>
    internal sealed class EndfieldRecoveredSphereOutsideDeferredPresentation :
        IDisposable
    {
        internal const string EnvironmentVariable =
            "ENDFIELD_RECOVERED_SPHERE_OUTSIDE_PRESENTATION";
        private const string ShaderName =
            "Hidden/Endfield/Recovered/CharInfo/SphereOutsideDeferredPresentation";
        private static readonly int ResolvedColorId =
            Shader.PropertyToID("_EndfieldSphereResolvedColor");
        private static readonly int SourceSceneColorId =
            Shader.PropertyToID("_EndfieldSphereSourceSceneColor");
        private static readonly int OwnershipMaskId =
            Shader.PropertyToID("_EndfieldSphereOwnershipMask");
        private static readonly int PrivateDepthId =
            Shader.PropertyToID("_EndfieldSpherePrivateDepth");
        internal static readonly int ReadyId =
            Shader.PropertyToID("_EndfieldRecoveredSphereOutsidePresentationReady");

        private readonly bool requested;
        private Material material;
        private int depthPassIndex = -1;
        private int colorPassIndex = -1;
        private int publishedFrame = -1;
        private int publishedCamera;
        private int publishedWidth;
        private int publishedHeight;
        private bool loggedFailure;
        private bool loggedActivation;

        internal EndfieldRecoveredSphereOutsideDeferredPresentation()
        {
            requested = IsEnabled(Environment.GetEnvironmentVariable(
                EnvironmentVariable));
            Shader.SetGlobalFloat(ReadyId, 0.0f);
        }

        internal bool PublishDepth(
            ScriptableRenderContext context,
            Camera camera,
            int width,
            int height,
            bool gBufferFrameReady,
            EndfieldRecoveredDeferredGBufferFrame gBufferFrame,
            RenderTargetIdentifier canonicalColorTarget,
            RenderTargetIdentifier canonicalDepthTarget)
        {
            publishedFrame = -1;
            if (!requested)
                return false;
            if (!gBufferFrameReady || camera == null || gBufferFrame == null)
                return FailClosed("SphereOutside depth inputs are unavailable");
            if (!gBufferFrame.TryGetSphereOutsidePresentationInputs(
                    camera,
                    width,
                    height,
                    out _,
                    out RenderTexture mask,
                    out RenderTexture depth,
                    out string inputFailure))
                return FailClosed(inputFailure);
            if (!TryEnsureMaterial(out string materialFailure))
                return FailClosed(materialFailure);

            var command = new CommandBuffer
            {
                name = "Publish recovered SphereOutside canonical depth"
            };
            try
            {
                command.SetGlobalTexture(OwnershipMaskId, mask);
                command.SetGlobalTexture(PrivateDepthId, depth);
                command.SetRenderTarget(canonicalColorTarget, canonicalDepthTarget);
                command.SetViewport(new Rect(0.0f, 0.0f, width, height));
                command.DrawProcedural(
                    Matrix4x4.identity,
                    material,
                    depthPassIndex,
                    MeshTopology.Triangles,
                    3,
                    1);
                context.ExecuteCommandBuffer(command);
            }
            finally
            {
                command.Release();
            }
            publishedFrame = Time.frameCount;
            publishedCamera = camera.GetInstanceID();
            publishedWidth = width;
            publishedHeight = height;
            return true;
        }

        internal bool Render(
            ScriptableRenderContext context,
            Camera camera,
            int width,
            int height,
            bool deferredConsumerReady,
            EndfieldRecoveredDeferredGBufferFrame gBufferFrame,
            RenderTexture resolvedColor,
            RenderTargetIdentifier canonicalColorTarget,
            RenderTargetIdentifier canonicalDepthTarget)
        {
            Shader.SetGlobalFloat(ReadyId, 0.0f);
            if (!requested)
                return false;
            if (!deferredConsumerReady)
                return FailClosed("SphereOutside deferred resolver output is not ready");
            if (camera == null || gBufferFrame == null ||
                resolvedColor == null || !resolvedColor.IsCreated())
                return FailClosed("SphereOutside presentation inputs are unavailable");
            if (!gBufferFrame.TryGetSphereOutsidePresentationInputs(
                    camera,
                    width,
                    height,
                    out RenderTexture sourceSceneColor,
                    out RenderTexture mask,
                    out _,
                    out string inputFailure))
                return FailClosed(inputFailure);
            if (publishedFrame != Time.frameCount ||
                publishedCamera != camera.GetInstanceID() ||
                publishedWidth != width || publishedHeight != height)
                return FailClosed(
                    "SphereOutside depth was not published before deferred presentation");
            if (!TryEnsureMaterial(out string materialFailure))
                return FailClosed(materialFailure);

            var command = new CommandBuffer
            {
                name = "Present recovered SphereOutside deferred resolve"
            };
            try
            {
                command.SetGlobalTexture(ResolvedColorId, resolvedColor);
                command.SetGlobalTexture(SourceSceneColorId, sourceSceneColor);
                command.SetGlobalTexture(OwnershipMaskId, mask);
                command.SetRenderTarget(canonicalColorTarget, canonicalDepthTarget);
                command.SetViewport(new Rect(0.0f, 0.0f, width, height));
                command.DrawProcedural(
                    Matrix4x4.identity,
                    material,
                    colorPassIndex,
                    MeshTopology.Triangles,
                    3,
                    1);
                command.SetGlobalFloat(ReadyId, 1.0f);
                context.ExecuteCommandBuffer(command);
            }
            finally
            {
                command.Release();
            }
            if (!loggedActivation)
            {
                Debug.Log(
                    "Recovered SphereOutside physical deferred presentation active: " +
                    $"camera={camera.name}, size={width}x{height}, " +
                    "depth=Greater+write, color=Equal+replace, ordering=before-ForwardOpaque.");
                loggedActivation = true;
            }
            loggedFailure = false;
            return true;
        }

        public void Dispose()
        {
            Shader.SetGlobalFloat(ReadyId, 0.0f);
            if (material != null)
            {
                if (Application.isPlaying)
                    UnityEngine.Object.Destroy(material);
                else
                    UnityEngine.Object.DestroyImmediate(material);
            }
            material = null;
            depthPassIndex = -1;
            colorPassIndex = -1;
            publishedFrame = -1;
        }

        private bool TryEnsureMaterial(out string failure)
        {
            failure = string.Empty;
            if (material != null && depthPassIndex >= 0 && colorPassIndex >= 0)
                return true;
            Shader shader = Shader.Find(ShaderName);
            if (shader == null || !shader.isSupported)
            {
                failure = "SphereOutside deferred presentation shader is unavailable";
                return false;
            }
            material = new Material(shader)
            {
                name = "Recovered SphereOutside deferred presentation",
                hideFlags = HideFlags.HideAndDontSave,
            };
            depthPassIndex = material.FindPass("PublishSphereOutsideDepth");
            colorPassIndex = material.FindPass("PresentSphereOutsideDeferredResolve");
            if (depthPassIndex < 0 || colorPassIndex < 0)
            {
                failure = "SphereOutside presentation shader passes are unavailable";
                return false;
            }
            return true;
        }

        private bool FailClosed(string failure)
        {
            Shader.SetGlobalFloat(ReadyId, 0.0f);
            if (!loggedFailure)
            {
                Debug.LogWarning(
                    "Recovered SphereOutside presentation failed closed: " + failure);
                loggedFailure = true;
            }
            return false;
        }

        private static bool IsEnabled(string value)
        {
            return value == "1" ||
                string.Equals(value, "true", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(value, "yes", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(value, "on", StringComparison.OrdinalIgnoreCase);
        }
    }
}
