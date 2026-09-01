using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEngine;
using L = EndfieldGraphShaderLabEditor.EndfieldLastRiteOverviewHeadEffectImporter;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Restores the ten already-retained Endminf physical rock bindings and
    /// the source-identified M27 hand-crystal particle renderer.
    /// This does not rebuild the missing source stage or broaden LitEffect
    /// admission; it validates exact PathIDs and tracked asset payloads first.
    /// </summary>
    public static class EndfieldEndminfLitEffectCompatibilityBindingBuilder
    {
        private const string Prefab =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Effects/Overview/P_fxui_endminm003_overview_01.prefab";
        private const string M27Prefab =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Effects/Overview/P_fxui_endminm003_overview_02.prefab";
        private const string Material01 =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Effects/Overview/Materials/M_fx_endminm_gfx_01_p5A6341E8A834E421.mat";
        private const string Material38 =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Effects/Overview/Materials/M_fx_endminm_gfx_38_pAFCE491DD7BC5724.mat";
        private const string Material27 =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Effects/Overview/Materials/M_fx_endminm_gfx_27_pA531A88850690EB8.mat";
        private const string RockMesh =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Effects/Overview/Meshes/S_rock_small_1_017_02_lod2_p8EC9950E5461C8D9.obj";

        private const long Material01PathId = 0x5A6341E8A834E421L;
        private const long Material38PathId = unchecked((long)0xAFCE491DD7BC5724UL);
        private const long Material27PathId = unchecked((long)0xA531A88850690EB8UL);
        private const long M27RendererPathId = 59284134265994738L;
        private const long RockMeshPathId = unchecked((long)0x8EC9950E5461C8D9UL);
        private const long LitEffectShaderPathId = 6428594484694422749L;
        private const string CompatibilityShader =
            "Hidden/Endfield/Compatibility/Endminf/LitEffectParallax";
        private const string RockMeshSha256 =
            "e3bbdc9973e5f9dfb2d499fb440be36f99a525b525a22af8ce63b9c48402f8a7";
        private const string SourceMaterialRoot =
            "export_full/recovered/AnimeStudio-cli/StreamingAssets/json_by_type/Material/";

        private sealed class MaterialSource
        {
            public string relativePath;
            public string sha256;
        }

        private static readonly Dictionary<long, MaterialSource> MaterialSources =
            new Dictionary<long, MaterialSource> {
                { Material01PathId, new MaterialSource {
                    relativePath = SourceMaterialRoot +
                        "M_fx_endminm_gfx_01_p5A6341E8A834E421.json",
                    sha256 = "247e90600649b896249bdb4884abaa9d89aaa961d3a76d826cad9159a420426d",
                } },
                { Material27PathId, new MaterialSource {
                    relativePath = SourceMaterialRoot +
                        "M_fx_endminm_gfx_27_pA531A88850690EB8.json",
                    sha256 = "bf067450ab4bfd747747bc7b0f15b0c865fdc042cc1ef119646e8bec6af22b46",
                } },
                { Material38PathId, new MaterialSource {
                    relativePath = SourceMaterialRoot +
                        "M_fx_endminm_gfx_38_pAFCE491DD7BC5724.json",
                    sha256 = "3581bdfd934d8c8e3d3cdbdfdbe7188dd38f2a1b951f8114a6a47a7da34aa8f6",
                } },
            };

        private static readonly string[] SourceFloatFields = {
            "_BaseColorTintCover", "_BaseColorBrighterScale",
            "_NormalScale", "_RoughnessMin", "_RoughnessMax",
            "_OcclusionStrength", "_TwoSidedNormal", "_Metallic",
            "_BaseTextureMapCount",
            "_BaseUVSet", "_BasePbrMapUVSet", "_ParallaxMapUVType",
            "_ParallaxNoiseMapTilling", "_ParallaxFresnelStrength",
            "_ParallaxStrength", "_ParallaxTilling", "_ParallaxMarchNum",
            "_ParallaxMinBrightness", "_ParallaxIntensity",
        };
        private static readonly string[] SourceColorFields = {
            "_BaseColor", "_ParallaxColor", "_ParallaxColorDark",
        };
        private static readonly string[] SourceTextureFields = {
            "_BaseColorMap", "_NormalMap", "_MROMap", "_ParallaxMap",
        };

        [MenuItem("Endfield/Character Recovery Lab/Repair Endminf LitEffect Bindings")]
        public static void BuildAndValidate()
        {
            Require(HashAsset(RockMesh) == RockMeshSha256,
                "Endminf LitEffect rock mesh payload hash drifted: " + RockMesh);

            Material material01 = AssetDatabase.LoadAssetAtPath<Material>(Material01);
            Material material38 = AssetDatabase.LoadAssetAtPath<Material>(Material38);
            Material material27 = AssetDatabase.LoadAssetAtPath<Material>(Material27);
            Mesh mesh = AssetDatabase.LoadAllAssetsAtPath(RockMesh)
                .OfType<Mesh>().SingleOrDefault();
            Require(material01 != null && material38 != null && material27 != null && mesh != null,
                "Endminf LitEffect compatibility assets are missing");
            Require(material01.shader != null && material38.shader != null && material27.shader != null &&
                material01.shader.name == CompatibilityShader &&
                material38.shader.name == CompatibilityShader &&
                material27.shader.name == CompatibilityShader,
                "Endminf LitEffect compatibility shader binding drifted");
            ValidateSourceMaterial(material01, Material01PathId);
            ValidateSourceMaterial(material27, Material27PathId);
            ValidateSourceMaterial(material38, Material38PathId);

            GameObject root = PrefabUtility.LoadPrefabContents(Prefab);
            Require(root != null, "Endminf overview_01 prefab is missing");
            try
            {
                EndfieldRecoveredParticleEffectSource source =
                    root.GetComponent<EndfieldRecoveredParticleEffectSource>();
                Require(source != null && source.contractSchema ==
                    EndfieldRecoveredCharEffectSpawner.EndminfOverviewContractSchema,
                    "Endminf overview_01 source contract drifted");
                Require(source.particleNodes != null &&
                    source.particleNodes.Length == 33 &&
                    source.particleNodes.All(node => node != null &&
                        node.generatedParticleSystem != null &&
                        node.generatedRenderer != null) &&
                    source.particleNodes.Select(node => node.generatedRenderer)
                        .Distinct().Count() == source.particleNodes.Length,
                    "Endminf retained particle direct-reference set drifted");

                var rows = new List<EndfieldEndminfLitEffectCompatibilityBinding.Row>();
                int material01Count = 0;
                int material38Count = 0;
                foreach (EndfieldRecoveredParticleNodeSource node in
                         source.particleNodes)
                {
                    if (node.materialPathIds == null || node.materialPathIds.Length != 1 ||
                        node.meshPathIds == null || node.meshPathIds.Length != 1 ||
                        node.meshPathIds[0] != RockMeshPathId ||
                        (node.materialPathIds[0] != Material01PathId &&
                         node.materialPathIds[0] != Material38PathId))
                        continue;

                    ParticleSystemRenderer renderer = node.generatedRenderer;
                    Require(renderer != null,
                        "Endminf LitEffect target renderer is missing");
                    long materialPathId = node.materialPathIds[0];
                    Material material = materialPathId == Material01PathId
                        ? material01 : material38;
                    bool retainedFailClosed =
                        node.rendererFailClosedForUnrecoveredShader &&
                        !renderer.enabled && renderer.sharedMaterials.Length == 0;
                    bool freshlyAdmitted =
                        !node.rendererFailClosedForUnrecoveredShader &&
                        renderer.enabled &&
                        renderer.renderMode == ParticleSystemRenderMode.Mesh &&
                        renderer.sharedMaterials.Length == 1 &&
                        renderer.sharedMaterial == material;
                    Require(retainedFailClosed || freshlyAdmitted,
                        "Endminf LitEffect retained/admitted boundary drifted");
                    if (materialPathId == Material01PathId) material01Count++;
                    else material38Count++;

                    // Preserve the exact default behavior. The runtime component
                    // supplies these references only under the explicit opt-in.
                    renderer.enabled = false;
                    renderer.sharedMaterials = Array.Empty<Material>();
                    node.rendererFailClosedForUnrecoveredShader = true;
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

            BuildM27Binding(material27, mesh);

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            ValidateSaved();
        }

        private static void BuildM27Binding(Material material, Mesh mesh)
        {
            GameObject root = PrefabUtility.LoadPrefabContents(M27Prefab);
            Require(root != null, "Endminf overview_02 prefab is missing");
            try
            {
                EndfieldRecoveredParticleEffectSource source =
                    root.GetComponent<EndfieldRecoveredParticleEffectSource>();
                Require(source != null && source.contractSchema ==
                    EndfieldRecoveredCharEffectSpawner.EndminfOverviewContractSchema &&
                    source.particleNodes != null &&
                    source.particleNodes.Length == 18 &&
                    source.particleNodes.All(node => node != null &&
                        node.generatedParticleSystem != null &&
                        node.generatedRenderer != null),
                    "Endminf overview_02 source contract drifted");
                int index = Array.FindIndex(source.particleNodes,
                    node => node.particleRendererPathId == M27RendererPathId);
                Require(index >= 0, "Endminf M27 renderer identity is missing");
                EndfieldRecoveredParticleNodeSource node = source.particleNodes[index];
                ParticleSystemRenderer renderer = node.generatedRenderer;
                Require(node.materialPathIds != null && node.materialPathIds.Length == 1 &&
                    node.materialPathIds[0] == Material27PathId &&
                    node.meshPathIds != null && node.meshPathIds.Length == 1 &&
                    node.meshPathIds[0] == RockMeshPathId,
                    "Endminf M27 material/mesh identity drifted");
                bool retainedFailClosed =
                    node.rendererFailClosedForUnrecoveredShader &&
                    !renderer.enabled && renderer.sharedMaterials.Length == 0 &&
                    (renderer.mesh == null || renderer.mesh == mesh);
                bool freshlyAdmitted =
                    !node.rendererFailClosedForUnrecoveredShader &&
                    renderer.enabled &&
                    renderer.renderMode == ParticleSystemRenderMode.Mesh &&
                    renderer.sharedMaterials.Length == 1 &&
                    renderer.sharedMaterial == material && renderer.mesh == mesh;
                Require(retainedFailClosed || freshlyAdmitted,
                    "Endminf M27 retained/admitted boundary drifted: " +
                    "failClosed=" + node.rendererFailClosedForUnrecoveredShader +
                    ", sourceEnabled=" + node.sourceRendererEnabled +
                    ", rendererEnabled=" + renderer.enabled +
                    ", materialCount=" + renderer.sharedMaterials.Length +
                    ", mesh=" + (renderer.mesh == null ? "<null>" : renderer.mesh.name));

                renderer.enabled = false;
                renderer.sharedMaterials = Array.Empty<Material>();
                renderer.SetMeshes(Array.Empty<Mesh>(), 0);
                node.rendererFailClosedForUnrecoveredShader = true;
                EndfieldEndminfLitEffectCompatibilityBinding binding =
                    root.GetComponent<EndfieldEndminfLitEffectCompatibilityBinding>();
                if (binding == null)
                    binding = root.AddComponent<EndfieldEndminfLitEffectCompatibilityBinding>();
                binding.contractSchema =
                    EndfieldEndminfLitEffectCompatibilityBinding.ContractSchema;
                binding.rows = new[] {
                    new EndfieldEndminfLitEffectCompatibilityBinding.Row {
                        particleRendererPathId = M27RendererPathId,
                        materialPathId = Material27PathId,
                        meshPathId = RockMeshPathId,
                        renderer = renderer,
                        material = material,
                        mesh = mesh,
                    }
                };
                EditorUtility.SetDirty(binding);
                PrefabUtility.SaveAsPrefabAsset(root, M27Prefab);
            }
            finally
            {
                PrefabUtility.UnloadPrefabContents(root);
            }
        }

        private static void ValidateSaved()
        {
            GameObject root = AssetDatabase.LoadAssetAtPath<GameObject>(Prefab);
            EndfieldEndminfLitEffectCompatibilityBinding binding = root != null
                ? root.GetComponent<EndfieldEndminfLitEffectCompatibilityBinding>() : null;
            EndfieldRecoveredParticleEffectSource source = root != null
                ? root.GetComponent<EndfieldRecoveredParticleEffectSource>() : null;
            Require(binding != null && binding.contractSchema ==
                EndfieldEndminfLitEffectCompatibilityBinding.ContractSchema &&
                binding.rows != null && binding.rows.Length == 10,
                "Saved Endminf LitEffect compatibility binding drifted");
            Require(binding.TryValidateForRecoveryAudit(out string bindingFailure),
                "Saved Endminf LitEffect runtime validation failed: " + bindingFailure);
            Require(binding.rows.All(row => row != null && row.renderer != null &&
                row.material != null && row.mesh != null &&
                !row.renderer.enabled && row.renderer.sharedMaterials.Length == 0 &&
                row.meshPathId == RockMeshPathId &&
                (row.materialPathId == Material01PathId ||
                 row.materialPathId == Material38PathId)) &&
                binding.rows.Select(row => row.particleRendererPathId).Distinct().Count() == 10,
                "Saved Endminf LitEffect direct-reference rows drifted");
            Require(source != null && source.particleNodes != null &&
                binding.rows.All(row => source.particleNodes.Count(node =>
                    node.particleRendererPathId == row.particleRendererPathId &&
                    node.sourceRendererEnabled &&
                    node.generatedRenderer == row.renderer &&
                    node.rendererFailClosedForUnrecoveredShader) == 1),
                "Saved Endminf LitEffect marker boundary drifted");

            GameObject m27Root = AssetDatabase.LoadAssetAtPath<GameObject>(M27Prefab);
            EndfieldEndminfLitEffectCompatibilityBinding m27Binding = m27Root != null
                ? m27Root.GetComponent<EndfieldEndminfLitEffectCompatibilityBinding>() : null;
            EndfieldRecoveredParticleEffectSource m27Source = m27Root != null
                ? m27Root.GetComponent<EndfieldRecoveredParticleEffectSource>() : null;
            Require(m27Binding != null && m27Binding.contractSchema ==
                EndfieldEndminfLitEffectCompatibilityBinding.ContractSchema &&
                m27Binding.rows != null && m27Binding.rows.Length == 1,
                "Saved Endminf M27 compatibility binding drifted");
            Require(m27Binding.TryValidateForRecoveryAudit(out string m27BindingFailure),
                "Saved Endminf M27 runtime validation failed: " + m27BindingFailure);
            EndfieldEndminfLitEffectCompatibilityBinding.Row m27 = m27Binding.rows[0];
            Require(m27 != null && m27.renderer != null && m27.material != null &&
                m27.mesh != null && !m27.renderer.enabled &&
                m27.renderer.sharedMaterials.Length == 0 && m27.renderer.mesh == null &&
                m27.particleRendererPathId == M27RendererPathId &&
                m27.materialPathId == Material27PathId &&
                m27.meshPathId == RockMeshPathId,
                "Saved Endminf M27 direct-reference row drifted");
            Require(m27Source != null && m27Source.particleNodes != null &&
                m27Source.particleNodes.Count(node =>
                    node.particleRendererPathId == M27RendererPathId &&
                    node.sourceRendererEnabled &&
                    node.generatedRenderer == m27.renderer &&
                    node.rendererFailClosedForUnrecoveredShader) == 1,
                "Saved Endminf M27 marker boundary drifted");
        }

        private static void ValidateSourceMaterial(Material material, long pathId)
        {
            MaterialSource source = null;
            Require(material != null && MaterialSources.TryGetValue(pathId, out source),
                "Endminf LitEffect source material identity is unknown: p" +
                unchecked((ulong)pathId).ToString("X16"));
            string repo = Directory.GetParent(Application.dataPath).Parent.FullName;
            string sourcePath = Path.Combine(
                repo,
                source.relativePath.Replace('/', Path.DirectorySeparatorChar));
            Require(File.Exists(sourcePath) && HashFile(sourcePath) == source.sha256,
                "Endminf LitEffect source material hash drifted: " + source.relativePath);
            Dictionary<string, object> row = L.Dict(
                ManifestMiniJson.Deserialize(File.ReadAllText(sourcePath, Encoding.UTF8)));
            Require(L.PPtrId(row["m_Shader"]) == LitEffectShaderPathId &&
                L.Str(row, "m_Name") == material.name &&
                L.Int(row, "m_CustomRenderQueue") == material.renderQueue &&
                L.List(row["m_ValidKeywords"]).Cast<object>()
                    .Select(value => Convert.ToString(value))
                    .SequenceEqual(new[] { "_PARALLAX_MAP" }),
                "Endminf LitEffect source material header drifted: " + material.name);

            Dictionary<string, object> saved = L.Dict(row["m_SavedProperties"]);
            Dictionary<string, object> floats = L.Dict(saved["m_Floats"]);
            foreach (string field in SourceFloatFields)
            {
                Require(floats.ContainsKey(field) && material.HasProperty(field) &&
                    Mathf.Abs(material.GetFloat(field) - L.Float(floats, field)) <= 1.0e-6f,
                    "Endminf LitEffect source float drifted: " + material.name + "." + field);
            }
            Dictionary<string, object> colors = L.Dict(saved["m_Colors"]);
            foreach (string field in SourceColorFields)
            {
                Require(colors.ContainsKey(field) && material.HasProperty(field),
                    "Endminf LitEffect source color is absent: " + material.name + "." + field);
                Dictionary<string, object> value = L.Dict(colors[field]);
                Color expected = new Color(
                    L.Float(value, "r"), L.Float(value, "g"),
                    L.Float(value, "b"), L.Float(value, "a"));
                Color actual = material.GetColor(field);
                Require(MaxAbs(actual, expected) <= 1.0e-6f,
                    "Endminf LitEffect source color drifted: " + material.name + "." + field);
            }
            Dictionary<string, object> textures = L.Dict(saved["m_TexEnvs"]);
            foreach (string field in SourceTextureFields)
            {
                Dictionary<string, object> textureRow = L.Dict(textures[field]);
                long texturePathId = L.PPtrId(textureRow["m_Texture"]);
                Texture texture = material.GetTexture(field);
                string texturePath = texture == null
                    ? string.Empty
                    : AssetDatabase.GetAssetPath(texture);
                string suffix = "_p" + unchecked((ulong)texturePathId)
                    .ToString("X16") + ".png";
                Require(texturePathId != 0 && texture != null &&
                    texturePath.EndsWith(suffix, StringComparison.OrdinalIgnoreCase),
                    "Endminf LitEffect source texture PathID drifted: " +
                    material.name + "." + field);
                Vector2 expectedScale = Vector2Value(textureRow["m_Scale"]);
                Vector2 expectedOffset = Vector2Value(textureRow["m_Offset"]);
                Require(MaxAbs(material.GetTextureScale(field), expectedScale) <= 1.0e-6f &&
                    MaxAbs(material.GetTextureOffset(field), expectedOffset) <= 1.0e-6f,
                    "Endminf LitEffect source texture transform drifted: " +
                    material.name + "." + field);
            }
            Require(!HasSerializedMaterialProperty(
                    material,
                    "_RecoveredParallaxCompatibilityScale"),
                "Endminf LitEffect material retained capture-fitted scale: " +
                material.name);
        }

        private static Vector2 Vector2Value(object value)
        {
            Dictionary<string, object> row = L.Dict(value);
            return new Vector2(
                row.ContainsKey("x") ? L.Float(row, "x") : L.Float(row, "X"),
                row.ContainsKey("y") ? L.Float(row, "y") : L.Float(row, "Y"));
        }

        private static float MaxAbs(Color left, Color right) => Mathf.Max(
            Mathf.Abs(left.r - right.r), Mathf.Abs(left.g - right.g),
            Mathf.Abs(left.b - right.b), Mathf.Abs(left.a - right.a));

        private static float MaxAbs(Vector2 left, Vector2 right) => Mathf.Max(
            Mathf.Abs(left.x - right.x), Mathf.Abs(left.y - right.y));

        private static bool HasSerializedMaterialProperty(
            Material material,
            string propertyName)
        {
            var serialized = new SerializedObject(material);
            foreach (string path in new[] {
                "m_SavedProperties.m_Floats",
                "m_SavedProperties.m_Colors",
                "m_SavedProperties.m_TexEnvs",
                "m_SavedProperties.m_Ints",
            })
            {
                SerializedProperty values = serialized.FindProperty(path);
                if (values == null || !values.isArray)
                    continue;
                for (int index = 0; index < values.arraySize; index++)
                {
                    SerializedProperty key = values.GetArrayElementAtIndex(index)
                        .FindPropertyRelative("first");
                    if (key != null && string.Equals(
                            key.stringValue,
                            propertyName,
                            StringComparison.Ordinal))
                        return true;
                }
            }
            return false;
        }

        private static string HashAsset(string assetPath)
        {
            string project = Directory.GetParent(Application.dataPath).FullName;
            string absolute = Path.Combine(project,
                assetPath.Replace('/', Path.DirectorySeparatorChar));
            Require(File.Exists(absolute), "Missing compatibility asset: " + assetPath);
            return HashFile(absolute);
        }

        private static string HashFile(string absolute)
        {
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
