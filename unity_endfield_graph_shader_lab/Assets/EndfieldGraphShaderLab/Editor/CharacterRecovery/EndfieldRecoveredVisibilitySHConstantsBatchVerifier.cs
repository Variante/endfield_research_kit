using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Verifies the installed VisibilitySHConstData producer constants and the
    /// exact global constant-buffer binding used by the selected deferred pass.
    /// </summary>
    public static class EndfieldRecoveredVisibilitySHConstantsBatchVerifier
    {
        private const string ComputeResourceName =
            "EndfieldRecoveredVisibilitySHConstantsProbe";
        private const string KernelName = "Readback";
        private const string SourceAuditRelativePath =
            "scratch/reverse_engineering/visibility_sh_constants/audit.json";
        private const string ExpectedSourceAuditSha256 =
            "338b29513855466b7bf5b245639b20af5f1540e4727352898b71a485e2370882";

        private static readonly int ReadbackId = Shader.PropertyToID(
            "_EndfieldRecoveredVisibilitySHConstantsReadback");

        [Serializable]
        private sealed class RejectionReport
        {
            public string gate;
            public string input;
            public string requiredDiagnosticToken;
            public string diagnostic;
            public bool rejected;
            public bool diagnosticMatched;
        }

        [Serializable]
        private sealed class ValidationReport
        {
            public string schema;
            public bool valid;
            public string graphicsApi;
            public string diagnosticScope;
            public bool defaultOff;
            public bool retailVisibilityTextureClosed;
            public bool fullConstantBufferSourceClosed;
            public string sourceAuditPath;
            public string sourceAuditSha256;
            public string expectedSourceAuditSha256;
            public bool sourceAuditHashMatches;
            public int cameraWidth;
            public int cameraHeight;
            public int outputWidth;
            public int outputHeight;
            public int bufferBytes;
            public bool publicationReturnedReady;
            public bool readyObserved;
            public bool allPublishedWordsMatch;
            public bool selectedDeferredWordsMatch;
            public bool nativeZeroTailMatch;
            public int selectedFirstWord;
            public int selectedWordCount;
            public string[] expectedWords;
            public string[] actualWords;
            public RejectionReport[] failClosedGates;
            public string[] failures;
        }

        [MenuItem(
            "Endfield/Character Recovery Lab/" +
            "Verify Recovered VisibilitySH Constants")]
        public static void VerifyBatch()
        {
            string projectRoot = Path.GetFullPath(
                Path.Combine(Application.dataPath, ".."));
            string sourceAuditPath = Path.Combine(
                projectRoot,
                SourceAuditRelativePath.Replace(
                    '/',
                    Path.DirectorySeparatorChar));
            string outputRoot = Path.Combine(
                projectRoot,
                "scratch",
                "character_recovery",
                "visibility_sh_constants");
            Directory.CreateDirectory(outputRoot);

            var failures = new List<string>();
            string sourceHash = File.Exists(sourceAuditPath)
                ? Sha256File(sourceAuditPath)
                : string.Empty;
            bool sourceHashMatches = string.Equals(
                sourceHash,
                ExpectedSourceAuditSha256,
                StringComparison.Ordinal);
            if (!sourceHashMatches)
            {
                failures.Add(
                    "source_audit_hash: expected " +
                    ExpectedSourceAuditSha256 + ", actual " +
                    (string.IsNullOrEmpty(sourceHash) ? "missing" : sourceHash) +
                    ", source=" + sourceAuditPath);
            }

            var fixture = new Vector4[
                EndfieldRecoveredVisibilitySHConstantsContract.VectorCount];
            string fixtureFailure;
            if (!EndfieldRecoveredVisibilitySHConstantsContract.TryBuild(
                    3840,
                    2160,
                    fixture,
                    out fixtureFailure))
            {
                throw new InvalidOperationException(
                    "Known-good VisibilitySHConstData fixture was rejected: " +
                    fixtureFailure);
            }
            uint[] expected =
                EndfieldRecoveredVisibilitySHConstantsContract
                    .BuildExpectedWords(fixture);
            uint[] readback = new uint[1 + expected.Length];
            bool publicationReady = false;
            if (!SystemInfo.supportsComputeShaders)
            {
                failures.Add("gpu_capability: compute shaders are unavailable");
            }
            else
            {
                ComputeShader compute =
                    Resources.Load<ComputeShader>(ComputeResourceName);
                if (compute == null)
                {
                    failures.Add(
                        "compute_resource: Resources/" + ComputeResourceName +
                        ".compute is unavailable");
                }
                else
                {
                    int kernel = compute.FindKernel(KernelName);
                    publicationReady = RunGpuReadback(
                        compute,
                        kernel,
                        readback,
                        out string publicationFailure);
                    if (!publicationReady)
                    {
                        failures.Add(
                            "publication: " + publicationFailure);
                    }
                }
            }

            bool readyObserved = readback[0] == 0x3F800000u;
            var actual = new uint[expected.Length];
            Array.Copy(readback, 1, actual, 0, actual.Length);
            bool allWordsMatch = WordsEqual(expected, actual, 0, expected.Length);
            int selectedFirstWord =
                EndfieldRecoveredVisibilitySHConstantsContract
                    .SelectedReadFirstVector * 4;
            int selectedWordCount =
                EndfieldRecoveredVisibilitySHConstantsContract
                    .SelectedReadVectorCount * 4;
            bool selectedWordsMatch = WordsEqual(
                expected,
                actual,
                selectedFirstWord,
                selectedWordCount);
            bool tailZero = true;
            for (int index = 20; index < actual.Length; index++)
                tailZero &= actual[index] == 0u;
            if (!readyObserved)
                failures.Add("ready_flag: expected 0x3F800000, actual " + Hex(readback[0]));
            if (!allWordsMatch)
                failures.Add("gpu_readback: one or more 128-byte fixture words differ");
            if (!selectedWordsMatch)
                failures.Add("selected_consumer: words 8..15 differ from native b33 rows 2..3");
            if (!tailZero)
                failures.Add("native_zero_tail: source-closed words 20..31 are not zero");

            RejectionReport[] rejections =
            {
                VerifyRejection(
                    "zero_width",
                    0,
                    2160,
                    "camera dimensions must be positive"),
                VerifyRejection(
                    "half_width_zero",
                    1,
                    2160,
                    "half-resolution dimensions must remain positive"),
                VerifyRejection(
                    "float_integer_overflow",
                    0x01000000,
                    2160,
                    "exceed exact float-integer transport")
            };
            foreach (RejectionReport rejection in rejections)
            {
                if (!rejection.rejected || !rejection.diagnosticMatched)
                {
                    failures.Add(
                        "fail_closed_gate:" + rejection.gate +
                        " expected token '" + rejection.requiredDiagnosticToken +
                        "', actual '" + rejection.diagnostic + "'");
                }
            }

            string api = ApiName(SystemInfo.graphicsDeviceType);
            var report = new ValidationReport
            {
                schema =
                    "endfield-recovered-visibility-sh-constants-validation-v2",
                valid = failures.Count == 0,
                graphicsApi = api,
                diagnosticScope =
                    "all installed 128-byte b33 producer rows source-closed: " +
                    "fixed/frame rows 0..4 and native-zero rows 5..7; retail " +
                    "VisibilitySH texture contents remain open",
                defaultOff = true,
                retailVisibilityTextureClosed = false,
                fullConstantBufferSourceClosed = true,
                sourceAuditPath = sourceAuditPath,
                sourceAuditSha256 = sourceHash,
                expectedSourceAuditSha256 = ExpectedSourceAuditSha256,
                sourceAuditHashMatches = sourceHashMatches,
                cameraWidth = 3840,
                cameraHeight = 2160,
                outputWidth = 1920,
                outputHeight = 1080,
                bufferBytes =
                    EndfieldRecoveredVisibilitySHConstantsContract.SizeBytes,
                publicationReturnedReady = publicationReady,
                readyObserved = readyObserved,
                allPublishedWordsMatch = allWordsMatch,
                selectedDeferredWordsMatch = selectedWordsMatch,
                nativeZeroTailMatch = tailZero,
                selectedFirstWord = selectedFirstWord,
                selectedWordCount = selectedWordCount,
                expectedWords = HexWords(expected),
                actualWords = HexWords(actual),
                failClosedGates = rejections,
                failures = failures.ToArray()
            };
            string reportPath = Path.Combine(
                outputRoot,
                "gpu_validation_" + api + ".json");
            File.WriteAllText(
                reportPath,
                JsonUtility.ToJson(report, true) + Environment.NewLine);
            if (!report.valid)
            {
                throw new InvalidOperationException(
                    "VisibilitySHConstData validation failed: " +
                    string.Join("; ", report.failures) +
                    ". Report=" + reportPath);
            }
            Debug.Log(
                "Recovered VisibilitySHConstData validation passed: " +
                "all 32 native words exact, selected words=8/8, " +
                "fail-closed gates=3/3, api=" + api +
                ", report=" + reportPath +
                ". Retail VisibilitySH texture contents remain open.");
        }

        private static bool RunGpuReadback(
            ComputeShader compute,
            int kernel,
            uint[] output,
            out string failure)
        {
            failure = null;
            ComputeBuffer readback = null;
            CommandBuffer command = null;
            var owner = new EndfieldRecoveredVisibilitySHConstants();
            try
            {
                readback = new ComputeBuffer(
                    output.Length,
                    sizeof(uint),
                    ComputeBufferType.Structured)
                {
                    name = "Recovered VisibilitySHConstData Validation Readback"
                };
                readback.SetData(new uint[output.Length]);
                command = new CommandBuffer
                {
                    name = "Verify Recovered VisibilitySHConstData Global Binding"
                };
                owner.ResetPublication(command);
                bool ready = owner.PrepareAndPublish(
                    3840,
                    2160,
                    command,
                    out failure);
                command.SetComputeBufferParam(
                    compute,
                    kernel,
                    ReadbackId,
                    readback);
                command.DispatchCompute(compute, kernel, 1, 1, 1);
                Graphics.ExecuteCommandBuffer(command);
                readback.GetData(output);
                return ready;
            }
            finally
            {
                command?.Release();
                owner.Dispose();
                readback?.Release();
            }
        }

        private static RejectionReport VerifyRejection(
            string gate,
            int width,
            int height,
            string requiredToken)
        {
            var ignored = new Vector4[
                EndfieldRecoveredVisibilitySHConstantsContract.VectorCount];
            bool accepted =
                EndfieldRecoveredVisibilitySHConstantsContract.TryBuild(
                    width,
                    height,
                    ignored,
                    out string diagnostic);
            return new RejectionReport
            {
                gate = gate,
                input = "width=" + width + ", height=" + height,
                requiredDiagnosticToken = requiredToken,
                diagnostic = diagnostic,
                rejected = !accepted,
                diagnosticMatched = !accepted && diagnostic != null &&
                    diagnostic.IndexOf(
                        requiredToken,
                        StringComparison.Ordinal) >= 0
            };
        }

        private static bool WordsEqual(
            uint[] expected,
            uint[] actual,
            int start,
            int count)
        {
            if (expected.Length != actual.Length || start < 0 || count < 0 ||
                start + count > expected.Length)
                return false;
            for (int index = start; index < start + count; index++)
            {
                if (expected[index] != actual[index])
                    return false;
            }
            return true;
        }

        private static string[] HexWords(uint[] words)
        {
            var result = new string[words.Length];
            for (int index = 0; index < words.Length; index++)
                result[index] = Hex(words[index]);
            return result;
        }

        private static string Hex(uint value)
        {
            return "0x" + value.ToString("X8");
        }

        private static string ApiName(GraphicsDeviceType type)
        {
            switch (type)
            {
                case GraphicsDeviceType.Direct3D11:
                    return "d3d11";
                case GraphicsDeviceType.Direct3D12:
                    return "d3d12";
                default:
                    return type.ToString().ToLowerInvariant();
            }
        }

        private static string Sha256File(string path)
        {
            using (FileStream stream = File.OpenRead(path))
            using (SHA256 sha = SHA256.Create())
                return BitConverter.ToString(sha.ComputeHash(stream))
                    .Replace("-", string.Empty)
                    .ToLowerInvariant();
        }
    }
}
