using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEngine;
using L = EndfieldGraphShaderLabEditor.EndfieldLastRiteOverviewHeadEffectImporter;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>Imports only source-closed generic Endminf effect animation bindings.</summary>
    public static class EndfieldEndminfEffectAnimationImporter
    {
        private const string EffectRoot =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Effects/Overview";
        private const string Prefab = EffectRoot + "/P_fxui_endminm003_overview_01.prefab";
        private const string AnimationRoot = EffectRoot + "/Animation";
        private const string VisibilityContract =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/endminf_overview_rock_visibility.json";
        private const string EffectNanguanPath = "effect_nanguan";
        private const string CompositeRockClipName =
            "A_fx_endminf_ui_overview_03_04";
        private const string CompositeRockClipAsset =
            AnimationRoot + "/" + CompositeRockClipName + ".anim";
        private const int GameObjectActiveAttribute = 2086281974;
        private static readonly string[] ExpectedRockVisibilityPaths = {
            "Sphere002/Dummy002/P_endminf_ui_overview_01_rock_01",
            "Sphere003/Dummy005/P_endminf_ui_overview_01_rock_02",
            "Sphere004/Dummy004/P_endminf_ui_overview_01_rock_03",
            "Sphere005/Dummy003/P_endminf_ui_overview_01_rock_04",
        };

        [MenuItem("Endfield/Character Recovery Lab/Build Endminf Effect Animation")]
        public static void BuildAndValidate()
        {
            string project = Directory.GetParent(Application.dataPath).FullName;
            Dictionary<string, object> rockVisibility = Load(project, VisibilityContract);
            ValidateRockVisibilitySource(rockVisibility);
            L.EnsureFolder(AnimationRoot);
            AnimationClip rigClip = AssetDatabase.LoadAssetAtPath<AnimationClip>(
                AnimationRoot + "/A_actor_endminf_ui_overview_02.anim");
            AnimationClip sourceRocks = AssetDatabase.LoadAssetAtPath<AnimationClip>(
                AnimationRoot + "/A_fx_endminf_ui_overview_04.anim");
            Require(rigClip != null && rigClip.legacy,
                "cached exact A_actor_endminf_ui_overview_02 clip is missing");
            Require(sourceRocks != null && sourceRocks.legacy,
                "cached exact A_fx_endminf_ui_overview_04 clip is missing");
            AnimationClip rocksClip = CopyClip(
                sourceRocks,
                CompositeRockClipAsset,
                CompositeRockClipName);
            AddRockVisibilityCurves(rocksClip, rockVisibility);

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

        private static AnimationClip CopyClip(
            AnimationClip source,
            string assetPath,
            string clipName)
        {
            AnimationClip destination = AssetDatabase.LoadAssetAtPath<AnimationClip>(assetPath);
            if (destination == null)
            {
                destination = new AnimationClip();
                AssetDatabase.CreateAsset(destination, assetPath);
            }
            EditorUtility.CopySerialized(source, destination);
            destination.name = clipName;
            destination.legacy = true;
            EditorUtility.SetDirty(destination);
            return destination;
        }

        private static void ValidateRockVisibilitySource(
            Dictionary<string, object> source)
        {
            Require(L.Str(source, "schema") ==
                    "endfield.endminf-overview-rock-visibility.v1" &&
                L.Str(source, "clip") == "A_fx_endminf_ui_overview_03" &&
                Mathf.Abs(L.Float(source, "sampleRate") - 30f) < 0.001f &&
                Mathf.Abs(L.Float(source, "durationSeconds") - 1.5f) < 0.001f,
                "A_fx_endminf_ui_overview_03 identity/timing drifted");

            IList activeCurves = L.List(source["resolvedBindings"]);
            Require(activeCurves.Count == ExpectedRockVisibilityPaths.Length,
                "A_fx_endminf_ui_overview_03 resolved active-curve census drifted");
            var paths = new HashSet<string>(StringComparer.Ordinal);
            foreach (object curveValue in activeCurves)
            {
                Dictionary<string, object> curve = L.Dict(curveValue);
                string sourcePath = L.Str(curve, "path");
                Require(ExpectedRockVisibilityPaths.Contains(sourcePath),
                    "Unexpected resolved rock active curve: " + sourcePath);
                Require(paths.Add(sourcePath),
                    "Duplicate resolved rock active curve: " + sourcePath);
                Require(L.Str(curve, "property") == "m_IsActive",
                    "Rock active property drifted: " + sourcePath);
                Require(Mathf.Abs(L.Float(curve, "initialValue") - 1f) < 1e-6f &&
                    Mathf.Abs(L.Float(curve, "finalValue")) < 1e-6f,
                    "Rock active values drifted: " + sourcePath);
            }
            Require(paths.SetEquals(ExpectedRockVisibilityPaths),
                "Resolved rock active-curve path set drifted");

            IList unresolved = L.List(source["unresolvedBindings"]);
            Require(unresolved.Count == 1,
                "Expected exactly one fail-closed source binding");
            Dictionary<string, object> missing = L.Dict(unresolved[0]);
            Require(L.Str(missing, "type") == "GameObject" &&
                L.Int(missing, "attribute") == GameObjectActiveAttribute &&
                Mathf.Abs(L.Float(missing, "constantValue")) < 1e-6f &&
                L.Str(missing, "policy") == "fail_closed_do_not_fabricate_target",
                "Unresolved constant-zero rock binding contract drifted");
        }

        private static void AddRockVisibilityCurves(
            AnimationClip clip,
            Dictionary<string, object> source)
        {
            float sampleRate = L.Float(source, "sampleRate");
            float duration = L.Float(source, "durationSeconds");
            int sampleCount = Mathf.RoundToInt(duration * sampleRate) + 1;
            IList activeCurves = L.List(source["resolvedBindings"]);
            foreach (object curveValue in activeCurves)
            {
                Dictionary<string, object> curveSource = L.Dict(curveValue);
                string localPath = L.Str(curveSource, "path");
                var curve = new AnimationCurve();
                for (int index = 0; index < sampleCount; index++)
                {
                    curve.AddKey(
                        index / sampleRate,
                        index + 1 == sampleCount ? 0f : 1f);
                }
                for (int index = 0; index < curve.length; index++)
                {
                    AnimationUtility.SetKeyLeftTangentMode(
                        curve, index, AnimationUtility.TangentMode.Constant);
                    AnimationUtility.SetKeyRightTangentMode(
                        curve, index, AnimationUtility.TangentMode.Constant);
                }
                AnimationUtility.SetEditorCurve(
                    clip,
                    EditorCurveBinding.FloatCurve(
                        localPath,
                        typeof(GameObject),
                        "m_IsActive"),
                    curve);
            }
            EditorUtility.SetDirty(clip);
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
            animation.AddClip(clip, clip.name); animation.clip = clip; animation.playAutomatically = true;
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
                rocks.clip.name == CompositeRockClipName,
                "effect_nanguan playback drifted");
            Require(AnimationUtility.GetCurveBindings(rig.clip).Length == 30,
                "effect_01 curve census drifted");
            EditorCurveBinding[] rockBindings =
                AnimationUtility.GetCurveBindings(rocks.clip);
            Require(rockBindings.Length == 32,
                "effect_nanguan curve census drifted");
            string[] activePaths = rockBindings
                .Where(binding => binding.type == typeof(GameObject) &&
                    binding.propertyName == "m_IsActive")
                .Select(binding => binding.path)
                .OrderBy(path => path, StringComparer.Ordinal)
                .ToArray();
            Require(activePaths.SequenceEqual(
                    ExpectedRockVisibilityPaths.OrderBy(
                        path => path, StringComparer.Ordinal)),
                "effect_nanguan active-curve paths drifted");
            foreach (string path in activePaths)
            {
                AnimationCurve curve = AnimationUtility.GetEditorCurve(
                    rocks.clip,
                    EditorCurveBinding.FloatCurve(
                        path, typeof(GameObject), "m_IsActive"));
                Require(curve != null && curve.length == 46 &&
                    Mathf.Abs(curve.Evaluate(0f) - 1f) < 1e-6f &&
                    Mathf.Abs(curve.Evaluate(1.5f)) < 1e-6f,
                    "effect_nanguan active curve values drifted: " + path);
            }
        }

        private static Dictionary<string, object> Load(string repo, string relative)
        {
            string path = Path.Combine(repo, relative.Replace('/', Path.DirectorySeparatorChar));
            Require(File.Exists(path), "missing sampled effect clip: " + path);
            return L.Dict(ManifestMiniJson.Deserialize(File.ReadAllText(path)));
        }
        private static void Require(bool value,string message){if(!value)throw new InvalidOperationException(message);}
    }
}
