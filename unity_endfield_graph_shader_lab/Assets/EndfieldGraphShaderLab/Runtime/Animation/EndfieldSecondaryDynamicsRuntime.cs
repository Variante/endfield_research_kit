using System;
using System.Collections.Generic;
using System.Linq;
using System.Security.Cryptography;
using UnityEngine;
using UnityEngine.LowLevel;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Owns the recovered actor-level scheduling and binding boundary for the
    /// original secondary-dynamics solver. Numeric kernels remain gated until
    /// their source equations are translated and golden-vector verified.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class EndfieldSecondaryDynamicsRuntime : MonoBehaviour,
        IEndfieldOverviewParameterConsumer,
        IEndfieldOverviewParameterResetConsumer
    {
        private struct AfterEarlyUpdate { }
        private struct AfterScriptRunBehaviourFixedUpdate { }
        private struct AfterScriptRunDelayedTasks { }
        private struct BeforeScriptRunBehaviourLateUpdate { }
        private struct AfterScriptRunBehaviourLateUpdate { }
        private struct AfterScriptRunDelayedDynamicFrameRate { }
        private struct AfterFinishFrameRendering { }

        private static readonly List<EndfieldSecondaryDynamicsRuntime> Active =
            new List<EndfieldSecondaryDynamicsRuntime>();
        private static bool playerLoopInstalled;

        public EndfieldSecondaryDynamicsData data;

        [Tooltip("Diagnostic only. The recovered scheduling/writeback route is " +
                 "certified, but visible hair/cape shape equivalence is not. " +
                 "Keep disabled in reproduction output until a retail-shape gate passes.")]
        public bool enableUnverifiedSolverWriteback;

        public bool BindingValid { get; private set; }
        public string BindingFailure { get; private set; } = "not validated";
        public float TargetWeight { get; private set; }
        public float CurrentWeight { get; private set; }
        public bool SolverWritebackEnabled => BindingValid &&
            transformPublicationAdapter != null && frameCoordinator != null;
        public bool SolverCoordinatorEnabled => frameCoordinator != null;
        public int[] LastSimulationSubsteps { get; private set; } = Array.Empty<int>();
        public EndfieldSecondaryDynamicsKernels.Double3[][] PublicationPositions =>
            frameCoordinator == null ? null : frameCoordinator.PublicationPositions;
        public EndfieldSecondaryDynamicsKernels.Float4[][] PublicationRotations =>
            frameCoordinator == null ? null : frameCoordinator.PublicationRotations;
        public EndfieldSecondaryDynamicsTransformPublication.FinalValue[]
            LatestTransformPublication { get; private set; } =
                Array.Empty<EndfieldSecondaryDynamicsTransformPublication.FinalValue>();
        public bool TransformSnapshotReadEnabled => transformSnapshotAdapter != null;
        public EndfieldSecondaryDynamicsTransformSnapshotAdapter.SnapshotFrame
            LatestTransformSnapshot { get; private set; }
        public int UpdateLocation => updateLocation;
        public int PendingCrossFrameGeneration => crossFramePublication == null
            ? -1 : crossFramePublication.PendingGeneration;
        public int LastPublishedCrossFrameGeneration => crossFramePublication == null
            ? -1 : crossFramePublication.LastPublishedGeneration;

        [SerializeField, Range(0, 1)]
        private int updateLocation;
        private int fixedUpdateCount;
        private EndfieldSecondaryDynamicsTransformSnapshotAdapter transformSnapshotAdapter;
        private EndfieldSecondaryDynamicsFrameCoordinator frameCoordinator;
        private EndfieldSecondaryDynamicsTransformPublicationAdapter transformPublicationAdapter;
        private EndfieldSecondaryDynamicsCrossFramePublication crossFramePublication;

        private const float EnableRate = 8.0f;
        private const float DisableRate = 6.0f;
        private const float WeightEpsilon = 0.001f;

        private void OnEnable()
        {
            if (!enableUnverifiedSolverWriteback)
            {
                BindingValid = false;
                BindingFailure =
                    "solver writeback remains diagnostic-only: retail hair/cape " +
                    "shape equivalence has not passed";
                return;
            }

            BindingValid = ValidateBindings(out string failure);
            BindingFailure = failure;
            if (!BindingValid)
            {
                Debug.LogError(
                    "Recovered secondary dynamics failed closed on " + name + ": " + failure,
                    this);
                return;
            }

            try
            {
                transformSnapshotAdapter =
                    new EndfieldSecondaryDynamicsTransformSnapshotAdapter(transform, data);
                LatestTransformSnapshot = transformSnapshotAdapter.Capture();
                frameCoordinator = new EndfieldSecondaryDynamicsFrameCoordinator(
                    data, LatestTransformSnapshot.Owners);
                transformPublicationAdapter =
                    new EndfieldSecondaryDynamicsTransformPublicationAdapter(transform, data);
                crossFramePublication =
                    new EndfieldSecondaryDynamicsCrossFramePublication();
                // AddTransform initializes both the current and last world/local
                // arrays from the same live transform state. The coordinator's
                // initial publication arrays are built from that exact snapshot.
                crossFramePublication.SeedFromAddTransform(
                    frameCoordinator.PublicationPositions,
                    frameCoordinator.PublicationRotations);
            }
            catch (Exception exception)
            {
                BindingValid = false;
                BindingFailure = "transform snapshot adapter failed: " + exception.Message;
                transformSnapshotAdapter = null;
                frameCoordinator = null;
                transformPublicationAdapter = null;
                crossFramePublication = null;
                LatestTransformSnapshot = null;
                Debug.LogError(
                    "Recovered secondary dynamics failed closed on " + name + ": " +
                    BindingFailure, this);
                return;
            }

            if (!Active.Contains(this))
                Active.Add(this);
            InstallPlayerLoop();
        }

        private void OnDisable()
        {
            Active.Remove(this);
            TargetWeight = 0.0f;
            CurrentWeight = 0.0f;
            transformSnapshotAdapter = null;
            frameCoordinator = null;
            transformPublicationAdapter = null;
            crossFramePublication = null;
            LatestTransformSnapshot = null;
            LastSimulationSubsteps = Array.Empty<int>();
            LatestTransformPublication =
                Array.Empty<EndfieldSecondaryDynamicsTransformPublication.FinalValue>();
        }

        public void ApplyOverviewParameters(
            float weaponHide,
            float magicaClothWeight,
            float staticWeaponHide)
        {
            // The original consumer treats every non-zero authored overview
            // value as enabled; 0.01 is a trigger, not the final blend.
            TargetWeight = Mathf.Abs(magicaClothWeight) > 0.0f ? 1.0f : 0.0f;
        }

        public void RestoreOverviewParameters()
        {
            TargetWeight = 0.0f;
        }

        private void RunWholeClothPipelineBoundary()
        {
            float rate = TargetWeight > CurrentWeight ? EnableRate : DisableRate;
            float next = Mathf.MoveTowards(CurrentWeight, TargetWeight, rate * Time.deltaTime);
            if (Mathf.Abs(next - CurrentWeight) >= WeightEpsilon ||
                Mathf.Approximately(next, TargetWeight))
                CurrentWeight = next;

            try
            {
                // Observed cross-frame order is: finish prior master,
                // ReadTransform into current arrays, publish distinct last arrays,
                // then schedule current simulation. The one-callback retained
                // result models the observed histories. The public native
                // CopyDoubleBuffer method has no direct caller in the closed
                // target pipeline, so exact current-to-last transport ownership
                // remains unresolved. Source-recovered Reset seeding happens in
                // the owner solver before the first substep.
                LatestTransformSnapshot = transformSnapshotAdapter.Capture();
                EndfieldSecondaryDynamicsCrossFramePublication.Frame completed =
                    crossFramePublication.TakeCompletedForPublication();
                LatestTransformPublication = transformPublicationAdapter.Publish(
                    completed.Positions,
                    completed.Rotations,
                    CurrentWeight,
                    true);
                LastSimulationSubsteps = frameCoordinator.AdvanceFrame(
                    new EndfieldSecondaryDynamicsFrameCoordinator.FrameInput
                    {
                        Owners = LatestTransformSnapshot.Owners,
                        Timing = new EndfieldSecondaryDynamicsFrameCoordinator.FrameTiming(
                            true,
                            false,
                            false,
                            false,
                            Time.deltaTime,
                            Time.fixedDeltaTime,
                            Time.unscaledDeltaTime),
                        ActorRootStationary = LatestTransformSnapshot.ActorRootStationary,
                        ActorScale = LatestTransformSnapshot.ActorScale,
                        NegativeScale = LatestTransformSnapshot.NegativeScale,
                        WindZoneCount = 0,
                        Session = new EndfieldSecondaryDynamicsFrameCoordinator.SessionCertification(
                            data.sessionCertified,
                            data.sessionUseRelativeTransform,
                            data.sessionUseCrossFrameJob,
                            data.sessionUseAnimatorTransform,
                            EndfieldSecondaryDynamicsFrameCoordinator.WritebackRoute.TransformAccess),
                        PreviousColliderSamples =
                            LatestTransformSnapshot.PreviousColliderSamples,
                        CurrentColliderSamples =
                            LatestTransformSnapshot.CurrentColliderSamples,
                    });
                crossFramePublication.StageCurrentSimulation(
                    frameCoordinator.PublicationPositions,
                    frameCoordinator.PublicationRotations);
            }
            catch (Exception exception)
            {
                BindingValid = false;
                BindingFailure = "secondary-dynamics frame failed: " + exception.Message;
                Active.Remove(this);
                frameCoordinator = null;
                transformPublicationAdapter = null;
                crossFramePublication = null;
                Debug.LogError(
                    "Recovered secondary dynamics failed closed on " + name + ": " +
                    BindingFailure, this);
            }

            // Intentionally no transform writes here. The original executes
            // the complete read/simulate/write ClothUpdate pipeline on exactly
            // one selected side of ScriptRunBehaviourLateUpdate. It does not
            // split Start and End across the two callbacks.
        }

        private void OnAfterEarlyUpdate()
        {
            // RestoreTransformJob consumes the immutable AddTransform-time
            // local buffers for every source entry carrying flag 0x08.
            if (BindingValid && transformPublicationAdapter != null)
                transformPublicationAdapter.RestoreInitialLocals();
        }

        private void OnAfterFixedUpdate()
        {
            // The original callback increments only this counter; it never
            // invokes ClothUpdate from FixedUpdate.
            fixedUpdateCount++;
        }

        private void OnAfterUpdate()
        {
            // Reserved for animator cross-frame completion and monitoring.
        }

        private void OnBeforeLateUpdate()
        {
            if (updateLocation == 1)
                RunWholeClothPipelineBoundary();
        }

        private void OnAfterLateUpdate()
        {
            if (updateLocation == 0)
                RunWholeClothPipelineBoundary();
        }

        private void OnPreRenderingUpdate()
        {
            // Reserved for render-mesh publication.
        }

        private void OnAfterRendering()
        {
            fixedUpdateCount = 0;
        }

        private bool ValidateBindings(out string failure)
        {
            if (data == null || !data.sourceRecovered)
            {
                failure = "source-recovered data asset is missing";
                return false;
            }
            if (!string.Equals(data.actorKey, "endminf", StringComparison.Ordinal))
            {
                failure = "actor key differs from endminf";
                return false;
            }
            if (data.solverInputs == null || data.payloadDecode == null ||
                data.ownerRecovery == null || data.curveSamples == null ||
                data.solverScalarPacking == null || data.centerUpdate == null ||
                data.duplicateWrite == null || data.transformRead == null ||
                data.simulationStepTeamUpdate == null || data.sessionCertification == null ||
                string.IsNullOrEmpty(data.solverInputsSha256) ||
                string.IsNullOrEmpty(data.payloadDecodeSha256) ||
                string.IsNullOrEmpty(data.ownerRecoverySha256) ||
                string.IsNullOrEmpty(data.curveSamplesSha256) ||
                string.IsNullOrEmpty(data.solverScalarPackingSha256) ||
                string.IsNullOrEmpty(data.centerUpdateSha256) ||
                string.IsNullOrEmpty(data.duplicateWriteSha256) ||
                string.IsNullOrEmpty(data.transformReadSha256) ||
                string.IsNullOrEmpty(data.simulationStepTeamUpdateSha256) ||
                string.IsNullOrEmpty(data.sessionCertificationSha256))
            {
                failure = "source contract references or hashes are missing";
                return false;
            }
            if (!HashMatches(data.solverInputs, data.solverInputsSha256) ||
                !HashMatches(data.payloadDecode, data.payloadDecodeSha256) ||
                !HashMatches(data.ownerRecovery, data.ownerRecoverySha256) ||
                !HashMatches(data.curveSamples, data.curveSamplesSha256) ||
                !HashMatches(data.solverScalarPacking, data.solverScalarPackingSha256) ||
                !HashMatches(data.centerUpdate, data.centerUpdateSha256) ||
                !HashMatches(data.duplicateWrite, data.duplicateWriteSha256) ||
                !HashMatches(data.transformRead, data.transformReadSha256) ||
                !HashMatches(data.simulationStepTeamUpdate,
                    data.simulationStepTeamUpdateSha256) ||
                !HashMatches(data.sessionCertification,
                    data.sessionCertificationSha256))
            {
                failure = "source contract hash differs from generated binding data";
                return false;
            }
            if (!data.sessionCertified || data.sessionUseRelativeTransform ||
                !data.sessionUseCrossFrameJob || data.sessionUseAnimatorTransform ||
                !string.Equals(data.sessionWritebackRoute, "TransformAccess",
                    StringComparison.Ordinal))
            {
                failure = "live target session does not certify the supported transform route";
                return false;
            }
            if (data.owners == null || data.owners.Length != 4)
            {
                failure = "expected exactly four recovered cloth owners";
                return false;
            }
            if (data.colliders == null || data.colliders.Length != 10)
            {
                failure = "expected exactly ten recovered capsule colliders";
                return false;
            }
            for (int colliderIndex = 0; colliderIndex < data.colliders.Length; colliderIndex++)
            {
                EndfieldSecondaryDynamicsData.CapsuleCollider collider =
                    data.colliders[colliderIndex];
                if (string.IsNullOrEmpty(collider.transformPath) ||
                    transform.Find(collider.transformPath) == null ||
                    collider.direction < 0 || collider.direction > 2)
                {
                    failure = "capsule collider binding differs at index " + colliderIndex;
                    return false;
                }
            }

            int bindingCount = 0;
            var unique = new HashSet<string>(StringComparer.Ordinal);
            foreach (EndfieldSecondaryDynamicsData.Owner owner in data.owners)
            {
                EndfieldSecondaryDynamicsData.SolverInputs inputs = owner.solverInputs;
                if (!inputs.authoredScalarsRecovered ||
                    !inputs.compiledCurveSamplesRecovered ||
                    !HasCurve(inputs.dampingCurveData) ||
                    !HasCurve(inputs.radiusCurveData) ||
                    !HasCurve(inputs.distanceRestorationStiffness) ||
                    !HasCurve(inputs.angleRestorationStiffness) ||
                    !HasCurve(inputs.angleLimit))
                {
                    failure = "compiled curve samples differ for " + owner.ownerPath;
                    return false;
                }
                if (FloatBits(inputs.tetherStretchLimit) != 0x3cf5c28fU ||
                    FloatBits(inputs.distanceVelocityAttenuation) != 0x3e99999aU ||
                    !Finite(inputs.worldInertia) ||
                    !Finite(inputs.movementInertiaSmoothing) ||
                    !Finite(inputs.localInertia) ||
                    !Finite(inputs.localMovementSpeedLimit) ||
                    !Finite(inputs.localRotationSpeedLimit) ||
                    inputs.localInertia < 0f || inputs.localInertia > 1f ||
                    !Finite(inputs.colliderDynamicFriction) ||
                    FloatBits(inputs.colliderStaticFriction) !=
                    FloatBits(inputs.colliderDynamicFriction))
                {
                    failure = "retail GetClothParameters scalar packing differs for " +
                        owner.ownerPath;
                    return false;
                }
                if (transform.Find(owner.ownerPath) == null ||
                    transform.Find(owner.centerTransformPath) == null)
                {
                    failure = "owner/center path does not resolve: " + owner.ownerPath;
                    return false;
                }
                if (owner.proxyTransformPaths == null ||
                    owner.proxyTransformPaths.Length != owner.proxyVertexCount)
                {
                    failure = "proxy transform count differs for " + owner.ownerPath;
                    return false;
                }
                if (owner.colliderIndices == null ||
                    owner.colliderIndices.Length != owner.colliderCount ||
                    owner.colliderIndices.Any(index => index < 0 || index >= data.colliders.Length))
                {
                    failure = "collider index list differs for " + owner.ownerPath;
                    return false;
                }
                foreach (string path in owner.proxyTransformPaths)
                {
                    if (string.IsNullOrEmpty(path) || transform.Find(path) == null)
                    {
                        failure = "proxy transform path does not resolve: " + path;
                        return false;
                    }
                    bindingCount++;
                    unique.Add(path);
                }
            }

            if (bindingCount != data.expectedBindingCount ||
                unique.Count != data.expectedUniqueBindingCount ||
                bindingCount - unique.Count != data.expectedOverlappingBindingCount)
            {
                failure = "binding/overlap cardinality differs";
                return false;
            }
            failure = "";
            return true;
        }

        private static bool HasCurve(float[] values) =>
            values != null && values.Length == 16 &&
            values.All(value => !float.IsNaN(value) && !float.IsInfinity(value));

        private static bool Finite(float value) =>
            !float.IsNaN(value) && !float.IsInfinity(value);

        private static uint FloatBits(float value) =>
            BitConverter.ToUInt32(BitConverter.GetBytes(value), 0);

        private static void InstallPlayerLoop()
        {
            PlayerLoopSystem root = PlayerLoop.GetCurrentPlayerLoop();
            if (playerLoopInstalled && CountRecoveredPhases(root) == 7)
                return;
            if (CountRecoveredPhases(root) == 7)
            {
                playerLoopInstalled = true;
                return;
            }
            if (!InsertRecoveredPhases(ref root))
                throw new InvalidOperationException(
                    "One or more recovered secondary-dynamics PlayerLoop anchors were not found.");
            PlayerLoop.SetPlayerLoop(root);
            playerLoopInstalled = true;
        }

        private static int CountRecoveredPhases(PlayerLoopSystem system)
        {
            int count = IsRecoveredPhase(system.type) ? 1 : 0;
            if (system.subSystemList == null)
                return count;
            foreach (PlayerLoopSystem child in system.subSystemList)
                count += CountRecoveredPhases(child);
            return count;
        }

        private static bool IsRecoveredPhase(Type type)
        {
            return type == typeof(AfterEarlyUpdate) ||
                type == typeof(AfterScriptRunBehaviourFixedUpdate) ||
                type == typeof(AfterScriptRunDelayedTasks) ||
                type == typeof(BeforeScriptRunBehaviourLateUpdate) ||
                type == typeof(AfterScriptRunBehaviourLateUpdate) ||
                type == typeof(AfterScriptRunDelayedDynamicFrameRate) ||
                type == typeof(AfterFinishFrameRendering);
        }

        private static bool HashMatches(TextAsset asset, string expected)
        {
            using (SHA256 sha = SHA256.Create())
            {
                string actual = string.Concat(
                    sha.ComputeHash(asset.bytes).Select(value => value.ToString("x2")));
                return string.Equals(actual, expected, StringComparison.OrdinalIgnoreCase);
            }
        }

        private static bool InsertRecoveredPhases(ref PlayerLoopSystem system)
        {
            bool early = AppendToCategory(
                ref system,
                typeof(UnityEngine.PlayerLoop.EarlyUpdate),
                typeof(AfterEarlyUpdate),
                RunAfterEarlyUpdate);
            bool fixedUpdate = InsertRelativeTo(
                ref system,
                typeof(UnityEngine.PlayerLoop.FixedUpdate.ScriptRunBehaviourFixedUpdate),
                false,
                typeof(AfterScriptRunBehaviourFixedUpdate),
                RunAfterFixedUpdate);
            bool update = InsertRelativeTo(
                ref system,
                typeof(UnityEngine.PlayerLoop.Update.ScriptRunDelayedTasks),
                false,
                typeof(AfterScriptRunDelayedTasks),
                RunAfterUpdate);
            bool beforeLate = InsertRelativeTo(
                ref system,
                typeof(UnityEngine.PlayerLoop.PreLateUpdate.ScriptRunBehaviourLateUpdate),
                true,
                typeof(BeforeScriptRunBehaviourLateUpdate),
                RunBeforeLateUpdate);
            bool afterLate = InsertRelativeTo(
                ref system,
                typeof(UnityEngine.PlayerLoop.PreLateUpdate.ScriptRunBehaviourLateUpdate),
                false,
                typeof(AfterScriptRunBehaviourLateUpdate),
                RunAfterLateUpdate);
            bool preRendering = InsertRelativeTo(
                ref system,
                typeof(UnityEngine.PlayerLoop.PostLateUpdate.ScriptRunDelayedDynamicFrameRate),
                false,
                typeof(AfterScriptRunDelayedDynamicFrameRate),
                RunPreRenderingUpdate);
            bool afterRendering = InsertRelativeTo(
                ref system,
                typeof(UnityEngine.PlayerLoop.PostLateUpdate.FinishFrameRendering),
                false,
                typeof(AfterFinishFrameRendering),
                RunAfterRendering);
            return early && fixedUpdate && update && beforeLate && afterLate &&
                preRendering && afterRendering;
        }

        private static bool AppendToCategory(
            ref PlayerLoopSystem system,
            Type category,
            Type phase,
            PlayerLoopSystem.UpdateFunction update)
        {
            if (system.type == category)
            {
                var list = (system.subSystemList ?? Array.Empty<PlayerLoopSystem>()).ToList();
                list.Add(new PlayerLoopSystem { type = phase, updateDelegate = update });
                system.subSystemList = list.ToArray();
                return true;
            }
            if (system.subSystemList == null)
                return false;
            for (int index = 0; index < system.subSystemList.Length; index++)
            {
                PlayerLoopSystem child = system.subSystemList[index];
                if (AppendToCategory(ref child, category, phase, update))
                {
                    system.subSystemList[index] = child;
                    return true;
                }
            }
            return false;
        }

        private static bool InsertRelativeTo(
            ref PlayerLoopSystem system,
            Type anchor,
            bool before,
            Type phase,
            PlayerLoopSystem.UpdateFunction update)
        {
            if (system.subSystemList == null)
                return false;
            for (int index = 0; index < system.subSystemList.Length; index++)
            {
                PlayerLoopSystem child = system.subSystemList[index];
                if (child.type == anchor)
                {
                    var list = system.subSystemList.ToList();
                    list.Insert(before ? index : index + 1, new PlayerLoopSystem
                    {
                        type = phase,
                        updateDelegate = update,
                    });
                    system.subSystemList = list.ToArray();
                    return true;
                }
                if (InsertRelativeTo(ref child, anchor, before, phase, update))
                {
                    system.subSystemList[index] = child;
                    return true;
                }
            }
            return false;
        }

        private static void RunAfterEarlyUpdate() => RunActive(runtime => runtime.OnAfterEarlyUpdate());
        private static void RunAfterFixedUpdate() => RunActive(runtime => runtime.OnAfterFixedUpdate());
        private static void RunAfterUpdate() => RunActive(runtime => runtime.OnAfterUpdate());
        private static void RunBeforeLateUpdate() => RunActive(runtime => runtime.OnBeforeLateUpdate());
        private static void RunAfterLateUpdate() => RunActive(runtime => runtime.OnAfterLateUpdate());
        private static void RunPreRenderingUpdate() => RunActive(runtime => runtime.OnPreRenderingUpdate());
        private static void RunAfterRendering() => RunActive(runtime => runtime.OnAfterRendering());

        private static void RunActive(Action<EndfieldSecondaryDynamicsRuntime> action)
        {
            for (int index = Active.Count - 1; index >= 0; index--)
            {
                EndfieldSecondaryDynamicsRuntime runtime = Active[index];
                if (runtime == null)
                    Active.RemoveAt(index);
                else if (runtime.isActiveAndEnabled && runtime.BindingValid)
                    action(runtime);
            }
        }

    }
}
