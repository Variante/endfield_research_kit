using System;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Imports source-closed Endminf clip bindings. Legacy auto-play is only the lab's
    /// instantiation-time transport; it is not a retail EffectInstance/LOD timing claim.
    /// </summary>
    public static class EndfieldEndminfEffectAnimationImporter
    {
        private const string EffectRoot =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Effects/Overview";
        private const string Prefab = EffectRoot + "/P_fxui_endminm003_overview_01.prefab";
        private const string AnimationRoot = EffectRoot + "/Animation";
        private const string EffectNanguanPath = "effect_nanguan";
        private const string EffectNanguanClipName = "A_fx_endminf_ui_overview_04";

        [MenuItem("Endfield/Character Recovery Lab/Build Endminf Effect Animation")]
        public static void BuildAndValidate()
        {
            AnimationClip rigClip = AssetDatabase.LoadAssetAtPath<AnimationClip>(
                AnimationRoot + "/A_actor_endminf_ui_overview_02.anim");
            AnimationClip rocksClip = AssetDatabase.LoadAssetAtPath<AnimationClip>(
                AnimationRoot + "/" + EffectNanguanClipName + ".anim");
            Require(rigClip != null && rigClip.legacy,
                "cached exact A_actor_endminf_ui_overview_02 clip is missing");
            Require(rocksClip != null && rocksClip.legacy,
                "cached exact A_fx_endminf_ui_overview_04 clip is missing");

            GameObject root = PrefabUtility.LoadPrefabContents(Prefab);
            Require(root != null && root.name == "P_fxui_endminm003_overview_01",
                "Endminf overview_01 prefab root drifted");
            try
            {
                Bind(root.transform, "effect_01", rigClip,
                    new[] { "Dummy002", "Dummy003", "Dummy004" });
                Bind(root.transform, EffectNanguanPath, rocksClip,
                    new[] { "Sphere002", "Sphere003", "Sphere004", "Sphere005" });
                PrefabUtility.SaveAsPrefabAsset(root, Prefab);
            }
            finally { PrefabUtility.UnloadPrefabContents(root); }
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            ValidateSaved();
        }

        private static void Bind(Transform root, string hostPath, AnimationClip clip,
            string[] requiredDirectChildren)
        {
            Transform host = root.Find(hostPath);
            Require(host != null, "missing exact effect animation host: " + hostPath);
            foreach (string child in requiredDirectChildren)
                Require(host.Find(child) != null && host.Find(child).parent == host,
                    "missing exact direct animation path: " + hostPath + "/" + child);
            foreach (EditorCurveBinding binding in AnimationUtility.GetCurveBindings(clip))
                Require(host.Find(binding.path) != null,
                    "animation binding path does not resolve under " + hostPath + ": " + binding.path);
            Animation animation = host.GetComponent<Animation>();
            if (animation == null) animation = host.gameObject.AddComponent<Animation>();
            foreach (AnimationState state in animation.Cast<AnimationState>().ToArray())
                animation.RemoveClip(state.clip);
            animation.AddClip(clip, clip.name);
            animation.clip = clip;
            // Lab transport only: the retail owner transition and clip start relative to
            // EffectInstance.Start remain unresolved.
            animation.playAutomatically = true;
        }

        private static void ValidateSaved()
        {
            GameObject root = AssetDatabase.LoadAssetAtPath<GameObject>(Prefab);
            Require(root != null, "saved overview_01 prefab missing");
            Animation rig = root.transform.Find("effect_01").GetComponent<Animation>();
            Animation rocks = root.transform.Find(EffectNanguanPath).GetComponent<Animation>();
            Require(rig != null && rig.clip != null && rig.playAutomatically &&
                rig.clip.name == "A_actor_endminf_ui_overview_02", "effect_01 playback drifted");
            Require(rocks != null && rocks.clip != null && rocks.playAutomatically &&
                rocks.clip.name == EffectNanguanClipName,
                "effect_nanguan playback drifted");
            Require(AnimationUtility.GetCurveBindings(rig.clip).Length == 30,
                "effect_01 curve census drifted");
            EditorCurveBinding[] rockBindings =
                AnimationUtility.GetCurveBindings(rocks.clip);
            Require(rockBindings.Length == 28,
                "effect_nanguan curve census drifted");
            Require(!rockBindings.Any(binding => binding.type == typeof(GameObject) &&
                    binding.propertyName == "m_IsActive"),
                "effect_nanguan must not graft overview_03 GameObject visibility curves");
        }
        private static void Require(bool value,string message){if(!value)throw new InvalidOperationException(message);}
    }
}
