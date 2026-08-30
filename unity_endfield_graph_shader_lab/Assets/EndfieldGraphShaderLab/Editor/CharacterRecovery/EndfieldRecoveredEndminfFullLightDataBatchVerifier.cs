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
    /// Verifies the complete Endminf b31 contract independently from the
    /// older SphereOutside-selected zero-subset verifier.
    /// </summary>
    public static class EndfieldRecoveredEndminfFullLightDataBatchVerifier
    {
        private const string ComputeResourceName =
            "EndfieldRecoveredDeferredLightDataProbe";
        private const string ExpectedInvariantSha256 =
            "7b50fb8b2af8658d1b853e9271b087e0899e1913036d9f639bb1ea84dcae5765";
        private const int ActiveVectorCount = 6 + 12 * 8;
        private const int ActiveBytes = ActiveVectorCount * 16;
        private static readonly int[] ExpectedSourceOrder =
            { 7, 4, 2, 6, 10, 3, 9, 5, 8, 0, 11, 1 };
        private static readonly int ConstantsId = Shader.PropertyToID("_LightDataBuffer");
        private static readonly int BridgeConstantsId = Shader.PropertyToID("EndfieldCB4");
        private static readonly int ReadyId = Shader.PropertyToID(
            "_EndfieldRecoveredDeferredLightDataReady");
        private static readonly int ReadbackId = Shader.PropertyToID(
            "_EndfieldRecoveredDeferredLightDataReadback");

        [Serializable]
        private sealed class ValidationReport
        {
            public string schema;
            public bool valid;
            public string graphicsApi;
            public string sourceProvenance;
            public int bufferBytes;
            public int activeBytes;
            public int[] packedSourceOrder;
            public string invariantSha256;
            public bool invariantMatchesCapture;
            public bool inactiveRowsZero;
            public bool namedGpuExact;
            public bool bridgeGpuExact;
            public bool gpuTransportOnly;
            public bool overlapRejected;
            public bool missingAssignmentRejected;
            public bool sourceDirectColorRejected;
            public bool assignmentPlanFollowsPackedOrder;
            public string generatedActivePrefixPath;
            public string[] failures;
        }

        [MenuItem(
            "Endfield/Character Recovery Lab/" +
            "Verify Full Endminf Deferred LightData")]
        public static void VerifyBatch()
        {
            var failures = new List<string>();
            if (!EndfieldOriginalOperatorLightImporter.TryRead(
                    "Endminf",
                    out EndfieldHGOperatorLightData[] sourceLights,
                    out string sourceProvenance) ||
                sourceLights.Length !=
                    EndfieldRecoveredEndminfFullLightDataContract.EndminfPunctualLightCount)
            {
                throw new InvalidOperationException(
                    "The exact 12-row Endminf operator-light source is unavailable.");
            }
            string directionalFailure =
                "the generated CharInfo_Env parameter payload is unavailable";
            Vector3 sourceDirectionalForward = Vector3.zero;
            Quaternion sourceDirectionalRotation = Quaternion.identity;
            if (!EndfieldOriginalRenderParameterImporter.TryReadEnvironmentLight(
                    out Vector2 directPitchYaw,
                    out _,
                    out _,
                    out _,
                    out _,
                    out string environmentProvenance) ||
                !EndfieldRecoveredEnvironmentPhaseConsumer
                    .TryBuildSourceDirectionalRotation(
                        directPitchYaw,
                        out sourceDirectionalRotation,
                        out sourceDirectionalForward,
                        out directionalFailure))
            {
                throw new InvalidOperationException(
                    "The source-derived CharInfo_Env direct-light transform is " +
                    "unavailable: " + directionalFailure);
            }
            sourceProvenance += "; " + environmentProvenance;
            AssertFloatBits(
                sourceDirectionalRotation.x,
                0xBB9C7A9Eu,
                "source_directional_rotation_x",
                failures);
            AssertFloatBits(
                sourceDirectionalRotation.y,
                0xBF7089B2u,
                "source_directional_rotation_y",
                failures);
            AssertFloatBits(
                sourceDirectionalRotation.z,
                0x3EAF18E5u,
                "source_directional_rotation_z",
                failures);
            AssertFloatBits(
                sourceDirectionalRotation.w,
                0xBC56F613u,
                "source_directional_rotation_w",
                failures);

            var prepared = new EndfieldHGPreparedOperatorLight[sourceLights.Length];
            for (int packedIndex = 0; packedIndex < ExpectedSourceOrder.Length; packedIndex++)
            {
                int sourceIndex = ExpectedSourceOrder[packedIndex];
                EndfieldHGOperatorLightData light = sourceLights[sourceIndex];
                if (!TryNormalizeQuaternion(
                        light.rotation,
                        out Quaternion sourceRotation))
                {
                    throw new InvalidOperationException(
                        "The exact source rotation is invalid for Endminf row " +
                        sourceIndex + ".");
                }
                prepared[packedIndex] = new EndfieldHGPreparedOperatorLight
                {
                    sourceIndex = sourceIndex,
                    packedIndex = packedIndex,
                    light = light,
                    // Static source transforms are sufficient for the CPU/GPU
                    // transport fixture. Dynamic lanes are excluded from the
                    // independent capture-invariant digest.
                    worldPosition = light.position,
                    // Native VisibleLight.GetForward consumes transform matrix
                    // column 2. Rebuild it from rotation_xyzw, just as the live
                    // rig does, rather than using the JSON's derived forward
                    // echo as an independent runtime input.
                    worldForward =
                        EndfieldRecoveredNativeLightMath.RotationMatrixColumn2(
                            sourceRotation),
                    worldRotation = sourceRotation
                };
            }
            AssertPreparedRotation(
                prepared,
                6,
                new[] { 0x3ED0CEEFu, 0x3EABD767u, 0x3E283F0Au, 0x3F554533u },
                failures);
            AssertPreparedForward(
                prepared,
                6,
                new[] { 0x3F31777Au, 0xBF11B8B3u, 0x3EE2559Cu },
                failures);
            AssertPreparedRotation(
                prepared,
                8,
                new[] { 0xBDCA7005u, 0xBF2B9944u, 0xBDDBBDB6u, 0x3F3A4426u },
                failures);
            AssertPreparedForward(
                prepared,
                8,
                new[] { 0xBF7447F4u, 0x3E934B47u, 0x3DA798F8u },
                failures);
            AssertPreparedRotation(
                prepared,
                10,
                new[] { 0x3DD873E3u, 0x3F2C2999u, 0xBE36EEA6u, 0x3F35DBC6u },
                failures);
            AssertPreparedForward(
                prepared,
                10,
                new[] { 0x3F6AEFA9u, 0xBEC7E7F2u, 0x3D95C048u },
                failures);
            var assignments = new EndfieldHGPreparedShadowAssignment[2];
            if (!EndfieldRecoveredPunctualShadowProducer.TryBuildShadowAssignmentPlan(
                    prepared,
                    prepared.Length,
                    assignments,
                    out int assignmentCount,
                    out string assignmentFailure) ||
                assignmentCount != 2)
            {
                throw new InvalidOperationException(
                    "The production shadow assignment planner rejected the " +
                    "known-good prepared order: " + assignmentFailure);
            }
            bool assignmentPlanFollowsPackedOrder =
                assignments[0].sourceIndex == 3 &&
                assignments[0].packedIndex == 5 &&
                assignments[0].shadowBaseIndex == 40 &&
                assignments[0].faceCount == 1 &&
                assignments[1].sourceIndex == 11 &&
                assignments[1].packedIndex == 10 &&
                assignments[1].shadowBaseIndex == 41 &&
                assignments[1].faceCount == 1;
            if (!assignmentPlanFollowsPackedOrder)
                failures.Add("shadow_assignment_plan:packed_order_mismatch");
            var fixture = new Vector4[
                EndfieldRecoveredEndminfFullLightDataContract.VectorCount];
            if (!TryBuild(
                    sourceDirectionalForward,
                    prepared,
                    assignments,
                    assignmentCount,
                    fixture,
                    out string failure))
            {
                throw new InvalidOperationException(
                    "Known-good full Endminf LightData fixture was rejected: " + failure);
            }

            uint[] expectedWords = BuildWords(fixture);
            string invariantHash = InvariantSha256(expectedWords);
            bool invariantMatches = string.Equals(
                invariantHash,
                ExpectedInvariantSha256,
                StringComparison.Ordinal);
            if (!invariantMatches)
                failures.Add("capture_invariant_sha256:" + invariantHash);
            bool inactiveRowsZero = InactiveRowsAreZero(expectedWords);
            if (!inactiveRowsZero)
                failures.Add("generated_inactive_rows:nonzero");
            if (expectedWords[3 * 4 + 3] != 0x3FCFEBE8u)
                failures.Add("header_h3_w:expected_3FCFEBE8");
            AssertWord(expectedWords, 0, 0x3CAF388Fu, "header_h0_x", failures);
            AssertWord(expectedWords, 1, 0xBF248DBBu, "header_h0_y", failures);
            AssertWord(expectedWords, 2, 0xBF4407EEu, "header_h0_z", failures);
            AssertPackedR2Word(expectedWords, 3, 0, 0xBD3F80E8u, failures);
            AssertPackedR2Word(expectedWords, 3, 1, 0x3F680FE3u, failures);
            AssertPackedR2Word(expectedWords, 4, 0, 0x3E90E56Bu, failures);
            AssertPackedR2Word(expectedWords, 4, 1, 0x3EDE352Au, failures);
            AssertPackedR2Word(expectedWords, 5, 0, 0xBD9F1454u, failures);
            AssertPackedR2Word(expectedWords, 5, 1, 0x3F583AEBu, failures);
            AssertPackedR2Word(expectedWords, 5, 2, 0x3F3C6FD9u, failures);
            AssertPackedR2Word(expectedWords, 5, 3, 0x41C547FFu, failures);
            AssertPackedR2Word(expectedWords, 6, 0, 0x3E04C90Bu, failures);
            AssertPackedR2Word(expectedWords, 6, 1, 0x3D94FE68u, failures);
            AssertPackedR2Word(expectedWords, 7, 0, 0x3F000000u, failures);
            AssertPackedR2Word(expectedWords, 7, 1, 0x00000000u, failures);
            AssertPackedR2Word(expectedWords, 8, 0, 0x3F781640u, failures);
            AssertPackedR2Word(expectedWords, 8, 1, 0xBF00E720u, failures);
            AssertPackedR2Word(expectedWords, 9, 0, 0x3ECD744Cu, failures);
            AssertPackedR2Word(expectedWords, 9, 1, 0x3E4A2ED0u, failures);
            AssertPackedR2Word(expectedWords, 9, 2, 0x3F5F0B83u, failures);
            AssertPackedR2Word(expectedWords, 9, 3, 0x41888C17u, failures);
            AssertPackedR2Word(expectedWords, 10, 0, 0x3CD8D450u, failures);
            AssertPackedR2Word(expectedWords, 10, 1, 0x3EC3723Eu, failures);
            AssertPackedR2Word(expectedWords, 10, 2, 0x3DE86FECu, failures);
            AssertPackedR2Word(expectedWords, 10, 3, 0x3FCA69DAu, failures);
            AssertPackedR2Word(expectedWords, 11, 0, 0x3F000000u, failures);
            AssertPackedR2Word(expectedWords, 11, 1, 0x00000000u, failures);
            AssertPackedR2Word(expectedWords, 11, 2, 0x3F5D0988u, failures);
            AssertPackedR2Word(expectedWords, 11, 3, 0x4103B8C3u, failures);
            AssertShadowWord(expectedWords, 5, 0x42200000u, failures);
            AssertShadowWord(expectedWords, 10, 0x42240000u, failures);

            EndfieldHGPreparedShadowAssignment[] overlapping =
                (EndfieldHGPreparedShadowAssignment[])assignments.Clone();
            overlapping[1].shadowBaseIndex = 40;
            bool overlapRejected = !TryBuild(
                sourceDirectionalForward,
                prepared,
                overlapping,
                overlapping.Length,
                new Vector4[fixture.Length],
                out _);
            if (!overlapRejected)
                failures.Add("fail_closed:overlapping_shadow_slots");
            bool missingAssignmentRejected = !TryBuild(
                sourceDirectionalForward,
                prepared,
                assignments,
                1,
                new Vector4[fixture.Length],
                out _);
            if (!missingAssignmentRejected)
                failures.Add("fail_closed:missing_shadow_assignment");
            bool sourceDirectColorRejected = !TryBuild(
                sourceDirectionalForward,
                prepared,
                assignments,
                assignmentCount,
                new Color(1.0f, 1.0f, 1.0f, 0.999f),
                new Vector4[fixture.Length],
                out _);
            if (!sourceDirectColorRejected)
                failures.Add("fail_closed:source_direct_color_drift");

            bool namedExact = false;
            bool bridgeExact = false;
            ComputeBuffer constants = null;
            ComputeBuffer readback = null;
            CommandBuffer command = null;
            try
            {
                ComputeShader compute = Resources.Load<ComputeShader>(ComputeResourceName);
                if (!SystemInfo.supportsComputeShaders || compute == null)
                {
                    failures.Add("gpu_probe:compute_unavailable");
                }
                else
                {
                    constants = new ComputeBuffer(
                        fixture.Length,
                        sizeof(float) * 4,
                        ComputeBufferType.Constant);
                    constants.SetData(fixture);
                    readback = new ComputeBuffer(
                        expectedWords.Length + 1,
                        sizeof(uint),
                        ComputeBufferType.Structured);
                    uint[] named = new uint[expectedWords.Length + 1];
                    uint[] bridge = new uint[expectedWords.Length + 1];
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
                    namedExact = PayloadEqual(expectedWords, named);
                    bridgeExact = PayloadEqual(expectedWords, bridge);
                    if (!namedExact)
                        failures.Add("named_gpu_readback:mismatch");
                    if (!bridgeExact)
                        failures.Add("bridge_gpu_readback:mismatch");
                }
            }
            finally
            {
                command?.Release();
                readback?.Release();
                constants?.Release();
                Shader.SetGlobalFloat(ReadyId, 0.0f);
            }

            string projectRoot = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
            string outputRoot = Path.Combine(
                projectRoot,
                "scratch",
                "character_recovery",
                "endminf_full_light_data");
            Directory.CreateDirectory(outputRoot);
            string activePrefixPath = Path.Combine(
                outputRoot,
                "generated_active_prefix_" +
                SystemInfo.graphicsDeviceType +
                ".bin");
            var activePrefix = new byte[ActiveBytes];
            Buffer.BlockCopy(
                expectedWords,
                0,
                activePrefix,
                0,
                ActiveBytes);
            File.WriteAllBytes(activePrefixPath, activePrefix);
            var report = new ValidationReport
            {
                schema = "endfield.endminf-full-light-data-unity-validation.v1",
                valid = failures.Count == 0,
                graphicsApi = SystemInfo.graphicsDeviceType.ToString(),
                sourceProvenance = sourceProvenance,
                bufferBytes = EndfieldRecoveredEndminfFullLightDataContract.SizeBytes,
                activeBytes = ActiveBytes,
                packedSourceOrder = ExpectedSourceOrder,
                invariantSha256 = invariantHash,
                invariantMatchesCapture = invariantMatches,
                inactiveRowsZero = inactiveRowsZero,
                namedGpuExact = namedExact,
                bridgeGpuExact = bridgeExact,
                gpuTransportOnly = true,
                overlapRejected = overlapRejected,
                missingAssignmentRejected = missingAssignmentRejected,
                sourceDirectColorRejected = sourceDirectColorRejected,
                assignmentPlanFollowsPackedOrder = assignmentPlanFollowsPackedOrder,
                generatedActivePrefixPath = activePrefixPath,
                failures = failures.ToArray()
            };
            string reportPath = Path.Combine(
                outputRoot,
                "gpu_validation_" + SystemInfo.graphicsDeviceType + ".json");
            File.WriteAllText(
                reportPath,
                JsonUtility.ToJson(report, true) + Environment.NewLine);
            if (!report.valid)
            {
                throw new InvalidOperationException(
                    "Full Endminf LightData validation failed: " +
                    string.Join("; ", report.failures) + ". Report=" + reportPath);
            }
            Debug.Log(
                "Full Endminf retail _LightDataBuffer contract/GPU transport " +
                "validation passed: " +
                "capture-invariant lanes exact, inactive generated rows zero, " +
                "named/CB4 GPU paths exact, production assignment plan follows " +
                "the prepared packed order. Report=" +
                reportPath);
        }

        private static bool TryBuild(
            Vector3 sourceDirectionalForward,
            EndfieldHGPreparedOperatorLight[] prepared,
            EndfieldHGPreparedShadowAssignment[] assignments,
            int assignmentCount,
            Vector4[] destination,
            out string failure) =>
            TryBuild(
                sourceDirectionalForward,
                prepared,
                assignments,
                assignmentCount,
                Color.white,
                destination,
                out failure);

        private static bool TryBuild(
            Vector3 sourceDirectionalForward,
            EndfieldHGPreparedOperatorLight[] prepared,
            EndfieldHGPreparedShadowAssignment[] assignments,
            int assignmentCount,
            Color sourceDirectColor,
            Vector4[] destination,
            out string failure) =>
            EndfieldRecoveredEndminfFullLightDataContract.TryBuild(
                sourceDirectionalForward,
                Color.white,
                sourceDirectColor,
                EndfieldRecoveredDeferredLightDataContract.SourceDirectIntensityDividePi,
                1.0f,
                false,
                prepared,
                prepared.Length,
                assignments,
                assignmentCount,
                destination,
                out failure);

        private static bool TryNormalizeQuaternion(
            Quaternion value,
            out Quaternion normalized) =>
            EndfieldRecoveredNativeLightMath.TryNormalizeQuaternion(
                value,
                out normalized);

        private static void AssertWord(
            uint[] words,
            int index,
            uint expected,
            string lane,
            List<string> failures)
        {
            if (words[index] != expected)
            {
                failures.Add(
                    lane + ":expected=" + expected.ToString("X8") +
                    ",actual=" + words[index].ToString("X8"));
            }
        }

        private static void AssertFloatBits(
            float value,
            uint expected,
            string lane,
            List<string> failures) =>
            AssertWord(
                new[] { FloatBits(value) },
                0,
                expected,
                lane,
                failures);

        private static void AssertPackedR2Word(
            uint[] words,
            int packedIndex,
            int lane,
            uint expected,
            List<string> failures) =>
            AssertWord(
                words,
                (6 + packedIndex * 8 + 2) * 4 + lane,
                expected,
                "packed" + packedIndex + "_r2_" + lane,
                failures);

        private static void AssertPreparedRotation(
            EndfieldHGPreparedOperatorLight[] prepared,
            int packedIndex,
            uint[] expected,
            List<string> failures)
        {
            Quaternion value = prepared[packedIndex].worldRotation;
            AssertFloatBits(value.x, expected[0], "packed" + packedIndex + "_rotation_x", failures);
            AssertFloatBits(value.y, expected[1], "packed" + packedIndex + "_rotation_y", failures);
            AssertFloatBits(value.z, expected[2], "packed" + packedIndex + "_rotation_z", failures);
            AssertFloatBits(value.w, expected[3], "packed" + packedIndex + "_rotation_w", failures);
        }

        private static void AssertPreparedForward(
            EndfieldHGPreparedOperatorLight[] prepared,
            int packedIndex,
            uint[] expected,
            List<string> failures)
        {
            Vector3 value = prepared[packedIndex].worldForward;
            AssertFloatBits(value.x, expected[0], "packed" + packedIndex + "_forward_x", failures);
            AssertFloatBits(value.y, expected[1], "packed" + packedIndex + "_forward_y", failures);
            AssertFloatBits(value.z, expected[2], "packed" + packedIndex + "_forward_z", failures);
        }

        private static void AssertShadowWord(
            uint[] words,
            int packedIndex,
            uint expected,
            List<string> failures)
        {
            int word = (6 + packedIndex * 8 + 3) * 4;
            if (words[word] != expected)
            {
                failures.Add(
                    "shadow_slot:packed=" + packedIndex +
                    ",expected=" + expected.ToString("X8") +
                    ",actual=" + words[word].ToString("X8"));
            }
        }

        private static uint[] BuildWords(Vector4[] vectors)
        {
            var result = new uint[vectors.Length * 4];
            for (int index = 0; index < vectors.Length; index++)
            {
                Vector4 value = vectors[index];
                int word = index * 4;
                result[word + 0] = FloatBits(value.x);
                result[word + 1] = FloatBits(value.y);
                result[word + 2] = FloatBits(value.z);
                result[word + 3] = FloatBits(value.w);
            }
            return result;
        }

        private static string InvariantSha256(uint[] words)
        {
            var selected = new List<uint>(366);
            for (int index = 0; index < 24; index++)
                selected.Add(words[index]);
            for (int packed = 0; packed < 12; packed++)
            {
                int row = (6 + packed * 8) * 4;
                for (int word = 0; word < 4; word++) selected.Add(words[row + word]);
                selected.Add(words[row + 7]);
                // Packed rows 0..2 are the only follower-mode-1 lights whose
                // forward vectors depend on the live pose. The remaining rows
                // have source-stable forwards, so retain their exact oct lanes.
                if (packed >= 3)
                {
                    selected.Add(words[row + 8]);
                    selected.Add(words[row + 9]);
                }
                selected.Add(words[row + 10]);
                selected.Add(words[row + 11]);
                for (int word = 12; word < 32; word++) selected.Add(words[row + word]);
            }
            var bytes = new byte[selected.Count * 4];
            for (int index = 0; index < selected.Count; index++)
            {
                byte[] encoded = BitConverter.GetBytes(selected[index]);
                Buffer.BlockCopy(encoded, 0, bytes, index * 4, 4);
            }
            using (SHA256 sha = SHA256.Create())
            {
                byte[] digest = sha.ComputeHash(bytes);
                return BitConverter.ToString(digest).Replace("-", string.Empty).ToLowerInvariant();
            }
        }

        private static bool InactiveRowsAreZero(uint[] words)
        {
            int firstInactiveWord = (6 + 12 * 8) * 4;
            for (int index = firstInactiveWord; index < words.Length; index++)
            {
                if (words[index] != 0u)
                    return false;
            }
            return true;
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
            command = new CommandBuffer { name = "Verify full Endminf LightData " + kernelName };
            int kernel = compute.FindKernel(kernelName);
            command.SetGlobalConstantBuffer(
                constants,
                ConstantsId,
                0,
                EndfieldRecoveredEndminfFullLightDataContract.SizeBytes);
            command.SetGlobalConstantBuffer(
                constants,
                BridgeConstantsId,
                0,
                EndfieldRecoveredEndminfFullLightDataContract.SizeBytes);
            command.SetGlobalFloat(ReadyId, 1.0f);
            command.SetComputeBufferParam(compute, kernel, ReadbackId, readback);
            command.DispatchCompute(compute, kernel, 1, 1, 1);
            Graphics.ExecuteCommandBuffer(command);
            readback.GetData(destination);
        }

        private static bool PayloadEqual(uint[] expected, uint[] actual)
        {
            if (actual.Length != expected.Length + 1 || actual[0] != 0x3F800000u)
                return false;
            for (int index = 0; index < expected.Length; index++)
            {
                if (actual[index + 1] != expected[index])
                    return false;
            }
            return true;
        }

        private static uint FloatBits(float value) =>
            unchecked((uint)BitConverter.SingleToInt32Bits(value));
    }
}
