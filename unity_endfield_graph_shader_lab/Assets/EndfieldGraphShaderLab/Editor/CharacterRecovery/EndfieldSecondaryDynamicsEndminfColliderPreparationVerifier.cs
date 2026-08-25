using System;
using UnityEditor;
using UnityEngine;
using Data = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsData;
using Helper = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsEndminfColliderPreparation;
using K = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels;

namespace EndfieldGraphShaderLabEditor
{
    public static class EndfieldSecondaryDynamicsEndminfColliderPreparationVerifier
    {
        [MenuItem("Endfield/Character Recovery Lab/Verify Endminf Collider Preparation")]
        public static void VerifyMenu()
        {
            Verify();
            Debug.Log("Verified all 10 source-ordered Endminf collider inputs, reset transition, frame publication, and Collider Start outputs.");
        }

        public static void Verify()
        {
            Data.CapsuleCollider[] rows = AuthoredRows();
            Helper.TransformSample[] previous = Samples(10, D3(10.0, 20.0, 30.0), Q(0f, 0f, 0f, 1f), F3(2f, 3f, 4f));
            Helper.TransformSample[] current = Samples(10, D3(11.0, 22.0, 33.0), Q(0f, 0f, 0f, 1f), F3(2f, 3f, 4f));
            Helper.PreparedCollider[] prepared = Helper.RegisterAndPrepareAll(
                rows, previous, current, false, 0.25f, 0.5f, 0.75f);

            Require(prepared.Length == 10, "authored output count");
            for (int index = 0; index < prepared.Length; index++)
            {
                Helper.PreparedCollider row = prepared[index];
                byte expected = index == 4 ? (byte)0x34 : (byte)0x32;
                byte expectedRegistration = index == 4 ? (byte)0x74 : (byte)0x72;
                Require(row.SourceIndex == index, "source order " + index);
                Require(row.RegistrationFlag == expectedRegistration, "registration flag " + index);
                Require(row.ColliderStartFlag == expected, "start flag " + index);
                Require((row.ColliderStartFlag & Helper.Reset) == 0, "reset consumed " + index);
                RequireFinite(row.State.workData, "work " + index);
                RequireBits(row.State.workData.rotation, current[index].Rotation, "work rotation " + index);
            }

            RequireFloatBits(prepared[0].Size.x, 0x3ddf3b64U, "row0 radius0");
            RequireFloatBits(prepared[0].Size.y, 0x3deb851fU, "row0 separated radius1");
            RequireFloatBits(prepared[1].Size.x, 0x3d9db22dU, "row1 radius0");
            RequireFloatBits(prepared[1].Size.y, 0x3d9db22dU, "row1 rewritten radius1");
            RequireFloatBits(prepared[4].Size.x, 0x3dd70a3dU, "row4 radius0");
            RequireFloatBits(prepared[4].Size.y, 0x3dd70a3dU, "row4 rewritten radius1");
            RequireFloatBits(prepared[0].State.workData.radius0, Bits(.109f * 2f), "row0 work radius0");
            RequireFloatBits(prepared[0].State.workData.radius1, Bits(.115f * 2f), "row0 work radius1");
            RequireBits(prepared[0].State.workData.old0, prepared[0].State.workData.next0, "row0 reset endpoint0");
            RequireBits(prepared[0].State.workData.old1, prepared[0].State.workData.next1, "row0 reset endpoint1");

            // Identity rotation: base position plus center*scale, retained as double.
            RequireDouble(prepared[0].FramePosition.x, 11.0 + (double)(-0.07f * 2f), "row0 center x");
            RequireDouble(prepared[0].FramePosition.y, 22.0, "row0 center y");
            RequireDouble(prepared[0].FramePosition.z, 33.0 + (double)(-0.11f * 4f), "row0 center z");
            RequireDouble(prepared[4].FramePosition.x, 11.0, "row4 zero center x");
            RequireDouble(prepared[4].FramePosition.y, 22.0, "row4 zero center y");
            RequireDouble(prepared[4].FramePosition.z, 33.0, "row4 zero center z");

            VerifyRotatedCenterAndResetLifecycle(rows[0]);
            VerifyRejectedBoundaries(rows);
        }

        private static void VerifyRotatedCenterAndResetLifecycle(Data.CapsuleCollider source)
        {
            Helper.TransformSample initial = S(D3(1.0, 2.0, 3.0), Q(0f, 0f, 0f, 1f), F3(1f, 1f, 1f));
            Helper.RegisteredCollider state = Helper.Register(0, source, initial);
            Require(state.RegistrationFlag == 0x72 && state.Flag == 0x72, "registration reset flag");

            float halfSqrt = 0.70710677f;
            Helper.TransformSample rotated = S(
                D3(4.0, 5.0, 6.0), Q(0f, 0f, halfSqrt, halfSqrt), F3(2f, 1f, 1f));
            Helper.PreparedCollider first = Helper.PrepareAndStart(ref state, rotated, false, 0.5f, 0.5f, 0.5f);
            Require(first.ColliderStartFlag == 0x32, "first reset clear");
            // A 90-degree Z rotation maps scaled (-0.14,0,-0.11) to (0,-0.14,-0.11).
            RequireDouble(first.FramePosition.x, 4.0, "rotated center x");
            RequireDouble(first.FramePosition.y, 5.0 + (double)(-0.14f), "rotated center y");
            RequireDouble(first.FramePosition.z, 6.0 + (double)(-0.11f), "rotated center z");
            RequireBits(first.State.nowPosition, ToF3(first.FramePosition), "reset now position");
            RequireBits(first.State.oldPosition, ToF3(first.FramePosition), "reset old position");
            RequireBits(first.ColliderStartOldFrameRotation, rotated.Rotation, "reset old frame rotation");

            Helper.TransformSample next = S(D3(8.0, 9.0, 10.0), Q(0f, 0f, 0f, 1f), F3(1f, 1f, 1f));
            K.Double3 previousPublished = first.FramePosition;
            Helper.PreparedCollider second = Helper.PrepareAndStart(ref state, next, false, 0f, 1f, 1f);
            Require(second.ColliderStartFlag == 0x32, "ordinary flag stays clear");
            RequireBits(second.State.nowPosition, ToF3(previousPublished), "ordinary interpolation uses prior frame");

            Helper.PreparedCollider reset = Helper.PrepareAndStart(ref state, next, true, 0f, 0f, 0f);
            RequireBits(reset.State.nowPosition, ToF3(reset.FramePosition), "team reset current position");
            Require((reset.ColliderStartFlag & Helper.Reset) == 0, "team reset does not republish reset bit");
        }

        private static void VerifyRejectedBoundaries(Data.CapsuleCollider[] rows)
        {
            Helper.TransformSample identity = S(D3(0, 0, 0), Q(0, 0, 0, 1), F3(1, 1, 1));
            Data.CapsuleCollider type7 = rows[4];
            type7.alignedOnCenter = false;
            Expect<NotSupportedException>(() => Helper.Register(4, type7, identity), "type7");

            Data.CapsuleCollider generalY = rows[0];
            generalY.direction = 1;
            Expect<NotSupportedException>(() => Helper.Register(0, generalY, identity), "general Y");

            Data.CapsuleCollider reverse = rows[0];
            reverse.reverseDirection = true;
            Expect<NotSupportedException>(() => Helper.Register(0, reverse, identity), "reverse");

            Helper.TransformSample[] ten = Samples(10, D3(0, 0, 0), Q(0, 0, 0, 1), F3(1, 1, 1));
            Expect<ArgumentException>(() => Helper.RegisterAndPrepareAll(
                new Data.CapsuleCollider[9], ten, ten, false, 1f, 1f, 1f), "wrong count");
        }

        private static Data.CapsuleCollider[] AuthoredRows()
        {
            return new[]
            {
                C(-.07f, 0f, -.11f, .109f, .115f, .399f, 0, true),
                C(-.21f, 0f, 0f, .077f, .001f, .489f, 0, false),
                C(-.02f, 0f, -.08f, .054f, .069f, .237f, 0, true),
                C(-.09f, 0f, -.075f, .071f, .001f, .32f, 0, false),
                C(0f, 0f, 0f, .105f, .106f, .297f, 2, false),
                C(-.21f, 0f, 0f, .077f, .001f, .489f, 0, false),
                C(-.07f, 0f, -.11f, .114f, .129f, .399f, 0, true),
                C(-.02f, 0f, -.08f, .054f, .069f, .237f, 0, true),
                C(0f, 0f, 0f, .101f, .092f, .291f, 0, true),
                C(-.09f, 0f, -.075f, .071f, .001f, .32f, 0, false),
            };
        }

        private static Data.CapsuleCollider C(float cx, float cy, float cz,
            float sx, float sy, float sz, int direction, bool separated)
        {
            return new Data.CapsuleCollider
            {
                center = new Vector3(cx, cy, cz), size = new Vector3(sx, sy, sz),
                direction = direction, radiusSeparation = separated, alignedOnCenter = true,
            };
        }

        private static Helper.TransformSample[] Samples(int count, K.Double3 p, K.Float4 q, K.Float3 s)
        {
            var result = new Helper.TransformSample[count];
            for (int index = 0; index < count; index++) result[index] = S(p, q, s);
            return result;
        }

        private static Helper.TransformSample S(K.Double3 p, K.Float4 q, K.Float3 s) =>
            new Helper.TransformSample(p, q, s);
        private static K.Double3 D3(double x, double y, double z) => new K.Double3(x, y, z);
        private static K.Float3 F3(float x, float y, float z) => new K.Float3(x, y, z);
        private static K.Float4 Q(float x, float y, float z, float w) => new K.Float4(x, y, z, w);
        private static K.Float3 ToF3(K.Double3 value) => new K.Float3((float)value.x, (float)value.y, (float)value.z);

        private static void RequireFinite(K.ColliderStartWorkData value, string label)
        {
            Require(Finite(value.aabbMin.x) && Finite(value.aabbMin.y) && Finite(value.aabbMin.z), label + " min");
            Require(Finite(value.aabbMax.x) && Finite(value.aabbMax.y) && Finite(value.aabbMax.z), label + " max");
            Require(Finite(value.radius0) && Finite(value.radius1), label + " radii");
        }

        private static bool Finite(float value) => !float.IsNaN(value) && !float.IsInfinity(value);
        private static bool Finite(double value) => !double.IsNaN(value) && !double.IsInfinity(value);
        private static uint Bits(float value) => BitConverter.ToUInt32(BitConverter.GetBytes(value), 0);
        private static void RequireBits(K.Float3 actual, K.Float3 expected, string label)
        {
            RequireFloatBits(actual.x, Bits(expected.x), label + ".x");
            RequireFloatBits(actual.y, Bits(expected.y), label + ".y");
            RequireFloatBits(actual.z, Bits(expected.z), label + ".z");
        }

        private static void RequireBits(K.Float4 actual, K.Float4 expected, string label)
        {
            RequireFloatBits(actual.x, Bits(expected.x), label + ".x");
            RequireFloatBits(actual.y, Bits(expected.y), label + ".y");
            RequireFloatBits(actual.z, Bits(expected.z), label + ".z");
            RequireFloatBits(actual.w, Bits(expected.w), label + ".w");
        }

        private static void RequireBits(K.Double3 actual, K.Double3 expected, string label)
        {
            RequireDouble(actual.x, expected.x, label + ".x");
            RequireDouble(actual.y, expected.y, label + ".y");
            RequireDouble(actual.z, expected.z, label + ".z");
        }

        private static void RequireFloatBits(float actual, uint expected, string label)
        {
            if (Bits(actual) != expected)
                throw new InvalidOperationException(label + ": float bits differ.");
        }

        private static void RequireDouble(double actual, double expected, string label)
        {
            if (BitConverter.DoubleToInt64Bits(actual) != BitConverter.DoubleToInt64Bits(expected))
                throw new InvalidOperationException(label + ": double bits differ.");
        }

        private static void Require(bool condition, string label)
        {
            if (!condition) throw new InvalidOperationException("Endminf collider preparation verification failed: " + label);
        }

        private static void Expect<T>(Action action, string label) where T : Exception
        {
            try { action(); }
            catch (T) { return; }
            throw new InvalidOperationException("Expected " + typeof(T).Name + " for " + label + ".");
        }
    }
}
