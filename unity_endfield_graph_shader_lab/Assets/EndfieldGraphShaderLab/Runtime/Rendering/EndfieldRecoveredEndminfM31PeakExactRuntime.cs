using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using UnityEngine;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Default-off temporal admission for the exact two-draw M31 shell
    /// transport. Retail places M29/M30 and their surrounding transparent
    /// cohort between the two M31 draws, so the native payload is submitted at
    /// two pipeline insertion points. Unsupported packet shapes fall back to
    /// the ordinary renderer.
    /// </summary>
    public static class EndfieldRecoveredEndminfM31PeakExactRuntime
    {
        internal const string EnvironmentVariable =
            "ENDFIELD_RECOVERED_ENDMINF_M31_PEAK_EXACT";
        private const string NativeLibrary = "OriginalDxbcSwapPlugin";
        private const string MaterialName = "M_fx_endminm_gfx_31";
        private const float ViewerLeadSeconds = 2.0f / 60.0f;

        private static readonly List<ParticleSystemRenderer> Renderers =
            new List<ParticleSystemRenderer>();
        private static IntPtr renderEvent;
        private static bool prepared;
        private static bool failed;
        private static bool active;
        private static bool firstSubmissionPending;
        private static bool submissionPending;
        private static string failure = string.Empty;
        private static int selectedPacket = -1;
        private static uint validatedDrawCount;
        private static bool loggedActivation;
        private static bool loggedValidation;
        private static bool loggedFailure;
        private static bool loggedAdmission;
        private static bool loggedMissingRenderers;

        public static bool Requested => string.Equals(
            System.Environment.GetEnvironmentVariable(EnvironmentVariable),
            "1", StringComparison.Ordinal);

        internal static string Failure => failure;
        internal static bool HasPendingFirstSubmission => firstSubmissionPending;
        public static bool HasPendingValidation => submissionPending;

        internal static bool PrepareBeforeCulling(Camera camera)
        {
            active = false;
            selectedPacket = -1;
            if (!Requested || failed)
            {
                RestoreRenderers();
                return false;
            }
            if (SystemInfo.graphicsDeviceType != GraphicsDeviceType.Direct3D11)
                return Fail("exact M31 peak transport requires Direct3D11");
            if (camera == null ||
                camera.GetComponent<EndfieldHGOperatorPresentation>() == null)
            {
                RestoreRenderers();
                return false;
            }
            EndfieldHGOperatorLightRig lightRig =
                camera.GetComponent<EndfieldHGOperatorLightRig>();
            if (lightRig == null || lightRig.actorRoot == null ||
                !string.Equals(lightRig.actorRoot.name, "Endminf",
                    StringComparison.OrdinalIgnoreCase))
            {
                RestoreRenderers();
                return false;
            }
            if (!prepared && !PrepareNative())
                return false;

            float seconds = ResolveOverviewSeconds(lightRig.actorRoot);
            selectedPacket = float.IsNaN(seconds) ? -1 :
                ResolveNearestPacket(Mathf.Max(0.0f,
                    seconds - ViewerLeadSeconds));
            active = selectedPacket >= 0 &&
                EndfieldRecoveredM31PeakCaptureData.DrawCounts[selectedPacket] ==
                EndfieldRecoveredM31PeakCaptureData.NativePayloadDrawCount &&
                EndfieldRecoveredM31PeakCaptureData
                    .SplitOrderCompatible[selectedPacket];
            if (!loggedAdmission)
            {
                Debug.Log("Recovered exact Endminf M31 temporal admission: " +
                    "renderers=" + Renderers.Count + ", phase=" +
                    seconds.ToString("F6") + ", packet=" + selectedPacket +
                    ", splitCompatible=" + active + ".");
                loggedAdmission = true;
            }
            SetRendererSuppression(active);
            return active;
        }

        private static bool PrepareNative()
        {
            Renderers.Clear();
            foreach (ParticleSystemRenderer renderer in
                     UnityEngine.Object.FindObjectsOfType<ParticleSystemRenderer>(true))
            {
                if (renderer == null || !renderer.gameObject.scene.IsValid())
                    continue;
                Material material = renderer.sharedMaterial;
                if (material != null && material.name == MaterialName)
                    Renderers.Add(renderer);
            }
            if (Renderers.Count == 0)
            {
                if (!loggedMissingRenderers)
                {
                    Debug.Log("Recovered exact Endminf M31 peak is waiting for " +
                        "runtime-spawned M_fx_endminm_gfx_31 renderers.");
                    loggedMissingRenderers = true;
                }
                return false;
            }
            float[] phases = EndfieldRecoveredM31PeakCaptureData.PhaseSeconds;
            int[] frames = EndfieldRecoveredM31PeakCaptureData.SourceFrames;
            int[] drawCounts = EndfieldRecoveredM31PeakCaptureData.DrawCounts;
            int[] firstDrawOrdinals =
                EndfieldRecoveredM31PeakCaptureData.FirstDrawOrdinals;
            int[] lastDrawOrdinals =
                EndfieldRecoveredM31PeakCaptureData.LastDrawOrdinals;
            bool[] nativeOrderCompatible =
                EndfieldRecoveredM31PeakCaptureData.NativeOrderCompatible;
            bool[] splitOrderCompatible =
                EndfieldRecoveredM31PeakCaptureData.SplitOrderCompatible;
            int[] interleavedM29M30Counts =
                EndfieldRecoveredM31PeakCaptureData.InterleavedM29M30Counts;
            string[] hashes =
                EndfieldRecoveredM31PeakCaptureData.TemporalMetadataSha256;
            int packetCount = EndfieldRecoveredM31PeakCaptureData.PacketCount;
            if (!EndfieldRecoveredM31PeakCaptureData.PayloadPrepared ||
                !EndfieldRecoveredM31PeakCaptureData.DepthContractReady ||
                phases == null || frames == null || drawCounts == null ||
                firstDrawOrdinals == null || lastDrawOrdinals == null ||
                nativeOrderCompatible == null || splitOrderCompatible == null ||
                hashes == null || packetCount < 2 ||
                interleavedM29M30Counts == null ||
                phases.Length != packetCount || frames.Length != packetCount ||
                drawCounts.Length != packetCount ||
                firstDrawOrdinals.Length != packetCount ||
                lastDrawOrdinals.Length != packetCount ||
                nativeOrderCompatible.Length != packetCount ||
                splitOrderCompatible.Length != packetCount ||
                interleavedM29M30Counts.Length != packetCount ||
                hashes.Length != packetCount)
            {
                return Fail("the generated M31 temporal contract is incomplete");
            }
            bool foundAnchor = false;
            for (int index = 0; index < packetCount; ++index)
            {
                if (index > 0 && (phases[index] <= phases[index - 1] ||
                                  frames[index] <= frames[index - 1]))
                    return Fail("the generated M31 temporal order is invalid");
                if (drawCounts[index] <= 0 || string.IsNullOrEmpty(hashes[index]))
                    return Fail("the generated M31 packet identity is incomplete");
                if (firstDrawOrdinals[index] > lastDrawOrdinals[index] ||
                    lastDrawOrdinals[index] - firstDrawOrdinals[index] + 1 <
                        drawCounts[index])
                    return Fail("the generated M31 owner order is invalid");
                if (nativeOrderCompatible[index] !=
                    (lastDrawOrdinals[index] - firstDrawOrdinals[index] + 1 ==
                        drawCounts[index]))
                    return Fail("the generated M31 transport-order gate drifted");
                bool expectedSplitOrder = drawCounts[index] ==
                        EndfieldRecoveredM31PeakCaptureData.NativePayloadDrawCount &&
                    interleavedM29M30Counts[index] == 2;
                if (splitOrderCompatible[index] != expectedSplitOrder)
                    return Fail("the generated M31 split-order gate drifted");
                if (interleavedM29M30Counts[index] < 0 ||
                    nativeOrderCompatible[index] &&
                    interleavedM29M30Counts[index] != 0)
                    return Fail("the generated M31/M29/M30 owner order drifted");
                if (frames[index] ==
                    EndfieldRecoveredM31PeakCaptureData.AnchorFrame)
                {
                    foundAnchor = Mathf.Abs(phases[index] -
                        EndfieldRecoveredM31PeakCaptureData.AnchorPhaseSeconds) <=
                        0.000001f;
                }
            }
            if (!foundAnchor)
                return Fail("the generated M31 QPC phase anchor drifted");
            try
            {
                renderEvent = Native.GetRenderEventFunc();
                if (renderEvent == IntPtr.Zero)
                    return Fail("the native M31 peak event is unavailable");
                Native.ResetRuntimeState();
            }
            catch (Exception exception)
            {
                return Fail("the native M31 peak transport could not initialize: " +
                    exception.Message);
            }
            validatedDrawCount = 0;
            firstSubmissionPending = false;
            submissionPending = false;
            prepared = true;
            return true;
        }

        private static int ResolveNearestPacket(float seconds)
        {
            float[] phases = EndfieldRecoveredM31PeakCaptureData.PhaseSeconds;
            float leadingHalfSpacing = (phases[1] - phases[0]) * 0.5f;
            float trailingHalfSpacing =
                (phases[phases.Length - 1] - phases[phases.Length - 2]) * 0.5f;
            if (seconds < phases[0] - leadingHalfSpacing ||
                seconds > phases[phases.Length - 1] + trailingHalfSpacing)
                return -1;

            int nearest = 0;
            float nearestDistance = Mathf.Abs(seconds - phases[0]);
            for (int index = 1; index < phases.Length; ++index)
            {
                float distance = Mathf.Abs(seconds - phases[index]);
                if (distance < nearestDistance)
                {
                    nearest = index;
                    nearestDistance = distance;
                }
            }
            return nearest;
        }

        private static float ResolveOverviewSeconds(Transform actorRoot)
        {
            EndfieldOverviewPlayback playback = actorRoot != null
                ? actorRoot.GetComponentInChildren<EndfieldOverviewPlayback>(true)
                : null;
            Animator animator = playback != null ? playback.animatorSource : null;
            if (playback != null && playback.AnimatorContractActive &&
                animator != null && animator.enabled)
            {
                AnimatorClipInfo[] clips = animator.GetCurrentAnimatorClipInfo(0);
                if (clips.Length == 0 || clips[0].clip == null ||
                    clips[0].clip.name.IndexOf(
                        "overview_start", StringComparison.OrdinalIgnoreCase) < 0)
                    return float.NaN;
                float seconds = animator.GetCurrentAnimatorStateInfo(0)
                    .normalizedTime * clips[0].clip.length;
                return Mathf.Max(0.0f, seconds);
            }
            Animation animation = actorRoot != null
                ? actorRoot.GetComponentInChildren<Animation>(true)
                : null;
            AnimationState state = animation != null
                ? animation["ui_overview_start"] : null;
            if (state == null || !state.enabled)
                return float.NaN;
            return Mathf.Max(0.0f, state.time);
        }

        internal static bool RenderFirst(
            ScriptableRenderContext context,
            Camera camera,
            EndfieldRecoveredSceneColorHandle sceneColor,
            RenderTexture sceneMV,
            RenderTexture sceneDepth)
        {
            if (firstSubmissionPending)
                return Fail("the previous M31 split submission is incomplete");
            if (!RenderSplitEvent(
                    context, camera, sceneColor, sceneMV, sceneDepth, 0))
                return false;
            firstSubmissionPending = true;
            return true;
        }

        internal static bool RenderSecond(
            ScriptableRenderContext context,
            Camera camera,
            EndfieldRecoveredSceneColorHandle sceneColor,
            RenderTexture sceneMV,
            RenderTexture sceneDepth)
        {
            if (!firstSubmissionPending)
                return Fail("the second M31 split event has no first event");
            if (!RenderSplitEvent(
                    context, camera, sceneColor, sceneMV, sceneDepth, 1))
                return false;
            firstSubmissionPending = false;
            submissionPending = true;
            if (!loggedActivation)
            {
                Debug.Log(
                    "Recovered exact Endminf M31 submitted around the retail " +
                    "M29/M30 owner interval inside the " +
                    EndfieldRecoveredM31PeakCaptureData.PacketCount +
                    "-packet temporal envelope from capture " +
                    EndfieldRecoveredM31PeakCaptureData.TemporalSourceSession +
                    "; exact payload capture " +
                    EndfieldRecoveredM31PeakCaptureData.PayloadSourceSession +
                    " frame " +
                    EndfieldRecoveredM31PeakCaptureData.PayloadSourceFrame + ".");
                loggedActivation = true;
            }
            return true;
        }

        internal static void AbortPendingSplit(string reason)
        {
            if (firstSubmissionPending)
                Fail(reason ?? "the M31 split owner interval failed");
        }

        private static bool RenderSplitEvent(
            ScriptableRenderContext context,
            Camera camera,
            EndfieldRecoveredSceneColorHandle sceneColor,
            RenderTexture sceneMV,
            RenderTexture sceneDepth,
            int eventId)
        {
            if (!Requested || failed || !prepared || !active ||
                selectedPacket < 0)
                return false;
            if (camera == null || sceneMV == null || sceneDepth == null ||
                renderEvent == IntPtr.Zero)
                return Fail("the exact M31 peak render resources are incomplete");
            IntPtr depthPointer = sceneDepth.GetNativeTexturePtr();
            if (depthPointer == IntPtr.Zero)
                return Fail("the exact M31 peak depth pointer is null");
            try
            {
                if (Native.SetDepthResource(depthPointer) != 1)
                    return Fail("the native M31 peak depth gate rejected its input");
            }
            catch (Exception exception)
            {
                return Fail("the native M31 peak depth gate failed: " +
                    exception.Message);
            }

            var command = new CommandBuffer
            {
                name = "Recovered exact Endminf M31 split SceneColor/SceneMV draw"
            };
            command.SetRenderTarget(
                new[] { sceneColor.Target, new RenderTargetIdentifier(sceneMV) },
                new RenderTargetIdentifier(BuiltinRenderTextureType.None));
            command.IssuePluginEvent(renderEvent, eventId);
            context.ExecuteCommandBuffer(command);
            command.Release();
            return true;
        }

        public static bool ValidatePendingAfterSynchronizedRender(
            out string validationFailure)
        {
            validationFailure = string.Empty;
            if (!submissionPending)
                return true;
            submissionPending = false;
            try
            {
                uint draws = Native.GetDrawCount();
                uint failures = Native.GetFailureCount();
                int result = Native.GetLastResult();
                uint submittedDraws = draws >= validatedDrawCount
                    ? draws - validatedDrawCount
                    : uint.MaxValue;
                if (submittedDraws !=
                        EndfieldRecoveredM31PeakCaptureData.NativePayloadDrawCount ||
                    failures != 0 || result < 0)
                {
                    validationFailure = "native M31 peak result drifted: draws=" +
                        draws + ", failures=" + failures + ", hresult=0x" +
                        unchecked((uint)result).ToString("x8") +
                        ", previousValidatedDraws=" + validatedDrawCount +
                        ", submittedDraws=" + submittedDraws;
                    return Fail(validationFailure);
                }
                validatedDrawCount = draws;
                if (!loggedValidation)
                {
                    Debug.Log("Recovered exact Endminf M31 peak validated: " +
                        "both split events completed with S_OK.");
                    loggedValidation = true;
                }
                return true;
            }
            catch (Exception exception)
            {
                validationFailure = exception.Message;
                return Fail(validationFailure);
            }
        }

        private static bool Fail(string reason)
        {
            failed = true;
            active = false;
            selectedPacket = -1;
            firstSubmissionPending = false;
            submissionPending = false;
            failure = reason ?? "unknown exact M31 peak failure";
            RestoreRenderers();
            if (!loggedFailure)
            {
                Debug.LogWarning("Recovered exact Endminf M31 peak failed closed: " +
                    failure + ".");
                loggedFailure = true;
            }
            return false;
        }

        private static void SetRendererSuppression(bool suppress)
        {
            foreach (ParticleSystemRenderer renderer in Renderers)
                if (renderer != null) renderer.enabled = !suppress;
        }

        private static void RestoreRenderers()
        {
            SetRendererSuppression(false);
        }

        private static class Native
        {
            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM31PeakRenderEventFunc")]
            internal static extern IntPtr GetRenderEventFunc();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcSetM31PeakDepthResource")]
            internal static extern uint SetDepthResource(IntPtr sceneDepth);

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcResetM31PeakRuntimeState")]
            internal static extern void ResetRuntimeState();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM31PeakDrawCount")]
            internal static extern uint GetDrawCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM31PeakFailureCount")]
            internal static extern uint GetFailureCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM31PeakLastResult")]
            internal static extern int GetLastResult();
        }
    }
}
