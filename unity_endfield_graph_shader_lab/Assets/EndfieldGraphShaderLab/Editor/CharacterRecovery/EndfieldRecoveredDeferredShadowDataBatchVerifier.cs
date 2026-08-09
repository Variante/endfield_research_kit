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
    /// Verifies the full b34 transport and the selected 401-vector D3D11 CB5
    /// bridge while keeping all unowned ShadowData sections exactly zero.
    /// </summary>
    public static class EndfieldRecoveredDeferredShadowDataBatchVerifier
    {
        private const string ComputeResourceName =
            "EndfieldRecoveredDeferredShadowDataProbe";
        private const string SourceAuditRelativePath =
            "scratch/character_recovery/deferred_shadow_data/audit.json";
        private const string ExpectedSourceAuditSha256 =
            "2f9ba6db602f533ba13515bc97eb55a0a6f289dd5ece94565edad30c379926df";

        private static readonly int ConstantsId =
            Shader.PropertyToID("_ShadowData");
        private static readonly int BridgeConstantsId =
            Shader.PropertyToID("EndfieldCB5");
        private static readonly int ReadyId = Shader.PropertyToID(
            "_EndfieldRecoveredDeferredShadowDataReady");
        private static readonly int ReadbackId = Shader.PropertyToID(
            "_EndfieldRecoveredDeferredShadowDataReadback");

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
            public int d3d11SelectedBytes;
            public int d3d11SelectedVectors;
            public int fixtureTileResolution;
            public int fixtureFaceCount;
            public bool namedReadyObserved;
            public bool bridgeReadyObserved;
            public bool namedWordsExact;
            public bool bridgeWordsExact;
            public bool namedBridgePrefixExact;
            public bool unownedSectionsZero;
            public string expectedWordsSha256;
            public string namedWordsSha256;
            public string bridgeWordsSha256;
            public int expectedNonzeroWords;
            public int namedNonzeroWords;
            public RejectionReport[] failClosedGates;
            public string[] failures;
        }

        [MenuItem(
            "Endfield/Character Recovery Lab/" +
            "Verify Recovered Deferred ShadowData")]
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
                "deferred_shadow_data");
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
            RequireSelector(
                EndfieldRecoveredDeferredTransformVariables.IsRequested,
                EndfieldRecoveredDeferredTransformVariables.Selector,
                failures);
            RequireSelector(
                EndfieldRecoveredDeferredLightData.IsRequested,
                EndfieldRecoveredDeferredLightData.Selector,
                failures);
            RequireSelector(
                EndfieldRecoveredDeferredShadowData.IsRequested,
                EndfieldRecoveredDeferredShadowData.Selector,
                failures);

            const int tileResolution = 1024;
            const int faceCount = 1;
            var matrices = new Matrix4x4[56];
            var parameters = new Vector4[56];
            var rects = new Vector4[56];
            matrices[40] = Matrix4x4.TRS(
                new Vector3(0.25f, -0.5f, 0.75f),
                Quaternion.Euler(12.0f, 34.0f, 56.0f),
                new Vector3(1.25f, 0.75f, 2.0f));
            parameters[40] = new Vector4(0.0f, 0.003f, 0.002f, 1.0f);
            rects[40] = new Vector4(
                4.0f / 6.0f,
                0.0f,
                5.0f / 6.0f,
                1.0f / 4.0f);
            Vector4 texelSize = new Vector4(
                1.0f / 6144.0f,
                1.0f / 4096.0f,
                6144.0f,
                4096.0f);
            var fixture = new Vector4[
                EndfieldRecoveredDeferredShadowDataContract.VectorCount];
            if (!EndfieldRecoveredDeferredShadowDataContract
                    .TryBuildSelectedPunctualSubset(
                        matrices,
                        parameters,
                        rects,
                        texelSize,
                        tileResolution,
                        faceCount,
                        fixture,
                        out string fixtureFailure))
            {
                throw new InvalidOperationException(
                    "Known-good deferred ShadowData fixture was rejected: " +
                    fixtureFailure);
            }
            uint[] expected = EndfieldRecoveredDeferredShadowDataContract
                .BuildExpectedWords(fixture);
            int bridgeWordCount =
                EndfieldRecoveredDeferredShadowDataContract
                    .D3D11SelectedVectorCount * 4;
            uint[] named = new uint[1 + expected.Length];
            uint[] bridge = new uint[1 + bridgeWordCount];

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
                        EndfieldRecoveredDeferredShadowDataContract.VectorCount,
                        sizeof(float) * 4,
                        ComputeBufferType.Constant)
                    {
                        name = "Recovered deferred ShadowData validation fixture"
                    };
                    constants.SetData(fixture);
                    readback = new ComputeBuffer(
                        named.Length,
                        sizeof(uint),
                        ComputeBufferType.Structured)
                    {
                        name = "Recovered deferred ShadowData readback"
                    };

                    ReadKernel(
                        compute,
                        "ReadbackNamed",
                        constants,
                        readback,
                        named,
                        ref command);
                    readback.Release();
                    readback = new ComputeBuffer(
                        bridge.Length,
                        sizeof(uint),
                        ComputeBufferType.Structured);
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
                bool bridgeExact = PrefixEqual(expected, bridge);
                bool pathsExact = ReadbackPrefixEqual(named, bridge);
                bool unownedZero = UnownedSectionsAreZero(named);
                uint[] namedPayload = Slice(named, 1, expected.Length);
                uint[] bridgePayload = Slice(
                    bridge,
                    1,
                    bridgeWordCount);

                if (!namedReady)
                    failures.Add("named_ready_flag: expected 0x3F800000");
                if (!bridgeReady)
                    failures.Add("bridge_ready_flag: expected 0x3F800000");
                if (!namedExact)
                    failures.Add("named_gpu_readback: full b34 words differ");
                if (!bridgeExact)
                    failures.Add("bridge_gpu_readback: CB5 prefix words differ");
                if (!pathsExact)
                    failures.Add("named_bridge_parity: first 401 vectors differ");
                if (!unownedZero)
                {
                    failures.Add(
                        "unowned_sections: non-punctual or padding words are nonzero");
                }

                RejectionReport[] rejections =
                {
                    VerifyDestinationRejection(),
                    VerifyArrayRejection(),
                    VerifyTileRejection(),
                    VerifyFaceRejection(),
                    VerifyInactiveSlotRejection(),
                    VerifyRectRejection(),
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
                        "endfield-recovered-deferred-shadow-data-validation-v1",
                    valid = failures.Count == 0,
                    graphicsApi = api,
                    defaultOff = true,
                    pass0ConsumerEnabled = false,
                    sourceAuditPath = sourceAuditPath,
                    sourceAuditSha256 = sourceHash,
                    expectedSourceAuditSha256 = ExpectedSourceAuditSha256,
                    sourceAuditHashMatches = sourceHashMatches,
                    bufferBytes =
                        EndfieldRecoveredDeferredShadowDataContract.SizeBytes,
                    vectorCount =
                        EndfieldRecoveredDeferredShadowDataContract.VectorCount,
                    d3d11SelectedBytes =
                        EndfieldRecoveredDeferredShadowDataContract
                            .D3D11SelectedSizeBytes,
                    d3d11SelectedVectors =
                        EndfieldRecoveredDeferredShadowDataContract
                            .D3D11SelectedVectorCount,
                    fixtureTileResolution = tileResolution,
                    fixtureFaceCount = faceCount,
                    namedReadyObserved = namedReady,
                    bridgeReadyObserved = bridgeReady,
                    namedWordsExact = namedExact,
                    bridgeWordsExact = bridgeExact,
                    namedBridgePrefixExact = pathsExact,
                    unownedSectionsZero = unownedZero,
                    expectedWordsSha256 = Sha256Words(expected),
                    namedWordsSha256 = Sha256Words(namedPayload),
                    bridgeWordsSha256 = Sha256Words(bridgePayload),
                    expectedNonzeroWords = CountNonzero(expected),
                    namedNonzeroWords = CountNonzero(namedPayload),
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
                        "Deferred ShadowData validation failed: " +
                        string.Join("; ", report.failures) +
                        ". Report=" + reportPath);
                }
                Debug.Log(
                    "Recovered deferred ShadowData validation passed: " +
                    "all 2860 named words and 1604 CB5 words exact, " +
                    "unowned sections zero, fail-closed gates=6/6, api=" +
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

        private static void RequireSelector(
            bool requested,
            string selector,
            List<string> failures)
        {
            if (!requested)
                failures.Add("selector: " + selector + " must be explicitly enabled");
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
                name = "Verify deferred ShadowData " + kernelName
            };
            int kernel = compute.FindKernel(kernelName);
            command.SetGlobalConstantBuffer(
                constants,
                ConstantsId,
                0,
                EndfieldRecoveredDeferredShadowDataContract.SizeBytes);
            command.SetGlobalConstantBuffer(
                constants,
                BridgeConstantsId,
                0,
                EndfieldRecoveredDeferredShadowDataContract
                    .D3D11SelectedSizeBytes);
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
            Fixture(out Matrix4x4[] m, out Vector4[] p, out Vector4[] r);
            bool accepted = EndfieldRecoveredDeferredShadowDataContract
                .TryBuildSelectedPunctualSubset(
                    m, p, r, Texel(), 1024, 1,
                    new Vector4[1], out string diagnostic);
            return Rejection(
                "destination_size",
                "exactly 715 float4 vectors",
                accepted,
                diagnostic);
        }

        private static RejectionReport VerifyArrayRejection()
        {
            bool accepted = EndfieldRecoveredDeferredShadowDataContract
                .TryBuildSelectedPunctualSubset(
                    new Matrix4x4[1], new Vector4[56], new Vector4[56],
                    Texel(), 1024, 1, new Vector4[715],
                    out string diagnostic);
            return Rejection(
                "array_size",
                "exactly 56 rows",
                accepted,
                diagnostic);
        }

        private static RejectionReport VerifyTileRejection()
        {
            Fixture(out Matrix4x4[] m, out Vector4[] p, out Vector4[] r);
            bool accepted = EndfieldRecoveredDeferredShadowDataContract
                .TryBuildSelectedPunctualSubset(
                    m, p, r, Texel(), 768, 1, new Vector4[715],
                    out string diagnostic);
            return Rejection(
                "tile_resolution",
                "exactly 512 or 1024",
                accepted,
                diagnostic);
        }

        private static RejectionReport VerifyFaceRejection()
        {
            Fixture(out Matrix4x4[] m, out Vector4[] p, out Vector4[] r);
            bool accepted = EndfieldRecoveredDeferredShadowDataContract
                .TryBuildSelectedPunctualSubset(
                    m, p, r, Texel(), 1024, 2, new Vector4[715],
                    out string diagnostic);
            return Rejection(
                "face_count",
                "exactly 1 or 6",
                accepted,
                diagnostic);
        }

        private static RejectionReport VerifyInactiveSlotRejection()
        {
            Fixture(out Matrix4x4[] m, out Vector4[] p, out Vector4[] r);
            p[39] = Vector4.one;
            bool accepted = EndfieldRecoveredDeferredShadowDataContract
                .TryBuildSelectedPunctualSubset(
                    m, p, r, Texel(), 1024, 1, new Vector4[715],
                    out string diagnostic);
            return Rejection(
                "inactive_slot",
                "must remain exactly zero",
                accepted,
                diagnostic);
        }

        private static RejectionReport VerifyRectRejection()
        {
            Fixture(out Matrix4x4[] m, out Vector4[] p, out Vector4[] r);
            r[40].x = 0.5f;
            bool accepted = EndfieldRecoveredDeferredShadowDataContract
                .TryBuildSelectedPunctualSubset(
                    m, p, r, Texel(), 1024, 1, new Vector4[715],
                    out string diagnostic);
            return Rejection(
                "active_rect",
                "native dynamic-cache atlas tile",
                accepted,
                diagnostic);
        }

        private static void Fixture(
            out Matrix4x4[] matrices,
            out Vector4[] parameters,
            out Vector4[] rects)
        {
            matrices = new Matrix4x4[56];
            parameters = new Vector4[56];
            rects = new Vector4[56];
            matrices[40] = Matrix4x4.identity;
            parameters[40] = new Vector4(0.0f, 0.003f, 0.002f, 1.0f);
            rects[40] = new Vector4(4.0f / 6.0f, 0.0f, 5.0f / 6.0f, 0.25f);
        }

        private static Vector4 Texel()
        {
            return new Vector4(
                1.0f / 6144.0f,
                1.0f / 4096.0f,
                6144.0f,
                4096.0f);
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

        private static bool PrefixEqual(uint[] expected, uint[] readback)
        {
            if (readback.Length < 2 ||
                readback.Length - 1 > expected.Length)
            {
                return false;
            }
            for (int index = 0; index < readback.Length - 1; index++)
            {
                if (expected[index] != readback[index + 1])
                    return false;
            }
            return true;
        }

        private static bool ReadbackPrefixEqual(uint[] named, uint[] bridge)
        {
            for (int index = 1; index < bridge.Length; index++)
            {
                if (named[index] != bridge[index])
                    return false;
            }
            return true;
        }

        private static bool UnownedSectionsAreZero(uint[] named)
        {
            for (int vector = 0; vector < 715; vector++)
            {
                bool owned = vector >= 64 && vector <= 400;
                if (owned)
                    continue;
                for (int lane = 0; lane < 4; lane++)
                {
                    if (named[1 + vector * 4 + lane] != 0u)
                        return false;
                }
            }
            return true;
        }

        private static uint[] Slice(uint[] source, int offset, int count)
        {
            var result = new uint[count];
            Array.Copy(source, offset, result, 0, count);
            return result;
        }

        private static int CountNonzero(uint[] words)
        {
            int count = 0;
            foreach (uint word in words)
            {
                if (word != 0u)
                    count++;
            }
            return count;
        }

        private static string Sha256Words(uint[] words)
        {
            var bytes = new byte[words.Length * sizeof(uint)];
            Buffer.BlockCopy(words, 0, bytes, 0, bytes.Length);
            using (SHA256 sha = SHA256.Create())
            {
                return BitConverter.ToString(sha.ComputeHash(bytes))
                    .Replace("-", string.Empty)
                    .ToLowerInvariant();
            }
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
