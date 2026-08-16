using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEngine;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Materializes the three Li Zhiyan Overview peak particle roots recovered
    /// from the serialized VFS objects.  The source hierarchy, particle
    /// modules, renderer material arrays, and renderer mesh slots are copied
    /// exactly.  Materials deliberately stay on the fail-closed shader: this
    /// importer does not admit a retail shader variant or draw contract.
    /// </summary>
    public static class EndfieldLiZhiyanOverviewPeakParticleEffectImporter
    {
        internal const string ContractPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/" +
            "lizhiyan_overview_peak_particle_effects.json";
        internal const string GeneratedRoot =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/" +
            "Lizhiyan/Effects/OverviewPeakParticles";
        private const string MaterialRoot = GeneratedRoot + "/Materials";
        internal const string DiagnosticMaterialRoot = GeneratedRoot + "/DiagnosticMaterials";
        private const string MeshRoot = GeneratedRoot + "/Meshes";
        private const string TextureRoot = GeneratedRoot + "/Textures";
        private const string FailClosedShaderName =
            "Hidden/Endfield/Recovered/VFXUnavailableFailClosed";
        private const string DiagnosticShaderName =
            "Endfield/Recovered/VFXBaseV2SampleStack";
        private const string ExpectedSchema =
            "endfield.lizhiyan-overview-peak-particle-effects.v1";
        private const long ExpectedVfxBaseV2Shader = -1430105248647086886L;

        [MenuItem("Endfield/Character Recovery Lab/Build Li Zhiyan Overview Peak Particle Effects")]
        public static void BuildAndValidate()
        {
            Dictionary<string, object> contract = LoadContract();
            Shader failClosed = Shader.Find(FailClosedShaderName);
            Require(failClosed != null, "Missing fail-closed VFX shader " + FailClosedShaderName);
            EnsureFolder(GeneratedRoot);
            EnsureFolder(MaterialRoot);
            EnsureFolder(DiagnosticMaterialRoot);
            EnsureFolder(MeshRoot);
            EnsureFolder(TextureRoot);
            EndfieldZhuangfyParticleEffectImporter.Context context =
                BuildDependencies(contract, failClosed);

            foreach (object item in List(contract["effects"]))
                BuildEffect(Dict(item), contract, context);

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            ValidateGenerated(contract, context);
        }

        [MenuItem("Endfield/Character Recovery Lab/Validate Li Zhiyan Overview Peak Particle Effects")]
        public static void ValidateBatch()
        {
            Dictionary<string, object> contract = LoadContract();
            Shader failClosed = Shader.Find(FailClosedShaderName);
            Require(failClosed != null, "Missing fail-closed VFX shader " + FailClosedShaderName);
            EndfieldZhuangfyParticleEffectImporter.Context context =
                LoadGeneratedDependencies(contract, failClosed);
            ValidateGenerated(contract, context);
        }

        internal static string PrefabPath(string effectName) =>
            GeneratedRoot + "/" + effectName + ".prefab";

        internal static string DiagnosticMaterialPath(string name, long pathId) =>
            DiagnosticMaterialRoot + "/" + Safe(name) + "_p" +
            unchecked((ulong)pathId).ToString("X16", CultureInfo.InvariantCulture) + ".mat";

        private static Dictionary<string, object> LoadContract()
        {
            string absolute = ProjectAbsolute(ContractPath);
            Require(File.Exists(absolute), "Missing peak-particle contract " + absolute);
            Dictionary<string, object> contract = Dict(ManifestMiniJson.Deserialize(
                File.ReadAllText(absolute, Encoding.UTF8)));
            Require(Str(contract, "schema") == ExpectedSchema,
                "Li Zhiyan peak-particle contract schema drifted");
            Require(Str(contract, "status") ==
                "serialized_hierarchy_particle_material_texture_mesh_closed_visual_shader_fail_closed",
                "Li Zhiyan peak-particle contract status changed without importer review");
            Dictionary<string, object> summary = Dict(contract["summary"]);
            Require(Int(summary, "effects") == 3 &&
                Int(summary, "hierarchyNodes") == 17 &&
                Int(summary, "particlePairs") == 14 &&
                Int(summary, "materials") == 8 &&
                Int(summary, "uniqueTextures") == 13 &&
                Int(summary, "meshes") == 3,
                "Li Zhiyan peak-particle contract census drifted");
            Require(List(contract["effects"]).Count == 3 &&
                List(contract["materials"]).Count == 8 &&
                List(contract["textures"]).Count == 13 &&
                List(contract["meshes"]).Count == 3,
                "Li Zhiyan peak-particle dependency census drifted");
            Dictionary<string, object> shader = Dict(contract["shader"]);
            Require(Long(shader, "pathID") == ExpectedVfxBaseV2Shader &&
                Str(shader, "name") == "HGRP/Effect/VFXBaseV2",
                "Li Zhiyan peak-particle shader identity drifted");
            ValidateContractRows(contract);
            return contract;
        }

        private static void ValidateContractRows(Dictionary<string, object> contract)
        {
            var materialIds = new HashSet<long>();
            foreach (object item in List(contract["materials"]))
            {
                Dictionary<string, object> material = Dict(item);
                long id = Long(material, "pathID");
                Require(id != 0 && materialIds.Add(id), "Duplicate peak material PathID " + id);
                Require(Long(material, "shaderPathID") == ExpectedVfxBaseV2Shader,
                    "Peak material escaped VFXBaseV2 identity " + id);
            }
            var meshIds = new HashSet<long>();
            foreach (object item in List(contract["meshes"]))
            {
                Dictionary<string, object> mesh = Dict(item);
                long id = Long(mesh, "pathID");
                Require(id != 0 && meshIds.Add(id), "Duplicate peak mesh PathID " + id);
                ValidateArtifact(Dict(mesh["convertedObj"]), "mesh " + id);
            }
            var textureIds = new HashSet<long>();
            foreach (object item in List(contract["textures"]))
            {
                Dictionary<string, object> texture = Dict(item);
                long id = Long(texture, "pathID");
                Require(id != 0 && textureIds.Add(id), "Duplicate peak texture PathID " + id);
                ValidateArtifact(Dict(texture["convertedPng"]), "texture " + id);
            }

            var nodeIds = new HashSet<long>();
            int nodeCount = 0;
            int pairCount = 0;
            foreach (object effectItem in List(contract["effects"]))
            {
                Dictionary<string, object> effect = Dict(effectItem);
                Require(Str(effect, "effectName").Length != 0 &&
                    Long(effect, "rootGameObjectPathID") != 0 &&
                    Long(effect, "lodComponentPathID") != 0,
                    "Peak effect root identity is incomplete");
                IList nodes = List(effect["hierarchyNodes"]);
                IList pairs = List(effect["particlePairs"]);
                Require(nodes.Count > 0 && pairs.Count > 0,
                    "Peak effect has no serialized hierarchy or particles");
                var effectGameObjects = new HashSet<long>();
                foreach (object nodeItem in nodes)
                {
                    Dictionary<string, object> node = Dict(nodeItem);
                    long transform = Long(node, "transformPathID");
                    long gameObject = Long(node, "gameObjectPathID");
                    Require(transform != 0 && gameObject != 0 && nodeIds.Add(transform) &&
                        effectGameObjects.Add(gameObject), "Peak hierarchy identity is not unique");
                    nodeCount++;
                }
                foreach (object pairItem in pairs)
                {
                    Dictionary<string, object> pair = Dict(pairItem);
                    long gameObject = Long(pair, "gameObjectPathID");
                    Dictionary<string, object> system = Dict(pair["particleSystem"]);
                    Dictionary<string, object> renderer = Dict(pair["renderer"]);
                    Require(effectGameObjects.Contains(gameObject),
                        "Peak particle host is absent from hierarchy");
                    Require(Long(Dict(system["source"]), "pathID") != 0 &&
                        Long(Dict(renderer["source"]), "pathID") != 0,
                        "Peak particle component PathID is missing");
                    long[] materialRefs = PPtrIds(Dict(renderer["fields"])["m_Materials"]);
                    Require(materialRefs.Length > 0 && materialRefs.All(materialIds.Contains),
                        "Peak renderer material ownership is unresolved");
                    long[] meshRefs = new[]
                    {
                        PPtrId(Dict(renderer["fields"])["m_Mesh"]),
                        PPtrId(Dict(renderer["fields"])["m_Mesh1"]),
                        PPtrId(Dict(renderer["fields"])["m_Mesh2"]),
                        PPtrId(Dict(renderer["fields"])["m_Mesh3"]),
                    };
                    Require(meshRefs.All(id => id == 0 || meshIds.Contains(id)),
                        "Peak renderer mesh ownership is unresolved");
                    pairCount++;
                }
            }
            Require(nodeCount == 17 && pairCount == 14,
                "Peak hierarchy/particle census does not match summary");
        }

        private static EndfieldZhuangfyParticleEffectImporter.Context BuildDependencies(
            Dictionary<string, object> contract, Shader failClosed)
        {
            var context = new EndfieldZhuangfyParticleEffectImporter.Context();
            Shader diagnostic = Shader.Find(DiagnosticShaderName);
            Require(diagnostic != null, "Missing diagnostic VFXBaseV2 SampleStack shader");
            foreach (object item in List(contract["textures"]))
            {
                Dictionary<string, object> source = Dict(item);
                long id = Long(source, "pathID");
                Dictionary<string, object> artifact = Dict(source["convertedPng"]);
                string repoPath = Str(artifact, "path");
                string assetPath = TextureRoot + "/Texture_p" +
                    unchecked((ulong)id).ToString("X16", CultureInfo.InvariantCulture) + ".png";
                CopyIfDifferent(RepositoryAbsolute(repoPath), ProjectAbsolute(assetPath));
                AssetDatabase.ImportAsset(assetPath, ImportAssetOptions.ForceSynchronousImport);
                Texture2D texture = AssetDatabase.LoadAssetAtPath<Texture2D>(assetPath);
                Require(texture != null, "Unity did not import peak texture " + id);
                context.textures[id] = texture;
            }
            foreach (object item in List(contract["materials"]))
            {
                Dictionary<string, object> source = Dict(item);
                long id = Long(source, "pathID");
                string assetPath = MaterialRoot + "/" + Safe(Str(source, "name")) + "_p" +
                    unchecked((ulong)id).ToString("X16", CultureInfo.InvariantCulture) + ".mat";
                Material material = AssetDatabase.LoadAssetAtPath<Material>(assetPath);
                if (material == null)
                {
                    material = new Material(failClosed);
                    AssetDatabase.CreateAsset(material, assetPath);
                }
                material.shader = failClosed;
                material.shaderKeywords = Array.Empty<string>();
                material.name = Str(source, "name");
                material.renderQueue = Int(source, "customRenderQueue");
                EditorUtility.SetDirty(material);
                context.materials[id] = material;
                context.materialNames[id] = material.name;
                context.materialShaderPathIds[id] = Long(source, "shaderPathID");
                context.materialSources[id] = Dict(source["payload"]);
                string diagnosticPath = DiagnosticMaterialPath(Str(source, "name"), id);
                Material diagnosticMaterial = AssetDatabase.LoadAssetAtPath<Material>(diagnosticPath);
                if (diagnosticMaterial == null)
                {
                    diagnosticMaterial = new Material(diagnostic);
                    AssetDatabase.CreateAsset(diagnosticMaterial, diagnosticPath);
                }
                diagnosticMaterial.shader = diagnostic;
                diagnosticMaterial.name = Str(source, "name") + ".DiagnosticSampleStack";
                EndfieldZhuangfyParticleEffectImporter.ApplyRecoveredMaterialPayload(
                    diagnosticMaterial, Dict(source["payload"]), context);
                diagnosticMaterial.renderQueue = Int(source, "customRenderQueue");
                if (diagnosticMaterial.HasProperty("_UseSoftBlend"))
                    diagnosticMaterial.SetFloat("_UseSoftBlend", 0f);
                EditorUtility.SetDirty(diagnosticMaterial);
            }
            foreach (object item in List(contract["meshes"]))
            {
                Dictionary<string, object> source = Dict(item);
                long id = Long(source, "pathID");
                string name = Str(Dict(source["convertedObj"]), "path");
                string assetPath = MeshRoot + "/" + Safe(Path.GetFileNameWithoutExtension(name)) + ".obj";
                context.meshes[id] = ImportMesh(name, assetPath, Str(source, "name"));
            }
            Require(context.materials.Count == 8 && context.meshes.Count == 3 &&
                context.textures.Count == 13,
                "Peak generated dependency census drifted");
            return context;
        }

        private static EndfieldZhuangfyParticleEffectImporter.Context LoadGeneratedDependencies(
            Dictionary<string, object> contract, Shader failClosed)
        {
            var context = new EndfieldZhuangfyParticleEffectImporter.Context();
            foreach (object item in List(contract["materials"]))
            {
                Dictionary<string, object> source = Dict(item);
                long id = Long(source, "pathID");
                string assetPath = MaterialRoot + "/" + Safe(Str(source, "name")) + "_p" +
                    unchecked((ulong)id).ToString("X16", CultureInfo.InvariantCulture) + ".mat";
                Material material = AssetDatabase.LoadAssetAtPath<Material>(assetPath);
                Require(material != null && material.shader == failClosed,
                    "Peak fail-closed material is missing or escaped: " + assetPath);
                context.materials[id] = material;
                context.materialNames[id] = material.name;
                context.materialShaderPathIds[id] = Long(source, "shaderPathID");
            }
            foreach (object item in List(contract["meshes"]))
            {
                Dictionary<string, object> source = Dict(item);
                long id = Long(source, "pathID");
                string sourcePath = Str(Dict(source["convertedObj"]), "path");
                string assetPath = MeshRoot + "/" + Safe(Path.GetFileNameWithoutExtension(sourcePath)) + ".obj";
                Mesh mesh = AssetDatabase.LoadAllAssetsAtPath(assetPath).OfType<Mesh>().FirstOrDefault();
                Require(mesh != null, "Peak generated mesh is missing: " + assetPath);
                context.meshes[id] = mesh;
            }
            Require(context.materials.Count == 8 && context.meshes.Count == 3,
                "Peak generated dependency census drifted");
            return context;
        }

        private static Mesh ImportMesh(string repoRelativePath, string assetPath, string expectedName)
        {
            string source = RepositoryAbsolute(repoRelativePath);
            Require(File.Exists(source), "Missing converted peak mesh " + source);
            string destination = ProjectAbsolute(assetPath);
            Directory.CreateDirectory(Path.GetDirectoryName(destination));
            if (!File.Exists(destination) || Sha256(source) != Sha256(destination))
                File.Copy(source, destination, true);
            AssetDatabase.ImportAsset(assetPath, ImportAssetOptions.ForceSynchronousImport);
            Mesh mesh = AssetDatabase.LoadAllAssetsAtPath(assetPath).OfType<Mesh>()
                .FirstOrDefault(value => value.name == expectedName) ??
                AssetDatabase.LoadAllAssetsAtPath(assetPath).OfType<Mesh>().FirstOrDefault();
            Require(mesh != null, "Converted peak OBJ did not import a Mesh: " + assetPath);
            return mesh;
        }

        private static void BuildEffect(Dictionary<string, object> effect,
            Dictionary<string, object> contract,
            EndfieldZhuangfyParticleEffectImporter.Context context)
        {
            string effectName = Str(effect, "effectName");
            IList nodeRows = List(effect["hierarchyNodes"]);
            var objects = new Dictionary<long, GameObject>();
            var sources = new Dictionary<long, Dictionary<string, object>>();
            foreach (object item in nodeRows)
            {
                Dictionary<string, object> row = Dict(item);
                long transformId = Long(row, "transformPathID");
                Dictionary<string, object> go = Dict(row["gameObject"]);
                GameObject generated = new GameObject(Str(go, "m_Name"));
                generated.layer = Int(go, "m_Layer");
                // AnimeStudio's GameObject convenience JSON for these three
                // filtered roots omits m_IsActive. Runtime EffectLodCfg.Play
                // owns activation, so the manual diagnostic prefab defaults
                // the omitted state to active without claiming retail timing.
                generated.SetActive(!go.ContainsKey("m_IsActive") || Bool(go, "m_IsActive"));
                objects.Add(transformId, generated);
                sources.Add(transformId, row);
            }
            foreach (KeyValuePair<long, GameObject> item in objects)
            {
                Dictionary<string, object> transform = Dict(sources[item.Key]["transform"]);
                long parentId = PPtrId(transform["m_Father"]);
                if (parentId != 0)
                {
                    Require(objects.TryGetValue(parentId, out GameObject parent),
                        "Peak hierarchy parent is absent at " + effectName);
                    item.Value.transform.SetParent(parent.transform, false);
                }
                item.Value.transform.localPosition = Vector3Value(transform["m_LocalPosition"]);
                item.Value.transform.localRotation = QuaternionValue(transform["m_LocalRotation"]);
                item.Value.transform.localScale = Vector3Value(transform["m_LocalScale"]);
            }
            GameObject root = objects.Values.Single(value => value.transform.parent == null &&
                value.name == effectName);
            var markerNodes = new List<EndfieldRecoveredParticleNodeSource>();
            foreach (object item in List(effect["particlePairs"]))
            {
                Dictionary<string, object> pair = Dict(item);
                long gameObjectId = Long(pair, "gameObjectPathID");
                Dictionary<string, object> row = nodeRows.Cast<object>().Select(Dict)
                    .Single(value => Long(value, "gameObjectPathID") == gameObjectId);
                GameObject host = objects[Long(row, "transformPathID")];
                ParticleSystem system = host.AddComponent<ParticleSystem>();
                ParticleSystemRenderer renderer = system.GetComponent<ParticleSystemRenderer>();
                Dictionary<string, object> sourceSystem = Dict(pair["particleSystem"]);
                Dictionary<string, object> sourceRenderer = Dict(pair["renderer"]);
                var systemSerialized = new SerializedObject(system);
                EndfieldZhuangfyParticleEffectImporter.DisableAllKnownModules(systemSerialized);
                EndfieldZhuangfyParticleEffectImporter.ApplyTopLevelDictionary(
                    systemSerialized, Dict(sourceSystem["fields"]), context,
                    "LiZhiyan.Peak." + effectName + ".ParticleSystem");
                foreach (KeyValuePair<string, object> module in Dict(sourceSystem["enabledModules"]))
                    EndfieldZhuangfyParticleEffectImporter.ApplyNamedDictionary(
                        systemSerialized, module.Key, Dict(module.Value), context,
                        "LiZhiyan.Peak." + effectName + "." + module.Key);
                systemSerialized.ApplyModifiedPropertiesWithoutUndo();
                var rendererSerialized = new SerializedObject(renderer);
                EndfieldZhuangfyParticleEffectImporter.ApplyTopLevelDictionary(
                    rendererSerialized, Dict(sourceRenderer["fields"]), context,
                    "LiZhiyan.Peak." + effectName + ".ParticleSystemRenderer");
                rendererSerialized.ApplyModifiedPropertiesWithoutUndo();
                Dictionary<string, object> rendererFields = Dict(sourceRenderer["fields"]);
                long[] materialIds = PPtrIds(rendererFields["m_Materials"]);
                long[] meshIds = new[]
                {
                    PPtrId(rendererFields["m_Mesh"]), PPtrId(rendererFields["m_Mesh1"]),
                    PPtrId(rendererFields["m_Mesh2"]), PPtrId(rendererFields["m_Mesh3"]),
                };
                markerNodes.Add(new EndfieldRecoveredParticleNodeSource
                {
                    hierarchy = Str(pair, "hierarchy"),
                    gameObjectPathId = gameObjectId,
                    transformPathId = Long(row, "transformPathID"),
                    particleSystemPathId = Long(Dict(sourceSystem["source"]), "pathID"),
                    particleRendererPathId = Long(Dict(sourceRenderer["source"]), "pathID"),
                    materialPathIds = materialIds,
                    meshPathIds = meshIds.Where(id => id != 0).ToArray(),
                    shaderNames = materialIds.Select(_ => "HGRP/Effect/VFXBaseV2").ToArray(),
                    shaderPathIds = materialIds.Select(_ => ExpectedVfxBaseV2Shader).ToArray(),
                    sourceRendererEnabled = Bool(rendererFields, "m_Enabled"),
                    nativeParticlePayloadApplied = true,
                    nativeRendererPayloadApplied = true,
                    rendererFailClosedForUnrecoveredShader = true,
                });
            }
            Dictionary<string, object> timing = Dict(Dict(effect["lodComponent"])["effectLogicCfg"]);
            Dictionary<string, object> rootRow = nodeRows.Cast<object>().Select(Dict)
                .Single(row => Str(row, "hierarchy") == effectName);
            var marker = root.AddComponent<EndfieldRecoveredParticleEffectSource>();
            marker.contractSchema = ExpectedSchema;
            marker.effectRoot = effectName;
            marker.sourceHierarchy = effectName;
            marker.sourceGameObjectPathId = Long(rootRow, "gameObjectPathID");
            marker.sourceTransformPathId = Long(rootRow, "transformPathID");
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
                    generatedTransform = objects[transformId].transform,
                };
            }).ToArray();
            marker.particleNodes = markerNodes.ToArray();
            string prefabPath = GeneratedRoot + "/" + effectName + ".prefab";
            PrefabUtility.SaveAsPrefabAsset(root, prefabPath);
            UnityEngine.Object.DestroyImmediate(root);
        }

        private static void ValidateGenerated(Dictionary<string, object> contract,
            EndfieldZhuangfyParticleEffectImporter.Context context)
        {
            int roots = 0;
            int hierarchy = 0;
            int particles = 0;
            foreach (object item in List(contract["effects"]))
            {
                Dictionary<string, object> effect = Dict(item);
                string effectName = Str(effect, "effectName");
                string prefabPath = GeneratedRoot + "/" + effectName + ".prefab";
                GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
                Require(prefab != null, "Missing generated peak prefab " + prefabPath);
                EndfieldRecoveredParticleEffectSource marker =
                    prefab.GetComponent<EndfieldRecoveredParticleEffectSource>();
                Require(marker != null && marker.contractSchema == ExpectedSchema &&
                    marker.effectRoot == effectName && marker.hierarchyNodes.Length ==
                    List(effect["hierarchyNodes"]).Count && marker.particleNodes.Length ==
                    List(effect["particlePairs"]).Count && marker.particleNodes.All(value =>
                        value.rendererFailClosedForUnrecoveredShader),
                    "Peak source marker census drifted at " + effectName);
                Dictionary<string, object> timing = Dict(Dict(effect["lodComponent"])["effectLogicCfg"]);
                Require(Mathf.Approximately(marker.sourceEffectDuration, Float(timing, "duration")) &&
                    Mathf.Approximately(marker.sourceEffectDelay, Float(timing, "delay")),
                    "Peak timing marker drifted at " + effectName);

                Dictionary<string, object>[] rows = List(effect["hierarchyNodes"]).Cast<object>()
                    .Select(Dict).ToArray();
                foreach (Dictionary<string, object> row in rows)
                {
                    EndfieldRecoveredParticleHierarchyNodeSource node = marker.hierarchyNodes
                        .Single(value => value.transformPathId == Long(row, "transformPathID"));
                    Dictionary<string, object> transform = Dict(row["transform"]);
                    Require(node.generatedTransform != null &&
                        Nearly(node.generatedTransform.localPosition, Vector3Value(transform["m_LocalPosition"])) &&
                        Nearly(node.generatedTransform.localRotation, QuaternionValue(transform["m_LocalRotation"])) &&
                        Nearly(node.generatedTransform.localScale, Vector3Value(transform["m_LocalScale"])),
                        "Peak hierarchy TRS drifted at " + Str(row, "hierarchy"));
                }
                foreach (object pairItem in List(effect["particlePairs"]))
                {
                    Dictionary<string, object> pair = Dict(pairItem);
                    EndfieldRecoveredParticleNodeSource markerNode = marker.particleNodes.Single(
                        value => value.gameObjectPathId == Long(pair, "gameObjectPathID"));
                    Transform host = markerNode == null ? null : marker.hierarchyNodes.Single(
                        value => value.transformPathId == markerNode.transformPathId).generatedTransform;
                    Require(host != null, "Peak particle host transform is missing");
                    ParticleSystem system = host.GetComponent<ParticleSystem>();
                    ParticleSystemRenderer renderer = host.GetComponent<ParticleSystemRenderer>();
                    Require(system != null && renderer != null && renderer.sharedMaterials.Length ==
                        markerNode.materialPathIds.Length && renderer.sharedMaterials.All(value =>
                            value != null && value.shader == Shader.Find(FailClosedShaderName)),
                        "Peak renderer fail-closed/material census drifted at " + markerNode.hierarchy);
                    Dictionary<string, object> rendererFields = Dict(Dict(pair["renderer"])["fields"]);
                    long[] expectedMaterials = PPtrIds(rendererFields["m_Materials"]);
                    Require(expectedMaterials.SequenceEqual(markerNode.materialPathIds) &&
                        expectedMaterials.All(id => context.materials.ContainsKey(id)),
                        "Peak renderer material PathID ownership drifted at " + markerNode.hierarchy);
                    long[] expectedMeshes = new[]
                    {
                        PPtrId(rendererFields["m_Mesh"]), PPtrId(rendererFields["m_Mesh1"]),
                        PPtrId(rendererFields["m_Mesh2"]), PPtrId(rendererFields["m_Mesh3"]),
                    };
                    Require(expectedMeshes.Where(id => id != 0).SequenceEqual(markerNode.meshPathIds),
                        "Peak renderer mesh PathID marker drifted at " + markerNode.hierarchy);
                    Require((expectedMeshes[0] == 0 && renderer.mesh == null) ||
                        (expectedMeshes[0] != 0 && renderer.mesh == context.meshes[expectedMeshes[0]]),
                        "Peak renderer primary mesh ownership drifted at " + markerNode.hierarchy);
                    particles++;
                }
                Require(prefab.GetComponentsInChildren<ParticleSystem>(true).Length ==
                    marker.particleNodes.Length && prefab.GetComponentsInChildren<ParticleSystemRenderer>(true).Length ==
                    marker.particleNodes.Length, "Peak component census drifted at " + effectName);
                roots++;
                hierarchy += marker.hierarchyNodes.Length;
            }
            Require(roots == 3 && hierarchy == 17 && particles == 14,
                "Peak generated aggregate census drifted");
            Debug.Log("[Endfield Li Zhiyan] source-closed peak particle prefabs passed: " +
                "3 roots, 17 hierarchy nodes, 14 particle pairs, 8 fail-closed materials, 3 meshes");
        }

        private static void ValidateArtifact(Dictionary<string, object> artifact, string owner)
        {
            string relative = Str(artifact, "path");
            string absolute = RepositoryAbsolute(relative);
            Require(File.Exists(absolute), "Missing " + owner + " artifact " + absolute);
            Require(Long(artifact, "bytes") == new FileInfo(absolute).Length &&
                string.Equals(Str(artifact, "sha256"), Sha256(absolute), StringComparison.OrdinalIgnoreCase),
                "Hash/size mismatch for " + owner + " artifact " + relative);
        }

        private static string ProjectAbsolute(string path) => Path.GetFullPath(Path.Combine(
            Application.dataPath, "..", path.Replace('/', Path.DirectorySeparatorChar)));
        private static string RepositoryAbsolute(string path) => Path.GetFullPath(Path.Combine(
            Application.dataPath, "..", "..", path.Replace('/', Path.DirectorySeparatorChar)));
        private static void CopyIfDifferent(string source, string destination)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(destination));
            if (File.Exists(destination) && File.ReadAllBytes(source).SequenceEqual(File.ReadAllBytes(destination)))
                return;
            File.Copy(source, destination, true);
        }
        private static void EnsureFolder(string path) => EndfieldLastRiteOverviewHeadEffectImporter.EnsureFolder(path);
        private static string Safe(string value) => EndfieldLastRiteOverviewHeadEffectImporter.Safe(value);
        private static Dictionary<string, object> Dict(object value) => EndfieldLastRiteOverviewHeadEffectImporter.Dict(value);
        private static IList List(object value) => EndfieldLastRiteOverviewHeadEffectImporter.List(value);
        private static string Str(Dictionary<string, object> value, string key) => EndfieldLastRiteOverviewHeadEffectImporter.Str(value, key);
        private static long Long(Dictionary<string, object> value, string key) => EndfieldLastRiteOverviewHeadEffectImporter.Long(value, key);
        private static int Int(Dictionary<string, object> value, string key) => EndfieldLastRiteOverviewHeadEffectImporter.Int(value, key);
        private static bool Bool(Dictionary<string, object> value, string key) => EndfieldLastRiteOverviewHeadEffectImporter.Bool(value, key);
        private static float Float(Dictionary<string, object> value, string key) => EndfieldLastRiteOverviewHeadEffectImporter.Float(value, key);
        private static long PPtrId(object value) => EndfieldLastRiteOverviewHeadEffectImporter.PPtrId(value);
        private static long[] PPtrIds(object value) => EndfieldLastRiteOverviewHeadEffectImporter.PPtrIds(value);
        private static Vector3 Vector3Value(object value) => EndfieldLastRiteOverviewHeadEffectImporter.Vector3Value(value);
        private static Quaternion QuaternionValue(object value) => EndfieldLastRiteOverviewHeadEffectImporter.QuaternionValue(value);
        private static bool Nearly(Vector3 a, Vector3 b) => (a - b).sqrMagnitude <= 1e-12f;
        private static bool Nearly(Quaternion a, Quaternion b) => Mathf.Abs(a.x - b.x) <= 1e-6f &&
            Mathf.Abs(a.y - b.y) <= 1e-6f && Mathf.Abs(a.z - b.z) <= 1e-6f && Mathf.Abs(a.w - b.w) <= 1e-6f;
        private static string Sha256(string path)
        {
            using (SHA256 hash = SHA256.Create())
            using (FileStream stream = File.OpenRead(path))
                return BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", string.Empty);
        }
        private static void Require(bool condition, string message)
        {
            if (!condition) throw new InvalidOperationException(message);
        }
    }
}
