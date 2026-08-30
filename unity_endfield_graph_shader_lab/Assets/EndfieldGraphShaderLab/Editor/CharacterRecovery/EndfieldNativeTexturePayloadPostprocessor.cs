using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;
using UnityEngine.Experimental.Rendering;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Replaces selected PNG-derived character textures with the exact compressed
    /// image and mip bytes from the installed Texture2D objects. Stable PNG asset
    /// paths remain the owner, so existing GUIDs and material PPtrs do not move.
    /// Every injection is gated by the original PathID filename, source-object and
    /// descriptor hashes, PNG hash/GUID, exact import contract, and payload hash.
    /// </summary>
    public sealed class EndfieldNativeTexturePayloadPostprocessor : AssetPostprocessor
    {
        private static readonly string[] ContractAssetPaths = {
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/RenderParameters/" +
                "high_impact_texture_payload_contract.json",
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/RenderParameters/" +
                "endminf_liteffect_native_texture_payload_contract.json",
        };
        private const string AllowedPngRoot =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/";
        private static readonly string[] AllowedPayloadRoots = {
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/TexturePayloads/" +
                "CompressedMipChains/",
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/TexturePayloads/" +
                "EndminfLitEffect/",
        };
        private const string ExpectedSchema =
            "endfield.native-texture-payload-contract.v2";
        private const string ExpectedImportSchema =
            "endfield.character-texture-import-contract.v1";

        [Serializable]
        internal sealed class PayloadContract
        {
            public string schema;
            public string status;
            public string textureImportContractAssetPath;
            public string textureImportContractSha256;
            public int textureCount;
            public int generatedCopyCount;
            public long logicalPayloadBytes;
            public int uniquePayloadCount;
            public long uniquePayloadBytes;
            public long deduplicatedPayloadBytes;
            public PayloadRow[] textures;
        }

        [Serializable]
        internal sealed class PayloadRow
        {
            public string fileName;
            public string name;
            public long pathId;
            public string sourceObjectHash;
            public string sourceDescriptorSha256;
            public string payloadAssetPath;
            public string payloadSha256;
            public int payloadSize;
            public int width;
            public int height;
            public int textureFormat;
            public int mipCount;
            public int sourceColorSpace;
            public ImportProfile importProfile;
            public GeneratedCopy[] generatedCopies;
        }

        [Serializable]
        internal sealed class ImportProfile
        {
            public int textureType;
            public bool sRGBTexture;
            public bool mipmapEnabled;
            public bool streamingMipmaps;
            public int streamingMipmapsPriority;
            public int filterMode;
            public int anisoLevel;
            public float mipMapBias;
            public int wrapU;
            public int wrapV;
            public int wrapW;
        }

        [Serializable]
        internal sealed class GeneratedCopy
        {
            public string assetPath;
            public string guid;
            public string pngSha256;
        }

        [Serializable]
        private sealed class TextureImportContract
        {
            public string schema;
            public int textureCount;
            public TextureImportRow[] textures;
        }

        [Serializable]
        private sealed class TextureImportRow
        {
            public string fileName;
            public long pathId;
            public string sourceObjectHash;
            public string sourceDescriptorSha256;
            public int width;
            public int height;
            public int textureFormat;
            public int mipCount;
            public int completeImageSize;
            public int sourceColorSpace;
            public ImportProfile importProfile;
            public string payloadOwner;
        }

        internal sealed class ResolvedPayload
        {
            public PayloadRow Row;
            public byte[] Bytes;
            public GraphicsFormat GraphicsFormat;
            public long PayloadWriteTicks;
            public string PayloadContractAssetPath;
            public string ImportContractAssetPath;
            public string PayloadAssetPath;
        }

        private static Dictionary<string, ResolvedPayload> PayloadsByAssetPath;
        private static string ContractSetSignature;

        public override uint GetVersion()
        {
            return 2;
        }

        private void OnPreprocessTexture()
        {
            if (!TryResolve(assetPath, true, out ResolvedPayload payload))
                return;

            context.DependsOnSourceAsset(payload.PayloadContractAssetPath);
            context.DependsOnSourceAsset(payload.ImportContractAssetPath);
            context.DependsOnSourceAsset(payload.PayloadAssetPath);
            var importer = (TextureImporter)assetImporter;
            ApplyImportProfile(importer, payload.Row.importProfile);
        }

        private void OnPostprocessTexture(Texture2D texture)
        {
            if (!TryResolve(assetPath, true, out ResolvedPayload payload))
                return;

            if (!SystemInfo.IsFormatSupported(payload.GraphicsFormat, FormatUsage.Sample))
                throw new NotSupportedException(
                    $"Pinned editor cannot sample {payload.GraphicsFormat} for {assetPath}.");
            if (!texture.Reinitialize(
                    payload.Row.width,
                    payload.Row.height,
                    payload.GraphicsFormat,
                    payload.Row.mipCount > 1))
            {
                throw new InvalidOperationException(
                    $"Unity rejected exact native allocation for {assetPath}.");
            }

            texture.LoadRawTextureData(payload.Bytes);
            ApplyRuntimeProfile(texture, payload.Row.importProfile);
            texture.Apply(false, false);

            byte[] actual = texture.GetRawTextureData<byte>().ToArray();
            string actualSha256 = Sha256(actual);
            if (!string.Equals(
                    actualSha256,
                    payload.Row.payloadSha256,
                    StringComparison.OrdinalIgnoreCase))
            {
                throw new InvalidDataException(
                    $"Exact native payload drifted for {assetPath}: expected " +
                    $"{payload.Row.payloadSha256}, got {actualSha256}.");
            }
        }

        internal static bool TryResolveForValidation(
            string textureAssetPath,
            out ResolvedPayload payload)
        {
            return TryResolve(textureAssetPath, true, out payload);
        }

        internal static PayloadContract ReloadContractForValidation()
        {
            PayloadsByAssetPath = null;
            ContractSetSignature = null;
            EnsureContract();
            return ReadContract(ContractAssetPaths[0]);
        }

        private static bool TryResolve(
            string textureAssetPath,
            bool validatePngSource,
            out ResolvedPayload payload)
        {
            payload = null;
            string normalizedPath = NormalizeAssetPath(textureAssetPath);
            if (!normalizedPath.StartsWith(AllowedPngRoot, StringComparison.OrdinalIgnoreCase))
                return false;

            EnsureContract();
            if (PayloadsByAssetPath == null ||
                !PayloadsByAssetPath.TryGetValue(normalizedPath, out payload))
            {
                payload = null;
                return false;
            }

            GeneratedCopy copy = (payload.Row.generatedCopies ?? Array.Empty<GeneratedCopy>())
                .FirstOrDefault(row => string.Equals(
                    NormalizeAssetPath(row.assetPath),
                    normalizedPath,
                    StringComparison.OrdinalIgnoreCase));
            if (copy == null)
                throw new InvalidDataException(
                    $"Payload contract does not authorize generated copy {normalizedPath}.");

            string actualGuid = AssetDatabase.AssetPathToGUID(normalizedPath);
            if (string.IsNullOrEmpty(actualGuid) ||
                !string.Equals(actualGuid, copy.guid, StringComparison.OrdinalIgnoreCase))
            {
                throw new InvalidDataException(
                    $"PNG GUID gate failed for {normalizedPath}: expected {copy.guid}, " +
                    $"got {actualGuid ?? "<null>"}.");
            }

            if (validatePngSource)
            {
                string pngPath = AbsoluteProjectPath(normalizedPath);
                if (!File.Exists(pngPath))
                    throw new FileNotFoundException("Generated PNG disappeared.", pngPath);
                string actualPngSha256 = Sha256(File.ReadAllBytes(pngPath));
                if (!string.Equals(
                        actualPngSha256,
                        copy.pngSha256,
                        StringComparison.OrdinalIgnoreCase))
                {
                    throw new InvalidDataException(
                        $"PNG source hash gate failed for {normalizedPath}: expected " +
                        $"{copy.pngSha256}, got {actualPngSha256}.");
                }
            }

            RefreshPayloadIfNeeded(payload);
            return true;
        }

        private static void EnsureContract()
        {
            var contracts = new List<KeyValuePair<string, PayloadContract>>();
            foreach (string assetPath in ContractAssetPaths)
            {
                string path = AbsoluteProjectPath(assetPath);
                if (File.Exists(path))
                    contracts.Add(new KeyValuePair<string, PayloadContract>(
                        NormalizeAssetPath(assetPath),
                        ReadContract(assetPath)));
            }
            if (contracts.Count == 0)
            {
                PayloadsByAssetPath = null;
                ContractSetSignature = null;
                return;
            }

            var signatureParts = new List<string>();
            foreach (KeyValuePair<string, PayloadContract> pair in contracts)
            {
                PayloadContract contract = pair.Value;
                if (contract == null ||
                    string.IsNullOrWhiteSpace(contract.textureImportContractAssetPath))
                {
                    throw new InvalidDataException(
                        $"Native texture payload contract is unreadable: {pair.Key}.");
                }
                string importPath = AbsoluteProjectPath(
                    contract.textureImportContractAssetPath);
                string contractPath = AbsoluteProjectPath(pair.Key);
                if (!File.Exists(importPath))
                    throw new FileNotFoundException(
                        "TextureImporter source contract disappeared.", importPath);
                signatureParts.Add(
                    contractPath + ":" + File.GetLastWriteTimeUtc(contractPath).Ticks + ":" +
                    importPath + ":" + File.GetLastWriteTimeUtc(importPath).Ticks);
                foreach (string payloadPath in (contract.textures ?? Array.Empty<PayloadRow>())
                    .Select(row => AbsoluteProjectPath(row.payloadAssetPath))
                    .Distinct(StringComparer.OrdinalIgnoreCase)
                    .OrderBy(path => path, StringComparer.OrdinalIgnoreCase))
                {
                    signatureParts.Add(
                        payloadPath + ":" +
                        (File.Exists(payloadPath)
                            ? File.GetLastWriteTimeUtc(payloadPath).Ticks
                            : -1L));
                }
            }
            string signature = string.Join("|", signatureParts);
            if (PayloadsByAssetPath != null &&
                string.Equals(signature, ContractSetSignature, StringComparison.Ordinal))
                return;

            var resolved = new Dictionary<string, ResolvedPayload>(
                contracts.Sum(pair => Math.Max(0, pair.Value.textureCount)),
                StringComparer.OrdinalIgnoreCase);
            var payloadBytesByPath = new Dictionary<string, byte[]>(
                StringComparer.OrdinalIgnoreCase);
            var payloadLayoutByPath = new Dictionary<string, string>(
                StringComparer.OrdinalIgnoreCase);
            var payloadTicksByPath = new Dictionary<string, long>(
                StringComparer.OrdinalIgnoreCase);
            foreach (KeyValuePair<string, PayloadContract> pair in contracts)
            {
                PayloadContract contract = pair.Value;
                ValidateContractHeader(contract, pair.Key);
                string importContractPath = AbsoluteProjectPath(
                    contract.textureImportContractAssetPath);
                byte[] importBytes = File.ReadAllBytes(importContractPath);
                string actualImportSha256 = Sha256(importBytes);
                if (!string.Equals(
                        actualImportSha256,
                        contract.textureImportContractSha256,
                        StringComparison.OrdinalIgnoreCase))
                {
                    throw new InvalidDataException(
                        "TextureImporter source contract hash gate failed: expected " +
                        $"{contract.textureImportContractSha256}, got {actualImportSha256}.");
                }

                var importContract = JsonUtility.FromJson<TextureImportContract>(
                    System.Text.Encoding.UTF8.GetString(importBytes));
                if (importContract == null ||
                    !string.Equals(
                        importContract.schema,
                        ExpectedImportSchema,
                        StringComparison.Ordinal) ||
                    importContract.textureCount <= 0 ||
                    importContract.textures == null ||
                    importContract.textures.Length != importContract.textureCount)
                {
                    throw new InvalidDataException(
                        "TextureImporter source contract failed its structural gate.");
                }
                var importsByFile = importContract.textures.ToDictionary(
                    row => row.fileName,
                    StringComparer.OrdinalIgnoreCase);

                // Generated blobs are rebuildable and may be absent after a
                // project clean. Disable only that incomplete contract. A
                // separate source-closed contract must remain independently
                // available, and the payload timestamps in the cache signature
                // make a later rebuild visible without touching either JSON.
                if (contract.textures.Any(row =>
                        !File.Exists(AbsoluteProjectPath(row.payloadAssetPath))))
                    continue;

                long contractLogicalBytes = 0;
                long contractUniqueBytes = 0;
                int contractCopies = 0;
                var contractPayloadPaths = new HashSet<string>(
                    StringComparer.OrdinalIgnoreCase);
                foreach (PayloadRow row in contract.textures)
                {
                    ValidatePayloadRow(row, importsByFile);
                    string payloadPath = AbsoluteProjectPath(row.payloadAssetPath);
                    string payloadLayout = PayloadLayoutSignature(row);
                    if (payloadLayoutByPath.TryGetValue(
                            payloadPath,
                            out string existingLayout) &&
                        !string.Equals(
                            payloadLayout,
                            existingLayout,
                            StringComparison.Ordinal))
                    {
                        throw new InvalidDataException(
                            $"Deduplicated payload crossed an incompatible texture " +
                            $"layout: {row.payloadAssetPath}.");
                    }
                    if (!payloadBytesByPath.TryGetValue(payloadPath, out byte[] bytes))
                    {
                        bytes = File.ReadAllBytes(payloadPath);
                        payloadBytesByPath.Add(payloadPath, bytes);
                        payloadLayoutByPath.Add(payloadPath, payloadLayout);
                        payloadTicksByPath.Add(
                            payloadPath,
                            File.GetLastWriteTimeUtc(payloadPath).Ticks);
                    }
                    ValidatePayloadBytes(row, bytes, payloadPath);
                    var resolvedPayload = new ResolvedPayload {
                            Row = row,
                            Bytes = bytes,
                            GraphicsFormat = ResolveGraphicsFormat(row),
                            PayloadWriteTicks = payloadTicksByPath[payloadPath],
                            PayloadContractAssetPath = pair.Key,
                            ImportContractAssetPath = NormalizeAssetPath(
                                contract.textureImportContractAssetPath),
                            PayloadAssetPath = NormalizeAssetPath(row.payloadAssetPath),
                        };
                    foreach (GeneratedCopy copy in row.generatedCopies)
                    {
                        string copyPath = NormalizeAssetPath(copy.assetPath);
                        if (!resolved.TryAdd(copyPath, resolvedPayload))
                        {
                            throw new InvalidDataException(
                                $"Duplicate generated texture asset path across contracts: " +
                                $"{copyPath}.");
                        }
                    }
                    contractLogicalBytes += row.payloadSize;
                    contractCopies += row.generatedCopies.Length;
                    if (contractPayloadPaths.Add(payloadPath))
                        contractUniqueBytes += bytes.LongLength;
                }
                if (contractLogicalBytes != contract.logicalPayloadBytes ||
                    contractPayloadPaths.Count != contract.uniquePayloadCount ||
                    contractUniqueBytes != contract.uniquePayloadBytes ||
                    contractCopies != contract.generatedCopyCount)
                {
                    throw new InvalidDataException(
                        $"Native payload totals do not match contract {pair.Key}.");
                }
            }

            PayloadsByAssetPath = resolved;
            ContractSetSignature = signature;
        }

        private static void ValidateContractHeader(PayloadContract contract, string path)
        {
            if (!string.Equals(contract.schema, ExpectedSchema, StringComparison.Ordinal) ||
                !string.Equals(
                    contract.status,
                    "source_closed_current_build",
                    StringComparison.Ordinal) ||
                contract.textureCount <= 0 ||
                contract.generatedCopyCount <= 0 ||
                contract.logicalPayloadBytes <= 0 ||
                contract.uniquePayloadCount <= 0 ||
                contract.uniquePayloadCount > contract.textureCount ||
                contract.uniquePayloadBytes <= 0 ||
                contract.uniquePayloadBytes > contract.logicalPayloadBytes ||
                contract.deduplicatedPayloadBytes !=
                    contract.logicalPayloadBytes - contract.uniquePayloadBytes ||
                contract.textures == null ||
                contract.textures.Length != contract.textureCount)
            {
                throw new InvalidDataException(
                    $"Native texture payload contract is incomplete: {path}.");
            }
        }

        private static PayloadContract ReadContract(string assetPath)
        {
            string path = AbsoluteProjectPath(assetPath);
            if (!File.Exists(path))
                return null;
            return JsonUtility.FromJson<PayloadContract>(File.ReadAllText(path));
        }

        private static void ValidatePayloadRow(
            PayloadRow row,
            Dictionary<string, TextureImportRow> importsByFile)
        {
            if (row == null ||
                string.IsNullOrWhiteSpace(row.fileName) ||
                string.IsNullOrWhiteSpace(row.payloadAssetPath) ||
                row.generatedCopies == null ||
                row.generatedCopies.Length == 0 ||
                row.importProfile == null)
            {
                throw new InvalidDataException("Native payload contract contains an empty row.");
            }
            if (!AllowedPayloadRoots.Any(root => row.payloadAssetPath.StartsWith(
                    root,
                    StringComparison.OrdinalIgnoreCase)) ||
                !string.Equals(
                    Path.GetExtension(row.payloadAssetPath),
                    ".bytes",
                    StringComparison.OrdinalIgnoreCase))
            {
                throw new InvalidDataException(
                    $"Payload path escaped its generated root: {row.payloadAssetPath}.");
            }
            if (!importsByFile.TryGetValue(row.fileName, out TextureImportRow source))
                throw new InvalidDataException(
                    $"Missing TextureImporter source gate for {row.fileName}.");

            bool sourceMatches =
                source.pathId == row.pathId &&
                string.Equals(
                    source.sourceObjectHash,
                    row.sourceObjectHash,
                    StringComparison.OrdinalIgnoreCase) &&
                string.Equals(
                    source.sourceDescriptorSha256,
                    row.sourceDescriptorSha256,
                    StringComparison.OrdinalIgnoreCase) &&
                source.width == row.width &&
                source.height == row.height &&
                source.textureFormat == row.textureFormat &&
                source.mipCount == row.mipCount &&
                source.completeImageSize == row.payloadSize &&
                source.sourceColorSpace == row.sourceColorSpace &&
                string.Equals(
                    source.payloadOwner,
                    nameof(EndfieldNativeTexturePayloadPostprocessor),
                    StringComparison.Ordinal) &&
                ImportProfilesEqual(source.importProfile, row.importProfile);
            if (!sourceMatches)
                throw new InvalidDataException(
                    $"Original Texture2D source gate drifted for {row.fileName}.");

            foreach (GeneratedCopy copy in row.generatedCopies)
            {
                string copyPath = NormalizeAssetPath(copy.assetPath);
                if (!copyPath.StartsWith(AllowedPngRoot, StringComparison.OrdinalIgnoreCase) ||
                    !string.Equals(
                        Path.GetFileName(copyPath),
                        row.fileName,
                        StringComparison.OrdinalIgnoreCase) ||
                    string.IsNullOrWhiteSpace(copy.guid) ||
                    copy.guid.Length != 32 ||
                    string.IsNullOrWhiteSpace(copy.pngSha256) ||
                    copy.pngSha256.Length != 64)
                {
                    throw new InvalidDataException(
                        $"Generated-copy source gate is invalid for {row.fileName}.");
                }
            }
        }

        private static void RefreshPayloadIfNeeded(ResolvedPayload payload)
        {
            string path = AbsoluteProjectPath(payload.Row.payloadAssetPath);
            if (!File.Exists(path))
                throw new FileNotFoundException("Exact native payload disappeared.", path);
            long ticks = File.GetLastWriteTimeUtc(path).Ticks;
            if (ticks == payload.PayloadWriteTicks)
                return;
            byte[] bytes = File.ReadAllBytes(path);
            ValidatePayloadBytes(payload.Row, bytes, path);
            payload.Bytes = bytes;
            payload.PayloadWriteTicks = ticks;
        }

        private static void ValidatePayloadBytes(
            PayloadRow row,
            byte[] bytes,
            string payloadPath)
        {
            if (bytes.Length != row.payloadSize)
                throw new InvalidDataException(
                    $"Payload size gate failed for {payloadPath}: expected " +
                    $"{row.payloadSize}, got {bytes.Length}.");
            string actualSha256 = Sha256(bytes);
            if (!string.Equals(
                    actualSha256,
                    row.payloadSha256,
                    StringComparison.OrdinalIgnoreCase))
            {
                throw new InvalidDataException(
                    $"Payload hash gate failed for {payloadPath}: expected " +
                    $"{row.payloadSha256}, got {actualSha256}.");
            }
        }

        private static GraphicsFormat ResolveGraphicsFormat(PayloadRow row)
        {
            switch (row.textureFormat)
            {
                case 4:
                    return row.sourceColorSpace == 1
                        ? GraphicsFormat.R8G8B8A8_SRGB
                        : GraphicsFormat.R8G8B8A8_UNorm;
                case 10:
                    return row.sourceColorSpace == 1
                        ? GraphicsFormat.RGBA_DXT1_SRGB
                        : GraphicsFormat.RGBA_DXT1_UNorm;
                case 25:
                    return row.sourceColorSpace == 1
                        ? GraphicsFormat.RGBA_BC7_SRGB
                        : GraphicsFormat.RGBA_BC7_UNorm;
                case 27:
                    return GraphicsFormat.RG_BC5_UNorm;
                default:
                    throw new NotSupportedException(
                        $"Unsupported installed TextureFormat {row.textureFormat} " +
                        $"for {row.fileName}.");
            }
        }

        private static string PayloadLayoutSignature(PayloadRow row)
        {
            return string.Join(
                ":",
                row.width,
                row.height,
                row.textureFormat,
                row.mipCount,
                row.sourceColorSpace,
                row.payloadSize);
        }

        private static void ApplyImportProfile(
            TextureImporter importer,
            ImportProfile profile)
        {
            importer.textureType = (TextureImporterType)profile.textureType;
            importer.textureShape = TextureImporterShape.Texture2D;
            importer.sRGBTexture = profile.sRGBTexture;
            importer.mipmapEnabled = profile.mipmapEnabled;
            importer.streamingMipmaps = profile.streamingMipmaps;
            importer.streamingMipmapsPriority = profile.streamingMipmapsPriority;
            importer.filterMode = (FilterMode)profile.filterMode;
            importer.anisoLevel = profile.anisoLevel;
            importer.mipMapBias = profile.mipMapBias;
            importer.wrapModeU = (TextureWrapMode)profile.wrapU;
            importer.wrapModeV = (TextureWrapMode)profile.wrapV;
            importer.wrapModeW = (TextureWrapMode)profile.wrapW;
            importer.alphaIsTransparency = false;
            importer.npotScale = TextureImporterNPOTScale.None;
            importer.textureCompression = TextureImporterCompression.Uncompressed;
            importer.isReadable = true;
        }

        private static void ApplyRuntimeProfile(Texture texture, ImportProfile profile)
        {
            texture.filterMode = (FilterMode)profile.filterMode;
            texture.anisoLevel = profile.anisoLevel;
            texture.mipMapBias = profile.mipMapBias;
            texture.wrapModeU = (TextureWrapMode)profile.wrapU;
            texture.wrapModeV = (TextureWrapMode)profile.wrapV;
            texture.wrapModeW = (TextureWrapMode)profile.wrapW;
        }

        private static bool ImportProfilesEqual(ImportProfile left, ImportProfile right)
        {
            return left != null &&
                right != null &&
                left.textureType == right.textureType &&
                left.sRGBTexture == right.sRGBTexture &&
                left.mipmapEnabled == right.mipmapEnabled &&
                left.streamingMipmaps == right.streamingMipmaps &&
                left.streamingMipmapsPriority == right.streamingMipmapsPriority &&
                left.filterMode == right.filterMode &&
                left.anisoLevel == right.anisoLevel &&
                Math.Abs(left.mipMapBias - right.mipMapBias) < 0.000001f &&
                left.wrapU == right.wrapU &&
                left.wrapV == right.wrapV &&
                left.wrapW == right.wrapW;
        }

        private static string NormalizeAssetPath(string path)
        {
            return (path ?? string.Empty).Replace('\\', '/');
        }

        private static string AbsoluteProjectPath(string assetPath)
        {
            string projectRoot = Directory.GetParent(Application.dataPath).FullName;
            return Path.GetFullPath(Path.Combine(
                projectRoot,
                NormalizeAssetPath(assetPath).Replace('/', Path.DirectorySeparatorChar)));
        }

        internal static string Sha256(byte[] data)
        {
            using (var hash = SHA256.Create())
                return string.Concat(
                    hash.ComputeHash(data).Select(value => value.ToString("x2")));
        }
    }

    public static class EndfieldNativeTexturePayloadValidator
    {
        [Serializable]
        private sealed class ValidationReport
        {
            public string schema = "endfield.native-texture-payload-validation.v2";
            public string unityVersion;
            public string graphicsDeviceType;
            public int textureObjectCount;
            public int generatedCopyCount;
            public long logicalPayloadBytes;
            public int uniquePayloadCount;
            public long uniquePayloadBytes;
            public long deduplicatedPayloadBytes;
            public bool passed;
            public List<ValidationRow> textures = new List<ValidationRow>();
        }

        [Serializable]
        private sealed class ValidationRow
        {
            public string assetPath;
            public string expectedGuid;
            public string actualGuid;
            public string expectedSha256;
            public string actualSha256;
            public string graphicsFormat;
            public int width;
            public int height;
            public int mipCount;
            public int rawSize;
            public long localFileId;
            public bool exactPayload;
            public bool exactGuid;
            public bool stablePPtrIdentity;
            public bool exactImportContract;
            public string error;
        }

        public static void ValidateCommandLine()
        {
            EndfieldNativeTexturePayloadPostprocessor.PayloadContract contract =
                EndfieldNativeTexturePayloadPostprocessor.ReloadContractForValidation();
            if (contract == null)
                throw new FileNotFoundException(
                    "High-impact native texture payload contract was not found.");

            var paths = contract.textures
                .SelectMany(row => row.generatedCopies.Select(copy => copy.assetPath))
                .OrderBy(path => path, StringComparer.OrdinalIgnoreCase)
                .ToArray();
            foreach (string path in paths)
            {
                AssetDatabase.ImportAsset(
                    path,
                    ImportAssetOptions.ForceSynchronousImport |
                    ImportAssetOptions.ForceUpdate);
            }

            var report = new ValidationReport
            {
                unityVersion = Application.unityVersion,
                graphicsDeviceType = SystemInfo.graphicsDeviceType.ToString(),
                textureObjectCount = contract.textureCount,
                generatedCopyCount = paths.Length,
                logicalPayloadBytes = contract.logicalPayloadBytes,
                uniquePayloadCount = contract.uniquePayloadCount,
                uniquePayloadBytes = contract.uniquePayloadBytes,
                deduplicatedPayloadBytes = contract.deduplicatedPayloadBytes,
            };
            foreach (string path in paths)
                report.textures.Add(ValidateOne(path));

            report.passed =
                report.textureObjectCount == contract.textures.Length &&
                report.generatedCopyCount == contract.generatedCopyCount &&
                report.logicalPayloadBytes == contract.logicalPayloadBytes &&
                report.uniquePayloadCount == contract.uniquePayloadCount &&
                report.uniquePayloadBytes == contract.uniquePayloadBytes &&
                report.deduplicatedPayloadBytes ==
                    contract.logicalPayloadBytes - contract.uniquePayloadBytes &&
                report.textures.Count == contract.generatedCopyCount &&
                report.textures.All(row =>
                    string.IsNullOrEmpty(row.error) &&
                    row.exactPayload &&
                    row.exactGuid &&
                    row.stablePPtrIdentity &&
                    row.exactImportContract);

            string projectRoot = Directory.GetParent(Application.dataPath).FullName;
            string outputDirectory = Path.Combine(
                projectRoot,
                "scratch",
                "character_recovery",
                "priority_native_surface_payload");
            Directory.CreateDirectory(outputDirectory);
            string outputPath = Path.Combine(
                outputDirectory,
                "main_project_unity_validation.json");
            File.WriteAllText(
                outputPath,
                JsonUtility.ToJson(report, true) + Environment.NewLine);
            Debug.Log(
                $"Validated exact native character payloads: objects=" +
                $"{report.textureObjectCount}, copies={report.generatedCopyCount}, " +
                $"logicalBytes={report.logicalPayloadBytes}, " +
                $"uniquePayloads={report.uniquePayloadCount}, " +
                $"uniqueBytes={report.uniquePayloadBytes}, passed={report.passed}.");
            if (!report.passed)
                throw new InvalidOperationException(
                    "Native texture payload validation failed; see " + outputPath);
        }

        private static ValidationRow ValidateOne(string path)
        {
            var row = new ValidationRow { assetPath = path };
            try
            {
                if (!EndfieldNativeTexturePayloadPostprocessor.TryResolveForValidation(
                        path,
                        out EndfieldNativeTexturePayloadPostprocessor.ResolvedPayload payload))
                {
                    throw new InvalidOperationException("Payload contract did not resolve.");
                }
                EndfieldNativeTexturePayloadPostprocessor.GeneratedCopy copy =
                    payload.Row.generatedCopies.First(item => string.Equals(
                        item.assetPath,
                        path,
                        StringComparison.OrdinalIgnoreCase));
                row.expectedGuid = copy.guid;
                row.actualGuid = AssetDatabase.AssetPathToGUID(path);
                row.expectedSha256 = payload.Row.payloadSha256;

                TextureImporter importer = AssetImporter.GetAtPath(path) as TextureImporter;
                Texture2D texture = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
                if (importer == null || texture == null)
                    throw new InvalidOperationException(
                        "TextureImporter/Texture2D did not resolve.");

                byte[] actual = texture.GetRawTextureData<byte>().ToArray();
                row.actualSha256 = EndfieldNativeTexturePayloadPostprocessor.Sha256(actual);
                row.graphicsFormat = texture.graphicsFormat.ToString();
                row.width = texture.width;
                row.height = texture.height;
                row.mipCount = texture.mipmapCount;
                row.rawSize = actual.Length;
                row.exactPayload = actual.SequenceEqual(payload.Bytes) &&
                    string.Equals(
                        row.actualSha256,
                        row.expectedSha256,
                        StringComparison.OrdinalIgnoreCase);
                row.exactGuid = string.Equals(
                    row.actualGuid,
                    row.expectedGuid,
                    StringComparison.OrdinalIgnoreCase);
                if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(
                        texture,
                        out string objectGuid,
                        out long localFileId))
                {
                    throw new InvalidOperationException(
                        "Texture GUID/local-file-ID did not resolve.");
                }
                row.localFileId = localFileId;
                row.stablePPtrIdentity =
                    row.exactGuid &&
                    string.Equals(
                        objectGuid,
                        row.expectedGuid,
                        StringComparison.OrdinalIgnoreCase) &&
                    localFileId == 2800000;

                EndfieldNativeTexturePayloadPostprocessor.ImportProfile profile =
                    payload.Row.importProfile;
                row.exactImportContract =
                    texture.width == payload.Row.width &&
                    texture.height == payload.Row.height &&
                    texture.mipmapCount == payload.Row.mipCount &&
                    actual.Length == payload.Row.payloadSize &&
                    texture.graphicsFormat == payload.GraphicsFormat &&
                    texture.filterMode == (FilterMode)profile.filterMode &&
                    texture.anisoLevel == profile.anisoLevel &&
                    Math.Abs(texture.mipMapBias - profile.mipMapBias) < 0.000001f &&
                    texture.wrapModeU == (TextureWrapMode)profile.wrapU &&
                    texture.wrapModeV == (TextureWrapMode)profile.wrapV &&
                    texture.wrapModeW == (TextureWrapMode)profile.wrapW &&
                    importer.textureType == (TextureImporterType)profile.textureType &&
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
                    importer.isReadable;
            }
            catch (Exception ex)
            {
                row.error = ex.GetType().Name + ": " + ex.Message;
            }
            return row;
        }
    }
}
