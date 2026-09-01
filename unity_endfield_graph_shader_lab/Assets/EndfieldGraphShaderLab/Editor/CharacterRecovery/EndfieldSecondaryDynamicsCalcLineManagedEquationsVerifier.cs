using System;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEngine;
using K = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels;
using C = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsCalcLineManagedEquations;

namespace EndfieldGraphShaderLabEditor
{
    public static class EndfieldSecondaryDynamicsCalcLineManagedEquationsVerifier
    {
        [MenuItem("Endfield/Character Recovery/Verify Secondary Dynamics CalcLine Managed Equations")]
        public static void VerifyMenu()
        {
            VerifyPackedChildIndex();
            VerifyParallelAndQuarterTurnGoldenCases();
            VerifyAntiparallelAxisSelection();
            VerifyBinary32HelperGrouping();
            VerifyParentAndChildEquations();
            VerifyPerChildDirectionAndParentSum();
            VerifyEmptyAndUndefinedBranchesFailClosed();
            Debug.Log(
                "Verified value-only secondary-dynamics CalcLine managed equations; " +
                "runtime route and IFix selection remain fail-closed.");
        }

        private static void VerifyPackedChildIndex()
        {
            C.ChildIndex decoded = C.DecodeChildIndex((0xabcU << 20) | 0x54321U);
            Require(decoded.count == 0xabc, "packed child count");
            Require(decoded.localStart == 0x54321, "packed child local start");
        }

        private static void VerifyParallelAndQuarterTurnGoldenCases()
        {
            Require(C.TryFromToRotation(
                D(4.0, 0.0, 0.0),
                D(7.0, 0.0, 0.0),
                0.37,
                out K.Float4 parallel), "parallel FromToRotation");
            RequireQuaternionBits(
                parallel,
                0x00000000U, 0x00000000U, 0x00000000U, 0x3f800000U,
                "parallel identity");

            Require(C.TryFromToRotation(
                D(1.0, 0.0, 0.0),
                D(0.0, 1.0, 0.0),
                1.0,
                out K.Float4 axisAngle), "ninety-degree FromToRotation");
            RequireQuaternionBits(
                axisAngle,
                0x00000000U, 0x00000000U, 0x3f3504f4U, 0x3f3504f3U,
                "pinned float-half-angle AxisAngle");

            Require(C.TryFromToRotation(
                D(1.0, 0.0, 0.0),
                D(0.0, 1.0, 0.0),
                0.5,
                out K.Float4 quarterTurn), "quarter-turn FromToRotation");
            RequireQuaternionBits(
                quarterTurn,
                0x00000000U, 0x00000000U, 0x3ec3ef16U, 0x3f6c835eU,
                "half interpolation of ninety degrees");
        }

        private static void VerifyAntiparallelAxisSelection()
        {
            Require(C.TryFromToRotation(
                D(1.0, 0.0, 0.0),
                D(-1.0, 0.0, 0.0),
                1.0,
                out K.Float4 positiveZ), "x antiparallel branch");
            RequireQuaternionBits(
                positiveZ,
                0x00000000U, 0x00000000U, 0x3f800000U, 0xb33bbd2eU,
                "x antiparallel deterministic axis");

            Require(C.TryFromToRotation(
                D(0.0, 1.0, 0.0),
                D(0.0, -1.0, 0.0),
                1.0,
                out K.Float4 negativeZ), "y antiparallel branch");
            RequireQuaternionBits(
                negativeZ,
                0x00000000U, 0x00000000U, 0xbf800000U, 0xb33bbd2eU,
                "y antiparallel deterministic axis");

            // For finite negative X -> positive X, the pinned comparison chooses
            // positive X as its reference. Their cross product is zero. The
            // source then normalizes that zero axis without a guard, so this
            // value model must refuse to claim a quaternion for that case.
            Require(!C.TryFromToRotation(
                D(-1.0, 0.0, 0.0),
                D(1.0, 0.0, 0.0),
                1.0,
                out _), "negative-X antiparallel zero-axis branch must fail closed");
        }

        private static void VerifyBinary32HelperGrouping()
        {
            // Exact bit inputs deliberately distinguish the pinned grouping
            // from a left-associated Hamilton expression. Pinned y/z are
            // 4100ceb8/c18426e4; reassociation gives 4100ceb7/c18426e3.
            K.Float4 hamiltonLeft = QB(
                0x3f1c497cU, 0x40930be2U, 0x404c5865U, 0xc05dcaf9U);
            K.Float4 hamiltonRight = QB(
                0xc0452e61U, 0xc0e32288U, 0x40e41e55U, 0xbf03634aU);
            K.Float4 hamilton = C.MultiplyQuaternionBinary32(
                hamiltonLeft,
                hamiltonRight);
            RequireQuaternionBits(
                hamilton,
                0x428391bcU, 0x4100ceb8U, 0xc18426e4U, 0x41583d0cU,
                "pinned Hamilton grouping");

            // These exact inputs similarly distinguish the quaternion-vector
            // grouping. Pinned x/y are c2d5a4b6/c4e22f5c; a reassociated
            // expression produces c2d5a4b8/c4e22f5b.
            K.Float4 rotateQuaternion = QB(
                0xc0acdd5dU, 0x40988ce0U, 0x40dfbac4U, 0x3fa48ce5U);
            K.Float3 rotateVector = FB(
                0x3effe6ffU, 0x40f180e6U, 0xc0f71857U);
            K.Float3 rotated = C.RotateQuaternionBinary32(
                rotateQuaternion,
                rotateVector);
            RequireFloat3Bits(
                rotated,
                0xc2d5a4b6U, 0xc4e22f5cU, 0x448f898eU,
                "pinned quaternion-vector grouping");
        }

        private static void VerifyParentAndChildEquations()
        {
            var parent = new C.ParentSource(
                D(0.0, 0.0, 0.0),
                Q(0.0f, 0.0f, 0.0f, 1.0f),
                F(1.0f, 1.0f, 1.0f),
                Q(-1.0f, 1.0f, -1.0f, 1.0f),
                C.FlagMove,
                0.5,
                0.25);
            var children = new[]
            {
                new C.ChildSource(
                    D(0.0, 1.0, 0.0),
                    F(1.0f, 0.0f, 0.0f),
                    Q(0.0f, 0.0f, 0.70710677f, 0.70710677f),
                    C.FlagMove),
            };
            Require(C.TryCalculateParent(parent, children, out C.ParentValue result),
                "single-child parent equation");
            Require(result.hasChildren && result.children.Length == 1, "single child result");
            RequireDouble3(result.restSum, D(1.0, 0.0, 0.0), "rest sum");
            RequireDouble3(result.directionAccumulator, D(0.0, 1.0, 0.0), "direction sum");
            RequireQuaternionBits(
                result.rotation,
                0x00000000U, 0x00000000U, 0x3ec3ef16U, 0x3f6c835eU,
                "move parent interpolation");

            // Signed local rotation is componentwise before Hamilton products.
            // local z is negated, then the +90-degree child FromTo cancels it.
            RequireQuaternionBits(
                result.children[0].rotation,
                0x00000000U, 0x00000000U, 0x33000000U, 0x3f800000U,
                "signed local and child FromTo order");
        }

        private static void VerifyPerChildDirectionAndParentSum()
        {
            var parent = new C.ParentSource(
                D(0.0, 0.0, 0.0),
                Q(0.0f, 0.0f, 0.0f, 1.0f),
                F(1.0f, 1.0f, 1.0f),
                Q(1.0f, 1.0f, 1.0f, 1.0f),
                0,
                0.1,
                1.0);
            var children = new[]
            {
                Child(D(3.0, 0.0, 0.0), F(1.0f, 0.0f, 0.0f), C.FlagMove),
                Child(D(99.0, 99.0, 99.0), F(0.0f, 2.0f, 0.0f), 0),
                Child(D(0.0, 0.0, 4.0), F(0.0f, 0.0f, 1.0f), C.FlagMove),
            };
            Require(C.TryCalculateParent(parent, children, out C.ParentValue result),
                "mixed move/non-move parent equation");

            // Every child uses its own direction for child FromTo. The parent
            // accumulator independently adds all three child directions.
            RequireDouble3(
                result.children[1].childDirection,
                D(0.0, 2.0, 0.0),
                "non-move child direction uses rest vector");
            RequireDouble3(
                result.directionAccumulator,
                D(3.0, 2.0, 4.0),
                "parent direction sums every child direction");
            RequireDouble3(result.restSum, D(1.0, 2.0, 1.0), "ordered rest sum");
        }

        private static void VerifyEmptyAndUndefinedBranchesFailClosed()
        {
            C.ParentSource parent = IdentityParent();
            Require(C.TryCalculateParent(parent, Array.Empty<C.ChildSource>(), out C.ParentValue empty),
                "zero-child branch");
            Require(!empty.hasChildren && empty.children.Length == 0, "zero-child no-write marker");
            RequireQuaternionBits(
                empty.rotation,
                0x00000000U, 0x00000000U, 0x00000000U, 0x3f800000U,
                "zero-child preserves parent rotation");

            Require(!C.TryFromToRotation(
                D(0.0, 0.0, 0.0), D(1.0, 0.0, 0.0), 1.0, out _),
                "zero FromTo input must fail closed");
            Require(!C.TryFromToRotation(
                D(double.NaN, 0.0, 0.0), D(1.0, 0.0, 0.0), 1.0, out _),
                "non-finite FromTo input must fail closed");

            C.ChildSource degenerate = Child(
                D(1.0, 0.0, 0.0), F(0.0f, 0.0f, 0.0f), C.FlagMove);
            Require(!C.TryCalculateParent(parent, new[] { degenerate }, out _),
                "zero authored rest vector must fail closed");
        }

        private static C.ParentSource IdentityParent()
        {
            return new C.ParentSource(
                D(0.0, 0.0, 0.0),
                Q(0.0f, 0.0f, 0.0f, 1.0f),
                F(1.0f, 1.0f, 1.0f),
                Q(1.0f, 1.0f, 1.0f, 1.0f),
                C.FlagMove,
                1.0,
                1.0);
        }

        private static C.ChildSource Child(K.Double3 position, K.Float3 local, byte attribute)
        {
            return new C.ChildSource(
                position,
                local,
                Q(0.0f, 0.0f, 0.0f, 1.0f),
                attribute);
        }

        private static K.Double3 D(double x, double y, double z) => new K.Double3(x, y, z);
        private static K.Float3 F(float x, float y, float z) => new K.Float3(x, y, z);
        private static K.Float4 Q(float x, float y, float z, float w) => new K.Float4(x, y, z, w);
        private static K.Float3 FB(uint x, uint y, uint z) =>
            new K.Float3(Single(x), Single(y), Single(z));
        private static K.Float4 QB(uint x, uint y, uint z, uint w) =>
            new K.Float4(Single(x), Single(y), Single(z), Single(w));
        private static float Single(uint bits) =>
            BitConverter.Int32BitsToSingle(unchecked((int)bits));

        private static void RequireDouble3(K.Double3 actual, K.Double3 expected, string label)
        {
            Require(BitConverter.DoubleToInt64Bits(actual.x) == BitConverter.DoubleToInt64Bits(expected.x) &&
                    BitConverter.DoubleToInt64Bits(actual.y) == BitConverter.DoubleToInt64Bits(expected.y) &&
                    BitConverter.DoubleToInt64Bits(actual.z) == BitConverter.DoubleToInt64Bits(expected.z),
                label + " expected (" + expected.x + "," + expected.y + "," + expected.z +
                ") but got (" + actual.x + "," + actual.y + "," + actual.z + ")");
        }

        private static void RequireQuaternionBits(
            K.Float4 actual,
            uint x,
            uint y,
            uint z,
            uint w,
            string label)
        {
            RequireFloatBits(actual.x, x, label + " x");
            RequireFloatBits(actual.y, y, label + " y");
            RequireFloatBits(actual.z, z, label + " z");
            RequireFloatBits(actual.w, w, label + " w");
        }

        private static void RequireFloat3Bits(
            K.Float3 actual,
            uint x,
            uint y,
            uint z,
            string label)
        {
            RequireFloatBits(actual.x, x, label + " x");
            RequireFloatBits(actual.y, y, label + " y");
            RequireFloatBits(actual.z, z, label + " z");
        }

        private static void RequireFloatBits(float actual, uint expected, string label)
        {
            uint actualBits = unchecked((uint)BitConverter.SingleToInt32Bits(actual));
            Require(
                actualBits == expected,
                label + " expected 0x" + expected.ToString("x8") +
                " but got 0x" + actualBits.ToString("x8"));
        }

        private static void Require(bool condition, string message)
        {
            if (!condition)
                throw new InvalidOperationException(message);
        }
    }
}
