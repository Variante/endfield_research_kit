using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using UnityEngine;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Exact ordered 15-draw VFXBaseV2 cohort captured at Endminf's open-palm
    /// stone halo. Event zero precedes M29; event one resumes at ordinal 74.
    /// </summary>
    public static class EndfieldRecoveredEndminfVFXBaseV2PeakCohortRuntime
    {
        internal const string EnvironmentVariable =
            "ENDFIELD_RECOVERED_ENDMINF_VFXBASEV2_PEAK_COHORT_EXACT";
        private const string NativeLibrary = "OriginalDxbcSwapPlugin";
        // Frame 2723 matches clean extracted reference frame 219. The clean
        // sequence's established phase rule is (referenceFrame - 3) / 60.
        private const float PhaseSeconds = 3.600000f;
        private const float HalfWindowSeconds = 0.05f;
        private static readonly HashSet<string> MaterialNames =
            new HashSet<string>(StringComparer.Ordinal)
            {
                "M_fx_endminm_gfx_08",
                "M_fx_endminm_gfx_14",
                "M_fx_endminm_gfx_30",
                "M_fx_endminm_gfx_31",
                "M_fx_endminm_gfx_34",
                "M_fx_endminm_gfx_39",
                "M_fx_endminm_gfx_40",
                "M_fx_endminm_gfx_41",
                "M_fx_endminm_gfx_43",
            };
        private static readonly List<ParticleSystemRenderer> Renderers =
            new List<ParticleSystemRenderer>();
        private static IntPtr renderEvent;
        private static bool prepared;
        private static bool failed;
        private static bool active;
        private static bool preSubmitted;
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
            preSubmitted = false;
            if (!Requested || failed || camera == null)
            {
                RestoreRenderers();
                return false;
            }
            if (SystemInfo.graphicsDeviceType != GraphicsDeviceType.Direct3D11)
                return Fail("exact VFXBaseV2 open-palm cohort requires Direct3D11");
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
            active = !float.IsNaN(seconds) &&
                Mathf.Abs(seconds - PhaseSeconds) <= HalfWindowSeconds;
            SetRendererSuppression(active);
            return active;
        }

        private static bool PrepareNative()
        {
            if (!EndfieldRecoveredVFXBaseV2PeakCohortData.PayloadPrepared ||
                EndfieldRecoveredVFXBaseV2PeakCohortData.DrawCount != 15 ||
                EndfieldRecoveredVFXBaseV2PeakCohortData.TextureCount != 5)
                return Fail("generated VFXBaseV2 peak cohort is incomplete");
            Renderers.Clear();
            HashSet<string> found = new HashSet<string>(StringComparer.Ordinal);
            foreach (ParticleSystemRenderer renderer in
                     UnityEngine.Object.FindObjectsOfType<ParticleSystemRenderer>(true))
            {
                if (renderer == null || !renderer.gameObject.scene.IsValid())
                    continue;
                foreach (Material material in renderer.sharedMaterials)
                {
                    if (material == null || !MaterialNames.Contains(material.name))
                        continue;
                    Renderers.Add(renderer);
                    found.Add(material.name);
                    break;
                }
            }
            if (found.Count != MaterialNames.Count)
                return Fail("runtime Endminf hierarchy does not close all nine " +
                    "captured VFXBaseV2 peak materials");
            try
            {
                renderEvent = Native.GetRenderEventFunc();
                if (renderEvent == IntPtr.Zero)
                    return Fail("native VFXBaseV2 peak cohort event is unavailable");
                Native.ResetRuntimeState();
            }
            catch (Exception exception)
            {
                return Fail("native VFXBaseV2 peak cohort initialization failed: " +
                    exception.Message);
            }
            prepared = true;
            return true;
        }

        private static float ResolveOverviewSeconds(Transform actorRoot)
        {
            return EndfieldEndminfVisualCompatibilityClock
                .TryGetAuthenticatedSourceEffectElapsed(out float elapsed)
                ? elapsed
                : float.NaN;
        }

        internal static bool RenderPreM29(
            ScriptableRenderContext context, Camera camera,
            EndfieldRecoveredSceneColorHandle sceneColor, RenderTexture sceneMV,
            RenderTexture sceneDepth)
        {
            if (!PrepareRender(sceneDepth))
                return false;
            Issue(context, sceneColor, sceneMV, 0,
                "Recovered exact Endminf VFXBaseV2 peak ordinal 68");
            preSubmitted = true;
            return true;
        }

        internal static bool RenderPostM29(
            ScriptableRenderContext context, Camera camera,
            EndfieldRecoveredSceneColorHandle sceneColor, RenderTexture sceneMV,
            RenderTexture sceneDepth)
        {
            if (!preSubmitted)
                return Fail("VFXBaseV2 peak post cohort preceded its ordinal-68 draw");
            if (!PrepareRender(sceneDepth))
                return false;
            Issue(context, sceneColor, sceneMV, 1,
                "Recovered exact Endminf VFXBaseV2 peak ordinals 74-88");
            submissionPending = true;
            if (!loggedActivation)
            {
                Debug.Log("Recovered exact Endminf VFXBaseV2 peak submitted: " +
                    "15 draws in frame-2723 chronology around M29 ordinal 73.");
                loggedActivation = true;
            }
            return true;
        }

        private static bool PrepareRender(RenderTexture sceneDepth)
        {
            if (!Requested || failed || !prepared || !active ||
                sceneDepth == null || renderEvent == IntPtr.Zero)
                return false;
            IntPtr depthPointer = sceneDepth.GetNativeTexturePtr();
            if (depthPointer == IntPtr.Zero)
                return Fail("VFXBaseV2 peak depth pointer is null");
            try
            {
                return Native.SetDepthResource(depthPointer) == 1 ||
                    Fail("native VFXBaseV2 peak depth gate rejected its input");
            }
            catch (Exception exception)
            {
                return Fail("native VFXBaseV2 peak depth gate failed: " +
                    exception.Message);
            }
        }

        private static void Issue(
            ScriptableRenderContext context,
            EndfieldRecoveredSceneColorHandle sceneColor, RenderTexture sceneMV,
            int eventId, string name)
        {
            var command = new CommandBuffer { name = name };
            command.SetRenderTarget(
                new[] { sceneColor.Target, new RenderTargetIdentifier(sceneMV) },
                new RenderTargetIdentifier(BuiltinRenderTextureType.None));
            command.IssuePluginEvent(renderEvent, eventId);
            context.ExecuteCommandBuffer(command);
            command.Release();
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
                if (draws != EndfieldRecoveredVFXBaseV2PeakCohortData.DrawCount ||
                    failures != 0 || result < 0)
                {
                    validationFailure = "native VFXBaseV2 peak result drifted: " +
                        "draws=" + draws + ", failures=" + failures +
                        ", hresult=0x" + unchecked((uint)result).ToString("x8");
                    return Fail(validationFailure);
                }
                if (!loggedValidation)
                {
                    Debug.Log("Recovered exact Endminf VFXBaseV2 peak validated: " +
                        "all 15 chronological draws completed with S_OK.");
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
                if (renderer != null) renderer.enabled = !suppress;
        }

        private static void RestoreRenderers() => SetRendererSuppression(false);

        private static bool Fail(string reason)
        {
            failed = true;
            active = false;
            failure = reason ?? "unknown VFXBaseV2 peak cohort failure";
            RestoreRenderers();
            if (!loggedFailure)
            {
                Debug.LogWarning(
                    "Recovered exact Endminf VFXBaseV2 peak failed closed: " +
                    failure + ".");
                loggedFailure = true;
            }
            return false;
        }

        private static class Native
        {
            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetVFXBaseV2PeakCohortRenderEventFunc")]
            internal static extern IntPtr GetRenderEventFunc();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcSetVFXBaseV2PeakCohortDepthResource")]
            internal static extern uint SetDepthResource(IntPtr sceneDepth);

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcResetVFXBaseV2PeakCohortRuntimeState")]
            internal static extern void ResetRuntimeState();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetVFXBaseV2PeakCohortDrawCount")]
            internal static extern uint GetDrawCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetVFXBaseV2PeakCohortFailureCount")]
            internal static extern uint GetFailureCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetVFXBaseV2PeakCohortLastResult")]
            internal static extern int GetLastResult();
        }
    }
}
