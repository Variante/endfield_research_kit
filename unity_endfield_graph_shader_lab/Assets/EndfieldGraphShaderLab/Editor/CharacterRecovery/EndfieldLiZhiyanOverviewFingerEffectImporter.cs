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
using L = EndfieldGraphShaderLabEditor.EndfieldLastRiteOverviewHeadEffectImporter;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Materializes Li Zhiyan's exact finger-mounted Overview particle prefab.
    /// Its source VFXBaseV2 materials remain ColorMask-0 until the retail draw
    /// variant/draw/PSO/MRT contracts are independently admitted.
    /// </summary>
    public static class EndfieldLiZhiyanOverviewFingerEffectImporter
    {
        private const string ContractPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/" +
            "lizhiyan_overview_finger_effect.json";
        private const string GeneratedRoot =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/" +
            "Lizhiyan/Effects/OverviewFinger";
        private const string MaterialRoot = GeneratedRoot + "/Materials";
        private const string PrefabPath = GeneratedRoot +
            "/P_fxui_lizhiyan_overview_trails_Bip001_R_Finger2Nub.prefab";
        private const string FailClosedShaderName =
            "Hidden/Endfield/Recovered/VFXUnavailableFailClosed";
        private const string ExpectedSchema =
            "endfield.lizhiyan-overview-finger-effect.v2";
        private const string ExpectedEffect =
            "P_fxui_lizhiyan_overview_trails_Bip001_R_Finger2Nub";

        [MenuItem("Endfield/Character Recovery Lab/Build Li Zhiyan Overview Finger Effect")]
        public static void BuildAndValidate()
        {
            Dictionary<string, object> contract = L.Dict(
                ManifestMiniJson.Deserialize(File.ReadAllText(
                    L.ProjectAbsolute(ContractPath), Encoding.UTF8)));
            L.Require(L.Str(contract, "schema") == ExpectedSchema &&
                L.Str(contract, "effectName") == ExpectedEffect &&
                L.Str(contract, "mountPoint") == "Bip001_R_Finger2Nub",
                "Li Zhiyan finger-effect contract identity drifted");
            L.EnsureFolder(GeneratedRoot);
            L.EnsureFolder(MaterialRoot);

            Shader failClosed = Shader.Find(FailClosedShaderName);
            L.Require(failClosed != null, "Missing fail-closed VFX shader");
            var context = new EndfieldZhuangfyParticleEffectImporter.Context();
            foreach (object item in L.List(contract["materials"]))
            {
                Dictionary<string, object> source = L.Dict(item);
                long identity = L.Long(source, "pathID");
                string name = L.Str(source, "name");
                L.Require(L.Long(source, "shaderPathID") == -1430105248647086886L,
                    "Li Zhiyan material escaped VFXBaseV2 identity");
                string assetPath = MaterialRoot + "/" + L.Safe(name) + "_p" +
                    unchecked((ulong)identity).ToString("X16", CultureInfo.InvariantCulture) + ".mat";
                Material material = AssetDatabase.LoadAssetAtPath<Material>(assetPath);
                if (material == null)
                {
                    material = new Material(failClosed);
                    AssetDatabase.CreateAsset(material, assetPath);
                }
                material.shader = failClosed;
                material.name = name;
                material.shaderKeywords = Array.Empty<string>();
                material.renderQueue = L.Int(source, "customRenderQueue");
                EditorUtility.SetDirty(material);
                context.materials[identity] = material;
                context.materialNames[identity] = name;
                context.materialShaderPathIds[identity] = -1430105248647086886L;
            }
            L.Require(context.materials.Count == 6, "Li Zhiyan material census drifted");
            Dictionary<string, object> textureBoundary = L.Dict(contract["textureDependencyBoundary"]);
            L.Require(L.Str(textureBoundary, "status") ==
                    "assetmap_converted_png_and_bc7_native_mip_sampling_metadata_closed" &&
                L.List(textureBoundary["uniquePathIDs"]).Count == 8 &&
                L.List(textureBoundary["textures"]).Count == 8 &&
                L.List(textureBoundary["nativePayloads"]).Count == 8,
                "Li Zhiyan texture evidence boundary drifted");

            IList nodeRows = L.List(contract["hierarchyNodes"]);
            var nodesByTransform = new Dictionary<long, GameObject>();
            var sourceByTransform = new Dictionary<long, Dictionary<string, object>>();
            foreach (object item in nodeRows)
            {
                Dictionary<string, object> row = L.Dict(item);
                long transformId = L.Long(row, "transformPathID");
                Dictionary<string, object> gameObject = L.Dict(row["gameObject"]);
                GameObject generated = new GameObject(L.Str(gameObject, "m_Name"));
                generated.layer = L.Int(gameObject, "m_Layer");
                generated.SetActive(L.Bool(gameObject, "m_IsActive"));
                nodesByTransform[transformId] = generated;
                sourceByTransform[transformId] = row;
            }
            foreach (KeyValuePair<long, GameObject> pair in nodesByTransform)
            {
                Dictionary<string, object> transform = L.Dict(sourceByTransform[pair.Key]["transform"]);
                long father = L.PPtrId(transform["m_Father"]);
                if (father != 0)
                {
                    L.Require(nodesByTransform.TryGetValue(father, out GameObject parent),
                        "Li Zhiyan hierarchy parent is absent");
                    pair.Value.transform.SetParent(parent.transform, false);
                }
                pair.Value.transform.localPosition = L.Vector3Value(transform["m_LocalPosition"]);
                pair.Value.transform.localRotation = L.QuaternionValue(transform["m_LocalRotation"]);
                pair.Value.transform.localScale = L.Vector3Value(transform["m_LocalScale"]);
            }
            GameObject root = nodesByTransform.Values.Single(value =>
                value.transform.parent == null && value.name == ExpectedEffect);

            var markerNodes = new List<EndfieldRecoveredParticleNodeSource>();
            foreach (object item in L.List(contract["particlePairs"]))
            {
                Dictionary<string, object> pair = L.Dict(item);
                long gameObjectId = L.Long(pair, "gameObjectPathID");
                Dictionary<string, object> node = nodeRows.Cast<object>().Select(L.Dict)
                    .Single(row => L.Long(row, "gameObjectPathID") == gameObjectId);
                GameObject host = nodesByTransform[L.Long(node, "transformPathID")];
                ParticleSystem system = host.AddComponent<ParticleSystem>();
                ParticleSystemRenderer renderer = system.GetComponent<ParticleSystemRenderer>();
                Dictionary<string, object> systemRecord = L.Dict(pair["particleSystem"]);
                Dictionary<string, object> rendererRecord = L.Dict(pair["renderer"]);
                var systemSerialized = new SerializedObject(system);
                EndfieldZhuangfyParticleEffectImporter.DisableAllKnownModules(systemSerialized);
                EndfieldZhuangfyParticleEffectImporter.ApplyTopLevelDictionary(
                    systemSerialized, L.Dict(systemRecord["fields"]), context,
                    "LiZhiyan.ParticleSystem");
                foreach (KeyValuePair<string, object> module in L.Dict(systemRecord["enabledModules"]))
                    EndfieldZhuangfyParticleEffectImporter.ApplyNamedDictionary(
                        systemSerialized, module.Key, L.Dict(module.Value), context,
                        "LiZhiyan.ParticleSystem." + module.Key);
                systemSerialized.ApplyModifiedPropertiesWithoutUndo();
                var rendererSerialized = new SerializedObject(renderer);
                EndfieldZhuangfyParticleEffectImporter.ApplyTopLevelDictionary(
                    rendererSerialized, L.Dict(rendererRecord["fields"]), context,
                    "LiZhiyan.ParticleSystemRenderer");
                rendererSerialized.ApplyModifiedPropertiesWithoutUndo();
                long[] materialIds = L.PPtrIds(L.Dict(rendererRecord["fields"])["m_Materials"]);
                markerNodes.Add(new EndfieldRecoveredParticleNodeSource
                {
                    hierarchy = L.Str(pair, "hierarchy"),
                    gameObjectPathId = gameObjectId,
                    transformPathId = L.Long(node, "transformPathID"),
                    particleSystemPathId = L.Long(L.Dict(systemRecord["source"]), "pathID"),
                    particleRendererPathId = L.Long(L.Dict(rendererRecord["source"]), "pathID"),
                    materialPathIds = materialIds,
                    meshPathIds = Array.Empty<long>(),
                    shaderNames = materialIds.Select(_ => "HGRP/Effect/VFXBaseV2").ToArray(),
                    shaderPathIds = materialIds.Select(_ => -1430105248647086886L).ToArray(),
                    sourceRendererEnabled = L.Bool(L.Dict(rendererRecord["fields"]), "m_Enabled"),
                    nativeParticlePayloadApplied = true,
                    nativeRendererPayloadApplied = true,
                    rendererFailClosedForUnrecoveredShader = true,
                });
            }

            Dictionary<string, object> timing = L.Dict(L.Dict(contract["effectSetting"])["timing"]);
            var marker = root.AddComponent<EndfieldRecoveredParticleEffectSource>();
            marker.contractSchema = ExpectedSchema;
            marker.effectRoot = ExpectedEffect;
            marker.sourceHierarchy = ExpectedEffect;
            Dictionary<string, object> rootRow = nodeRows.Cast<object>().Select(L.Dict)
                .Single(row => L.Str(row, "hierarchy") == ExpectedEffect);
            marker.sourceGameObjectPathId = L.Long(rootRow, "gameObjectPathID");
            marker.sourceTransformPathId = L.Long(rootRow, "transformPathID");
            marker.sourceEffectLoops = L.Bool(timing, "isLoop");
            marker.sourceEffectDuration = L.Float(timing, "duration");
            marker.sourceEffectDelay = L.Float(timing, "delay");
            marker.materialExecutionBoundary = L.Str(contract, "executionBoundary");
            marker.hierarchyNodes = nodeRows.Cast<object>().Select(item =>
            {
                Dictionary<string, object> row = L.Dict(item);
                long transformId = L.Long(row, "transformPathID");
                return new EndfieldRecoveredParticleHierarchyNodeSource
                {
                    hierarchy = L.Str(row, "hierarchy"),
                    gameObjectPathId = L.Long(row, "gameObjectPathID"),
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
            L.Require(prefab != null, "Generated Li Zhiyan finger effect is missing");
            EndfieldRecoveredParticleEffectSource marker =
                prefab.GetComponent<EndfieldRecoveredParticleEffectSource>();
            L.Require(marker != null && marker.contractSchema == ExpectedSchema &&
                marker.effectRoot == ExpectedEffect && marker.hierarchyNodes.Length == 8 &&
                marker.particleNodes.Length == 7 && marker.particleNodes.All(value =>
                    value.rendererFailClosedForUnrecoveredShader) &&
                Mathf.Approximately(marker.sourceEffectDelay, 0.83333f) &&
                Mathf.Approximately(marker.sourceEffectDuration, 2.33333f) &&
                prefab.GetComponentsInChildren<ParticleSystem>(true).Length == 7 &&
                prefab.GetComponentsInChildren<ParticleSystemRenderer>(true).Length == 7 &&
                prefab.GetComponentsInChildren<Renderer>(true).SelectMany(value =>
                    value.sharedMaterials).All(material => material != null &&
                    material.shader != null && material.shader.name == FailClosedShaderName),
                "Li Zhiyan finger effect admission boundary drifted");
            Debug.Log("[Endfield Li Zhiyan] source-closed finger Overview effect passed: " +
                "8 nodes, 7 particles, delay=0.83333, duration=2.33333, " +
                "all 6 VFXBaseV2 materials fail-closed");
        }
    }
}
