using System;
using UnityEngine;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Source-closed punctual section of the original 11,440-byte ShadowData.
    /// The full allocation is retained while only the isolated overview
    /// producer's 56 matrices/params/rects and atlas texel size are populated.
    /// </summary>
    public static class EndfieldRecoveredDeferredShadowDataContract
    {
        public const int VectorCount = 715;
        public const int SizeBytes = VectorCount * sizeof(float) * 4;
        public const int D3D11SelectedVectorCount = 401;
        public const int D3D11SelectedSizeBytes =
            D3D11SelectedVectorCount * sizeof(float) * 4;

        public const int PunctualSlotCount = 56;
        public const int PunctualMatrixFirstVector = 64;
        public const int PunctualParamsFirstVector = 288;
        public const int PunctualRectFirstVector = 344;
        public const int PunctualTexelSizeVector = 400;
        public const int DynamicCacheBase = 40;
        public const int StaticAtlasTileColumns = 4;
        public const int AtlasTileRows = 4;
        public const int DynamicCapacity = 8;

        public static bool TryBuildSelectedPunctualSubset(
            Matrix4x4[] worldToShadow,
            Vector4[] shadowParams,
            Vector4[] shadowRects,
            Vector4 texelSize,
            int tileResolution,
            int faceCount,
            Vector4[] destination,
            out string failure)
        {
            failure = null;
            if (destination == null || destination.Length != VectorCount)
            {
                failure = "destination must contain exactly 715 float4 vectors";
                return false;
            }
            if (worldToShadow == null ||
                worldToShadow.Length != PunctualSlotCount ||
                shadowParams == null ||
                shadowParams.Length != PunctualSlotCount ||
                shadowRects == null ||
                shadowRects.Length != PunctualSlotCount)
            {
                failure =
                    "punctual source arrays must each contain exactly 56 rows";
                return false;
            }
            if (tileResolution != 512 && tileResolution != 1024)
            {
                failure = "source tile resolution must be exactly 512 or 1024";
                return false;
            }
            if (faceCount != 1 && faceCount != 6)
            {
                failure = "isolated punctual face count must be exactly 1 or 6";
                return false;
            }

            int atlasWidth =
                (StaticAtlasTileColumns +
                 DynamicCapacity / AtlasTileRows) * tileResolution;
            int atlasHeight = AtlasTileRows * tileResolution;
            Vector4 expectedTexelSize = new Vector4(
                1.0f / atlasWidth,
                1.0f / atlasHeight,
                atlasWidth,
                atlasHeight);
            if (!Finite(texelSize) ||
                !Approximately(texelSize, expectedTexelSize, 1.0e-7f))
            {
                failure =
                    "punctual atlas texel size does not match the recovered 6T x 4T allocation";
                return false;
            }

            for (int slot = 0; slot < PunctualSlotCount; slot++)
            {
                bool active = slot >= DynamicCacheBase &&
                    slot < DynamicCacheBase + faceCount;
                if (!active)
                {
                    if (!MatrixExactlyZero(worldToShadow[slot]) ||
                        shadowParams[slot] != Vector4.zero ||
                        shadowRects[slot] != Vector4.zero)
                    {
                        failure =
                            "unowned punctual slot " + slot +
                            " must remain exactly zero";
                        return false;
                    }
                    continue;
                }

                if (!Finite(worldToShadow[slot]) ||
                    MatrixExactlyZero(worldToShadow[slot]))
                {
                    failure =
                        "active punctual slot " + slot +
                        " must contain a finite nonzero receiver matrix";
                    return false;
                }
                Vector4 parameters = shadowParams[slot];
                if (!Finite(parameters) ||
                    parameters.x != 0.0f ||
                    parameters.y < 0.0f ||
                    !(parameters.z > 0.0f) ||
                    parameters.w < 0.0f ||
                    parameters.w > 1.0f)
                {
                    failure =
                        "active punctual slot " + slot +
                        " has invalid PCF_3x3 receiver parameters";
                    return false;
                }

                int dynamicIndex = slot - DynamicCacheBase;
                int tileX = StaticAtlasTileColumns +
                    dynamicIndex / AtlasTileRows;
                int tileY = dynamicIndex & (AtlasTileRows - 1);
                Vector4 expectedRect = new Vector4(
                    (float)(tileX * tileResolution) / atlasWidth,
                    (float)(tileY * tileResolution) / atlasHeight,
                    (float)((tileX + 1) * tileResolution) / atlasWidth,
                    (float)((tileY + 1) * tileResolution) / atlasHeight);
                if (!Finite(shadowRects[slot]) ||
                    !Approximately(shadowRects[slot], expectedRect, 1.0e-7f))
                {
                    failure =
                        "active punctual slot " + slot +
                        " does not match its native dynamic-cache atlas tile";
                    return false;
                }
            }

            Array.Clear(destination, 0, destination.Length);
            for (int slot = 0; slot < PunctualSlotCount; slot++)
            {
                int matrixFirst = PunctualMatrixFirstVector + slot * 4;
                Matrix4x4 matrix = worldToShadow[slot];
                for (int column = 0; column < 4; column++)
                    destination[matrixFirst + column] = matrix.GetColumn(column);
                destination[PunctualParamsFirstVector + slot] =
                    shadowParams[slot];
                destination[PunctualRectFirstVector + slot] =
                    shadowRects[slot];
            }
            destination[PunctualTexelSizeVector] = texelSize;
            return true;
        }

        public static uint[] BuildExpectedWords(Vector4[] vectors)
        {
            if (vectors == null || vectors.Length != VectorCount)
            {
                throw new ArgumentException(
                    "Expected exactly 715 vectors.",
                    nameof(vectors));
            }
            var words = new uint[VectorCount * 4];
            for (int vectorIndex = 0;
                 vectorIndex < vectors.Length;
                 vectorIndex++)
            {
                Vector4 value = vectors[vectorIndex];
                int first = vectorIndex * 4;
                words[first + 0] = FloatBits(value.x);
                words[first + 1] = FloatBits(value.y);
                words[first + 2] = FloatBits(value.z);
                words[first + 3] = FloatBits(value.w);
            }
            return words;
        }

        private static bool MatrixExactlyZero(Matrix4x4 matrix)
        {
            for (int index = 0; index < 16; index++)
            {
                if (matrix[index] != 0.0f)
                    return false;
            }
            return true;
        }

        private static bool Finite(Matrix4x4 matrix)
        {
            for (int index = 0; index < 16; index++)
            {
                if (!Finite(matrix[index]))
                    return false;
            }
            return true;
        }

        private static bool Finite(Vector4 value)
        {
            return Finite(value.x) && Finite(value.y) &&
                Finite(value.z) && Finite(value.w);
        }

        private static bool Finite(float value)
        {
            return !float.IsNaN(value) && !float.IsInfinity(value);
        }

        private static bool Approximately(
            Vector4 left,
            Vector4 right,
            float tolerance)
        {
            return Mathf.Abs(left.x - right.x) <= tolerance &&
                Mathf.Abs(left.y - right.y) <= tolerance &&
                Mathf.Abs(left.z - right.z) <= tolerance &&
                Mathf.Abs(left.w - right.w) <= tolerance;
        }

        private static uint FloatBits(float value)
        {
            return unchecked((uint)BitConverter.SingleToInt32Bits(value));
        }
    }
}
