using System;
using K = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels;
using C = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsCenterAggregation;
using P = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsEndminfColliderPreparation;
using S = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsOwnerSolver;
using U = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsSimulationStepTeamUpdate;
using T = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsTimeStepper;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Inert frame-level composition of the recovered Endminf secondary-dynamics helpers.
    /// All transform state is supplied as values and results remain publication arrays.
    /// </summary>
    public sealed class EndfieldSecondaryDynamicsFrameCoordinator
    {
        public const int OwnerCount = 4;

        public enum WritebackRoute { TransformAccess, AnimatorBuffer }
        public enum Stage { AggregateFixed, SimulationStepTeamUpdate, PrepareColliders, OwnerSolver }

        public interface IStageObserver
        {
            void OnStage(Stage stage, int ownerIndex, int substepIndex, S.Stage ownerStage, int sourceIndex);
        }

        public readonly struct SessionCertification
        {
            public readonly bool Certified;
            public readonly bool UseRelativeTransform;
            public readonly bool UseCrossFrameJob;
            public readonly bool UseAnimatorTransform;
            public readonly WritebackRoute Writeback;

            public SessionCertification(bool certified, bool useRelativeTransform,
                bool useCrossFrameJob, bool useAnimatorTransform, WritebackRoute writeback)
            {
                Certified = certified;
                UseRelativeTransform = useRelativeTransform;
                UseCrossFrameJob = useCrossFrameJob;
                UseAnimatorTransform = useAnimatorTransform;
                Writeback = writeback;
            }
        }

        public sealed class OwnerTransformSnapshot
        {
            public K.Double3[] CurrentWorldPositions;
            public K.Float4[] CurrentWorldRotations;
            public K.Double3[] PreviousWorldPositions;
            public K.Float4[] PreviousWorldRotations;
        }

        public readonly struct FrameTiming
        {
            public readonly bool Enabled;
            public readonly bool CullingInvisible;
            public readonly bool FixedUpdate;
            public readonly bool Unscaled;
            public readonly float DeltaTime;
            public readonly float FixedDeltaTime;
            public readonly float UnscaledDeltaTime;

            public FrameTiming(bool enabled, bool cullingInvisible, bool fixedUpdate, bool unscaled,
                float deltaTime, float fixedDeltaTime, float unscaledDeltaTime)
            {
                Enabled = enabled;
                CullingInvisible = cullingInvisible;
                FixedUpdate = fixedUpdate;
                Unscaled = unscaled;
                DeltaTime = deltaTime;
                FixedDeltaTime = fixedDeltaTime;
                UnscaledDeltaTime = unscaledDeltaTime;
            }
        }

        public sealed class FrameInput
        {
            public OwnerTransformSnapshot[] Owners;
            public FrameTiming Timing;
            public bool ActorRootStationary;
            public K.Float3 ActorScale;
            public bool NegativeScale;
            public int WindZoneCount;
            public SessionCertification Session;
            public P.TransformSample[] PreviousColliderSamples;
            public P.TransformSample[] CurrentColliderSamples;
        }

        private sealed class ForwardObserver : S.IStageObserver
        {
            private readonly EndfieldSecondaryDynamicsFrameCoordinator _coordinator;
            private readonly int _owner;
            public ForwardObserver(EndfieldSecondaryDynamicsFrameCoordinator coordinator, int owner)
            { _coordinator = coordinator; _owner = owner; }
            public void OnStage(S.Stage stage, int substepIndex, int sourceIndex) =>
                _coordinator._observer?.OnStage(Stage.OwnerSolver, _owner, substepIndex, stage, sourceIndex);
        }

        private readonly EndfieldSecondaryDynamicsData.Owner[] _owners;
        private readonly EndfieldSecondaryDynamicsData.CapsuleCollider[] _colliders;
        private readonly S[] _solvers;
        private readonly U.CenterState[] _centers;
        private readonly IStageObserver _observer;
        private readonly T.TimeManagerScalars _time = T.CreateRetailDefault();

        public K.Double3[][] PublicationPositions
        {
            get
            {
                var result = new K.Double3[OwnerCount][];
                for (int i = 0; i < OwnerCount; i++) result[i] = (K.Double3[])_solvers[i].PublicationPositions.Clone();
                return result;
            }
        }

        public K.Float4[][] PublicationRotations
        {
            get
            {
                var result = new K.Float4[OwnerCount][];
                for (int i = 0; i < OwnerCount; i++) result[i] = (K.Float4[])_solvers[i].PublicationRotations.Clone();
                return result;
            }
        }

        public EndfieldSecondaryDynamicsFrameCoordinator(EndfieldSecondaryDynamicsData data,
            OwnerTransformSnapshot[] initialSnapshots, IStageObserver observer = null)
        {
            if (data == null) throw new ArgumentNullException(nameof(data));
            ValidateData(data);
            ValidateSnapshots(data.owners, initialSnapshots);
            _owners = (EndfieldSecondaryDynamicsData.Owner[])data.owners.Clone();
            _colliders = (EndfieldSecondaryDynamicsData.CapsuleCollider[])data.colliders.Clone();
            _observer = observer;
            _solvers = new S[OwnerCount];
            _centers = new U.CenterState[OwnerCount];
            for (int owner = 0; owner < OwnerCount; owner++)
            {
                OwnerTransformSnapshot snapshot = initialSnapshots[owner];
                C.Result center = Aggregate(_owners[owner], snapshot.PreviousWorldPositions,
                    snapshot.PreviousWorldRotations);
                _centers[owner] = InitialCenter(center);
                _solvers[owner] = new S(_owners[owner], BaseFrame(snapshot),
                    new T.TeamState { TimeScale = 1f, FrameInterpolation = 1f },
                    new ForwardObserver(this, owner));
            }
        }

        public int[] AdvanceFrame(FrameInput input)
        {
            ValidateFrame(input);
            var counts = new int[OwnerCount];
            var candidateCenters = (U.CenterState[])_centers.Clone();
            var centerSteps = new S.CenterTeamStepInput[OwnerCount][];
            var capsuleFrames = new S.PreparedCapsuleFrame[OwnerCount];
            var clock = Clock(input.Timing);

            // Full preflight and pure preparation happens before any owner state advances.
            for (int owner = 0; owner < OwnerCount; owner++)
            {
                T.TeamState preview = _solvers[owner].TeamState;
                counts[owner] = T.AccumulateTeam(ref preview, clock, _time);
                C.Result previous = Aggregate(_owners[owner], input.Owners[owner].PreviousWorldPositions,
                    input.Owners[owner].PreviousWorldRotations);
                C.Result current = Aggregate(_owners[owner], input.Owners[owner].CurrentWorldPositions,
                    input.Owners[owner].CurrentWorldRotations);
                _observer?.OnStage(Stage.AggregateFixed, owner, -1, default, -1);

                centerSteps[owner] = new S.CenterTeamStepInput[counts[owner]];
                P.PreparedCollider[][] prepared = _owners[owner].colliderCount == 0
                    ? null : new P.PreparedCollider[counts[owner]][];
                P.RegisteredCollider[] registered = prepared == null
                    ? null : RegisterColliders(input.PreviousColliderSamples);
                U.CenterState center = candidateCenters[owner];
                for (int step = 0; step < counts[owner]; step++)
                {
                    if (!T.ExecuteTeamStepClock(ref preview, step, _time.SimulationDeltaTime))
                        throw new InvalidOperationException("The preflight retail clock rejected a substep.");
                    U.Execute(ref center, new U.FrameInput
                    {
                        Time = preview.Time,
                        FrameOldTime = preview.OldTime,
                        OldFrameWorldPosition = previous.Position,
                        FrameWorldPosition = current.Position,
                        OldFrameWorldRotation = previous.Rotation,
                        FrameWorldRotation = current.Rotation,
                        FrameScale = input.ActorScale,
                        WindZoneCount = input.WindZoneCount,
                        NegativeScale = input.NegativeScale,
                        StationaryActorRoot = input.ActorRootStationary,
                    }, new U.Parameters
                    {
                        LocalInertia = _owners[owner].solverInputs.localInertia,
                        LocalMovementSpeedLimit = _owners[owner].solverInputs.localMovementSpeedLimit,
                        LocalRotationSpeedLimit = _owners[owner].solverInputs.localRotationSpeedLimit,
                    }, _time.SimulationDeltaTime);
                    _observer?.OnStage(Stage.SimulationStepTeamUpdate, owner, step, default, -1);

                    if (prepared != null)
                    {
                        prepared[step] = PrepareColliders(registered, input.CurrentColliderSamples,
                            center.FrameInterpolation, center.StepMoveInertiaRatio, center.StepRotationInertiaRatio);
                        _observer?.OnStage(Stage.PrepareColliders, owner, step, default, -1);
                    }
                    centerSteps[owner][step] = MakeCenterInput(_owners[owner], center);
                }
                candidateCenters[owner] = center;
                capsuleFrames[owner] = prepared == null ? null : MakeCapsuleFrame(_owners[owner], prepared);
            }

            for (int owner = 0; owner < OwnerCount; owner++)
                _solvers[owner].AdvanceFrame(clock, BaseFrame(input.Owners[owner]),
                    centerSteps[owner], capsuleFrames[owner]);
            Array.Copy(candidateCenters, _centers, OwnerCount);
            return counts;
        }

        private static S.CenterTeamStepInput MakeCenterInput(EndfieldSecondaryDynamicsData.Owner owner,
            U.CenterState center) => new S.CenterTeamStepInput(
                1f, 1f, 1f, 0, 0, F3(0f, 0f, 0f), center.OldWorldPosition,
                center.StepVector, center.StepRotation, center.InertiaVector, center.InertiaRotation,
                center.NowWorldPosition, center.AngularVelocity, center.RotationAxis, 1f, true,
                owner.solverInputs.springEnabled, F3(1f, 1f, 1f), F3(1f, 1f, 1f), Identity(),
                owner.colliderCount == 0 ? null : ParticleRadii(owner));

        private static float[] ParticleRadii(EndfieldSecondaryDynamicsData.Owner owner)
        {
            var result = new float[owner.proxyVertexCount];
            for (int i = 0; i < result.Length; i++)
            {
                float radius = owner.solverInputs.radiusUsesCurve
                    ? SampleCurve(owner.vertexDepths[i], owner.solverInputs.radiusCurveData)
                    : owner.solverInputs.radiusValue;
                result[i] = Math.Max(radius, 0.0001f);
            }
            return result;
        }

        private static float SampleCurve(float depth, float[] values)
        {
            float clamped = Math.Min(Math.Max(depth, 0f), 1f);
            float scaled = clamped * 15f;
            int index = (int)scaled;
            const float step = 0.06666667014360428f;
            float fraction = (depth - index * step) / step;
            int first = Math.Min(Math.Max(index, 0), 15);
            int second = Math.Min(Math.Max(index + 1, 0), 15);
            return values[first] + fraction * (values[second] - values[first]);
        }

        private static S.PreparedCapsuleFrame MakeCapsuleFrame(EndfieldSecondaryDynamicsData.Owner owner,
            P.PreparedCollider[][] prepared)
        {
            var frame = new S.PreparedCapsuleFrame
            {
                WorkBySubstep = new K.CapsuleColliderWork[prepared.Length][],
                NowPositions = new K.Double3[P.AuthoredColliderCount],
                NowRotations = new K.Float4[P.AuthoredColliderCount],
                OldPositions = new K.Double3[P.AuthoredColliderCount],
                OldRotations = new K.Float4[P.AuthoredColliderCount],
            };
            for (int step = 0; step < prepared.Length; step++)
            {
                frame.WorkBySubstep[step] = new K.CapsuleColliderWork[owner.colliderCount];
                for (int local = 0; local < owner.colliderCount; local++)
                    frame.WorkBySubstep[step][local] = ToWork(prepared[step][owner.colliderIndices[local]]);
            }
            if (prepared.Length > 0)
            {
                for (int i = 0; i < P.AuthoredColliderCount; i++)
                {
                    P.PreparedCollider row = prepared[prepared.Length - 1][i];
                    frame.NowPositions[i] = row.FramePosition;
                    frame.NowRotations[i] = row.FrameRotation;
                    frame.OldPositions[i] = row.ColliderStartOldFramePosition;
                    frame.OldRotations[i] = row.ColliderStartOldFrameRotation;
                }
            }
            return frame;
        }

        private P.RegisteredCollider[] RegisterColliders(P.TransformSample[] previousSamples)
        {
            var result = new P.RegisteredCollider[P.AuthoredColliderCount];
            for (int i = 0; i < result.Length; i++)
                result[i] = P.Register(i, _colliders[i], previousSamples[i]);
            return result;
        }

        private static P.PreparedCollider[] PrepareColliders(P.RegisteredCollider[] registered,
            P.TransformSample[] currentSamples, float interpolation, float moveRatio, float rotationRatio)
        {
            var result = new P.PreparedCollider[P.AuthoredColliderCount];
            for (int i = 0; i < result.Length; i++)
                result[i] = P.PrepareAndStart(ref registered[i], currentSamples[i], false,
                    interpolation, moveRatio, rotationRatio);
            return result;
        }

        private static K.CapsuleColliderWork ToWork(P.PreparedCollider value)
        {
            K.ColliderStartWorkData work = value.State.workData;
            return new K.CapsuleColliderWork { flag = value.ColliderStartFlag,
                aabbMin = work.aabbMin, aabbMax = work.aabbMax, radius0 = work.radius0,
                radius1 = work.radius1, old0 = work.old0, old1 = work.old1,
                next0 = work.next0, next1 = work.next1,
                inverseOldRotation = work.inverseOldRotation, rotation = work.rotation };
        }

        private static C.Result Aggregate(EndfieldSecondaryDynamicsData.Owner owner,
            K.Double3[] positions, K.Float4[] rotations)
        {
            var binds = new K.Float4[owner.vertexBindPoseRotations.Length];
            for (int i = 0; i < binds.Length; i++)
            {
                UnityEngine.Quaternion q = owner.vertexBindPoseRotations[i];
                binds[i] = new K.Float4(q.x, q.y, q.z, q.w);
            }
            return C.AggregateFixed(positions, rotations, binds, owner.centerFixedList, 0,
                owner.centerFixedCount);
        }

        private static U.CenterState InitialCenter(C.Result center) => new U.CenterState
        {
            NowWorldPosition = center.Position, OldWorldPosition = center.Position,
            NowWorldRotation = center.Rotation, OldWorldRotation = center.Rotation,
            StepRotation = Identity(), InertiaRotation = Identity(),
            InitLocalGravityDirection = F3(0f, -1f, 0f),
        };

        private static S.BaseTransformFrame BaseFrame(OwnerTransformSnapshot snapshot) =>
            new S.BaseTransformFrame { CurrentPositions = snapshot.CurrentWorldPositions,
                CurrentRotations = snapshot.CurrentWorldRotations,
                PreviousPositions = snapshot.PreviousWorldPositions,
                PreviousRotations = snapshot.PreviousWorldRotations };

        private static T.TeamFrameInput Clock(FrameTiming timing) => new T.TeamFrameInput(
            timing.Enabled, timing.CullingInvisible, timing.FixedUpdate, timing.Unscaled,
            timing.DeltaTime, timing.FixedDeltaTime, timing.UnscaledDeltaTime);

        private static void ValidateData(EndfieldSecondaryDynamicsData data)
        {
            string[] names = { "MC_Ribbon2", "MC_Hair", "MC_Ribbon", "MC_Coat" };
            int[] counts = { 6, 30, 20, 70 };
            int[] fixedCounts = { 1, 8, 4, 9 };
            int[] colliderCounts = { 2, 0, 4, 4 };
            if (data.owners == null || data.owners.Length != OwnerCount || data.colliders == null ||
                data.colliders.Length != P.AuthoredColliderCount)
                throw new ArgumentException("The coordinator requires the exact four-owner/ten-collider Endminf topology.");
            for (int i = 0; i < OwnerCount; i++)
            {
                var owner = data.owners[i];
                if (owner.ownerPath != names[i] || owner.proxyVertexCount != counts[i] ||
                    owner.centerFixedCount != fixedCounts[i] || owner.colliderCount != colliderCounts[i] ||
                    owner.centerFixedList == null || owner.centerFixedList.Length != fixedCounts[i])
                    throw new ArgumentException("Owner topology or source order differs from Endminf.");
            }
        }

        private static void ValidateSnapshots(EndfieldSecondaryDynamicsData.Owner[] owners,
            OwnerTransformSnapshot[] snapshots)
        {
            if (snapshots == null || snapshots.Length != OwnerCount)
                throw new ArgumentException("Exactly four source-ordered owner snapshots are required.");
            for (int i = 0; i < OwnerCount; i++)
            {
                OwnerTransformSnapshot s = snapshots[i];
                int count = owners[i].proxyVertexCount;
                if (s == null || s.CurrentWorldPositions == null || s.CurrentWorldRotations == null ||
                    s.PreviousWorldPositions == null || s.PreviousWorldRotations == null ||
                    s.CurrentWorldPositions.Length != count || s.CurrentWorldRotations.Length != count ||
                    s.PreviousWorldPositions.Length != count || s.PreviousWorldRotations.Length != count)
                    throw new ArgumentException("Owner transform snapshots do not preserve source topology.");
            }
        }

        private void ValidateFrame(FrameInput input)
        {
            if (input == null) throw new ArgumentNullException(nameof(input));
            ValidateSnapshots(_owners, input.Owners);
            SessionCertification s = input.Session;
            if (!s.Certified || s.UseRelativeTransform || !s.UseCrossFrameJob ||
                s.UseAnimatorTransform || s.Writeback != WritebackRoute.TransformAccess)
                throw new NotSupportedException("Mutable transform-session flags are not certified for the Endminf overview target.");
            if (!input.ActorRootStationary || input.NegativeScale || input.WindZoneCount != 0 ||
                !(input.ActorScale.x > 0f) || !(input.ActorScale.y > 0f) || !(input.ActorScale.z > 0f))
                throw new NotSupportedException("Only stationary, positive-scale, zero-wind Endminf overview frames are supported.");
            if (input.PreviousColliderSamples == null || input.CurrentColliderSamples == null ||
                input.PreviousColliderSamples.Length != P.AuthoredColliderCount ||
                input.CurrentColliderSamples.Length != P.AuthoredColliderCount)
                throw new ArgumentException("Exactly ten source-ordered collider transform samples are required.");
        }

        private static K.Float3 F3(float x, float y, float z) => new K.Float3(x, y, z);
        private static K.Float4 Identity() => new K.Float4(0f, 0f, 0f, 1f);
    }
}
