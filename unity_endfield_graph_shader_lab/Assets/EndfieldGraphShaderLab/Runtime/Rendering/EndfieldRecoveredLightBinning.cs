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
        private static readonly int RetailConstantsReadyId =
            Shader.PropertyToID("_EndfieldRecoveredLightBinningConstantsReady");
        private static readonly int RetailLightCookieDataId =
            Shader.PropertyToID("_LightCookieData");
        private static readonly int RetailLightCookieTextureId =
            Shader.PropertyToID("_LightCookie");
        private static readonly int RetailLightCookieDataReadyId =
            Shader.PropertyToID("_EndfieldRecoveredLightCookieDataReady");

        private readonly Vector4[] descriptors =
            new Vector4[EndfieldHGOperatorLightRig.DescriptorVectorCount];
        private readonly ComputeShader compute;
        private readonly bool retailConstantsRequested;
        private readonly bool retailLightCookieDataRequested;
        private readonly int xyKernel = -1;
        private readonly int zKernel = -1;
        private ComputeBuffer descriptorBuffer;
        private ComputeBuffer binningBuffer;
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
        private bool disposed;

        internal EndfieldRecoveredLightBinning()
        {
            retailConstantsRequested =
                ReadBooleanEnvironment(ConstantsEnvironmentVariable) ||
                HasCommandLineArgument(ConstantsCommandLineArgument);
            retailLightCookieDataRequested =
                ReadBooleanEnvironment(LightCookieDataEnvironmentVariable) ||
                HasCommandLineArgument(LightCookieDataCommandLineArgument);
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
            EnsureZeroFallbackBuffer();
        }

        internal void PrepareCamera(
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
                return;
            }
            if (camera.orthographic)
            {
                ReportFailure(
                    "orthographic cameras are outside the recovered perspective CharInfo contract");
                BindRetailConstantsFallback(commandBuffer);
                BindRetailLightCookieDataFallback(commandBuffer);
                BindFallback(commandBuffer);
                return;
            }

            PublishRetailConstants(
                commandBuffer,
                lightCount,
                width,
                height,
                camera.nearClipPlane,
                camera.farClipPlane);
            PublishRetailLightCookieData(
                commandBuffer,
                rig,
                lightCount);

            if (!SystemInfo.supportsComputeShaders)
            {
                ReportFailure("the active graphics device does not support compute shaders");
                BindFallback(commandBuffer);
                return;
            }
            if (compute == null || xyKernel < 0 || zKernel < 0)
            {
                ReportFailure(
                    $"Resources/{ComputeResourceName}.compute or its BuildXY/BuildZ kernels are unavailable");
                BindFallback(commandBuffer);
                return;
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
                return;
            }

            try
            {
                descriptorBuffer.SetData(descriptors);
            }
            catch (Exception exception)
            {
                ReportFailure("descriptor upload failed: " + exception.Message);
                BindFallback(commandBuffer);
                return;
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
        }

        private void PublishRetailConstants(
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
                return;
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
                return;
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
                commandBuffer.SetGlobalFloat(RetailConstantsReadyId, 1.0f);
            }
            catch (Exception exception)
            {
                ReportConstantsFailure(
                    "48-byte constant-buffer publication failed: " + exception.Message);
                BindRetailConstantsFallback(commandBuffer);
                return;
            }

            if (!loggedConstantsActivation)
            {
                Debug.Log(
                    "Recovered _LightBinningConstants publication active for the " +
                    "source-closed isolated Overview rig: " +
                    $"{data.lightCount} lights, {data.actualWidth}x{data.actualHeight}, " +
                    $"{data.numTilesX}x{data.numTilesY} tiles. This does not claim " +
                    "the unresolved retail whole-scene survivor list.");
                loggedConstantsActivation = true;
            }
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

        private void PublishRetailLightCookieData(
            CommandBuffer commandBuffer,
            EndfieldHGOperatorLightRig rig,
            int sourceClosedLightCount)
        {
            if (!retailLightCookieDataRequested)
            {
                commandBuffer.SetGlobalFloat(RetailLightCookieDataReadyId, 0.0f);
                return;
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
                return;
            }

            if (!loggedLightCookieDataActivation)
            {
                Debug.Log(
                    "Recovered _LightCookieData publication active for the source-closed " +
                    $"zero-cookie isolated Overview rig ({sourceClosedLightCount} lights). " +
                    "The exact 2,560-byte binding is zero and _LightCookie is unobserved " +
                    "because every packed cookie index is -1. This does not claim the " +
                    "retail whole-scene cookie atlas.");
                loggedLightCookieDataActivation = true;
            }
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
            else
            {
                failure =
                    $"actor identity '{(rig.actorRoot != null ? rig.actorRoot.name : "<null>")}' " +
                    "is outside the source-closed Wulfa/Zhuangfy Overview fixtures";
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
