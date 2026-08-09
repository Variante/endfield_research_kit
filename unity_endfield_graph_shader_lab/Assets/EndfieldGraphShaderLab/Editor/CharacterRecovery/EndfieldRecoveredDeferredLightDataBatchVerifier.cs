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
    /// Verifies the source-closed selected pass-0 b31 subset through both the
    /// named constant buffer and the D3D11 DXBC-shell CB4 bridge.
    /// </summary>
    public static class EndfieldRecoveredDeferredLightDataBatchVerifier
    {
        private const string ComputeResourceName =
            "EndfieldRecoveredDeferredLightDataProbe";
        private const string SourceAuditRelativePath =
            "scratch/character_recovery/deferred_light_data/audit.json";
        private const string ExpectedSourceAuditSha256 =
            "ae3fc61b167a017796371f674bcec5e5ce60d1402eb53787f7e6b4e022a3434f";

        private static readonly int ConstantsId =
            Shader.PropertyToID("_LightDataBuffer");
        private static readonly int BridgeConstantsId =
            Shader.PropertyToID("EndfieldCB4");
        private static readonly int ReadyId = Shader.PropertyToID(
            "_EndfieldRecoveredDeferredLightDataReady");
        private static readonly int ReadbackId = Shader.PropertyToID(
            "_EndfieldRecoveredDeferredLightDataReadback");

        [Serializable]
        private sealed class RejectionReport
        {
            public string gate;
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
            public bool defaultOff;
            public bool pass0ConsumerEnabled;
            public string sourceAuditPath;
            public string sourceAuditSha256;
            public string expectedSourceAuditSha256;
            public bool sourceAuditHashMatches;
            public int bufferBytes;
            public int vectorCount;
            public int headerVectors;
            public int maxPunctualLights;
            public int vectorsPerPunctualLight;
            public int fixturePunctualLights;
            public bool namedReadyObserved;
            public bool bridgeReadyObserved;
            public bool namedWordsExact;
            public bool bridgeWordsExact;
            public bool namedBridgeWordsExact;
            public bool unresolvedWordsZero;
            public int expectedNonzeroWords;
            public int actualNonzeroWords;
            public RejectionReport[] failClosedGates;
            public string[] failures;
        }

        [MenuItem(
            "Endfield/Character Recovery Lab/" +
            "Verify Recovered Deferred LightData")]
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
                "deferred_light_data");
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
                    (string.IsNullOrEmpty(sourceHash)
                        ? "missing"
                        : sourceHash));
            }
            if (!EndfieldRecoveredDeferredTransformVariables.IsRequested)
            {
                failures.Add(
                    "selector: " +
                    EndfieldRecoveredDeferredTransformVariables.Selector +
                    " must be explicitly enabled");
            }
            if (!EndfieldRecoveredDeferredLightData.IsRequested)
            {
                failures.Add(
                    "selector: " +
                    EndfieldRecoveredDeferredLightData.Selector +
                    " must be explicitly enabled");
            }

            const int fixtureLightCount = 8;
            var fixture = new Vector4[
                EndfieldRecoveredDeferredLightDataContract.VectorCount];
            if (!EndfieldRecoveredDeferredLightDataContract
                    .TryBuildSelectedConsumerSubset(
                        EndfieldRecoveredDeferredLightDataContract
                            .SourceDirectionalForward,
                        new Color(0.8f, 0.9f, 1.0f, 1.0f),
                        fixtureLightCount,
                        fixture,
                        out string fixtureFailure))
            {
                throw new InvalidOperationException(
                    "Known-good deferred LightData fixture was rejected: " +
                    fixtureFailure);
            }
            uint[] expected = EndfieldRecoveredDeferredLightDataContract
                .BuildExpectedWords(fixture);
            uint[] named = new uint[1 + expected.Length];
            uint[] bridge = new uint[1 + expected.Length];

            ComputeBuffer constants = null;
            ComputeBuffer readback = null;
            CommandBuffer command = null;
            try
            {
                ComputeShader compute = Resources.Load<ComputeShader>(
                    ComputeResourceName);
                if (!SystemInfo.supportsComputeShaders)
                {
                    failures.Add(
                        "gpu_capability: compute shaders are unavailable");
                }
                else if (compute == null)
                {
                    failures.Add(
                        "compute_resource: Resources/" +
                        ComputeResourceName + ".compute is unavailable");
                }
                else
                {
                    constants = new ComputeBuffer(
                        EndfieldRecoveredDeferredLightDataContract.VectorCount,
                        sizeof(float) * 4,
                        ComputeBufferType.Constant)
                    {
                        name = "Recovered deferred LightData validation fixture"
                    };
                    constants.SetData(fixture);
                    readback = new ComputeBuffer(
                        named.Length,
                        sizeof(uint),
                        ComputeBufferType.Structured)
                    {
                        name = "Recovered deferred LightData readback"
                    };

                    ReadKernel(
                        compute,
                        "ReadbackNamed",
                        constants,
                        readback,
                        named,
                        ref command);
                    ReadKernel(
                        compute,
                        "ReadbackBridge",
                        constants,
                        readback,
                        bridge,
                        ref command);
                }

                bool namedReady = named[0] == 0x3F800000u;
                bool bridgeReady = bridge[0] == 0x3F800000u;
                bool namedExact = PayloadEqual(expected, named);
                bool bridgeExact = PayloadEqual(expected, bridge);
                bool pathsExact = WordsEqual(named, bridge);
                bool unresolvedZero = UnresolvedWordsAreZero(
                    named,
                    fixtureLightCount);
                int expectedNonzero = CountNonzero(expected, 0);
                int actualNonzero = CountNonzero(named, 1);

                if (!namedReady)
                    failures.Add("named_ready_flag: expected 0x3F800000");
                if (!bridgeReady)
                    failures.Add("bridge_ready_flag: expected 0x3F800000");
                if (!namedExact)
                {
                    failures.Add(
                        "named_gpu_readback: one or more 32864-byte words differ");
                }
                if (!bridgeExact)
                {
                    failures.Add(
                        "bridge_gpu_readback: one or more 32864-byte words differ");
                }
                if (!pathsExact)
                {
                    failures.Add(
                        "named_bridge_parity: constant-buffer paths differ");
                }
                if (!unresolvedZero)
                {
                    failures.Add(
                        "unresolved_words: non-selected b31 words are nonzero");
                }

                RejectionReport[] rejections =
                {
                    VerifyDestinationRejection(),
                    VerifyCountRejection(),
                    VerifyDirectionRejection(),
                    VerifyNonFiniteColorRejection(),
                };
                foreach (RejectionReport rejection in rejections)
                {
                    if (!rejection.rejected || !rejection.diagnosticMatched)
                    {
                        failures.Add(
                            "fail_closed_gate:" + rejection.gate +
                            " expected token '" +
                            rejection.requiredDiagnosticToken +
                            "', actual '" + rejection.diagnostic + "'");
                    }
                }

                string api = ApiName(SystemInfo.graphicsDeviceType);
                var report = new ValidationReport
                {
                    schema =
                        "endfield-recovered-deferred-light-data-validation-v1",
                    valid = failures.Count == 0,
                    graphicsApi = api,
                    defaultOff = true,
                    pass0ConsumerEnabled = false,
                    sourceAuditPath = sourceAuditPath,
                    sourceAuditSha256 = sourceHash,
                    expectedSourceAuditSha256 = ExpectedSourceAuditSha256,
                    sourceAuditHashMatches = sourceHashMatches,
                    bufferBytes =
                        EndfieldRecoveredDeferredLightDataContract.SizeBytes,
                    vectorCount =
                        EndfieldRecoveredDeferredLightDataContract.VectorCount,
                    headerVectors =
                        EndfieldRecoveredDeferredLightDataContract
                            .HeaderVectorCount,
                    maxPunctualLights =
                        EndfieldRecoveredDeferredLightDataContract
                            .MaxPunctualLightCount,
                    vectorsPerPunctualLight =
                        EndfieldRecoveredDeferredLightDataContract
                            .VectorsPerPunctualLight,
                    fixturePunctualLights = fixtureLightCount,
                    namedReadyObserved = namedReady,
                    bridgeReadyObserved = bridgeReady,
                    namedWordsExact = namedExact,
                    bridgeWordsExact = bridgeExact,
                    namedBridgeWordsExact = pathsExact,
                    unresolvedWordsZero = unresolvedZero,
                    expectedNonzeroWords = expectedNonzero,
                    actualNonzeroWords = actualNonzero,
                    failClosedGates = rejections,
                    failures = failures.ToArray(),
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
                        "Deferred LightData validation failed: " +
                        string.Join("; ", report.failures) +
                        ". Report=" + reportPath);
                }
                Debug.Log(
                    "Recovered deferred _LightDataBuffer validation passed: " +
                    "all 8216 words exact through named and CB4 paths, " +
                    "unresolved words zero, fail-closed gates=4/4, api=" +
                    api + ", report=" + reportPath +
                    ". Pass 0 remains disabled.");
            }
            finally
            {
                command?.Release();
                readback?.Release();
                constants?.Release();
                Shader.SetGlobalFloat(ReadyId, 0.0f);
            }
        }

        private static void ReadKernel(
            ComputeShader compute,
            string kernelName,
            ComputeBuffer constants,
            ComputeBuffer readback,
            uint[] destination,
            ref CommandBuffer command)
        {
            readback.SetData(new uint[destination.Length]);
            command?.Release();
            command = new CommandBuffer
            {
                name = "Verify deferred LightData " + kernelName
            };
            int kernel = compute.FindKernel(kernelName);
            command.SetGlobalConstantBuffer(
                constants,
                ConstantsId,
                0,
                EndfieldRecoveredDeferredLightDataContract.SizeBytes);
            command.SetGlobalConstantBuffer(
                constants,
                BridgeConstantsId,
                0,
                EndfieldRecoveredDeferredLightDataContract.SizeBytes);
            command.SetGlobalFloat(ReadyId, 1.0f);
            command.SetComputeBufferParam(
                compute,
                kernel,
                ReadbackId,
                readback);
            command.DispatchCompute(compute, kernel, 1, 1, 1);
            Graphics.ExecuteCommandBuffer(command);
            readback.GetData(destination);
        }

        private static RejectionReport VerifyDestinationRejection()
        {
            bool accepted = EndfieldRecoveredDeferredLightDataContract
                .TryBuildSelectedConsumerSubset(
                    EndfieldRecoveredDeferredLightDataContract
                        .SourceDirectionalForward,
                    Color.white,
                    8,
                    new Vector4[1],
                    out string diagnostic);
            return Rejection(
                "destination_size",
                "exactly 2054 float4 vectors",
                accepted,
                diagnostic);
        }

        private static RejectionReport VerifyCountRejection()
        {
            bool accepted = EndfieldRecoveredDeferredLightDataContract
                .TryBuildSelectedConsumerSubset(
                    EndfieldRecoveredDeferredLightDataContract
                        .SourceDirectionalForward,
                    Color.white,
                    257,
                    new Vector4[2054],
                    out string diagnostic);
            return Rejection(
                "punctual_count",
                "within [0, 256]",
                accepted,
                diagnostic);
        }

        private static RejectionReport VerifyDirectionRejection()
        {
            bool accepted = EndfieldRecoveredDeferredLightDataContract
                .TryBuildSelectedConsumerSubset(
                    Vector3.forward,
                    Color.white,
                    8,
                    new Vector4[2054],
                    out string diagnostic);
            return Rejection(
                "directional_source",
                "does not match the recovered CharInfo_Env source",
                accepted,
                diagnostic);
        }

        private static RejectionReport VerifyNonFiniteColorRejection()
        {
            bool accepted = EndfieldRecoveredDeferredLightDataContract
                .TryBuildSelectedConsumerSubset(
                    EndfieldRecoveredDeferredLightDataContract
                        .SourceDirectionalForward,
                    new Color(float.NaN, 1.0f, 1.0f, 1.0f),
                    8,
                    new Vector4[2054],
                    out string diagnostic);
            return Rejection(
                "nonfinite_color",
                "final color must be finite",
                accepted,
                diagnostic);
        }

        private static RejectionReport Rejection(
            string gate,
            string token,
            bool accepted,
            string diagnostic)
        {
            return new RejectionReport
            {
                gate = gate,
                requiredDiagnosticToken = token,
                diagnostic = diagnostic,
                rejected = !accepted,
                diagnosticMatched = !accepted && diagnostic != null &&
                    diagnostic.IndexOf(token, StringComparison.Ordinal) >= 0,
            };
        }

        private static bool PayloadEqual(uint[] expected, uint[] readback)
        {
            if (readback.Length != expected.Length + 1)
                return false;
            for (int index = 0; index < expected.Length; index++)
            {
                if (expected[index] != readback[index + 1])
                    return false;
            }
            return true;
        }

        private static bool WordsEqual(uint[] left, uint[] right)
        {
            if (left.Length != right.Length)
                return false;
            for (int index = 0; index < left.Length; index++)
            {
                if (left[index] != right[index])
                    return false;
            }
            return true;
        }

        private static bool UnresolvedWordsAreZero(
            uint[] readback,
            int lightCount)
        {
            var selected = new HashSet<int>();
            SelectVector(selected, 0, 0, 1, 2);
            SelectVector(selected, 1, 0, 1, 2, 3);
            SelectVector(selected, 4, 0, 2);
            for (int light = 0; light < lightCount; light++)
            {
                int record = 6 + light * 8;
                SelectVector(selected, record + 3, 2);
                SelectVector(selected, record + 5, 3);
            }
            for (int word = 0; word < readback.Length - 1; word++)
            {
                if (!selected.Contains(word) && readback[word + 1] != 0u)
                    return false;
            }
            return true;
        }

        private static void SelectVector(
            HashSet<int> selected,
            int vector,
            params int[] lanes)
        {
            foreach (int lane in lanes)
                selected.Add(vector * 4 + lane);
        }

        private static int CountNonzero(uint[] words, int offset)
        {
            int count = 0;
            for (int index = offset; index < words.Length; index++)
            {
                if (words[index] != 0u)
                    count++;
            }
            return count;
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
            {
                return BitConverter.ToString(sha.ComputeHash(stream))
                    .Replace("-", string.Empty)
                    .ToLowerInvariant();
            }
        }
    }
}
