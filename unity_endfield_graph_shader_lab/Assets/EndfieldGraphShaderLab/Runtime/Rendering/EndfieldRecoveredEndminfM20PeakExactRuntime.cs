using System;
using System.Runtime.InteropServices;
using UnityEngine;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>Default-off exact retail M20 gas plume from capture frame 1748.</summary>
    public static class EndfieldRecoveredEndminfM20PeakExactRuntime
    {
        internal const string EnvironmentVariable =
            "ENDFIELD_RECOVERED_ENDMINF_M20_PEAK_EXACT";
        private const string NativeLibrary = "OriginalDxbcSwapPlugin";
        private const string MaterialName = "M_fx_endminm_gfx_20";
        private const float ViewerLeadSeconds = 2.0f / 60.0f;
        private const float HalfWindowSeconds = 1.0f / 120.0f;
        private static IntPtr renderEvent;
        private static ParticleSystemRenderer selectedRenderer;
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
        public static bool ActiveThisFrame => active;
        public static bool SubmittedThisFrame => submittedThisFrame;
        public static bool ValidatedThisFrame => validatedThisFrame;
        public static bool HasPendingValidation => submissionPending;

        internal static bool PrepareBeforeCulling(Camera camera)
        {
            active = false;
            submittedThisFrame = false;
            validatedThisFrame = false;
            if (!Requested || failed || camera == null)
                return false;
            if (SystemInfo.graphicsDeviceType != GraphicsDeviceType.Direct3D11)
                return Fail("exact M20 peak transport requires Direct3D11");
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
                seconds - EndfieldRecoveredM20PeakCaptureData.PhaseSeconds) <=
                HalfWindowSeconds;
            if (selectedRenderer != null)
                selectedRenderer.enabled = !active;
            return active;
        }

        private static bool PrepareNative()
        {
            selectedRenderer = null;
            foreach (ParticleSystemRenderer renderer in
                     UnityEngine.Object.FindObjectsOfType<ParticleSystemRenderer>(true))
            {
                if (renderer == null || !renderer.gameObject.scene.IsValid() ||
                    !string.Equals(renderer.name, "smoke (2)", StringComparison.Ordinal) ||
                    renderer.transform.parent == null ||
                    !string.Equals(renderer.transform.parent.name, "all",
                        StringComparison.Ordinal))
                    continue;
                Material material = renderer.sharedMaterial;
                if (material == null || !string.Equals(
                        material.name, MaterialName, StringComparison.Ordinal))
                    continue;
                if (selectedRenderer != null)
                    return Fail("the source-identified M20 smoke owner is not unique");
                selectedRenderer = renderer;
            }
            if (selectedRenderer == null)
                return false;
            try
            {
                renderEvent = Native.GetRenderEventFunc();
                if (renderEvent == IntPtr.Zero)
                    return Fail("the native M20 peak event is unavailable");
                Native.ResetRuntimeState();
            }
            catch (Exception exception)
            {
                return Fail("the native M20 peak transport could not initialize: " +
                    exception.Message);
            }
            prepared = true;
            return true;
        }

        internal static bool Render(
            ScriptableRenderContext context,
            Camera camera,
            EndfieldRecoveredSceneColorHandle sceneColor,
            RenderTexture sceneMV,
            RenderTexture sceneDepth)
        {
            if (!Requested || failed || !prepared || !active)
                return false;
            if (camera == null || sceneMV == null || sceneDepth == null ||
                renderEvent == IntPtr.Zero)
                return Fail("the exact M20 peak render resources are incomplete");
            IntPtr depthPointer = sceneDepth.GetNativeTexturePtr();
            if (depthPointer == IntPtr.Zero)
                return Fail("the exact M20 scene-depth pointer is null");
            try
            {
                if (Native.SetDepthResource(depthPointer) != 1)
                    return Fail("the native M20 depth gate rejected its input");
            }
            catch (Exception exception)
            {
                return Fail("the native M20 depth gate failed: " + exception.Message);
            }
            var command = new CommandBuffer
            {
                name = "Recovered exact retail Endminf M20 gas plume"
            };
            command.SetRenderTarget(
                new[] {
                    sceneColor.Target,
                    new RenderTargetIdentifier(sceneMV),
                },
                new RenderTargetIdentifier(sceneDepth));
            command.IssuePluginEvent(renderEvent, 0);
            context.ExecuteCommandBuffer(command);
            command.Release();
            submissionPending = true;
            submittedThisFrame = true;
            if (!loggedActivation)
            {
                Debug.Log("Recovered exact retail Endminf M20 draw submitted from " +
                    EndfieldRecoveredM20PeakCaptureData.SourceSession + " frame " +
                    EndfieldRecoveredM20PeakCaptureData.SourceFrame + ".");
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
                if (draws == 0 || failures != 0 || result < 0)
                {
                    validationFailure = "native M20 result drifted: draws=" + draws +
                        ", failures=" + failures + ", hresult=0x" +
                        unchecked((uint)result).ToString("x8");
                    return Fail(validationFailure);
                }
                validatedThisFrame = true;
                if (!loggedValidation)
                {
                    Debug.Log("Recovered exact retail Endminf M20 draw validated.");
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

        private static float ResolveOverviewSeconds(Transform actorRoot)
        {
            EndfieldOverviewPlayback playback =
                actorRoot.GetComponentInChildren<EndfieldOverviewPlayback>(true);
            Animator animator = playback != null ? playback.animatorSource : null;
            if (playback != null && playback.AnimatorContractActive &&
                animator != null && animator.enabled)
            {
                AnimatorClipInfo[] clips = animator.GetCurrentAnimatorClipInfo(0);
                if (clips.Length == 0 || clips[0].clip == null ||
                    clips[0].clip.name.IndexOf("overview_start",
                        StringComparison.OrdinalIgnoreCase) < 0)
                    return float.NaN;
                return Mathf.Max(0.0f,
                    animator.GetCurrentAnimatorStateInfo(0).normalizedTime *
                    clips[0].clip.length - ViewerLeadSeconds);
            }
            Animation animation =
                actorRoot.GetComponentInChildren<Animation>(true);
            AnimationState state = animation != null
                ? animation["ui_overview_start"] : null;
            return state != null && state.enabled
                ? Mathf.Max(0.0f, state.time - ViewerLeadSeconds)
                : float.NaN;
        }

        private static bool Fail(string reason)
        {
            failed = true;
            failure = reason ?? "unknown exact M20 failure";
            if (selectedRenderer != null)
                selectedRenderer.enabled = true;
            if (!loggedFailure)
            {
                Debug.LogWarning("Recovered exact Endminf M20 failed closed: " +
                    failure + ".");
                loggedFailure = true;
            }
            return false;
        }

        private static class Native
        {
            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM20PeakRenderEventFunc")]
            internal static extern IntPtr GetRenderEventFunc();
            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcSetM20PeakDepthResource")]
            internal static extern uint SetDepthResource(IntPtr sceneDepth);
            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcResetM20PeakRuntimeState")]
            internal static extern void ResetRuntimeState();
            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM20PeakDrawCount")]
            internal static extern uint GetDrawCount();
            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM20PeakFailureCount")]
            internal static extern uint GetFailureCount();
            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM20PeakLastResult")]
            internal static extern int GetLastResult();
        }
    }
}
