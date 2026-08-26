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
    /// One-shot, fail-closed capture of the dedicated M27 shell's Unity-
    /// compiled D3D11 stage hashes. The native callback does not substitute
    /// until these independently observed identities are pinned.
    /// </summary>
    public static class EndfieldM27ShellHashCapture
    {
        private const string NativeLibrary = "OriginalDxbcSwapPlugin";
        private const string ShaderAsset =
            "Assets/EndfieldGraphShaderLab/Shaders/Diagnostics/" +
            "EndfieldEndminfM27ExactAbiShell.shader";
        private const string OutputEnvironment =
            "ENDFIELD_M27_SHELL_HASH_OUTPUT";

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

                AssetDatabase.ImportAsset(
                    ShaderAsset,
                    ImportAssetOptions.ForceUpdate |
                    ImportAssetOptions.ForceSynchronousImport);

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
                bool bothStagesObserved =
                    vertex.Any(value => value != 0) &&
                    pixel.Any(value => value != 0);
                if (registryReady != 0 || matchCount != 0 ||
                    (bothStagesObserved && variantHashConflictCount != 0) ||
                    mismatchCount < 1 || callbackCount < 2)
                {
                    throw new InvalidOperationException(
                        "Unpinned M27 registry did not remain fail closed: " +
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
                    status = bothStagesObserved
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
                };
                Directory.CreateDirectory(Path.GetDirectoryName(output));
                File.WriteAllText(output, JsonUtility.ToJson(report, true));
                Debug.Log(
                    "Observed fail-closed M27 Unity shell state: status=" +
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
        }
    }
}
