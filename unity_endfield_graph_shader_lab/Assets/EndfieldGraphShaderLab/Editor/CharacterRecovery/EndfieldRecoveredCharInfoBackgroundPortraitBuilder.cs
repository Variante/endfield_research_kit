using System;
using System.IO;
using System.Security.Cryptography;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace EndfieldGraphShaderLabEditor
{
    using EndfieldGraphShaderLab;

    /// <summary>
    /// Imports and binds the original-data CharInfo overview portrait route.
    /// No placement or color value is fitted to a screenshot: the texture,
    /// padded sprite rectangle, prefab transform, overview camera transform,
    /// settled animation alpha, and material depth equation are source-owned.
    /// </summary>
    public static class EndfieldRecoveredCharInfoBackgroundPortraitBuilder
    {
        public const string GeneratedRoot =
            "Assets/EndfieldGraphShaderLab/Generated/CharInfoBackgroundPortrait";
        public const string OriginalDataRoot =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoBackgroundPortrait";
        public const string SourceManifestPath = OriginalDataRoot + "/source_manifest.json";

        private const string TextureRoot = GeneratedRoot + "/Textures";
        private const string MaterialRoot = GeneratedRoot + "/Materials";
        private const string MeshRoot = GeneratedRoot + "/Meshes";
        private const string WulfaTextureAssetPath =
            TextureRoot + "/bg_charinfo_chr_0028_wulfa.png";
        private const string ZhuangfyTextureAssetPath =
            TextureRoot + "/bg_charinfo_chr_0030_zhuangfy.png";
        private const string MaterialAssetPath =
            MaterialRoot + "/M_RecoveredCharInfoBackgroundPortrait.mat";
        private const string WulfaMeshAssetPath =
            MeshRoot + "/RecoveredCharInfoBackgroundPortraitWulfaTightQuad.asset";
        private const string ZhuangfyMeshAssetPath =
            MeshRoot + "/RecoveredCharInfoBackgroundPortraitZhuangfyTightQuad.asset";
        private const string SceneObjectName =
            "RecoveredCharInfoBackgroundPortrait";
        private const string ViewerScenePath =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Scenes/CharacterRecoveryViewer.unity";
        private const string FastViewerScenePath =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Scenes/CharacterRenderStyleFast.unity";

        private const string WulfaSourceRelativePath =
            "export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/Texture2D/" +
            "bg_charinfo_chr_0028_wulfa_p98B763E6C1636E1F.png";
        private const string ZhuangfySourceRelativePath =
            "export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/Texture2D/" +
            "bg_charinfo_chr_0030_zhuangfy_p854C77D240F142E7.png";
        private const string WulfaSourceSha256 =
            "426F6391011A58F88F2C51CBF1809F6068B07F10A17A08336528BDC3C20D9225";
        private const string ZhuangfySourceSha256 =
            "2B214668CA5B48EF6D9ECBEE6E3DFFA50C9E7536D47C65D5272DA673CF472A77";
        private const float SourceLogicalSpriteSize = 1022.0f;
        private const float SourceTextureSize = 1024.0f;
        private static readonly Rect WulfaSourceTextureRect =
            new Rect(211.07613f, 55.051315f, 605.87256f, 904.87256f);
        private static readonly Rect ZhuangfySourceTextureRect =
            new Rect(209.01112f, 98.051315f, 675.9128f, 923.94867f);

        [MenuItem("Endfield/Character Recovery Lab/Build CharInfo Background Portrait Recovery")]
        public static void BuildAndBind()
        {
            EnsureSourceAssets();
            int boundScenes = 0;
            foreach (string scenePath in new[] { ViewerScenePath, FastViewerScenePath })
            {
                if (!File.Exists(AssetPathToFullPath(scenePath)))
                    continue;

                Scene scene = EditorSceneManager.OpenScene(scenePath, OpenSceneMode.Single);
                Camera camera = Camera.main ?? UnityEngine.Object.FindObjectOfType<Camera>(true);
                Transform actor = FindActiveActor(out string actorName);
                if (camera == null)
                {
                    throw new InvalidOperationException(
                        $"The canonical scene has no camera for the recovered CharInfo portrait: {scenePath}");
                }
                if (actor == null)
                {
                    throw new InvalidOperationException(
                        $"The canonical scene has no active Wulfa or Zhuangfy actor root: {scenePath}");
                }

                EnsureAndBind(camera, actorName, actor);
                EditorSceneManager.MarkSceneDirty(scene);
                if (!EditorSceneManager.SaveScene(scene, scenePath, false))
                    throw new IOException($"Could not save recovered portrait binding: {scenePath}");
                boundScenes++;
            }
            if (boundScenes == 0)
            {
                throw new FileNotFoundException(
                    "No canonical character-recovery scene exists. Build the shared viewer first.",
                    ViewerScenePath);
            }
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            VerifyStaticRecovery();
            Debug.Log(
                $"Recovered CharInfo background portrait built and bound from original data: scenes={boundScenes}.");
        }

        [MenuItem("Endfield/Character Recovery Lab/Verify CharInfo Background Portrait Recovery")]
        public static void VerifyStaticRecovery()
        {
            PortraitAssets assets = EnsureSourceAssets();
            Require(
                Sha256(AssetPathToFullPath(WulfaTextureAssetPath)) == WulfaSourceSha256,
                "Generated Wulfa portrait texture hash drifted.");
            Require(
                Sha256(AssetPathToFullPath(ZhuangfyTextureAssetPath)) == ZhuangfySourceSha256,
                "Generated Zhuangfy portrait texture hash drifted.");
            Require(assets.wulfaTexture != null, "Wulfa portrait Texture2D is missing.");
            Require(assets.zhuangfyTexture != null, "Zhuangfy portrait Texture2D is missing.");
            Require(
                assets.wulfaTexture.width == 1024 && assets.wulfaTexture.height == 1024,
                "Wulfa portrait Texture2D is not 1024 square.");
            Require(
                assets.zhuangfyTexture.width == 1024 && assets.zhuangfyTexture.height == 1024,
                "Zhuangfy portrait Texture2D is not 1024 square.");
            Require(
                assets.material != null &&
                assets.material.shader != null &&
                assets.material.shader.name ==
                    EndfieldRecoveredCharInfoBackgroundPortrait.ShaderName,
                "Recovered portrait material is not bound to the source-equation shader.");
            VerifySimpleSpriteMesh(
                assets.wulfaMesh,
                WulfaSourceTextureRect,
                "Wulfa");
            VerifySimpleSpriteMesh(
                assets.zhuangfyMesh,
                ZhuangfySourceTextureRect,
                "Zhuangfy");

            TextureImporter wulfaImporter =
                AssetImporter.GetAtPath(WulfaTextureAssetPath) as TextureImporter;
            TextureImporter zhuangfyImporter =
                AssetImporter.GetAtPath(ZhuangfyTextureAssetPath) as TextureImporter;
            VerifyTextureImporter(wulfaImporter, "Wulfa");
            VerifyTextureImporter(zhuangfyImporter, "Zhuangfy");

            TextAsset manifest = AssetDatabase.LoadAssetAtPath<TextAsset>(SourceManifestPath);
            Require(
                manifest != null &&
                manifest.text.Contains(
                    "endfield.charinfo.background-portrait.original-data.v1"),
                "Recovered CharInfo portrait source manifest is missing or has the wrong schema.");
            Require(
                manifest.text.Contains("\"runtime_atlas_compatible\": false") &&
                manifest.text.Contains(
                    "\"world_ui_sorting_criteria\": [\"CommonTransparent\", \"RendererPriority\"]") &&
                manifest.text.Contains(
                    "HGRenderPathBase publishes the 720-byte buffer as _UIRenderingConstants"),
                "Recovered CharInfo portrait runtime UI closure evidence is missing or stale.");

            Debug.Log(
                "Recovered CharInfo background portrait static verification passed: " +
                "two exact Texture2D hashes, actor-specific GenerateSimpleSprite " +
                "tight quads within the logical 1022-square sprite rect, " +
                "runtime-atlas incompatibility above the retail 512-pixel limit, " +
                "world-UI CommonTransparent/RendererPriority sorting evidence, " +
                "900x900 card, settled alpha 90/255, and exact scene-depth " +
                "comparison equation are bound.");
        }

        public static EndfieldRecoveredCharInfoBackgroundPortrait EnsureAndBind(
            Camera camera,
            string actorName,
            Transform actorRoot)
        {
            if (camera == null)
                throw new ArgumentNullException(nameof(camera));
            if (actorRoot == null)
                throw new ArgumentNullException(nameof(actorRoot));

            PortraitAssets assets = EnsureSourceAssets();
            Scene scene = camera.gameObject.scene;
            GameObject portraitObject = FindScenePortraitObject(scene);
            if (portraitObject == null)
            {
                portraitObject = new GameObject(SceneObjectName);
                if (scene.IsValid())
                    SceneManager.MoveGameObjectToScene(portraitObject, scene);
            }
            portraitObject.layer = EndfieldRecoveredCharInfoBackgroundPortrait.SourceUiLayer;

            MeshFilter filter = EnsureComponent<MeshFilter>(portraitObject);
            filter.sharedMesh = string.Equals(
                actorName,
                "Zhuangfy",
                StringComparison.OrdinalIgnoreCase)
                ? assets.zhuangfyMesh
                : assets.wulfaMesh;
            MeshRenderer renderer = EnsureComponent<MeshRenderer>(portraitObject);
            renderer.sharedMaterial = assets.material;
            renderer.shadowCastingMode = ShadowCastingMode.Off;
            renderer.receiveShadows = false;
            renderer.lightProbeUsage = LightProbeUsage.Off;
            renderer.reflectionProbeUsage = ReflectionProbeUsage.Off;
            renderer.motionVectorGenerationMode = MotionVectorGenerationMode.ForceNoMotion;
            renderer.sortingLayerID = 0;
            renderer.sortingOrder = 0;

            EndfieldRecoveredCharInfoBackgroundPortrait component =
                EnsureComponent<EndfieldRecoveredCharInfoBackgroundPortrait>(portraitObject);
            component.portraitRenderer = renderer;
            component.portraitMeshFilter = filter;
            component.wulfaMesh = assets.wulfaMesh;
            component.zhuangfyMesh = assets.zhuangfyMesh;
            component.wulfaTexture = assets.wulfaTexture;
            component.zhuangfyTexture = assets.zhuangfyTexture;
            component.sourceManifest = assets.sourceManifest;
            component.enableRecoveredPortrait = false;
            component.ConfigureActor(actorRoot, actorName);

            EditorUtility.SetDirty(filter);
            EditorUtility.SetDirty(renderer);
            EditorUtility.SetDirty(component);
            EditorUtility.SetDirty(portraitObject);
            return component;
        }

        private static PortraitAssets EnsureSourceAssets()
        {
            EnsureAssetFolder(GeneratedRoot);
            EnsureAssetFolder(TextureRoot);
            EnsureAssetFolder(MaterialRoot);
            EnsureAssetFolder(MeshRoot);

            string projectRoot = Directory.GetCurrentDirectory();
            string repositoryRoot = Path.GetFullPath(Path.Combine(projectRoot, ".."));
            string wulfaSource = Path.Combine(
                repositoryRoot,
                WulfaSourceRelativePath.Replace('/', Path.DirectorySeparatorChar));
            string zhuangfySource = Path.Combine(
                repositoryRoot,
                ZhuangfySourceRelativePath.Replace('/', Path.DirectorySeparatorChar));

            CopyVerifiedSource(
                wulfaSource,
                WulfaTextureAssetPath,
                WulfaSourceSha256);
            CopyVerifiedSource(
                zhuangfySource,
                ZhuangfyTextureAssetPath,
                ZhuangfySourceSha256);

            Texture2D wulfa = ImportPortraitTexture(WulfaTextureAssetPath);
            Texture2D zhuangfy = ImportPortraitTexture(ZhuangfyTextureAssetPath);
            Material material = EnsureMaterial();
            Mesh wulfaMesh = EnsureSimpleSpriteMesh(
                WulfaMeshAssetPath,
                "RecoveredCharInfoBackgroundPortraitWulfaTightQuad",
                WulfaSourceTextureRect);
            Mesh zhuangfyMesh = EnsureSimpleSpriteMesh(
                ZhuangfyMeshAssetPath,
                "RecoveredCharInfoBackgroundPortraitZhuangfyTightQuad",
                ZhuangfySourceTextureRect);
            TextAsset manifest = AssetDatabase.LoadAssetAtPath<TextAsset>(SourceManifestPath);
            if (manifest == null)
                throw new FileNotFoundException(
                    "Recovered CharInfo portrait source manifest is missing.",
                    SourceManifestPath);

            return new PortraitAssets
            {
                wulfaTexture = wulfa,
                zhuangfyTexture = zhuangfy,
                material = material,
                wulfaMesh = wulfaMesh,
                zhuangfyMesh = zhuangfyMesh,
                sourceManifest = manifest,
            };
        }

        private static void CopyVerifiedSource(
            string sourcePath,
            string destinationAssetPath,
            string expectedSha256)
        {
            if (!File.Exists(sourcePath))
                throw new FileNotFoundException(
                    "Original CharInfo background portrait source is missing.",
                    sourcePath);
            string actualSourceHash = Sha256(sourcePath);
            if (!string.Equals(
                actualSourceHash,
                expectedSha256,
                StringComparison.OrdinalIgnoreCase))
            {
                throw new InvalidDataException(
                    $"Original CharInfo portrait hash mismatch: {sourcePath}; " +
                    $"expected={expectedSha256}, actual={actualSourceHash}.");
            }

            string destinationPath = AssetPathToFullPath(destinationAssetPath);
            Directory.CreateDirectory(Path.GetDirectoryName(destinationPath) ?? ".");
            bool copy = !File.Exists(destinationPath) ||
                        !string.Equals(
                            Sha256(destinationPath),
                            expectedSha256,
                            StringComparison.OrdinalIgnoreCase);
            if (copy)
            {
                File.Copy(sourcePath, destinationPath, true);
                AssetDatabase.ImportAsset(
                    destinationAssetPath,
                    ImportAssetOptions.ForceSynchronousImport |
                    ImportAssetOptions.ForceUpdate);
            }
        }

        private static Texture2D ImportPortraitTexture(string assetPath)
        {
            AssetDatabase.ImportAsset(
                assetPath,
                ImportAssetOptions.ForceSynchronousImport);
            TextureImporter importer = AssetImporter.GetAtPath(assetPath) as TextureImporter;
            if (importer == null)
                throw new InvalidDataException($"No TextureImporter for {assetPath}.");

            bool changed = false;
            if (importer.textureType != TextureImporterType.Default)
            {
                importer.textureType = TextureImporterType.Default;
                changed = true;
            }
            if (importer.textureShape != TextureImporterShape.Texture2D)
            {
                importer.textureShape = TextureImporterShape.Texture2D;
                changed = true;
            }
            if (!importer.sRGBTexture)
            {
                importer.sRGBTexture = true;
                changed = true;
            }
            if (importer.alphaSource != TextureImporterAlphaSource.FromInput)
            {
                importer.alphaSource = TextureImporterAlphaSource.FromInput;
                changed = true;
            }
            if (importer.alphaIsTransparency)
            {
                importer.alphaIsTransparency = false;
                changed = true;
            }
            if (importer.mipmapEnabled)
            {
                importer.mipmapEnabled = false;
                changed = true;
            }
            if (importer.npotScale != TextureImporterNPOTScale.None)
            {
                importer.npotScale = TextureImporterNPOTScale.None;
                changed = true;
            }
            if (importer.filterMode != FilterMode.Bilinear)
            {
                importer.filterMode = FilterMode.Bilinear;
                changed = true;
            }
            if (importer.wrapMode != TextureWrapMode.Clamp)
            {
                importer.wrapMode = TextureWrapMode.Clamp;
                changed = true;
            }
            if (importer.textureCompression != TextureImporterCompression.Uncompressed)
            {
                importer.textureCompression = TextureImporterCompression.Uncompressed;
                changed = true;
            }
            if (importer.maxTextureSize != 1024)
            {
                importer.maxTextureSize = 1024;
                changed = true;
            }
            if (changed)
                importer.SaveAndReimport();

            Texture2D texture = AssetDatabase.LoadAssetAtPath<Texture2D>(assetPath);
            if (texture == null)
                throw new InvalidDataException($"Could not import portrait texture {assetPath}.");
            return texture;
        }

        private static Material EnsureMaterial()
        {
            Shader shader = Shader.Find(
                EndfieldRecoveredCharInfoBackgroundPortrait.ShaderName);
            if (shader == null)
            {
                throw new InvalidOperationException(
                    "Recovered CharInfo portrait shader is unavailable: " +
                    EndfieldRecoveredCharInfoBackgroundPortrait.ShaderName);
            }

            Material material = AssetDatabase.LoadAssetAtPath<Material>(MaterialAssetPath);
            if (material == null)
            {
                material = new Material(shader)
                {
                    name = "M_RecoveredCharInfoBackgroundPortrait",
                };
                AssetDatabase.CreateAsset(material, MaterialAssetPath);
            }
            material.shader = shader;
            material.SetColor(
                "_TintColor",
                new Color(
                    1.0f,
                    1.0f,
                    1.0f,
                    EndfieldRecoveredCharInfoBackgroundPortrait.SettledAnimationAlpha));
            material.SetFloat(
                "_DepthOffset",
                EndfieldRecoveredCharInfoBackgroundPortrait.SourceDepthOffset);
            material.renderQueue = 3000;
            EditorUtility.SetDirty(material);
            return material;
        }

        private static Mesh EnsureSimpleSpriteMesh(
            string assetPath,
            string meshName,
            Rect textureRect)
        {
            Mesh mesh = AssetDatabase.LoadAssetAtPath<Mesh>(assetPath);
            if (mesh == null)
            {
                mesh = new Mesh
                {
                    name = meshName,
                };
                AssetDatabase.CreateAsset(mesh, assetPath);
            }

            float left = -0.5f + textureRect.xMin / SourceLogicalSpriteSize;
            float bottom = -0.5f + textureRect.yMin / SourceLogicalSpriteSize;
            float right = -0.5f + textureRect.xMax / SourceLogicalSpriteSize;
            float top = -0.5f + textureRect.yMax / SourceLogicalSpriteSize;
            float uMin = textureRect.xMin / SourceTextureSize;
            float vMin = textureRect.yMin / SourceTextureSize;
            float uMax = textureRect.xMax / SourceTextureSize;
            float vMax = textureRect.yMax / SourceTextureSize;

            mesh.name = meshName;
            mesh.Clear();
            mesh.vertices = new[]
            {
                new Vector3(left, bottom, 0.0f),
                new Vector3(right, bottom, 0.0f),
                new Vector3(right, top, 0.0f),
                new Vector3(left, top, 0.0f),
            };
            mesh.uv = new[]
            {
                new Vector2(uMin, vMax),
                new Vector2(uMax, vMax),
                new Vector2(uMax, vMin),
                new Vector2(uMin, vMin),
            };
            mesh.triangles = new[] { 0, 2, 1, 0, 3, 2 };
            mesh.RecalculateBounds();
            mesh.UploadMeshData(false);
            EditorUtility.SetDirty(mesh);
            return mesh;
        }

        private static void VerifySimpleSpriteMesh(
            Mesh mesh,
            Rect textureRect,
            string actor)
        {
            Require(
                mesh != null && mesh.vertexCount == 4,
                $"Recovered {actor} simple-sprite quad is missing or malformed.");

            float left = -0.5f + textureRect.xMin / SourceLogicalSpriteSize;
            float bottom = -0.5f + textureRect.yMin / SourceLogicalSpriteSize;
            float right = -0.5f + textureRect.xMax / SourceLogicalSpriteSize;
            float top = -0.5f + textureRect.yMax / SourceLogicalSpriteSize;
            Vector3[] expectedVertices =
            {
                new Vector3(left, bottom, 0.0f),
                new Vector3(right, bottom, 0.0f),
                new Vector3(right, top, 0.0f),
                new Vector3(left, top, 0.0f),
            };
            Vector2[] expectedUv =
            {
                new Vector2(textureRect.xMin / SourceTextureSize, textureRect.yMax / SourceTextureSize),
                new Vector2(textureRect.xMax / SourceTextureSize, textureRect.yMax / SourceTextureSize),
                new Vector2(textureRect.xMax / SourceTextureSize, textureRect.yMin / SourceTextureSize),
                new Vector2(textureRect.xMin / SourceTextureSize, textureRect.yMin / SourceTextureSize),
            };

            Vector3[] vertices = mesh.vertices;
            Vector2[] uv = mesh.uv;
            Require(
                vertices.Length == expectedVertices.Length && uv.Length == expectedUv.Length,
                $"Recovered {actor} simple-sprite vertex stream is incomplete.");
            for (int i = 0; i < expectedVertices.Length; i++)
            {
                Require(
                    Vector3.SqrMagnitude(vertices[i] - expectedVertices[i]) < 1e-12f,
                    $"Recovered {actor} simple-sprite vertex {i} drifted.");
                Require(
                    Vector2.SqrMagnitude(uv[i] - expectedUv[i]) < 1e-12f,
                    $"Recovered {actor} simple-sprite UV {i} drifted.");
            }

            int[] triangles = mesh.triangles;
            int[] expectedTriangles = { 0, 2, 1, 0, 3, 2 };
            Require(
                triangles.Length == expectedTriangles.Length,
                $"Recovered {actor} simple-sprite index stream is incomplete.");
            for (int i = 0; i < expectedTriangles.Length; i++)
            {
                Require(
                    triangles[i] == expectedTriangles[i],
                    $"Recovered {actor} simple-sprite index {i} drifted.");
            }
        }

        private static GameObject FindScenePortraitObject(Scene scene)
        {
            EndfieldRecoveredCharInfoBackgroundPortrait[] components =
                Resources.FindObjectsOfTypeAll<EndfieldRecoveredCharInfoBackgroundPortrait>();
            for (int i = 0; i < components.Length; i++)
            {
                EndfieldRecoveredCharInfoBackgroundPortrait component = components[i];
                if (component != null &&
                    component.gameObject.scene.IsValid() &&
                    component.gameObject.scene == scene)
                {
                    return component.gameObject;
                }
            }
            return null;
        }

        private static Transform FindActiveActor(out string actorName)
        {
            Transform[] transforms = Resources.FindObjectsOfTypeAll<Transform>();
            for (int i = 0; i < transforms.Length; i++)
            {
                Transform transform = transforms[i];
                if (transform == null ||
                    !transform.gameObject.scene.IsValid() ||
                    !transform.gameObject.activeInHierarchy)
                {
                    continue;
                }
                if (string.Equals(transform.name, "Wulfa", StringComparison.OrdinalIgnoreCase))
                {
                    actorName = "Wulfa";
                    return transform;
                }
                if (string.Equals(transform.name, "Zhuangfy", StringComparison.OrdinalIgnoreCase))
                {
                    actorName = "Zhuangfy";
                    return transform;
                }
            }
            actorName = null;
            return null;
        }

        private static void VerifyTextureImporter(TextureImporter importer, string actor)
        {
            Require(importer != null, $"{actor} portrait importer is missing.");
            Require(importer.textureType == TextureImporterType.Default, $"{actor} texture type drifted.");
            Require(importer.sRGBTexture, $"{actor} portrait must sample through hardware sRGB decode.");
            Require(importer.alphaSource == TextureImporterAlphaSource.FromInput, $"{actor} alpha source drifted.");
            Require(!importer.alphaIsTransparency, $"{actor} RGB must not be rewritten by alpha dilation.");
            Require(!importer.mipmapEnabled, $"{actor} original source has one mip.");
            Require(importer.filterMode == FilterMode.Bilinear, $"{actor} original filter mode is bilinear.");
            Require(importer.wrapMode == TextureWrapMode.Clamp, $"{actor} original wrap mode is clamp.");
            Require(
                importer.textureCompression == TextureImporterCompression.Uncompressed,
                $"{actor} decoded BC7 pixels must not be recompressed.");
        }

        private static void EnsureAssetFolder(string assetPath)
        {
            string[] parts = assetPath.Split('/');
            string current = parts[0];
            for (int i = 1; i < parts.Length; i++)
            {
                string next = current + "/" + parts[i];
                if (!AssetDatabase.IsValidFolder(next))
                    AssetDatabase.CreateFolder(current, parts[i]);
                current = next;
            }
        }

        private static T EnsureComponent<T>(GameObject gameObject) where T : Component
        {
            T component = gameObject.GetComponent<T>();
            return component != null ? component : gameObject.AddComponent<T>();
        }

        private static string AssetPathToFullPath(string assetPath)
        {
            return Path.GetFullPath(Path.Combine(Directory.GetCurrentDirectory(), assetPath));
        }

        private static string Sha256(string path)
        {
            using (FileStream stream = File.OpenRead(path))
            using (SHA256 sha = SHA256.Create())
                return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", string.Empty);
        }

        private static void Require(bool condition, string message)
        {
            if (!condition)
                throw new InvalidDataException(message);
        }

        private sealed class PortraitAssets
        {
            public Texture2D wulfaTexture;
            public Texture2D zhuangfyTexture;
            public Material material;
            public Mesh wulfaMesh;
            public Mesh zhuangfyMesh;
            public TextAsset sourceManifest;
        }
    }
}
