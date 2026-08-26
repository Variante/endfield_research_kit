using System;
using System.Runtime.InteropServices;
using UnityEngine;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Exact direct-D3D11 transport for the captured Endminf M27 HGBuffer draw.
    /// It preserves the retail shader's separate VS/PS constant-buffer and SRV
    /// namespaces, which Unity's shared material shell cannot represent.
    /// </summary>
    public static class EndfieldRecoveredEndminfM27ExactRuntime
    {
        public const string EnvironmentVariable =
            "ENDFIELD_RECOVERED_ENDMINF_M27_EXACT_DXBC";
        private const string NativeLibrary = "OriginalDxbcSwapPlugin";

        private static bool prepared;
        private static bool failed;
        private static string failure = string.Empty;
        private static IntPtr renderEvent;
        private static bool submissionPending;
        private static bool loggedActivation;
        private static bool loggedValidation;
        private static bool loggedFailure;
        private static int selectedPacket = -1;
        private static float overviewEpoch = float.NaN;

        public static bool Requested => string.Equals(
            Environment.GetEnvironmentVariable(EnvironmentVariable),
            "1",
            StringComparison.Ordinal);

        public static bool HasPendingValidation => submissionPending;
        internal static bool Initialized => prepared && !failed;
        internal static bool HasActivePacket => Initialized && selectedPacket >= 0;
        public static string Failure => failure;

        internal static bool Prepare(
            Material sourceMaterial,
            Camera camera)
        {
            if (!Requested || failed)
                return false;
            if (SystemInfo.graphicsDeviceType != GraphicsDeviceType.Direct3D11)
                return Fail("exact M27 transport requires Direct3D11");
            if (!prepared && sourceMaterial == null)
                return Fail("the retained M27 source material is absent");
            if (!prepared)
            {
                try
                {
                    renderEvent = Native.GetM27RenderEventFunc();
                    if (renderEvent == IntPtr.Zero)
                        return Fail("the native M27 render event is unavailable");
                    Native.ResetM27RuntimeState();
                    if (Native.GetM27PacketCount() !=
                        EndfieldRecoveredM27TemporalCaptureData.PacketCount)
                    {
                        return Fail(
                            "native M27 packet count does not match generated data");
                    }
                    selectedPacket = -1;
                    overviewEpoch = float.NaN;
                    prepared = true;
                }
                catch (Exception exception)
                {
                    return Fail(
                        "the native M27 transport could not initialize: " +
                        exception.Message);
                }
            }

            EndfieldHGOperatorLightRig lightRig = camera != null
                ? camera.GetComponent<EndfieldHGOperatorLightRig>()
                : null;
            Transform actorRoot = lightRig != null ? lightRig.actorRoot : null;
            if (actorRoot == null || !string.Equals(
                    actorRoot.name,
                    "Endminf",
                    StringComparison.OrdinalIgnoreCase))
                return Fail("the camera has no selected Endminf actor clock");
            selectedPacket = ResolvePacket(actorRoot);
            if (selectedPacket < 0)
            {
                // The source ParticleSystem becomes live shortly before the
                // first retained packet and can outlive the final packet.
                // Those bounded intervals have no captured M27 draw. Keep the
                // five-target owner valid but submit no native event; a later
                // frame may enter the retained packet envelope.
                return true;
            }
            try
            {
                if (Native.SetM27PacketIndex((uint)selectedPacket) != 1)
                    return Fail("the native M27 packet selector rejected the phase");
            }
            catch (Exception exception)
            {
                return Fail("the native M27 packet could not bind: " +
                    exception.Message);
            }
            return true;
        }

        private static int ResolvePacket(Transform actorRoot)
        {
            float seconds;
            if (!float.IsNaN(overviewEpoch))
            {
                seconds = Mathf.Max(0.0f, Time.time - overviewEpoch);
            }
            else
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
                        return -1;
                    AnimatorStateInfo info = animator.GetCurrentAnimatorStateInfo(0);
                    seconds = info.normalizedTime * clips[0].clip.length;
                    overviewEpoch = Time.time - seconds;
                    return ResolveNearestPacket(seconds);
                }
                Animation animation = actorRoot != null
                    ? actorRoot.GetComponentInChildren<Animation>(true)
                    : null;
                AnimationState state = animation != null
                    ? animation["ui_overview_start"]
                    : null;
                if (state == null || !state.enabled)
                    return -1;
                seconds = state.time;
                overviewEpoch = Time.time - seconds;
            }
            return ResolveNearestPacket(seconds);
        }

        private static int ResolveNearestPacket(float seconds)
        {
            float[] phases = EndfieldRecoveredM27TemporalCaptureData.PhaseSeconds;
            float leadingHalfInterval = (phases[1] - phases[0]) * 0.5f;
            float trailingHalfInterval =
                (phases[phases.Length - 1] - phases[phases.Length - 2]) * 0.5f;
            if (seconds < phases[0] - leadingHalfInterval ||
                seconds > phases[phases.Length - 1] + trailingHalfInterval)
                return -1;
            int nearest = 0;
            float distance = Mathf.Abs(seconds - phases[0]);
            for (int index = 1; index < phases.Length; ++index)
            {
                float candidate = Mathf.Abs(seconds - phases[index]);
                if (candidate < distance)
                {
                    distance = candidate;
                    nearest = index;
                }
            }
            return nearest;
        }

        internal static bool Issue(CommandBuffer command)
        {
            if (!Requested || failed || !prepared || renderEvent == IntPtr.Zero)
                return false;
            if (selectedPacket < 0)
                return true;
            command.IssuePluginEvent(renderEvent, 0);
            submissionPending = true;
            if (!loggedActivation)
            {
                Debug.Log(
                    "Recovered exact Endminf M27 native HGBuffer draw submitted: " +
                    "16 phase packets, five MRTs, capture 20260826T162514Z.");
                loggedActivation = true;
            }
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
                uint draws = Native.GetM27DrawCount();
                uint failures = Native.GetM27DrawFailureCount();
                int result = Native.GetM27DrawLastResult();
                uint stage = Native.GetM27DrawFailureStage();
                if (draws == 0 || failures != 0 || result < 0)
                {
                    validationFailure = "native M27 result drifted: draws=" +
                        draws + ", failures=" + failures + ", hresult=0x" +
                        unchecked((uint)result).ToString("x8") +
                        ", stage=" + stage;
                    return Fail(validationFailure);
                }
                if (!loggedValidation)
                {
                    Debug.Log(
                        "Recovered exact Endminf M27 native draw validated: " +
                        "draw count is nonzero and the callback reported S_OK.");
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
            failure = reason ?? "unknown exact M27 failure";
            if (!loggedFailure)
            {
                Debug.LogWarning(
                    "Recovered exact Endminf M27 failed closed: " + failure + ".");
                loggedFailure = true;
            }
            return false;
        }

        private static class Native
        {
            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM27RenderEventFunc")]
            internal static extern IntPtr GetM27RenderEventFunc();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcSetM27PacketIndex")]
            internal static extern uint SetM27PacketIndex(uint packetIndex);

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM27PacketCount")]
            internal static extern uint GetM27PacketCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcResetM27RuntimeState")]
            internal static extern void ResetM27RuntimeState();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM27DrawCount")]
            internal static extern uint GetM27DrawCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM27DrawFailureCount")]
            internal static extern uint GetM27DrawFailureCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM27DrawLastResult")]
            internal static extern int GetM27DrawLastResult();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM27DrawFailureStage")]
            internal static extern uint GetM27DrawFailureStage();
        }
    }
}
