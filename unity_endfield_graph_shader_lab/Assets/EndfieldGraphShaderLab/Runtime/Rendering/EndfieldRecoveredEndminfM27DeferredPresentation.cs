using System;
using Unity.Collections;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Presents only pixels owned by the identity-gated M27 HGBuffer draw.
    /// The private particle depth is written into the canonical depth target
    /// before ForwardOpaque, then presents color after ForwardOpaque. This
    /// preserves actor occlusion without letting the CharInfo forward cohort
    /// overwrite the resolved shards.
    /// </summary>
    internal sealed class EndfieldRecoveredEndminfM27DeferredPresentation :
        IDisposable
    {
        internal const string EnvironmentVariable =
            "ENDFIELD_RECOVERED_ENDMINF_M27_PRESENTATION";
        private const string ShaderName =
            "Hidden/Endfield/Recovered/Endminf/M27DeferredPresentation";
        private static readonly int ResolvedColorId =
            Shader.PropertyToID("_EndfieldM27ResolvedColor");
        private static readonly int SourceSceneColorId =
            Shader.PropertyToID("_EndfieldM27SourceSceneColor");
        private static readonly int OwnershipMaskId =
            Shader.PropertyToID("_EndfieldM27OwnershipMask");
        private static readonly int PrivateDepthId =
            Shader.PropertyToID("_EndfieldM27PrivateDepth");
        private static readonly int ReadyId =
            Shader.PropertyToID("_EndfieldRecoveredEndminfM27PresentationReady");

        private readonly bool requested;
        private Material material;
        private int depthPassIndex = -1;
        private int colorPassIndex = -1;
        private int depthPublicationFrame = -1;
        private int depthPublicationCameraInstanceId;
        private int depthPublicationWidth;
        private int depthPublicationHeight;
        private bool loggedFailure;
        private string lastFailure = string.Empty;
        private bool activationLogged;
        private RenderTexture diagnosticBefore;
        private RenderTexture diagnosticAfter;
        private byte[] diagnosticBeforeBytes;
        private byte[] diagnosticAfterBytes;
        private bool diagnosticRequested;
        private bool diagnosticLogged;
        private byte[] diagnosticSourceSceneBytes;
        private byte[] diagnosticResolvedBytes;
        private byte[] diagnosticMaskBytes;
        private bool inputDiagnosticLogged;
        private int diagnosticWidth;
        private int diagnosticHeight;

        internal EndfieldRecoveredEndminfM27DeferredPresentation()
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
            depthPublicationFrame = -1;
            if (!requested)
                return false;
            if (EndfieldRecoveredEndminfM27ExactRuntime.Requested &&
                !EndfieldRecoveredEndminfM27ExactRuntime.HandCrystalPacketSelected)
                return false;
            if (!gBufferFrameReady || camera == null || gBufferFrame == null)
                return FailClosed("M27 depth publication inputs are unavailable");
            if (!gBufferFrame.TryGetEndminfM27PresentationInputs(
                    camera,
                    width,
                    height,
                    out _,
                    out RenderTexture ownershipMask,
                    out RenderTexture privateDepth,
                    out string inputFailure))
                return FailClosed(inputFailure);
            if (!TryEnsureMaterial(out string materialFailure))
                return FailClosed(materialFailure);

            var command = new CommandBuffer
            {
                name = "Publish recovered Endminf M27 canonical depth"
            };
            try
            {
                command.SetGlobalTexture(OwnershipMaskId, ownershipMask);
                command.SetGlobalTexture(PrivateDepthId, privateDepth);
                command.SetRenderTarget(
                    canonicalColorTarget,
                    canonicalDepthTarget);
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
            depthPublicationFrame = Time.frameCount;
            depthPublicationCameraInstanceId = camera.GetInstanceID();
            depthPublicationWidth = width;
            depthPublicationHeight = height;
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
            RenderTextureDescriptor canonicalColorDescriptor,
            RenderTargetIdentifier canonicalColorTarget,
            RenderTargetIdentifier canonicalDepthTarget)
        {
            Shader.SetGlobalFloat(ReadyId, 0.0f);
            if (!requested)
                return false;
            if (EndfieldRecoveredEndminfM27ExactRuntime.Requested &&
                !EndfieldRecoveredEndminfM27ExactRuntime.HandCrystalPacketSelected)
                return false;
            if (!deferredConsumerReady)
                return FailClosed("deferred resolver output is not ready");
            if (camera == null || gBufferFrame == null ||
                resolvedColor == null || !resolvedColor.IsCreated())
                return FailClosed("presentation inputs are unavailable");
            if (!gBufferFrame.TryGetEndminfM27PresentationInputs(
                    camera,
                    width,
                    height,
                    out RenderTexture sourceSceneColor,
                    out RenderTexture ownershipMask,
                    out RenderTexture privateDepth,
                    out string inputFailure))
                return FailClosed(inputFailure);
            if (depthPublicationFrame != Time.frameCount ||
                depthPublicationCameraInstanceId != camera.GetInstanceID() ||
                depthPublicationWidth != width ||
                depthPublicationHeight != height)
            {
                return FailClosed(
                    "identity-specific M27 depth was not published before shadow generation");
            }
            if (!TryEnsureMaterial(out string materialFailure))
                return FailClosed(materialFailure);

            var command = new CommandBuffer
            {
                name = "Present recovered Endminf M27 deferred resolve"
            };
            try
            {
                bool captureDiagnostic =
                    TryPrepareDiagnostic(
                        width,
                        height,
                        canonicalColorDescriptor);
                if (captureDiagnostic)
                    command.CopyTexture(
                        canonicalColorTarget,
                        new RenderTargetIdentifier(diagnosticBefore));
                command.SetGlobalTexture(ResolvedColorId, resolvedColor);
                command.SetGlobalTexture(SourceSceneColorId, sourceSceneColor);
                command.SetGlobalTexture(OwnershipMaskId, ownershipMask);
                command.SetGlobalTexture(PrivateDepthId, privateDepth);
                command.SetRenderTarget(
                    canonicalColorTarget,
                    canonicalDepthTarget);
                command.SetViewport(new Rect(0.0f, 0.0f, width, height));
                command.DrawProcedural(
                    Matrix4x4.identity,
                    material,
                    colorPassIndex,
                    MeshTopology.Triangles,
                    3,
                    1);
                if (captureDiagnostic)
                {
                    command.CopyTexture(
                        canonicalColorTarget,
                        new RenderTargetIdentifier(diagnosticAfter));
                    diagnosticRequested = true;
                    command.RequestAsyncReadback(
                        diagnosticBefore,
                        0,
                        request => CompleteDiagnostic(request, true));
                    command.RequestAsyncReadback(
                        diagnosticAfter,
                        0,
                        request => CompleteDiagnostic(request, false));
                    command.RequestAsyncReadback(
                        sourceSceneColor,
                        0,
                        request => CompleteInputDiagnostic(request, 0));
                    command.RequestAsyncReadback(
                        resolvedColor,
                        0,
                        request => CompleteInputDiagnostic(request, 1));
                    command.RequestAsyncReadback(
                        ownershipMask,
                        0,
                        request => CompleteInputDiagnostic(request, 2));
                }
                command.SetGlobalFloat(ReadyId, 1.0f);
                context.ExecuteCommandBuffer(command);
            }
            finally
            {
                command.Release();
            }

            if (!activationLogged)
            {
                Debug.Log(
                    "Recovered Endminf M27 deferred presentation active: " +
                    $"camera={camera.name}, size={width}x{height}, " +
                    "ownerMask=SceneColor.rgb, depthPrepass=Greater+write, " +
                    "colorTest=Equal, colorDepthWrite=false, " +
                    "ordering=depth-before/color-after-ForwardOpaque, " +
                    "presented=true.");
                activationLogged = true;
            }
            loggedFailure = false;
            lastFailure = string.Empty;
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
                material = null;
            }
            depthPassIndex = -1;
            colorPassIndex = -1;
            depthPublicationFrame = -1;
            ReleaseTexture(diagnosticBefore);
            ReleaseTexture(diagnosticAfter);
            diagnosticBefore = null;
            diagnosticAfter = null;
        }

        private bool TryEnsureMaterial(out string failure)
        {
            failure = string.Empty;
            if (material != null && depthPassIndex >= 0 && colorPassIndex >= 0)
                return true;
            Shader shader = Shader.Find(ShaderName);
            if (shader == null || !shader.isSupported)
            {
                failure = "M27 deferred presentation shader is unavailable";
                return false;
            }
            material = new Material(shader)
            {
                name = "Recovered Endminf M27 deferred presentation",
                hideFlags = HideFlags.HideAndDontSave,
            };
            depthPassIndex = material.FindPass("PublishM27Depth");
            colorPassIndex = material.FindPass("PresentM27DeferredResolve");
            if (depthPassIndex < 0 || colorPassIndex < 0)
            {
                failure = "M27 deferred presentation passes are unavailable";
                if (Application.isPlaying)
                    UnityEngine.Object.Destroy(material);
                else
                    UnityEngine.Object.DestroyImmediate(material);
                material = null;
                depthPassIndex = -1;
                colorPassIndex = -1;
                return false;
            }
            return true;
        }

        private bool FailClosed(string failure)
        {
            if (!loggedFailure || !string.Equals(
                    failure,
                    lastFailure,
                    StringComparison.Ordinal))
            {
                Debug.LogWarning(
                    "Recovered Endminf M27 deferred presentation failed closed: " +
                    failure + ".");
                loggedFailure = true;
                lastFailure = failure;
            }
            return false;
        }

        private bool TryPrepareDiagnostic(
            int width,
            int height,
            RenderTextureDescriptor descriptor)
        {
            if (diagnosticRequested ||
                diagnosticBefore != null ||
                (EndfieldRecoveredEndminfM27ExactRuntime.Requested &&
                 !EndfieldRecoveredEndminfM27ExactRuntime.PeakStonePacketSelected) ||
                !SystemInfo.supportsAsyncGPUReadback ||
                descriptor.width != width ||
                descriptor.height != height ||
                descriptor.graphicsFormat == GraphicsFormat.None)
                return false;
            descriptor.depthBufferBits = 0;
            descriptor.depthStencilFormat = GraphicsFormat.None;
            descriptor.msaaSamples = 1;
            descriptor.useMipMap = false;
            descriptor.autoGenerateMips = false;
            diagnosticBefore = CreateDiagnosticTexture(
                descriptor,
                "Recovered M27 presentation before");
            diagnosticAfter = CreateDiagnosticTexture(
                descriptor,
                "Recovered M27 presentation after");
            diagnosticWidth = width;
            diagnosticHeight = height;
            return diagnosticBefore != null && diagnosticAfter != null;
        }

        private static RenderTexture CreateDiagnosticTexture(
            RenderTextureDescriptor descriptor,
            string name)
        {
            var texture = new RenderTexture(descriptor)
            {
                name = name,
                hideFlags = HideFlags.HideAndDontSave,
                filterMode = FilterMode.Point,
                wrapMode = TextureWrapMode.Clamp,
            };
            if (!texture.Create())
            {
                ReleaseTexture(texture);
                return null;
            }
            return texture;
        }

        private void CompleteDiagnostic(
            AsyncGPUReadbackRequest request,
            bool before)
        {
            if (request.hasError)
            {
                Debug.LogWarning(
                    "Recovered Endminf M27 presentation differential " +
                    "readback failed closed.");
                return;
            }
            NativeArray<byte> data = request.GetData<byte>();
            byte[] copy = data.ToArray();
            if (before)
                diagnosticBeforeBytes = copy;
            else
                diagnosticAfterBytes = copy;
            TryLogDiagnostic();
            TryLogInputDiagnostic();
        }

        private void TryLogDiagnostic()
        {
            if (diagnosticLogged ||
                diagnosticBeforeBytes == null ||
                diagnosticAfterBytes == null)
                return;
            diagnosticLogged = true;
            if (diagnosticBeforeBytes.Length != diagnosticAfterBytes.Length)
            {
                Debug.LogWarning(
                    "Recovered Endminf M27 presentation differential failed " +
                    "closed: readback lengths differ.");
                return;
            }
            int pixels = Math.Max(1, diagnosticWidth * diagnosticHeight);
            int bytesPerPixel = diagnosticBeforeBytes.Length / pixels;
            int changedPixels = 0;
            long absoluteByteDifference = 0;
            int minX = diagnosticWidth;
            int minY = diagnosticHeight;
            int maxX = -1;
            int maxY = -1;
            for (int pixel = 0; pixel < pixels; pixel++)
            {
                bool changed = false;
                int offset = pixel * bytesPerPixel;
                for (int lane = 0; lane < bytesPerPixel; lane++)
                {
                    int difference = Math.Abs(
                        diagnosticAfterBytes[offset + lane] -
                        diagnosticBeforeBytes[offset + lane]);
                    absoluteByteDifference += difference;
                    changed = changed || difference != 0;
                }
                if (!changed)
                    continue;
                changedPixels++;
                int x = pixel % diagnosticWidth;
                int y = pixel / diagnosticWidth;
                minX = Math.Min(minX, x);
                minY = Math.Min(minY, y);
                maxX = Math.Max(maxX, x);
                maxY = Math.Max(maxY, y);
            }
            Debug.Log(
                "Recovered Endminf M27 presentation same-command differential: " +
                $"size={diagnosticWidth}x{diagnosticHeight}, " +
                $"bytesPerPixel={bytesPerPixel}, changedPixels={changedPixels}, " +
                $"absoluteByteDifference={absoluteByteDifference}, " +
                $"bounds={(changedPixels == 0 ? "empty" : $"{minX},{minY}-{maxX + 1},{maxY + 1}")}, " +
                "sameFrame=true, presented=true.");
        }

        private void CompleteInputDiagnostic(
            AsyncGPUReadbackRequest request,
            int role)
        {
            if (request.hasError)
            {
                Debug.LogWarning(
                    "Recovered Endminf M27 presentation input readback " +
                    "failed closed: role=" + role + ".");
                return;
            }
            byte[] copy = request.GetData<byte>().ToArray();
            if (role == 0)
                diagnosticSourceSceneBytes = copy;
            else if (role == 1)
                diagnosticResolvedBytes = copy;
            else
                diagnosticMaskBytes = copy;
            TryLogInputDiagnostic();
        }

        private void TryLogInputDiagnostic()
        {
            if (inputDiagnosticLogged ||
                diagnosticSourceSceneBytes == null ||
                diagnosticResolvedBytes == null ||
                diagnosticMaskBytes == null ||
                diagnosticBeforeBytes == null)
                return;
            inputDiagnosticLogged = true;
            int pixels = diagnosticWidth * diagnosticHeight;
            if (diagnosticSourceSceneBytes.Length != pixels * 4 ||
                diagnosticMaskBytes.Length != pixels * 4 ||
                diagnosticResolvedBytes.Length != pixels * 16)
            {
                Debug.LogWarning(
                    "Recovered Endminf M27 presentation input diagnostic " +
                    "failed closed: unexpected readback byte lengths.");
                return;
            }
            uint clearScenePacked = BitConverter.ToUInt32(
                diagnosticSourceSceneBytes,
                0);
            int ownedPixels = 0;
            int authoredSceneDifferentFromClear = 0;
            int resolvedNonzeroPixels = 0;
            int resolvedMirrorYNonzeroPixels = 0;
            int canonicalEqualsSourcePixels = 0;
            float resolvedMinimum = float.PositiveInfinity;
            float resolvedMaximum = float.NegativeInfinity;
            for (int pixel = 0; pixel < pixels; pixel++)
            {
                int maskOffset = pixel * 4;
                if (diagnosticMaskBytes[maskOffset] == 0 &&
                    diagnosticMaskBytes[maskOffset + 1] == 0 &&
                    diagnosticMaskBytes[maskOffset + 2] == 0)
                    continue;
                ownedPixels++;
                if (BitConverter.ToUInt32(
                        diagnosticSourceSceneBytes,
                        pixel * 4) != clearScenePacked)
                    authoredSceneDifferentFromClear++;
                if (BitConverter.ToUInt32(diagnosticBeforeBytes, pixel * 4) ==
                    BitConverter.ToUInt32(
                        diagnosticSourceSceneBytes,
                        pixel * 4))
                    canonicalEqualsSourcePixels++;
                bool resolvedNonzero = false;
                for (int lane = 0; lane < 3; lane++)
                {
                    float value = BitConverter.ToSingle(
                        diagnosticResolvedBytes,
                        pixel * 16 + lane * 4);
                    if (float.IsNaN(value) || float.IsInfinity(value))
                        continue;
                    resolvedMinimum = Math.Min(resolvedMinimum, value);
                    resolvedMaximum = Math.Max(resolvedMaximum, value);
                    resolvedNonzero = resolvedNonzero || value != 0.0f;
                }
                if (resolvedNonzero)
                    resolvedNonzeroPixels++;
                int x = pixel % diagnosticWidth;
                int y = pixel / diagnosticWidth;
                int mirroredPixel =
                    (diagnosticHeight - 1 - y) * diagnosticWidth + x;
                bool mirrorYNonzero = false;
                for (int lane = 0; lane < 3; lane++)
                {
                    float value = BitConverter.ToSingle(
                        diagnosticResolvedBytes,
                        mirroredPixel * 16 + lane * 4);
                    mirrorYNonzero = mirrorYNonzero ||
                        (!float.IsNaN(value) &&
                         !float.IsInfinity(value) &&
                         value != 0.0f);
                }
                if (mirrorYNonzero)
                    resolvedMirrorYNonzeroPixels++;
            }
            // Depth range is reported by the M27 producer's own readback
            // separately; this joined report focuses on color ownership.
            Debug.Log(
                "Recovered Endminf M27 presentation joined input diagnostic: " +
                $"ownedPixels={ownedPixels}, " +
                $"authoredSceneDifferentFromClear={authoredSceneDifferentFromClear}, " +
                $"canonicalEqualsSourcePixels={canonicalEqualsSourcePixels}, " +
                $"resolvedNonzeroPixels={resolvedNonzeroPixels}, " +
                $"resolvedMirrorYNonzeroPixels={resolvedMirrorYNonzeroPixels}, " +
                $"resolvedRgbRange={resolvedMinimum:R}..{resolvedMaximum:R}, " +
                $"clearScenePacked=0x{clearScenePacked:x8}, sameFrame=true.");
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

        private static bool IsEnabled(string value)
        {
            return value == "1" ||
                string.Equals(value, "true", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(value, "yes", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(value, "on", StringComparison.OrdinalIgnoreCase);
        }
    }
}
