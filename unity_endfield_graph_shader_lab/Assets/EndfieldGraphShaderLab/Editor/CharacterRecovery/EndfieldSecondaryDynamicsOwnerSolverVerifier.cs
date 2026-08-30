using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using CD = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsCalcDisplayPosition;
using K = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels;
using Solver = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsOwnerSolver;
using T = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsTimeStepper;

namespace EndfieldGraphShaderLabEditor
{
    public static class EndfieldSecondaryDynamicsOwnerSolverVerifier
    {
        private sealed class Trace : Solver.IStageObserver
        {
            public readonly List<string> Rows = new List<string>();
            public void OnStage(Solver.Stage stage, int substepIndex, int sourceIndex) =>
                Rows.Add(substepIndex + ":" + stage + ":" + sourceIndex);
        }

        [MenuItem("Endfield/Character Recovery Lab/Verify Inert Endminf Owner Solver")]
        public static void VerifyMenu()
        {
            Verify();
            Debug.Log(
                "Verified inert pure-managed Endminf owner solver: source-derived Reset initialization, " +
                "retail 1/2-step cadence surface, ordered two-pass Distance, and Hair no-collider path.");
        }

        public static void Verify()
        {
            VerifyResetSeedingAndConsumption();

            Trace trace = new Trace();
            Solver.BaseTransformFrame pose = Pose();
            var team = new T.TeamState { TimeScale = 1f, FrameInterpolation = 1f };
            var solver = new Solver(
                HairOwner(),
                pose,
                team,
                trace);

            Require(solver.PublicationPositions.Length == 3, "proxy allocation count");
            RequireBits((float)solver.PublicationPositions[2].y, Bits(2f), "explicit initialization position");
            RequireBits(solver.PublicationRotations[1].w, Bits(1f), "explicit initialization rotation");
            RequireBits(solver.Velocities[1].x, 0U, "zero velocity initialization");
            pose.CurrentPositions[2] = D3(99, 99, 99);
            RequireBits((float)solver.PublicationPositions[2].y, Bits(2f),
                "initial state does not alias caller arrays");
            pose = Pose();

            int first = solver.AdvanceFrame(FrameClock(), pose, Steps(1));
            Require(first == 1, "first 60 fps frame has one 90 Hz step");
            RequireTrace(trace.Rows, 0, 1);

            trace.Rows.Clear();
            int second = solver.AdvanceFrame(FrameClock(), pose, Steps(2));
            Require(second == 2, "second 60 fps frame has two 90 Hz steps");
            RequireTrace(trace.Rows, 0, 2);

            K.Double3 before = solver.PublicationPositions[1];
            Expect<ArgumentException>(() => solver.AdvanceFrame(FrameClock(), pose, Steps(0)));
            RequireBits((float)solver.PublicationPositions[1].x, Bits((float)before.x),
                "failed frame does not commit proxy state");
            Expect<NotSupportedException>(() =>
                solver.AdvanceFrame(FrameClock(), pose, Steps(1), new Solver.PreparedCapsuleFrame()));

            // Ribbon/Coat source baselines omit their immediate movable anchor from
            // baseLineData. The managed slice must still expose that global parent to
            // the angle kernel and commit any parent correction back to owner state.
            EndfieldGraphShaderLab.EndfieldSecondaryDynamicsData.Owner anchored = HairOwner();
            anchored.baseLineDataCounts = new ushort[] { 2 };
            anchored.baseLineData = new ushort[] { 1, 2 };
            var anchoredSolver = new Solver(anchored, Pose(),
                new T.TeamState { TimeScale = 1f, FrameInterpolation = 1f });
            Require(anchoredSolver.AdvanceFrame(FrameClock(), Pose(), Steps(1)) == 1,
                "external baseline anchor closure");
        }

        private static void VerifyResetSeedingAndConsumption()
        {
            Solver.BaseTransformFrame pose = ResetPose();
            var solver = new Solver(
                HairOwner(),
                pose,
                new T.TeamState
                {
                    Flag = T.FlagValid | CD.FlagProcess | T.FlagReset |
                        T.FlagTimeReset | CD.FlagRunning,
                    TimeScale = 1f,
                    FrameInterpolation = 1f,
                });

            RequireBits((float)solver.SimulationPositions[1].x, 0U,
                "RegisterProxyMesh allocation remains default before Reset is consumed");

            int steps = solver.AdvanceFrame(
                new T.TeamFrameInput(true, false, false, false,
                    1f / 120f, 1f / 120f, 1f / 120f),
                pose,
                Steps(0));
            Require(steps == 0, "Reset is consumed on a zero-substep ClothUpdate");

            for (int index = 0; index < pose.CurrentPositions.Length; index++)
            {
                RequireDouble3Bits(solver.SimulationPositions[index], pose.CurrentPositions[index],
                    "Reset seeds collapsed nextPos/oldPos from current positions");
                RequireDouble3Bits(solver.BasePositions[index], pose.CurrentPositions[index],
                    "Reset seeds basePos from current positions");
                RequireDouble3Bits(solver.DisplayOldPositions[index], pose.CurrentPositions[index],
                    "Reset seeds oldPosition from current positions");
                RequireDouble3Bits(solver.VelocityPositions[index], pose.CurrentPositions[index],
                    "Reset seeds velocityPos from current positions");
                RequireDouble3Bits(solver.DisplayPositions[index], pose.CurrentPositions[index],
                    "Reset seeds dispPos from current positions");
                RequireFloat4Bits(solver.SimulationRotations[index], pose.CurrentRotations[index],
                    "Reset seeds oldRot from current rotations");
                RequireFloat4Bits(solver.BaseRotations[index], pose.CurrentRotations[index],
                    "Reset seeds baseRot from current rotations");
                RequireFloat4Bits(solver.DisplayOldRotations[index], pose.CurrentRotations[index],
                    "Reset seeds oldRotation from current rotations");
                RequireFloat3Zero(solver.Velocities[index], "Reset clears velocity");
                RequireFloat3Zero(solver.RealVelocities[index], "Reset clears realVelocity");
                RequireBits(solver.Frictions[index], 0U, "Reset clears friction");
                RequireBits(solver.StaticFrictions[index], 0U, "Reset clears staticFriction");
                RequireFloat3Zero(solver.CollisionNormals[index], "Reset clears collisionNormal");
            }

            Require((solver.TeamState.Flag & (T.FlagReset | T.FlagTimeReset)) == 0UL,
                "PostTeam consumes Reset and TimeReset after publication");
            Require(solver.TeamState.Flag == (T.FlagValid | CD.FlagProcess | CD.FlagRunning),
                "PostTeam preserves non-transient lifecycle flags");
        }

        private static void RequireTrace(List<string> rows, int firstSubstep, int count)
        {
            string[] stages =
            {
                "Start:-1", "BasicPosture:-1", "Tether:-1", "DistancePass1:-1",
                "AngleBaseline:0", "DistancePass2:-1", "End:-1",
                "ColliderSnapshotBoundary:-1",
            };
            Require(rows.Count == stages.Length * count + 1, "stage trace count");
            int cursor = 0;
            for (int step = firstSubstep; step < firstSubstep + count; step++)
                for (int stage = 0; stage < stages.Length; stage++)
                    Require(rows[cursor++] == step + ":" + stages[stage],
                        "recovered stage order at substep " + step + ", stage " + stage);
            Require(
                rows[cursor] == "-1:CalcDisplayPosition:-1",
                "CalcDisplayPosition must follow the final Simulation End/collider boundary.");
            Require(!rows.Exists(row => row.Contains("PointCollision")),
                "Hair follows the authored no-collider path");
            int distance1 = rows.FindIndex(row => row.Contains("DistancePass1"));
            int angle = rows.FindIndex(row => row.Contains("AngleBaseline"));
            int distance2 = rows.FindIndex(row => row.Contains("DistancePass2"));
            Require(distance1 < angle && angle < distance2, "ordered two-pass Distance surface");
        }

        private static Solver.CenterTeamStepInput[] Steps(int count)
        {
            var result = new Solver.CenterTeamStepInput[count];
            for (int index = 0; index < count; index++)
            {
                result[index] = new Solver.CenterTeamStepInput(
                    1f,
                    1f,
                    1f,
                    0,
                    0,
                    F3(0f, 0f, 0f),
                    D3(0.0, 0.0, 0.0),
                    F3(0f, 0f, 0f),
                    Q(),
                    F3(0f, 0f, 0f),
                    Q(),
                    D3(0.0, 0.0, 0.0),
                    0f,
                    F3(0f, 1f, 0f),
                    1f,
                    true,
                    false,
                    F3(1f, 1f, 1f),
                    F3(1f, 1f, 1f),
                    Q(),
                    null);
            }
            return result;
        }

        private static T.TeamFrameInput FrameClock() =>
            new T.TeamFrameInput(true, false, false, false,
                1f / 60f, 1f / 60f, 1f / 60f);

        private static Solver.BaseTransformFrame Pose()
        {
            K.Double3[] positions = { D3(0, 0, 0), D3(0, 1, 0), D3(0, 2, 0) };
            K.Float4[] rotations = { Q(), Q(), Q() };
            return new Solver.BaseTransformFrame
            {
                CurrentPositions = (K.Double3[])positions.Clone(),
                CurrentRotations = (K.Float4[])rotations.Clone(),
                PreviousPositions = (K.Double3[])positions.Clone(),
                PreviousRotations = (K.Float4[])rotations.Clone(),
            };
        }

        private static Solver.BaseTransformFrame ResetPose()
        {
            K.Double3[] current = { D3(10, 20, 30), D3(11, 21, 31), D3(12, 22, 32) };
            K.Double3[] previous = { D3(-10, -20, -30), D3(-11, -21, -31), D3(-12, -22, -32) };
            K.Float4[] currentRotations =
            {
                Q(),
                new K.Float4(0f, 0f, 0.5f, 0.8660254f),
                new K.Float4(0.5f, 0f, 0f, 0.8660254f),
            };
            K.Float4[] previousRotations = { Q(), Q(), Q() };
            return new Solver.BaseTransformFrame
            {
                CurrentPositions = current,
                CurrentRotations = currentRotations,
                PreviousPositions = previous,
                PreviousRotations = previousRotations,
            };
        }

        private static EndfieldGraphShaderLab.EndfieldSecondaryDynamicsData.Owner HairOwner()
        {
            float[] ones = new float[16];
            for (int index = 0; index < ones.Length; index++)
                ones[index] = 1f;
            return new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsData.Owner
            {
                ownerPath = "MC_Hair",
                proxyTransformPaths = new[] { "Hair0", "Hair1", "Hair2" },
                proxyVertexCount = 3,
                baselineCount = 1,
                colliderCount = 0,
                referenceIndices = new[] { 0, 1, 2 },
                attributes = new byte[] { 0, 2, 2 },
                vertexDepths = new[] { 0f, 0.5f, 1f },
                vertexRootIndices = new[] { -1, 0, 0 },
                vertexParentIndices = new[] { -1, 0, 1 },
                vertexLocalPositions = new[] { Vector3.zero, Vector3.up, Vector3.up },
                vertexLocalRotations = new[] { Quaternion.identity, Quaternion.identity, Quaternion.identity },
                vertexBindPoseRotations = new[] { Quaternion.identity, Quaternion.identity, Quaternion.identity },
                vertexToTransformRotations = new[] { Quaternion.identity, Quaternion.identity, Quaternion.identity },
                baseLineFlags = new byte[] { 1 },
                baseLineStartDataIndices = new ushort[] { 0 },
                baseLineDataCounts = new ushort[] { 3 },
                baseLineData = new ushort[] { 0, 1, 2 },
                centerFixedList = Array.Empty<ushort>(),
                distanceConstraintIndexArray = new[] { 0x00100000, 0x00100001, 0x00100002 },
                distanceConstraintDataArray = new ushort[] { 1, 0, 1 },
                distanceConstraintRestLengths = new[] { 1f, 1f, 1f },
                colliderIndices = Array.Empty<int>(),
                solverInputs = new EndfieldGraphShaderLab.EndfieldSecondaryDynamicsData.SolverInputs
                {
                    authoredScalarsRecovered = true,
                    compiledCurveSamplesRecovered = true,
                    dampingCurveData = (float[])ones.Clone(),
                    radiusCurveData = (float[])ones.Clone(),
                    distanceRestorationStiffness = (float[])ones.Clone(),
                    angleRestorationStiffness = (float[])ones.Clone(),
                    angleLimit = (float[])ones.Clone(),
                    normalAxis = 1,
                    gravity = 0f,
                    gravityDirection = Vector3.down,
                    animationPoseRatio = 1f,
                    inertiaDepth = 0f,
                    tetherDistanceCompression = 0.1f,
                    tetherStretchLimit = BitConverter.Int32BitsToSingle(unchecked((int)0x3cf5c28f)),
                    distanceVelocityAttenuation = BitConverter.Int32BitsToSingle(unchecked((int)0x3e99999a)),
                    angleRestorationEnabled = true,
                    angleRestorationVelocityAttenuation = 0f,
                    angleRestorationGravityFalloff = 0f,
                    angleLimitEnabled = false,
                    particleSpeedLimitEnabled = false,
                    colliderDynamicFriction = 0f,
                    colliderStaticFriction = 0f,
                    springPower = 0f,
                    springLimitDistance = 1f,
                    springNormalLimitRatio = 1f,
                    springNoise = 0f,
                },
            };
        }

        private static K.Double3 D3(double x, double y, double z) => new K.Double3(x, y, z);
        private static K.Float3 F3(float x, float y, float z) => new K.Float3(x, y, z);
        private static K.Float4 Q() => new K.Float4(0f, 0f, 0f, 1f);

        private static void Require(bool condition, string message)
        {
            if (!condition)
                throw new InvalidOperationException("Inert Endminf owner solver verification failed: " + message);
        }

        private static uint Bits(float value) => BitConverter.ToUInt32(BitConverter.GetBytes(value), 0);

        private static void RequireBits(float actual, uint expected, string message)
        {
            if (Bits(actual) != expected)
                throw new InvalidOperationException(
                    "Inert Endminf owner solver verification failed: " + message);
        }

        private static void RequireDouble3Bits(K.Double3 actual, K.Double3 expected, string message)
        {
            RequireBits((float)actual.x, Bits((float)expected.x), message + " x");
            RequireBits((float)actual.y, Bits((float)expected.y), message + " y");
            RequireBits((float)actual.z, Bits((float)expected.z), message + " z");
        }

        private static void RequireFloat4Bits(K.Float4 actual, K.Float4 expected, string message)
        {
            RequireBits(actual.x, Bits(expected.x), message + " x");
            RequireBits(actual.y, Bits(expected.y), message + " y");
            RequireBits(actual.z, Bits(expected.z), message + " z");
            RequireBits(actual.w, Bits(expected.w), message + " w");
        }

        private static void RequireFloat3Zero(K.Float3 actual, string message)
        {
            RequireBits(actual.x, 0U, message + " x");
            RequireBits(actual.y, 0U, message + " y");
            RequireBits(actual.z, 0U, message + " z");
        }

        private static void Expect<TException>(Action action) where TException : Exception
        {
            try { action(); }
            catch (TException) { return; }
            throw new InvalidOperationException(
                "Inert Endminf owner solver verification failed: expected " + typeof(TException).Name);
        }
    }
}
