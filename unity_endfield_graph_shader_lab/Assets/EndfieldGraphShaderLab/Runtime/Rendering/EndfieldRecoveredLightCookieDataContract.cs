using System;
using UnityEngine;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Exact binding-37 byte layout used by the installed deferred resolver.
    /// The source-closed no-cookie state is all zero; non-empty cookie atlas
    /// allocation and matrix generation remain native/capture-only.
    /// </summary>
    public static class EndfieldRecoveredLightCookieDataContract
    {
        public const int MaxCookieCount = 32;
        public const int AtlasVectorCount = MaxCookieCount;
        public const int MatrixVectorCount = MaxCookieCount * 4;
        public const int VectorCount = AtlasVectorCount + MatrixVectorCount;
        public const int AtlasBytes = AtlasVectorCount * 16;
        public const int MatrixBytes = MatrixVectorCount * 16;
        public const int SizeBytes = AtlasBytes + MatrixBytes;

        public static bool TryValidateZeroCookieFrame(
            int lightCount,
            bool hasAnyCookie,
            out string failure)
        {
            if (lightCount < 0 || lightCount > MaxCookieCount)
            {
                failure =
                    $"light count {lightCount} is outside the recovered 0..{MaxCookieCount} range";
                return false;
            }
            if (hasAnyCookie)
            {
                failure =
                    "at least one selected light references a cookie; non-empty atlas allocation " +
                    "and matrix generation are not recovered";
                return false;
            }

            failure = string.Empty;
            return true;
        }

        public static void FillDiagnosticFixture(Vector4[] destination)
        {
            if (destination == null || destination.Length != VectorCount)
            {
                throw new ArgumentException(
                    $"LightCookieData requires exactly {VectorCount} float4 values",
                    nameof(destination));
            }

            for (int vectorIndex = 0; vectorIndex < destination.Length; vectorIndex++)
            {
                int word = vectorIndex * 4;
                destination[vectorIndex] = new Vector4(
                    BitConverter.Int32BitsToSingle(unchecked((int)(0x51000000u + (uint)word))),
                    BitConverter.Int32BitsToSingle(unchecked((int)(0x51000001u + (uint)word))),
                    BitConverter.Int32BitsToSingle(unchecked((int)(0x51000002u + (uint)word))),
                    BitConverter.Int32BitsToSingle(unchecked((int)(0x51000003u + (uint)word))));
            }
        }
    }
}
