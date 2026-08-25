using System;
using System.Runtime.CompilerServices;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Source translations of individually closed original solver kernels.
    /// These methods remain disconnected from transform writeback until the
    /// complete active Endminf stage set is translated and verified.
    /// </summary>
    public static class EndfieldSecondaryDynamicsKernels
    {
        public struct Double3
        {
            public double x;
            public double y;
            public double z;

            public Double3(double x, double y, double z)
            {
                this.x = x;
                this.y = y;
                this.z = z;
            }
        }

        public static bool ProjectTether(
            Double3 rootNext,
            ref Double3 childNext,
            Double3 rootBasic,
            Double3 childBasic,
            float compressionLimit,
            float stretchLimit,
            ref Double3 childVelocityPosition)
        {
            double dx = rootNext.x - childNext.x;
            double dy = rootNext.y - childNext.y;
            double dz = rootNext.z - childNext.z;
            double currentLength = Math.Sqrt(dx * dx + dy * dy + dz * dz);
            if (currentLength < 9.99999993922529e-9)
                return false;

            double bdx = rootBasic.x - childBasic.x;
            double bdy = rootBasic.y - childBasic.y;
            double bdz = rootBasic.z - childBasic.z;
            double basicLength = Math.Sqrt(bdx * bdx + bdy * bdy + bdz * bdz);
            if (basicLength == 0.0)
                return false;

            double ratio = currentLength / basicLength;
            double targetRatio;
            double activation;
            float compressionThresholdFloat = SubtractBinary32(1.0f, compressionLimit);
            double compressionThreshold = compressionThresholdFloat;
            if (compressionThreshold > ratio)
            {
                targetRatio = compressionThreshold;
                activation = Math.Min(
                    Math.Max((targetRatio - ratio) / 0.30000001192092896, 0.0),
                    1.0);
            }
            else
            {
                float stretchThresholdFloat = AddBinary32(1.0f, stretchLimit);
                double stretchThreshold = stretchThresholdFloat;
                if (ratio <= stretchThreshold)
                    return false;
                targetRatio = stretchThreshold;
                activation = Math.Min(
                    Math.Max((ratio - targetRatio) / 0.30000001192092896, 0.0),
                    1.0);
            }

            double signedError = currentLength - basicLength * targetRatio;
            double nx = dx / currentLength;
            double ny = dy / currentLength;
            double nz = dz / currentLength;
            double correctionMagnitude = activation * signedError;
            double cx = nx * correctionMagnitude;
            double cy = ny * correctionMagnitude;
            double cz = nz * correctionMagnitude;

            childNext.x += cx;
            childNext.y += cy;
            childNext.z += cz;
            childVelocityPosition.x += cx * 0.699999988079071;
            childVelocityPosition.y += cy * 0.699999988079071;
            childVelocityPosition.z += cz * 0.699999988079071;
            return true;
        }

        // Mono may retain an intermediate Single expression in wider
        // precision. The no-inline ABI boundary reproduces Burst's explicit
        // vaddss/vsubss binary32 rounding before conversion to binary64.
        [MethodImpl(MethodImplOptions.NoInlining)]
        private static float AddBinary32(float left, float right)
        {
            return left + right;
        }

        [MethodImpl(MethodImplOptions.NoInlining)]
        private static float SubtractBinary32(float left, float right)
        {
            return left - right;
        }
    }
}
