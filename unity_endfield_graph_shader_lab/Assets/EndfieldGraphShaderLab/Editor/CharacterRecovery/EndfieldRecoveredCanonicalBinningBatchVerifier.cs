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
    /// Verifies the exact combined raw _BinningBuffer transport on the active
    /// graphics backend. The fixture uses deterministic light words and the
    /// source-closed zero-local-reflection CharInfo tail.
    /// </summary>
    public static class EndfieldRecoveredCanonicalBinningBatchVerifier
    {
        private const string ComputeResourceName =
            "EndfieldRecoveredCanonicalBinning";
        private const string BuildKernelName = "BuildCanonicalCombined";
        private const string ReadKernelName = "ReadCanonicalGlobal";
        private const string SourceAuditRelativePath =
            "scratch/character_recovery/charinfo_light_binning/audit.json";
        private const string ExpectedSourceAuditSha256 =
            "2645ce94ea683d6b224928dfcf834c0a05cef4a01060ed081069777533c3977c";

        private static readonly int LightInputId =
            Shader.PropertyToID("_EndfieldRecoveredLightBinningBuffer");
        private static readonly int CanonicalOutputId =
            Shader.PropertyToID("_EndfieldRecoveredCanonicalBinningBuffer");
        private static readonly int CanonicalReadbackId =
            Shader.PropertyToID("_EndfieldRecoveredCanonicalBinningReadback");
        private static readonly int LightWordCountId =
            Shader.PropertyToID("_EndfieldRecoveredCanonicalLightWordCount");
        private static readonly int CombinedWordCountId =
            Shader.PropertyToID("_EndfieldRecoveredCanonicalCombinedWordCount");
        private static readonly int BinningBufferId =
            Shader.PropertyToID("_BinningBuffer");

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
            public bool canonicalPublicationDefaultOff;
            public bool noLocalReflectionSourceClosed;
            public string sourceAuditPath;
            public string sourceAuditSha256;
            public string expectedSourceAuditSha256;
            public bool sourceAuditHashMatches;
            public int fixtureWidth;
            public int fixtureHeight;
            public int tileX;
            public int tileY;
            public int tileCount;
            public int lightXYOffset;
            public int lightZOffset;
            public int lightWordCount;
            public int reflectionXYOffset;
            public int reflectionZOffset;
            public int reflectionWordCount;
            public int totalWordCount;
            public int totalBytes;
            public bool rawGlobalReadbackMatches;
            public bool lightSegmentMatches;
            public bool reflectionSegmentIsZero;
            public RejectionReport[] failClosedGates;
            public string[] failures;
        }

        [MenuItem(
            "Endfield/Character Recovery Lab/" +
            "Verify Recovered Canonical Binning Buffer")]
        public static void VerifyBatch()
        {
            string projectRoot = Path.GetFullPath(
                Path.Combine(Application.dataPath, ".."));
            string sourceAuditPath = Path.Combine(
                projectRoot,
                SourceAuditRelativePath.Replace('/', Path.DirectorySeparatorChar));
            string outputRoot = Path.Combine(
                projectRoot,
                "scratch",
                "character_recovery",
                "canonical_binning_buffer");
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
                    "source_audit_hash: expected " + ExpectedSourceAuditSha256 +
                    ", actual " +
                    (string.IsNullOrEmpty(sourceHash) ? "missing" : sourceHash) +
                    ", source=" + sourceAuditPath);
            }

            const int width = 3840;
            const int height = 2160;
            EndfieldRecoveredCanonicalBinningLayoutContract.Layout layout;
            string layoutFailure;
            if (!EndfieldRecoveredCanonicalBinningLayoutContract.TryBuild(
                    width,
                    height,
                    out layout,
                    out layoutFailure))
            {
                throw new InvalidOperationException(
                    "Known-good 3840x2160 layout was rejected: " + layoutFailure);
            }
            if (layout.tileX != 120 ||
                layout.tileY != 68 ||
                layout.tileCount != 8160 ||
                layout.lightXYOffset != 0 ||
                layout.lightZOffset != 65280 ||
                layout.lightWordCount != 81664 ||
                layout.reflectionXYOffset != 81664 ||
                layout.reflectionZOffset != 89824 ||
                layout.reflectionWordCount != 9184 ||
                layout.totalWordCount != 90848)
            {
                failures.Add(
                    "fixture_layout: expected 120x68, offsets " +
                    "0/65280/81664/89824 and counts 81664/9184/90848; actual " +
                    $"{layout.tileX}x{layout.tileY}, offsets " +
                    $"{layout.lightXYOffset}/{layout.lightZOffset}/" +
                    $"{layout.reflectionXYOffset}/{layout.reflectionZOffset}, counts " +
                    $"{layout.lightWordCount}/{layout.reflectionWordCount}/" +
                    layout.totalWordCount);
            }

            RejectionReport[] rejectionReports =
            {
                VerifyRejection(
                    "zero_width",
                    0,
                    2160,
                    "render dimensions must be positive"),
                VerifyRejection(
                    "tile_x_overflow",
                    8193,
                    2160,
                    "exceed the installed 256x128 limit"),
                VerifyRejection(
                    "tile_y_overflow",
                    3840,
                    4097,
                    "exceed the installed 256x128 limit")
            };
            foreach (RejectionReport rejection in rejectionReports)
            {
                if (!rejection.rejected || !rejection.diagnosticMatched)
                {
                    failures.Add(
                        "fail_closed_gate:" + rejection.gate +
                        " expected token '" + rejection.requiredDiagnosticToken +
                        "', actual '" + rejection.diagnostic + "'");
                }
            }

            bool rawGlobalReadbackMatches = false;
            bool lightSegmentMatches = false;
            bool reflectionSegmentIsZero = false;
            if (!SystemInfo.supportsComputeShaders)
            {
                failures.Add("gpu_capability: compute shaders are unavailable");
            }
            else
            {
                ComputeShader compute = Resources.Load<ComputeShader>(
                    ComputeResourceName);
                if (compute == null)
                {
                    failures.Add(
                        "compute_resource: Resources/" + ComputeResourceName +
                        ".compute is unavailable");
                }
                else
                {
                    uint[] sourceWords = BuildSourceWords(layout.lightWordCount);
                    uint[] actualWords = RunGpuReadback(
                        compute,
                        compute.FindKernel(BuildKernelName),
                        compute.FindKernel(ReadKernelName),
                        layout,
                        sourceWords);
                    lightSegmentMatches = SegmentMatches(
                        actualWords,
                        0,
                        sourceWords);
                    reflectionSegmentIsZero = IsZero(
                        actualWords,
                        layout.reflectionXYOffset,
                        layout.reflectionWordCount);
                    rawGlobalReadbackMatches =
                        lightSegmentMatches && reflectionSegmentIsZero;
                    if (!lightSegmentMatches)
                    {
                        failures.Add(
                            "gpu_light_segment: raw global readback differs from " +
                            "the recovered light XY/Z source words");
                    }
                    if (!reflectionSegmentIsZero)
                    {
                        failures.Add(
                            "gpu_reflection_segment: no-local-probe tail contains " +
                            "a nonzero word");
                    }
                }
            }

            string api = ApiName(SystemInfo.graphicsDeviceType);
            var report = new ValidationReport
            {
                schema = "endfield-recovered-canonical-binning-validation-v1",
                valid = failures.Count == 0,
                graphicsApi = api,
                diagnosticScope =
                    "exact raw _BinningBuffer transport for recovered isolated " +
                    "light words plus the source-closed no-local-reflection tail; " +
                    "not a retail whole-scene light census",
                canonicalPublicationDefaultOff = true,
                noLocalReflectionSourceClosed = true,
                sourceAuditPath = sourceAuditPath,
                sourceAuditSha256 = sourceHash,
                expectedSourceAuditSha256 = ExpectedSourceAuditSha256,
                sourceAuditHashMatches = sourceHashMatches,
                fixtureWidth = width,
                fixtureHeight = height,
                tileX = layout.tileX,
                tileY = layout.tileY,
                tileCount = layout.tileCount,
                lightXYOffset = layout.lightXYOffset,
                lightZOffset = layout.lightZOffset,
                lightWordCount = layout.lightWordCount,
                reflectionXYOffset = layout.reflectionXYOffset,
                reflectionZOffset = layout.reflectionZOffset,
                reflectionWordCount = layout.reflectionWordCount,
                totalWordCount = layout.totalWordCount,
                totalBytes = checked(
                    layout.totalWordCount *
                    EndfieldRecoveredCanonicalBinningLayoutContract.WordStrideBytes),
                rawGlobalReadbackMatches = rawGlobalReadbackMatches,
                lightSegmentMatches = lightSegmentMatches,
                reflectionSegmentIsZero = reflectionSegmentIsZero,
                failClosedGates = rejectionReports,
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
                    "Canonical binning-buffer validation failed: " +
                    string.Join("; ", report.failures) +
                    ". Report=" + reportPath);
            }
            Debug.Log(
                "Recovered canonical _BinningBuffer validation passed: " +
                "120x68 tiles, light=81664 words, reflection=9184 zero words, " +
                "combined=90848 words/363392 bytes, raw global readback exact, " +
                "fail-closed gates=3/3, api=" + api +
                ", report=" + reportPath + ". Publication remains default-off.");
        }

        private static uint[] RunGpuReadback(
            ComputeShader compute,
            int buildKernel,
            int readKernel,
            EndfieldRecoveredCanonicalBinningLayoutContract.Layout layout,
            uint[] sourceWords)
        {
            ComputeBuffer source = null;
            ComputeBuffer combined = null;
            ComputeBuffer readback = null;
            CommandBuffer command = null;
            try
            {
                source = new ComputeBuffer(
                    sourceWords.Length,
                    sizeof(uint),
                    ComputeBufferType.Structured);
                source.SetData(sourceWords);
                combined = new ComputeBuffer(
                    layout.totalWordCount,
                    sizeof(uint),
                    ComputeBufferType.Raw);
                readback = new ComputeBuffer(
                    layout.totalWordCount,
                    sizeof(uint),
                    ComputeBufferType.Structured);
                readback.SetData(new uint[layout.totalWordCount]);

                command = new CommandBuffer
                {
                    name = "Verify Recovered Canonical Binning Buffer"
                };
                command.SetComputeBufferParam(
                    compute, buildKernel, LightInputId, source);
                command.SetComputeBufferParam(
                    compute, buildKernel, CanonicalOutputId, combined);
                command.SetComputeIntParam(
                    compute, LightWordCountId, layout.lightWordCount);
                command.SetComputeIntParam(
                    compute, CombinedWordCountId, layout.totalWordCount);
                command.DispatchCompute(
                    compute,
                    buildKernel,
                    (layout.totalWordCount + 63) / 64,
                    1,
                    1);
                command.SetGlobalBuffer(BinningBufferId, combined);
                command.SetComputeBufferParam(
                    compute, readKernel, CanonicalReadbackId, readback);
                command.SetComputeIntParam(
                    compute, CombinedWordCountId, layout.totalWordCount);
                command.DispatchCompute(
                    compute,
                    readKernel,
                    (layout.totalWordCount + 63) / 64,
                    1,
                    1);
                Graphics.ExecuteCommandBuffer(command);

                var actual = new uint[layout.totalWordCount];
                readback.GetData(actual);
                return actual;
            }
            finally
            {
                command?.Release();
                source?.Release();
                combined?.Release();
                readback?.Release();
            }
        }

        private static uint[] BuildSourceWords(int count)
        {
            var words = new uint[count];
            for (uint index = 0; index < words.Length; index++)
            {
                words[index] =
                    unchecked(index * 2654435761u) ^ 0xA5C31F29u;
            }
            return words;
        }

        private static bool SegmentMatches(
            uint[] actual,
            int offset,
            uint[] expected)
        {
            if (actual == null || expected == null ||
                offset < 0 || offset + expected.Length > actual.Length)
            {
                return false;
            }
            for (int index = 0; index < expected.Length; index++)
            {
                if (actual[offset + index] != expected[index])
                    return false;
            }
            return true;
        }

        private static bool IsZero(uint[] words, int offset, int count)
        {
            if (words == null || offset < 0 || count < 0 ||
                offset + count > words.Length)
            {
                return false;
            }
            for (int index = 0; index < count; index++)
            {
                if (words[offset + index] != 0u)
                    return false;
            }
            return true;
        }

        private static RejectionReport VerifyRejection(
            string gate,
            int width,
            int height,
            string requiredToken)
        {
            EndfieldRecoveredCanonicalBinningLayoutContract.Layout ignored;
            string diagnostic;
            bool accepted = EndfieldRecoveredCanonicalBinningLayoutContract.TryBuild(
                width,
                height,
                out ignored,
                out diagnostic);
            return new RejectionReport
            {
                gate = gate,
                input = "width=" + width + ", height=" + height,
                requiredDiagnosticToken = requiredToken,
                diagnostic = diagnostic,
                rejected = !accepted,
                diagnosticMatched = !accepted && diagnostic != null &&
                    diagnostic.IndexOf(requiredToken, StringComparison.Ordinal) >= 0
            };
        }

        private static string ApiName(GraphicsDeviceType api)
        {
            if (api == GraphicsDeviceType.Direct3D11)
                return "d3d11";
            if (api == GraphicsDeviceType.Direct3D12)
                return "d3d12";
            return api.ToString().ToLowerInvariant();
        }

        private static string Sha256File(string path)
        {
            using (FileStream stream = File.OpenRead(path))
            using (SHA256 hash = SHA256.Create())
            {
                return BitConverter.ToString(hash.ComputeHash(stream))
                    .Replace("-", string.Empty)
                    .ToLowerInvariant();
            }
        }
    }
}
