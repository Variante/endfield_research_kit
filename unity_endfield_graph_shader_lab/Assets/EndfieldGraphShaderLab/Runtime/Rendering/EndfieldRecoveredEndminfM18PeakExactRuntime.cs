using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using UnityEngine;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>Default-off exact M18 amber diffusion shell from Full frame 2775.</summary>
    public static class EndfieldRecoveredEndminfM18PeakExactRuntime
    {
        internal const string EnvironmentVariable =
            "ENDFIELD_RECOVERED_ENDMINF_M18_PEAK_EXACT";
        private const string NativeLibrary = "OriginalDxbcSwapPlugin";
        private const string MaterialName = "M_fx_endminm_gfx_18";
        private const float ViewerLeadSeconds = 2.0f / 60.0f;
        private const float HalfWindowSeconds = 0.05f;
        private static readonly List<ParticleSystemRenderer> Renderers =
            new List<ParticleSystemRenderer>();
        private static readonly string[][] TextureProperties = {
            new[] {"_MainTex"},
            new[] {"_DisturbTex1", "_SampleTex0"},
            new[] {"_MaskTex", "_SampleTex1"},
            new[] {"_BlendTex", "_SampleTex2"},
            new[] {"_DissolveTex", "_SampleTex3"},
        };
        private static IntPtr renderEvent;
        private static bool prepared;
        private static bool failed;
        private static bool active;
        private static bool submissionPending;
        private static string failure = string.Empty;
        private static bool loggedActivation;
        private static bool loggedValidation;
        private static bool loggedFailure;

        public static bool Requested => string.Equals(
            Environment.GetEnvironmentVariable(EnvironmentVariable),
            "1", StringComparison.Ordinal);
        internal static string Failure => failure;
        public static bool HasPendingValidation => submissionPending;

        internal static bool PrepareBeforeCulling(Camera camera)
        {
            active = false;
            if (!Requested || failed || camera == null)
                return false;
            if (SystemInfo.graphicsDeviceType != GraphicsDeviceType.Direct3D11)
                return Fail("exact M18 peak transport requires Direct3D11");
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
                seconds - EndfieldRecoveredM18PeakCaptureData.PhaseSeconds) <=
                HalfWindowSeconds;
            foreach (ParticleSystemRenderer renderer in Renderers)
                if (renderer != null) renderer.enabled = !active;
            return active;
        }

        private static bool PrepareNative()
        {
            Renderers.Clear();
            Material sourceMaterial = null;
            foreach (ParticleSystemRenderer renderer in
                     UnityEngine.Object.FindObjectsOfType<ParticleSystemRenderer>(true))
            {
                if (renderer == null || !renderer.gameObject.scene.IsValid())
                    continue;
                Material material = renderer.sharedMaterial;
                if (material == null || material.name != MaterialName)
                    continue;
                Renderers.Add(renderer);
                if (sourceMaterial == null)
                    sourceMaterial = material;
            }
            if (sourceMaterial == null || Renderers.Count == 0)
                return false;
            var pointers = new IntPtr[5];
            for (int slot = 0; slot < TextureProperties.Length; ++slot)
            {
                Texture texture = ResolveTexture(sourceMaterial,
                    TextureProperties[slot]);
                if (texture == null)
                    return Fail("M18 texture slot t" + slot + " is unresolved");
                pointers[slot] = texture.GetNativeTexturePtr();
                if (pointers[slot] == IntPtr.Zero)
                    return Fail("M18 texture slot t" + slot + " has no native pointer");
            }
            try
            {
                renderEvent = Native.GetRenderEventFunc();
                if (renderEvent == IntPtr.Zero)
                    return Fail("the native M18 peak event is unavailable");
                Native.ResetRuntimeState();
                if (Native.SetTextureResources(
                        pointers[0], pointers[1], pointers[2], pointers[3],
                        pointers[4]) != 1)
                    return Fail("the native M18 texture gate rejected its inputs");
            }
            catch (Exception exception)
            {
                return Fail("the native M18 peak transport could not initialize: " +
                    exception.Message);
            }
            prepared = true;
            return true;
        }

        private static Texture ResolveTexture(Material material, string[] names)
        {
            foreach (string name in names)
            {
                if (!material.HasProperty(name))
                    continue;
                Texture texture = material.GetTexture(name);
                if (texture != null)
                    return texture;
            }
            return null;
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
                return Fail("the exact M18 peak render resources are incomplete");
            var command = new CommandBuffer
            {
                name = "Recovered exact Endminf M18 amber diffusion shell"
            };
            command.SetRenderTarget(
                sceneColor.Target,
                new RenderTargetIdentifier(sceneDepth));
            command.IssuePluginEvent(renderEvent, 0);
            context.ExecuteCommandBuffer(command);
            command.Release();
            submissionPending = true;
            if (!loggedActivation)
            {
                Debug.Log("Recovered exact Endminf M18 diffusion shell submitted " +
                    "from " + EndfieldRecoveredM18PeakCaptureData.SourceSession +
                    " frame " + EndfieldRecoveredM18PeakCaptureData.SourceFrame + ".");
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
                if (draws < EndfieldRecoveredM18PeakCaptureData.DrawCount ||
                    failures != 0 || result < 0)
                {
                    validationFailure = "native M18 peak result drifted: draws=" +
                        draws + ", failures=" + failures + ", hresult=0x" +
                        unchecked((uint)result).ToString("x8");
                    return Fail(validationFailure);
                }
                if (!loggedValidation)
                {
                    Debug.Log("Recovered exact Endminf M18 diffusion shell validated S_OK.");
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
            failure = reason ?? "unknown exact M18 peak failure";
            foreach (ParticleSystemRenderer renderer in Renderers)
                if (renderer != null) renderer.enabled = true;
            if (!loggedFailure)
            {
                Debug.LogWarning("Recovered exact Endminf M18 peak failed closed: " +
                    failure + ".");
                loggedFailure = true;
            }
            return false;
        }

        private static class Native
        {
            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM18PeakRenderEventFunc")]
            internal static extern IntPtr GetRenderEventFunc();
            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcSetM18PeakTextureResources")]
            internal static extern uint SetTextureResources(
                IntPtr t0, IntPtr t1, IntPtr t2, IntPtr t3, IntPtr t4);
            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcResetM18PeakRuntimeState")]
            internal static extern void ResetRuntimeState();
            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM18PeakDrawCount")]
            internal static extern uint GetDrawCount();
            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM18PeakFailureCount")]
            internal static extern uint GetFailureCount();
            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM18PeakLastResult")]
            internal static extern int GetLastResult();
        }
    }
}
