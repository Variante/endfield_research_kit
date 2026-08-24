using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Isolated one-frame proof for the exact selected deferred-resolver DXBC.
    /// It is inert unless a disposable scene contains this component and the
    /// explicit command-line token is present.
    /// </summary>
    public sealed class EndfieldOriginalDxbcDiagnosticRuntime : MonoBehaviour
    {
        public const string ShaderName =
            "Hidden/Endfield/Diagnostics/OriginalDeferredResolverDxbc";
        public const string KeywordName = "ENDFIELD_ORIGINAL_DXBC_EXACT";
        public const string ActivationArgument =
            "-endfield-original-dxbc-diagnostic";
        public const string OutputArgument =
            "-endfield-original-dxbc-output";
        public const string VertexSha256 =
            "a6afe2c96caa3fd940004ce9ee725886d0f8df683d5f73403278743e32563155";
        public const string PixelSha256 =
            "b21a1e35eda1c5bcb60198c6af313799ddcc94d0cee0be9025938f3ba8c56b6f";

        private static readonly int[] ConstantBufferFloat4Counts =
        {
            45, 157, 259, 3, 2054, 401, 216, 160, 4,
        };

        [SerializeField] private Shader diagnosticShader;
        [SerializeField] private Material diagnosticMaterial;

        public void Configure(Shader shader)
        {
            diagnosticShader = shader;
            diagnosticMaterial = null;
        }

        public void Configure(Shader shader, Material material)
        {
            diagnosticShader = shader;
            diagnosticMaterial = material;
        }

        private IEnumerator Start()
        {
            // Keep the proof out of scene construction and execute it in one
            // isolated player frame after the graphics device is initialized.
            yield return null;

            string outputPath = ReadArgument(
                Environment.GetCommandLineArgs(),
                OutputArgument);
            if (string.IsNullOrWhiteSpace(outputPath))
            {
                outputPath = Path.Combine(
                    Application.persistentDataPath,
                    "original_dxbc_exact_standalone_validation.json");
            }

            bool passed = RunAndWrite(
                diagnosticShader,
                diagnosticMaterial,
                outputPath,
                "standalone-player");
            Debug.Log(
                "Original DXBC standalone diagnostic: " +
                (passed ? "PASS" : "NO_ACTIVATION") +
                "; report=" + outputPath);
            Application.Quit(passed ? 0 : 7);
        }

        public static bool RunAndWrite(
            Shader shader,
            string outputPath,
            string host)
        {
            return RunAndWrite(shader, null, outputPath, host);
        }

        public static bool RunAndWrite(
            Shader shader,
            Material materialTemplate,
            string outputPath,
            string host)
        {
            DiagnosticResult result;
            try
            {
                result = Run(shader, materialTemplate, host);
            }
            catch (Exception exception)
            {
                TryDisarm();
                result = DiagnosticResult.Failed(
                    host,
                    exception.GetType().FullName + ": " + exception.Message);
            }

            string directory = Path.GetDirectoryName(outputPath);
            if (!string.IsNullOrEmpty(directory))
                Directory.CreateDirectory(directory);
            File.WriteAllText(
                outputPath,
                RenderReport(result),
                new UTF8Encoding(false));
            if (!result.Passed)
                Debug.LogError("Original DXBC diagnostic failed closed: " + result.Error);
            return result.Passed;
        }

        // The isolated standalone player must contain the exact replacement
        // DXBC in its serialized shader variant.  The native compiler hook is
        // intentionally armed only around BuildPipeline.BuildPlayer; this
        // keeps the production/editor path fail-closed while making the
        // diagnostic build independent of a stale Unity shader-cache entry.
        public static bool ArmForStandaloneBuild()
        {
            if (!Application.isBatchMode ||
                SystemInfo.graphicsDeviceType != GraphicsDeviceType.Direct3D11)
                return false;
            return Native.SetDiagnosticArmed(1) == 1;
        }

        public static void DisarmAfterStandaloneBuild()
        {
            Native.SetDiagnosticArmed(0);
        }

        public static string StandaloneBuildCounters()
        {
            return
                "callbacks=" + Native.GetCallbackCount() +
                ", vertex=" + Native.GetVertexSwapCount() +
                ", pixel=" + Native.GetPixelSwapCount() +
                ", failures=" + Native.GetFailureCount();
        }

        public static Color RunRecoveredHlslNeutralFixture(Shader shader)
        {
            if (SystemInfo.graphicsDeviceType != GraphicsDeviceType.Direct3D11)
                throw new InvalidOperationException(
                    "Recovered HLSL fixture requires Direct3D11.");
            if (shader == null || !shader.isSupported)
                throw new InvalidOperationException(
                    "Recovered HLSL fixture shader is unavailable or unsupported.");

            Material material = null;
            var buffers = new List<ComputeBuffer>();
            var textures = new List<Texture>();
            var command = new CommandBuffer
            {
                name = "Endfield Recovered Deferred HLSL Neutral Fixture",
            };
            RenderTexture target = null;
            Texture2D readback = null;
            try
            {
                material = new Material(shader)
                {
                    name = "Endfield Recovered Deferred HLSL Neutral Fixture",
                    hideFlags = HideFlags.HideAndDontSave,
                };
                BindConstantBuffers(command, buffers);
                BindResources(command, buffers, textures);

                var descriptor = new RenderTextureDescriptor(1, 1)
                {
                    graphicsFormat = GraphicsFormat.R32G32B32A32_SFloat,
                    depthStencilFormat = GraphicsFormat.None,
                    dimension = TextureDimension.Tex2D,
                    msaaSamples = 1,
                    mipCount = 1,
                    sRGB = false,
                    useMipMap = false,
                    autoGenerateMips = false,
                    enableRandomWrite = false,
                };
                target = new RenderTexture(descriptor)
                {
                    name = "Endfield Recovered Deferred HLSL Fixture Target",
                    hideFlags = HideFlags.HideAndDontSave,
                    filterMode = FilterMode.Point,
                    wrapMode = TextureWrapMode.Clamp,
                };
                if (!target.Create())
                    throw new InvalidOperationException(
                        "Could not create recovered HLSL fixture target.");

                command.SetRenderTarget(target);
                command.ClearRenderTarget(false, true, Color.magenta);
                command.DrawProcedural(
                    Matrix4x4.identity,
                    material,
                    0,
                    MeshTopology.Triangles,
                    3,
                    1);
                Graphics.ExecuteCommandBuffer(command);

                readback = new Texture2D(
                    1,
                    1,
                    TextureFormat.RGBAFloat,
                    false,
                    true)
                {
                    hideFlags = HideFlags.HideAndDontSave,
                };
                RenderTexture previous = RenderTexture.active;
                try
                {
                    RenderTexture.active = target;
                    readback.ReadPixels(new Rect(0, 0, 1, 1), 0, 0, false);
                    readback.Apply(false, false);
                }
                finally
                {
                    RenderTexture.active = previous;
                }
                return readback.GetPixel(0, 0);
            }
            finally
            {
                command.Release();
                foreach (ComputeBuffer buffer in buffers)
                    buffer?.Release();
                foreach (Texture texture in textures)
                    DisposeUnityObject(texture);
                if (target != null)
                {
                    target.Release();
                    DisposeUnityObject(target);
                }
                DisposeUnityObject(readback);
                DisposeUnityObject(material);
            }
        }

        private static DiagnosticResult Run(
            Shader shader,
            Material materialTemplate,
            string host)
        {
            string[] commandLine = Environment.GetCommandLineArgs();
            if (!commandLine.Contains(ActivationArgument, StringComparer.Ordinal))
            {
                throw new InvalidOperationException(
                    "Explicit diagnostic command-line token is absent.");
            }
            if (!Application.isBatchMode)
            {
                throw new InvalidOperationException(
                    "Diagnostic is restricted to batch-mode isolated runs.");
            }
            if (SystemInfo.graphicsDeviceType != GraphicsDeviceType.Direct3D11)
            {
                throw new InvalidOperationException(
                    "Diagnostic requires Direct3D11; actual=" +
                    SystemInfo.graphicsDeviceType + ".");
            }
            if (shader == null || shader.name != ShaderName)
            {
                throw new InvalidOperationException(
                    "Exact diagnostic Shader asset is unavailable.");
            }
            if (!shader.isSupported)
                throw new InvalidOperationException("Diagnostic Shader is unsupported.");

            uint contractVersion = Native.GetContractVersion();
            if (contractVersion != 1)
            {
                throw new InvalidOperationException(
                    "Native diagnostic contract drift: " + contractVersion + ".");
            }
            if (Native.GetDiagnosticArmed() != 0)
            {
                throw new InvalidOperationException(
                    "Native plugin was already armed before the isolated run.");
            }
            uint pluginLoadCount = Native.GetPluginLoadCount();
            uint configureCount = Native.GetConfigureCount();
            if (pluginLoadCount == 0 || configureCount == 0)
            {
                throw new InvalidOperationException(
                    "Shader-extension registration is absent: plugin_loads=" +
                    pluginLoadCount + ", configure_events=" + configureCount + ".");
            }

            Material material = null;
            var buffers = new List<ComputeBuffer>();
            var textures = new List<Texture>();
            var command = new CommandBuffer
            {
                name = "Endfield Original DXBC One-Frame Diagnostic",
            };
            RenderTexture target = null;
            Texture2D readback = null;
            bool armed = false;
            try
            {
                uint armResult = Native.SetDiagnosticArmed(1);
                armed = armResult == 1;
                if (!armed)
                    throw new InvalidOperationException("Native arm request failed.");

                if (Native.GetCallbackCount() != 0 ||
                    Native.GetVertexSwapCount() != 0 ||
                    Native.GetPixelSwapCount() != 0)
                {
                    throw new InvalidOperationException(
                        "Native counters were not reset at the arm boundary.");
                }

                // Construct the material only after arming. Unity may compile
                // a missing local variant while the material is created; doing
                // this before arming would make those compiler callbacks
                // invisible to the exact replacement gate.
                if (materialTemplate != null &&
                    (materialTemplate.shader == null ||
                     materialTemplate.shader.name != ShaderName))
                {
                    throw new InvalidOperationException(
                        "Serialized exact diagnostic material references an " +
                        "unexpected Shader.");
                }
                material = materialTemplate != null
                    ? new Material(materialTemplate)
                    : new Material(shader);
                material.name = "Endfield Original DXBC Isolated Diagnostic";
                material.hideFlags = HideFlags.HideAndDontSave;

                var keyword = new LocalKeyword(shader, KeywordName);
                if (!keyword.isValid)
                    throw new InvalidOperationException(
                        "Reserved local keyword is absent from the diagnostic Shader.");
                material.SetKeyword(keyword, true);
                if (!material.IsKeywordEnabled(keyword))
                    throw new InvalidOperationException(
                        "Reserved local keyword did not become active.");
                BindConstantBuffers(command, buffers);
                ulong[] nativeTexturePointers = BindResources(command, buffers, textures);
                Native.SetDiagnosticTexturePointers(
                    nativeTexturePointers,
                    (uint)nativeTexturePointers.Length);

                var descriptor = new RenderTextureDescriptor(1, 1)
                {
                    graphicsFormat = GraphicsFormat.R32G32B32A32_SFloat,
                    depthStencilFormat = GraphicsFormat.None,
                    dimension = TextureDimension.Tex2D,
                    msaaSamples = 1,
                    mipCount = 1,
                    sRGB = false,
                    useMipMap = false,
                    autoGenerateMips = false,
                    enableRandomWrite = false,
                };
                target = new RenderTexture(descriptor)
                {
                    name = "Endfield Original DXBC One-Pixel Target",
                    hideFlags = HideFlags.HideAndDontSave,
                    filterMode = FilterMode.Point,
                    wrapMode = TextureWrapMode.Clamp,
                };
                if (!target.Create())
                    throw new InvalidOperationException("Could not create diagnostic target.");

                Color sentinel = new Color(0.125f, 0.25f, 0.5f, 0.75f);
                command.SetRenderTarget(target);
                command.ClearRenderTarget(false, true, sentinel);
                // Unity applies SetGlobalConstantBuffer/SetGlobalTexture at a
                // material draw boundary. Keep one shell draw solely to
                // establish the synthetic b/t/s state, then overwrite its
                // pixel with the exact native program in event 0.
                command.DrawProcedural(
                    Matrix4x4.identity,
                    material,
                    0,
                    MeshTopology.Triangles,
                    3,
                    1);
                IntPtr renderEvent = Native.GetRenderEventFunc();
                if (renderEvent == IntPtr.Zero)
                    throw new InvalidOperationException(
                        "Native post-draw inspection event is unavailable.");
                // The exact selected programs are native D3D11 objects, not
                // the shell material's compiled variant. Event 0 installs
                // them and issues the draw after Unity has bound the fixture
                // resources; this prevents DrawProcedural from overwriting
                // the exact stages before execution.
                command.IssuePluginEvent(renderEvent, 0);
                command.IssuePluginEvent(renderEvent, 1);
                Graphics.ExecuteCommandBuffer(command);

                readback = new Texture2D(
                    1,
                    1,
                    TextureFormat.RGBAFloat,
                    false,
                    true)
                {
                    name = "Endfield Original DXBC Readback",
                    hideFlags = HideFlags.HideAndDontSave,
                };
                RenderTexture previous = RenderTexture.active;
                try
                {
                    RenderTexture.active = target;
                    readback.ReadPixels(new Rect(0, 0, 1, 1), 0, 0, false);
                    readback.Apply(false, false);
                }
                finally
                {
                    RenderTexture.active = previous;
                }

                Color pixel = readback.GetPixel(0, 0);
                string outputSha256 = Hash(readback.GetRawTextureData());
                string sentinelSha256 = HashFloatColor(sentinel);
                bool finite =
                    IsFinite(pixel.r) &&
                    IsFinite(pixel.g) &&
                    IsFinite(pixel.b) &&
                    IsFinite(pixel.a);
                bool changed = outputSha256 != sentinelSha256;

                uint callbacks = Native.GetCallbackCount();
                uint vertexSwaps = Native.GetVertexSwapCount();
                uint pixelSwaps = Native.GetPixelSwapCount();
                uint failures = Native.GetFailureCount();
                uint blocked = Native.GetBlockedCount();
                uint unarmedCallbacks = Native.GetUnarmedCallbackCount();
                int lastResult = Native.GetLastResult();
                uint renderEvents = Native.GetRenderEventCount();
                uint exactShaderBound = Native.GetExactShaderBound();
                uint constantBufferMask = Native.GetConstantBufferMask();
                uint shaderResourceMask = Native.GetShaderResourceMask();
                uint postDrawShaderResourceMask =
                    Native.GetPostDrawShaderResourceMask();
                uint samplerMask = Native.GetSamplerMask();
                bool resourceBindingsCompatible =
                    renderEvents >= 2 &&
                    exactShaderBound != 0 &&
                    shaderResourceMask != 0 &&
                    failures == 0 &&
                    finite &&
                    changed;

                bool passed =
                    failures == 0 &&
                    blocked == 0 &&
                    unarmedCallbacks == 0 &&
                    lastResult == 0 &&
                    exactShaderBound != 0 &&
                    resourceBindingsCompatible &&
                    finite &&
                    changed;
                string error = passed
                    ? string.Empty
                    : "Exact-runtime draw gate failed: callbacks=" + callbacks +
                      ", vertex=" + vertexSwaps +
                      ", pixel=" + pixelSwaps +
                      ", failures=" + failures +
                      ", blocked=" + blocked +
                      ", unarmed=" + unarmedCallbacks +
                      ", last=0x" + lastResult.ToString("x8") +
                      ", render_events=" + renderEvents +
                      ", exact_bound=" + exactShaderBound +
                      ", cb_mask=0x" + constantBufferMask.ToString("x") +
                      ", srv_mask=0x" + shaderResourceMask.ToString("x") +
                      ", sampler_mask=0x" + samplerMask.ToString("x") +
                      ", finite=" + finite +
                      ", changed=" + changed + ".";

                return new DiagnosticResult(
                    passed,
                    host,
                    error,
                    contractVersion,
                    pluginLoadCount,
                    configureCount,
                    callbacks,
                    unarmedCallbacks,
                    blocked,
                    vertexSwaps,
                    pixelSwaps,
                    failures,
                    lastResult,
                    renderEvents,
                    exactShaderBound,
                    constantBufferMask,
                    shaderResourceMask,
                    postDrawShaderResourceMask,
                    samplerMask,
                    resourceBindingsCompatible,
                    finite,
                    changed,
                    pixel,
                    outputSha256,
                    sentinelSha256);
            }
            finally
            {
                if (armed)
                    Native.SetDiagnosticArmed(0);
                Native.SetDiagnosticTexturePointers(null, 0);
                command.Release();
                foreach (ComputeBuffer buffer in buffers)
                    buffer?.Release();
                foreach (Texture texture in textures)
                    DisposeUnityObject(texture);
                if (target != null)
                {
                    target.Release();
                    DisposeUnityObject(target);
                }
                DisposeUnityObject(readback);
                DisposeUnityObject(material);
            }
        }

        private static void BindConstantBuffers(
            CommandBuffer command,
            ICollection<ComputeBuffer> buffers)
        {
            for (int slot = 0; slot < ConstantBufferFloat4Counts.Length; slot++)
            {
                int count = ConstantBufferFloat4Counts[slot];
                var values = new Vector4[count];
                if (slot == 0)
                {
                    SetIdentityRows(values, 0);
                    SetIdentityRows(values, 24);
                    values[44] = new Vector4(0.0f, 0.0f, 1.0f, 1.0f);
                }
                else if (slot == 1)
                {
                    values[0] = Vector4.one;
                    values[4] = new Vector4(0.0f, 0.0f, 0.0f, 1.0f);
                    // Exact disabled-height-fog reset values written by
                    // HGAtmosphereRenderer.ResetShaderVariablesGlobalHeightFog.
                    // Leaving both vectors zero makes the original resolver
                    // evaluate log(0) * 0 in its neutral fog composition.
                    values[81] = new Vector4(0.0f, 1.0f, 0.0f, 0.0f);
                    values[82] = new Vector4(0.0f, 0.0f, 0.0f, 1.0f);
                    values[156] = Vector4.zero;
                }

                var buffer = new ComputeBuffer(
                    count,
                    sizeof(float) * 4,
                    ComputeBufferType.Constant)
                {
                    name = "Endfield Original DXBC CB" + slot,
                };
                buffer.SetData(values);
                buffers.Add(buffer);
                command.SetGlobalConstantBuffer(
                    buffer,
                    Shader.PropertyToID("EndfieldCB" + slot),
                    0,
                    count * sizeof(float) * 4);
            }
        }

        private static ulong[] BindResources(
            CommandBuffer command,
            ICollection<ComputeBuffer> buffers,
            ICollection<Texture> textures)
        {
            var structured = new ComputeBuffer(
                4096,
                sizeof(uint),
                ComputeBufferType.Structured)
            {
                name = "Endfield Original DXBC Zero Structured Buffer",
            };
            structured.SetData(new uint[4096]);
            buffers.Add(structured);
            command.SetGlobalBuffer(
                Shader.PropertyToID("_EndfieldBufferT0"),
                structured);

            Texture2D zero2D = Make2D(
                "Endfield Original DXBC Zero 2D",
                Color.clear,
                TextureFormat.RGBAFloat);
            Texture2D depth2D = Make2D(
                "Endfield Original DXBC Depth 2D",
                new Color(0.5f, 0.0f, 0.0f, 0.0f),
                TextureFormat.RGBAFloat);
            Texture2D shadow2D = Make2D(
                "Endfield Original DXBC Shadow 2D",
                Color.white,
                TextureFormat.RFloat);
            Texture2D gbufferA = Make2D(
                "Endfield Original DXBC GBuffer A",
                new Color(0.2f, 0.3f, 0.4f, 0.5f),
                TextureFormat.RGBAFloat);
            Texture2D gbufferB = Make2D(
                "Endfield Original DXBC GBuffer B",
                new Color(0.5f, 0.5f, 0.0f, 0.0f),
                TextureFormat.RGBAFloat);
            Texture2D gbufferC = Make2D(
                "Endfield Original DXBC GBuffer C",
                new Color(0.05f, 0.0f, 0.0f, 1.0f),
                TextureFormat.RGBAFloat);
            Texture2DArray zeroArray = MakeArray();
            Texture3D zero3D = Make3D();
            textures.Add(zero2D);
            textures.Add(depth2D);
            textures.Add(shadow2D);
            textures.Add(gbufferA);
            textures.Add(gbufferB);
            textures.Add(gbufferC);
            textures.Add(zeroArray);
            textures.Add(zero3D);

            var nativeTexturePointers = new ulong[26];
            for (int slot = 1; slot <= 25; slot++)
            {
                Texture texture;
                if (slot == 1)
                    texture = depth2D;
                else if (slot == 5)
                    texture = zeroArray;
                else if (slot == 6)
                    texture = shadow2D;
                else if (slot == 13 || (slot >= 16 && slot <= 21))
                    texture = zero3D;
                // The selected original D3D11 compact resolver consumes the
                // producer's logical GBuffer in t23=A, t24=B, t25=C order.
                // Keep this explicit in the exact-DXBC fixture; source HLSL
                // identifiers are _60/_61/_62, not the compact register names.
                else if (slot == 23)
                    texture = gbufferA;
                else if (slot == 24)
                    texture = gbufferB;
                else if (slot == 25)
                    texture = gbufferC;
                else
                    texture = zero2D;
                command.SetGlobalTexture(
                    Shader.PropertyToID("_EndfieldTextureT" + slot),
                    texture);
                nativeTexturePointers[slot] = NativeTexturePointer(texture);
            }
            return nativeTexturePointers;
        }

        private static ulong NativeTexturePointer(Texture texture)
        {
            // D3D11 GetNativeTexturePtr returns the underlying
            // ID3D11Resource*. The exact native event creates a compatible
            // SRV for each resource after Unity's command-buffer state has
            // been established.
            return texture == null
                ? 0ul
                : unchecked((ulong)texture.GetNativeTexturePtr().ToInt64());
        }

        private static Texture2D Make2D(
            string name,
            Color value,
            TextureFormat format)
        {
            var texture = new Texture2D(1, 1, format, false, true)
            {
                name = name,
                hideFlags = HideFlags.HideAndDontSave,
                filterMode = FilterMode.Point,
                wrapMode = TextureWrapMode.Clamp,
            };
            texture.SetPixel(0, 0, value);
            texture.Apply(false, true);
            return texture;
        }

        private static Texture2DArray MakeArray()
        {
            var texture = new Texture2DArray(
                1,
                1,
                1,
                TextureFormat.RGBAFloat,
                false,
                true)
            {
                name = "Endfield Original DXBC Zero 2D Array",
                hideFlags = HideFlags.HideAndDontSave,
                filterMode = FilterMode.Point,
                wrapMode = TextureWrapMode.Clamp,
            };
            texture.SetPixels(new[] { Color.clear }, 0, 0);
            texture.Apply(false, true);
            return texture;
        }

        private static Texture3D Make3D()
        {
            var texture = new Texture3D(
                1,
                1,
                1,
                TextureFormat.RGBAFloat,
                false)
            {
                name = "Endfield Original DXBC Zero 3D",
                hideFlags = HideFlags.HideAndDontSave,
                filterMode = FilterMode.Point,
                wrapMode = TextureWrapMode.Clamp,
            };
            texture.SetPixels(new[] { Color.clear });
            texture.Apply(false, true);
            return texture;
        }

        private static void SetIdentityRows(Vector4[] values, int start)
        {
            values[start + 0] = new Vector4(1, 0, 0, 0);
            values[start + 1] = new Vector4(0, 1, 0, 0);
            values[start + 2] = new Vector4(0, 0, 1, 0);
            values[start + 3] = new Vector4(0, 0, 0, 1);
        }

        private static bool IsFinite(float value)
        {
            return !float.IsNaN(value) && !float.IsInfinity(value);
        }

        private static string Hash(byte[] bytes)
        {
            using SHA256 sha = SHA256.Create();
            return string.Concat(
                sha.ComputeHash(bytes).Select(value => value.ToString("x2")));
        }

        private static string HashFloatColor(Color color)
        {
            var bytes = new List<byte>(sizeof(float) * 4);
            foreach (float value in new[] { color.r, color.g, color.b, color.a })
                bytes.AddRange(BitConverter.GetBytes(value));
            return Hash(bytes.ToArray());
        }

        private static string RenderReport(DiagnosticResult result)
        {
            string Float(float value) =>
                value.ToString("R", CultureInfo.InvariantCulture);
            var builder = new StringBuilder();
            builder.AppendLine("{");
            builder.AppendLine(
                "  \"schema\": \"endfield.original-dxbc-exact-unity-frame.v1\",");
            builder.AppendLine(
                "  \"status\": \"" +
                (result.Passed ? "pass" : "no_activation") + "\",");
            builder.AppendLine("  \"host\": \"" + Escape(result.Host) + "\",");
            builder.AppendLine(
                "  \"activation_policy\": \"default-off-fail-closed\",");
            builder.AppendLine(
                "  \"production_room_submitted\": false,");
            builder.AppendLine(
                "  \"graphics_device_type\": \"" +
                SystemInfo.graphicsDeviceType + "\",");
            builder.AppendLine(
                "  \"graphics_device_name\": \"" +
                Escape(SystemInfo.graphicsDeviceName) + "\",");
            builder.AppendLine(
                "  \"unity_version\": \"" + Escape(Application.unityVersion) + "\",");
            builder.AppendLine(
                "  \"keyword\": \"" + KeywordName + "\",");
            builder.AppendLine(
                "  \"vertex_sha256\": \"" + VertexSha256 + "\",");
            builder.AppendLine(
                "  \"pixel_sha256\": \"" + PixelSha256 + "\",");
            builder.AppendLine(
                "  \"native_contract_version\": " + result.ContractVersion + ",");
            builder.AppendLine(
                "  \"plugin_load_count\": " + result.PluginLoadCount + ",");
            builder.AppendLine(
                "  \"configure_event_count\": " + result.ConfigureCount + ",");
            builder.AppendLine(
                "  \"callback_count\": " + result.CallbackCount + ",");
            builder.AppendLine(
                "  \"unarmed_callback_count\": " +
                result.UnarmedCallbackCount + ",");
            builder.AppendLine(
                "  \"blocked_callback_count\": " + result.BlockedCount + ",");
            builder.AppendLine(
                "  \"vertex_swap_count\": " + result.VertexSwapCount + ",");
            builder.AppendLine(
                "  \"pixel_swap_count\": " + result.PixelSwapCount + ",");
            builder.AppendLine(
                "  \"failure_count\": " + result.FailureCount + ",");
            builder.AppendLine(
                "  \"last_hresult\": \"0x" +
                result.LastResult.ToString("x8") + "\",");
            builder.AppendLine(
                "  \"render_event_count\": " + result.RenderEventCount + ",");
            builder.AppendLine(
                "  \"post_draw_exact_shader_objects_bound\": " +
                result.ExactShaderBound.ToString().ToLowerInvariant() + ",");
            builder.AppendLine(
                "  \"post_draw_constant_buffer_mask\": \"0x" +
                result.ConstantBufferMask.ToString("x") + "\",");
            builder.AppendLine(
                "  \"post_draw_shader_resource_mask\": \"0x" +
                result.PostDrawShaderResourceMask.ToString("x") + "\",");
            builder.AppendLine(
                "  \"shader_resource_mask\": \"0x" +
                result.ShaderResourceMask.ToString("x") + "\",");
            builder.AppendLine(
                "  \"post_draw_sampler_mask\": \"0x" +
                result.SamplerMask.ToString("x") + "\",");
            builder.AppendLine(
                "  \"resource_binding_compatible\": " +
                result.ResourceBindingsCompatible.ToString().ToLowerInvariant() + ",");
            builder.AppendLine(
                "  \"post_draw_state_note\": " +
                "\"native event 0 executes the exact D3D11 draw; event 1 " +
                "records the post-draw bindings.\",");
            builder.AppendLine(
                "  \"readback_finite\": " +
                result.ReadbackFinite.ToString().ToLowerInvariant() + ",");
            builder.AppendLine(
                "  \"disabled_height_fog_reset_defaults_applied\": true,");
            builder.AppendLine(
                "  \"neutral_fixture_numeric_fidelity\": false,");
            builder.AppendLine(
                "  \"readback_changed_from_sentinel\": " +
                result.ReadbackChanged.ToString().ToLowerInvariant() + ",");
            builder.AppendLine("  \"pixel\": [");
            builder.AppendLine("    " + Float(result.Pixel.r) + ",");
            builder.AppendLine("    " + Float(result.Pixel.g) + ",");
            builder.AppendLine("    " + Float(result.Pixel.b) + ",");
            builder.AppendLine("    " + Float(result.Pixel.a));
            builder.AppendLine("  ],");
            builder.AppendLine(
                "  \"rgba_float_sha256\": \"" + result.OutputSha256 + "\",");
            builder.AppendLine(
                "  \"sentinel_rgba_float_sha256\": \"" +
                result.SentinelSha256 + "\",");
            builder.AppendLine(
                "  \"error\": \"" + Escape(result.Error) + "\"");
            builder.AppendLine("}");
            return builder.ToString();
        }

        private static string Escape(string value)
        {
            return (value ?? string.Empty)
                .Replace("\\", "\\\\")
                .Replace("\"", "\\\"")
                .Replace("\r", "\\r")
                .Replace("\n", "\\n");
        }

        private static void TryDisarm()
        {
            try
            {
                Native.SetDiagnosticArmed(0);
            }
            catch
            {
                // The report retains the original load/contract failure.
            }
        }

        private static void DisposeUnityObject(UnityEngine.Object value)
        {
            if (value == null)
                return;
            if (Application.isPlaying)
                Destroy(value);
            else
                DestroyImmediate(value);
        }

        private static string ReadArgument(string[] args, string name)
        {
            for (int index = 0; index + 1 < args.Length; index++)
            {
                if (string.Equals(args[index], name, StringComparison.Ordinal))
                    return args[index + 1];
            }
            return null;
        }

        private readonly struct DiagnosticResult
        {
            internal readonly bool Passed;
            internal readonly string Host;
            internal readonly string Error;
            internal readonly uint ContractVersion;
            internal readonly uint PluginLoadCount;
            internal readonly uint ConfigureCount;
            internal readonly uint CallbackCount;
            internal readonly uint UnarmedCallbackCount;
            internal readonly uint BlockedCount;
            internal readonly uint VertexSwapCount;
            internal readonly uint PixelSwapCount;
            internal readonly uint FailureCount;
            internal readonly int LastResult;
            internal readonly uint RenderEventCount;
            internal readonly bool ExactShaderBound;
            internal readonly uint ConstantBufferMask;
            internal readonly uint ShaderResourceMask;
            internal readonly uint PostDrawShaderResourceMask;
            internal readonly uint SamplerMask;
            internal readonly bool ResourceBindingsCompatible;
            internal readonly bool ReadbackFinite;
            internal readonly bool ReadbackChanged;
            internal readonly Color Pixel;
            internal readonly string OutputSha256;
            internal readonly string SentinelSha256;

            internal DiagnosticResult(
                bool passed,
                string host,
                string error,
                uint contractVersion,
                uint pluginLoadCount,
                uint configureCount,
                uint callbackCount,
                uint unarmedCallbackCount,
                uint blockedCount,
                uint vertexSwapCount,
                uint pixelSwapCount,
                uint failureCount,
                int lastResult,
                uint renderEventCount,
                uint exactShaderBound,
                uint constantBufferMask,
                uint shaderResourceMask,
                uint postDrawShaderResourceMask,
                uint samplerMask,
                bool resourceBindingsCompatible,
                bool readbackFinite,
                bool readbackChanged,
                Color pixel,
                string outputSha256,
                string sentinelSha256)
            {
                Passed = passed;
                Host = host;
                Error = error;
                ContractVersion = contractVersion;
                PluginLoadCount = pluginLoadCount;
                ConfigureCount = configureCount;
                CallbackCount = callbackCount;
                UnarmedCallbackCount = unarmedCallbackCount;
                BlockedCount = blockedCount;
                VertexSwapCount = vertexSwapCount;
                PixelSwapCount = pixelSwapCount;
                FailureCount = failureCount;
                LastResult = lastResult;
                RenderEventCount = renderEventCount;
                ExactShaderBound = exactShaderBound == 1;
                ConstantBufferMask = constantBufferMask;
                ShaderResourceMask = shaderResourceMask;
                PostDrawShaderResourceMask = postDrawShaderResourceMask;
                SamplerMask = samplerMask;
                ResourceBindingsCompatible = resourceBindingsCompatible;
                ReadbackFinite = readbackFinite;
                ReadbackChanged = readbackChanged;
                Pixel = pixel;
                OutputSha256 = outputSha256 ?? string.Empty;
                SentinelSha256 = sentinelSha256 ?? string.Empty;
            }

            internal static DiagnosticResult Failed(string host, string error)
            {
                return new DiagnosticResult(
                    false,
                    host,
                    error,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    unchecked((int)0x80004005),
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    false,
                    false,
                    false,
                    Color.clear,
                    string.Empty,
                    string.Empty);
            }
        }

        private static class Native
        {
            private const string Library = "OriginalDxbcSwapPlugin";

            [DllImport(Library, EntryPoint = "EndfieldOriginalDxbcGetContractVersion")]
            internal static extern uint GetContractVersion();

            [DllImport(Library, EntryPoint = "EndfieldOriginalDxbcGetPluginLoadCount")]
            internal static extern uint GetPluginLoadCount();

            [DllImport(Library, EntryPoint = "EndfieldOriginalDxbcGetConfigureCount")]
            internal static extern uint GetConfigureCount();

            [DllImport(Library, EntryPoint = "EndfieldOriginalDxbcSetDiagnosticArmed")]
            internal static extern uint SetDiagnosticArmed(uint armed);

            [DllImport(Library, EntryPoint = "EndfieldOriginalDxbcSetDiagnosticTexturePointers")]
            internal static extern void SetDiagnosticTexturePointers(
                [In] ulong[] texturePointers,
                uint count);

            [DllImport(Library, EntryPoint = "EndfieldOriginalDxbcGetDiagnosticArmed")]
            internal static extern uint GetDiagnosticArmed();

            [DllImport(Library, EntryPoint = "EndfieldOriginalDxbcGetCallbackCount")]
            internal static extern uint GetCallbackCount();

            [DllImport(Library, EntryPoint = "EndfieldOriginalDxbcGetUnarmedCallbackCount")]
            internal static extern uint GetUnarmedCallbackCount();

            [DllImport(Library, EntryPoint = "EndfieldOriginalDxbcGetBlockedCount")]
            internal static extern uint GetBlockedCount();

            [DllImport(Library, EntryPoint = "EndfieldOriginalDxbcGetVertexSwapCount")]
            internal static extern uint GetVertexSwapCount();

            [DllImport(Library, EntryPoint = "EndfieldOriginalDxbcGetPixelSwapCount")]
            internal static extern uint GetPixelSwapCount();

            [DllImport(Library, EntryPoint = "EndfieldOriginalDxbcGetFailureCount")]
            internal static extern uint GetFailureCount();

            [DllImport(Library, EntryPoint = "EndfieldOriginalDxbcGetLastResult")]
            internal static extern int GetLastResult();

            [DllImport(Library, EntryPoint = "EndfieldOriginalDxbcGetRenderEventFunc")]
            internal static extern IntPtr GetRenderEventFunc();

            [DllImport(Library, EntryPoint = "EndfieldOriginalDxbcGetRenderEventCount")]
            internal static extern uint GetRenderEventCount();

            [DllImport(Library, EntryPoint = "EndfieldOriginalDxbcGetExactShaderBound")]
            internal static extern uint GetExactShaderBound();

            [DllImport(Library, EntryPoint = "EndfieldOriginalDxbcGetConstantBufferMask")]
            internal static extern uint GetConstantBufferMask();

            [DllImport(Library, EntryPoint = "EndfieldOriginalDxbcGetShaderResourceMask")]
            internal static extern uint GetShaderResourceMask();

            [DllImport(Library, EntryPoint = "EndfieldOriginalDxbcGetPostDrawShaderResourceMask")]
            internal static extern uint GetPostDrawShaderResourceMask();

            [DllImport(Library, EntryPoint = "EndfieldOriginalDxbcGetSamplerMask")]
            internal static extern uint GetSamplerMask();
        }
    }
}
