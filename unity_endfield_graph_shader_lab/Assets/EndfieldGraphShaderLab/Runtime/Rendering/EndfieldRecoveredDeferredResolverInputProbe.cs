using System;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Default-off, non-presented consumer probe for the source-closed
    /// deferred resolver input boundary. It reads the exact _62/_61/_60
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

        private readonly bool requested;
        private Material material;
        private RenderTexture output;
        private ComputeBuffer zeroHdplsBuffer;
        private int allocatedWidth;
        private int allocatedHeight;
        private bool activationLogged;
        private bool failureLogged;
        private bool readbackRequested;
        private bool disposed;

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
            if (camera == null || gBufferFrame == null ||
                !gBufferFrame.TryGetResolverInputs(
                    out RenderTexture resolverT23,
                    out RenderTexture resolverT24,
                    out RenderTexture resolverT25))
            {
                failure = "same-frame C/B/A resolver textures are unavailable";
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
                    "sourceIdentifiers=t23:_62,t24:_61,t25:_60, " +
                    "registerBridges=b0..b8, b6=zero-fallback, " +
                    "presented=false, retailPass0=false.");
                activationLogged = true;
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
