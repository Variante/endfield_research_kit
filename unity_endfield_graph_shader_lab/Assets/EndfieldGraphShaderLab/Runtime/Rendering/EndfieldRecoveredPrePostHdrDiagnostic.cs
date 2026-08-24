using System;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using Unity.Collections;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Explicit one-shot diagnostic for the canonical physical-HDR scene color
    /// immediately before bloom/Uber. Normal rendering never arms this path.
    /// </summary>
    public static class EndfieldRecoveredPrePostHdrDiagnostic
    {
        [Serializable]
        private sealed class CaptureReport
        {
            public string schema = "endfield.pre-post-hdr-capture.v2";
            public string status;
            public string label;
            public string cohort;
            public float sampleTime;
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
        }

        private static readonly object Gate = new object();
        private static CaptureRequest armed;
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
                if (armed != null)
                    throw new InvalidOperationException(
                        "A pre-post HDR capture is already armed: " + armed.label);
                armed = new CaptureRequest
                {
                    outputDirectory = Path.GetFullPath(outputDirectory),
                    label = label,
                    cohort = cohort ?? string.Empty,
                    sampleTime = sampleTime,
                };
            }
        }

        internal static void CaptureIfArmed(
            ScriptableRenderContext context,
            Camera camera,
            RenderTargetIdentifier source,
            RenderTextureDescriptor sourceDescriptor)
        {
            CaptureRequest request;
            lock (Gate)
            {
                request = armed;
                armed = null;
                if (request == null)
                    return;
                pendingCount++;
            }

            var report = new CaptureReport
            {
                status = "pending",
                label = request.label,
                cohort = request.cohort,
                sampleTime = request.sampleTime,
                cameraName = camera != null ? camera.name : string.Empty,
                width = sourceDescriptor.width,
                height = sourceDescriptor.height,
                graphicsFormat = sourceDescriptor.graphicsFormat.ToString(),
            };
            RenderTexture capture = null;
            try
            {
                if (sourceDescriptor.graphicsFormat !=
                    HGCompatRenderPipeline.RecoveredSceneColorFormat)
                {
                    throw new InvalidOperationException(
                        "Pre-post HDR source format drifted: expected " +
                        HGCompatRenderPipeline.RecoveredSceneColorFormat +
                        ", actual " + sourceDescriptor.graphicsFormat + ".");
                }
                if (!SystemInfo.supportsAsyncGPUReadback)
                    throw new InvalidOperationException(
                        "AsyncGPUReadback is unavailable on the active graphics device.");

                var descriptor = sourceDescriptor;
                descriptor.depthBufferBits = 0;
                descriptor.depthStencilFormat = GraphicsFormat.None;
                descriptor.msaaSamples = 1;
                descriptor.useMipMap = false;
                descriptor.autoGenerateMips = false;
                capture = new RenderTexture(descriptor)
                {
                    name = "Endfield pre-post HDR diagnostic " + request.label,
                    hideFlags = HideFlags.HideAndDontSave,
                    filterMode = FilterMode.Point,
                    wrapMode = TextureWrapMode.Clamp,
                };
                if (!capture.Create())
                    throw new InvalidOperationException(
                        "Could not allocate the pre-post HDR diagnostic target.");

                RenderTexture ownedCapture = capture;
                var command = new CommandBuffer
                {
                    name = "Capture recovered pre-post HDR scene color"
                };
                command.CopyTexture(source, new RenderTargetIdentifier(ownedCapture));
                command.RequestAsyncReadback(ownedCapture, 0, readback =>
                    Complete(request, report, ownedCapture, readback));
                context.ExecuteCommandBuffer(command);
                command.Release();
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
                if (armed != null)
                    throw new InvalidOperationException(
                        "A pre-post HDR capture remained armed but was never consumed: " +
                        armed.label);
                if (pendingCount != 0)
                    throw new InvalidOperationException(
                        "Pre-post HDR callbacks are still pending: " + pendingCount + ".");
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
            CaptureReport report,
            RenderTexture capture,
            AsyncGPUReadbackRequest readback)
        {
            string failure = null;
            try
            {
                if (readback.hasError)
                    throw new InvalidOperationException("HDR GPU readback failed.");
                NativeArray<byte> data = readback.GetData<byte>();
                byte[] raw = data.ToArray();
                int nonzero = 0;
                for (int index = 0; index < raw.Length; index++)
                {
                    if (raw[index] != 0)
                        nonzero++;
                }
                string baseName = SafeFileName(request.label);
                Directory.CreateDirectory(request.outputDirectory);
                string rawPath = Path.Combine(
                    request.outputDirectory,
                    baseName + ".raw");
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
            CaptureReport report)
        {
            Directory.CreateDirectory(request.outputDirectory);
            string path = Path.Combine(
                request.outputDirectory,
                SafeFileName(request.label) + ".json");
            File.WriteAllText(
                path,
                JsonUtility.ToJson(report, true) + "\n",
                new UTF8Encoding(false));
        }

        private static string SafeFileName(string value)
        {
            char[] invalid = Path.GetInvalidFileNameChars();
            var builder = new StringBuilder(value.Length);
            for (int index = 0; index < value.Length; index++)
            {
                char character = value[index];
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
