using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace EndfieldGraphShaderLab.Editor
{
    /// <summary>
    /// Editor-only gate for the shared CharEffect adapter.  It intentionally
    /// reports source-prefab nodes that are fail-closed rather than trying to
    /// repair them with a guessed HGRP shader or a guessed EffectSetting.
    /// </summary>
    public static class EndfieldRecoveredCharEffectSpawnerVerifier
    {
        private const string PrefabRoot =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Zhuangfy/Effects/GachaParticles/Prefabs";
        private const string CharInfoPrefabRoot =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/CharInfo/Effects/CharEffect/Prefabs";

        [MenuItem("Endfield/Character Recovery/Verify CharEffect Prefabs")]
        public static void VerifyGeneratedPrefabs()
        {
            var paths = new List<string>();
            foreach (string root in new[] { PrefabRoot, CharInfoPrefabRoot })
            {
                foreach (string guid in AssetDatabase.FindAssets("t:Prefab", new[] { root }))
                    paths.Add(AssetDatabase.GUIDToAssetPath(guid));
            }
            int admitted = 0;
            int rejected = 0;
            var failures = new List<string>();

            foreach (string path in paths.Distinct(StringComparer.Ordinal))
            {
                GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if (prefab == null)
                    continue;

                if (TryValidatePrefab(prefab, out string reason))
                {
                    admitted++;
                    Debug.Log("[Endfield CharEffect] admitted source-closed prefab: " + path);
                }
                else
                {
                    rejected++;
                    failures.Add(path + " -> " + reason);
                }
            }

            foreach (string failure in failures)
                Debug.LogWarning("[Endfield CharEffect] fail-closed: " + failure);

            Debug.Log(
                "[Endfield CharEffect] verification complete: admitted=" + admitted +
                ", fail_closed=" + rejected +
                ", unknown HGRP semantics were not approximated.");
        }

        public static bool TryValidatePrefab(GameObject prefab, out string reason)
        {
            reason = string.Empty;
            if (prefab == null)
            {
                reason = "prefab is null";
                return false;
            }

            EndfieldRecoveredParticleEffectSource marker =
                prefab.GetComponent<EndfieldRecoveredParticleEffectSource>();
            if (marker == null)
            {
                reason = "missing EndfieldRecoveredParticleEffectSource";
                return false;
            }
            if (!EndfieldRecoveredCharEffectSpawner.IsSupportedContractSchema(
                marker.contractSchema))
            {
                reason = "unsupported source contract schema";
                return false;
            }

            ParticleSystem[] systems =
                prefab.GetComponentsInChildren<ParticleSystem>(true);
            ParticleSystemRenderer[] renderers =
                prefab.GetComponentsInChildren<ParticleSystemRenderer>(true);
            if (marker.particleNodes == null ||
                marker.particleNodes.Length == 0 ||
                systems.Length != marker.particleNodes.Length ||
                renderers.Length != marker.particleNodes.Length)
            {
                reason = "particle/renderer count is not source-closed";
                return false;
            }

            foreach (EndfieldRecoveredParticleNodeSource node in marker.particleNodes)
            {
                if (node == null || !node.nativeParticlePayloadApplied ||
                    !node.nativeRendererPayloadApplied)
                {
                    reason = "native particle or renderer payload is incomplete";
                    return false;
                }
                if (node.rendererFailClosedForUnrecoveredShader)
                {
                    reason = "one renderer is explicitly fail-closed for an unrecovered shader";
                    return false;
                }
            }

            for (int index = 0; index < renderers.Length; index++)
            {
                ParticleSystemRenderer renderer = renderers[index];
                EndfieldRecoveredParticleNodeSource node = marker.particleNodes[index];
                if (renderer == null)
                {
                    reason = "renderer is missing";
                    return false;
                }
                if (!node.sourceRendererEnabled)
                {
                    if (renderer.enabled)
                    {
                        reason = "disabled source renderer became enabled";
                        return false;
                    }
                    continue;
                }
                if (renderer.sharedMaterials == null || renderer.sharedMaterials.Length == 0)
                {
                    reason = "enabled renderer has no source material";
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
                            "material/shader is unresolved or explicitly fail-closed";
                        return false;
                    }
                }
            }
            return true;
        }
    }
}
