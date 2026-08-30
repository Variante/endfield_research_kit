using System;
using Unity.Collections;
using UnityEngine;
using UnityEngine.Experimental.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Rebuilds HGRenderPipeline.m_multiscatteringLut from the installed
    /// SetupMultiscatteringLut producer. The source method creates one
    /// 32x32 R16_UNorm texture, evaluates the Imageworks GGX directional
    /// albedo fit over roughness/NdotV [0, 1], and quantizes it to UNorm16.
    /// </summary>
    public static class EndfieldRecoveredMultiscatteringLut
    {
        public const int Size = 32;

        private const float Sa = -0.170718f;
        private const float Sb = 4.0798502f;
        private const float Sc = -11.5295f;
        private const float Sd = 18.4961f;
        private const float Se = -9.23618f;

        private const float Ta = 0.0632331f;
        private const float Tb = 3.1434f;
        private const float Tc = -7.47567f;
        private const float Td = 13.0482f;
        private const float Te = -7.0401f;

        public static Texture2D Create()
        {
            if (!SystemInfo.IsFormatSupported(
                    GraphicsFormat.R16_UNorm,
                    FormatUsage.Sample))
            {
                throw new NotSupportedException(
                    "The recovered multiscattering LUT requires sampled " +
                    "R16_UNorm texture support.");
            }

            Texture2D texture = null;
            try
            {
                texture = new Texture2D(
                    Size,
                    Size,
                    GraphicsFormat.R16_UNorm,
                    TextureCreationFlags.None)
                {
                    name = "Recovered HGRenderPipeline multiscattering LUT",
                    filterMode = FilterMode.Bilinear,
                    wrapMode = TextureWrapMode.Clamp,
                    hideFlags = HideFlags.HideAndDontSave,
                };

                NativeArray<ushort> texels =
                    texture.GetRawTextureData<ushort>();
                Populate(texels);
                texture.Apply(false, true);
                return texture;
            }
            catch
            {
                if (texture != null)
                {
                    if (Application.isPlaying)
                        UnityEngine.Object.Destroy(texture);
                    else
                        UnityEngine.Object.DestroyImmediate(texture);
                }
                throw;
            }
        }

        public static void Populate(NativeArray<ushort> texels)
        {
            if (!texels.IsCreated || texels.Length != Size * Size)
            {
                throw new ArgumentException(
                    "The multiscattering destination must contain exactly " +
                    "1024 UNorm16 texels.",
                    nameof(texels));
            }

            int destinationIndex = 0;
            for (int roughnessIndex = 0;
                 roughnessIndex < Size;
                 roughnessIndex++)
            {
                float roughness = roughnessIndex / (Size - 1.0f);
                float roughness2 = roughness * roughness;
                float roughness3 = roughness2 * roughness;
                float roughness4 = roughness2 * roughness2;
                float sB = Sb * roughness;
                float sC = Sc * roughness2;
                float sD = Sd * roughness3;
                float sE = Se * roughness4;
                float tB = Tb * roughness;
                float tC = Tc * roughness2;
                float tD = Td * roughness3;
                float tE = Te * roughness4;

                for (int nDotVIndex = 0;
                     nDotVIndex < Size;
                     nDotVIndex++)
                {
                    float nDotV = nDotVIndex / (Size - 1.0f);
                    // Preserve the installed producer's scalar accumulation
                    // order. Reassociating these sums changes UNorm16 edge
                    // texels even though the mathematical fit is identical.
                    float s = Sa * Mathf.Sqrt(nDotV);
                    s += sB;
                    s += sC;
                    s += sD;
                    s += sE;
                    float t = Ta * nDotV;
                    t += tB;
                    t += tC;
                    t += tD;
                    t += tE;
                    float s2 = s * s;
                    float t2 = t * t;
                    float oneMinusDirectionalAlbedo = Mathf.Clamp01(
                        Mathf.Pow(nDotV, 0.75f) * (s2 * s2 * s2) /
                        (t2 * t2 * t2 + nDotV * nDotV));

                    // The installed producer performs this exact UNorm16
                    // truncation. At roughness=NdotV=0 its 0/0 NaN reaches
                    // cvttss2si, whose low 16 bits are zero.
                    int quantized = float.IsNaN(oneMinusDirectionalAlbedo)
                        ? int.MinValue
                        : (int)(oneMinusDirectionalAlbedo * ushort.MaxValue);
                    texels[destinationIndex++] = unchecked((ushort)quantized);
                }
            }
        }
    }
}
