using System;
using System.Linq;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEngine;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Installs the one independently AssetMap-proven Last Rite Overview
    /// effect binding. The prefab remains runtime-rejected while its exact
    /// VFXBaseV2 materials are fail-closed; the other controller requests stay
    /// explicitly unbound.
    /// </summary>
    public static class EndfieldLastRiteOverviewEffectBindingBuilder
    {
        private const string ActorPrefabPath =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Lastrite/Prefabs/Lastrite.prefab";
        private const string EffectPrefabPath =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Lastrite/Effects/OverviewHead/" +
            "P_fxui_lastrite_ui_overview_start_01_01.prefab";
        private const string EffectName =
            "P_fxui_lastrite_ui_overview_start_01_01";
        private static readonly EndfieldOverviewEffectRequest[] ControllerRequests =
        {
            Request("P_fxui_lastrite_ui_overview_start_01_01", "Bip001_HeadNub"),
            Request("P_fxui_lastrite_ui_overview_start_01_02", ""),
            Request("P_fxui_lastrite_ui_overview_start_01_03", "Root"),
            Request("P_fxui_lastrite_ui_overview_start_01_04", "Bip001_R_Thigh"),
            Request("P_fxui_lastrite_ui_overview_start_01_05", "Bip001_L_UpperArm"),
            Request("P_fxui_lastrite_ui_overview_start_01_hand_L", "Bip001_L_Finger2Nub"),
            Request("P_fxui_lastrite_ui_overview_start_01_hand_R", "Bip001_R_Finger2Nub"),
            Request("P_fxui_lastrite_ui_overview_start_01_ear_asset", ""),
        };

        private static EndfieldOverviewEffectRequest Request(string prefabName,
            string mountPoint)
        {
            return new EndfieldOverviewEffectRequest
            {
                prefabName = prefabName,
                mountPoint = mountPoint,
            };
        }

        [MenuItem("Endfield/Character Recovery Lab/Bind Last Rite Overview Head Effect")]
        public static void BuildAndValidate()
        {
            GameObject effect = AssetDatabase.LoadAssetAtPath<GameObject>(EffectPrefabPath);
            if (effect == null)
                throw new InvalidOperationException("Last Rite Overview head effect is missing");
            GameObject root = PrefabUtility.LoadPrefabContents(ActorPrefabPath);
            if (root == null)
                throw new InvalidOperationException("Last Rite actor prefab is missing");
            try
            {
                EndfieldOverviewPlayback playback =
                    root.GetComponentInChildren<EndfieldOverviewPlayback>(true);
                if (playback == null)
                    throw new InvalidOperationException(
                        "Last Rite Overview playback is missing");
                playback.entranceEffects = ControllerRequests.ToArray();
                EditorUtility.SetDirty(playback);
                if (root.GetComponentsInChildren<Transform>(true).Count(value =>
                        value.name == "Bip001_HeadNub") != 1)
                    throw new InvalidOperationException(
                        "Last Rite head effect mount is not unique");
                EndfieldRecoveredCharEffectSpawner spawner =
                    playback.GetComponent<EndfieldRecoveredCharEffectSpawner>();
                if (spawner == null)
                    spawner = playback.gameObject.AddComponent<
                        EndfieldRecoveredCharEffectSpawner>();
                spawner.ReplaceBindings(new[]
                {
                    new EndfieldRecoveredCharEffectSpawner.Binding
                    {
                        requestPrefabName = EffectName,
                        prefab = effect,
                        requiredMountPoint = "Bip001_HeadNub",
                        expectedEffectRoot = EffectName,
                        expectedDelay = 3.5f,
                        expectedDuration = 13.5f,
                    },
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
            ValidateSaved();
        }

        private static void ValidateSaved()
        {
            GameObject actor = AssetDatabase.LoadAssetAtPath<GameObject>(ActorPrefabPath);
            EndfieldOverviewPlayback playback = actor == null
                ? null
                : actor.GetComponentInChildren<EndfieldOverviewPlayback>(true);
            EndfieldRecoveredCharEffectSpawner spawner = playback == null
                ? null
                : playback.GetComponent<EndfieldRecoveredCharEffectSpawner>();
            if (playback == null || playback.entranceEffects == null ||
                playback.entranceEffects.Length != ControllerRequests.Length ||
                !playback.entranceEffects.Select(value =>
                    value.prefabName + "\0" + value.mountPoint).SequenceEqual(
                    ControllerRequests.Select(value =>
                        value.prefabName + "\0" + value.mountPoint)) ||
                spawner == null || spawner.Bindings == null ||
                spawner.Bindings.Length != 1)
                throw new InvalidOperationException(
                    "Last Rite exact partial binding did not serialize");
            EndfieldRecoveredCharEffectSpawner.Binding binding = spawner.Bindings[0];
            EndfieldRecoveredParticleEffectSource marker = binding.prefab == null
                ? null
                : binding.prefab.GetComponent<EndfieldRecoveredParticleEffectSource>();
            if (binding.requestPrefabName != EffectName ||
                binding.requiredMountPoint != "Bip001_HeadNub" ||
                !Mathf.Approximately(binding.expectedDelay, 3.5f) ||
                !Mathf.Approximately(binding.expectedDuration, 13.5f) ||
                marker == null || marker.effectRoot != EffectName ||
                marker.particleNodes.Length != 5 ||
                !marker.particleNodes.All(value =>
                    value.rendererFailClosedForUnrecoveredShader) ||
                !spawner.RejectUnboundRequests)
                throw new InvalidOperationException(
                    "Last Rite Overview head binding/admission boundary drifted");
            Debug.Log(
                "[Endfield Last Rite] bound exact head Overview request at " +
                "Bip001_HeadNub with delay=3.5/duration=13.5; runtime remains " +
                "fail-closed for six unrecovered VFXBaseV2 materials; seven " +
                "other FromOverview requests remain explicitly unbound");
        }
    }
}
