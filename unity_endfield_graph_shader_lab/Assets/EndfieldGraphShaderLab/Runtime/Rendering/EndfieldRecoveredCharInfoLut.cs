using System;
using System.Security.Cryptography;
using Unity.Collections;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Owns the offline-recovered CharInfo 32x32x32 grade flattened into the
    /// original 1024x32 linear RGBAHalf render target.
    /// </summary>
    internal sealed class EndfieldRecoveredCharInfoLut : IDisposable
    {
        public const int Size = 32;
        public const int Width = Size * Size;
        public const int Height = Size;

        private const string BuilderShaderName =
            "Hidden/Endfield/HGRPCompat/RecoveredCharInfoLutBuilder2D";
        private const string ExactEndminfResource =
            "EndfieldCharInfo/EndminfCharInfoLut1024x32Rgba16f";
        private const int ExactEndminfByteLength = Width * Height * 8;
        private const string ExactEndminfSha256 =
            "717c1d483662c00abe55e1c56a9d024f45e5c84c430ed9dd2854cb386f372482";
        private const string ExactEndminfValidationPass =
            "VERIFY_EXACT_ENDMINF_LUT_SENTINELS";
        private static readonly byte[] ExactEndminfGpuSentinels =
        {
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x3c,
            0x00, 0x3c, 0x9d, 0x3a, 0xb0, 0x30, 0x00, 0x3c,
            0xe7, 0x3b, 0x00, 0x3c, 0x48, 0x3b, 0x00, 0x3c,
            0x00, 0x3c, 0x35, 0x35, 0x6b, 0x3b, 0x00, 0x3c,
            0x00, 0x3c, 0xff, 0x3b, 0xfd, 0x3b, 0x00, 0x3c,
        };

        private readonly Material builderMaterial;
        private RenderTexture texture;
        private Texture2D exactEndminfTexture;
        private RenderTexture exactEndminfValidationTarget;
        private bool buildQueued;
        private bool exactEndminfLoadAttempted;
        private bool exactEndminfGpuValidationQueued;
        private bool exactEndminfGpuValidationComplete;
        private bool exactEndminfGpuValidated;
        private string exactEndminfFailure = string.Empty;

        public EndfieldRecoveredCharInfoLut()
        {
            Shader builderShader = Shader.Find(BuilderShaderName);
            if (builderShader == null || !builderShader.isSupported)
            {
                Debug.LogWarning(
                    $"Recovered CharInfo LUT builder is unavailable: {BuilderShaderName}");
                return;
            }

            builderMaterial = new Material(builderShader)
            {
                hideFlags = HideFlags.HideAndDontSave,
                name = "Endfield Recovered CharInfo LUT Builder"
            };
        }

        public Texture Texture => texture;

        public Texture ExactEndminfTexture => exactEndminfTexture;

        public string ExactEndminfFailure => exactEndminfFailure;

        public bool ExactEndminfGpuValidationPending =>
            exactEndminfGpuValidationQueued;

        public bool ExactEndminfGpuValidated => exactEndminfGpuValidated;

        public string ExactEndminfSha => ExactEndminfSha256;

        public bool EnqueueExactEndminfGpuValidation(CommandBuffer commandBuffer)
        {
            if (exactEndminfGpuValidated)
                return true;
            if (exactEndminfGpuValidationComplete ||
                exactEndminfGpuValidationQueued)
                return false;
            if (commandBuffer == null)
                return FailExactEndminf("GPU validation command buffer is absent");
            if (SystemInfo.graphicsDeviceType != GraphicsDeviceType.Direct3D11)
                return FailExactEndminf("GPU validation requires Direct3D11");
            if (!SystemInfo.supportsAsyncGPUReadback)
                return FailExactEndminf("GPU validation requires AsyncGPUReadback");
            if (!EnsureExactEndminfTexture())
                return false;
            int pass = builderMaterial == null
                ? -1
                : builderMaterial.FindPass(ExactEndminfValidationPass);
            if (pass < 0)
                return FailExactEndminf("GPU sentinel validation pass is unavailable");
            EnsureExactEndminfValidationTarget();
            if (exactEndminfValidationTarget == null ||
                !exactEndminfValidationTarget.IsCreated())
                return FailExactEndminf("GPU sentinel target is unavailable");

            builderMaterial.SetTexture("_ExactEndminfLut", exactEndminfTexture);
            commandBuffer.BeginSample("Validate exact Endminf CharInfo LUT");
            commandBuffer.SetRenderTarget(exactEndminfValidationTarget);
            commandBuffer.SetViewport(new Rect(0.0f, 0.0f, 5.0f, 1.0f));
            commandBuffer.DrawProcedural(
                Matrix4x4.identity,
                builderMaterial,
                pass,
                MeshTopology.Triangles,
                3,
                1);
            commandBuffer.RequestAsyncReadback(
                exactEndminfValidationTarget,
                0,
                CompleteExactEndminfGpuValidation);
            commandBuffer.EndSample("Validate exact Endminf CharInfo LUT");
            exactEndminfGpuValidationQueued = true;
            return false;
        }

        /// <summary>
        /// Loads the exact captured Endminf CharInfo t2 resource without any
        /// importer color conversion or row/channel transformation. This is
        /// intentionally separate from the procedural compatibility LUT.
        /// </summary>
        public bool EnsureExactEndminfTexture()
        {
            if (exactEndminfTexture != null)
                return true;
            if (exactEndminfLoadAttempted)
                return false;
            exactEndminfLoadAttempted = true;

            TextAsset source = Resources.Load<TextAsset>(ExactEndminfResource);
            if (source == null)
                return FailExactEndminf("captured raw LUT resource is absent");
            byte[] payload = source.bytes;
            if (payload == null || payload.Length != ExactEndminfByteLength)
            {
                return FailExactEndminf(
                    "captured raw LUT length drifted: expected " +
                    ExactEndminfByteLength + ", got " +
                    (payload == null ? 0 : payload.Length));
            }

            if (exactEndminfValidationTarget != null)
            {
                exactEndminfValidationTarget.Release();
                DestroyResource(exactEndminfValidationTarget);
                exactEndminfValidationTarget = null;
            }
            string payloadHash;
            using (SHA256 sha = SHA256.Create())
            {
                payloadHash = BitConverter.ToString(sha.ComputeHash(payload))
                    .Replace("-", string.Empty)
                    .ToLowerInvariant();
            }
            if (!string.Equals(
                    payloadHash,
                    ExactEndminfSha256,
                    StringComparison.Ordinal))
            {
                return FailExactEndminf(
                    "captured raw LUT hash drifted: expected " +
                    ExactEndminfSha256 + ", got " + payloadHash);
            }
            if (!HasSentinel(payload, 0, 0,
                    new byte[] { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x3c }) ||
                !HasSentinel(payload, 31, 0,
                    new byte[] { 0x00, 0x3c, 0x9d, 0x3a, 0xb0, 0x30, 0x00, 0x3c }) ||
                !HasSentinel(payload, 0, 31,
                    new byte[] { 0xe7, 0x3b, 0x00, 0x3c, 0x48, 0x3b, 0x00, 0x3c }) ||
                !HasSentinel(payload, 992, 0,
                    new byte[] { 0x00, 0x3c, 0x35, 0x35, 0x6b, 0x3b, 0x00, 0x3c }) ||
                !HasSentinel(payload, 1023, 31,
                    new byte[] { 0x00, 0x3c, 0xff, 0x3b, 0xfd, 0x3b, 0x00, 0x3c }))
            {
                return FailExactEndminf(
                    "captured raw LUT orientation/channel sentinels drifted");
            }
            GraphicsFormat format = GraphicsFormat.R16G16B16A16_SFloat;
            if (!SystemInfo.IsFormatSupported(format, FormatUsage.Sample))
            {
                return FailExactEndminf(
                    "captured RGBA16F LUT sampling is unsupported");
            }
            try
            {
                exactEndminfTexture = new Texture2D(
                    Width,
                    Height,
                    format,
                    TextureCreationFlags.None)
                {
                    hideFlags = HideFlags.HideAndDontSave,
                    name = "Endminf Exact Captured CharInfo LUT 1024x32 RGBAHalf",
                    filterMode = FilterMode.Bilinear,
                    wrapMode = TextureWrapMode.Clamp,
                    anisoLevel = 0,
                };
                if (exactEndminfTexture.graphicsFormat != format ||
                    exactEndminfTexture.mipmapCount != 1)
                {
                    DestroyResource(exactEndminfTexture);
                    exactEndminfTexture = null;
                    return FailExactEndminf(
                        "captured raw LUT texture descriptor drifted");
                }
                exactEndminfTexture.SetPixelData<byte>(payload, 0);
                exactEndminfTexture.Apply(false, true);
                Debug.Log(
                    "Loaded exact captured Endminf CharInfo LUT: " +
                    Width + "x" + Height + ", " + format +
                    ", sha256=" + ExactEndminfSha256 + ".");
                return true;
            }
            catch (Exception exception)
            {
                if (exactEndminfTexture != null)
                {
                    DestroyResource(exactEndminfTexture);
                    exactEndminfTexture = null;
                }
                return FailExactEndminf(
                    "captured raw LUT upload failed: " + exception.Message);
            }
        }

        /// <summary>
        /// Ensures that the LUT build precedes its first lookup in the supplied
        /// command buffer. Returns false when the platform cannot provide the
        /// recovered FP16 resource, allowing the analytic fallback to remain active.
        /// </summary>
        public bool EnqueueBuild(CommandBuffer commandBuffer)
        {
            if (builderMaterial == null || commandBuffer == null)
                return false;

            EnsureTexture();
            if (texture == null || !texture.IsCreated())
                return false;

            if (!buildQueued)
            {
                commandBuffer.BeginSample("Endfield Recovered CharInfo LUT Build");
                commandBuffer.SetRenderTarget(
                    new RenderTargetIdentifier(texture));
                commandBuffer.SetViewport(new Rect(0.0f, 0.0f, Width, Height));
                commandBuffer.DrawProcedural(
                    Matrix4x4.identity,
                    builderMaterial,
                    0,
                    MeshTopology.Triangles,
                    3,
                    1);
                commandBuffer.EndSample("Endfield Recovered CharInfo LUT Build");
                buildQueued = true;
            }

            return true;
        }

        public void Dispose()
        {
            if (texture != null)
            {
                texture.Release();
                DestroyResource(texture);
                texture = null;
            }

            if (exactEndminfTexture != null)
            {
                DestroyResource(exactEndminfTexture);
                exactEndminfTexture = null;
            }

            if (builderMaterial != null)
                DestroyResource(builderMaterial);
        }

        private void EnsureTexture()
        {
            if (texture != null && texture.IsCreated())
                return;

            if (!SystemInfo.SupportsRenderTextureFormat(RenderTextureFormat.ARGBHalf))
            {
                Debug.LogWarning(
                    "This GPU does not support the recovered CharInfo RGBAHalf LUT format.");
                return;
            }

            if (texture != null)
            {
                DestroyResource(texture);
                texture = null;
            }

            var descriptor = new RenderTextureDescriptor(
                Width,
                Height,
                RenderTextureFormat.ARGBHalf,
                0)
            {
                msaaSamples = 1,
                volumeDepth = 1,
                sRGB = false,
                useMipMap = false,
                autoGenerateMips = false,
            };

            texture = new RenderTexture(descriptor)
            {
                hideFlags = HideFlags.HideAndDontSave,
                name = "Endfield Recovered CharInfo LUT 1024x32 RGBAHalf",
                filterMode = FilterMode.Bilinear,
                wrapMode = TextureWrapMode.Clamp,
                anisoLevel = 0,
            };
            buildQueued = false;
            if (!texture.Create())
            {
                Debug.LogWarning(
                    "Could not create the recovered CharInfo 1024x32 RGBAHalf LUT.");
                DestroyResource(texture);
                texture = null;
                return;
            }

            Debug.Log(
                "Recovered CharInfo LUT created: " +
                $"{Width}x{Height}, {texture.graphicsFormat}, " +
                $"filter={texture.filterMode}, wrap={texture.wrapMode}");
        }

        private bool FailExactEndminf(string reason)
        {
            exactEndminfGpuValidationComplete = true;
            exactEndminfFailure = reason ?? "unknown captured LUT failure";
            Debug.LogWarning(
                "Exact Endminf CharInfo LUT failed closed: " +
                exactEndminfFailure + ".");
            return false;
        }

        private void EnsureExactEndminfValidationTarget()
        {
            if (exactEndminfValidationTarget != null &&
                exactEndminfValidationTarget.IsCreated())
                return;
            var descriptor = new RenderTextureDescriptor(
                5,
                1,
                GraphicsFormat.R16G16B16A16_SFloat,
                GraphicsFormat.None)
            {
                msaaSamples = 1,
                volumeDepth = 1,
                sRGB = false,
                useMipMap = false,
                autoGenerateMips = false,
            };
            exactEndminfValidationTarget = new RenderTexture(descriptor)
            {
                hideFlags = HideFlags.HideAndDontSave,
                name = "Exact Endminf LUT GPU sentinel target",
                filterMode = FilterMode.Point,
                wrapMode = TextureWrapMode.Clamp,
            };
            if (!exactEndminfValidationTarget.Create())
            {
                DestroyResource(exactEndminfValidationTarget);
                exactEndminfValidationTarget = null;
            }
        }

        private void CompleteExactEndminfGpuValidation(
            AsyncGPUReadbackRequest request)
        {
            exactEndminfGpuValidationQueued = false;
            exactEndminfGpuValidationComplete = true;
            if (request.hasError)
            {
                FailExactEndminf("GPU sentinel readback failed");
                return;
            }
            NativeArray<byte> data = request.GetData<byte>();
            if (data.Length != ExactEndminfGpuSentinels.Length)
            {
                FailExactEndminf(
                    "GPU sentinel byte length drifted: expected " +
                    ExactEndminfGpuSentinels.Length + ", got " + data.Length);
                return;
            }
            for (int index = 0; index < data.Length; index++)
            {
                if (data[index] == ExactEndminfGpuSentinels[index])
                    continue;
                FailExactEndminf(
                    "GPU sentinel bytes drifted at offset " + index);
                return;
            }
            exactEndminfGpuValidated = true;
            exactEndminfFailure = string.Empty;
            Debug.Log(
                "Validated exact Endminf CharInfo LUT through five D3D11 GPU samples: " +
                ExactEndminfSha256 + ".");
        }

        private static bool HasSentinel(
            byte[] payload,
            int x,
            int y,
            byte[] expected)
        {
            int offset = (y * Width + x) * 8;
            if (payload == null || expected == null || expected.Length != 8 ||
                offset < 0 || offset + expected.Length > payload.Length)
                return false;
            for (int index = 0; index < expected.Length; index++)
            {
                if (payload[offset + index] != expected[index])
                    return false;
            }
            return true;
        }

        private static void DestroyResource(UnityEngine.Object resource)
        {
            if (resource == null)
                return;

            if (Application.isPlaying)
                UnityEngine.Object.Destroy(resource);
            else
                UnityEngine.Object.DestroyImmediate(resource);
        }
    }
}
