using System;
using System.Linq;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEngine;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>Installs Li Zhiyan's 12 controller-owned Overview requests and binds only the source-closed finger effect.</summary>
    public static class EndfieldLiZhiyanOverviewEffectBindingBuilder
    {
        private const string ActorPrefabPath =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Lizhiyan/Prefabs/Lizhiyan.prefab";
        private const string EffectName =
            "P_fxui_lizhiyan_overview_trails_Bip001_R_Finger2Nub";
        private const string EffectPrefabPath =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Lizhiyan/Effects/OverviewFinger/" +
            EffectName + ".prefab";
        private static readonly EndfieldOverviewEffectRequest[] ControllerRequests =
        {
            Request("P_fxui_lizhiyan_overview_start_09", ""),
            Request("P_fxui_lizhiyan_overview_start_10", ""),
            Request("P_fxui_lizhiyan_overview_start_01", ""),
            Request("P_fxui_lizhiyan_overview_start_02", ""),
            Request("P_fxui_lizhiyan_overview_start_03", ""),
            Request(EffectName, "Bip001_R_Finger2Nub"),
            Request("P_fxui_lizhiyan_overview_start_04", ""),
            Request("P_fxui_lizhiyan_overview_start_05", ""),
            Request("P_fxui_lizhiyan_overview_start_06", ""),
            Request("P_fxui_lizhiyan_overview_start_07", ""),
            Request("P_fxui_lizhiyan_overview_start_04_1", ""),
            Request("P_fxui_lizhiyan_overview_start_04_2", ""),
        };

        private static EndfieldOverviewEffectRequest Request(string name, string mount) =>
            new EndfieldOverviewEffectRequest { prefabName = name, mountPoint = mount };

        [MenuItem("Endfield/Character Recovery Lab/Bind Li Zhiyan Overview Finger Effect")]
        public static void BuildAndValidate()
        {
            GameObject effect = AssetDatabase.LoadAssetAtPath<GameObject>(EffectPrefabPath);
            if (effect == null) throw new InvalidOperationException("Li Zhiyan finger effect is missing");
            GameObject root = PrefabUtility.LoadPrefabContents(ActorPrefabPath);
            if (root == null) throw new InvalidOperationException("Li Zhiyan actor prefab is missing");
            try
            {
                EndfieldOverviewPlayback playback = root.GetComponentInChildren<EndfieldOverviewPlayback>(true);
                if (playback == null) throw new InvalidOperationException("Li Zhiyan Overview playback is missing");
                if (root.GetComponentsInChildren<Transform>(true).Count(value =>
                        value.name == "Bip001_R_Finger2Nub") != 1)
                    throw new InvalidOperationException("Li Zhiyan finger mount is not unique");
                playback.entranceEffects = ControllerRequests.ToArray();
                EditorUtility.SetDirty(playback);
                EndfieldRecoveredCharEffectSpawner spawner =
                    playback.GetComponent<EndfieldRecoveredCharEffectSpawner>();
                if (spawner == null) spawner = playback.gameObject.AddComponent<EndfieldRecoveredCharEffectSpawner>();
                spawner.ReplaceBindings(new[]
                {
                    new EndfieldRecoveredCharEffectSpawner.Binding
                    {
                        requestPrefabName = EffectName,
                        prefab = effect,
                        requiredMountPoint = "Bip001_R_Finger2Nub",
                        expectedEffectRoot = EffectName,
                        expectedDelay = 0.83333f,
                        expectedDuration = 2.33333f,
                    },
                });
                spawner.RejectUnboundRequests = true;
                EditorUtility.SetDirty(spawner);
                PrefabUtility.SaveAsPrefabAsset(root, ActorPrefabPath);
            }
            finally { PrefabUtility.UnloadPrefabContents(root); }
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            ValidateSaved();
        }

        private static void ValidateSaved()
        {
            GameObject actor = AssetDatabase.LoadAssetAtPath<GameObject>(ActorPrefabPath);
            EndfieldOverviewPlayback playback = actor == null ? null : actor.GetComponentInChildren<EndfieldOverviewPlayback>(true);
            EndfieldRecoveredCharEffectSpawner spawner = playback == null ? null : playback.GetComponent<EndfieldRecoveredCharEffectSpawner>();
            if (playback == null || playback.entranceEffects == null ||
                playback.entranceEffects.Length != 12 || spawner == null ||
                spawner.Bindings == null || spawner.Bindings.Length != 1 || !spawner.RejectUnboundRequests)
                throw new InvalidOperationException("Li Zhiyan partial Overview binding did not serialize");
            EndfieldRecoveredCharEffectSpawner.Binding binding = spawner.Bindings[0];
            EndfieldRecoveredParticleEffectSource marker = binding.prefab == null ? null :
                binding.prefab.GetComponent<EndfieldRecoveredParticleEffectSource>();
            if (binding.requestPrefabName != EffectName || binding.requiredMountPoint != "Bip001_R_Finger2Nub" ||
                !Mathf.Approximately(binding.expectedDelay, 0.83333f) ||
                !Mathf.Approximately(binding.expectedDuration, 2.33333f) || marker == null ||
                marker.effectRoot != EffectName || marker.particleNodes.Length != 7 ||
                !marker.particleNodes.All(value => value.rendererFailClosedForUnrecoveredShader))
                throw new InvalidOperationException("Li Zhiyan finger binding boundary drifted");
            Debug.Log("[Endfield Li Zhiyan] bound exact finger Overview request at Bip001_R_Finger2Nub; " +
                "11 controller requests remain explicitly unbound and six VFXBaseV2 materials remain fail-closed");
        }
    }
}
