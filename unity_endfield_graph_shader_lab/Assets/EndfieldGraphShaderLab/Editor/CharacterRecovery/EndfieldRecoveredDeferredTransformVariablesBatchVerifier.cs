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
    /// Verifies the selected pass-0 b30 camera fields through the exact global
    /// constant-buffer name on both supported lab graphics APIs.
    /// </summary>
    public static class EndfieldRecoveredDeferredTransformVariablesBatchVerifier
    {
        private const string ComputeResourceName =
            "EndfieldRecoveredDeferredTransformVariablesProbe";
        private const string KernelName = "Readback";
        private const string SourceAuditRelativePath =
            "../reports/assets/character_recovery/" +
            "endminf_m27_b0_source_contract.json";
        private const string ExpectedSourceAuditSha256 =
            "4ba38b099d2ff3d893529cd90fabf234002b9c542868090ec3113e4b1b2c9f5f";

        private static readonly int ReadbackId = Shader.PropertyToID(
            "_EndfieldRecoveredDeferredTransformReadback");

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
            public int[] selectedUsedVectors;
            public bool publicationReturnedReady;
            public bool readyObserved;
            public bool allPublishedWordsMatch;
            public bool selectedConsumerWordsMatch;
            public bool unresolvedRegistersZero;
            public bool viewInverseRoundTrip;
            public bool worldClipRoundTrip;
            public float worldClipRoundTripMaxError;
            public bool resetHistoryMatchesCurrent;
            public bool contiguousHistoryMatchesPrevious;
            public bool discontinuityResetIgnoresStaleHistory;
            public bool ownerSourceReadyAfterPublish;
            public bool duplicateSameFrameRejected;
            public bool duplicateResetSourceReady;
            public bool temporalHistoryStatePolicyPassed;
            public string[] expectedWords;
            public string[] actualWords;
            public RejectionReport[] failClosedGates;
            public string[] failures;
        }

        [MenuItem(
            "Endfield/Character Recovery Lab/" +
            "Verify Recovered Deferred TransformVariables")]
        public static void VerifyBatch()
        {
            string projectRoot = Path.GetFullPath(
                Path.Combine(Application.dataPath, ".."));
            string sourceAuditPath = Path.GetFullPath(Path.Combine(
                projectRoot,
                SourceAuditRelativePath.Replace('/', Path.DirectorySeparatorChar)));
            string outputRoot = Path.Combine(
                projectRoot,
                "scratch",
                "character_recovery",
                "deferred_transform_variables");
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
                    (string.IsNullOrEmpty(sourceHash) ? "missing" : sourceHash));
            }
            if (!EndfieldRecoveredDeferredTransformVariables.IsRequested)
            {
                failures.Add(
                    "selector: " +
                    EndfieldRecoveredDeferredTransformVariables.Selector +
                    " must be explicitly enabled");
            }

            GameObject cameraObject = null;
            ComputeBuffer readbackBuffer = null;
            CommandBuffer command = null;
            var owner = new EndfieldRecoveredDeferredTransformVariables();
            uint[] readback = new uint[1 +
                EndfieldRecoveredDeferredTransformVariablesContract.VectorCount * 4];
            var fixture = new Vector4[
                EndfieldRecoveredDeferredTransformVariablesContract.VectorCount];
            bool publicationReady = false;
            try
            {
                cameraObject = new GameObject(
                    "Recovered Deferred TransformVariables Validation Camera");
                cameraObject.hideFlags = HideFlags.HideAndDontSave;
                Camera camera = cameraObject.AddComponent<Camera>();
                camera.transform.SetPositionAndRotation(
                    new Vector3(1.25f, 2.5f, -3.75f),
                    Quaternion.Euler(12.0f, -27.0f, 3.0f));
                camera.fieldOfView = 35.5f;
                camera.aspect = 640.0f / 720.0f;
                camera.nearClipPlane = 0.3f;
                camera.farClipPlane = 1000.0f;

                if (!EndfieldRecoveredDeferredTransformVariablesContract.TryBuild(
                        camera,
                        true,
                        fixture,
                        out string fixtureFailure))
                {
                    throw new InvalidOperationException(
                        "Known-good deferred transform fixture was rejected: " +
                        fixtureFailure);
                }
                uint[] expected =
                    EndfieldRecoveredDeferredTransformVariablesContract
                        .BuildExpectedWords(fixture);
                bool resetHistoryMatchesCurrent =
                    ResetHistoryMatchesCurrent(fixture);
                bool contiguousHistoryMatchesPrevious =
                    ContiguousHistoryMatchesPrevious(camera, fixture);
                bool discontinuityResetIgnoresStaleHistory =
                    DiscontinuityResetIgnoresStaleHistory(camera);
                bool temporalHistoryStatePolicyPassed =
                    TemporalHistoryStatePolicyPassed();

                ComputeShader compute = Resources.Load<ComputeShader>(
                    ComputeResourceName);
                if (!SystemInfo.supportsComputeShaders)
                {
                    failures.Add("gpu_capability: compute shaders are unavailable");
                }
                else if (compute == null)
                {
                    failures.Add(
                        "compute_resource: Resources/" + ComputeResourceName +
                        ".compute is unavailable");
                }
                else
                {
                    int kernel = compute.FindKernel(KernelName);
                    readbackBuffer = new ComputeBuffer(
                        readback.Length,
                        sizeof(uint),
                        ComputeBufferType.Structured)
                    {
                        name = "Recovered Deferred TransformVariables Readback"
                    };
                    readbackBuffer.SetData(new uint[readback.Length]);
                    command = new CommandBuffer
                    {
                        name = "Verify Recovered Deferred TransformVariables"
                    };
                    publicationReady = owner.PrepareAndPublish(
                        camera,
                        true,
                        640,
                        720,
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
                bool ownerSourceReadyAfterPublish =
                    publicationReady && owner.CurrentM27SourceReady;
                bool duplicateSameFrameRejected =
                    DuplicateSameFrameRejected(
                        camera,
                        out bool duplicateResetSourceReady);

                bool readyObserved = readback[0] == 0x3F800000u;
                var actual = new uint[expected.Length];
                Array.Copy(readback, 1, actual, 0, actual.Length);
                bool allWordsMatch = WordsEqual(expected, actual);
                bool selectedWordsMatch = SelectedWordsEqual(expected, actual);
                bool unresolvedZero = UnresolvedVectorsAreZero(actual);
                bool inverseRoundTrip = MatrixApproximatelyIdentity(
                    UnpackMatrix(fixture, 0) * UnpackMatrix(fixture, 4),
                    2.0e-5f);
                float worldRoundTripError = WorldClipRoundTripError(
                    camera,
                    UnpackMatrix(fixture, 24));
                bool worldRoundTrip = worldRoundTripError <= 2.0e-4f;

                if (!readyObserved)
                    failures.Add("ready_flag: expected 0x3F800000");
                if (!allWordsMatch)
                    failures.Add("gpu_readback: one or more 1312-byte words differ");
                if (!selectedWordsMatch)
                    failures.Add("selected_consumer: one or more b30 used words differ");
                if (!unresolvedZero)
                    failures.Add("unresolved_registers: unknown b30 rows are nonzero");
                if (!inverseRoundTrip)
                    failures.Add("view_inverse: View * InvView is not identity");
                if (!worldRoundTrip)
                {
                    failures.Add(
                        "world_clip_roundtrip: max error=" +
                        worldRoundTripError.ToString("R"));
                }
                if (!resetHistoryMatchesCurrent)
                {
                    failures.Add(
                        "temporal_reset: previous matrix/camera do not match " +
                        "the current source-built frame");
                }
                if (!contiguousHistoryMatchesPrevious)
                {
                    failures.Add(
                        "temporal_contiguous: previous matrix/camera do not " +
                        "match the supplied immediately preceding frame");
                }
                if (!discontinuityResetIgnoresStaleHistory)
                {
                    failures.Add(
                        "temporal_discontinuity: reset did not ignore stale " +
                        "matrix/camera inputs");
                }
                if (!ownerSourceReadyAfterPublish)
                    failures.Add("owner_source_ready: publish did not authenticate b0");
                if (!duplicateSameFrameRejected)
                {
                    failures.Add(
                        "owner_duplicate: same-camera same-frame publication " +
                        "was not rejected with an actionable diagnostic");
                }
                if (!duplicateResetSourceReady)
                {
                    failures.Add(
                        "owner_duplicate_reset: failed publication did not " +
                        "reset CurrentM27SourceReady");
                }
                if (!temporalHistoryStatePolicyPassed)
                {
                    failures.Add(
                        "owner_history_policy: contiguous/discontinuous " +
                        "history decisions drifted");
                }

                RejectionReport[] rejections =
                {
                    VerifyDestinationRejection(),
                    VerifyNonFiniteRejection(),
                    VerifySingularRejection(),
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
                        "endfield-recovered-deferred-transform-variables-" +
                        "validation-v1",
                    valid = failures.Count == 0,
                    graphicsApi = api,
                    defaultOff = true,
                    pass0ConsumerEnabled = false,
                    sourceAuditPath = sourceAuditPath,
                    sourceAuditSha256 = sourceHash,
                    expectedSourceAuditSha256 = ExpectedSourceAuditSha256,
                    sourceAuditHashMatches = sourceHashMatches,
                    bufferBytes =
                        EndfieldRecoveredDeferredTransformVariablesContract
                            .SizeBytes,
                    vectorCount =
                        EndfieldRecoveredDeferredTransformVariablesContract
                            .VectorCount,
                    d3d11SelectedBytes =
                        EndfieldRecoveredDeferredTransformVariablesContract
                            .D3D11SelectedSizeBytes,
                    selectedUsedVectors =
                        EndfieldRecoveredDeferredTransformVariablesContract
                            .SelectedUsedVectors,
                    publicationReturnedReady = publicationReady,
                    readyObserved = readyObserved,
                    allPublishedWordsMatch = allWordsMatch,
                    selectedConsumerWordsMatch = selectedWordsMatch,
                    unresolvedRegistersZero = unresolvedZero,
                    viewInverseRoundTrip = inverseRoundTrip,
                    worldClipRoundTrip = worldRoundTrip,
                    worldClipRoundTripMaxError = worldRoundTripError,
                    resetHistoryMatchesCurrent = resetHistoryMatchesCurrent,
                    contiguousHistoryMatchesPrevious =
                        contiguousHistoryMatchesPrevious,
                    discontinuityResetIgnoresStaleHistory =
                        discontinuityResetIgnoresStaleHistory,
                    ownerSourceReadyAfterPublish = ownerSourceReadyAfterPublish,
                    duplicateSameFrameRejected = duplicateSameFrameRejected,
                    duplicateResetSourceReady = duplicateResetSourceReady,
                    temporalHistoryStatePolicyPassed =
                        temporalHistoryStatePolicyPassed,
                    expectedWords = HexWords(expected),
                    actualWords = HexWords(actual),
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
                        "Deferred TransformVariables validation failed: " +
                        string.Join("; ", report.failures) +
                        ". Report=" + reportPath);
                }
                Debug.Log(
                    "Recovered deferred _TransformVariables validation passed: " +
                    "all 328 words exact, selected vectors=" +
                    EndfieldRecoveredDeferredTransformVariablesContract
                        .SelectedUsedVectors.Length + "/" +
                    EndfieldRecoveredDeferredTransformVariablesContract
                        .SelectedUsedVectors.Length + ", " +
                    "unresolved rows zero, fail-closed gates=3/3, api=" + api +
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

        private static RejectionReport VerifyDestinationRejection()
        {
            bool accepted =
                EndfieldRecoveredDeferredTransformVariablesContract.TryBuild(
                    Matrix4x4.identity,
                    Matrix4x4.identity,
                    Vector3.zero,
                    new Vector4[1],
                    out string diagnostic);
            return Rejection(
                "destination_size",
                "exactly 82 float4 vectors",
                accepted,
                diagnostic);
        }

        private static RejectionReport VerifyNonFiniteRejection()
        {
            bool accepted =
                EndfieldRecoveredDeferredTransformVariablesContract.TryBuild(
                    Matrix4x4.identity,
                    Matrix4x4.identity,
                    new Vector3(float.NaN, 0.0f, 0.0f),
                    new Vector4[82],
                    out string diagnostic);
            return Rejection(
                "nonfinite_camera",
                "camera position must contain only finite values",
                accepted,
                diagnostic);
        }

        private static RejectionReport VerifySingularRejection()
        {
            bool accepted =
                EndfieldRecoveredDeferredTransformVariablesContract.TryBuild(
                    Matrix4x4.zero,
                    Matrix4x4.identity,
                    Vector3.zero,
                    new Vector4[82],
                    out string diagnostic);
            return Rejection(
                "singular_view",
                "view matrix must be invertible",
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

        private static bool SelectedWordsEqual(uint[] expected, uint[] actual)
        {
            foreach (int vector in
                EndfieldRecoveredDeferredTransformVariablesContract
                    .SelectedUsedVectors)
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
                EndfieldRecoveredDeferredTransformVariablesContract
                    .SelectedUsedVectors);
            for (int vector = 0; vector < 82; vector++)
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
            if (expected.Length != actual.Length)
                return false;
            for (int index = 0; index < expected.Length; index++)
            {
                if (expected[index] != actual[index])
                    return false;
            }
            return true;
        }

        private static Matrix4x4 UnpackMatrix(Vector4[] vectors, int first)
        {
            var matrix = new Matrix4x4();
            for (int column = 0; column < 4; column++)
                matrix.SetColumn(column, vectors[first + column]);
            return matrix;
        }

        private static bool ResetHistoryMatchesCurrent(Vector4[] vectors)
        {
            return VectorRangeExactlyEqual(
                    vectors,
                    EndfieldRecoveredDeferredTransformVariablesContract
                        .NonJitteredViewNoTranslationProjectionFirstVector,
                    vectors,
                    EndfieldRecoveredDeferredTransformVariablesContract
                        .PreviousNonJitteredViewNoTranslationProjectionFirstVector,
                    4) &&
                VectorExactlyEqual(
                    vectors[
                        EndfieldRecoveredDeferredTransformVariablesContract
                            .CameraPositionVector],
                    vectors[
                        EndfieldRecoveredDeferredTransformVariablesContract
                            .PreviousCameraPositionVector]);
        }

        private static bool ContiguousHistoryMatchesPrevious(
            Camera camera,
            Vector4[] previous)
        {
            Matrix4x4 previousProjection = UnpackMatrix(
                previous,
                EndfieldRecoveredDeferredTransformVariablesContract
                    .NonJitteredViewNoTranslationProjectionFirstVector);
            Vector4 previousCameraVector = previous[
                EndfieldRecoveredDeferredTransformVariablesContract
                    .CameraPositionVector];
            Vector3 previousCamera = new Vector3(
                previousCameraVector.x,
                previousCameraVector.y,
                previousCameraVector.z);
            Matrix4x4 movedView = Matrix4x4.TRS(
                camera.transform.position + new Vector3(0.5f, -0.25f, 1.0f),
                Quaternion.Euler(17.0f, -19.0f, 5.0f),
                Vector3.one).inverse;
            Matrix4x4 gpuProjection = GL.GetGPUProjectionMatrix(
                camera.projectionMatrix,
                true);
            var current = new Vector4[
                EndfieldRecoveredDeferredTransformVariablesContract.VectorCount];
            if (!EndfieldRecoveredDeferredTransformVariablesContract.TryBuild(
                    movedView,
                    gpuProjection,
                    gpuProjection,
                    camera.transform.position +
                        new Vector3(0.5f, -0.25f, 1.0f),
                    previousProjection,
                    previousCamera,
                    true,
                    current,
                    out _))
            {
                return false;
            }
            return VectorRangeExactlyEqual(
                    previous,
                    EndfieldRecoveredDeferredTransformVariablesContract
                        .NonJitteredViewNoTranslationProjectionFirstVector,
                    current,
                    EndfieldRecoveredDeferredTransformVariablesContract
                        .PreviousNonJitteredViewNoTranslationProjectionFirstVector,
                    4) &&
                VectorExactlyEqual(
                    previous[
                        EndfieldRecoveredDeferredTransformVariablesContract
                            .CameraPositionVector],
                    current[
                        EndfieldRecoveredDeferredTransformVariablesContract
                            .PreviousCameraPositionVector]);
        }

        private static bool DiscontinuityResetIgnoresStaleHistory(Camera camera)
        {
            Matrix4x4 view = camera.worldToCameraMatrix;
            Matrix4x4 projection = GL.GetGPUProjectionMatrix(
                camera.projectionMatrix,
                true);
            var current = new Vector4[
                EndfieldRecoveredDeferredTransformVariablesContract.VectorCount];
            if (!EndfieldRecoveredDeferredTransformVariablesContract.TryBuild(
                    view,
                    projection,
                    projection,
                    camera.transform.position,
                    Matrix4x4.Scale(new Vector3(9.0f, 8.0f, 7.0f)),
                    new Vector3(6.0f, 5.0f, 4.0f),
                    false,
                    current,
                    out _))
            {
                return false;
            }
            return ResetHistoryMatchesCurrent(current);
        }

        private static bool VectorRangeExactlyEqual(
            Vector4[] left,
            int leftFirst,
            Vector4[] right,
            int rightFirst,
            int count)
        {
            for (int index = 0; index < count; index++)
            {
                if (!VectorExactlyEqual(
                        left[leftFirst + index],
                        right[rightFirst + index]))
                    return false;
            }
            return true;
        }

        private static bool VectorExactlyEqual(Vector4 left, Vector4 right)
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

        private static bool DuplicateSameFrameRejected(
            Camera camera,
            out bool sourceReadyReset)
        {
            sourceReadyReset = false;
            var owner = new EndfieldRecoveredDeferredTransformVariables();
            var command = new CommandBuffer
            {
                name = "Verify duplicate TransformVariables publication"
            };
            try
            {
                bool first = owner.PrepareAndPublish(
                    camera,
                    true,
                    640,
                    720,
                    command,
                    out _);
                bool firstReady = owner.CurrentM27SourceReady;
                bool second = owner.PrepareAndPublish(
                    camera,
                    true,
                    640,
                    720,
                    command,
                    out string diagnostic);
                sourceReadyReset = !owner.CurrentM27SourceReady;
                return first && firstReady && !second &&
                    diagnostic != null && diagnostic.Contains("twice");
            }
            finally
            {
                command.Release();
                owner.Dispose();
            }
        }

        private static bool TemporalHistoryStatePolicyPassed()
        {
            var history = new EndfieldRecoveredDeferredTransformVariablesContract
                .CameraHistoryState();
            if (!EndfieldRecoveredDeferredTransformVariablesContract
                    .TryEvaluateHistory(
                        history, 0, 640, 720, true,
                        out bool initialReady, out _) || initialReady)
            {
                return false;
            }
            EndfieldRecoveredDeferredTransformVariablesContract.CommitHistory(
                history,
                Matrix4x4.identity,
                new Vector3(1.0f, 2.0f, 3.0f),
                0,
                640,
                720,
                true);
            if (!EndfieldRecoveredDeferredTransformVariablesContract
                    .TryEvaluateHistory(
                        history, 1, 640, 720, true,
                        out bool contiguousReady, out _) || !contiguousReady)
            {
                return false;
            }
            if (!EndfieldRecoveredDeferredTransformVariablesContract
                    .TryEvaluateHistory(
                        history, 1, 641, 720, true,
                        out bool resizedReady, out _) || resizedReady)
            {
                return false;
            }
            if (!EndfieldRecoveredDeferredTransformVariablesContract
                    .TryEvaluateHistory(
                        history, 1, 640, 720, false,
                        out bool targetChangedReady, out _) ||
                targetChangedReady)
            {
                return false;
            }
            if (!EndfieldRecoveredDeferredTransformVariablesContract
                    .TryEvaluateHistory(
                        history, 2, 640, 720, true,
                        out bool gapReady, out _) || gapReady)
            {
                return false;
            }
            return !EndfieldRecoveredDeferredTransformVariablesContract
                .TryEvaluateHistory(
                    history, 0, 640, 720, true,
                    out _, out string duplicateFailure) &&
                duplicateFailure != null &&
                duplicateFailure.Contains("twice");
        }

        private static bool MatrixApproximatelyIdentity(
            Matrix4x4 matrix,
            float tolerance)
        {
            for (int row = 0; row < 4; row++)
            {
                for (int column = 0; column < 4; column++)
                {
                    float expected = row == column ? 1.0f : 0.0f;
                    if (Mathf.Abs(matrix[row, column] - expected) > tolerance)
                        return false;
                }
            }
            return true;
        }

        private static float WorldClipRoundTripError(
            Camera camera,
            Matrix4x4 inverseViewProjection)
        {
            Vector3 world = camera.transform.position +
                camera.transform.forward * 5.0f +
                camera.transform.right * 0.25f +
                camera.transform.up * 0.125f;
            Matrix4x4 viewProjection =
                GL.GetGPUProjectionMatrix(camera.projectionMatrix, true) *
                camera.worldToCameraMatrix;
            Vector4 clip = viewProjection * new Vector4(
                world.x,
                world.y,
                world.z,
                1.0f);
            Vector4 restored = inverseViewProjection * clip;
            Vector3 reconstructed = new Vector3(
                restored.x / restored.w,
                restored.y / restored.w,
                restored.z / restored.w);
            Vector3 delta = reconstructed - world;
            return Mathf.Max(
                Mathf.Abs(delta.x),
                Mathf.Abs(delta.y),
                Mathf.Abs(delta.z));
        }

        private static string[] HexWords(uint[] words)
        {
            var result = new string[words.Length];
            for (int index = 0; index < words.Length; index++)
                result[index] = "0x" + words[index].ToString("X8");
            return result;
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
