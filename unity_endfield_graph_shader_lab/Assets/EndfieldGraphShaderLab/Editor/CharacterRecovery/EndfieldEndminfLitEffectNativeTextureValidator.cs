using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Verifies the source/capture-gated Endminf LitEffect texture transport.
    /// The PNG assets retain ownership of their GUID/local-file-ID identities;
    /// only their imported GPU bytes are replaced with installed BC5/BC7 mips.
    /// </summary>
    public static class EndfieldEndminfLitEffectNativeTextureValidator
    {
        private const string ContractAssetPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/RenderParameters/" +
            "endminf_liteffect_native_texture_payload_contract.json";

        [Serializable]
        private sealed class Contract
        {
            public string schema;
            public string status;
            public int textureCount;
            public int generatedCopyCount;
            public PayloadRow[] textures;
            public MaterialBinding[] materialBindings;
        }

        [Serializable]
        private sealed class PayloadRow
        {
            public string fileName;
            public string property;
            public long pathId;
            public string payloadSha256;
            public int payloadSize;
            public int width;
            public int height;
            public int textureFormat;
            public int dxgiFormat;
            public int mipCount;
            public int sourceColorSpace;
            public EndfieldNativeTexturePayloadPostprocessor.ImportProfile importProfile;
            public EndfieldNativeTexturePayloadPostprocessor.GeneratedCopy[] generatedCopies;
        }

        [Serializable]
        private sealed class MaterialBinding
        {
            public string assetPath;
            public string sha256;
            public PropertyBinding[] textureBindings;
        }

        [Serializable]
        private sealed class PropertyBinding
        {
            public string property;
            public string guid;
            public long localFileId;
        }

        [Serializable]
        private sealed class Report
        {
            public string schema = "endfield.endminf-liteffect-native-texture-validation.v2";
            public string unityVersion;
            public string graphicsDeviceType;
            public int textureCount;
            public int materialCount;
            public bool passed;
            public List<TextureResult> textures = new List<TextureResult>();
            public List<MaterialResult> materials = new List<MaterialResult>();
        }

        [Serializable]
        private sealed class TextureResult
        {
            public string property;
            public string assetPath;
            public string guid;
            public long localFileId;
            public string graphicsFormat;
            public string rawSha256;
            public int rawBytes;
            public int mipCount;
            public int sourceDxgiFormat;
            public bool passed;
            public string error;
        }

        [Serializable]
        private sealed class MaterialResult
        {
            public string assetPath;
            public int exactBindingCount;
            public bool passed;
            public string error;
        }

        [MenuItem("Endfield/Character Recovery Lab/Validate Endminf LitEffect Native Textures")]
        public static void ValidateCommandLine()
        {
            string contractPath = AbsoluteProjectPath(ContractAssetPath);
            if (!File.Exists(contractPath))
                throw new FileNotFoundException(
                    "Endminf LitEffect native texture contract is missing.", contractPath);
            Contract contract = JsonUtility.FromJson<Contract>(File.ReadAllText(contractPath));
            Require(contract != null &&
                contract.schema == "endfield.native-texture-payload-contract.v2" &&
                contract.status == "source_closed_current_build" &&
                contract.textureCount == 4 &&
                contract.generatedCopyCount == 4 &&
                contract.textures != null && contract.textures.Length == 4 &&
                contract.materialBindings != null && contract.materialBindings.Length == 3,
                "Endminf LitEffect native texture contract is incomplete");

            foreach (PayloadRow row in contract.textures)
            {
                Require(row.generatedCopies != null && row.generatedCopies.Length == 1,
                    "Endminf LitEffect texture copy cardinality drifted: " + row.fileName);
                AssetDatabase.ImportAsset(
                    row.generatedCopies[0].assetPath,
                    ImportAssetOptions.ForceSynchronousImport |
                    ImportAssetOptions.ForceUpdate);
            }

            var report = new Report {
                unityVersion = Application.unityVersion,
                graphicsDeviceType = SystemInfo.graphicsDeviceType.ToString(),
                textureCount = contract.textureCount,
                materialCount = contract.materialBindings.Length,
            };
            var texturesByProperty = new Dictionary<string, Texture2D>(
                StringComparer.Ordinal);
            foreach (PayloadRow row in contract.textures)
            {
                TextureResult result = ValidateTexture(row, out Texture2D texture);
                report.textures.Add(result);
                if (result.passed)
                    texturesByProperty.Add(row.property, texture);
            }
            foreach (MaterialBinding binding in contract.materialBindings)
                report.materials.Add(ValidateMaterial(binding, texturesByProperty));

            report.passed =
                report.textures.Count == 4 && report.textures.All(row => row.passed) &&
                report.materials.Count == 3 && report.materials.All(row => row.passed);
            string output = Path.Combine(
                Directory.GetParent(Application.dataPath).FullName,
                "scratch",
                "character_recovery",
                "endminf_liteffect_native_texture",
                "unity_validation.json");
            Directory.CreateDirectory(Path.GetDirectoryName(output));
            File.WriteAllText(output, JsonUtility.ToJson(report, true) + Environment.NewLine);
            Debug.Log(
                $"Validated Endminf LitEffect native textures: textures={report.textureCount}, " +
                $"materials={report.materialCount}, passed={report.passed}.");
            if (!report.passed)
                throw new InvalidOperationException(
                    "Endminf LitEffect native texture validation failed; see " + output);
        }

        private static TextureResult ValidateTexture(
            PayloadRow row,
            out Texture2D texture)
        {
            var result = new TextureResult {
                property = row.property,
                assetPath = row.generatedCopies[0].assetPath,
                sourceDxgiFormat = row.dxgiFormat,
            };
            texture = null;
            try
            {
                Require(EndfieldNativeTexturePayloadPostprocessor.TryResolveForValidation(
                        result.assetPath,
                        out EndfieldNativeTexturePayloadPostprocessor.ResolvedPayload payload),
                    "native payload did not resolve");
                Require(payload.Row.pathId == row.pathId &&
                    payload.Row.payloadSize == row.payloadSize &&
                    payload.Row.payloadSha256.Equals(
                        row.payloadSha256,
                        StringComparison.OrdinalIgnoreCase),
                    "resolved source identity drifted");
                texture = AssetDatabase.LoadAssetAtPath<Texture2D>(result.assetPath);
                TextureImporter importer = AssetImporter.GetAtPath(result.assetPath) as TextureImporter;
                Require(texture != null && importer != null, "texture/importer did not resolve");
                Require(AssetDatabase.TryGetGUIDAndLocalFileIdentifier(
                        texture,
                        out string guid,
                        out long localFileId),
                    "stable PPtr identity did not resolve");
                byte[] raw = texture.GetRawTextureData<byte>().ToArray();
                result.guid = guid;
                result.localFileId = localFileId;
                result.graphicsFormat = texture.graphicsFormat.ToString();
                result.rawSha256 = EndfieldNativeTexturePayloadPostprocessor.Sha256(raw);
                result.rawBytes = raw.Length;
                result.mipCount = texture.mipmapCount;
                var profile = row.importProfile;
                result.passed =
                    guid.Equals(row.generatedCopies[0].guid, StringComparison.OrdinalIgnoreCase) &&
                    localFileId == 2800000 &&
                    raw.SequenceEqual(payload.Bytes) &&
                    result.rawSha256.Equals(row.payloadSha256, StringComparison.OrdinalIgnoreCase) &&
                    raw.Length == row.payloadSize &&
                    texture.width == row.width && texture.height == row.height &&
                    texture.mipmapCount == row.mipCount &&
                    texture.graphicsFormat == payload.GraphicsFormat &&
                    row.dxgiFormat == ExpectedDxgiFormat(row) &&
                    importer.textureType == (TextureImporterType)profile.textureType &&
                    importer.textureShape == TextureImporterShape.Texture2D &&
                    importer.sRGBTexture == profile.sRGBTexture &&
                    importer.mipmapEnabled == profile.mipmapEnabled &&
                    importer.streamingMipmaps == profile.streamingMipmaps &&
                    importer.streamingMipmapsPriority == profile.streamingMipmapsPriority &&
                    importer.filterMode == (FilterMode)profile.filterMode &&
                    importer.anisoLevel == profile.anisoLevel &&
                    Math.Abs(importer.mipMapBias - profile.mipMapBias) < 0.000001f &&
                    importer.wrapModeU == (TextureWrapMode)profile.wrapU &&
                    importer.wrapModeV == (TextureWrapMode)profile.wrapV &&
                    importer.wrapModeW == (TextureWrapMode)profile.wrapW &&
                    !importer.alphaIsTransparency &&
                    importer.npotScale == TextureImporterNPOTScale.None &&
                    importer.textureCompression == TextureImporterCompression.Uncompressed &&
                    importer.isReadable &&
                    texture.isReadable &&
                    texture.filterMode == (FilterMode)profile.filterMode &&
                    texture.anisoLevel == profile.anisoLevel &&
                    Math.Abs(texture.mipMapBias - profile.mipMapBias) < 0.000001f &&
                    texture.wrapModeU == (TextureWrapMode)profile.wrapU &&
                    texture.wrapModeV == (TextureWrapMode)profile.wrapV &&
                    texture.wrapModeW == (TextureWrapMode)profile.wrapW;
                if (!result.passed)
                    result.error = "one or more exact payload/import/runtime gates failed";
            }
            catch (Exception ex)
            {
                result.error = ex.GetType().Name + ": " + ex.Message;
                result.passed = false;
            }
            return result;
        }

        private static MaterialResult ValidateMaterial(
            MaterialBinding binding,
            Dictionary<string, Texture2D> texturesByProperty)
        {
            var result = new MaterialResult { assetPath = binding.assetPath };
            try
            {
                string materialPath = AbsoluteProjectPath(binding.assetPath);
                Require(File.Exists(materialPath), "material file is missing");
                Require(EndfieldNativeTexturePayloadPostprocessor.Sha256(
                        File.ReadAllBytes(materialPath)).Equals(
                        binding.sha256,
                        StringComparison.OrdinalIgnoreCase),
                    "material source hash drifted");
                Material material = AssetDatabase.LoadAssetAtPath<Material>(binding.assetPath);
                Require(material != null, "material did not resolve");
                Require(binding.textureBindings != null &&
                    binding.textureBindings.Length == texturesByProperty.Count,
                    "material property binding contract is incomplete");
                foreach (PropertyBinding expected in binding.textureBindings)
                {
                    Require(texturesByProperty.TryGetValue(
                            expected.property,
                            out Texture2D texture),
                        "contract texture property is unknown: " + expected.property);
                    Require(AssetDatabase.TryGetGUIDAndLocalFileIdentifier(
                            texture,
                            out string guid,
                            out long localFileId) &&
                        guid.Equals(expected.guid, StringComparison.OrdinalIgnoreCase) &&
                        localFileId == expected.localFileId,
                        "material property identity contract drifted: " + expected.property);
                    Require(material.HasTexture(expected.property),
                        "material property is missing: " + expected.property);
                    Require(material.GetTexture(expected.property) == texture,
                        "material texture PPtr drifted: " + expected.property);
                    result.exactBindingCount++;
                }
                result.passed = result.exactBindingCount == 4;
            }
            catch (Exception ex)
            {
                result.error = ex.GetType().Name + ": " + ex.Message;
                result.passed = false;
            }
            return result;
        }

        private static int ExpectedDxgiFormat(PayloadRow row)
        {
            if (row.textureFormat == 25 && row.sourceColorSpace == 1)
                return 99;
            if (row.textureFormat == 27 && row.sourceColorSpace == 0)
                return 83;
            throw new InvalidDataException(
                $"Unsupported Endminf LitEffect source format/color combination: " +
                $"{row.textureFormat}/{row.sourceColorSpace}.");
        }

        private static string AbsoluteProjectPath(string assetPath)
        {
            return Path.GetFullPath(Path.Combine(
                Directory.GetParent(Application.dataPath).FullName,
                assetPath.Replace('/', Path.DirectorySeparatorChar)));
        }

        private static void Require(bool condition, string message)
        {
            if (!condition)
                throw new InvalidDataException(message);
        }
    }
}
