using System;
using UnityEditor;
using UnityEngine;

namespace EndfieldGraphShaderLabEditor
{
    public static class EndfieldSecondaryDynamicsKernelGoldenVerifier
    {
        private readonly struct Case
        {
            public readonly string name;
            public readonly EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Double3 current;
            public readonly EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Double3 basic;
            public readonly string[] nextBits;
            public readonly string[] velocityBits;

            public Case(string name, double x, double y, double z, double bx, double by, double bz, string[] nextBits, string[] velocityBits)
            {
                this.name = name;
                current = new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Double3(x, y, z);
                basic = new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Double3(bx, by, bz);
                this.nextBits = nextBits;
                this.velocityBits = velocityBits;
            }
        }

        private static readonly Case[] Cases =
        {
            new Case("stretch_full_axis", 2, 0, 0, 1, 0, 0,
                new[] { "000000a09999f13f", "0000000000000000", "0000000000000000" },
                new[] { "e07a142685ebf53f", "0000000000000000", "0000000000000000" }),
            new Case("compression_full_axis", 0.5, 0, 0, 1, 0, 0,
                new[] { "000000c0ccccec3f", "0000000000000000", "0000000000000000" },
                new[] { "400ad783c2f5e83f", "0000000000000000", "0000000000000000" }),
            new Case("dead_zone", 1.05, 0, 0, 1, 0, 0,
                new[] { "cdccccccccccf03f", "0000000000000000", "0000000000000000" },
                new[] { "cdccccccccccf03f", "0000000000000000", "0000000000000000" }),
            new Case("stretch_partial", 1.2, 0, 0, 1, 0, 0,
                new[] { "94f449afaaaaf23f", "0000000000000000", "0000000000000000" },
                new[] { "aba29170a0d3f23f", "0000000000000000", "0000000000000000" }),
            new Case("stretch_full_oblique", 2, 1, -0.5, 1, 0.5, -0.25,
                new[] { "000000a09999f13f", "000000a09999e13f", "000000a09999d1bf" },
                new[] { "e07a142685ebf53f", "e07a142685ebe53f", "e07a142685ebd5bf" }),
        };

        [MenuItem("Endfield/Character Recovery/Verify Secondary Dynamics Kernel Golden Vectors")]
        public static void VerifyMenu()
        {
            VerifyFloatSinCosGoldenVectors();
            VerifyTetherGoldenVectors();
            VerifyDistanceGoldenVectors();
            VerifyPointCollisionGoldenVectors();
            VerifyAngleGoldenVectors();
            VerifyBasicPostureGoldenVectors();
            VerifySimulationEndGoldenVectors();
            Debug.Log("Verified float sincos, Angle, tether, Distance, Point-capsule, BasicPosture, and Simulation End native AVX2 vectors exactly.");
        }

        public static void VerifyFloatSinCosGoldenVectors()
        {
            string[,] cases =
            {
                { "positive_zero", "00000000", "00000000", "0000803f" },
                { "negative_zero", "00000080", "00000080", "0000803f" },
                { "smallest_subnormal", "01000000", "01000000", "0000803f" },
                { "negative_smallest_subnormal", "01000080", "01000080", "0000803f" },
                { "one", "0000803f", "a46a573f", "40510a3f" },
                { "minus_one", "000080bf", "a46a57bf", "40510a3f" },
                { "pi_over_four", "db0f493f", "f404353f", "f304353f" },
                { "small_below_125", "fffff942", "38b51dbf", "5aa7493f" },
                { "small_at_125", "0000fa42", "d4b41dbf", "a8a7493f" },
                { "small_above_125", "0100fa42", "6fb41dbf", "f8a7493f" },
                { "negative_125", "0000fac2", "d4b41d3f", "a8a7493f" },
                { "medium_below_39000", "ff571847", "520b863e", "2812773f" },
                { "large_at_39000", "00581847", "33f9873e", "a6ce763f" },
                { "large_above_39000", "01581847", "8ce6893e", "2e8a763f" },
                { "negative_39000", "005818c7", "33f987be", "a6ce763f" },
                { "large_power", "0000004f", "c9a778bf", "1786733e" },
                { "very_large", "caf24971", "b0894abf", "21921cbf" },
                { "maximum_finite", "ffff7f7f", "b39905bf", "965f5a3f" },
                { "negative_maximum_finite", "ffff7fff", "b399053f", "965f5a3f" },
                { "positive_infinity", "0000807f", "0000c07f", "0000c07f" },
                { "negative_infinity", "000080ff", "0000c07f", "0000c07f" },
                { "quiet_nan_payload", "4523c17f", "0000c07f", "0000c07f" },
                { "negative_quiet_nan", "2143c5ff", "0000c07f", "0000c07f" },
                { "signaling_nan_payload", "4523a17f", "0000c07f", "0000c07f" },
            };
            for (int index = 0; index < cases.GetLength(0); index++)
            {
                float input = FloatFromLittleEndianHex(cases[index, 1]);
                EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.FloatSinCosBinary32(
                    input, out float sine, out float cosine);
                RequireFloatBits(cases[index, 0] + " sine", sine, cases[index, 2]);
                RequireFloatBits(cases[index, 0] + " cosine", cosine, cases[index, 3]);
            }
        }

        public static void VerifyTetherGoldenVectors()
        {
            var zero = new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Double3(0, 0, 0);
            foreach (Case row in Cases)
            {
                var next = row.current;
                var velocity = row.current;
                EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.ProjectTether(
                    zero, ref next, zero, row.basic, 0.1f, 0.1f, ref velocity);
                RequireBits(row.name + " next", next, row.nextBits);
                RequireBits(row.name + " velocityPos", velocity, row.velocityBits);
            }
        }

        public static void VerifyDistanceGoldenVectors()
        {
            float[] oneCurve = new float[16];
            for (int index = 0; index < oneCurve.Length; index++)
                oneCurve[index] = 1.0f;
            float[] depthCurve = new float[16];
            for (int index = 0; index < depthCurve.Length; index++)
                depthCurve[index] = index / 15.0f;

            VerifyDistanceCase("single_constraint_stretch",
                D3(0, 0, 0, 2, 0, 0), D3(0, 0, 0, 1, 0, 0),
                D3(0, 0, 0, 2, 0, 0), new byte[] { 2, 2 },
                new float[] { 0, 0 }, new float[] { 0, 0 },
                new ushort[] { 1 }, new float[] { 1 }, 1, oneCurve, 0.7f, 0,
                new[] { "000000000000e03f", "0000000000000000", "0000000000000000" },
                new[] { "000000606666d63f", "0000000000000000", "0000000000000000" }, 1);
            VerifyDistanceCase("single_constraint_compression",
                D3(0, 0, 0, 0.5, 0, 0), D3(0, 0, 0, 1, 0, 0),
                D3(0, 0, 0, 0.5, 0, 0), new byte[] { 2, 2 },
                new float[] { 0, 0 }, new float[] { 0, 0 },
                new ushort[] { 1 }, new float[] { 1 }, 1, oneCurve, 0.7f, 0,
                new[] { "000000000000d0bf", "0000000000000000", "0000000000000000" },
                new[] { "000000606666c6bf", "0000000000000000", "0000000000000000" }, 1);
            VerifyDistanceCase("negative_signed_rest_half_stiffness",
                D3(0, 0, 0, 2, 0, 0), D3(0, 0, 0, 1, 0, 0),
                D3(0, 0, 0, 2, 0, 0), new byte[] { 2, 2 },
                new float[] { 0, 0 }, new float[] { 0, 0 },
                new ushort[] { 1 }, new float[] { -1 }, 1, oneCurve, 0.7f, 0,
                new[] { "000000000000d03f", "0000000000000000", "0000000000000000" },
                new[] { "000000606666c63f", "0000000000000000", "0000000000000000" }, 1);
            VerifyDistanceCase("fractional_curve_stiffness",
                D3(0, 0, 0, 2, 1, -0.5), D3(0, 0, 0, 1, 0.5, -0.25),
                D3(0, 0, 0, 2, 1, -0.5), new byte[] { 2, 2 },
                new float[] { 0.37f, 0.62f }, new float[] { 0.2f, 0.4f },
                new ushort[] { 1 }, new float[] { 1 }, 0.8f, depthCurve, 0.65f, 0,
                new[] { "bfca09869e2dc33f", "bfca09869e2db33f", "bfca09869e2da3bf" },
                new[] { "8dd5813881eeb83f", "8dd5813881eea83f", "8dd5813881ee98bf" }, 1);
            VerifyDistanceCase("animation_pose_blend",
                D3(0, 0, 0, 2, 0, 0), D3(0, 0, 0, 1.5, 0, 0),
                D3(0, 0, 0, 2, 0, 0), new byte[] { 2, 2 },
                new float[] { 0, 0 }, new float[] { 0, 0 },
                new ushort[] { 1 }, new float[] { 1 }, 1, oneCurve, 0.7f, 0.25f,
                new[] { "000000000000dc3f", "0000000000000000", "0000000000000000" },
                new[] { "000000949999d33f", "0000000000000000", "0000000000000000" }, 1);
            VerifyDistanceCase("two_constraint_mean",
                D3(0, 0, 0, 2, 0, 0, 0, 2, 0), D3(0, 0, 0, 1, 0, 0, 0, 1, 0),
                D3(0, 0, 0, 2, 0, 0, 0, 2, 0), new byte[] { 2, 2, 2 },
                new float[] { 0, 0, 0 }, new float[] { 0, 0, 0 },
                new ushort[] { 1, 2 }, new float[] { 1, 1 }, 1, oneCurve, 0.7f, 0,
                new[] { "000000000000d03f", "000000000000d03f", "0000000000000000" },
                new[] { "000000606666c63f", "000000606666c63f", "0000000000000000" }, 2);
            VerifyDistanceCase("degenerate_constraint_no_write",
                D3(0.125, -0.25, 0.5, 0.125, -0.25, 0.5), D3(0, 0, 0, 1, 0, 0),
                D3(3, 4, 5, 0, 0, 0), new byte[] { 2, 2 },
                new float[] { 0, 0 }, new float[] { 0, 0 },
                new ushort[] { 1 }, new float[] { 1 }, 1, oneCurve, 0.7f, 0,
                new[] { "000000000000c03f", "000000000000d0bf", "000000000000e03f" },
                new[] { "0000000000000840", "0000000000001040", "0000000000001440" }, 0);
            VerifyDistanceCase("empty_packed_range_no_write",
                D3(-0.75, 0.5, 1.25, 2, 0, 0), D3(0, 0, 0, 1, 0, 0),
                D3(-2, 7, 0.25, 0, 0, 0), new byte[] { 2, 2 },
                new float[] { 0, 0 }, new float[] { 0, 0 },
                Array.Empty<ushort>(), Array.Empty<float>(), 1, oneCurve, 0.7f, 0,
                new[] { "000000000000e8bf", "000000000000e03f", "000000000000f43f" },
                new[] { "00000000000000c0", "0000000000001c40", "000000000000d03f" }, 0);
        }

        private static void VerifyDistanceCase(
            string name,
            EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Double3[] next,
            EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Double3[] basic,
            EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Double3[] velocity,
            byte[] attributes,
            float[] depths,
            float[] friction,
            ushort[] neighbors,
            float[] rest,
            float simulationPower,
            float[] curve,
            float velocityAttenuation,
            float animationPoseRatio,
            string[] nextBits,
            string[] velocityBits,
            int expectedAccepted)
        {
            int accepted = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.ProjectDistance(
                0, next, basic, velocity, attributes, depths, friction, neighbors, rest,
                simulationPower, curve, velocityAttenuation, animationPoseRatio, 1, 1, 0);
            if (accepted != expectedAccepted)
                throw new InvalidOperationException(name + " accepted count differs.");
            RequireBits(name + " next", next[0], nextBits);
            RequireBits(name + " velocityPos", velocity[0], velocityBits);
        }

        private static EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Double3[] D3(
            params double[] values)
        {
            var result = new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Double3[values.Length / 3];
            for (int index = 0; index < result.Length; index++)
                result[index] = new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Double3(
                    values[index * 3], values[index * 3 + 1], values[index * 3 + 2]);
            return result;
        }

        public static void VerifyPointCollisionGoldenVectors()
        {
            VerifyPointCase("static_capsule_penetration", 0.2, 0, 0,
                0, -1, 0, 0, 1, 0, 0, -1, 0, 0, 1, 0,
                0.3f, 0.3f, new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float4(0, 0, 0, 1),
                new[] { "000000a09999d93f", "0000000000000000", "0000000000000000" },
                "0000803f", new[] { "0000803f", "00000000", "00000000" }, 1);
            VerifyPointCase("no_contact_normal_zero", 0.6, 0, 0,
                0, -1, 0, 0, 1, 0, 0, -1, 0, 0, 1, 0,
                0.3f, 0.3f, new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float4(0, 0, 0, 1),
                new[] { "333333333333e33f", "0000000000000000", "0000000000000000" },
                "00000000", new[] { "00000000", "00000000", "00000000" }, 0);
            VerifyPointCase("translated_collider_transport", 0.2, 0, 0,
                0, -1, 0, 0, 1, 0, 0.1, -1, 0, 0.1, 1, 0,
                0.3f, 0.3f, new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float4(0, 0, 0, 1),
                new[] { "333333030000e03f", "0000000000000000", "0000000000000000" },
                "0000803f", new[] { "0000803f", "00000000", "00000000" }, 1);
            VerifyPointCase("rotated_collider_transport", 0.2, 0, 0,
                0, -1, 0, 0, 1, 0, 0, -1, 0, 0, 1, 0,
                0.3f, 0.3f, new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float4(0, 0, 0.7071067690849304f, 0.7071067690849304f),
                new[] { "9a9999999999c93f", "000000a09999d93f", "0000000000000000" },
                "0000803f", new[] { "00000000", "0000803f", "00000000" }, 1);
            VerifyPointCase("tapered_capsule_radius", 0.2, 0.5, 0,
                0, -1, 0, 0, 1, 0, 0, -1, 0, 0, 1, 0,
                0.2f, 0.4f, new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float4(0, 0, 0, 1),
                new[] { "000000e0ccccdc3f", "000000000000e03f", "0000000000000000" },
                "0000803f", new[] { "0000803f", "00000000", "00000000" }, 1);
            VerifyPointCase("friction_near_contact", 0.45, 0, 0,
                0, -1, 0, 0, 1, 0, 0, -1, 0, 0, 1, 0,
                0.3f, 0.3f, new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float4(0, 0, 0, 1),
                new[] { "cdccccccccccdc3f", "0000000000000000", "0000000000000000" },
                "0100003f", new[] { "0000803f", "00000000", "00000000" }, 0);
        }

        private static void VerifyPointCase(
            string name, double px, double py, double pz,
            double a0x, double a0y, double a0z, double a1x, double a1y, double a1z,
            double b0x, double b0y, double b0z, double b1x, double b1y, double b1z,
            float radius0, float radius1,
            EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float4 rotation,
            string[] nextBits, string frictionBits, string[] normalBits, int expectedCount)
        {
            var next = new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Double3(px, py, pz);
            var velocity = next;
            float friction = 0;
            var collider = new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.CapsuleColliderWork
            {
                flag = 0x32,
                aabbMin = new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Double3(-100, -100, -100),
                aabbMax = new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Double3(100, 100, 100),
                radius0 = radius0,
                radius1 = radius1,
                old0 = new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Double3(a0x, a0y, a0z),
                old1 = new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Double3(a1x, a1y, a1z),
                next0 = new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Double3(b0x, b0y, b0z),
                next1 = new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Double3(b1x, b1y, b1z),
                inverseOldRotation = new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float4(0, 0, 0, 1),
                rotation = rotation,
            };
            int count = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.ProjectPointCapsules(
                ref next, ref velocity, ref friction, out var normal, 0.1f,
                new[] { collider }, false);
            if (count != expectedCount)
                throw new InvalidOperationException(name + " penetrating count differs.");
            RequireBits(name + " next", next, nextBits);
            RequireFloatBits(name + " friction", friction, frictionBits);
            RequireFloatBits(name + " normal.x", normal.x, normalBits[0]);
            RequireFloatBits(name + " normal.y", normal.y, normalBits[1]);
            RequireFloatBits(name + " normal.z", normal.z, normalBits[2]);
        }

        private static void RequireFloatBits(string label, float value, string expected)
        {
            string bits = BitConverter.ToString(BitConverter.GetBytes(value))
                .Replace("-", "").ToLowerInvariant();
            if (!string.Equals(bits, expected, StringComparison.Ordinal))
                throw new InvalidOperationException(label + " differs: " + bits + " != " + expected);
        }

        private static float FloatFromLittleEndianHex(string value)
        {
            byte[] bytes = new byte[4];
            for (int index = 0; index < bytes.Length; index++)
                bytes[index] = Convert.ToByte(value.Substring(index * 2, 2), 16);
            return BitConverter.ToSingle(bytes, 0);
        }

        public static void VerifyAngleGoldenVectors()
        {
            string[] zeroDouble3 = { "0000000000000000", "0000000000000000", "0000000000000000" };
            VerifyAngleCase("restoration_only_aligned", 1, 0, false, 10, 1, true, 1, 0.6f, 0, 0, 0,
                zeroDouble3, new[] { "000000f4ffffef3f", "0000000000000000", "0000000000000000" },
                new[] { "000000e0cccc4cbe", "0000000000000000", "0000000000000000" },
                new[] { "00000000", "00000000", "00000000", "0000803f" }, "00000000",
                new[] { "00000000", "00000000", "00000000" },
                new[] { "00000000", "00000000", "00000000", "00000000" },
                new[] { "0000803f", "00000000", "00000000" });
            VerifyAngleCase("restoration_only_bent", 0, 1, false, 10, 1, true, 0.35f, 0.6f, 0, 0, 0,
                zeroDouble3, new[] { "46a6e58e362be83f", "4671f0f23815e33f", "0000000000000000" },
                new[] { "2cf302f2a700dd3f", "d46103344400cfbf", "0000000000000000" },
                new[] { "00000000", "00000000", "00000000", "0000803f" }, "00000000",
                new[] { "00000000", "00000000", "00000000" },
                new[] { "00000000", "00000000", "00000000", "00000000" },
                new[] { "0000803f", "00000000", "00000000" });
            VerifyAngleCase("hair_limit_inside_cone", 1, 0.08, true, 10, 1, false, 1, 0.6f, 0, 0, 0,
                zeroDouble3, new[] { "7a0e75150000f03f", "3e312563e17ab43f", "0000000000000000" },
                new[] { "9c600432c04f733e", "b2271d3e00b8383e", "0000000000000000" },
                new[] { "00000000", "00000000", "ca72233d", "cdcb7f3f" }, "b168803f",
                new[] { "0000803f", "00000000", "00000000" },
                new[] { "00000000", "00000000", "00000000", "0000803f" },
                new[] { "00000000", "00000000", "00000000" });
            VerifyAngleCase("hair_limit_outside_cone", 0, 1, true, 10, 1, false, 1, 0.6f, 0, 0, 0,
                zeroDouble3, new[] { "3aca53f5a096ec3f", "e67f4677324ece3f", "0000000000000000" },
                new[] { "d2288f04c4bae93f", "dec1649b34fbe5bf", "0000000000000000" },
                new[] { "00000000", "00000000", "a844043e", "fcda7d3f" }, "0000803f",
                new[] { "0000803f", "00000000", "00000000" },
                new[] { "00000000", "00000000", "00000000", "0000803f" },
                new[] { "00000000", "00000000", "00000000" });
            VerifyAngleCase("combined_limit_then_restoration", 0, 1, true, 10, 1, true, 0.125f, 0.6f, 0, 0, 0,
                zeroDouble3, new[] { "f26f70206710ed3f", "505d3c28b6f0c93f", "0000000000000000" },
                new[] { "005aec963eaee93f", "6aaf8512e61fe6bf", "0000000000000000" },
                new[] { "00000000", "00000000", "fb3def3d", "4d3f7e3f" }, "0000803f",
                new[] { "0000803f", "00000000", "00000000" },
                new[] { "00000000", "00000000", "00000000", "0000803f" },
                new[] { "0000803f", "00000000", "00000000" });
            VerifyAngleCase("active_parent_writeback", 0, 1, false, 10, 1, true, 0.125f, 0, 2, 0, 0,
                new[] { "00f65a623082c1bf", "80d2680518d1a83f", "0000000000000000" },
                new[] { "778748113ff6d63f", "e1c272446658ed3f", "0000000000000000" },
                zeroDouble3, new[] { "00000000", "00000000", "00000000", "0000803f" }, "00000000",
                new[] { "00000000", "00000000", "00000000" },
                new[] { "00000000", "00000000", "00000000", "00000000" },
                new[] { "0000803f", "00000000", "00000000" });
            VerifyAngleCase("friction_mobility", 0, 1, false, 10, 1, true, 0.35f, 0, 0, 0.25f, 0.75f,
                zeroDouble3, new[] { "f30f6c02e307e03f", "9d3fc6f9f9dfe83f", "0000000000000000" },
                zeroDouble3, new[] { "00000000", "00000000", "00000000", "0000803f" }, "00000000",
                new[] { "00000000", "00000000", "00000000" },
                new[] { "00000000", "00000000", "00000000", "00000000" },
                new[] { "0000803f", "00000000", "00000000" });
        }

        private static void VerifyAngleCase(
            string name, double childX, double childY,
            bool limit, float limitDegrees, float limitStiffness,
            bool restoration, float restorationStrength, float restorationVelocityAttenuation,
            byte parentAttribute, float parentFriction, float childFriction,
            string[] parentNextBits, string[] childNextBits, string[] childVelocityBits,
            string[] childRotationBits, string childLengthBits, string[] childLocalPositionBits,
            string[] childLocalRotationBits, string[] childRestorationBits)
        {
            var zero = new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Double3(0, 0, 0);
            var identity = new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float4(0, 0, 0, 1);
            var next = new[] { zero, new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Double3(childX, childY, 0) };
            var velocity = new[] { zero, zero };
            var rotations = new[] { default(EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float4), default(EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float4) };
            var lengths = new float[2];
            var localPositions = new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float3[2];
            var localRotations = new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float4[2];
            var restorationVectors = new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float3[2];
            float[] restorationCurve = ConstantCurve(restorationStrength);
            float[] limitCurve = ConstantCurve(limitDegrees);
            EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.ProjectAngle(
                new byte[] { parentAttribute, 2 }, new[] { 0.0f, 0.37f },
                new[] { parentFriction, childFriction },
                new[] { zero, new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Double3(1, 0, 0) },
                new[] { identity, identity }, next, velocity,
                restoration, restorationCurve, restorationVelocityAttenuation, 0,
                limit, limitCurve, limitStiffness, 1, 1,
                rotations, lengths, localPositions, localRotations, restorationVectors);

            RequireBits(name + " next parent", next[0], parentNextBits);
            RequireBits(name + " next child", next[1], childNextBits);
            RequireBits(name + " velocity parent", velocity[0], new[] { "0000000000000000", "0000000000000000", "0000000000000000" });
            RequireBits(name + " velocity child", velocity[1], childVelocityBits);
            RequireFloat4Bits(name + " rotation parent", rotations[0], new[] { "00000000", "00000000", "00000000", "0000803f" });
            RequireFloat4Bits(name + " rotation child", rotations[1], childRotationBits);
            RequireFloatBits(name + " length parent", lengths[0], "00000000");
            RequireFloatBits(name + " length child", lengths[1], childLengthBits);
            RequireFloat3Bits(name + " local position parent", localPositions[0], new[] { "00000000", "00000000", "00000000" });
            RequireFloat3Bits(name + " local position child", localPositions[1], childLocalPositionBits);
            RequireFloat4Bits(name + " local rotation parent", localRotations[0], new[] { "00000000", "00000000", "00000000", "00000000" });
            RequireFloat4Bits(name + " local rotation child", localRotations[1], childLocalRotationBits);
            RequireFloat3Bits(name + " restoration parent", restorationVectors[0], new[] { "00000000", "00000000", "00000000" });
            RequireFloat3Bits(name + " restoration child", restorationVectors[1], childRestorationBits);
        }

        private static float[] ConstantCurve(float value)
        {
            var result = new float[16];
            for (int index = 0; index < result.Length; index++)
                result[index] = value;
            return result;
        }

        private static void RequireFloat4Bits(string label,
            EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float4 value, string[] expected)
        {
            RequireFloatBits(label + ".x", value.x, expected[0]);
            RequireFloatBits(label + ".y", value.y, expected[1]);
            RequireFloatBits(label + ".z", value.z, expected[2]);
            RequireFloatBits(label + ".w", value.w, expected[3]);
        }

        public static void VerifyBasicPostureGoldenVectors()
        {
            var identity = new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float4(0, 0, 0, 1);
            VerifyBasicCase("root_identity_ratio_zero", new[] { -1 }, new byte[] { 2 },
                F3(0, 0, 0), F4(0, 0, 0, 1), F3(8, 9, 10), F4(0, 0, 0, 1),
                F3(1.25f, -2.5f, 3.75f), F4(0, 0, 0, 1),
                new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float3(1, 1, 1), 1,
                new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float3(1, 1, 1),
                new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float4(1, 1, 1, 1), 0,
                new[] { new[] { "0000a03f", "000020c0", "00007040" } },
                new[] { new[] { "00000000", "00000000", "00000000", "0000803f" } });
            VerifyBasicCase("child_positive_scale_ratio_zero", new[] { -1, 0 }, new byte[] { 2, 2 },
                F3(0, 0, 0, 1, 0.5f, -0.25f), F4(0, 0, 0, 1, 0, 0, 0.70710677f, 0.70710677f),
                F3(0, 0, 0, 0, 0, 0), F4(0, 0, 0, 1, 0, 0, 0, 1),
                F3(10, -1, 2, 99, 99, 99), F4(0, 0, 0, 1, 0, 0, 0, 1),
                new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float3(2, 3, 4), 0.5f,
                new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float3(1, 1, 1),
                new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float4(1, 1, 1, 1), 0,
                new[] { new[] { "00002041", "000080bf", "00000040" }, new[] { "00003041", "000080be", "0000c03f" } },
                new[] { new[] { "00000000", "00000000", "00000000", "0000803f" }, new[] { "00000000", "00000000", "f304353f", "f304353f" } });
            VerifyBasicCase("child_negative_scale_ratio_zero", new[] { -1, 0 }, new byte[] { 2, 2 },
                F3(0, 0, 0, 1, -0.5f, 0.25f), F4(0, 0, 0, 1, 0, 0, 0, 1),
                F3(0, 0, 0, 0, 0, 0), F4(0, 0, 0, 1, 0, 0, 0, 1),
                F3(-3, 4, 1, 50, 50, 50), F4(0, 0, 0, 1, 0, 0, 0, 1),
                new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float3(1, 1, 1), 1,
                new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float3(-1, 1, 1),
                new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float4(1, 1, 1, 1), 0,
                new[] { new[] { "000040c0", "00008040", "0000803f" }, new[] { "000080c0", "00006040", "0000a03f" } },
                new[] { new[] { "00000000", "00000000", "00000000", "0000803f" }, new[] { "00000000", "00000000", "00000000", "0000803f" } });
            VerifyBasicCase("partial_pose_position_and_nlerp", new[] { -1, 0 }, new byte[] { 2, 2 },
                F3(0, 0, 0, 2, 0, 0), F4(0, 0, 0, 1, 0, 0, 0, 1),
                F3(2, 4, 6, 6, 4, 6), F4(0, 0, 0.043619387f, 0.99904823f, 0, 0, 0.043619387f, 0.99904823f),
                F3(0, 0, 0, 0, 0, 0), F4(0, 0, 0, 1, 0, 0, 0, 1),
                new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float3(1, 1, 1), 1,
                new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float3(1, 1, 1),
                new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float4(1, 1, 1, 1), 0.25f,
                new[] { new[] { "0000003f", "0000803f", "0000c03f" }, new[] { "00004040", "0000803f", "0000c03f" } },
                new[] { new[] { "00000000", "00000000", "b6b7323c", "e5fb7f3f" }, new[] { "00000000", "00000000", "b6b7323c", "e5fb7f3f" } });
            VerifyBasicCase("partial_pose_representative_slerp", new[] { -1 }, new byte[] { 2 },
                F3(0, 0, 0), F4(0, 0, 0, 1), F3(3, -2, 1), F4(0, 0.70710677f, 0, 0.70710677f),
                F3(1, 2, 3), F4(0, 0, 0, 1),
                new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float3(1, 1, 1), 1,
                new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float3(1, 1, 1),
                new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float4(1, 1, 1, 1), 0.375f,
                new[] { new[] { "0000e03f", "0000003f", "00001040" } },
                new[] { new[] { "00000000", "32a0943e", "00000000", "0afa743f" } });
            VerifyBasicCase("pose_ratio_one_early_exit", new[] { -1, 0 }, new byte[] { 2, 2 },
                F3(0, 0, 0, 9, 9, 9), F4(0, 0, 0, 1, 0, 0, 0, 1),
                F3(7, 8, 9, 10, 11, 12), F4(0, 0, 0, 1, 0, 0, 0, 1),
                F3(-1, -2, -3, -4, -5, -6), F4(0, 0, 0, 1, 0.2f, 0.3f, 0.4f, 0.5f),
                new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float3(1, 1, 1), 1,
                new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float3(1, 1, 1),
                new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float4(1, 1, 1, 1), 1,
                new[] { new[] { "000080bf", "000000c0", "000040c0" }, new[] { "000080c0", "0000a0c0", "0000c0c0" } },
                new[] { new[] { "00000000", "00000000", "00000000", "0000803f" }, new[] { "cdcc4c3e", "9a99993e", "cdcccc3e", "0000003f" } });
        }

        private static void VerifyBasicCase(string name, int[] parents, byte[] attributes,
            EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float3[] localPositions,
            EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float4[] localRotations,
            EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float3[] basePositions,
            EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float4[] baseRotations,
            EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float3[] stepPositions,
            EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float4[] stepRotations,
            EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float3 initScale, float scaleRatio,
            EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float3 negativeScaleDirection,
            EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float4 negativeScaleQuaternion,
            float ratio, string[][] positionBits, string[][] rotationBits)
        {
            EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.UpdateBasicPosture(
                parents, attributes, localPositions, localRotations, basePositions, baseRotations,
                stepPositions, stepRotations, initScale, scaleRatio, negativeScaleDirection,
                negativeScaleQuaternion, ratio);
            for (int index = 0; index < stepPositions.Length; index++)
            {
                RequireFloatBits(name + " position.x", stepPositions[index].x, positionBits[index][0]);
                RequireFloatBits(name + " position.y", stepPositions[index].y, positionBits[index][1]);
                RequireFloatBits(name + " position.z", stepPositions[index].z, positionBits[index][2]);
                RequireFloatBits(name + " rotation.x", stepRotations[index].x, rotationBits[index][0]);
                RequireFloatBits(name + " rotation.y", stepRotations[index].y, rotationBits[index][1]);
                RequireFloatBits(name + " rotation.z", stepRotations[index].z, rotationBits[index][2]);
                RequireFloatBits(name + " rotation.w", stepRotations[index].w, rotationBits[index][3]);
            }
        }

        private static EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float3[] F3(params float[] values)
        {
            var result = new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float3[values.Length / 3];
            for (int i = 0; i < result.Length; i++)
                result[i] = new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float3(values[i * 3], values[i * 3 + 1], values[i * 3 + 2]);
            return result;
        }

        private static EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float4[] F4(params float[] values)
        {
            var result = new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float4[values.Length / 4];
            for (int i = 0; i < result.Length; i++)
                result[i] = new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float4(values[i * 4], values[i * 4 + 1], values[i * 4 + 2], values[i * 4 + 3]);
            return result;
        }

        public static void VerifySimulationEndGoldenVectors()
        {
            VerifySimulationEndCase("inactive_bypass", false, -1, 0, 0, 0,
                D3(2, 3, 4), D3(1, 1, 1), D3(1, 1, 1), 0, 0, F3v(0, 0, 0),
                new[] { "00000000", "00000000", "00000000" }, new[] { "00000040", "00008040", "0000c040" },
                new[] { "0000000000000040", "0000000000000840", "0000000000001040" }, "00000000", "00000000");
            VerifySimulationEndCase("active_unlimited", true, -1, 0, 0, 0,
                D3(2, 3, 4), D3(1, 1, 1), D3(1, 1, 1), 0, 0, F3v(0, 0, 0),
                new[] { "00000040", "00008040", "0000c040" }, new[] { "00000040", "00008040", "0000c040" },
                new[] { "0000000000000040", "0000000000000840", "0000000000001040" }, "00000000", "00000000");
            VerifySimulationEndCase("active_speed_limit", true, 2, 0, 0, 0,
                D3(2, 3, 4), D3(1, 1, 1), D3(1, 1, 1), 0, 0, F3v(0, 0, 0),
                new[] { "77d6083f", "77d6883f", "b341cd3f" }, new[] { "00000040", "00008040", "0000c040" },
                new[] { "0000000000000040", "0000000000000840", "0000000000001040" }, "00000000", "00000000");
            VerifySimulationEndCase("static_friction_accumulation", true, -1, 0, 0.5f, 0,
                D3(0.01, 0, 0), D3(0, 0, 0), D3(-0.5, 0, 0), 0.75f, 0.25f, F3v(0, 1, 0),
                new[] { "5c8f823f", "00000000", "00000000" }, new[] { "1ea7683c", "00000000", "00000000" },
                new[] { "d7a370bde3147d3f", "0000000000000000", "0000000000000000" }, "6766e63e", "e17a943e");
            VerifySimulationEndCase("static_friction_release", true, -1, 0, 0.1f, 0,
                D3(0.075, 0, 0), D3(0, 0, 0), D3(-0.5, 0, 0), 0.75f, 0.7f, F3v(0, 1, 0),
                new[] { "3333933f", "00000000", "00000000" }, new[] { "c3f5a83d", "00000000", "00000000" },
                new[] { "67666652b81ea53f", "0000000000000000", "0000000000000000" }, "6766e63e", "6666e63e");
            VerifySimulationEndCase("static_friction_no_contact_decay", true, -1, 0, 0.5f, 0,
                D3(2, 3, 4), D3(1, 1, 1), D3(1, 1, 1), 0.75f, 0.4f, F3v(0, 0, 0),
                new[] { "00000040", "00008040", "0000c040" }, new[] { "00000040", "00008040", "0000c040" },
                new[] { "0000000000000040", "0000000000000840", "0000000000001040" }, "6766e63e", "3333b33e");
            VerifySimulationEndCase("dynamic_friction_attenuation", true, -1, 0.8f, 0, 0,
                D3(1, 0, 0), D3(0, 0, 0), D3(0, 0, 0), 0.5f, 0, F3v(0, 1, 0),
                new[] { "3333b33f", "00000000", "00000000" }, new[] { "00000040", "00000000", "00000000" },
                new[] { "000000000000f03f", "0000000000000000", "0000000000000000" }, "9a99993e", "00000000");
            VerifySimulationEndCase("center_centrifugal_response", true, -1, 0, 0, 0.5f,
                D3(2, 0, 0), D3(1, 0, 0), D3(2, 0, 1), 0, 0, F3v(0, 0, 0),
                new[] { "295c0f3e", "00000000", "000000c0" }, new[] { "00000040", "00000000", "00000000" },
                new[] { "0000000000000040", "0000000000000000", "0000000000000000" }, "00000000", "00000000",
                2, F3v(0, 1, 0));
        }

        private static void VerifySimulationEndCase(string name, bool active, float speedLimit,
            float dynamicFriction, float staticFrictionParameter, float centrifugalAcceleration,
            EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Double3 next,
            EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Double3 previous,
            EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Double3 velocityPosition,
            float friction, float staticFriction,
            EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float3 collisionNormal,
            string[] velocityBits, string[] realVelocityBits, string[] correctedBits,
            string frictionBits, string staticFrictionBits, float angularVelocity = 0,
            EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float3 axis = default)
        {
            var velocity = F3v(99, 99, 99);
            var realVelocity = F3v(99, 99, 99);
            EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.FinishSimulationParticle(
                active, 0.5f, 1, 1, speedLimit, centrifugalAcceleration, dynamicFriction,
                staticFrictionParameter, 0.25f, D3(0, 0, 0), angularVelocity,
                angularVelocity == 0 ? F3v(0, 1, 0) : axis, ref next, previous,
                ref velocityPosition, ref velocity, ref realVelocity, ref friction,
                ref staticFriction, collisionNormal);
            RequireFloat3Bits(name + " velocity", velocity, velocityBits);
            RequireFloat3Bits(name + " realVelocity", realVelocity, realVelocityBits);
            RequireBits(name + " corrected", next, correctedBits);
            RequireFloatBits(name + " friction", friction, frictionBits);
            RequireFloatBits(name + " staticFriction", staticFriction, staticFrictionBits);
        }

        private static EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Double3 D3(double x, double y, double z)
        {
            return new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Double3(x, y, z);
        }

        private static EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float3 F3v(float x, float y, float z)
        {
            return new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float3(x, y, z);
        }

        private static void RequireFloat3Bits(string label,
            EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Float3 value, string[] expected)
        {
            RequireFloatBits(label + ".x", value.x, expected[0]);
            RequireFloatBits(label + ".y", value.y, expected[1]);
            RequireFloatBits(label + ".z", value.z, expected[2]);
        }

        private static void RequireBits(
            string label,
            EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels.Double3 value,
            string[] expected)
        {
            double[] actual = { value.x, value.y, value.z };
            for (int index = 0; index < 3; index++)
            {
                string bits = BitConverter.ToString(BitConverter.GetBytes(actual[index]))
                    .Replace("-", "").ToLowerInvariant();
                if (!string.Equals(bits, expected[index], StringComparison.Ordinal))
                    throw new InvalidOperationException(
                        label + "[" + index + "] differs: " + bits + " != " + expected[index]);
            }
        }
    }
}
