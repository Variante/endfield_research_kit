using System;
using System.Collections.Generic;
using UnityEngine;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// A deliberately non-solver probe for the recovered BeyondDynamicBone
    /// topology.  It only snapshots transforms and checks the ordering of a
    /// read/audit-marker/identity-writeback-shaped lifecycle.  It does not integrate a
    /// spring, constraint, collision, Burst, or PlayerLoop implementation and
    /// must never be used as evidence that retail secondary dynamics run.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class EndfieldSecondaryDynamicsLifecycleProbe : MonoBehaviour
    {
        /// <summary>
        /// This probe is an audit harness, not a retail solver.  Keep this
        /// constant false so callers cannot accidentally promote its report to
        /// secondary_dynamics_verified evidence.
        /// </summary>
        public const bool IsRetailSolver = false;

        /// <summary>
        /// The serialized CharInfo weight used by the current Endminf
        /// contract. It is an observed input value, not a solver threshold.
        /// </summary>
        public const float EndminfSerializedOverviewWeight = 0.01f;

        /// <summary>
        /// A transform that belongs to an owner topology entry.  Nodes are
        /// supplied by the editor probe after resolving the serialized paths
        /// against a prefab; the runtime component never discovers or invents
        /// a topology on its own.
        /// </summary>
        public sealed class TopologyNode
        {
            public string path;
            public string role;
            public string owner;
            public string componentType;
            public Transform transform;
        }

        /// <summary>
        /// A compact immutable copy of a Transform's local state.  Both the
        /// previous and current arrays are allocated even though this probe
        /// intentionally performs no simulation between them.
        /// </summary>
        public struct TransformState
        {
            public Vector3 position;
            public Quaternion rotation;
            public Vector3 scale;

            public TransformState(Transform source)
            {
                position = source.localPosition;
                rotation = source.localRotation;
                scale = source.localScale;
            }

            public void WriteTo(Transform destination)
            {
                destination.localPosition = position;
                destination.localRotation = rotation;
                destination.localScale = scale;
            }

            public bool ApproximatelyEquals(TransformState other, float tolerance)
            {
                return Vector3.SqrMagnitude(position - other.position) <= tolerance * tolerance &&
                       Quaternion.Angle(rotation, other.rotation) <= tolerance &&
                       Vector3.SqrMagnitude(scale - other.scale) <= tolerance * tolerance;
            }
        }

        [Serializable]
        public sealed class LifecycleAudit
        {
            public string scenario = "";
            public bool configured;
            public bool movement_disabled;
            public bool gate_open;
            public bool state_allocated;
            // These two fields are reserved for a real retail/runtime hook.
            // The probe below never invokes that hook, so they must stay
            // false.  Keeping them separate from the audit markers prevents
            // an identity no-op from being mistaken for native callback or
            // transform writeback evidence.
            public bool callback_invoked;
            public bool writeback_invoked;
            public bool audit_callback_marker_invoked;
            public bool identity_writeback_invoked;
            public bool identity_writeback_skipped;
            public bool ordering_verified;
            public bool transforms_unchanged;
            public bool passed;
            public int tracked_transform_count;
            public int root_count;
            public int collider_count;
            public string gate_reason = "";
            public string[] events = Array.Empty<string>();
            public string limitation =
                "non-solver lifecycle audit only; no retail secondary dynamics " +
                "solver, PlayerLoop registration, or secondary_dynamics_verified " +
                "claim is produced";
        }

        private readonly List<TopologyNode> nodes = new List<TopologyNode>();
        private TransformState[] previousState = Array.Empty<TransformState>();
        private TransformState[] currentState = Array.Empty<TransformState>();

        private bool configured;
        private bool componentEnabled;
        private bool ownerActive;
        private bool movementEnabled;
        private float globalWeight;
        private float simulateWeight;
        private float blendWeight;
        private bool sourceEnabled = true;

        /// <summary>Read-only access for editor reports and focused tests.</summary>
        public IReadOnlyList<TopologyNode> Nodes => nodes;

        public int PreviousStateCount => previousState.Length;
        public int CurrentStateCount => currentState.Length;
        public bool SecondaryDynamicsVerified => false;

        /// <summary>
        /// Copies the resolved topology and allocates previous/current state.
        /// Null transforms are rejected instead of being silently omitted.
        /// </summary>
        public void Configure(IReadOnlyList<TopologyNode> resolvedNodes)
        {
            if (resolvedNodes == null)
                throw new ArgumentNullException(nameof(resolvedNodes));
            if (resolvedNodes.Count == 0)
                throw new ArgumentException("Secondary dynamics topology is empty.", nameof(resolvedNodes));

            nodes.Clear();
            for (int index = 0; index < resolvedNodes.Count; index++)
            {
                TopologyNode node = resolvedNodes[index];
                if (node == null || node.transform == null)
                {
                    string path = node == null ? "<null>" : node.path;
                    throw new InvalidOperationException(
                        "Secondary dynamics topology contains an unresolved transform: " + path);
                }
                nodes.Add(node);
            }

            previousState = new TransformState[nodes.Count];
            currentState = new TransformState[nodes.Count];
            configured = true;
            componentEnabled = true;
            ownerActive = true;
            movementEnabled = false;
            globalWeight = EndminfSerializedOverviewWeight;
            simulateWeight = 1.0f;
            blendWeight = 1.0f;
            sourceEnabled = true;
        }

        /// <summary>
        /// Mirrors the serialized component/owner/weight gates used for the
        /// audit.  It deliberately does not call any dynamic solver API.
        /// </summary>
        public void SetLifecycleGates(
            bool componentIsEnabled,
            bool ownerIsActive,
            bool movementIsEnabled,
            float serializedGlobalWeight,
            float serializedSimulateWeight,
            float serializedBlendWeight,
            bool serializedOwnerEnabled = true)
        {
            componentEnabled = componentIsEnabled;
            ownerActive = ownerIsActive;
            movementEnabled = movementIsEnabled;
            globalWeight = serializedGlobalWeight;
            simulateWeight = serializedSimulateWeight;
            blendWeight = serializedBlendWeight;
            sourceEnabled = serializedOwnerEnabled;
        }

        /// <summary>
        /// Runs one deterministic lifecycle audit.  The audit marker is a
        /// no-op by design: its purpose is to prove ordering and frozen
        /// identity writeback, not
        /// to approximate the missing retail dynamics solver.
        /// </summary>
        public LifecycleAudit RunLifecycleAudit(string scenario)
        {
            if (!configured)
                throw new InvalidOperationException("Configure the topology before auditing lifecycle.");

            var audit = new LifecycleAudit
            {
                scenario = string.IsNullOrEmpty(scenario) ? "unnamed" : scenario,
                configured = configured,
                movement_disabled = !movementEnabled,
                tracked_transform_count = nodes.Count,
                root_count = CountRole("root"),
                collider_count = CountRole("collider"),
                state_allocated = previousState.Length == nodes.Count &&
                                  currentState.Length == nodes.Count
            };
            var events = new List<string>();

            // The read phase is always observable.  This makes a gated frame
            // distinguishable from a malformed/never-configured probe.
            ReadState(events);
            audit.gate_open = EvaluateGate(out audit.gate_reason);
            if (!audit.gate_open)
            {
                events.Add("gated");
                audit.events = events.ToArray();
                audit.callback_invoked = false;
                audit.writeback_invoked = false;
                audit.audit_callback_marker_invoked = false;
                audit.identity_writeback_invoked = false;
                audit.ordering_verified = IsReadThenGate(events);
                audit.transforms_unchanged = CompareCurrentStateToTransforms();
                audit.passed = audit.state_allocated && audit.ordering_verified &&
                               audit.transforms_unchanged;
                return audit;
            }

            // This marker is intentionally not a callback.  A future
            // implementation may supply a real solver separately; this class
            // must remain a non-solver audit and therefore never claims that
            // a native callback ran or that native writeback occurred.
            events.Add("audit_callback_marker");
            audit.audit_callback_marker_invoked = true;

            audit.identity_writeback_invoked = WriteBack(events);
            audit.identity_writeback_skipped = !audit.identity_writeback_invoked;
            audit.events = events.ToArray();
            audit.ordering_verified = IsReadAuditMarkerIdentityWriteback(events);
            audit.transforms_unchanged = CompareCurrentStateToTransforms();
            audit.passed = audit.state_allocated && audit.movement_disabled &&
                           audit.gate_open && audit.audit_callback_marker_invoked &&
                           audit.identity_writeback_invoked && audit.ordering_verified &&
                           audit.transforms_unchanged;
            return audit;
        }

        private void ReadState(List<string> events)
        {
            // Previous/current are intentionally separate arrays.  This is a
            // state-topology audit only; no integration occurs between reads.
            for (int index = 0; index < nodes.Count; index++)
            {
                previousState[index] = currentState[index];
                currentState[index] = new TransformState(nodes[index].transform);
                if (index == 0)
                    events.Add("read");
            }
        }

        private bool WriteBack(List<string> events)
        {
            // Movement must be disabled for this probe.  Writing the captured
            // current pose back is therefore an identity operation, but still
            // verifies that identity writeback occurs after the audit marker.
            if (movementEnabled)
            {
                events.Add("identity_writeback_skipped_movement_enabled");
                return false;
            }
            for (int index = 0; index < nodes.Count; index++)
                currentState[index].WriteTo(nodes[index].transform);
            events.Add("identity_writeback");
            return true;
        }

        private bool EvaluateGate(out string reason)
        {
            if (!componentEnabled)
            {
                reason = "component_disabled";
                return false;
            }
            if (!ownerActive)
            {
                reason = "owner_inactive";
                return false;
            }
            if (!sourceEnabled)
            {
                reason = "serialized_owner_disabled";
                return false;
            }
            if (!IsFinite(globalWeight) || !IsFinite(simulateWeight) ||
                !IsFinite(blendWeight))
            {
                reason = "non_finite_weight";
                return false;
            }
            if (globalWeight <= 0.0f)
            {
                reason = "global_weight_zero";
                return false;
            }
            if (simulateWeight <= 0.0f)
            {
                reason = "simulate_weight_zero";
                return false;
            }
            if (blendWeight <= 0.0f)
            {
                reason = "blend_weight_zero";
                return false;
            }
            reason = "open";
            return true;
        }

        private static bool IsFinite(float value)
        {
            return !float.IsNaN(value) && !float.IsInfinity(value);
        }

        private int CountRole(string role)
        {
            int count = 0;
            for (int index = 0; index < nodes.Count; index++)
            {
                if (string.Equals(nodes[index].role, role, StringComparison.Ordinal))
                    count++;
            }
            return count;
        }

        private bool CompareCurrentStateToTransforms()
        {
            const float tolerance = 0.0001f;
            for (int index = 0; index < nodes.Count; index++)
            {
                if (!currentState[index].ApproximatelyEquals(
                        new TransformState(nodes[index].transform), tolerance))
                    return false;
            }
            return true;
        }

        private static bool IsReadThenGate(IReadOnlyList<string> events)
        {
            return events.Count == 2 && events[0] == "read" && events[1] == "gated";
        }

        private static bool IsReadAuditMarkerIdentityWriteback(IReadOnlyList<string> events)
        {
            return events.Count == 3 && events[0] == "read" &&
                   events[1] == "audit_callback_marker" &&
                   events[2] == "identity_writeback";
        }
    }
}
