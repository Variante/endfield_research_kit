using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using UnityEngine;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Default-off exact temporal transport for the captured Endminf M29
    /// SceneColor/SceneMV particle sequence.
    /// </summary>
    public static class EndfieldRecoveredEndminfM29ExactRuntime
    {
        internal const string EnvironmentVariable =
            "ENDFIELD_RECOVERED_ENDMINF_M29_EXACT";
        private const string NativeLibrary = "OriginalDxbcSwapPlugin";
        private const string MaterialName = "M_fx_endminm_gfx_29";

        // The focused viewer presents the body Animator two 60-Hz ticks ahead
        // of its requested timestamp. Normalize its authoritative phase before
        // selecting the nearest captured packet.
        private const float ViewerLeadSeconds = 2.0f / 60.0f;

        private static readonly List<ParticleSystemRenderer> Renderers =
            new List<ParticleSystemRenderer>();
        private static IntPtr renderEvent;
        private static bool prepared;
        private static bool failed;
        private static bool active;
        private static bool submissionPending;
        private static string failure = string.Empty;
        private static int selectedPacket = -1;
        private static uint validatedDrawCount;
        private static bool loggedActivation;
        private static bool loggedValidation;
        private static bool loggedFailure;
        private static bool loggedMissingRenderers;

        public static bool Requested => string.Equals(
            System.Environment.GetEnvironmentVariable(EnvironmentVariable),
            "1", StringComparison.Ordinal);

        internal static string Failure => failure;
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
                return Fail("exact M29 transport requires Direct3D11");
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

            selectedPacket = ResolvePacket(lightRig.actorRoot);
            active = selectedPacket >= 0;
            SetRendererSuppression(active);
            if (!active)
                return false;

            try
            {
                if (Native.SetPacketIndex((uint)selectedPacket) != 1)
                    return Fail("the native M29 packet selector rejected the phase");
            }
            catch (Exception exception)
            {
                return Fail("native M29 packet selection failed: " +
                    exception.Message);
            }
            return true;
        }

        private static bool PrepareNative()
        {
            if (!EndfieldRecoveredM29ExactCaptureData.GeometryContractReady)
            {
                return Fail(
                    "captured M29 draw-local IA offsets are unavailable; " +
                    "the shared-ring geometry payload is not replay-safe");
            }
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
                    Debug.Log("Recovered exact Endminf M29 is waiting for " +
                        "runtime-spawned M_fx_endminm_gfx_29 renderers.");
                    loggedMissingRenderers = true;
                }
                return false;
            }

            float[] phases = EndfieldRecoveredM29ExactCaptureData.PacketPhases;
            if (phases == null || phases.Length !=
                    EndfieldRecoveredM29ExactCaptureData.PacketCount ||
                phases.Length < 2)
            {
                return Fail("the generated M29 temporal contract is incomplete");
            }
            for (int index = 1; index < phases.Length; ++index)
            {
                if (phases[index] <= phases[index - 1])
                    return Fail("the generated M29 packet phases are not increasing");
            }

            try
            {
                renderEvent = Native.GetRenderEventFunc();
                if (renderEvent == IntPtr.Zero)
                    return Fail("the native M29 render event is unavailable");
                if (Native.GetPacketCount() !=
                    EndfieldRecoveredM29ExactCaptureData.PacketCount)
                {
                    return Fail(
                        "native M29 packet count does not match generated data");
                }
                Native.ResetRuntimeState();
            }
            catch (Exception exception)
            {
                return Fail("the native M29 transport could not initialize: " +
                    exception.Message);
            }

            validatedDrawCount = 0;
            prepared = true;
            return true;
        }

        private static int ResolvePacket(Transform actorRoot)
        {
            float seconds = ResolveOverviewStartSeconds(actorRoot);
            if (float.IsNaN(seconds))
                return -1;
            return ResolveNearestPacket(Mathf.Max(0.0f,
                seconds - ViewerLeadSeconds));
        }

        private static float ResolveOverviewStartSeconds(Transform actorRoot)
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
                {
                    return float.NaN;
                }
                return animator.GetCurrentAnimatorStateInfo(0).normalizedTime *
                    clips[0].clip.length;
            }

            Animation animation = actorRoot != null
                ? actorRoot.GetComponentInChildren<Animation>(true)
                : null;
            AnimationState state = animation != null
                ? animation["ui_overview_start"]
                : null;
            if (state == null || !state.enabled)
                return float.NaN;
            return state.time;
        }

        private static int ResolveNearestPacket(float seconds)
        {
            float[] phases = EndfieldRecoveredM29ExactCaptureData.PacketPhases;
            float leadingHalfSpacing = (phases[1] - phases[0]) * 0.5f;
            float trailingHalfSpacing =
                (phases[phases.Length - 1] - phases[phases.Length - 2]) * 0.5f;
            if (seconds < phases[0] - leadingHalfSpacing ||
                seconds > phases[phases.Length - 1] + trailingHalfSpacing)
            {
                return -1;
            }

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

        internal static bool Render(
            ScriptableRenderContext context,
            Camera camera,
            EndfieldRecoveredSceneColorHandle sceneColor,
            RenderTexture sceneMV,
            RenderTexture sceneDepth)
        {
            if (!Requested || failed || !prepared || !active ||
                selectedPacket < 0)
            {
                return false;
            }
            if (camera == null || sceneMV == null || sceneDepth == null ||
                renderEvent == IntPtr.Zero)
            {
                return Fail("the exact M29 render resources are incomplete");
            }

            IntPtr depthPointer = sceneDepth.GetNativeTexturePtr();
            if (depthPointer == IntPtr.Zero)
                return Fail("the exact M29 depth pointer is null");
            try
            {
                if (Native.SetDepthResource(depthPointer) != 1)
                    return Fail("the native M29 depth gate rejected its input");
            }
            catch (Exception exception)
            {
                return Fail("the native M29 depth gate failed: " +
                    exception.Message);
            }

            var command = new CommandBuffer
            {
                name = "Recovered exact Endminf M29 SceneColor/SceneMV draw"
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

            if (!loggedActivation)
            {
                Debug.Log("Recovered exact Endminf M29 submitted: " +
                    EndfieldRecoveredM29ExactCaptureData.PacketCount +
                    " temporal SceneColor/SceneMV packets.");
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
                uint submittedDraws = draws >= validatedDrawCount
                    ? draws - validatedDrawCount
                    : uint.MaxValue;
                if (submittedDraws != 1 || failures != 0 || result < 0)
                {
                    validationFailure = "native M29 result drifted: draws=" +
                        draws + ", failures=" + failures + ", hresult=0x" +
                        unchecked((uint)result).ToString("x8") +
                        ", previousValidatedDraws=" + validatedDrawCount +
                        ", submittedDraws=" + submittedDraws;
                    return Fail(validationFailure);
                }
                validatedDrawCount = draws;
                if (!loggedValidation)
                {
                    Debug.Log("Recovered exact Endminf M29 validated: " +
                        "the synchronized packet draw completed with S_OK.");
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

        private static void SetRendererSuppression(bool suppress)
        {
            foreach (ParticleSystemRenderer renderer in Renderers)
            {
                if (renderer != null)
                    renderer.enabled = !suppress;
            }
        }

        private static void RestoreRenderers()
        {
            SetRendererSuppression(false);
        }

        private static bool Fail(string reason)
        {
            failed = true;
            active = false;
            selectedPacket = -1;
            failure = reason ?? "unknown exact M29 failure";
            RestoreRenderers();
            if (!loggedFailure)
            {
                Debug.LogWarning("Recovered exact Endminf M29 failed closed: " +
                    failure + ".");
                loggedFailure = true;
            }
            return false;
        }

        private static class Native
        {
            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM29RenderEventFunc")]
            internal static extern IntPtr GetRenderEventFunc();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcSetM29DepthResource")]
            internal static extern uint SetDepthResource(IntPtr sceneDepth);

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcSetM29PacketIndex")]
            internal static extern uint SetPacketIndex(uint packetIndex);

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcResetM29RuntimeState")]
            internal static extern void ResetRuntimeState();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM29PacketCount")]
            internal static extern uint GetPacketCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM29DrawCount")]
            internal static extern uint GetDrawCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM29FailureCount")]
            internal static extern uint GetFailureCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM29LastResult")]
            internal static extern int GetLastResult();
        }
    }
}
