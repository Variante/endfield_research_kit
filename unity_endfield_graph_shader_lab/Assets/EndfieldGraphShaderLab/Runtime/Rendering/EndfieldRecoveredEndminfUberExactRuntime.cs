using System;
using System.Runtime.InteropServices;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Source-sparse D3D11 transport for Endminf's exact ordinary and
    /// BLOOM + RADIAL_BLUR + VIGNETTE peak Uber draws. The native side
    /// owns the stage-local captured constant payload and exact DXBC objects;
    /// this bridge owns stable Unity textures and schedules their copies before
    /// the render-thread event.
    /// </summary>
    internal sealed class EndfieldRecoveredEndminfUberExactRuntime : IDisposable
    {
        internal const string EnvironmentVariable =
            "ENDFIELD_RECOVERED_ENDMINF_UBER_EXACT";
        internal const string EarlyDiagnosticEnvironmentVariable =
            "ENDFIELD_RECOVERED_ENDMINF_UBER_EARLY_DIAGNOSTIC";
        private const string NativeLibrary = "OriginalDxbcSwapPlugin";
        // Capture 20260827T183054Z supplies two independently registered exact
        // combined-Uber packets. Frame 1600's retained radial/chromatic values
        // solve the authored source curves to 0.02256267 s; its accumulated
        // backbuffer maps to clean reference frame 8. Frame 1818 maps to clean
        // reference frame 264 / 4.35 s in the body/reference clock, while its
        // retained c0.z/c25.y values solve the authenticated source-effect
        // clock to 4.4333334 s. Their other PS lanes differ materially, so each
        // is admitted for only its nearest 60 Hz source-effect sample.
        internal const float EarlyCapturePhaseSeconds = 0.02256267f;
        internal const float CapturePhaseSeconds = 4.4333334f;
        private const float HalfWindowSeconds = 1.0f / 120.0f;

        private RenderTexture sourceTexture;
        private RenderTexture bloomTexture;
        private RenderTexture outputTexture;
        private IntPtr renderEvent;
        private bool initialized;
        private bool failed;
        private bool submissionPending;
        private uint validatedDrawCount;
        private string failure = string.Empty;
        private bool loggedActivation;
        private bool loggedValidation;
        private bool loggedFailure;

        internal bool Requested => string.Equals(
            System.Environment.GetEnvironmentVariable(EnvironmentVariable),
            "1",
            StringComparison.Ordinal);

        internal string Failure => failure;

        internal bool HasPendingValidation => submissionPending;

        internal string LastSubmittedVariant { get; private set; } = string.Empty;

        internal bool ValidatePendingAfterSynchronizedRender(
            out string validationFailure)
        {
            validationFailure = string.Empty;
            if (!submissionPending)
                return true;
            bool valid = ValidatePending();
            if (!valid)
                validationFailure = failure;
            return valid;
        }

        internal bool Enqueue(
            CommandBuffer command,
            RenderTargetIdentifier source,
            RenderTargetIdentifier bloom,
            Texture lut,
            RenderTargetIdentifier destination,
            int width,
            int height,
            int bloomWidth,
            int bloomHeight,
            float exposure,
            bool hasPost,
            EndfieldEndminfVisualCompatibilityClock.RecoveredPostState post)
        {
            if (!Requested || failed)
                return false;
            if (command == null || lut == null)
                return Fail("exact Uber inputs are incomplete");
            if (SystemInfo.graphicsDeviceType != GraphicsDeviceType.Direct3D11)
                return Fail("exact Uber transport requires Direct3D11");
            if (!ValidatePending())
                return false;
            if (!Initialize())
                return false;
            if (!EnsureTextures(width, height, bloomWidth, bloomHeight))
                return false;

            IntPtr sourcePointer = sourceTexture.GetNativeTexturePtr();
            IntPtr bloomPointer = bloomTexture.GetNativeTexturePtr();
            IntPtr lutPointer = lut.GetNativeTexturePtr();
            if (sourcePointer == IntPtr.Zero || bloomPointer == IntPtr.Zero ||
                lutPointer == IntPtr.Zero)
            {
                return Fail("exact Uber native texture pointers are null");
            }

            Vector2 center = hasPost
                ? post.centerViewport
                : new Vector2(0.5f, 0.5f);
            float radial = hasPost ? post.radialIntensity : 0.0f;
            float power = hasPost ? post.effectivePower : 1.0f;
            uint variant = EarlyDiagnosticRequested &&
                IsEarlyCapturedPhase(hasPost, post)
                ? 2u
                : IsCapturedPhase(hasPost, post) ? 1u : 0u;
            uint packet;
            try
            {
                if (Native.GetPayloadReady() != 1)
                    return Fail(
                        "validated Endminf Uber live constant payload is unavailable");
                if (Native.SetTextureResources(
                        sourcePointer, bloomPointer, lutPointer) != 1)
                {
                    return Fail("native exact Uber texture gate rejected its inputs");
                }
                packet = Native.QueuePacketVariant(
                    variant,
                    width,
                    height,
                    exposure,
                    center.x,
                    center.y,
                    radial,
                    power);
            }
            catch (Exception exception)
            {
                return Fail("native exact Uber queue failed: " + exception.Message);
            }
            if (packet == 0 || packet > int.MaxValue)
                return Fail("native exact Uber packet ring rejected the frame");
            LastSubmittedVariant = variant == 2u
                ? "early"
                : variant == 1u ? "peak" : "normal";

            // The temporary SRP identifiers cannot expose stable native
            // pointers. Copy them into persistent exact-format resources first;
            // the plugin event then samples those resources and writes a distinct
            // persistent linear-UNorm output.
            command.CopyTexture(source, new RenderTargetIdentifier(sourceTexture));
            command.CopyTexture(bloom, new RenderTargetIdentifier(bloomTexture));
            // Unity 2022 promotes a requested D24S8 RenderTexture to D32S8 on
            // this adapter. The native exact draw therefore creates, clears,
            // binds, validates, and releases/restores its own R24G8/D24S8
            // attachment around the retail fullscreen draw.
            command.SetRenderTarget(new RenderTargetIdentifier(outputTexture));
            command.IssuePluginEvent(renderEvent, checked((int)packet));
            command.CopyTexture(
                new RenderTargetIdentifier(outputTexture), destination);
            submissionPending = true;

            if (!loggedActivation)
            {
                Debug.Log(
                    "Recovered exact Endminf Uber native draw submitted: " +
                    (variant == 2u ? "Early" : variant == 1u ? "Peak" : "Normal") + "; " +
                    "RGBA16F source, packed half-resolution bloom, FP16 LogLut2D, " +
                    "linear R8G8B8A8_UNorm output.");
                loggedActivation = true;
            }
            return true;
        }

        internal static bool IsCapturedPhase(
            bool hasPost,
            EndfieldEndminfVisualCompatibilityClock.RecoveredPostState post)
        {
            return hasPost &&
                post.mode == 6 &&
                !float.IsNaN(post.elapsed) &&
                !float.IsInfinity(post.elapsed) &&
                Mathf.Abs(post.elapsed - CapturePhaseSeconds) <=
                    HalfWindowSeconds;
        }

        internal static bool IsEarlyCapturedPhase(
            bool hasPost,
            EndfieldEndminfVisualCompatibilityClock.RecoveredPostState post)
        {
            return hasPost &&
                post.mode == 6 &&
                !float.IsNaN(post.elapsed) &&
                !float.IsInfinity(post.elapsed) &&
                Mathf.Abs(post.elapsed - EarlyCapturePhaseSeconds) <=
                    HalfWindowSeconds;
        }

        private static bool EarlyDiagnosticRequested => string.Equals(
            System.Environment.GetEnvironmentVariable(
                EarlyDiagnosticEnvironmentVariable),
            "1",
            StringComparison.Ordinal);

        public void Dispose()
        {
            ReleaseTexture(ref sourceTexture);
            ReleaseTexture(ref bloomTexture);
            ReleaseTexture(ref outputTexture);
        }

        private bool Initialize()
        {
            if (initialized)
                return true;
            try
            {
                renderEvent = Native.GetRenderEventFunc();
                if (renderEvent == IntPtr.Zero)
                    return Fail("native exact Uber render event is unavailable");
                Native.ResetRuntimeState();
            }
            catch (Exception exception)
            {
                return Fail(
                    "native exact Uber transport could not initialize: " +
                    exception.Message);
            }
            initialized = true;
            return true;
        }

        private bool ValidatePending()
        {
            if (!submissionPending)
                return true;
            submissionPending = false;
            try
            {
                uint draws = Native.GetDrawCount();
                uint failures = Native.GetFailureCount();
                int result = Native.GetLastResult();
                uint stage = Native.GetFailureStage();
                if (draws <= validatedDrawCount || failures != 0 || result < 0)
                {
                    return Fail(
                        "native exact Uber result drifted: draws=" + draws +
                        ", previous=" + validatedDrawCount +
                        ", failures=" + failures +
                        ", stage=" + stage +
                        ", hresult=0x" +
                        unchecked((uint)result).ToString("x8"));
                }
                validatedDrawCount = draws;
                if (!loggedValidation)
                {
                    Debug.Log(
                        "Recovered exact Endminf Uber native draw validated: " +
                        "draw count advanced with no native failure.");
                    loggedValidation = true;
                }
                return true;
            }
            catch (Exception exception)
            {
                return Fail(
                    "native exact Uber validation failed: " + exception.Message);
            }
        }

        private bool EnsureTextures(
            int width,
            int height,
            int bloomWidth,
            int bloomHeight)
        {
            if (width <= 0 || height <= 0 || bloomWidth <= 0 || bloomHeight <= 0)
                return Fail("exact Uber texture dimensions are invalid");
            if (!EnsureTexture(
                    ref sourceTexture,
                    width,
                    height,
                    GraphicsFormat.R16G16B16A16_SFloat,
                    "Endfield Exact Uber Source RGBA16F",
                    FilterMode.Bilinear))
                return false;
            if (!EnsureTexture(
                    ref bloomTexture,
                    bloomWidth,
                    bloomHeight,
                    GraphicsFormat.B10G11R11_UFloatPack32,
                    "Endfield Exact Uber Bloom R11G11B10",
                    FilterMode.Bilinear))
                return false;
            if (!EnsureTexture(
                ref outputTexture,
                width,
                height,
                GraphicsFormat.R8G8B8A8_UNorm,
                "Endfield Exact Uber Linear UNorm Output",
                FilterMode.Point))
                return false;
            return true;
        }

        private bool EnsureTexture(
            ref RenderTexture texture,
            int width,
            int height,
            GraphicsFormat format,
            string name,
            FilterMode filter)
        {
            if (texture != null && texture.IsCreated() &&
                texture.width == width && texture.height == height &&
                texture.graphicsFormat == format)
                return true;
            ReleaseTexture(ref texture);
            if (!SystemInfo.IsFormatSupported(format, FormatUsage.Render))
                return Fail(name + " format is unsupported");
            var descriptor = new RenderTextureDescriptor(width, height)
            {
                graphicsFormat = format,
                depthStencilFormat = GraphicsFormat.None,
                msaaSamples = 1,
                useMipMap = false,
                autoGenerateMips = false,
                sRGB = false,
            };
            texture = new RenderTexture(descriptor)
            {
                hideFlags = HideFlags.HideAndDontSave,
                name = name,
                filterMode = filter,
                wrapMode = TextureWrapMode.Clamp,
                anisoLevel = 0,
            };
            if (!texture.Create())
            {
                ReleaseTexture(ref texture);
                return Fail("could not create " + name);
            }
            return true;
        }

        private bool Fail(string reason)
        {
            failed = true;
            failure = reason ?? "unknown exact Uber failure";
            if (!loggedFailure)
            {
                Debug.LogWarning(
                    "Recovered exact Endminf Uber failed closed: " +
                    failure + ". Compatibility Uber remains active.");
                loggedFailure = true;
            }
            return false;
        }

        private static void ReleaseTexture(ref RenderTexture texture)
        {
            if (texture == null)
                return;
            texture.Release();
            if (Application.isPlaying)
                UnityEngine.Object.Destroy(texture);
            else
                UnityEngine.Object.DestroyImmediate(texture);
            texture = null;
        }

        private static class Native
        {
            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetEndminfUberPayloadReady")]
            internal static extern uint GetPayloadReady();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetEndminfUberRenderEventFunc")]
            internal static extern IntPtr GetRenderEventFunc();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcSetEndminfUberTextureResources")]
            internal static extern uint SetTextureResources(
                IntPtr source,
                IntPtr bloom,
                IntPtr lut);

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcQueueEndminfUberPacketVariant")]
            internal static extern uint QueuePacketVariant(
                uint variant,
                float screenWidth,
                float screenHeight,
                float exposure,
                float centerX,
                float centerY,
                float radialIntensity,
                float power);

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcResetEndminfUberRuntimeState")]
            internal static extern void ResetRuntimeState();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetEndminfUberDrawCount")]
            internal static extern uint GetDrawCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetEndminfUberFailureCount")]
            internal static extern uint GetFailureCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetEndminfUberLastResult")]
            internal static extern int GetLastResult();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetEndminfUberFailureStage")]
            internal static extern uint GetFailureStage();
        }
    }
}
