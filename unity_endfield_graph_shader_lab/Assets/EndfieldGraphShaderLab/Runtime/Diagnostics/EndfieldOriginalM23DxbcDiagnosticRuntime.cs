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
    /// Isolated, opt-in M23 exact-DXBC execution gate. This component is used
    /// only by the generated diagnostic scene/player; it is never part of the
    /// normal character viewer and it never claims visual fidelity.
    /// </summary>
    public sealed class EndfieldOriginalM23DxbcDiagnosticRuntime : MonoBehaviour
    {
        public const string ShaderName =
            "Hidden/Endfield/Diagnostics/OriginalM23Dxbc";
        public const string KeywordName = "ENDFIELD_ORIGINAL_M23_DXBC_EXACT";
        public const string ActivationArgument =
            "-endfield-original-m23-dxbc-diagnostic";
        public const string OutputArgument =
            "-endfield-original-m23-dxbc-output";
        public const string VisualGridArgument =
            "-endfield-original-m23-dxbc-visual-grid";
        public const string VertexSha256 =
            "7d0a508f7b1e5c9aef0b89489feae97f8669a8cddaba1de0ccc0e26fd0eb2ca0";
        public const string PixelSha256 =
            "0ff508aa08112122c14a3ece17d12f15778eaf39ad0c639c946512dc996b6f83";

        private static readonly int[] SharedConstantBufferFloat4Counts =
            { 45, 105, 104, 14, 50 };
        private const uint VisualGridMode = 1u;
        private const uint VisualGridSize = 16u;
        private const int VisualGridFloatCount = 16 * 16 * 4;
        private const uint VisualGridConfigAllBits = 0x7fu;

        [SerializeField] private Shader diagnosticShader;

        public void Configure(Shader shader)
        {
            diagnosticShader = shader;
        }

        private IEnumerator Start()
        {
            yield return null;
            string output = ReadArgument(Environment.GetCommandLineArgs(), OutputArgument);
            if (string.IsNullOrWhiteSpace(output))
                output = Path.Combine(Application.persistentDataPath,
                    "original_m23_dxbc_exact_standalone_validation.json");
            bool visualGrid = HasArgument(Environment.GetCommandLineArgs(), VisualGridArgument);
            bool passed = RunAndWrite(diagnosticShader, output, visualGrid);
            Debug.Log("Original M23 DXBC bridge: " + (passed ? "PASS" : "FAIL") +
                      "; report=" + output);
            Application.Quit(passed ? 0 : 7);
        }

        public static bool RunAndWrite(Shader shader, string outputPath)
        {
            return RunAndWrite(shader, outputPath, false);
        }

        public static bool RunAndWrite(Shader shader, string outputPath, bool visualGrid)
        {
            Result result;
            VisualGridData visual = null;
            try
            {
                result = Run(shader, visualGrid);
                if (visualGrid)
                {
                    visual = CaptureVisualGrid(outputPath);
                    if (!visual.Valid)
                        result = Result.Failed("M23 visual grid validation failed: " + visual.Error);
                }
            }
            catch (Exception exception)
            {
                TryDisarmAndCleanup();
                result = Result.Failed(exception.GetType().FullName + ": " + exception.Message);
                if (visualGrid && visual == null)
                    visual = new VisualGridData { Error = result.Error };
            }
            finally
            {
                if (visualGrid)
                {
                    try { Native.SetVisualMode(0); }
                    catch { }
                }
            }
            WriteText(outputPath, RenderReport(result, visual));
            if (!result.Passed)
                Debug.LogError("Original M23 DXBC bridge: " + result.Error);
            return result.Passed;
        }

        public static bool WriteD3D12NonActivationReport(string outputPath)
        {
            GraphicsDeviceType actual = SystemInfo.graphicsDeviceType;
            uint armed = 0, vertex = 0, pixel = 0;
            string error = string.Empty;
            try
            {
                armed = Native.GetArmed();
                vertex = Native.GetVertexSwapCount();
                pixel = Native.GetPixelSwapCount();
            }
            catch (Exception exception)
            {
                error = exception.GetType().FullName + ": " + exception.Message;
            }
            bool passed = actual == GraphicsDeviceType.Direct3D12 && armed == 0 &&
                vertex == 0 && pixel == 0 && string.IsNullOrEmpty(error);
            WriteText(outputPath,
                "{\n" +
                "  \"schema\": \"endfield.original-m23-dxbc-d3d12-non-activation.v1\",\n" +
                "  \"status\": \"" + (passed ? "pass" : "fail") + "\",\n" +
                "  \"actual_graphics_api\": \"" + actual + "\",\n" +
                "  \"diagnostic_armed\": " + armed + ",\n" +
                "  \"vertex_swap_count\": " + vertex + ",\n" +
                "  \"pixel_swap_count\": " + pixel + ",\n" +
                "  \"visual_fidelity_claim\": false,\n" +
                "  \"error\": \"" + Escape(error) + "\"\n}\n");
            return passed;
        }

        private static Result Run(Shader shader, bool visualGrid)
        {
            string[] args = Environment.GetCommandLineArgs();
            if (!args.Contains(ActivationArgument, StringComparer.Ordinal))
                throw new InvalidOperationException("Explicit M23 diagnostic token is absent.");
            if (!Application.isBatchMode)
                throw new InvalidOperationException("M23 diagnostic requires batch mode.");
            if (SystemInfo.graphicsDeviceType != GraphicsDeviceType.Direct3D11)
                throw new InvalidOperationException("M23 diagnostic requires Direct3D11; actual=" +
                    SystemInfo.graphicsDeviceType + ".");
            if (shader == null || shader.name != ShaderName || !shader.isSupported)
                throw new InvalidOperationException("M23 diagnostic shader is unavailable.");
            if (Native.GetContractVersion() != 1 || Native.GetArmed() != 0 ||
                Native.GetPluginLoadCount() == 0 || Native.GetConfigureCount() == 0)
                throw new InvalidOperationException("M23 native bridge contract is absent or already armed.");
            if (Native.SetVisualMode(visualGrid ? VisualGridMode : 0u) != 1u)
                throw new InvalidOperationException("M23 visual mode could not be selected while disarmed.");

            var material = new Material(shader)
            {
                name = "Endfield Original M23 DXBC Exact Diagnostic",
                hideFlags = HideFlags.HideAndDontSave,
            };
            var buffers = new List<ComputeBuffer>();
            var textures = new List<Texture>();
            var command = new CommandBuffer { name = "Endfield Original M23 DXBC Bridge" };
            Mesh mesh = null;
            RenderTexture target = null;
            RenderTexture depth = null;
            Texture2D readback = null;
            bool armed = false;
            try
            {
                armed = Native.SetArmed(1) == 1;
                if (!armed)
                    throw new InvalidOperationException("M23 native bridge arm failed.");
                if (Native.GetCallbackCount() != 0 || Native.GetVertexSwapCount() != 0 ||
                    Native.GetPixelSwapCount() != 0)
                    throw new InvalidOperationException("M23 bridge counters were not reset at arm.");

                var keyword = new LocalKeyword(shader, KeywordName);
                if (!keyword.isValid)
                    throw new InvalidOperationException("M23 exact keyword is absent.");
                material.SetKeyword(keyword, true);
                BindConstantBuffers(command, buffers);
                BindResources(command, buffers, textures);
                mesh = MakeMesh();
                target = MakeColorTarget("M23 Exact Diagnostic Target");
                depth = MakeDepthTarget();
                Color sentinel = new Color(0.125f, 0.25f, 0.5f, 0.75f);
                command.SetRenderTarget(target);
                command.ClearRenderTarget(false, true, sentinel);
                command.SetRenderTarget(target, depth);
                IntPtr eventFunction = Native.GetRenderEventFunc();
                if (eventFunction == IntPtr.Zero)
                    throw new InvalidOperationException("M23 bridge render event is absent.");
                // Event 4/5 are observation-only callbacks placed immediately
                // around this real Unity DrawMesh. They copy only VS b3 into a
                // staging readback when its recovered 224-byte contract holds.
                command.IssuePluginEvent(eventFunction, 4);
                command.DrawMesh(mesh, Matrix4x4.identity, material, 0, 0);
                command.IssuePluginEvent(eventFunction, 5);
                command.IssuePluginEvent(eventFunction, 1);
                command.IssuePluginEvent(eventFunction, 2);
                Graphics.ExecuteCommandBuffer(command);

                readback = Readback(target, "M23 Exact Diagnostic Readback");
                uint callback = Native.GetCallbackCount();
                uint unarmed = Native.GetUnarmedCallbackCount();
                uint platformBlocked = Native.GetPlatformBlockedCount();
                uint shellInputObserved = Native.GetShellInputObservedCount();
                uint blocked = Native.GetBlockedCount();
                uint vertexSwap = Native.GetVertexSwapCount();
                uint pixelSwap = Native.GetPixelSwapCount();
                uint failures = Native.GetFailureCount();
                int hresult = Native.GetLastResult();
                uint events = Native.GetRenderEventCount();
                uint ignoredEvents = Native.GetIgnoredRenderEventCount();
                uint nativeExecution = Native.GetNativeExecutionCount();
                bool exactBound = Native.GetExactShaderBound() == 1;
                uint vsCb = Native.GetVertexConstantBufferMask();
                uint vsSrv = Native.GetVertexShaderResourceMask();
                uint psCb = Native.GetPixelConstantBufferMask();
                uint psSrv = Native.GetPixelShaderResourceMask();
                uint psSampler = Native.GetPixelSamplerMask();
                RealDrawObservation realDraw = ReadRealDrawObservation();
                Color pixel = readback.GetPixel(0, 0);
                var cleanup = new CommandBuffer { name = "Endfield Original M23 DXBC Cleanup" };
                cleanup.IssuePluginEvent(eventFunction, 3);
                Graphics.ExecuteCommandBuffer(cleanup);
                cleanup.Release();
                uint cleanupCount = Native.GetCleanupCount();
                uint cleanupPending = Native.GetCleanupPending();
                armed = false;
                bool executionGate = callback == 2 && unarmed == 0 && platformBlocked == 0 &&
                    shellInputObserved == 2 && blocked == 0 && vertexSwap == 1 && pixelSwap == 1 &&
                    failures == 0 && hresult == 0 && events == 4 && ignoredEvents == 0 &&
                    nativeExecution == 1 && exactBound && vsCb == 0x1Fu &&
                    vsSrv == (visualGrid ? 0u : 1u) &&
                    psCb == 0x1Fu && psSrv == 0x1Fu && psSampler == 0x1Fu &&
                    cleanupCount == 1 && cleanupPending == 0;
                return new Result(executionGate,
                    executionGate ? string.Empty : "M23 exact native execution gate failed.",
                    callback, unarmed, platformBlocked, shellInputObserved, blocked, vertexSwap,
                    pixelSwap, failures, hresult, events, ignoredEvents, nativeExecution,
                    cleanupCount, cleanupPending, exactBound, vsCb, vsSrv, psCb, psSrv,
                    psSampler, ColorFinite(pixel), pixel, HashFloatColor(pixel),
                    HashFloatColor(sentinel), executionGate, realDraw);
            }
            finally
            {
                if (armed) TryDisarmAndCleanup();
                command.Release();
                foreach (ComputeBuffer buffer in buffers) buffer.Dispose();
                foreach (Texture texture in textures) DisposeUnityObject(texture);
                Release(target); Release(depth);
                DisposeUnityObject(readback); DisposeUnityObject(mesh); DisposeUnityObject(material);
            }
        }

        private static void BindConstantBuffers(CommandBuffer command, ICollection<ComputeBuffer> buffers)
        {
            for (int slot = 0; slot < SharedConstantBufferFloat4Counts.Length; slot++)
            {
                int count = SharedConstantBufferFloat4Counts[slot];
                var values = new Vector4[count];
                if (slot == 0) values[0] = Vector4.one;
                if (slot == 1) values[0] = Vector4.one;
                if (slot == 2) values[0] = Vector4.one;
                if (slot == 3) values[0] = Vector4.one;
                if (slot == 4) values[3] = new Vector4(1, 0, 0, 0);
                var buffer = new ComputeBuffer(count, sizeof(float) * 4, ComputeBufferType.Constant)
                { name = "Endfield M23 shared CB" + slot };
                buffer.SetData(values);
                buffers.Add(buffer);
                command.SetGlobalConstantBuffer(buffer, Shader.PropertyToID("EndfieldM23CB" + slot),
                    0, count * sizeof(float) * 4);
            }
        }

        private static void BindResources(CommandBuffer command, ICollection<ComputeBuffer> buffers,
            ICollection<Texture> textures)
        {
            var structured = new ComputeBuffer(256, sizeof(float) * 4, ComputeBufferType.Structured)
            { name = "Endfield M23 VS t0" };
            structured.SetData(new Vector4[256]);
            buffers.Add(structured);
            command.SetGlobalBuffer("_EndfieldM23VST0", structured);
            for (int slot = 0; slot < 5; slot++)
            {
                var texture = Make2D("Endfield M23 PS t" + slot,
                    slot == 0 ? Color.white : Color.clear);
                textures.Add(texture);
                command.SetGlobalTexture("_EndfieldM23TextureT" + slot, texture);
            }
        }

        private static Mesh MakeMesh()
        {
            var mesh = new Mesh { name = "Endfield M23 136-byte Vertex Fixture",
                hideFlags = HideFlags.HideAndDontSave };
            var layout = new[]
            {
                new VertexAttributeDescriptor(VertexAttribute.Position, VertexAttributeFormat.Float32, 3),
                new VertexAttributeDescriptor(VertexAttribute.Normal, VertexAttributeFormat.Float32, 3),
                new VertexAttributeDescriptor(VertexAttribute.Tangent, VertexAttributeFormat.Float32, 4),
                new VertexAttributeDescriptor(VertexAttribute.Color, VertexAttributeFormat.Float32, 4, 1),
                new VertexAttributeDescriptor(VertexAttribute.TexCoord0, VertexAttributeFormat.Float32, 4, 1),
                new VertexAttributeDescriptor(VertexAttribute.TexCoord1, VertexAttributeFormat.Float32, 4, 1),
                new VertexAttributeDescriptor(VertexAttribute.TexCoord4, VertexAttributeFormat.Float32, 4, 1),
                new VertexAttributeDescriptor(VertexAttribute.BlendWeight, VertexAttributeFormat.Float32, 4, 2),
                new VertexAttributeDescriptor(VertexAttribute.BlendIndices, VertexAttributeFormat.UInt32, 4, 2),
            };
            if (Marshal.SizeOf(typeof(M23VertexStream0)) +
                Marshal.SizeOf(typeof(M23VertexStream1)) +
                Marshal.SizeOf(typeof(M23VertexStream2)) != 136)
                throw new InvalidOperationException("M23 vertex ABI drift.");
            mesh.SetVertexBufferParams(3, layout);
            var stream0 = new M23VertexStream0[3];
            var stream1 = new M23VertexStream1[3];
            var stream2 = new M23VertexStream2[3];
            Vector3[] positions = { new Vector3(-1, -1, 0), new Vector3(3, -1, 0), new Vector3(-1, 3, 0) };
            Vector4[] uv = { new Vector4(0, 0, 0, 0), new Vector4(2, 0, 0, 0), new Vector4(0, 2, 0, 0) };
            for (int i = 0; i < 3; i++)
            {
                stream0[i] = M23VertexStream0.Make(positions[i]);
                stream1[i] = M23VertexStream1.Make(uv[i]);
                stream2[i] = M23VertexStream2.Default();
            }
            mesh.SetVertexBufferData(stream0, 0, 0, 3, 0, MeshUpdateFlags.DontRecalculateBounds);
            mesh.SetVertexBufferData(stream1, 0, 0, 3, 1, MeshUpdateFlags.DontRecalculateBounds);
            mesh.SetVertexBufferData(stream2, 0, 0, 3, 2, MeshUpdateFlags.DontRecalculateBounds);
            mesh.SetIndexBufferParams(3, IndexFormat.UInt16);
            mesh.SetIndexBufferData(new ushort[] { 0, 1, 2 }, 0, 0, 3);
            mesh.subMeshCount = 1;
            mesh.SetSubMesh(0, new SubMeshDescriptor(0, 3, MeshTopology.Triangles),
                MeshUpdateFlags.DontRecalculateBounds);
            mesh.bounds = new Bounds(Vector3.zero, Vector3.one * 8);
            return mesh;
        }

        private static RenderTexture MakeColorTarget(string name)
        {
            var descriptor = new RenderTextureDescriptor(1, 1)
            {
                graphicsFormat = GraphicsFormat.R32G32B32A32_SFloat,
                depthStencilFormat = GraphicsFormat.None, dimension = TextureDimension.Tex2D,
                msaaSamples = 1, mipCount = 1, sRGB = false,
                useMipMap = false, autoGenerateMips = false,
            };
            var target = new RenderTexture(descriptor) { name = name,
                hideFlags = HideFlags.HideAndDontSave, filterMode = FilterMode.Point,
                wrapMode = TextureWrapMode.Clamp };
            if (!target.Create()) throw new InvalidOperationException("Could not create target.");
            return target;
        }

        private static RenderTexture MakeDepthTarget()
        {
            var descriptor = new RenderTextureDescriptor(1, 1)
            { graphicsFormat = GraphicsFormat.None,
                depthStencilFormat = GraphicsFormat.D24_UNorm_S8_UInt,
                dimension = TextureDimension.Tex2D, msaaSamples = 1 };
            var target = new RenderTexture(descriptor) { name = "Endfield M23 Depth",
                hideFlags = HideFlags.HideAndDontSave };
            if (!target.Create()) throw new InvalidOperationException("Could not create depth target.");
            return target;
        }

        private static Texture2D Readback(RenderTexture target, string name)
        {
            var result = new Texture2D(1, 1, TextureFormat.RGBAFloat, false, true)
            { name = name, hideFlags = HideFlags.HideAndDontSave };
            RenderTexture previous = RenderTexture.active;
            try { RenderTexture.active = target; result.ReadPixels(new Rect(0, 0, 1, 1), 0, 0, false); result.Apply(false, false); }
            finally { RenderTexture.active = previous; }
            return result;
        }

        private static Texture2D Make2D(string name, Color value)
        {
            var texture = new Texture2D(1, 1, TextureFormat.RGBAFloat, false, true)
            { name = name, hideFlags = HideFlags.HideAndDontSave, filterMode = FilterMode.Point,
                wrapMode = TextureWrapMode.Clamp };
            texture.SetPixel(0, 0, value); texture.Apply(false, true); return texture;
        }

        private static VisualGridData CaptureVisualGrid(string outputPath)
        {
            var result = new VisualGridData
            {
                FloatCount = VisualGridFloatCount,
            };
            float[] values = new float[VisualGridFloatCount];
            try
            {
                result.ConfigMask = Native.GetVisualConfigMask();
                result.Size = Native.GetVisualGridSize();
                result.FinitePixels = Native.GetVisualGridFinitePixels();
                result.NonzeroPixels = Native.GetVisualGridNonzeroPixels();
                result.RgbNonzeroPixels = Native.GetVisualGridRgbNonzeroPixels();
                result.AlphaNonzeroPixels = Native.GetVisualGridAlphaNonzeroPixels();
                if (Native.GetVisualMode() != VisualGridMode)
                    throw new InvalidOperationException("native visual mode is not 1");
                if (result.Size != VisualGridSize)
                    throw new InvalidOperationException("unexpected visual grid size=" + result.Size);
                if (result.ConfigMask != VisualGridConfigAllBits)
                    throw new InvalidOperationException("unexpected visual config mask=" + result.ConfigMask);
                if (Native.GetVisualGridValid() != 1u)
                    throw new InvalidOperationException("native visual grid is not valid");
                uint copied = Native.CopyVisualGrid(values, VisualGridFloatCount);
                if (copied != VisualGridFloatCount)
                    throw new InvalidOperationException("visual grid copy count=" + copied);
                for (int i = 0; i < values.Length; i++)
                {
                    if (!IsFinite(values[i]))
                        throw new InvalidOperationException("visual grid contains non-finite float at index=" + i);
                    if (Mathf.Abs(values[i]) > 1000000f)
                        throw new InvalidOperationException("visual grid float is unbounded at index=" + i);
                }
                if (result.FinitePixels != VisualGridSize * VisualGridSize)
                    throw new InvalidOperationException("native finite-pixel count=" + result.FinitePixels);
                result.FloatSha256 = HashFloatArray(values);
                result.PngPath = TryWriteVisualPng(outputPath, values, out string pngError);
                result.PngEncoding = string.IsNullOrEmpty(result.PngPath)
                    ? string.Empty : "Unity Texture2D RGBAFloat EncodeToPNG (clamped preview)";
                result.Error = pngError;
                result.Valid = true;
                return result;
            }
            catch (Exception exception)
            {
                result.Error = exception.GetType().FullName + ": " + exception.Message;
                result.Valid = false;
                return result;
            }
        }

        private static string HashFloatArray(float[] values)
        {
            byte[] bytes = new byte[sizeof(float) * values.Length];
            Buffer.BlockCopy(values, 0, bytes, 0, bytes.Length);
            using (SHA256 sha = SHA256.Create()) return ToHex(sha.ComputeHash(bytes));
        }

        private static string TryWriteVisualPng(string outputPath, float[] values, out string error)
        {
            error = string.Empty;
            Texture2D texture = null;
            try
            {
                texture = new Texture2D((int)VisualGridSize, (int)VisualGridSize,
                    TextureFormat.RGBAFloat, false, true)
                { name = "Endfield M23 Synthetic Visual Grid", hideFlags = HideFlags.HideAndDontSave,
                    filterMode = FilterMode.Point, wrapMode = TextureWrapMode.Clamp };
                var pixels = new Color[(int)(VisualGridSize * VisualGridSize)];
                for (int pixel = 0; pixel < pixels.Length; pixel++)
                {
                    int offset = pixel * 4;
                    pixels[pixel] = new Color(values[offset], values[offset + 1],
                        values[offset + 2], values[offset + 3]);
                }
                texture.SetPixels(pixels);
                texture.Apply(false, false);
                byte[] png = texture.EncodeToPNG();
                if (png == null || png.Length == 0)
                    throw new InvalidOperationException("Texture2D.EncodeToPNG returned no bytes");
                string path = Path.ChangeExtension(outputPath, ".png");
                WriteBytes(path, png);
                return path;
            }
            catch (Exception exception)
            {
                error = "PNG preview unavailable: " + exception.GetType().FullName + ": " + exception.Message;
                return string.Empty;
            }
            finally
            {
                DisposeUnityObject(texture);
            }
        }

        private static void WriteBytes(string path, byte[] value)
        {
            string directory = Path.GetDirectoryName(path);
            if (!string.IsNullOrEmpty(directory)) Directory.CreateDirectory(directory);
            File.WriteAllBytes(path, value);
        }

        private static RealDrawObservation ReadRealDrawObservation()
        {
            var result = new RealDrawObservation
            {
                BeforeCount = Native.GetRealDrawBeforeCount(),
                AfterCount = Native.GetRealDrawAfterCount(),
                BeforeByteWidth = Native.GetRealDrawBeforeVsCb3ByteWidth(),
                AfterByteWidth = Native.GetRealDrawAfterVsCb3ByteWidth(),
                BeforeValid = Native.GetRealDrawBeforeVsCb3Valid() == 1u,
                AfterValid = Native.GetRealDrawAfterVsCb3Valid() == 1u,
            };
            byte[] before = new byte[RealDrawObservation.VsCb3ByteCount];
            byte[] after = new byte[RealDrawObservation.VsCb3ByteCount];
            uint beforeCopied = Native.CopyRealDrawBeforeVsCb3(before, (uint)before.Length);
            uint afterCopied = Native.CopyRealDrawAfterVsCb3(after, (uint)after.Length);
            result.BeforeBytesCopied = beforeCopied;
            result.AfterBytesCopied = afterCopied;
            if (beforeCopied == before.Length) result.BeforeHex = Hex(before);
            if (afterCopied == after.Length) result.AfterHex = Hex(after);
            result.Passed = result.BeforeCount == 1 && result.AfterCount == 1 &&
                result.BeforeByteWidth == RealDrawObservation.VsCb3ByteCount &&
                result.AfterByteWidth == RealDrawObservation.VsCb3ByteCount &&
                result.BeforeValid && result.AfterValid &&
                beforeCopied == before.Length && afterCopied == after.Length;
            result.Error = result.Passed ? string.Empty :
                "real DrawMesh VS cb3 observation was unavailable or failed closed";
            return result;
        }

        private static string Hex(byte[] bytes)
        {
            var result = new StringBuilder(bytes.Length * 2);
            foreach (byte value in bytes) result.Append(value.ToString("x2", CultureInfo.InvariantCulture));
            return result.ToString();
        }

        private static string RenderReport(Result value, VisualGridData visual)
        {
            bool syntheticGrid = visual != null;
            return "{\n" +
                "  \"schema\": \"endfield.original-m23-dxbc-exact-live.v1\",\n" +
                "  \"status\": \"" + (value.Passed ? "pass" : "fail") + "\",\n" +
                "  \"standalone_only\": true,\n" +
                "  \"production_submission\": false,\n" +
                "  \"graphics_api\": \"" + SystemInfo.graphicsDeviceType + "\",\n" +
                "  \"keyword\": \"" + KeywordName + "\",\n" +
                "  \"vertex_sha256\": \"" + VertexSha256 + "\",\n" +
                "  \"pixel_sha256\": \"" + PixelSha256 + "\",\n" +
                "  \"vertex_stride\": 136,\n" +
                "  \"constant_buffer_float4_counts\": [45,105,104,14,50],\n" +
                "  \"callback_count\": " + value.CallbackCount + ",\n" +
                "  \"unarmed_callback_count\": " + value.UnarmedCallbackCount + ",\n" +
                "  \"platform_blocked_count\": " + value.PlatformBlockedCount + ",\n" +
                "  \"shell_input_observed_count\": " + value.ShellInputObservedCount + ",\n" +
                "  \"blocked_count\": " + value.BlockedCount + ",\n" +
                "  \"vertex_swap_count\": " + value.VertexSwapCount + ",\n" +
                "  \"pixel_swap_count\": " + value.PixelSwapCount + ",\n" +
                "  \"failure_count\": " + value.FailureCount + ",\n" +
                "  \"last_hresult\": " + value.LastResult + ",\n" +
                "  \"render_event_count\": " + value.RenderEventCount + ",\n" +
                "  \"ignored_render_event_count\": " + value.IgnoredRenderEventCount + ",\n" +
                "  \"cleanup_count\": " + value.CleanupCount + ",\n" +
                "  \"cleanup_pending\": " + value.CleanupPending + ",\n" +
                "  \"native_execution_count\": " + value.NativeExecutionCount + ",\n" +
                "  \"exact_shader_bound\": " + Bool(value.ExactShaderBound) + ",\n" +
                "  \"vertex_constant_buffer_mask\": " + value.VertexConstantBufferMask + ",\n" +
                "  \"vertex_shader_resource_mask\": " + value.VertexShaderResourceMask + ",\n" +
                "  \"pixel_constant_buffer_mask\": " + value.PixelConstantBufferMask + ",\n" +
                "  \"pixel_shader_resource_mask\": " + value.PixelShaderResourceMask + ",\n" +
                "  \"pixel_sampler_mask\": " + value.PixelSamplerMask + ",\n" +
                "  \"real_draw_before_count\": " + value.RealDraw.BeforeCount + ",\n" +
                "  \"real_draw_after_count\": " + value.RealDraw.AfterCount + ",\n" +
                "  \"real_draw_before_vs_cb3_byte_width\": " + value.RealDraw.BeforeByteWidth + ",\n" +
                "  \"real_draw_after_vs_cb3_byte_width\": " + value.RealDraw.AfterByteWidth + ",\n" +
                "  \"real_draw_before_vs_cb3_valid\": " + Bool(value.RealDraw.BeforeValid) + ",\n" +
                "  \"real_draw_after_vs_cb3_valid\": " + Bool(value.RealDraw.AfterValid) + ",\n" +
                "  \"real_draw_before_vs_cb3_bytes_copied\": " + value.RealDraw.BeforeBytesCopied + ",\n" +
                "  \"real_draw_after_vs_cb3_bytes_copied\": " + value.RealDraw.AfterBytesCopied + ",\n" +
                "  \"real_draw_before_vs_cb3_hex\": \"" + value.RealDraw.BeforeHex + "\",\n" +
                "  \"real_draw_after_vs_cb3_hex\": \"" + value.RealDraw.AfterHex + "\",\n" +
                "  \"real_draw_observation_passed\": " + Bool(value.RealDraw.Passed) + ",\n" +
                "  \"real_draw_observation_error\": \"" + Escape(value.RealDraw.Error) + "\",\n" +
                "  \"execution_binding_compatible\": " + Bool(value.ExecutionBindingCompatible) + ",\n" +
                "  \"numeric_finite\": " + Bool(value.NumericFinite) + ",\n" +
                "  \"synthetic_grid\": " + Bool(syntheticGrid) + ",\n" +
                "  \"actor_particle_input\": false,\n" +
                "  \"visual_fidelity_claim\": false,\n" +
                "  \"visual_grid_mode\": " + (syntheticGrid ? VisualGridMode.ToString(CultureInfo.InvariantCulture) : "0") + ",\n" +
                "  \"visual_grid_valid\": " + Bool(visual != null && visual.Valid) + ",\n" +
                "  \"visual_grid_config_mask\": " + (visual == null ? "0" : visual.ConfigMask.ToString(CultureInfo.InvariantCulture)) + ",\n" +
                "  \"visual_grid_size\": " + (visual == null ? "0" : visual.Size.ToString(CultureInfo.InvariantCulture)) + ",\n" +
                "  \"visual_grid_float_count\": " + (visual == null ? "0" : visual.FloatCount.ToString(CultureInfo.InvariantCulture)) + ",\n" +
                "  \"visual_grid_finite_pixels\": " + (visual == null ? "0" : visual.FinitePixels.ToString(CultureInfo.InvariantCulture)) + ",\n" +
                "  \"visual_grid_nonzero_pixels\": " + (visual == null ? "0" : visual.NonzeroPixels.ToString(CultureInfo.InvariantCulture)) + ",\n" +
                "  \"visual_grid_rgb_nonzero_pixels\": " + (visual == null ? "0" : visual.RgbNonzeroPixels.ToString(CultureInfo.InvariantCulture)) + ",\n" +
                "  \"visual_grid_alpha_nonzero_pixels\": " + (visual == null ? "0" : visual.AlphaNonzeroPixels.ToString(CultureInfo.InvariantCulture)) + ",\n" +
                "  \"visual_grid_float_sha256\": \"" + Escape(visual == null ? string.Empty : visual.FloatSha256) + "\",\n" +
                "  \"visual_grid_png\": \"" + Escape(visual == null ? string.Empty : visual.PngPath) + "\",\n" +
                "  \"visual_grid_png_encoding\": \"" + Escape(visual == null ? string.Empty : visual.PngEncoding) + "\",\n" +
                "  \"visual_grid_error\": \"" + Escape(visual == null ? string.Empty : visual.Error) + "\",\n" +
                "  \"pixel\": " + RenderColor(value.Pixel) + ",\n" +
                "  \"pixel_sha256\": \"" + value.PixelSha256 + "\",\n" +
                "  \"sentinel_sha256\": \"" + value.SentinelSha256 + "\",\n" +
                "  \"error\": \"" + Escape(value.Error) + "\"\n}\n";
        }

        private static string RenderColor(Color value) => "[" + Number(value.r) + "," + Number(value.g) + "," + Number(value.b) + "," + Number(value.a) + "]";
        private static string Number(float value) => float.IsNaN(value) ? "\"NaN\"" : float.IsPositiveInfinity(value) ? "\"Infinity\"" : float.IsNegativeInfinity(value) ? "\"-Infinity\"" : value.ToString("R", CultureInfo.InvariantCulture);
        private static string Bool(bool value) => value ? "true" : "false";
        private static bool ColorFinite(Color value) => IsFinite(value.r) && IsFinite(value.g) && IsFinite(value.b) && IsFinite(value.a);
        private static bool IsFinite(float value) => !float.IsNaN(value) && !float.IsInfinity(value);
        private static string HashFloatColor(Color value)
        { var values = new[] { value.r, value.g, value.b, value.a }; var bytes = new byte[sizeof(float) * 4]; Buffer.BlockCopy(values, 0, bytes, 0, bytes.Length); using (SHA256 sha = SHA256.Create()) return ToHex(sha.ComputeHash(bytes)); }
        private static string ToHex(byte[] bytes) { var result = new StringBuilder(bytes.Length * 2); foreach (byte value in bytes) result.Append(value.ToString("x2", CultureInfo.InvariantCulture)); return result.ToString(); }
        private static string Escape(string value) => (value ?? string.Empty).Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\r", "\\r").Replace("\n", "\\n");
        private static bool HasArgument(string[] args, string name) { return args != null && args.Contains(name, StringComparer.Ordinal); }
        private static string ReadArgument(string[] args, string name) { for (int i = 0; i + 1 < args.Length; i++) if (string.Equals(args[i], name, StringComparison.Ordinal)) return args[i + 1]; return null; }
        private static void WriteText(string path, string value) { string directory = Path.GetDirectoryName(path); if (!string.IsNullOrEmpty(directory)) Directory.CreateDirectory(directory); File.WriteAllText(path, value, new UTF8Encoding(false)); }
        private static void TryDisarmAndCleanup()
        {
            try
            {
                Native.SetArmed(0);
                IntPtr eventFunction = Native.GetRenderEventFunc();
                if (eventFunction == IntPtr.Zero) return;
                var cleanup = new CommandBuffer { name = "Endfield Original M23 DXBC Cleanup" };
                cleanup.IssuePluginEvent(eventFunction, 3);
                Graphics.ExecuteCommandBuffer(cleanup);
                cleanup.Release();
            }
            catch { }
        }
        private static void Release(RenderTexture value) { if (value == null) return; value.Release(); DisposeUnityObject(value); }
        private static void DisposeUnityObject(UnityEngine.Object value) { if (value == null) return; if (Application.isPlaying) Destroy(value); else DestroyImmediate(value); }

        private sealed class RealDrawObservation
        {
            internal const int VsCb3ByteCount = 14 * 16;
            internal uint BeforeCount, AfterCount, BeforeByteWidth, AfterByteWidth;
            internal uint BeforeBytesCopied, AfterBytesCopied;
            internal bool BeforeValid, AfterValid, Passed;
            internal string BeforeHex = string.Empty, AfterHex = string.Empty, Error = string.Empty;
            internal static RealDrawObservation Empty => new RealDrawObservation
            { Error = "real DrawMesh VS cb3 observation was not captured" };
        }

        private sealed class VisualGridData
        {
            internal bool Valid;
            internal uint ConfigMask, Size, FinitePixels, NonzeroPixels, RgbNonzeroPixels, AlphaNonzeroPixels;
            internal int FloatCount;
            internal string FloatSha256 = string.Empty, PngPath = string.Empty, PngEncoding = string.Empty, Error = string.Empty;
        }

        [StructLayout(LayoutKind.Sequential, Pack = 1)]
        private struct M23VertexStream0
        {
            internal Vector3 Position, Normal;
            internal Vector4 Tangent;
            internal static M23VertexStream0 Make(Vector3 position) => new M23VertexStream0
            { Position = position, Normal = Vector3.forward, Tangent = new Vector4(1, 0, 0, 1) };
        }

        [StructLayout(LayoutKind.Sequential, Pack = 1)]
        private struct M23VertexStream1
        {
            internal Vector4 Color, Texcoord0, Texcoord1, Texcoord4;
            internal static M23VertexStream1 Make(Vector4 uv) => new M23VertexStream1
            { Color = Vector4.one, Texcoord0 = uv, Texcoord1 = Vector4.zero, Texcoord4 = Vector4.zero };
        }

        [StructLayout(LayoutKind.Sequential, Pack = 1)]
        private struct M23VertexStream2
        {
            internal Vector4 BlendWeights;
            internal uint BlendIndex0, BlendIndex1, BlendIndex2, BlendIndex3;
            internal static M23VertexStream2 Default() => new M23VertexStream2
            { BlendWeights = new Vector4(1, 0, 0, 0) };
        }

        private readonly struct Result
        {
            internal readonly bool Passed, ExactShaderBound, ExecutionBindingCompatible, NumericFinite;
            internal readonly string Error, PixelSha256, SentinelSha256;
            internal readonly uint CallbackCount, UnarmedCallbackCount, PlatformBlockedCount, ShellInputObservedCount, BlockedCount, VertexSwapCount, PixelSwapCount, FailureCount, RenderEventCount, IgnoredRenderEventCount, CleanupCount, CleanupPending, NativeExecutionCount, VertexConstantBufferMask, VertexShaderResourceMask, PixelConstantBufferMask, PixelShaderResourceMask, PixelSamplerMask;
            internal readonly int LastResult;
            internal readonly Color Pixel;
            internal readonly RealDrawObservation RealDraw;
            internal Result(bool passed, string error, uint callback, uint unarmed, uint platformBlocked, uint shellInputObserved, uint blocked, uint vertexSwap, uint pixelSwap, uint failures, int lastResult, uint events, uint ignored, uint nativeExecution, uint cleanupCount, uint cleanupPending, bool exactBound, uint vsCb, uint vsSrv, uint psCb, uint psSrv, uint psSampler, bool finite, Color pixel, string pixelSha, string sentinelSha, bool execution, RealDrawObservation realDraw)
            { Passed = passed; Error = error ?? string.Empty; CallbackCount = callback; UnarmedCallbackCount = unarmed; PlatformBlockedCount = platformBlocked; ShellInputObservedCount = shellInputObserved; BlockedCount = blocked; VertexSwapCount = vertexSwap; PixelSwapCount = pixelSwap; FailureCount = failures; LastResult = lastResult; RenderEventCount = events; IgnoredRenderEventCount = ignored; NativeExecutionCount = nativeExecution; CleanupCount = cleanupCount; CleanupPending = cleanupPending; ExactShaderBound = exactBound; VertexConstantBufferMask = vsCb; VertexShaderResourceMask = vsSrv; PixelConstantBufferMask = psCb; PixelShaderResourceMask = psSrv; PixelSamplerMask = psSampler; NumericFinite = finite; Pixel = pixel; PixelSha256 = pixelSha; SentinelSha256 = sentinelSha; ExecutionBindingCompatible = execution; RealDraw = realDraw ?? RealDrawObservation.Empty; }
            internal static Result Failed(string error) => new Result(false, error, 0, 0, 0, 0, 0, 0, 0, 0, unchecked((int)0x80004005), 0, 0, 0, 0, 0, false, 0, 0, 0, 0, 0, false, Color.clear, string.Empty, string.Empty, false, RealDrawObservation.Empty);
        }

        private static class Native
        {
            private const string Library = "OriginalM23DxbcExactPlugin";
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetContractVersion", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetContractVersion();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetPluginLoadCount", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetPluginLoadCount();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetConfigureCount", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetConfigureCount();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeSetVisualMode", CallingConvention = CallingConvention.Cdecl)] internal static extern uint SetVisualMode(uint mode);
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetVisualMode", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetVisualMode();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeSetArmed", CallingConvention = CallingConvention.Cdecl)] internal static extern uint SetArmed(uint armed);
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetArmed", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetArmed();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetCallbackCount", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetCallbackCount();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetUnarmedCallbackCount", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetUnarmedCallbackCount();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetPlatformBlockedCount", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetPlatformBlockedCount();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetShellInputObservedCount", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetShellInputObservedCount();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetBlockedCount", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetBlockedCount();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetVertexSwapCount", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetVertexSwapCount();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetPixelSwapCount", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetPixelSwapCount();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetFailureCount", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetFailureCount();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetLastResult", CallingConvention = CallingConvention.Cdecl)] internal static extern int GetLastResult();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetRenderEventFunc", CallingConvention = CallingConvention.Cdecl)] internal static extern IntPtr GetRenderEventFunc();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetRenderEventCount", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetRenderEventCount();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetIgnoredRenderEventCount", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetIgnoredRenderEventCount();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetCleanupCount", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetCleanupCount();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetCleanupPending", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetCleanupPending();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetNativeExecutionCount", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetNativeExecutionCount();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetExactShaderBound", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetExactShaderBound();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetVertexConstantBufferMask", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetVertexConstantBufferMask();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetVertexShaderResourceMask", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetVertexShaderResourceMask();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetPixelConstantBufferMask", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetPixelConstantBufferMask();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetPixelShaderResourceMask", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetPixelShaderResourceMask();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetPixelSamplerMask", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetPixelSamplerMask();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetRealDrawBeforeCount", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetRealDrawBeforeCount();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetRealDrawAfterCount", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetRealDrawAfterCount();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetRealDrawBeforeVsCb3Valid", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetRealDrawBeforeVsCb3Valid();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetRealDrawAfterVsCb3Valid", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetRealDrawAfterVsCb3Valid();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetRealDrawBeforeVsCb3ByteWidth", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetRealDrawBeforeVsCb3ByteWidth();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetRealDrawAfterVsCb3ByteWidth", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetRealDrawAfterVsCb3ByteWidth();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeCopyRealDrawBeforeVsCb3", CallingConvention = CallingConvention.Cdecl)] internal static extern uint CopyRealDrawBeforeVsCb3([Out] byte[] outputBytes, uint outputByteCount);
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeCopyRealDrawAfterVsCb3", CallingConvention = CallingConvention.Cdecl)] internal static extern uint CopyRealDrawAfterVsCb3([Out] byte[] outputBytes, uint outputByteCount);
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetVisualGridValid", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetVisualGridValid();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetVisualConfigMask", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetVisualConfigMask();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetVisualGridSize", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetVisualGridSize();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetVisualGridFinitePixels", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetVisualGridFinitePixels();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetVisualGridNonzeroPixels", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetVisualGridNonzeroPixels();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetVisualGridRgbNonzeroPixels", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetVisualGridRgbNonzeroPixels();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeGetVisualGridAlphaNonzeroPixels", CallingConvention = CallingConvention.Cdecl)] internal static extern uint GetVisualGridAlphaNonzeroPixels();
            [DllImport(Library, EntryPoint = "EndfieldOriginalM23DxbcBridgeCopyVisualGrid", CallingConvention = CallingConvention.Cdecl)] internal static extern uint CopyVisualGrid([Out] float[] outputFloats, uint outputFloatCount);
        }
    }
}
