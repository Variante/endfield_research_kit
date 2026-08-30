using System;
using System.Globalization;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using Unity.Collections;
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
        private const int ConstantBufferSlotCount = 9;
        private const int LegacyHlslTextureSlotCount = 28;
        private const int LegacyHlslConstantBufferSlotCount = 10;
        private static readonly int[] ConstantBufferIds = CreateConstantBufferIds();
        private static readonly int[] ConstantBufferByteCounts =
        {
            45 * sizeof(float) * 4,
            157 * sizeof(float) * 4,
            259 * sizeof(float) * 4,
            3 * sizeof(float) * 4,
            2054 * sizeof(float) * 4,
            401 * sizeof(float) * 4,
            216 * sizeof(float) * 4,
            160 * sizeof(float) * 4,
            4 * sizeof(float) * 4,
        };
        private static readonly int BufferT0Id =
            Shader.PropertyToID("_EndfieldBufferT0");
        private static readonly int ReadyId =
            Shader.PropertyToID("_EndfieldRecoveredDeferredExactConsumerReady");
        private static readonly int[] TextureIds = CreateTextureIds();
        private static readonly int[] LegacyHlslTextureIds =
            CreateTextureIds(LegacyHlslTextureSlotCount);
        private static readonly int[] LegacyHlslConstantBufferIds =
            CreateConstantBufferIds(LegacyHlslConstantBufferSlotCount);

        private readonly bool requested;
        private Material material;
        private Material recoveredHlslMaterial;
        private RenderTexture output;
        private RenderTexture recoveredHlslOutput;
        private Texture2D fallback2D;
        private Texture2DArray fallbackArray;
        private Texture3D fallback3D;
        private Texture3D integratedFogFallback;
        private Texture2D multiscatteringLut;
        private ComputeBuffer zeroHdplsBuffer;
        private ComputeBuffer zeroSubsurfaceProfileBuffer;
        private int allocatedWidth;
        private int allocatedHeight;
        private bool loggedFailure;
        private string lastFailure = string.Empty;
        private bool readbackRequested;
        private bool recoveredHlslReadbackRequested;
        private float[] exactReadbackFloats;
        private float[] recoveredHlslReadbackFloats;
        private bool comparisonLogged;
        private bool exactContentValidationComplete;
        private bool exactContentValid;
        private int contentValidationGeneration = 1;
        private ulong nativePendingSubmissionSerial;
        private bool disposed;

        internal EndfieldRecoveredDeferredExactConsumer()
        {
            requested =
                EndfieldRecoveredDeferredResolverBindingPolicy
                    .IsExactConsumerRequested;
            Shader.SetGlobalFloat(ReadyId, 0.0f);
        }

        internal bool Requested => requested;

        internal RenderTexture ExactOutput => output;

        internal bool PresentationReady =>
            exactContentValidationComplete && exactContentValid &&
            output != null && output.IsCreated();

        internal void SuppressInactiveFrame()
        {
            // Presentation authority belongs to one continuous source-owner
            // interval. Never carry an asynchronous positive content result
            // across an inactive gap, where the private depth/output belong
            // to an earlier effect frame.
            InvalidateContentValidation();
            Shader.SetGlobalFloat(ReadyId, 0.0f);
        }

        internal bool Render(
            ScriptableRenderContext context,
            Camera camera,
            int width,
            int height,
            EndfieldRecoveredDeferredGBufferFrame gBufferFrame,
            EndfieldRecoveredDeferredResolverInputProbe.ResourceFrame resources,
            EndfieldRecoveredDeferredTransformVariables transformVariables,
            EndfieldRecoveredShaderVariablesGlobal shaderVariablesGlobal,
            EndfieldRecoveredReflectionProbeFallback reflectionProbeFallback,
            EndfieldRecoveredLightBinning lightBinning,
            EndfieldRecoveredVisibilitySHConstants visibilitySHConstants,
            EndfieldRecoveredDeferredLightData selectedLightData,
            EndfieldRecoveredEndminfFullDeferredLightData fullEndminfLightData,
            bool useFullEndminfLightData,
            EndfieldRecoveredDeferredShadowData shadowData,
            bool transformsReady,
            bool shaderVariablesReady,
            bool lightDataReady,
            bool shadowDataReady,
            RenderTargetIdentifier canonicalColorTarget,
            RenderTargetIdentifier canonicalDepthTarget)
        {
            Shader.SetGlobalFloat(ReadyId, 0.0f);
            if (!requested)
                return false;
            if (nativePendingSubmissionSerial != 0)
            {
                try
                {
                    ulong completedSerial =
                        Native.GetCompletedDiagnosticSubmissionSerial();
                    if (completedSerial < nativePendingSubmissionSerial)
                        return FailClosed(
                            "previous exact consumer render submission is still pending: " +
                            $"submitted={nativePendingSubmissionSerial}," +
                            $"completed={completedSerial}");
                    nativePendingSubmissionSerial = 0;
                }
                catch (Exception exception)
                {
                    return FailClosed(
                        "previous exact consumer submission state is unavailable: " +
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
                    $"exact consumer camera={camera.name} requires physical " +
                    "t0/t1/t5/t6/t7/t11 resources: " +
                    resources.BuildStatusToken());
            if (!resources.T14Ready || !resources.T15Ready)
                return FailClosed(
                    "exact retail consumer requires source-backed t16 LogSH and t17 " +
                    "VisibilitySH publications: " + resources.BuildStatusToken() +
                    $",t16={(resources.T14Ready ? "ready" : "absent")}," +
                    $"t17={(resources.T15Ready ? "ready" : "absent")}");
            if (!transformsReady || !shaderVariablesReady ||
                !lightDataReady || !shadowDataReady)
            {
                return FailClosed(
                    "exact consumer constant-buffer prerequisites are not ready: " +
                    $"b0={transformsReady}, b1={shaderVariablesReady}, " +
                    $"b4={lightDataReady}, b5={shadowDataReady}");
            }
            EnsureZeroHdplsBuffer();
            EnsureZeroSubsurfaceProfileBuffer();
            if (!TryBuildConstantBuffers(
                    camera,
                    width,
                    height,
                    transformVariables,
                    shaderVariablesGlobal,
                    reflectionProbeFallback,
                    lightBinning,
                    visibilitySHConstants,
                    selectedLightData,
                    fullEndminfLightData,
                    useFullEndminfLightData,
                    resources,
                    shadowData,
                    out ComputeBuffer[] constantBuffers,
                    out string constantBufferFailure))
            {
                return FailClosed(constantBufferFailure);
            }
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
            // A/B/C are produced in the isolated five-target sidecar, so t1
            // must come from that same publication.  Canonical camera depth
            // does not contain sidecar-only owners such as Endminf M27 and
            // would reconstruct unrelated world positions for their pixels.
            if (!gBufferFrame.TryGetResolverDepth(
                    camera,
                    width,
                    height,
                    out RenderTexture resolverDepth,
                    out string resolverDepthFailure))
            {
                return FailClosed(resolverDepthFailure);
            }
            Texture cameraDepth = resolverDepth;
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
            ulong[] retainedResourcePointers = new ulong[
                TextureSlotCount + ConstantBufferSlotCount + 2];
            CommandBuffer command = new CommandBuffer
            {
                name = "Recovered exact deferred resolver consumer"
            };
            bool eventQueued = false;
            ulong submissionSerial = 0;
            try
            {
                if (!TryPrepareNative(out string nativeFailure))
                    return FailClosed(nativeFailure);

                BindLegacyHlslInputs(
                    constantBuffers,
                    resources,
                    cameraDepth,
                    resolverT23,
                    resolverT24,
                    resolverT25);

                for (int slot = 0; slot < ConstantBufferSlotCount; slot++)
                {
                    command.SetGlobalConstantBuffer(
                        constantBuffers[slot],
                        ConstantBufferIds[slot],
                        0,
                        ConstantBufferByteCounts[slot]);
                }
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

                Array.Copy(
                    pointers,
                    0,
                    retainedResourcePointers,
                    0,
                    TextureSlotCount);
                for (int slot = 0; slot < ConstantBufferSlotCount; slot++)
                {
                    retainedResourcePointers[TextureSlotCount + slot] =
                        NativeBufferPointer(constantBuffers[slot]);
                }
                retainedResourcePointers[
                    TextureSlotCount + ConstantBufferSlotCount] =
                    NativeTexturePointer(output);
                retainedResourcePointers[
                    TextureSlotCount + ConstantBufferSlotCount + 1] =
                    NativeTexturePointer(recoveredHlslOutput);
                for (int index = 0; index < retainedResourcePointers.Length; index++)
                {
                    if (retainedResourcePointers[index] == 0)
                    {
                        return FailClosed(
                            "exact consumer retained native resource pointer " +
                            index + " is unavailable");
                    }
                }
                submissionSerial = Native.BeginDiagnosticSubmission(
                    pointers,
                    TextureSlotCount,
                    retainedResourcePointers,
                    checked((uint)retainedResourcePointers.Length));
                if (submissionSerial == 0)
                {
                    return FailClosed(
                        "exact consumer native submission was rejected because " +
                        "another submission owns the resource lifetime");
                }
                command.SetRenderTarget(recoveredHlslOutput);
                command.ClearRenderTarget(false, true, Color.clear);
                command.SetViewport(new Rect(0.0f, 0.0f, width, height));
                command.DrawProcedural(
                    Matrix4x4.identity,
                    recoveredHlslMaterial,
                    0,
                    MeshTopology.Triangles,
                    3,
                    1);
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
                // Keep the shell draw disarmed so Unity's own SRVs are bound
                // from the shell reflection metadata. Event 3 arms the
                // native exact draw only after that shell draw completes.
                command.IssuePluginEvent(renderEvent, 3);
                command.IssuePluginEvent(renderEvent, 0);
                RequestReadback(
                    command,
                    camera.name,
                    width,
                    height,
                    resources.t11ContentValid);
                RequestRecoveredHlslReadback(
                    command, camera.name, width, height);
                command.IssuePluginEvent(renderEvent, 1);
                // The native event clears armed state and pointer ownership on
                // the render thread after the exact draw/readback copy. Do not
                // clear those pointers from this C# finally block while SRP
                // may still be submitting the command buffer.
                command.IssuePluginEvent(renderEvent, 2);
                eventQueued = true;
                nativePendingSubmissionSerial = submissionSerial;
                command.SetRenderTarget(
                    canonicalColorTarget,
                    canonicalDepthTarget);
                command.SetViewport(new Rect(0.0f, 0.0f, width, height));
                context.ExecuteCommandBuffer(command);

                uint failureCount = Native.GetFailureCount();
                uint exactBound = Native.GetExactShaderBound();
                uint resourceMask = Native.GetShaderResourceMask();
                uint resourceFailureMask = Native.GetShaderResourceFailureMask();
                uint constantBufferMask = Native.GetConstantBufferMask();
                Debug.Log(
                    "Recovered exact deferred resolver consumer submitted: " +
                    $"camera={camera.name}, size={width}x{height}, " +
                    $"publicationSerial={publicationSerial}, " +
                    $"nativeSubmissionSerial={submissionSerial}, " +
                    $"exactBound={exactBound}, " +
                    $"resourceMask=0x{resourceMask:x}, " +
                    $"resourceFailureMask=0x{resourceFailureMask:x}, " +
                    $"resourceFailureResults={FormatResourceFailures()}, " +
                    $"constantBufferMask=0x{constantBufferMask:x}, " +
                    $"failureCount={failureCount}, presented=false, " +
                    "retailPass0=false, screenContentValid=false.");
                Debug.Log(
                    "Recovered exact deferred resolver source texture closures: " +
                    "variant=live-b21a1e35eda1c5bc," +
                    "b6=HDPLS:zero-local-fallback," +
                    "t8=HDPLS:white-inactive-fallback," +
                    "t9=CSMRamp:black-null-fallback," +
                    $"t10=multiscattering:{(multiscatteringLut != null ? "ready" : "absent")}," +
                    $"t11=screenShadow:{(resources.T11Ready ? "ready" : "absent")}:" +
                    $"contentValid={resources.t11ContentValid.ToString().ToLowerInvariant()}," +
                    "t12=LightCookie:black-zero-cookie," +
                    "t13=IntegratedFog:black-disabled-1x1-ASTC," +
                    $"t14=LogSH:{(resources.T14Ready ? "ready" : "absent")}," +
                    $"t15=VisibilitySH:{(resources.T15Ready ? "ready" : "absent")}," +
                    "t16-t21=IrradianceV2:zero-inactive-fallback," +
                    "t22=wetness:white-disabled-fallback," +
                    "t23-t25=GBuffer:A/B/C," +
                    "fallbackTextureSlots=t2,t3,t4.");
                loggedFailure = false;
                lastFailure = string.Empty;
                Shader.SetGlobalFloat(ReadyId, 1.0f);
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
                    try
                    {
                        if (submissionSerial != 0 &&
                            Native.CancelDiagnosticSubmission(submissionSerial) == 0)
                        {
                            Debug.LogError(
                                "Exact consumer could not cancel an unqueued native " +
                                $"submission: serial={submissionSerial}.");
                        }
                    }
                    catch (Exception exception)
                    {
                        Debug.LogError(
                            "Exact consumer unqueued-submission cancellation " +
                            "failed; native unload remains the final ownership " +
                            "boundary: " + exception.Message);
                    }
                }
                command.Release();
            }
        }

        public void Dispose()
        {
            if (disposed)
                return;
            disposed = true;
            Shader.SetGlobalFloat(ReadyId, 0.0f);
            if (nativePendingSubmissionSerial != 0)
            {
                try
                {
                    ulong completedSerial =
                        Native.GetCompletedDiagnosticSubmissionSerial();
                    if (completedSerial < nativePendingSubmissionSerial)
                    {
                        // BeginDiagnosticSubmission AddRefs every D3D11 resource
                        // used by the queued draw/readbacks. Event 2 releases
                        // that ownership and publishes completion. Never clear
                        // or cancel here: Dispose can run before event 3 starts.
                        Debug.LogWarning(
                            "Exact consumer disposed with a native submission " +
                            "still queued; native event 2 retains its D3D11 " +
                            $"resources safely: submitted={nativePendingSubmissionSerial}," +
                            $"completed={completedSerial}.");
                    }
                    else
                    {
                        nativePendingSubmissionSerial = 0;
                    }
                }
                catch (Exception exception)
                {
                    // Do not mutate native pointer/armed state during shutdown.
                    // The plugin owns retained COM references until event 2 or
                    // UnityPluginUnload abandons the pending submission.
                    Debug.LogWarning(
                        "Exact consumer could not query native completion during " +
                        "shutdown; retained resources remain native-owned: " +
                        exception.Message);
                }
            }
            ReleaseOutput();
            DisposeUnityObject(fallback2D);
            DisposeUnityObject(fallbackArray);
            DisposeUnityObject(fallback3D);
            DisposeUnityObject(integratedFogFallback);
            DisposeUnityObject(multiscatteringLut);
            DisposeUnityObject(material);
            DisposeUnityObject(recoveredHlslMaterial);
            if (zeroHdplsBuffer != null)
            {
                zeroHdplsBuffer.Release();
                zeroHdplsBuffer = null;
            }
            if (zeroSubsurfaceProfileBuffer != null)
            {
                zeroSubsurfaceProfileBuffer.Release();
                zeroSubsurfaceProfileBuffer = null;
            }
            fallback2D = null;
            fallbackArray = null;
            fallback3D = null;
            integratedFogFallback = null;
            multiscatteringLut = null;
            material = null;
            recoveredHlslMaterial = null;
        }

        private bool TryBuildConstantBuffers(
            Camera camera,
            int width,
            int height,
            EndfieldRecoveredDeferredTransformVariables transformVariables,
            EndfieldRecoveredShaderVariablesGlobal shaderVariablesGlobal,
            EndfieldRecoveredReflectionProbeFallback reflectionProbeFallback,
            EndfieldRecoveredLightBinning lightBinning,
            EndfieldRecoveredVisibilitySHConstants visibilitySHConstants,
            EndfieldRecoveredDeferredLightData selectedLightData,
            EndfieldRecoveredEndminfFullDeferredLightData fullEndminfLightData,
            bool useFullEndminfLightData,
            EndfieldRecoveredDeferredResolverInputProbe.ResourceFrame resources,
            EndfieldRecoveredDeferredShadowData shadowData,
            out ComputeBuffer[] buffers,
            out string failure)
        {
            failure = string.Empty;
            if (lightBinning == null ||
                !lightBinning.TryGetCurrentExactConstantBuffers(
                    camera,
                    width,
                    height,
                    out ComputeBuffer lightBinningConstants,
                    out ComputeBuffer lightCookieData,
                    out failure))
            {
                if (lightBinning == null)
                    failure = "exact consumer light-binning owner is unavailable";
                buffers = null;
                return false;
            }
            ComputeBuffer publishedLightDataBuffer = null;
            uint preparedSerial = 0;
            bool lightPublicationReady = useFullEndminfLightData
                ? fullEndminfLightData != null &&
                  fullEndminfLightData.TryGetCurrentPublication(
                      camera,
                      out publishedLightDataBuffer,
                      out preparedSerial,
                      out failure)
                : selectedLightData != null &&
                  selectedLightData.TryGetCurrentPublication(
                      camera,
                      out publishedLightDataBuffer,
                      out preparedSerial,
                      out failure);
            if (!lightPublicationReady)
            {
                if (string.IsNullOrEmpty(failure))
                    failure = useFullEndminfLightData
                        ? "exact consumer full Endminf LightData owner is unavailable"
                        : "exact consumer selected LightData owner is unavailable";
                buffers = null;
                return false;
            }
            if (resources.t6PreparedSerial != preparedSerial)
            {
                failure = "exact consumer t6 does not match the b4 camera/frame publication";
                buffers = null;
                return false;
            }
            if (shadowData == null ||
                !shadowData.TryGetCurrentPublication(
                    camera,
                    preparedSerial,
                    out ComputeBuffer publishedShadowDataBuffer,
                    out failure))
            {
                if (shadowData == null)
                    failure = "exact consumer ShadowData owner is unavailable";
                buffers = null;
                return false;
            }
            buffers = new[]
            {
                transformVariables?.CurrentBuffer,
                shaderVariablesGlobal?.CurrentBuffer,
                reflectionProbeFallback?.CurrentGlobalDataBuffer,
                lightBinningConstants,
                publishedLightDataBuffer,
                publishedShadowDataBuffer,
                zeroHdplsBuffer,
                lightCookieData,
                visibilitySHConstants?.CurrentBuffer,
            };
            failure = string.Empty;
            for (int slot = 0; slot < buffers.Length; slot++)
            {
                if (buffers[slot] == null || !buffers[slot].IsValid())
                {
                    failure = slot == 6
                        ? "exact consumer b6 local HDPLS zero fallback allocation is unavailable"
                        : "exact consumer b" + slot +
                          " source-backed constant buffer is unavailable";
                    return false;
                }
            }
            return true;
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
                name = "Recovered exact deferred resolver b6 zero fallback"
            };
            zeroHdplsBuffer.SetData(new Vector4[216]);
        }

        private void EnsureZeroSubsurfaceProfileBuffer()
        {
            if (zeroSubsurfaceProfileBuffer != null)
                return;
            zeroSubsurfaceProfileBuffer = new ComputeBuffer(
                15,
                sizeof(float) * 4,
                ComputeBufferType.Constant)
            {
                name = "Recovered legacy HLSL resolver b7 zero fallback"
            };
            zeroSubsurfaceProfileBuffer.SetData(new Vector4[15]);
        }

        private void BindLegacyHlslInputs(
            ComputeBuffer[] currentBuffers,
            EndfieldRecoveredDeferredResolverInputProbe.ResourceFrame resources,
            Texture cameraDepth,
            RenderTexture resolverT23,
            RenderTexture resolverT24,
            RenderTexture resolverT25)
        {
            ComputeBuffer[] legacyBuffers =
            {
                currentBuffers[0], currentBuffers[1], currentBuffers[2],
                currentBuffers[3], currentBuffers[4], currentBuffers[5],
                currentBuffers[6], zeroSubsurfaceProfileBuffer,
                currentBuffers[7], currentBuffers[8],
            };
            int[] byteCounts =
            {
                45, 157, 259, 3, 2054, 401, 216, 15, 160, 4,
            };
            for (int slot = 0; slot < LegacyHlslConstantBufferSlotCount; slot++)
            {
                recoveredHlslMaterial.SetConstantBuffer(
                    LegacyHlslConstantBufferIds[slot],
                    legacyBuffers[slot],
                    0,
                    byteCounts[slot] * sizeof(float) * 4);
            }
            recoveredHlslMaterial.SetBuffer(BufferT0Id, resources.t0Binning);
            for (int slot = 1; slot < LegacyHlslTextureSlotCount; slot++)
            {
                recoveredHlslMaterial.SetTexture(
                    LegacyHlslTextureIds[slot],
                    SelectLegacyHlslTexture(
                        slot,
                        cameraDepth,
                        resources,
                        resolverT23,
                        resolverT24,
                        resolverT25));
            }
        }

        private Texture SelectLegacyHlslTexture(
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
                case 8: return Texture2D.whiteTexture;
                case 9: return Texture2D.blackTexture;
                case 10: return multiscatteringLut;
                case 11:
                case 12: return fallbackArray;
                case 13: return resources.t11ScreenShadow;
                case 14: return Texture2D.blackTexture;
                case 15: return integratedFogFallback;
                case 16: return resources.t14LogSh;
                case 17: return resources.t15VisibilitySh;
                case 18:
                case 19:
                case 20:
                case 21:
                case 22:
                case 23: return fallback3D;
                case 24: return Texture2D.whiteTexture;
                case 25: return resolverT23;
                case 26: return resolverT24;
                case 27: return resolverT25;
                default: return fallback2D;
            }
        }

        private bool TryPrepareNative(out string failure)
        {
            failure = string.Empty;
            try
            {
                if (Native.GetContractVersion() != 2)
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
            if (material != null && recoveredHlslMaterial != null)
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
            Shader recoveredHlslShader = Shader.Find(
                "Hidden/Endfield/Recovered/DeferredPass0CompileDiagnostic");
            if (recoveredHlslShader == null || !recoveredHlslShader.isSupported)
            {
                failure = "recovered deferred pass-0 HLSL shader is unavailable; ";
                DisposeUnityObject(material);
                material = null;
                return false;
            }
            recoveredHlslMaterial = new Material(recoveredHlslShader)
            {
                name = "Recovered deferred pass-0 HLSL sidecar",
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
                if (integratedFogFallback == null)
                {
                    integratedFogFallback = new Texture3D(
                        1,
                        1,
                        1,
                        TextureFormat.ASTC_4x4,
                        false)
                    {
                        name = "Recovered exact resolver disabled volumetric fog fallback",
                        filterMode = FilterMode.Point,
                        wrapMode = TextureWrapMode.Clamp,
                        hideFlags = HideFlags.HideAndDontSave,
                    };
                    integratedFogFallback.SetPixel(
                        0,
                        0,
                        0,
                        new Color(0.0f, 0.0f, 0.0f, 1.0f));
                    integratedFogFallback.Apply(false, true);
                }
                if (multiscatteringLut == null)
                {
                    multiscatteringLut =
                        EndfieldRecoveredMultiscatteringLut.Create();
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
                allocatedHeight == height && recoveredHlslOutput != null)
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
                recoveredHlslOutput = new RenderTexture(output.descriptor)
                {
                    name = "Recovered deferred pass-0 HLSL output",
                    filterMode = FilterMode.Point,
                    wrapMode = TextureWrapMode.Clamp,
                    hideFlags = HideFlags.HideAndDontSave,
                };
                if (!recoveredHlslOutput.Create())
                {
                    failure = "recovered HLSL resolver output creation failed; ";
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
            int height,
            bool t11ContentValid)
        {
            if (readbackRequested || !SystemInfo.supportsAsyncGPUReadback)
                return;
            readbackRequested = true;
            int generation = contentValidationGeneration;
            command.RequestAsyncReadback(output, 0, request =>
            {
                if (disposed || generation != contentValidationGeneration)
                    return;
                if (request.hasError)
                {
                    readbackRequested = false;
                    exactContentValidationComplete = false;
                    exactContentValid = false;
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
                byte[] byteCopy = new byte[data.Length];
                data.CopyTo(byteCopy);
                string sha256 = Hash(byteCopy);
                NativeArray<float> floats = request.GetData<float>();
                exactReadbackFloats = floats.ToArray();
                int finiteFloats = 0;
                int nonFiniteFloats = 0;
                int nonzeroRgbFloats = 0;
                float minimum = float.PositiveInfinity;
                float maximum = float.NegativeInfinity;
                for (int index = 0; index < floats.Length; index++)
                {
                    float value = floats[index];
                    if (float.IsNaN(value) || float.IsInfinity(value))
                    {
                        nonFiniteFloats++;
                        continue;
                    }
                    finiteFloats++;
                    minimum = Mathf.Min(minimum, value);
                    maximum = Mathf.Max(maximum, value);
                    if ((index & 3) != 3 && Mathf.Abs(value) > 1.0e-6f)
                        nonzeroRgbFloats++;
                }
                exactContentValidationComplete = true;
                bool numericContentValid =
                    nonFiniteFloats == 0 && nonzeroRgbFloats > 0;
                // A numerically nonzero resolver result is not presentation
                // authority. The selected retail program consumes t11 with
                // screen-space shadows enabled, so the exact output may be
                // presented only when the same-frame t11 producer separately
                // certifies its source content and provenance.
                exactContentValid = t11ContentValid && numericContentValid;
                Debug.Log(
                    "Recovered exact deferred resolver consumer readback: " +
                    $"camera={cameraName}, size={width}x{height}, " +
                    $"bytes={data.Length}, nonzeroBytes={nonzeroBytes}, " +
                    $"exactBound={Native.GetExactShaderBound()}, " +
                    $"resourceMask=0x{Native.GetShaderResourceMask():x}, " +
                    $"resourceFailureMask=0x{Native.GetShaderResourceFailureMask():x}, " +
                    $"resourceFailureResults={FormatResourceFailures()}, " +
                    $"constantBufferMask=0x{Native.GetConstantBufferMask():x}, " +
                    $"rgbaFloatSha256={sha256}, " +
                    $"finiteFloats={finiteFloats}, " +
                    $"nonFiniteFloats={nonFiniteFloats}, " +
                    $"nonzeroRgbFloats={nonzeroRgbFloats}, " +
                    $"numericContentValid={numericContentValid}, " +
                    $"t11ContentValid={t11ContentValid}, " +
                    $"screenContentValid={exactContentValid}, " +
                    $"min={minimum.ToString("R", CultureInfo.InvariantCulture)}, " +
                    $"max={maximum.ToString("R", CultureInfo.InvariantCulture)}, " +
                    $"failureCount={Native.GetFailureCount()}, " +
                    "presented=false, retailPass0=false.");
                TryLogHlslComparison(cameraName, width, height);
            });
        }

        private void RequestRecoveredHlslReadback(
            CommandBuffer command,
            string cameraName,
            int width,
            int height)
        {
            if (recoveredHlslReadbackRequested ||
                !SystemInfo.supportsAsyncGPUReadback)
                return;
            recoveredHlslReadbackRequested = true;
            int generation = contentValidationGeneration;
            command.RequestAsyncReadback(recoveredHlslOutput, 0, request =>
            {
                if (disposed || generation != contentValidationGeneration)
                    return;
                if (request.hasError)
                {
                    recoveredHlslReadbackRequested = false;
                    Debug.LogWarning(
                        "Recovered deferred pass-0 HLSL sidecar readback failed closed.");
                    return;
                }
                NativeArray<float> floats = request.GetData<float>();
                recoveredHlslReadbackFloats = floats.ToArray();
                int nonFinite = 0;
                for (int index = 0; index < floats.Length; index++)
                {
                    if (float.IsNaN(floats[index]) || float.IsInfinity(floats[index]))
                        nonFinite++;
                }
                byte[] bytes = new byte[request.GetData<byte>().Length];
                request.GetData<byte>().CopyTo(bytes);
                Debug.Log(
                    "Recovered deferred pass-0 HLSL sidecar readback: " +
                    $"camera={cameraName}, size={width}x{height}, " +
                    $"rgbaFloatSha256={Hash(bytes)}, " +
                    $"finiteFloats={floats.Length - nonFinite}, " +
                    $"nonFiniteFloats={nonFinite}, presented=false.");
                TryLogHlslComparison(cameraName, width, height);
            });
        }

        private void TryLogHlslComparison(
            string cameraName,
            int width,
            int height)
        {
            if (comparisonLogged || exactReadbackFloats == null ||
                recoveredHlslReadbackFloats == null)
                return;
            comparisonLogged = true;
            if (exactReadbackFloats.Length != recoveredHlslReadbackFloats.Length)
            {
                Debug.LogWarning(
                    "Recovered deferred pass-0 HLSL comparison failed closed: " +
                    "readback lengths differ.");
                return;
            }

            double squaredError = 0.0;
            float maximumAbsoluteError = 0.0f;
            int over1e6 = 0;
            int over1e4 = 0;
            int over1e3 = 0;
            for (int index = 0; index < exactReadbackFloats.Length; index++)
            {
                float error = Mathf.Abs(
                    exactReadbackFloats[index] - recoveredHlslReadbackFloats[index]);
                maximumAbsoluteError = Mathf.Max(maximumAbsoluteError, error);
                squaredError += (double)error * error;
                if (error > 1.0e-6f) over1e6++;
                if (error > 1.0e-4f) over1e4++;
                if (error > 1.0e-3f) over1e3++;
            }
            double rmse = Math.Sqrt(
                squaredError / Math.Max(1, exactReadbackFloats.Length));
            Debug.Log(
                "Recovered deferred pass-0 HLSL vs exact DXBC comparison: " +
                $"camera={cameraName}, size={width}x{height}, " +
                $"floatCount={exactReadbackFloats.Length}, " +
                $"maxAbs={maximumAbsoluteError.ToString("R", CultureInfo.InvariantCulture)}, " +
                $"rmse={rmse.ToString("R", CultureInfo.InvariantCulture)}, " +
                $"over1e-6={over1e6}, over1e-4={over1e4}, over1e-3={over1e3}, " +
                "presented=false.");
        }

        private bool FailClosed(string failure)
        {
            if (!loggedFailure || !string.Equals(
                    failure,
                    lastFailure,
                    StringComparison.Ordinal))
            {
                Debug.LogWarning(
                    "Recovered exact deferred resolver consumer failed closed: " +
                    failure + ".");
                loggedFailure = true;
                lastFailure = failure;
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

        private static string Hash(byte[] bytes)
        {
            using SHA256 sha = SHA256.Create();
            byte[] digest = sha.ComputeHash(bytes);
            var builder = new StringBuilder(digest.Length * 2);
            for (int index = 0; index < digest.Length; index++)
                builder.Append(digest[index].ToString("x2"));
            return builder.ToString();
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
                case 10: return multiscatteringLut;
                // CharInfo serializes a null CSM ramp; the installed native
                // push binds Texture2D.blackTexture for this slot.
                case 9: return Texture2D.blackTexture;
                // The selected CharInfo HDPLS selector rows are all zero; the
                // inactive native push binds white to the HDPLS screen mask.
                case 8: return Texture2D.whiteTexture;
                case 11: return resources.t11ScreenShadow;
                // The source-closed isolated light fixtures have no cookie
                // indices; the native zero-cookie transport binds black.
                case 12: return Texture2D.blackTexture;
                // The installed CharInfo route disables volumetric fog and
                // publishes the native 1x1x1 ASTC_4x4 black Texture3D.
                case 13: return integratedFogFallback;
                case 23: return resolverT23;
                case 24: return resolverT24;
                case 25: return resolverT25;
                // The installed CharInfo V2 route resolves no /aiTest/index.bytes
                // map, so the native missing-map result uses one shared 1x1x1
                // zero Texture3D for all six irradiance slots.  This fixture
                // texture mirrors that zero texel only; it is not a live V2
                // atlas and must not be replaced with the legacy Gacha payload.
                case 16:
                case 17:
                case 18:
                case 19:
                case 20:
                case 21:
                    return fallback3D;
                case 14: return resources.t14LogSh;
                case 15: return resources.t15VisibilitySh;
                // The selected CharInfo environment keeps rain/wetness
                // disabled; the original native push binds its white fallback
                // to the wetness slot in that state.
                case 22: return Texture2D.whiteTexture;
                default:
                    return fallback2D;
            }
        }

        private static int[] CreateTextureIds()
        {
            return CreateTextureIds(TextureSlotCount);
        }

        private static int[] CreateTextureIds(int count)
        {
            var ids = new int[count];
            for (int slot = 1; slot < count; slot++)
                ids[slot] = Shader.PropertyToID("_EndfieldTextureT" + slot);
            return ids;
        }

        private static int[] CreateConstantBufferIds()
        {
            return CreateConstantBufferIds(ConstantBufferSlotCount);
        }

        private static int[] CreateConstantBufferIds(int count)
        {
            var ids = new int[count];
            for (int slot = 0; slot < count; slot++)
                ids[slot] = Shader.PropertyToID("EndfieldCB" + slot);
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
            if (output != null)
            {
                if (output.IsCreated())
                    output.Release();
                DisposeUnityObject(output);
            }
            if (recoveredHlslOutput != null)
            {
                if (recoveredHlslOutput.IsCreated())
                    recoveredHlslOutput.Release();
                DisposeUnityObject(recoveredHlslOutput);
            }
            output = null;
            recoveredHlslOutput = null;
            InvalidateContentValidation();
            allocatedWidth = 0;
            allocatedHeight = 0;
        }

        private void InvalidateContentValidation()
        {
            unchecked
            {
                contentValidationGeneration++;
            }
            readbackRequested = false;
            recoveredHlslReadbackRequested = false;
            exactReadbackFloats = null;
            recoveredHlslReadbackFloats = null;
            comparisonLogged = false;
            exactContentValidationComplete = false;
            exactContentValid = false;
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
                "EndfieldOriginalDxbcBeginDiagnosticSubmission")]
            internal static extern ulong BeginDiagnosticSubmission(
                [In] ulong[] texturePointers,
                uint texturePointerCount,
                [In] ulong[] retainedResourcePointers,
                uint retainedResourceCount);

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcCancelDiagnosticSubmission")]
            internal static extern uint CancelDiagnosticSubmission(
                ulong submissionSerial);

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetCompletedDiagnosticSubmissionSerial")]
            internal static extern ulong GetCompletedDiagnosticSubmissionSerial();

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
                "EndfieldOriginalDxbcGetConstantBufferMask")]
            internal static extern uint GetConstantBufferMask();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetExactShaderBound")]
            internal static extern uint GetExactShaderBound();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetRenderEventFunc")]
            internal static extern IntPtr GetRenderEventFunc();
        }
    }
}
