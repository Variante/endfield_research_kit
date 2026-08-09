using System;
using System.Runtime.InteropServices;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Exact 48-byte retail LightCulling+0x60 constant-buffer layout recovered
    /// from the installed GameAssembly.  This type does not discover a light
    /// census: callers must provide a source-closed selected-light count.
    /// </summary>
    public static class EndfieldRecoveredLightBinningConstantsContract
    {
        public const int SizeBytes = 48;
        public const int TileSize = 32;
        public const int SliceCount = 2048;
        public const float ZBinSlice = 1.0f;
        public const int MaximumPunctualLightCount = 32;

        [StructLayout(LayoutKind.Sequential, Pack = 4)]
        public struct Data
        {
            public int lightCount;
            public int numTiles;
            public int actualWidth;
            public int actualHeight;
            public float tileSize;
            public float numTilesX;
            public float numTilesY;
            public float numSliceZ;
            public float nearClipPlane;
            public float farClipPlane;
            public float zBinSlice;
            public float invZBinSlice;
        }

        public static bool TryBuild(
            int sourceClosedLightCount,
            int actualWidth,
            int actualHeight,
            float nearClipPlane,
            float farClipPlane,
            out Data data,
            out string failure)
        {
            data = default;
            failure = string.Empty;

            if (Marshal.SizeOf<Data>() != SizeBytes)
            {
                failure =
                    $"managed LightBinningConstants size is {Marshal.SizeOf<Data>()}; " +
                    $"expected the recovered {SizeBytes}-byte ABI";
                return false;
            }
            if (sourceClosedLightCount < 0 ||
                sourceClosedLightCount > MaximumPunctualLightCount)
            {
                failure =
                    $"source-closed light count {sourceClosedLightCount} is outside " +
                    $"the recovered 0..{MaximumPunctualLightCount} range";
                return false;
            }
            if (actualWidth <= 0 || actualHeight <= 0)
            {
                failure =
                    $"render dimensions must be positive, got " +
                    $"{actualWidth}x{actualHeight}";
                return false;
            }
            if (!IsFinite(nearClipPlane) || !IsFinite(farClipPlane) ||
                nearClipPlane <= 0.0f || farClipPlane <= nearClipPlane)
            {
                failure =
                    $"camera clip range must be finite and ordered, got " +
                    $"near={nearClipPlane}, far={farClipPlane}";
                return false;
            }

            int tilesX = 1 + (actualWidth - 1) / TileSize;
            int tilesY = 1 + (actualHeight - 1) / TileSize;
            long tileCount = (long)tilesX * tilesY;
            if (tileCount > int.MaxValue)
            {
                failure =
                    $"tile count {tileCount} exceeds the recovered signed-int field";
                return false;
            }

            data = new Data
            {
                lightCount = sourceClosedLightCount,
                numTiles = (int)tileCount,
                actualWidth = actualWidth,
                actualHeight = actualHeight,
                tileSize = TileSize,
                numTilesX = tilesX,
                numTilesY = tilesY,
                numSliceZ = SliceCount,
                nearClipPlane = nearClipPlane,
                farClipPlane = farClipPlane,
                zBinSlice = ZBinSlice,
                invZBinSlice = 1.0f / ZBinSlice,
            };
            return true;
        }

        private static bool IsFinite(float value)
        {
            return !float.IsNaN(value) && !float.IsInfinity(value);
        }
    }
}
