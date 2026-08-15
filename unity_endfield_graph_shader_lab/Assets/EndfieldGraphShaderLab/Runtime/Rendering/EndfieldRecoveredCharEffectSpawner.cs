using System;
using System.Collections.Generic;
using UnityEngine;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Shared Overview entrance-effect adapter for generated, source-closed
    /// ParticleSystem prefabs.  The component is intentionally data-driven:
    /// no prefab-name fallback, EffectSetting emulation, or HGRP shader
    /// approximation is performed here.
    /// </summary>
    [DisallowMultipleComponent]
    [AddComponentMenu("Endfield/Character Recovery/Char Effect Spawner")]
    public sealed class EndfieldRecoveredCharEffectSpawner : MonoBehaviour,
        IEndfieldOverviewEffectSpawner
    {
        public const string ExpectedContractSchema =
            "endfield.zhuangfy-gacha-particle-inventory.v1";
        public const string CharInfoContractSchema =
            "endfield.charinfo-char-effect-particle.v1";

        public static bool IsSupportedContractSchema(string schema)
        {
            return string.Equals(schema, ExpectedContractSchema, StringComparison.Ordinal) ||
                string.Equals(schema, CharInfoContractSchema, StringComparison.Ordinal);
        }

        [Serializable]
        public sealed class Binding
        {
            [Tooltip("Exact EndfieldOverviewEffectRequest.prefabName.")]
            public string requestPrefabName;

            [Tooltip("Generated prefab with an EndfieldRecoveredParticleEffectSource marker.")]
            public GameObject prefab;

            [Tooltip("Optional exact mount path below the actor root. Empty means actor root.")]
            public string requiredMountPoint;

            [Tooltip("Explicit source scene mount. Required for external mounts such as singleEffects/effect<height>.")]
            public Transform explicitMount;

            [Tooltip("Source owner path from the serialized contract; evidence only, never resolved by name.")]
            public string sourceMountOwner;

            public long sourceMountGameObjectPathId;
            public long sourceMountTransformPathId;

            [Tooltip("Optional marker effectRoot assertion. Empty means use the marker value.")]
            public string expectedEffectRoot;

            [Min(0f)]
            public float expectedDuration;
        }

        [SerializeField]
        private Binding[] bindings = Array.Empty<Binding>();

        [SerializeField]
        private bool rejectUnboundRequests = true;

        private readonly Dictionary<string, GameObject> activeEffects =
            new Dictionary<string, GameObject>(StringComparer.Ordinal);

        public Binding[] Bindings => bindings;

        public void ReplaceBindings(Binding[] value)
        {
            bindings = value ?? Array.Empty<Binding>();
        }

        public bool RejectUnboundRequests
        {
            get => rejectUnboundRequests;
            set => rejectUnboundRequests = value;
        }

        public void SpawnOverviewEffect(
            EndfieldOverviewEffectRequest request,
            Transform actorRoot)
        {
            if (string.IsNullOrEmpty(request.prefabName))
                return;

            Binding binding = FindBinding(request.prefabName);
            if (binding == null)
            {
                FailClosed(
                    "unbound_effect_request",
                    request.prefabName,
                    "No exact CharEffect binding exists.");
                return;
            }

            if (!TryValidateBinding(binding, request, out string reason))
            {
                FailClosed("invalid_effect_binding", request.prefabName, reason);
                return;
            }

            Transform mount = ResolveMount(binding, request, actorRoot, out reason);
            if (mount == null)
            {
                FailClosed("missing_effect_mount", request.prefabName, reason);
                return;
            }

            FinishOverviewEffect(request.prefabName);

            GameObject instance = Instantiate(binding.prefab, mount, false);
            instance.name = binding.prefab.name + "__OverviewRuntime";
            instance.SetActive(false);

            ParticleSystem[] systems =
                instance.GetComponentsInChildren<ParticleSystem>(true);
            foreach (ParticleSystem system in systems)
            {
                system.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            }

            activeEffects[request.prefabName] = instance;
            instance.SetActive(true);
            foreach (ParticleSystem system in systems)
                system.Play(true);
        }

        public void FinishOverviewEffect(string prefabName)
        {
            if (string.IsNullOrEmpty(prefabName))
                return;

            if (!activeEffects.TryGetValue(prefabName, out GameObject instance))
                return;

            activeEffects.Remove(prefabName);
            if (instance == null)
                return;

            foreach (ParticleSystem system in
                instance.GetComponentsInChildren<ParticleSystem>(true))
            {
                system.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            }
            Destroy(instance);
        }

        private void OnDisable()
        {
            FinishAllEffects();
        }

        private void OnDestroy()
        {
            FinishAllEffects();
        }

        private void FinishAllEffects()
        {
            string[] names = new string[activeEffects.Count];
            activeEffects.Keys.CopyTo(names, 0);
            foreach (string name in names)
                FinishOverviewEffect(name);
        }

        private Binding FindBinding(string requestPrefabName)
        {
            if (bindings == null)
                return null;
            foreach (Binding binding in bindings)
            {
                if (binding != null &&
                    string.Equals(
                        binding.requestPrefabName,
                        requestPrefabName,
                        StringComparison.Ordinal))
                    return binding;
            }
            return null;
        }

        private static Transform ResolveMount(
            Binding binding,
            EndfieldOverviewEffectRequest request,
            Transform actorRoot,
            out string reason)
        {
            reason = string.Empty;
            if (actorRoot == null)
            {
                reason = "Actor root is null.";
                return null;
            }

            string required = binding.requiredMountPoint ?? string.Empty;
            string requested = request.mountPoint ?? string.Empty;
            if (!string.Equals(required, requested, StringComparison.Ordinal))
            {
                reason =
                    "Requested mount point does not match the binding: '" +
                    requested + "' versus '" + required + "'.";
                return null;
            }

            if (binding.explicitMount != null)
                return binding.explicitMount;

            if (required.StartsWith("sceneObject.", StringComparison.Ordinal))
            {
                reason = "External source mount requires an explicit Transform binding.";
                return null;
            }

            if (requested.Length == 0)
                return actorRoot;

            Transform mount = actorRoot.Find(requested);
            if (mount == null)
                reason = "Exact mount path was not found below the actor root.";
            return mount;
        }

        private static bool TryValidateBinding(
            Binding binding,
            EndfieldOverviewEffectRequest request,
            out string reason)
        {
            reason = string.Empty;
            if (binding.prefab == null)
            {
                reason = "Binding prefab is null.";
                return false;
            }

            if (!string.Equals(
                binding.requestPrefabName,
                request.prefabName,
                StringComparison.Ordinal))
            {
                reason = "Binding request name is not exact.";
                return false;
            }

            EndfieldRecoveredParticleEffectSource marker =
                binding.prefab.GetComponent<EndfieldRecoveredParticleEffectSource>();
            if (marker == null)
            {
                reason = "Prefab has no source particle contract marker.";
                return false;
            }
            if (!IsSupportedContractSchema(marker.contractSchema))
            {
                reason = "Unsupported or unknown particle contract schema.";
                return false;
            }
            if (string.IsNullOrEmpty(marker.effectRoot))
            {
                reason = "Source marker has no effectRoot.";
                return false;
            }
            if (!string.IsNullOrEmpty(binding.expectedEffectRoot) &&
                marker.effectRoot != binding.expectedEffectRoot)
            {
                reason = "Source effectRoot does not match the explicit binding.";
                return false;
            }
            if (binding.expectedDuration > 0f &&
                !Mathf.Approximately(binding.expectedDuration, marker.sourceEffectDuration))
            {
                reason = "Source effect duration does not match the explicit binding.";
                return false;
            }
            if (marker.particleNodes == null || marker.particleNodes.Length == 0)
            {
                reason = "Source marker has no particle nodes.";
                return false;
            }

            ParticleSystem[] systems =
                binding.prefab.GetComponentsInChildren<ParticleSystem>(true);
            ParticleSystemRenderer[] renderers =
                binding.prefab.GetComponentsInChildren<ParticleSystemRenderer>(true);
            if (systems.Length != marker.particleNodes.Length ||
                renderers.Length != marker.particleNodes.Length)
            {
                reason = "Generated particle/renderer counts drifted from the source marker.";
                return false;
            }

            foreach (EndfieldRecoveredParticleNodeSource node in marker.particleNodes)
            {
                if (node == null ||
                    !node.nativeParticlePayloadApplied ||
                    !node.nativeRendererPayloadApplied ||
                    node.rendererFailClosedForUnrecoveredShader)
                {
                    reason =
                        "At least one particle node is incomplete or fail-closed for an " +
                        "unrecovered shader.";
                    return false;
                }
            }

            for (int index = 0; index < renderers.Length; index++)
            {
                ParticleSystemRenderer renderer = renderers[index];
                EndfieldRecoveredParticleNodeSource node = marker.particleNodes[index];
                if (renderer == null)
                {
                    reason = "Particle renderer is missing.";
                    return false;
                }
                if (!node.sourceRendererEnabled)
                {
                    if (renderer.enabled)
                    {
                        reason = "Disabled source renderer became enabled.";
                        return false;
                    }
                    continue;
                }
                if (renderer.sharedMaterials == null || renderer.sharedMaterials.Length == 0)
                {
                    reason = "Enabled particle renderer has no source material.";
                    return false;
                }
                foreach (Material material in renderer.sharedMaterials)
                {
                    if (material == null || material.shader == null ||
                        material.shader.name.IndexOf(
                            "Unavailable",
                            StringComparison.OrdinalIgnoreCase) >= 0 ||
                        material.shader.name.IndexOf(
                            "FailClosed",
                            StringComparison.OrdinalIgnoreCase) >= 0)
                    {
                        reason =
                            "Particle material/shader is unresolved or explicitly " +
                            "fail-closed.";
                        return false;
                    }
                }
            }
            return true;
        }

        private void FailClosed(string code, string effectName, string reason)
        {
            if (rejectUnboundRequests || code != "unbound_effect_request")
            {
                Debug.LogWarning(
                    "[Endfield CharEffect] " + code + " for '" + effectName + "': " +
                    reason,
                    this);
            }
        }
    }
}
