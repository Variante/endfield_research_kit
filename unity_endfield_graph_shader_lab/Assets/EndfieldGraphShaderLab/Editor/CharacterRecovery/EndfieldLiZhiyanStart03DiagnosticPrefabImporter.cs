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
    /// Imports the serialized start_03 static-mesh sibling into an isolated
    /// diagnostic prefab. Converted OBJ geometry is source-exact for the two
    /// recorded Mesh PathIDs, but native payload/Unity parity and shader
    /// variant admission remain deliberately closed.
    /// </summary>
    public static class EndfieldLiZhiyanStart03DiagnosticPrefabImporter
    {
        public const string ContractPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/" +
            "lizhiyan_overview_start_02_03_effects.json";
        public const string GeneratedRoot =
            "Assets/EndfieldGraphShaderLab/Generated/Diagnostics/LiZhiyanStart03";
        public const string GeneratedPrefabPath = GeneratedRoot + "/Prefabs/" +
            "P_fxui_lizhiyan_overview_start_03_DIAGNOSTIC.prefab";
        private const string SourceRoot = GeneratedRoot + "/Source";
        private const string MaterialRoot = GeneratedRoot + "/Materials";
        private const string ShaderName = "Endfield/Recovered/LiZhiyanStart01Diagnostic";
        private const string EffectName = "P_fxui_lizhiyan_overview_start_03";
        private const string Schema = "endfield.lizhiyan-overview-static-sibling-effects.v1";
        private const string Aggregate = "AB587FDA1E0AEC1761A10F334959541FA0217347E595D18415850791AE33545B";
        private const long RootGameObject = -4762735294709058244L;
        private const long RootTransform = -1899328819351145156L;
        private const long EffectSetting = 8184202388571141436L;
        private const long AnimatorPath = -9082212685869435588L;
        private const long HelperPath = -2813493105014622916L;
        private const long ClipPath = 7360398354216100382L;
        private const float Duration = 7f;
        private const float ClipRate = 30f;
        private const float ClipStop = 6.366667f;
        private const string ClipAssetPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/" +
            "A_fxui__lizhiyan_overview_start_01.anim";
        private const string ClipHash = "C1D7846FB29A9AF720B2760BA2EEA97B870CAC8DF101DADE797A2301778FF920";

        private sealed class Sources
        {
            public readonly Dictionary<long, Mesh> meshes = new Dictionary<long, Mesh>();
            public readonly Dictionary<long, Texture2D> textures = new Dictionary<long, Texture2D>();
            public AnimationClip clip;
        }

        private sealed class MaterialReport { public int applied; public int unsupported; }

        [MenuItem("Endfield/Character Recovery Lab/Build Li Zhiyan start_03 Diagnostic Prefab")]
        public static void BuildAndValidate()
        {
            Dictionary<string, object> root = ReadContract();
            Dictionary<string, object> effect = FindEffect(root);
            ValidateContract(root, effect);
            Sources sources = ImportSources(root, effect);
            Shader shader = Shader.Find(ShaderName);
            Require(shader != null, "Missing diagnostic shader: " + ShaderName);
            var materials = new Dictionary<long, Material>();
            int applied = 0, unsupported = 0;
            foreach (object value in List(effect, "materials"))
            {
                MaterialReport report;
                Material material = BuildMaterial(Dict(value), shader, sources.textures, out report);
                materials[Long(Dict(value), "pathID")] = material;
                applied += report.applied;
                unsupported += report.unsupported;
            }
            GameObject instance = null;
            try
            {
                instance = BuildHierarchy(effect, sources, materials);
                EndfieldLiZhiyanBehavioralAnimationSimulation simulation =
                    instance.GetComponent<EndfieldLiZhiyanBehavioralAnimationSimulation>();
                string reason = string.Empty;
                Require(simulation != null && simulation.TryConstructSimulation(out reason),
                    "Behavioral simulator failed: " + reason);
                EnsureFolder(GeneratedRoot + "/Prefabs");
                PrefabUtility.SaveAsPrefabAsset(instance, GeneratedPrefabPath);
            }
            finally
            {
                if (instance != null) UnityEngine.Object.DestroyImmediate(instance);
            }
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            EndfieldLiZhiyanStart03DiagnosticPrefabValidator.ValidateGenerated(
                GeneratedPrefabPath, unsupported, applied);
            Debug.Log("[Endfield Li Zhiyan] start_03 diagnostic prefab built and validated: " +
                GeneratedPrefabPath + "; visibleAdmission=false; shader-supported properties applied=" +
                applied + "; unsupported serialized properties=" + unsupported + ".");
        }

        public static void ValidateExisting()
        {
            EndfieldLiZhiyanStart03DiagnosticPrefabValidator.ValidateGenerated(
                GeneratedPrefabPath, -1, -1);
        }

        internal static Dictionary<string, object> ReadContract()
        {
            string path = ProjectAbsolute(ContractPath);
            Require(File.Exists(path), "Missing sibling effect contract: " + path);
            return Dict(ManifestMiniJson.Deserialize(File.ReadAllText(path, Encoding.UTF8)));
        }

        private static Dictionary<string, object> FindEffect(Dictionary<string, object> root)
        {
            foreach (object value in List(root, "effects"))
            {
                Dictionary<string, object> effect = Dict(value);
                if (Str(effect, "effectName") == EffectName) return effect;
            }
            throw new InvalidOperationException("start_03 effect is absent from sibling contract");
        }

        private static void ValidateContract(Dictionary<string, object> root, Dictionary<string, object> effect)
        {
            Require(Str(root, "schema") == Schema && Str(root, "status") ==
                "start02_start03_serialized_sources_closed_visible_fail_closed", "Sibling contract identity drifted");
            Require(Str(Dict(root["summary"]), "sourceAggregateSha256").Equals(Aggregate, StringComparison.OrdinalIgnoreCase), "Sibling aggregate hash drifted");
            Require(Str(effect, "effectName") == EffectName && Long(Dict(effect["effectSetting"]), "pathID") == EffectSetting, "start_03 identity drifted");
            Dictionary<string, object> timing = Dict(Dict(effect["effectSetting"])["timing"]);
            Require(Math.Abs(Float(timing, "duration") - Duration) < .0001f && Bool(timing, "isLoop") == false, "start_03 timing drifted");
            Dictionary<string, object> shared = Dict(root["sharedAnimation"]);
            Require(Long(shared, "pathID") == ClipPath, "Shared animation PathID drifted");
            Require(PPtrId(Dict(Dict(effect["animation"])["helper"])["startAnimationClip"]) == ClipPath, "start_03 helper clip drifted");
            ValidateHash(ProjectAbsolute(ClipAssetPath), ClipHash, "shared animation clip");
            Require(List(effect, "hierarchyNodes").Count == 4 && List(effect, "staticMeshNodes").Count == 3 && List(effect, "materials").Count == 3, "start_03 census drifted");
        }

        private static Sources ImportSources(Dictionary<string, object> root, Dictionary<string, object> effect)
        {
            EnsureFolder(SourceRoot);
            var sources = new Sources();
            foreach (object dependencyValue in List(root, "textureDependencies"))
            {
                Dictionary<string, object> dependency = Dict(dependencyValue);
                Dictionary<string, object> png = Dict(dependency["convertedPng"]);
                string source = Str(png, "path");
                string asset = SourceRoot + "/" + Path.GetFileName(source);
                CopyAndImport(source, asset);
                Texture2D texture = AssetDatabase.LoadAssetAtPath<Texture2D>(asset);
                Require(texture != null, "Texture import failed: " + asset);
                ValidateHash(RepositoryAbsolute(source), Str(png, "sha256"), "texture " + Long(dependency, "pathID"));
                sources.textures[Long(dependency, "pathID")] = texture;
            }
            foreach (object dependencyValue in List(effect, "meshDependencies"))
            {
                Dictionary<string, object> dependency = Dict(dependencyValue);
                Dictionary<string, object> obj = Dict(dependency["convertedObj"]);
                string source = Str(obj, "path");
                string asset = SourceRoot + "/" + Path.GetFileName(source);
                CopyAndImport(source, asset);
                Mesh mesh = AssetDatabase.LoadAllAssetsAtPath(asset).OfType<Mesh>().FirstOrDefault();
                Require(mesh != null, "Mesh import failed: " + asset);
                ValidateHash(RepositoryAbsolute(source), Str(obj, "sha256"), "mesh " + Long(dependency, "pathID"));
                sources.meshes[Long(dependency, "pathID")] = mesh;
            }
            AssetDatabase.ImportAsset(ClipAssetPath, ImportAssetOptions.ForceUpdate);
            sources.clip = AssetDatabase.LoadAssetAtPath<AnimationClip>(ClipAssetPath);
            Require(sources.clip != null, "Shared animation clip did not import");
            return sources;
        }

        private static Material BuildMaterial(Dictionary<string, object> source, Shader shader, Dictionary<long, Texture2D> textures, out MaterialReport report)
        {
            report = new MaterialReport();
            long id = Long(source, "pathID");
            string path = MaterialRoot + "/" + Safe(Str(source, "name")) + "_p" + unchecked((ulong)id).ToString("X16", CultureInfo.InvariantCulture) + ".mat";
            EnsureFolder(MaterialRoot);
            Material material = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (material == null) { material = new Material(shader); AssetDatabase.CreateAsset(material, path); }
            material.shader = shader; material.name = Str(source, "name"); material.renderQueue = Int(source, "customRenderQueue");
            Dictionary<string, object> payload = Dict(source["payload"]);
            Dictionary<string, object> saved = Dict(payload["m_SavedProperties"]);
            ApplyFloats(material, DictOrEmpty(saved, "m_Floats"), report);
            ApplyFloats(material, DictOrEmpty(saved, "m_Ints"), report);
            ApplyColors(material, DictOrEmpty(saved, "m_Colors"), report);
            ApplyTextures(material, DictOrEmpty(saved, "m_TexEnvs"), textures, report);
            IList keywords = payload.ContainsKey("m_ValidKeywords") ? payload["m_ValidKeywords"] as IList : null;
            material.shaderKeywords = keywords == null ? Array.Empty<string>() : keywords.Cast<object>().Select(v => Convert.ToString(v, CultureInfo.InvariantCulture)).ToArray();
            Require(material.HasProperty("_LiMaterialMode"), "Li diagnostic shader lost _LiMaterialMode");
            material.SetFloat("_LiMaterialMode", 9f);
            EditorUtility.SetDirty(material);
            return material;
        }

        private static GameObject BuildHierarchy(Dictionary<string, object> effect, Sources sources, Dictionary<long, Material> materials)
        {
            IList rows = List(effect, "hierarchyNodes");
            var objects = new Dictionary<long, GameObject>(); var transforms = new Dictionary<long, long>();
            foreach (object value in rows)
            {
                Dictionary<string, object> row = Dict(value); Dictionary<string, object> go = Dict(row["gameObject"]);
                long gid = Long(row, "gameObjectPathID"), tid = Long(row, "transformPathID");
                objects[gid] = new GameObject(Str(go, "m_Name")); transforms[tid] = gid;
            }
            foreach (object value in rows)
            {
                Dictionary<string, object> row = Dict(value); Dictionary<string, object> tr = Dict(row["transform"]);
                long gid = Long(row, "gameObjectPathID"); long parent = PPtrId(tr["m_Father"]);
                if (parent != 0) { Require(transforms.ContainsKey(parent), "start_03 hierarchy parent missing"); objects[gid].transform.SetParent(objects[transforms[parent]].transform, false); }
                objects[gid].transform.localPosition = Vector3Value(tr["m_LocalPosition"]); objects[gid].transform.localRotation = QuaternionValue(tr["m_LocalRotation"]); objects[gid].transform.localScale = Vector3Value(tr["m_LocalScale"]);
            }
            GameObject root = objects[RootGameObject]; Require(root != null && root.transform.parent == null && root.name == EffectName, "start_03 root drifted");
            root.AddComponent<Animator>();
            var markerHierarchy = new List<EndfieldRecoveredStaticMeshHierarchyNodeSource>();
            foreach (object value in rows) { Dictionary<string, object> row = Dict(value); long gid = Long(row, "gameObjectPathID"); markerHierarchy.Add(new EndfieldRecoveredStaticMeshHierarchyNodeSource { hierarchy = Str(row, "hierarchy"), gameObjectPathId = gid, transformPathId = Long(row, "transformPathID"), generatedTransform = objects[gid].transform }); }
            var markerMeshes = new List<EndfieldRecoveredStaticMeshNodeSource>(); var probes = new List<EndfieldLiZhiyanBehavioralAnimationSimulation.RendererProbeBinding>();
            foreach (object value in List(effect, "staticMeshNodes"))
            {
                Dictionary<string, object> row = Dict(value); long gid = Long(row, "gameObjectPathID"); GameObject host = objects[gid]; MeshFilter filter = host.AddComponent<MeshFilter>(); MeshRenderer renderer = host.AddComponent<MeshRenderer>(); long meshId = PPtrId(row["mesh"]); Require(sources.meshes.ContainsKey(meshId), "start_03 mesh dependency missing"); filter.sharedMesh = sources.meshes[meshId];
                var assigned = new List<Material>(); var materialIds = new List<long>(); foreach (object materialValue in List(row, "materials")) { long mid = PPtrId(materialValue); Require(materials.ContainsKey(mid), "start_03 material dependency missing"); materialIds.Add(mid); assigned.Add(materials[mid]); }
                renderer.sharedMaterials = assigned.ToArray(); ApplyRendererFields(renderer, Dict(row["meshRenderer"]));
                markerMeshes.Add(new EndfieldRecoveredStaticMeshNodeSource { hierarchy = Str(row, "hierarchy"), gameObjectPathId = gid, transformPathId = FindTransform(rows, gid), meshFilterPathId = Long(row, "meshFilterPathID"), meshRendererPathId = Long(row, "meshRendererPathID"), meshPathId = meshId, materialPathIds = materialIds.ToArray(), shaderPathIds = materialIds.Select(_ => -1430105248647086886L).ToArray(), generatedMeshFilter = filter, generatedMeshRenderer = renderer, sourceRendererEnabled = renderer.enabled, nativeMeshPayloadApplied = false, nativeRendererPayloadApplied = false, nativeTexturePayloadsApplied = false, exactShaderVariantsApplied = false, rendererFailClosedForUnrecoveredShader = true });
                probes.Add(new EndfieldLiZhiyanBehavioralAnimationSimulation.RendererProbeBinding(Long(row, "meshRendererPathID"), Str(row, "hierarchy"), renderer));
            }
            EndfieldRecoveredStaticMeshEffectSource marker = root.AddComponent<EndfieldRecoveredStaticMeshEffectSource>();
            marker.contractSchema = Schema; marker.effectRoot = EffectName; marker.sourceHierarchy = EffectName; marker.sourceGameObjectPathId = RootGameObject; marker.sourceTransformPathId = RootTransform; marker.sourceEffectSettingPathId = EffectSetting; marker.sourcePayloadApplied = false; marker.sourceEffectSettingPayloadApplied = false; marker.sourceEffectLoops = false; marker.sourceEffectDuration = Duration; marker.sourceEffectDelay = 0f; marker.sourceEffectRandomDelay = 0f; marker.sourceAnimatorPathId = AnimatorPath; marker.sourceAnimationHelperPathId = HelperPath; marker.sourceStartAnimationClipPathId = ClipPath; marker.sourceStartAnimationClip = sources.clip; marker.sourceStartAnimationClipName = "A_fxui__lizhiyan_overview_start_01"; marker.sourceStartAnimationSampleRate = ClipRate; marker.sourceStartAnimationStopTime = ClipStop; marker.sourceAnimationBindingsResolved = false; marker.sourceAnimationPayloadApplied = false; marker.sourceAggregateSha256 = Aggregate; marker.visibleAdmission = false;
            marker.blockedBy = new[] { "native Mesh payload and Unity import parity are not pinned", "native Texture2D mip payloads and Unity import parity are not pinned", "converted OBJ geometry is source-exact for serialized Mesh PathIDs, but native Mesh payload parity is not admitted", "VFXBaseV2 material variants lack exact selected DXBC/descriptor/draw admission", "shared start_01 clip is attached for diagnostics only; runtime binding remains closed" };
            marker.materialExecutionBoundary = "diagnostic_approximation_only: M15/M16/M17 use serialized Mask-Blend-Dissolve route on reused start_01 shader; converted OBJ geometry exact-source boundary; native payload, exact variants, animation payload, and visibleAdmission=false";
            marker.hierarchyNodes = markerHierarchy.ToArray(); marker.staticMeshNodes = markerMeshes.ToArray();
            EndfieldLiZhiyanBehavioralAnimationSimulation simulation = root.AddComponent<EndfieldLiZhiyanBehavioralAnimationSimulation>(); simulation.ConfigureSourceIdentity(EffectName, EffectSetting, ClipPath, sources.clip, Duration); simulation.ConfigureRendererProbeBindings(probes.ToArray()); return root;
        }

        private static void ApplyRendererFields(MeshRenderer renderer, Dictionary<string, object> source) { if (source.ContainsKey("m_Enabled")) renderer.enabled = Bool(source, "m_Enabled"); if (source.ContainsKey("m_CastShadows")) renderer.shadowCastingMode = (ShadowCastingMode)Int(source, "m_CastShadows"); if (source.ContainsKey("m_ReceiveShadows")) renderer.receiveShadows = Bool(source, "m_ReceiveShadows"); if (source.ContainsKey("m_RenderingLayerMask")) renderer.renderingLayerMask = unchecked((uint)Long(source, "m_RenderingLayerMask")); if (source.ContainsKey("m_RendererPriority")) renderer.rendererPriority = Int(source, "m_RendererPriority"); if (source.ContainsKey("m_SortingLayerID")) renderer.sortingLayerID = Int(source, "m_SortingLayerID"); if (source.ContainsKey("m_SortingOrder")) renderer.sortingOrder = Int(source, "m_SortingOrder"); }
        private static void ApplyFloats(Material m, Dictionary<string, object> values, MaterialReport r) { foreach (var item in values) { if (!m.HasProperty(item.Key)) { r.unsupported++; continue; } m.SetFloat(item.Key, FloatValue(item.Value)); r.applied++; } }
        private static void ApplyColors(Material m, Dictionary<string, object> values, MaterialReport r) { foreach (var item in values) { if (!m.HasProperty(item.Key)) { r.unsupported++; continue; } m.SetColor(item.Key, ColorValue(item.Value)); r.applied++; } }
        private static void ApplyTextures(Material m, Dictionary<string, object> values, Dictionary<long, Texture2D> textures, MaterialReport r) { foreach (var item in values) { if (!m.HasProperty(item.Key)) { r.unsupported++; continue; } Dictionary<string, object> env = Dict(item.Value); Texture2D texture = null; if (env.ContainsKey("m_Texture") && env["m_Texture"] != null) { Dictionary<string, object> ptr = Dict(env["m_Texture"]); if (ptr.ContainsKey("m_PathID")) textures.TryGetValue(Long(ptr, "m_PathID"), out texture); } m.SetTexture(item.Key, texture); if (env.ContainsKey("m_Scale")) m.SetTextureScale(item.Key, Vector2Value(env["m_Scale"])); if (env.ContainsKey("m_Offset")) m.SetTextureOffset(item.Key, Vector2Value(env["m_Offset"])); r.applied++; } }
        private static long FindTransform(IList rows, long gid) { foreach (object value in rows) { Dictionary<string, object> row = Dict(value); if (Long(row, "gameObjectPathID") == gid) return Long(row, "transformPathID"); } throw new InvalidOperationException("start_03 transform missing"); }
        private static void CopyAndImport(string source, string asset) { EnsureFolder(Path.GetDirectoryName(asset).Replace('\\', '/')); File.Copy(RepositoryAbsolute(source), ProjectAbsolute(asset), true); AssetDatabase.ImportAsset(asset, ImportAssetOptions.ForceUpdate); }
        private static void ValidateHash(string path, string expected, string label) { Require(File.Exists(path), "Missing " + label + ": " + path); using (SHA256 sha = SHA256.Create()) using (FileStream stream = File.OpenRead(path)) { string actual = BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", "").ToUpperInvariant(); Require(actual == expected.ToUpperInvariant(), label + " hash mismatch"); } }
        private static void EnsureFolder(string folder) { string[] parts = folder.Split('/'); string current = parts[0]; for (int i = 1; i < parts.Length; i++) { string next = current + "/" + parts[i]; if (!AssetDatabase.IsValidFolder(next)) AssetDatabase.CreateFolder(current, parts[i]); current = next; } }
        private static string ProjectRootAbsolute { get { return Directory.GetParent(Application.dataPath).FullName; } }
        private static string ProjectAbsolute(string path) { return Path.GetFullPath(Path.Combine(ProjectRootAbsolute, path.Replace('/', Path.DirectorySeparatorChar))); }
        private static string RepositoryAbsolute(string path) { string root = Directory.GetParent(ProjectRootAbsolute).FullName; return Path.GetFullPath(Path.Combine(root, path.Replace('/', Path.DirectorySeparatorChar))); }
        private static string Safe(string value) { foreach (char c in Path.GetInvalidFileNameChars()) value = value.Replace(c, '_'); return value.Replace(' ', '_'); }
        private static Dictionary<string, object> Dict(object value) { var d = value as Dictionary<string, object>; Require(d != null, "Expected JSON object"); return d; }
        private static Dictionary<string, object> DictOrEmpty(Dictionary<string, object> d, string key) { return d.ContainsKey(key) && d[key] != null ? Dict(d[key]) : new Dictionary<string, object>(); }
        private static IList List(Dictionary<string, object> d, string key) { Require(d.ContainsKey(key) && d[key] != null, "Expected JSON array: " + key); return (IList)d[key]; }
        private static string Str(Dictionary<string, object> d, string key) { Require(d.ContainsKey(key), "Missing JSON value: " + key); return Convert.ToString(d[key], CultureInfo.InvariantCulture); }
        private static long Long(Dictionary<string, object> d, string key) { Require(d.ContainsKey(key), "Missing JSON integer: " + key); return ToLong(d[key]); }
        private static long ToLong(object value) { if (value is long) return (long)value; if (value is int) return (int)value; if (value is double) return checked((long)(double)value); return long.Parse(Convert.ToString(value, CultureInfo.InvariantCulture), NumberStyles.Integer, CultureInfo.InvariantCulture); }
        private static int Int(Dictionary<string, object> d, string key) { return checked((int)Long(d, key)); }
        private static float Float(Dictionary<string, object> d, string key) { return FloatValue(d[key]); }
        private static float FloatValue(object value) { return Convert.ToSingle(value, CultureInfo.InvariantCulture); }
        private static bool Bool(Dictionary<string, object> d, string key) { object value = d[key]; return value is bool ? (bool)value : Math.Abs(FloatValue(value)) > .5f; }
        private static long PPtrId(object value) { Dictionary<string, object> d = Dict(value); if (d.ContainsKey("m_PathID")) return Long(d, "m_PathID"); return d.ContainsKey("pathID") ? Long(d, "pathID") : 0L; }
        private static float Component(Dictionary<string, object> d, string a, string b) { return FloatValue(d.ContainsKey(a) ? d[a] : d[b]); }
        private static Vector3 Vector3Value(object value) { Dictionary<string, object> d = Dict(value); return new Vector3(Component(d, "X", "x"), Component(d, "Y", "y"), Component(d, "Z", "z")); }
        private static Quaternion QuaternionValue(object value) { Dictionary<string, object> d = Dict(value); return new Quaternion(Component(d, "X", "x"), Component(d, "Y", "y"), Component(d, "Z", "z"), Component(d, "W", "w")); }
        private static Vector2 Vector2Value(object value) { Dictionary<string, object> d = Dict(value); return new Vector2(Component(d, "x", "X"), Component(d, "y", "Y")); }
        private static Color ColorValue(object value) { Dictionary<string, object> d = Dict(value); return new Color(Component(d, "r", "R"), Component(d, "g", "G"), Component(d, "b", "B"), Component(d, "a", "A")); }
        private static void Require(bool condition, string message) { if (!condition) throw new InvalidOperationException(message); }
    }
}
