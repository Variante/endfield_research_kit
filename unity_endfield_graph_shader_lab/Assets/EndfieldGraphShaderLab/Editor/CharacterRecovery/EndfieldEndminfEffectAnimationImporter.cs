using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
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
            "ba01b72a7d476b7b8d0e16b806c9e18d8ac07b623d1951f4f0e53f55f5649d1d";

        [MenuItem("Endfield/Character Recovery Lab/Build Endminf Effect Animation")]
        public static void BuildAndValidate()
        {
            Dictionary<string, object> contract = LoadSemanticContract();
            IList clips = L.List(contract["clips"]);
            Dictionary<string, object> rigContract = FindClipContract(
                clips,
                "A_actor_endminf_ui_overview_02");
            Dictionary<string, object> rocksContract = FindClipContract(
                clips,
                EffectNanguanClipName);
            L.EnsureFolder(AnimationRoot);
            AnimationClip rigClip = BuildOrReplaceClip(rigContract);
            AnimationClip rocksClip = BuildOrReplaceClip(rocksContract);
            AssetDatabase.SaveAssets();
            ValidateSemanticClip(rigContract, rigClip, 30, 354);
            ValidateSemanticClip(rocksContract, rocksClip, 28, 263);

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
            Dictionary<string, object> contract = LoadSemanticContract();
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
            IList clips = L.List(contract["clips"]);
            ValidateSemanticClip(
                FindClipContract(clips, "A_actor_endminf_ui_overview_02"),
                rig.clip,
                30,
                354);
            ValidateSemanticClip(
                FindClipContract(clips, EffectNanguanClipName),
                rocks.clip,
                28,
                263);
        }

        private static Dictionary<string, object> LoadSemanticContract()
        {
            string path = ProjectAbsolute(SemanticContract);
            Require(HashFile(path) == SemanticContractSha256,
                "Endminf source-derived rebuildable animation contract drifted");
            Dictionary<string, object> contract = L.Dict(
                ManifestMiniJson.Deserialize(File.ReadAllText(path)));
            Require(
                L.Str(contract, "schema") ==
                    "endfield.endminf-effect-animation-source-curves.v2" &&
                L.Str(contract, "status") ==
                    "source_derived_rebuildable_curve_contract",
                "Endminf rebuildable animation contract schema drifted");
            IList clips = L.List(contract["clips"]);
            Require(clips.Count == 2,
                "Endminf rebuildable animation clip census drifted");
            ValidateClipContract(
                FindClipContract(clips, "A_actor_endminf_ui_overview_02"),
                RigSourceFile,
                RigSourceSha256,
                30,
                354);
            ValidateClipContract(
                FindClipContract(clips, EffectNanguanClipName),
                RocksSourceFile,
                RocksSourceSha256,
                28,
                263);
            return contract;
        }

        private static Dictionary<string, object> FindClipContract(
            IList clips,
            string clipName)
        {
            Dictionary<string, object>[] matches = clips.Cast<object>()
                .Select(L.Dict)
                .Where(row => string.Equals(
                    L.Str(row, "name"), clipName, StringComparison.Ordinal))
                .ToArray();
            Require(matches.Length == 1,
                "Endminf rebuildable animation identity is missing or " +
                "ambiguous: " + clipName);
            return matches[0];
        }

        private static void ValidateClipContract(
            Dictionary<string, object> row,
            string expectedSourceFile,
            string expectedSourceSha256,
            int expectedBindingCount,
            int expectedKeyCount)
        {
            string clipName = L.Str(row, "name");
            Require(
                L.Str(row, "sourceFile") == expectedSourceFile &&
                L.Str(row, "sourceSha256") == expectedSourceSha256 &&
                L.Int(row, "bindingCount") == expectedBindingCount &&
                L.Int(row, "keyCountPerBinding") == expectedKeyCount,
                "Endminf rebuildable animation source identity drifted: " +
                clipName);
            IList times = L.List(row["keyTimes"]);
            Require(times.Count == expectedKeyCount,
                "Endminf rebuildable animation key-time census drifted: " +
                clipName);
            float previous = float.NegativeInfinity;
            foreach (object value in times)
            {
                float time = Convert.ToSingle(value);
                Require(IsFinite(time) && time > previous,
                    "Endminf rebuildable animation key times are invalid: " +
                    clipName);
                previous = time;
            }
            Require(SameFloat(previous, Convert.ToSingle(row["duration"])) &&
                IsFinite(Convert.ToSingle(row["sampleRate"])) &&
                Convert.ToSingle(row["sampleRate"]) > 0f,
                "Endminf rebuildable animation range drifted: " + clipName);
            Dictionary<string, object> settings = L.Dict(row["keySettings"]);
            Require(
                L.Int(settings, "leftTangentMode") == 0 &&
                L.Int(settings, "rightTangentMode") == 0 &&
                L.Int(settings, "weightedMode") == 0 &&
                SameFloat(L.Float(settings, "inWeight"), 1f / 3f) &&
                SameFloat(L.Float(settings, "outWeight"), 1f / 3f),
                "Endminf rebuildable animation key settings drifted: " +
                clipName);
            Dictionary<string, object> transport = L.Dict(row["unityTransport"]);
            Require(L.Bool(transport, "legacy") &&
                !L.Bool(transport, "compressed") &&
                L.Int(transport, "wrapMode") == 0 &&
                L.Bool(transport, "useHighQualityCurve"),
                "Endminf rebuildable animation Unity transport drifted: " +
                clipName);

            IList curves = L.List(row["curves"]);
            Require(curves.Count == expectedBindingCount,
                "Endminf rebuildable animation curve census drifted: " +
                clipName);
            var identities = new HashSet<string>(StringComparer.Ordinal);
            string previousIdentity = null;
            foreach (object curveValue in curves)
            {
                Dictionary<string, object> curve = L.Dict(curveValue);
                string identity = L.Str(curve, "path") + "\0" +
                    L.Str(curve, "propertyName");
                Require(identities.Add(identity) &&
                    (previousIdentity == null || string.CompareOrdinal(
                        previousIdentity, identity) < 0),
                    "Endminf rebuildable animation binding order drifted: " +
                    clipName);
                previousIdentity = identity;
                IList values = L.List(curve["values"]);
                IList inTangents = L.List(curve["inTangents"]);
                IList outTangents = L.List(curve["outTangents"]);
                Require(L.Int(curve, "keyCount") == expectedKeyCount &&
                    values.Count == expectedKeyCount &&
                    inTangents.Count == expectedKeyCount &&
                    outTangents.Count == expectedKeyCount,
                    "Endminf rebuildable animation curve shape drifted: " +
                    clipName + "/" + identity.Replace('\0', '/'));
                Require(HashTimeValues(times, values) ==
                        L.Str(curve, "keyTimeValueSha256") &&
                    HashKeyPayload(
                        times,
                        values,
                        inTangents,
                        outTangents,
                        settings) == L.Str(curve, "keyPayloadSha256"),
                    "Endminf rebuildable animation curve digest drifted: " +
                    clipName + "/" + identity.Replace('\0', '/'));
            }
        }

        private static AnimationClip BuildOrReplaceClip(
            Dictionary<string, object> contract)
        {
            string clipName = L.Str(contract, "name");
            string assetPath = AnimationRoot + "/" + clipName + ".anim";
            AnimationClip clip = AssetDatabase.LoadAssetAtPath<AnimationClip>(
                assetPath);
            if (clip == null)
            {
                clip = new AnimationClip { name = clipName };
                AssetDatabase.CreateAsset(clip, assetPath);
            }
            foreach (EditorCurveBinding binding in
                     AnimationUtility.GetCurveBindings(clip))
                AnimationUtility.SetEditorCurve(clip, binding, null);
            foreach (EditorCurveBinding binding in
                     AnimationUtility.GetObjectReferenceCurveBindings(clip))
                AnimationUtility.SetObjectReferenceCurve(clip, binding, null);

            Dictionary<string, object> transport = L.Dict(
                contract["unityTransport"]);
            clip.name = clipName;
            clip.legacy = L.Bool(transport, "legacy");
            clip.wrapMode = (WrapMode)L.Int(transport, "wrapMode");
            clip.frameRate = Convert.ToSingle(contract["sampleRate"]);
            var serialized = new SerializedObject(clip);
            SerializedProperty compressed = serialized.FindProperty("m_Compressed");
            SerializedProperty highQuality = serialized.FindProperty(
                "m_UseHighQualityCurve");
            Require(compressed != null && highQuality != null,
                "Endminf AnimationClip transport fields are unavailable: " +
                clipName);
            compressed.boolValue = L.Bool(transport, "compressed");
            highQuality.boolValue = L.Bool(
                transport,
                "useHighQualityCurve");
            serialized.ApplyModifiedPropertiesWithoutUndo();

            IList times = L.List(contract["keyTimes"]);
            Dictionary<string, object> settings = L.Dict(
                contract["keySettings"]);
            foreach (object curveValue in L.List(contract["curves"]))
            {
                Dictionary<string, object> row = L.Dict(curveValue);
                IList values = L.List(row["values"]);
                IList inTangents = L.List(row["inTangents"]);
                IList outTangents = L.List(row["outTangents"]);
                var keys = new Keyframe[times.Count];
                for (int index = 0; index < keys.Length; index++)
                {
                    keys[index] = new Keyframe(
                        Convert.ToSingle(times[index]),
                        Convert.ToSingle(values[index]),
                        Convert.ToSingle(inTangents[index]),
                        Convert.ToSingle(outTangents[index]),
                        L.Float(settings, "inWeight"),
                        L.Float(settings, "outWeight")) {
                        weightedMode = (WeightedMode)L.Int(
                            settings,
                            "weightedMode"),
                    };
                }
                var curve = new AnimationCurve(keys);
                for (int index = 0; index < keys.Length; index++)
                {
                    AnimationUtility.SetKeyLeftTangentMode(
                        curve,
                        index,
                        (AnimationUtility.TangentMode)L.Int(
                            settings,
                            "leftTangentMode"));
                    AnimationUtility.SetKeyRightTangentMode(
                        curve,
                        index,
                        (AnimationUtility.TangentMode)L.Int(
                            settings,
                            "rightTangentMode"));
                }
                AnimationUtility.SetEditorCurve(
                    clip,
                    EditorCurveBinding.FloatCurve(
                        L.Str(row, "path"),
                        typeof(Transform),
                        L.Str(row, "propertyName")),
                    curve);
            }
            EditorUtility.SetDirty(clip);
            return clip;
        }

        private static void ValidateSemanticClip(
            Dictionary<string, object> sourceContract,
            AnimationClip clip,
            int expectedBindingCount,
            int expectedKeyCount)
        {
            string clipName = L.Str(sourceContract, "name");
            Dictionary<string, object> transport = L.Dict(
                sourceContract["unityTransport"]);
            Require(clip != null && clip.legacy && clip.name == clipName &&
                SameFloat(clip.frameRate, Convert.ToSingle(
                    sourceContract["sampleRate"])) &&
                SameFloat(clip.length, Convert.ToSingle(
                    sourceContract["duration"])) &&
                (int)clip.wrapMode == L.Int(transport, "wrapMode"),
                "Endminf generated AnimationClip identity/range drifted: " +
                clipName);
            var serialized = new SerializedObject(clip);
            SerializedProperty compressed = serialized.FindProperty(
                "m_Compressed");
            SerializedProperty highQuality = serialized.FindProperty(
                "m_UseHighQualityCurve");
            Require(compressed != null && highQuality != null &&
                compressed.boolValue == L.Bool(transport, "compressed") &&
                highQuality.boolValue == L.Bool(
                    transport,
                    "useHighQualityCurve") &&
                AnimationUtility.GetObjectReferenceCurveBindings(clip).Length == 0,
                "Endminf generated AnimationClip transport drifted: " +
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
            IList expectedTimes = L.List(sourceContract["keyTimes"]);
            Dictionary<string, object> settings = L.Dict(
                sourceContract["keySettings"]);
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
                ValidateExactKeyPayload(
                    curve,
                    expectedTimes,
                    L.List(curveRow["values"]),
                    L.List(curveRow["inTangents"]),
                    L.List(curveRow["outTangents"]),
                    settings,
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
            Keyframe[] keys = curve.keys;
            using (var bytes = new MemoryStream())
            using (var writer = new BinaryWriter(bytes))
            {
                foreach (Keyframe key in keys)
                {
                    WriteFloat(writer, key.time);
                    WriteFloat(writer, key.value);
                }
                writer.Flush();
                return HashBytes(bytes.ToArray());
            }
        }

        private static string HashTimeValues(IList times, IList values)
        {
            Require(times.Count == values.Count,
                "Endminf animation time/value arrays have different lengths");
            using (var bytes = new MemoryStream())
            using (var writer = new BinaryWriter(bytes))
            {
                for (int index = 0; index < times.Count; index++)
                {
                    WriteFloat(writer, Convert.ToSingle(times[index]));
                    WriteFloat(writer, Convert.ToSingle(values[index]));
                }
                writer.Flush();
                return HashBytes(bytes.ToArray());
            }
        }

        private static string HashKeyPayload(
            IList times,
            IList values,
            IList inTangents,
            IList outTangents,
            Dictionary<string, object> settings)
        {
            Require(times.Count == values.Count &&
                times.Count == inTangents.Count &&
                times.Count == outTangents.Count,
                "Endminf animation key payload arrays have different lengths");
            using (var bytes = new MemoryStream())
            using (var writer = new BinaryWriter(bytes))
            {
                for (int index = 0; index < times.Count; index++)
                {
                    WriteFloat(writer, Convert.ToSingle(times[index]));
                    WriteFloat(writer, Convert.ToSingle(values[index]));
                    WriteFloat(writer, Convert.ToSingle(inTangents[index]));
                    WriteFloat(writer, Convert.ToSingle(outTangents[index]));
                    writer.Write(L.Int(settings, "leftTangentMode"));
                    writer.Write(L.Int(settings, "rightTangentMode"));
                    writer.Write(L.Int(settings, "weightedMode"));
                    WriteFloat(writer, L.Float(settings, "inWeight"));
                    WriteFloat(writer, L.Float(settings, "outWeight"));
                }
                writer.Flush();
                return HashBytes(bytes.ToArray());
            }
        }

        private static void ValidateExactKeyPayload(
            AnimationCurve curve,
            IList times,
            IList values,
            IList inTangents,
            IList outTangents,
            Dictionary<string, object> settings,
            string owner)
        {
            Keyframe[] keys = curve.keys;
            Require(keys.Length == times.Count && keys.Length == values.Count &&
                keys.Length == inTangents.Count &&
                keys.Length == outTangents.Count,
                "Endminf generated AnimationClip exact key arrays drifted: " +
                owner);
            for (int index = 0; index < keys.Length; index++)
            {
                Keyframe key = keys[index];
                Require(SameFloat(key.time, Convert.ToSingle(times[index])) &&
                    SameFloat(key.value, Convert.ToSingle(values[index])) &&
                    SameFloat(
                        key.inTangent,
                        Convert.ToSingle(inTangents[index])) &&
                    SameFloat(
                        key.outTangent,
                        Convert.ToSingle(outTangents[index])) &&
                    (int)key.weightedMode ==
                        L.Int(settings, "weightedMode") &&
                    SameFloat(key.inWeight, L.Float(settings, "inWeight")) &&
                    SameFloat(key.outWeight, L.Float(settings, "outWeight")) &&
                    AnimationUtility.GetKeyLeftTangentMode(curve, index) ==
                        (AnimationUtility.TangentMode)L.Int(
                            settings,
                            "leftTangentMode") &&
                    AnimationUtility.GetKeyRightTangentMode(curve, index) ==
                        (AnimationUtility.TangentMode)L.Int(
                            settings,
                            "rightTangentMode"),
                    "Endminf generated AnimationClip exact key payload drifted: " +
                    owner + "[" + index + "]");
            }
        }

        private static void WriteFloat(BinaryWriter writer, float value)
        {
            Require(IsFinite(value),
                "Endminf animation payload contains a non-finite float");
            writer.Write(value == 0f ? 0f : value);
        }

        private static string HashBytes(byte[] value)
        {
            using (SHA256 sha = SHA256.Create())
                return BitConverter.ToString(sha.ComputeHash(value))
                    .Replace("-", string.Empty)
                    .ToLowerInvariant();
        }

        private static bool SameFloat(float left, float right)
        {
            if (!IsFinite(left) || !IsFinite(right)) return false;
            if (left == 0f && right == 0f) return true;
            return BitConverter.ToInt32(BitConverter.GetBytes(left), 0) ==
                BitConverter.ToInt32(BitConverter.GetBytes(right), 0);
        }

        private static bool IsFinite(float value)
        {
            return !float.IsNaN(value) && !float.IsInfinity(value);
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
            string canonicalText = File.ReadAllText(path)
                .Replace("\r\n", "\n")
                .Replace("\r", "\n");
            using (SHA256 sha = SHA256.Create())
                return BitConverter.ToString(
                        sha.ComputeHash(Encoding.UTF8.GetBytes(canonicalText)))
                    .Replace("-", string.Empty)
                    .ToLowerInvariant();
        }
        private static void Require(bool value,string message){if(!value)throw new InvalidOperationException(message);}
    }
}
