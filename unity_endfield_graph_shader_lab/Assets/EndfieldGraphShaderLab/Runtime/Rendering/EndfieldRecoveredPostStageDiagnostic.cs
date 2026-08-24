using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using Unity.Collections;
using UnityEngine;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Explicit five-stage post diagnostic. Normal rendering never arms it.
    /// Every stage is copied into an owned exact-format target before the
    /// source temporary can be reused or released.
    /// </summary>
    public static class EndfieldRecoveredPostStageDiagnostic
    {
        public const string BeforeTemporal = "before_temporal";
        public const string AfterTemporal = "after_temporal_bloom_input";
        public const string BloomPrefilterMip0 = "bloom_prefilter_mip0";
        public const string BloomReconstructedMip0 = "bloom_reconstructed_mip0";
        public const string FinalUber = "final_uber";

        private static readonly string[] ExpectedStages =
        {
            BeforeTemporal,
            AfterTemporal,
            BloomPrefilterMip0,
            BloomReconstructedMip0,
            FinalUber,
        };

        [Serializable]
        private sealed class StageReport
        {
            public string schema = "endfield.post-stage-capture.v1";
            public string status;
            public string label;
            public string cohort;
            public float sampleTime;
            public string stage;
            public string cameraName;
            public int width;
            public int height;
            public string graphicsFormat;
            public int byteLength;
            public int bytesPerPixel;
            public int nonzeroBytes;
            public string sha256;
            public string rawPath;
            public string failure;
        }

        private sealed class CaptureRequest
        {
            public string outputDirectory;
            public string label;
            public string cohort;
            public float sampleTime;
            public string cameraName;
            public readonly HashSet<string> stages =
                new HashSet<string>(StringComparer.Ordinal);
        }

        private static readonly object Gate = new object();
        private static CaptureRequest armed;
        private static CaptureRequest active;
        private static CaptureRequest completed;
        private static int pendingCount;
        private static string asynchronousFailure;

        public static void Arm(
            string outputDirectory,
            string label,
            string cohort,
            float sampleTime)
        {
            if (string.IsNullOrWhiteSpace(outputDirectory))
                throw new ArgumentException("Output directory is required.", nameof(outputDirectory));
            if (string.IsNullOrWhiteSpace(label))
                throw new ArgumentException("Capture label is required.", nameof(label));
            lock (Gate)
            {
                if (armed != null || active != null || completed != null ||
                    pendingCount != 0)
                    throw new InvalidOperationException(
                        "A post-stage capture is already active or pending.");
                armed = new CaptureRequest
                {
                    outputDirectory = Path.GetFullPath(outputDirectory),
                    label = label,
                    cohort = cohort ?? string.Empty,
                    sampleTime = sampleTime,
                };
            }
        }

        internal static void CaptureBeforeTemporalIfArmed(
            ScriptableRenderContext context,
            Camera camera,
            RenderTargetIdentifier source,
            RenderTextureDescriptor descriptor)
        {
            lock (Gate)
            {
                if (armed == null)
                    return;
                active = armed;
                armed = null;
                active.cameraName = camera != null ? camera.name : string.Empty;
            }
            var command = new CommandBuffer
            {
                name = "Capture recovered post stage before temporal resolve"
            };
            EnqueueStageIfActive(command, BeforeTemporal, source, descriptor);
            context.ExecuteCommandBuffer(command);
            command.Release();
        }

        internal static void EnqueueStageIfActive(
            CommandBuffer command,
            string stage,
            RenderTargetIdentifier source,
            RenderTextureDescriptor descriptor)
        {
            CaptureRequest request;
            lock (Gate)
            {
                request = active;
                if (request == null)
                    return;
                if (!request.stages.Add(stage))
                    throw new InvalidOperationException(
                        "Post stage was captured twice: " + stage);
                pendingCount++;
                if (string.Equals(stage, FinalUber, StringComparison.Ordinal))
                {
                    completed = request;
                    active = null;
                }
            }

            var report = new StageReport
            {
                status = "pending",
                label = request.label,
                cohort = request.cohort,
                sampleTime = request.sampleTime,
                stage = stage,
                cameraName = request.cameraName,
                width = descriptor.width,
                height = descriptor.height,
                graphicsFormat = descriptor.graphicsFormat.ToString(),
            };
            RenderTexture capture = null;
            try
            {
                descriptor.depthBufferBits = 0;
                descriptor.depthStencilFormat =
                    UnityEngine.Experimental.Rendering.GraphicsFormat.None;
                descriptor.msaaSamples = 1;
                descriptor.useMipMap = false;
                descriptor.autoGenerateMips = false;
                capture = new RenderTexture(descriptor)
                {
                    name = "Endfield post-stage diagnostic " +
                        request.label + " " + stage,
                    hideFlags = HideFlags.HideAndDontSave,
                    filterMode = FilterMode.Point,
                    wrapMode = TextureWrapMode.Clamp,
                };
                if (!capture.Create())
                    throw new InvalidOperationException(
                        "Could not allocate post-stage target for " + stage + ".");
                RenderTexture ownedCapture = capture;
                command.CopyTexture(source, ownedCapture);
                command.RequestAsyncReadback(ownedCapture, 0, readback =>
                    Complete(request, report, ownedCapture, readback));
                capture = null;
            }
            catch (Exception exception)
            {
                report.status = "failed_closed";
                report.failure = exception.ToString();
                WriteReport(request, report);
                RegisterCompletion(report.failure);
            }
            finally
            {
                Release(capture);
            }
        }

        public static void WaitForPending()
        {
            AsyncGPUReadback.WaitAllRequests();
            lock (Gate)
            {
                if (armed != null || active != null)
                    throw new InvalidOperationException(
                        "A post-stage request was not fully consumed by the pipeline.");
                if (pendingCount != 0)
                    throw new InvalidOperationException(
                        "Post-stage callbacks are still pending: " + pendingCount + ".");
                if (completed == null)
                    throw new InvalidOperationException(
                        "The final post stage was not captured.");
                foreach (string stage in ExpectedStages)
                {
                    if (!completed.stages.Contains(stage))
                        throw new InvalidOperationException(
                            "Required post stage was not captured: " + stage + ".");
                }
                completed = null;
                if (!string.IsNullOrEmpty(asynchronousFailure))
                {
                    string failure = asynchronousFailure;
                    asynchronousFailure = null;
                    throw new InvalidOperationException(failure);
                }
            }
        }

        private static void Complete(
            CaptureRequest request,
            StageReport report,
            RenderTexture capture,
            AsyncGPUReadbackRequest readback)
        {
            string failure = null;
            try
            {
                if (readback.hasError)
                    throw new InvalidOperationException(
                        "Post-stage GPU readback failed: " + report.stage + ".");
                NativeArray<byte> data = readback.GetData<byte>();
                byte[] raw = data.ToArray();
                int nonzero = 0;
                for (int index = 0; index < raw.Length; index++)
                {
                    if (raw[index] != 0)
                        nonzero++;
                }
                string directory = Path.Combine(
                    request.outputDirectory,
                    SafeFileName(request.label));
                Directory.CreateDirectory(directory);
                string rawPath = Path.Combine(
                    directory,
                    SafeFileName(report.stage) + ".raw");
                File.WriteAllBytes(rawPath, raw);
                report.status = "ok";
                report.byteLength = raw.Length;
                report.bytesPerPixel = raw.Length /
                    Math.Max(1, report.width * report.height);
                report.nonzeroBytes = nonzero;
                report.sha256 = Hash(raw);
                report.rawPath = rawPath;
            }
            catch (Exception exception)
            {
                report.status = "failed_closed";
                report.failure = exception.ToString();
                failure = report.failure;
            }
            finally
            {
                Release(capture);
                WriteReport(request, report);
                RegisterCompletion(failure);
            }
        }

        private static void RegisterCompletion(string failure)
        {
            lock (Gate)
            {
                pendingCount--;
                if (!string.IsNullOrEmpty(failure) &&
                    string.IsNullOrEmpty(asynchronousFailure))
                {
                    asynchronousFailure = failure;
                }
            }
        }

        private static void WriteReport(
            CaptureRequest request,
            StageReport report)
        {
            string directory = Path.Combine(
                request.outputDirectory,
                SafeFileName(request.label));
            Directory.CreateDirectory(directory);
            File.WriteAllText(
                Path.Combine(directory, SafeFileName(report.stage) + ".json"),
                JsonUtility.ToJson(report, true) + "\n",
                new UTF8Encoding(false));
        }

        private static string SafeFileName(string value)
        {
            char[] invalid = Path.GetInvalidFileNameChars();
            var builder = new StringBuilder(value.Length);
            foreach (char character in value)
            {
                builder.Append(Array.IndexOf(invalid, character) >= 0
                    ? '_'
                    : character);
            }
            return builder.ToString();
        }

        private static string Hash(byte[] data)
        {
            using (SHA256 sha = SHA256.Create())
            {
                return BitConverter.ToString(sha.ComputeHash(data))
                    .Replace("-", string.Empty)
                    .ToLowerInvariant();
            }
        }

        private static void Release(RenderTexture texture)
        {
            if (texture == null)
                return;
            texture.Release();
            if (Application.isPlaying)
                UnityEngine.Object.Destroy(texture);
            else
                UnityEngine.Object.DestroyImmediate(texture);
        }
    }
}
