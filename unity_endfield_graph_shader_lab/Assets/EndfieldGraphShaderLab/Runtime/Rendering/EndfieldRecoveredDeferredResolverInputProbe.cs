using System;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Default-off, non-presented consumer probe for the source-closed
    /// deferred resolver input boundary. It reads the exact _60/_61/_62
    /// t23/t24/t25 order and the recovered b0-b8 bridge, but deliberately does
    /// not implement or submit the retail lighting result.
    /// </summary>
    internal sealed class EndfieldRecoveredDeferredResolverInputProbe : IDisposable
    {
        private const string ShaderName =
            "Hidden/Endfield/Recovered/DeferredResolverInputProbe";

        private static readonly int ReadyId = Shader.PropertyToID(
            "_EndfieldRecoveredDeferredResolverInputProbeReady");
        private static readonly int ExactDxbcBridgeConstantsId =
            Shader.PropertyToID("EndfieldCB6");
        private static readonly int ResolverT0Id =
            Shader.PropertyToID("_EndfieldRecoveredDeferredResolverT0");
        private static readonly int ResolverT1Id =
            Shader.PropertyToID("_EndfieldRecoveredDeferredResolverT1");
        private static readonly int ResolverT5Id =
            Shader.PropertyToID("_EndfieldRecoveredDeferredResolverT5");
        private static readonly int ResolverT6Id =
            Shader.PropertyToID("_EndfieldRecoveredDeferredResolverT6");
        private static readonly int ResolverT7Id =
            Shader.PropertyToID("_EndfieldRecoveredDeferredResolverT7");
        private static readonly int ResolverT11Id =
            Shader.PropertyToID("_EndfieldRecoveredDeferredResolverT11");
        private static readonly int CameraDepthSourceId =
            Shader.PropertyToID("_EndfieldRecoveredCameraDepthTexture");

        private readonly bool requested;
        private Material material;
        private RenderTexture output;
        private ComputeBuffer zeroHdplsBuffer;
        private int allocatedWidth;
        private int allocatedHeight;
        private bool activationLogged;
        private bool resourceSnapshotLogged;
        private bool failureLogged;
        private bool readbackRequested;
        private bool disposed;

        internal struct ResourceFrame
        {
            internal bool cameraDepthReady;
            internal RenderTexture t1CameraDepth;
            internal ComputeBuffer t0Binning;
            internal RenderTexture t5Reflection;
            internal RenderTexture t6PunctualShadow;
            internal uint t6PreparedSerial;
            internal RenderTexture t7LowResShadow;
            internal RenderTexture t11ScreenShadow;
            internal Texture2D t14LogSh;
            internal RenderTexture t15VisibilitySh;

            internal bool T1Ready =>
                cameraDepthReady;
            internal bool T1PhysicalReady =>
                t1CameraDepth != null && t1CameraDepth.IsCreated();
            internal bool T0Ready =>
                t0Binning != null && t0Binning.IsValid();
            internal bool T5Ready =>
                t5Reflection != null && t5Reflection.IsCreated();
            internal bool T6Ready =>
                t6PreparedSerial != 0 &&
                t6PunctualShadow != null && t6PunctualShadow.IsCreated();
            internal bool T7Ready =>
                t7LowResShadow != null && t7LowResShadow.IsCreated();
            internal bool T11Ready =>
                t11ScreenShadow != null && t11ScreenShadow.IsCreated();
            internal bool T14Ready =>
                t14LogSh != null && t14LogSh.GetNativeTexturePtr() != IntPtr.Zero;
            internal bool T15Ready =>
                t15VisibilitySh != null && t15VisibilitySh.IsCreated();

            internal bool AllPhysical =>
                T1PhysicalReady && T0Ready && T5Ready && T6Ready &&
                T7Ready && T11Ready;

            internal string BuildStatusToken()
            {
                return
                    $"t0={(T0Ready ? "ready" : "absent")}," +
                    $"t1={(T1PhysicalReady ? "ready" : T1Ready ? "nonphysical" : "absent")}," +
                    $"t5={(T5Ready ? "ready" : "absent")}," +
                    $"t6={(T6Ready ? "ready" : "absent")}," +
                    $"t7={(T7Ready ? "ready" : "absent")}," +
                    $"t11={(T11Ready ? "allocated" : "absent")}";
            }

            internal string BuildShapeToken(int width, int height)
            {
                return
                    $"t1={Describe(t1CameraDepth)}," +
                    $"t5={Describe(t5Reflection)}," +
                    $"t6={Describe(t6PunctualShadow)}," +
                    $"t7={Describe(t7LowResShadow)}," +
                    $"t11={Describe(t11ScreenShadow)}";
            }

            private static string Describe(RenderTexture texture)
            {
                if (texture == null || !texture.IsCreated())
                    return "none";
                int depth = texture.dimension == TextureDimension.Tex2DArray
                    ? texture.volumeDepth
                    : 1;
                return $"{texture.width}x{texture.height}x{depth}";
            }

            private static string Describe(Texture texture)
            {
                if (texture == null || texture.GetNativeTexturePtr() == IntPtr.Zero)
                    return "none";
                return $"{texture.width}x{texture.height}";
            }
        }

        internal static ResourceFrame CaptureResources(
            Camera camera,
            int width,
            int height,
            bool cameraDepthReady,
            RenderTexture cameraDepth,
            EndfieldRecoveredLightBinning lightBinning,
            EndfieldRecoveredReflectionProbeFallback reflection,
            EndfieldRecoveredPunctualShadowProducer punctual,
            uint expectedPunctualPreparedSerial,
            EndfieldRecoveredLowResDirectionalShadowProducer lowRes,
            EndfieldRecoveredScreenShadowMaskProducer screen,
            EndfieldRecoveredVisibilitySHProducer visibility)
        {
            ResourceFrame frame = new ResourceFrame
            {
                cameraDepthReady = cameraDepthReady,
                t1CameraDepth = cameraDepth
            };
            if (lightBinning != null)
            {
                lightBinning.TryGetCurrentCanonicalPublication(
                    camera,
                    width,
                    height,
                    out frame.t0Binning);
            }
            if (reflection != null)
            {
                reflection.TryGetCurrentPublication(
                    camera,
                    width,
                    height,
                    out frame.t5Reflection);
            }
            if (punctual != null)
            {
                punctual.TryGetCurrentPublication(
                    camera,
                    expectedPunctualPreparedSerial,
                    out Matrix4x4[] ignoredMatrices,
                    out Vector4[] ignoredParams,
                    out Vector4[] ignoredRects,
                    out Vector4 ignoredTexelSize,
                    out frame.t6PunctualShadow,
                    out string ignoredFailure);
                if (frame.t6PunctualShadow != null)
                    frame.t6PreparedSerial = expectedPunctualPreparedSerial;
            }
            if (lowRes != null)
            {
                lowRes.TryGetCurrentPublication(
                    camera,
                    width,
                    height,
                    out frame.t7LowResShadow);
            }
            if (screen != null)
            {
                screen.TryGetCurrentPublication(
                    camera,
                    width,
                    height,
                    out frame.t11ScreenShadow);
            }
            if (visibility != null)
            {
                visibility.TryGetCurrentPublication(
                    camera,
                    width,
                    height,
                    out frame.t14LogSh,
                    out frame.t15VisibilitySh,
                    out string ignoredFailure);
            }
            return frame;
        }

        internal EndfieldRecoveredDeferredResolverInputProbe()
        {
            requested = EndfieldRecoveredDeferredResolverBindingPolicy.IsRequested;
            Shader.SetGlobalFloat(ReadyId, 0.0f);
        }

        internal bool Requested => requested;

        internal bool Render(
            ScriptableRenderContext context,
            Camera camera,
            int width,
            int height,
            EndfieldRecoveredDeferredGBufferFrame gBufferFrame,
            bool gBufferReady,
            bool transformsReady,
            bool shaderVariablesReady,
            bool lightDataReady,
            bool shadowDataReady,
            ResourceFrame resourceFrame,
            RenderTargetIdentifier canonicalColorTarget,
            RenderTargetIdentifier canonicalDepthTarget)
        {
            if (!requested)
                return false;

            string failure;
            if (!gBufferReady)
            {
                failure = "same-frame deferred GBuffer sidecar is not ready";
                FailClosed(context, failure);
                return false;
            }
            if (!transformsReady || !shaderVariablesReady ||
                !lightDataReady || !shadowDataReady)
            {
                failure =
                    "selected b30/b35/b31/b34 inputs are not all ready: " +
                    $"b30={transformsReady}, b35={shaderVariablesReady}, " +
                    $"b31={lightDataReady}, b34={shadowDataReady}";
                FailClosed(context, failure);
                return false;
            }
            RenderTexture resolverT23 = null;
            RenderTexture resolverT24 = null;
            RenderTexture resolverT25 = null;
            uint resolverPublicationSerial = 0;
            if (camera == null)
            {
                failure = "resolver input probe received a null camera";
                FailClosed(context, failure);
                return false;
            }
            if (gBufferFrame == null)
            {
                failure = "resolver input probe received a null GBuffer frame";
                FailClosed(context, failure);
                return false;
            }
            if (!gBufferFrame.TryGetResolverInputs(
                    camera,
                    width,
                    height,
                    out resolverT23,
                    out resolverT24,
                    out resolverT25,
                    out resolverPublicationSerial,
                    out failure))
            {
                FailClosed(context, failure);
                return false;
            }
            if (!resourceFrame.T0Ready ||
                !resourceFrame.T1Ready ||
                !resourceFrame.T5Ready ||
                !resourceFrame.T6Ready)
            {
                failure =
                    "core resolver target resources are not all ready: " +
                    resourceFrame.BuildStatusToken();
                FailClosed(context, failure);
                return false;
            }
            if (EndfieldRecoveredDeferredResolverBindingPolicy
                    .IsResourceProbeRequested &&
                !resourceFrame.AllPhysical)
            {
                failure =
                    "strict resolver target-resource probe requires physical " +
                    "t0/t1/t5/t6/t7/t11 resources: " +
                    resourceFrame.BuildStatusToken();
                FailClosed(context, failure);
                return false;
            }
            if (!TryResolveMaterial(out failure) ||
                !TryEnsureOutput(width, height, out failure))
            {
                FailClosed(context, failure);
                return false;
            }

            var command = new CommandBuffer
            {
                name = "Recovered deferred resolver input probe"
            };
            try
            {
                EnsureZeroHdplsBuffer();
                command.SetGlobalConstantBuffer(
                    zeroHdplsBuffer,
                    ExactDxbcBridgeConstantsId,
                    0,
                    216 * sizeof(float) * 4);
                command.SetGlobalBuffer(ResolverT0Id, resourceFrame.t0Binning);
                command.SetGlobalTexture(
                    ResolverT1Id,
                    new RenderTargetIdentifier(CameraDepthSourceId));
                command.SetGlobalTexture(ResolverT5Id, resourceFrame.t5Reflection);
                command.SetGlobalTexture(ResolverT6Id, resourceFrame.t6PunctualShadow);
                command.SetGlobalTexture(
                    ResolverT7Id,
                    resourceFrame.T7Ready ? resourceFrame.t7LowResShadow : Texture2D.whiteTexture);
                command.SetGlobalTexture(
                    ResolverT11Id,
                    resourceFrame.T11Ready ? resourceFrame.t11ScreenShadow : Texture2D.whiteTexture);
                command.SetGlobalTexture(
                    EndfieldRecoveredDeferredGBufferFrame.ResolverGBufferT23Id,
                    resolverT23);
                command.SetGlobalTexture(
                    EndfieldRecoveredDeferredGBufferFrame.ResolverGBufferT24Id,
                    resolverT24);
                command.SetGlobalTexture(
                    EndfieldRecoveredDeferredGBufferFrame.ResolverGBufferT25Id,
                    resolverT25);
                command.SetGlobalTexture(
                    EndfieldRecoveredDeferredGBufferFrame.ResolverSourceTextureT23Id,
                    resolverT23);
                command.SetGlobalTexture(
                    EndfieldRecoveredDeferredGBufferFrame.ResolverSourceTextureT24Id,
                    resolverT24);
                command.SetGlobalTexture(
                    EndfieldRecoveredDeferredGBufferFrame.ResolverSourceTextureT25Id,
                    resolverT25);
                command.SetGlobalFloat(ReadyId, 0.0f);
                command.SetRenderTarget(output);
                command.ClearRenderTarget(false, true, Color.clear);
                command.SetViewport(new Rect(0.0f, 0.0f, width, height));
                command.DrawProcedural(
                    Matrix4x4.identity,
                    material,
                    0,
                    MeshTopology.Triangles,
                    3,
                    1);
                if (!readbackRequested && SystemInfo.supportsAsyncGPUReadback)
                {
                    readbackRequested = true;
                    string cameraName = camera.name;
                    command.RequestAsyncReadback(output, 0, request =>
                    {
                        if (request.hasError)
                        {
                            Debug.LogWarning(
                                "Recovered deferred resolver input probe GPU " +
                                "readback failed closed.");
                            return;
                        }
                        var data = request.GetData<byte>();
                        int nonzeroBytes = 0;
                        for (int index = 0; index < data.Length; index++)
                        {
                            if (data[index] != 0)
                                nonzeroBytes++;
                        }
                        Debug.Log(
                            "Recovered deferred resolver input probe readback: " +
                            $"camera={cameraName}, size={width}x{height}, " +
                            $"bytes={data.Length}, nonzeroBytes={nonzeroBytes}. " +
                            "This is input-order evidence, not retail lighting parity.");
                    });
                }
                command.SetGlobalFloat(ReadyId, 1.0f);
                command.SetRenderTarget(canonicalColorTarget, canonicalDepthTarget);
                command.SetViewport(new Rect(0.0f, 0.0f, width, height));
                context.ExecuteCommandBuffer(command);
            }
            catch (Exception exception)
            {
                failure = "resolver input probe submission failed: " + exception.Message;
                FailClosed(context, failure);
                return false;
            }
            finally
            {
                command.Release();
            }

            if (!activationLogged)
            {
                Debug.Log(
                    "Recovered deferred resolver input consumer probe active: " +
                    $"camera={camera.name}, size={width}x{height}, " +
                    $"publicationSerial={resolverPublicationSerial}, " +
                    "sourceIdentifiers=t23:_60,t24:_61,t25:_62, " +
                    "registerBridges=b0..b8, b6=zero-fallback, " +
                    "presented=false, retailPass0=false.");
                activationLogged = true;
            }
            if (!resourceSnapshotLogged)
            {
                Debug.Log(
                    "Recovered deferred resolver target-resource snapshot: " +
                    resourceFrame.BuildStatusToken() + ", " +
                    resourceFrame.BuildShapeToken(width, height) + ", " +
                    $"allPhysical={resourceFrame.AllPhysical.ToString().ToLowerInvariant()}, " +
                    "screenContentValid=false.");
                resourceSnapshotLogged = true;
            }
            failureLogged = false;
            return true;
        }

        public void Dispose()
        {
            if (disposed)
                return;
            disposed = true;
            Shader.SetGlobalFloat(ReadyId, 0.0f);
            if (zeroHdplsBuffer != null)
            {
                zeroHdplsBuffer.Release();
                zeroHdplsBuffer = null;
            }
            ReleaseOutput();
            if (material != null)
            {
                if (Application.isPlaying)
                    UnityEngine.Object.Destroy(material);
                else
                    UnityEngine.Object.DestroyImmediate(material);
                material = null;
            }
        }

        private bool TryResolveMaterial(out string failure)
        {
            failure = string.Empty;
            if (material != null)
                return true;
            Shader shader = Shader.Find(ShaderName);
            if (shader == null || !shader.isSupported)
            {
                failure = "deferred resolver input probe shader is unavailable";
                return false;
            }
            material = new Material(shader)
            {
                name = "Recovered deferred resolver input probe",
                hideFlags = HideFlags.HideAndDontSave,
            };
            return true;
        }

        private bool TryEnsureOutput(int width, int height, out string failure)
        {
            failure = string.Empty;
            if (width <= 0 || height <= 0)
            {
                failure = $"invalid resolver probe extent {width}x{height}";
                return false;
            }
            if (output != null && allocatedWidth == width &&
                allocatedHeight == height)
                return true;

            ReleaseOutput();
            if (!SystemInfo.IsFormatSupported(
                    GraphicsFormat.R32G32B32A32_SFloat,
                    FormatUsage.Render))
            {
                failure = "R32G32B32A32_SFloat probe target is unsupported";
                return false;
            }
            try
            {
                var descriptor = new RenderTextureDescriptor(width, height)
                {
                    graphicsFormat = GraphicsFormat.R32G32B32A32_SFloat,
                    depthStencilFormat = GraphicsFormat.None,
                    msaaSamples = 1,
                    bindMS = false,
                    dimension = TextureDimension.Tex2D,
                    useMipMap = false,
                    autoGenerateMips = false,
                    enableRandomWrite = false,
                    sRGB = false,
                };
                output = new RenderTexture(descriptor)
                {
                    name = "Recovered deferred resolver input probe output",
                    filterMode = FilterMode.Point,
                    wrapMode = TextureWrapMode.Clamp,
                    hideFlags = HideFlags.HideAndDontSave,
                };
                if (!output.Create())
                {
                    failure = "resolver input probe target creation failed";
                    ReleaseOutput();
                    return false;
                }
                allocatedWidth = width;
                allocatedHeight = height;
                return true;
            }
            catch (Exception exception)
            {
                failure = "resolver input probe target allocation failed: " +
                    exception.Message;
                ReleaseOutput();
                return false;
            }
        }

        private void EnsureZeroHdplsBuffer()
        {
            if (zeroHdplsBuffer != null)
                return;
            zeroHdplsBuffer = new ComputeBuffer(
                216,
                sizeof(float) * 4,
                ComputeBufferType.Constant)
            {
                name = "Recovered deferred resolver b6 zero fallback"
            };
            zeroHdplsBuffer.SetData(new Vector4[216]);
        }

        private void FailClosed(ScriptableRenderContext context, string failure)
        {
            Shader.SetGlobalFloat(ReadyId, 0.0f);
            if (!failureLogged)
            {
                Debug.LogWarning(
                    "Recovered deferred resolver input probe failed closed: " +
                    failure + ".");
                failureLogged = true;
            }
        }

        private void ReleaseOutput()
        {
            if (output == null)
                return;
            if (output.IsCreated())
                output.Release();
            if (Application.isPlaying)
                UnityEngine.Object.Destroy(output);
            else
                UnityEngine.Object.DestroyImmediate(output);
            output = null;
            allocatedWidth = 0;
            allocatedHeight = 0;
        }
    }
}
