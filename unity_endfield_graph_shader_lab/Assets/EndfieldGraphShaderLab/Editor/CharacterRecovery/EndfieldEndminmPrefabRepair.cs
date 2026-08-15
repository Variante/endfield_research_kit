using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Rebuilds the one playable-catalog prefab that can be absent after an
    /// interrupted bulk import. The source manifest and output identity are
    /// fixed here so this repair cannot silently broaden to another actor.
    /// </summary>
    public static class EndfieldEndminmPrefabRepair
    {
        private const string ManifestPath =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminm/endminm_ui_recovery_manifest.json";
        private const string PrefabPath =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminm/Prefabs/Endminm.prefab";

        private static readonly string[] PreviewClips =
        {
            "A_actor_endminm_ui_overview_loop",
            "A_actor_endminm_ui_overview_start",
            "A_actor_endminm_uiteam_idle_01",
        };

        [MenuItem("Endfield/Character Recovery Lab/Repair Endminm Prefab")]
        public static void BuildAndValidate()
        {
            string source = Path.Combine(
                Directory.GetCurrentDirectory(), ManifestPath);
            if (!File.Exists(source))
                throw new FileNotFoundException(
                    "Endminm source manifest is missing", source);

            EditorSceneManager.NewScene(
                NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var spec = new EndfieldManifestCharacterSetup.ManifestCharacterSpec(
                ManifestPath,
                "Endminm",
                "Endministrator (endminm)",
                Vector3.zero,
                false,
                PreviewClips,
                false,
                PrefabPath);
            GameObject instance = EndfieldManifestCharacterSetup.BuildCharacter(spec);
            if (instance == null)
                throw new InvalidOperationException(
                    "Endminm manifest import returned no actor root");
            UnityEngine.Object.DestroyImmediate(instance);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);

            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
            if (prefab == null || prefab.name != "Endminm")
                throw new InvalidDataException(
                    "Endminm prefab identity was not generated exactly");
            if (!prefab.GetComponentsInChildren<SkinnedMeshRenderer>(true).Any())
                throw new InvalidDataException(
                    "Endminm prefab has no recovered skinned renderers");

            Debug.Log(
                "[Endfield Endminm] prefab repair passed: " + PrefabPath);
        }
    }
}
