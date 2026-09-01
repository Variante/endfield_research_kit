using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEngine;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Bakes installed-game CharInfo records into player-build-safe assets.
    /// Camera, portrait geometry, portrait pixels, volume values, and overview
    /// light rows all come from generated original-data payloads; this builder
    /// does not fit any value to a screenshot.
    /// </summary>
    public static class EndfieldPlayableCharInfoProfileBuilder
    {
        public const string SourceManifestAssetPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/" +
            "CharInfoPlayableProfiles/source_profiles.json";
        public const string GeneratedRoot =
            "Assets/EndfieldGraphShaderLab/Generated/CharInfoPlayableProfiles";
        public const string TextureRoot = GeneratedRoot + "/Textures";
        public const string MeshRoot = GeneratedRoot + "/Meshes";
        public const string ProfileRoot = GeneratedRoot + "/Profiles";

        private const string ExpectedSchema =
            "endfield.playable-charinfo-presentation-profiles.v1";
        private const float SourceTextureSize = 1024.0f;

        [MenuItem("Endfield/Character Recovery Lab/Build All Playable CharInfo Profiles")]
        public static void BuildAllProfilesMenu()
        {
            Dictionary<string, CharacterRecoveryPresentationProfile> profiles =
                BuildAllProfiles();
            Debug.Log(
                $"Built {profiles.Count} source-recovered playable CharInfo presentation profiles.");
        }

        [MenuItem("Endfield/Character Recovery Lab/Verify Playable CharInfo Portrait Orientation")]
        public static void VerifyPortraitOrientationMenu()
        {
            int verifiedCount = VerifyPortraitOrientation();
            Debug.Log(
                $"Playable CharInfo portrait orientation verification passed: " +
                $"profiles={verifiedCount}, display-upright PNG rows map to " +
                "bottom=vMin/top=vMax with no second vertical flip.");
        }

        public static Dictionary<string, CharacterRecoveryPresentationProfile>
            BuildAllProfiles()
        {
            string sourceFullPath = AssetPathToFullPath(SourceManifestAssetPath);
            if (!File.Exists(sourceFullPath))
            {
                throw new FileNotFoundException(
                    "Playable CharInfo source profiles are missing. Run " +
                    "recover_playable_charinfo_profiles.bat first.",
                    sourceFullPath);
            }

            Dictionary<string, object> payload = Dict(
                ManifestMiniJson.Deserialize(
                    File.ReadAllText(sourceFullPath, Encoding.UTF8)));
            if (!string.Equals(
                    Str(Get(payload, "schema")),
                    ExpectedSchema,
                    StringComparison.Ordinal) ||
                !Bool(Get(Dict(Get(payload, "validation")), "ok")))
            {
                throw new InvalidDataException(
                    "Playable CharInfo source profile payload failed schema/validation checks.");
            }

            IList characterRows = List(Get(payload, "characters"));
            int expectedCount = Int(Get(payload, "character_count"));
            if (expectedCount <= 0 || characterRows.Count != expectedCount)
            {
                throw new InvalidDataException(
                    $"Playable CharInfo payload count mismatch: declared={expectedCount}, rows={characterRows.Count}.");
            }

            EnsureFolders();
            string repositoryRoot = Path.GetFullPath(Path.Combine(
                Directory.GetCurrentDirectory(),
                ".."));
            foreach (object rowObject in characterRows)
            {
                Dictionary<string, object> row = Dict(rowObject);
                Dictionary<string, object> portrait = Dict(Get(row, "portrait"));
                Dictionary<string, object> texturePng =
                    Dict(Get(portrait, "texture_png"));
                CopyVerifiedTexture(repositoryRoot, portrait, texturePng);
            }
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);

            TextAsset sourceManifest =
                AssetDatabase.LoadAssetAtPath<TextAsset>(SourceManifestAssetPath);
            if (sourceManifest == null)
                throw new InvalidDataException(
                    $"Unity could not import source profile manifest {SourceManifestAssetPath}.");

            var result = new Dictionary<string, CharacterRecoveryPresentationProfile>(
                StringComparer.OrdinalIgnoreCase);
            foreach (object rowObject in characterRows)
            {
                Dictionary<string, object> row = Dict(rowObject);
                CharacterRecoveryPresentationProfile profile =
                    BuildProfile(row, sourceManifest);
                if (!result.TryAdd(profile.rootName, profile))
                    throw new InvalidDataException(
                        $"Duplicate playable CharInfo root name: {profile.rootName}.");
            }

            if (result.Count != expectedCount)
                throw new InvalidDataException(
                    $"Built {result.Count} CharInfo profiles; expected {expectedCount}.");
            AssetDatabase.SaveAssets();
            VerifyPortraitOrientation(payload, result);
            return result;
        }

        public static int VerifyPortraitOrientation()
        {
            string sourceFullPath = AssetPathToFullPath(SourceManifestAssetPath);
            if (!File.Exists(sourceFullPath))
                throw new FileNotFoundException(
                    "Playable CharInfo source profiles are missing.",
                    sourceFullPath);
            Dictionary<string, object> payload = Dict(
                ManifestMiniJson.Deserialize(
                    File.ReadAllText(sourceFullPath, Encoding.UTF8)));
            IList rows = List(Get(payload, "characters"));
            var profiles = new Dictionary<string, CharacterRecoveryPresentationProfile>(
                StringComparer.OrdinalIgnoreCase);
            foreach (object rowObject in rows)
            {
                Dictionary<string, object> row = Dict(rowObject);
                string rootName = Str(Get(row, "root_name"));
                CharacterRecoveryPresentationProfile profile = LoadProfile(rootName);
                if (profile == null || !profiles.TryAdd(rootName, profile))
                    throw new InvalidDataException(
                        $"Playable CharInfo portrait profile is missing or duplicated: {rootName}.");
            }
            VerifyPortraitOrientation(payload, profiles);
            return profiles.Count;
        }

        public static CharacterRecoveryPresentationProfile LoadProfile(
            string rootName)
        {
            if (string.IsNullOrWhiteSpace(rootName))
                return null;
            return AssetDatabase.LoadAssetAtPath<CharacterRecoveryPresentationProfile>(
                ProfileAssetPath(rootName));
        }

        public static string ProfileAssetPath(string rootName) =>
            $"{ProfileRoot}/{Safe(rootName)}.asset";

        private static CharacterRecoveryPresentationProfile BuildProfile(
            Dictionary<string, object> row,
            TextAsset sourceManifest)
        {
            string rootName = Str(Get(row, "root_name"));
            string characterId = Str(Get(row, "character_id"));
            if (rootName.Length == 0 || characterId.Length == 0)
                throw new InvalidDataException("Playable CharInfo profile has no root_name/character_id.");

            Dictionary<string, object> camera = Dict(Get(row, "camera"));
            Dictionary<string, object> portrait = Dict(Get(row, "portrait"));
            ValidatePortraitPackingForUnflippedUv(portrait, rootName);
            Dictionary<string, object> texturePng = Dict(Get(portrait, "texture_png"));
            Dictionary<string, object> logicalRect = Dict(Get(portrait, "logical_rect"));
            Dictionary<string, object> textureRectRecord =
                Dict(Get(portrait, "texture_rect"));
            float logicalWidth = Float(Get(logicalRect, "width"));
            float logicalHeight = Float(Get(logicalRect, "height"));
            if (Mathf.Abs(logicalWidth - logicalHeight) > 0.0001f || logicalWidth <= 0.0f)
                throw new InvalidDataException(
                    $"{rootName} portrait logical rect is not a positive square.");

            string textureAssetPath = TextureAssetPath(portrait);
            Texture2D portraitTexture = ImportPortraitTexture(textureAssetPath);
            if (portraitTexture.width != 1024 || portraitTexture.height != 1024)
                throw new InvalidDataException(
                    $"{rootName} portrait is not the recovered 1024-square Texture2D.");
            Rect textureRect = new Rect(
                Float(Get(textureRectRecord, "x")),
                Float(Get(textureRectRecord, "y")),
                Float(Get(textureRectRecord, "width")),
                Float(Get(textureRectRecord, "height")));
            Mesh portraitMesh = EnsureSimpleSpriteMesh(
                $"{MeshRoot}/{Safe(rootName)}_CharInfoPortraitTightQuad.asset",
                $"{Safe(rootName)}_CharInfoPortraitTightQuad",
                logicalWidth,
                textureRect);

            string profilePath = ProfileAssetPath(rootName);
            CharacterRecoveryPresentationProfile profile =
                AssetDatabase.LoadAssetAtPath<CharacterRecoveryPresentationProfile>(
                    profilePath);
            if (profile == null)
            {
                profile = ScriptableObject.CreateInstance<
                    CharacterRecoveryPresentationProfile>();
                profile.name = rootName + " CharInfo Presentation";
                AssetDatabase.CreateAsset(profile, profilePath);
            }

            profile.schema = "endfield.playable-charinfo-presentation-profile.v1";
            profile.sourceRecovered = true;
            profile.characterId = characterId;
            profile.actorToken = Str(Get(row, "actor_token"));
            profile.rootName = rootName;
            profile.displayName = Str(Get(row, "display_name"), rootName);
            profile.cameraGroup = Str(Get(row, "camera_group"));
            profile.lightGroup = Str(Get(row, "light_group"));
            profile.sourceManifest = sourceManifest;
            profile.cameraPosition = Vector3List(List(Get(camera, "position")));
            profile.lookAtPosition = Vector3List(List(Get(camera, "look_at")));
            profile.authoredOverviewRotation =
                QuaternionList(List(Get(camera, "authored_rotation_xyzw")));
            profile.fieldOfView = Float(Get(camera, "field_of_view"));
            profile.nearClip = Float(Get(camera, "near_clip"));
            profile.farClip = Float(Get(camera, "far_clip"));
            Vector2 sensorSize = Vector2List(List(Get(camera, "sensor_size")));
            profile.referenceAspect = sensorSize.y > 0.0f
                ? sensorSize.x / sensorSize.y
                : 16.0f / 9.0f;
            profile.gyroscopeEntryOffsets =
                Vector2List(List(Get(camera, "gyroscope_entry_offsets")));
            profile.overviewImageOffset =
                Vector3Dictionary(Dict(Get(row, "overview_image_offset")));
            profile.portraitTexture = portraitTexture;
            profile.portraitMesh = portraitMesh;

            GameObject scratch = new GameObject(
                "__CharInfoProfileLighting_" + rootName);
            scratch.SetActive(false);
            try
            {
                EndfieldHGRPCharacterLightingVolume volume =
                    scratch.AddComponent<EndfieldHGRPCharacterLightingVolume>();
                volume.compatibilityShaderInfluence = 1.0f;
                if (!EndfieldOriginalRenderParameterImporter.TryApplyCharacterLighting(
                        volume,
                        rootName,
                        out string lightingProvenance))
                {
                    throw new InvalidDataException(
                        $"Could not load original character-volume overrides for {rootName}.");
                }
                volume.compatibilityShaderInfluence = 1.0f;
                volume.postExposureEV = 0.0f;
                if (profile.characterLighting == null)
                    profile.characterLighting = new CharacterRecoveryLightingProfile();
                profile.characterLighting.CaptureFrom(volume);
                profile.characterLightingProvenance = lightingProvenance;
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(scratch);
            }

            if (!EndfieldOriginalOperatorLightImporter.TryRead(
                    rootName,
                    out EndfieldHGOperatorLightData[] operatorLights,
                    out string operatorLightProvenance))
            {
                throw new InvalidDataException(
                    $"Could not load original overview-light rows for {rootName}.");
            }
            profile.operatorLights = operatorLights;
            profile.operatorLightProvenance = operatorLightProvenance;
            EditorUtility.SetDirty(profile);
            return profile;
        }

        private static void CopyVerifiedTexture(
            string repositoryRoot,
            Dictionary<string, object> portrait,
            Dictionary<string, object> texturePng)
        {
            string relativeSource = Str(Get(texturePng, "path"));
            string expectedHash = Str(Get(texturePng, "sha256"));
            if (relativeSource.Length == 0 || expectedHash.Length != 64)
                throw new InvalidDataException("Portrait texture source path/hash is incomplete.");
            string sourcePath = Path.GetFullPath(Path.Combine(
                repositoryRoot,
                relativeSource.Replace('/', Path.DirectorySeparatorChar)));
            if (!File.Exists(sourcePath))
                throw new FileNotFoundException(
                    "Recovered playable portrait Texture2D is missing.",
                    sourcePath);
            string actualHash = Sha256(sourcePath);
            if (!string.Equals(actualHash, expectedHash, StringComparison.OrdinalIgnoreCase))
            {
                throw new InvalidDataException(
                    $"Recovered portrait hash mismatch: {sourcePath}; " +
                    $"expected={expectedHash}, actual={actualHash}.");
            }

            string destinationAssetPath = TextureAssetPath(portrait);
            string destinationPath = AssetPathToFullPath(destinationAssetPath);
            if (!File.Exists(destinationPath) ||
                !string.Equals(
                    Sha256(destinationPath),
                    expectedHash,
                    StringComparison.OrdinalIgnoreCase))
            {
                File.Copy(sourcePath, destinationPath, true);
            }
        }

        private static Texture2D ImportPortraitTexture(string assetPath)
        {
            AssetDatabase.ImportAsset(
                assetPath,
                ImportAssetOptions.ForceSynchronousImport);
            TextureImporter importer =
                AssetImporter.GetAtPath(assetPath) as TextureImporter;
            if (importer == null)
                throw new InvalidDataException($"No TextureImporter for {assetPath}.");

            bool changed =
                importer.textureType != TextureImporterType.Default ||
                importer.textureShape != TextureImporterShape.Texture2D ||
                !importer.sRGBTexture ||
                importer.alphaSource != TextureImporterAlphaSource.FromInput ||
                importer.alphaIsTransparency ||
                importer.mipmapEnabled ||
                importer.npotScale != TextureImporterNPOTScale.None ||
                importer.filterMode != FilterMode.Bilinear ||
                importer.wrapMode != TextureWrapMode.Clamp ||
                importer.textureCompression != TextureImporterCompression.Uncompressed ||
                importer.maxTextureSize != 1024;
            importer.textureType = TextureImporterType.Default;
            importer.textureShape = TextureImporterShape.Texture2D;
            importer.sRGBTexture = true;
            importer.alphaSource = TextureImporterAlphaSource.FromInput;
            importer.alphaIsTransparency = false;
            importer.mipmapEnabled = false;
            importer.npotScale = TextureImporterNPOTScale.None;
            importer.filterMode = FilterMode.Bilinear;
            importer.wrapMode = TextureWrapMode.Clamp;
            importer.textureCompression = TextureImporterCompression.Uncompressed;
            importer.maxTextureSize = 1024;
            if (changed)
                importer.SaveAndReimport();

            Texture2D texture = AssetDatabase.LoadAssetAtPath<Texture2D>(assetPath);
            if (texture == null)
                throw new InvalidDataException($"Could not import {assetPath}.");
            return texture;
        }

        private static Mesh EnsureSimpleSpriteMesh(
            string assetPath,
            string meshName,
            float logicalSpriteSize,
            Rect textureRect)
        {
            Mesh mesh = AssetDatabase.LoadAssetAtPath<Mesh>(assetPath);
            if (mesh == null)
            {
                mesh = new Mesh { name = meshName };
                AssetDatabase.CreateAsset(mesh, assetPath);
            }

            float left = -0.5f + textureRect.xMin / logicalSpriteSize;
            float bottom = -0.5f + textureRect.yMin / logicalSpriteSize;
            float right = -0.5f + textureRect.xMax / logicalSpriteSize;
            float top = -0.5f + textureRect.yMax / logicalSpriteSize;
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
                // The exported PNG is display-upright. TextureImporter maps
                // its rows to Unity's bottom-origin sampling convention, so
                // the source tight-rect UVs must not be flipped a second time.
                new Vector2(textureRect.xMin / SourceTextureSize, textureRect.yMin / SourceTextureSize),
                new Vector2(textureRect.xMax / SourceTextureSize, textureRect.yMin / SourceTextureSize),
                new Vector2(textureRect.xMax / SourceTextureSize, textureRect.yMax / SourceTextureSize),
                new Vector2(textureRect.xMin / SourceTextureSize, textureRect.yMax / SourceTextureSize),
            };
            mesh.triangles = new[] { 0, 2, 1, 0, 3, 2 };
            mesh.RecalculateBounds();
            mesh.UploadMeshData(false);
            EditorUtility.SetDirty(mesh);
            return mesh;
        }

        private static void VerifyPortraitOrientation(
            Dictionary<string, object> payload,
            Dictionary<string, CharacterRecoveryPresentationProfile> profiles)
        {
            if (!string.Equals(
                    Str(Get(payload, "schema")),
                    ExpectedSchema,
                    StringComparison.Ordinal) ||
                !Bool(Get(Dict(Get(payload, "validation")), "ok")))
            {
                throw new InvalidDataException(
                    "Playable CharInfo source profile payload failed orientation validation.");
            }

            IList rows = List(Get(payload, "characters"));
            int expectedCount = Int(Get(payload, "character_count"));
            if (expectedCount <= 0 || rows.Count != expectedCount ||
                profiles.Count != expectedCount)
            {
                throw new InvalidDataException(
                    "Playable CharInfo portrait orientation input count is inconsistent.");
            }

            foreach (object rowObject in rows)
            {
                Dictionary<string, object> row = Dict(rowObject);
                string rootName = Str(Get(row, "root_name"));
                if (!profiles.TryGetValue(rootName, out CharacterRecoveryPresentationProfile profile) ||
                    profile == null || profile.portraitTexture == null ||
                    profile.portraitMesh == null)
                {
                    throw new InvalidDataException(
                        $"{rootName} playable portrait assets are incomplete.");
                }

                Dictionary<string, object> portrait = Dict(Get(row, "portrait"));
                ValidatePortraitPackingForUnflippedUv(portrait, rootName);
                Dictionary<string, object> logicalRect = Dict(Get(portrait, "logical_rect"));
                Dictionary<string, object> textureRectRecord =
                    Dict(Get(portrait, "texture_rect"));
                float logicalWidth = Float(Get(logicalRect, "width"));
                Rect textureRect = new Rect(
                    Float(Get(textureRectRecord, "x")),
                    Float(Get(textureRectRecord, "y")),
                    Float(Get(textureRectRecord, "width")),
                    Float(Get(textureRectRecord, "height")));
                VerifyPortraitMeshOrientation(
                    profile.portraitMesh,
                    logicalWidth,
                    textureRect,
                    rootName);

                TextureImporter importer =
                    AssetImporter.GetAtPath(TextureAssetPath(portrait)) as TextureImporter;
                if (importer == null ||
                    importer.textureType != TextureImporterType.Default ||
                    importer.textureShape != TextureImporterShape.Texture2D ||
                    importer.alphaSource != TextureImporterAlphaSource.FromInput ||
                    importer.mipmapEnabled ||
                    importer.wrapMode != TextureWrapMode.Clamp)
                {
                    throw new InvalidDataException(
                        $"{rootName} portrait importer no longer preserves the display-upright PNG contract.");
                }
            }
        }

        private static void ValidatePortraitPackingForUnflippedUv(
            Dictionary<string, object> portrait,
            string rootName)
        {
            Dictionary<string, object> packing = Dict(Get(portrait, "packing"));
            if (!string.Equals(
                    Str(Get(packing, "meshType")),
                    "Tight",
                    StringComparison.Ordinal) ||
                !string.Equals(
                    Str(Get(packing, "packingMode")),
                    "Tight",
                    StringComparison.Ordinal) ||
                !string.Equals(
                    Str(Get(packing, "packingRotation")),
                    "None",
                    StringComparison.Ordinal) ||
                Int(Get(packing, "packed")) != 0)
            {
                throw new InvalidDataException(
                    $"{rootName} portrait packing cannot use the recovered " +
                    "unflipped tight-rectangle UV path: expected " +
                    "meshType=Tight, packingMode=Tight, " +
                    "packingRotation=None, packed=0.");
            }
        }

        private static void VerifyPortraitMeshOrientation(
            Mesh mesh,
            float logicalSpriteSize,
            Rect textureRect,
            string rootName)
        {
            Vector3[] vertices = mesh.vertices;
            Vector2[] uv = mesh.uv;
            int[] triangles = mesh.triangles;
            if (vertices.Length != 4 || uv.Length != 4 || triangles.Length != 6)
                throw new InvalidDataException(
                    $"{rootName} portrait tight quad is malformed.");

            float left = -0.5f + textureRect.xMin / logicalSpriteSize;
            float bottom = -0.5f + textureRect.yMin / logicalSpriteSize;
            float right = -0.5f + textureRect.xMax / logicalSpriteSize;
            float top = -0.5f + textureRect.yMax / logicalSpriteSize;
            Vector3[] expectedVertices =
            {
                new Vector3(left, bottom, 0.0f),
                new Vector3(right, bottom, 0.0f),
                new Vector3(right, top, 0.0f),
                new Vector3(left, top, 0.0f),
            };
            Vector2[] expectedUv =
            {
                new Vector2(textureRect.xMin / SourceTextureSize, textureRect.yMin / SourceTextureSize),
                new Vector2(textureRect.xMax / SourceTextureSize, textureRect.yMin / SourceTextureSize),
                new Vector2(textureRect.xMax / SourceTextureSize, textureRect.yMax / SourceTextureSize),
                new Vector2(textureRect.xMin / SourceTextureSize, textureRect.yMax / SourceTextureSize),
            };
            int[] expectedTriangles = { 0, 2, 1, 0, 3, 2 };
            for (int index = 0; index < 4; index++)
            {
                if (Vector3.SqrMagnitude(vertices[index] - expectedVertices[index]) >= 1e-12f ||
                    Vector2.SqrMagnitude(uv[index] - expectedUv[index]) >= 1e-12f)
                {
                    throw new InvalidDataException(
                        $"{rootName} portrait vertex/UV row {index} violates the recovered tight-sprite contract.");
                }
            }
            for (int index = 0; index < expectedTriangles.Length; index++)
            {
                if (triangles[index] != expectedTriangles[index])
                    throw new InvalidDataException(
                        $"{rootName} portrait triangle row {index} drifted.");
            }
            if (!(vertices[0].y < vertices[2].y && uv[0].y < uv[2].y))
            {
                throw new InvalidDataException(
                    $"{rootName} portrait is vertically inverted: bottom must sample vMin and top vMax.");
            }
        }

        private static string TextureAssetPath(Dictionary<string, object> portrait)
        {
            string name = Str(Get(portrait, "name"));
            if (name.Length == 0)
                throw new InvalidDataException("Playable portrait row has no name.");
            return $"{TextureRoot}/{Safe(name)}.png";
        }

        private static void EnsureFolders()
        {
            foreach (string assetPath in new[]
                     {
                         GeneratedRoot,
                         TextureRoot,
                         MeshRoot,
                         ProfileRoot,
                     })
            {
                Directory.CreateDirectory(AssetPathToFullPath(assetPath));
            }
        }

        private static string AssetPathToFullPath(string assetPath) =>
            Path.GetFullPath(Path.Combine(
                Directory.GetCurrentDirectory(),
                assetPath.Replace('/', Path.DirectorySeparatorChar)));

        private static string Sha256(string path)
        {
            using (SHA256 hash = SHA256.Create())
            using (FileStream stream = File.OpenRead(path))
                return BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", "");
        }

        private static string Safe(string value)
        {
            foreach (char invalid in Path.GetInvalidFileNameChars())
                value = value.Replace(invalid, '_');
            return value;
        }

        private static object Get(Dictionary<string, object> dictionary, string key) =>
            dictionary != null && dictionary.TryGetValue(key, out object value)
                ? value
                : null;

        private static Dictionary<string, object> Dict(object value) =>
            value as Dictionary<string, object> ??
            new Dictionary<string, object>();

        private static IList List(object value) =>
            value as IList ?? Array.Empty<object>();

        private static string Str(object value, string fallback = "") =>
            value == null
                ? fallback
                : Convert.ToString(value, CultureInfo.InvariantCulture) ?? fallback;

        private static bool Bool(object value) =>
            value is bool boolean
                ? boolean
                : value != null &&
                  Convert.ToDouble(value, CultureInfo.InvariantCulture) != 0.0;

        private static int Int(object value) =>
            value == null
                ? 0
                : Convert.ToInt32(value, CultureInfo.InvariantCulture);

        private static float Float(object value) =>
            value == null
                ? 0.0f
                : Convert.ToSingle(value, CultureInfo.InvariantCulture);

        private static Vector2 Vector2List(IList values) => new Vector2(
            Float(values.Count > 0 ? values[0] : null),
            Float(values.Count > 1 ? values[1] : null));

        private static Vector3 Vector3List(IList values) => new Vector3(
            Float(values.Count > 0 ? values[0] : null),
            Float(values.Count > 1 ? values[1] : null),
            Float(values.Count > 2 ? values[2] : null));

        private static Vector3 Vector3Dictionary(
            Dictionary<string, object> values) => new Vector3(
            Float(Get(values, "x")),
            Float(Get(values, "y")),
            Float(Get(values, "z")));

        private static Quaternion QuaternionList(IList values)
        {
            Quaternion quaternion = new Quaternion(
                Float(values.Count > 0 ? values[0] : null),
                Float(values.Count > 1 ? values[1] : null),
                Float(values.Count > 2 ? values[2] : null),
                Float(values.Count > 3 ? values[3] : null));
            quaternion.Normalize();
            return quaternion;
        }
    }
}
