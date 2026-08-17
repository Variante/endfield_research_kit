using System;
using System.Collections;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using UnityEngine;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>Opt-in shader-object substitution on the real M23 ParticleSystemRenderer.</summary>
    public sealed class EndfieldLiZhiyanM23ExactSubstitutionProbe : MonoBehaviour
    {
        public const string ActivationArgument = "-endfield-m23-exact-source-substitution";
        public const string OutputArgument = "-endfield-m23-exact-source-substitution-output";
        private const string Keyword = "ENDFIELD_ORIGINAL_M23_DXBC_EXACT";

        [SerializeField] private ParticleSystemRenderer targetRenderer;

        public void Configure(ParticleSystemRenderer renderer) => targetRenderer = renderer;

        private void Start()
        {
            string[] args = Environment.GetCommandLineArgs();
            if (!Has(args, ActivationArgument)) return;
            Debug.Log("M23 exact source substitution probe activated.");
            StartCoroutine(Run(args));
        }

        private IEnumerator Run(string[] args)
        {
            string output = Read(args, OutputArgument);
            if (string.IsNullOrWhiteSpace(output))
                output = Path.Combine(Application.persistentDataPath, "m23_exact_source_substitution.json");
            string failure = string.Empty;
            Material clone = null;
            bool armed = false;
            try
            {
                if (Application.isBatchMode || SystemInfo.graphicsDeviceType != GraphicsDeviceType.Direct3D11)
                    throw new InvalidOperationException("normal D3D11 player required");
                if (targetRenderer == null || targetRenderer.GetComponent<MeshRenderer>() != null ||
                    targetRenderer.GetComponent<MeshFilter>() != null)
                    throw new InvalidOperationException("exact source ParticleSystemRenderer identity missing");
                if (Native.GetContractVersion() != 1 || Native.GetPluginLoadCount() == 0 ||
                    Native.GetConfigureCount() == 0 || Native.GetArmed() != 0)
                    throw new InvalidOperationException("native bridge unavailable or already armed");
                clone = new Material(targetRenderer.sharedMaterial) { name = targetRenderer.sharedMaterial.name + " ExactSubstitution" };
                armed = Native.SetArmed(1) == 1;
                if (!armed) throw new InvalidOperationException("bridge arm failed");
                clone.EnableKeyword(Keyword);
                targetRenderer.sharedMaterial = clone;
            }
            catch (Exception exception)
            {
                failure = exception.GetType().FullName + ": " + exception.Message;
            }

            if (string.IsNullOrEmpty(failure))
            {
                yield return null;
                yield return null;
            }

            uint callbacks = 0, shell = 0, vs = 0, ps = 0, failures = 0;
            int hresult = 0;
            try
            {
                callbacks = Native.GetCallbackCount();
                shell = Native.GetShellInputObservedCount();
                vs = Native.GetVertexSwapCount();
                ps = Native.GetPixelSwapCount();
                failures = Native.GetFailureCount();
                hresult = Native.GetLastResult();
            }
            catch (Exception exception)
            {
                failure = exception.GetType().FullName + ": " + exception.Message;
            }
            bool substitution = string.IsNullOrEmpty(failure) && callbacks == 2 && shell == 2 &&
                vs == 1 && ps == 1 && failures == 0 && hresult == 0;
            Write(output, substitution, failure, callbacks, shell, vs, ps, failures, hresult);

            if (armed)
            {
                Native.SetArmed(0);
                IntPtr callback = Native.GetRenderEventFunc();
                if (callback != IntPtr.Zero)
                {
                    var cleanup = new CommandBuffer { name = "M23 source substitution cleanup" };
                    cleanup.IssuePluginEvent(callback, 3);
                    Graphics.ExecuteCommandBuffer(cleanup);
                    cleanup.Release();
                }
            }
            yield break;
        }

        private static void Write(string path, bool substitution, string failure, uint callbacks,
            uint shell, uint vs, uint ps, uint failures, int hresult)
        {
            string directory = Path.GetDirectoryName(path);
            if (!string.IsNullOrEmpty(directory)) Directory.CreateDirectory(directory);
            File.WriteAllText(path, "{\n" +
                "  \"schema\": \"endfield.lizhiyan-m23-exact-source-substitution.v1\",\n" +
                "  \"status\": \"" + (substitution ? "pass" : "fail") + "\",\n" +
                "  \"source_renderer_identity_preserved\": true,\n" +
                "  \"shader_substitution\": true,\n" +
                "  \"retail_shader_selection_claim\": false,\n" +
                "  \"callback_count\": " + callbacks + ",\n" +
                "  \"shell_input_observed_count\": " + shell + ",\n" +
                "  \"vertex_swap_count\": " + vs + ",\n" +
                "  \"pixel_swap_count\": " + ps + ",\n" +
                "  \"failure_count\": " + failures + ",\n" +
                "  \"last_hresult\": " + hresult + ",\n" +
                "  \"failure\": \"" + Escape(failure) + "\"\n}\n", new UTF8Encoding(false));
        }

        private static bool Has(string[] args, string name) => Array.IndexOf(args, name) >= 0;
        private static string Read(string[] args, string name)
        {
            for (int i = 0; i < args.Length; i++)
            {
                if (args[i] == name && i + 1 < args.Length) return args[i + 1];
                string prefix = name + "=";
                if (args[i].StartsWith(prefix, StringComparison.Ordinal))
                    return args[i].Substring(prefix.Length);
            }
            return null;
        }
        private static string Escape(string value) => (value ?? string.Empty).Replace("\\", "\\\\").Replace("\"", "\\\"");

        private static class Native
        {
            private const string Library = "OriginalM23DxbcExactPlugin";
            [DllImport(Library, CallingConvention = CallingConvention.Cdecl, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetContractVersion")] internal static extern uint GetContractVersion();
            [DllImport(Library, CallingConvention = CallingConvention.Cdecl, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetPluginLoadCount")] internal static extern uint GetPluginLoadCount();
            [DllImport(Library, CallingConvention = CallingConvention.Cdecl, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetConfigureCount")] internal static extern uint GetConfigureCount();
            [DllImport(Library, CallingConvention = CallingConvention.Cdecl, EntryPoint = "EndfieldOriginalM23DxbcBridgeSetArmed")] internal static extern uint SetArmed(uint value);
            [DllImport(Library, CallingConvention = CallingConvention.Cdecl, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetArmed")] internal static extern uint GetArmed();
            [DllImport(Library, CallingConvention = CallingConvention.Cdecl, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetCallbackCount")] internal static extern uint GetCallbackCount();
            [DllImport(Library, CallingConvention = CallingConvention.Cdecl, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetShellInputObservedCount")] internal static extern uint GetShellInputObservedCount();
            [DllImport(Library, CallingConvention = CallingConvention.Cdecl, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetVertexSwapCount")] internal static extern uint GetVertexSwapCount();
            [DllImport(Library, CallingConvention = CallingConvention.Cdecl, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetPixelSwapCount")] internal static extern uint GetPixelSwapCount();
            [DllImport(Library, CallingConvention = CallingConvention.Cdecl, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetFailureCount")] internal static extern uint GetFailureCount();
            [DllImport(Library, CallingConvention = CallingConvention.Cdecl, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetLastResult")] internal static extern int GetLastResult();
            [DllImport(Library, CallingConvention = CallingConvention.Cdecl, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetRenderEventFunc")] internal static extern IntPtr GetRenderEventFunc();
        }
    }
}
