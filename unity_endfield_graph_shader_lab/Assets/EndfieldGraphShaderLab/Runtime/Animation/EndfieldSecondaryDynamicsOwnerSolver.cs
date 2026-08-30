using System;
using K = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels;
using T = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsTimeStepper;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Inert, pure-managed orchestration of the recovered Endminf owner solver.
    /// This class owns proxy state only: it has no PlayerLoop hook and never writes Transforms.
    /// Inputs omitted by EndfieldSecondaryDynamicsData remain explicit and fail closed.
    /// </summary>
    public sealed class EndfieldSecondaryDynamicsOwnerSolver
    {
        public enum Stage
        {
            Start,
            BasicPosture,
            Tether,
            DistancePass1,
            AngleBaseline,
            PointCollision,
            DistancePass2,
            End,
            ColliderSnapshotBoundary,
            CalcDisplayPosition,
        }

        public interface IStageObserver
        {
            void OnStage(Stage stage, int substepIndex, int sourceIndex);
        }

        public sealed class BaseTransformFrame
        {
            public K.Double3[] CurrentPositions;
            public K.Float4[] CurrentRotations;
            public K.Double3[] PreviousPositions;
            public K.Float4[] PreviousRotations;
        }

        public readonly struct CenterTeamStepInput
        {
            public readonly float GravityRatio;
            public readonly float ScaleRatio;
            public readonly float VelocityWeight;
            public readonly int TeamFlag;
            public readonly int ForceMode;
            public readonly K.Float3 ImpactForce;
            public readonly K.Double3 CenterOldWorldPosition;
            public readonly K.Float3 CenterStepVector;
            public readonly K.Float4 CenterStepRotation;
            public readonly K.Float3 CenterInertiaVector;
            public readonly K.Float4 CenterInertiaRotation;
            public readonly K.Double3 CenterPosition;
            public readonly float CenterAngularVelocity;
            public readonly K.Float3 CenterRotationAxis;
            public readonly float GravityDot;
            public readonly bool Active;
            public readonly bool BoneSpringCollision;
            public readonly K.Float3 InitialScale;
            public readonly K.Float3 NegativeScaleDirection;
            public readonly K.Float4 NegativeScaleQuaternion;
            public readonly float[] ParticleRadii;

            public CenterTeamStepInput(
                float gravityRatio,
                float scaleRatio,
                float velocityWeight,
                int teamFlag,
                int forceMode,
                K.Float3 impactForce,
                K.Double3 centerOldWorldPosition,
                K.Float3 centerStepVector,
                K.Float4 centerStepRotation,
                K.Float3 centerInertiaVector,
                K.Float4 centerInertiaRotation,
                K.Double3 centerPosition,
                float centerAngularVelocity,
                K.Float3 centerRotationAxis,
                float gravityDot,
                bool active,
                bool boneSpringCollision,
                K.Float3 initialScale,
                K.Float3 negativeScaleDirection,
                K.Float4 negativeScaleQuaternion,
                float[] particleRadii)
            {
                GravityRatio = gravityRatio;
                ScaleRatio = scaleRatio;
                VelocityWeight = velocityWeight;
                TeamFlag = teamFlag;
                ForceMode = forceMode;
                ImpactForce = impactForce;
                CenterOldWorldPosition = centerOldWorldPosition;
                CenterStepVector = centerStepVector;
                CenterStepRotation = centerStepRotation;
                CenterInertiaVector = centerInertiaVector;
                CenterInertiaRotation = centerInertiaRotation;
                CenterPosition = centerPosition;
                CenterAngularVelocity = centerAngularVelocity;
                CenterRotationAxis = centerRotationAxis;
                GravityDot = gravityDot;
                Active = active;
                BoneSpringCollision = boneSpringCollision;
                InitialScale = initialScale;
                NegativeScaleDirection = negativeScaleDirection;
                NegativeScaleQuaternion = negativeScaleQuaternion;
                ParticleRadii = particleRadii;
            }
        }

        public sealed class PreparedCapsuleFrame
        {
            // Each entry is already prepared for the corresponding solver substep and
            // is in this owner's collider-reference source order.
            public K.CapsuleColliderWork[][] WorkBySubstep;
            public K.Double3[] NowPositions;
            public K.Float4[] NowRotations;
            public K.Double3[] OldPositions;
            public K.Float4[] OldRotations;
        }

        private sealed class Baseline
        {
            public int[] Vertices;
            public int[] LocalParents;
        }

        private readonly EndfieldSecondaryDynamicsData.Owner _owner;
        private readonly T.TimeManagerScalars _timeManager;
        private readonly Baseline[] _baselines;
        private readonly short[] _displayTeamIds;
        private readonly IStageObserver _observer;
        private T.TeamState _team;

        public K.Double3[] BasePositions { get; private set; }
        public K.Float4[] BaseRotations { get; private set; }
        public K.Double3[] StepBasicPositions { get; private set; }
        public K.Float4[] StepBasicRotations { get; private set; }
        public K.Double3[] VelocityPositions { get; private set; }
        public K.Double3[] SimulationPositions { get; private set; }
        public K.Float4[] SimulationRotations { get; private set; }
        public K.Double3[] DisplayPositions { get; private set; }
        public K.Double3[] DisplayOldPositions { get; private set; }
        public K.Float4[] DisplayOldRotations { get; private set; }
        public K.Double3[] PublicationPositions { get; private set; }
        public K.Float4[] PublicationRotations { get; private set; }
        public K.Float3[] Velocities { get; private set; }
        public K.Float3[] RealVelocities { get; private set; }
        public float[] Frictions { get; private set; }
        public float[] StaticFrictions { get; private set; }
        public K.Float3[] CollisionNormals { get; private set; }
        public T.TeamState TeamState => _team;

        public EndfieldSecondaryDynamicsOwnerSolver(
            EndfieldSecondaryDynamicsData.Owner owner,
            BaseTransformFrame initialBaseTransforms,
            T.TeamState initialTeamState,
            IStageObserver observer = null)
        {
            _owner = CloneOwner(owner);
            _timeManager = T.CreateRetailDefault();
            _team = initialTeamState;
            _observer = observer;
            ValidateOwner(_owner);
            ValidateBaseFrame(initialBaseTransforms, _owner.proxyVertexCount);
            _baselines = BuildBaselines(_owner);
            _displayTeamIds = new short[_owner.proxyVertexCount];
            for (int particle = 0; particle < _displayTeamIds.Length; particle++)
                _displayTeamIds[particle] = 1;
            AllocateAndInitialize(initialBaseTransforms.CurrentPositions, initialBaseTransforms.CurrentRotations);
        }

        /// <summary>
        /// Advances the owned team clock and executes zero or more recovered solver steps.
        /// All mutable proxy state is committed only after every requested step succeeds.
        /// </summary>
        public int AdvanceFrame(
            T.TeamFrameInput clockInput,
            BaseTransformFrame baseTransforms,
            CenterTeamStepInput[] centerTeamSteps,
            PreparedCapsuleFrame preparedCapsules = null)
        {
            ValidateBaseFrame(baseTransforms, _owner.proxyVertexCount);

            T.TeamState candidateTeam = _team;
            int stepCount = T.AccumulateTeam(ref candidateTeam, clockInput, _timeManager);
            if (centerTeamSteps == null || centerTeamSteps.Length != stepCount)
                throw new ArgumentException("Center/team input must contain exactly one entry per accumulated substep.", nameof(centerTeamSteps));
            ValidateCapsules(preparedCapsules, stepCount);
            for (int step = 0; step < stepCount; step++)
                ValidateStepInput(centerTeamSteps[step], preparedCapsules, step);

            State candidate = CloneState();
            K.Double3[] candidateOldColliderPositions = preparedCapsules == null
                ? null : (K.Double3[])preparedCapsules.OldPositions.Clone();
            K.Float4[] candidateOldColliderRotations = preparedCapsules == null
                ? null : (K.Float4[])preparedCapsules.OldRotations.Clone();

            for (int step = 0; step < stepCount; step++)
            {
                if (!T.ExecuteTeamStepClock(
                    ref candidateTeam, step, _timeManager.SimulationDeltaTime))
                    throw new InvalidOperationException("The recovered team clock rejected an accumulated substep.");
                ExecuteSubstep(
                    candidate,
                    baseTransforms,
                    centerTeamSteps[step],
                    preparedCapsules == null ? null : preparedCapsules.WorkBySubstep[step],
                    step,
                    candidateTeam.FrameInterpolation,
                    candidateTeam.NowUpdateTime);

                Notify(Stage.ColliderSnapshotBoundary, step, -1);
                if (preparedCapsules != null)
                {
                    K.FinishColliderSnapshots(
                        _owner.colliderIndices,
                        preparedCapsules.NowPositions,
                        preparedCapsules.NowRotations,
                        candidateOldColliderPositions,
                        candidateOldColliderRotations,
                        _owner.colliderIndices.Length);
                }
            }

            PublishDisplayPosition(
                candidate,
                baseTransforms,
                candidateTeam,
                stepCount > 0);
            Notify(Stage.CalcDisplayPosition, -1, -1);

            Commit(candidate);
            _team = candidateTeam;
            if (preparedCapsules != null)
            {
                Array.Copy(candidateOldColliderPositions, preparedCapsules.OldPositions,
                    candidateOldColliderPositions.Length);
                Array.Copy(candidateOldColliderRotations, preparedCapsules.OldRotations,
                    candidateOldColliderRotations.Length);
            }
            return stepCount;
        }

        private void ExecuteSubstep(
            State state,
            BaseTransformFrame transforms,
            CenterTeamStepInput input,
            K.CapsuleColliderWork[] colliders,
            int substep,
            float frameInterpolation,
            float teamTime)
        {
            int count = _owner.proxyVertexCount;
            var previousPositions = (K.Double3[])state.SimulationPositions.Clone();
            Notify(Stage.Start, substep, -1);
            for (int particle = 0; particle < count; particle++)
            {
                K.StartSimulationParticleZeroWind(
                    _timeManager.SimulationPower.Z,
                    _timeManager.SimulationDeltaTime,
                    _owner.attributes[particle],
                    _owner.vertexDepths[particle],
                    transforms.CurrentPositions[particle],
                    transforms.CurrentRotations[particle],
                    state.DisplayOldPositions[particle],
                    state.DisplayOldRotations[particle],
                    previousPositions[particle],
                    state.Velocities[particle],
                    frameInterpolation,
                    teamTime,
                    input.TeamFlag,
                    input.GravityRatio,
                    input.ScaleRatio,
                    input.VelocityWeight,
                    input.ForceMode,
                    input.ImpactForce,
                    _owner.solverInputs.gravity,
                    ToFloat3(_owner.solverInputs.gravityDirection),
                    _owner.solverInputs.dampingCurveData,
                    _owner.solverInputs.normalAxis,
                    _owner.solverInputs.inertiaDepth,
                    input.CenterOldWorldPosition,
                    input.CenterStepVector,
                    input.CenterStepRotation,
                    input.CenterInertiaVector,
                    input.CenterInertiaRotation,
                    _owner.solverInputs.springPower,
                    _owner.solverInputs.springLimitDistance,
                    _owner.solverInputs.springNormalLimitRatio,
                    _owner.solverInputs.springNoise,
                    out state.BasePositions[particle],
                    out state.BaseRotations[particle],
                    out state.StepBasicPositions[particle],
                    out state.StepBasicRotations[particle],
                    out state.VelocityPositions[particle],
                    out state.SimulationPositions[particle]);
                state.SimulationRotations[particle] = state.StepBasicRotations[particle];
                state.Frictions[particle] = 0f;
                state.CollisionNormals[particle] = new K.Float3(0f, 0f, 0f);
            }

            Notify(Stage.BasicPosture, substep, -1);
            // BasicPosture's positions are float3 buffers in the native job. Publish them
            // back into the double3 proxy buffer before the recovered constraints run.
            K.Float3[] basicFloat = ToFloat3Array(state.StepBasicPositions);
            K.UpdateBasicPosture(
                _owner.vertexParentIndices,
                _owner.attributes,
                ToFloat3Array(_owner.vertexLocalPositions),
                ToFloat4Array(_owner.vertexLocalRotations),
                ToFloat3Array(state.BasePositions),
                state.BaseRotations,
                basicFloat,
                state.StepBasicRotations,
                input.InitialScale,
                input.ScaleRatio,
                input.NegativeScaleDirection,
                input.NegativeScaleQuaternion,
                _owner.solverInputs.animationPoseRatio);
            for (int particle = 0; particle < count; particle++)
            {
                state.StepBasicPositions[particle] = ToDouble3(basicFloat[particle]);
                state.SimulationRotations[particle] = state.StepBasicRotations[particle];
            }

            Notify(Stage.Tether, substep, -1);
            for (int particle = 0; particle < count; particle++)
            {
                int root = _owner.vertexRootIndices[particle];
                if ((_owner.attributes[particle] & 2) == 0 || root < 0)
                    continue;
                K.ProjectTether(
                    state.SimulationPositions[root],
                    ref state.SimulationPositions[particle],
                    state.StepBasicPositions[root],
                    state.StepBasicPositions[particle],
                    _owner.solverInputs.tetherDistanceCompression,
                    _owner.solverInputs.tetherStretchLimit,
                    ref state.VelocityPositions[particle]);
            }

            ProjectDistancePass(state, input, substep, Stage.DistancePass1);

            for (int baselineIndex = 0; baselineIndex < _baselines.Length; baselineIndex++)
            {
                Notify(Stage.AngleBaseline, substep, baselineIndex);
                ProjectBaseline(state, _baselines[baselineIndex], input.GravityDot);
            }

            if (colliders != null)
            {
                Notify(Stage.PointCollision, substep, -1);
                for (int particle = 0; particle < count; particle++)
                {
                    byte attribute = _owner.attributes[particle];
                    if ((attribute & 3) == 0 || (attribute & 0x10) != 0 ||
                        ((attribute & 2) == 0 && (input.TeamFlag & 0x2000) == 0))
                        continue;
                    K.ProjectPointCapsules(
                        ref state.SimulationPositions[particle],
                        ref state.VelocityPositions[particle],
                        ref state.Frictions[particle],
                        out state.CollisionNormals[particle],
                        input.ParticleRadii[particle],
                        colliders,
                        input.BoneSpringCollision);
                }
            }

            ProjectDistancePass(state, input, substep, Stage.DistancePass2);

            Notify(Stage.End, substep, -1);
            for (int particle = 0; particle < count; particle++)
            {
                float speedLimit = _owner.solverInputs.particleSpeedLimitEnabled
                    ? _owner.solverInputs.particleSpeedLimit : -1f;
                K.FinishSimulationParticle(
                    input.Active,
                    _timeManager.SimulationDeltaTime,
                    input.ScaleRatio,
                    input.VelocityWeight,
                    speedLimit,
                    _owner.solverInputs.centrifugalAcceleration,
                    _owner.solverInputs.colliderDynamicFriction,
                    _owner.solverInputs.colliderStaticFriction,
                    _owner.vertexDepths[particle],
                    input.CenterPosition,
                    input.CenterAngularVelocity,
                    input.CenterRotationAxis,
                    ref state.SimulationPositions[particle],
                    previousPositions[particle],
                    ref state.VelocityPositions[particle],
                    ref state.Velocities[particle],
                    ref state.RealVelocities[particle],
                    ref state.Frictions[particle],
                    ref state.StaticFrictions[particle],
                    state.CollisionNormals[particle]);
            }
        }

        private void ProjectDistancePass(
            State state,
            CenterTeamStepInput input,
            int substep,
            Stage stage)
        {
            Notify(stage, substep, -1);
            for (int particle = 0; particle < _owner.proxyVertexCount; particle++)
            {
                int packed = _owner.distanceConstraintIndexArray[particle];
                int start = packed & 0x000fffff;
                int count = (int)((uint)packed >> 20);
                if (count == 0 || (_owner.attributes[particle] & 3) == 0 ||
                    ((_owner.attributes[particle] & 2) == 0 &&
                     (input.TeamFlag & 0x2000) == 0))
                    continue;
                var neighbors = new ushort[count];
                var rest = new float[count];
                Array.Copy(_owner.distanceConstraintDataArray, start, neighbors, 0, count);
                Array.Copy(_owner.distanceConstraintRestLengths, start, rest, 0, count);
                K.ProjectDistance(
                    particle,
                    state.SimulationPositions,
                    state.BasePositions,
                    state.VelocityPositions,
                    _owner.attributes,
                    _owner.vertexDepths,
                    state.Frictions,
                    neighbors,
                    rest,
                    _timeManager.SimulationPower.Y,
                    _owner.solverInputs.distanceRestorationStiffness,
                    _owner.solverInputs.distanceVelocityAttenuation,
                    _owner.solverInputs.animationPoseRatio,
                    input.InitialScale.x,
                    input.ScaleRatio,
                    input.TeamFlag);
            }
        }

        private void ProjectBaseline(State state, Baseline baseline, float gravityDot)
        {
            int count = baseline.Vertices.Length;
            var attributes = new byte[count];
            var depths = new float[count];
            var frictions = new float[count];
            var basicPositions = new K.Double3[count];
            var basicRotations = new K.Float4[count];
            var nextPositions = new K.Double3[count];
            var velocityPositions = new K.Double3[count];
            var rotations = new K.Float4[count];
            var lengths = new float[count];
            var localPositions = new K.Float3[count];
            var localRotations = new K.Float4[count];
            var restorationVectors = new K.Float3[count];
            for (int local = 0; local < count; local++)
            {
                int particle = baseline.Vertices[local];
                attributes[local] = _owner.attributes[particle];
                depths[local] = _owner.vertexDepths[particle];
                frictions[local] = state.Frictions[particle];
                basicPositions[local] = state.StepBasicPositions[particle];
                basicRotations[local] = state.StepBasicRotations[particle];
                nextPositions[local] = state.SimulationPositions[particle];
                velocityPositions[local] = state.VelocityPositions[particle];
                rotations[local] = state.SimulationRotations[particle];
            }
            K.ProjectAngle(
                attributes,
                baseline.LocalParents,
                depths,
                frictions,
                basicPositions,
                basicRotations,
                nextPositions,
                velocityPositions,
                _owner.solverInputs.angleRestorationEnabled,
                _owner.solverInputs.angleRestorationStiffness,
                _owner.solverInputs.angleRestorationVelocityAttenuation,
                _owner.solverInputs.angleRestorationGravityFalloff,
                _owner.solverInputs.angleLimitEnabled,
                _owner.solverInputs.angleLimit,
                _owner.solverInputs.angleLimitStiffness,
                _timeManager.SimulationPower.W,
                gravityDot,
                rotations,
                lengths,
                localPositions,
                localRotations,
                restorationVectors);
            for (int local = 0; local < count; local++)
            {
                int particle = baseline.Vertices[local];
                state.SimulationPositions[particle] = nextPositions[local];
                state.VelocityPositions[particle] = velocityPositions[local];
                state.SimulationRotations[particle] = rotations[local];
            }
        }

        private void PublishDisplayPosition(
            State state,
            BaseTransformFrame transforms,
            T.TeamState team,
            bool simulatedThisFrame)
        {
            int count = _owner.proxyVertexCount;
            K.Double3[] currentPositions = simulatedThisFrame
                ? state.SimulationPositions
                : transforms.CurrentPositions;
            K.Float4[] currentRotations = simulatedThisFrame
                ? state.SimulationRotations
                : transforms.CurrentRotations;
            Array.Copy(currentPositions, state.PublicationPositions, count);
            Array.Copy(currentRotations, state.PublicationRotations, count);

            EndfieldSecondaryDynamicsCalcDisplayPosition.ExecuteRange(
                new EndfieldSecondaryDynamicsCalcDisplayPosition.Job
                {
                    DeltaTime = _timeManager.SimulationDeltaTime,
                    Time = team.Time,
                    OldTime = team.OldTime,
                    NowUpdateTime = team.NowUpdateTime,
                    BlendWeight = _owner.solverInputs.blendWeight,
                    TeamFlag = team.Flag,
                    ParticleChunkStart = 0,
                    ProxyCommonChunkStart = 0,
                    TeamIds = _displayTeamIds,
                    Attributes = _owner.attributes,
                    VertexRootIndices = _owner.vertexRootIndices,
                    OldPos = state.SimulationPositions,
                    DisplayPos = state.DisplayPositions,
                    RealVelocity = state.RealVelocities,
                    Positions = state.PublicationPositions,
                    Rotations = state.PublicationRotations,
                    OldPosition = state.DisplayOldPositions,
                    OldRotation = state.DisplayOldRotations,
                },
                0,
                count);
        }

        private void AllocateAndInitialize(K.Double3[] positions, K.Float4[] rotations)
        {
            int count = _owner.proxyVertexCount;
            // RegisterProxyMesh extends the simulation/display/history arrays
            // with default(T); it does not seed authored poses or a reset
            // trajectory. The VirtualMesh publication arrays are separate and
            // already contain the current transform-read pose.
            BasePositions = new K.Double3[count];
            BaseRotations = new K.Float4[count];
            StepBasicPositions = new K.Double3[count];
            StepBasicRotations = new K.Float4[count];
            VelocityPositions = new K.Double3[count];
            SimulationPositions = new K.Double3[count];
            SimulationRotations = new K.Float4[count];
            DisplayPositions = new K.Double3[count];
            DisplayOldPositions = new K.Double3[count];
            DisplayOldRotations = new K.Float4[count];
            PublicationPositions = (K.Double3[])positions.Clone();
            PublicationRotations = (K.Float4[])rotations.Clone();
            Velocities = new K.Float3[count];
            RealVelocities = new K.Float3[count];
            Frictions = new float[count];
            StaticFrictions = new float[count];
            CollisionNormals = new K.Float3[count];
        }

        private sealed class State
        {
            public K.Double3[] BasePositions;
            public K.Float4[] BaseRotations;
            public K.Double3[] StepBasicPositions;
            public K.Float4[] StepBasicRotations;
            public K.Double3[] VelocityPositions;
            public K.Double3[] SimulationPositions;
            public K.Float4[] SimulationRotations;
            public K.Double3[] DisplayPositions;
            public K.Double3[] DisplayOldPositions;
            public K.Float4[] DisplayOldRotations;
            public K.Double3[] PublicationPositions;
            public K.Float4[] PublicationRotations;
            public K.Float3[] Velocities;
            public K.Float3[] RealVelocities;
            public float[] Frictions;
            public float[] StaticFrictions;
            public K.Float3[] CollisionNormals;
        }

        private State CloneState() => new State
        {
            BasePositions = (K.Double3[])BasePositions.Clone(),
            BaseRotations = (K.Float4[])BaseRotations.Clone(),
            StepBasicPositions = (K.Double3[])StepBasicPositions.Clone(),
            StepBasicRotations = (K.Float4[])StepBasicRotations.Clone(),
            VelocityPositions = (K.Double3[])VelocityPositions.Clone(),
            SimulationPositions = (K.Double3[])SimulationPositions.Clone(),
            SimulationRotations = (K.Float4[])SimulationRotations.Clone(),
            DisplayPositions = (K.Double3[])DisplayPositions.Clone(),
            DisplayOldPositions = (K.Double3[])DisplayOldPositions.Clone(),
            DisplayOldRotations = (K.Float4[])DisplayOldRotations.Clone(),
            PublicationPositions = (K.Double3[])PublicationPositions.Clone(),
            PublicationRotations = (K.Float4[])PublicationRotations.Clone(),
            Velocities = (K.Float3[])Velocities.Clone(),
            RealVelocities = (K.Float3[])RealVelocities.Clone(),
            Frictions = (float[])Frictions.Clone(),
            StaticFrictions = (float[])StaticFrictions.Clone(),
            CollisionNormals = (K.Float3[])CollisionNormals.Clone(),
        };

        private void Commit(State state)
        {
            BasePositions = state.BasePositions;
            BaseRotations = state.BaseRotations;
            StepBasicPositions = state.StepBasicPositions;
            StepBasicRotations = state.StepBasicRotations;
            VelocityPositions = state.VelocityPositions;
            SimulationPositions = state.SimulationPositions;
            SimulationRotations = state.SimulationRotations;
            DisplayPositions = state.DisplayPositions;
            DisplayOldPositions = state.DisplayOldPositions;
            DisplayOldRotations = state.DisplayOldRotations;
            PublicationPositions = state.PublicationPositions;
            PublicationRotations = state.PublicationRotations;
            Velocities = state.Velocities;
            RealVelocities = state.RealVelocities;
            Frictions = state.Frictions;
            StaticFrictions = state.StaticFrictions;
            CollisionNormals = state.CollisionNormals;
        }

        private static Baseline[] BuildBaselines(EndfieldSecondaryDynamicsData.Owner owner)
        {
            var result = new Baseline[owner.baselineCount];
            for (int baselineIndex = 0; baselineIndex < result.Length; baselineIndex++)
            {
                if (owner.baseLineFlags[baselineIndex] != 1)
                    throw new NotSupportedException("Only the recovered Endminf baseline flag 1 is supported.");
                int start = owner.baseLineStartDataIndices[baselineIndex];
                int count = owner.baseLineDataCounts[baselineIndex];
                if (count < 2)
                    throw new ArgumentException("Every recovered Endminf angle baseline requires at least two particles.");
                var sourceVertices = new int[count];
                var localByGlobal = new System.Collections.Generic.Dictionary<int, int>();
                for (int local = 0; local < count; local++)
                {
                    int particle = owner.baseLineData[start + local];
                    if (localByGlobal.ContainsKey(particle))
                        throw new ArgumentException("An angle baseline repeats a proxy vertex.");
                    sourceVertices[local] = particle;
                    localByGlobal.Add(particle, local);
                }

                // Retail baselines may begin at a movable child whose immediate parent
                // is the anchor just outside baseLineData. The Burst job addresses the
                // full proxy arrays, so that parent participates in corrections without
                // being visited as a baseline child. Prepending it as a synthetic local
                // root gives the sliced managed kernel the same addressable closure.
                int externalParent = owner.vertexParentIndices[sourceVertices[0]];
                bool prependAnchor = externalParent >= 0 &&
                    !localByGlobal.ContainsKey(externalParent);
                var vertices = new int[count + (prependAnchor ? 1 : 0)];
                int sourceOffset = prependAnchor ? 1 : 0;
                if (prependAnchor)
                    vertices[0] = externalParent;
                Array.Copy(sourceVertices, 0, vertices, sourceOffset, count);

                localByGlobal.Clear();
                for (int local = 0; local < vertices.Length; local++)
                    localByGlobal.Add(vertices[local], local);
                var localParents = new int[vertices.Length];
                for (int local = 0; local < vertices.Length; local++)
                {
                    int parent = owner.vertexParentIndices[vertices[local]];
                    if (local == 0)
                        localParents[local] = -1;
                    else if (!localByGlobal.TryGetValue(parent, out localParents[local]))
                        throw new NotSupportedException(
                            "An Endminf angle parent lies outside its source baseline closure.");
                }
                result[baselineIndex] = new Baseline { Vertices = vertices, LocalParents = localParents };
            }
            return result;
        }

        private static void ValidateOwner(EndfieldSecondaryDynamicsData.Owner owner)
        {
            int count = owner.proxyVertexCount;
            if (count <= 0 || owner.proxyTransformPaths == null || owner.proxyTransformPaths.Length != count)
                throw new ArgumentException("Owner proxy topology is missing or inconsistent.", nameof(owner));
            RequireLength(owner.referenceIndices, count, "reference indices");
            RequireLength(owner.attributes, count, "attributes");
            RequireLength(owner.vertexDepths, count, "depths");
            RequireLength(owner.vertexRootIndices, count, "root indices");
            RequireLength(owner.vertexParentIndices, count, "parent indices");
            RequireLength(owner.vertexLocalPositions, count, "local positions");
            RequireLength(owner.vertexLocalRotations, count, "local rotations");
            RequireLength(owner.vertexBindPoseRotations, count, "bind-pose rotations");
            RequireLength(owner.vertexToTransformRotations, count, "vertex-to-transform rotations");
            RequireLength(owner.distanceConstraintIndexArray, count, "distance indices");
            if (owner.baseLineFlags == null || owner.baseLineStartDataIndices == null ||
                owner.baseLineDataCounts == null || owner.baseLineData == null ||
                owner.baseLineFlags.Length != owner.baselineCount ||
                owner.baseLineStartDataIndices.Length != owner.baselineCount ||
                owner.baseLineDataCounts.Length != owner.baselineCount)
                throw new ArgumentException("Owner baseline topology is missing or inconsistent.", nameof(owner));
            if (owner.centerFixedList == null || owner.centerFixedList.Length != owner.centerFixedCount)
                throw new ArgumentException("Owner center-fixed topology is missing or inconsistent.", nameof(owner));
            if (owner.distanceConstraintDataArray == null || owner.distanceConstraintRestLengths == null ||
                owner.distanceConstraintDataArray.Length != owner.distanceConstraintRestLengths.Length)
                throw new ArgumentException("Owner distance topology is missing or inconsistent.", nameof(owner));
            if (owner.colliderIndices == null || owner.colliderIndices.Length != owner.colliderCount)
                throw new ArgumentException("Owner collider source order is missing or inconsistent.", nameof(owner));
            if (!owner.solverInputs.authoredScalarsRecovered || !owner.solverInputs.compiledCurveSamplesRecovered)
                throw new NotSupportedException("Authored scalars and compiled curve buffers must be recovered.");
            RequireCurve(owner.solverInputs.dampingCurveData, "damping");
            RequireCurve(owner.solverInputs.radiusCurveData, "radius");
            RequireCurve(owner.solverInputs.distanceRestorationStiffness, "distance");
            RequireCurve(owner.solverInputs.angleRestorationStiffness, "angle restoration");
            RequireCurve(owner.solverInputs.angleLimit, "angle limit");
            if (!owner.solverInputs.angleRestorationEnabled && !owner.solverInputs.angleLimitEnabled)
                throw new NotSupportedException("Every Endminf owner requires a recovered active Angle family.");
            if (owner.solverInputs.normalAxis < 0 || owner.solverInputs.normalAxis > 5)
                throw new NotSupportedException("The recovered normal axis must be in the exact 0-5 domain.");
            RequireFinite(owner.solverInputs.tetherStretchLimit, "tether stretch limit");
            RequireFinite(owner.solverInputs.distanceVelocityAttenuation, "distance velocity attenuation");
            RequireFinite(owner.solverInputs.colliderStaticFriction, "static friction");
            if (Bits(owner.solverInputs.tetherStretchLimit) != 0x3cf5c28fU ||
                Bits(owner.solverInputs.distanceVelocityAttenuation) != 0x3e99999aU)
                throw new NotSupportedException(
                    "The recovered GetClothParameters solver constants differ from the pinned retail body.");
            if (Bits(owner.solverInputs.colliderStaticFriction) !=
                Bits(owner.solverInputs.colliderDynamicFriction))
                throw new NotSupportedException(
                    "Endminf requires the authored collider friction copied to both dynamic and static fields.");
            for (int particle = 0; particle < count; particle++)
            {
                int root = owner.vertexRootIndices[particle];
                int parent = owner.vertexParentIndices[particle];
                if (root < -1 || root >= count || parent < -1 || parent >= count)
                    throw new ArgumentException("Owner proxy parent/root topology is out of range.", nameof(owner));
                int packed = owner.distanceConstraintIndexArray[particle];
                int start = packed & 0x000fffff;
                int neighborCount = (int)((uint)packed >> 20);
                if (start + neighborCount > owner.distanceConstraintDataArray.Length)
                    throw new ArgumentException("Owner packed distance topology is out of range.", nameof(owner));
            }
            for (int baseline = 0; baseline < owner.baselineCount; baseline++)
            {
                int start = owner.baseLineStartDataIndices[baseline];
                int baselineCount = owner.baseLineDataCounts[baseline];
                if (start + baselineCount > owner.baseLineData.Length)
                    throw new ArgumentException("An owner baseline slice is outside the flattened topology.", nameof(owner));
            }
            for (int index = 0; index < owner.baseLineData.Length; index++)
                if (owner.baseLineData[index] >= count)
                    throw new ArgumentException("An angle baseline vertex is outside the owner proxy range.", nameof(owner));
            for (int index = 0; index < owner.centerFixedList.Length; index++)
                if (owner.centerFixedList[index] >= count)
                    throw new ArgumentException("A center-fixed vertex is outside the owner proxy range.", nameof(owner));
            for (int index = 0; index < owner.distanceConstraintDataArray.Length; index++)
            {
                if (owner.distanceConstraintDataArray[index] >= count)
                    throw new ArgumentException("A distance neighbor is outside the owner proxy range.", nameof(owner));
                RequireFinite(owner.distanceConstraintRestLengths[index], "distance rest length");
            }
        }

        private static void ValidateBaseFrame(BaseTransformFrame frame, int count)
        {
            if (frame == null)
                throw new ArgumentNullException(nameof(frame));
            RequireLength(frame.CurrentPositions, count, "current base positions");
            RequireLength(frame.CurrentRotations, count, "current base rotations");
            RequireLength(frame.PreviousPositions, count, "previous base positions");
            RequireLength(frame.PreviousRotations, count, "previous base rotations");
            for (int index = 0; index < count; index++)
            {
                RequireFinite(frame.CurrentPositions[index], "current base position");
                RequireFinite(frame.CurrentRotations[index], "current base rotation");
                RequireFinite(frame.PreviousPositions[index], "previous base position");
                RequireFinite(frame.PreviousRotations[index], "previous base rotation");
            }
        }

        private void ValidateCapsules(PreparedCapsuleFrame frame, int stepCount)
        {
            if (_owner.colliderCount == 0)
            {
                if (frame != null)
                    throw new NotSupportedException("A zero-collider owner must use the exact no-collider path.");
                return;
            }
            if (frame == null || frame.WorkBySubstep == null || frame.WorkBySubstep.Length != stepCount)
                throw new ArgumentException("Prepared capsule work must contain exactly one source-ordered set per substep.", nameof(frame));
            if (frame.NowPositions == null || frame.NowRotations == null ||
                frame.OldPositions == null || frame.OldRotations == null ||
                frame.NowPositions.Length != frame.NowRotations.Length ||
                frame.NowPositions.Length != frame.OldPositions.Length ||
                frame.NowPositions.Length != frame.OldRotations.Length)
                throw new ArgumentException("Prepared collider snapshot arrays are missing or inconsistent.", nameof(frame));
            for (int index = 0; index < _owner.colliderIndices.Length; index++)
                if (_owner.colliderIndices[index] < 0 || _owner.colliderIndices[index] >= frame.NowPositions.Length)
                    throw new ArgumentException("An owner collider index is outside the prepared snapshot arrays.", nameof(frame));
        }

        private void ValidateStepInput(
            CenterTeamStepInput input,
            PreparedCapsuleFrame capsules,
            int substep)
        {
            RequireFinite(input.GravityRatio, "gravity ratio");
            RequireFinite(input.ScaleRatio, "scale ratio");
            RequireFinite(input.VelocityWeight, "velocity weight");
            RequireFinite(input.CenterAngularVelocity, "center angular velocity");
            RequireFinite(input.GravityDot, "gravity dot");
            RequireFinite(input.ImpactForce, "impact force");
            RequireFinite(input.CenterOldWorldPosition, "center old world position");
            RequireFinite(input.CenterStepVector, "center step vector");
            RequireFinite(input.CenterStepRotation, "center step rotation");
            RequireFinite(input.CenterInertiaVector, "center inertia vector");
            RequireFinite(input.CenterInertiaRotation, "center inertia rotation");
            RequireFinite(input.CenterPosition, "center position");
            RequireFinite(input.CenterRotationAxis, "center rotation axis");
            RequireFinite(input.InitialScale, "initial scale");
            RequireFinite(input.NegativeScaleDirection, "negative scale direction");
            RequireFinite(input.NegativeScaleQuaternion, "negative scale quaternion");
            if (input.ScaleRatio <= 0f)
                throw new NotSupportedException("Only a positive recovered scale ratio is supported.");
            if (input.ForceMode != 0 && input.ForceMode != 1 && input.ForceMode != 2 &&
                input.ForceMode != 10 && input.ForceMode != 11)
                throw new NotSupportedException("The requested Simulation Start force mode is not recovered.");
            if (_owner.colliderCount > 0)
            {
                K.CapsuleColliderWork[] work = capsules.WorkBySubstep[substep];
                if (work == null || work.Length != _owner.colliderCount)
                    throw new ArgumentException("Prepared capsule work does not preserve owner source order.");
                RequireLength(input.ParticleRadii, _owner.proxyVertexCount, "particle radii");
                for (int index = 0; index < input.ParticleRadii.Length; index++)
                {
                    RequireFinite(input.ParticleRadii[index], "particle radius");
                    if (input.ParticleRadii[index] < 0f)
                        throw new ArgumentOutOfRangeException("particle radius");
                }
            }
            else if (input.ParticleRadii != null && input.ParticleRadii.Length != 0)
            {
                throw new NotSupportedException("The no-collider owner path does not consume particle radii.");
            }
        }

        private void Notify(Stage stage, int substep, int sourceIndex)
        {
            _observer?.OnStage(stage, substep, sourceIndex);
        }

        private static EndfieldSecondaryDynamicsData.Owner CloneOwner(
            EndfieldSecondaryDynamicsData.Owner source)
        {
            source.proxyTransformPaths = Clone(source.proxyTransformPaths);
            source.referenceIndices = Clone(source.referenceIndices);
            source.attributes = Clone(source.attributes);
            source.vertexDepths = Clone(source.vertexDepths);
            source.vertexRootIndices = Clone(source.vertexRootIndices);
            source.vertexParentIndices = Clone(source.vertexParentIndices);
            source.vertexLocalPositions = Clone(source.vertexLocalPositions);
            source.vertexLocalRotations = Clone(source.vertexLocalRotations);
            source.vertexBindPoseRotations = Clone(source.vertexBindPoseRotations);
            source.vertexToTransformRotations = Clone(source.vertexToTransformRotations);
            source.baseLineFlags = Clone(source.baseLineFlags);
            source.baseLineStartDataIndices = Clone(source.baseLineStartDataIndices);
            source.baseLineDataCounts = Clone(source.baseLineDataCounts);
            source.baseLineData = Clone(source.baseLineData);
            source.centerFixedList = Clone(source.centerFixedList);
            source.distanceConstraintIndexArray = Clone(source.distanceConstraintIndexArray);
            source.distanceConstraintDataArray = Clone(source.distanceConstraintDataArray);
            source.distanceConstraintRestLengths = Clone(source.distanceConstraintRestLengths);
            source.colliderIndices = Clone(source.colliderIndices);
            EndfieldSecondaryDynamicsData.SolverInputs solver = source.solverInputs;
            solver.dampingCurveData = Clone(solver.dampingCurveData);
            solver.radiusCurveData = Clone(solver.radiusCurveData);
            solver.distanceRestorationStiffness = Clone(solver.distanceRestorationStiffness);
            solver.angleRestorationStiffness = Clone(solver.angleRestorationStiffness);
            solver.angleLimit = Clone(solver.angleLimit);
            source.solverInputs = solver;
            return source;
        }

        private static TElement[] Clone<TElement>(TElement[] value) =>
            value == null ? null : (TElement[])value.Clone();

        private static void RequireLength(Array value, int expected, string name)
        {
            if (value == null || value.Length != expected)
                throw new ArgumentException(name + " must contain exactly " + expected + " entries.");
        }

        private static void RequireCurve(float[] values, string name)
        {
            RequireLength(values, 16, name + " curve");
            for (int index = 0; index < values.Length; index++)
                RequireFinite(values[index], name + " curve");
        }

        private static void RequireFinite(float value, string name)
        {
            if (float.IsNaN(value) || float.IsInfinity(value))
                throw new ArgumentOutOfRangeException(name, "A finite binary32 value is required.");
        }

        private static void RequireFinite(K.Float3 value, string name)
        {
            RequireFinite(value.x, name);
            RequireFinite(value.y, name);
            RequireFinite(value.z, name);
        }

        private static void RequireFinite(K.Float4 value, string name)
        {
            RequireFinite(value.x, name);
            RequireFinite(value.y, name);
            RequireFinite(value.z, name);
            RequireFinite(value.w, name);
        }

        private static void RequireFinite(K.Double3 value, string name)
        {
            if (double.IsNaN(value.x) || double.IsInfinity(value.x) ||
                double.IsNaN(value.y) || double.IsInfinity(value.y) ||
                double.IsNaN(value.z) || double.IsInfinity(value.z))
                throw new ArgumentOutOfRangeException(name, "A finite binary64 vector is required.");
        }

        private static uint Bits(float value) =>
            BitConverter.ToUInt32(BitConverter.GetBytes(value), 0);

        private static K.Float3 ToFloat3(UnityEngine.Vector3 value) =>
            new K.Float3(value.x, value.y, value.z);

        private static K.Float4 ToFloat4(UnityEngine.Quaternion value) =>
            new K.Float4(value.x, value.y, value.z, value.w);

        private static K.Double3 ToDouble3(K.Float3 value) =>
            new K.Double3(value.x, value.y, value.z);

        private static K.Float3[] ToFloat3Array(UnityEngine.Vector3[] values)
        {
            var result = new K.Float3[values.Length];
            for (int index = 0; index < values.Length; index++)
                result[index] = ToFloat3(values[index]);
            return result;
        }

        private static K.Float4[] ToFloat4Array(UnityEngine.Quaternion[] values)
        {
            var result = new K.Float4[values.Length];
            for (int index = 0; index < values.Length; index++)
                result[index] = ToFloat4(values[index]);
            return result;
        }

        private static K.Float3[] ToFloat3Array(K.Double3[] values)
        {
            var result = new K.Float3[values.Length];
            for (int index = 0; index < values.Length; index++)
                result[index] = new K.Float3(
                    (float)values[index].x, (float)values[index].y, (float)values[index].z);
            return result;
        }
    }
}
