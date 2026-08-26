using System;
using System.Runtime.InteropServices;
using UnityEngine;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Default-off exact transport for the captured Endminf M13 huan billboard.
    /// Native D3D11 owns the stage-specific constants and five BC7 SRVs.
    /// </summary>
    public static class EndfieldRecoveredEndminfM13ExactRuntime
    {
        internal const string EnvironmentVariable =
            "ENDFIELD_RECOVERED_ENDMINF_M13_EXACT";
        private const string NativeLibrary = "OriginalDxbcSwapPlugin";
        private const string MaterialName = "M_fx_endminm_gfx_13";
        private static readonly int ReadyId = Shader.PropertyToID(
            "_EndfieldRecoveredEndminfM13ExactReady");

        private static bool prepared;
        private static bool failed;
        private static string failure = string.Empty;
        private static bool loggedActivation;
        private static bool loggedValidation;
        private static bool loggedFailure;
        private static bool suppressDrawForCapture;
        private static bool submissionPending;
        private static int submittedFrame = -1;
        private static IntPtr renderEvent;
        private static ParticleSystemRenderer selectedRenderer;
        private static float overviewEpoch = float.NaN;

        public static bool Requested => string.Equals(
            System.Environment.GetEnvironmentVariable(EnvironmentVariable),
            "1",
            StringComparison.Ordinal);

        internal static string Failure => failure;
        public static bool HasPendingValidation => submissionPending;

        internal static bool PrepareBeforeCulling(Camera camera)
        {
            Shader.SetGlobalFloat(ReadyId, 0.0f);
            if (!Requested || failed)
                return false;
            if (SystemInfo.graphicsDeviceType != GraphicsDeviceType.Direct3D11)
                return Fail("exact M13 transport requires Direct3D11");
            if (camera == null ||
                camera.GetComponent<EndfieldHGOperatorPresentation>() == null)
                return false;
            EndfieldHGOperatorLightRig lightRig =
                camera.GetComponent<EndfieldHGOperatorLightRig>();
            if (lightRig == null || lightRig.actorRoot == null ||
                !string.Equals(lightRig.actorRoot.name, "Endminf",
                    StringComparison.OrdinalIgnoreCase))
                return false;
            if (submissionPending && Time.frameCount > submittedFrame)
            {
                if (!ValidatePendingAfterSynchronizedRender(
                        out string validationFailure))
                    return false;
            }
            if (!prepared)
            {
                foreach (ParticleSystemRenderer renderer in
                    UnityEngine.Object.FindObjectsOfType<ParticleSystemRenderer>(true))
                {
                    if (renderer == null || !renderer.gameObject.scene.IsValid())
                        continue;
                    Material material = renderer.sharedMaterial;
                    if (material == null || material.name != MaterialName)
                        continue;
                    if (selectedRenderer != null)
                        return Fail("multiple live M13 particle renderers were found");
                    selectedRenderer = renderer;
                }
                if (selectedRenderer == null)
                    return Fail("the live M13 particle renderer is absent");
                try
                {
                    renderEvent = Native.GetM13RenderEventFunc();
                    if (renderEvent == IntPtr.Zero)
                        return Fail("the native M13 render event is unavailable");
                    Native.ResetM13RuntimeState();
                }
                catch (Exception exception)
                {
                    return Fail("the native M13 transport could not initialize: " +
                        exception.Message);
                }
                suppressDrawForCapture = string.Equals(
                    System.Environment.GetEnvironmentVariable(
                        "ENDFIELD_ENDMINF_CAPTURE_EXCLUDE_MATERIAL"),
                    MaterialName,
                    StringComparison.Ordinal);
                prepared = true;
            }

            bool active = ResolvePhase(lightRig.actorRoot);
            if (selectedRenderer != null)
                selectedRenderer.enabled = !active;
            return active;
        }

        private static bool ResolvePhase(Transform actorRoot)
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
                        return false;
                    AnimatorStateInfo info = animator.GetCurrentAnimatorStateInfo(0);
                    seconds = info.normalizedTime * clips[0].clip.length;
                    overviewEpoch = Time.time - seconds;
                }
                else
                {
                    Animation animation = actorRoot != null
                        ? actorRoot.GetComponentInChildren<Animation>(true)
                        : null;
                    AnimationState state = animation != null
                        ? animation["ui_overview_start"]
                        : null;
                    if (state == null || !state.enabled)
                        return false;
                    seconds = state.time;
                    overviewEpoch = Time.time - seconds;
                }
            }
            return Mathf.Abs(seconds -
                EndfieldRecoveredM13ExactCaptureData.PhaseSeconds) <=
                EndfieldRecoveredM13ExactCaptureData.ActiveHalfWidthSeconds;
        }

        internal static bool Render(
            ScriptableRenderContext context,
            Camera camera,
            EndfieldRecoveredSceneColorHandle sceneColor,
            RenderTexture sceneMV)
        {
            Shader.SetGlobalFloat(ReadyId, 0.0f);
            if (!Requested || failed || !prepared)
                return false;
            if (camera == null || sceneMV == null || renderEvent == IntPtr.Zero)
                return Fail("the exact M13 render resources are incomplete");
            if (suppressDrawForCapture)
            {
                Shader.SetGlobalFloat(ReadyId, 1.0f);
                return true;
            }
            var command = new CommandBuffer
            {
                name = "Recovered exact Endminf M13 SceneColor/SceneMV draw"
            };
            command.SetRenderTarget(
                new[]
                {
                    sceneColor.Target,
                    new RenderTargetIdentifier(sceneMV),
                },
                new RenderTargetIdentifier(BuiltinRenderTextureType.None));
            command.IssuePluginEvent(renderEvent, 0);
            context.ExecuteCommandBuffer(command);
            command.Release();
            submissionPending = true;
            submittedFrame = Time.frameCount;
            Shader.SetGlobalFloat(ReadyId, 1.0f);
            if (!loggedActivation)
            {
                Debug.Log(
                    "Recovered exact Endminf M13 native draw submitted: frame 5404, " +
                    "SceneColor/SceneMV, capture 20260826T144934Z.");
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
            if (!ValidateAfterSubmit(out validationFailure))
                return Fail(validationFailure);
            if (!loggedValidation)
            {
                Debug.Log(
                    "Recovered exact Endminf M13 native draw validated: " +
                    "draw count is nonzero and the callback reported S_OK.");
                loggedValidation = true;
            }
            return true;
        }

        internal static bool ValidateAfterSubmit(out string validationFailure)
        {
            validationFailure = string.Empty;
            if (!Requested || failed || !prepared)
            {
                validationFailure = failure;
                return false;
            }
            try
            {
                uint draws = Native.GetM13DrawCount();
                uint failures = Native.GetM13FailureCount();
                int result = Native.GetM13LastResult();
                if (draws == 0 || failures != 0 || result < 0)
                {
                    validationFailure = "native M13 result drifted: draws=" +
                        draws + ", failures=" + failures + ", hresult=0x" +
                        unchecked((uint)result).ToString("x8");
                    return false;
                }
                return true;
            }
            catch (Exception exception)
            {
                validationFailure = exception.Message;
                return false;
            }
        }

        private static bool Fail(string reason)
        {
            failed = true;
            failure = reason ?? "unknown exact M13 failure";
            if (selectedRenderer != null)
                selectedRenderer.enabled = true;
            Shader.SetGlobalFloat(ReadyId, 0.0f);
            if (!loggedFailure)
            {
                Debug.LogWarning(
                    "Recovered exact Endminf M13 failed closed: " + failure + ".");
                loggedFailure = true;
            }
            return false;
        }

        private static class Native
        {
            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM13RenderEventFunc")]
            internal static extern IntPtr GetM13RenderEventFunc();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcResetM13RuntimeState")]
            internal static extern void ResetM13RuntimeState();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM13DrawCount")]
            internal static extern uint GetM13DrawCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM13FailureCount")]
            internal static extern uint GetM13FailureCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM13LastResult")]
            internal static extern int GetM13LastResult();
        }
    }
}
