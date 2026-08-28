using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using UnityEngine;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>Default-off exact M21 stone-shell draw from Full frame 2775.</summary>
    public static class EndfieldRecoveredEndminfM21PeakExactRuntime
    {
        internal const string EnvironmentVariable =
            "ENDFIELD_RECOVERED_ENDMINF_M21_PEAK_EXACT";
        private const string NativeLibrary = "OriginalDxbcSwapPlugin";
        private const string MaterialName = "M_fx_endminm_gfx_21";
        private const float ViewerLeadSeconds = 2.0f / 60.0f;
        // Full frame 2775 supplies one authoritative 60 Hz packet, not a
        // reusable multi-frame animation. Admit only the nearest simulation
        // sample; adjacent ticks must fall back to the authored renderer.
        private const float HalfWindowSeconds = 1.0f / 120.0f;
        private static readonly List<ParticleSystemRenderer> Renderers =
            new List<ParticleSystemRenderer>();
        private static IntPtr renderEvent;
        private static bool prepared;
        private static bool failed;
        private static bool active;
        private static bool submissionPending;
        private static bool submittedThisFrame;
        private static bool validatedThisFrame;
        private static string failure = string.Empty;
        private static bool loggedActivation;
        private static bool loggedValidation;
        private static bool loggedFailure;

        public static bool Requested => string.Equals(
            Environment.GetEnvironmentVariable(EnvironmentVariable),
            "1", StringComparison.Ordinal);
        public static string Failure => failure;
        public static bool HasPendingValidation => submissionPending;
        public static bool ActiveThisFrame => active;
        public static bool SubmittedThisFrame => submittedThisFrame;
        public static bool ValidatedThisFrame => validatedThisFrame;

        internal static bool PrepareBeforeCulling(Camera camera)
        {
            active = false;
            submittedThisFrame = false;
            validatedThisFrame = false;
            if (!Requested || failed || camera == null)
                return false;
            if (SystemInfo.graphicsDeviceType != GraphicsDeviceType.Direct3D11)
                return Fail("exact M21 peak transport requires Direct3D11");
            EndfieldHGOperatorLightRig lightRig =
                camera.GetComponent<EndfieldHGOperatorLightRig>();
            if (lightRig == null || lightRig.actorRoot == null ||
                !string.Equals(lightRig.actorRoot.name, "Endminf",
                    StringComparison.OrdinalIgnoreCase))
                return false;
            if (!prepared && !PrepareNative())
                return false;
            float seconds = ResolveOverviewSeconds(lightRig.actorRoot);
            active = !float.IsNaN(seconds) && Mathf.Abs(
                seconds - EndfieldRecoveredM21PeakCaptureData.PhaseSeconds) <=
                HalfWindowSeconds;
            foreach (ParticleSystemRenderer renderer in Renderers)
                if (renderer != null) renderer.enabled = !active;
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
                return false;
            try
            {
                renderEvent = Native.GetRenderEventFunc();
                if (renderEvent == IntPtr.Zero)
                    return Fail("the native M21 peak event is unavailable");
                Native.ResetRuntimeState();
            }
            catch (Exception exception)
            {
                return Fail("the native M21 peak transport could not initialize: " +
                    exception.Message);
            }
            prepared = true;
            return true;
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
                return Mathf.Max(0.0f,
                    animator.GetCurrentAnimatorStateInfo(0).normalizedTime *
                    clips[0].clip.length - ViewerLeadSeconds);
            }
            Animation animation = actorRoot != null
                ? actorRoot.GetComponentInChildren<Animation>(true)
                : null;
            AnimationState state = animation != null
                ? animation["ui_overview_start"] : null;
            return state != null && state.enabled
                ? Mathf.Max(0.0f, state.time - ViewerLeadSeconds)
                : float.NaN;
        }

        internal static bool Render(
            ScriptableRenderContext context,
            Camera camera,
            EndfieldRecoveredSceneColorHandle sceneColor,
            RenderTexture sceneDepth)
        {
            if (!Requested || failed || !prepared || !active)
                return false;
            if (camera == null || sceneDepth == null || renderEvent == IntPtr.Zero)
                return Fail("the exact M21 peak render resources are incomplete");
            var command = new CommandBuffer
            {
                name = "Recovered exact Endminf M21 stone-shell draw"
            };
            command.SetRenderTarget(
                sceneColor.Target,
                new RenderTargetIdentifier(sceneDepth));
            command.IssuePluginEvent(renderEvent, 0);
            context.ExecuteCommandBuffer(command);
            command.Release();
            submissionPending = true;
            submittedThisFrame = true;
            if (!loggedActivation)
            {
                Debug.Log("Recovered exact Endminf M21 stone shell submitted from " +
                    EndfieldRecoveredM21PeakCaptureData.SourceSession + " frame " +
                    EndfieldRecoveredM21PeakCaptureData.SourceFrame + ".");
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
                uint draws = Native.GetDrawCount();
                uint failures = Native.GetFailureCount();
                int result = Native.GetLastResult();
                if (draws < EndfieldRecoveredM21PeakCaptureData.DrawCount ||
                    failures != 0 || result < 0)
                {
                    validationFailure = "native M21 peak result drifted: draws=" +
                        draws + ", failures=" + failures + ", hresult=0x" +
                        unchecked((uint)result).ToString("x8");
                    return Fail(validationFailure);
                }
                if (!loggedValidation)
                {
                    Debug.Log("Recovered exact Endminf M21 stone shell validated S_OK.");
                    loggedValidation = true;
                }
                validatedThisFrame = true;
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
            failure = reason ?? "unknown exact M21 peak failure";
            foreach (ParticleSystemRenderer renderer in Renderers)
                if (renderer != null) renderer.enabled = true;
            if (!loggedFailure)
            {
                Debug.LogWarning("Recovered exact Endminf M21 peak failed closed: " +
                    failure + ".");
                loggedFailure = true;
            }
            return false;
        }

        private static class Native
        {
            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM21PeakRenderEventFunc")]
            internal static extern IntPtr GetRenderEventFunc();
            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcResetM21PeakRuntimeState")]
            internal static extern void ResetRuntimeState();
            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM21PeakDrawCount")]
            internal static extern uint GetDrawCount();
            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM21PeakFailureCount")]
            internal static extern uint GetFailureCount();
            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM21PeakLastResult")]
            internal static extern int GetLastResult();
        }
    }
}
