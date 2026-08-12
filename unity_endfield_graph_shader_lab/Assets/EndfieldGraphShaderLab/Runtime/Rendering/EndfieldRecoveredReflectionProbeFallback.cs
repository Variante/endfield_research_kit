using System;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Owns the binary-derived no-local-probe reflection resources required by
    /// the selected original deferred resolver. The compatibility pipeline
    /// constructs it, but publication remains gated by the default-off exact
    /// canonical-binning path and fails closed before pass-0 activation.
    /// </summary>
    public sealed class EndfieldRecoveredReflectionProbeFallback : IDisposable
    {
        private const string ComputeResourceName =
            "EndfieldRecoveredReflectionProbeOct";
        private const string KernelName =
            "SampleOneTextureMip4AndNotReadSrc";

        private const int TileSize = 32;
        private const int LightSliceCount = 2048;
        private const int LightWordsPerBin = 8;
        private const int ReflectionSliceCount = 1024;
        private const int ReflectionWordsPerBin = 1;

        private const int OctWorkingSize = 512;
        private const int OctPadding = 32;
        private const int OctPhysicalSize =
            OctWorkingSize + OctPadding * 2;
        private const int OctSliceCount = 32;
        private const int OctDestinationSlice = 0;
        private const int GlobalBufferBytes = 4160;
        private const int GlobalBufferVectorCount =
            GlobalBufferBytes / (sizeof(float) * 4);

        // Exact Rec.709 projection of the serialized CharInfo
        // HGEnvironmentPhase.skyConfig.skyAmbientSH coefficients 3,2,1,0.
        private static readonly Vector4 CharInfoSkyL1Luminance =
            new Vector4(
                -0.0075507620349526405f,
                0.01217081118375063f,
                0.47223734855651855f,
                1.0963057279586792f);

        private static readonly int Cubemap0Id =
            Shader.PropertyToID("Cubemap0");
        private static readonly int OctTextureMip0Id =
            Shader.PropertyToID("_OctTextureMip0");
        private static readonly int OctTextureMip1Id =
            Shader.PropertyToID("_OctTextureMip1");
        private static readonly int OctTextureMip2Id =
            Shader.PropertyToID("_OctTextureMip2");
        private static readonly int OctTextureMip3Id =
            Shader.PropertyToID("_OctTextureMip3");
        private static readonly int BlendParam0Id =
            Shader.PropertyToID("_ReflectionProbeBlendParam0");
        private static readonly int BlendParam1Id =
            Shader.PropertyToID("_ReflectionProbeBlendParam1");
        private static readonly int BlendParam2Id =
            Shader.PropertyToID("_ReflectionProbeBlendParam2");
        private static readonly int BlendParam3Id =
            Shader.PropertyToID("_ReflectionProbeBlendParam3");

        private static readonly int ReflectionOctTextureArrayId =
            Shader.PropertyToID("_ReflectionProbeOctTextureArray");
        private static readonly int ReflectionGlobalDataId =
            Shader.PropertyToID("ReflectionProbeGlobalData");
        private static readonly int ExactDxbcBridgeGlobalDataId =
            Shader.PropertyToID("EndfieldCB2");
        private static readonly int BinningBufferId =
            Shader.PropertyToID("_BinningBuffer");
        private static readonly int BinningBufferOffsetsId =
            Shader.PropertyToID("_BinningBufferOffsets");
        private static readonly int ReadyId =
            Shader.PropertyToID("_EndfieldRecoveredReflectionProbeFallbackReady");

        private readonly Vector4[] globalData =
            new Vector4[GlobalBufferVectorCount];
        private readonly ComputeShader compute;
        private readonly int kernel = -1;

        private RenderTexture octTextureArray;
        private ComputeBuffer reflectionGlobalData;
        private ComputeBuffer zeroBinningBuffer;
        private uint[] zeroBinningWords;
        private Cubemap populatedSource;
        private bool octDispatchRecorded;
        private bool publicationValid;
        private int publicationCameraInstanceId;
        private int publicationFrame;
        private int publicationWidth;
        private int publicationHeight;
        private bool disposed;

        public EndfieldRecoveredReflectionProbeFallback()
        {
            compute = Resources.Load<ComputeShader>(ComputeResourceName);
            if (compute != null)
            {
                try
                {
                    kernel = compute.FindKernel(KernelName);
                }
                catch (Exception exception)
                {
                    Debug.LogWarning(
                        "Recovered reflection fallback could not resolve " +
                        $"{KernelName}: {exception.Message}");
                }
            }
        }

        internal bool PrepareAndPublishDiagnostic(
            Camera camera,
            int width,
            int height,
            Cubemap source,
            CommandBuffer commandBuffer,
            out string failure)
        {
            return PrepareAndPublishRecoveredResources(
                camera,
                width,
                height,
                source,
                commandBuffer,
                true,
                out failure);
        }

        internal ComputeBuffer CurrentGlobalDataBuffer => reflectionGlobalData;

        public bool PrepareAndPublishRecoveredResources(
            Camera camera,
            int width,
            int height,
            Cubemap source,
            CommandBuffer commandBuffer,
            bool publishLegacyZeroBinningBuffer,
            out string failure)
        {
            failure = null;
            if (disposed)
                throw new ObjectDisposedException(
                    nameof(EndfieldRecoveredReflectionProbeFallback));
            if (camera == null)
                throw new ArgumentNullException(nameof(camera));
            if (commandBuffer == null)
                throw new ArgumentNullException(nameof(commandBuffer));
            commandBuffer.SetGlobalFloat(ReadyId, 0.0f);
            publicationValid = false;
            if (source == null)
            {
                failure = "the exact T_hdri_env_char_01 Cubemap is not bound";
                return false;
            }
            if (camera.orthographic)
            {
                failure =
                    "orthographic cameras are outside the recovered CharInfo contract";
                return false;
            }
            if (!SystemInfo.supportsComputeShaders)
            {
                failure = "the active graphics device does not support compute";
                return false;
            }
            if (compute == null || kernel < 0)
            {
                failure =
                    $"Resources/{ComputeResourceName}.compute is unavailable";
                return false;
            }
            if (!string.Equals(
                    source.name,
                    "T_hdri_env_char_01",
                    StringComparison.Ordinal))
            {
                failure =
                    "the source Cubemap is not the exact T_hdri_env_char_01 asset";
                return false;
            }
            if (source.width != 128 ||
                source.height != 128 ||
                source.mipmapCount != 8 ||
                source.format != TextureFormat.BC6H)
            {
                failure =
                    "the source is not the recovered 128x128 BC6H eight-mip Cubemap";
                return false;
            }

            width = Mathf.Max(width, 1);
            height = Mathf.Max(height, 1);
            int tileX = (width + TileSize - 1) / TileSize;
            int tileY = (height + TileSize - 1) / TileSize;
            int tileCount = tileX * tileY;
            int lightWordCount =
                (tileCount + LightSliceCount) * LightWordsPerBin;
            int reflectionWordCount =
                (tileCount + ReflectionSliceCount) *
                ReflectionWordsPerBin;
            int combinedWordCount = lightWordCount + reflectionWordCount;
            int reflectionXYOffset = lightWordCount;
            int reflectionZOffset = reflectionXYOffset + tileCount;

            try
            {
                EnsureOctTexture();
                EnsureGlobalBuffer();
                EnsureZeroBinningBuffer(combinedWordCount);
            }
            catch (Exception exception)
            {
                failure = "resource allocation failed: " + exception.Message;
                return false;
            }

            if (populatedSource != source || !octDispatchRecorded)
            {
                RecordOctDispatch(commandBuffer, source);
                populatedSource = source;
                octDispatchRecorded = true;
            }

            float nearClip = camera.nearClipPlane;
            float nearHeight = 2.0f * nearClip * Mathf.Tan(
                camera.fieldOfView * 0.5f * Mathf.Deg2Rad);
            float nearWidth = nearHeight * camera.aspect;
            float tileHeightAtNear = nearHeight * TileSize / tileY;

            Array.Clear(globalData, 0, globalData.Length);
            globalData[0] = new Vector4(
                tileX,
                tileY,
                tileCount,
                1.0f / TileSize);
            globalData[1] = new Vector4(
                ReflectionSliceCount,
                1.0f,
                1.0f,
                (float)OctWorkingSize / OctPhysicalSize);
            // Native HGReflectionProbe.UpdateViewCBHandle overwrites Param2.x
            // with the local-probe count. The isolated CharInfo fallback has
            // no local records, so x is exactly zero.
            globalData[2] = new Vector4(
                0.0f,
                nearHeight,
                tileHeightAtNear,
                (float)OctPadding / OctPhysicalSize);
            globalData[3] = CharInfoSkyL1Luminance;
            reflectionGlobalData.SetData(globalData);

            commandBuffer.SetGlobalTexture(
                ReflectionOctTextureArrayId,
                octTextureArray);
            commandBuffer.SetGlobalConstantBuffer(
                reflectionGlobalData,
                ReflectionGlobalDataId,
                0,
                GlobalBufferBytes);
            // The selected installed D3D11 fallback resolver addresses this
            // same source buffer as b2 and reads only vectors c0..c258.
            commandBuffer.SetGlobalConstantBuffer(
                reflectionGlobalData,
                ExactDxbcBridgeGlobalDataId,
                0,
                259 * sizeof(float) * 4);
            if (publishLegacyZeroBinningBuffer)
            {
                commandBuffer.SetGlobalBuffer(
                    BinningBufferId,
                    zeroBinningBuffer);
                commandBuffer.SetGlobalVector(
                    BinningBufferOffsetsId,
                    new Vector4(
                        0.0f,
                        tileCount * LightWordsPerBin,
                        reflectionXYOffset,
                        reflectionZOffset));
            }
            commandBuffer.SetGlobalFloat(ReadyId, 1.0f);
            publicationValid = true;
            publicationCameraInstanceId = camera.GetInstanceID();
            publicationFrame = Time.frameCount;
            publicationWidth = width;
            publicationHeight = height;
            return true;
        }

        internal void ResetPublication(CommandBuffer commandBuffer)
        {
            if (commandBuffer == null)
                throw new ArgumentNullException(nameof(commandBuffer));
            publicationValid = false;
            commandBuffer.SetGlobalFloat(ReadyId, 0.0f);
        }

        internal bool TryGetCurrentPublication(
            Camera camera,
            int width,
            int height,
            out RenderTexture publishedTexture)
        {
            publishedTexture = null;
            if (!publicationValid ||
                camera == null ||
                publicationCameraInstanceId != camera.GetInstanceID() ||
                publicationFrame != Time.frameCount ||
                publicationWidth != width ||
                publicationHeight != height ||
                octTextureArray == null ||
                !octTextureArray.IsCreated())
            {
                return false;
            }
            publishedTexture = octTextureArray;
            return true;
        }

        private void EnsureOctTexture()
        {
            if (octTextureArray != null && octTextureArray.IsCreated())
                return;
            ReleaseOctTexture();
            var descriptor = new RenderTextureDescriptor(
                OctPhysicalSize,
                OctPhysicalSize,
                GraphicsFormat.R16G16B16A16_SFloat,
                0)
            {
                dimension = TextureDimension.Tex2DArray,
                volumeDepth = OctSliceCount,
                msaaSamples = 1,
                sRGB = false,
                useMipMap = true,
                autoGenerateMips = false,
                enableRandomWrite = true,
                mipCount = 0
            };
            octTextureArray = new RenderTexture(descriptor)
            {
                name = "Endfield Recovered Reflection Probe Oct Array",
                hideFlags = HideFlags.HideAndDontSave,
                filterMode = FilterMode.Bilinear,
                wrapMode = TextureWrapMode.Clamp
            };
            if (!octTextureArray.Create())
                throw new InvalidOperationException(
                    "could not create the 576x576x32 RGBAHalf oct array");
            octDispatchRecorded = false;
            populatedSource = null;
            publicationValid = false;
        }

        private void EnsureGlobalBuffer()
        {
            if (reflectionGlobalData != null)
                return;
            reflectionGlobalData = new ComputeBuffer(
                GlobalBufferVectorCount,
                sizeof(float) * 4,
                ComputeBufferType.Constant)
            {
                name = "Endfield Recovered ReflectionProbeGlobalData"
            };
        }

        private void EnsureZeroBinningBuffer(int wordCount)
        {
            if (zeroBinningBuffer != null &&
                zeroBinningBuffer.count == wordCount)
            {
                return;
            }
            zeroBinningBuffer?.Release();
            zeroBinningBuffer = null;
            zeroBinningWords = new uint[wordCount];
            zeroBinningBuffer = new ComputeBuffer(
                wordCount,
                sizeof(uint),
                ComputeBufferType.Raw)
            {
                name =
                    "Endfield Recovered Combined Light/Reflection Zero Binning"
            };
            zeroBinningBuffer.SetData(zeroBinningWords);
        }

        private void RecordOctDispatch(
            CommandBuffer commandBuffer,
            Cubemap source)
        {
            RecordOctDispatch(
                commandBuffer,
                source,
                0,
                OctWorkingSize,
                OctPadding,
                32,
                0);
            RecordOctDispatch(
                commandBuffer,
                source,
                4,
                OctWorkingSize >> 4,
                OctPadding >> 4,
                2,
                4);
        }

        private void RecordOctDispatch(
            CommandBuffer commandBuffer,
            Cubemap source,
            int sourceMip,
            int size,
            int padding,
            int groups,
            int destinationMipBase)
        {
            commandBuffer.SetComputeTextureParam(
                compute,
                kernel,
                Cubemap0Id,
                source);
            commandBuffer.SetComputeTextureParam(
                compute,
                kernel,
                OctTextureMip0Id,
                octTextureArray,
                destinationMipBase + 0);
            commandBuffer.SetComputeTextureParam(
                compute,
                kernel,
                OctTextureMip1Id,
                octTextureArray,
                destinationMipBase + 1);
            commandBuffer.SetComputeTextureParam(
                compute,
                kernel,
                OctTextureMip2Id,
                octTextureArray,
                destinationMipBase + 2);
            commandBuffer.SetComputeTextureParam(
                compute,
                kernel,
                OctTextureMip3Id,
                octTextureArray,
                destinationMipBase + 3);
            commandBuffer.SetComputeVectorParam(
                compute,
                BlendParam0Id,
                new Vector4(size, size, 1.0f / size, 1.0f / size));
            commandBuffer.SetComputeVectorParam(
                compute,
                BlendParam1Id,
                new Vector4(
                    sourceMip,
                    OctDestinationSlice,
                    padding,
                    0.0f));
            commandBuffer.SetComputeVectorParam(
                compute,
                BlendParam2Id,
                Vector4.zero);
            commandBuffer.SetComputeVectorParam(
                compute,
                BlendParam3Id,
                Vector4.zero);
            commandBuffer.DispatchCompute(
                compute,
                kernel,
                groups,
                groups,
                1);
        }

        private void ReleaseOctTexture()
        {
            if (octTextureArray == null)
                return;
            octTextureArray.Release();
            UnityEngine.Object.DestroyImmediate(octTextureArray);
            octTextureArray = null;
        }

        public void Dispose()
        {
            if (disposed)
                return;
            disposed = true;
            publicationValid = false;
            ReleaseOctTexture();
            reflectionGlobalData?.Release();
            reflectionGlobalData = null;
            zeroBinningBuffer?.Release();
            zeroBinningBuffer = null;
            zeroBinningWords = null;
            populatedSource = null;
            octDispatchRecorded = false;
        }
    }
}
