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
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Builds the source-scoped start_02 sibling diagnostic prefab.
    ///
    /// The imported OBJ/PNG/FBX files are inspection inputs only.  This file
    /// intentionally leaves native mesh payload, exact shader variants, and
    /// runtime visibility closed.  Plane009 is explicitly provisional
    /// converted geometry until a native mesh payload is admitted.
    /// </summary>
    public static class EndfieldLiZhiyanStart02DiagnosticPrefabImporter
    {
        public const string ContractPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/" +
            "lizhiyan_overview_start_02_03_effects.json";
        public const string GeneratedRoot =
            "Assets/EndfieldGraphShaderLab/Generated/Diagnostics/LiZhiyanStart02";
        public const string PrefabPath = GeneratedRoot + "/Prefabs/" +
            "P_fxui_lizhiyan_overview_start_02_DIAGNOSTIC.prefab";

        private const string EffectName = "P_fxui_lizhiyan_overview_start_02";
        private const string ShaderName =
            "Endfield/Recovered/LiZhiyanStart01Diagnostic";
        private const string ExpectedSchema =
            "endfield.lizhiyan-overview-static-sibling-effects.v1";
        private const string ExpectedStatus =
            "start02_start03_serialized_sources_closed_visible_fail_closed";
        private const string AggregateSha256 =
            "AB587FDA1E0AEC1761A10F334959541FA0217347E595D18415850791AE33545B";
        private const long RootGameObjectPathId = 2896713466425102497L;
        private const long RootTransformPathId = -210178290990919519L;
        private const long EffectSettingPathId = 3940221264379367585L;
        private const long AnimatorPathId = 9077272783571767457L;
        private const long AnimationHelperPathId = 8739770745933123745L;
        private const long ClipPathId = 7360398354216100382L;
        private const float EffectDuration = 5f;
        private const float ClipSampleRate = 30f;
        private const float ClipStopTime = 6.366667f;
        private const long MeshPathId = 7032717393607757449L;
        private const string MeshRelativePath =
            "export_full/recovered/AnimeStudio-cli/StreamingAssets/" +
            "convert_by_type/Mesh/Plane009_p61993B3563B38E89.obj";
        private const string MeshSha256 =
            "E900D483F3CBE934E7CC26DE1EC1AB28732C981A4282DC96571822C6D0A3B7B8";
        private const string FbxProjectPath =
            "Assets/EndfieldGraphShaderLab/TempLiZhiyanFbxInspection/" +
            "P_fxui_lizhiyan_overview_start_02_p7DF8F380D21DD0A1.fbx";
        private const string FbxSha256 =
            "C85FD61C6004AC6DEE2BEE98B281A03FB7ADF8764C450ECF0881DBB1DE41B862";
        private const string ClipProjectPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/" +
            "A_fxui__lizhiyan_overview_start_01.anim";
        private const string ClipSha256 =
            "C1D7846FB29A9AF720B2760BA2EEA97B870CAC8DF101DADE797A2301778FF920";

        private static readonly Dictionary<long, string> MaterialModes =
            new Dictionary<long, string>
            {
                { -481371258366057841L, "9" },
                { 2540816063756981481L, "9" },
                { -2434886401441015548L, "11" },
            };

        private sealed class ImportedSources
        {
            public readonly Dictionary<long, Mesh> meshes =
                new Dictionary<long, Mesh>();
            public readonly Dictionary<long, Texture2D> textures =
                new Dictionary<long, Texture2D>();
            public AnimationClip clip;
        }

        private sealed class MaterialReport
        {
            public int applied;
            public int unsupported;
        }

        [MenuItem("Endfield/Character Recovery Lab/Build Li Zhiyan start_02 Diagnostic Prefab")]
        public static void BuildAndValidate()
        {
            Dictionary<string, object> contract = ReadContract();
            Dictionary<string, object> effect = SelectEffect(contract);
            ValidateContractAndSourceHashes(contract, effect);
            ImportedSources sources = ImportPinnedSources(contract, effect);
            Shader shader = Shader.Find(ShaderName);
            Require(shader != null, "Missing Li Zhiyan diagnostic shader: " + ShaderName);

            var materials = new Dictionary<long, Material>();
            int applied = 0;
            int unsupported = 0;
            foreach (object item in List(effect, "materials"))
            {
                MaterialReport report;
                Dictionary<string, object> source = Dict(item);
                Material material = BuildMaterial(source, shader, sources.textures, out report);
                materials[Long(source, "pathID")] = material;
                applied += report.applied;
                unsupported += report.unsupported;
            }

            GameObject root = null;
            try
            {
                root = BuildHierarchy(contract, effect, sources, materials);
                string reason = string.Empty;
                EndfieldLiZhiyanBehavioralAnimationSimulation simulation =
                    root.GetComponent<EndfieldLiZhiyanBehavioralAnimationSimulation>();
                bool constructed = simulation != null && simulation.TryConstructSimulation(out reason);
                Require(constructed,
                    "Li Zhiyan start_02 behavioral simulation failed: " + reason);
                EnsureFolder(GeneratedRoot);
                EnsureFolder(GeneratedRoot + "/Prefabs");
                PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
            }
            finally
            {
                if (root != null)
                    UnityEngine.Object.DestroyImmediate(root);
            }

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            EndfieldLiZhiyanStart02DiagnosticPrefabValidator.ValidateGenerated(
                PrefabPath, unsupported, applied);
            Debug.Log("[Endfield Li Zhiyan] start_02 diagnostic prefab built and " +
                "validated; provisional Plane009 geometry; visibleAdmission=false.");
        }

        public static void ValidateExisting()
        {
            EndfieldLiZhiyanStart02DiagnosticPrefabValidator.ValidateGenerated(
                PrefabPath, -1, -1);
        }

        internal static Dictionary<string, object> ReadContract()
        {
            string path = ProjectAbsolute(ContractPath);
            Require(File.Exists(path), "Missing Li Zhiyan sibling contract: " + path);
            return Dict(ManifestMiniJson.Deserialize(File.ReadAllText(path, Encoding.UTF8)));
        }

        private static Dictionary<string, object> SelectEffect(
            Dictionary<string, object> contract)
        {
            Require(Str(contract, "schema") == ExpectedSchema &&
                Str(contract, "status") == ExpectedStatus,
                "Li Zhiyan sibling contract schema/status drifted");
            foreach (object item in List(contract, "effects"))
            {
                Dictionary<string, object> effect = Dict(item);
                if (Str(effect, "effectName") == EffectName)
                    return effect;
            }
            throw new InvalidOperationException("start_02 effect is absent from sibling contract");
        }

        private static void ValidateContractAndSourceHashes(
            Dictionary<string, object> contract, Dictionary<string, object> effect)
        {
            Dictionary<string, object> summary = Dict(contract["summary"]);
            Require(Str(summary, "sourceAggregateSha256") == AggregateSha256 &&
                Long(summary, "effects") == 2L && Long(summary, "staticMeshNodes") == 6L,
                "Li Zhiyan sibling aggregate identity drifted");
            Dictionary<string, object> effectSummary = Dict(effect["summary"]);
            Require(Long(effectSummary, "hierarchyNodes") == 4L &&
                Long(effectSummary, "staticMeshNodes") == 3L &&
                Long(effectSummary, "particleSystems") == 0L &&
                Long(effectSummary, "materials") == 3L,
                "Li Zhiyan start_02 census drifted");
            Dictionary<string, object> setting = Dict(effect["effectSetting"]);
            Require(Long(setting, "pathID") == EffectSettingPathId,
                "Li Zhiyan start_02 EffectSetting PathID drifted");
            Dictionary<string, object> timing = Dict(setting["timing"]);
            Require(Math.Abs(Float(timing, "duration") - EffectDuration) < 0.0001f,
                "Li Zhiyan start_02 duration drifted");
            Dictionary<string, object> animation = Dict(effect["animation"]);
            Require(Long(animation, "animatorPathID") == AnimatorPathId &&
                Long(animation, "helperPathID") == AnimationHelperPathId,
                "Li Zhiyan start_02 Animator/helper identity drifted");
            Dictionary<string, object> clip = Dict(animation["startAnimationClip"]);
            Require(Long(clip, "pathID") == ClipPathId,
                "Li Zhiyan shared clip contract drifted");
            ValidateHash(RepositoryAbsolute(MeshRelativePath), MeshSha256, "provisional Plane009 OBJ");
            ValidateHash(ProjectAbsolute(FbxProjectPath), FbxSha256, "start_02 Animator FBX");
            ValidateHash(ProjectAbsolute(ClipProjectPath), ClipSha256, "shared start clip");

            HashSet<long> meshIds = new HashSet<long>();
            foreach (object item in List(effect, "meshDependencies"))
            {
                Dictionary<string, object> mesh = Dict(item);
                long id = Long(mesh, "pathID");
                Dictionary<string, object> obj = Dict(mesh["convertedObj"]);
                Require(id == MeshPathId && Str(obj, "path") == MeshRelativePath &&
                    Str(obj, "sha256").Equals(MeshSha256, StringComparison.OrdinalIgnoreCase),
                    "Li Zhiyan start_02 Plane009 source contract drifted");
                meshIds.Add(id);
            }
            Require(meshIds.SetEquals(new[] { MeshPathId }),
                "Li Zhiyan start_02 mesh dependency census drifted");
            HashSet<long> materialIds = new HashSet<long>();
            foreach (object item in List(effect, "materials"))
            {
                Dictionary<string, object> material = Dict(item);
                long id = Long(material, "pathID");
                Require(MaterialModes.ContainsKey(id), "Unexpected start_02 material: " + id);
                materialIds.Add(id);
            }
            Require(materialIds.SetEquals(MaterialModes.Keys),
                "Li Zhiyan start_02 material dependency census drifted");
            foreach (object item in List(contract, "textureDependencies"))
            {
                Dictionary<string, object> texture = Dict(item);
                Dictionary<string, object> png = Dict(texture["convertedPng"]);
                ValidateHash(RepositoryAbsolute(Str(png, "path")), Str(png, "sha256"),
                    "Li Zhiyan texture " + Long(texture, "pathID"));
            }
        }

        private static ImportedSources ImportPinnedSources(
            Dictionary<string, object> contract, Dictionary<string, object> effect)
        {
            EnsureFolder(GeneratedRoot);
            EnsureFolder(GeneratedRoot + "/Source");
            string meshAssetPath = GeneratedRoot + "/Source/" + Path.GetFileName(MeshRelativePath);
            File.Copy(RepositoryAbsolute(MeshRelativePath), ProjectAbsolute(meshAssetPath), true);
            AssetDatabase.ImportAsset(meshAssetPath, ImportAssetOptions.ForceUpdate);
            Mesh mesh = AssetDatabase.LoadAllAssetsAtPath(meshAssetPath).OfType<Mesh>()
                .FirstOrDefault(value => value != null);
            Require(mesh != null, "Provisional Plane009 OBJ did not import as a Unity Mesh");

            string fbxAssetPath = GeneratedRoot + "/Source/" + Path.GetFileName(FbxProjectPath);
            File.Copy(ProjectAbsolute(FbxProjectPath), ProjectAbsolute(fbxAssetPath), true);
            AssetDatabase.ImportAsset(fbxAssetPath, ImportAssetOptions.ForceUpdate);
            Require(AssetDatabase.LoadAssetAtPath<GameObject>(fbxAssetPath) != null,
                "start_02 Animator FBX did not import as a GameObject");

            var result = new ImportedSources();
            result.meshes[MeshPathId] = mesh;
            foreach (object item in List(contract, "textureDependencies"))
            {
                Dictionary<string, object> texture = Dict(item);
                Dictionary<string, object> png = Dict(texture["convertedPng"]);
                string sourcePath = Str(png, "path");
                string assetPath = GeneratedRoot + "/Source/" + Path.GetFileName(sourcePath);
                File.Copy(RepositoryAbsolute(sourcePath), ProjectAbsolute(assetPath), true);
                AssetDatabase.ImportAsset(assetPath, ImportAssetOptions.ForceUpdate);
                Texture2D imported = AssetDatabase.LoadAssetAtPath<Texture2D>(assetPath);
                Require(imported != null, "Li Zhiyan texture did not import: " + assetPath);
                result.textures[Long(texture, "pathID")] = imported;
            }
            AssetDatabase.ImportAsset(ClipProjectPath, ImportAssetOptions.ForceUpdate);
            result.clip = AssetDatabase.LoadAssetAtPath<AnimationClip>(ClipProjectPath);
            Require(result.clip != null &&
                Math.Abs(result.clip.frameRate - ClipSampleRate) < 0.0001f &&
                Math.Abs(result.clip.length - ClipStopTime) < 0.0001f,
                "Shared Li Zhiyan animation clip identity drifted");
            return result;
        }

        private static Material BuildMaterial(Dictionary<string, object> source, Shader shader,
            Dictionary<long, Texture2D> textures, out MaterialReport report)
        {
            report = new MaterialReport();
            long id = Long(source, "pathID");
            string assetPath = GeneratedRoot + "/Materials/" + Safe(Str(source, "name")) +
                "_p" + unchecked((ulong)id).ToString("X16", CultureInfo.InvariantCulture) + ".mat";
            EnsureFolder(GeneratedRoot + "/Materials");
            Material material = AssetDatabase.LoadAssetAtPath<Material>(assetPath);
            if (material == null)
            {
                material = new Material(shader);
                AssetDatabase.CreateAsset(material, assetPath);
            }
            material.shader = shader;
            material.name = Str(source, "name");
            material.renderQueue = Int(source, "customRenderQueue");
            Dictionary<string, object> payload = Dict(source["payload"]);
            Dictionary<string, object> saved = Dict(payload["m_SavedProperties"]);
            ApplyFloats(material, DictOrEmpty(saved, "m_Floats"), report);
            ApplyFloats(material, DictOrEmpty(saved, "m_Ints"), report);
            ApplyColors(material, DictOrEmpty(saved, "m_Colors"), report);
            ApplyTextures(material, DictOrEmpty(saved, "m_TexEnvs"), textures, report);
            IList keywords = ListValue(payload, "m_ValidKeywords");
            material.shaderKeywords = keywords == null ? Array.Empty<string>() :
                keywords.Cast<object>().Select(value => Convert.ToString(value,
                    CultureInfo.InvariantCulture)).ToArray();
            Require(material.HasProperty("_LiMaterialMode"),
                "Li diagnostic shader lost _LiMaterialMode");
            // Contract-directed diagnostic route: 12/13 are mode 9; 14 is mode 11.
            material.SetFloat("_LiMaterialMode", float.Parse(MaterialModes[id],
                CultureInfo.InvariantCulture));
            EditorUtility.SetDirty(material);
            return material;
        }

        private static GameObject BuildHierarchy(Dictionary<string, object> contract,
            Dictionary<string, object> effect, ImportedSources sources,
            Dictionary<long, Material> materials)
        {
            var objects = new Dictionary<long, GameObject>();
            var transforms = new Dictionary<long, long>();
            IList rows = List(effect, "hierarchyNodes");
            foreach (object item in rows)
            {
                Dictionary<string, object> row = Dict(item);
                Dictionary<string, object> go = Dict(row["gameObject"]);
                long goId = Long(row, "gameObjectPathID");
                GameObject generated = new GameObject(Str(go, "m_Name"));
                objects[goId] = generated;
                transforms[Long(row, "transformPathID")] = goId;
            }
            foreach (object item in rows)
            {
                Dictionary<string, object> row = Dict(item);
                Dictionary<string, object> transform = Dict(row["transform"]);
                long goId = Long(row, "gameObjectPathID");
                long father = PPtrId(transform["m_Father"]);
                if (father != 0L)
                    objects[goId].transform.SetParent(objects[transforms[father]].transform, false);
                objects[goId].transform.localPosition = Vector3Value(transform["m_LocalPosition"]);
                objects[goId].transform.localRotation = QuaternionValue(transform["m_LocalRotation"]);
                objects[goId].transform.localScale = Vector3Value(transform["m_LocalScale"]);
            }
            GameObject root = objects[RootGameObjectPathId];
            Require(root != null && root.name == EffectName && root.transform.parent == null,
                "Li Zhiyan start_02 diagnostic root drifted");
            root.AddComponent<Animator>();

            var markerNodes = new List<EndfieldRecoveredStaticMeshHierarchyNodeSource>();
            foreach (object item in rows)
            {
                Dictionary<string, object> row = Dict(item);
                long id = Long(row, "gameObjectPathID");
                markerNodes.Add(new EndfieldRecoveredStaticMeshHierarchyNodeSource
                {
                    hierarchy = Str(row, "hierarchy"),
                    gameObjectPathId = id,
                    transformPathId = Long(row, "transformPathID"),
                    generatedTransform = objects[id].transform,
                });
            }
            var markerMeshes = new List<EndfieldRecoveredStaticMeshNodeSource>();
            var probes = new List<EndfieldLiZhiyanBehavioralAnimationSimulation.RendererProbeBinding>();
            foreach (object item in List(effect, "staticMeshNodes"))
            {
                Dictionary<string, object> row = Dict(item);
                long goId = Long(row, "gameObjectPathID");
                GameObject host = objects[goId];
                MeshFilter filter = host.AddComponent<MeshFilter>();
                MeshRenderer renderer = host.AddComponent<MeshRenderer>();
                long meshId = Long(Dict(row["mesh"]), "pathID");
                filter.sharedMesh = sources.meshes[meshId];
                var assigned = new List<Material>();
                var materialIds = new List<long>();
                foreach (object materialItem in List(row, "materials"))
                {
                    long materialId = PPtrId(materialItem);
                    Require(materials.ContainsKey(materialId), "Material dependency is absent: " + materialId);
                    assigned.Add(materials[materialId]);
                    materialIds.Add(materialId);
                }
                renderer.sharedMaterials = assigned.ToArray();
                ApplyRendererFields(renderer, row["meshRenderer"] as Dictionary<string, object>);
                markerMeshes.Add(new EndfieldRecoveredStaticMeshNodeSource
                {
                    hierarchy = Str(row, "hierarchy"),
                    gameObjectPathId = goId,
                    transformPathId = FindTransformId(rows, goId),
                    meshFilterPathId = Long(row, "meshFilterPathID"),
                    meshRendererPathId = Long(row, "meshRendererPathID"),
                    meshPathId = meshId,
                    materialPathIds = materialIds.ToArray(),
                    shaderPathIds = materialIds.Select(value => -1430105248647086886L).ToArray(),
                    generatedMeshFilter = filter,
                    generatedMeshRenderer = renderer,
                    sourceRendererEnabled = renderer.enabled,
                    nativeMeshPayloadApplied = false,
                    nativeRendererPayloadApplied = false,
                    nativeTexturePayloadsApplied = false,
                    exactShaderVariantsApplied = false,
                    rendererFailClosedForUnrecoveredShader = true,
                });
                probes.Add(new EndfieldLiZhiyanBehavioralAnimationSimulation.RendererProbeBinding(
                    Long(row, "meshRendererPathID"), Str(row, "hierarchy"), renderer));
            }

            Dictionary<string, object> animation = Dict(effect["animation"]);
            Dictionary<string, object> clip = Dict(animation["startAnimationClip"]);
            EditorCurveBinding[] importedBindings = AnimationUtility.GetCurveBindings(sources.clip);
            string[] siblingPaths = importedBindings
                .Where(value => value.path == "S_fx_lzy_fenweiqiliu_02" ||
                    value.path == "S_fx_lzy_fenweiqiliu_02 (1)" ||
                    value.path == "S_fx_lzy_fenweiqiliu_02 (3)")
                .Select(value => value.path).Distinct(StringComparer.Ordinal).ToArray();
            string[] siblingProperties = importedBindings
                .Where(value => siblingPaths.Contains(value.path))
                .Select(value => value.propertyName).Distinct(StringComparer.Ordinal).ToArray();
            EndfieldRecoveredStaticMeshEffectSource marker =
                root.AddComponent<EndfieldRecoveredStaticMeshEffectSource>();
            marker.contractSchema = ExpectedSchema;
            marker.effectRoot = EffectName;
            marker.sourceHierarchy = EffectName;
            marker.sourceGameObjectPathId = RootGameObjectPathId;
            marker.sourceTransformPathId = RootTransformPathId;
            marker.sourceEffectSettingPathId = EffectSettingPathId;
            marker.sourcePayloadApplied = false;
            marker.sourceEffectSettingPayloadApplied = false;
            marker.sourceEffectLoops = false;
            marker.sourceEffectDuration = EffectDuration;
            marker.sourceEffectDelay = 0f;
            marker.sourceEffectRandomDelay = 0f;
            marker.sourceAnimatorPathId = AnimatorPathId;
            marker.sourceAnimationHelperPathId = AnimationHelperPathId;
            marker.sourceStartAnimationClipPathId = ClipPathId;
            marker.sourceStartAnimationClip = sources.clip;
            marker.sourceStartAnimationClipName = "A_fxui__lizhiyan_overview_start_01";
            marker.sourceStartAnimationSampleRate = ClipSampleRate;
            marker.sourceStartAnimationStopTime = ClipStopTime;
            marker.sourceAnimationTargetPaths = siblingPaths;
            marker.sourceAnimationTargetPathHashes = siblingPaths
                .Select(Animator.StringToHash).Select(value => (long)value).ToArray();
            marker.sourceAnimationMaterialProperties = siblingProperties;
            marker.sourceAnimationMaterialPropertyHashes = siblingProperties
                .Select(Shader.PropertyToID).Select(value => (long)value).ToArray();
            marker.sourceAnimationBindingsResolved = false;
            marker.sourceAnimationPayloadApplied = false;
            marker.sourceAggregateSha256 = AggregateSha256;
            marker.visibleAdmission = false;
            marker.blockedBy = new[]
            {
                "Plane009 is provisional converted geometry; native Mesh payload parity is not admitted",
                "native Texture2D mip payloads and Unity import parity are not admitted",
                "selected VFXBaseV2 shader variants/descriptors/draw ownership are not admitted",
                "normal runtime binding remains intentionally disabled for this diagnostic prefab",
                "only 15/53 shared clip curves target this start_02 sibling",
            };
            marker.materialExecutionBoundary =
                "diagnostic_approximation_only: M12/M13=_LiMaterialMode 9; " +
                "M14=_LiMaterialMode 11; Plane009=provisional converted geometry; " +
                "animation_bindings=15/53_partial; exact variants not admitted";
            marker.hierarchyNodes = markerNodes.ToArray();
            marker.staticMeshNodes = markerMeshes.ToArray();
            EndfieldLiZhiyanBehavioralAnimationSimulation simulation =
                root.AddComponent<EndfieldLiZhiyanBehavioralAnimationSimulation>();
            simulation.ConfigureSourceIdentity(EffectName, EffectSettingPathId, ClipPathId,
                sources.clip, EffectDuration);
            simulation.ConfigureRendererProbeBindings(probes.ToArray());
            return root;
        }

        private static void ApplyRendererFields(MeshRenderer renderer,
            Dictionary<string, object> fields)
        {
            if (fields == null) return;
            if (fields.ContainsKey("m_Enabled")) renderer.enabled = Bool(fields, "m_Enabled");
            if (fields.ContainsKey("m_CastShadows"))
                renderer.shadowCastingMode = (ShadowCastingMode)Int(fields, "m_CastShadows");
            if (fields.ContainsKey("m_ReceiveShadows"))
                renderer.receiveShadows = Bool(fields, "m_ReceiveShadows");
            if (fields.ContainsKey("m_RenderingLayerMask"))
                renderer.renderingLayerMask = unchecked((uint)Long(fields, "m_RenderingLayerMask"));
            if (fields.ContainsKey("m_RendererPriority"))
                renderer.rendererPriority = Int(fields, "m_RendererPriority");
            if (fields.ContainsKey("m_SortingLayerID"))
                renderer.sortingLayerID = Int(fields, "m_SortingLayerID");
            if (fields.ContainsKey("m_SortingOrder"))
                renderer.sortingOrder = Int(fields, "m_SortingOrder");
        }

        private static long FindTransformId(IList rows, long gameObjectId)
        {
            foreach (object item in rows)
            {
                Dictionary<string, object> row = Dict(item);
                if (Long(row, "gameObjectPathID") == gameObjectId)
                    return Long(row, "transformPathID");
            }
            throw new InvalidOperationException(
                "Li Zhiyan start_02 hierarchy row is absent for GameObject " + gameObjectId);
        }

        private static void ApplyFloats(Material material, Dictionary<string, object> values,
            MaterialReport report)
        {
            foreach (KeyValuePair<string, object> item in values)
            {
                if (!material.HasProperty(item.Key)) { report.unsupported++; continue; }
                material.SetFloat(item.Key, FloatValue(item.Value)); report.applied++;
            }
        }

        private static void ApplyColors(Material material, Dictionary<string, object> values,
            MaterialReport report)
        {
            foreach (KeyValuePair<string, object> item in values)
            {
                if (!material.HasProperty(item.Key)) { report.unsupported++; continue; }
                material.SetColor(item.Key, ColorValue(item.Value)); report.applied++;
            }
        }

        private static void ApplyTextures(Material material, Dictionary<string, object> values,
            Dictionary<long, Texture2D> textures, MaterialReport report)
        {
            foreach (KeyValuePair<string, object> item in values)
            {
                if (!material.HasProperty(item.Key)) { report.unsupported++; continue; }
                Dictionary<string, object> env = Dict(item.Value);
                Dictionary<string, object> ptr = env.ContainsKey("m_Texture") && env["m_Texture"] != null
                    ? Dict(env["m_Texture"]) : null;
                Texture2D texture = null;
                if (ptr != null && ptr.ContainsKey("m_PathID"))
                    textures.TryGetValue(Long(ptr, "m_PathID"), out texture);
                material.SetTexture(item.Key, texture);
                if (env.ContainsKey("m_Scale")) material.SetTextureScale(item.Key, Vector2Value(env["m_Scale"]));
                if (env.ContainsKey("m_Offset")) material.SetTextureOffset(item.Key, Vector2Value(env["m_Offset"]));
                report.applied++;
            }
        }

        private static long[] LongArray(Dictionary<string, object> source, string key)
        {
            return List(source, key).Cast<object>().Select(ToLong).ToArray();
        }

        private static string[] StringArray(Dictionary<string, object> source, string key,
            string valueKey)
        {
            return List(source, key).Cast<object>().Select(value => Str(Dict(value), valueKey)).ToArray();
        }

        private static void ValidateHash(string path, string expected, string label)
        {
            Require(File.Exists(path), "Missing " + label + ": " + path);
            using (SHA256 sha = SHA256.Create())
            using (FileStream stream = File.OpenRead(path))
            {
                string actual = BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", "");
                Require(actual.Equals(expected, StringComparison.OrdinalIgnoreCase),
                    label + " hash mismatch; expected " + expected + ", got " + actual);
            }
        }

        private static void EnsureFolder(string folder)
        {
            string[] parts = folder.Split('/');
            string current = parts[0];
            for (int i = 1; i < parts.Length; i++)
            {
                string next = current + "/" + parts[i];
                if (!AssetDatabase.IsValidFolder(next)) AssetDatabase.CreateFolder(current, parts[i]);
                current = next;
            }
        }

        private static string ProjectRootAbsolute => Directory.GetParent(Application.dataPath).FullName;
        internal static string ProjectAbsolute(string path) => Path.GetFullPath(Path.Combine(
            ProjectRootAbsolute, path.Replace('/', Path.DirectorySeparatorChar)));
        private static string RepositoryAbsolute(string path) => Path.GetFullPath(Path.Combine(
            Directory.GetParent(ProjectRootAbsolute).FullName,
            path.Replace('/', Path.DirectorySeparatorChar)));
        private static string Safe(string value)
        {
            foreach (char invalid in Path.GetInvalidFileNameChars()) value = value.Replace(invalid, '_');
            return value.Replace(' ', '_');
        }
        private static Dictionary<string, object> Dict(object value)
        { var result = value as Dictionary<string, object>; Require(result != null, "Expected JSON object"); return result; }
        private static Dictionary<string, object> DictOrEmpty(Dictionary<string, object> source, string key)
        { return source.ContainsKey(key) && source[key] != null ? Dict(source[key]) : new Dictionary<string, object>(); }
        private static IList List(Dictionary<string, object> source, string key)
        { Require(source.ContainsKey(key) && source[key] != null, "Expected JSON array: " + key); return (IList)source[key]; }
        private static IList ListValue(Dictionary<string, object> source, string key)
        { return source.ContainsKey(key) && source[key] != null ? source[key] as IList : null; }
        private static string Str(Dictionary<string, object> source, string key)
        { Require(source.ContainsKey(key), "Missing JSON string: " + key); return Convert.ToString(source[key], CultureInfo.InvariantCulture); }
        private static long Long(Dictionary<string, object> source, string key)
        { Require(source.ContainsKey(key), "Missing JSON integer: " + key); return ToLong(source[key]); }
        private static long ToLong(object value)
        { if (value is long) return (long)value; if (value is int) return (int)value; if (value is double) return checked((long)(double)value); return long.Parse(Convert.ToString(value, CultureInfo.InvariantCulture), NumberStyles.Integer, CultureInfo.InvariantCulture); }
        private static int Int(Dictionary<string, object> source, string key) { return checked((int)Long(source, key)); }
        private static float Float(Dictionary<string, object> source, string key) { return FloatValue(source[key]); }
        private static float FloatValue(object value) { return Convert.ToSingle(value, CultureInfo.InvariantCulture); }
        private static bool Bool(Dictionary<string, object> source, string key) { return Math.Abs(FloatValue(source[key])) > 0.5f; }
        private static long PPtrId(object value)
        { Dictionary<string, object> p = Dict(value); return p.ContainsKey("m_PathID") ? Long(p, "m_PathID") : (p.ContainsKey("pathID") ? Long(p, "pathID") : 0L); }
        private static Vector3 Vector3Value(object value) { Dictionary<string, object> p = Dict(value); return new Vector3(Component(p, "X", "x"), Component(p, "Y", "y"), Component(p, "Z", "z")); }
        private static Quaternion QuaternionValue(object value) { Dictionary<string, object> p = Dict(value); return new Quaternion(Component(p, "X", "x"), Component(p, "Y", "y"), Component(p, "Z", "z"), Component(p, "W", "w")); }
        private static Vector2 Vector2Value(object value) { Dictionary<string, object> p = Dict(value); return new Vector2(Component(p, "x", "X"), Component(p, "y", "Y")); }
        private static Color ColorValue(object value) { Dictionary<string, object> p = Dict(value); return new Color(Component(p, "r", "R"), Component(p, "g", "G"), Component(p, "b", "B"), Component(p, "a", "A")); }
        private static float Component(Dictionary<string, object> source, string preferred, string alternate)
        { return source.ContainsKey(preferred) ? FloatValue(source[preferred]) : FloatValue(source[alternate]); }
        private static void Require(bool condition, string message) { if (!condition) throw new InvalidOperationException(message); }
    }
}
