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
        private struct BeforeScriptRunBehaviourLateUpdate { }
        private struct AfterScriptRunBehaviourLateUpdate { }

        private static readonly List<EndfieldSecondaryDynamicsRuntime> Active =
            new List<EndfieldSecondaryDynamicsRuntime>();
        private static bool playerLoopInstalled;

        public EndfieldSecondaryDynamicsData data;

        public bool BindingValid { get; private set; }
        public string BindingFailure { get; private set; } = "not validated";
        public float TargetWeight { get; private set; }
        public float CurrentWeight { get; private set; }
        public bool SolverWritebackEnabled => false;

        private const float EnableRate = 8.0f;
        private const float DisableRate = 6.0f;
        private const float WeightEpsilon = 0.001f;

        private void OnEnable()
        {
            BindingValid = ValidateBindings(out string failure);
            BindingFailure = failure;
            if (!BindingValid)
            {
                Debug.LogError(
                    "Recovered secondary dynamics failed closed on " + name + ": " + failure,
                    this);
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

        private void BeforeLateUpdate()
        {
            float rate = TargetWeight > CurrentWeight ? EnableRate : DisableRate;
            float next = Mathf.MoveTowards(CurrentWeight, TargetWeight, rate * Time.deltaTime);
            if (Mathf.Abs(next - CurrentWeight) >= WeightEpsilon ||
                Mathf.Approximately(next, TargetWeight))
                CurrentWeight = next;

            // Intentionally no transform writes here. This phase is the exact
            // recovered scheduling boundary reserved for the translated Start,
            // constraint, and Update Basic Posture kernels.
        }

        private void AfterLateUpdate()
        {
            // Intentionally no transform writes here. This phase is reserved
            // for the translated End kernel and centralized transform manager.
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
                string.IsNullOrEmpty(data.solverInputsSha256) ||
                string.IsNullOrEmpty(data.payloadDecodeSha256))
            {
                failure = "source contract references or hashes are missing";
                return false;
            }
            if (!HashMatches(data.solverInputs, data.solverInputsSha256) ||
                !HashMatches(data.payloadDecode, data.payloadDecodeSha256))
            {
                failure = "source contract hash differs from generated binding data";
                return false;
            }
            if (data.owners == null || data.owners.Length != 4)
            {
                failure = "expected exactly four recovered cloth owners";
                return false;
            }

            int bindingCount = 0;
            var unique = new HashSet<string>(StringComparer.Ordinal);
            foreach (EndfieldSecondaryDynamicsData.Owner owner in data.owners)
            {
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

        private static void InstallPlayerLoop()
        {
            PlayerLoopSystem root = PlayerLoop.GetCurrentPlayerLoop();
            if (playerLoopInstalled && ContainsRecoveredPhase(root))
                return;
            if (ContainsRecoveredPhase(root))
            {
                playerLoopInstalled = true;
                return;
            }
            if (!InsertRecoveredPhases(ref root))
                throw new InvalidOperationException(
                    "PreLateUpdate.ScriptRunBehaviourLateUpdate was not found in the PlayerLoop.");
            PlayerLoop.SetPlayerLoop(root);
            playerLoopInstalled = true;
        }

        private static bool ContainsRecoveredPhase(PlayerLoopSystem system)
        {
            if (system.type == typeof(BeforeScriptRunBehaviourLateUpdate))
                return true;
            if (system.subSystemList == null)
                return false;
            foreach (PlayerLoopSystem child in system.subSystemList)
            {
                if (ContainsRecoveredPhase(child))
                    return true;
            }
            return false;
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
            if (system.subSystemList == null)
                return false;
            for (int index = 0; index < system.subSystemList.Length; index++)
            {
                PlayerLoopSystem child = system.subSystemList[index];
                if (child.type == typeof(UnityEngine.PlayerLoop.PreLateUpdate.ScriptRunBehaviourLateUpdate))
                {
                    var list = system.subSystemList.ToList();
                    list.Insert(index, new PlayerLoopSystem
                    {
                        type = typeof(BeforeScriptRunBehaviourLateUpdate),
                        updateDelegate = RunBeforeLateUpdate,
                    });
                    list.Insert(index + 2, new PlayerLoopSystem
                    {
                        type = typeof(AfterScriptRunBehaviourLateUpdate),
                        updateDelegate = RunAfterLateUpdate,
                    });
                    system.subSystemList = list.ToArray();
                    return true;
                }
                if (InsertRecoveredPhases(ref child))
                {
                    system.subSystemList[index] = child;
                    return true;
                }
            }
            return false;
        }

        private static void RunBeforeLateUpdate()
        {
            for (int index = Active.Count - 1; index >= 0; index--)
            {
                EndfieldSecondaryDynamicsRuntime runtime = Active[index];
                if (runtime == null)
                    Active.RemoveAt(index);
                else if (runtime.isActiveAndEnabled && runtime.BindingValid)
                    runtime.BeforeLateUpdate();
            }
        }

        private static void RunAfterLateUpdate()
        {
            for (int index = Active.Count - 1; index >= 0; index--)
            {
                EndfieldSecondaryDynamicsRuntime runtime = Active[index];
                if (runtime == null)
                    Active.RemoveAt(index);
                else if (runtime.isActiveAndEnabled && runtime.BindingValid)
                    runtime.AfterLateUpdate();
            }
        }
    }
}
