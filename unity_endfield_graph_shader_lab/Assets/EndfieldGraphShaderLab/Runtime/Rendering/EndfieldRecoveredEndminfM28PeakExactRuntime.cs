using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Default-off direct-D3D11 transport for Endminf's captured M28 peak
    /// refraction draw. A persistent packed-HDR snapshot breaks the D3D11
    /// SceneColor SRV/RTV alias while retaining the live SceneColor, SceneMV,
    /// and depth attachments as the draw outputs.
    /// </summary>
    public sealed class EndfieldRecoveredEndminfM28PeakExactRuntime : IDisposable
    {
        internal const string EnvironmentVariable =
            "ENDFIELD_RECOVERED_ENDMINF_M28_PEAK_EXACT";
        private const string NativeLibrary = "OriginalDxbcSwapPlugin";
        private const string MaterialName = "M_fx_endminm_gfx_28";
        private const string EditorMaterialAsset =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/" +
            "Endminf/Effects/Overview/Materials/" +
            "M_fx_endminm_gfx_28_pBF7FEE87831B48FB.mat";
        // Full frame 2775 supplies one authoritative 60 Hz packet, not a
        // reusable multi-frame animation. Admit only the nearest simulation
        // sample; adjacent ticks must fall back to the authored renderer.
        private const float HalfWindowSeconds = 1.0f / 120.0f;

        private static EndfieldRecoveredEndminfM28PeakExactRuntime activeInstance;

        private readonly List<ParticleSystemRenderer> sourceRenderers =
            new List<ParticleSystemRenderer>();
        private readonly List<bool> sourceRendererEnabledStates =
            new List<bool>();
        private Texture refractTexture;
        private Texture dissolveTexture;
        private RenderTexture sceneColorSnapshot;
        private IntPtr renderEvent;
        private bool initialized;
        private bool active;
        private bool failed;
        private bool submissionPending;
        private bool submittedThisFrame;
        private bool validatedThisFrame;
        private uint validatedDrawCount;
        private string failure = string.Empty;
        private bool loggedActivation;
        private bool loggedValidation;
        private bool loggedFailure;
        private bool sourceRenderersSuppressed;

        internal EndfieldRecoveredEndminfM28PeakExactRuntime()
        {
            activeInstance = this;
        }

        public static bool Requested => string.Equals(
            Environment.GetEnvironmentVariable(EnvironmentVariable),
            "1",
            StringComparison.Ordinal);

        public static bool HasPendingValidation =>
            activeInstance != null && activeInstance.submissionPending;

        public static bool ActiveThisFrame =>
            activeInstance != null && activeInstance.active;
        public static bool SubmittedThisFrame =>
            activeInstance != null && activeInstance.submittedThisFrame;
        public static bool ValidatedThisFrame =>
            activeInstance != null && activeInstance.validatedThisFrame;
        public static string CurrentFailure =>
            activeInstance != null ? activeInstance.failure : string.Empty;

        internal string Failure => failure;

        internal bool PrepareBeforeCulling(Camera camera)
        {
            active = false;
            submittedThisFrame = false;
            validatedThisFrame = false;
            RestoreSourceRenderers();
            if (!Requested || failed || camera == null)
                return false;
            if (SystemInfo.graphicsDeviceType != GraphicsDeviceType.Direct3D11)
                return Fail("exact M28 peak transport requires Direct3D11");
            if (EndfieldRecoveredM28PeakCaptureData.DrawCount <= 0)
            {
                return Fail("generated M28 peak capture payload is unavailable");
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
            if (!initialized && !Initialize())
                return false;

            float seconds = ResolveOverviewSeconds(lightRig.actorRoot);
            active = !float.IsNaN(seconds) && Mathf.Abs(
                seconds - EndfieldRecoveredM28PeakCaptureData.PhaseSeconds) <=
                HalfWindowSeconds;
            if (!active)
                return false;

            if (!EnsureSceneColorSnapshot(
                    Mathf.Max(camera.pixelWidth, 1),
                    Mathf.Max(camera.pixelHeight, 1)))
            {
                return false;
            }
            if (!ConfigureNativeTextures())
                return false;

            SuppressSourceRenderers();
            return true;
        }

        internal bool Render(
            ScriptableRenderContext context,
            Camera camera,
            EndfieldRecoveredSceneColorHandle sceneColor,
            RenderTexture sceneMV,
            RenderTexture sceneDepth)
        {
            if (!Requested || failed || !initialized || !active)
                return false;
            if (camera == null || sceneMV == null || sceneDepth == null ||
                sceneColorSnapshot == null || !sceneColorSnapshot.IsCreated() ||
                renderEvent == IntPtr.Zero)
            {
                return Fail("the exact M28 peak render resources are incomplete");
            }
            if (!SceneColorDescriptorsMatch(
                    sceneColor.descriptor,
                    sceneColorSnapshot.descriptor))
            {
                return Fail(
                    "the live M28 SceneColor descriptor does not match its native snapshot");
            }
            try
            {
                if (sceneColor.descriptor.width <= 0 ||
                    sceneColor.descriptor.height <= 0 ||
                    Native.SetOutputDimensions(
                        (uint)sceneColor.descriptor.width,
                        (uint)sceneColor.descriptor.height) != 1)
                    return Fail("the native M28 output-size gate rejected its input");
            }
            catch (Exception exception)
            {
                return Fail("the native M28 output-size gate failed: " +
                    exception.Message);
            }

            var command = new CommandBuffer
            {
                name = "Recovered exact Endminf M28 peak refraction"
            };
            command.CopyTexture(
                sceneColor.Target,
                new RenderTargetIdentifier(sceneColorSnapshot));
            command.SetRenderTarget(
                new[]
                {
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
                Debug.Log(
                    "Recovered exact Endminf M28 peak refraction submitted with " +
                    "a persistent packed-HDR SceneColor snapshot.");
                loggedActivation = true;
            }
            return true;
        }

        public static bool ValidatePendingAfterSynchronizedRender(
            out string validationFailure)
        {
            validationFailure = string.Empty;
            if (activeInstance == null || !activeInstance.submissionPending)
                return true;
            return activeInstance.ValidatePending(out validationFailure);
        }

        public void Dispose()
        {
            active = false;
            RestoreSourceRenderers();
            ReleaseTexture(ref sceneColorSnapshot);
            if (ReferenceEquals(activeInstance, this))
                activeInstance = null;
        }

        private bool Initialize()
        {
            sourceRenderers.Clear();
            Material sourceMaterial = null;
            foreach (ParticleSystemRenderer renderer in
                     UnityEngine.Object.FindObjectsOfType<ParticleSystemRenderer>(true))
            {
                if (renderer == null || !renderer.gameObject.scene.IsValid())
                    continue;
                Material material = renderer.sharedMaterial;
                bool exactMaterial = material != null &&
                    material.name == MaterialName;
                bool exactSourceNode = IsM28SourceRenderer(renderer);
                if (!exactMaterial && !exactSourceNode)
                    continue;
                sourceRenderers.Add(renderer);
                if (sourceMaterial == null && exactMaterial)
                    sourceMaterial = material;
            }
            if (sourceMaterial == null)
            {
                foreach (Material material in Resources.FindObjectsOfTypeAll<Material>())
                {
                    if (material != null && material.name == MaterialName)
                    {
                        sourceMaterial = material;
                        break;
                    }
                }
            }
#if UNITY_EDITOR
            if (sourceMaterial == null)
                sourceMaterial = UnityEditor.AssetDatabase.LoadAssetAtPath<Material>(
                    EditorMaterialAsset);
#endif
            if (sourceMaterial == null)
                return Fail("the pinned M28 source material is not loaded");
            if (sourceRenderers.Count == 0)
                return Fail("the retained M28 source renderer is absent");

            refractTexture = ResolveTexture(sourceMaterial, "_RefractTex");
            dissolveTexture = ResolveTexture(sourceMaterial, "_DissolveTex");
            if (refractTexture == null || dissolveTexture == null)
                return Fail("the retained M28 t0/t1 texture binding is incomplete");

            try
            {
                renderEvent = Native.GetRenderEventFunc();
                if (renderEvent == IntPtr.Zero)
                    return Fail("the native M28 peak render event is unavailable");
                Native.ResetRuntimeState();
            }
            catch (Exception exception)
            {
                return Fail(
                    "the native M28 peak transport could not initialize: " +
                    exception.Message);
            }
            initialized = true;
            return true;
        }

        private static bool IsM28SourceRenderer(ParticleSystemRenderer renderer)
        {
            if (renderer == null || renderer.name != "Particle System (9)" ||
                renderer.transform.parent == null ||
                renderer.transform.parent.name != "all")
            {
                return false;
            }
            EndfieldRecoveredParticleEffectSource source =
                renderer.GetComponentInParent<
                    EndfieldRecoveredParticleEffectSource>(true);
            return source != null && source.effectRoot ==
                "P_fxui_endminm003_overview_02";
        }

        private bool ConfigureNativeTextures()
        {
            IntPtr t0 = refractTexture != null
                ? refractTexture.GetNativeTexturePtr()
                : IntPtr.Zero;
            IntPtr t1 = dissolveTexture != null
                ? dissolveTexture.GetNativeTexturePtr()
                : IntPtr.Zero;
            IntPtr t2 = sceneColorSnapshot != null
                ? sceneColorSnapshot.GetNativeTexturePtr()
                : IntPtr.Zero;
            if (t0 == IntPtr.Zero || t1 == IntPtr.Zero || t2 == IntPtr.Zero)
                return Fail("one or more M28 native texture pointers are null");
            try
            {
                if (Native.SetTextureResources(t0, t1, t2) != 1)
                    return Fail("the native M28 texture gate rejected t0/t1/t2");
            }
            catch (Exception exception)
            {
                return Fail(
                    "the native M28 texture transport failed: " +
                    exception.Message);
            }
            return true;
        }

        private bool EnsureSceneColorSnapshot(int width, int height)
        {
            GraphicsFormat format = HDRenderPipeline.RecoveredSceneColorFormat;
            if (sceneColorSnapshot != null && sceneColorSnapshot.IsCreated() &&
                sceneColorSnapshot.width == width &&
                sceneColorSnapshot.height == height &&
                sceneColorSnapshot.graphicsFormat == format &&
                sceneColorSnapshot.antiAliasing == 1)
            {
                return true;
            }

            ReleaseTexture(ref sceneColorSnapshot);
            if ((SystemInfo.copyTextureSupport & CopyTextureSupport.Basic) == 0)
                return Fail("basic GPU CopyTexture support is unavailable");
            if (!SystemInfo.IsFormatSupported(format, FormatUsage.Render) ||
                !SystemInfo.SupportsRenderTextureFormat(
                    RenderTextureFormat.RGB111110Float))
            {
                return Fail("the packed-HDR M28 SceneColor snapshot is unsupported");
            }

            var descriptor = new RenderTextureDescriptor(width, height)
            {
                graphicsFormat = format,
                depthStencilFormat = GraphicsFormat.None,
                msaaSamples = 1,
                useMipMap = false,
                autoGenerateMips = false,
                sRGB = false,
            };
            sceneColorSnapshot = new RenderTexture(descriptor)
            {
                hideFlags = HideFlags.HideAndDontSave,
                name = "Endfield Exact M28 SceneColor Snapshot",
                filterMode = FilterMode.Bilinear,
                wrapMode = TextureWrapMode.Clamp,
                anisoLevel = 0,
            };
            if (!sceneColorSnapshot.Create())
            {
                ReleaseTexture(ref sceneColorSnapshot);
                return Fail("could not create the exact M28 SceneColor snapshot");
            }
            return true;
        }

        private bool ValidatePending(out string validationFailure)
        {
            validationFailure = string.Empty;
            submissionPending = false;
            try
            {
                uint draws = Native.GetDrawCount();
                uint failures = Native.GetFailureCount();
                int result = Native.GetLastResult();
                uint expected = validatedDrawCount +
                    (uint)EndfieldRecoveredM28PeakCaptureData.DrawCount;
                if (draws < expected || failures != 0 || result < 0)
                {
                    validationFailure =
                        "native M28 peak result drifted: draws=" + draws +
                        ", expected-at-least=" + expected +
                        ", failures=" + failures +
                        ", hresult=0x" +
                        unchecked((uint)result).ToString("x8");
                    return Fail(validationFailure);
                }
                if (Native.GetScreenSizePatchStatus() != 1)
                {
                    validationFailure =
                        "native M28 screen constants were not patched";
                    return Fail(validationFailure);
                }
                validatedDrawCount = draws;
                validatedThisFrame = true;
                if (!loggedValidation)
                {
                    Debug.Log(
                        "Recovered exact Endminf M28 peak refraction validated S_OK.");
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

        private bool Fail(string reason)
        {
            failed = true;
            active = false;
            failure = reason ?? "unknown exact M28 peak failure";
            RestoreSourceRenderers();
            if (!loggedFailure)
            {
                Debug.LogWarning(
                    "Recovered exact Endminf M28 peak failed closed: " +
                    failure + ".");
                loggedFailure = true;
            }
            return false;
        }

        private void SuppressSourceRenderers()
        {
            sourceRendererEnabledStates.Clear();
            foreach (ParticleSystemRenderer renderer in sourceRenderers)
            {
                bool wasEnabled = renderer != null && renderer.enabled;
                sourceRendererEnabledStates.Add(wasEnabled);
                if (renderer != null && wasEnabled)
                    renderer.enabled = false;
            }
            sourceRenderersSuppressed = true;
        }

        private void RestoreSourceRenderers()
        {
            if (!sourceRenderersSuppressed)
                return;
            int count = Mathf.Min(
                sourceRenderers.Count,
                sourceRendererEnabledStates.Count);
            for (int index = 0; index < count; ++index)
            {
                ParticleSystemRenderer renderer = sourceRenderers[index];
                if (renderer != null)
                    renderer.enabled = sourceRendererEnabledStates[index];
            }
            sourceRendererEnabledStates.Clear();
            sourceRenderersSuppressed = false;
        }

        private static Texture ResolveTexture(Material material, string name)
        {
            return material != null && material.HasProperty(name)
                ? material.GetTexture(name)
                : null;
        }

        private static float ResolveOverviewSeconds(Transform actorRoot)
        {
            return EndfieldEndminfVisualCompatibilityClock
                .TryGetAuthenticatedSourceEffectElapsed(out float elapsed)
                ? elapsed
                : float.NaN;
        }

        private static bool SceneColorDescriptorsMatch(
            RenderTextureDescriptor live,
            RenderTextureDescriptor snapshot)
        {
            return live.width == snapshot.width &&
                live.height == snapshot.height &&
                live.volumeDepth == 1 && snapshot.volumeDepth == 1 &&
                live.graphicsFormat == snapshot.graphicsFormat &&
                live.msaaSamples == 1 && snapshot.msaaSamples == 1 &&
                live.dimension == TextureDimension.Tex2D &&
                snapshot.dimension == TextureDimension.Tex2D &&
                !live.useMipMap && !snapshot.useMipMap;
        }

        private static void ReleaseTexture(ref RenderTexture texture)
        {
            if (texture == null)
                return;
            texture.Release();
            if (Application.isPlaying)
                UnityEngine.Object.Destroy(texture);
            else
                UnityEngine.Object.DestroyImmediate(texture);
            texture = null;
        }

        private static class Native
        {
            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM28PeakRenderEventFunc")]
            internal static extern IntPtr GetRenderEventFunc();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcSetM28PeakTextureResources")]
            internal static extern uint SetTextureResources(
                IntPtr t0,
                IntPtr t1,
                IntPtr t2);

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcSetM28PeakOutputDimensions")]
            internal static extern uint SetOutputDimensions(uint width, uint height);

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM28PeakScreenSizePatchStatus")]
            internal static extern uint GetScreenSizePatchStatus();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcResetM28PeakRuntimeState")]
            internal static extern void ResetRuntimeState();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM28PeakDrawCount")]
            internal static extern uint GetDrawCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM28PeakFailureCount")]
            internal static extern uint GetFailureCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM28PeakLastResult")]
            internal static extern int GetLastResult();
        }
    }
}
