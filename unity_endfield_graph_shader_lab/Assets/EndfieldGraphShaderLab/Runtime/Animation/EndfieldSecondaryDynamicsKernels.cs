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

        public struct Float3
        {
            public float x;
            public float y;
            public float z;

            public Float3(float x, float y, float z)
            {
                this.x = x;
                this.y = y;
                this.z = z;
            }
        }

        public struct Float4
        {
            public float x;
            public float y;
            public float z;
            public float w;

            public Float4(float x, float y, float z, float w)
            {
                this.x = x;
                this.y = y;
                this.z = z;
                this.w = w;
            }
        }

        public struct CapsuleColliderWork
        {
            public byte flag;
            public Double3 aabbMin;
            public Double3 aabbMax;
            public float radius0;
            public float radius1;
            public Double3 old0;
            public Double3 old1;
            public Double3 next0;
            public Double3 next1;
            public Float4 inverseOldRotation;
            public Float4 rotation;
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

        public static int ProjectPointCapsules(
            ref Double3 nextPosition,
            ref Double3 velocityPosition,
            ref float friction,
            out Float3 collisionNormal,
            float particleRadius,
            CapsuleColliderWork[] colliders,
            bool boneSpring)
        {
            Double3 original = nextPosition;
            double addX = 0.0;
            double addY = 0.0;
            double addZ = 0.0;
            float addNormalX = 0.0f;
            float addNormalY = 0.0f;
            float addNormalZ = 0.0f;
            float contactNormalX = 0.0f;
            float contactNormalY = 0.0f;
            float contactNormalZ = 0.0f;
            double minimumDistance = double.MaxValue;
            int penetratingCount = 0;
            bool contactFound = false;

            if (colliders != null)
            {
                foreach (CapsuleColliderWork collider in colliders)
                {
                    int type = collider.flag & 0x0f;
                    if ((collider.flag & 0x30) != 0x30 || type < 2 || type > 7)
                        continue;
                    double expandedRadius = particleRadius * 2.0;
                    if (original.x + expandedRadius < collider.aabbMin.x ||
                        original.y + expandedRadius < collider.aabbMin.y ||
                        original.z + expandedRadius < collider.aabbMin.z ||
                        original.x - expandedRadius > collider.aabbMax.x ||
                        original.y - expandedRadius > collider.aabbMax.y ||
                        original.z - expandedRadius > collider.aabbMax.z)
                        continue;

                    double ux = collider.old1.x - collider.old0.x;
                    double uy = collider.old1.y - collider.old0.y;
                    double uz = collider.old1.z - collider.old0.z;
                    double denominator = (ux * ux + uy * uy) + uz * uz;
                    float t = 0.0f;
                    if (denominator != 0.0)
                    {
                        double px = original.x - collider.old0.x;
                        double py = original.y - collider.old0.y;
                        double pz = original.z - collider.old0.z;
                        t = (float)(((px * ux + py * uy) + pz * uz) / denominator);
                        t = Math.Min(Math.Max(t, 0.0f), 1.0f);
                    }
                    float colliderRadius = AddBinary32(
                        collider.radius0,
                        MultiplyBinary32(
                            SubtractBinary32(collider.radius1, collider.radius0), t));
                    double td = t;
                    double oldCenterX = collider.old0.x + ux * td;
                    double oldCenterY = collider.old0.y + uy * td;
                    double oldCenterZ = collider.old0.z + uz * td;
                    Float3 local = RotateQuaternionBinary32(
                        collider.inverseOldRotation,
                        new Float3(
                            (float)(original.x - oldCenterX),
                            (float)(original.y - oldCenterY),
                            (float)(original.z - oldCenterZ)));
                    Float3 transportedFloat = RotateQuaternionBinary32(collider.rotation, local);
                    double tx = transportedFloat.x;
                    double ty = transportedFloat.y;
                    double tz = transportedFloat.z;
                    double transportedLength = Math.Sqrt((tx * tx + ty * ty) + tz * tz);
                    double nx = tx / transportedLength;
                    double ny = ty / transportedLength;
                    double nz = tz / transportedLength;
                    double newCenterX = collider.next0.x + (collider.next1.x - collider.next0.x) * td;
                    double newCenterY = collider.next0.y + (collider.next1.y - collider.next0.y) * td;
                    double newCenterZ = collider.next0.z + (collider.next1.z - collider.next0.z) * td;
                    float surfaceRadius = AddBinary32(colliderRadius, particleRadius);
                    double surfaceX = newCenterX + nx * surfaceRadius;
                    double surfaceY = newCenterY + ny * surfaceRadius;
                    double surfaceZ = newCenterZ + nz * surfaceRadius;
                    double distance = ((original.x - surfaceX) * nx +
                        (original.y - surfaceY) * ny) + (original.z - surfaceZ) * nz;
                    float nxf = (float)nx;
                    float nyf = (float)ny;
                    float nzf = (float)nz;
                    if (distance <= 0.0)
                    {
                        addX += -nx * distance;
                        addY += -ny * distance;
                        addZ += -nz * distance;
                        addNormalX = AddBinary32(addNormalX, nxf);
                        addNormalY = AddBinary32(addNormalY, nyf);
                        addNormalZ = AddBinary32(addNormalZ, nzf);
                        penetratingCount++;
                    }
                    if (distance <= particleRadius)
                    {
                        contactNormalX = AddBinary32(contactNormalX, nxf);
                        contactNormalY = AddBinary32(contactNormalY, nyf);
                        contactNormalZ = AddBinary32(contactNormalZ, nzf);
                        minimumDistance = Math.Min(minimumDistance, distance);
                        contactFound = true;
                    }
                }
            }

            if (penetratingCount > 0)
            {
                float inverseCount = DivideBinary32(1.0f, penetratingCount);
                float averageX = MultiplyBinary32(addNormalX, inverseCount);
                float averageY = MultiplyBinary32(addNormalY, inverseCount);
                float averageZ = MultiplyBinary32(addNormalZ, inverseCount);
                float normalLength = SqrtBinary32(AddBinary32(
                    AddBinary32(MultiplyBinary32(averageX, averageX), MultiplyBinary32(averageY, averageY)),
                    MultiplyBinary32(averageZ, averageZ)));
                if (normalLength >= 1.0e-8f)
                {
                    float weight = Math.Min(normalLength, 1.0f);
                    nextPosition.x += addX / penetratingCount * weight;
                    nextPosition.y += addY / penetratingCount * weight;
                    nextPosition.z += addZ / penetratingCount * weight;
                }
                if (boneSpring)
                {
                    velocityPosition.x += addX;
                    velocityPosition.y += addY;
                    velocityPosition.z += addZ;
                }
            }

            collisionNormal = new Float3(0, 0, 0);
            if (contactFound && particleRadius > 0.0f)
            {
                float normalLengthSquared = AddBinary32(
                    AddBinary32(
                        MultiplyBinary32(contactNormalX, contactNormalX),
                        MultiplyBinary32(contactNormalY, contactNormalY)),
                    MultiplyBinary32(contactNormalZ, contactNormalZ));
                if (normalLengthSquared > 1.0e-6f)
                {
                    double ratio = Math.Min(Math.Max(minimumDistance / particleRadius, 0.0), 1.0);
                    friction = Math.Max(friction, (float)(1.0 - ratio));
                    collisionNormal = NormalizeFloat3Binary32(
                        new Float3(contactNormalX, contactNormalY, contactNormalZ));
                }
            }
            return penetratingCount;
        }

        private static Float3 RotateQuaternionBinary32(Float4 q, Float3 v)
        {
            float tx = MultiplyBinary32(2.0f, SubtractBinary32(
                MultiplyBinary32(q.y, v.z), MultiplyBinary32(q.z, v.y)));
            float ty = MultiplyBinary32(2.0f, SubtractBinary32(
                MultiplyBinary32(q.z, v.x), MultiplyBinary32(q.x, v.z)));
            float tz = MultiplyBinary32(2.0f, SubtractBinary32(
                MultiplyBinary32(q.x, v.y), MultiplyBinary32(q.y, v.x)));
            float cx = SubtractBinary32(MultiplyBinary32(q.y, tz), MultiplyBinary32(q.z, ty));
            float cy = SubtractBinary32(MultiplyBinary32(q.z, tx), MultiplyBinary32(q.x, tz));
            float cz = SubtractBinary32(MultiplyBinary32(q.x, ty), MultiplyBinary32(q.y, tx));
            return new Float3(
                AddBinary32(AddBinary32(v.x, MultiplyBinary32(q.w, tx)), cx),
                AddBinary32(AddBinary32(v.y, MultiplyBinary32(q.w, ty)), cy),
                AddBinary32(AddBinary32(v.z, MultiplyBinary32(q.w, tz)), cz));
        }

        private static Float3 NormalizeFloat3Binary32(Float3 value)
        {
            float lengthSquared = AddBinary32(
                AddBinary32(MultiplyBinary32(value.x, value.x), MultiplyBinary32(value.y, value.y)),
                MultiplyBinary32(value.z, value.z));
            float inverse = DivideBinary32(1.0f, SqrtBinary32(lengthSquared));
            return new Float3(
                MultiplyBinary32(value.x, inverse),
                MultiplyBinary32(value.y, inverse),
                MultiplyBinary32(value.z, inverse));
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

        [MethodImpl(MethodImplOptions.NoInlining)]
        private static float SqrtBinary32(float value)
        {
            return (float)Math.Sqrt(value);
        }
    }
}
