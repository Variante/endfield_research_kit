using System;
using System.Linq;
using UnityEditor;
using UnityEngine;
using EndfieldGraphShaderLab;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Binds the controller-owned AnimatorBehaviourPlayEffect records to the
    /// exact generated Zhuang Fanyi effect assets. This is Character Info
    /// Overview ownership; it does not reuse the Gacha Timeline owner.
    /// </summary>
    public static class EndfieldZhuangfyOverviewEffectBindingBuilder
    {
        private const string ActorPrefabPath =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Zhuangfy/Prefabs/Zhuangfy.prefab";
        private const string EffectPrefabRoot =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Zhuangfy/Effects/GachaParticles/Prefabs/";

        [MenuItem("Endfield/Character Recovery Lab/Bind Zhuangfy Overview Effects")]
        public static void BuildAndValidate()
        {
            GameObject root = PrefabUtility.LoadPrefabContents(ActorPrefabPath);
            if (root == null)
                throw new InvalidOperationException("Zhuangfy actor prefab is missing");
            try
            {
                EndfieldOverviewPlayback playback =
                    root.GetComponentInChildren<EndfieldOverviewPlayback>(true);
                if (playback == null)
                    throw new InvalidOperationException(
                        "Zhuangfy prefab has no recovered Overview playback");

                EndfieldRecoveredCharEffectSpawner spawner =
                    playback.GetComponent<EndfieldRecoveredCharEffectSpawner>();
                if (spawner == null)
                    spawner = playback.gameObject.AddComponent<
                        EndfieldRecoveredCharEffectSpawner>();
                spawner.ReplaceBindings(new[]
                {
                    Existing(
                        "P_fxui_zhuangfy_ui_overview_start_01_piaodai",
                        "RecoveredProps/P_fxui_zhuangfy_ui_overview_start_01_piaodai"),
                    Particle(
                        "P_fxui_zhuangfy_ui_overview_start_01_01",
                        string.Empty,
                        0f,
                        8f),
                    Particle(
                        "P_fxui_zhuangfy_ui_overview_start_01_baofa",
                        string.Empty,
                        6.1f,
                        3f),
                    Particle(
                        "P_fxui_zhuangfy_ui_overview_start_01_finger_lightning",
                        "Bip001_R_Finger2Nub",
                        4.4333334f,
                        2f),
                });
                spawner.RejectUnboundRequests = true;
                EditorUtility.SetDirty(spawner);
                PrefabUtility.SaveAsPrefabAsset(root, ActorPrefabPath);
            }
            finally
            {
                PrefabUtility.UnloadPrefabContents(root);
            }

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            ValidateSavedPrefab();
        }

        private static EndfieldRecoveredCharEffectSpawner.Binding Existing(
            string effectName,
            string actorRelativePath)
        {
            return new EndfieldRecoveredCharEffectSpawner.Binding
            {
                requestPrefabName = effectName,
                existingActorObjectPath = actorRelativePath,
                expectedEffectRoot = effectName,
            };
        }

        private static EndfieldRecoveredCharEffectSpawner.Binding Particle(
            string effectName,
            string mountPoint,
            float delay,
            float duration)
        {
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(
                EffectPrefabRoot + effectName + ".prefab");
            if (prefab == null)
                throw new InvalidOperationException(
                    "Generated source-closed effect prefab is missing: " + effectName);
            return new EndfieldRecoveredCharEffectSpawner.Binding
            {
                requestPrefabName = effectName,
                prefab = prefab,
                requiredMountPoint = mountPoint,
                expectedEffectRoot = effectName,
                expectedDelay = delay,
                expectedDuration = duration,
            };
        }

        private static void ValidateSavedPrefab()
        {
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(ActorPrefabPath);
            if (prefab == null)
                throw new InvalidOperationException("Saved Zhuangfy prefab is missing");
            EndfieldOverviewPlayback playback =
                prefab.GetComponentInChildren<EndfieldOverviewPlayback>(true);
            EndfieldRecoveredCharEffectSpawner spawner = playback == null
                ? null
                : playback.GetComponent<EndfieldRecoveredCharEffectSpawner>();
            if (spawner == null || spawner.Bindings == null ||
                spawner.Bindings.Length != 4)
                throw new InvalidOperationException(
                    "Zhuangfy Overview effect bindings did not serialize exactly");
            string[] requestNames = playback.entranceEffects
                .Select(value => value.prefabName)
                .OrderBy(value => value, StringComparer.Ordinal)
                .ToArray();
            string[] bindingNames = spawner.Bindings
                .Select(value => value.requestPrefabName)
                .OrderBy(value => value, StringComparer.Ordinal)
                .ToArray();
            if (!requestNames.SequenceEqual(bindingNames, StringComparer.Ordinal))
                throw new InvalidOperationException(
                    "Controller-owned effect requests and runtime bindings drifted");
            EndfieldRecoveredCharEffectSpawner.Binding piaodai =
                spawner.Bindings.Single(value => value.requestPrefabName.EndsWith(
                    "_piaodai", StringComparison.Ordinal));
            if (piaodai.prefab != null ||
                prefab.transform.Find(piaodai.existingActorObjectPath) == null)
                throw new InvalidOperationException(
                    "Zhuangfy piaodai existing-object binding drifted");
            ValidateParticleBinding(spawner.Bindings, "_01", 0f, 8f);
            ValidateParticleBinding(spawner.Bindings, "_baofa", 6.1f, 3f);
            ValidateParticleBinding(
                spawner.Bindings, "_finger_lightning", 4.4333334f, 2f);
            if (prefab.GetComponentsInChildren<Transform>(true).Count(
                    value => value.name == "Bip001_R_Finger2Nub") != 1)
                throw new InvalidOperationException(
                    "Zhuangfy finger-lightning mount is not unique");

            Debug.Log(
                "[Endfield Zhuangfy] Overview AnimatorBehaviourPlayEffect bindings " +
                "passed: piaodai(existing), _01(0/8), baofa(6.1/3), " +
                "finger(4.4333334/2@Bip001_R_Finger2Nub)");
        }

        private static void ValidateParticleBinding(
            EndfieldRecoveredCharEffectSpawner.Binding[] bindings,
            string suffix,
            float delay,
            float duration)
        {
            EndfieldRecoveredCharEffectSpawner.Binding binding = bindings.Single(
                value => value.requestPrefabName.EndsWith(
                    suffix, StringComparison.Ordinal));
            EndfieldRecoveredParticleEffectSource marker = binding.prefab == null
                ? null
                : binding.prefab.GetComponent<EndfieldRecoveredParticleEffectSource>();
            if (marker == null ||
                marker.effectRoot != binding.requestPrefabName ||
                marker.contractSchema !=
                    EndfieldRecoveredCharEffectSpawner.ExpectedContractSchema ||
                !Mathf.Approximately(binding.expectedDelay, delay) ||
                !Mathf.Approximately(binding.expectedDuration, duration) ||
                !Mathf.Approximately(marker.sourceEffectDuration, duration))
                throw new InvalidOperationException(
                    "Zhuangfy particle effect timing/source binding drifted: " + suffix);
        }
    }
}
