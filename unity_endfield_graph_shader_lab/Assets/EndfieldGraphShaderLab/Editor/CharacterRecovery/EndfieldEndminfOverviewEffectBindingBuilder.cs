using System;
using System.Linq;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace EndfieldGraphShaderLabEditor
{
    public static class EndfieldEndminfOverviewEffectBindingBuilder
    {
        private const string Actor = "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Prefabs/Endminf.prefab";
        private const string Effects = "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Effects/Overview/";
        private static readonly string[] Names = { "P_fxui_endminm003_overview_01", "P_fxui_endminm003_overview_02", "P_fxui_endminm003_overview_03", "P_fxui_endminm003_overview_04" };
        private static readonly float[] Durations = { 9f, 10f, 9f, 9f };
        private const string ViewerScene =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Scenes/CharacterRecoveryViewer.unity";

        public static void OpenVisualReproductionInPlayMode()
        {
            EndfieldEndminfOverviewEffectImporter.BuildAndValidate();
            BuildAndValidate();
            EditorSceneManager.OpenScene(ViewerScene, OpenSceneMode.Single);
            EditorApplication.delayCall += () =>
            {
                if (!EditorApplication.isPlayingOrWillChangePlaymode)
                    EditorApplication.EnterPlaymode();
            };
        }

        [MenuItem("Endfield/Character Recovery Lab/Bind Endminf Overview Effects")]
        public static void BuildAndValidate()
        {
            GameObject actor = PrefabUtility.LoadPrefabContents(Actor);
            if (actor == null) throw new InvalidOperationException("Endminf actor is missing");
            try
            {
                EndfieldOverviewPlayback playback = actor.GetComponentInChildren<EndfieldOverviewPlayback>(true);
                if (playback == null) throw new InvalidOperationException("Endminf Overview playback is missing");
                playback.entranceEffects = Names.Select(name => new EndfieldOverviewEffectRequest {
                    prefabName = name, mountPoint = "", finishWhenExit = true,
                    finishWhenTransition = false
                }).ToArray();
                EndfieldRecoveredCharEffectSpawner spawner = playback.GetComponent<EndfieldRecoveredCharEffectSpawner>();
                if (spawner == null) spawner = playback.gameObject.AddComponent<EndfieldRecoveredCharEffectSpawner>();
                spawner.ReplaceBindings(Names.Select((name, index) => new EndfieldRecoveredCharEffectSpawner.Binding {
                    requestPrefabName = name, prefab = AssetDatabase.LoadAssetAtPath<GameObject>(Effects + name + ".prefab"),
                    requiredMountPoint = "", expectedEffectRoot = name, expectedDelay = 0f,
                    expectedDuration = Durations[index], stationaryPosition = true,
                    shouldFollowScale = false, shouldFollowRotation = true,
                    shouldFollowMainObjRotation = false }).ToArray());
                spawner.RejectUnboundRequests = true;
                EditorUtility.SetDirty(playback); EditorUtility.SetDirty(spawner);
                PrefabUtility.SaveAsPrefabAsset(actor, Actor);
            }
            finally { PrefabUtility.UnloadPrefabContents(actor); }
            AssetDatabase.SaveAssets(); AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            GameObject saved = AssetDatabase.LoadAssetAtPath<GameObject>(Actor);
            EndfieldOverviewPlayback check = saved.GetComponentInChildren<EndfieldOverviewPlayback>(true);
            EndfieldRecoveredCharEffectSpawner source = check.GetComponent<EndfieldRecoveredCharEffectSpawner>();
            if (check.entranceEffects.Length != 4 || source.Bindings.Length != 4 ||
                check.entranceEffects.Any(row => row.prefabName == "A_actor_endminf_ui_overview_02") ||
                check.entranceEffects.Any(row => !row.finishWhenExit || row.finishWhenTransition) ||
                source.Bindings.Any(row => row.prefab == null || !row.stationaryPosition ||
                    row.shouldFollowScale || !row.shouldFollowRotation ||
                    row.shouldFollowMainObjRotation))
                throw new InvalidOperationException("Endminf exact entrance-effect binding drifted");
        }
    }
}
