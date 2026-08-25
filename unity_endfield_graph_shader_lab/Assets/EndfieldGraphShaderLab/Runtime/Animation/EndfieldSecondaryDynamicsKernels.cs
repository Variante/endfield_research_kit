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
        private const string FloatSinCosReducerTableHex =
            "83f9223e889cdc31e14fa9243ffaea170ee60b3ddf8d8db03e602da43ffaea170" +
            "ee60b3ddf8d8db03e602da43ffaea17dc603e3bf5ddd8aed90356a2eaa3af15d" +
            "c603e3bf5ddd8aed90356a2eaa3af15dc603e3bf5ddd8aed90356a2eaa3af15d" +
            "c603e3bf5ddd8aed90356a2eaa3af156e83793a2a889c2d9df02721aa8fbe14" +
            "6e83793a2a889c2d9df02721aa8fbe14dd06f339abef46adc51eb0a0ade00294" +
            "b90d66395341642c157bc09f2d2b3891721bcc385341642c157bc09f2d2b3891" +
            "e53618386bf5ddaa0c2a769b6f9afa0e27b7c136542a88290c2a769b6f9afa0e" +
            "27b7c136542a88290c2a769b6f9afa0e27b7c136542a88290c2a769b6f9afa0e" +
            "4e6e0336542a88290c2a769b6f9afa0e91935b33e14fa9243ffaea1790c8328b" +
            "91935b33e14fa9243ffaea1790c8328b91935b33e14fa9243ffaea1790c8328b" +
            "91935b33e14fa9243ffaea1790c8328b91935b33e14fa9243ffaea1790c8328b" +
            "91935b33e14fa9243ffaea1790c8328b2227b732e14fa9243ffaea1790c8328b" +
            "889cdc31e14fa9243ffaea1790c8328b889cdc31e14fa9243ffaea1790c8328b" +
            "10393931e14fa9243ffaea1790c8328b41e46430853fa5230b2e289603775309" +
            "41e46430853fa5230b2e28960377530983c8c92ff68035a30b2e289603775309" +
            "0591132f14fe94220b2e2896037753092a889c2d9df02721aa8fbe14f2233288" +
            "2a889c2d9df02721aa8fbe14f22332882a889c2d9df02721aa8fbe14f2233288" +
            "5341642c157bc09f2d2b3891db06ee045341642c157bc09f2d2b3891db06ee04" +
            "5341642c157bc09f2d2b3891db06ee04a582c82bac13fe1e2d2b3891db06ee04" +
            "4a05112bac13fe1e2d2b3891db06ee04542a88290c2a769b6f9afa0e76927c81" +
            "542a88290c2a769b6f9afa0e76927c81542a88290c2a769b6f9afa0e76927c81" +
            "40a582270c2a769b6f9afa0e76927c8140a582270c2a769b6f9afa0e76927c81" +
            "40a582270c2a769b6f9afa0e76927c8140a582270c2a769b6f9afa0e76927c81" +
            "e14fa9243ffaea1790c8328b15db0600e14fa9243ffaea1790c8328b15db0600" +
            "e14fa9243ffaea1790c8328b15db0600e14fa9243ffaea1790c8328b15db0600" +
            "e14fa9243ffaea1790c8328b15db0600e14fa9243ffaea1790c8328b15db0600" +
            "853fa5230b2e28960377530915db0000853fa5230b2e28960377530915db0000" +
            "14fe94220b2e28960377530915db000014fe94220b2e28960377530915db0000" +
            "9df02721aa8fbe14f2233288eb2400809df02721aa8fbe14f2233288eb240080" +
            "9df02721aa8fbe14f2233288eb24008075c21f20a73efa13c98f4887eb040080" +
            "75c21f20a73efa13c98f4887eb040080ac13fe1e2d2b3891db06ee0415000000" +
            "ac13fe1e2d2b3891db06ee0415000000ac13fe1e2d2b3891db06ee0415000000" +
            "58277c1e2d2b3891db06ee0415000000b04ef81d2d2b3891db06ee0415000000" +
            "5f9d703da7a98f3027c90fa36233b596bf3ae13cb2ac60b027c90fa36233b596" +
            "7d75423c6f9afa2e76927ca1e2c9ac14faea843b6f9afa2e76927ca1e2c9ac14" +
            "485f1d3924b22cac96625b1e7987cd91485f1d3924b22cac96625b1e7987cd91" +
            "485f1d3924b22cac96625b1e7987cd91485f1d3924b22cac96625b1e7987cd91" +
            "485f1d3924b22cac96625b1e7987cd913ffaea3790c832ab96625b1e7987cd91" +
            "3ffaea3790c832ab96625b1e7987cd913ffaea3790c832ab96625b1e7987cd91" +
            "7df45537e06e9a2a96625b1e7987cd91fbe8ab363f224baaaa75129d1de2c910" +
            "eaa3af3503775329ad14db1c8e77d88feaa3af3503775329ad14db1c8e77d88f" +
            "aa8fbe34f22332a84dad939bc8219e0eaa8fbe34f22332a84dad939bc8219e0e" +
            "a73efa33c98f48a7676a1d9a410e710da73efa33c98f48a7676a1d9a410e710d" +
            "4d7d7433dbc05d26322bc519410e710d9afae832dbc05d26322bc519410e710d" +
            "35f5513292fc08a53653eb98f01b6f8b6aeaa33192fc08a53653eb98f01b6f8b" +
            "a7a98f3027c90fa36233b59684208709a7a98f3027c90fa36233b59684208709" +
            "6f9afa2e76927ca1e2c9ac14801064076f9afa2e76927ca1e2c9ac1480106407" +
            "6f9afa2e76927ca1e2c9ac14801064076f9afa2e76927ca1e2c9ac1480106407" +
            "de34752e76927ca1e2c9ac1480106407bc69ea2d76927ca1e2c9ac1480106407" +
            "77d3542d96625b1e7987cd91f30f8204eea6a92c96625b1e7987cd91f30f8204" +
            "b89ba62b96625b1e7987cd91f30f8204b89ba62b96625b1e7987cd91f30f8204" +
            "e06e9a2a96625b1e7987cd91f30f82040700000008000000090000000a000000";

        private static readonly float[] FloatSinCosReducerTable = BuildFloatSinCosReducerTable();

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

        public static void ProjectAngle(
            byte[] attributes,
            float[] depths,
            float[] frictions,
            Double3[] basicPositions,
            Float4[] basicRotations,
            Double3[] nextPositions,
            Double3[] velocityPositions,
            bool restoration,
            float[] restorationCurve,
            float restorationVelocityAttenuation,
            float restorationGravityFalloff,
            bool limit,
            float[] limitCurve,
            float limitStiffness,
            float simulationPowerW,
            float gravityDot,
            Float4[] rotations,
            float[] lengths,
            Float3[] localPositions,
            Float4[] localRotations,
            Float3[] restorationVectors)
        {
            if (attributes.Length != 2 || depths.Length != 2 || frictions.Length != 2 ||
                basicPositions.Length != 2 || basicRotations.Length != 2 ||
                nextPositions.Length != 2 || velocityPositions.Length != 2 ||
                rotations.Length != 2 || lengths.Length != 2 || localPositions.Length != 2 ||
                localRotations.Length != 2 || restorationVectors.Length != 2)
                throw new ArgumentException("Controlled Angle source port requires exactly two particles.");
            if ((restoration && (restorationCurve == null || restorationCurve.Length != 16)) ||
                (limit && (limitCurve == null || limitCurve.Length != 16)))
                throw new ArgumentException("Angle curves must contain 16 samples.");

            rotations[0] = basicRotations[0];
            rotations[1] = basicRotations[1];
            if (limit)
            {
                lengths[1] = (float)LengthDouble3(SubtractDouble3(nextPositions[0], nextPositions[1]));
                Double3 basicDirection = NormalizeDouble3(SubtractDouble3(basicPositions[1], basicPositions[0]));
                Double3 local = RotateQuaternionDouble(
                    InverseQuaternionBinary32(basicRotations[0]), basicDirection);
                localPositions[1] = new Float3((float)local.x, (float)local.y, (float)local.z);
                localRotations[1] = MultiplyQuaternionBinary32(
                    InverseQuaternionBinary32(basicRotations[0]), basicRotations[1]);
            }
            if (restoration)
            {
                Double3 rest = SubtractDouble3(basicPositions[1], basicPositions[0]);
                restorationVectors[1] = new Float3((float)rest.x, (float)rest.y, (float)rest.z);
            }

            for (int sweep = 0; sweep < 3; sweep++)
            {
                float t = AddBinary32(MultiplyBinary32(MultiplyBinary32(sweep, 0.5f), 0.4f), 0.1f);
                float oneMinusT = SubtractBinary32(1.0f, t);
                Double3 p = nextPositions[1];
                Double3 q = nextPositions[0];
                double childMobility = AngleMobility(frictions[1]);
                double parentMobility = AngleMobility(frictions[0]);
                if (limit)
                {
                    Double3 u = RotateQuaternionDouble(rotations[0], ToDouble3(localPositions[1]));
                    Double3 d = SubtractDouble3(p, q);
                    double currentLength = LengthDouble3(d);
                    double blendLength = currentLength + 0.5 * (lengths[1] - currentLength);
                    Double3 direction = MultiplyDouble3(d, 1.0 / currentLength);
                    Double3 unconstrained = MultiplyDouble3(direction, blendLength);
                    float limitRadians = MultiplyBinary32(
                        SampleAngleCurve(depths[1], limitCurve), 0.01745329238474369f);
                    double phi = AcosBurstDouble(Math.Min(Math.Max(
                        DotDouble3(unconstrained, u) /
                        (LengthDouble3(unconstrained) * LengthDouble3(u)), -1.0), 1.0));
                    Double3 constrained = unconstrained;
                    if (phi > limitRadians)
                    {
                        Double3 vn = NormalizeDouble3(unconstrained);
                        Double3 un = NormalizeDouble3(u);
                        double psi = AcosBurstDouble(Math.Min(Math.Max(DotDouble3(vn, un), -1.0), 1.0));
                        double beta = phi + limitStiffness * (limitRadians - phi);
                        if (beta < psi)
                        {
                            double theta = psi * ((psi - beta) / psi);
                            constrained = RotateQuaternionDouble(
                                RotationBetweenDouble(vn, un, theta), unconstrained);
                        }
                    }
                    Double3 childTarget = AddDouble3(q, AddDouble3(
                        MultiplyDouble3(unconstrained, 0.4000000059604645),
                        MultiplyDouble3(constrained, 0.6000000238418579)));
                    Double3 childCorrection = MultiplyDouble3(
                        SubtractDouble3(childTarget, p), childMobility);
                    nextPositions[1] = AddDouble3(p, childCorrection);
                    velocityPositions[1] = AddDouble3(
                        velocityPositions[1], MultiplyDouble3(childCorrection, 0.8999999761581421));
                    if ((attributes[0] & 2) != 0)
                    {
                        Double3 parentCorrection = MultiplyDouble3(
                            SubtractDouble3(unconstrained, constrained),
                            parentMobility * 0.4000000059604645);
                        nextPositions[0] = AddDouble3(q, parentCorrection);
                        velocityPositions[0] = AddDouble3(
                            velocityPositions[0], MultiplyDouble3(parentCorrection, 0.8999999761581421));
                    }
                    Double3 updatedDirection = SubtractDouble3(nextPositions[1], nextPositions[0]);
                    Float4 baseRotation = MultiplyQuaternionBinary32(rotations[0], localRotations[1]);
                    Float4 deltaRotation = RotationBetweenDouble(u, updatedDirection, null);
                    rotations[1] = MultiplyQuaternionBinary32(deltaRotation, baseRotation);
                }

                if (restoration)
                {
                    p = nextPositions[1];
                    q = nextPositions[0];
                    Double3 d = SubtractDouble3(p, q);
                    Double3 rest = ToDouble3(restorationVectors[1]);
                    Double3 dn = NormalizeDouble3(d);
                    Double3 rn = NormalizeDouble3(rest);
                    double angle = AcosBurstDouble(Math.Min(Math.Max(DotDouble3(dn, rn), -1.0), 1.0));
                    float strength = Math.Min(Math.Max(
                        SampleAngleCurve(depths[1], restorationCurve), 0.0f), 1.0f);
                    strength = Math.Min(Math.Max(
                        MultiplyBinary32(strength, simulationPowerW), 0.0f), 1.0f);
                    float gravityMix = AddBinary32(
                        SubtractBinary32(1.0f, restorationGravityFalloff),
                        MultiplyBinary32(gravityDot, restorationGravityFalloff));
                    strength = MultiplyBinary32(strength, gravityMix);
                    Double3 rotated = RotateQuaternionDouble(
                        RotationBetweenDouble(dn, rn, angle * strength), d);
                    Double3 weightedCurrent = AddDouble3(q, MultiplyDouble3(d, t));
                    Double3 childTarget = AddDouble3(
                        weightedCurrent, MultiplyDouble3(rotated, oneMinusT));
                    Double3 childCorrection = MultiplyDouble3(
                        SubtractDouble3(childTarget, p), parentMobility);
                    nextPositions[1] = AddDouble3(p, childCorrection);
                    velocityPositions[1] = AddDouble3(
                        velocityPositions[1],
                        MultiplyDouble3(childCorrection, restorationVelocityAttenuation));
                    if ((attributes[0] & 2) != 0)
                    {
                        Double3 parentDelta = SubtractDouble3(
                            SubtractDouble3(weightedCurrent, MultiplyDouble3(rotated, t)), q);
                        Double3 parentCorrection = MultiplyDouble3(parentDelta, childMobility);
                        nextPositions[0] = AddDouble3(q, parentCorrection);
                        velocityPositions[0] = AddDouble3(
                            velocityPositions[0],
                            MultiplyDouble3(parentCorrection, restorationVelocityAttenuation));
                    }
                }
            }
        }

        public static void UpdateBasicPosture(
            int[] parentIndices,
            byte[] attributes,
            Float3[] localPositions,
            Float4[] localRotations,
            Float3[] basePositions,
            Float4[] baseRotations,
            Float3[] stepPositions,
            Float4[] stepRotations,
            Float3 initScale,
            float scaleRatio,
            Float3 negativeScaleDirection,
            Float4 negativeScaleQuaternion,
            float animationPoseRatio)
        {
            if (animationPoseRatio > 0.99f)
                return;
            for (int vertex = 0; vertex < parentIndices.Length; vertex++)
            {
                int parent = parentIndices[vertex];
                if ((attributes[vertex] & 2) != 0 && parent >= 0)
                {
                    Float3 local = localPositions[vertex];
                    Float3 scaled = new Float3(
                        MultiplyBinary32(MultiplyBinary32(MultiplyBinary32(local.x, negativeScaleDirection.x), initScale.x), scaleRatio),
                        MultiplyBinary32(MultiplyBinary32(MultiplyBinary32(local.y, negativeScaleDirection.y), initScale.y), scaleRatio),
                        MultiplyBinary32(MultiplyBinary32(MultiplyBinary32(local.z, negativeScaleDirection.z), initScale.z), scaleRatio));
                    Float3 rotated = RotateQuaternionBinary32(stepRotations[parent], scaled);
                    stepPositions[vertex] = new Float3(
                        AddBinary32(stepPositions[parent].x, rotated.x),
                        AddBinary32(stepPositions[parent].y, rotated.y),
                        AddBinary32(stepPositions[parent].z, rotated.z));
                    Float4 authored = localRotations[vertex];
                    authored = new Float4(
                        MultiplyBinary32(negativeScaleQuaternion.x, authored.x),
                        MultiplyBinary32(negativeScaleQuaternion.y, authored.y),
                        MultiplyBinary32(negativeScaleQuaternion.z, authored.z),
                        MultiplyBinary32(negativeScaleQuaternion.w, authored.w));
                    stepRotations[vertex] = MultiplyQuaternionBinary32(stepRotations[parent], authored);
                }
                else
                {
                    stepRotations[vertex] = NormalizeFloat4Binary32(stepRotations[vertex]);
                }
            }
            if (animationPoseRatio <= 1.0e-8f)
                return;
            for (int vertex = 0; vertex < parentIndices.Length; vertex++)
            {
                Float3 step = stepPositions[vertex];
                Float3 authored = basePositions[vertex];
                stepPositions[vertex] = new Float3(
                    AddBinary32(step.x, MultiplyBinary32(animationPoseRatio, SubtractBinary32(authored.x, step.x))),
                    AddBinary32(step.y, MultiplyBinary32(animationPoseRatio, SubtractBinary32(authored.y, step.y))),
                    AddBinary32(step.z, MultiplyBinary32(animationPoseRatio, SubtractBinary32(authored.z, step.z))));
                stepRotations[vertex] = SlerpQuaternionBinary32(
                    stepRotations[vertex], baseRotations[vertex], animationPoseRatio);
            }
        }

        public static void FinishSimulationParticle(
            bool active,
            float deltaTime,
            float scaleRatio,
            float velocityWeight,
            float particleSpeedLimit,
            float centrifugalAcceleration,
            float dynamicFriction,
            float staticFrictionParameter,
            float depth,
            Double3 centerPosition,
            float centerAngularVelocity,
            Float3 centerRotationAxis,
            ref Double3 nextPosition,
            Double3 previousPosition,
            ref Double3 velocityPosition,
            ref Float3 velocity,
            ref Float3 realVelocity,
            ref float friction,
            ref float staticFriction,
            Float3 collisionNormal)
        {
            double dt = deltaTime;
            Double3 corrected = nextPosition;
            if (!active)
            {
                velocity = new Float3(0.0f, 0.0f, 0.0f);
            }
            else
            {
                Double3 correctedVelocityPosition = velocityPosition;
                float normalSquared = DotFloat3Binary32(collisionNormal, collisionNormal);
                float threshold = MultiplyBinary32(scaleRatio, staticFrictionParameter);
                double accumulatedStaticFriction = staticFriction;
                if (normalSquared > 1.0e-8f && friction > 0.0f && threshold > 0.0f)
                {
                    Double3 delta = SubtractDouble3(nextPosition, previousPosition);
                    double normalDistance = DotFloatDouble3(collisionNormal, delta);
                    Double3 tangent = new Double3(
                        delta.x - collisionNormal.x * normalDistance,
                        delta.y - collisionNormal.y * normalDistance,
                        delta.z - collisionNormal.z * normalDistance);
                    double tangentSpeed = LengthDouble3(tangent) / dt;
                    if (threshold > tangentSpeed)
                        accumulatedStaticFriction += 0.03999999910593033;
                    else
                        accumulatedStaticFriction -= Math.Max(
                            (tangentSpeed - threshold) / 0.20000000298023224,
                            0.05000000074505806);
                    accumulatedStaticFriction = Math.Min(Math.Max(accumulatedStaticFriction, 0.0), 1.0);
                    Double3 correction = MultiplyDouble3(tangent, accumulatedStaticFriction);
                    corrected = SubtractDouble3(nextPosition, correction);
                    correctedVelocityPosition = SubtractDouble3(velocityPosition, correction);
                }
                else
                {
                    accumulatedStaticFriction = Math.Min(
                        Math.Max(accumulatedStaticFriction - 0.05000000074505806, 0.0), 1.0);
                }
                staticFriction = (float)accumulatedStaticFriction;

                Double3 velocity0 = MultiplyDouble3(
                    SubtractDouble3(corrected, correctedVelocityPosition), 1.0 / dt);
                double speed0Squared = DotDouble3(velocity0, velocity0);
                Float3 direction0 = speed0Squared > 1.0e-8
                    ? NormalizeDouble3ToFloatBinary32(velocity0)
                    : new Float3(0.0f, 0.0f, 0.0f);
                Double3 velocity1 = velocity0;
                if (friction > 1.0e-8f && normalSquared > 1.0e-8f &&
                    dynamicFriction > 0.0f && speed0Squared >= 1.0e-8)
                {
                    float hemisphere = AddBinary32(
                        MultiplyBinary32(DotFloat3Binary32(collisionNormal, direction0), 0.5f), 0.5f);
                    float directionalLoss = SubtractBinary32(
                        1.0f, MultiplyBinary32(hemisphere, hemisphere));
                    float strength = Math.Min(Math.Max(
                        MultiplyBinary32(dynamicFriction, friction), 0.0f), 1.0f);
                    float attenuation = MultiplyBinary32(strength, directionalLoss);
                    velocity1 = new Double3(
                        velocity0.x - velocity0.x * attenuation,
                        velocity0.y - velocity0.y * attenuation,
                        velocity0.z - velocity0.z * attenuation);
                }

                Double3 velocity2 = velocity1;
                if (particleSpeedLimit >= 0.0f)
                {
                    float scaledLimit = MultiplyBinary32(particleSpeedLimit, scaleRatio);
                    double speed = LengthDouble3(velocity1);
                    if (!(speed <= scaledLimit || speed <= 9.999999717180685e-10))
                        velocity2 = MultiplyDouble3(velocity1, scaledLimit / speed);
                }

                Double3 finalVelocity = velocity2;
                if (centerAngularVelocity > 1.0e-8f && centrifugalAcceleration > 1.0e-8f &&
                    speed0Squared >= 1.0e-8)
                {
                    Double3 radialInput = new Double3(
                        (float)(corrected.x - centerPosition.x),
                        (float)(corrected.y - centerPosition.y),
                        (float)(corrected.z - centerPosition.z));
                    double axial = DotFloatDouble3(centerRotationAxis, radialInput);
                    Double3 radial = new Double3(
                        radialInput.x - centerRotationAxis.x * axial,
                        radialInput.y - centerRotationAxis.y * axial,
                        radialInput.z - centerRotationAxis.z * axial);
                    double radialLength = LengthDouble3(radial);
                    if (radialLength > 1.0e-8)
                    {
                        Double3 radialDirection = MultiplyDouble3(radial, 1.0 / radialLength);
                        Double3 tangentCross = new Double3(
                            centerRotationAxis.y * radialDirection.z - centerRotationAxis.z * radialDirection.y,
                            centerRotationAxis.z * radialDirection.x - centerRotationAxis.x * radialDirection.z,
                            centerRotationAxis.x * radialDirection.y - centerRotationAxis.y * radialDirection.x);
                        Double3 tangent = MultiplyDouble3(tangentCross, 1.0 / LengthDouble3(tangentCross));
                        double alignment = Math.Min(Math.Max(
                            tangent.x * direction0.x + tangent.y * direction0.y + tangent.z * direction0.z,
                            0.0), 1.0);
                        float depthFactor = AddBinary32(SubtractBinary32(1.0f, depth), 1.0f);
                        float angularTerm = MultiplyBinary32(
                            MultiplyBinary32(centerAngularVelocity, depthFactor), centerAngularVelocity);
                        double magnitude = radialLength * angularTerm * alignment;
                        magnitude *= centrifugalAcceleration * 0.019999999552965164;
                        finalVelocity = new Double3(
                            velocity2.x + radialDirection.x * magnitude,
                            velocity2.y + radialDirection.y * magnitude,
                            velocity2.z + radialDirection.z * magnitude);
                    }
                }

                velocity = new Float3(
                    (float)(finalVelocity.x * velocityWeight),
                    (float)(finalVelocity.y * velocityWeight),
                    (float)(finalVelocity.z * velocityWeight));
                friction = MultiplyBinary32(friction, 0.6000000238418579f);
            }

            realVelocity = new Float3(
                (float)((corrected.x - previousPosition.x) / dt),
                (float)((corrected.y - previousPosition.y) / dt),
                (float)((corrected.z - previousPosition.z) / dt));
            nextPosition = corrected;
        }

        private static float SampleAngleCurve(float depth, float[] values)
        {
            float clamped = Math.Min(Math.Max(depth, 0.0f), 1.0f);
            float scaled = MultiplyBinary32(clamped, 15.0f);
            int index = (int)scaled;
            const float step = 0.06666667014360428f;
            float fraction = DivideBinary32(
                SubtractBinary32(depth, MultiplyBinary32(index, step)), step);
            int first = Math.Min(Math.Max(index, 0), 15);
            int second = Math.Min(Math.Max(index + 1, 0), 15);
            return AddBinary32(
                values[first],
                MultiplyBinary32(fraction, SubtractBinary32(values[second], values[first])));
        }

        private static float AngleMobility(float friction)
        {
            return DivideBinary32(1.0f, AddBinary32(1.0f, MultiplyBinary32(3.0f, friction)));
        }

        private static double AcosBurstDouble(double value)
        {
            double x = Math.Min(Math.Max(value, -1.0), 1.0);
            double absolute = Math.Abs(x);
            double asin;
            if (absolute < 0.5)
            {
                asin = AsinBurstPolynomialDouble(absolute, absolute * absolute);
            }
            else
            {
                double y = (1.0 - absolute) * 0.5;
                asin = Math.PI * 0.5 - 2.0 * AsinBurstPolynomialDouble(Math.Sqrt(y), y);
            }
            if (x < 0.0)
                asin = -asin;
            return Math.PI * 0.5 - asin;
        }

        private static double AsinBurstPolynomialDouble(double s, double y)
        {
            const double a0 = 0.031615876506539346;
            const double a1 = 0.012153605255773773;
            const double a2 = 0.019290454772679107;
            const double a3 = 0.017359569912236146;
            const double b0 = -0.015819182433299966;
            const double b1 = 0.013887151845016092;
            const double b2 = 0.006606077476277171;
            const double b3 = 0.022371761819320483;
            const double c0 = 0.07500000000378582;
            const double c1 = 0.16666666666664975;
            const double d0 = 0.030381959280381322;
            const double d1 = 0.044642856813771024;
            double y2 = y * y;
            double t0 = b2 + a2 * y + y2 * (b0 + a0 * y);
            double t1 = b3 + a3 * y + y2 * (b1 + a1 * y);
            double p = c1 + c0 * y + y2 * (d1 + d0 * y) +
                y2 * y2 * t1 + Math.Pow(y2, 4.0) * t0;
            return s + s * y * p;
        }

        private static Float4 RotationBetweenDouble(
            Double3 source, Double3 target, double? requestedAngle)
        {
            Double3 sourceNormal = NormalizeDouble3(source);
            Double3 targetNormal = NormalizeDouble3(target);
            double cosine = Math.Min(Math.Max(DotDouble3(sourceNormal, targetNormal), -1.0), 1.0);
            double angle = requestedAngle ?? AcosBurstDouble(cosine);
            if (Math.Abs(1.0 - cosine) < 9.999999974752427e-7)
                return new Float4(0.0f, 0.0f, 0.0f, 1.0f);
            Double3 axis;
            if (Math.Abs(1.0 + cosine) < 9.999999974752427e-7)
            {
                Double3 helper = Math.Abs(sourceNormal.x) > Math.Abs(sourceNormal.y)
                    ? new Double3(1.0, 1.0, 1.0)
                    : new Double3(1.0, 0.0, 0.0);
                axis = NormalizeDouble3(CrossDouble3(sourceNormal, helper));
                if (!requestedAngle.HasValue)
                    angle = 3.1415927410125732;
            }
            else
            {
                axis = NormalizeDouble3(CrossDouble3(sourceNormal, targetNormal));
            }
            return AxisAngleBinary32(axis, angle);
        }

        private static Float4 AxisAngleBinary32(Double3 axis, double angle)
        {
            float x = (float)axis.x;
            float y = (float)axis.y;
            float z = (float)axis.z;
            float half = MultiplyBinary32((float)angle, 0.5f);
            FloatSinCosBinary32(half, out float sine, out float cosine);
            return new Float4(
                MultiplyBinary32(x, sine),
                MultiplyBinary32(y, sine),
                MultiplyBinary32(z, sine),
                cosine);
        }

        private static Float4 InverseQuaternionBinary32(Float4 value)
        {
            return new Float4(-value.x, -value.y, -value.z, value.w);
        }

        private static Double3 RotateQuaternionDouble(Float4 q, Double3 value)
        {
            Double3 xyz = new Double3(q.x, q.y, q.z);
            Double3 t = MultiplyDouble3(CrossDouble3(xyz, value), 2.0);
            return AddDouble3(value, AddDouble3(MultiplyDouble3(t, q.w), CrossDouble3(xyz, t)));
        }

        private static Double3 CrossDouble3(Double3 a, Double3 b)
        {
            return new Double3(
                a.y * b.z - a.z * b.y,
                a.z * b.x - a.x * b.z,
                a.x * b.y - a.y * b.x);
        }

        private static Double3 NormalizeDouble3(Double3 value)
        {
            return MultiplyDouble3(value, 1.0 / LengthDouble3(value));
        }

        private static Double3 AddDouble3(Double3 a, Double3 b)
        {
            return new Double3(a.x + b.x, a.y + b.y, a.z + b.z);
        }

        private static Double3 ToDouble3(Float3 value)
        {
            return new Double3(value.x, value.y, value.z);
        }

        public static void FloatSinCosBinary32(float value, out float sine, out float cosine)
        {
            uint inputBits = FloatBits(value);
            float absolute = FloatFromBits(inputBits & 0x7fffffffu);
            int quadrant;
            float reduced;
            if (absolute < 125.0f)
            {
                float scaled = MultiplyBinary32(value, FloatFromBits(0x3f22f983u));
                quadrant = (int)AddBinary32(scaled, scaled < 0.0f ? -0.5f : 0.5f);
                float n = quadrant;
                reduced = AddBinary32(
                    AddBinary32(
                        AddBinary32(value, MultiplyBinary32(n, FloatFromBits(0xbfc90e00u))),
                        MultiplyBinary32(n, FloatFromBits(0xb86d5000u))),
                    MultiplyBinary32(n, FloatFromBits(0xb0885a31u)));
            }
            else if (absolute < 39000.0f)
            {
                float scaled = MultiplyBinary32(value, FloatFromBits(0x3f22f983u));
                quadrant = (int)AddBinary32(scaled, scaled < 0.0f ? -0.5f : 0.5f);
                float n = quadrant;
                reduced = AddBinary32(
                    AddBinary32(
                        AddBinary32(
                            AddBinary32(value, MultiplyBinary32(n, FloatFromBits(0xbfc90000u))),
                            MultiplyBinary32(n, FloatFromBits(0xb9fd8000u))),
                        MultiplyBinary32(n, FloatFromBits(0xb4a88000u))),
                    MultiplyBinary32(n, FloatFromBits(0xae85a309u)));
            }
            else if ((inputBits & 0x7f800000u) != 0x7f800000u)
            {
                FloatSinCosLargeReduce(inputBits, out quadrant, out float hi, out float lo);
                reduced = AddBinary32(hi, lo);
            }
            else
            {
                quadrant = 0;
                reduced = FloatFromBits(0x7fc00000u);
            }

            float square = MultiplyBinary32(reduced, reduced);
            sine = FloatFromBits(0x80000000u);
            if (inputBits != 0x80000000u)
            {
                float polynomial = AddBinary32(
                    MultiplyBinary32(square, FloatFromBits(0xb94ca65bu)),
                    FloatFromBits(0x3c08839au));
                polynomial = AddBinary32(
                    MultiplyBinary32(square, polynomial), FloatFromBits(0xbe2aaaa2u));
                sine = AddBinary32(
                    reduced, MultiplyBinary32(reduced, MultiplyBinary32(square, polynomial)));
            }
            float cosinePolynomial = AddBinary32(
                MultiplyBinary32(square, FloatFromBits(0xb491ed89u)), FloatFromBits(0x37d0078bu));
            cosinePolynomial = AddBinary32(
                MultiplyBinary32(square, cosinePolynomial), FloatFromBits(0xbab60b58u));
            cosinePolynomial = AddBinary32(
                MultiplyBinary32(square, cosinePolynomial), FloatFromBits(0x3d2aaaaau));
            cosinePolynomial = AddBinary32(MultiplyBinary32(square, cosinePolynomial), -0.5f);
            cosine = AddBinary32(MultiplyBinary32(square, cosinePolynomial), 1.0f);

            float outSine;
            float outCosine;
            if ((quadrant & 1) != 0)
            {
                outCosine = sine;
                outSine = (quadrant & 2) != 0 ? XorFloatSign(cosine) : cosine;
            }
            else
            {
                outCosine = cosine;
                outSine = (quadrant & 2) != 0 ? XorFloatSign(sine) : sine;
            }
            if (((quadrant + 1) & 2) != 0)
                outCosine = XorFloatSign(outCosine);
            sine = outSine;
            cosine = outCosine;
        }

        private static void FloatSinCosLargeReduce(
            uint inputBits, out int quadrant, out float reducedHigh, out float reducedLow)
        {
            int exponent = (int)((inputBits >> 23) & 0xffu);
            uint shift = (uint)(exponent < 0xda ? 1 : 0) << 29;
            uint normalizedBits = unchecked(shift + inputBits - 0x20000000u);
            float x0 = FloatFromBits(normalizedBits);
            int tableIndex = exponent >= 0x98 ? 4 * exponent - 0x260 : 0;

            float tab0 = FloatSinCosReducerTable[tableIndex];
            float xhi = FloatFromBits(normalizedBits & 0xfffff000u);
            float xlo = SubtractBinary32(x0, xhi);
            float tab0hi = FloatFromBits(FloatBits(tab0) & 0xfffff000u);
            float tab0lo = SubtractBinary32(tab0, tab0hi);
            float product0 = MultiplyBinary32(tab0, x0);
            float error0 = SubtractBinary32(MultiplyBinary32(xhi, tab0hi), product0);
            error0 = AddBinary32(MultiplyBinary32(xlo, tab0hi), error0);
            error0 = AddBinary32(MultiplyBinary32(tab0lo, xhi), error0);
            error0 = AddBinary32(MultiplyBinary32(xlo, tab0lo), error0);

            float coarse = MultiplyBinary32(TruncateBinary32(MultiplyBinary32(0.0009765625f, product0)), 1024.0f);
            float remainder0 = SubtractBinary32(product0, coarse);
            int positive0 = product0 > 0.0f ? 1 : 0;
            int q0 = (((positive0 + (int)MultiplyBinary32(remainder0, 8.0f) + 3) & 7) - 3) >> 1;
            float half0 = FloatFromBits((FloatBits(product0) & 0x80000000u) | 0x3f000000u);
            float rounded0 = MultiplyBinary32(
                TruncateBinary32(AddBinary32(MultiplyBinary32(4.0f, remainder0), half0)), 0.25f);
            float reduced0 = SubtractBinary32(remainder0, rounded0);
            if (AbsoluteBinary32(reduced0) > 0.125f)
                reduced0 = SubtractBinary32(reduced0, half0);
            if (AbsoluteBinary32(reduced0) > 10000000000.0f)
                reduced0 = FloatFromBits(FloatBits(reduced0) & 0x80000000u);
            bool exact0 = AbsoluteBinary32(product0) == FloatFromBits(0x3dffffffu);
            if (exact0)
                reduced0 = product0;

            float savedError0 = error0;
            float sum0 = AddBinary32(error0, reduced0);
            float tab1 = FloatSinCosReducerTable[tableIndex + 1];
            float product1 = MultiplyBinary32(tab1, x0);
            float sum1 = AddBinary32(product1, sum0);
            float coarse1 = MultiplyBinary32(TruncateBinary32(MultiplyBinary32(0.0009765625f, sum1)), 1024.0f);
            float remainder1 = SubtractBinary32(sum1, coarse1);
            int carriedQ0 = exact0 ? 0 : q0;
            float tab1hi = FloatFromBits(FloatBits(tab1) & 0xfffff000u);
            int positive1 = sum1 > 0.0f ? 1 : 0;
            float half1 = FloatFromBits((FloatBits(sum1) & 0x80000000u) | 0x3f000000u);
            float rounded1 = MultiplyBinary32(
                TruncateBinary32(AddBinary32(MultiplyBinary32(4.0f, remainder1), half1)), 0.25f);
            float reduced1 = SubtractBinary32(remainder1, rounded1);
            if (AbsoluteBinary32(reduced1) > 0.125f)
                reduced1 = SubtractBinary32(reduced1, half1);
            int q1 = (((positive1 + (int)MultiplyBinary32(remainder1, 8.0f) + 3) & 7) - 3) >> 1;
            bool exact1 = AbsoluteBinary32(sum1) == FloatFromBits(0x3dffffffu);
            if (AbsoluteBinary32(reduced1) > 10000000000.0f)
                reduced1 = FloatFromBits(FloatBits(reduced1) & 0x80000000u);
            if (exact1)
                reduced1 = sum1;
            quadrant = carriedQ0 + (exact1 ? 0 : q1);

            if (AbsoluteBinary32(FloatFromBits(normalizedBits & 0x7fffffffu)) < FloatFromBits(0x3f333333u))
            {
                reducedHigh = x0;
                reducedLow = 0.0f;
                return;
            }

            float productHi = MultiplyBinary32(xhi, tab1hi);
            float tab1lo = SubtractBinary32(tab1, tab1hi);
            float productError = SubtractBinary32(productHi, product1);
            productError = AddBinary32(MultiplyBinary32(xlo, tab1hi), productError);
            productError = AddBinary32(MultiplyBinary32(tab1lo, xhi), productError);
            float sum1Tail = SubtractBinary32(sum1, sum0);
            float reduced0Tail = SubtractBinary32(reduced0, sum0);
            productError = AddBinary32(MultiplyBinary32(tab1lo, xlo), productError);
            float recoveredProduct1 = SubtractBinary32(sum1, sum1Tail);
            reduced0Tail = AddBinary32(reduced0Tail, savedError0);
            reduced0Tail = AddBinary32(productError, reduced0Tail);
            float sum0Tail = SubtractBinary32(sum0, recoveredProduct1);
            float product1Tail = SubtractBinary32(product1, sum1Tail);
            sum0Tail = AddBinary32(product1Tail, sum0Tail);
            reduced0Tail = AddBinary32(reduced0Tail, sum0Tail);
            float combined = AddBinary32(reduced0Tail, reduced1);
            float combineError = SubtractBinary32(reduced1, combined);
            combineError = AddBinary32(reduced0Tail, combineError);

            float tab2 = FloatSinCosReducerTable[tableIndex + 2];
            float tab2hi = FloatFromBits(FloatBits(tab2) & 0xfffff000u);
            float tab2lo = SubtractBinary32(tab2, tab2hi);
            float product2 = MultiplyBinary32(tab2, x0);
            float product2Error = SubtractBinary32(MultiplyBinary32(xhi, tab2hi), product2);
            product2Error = AddBinary32(MultiplyBinary32(tab2lo, xhi), product2Error);
            product2Error = AddBinary32(MultiplyBinary32(xlo, tab2hi), product2Error);
            product2Error = AddBinary32(MultiplyBinary32(xlo, tab2lo), product2Error);
            float product3 = MultiplyBinary32(x0, FloatSinCosReducerTable[tableIndex | 3]);
            float tail = AddBinary32(AddBinary32(product3, product2Error), combineError);
            float leading = AddBinary32(product2, combined);
            float recoveredCombined = SubtractBinary32(leading, combined);
            float leadingError = SubtractBinary32(product2, recoveredCombined);
            leadingError = AddBinary32(
                leadingError, SubtractBinary32(combined, SubtractBinary32(leading, recoveredCombined)));
            tail = AddBinary32(tail, leadingError);
            reducedHigh = AddBinary32(leading, tail);
            reducedLow = AddBinary32(tail, SubtractBinary32(leading, reducedHigh));

            float splitHigh = FloatFromBits(FloatBits(reducedHigh) & 0xfffff000u);
            float splitLow = SubtractBinary32(reducedHigh, splitHigh);
            float radiansHigh = MultiplyBinary32(reducedHigh, FloatFromBits(0x40c90fdbu));
            float radiansError = SubtractBinary32(
                MultiplyBinary32(splitHigh, FloatFromBits(0x40c90000u)), radiansHigh);
            radiansError = AddBinary32(MultiplyBinary32(splitLow, FloatFromBits(0x40c90000u)), radiansError);
            radiansError = AddBinary32(MultiplyBinary32(splitHigh, FloatFromBits(0x3afdb000u)), radiansError);
            radiansError = AddBinary32(MultiplyBinary32(splitLow, FloatFromBits(0x3afdb000u)), radiansError);
            radiansError = AddBinary32(MultiplyBinary32(reducedHigh, FloatFromBits(0xb43bbd2eu)), radiansError);
            reducedLow = AddBinary32(MultiplyBinary32(reducedLow, FloatFromBits(0x40c90fdbu)), radiansError);
            reducedHigh = radiansHigh;
        }

        private static float[] BuildFloatSinCosReducerTable()
        {
            var table = new float[416];
            for (int index = 0; index < table.Length; index++)
            {
                int offset = index * 8;
                uint bits = uint.Parse(
                    FloatSinCosReducerTableHex.Substring(offset + 6, 2) +
                    FloatSinCosReducerTableHex.Substring(offset + 4, 2) +
                    FloatSinCosReducerTableHex.Substring(offset + 2, 2) +
                    FloatSinCosReducerTableHex.Substring(offset, 2),
                    System.Globalization.NumberStyles.HexNumber,
                    System.Globalization.CultureInfo.InvariantCulture);
                table[index] = FloatFromBits(bits);
            }
            return table;
        }

        private static float AbsoluteBinary32(float value)
        {
            return FloatFromBits(FloatBits(value) & 0x7fffffffu);
        }

        private static float XorFloatSign(float value)
        {
            return FloatFromBits(FloatBits(value) ^ 0x80000000u);
        }

        private static float TruncateBinary32(float value)
        {
            return (float)(int)value;
        }

        private static uint FloatBits(float value)
        {
            return BitConverter.ToUInt32(BitConverter.GetBytes(value), 0);
        }

        private static float FloatFromBits(uint bits)
        {
            return BitConverter.ToSingle(BitConverter.GetBytes(bits), 0);
        }

        private static Float4 SlerpQuaternionBinary32(Float4 a, Float4 b, float t)
        {
            float dot = DotFloat4Binary32(a, b);
            if (dot < 0.0f)
            {
                b = new Float4(-b.x, -b.y, -b.z, -b.w);
                dot = -dot;
            }
            if (dot >= 0.9995f)
            {
                return NormalizeFloat4Binary32(new Float4(
                    AddBinary32(a.x, MultiplyBinary32(t, SubtractBinary32(b.x, a.x))),
                    AddBinary32(a.y, MultiplyBinary32(t, SubtractBinary32(b.y, a.y))),
                    AddBinary32(a.z, MultiplyBinary32(t, SubtractBinary32(b.z, a.z))),
                    AddBinary32(a.w, MultiplyBinary32(t, SubtractBinary32(b.w, a.w)))));
            }
            float theta = AcosBurstBinary32(dot);
            float inverseSin = DivideBinary32(
                1.0f,
                SqrtBinary32(SubtractBinary32(1.0f, MultiplyBinary32(dot, dot))));
            float weightA = MultiplyBinary32(
                inverseSin,
                SinBurstBoundedBinary32(MultiplyBinary32(SubtractBinary32(1.0f, t), theta)));
            float weightB = MultiplyBinary32(
                inverseSin,
                SinBurstBoundedBinary32(MultiplyBinary32(t, theta)));
            return new Float4(
                AddBinary32(MultiplyBinary32(a.x, weightA), MultiplyBinary32(b.x, weightB)),
                AddBinary32(MultiplyBinary32(a.y, weightA), MultiplyBinary32(b.y, weightB)),
                AddBinary32(MultiplyBinary32(a.z, weightA), MultiplyBinary32(b.z, weightB)),
                AddBinary32(MultiplyBinary32(a.w, weightA), MultiplyBinary32(b.w, weightB)));
        }

        private static float SinBurstBoundedBinary32(float value)
        {
            if (float.IsNaN(value) || float.IsInfinity(value) || Math.Abs(value) >= 125.0f)
                throw new ArgumentOutOfRangeException(nameof(value), "Pinned BasicPosture sine fast path exceeded.");
            float quotient = MultiplyBinary32(value, 0.31830987334251404f);
            int rounded = (int)AddBinary32(quotient, quotient < 0.0f ? -0.5f : 0.5f);
            float roundedFloat = rounded;
            float reduced = AddBinary32(value, MultiplyBinary32(roundedFloat, -3.1414794921875f));
            reduced = AddBinary32(reduced, MultiplyBinary32(roundedFloat, -0.0001131594181060791f));
            reduced = AddBinary32(reduced, MultiplyBinary32(roundedFloat, -1.984187258941006e-09f));
            float signed = (rounded & 1) != 0 ? -reduced : reduced;
            float square = MultiplyBinary32(reduced, reduced);
            float polynomial = AddBinary32(
                MultiplyBinary32(square, 2.6083159809786594e-06f), -0.00019810690719168633f);
            polynomial = AddBinary32(MultiplyBinary32(square, polynomial), 0.00833307858556509f);
            polynomial = AddBinary32(MultiplyBinary32(square, polynomial), -0.16666659712791443f);
            return AddBinary32(signed, MultiplyBinary32(square, MultiplyBinary32(signed, polynomial)));
        }

        private static float AcosBurstBinary32(float value)
        {
            float absolute = Math.Abs(value);
            float polynomialInput;
            float root;
            if (absolute < 0.5f)
            {
                polynomialInput = MultiplyBinary32(value, value);
                root = absolute;
            }
            else
            {
                polynomialInput = MultiplyBinary32(0.5f, SubtractBinary32(1.0f, absolute));
                root = absolute == 1.0f ? 0.0f : SqrtBinary32(polynomialInput);
            }
            float polynomial = AddBinary32(MultiplyBinary32(polynomialInput, 0.04197454825043678f), 0.024240460246801376f);
            polynomial = AddBinary32(MultiplyBinary32(polynomialInput, polynomial), 0.04547423869371414f);
            polynomial = AddBinary32(MultiplyBinary32(polynomialInput, polynomial), 0.07495029270648956f);
            polynomial = AddBinary32(MultiplyBinary32(polynomialInput, polynomial), 0.16666772961616516f);
            float signedRoot = value < 0.0f ? -root : root;
            float asin = AddBinary32(signedRoot, MultiplyBinary32(polynomialInput, MultiplyBinary32(signedRoot, polynomial)));
            if (absolute < 0.5f)
                return SubtractBinary32(1.5707963705062866f, asin);
            float doubled = AddBinary32(root, MultiplyBinary32(polynomialInput, MultiplyBinary32(root, polynomial)));
            doubled = AddBinary32(doubled, doubled);
            return value < 0.0f ? SubtractBinary32(3.1415927410125732f, doubled) : doubled;
        }

        private static float DotFloat4Binary32(Float4 a, Float4 b)
        {
            return AddBinary32(
                AddBinary32(MultiplyBinary32(a.x, b.x), MultiplyBinary32(a.y, b.y)),
                AddBinary32(MultiplyBinary32(a.z, b.z), MultiplyBinary32(a.w, b.w)));
        }

        private static Float4 NormalizeFloat4Binary32(Float4 value)
        {
            float inverse = DivideBinary32(1.0f, SqrtBinary32(DotFloat4Binary32(value, value)));
            return new Float4(
                MultiplyBinary32(value.x, inverse), MultiplyBinary32(value.y, inverse),
                MultiplyBinary32(value.z, inverse), MultiplyBinary32(value.w, inverse));
        }

        private static Float4 MultiplyQuaternionBinary32(Float4 a, Float4 b)
        {
            return new Float4(
                AddBinary32(AddBinary32(MultiplyBinary32(a.w, b.x), MultiplyBinary32(a.x, b.w)), SubtractBinary32(MultiplyBinary32(a.y, b.z), MultiplyBinary32(a.z, b.y))),
                AddBinary32(AddBinary32(MultiplyBinary32(a.w, b.y), MultiplyBinary32(a.y, b.w)), SubtractBinary32(MultiplyBinary32(a.z, b.x), MultiplyBinary32(a.x, b.z))),
                AddBinary32(AddBinary32(MultiplyBinary32(a.w, b.z), MultiplyBinary32(a.z, b.w)), SubtractBinary32(MultiplyBinary32(a.x, b.y), MultiplyBinary32(a.y, b.x))),
                SubtractBinary32(SubtractBinary32(SubtractBinary32(MultiplyBinary32(a.w, b.w), MultiplyBinary32(a.x, b.x)), MultiplyBinary32(a.y, b.y)), MultiplyBinary32(a.z, b.z)));
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

        private static float DotFloat3Binary32(Float3 a, Float3 b)
        {
            return AddBinary32(
                AddBinary32(MultiplyBinary32(a.x, b.x), MultiplyBinary32(a.y, b.y)),
                MultiplyBinary32(a.z, b.z));
        }

        private static Float3 NormalizeDouble3ToFloatBinary32(Double3 value)
        {
            Float3 rounded = new Float3((float)value.x, (float)value.y, (float)value.z);
            float inverse = DivideBinary32(1.0f, SqrtBinary32(DotFloat3Binary32(rounded, rounded)));
            return new Float3(
                MultiplyBinary32(rounded.x, inverse),
                MultiplyBinary32(rounded.y, inverse),
                MultiplyBinary32(rounded.z, inverse));
        }

        private static double DotFloatDouble3(Float3 a, Double3 b)
        {
            return (a.x * b.x + a.y * b.y) + a.z * b.z;
        }

        private static double DotDouble3(Double3 a, Double3 b)
        {
            return (a.x * b.x + a.y * b.y) + a.z * b.z;
        }

        private static double LengthDouble3(Double3 value)
        {
            return Math.Sqrt(DotDouble3(value, value));
        }

        private static Double3 SubtractDouble3(Double3 a, Double3 b)
        {
            return new Double3(a.x - b.x, a.y - b.y, a.z - b.z);
        }

        private static Double3 MultiplyDouble3(Double3 value, double scalar)
        {
            return new Double3(value.x * scalar, value.y * scalar, value.z * scalar);
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
