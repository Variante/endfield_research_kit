using System;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Replays the installed HGPunctualLightShadowManagerV2 constructor-default
    /// atlas request on the pinned Unity/D3D12 backend. This closes descriptor
    /// resolution only; it does not substitute for target-frame depth texels.
    /// </summary>
    public static class EndfieldPunctualShadowAtlasDescriptorBatchProbe
    {
        private const string OutputEnvironment =
            "ENDFIELD_PUNCTUAL_SHADOW_ATLAS_PROBE_OUTPUT";
        private const string ShaderName =
            "Hidden/Endfield/HGRPCompat/DefaultShadowTextureProbe";
        private const int Width = 3072;
        private const int Height = 2048;
        private const int RequestedDepthBits = 16;
        private const int RequestedColorFormatNumeric = 4;
        private static readonly int ShadowTextureId =
            Shader.PropertyToID("_EndfieldDefaultShadowProbeTexture");

        [Serializable]
        private sealed class Sample
        {
            public string mode;
            public float clearDepth;
            public float rawDepth;
            public float expectedStoredDepth;
            public float expectedD16Depth;
            public float absoluteD16Error;
            public float compareZero;
            public float compareHalf;
            public float compareOne;
        }

        [Serializable]
        private sealed class Report
        {
            public string schema;
            public string unityVersion;
            public string graphicsDeviceType;
            public bool usesReversedZBuffer;
            public int width;
            public int height;
            public int requestedDepthBufferBits;
            public string requestedColorFormat;
            public int requestedColorFormatNumeric;
            public string actualGraphicsFormat;
            public string actualDepthStencilFormat;
            public int actualDepthBufferBits;
            public string shadowSamplingMode;
            public string filterMode;
            public string wrapMode;
            public bool d16RenderSupported;
            public bool d16GenericSampleSupportQuery;
            public bool depthSubElementSamplingExecuted;
            public bool descriptorMatches;
            public bool reversedZEndpointsMatch;
            public bool d16QuantizationMatches;
            public Sample[] samples;
        }

        [MenuItem(
            "Endfield/Character Recovery Lab/Probe Punctual Shadow Atlas Descriptor")]
        public static void Probe()
        {
            string outputRoot =
                Environment.GetEnvironmentVariable(OutputEnvironment);
            if (string.IsNullOrWhiteSpace(outputRoot))
            {
                throw new InvalidOperationException(
                    OutputEnvironment +
                    " must name an explicit output directory.");
            }
            outputRoot = Path.GetFullPath(outputRoot);
            Directory.CreateDirectory(outputRoot);

            Shader shader = Shader.Find(ShaderName);
            if (shader == null || !shader.isSupported)
            {
                throw new InvalidOperationException(
                    "Punctual-shadow descriptor probe shader is missing or unsupported.");
            }

            var material = new Material(shader)
            {
                name = "Punctual Shadow Atlas Descriptor Probe",
                hideFlags = HideFlags.HideAndDontSave
            };
            RenderTexture witness = null;
            try
            {
                witness = CreateAtlas("descriptor-witness");
                Sample clearZero = ReadControlledSample(
                    material,
                    0.0f,
                    "unity-clear-api-depth-0");
                Sample clearOne = ReadControlledSample(
                    material,
                    1.0f,
                    "unity-clear-api-depth-1");
                Sample quantized = ReadControlledSample(
                    material,
                    0.1234567f,
                    "unity-clear-api-depth-0.1234567");

                bool descriptorMatches =
                    witness.width == Width &&
                    witness.height == Height &&
                    witness.depthStencilFormat == GraphicsFormat.D16_UNorm &&
                    witness.depth == RequestedDepthBits &&
                    witness.descriptor.shadowSamplingMode ==
                        ShadowSamplingMode.CompareDepths &&
                    witness.filterMode == FilterMode.Point &&
                    witness.wrapMode == TextureWrapMode.Clamp &&
                    witness.descriptor.msaaSamples == 1 &&
                    !witness.descriptor.useMipMap &&
                    !witness.descriptor.autoGenerateMips &&
                    !witness.descriptor.enableRandomWrite &&
                    !witness.descriptor.bindMS;
                bool endpointsMatch =
                    Mathf.Abs(clearZero.rawDepth - 1.0f) <= 0.00001f &&
                    Mathf.Abs(clearOne.rawDepth) <= 0.00001f &&
                    clearOne.compareHalf > 0.9999f &&
                    clearOne.compareOne > 0.9999f;
                bool quantizationMatches =
                    quantized.absoluteD16Error <= 0.000002f;

                var report = new Report
                {
                    schema = "endfield-punctual-shadow-atlas-descriptor-probe-v1",
                    unityVersion = Application.unityVersion,
                    graphicsDeviceType = SystemInfo.graphicsDeviceType.ToString(),
                    usesReversedZBuffer = SystemInfo.usesReversedZBuffer,
                    width = witness.width,
                    height = witness.height,
                    requestedDepthBufferBits = RequestedDepthBits,
                    requestedColorFormat =
                        ((GraphicsFormat)RequestedColorFormatNumeric).ToString(),
                    requestedColorFormatNumeric = RequestedColorFormatNumeric,
                    actualGraphicsFormat = witness.graphicsFormat.ToString(),
                    actualDepthStencilFormat = witness.depthStencilFormat.ToString(),
                    actualDepthBufferBits = witness.depth,
                    shadowSamplingMode =
                        witness.descriptor.shadowSamplingMode.ToString(),
                    filterMode = witness.filterMode.ToString(),
                    wrapMode = witness.wrapMode.ToString(),
                    d16RenderSupported = SystemInfo.IsFormatSupported(
                        GraphicsFormat.D16_UNorm,
                        FormatUsage.Render),
                    d16GenericSampleSupportQuery = SystemInfo.IsFormatSupported(
                        GraphicsFormat.D16_UNorm,
                        FormatUsage.Sample),
                    depthSubElementSamplingExecuted =
                        endpointsMatch && quantizationMatches,
                    descriptorMatches = descriptorMatches,
                    reversedZEndpointsMatch = endpointsMatch,
                    d16QuantizationMatches = quantizationMatches,
                    samples = new[] { clearZero, clearOne, quantized }
                };
                string reportPath = Path.Combine(
                    outputRoot,
                    "punctual_shadow_atlas_descriptor_probe.json");
                File.WriteAllText(
                    reportPath,
                    JsonUtility.ToJson(report, true) + Environment.NewLine);
                Debug.Log(
                    "Punctual-shadow atlas descriptor probe wrote " +
                    reportPath + ": actual=" +
                    report.actualDepthStencilFormat + ", descriptorMatches=" +
                    descriptorMatches + ", reversedZEndpointsMatch=" +
                    endpointsMatch + ", d16QuantizationMatches=" +
                    quantizationMatches + ".");

                if (report.unityVersion != "2022.3.62f3" ||
                    report.graphicsDeviceType != "Direct3D12" ||
                    !report.usesReversedZBuffer ||
                    !report.d16RenderSupported ||
                    !descriptorMatches ||
                    !endpointsMatch ||
                    !quantizationMatches)
                {
                    throw new InvalidOperationException(
                        "Punctual-shadow atlas descriptor probe did not close " +
                        "the pinned Unity 2022.3.62f3 D3D12 contract.");
                }
            }
            finally
            {
                DestroyTexture(witness);
                UnityEngine.Object.DestroyImmediate(material);
            }
        }

        private static Sample ReadControlledSample(
            Material material,
            float clearDepth,
            string mode)
        {
            RenderTexture shadow = CreateAtlas(mode);
            try
            {
                var commandBuffer = new CommandBuffer
                {
                    name = "Clear punctual-shadow descriptor probe"
                };
                try
                {
                    commandBuffer.SetRenderTarget(shadow);
                    commandBuffer.ClearRenderTarget(
                        true,
                        false,
                        Color.black,
                        clearDepth);
                    Graphics.ExecuteCommandBuffer(commandBuffer);
                }
                finally
                {
                    commandBuffer.Release();
                }
                return ReadSample(material, shadow, clearDepth, mode);
            }
            finally
            {
                DestroyTexture(shadow);
            }
        }

        private static RenderTexture CreateAtlas(string suffix)
        {
            var descriptor = new RenderTextureDescriptor(Width, Height)
            {
                graphicsFormat = (GraphicsFormat)RequestedColorFormatNumeric,
                depthBufferBits = RequestedDepthBits,
                msaaSamples = 1,
                volumeDepth = 1,
                dimension = TextureDimension.Tex2D,
                sRGB = false,
                useMipMap = false,
                autoGenerateMips = false,
                enableRandomWrite = false,
                bindMS = false,
                memoryless = RenderTextureMemoryless.None,
                shadowSamplingMode = ShadowSamplingMode.CompareDepths
            };
            var shadow = new RenderTexture(descriptor)
            {
                name = "Punctual Shadowmap Probe " + suffix,
                hideFlags = HideFlags.HideAndDontSave,
                filterMode = FilterMode.Point,
                wrapMode = TextureWrapMode.Clamp,
                anisoLevel = 1,
                mipMapBias = 0.0f
            };
            if (!shadow.Create())
            {
                UnityEngine.Object.DestroyImmediate(shadow);
                throw new InvalidOperationException(
                    "Could not create the 3072x2048 comparison-depth atlas.");
            }
            return shadow;
        }

        private static Sample ReadSample(
            Material material,
            RenderTexture shadow,
            float clearDepth,
            string mode)
        {
            var outputDescriptor = new RenderTextureDescriptor(
                1,
                1,
                GraphicsFormat.R32G32B32A32_SFloat,
                0)
            {
                msaaSamples = 1,
                sRGB = false,
                useMipMap = false,
                autoGenerateMips = false,
                enableRandomWrite = false
            };
            var output = new RenderTexture(outputDescriptor)
            {
                name = "Punctual Shadow Atlas Probe Output",
                hideFlags = HideFlags.HideAndDontSave,
                filterMode = FilterMode.Point,
                wrapMode = TextureWrapMode.Clamp
            };
            try
            {
                if (!output.Create())
                {
                    throw new InvalidOperationException(
                        "Could not create the punctual-shadow probe readback target.");
                }
                var commandBuffer = new CommandBuffer
                {
                    name = "Sample punctual-shadow comparison texture"
                };
                try
                {
                    commandBuffer.SetGlobalTexture(
                        ShadowTextureId,
                        new RenderTargetIdentifier(shadow),
                        RenderTextureSubElement.Depth);
                    commandBuffer.SetRenderTarget(output);
                    commandBuffer.DrawProcedural(
                        Matrix4x4.identity,
                        material,
                        0,
                        MeshTopology.Triangles,
                        3,
                        1);
                    Graphics.ExecuteCommandBuffer(commandBuffer);
                }
                finally
                {
                    commandBuffer.Release();
                }

                AsyncGPUReadbackRequest request =
                    AsyncGPUReadback.Request(output, 0);
                request.WaitForCompletion();
                if (request.hasError)
                {
                    throw new InvalidOperationException(
                        "Punctual-shadow descriptor GPU readback failed.");
                }
                Vector4 value = request.GetData<Vector4>()[0];
                float expectedStored = 1.0f - clearDepth;
                float expectedD16 =
                    Mathf.Round(expectedStored * 65535.0f) / 65535.0f;
                return new Sample
                {
                    mode = mode,
                    clearDepth = clearDepth,
                    rawDepth = value.x,
                    expectedStoredDepth = expectedStored,
                    expectedD16Depth = expectedD16,
                    absoluteD16Error = Mathf.Abs(value.x - expectedD16),
                    compareZero = value.y,
                    compareHalf = value.z,
                    compareOne = value.w
                };
            }
            finally
            {
                DestroyTexture(output);
            }
        }

        private static void DestroyTexture(RenderTexture texture)
        {
            if (texture == null)
                return;
            texture.Release();
            UnityEngine.Object.DestroyImmediate(texture);
        }
    }
}
