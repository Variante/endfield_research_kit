using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using F = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsFrameCoordinator;
using K = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels;
using P = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsEndminfColliderPreparation;
using D = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsData;
using CD = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsCalcDisplayPosition;
using S = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsOwnerSolver;
using T = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsTimeStepper;

namespace EndfieldGraphShaderLabEditor
{
    public static class EndfieldSecondaryDynamicsFrameCoordinatorVerifier
    {
        private sealed class Trace : F.IStageObserver
        {
            public readonly List<string> Rows = new List<string>();
            public void OnStage(F.Stage stage, int owner, int step,
                S.Stage ownerStage, int source) =>
                Rows.Add(owner + ":" + step + ":" + stage + ":" + ownerStage + ":" + source);
        }

        [MenuItem("Endfield/Character Recovery Lab/Verify Inert Endminf Frame Coordinator")]
        public static void VerifyMenu()
        {
            Verify();
            Debug.Log("Verified inert pure-managed Endminf four-owner frame coordinator, stage order, rollback, and value-only publication.");
        }

        public static void Verify()
        {
            D data = ScriptableObject.CreateInstance<D>();
            try
            {
                data.owners = Owners();
                data.colliders = Colliders();
                F.OwnerTransformSnapshot[] snapshots = Snapshots(data.owners);
                var trace = new Trace();
                var coordinator = new F(data, snapshots, trace);

                K.Double3[][] before = coordinator.PublicationPositions;
                F.FrameInput frame = Frame(snapshots);
                int[] counts = coordinator.AdvanceFrame(frame);
                for (int owner = 0; owner < 4; owner++) Require(counts[owner] == 1, "retail first-frame count");
                RequireTrace(trace.Rows);
                VerifyDistinctFrameOldTime(data, snapshots);
                VerifyPositiveScaleQuaternionSignMask();

                // The coordinator consumes snapshots as values and never writes their arrays.
                for (int owner = 0; owner < 4; owner++)
                    for (int vertex = 0; vertex < snapshots[owner].CurrentWorldPositions.Length; vertex++)
                        Require(BitConverter.DoubleToInt64Bits(snapshots[owner].CurrentWorldPositions[vertex].y) ==
                            BitConverter.DoubleToInt64Bits(vertex * 0.01), "no transform-snapshot write");

                K.Double3[][] committed = coordinator.PublicationPositions;
                frame.Session = new F.SessionCertification(true, true, true, false,
                    F.WritebackRoute.TransformAccess);
                Expect<NotSupportedException>(() => coordinator.AdvanceFrame(frame));
                K.Double3[][] afterFailure = coordinator.PublicationPositions;
                RequireEqual(committed, afterFailure, "session failure rollback");

                frame = Frame(snapshots);
                frame.Owners[3].CurrentWorldPositions = new K.Double3[69];
                Expect<ArgumentException>(() => coordinator.AdvanceFrame(frame));
                RequireEqual(committed, coordinator.PublicationPositions, "topology failure rollback");

                Require(before.Length == 4 && committed.Length == 4, "publication-only owner arrays");
            }
            finally { UnityEngine.Object.DestroyImmediate(data); }
        }

        private static void VerifyDistinctFrameOldTime(
            D data,
            F.OwnerTransformSnapshot[] snapshots)
        {
            var coordinator = new F(data, snapshots);
            F.FrameInput frame = Frame(snapshots);
            frame.Timing = new F.FrameTiming(
                true,
                false,
                false,
                false,
                1f / 120f,
                1f / 120f,
                1f / 120f);
            int[] firstCounts = coordinator.AdvanceFrame(frame);
            int[] secondCounts = coordinator.AdvanceFrame(frame);
            for (int owner = 0; owner < 4; owner++)
            {
                Require(firstCounts[owner] == 0, "120 Hz first frame must accumulate zero steps");
                Require(secondCounts[owner] == 1, "120 Hz second frame must accumulate one step");
            }

            T.TimeManagerScalars time = T.CreateRetailDefault();
            var expectedTeam = new T.TeamState
            {
                Flag = CD.FlagProcess | CD.FlagRunning,
                TimeScale = 1f,
                FrameInterpolation = 1f,
            };
            var clock = new T.TeamFrameInput(
                true,
                false,
                false,
                false,
                1f / 120f,
                1f / 120f,
                1f / 120f);
            Require(T.AccumulateTeam(ref expectedTeam, clock, time) == 0,
                "reference 120 Hz first frame count");
            Require(T.AccumulateTeam(ref expectedTeam, clock, time) == 1,
                "reference 120 Hz second frame count");
            Require(
                T.ExecuteTeamStepClock(
                    ref expectedTeam,
                    0,
                    time.SimulationDeltaTime),
                "reference 120 Hz first substep");

            float actual = coordinator.CenterStates[0].FrameInterpolation;
            Require(
                BitConverter.SingleToInt32Bits(actual) ==
                BitConverter.SingleToInt32Bits(expectedTeam.FrameInterpolation),
                "coordinator must use TeamData.frameOldTime for the 120/90 Hz center interpolation");
            Require(actual > 0.6f && actual < 0.7f,
                "120/90 Hz center interpolation must be the native two-thirds cadence, not oldTime's one-third alias");
        }

        private static void VerifyPositiveScaleQuaternionSignMask()
        {
            const float qz90 = 0.70710677f;
            var stepPositions = new[]
            {
                F3(0f, 0f, 0f),
                F3(0f, 0f, 0f),
            };
            var stepRotations = new[]
            {
                Q(),
                Q(),
            };
            K.UpdateBasicPosture(
                new[] { -1, 0 },
                new byte[] { 2, 2 },
                new[] { F3(0f, 0f, 0f), F3(0f, 0f, 0f) },
                new[] { Q(), new K.Float4(0f, 0f, qz90, qz90) },
                new[] { F3(0f, 0f, 0f), F3(0f, 0f, 0f) },
                new[] { Q(), Q() },
                stepPositions,
                stepRotations,
                F3(1f, 1f, 1f),
                1f,
                F3(1f, 1f, 1f),
                F.PositiveScaleQuaternionSignMask,
                0f);
            RequireFloatBits(stepRotations[1].x, 0f,
                "positive-scale posture rotation x");
            RequireFloatBits(stepRotations[1].y, 0f,
                "positive-scale posture rotation y");
            RequireFloatBits(stepRotations[1].z, qz90,
                "positive-scale posture rotation z");
            RequireFloatBits(stepRotations[1].w, qz90,
                "positive-scale posture rotation w");
        }

        private static void RequireFloatBits(float actual, float expected, string message)
        {
            Require(
                BitConverter.SingleToInt32Bits(actual) ==
                BitConverter.SingleToInt32Bits(expected),
                message);
        }

        private static void RequireTrace(List<string> rows)
        {
            int cursor = 0;
            for (int owner = 0; owner < 4; owner++)
            {
                Require(rows[cursor++] == owner + ":-1:AggregateFixed:Start:-1", "aggregate source order");
                Require(rows[cursor++] == owner + ":0:SimulationStepTeamUpdate:Start:-1", "team update order");
                if (owner != 1)
                    Require(rows[cursor++] == owner + ":0:PrepareColliders:Start:-1", "collider preparation order");
            }
            string[] withoutCollision = { "Start", "BasicPosture", "Tether", "DistancePass1",
                "AngleBaseline", "DistancePass2", "End", "ColliderSnapshotBoundary" };
            for (int owner = 0; owner < 4; owner++)
            {
                var stages = new List<string>(withoutCollision);
                if (owner != 1) stages.Insert(5, "PointCollision");
                foreach (string stage in stages)
                    Require(rows[cursor++].StartsWith(owner + ":0:OwnerSolver:" + stage + ":"),
                        "owner solver stage " + owner + "/" + stage);
                Require(
                    rows[cursor++] == owner + ":-1:OwnerSolver:CalcDisplayPosition:-1",
                    "owner CalcDisplayPosition publication order " + owner);
            }
            Require(cursor == rows.Count && rows.Count == 50, "exact four-owner stage count");
            Require(!rows.Exists(row => row.StartsWith("1:0:OwnerSolver:PointCollision")),
                "Hair exact no-collider path");
        }

        private static F.FrameInput Frame(F.OwnerTransformSnapshot[] snapshots) => new F.FrameInput
        {
            Owners = CloneSnapshots(snapshots),
            Timing = new F.FrameTiming(true, false, false, false,
                1f / 60f, 1f / 60f, 1f / 60f),
            ActorRootStationary = true,
            ActorScale = F3(1f, 1f, 1f),
            NegativeScale = false,
            WindZoneCount = 0,
            // Controlled certified route for the coordinator equations. The live
            // overview values still require the contract's two telemetry lanes.
            Session = new F.SessionCertification(
                true, false, true, false, F.WritebackRoute.TransformAccess),
            PreviousColliderSamples = ColliderSamples(),
            CurrentColliderSamples = ColliderSamples(),
        };

        private static F.OwnerTransformSnapshot[] Snapshots(D.Owner[] owners)
        {
            var result = new F.OwnerTransformSnapshot[4];
            for (int owner = 0; owner < 4; owner++)
            {
                int count = owners[owner].proxyVertexCount;
                var positions = new K.Double3[count];
                var rotations = new K.Float4[count];
                for (int i = 0; i < count; i++)
                {
                    positions[i] = new K.Double3(owner * 0.1, i * 0.01, 0.0);
                    rotations[i] = Q();
                }
                result[owner] = new F.OwnerTransformSnapshot
                {
                    CurrentWorldPositions = (K.Double3[])positions.Clone(),
                    CurrentWorldRotations = (K.Float4[])rotations.Clone(),
                    PreviousWorldPositions = (K.Double3[])positions.Clone(),
                    PreviousWorldRotations = (K.Float4[])rotations.Clone(),
                };
            }
            return result;
        }

        private static F.OwnerTransformSnapshot[] CloneSnapshots(F.OwnerTransformSnapshot[] source)
        {
            var result = new F.OwnerTransformSnapshot[source.Length];
            for (int i = 0; i < source.Length; i++) result[i] = new F.OwnerTransformSnapshot
            {
                CurrentWorldPositions = (K.Double3[])source[i].CurrentWorldPositions.Clone(),
                CurrentWorldRotations = (K.Float4[])source[i].CurrentWorldRotations.Clone(),
                PreviousWorldPositions = (K.Double3[])source[i].PreviousWorldPositions.Clone(),
                PreviousWorldRotations = (K.Float4[])source[i].PreviousWorldRotations.Clone(),
            };
            return result;
        }

        private static P.TransformSample[] ColliderSamples()
        {
            var result = new P.TransformSample[10];
            for (int i = 0; i < result.Length; i++)
                result[i] = new P.TransformSample(new K.Double3(i * 0.01, 0.5, 0.0), Q(), F3(1f, 1f, 1f));
            return result;
        }

        private static D.CapsuleCollider[] Colliders()
        {
            uint[,] centers =
            {
                { 0xbd8f5c29U, 0U, 0xbde147aeU }, { 0xbe570a3dU, 0U, 0U },
                { 0xbca3d70aU, 0U, 0xbda3d70aU }, { 0xbdb851ecU, 0U, 0xbd99999aU },
                { 0U, 0U, 0U }, { 0xbe570a3dU, 0U, 0U },
                { 0xbd8f5c29U, 0U, 0xbde147aeU }, { 0xbca3d70aU, 0U, 0xbda3d70aU },
                { 0U, 0U, 0U }, { 0xbdb851ecU, 0U, 0xbd99999aU },
            };
            uint[,] sizes =
            {
                { 0x3ddf3b64U, 0x3deb851fU, 0x3ecc49baU }, { 0x3d9db22dU, 0x3a83126fU, 0x3efa5e35U },
                { 0x3d5d2f1bU, 0x3d8d4fdfU, 0x3e72b021U }, { 0x3d916873U, 0x3a83126fU, 0x3ea3d70aU },
                { 0x3dd70a3dU, 0x3dd91687U, 0x3e981062U }, { 0x3d9db22dU, 0x3a83126fU, 0x3efa5e35U },
                { 0x3de978d5U, 0x3e041893U, 0x3ecc49baU }, { 0x3d5d2f1bU, 0x3d8d4fdfU, 0x3e72b021U },
                { 0x3dced917U, 0x3dbc6a7fU, 0x3e94fdf4U }, { 0x3d916873U, 0x3a83126fU, 0x3ea3d70aU },
            };
            var result = new D.CapsuleCollider[10];
            for (int i = 0; i < result.Length; i++) result[i] = new D.CapsuleCollider
            {
                transformPath = "Collider/" + i,
                center = new Vector3(FromBits(centers[i, 0]), FromBits(centers[i, 1]), FromBits(centers[i, 2])),
                size = new Vector3(FromBits(sizes[i, 0]), FromBits(sizes[i, 1]), FromBits(sizes[i, 2])),
                direction = i == 4 ? 2 : 0,
                radiusSeparation = i == 0 || i == 2 || i == 6 || i == 7 || i == 8,
                alignedOnCenter = true,
            };
            return result;
        }

        private static D.Owner[] Owners()
        {
            string[] names = { "MC_Ribbon2", "MC_Hair", "MC_Ribbon", "MC_Coat" };
            int[] counts = { 6, 30, 20, 70 };
            int[] fixedCounts = { 1, 8, 4, 9 };
            int[][] colliderIndices = { new[] { 0, 1 }, Array.Empty<int>(),
                new[] { 2, 3, 4, 5 }, new[] { 6, 7, 8, 9 } };
            var result = new D.Owner[4];
            for (int owner = 0; owner < 4; owner++)
                result[owner] = Owner(names[owner], counts[owner], fixedCounts[owner], colliderIndices[owner]);
            return result;
        }

        private static D.Owner Owner(string name, int count, int fixedCount,
            int[] colliderIndices)
        {
            var paths = new string[count];
            var references = new int[count];
            var attributes = new byte[count];
            var depths = new float[count];
            var roots = new int[count];
            var parents = new int[count];
            var localPositions = new Vector3[count];
            var rotations = new Quaternion[count];
            var fixedList = new ushort[fixedCount];
            var packed = new int[count];
            for (int i = 0; i < count; i++)
            {
                paths[i] = name + "/" + i; references[i] = i; attributes[i] = (byte)(i < fixedCount ? 0 : 2);
                depths[i] = count == 1 ? 0f : (float)i / (count - 1); roots[i] = i == 0 ? -1 : 0;
                parents[i] = i == 0 ? -1 : i - 1; localPositions[i] = i == 0 ? Vector3.zero : Vector3.up * 0.01f;
                rotations[i] = Quaternion.identity;
                if (i < fixedCount) fixedList[i] = (ushort)i;
            }
            float[] ones = new float[16]; for (int i = 0; i < 16; i++) ones[i] = 1f;
            return new D.Owner
            {
                ownerPath = name, proxyTransformPaths = paths, proxyVertexCount = count,
                baselineCount = 1, centerFixedCount = fixedCount, colliderCount = colliderIndices.Length,
                referenceIndices = references, attributes = attributes, vertexDepths = depths,
                vertexRootIndices = roots, vertexParentIndices = parents, vertexLocalPositions = localPositions,
                vertexLocalRotations = (Quaternion[])rotations.Clone(), vertexBindPoseRotations = (Quaternion[])rotations.Clone(),
                vertexToTransformRotations = (Quaternion[])rotations.Clone(), baseLineFlags = new byte[] { 1 },
                baseLineStartDataIndices = new ushort[] { 0 }, baseLineDataCounts = new ushort[] { 2 },
                baseLineData = new ushort[] { 0, 1 }, centerFixedList = fixedList,
                distanceConstraintIndexArray = packed, distanceConstraintDataArray = Array.Empty<ushort>(),
                distanceConstraintRestLengths = Array.Empty<float>(), colliderIndices = colliderIndices,
                solverInputs = SolverInputs(name),
            };
        }

        private static D.SolverInputs SolverInputs(string name)
        {
            float[] ones = new float[16]; for (int i = 0; i < 16; i++) ones[i] = 1f;
            return new D.SolverInputs
            {
                authoredScalarsRecovered = true, compiledCurveSamplesRecovered = true,
                dampingCurveData = (float[])ones.Clone(), radiusCurveData = (float[])ones.Clone(),
                distanceRestorationStiffness = (float[])ones.Clone(), angleRestorationStiffness = (float[])ones.Clone(),
                angleLimit = (float[])ones.Clone(), normalAxis = 1, gravityDirection = Vector3.down,
                animationPoseRatio = 1f, localInertia = name == "MC_Hair" ? 1f : name == "MC_Coat" ? 0.8f : 0f,
                localMovementSpeedLimit = -1f, localRotationSpeedLimit = name == "MC_Coat" ? 720f : -1f,
                radiusValue = 0.01f, tetherStretchLimit = BitConverter.Int32BitsToSingle(unchecked((int)0x3cf5c28f)),
                distanceVelocityAttenuation = BitConverter.Int32BitsToSingle(unchecked((int)0x3e99999a)),
                angleRestorationEnabled = true, colliderDynamicFriction = 0f, colliderStaticFriction = 0f,
                springLimitDistance = 1f, springNormalLimitRatio = 1f,
            };
        }

        private static void RequireEqual(K.Double3[][] left, K.Double3[][] right, string message)
        {
            Require(left.Length == right.Length, message);
            for (int i = 0; i < left.Length; i++) for (int j = 0; j < left[i].Length; j++)
            {
                Require(BitConverter.DoubleToInt64Bits(left[i][j].x) == BitConverter.DoubleToInt64Bits(right[i][j].x), message);
                Require(BitConverter.DoubleToInt64Bits(left[i][j].y) == BitConverter.DoubleToInt64Bits(right[i][j].y), message);
                Require(BitConverter.DoubleToInt64Bits(left[i][j].z) == BitConverter.DoubleToInt64Bits(right[i][j].z), message);
            }
        }

        private static K.Float3 F3(float x, float y, float z) => new K.Float3(x, y, z);
        private static K.Float4 Q() => new K.Float4(0f, 0f, 0f, 1f);
        private static uint Bits(float value) => BitConverter.ToUInt32(BitConverter.GetBytes(value), 0);
        private static float FromBits(uint value) => BitConverter.ToSingle(BitConverter.GetBytes(value), 0);
        private static void RequireBits(float actual, uint expected, string message) => Require(Bits(actual) == expected, message);
        private static void Require(bool condition, string message)
        { if (!condition) throw new InvalidOperationException("Frame coordinator verification failed: " + message); }
        private static void Expect<T>(Action action) where T : Exception
        { try { action(); } catch (T) { return; } throw new InvalidOperationException("Expected " + typeof(T).Name); }
    }
}
