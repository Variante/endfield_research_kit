using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEngine;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Materializes the exact serialized hierarchy and component payload for
    /// Last Rite's head-mounted Overview effect. Its six HGRP materials remain
    /// deliberately ColorMask-0 until their binary shader variants close.
    /// </summary>
    public static class EndfieldLastRiteOverviewHeadEffectImporter
    {
        private const string ContractPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/" +
            "lastrite_overview_head_effect.json";
        private const string GeneratedRoot =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/" +
            "Lastrite/Effects/OverviewHead";
        private const string MaterialRoot = GeneratedRoot + "/Materials";
        private const string MeshRoot = GeneratedRoot + "/Meshes";
        private const string PrefabPath = GeneratedRoot +
            "/P_fxui_lastrite_ui_overview_start_01_01.prefab";
        private const string FailClosedShaderName =
            "Hidden/Endfield/Recovered/VFXUnavailableFailClosed";
        private const string ExpectedSchema =
            "endfield.lastrite-overview-head-effect.v2";
        private const string ExpectedEffect =
            "P_fxui_lastrite_ui_overview_start_01_01";

        [MenuItem("Endfield/Character Recovery Lab/Build Last Rite Overview Head Effect")]
        public static void BuildAndValidate()
        {
            Dictionary<string, object> contract = Dict(
                ManifestMiniJson.Deserialize(File.ReadAllText(
                    ProjectAbsolute(ContractPath), Encoding.UTF8)));
            Require(Str(contract, "schema") == ExpectedSchema,
                "Last Rite effect contract schema drifted");
            Require(Str(contract, "effectName") == ExpectedEffect,
                "Last Rite effect identity drifted");
            EnsureFolder(GeneratedRoot);
            EnsureFolder(MaterialRoot);
            EnsureFolder(MeshRoot);

            Shader failClosed = Shader.Find(FailClosedShaderName);
            Require(failClosed != null, "Missing fail-closed VFX shader");
            var context = new EndfieldZhuangfyParticleEffectImporter.Context();
            foreach (object item in List(contract["materials"]))
            {
                Dictionary<string, object> source = Dict(item);
                long identity = Long(source, "pathID");
                string name = Str(source, "name");
                Require(Long(source, "shaderPathID") == -1430105248647086886L,
                    "Last Rite material escaped the exact VFXBaseV2 shader identity");
                string assetPath = MaterialRoot + "/" + Safe(name) + "_p" +
                    unchecked((ulong)identity).ToString("X16", CultureInfo.InvariantCulture) +
                    ".mat";
                Material material = AssetDatabase.LoadAssetAtPath<Material>(assetPath);
                if (material == null)
                {
                    material = new Material(failClosed);
                    AssetDatabase.CreateAsset(material, assetPath);
                }
                material.shader = failClosed;
                material.name = name;
                material.shaderKeywords = Array.Empty<string>();
                material.renderQueue = Int(source, "customRenderQueue");
                EditorUtility.SetDirty(material);
                context.materials[identity] = material;
                context.materialNames[identity] = name;
                context.materialShaderPathIds[identity] = Long(source, "shaderPathID");
            }
            Require(context.materials.Count == 6,
                "Last Rite material dependency census drifted");
            Dictionary<string, object> textureBoundary =
                Dict(contract["textureDependencyBoundary"]);
            Require(Str(textureBoundary, "status") ==
                    "assetmap_identity_and_converted_png_closed_native_mip_payload_pending" &&
                List(textureBoundary["uniquePathIDs"]).Count == 12 &&
                List(textureBoundary["textures"]).Count == 12,
                "Last Rite texture evidence boundary drifted");

            Dictionary<string, object> meshRenderer = Dict(contract["meshRenderer"]);
            Dictionary<string, object> meshSource = Dict(meshRenderer["mesh"]);
            long meshIdentity = Long(meshSource, "pathID");
            string meshName = Str(meshSource, "name");
            string meshAssetPath = MeshRoot + "/" + Safe(meshName) + "_p" +
                unchecked((ulong)meshIdentity).ToString("X16", CultureInfo.InvariantCulture) +
                ".asset";
            context.meshes[meshIdentity] =
                EndfieldZhuangfyParticleEffectImporter.BuildMesh(
                    Dict(meshSource["payload"]), meshAssetPath, meshName,
                    "embedded Last Rite effect contract");

            IList nodeRows = List(contract["hierarchyNodes"]);
            var nodesByTransform = new Dictionary<long, GameObject>();
            var nodeSourceByTransform = new Dictionary<long, Dictionary<string, object>>();
            foreach (object item in nodeRows)
            {
                Dictionary<string, object> row = Dict(item);
                long transformId = Long(row, "transformPathID");
                Dictionary<string, object> gameObject = Dict(row["gameObject"]);
                GameObject generated = new GameObject(Str(gameObject, "m_Name"));
                generated.layer = Int(gameObject, "m_Layer");
                generated.SetActive(Bool(gameObject, "m_IsActive"));
                nodesByTransform[transformId] = generated;
                nodeSourceByTransform[transformId] = row;
            }
            foreach (KeyValuePair<long, GameObject> pair in nodesByTransform)
            {
                Dictionary<string, object> row = nodeSourceByTransform[pair.Key];
                Dictionary<string, object> transform = Dict(row["transform"]);
                long father = PPtrId(transform["m_Father"]);
                if (father != 0)
                {
                    Require(nodesByTransform.TryGetValue(father, out GameObject parent),
                        "Last Rite hierarchy parent is absent");
                    pair.Value.transform.SetParent(parent.transform, false);
                }
                pair.Value.transform.localPosition = Vector3Value(transform["m_LocalPosition"]);
                pair.Value.transform.localRotation = QuaternionValue(transform["m_LocalRotation"]);
                pair.Value.transform.localScale = Vector3Value(transform["m_LocalScale"]);
            }
            GameObject root = nodesByTransform.Values.Single(value =>
                value.transform.parent == null && value.name == ExpectedEffect);

            var markerNodes = new List<EndfieldRecoveredParticleNodeSource>();
            foreach (object item in List(contract["particlePairs"]))
            {
                Dictionary<string, object> pair = Dict(item);
                long gameObjectId = Long(pair, "gameObjectPathID");
                Dictionary<string, object> nodeRow = nodeRows.Cast<object>()
                    .Select(Dict).Single(row => Long(row, "gameObjectPathID") == gameObjectId);
                GameObject host = nodesByTransform[Long(nodeRow, "transformPathID")];
                ParticleSystem system = host.AddComponent<ParticleSystem>();
                ParticleSystemRenderer renderer = system.GetComponent<ParticleSystemRenderer>();
                Dictionary<string, object> systemRecord = Dict(pair["particleSystem"]);
                Dictionary<string, object> rendererRecord = Dict(pair["renderer"]);
                var systemSerialized = new SerializedObject(system);
                EndfieldZhuangfyParticleEffectImporter.DisableAllKnownModules(systemSerialized);
                EndfieldZhuangfyParticleEffectImporter.ApplyTopLevelDictionary(
                    systemSerialized, Dict(systemRecord["fields"]), context,
                    "LastRite.ParticleSystem");
                foreach (KeyValuePair<string, object> module in
                    Dict(systemRecord["enabledModules"]))
                {
                    EndfieldZhuangfyParticleEffectImporter.ApplyNamedDictionary(
                        systemSerialized, module.Key, Dict(module.Value), context,
                        "LastRite.ParticleSystem." + module.Key);
                }
                systemSerialized.ApplyModifiedPropertiesWithoutUndo();
                var rendererSerialized = new SerializedObject(renderer);
                EndfieldZhuangfyParticleEffectImporter.ApplyTopLevelDictionary(
                    rendererSerialized, Dict(rendererRecord["fields"]), context,
                    "LastRite.ParticleSystemRenderer");
                rendererSerialized.ApplyModifiedPropertiesWithoutUndo();
                long[] materialIds = PPtrIds(
                    Dict(rendererRecord["fields"])["m_Materials"]);
                long systemPathId = Long(Dict(systemRecord["source"]), "pathID");
                long rendererPathId = Long(Dict(rendererRecord["source"]), "pathID");
                markerNodes.Add(new EndfieldRecoveredParticleNodeSource
                {
                    hierarchy = Str(pair, "hierarchy"),
                    gameObjectPathId = gameObjectId,
                    transformPathId = Long(nodeRow, "transformPathID"),
                    particleSystemPathId = systemPathId,
                    particleRendererPathId = rendererPathId,
                    materialPathIds = materialIds,
                    meshPathIds = Array.Empty<long>(),
                    shaderNames = materialIds.Select(_ => "HGRP/Effect/VFXBaseV2").ToArray(),
                    shaderPathIds = materialIds.Select(_ => -1430105248647086886L).ToArray(),
                    sourceRendererEnabled = Bool(Dict(rendererRecord["fields"]), "m_Enabled"),
                    nativeParticlePayloadApplied = true,
                    nativeRendererPayloadApplied = true,
                    rendererFailClosedForUnrecoveredShader = true,
                });
            }

            string meshHierarchy = Str(meshRenderer, "hierarchy");
            Dictionary<string, object> meshNode = nodeRows.Cast<object>()
                .Select(Dict).Single(row => Str(row, "hierarchy") == meshHierarchy);
            GameObject meshHost = nodesByTransform[Long(meshNode, "transformPathID")];
            MeshFilter filter = meshHost.AddComponent<MeshFilter>();
            filter.sharedMesh = context.meshes[meshIdentity];
            MeshRenderer generatedMeshRenderer = meshHost.AddComponent<MeshRenderer>();
            var meshRendererSerialized = new SerializedObject(generatedMeshRenderer);
            EndfieldZhuangfyParticleEffectImporter.ApplyTopLevelDictionary(
                meshRendererSerialized, Dict(meshRenderer["rendererFields"]), context,
                "LastRite.MeshRenderer");
            meshRendererSerialized.ApplyModifiedPropertiesWithoutUndo();

            Dictionary<string, object> setting = Dict(contract["effectSetting"]);
            Dictionary<string, object> timing = Dict(setting["timing"]);
            var marker = root.AddComponent<EndfieldRecoveredParticleEffectSource>();
            marker.contractSchema = ExpectedSchema;
            marker.effectRoot = ExpectedEffect;
            marker.sourceHierarchy = ExpectedEffect;
            marker.sourceGameObjectPathId = Long(
                nodeRows.Cast<object>().Select(Dict).Single(row =>
                    Str(row, "hierarchy") == ExpectedEffect), "gameObjectPathID");
            marker.sourceTransformPathId = nodesByTransform.Single(pair =>
                pair.Value == root).Key;
            marker.sourceEffectLoops = Bool(timing, "isLoop");
            marker.sourceEffectDuration = Float(timing, "duration");
            marker.sourceEffectDelay = Float(timing, "delay");
            marker.sourceEffectRandomDelay = Bool(timing, "randomDelay") ? 1f : 0f;
            marker.materialExecutionBoundary = Str(contract, "executionBoundary");
            marker.hierarchyNodes = nodeRows.Cast<object>().Select(item =>
            {
                Dictionary<string, object> row = Dict(item);
                long transformId = Long(row, "transformPathID");
                return new EndfieldRecoveredParticleHierarchyNodeSource
                {
                    hierarchy = Str(row, "hierarchy"),
                    gameObjectPathId = Long(row, "gameObjectPathID"),
                    transformPathId = transformId,
                    generatedTransform = nodesByTransform[transformId].transform,
                };
            }).ToArray();
            marker.particleNodes = markerNodes.ToArray();

            PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
            UnityEngine.Object.DestroyImmediate(root);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            ValidateGenerated();
        }

        private static void ValidateGenerated()
        {
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
            Require(prefab != null, "Generated Last Rite effect prefab is missing");
            EndfieldRecoveredParticleEffectSource marker =
                prefab.GetComponent<EndfieldRecoveredParticleEffectSource>();
            Require(marker != null && marker.contractSchema == ExpectedSchema &&
                marker.effectRoot == ExpectedEffect &&
                marker.hierarchyNodes.Length == 8 &&
                marker.particleNodes.Length == 5 &&
                marker.particleNodes.All(value =>
                    value.rendererFailClosedForUnrecoveredShader) &&
                Mathf.Approximately(marker.sourceEffectDelay, 3.5f) &&
                Mathf.Approximately(marker.sourceEffectDuration, 13.5f),
                "Generated Last Rite source marker drifted");
            Require(prefab.GetComponentsInChildren<ParticleSystem>(true).Length == 5 &&
                prefab.GetComponentsInChildren<ParticleSystemRenderer>(true).Length == 5 &&
                prefab.GetComponentsInChildren<MeshRenderer>(true).Length == 1 &&
                prefab.GetComponentsInChildren<Renderer>(true).SelectMany(value =>
                    value.sharedMaterials).All(material => material != null &&
                    material.shader != null && material.shader.name == FailClosedShaderName),
                "Last Rite generated renderers escaped fail-closed material admission");
            Debug.Log(
                "[Endfield Last Rite] source-closed Overview head effect passed: " +
                "8 nodes, 5 particles, 1 head mesh, delay=3.5, duration=13.5, " +
                "all 6 VFXBaseV2 materials fail-closed");
        }

        internal static void EnsureFolder(string path)
        {
            string[] parts = path.Split('/');
            string current = parts[0];
            for (int index = 1; index < parts.Length; index++)
            {
                string next = current + "/" + parts[index];
                if (!AssetDatabase.IsValidFolder(next))
                    AssetDatabase.CreateFolder(current, parts[index]);
                current = next;
            }
        }

        internal static string ProjectAbsolute(string path) =>
            Path.GetFullPath(Path.Combine(Application.dataPath, "..", path));

        private static string RepoAbsolute(string path) =>
            Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", path));

        internal static string Safe(string value) =>
            string.Concat(value.Select(ch => Path.GetInvalidFileNameChars().Contains(ch) ? '_' : ch));

        internal static Dictionary<string, object> Dict(object value) =>
            value as Dictionary<string, object> ?? throw new InvalidOperationException("Expected object");

        internal static IList List(object value) =>
            value as IList ?? throw new InvalidOperationException("Expected array");

        internal static string Str(Dictionary<string, object> value, string key) =>
            value.TryGetValue(key, out object result) ? Convert.ToString(result, CultureInfo.InvariantCulture) : string.Empty;

        internal static long Long(Dictionary<string, object> value, string key) =>
            value.TryGetValue(key, out object result) ? Convert.ToInt64(result, CultureInfo.InvariantCulture) : 0L;

        internal static int Int(Dictionary<string, object> value, string key) =>
            checked((int)Long(value, key));

        internal static bool Bool(Dictionary<string, object> value, string key) =>
            value.TryGetValue(key, out object result) && Convert.ToBoolean(result, CultureInfo.InvariantCulture);

        internal static float Float(Dictionary<string, object> value, string key) =>
            value.TryGetValue(key, out object result) ? Convert.ToSingle(result, CultureInfo.InvariantCulture) : 0f;

        internal static long PPtrId(object value) =>
            value is Dictionary<string, object> row ? Long(row, "m_PathID") : 0L;

        internal static long[] PPtrIds(object value) =>
            List(value).Cast<object>().Select(PPtrId).Where(identity => identity != 0).ToArray();

        private static float Number(Dictionary<string, object> value, string lower, string upper) =>
            value.TryGetValue(lower, out object result) || value.TryGetValue(upper, out result)
                ? Convert.ToSingle(result, CultureInfo.InvariantCulture) : 0f;

        internal static Vector3 Vector3Value(object value)
        {
            Dictionary<string, object> row = Dict(value);
            return new Vector3(Number(row, "x", "X"), Number(row, "y", "Y"), Number(row, "z", "Z"));
        }

        internal static Quaternion QuaternionValue(object value)
        {
            Dictionary<string, object> row = Dict(value);
            return new Quaternion(Number(row, "x", "X"), Number(row, "y", "Y"),
                Number(row, "z", "Z"), Number(row, "w", "W"));
        }

        internal static void Require(bool value, string message)
        {
            if (!value)
                throw new InvalidOperationException(message);
        }
    }
}
