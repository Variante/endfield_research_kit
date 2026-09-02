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
    /// Verifies the source-closed selected b35 rows through both the canonical
    /// ShaderVariablesGlobal name and the original D3D11 EndfieldCB1 bridge.
    /// </summary>
    public static class EndfieldRecoveredShaderVariablesGlobalBatchVerifier
    {
        private const string ComputeResourceName =
            "EndfieldRecoveredShaderVariablesGlobalProbe";
        private const string KernelName = "Readback";
        private const string SourceAuditRelativePath =
            "scratch/character_recovery/deferred_shader_variables_global/audit.json";
        private const string ExpectedSourceAuditSha256 =
            "5c81871116bc6618c51be65437bb826a1b7a0b6c9e5c2715b57279469e770e76";

        private static readonly int ReadbackId = Shader.PropertyToID(
            "_EndfieldRecoveredShaderVariablesGlobalReadback");

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
        private sealed class M27PartialSourceReport
        {
            public bool valid;
            public bool buildAccepted;
            public bool exposureC27Populated;
            public bool vfxParams0C103Populated;
            public bool unresolvedTaaC19Zero;
            public bool unresolvedMipBiasC26Zero;
            public bool unresolvedAnchorC105Zero;
            public bool c26InlineSourceAccepted;
            public bool c26InlineValueMatches;
            public bool c26MalformedSourceRejected;
            public bool c26Pow2MismatchRejected;
            public bool c26OverlayPopulated;
            public bool c26OverlayPreservedPartialSources;
            public bool c26ResourceStateValid;
            public bool c26ResourceReady;
            public string c26ResourceDiagnostic;
            public bool m27AdmissionRejected;
            public string admissionDiagnostic;
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
            public int selectedVectorCount;
            public int[] selectedUsedVectors;
            public bool publicationReturnedReady;
            public bool readyObserved;
            public bool canonicalWordsMatch;
            public bool d3d11BridgeWordsMatch;
            public bool selectedConsumerWordsMatch;
            public bool unresolvedRegistersZero;
            public string[] selectedDefaultSHWords;
            public string[] expectedWords;
            public string[] actualCanonicalWords;
            public string[] actualD3D11BridgeWords;
            public M27PartialSourceReport partialOwnedSources;
            public RejectionReport[] failClosedGates;
            public string[] failures;
        }

        [MenuItem(
            "Endfield/Character Recovery Lab/" +
            "Verify Recovered ShaderVariablesGlobal")]
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
                "shader_variables_global");
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
            if (!EndfieldRecoveredShaderVariablesGlobal.IsRequested)
            {
                failures.Add(
                    "selector: " +
                    EndfieldRecoveredShaderVariablesGlobal.Selector +
                    " must be explicitly enabled");
            }

            GameObject cameraObject = null;
            ComputeBuffer readbackBuffer = null;
            CommandBuffer command = null;
            var owner = new EndfieldRecoveredShaderVariablesGlobal();
            const int CanonicalWordCount =
                EndfieldRecoveredShaderVariablesGlobalContract.VectorCount * 4;
            const int BridgeWordCount =
                EndfieldRecoveredShaderVariablesGlobalContract
                    .D3D11SelectedVectorCount * 4;
            var readback = new uint[1 + CanonicalWordCount + BridgeWordCount];
            var fixture = new Vector4[
                EndfieldRecoveredShaderVariablesGlobalContract.VectorCount];
            bool publicationReady = false;
            try
            {
                cameraObject = new GameObject(
                    "Recovered ShaderVariablesGlobal Validation Camera");
                cameraObject.hideFlags = HideFlags.HideAndDontSave;
                Camera camera = cameraObject.AddComponent<Camera>();
                camera.orthographic = false;
                camera.nearClipPlane = 0.1f;
                camera.farClipPlane = 50.0f;
                camera.aspect = 640.0f / 720.0f;

                if (!EndfieldRecoveredShaderVariablesGlobalContract.TryBuild(
                        camera,
                        640,
                        720,
                        EndfieldRecoveredShaderVariablesGlobalContract
                            .SelectedEnvironmentParams,
                        true,
                        fixture,
                        out string fixtureFailure))
                {
                    throw new InvalidOperationException(
                        "Known-good ShaderVariablesGlobal fixture was rejected: " +
                        fixtureFailure);
                }
                uint[] expected =
                    EndfieldRecoveredShaderVariablesGlobalContract
                        .BuildExpectedWords(fixture);

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
                    int kernel = compute.FindKernel(KernelName);
                    readbackBuffer = new ComputeBuffer(
                        readback.Length,
                        sizeof(uint),
                        ComputeBufferType.Structured)
                    {
                        name = "Recovered ShaderVariablesGlobal Readback"
                    };
                    readbackBuffer.SetData(new uint[readback.Length]);
                    command = new CommandBuffer
                    {
                        name = "Verify Recovered ShaderVariablesGlobal"
                    };
                    publicationReady = owner.PrepareAndPublish(
                        camera,
                        640,
                        720,
                        EndfieldRecoveredShaderVariablesGlobalContract
                            .SelectedEnvironmentParams,
                        true,
                        command,
                        out string publicationFailure);
                    if (!publicationReady)
                        failures.Add("publication: " + publicationFailure);
                    command.SetComputeBufferParam(
                        compute,
                        kernel,
                        ReadbackId,
                        readbackBuffer);
                    command.DispatchCompute(compute, kernel, 1, 1, 1);
                    Graphics.ExecuteCommandBuffer(command);
                    readbackBuffer.GetData(readback);
                }

                bool readyObserved = readback[0] == 0x3F800000u;
                var actualCanonical = new uint[CanonicalWordCount];
                var actualBridge = new uint[BridgeWordCount];
                Array.Copy(
                    readback,
                    1,
                    actualCanonical,
                    0,
                    actualCanonical.Length);
                Array.Copy(
                    readback,
                    1 + CanonicalWordCount,
                    actualBridge,
                    0,
                    actualBridge.Length);
                bool canonicalMatches = WordsEqual(expected, actualCanonical);
                bool bridgeMatches = PrefixWordsEqual(
                    expected,
                    actualBridge,
                    BridgeWordCount);
                bool selectedMatches = SelectedWordsEqual(
                    expected,
                    actualCanonical);
                bool unresolvedZero = UnresolvedVectorsAreZero(
                    actualCanonical);
                M27PartialSourceReport partialOwnedSources =
                    VerifyPartialM27OwnedSources(camera);

                if (!readyObserved)
                    failures.Add("ready_flag: expected 0x3F800000");
                if (!canonicalMatches)
                {
                    failures.Add(
                        "canonical_readback: one or more 3200-byte words differ");
                }
                if (!bridgeMatches)
                {
                    failures.Add(
                        "d3d11_bridge_readback: one or more 2512-byte words differ");
                }
                if (!selectedMatches)
                {
                    failures.Add(
                        "selected_consumer: one or more b35 used words differ");
                }
                if (!unresolvedZero)
                {
                    failures.Add(
                        "unresolved_registers: unknown b35 rows are nonzero");
                }
                if (!partialOwnedSources.valid)
                {
                    failures.Add(
                        "partial_m27_owned_sources: c26/c27/c103 propagation or " +
                        "fail-closed admission validation failed");
                }

                RejectionReport[] rejections =
                {
                    VerifyPrerequisiteRejection(camera),
                    VerifyDimensionRejection(camera),
                    VerifyOrthographicRejection(camera),
                    VerifyNearClipRejection(camera),
                    VerifyEnvironmentRejection(camera),
                    VerifyDestinationRejection(camera),
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

                int shWord =
                    EndfieldRecoveredShaderVariablesGlobalContract
                        .DefaultSHRedVector * 4;
                var shWords = new uint[4];
                Array.Copy(expected, shWord, shWords, 0, 4);
                string api = ApiName(SystemInfo.graphicsDeviceType);
                var report = new ValidationReport
                {
                    schema =
                        "endfield-recovered-shader-variables-global-" +
                        "validation-v2",
                    valid = failures.Count == 0,
                    graphicsApi = api,
                    defaultOff = true,
                    pass0ConsumerEnabled = false,
                    sourceAuditPath = sourceAuditPath,
                    sourceAuditSha256 = sourceHash,
                    expectedSourceAuditSha256 = ExpectedSourceAuditSha256,
                    sourceAuditHashMatches = sourceHashMatches,
                    bufferBytes =
                        EndfieldRecoveredShaderVariablesGlobalContract.SizeBytes,
                    vectorCount =
                        EndfieldRecoveredShaderVariablesGlobalContract.VectorCount,
                    d3d11SelectedBytes =
                        EndfieldRecoveredShaderVariablesGlobalContract
                            .D3D11SelectedSizeBytes,
                    selectedVectorCount =
                        EndfieldRecoveredShaderVariablesGlobalContract
                            .SelectedUsedVectors.Length,
                    selectedUsedVectors =
                        EndfieldRecoveredShaderVariablesGlobalContract
                            .SelectedUsedVectors,
                    publicationReturnedReady = publicationReady,
                    readyObserved = readyObserved,
                    canonicalWordsMatch = canonicalMatches,
                    d3d11BridgeWordsMatch = bridgeMatches,
                    selectedConsumerWordsMatch = selectedMatches,
                    unresolvedRegistersZero = unresolvedZero,
                    selectedDefaultSHWords = HexWords(shWords),
                    expectedWords = HexWords(expected),
                    actualCanonicalWords = HexWords(actualCanonical),
                    actualD3D11BridgeWords = HexWords(actualBridge),
                    partialOwnedSources = partialOwnedSources,
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
                        "ShaderVariablesGlobal validation failed: " +
                        string.Join("; ", report.failures) +
                        ". Report=" + reportPath);
                }
                Debug.Log(
                    "Recovered ShaderVariablesGlobal validation passed: " +
                    "canonical 800/800 and EndfieldCB1 628/628 words exact, " +
                    "selected rows=32/32, unresolved rows zero, " +
                    "fail-closed gates=6/6, api=" + api +
                    ", report=" + reportPath +
                    ". Pass 0 remains disabled.");
            }
            finally
            {
                command?.Release();
                readbackBuffer?.Release();
                owner.Dispose();
                if (cameraObject != null)
                    UnityEngine.Object.DestroyImmediate(cameraObject);
            }
        }

        private static RejectionReport VerifyPrerequisiteRejection(
            Camera camera)
        {
            bool accepted = TryBuild(
                camera,
                640,
                720,
                EndfieldRecoveredShaderVariablesGlobalContract
                    .SelectedEnvironmentParams,
                false,
                new Vector4[200],
                out string diagnostic);
            return Rejection("prerequisites", "prerequisites are required", accepted, diagnostic);
        }

        private static M27PartialSourceReport VerifyPartialM27OwnedSources(
            Camera camera)
        {
            const float Exposure = 2.0f;
            Vector3 playerPosition = new Vector3(1.25f, -2.5f, 3.75f);
            const float ClockSeconds = 1025.5f;
            EndfieldRecoveredShaderVariablesGlobalContract.M27SourceInputs
                inputs = EndfieldRecoveredShaderVariablesGlobalContract
                    .M27SourceInputs
                    .CurrentTargetPerspectiveExposureAndVFXPlayer(
                        Exposure,
                        true,
                        playerPosition,
                        ClockSeconds,
                        true);
            var values = new Vector4[
                EndfieldRecoveredShaderVariablesGlobalContract.VectorCount];
            bool buildAccepted =
                EndfieldRecoveredShaderVariablesGlobalContract.TryBuild(
                    camera,
                    640,
                    720,
                    EndfieldRecoveredShaderVariablesGlobalContract
                        .SelectedEnvironmentParams,
                    true,
                    inputs,
                    values,
                    out _);
            bool m27Admitted =
                EndfieldRecoveredShaderVariablesGlobalContract
                    .TryValidateM27SourceReadiness(
                        inputs,
                        out string admissionDiagnostic);

            bool exposurePopulated = buildAccepted && VectorBitsEqual(
                values[EndfieldRecoveredShaderVariablesGlobalContract
                    .ExposureWithMiscParamsVector],
                new Vector4(Exposure, 1.0f / Exposure, 640.0f / 720.0f, 0.0f));
            bool vfxParams0Populated = buildAccepted && VectorBitsEqual(
                values[EndfieldRecoveredShaderVariablesGlobalContract
                    .VFXParams0Vector],
                new Vector4(
                    playerPosition.x,
                    playerPosition.y,
                    playerPosition.z,
                    ClockSeconds % 1024.0f));
            bool taaZero = buildAccepted && VectorBitsEqual(
                values[EndfieldRecoveredShaderVariablesGlobalContract
                    .TaaJitterStrengthVector],
                Vector4.zero);
            bool mipBiasZero = buildAccepted && VectorBitsEqual(
                values[EndfieldRecoveredShaderVariablesGlobalContract
                    .GlobalMipBiasVector],
                Vector4.zero);
            bool anchorZero = buildAccepted && VectorBitsEqual(
                values[EndfieldRecoveredShaderVariablesGlobalContract
                    .VFXParams2Vector],
                Vector4.zero);
            bool admissionRejected =
                !m27Admitted &&
                admissionDiagnostic != null &&
                admissionDiagnostic.IndexOf(
                    "c19.zw",
                    StringComparison.Ordinal) >= 0;
            string exactPayload = BuildInlineM27C26Payload("3f800000");
            bool c26InlineAccepted =
                EndfieldRecoveredM27GlobalMipBiasSource.TryValidatePayloadJson(
                    exactPayload,
                    out float c26InlineValue,
                    out _);
            bool c26InlineValueMatches = c26InlineAccepted &&
                unchecked((uint)BitConverter.SingleToInt32Bits(c26InlineValue)) ==
                    0x00000000u;
            bool c26MalformedRejected =
                !EndfieldRecoveredM27GlobalMipBiasSource.TryValidatePayloadJson(
                    "{\"schema\":\"bad\"}",
                    out _,
                    out _);
            bool c26Pow2MismatchRejected =
                !EndfieldRecoveredM27GlobalMipBiasSource.TryValidatePayloadJson(
                    BuildInlineM27C26Payload("3f000000"),
                    out _,
                    out _);
            EndfieldRecoveredShaderVariablesGlobalContract.M27SourceInputs
                overlayInputs = inputs.WithPhysicalCameraGlobalMipBias(
                    c26InlineValue,
                    c26InlineAccepted);
            var overlayValues = new Vector4[
                EndfieldRecoveredShaderVariablesGlobalContract.VectorCount];
            bool overlayBuildAccepted =
                EndfieldRecoveredShaderVariablesGlobalContract.TryBuild(
                    camera,
                    640,
                    720,
                    EndfieldRecoveredShaderVariablesGlobalContract
                        .SelectedEnvironmentParams,
                    true,
                    overlayInputs,
                    overlayValues,
                    out _);
            bool c26OverlayPopulated = overlayBuildAccepted && VectorBitsEqual(
                overlayValues[EndfieldRecoveredShaderVariablesGlobalContract
                    .GlobalMipBiasVector],
                new Vector4(0.0f, 1.0f, 0.0f, 0.0f));
            bool c26OverlayPreservedPartialSources = overlayBuildAccepted &&
                VectorBitsEqual(
                    overlayValues[EndfieldRecoveredShaderVariablesGlobalContract
                        .ExposureWithMiscParamsVector],
                    values[EndfieldRecoveredShaderVariablesGlobalContract
                        .ExposureWithMiscParamsVector]) &&
                VectorBitsEqual(
                    overlayValues[EndfieldRecoveredShaderVariablesGlobalContract
                        .VFXParams0Vector],
                    values[EndfieldRecoveredShaderVariablesGlobalContract
                        .VFXParams0Vector]) &&
                VectorBitsEqual(
                    overlayValues[EndfieldRecoveredShaderVariablesGlobalContract
                        .TaaJitterStrengthVector],
                    Vector4.zero) &&
                VectorBitsEqual(
                    overlayValues[EndfieldRecoveredShaderVariablesGlobalContract
                        .VFXParams2Vector],
                    Vector4.zero);
            var resourceOwner = new EndfieldRecoveredM27GlobalMipBiasSource();
            bool c26ResourceReady = resourceOwner.TryGetGlobalMipBias(
                out float c26ResourceValue,
                out string c26ResourceDiagnostic);
            bool c26ResourceExists = Resources.Load<TextAsset>(
                EndfieldRecoveredM27GlobalMipBiasSource.ResourceName) != null;
            bool c26ResourceStateValid = c26ResourceExists
                ? c26ResourceReady &&
                    unchecked((uint)BitConverter.SingleToInt32Bits(
                        c26ResourceValue)) == 0x00000000u
                : !c26ResourceReady;
            return new M27PartialSourceReport
            {
                valid = buildAccepted &&
                    exposurePopulated &&
                    vfxParams0Populated &&
                    taaZero &&
                    mipBiasZero &&
                    anchorZero &&
                    c26InlineAccepted &&
                    c26InlineValueMatches &&
                    c26MalformedRejected &&
                    c26Pow2MismatchRejected &&
                    c26OverlayPopulated &&
                    c26OverlayPreservedPartialSources &&
                    c26ResourceStateValid &&
                    admissionRejected,
                buildAccepted = buildAccepted,
                exposureC27Populated = exposurePopulated,
                vfxParams0C103Populated = vfxParams0Populated,
                unresolvedTaaC19Zero = taaZero,
                unresolvedMipBiasC26Zero = mipBiasZero,
                unresolvedAnchorC105Zero = anchorZero,
                c26InlineSourceAccepted = c26InlineAccepted,
                c26InlineValueMatches = c26InlineValueMatches,
                c26MalformedSourceRejected = c26MalformedRejected,
                c26Pow2MismatchRejected = c26Pow2MismatchRejected,
                c26OverlayPopulated = c26OverlayPopulated,
                c26OverlayPreservedPartialSources =
                    c26OverlayPreservedPartialSources,
                c26ResourceStateValid = c26ResourceStateValid,
                c26ResourceReady = c26ResourceReady,
                c26ResourceDiagnostic = c26ResourceDiagnostic,
                m27AdmissionRejected = admissionRejected,
                admissionDiagnostic = admissionDiagnostic,
            };
        }

        private static string BuildInlineM27C26Payload(
            string publishedC26YBits)
        {
            return "{" +
                "\"schema\":\"" +
                EndfieldRecoveredM27GlobalMipBiasSource.PayloadSchema + "\"," +
                "\"status\":\"" +
                EndfieldRecoveredM27GlobalMipBiasSource.PayloadStatus + "\"," +
                "\"sourceSession\":\"" +
                EndfieldRecoveredM27GlobalMipBiasSource.SourceSession + "\"," +
                "\"sourceReportSha256\":\"" +
                EndfieldRecoveredM27GlobalMipBiasSource.SourceReportSha256 + "\"," +
                "\"receiptSha256\":\"" +
                EndfieldRecoveredM27GlobalMipBiasSource.ReceiptSha256 + "\"," +
                "\"runtimePackageSha256\":\"" +
                EndfieldRecoveredM27GlobalMipBiasSource.RuntimePackageSha256 + "\"," +
                "\"staticContractSha256\":\"" +
                EndfieldRecoveredM27GlobalMipBiasSource.StaticContractSha256 +
                "\",\"rendererPathId\":\"" +
                EndfieldRecoveredM27GlobalMipBiasSource.RendererPathId + "\"," +
                "\"materialMipBiasBits\":\"00000000\"," +
                "\"dynamicTermBits\":\"00000000\"," +
                "\"globalMipBiasBits\":\"00000000\"," +
                "\"publishedC26YBits\":\"" + publishedC26YBits + "\"," +
                "\"canPopulatePhysicalCameraMipBiasSource\":true," +
                "\"presentationAuthority\":false}";
        }

        private static RejectionReport VerifyDimensionRejection(Camera camera)
        {
            bool accepted = TryBuild(
                camera,
                0,
                720,
                EndfieldRecoveredShaderVariablesGlobalContract
                    .SelectedEnvironmentParams,
                true,
                new Vector4[200],
                out string diagnostic);
            return Rejection("dimensions", "dimensions must be positive", accepted, diagnostic);
        }

        private static RejectionReport VerifyOrthographicRejection(Camera camera)
        {
            camera.orthographic = true;
            bool accepted = TryBuild(
                camera,
                640,
                720,
                EndfieldRecoveredShaderVariablesGlobalContract
                    .SelectedEnvironmentParams,
                true,
                new Vector4[200],
                out string diagnostic);
            camera.orthographic = false;
            return Rejection("camera_mode", "must be perspective", accepted, diagnostic);
        }

        private static RejectionReport VerifyNearClipRejection(Camera camera)
        {
            camera.nearClipPlane = 0.2f;
            bool accepted = TryBuild(
                camera,
                640,
                720,
                EndfieldRecoveredShaderVariablesGlobalContract
                    .SelectedEnvironmentParams,
                true,
                new Vector4[200],
                out string diagnostic);
            camera.nearClipPlane = 0.1f;
            return Rejection("near_clip", "exact float32 0.1", accepted, diagnostic);
        }

        private static RejectionReport VerifyEnvironmentRejection(Camera camera)
        {
            bool accepted = TryBuild(
                camera,
                640,
                720,
                Vector4.one,
                true,
                new Vector4[200],
                out string diagnostic);
            return Rejection("environment", "serialized phase", accepted, diagnostic);
        }

        private static RejectionReport VerifyDestinationRejection(Camera camera)
        {
            bool accepted = TryBuild(
                camera,
                640,
                720,
                EndfieldRecoveredShaderVariablesGlobalContract
                    .SelectedEnvironmentParams,
                true,
                new Vector4[1],
                out string diagnostic);
            return Rejection("destination_size", "exactly 200 float4", accepted, diagnostic);
        }

        private static bool TryBuild(
            Camera camera,
            int width,
            int height,
            Vector4 environmentParams,
            bool prerequisitesReady,
            Vector4[] destination,
            out string diagnostic)
        {
            return EndfieldRecoveredShaderVariablesGlobalContract.TryBuild(
                camera,
                width,
                height,
                environmentParams,
                prerequisitesReady,
                destination,
                out diagnostic);
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

        private static bool SelectedWordsEqual(uint[] expected, uint[] actual)
        {
            foreach (int vector in
                EndfieldRecoveredShaderVariablesGlobalContract.SelectedUsedVectors)
            {
                for (int lane = 0; lane < 4; lane++)
                {
                    int word = vector * 4 + lane;
                    if (expected[word] != actual[word])
                        return false;
                }
            }
            return true;
        }

        private static bool UnresolvedVectorsAreZero(uint[] words)
        {
            var selected = new HashSet<int>(
                EndfieldRecoveredShaderVariablesGlobalContract
                    .SelectedUsedVectors);
            for (int vector = 0;
                 vector < EndfieldRecoveredShaderVariablesGlobalContract.VectorCount;
                 vector++)
            {
                if (selected.Contains(vector))
                    continue;
                for (int lane = 0; lane < 4; lane++)
                {
                    if (words[vector * 4 + lane] != 0u)
                        return false;
                }
            }
            return true;
        }

        private static bool WordsEqual(uint[] expected, uint[] actual)
        {
            return PrefixWordsEqual(expected, actual, expected.Length);
        }

        private static bool VectorBitsEqual(Vector4 left, Vector4 right)
        {
            return BitConverter.SingleToInt32Bits(left.x) ==
                    BitConverter.SingleToInt32Bits(right.x) &&
                BitConverter.SingleToInt32Bits(left.y) ==
                    BitConverter.SingleToInt32Bits(right.y) &&
                BitConverter.SingleToInt32Bits(left.z) ==
                    BitConverter.SingleToInt32Bits(right.z) &&
                BitConverter.SingleToInt32Bits(left.w) ==
                    BitConverter.SingleToInt32Bits(right.w);
        }

        private static bool PrefixWordsEqual(
            uint[] expected,
            uint[] actual,
            int count)
        {
            if (expected.Length < count || actual.Length != count)
                return false;
            for (int index = 0; index < count; index++)
            {
                if (expected[index] != actual[index])
                    return false;
            }
            return true;
        }

        private static string[] HexWords(uint[] words)
        {
            var rendered = new string[words.Length];
            for (int index = 0; index < words.Length; index++)
                rendered[index] = "0x" + words[index].ToString("x8");
            return rendered;
        }

        private static string Sha256File(string path)
        {
            using (var stream = File.OpenRead(path))
            using (var digest = SHA256.Create())
                return HexBytes(digest.ComputeHash(stream));
        }

        private static string HexBytes(byte[] bytes)
        {
            return BitConverter.ToString(bytes).Replace("-", string.Empty).ToLowerInvariant();
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
    }
}
