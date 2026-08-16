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
    /// Builds an isolated, source-scoped Li Zhiyan start_01 diagnostic prefab.
    ///
    /// This importer deliberately does not admit the effect to the normal
    /// actor binding.  The OBJ/PNG inputs and the serialized material payload
    /// are useful for a visual laboratory only; native Mesh/Texture payload
    /// parity and the selected VFXBaseV2 variants remain explicitly closed.
    /// </summary>
    public static class EndfieldLiZhiyanStart01DiagnosticPrefabImporter
    {
        public const string ContractPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/" +
            "lizhiyan_overview_start_01_effect.json";
        public const string GeneratedRoot =
            "Assets/EndfieldGraphShaderLab/Generated/Diagnostics/" +
            "LiZhiyanStart01";
        private const string SourceRoot = GeneratedRoot + "/Source";
        private const string MaterialRoot = GeneratedRoot + "/Materials";
        private const string PrefabPath = GeneratedRoot + "/Prefabs/" +
            "P_fxui_lizhiyan_overview_start_01_DIAGNOSTIC.prefab";
        private const string ShaderName = "Endfield/Recovered/VFXBaseV2SampleStack";
        private const string ExpectedSchema =
            "endfield.lizhiyan-overview-start01-effect.v1";
        private const string ExpectedEffect =
            "P_fxui_lizhiyan_overview_start_01";
        private const string ExpectedAggregateSha256 =
            "5B83D031736E9CE864F1D2BE021C0E1A04BCA29D11291A506AD9740ADC047511";
        private const string ObjRelativePath =
            "export_full/recovered/AnimeStudio-cli/StreamingAssets/" +
            "convert_by_type/Mesh/S_fx_lzy_tiaodaifenwei_01_" +
            "pA111149ECDFB5C6C.obj";
        private const string ObjSha256 =
            "787CD7A33CDF2E4F7615296E961264982AA933CA14F9C2B859A7BC7CB9161555";
        private const string FbxRelativePath =
            "export_full/recovered/AnimeStudio-cli/StreamingAssets/" +
            "convert_by_type/Animator/P_fxui_lizhiyan_overview_start_01_" +
            "p9555228EC24376E5.fbx";
        private const string FbxSha256 =
            "DC21C45546C641DB158ED2DA9EC2C82B7DAC50CCCEF0CC97F8FFC579F5895FEC";
        private const string AnimationAssetPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/" +
            "A_fxui__lizhiyan_overview_start_01.anim";
        private const string AnimationSha256 =
            "C1D7846FB29A9AF720B2760BA2EEA97B870CAC8DF101DADE797A2301778FF920";
        private const long MeshPathId = -6840663686705882004L;
        private const long RootGameObjectPathId = 1314393592276219621L;
        private const long RootTransformPathId = 4995983695754262245L;
        private const long EffectSettingPathId = 2305038813790631653L;
        private const long AnimatorPathId = -7686199192497981723L;
        private const long AnimationHelperPathId = -8633596874860955931L;
        private const long StartAnimationClipPathId = 7360398354216100382L;
        private const float EffectLifetime = 2.2f;
        private const float AnimationSampleRate = 30f;
        private const float AnimationStopTime = 6.366667f;

        private static readonly Dictionary<long, string> ExpectedTextureHashes =
            new Dictionary<long, string>
            {
                { -3788096699771536442L,
                    "5A06D651A020EA4ECF2C06EEF1A73EF795DCEAF194E970A82244A4980B7730BB" },
                { -2436663960397463630L,
                    "0C1782D2B4B6471F89ACF98FB910A4229D5B326C59922CE5453C9B5F397737A1" },
                { -1647025128171678556L,
                    "FD335206B2DE7D4578B941CEB2BCEC79E56541017F07B3EB9F6655AD76450939" },
                { 1332343754204177352L,
                    "2A8A730813AA6C003ADE0FF96D30D8A0B83F530C9710A5BC13E4F70B6E615275" },
                { 2432870227437740027L,
                    "AEF872A21AD20A4F249D015DDDC955E7184D208ED00BB9FF682FBFF9C6C40FD1" },
                { 5503065527579778695L,
                    "AFE500C2B365D83840FF095D0A069C4079D2B7C1098451B1A94B8CABE38E97F2" },
                { 5707730051549422076L,
                    "C2541AA64B2992E47501B997B0707D1282F41A02C2486C63EC9089F0048B6B84" },
                { 7553184953741353081L,
                    "24F5CE1613BCE50CF61A983136C9DC9169E6D9F70743164DCE3D4C26ACAD4701" },
            };

        private sealed class ImportedSources
        {
            public string objAssetPath;
            public string fbxAssetPath;
            public Mesh mesh;
            public AnimationClip clip;
            public readonly Dictionary<long, Texture2D> textures =
                new Dictionary<long, Texture2D>();
        }

        private sealed class MaterialBuildReport
        {
            public int applied;
            public int unsupported;
        }

        [MenuItem(
            "Endfield/Character Recovery Lab/Build Li Zhiyan start_01 Diagnostic Prefab")]
        public static void BuildAndValidate()
        {
            Dictionary<string, object> contract = ReadContract();

            // This is intentionally a complete preflight.  No generated asset,
            // prefab, or material is touched until every pinned source hash has
            // passed and the contract identity has been checked.
            ValidateContractAndSourceHashes(contract);
            ImportedSources sources = ImportPinnedSources(contract);
            Shader shader = Shader.Find(ShaderName);
            Require(shader != null, "Missing diagnostic shader: " + ShaderName);

            Dictionary<long, Material> materials = new Dictionary<long, Material>();
            int appliedProperties = 0;
            int unsupportedProperties = 0;
            foreach (object item in List(contract, "materials"))
            {
                Dictionary<string, object> materialSource = Dict(item);
                MaterialBuildReport report;
                Material material = BuildMaterial(
                    materialSource, shader, sources.textures, out report);
                long pathId = Long(materialSource, "pathID");
                materials[pathId] = material;
                appliedProperties += report.applied;
                unsupportedProperties += report.unsupported;
            }

            GameObject generatedRoot = null;
            try
            {
                generatedRoot = BuildHierarchy(contract, sources, materials);
                string constructionReason;
                EndfieldLiZhiyanBehavioralAnimationSimulation simulation =
                    generatedRoot.GetComponent<EndfieldLiZhiyanBehavioralAnimationSimulation>();
                Require(simulation != null, "Behavioral animation simulator was not attached");
                Require(simulation.TryConstructSimulation(out constructionReason),
                    "Behavioral animation simulator failed: " + constructionReason);

                EnsureFolder(GeneratedRoot);
                EnsureFolder(GeneratedRoot + "/Prefabs");
                PrefabUtility.SaveAsPrefabAsset(generatedRoot, PrefabPath);
            }
            finally
            {
                if (generatedRoot != null)
                    UnityEngine.Object.DestroyImmediate(generatedRoot);
            }

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            EndfieldLiZhiyanStart01DiagnosticPrefabValidator.ValidateGenerated(
                PrefabPath, unsupportedProperties, appliedProperties);
            Debug.Log(
                "[Endfield Li Zhiyan] start_01 diagnostic prefab built and validated: " +
                PrefabPath + "; shader-supported properties applied=" +
                appliedProperties + ", unsupported serialized properties=" +
                unsupportedProperties + "; visibleAdmission=false.");
        }

        public static string GeneratedPrefabPath => PrefabPath;

        public static void ValidateExisting()
        {
            EndfieldLiZhiyanStart01DiagnosticPrefabValidator.ValidateGenerated(
                PrefabPath, -1, -1);
        }

        internal static Dictionary<string, object> ReadContract()
        {
            string path = ProjectAbsolute(ContractPath);
            Require(File.Exists(path), "Missing Li Zhiyan effect contract: " + path);
            return Dict(ManifestMiniJson.Deserialize(File.ReadAllText(path, Encoding.UTF8)));
        }

        private static void ValidateContractAndSourceHashes(
            Dictionary<string, object> contract)
        {
            Require(Str(contract, "schema") == ExpectedSchema,
                "Li Zhiyan start_01 contract schema drifted");
            Require(Str(contract, "effectName") == ExpectedEffect,
                "Li Zhiyan start_01 effect identity drifted");
            Dictionary<string, object> summary = Dict(contract["summary"]);
            Require(Str(summary, "sourceAggregateSha256") == ExpectedAggregateSha256,
                "Li Zhiyan start_01 aggregate contract hash drifted");
            Require(Long(Dict(contract["effectSetting"]), "pathID") == EffectSettingPathId,
                "Li Zhiyan EffectSetting PathID drifted");
            Dictionary<string, object> mesh = Dict(contract["meshDependency"]);
            Dictionary<string, object> obj = Dict(mesh["convertedObj"]);
            Require(Str(obj, "path") == ObjRelativePath &&
                Str(obj, "sha256").Equals(ObjSha256, StringComparison.OrdinalIgnoreCase),
                "Li Zhiyan shared OBJ source contract drifted");
            ValidateHash(RepositoryAbsolute(ObjRelativePath), ObjSha256, "shared OBJ");
            ValidateHash(RepositoryAbsolute(FbxRelativePath), FbxSha256, "exact start_01 FBX");
            ValidateHash(ProjectAbsolute(AnimationAssetPath), AnimationSha256,
                "resolved start animation clip");

            Dictionary<string, object> animation = Dict(contract["animation"]);
            Require(Long(animation, "animatorPathID") == AnimatorPathId &&
                Long(animation, "helperPathID") == AnimationHelperPathId,
                "Li Zhiyan animation helper identity drifted");
            Dictionary<string, object> startClip = Dict(animation["startAnimationClip"]);
            Require(Long(startClip, "pathID") == StartAnimationClipPathId &&
                Math.Abs(Float(startClip, "sampleRate") - AnimationSampleRate) < 0.0001f &&
                Math.Abs(Float(startClip, "stopTime") - AnimationStopTime) < 0.0001f,
                "Li Zhiyan start animation clip contract drifted");
            Require(animation["loopAnimationClip"] == null &&
                animation["endAnimationClip"] == null,
                "start-only Li Zhiyan contract unexpectedly gained loop/end clips");

            HashSet<long> textureIds = new HashSet<long>();
            foreach (object item in List(contract, "textureDependencies"))
            {
                Dictionary<string, object> texture = Dict(item);
                long id = Long(texture, "pathID");
                Require(ExpectedTextureHashes.ContainsKey(id),
                    "Unexpected Li Zhiyan texture dependency: " + id);
                Dictionary<string, object> png = Dict(texture["convertedPng"]);
                string relativePath = Str(png, "path");
                Require(Str(png, "sha256").Equals(ExpectedTextureHashes[id],
                    StringComparison.OrdinalIgnoreCase),
                    "Texture hash in Li Zhiyan contract drifted: " + id);
                ValidateHash(RepositoryAbsolute(relativePath), ExpectedTextureHashes[id],
                    "Li Zhiyan texture " + id);
                textureIds.Add(id);
            }
            Require(textureIds.Count == ExpectedTextureHashes.Count,
                "Li Zhiyan texture dependency census drifted");
        }

        private static ImportedSources ImportPinnedSources(
            Dictionary<string, object> contract)
        {
            EnsureFolder(GeneratedRoot);
            EnsureFolder(SourceRoot);

            string objAssetPath = SourceRoot + "/" + Path.GetFileName(ObjRelativePath);
            string fbxAssetPath = SourceRoot + "/" + Path.GetFileName(FbxRelativePath);
            File.Copy(RepositoryAbsolute(ObjRelativePath), ProjectAbsolute(objAssetPath), true);
            File.Copy(RepositoryAbsolute(FbxRelativePath), ProjectAbsolute(fbxAssetPath), true);
            AssetDatabase.ImportAsset(objAssetPath, ImportAssetOptions.ForceUpdate);
            AssetDatabase.ImportAsset(fbxAssetPath, ImportAssetOptions.ForceUpdate);

            var sources = new ImportedSources
            {
                objAssetPath = objAssetPath,
                fbxAssetPath = fbxAssetPath,
            };
            GameObject fbx = AssetDatabase.LoadAssetAtPath<GameObject>(fbxAssetPath);
            Require(fbx != null, "Pinned start_01 FBX did not import as a GameObject");
            sources.mesh = AssetDatabase.LoadAllAssetsAtPath(objAssetPath)
                .OfType<Mesh>()
                .FirstOrDefault(value => value.name == "S_fx_lzy_tiaodaifenwei_01") ??
                AssetDatabase.LoadAllAssetsAtPath(objAssetPath).OfType<Mesh>().FirstOrDefault();
            Require(sources.mesh != null,
                "Pinned shared OBJ did not import a Unity Mesh");

            foreach (object item in List(contract, "textureDependencies"))
            {
                Dictionary<string, object> texture = Dict(item);
                long id = Long(texture, "pathID");
                Dictionary<string, object> png = Dict(texture["convertedPng"]);
                string sourcePath = Str(png, "path");
                string assetPath = SourceRoot + "/" + Path.GetFileName(sourcePath);
                File.Copy(RepositoryAbsolute(sourcePath), ProjectAbsolute(assetPath), true);
                AssetDatabase.ImportAsset(assetPath, ImportAssetOptions.ForceUpdate);
                Texture2D imported = AssetDatabase.LoadAssetAtPath<Texture2D>(assetPath);
                Require(imported != null, "Pinned texture did not import: " + assetPath);
                sources.textures[id] = imported;
            }

            AssetDatabase.ImportAsset(AnimationAssetPath, ImportAssetOptions.ForceUpdate);
            sources.clip = AssetDatabase.LoadAssetAtPath<AnimationClip>(AnimationAssetPath);
            Require(sources.clip != null, "Resolved start animation clip did not import");
            return sources;
        }

        private static Material BuildMaterial(
            Dictionary<string, object> source,
            Shader shader,
            Dictionary<long, Texture2D> textures,
            out MaterialBuildReport report)
        {
            report = new MaterialBuildReport();
            long pathId = Long(source, "pathID");
            string name = Str(source, "name");
            string assetPath = MaterialRoot + "/" + Safe(name) + "_p" +
                unchecked((ulong)pathId).ToString("X16", CultureInfo.InvariantCulture) + ".mat";
            EnsureFolder(MaterialRoot);
            Material material = AssetDatabase.LoadAssetAtPath<Material>(assetPath);
            if (material == null)
            {
                material = new Material(shader);
                AssetDatabase.CreateAsset(material, assetPath);
            }
            material.shader = shader;
            material.name = name;
            material.renderQueue = Int(source, "customRenderQueue");

            Dictionary<string, object> payload = Dict(source["payload"]);
            if (payload.ContainsKey("m_EnableInstancingVariants"))
                material.enableInstancing = Bool(payload, "m_EnableInstancingVariants");
            Dictionary<string, object> saved = Dict(payload["m_SavedProperties"]);
            ApplyFloats(material, DictOrEmpty(saved, "m_Floats"), report);
            ApplyFloats(material, DictOrEmpty(saved, "m_Ints"), report);
            ApplyColors(material, DictOrEmpty(saved, "m_Colors"), report);
            ApplyTextures(material, DictOrEmpty(saved, "m_TexEnvs"), textures, report);

            IList keywords = ListValue(payload, "m_ValidKeywords");
            if (keywords == null)
                keywords = ListValue(source, "validKeywords");
            material.shaderKeywords = keywords == null
                ? Array.Empty<string>()
                : keywords.Cast<object>()
                    .Select(value => Convert.ToString(value, CultureInfo.InvariantCulture))
                    .ToArray();
            EditorUtility.SetDirty(material);
            return material;
        }

        private static void ApplyFloats(
            Material material, Dictionary<string, object> values,
            MaterialBuildReport report)
        {
            foreach (KeyValuePair<string, object> item in values)
            {
                if (!material.HasProperty(item.Key))
                {
                    report.unsupported++;
                    continue;
                }
                material.SetFloat(item.Key, FloatValue(item.Value));
                report.applied++;
            }
        }

        private static void ApplyColors(
            Material material, Dictionary<string, object> values,
            MaterialBuildReport report)
        {
            foreach (KeyValuePair<string, object> item in values)
            {
                if (!material.HasProperty(item.Key))
                {
                    report.unsupported++;
                    continue;
                }
                material.SetColor(item.Key, ColorValue(item.Value));
                report.applied++;
            }
        }

        private static void ApplyTextures(
            Material material, Dictionary<string, object> values,
            Dictionary<long, Texture2D> textures,
            MaterialBuildReport report)
        {
            foreach (KeyValuePair<string, object> item in values)
            {
                if (!material.HasProperty(item.Key))
                {
                    report.unsupported++;
                    continue;
                }
                Dictionary<string, object> textureEnv = Dict(item.Value);
                Dictionary<string, object> texturePtr =
                    textureEnv.ContainsKey("m_Texture") && textureEnv["m_Texture"] != null
                        ? Dict(textureEnv["m_Texture"])
                        : null;
                Texture2D texture = null;
                if (texturePtr != null && texturePtr.ContainsKey("m_PathID"))
                    textures.TryGetValue(Long(texturePtr, "m_PathID"), out texture);
                material.SetTexture(item.Key, texture);
                if (textureEnv.ContainsKey("m_Scale"))
                    material.SetTextureScale(item.Key, Vector2Value(textureEnv["m_Scale"]));
                if (textureEnv.ContainsKey("m_Offset"))
                    material.SetTextureOffset(item.Key, Vector2Value(textureEnv["m_Offset"]));
                report.applied++;
            }
        }

        private static GameObject BuildHierarchy(
            Dictionary<string, object> contract,
            ImportedSources sources,
            Dictionary<long, Material> materials)
        {
            IList hierarchyRows = List(contract, "hierarchyNodes");
            var objects = new Dictionary<long, GameObject>();
            var transforms = new Dictionary<long, long>();
            foreach (object item in hierarchyRows)
            {
                Dictionary<string, object> row = Dict(item);
                long gameObjectId = Long(row, "gameObjectPathID");
                long transformId = Long(row, "transformPathID");
                Dictionary<string, object> gameObject = Dict(row["gameObject"]);
                GameObject generated = new GameObject(Str(gameObject, "m_Name"));
                // This effect contract records the serialized component
                // census but not GameObject layer/active fields.  Unity's
                // default layer and active state are therefore deterministic
                // diagnostic defaults, not claims about the native prefab.
                if (gameObject.ContainsKey("m_Layer"))
                    generated.layer = Int(gameObject, "m_Layer");
                if (gameObject.ContainsKey("m_IsActive"))
                    generated.SetActive(Bool(gameObject, "m_IsActive"));
                objects[gameObjectId] = generated;
                transforms[transformId] = gameObjectId;
            }
            foreach (object item in hierarchyRows)
            {
                Dictionary<string, object> row = Dict(item);
                long gameObjectId = Long(row, "gameObjectPathID");
                Dictionary<string, object> transform = Dict(row["transform"]);
                long transformId = Long(row, "transformPathID");
                long father = PPtrId(transform["m_Father"]);
                if (father != 0L)
                {
                    Require(transforms.ContainsKey(father),
                        "Li Zhiyan hierarchy parent is absent: " + father);
                    objects[gameObjectId].transform.SetParent(
                        objects[transforms[father]].transform, false);
                }
                objects[gameObjectId].transform.localPosition =
                    Vector3Value(transform["m_LocalPosition"]);
                objects[gameObjectId].transform.localRotation =
                    QuaternionValue(transform["m_LocalRotation"]);
                objects[gameObjectId].transform.localScale =
                    Vector3Value(transform["m_LocalScale"]);
            }

            GameObject root = objects[RootGameObjectPathId];
            Require(root != null && root.transform.parent == null &&
                root.name == ExpectedEffect, "Li Zhiyan diagnostic root drifted");
            root.AddComponent<Animator>();

            var markerNodes = new List<EndfieldRecoveredStaticMeshHierarchyNodeSource>();
            foreach (object item in hierarchyRows)
            {
                Dictionary<string, object> row = Dict(item);
                long gameObjectId = Long(row, "gameObjectPathID");
                long transformId = Long(row, "transformPathID");
                markerNodes.Add(new EndfieldRecoveredStaticMeshHierarchyNodeSource
                {
                    hierarchy = Str(row, "hierarchy"),
                    gameObjectPathId = gameObjectId,
                    transformPathId = transformId,
                    generatedTransform = objects[gameObjectId].transform,
                });
            }

            var markerMeshNodes = new List<EndfieldRecoveredStaticMeshNodeSource>();
            var rendererBindings = new List<
                EndfieldLiZhiyanBehavioralAnimationSimulation.RendererProbeBinding>();
            foreach (object item in List(contract, "staticMeshNodes"))
            {
                Dictionary<string, object> row = Dict(item);
                long gameObjectId = Long(row, "gameObjectPathID");
                GameObject host = objects[gameObjectId];
                MeshFilter filter = host.AddComponent<MeshFilter>();
                MeshRenderer renderer = host.AddComponent<MeshRenderer>();
                filter.sharedMesh = sources.mesh;
                Dictionary<string, object> mesh = Dict(row["mesh"]);
                long meshPathId = Long(mesh, "pathID");
                IList materialRows = List(row, "materials");
                var assigned = new List<Material>();
                var materialIds = new List<long>();
                foreach (object materialItem in materialRows)
                {
                    long materialId = PPtrId(materialItem);
                    Require(materials.ContainsKey(materialId),
                        "Li Zhiyan material dependency is absent: " + materialId);
                    materialIds.Add(materialId);
                    assigned.Add(materials[materialId]);
                }
                renderer.sharedMaterials = assigned.ToArray();
                ApplyRendererFields(renderer, Dict(row["meshRenderer"]));
                long transformId = FindTransformId(hierarchyRows, gameObjectId);
                markerMeshNodes.Add(new EndfieldRecoveredStaticMeshNodeSource
                {
                    hierarchy = Str(row, "hierarchy"),
                    gameObjectPathId = gameObjectId,
                    transformPathId = transformId,
                    meshFilterPathId = Long(row, "meshFilterPathID"),
                    meshRendererPathId = Long(row, "meshRendererPathID"),
                    meshPathId = meshPathId,
                    materialPathIds = materialIds.ToArray(),
                    shaderPathIds = materialIds.Select(_ => -1430105248647086886L).ToArray(),
                    generatedMeshFilter = filter,
                    generatedMeshRenderer = renderer,
                    sourceRendererEnabled = renderer.enabled,
                    nativeMeshPayloadApplied = false,
                    nativeRendererPayloadApplied = false,
                    nativeTexturePayloadsApplied = false,
                    exactShaderVariantsApplied = false,
                    rendererFailClosedForUnrecoveredShader = false,
                });
                rendererBindings.Add(
                    new EndfieldLiZhiyanBehavioralAnimationSimulation.RendererProbeBinding(
                        Long(row, "meshRendererPathID"), Str(row, "hierarchy"), renderer));
            }

            Dictionary<string, object> animation = Dict(contract["animation"]);
            Dictionary<string, object> startClip = Dict(animation["startAnimationClip"]);
            Dictionary<string, object> bindings =
                Dict(startClip["floatCurveBindings"]);
            var targetHashes = List(bindings, "targetPathHashes")
                .Cast<object>().Select(ToLong).ToArray();
            var targetPaths = List(bindings, "targetPaths")
                .Cast<object>().Select(value => Str(Dict(value), "path")).ToArray();
            var propertyHashes = List(bindings, "materialPropertyHashes")
                .Cast<object>().Select(ToLong).ToArray();
            var properties = List(bindings, "materialProperties")
                .Cast<object>().Select(value => Str(Dict(value), "property")).ToArray();
            EndfieldRecoveredStaticMeshEffectSource marker =
                root.AddComponent<EndfieldRecoveredStaticMeshEffectSource>();
            marker.contractSchema = Str(contract, "schema");
            marker.effectRoot = ExpectedEffect;
            marker.sourceHierarchy = ExpectedEffect;
            marker.sourceGameObjectPathId = RootGameObjectPathId;
            marker.sourceTransformPathId = RootTransformPathId;
            marker.sourceEffectSettingPathId = EffectSettingPathId;
            marker.sourcePayloadApplied = false;
            marker.sourceEffectSettingPayloadApplied = false;
            marker.sourceEffectLoops = false;
            marker.sourceEffectDuration = EffectLifetime;
            marker.sourceEffectDelay = 0f;
            marker.sourceEffectRandomDelay = 0f;
            marker.sourceAnimatorPathId = AnimatorPathId;
            marker.sourceAnimationHelperPathId = AnimationHelperPathId;
            marker.sourceStartAnimationClipPathId = StartAnimationClipPathId;
            marker.sourceStartAnimationClip = sources.clip;
            marker.sourceStartAnimationClipName = Str(startClip, "name");
            marker.sourceStartAnimationSampleRate = AnimationSampleRate;
            marker.sourceStartAnimationStopTime = AnimationStopTime;
            marker.sourceAnimationTargetPathHashes = targetHashes;
            marker.sourceAnimationTargetPaths = targetPaths;
            marker.sourceAnimationMaterialPropertyHashes = propertyHashes;
            marker.sourceAnimationMaterialProperties = properties;
            marker.sourceAnimationBindingsResolved = true;
            marker.sourceAnimationPayloadApplied = false;
            marker.sourceAggregateSha256 = ExpectedAggregateSha256;
            marker.visibleAdmission = false;
            marker.blockedBy = new[]
            {
                "native Mesh payload and Unity import parity are not pinned",
                "native Texture2D mip payloads and Unity import parity are not pinned",
                "three VFXBaseV2 material variants lack exact selected DXBC/descriptor/draw admission",
                "normal runtime binding remains intentionally disabled for this diagnostic prefab",
            };
            marker.materialExecutionBoundary =
                "diagnostic_approximation_only: shader-supported serialized properties " +
                "applied to Endfield/Recovered/VFXBaseV2SampleStack; exact variants not admitted";
            marker.hierarchyNodes = markerNodes.ToArray();
            marker.staticMeshNodes = markerMeshNodes.ToArray();

            EndfieldLiZhiyanBehavioralAnimationSimulation simulation =
                root.AddComponent<EndfieldLiZhiyanBehavioralAnimationSimulation>();
            simulation.ConfigureSourceIdentity(
                ExpectedEffect, EffectSettingPathId, StartAnimationClipPathId,
                sources.clip, EffectLifetime);
            simulation.ConfigureRendererProbeBindings(rendererBindings.ToArray());
            return root;
        }

        private static void ApplyRendererFields(
            MeshRenderer renderer, Dictionary<string, object> source)
        {
            Dictionary<string, object> fields = source.ContainsKey("fields")
                ? Dict(source["fields"]) : source;
            if (fields.ContainsKey("m_Enabled"))
                renderer.enabled = Bool(fields, "m_Enabled");
            if (fields.ContainsKey("m_CastShadows"))
                renderer.shadowCastingMode =
                    (ShadowCastingMode)Int(fields, "m_CastShadows");
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
                "Li Zhiyan hierarchy row is absent for GameObject " + gameObjectId);
        }

        private static void ValidateHash(string absolutePath, string expected, string label)
        {
            Require(File.Exists(absolutePath), "Missing " + label + ": " + absolutePath);
            using (SHA256 sha = SHA256.Create())
            using (FileStream stream = File.OpenRead(absolutePath))
            {
                string actual = BitConverter.ToString(sha.ComputeHash(stream))
                    .Replace("-", string.Empty).ToUpperInvariant();
                Require(actual == expected.ToUpperInvariant(),
                    label + " hash mismatch; expected " + expected + ", got " + actual);
            }
        }

        private static void EnsureFolder(string assetFolder)
        {
            string[] parts = assetFolder.Split('/');
            string current = parts[0];
            for (int index = 1; index < parts.Length; index++)
            {
                string next = current + "/" + parts[index];
                if (!AssetDatabase.IsValidFolder(next))
                    AssetDatabase.CreateFolder(current, parts[index]);
                current = next;
            }
        }

        private static string ProjectRootAbsolute =>
            Directory.GetParent(Application.dataPath).FullName;

        internal static string ProjectAbsolute(string path)
        {
            return Path.GetFullPath(Path.Combine(
                ProjectRootAbsolute, path.Replace('/', Path.DirectorySeparatorChar)));
        }

        private static string RepositoryAbsolute(string path)
        {
            string repositoryRoot = Directory.GetParent(ProjectRootAbsolute).FullName;
            return Path.GetFullPath(Path.Combine(
                repositoryRoot, path.Replace('/', Path.DirectorySeparatorChar)));
        }

        private static string Safe(string value)
        {
            foreach (char invalid in Path.GetInvalidFileNameChars())
                value = value.Replace(invalid, '_');
            return value.Replace(' ', '_');
        }

        private static Dictionary<string, object> Dict(object value)
        {
            var result = value as Dictionary<string, object>;
            Require(result != null, "Expected JSON object");
            return result;
        }

        private static Dictionary<string, object> DictOrEmpty(
            Dictionary<string, object> source, string key)
        {
            return source.ContainsKey(key) && source[key] != null
                ? Dict(source[key]) : new Dictionary<string, object>();
        }

        private static IList List(Dictionary<string, object> source, string key)
        {
            Require(source.ContainsKey(key) && source[key] != null,
                "Expected JSON array: " + key);
            return (IList)source[key];
        }

        private static IList ListValue(Dictionary<string, object> source, string key)
        {
            return source.ContainsKey(key) && source[key] != null
                ? source[key] as IList : null;
        }

        private static string Str(Dictionary<string, object> source, string key)
        {
            Require(source.ContainsKey(key), "Missing JSON string: " + key);
            return Convert.ToString(source[key], CultureInfo.InvariantCulture);
        }

        private static long Long(Dictionary<string, object> source, string key)
        {
            Require(source.ContainsKey(key), "Missing JSON integer: " + key);
            return ToLong(source[key]);
        }

        private static long ToLong(object value)
        {
            if (value is long)
                return (long)value;
            if (value is int)
                return (int)value;
            if (value is double)
                return checked((long)(double)value);
            return long.Parse(Convert.ToString(value, CultureInfo.InvariantCulture),
                NumberStyles.Integer, CultureInfo.InvariantCulture);
        }

        private static int Int(Dictionary<string, object> source, string key)
        {
            return checked((int)Long(source, key));
        }

        private static float Float(Dictionary<string, object> source, string key)
        {
            Require(source.ContainsKey(key), "Missing JSON number: " + key);
            return FloatValue(source[key]);
        }

        private static float FloatValue(object value)
        {
            return Convert.ToSingle(value, CultureInfo.InvariantCulture);
        }

        private static bool Bool(Dictionary<string, object> source, string key)
        {
            Require(source.ContainsKey(key), "Missing JSON boolean: " + key);
            object value = source[key];
            if (value is bool)
                return (bool)value;
            return Math.Abs(FloatValue(value)) > 0.5f;
        }

        private static long PPtrId(object value)
        {
            Dictionary<string, object> pointer = Dict(value);
            if (pointer.ContainsKey("m_PathID"))
                return Long(pointer, "m_PathID");
            if (pointer.ContainsKey("pathID"))
                return Long(pointer, "pathID");
            return 0L;
        }

        private static Vector3 Vector3Value(object value)
        {
            Dictionary<string, object> point = Dict(value);
            return new Vector3(
                Component(point, "X", "x"),
                Component(point, "Y", "y"),
                Component(point, "Z", "z"));
        }

        private static Quaternion QuaternionValue(object value)
        {
            Dictionary<string, object> point = Dict(value);
            return new Quaternion(
                Component(point, "X", "x"),
                Component(point, "Y", "y"),
                Component(point, "Z", "z"),
                Component(point, "W", "w"));
        }

        private static Vector2 Vector2Value(object value)
        {
            Dictionary<string, object> point = Dict(value);
            return new Vector2(
                Component(point, "x", "X"), Component(point, "y", "Y"));
        }

        private static Color ColorValue(object value)
        {
            Dictionary<string, object> color = Dict(value);
            return new Color(
                Component(color, "r", "R"), Component(color, "g", "G"),
                Component(color, "b", "B"), Component(color, "a", "A"));
        }

        private static float Component(
            Dictionary<string, object> source, string preferred, string alternate)
        {
            if (source.ContainsKey(preferred))
                return FloatValue(source[preferred]);
            Require(source.ContainsKey(alternate), "Missing vector component: " + preferred);
            return FloatValue(source[alternate]);
        }

        private static void Require(bool condition, string message)
        {
            if (!condition)
                throw new InvalidOperationException(message);
        }
    }
}
