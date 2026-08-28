using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using UnityEngine;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Default-off exact two-draw M31 shell checkpoint captured at clean
    /// reference frame 264 (body phase 4.35 seconds).
    /// </summary>
    public static class EndfieldRecoveredEndminfM31PeakExactRuntime
    {
        internal const string EnvironmentVariable =
            "ENDFIELD_RECOVERED_ENDMINF_M31_PEAK_EXACT";
        private const string NativeLibrary = "OriginalDxbcSwapPlugin";
        private const string MaterialName = "M_fx_endminm_gfx_31";
        private const float ViewerLeadSeconds = 2.0f / 60.0f;
        // Viewer capture advances the body Animator by two 60-Hz ticks before
        // the requested presentation timestamp. Admit that measured lead while
        // keeping this single-frame packet outside the neighboring 0.1 s bins.
        private const float HalfWindowSeconds = 0.05f;

        private static readonly List<ParticleSystemRenderer> Renderers =
            new List<ParticleSystemRenderer>();
        private static IntPtr renderEvent;
        private static bool prepared;
        private static bool failed;
        private static bool active;
        private static bool submissionPending;
        private static string failure = string.Empty;
        private static bool loggedActivation;
        private static bool loggedValidation;
        private static bool loggedFailure;
        private static bool loggedAdmission;
        private static bool loggedMissingRenderers;

        public static bool Requested => string.Equals(
            System.Environment.GetEnvironmentVariable(EnvironmentVariable),
            "1", StringComparison.Ordinal);

        internal static string Failure => failure;
        public static bool HasPendingValidation => submissionPending;

        internal static bool PrepareBeforeCulling(Camera camera)
        {
            active = false;
            if (!Requested || failed || camera == null)
                return false;
            if (SystemInfo.graphicsDeviceType != GraphicsDeviceType.Direct3D11)
                return Fail("exact M31 peak transport requires Direct3D11");
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
                seconds - EndfieldRecoveredM31PeakCaptureData.PhaseSeconds) <=
                HalfWindowSeconds;
            if (!loggedAdmission)
            {
                Debug.Log("Recovered exact Endminf M31 peak admission: " +
                    "renderers=" + Renderers.Count + ", phase=" +
                    seconds.ToString("F6") + ", target=" +
                    EndfieldRecoveredM31PeakCaptureData.PhaseSeconds.ToString("F6") +
                    ", active=" + active + ".");
                loggedAdmission = true;
            }
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
            {
                if (!loggedMissingRenderers)
                {
                    Debug.Log("Recovered exact Endminf M31 peak is waiting for " +
                        "runtime-spawned M_fx_endminm_gfx_31 renderers.");
                    loggedMissingRenderers = true;
                }
                return false;
            }
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
                float seconds = animator.GetCurrentAnimatorStateInfo(0)
                    .normalizedTime * clips[0].clip.length;
                return Mathf.Max(0.0f, seconds - ViewerLeadSeconds);
            }
            Animation animation = actorRoot != null
                ? actorRoot.GetComponentInChildren<Animation>(true)
                : null;
            AnimationState state = animation != null
                ? animation["ui_overview_start"] : null;
            if (state == null || !state.enabled)
                return float.NaN;
            return Mathf.Max(0.0f, state.time - ViewerLeadSeconds);
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
                name = "Recovered exact Endminf M31 peak SceneColor/SceneMV draws"
            };
            command.SetRenderTarget(
                new[] { sceneColor.Target, new RenderTargetIdentifier(sceneMV) },
                new RenderTargetIdentifier(BuiltinRenderTextureType.None));
            command.IssuePluginEvent(renderEvent, 0);
            context.ExecuteCommandBuffer(command);
            command.Release();
            submissionPending = true;
            if (!loggedActivation)
            {
                Debug.Log(
                    "Recovered exact Endminf M31 peak submitted: two retail " +
                    "SceneColor/SceneMV draws from capture " +
                    EndfieldRecoveredM31PeakCaptureData.SourceSession +
                    " frame " + EndfieldRecoveredM31PeakCaptureData.SourceFrame + ".");
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
                if (draws < EndfieldRecoveredM31PeakCaptureData.DrawCount ||
                    failures != 0 || result < 0)
                {
                    validationFailure = "native M31 peak result drifted: draws=" +
                        draws + ", failures=" + failures + ", hresult=0x" +
                        unchecked((uint)result).ToString("x8");
                    return Fail(validationFailure);
                }
                if (!loggedValidation)
                {
                    Debug.Log("Recovered exact Endminf M31 peak validated: " +
                        "both captured draws completed with S_OK.");
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
            failure = reason ?? "unknown exact M31 peak failure";
            foreach (ParticleSystemRenderer renderer in Renderers)
                if (renderer != null) renderer.enabled = true;
            if (!loggedFailure)
            {
                Debug.LogWarning("Recovered exact Endminf M31 peak failed closed: " +
                    failure + ".");
                loggedFailure = true;
            }
            return false;
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
