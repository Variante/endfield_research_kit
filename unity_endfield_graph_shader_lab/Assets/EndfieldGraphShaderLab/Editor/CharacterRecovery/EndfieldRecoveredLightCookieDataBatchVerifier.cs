using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLabEditor
{
    public static class EndfieldRecoveredLightCookieDataBatchVerifier
    {
        private const string ComputeResourceName =
            "EndfieldRecoveredLightCookieDataProbe";
        private const string KernelName = "Readback";

        private static readonly int CookieDataId =
            Shader.PropertyToID("_LightCookieData");
        private static readonly int ReadbackId = Shader.PropertyToID(
            "_EndfieldRecoveredLightCookieDataReadback");

        [Serializable]
        private sealed class GateReport
        {
            public string gate;
            public bool rejected;
            public string diagnostic;
        }

        [Serializable]
        private sealed class ValidationReport
        {
            public string schema;
            public string graphicsDeviceType;
            public int sizeBytes;
            public int atlasBytes;
            public int matrixBytes;
            public int vectorCount;
            public int wordCount;
            public string fixtureSha256;
            public string gpuReadbackSha256;
            public bool gpuReadbackMatches;
            public bool zeroCookieFrameAccepted;
            public GateReport[] failClosedGates;
            public string[] failures;
        }

        public static void VerifyBatch()
        {
            List<string> failures = new List<string>();
            ValidateConstants(failures);

            string validFailure;
            bool valid = EndfieldGraphShaderLab
                .EndfieldRecoveredLightCookieDataContract
                .TryValidateZeroCookieFrame(8, false, out validFailure);
            if (!valid)
                failures.Add("valid zero-cookie fixture rejected: " + validFailure);

            GateReport[] gates =
            {
                RunGate("negative light count", -1, false),
                RunGate("light count above 32", 33, false),
                RunGate("non-empty cookie set", 8, true)
            };
            foreach (GateReport gate in gates)
            {
                if (!gate.rejected || string.IsNullOrEmpty(gate.diagnostic))
                {
                    failures.Add(
                        $"fail-closed gate '{gate.gate}' did not return a diagnostic");
                }
            }

            Vector4[] fixture = new Vector4[
                EndfieldGraphShaderLab.EndfieldRecoveredLightCookieDataContract.VectorCount];
            EndfieldGraphShaderLab.EndfieldRecoveredLightCookieDataContract
                .FillDiagnosticFixture(fixture);
            uint[] expected = ToWords(fixture);
            uint[] actual = new uint[expected.Length];
            bool gpuMatches = false;

            ComputeShader compute = Resources.Load<ComputeShader>(ComputeResourceName);
            if (compute == null)
            {
                failures.Add($"Resources/{ComputeResourceName}.compute was not found");
            }
            else
            {
                try
                {
                    int kernel = compute.FindKernel(KernelName);
                    RunGpuReadback(compute, kernel, fixture, actual);
                    gpuMatches = WordsEqual(expected, actual);
                    if (!gpuMatches)
                    {
                        int mismatch = FirstMismatch(expected, actual);
                        failures.Add(
                            $"GPU constant-buffer readback mismatch at word {mismatch}: " +
                            $"expected 0x{expected[mismatch]:x8}, actual 0x{actual[mismatch]:x8}");
                    }
                }
                catch (Exception exception)
                {
                    failures.Add("GPU validation failed: " + exception);
                }
            }

            string api = ApiName(SystemInfo.graphicsDeviceType);
            string reportDirectory = Path.Combine(
                Directory.GetParent(Application.dataPath).FullName,
                "scratch",
                "character_recovery",
                "light_cookie_data");
            Directory.CreateDirectory(reportDirectory);
            string reportPath = Path.Combine(
                reportDirectory,
                "gpu_validation_" + api + ".json");
            ValidationReport report = new ValidationReport
            {
                schema = "endfield.recovered-light-cookie-data-gpu-validation.v1",
                graphicsDeviceType = SystemInfo.graphicsDeviceType.ToString(),
                sizeBytes = EndfieldGraphShaderLab
                    .EndfieldRecoveredLightCookieDataContract.SizeBytes,
                atlasBytes = EndfieldGraphShaderLab
                    .EndfieldRecoveredLightCookieDataContract.AtlasBytes,
                matrixBytes = EndfieldGraphShaderLab
                    .EndfieldRecoveredLightCookieDataContract.MatrixBytes,
                vectorCount = fixture.Length,
                wordCount = expected.Length,
                fixtureSha256 = Sha256(expected),
                gpuReadbackSha256 = Sha256(actual),
                gpuReadbackMatches = gpuMatches,
                zeroCookieFrameAccepted = valid,
                failClosedGates = gates,
                failures = failures.ToArray()
            };
            File.WriteAllText(
                reportPath,
                JsonUtility.ToJson(report, true) + Environment.NewLine);

            if (failures.Count != 0)
                throw new InvalidOperationException(string.Join(" | ", failures));

            Debug.Log(
                "Recovered LightCookieData validation passed: exact 2,560-byte " +
                $"layout, {expected.Length}/{expected.Length} GPU words, API={api}, " +
                $"report={reportPath}. Non-empty retail cookie atlases remain open.");
        }

        private static void ValidateConstants(List<string> failures)
        {
            Type contract = typeof(EndfieldGraphShaderLab
                .EndfieldRecoveredLightCookieDataContract);
            if (EndfieldGraphShaderLab.EndfieldRecoveredLightCookieDataContract.MaxCookieCount != 32 ||
                EndfieldGraphShaderLab.EndfieldRecoveredLightCookieDataContract.AtlasBytes != 512 ||
                EndfieldGraphShaderLab.EndfieldRecoveredLightCookieDataContract.MatrixBytes != 2048 ||
                EndfieldGraphShaderLab.EndfieldRecoveredLightCookieDataContract.SizeBytes != 2560 ||
                EndfieldGraphShaderLab.EndfieldRecoveredLightCookieDataContract.VectorCount != 160)
            {
                failures.Add("LightCookieData public layout constants changed");
            }
            if (contract == null)
                failures.Add("LightCookieData contract type was not loaded");
        }

        private static GateReport RunGate(string name, int count, bool hasCookie)
        {
            string diagnostic;
            bool accepted = EndfieldGraphShaderLab
                .EndfieldRecoveredLightCookieDataContract
                .TryValidateZeroCookieFrame(count, hasCookie, out diagnostic);
            return new GateReport
            {
                gate = name,
                rejected = !accepted,
                diagnostic = diagnostic
            };
        }

        private static void RunGpuReadback(
            ComputeShader compute,
            int kernel,
            Vector4[] fixture,
            uint[] actual)
        {
            ComputeBuffer constants = null;
            ComputeBuffer readback = null;
            CommandBuffer command = null;
            try
            {
                constants = new ComputeBuffer(
                    fixture.Length,
                    sizeof(float) * 4,
                    ComputeBufferType.Constant);
                constants.SetData(fixture);
                readback = new ComputeBuffer(
                    fixture.Length,
                    sizeof(uint) * 4,
                    ComputeBufferType.Structured);
                readback.SetData(new Vector4[fixture.Length]);

                command = new CommandBuffer
                {
                    name = "Verify Recovered LightCookieData Global Binding"
                };
                command.SetGlobalConstantBuffer(
                    constants,
                    CookieDataId,
                    0,
                    EndfieldGraphShaderLab.EndfieldRecoveredLightCookieDataContract.SizeBytes);
                command.SetComputeBufferParam(compute, kernel, ReadbackId, readback);
                command.DispatchCompute(compute, kernel, 3, 1, 1);
                Graphics.ExecuteCommandBuffer(command);

                Vector4[] values = new Vector4[fixture.Length];
                readback.GetData(values);
                uint[] words = ToWords(values);
                Array.Copy(words, actual, words.Length);
            }
            finally
            {
                command?.Release();
                readback?.Release();
                constants?.Release();
            }
        }

        private static uint[] ToWords(Vector4[] values)
        {
            uint[] result = new uint[values.Length * 4];
            for (int index = 0; index < values.Length; index++)
            {
                result[index * 4] = Bits(values[index].x);
                result[index * 4 + 1] = Bits(values[index].y);
                result[index * 4 + 2] = Bits(values[index].z);
                result[index * 4 + 3] = Bits(values[index].w);
            }
            return result;
        }

        private static uint Bits(float value)
        {
            return unchecked((uint)BitConverter.SingleToInt32Bits(value));
        }

        private static bool WordsEqual(uint[] left, uint[] right)
        {
            return FirstMismatch(left, right) < 0;
        }

        private static int FirstMismatch(uint[] left, uint[] right)
        {
            if (left.Length != right.Length)
                return 0;
            for (int index = 0; index < left.Length; index++)
            {
                if (left[index] != right[index])
                    return index;
            }
            return -1;
        }

        private static string Sha256(uint[] words)
        {
            byte[] bytes = new byte[words.Length * sizeof(uint)];
            Buffer.BlockCopy(words, 0, bytes, 0, bytes.Length);
            using (SHA256 hash = SHA256.Create())
            {
                return BitConverter.ToString(hash.ComputeHash(bytes))
                    .Replace("-", string.Empty)
                    .ToLowerInvariant();
            }
        }

        private static string ApiName(GraphicsDeviceType type)
        {
            return type == GraphicsDeviceType.Direct3D12 ? "d3d12" :
                type == GraphicsDeviceType.Direct3D11 ? "d3d11" :
                type.ToString().ToLowerInvariant();
        }
    }
}
