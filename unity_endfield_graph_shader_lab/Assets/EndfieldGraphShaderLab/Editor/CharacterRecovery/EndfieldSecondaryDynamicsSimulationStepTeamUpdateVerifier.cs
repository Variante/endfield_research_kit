using System;
using UnityEditor;
using UnityEngine;
using Helper = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsSimulationStepTeamUpdate;
using K = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels;

namespace EndfieldGraphShaderLabEditor
{
    public static class EndfieldSecondaryDynamicsSimulationStepTeamUpdateVerifier
    {
        private const float Dt = 0.011111111380159855f;

        [MenuItem("Endfield/Character Recovery Lab/Verify Secondary Dynamics Simulation Step Team Update")]
        public static void VerifyMenu()
        {
            Verify();
            Debug.Log("Verified direct native Hair/Coat SimulationStepTeamUpdate vectors bit-exact and fail-closed unsupported branches.");
        }

        public static void Verify()
        {
            VerifyHair();
            VerifyCoat();
            VerifyInterpolationAndStateAdvance();
            VerifyFailClosed();
        }

        private static void VerifyHair()
        {
            Helper.CenterState state = InitialState();
            Helper.Execute(ref state, Frame(0.015625, -0.0078125, 0.00390625, 22.5f),
                Parameters(1f, -1f, -1f), Dt);
            VerifyCommon(state,
                0x00000000U, 0x00000000U,
                "0000803c000000bc0000803b", "0000000000000000c3c5473ebf147b3f",
                "000000000000000000000000", "000000000000000000000000fdff7f3f",
                0x420d5f1fU, "00000000000000000700803f",
                "000000000000903f00000000000080bf000000000000703f",
                "0000000000000000c3c5473ebf147b3f");
        }

        private static void VerifyCoat()
        {
            Helper.CenterState state = InitialState();
            Helper.Execute(ref state, Frame(0.03125, 0.015625, -0.0078125, 45f),
                Parameters(0.8f, 5f, 720f), Dt);
            VerifyCommon(state,
                0x3e4cccccU, 0x3f527d26U,
                "0000003d0000803c000000bc", "000000000000000017efc33e60836c3f",
                "cccccc3bcccc4c3bccccccba", "0000000000000000c275a23e58c5723f",
                0x428d5f20U, "00000000000000000600803f",
                "000000000000a03f000000000000903f00000000000080bf",
                "000000000000000017efc33e60836c3f");
        }

        private static void VerifyCommon(Helper.CenterState state,
            uint moveRatio, uint rotationRatio, string stepVector, string stepRotation,
            string inertiaVector, string inertiaRotation, uint angularVelocity, string rotationAxis,
            string nowPosition, string nowRotation)
        {
            RequireBits(state.FrameInterpolation, 0x3f800000U, "frame interpolation");
            RequireBits(state.StepMoveInertiaRatio, moveRatio, "move ratio");
            RequireBits(state.StepRotationInertiaRatio, rotationRatio, "rotation ratio");
            RequireHex(state.StepVector, stepVector, "step vector");
            RequireHex(state.StepRotation, stepRotation, "step rotation");
            RequireHex(state.InertiaVector, inertiaVector, "inertia vector");
            RequireHex(state.InertiaRotation, inertiaRotation, "inertia rotation");
            RequireBits(state.AngularVelocity, angularVelocity, "angular velocity");
            RequireHex(state.RotationAxis, rotationAxis, "rotation axis");
            RequireHex(state.NowWorldPosition, nowPosition, "now position");
            RequireHex(state.NowWorldRotation, nowRotation, "now rotation");
            RequireHex(state.OldWorldPosition, "000000000000000000000000000000000000000000000000", "old position");
            RequireHex(state.OldWorldRotation, "0000000000000000000000000000803f", "old rotation");
            RequireBits(state.StepMovingSpeed, 0x40e80000U, "preserved moving speed");
            RequireHex(state.StepMovingDirection, "0000803e000000bf0000403f", "preserved moving direction");
            RequireHex(state.InitLocalGravityDirection, "000000be0000c03e000020bf", "preserved gravity direction");
        }

        private static void VerifyInterpolationAndStateAdvance()
        {
            Helper.CenterState state = InitialState();
            state.NowUpdateTime = 0.5f;
            Helper.FrameInput frame = Frame(1.0, 2.0, 3.0, 22.5f);
            frame.Time = 1f;
            frame.FrameOldTime = 0f;
            frame.OldFrameWorldPosition = new K.Double3(0.0, 0.0, 0.0);
            Helper.Execute(ref state, frame, Parameters(1f, -1f, -1f), Dt);
            Require(state.FrameInterpolation > 0.5f && state.FrameInterpolation < 1f, "bounded interpolation branch");
            K.Double3 priorNow = state.NowWorldPosition;
            K.Float4 priorRotation = state.NowWorldRotation;
            Helper.Execute(ref state, frame, Parameters(1f, -1f, -1f), Dt);
            RequireHex(state.OldWorldPosition, Hex(priorNow), "second-step old position advancement");
            RequireHex(state.OldWorldRotation, Hex(priorRotation), "second-step old rotation advancement");
        }

        private static void VerifyFailClosed()
        {
            Helper.CenterState baseline = InitialState();
            ExpectRejected(baseline, Mutate(Frame(0, 0, 0, 0), (ref Helper.FrameInput f) => f.WindZoneCount = 1),
                Parameters(1f, -1f, -1f), Dt, Helper.ExecutionRoute.Unpatched, typeof(NotSupportedException));
            ExpectRejected(baseline, Mutate(Frame(0, 0, 0, 0), (ref Helper.FrameInput f) => f.NegativeScale = true),
                Parameters(1f, -1f, -1f), Dt, Helper.ExecutionRoute.Unpatched, typeof(NotSupportedException));
            ExpectRejected(baseline, Frame(0, 0, 0, 0), Parameters(1f, -1f, -1f), Dt,
                Helper.ExecutionRoute.IFixPatched, typeof(NotSupportedException));
            ExpectRejected(baseline, Frame(0, 0, 0, 0), Parameters(1f, -1f, -1f), 1f / 60f,
                Helper.ExecutionRoute.Unpatched, typeof(NotSupportedException));
            Helper.FrameInput malformed = Frame(0, 0, 0, 0);
            malformed.FrameWorldPosition = new K.Double3(double.NaN, 0, 0);
            ExpectRejected(baseline, malformed, Parameters(1f, -1f, -1f), Dt,
                Helper.ExecutionRoute.Unpatched, typeof(ArgumentOutOfRangeException));
        }

        private static void ExpectRejected(Helper.CenterState baseline, Helper.FrameInput frame,
            Helper.Parameters parameters, float dt, Helper.ExecutionRoute route, Type exceptionType)
        {
            Helper.CenterState state = baseline;
            bool rejected = false;
            try { Helper.Execute(ref state, frame, parameters, dt, route); }
            catch (Exception exception) when (exception.GetType() == exceptionType) { rejected = true; }
            Require(rejected, "expected " + exceptionType.Name);
            RequireHex(state.NowWorldPosition, Hex(baseline.NowWorldPosition), "transactional rejection position");
            RequireBits(state.NowUpdateTime, Bits(baseline.NowUpdateTime), "transactional rejection clock");
        }

        private static Helper.CenterState InitialState()
        {
            return new Helper.CenterState
            {
                NowUpdateTime = 1f - Dt,
                FrameInterpolation = 1f,
                NowWorldPosition = new K.Double3(0, 0, 0),
                OldWorldPosition = new K.Double3(0, 0, 0),
                NowWorldRotation = Q(0, 0, 0, 1),
                OldWorldRotation = Q(0, 0, 0, 1),
                StepRotation = Q(0, 0, 0, 1),
                InertiaRotation = Q(0, 0, 0, 1),
                StepMovingSpeed = 7.25f,
                StepMovingDirection = new K.Float3(0.25f, -0.5f, 0.75f),
                InitLocalGravityDirection = new K.Float3(-0.125f, 0.375f, -0.625f),
            };
        }

        private static Helper.FrameInput Frame(double x, double y, double z, float degrees)
        {
            double halfRadians = degrees * Math.PI / 360.0;
            K.Float4 rotation = degrees == 22.5f
                ? Q(0, 0, FromBits(0x3e47c5c3U), FromBits(0x3f7b14bfU))
                : degrees == 45f
                    ? Q(0, 0, FromBits(0x3ec3ef17U), FromBits(0x3f6c8360U))
                    : Q(0, 0, (float)Math.Sin(halfRadians), (float)Math.Cos(halfRadians));
            return new Helper.FrameInput
            {
                Time = 1f,
                FrameOldTime = 1f - Dt,
                OldFrameWorldPosition = new K.Double3(0, 0, 0),
                FrameWorldPosition = new K.Double3(x, y, z),
                OldFrameWorldRotation = Q(0, 0, 0, 1),
                FrameWorldRotation = rotation,
                FrameScale = new K.Float3(1, 1, 1),
                WindZoneCount = 0,
                NegativeScale = false,
                StationaryActorRoot = true,
            };
        }

        private static Helper.FrameInput Mutate(Helper.FrameInput value, ActionRef<Helper.FrameInput> mutate)
        {
            mutate(ref value);
            return value;
        }

        private delegate void ActionRef<T>(ref T value);
        private static Helper.Parameters Parameters(float inertia, float movementLimit, float rotationLimit) =>
            new Helper.Parameters
            {
                LocalInertia = inertia,
                LocalMovementSpeedLimit = movementLimit,
                LocalRotationSpeedLimit = rotationLimit,
            };
        private static K.Float4 Q(float x, float y, float z, float w) => new K.Float4(x, y, z, w);

        private static void Require(bool condition, string message)
        {
            if (!condition) throw new InvalidOperationException("SimulationStepTeamUpdate verification failed: " + message);
        }

        private static void RequireBits(float value, uint expected, string label)
        {
            uint actual = Bits(value);
            if (actual != expected) throw new InvalidOperationException(string.Format(
                "SimulationStepTeamUpdate verification failed: {0}: {1:x8} != {2:x8}", label, actual, expected));
        }

        private static void RequireHex(K.Float3 value, string expected, string label) => RequireHex(Hex(value), expected, label);
        private static void RequireHex(K.Float4 value, string expected, string label) => RequireHex(Hex(value), expected, label);
        private static void RequireHex(K.Double3 value, string expected, string label) => RequireHex(Hex(value), expected, label);
        private static void RequireHex(string actual, string expected, string label)
        {
            if (!string.Equals(actual, expected, StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("SimulationStepTeamUpdate verification failed: " + label + ": " + actual + " != " + expected);
        }

        private static string Hex(K.Float3 value) => Hex(new[] { value.x, value.y, value.z });
        private static string Hex(K.Float4 value) => Hex(new[] { value.x, value.y, value.z, value.w });
        private static string Hex(K.Double3 value) => Hex(new[] { value.x, value.y, value.z });
        private static string Hex(float[] values) => BitConverter.ToString(Bytes(values)).Replace("-", "").ToLowerInvariant();
        private static string Hex(double[] values) => BitConverter.ToString(Bytes(values)).Replace("-", "").ToLowerInvariant();
        private static byte[] Bytes(float[] values) { byte[] bytes = new byte[values.Length * 4]; Buffer.BlockCopy(values, 0, bytes, 0, bytes.Length); return bytes; }
        private static byte[] Bytes(double[] values) { byte[] bytes = new byte[values.Length * 8]; Buffer.BlockCopy(values, 0, bytes, 0, bytes.Length); return bytes; }
        private static uint Bits(float value) => BitConverter.ToUInt32(BitConverter.GetBytes(value), 0);
        private static float FromBits(uint value) => BitConverter.ToSingle(BitConverter.GetBytes(value), 0);
    }
}
