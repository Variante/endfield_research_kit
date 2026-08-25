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

        public static int ProjectDistance(
            int particle,
            Double3[] nextPositions,
            Double3[] basePositions,
            Double3[] velocityPositions,
            byte[] attributes,
            float[] depths,
            float[] frictions,
            ushort[] neighborParticles,
            float[] signedRestLengths,
            float simulationPowerY,
            float[] restorationStiffness,
            float velocityAttenuation,
            float animationPoseRatio,
            float initScaleX,
            float scaleRatio,
            int teamFlag)
        {
            if (neighborParticles == null || signedRestLengths == null ||
                neighborParticles.Length == 0)
                return 0;
            if (neighborParticles.Length != signedRestLengths.Length)
                throw new ArgumentException("Distance neighbor/rest arrays differ in length.");
            if (restorationStiffness == null || restorationStiffness.Length != 16)
                throw new ArgumentException("Distance restoration curve must contain 16 samples.");

            float depth = depths[particle];
            float clampedDepth = Math.Min(Math.Max(depth, 0.0f), 1.0f);
            float coordinate = MultiplyBinary32(clampedDepth, 15.0f);
            int curveIndex = (int)coordinate;
            int nextCurveIndex = Math.Min(curveIndex + 1, 15);
            const float CurveStep = 0.06666667014360428f;
            float fraction = DivideBinary32(
                SubtractBinary32(depth, MultiplyBinary32(curveIndex, CurveStep)),
                CurveStep);
            float curve = AddBinary32(
                restorationStiffness[curveIndex],
                MultiplyBinary32(
                    fraction,
                    SubtractBinary32(
                        restorationStiffness[nextCurveIndex],
                        restorationStiffness[curveIndex])));
            curve = Math.Min(Math.Max(curve, 0.0f), 1.0f);
            float baseStiffness = MultiplyBinary32(simulationPowerY, curve);
            float currentWeight = DistanceWeight(
                attributes[particle], depths[particle], frictions[particle], teamFlag);
            float scale = MultiplyBinary32(initScaleX, scaleRatio);

            Double3 current = nextPositions[particle];
            double sumX = 0.0;
            double sumY = 0.0;
            double sumZ = 0.0;
            int accepted = 0;
            for (int index = 0; index < neighborParticles.Length; index++)
            {
                int neighbor = neighborParticles[index];
                float signedRest = signedRestLengths[index];
                float stiffness = signedRest > 0.0f
                    ? baseStiffness
                    : MultiplyBinary32(baseStiffness, 0.5f);
                stiffness = Math.Min(Math.Max(stiffness, 0.0f), 1.0f);

                double dx = nextPositions[neighbor].x - current.x;
                double dy = nextPositions[neighbor].y - current.y;
                double dz = nextPositions[neighbor].z - current.z;
                double length = Math.Sqrt(dx * dx + dy * dy + dz * dz);
                if (length < 9.99999993922529e-9)
                    continue;

                double bdx = basePositions[neighbor].x - basePositions[particle].x;
                double bdy = basePositions[neighbor].y - basePositions[particle].y;
                double bdz = basePositions[neighbor].z - basePositions[particle].z;
                double baseLength = Math.Sqrt(bdx * bdx + bdy * bdy + bdz * bdz);
                float referenceFloat = MultiplyBinary32(Math.Abs(signedRest), scale);
                double reference = referenceFloat;
                double target = reference + (baseLength - reference) * animationPoseRatio;
                float neighborWeight = DistanceWeight(
                    attributes[neighbor], depths[neighbor], frictions[neighbor], teamFlag);
                double weightSum = AddBinary32(currentWeight, neighborWeight);
                sumX += DistanceCorrectionComponent(
                    dx, length, stiffness, target, weightSum, currentWeight);
                sumY += DistanceCorrectionComponent(
                    dy, length, stiffness, target, weightSum, currentWeight);
                sumZ += DistanceCorrectionComponent(
                    dz, length, stiffness, target, weightSum, currentWeight);
                accepted++;
            }

            if (accepted == 0)
                return 0;
            double inverseCount = 1.0 / accepted;
            double correctionX = sumX * inverseCount;
            double correctionY = sumY * inverseCount;
            double correctionZ = sumZ * inverseCount;
            nextPositions[particle] = new Double3(
                current.x + correctionX,
                current.y + correctionY,
                current.z + correctionZ);
            Double3 velocity = velocityPositions[particle];
            velocityPositions[particle] = new Double3(
                velocity.x + correctionX * velocityAttenuation,
                velocity.y + correctionY * velocityAttenuation,
                velocity.z + correctionZ * velocityAttenuation);
            return accepted;
        }

        private static float DistanceWeight(
            byte attribute,
            float depth,
            float friction,
            int teamFlag)
        {
            float denominator;
            if ((attribute & 2) != 0)
            {
                denominator = AddBinary32(MultiplyBinary32(friction, 3.0f), 1.0f);
                float remainingDepth = SubtractBinary32(1.0f, depth);
                denominator = AddBinary32(
                    denominator,
                    MultiplyBinary32(
                        MultiplyBinary32(remainingDepth, remainingDepth),
                        5.0f));
            }
            else
            {
                denominator = (teamFlag & 0x2000) != 0 ? 10.0f : 50.0f;
            }
            return DivideBinary32(1.0f, denominator);
        }

        private static double DistanceCorrectionComponent(
            double delta,
            double length,
            float stiffness,
            double target,
            double weightSum,
            float currentWeight)
        {
            double correction = delta * (1.0 / length);
            correction *= stiffness;
            correction *= length - target;
            correction /= weightSum;
            correction *= currentWeight;
            return correction;
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

        [MethodImpl(MethodImplOptions.NoInlining)]
        private static float MultiplyBinary32(float left, float right)
        {
            return left * right;
        }

        [MethodImpl(MethodImplOptions.NoInlining)]
        private static float DivideBinary32(float left, float right)
        {
            return left / right;
        }
    }
}
