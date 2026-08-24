using System;
using UnityEngine;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Owns the exact recovered XY/Z membership buffers for the isolated
    /// original CharInfo overview-light rig. Native arbitrary-scene candidate
    /// culling remains outside this class and is not approximated here.
    /// </summary>
    internal sealed class EndfieldRecoveredLightBinning : IDisposable
    {
        private const string ComputeResourceName = "EndfieldRecoveredLightBinning";
        private const string ConstantsEnvironmentVariable =
            "ENDFIELD_RECOVERED_LIGHT_BINNING_CONSTANTS";
        private const string ConstantsCommandLineArgument =
            "-endfield-recovered-light-binning-constants";
        private const string LightCookieDataEnvironmentVariable =
            "ENDFIELD_RECOVERED_LIGHT_COOKIE_DATA";
        private const string LightCookieDataCommandLineArgument =
            "-endfield-recovered-light-cookie-data";
        private const string CanonicalBinningComputeResourceName =
            "EndfieldRecoveredCanonicalBinning";
        private const string CanonicalBinningEnvironmentVariable =
            "ENDFIELD_RECOVERED_CANONICAL_BINNING_BUFFER";
        private const string CanonicalBinningCommandLineArgument =
            "-endfield-recovered-canonical-binning-buffer";
        private const int TileSize = EndfieldRecoveredLightBinningConstantsContract.TileSize;
        private const int SliceCount = EndfieldRecoveredLightBinningConstantsContract.SliceCount;
        private const int WordsPerBin = 8;
        private const float ZSliceSize =
            EndfieldRecoveredLightBinningConstantsContract.ZBinSlice;

        private static readonly int DescriptorBufferId =
            Shader.PropertyToID("_EndfieldRecoveredLightDescriptors");
        private static readonly int BinningBufferId =
            Shader.PropertyToID("_EndfieldRecoveredLightBinningBuffer");
        private static readonly int PunctualLightCountId =
            Shader.PropertyToID("_PunctualLightCount");
        private static readonly int NumTilesId = Shader.PropertyToID("_NumTiles");
        private static readonly int ActualWidthId = Shader.PropertyToID("_ActualWidth");
        private static readonly int ActualHeightId = Shader.PropertyToID("_ActualHeight");
        private static readonly int TileSizeId = Shader.PropertyToID("_TileSize");
        private static readonly int NumTilesXId = Shader.PropertyToID("_NumTilesX");
        private static readonly int NumTilesYId = Shader.PropertyToID("_NumTilesY");
        private static readonly int NumSliceZId = Shader.PropertyToID("_NumSliceZ");
        private static readonly int NearClipPlaneId = Shader.PropertyToID("_NearClipPlane");
        private static readonly int FarClipPlaneId = Shader.PropertyToID("_FarClipPlane");
        private static readonly int ZBinSliceId = Shader.PropertyToID("_ZBinSlice");
        private static readonly int InvZBinSliceId = Shader.PropertyToID("_InvZBinSlice");
        private static readonly int NearPlaneParamsId =
            Shader.PropertyToID("_EndfieldRecoveredLightNearPlaneParams");
        private static readonly int ZOffsetId =
            Shader.PropertyToID("_EndfieldRecoveredLightBinningZOffset");
        private static readonly int GlobalLayoutId =
            Shader.PropertyToID("_EndfieldRecoveredLightBinningLayout");
        private static readonly int GlobalDepthId =
            Shader.PropertyToID("_EndfieldRecoveredLightBinningDepth");
        private static readonly int GlobalAvailableId =
            Shader.PropertyToID("_EndfieldRecoveredLightBinningAvailable");
        private static readonly int OperatorLightCountId =
            Shader.PropertyToID("_EndfieldOperatorLightCount");
        private static readonly int RecoveredClusteredNprLightLoopId =
            Shader.PropertyToID("_EndfieldRecoveredClusteredNprLightLoop");
        private static readonly int RetailConstantsId =
            Shader.PropertyToID("_LightBinningConstants");
        // The selected original D3D11 resolver exposes the same 48-byte
        // LightBinningConstants payload as register b3.  Keep this bridge
        // beside the semantic name; it is only published when the explicit
        // recovered transport selector is enabled.
        private static readonly int ExactDxbcBridgeConstantsId =
            Shader.PropertyToID("EndfieldCB3");
        private static readonly int RetailConstantsReadyId =
            Shader.PropertyToID("_EndfieldRecoveredLightBinningConstantsReady");
        private static readonly int RetailLightCookieDataId =
            Shader.PropertyToID("_LightCookieData");
        // The source-closed zero-cookie payload occupies the selected
        // resolver's register b7 as well as its semantic LightCookieData
        // name.  The alias is intentionally not used as an active-cookie
        // claim; non-empty atlas/matrix generation remains open.
        private static readonly int ExactDxbcBridgeLightCookieDataId =
            Shader.PropertyToID("EndfieldCB7");
        private static readonly int RetailLightCookieTextureId =
            Shader.PropertyToID("_LightCookie");
        private static readonly int RetailLightCookieDataReadyId =
            Shader.PropertyToID("_EndfieldRecoveredLightCookieDataReady");
        private static readonly int CanonicalBinningBufferId =
            Shader.PropertyToID("_BinningBuffer");
        private static readonly int CanonicalBinningOffsetsId =
            Shader.PropertyToID("_BinningBufferOffsets");
        private static readonly int CanonicalBinningReadyId =
            Shader.PropertyToID("_EndfieldRecoveredCanonicalBinningReady");
        private static readonly int CanonicalBinningOutputId =
            Shader.PropertyToID("_EndfieldRecoveredCanonicalBinningBuffer");
        private static readonly int CanonicalLightWordCountId =
            Shader.PropertyToID("_EndfieldRecoveredCanonicalLightWordCount");
        private static readonly int CanonicalCombinedWordCountId =
            Shader.PropertyToID("_EndfieldRecoveredCanonicalCombinedWordCount");

        private readonly Vector4[] descriptors =
            new Vector4[EndfieldHGOperatorLightRig.DescriptorVectorCount];
        private readonly ComputeShader compute;
        private readonly ComputeShader canonicalBinningCompute;
        private readonly bool retailConstantsRequested;
        private readonly bool retailLightCookieDataRequested;
        private readonly bool canonicalBinningRequested;
        private readonly int xyKernel = -1;
        private readonly int zKernel = -1;
        private readonly int canonicalBinningKernel = -1;
        private ComputeBuffer descriptorBuffer;
        private ComputeBuffer binningBuffer;
        private ComputeBuffer canonicalBinningBuffer;
        private ComputeBuffer zeroFallbackBuffer;
        private ComputeBuffer retailConstantsBuffer;
        private ComputeBuffer zeroRetailConstantsBuffer;
        private ComputeBuffer zeroRetailLightCookieDataBuffer;
        private readonly Vector4[] retailConstantsVectors = new Vector4[3];
        private bool loggedActivation;
        private bool loggedFailure;
        private bool loggedConstantsActivation;
        private bool loggedConstantsFailure;
        private bool loggedLightCookieDataActivation;
        private bool loggedLightCookieDataFailure;
        private bool loggedCanonicalBinningActivation;
        private bool loggedCanonicalBinningFailure;
        private bool canonicalPublicationValid;
        private int canonicalPublicationCameraInstanceId;
        private int canonicalPublicationFrame;
        private int canonicalPublicationWidth;
        private int canonicalPublicationHeight;
        private bool retailConstantsPublicationValid;
        private bool lightCookiePublicationValid;
        private int retailPublicationCameraInstanceId;
        private int retailPublicationFrame;
        private int retailPublicationWidth;
        private int retailPublicationHeight;
        private bool disposed;

        internal EndfieldRecoveredLightBinning()
        {
            retailConstantsRequested =
                ReadBooleanEnvironment(ConstantsEnvironmentVariable) ||
                HasCommandLineArgument(ConstantsCommandLineArgument) ||
                EndfieldRecoveredDeferredResolverBindingPolicy.IsRequested;
            retailLightCookieDataRequested =
                ReadBooleanEnvironment(LightCookieDataEnvironmentVariable) ||
                HasCommandLineArgument(LightCookieDataCommandLineArgument) ||
                EndfieldRecoveredDeferredResolverBindingPolicy.IsRequested;
            canonicalBinningRequested =
                ReadBooleanEnvironment(CanonicalBinningEnvironmentVariable) ||
                HasCommandLineArgument(CanonicalBinningCommandLineArgument);
            compute = Resources.Load<ComputeShader>(ComputeResourceName);
            if (compute != null)
            {
                try
                {
                    xyKernel = compute.FindKernel("BuildXY");
                    zKernel = compute.FindKernel("BuildZ");
                }
                catch (Exception exception)
                {
                    Debug.LogWarning(
                        "Recovered light binning could not resolve BuildXY/BuildZ: " +
                        exception.Message);
                }
            }
            canonicalBinningCompute =
                Resources.Load<ComputeShader>(CanonicalBinningComputeResourceName);
            if (canonicalBinningCompute != null)
            {
                try
                {
                    canonicalBinningKernel = canonicalBinningCompute.FindKernel(
                        "BuildCanonicalCombined");
                }
                catch (Exception exception)
                {
                    Debug.LogWarning(
                        "Recovered canonical binning could not resolve " +
                        "BuildCanonicalCombined: " + exception.Message);
                }
            }
            EnsureZeroFallbackBuffer();
        }

        internal bool PrepareCamera(
            Camera camera,
            int width,
            int height,
            EndfieldHGOperatorLightRig rig,
            CommandBuffer commandBuffer)
        {
            if (disposed)
                throw new ObjectDisposedException(nameof(EndfieldRecoveredLightBinning));
            if (camera == null)
                throw new ArgumentNullException(nameof(camera));
            if (commandBuffer == null)
                throw new ArgumentNullException(nameof(commandBuffer));
            canonicalPublicationValid = false;
            retailConstantsPublicationValid = false;
            lightCookiePublicationValid = false;
            commandBuffer.SetGlobalFloat(CanonicalBinningReadyId, 0.0f);

            bool membershipRequested =
                rig != null &&
                rig.sourceBackedClusteredNprLightLoop &&
                rig.sourceBackedLightBinningMembership;
            int lightCount = 0;
            if (rig != null)
            {
                lightCount = rig.PrepareSourceBackedFrame(
                    camera,
                    commandBuffer,
                    membershipRequested ? descriptors : null);
            }
            else
            {
                // Prevent a second camera without a rig from consuming the
                // previous camera's immediate/global light state.
                commandBuffer.SetGlobalInt(OperatorLightCountId, 0);
                commandBuffer.SetGlobalFloat(RecoveredClusteredNprLightLoopId, 0.0f);
            }

            if (!membershipRequested)
            {
                BindRetailConstantsFallback(commandBuffer);
                BindRetailLightCookieDataFallback(commandBuffer);
                BindFallback(commandBuffer);
                return false;
            }
            if (camera.orthographic)
            {
                ReportFailure(
                    "orthographic cameras are outside the recovered perspective CharInfo contract");
                BindRetailConstantsFallback(commandBuffer);
                BindRetailLightCookieDataFallback(commandBuffer);
                BindFallback(commandBuffer);
                return false;
            }

            retailConstantsPublicationValid = PublishRetailConstants(
                commandBuffer,
                lightCount,
                width,
                height,
                camera.nearClipPlane,
                camera.farClipPlane);
            lightCookiePublicationValid = PublishRetailLightCookieData(
                commandBuffer,
                rig,
                lightCount);
            retailPublicationCameraInstanceId = camera.GetInstanceID();
            retailPublicationFrame = Time.frameCount;
            retailPublicationWidth = width;
            retailPublicationHeight = height;

            if (!SystemInfo.supportsComputeShaders)
            {
                ReportFailure("the active graphics device does not support compute shaders");
                BindFallback(commandBuffer);
                return false;
            }
            if (compute == null || xyKernel < 0 || zKernel < 0)
            {
                ReportFailure(
                    $"Resources/{ComputeResourceName}.compute or its BuildXY/BuildZ kernels are unavailable");
                BindFallback(commandBuffer);
                return false;
            }

            width = Mathf.Max(width, 1);
            height = Mathf.Max(height, 1);
            int tileCountX = (width + TileSize - 1) / TileSize;
            int tileCountY = (height + TileSize - 1) / TileSize;
            int tileCount = tileCountX * tileCountY;
            int zOffset = tileCount * WordsPerBin;
            int requiredWordCount =
                zOffset + SliceCount * WordsPerBin;

            string bufferFailure;
            if (!EnsureBuffers(requiredWordCount, out bufferFailure))
            {
                ReportFailure(bufferFailure);
                BindFallback(commandBuffer);
                return false;
            }

            try
            {
                descriptorBuffer.SetData(descriptors);
            }
            catch (Exception exception)
            {
                ReportFailure("descriptor upload failed: " + exception.Message);
                BindFallback(commandBuffer);
                return false;
            }

            float nearClip = camera.nearClipPlane;
            float farClip = camera.farClipPlane;
            float nearHeight = 2.0f * nearClip * Mathf.Tan(
                camera.fieldOfView * 0.5f * Mathf.Deg2Rad);
            float nearWidth = nearHeight * ((float)width / height);
            float tileStepAtNear = nearHeight / height * TileSize;

            SetCommonComputeParameters(
                commandBuffer,
                lightCount,
                tileCount,
                width,
                height,
                tileCountX,
                tileCountY,
                nearClip,
                farClip,
                new Vector4(nearWidth, nearHeight, tileStepAtNear, 0.0f),
                zOffset);

            commandBuffer.SetComputeBufferParam(
                compute, xyKernel, DescriptorBufferId, descriptorBuffer);
            commandBuffer.SetComputeBufferParam(
                compute, xyKernel, BinningBufferId, binningBuffer);
            commandBuffer.SetComputeBufferParam(
                compute, zKernel, DescriptorBufferId, descriptorBuffer);
            commandBuffer.SetComputeBufferParam(
                compute, zKernel, BinningBufferId, binningBuffer);
            commandBuffer.DispatchCompute(
                compute,
                xyKernel,
                (tileCountX + 7) / 8,
                (tileCountY + 7) / 8,
                1);
            commandBuffer.DispatchCompute(
                compute,
                zKernel,
                (SliceCount + 63) / 64,
                1,
                1);

            bool canonicalBinningPublished = PublishCanonicalBinning(
                commandBuffer,
                width,
                height,
                requiredWordCount);
            if (canonicalBinningPublished)
            {
                canonicalPublicationValid = true;
                canonicalPublicationCameraInstanceId = camera.GetInstanceID();
                canonicalPublicationFrame = Time.frameCount;
                canonicalPublicationWidth = width;
                canonicalPublicationHeight = height;
            }

            commandBuffer.SetGlobalBuffer(BinningBufferId, binningBuffer);
            commandBuffer.SetGlobalVector(
                GlobalLayoutId,
                new Vector4(tileCountX, tileCountY, SliceCount, zOffset));
            commandBuffer.SetGlobalVector(
                GlobalDepthId,
                new Vector4(nearClip, ZSliceSize, 1.0f / ZSliceSize, farClip));
            commandBuffer.SetGlobalFloat(GlobalAvailableId, 1.0f);

            if (!loggedActivation)
            {
                Debug.Log(
                    "Recovered isolated-rig light membership active: " +
                    $"{lightCount} lights, {tileCountX}x{tileCountY} XY tiles, " +
                    $"{SliceCount} one-unit Z slices, {requiredWordCount} uint words.");
                loggedActivation = true;
            }
            return canonicalBinningPublished;
        }

        internal ComputeBuffer CurrentRetailConstantsBuffer => retailConstantsBuffer;

        internal ComputeBuffer CurrentLightCookieDataBuffer =>
            zeroRetailLightCookieDataBuffer;

        internal bool TryGetCurrentExactConstantBuffers(
            Camera camera,
            int width,
            int height,
            out ComputeBuffer constants,
            out ComputeBuffer lightCookieData,
            out string failure)
        {
            constants = null;
            lightCookieData = null;
            failure = string.Empty;
            if (!retailConstantsPublicationValid ||
                !lightCookiePublicationValid ||
                camera == null ||
                retailPublicationCameraInstanceId != camera.GetInstanceID() ||
                retailPublicationFrame != Time.frameCount ||
                retailPublicationWidth != width ||
                retailPublicationHeight != height ||
                retailConstantsBuffer == null ||
                !retailConstantsBuffer.IsValid() ||
                zeroRetailLightCookieDataBuffer == null ||
                !zeroRetailLightCookieDataBuffer.IsValid())
            {
                failure =
                    "current-camera LightBinningConstants/zero-cookie publication is not provenance-valid";
                return false;
            }
            constants = retailConstantsBuffer;
            lightCookieData = zeroRetailLightCookieDataBuffer;
            return true;
        }

        private bool PublishCanonicalBinning(
            CommandBuffer commandBuffer,
            int width,
            int height,
            int recoveredLightWordCount)
        {
            if (!canonicalBinningRequested)
                return false;

            EndfieldRecoveredCanonicalBinningLayoutContract.Layout layout;
            string failure;
            if (!EndfieldRecoveredCanonicalBinningLayoutContract.TryBuild(
                    width,
                    height,
                    out layout,
                    out failure))
            {
                ReportCanonicalBinningFailure(failure);
                return false;
            }
            if (layout.lightWordCount != recoveredLightWordCount)
            {
                ReportCanonicalBinningFailure(
                    "light segment size disagrees with the installed layout: " +
                    $"expected {layout.lightWordCount}, actual {recoveredLightWordCount}");
                return false;
            }
            if (canonicalBinningCompute == null || canonicalBinningKernel < 0)
            {
                ReportCanonicalBinningFailure(
                    $"Resources/{CanonicalBinningComputeResourceName}.compute or " +
                    "BuildCanonicalCombined is unavailable");
                return false;
            }

            try
            {
                EnsureCanonicalBinningBuffer(layout.totalWordCount);
                commandBuffer.SetComputeBufferParam(
                    canonicalBinningCompute,
                    canonicalBinningKernel,
                    BinningBufferId,
                    binningBuffer);
                commandBuffer.SetComputeBufferParam(
                    canonicalBinningCompute,
                    canonicalBinningKernel,
                    CanonicalBinningOutputId,
                    canonicalBinningBuffer);
                commandBuffer.SetComputeIntParam(
                    canonicalBinningCompute,
                    CanonicalLightWordCountId,
                    layout.lightWordCount);
                commandBuffer.SetComputeIntParam(
                    canonicalBinningCompute,
                    CanonicalCombinedWordCountId,
                    layout.totalWordCount);
                commandBuffer.DispatchCompute(
                    canonicalBinningCompute,
                    canonicalBinningKernel,
                    (layout.totalWordCount + 63) / 64,
                    1,
                    1);
                commandBuffer.SetGlobalBuffer(
                    CanonicalBinningBufferId,
                    canonicalBinningBuffer);
                commandBuffer.SetGlobalVector(
                    CanonicalBinningOffsetsId,
                    new Vector4(
                        layout.lightXYOffset,
                        layout.lightZOffset,
                        layout.reflectionXYOffset,
                        layout.reflectionZOffset));
                commandBuffer.SetGlobalFloat(CanonicalBinningReadyId, 1.0f);
            }
            catch (Exception exception)
            {
                ReportCanonicalBinningFailure(
                    "combined raw-buffer publication failed: " + exception.Message);
                commandBuffer.SetGlobalFloat(CanonicalBinningReadyId, 0.0f);
                return false;
            }

            if (!loggedCanonicalBinningActivation)
            {
                Debug.Log(
                    "Recovered canonical _BinningBuffer active for the " +
                    "source-closed no-local-probe CharInfo fixture: " +
                    $"light={layout.lightWordCount} words, " +
                    $"reflection={layout.reflectionWordCount} zero words, " +
                    $"combined={layout.totalWordCount} words.");
                loggedCanonicalBinningActivation = true;
            }
            return true;
        }

        internal void DisableCanonicalPublication(CommandBuffer commandBuffer)
        {
            if (commandBuffer == null)
                throw new ArgumentNullException(nameof(commandBuffer));
            canonicalPublicationValid = false;
            commandBuffer.SetGlobalFloat(CanonicalBinningReadyId, 0.0f);
        }

        internal bool TryGetCurrentCanonicalPublication(
            Camera camera,
            int width,
            int height,
            out ComputeBuffer publishedBuffer)
        {
            publishedBuffer = null;
            if (!canonicalPublicationValid ||
                camera == null ||
                canonicalPublicationCameraInstanceId != camera.GetInstanceID() ||
                canonicalPublicationFrame != Time.frameCount ||
                canonicalPublicationWidth != width ||
                canonicalPublicationHeight != height ||
                canonicalBinningBuffer == null ||
                !canonicalBinningBuffer.IsValid())
            {
                return false;
            }
            publishedBuffer = canonicalBinningBuffer;
            return true;
        }

        private void EnsureCanonicalBinningBuffer(int wordCount)
        {
            if (canonicalBinningBuffer != null &&
                canonicalBinningBuffer.count == wordCount)
            {
                return;
            }
            canonicalBinningBuffer?.Release();
            canonicalBinningBuffer = new ComputeBuffer(
                wordCount,
                EndfieldRecoveredCanonicalBinningLayoutContract.WordStrideBytes,
                ComputeBufferType.Raw)
            {
                name = "Endfield Recovered Canonical Light/Reflection Binning"
            };
        }

        private bool PublishRetailConstants(
            CommandBuffer commandBuffer,
            int sourceClosedLightCount,
            int width,
            int height,
            float nearClip,
            float farClip)
        {
            if (!retailConstantsRequested)
            {
                commandBuffer.SetGlobalFloat(RetailConstantsReadyId, 0.0f);
                return false;
            }

            EndfieldRecoveredLightBinningConstantsContract.Data data;
            string failure = string.Empty;
            if (!EndfieldRecoveredLightBinningConstantsContract.TryBuild(
                    sourceClosedLightCount,
                    width,
                    height,
                    nearClip,
                    farClip,
                    out data,
                    out failure))
            {
                ReportConstantsFailure(failure);
                BindRetailConstantsFallback(commandBuffer);
                return false;
            }

            try
            {
                EnsureRetailConstantsBuffers();
                PackRetailConstants(data, retailConstantsVectors);
                retailConstantsBuffer.SetData(retailConstantsVectors);
                commandBuffer.SetGlobalConstantBuffer(
                    retailConstantsBuffer,
                    RetailConstantsId,
                    0,
                    EndfieldRecoveredLightBinningConstantsContract.SizeBytes);
                commandBuffer.SetGlobalConstantBuffer(
                    retailConstantsBuffer,
                    ExactDxbcBridgeConstantsId,
                    0,
                    EndfieldRecoveredLightBinningConstantsContract.SizeBytes);
                commandBuffer.SetGlobalFloat(RetailConstantsReadyId, 1.0f);
            }
            catch (Exception exception)
            {
                ReportConstantsFailure(
                    "48-byte constant-buffer publication failed: " + exception.Message);
                BindRetailConstantsFallback(commandBuffer);
                return false;
            }

            if (!loggedConstantsActivation)
            {
                Debug.Log(
                    "Recovered _LightBinningConstants publication active for the " +
                    "source-closed isolated Overview rig: " +
                    $"{data.lightCount} lights, {data.actualWidth}x{data.actualHeight}, " +
                    $"{data.numTilesX}x{data.numTilesY} tiles. This does not claim " +
                    "the unresolved retail whole-scene survivor list; " +
                    "exact resolver bridge=EndfieldCB3.");
                loggedConstantsActivation = true;
            }
            return true;
        }

        private void EnsureRetailConstantsBuffers()
        {
            if (retailConstantsBuffer == null)
            {
                retailConstantsBuffer = new ComputeBuffer(
                    3,
                    sizeof(float) * 4,
                    ComputeBufferType.Constant)
                {
                    name = "Endfield Recovered LightBinningConstants"
                };
            }
            if (zeroRetailConstantsBuffer == null)
            {
                zeroRetailConstantsBuffer = new ComputeBuffer(
                    3,
                    sizeof(float) * 4,
                    ComputeBufferType.Constant)
                {
                    name = "Endfield Recovered LightBinningConstants Zero Fallback"
                };
                zeroRetailConstantsBuffer.SetData(new Vector4[3]);
            }
        }

        private bool PublishRetailLightCookieData(
            CommandBuffer commandBuffer,
            EndfieldHGOperatorLightRig rig,
            int sourceClosedLightCount)
        {
            if (!retailLightCookieDataRequested)
            {
                commandBuffer.SetGlobalFloat(RetailLightCookieDataReadyId, 0.0f);
                return false;
            }

            string failure = string.Empty;
            if (!TryValidateSourceClosedZeroCookieFrame(
                    rig,
                    sourceClosedLightCount,
                    out failure))
            {
                ReportLightCookieDataFailure(
                    failure);
                BindRetailLightCookieDataFallback(commandBuffer);
                return false;
            }

            try
            {
                EnsureZeroRetailLightCookieDataBuffer();
                commandBuffer.SetGlobalConstantBuffer(
                    zeroRetailLightCookieDataBuffer,
                    RetailLightCookieDataId,
                    0,
                    EndfieldRecoveredLightCookieDataContract.SizeBytes);
                commandBuffer.SetGlobalConstantBuffer(
                    zeroRetailLightCookieDataBuffer,
                    ExactDxbcBridgeLightCookieDataId,
                    0,
                    EndfieldRecoveredLightCookieDataContract.SizeBytes);
                // The exact resolver skips this texture when every packed
                // cookie index is -1. A valid black descriptor is therefore
                // transport-only and cannot affect the source-closed path.
                commandBuffer.SetGlobalTexture(
                    RetailLightCookieTextureId,
                    Texture2D.blackTexture);
                commandBuffer.SetGlobalFloat(RetailLightCookieDataReadyId, 1.0f);
            }
            catch (Exception exception)
            {
                ReportLightCookieDataFailure(
                    "2,560-byte constant-buffer publication failed: " + exception.Message);
                BindRetailLightCookieDataFallback(commandBuffer);
                return false;
            }

            if (!loggedLightCookieDataActivation)
            {
                Debug.Log(
                    "Recovered _LightCookieData publication active for the source-closed " +
                    $"zero-cookie isolated Overview rig ({sourceClosedLightCount} lights). " +
                    "The exact 2,560-byte binding is zero and _LightCookie is unobserved " +
                    "because every packed cookie index is -1. This does not claim the " +
                    "retail whole-scene cookie atlas; exact resolver bridge=EndfieldCB7.");
                loggedLightCookieDataActivation = true;
            }
            return true;
        }

        private static bool TryValidateSourceClosedZeroCookieFrame(
            EndfieldHGOperatorLightRig rig,
            int preparedLightCount,
            out string failure)
        {
            failure = string.Empty;
            if (rig == null)
            {
                failure = "no isolated Overview light rig is bound";
                return false;
            }
            if (!rig.sourceBackedClusteredNprLightLoop ||
                !rig.sourceBackedLightBinningMembership)
            {
                failure =
                    "the source-backed clustered loop and exact isolated membership are not both enabled";
                return false;
            }

            int installedFixtureCount;
            if (rig.actorRoot != null && string.Equals(
                    rig.actorRoot.name,
                    "Wulfa",
                    StringComparison.OrdinalIgnoreCase))
            {
                installedFixtureCount = 8;
            }
            else if (rig.actorRoot != null && string.Equals(
                         rig.actorRoot.name,
                         "Zhuangfy",
                         StringComparison.OrdinalIgnoreCase))
            {
                installedFixtureCount = 6;
            }
            else if (rig.actorRoot != null && string.Equals(
                         rig.actorRoot.name,
                         "Endminf",
                         StringComparison.OrdinalIgnoreCase))
            {
                installedFixtureCount = 12;
            }
            else
            {
                failure =
                    $"actor identity '{(rig.actorRoot != null ? rig.actorRoot.name : "<null>")}' " +
                    "is outside the source-closed Wulfa/Zhuangfy/Endminf Overview fixtures";
                return false;
            }
            if (rig.lights == null || rig.lights.Length != installedFixtureCount ||
                preparedLightCount != installedFixtureCount)
            {
                failure =
                    $"installed Overview light-list identity mismatch: expected " +
                    $"{installedFixtureCount}, found {preparedLightCount}";
                return false;
            }

            for (int sourceIndex = 0; sourceIndex < rig.lights.Length; sourceIndex++)
            {
                if (rig.lights[sourceIndex].hasCookie)
                {
                    failure =
                        $"source light {sourceIndex} ('{rig.lights[sourceIndex].sourceName}') " +
                        "references a cookie";
                    return false;
                }
            }

            return EndfieldRecoveredLightCookieDataContract.TryValidateZeroCookieFrame(
                preparedLightCount,
                false,
                out failure);
        }

        private void EnsureZeroRetailLightCookieDataBuffer()
        {
            if (zeroRetailLightCookieDataBuffer != null)
                return;
            zeroRetailLightCookieDataBuffer = new ComputeBuffer(
                EndfieldRecoveredLightCookieDataContract.VectorCount,
                sizeof(float) * 4,
                ComputeBufferType.Constant)
            {
                name = "Endfield Recovered LightCookieData Zero-Cookie Fixture"
            };
            zeroRetailLightCookieDataBuffer.SetData(
                new Vector4[EndfieldRecoveredLightCookieDataContract.VectorCount]);
        }

        private void BindRetailConstantsFallback(CommandBuffer commandBuffer)
        {
            if (!retailConstantsRequested)
            {
                commandBuffer.SetGlobalFloat(RetailConstantsReadyId, 0.0f);
                return;
            }
            try
            {
                EnsureRetailConstantsBuffers();
                commandBuffer.SetGlobalConstantBuffer(
                    zeroRetailConstantsBuffer,
                    RetailConstantsId,
                    0,
                    EndfieldRecoveredLightBinningConstantsContract.SizeBytes);
                commandBuffer.SetGlobalConstantBuffer(
                    zeroRetailConstantsBuffer,
                    ExactDxbcBridgeConstantsId,
                    0,
                    EndfieldRecoveredLightBinningConstantsContract.SizeBytes);
            }
            catch (Exception exception)
            {
                ReportConstantsFailure(
                    "zero constant-buffer fallback failed: " + exception.Message);
            }
            commandBuffer.SetGlobalFloat(RetailConstantsReadyId, 0.0f);
        }

        private void BindRetailLightCookieDataFallback(CommandBuffer commandBuffer)
        {
            if (!retailLightCookieDataRequested)
            {
                commandBuffer.SetGlobalFloat(RetailLightCookieDataReadyId, 0.0f);
                return;
            }
            try
            {
                EnsureZeroRetailLightCookieDataBuffer();
                commandBuffer.SetGlobalConstantBuffer(
                    zeroRetailLightCookieDataBuffer,
                    RetailLightCookieDataId,
                    0,
                    EndfieldRecoveredLightCookieDataContract.SizeBytes);
                commandBuffer.SetGlobalConstantBuffer(
                    zeroRetailLightCookieDataBuffer,
                    ExactDxbcBridgeLightCookieDataId,
                    0,
                    EndfieldRecoveredLightCookieDataContract.SizeBytes);
                commandBuffer.SetGlobalTexture(
                    RetailLightCookieTextureId,
                    Texture2D.blackTexture);
            }
            catch (Exception exception)
            {
                ReportLightCookieDataFailure(
                    "zero LightCookieData fallback failed: " + exception.Message);
            }
            commandBuffer.SetGlobalFloat(RetailLightCookieDataReadyId, 0.0f);
        }

        internal static void PackRetailConstants(
            EndfieldRecoveredLightBinningConstantsContract.Data data,
            Vector4[] destination)
        {
            if (destination == null || destination.Length != 3)
                throw new ArgumentException(
                    "LightBinningConstants packing requires exactly three float4 values",
                    nameof(destination));
            destination[0] = new Vector4(
                BitConverter.Int32BitsToSingle(data.lightCount),
                BitConverter.Int32BitsToSingle(data.numTiles),
                BitConverter.Int32BitsToSingle(data.actualWidth),
                BitConverter.Int32BitsToSingle(data.actualHeight));
            destination[1] = new Vector4(
                data.tileSize,
                data.numTilesX,
                data.numTilesY,
                data.numSliceZ);
            destination[2] = new Vector4(
                data.nearClipPlane,
                data.farClipPlane,
                data.zBinSlice,
                data.invZBinSlice);
        }

        private void SetCommonComputeParameters(
            CommandBuffer commandBuffer,
            int lightCount,
            int tileCount,
            int width,
            int height,
            int tileCountX,
            int tileCountY,
            float nearClip,
            float farClip,
            Vector4 nearPlaneParams,
            int zOffset)
        {
            commandBuffer.SetComputeIntParam(compute, PunctualLightCountId, lightCount);
            commandBuffer.SetComputeIntParam(compute, NumTilesId, tileCount);
            commandBuffer.SetComputeIntParam(compute, ActualWidthId, width);
            commandBuffer.SetComputeIntParam(compute, ActualHeightId, height);
            commandBuffer.SetComputeFloatParam(compute, TileSizeId, TileSize);
            commandBuffer.SetComputeFloatParam(compute, NumTilesXId, tileCountX);
            commandBuffer.SetComputeFloatParam(compute, NumTilesYId, tileCountY);
            commandBuffer.SetComputeFloatParam(compute, NumSliceZId, SliceCount);
            commandBuffer.SetComputeFloatParam(compute, NearClipPlaneId, nearClip);
            commandBuffer.SetComputeFloatParam(compute, FarClipPlaneId, farClip);
            commandBuffer.SetComputeFloatParam(compute, ZBinSliceId, ZSliceSize);
            commandBuffer.SetComputeFloatParam(compute, InvZBinSliceId, 1.0f / ZSliceSize);
            commandBuffer.SetComputeVectorParam(compute, NearPlaneParamsId, nearPlaneParams);
            commandBuffer.SetComputeIntParam(compute, ZOffsetId, zOffset);
        }

        private bool EnsureBuffers(int requiredWordCount, out string failure)
        {
            failure = null;
            try
            {
                if (descriptorBuffer == null)
                {
                    descriptorBuffer = new ComputeBuffer(
                        EndfieldHGOperatorLightRig.DescriptorVectorCount,
                        sizeof(float) * 4,
                        ComputeBufferType.Structured)
                    {
                        name = "Endfield Recovered Light Culling Descriptors"
                    };
                }

                if (binningBuffer == null || binningBuffer.count < requiredWordCount)
                {
                    binningBuffer?.Release();
                    binningBuffer = new ComputeBuffer(
                        requiredWordCount,
                        sizeof(uint),
                        ComputeBufferType.Structured)
                    {
                        name = "Endfield Recovered Light XY/Z Membership"
                    };
                }
                return true;
            }
            catch (Exception exception)
            {
                failure = "GPU buffer allocation failed: " + exception.Message;
                descriptorBuffer?.Release();
                descriptorBuffer = null;
                binningBuffer?.Release();
                binningBuffer = null;
                return false;
            }
        }

        private void EnsureZeroFallbackBuffer()
        {
            if (zeroFallbackBuffer != null)
                return;
            try
            {
                zeroFallbackBuffer = new ComputeBuffer(
                    1,
                    sizeof(uint),
                    ComputeBufferType.Structured)
                {
                    name = "Endfield Recovered Light Membership Zero Fallback"
                };
                zeroFallbackBuffer.SetData(new uint[] { 0u });
            }
            catch (Exception exception)
            {
                zeroFallbackBuffer?.Release();
                zeroFallbackBuffer = null;
                ReportFailure("zero fallback buffer allocation failed: " + exception.Message);
            }
        }

        private void BindFallback(CommandBuffer commandBuffer)
        {
            EnsureZeroFallbackBuffer();
            if (zeroFallbackBuffer != null)
                commandBuffer.SetGlobalBuffer(BinningBufferId, zeroFallbackBuffer);
            commandBuffer.SetGlobalVector(GlobalLayoutId, new Vector4(1.0f, 1.0f, 1.0f, 0.0f));
            commandBuffer.SetGlobalVector(GlobalDepthId, new Vector4(0.0f, 1.0f, 1.0f, 0.0f));
            commandBuffer.SetGlobalFloat(GlobalAvailableId, 0.0f);
        }

        private void ReportFailure(string message)
        {
            if (loggedFailure)
                return;
            Debug.LogWarning(
                "Recovered isolated-rig light membership is falling back to the " +
                "existing direct source-light loop because " + message + ".");
            loggedFailure = true;
        }

        private void ReportConstantsFailure(string message)
        {
            if (loggedConstantsFailure)
                return;
            Debug.LogWarning(
                "Recovered _LightBinningConstants is disabled for this camera because " +
                message + ". The canonical binding is zeroed and its ready flag is false.");
            loggedConstantsFailure = true;
        }

        private void ReportLightCookieDataFailure(string message)
        {
            if (loggedLightCookieDataFailure)
                return;
            Debug.LogWarning(
                "Recovered _LightCookieData is disabled for this camera because " +
                message + ". The canonical binding is zeroed and its ready flag is false.");
            loggedLightCookieDataFailure = true;
        }

        private void ReportCanonicalBinningFailure(string message)
        {
            if (loggedCanonicalBinningFailure)
                return;
            Debug.LogWarning(
                "Recovered canonical _BinningBuffer remains disabled because " +
                message + ". Its ready flag is false and no canonical buffer is published.");
            loggedCanonicalBinningFailure = true;
        }

        private static bool ReadBooleanEnvironment(string name)
        {
            string value = Environment.GetEnvironmentVariable(name);
            return string.Equals(value, "1", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(value, "true", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(value, "yes", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(value, "on", StringComparison.OrdinalIgnoreCase);
        }

        private static bool HasCommandLineArgument(string argument)
        {
            foreach (string value in Environment.GetCommandLineArgs())
            {
                if (string.Equals(value, argument, StringComparison.OrdinalIgnoreCase))
                    return true;
            }
            return false;
        }

        public void Dispose()
        {
            if (disposed)
                return;
            disposed = true;
            descriptorBuffer?.Release();
            descriptorBuffer = null;
            binningBuffer?.Release();
            binningBuffer = null;
            canonicalBinningBuffer?.Release();
            canonicalBinningBuffer = null;
            canonicalPublicationValid = false;
            zeroFallbackBuffer?.Release();
            zeroFallbackBuffer = null;
            retailConstantsBuffer?.Release();
            retailConstantsBuffer = null;
            zeroRetailConstantsBuffer?.Release();
            zeroRetailConstantsBuffer = null;
            zeroRetailLightCookieDataBuffer?.Release();
            zeroRetailLightCookieDataBuffer = null;
        }
    }
}
