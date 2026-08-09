using System;
using System.Collections.Generic;
using System.IO;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Verifies that the exact environment Cubemap's recovered oct/global
    /// resources coexist with, and do not overwrite, the canonical raw
    /// light/zero-reflection binning buffer in one command stream.
    /// </summary>
    public static class EndfieldRecoveredReflectionFrameBatchVerifier
    {
        private const string ProbeResourceName =
            "EndfieldRecoveredReflectionFrameProbe";
        private const string ProbeKernelName = "ReadFrame";
        private const int Width = 3840;
        private const int Height = 2160;
        private const int ReadbackWordCount = 30;

        private static readonly int BinningBufferId =
            Shader.PropertyToID("_BinningBuffer");
        private static readonly int CanonicalReadyId =
            Shader.PropertyToID("_EndfieldRecoveredCanonicalBinningReady");
        private static readonly int ReadbackId = Shader.PropertyToID(
            "_EndfieldRecoveredReflectionFrameReadback");

        [Serializable]
        private sealed class ValidationReport
        {
            public string schema;
            public bool valid;
            public string graphicsApi;
            public string diagnosticScope;
            public bool defaultOff;
            public string sourceCubemapAssetPath;
            public string sourcePayloadSha256;
            public bool missingSourceRejected;
            public string missingSourceDiagnostic;
            public bool wrongSourceRejected;
            public string wrongSourceDiagnostic;
            public bool recoveredPublicationReturnedReady;
            public bool canonicalReadyObserved;
            public bool reflectionReadyObserved;
            public bool canonicalBufferPreserved;
            public bool reflectionGlobalDataMatches;
            public bool octDimensionsMatch;
            public bool octCenterFiniteNonzero;
            public string[] canonicalSentinelWords;
            public string[] expectedGlobalWords;
            public string[] actualGlobalWords;
            public int octWidth;
            public int octHeight;
            public int octSlices;
            public int octMipCount;
            public string[] octCenterBits;
            public string[] failures;
        }

        [MenuItem(
            "Endfield/Character Recovery Lab/" +
            "Verify Recovered Canonical Reflection Frame")]
        public static void VerifyBatch()
        {
            string projectRoot = Path.GetFullPath(
                Path.Combine(Application.dataPath, ".."));
            string outputRoot = Path.Combine(
                projectRoot,
                "scratch",
                "character_recovery",
                "canonical_reflection_frame");
            Directory.CreateDirectory(outputRoot);
            var failures = new List<string>();

            EndfieldRecoveredCharCubemapImporter
                .VerifyRecoveredCharInfoEnvironmentReflectionCubemap();
            Cubemap source = AssetDatabase.LoadAssetAtPath<Cubemap>(
                EndfieldRecoveredCharCubemapImporter
                    .EnvironmentReflectionCubemapAssetPath);
            Cubemap wrongSource = AssetDatabase.LoadAssetAtPath<Cubemap>(
                EndfieldRecoveredCharCubemapImporter.CubemapAssetPath);
            ComputeShader probe = Resources.Load<ComputeShader>(
                ProbeResourceName);
            if (source == null || wrongSource == null || probe == null)
            {
                throw new InvalidOperationException(
                    "Required exact Cubemaps or reflection-frame probe are missing");
            }

            EndfieldRecoveredCanonicalBinningLayoutContract.Layout layout;
            string layoutFailure;
            if (!EndfieldRecoveredCanonicalBinningLayoutContract.TryBuild(
                    Width,
                    Height,
                    out layout,
                    out layoutFailure))
            {
                throw new InvalidOperationException(
                    "Known-good frame layout was rejected: " + layoutFailure);
            }

            GameObject cameraObject = null;
            EndfieldRecoveredReflectionProbeFallback owner = null;
            ComputeBuffer canonical = null;
            ComputeBuffer readback = null;
            CommandBuffer command = null;
            bool missingSourceRejected = false;
            string missingSourceDiagnostic = string.Empty;
            bool wrongSourceRejected = false;
            string wrongSourceDiagnostic = string.Empty;
            bool publicationReady = false;
            uint[] actual = new uint[ReadbackWordCount];
            uint[] canonicalWords = BuildCanonicalWords(layout);
            try
            {
                cameraObject = new GameObject(
                    "Recovered Canonical Reflection Frame Camera");
                Camera camera = cameraObject.AddComponent<Camera>();
                camera.orthographic = false;
                camera.nearClipPlane = 0.1f;
                camera.farClipPlane = 50.0f;
                camera.fieldOfView = 60.0f;
                camera.aspect = (float)Width / Height;

                owner = new EndfieldRecoveredReflectionProbeFallback();
                canonical = new ComputeBuffer(
                    layout.totalWordCount,
                    sizeof(uint),
                    ComputeBufferType.Raw);
                canonical.SetData(canonicalWords);
                readback = new ComputeBuffer(
                    ReadbackWordCount,
                    sizeof(uint),
                    ComputeBufferType.Structured);
                readback.SetData(actual);
                command = new CommandBuffer
                {
                    name = "Verify Recovered Canonical Reflection Frame"
                };

                string failure;
                missingSourceRejected =
                    !owner.PrepareAndPublishRecoveredResources(
                        camera,
                        Width,
                        Height,
                        null,
                        command,
                        false,
                        out failure);
                missingSourceDiagnostic = failure ?? string.Empty;
                wrongSourceRejected =
                    !owner.PrepareAndPublishRecoveredResources(
                        camera,
                        Width,
                        Height,
                        wrongSource,
                        command,
                        false,
                        out failure);
                wrongSourceDiagnostic = failure ?? string.Empty;
                if (!missingSourceRejected ||
                    missingSourceDiagnostic.IndexOf(
                        "not bound",
                        StringComparison.Ordinal) < 0)
                {
                    failures.Add(
                        "missing_source_gate: expected rejection containing " +
                        "'not bound', actual '" + missingSourceDiagnostic + "'");
                }
                if (!wrongSourceRejected ||
                    wrongSourceDiagnostic.IndexOf(
                        "not the exact T_hdri_env_char_01",
                        StringComparison.Ordinal) < 0)
                {
                    failures.Add(
                        "wrong_source_gate: expected exact-asset rejection, actual '" +
                        wrongSourceDiagnostic + "'");
                }

                command.SetGlobalBuffer(BinningBufferId, canonical);
                command.SetGlobalFloat(CanonicalReadyId, 1.0f);
                publicationReady = owner.PrepareAndPublishRecoveredResources(
                    camera,
                    Width,
                    Height,
                    source,
                    command,
                    false,
                    out failure);
                if (!publicationReady)
                {
                    failures.Add(
                        "recovered_publication: exact source was rejected: " +
                        failure);
                }

                int probeKernel = probe.FindKernel(ProbeKernelName);
                command.SetComputeBufferParam(
                    probe,
                    probeKernel,
                    ReadbackId,
                    readback);
                command.DispatchCompute(probe, probeKernel, 1, 1, 1);
                Graphics.ExecuteCommandBuffer(command);
                readback.GetData(actual);
            }
            finally
            {
                command?.Release();
                readback?.Release();
                canonical?.Release();
                owner?.Dispose();
                if (cameraObject != null)
                    UnityEngine.Object.DestroyImmediate(cameraObject);
            }

            uint[] expectedGlobal = BuildExpectedGlobalWords();
            uint[] actualGlobal = new uint[expectedGlobal.Length];
            Array.Copy(actual, 6, actualGlobal, 0, actualGlobal.Length);
            bool canonicalReadyObserved = actual[0] == FloatBits(1.0f);
            bool reflectionReadyObserved = actual[1] == FloatBits(1.0f);
            bool canonicalPreserved =
                actual[2] == canonicalWords[0] &&
                actual[3] == canonicalWords[layout.lightWordCount - 1] &&
                actual[4] == 0u &&
                actual[5] == 0u;
            bool globalMatches = WordsEqual(expectedGlobal, actualGlobal);
            bool dimensionsMatch =
                actual[22] == 576u &&
                actual[23] == 576u &&
                actual[24] == 32u &&
                actual[25] == 10u;
            bool centerFiniteNonzero = IsFiniteNonzeroFloat4(actual, 26);
            if (!canonicalReadyObserved)
                failures.Add("canonical_ready: probe did not observe 1.0");
            if (!reflectionReadyObserved)
                failures.Add("reflection_ready: probe did not observe 1.0");
            if (!canonicalPreserved)
                failures.Add("canonical_buffer: reflection publication overwrote a sentinel");
            if (!globalMatches)
                failures.Add("reflection_global: first four vectors differ");
            if (!dimensionsMatch)
                failures.Add("reflection_oct: expected 576x576x32 with 10 mips");
            if (!centerFiniteNonzero)
                failures.Add("reflection_oct: mip-0 center is zero or non-finite");

            string api = ApiName(SystemInfo.graphicsDeviceType);
            var report = new ValidationReport
            {
                schema = "endfield-recovered-canonical-reflection-frame-v1",
                valid = failures.Count == 0,
                graphicsApi = api,
                diagnosticScope =
                    "same-command canonical raw binning plus exact no-local " +
                    "reflection oct/global publication; pass-0 remains default-off",
                defaultOff = true,
                sourceCubemapAssetPath =
                    EndfieldRecoveredCharCubemapImporter
                        .EnvironmentReflectionCubemapAssetPath,
                sourcePayloadSha256 =
                    EndfieldRecoveredCharCubemapImporter
                        .EnvironmentReflectionExpectedPayloadSha256,
                missingSourceRejected = missingSourceRejected,
                missingSourceDiagnostic = missingSourceDiagnostic,
                wrongSourceRejected = wrongSourceRejected,
                wrongSourceDiagnostic = wrongSourceDiagnostic,
                recoveredPublicationReturnedReady = publicationReady,
                canonicalReadyObserved = canonicalReadyObserved,
                reflectionReadyObserved = reflectionReadyObserved,
                canonicalBufferPreserved = canonicalPreserved,
                reflectionGlobalDataMatches = globalMatches,
                octDimensionsMatch = dimensionsMatch,
                octCenterFiniteNonzero = centerFiniteNonzero,
                canonicalSentinelWords = HexWords(new[]
                {
                    actual[2], actual[3], actual[4], actual[5]
                }),
                expectedGlobalWords = HexWords(expectedGlobal),
                actualGlobalWords = HexWords(actualGlobal),
                octWidth = unchecked((int)actual[22]),
                octHeight = unchecked((int)actual[23]),
                octSlices = unchecked((int)actual[24]),
                octMipCount = unchecked((int)actual[25]),
                octCenterBits = HexWords(new[]
                {
                    actual[26], actual[27], actual[28], actual[29]
                }),
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
                    "Canonical reflection-frame validation failed: " +
                    string.Join("; ", report.failures) +
                    ". Report=" + reportPath);
            }
            Debug.Log(
                "Recovered canonical reflection frame validation passed: " +
                "both readiness flags=1, canonical sentinels preserved, " +
                "ReflectionProbeGlobalData vectors exact, oct=576x576x32/10 mips, " +
                "source gates=2/2, api=" + api + ", report=" + reportPath +
                ". Pass-0 remains default-off.");
        }

        private static uint[] BuildCanonicalWords(
            EndfieldRecoveredCanonicalBinningLayoutContract.Layout layout)
        {
            var words = new uint[layout.totalWordCount];
            for (uint index = 0; index < layout.lightWordCount; index++)
                words[index] = unchecked(index * 2654435761u) ^ 0xA5C31F29u;
            return words;
        }

        private static uint[] BuildExpectedGlobalWords()
        {
            const float nearClip = 0.1f;
            float nearHeight = 2.0f * nearClip * Mathf.Tan(
                60.0f * 0.5f * Mathf.Deg2Rad);
            Vector4[] values =
            {
                new Vector4(120.0f, 68.0f, 8160.0f, 1.0f / 32.0f),
                new Vector4(1024.0f, 1.0f, 1.0f, 512.0f / 576.0f),
                new Vector4(
                    0.0f,
                    nearHeight,
                    nearHeight * 32.0f / 68.0f,
                    32.0f / 576.0f),
                new Vector4(
                    -0.0075507620349526405f,
                    0.01217081118375063f,
                    0.47223734855651855f,
                    1.0963057279586792f)
            };
            var words = new uint[16];
            for (int index = 0; index < values.Length; index++)
            {
                words[index * 4 + 0] = FloatBits(values[index].x);
                words[index * 4 + 1] = FloatBits(values[index].y);
                words[index * 4 + 2] = FloatBits(values[index].z);
                words[index * 4 + 3] = FloatBits(values[index].w);
            }
            return words;
        }

        private static bool IsFiniteNonzeroFloat4(uint[] words, int offset)
        {
            bool nonzero = false;
            for (int index = 0; index < 4; index++)
            {
                float value = BitConverter.Int32BitsToSingle(
                    unchecked((int)words[offset + index]));
                if (float.IsNaN(value) || float.IsInfinity(value))
                    return false;
                nonzero |= value != 0.0f;
            }
            return nonzero;
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

        private static string[] HexWords(uint[] words)
        {
            var result = new string[words.Length];
            for (int index = 0; index < words.Length; index++)
                result[index] = "0x" + words[index].ToString("X8");
            return result;
        }

        private static string ApiName(GraphicsDeviceType api)
        {
            if (api == GraphicsDeviceType.Direct3D11)
                return "d3d11";
            if (api == GraphicsDeviceType.Direct3D12)
                return "d3d12";
            return api.ToString().ToLowerInvariant();
        }
    }
}
