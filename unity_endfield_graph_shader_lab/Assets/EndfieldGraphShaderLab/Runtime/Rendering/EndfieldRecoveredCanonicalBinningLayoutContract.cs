using System;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Exact installed BinningPass layout for the selected CharInfo camera.
    /// The reflection segment is the source-closed no-local-probe fallback.
    /// </summary>
    public static class EndfieldRecoveredCanonicalBinningLayoutContract
    {
        public const int TileSize = 32;
        public const int MaxTileX = 256;
        public const int MaxTileY = 128;
        public const int LightSliceCount = 2048;
        public const int LightWordsPerBin = 8;
        public const int ReflectionSliceCount = 1024;
        public const int ReflectionWordsPerBin = 1;
        public const int WordStrideBytes = sizeof(uint);

        public struct Layout
        {
            public int tileX;
            public int tileY;
            public int tileCount;
            public int lightXYOffset;
            public int lightZOffset;
            public int lightWordCount;
            public int reflectionXYOffset;
            public int reflectionZOffset;
            public int reflectionWordCount;
            public int totalWordCount;
        }

        public static bool TryBuild(
            int width,
            int height,
            out Layout layout,
            out string failure)
        {
            layout = default;
            failure = string.Empty;
            if (width <= 0 || height <= 0)
            {
                failure = "render dimensions must be positive";
                return false;
            }

            try
            {
                int tileX = checked((int)(((long)width + TileSize - 1) / TileSize));
                int tileY = checked((int)(((long)height + TileSize - 1) / TileSize));
                if (tileX > MaxTileX || tileY > MaxTileY)
                {
                    failure =
                        $"tile dimensions {tileX}x{tileY} exceed the installed " +
                        $"{MaxTileX}x{MaxTileY} limit";
                    return false;
                }

                int tileCount = checked(tileX * tileY);
                int lightXYOffset = 0;
                int lightZOffset = checked(tileCount * LightWordsPerBin);
                int lightWordCount = checked(
                    (tileCount + LightSliceCount) * LightWordsPerBin);
                int reflectionXYOffset = lightWordCount;
                int reflectionZOffset = checked(reflectionXYOffset + tileCount);
                int reflectionWordCount = checked(
                    tileCount + ReflectionSliceCount);
                int totalWordCount = checked(
                    lightWordCount + reflectionWordCount);

                layout = new Layout
                {
                    tileX = tileX,
                    tileY = tileY,
                    tileCount = tileCount,
                    lightXYOffset = lightXYOffset,
                    lightZOffset = lightZOffset,
                    lightWordCount = lightWordCount,
                    reflectionXYOffset = reflectionXYOffset,
                    reflectionZOffset = reflectionZOffset,
                    reflectionWordCount = reflectionWordCount,
                    totalWordCount = totalWordCount
                };
                return true;
            }
            catch (OverflowException)
            {
                failure = "binning layout arithmetic overflowed";
                return false;
            }
        }
    }
}
