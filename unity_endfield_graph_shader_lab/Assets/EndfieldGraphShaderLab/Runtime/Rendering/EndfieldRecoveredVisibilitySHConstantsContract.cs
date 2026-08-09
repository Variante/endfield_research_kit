using System;
using UnityEngine;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Exact installed 128-byte VisibilitySHConstData producer for the current
    /// active untiled route. The native function zero-fills the entire source
    /// struct, overwrites vectors 0..4, and copies untouched zero vectors 5..7.
    /// The selected deferred resolver itself reads only vectors 2 and 3.
    /// </summary>
    public static class EndfieldRecoveredVisibilitySHConstantsContract
    {
        public const int SizeBytes = 128;
        public const int VectorCount = 8;
        public const int SelectedReadFirstVector = 2;
        public const int SelectedReadVectorCount = 2;

        public static bool TryBuild(
            int cameraWidth,
            int cameraHeight,
            Vector4[] destination,
            out string failure)
        {
            failure = null;
            if (destination == null || destination.Length != VectorCount)
            {
                failure = "destination must contain exactly eight float4 vectors";
                return false;
            }
            if (cameraWidth <= 0 || cameraHeight <= 0)
            {
                failure = "camera dimensions must be positive";
                return false;
            }
            if (cameraWidth > 0x00FFFFFF || cameraHeight > 0x00FFFFFF)
            {
                failure = "camera dimensions exceed exact float-integer transport";
                return false;
            }

            // The installed default enables the signed truncating half-size
            // branch. Positive C# integer division has the same result.
            int outputWidth = cameraWidth / 2;
            int outputHeight = cameraHeight / 2;
            if (outputWidth <= 0 || outputHeight <= 0)
            {
                failure = "retail half-resolution dimensions must remain positive";
                return false;
            }

            // Matches the native 0x80-byte zero-fill before rows 0..4 are
            // overwritten. Rows 5..7 consequently remain exact zero.
            Array.Clear(destination, 0, destination.Length);
            destination[0] = Bits(
                0x409D41DDu,
                0x40956445u,
                0xC09D41DDu,
                0xC0956445u);
            destination[1] = Bits(
                0x418B5D98u,
                0x4118E06Bu,
                0xC18B5D98u,
                0xC118E06Bu);
            destination[2] = Bits(
                0x3F800000u,
                0x3EA16095u,
                0x3F800000u,
                0x3F800000u);
            destination[3] = new Vector4(
                FloatFromBits(0x3E5B57C6u),
                0.0f,
                outputWidth,
                outputHeight);
            destination[4] = new Vector4(
                FloatFromBits(0x3F4CCCCDu),
                FloatFromBits(0x40A00000u),
                1.0f / outputWidth,
                1.0f / outputHeight);
            return true;
        }

        public static uint[] BuildExpectedWords(Vector4[] vectors)
        {
            if (vectors == null || vectors.Length != VectorCount)
                throw new ArgumentException(
                    "Expected exactly eight vectors.",
                    nameof(vectors));
            var words = new uint[VectorCount * 4];
            for (int index = 0; index < vectors.Length; index++)
            {
                Vector4 value = vectors[index];
                int word = index * 4;
                words[word + 0] = FloatBits(value.x);
                words[word + 1] = FloatBits(value.y);
                words[word + 2] = FloatBits(value.z);
                words[word + 3] = FloatBits(value.w);
            }
            return words;
        }

        private static Vector4 Bits(uint x, uint y, uint z, uint w)
        {
            return new Vector4(
                FloatFromBits(x),
                FloatFromBits(y),
                FloatFromBits(z),
                FloatFromBits(w));
        }

        private static float FloatFromBits(uint value)
        {
            return BitConverter.Int32BitsToSingle(unchecked((int)value));
        }

        private static uint FloatBits(float value)
        {
            return unchecked((uint)BitConverter.SingleToInt32Bits(value));
        }
    }
}
