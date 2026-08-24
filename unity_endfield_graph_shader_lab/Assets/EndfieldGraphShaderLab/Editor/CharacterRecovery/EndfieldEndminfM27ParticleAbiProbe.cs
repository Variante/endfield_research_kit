using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using EndfieldGraphShaderLab;
using Unity.Collections;
using UnityEditor;
using UnityEngine;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Read-only, default-off probe for the retained M27 particle renderer.
    /// It deliberately does not enable the blocked renderer, bind a material,
    /// mutate its streams, or render a frame.
    /// </summary>
    public static class EndfieldEndminfM27ParticleAbiProbe
    {
        private const string PrefabPath =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Effects/Overview/" +
            "P_fxui_endminm003_overview_02.prefab";
        private const string MeshPath =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Effects/Overview/Meshes/" +
            "S_rock_small_1_017_02_lod2_p8EC9950E5461C8D9.obj";
        private const long RendererPathId = 59284134265994738L;

        [Serializable]
        private sealed class Report
        {
            public string schema = "endfield.endminf-m27-particle-abi-unity-probe.v1";
            public string status = "ok";
            public string unityVersion;
            public string prefabPath = PrefabPath;
            public string hierarchy;
            public long rendererPathId = RendererPathId;
            public bool rendererEnabled;
            public bool enableGPUInstancing;
            public string renderMode;
            public string[] activeVertexStreams;
            public int retainedMaterialCount;
            public bool retainedMeshAssigned;
            public string exactMeshPath = MeshPath;
            public string exactMeshName;
            public int exactMeshVertexCount;
            public int exactMeshBoneWeightCount;
            public int exactMeshBindPoseCount;
            public int exactMeshBonesPerVertexRowCount;
            public int exactMeshBonesPerVertexInfluenceSum;
            public string boundary =
                "Read-only retained-state probe; no renderer, stream, material, mesh, particle, or prefab mutation.";
        }

        public static void Run()
        {
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
            Require(prefab != null, "missing retained overview_02 prefab: " + PrefabPath);
            EndfieldRecoveredParticleEffectSource source =
                prefab.GetComponent<EndfieldRecoveredParticleEffectSource>();
            Require(source != null, "overview_02 prefab has no recovered particle source marker");

            ParticleSystemRenderer[] renderers =
                prefab.GetComponentsInChildren<ParticleSystemRenderer>(true);
            Require(
                renderers.Length == source.particleNodes.Length,
                $"marker/renderer count mismatch: {source.particleNodes.Length} != {renderers.Length}");
            int index = Array.FindIndex(
                source.particleNodes,
                value => value.particleRendererPathId == RendererPathId);
            Require(index >= 0, "retained marker has no M27 renderer PathID");
            ParticleSystemRenderer renderer = renderers[index];
            string hierarchy = Hierarchy(renderer.transform, prefab.transform);
            Require(hierarchy == "all/suikuai (2)", "M27 hierarchy drifted: " + hierarchy);

            var streams = new List<ParticleSystemVertexStream>();
            renderer.GetActiveVertexStreams(streams);
            string[] expectedStreams =
            {
                "Position", "Normal", "Color", "UV", "UV2", "Custom1XYZW"
            };
            string[] actualStreams = streams.Select(value => value.ToString()).ToArray();
            Require(
                actualStreams.SequenceEqual(expectedStreams),
                "M27 active streams drifted: " + string.Join(", ", actualStreams));
            Require(renderer.enableGPUInstancing, "M27 source GPU-instancing flag was not retained");
            Require(!renderer.enabled, "M27 must remain blocked during the ABI probe");
            Require(renderer.sharedMaterials.Length == 0, "M27 unexpectedly has a retained material");
            Require(renderer.mesh == null, "M27 unexpectedly has a retained mesh binding");

            Mesh mesh = AssetDatabase.LoadAssetAtPath<Mesh>(MeshPath);
            Require(mesh != null, "missing exact M27 mesh asset: " + MeshPath);
            int boneWeightCount;
            int bonesPerVertexRowCount;
            int bonesPerVertexInfluenceSum;
            using (NativeArray<BoneWeight1> weights = mesh.GetAllBoneWeights())
            using (NativeArray<byte> bonesPerVertex = mesh.GetBonesPerVertex())
            {
                boneWeightCount = weights.Length;
                bonesPerVertexRowCount = bonesPerVertex.Length;
                bonesPerVertexInfluenceSum = 0;
                for (int boneIndex = 0; boneIndex < bonesPerVertex.Length; boneIndex++)
                {
                    bonesPerVertexInfluenceSum += bonesPerVertex[boneIndex];
                }
            }
            Require(mesh.vertexCount == 29, $"M27 mesh vertex count drifted: {mesh.vertexCount}");
            Require(boneWeightCount == 0, $"M27 mesh unexpectedly has {boneWeightCount} bone weights");
            Require(mesh.bindposes.Length == 0, $"M27 mesh unexpectedly has {mesh.bindposes.Length} bind poses");
            Require(
                bonesPerVertexRowCount == 0,
                $"M27 mesh unexpectedly has {bonesPerVertexRowCount} bones-per-vertex rows");
            Require(
                bonesPerVertexInfluenceSum == 0,
                $"M27 mesh unexpectedly has {bonesPerVertexInfluenceSum} bone influences");

            var report = new Report
            {
                unityVersion = Application.unityVersion,
                hierarchy = hierarchy,
                rendererEnabled = renderer.enabled,
                enableGPUInstancing = renderer.enableGPUInstancing,
                renderMode = renderer.renderMode.ToString(),
                activeVertexStreams = actualStreams,
                retainedMaterialCount = renderer.sharedMaterials.Length,
                retainedMeshAssigned = renderer.mesh != null,
                exactMeshName = mesh.name,
                exactMeshVertexCount = mesh.vertexCount,
                exactMeshBoneWeightCount = boneWeightCount,
                exactMeshBindPoseCount = mesh.bindposes.Length,
                exactMeshBonesPerVertexRowCount = bonesPerVertexRowCount,
                exactMeshBonesPerVertexInfluenceSum = bonesPerVertexInfluenceSum,
            };
            string output = Path.GetFullPath(Path.Combine(
                Application.dataPath,
                "../../reports/assets/character_recovery/endminf_m27_particle_abi_unity_probe.json"));
            Directory.CreateDirectory(Path.GetDirectoryName(output));
            File.WriteAllText(output, JsonUtility.ToJson(report, true) + "\n");
            Debug.Log("Endminf M27 particle ABI Unity probe passed: " + output);
        }

        private static string Hierarchy(Transform value, Transform root)
        {
            var names = new List<string>();
            while (value != null && value != root)
            {
                names.Add(value.name);
                value = value.parent;
            }
            names.Reverse();
            return string.Join("/", names);
        }

        private static void Require(bool condition, string message)
        {
            if (!condition)
            {
                throw new InvalidOperationException(message);
            }
        }
    }
}
