using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEngine;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Restores only the ten already-retained Endminf physical rock bindings.
    /// This does not rebuild the missing source stage or broaden LitEffect
    /// admission; it validates exact PathIDs and tracked asset payloads first.
    /// </summary>
    public static class EndfieldEndminfLitEffectCompatibilityBindingBuilder
    {
        private const string Prefab =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Effects/Overview/P_fxui_endminm003_overview_01.prefab";
        private const string Material01 =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Effects/Overview/Materials/M_fx_endminm_gfx_01_p5A6341E8A834E421.mat";
        private const string Material38 =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Effects/Overview/Materials/M_fx_endminm_gfx_38_pAFCE491DD7BC5724.mat";
        private const string RockMesh =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Effects/Overview/Meshes/S_rock_small_1_017_02_lod2_p8EC9950E5461C8D9.obj";

        private const long Material01PathId = 0x5A6341E8A834E421L;
        private const long Material38PathId = unchecked((long)0xAFCE491DD7BC5724UL);
        private const long RockMeshPathId = unchecked((long)0x8EC9950E5461C8D9UL);
        private const string CompatibilityShader =
            "Hidden/Endfield/Compatibility/Endminf/LitEffectM01M38";

        private static readonly Dictionary<string, string> ExpectedSha256 =
            new Dictionary<string, string>(StringComparer.Ordinal) {
                { Material01, "626dc677675fea1a3a0f2f0079c9755455d37336cfe8cd682e3332669606f509" },
                { Material38, "b52f21342f56dd8b7801fe31217cc806a88553f5cba1cc688084dd229edcd38a" },
                { RockMesh, "e3bbdc9973e5f9dfb2d499fb440be36f99a525b525a22af8ce63b9c48402f8a7" },
            };

        [MenuItem("Endfield/Character Recovery Lab/Repair Endminf LitEffect Bindings")]
        public static void BuildAndValidate()
        {
            foreach (KeyValuePair<string, string> row in ExpectedSha256)
                Require(HashAsset(row.Key) == row.Value,
                    "Endminf LitEffect compatibility asset hash drifted: " + row.Key);

            Material material01 = AssetDatabase.LoadAssetAtPath<Material>(Material01);
            Material material38 = AssetDatabase.LoadAssetAtPath<Material>(Material38);
            Mesh mesh = AssetDatabase.LoadAllAssetsAtPath(RockMesh)
                .OfType<Mesh>().SingleOrDefault();
            Require(material01 != null && material38 != null && mesh != null,
                "Endminf LitEffect compatibility assets are missing");
            Require(material01.shader != null && material38.shader != null &&
                material01.shader.name == CompatibilityShader &&
                material38.shader.name == CompatibilityShader,
                "Endminf LitEffect compatibility shader binding drifted");

            GameObject root = PrefabUtility.LoadPrefabContents(Prefab);
            Require(root != null, "Endminf overview_01 prefab is missing");
            try
            {
                EndfieldRecoveredParticleEffectSource source =
                    root.GetComponent<EndfieldRecoveredParticleEffectSource>();
                ParticleSystemRenderer[] renderers =
                    root.GetComponentsInChildren<ParticleSystemRenderer>(true);
                Require(source != null && source.contractSchema ==
                    EndfieldRecoveredCharEffectSpawner.EndminfOverviewContractSchema,
                    "Endminf overview_01 source contract drifted");
                Require(source.particleNodes != null &&
                    source.particleNodes.Length == renderers.Length,
                    "Endminf retained particle-node/renderer order drifted");

                var rows = new List<EndfieldEndminfLitEffectCompatibilityBinding.Row>();
                int material01Count = 0;
                int material38Count = 0;
                for (int index = 0; index < source.particleNodes.Length; index++)
                {
                    EndfieldRecoveredParticleNodeSource node = source.particleNodes[index];
                    if (node.materialPathIds == null || node.materialPathIds.Length != 1 ||
                        node.meshPathIds == null || node.meshPathIds.Length != 1 ||
                        node.meshPathIds[0] != RockMeshPathId ||
                        (node.materialPathIds[0] != Material01PathId &&
                         node.materialPathIds[0] != Material38PathId))
                        continue;

                    ParticleSystemRenderer renderer = renderers[index];
                    Require(renderer != null,
                        "Endminf LitEffect target renderer is missing");
                    long materialPathId = node.materialPathIds[0];
                    Material material = materialPathId == Material01PathId
                        ? material01 : material38;
                    if (!node.rendererFailClosedForUnrecoveredShader)
                    {
                        Require(renderer.enabled &&
                            renderer.renderMode == ParticleSystemRenderMode.Mesh &&
                            renderer.sharedMaterials.Length == 1 &&
                            renderer.sharedMaterial == material,
                            "Fresh Endminf LitEffect source-stage binding drifted");
                    }
                    if (materialPathId == Material01PathId) material01Count++;
                    else material38Count++;

                    // Preserve the exact default behavior. The runtime component
                    // supplies these references only under the explicit opt-in.
                    renderer.enabled = false;
                    renderer.sharedMaterials = Array.Empty<Material>();
                    rows.Add(new EndfieldEndminfLitEffectCompatibilityBinding.Row {
                        particleRendererPathId = node.particleRendererPathId,
                        materialPathId = materialPathId,
                        meshPathId = RockMeshPathId,
                        renderer = renderer,
                        material = material,
                        mesh = mesh,
                    });
                }

                Require(rows.Count == 10 && material01Count == 7 && material38Count == 3 &&
                    rows.Select(row => row.particleRendererPathId).Distinct().Count() == 10,
                    "Endminf primary rock compatibility census drifted");
                EndfieldEndminfLitEffectCompatibilityBinding binding =
                    root.GetComponent<EndfieldEndminfLitEffectCompatibilityBinding>();
                if (binding == null)
                    binding = root.AddComponent<EndfieldEndminfLitEffectCompatibilityBinding>();
                binding.contractSchema =
                    EndfieldEndminfLitEffectCompatibilityBinding.ContractSchema;
                binding.rows = rows.ToArray();
                EditorUtility.SetDirty(binding);
                PrefabUtility.SaveAsPrefabAsset(root, Prefab);
            }
            finally
            {
                PrefabUtility.UnloadPrefabContents(root);
            }

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            ValidateSaved();
        }

        private static void ValidateSaved()
        {
            GameObject root = AssetDatabase.LoadAssetAtPath<GameObject>(Prefab);
            EndfieldEndminfLitEffectCompatibilityBinding binding = root != null
                ? root.GetComponent<EndfieldEndminfLitEffectCompatibilityBinding>() : null;
            Require(binding != null && binding.contractSchema ==
                EndfieldEndminfLitEffectCompatibilityBinding.ContractSchema &&
                binding.rows != null && binding.rows.Length == 10,
                "Saved Endminf LitEffect compatibility binding drifted");
            Require(binding.rows.All(row => row != null && row.renderer != null &&
                row.material != null && row.mesh != null &&
                !row.renderer.enabled && row.renderer.sharedMaterials.Length == 0 &&
                row.meshPathId == RockMeshPathId &&
                (row.materialPathId == Material01PathId ||
                 row.materialPathId == Material38PathId)) &&
                binding.rows.Select(row => row.particleRendererPathId).Distinct().Count() == 10,
                "Saved Endminf LitEffect direct-reference rows drifted");
        }

        private static string HashAsset(string assetPath)
        {
            string project = Directory.GetParent(Application.dataPath).FullName;
            string absolute = Path.Combine(project,
                assetPath.Replace('/', Path.DirectorySeparatorChar));
            Require(File.Exists(absolute), "Missing compatibility asset: " + assetPath);
            using (SHA256 sha = SHA256.Create())
                return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(absolute)))
                    .Replace("-", "").ToLowerInvariant();
        }

        private static void Require(bool condition, string message)
        {
            if (!condition) throw new InvalidOperationException(message);
        }
    }
}
