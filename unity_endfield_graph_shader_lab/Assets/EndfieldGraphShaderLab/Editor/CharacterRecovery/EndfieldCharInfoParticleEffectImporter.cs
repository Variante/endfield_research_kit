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
    /// Imports the source-closed two-node Character Info CharEffect contract.
    /// This is deliberately separate from the large Zhuangfy/Gacha importer:
    /// Character Info owns the effect, uses a VFXRefract MRT material, and has
    /// no Gacha EffectSetting or Timeline lifetime to infer.
    /// </summary>
    public static class EndfieldCharInfoParticleEffectImporter
    {
        private const string ContractAssetPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/char_effect_particle_contract.json";
        private const string Schema = "endfield.charinfo-char-effect-particle.v1";
        private const string RecoveredShaderName =
            "Hidden/Endfield/Recovered/Zhuangfy/VFXRefractMRT";
        private const string GeneratedRoot =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/CharInfo/Effects/CharEffect";
        private const string PrefabPath = GeneratedRoot + "/Prefabs/CharEffect.prefab";
        private const string RuntimePrefabPath =
            "Assets/EndfieldGraphShaderLab/Resources/EndfieldCharInfo/CharEffect.prefab";
        private const string MaterialPath = GeneratedRoot + "/Materials/M_UI_charChoose_12.mat";
        private const string TexturePath = GeneratedRoot + "/Textures/T_fx_mask_01_M.png";
        private const string SourcePrefabRoot = "CharEffect";
        private const string SourceTrailName = "trail";
        private static readonly HashSet<string> KnownRetailOnlyFields =
            new HashSet<string>(StringComparer.Ordinal)
            {
                "maxAliveDistance", "limitAliveDistance", "m_CharacterIndex",
                "m_RealtimeShadowCaster", "m_SubMeshRenderMode", "m_RayTracingMode",
                "m_RayTraceProcedural", "m_RenderFoliageOccluder",
                "m_PlatformSpecificCastShadows", "m_ShadowProxyMesh",
                "m_EnableCharacterOutline", "m_EnablePerRendererLighting",
                "m_PerRendererLightingOffset", "m_PerRendererLightingAnchor",
                "m_LightModeMask", "m_RendererSortingFudge", "m_EnableHGGPUInstancing",
                "m_RenderInUI", "m_UISortingOrder", "m_CutoutTexture",
                "m_CutOutTextureOpacityMode", "m_CutOutMode", "m_CutOutThreshold",
                "m_DisableCutOutAnimation", "m_CutoutGeomUV",
                "m_TextureClipThresholdUpper",
            };

        [MenuItem("Endfield/Character Recovery Lab/Build CharInfo CharEffect (Source Closed)")]
        public static void BuildAndValidate()
        {
            Dictionary<string, object> contract = LoadContract();
            EnsureFolders();
            Texture2D texture = BuildTexture(contract);
            Material material = BuildMaterial(contract, texture);
            BuildPrefab(contract, material);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            ValidateGenerated(contract, material);
            Debug.Log("[Endfield CharInfo] source-closed CharEffect import passed: " + PrefabPath);
        }

        public static void ValidateBatch()
        {
            Dictionary<string, object> contract = LoadContract();
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
            Material material = AssetDatabase.LoadAssetAtPath<Material>(MaterialPath);
            Require(prefab != null, "Missing generated CharInfo CharEffect prefab: " + PrefabPath);
            Require(material != null, "Missing generated CharInfo CharEffect material: " + MaterialPath);
            ValidateGenerated(contract, material);
        }

        private static Dictionary<string, object> LoadContract()
        {
            string absolute = AssetToAbsolute(ContractAssetPath);
            Require(File.Exists(absolute), "Missing CharInfo particle contract: " + absolute);
            Dictionary<string, object> contract = Dict(
                ManifestMiniJson.Deserialize(File.ReadAllText(absolute, Encoding.UTF8)));
            Require(Str(contract, "schema") == Schema, "Unexpected CharInfo particle schema");
            Require(Str(contract, "effect_root") == SourcePrefabRoot, "CharEffect root drifted");
            Require(List(contract["nodes"]).Count == 2, "CharInfo CharEffect must contain exactly two nodes");
            Require(
                Str(Dict(contract["material"]), "shaderName") == "HGRP/Effect/VFXRefract" &&
                Str(Dict(contract["material"]), "recoveredShaderName") == RecoveredShaderName,
                "CharInfo material shader gate drifted");
            Dictionary<string, object> gate = Dict(contract["execution_gate"]);
            Require(Int(gate, "queue") == 3000, "CharInfo material queue gate drifted");
            Require(Str(gate, "lightMode") == "Distortion", "CharInfo light mode gate drifted");
            Require(Str(gate, "fragmentDxbcHash") == "f905de094d0261d5", "CharInfo fragment gate drifted");
            Require(
                List(gate["keywords"]).Cast<object>().Select(Str).SequenceEqual(
                    new[] { "HG_ENABLE_MV", "_USE_RBOFFSET" }, StringComparer.Ordinal),
                "CharInfo keyword gate drifted");
            return contract;
        }

        private static void EnsureFolders()
        {
            EnsureFolder(GeneratedRoot);
            EnsureFolder(GeneratedRoot + "/Prefabs");
            EnsureFolder(GeneratedRoot + "/Materials");
            EnsureFolder(GeneratedRoot + "/Textures");
            EnsureFolder("Assets/EndfieldGraphShaderLab/Resources");
            EnsureFolder("Assets/EndfieldGraphShaderLab/Resources/EndfieldCharInfo");
        }

        private static Texture2D BuildTexture(Dictionary<string, object> contract)
        {
            Dictionary<string, object> source = Dict(contract["texture"]);
            string sourcePath = RepoRelativeToAbsolute(Str(source, "path"));
            Require(File.Exists(sourcePath), "Missing exact CharInfo texture: " + sourcePath);
            Require(Sha256(sourcePath) == Str(source, "sha256").ToUpperInvariant(),
                "CharInfo texture SHA-256 gate failed");
            string destination = AssetToAbsolute(TexturePath);
            CopyIfDifferent(sourcePath, destination);
            AssetDatabase.ImportAsset(TexturePath, ImportAssetOptions.ForceSynchronousImport);
            Texture2D texture = AssetDatabase.LoadAssetAtPath<Texture2D>(TexturePath);
            Require(texture != null, "Unity did not import CharInfo texture");
            return texture;
        }

        private static Material BuildMaterial(
            Dictionary<string, object> contract,
            Texture2D texture)
        {
            Dictionary<string, object> source = Dict(contract["material"]);
            Shader shader = Shader.Find(RecoveredShaderName);
            Require(shader != null && shader.isSupported, "Missing supported CharInfo VFXRefract MRT shader");
            Material material = AssetDatabase.LoadAssetAtPath<Material>(MaterialPath);
            if (material == null)
            {
                material = new Material(shader);
                AssetDatabase.CreateAsset(material, MaterialPath);
            }
            material.shader = shader;
            material.name = Str(source, "name");
            ApplyMaterialPayload(material, Dict(source["fields"]), texture);
            EditorUtility.SetDirty(material);
            return material;
        }

        private static void BuildPrefab(
            Dictionary<string, object> contract,
            Material material)
        {
            GameObject root = new GameObject(SourcePrefabRoot);
            try
            {
                IList nodes = List(contract["nodes"]);
                Dictionary<string, object> rootNode = Dict(nodes[0]);
                Dictionary<string, object> trailNode = Dict(nodes[1]);
                Require(Str(rootNode, "hierarchy") == SourcePrefabRoot, "CharEffect root node drifted");
                Require(Str(trailNode, "hierarchy") == SourcePrefabRoot + "/" + SourceTrailName,
                    "CharEffect trail hierarchy drifted");

                GameObject trail = new GameObject(SourceTrailName);
                trail.transform.SetParent(root.transform, false);
                ApplyTransformPayload(root.transform, Dict(rootNode["transform"]), "CharEffect.Transform");
                ApplyTransformPayload(trail.transform, Dict(trailNode["transform"]), "CharEffect/trail.Transform");

                BuildParticleNode(root, rootNode, material);
                BuildParticleNode(trail, trailNode, material);

                EndfieldRecoveredParticleEffectSource marker =
                    root.AddComponent<EndfieldRecoveredParticleEffectSource>();
                PopulateMarker(marker, contract, root, trail);

                if (AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath) != null)
                    AssetDatabase.DeleteAsset(PrefabPath);
                PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
                if (AssetDatabase.LoadAssetAtPath<GameObject>(RuntimePrefabPath) != null)
                    AssetDatabase.DeleteAsset(RuntimePrefabPath);
                PrefabUtility.SaveAsPrefabAsset(root, RuntimePrefabPath);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
        }

        private static void BuildParticleNode(
            GameObject target,
            Dictionary<string, object> node,
            Material material)
        {
            ParticleSystem system = target.AddComponent<ParticleSystem>();
            ParticleSystemRenderer renderer = target.GetComponent<ParticleSystemRenderer>();
            Require(renderer != null, "Unity did not create a ParticleSystemRenderer for " + node["hierarchy"]);
            Dictionary<string, object> particle = Dict(node["particle_system"]);
            Dictionary<string, object> rendererData = Dict(node["particle_renderer"]);
            ApplySerializedDictionary(
                new SerializedObject(system), particle, "ParticleSystem." + node["hierarchy"],
                value => ResolveReference(value, material, "ParticleSystem"),
                "m_GameObject");
            ApplySerializedDictionary(
                new SerializedObject(renderer), rendererData, "ParticleSystemRenderer." + node["hierarchy"],
                value => ResolveReference(value, material, "ParticleSystemRenderer"),
                "m_GameObject");
        }

        private static void PopulateMarker(
            EndfieldRecoveredParticleEffectSource marker,
            Dictionary<string, object> contract,
            GameObject root,
            GameObject trail)
        {
            marker.contractSchema = Schema;
            marker.effectRoot = SourcePrefabRoot;
            marker.sourceHierarchy = Str(contract, "source_prefab") + "/CharEffect";
            IList nodes = List(contract["nodes"]);
            Dictionary<string, object> rootNode = Dict(nodes[0]);
            marker.sourceGameObjectPathId = Long(Dict(rootNode["game_object_source"]), "pathID");
            marker.sourceTransformPathId = Long(Dict(rootNode["transform_source"]), "pathID");
            marker.sourceEffectLoops = false;
            marker.sourceEffectDuration = Float(Dict(rootNode["particle_system"]), "lengthInSec");
            marker.sourceEffectDelay = 0f;
            marker.sourceEffectRandomDelay = 0f;
            marker.materialExecutionBoundary = Str(contract, "boundary");
            marker.hierarchyNodes = new[]
            {
                NodeSource(Dict(nodes[0]), root.transform),
                NodeSource(Dict(nodes[1]), trail.transform),
            };
            marker.particleNodes = new[]
            {
                ParticleSource(Dict(nodes[0]), Long(Dict(contract["material"]), "shaderPathID")),
                ParticleSource(Dict(nodes[1]), Long(Dict(contract["material"]), "shaderPathID")),
            };
        }

        private static EndfieldRecoveredParticleHierarchyNodeSource NodeSource(
            Dictionary<string, object> node,
            Transform generated)
        {
            Dictionary<string, object> go = Dict(node["game_object_source"]);
            Dictionary<string, object> transform = Dict(node["transform_source"]);
            return new EndfieldRecoveredParticleHierarchyNodeSource
            {
                hierarchy = Str(node, "hierarchy"),
                gameObjectPathId = Long(go, "pathID"),
                transformPathId = Long(transform, "pathID"),
                generatedTransform = generated,
            };
        }

        private static EndfieldRecoveredParticleNodeSource ParticleSource(
            Dictionary<string, object> node,
            long shaderPathId)
        {
            Dictionary<string, object> go = Dict(node["game_object_source"]);
            Dictionary<string, object> transform = Dict(node["transform_source"]);
            Dictionary<string, object> particle = Dict(node["particle_system_source"]);
            Dictionary<string, object> renderer = Dict(node["particle_renderer_source"]);
            IList materialList = List(Dict(node["particle_renderer"])["m_Materials"]);
            Require(materialList.Count == 1, "CharInfo renderer must have one material PPtr");
            Dictionary<string, object> material = Dict(materialList[0]);
            return new EndfieldRecoveredParticleNodeSource
            {
                hierarchy = Str(node, "hierarchy"),
                gameObjectPathId = Long(go, "pathID"),
                transformPathId = Long(transform, "pathID"),
                particleSystemPathId = Long(particle, "pathID"),
                particleRendererPathId = Long(renderer, "pathID"),
                materialPathIds = new[] { Long(material, "m_PathID") },
                meshPathIds = Array.Empty<long>(),
                shaderNames = Long(material, "m_PathID") == 0
                    ? Array.Empty<string>()
                    : new[] { "HGRP/Effect/VFXRefract" },
                shaderPathIds = Long(material, "m_PathID") == 0
                    ? Array.Empty<long>()
                    : new[] { shaderPathId },
                sourceRendererEnabled = Bool(Dict(node["particle_renderer"]), "m_Enabled"),
                nativeParticlePayloadApplied = true,
                nativeRendererPayloadApplied = true,
                rendererFailClosedForUnrecoveredShader = false,
            };
        }

        private static void ValidateGenerated(
            Dictionary<string, object> contract,
            Material expectedMaterial)
        {
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
            GameObject runtimePrefab =
                AssetDatabase.LoadAssetAtPath<GameObject>(RuntimePrefabPath);
            Require(prefab != null, "Generated CharInfo CharEffect prefab is missing");
            Require(runtimePrefab != null,
                "Generated runtime CharInfo CharEffect resource is missing");
            EndfieldRecoveredParticleEffectSource marker =
                prefab.GetComponent<EndfieldRecoveredParticleEffectSource>();
            Require(marker != null && marker.contractSchema == Schema, "CharInfo marker schema mismatch");
            EndfieldRecoveredParticleEffectSource runtimeMarker =
                runtimePrefab.GetComponent<EndfieldRecoveredParticleEffectSource>();
            Require(runtimeMarker != null && runtimeMarker.contractSchema == Schema,
                "Runtime CharInfo marker schema mismatch");
            Require(marker.hierarchyNodes.Length == 2 && marker.particleNodes.Length == 2,
                "CharInfo marker node count mismatch");
            ParticleSystem[] systems = prefab.GetComponentsInChildren<ParticleSystem>(true);
            ParticleSystemRenderer[] renderers = prefab.GetComponentsInChildren<ParticleSystemRenderer>(true);
            Require(systems.Length == 2 && renderers.Length == 2, "CharInfo generated particle count mismatch");
            IList nodes = List(contract["nodes"]);
            for (int index = 0; index < renderers.Length; index++)
            {
                Dictionary<string, object> node = Dict(nodes[index]);
                bool enabled = Bool(Dict(node["particle_renderer"]), "m_Enabled");
                if (enabled)
                {
                    Require(renderers[index].sharedMaterials.Length == 1 &&
                        renderers[index].sharedMaterials[0] == expectedMaterial,
                        "CharInfo enabled renderer material identity mismatch");
                }
                else
                {
                    Require(!renderers[index].enabled &&
                        renderers[index].sharedMaterials.All(value => value == null),
                        "CharInfo disabled renderer must retain its null material PPtr");
                }
            }
            Require(expectedMaterial.shader != null && expectedMaterial.shader.name == RecoveredShaderName,
                "CharInfo generated shader identity mismatch");
            Require(expectedMaterial.renderQueue == 3000 &&
                expectedMaterial.shaderKeywords.SequenceEqual(new[] { "_USE_RBOFFSET" }, StringComparer.Ordinal),
                "CharInfo generated material queue/keyword mismatch");

            for (int index = 0; index < nodes.Count; index++)
            {
                Dictionary<string, object> node = Dict(nodes[index]);
                Transform target = systems[index].transform;
                VerifyTransformPayload(target, Dict(node["transform"]), Str(node, "hierarchy") + ".Transform");
                VerifySerializedDictionary(new SerializedObject(systems[index]), Dict(node["particle_system"]),
                    "ParticleSystem." + node["hierarchy"], _ => null, "m_GameObject");
                VerifySerializedDictionary(new SerializedObject(renderers[index]), Dict(node["particle_renderer"]),
                    "ParticleSystemRenderer." + node["hierarchy"], value => ResolveReferenceForVerify(value, expectedMaterial), "m_GameObject");
            }
        }

        private static void ApplyTransformPayload(
            Transform target,
            Dictionary<string, object> values,
            string owner)
        {
            target.localPosition = Vector3Value(values["m_LocalPosition"]);
            target.localRotation = QuaternionValue(values["m_LocalRotation"]);
            target.localScale = Vector3Value(values["m_LocalScale"]);
        }

        private static void VerifyTransformPayload(
            Transform target,
            Dictionary<string, object> values,
            string owner)
        {
            Require(Nearly(target.localPosition, Vector3Value(values["m_LocalPosition"])), "Transform position mismatch at " + owner);
            Require(Nearly(target.localRotation, QuaternionValue(values["m_LocalRotation"])), "Transform rotation mismatch at " + owner);
            Require(Nearly(target.localScale, Vector3Value(values["m_LocalScale"])), "Transform scale mismatch at " + owner);
        }

        private static void ApplyMaterialPayload(
            Material material,
            Dictionary<string, object> fields,
            Texture2D texture)
        {
            material.renderQueue = Int(fields, "m_CustomRenderQueue", 3000);
            material.enableInstancing = Bool(fields, "m_EnableInstancingVariants");
            Dictionary<string, object> tags = Dict(fields["m_StringTagMap"]);
            foreach (KeyValuePair<string, object> pair in tags)
                material.SetOverrideTag(pair.Key, Str(pair.Value));
            foreach (string pass in List(fields["m_DisabledShaderPasses"]).Cast<object>().Select(Str))
                material.SetShaderPassEnabled(pass, false);
            Dictionary<string, object> saved = Dict(fields["m_SavedProperties"]);
            foreach (KeyValuePair<string, object> pair in Dict(saved["m_TexEnvs"]))
            {
                if (!material.HasProperty(pair.Key))
                    continue;
                Dictionary<string, object> env = Dict(pair.Value);
                long pathId = Long(Dict(env["m_Texture"]), "m_PathID");
                Texture2D value = pathId == 0 ? null : texture;
                if (pathId != 0)
                    Require(pair.Key == "_RefractTex" && value != null, "Unexpected CharInfo texture PPtr at " + pair.Key);
                material.SetTexture(pair.Key, value);
                material.SetTextureScale(pair.Key, Vector2Value(env["m_Scale"]));
                material.SetTextureOffset(pair.Key, Vector2Value(env["m_Offset"]));
            }
            foreach (KeyValuePair<string, object> pair in Dict(saved["m_Floats"]))
            {
                if (!material.HasProperty(pair.Key))
                    continue;
                material.SetFloat(pair.Key, Float(pair.Value));
            }
            foreach (KeyValuePair<string, object> pair in Dict(saved["m_Ints"]))
            {
                if (!material.HasProperty(pair.Key))
                    continue;
                material.SetInt(pair.Key, Int(pair.Value));
            }
            foreach (KeyValuePair<string, object> pair in Dict(saved["m_Colors"]))
            {
                if (!material.HasProperty(pair.Key))
                    continue;
                material.SetColor(pair.Key, ColorValue(pair.Value));
            }
            material.shaderKeywords = List(fields["m_ValidKeywords"]).Cast<object>().Select(Str).ToArray();
            Require(material.HasProperty("_RefractTex") && material.GetTexture("_RefractTex") == texture,
                "CharInfo exact _RefractTex gate failed");
            Require(material.HasProperty("_UseRBOffset") && Nearly(material.GetFloat("_UseRBOffset"), 1f),
                "CharInfo exact _UseRBOffset gate failed");
        }

        private static UnityEngine.Object ResolveReference(object value, Material material, string owner)
        {
            Dictionary<string, object> pptr = Dict(value);
            long pathId = Long(pptr, "m_PathID");
            if (pathId == 0)
                return null;
            if (owner == "ParticleSystemRenderer" && pathId == 4388811075012960551L)
                return material;
            throw new InvalidOperationException("Unknown non-null CharInfo PPtr " + pathId + " at " + owner);
        }

        private static UnityEngine.Object ResolveReferenceForVerify(object value, Material material)
        {
            long pathId = Long(Dict(value), "m_PathID");
            return pathId == 0 ? null : material;
        }

        private static void ApplySerializedDictionary(
            SerializedObject serialized,
            Dictionary<string, object> values,
            string owner,
            Func<object, UnityEngine.Object> resolve,
            params string[] skipped)
        {
            HashSet<string> skip = new HashSet<string>(skipped, StringComparer.Ordinal);
            serialized.UpdateIfRequiredOrScript();
            foreach (KeyValuePair<string, object> pair in values)
            {
                if (skip.Contains(pair.Key))
                    continue;
                SerializedProperty property = serialized.FindProperty(pair.Key);
                if (property == null && KnownRetailOnlyFields.Contains(pair.Key))
                    continue;
                Require(property != null, "Unity serialized property missing at " + owner + "." + pair.Key);
                ApplyProperty(property, pair.Value, owner + "." + pair.Key, resolve);
            }
            serialized.ApplyModifiedPropertiesWithoutUndo();
        }

        private static void ApplyProperty(
            SerializedProperty property,
            object value,
            string path,
            Func<object, UnityEngine.Object> resolve)
        {
            if (property.propertyType == SerializedPropertyType.ObjectReference)
            {
                property.objectReferenceValue = resolve(value);
                return;
            }
            if (property.isArray && property.propertyType != SerializedPropertyType.String)
            {
                IList list = List(value);
                property.arraySize = list.Count;
                for (int index = 0; index < list.Count; index++)
                    ApplyProperty(property.GetArrayElementAtIndex(index), list[index], path + "[" + index + "]", resolve);
                return;
            }
            switch (property.propertyType)
            {
                case SerializedPropertyType.Integer: property.longValue = Long(value); return;
                case SerializedPropertyType.Boolean: property.boolValue = Bool(value); return;
                case SerializedPropertyType.Float: property.floatValue = Float(value); return;
                case SerializedPropertyType.String: property.stringValue = Str(value); return;
                case SerializedPropertyType.Color: property.colorValue = ColorValue(value); return;
                case SerializedPropertyType.Enum: property.enumValueIndex = Int(value); return;
                case SerializedPropertyType.Vector2: property.vector2Value = Vector2Value(value); return;
                case SerializedPropertyType.Vector3: property.vector3Value = Vector3Value(value); return;
                case SerializedPropertyType.Vector4: property.vector4Value = Vector4Value(value); return;
                case SerializedPropertyType.Quaternion: property.quaternionValue = QuaternionValue(value); return;
                case SerializedPropertyType.AnimationCurve: property.animationCurveValue = CurveValue(value); return;
#if UNITY_2021_2_OR_NEWER
                case SerializedPropertyType.Gradient: property.gradientValue = GradientValue(value); return;
#endif
                case SerializedPropertyType.LayerMask: property.intValue = LayerMaskValue(value); return;
                case SerializedPropertyType.Generic:
                    foreach (KeyValuePair<string, object> pair in Dict(value))
                    {
                        SerializedProperty child = property.FindPropertyRelative(pair.Key);
                        if (child == null && KnownRetailOnlyFields.Contains(pair.Key))
                            continue;
                        Require(child != null, "Unity serialized child missing at " + path + "." + pair.Key);
                        ApplyProperty(child, pair.Value, path + "." + pair.Key, resolve);
                    }
                    return;
                default: throw new NotSupportedException("Unsupported serialized property " + path + " (" + property.propertyType + ")");
            }
        }

        private static void VerifySerializedDictionary(
            SerializedObject serialized,
            Dictionary<string, object> values,
            string owner,
            Func<object, UnityEngine.Object> resolve,
            params string[] skipped)
        {
            HashSet<string> skip = new HashSet<string>(skipped, StringComparer.Ordinal);
            serialized.UpdateIfRequiredOrScript();
            foreach (KeyValuePair<string, object> pair in values)
            {
                if (skip.Contains(pair.Key))
                    continue;
                SerializedProperty property = serialized.FindProperty(pair.Key);
                if (property == null && KnownRetailOnlyFields.Contains(pair.Key))
                    continue;
                Require(property != null, "Unity serialized property missing at " + owner + "." + pair.Key);
                VerifyProperty(property, pair.Value, owner + "." + pair.Key, resolve);
            }
        }

        private static void VerifyProperty(
            SerializedProperty property,
            object value,
            string path,
            Func<object, UnityEngine.Object> resolve)
        {
            if (property.propertyType == SerializedPropertyType.ObjectReference)
            {
                Require(property.objectReferenceValue == resolve(value), "Object reference mismatch at " + path);
                return;
            }
            if (property.isArray && property.propertyType != SerializedPropertyType.String)
            {
                IList list = List(value);
                Require(property.arraySize == list.Count, "Array length mismatch at " + path);
                for (int index = 0; index < list.Count; index++)
                    VerifyProperty(property.GetArrayElementAtIndex(index), list[index], path + "[" + index + "]", resolve);
                return;
            }
            switch (property.propertyType)
            {
                case SerializedPropertyType.Integer: Require(property.longValue == Long(value), "Integer mismatch at " + path); return;
                case SerializedPropertyType.Boolean: Require(property.boolValue == Bool(value), "Boolean mismatch at " + path); return;
                case SerializedPropertyType.Float: Require(Nearly(property.floatValue, Float(value)), "Float mismatch at " + path); return;
                case SerializedPropertyType.String: Require(property.stringValue == Str(value), "String mismatch at " + path); return;
                case SerializedPropertyType.Color: Require(Nearly(property.colorValue, ColorValue(value)), "Color mismatch at " + path); return;
                case SerializedPropertyType.Enum: Require(property.enumValueIndex == Int(value), "Enum mismatch at " + path); return;
                case SerializedPropertyType.Vector2: Require(Nearly(property.vector2Value, Vector2Value(value)), "Vector2 mismatch at " + path); return;
                case SerializedPropertyType.Vector3: Require(Nearly(property.vector3Value, Vector3Value(value)), "Vector3 mismatch at " + path); return;
                case SerializedPropertyType.Vector4: Require(Nearly(property.vector4Value, Vector4Value(value)), "Vector4 mismatch at " + path); return;
                case SerializedPropertyType.Quaternion: Require(Nearly(property.quaternionValue, QuaternionValue(value)), "Quaternion mismatch at " + path); return;
                case SerializedPropertyType.AnimationCurve: VerifyCurve(property.animationCurveValue, CurveValue(value), path); return;
#if UNITY_2021_2_OR_NEWER
                case SerializedPropertyType.Gradient: VerifyGradient(property.gradientValue, GradientValue(value), path); return;
#endif
                case SerializedPropertyType.LayerMask: Require(property.intValue == LayerMaskValue(value), "Layer mask mismatch at " + path); return;
                case SerializedPropertyType.Generic:
                    foreach (KeyValuePair<string, object> pair in Dict(value))
                    {
                        SerializedProperty child = property.FindPropertyRelative(pair.Key);
                        if (child == null && KnownRetailOnlyFields.Contains(pair.Key))
                            continue;
                        Require(child != null, "Unity serialized child missing at " + path + "." + pair.Key);
                        VerifyProperty(child, pair.Value, path + "." + pair.Key, resolve);
                    }
                    return;
                default: throw new NotSupportedException("Unsupported serialized verification property " + path + " (" + property.propertyType + ")");
            }
        }

        private static AnimationCurve CurveValue(object value)
        {
            Dictionary<string, object> data = Dict(value);
            var keys = new List<Keyframe>();
            foreach (object item in List(data["m_Curve"]))
            {
                Dictionary<string, object> key = Dict(item);
                Keyframe frame = new Keyframe(Float(key, "time"), Float(key, "value"), Float(key, "inSlope"), Float(key, "outSlope"), Float(key, "inWeight"), Float(key, "outWeight"));
                frame.weightedMode = (WeightedMode)Int(key, "weightedMode");
                keys.Add(frame);
            }
            return new AnimationCurve(keys.ToArray())
            {
                preWrapMode = (WrapMode)Int(data, "m_PreInfinity"),
                postWrapMode = (WrapMode)Int(data, "m_PostInfinity"),
            };
        }

        private static Gradient GradientValue(object value)
        {
            Dictionary<string, object> data = Dict(value);
            int colorCount = Int(data, "m_NumColorKeys");
            int alphaCount = Int(data, "m_NumAlphaKeys");
            var colors = new GradientColorKey[colorCount];
            var alphas = new GradientAlphaKey[alphaCount];
            for (int i = 0; i < colorCount; i++) colors[i] = new GradientColorKey(ColorValue(data["key" + i]), Int(data, "ctime" + i) / 65535f);
            for (int i = 0; i < alphaCount; i++) alphas[i] = new GradientAlphaKey(ColorValue(data["key" + i]).a, Int(data, "atime" + i) / 65535f);
            var gradient = new Gradient { mode = (GradientMode)Int(data, "m_Mode") };
            gradient.SetKeys(colors, alphas);
            return gradient;
        }

        private static void VerifyCurve(AnimationCurve actual, AnimationCurve expected, string path)
        {
            Require(actual != null && actual.length == expected.length, "Curve key count mismatch at " + path);
            Require(actual.preWrapMode == expected.preWrapMode && actual.postWrapMode == expected.postWrapMode, "Curve wrap mismatch at " + path);
            for (int i = 0; i < actual.length; i++)
            {
                Keyframe a = actual.keys[i];
                Keyframe e = expected.keys[i];
                Require(Nearly(a.time, e.time) && Nearly(a.value, e.value) && Nearly(a.inTangent, e.inTangent) && Nearly(a.outTangent, e.outTangent) && Nearly(a.inWeight, e.inWeight) && Nearly(a.outWeight, e.outWeight) && a.weightedMode == e.weightedMode, "Curve mismatch at " + path + "[" + i + "]");
            }
        }

        private static void VerifyGradient(Gradient actual, Gradient expected, string path)
        {
            Require(actual != null && actual.mode == expected.mode, "Gradient mode mismatch at " + path);
            Require(actual.colorKeys.Length == expected.colorKeys.Length && actual.alphaKeys.Length == expected.alphaKeys.Length, "Gradient key count mismatch at " + path);
            for (int i = 0; i < actual.colorKeys.Length; i++) Require(Nearly(actual.colorKeys[i].color, expected.colorKeys[i].color) && Nearly(actual.colorKeys[i].time, expected.colorKeys[i].time), "Gradient color mismatch at " + path);
            for (int i = 0; i < actual.alphaKeys.Length; i++) Require(Nearly(actual.alphaKeys[i].alpha, expected.alphaKeys[i].alpha) && Nearly(actual.alphaKeys[i].time, expected.alphaKeys[i].time), "Gradient alpha mismatch at " + path);
        }

        private static Dictionary<string, object> Dict(object value) => value as Dictionary<string, object> ?? throw new InvalidOperationException("Expected JSON object");
        private static IList List(object value) => value as IList ?? throw new InvalidOperationException("Expected JSON array");
        private static string Str(object value) => Convert.ToString(value, CultureInfo.InvariantCulture) ?? string.Empty;
        private static string Str(Dictionary<string, object> values, string key) => Str(values[key]);
        private static bool Bool(object value) => Convert.ToBoolean(value, CultureInfo.InvariantCulture);
        private static bool Bool(Dictionary<string, object> values, string key) => Bool(values[key]);
        private static int Int(object value) => Convert.ToInt32(value, CultureInfo.InvariantCulture);
        private static int Int(Dictionary<string, object> values, string key, int fallback = 0) => values.TryGetValue(key, out object value) ? Int(value) : fallback;
        private static int LayerMaskValue(object value)
        {
            if (value is Dictionary<string, object> dict && dict.TryGetValue("m_Bits", out object bits))
                return unchecked((int)(uint)Long(bits));
            return unchecked((int)Long(value));
        }
        private static long Long(object value) => Convert.ToInt64(value, CultureInfo.InvariantCulture);
        private static long Long(Dictionary<string, object> values, string key) => Long(values[key]);
        private static float Float(object value) => Convert.ToSingle(value, CultureInfo.InvariantCulture);
        private static float Float(Dictionary<string, object> values, string key) => Float(values[key]);
        private static Vector2 Vector2Value(object value) { Dictionary<string, object> d = Dict(value); return new Vector2(FloatEither(d, "x", "X"), FloatEither(d, "y", "Y")); }
        private static Vector3 Vector3Value(object value) { Dictionary<string, object> d = Dict(value); return new Vector3(FloatEither(d, "x", "X"), FloatEither(d, "y", "Y"), FloatEither(d, "z", "Z")); }
        private static Vector4 Vector4Value(object value) { Dictionary<string, object> d = Dict(value); return new Vector4(FloatEither(d, "x", "X"), FloatEither(d, "y", "Y"), FloatEither(d, "z", "Z"), FloatEither(d, "w", "W")); }
        private static Quaternion QuaternionValue(object value) { Dictionary<string, object> d = Dict(value); return new Quaternion(FloatEither(d, "x", "X"), FloatEither(d, "y", "Y"), FloatEither(d, "z", "Z"), FloatEither(d, "w", "W", 1f)); }
        private static Color ColorValue(object value) { Dictionary<string, object> d = Dict(value); return new Color(FloatEither(d, "r", "R"), FloatEither(d, "g", "G"), FloatEither(d, "b", "B"), FloatEither(d, "a", "A", 1f)); }
        private static float FloatEither(Dictionary<string, object> d, string a, string b, float fallback = 0f) => d.TryGetValue(a, out object value) ? Float(value) : (d.TryGetValue(b, out value) ? Float(value) : fallback);
        private static bool Nearly(float a, float b) => Mathf.Abs(a - b) <= 1e-5f;
        private static bool Nearly(Vector2 a, Vector2 b) => (a - b).sqrMagnitude <= 1e-10f;
        private static bool Nearly(Vector3 a, Vector3 b) => (a - b).sqrMagnitude <= 1e-10f;
        private static bool Nearly(Vector4 a, Vector4 b) => (a - b).sqrMagnitude <= 1e-10f;
        private static bool Nearly(Quaternion a, Quaternion b) => Mathf.Abs(a.x - b.x) <= 1e-5f && Mathf.Abs(a.y - b.y) <= 1e-5f && Mathf.Abs(a.z - b.z) <= 1e-5f && Mathf.Abs(a.w - b.w) <= 1e-5f;
        private static bool Nearly(Color a, Color b) => Nearly(a.r, b.r) && Nearly(a.g, b.g) && Nearly(a.b, b.b) && Nearly(a.a, b.a);
        private static void Require(bool condition, string message) { if (!condition) throw new InvalidOperationException(message); }
        private static string AssetToAbsolute(string path) => Path.GetFullPath(Path.Combine(Application.dataPath, path.Substring("Assets/".Length).Replace('/', Path.DirectorySeparatorChar)));
        private static string RepoRelativeToAbsolute(string path) => Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", path.Replace('/', Path.DirectorySeparatorChar)));
        private static void EnsureFolder(string assetPath) { string current = "Assets"; foreach (string segment in assetPath.Substring("Assets/".Length).Split('/')) { string next = current + "/" + segment; if (!AssetDatabase.IsValidFolder(next)) AssetDatabase.CreateFolder(current, segment); current = next; } }
        private static void CopyIfDifferent(string source, string destination) { Directory.CreateDirectory(Path.GetDirectoryName(destination)); if (!File.Exists(destination) || Sha256(source) != Sha256(destination)) File.Copy(source, destination, true); }
        private static string Sha256(string path) { using (SHA256 hash = SHA256.Create()) using (FileStream stream = File.OpenRead(path)) return BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", string.Empty); }
    }
}
