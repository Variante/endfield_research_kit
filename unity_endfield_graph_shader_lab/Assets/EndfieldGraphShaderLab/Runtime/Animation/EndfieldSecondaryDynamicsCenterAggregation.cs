using System;
using System.Runtime.CompilerServices;
using K = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Pure managed transcription of the CalcCenter-owned Endminf fixed-center
    /// aggregation and stationary-component velocity smoothing paths. The
    /// SimulationStepTeamUpdate-owned step/inertia/angular fields are deliberately
    /// absent from this helper.
    /// </summary>
    public static class EndfieldSecondaryDynamicsCenterAggregation
    {
        public readonly struct Result
        {
            public readonly K.Double3 Position;
            public readonly K.Float4 Rotation;

            public Result(K.Double3 position, K.Float4 rotation)
            {
                Position = position;
                Rotation = rotation;
            }
        }

        public static Result AggregateFixed(
            K.Double3[] positions,
            K.Float4[] rotations,
            K.Float4[] bindRotations,
            ushort[] fixedIndices,
            int startIndex,
            int count)
        {
            ValidateInputs(positions, rotations, bindRotations, fixedIndices, startIndex, count);

            double positionX = 0.0;
            double positionY = 0.0;
            double positionZ = 0.0;
            K.Float3 upSum = new K.Float3(0f, 0f, 0f);
            K.Float3 forwardSum = new K.Float3(0f, 0f, 0f);

            int end = startIndex + count;
            for (int ordinal = startIndex; ordinal < end; ordinal++)
            {
                int index = fixedIndices[ordinal];
                K.Double3 position = positions[index];
                positionX = Add(positionX, position.x);
                positionY = Add(positionY, position.y);
                positionZ = Add(positionZ, position.z);

                K.Float4 relative = HamiltonProduct(rotations[index], bindRotations[index]);
                RotatedBasisPair(relative, out K.Float3 up, out K.Float3 forward);
                upSum = Add(upSum, up);
                forwardSum = Add(forwardSum, forward);
            }

            double divisor = count;
            K.Double3 mean = new K.Double3(
                Divide(positionX, divisor),
                Divide(positionY, divisor),
                Divide(positionZ, divisor));

            K.Float3 forwardNormalized = Normalize(forwardSum, "forward sum");
            K.Float3 upNormalized = Normalize(upSum, "up sum");
            K.Float3 right = Normalize(Cross(upNormalized, forwardNormalized), "right basis");
            K.Float3 correctedUp = Cross(forwardNormalized, right);
            K.Float4 rotation = Normalize(QuaternionFromMatrix(right, correctedUp, forwardNormalized), "center rotation");
            return new Result(mean, rotation);
        }

        public static K.Float3 SmoothStationaryRootVelocity(
            K.Float3 oldVelocity,
            float movementInertiaSmoothing)
        {
            ValidateFinite(oldVelocity, nameof(oldVelocity));
            if (!Finite(movementInertiaSmoothing) || movementInertiaSmoothing < 0f || movementInertiaSmoothing > 1f)
                throw new ArgumentOutOfRangeException(nameof(movementInertiaSmoothing));

            float basis = Sub(1f, movementInertiaSmoothing);
            float power = (float)Math.Pow((double)basis, 3.0);
            float blend = Add(Mul(power, 0.99f), 0.01f);
            blend = blend < 0f ? 0f : blend > 1f ? 1f : blend;
            return new K.Float3(
                SmoothLane(oldVelocity.x, blend),
                SmoothLane(oldVelocity.y, blend),
                SmoothLane(oldVelocity.z, blend));
        }

        // Literal lane-shaped Hamilton product used by the pinned AVX2 core.
        public static K.Float4 HamiltonProduct(K.Float4 left, K.Float4 right)
        {
            ValidateQuaternion(left, nameof(left));
            ValidateQuaternion(right, nameof(right));
            K.Float4 awb = Mul(Splat(left.w), right);
            K.Float4 bwa = Mul(Shuffle(left, 0x24), Shuffle(right, 0x3f));
            K.Float4 cross = Mul(Shuffle(left, 0x49), Shuffle(right, 0x52));
            K.Float4 signed = Mul(Add(bwa, cross), new K.Float4(1f, 1f, 1f, -1f));
            K.Float4 tail = Mul(Shuffle(left, 0x92), Shuffle(right, 0x89));
            return Sub(Add(awb, signed), tail);
        }

        private static void RotatedBasisPair(K.Float4 q, out K.Float3 up, out K.Float3 forward)
        {
            // Exact quaternion-vector rotations of up and forward, arranged as
            // the source AVX lane sequence at 0x28fbbd..0x28fc3f.
            K.Float4 oneXw = new K.Float4(0f, 1f, 0f, 1f);
            K.Float4 oneZ = new K.Float4(0f, 0f, 1f, 0f);
            K.Float4 oneX = new K.Float4(1f, 0f, 0f, 0f);
            K.Float4 qC9 = Shuffle(q, 0xc9);
            K.Float4 qW = Splat(q.w);

            K.Float4 twice = Mul(Sub(Mul(q, oneX), Mul(qC9, oneXw)), Splat(2f));
            K.Float4 twiceC9 = Shuffle(twice, 0xc9);
            K.Float4 first = Add(Mul(qW, twiceC9), oneXw);
            first = Add(first, Shuffle(Sub(Mul(q, Shuffle(twice, 0xd2)), Mul(twiceC9, qC9)), 0xc9));

            twice = Mul(Sub(Mul(q, oneXw), Mul(oneZ, qC9)), Splat(2f));
            twiceC9 = Shuffle(twice, 0xc9);
            K.Float4 second = Add(Mul(qW, twiceC9), oneZ);
            second = Add(second, Shuffle(Sub(Mul(Shuffle(twice, 0xd2), q), Mul(twiceC9, qC9)), 0xc9));

            up = new K.Float3(first.x, first.y, first.z);
            forward = new K.Float3(second.x, second.y, second.z);
        }

        private static K.Float4 QuaternionFromMatrix(K.Float3 u, K.Float3 v, K.Float3 w)
        {
            uint uSign = Bits(u.x) & 0x80000000U;
            float t = Add(v.y, FromBits(Bits(w.z) ^ uSign));
            uint uMask = uSign != 0 ? 0xffffffffU : 0U;
            uint tMask = (Bits(t) & 0x80000000U) != 0 ? 0xffffffffU : 0U;

            uint[] signFlips = { 0U, 0x80000000U, 0x80000000U, 0x80000000U };
            uint[] uFlips = { 0U, 0x80000000U, 0U, 0x80000000U };
            uint[] tFlips = { 0x80000000U, 0x80000000U, 0x80000000U, 0U };
            K.Float4 left = new K.Float4(Add(1f, Math.Abs(u.x)), u.y, w.x, v.z);
            K.Float4 right = new K.Float4(t, v.x, u.z, w.y);
            K.Float4 value = default;
            for (int lane = 0; lane < 4; lane++)
            {
                uint signs = signFlips[lane] ^ (uMask & uFlips[lane]) ^ (tMask & tFlips[lane]);
                SetLane(ref value, lane, Add(GetLane(left, lane), FromBits(Bits(GetLane(right, lane)) ^ signs)));
            }

            if (uMask != 0) value = new K.Float4(value.z, value.w, value.x, value.y);
            if (tMask == 0) value = new K.Float4(value.w, value.z, value.y, value.x);
            return value;
        }

        private static K.Float3 Normalize(K.Float3 value, string label)
        {
            float lengthSquared = Add(Add(Mul(value.x, value.x), Mul(value.y, value.y)), Mul(value.z, value.z));
            if (!Finite(lengthSquared) || !(lengthSquared > 0f))
                throw new ArgumentException("Degenerate " + label + ".");
            float length = (float)Math.Sqrt((double)lengthSquared);
            float reciprocal = Divide(1f, length);
            K.Float3 result = new K.Float3(Mul(value.x, reciprocal), Mul(value.y, reciprocal), Mul(value.z, reciprocal));
            ValidateFinite(result, label);
            return result;
        }

        private static K.Float4 Normalize(K.Float4 value, string label)
        {
            float xx = Mul(value.x, value.x);
            float yy = Mul(value.y, value.y);
            float zz = Mul(value.z, value.z);
            float ww = Mul(value.w, value.w);
            float lengthSquared = Add(Add(xx, yy), Add(zz, ww));
            if (!Finite(lengthSquared) || !(lengthSquared > 0f))
                throw new ArgumentException("Degenerate " + label + ".");
            float reciprocal = Divide(1f, (float)Math.Sqrt((double)lengthSquared));
            K.Float4 result = Mul(value, Splat(reciprocal));
            ValidateFinite(result, label);
            return result;
        }

        private static K.Float3 Cross(K.Float3 left, K.Float3 right) => new K.Float3(
            Sub(Mul(left.y, right.z), Mul(left.z, right.y)),
            Sub(Mul(left.z, right.x), Mul(left.x, right.z)),
            Sub(Mul(left.x, right.y), Mul(left.y, right.x)));

        private static K.Float3 Add(K.Float3 left, K.Float3 right) => new K.Float3(
            Add(left.x, right.x), Add(left.y, right.y), Add(left.z, right.z));
        private static K.Float4 Add(K.Float4 left, K.Float4 right) => new K.Float4(
            Add(left.x, right.x), Add(left.y, right.y), Add(left.z, right.z), Add(left.w, right.w));
        private static K.Float4 Sub(K.Float4 left, K.Float4 right) => new K.Float4(
            Sub(left.x, right.x), Sub(left.y, right.y), Sub(left.z, right.z), Sub(left.w, right.w));
        private static K.Float4 Mul(K.Float4 left, K.Float4 right) => new K.Float4(
            Mul(left.x, right.x), Mul(left.y, right.y), Mul(left.z, right.z), Mul(left.w, right.w));
        private static K.Float4 Splat(float value) => new K.Float4(value, value, value, value);

        private static K.Float4 Shuffle(K.Float4 value, int immediate) => new K.Float4(
            GetLane(value, immediate & 3),
            GetLane(value, (immediate >> 2) & 3),
            GetLane(value, (immediate >> 4) & 3),
            GetLane(value, (immediate >> 6) & 3));

        private static float GetLane(K.Float4 value, int lane)
        {
            switch (lane) { case 0: return value.x; case 1: return value.y; case 2: return value.z; default: return value.w; }
        }

        private static void SetLane(ref K.Float4 value, int lane, float laneValue)
        {
            switch (lane) { case 0: value.x = laneValue; break; case 1: value.y = laneValue; break; case 2: value.z = laneValue; break; default: value.w = laneValue; break; }
        }

        private static float SmoothLane(float oldValue, float blend) =>
            Add(oldValue, Mul(blend, Sub(0f, oldValue)));

        private static void ValidateInputs(K.Double3[] positions, K.Float4[] rotations, K.Float4[] bindRotations,
            ushort[] fixedIndices, int startIndex, int count)
        {
            if (positions == null || rotations == null || bindRotations == null || fixedIndices == null)
                throw new ArgumentNullException("Fixed-center inputs cannot be null.");
            if (positions.Length != rotations.Length || positions.Length != bindRotations.Length)
                throw new ArgumentException("Proxy position and rotation arrays must have identical lengths.");
            if (count <= 0 || startIndex < 0 || startIndex > fixedIndices.Length - count)
                throw new ArgumentOutOfRangeException(nameof(count), "Fixed-center range must be nonempty and in bounds.");
            for (int ordinal = startIndex; ordinal < startIndex + count; ordinal++)
            {
                int index = fixedIndices[ordinal];
                if (index >= positions.Length) throw new ArgumentOutOfRangeException(nameof(fixedIndices));
                ValidateFinite(positions[index], nameof(positions));
                ValidateQuaternion(rotations[index], nameof(rotations));
                ValidateQuaternion(bindRotations[index], nameof(bindRotations));
            }
        }

        private static void ValidateFinite(K.Double3 value, string label)
        {
            if (!Finite(value.x) || !Finite(value.y) || !Finite(value.z)) throw new ArgumentOutOfRangeException(label);
        }
        private static void ValidateFinite(K.Float3 value, string label)
        {
            if (!Finite(value.x) || !Finite(value.y) || !Finite(value.z)) throw new ArgumentOutOfRangeException(label);
        }
        private static void ValidateFinite(K.Float4 value, string label)
        {
            if (!Finite(value.x) || !Finite(value.y) || !Finite(value.z) || !Finite(value.w)) throw new ArgumentOutOfRangeException(label);
        }
        private static void ValidateQuaternion(K.Float4 value, string label)
        {
            ValidateFinite(value, label);
            float lengthSquared = Add(Add(Mul(value.x, value.x), Mul(value.y, value.y)),
                Add(Mul(value.z, value.z), Mul(value.w, value.w)));
            if (!Finite(lengthSquared) || !(lengthSquared > 0f))
                throw new ArgumentException("Degenerate quaternion.", label);
        }
        private static bool Finite(float value) => !float.IsNaN(value) && !float.IsInfinity(value);
        private static bool Finite(double value) => !double.IsNaN(value) && !double.IsInfinity(value);
        private static uint Bits(float value) => BitConverter.ToUInt32(BitConverter.GetBytes(value), 0);
        private static float FromBits(uint value) => BitConverter.ToSingle(BitConverter.GetBytes(value), 0);

        [MethodImpl(MethodImplOptions.NoInlining)] private static float Add(float left, float right) => left + right;
        [MethodImpl(MethodImplOptions.NoInlining)] private static float Sub(float left, float right) => left - right;
        [MethodImpl(MethodImplOptions.NoInlining)] private static float Mul(float left, float right) => left * right;
        [MethodImpl(MethodImplOptions.NoInlining)] private static float Divide(float left, float right) => left / right;
        [MethodImpl(MethodImplOptions.NoInlining)] private static double Add(double left, double right) => left + right;
        [MethodImpl(MethodImplOptions.NoInlining)] private static double Divide(double left, double right) => left / right;
    }
}
