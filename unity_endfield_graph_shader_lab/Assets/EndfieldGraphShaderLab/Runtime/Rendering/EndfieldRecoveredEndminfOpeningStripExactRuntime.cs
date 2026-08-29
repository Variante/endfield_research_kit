using System;
using System.Runtime.InteropServices;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>Exact retained replay of CharEffect/trail's opening packets.</summary>
    public static class EndfieldRecoveredEndminfOpeningStripExactRuntime
    {
        internal const string EnvironmentVariable =
            "ENDFIELD_RECOVERED_ENDMINF_OPENING_STRIP_EXACT";
        private const string NativeLibrary = "OriginalDxbcSwapPlugin";
        private const string MaterialName = "M_UI_charChoose_12";
        private const float ViewerLeadSeconds = 2.0f / 60.0f;
        private const float HalfWindowSeconds = 1.0f / 60.0f;

        private static ParticleSystemRenderer sourceRenderer;
        private static RenderTexture sceneColorSnapshot;
        private static IntPtr renderEvent;
        private static bool initialized;
        private static bool active;
        private static bool failed;
        private static bool submissionPending;
        private static bool submittedThisFrame;
        private static bool validatedThisFrame;
        private static int selectedPacket = -1;
        private static string failure = string.Empty;
        private static bool loggedActivation;
        private static bool loggedValidation;

        public static bool Requested => string.Equals(
            Environment.GetEnvironmentVariable(EnvironmentVariable), "1",
            StringComparison.Ordinal);
        public static bool ActiveThisFrame => Requested && active && !failed;
        public static bool HasPendingValidation => submissionPending;
        public static bool SubmittedThisFrame => submittedThisFrame;
        public static bool ValidatedThisFrame => validatedThisFrame;
        public static int SelectedPacketThisFrame => ActiveThisFrame
            ? selectedPacket
            : -1;
        public static int SourceFrameThisFrame => SelectedPacketThisFrame >= 0
            ? EndfieldRecoveredOpeningStripCaptureData.SourceFrames[
                SelectedPacketThisFrame]
            : -1;
        public static string Failure => failure;

        internal static bool PrepareBeforeCulling(Camera camera)
        {
            active = false;
            submittedThisFrame = false;
            validatedThisFrame = false;
            selectedPacket = -1;
            if (sourceRenderer != null)
                sourceRenderer.enabled = true;
            if (!Requested || failed || camera == null)
                return false;
            if (SystemInfo.graphicsDeviceType != GraphicsDeviceType.Direct3D11)
                return Fail("exact opening-strip transport requires Direct3D11");
            EndfieldHGOperatorLightRig rig =
                camera.GetComponent<EndfieldHGOperatorLightRig>();
            if (rig == null || rig.actorRoot == null ||
                !string.Equals(rig.actorRoot.name, "Endminf",
                    StringComparison.OrdinalIgnoreCase))
                return false;
            if (submissionPending && !ValidatePending(out string validationFailure))
                return Fail(validationFailure);
            if (!RefreshOptionalSourceRendererAndInitializeTransport())
                return false;
            selectedPacket = ResolvePacket(rig.actorRoot);
            active = selectedPacket >= 0;
            if (!active)
                return false;
            try
            {
                if (Native.SetPacketIndex((uint)selectedPacket) != 1)
                    return Fail("native opening-strip packet selector rejected the phase");
            }
            catch (Exception exception)
            {
                return Fail("native opening-strip selection failed: " + exception.Message);
            }
            if (sourceRenderer != null)
                sourceRenderer.enabled = false;
            return true;
        }

        internal static bool Render(
            ScriptableRenderContext context,
            Camera camera,
            EndfieldRecoveredSceneColorHandle sceneColor,
            RenderTexture sceneMV,
            RenderTexture sceneDepth)
        {
            if (!ActiveThisFrame)
                return false;
            if (camera == null || sceneMV == null || sceneDepth == null ||
                !EnsureSnapshot(camera.pixelWidth, camera.pixelHeight))
                return Fail("exact opening-strip render resources are incomplete");
            try
            {
                if (Native.SetOutputDimensions(
                        (uint)camera.pixelWidth, (uint)camera.pixelHeight) != 1)
                    return Fail("native opening-strip output-dimension gate rejected the target");
                if (Native.SetTextureResources(
                        sceneColorSnapshot.GetNativeTexturePtr()) != 1)
                    return Fail("native opening-strip scene-color gate rejected t1");
            }
            catch (Exception exception)
            {
                return Fail("native opening-strip texture setup failed: " + exception.Message);
            }
            var command = new CommandBuffer
            {
                name = "Recovered exact Endminf opening strips"
            };
            command.CopyTexture(
                sceneColor.Target, new RenderTargetIdentifier(sceneColorSnapshot));
            command.SetRenderTarget(
                new[] { sceneColor.Target, new RenderTargetIdentifier(sceneMV) },
                new RenderTargetIdentifier(sceneDepth));
            command.IssuePluginEvent(renderEvent, 0);
            context.ExecuteCommandBuffer(command);
            command.Release();
            submissionPending = true;
            submittedThisFrame = true;
            if (!loggedActivation)
            {
                Debug.Log("Recovered exact Endminf opening-strip packets active from " +
                    EndfieldRecoveredOpeningStripCaptureData.SourceSession + ".");
                loggedActivation = true;
            }
            return true;
        }

        private static bool RefreshOptionalSourceRendererAndInitializeTransport()
        {
            if (sourceRenderer == null)
            {
                foreach (ParticleSystemRenderer renderer in
                         UnityEngine.Object.FindObjectsOfType<ParticleSystemRenderer>(true))
                {
                    if (renderer == null || !renderer.gameObject.scene.IsValid())
                        continue;
                    Material material = renderer.sharedMaterial;
                    if (material == null || material.name != MaterialName)
                        continue;
                    if (sourceRenderer != null)
                        return Fail("multiple live opening-strip renderers were found");
                    sourceRenderer = renderer;
                }
            }
            if (initialized)
                return true;
            try
            {
                renderEvent = Native.GetRenderEventFunc();
                if (renderEvent == IntPtr.Zero)
                    return Fail("native opening-strip event is unavailable");
                Native.ResetRuntimeState();
                if (Native.GetPacketCount() !=
                    EndfieldRecoveredOpeningStripCaptureData.PacketCount)
                    return Fail("native opening-strip packet count drifted");
            }
            catch (Exception exception)
            {
                return Fail("native opening-strip initialization failed: " + exception.Message);
            }
            initialized = true;
            return true;
        }

        private static int ResolvePacket(Transform actorRoot)
        {
            EndfieldOverviewPlayback playback =
                actorRoot.GetComponentInChildren<EndfieldOverviewPlayback>(true);
            Animator animator = playback != null ? playback.animatorSource : null;
            float seconds;
            if (playback != null && playback.AnimatorContractActive &&
                animator != null && animator.enabled)
            {
                AnimatorClipInfo[] clips = animator.GetCurrentAnimatorClipInfo(0);
                if (clips.Length == 0 || clips[0].clip == null ||
                    clips[0].clip.name.IndexOf("overview_start",
                        StringComparison.OrdinalIgnoreCase) < 0)
                    return -1;
                seconds = animator.GetCurrentAnimatorStateInfo(0).normalizedTime *
                    clips[0].clip.length;
            }
            else
            {
                Animation animation =
                    actorRoot.GetComponentInChildren<Animation>(true);
                AnimationState state = animation != null
                    ? animation["ui_overview_start"] : null;
                if (state == null || !state.enabled) return -1;
                seconds = state.time;
            }
            seconds = Mathf.Max(0.0f, seconds - ViewerLeadSeconds);
            float[] phases = EndfieldRecoveredOpeningStripCaptureData.PhaseSeconds;
            int nearest = -1;
            float distance = float.PositiveInfinity;
            for (int index = 0; index < phases.Length; ++index)
            {
                float current = Mathf.Abs(seconds - phases[index]);
                if (current < distance) { nearest = index; distance = current; }
            }
            return distance <= HalfWindowSeconds ? nearest : -1;
        }

        private static bool EnsureSnapshot(int width, int height)
        {
            width = Mathf.Max(width, 1); height = Mathf.Max(height, 1);
            GraphicsFormat format = HDRenderPipeline.RecoveredSceneColorFormat;
            if (sceneColorSnapshot != null && sceneColorSnapshot.IsCreated() &&
                sceneColorSnapshot.width == width && sceneColorSnapshot.height == height &&
                sceneColorSnapshot.graphicsFormat == format)
                return true;
            if (sceneColorSnapshot != null)
            {
                sceneColorSnapshot.Release();
                UnityEngine.Object.DestroyImmediate(sceneColorSnapshot);
            }
            sceneColorSnapshot = new RenderTexture(new RenderTextureDescriptor(width, height)
            {
                graphicsFormat = format,
                depthStencilFormat = GraphicsFormat.None,
                msaaSamples = 1,
                useMipMap = false,
                autoGenerateMips = false,
                sRGB = false,
            }) { name = "Endfield Exact Opening Strip SceneColor", filterMode = FilterMode.Bilinear };
            return sceneColorSnapshot.Create();
        }

        public static bool ValidatePendingAfterSynchronizedRender(
            out string reason)
        {
            return ValidatePending(out reason);
        }

        private static bool ValidatePending(out string reason)
        {
            submissionPending = false; reason = string.Empty;
            try
            {
                uint draws = Native.GetDrawCount();
                uint failures = Native.GetFailureCount();
                int result = Native.GetLastResult();
                uint screenSizePatched = Native.GetScreenSizePatchStatus();
                if (draws == 0 || failures != 0 || result < 0 ||
                    screenSizePatched != 1)
                {
                    reason = "native opening-strip result drifted: draws=" + draws +
                        ", failures=" + failures + ", hresult=0x" +
                        unchecked((uint)result).ToString("x8") +
                        ", screenSizePatched=" + screenSizePatched;
                    return false;
                }
                if (!loggedValidation)
                {
                    Debug.Log("Recovered exact opening-strip native draw validated S_OK.");
                    loggedValidation = true;
                }
                validatedThisFrame = true;
                return true;
            }
            catch (Exception exception) { reason = exception.Message; return false; }
        }

        private static bool Fail(string reason)
        {
            failed = true; active = false; failure = reason;
            if (sourceRenderer != null) sourceRenderer.enabled = true;
            Debug.LogWarning("Recovered exact opening strip failed closed: " + reason + ".");
            return false;
        }

        private static class Native
        {
            [DllImport(NativeLibrary, EntryPoint = "EndfieldOriginalDxbcGetOpeningStripRenderEventFunc")]
            internal static extern IntPtr GetRenderEventFunc();
            [DllImport(NativeLibrary, EntryPoint = "EndfieldOriginalDxbcSetOpeningStripTextureResources")]
            internal static extern uint SetTextureResources(IntPtr sceneColor);
            [DllImport(NativeLibrary, EntryPoint = "EndfieldOriginalDxbcSetOpeningStripOutputDimensions")]
            internal static extern uint SetOutputDimensions(uint width, uint height);
            [DllImport(NativeLibrary, EntryPoint = "EndfieldOriginalDxbcGetOpeningStripScreenSizePatchStatus")]
            internal static extern uint GetScreenSizePatchStatus();
            [DllImport(NativeLibrary, EntryPoint = "EndfieldOriginalDxbcSetOpeningStripPacketIndex")]
            internal static extern uint SetPacketIndex(uint index);
            [DllImport(NativeLibrary, EntryPoint = "EndfieldOriginalDxbcGetOpeningStripPacketCount")]
            internal static extern uint GetPacketCount();
            [DllImport(NativeLibrary, EntryPoint = "EndfieldOriginalDxbcResetOpeningStripRuntimeState")]
            internal static extern void ResetRuntimeState();
            [DllImport(NativeLibrary, EntryPoint = "EndfieldOriginalDxbcGetOpeningStripDrawCount")]
            internal static extern uint GetDrawCount();
            [DllImport(NativeLibrary, EntryPoint = "EndfieldOriginalDxbcGetOpeningStripFailureCount")]
            internal static extern uint GetFailureCount();
            [DllImport(NativeLibrary, EntryPoint = "EndfieldOriginalDxbcGetOpeningStripLastResult")]
            internal static extern int GetLastResult();
        }
    }
}
