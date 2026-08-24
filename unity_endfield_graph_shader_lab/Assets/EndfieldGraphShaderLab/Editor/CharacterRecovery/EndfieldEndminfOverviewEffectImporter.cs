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
using L = EndfieldGraphShaderLabEditor.EndfieldLastRiteOverviewHeadEffectImporter;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>Imports the exact Endminf Overview hierarchies and native particle payloads.
    /// Renderers remain disabled until their individual shader/material closure is admitted.</summary>
    public static class EndfieldEndminfOverviewEffectImporter
    {
        private const string StageRelative =
            "unity_endfield_graph_shader_lab/scratch/character_recovery/endminf_external_fx_rig/exact_four_root_stage";
        private const string GeneratedRoot =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Effects/Overview";
        private const string MaterialRoot = GeneratedRoot + "/Materials";
        private const string TextureRoot = GeneratedRoot + "/Textures";
        private const string MeshRoot = GeneratedRoot + "/Meshes";
        private const long RefractShaderPathId = 7766268189260370413L;
        private const long BaseV2ShaderPathId = -1430105248647086886L;
        private const long LitEffectShaderPathId = 6428594484694422749L;
        public const string LitEffectCompatibilityEnvironment = "ENDFIELD_ENDMINF_LITEFFECT_VISUAL_COMPAT";
        private static readonly long[] LitEffectCompatibilityMaterials = {
            0x5A6341E8A834E421L,
            unchecked((long)0xAFCE491DD7BC5724UL),
            // P_fxui_endminm003_overview_02/all/suikuai (2).
            unchecked((long)0xA531A88850690EB8UL),
        };
        // M28 uses the selected VFXRefract MRT ABI. Native
        // DistortionPassConstructor evidence confirms retail clones/copies
        // scene color, binds color+SceneMV+depth, then draws the distortion
        // renderer lists. The recovered compositor now supplies that topology;
        // Endminf admission remains explicit until its direct-frame gate passes.
        private const long EndminfRefract28Material = unchecked((long)0xBF7FEE87831B48FBUL);
        private const string VisualCompatibilityEnvironment =
            "ENDFIELD_ENDMINF_VISUAL_COMPATIBILITY";
        private static readonly long[] AdmittedRefractMaterials =
            IsVisualCompatibilityRequested()
                ? new[] {
                    EndminfRefract28Material,
                    // P_fxui_endminm003_overview_02/all/suikuai (1).
                    // This source renderer is authored enabled and uses the
                    // same recovered Refract shader ABI as M28.
                    0x19E6A2A7AE736DA5L,
                }
                : Array.Empty<long>();
        // Exact source identities selected by the focused Endminf BaseV2
        // variant audit. Each row is revalidated against name, shader PathID,
        // queue and ordered local keywords before any renderer is enabled.
        private static readonly Dictionary<long, string[]> AdmittedBaseV2Materials =
            new Dictionary<long, string[]> {
                { 0x13C3BA85865CFBD0L, new[] { "_SAMPLE_TEX0" } },
                { 0x57A25F1386F7012FL, new[] { "_SAMPLE_TEX0", "_SAMPLE_TEX1", "_SAMPLE_TEX2", "_SAMPLE_TEX3", "_USE_POLARUV", "_USE_SCREENUV" } },
                { 0x418FE5EF54286417L, new[] { "_SAMPLE_TEX0", "_USE_POLARUV", "_USE_SCREENUV" } },
                { 0x392693FCB1EC4C68L, Array.Empty<string>() },
                { unchecked((long)0xF43088E31E25D24AUL), new[] { "_SAMPLE_TEX0" } },
                { unchecked((long)0xEC97B180E0A82AB7UL), new[] { "_USE_SOFTBLEND" } },
                { 0x602883BD6BB1831BL, new[] { "_USE_SOFTBLEND" } },
                { unchecked((long)0xBF692EC36800069DUL), new[] { "_USE_SOFTBLEND" } },
                { 0x26EC2259AEC716E7L, new[] { "_USE_SOFTBLEND" } },
                { unchecked((long)0xF6DCA5E6B2122169UL), new[] { "_USE_SOFTBLEND" } },
                { unchecked((long)0xF1C3F38D51FA67EFUL), new[] { "_SAMPLE_TEX0" } },
                { 0x7010821E75C0A247L, new[] { "_SAMPLE_TEX0", "_SAMPLE_TEX1", "_SAMPLE_TEX2", "_SAMPLE_TEX3" } },
                { unchecked((long)0xEE9E2589EB9513AEUL), new[] { "_SAMPLE_TEX0", "_SAMPLE_TEX1", "_USE_SOFTBLEND" } },
                { unchecked((long)0x8EE22B791F9A2753UL), new[] { "_USE_FRESNEL" } },
                { 0x364397B467C89F2EL, new[] { "_USE_SOFTBLEND" } },
                { 0x3409DAC8F2A1253DL, Array.Empty<string>() },
                { 0x014C92101D852EC4L, new[] { "_USE_SOFTBLEND" } },
                { 0x632B1622242536ECL, new[] { "_USE_SOFTBLEND" } },
                { 0x655CC24C5B0D67F2L, new[] { "_USE_SOFTBLEND" } },
                { unchecked((long)0xB17322AF98845218UL), new[] { "_USE_SOFTBLEND" } },
                { unchecked((long)0xE744767C80FE8433UL), new[] { "_SAMPLE_TEX0", "_SAMPLE_TEX1" } },
                { 0x5D8517046749BD84L, new[] { "_SAMPLE_TEX0", "_SAMPLE_TEX1" } },
                { unchecked((long)0x9914E0CD5285A586UL), Array.Empty<string>() },
                { unchecked((long)0xA55BF26D14F133FEUL), new[] { "_SAMPLE_TEX0", "_SAMPLE_TEX1", "_USE_POLARUV", "_USE_SCREENUV" } },
                { 0x2FE0832EAEFAA074L, new[] { "_USE_SOFTBLEND" } },
                { 0x5F6E5795FD9FD4B6L, new[] { "_SAMPLE_TEX0" } },
                { 0x3AF64D68AFB748E7L, new[] { "_USE_SOFTBLEND" } },
                { 0x7BCC4552203800A8L, new[] { "_SAMPLE_TEX0", "_SAMPLE_TEX1" } },
                { 0x65C0CDA093B23305L, new[] { "_USE_SOFTBLEND" } },
                { 0x75A3068776F01BCFL, new[] { "_SAMPLE_TEX0", "_USE_POLARUV", "_USE_SCREENUV" } },
                { 0x75854801AE9519E8L, new[] { "_SAMPLE_TEX0", "_SAMPLE_TEX1", "_SAMPLE_TEX2", "_USE_VERTOFFSET" } },
                { unchecked((long)0xAE712D0FF5A7A00AUL), new[] { "_USE_SOFTBLEND" } },
                { 0x49DDD5599C166F6BL, new[] { "_SAMPLE_TEX0", "_USE_POLARUV", "_USE_SCREENUV" } },
                { 0x5FE318FDDD817ADAL, new[] { "_USE_SOFTBLEND" } },
                { 0x73D80B62F5BA886FL, new[] { "_USE_SOFTBLEND" } },
                { unchecked((long)0x9EBBC39832869160UL), Array.Empty<string>() },
            };
        private static readonly string[] Roots = {
            "P_fxui_endminm003_overview_01", "P_fxui_endminm003_overview_02",
            "P_fxui_endminm003_overview_03", "P_fxui_endminm003_overview_04" };
        private static readonly Dictionary<string, float> Durations =
            new Dictionary<string, float>(StringComparer.Ordinal) {
                { Roots[0], 9f }, { Roots[1], 10f }, { Roots[2], 9f }, { Roots[3], 9f } };

        [MenuItem("Endfield/Character Recovery Lab/Build Endminf Overview Effects")]
        public static void BuildAndValidate()
        {
            string repo = Directory.GetParent(Application.dataPath).Parent.FullName;
            string stage = Path.Combine(repo, StageRelative.Replace('/', Path.DirectorySeparatorChar));
            L.Require(File.Exists(Path.Combine(stage, "external_ui_effect_stage.json")),
                "Endminf exact effect stage is missing");
            Dictionary<long, Dictionary<string, object>> gos = LoadType(stage, "GameObject");
            Dictionary<long, Dictionary<string, object>> transforms = LoadType(stage, "Transform");
            Dictionary<long, Dictionary<string, object>> systems = LoadType(stage, "ParticleSystem");
            Dictionary<long, Dictionary<string, object>> renderers = LoadType(stage, "ParticleSystemRenderer");
            Dictionary<long, Dictionary<string, object>> behaviours = LoadType(stage, "MonoBehaviour");
            L.Require(gos.Count == 101 && transforms.Count == 101 && systems.Count == 70 &&
                renderers.Count == 70, "Endminf effect stage census drifted");
            var transformByGo = transforms.ToDictionary(pair => L.PPtrId(pair.Value["m_GameObject"]), pair => pair.Key);
            var goByTransform = transformByGo.ToDictionary(pair => pair.Value, pair => pair.Key);
            var rootByTransform = new Dictionary<long, string>();
            Func<long, string> findRoot = null;
            findRoot = id => {
                if (rootByTransform.TryGetValue(id, out string cached)) return cached;
                Dictionary<string, object> t = transforms[id]; long father = L.PPtrId(t["m_Father"]);
                string result = father == 0 ? L.Str(gos[goByTransform[id]], "m_Name") : findRoot(father);
                rootByTransform[id] = result; return result;
            };
            L.EnsureFolder(GeneratedRoot);
            L.EnsureFolder(MaterialRoot); L.EnsureFolder(TextureRoot); L.EnsureFolder(MeshRoot);
            EndfieldZhuangfyParticleEffectImporter.Context context =
                BuildAdmittedDependencies(repo);
            foreach (string rootName in Roots)
            {
                var generated = new Dictionary<long, GameObject>();
                foreach (long transformId in transforms.Keys.Where(id => findRoot(id) == rootName))
                {
                    Dictionary<string, object> go = gos[goByTransform[transformId]];
                    var obj = new GameObject(L.Str(go, "m_Name"));
                    obj.layer = L.Int(go, "m_Layer");
                    // The targeted AnimeStudio GameObject view omits m_IsActive.
                    // Runtime FromOverview instantiation activates this authored
                    // one-shot hierarchy; renderer visibility remains separately
                    // gated below by exact material/shader admission.
                    obj.SetActive(true);
                    generated[transformId] = obj;
                }
                foreach (var pair in generated)
                {
                    Dictionary<string, object> t = transforms[pair.Key]; long father = L.PPtrId(t["m_Father"]);
                    if (father != 0) pair.Value.transform.SetParent(generated[father].transform, false);
                    pair.Value.transform.localPosition = L.Vector3Value(t["m_LocalPosition"]);
                    pair.Value.transform.localRotation = L.QuaternionValue(t["m_LocalRotation"]);
                    pair.Value.transform.localScale = L.Vector3Value(t["m_LocalScale"]);
                }
                GameObject root = generated.Values.Single(value => value.transform.parent == null);
                AttachExactLodActivation(root, rootName, generated, transformByGo,
                    goByTransform, gos, behaviours);
                var markerNodes = new List<EndfieldRecoveredParticleNodeSource>();
                var markerByHost = new Dictionary<GameObject, EndfieldRecoveredParticleNodeSource>();
                foreach (var pair in systems.Where(row => generated.ContainsKey(transformByGo[L.PPtrId(row.Value["m_GameObject"])])))
                {
                    long goId = L.PPtrId(pair.Value["m_GameObject"]); long transformId = transformByGo[goId];
                    GameObject host = generated[transformId]; ParticleSystem system = host.AddComponent<ParticleSystem>();
                    var serialized = new SerializedObject(system);
                    EndfieldZhuangfyParticleEffectImporter.DisableAllKnownModules(serialized);
                    var safeParticle = new Dictionary<string, object>(pair.Value);
                    // AnimeStudio provenance is validated by the staged source
                    // contract; it is not a serialized ParticleSystem field.
                    safeParticle.Remove("$animestudio");
                    safeParticle.Remove("Name");
                    if (safeParticle.TryGetValue("ShapeModule", out object shapeValue))
                    {
                        var shape = new Dictionary<string, object>(L.Dict(shapeValue));
                        if (shape.TryGetValue("m_Texture", out object shapeTexture) &&
                            L.PPtrId(shapeTexture) == 6970530313307194154L)
                        {
                            // This optional shape-mask texture is outside the
                            // admitted material closure. Null it explicitly;
                            // importing an unrelated texture would broaden the
                            // evidence gate while every renderer is fail-closed.
                            shape["m_Texture"] = new Dictionary<string, object> {
                                { "m_FileID", 0L }, { "m_PathID", 0L }
                            };
                        }
                        safeParticle["ShapeModule"] = shape;
                    }
                    if (safeParticle.TryGetValue("ExternalForcesModule", out object externalValue))
                    {
                        var external = new Dictionary<string, object>(L.Dict(externalValue));
                        if (external.TryGetValue("influenceList", out object influenceValue) &&
                            influenceValue is IList influenceList && influenceList.Count > 0)
                        {
                            // The referenced external-force producer is not part
                            // of this exact prefab closure. Keep the particle
                            // payload executable but fail this optional module
                            // closed instead of fabricating its field object.
                            external["enabled"] = false;
                            external["influenceList"] = new List<object>();
                        }
                        safeParticle["ExternalForcesModule"] = external;
                    }
                    EndfieldZhuangfyParticleEffectImporter.ApplyTopLevelDictionary(serialized, safeParticle, context,
                        "Endminf.ParticleSystem");
                    foreach (KeyValuePair<string, object> module in safeParticle.Where(field =>
                        field.Key.EndsWith("Module", StringComparison.Ordinal) && field.Value is Dictionary<string, object>))
                    {
                        Dictionary<string, object> fields = L.Dict(module.Value);
                        if (L.Bool(fields, "enabled"))
                            EndfieldZhuangfyParticleEffectImporter.ApplyNamedDictionary(
                                serialized, module.Key, fields, context,
                                "Endminf.ParticleSystem." + module.Key);
                    }
                    serialized.ApplyModifiedPropertiesWithoutUndo();
                    var rendererRow = renderers.Single(row => L.PPtrId(row.Value["m_GameObject"]) == goId);
                    ParticleSystemRenderer renderer = system.GetComponent<ParticleSystemRenderer>();
                    Dictionary<string, object> safeRenderer = new Dictionary<string, object>(rendererRow.Value);
                    safeRenderer.Remove("$animestudio"); safeRenderer.Remove("Name");
                    safeRenderer.Remove("m_Materials");
                    long[] meshIds = rendererRow.Value
                        .Where(field => field.Key.StartsWith("m_Mesh", StringComparison.Ordinal))
                        .Select(field => L.PPtrId(field.Value))
                        .Where(id => id != 0)
                        .Distinct()
                        .ToArray();
                    foreach (string meshField in safeRenderer.Keys
                        .Where(key => key.StartsWith("m_Mesh", StringComparison.Ordinal)).ToArray())
                        safeRenderer.Remove(meshField);
                    var rendererSerialized = new SerializedObject(renderer);
                    EndfieldZhuangfyParticleEffectImporter.ApplyTopLevelDictionary(rendererSerialized,
                        safeRenderer, context, "Endminf.ParticleSystemRenderer");
                    rendererSerialized.ApplyModifiedPropertiesWithoutUndo();
                    long[] materialIds = L.PPtrIds(rendererRow.Value["m_Materials"]);
                    bool admitted = meshIds.All(context.meshes.ContainsKey) && materialIds.Length > 0 &&
                        materialIds.All(context.materials.ContainsKey);
                    if (meshIds.Length > 0 && meshIds.All(context.meshes.ContainsKey))
                    {
                        renderer.SetMeshes(meshIds.Select(id => context.meshes[id]).ToArray(), meshIds.Length);
                        // SetMeshes only fills the mesh slots; it does not
                        // switch Unity's renderer out of Billboard mode. The
                        // source m_Mesh PathIDs are direct evidence that these
                        // nodes use mesh particles (including Endminf's four
                        // authored source-stone variants).
                        renderer.renderMode = ParticleSystemRenderMode.Mesh;
                    }
                    renderer.sharedMaterials = admitted
                        ? materialIds.Select(id => context.materials[id]).ToArray()
                        : Array.Empty<Material>();
                    renderer.enabled = admitted && L.Bool(rendererRow.Value, "m_Enabled");
                    var markerNode = new EndfieldRecoveredParticleNodeSource {
                        gameObjectPathId = goId, transformPathId = transformId,
                        particleSystemPathId = pair.Key, particleRendererPathId = rendererRow.Key,
                        materialPathIds = materialIds,
                        meshPathIds = meshIds,
                        sourceRendererEnabled = renderer.enabled, nativeParticlePayloadApplied = true,
                        nativeRendererPayloadApplied = true,
                        rendererFailClosedForUnrecoveredShader = !admitted };
                    markerNodes.Add(markerNode); markerByHost[host] = markerNode;
                }
                markerNodes = root.GetComponentsInChildren<ParticleSystemRenderer>(true)
                    .Select(renderer => markerByHost[renderer.gameObject]).ToList();
                var marker = root.AddComponent<EndfieldRecoveredParticleEffectSource>();
                marker.contractSchema = EndfieldRecoveredCharEffectSpawner.EndminfOverviewContractSchema;
                marker.effectRoot = rootName; marker.sourceEffectDuration = Durations[rootName];
                marker.sourceEffectDelay = 0f; marker.sourceEffectLoops = false;
                marker.particleNodes = markerNodes.ToArray();
                PrefabUtility.SaveAsPrefabAsset(root, GeneratedRoot + "/" + rootName + ".prefab");
                UnityEngine.Object.DestroyImmediate(root);
            }
            AssetDatabase.SaveAssets(); AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            // Rebuilding the source hierarchy replaces the prefab contents, so
            // restore the separately decoded, source-closed transform clips
            // before validating or publishing the generated roots.
            EndfieldEndminfEffectAnimationImporter.BuildAndValidate();
            ValidateGenerated();
        }

        private static void AttachExactLodActivation(GameObject root, string rootName,
            Dictionary<long, GameObject> generated, Dictionary<long, long> transformByGo,
            Dictionary<long, long> goByTransform, Dictionary<long, Dictionary<string, object>> gos,
            Dictionary<long, Dictionary<string, object>> behaviours)
        {
            long rootTransform = generated.Single(pair => pair.Value == root).Key;
            long rootGo = goByTransform[rootTransform];
            Dictionary<string, object> source = behaviours.Values.SingleOrDefault(value =>
                value.ContainsKey("lodSetting") && L.PPtrId(value["m_GameObject"]) == rootGo);
            L.Require(source != null, "Missing exact EffectSetting source for " + rootName);
            IList sourceRows = L.List(source["lodSetting"]);
            IList distanceCfg = L.List(source["distanceLodCfgList"]);
            bool useDistanceLod = L.Bool(source, "isUseDistanceLod");
            bool cameraDistanceResolved = !useDistanceLod || distanceCfg.Count == 1;
            L.Require(cameraDistanceResolved,
                rootName + " requires an unresolved camera-selected distance LOD index");
            var rows = new List<EndfieldRecoveredEffectLodRow>();
            var seen = new HashSet<long>();
            foreach (object value in sourceRows)
            {
                Dictionary<string, object> row = L.Dict(value);
                long goId = L.PPtrId(row["gameobject"]);
                long transformId = 0;
                GameObject target = null;
                L.Require(goId != 0 && transformByGo.TryGetValue(goId, out transformId) &&
                    generated.TryGetValue(transformId, out target),
                    rootName + " EffectLod row target is outside the imported hierarchy: " + goId);
                L.Require(seen.Add(goId), rootName + " EffectLod duplicate GameObject row: " + goId);
                IList infos = L.List(row["_distanceLodInfos"]);
                L.Require(infos.Count == 1 || infos.Count == distanceCfg.Count,
                    rootName + " distance row cardinality does not match its exact config census");
                rows.Add(new EndfieldRecoveredEffectLodRow {
                    target = target.transform,
                    settingLodLevel = L.Int(row, "settingLodLevel"),
                    targetLayer = L.Int(row, "targetLayer"),
                    // Native _RefreshLod leaves the mask result unchanged when
                    // m_distanceLodInfo is null. A sole serialized row supplies
                    // its exact active byte; multiple rows require a recovered
                    // camera-selected index and therefore fail above.
                    // When distance LOD is disabled, native initialization uses
                    // row zero. When it is enabled here, the sole distance cfg
                    // also makes row zero camera-independent.
                    distanceActive = L.Bool(L.Dict(infos[0]), "isActive")
                });
            }
            L.Require(rows.Count == sourceRows.Count && rows.Count == generated.Count,
                rootName + " EffectLod/source hierarchy census mismatch: rows=" + rows.Count +
                " hierarchy=" + generated.Count);
            var activation = root.AddComponent<EndfieldRecoveredEffectLodActivation>();
            activation.showSettingLodLevel = 15;
            activation.showTargetLayers = 3;
            activation.useDistanceLod = useDistanceLod;
            activation.cullDisabled = L.Bool(source, "_isCullDisable");
            activation.cameraDistanceResolved = cameraDistanceResolved;
            activation.rows = rows.ToArray();
            L.Require((!activation.useDistanceLod || activation.cameraDistanceResolved) && activation.cullDisabled,
                rootName + " EffectLod camera/distance gate drifted");
            activation.ApplyBeforePlay();
        }

        private static Dictionary<long, Dictionary<string, object>> LoadType(string stage, string type)
        {
            var result = new Dictionary<long, Dictionary<string, object>>();
            foreach (string path in Directory.GetFiles(Path.Combine(stage, type), "*.json"))
            {
                string hex = Path.GetFileNameWithoutExtension(path).Split(new[] { "_p" }, StringSplitOptions.None).Last();
                long id = unchecked((long)ulong.Parse(hex, NumberStyles.HexNumber, CultureInfo.InvariantCulture));
                result[id] = L.Dict(ManifestMiniJson.Deserialize(File.ReadAllText(path, Encoding.UTF8)));
            }
            return result;
        }

        private static void ValidateGenerated()
        {
            int total = 0;
            int admitted = 0;
            foreach (string name in Roots)
            {
                GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(GeneratedRoot + "/" + name + ".prefab");
                EndfieldRecoveredParticleEffectSource marker = prefab == null ? null : prefab.GetComponent<EndfieldRecoveredParticleEffectSource>();
                L.Require(marker != null && marker.effectRoot == name && marker.particleNodes.Length > 0 &&
                    marker.particleNodes.All(row => row.nativeParticlePayloadApplied &&
                        row.nativeRendererPayloadApplied),
                    "Endminf executable fail-closed effect drifted: " + name);
                total += marker.particleNodes.Length;
                admitted += marker.particleNodes.Count(
                    row => !row.rendererFailClosedForUnrecoveredShader);
            }
            L.Require(total == 70, "Endminf generated particle census drifted");
            L.Require(admitted > 0,
                "Endminf exact BaseV2 material gate admitted no renderers");
        }

        private static EndfieldZhuangfyParticleEffectImporter.Context BuildAdmittedDependencies(string repo)
        {
            var context = new EndfieldZhuangfyParticleEffectImporter.Context();
            bool visualCompatibility = IsVisualCompatibilityRequested();
            Shader shader = Shader.Find(
                "Hidden/Endfield/Recovered/Zhuangfy/VFXRefractMRT");
            L.Require(shader != null, "Exact recovered VFXRefract shader is missing");
            if (visualCompatibility)
                Debug.Log("Endminf M_fx_endminm_gfx_28 admitted through the recovered " +
                    "Distortion MRT scene-color clone path for direct-frame validation.");
            Shader baseV2Shader = Shader.Find("Hidden/Endfield/Recovered/Zhuangfy/VFXBaseV2MRT");
            L.Require(baseV2Shader != null, "Exact recovered VFXBaseV2 shader is missing");
            bool litEffectCompatibility = string.Equals(
                Environment.GetEnvironmentVariable(LitEffectCompatibilityEnvironment), "1",
                StringComparison.Ordinal);
            Shader litEffectCompatibilityShader = Shader.Find(
                "Hidden/Endfield/Compatibility/Endminf/LitEffectM01M38");
            if (litEffectCompatibility)
                L.Require(litEffectCompatibilityShader != null,
                    "Endminf LitEffect visual-compatibility shader is missing");
            string materialSourceRoot = Path.Combine(repo,
                "export_full/recovered/AnimeStudio-cli/StreamingAssets/json_by_type/Material");
            string textureSourceRoot = Path.Combine(repo,
                "export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/Texture2D");
            string meshSourceRoot = Path.Combine(repo,
                "export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/Mesh");
            long[] admittedMeshIds = {
                // P_fxui_endminm003_overview_02/all/kuosan. This exact
                // Plane059 mesh is the expanding-ring producer paired with
                // M_fx_endminm_gfx_18; omitting it fail-closes the renderer.
                468687656999008020L,
                9180196635748412994L, 6551658390352545759L,
                2869508565256554463L, 4104586682243008479L,
                5519914799358855135L,
                // Four authored shitou (1) mesh variants.
                1706495650298738979L,
                unchecked((long)0xAAF0B443C46F3923UL),
                unchecked((long)0xA53E934EA8413923UL),
                // overview_04 exact Loft003 and Sphere001 mesh payloads.
                unchecked((long)0x890E4AE43F826188UL),
                0x203E31C3FB31152FL };
            if (litEffectCompatibility)
                admittedMeshIds = admittedMeshIds.Concat(new[] {
                    unchecked((long)0x8EC9950E5461C8D9UL) }).ToArray();
            foreach (long meshId in admittedMeshIds)
            {
                string suffix = "_p" + unchecked((ulong)meshId).ToString("X16", CultureInfo.InvariantCulture) + ".obj";
                string source = Directory.GetFiles(meshSourceRoot, "*" + suffix).Single();
                string asset = MeshRoot + "/" + Path.GetFileName(source);
                File.Copy(source, L.ProjectAbsolute(asset), true);
                AssetDatabase.ImportAsset(asset, ImportAssetOptions.ForceSynchronousImport);
                Mesh mesh = AssetDatabase.LoadAllAssetsAtPath(asset).OfType<Mesh>().Single();
                context.meshes[meshId] = mesh;
            }
            var materialRows = new Dictionary<long, Dictionary<string, object>>();
            foreach (long id in AdmittedRefractMaterials)
            {
                string suffix = "_p" + unchecked((ulong)id).ToString("X16", CultureInfo.InvariantCulture) + ".json";
                string source = Directory.GetFiles(materialSourceRoot, "*" + suffix).Single();
                Dictionary<string, object> row = L.Dict(ManifestMiniJson.Deserialize(File.ReadAllText(source, Encoding.UTF8)));
                L.Require(L.PPtrId(row["m_Shader"]) == RefractShaderPathId, "Refract material shader identity drifted");
                materialRows[id] = row;
                foreach (object item in L.Dict(L.Dict(row["m_SavedProperties"])["m_TexEnvs"]).Values)
                {
                    long textureId = L.PPtrId(L.Dict(item)["m_Texture"]); if (textureId == 0 || context.textures.ContainsKey(textureId)) continue;
                    string hex = unchecked((ulong)textureId).ToString("X16", CultureInfo.InvariantCulture);
                    string[] candidates = AssetDatabase.FindAssets("t:Texture2D", new[] {
                            "Assets/EndfieldGraphShaderLab/Generated" })
                        .Select(AssetDatabase.GUIDToAssetPath)
                        .Where(path => Path.GetFileNameWithoutExtension(path).EndsWith("_p" + hex, StringComparison.Ordinal))
                        .OrderBy(path => path.EndsWith(".asset", StringComparison.OrdinalIgnoreCase) ? 0 :
                            path.StartsWith(TextureRoot, StringComparison.Ordinal) ? 1 : 2).ToArray();
                    string asset = candidates.FirstOrDefault();
                    if (asset == null) asset = BuildExactEndminfNativeTexture(textureId);
                    L.Require(asset != null, "BaseV2 native texture payload is not already admitted: p" + hex);
                    context.textures[textureId] = AssetDatabase.LoadAssetAtPath<Texture2D>(asset);
                }
            }
            foreach (KeyValuePair<long, string[]> selected in AdmittedBaseV2Materials)
            {
                long id = selected.Key;
                string suffix = "_p" + unchecked((ulong)id).ToString("X16", CultureInfo.InvariantCulture) + ".json";
                string source = Directory.GetFiles(materialSourceRoot, "*" + suffix).Single();
                Dictionary<string, object> row = L.Dict(ManifestMiniJson.Deserialize(File.ReadAllText(source, Encoding.UTF8)));
                L.Require(L.PPtrId(row["m_Shader"]) == BaseV2ShaderPathId,
                    "BaseV2 material shader identity drifted: " + Path.GetFileName(source));
                string[] actualKeywords = L.List(row["m_ValidKeywords"]).Cast<object>()
                    .Select(value => Convert.ToString(value, CultureInfo.InvariantCulture)).ToArray();
                L.Require(actualKeywords.SequenceEqual(selected.Value),
                    "BaseV2 material keyword identity drifted: " + Path.GetFileName(source));
                materialRows[id] = row;
                foreach (object item in L.Dict(L.Dict(row["m_SavedProperties"])["m_TexEnvs"]).Values)
                {
                    long textureId = L.PPtrId(L.Dict(item)["m_Texture"]); if (textureId == 0 || context.textures.ContainsKey(textureId)) continue;
                    string hex = unchecked((ulong)textureId).ToString("X16", CultureInfo.InvariantCulture);
                    string[] candidates = AssetDatabase.FindAssets("t:Texture2D", new[] {
                            "Assets/EndfieldGraphShaderLab/Generated" })
                        .Select(AssetDatabase.GUIDToAssetPath)
                        .Where(path => Path.GetFileNameWithoutExtension(path).EndsWith("_p" + hex, StringComparison.Ordinal))
                        .OrderBy(path => path.EndsWith(".asset", StringComparison.OrdinalIgnoreCase) ? 0 :
                            path.StartsWith(TextureRoot, StringComparison.Ordinal) ? 1 : 2).ToArray();
                    string asset = candidates.FirstOrDefault();
                    if (asset == null) asset = BuildExactEndminfNativeTexture(textureId);
                    L.Require(asset != null, "BaseV2 native texture payload is not already admitted: p" + hex);
                    context.textures[textureId] = AssetDatabase.LoadAssetAtPath<Texture2D>(asset);
                }
            }
            if (litEffectCompatibility)
            {
                foreach (long id in LitEffectCompatibilityMaterials)
                {
                    string suffix = "_p" + unchecked((ulong)id).ToString("X16", CultureInfo.InvariantCulture) + ".json";
                    string source = Directory.GetFiles(materialSourceRoot, "*" + suffix).Single();
                    Dictionary<string, object> row = L.Dict(ManifestMiniJson.Deserialize(File.ReadAllText(source, Encoding.UTF8)));
                    string[] keywords = L.List(row["m_ValidKeywords"]).Cast<object>()
                        .Select(value => Convert.ToString(value, CultureInfo.InvariantCulture)).ToArray();
                    L.Require(L.PPtrId(row["m_Shader"]) == LitEffectShaderPathId &&
                        keywords.SequenceEqual(new[] { "_PARALLAX_MAP" }) &&
                        L.Int(row, "m_CustomRenderQueue") == 2000,
                        "LitEffect compatibility identity drifted: " + Path.GetFileName(source));
                    materialRows[id] = row;
                    string[] compatibilityTextures = {
                        "_BaseColorMap", "_MROMap", "_NormalMap", "_ParallaxMap" };
                    foreach (KeyValuePair<string, object> textureRow in
                        L.Dict(L.Dict(row["m_SavedProperties"])["m_TexEnvs"])
                            .Where(value => compatibilityTextures.Contains(value.Key)))
                    {
                        long textureId = L.PPtrId(L.Dict(textureRow.Value)["m_Texture"]);
                        if (textureId == 0 || context.textures.ContainsKey(textureId)) continue;
                        string asset = BuildExactEndminfNativeTexture(textureId);
                        if (asset == null)
                        {
                            string hex = unchecked((ulong)textureId).ToString("X16", CultureInfo.InvariantCulture);
                            string sourceTexture = Directory.GetFiles(textureSourceRoot, "*_p" + hex + ".png").Single();
                            asset = TextureRoot + "/Compatibility_" + Path.GetFileName(sourceTexture);
                            File.Copy(sourceTexture, L.ProjectAbsolute(asset), true);
                            AssetDatabase.ImportAsset(asset, ImportAssetOptions.ForceSynchronousImport);
                        }
                        context.textures[textureId] = AssetDatabase.LoadAssetAtPath<Texture2D>(asset);
                    }
                }
            }
            foreach (KeyValuePair<long, Dictionary<string, object>> entry in materialRows)
            {
                long id = entry.Key;
                Dictionary<string, object> row = entry.Value;
                string name = L.Str(row, "m_Name");
                string asset = MaterialRoot + "/" + L.Safe(name) + "_p" + unchecked((ulong)id).ToString("X16") + ".mat";
                Material material = AssetDatabase.LoadAssetAtPath<Material>(asset);
                Shader selectedShader = AdmittedBaseV2Materials.ContainsKey(id) ? baseV2Shader :
                    LitEffectCompatibilityMaterials.Contains(id) ? litEffectCompatibilityShader : shader;
                if (material == null) { material = new Material(selectedShader); AssetDatabase.CreateAsset(material, asset); }
                material.shader = selectedShader; material.name = name;
                EndfieldZhuangfyParticleEffectImporter.ApplyRecoveredMaterialPayload(material, row, context);
                if (AdmittedBaseV2Materials.ContainsKey(id))
                {
                    Dictionary<string, object> saved = L.Dict(row["m_SavedProperties"]);
                    Dictionary<string, object> colors = L.Dict(saved["m_Colors"]);
                    L.Require(colors.TryGetValue("_TintColor", out object rawTintValue),
                        "Selected Endminf BaseV2 material lost raw _TintColor " + name);
                    Dictionary<string, object> rawTintRow = L.Dict(rawTintValue);
                    Color rawTint = new Color(
                        L.Float(rawTintRow, "r"),
                        L.Float(rawTintRow, "g"),
                        L.Float(rawTintRow, "b"),
                        L.Float(rawTintRow, "a"));
                    material.SetFloat("_UseRecoveredRawTintColor", 1f);
                    material.SetVector("_RecoveredRawTintColor",
                        new Vector4(rawTint.r, rawTint.g, rawTint.b, rawTint.a));
                    Vector4 recoveredRawTint = material.GetVector("_RecoveredRawTintColor");
                    L.Require(
                        Mathf.Abs(material.GetFloat("_UseRecoveredRawTintColor") - 1f) <= 1.0e-6f &&
                        Vector4.Distance(recoveredRawTint,
                            new Vector4(rawTint.r, rawTint.g, rawTint.b, rawTint.a)) <= 1.0e-6f,
                        "Selected Endminf BaseV2 raw tint transport drifted " + name);
                }
                if (visualCompatibility && id == EndminfRefract28Material)
                {
                    Texture dissolveTexture = material.GetTexture("_DissolveTex");
                    Vector4 dissolveSpeed = material.GetVector("_DissolveUVSpeed");
                    L.Require(material.IsKeywordEnabled("_USE_DISSOLVE") &&
                        dissolveTexture != null &&
                        dissolveTexture.name.StartsWith("T_fx_mask_17_C_M", StringComparison.Ordinal) &&
                        material.GetVector("_DissolveTex_ST") == new Vector4(1f, 1f, 0f, 0f) &&
                        dissolveSpeed == Vector4.zero &&
                        Mathf.Abs(material.GetFloat("_DissolveUVRotate") - -90f) <= 1.0e-6f &&
                        Mathf.Abs(material.GetFloat("_DissolveScheduleOffset") - 0.571f) <= 1.0e-6f &&
                        Mathf.Abs(material.GetFloat("_DissolveEdgeSharp") - 1f) <= 1.0e-6f,
                        "M28 visual-compatibility dissolve payload drifted");
                }
                material.renderQueue = L.Int(row, "m_CustomRenderQueue"); EditorUtility.SetDirty(material);
                context.materials[id] = material;
                context.materialShaderPathIds[id] = AdmittedBaseV2Materials.ContainsKey(id)
                    ? BaseV2ShaderPathId : LitEffectCompatibilityMaterials.Contains(id)
                        ? LitEffectShaderPathId : RefractShaderPathId;
            }
            return context;
        }

        private static bool IsVisualCompatibilityRequested()
        {
            string value = Environment.GetEnvironmentVariable(
                VisualCompatibilityEnvironment);
            return string.Equals(value, "1", StringComparison.Ordinal) ||
                   string.Equals(value, "true", StringComparison.OrdinalIgnoreCase) ||
                   string.Equals(value, "on", StringComparison.OrdinalIgnoreCase);
        }

        private static string BuildExactEndminfNativeTexture(long pathId)
        {
            string hex = unchecked((ulong)pathId).ToString("X16", CultureInfo.InvariantCulture);
            string sourceRoot = "Assets/EndfieldGraphShaderLab/Generated/OriginalData/TexturePayloads/Endminf";
            string[] manifests = AssetDatabase.FindAssets("", new[] { sourceRoot })
                .Select(AssetDatabase.GUIDToAssetPath)
                .Where(path => path.EndsWith("_p" + hex + ".texture2d.bc7.manifest.json", StringComparison.Ordinal))
                .ToArray();
            if (manifests.Length == 0) return null;
            L.Require(manifests.Length == 1, "Ambiguous exact Endminf native texture manifest: p" + hex);
            string manifestPath = manifests[0];
            Dictionary<string, object> manifest = L.Dict(ManifestMiniJson.Deserialize(
                File.ReadAllText(L.ProjectAbsolute(manifestPath), Encoding.UTF8)));
            L.Require(L.Str(manifest, "schema") == "animestudio.texture2d-native-payload.v1" &&
                Convert.ToInt64(manifest["pathId"], CultureInfo.InvariantCulture) == pathId &&
                L.Str(manifest, "format") == "BC7" && L.Int(manifest, "formatValue") == 25 &&
                L.Int(manifest, "mipsStripped") == 0 && L.Int(manifest, "imageCount") == 1 &&
                L.Int(manifest, "textureDimension") == 2,
                "Exact Endminf native texture descriptor drifted: p" + hex);
            Dictionary<string, object> payloadRow = L.Dict(manifest["payload"]);
            string payloadPath = sourceRoot + "/" + L.Str(payloadRow, "file");
            byte[] payload = File.ReadAllBytes(L.ProjectAbsolute(payloadPath));
            string actualSha;
            using (SHA256 sha = SHA256.Create())
                actualSha = BitConverter.ToString(sha.ComputeHash(payload)).Replace("-", "");
            L.Require(payload.Length == L.Int(payloadRow, "bytes") &&
                actualSha == L.Str(payloadRow, "sha256"),
                "Exact Endminf native texture payload drifted: p" + hex);
            string name = L.Str(manifest, "name");
            string assetPath = TextureRoot + "/" + L.Safe(name) + "_p" + hex + ".asset";
            if (AssetDatabase.LoadMainAssetAtPath(assetPath) != null)
                L.Require(AssetDatabase.DeleteAsset(assetPath), "Could not replace native texture: p" + hex);
            Dictionary<string, object> settings = L.Dict(manifest["textureSettings"]);
            var texture = new Texture2D(L.Int(manifest, "width"), L.Int(manifest, "height"),
                TextureFormat.BC7, L.Int(manifest, "mipCount"), L.Int(manifest, "colorSpace") == 0) {
                name = name,
                filterMode = (FilterMode)L.Int(settings, "filterMode"),
                anisoLevel = L.Int(settings, "aniso"),
                mipMapBias = Convert.ToSingle(settings["mipBias"], CultureInfo.InvariantCulture),
                wrapModeU = (TextureWrapMode)L.Int(settings, "wrapU"),
                wrapModeV = (TextureWrapMode)L.Int(settings, "wrapV"),
                wrapModeW = (TextureWrapMode)L.Int(settings, "wrapW"),
            };
            texture.LoadRawTextureData(payload); texture.Apply(false, false);
            AssetDatabase.CreateAsset(texture, assetPath);
            AssetDatabase.ImportAsset(assetPath, ImportAssetOptions.ForceSynchronousImport);
            Texture2D loaded = AssetDatabase.LoadAssetAtPath<Texture2D>(assetPath);
            L.Require(loaded != null && loaded.width == L.Int(manifest, "width") &&
                loaded.height == L.Int(manifest, "height") && loaded.mipmapCount == L.Int(manifest, "mipCount") &&
                loaded.format == TextureFormat.BC7,
                "Unity exact Endminf native texture validation failed: p" + hex);
            return assetPath;
        }
    }
}
