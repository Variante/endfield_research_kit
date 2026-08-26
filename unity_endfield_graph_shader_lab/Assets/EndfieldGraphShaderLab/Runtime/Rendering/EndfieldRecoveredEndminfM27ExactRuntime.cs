using System;
using System.Runtime.InteropServices;
using UnityEngine;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Exact direct-D3D11 transport for the captured Endminf M27 HGBuffer draw.
    /// It preserves the retail shader's separate VS/PS constant-buffer and SRV
    /// namespaces, which Unity's shared material shell cannot represent.
    /// </summary>
    public static class EndfieldRecoveredEndminfM27ExactRuntime
    {
        public const string EnvironmentVariable =
            "ENDFIELD_RECOVERED_ENDMINF_M27_EXACT_DXBC";
        private const string NativeLibrary = "OriginalDxbcSwapPlugin";

        private static bool prepared;
        private static bool failed;
        private static string failure = string.Empty;
        private static IntPtr renderEvent;
        private static bool submissionPending;
        private static bool loggedActivation;
        private static bool loggedValidation;
        private static bool loggedFailure;

        public static bool Requested => string.Equals(
            Environment.GetEnvironmentVariable(EnvironmentVariable),
            "1",
            StringComparison.Ordinal);

        public static bool HasPendingValidation => submissionPending;
        public static string Failure => failure;

        internal static bool Prepare(Material sourceMaterial)
        {
            if (!Requested || failed)
                return false;
            if (SystemInfo.graphicsDeviceType != GraphicsDeviceType.Direct3D11)
                return Fail("exact M27 transport requires Direct3D11");
            if (sourceMaterial == null)
                return Fail("the retained M27 source material is absent");
            if (!prepared)
            {
                try
                {
                    renderEvent = Native.GetM27RenderEventFunc();
                    if (renderEvent == IntPtr.Zero)
                        return Fail("the native M27 render event is unavailable");
                    Native.ResetM27RuntimeState();
                    prepared = true;
                }
                catch (Exception exception)
                {
                    return Fail(
                        "the native M27 transport could not initialize: " +
                        exception.Message);
                }
            }

            Texture baseColor = GetRequiredTexture(sourceMaterial, "_BaseColorMap");
            Texture normal = GetRequiredTexture(sourceMaterial, "_NormalMap");
            Texture mro = GetRequiredTexture(sourceMaterial, "_MROMap");
            Texture parallax = GetRequiredTexture(sourceMaterial, "_ParallaxMap");
            if (baseColor == null || normal == null || mro == null || parallax == null)
                return false;
            Texture fallback = Texture2D.blackTexture;
            try
            {
                uint ready = Native.SetM27TextureResources(
                    baseColor.GetNativeTexturePtr(),
                    normal.GetNativeTexturePtr(),
                    mro.GetNativeTexturePtr(),
                    parallax.GetNativeTexturePtr(),
                    fallback.GetNativeTexturePtr(),
                    fallback.GetNativeTexturePtr());
                if (ready != 1)
                    return Fail("one or more native M27 texture pointers are absent");
            }
            catch (Exception exception)
            {
                return Fail("the native M27 textures could not bind: " +
                    exception.Message);
            }
            return true;
        }

        internal static bool Issue(CommandBuffer command)
        {
            if (!Requested || failed || !prepared || renderEvent == IntPtr.Zero)
                return false;
            command.IssuePluginEvent(renderEvent, 0);
            submissionPending = true;
            if (!loggedActivation)
            {
                Debug.Log(
                    "Recovered exact Endminf M27 native HGBuffer draw submitted: " +
                    "frame 2529, five MRTs, capture 20260826T141208Z.");
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
                uint draws = Native.GetM27DrawCount();
                uint failures = Native.GetM27DrawFailureCount();
                int result = Native.GetM27DrawLastResult();
                if (draws == 0 || failures != 0 || result < 0)
                {
                    validationFailure = "native M27 result drifted: draws=" +
                        draws + ", failures=" + failures + ", hresult=0x" +
                        unchecked((uint)result).ToString("x8");
                    return Fail(validationFailure);
                }
                if (!loggedValidation)
                {
                    Debug.Log(
                        "Recovered exact Endminf M27 native draw validated: " +
                        "draw count is nonzero and the callback reported S_OK.");
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

        private static Texture GetRequiredTexture(Material material, string property)
        {
            Texture texture = material.HasProperty(property)
                ? material.GetTexture(property)
                : null;
            if (texture == null)
                Fail("the retained M27 texture " + property + " is absent");
            return texture;
        }

        private static bool Fail(string reason)
        {
            failed = true;
            failure = reason ?? "unknown exact M27 failure";
            if (!loggedFailure)
            {
                Debug.LogWarning(
                    "Recovered exact Endminf M27 failed closed: " + failure + ".");
                loggedFailure = true;
            }
            return false;
        }

        private static class Native
        {
            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM27RenderEventFunc")]
            internal static extern IntPtr GetM27RenderEventFunc();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcSetM27TextureResources")]
            internal static extern uint SetM27TextureResources(
                IntPtr texture0,
                IntPtr texture1,
                IntPtr texture2,
                IntPtr texture3,
                IntPtr texture4,
                IntPtr texture5);

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcResetM27RuntimeState")]
            internal static extern void ResetM27RuntimeState();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM27DrawCount")]
            internal static extern uint GetM27DrawCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM27DrawFailureCount")]
            internal static extern uint GetM27DrawFailureCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM27DrawLastResult")]
            internal static extern int GetM27DrawLastResult();
        }
    }
}
