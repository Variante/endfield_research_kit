using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Imports the exact raw mesh channels and native compressed texture
    /// payloads recovered from the installed Endfield client, recreates the
    /// serialized CharInfo hierarchy, and binds a default-off strict selector
    /// into the two generated viewer scenes. The importer intentionally marks
    /// the branch incomplete while SphereOutside's HGRP/Lit deferred-lighting
    /// semantics remain unavailable in the forward compatibility renderer.
    /// </summary>
    public static class EndfieldRecoveredCharInfoPresentationBuilder
    {
        public const string SourceRoot =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/" +
            "CharInfoPresentation";
        public const string GeneratedRoot =
            "Assets/EndfieldGraphShaderLab/Generated/CharInfoPresentation";
        public const string PrefabPath =
            GeneratedRoot + "/RecoveredCharInfoPresentation.prefab";

        private const string ManifestPath = SourceRoot + "/source_manifest.json";
        private const string ReadySubsetOpenStatePath =
            SourceRoot + "/ready_subset_open_state.json";
        private const string MeshRoot = SourceRoot + "/Meshes";
        private const string TextureRoot = SourceRoot + "/Textures";
        private const string MaterialSourceRoot = SourceRoot + "/Materials";

        private const string GeneratedMeshRoot = GeneratedRoot + "/Meshes";
        private const string GeneratedTextureRoot = GeneratedRoot + "/Textures";
        private const string GeneratedMaterialRoot = GeneratedRoot + "/Materials";

        private static readonly string[] GeneratedScenePaths =
        {
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Scenes/" +
                "CharacterRecoveryViewer.unity",
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Scenes/" +
                "CharacterRenderStyleFast.unity",
        };

        private static readonly SourceFileSpec SphereMeshSource =
            new SourceFileSpec(
                MeshRoot + "/Sphere.json",
                "d38e8b88757f985dc8cbfe7ac5644708e273cfa5d73583365d57d50c3488f3d2");
        private static readonly SourceFileSpec WallMeshSource =
            new SourceFileSpec(
                MeshRoot + "/GeoSphere001.json",
                "cfaf12f935cf5f7988eacad7cce053f166806d8c03cb5132e035d41e711a69b1");
        private static readonly SourceFileSpec GridMeshSource =
            new SourceFileSpec(
                MeshRoot + "/S_GridFar.json",
                "78129cb2516b11b422850ba7ff9d526eb1d75e8a8567255b90bac44bd7454fa3");

        private static readonly TextureSourceSpec FloorTextureSource =
            new TextureSourceSpec(
                TextureRoot + "/T_D_CharFloor.bc7.bytes",
                "09155d8e3b19bec5ab9a22f1d5d7e615b4018076048453f2972edaffa4947405",
                "T_D_CharFloor",
                2048,
                2048,
                12,
                TextureFormat.BC7,
                false);
        private static readonly TextureSourceSpec FloorSdfTextureSource =
            new TextureSourceSpec(
                TextureRoot + "/deco_charInfo_floor_output_1.bc7.bytes",
                "fdf8a307af808f83dbc0df741cfeac7bbaba17f4b3151780d27d6f801400a791",
                "deco_charInfo_floor_output_1",
                2048,
                2048,
                12,
                TextureFormat.BC7,
                false);
        private static readonly TextureSourceSpec WallTextureSource =
            new TextureSourceSpec(
                TextureRoot + "/T_D_CharWall.bc7.bytes",
                "ffbaf2f9814463a4082debc94e61d2e85a5ecbb4f12bf05e5f2b983277384f53",
                "T_D_CharWall",
                2048,
                2048,
                12,
                TextureFormat.BC7,
                true);
        private static readonly TextureSourceSpec GridTextureSource =
            new TextureSourceSpec(
                TextureRoot + "/T_GridLineFar.bc7.bytes",
                "8bac75798191d32946f9467d8c3b4be46a2a83e6d6e25f75dafb84e35d2352dc",
                "T_GridLineFar",
                128,
                128,
                8,
                TextureFormat.BC7,
                false);
        private static readonly TextureSourceSpec OutsideMroTextureSource =
            new TextureSourceSpec(
                TextureRoot + "/T_default_mro_MRO.dxt1.bytes",
                "bfdb2a01c9c975eaf1e1cb539874561278917a766ed65ee14ae066196d64caeb",
                "T_default_mro_MRO",
                4,
                4,
                1,
                TextureFormat.DXT1,
                false);

        private static readonly MaterialSourceSpec GridMaterialSource =
            new MaterialSourceSpec(
                MaterialSourceRoot + "/M_GridFar.json",
                "12256d18efcaaf75563b38fca068333e30d62955ce7790664b8ee790eb562e3e",
                MaterialSourceRoot + "/M_GridFar.raw.json",
                "39caa8a4eb85a8028b114cc8092d00b2fa09eb4a70193ed2650aa927b2ee5972");
        private static readonly MaterialSourceSpec FloorMaterialSource =
            new MaterialSourceSpec(
                MaterialSourceRoot + "/M_CharInfoFloor_graph_0_material.json",
                "64eaded2524cc7df74613b0f780bd16d0a8740a9a8c37af06733ae72254823a9",
                MaterialSourceRoot + "/M_CharInfoFloor_graph_0_material.raw.json",
                "be39a97bd371003b3b9657aa5e8941fd10a441feb96da85121711886444cb308");
        private static readonly MaterialSourceSpec ShadowMaterialSource =
            new MaterialSourceSpec(
                MaterialSourceRoot + "/M_CharInfo_ShadowReceiver.json",
                "f679f51db0fcc4e013c4e4da58bbbdbf40606a696e055244cf76c690228f0122",
                MaterialSourceRoot + "/M_CharInfo_ShadowReceiver.raw.json",
                "d5e5fbe3740a958bd4795509d87a2c34425b01404eeafb5f5191d8ccce09769a");
        private static readonly MaterialSourceSpec WallMaterialSource =
            new MaterialSourceSpec(
                MaterialSourceRoot + "/M_charInfo_wall.json",
                "b0c9bb1eed8b01664caf17f5738a036dc92b6301d17632a3128526b858c642ec",
                MaterialSourceRoot + "/M_charInfo_wall.raw.json",
                "2b364d8ec030c2dbf0595b9d3272a11a4e51c601390c98d6c892d72dcb5494d4");
        private static readonly MaterialSourceSpec OutsideMaterialSource =
            new MaterialSourceSpec(
                MaterialSourceRoot + "/M_CharInfo_outside.json",
                "7b77717886e7de37a01a83c55e2980fdb8846e9030202dda4bafc34aa783a7a1",
                MaterialSourceRoot + "/M_CharInfo_outside.raw.json",
                "45b4e36ddf66010b838abdbad0e7bf8906d5cf2ec2ea9997771bd14c75ecfaf7");

        [MenuItem("Endfield/Character Recovery Lab/Build Exact CharInfo Presentation")]
        public static void BuildAndBind()
        {
            EnsureGeneratedFolders();
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);

            Mesh sphereMesh = ImportMesh(
                SphereMeshSource,
                GeneratedMeshRoot + "/Sphere.asset",
                "Sphere",
                509,
                2304,
                2);
            Mesh wallMesh = ImportMesh(
                WallMeshSource,
                GeneratedMeshRoot + "/GeoSphere001.asset",
                "GeoSphere001",
                1028,
                5400,
                0);
            Mesh gridMesh = ImportMesh(
                GridMeshSource,
                GeneratedMeshRoot + "/S_GridFar.asset",
                "S_GridFar",
                1012,
                1518,
                3);

            Texture2D floorTexture = ImportTexture(
                FloorTextureSource,
                GeneratedTextureRoot + "/T_D_CharFloor.asset");
            Texture2D floorSdfTexture = ImportTexture(
                FloorSdfTextureSource,
                GeneratedTextureRoot + "/deco_charInfo_floor_output_1.asset");
            Texture2D wallTexture = ImportTexture(
                WallTextureSource,
                GeneratedTextureRoot + "/T_D_CharWall.asset");
            Texture2D gridTexture = ImportTexture(
                GridTextureSource,
                GeneratedTextureRoot + "/T_GridLineFar.asset");
            Texture2D outsideMroTexture = ImportTexture(
                OutsideMroTextureSource,
                GeneratedTextureRoot + "/T_default_mro_MRO.asset");

            Material gridMaterial = BuildGridMaterial(gridTexture);
            Material floorMaterial = BuildFloorMaterial(
                floorTexture,
                floorSdfTexture);
            Material wallMaterial = BuildWallMaterial(wallTexture);
            Material shadowMaterial = BuildShadowMaterial();
            Material outsideMaterial = BuildUnavailableOutsideMaterial(
                outsideMroTexture);

            BuildPrefab(
                sphereMesh,
                wallMesh,
                gridMesh,
                outsideMaterial,
                floorMaterial,
                wallMaterial,
                shadowMaterial,
                gridMaterial);
            int boundSceneCount = BindIntoGeneratedScenes();
            Verify();
            Debug.Log(
                "Exact CharInfo presentation source branch built and bound: " +
                $"prefab={PrefabPath}, scenes={boundSceneCount}. " +
                "The selector remains default-off and fail-closed because " +
                "SphereOutside still requires the original HGRP/Lit deferred " +
                "lighting path.");
        }

        /// <summary>
        /// Rebuilds only the exact installed-data mesh, MRO texture, and
        /// source-specialized material needed by the default-off five-MRT
        /// SphereOutside HGBuffer diagnostic. This intentionally avoids scene
        /// mutation and the broader presentation-scene binding verifier.
        /// </summary>
        public static void BuildSphereOutsideHGBufferDiagnosticAssets()
        {
            EnsureGeneratedFolders();
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);

            ImportMesh(
                SphereMeshSource,
                GeneratedMeshRoot + "/Sphere.asset",
                "Sphere",
                509,
                2304,
                2);
            Texture2D outsideMroTexture = ImportTexture(
                OutsideMroTextureSource,
                GeneratedTextureRoot + "/T_default_mro_MRO.asset");
            BuildUnavailableOutsideMaterial(outsideMroTexture);

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
        }

        /// <summary>
        /// Binds the already recovered source presentation prefab into one
        /// open viewer scene. This deliberately does not rebuild source assets
        /// or change the prefab's default-off contract.
        /// </summary>
        public static EndfieldRecoveredCharInfoPresentation EnsureBoundIntoScene(
            Scene scene,
            bool enableReadySubsetDiagnostic)
        {
            if (!scene.IsValid() || !scene.isLoaded)
                throw new ArgumentException("A loaded scene is required.", nameof(scene));

            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
            if (prefab == null)
            {
                throw new FileNotFoundException(
                    "The recovered CharInfo presentation prefab is missing. " +
                    "Run Build Exact CharInfo Presentation first.",
                    PrefabPath);
            }

            EndfieldRecoveredCharInfoPresentation controller = null;
            foreach (EndfieldRecoveredCharInfoPresentation candidate in
                UnityEngine.Object.FindObjectsOfType<
                    EndfieldRecoveredCharInfoPresentation>(true))
            {
                if (candidate == null || candidate.gameObject.scene != scene)
                    continue;
                if (controller == null)
                {
                    controller = candidate;
                    continue;
                }
                UnityEngine.Object.DestroyImmediate(candidate.gameObject);
            }

            if (controller == null)
            {
                GameObject instance = (GameObject)PrefabUtility.InstantiatePrefab(
                    prefab,
                    scene);
                if (instance == null)
                    throw new InvalidOperationException(
                        $"Could not instantiate {PrefabPath} into {scene.path}.");
                instance.name = "RecoveredCharInfoPresentation";
                SetLocalTransform(
                    instance.transform,
                    Vector3.zero,
                    Quaternion.identity,
                    Vector3.one);
                controller =
                    instance.GetComponent<EndfieldRecoveredCharInfoPresentation>();
            }

            Renderer compatibilityBackdrop = FindCompatibilityBackdrop(scene);
            if (controller == null || compatibilityBackdrop == null)
            {
                throw new InvalidDataException(
                    $"Could not bind the recovered CharInfo presentation in {scene.path}.");
            }

            controller.compatibilityBackdropRenderer = compatibilityBackdrop;
            controller.enableRecoveredPresentation = false;
            controller.enableReadySubsetDiagnostic =
                enableReadySubsetDiagnostic;
            controller.enableEndminfSourceBackground = false;
            controller.enableEndminfSourceForwardOverlay = false;
            controller.RefreshSelection();
            EditorUtility.SetDirty(controller);
            return controller;
        }

        [MenuItem("Endfield/Character Recovery Lab/Verify Exact CharInfo Presentation")]
        public static void Verify()
        {
            ValidateMeshAsset(
                AssetDatabase.LoadAssetAtPath<Mesh>(
                    GeneratedMeshRoot + "/Sphere.asset"),
                "Sphere",
                509,
                2304,
                2,
                true);
            ValidateMeshAsset(
                AssetDatabase.LoadAssetAtPath<Mesh>(
                    GeneratedMeshRoot + "/GeoSphere001.asset"),
                "GeoSphere001",
                1028,
                5400,
                0,
                true);
            ValidateMeshAsset(
                AssetDatabase.LoadAssetAtPath<Mesh>(
                    GeneratedMeshRoot + "/S_GridFar.asset"),
                "S_GridFar",
                1012,
                1518,
                3,
                false);

            VerifyTextureAsset(
                AssetDatabase.LoadAssetAtPath<Texture2D>(
                    GeneratedTextureRoot + "/T_D_CharFloor.asset"),
                FloorTextureSource);
            VerifyTextureAsset(
                AssetDatabase.LoadAssetAtPath<Texture2D>(
                    GeneratedTextureRoot + "/deco_charInfo_floor_output_1.asset"),
                FloorSdfTextureSource);
            VerifyTextureAsset(
                AssetDatabase.LoadAssetAtPath<Texture2D>(
                    GeneratedTextureRoot + "/T_D_CharWall.asset"),
                WallTextureSource);
            VerifyTextureAsset(
                AssetDatabase.LoadAssetAtPath<Texture2D>(
                    GeneratedTextureRoot + "/T_GridLineFar.asset"),
                GridTextureSource);
            VerifyTextureAsset(
                AssetDatabase.LoadAssetAtPath<Texture2D>(
                    GeneratedTextureRoot + "/T_default_mro_MRO.asset"),
                OutsideMroTextureSource);

            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
            if (prefab == null)
                throw new InvalidDataException($"Missing presentation prefab: {PrefabPath}");
            EndfieldRecoveredCharInfoPresentation controller =
                prefab.GetComponent<EndfieldRecoveredCharInfoPresentation>();
            if (controller == null)
                throw new InvalidDataException("Presentation prefab has no strict selector.");
            if (controller.enableRecoveredPresentation ||
                controller.enableReadySubsetDiagnostic ||
                controller.enableEndminfSourceBackground ||
                controller.enableEndminfSourceForwardOverlay ||
                controller.exactSourceAssetsReady ||
                controller.sourceContent == null ||
                controller.sourceContent.activeSelf)
            {
                throw new InvalidDataException(
                    "Presentation prefab is not default-off and fail-closed.");
            }
            if (controller.settledOpenState == null ||
                AssetDatabase.GetAssetPath(controller.settledOpenState) !=
                    ReadySubsetOpenStatePath)
            {
                throw new InvalidDataException(
                    "Presentation prefab is missing the source-derived " +
                    "settled/opened ready-subset state.");
            }
            string readySubsetFailure;
            if (!controller.ValidateReadySubsetReadiness(
                    out readySubsetFailure))
            {
                throw new InvalidDataException(
                    "Ready-subset diagnostic source contract failed: " +
                    readySubsetFailure);
            }
            string endminfSourceBackgroundFailure;
            if (!controller.ValidateEndminfSourceBackgroundReadiness(
                    out endminfSourceBackgroundFailure))
            {
                throw new InvalidDataException(
                    "Endminf source-background contract failed: " +
                    endminfSourceBackgroundFailure);
            }
            if (controller.sphereOutsideRenderer == null ||
                controller.floorRenderer == null ||
                controller.wallRenderer == null ||
                controller.shadowPlaneRenderer == null ||
                controller.farGridRenderer == null)
            {
                throw new InvalidDataException(
                    "Presentation prefab is missing one or more exact renderer references.");
            }
            if (controller.sphereOutsideRenderer.sharedMaterial == null ||
                controller.sphereOutsideRenderer.sharedMaterial.shader == null ||
                controller.sphereOutsideRenderer.sharedMaterial.shader.name !=
                    EndfieldRecoveredCharInfoPresentation.UnavailableLitShaderName)
            {
                throw new InvalidDataException(
                    "SphereOutside must retain the explicit no-draw HGRP/Lit " +
                    "unavailable marker until deferred semantics are recovered.");
            }

            VerifyPrefabHierarchy(controller);
            VerifyGeneratedSceneBindings();

            Debug.Log(
                "Exact CharInfo presentation static verification passed; " +
                "readiness remains false at the HGRP/Lit deferred-lighting gate.");
        }

        private static void VerifyPrefabHierarchy(
            EndfieldRecoveredCharInfoPresentation controller)
        {
            Transform content = controller.sourceContent.transform;
            if (content.name != "ExactSourceContent" ||
                content.parent != controller.transform)
            {
                throw new InvalidDataException(
                    "Presentation prefab lost its ExactSourceContent root.");
            }
            VerifyLocalTransform(
                content,
                Vector3.zero,
                Quaternion.identity,
                Vector3.one,
                "ExactSourceContent");

            Transform sphere = controller.sphereOutsideRenderer.transform;
            Transform meshRoot = sphere.parent;
            Transform charInfoScene = meshRoot != null ? meshRoot.parent : null;
            Transform charInfoChar =
                charInfoScene != null ? charInfoScene.parent : null;
            if (meshRoot == null || meshRoot.name != "Mesh" ||
                charInfoScene == null || charInfoScene.name != "CharInfo_Scene" ||
                charInfoChar == null || charInfoChar.name != "CharInfoChar" ||
                charInfoChar.parent != content)
            {
                throw new InvalidDataException(
                    "Presentation prefab lost the serialized CharInfo hierarchy.");
            }
            VerifyLocalTransform(
                charInfoChar,
                Vector3.zero,
                Quaternion.identity,
                Vector3.one,
                "CharInfoChar");
            VerifyLocalTransform(
                charInfoScene,
                Vector3.zero,
                Quaternion.identity,
                Vector3.one,
                "CharInfo_Scene");
            VerifyLocalTransform(
                meshRoot,
                new Vector3(-1.9700003f, 0.0f, -1.5599998f),
                new Quaternion(0.0f, -0.0914292f, 0.0f, 0.9958116f),
                Vector3.one,
                "Mesh");

            VerifyRenderer(
                controller.sphereOutsideRenderer,
                meshRoot,
                "SphereOutside",
                "Sphere",
                "M_CharInfo_outside",
                EndfieldRecoveredCharInfoPresentation.UnavailableLitShaderName,
                new Vector3(2.3f, 0.0f, 1.7f),
                Quaternion.identity,
                new Vector3(50.0f, 50.0f, 50.0f),
                ShadowCastingMode.Off,
                LightProbeUsage.BlendProbes,
                1u);
            VerifyRenderer(
                controller.floorRenderer,
                meshRoot,
                "CharFloorEffect",
                "Quad",
                "M_CharInfoFloor_graph_0_material",
                EndfieldRecoveredCharInfoPresentation.FloorShaderName,
                new Vector3(1.8081535f, 0.0f, 2.0754473f),
                new Quaternion(
                    0.15008254f,
                    0.6909958f,
                    -0.6909958f,
                    0.15008254f),
                new Vector3(35.0f, 35.0f, 35.0f),
                ShadowCastingMode.On,
                LightProbeUsage.Off,
                1u);
            VerifyRenderer(
                controller.wallRenderer,
                meshRoot,
                "GeoSphere001",
                "GeoSphere001",
                "M_charInfo_wall",
                EndfieldRecoveredCharInfoPresentation.WallShaderName,
                new Vector3(2.3f, 0.0f, 1.7f),
                new Quaternion(0.7071068f, 0.0f, 0.0f, 0.7071068f),
                new Vector3(0.75f, 0.75f, 0.75f),
                ShadowCastingMode.On,
                LightProbeUsage.BlendProbes,
                1u);
            VerifyRenderer(
                controller.shadowPlaneRenderer,
                meshRoot,
                "ShadowPlane",
                "Plane",
                "M_CharInfo_ShadowReceiver",
                EndfieldRecoveredCharInfoPresentation.ShadowReceiverShaderName,
                new Vector3(2.278f, 0.032f, 1.114f),
                Quaternion.identity,
                Vector3.one,
                ShadowCastingMode.On,
                LightProbeUsage.Off,
                uint.MaxValue);

            Transform far = controller.farGridRenderer.transform;
            Transform gridDeco = far.parent;
            if (gridDeco == null || gridDeco.name != "GridDeco" ||
                gridDeco.parent != charInfoChar)
            {
                throw new InvalidDataException(
                    "Presentation prefab lost the GridDeco/Far hierarchy.");
            }
            VerifyLocalTransform(
                gridDeco,
                Vector3.zero,
                Quaternion.identity,
                Vector3.one,
                "GridDeco");
            VerifyRenderer(
                controller.farGridRenderer,
                gridDeco,
                "Far",
                "S_GridFar",
                "M_GridFar",
                EndfieldRecoveredCharInfoPresentation.GridShaderName,
                new Vector3(-10.53f, 1.4f, -13.4f),
                new Quaternion(0.0f, 0.3007058f, 0.0f, 0.95371693f),
                Vector3.one,
                ShadowCastingMode.On,
                LightProbeUsage.BlendProbes,
                1u);
        }

        private static void VerifyRenderer(
            Renderer renderer,
            Transform expectedParent,
            string objectName,
            string meshName,
            string materialName,
            string shaderName,
            Vector3 localPosition,
            Quaternion localRotation,
            Vector3 localScale,
            ShadowCastingMode shadowCastingMode,
            LightProbeUsage lightProbeUsage,
            uint renderingLayerMask)
        {
            MeshFilter filter = renderer.GetComponent<MeshFilter>();
            Material material = renderer.sharedMaterial;
            if (renderer.name != objectName || renderer.transform.parent != expectedParent ||
                renderer.gameObject.layer != 13 || !renderer.enabled ||
                filter == null || filter.sharedMesh == null ||
                filter.sharedMesh.name != meshName || material == null ||
                material.name != materialName || material.shader == null ||
                material.shader.name != shaderName ||
                renderer.shadowCastingMode != shadowCastingMode ||
                !renderer.receiveShadows ||
                renderer.motionVectorGenerationMode !=
                    MotionVectorGenerationMode.Object ||
                renderer.lightProbeUsage != lightProbeUsage ||
                renderer.reflectionProbeUsage != ReflectionProbeUsage.BlendProbes ||
                renderer.renderingLayerMask != renderingLayerMask ||
                renderer.sortingLayerID != 0 || renderer.sortingOrder != 0 ||
                renderer.rendererPriority != 0)
            {
                throw new InvalidDataException(
                    $"Recovered renderer state mismatch for {objectName}.");
            }
            VerifyLocalTransform(
                renderer.transform,
                localPosition,
                localRotation,
                localScale,
                objectName);
        }

        private static void VerifyLocalTransform(
            Transform transform,
            Vector3 expectedPosition,
            Quaternion expectedRotation,
            Vector3 expectedScale,
            string label)
        {
            const float toleranceSquared = 1.0e-10f;
            float rotationError =
                1.0f - Mathf.Abs(Quaternion.Dot(transform.localRotation, expectedRotation));
            if ((transform.localPosition - expectedPosition).sqrMagnitude >
                    toleranceSquared ||
                (transform.localScale - expectedScale).sqrMagnitude >
                    toleranceSquared ||
                rotationError > 1.0e-6f)
            {
                throw new InvalidDataException(
                    $"Recovered local transform mismatch for {label}.");
            }
        }

        private static void VerifyGeneratedSceneBindings()
        {
            SceneSetup[] previousSetup = EditorSceneManager.GetSceneManagerSetup();
            try
            {
                foreach (string scenePath in GeneratedScenePaths)
                {
                    Scene scene = EditorSceneManager.OpenScene(
                        scenePath,
                        OpenSceneMode.Single);
                    EndfieldRecoveredCharInfoPresentation found = null;
                    int count = 0;
                    foreach (EndfieldRecoveredCharInfoPresentation controller in
                        UnityEngine.Object.FindObjectsOfType<
                            EndfieldRecoveredCharInfoPresentation>(true))
                    {
                        if (controller == null || controller.gameObject.scene != scene)
                            continue;
                        found = controller;
                        count++;
                    }
                    string settledOpenStatePath = found == null ||
                        found.settledOpenState == null
                            ? string.Empty
                            : AssetDatabase.GetAssetPath(found.settledOpenState);
                    string backdropName = found == null ||
                        found.compatibilityBackdropRenderer == null
                            ? string.Empty
                            : found.compatibilityBackdropRenderer.gameObject.name;
                    bool sourceContentActive = found != null &&
                        found.sourceContent != null &&
                        found.sourceContent.activeSelf;
                    if (count != 1 || found == null ||
                        found.enableRecoveredPresentation ||
                        found.enableReadySubsetDiagnostic ||
                        found.enableEndminfSourceBackground ||
                        found.enableEndminfSourceForwardOverlay ||
                        found.exactSourceAssetsReady || found.sourceContent == null ||
                        sourceContentActive ||
                        settledOpenStatePath != ReadySubsetOpenStatePath ||
                        found.compatibilityBackdropRenderer == null ||
                        backdropName != "ReferenceBackdrop")
                    {
                        throw new InvalidDataException(
                            "Strict presentation scene binding mismatch: " +
                            $"scene={scenePath}, controllers={count}, " +
                            $"found={(found != null)}, " +
                            $"exact={found?.enableRecoveredPresentation}, " +
                            $"readySubset={found?.enableReadySubsetDiagnostic}, " +
                            $"sourceBackground={found?.enableEndminfSourceBackground}, " +
                            $"sourceForwardOverlay={found?.enableEndminfSourceForwardOverlay}, " +
                            $"sourceReady={found?.exactSourceAssetsReady}, " +
                            $"sourceContent={(found?.sourceContent != null)}, " +
                            $"sourceContentActive={sourceContentActive}, " +
                            $"settledOpenState={settledOpenStatePath}, " +
                            $"backdrop={backdropName}. The backdrop renderer's " +
                            "serialized enabled state is intentionally not a binding " +
                            "gate; the runtime selector owns it.");
                    }
                }
            }
            finally
            {
                if (previousSetup != null && previousSetup.Length > 0)
                    EditorSceneManager.RestoreSceneManagerSetup(previousSetup);
            }
        }

        private static Mesh ImportMesh(
            SourceFileSpec source,
            string assetPath,
            string expectedName,
            int expectedVertexCount,
            int expectedIndexCount,
            int expectedUv1Dimension)
        {
            MeshJson payload = ReadJson<MeshJson>(source);
            ValidateMeshJson(
                payload,
                expectedName,
                expectedVertexCount,
                expectedIndexCount,
                expectedUv1Dimension);

            Mesh rebuilt = new Mesh
            {
                name = expectedName,
                indexFormat = expectedVertexCount > ushort.MaxValue
                    ? IndexFormat.UInt32
                    : IndexFormat.UInt16,
            };
            rebuilt.SetVertices(ToVector3(payload.m_Vertices));
            rebuilt.SetNormals(ToVector3(payload.m_Normals));
            if (payload.m_Tangents != null && payload.m_Tangents.Length > 0)
                rebuilt.SetTangents(ToVector4(payload.m_Tangents));
            rebuilt.SetUVs(0, ToVector2(payload.m_UV0));
            if (expectedUv1Dimension == 2)
                rebuilt.SetUVs(1, ToVector2(payload.m_UV1));
            else if (expectedUv1Dimension == 3)
                rebuilt.SetUVs(1, ToVector3(payload.m_UV1));

            rebuilt.subMeshCount = 1;
            rebuilt.SetIndices(
                payload.m_Indices,
                MeshTopology.Triangles,
                0,
                false,
                0);
            AabbJson sourceBounds = payload.m_SubMeshes[0].localAABB;
            Bounds importedBounds = new Bounds(
                ToVector3(sourceBounds.m_Center),
                ToVector3(sourceBounds.m_Extent) * 2.0f);
            SubMeshDescriptor subMesh = rebuilt.GetSubMesh(0);
            subMesh.bounds = importedBounds;
            rebuilt.SetSubMesh(
                0,
                subMesh,
                MeshUpdateFlags.DontRecalculateBounds);
            rebuilt.bounds = importedBounds;

            Mesh imported = ReplaceOrCreateAsset(rebuilt, assetPath);
            ValidateMeshAsset(
                imported,
                expectedName,
                expectedVertexCount,
                expectedIndexCount,
                expectedUv1Dimension,
                payload.m_Tangents != null && payload.m_Tangents.Length > 0);
            return imported;
        }

        private static void ValidateMeshJson(
            MeshJson mesh,
            string expectedName,
            int expectedVertexCount,
            int expectedIndexCount,
            int expectedUv1Dimension)
        {
            if (mesh == null || mesh.m_Name != expectedName ||
                mesh.m_VertexCount != expectedVertexCount ||
                mesh.m_Vertices == null ||
                mesh.m_Vertices.Length != expectedVertexCount * 3 ||
                mesh.m_Normals == null ||
                mesh.m_Normals.Length != expectedVertexCount * 3 ||
                mesh.m_UV0 == null ||
                mesh.m_UV0.Length != expectedVertexCount * 2 ||
                mesh.m_Indices == null ||
                mesh.m_Indices.Length != expectedIndexCount ||
                mesh.m_SubMeshes == null ||
                mesh.m_SubMeshes.Length != 1 ||
                mesh.m_SubMeshes[0].firstByte != 0 ||
                mesh.m_SubMeshes[0].baseVertex != 0 ||
                mesh.m_SubMeshes[0].indexCount != expectedIndexCount ||
                mesh.m_SubMeshes[0].topology != "Triangles")
            {
                throw new InvalidDataException(
                    $"Recovered mesh JSON shape mismatch for {expectedName}.");
            }
            int expectedUv1FloatCount =
                expectedVertexCount * expectedUv1Dimension;
            int actualUv1FloatCount = mesh.m_UV1 == null ? 0 : mesh.m_UV1.Length;
            if (actualUv1FloatCount != expectedUv1FloatCount)
            {
                throw new InvalidDataException(
                    $"Recovered mesh {expectedName} UV1 dimension mismatch: " +
                    $"floats={actualUv1FloatCount}, expected={expectedUv1FloatCount}.");
            }
        }

        private static void ValidateMeshAsset(
            Mesh mesh,
            string expectedName,
            int expectedVertexCount,
            int expectedIndexCount,
            int expectedUv1Dimension,
            bool expectTangents)
        {
            if (mesh == null || mesh.name != expectedName ||
                mesh.vertexCount != expectedVertexCount ||
                mesh.subMeshCount != 1 ||
                mesh.GetIndexCount(0) != (uint)expectedIndexCount ||
                !mesh.HasVertexAttribute(VertexAttribute.Position) ||
                !mesh.HasVertexAttribute(VertexAttribute.Normal) ||
                !mesh.HasVertexAttribute(VertexAttribute.TexCoord0) ||
                mesh.HasVertexAttribute(VertexAttribute.Color) ||
                mesh.HasVertexAttribute(VertexAttribute.Tangent) != expectTangents)
            {
                throw new InvalidDataException(
                    $"Imported recovered mesh validation failed for {expectedName}.");
            }
            bool hasUv1 = mesh.HasVertexAttribute(VertexAttribute.TexCoord1);
            if ((expectedUv1Dimension == 0 && hasUv1) ||
                (expectedUv1Dimension != 0 &&
                 (!hasUv1 || mesh.GetVertexAttributeDimension(
                     VertexAttribute.TexCoord1) != expectedUv1Dimension)))
            {
                throw new InvalidDataException(
                    $"Imported recovered mesh UV1 validation failed for {expectedName}.");
            }
            if (!BoundsApproximatelyEqual(mesh.GetSubMesh(0).bounds, mesh.bounds))
            {
                throw new InvalidDataException(
                    $"Imported recovered mesh submesh bounds failed for {expectedName}: " +
                    $"{mesh.GetSubMesh(0).bounds} != {mesh.bounds}.");
            }
        }

        private static bool BoundsApproximatelyEqual(Bounds left, Bounds right)
        {
            const float epsilon = 0.00001f;
            return Vector3.SqrMagnitude(left.center - right.center) <=
                       epsilon * epsilon &&
                   Vector3.SqrMagnitude(left.extents - right.extents) <=
                       epsilon * epsilon;
        }

        private static Texture2D ImportTexture(
            TextureSourceSpec source,
            string assetPath)
        {
            byte[] payload = ReadAndValidateBytes(source.File);
            Texture2D rebuilt = new Texture2D(
                source.Width,
                source.Height,
                source.Format,
                source.MipCount,
                source.Linear)
            {
                name = source.Name,
                filterMode = FilterMode.Bilinear,
                anisoLevel = 1,
                mipMapBias = 0.0f,
                wrapModeU = TextureWrapMode.Repeat,
                wrapModeV = TextureWrapMode.Repeat,
                wrapModeW = TextureWrapMode.Repeat,
            };
            rebuilt.LoadRawTextureData(payload);
            rebuilt.Apply(false, false);
            Texture2D imported = ReplaceOrCreateAsset(rebuilt, assetPath);
            VerifyTextureAsset(imported, source);
            return imported;
        }

        private static void VerifyTextureAsset(
            Texture2D texture,
            TextureSourceSpec source)
        {
            if (texture == null || texture.name != source.Name ||
                texture.width != source.Width ||
                texture.height != source.Height ||
                texture.mipmapCount != source.MipCount ||
                texture.format != source.Format ||
                texture.isDataSRGB == source.Linear ||
                texture.filterMode != FilterMode.Bilinear ||
                texture.anisoLevel != 1 ||
                Math.Abs(texture.mipMapBias) > 0.000001f ||
                texture.wrapModeU != TextureWrapMode.Repeat ||
                texture.wrapModeV != TextureWrapMode.Repeat ||
                texture.wrapModeW != TextureWrapMode.Repeat)
            {
                throw new InvalidDataException(
                    $"Imported recovered texture validation failed for {source.Name}.");
            }

            var nativePayload = texture.GetRawTextureData<byte>();
            byte[] payload = new byte[nativePayload.Length];
            for (int index = 0; index < payload.Length; index++)
                payload[index] = nativePayload[index];
            string actualHash = ComputeSha256(payload);
            if (!string.Equals(
                    actualHash,
                    source.File.Sha256,
                    StringComparison.OrdinalIgnoreCase))
            {
                throw new InvalidDataException(
                    $"Imported texture payload hash mismatch for {source.Name}: " +
                    $"{actualHash} != {source.File.Sha256}.");
            }
        }

        private static Material BuildGridMaterial(Texture2D texture)
        {
            MaterialBundle source = ReadMaterial(GridMaterialSource);
            ValidateMaterialIdentity(
                source,
                "M_GridFar",
                5133847487179873275L,
                2950,
                "_ALPHATEST_ON",
                "_USE_GRID_LINE");
            ValidateTextureReference(
                source.Normalized.m_SavedProperties.m_TexEnvs._MainTex,
                -169345958455036648L,
                "M_GridFar._MainTex");

            Material material = NewMaterial(
                source,
                EndfieldRecoveredCharInfoPresentation.GridShaderName);
            SavedPropertiesJson saved = source.Normalized.m_SavedProperties;
            SetTexture(material, "_MainTex", texture, saved.m_TexEnvs._MainTex);
            SetColor(material, "_TintColor", saved.m_Colors._TintColor);
            SetVector(material, "_MainTexUVSpeed", saved.m_Colors._MainTexUVSpeed);
            SetFloats(
                material,
                saved.m_Floats,
                "_AlphaClipThreshold",
                "_AlphaDstBlend",
                "_AlphaSrcBlend",
                "_CullMode",
                "_DisableVertColor",
                "_DstBlend",
                "_ExpIntensity",
                "_ExpThreshold",
                "_ForceMoveToFarPlane",
                "_GridLineWidth",
                "_IgnorePostExposure",
                "_InParticle",
                "_MainTexUVRotate",
                "_MainUVSet",
                "_NearCameraFadeDistanceEnd",
                "_NearCameraFadeDistanceEnd2",
                "_NearCameraFadeDistanceStart",
                "_NearCameraFadeDistanceStart2",
                "_SrcBlend",
                "_TintColorAlpha",
                "_TintColorIntensity",
                "_UseAlphaTest",
                "_UseGridLine",
                "_UseMainTexAsAlpha",
                "_UseNearCameraFade",
                "_ZTest",
                "_ZWriteMode");
            return SaveMaterial(
                material,
                GeneratedMaterialRoot + "/M_GridFar.mat");
        }

        private static Material BuildFloorMaterial(
            Texture2D baseTexture,
            Texture2D sdfTexture)
        {
            MaterialBundle source = ReadMaterial(FloorMaterialSource);
            ValidateMaterialIdentity(
                source,
                "M_CharInfoFloor_graph_0_material",
                146085953729050126L,
                2000,
                "_APPLY_COLOR_BANDING_DITHER",
                "_USE_BLEND");
            SavedPropertiesJson saved = source.Normalized.m_SavedProperties;
            ValidateTextureReference(
                saved.m_TexEnvs._BaseTex,
                -4372870815771908668L,
                "M_CharInfoFloor._BaseTex");
            ValidateTextureReference(
                saved.m_TexEnvs._BlendSDFTex,
                -3113807286584698696L,
                "M_CharInfoFloor._BlendSDFTex");

            Material material = NewMaterial(
                source,
                EndfieldRecoveredCharInfoPresentation.FloorShaderName);
            SetTexture(material, "_BaseTex", baseTexture, saved.m_TexEnvs._BaseTex);
            SetTexture(
                material,
                "_BlendSDFTex",
                sdfTexture,
                saved.m_TexEnvs._BlendSDFTex);
            SetColor(material, "_TintColor", saved.m_Colors._TintColor);
            SetColor(material, "_BlendTint", saved.m_Colors._BlendTint);
            SetFloats(
                material,
                saved.m_Floats,
                "_APPLY_COLOR_BANDING_DITHER",
                "_CullMode",
                "_DstBlend",
                "_IgnorePostExposure",
                "_SDFSwitchEnd",
                "_SDFSwitchStart",
                "_SrcBlend",
                "_SurfaceType",
                "_TintColorAlpha",
                "_TintColorIntensity",
                "_UseBlend",
                "_ZTest",
                "_ZWrite");
            return SaveMaterial(
                material,
                GeneratedMaterialRoot +
                    "/M_CharInfoFloor_graph_0_material.mat");
        }

        private static Material BuildWallMaterial(Texture2D texture)
        {
            MaterialBundle source = ReadMaterial(WallMaterialSource);
            ValidateMaterialIdentity(
                source,
                "M_charInfo_wall",
                -1430105248647086886L,
                2000);
            SavedPropertiesJson saved = source.Normalized.m_SavedProperties;
            ValidateTextureReference(
                saved.m_TexEnvs._MainTex,
                6218978860208401686L,
                "M_charInfo_wall._MainTex");

            Material material = NewMaterial(
                source,
                EndfieldRecoveredCharInfoPresentation.WallShaderName);
            SetTexture(material, "_MainTex", texture, saved.m_TexEnvs._MainTex);
            SetColor(material, "_TintColor", saved.m_Colors._TintColor);
            SetFloats(
                material,
                saved.m_Floats,
                "_CullMode",
                "_IgnorePostExposure",
                "_ProcedureAlpha",
                "_SurfaceType",
                "_TintColorAlpha",
                "_TintColorIntensity",
                "_UseMainTexAsAlpha",
                "_ZTest",
                "_ZWrite");
            return SaveMaterial(
                material,
                GeneratedMaterialRoot + "/M_charInfo_wall.mat");
        }

        private static Material BuildShadowMaterial()
        {
            MaterialBundle source = ReadMaterial(ShadowMaterialSource);
            ValidateMaterialIdentity(
                source,
                "M_CharInfo_ShadowReceiver",
                2521598335323475540L,
                -1);
            SavedPropertiesJson saved = source.Normalized.m_SavedProperties;
            Material material = NewMaterial(
                source,
                EndfieldRecoveredCharInfoPresentation.ShadowReceiverShaderName);
            SetColor(material, "_ShadowColor", saved.m_Colors._ShadowColor);
            SetColor(material, "_CapsuleAoColor", saved.m_Colors._CapsuleAoColor);
            SetFloats(
                material,
                saved.m_Floats,
                "_CircleFade",
                "_CircleFadeDistance",
                "_CircleFadeSmoothness",
                "_DisableCharacterSelfShadow",
                "_DisableSceneShadow");
            return SaveMaterial(
                material,
                GeneratedMaterialRoot + "/M_CharInfo_ShadowReceiver.mat");
        }

        private static Material BuildUnavailableOutsideMaterial(Texture2D mroTexture)
        {
            MaterialBundle source = ReadMaterial(OutsideMaterialSource);
            ValidateMaterialIdentity(
                source,
                "M_CharInfo_outside",
                5324015590718682574L,
                2000);
            SavedPropertiesJson saved = source.Normalized.m_SavedProperties;
            ValidateTextureReference(
                saved.m_TexEnvs._MROMap,
                -1246962829539794806L,
                "M_CharInfo_outside._MROMap");
            Material material = NewMaterial(
                source,
                EndfieldRecoveredCharInfoPresentation.UnavailableLitShaderName);
            SetTexture(material, "_MROMap", mroTexture, saved.m_TexEnvs._MROMap);
            SetColor(material, "_BaseColor", saved.m_Colors._BaseColor);
            SetFloats(
                material,
                saved.m_Floats,
                "_CullMode",
                "_EnableSubsurface",
                "_IgnorePostExposure",
                "_Metallic",
                "_NormalScale",
                "_OcclusionStrength",
                "_PorosityFactorX",
                "_PorosityFactorY",
                "_PorosityFactorZ",
                "_RoughnessMax",
                "_RoughnessMin");
            return SaveMaterial(
                material,
                GeneratedMaterialRoot + "/M_CharInfo_outside.mat");
        }

        private static MaterialBundle ReadMaterial(MaterialSourceSpec source)
        {
            return new MaterialBundle
            {
                Normalized = ReadJson<NormalizedMaterialJson>(source.Normalized),
                Raw = ReadJson<RawMaterialJson>(source.Raw),
            };
        }

        private static void ValidateMaterialIdentity(
            MaterialBundle source,
            string expectedName,
            long expectedShaderPathId,
            int expectedRenderQueue,
            params string[] expectedKeywords)
        {
            if (source.Normalized == null || source.Raw == null ||
                source.Normalized.m_Name != expectedName ||
                source.Raw.m_Name != expectedName ||
                source.Normalized.m_Shader == null ||
                source.Normalized.m_Shader.m_PathID != expectedShaderPathId ||
                source.Raw.m_CustomRenderQueue != expectedRenderQueue)
            {
                throw new InvalidDataException(
                    $"Recovered material identity mismatch for {expectedName}.");
            }

            string[] actual = source.Raw.m_ValidKeywords ?? Array.Empty<string>();
            if (actual.Length != expectedKeywords.Length)
                throw new InvalidDataException(
                    $"Recovered keyword count mismatch for {expectedName}.");
            foreach (string keyword in expectedKeywords)
            {
                if (Array.IndexOf(actual, keyword) < 0)
                    throw new InvalidDataException(
                        $"Recovered material {expectedName} lacks keyword {keyword}.");
            }
        }

        private static void ValidateTextureReference(
            TexEnvJson environment,
            long expectedPathId,
            string label)
        {
            if (environment == null || environment.m_Texture == null ||
                environment.m_Texture.IsNull ||
                environment.m_Texture.m_PathID != expectedPathId)
            {
                throw new InvalidDataException(
                    $"Recovered texture reference mismatch for {label}.");
            }
        }

        private static Material NewMaterial(
            MaterialBundle source,
            string shaderName)
        {
            Shader shader = Shader.Find(shaderName);
            if (shader == null)
                throw new InvalidDataException($"Recovered shader is missing: {shaderName}");
            Material material = new Material(shader)
            {
                name = source.Normalized.m_Name,
                renderQueue = source.Raw.m_CustomRenderQueue,
                shaderKeywords = source.Raw.m_ValidKeywords ?? Array.Empty<string>(),
            };
            if (source.Raw.disabledShaderPasses != null)
            {
                foreach (string passName in source.Raw.disabledShaderPasses)
                    material.SetShaderPassEnabled(passName, false);
            }
            return material;
        }

        private static Material SaveMaterial(Material material, string path)
        {
            Material imported = ReplaceOrCreateAsset(material, path);
            EditorUtility.SetDirty(imported);
            return imported;
        }

        private static void SetTexture(
            Material material,
            string property,
            Texture texture,
            TexEnvJson source)
        {
            material.SetTexture(property, texture);
            material.SetTextureScale(
                property,
                new Vector2(source.m_Scale.X, source.m_Scale.Y));
            material.SetTextureOffset(
                property,
                new Vector2(source.m_Offset.X, source.m_Offset.Y));
        }

        private static void SetColor(
            Material material,
            string property,
            Color value)
        {
            material.SetColor(property, value);
        }

        private static void SetVector(
            Material material,
            string property,
            Color value)
        {
            material.SetVector(
                property,
                new Vector4(value.r, value.g, value.b, value.a));
        }

        private static void SetFloats(
            Material material,
            FloatsJson source,
            params string[] names)
        {
            foreach (string name in names)
                material.SetFloat(name, source.Get(name));
        }

        private static void BuildPrefab(
            Mesh sphereMesh,
            Mesh wallMesh,
            Mesh gridMesh,
            Material outsideMaterial,
            Material floorMaterial,
            Material wallMaterial,
            Material shadowMaterial,
            Material gridMaterial)
        {
            Mesh quad = ResolveBuiltinPrimitiveMesh(PrimitiveType.Quad, "Quad");
            Mesh plane = ResolveBuiltinPrimitiveMesh(PrimitiveType.Plane, "Plane");

            TextAsset sourceManifest =
                AssetDatabase.LoadAssetAtPath<TextAsset>(ManifestPath);
            if (sourceManifest == null)
                throw new FileNotFoundException("Missing CharInfo source manifest.", ManifestPath);
            TextAsset readySubsetOpenState =
                AssetDatabase.LoadAssetAtPath<TextAsset>(
                    ReadySubsetOpenStatePath);
            if (readySubsetOpenState == null)
            {
                throw new FileNotFoundException(
                    "Missing source-derived CharInfo ready-subset opened state.",
                    ReadySubsetOpenStatePath);
            }
            ManifestJson manifest = JsonUtility.FromJson<ManifestJson>(sourceManifest.text);
            if (manifest == null)
                throw new InvalidDataException("Could not parse CharInfo source manifest.");

            GameObject root = new GameObject("RecoveredCharInfoPresentation");
            try
            {
                EndfieldRecoveredCharInfoPresentation controller =
                    root.AddComponent<EndfieldRecoveredCharInfoPresentation>();
                GameObject content = CreateNode("ExactSourceContent", root.transform, 0);
                GameObject charInfoChar = CreateNode("CharInfoChar", content.transform, 13);
                GameObject charInfoScene =
                    CreateNode("CharInfo_Scene", charInfoChar.transform, 13);
                GameObject meshRoot = CreateNode("Mesh", charInfoScene.transform, 13);
                SetLocalTransform(
                    meshRoot.transform,
                    new Vector3(-1.9700003f, 0.0f, -1.5599998f),
                    new Quaternion(0.0f, -0.0914292f, 0.0f, 0.9958116f),
                    Vector3.one);

                MeshRenderer sphereRenderer = CreateRenderer(
                    "SphereOutside",
                    meshRoot.transform,
                    sphereMesh,
                    outsideMaterial,
                    new Vector3(2.3f, 0.0f, 1.7f),
                    Quaternion.identity,
                    new Vector3(50.0f, 50.0f, 50.0f),
                    ShadowCastingMode.Off,
                    LightProbeUsage.BlendProbes,
                    ReflectionProbeUsage.BlendProbes,
                    1u);
                MeshRenderer floorRenderer = CreateRenderer(
                    "CharFloorEffect",
                    meshRoot.transform,
                    quad,
                    floorMaterial,
                    new Vector3(1.8081535f, 0.0f, 2.0754473f),
                    new Quaternion(
                        0.15008254f,
                        0.6909958f,
                        -0.6909958f,
                        0.15008254f),
                    new Vector3(35.0f, 35.0f, 35.0f),
                    ShadowCastingMode.On,
                    LightProbeUsage.Off,
                    ReflectionProbeUsage.BlendProbes,
                    1u);
                MeshRenderer wallRenderer = CreateRenderer(
                    "GeoSphere001",
                    meshRoot.transform,
                    wallMesh,
                    wallMaterial,
                    new Vector3(2.3f, 0.0f, 1.7f),
                    new Quaternion(0.7071068f, 0.0f, 0.0f, 0.7071068f),
                    new Vector3(0.75f, 0.75f, 0.75f),
                    ShadowCastingMode.On,
                    LightProbeUsage.BlendProbes,
                    ReflectionProbeUsage.BlendProbes,
                    1u);
                MeshRenderer shadowRenderer = CreateRenderer(
                    "ShadowPlane",
                    meshRoot.transform,
                    plane,
                    shadowMaterial,
                    new Vector3(2.278f, 0.032f, 1.114f),
                    Quaternion.identity,
                    Vector3.one,
                    ShadowCastingMode.On,
                    LightProbeUsage.Off,
                    ReflectionProbeUsage.BlendProbes,
                    uint.MaxValue);

                GameObject gridDeco =
                    CreateNode("GridDeco", charInfoChar.transform, 13);
                MeshRenderer gridRenderer = CreateRenderer(
                    "Far",
                    gridDeco.transform,
                    gridMesh,
                    gridMaterial,
                    new Vector3(-10.53f, 1.4f, -13.4f),
                    new Quaternion(0.0f, 0.3007058f, 0.0f, 0.95371693f),
                    Vector3.one,
                    ShadowCastingMode.On,
                    LightProbeUsage.BlendProbes,
                    ReflectionProbeUsage.BlendProbes,
                    1u);

                controller.enableRecoveredPresentation = false;
                controller.enableReadySubsetDiagnostic = false;
                controller.enableEndminfSourceBackground = false;
                controller.enableEndminfSourceForwardOverlay = false;
                controller.sourceContent = content;
                controller.sphereOutsideRenderer = sphereRenderer;
                controller.floorRenderer = floorRenderer;
                controller.wallRenderer = wallRenderer;
                controller.shadowPlaneRenderer = shadowRenderer;
                controller.farGridRenderer = gridRenderer;
                controller.sourceManifest = sourceManifest;
                controller.settledOpenState = readySubsetOpenState;
                controller.exactSourceAssetsReady = manifest.complete &&
                    Shader.Find("Endfield/Recovered/CharInfo/HGRPLit") != null;
                controller.readinessFailure = controller.exactSourceAssetsReady
                    ? string.Empty
                    : manifest.blocking_gap_summary;
                content.SetActive(false);

                PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
            AssetDatabase.SaveAssets();
        }

        private static GameObject CreateNode(
            string name,
            Transform parent,
            int layer)
        {
            GameObject node = new GameObject(name) { layer = layer };
            node.transform.SetParent(parent, false);
            SetLocalTransform(
                node.transform,
                Vector3.zero,
                Quaternion.identity,
                Vector3.one);
            return node;
        }

        private static Mesh ResolveBuiltinPrimitiveMesh(
            PrimitiveType primitiveType,
            string expectedName)
        {
            // The original PPtrs are literally fileID 36 (unity default
            // resources), PathIDs 10210/10209. CreatePrimitive is Unity's
            // public resolver for those same built-in Mesh objects; the
            // temporary GameObject and Collider are discarded without copying
            // or recalculating the Mesh.
            GameObject temporary = GameObject.CreatePrimitive(primitiveType);
            try
            {
                MeshFilter filter = temporary.GetComponent<MeshFilter>();
                Mesh mesh = filter != null ? filter.sharedMesh : null;
                if (mesh == null || mesh.name != expectedName)
                {
                    throw new InvalidDataException(
                        $"Unity default resources did not resolve exact " +
                        $"{expectedName} mesh.");
                }
                return mesh;
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(temporary);
            }
        }

        private static MeshRenderer CreateRenderer(
            string name,
            Transform parent,
            Mesh mesh,
            Material material,
            Vector3 localPosition,
            Quaternion localRotation,
            Vector3 localScale,
            ShadowCastingMode shadowCasting,
            LightProbeUsage lightProbeUsage,
            ReflectionProbeUsage reflectionProbeUsage,
            uint renderingLayerMask)
        {
            GameObject node = CreateNode(name, parent, 13);
            SetLocalTransform(
                node.transform,
                localPosition,
                localRotation,
                localScale);
            MeshFilter filter = node.AddComponent<MeshFilter>();
            filter.sharedMesh = mesh;
            MeshRenderer renderer = node.AddComponent<MeshRenderer>();
            renderer.sharedMaterial = material;
            renderer.enabled = true;
            renderer.shadowCastingMode = shadowCasting;
            renderer.receiveShadows = true;
            renderer.motionVectorGenerationMode = MotionVectorGenerationMode.Object;
            renderer.lightProbeUsage = lightProbeUsage;
            renderer.reflectionProbeUsage = reflectionProbeUsage;
            renderer.renderingLayerMask = renderingLayerMask;
            renderer.sortingLayerID = 0;
            renderer.sortingOrder = 0;
            renderer.rendererPriority = 0;
            return renderer;
        }

        private static void SetLocalTransform(
            Transform transform,
            Vector3 position,
            Quaternion rotation,
            Vector3 scale)
        {
            transform.localPosition = position;
            transform.localRotation = rotation;
            transform.localScale = scale;
        }

        private static int BindIntoGeneratedScenes()
        {
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
            if (prefab == null)
                throw new InvalidDataException($"Missing presentation prefab: {PrefabPath}");

            SceneSetup[] previousSetup = EditorSceneManager.GetSceneManagerSetup();
            int count = 0;
            try
            {
                foreach (string scenePath in GeneratedScenePaths)
                {
                    if (AssetDatabase.LoadAssetAtPath<SceneAsset>(scenePath) == null)
                        throw new FileNotFoundException(
                            "Generated character recovery scene is missing.",
                            scenePath);

                    Scene scene = EditorSceneManager.OpenScene(
                        scenePath,
                        OpenSceneMode.Single);
                    foreach (EndfieldRecoveredCharInfoPresentation existing in
                        UnityEngine.Object.FindObjectsOfType<
                            EndfieldRecoveredCharInfoPresentation>(true))
                    {
                        if (existing != null && existing.gameObject.scene == scene)
                            UnityEngine.Object.DestroyImmediate(existing.gameObject);
                    }

                    GameObject instance = (GameObject)PrefabUtility.InstantiatePrefab(
                        prefab,
                        scene);
                    instance.name = "RecoveredCharInfoPresentation";
                    SetLocalTransform(
                        instance.transform,
                        Vector3.zero,
                        Quaternion.identity,
                        Vector3.one);
                    EndfieldRecoveredCharInfoPresentation controller =
                        instance.GetComponent<EndfieldRecoveredCharInfoPresentation>();
                    Renderer compatibilityBackdrop =
                        FindCompatibilityBackdrop(scene);
                    if (controller == null || compatibilityBackdrop == null)
                    {
                        throw new InvalidDataException(
                            $"Could not bind strict presentation selector in {scenePath}.");
                    }
                    controller.compatibilityBackdropRenderer = compatibilityBackdrop;
                    controller.enableRecoveredPresentation = false;
                    controller.enableReadySubsetDiagnostic = false;
                    controller.enableEndminfSourceBackground = false;
                    controller.enableEndminfSourceForwardOverlay = false;
                    if (controller.sourceContent != null)
                        controller.sourceContent.SetActive(false);
                    EditorUtility.SetDirty(controller);

                    EditorSceneManager.MarkSceneDirty(scene);
                    if (!EditorSceneManager.SaveScene(scene))
                        throw new IOException($"Could not save scene {scenePath}.");
                    count++;
                }
            }
            finally
            {
                if (previousSetup != null && previousSetup.Length > 0)
                    EditorSceneManager.RestoreSceneManagerSetup(previousSetup);
            }
            AssetDatabase.SaveAssets();
            return count;
        }

        private static Renderer FindCompatibilityBackdrop(Scene scene)
        {
            foreach (Renderer renderer in
                UnityEngine.Object.FindObjectsOfType<Renderer>(true))
            {
                if (renderer == null || renderer.gameObject.scene != scene)
                    continue;
                Material material = renderer.sharedMaterial;
                MeshFilter filter = renderer.GetComponent<MeshFilter>();
                bool isGeneratedReferenceBackdrop =
                    renderer.gameObject.name == "ReferenceBackdrop" &&
                    filter != null && filter.sharedMesh != null &&
                    filter.sharedMesh.name == "ReferenceBackdropQuad" &&
                    material != null &&
                    AssetDatabase.GetAssetPath(material) ==
                        "Assets/EndfieldGraphShaderLab/Generated/Characters/" +
                        "Shared/Materials/M_ReferenceBackdrop.mat";
                bool isLegacyShaderBackdrop =
                    material != null && material.shader != null &&
                    material.shader.name ==
                        "Endfield/CharacterRecovery/ReferenceBackdrop";
                if (isGeneratedReferenceBackdrop || isLegacyShaderBackdrop)
                {
                    return renderer;
                }
            }
            return null;
        }

        private static T ReplaceOrCreateAsset<T>(T rebuilt, string assetPath)
            where T : UnityEngine.Object
        {
            T existing = AssetDatabase.LoadAssetAtPath<T>(assetPath);
            UnityEngine.Object existingMain =
                AssetDatabase.LoadMainAssetAtPath(assetPath);
            if (existingMain != null && existing == null)
            {
                UnityEngine.Object.DestroyImmediate(rebuilt);
                throw new InvalidDataException(
                    $"Existing asset has wrong type: {assetPath}");
            }

            if (existing == null)
            {
                AssetDatabase.CreateAsset(rebuilt, assetPath);
                existing = rebuilt;
            }
            else
            {
                EditorUtility.CopySerialized(rebuilt, existing);
                UnityEngine.Object.DestroyImmediate(rebuilt);
                EditorUtility.SetDirty(existing);
            }
            AssetDatabase.SaveAssets();
            AssetDatabase.ImportAsset(assetPath, ImportAssetOptions.ForceUpdate);
            return AssetDatabase.LoadAssetAtPath<T>(assetPath);
        }

        private static T ReadJson<T>(SourceFileSpec source)
        {
            byte[] data = ReadAndValidateBytes(source);
            T parsed = JsonUtility.FromJson<T>(Encoding.UTF8.GetString(data));
            if (parsed == null)
                throw new InvalidDataException($"Could not parse source JSON: {source.Path}");
            return parsed;
        }

        private static byte[] ReadAndValidateBytes(SourceFileSpec source)
        {
            string fullPath = ToFullPath(source.Path);
            if (!File.Exists(fullPath))
                throw new FileNotFoundException("Recovered source file is missing.", fullPath);
            byte[] data = File.ReadAllBytes(fullPath);
            string actualHash = ComputeSha256(data);
            if (!string.Equals(
                    actualHash,
                    source.Sha256,
                    StringComparison.OrdinalIgnoreCase))
            {
                throw new InvalidDataException(
                    $"Recovered source hash mismatch for {source.Path}: " +
                    $"{actualHash} != {source.Sha256}.");
            }
            return data;
        }

        private static string ComputeSha256(byte[] data)
        {
            using (SHA256 sha = SHA256.Create())
            {
                return BitConverter.ToString(sha.ComputeHash(data))
                    .Replace("-", string.Empty)
                    .ToLowerInvariant();
            }
        }

        private static string ToFullPath(string assetPath)
        {
            string projectRoot = Path.GetFullPath(
                Path.Combine(Application.dataPath, ".."));
            return Path.Combine(
                projectRoot,
                assetPath.Replace('/', Path.DirectorySeparatorChar));
        }

        private static void EnsureGeneratedFolders()
        {
            Directory.CreateDirectory(ToFullPath(GeneratedMeshRoot));
            Directory.CreateDirectory(ToFullPath(GeneratedTextureRoot));
            Directory.CreateDirectory(ToFullPath(GeneratedMaterialRoot));
        }

        private static List<Vector2> ToVector2(float[] values)
        {
            if (values == null || values.Length % 2 != 0)
                throw new InvalidDataException("Vector2 source array is malformed.");
            List<Vector2> result = new List<Vector2>(values.Length / 2);
            for (int index = 0; index < values.Length; index += 2)
                result.Add(new Vector2(values[index], values[index + 1]));
            return result;
        }

        private static List<Vector3> ToVector3(float[] values)
        {
            if (values == null || values.Length % 3 != 0)
                throw new InvalidDataException("Vector3 source array is malformed.");
            List<Vector3> result = new List<Vector3>(values.Length / 3);
            for (int index = 0; index < values.Length; index += 3)
            {
                result.Add(new Vector3(
                    values[index],
                    values[index + 1],
                    values[index + 2]));
            }
            return result;
        }

        private static List<Vector4> ToVector4(float[] values)
        {
            if (values == null || values.Length % 4 != 0)
                throw new InvalidDataException("Vector4 source array is malformed.");
            List<Vector4> result = new List<Vector4>(values.Length / 4);
            for (int index = 0; index < values.Length; index += 4)
            {
                result.Add(new Vector4(
                    values[index],
                    values[index + 1],
                    values[index + 2],
                    values[index + 3]));
            }
            return result;
        }

        private static Vector3 ToVector3(Vector3Json value)
        {
            return new Vector3(value.X, value.Y, value.Z);
        }

        private sealed class SourceFileSpec
        {
            public SourceFileSpec(string path, string sha256)
            {
                Path = path;
                Sha256 = sha256;
            }

            public string Path { get; }
            public string Sha256 { get; }
        }

        private sealed class TextureSourceSpec
        {
            public TextureSourceSpec(
                string path,
                string sha256,
                string name,
                int width,
                int height,
                int mipCount,
                TextureFormat format,
                bool linear)
            {
                File = new SourceFileSpec(path, sha256);
                Name = name;
                Width = width;
                Height = height;
                MipCount = mipCount;
                Format = format;
                Linear = linear;
            }

            public SourceFileSpec File { get; }
            public string Name { get; }
            public int Width { get; }
            public int Height { get; }
            public int MipCount { get; }
            public TextureFormat Format { get; }
            public bool Linear { get; }
        }

        private sealed class MaterialSourceSpec
        {
            public MaterialSourceSpec(
                string normalizedPath,
                string normalizedSha256,
                string rawPath,
                string rawSha256)
            {
                Normalized = new SourceFileSpec(normalizedPath, normalizedSha256);
                Raw = new SourceFileSpec(rawPath, rawSha256);
            }

            public SourceFileSpec Normalized { get; }
            public SourceFileSpec Raw { get; }
        }

        private sealed class MaterialBundle
        {
            public NormalizedMaterialJson Normalized;
            public RawMaterialJson Raw;
        }

        [Serializable]
        private sealed class ManifestJson
        {
            public bool complete;
            public string blocking_gap_summary;
        }

        [Serializable]
        private sealed class MeshJson
        {
            public SubMeshJson[] m_SubMeshes;
            public int m_VertexCount;
            public float[] m_Vertices;
            public float[] m_Normals;
            public float[] m_Colors;
            public float[] m_UV0;
            public float[] m_UV1;
            public float[] m_UV2;
            public float[] m_Tangents;
            public int[] m_Indices;
            public string m_Name;
        }

        [Serializable]
        private sealed class SubMeshJson
        {
            public int firstByte;
            public int indexCount;
            public string topology;
            public int baseVertex;
            public int firstVertex;
            public int vertexCount;
            public AabbJson localAABB;
        }

        [Serializable]
        private sealed class AabbJson
        {
            public Vector3Json m_Center;
            public Vector3Json m_Extent;
        }

        [Serializable]
        private sealed class Vector3Json
        {
            public float X;
            public float Y;
            public float Z;
        }

        [Serializable]
        private sealed class Vector2Json
        {
            public float X;
            public float Y;
        }

        [Serializable]
        private sealed class NormalizedMaterialJson
        {
            public PPtrJson m_Shader;
            public SavedPropertiesJson m_SavedProperties;
            public string m_Name;
        }

        [Serializable]
        private sealed class RawMaterialJson
        {
            public string m_Name;
            public string[] m_ValidKeywords;
            public string[] m_InvalidKeywords;
            public int m_CustomRenderQueue;
            public string[] disabledShaderPasses;
        }

        [Serializable]
        private sealed class SavedPropertiesJson
        {
            public TexEnvsJson m_TexEnvs;
            public FloatsJson m_Floats;
            public ColorsJson m_Colors;
        }

        [Serializable]
        private sealed class TexEnvsJson
        {
            public TexEnvJson _MainTex;
            public TexEnvJson _BaseTex;
            public TexEnvJson _BlendSDFTex;
            public TexEnvJson _MROMap;
        }

        [Serializable]
        private sealed class TexEnvJson
        {
            public PPtrJson m_Texture;
            public Vector2Json m_Scale;
            public Vector2Json m_Offset;
        }

        [Serializable]
        private sealed class PPtrJson
        {
            public int m_FileID;
            public long m_PathID;
            public bool IsNull;
        }

        [Serializable]
        private sealed class ColorsJson
        {
            public Color _TintColor;
            public Color _MainTexUVSpeed;
            public Color _BlendTint;
            public Color _ShadowColor;
            public Color _CapsuleAoColor;
            public Color _BaseColor;
        }

        [Serializable]
        private sealed class FloatsJson
        {
            public float _APPLY_COLOR_BANDING_DITHER;
            public float _AlphaClipThreshold;
            public float _AlphaDstBlend;
            public float _AlphaSrcBlend;
            public float _CircleFade;
            public float _CircleFadeDistance;
            public float _CircleFadeSmoothness;
            public float _CullMode;
            public float _DisableCharacterSelfShadow;
            public float _DisableSceneShadow;
            public float _DisableVertColor;
            public float _DstBlend;
            public float _EnableSubsurface;
            public float _ExpIntensity;
            public float _ExpThreshold;
            public float _ForceMoveToFarPlane;
            public float _GridLineWidth;
            public float _IgnorePostExposure;
            public float _InParticle;
            public float _MainTexUVRotate;
            public float _MainUVSet;
            public float _Metallic;
            public float _NearCameraFadeDistanceEnd;
            public float _NearCameraFadeDistanceEnd2;
            public float _NearCameraFadeDistanceStart;
            public float _NearCameraFadeDistanceStart2;
            public float _NormalScale;
            public float _OcclusionStrength;
            public float _PorosityFactorX;
            public float _PorosityFactorY;
            public float _PorosityFactorZ;
            public float _ProcedureAlpha;
            public float _RoughnessMax;
            public float _RoughnessMin;
            public float _SDFSwitchEnd;
            public float _SDFSwitchStart;
            public float _SrcBlend;
            public float _SurfaceType;
            public float _TintColorAlpha;
            public float _TintColorIntensity;
            public float _UseAlphaTest;
            public float _UseBlend;
            public float _UseGridLine;
            public float _UseMainTexAsAlpha;
            public float _UseNearCameraFade;
            public float _ZTest;
            public float _ZWrite;
            public float _ZWriteMode;

            public float Get(string name)
            {
                switch (name)
                {
                    case "_APPLY_COLOR_BANDING_DITHER": return _APPLY_COLOR_BANDING_DITHER;
                    case "_AlphaClipThreshold": return _AlphaClipThreshold;
                    case "_AlphaDstBlend": return _AlphaDstBlend;
                    case "_AlphaSrcBlend": return _AlphaSrcBlend;
                    case "_CircleFade": return _CircleFade;
                    case "_CircleFadeDistance": return _CircleFadeDistance;
                    case "_CircleFadeSmoothness": return _CircleFadeSmoothness;
                    case "_CullMode": return _CullMode;
                    case "_DisableCharacterSelfShadow": return _DisableCharacterSelfShadow;
                    case "_DisableSceneShadow": return _DisableSceneShadow;
                    case "_DisableVertColor": return _DisableVertColor;
                    case "_DstBlend": return _DstBlend;
                    case "_EnableSubsurface": return _EnableSubsurface;
                    case "_ExpIntensity": return _ExpIntensity;
                    case "_ExpThreshold": return _ExpThreshold;
                    case "_ForceMoveToFarPlane": return _ForceMoveToFarPlane;
                    case "_GridLineWidth": return _GridLineWidth;
                    case "_IgnorePostExposure": return _IgnorePostExposure;
                    case "_InParticle": return _InParticle;
                    case "_MainTexUVRotate": return _MainTexUVRotate;
                    case "_MainUVSet": return _MainUVSet;
                    case "_Metallic": return _Metallic;
                    case "_NearCameraFadeDistanceEnd": return _NearCameraFadeDistanceEnd;
                    case "_NearCameraFadeDistanceEnd2": return _NearCameraFadeDistanceEnd2;
                    case "_NearCameraFadeDistanceStart": return _NearCameraFadeDistanceStart;
                    case "_NearCameraFadeDistanceStart2": return _NearCameraFadeDistanceStart2;
                    case "_NormalScale": return _NormalScale;
                    case "_OcclusionStrength": return _OcclusionStrength;
                    case "_PorosityFactorX": return _PorosityFactorX;
                    case "_PorosityFactorY": return _PorosityFactorY;
                    case "_PorosityFactorZ": return _PorosityFactorZ;
                    case "_ProcedureAlpha": return _ProcedureAlpha;
                    case "_RoughnessMax": return _RoughnessMax;
                    case "_RoughnessMin": return _RoughnessMin;
                    case "_SDFSwitchEnd": return _SDFSwitchEnd;
                    case "_SDFSwitchStart": return _SDFSwitchStart;
                    case "_SrcBlend": return _SrcBlend;
                    case "_SurfaceType": return _SurfaceType;
                    case "_TintColorAlpha": return _TintColorAlpha;
                    case "_TintColorIntensity": return _TintColorIntensity;
                    case "_UseAlphaTest": return _UseAlphaTest;
                    case "_UseBlend": return _UseBlend;
                    case "_UseGridLine": return _UseGridLine;
                    case "_UseMainTexAsAlpha": return _UseMainTexAsAlpha;
                    case "_UseNearCameraFade": return _UseNearCameraFade;
                    case "_ZTest": return _ZTest;
                    case "_ZWrite": return _ZWrite;
                    case "_ZWriteMode": return _ZWriteMode;
                    default:
                        throw new InvalidDataException(
                            $"Unknown recovered material float field: {name}");
                }
            }
        }
    }
}
