using System;
using UnityEngine;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Selected-consumer subset of the original deferred pass-0 b35
    /// ShaderVariablesGlobal constant buffer. Every non-selected row remains
    /// zero until its producer is independently recovered.
    /// </summary>
    public static class EndfieldRecoveredShaderVariablesGlobalContract
    {
        public const int SizeBytes = 3200;
        public const int VectorCount = 200;
        public const int D3D11SelectedSizeBytes = 2512;
        public const int D3D11SelectedVectorCount = 157;

        public const int ScreenSizeVector = 0;
        public const int ProjectionParamsVector = 3;
        public const int OrthoParamsVector = 4;
        public const int GlobalMipBiasVector = 26;
        public const int BinningOffsetsVector = 28;
        public const int EnvironmentParamsVector = 29;
        public const int GraphicsFeatures0Vector = 30;
        public const int GraphicsFeatures1Vector = 31;
        public const int AtmosphereFogFirstVector = 71;
        public const int HeightFogFirstVector = 77;
        public const int VolumetricFogFirstVector = 83;
        public const int IrradianceParamsFirstVector = 132;
        public const int DefaultSHRedVector = 135;
        public const int DefaultSHGreenVector = 136;
        public const int DefaultSHBlueVector = 137;
        public const int WetnessVector = 156;

        public static readonly Vector4 SelectedEnvironmentParams = new Vector4(
            0.28772247f,
            0.28772247f,
            1.0f,
            0.0f);

        public static readonly Vector4 SelectedDefaultSH = new Vector4(
            -0.007550761f,
            0.47223732f,
            0.012170809f,
            1.0963056f);

        public static readonly int[] SelectedUsedVectors =
        {
            0, 3, 4, 26, 28, 29, 30, 31,
            71, 72, 73, 74, 75, 76,
            77, 78, 79, 80, 81, 82,
            83, 84, 85, 86, 87,
            132, 133, 134, 135, 136, 137,
            156,
        };

        public static bool TryBuild(
            Camera camera,
            int width,
            int height,
            Vector4 environmentParams,
            bool prerequisitesReady,
            Vector4[] destination,
            out string failure)
        {
            failure = null;
            if (!prerequisitesReady)
            {
                failure =
                    "canonical binning/reflection/VisibilitySH and deferred " +
                    "TransformVariables prerequisites are required";
                return false;
            }
            if (camera == null)
            {
                failure = "physical camera is required";
                return false;
            }
            if (width <= 0 || height <= 0)
            {
                failure = "render dimensions must be positive";
                return false;
            }
            if (camera.orthographic)
            {
                failure = "selected CharInfo camera must be perspective";
                return false;
            }
            if (FloatBits(camera.nearClipPlane) != FloatBits(0.1f))
            {
                failure =
                    "selected CharInfo near clip must be exact float32 0.1";
                return false;
            }
            if (FloatBits(environmentParams.x) !=
                    FloatBits(SelectedEnvironmentParams.x) ||
                FloatBits(environmentParams.y) !=
                    FloatBits(SelectedEnvironmentParams.y))
            {
                failure =
                    "selected CharInfo environment diffuse/specular factors " +
                    "must match the serialized phase";
                return false;
            }
            if (destination == null || destination.Length != VectorCount)
            {
                failure =
                    "destination must contain exactly 200 float4 vectors";
                return false;
            }
            if (!EndfieldRecoveredCanonicalBinningLayoutContract.TryBuild(
                    width,
                    height,
                    out EndfieldRecoveredCanonicalBinningLayoutContract.Layout
                        layout,
                    out failure))
            {
                return false;
            }

            Array.Clear(destination, 0, destination.Length);
            destination[ScreenSizeVector] = new Vector4(
                0.0f,
                0.0f,
                1.0f / width,
                1.0f / height);
            destination[ProjectionParamsVector] = new Vector4(
                0.0f,
                camera.nearClipPlane,
                0.0f,
                0.0f);
            // c4.w is the selected perspective flag and is exactly zero.
            destination[OrthoParamsVector] = Vector4.zero;
            // c26.x is mip bias 0; c26.w is branch-dead behind c83.z=0.
            destination[GlobalMipBiasVector] = Vector4.zero;
            destination[BinningOffsetsVector] = new Vector4(
                IntBits(layout.lightXYOffset),
                IntBits(layout.lightZOffset),
                IntBits(layout.reflectionXYOffset),
                IntBits(layout.reflectionZOffset));
            destination[EnvironmentParamsVector] = new Vector4(
                SelectedEnvironmentParams.x,
                SelectedEnvironmentParams.y,
                0.0f,
                0.0f);
            destination[GraphicsFeatures0Vector] = new Vector4(
                0.0f,
                0.0f,
                1.0f,
                1.0f);
            destination[GraphicsFeatures1Vector] = new Vector4(
                7.0f,
                0.0f,
                0.0f,
                0.0f);

            destination[71] = Vector4.zero;
            destination[72] = new Vector4(0.0f, 0.0f, 1.0f, 0.001f);
            destination[73] = new Vector4(0.00001f, 0.00001f, 0.00001f, 0.0f);
            destination[74] = new Vector4(0.0f, 0.0f, 0.0f, -1.0f);
            destination[75] = Vector4.zero;
            destination[76] = new Vector4(0.0f, 0.0f, 0.0f, -65535.0f);

            destination[77] = Vector4.zero;
            destination[78] = Vector4.zero;
            destination[79] = new Vector4(0.0f, 0.0f, 0.0f, 1.0f);
            destination[80] = Vector4.zero;
            destination[81] = new Vector4(0.0f, 1.0f, 0.0f, 0.0f);
            destination[82] = new Vector4(0.0f, 0.0f, 0.0f, 1.0f);

            // c83.z disables every downstream volumetric read. c83..c87 and
            // inactive V2 irradiance c132..c134 remain exact zero vectors.
            for (int vector = 83; vector <= 87; vector++)
                destination[vector] = Vector4.zero;
            for (int vector = 132; vector <= 134; vector++)
                destination[vector] = Vector4.zero;

            destination[DefaultSHRedVector] = SelectedDefaultSH;
            destination[DefaultSHGreenVector] = SelectedDefaultSH;
            destination[DefaultSHBlueVector] = SelectedDefaultSH;
            destination[WetnessVector] = Vector4.zero;
            return true;
        }

        public static uint[] BuildExpectedWords(Vector4[] vectors)
        {
            if (vectors == null || vectors.Length != VectorCount)
            {
                throw new ArgumentException(
                    "Expected exactly 200 vectors.",
                    nameof(vectors));
            }
            var words = new uint[VectorCount * 4];
            for (int vectorIndex = 0; vectorIndex < vectors.Length; vectorIndex++)
            {
                Vector4 value = vectors[vectorIndex];
                int word = vectorIndex * 4;
                words[word + 0] = FloatBits(value.x);
                words[word + 1] = FloatBits(value.y);
                words[word + 2] = FloatBits(value.z);
                words[word + 3] = FloatBits(value.w);
            }
            return words;
        }

        private static float IntBits(int value)
        {
            return BitConverter.Int32BitsToSingle(value);
        }

        private static uint FloatBits(float value)
        {
            return unchecked((uint)BitConverter.SingleToInt32Bits(value));
        }
    }
}
