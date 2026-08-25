using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using Helper = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsCenterAggregation;
using K = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels;

namespace EndfieldGraphShaderLabEditor
{
    public static class EndfieldSecondaryDynamicsCenterAggregationVerifier
    {
        private static readonly ushort[] Ribbon2 = { 0 };
        private static readonly ushort[] Hair = { 0, 3, 7, 10, 13, 17, 22, 26 };
        private static readonly ushort[] Ribbon = { 0, 6, 10, 16 };
        private static readonly ushort[] Coat = { 2, 4, 12, 26, 28, 33, 45, 47, 55 };

        [MenuItem("Endfield/Character Recovery Lab/Verify Secondary Dynamics Center Aggregation")]
        public static void VerifyMenu()
        {
            Verify();
            Debug.Log("Verified all 13 CalcCenter contract vectors bit-exact for Endminf fixed-center aggregation and stationary-root smoothing.");
        }

        public static void Verify()
        {
            int verified = 0;
            VerifyFixed("ribbon2 planar", Ribbon2, false,
                "000000000000f03f00000000000000000000000000000000", "0000000000000000441daf3eb18f703f"); verified++;
            VerifyFixed("hair planar", Hair, false,
                "0000000000802a40000000000080384000000000008028c0", "00000000000000009b01073fcc81593f"); verified++;
            VerifyFixed("ribbon planar", Ribbon, false,
                "0000000000002240000000000000304000000000000020c0", "0000000000000000778c093f80e8573f"); verified++;
            VerifyFixed("coat planar", Coat, false,
                "0000000000003d400000000000004c400000000000003cc0", "000000000000000089990c3f13ef553f"); verified++;
            VerifyFixed("hair spatial", Hair, true,
                "0000000000802a40000000000080384000000000008028c0", "6c8b493ed825383dcea5063f8781533f"); verified++;
            VerifyFixed("ribbon spatial", Ribbon, true,
                "0000000000002240000000000000304000000000000020c0", "581b0c3e83a2b43c586e093f9d0c553f"); verified++;
            VerifyFixed("coat spatial", Coat, true,
                "0000000000003d400000000000004c400000000000003cc0", "f8de473ed50e923d65890b3f67ee4f3f"); verified++;

            VerifyAnimated("hair", Hair,
                "0000000000802a40000000000080384000000000008028c0", "00000000000000009b01073fcc81593f",
                "efa7c64b37892a4091ed7c3f357e384039b4c876be7f28c0", "0000000000000000388d163f1c0d4f3f"); verified += 2;
            VerifyAnimated("coat", Coat,
                "0000000000003d400000000000004c400000000000003cc0", "000000000000000089990c3f13ef553f",
                "85eb51b81e053d40e4d022dbf9fe4b406fa575dfe2ff3bc0", "000000000000000083eb1c3f79444a3f"); verified += 2;

            VerifySmoothing("hair"); verified++;
            VerifySmoothing("coat"); verified++;
            Require(verified == 13, "contract vector count");
            VerifyRejectedBoundaries();
        }

        private static void VerifyFixed(string label, ushort[] fixedIndices, bool spatial,
            string expectedPosition, string expectedRotation)
        {
            BuildSynthetic(fixedIndices, spatial, out K.Double3[] positions, out K.Float4[] rotations,
                out K.Float4[] binds);
            Helper.Result result = Helper.AggregateFixed(positions, rotations, binds, fixedIndices, 0, fixedIndices.Length);
            RequireHex(result.Position, expectedPosition, label + " position");
            RequireHex(result.Rotation, expectedRotation, label + " rotation");
        }

        private static void VerifyAnimated(string label, ushort[] fixedIndices,
            string bootstrapPosition, string bootstrapRotation, string animatedPosition, string animatedRotation)
        {
            BuildSynthetic(fixedIndices, false, out K.Double3[] positions, out K.Float4[] rotations,
                out K.Float4[] binds);
            Helper.Result bootstrap = Helper.AggregateFixed(positions, rotations, binds, fixedIndices, 0, fixedIndices.Length);
            RequireHex(bootstrap.Position, bootstrapPosition, label + " bootstrap position");
            RequireHex(bootstrap.Rotation, bootstrapRotation, label + " bootstrap rotation");

            for (int ordinal = 0; ordinal < fixedIndices.Length; ordinal++)
            {
                int index = fixedIndices[ordinal];
                K.Double3 p = positions[index];
                positions[index] = new K.Double3(
                    p.x + 0.004 * (ordinal + 1), p.y - 0.002 * ordinal, p.z + 0.001 * (ordinal & 1));
                float angle = F32((34.0 + (index % 12) * 5.0 + ordinal * 1.25) * 0.008726646259971648);
                rotations[index] = Q(0f, 0f, F32(Math.Sin(angle)), F32(Math.Cos(angle)));
            }

            Helper.Result animated = Helper.AggregateFixed(positions, rotations, binds, fixedIndices, 0, fixedIndices.Length);
            RequireHex(animated.Position, animatedPosition, label + " animated position");
            RequireHex(animated.Rotation, animatedRotation, label + " animated rotation");
        }

        private static void VerifySmoothing(string label)
        {
            K.Float3 first = Helper.SmoothStationaryRootVelocity(F3(9f, -10f, 11f), 0.4f);
            K.Float3 second = Helper.SmoothStationaryRootVelocity(first, 0.4f);
            RequireHex(first, "b988df40065ff8c0aa9a0841", label + " smoothing first");
            RequireHex(second, "8a7fad4099c6c0c0a90dd440", label + " smoothing second");
        }

        private static void BuildSynthetic(ushort[] fixedIndices, bool spatial,
            out K.Double3[] positions, out K.Float4[] rotations, out K.Float4[] binds)
        {
            int length = 0;
            foreach (ushort index in fixedIndices) length = Math.Max(length, index + 1);
            positions = new K.Double3[length];
            rotations = new K.Float4[length];
            binds = new K.Float4[length];
            for (int index = 0; index < length; index++)
            {
                positions[index] = new K.Double3(index + 1.0, 2.0 * index, -index);
                float angle = F32((30.0 + (index % 12) * 5.0) * 0.008726646259971648);
                K.Float4 planar = Q(0f, 0f, F32(Math.Sin(angle)), F32(Math.Cos(angle)));
                float bindAngle = F32(10.0 * 0.008726646259971648);
                K.Float4 planarBind = Q(0f, 0f, F32(Math.Sin(bindAngle)), F32(Math.Cos(bindAngle)));
                if (!spatial)
                {
                    rotations[index] = planar;
                    binds[index] = planarBind;
                    continue;
                }

                float xAngle = F32((7.0 + (index % 5) * 3.0) * 0.008726646259971648);
                float yAngle = F32((-11.0 + (index % 7) * 2.0) * 0.008726646259971648);
                K.Float4 qx = Q(F32(Math.Sin(xAngle)), 0f, 0f, F32(Math.Cos(xAngle)));
                K.Float4 qy = Q(0f, F32(Math.Sin(yAngle)), 0f, F32(Math.Cos(yAngle)));
                rotations[index] = SourceHamilton(SourceHamilton(planar, qy), qx);
                binds[index] = SourceHamilton(planarBind, qx);
            }
        }

        // Contract fixture generation uses this scalar binary32 Hamilton order.
        private static K.Float4 SourceHamilton(K.Float4 a, K.Float4 b) => Q(
            Add(Add(Mul(a.w, b.x), Mul(a.x, b.w)), Sub(Mul(a.y, b.z), Mul(a.z, b.y))),
            Add(Sub(Mul(a.w, b.y), Mul(a.x, b.z)), Add(Mul(a.y, b.w), Mul(a.z, b.x))),
            Add(Add(Mul(a.w, b.z), Mul(a.x, b.y)), Sub(Mul(a.z, b.w), Mul(a.y, b.x))),
            Sub(Sub(Mul(a.w, b.w), Mul(a.x, b.x)), Add(Mul(a.y, b.y), Mul(a.z, b.z))));

        private static void VerifyRejectedBoundaries()
        {
            K.Double3[] positions = { new K.Double3(0, 0, 0) };
            K.Float4[] rotations = { Q(0, 0, 0, 1) };
            ushort[] one = { 0 };
            Expect<ArgumentOutOfRangeException>(() => Helper.AggregateFixed(positions, rotations, rotations, one, 0, 0), "empty range");
            Expect<ArgumentException>(() => Helper.AggregateFixed(positions, new K.Float4[0], rotations, one, 0, 1), "malformed topology");
            positions[0] = new K.Double3(double.NaN, 0, 0);
            Expect<ArgumentOutOfRangeException>(() => Helper.AggregateFixed(positions, rotations, rotations, one, 0, 1), "nonfinite position");
            positions[0] = new K.Double3(0, 0, 0);
            rotations[0] = Q(0, 0, 0, 0);
            Expect<ArgumentException>(() => Helper.AggregateFixed(positions, rotations, rotations, one, 0, 1), "degenerate basis");
            Expect<ArgumentOutOfRangeException>(() => Helper.SmoothStationaryRootVelocity(F3(float.PositiveInfinity, 0, 0), 0.4f), "nonfinite velocity");
            Expect<ArgumentOutOfRangeException>(() => Helper.SmoothStationaryRootVelocity(F3(0, 0, 0), 1.1f), "unsupported smoothing");
        }

        private static void RequireHex(K.Double3 value, string expected, string label) =>
            Require(Hex(Doubles(value.x, value.y, value.z)) == expected, label);
        private static void RequireHex(K.Float3 value, string expected, string label) =>
            Require(Hex(Floats(value.x, value.y, value.z)) == expected, label);
        private static void RequireHex(K.Float4 value, string expected, string label) =>
            Require(Hex(Floats(value.x, value.y, value.z, value.w)) == expected, label);

        private static byte[] Doubles(params double[] values)
        {
            var bytes = new List<byte>();
            foreach (double value in values) bytes.AddRange(BitConverter.GetBytes(value));
            return bytes.ToArray();
        }
        private static byte[] Floats(params float[] values)
        {
            var bytes = new List<byte>();
            foreach (float value in values) bytes.AddRange(BitConverter.GetBytes(value));
            return bytes.ToArray();
        }
        private static string Hex(byte[] bytes) => BitConverter.ToString(bytes).Replace("-", "").ToLowerInvariant();
        private static K.Float3 F3(float x, float y, float z) => new K.Float3(x, y, z);
        private static K.Float4 Q(float x, float y, float z, float w) => new K.Float4(x, y, z, w);
        private static float F32(double value) => (float)value;
        private static float Add(float left, float right) => left + right;
        private static float Sub(float left, float right) => left - right;
        private static float Mul(float left, float right) => left * right;

        private static void Require(bool condition, string label)
        {
            if (!condition) throw new InvalidOperationException("Center aggregation verification failed: " + label);
        }
        private static void Expect<T>(Action action, string label) where T : Exception
        {
            try { action(); }
            catch (T) { return; }
            throw new InvalidOperationException("Expected " + typeof(T).Name + " for " + label + ".");
        }
    }
}
