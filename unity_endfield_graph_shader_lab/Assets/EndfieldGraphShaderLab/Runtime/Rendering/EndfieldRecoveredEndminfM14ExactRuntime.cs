using System;
using System.Runtime.InteropServices;
using UnityEngine;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Default-off exact checkpoint transport for the captured Endminf M14
    /// VFXBaseV2 draw. The native event is required because retail reuses
    /// b0-b3 for different vertex and pixel payloads.
    /// </summary>
    internal static class EndfieldRecoveredEndminfM14ExactRuntime
    {
        internal const string EnvironmentVariable =
            "ENDFIELD_RECOVERED_ENDMINF_M14_EXACT";
        private const string NativeLibrary = "OriginalDxbcSwapPlugin";
        private const string MaterialName = "M_fx_endminm_gfx_14";
        private static readonly int ReadyId = Shader.PropertyToID(
            "_EndfieldRecoveredEndminfM14ExactReady");

        private static Texture mainTexture;
        private static bool prepared;
        private static bool failed;
        private static string failure = string.Empty;
        private static bool loggedActivation;
        private static bool loggedFailure;
        private static IntPtr renderEvent;
        private static bool suppressDrawForCapture;
        private static ParticleSystemRenderer selectedRenderer;
        private static int selectedPacket = -1;
        private static float overviewEpoch = float.NaN;

        internal static bool Requested => string.Equals(
            System.Environment.GetEnvironmentVariable(EnvironmentVariable),
            "1",
            StringComparison.Ordinal);

        internal static string Failure => failure;

        internal static bool PrepareBeforeCulling(Camera camera)
        {
            Shader.SetGlobalFloat(ReadyId, 0.0f);
            if (!Requested)
                return false;
            if (failed)
                return false;
            if (SystemInfo.graphicsDeviceType != GraphicsDeviceType.Direct3D11)
                return Fail("exact M14 transport requires Direct3D11");
            if (camera == null ||
                camera.GetComponent<EndfieldHGOperatorPresentation>() == null)
            {
                return false;
            }
            EndfieldHGOperatorLightRig lightRig =
                camera.GetComponent<EndfieldHGOperatorLightRig>();
            if (lightRig == null || lightRig.actorRoot == null ||
                !string.Equals(
                    lightRig.actorRoot.name,
                    "Endminf",
                    StringComparison.OrdinalIgnoreCase))
            {
                return false;
            }
            if (!prepared)
            {
                ParticleSystemRenderer[] renderers =
                    UnityEngine.Object.FindObjectsOfType<ParticleSystemRenderer>(true);
                foreach (ParticleSystemRenderer renderer in renderers)
                {
                    if (renderer == null || !renderer.gameObject.scene.IsValid())
                        continue;
                    Material material = renderer.sharedMaterial;
                    if (material == null || material.name != MaterialName)
                        continue;
                    if (selectedRenderer != null)
                        return Fail("multiple live M14 particle renderers were found");
                    selectedRenderer = renderer;
                    mainTexture = material.GetTexture("_MainTex");
                }
                if (selectedRenderer == null)
                    return Fail("the live M14 particle renderer is absent");
                if (mainTexture == null)
                    return Fail("the exact M14 native-mip texture is absent");

                try
                {
                    renderEvent = Native.GetM14RenderEventFunc();
                    if (renderEvent == IntPtr.Zero)
                        return Fail("the native M14 render event is unavailable");
                    if (Native.GetM14PacketCount() !=
                        EndfieldRecoveredM14ExactCaptureData.PacketCount)
                    {
                        return Fail("native M14 packet count does not match generated data");
                    }
                    Native.ResetM14RuntimeState();
                }
                catch (Exception exception)
                {
                    return Fail("the native M14 transport could not initialize: " +
                        exception.Message);
                }

                suppressDrawForCapture = string.Equals(
                    System.Environment.GetEnvironmentVariable(
                        "ENDFIELD_ENDMINF_CAPTURE_EXCLUDE_MATERIAL"),
                    MaterialName,
                    StringComparison.Ordinal);
                prepared = true;
            }

            selectedPacket = ResolvePacket(lightRig.actorRoot);
            bool packetActive = selectedPacket >= 0;
            if (selectedRenderer != null)
                selectedRenderer.enabled = !packetActive;
            if (!packetActive)
                return false;
            try
            {
                if (Native.SetM14PacketIndex((uint)selectedPacket) != 1)
                    return Fail("native M14 packet selector rejected the phase");
            }
            catch (Exception exception)
            {
                return Fail("native M14 packet selection failed: " + exception.Message);
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
            float[] phases = EndfieldRecoveredM14ExactCaptureData.PhaseSeconds;
            if (seconds < phases[0] - 0.125f ||
                seconds > phases[phases.Length - 1] + 0.125f)
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

        internal static bool Render(
            ScriptableRenderContext context,
            Camera camera,
            EndfieldRecoveredSceneColorHandle sceneColor,
            RenderTexture sceneMV,
            RenderTexture sceneDepth)
        {
            Shader.SetGlobalFloat(ReadyId, 0.0f);
            if (!Requested || failed || !prepared)
                return false;
            if (camera == null || sceneMV == null || sceneDepth == null ||
                mainTexture == null || renderEvent == IntPtr.Zero)
            {
                return Fail("the exact M14 render resources are incomplete");
            }
            if (suppressDrawForCapture)
            {
                Shader.SetGlobalFloat(ReadyId, 1.0f);
                return true;
            }
            IntPtr depthPointer = sceneDepth.GetNativeTexturePtr();
            IntPtr mainPointer = mainTexture.GetNativeTexturePtr();
            if (depthPointer == IntPtr.Zero || mainPointer == IntPtr.Zero)
                return Fail("the exact M14 D3D11 texture pointers are null");
            try
            {
                if (Native.SetM14TextureResources(depthPointer, mainPointer) != 1)
                    return Fail("the native M14 texture gate rejected its inputs");
            }
            catch (Exception exception)
            {
                return Fail("the native M14 texture gate failed: " +
                    exception.Message);
            }

            var command = new CommandBuffer
            {
                name = "Recovered exact Endminf M14 SceneColor/SceneMV draw"
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

            Shader.SetGlobalFloat(ReadyId, 1.0f);
            if (!loggedActivation)
            {
                Debug.Log(
                    "Recovered exact Endminf M14 native draw submitted: " +
                    "7 phase packets, SceneColor/SceneMV, capture 20260826T091023Z.");
                loggedActivation = true;
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
                uint draws = Native.GetM14DrawCount();
                uint failures = Native.GetM14FailureCount();
                int result = Native.GetM14LastResult();
                if (draws == 0 || failures != 0 || result < 0)
                {
                    validationFailure = "native M14 result drifted: draws=" +
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
            failure = reason ?? "unknown exact M14 failure";
            if (selectedRenderer != null)
                selectedRenderer.enabled = true;
            Shader.SetGlobalFloat(ReadyId, 0.0f);
            if (!loggedFailure)
            {
                Debug.LogWarning(
                    "Recovered exact Endminf M14 failed closed: " + failure + ".");
                loggedFailure = true;
            }
            return false;
        }

        private static class Native
        {
            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM14RenderEventFunc")]
            internal static extern IntPtr GetM14RenderEventFunc();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcSetM14TextureResources")]
            internal static extern uint SetM14TextureResources(
                IntPtr sceneDepth,
                IntPtr mainTexture);

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcSetM14PacketIndex")]
            internal static extern uint SetM14PacketIndex(uint packetIndex);

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM14PacketCount")]
            internal static extern uint GetM14PacketCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcResetM14RuntimeState")]
            internal static extern void ResetM14RuntimeState();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM14DrawCount")]
            internal static extern uint GetM14DrawCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM14FailureCount")]
            internal static extern uint GetM14FailureCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM14LastResult")]
            internal static extern int GetM14LastResult();
        }
    }
}
