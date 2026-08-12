using System;
using System.Runtime.InteropServices;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Default-off, non-presented bridge that executes the selected original
    /// deferred-resolver DXBC against the current recovered frame resources.
    /// It is deliberately a D3D11-only diagnostic: no retail target is
    /// replaced, and failure to prove every source pointer fails closed.
    /// </summary>
    internal sealed class EndfieldRecoveredDeferredExactConsumer : IDisposable
    {
        private const string NativeLibrary = "OriginalDxbcSwapPlugin";
        private const string ShaderName =
            EndfieldOriginalDxbcDiagnosticRuntime.ShaderName;
        private const int TextureSlotCount = 26;
        private static readonly int BufferT0Id =
            Shader.PropertyToID("_EndfieldBufferT0");
        private static readonly int CameraDepthId =
            Shader.PropertyToID("_EndfieldRecoveredCameraDepthTexture");
        private static readonly int[] TextureIds = CreateTextureIds();

        private readonly bool requested;
        private Material material;
        private RenderTexture output;
        private Texture2D fallback2D;
        private Texture2DArray fallbackArray;
        private Texture3D fallback3D;
        private int allocatedWidth;
        private int allocatedHeight;
        private bool loggedFailure;
        private bool readbackRequested;
        private bool nativeEventPending;
        private bool disposed;

        internal EndfieldRecoveredDeferredExactConsumer()
        {
            requested =
                EndfieldRecoveredDeferredResolverBindingPolicy
                    .IsExactConsumerRequested;
        }

        internal bool Requested => requested;

        internal bool Render(
            ScriptableRenderContext context,
            Camera camera,
            int width,
            int height,
            EndfieldRecoveredDeferredGBufferFrame gBufferFrame,
            EndfieldRecoveredDeferredResolverInputProbe.ResourceFrame resources,
            RenderTargetIdentifier canonicalColorTarget,
            RenderTargetIdentifier canonicalDepthTarget)
        {
            if (!requested)
                return false;
            if (nativeEventPending)
            {
                try
                {
                    if (Native.GetDiagnosticArmed() != 0)
                        return FailClosed(
                            "previous exact consumer render event is still pending");
                    nativeEventPending = false;
                }
                catch (Exception exception)
                {
                    return FailClosed(
                        "previous exact consumer event state is unavailable: " +
                        exception.Message);
                }
            }
            if (SystemInfo.graphicsDeviceType != GraphicsDeviceType.Direct3D11)
            {
                return FailClosed(
                    "exact original deferred DXBC consumer requires Direct3D11");
            }
            if (camera == null || gBufferFrame == null)
                return FailClosed("exact consumer received no camera or GBuffer frame");
            if (!resources.AllPhysical)
                return FailClosed(
                    "exact consumer requires physical t0/t1/t5/t6/t7/t22 resources: " +
                    resources.BuildStatusToken());
            if (!gBufferFrame.TryGetResolverInputs(
                    camera,
                    width,
                    height,
                    out RenderTexture resolverT23,
                    out RenderTexture resolverT24,
                    out RenderTexture resolverT25,
                    out uint publicationSerial,
                    out string gBufferFailure))
            {
                return FailClosed(gBufferFailure);
            }
            Texture cameraDepth = Shader.GetGlobalTexture(CameraDepthId);
            if (!IsCreated(cameraDepth))
                return FailClosed("same-frame camera depth texture is unavailable");
            string materialFailure = string.Empty;
            string fallbackFailure = string.Empty;
            string outputFailure = string.Empty;
            if (!TryResolveMaterial(out materialFailure) ||
                !TryEnsureFallbacks(out fallbackFailure) ||
                !TryEnsureOutput(width, height, out outputFailure))
            {
                return FailClosed(
                    materialFailure + fallbackFailure + outputFailure);
            }

            ulong[] pointers = new ulong[TextureSlotCount];
            CommandBuffer command = new CommandBuffer
            {
                name = "Recovered exact deferred resolver consumer"
            };
            bool armed = false;
            bool eventQueued = false;
            try
            {
                if (!TryArmNative(out string nativeFailure))
                    return FailClosed(nativeFailure);
                armed = true;

                command.SetGlobalBuffer(BufferT0Id, resources.t0Binning);
                pointers[0] = NativeBufferPointer(resources.t0Binning);
                for (int slot = 1; slot < TextureSlotCount; slot++)
                {
                    Texture texture = SelectTexture(
                        slot,
                        cameraDepth,
                        resources,
                        resolverT23,
                        resolverT24,
                        resolverT25);
                    if (!IsCreated(texture))
                        return FailClosed(
                            "exact consumer texture t" + slot + " is unavailable");
                    command.SetGlobalTexture(TextureIds[slot], texture);
                    pointers[slot] = NativeTexturePointer(texture);
                    if (pointers[slot] == 0)
                        return FailClosed(
                            "exact consumer native texture pointer t" + slot +
                            " is unavailable");
                }
                if (pointers[0] == 0)
                    return FailClosed("exact consumer native t0 buffer pointer is unavailable");

                Native.SetDiagnosticTexturePointers(pointers, TextureSlotCount);
                command.SetRenderTarget(output);
                command.ClearRenderTarget(false, true, Color.clear);
                command.SetViewport(new Rect(0.0f, 0.0f, width, height));
                // The shell establishes Unity's b0..b8 and sampler metadata;
                // the native event replaces only the shader stages and draws
                // the embedded exact DXBC after all source pointers are set.
                command.DrawProcedural(
                    Matrix4x4.identity,
                    material,
                    0,
                    MeshTopology.Triangles,
                    3,
                    1);
                IntPtr renderEvent = Native.GetRenderEventFunc();
                if (renderEvent == IntPtr.Zero)
                    return FailClosed("exact consumer native render event is unavailable");
                command.IssuePluginEvent(renderEvent, 0);
                RequestReadback(command, camera.name, width, height);
                // The native event clears armed state and pointer ownership on
                // the render thread after the exact draw/readback copy. Do not
                // clear those pointers from this C# finally block while SRP
                // may still be submitting the command buffer.
                command.IssuePluginEvent(renderEvent, 2);
                eventQueued = true;
                nativeEventPending = true;
                command.SetRenderTarget(
                    canonicalColorTarget,
                    canonicalDepthTarget);
                command.SetViewport(new Rect(0.0f, 0.0f, width, height));
                context.ExecuteCommandBuffer(command);

                uint failureCount = Native.GetFailureCount();
                uint exactBound = Native.GetExactShaderBound();
                uint resourceMask = Native.GetShaderResourceMask();
                uint resourceFailureMask = Native.GetShaderResourceFailureMask();
                Debug.Log(
                    "Recovered exact deferred resolver consumer submitted: " +
                    $"camera={camera.name}, size={width}x{height}, " +
                    $"publicationSerial={publicationSerial}, " +
                    $"exactBound={exactBound}, " +
                    $"resourceMask=0x{resourceMask:x}, " +
                    $"resourceFailureMask=0x{resourceFailureMask:x}, " +
                    $"resourceFailureResults={FormatResourceFailures()}, " +
                    $"failureCount={failureCount}, presented=false, " +
                    "retailPass0=false, screenContentValid=false.");
                loggedFailure = false;
                return true;
            }
            catch (Exception exception)
            {
                return FailClosed("exact consumer submission failed: " + exception.Message);
            }
            finally
            {
                if (!eventQueued)
                {
                    Native.SetDiagnosticTexturePointers(null, 0);
                    if (armed)
                        Native.SetDiagnosticArmed(0);
                }
                command.Release();
            }
        }

        public void Dispose()
        {
            if (disposed)
                return;
            disposed = true;
            try
            {
                Native.SetDiagnosticTexturePointers(null, 0);
                Native.SetDiagnosticArmed(0);
            }
            catch
            {
                // Native plugin may already be unloaded during editor shutdown.
            }
            ReleaseOutput();
            DisposeUnityObject(fallback2D);
            DisposeUnityObject(fallbackArray);
            DisposeUnityObject(fallback3D);
            DisposeUnityObject(material);
            fallback2D = null;
            fallbackArray = null;
            fallback3D = null;
            material = null;
        }

        private bool TryArmNative(out string failure)
        {
            failure = string.Empty;
            try
            {
                if (Native.GetContractVersion() != 1)
                {
                    failure = "exact consumer native contract version is unsupported";
                    return false;
                }
                if (Native.GetPluginLoadCount() == 0 ||
                    Native.GetConfigureCount() == 0)
                {
                    failure = "exact consumer native plugin is not configured";
                    return false;
                }
                if (Native.GetDiagnosticArmed() != 0)
                {
                    failure = "exact consumer native plugin was already armed";
                    return false;
                }
                if (Native.SetDiagnosticArmed(1) != 1)
                {
                    failure = "exact consumer native arm request failed";
                    return false;
                }
                return true;
            }
            catch (Exception exception)
            {
                failure = "exact consumer native plugin unavailable: " +
                    exception.Message;
                return false;
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
                failure = "exact deferred DXBC shell shader is unavailable; ";
                return false;
            }
            material = new Material(shader)
            {
                name = "Recovered exact deferred resolver shell",
                hideFlags = HideFlags.HideAndDontSave,
            };
            return true;
        }

        private bool TryEnsureFallbacks(out string failure)
        {
            failure = string.Empty;
            try
            {
                if (fallback2D == null)
                {
                    fallback2D = new Texture2D(
                        1,
                        1,
                        TextureFormat.RGBAFloat,
                        false,
                        true)
                    {
                        name = "Recovered exact resolver 2D fallback",
                        filterMode = FilterMode.Point,
                        wrapMode = TextureWrapMode.Clamp,
                        hideFlags = HideFlags.HideAndDontSave,
                    };
                    fallback2D.SetPixel(0, 0, Color.clear);
                    fallback2D.Apply(false, true);
                }
                if (fallbackArray == null)
                {
                    fallbackArray = new Texture2DArray(
                        1,
                        1,
                        1,
                        TextureFormat.RGBAFloat,
                        false,
                        true)
                    {
                        name = "Recovered exact resolver array fallback",
                        filterMode = FilterMode.Point,
                        wrapMode = TextureWrapMode.Clamp,
                        hideFlags = HideFlags.HideAndDontSave,
                    };
                    fallbackArray.SetPixels(new[] { Color.clear }, 0, 0);
                    fallbackArray.Apply(false, true);
                }
                if (fallback3D == null)
                {
                    fallback3D = new Texture3D(
                        1,
                        1,
                        1,
                        TextureFormat.RGBAFloat,
                        false)
                    {
                        name = "Recovered exact resolver 3D fallback",
                        filterMode = FilterMode.Point,
                        wrapMode = TextureWrapMode.Clamp,
                        hideFlags = HideFlags.HideAndDontSave,
                    };
                    fallback3D.SetPixels(new[] { Color.clear });
                    fallback3D.Apply(false, true);
                }
                return true;
            }
            catch (Exception exception)
            {
                failure = "exact resolver fallback allocation failed: " +
                    exception.Message + "; ";
                return false;
            }
        }

        private bool TryEnsureOutput(int width, int height, out string failure)
        {
            failure = string.Empty;
            if (output != null && allocatedWidth == width &&
                allocatedHeight == height)
                return true;
            ReleaseOutput();
            if (!SystemInfo.IsFormatSupported(
                    GraphicsFormat.R32G32B32A32_SFloat,
                    FormatUsage.Render))
            {
                failure = "exact resolver output format is unsupported; ";
                return false;
            }
            try
            {
                output = new RenderTexture(new RenderTextureDescriptor(width, height)
                {
                    graphicsFormat = GraphicsFormat.R32G32B32A32_SFloat,
                    depthStencilFormat = GraphicsFormat.None,
                    dimension = TextureDimension.Tex2D,
                    msaaSamples = 1,
                    useMipMap = false,
                    autoGenerateMips = false,
                    enableRandomWrite = false,
                    sRGB = false,
                })
                {
                    name = "Recovered exact deferred resolver output",
                    filterMode = FilterMode.Point,
                    wrapMode = TextureWrapMode.Clamp,
                    hideFlags = HideFlags.HideAndDontSave,
                };
                if (!output.Create())
                {
                    failure = "exact resolver output creation failed; ";
                    ReleaseOutput();
                    return false;
                }
                allocatedWidth = width;
                allocatedHeight = height;
                return true;
            }
            catch (Exception exception)
            {
                failure = "exact resolver output allocation failed: " +
                    exception.Message + "; ";
                ReleaseOutput();
                return false;
            }
        }

        private void RequestReadback(
            CommandBuffer command,
            string cameraName,
            int width,
            int height)
        {
            if (readbackRequested || !SystemInfo.supportsAsyncGPUReadback)
                return;
            readbackRequested = true;
            command.RequestAsyncReadback(output, 0, request =>
            {
                if (request.hasError)
                {
                    Debug.LogWarning(
                        "Recovered exact deferred resolver consumer readback failed closed.");
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
                    "Recovered exact deferred resolver consumer readback: " +
                    $"camera={cameraName}, size={width}x{height}, " +
                    $"bytes={data.Length}, nonzeroBytes={nonzeroBytes}, " +
                    $"exactBound={Native.GetExactShaderBound()}, " +
                    $"resourceMask=0x{Native.GetShaderResourceMask():x}, " +
                    $"resourceFailureMask=0x{Native.GetShaderResourceFailureMask():x}, " +
                    $"resourceFailureResults={FormatResourceFailures()}, " +
                    $"failureCount={Native.GetFailureCount()}, " +
                    "presented=false, retailPass0=false.");
            });
        }

        private bool FailClosed(string failure)
        {
            if (!loggedFailure)
            {
                Debug.LogWarning(
                    "Recovered exact deferred resolver consumer failed closed: " +
                    failure + ".");
                loggedFailure = true;
            }
            return false;
        }

        private static string FormatResourceFailures()
        {
            var values = new System.Text.StringBuilder();
            for (int slot = 0; slot < TextureSlotCount; slot++)
            {
                int result = Native.GetShaderResourceFailureResult((uint)slot);
                if (result == 0)
                    continue;
                if (values.Length != 0)
                    values.Append(';');
                values.Append('t');
                values.Append(slot);
                values.Append("=0x");
                values.Append(result.ToString("x8"));
            }
            return values.Length == 0 ? "none" : values.ToString();
        }

        private Texture SelectTexture(
            int slot,
            Texture cameraDepth,
            EndfieldRecoveredDeferredResolverInputProbe.ResourceFrame resources,
            RenderTexture resolverT23,
            RenderTexture resolverT24,
            RenderTexture resolverT25)
        {
            switch (slot)
            {
                case 1: return cameraDepth;
                case 5: return resources.t5Reflection;
                case 6: return resources.t6PunctualShadow;
                case 7: return resources.t7LowResShadow;
                case 22: return resources.t22ScreenShadow;
                case 23: return resolverT23;
                case 24: return resolverT24;
                case 25: return resolverT25;
                case 13:
                case 16:
                case 17:
                case 18:
                case 19:
                case 20:
                case 21:
                    return fallback3D;
                default:
                    return fallback2D;
            }
        }

        private static int[] CreateTextureIds()
        {
            var ids = new int[TextureSlotCount];
            for (int slot = 1; slot < TextureSlotCount; slot++)
                ids[slot] = Shader.PropertyToID("_EndfieldTextureT" + slot);
            return ids;
        }

        private static bool IsCreated(Texture texture)
        {
            if (texture == null)
                return false;
            if (texture is RenderTexture renderTexture)
                return renderTexture.IsCreated();
            return texture.GetNativeTexturePtr() != IntPtr.Zero;
        }

        private static ulong NativeTexturePointer(Texture texture)
        {
            return texture == null
                ? 0ul
                : unchecked((ulong)texture.GetNativeTexturePtr().ToInt64());
        }

        private static ulong NativeBufferPointer(ComputeBuffer buffer)
        {
            return buffer == null
                ? 0ul
                : unchecked((ulong)buffer.GetNativeBufferPtr().ToInt64());
        }

        private void ReleaseOutput()
        {
            if (output == null)
                return;
            if (output.IsCreated())
                output.Release();
            DisposeUnityObject(output);
            output = null;
            allocatedWidth = 0;
            allocatedHeight = 0;
        }

        private static void DisposeUnityObject(UnityEngine.Object value)
        {
            if (value == null)
                return;
            if (Application.isPlaying)
                UnityEngine.Object.Destroy(value);
            else
                UnityEngine.Object.DestroyImmediate(value);
        }

        private static class Native
        {
            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetContractVersion")]
            internal static extern uint GetContractVersion();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetPluginLoadCount")]
            internal static extern uint GetPluginLoadCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetConfigureCount")]
            internal static extern uint GetConfigureCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcSetDiagnosticArmed")]
            internal static extern uint SetDiagnosticArmed(uint armed);

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcSetDiagnosticTexturePointers")]
            internal static extern void SetDiagnosticTexturePointers(
                [In] ulong[] texturePointers,
                uint count);

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetDiagnosticArmed")]
            internal static extern uint GetDiagnosticArmed();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetFailureCount")]
            internal static extern uint GetFailureCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetShaderResourceMask")]
            internal static extern uint GetShaderResourceMask();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetShaderResourceFailureMask")]
            internal static extern uint GetShaderResourceFailureMask();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetShaderResourceFailureResult")]
            internal static extern int GetShaderResourceFailureResult(uint slot);

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetExactShaderBound")]
            internal static extern uint GetExactShaderBound();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetRenderEventFunc")]
            internal static extern IntPtr GetRenderEventFunc();
        }
    }
}
