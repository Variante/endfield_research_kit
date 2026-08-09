using System;
using System.IO;
using System.Security.Cryptography;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Rebuilds the exact CharInfo character-reflection, environment-reflection,
    /// and visible-sky Cubemaps from face-major BC6H payloads exported by
    /// AnimeStudio. No pixel decode, orientation transform, color conversion,
    /// or mip regeneration occurs. The environment-reflection Cubemap is bound
    /// separately for the default-off recovered reflection-probe oct/global
    /// frame path; it never substitutes the direct character Cubemap.
    /// </summary>
    public static class EndfieldRecoveredCharCubemapImporter
    {
        public const string SourcePayloadAssetPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfo/" +
            "T_hdri_reflection_char_01.cubemap.bc6h.bytes";

        public const string CubemapAssetPath =
            "Assets/EndfieldGraphShaderLab/Generated/Environment/" +
            "T_hdri_reflection_char_01.asset";

        public const string SkySourcePayloadAssetPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfo/" +
            "T_hdri_006.cubemap.bc6h.bytes";

        public const string SkyCubemapAssetPath =
            "Assets/EndfieldGraphShaderLab/Generated/Environment/" +
            "T_hdri_006.asset";

        public const string EnvironmentReflectionSourcePayloadAssetPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfo/" +
            "T_hdri_env_char_01.cubemap.bc6h.bytes";

        public const string EnvironmentReflectionCubemapAssetPath =
            "Assets/EndfieldGraphShaderLab/Generated/Environment/" +
            "T_hdri_env_char_01.asset";

        private static readonly string[] GeneratedScenePaths =
        {
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Scenes/" +
                "CharacterRecoveryViewer.unity",
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Scenes/" +
                "CharacterRenderStyleFast.unity",
        };

        public const string ExpectedPayloadSha256 =
            "898ff663c8d447456666612e55697f7aecde13c03b19b74f9df5b73735e2c9df";

        public const string SkyExpectedPayloadSha256 =
            "070fd7c568b9db9c1cfc936e3fe081465807e761d28090761c92f6f94444214e";

        public const string EnvironmentReflectionExpectedPayloadSha256 =
            "948f8d8dfb77e1b29171c4b04caaa679202e06624ab7be2203719e11ca6ee7b7";

        private const int Size = 128;
        private const int MipCount = 8;
        private const int FaceCount = 6;
        private const int ExpectedPayloadSize = 131232;

        private static readonly int[] MipByteSizes =
        {
            16384,
            4096,
            1024,
            256,
            64,
            16,
            16,
            16,
        };

        private static readonly CubemapFace[] Faces =
        {
            CubemapFace.PositiveX,
            CubemapFace.NegativeX,
            CubemapFace.PositiveY,
            CubemapFace.NegativeY,
            CubemapFace.PositiveZ,
            CubemapFace.NegativeZ,
        };

        [MenuItem("Endfield/Character Recovery Lab/Import Recovered CharInfo Cubemap")]
        public static void ImportRecoveredCharInfoCubemap()
        {
            Cubemap imported = ImportExactCubemap(
                SourcePayloadAssetPath,
                CubemapAssetPath,
                ExpectedPayloadSha256,
                "T_hdri_reflection_char_01");
            int boundVolumeCount = BindIntoGeneratedScenes(imported);
            Debug.Log(
                "Recovered CharInfo Cubemap imported: " +
                $"asset={CubemapAssetPath}, format={imported.format}, " +
                $"size={imported.width}, mips={imported.mipmapCount}, faces={FaceCount}, " +
                $"filter={imported.filterMode}, wrap={imported.wrapModeU}/" +
                $"{imported.wrapModeV}/{imported.wrapModeW}, " +
                $"linear={!imported.isDataSRGB}, boundVolumes={boundVolumeCount}, " +
                $"payloadSha256={ExpectedPayloadSha256}");
        }

        public static void VerifyRecoveredCharInfoCubemap()
        {
            byte[] payload = ReadAndValidateSourcePayload(
                SourcePayloadAssetPath,
                ExpectedPayloadSha256);
            Cubemap cubemap = AssetDatabase.LoadAssetAtPath<Cubemap>(CubemapAssetPath);
            ValidateImportedAsset(
                cubemap,
                payload,
                CubemapAssetPath,
                ExpectedPayloadSha256);
            Debug.Log(
                "Recovered CharInfo Cubemap verification passed: " +
                $"asset={CubemapAssetPath}, payloadSha256={ExpectedPayloadSha256}");
        }

        [MenuItem("Endfield/Character Recovery Lab/Import Recovered CharInfo Sky Cubemap")]
        public static void ImportRecoveredCharInfoSkyCubemap()
        {
            Cubemap imported = ImportExactCubemap(
                SkySourcePayloadAssetPath,
                SkyCubemapAssetPath,
                SkyExpectedPayloadSha256,
                "T_hdri_006");
            int boundCameraCount = BindSkyIntoGeneratedScenes(imported);
            Debug.Log(
                "Recovered CharInfo sky Cubemap imported: " +
                $"asset={SkyCubemapAssetPath}, format={imported.format}, " +
                $"size={imported.width}, mips={imported.mipmapCount}, faces={FaceCount}, " +
                $"filter={imported.filterMode}, wrap={imported.wrapModeU}/" +
                $"{imported.wrapModeV}/{imported.wrapModeW}, " +
                $"linear={!imported.isDataSRGB}, boundCameras={boundCameraCount}, " +
                $"payloadSha256={SkyExpectedPayloadSha256}");
        }

        public static void VerifyRecoveredCharInfoSkyCubemap()
        {
            byte[] payload = ReadAndValidateSourcePayload(
                SkySourcePayloadAssetPath,
                SkyExpectedPayloadSha256);
            Cubemap cubemap = AssetDatabase.LoadAssetAtPath<Cubemap>(
                SkyCubemapAssetPath);
            ValidateImportedAsset(
                cubemap,
                payload,
                SkyCubemapAssetPath,
                SkyExpectedPayloadSha256);
            Debug.Log(
                "Recovered CharInfo sky Cubemap verification passed: " +
                $"asset={SkyCubemapAssetPath}, " +
                $"payloadSha256={SkyExpectedPayloadSha256}");
        }

        [MenuItem(
            "Endfield/Character Recovery Lab/Import Recovered CharInfo " +
            "Environment Reflection Cubemap")]
        public static void ImportRecoveredCharInfoEnvironmentReflectionCubemap()
        {
            Cubemap imported = ImportExactCubemap(
                EnvironmentReflectionSourcePayloadAssetPath,
                EnvironmentReflectionCubemapAssetPath,
                EnvironmentReflectionExpectedPayloadSha256,
                "T_hdri_env_char_01");
            int boundVolumeCount =
                BindEnvironmentReflectionIntoGeneratedScenes(imported);
            Debug.Log(
                "Recovered CharInfo environment-reflection Cubemap imported " +
                "for the default-off reflection-probe frame path: " +
                $"asset={EnvironmentReflectionCubemapAssetPath}, " +
                $"format={imported.format}, size={imported.width}, " +
                $"mips={imported.mipmapCount}, faces={FaceCount}, " +
                $"boundVolumes={boundVolumeCount}, " +
                $"payloadSha256={EnvironmentReflectionExpectedPayloadSha256}");
        }

        public static void VerifyRecoveredCharInfoEnvironmentReflectionCubemap()
        {
            byte[] payload = ReadAndValidateSourcePayload(
                EnvironmentReflectionSourcePayloadAssetPath,
                EnvironmentReflectionExpectedPayloadSha256);
            Cubemap cubemap = AssetDatabase.LoadAssetAtPath<Cubemap>(
                EnvironmentReflectionCubemapAssetPath);
            ValidateImportedAsset(
                cubemap,
                payload,
                EnvironmentReflectionCubemapAssetPath,
                EnvironmentReflectionExpectedPayloadSha256);
            Debug.Log(
                "Recovered CharInfo environment-reflection Cubemap " +
                "verification passed: " +
                $"asset={EnvironmentReflectionCubemapAssetPath}, " +
                $"payloadSha256={EnvironmentReflectionExpectedPayloadSha256}");
        }

        public static void ImportRecoveredCharInfoCubemaps()
        {
            ImportRecoveredCharInfoCubemap();
            ImportRecoveredCharInfoSkyCubemap();
            ImportRecoveredCharInfoEnvironmentReflectionCubemap();
        }

        private static Cubemap ImportExactCubemap(
            string sourcePayloadAssetPath,
            string cubemapAssetPath,
            string expectedPayloadSha256,
            string cubemapName)
        {
            byte[] payload = ReadAndValidateSourcePayload(
                sourcePayloadAssetPath,
                expectedPayloadSha256);
            EnsureAssetFolder(cubemapAssetPath);

            Cubemap cubemap = AssetDatabase.LoadAssetAtPath<Cubemap>(
                cubemapAssetPath);
            UnityEngine.Object existingMainAsset =
                AssetDatabase.LoadMainAssetAtPath(cubemapAssetPath);
            if (existingMainAsset != null && cubemap == null)
            {
                throw new InvalidOperationException(
                    $"Existing asset is not a Cubemap: {cubemapAssetPath}");
            }

            bool created = cubemap == null;
            Cubemap rebuilt = new Cubemap(
                Size,
                TextureFormat.BC6H,
                MipCount,
                true)
            {
                name = cubemapName,
            };
            ApplyExactPayload(rebuilt, payload);
            ApplySerializedSamplingState(rebuilt);
            rebuilt.Apply(false, false);

            if (created)
            {
                cubemap = rebuilt;
                AssetDatabase.CreateAsset(cubemap, cubemapAssetPath);
            }
            else
            {
                EditorUtility.CopySerialized(rebuilt, cubemap);
                UnityEngine.Object.DestroyImmediate(rebuilt);
                EditorUtility.SetDirty(cubemap);
            }

            AssetDatabase.SaveAssets();
            AssetDatabase.ImportAsset(
                cubemapAssetPath,
                ImportAssetOptions.ForceUpdate);

            Cubemap imported = AssetDatabase.LoadAssetAtPath<Cubemap>(
                cubemapAssetPath);
            ValidateImportedAsset(
                imported,
                payload,
                cubemapAssetPath,
                expectedPayloadSha256);
            return imported;
        }

        private static byte[] ReadAndValidateSourcePayload(
            string sourcePayloadAssetPath,
            string expectedPayloadSha256)
        {
            string projectRoot = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
            string sourcePath = Path.Combine(
                projectRoot,
                sourcePayloadAssetPath.Replace('/', Path.DirectorySeparatorChar));
            if (!File.Exists(sourcePath))
            {
                throw new FileNotFoundException(
                    "Recovered CharInfo BC6H payload is missing.",
                    sourcePath);
            }

            byte[] payload = File.ReadAllBytes(sourcePath);
            if (payload.Length != ExpectedPayloadSize)
            {
                throw new InvalidDataException(
                    $"Unexpected CharInfo Cubemap payload size: {payload.Length}; " +
                    $"expected {ExpectedPayloadSize}.");
            }

            string payloadSha256 = ComputeSha256(payload);
            if (!string.Equals(
                payloadSha256,
                expectedPayloadSha256,
                StringComparison.OrdinalIgnoreCase))
            {
                throw new InvalidDataException(
                    $"Unexpected CharInfo Cubemap payload SHA-256: {payloadSha256}; " +
                    $"expected {expectedPayloadSha256}.");
            }
            return payload;
        }

        private static void ApplyExactPayload(Cubemap cubemap, byte[] payload)
        {
            int offset = 0;
            for (int faceIndex = 0; faceIndex < Faces.Length; faceIndex++)
            {
                for (int mip = 0; mip < MipCount; mip++)
                {
                    int byteSize = MipByteSizes[mip];
                    byte[] slice = new byte[byteSize];
                    Buffer.BlockCopy(payload, offset, slice, 0, byteSize);
                    cubemap.SetPixelData(slice, mip, Faces[faceIndex], 0);
                    offset += byteSize;
                }
            }

            if (offset != payload.Length)
            {
                throw new InvalidDataException(
                    $"Cubemap face/mip layout consumed {offset} bytes; " +
                    $"payload contains {payload.Length} bytes.");
            }
        }

        private static void ApplySerializedSamplingState(Cubemap cubemap)
        {
            cubemap.filterMode = FilterMode.Trilinear;
            cubemap.anisoLevel = 1;
            cubemap.mipMapBias = 0.0f;
            cubemap.wrapModeU = TextureWrapMode.Clamp;
            cubemap.wrapModeV = TextureWrapMode.Clamp;
            cubemap.wrapModeW = TextureWrapMode.Clamp;
        }

        private static void ValidateImportedAsset(
            Cubemap cubemap,
            byte[] expectedPayload,
            string cubemapAssetPath,
            string expectedPayloadSha256)
        {
            if (cubemap == null)
            {
                throw new InvalidOperationException(
                    $"Recovered Cubemap asset does not exist: {cubemapAssetPath}");
            }

            ValidateShape(cubemap);
            if (cubemap.filterMode != FilterMode.Trilinear ||
                cubemap.anisoLevel != 1 ||
                Math.Abs(cubemap.mipMapBias) > 0.000001f ||
                cubemap.wrapModeU != TextureWrapMode.Clamp ||
                cubemap.wrapModeV != TextureWrapMode.Clamp ||
                cubemap.wrapModeW != TextureWrapMode.Clamp)
            {
                throw new InvalidDataException(
                    "Recovered Cubemap sampler state does not match the serialized source.");
            }

            byte[] assetPayload = ReadExactAssetPayload(cubemap);
            string assetSha256 = ComputeSha256(assetPayload);
            if (!string.Equals(
                assetSha256,
                expectedPayloadSha256,
                StringComparison.OrdinalIgnoreCase))
            {
                throw new InvalidDataException(
                    $"Recovered Cubemap asset payload SHA-256 mismatch: {assetSha256}; " +
                    $"expected {expectedPayloadSha256}.");
            }

            if (assetPayload.Length != expectedPayload.Length)
            {
                throw new InvalidDataException(
                    "Recovered Cubemap asset payload length changed during import.");
            }
        }

        private static void ValidateShape(Cubemap cubemap)
        {
            if (cubemap.width != Size ||
                cubemap.height != Size ||
                cubemap.format != TextureFormat.BC6H ||
                cubemap.mipmapCount != MipCount ||
                cubemap.isDataSRGB)
            {
                throw new InvalidDataException(
                    "Recovered Cubemap shape/format mismatch: " +
                    $"size={cubemap.width}x{cubemap.height}, format={cubemap.format}, " +
                    $"mips={cubemap.mipmapCount}, isDataSRGB={cubemap.isDataSRGB}; " +
                    $"expected {Size}x{Size}, BC6H, {MipCount} mips, linear data.");
            }
        }

        private static byte[] ReadExactAssetPayload(Cubemap cubemap)
        {
            byte[] payload = new byte[ExpectedPayloadSize];
            int offset = 0;
            for (int faceIndex = 0; faceIndex < Faces.Length; faceIndex++)
            {
                for (int mip = 0; mip < MipCount; mip++)
                {
                    int byteSize = MipByteSizes[mip];
                    var source = cubemap.GetPixelData<byte>(mip, Faces[faceIndex]);
                    if (source.Length != byteSize)
                    {
                        throw new InvalidDataException(
                            $"Recovered Cubemap face {Faces[faceIndex]} mip {mip} " +
                            $"contains {source.Length} bytes; expected {byteSize}.");
                    }
                    for (int i = 0; i < byteSize; i++)
                    {
                        payload[offset + i] = source[i];
                    }
                    offset += byteSize;
                }
            }
            return payload;
        }

        private static string ComputeSha256(byte[] data)
        {
            using (SHA256 sha256 = SHA256.Create())
            {
                return BitConverter.ToString(sha256.ComputeHash(data))
                    .Replace("-", string.Empty)
                    .ToLowerInvariant();
            }
        }

        private static int BindIntoGeneratedScenes(Cubemap cubemap)
        {
            SceneSetup[] previousSetup = EditorSceneManager.GetSceneManagerSetup();
            int total = 0;
            try
            {
                foreach (string scenePath in GeneratedScenePaths)
                {
                    if (AssetDatabase.LoadAssetAtPath<SceneAsset>(scenePath) == null)
                    {
                        Debug.LogWarning(
                            $"Recovered Cubemap binding skipped missing scene: {scenePath}");
                        continue;
                    }

                    Scene scene = EditorSceneManager.OpenScene(scenePath, OpenSceneMode.Single);
                    EndfieldHGRPCharacterLightingVolume[] volumes =
                        UnityEngine.Object.FindObjectsOfType<
                            EndfieldHGRPCharacterLightingVolume>(true);
                    int sceneCount = 0;
                    foreach (EndfieldHGRPCharacterLightingVolume volume in volumes)
                    {
                        if (volume == null || volume.gameObject.scene != scene)
                            continue;
                        volume.characterReflectionCubemap = cubemap;
                        EditorUtility.SetDirty(volume);
                        sceneCount++;
                    }

                    if (sceneCount == 0)
                    {
                        throw new InvalidDataException(
                            $"Generated recovery scene contains no character-lighting volume: " +
                            scenePath);
                    }

                    EditorSceneManager.MarkSceneDirty(scene);
                    if (!EditorSceneManager.SaveScene(scene))
                    {
                        throw new IOException(
                            $"Could not save recovered Cubemap binding in {scenePath}");
                    }
                    total += sceneCount;
                }
            }
            finally
            {
                if (previousSetup != null && previousSetup.Length > 0)
                    EditorSceneManager.RestoreSceneManagerSetup(previousSetup);
            }
            AssetDatabase.SaveAssets();
            return total;
        }

        private static int BindEnvironmentReflectionIntoGeneratedScenes(
            Cubemap cubemap)
        {
            SceneSetup[] previousSetup = EditorSceneManager.GetSceneManagerSetup();
            int total = 0;
            try
            {
                foreach (string scenePath in GeneratedScenePaths)
                {
                    if (AssetDatabase.LoadAssetAtPath<SceneAsset>(scenePath) == null)
                    {
                        Debug.LogWarning(
                            "Recovered environment-reflection binding skipped " +
                            $"missing scene: {scenePath}");
                        continue;
                    }

                    Scene scene = EditorSceneManager.OpenScene(
                        scenePath,
                        OpenSceneMode.Single);
                    EndfieldHGRPCharacterLightingVolume[] volumes =
                        UnityEngine.Object.FindObjectsOfType<
                            EndfieldHGRPCharacterLightingVolume>(true);
                    int sceneCount = 0;
                    foreach (EndfieldHGRPCharacterLightingVolume volume in volumes)
                    {
                        if (volume == null || volume.gameObject.scene != scene)
                            continue;
                        volume.environmentReflectionCubemap = cubemap;
                        EditorUtility.SetDirty(volume);
                        sceneCount++;
                    }

                    if (sceneCount == 0)
                    {
                        throw new InvalidDataException(
                            "Generated recovery scene contains no character-lighting " +
                            "volume: " + scenePath);
                    }

                    EditorSceneManager.MarkSceneDirty(scene);
                    if (!EditorSceneManager.SaveScene(scene))
                    {
                        throw new IOException(
                            "Could not save recovered environment-reflection " +
                            "Cubemap binding in " + scenePath);
                    }
                    total += sceneCount;
                }
            }
            finally
            {
                if (previousSetup != null && previousSetup.Length > 0)
                    EditorSceneManager.RestoreSceneManagerSetup(previousSetup);
            }
            AssetDatabase.SaveAssets();
            return total;
        }

        private static int BindSkyIntoGeneratedScenes(Cubemap cubemap)
        {
            SceneSetup[] previousSetup =
                EditorSceneManager.GetSceneManagerSetup();
            int total = 0;
            try
            {
                foreach (string scenePath in GeneratedScenePaths)
                {
                    if (AssetDatabase.LoadAssetAtPath<SceneAsset>(scenePath) == null)
                    {
                        Debug.LogWarning(
                            $"Recovered sky binding skipped missing scene: {scenePath}");
                        continue;
                    }

                    Scene scene = EditorSceneManager.OpenScene(
                        scenePath,
                        OpenSceneMode.Single);
                    Camera targetCamera = null;
                    foreach (Camera camera in
                        UnityEngine.Object.FindObjectsOfType<Camera>(true))
                    {
                        if (camera == null || camera.gameObject.scene != scene)
                            continue;
                        if (targetCamera == null)
                            targetCamera = camera;
                        if (camera.CompareTag("MainCamera"))
                        {
                            targetCamera = camera;
                            break;
                        }
                    }
                    if (targetCamera == null)
                    {
                        throw new InvalidDataException(
                            $"Generated recovery scene contains no camera: " +
                            scenePath);
                    }

                    EndfieldManifestCharacterSetup.ConfigureRecoveredCharInfoSky(
                        targetCamera,
                        requireSourceAssets: true);
                    EndfieldRecoveredCharInfoSky sourceSky =
                        targetCamera.GetComponent<EndfieldRecoveredCharInfoSky>();
                    if (sourceSky == null || sourceSky.sourceCubemap != cubemap)
                    {
                        throw new InvalidDataException(
                            $"Recovered source-sky binding failed in {scenePath}");
                    }

                    EditorSceneManager.MarkSceneDirty(scene);
                    if (!EditorSceneManager.SaveScene(scene))
                    {
                        throw new IOException(
                            $"Could not save recovered sky binding in {scenePath}");
                    }
                    total++;
                }
            }
            finally
            {
                if (previousSetup != null && previousSetup.Length > 0)
                    EditorSceneManager.RestoreSceneManagerSetup(previousSetup);
            }
            AssetDatabase.SaveAssets();
            return total;
        }

        private static void EnsureAssetFolder(string cubemapAssetPath)
        {
            string projectRoot = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
            string assetDirectory = Path.GetDirectoryName(Path.Combine(
                projectRoot,
                cubemapAssetPath.Replace('/', Path.DirectorySeparatorChar)));
            Directory.CreateDirectory(assetDirectory);
            AssetDatabase.Refresh();
        }
    }
}
