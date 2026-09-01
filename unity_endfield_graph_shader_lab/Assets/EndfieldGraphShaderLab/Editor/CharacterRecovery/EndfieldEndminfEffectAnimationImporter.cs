using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;
using L = EndfieldGraphShaderLabEditor.EndfieldLastRiteOverviewHeadEffectImporter;

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
        private const string ExactStageRelative =
            "unity_endfield_graph_shader_lab/scratch/character_recovery/" +
            "endminf_external_fx_rig/exact_four_root_stage/AnimationClip";
        private const string RigSourceFile =
            "A_actor_endminf_ui_overview_02_p910F78E15CD34301.json";
        private const string RocksSourceFile =
            "A_fx_endminf_ui_overview_04_pDB8EF20719226683.json";
        private const string RigSourceSha256 =
            "22c191d15ea18dc2d890b9c6e4411e8e2985c6ea5fd6db96263b499e3d86a70d";
        private const string RocksSourceSha256 =
            "220ae359098e5a843afdced4680265e3eead2aba79b926988c5ba46ae6d42e6f";
        private const string SemanticContract =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/" +
            "endminf_effect_animation_source_curve_contract.json";
        private const string SemanticContractSha256 =
            "f44cd823397eaa4e513199dd1d410c11a3268ce168b19d2f1f29d0e851e9ed50";

        [MenuItem("Endfield/Character Recovery Lab/Build Endminf Effect Animation")]
        public static void BuildAndValidate()
        {
            ValidateExactAnimationEvidence();
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
            ValidateExactAnimationEvidence();
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

        private static void ValidateExactAnimationEvidence()
        {
            string repo = Directory.GetParent(Application.dataPath).Parent.FullName;
            string stage = Path.Combine(
                repo,
                ExactStageRelative.Replace(
                    '/',
                    Path.DirectorySeparatorChar));
            Require(HashFile(Path.Combine(stage, RigSourceFile)) ==
                    RigSourceSha256 &&
                HashFile(Path.Combine(stage, RocksSourceFile)) ==
                    RocksSourceSha256,
                "Endminf exact source AnimationClip payload drifted");
            string semanticContractPath = ProjectAbsolute(SemanticContract);
            Require(HashFile(semanticContractPath) == SemanticContractSha256,
                "Endminf source-derived animation semantic contract drifted");
            Dictionary<string, object> contract = L.Dict(
                ManifestMiniJson.Deserialize(File.ReadAllText(
                    semanticContractPath)));
            Require(
                L.Str(contract, "schema") ==
                    "endfield.endminf-effect-animation-source-curves.v1" &&
                L.Str(contract, "status") ==
                    "source_derived_semantic_curve_contract",
                "Endminf animation semantic contract schema drifted");
            IList clips = L.List(contract["clips"]);
            Require(clips.Count == 2,
                "Endminf animation semantic clip census drifted");
            ValidateSemanticClip(
                clips.Cast<object>().Select(L.Dict).Single(row =>
                    L.Str(row, "name") ==
                        "A_actor_endminf_ui_overview_02"),
                RigSourceFile,
                RigSourceSha256,
                30,
                354);
            ValidateSemanticClip(
                clips.Cast<object>().Select(L.Dict).Single(row =>
                    L.Str(row, "name") == EffectNanguanClipName),
                RocksSourceFile,
                RocksSourceSha256,
                28,
                263);
        }

        private static void ValidateSemanticClip(
            Dictionary<string, object> sourceContract,
            string expectedSourceFile,
            string expectedSourceSha256,
            int expectedBindingCount,
            int expectedKeyCount)
        {
            string clipName = L.Str(sourceContract, "name");
            Require(
                L.Str(sourceContract, "sourceFile") == expectedSourceFile &&
                L.Str(sourceContract, "sourceSha256") ==
                    expectedSourceSha256 &&
                L.Int(sourceContract, "bindingCount") ==
                    expectedBindingCount &&
                L.Int(sourceContract, "keyCountPerBinding") ==
                    expectedKeyCount,
                "Endminf source-derived animation row drifted: " + clipName);
            AnimationClip clip = AssetDatabase.LoadAssetAtPath<AnimationClip>(
                AnimationRoot + "/" + clipName + ".anim");
            Require(clip != null && clip.legacy && clip.name == clipName &&
                Mathf.Abs(clip.frameRate - Convert.ToSingle(
                    sourceContract["sampleRate"])) <= 1.0e-6f &&
                Mathf.Abs(clip.length - Convert.ToSingle(
                    sourceContract["duration"])) <= 1.0e-5f,
                "Endminf generated AnimationClip identity/range drifted: " +
                clipName);

            EditorCurveBinding[] bindings =
                AnimationUtility.GetCurveBindings(clip);
            Require(bindings.Length == expectedBindingCount &&
                bindings.All(binding => binding.type == typeof(Transform)) &&
                bindings.Select(BindingKey).Distinct(StringComparer.Ordinal)
                    .Count() == bindings.Length,
                "Endminf generated AnimationClip binding set drifted: " +
                clipName);
            Dictionary<string, EditorCurveBinding> bindingByKey =
                bindings.ToDictionary(
                    BindingKey,
                    binding => binding,
                    StringComparer.Ordinal);
            IList expectedCurves = L.List(sourceContract["curves"]);
            Require(expectedCurves.Count == bindings.Length,
                "Endminf source-derived curve census drifted: " + clipName);
            var consumed = new HashSet<string>(StringComparer.Ordinal);
            foreach (object curveValue in expectedCurves)
            {
                Dictionary<string, object> curveRow = L.Dict(curveValue);
                string key = L.Str(curveRow, "path") + "\0" +
                    L.Str(curveRow, "propertyName");
                EditorCurveBinding binding = default(EditorCurveBinding);
                bool hasSourceBinding = consumed.Add(key) &&
                    bindingByKey.TryGetValue(key, out binding);
                Require(hasSourceBinding,
                    "Endminf generated AnimationClip lost source binding: " +
                    clipName + "/" + key.Replace('\0', '/'));
                AnimationCurve curve = AnimationUtility.GetEditorCurve(
                    clip,
                    binding);
                Require(curve != null &&
                    curve.length == L.Int(curveRow, "keyCount") &&
                    curve.length == expectedKeyCount &&
                    HashCurveTimeValues(curve) ==
                        L.Str(curveRow, "keyTimeValueSha256"),
                    "Endminf generated AnimationClip key time/value drifted: " +
                    clipName + "/" + key.Replace('\0', '/'));
                ValidateSourceDerivedTangents(
                    curve,
                    clipName + "/" + key.Replace('\0', '/'));
            }
            Require(consumed.Count == bindings.Length,
                "Endminf generated AnimationClip gained an extra binding: " +
                clipName);
        }

        private static string BindingKey(EditorCurveBinding binding)
        {
            return binding.path + "\0" + binding.propertyName;
        }

        private static string HashCurveTimeValues(AnimationCurve curve)
        {
            using (var bytes = new MemoryStream())
            using (var writer = new BinaryWriter(bytes))
            {
                foreach (Keyframe key in curve.keys)
                {
                    writer.Write(key.time == 0f ? 0f : key.time);
                    writer.Write(key.value == 0f ? 0f : key.value);
                }
                writer.Flush();
                using (SHA256 sha = SHA256.Create())
                    return BitConverter.ToString(
                            sha.ComputeHash(bytes.ToArray()))
                        .Replace("-", string.Empty)
                        .ToLowerInvariant();
            }
        }

        private static void ValidateSourceDerivedTangents(
            AnimationCurve curve,
            string owner)
        {
            Keyframe[] keys = curve.keys;
            for (int index = 0; index < keys.Length; index++)
            {
                int left = Math.Max(0, index - 1);
                int right = Math.Min(keys.Length - 1, index + 1);
                float deltaTime = keys[right].time - keys[left].time;
                float expected = Mathf.Abs(deltaTime) <= 1.0e-12f
                    ? 0f
                    : (keys[right].value - keys[left].value) /
                        deltaTime;
                Keyframe key = keys[index];
                Require(NearlyTangent(key.inTangent, expected) &&
                    NearlyTangent(key.outTangent, expected) &&
                    key.weightedMode == WeightedMode.None &&
                    NearlyTangent(key.inWeight, 1f / 3f) &&
                    NearlyTangent(key.outWeight, 1f / 3f) &&
                    AnimationUtility.GetKeyLeftTangentMode(curve, index) ==
                        AnimationUtility.TangentMode.Free &&
                    AnimationUtility.GetKeyRightTangentMode(curve, index) ==
                        AnimationUtility.TangentMode.Free,
                    "Endminf generated AnimationClip tangent/weight drifted: " +
                    owner + "[" + index + "]");
            }
        }

        private static bool NearlyTangent(float actual, float expected)
        {
            return !float.IsNaN(actual) && !float.IsInfinity(actual) &&
                !float.IsNaN(expected) && !float.IsInfinity(expected) &&
                Mathf.Abs(actual - expected) <= Mathf.Max(
                    2.0e-5f,
                    Mathf.Abs(expected) * 2.0e-4f);
        }

        private static string ProjectAbsolute(string assetPath)
        {
            return Path.Combine(
                Directory.GetParent(Application.dataPath).FullName,
                assetPath.Replace('/', Path.DirectorySeparatorChar));
        }

        private static string HashFile(string path)
        {
            Require(File.Exists(path),
                "Missing exact Endminf animation evidence: " + path);
            using (SHA256 sha = SHA256.Create())
                return BitConverter.ToString(
                        sha.ComputeHash(File.ReadAllBytes(path)))
                    .Replace("-", string.Empty)
                    .ToLowerInvariant();
        }
        private static void Require(bool value,string message){if(!value)throw new InvalidOperationException(message);}
    }
}
