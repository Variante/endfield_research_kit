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
            VerifyTetherGoldenVectors();
            Debug.Log("Verified five native AVX2 tether golden vectors exactly.");
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
