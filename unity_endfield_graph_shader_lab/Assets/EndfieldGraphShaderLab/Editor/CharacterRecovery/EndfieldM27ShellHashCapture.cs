using System;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Captures and validates the dedicated M27 shell's Unity-compiled D3D11
    /// stage hashes. The native callback substitutes only stage+SHA identities
    /// pinned from a reserved-variant callback-inventory delta.
    /// </summary>
    public static class EndfieldM27ShellHashCapture
    {
        private const string NativeLibrary = "OriginalDxbcSwapPlugin";
        private const string ShaderAsset =
            "Assets/EndfieldGraphShaderLab/Shaders/Diagnostics/" +
            "EndfieldEndminfM27ExactAbiShell.shader";
        private const string OutputEnvironment =
            "ENDFIELD_M27_SHELL_HASH_OUTPUT";
        private const string M14ShaderAsset =
            "Assets/EndfieldGraphShaderLab/Shaders/Diagnostics/" +
            "EndfieldEndminfM14ExactAbiShell.shader";
        private const string M14OutputEnvironment =
            "ENDFIELD_M14_SHELL_HASH_OUTPUT";

        public static void PreparePinnedRuntimeVariant()
        {
            if (SystemInfo.graphicsDeviceType != GraphicsDeviceType.Direct3D11)
                throw new InvalidOperationException(
                    "Exact M27 runtime preparation requires Direct3D11.");
            if (Native.GetContractVersion() != 2 ||
                Native.GetM27RegistryReady() != 1)
            {
                throw new InvalidOperationException(
                    "The exact M27 stage+SHA registry is not ready.");
            }
            if (Native.SetM27SubstitutionArmed(1) != 1)
                throw new InvalidOperationException(
                    "The exact M27 compiler route could not be armed.");
            try
            {
                ForceRecompileWhileArmed();
                ForceLoadReservedVariant();
                uint matches = Native.GetM27MatchCount();
                uint vertexSwaps = Native.GetVertexSwapCount();
                uint pixelSwaps = Native.GetPixelSwapCount();
                uint failures = Native.GetFailureCount();
                if (matches != 2 || vertexSwaps != 1 || pixelSwaps != 1 ||
                    failures != 0)
                {
                    throw new InvalidOperationException(
                        "Exact M27 runtime variant preparation failed: " +
                        $"matches={matches}, vertexSwaps={vertexSwaps}, " +
                        $"pixelSwaps={pixelSwaps}, failures={failures}.");
                }
                Debug.Log(
                    "Prepared exact Endminf M27 runtime variant: " +
                    "stage+SHA substitutions=2, VS=10/9, PS=10/5.");
            }
            finally
            {
                Native.SetM27SubstitutionArmed(0);
            }
        }

        public static void PrepareRawRuntimeVariant()
        {
            if (SystemInfo.graphicsDeviceType != GraphicsDeviceType.Direct3D11)
                throw new InvalidOperationException(
                    "Raw M27 shell preparation requires Direct3D11.");
            Native.SetM27SubstitutionArmed(0);
            ForceRecompileWhileArmed();
            ForceLoadReservedVariant();
            uint matches = Native.GetM27MatchCount();
            uint vertexSwaps = Native.GetVertexSwapCount();
            uint pixelSwaps = Native.GetPixelSwapCount();
            if (matches != 0 || vertexSwaps != 0 || pixelSwaps != 0)
            {
                throw new InvalidOperationException(
                    "Raw M27 shell preparation unexpectedly substituted a " +
                    $"stage: matches={matches}, vertexSwaps={vertexSwaps}, " +
                    $"pixelSwaps={pixelSwaps}.");
            }
            Debug.Log(
                "Prepared unsubstituted Endminf M27 ABI shell control: " +
                "stage+SHA substitutions=0.");
        }

        [Serializable]
        private sealed class Report
        {
            public string schema;
            public string status;
            public string unityVersion;
            public string graphicsDeviceType;
            public string shaderAsset;
            public string shaderSourceSha256;
            public uint contractVersion;
            public uint registryReady;
            public uint callbackCount;
            public uint mismatchCount;
            public uint matchCount;
            public uint variantHashConflictCount;
            public uint maximumVertexInputs;
            public uint maximumVertexOutputs;
            public uint maximumPixelInputs;
            public uint maximumPixelOutputs;
            public string vertexShellSha256;
            public string pixelShellSha256;
            public CallbackObservation[] callbackObservations;
        }

        [Serializable]
        private sealed class CallbackObservation
        {
            public uint stage;
            public uint byteCodeSize;
            public uint inputParameters;
            public uint outputParameters;
            public uint boundResources;
            public uint constantBuffer0Bytes;
            public uint constantBuffer1Bytes;
            public uint constantBuffer2Bytes;
            public uint constantBuffer3Bytes;
            public uint constantBuffer4Bytes;
            public string textureSlotMask;
            public string samplerSlotMask;
            public string sha256;
        }

        public static void Run()
        {
            string output = Environment.GetEnvironmentVariable(
                OutputEnvironment);
            if (string.IsNullOrWhiteSpace(output))
            {
                output = Path.GetFullPath(Path.Combine(
                    Application.dataPath,
                    "..",
                    "scratch",
                    "character_recovery",
                    "m27_hgbuffer",
                    "shell_hashes.json"));
            }
            else
            {
                output = Path.GetFullPath(output);
            }

            try
            {
                if (SystemInfo.graphicsDeviceType !=
                    GraphicsDeviceType.Direct3D11)
                {
                    throw new InvalidOperationException(
                        "M27 shell hash capture requires Direct3D11; actual=" +
                        SystemInfo.graphicsDeviceType + ".");
                }
                if (Native.GetContractVersion() != 2)
                    throw new InvalidOperationException(
                        "Original DXBC plugin contract version drifted.");
                if (Native.SetM27SubstitutionArmed(1) != 1)
                    throw new InvalidOperationException(
                        "M27 substitution callback could not be armed.");

                ForceRecompileWhileArmed();
                ForceLoadReservedVariant();

                uint configureCount = Native.GetConfigureCount();
                uint callbackCountBeforeRead = Native.GetCallbackCount();
                uint mismatchCountBeforeRead = Native.GetM27MismatchCount();
                uint vertexSignature = Native.GetM27MaximumSignatureCounts(1);
                uint pixelSignature = Native.GetM27MaximumSignatureCounts(2);
                Debug.Log(
                    "M27 shell compiler-extension counters after import: " +
                    $"configure={configureCount}, " +
                    $"callbacks={callbackCountBeforeRead}, " +
                    $"mismatches={mismatchCountBeforeRead}, " +
                    $"maxVS={vertexSignature >> 16}/{vertexSignature & 0xffff}, " +
                    $"maxPS={pixelSignature >> 16}/{pixelSignature & 0xffff}.");
                if (configureCount == 0)
                {
                    throw new InvalidOperationException(
                        "Unity did not configure the native shader compiler " +
                        "extension in this editor process; a shader reimport " +
                        "cannot observe M27 shell hashes.");
                }
                if (callbackCountBeforeRead < 2)
                {
                    throw new InvalidOperationException(
                        "Unity configured the shader compiler extension but " +
                        "did not request both reserved M27 shader stages " +
                        "during import: callbacks=" +
                        callbackCountBeforeRead + ".");
                }

                byte[] vertex = ReadObservedHash(1);
                byte[] pixel = ReadObservedHash(2);
                uint callbackCount = Native.GetCallbackCount();
                uint mismatchCount = Native.GetM27MismatchCount();
                uint matchCount = Native.GetM27MatchCount();
                uint variantHashConflictCount =
                    Native.GetM27VariantHashConflictCount();
                uint registryReady = Native.GetM27RegistryReady();
                CallbackObservation[] callbackObservations =
                    ReadCallbackObservations();
                bool bothStagesObserved =
                    vertex.Any(value => value != 0) &&
                    pixel.Any(value => value != 0);
                bool validState = registryReady != 0
                    ? bothStagesObserved && matchCount >= 2 &&
                        mismatchCount == 0 &&
                        variantHashConflictCount == 0 && callbackCount >= 2
                    : matchCount == 0 &&
                        (!bothStagesObserved || variantHashConflictCount == 0) &&
                        callbackCount >= 2;
                if (!validState)
                {
                    throw new InvalidOperationException(
                        "M27 shell substitution state failed validation: " +
                        $"ready={registryReady}, matches={matchCount}, " +
                        $"mismatches={mismatchCount}, callbacks={callbackCount}, " +
                        $"variantHashConflicts={variantHashConflictCount}.");
                }

                string shaderPath = Path.GetFullPath(Path.Combine(
                    Application.dataPath,
                    "..",
                    ShaderAsset));
                var report = new Report
                {
                    schema = "endfield.m27-unity-shell-hashes.v1",
                    status = registryReady != 0 && bothStagesObserved
                        ? "pinned_substitution_activated"
                        : bothStagesObserved
                            ? "observed_unpinned_fail_closed"
                            : "unity_shell_abi_mismatch_fail_closed",
                    unityVersion = Application.unityVersion,
                    graphicsDeviceType = SystemInfo.graphicsDeviceType.ToString(),
                    shaderAsset = ShaderAsset,
                    shaderSourceSha256 = HashFile(shaderPath),
                    contractVersion = Native.GetContractVersion(),
                    registryReady = registryReady,
                    callbackCount = callbackCount,
                    mismatchCount = mismatchCount,
                    matchCount = matchCount,
                    variantHashConflictCount = variantHashConflictCount,
                    maximumVertexInputs = vertexSignature >> 16,
                    maximumVertexOutputs = vertexSignature & 0xffff,
                    maximumPixelInputs = pixelSignature >> 16,
                    maximumPixelOutputs = pixelSignature & 0xffff,
                    vertexShellSha256 = vertex.Any(value => value != 0)
                        ? Hex(vertex)
                        : string.Empty,
                    pixelShellSha256 = pixel.Any(value => value != 0)
                        ? Hex(pixel)
                        : string.Empty,
                    callbackObservations = callbackObservations,
                };
                Directory.CreateDirectory(Path.GetDirectoryName(output));
                File.WriteAllText(output, JsonUtility.ToJson(report, true));
                Debug.Log(
                    "Validated M27 Unity shell state: status=" +
                    report.status + ", VS=" +
                    report.vertexShellSha256 + ", PS=" +
                    report.pixelShellSha256 + ", output=" + output + ".");
                Native.SetM27SubstitutionArmed(0);
                EditorApplication.Exit(0);
            }
            catch (Exception exception)
            {
                try
                {
                    Native.SetM27SubstitutionArmed(0);
                }
                catch
                {
                    // Preserve the original actionable capture failure.
                }
                Debug.LogException(exception);
                EditorApplication.Exit(1);
            }
        }

        public static void RunM14Observation()
        {
            string output = Environment.GetEnvironmentVariable(
                M14OutputEnvironment);
            if (string.IsNullOrWhiteSpace(output))
            {
                output = Path.GetFullPath(Path.Combine(
                    Application.dataPath,
                    "..",
                    "scratch",
                    "character_recovery",
                    "m14_vfxbasev2",
                    "shell_hash_observation.json"));
            }
            else
            {
                output = Path.GetFullPath(output);
            }

            try
            {
                if (SystemInfo.graphicsDeviceType !=
                    GraphicsDeviceType.Direct3D11)
                {
                    throw new InvalidOperationException(
                        "M14 shell observation requires Direct3D11; actual=" +
                        SystemInfo.graphicsDeviceType + ".");
                }
                if (Native.GetContractVersion() != 2)
                    throw new InvalidOperationException(
                        "Original DXBC plugin contract version drifted.");
                if (Native.SetM27SubstitutionArmed(1) != 1)
                    throw new InvalidOperationException(
                        "The reserved exact-stage callback could not be armed.");

                ForceRecompileWhileArmed(M14ShaderAsset);
                ForceLoadReservedVariant(M14ShaderAsset);
                CallbackObservation[] observations = ReadCallbackObservations();
                Directory.CreateDirectory(Path.GetDirectoryName(output));
                File.WriteAllText(
                    output + ".callbacks.json",
                    JsonUtility.ToJson(new Report
                    {
                        schema = "endfield.m14-unity-shell-callbacks.v1",
                        status = "raw_callback_inventory",
                        callbackObservations = observations,
                    }, true));
                CallbackObservation[] vertexCandidates = observations.Where(value =>
                    value.stage == 1 && value.inputParameters == 8 &&
                    value.outputParameters == 7).ToArray();
                CallbackObservation[] pixelCandidates = observations.Where(value =>
                    value.stage == 2 && value.inputParameters == 7 &&
                    value.outputParameters == 2).ToArray();
                CallbackObservation vertex = vertexCandidates.Single(value =>
                    value.byteCodeSize == 1424 && value.sha256 ==
                    "0dc6bf259f8510c1e280160543cab0b591485a34bf226c048bf3f245fdad6714");
                CallbackObservation pixel = pixelCandidates.Single(value =>
                    value.byteCodeSize == 3192 && value.sha256 ==
                    "465a86bc25083537c7cfa6d8f481253d907a29e4097fc5ce378d080083e25b57");
                uint matchCount = Native.GetM27MatchCount();
                uint vertexSwaps = Native.GetVertexSwapCount();
                uint pixelSwaps = Native.GetPixelSwapCount();
                uint failures = Native.GetFailureCount();
                if (matchCount < 2 || vertexSwaps == 0 ||
                    vertexSwaps != pixelSwaps ||
                    matchCount != vertexSwaps + pixelSwaps || failures != 0)
                {
                    throw new InvalidOperationException(
                        "Pinned M14 shell substitution failed validation: " +
                        $"matches={matchCount}, vertexSwaps={vertexSwaps}, " +
                        $"pixelSwaps={pixelSwaps}, failures={failures}.");
                }
                var report = new Report
                {
                    schema = "endfield.m14-unity-shell-hashes.v1",
                    status = "pinned_substitution_activated",
                    unityVersion = Application.unityVersion,
                    graphicsDeviceType = SystemInfo.graphicsDeviceType.ToString(),
                    shaderAsset = M14ShaderAsset,
                    shaderSourceSha256 = HashFile(Path.GetFullPath(Path.Combine(
                        Application.dataPath, "..", M14ShaderAsset))),
                    contractVersion = Native.GetContractVersion(),
                    registryReady = Native.GetM27RegistryReady(),
                    callbackCount = Native.GetCallbackCount(),
                    mismatchCount = Native.GetM27MismatchCount(),
                    matchCount = matchCount,
                    variantHashConflictCount =
                        Native.GetM27VariantHashConflictCount(),
                    maximumVertexInputs = vertex.inputParameters,
                    maximumVertexOutputs = vertex.outputParameters,
                    maximumPixelInputs = pixel.inputParameters,
                    maximumPixelOutputs = pixel.outputParameters,
                    vertexShellSha256 = vertex.sha256,
                    pixelShellSha256 = pixel.sha256,
                    callbackObservations = observations,
                };
                Directory.CreateDirectory(Path.GetDirectoryName(output));
                File.WriteAllText(output, JsonUtility.ToJson(report, true));
                Debug.Log(
                    "Validated pinned M14 Unity shell hashes: VS=" +
                    vertex.sha256 + ", PS=" + pixel.sha256 +
                    ", output=" + output + ".");
                Native.SetM27SubstitutionArmed(0);
                EditorApplication.Exit(0);
            }
            catch (Exception exception)
            {
                try
                {
                    Native.SetM27SubstitutionArmed(0);
                }
                catch
                {
                    // Preserve the original actionable observation failure.
                }
                Debug.LogException(exception);
                EditorApplication.Exit(1);
            }
        }

        private static byte[] ReadObservedHash(uint stage)
        {
            byte[] value = new byte[32];
            uint written = Native.GetM27ObservedShellSha256(
                    stage,
                    value,
                    (uint)value.Length);
            if (written != value.Length)
            {
                throw new InvalidOperationException(
                    "Could not read observed M27 stage " + stage +
                    " hash: bytesWritten=" + written + ".");
            }
            return value;
        }

        private static void ForceRecompileWhileArmed()
        {
            ForceRecompileWhileArmed(ShaderAsset);
        }

        private static void ForceRecompileWhileArmed(string shaderAsset)
        {
            string shaderPath = Path.GetFullPath(Path.Combine(
                Application.dataPath,
                "..",
                shaderAsset));
            byte[] original = File.ReadAllBytes(shaderPath);
            byte[] touch = System.Text.Encoding.ASCII.GetBytes(
                "\n// ENDFIELD_M27_ARMED_CAPTURE_REIMPORT\n");
            var modified = new byte[original.Length + touch.Length];
            Buffer.BlockCopy(original, 0, modified, 0, original.Length);
            Buffer.BlockCopy(touch, 0, modified, original.Length, touch.Length);
            try
            {
                File.WriteAllBytes(shaderPath, modified);
                AssetDatabase.ImportAsset(
                    shaderAsset,
                    ImportAssetOptions.ForceUpdate |
                    ImportAssetOptions.ForceSynchronousImport);
            }
            finally
            {
                File.WriteAllBytes(shaderPath, original);
            }
        }

        private static void ForceLoadReservedVariant()
        {
            ForceLoadReservedVariant(ShaderAsset);
        }

        private static void ForceLoadReservedVariant(string shaderAsset)
        {
            Shader shader = AssetDatabase.LoadAssetAtPath<Shader>(shaderAsset);
            if (shader == null)
                throw new InvalidOperationException(
                    "Could not load the dedicated M27 shell shader.");
            ShaderUtil.ClearCachedData(shader);
            var material = new Material(shader)
            {
                hideFlags = HideFlags.HideAndDontSave,
            };
            try
            {
                material.EnableKeyword("ENDFIELD_ORIGINAL_DXBC_M27_EXACT");
                if (!material.SetPass(0))
                {
                    string messages = string.Join(
                        " | ",
                        ShaderUtil.GetShaderMessages(shader).Select(value =>
                            value.severity + ": " + value.message +
                            " (" + value.file + ":" + value.line + ")"));
                    throw new InvalidOperationException(
                        "Could not activate the reserved exact shell variant " +
                        shaderAsset + ". Import messages: " + messages);
                }
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(material);
            }
        }

        private static CallbackObservation[] ReadCallbackObservations()
        {
            uint count = Native.GetM27CallbackObservationCount();
            var values = new CallbackObservation[count];
            for (uint index = 0; index < count; ++index)
            {
                var metadata = new uint[12];
                var digest = new byte[32];
                uint written = Native.GetM27CallbackObservation(
                    index,
                    metadata,
                    (uint)metadata.Length,
                    digest,
                    (uint)digest.Length);
                if (written != metadata.Length)
                {
                    throw new InvalidOperationException(
                        "Could not read M27 callback observation " + index +
                        ": metadataWritten=" + written + ".");
                }
                values[index] = new CallbackObservation
                {
                    stage = metadata[0],
                    byteCodeSize = metadata[1],
                    inputParameters = metadata[2],
                    outputParameters = metadata[3],
                    boundResources = metadata[4],
                    constantBuffer0Bytes = metadata[5],
                    constantBuffer1Bytes = metadata[6],
                    constantBuffer2Bytes = metadata[7],
                    constantBuffer3Bytes = metadata[8],
                    constantBuffer4Bytes = metadata[9],
                    textureSlotMask = "0x" + metadata[10].ToString("x8"),
                    samplerSlotMask = "0x" + metadata[11].ToString("x8"),
                    sha256 = Hex(digest),
                };
            }
            return values;
        }

        private static string HashFile(string path)
        {
            using (SHA256 sha = SHA256.Create())
                return Hex(sha.ComputeHash(File.ReadAllBytes(path)));
        }

        private static string Hex(byte[] value)
        {
            return string.Concat(value.Select(item => item.ToString("x2")));
        }

        private static class Native
        {
            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetContractVersion")]
            internal static extern uint GetContractVersion();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetConfigureCount")]
            internal static extern uint GetConfigureCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcSetM27SubstitutionArmed")]
            internal static extern uint SetM27SubstitutionArmed(uint armed);

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM27RegistryReady")]
            internal static extern uint GetM27RegistryReady();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM27MatchCount")]
            internal static extern uint GetM27MatchCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM27MismatchCount")]
            internal static extern uint GetM27MismatchCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM27VariantHashConflictCount")]
            internal static extern uint GetM27VariantHashConflictCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM27MaximumSignatureCounts")]
            internal static extern uint GetM27MaximumSignatureCounts(uint stage);

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM27ObservedShellSha256")]
            internal static extern uint GetM27ObservedShellSha256(
                uint stage,
                [Out] byte[] output,
                uint outputSize);

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetCallbackCount")]
            internal static extern uint GetCallbackCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetVertexSwapCount")]
            internal static extern uint GetVertexSwapCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetPixelSwapCount")]
            internal static extern uint GetPixelSwapCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetFailureCount")]
            internal static extern uint GetFailureCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM27CallbackObservationCount")]
            internal static extern uint GetM27CallbackObservationCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM27CallbackObservation")]
            internal static extern uint GetM27CallbackObservation(
                uint index,
                [Out] uint[] metadata,
                uint metadataCount,
                [Out] byte[] sha256,
                uint sha256Size);
        }
    }
}
