using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Verifies the recovered 48-byte LightCulling+0x60 ABI on CPU and through
    /// the same global constant-buffer binding used by the runtime port. The
    /// fixture count is source-closed only for the isolated Wulfa Overview rig.
    /// </summary>
    public static class EndfieldRecoveredLightBinningConstantsBatchVerifier
    {
        private const string ComputeResourceName =
            "EndfieldRecoveredLightBinningConstantsProbe";
        private const string KernelName = "Readback";
        private const string SourceAuditRelativePath =
            "scratch/reverse_engineering/zhuangfy_gacha_light_binning_producer/audit.json";
        private const string ExpectedSourceAuditSha256 =
            "a0faf1fcc22e144efe01a62b0de922ee9910f64543a0c5d09577b72f0e7af61e";

        private static readonly int ConstantsId =
            Shader.PropertyToID("_LightBinningConstants");
        private static readonly int ReadbackId = Shader.PropertyToID(
            "_EndfieldRecoveredLightBinningConstantsReadback");

        [Serializable]
        private sealed class FieldReport
        {
            public string name;
            public int offset;
            public string expectedBits;
            public string actualBits;
            public bool matches;
        }

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
            public bool canonicalBindingDefaultOff;
            public bool retailWholeSceneLightListClosed;
            public string sourceAuditPath;
            public string sourceAuditSha256;
            public string expectedSourceAuditSha256;
            public bool sourceAuditHashMatches;
            public int managedSizeBytes;
            public int recoveredSizeBytes;
            public bool managedSizeMatches;
            public int fixtureLightCount;
            public int fixtureWidth;
            public int fixtureHeight;
            public float fixtureNearClip;
            public float fixtureFarClip;
            public int fixtureNumTiles;
            public float fixtureNumTilesX;
            public float fixtureNumTilesY;
            public string computeResource;
            public string kernel;
            public bool globalConstantBufferGpuReadbackMatches;
            public FieldReport[] fields;
            public RejectionReport[] failClosedGates;
            public string[] failures;
        }

        [MenuItem(
            "Endfield/Character Recovery Lab/" +
            "Verify Recovered Light Binning Constants")]
        public static void VerifyBatch()
        {
            string projectRoot = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
            string repositoryRoot = Path.GetFullPath(Path.Combine(projectRoot, ".."));
            string sourceAuditPath = Path.Combine(
                repositoryRoot,
                SourceAuditRelativePath.Replace('/', Path.DirectorySeparatorChar));
            string outputRoot = Path.Combine(
                projectRoot,
                "scratch",
                "character_recovery",
                "light_binning_constants");
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
                    ", actual " + (string.IsNullOrEmpty(sourceHash) ? "missing" : sourceHash) +
                    ", source=" + sourceAuditPath);
            }

            int managedSize = Marshal.SizeOf<
                EndfieldRecoveredLightBinningConstantsContract.Data>();
            if (managedSize != EndfieldRecoveredLightBinningConstantsContract.SizeBytes)
            {
                failures.Add(
                    "managed_size: expected 48 bytes, actual " + managedSize);
            }

            EndfieldRecoveredLightBinningConstantsContract.Data fixture;
            string fixtureFailure;
            if (!EndfieldRecoveredLightBinningConstantsContract.TryBuild(
                    8,
                    3840,
                    2160,
                    0.1f,
                    50.0f,
                    out fixture,
                    out fixtureFailure))
            {
                throw new InvalidOperationException(
                    "Known-good Wulfa fixture was rejected: " + fixtureFailure);
            }
            if (fixture.numTiles != 8160 ||
                fixture.numTilesX != 120.0f ||
                fixture.numTilesY != 68.0f)
            {
                failures.Add(
                    "fixture_tiles: expected 120x68=8160, actual " +
                    fixture.numTilesX + "x" + fixture.numTilesY + "=" + fixture.numTiles);
            }

            string[] fieldNames =
            {
                "lightCount", "numTiles", "actualWidth", "actualHeight",
                "tileSize", "numTilesX", "numTilesY", "numSliceZ",
                "nearClipPlane", "farClipPlane", "zBinSlice", "invZBinSlice"
            };
            uint[] expected = BuildExpectedWords(fixture);
            uint[] actual = new uint[expected.Length];
            bool gpuMatches = false;

            if (!SystemInfo.supportsComputeShaders)
            {
                failures.Add("gpu_capability: compute shaders are unavailable");
            }
            else
            {
                ComputeShader compute = Resources.Load<ComputeShader>(ComputeResourceName);
                if (compute == null)
                {
                    failures.Add(
                        "compute_resource: Resources/" + ComputeResourceName +
                        ".compute is unavailable");
                }
                else
                {
                    int kernel = compute.FindKernel(KernelName);
                    RunGpuReadback(compute, kernel, fixture, actual);
                    gpuMatches = WordsEqual(expected, actual);
                    if (!gpuMatches)
                    {
                        failures.Add(
                            "gpu_readback: global _LightBinningConstants words differ " +
                            "from the recovered 48-byte fixture");
                    }
                }
            }

            var fieldReports = new FieldReport[fieldNames.Length];
            for (int index = 0; index < fieldNames.Length; index++)
            {
                int offset = checked((int)Marshal.OffsetOf<
                    EndfieldRecoveredLightBinningConstantsContract.Data>(
                        fieldNames[index]));
                int expectedOffset = index * sizeof(uint);
                bool offsetMatches = offset == expectedOffset;
                bool bitsMatch = expected[index] == actual[index];
                if (!offsetMatches)
                {
                    failures.Add(
                        "field_offset:" + fieldNames[index] + " expected " +
                        expectedOffset + ", actual " + offset);
                }
                fieldReports[index] = new FieldReport
                {
                    name = fieldNames[index],
                    offset = offset,
                    expectedBits = Hex(expected[index]),
                    actualBits = Hex(actual[index]),
                    matches = offsetMatches && bitsMatch
                };
            }

            RejectionReport[] rejectionReports =
            {
                VerifyRejection("negative_light_count", -1, 1920, 1080, 0.1f, 50.0f,
                    "outside the recovered 0..32 range"),
                VerifyRejection("over_cap_light_count", 33, 1920, 1080, 0.1f, 50.0f,
                    "outside the recovered 0..32 range"),
                VerifyRejection("zero_width", 8, 0, 1080, 0.1f, 50.0f,
                    "render dimensions must be positive"),
                VerifyRejection("reversed_clip_range", 8, 1920, 1080, 50.0f, 0.1f,
                    "camera clip range must be finite and ordered"),
                VerifyRejection(
                    "tile_count_overflow",
                    8,
                    int.MaxValue,
                    int.MaxValue,
                    0.1f,
                    50.0f,
                    "tile count")
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

            string api = ApiName(SystemInfo.graphicsDeviceType);
            var report = new ValidationReport
            {
                schema = "endfield-recovered-light-binning-constants-validation-v1",
                valid = failures.Count == 0,
                graphicsApi = api,
                diagnosticScope =
                    "48-byte ABI plus source-closed isolated Wulfa Overview count; " +
                    "not a retail whole-scene light census",
                canonicalBindingDefaultOff = true,
                retailWholeSceneLightListClosed = false,
                sourceAuditPath = sourceAuditPath,
                sourceAuditSha256 = sourceHash,
                expectedSourceAuditSha256 = ExpectedSourceAuditSha256,
                sourceAuditHashMatches = sourceHashMatches,
                managedSizeBytes = managedSize,
                recoveredSizeBytes =
                    EndfieldRecoveredLightBinningConstantsContract.SizeBytes,
                managedSizeMatches = managedSize ==
                    EndfieldRecoveredLightBinningConstantsContract.SizeBytes,
                fixtureLightCount = fixture.lightCount,
                fixtureWidth = fixture.actualWidth,
                fixtureHeight = fixture.actualHeight,
                fixtureNearClip = fixture.nearClipPlane,
                fixtureFarClip = fixture.farClipPlane,
                fixtureNumTiles = fixture.numTiles,
                fixtureNumTilesX = fixture.numTilesX,
                fixtureNumTilesY = fixture.numTilesY,
                computeResource = ComputeResourceName,
                kernel = KernelName,
                globalConstantBufferGpuReadbackMatches = gpuMatches,
                fields = fieldReports,
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
                    "Light-binning constants validation failed: " +
                    string.Join("; ", report.failures) +
                    ". Report=" + reportPath);
            }
            Debug.Log(
                "Recovered LightBinningConstants validation passed: " +
                "size=48, Wulfa fixture=8 lights/120x68 tiles, " +
                "GPU words=12/12, fail-closed gates=5/5, api=" + api +
                ", report=" + reportPath + ". Retail whole-scene light list remains open.");
        }

        private static void RunGpuReadback(
            ComputeShader compute,
            int kernel,
            EndfieldRecoveredLightBinningConstantsContract.Data fixture,
            uint[] actual)
        {
            ComputeBuffer constants = null;
            ComputeBuffer readback = null;
            CommandBuffer command = null;
            try
            {
                constants = new ComputeBuffer(3, sizeof(float) * 4, ComputeBufferType.Constant)
                {
                    name = "Recovered LightBinningConstants Validation Fixture"
                };
                constants.SetData(PackVectors(fixture));
                readback = new ComputeBuffer(12, sizeof(uint), ComputeBufferType.Structured)
                {
                    name = "Recovered LightBinningConstants Validation Readback"
                };
                readback.SetData(new uint[12]);

                command = new CommandBuffer
                {
                    name = "Verify Recovered LightBinningConstants Global Binding"
                };
                command.SetGlobalConstantBuffer(
                    constants,
                    ConstantsId,
                    0,
                    EndfieldRecoveredLightBinningConstantsContract.SizeBytes);
                command.SetComputeBufferParam(compute, kernel, ReadbackId, readback);
                command.DispatchCompute(compute, kernel, 1, 1, 1);
                Graphics.ExecuteCommandBuffer(command);
                readback.GetData(actual);
            }
            finally
            {
                command?.Release();
                constants?.Release();
                readback?.Release();
            }
        }

        private static Vector4[] PackVectors(
            EndfieldRecoveredLightBinningConstantsContract.Data data)
        {
            return new[]
            {
                new Vector4(
                    BitConverter.Int32BitsToSingle(data.lightCount),
                    BitConverter.Int32BitsToSingle(data.numTiles),
                    BitConverter.Int32BitsToSingle(data.actualWidth),
                    BitConverter.Int32BitsToSingle(data.actualHeight)),
                new Vector4(data.tileSize, data.numTilesX, data.numTilesY, data.numSliceZ),
                new Vector4(
                    data.nearClipPlane,
                    data.farClipPlane,
                    data.zBinSlice,
                    data.invZBinSlice)
            };
        }

        private static uint[] BuildExpectedWords(
            EndfieldRecoveredLightBinningConstantsContract.Data data)
        {
            return new[]
            {
                unchecked((uint)data.lightCount),
                unchecked((uint)data.numTiles),
                unchecked((uint)data.actualWidth),
                unchecked((uint)data.actualHeight),
                FloatBits(data.tileSize),
                FloatBits(data.numTilesX),
                FloatBits(data.numTilesY),
                FloatBits(data.numSliceZ),
                FloatBits(data.nearClipPlane),
                FloatBits(data.farClipPlane),
                FloatBits(data.zBinSlice),
                FloatBits(data.invZBinSlice)
            };
        }

        private static RejectionReport VerifyRejection(
            string gate,
            int lightCount,
            int width,
            int height,
            float nearClip,
            float farClip,
            string requiredToken)
        {
            EndfieldRecoveredLightBinningConstantsContract.Data ignored;
            string diagnostic;
            bool accepted = EndfieldRecoveredLightBinningConstantsContract.TryBuild(
                lightCount,
                width,
                height,
                nearClip,
                farClip,
                out ignored,
                out diagnostic);
            return new RejectionReport
            {
                gate = gate,
                input = "lightCount=" + lightCount + ", width=" + width +
                    ", height=" + height + ", near=" + nearClip + ", far=" + farClip,
                requiredDiagnosticToken = requiredToken,
                diagnostic = diagnostic,
                rejected = !accepted,
                diagnosticMatched = !accepted && diagnostic != null &&
                    diagnostic.IndexOf(requiredToken, StringComparison.Ordinal) >= 0
            };
        }

        private static bool WordsEqual(uint[] expected, uint[] actual)
        {
            if (expected.Length != actual.Length)
                return false;
            for (int index = 0; index < expected.Length; index++)
            {
                if (expected[index] != actual[index])
                    return false;
            }
            return true;
        }

        private static uint FloatBits(float value)
        {
            return unchecked((uint)BitConverter.SingleToInt32Bits(value));
        }

        private static string Hex(uint value)
        {
            return "0x" + value.ToString("X8");
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
