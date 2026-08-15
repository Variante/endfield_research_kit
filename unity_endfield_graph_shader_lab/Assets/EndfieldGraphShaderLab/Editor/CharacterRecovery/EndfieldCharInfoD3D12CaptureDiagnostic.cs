using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Executes an isolated D3D12 replay draw of the recovered Character Info
    /// CharEffect/trail.  This is deliberately a diagnostic, not a retail
    /// capture: Unity's CommandBuffer.DrawRenderer is the draw source and the
    /// report labels all admission/readback facts as replay evidence.
    /// </summary>
    public static class EndfieldCharInfoD3D12CaptureDiagnostic
    {
        private const string PrefabPath =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/CharInfo/Effects/CharEffect/Prefabs/CharEffect.prefab";
        private const string ShaderName =
            "Hidden/Endfield/Recovered/Zhuangfy/VFXRefractMRT";
        private const string OutputArgument = "-endfield-charinfo-d3d12-output";
        private const int Width = 64;
        private const int Height = 64;

        private const GraphicsFormat SceneColorFormat =
            GraphicsFormat.B10G11R11_UFloatPack32;
        private const GraphicsFormat SceneMvFormat =
            GraphicsFormat.A2B10G10R10_UNormPack32;
        private const GraphicsFormat DepthFormat = GraphicsFormat.D32_SFloat;

        [MenuItem("Endfield/Character Recovery/Capture CharInfo D3D12 Diagnostic")]
        public static void CaptureAndWrite()
        {
            string outputPath = ReadArgument(
                Environment.GetCommandLineArgs(), OutputArgument);
            if (string.IsNullOrWhiteSpace(outputPath))
            {
                outputPath = Path.Combine(
                    Directory.GetCurrentDirectory(),
                    "scratch",
                    "character_recovery",
                    "charinfo_d3d12_capture",
                    "diagnostic.json");
            }

            DiagnosticResult result;
            try
            {
                result = Capture();
            }
            catch (Exception exception)
            {
                result = DiagnosticResult.Failed(
                    exception.GetType().FullName + ": " + exception.Message);
            }

            WriteText(outputPath, Render(result));
            if (result.Passed)
            {
                Debug.Log(
                    "[Endfield CharInfo] D3D12 replay capture diagnostic PASS: " +
                    outputPath);
                EditorApplication.Exit(0);
            }
            else
            {
                Debug.LogError(
                    "[Endfield CharInfo] D3D12 replay capture diagnostic FAIL: " +
                    result.Error + "; report=" + outputPath);
                EditorApplication.Exit(17);
            }
        }

        private static DiagnosticResult Capture()
        {
            GraphicsDeviceType api = SystemInfo.graphicsDeviceType;
            if (api != GraphicsDeviceType.Direct3D12)
                throw new InvalidOperationException(
                    "D3D12 is required; actual=" + api + ".");

            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
            if (prefab == null)
                throw new FileNotFoundException("CharEffect prefab is missing.", PrefabPath);

            GameObject instance = null;
            GameObject cameraObject = null;
            RenderTexture sceneColor = null;
            RenderTexture sceneMv = null;
            RenderTexture depth = null;
            RenderTexture sceneSource = null;
            try
            {
                instance = UnityEngine.Object.Instantiate(prefab);
                instance.name = "CharEffect__D3D12ReplayDiagnostic";
                instance.transform.position = Vector3.zero;
                instance.transform.rotation = Quaternion.identity;
                instance.transform.localScale = Vector3.one;
                instance.SetActive(true);

                EndfieldRecoveredParticleEffectSource marker =
                    instance.GetComponent<EndfieldRecoveredParticleEffectSource>();
                if (marker == null)
                    throw new InvalidOperationException("CharEffect source marker is missing.");

                ParticleSystem[] systems =
                    instance.GetComponentsInChildren<ParticleSystem>(true);
                ParticleSystemRenderer[] renderers =
                    instance.GetComponentsInChildren<ParticleSystemRenderer>(true);
                ParticleSystemRenderer trail = renderers.SingleOrDefault(value =>
                    value != null && value.enabled);
                if (trail == null)
                    throw new InvalidOperationException("No enabled CharEffect/trail renderer.");
                Material material = trail.sharedMaterials.FirstOrDefault();
                if (material == null || material.shader == null ||
                    material.shader.name != ShaderName)
                {
                    throw new InvalidOperationException(
                        "CharEffect/trail material is not the recovered VFXRefract shader.");
                }

                Camera camera = MakeCamera(out cameraObject);
                foreach (ParticleSystem system in systems)
                {
                    system.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
                    system.Simulate(0.125f, true, true, true);
                }

                List<ParticleSnapshot> survivors = CaptureSurvivors(systems);
                DrawAdmission admission = CaptureAdmission(
                    marker, trail, material, camera);
                MaterialSnapshot materialState = CaptureMaterial(material);

                sceneColor = CreateTarget(SceneColorFormat, "CharInfo SceneColor");
                sceneMv = CreateTarget(SceneMvFormat, "CharInfo SceneMV");
                depth = CreateDepthTarget();
                sceneSource = CreateSceneSource();

                RenderReplay(
                    camera,
                    trail,
                    material,
                    sceneColor,
                    sceneMv,
                    depth,
                    sceneSource);

                ReadbackSnapshot colorReadback = Readback(sceneColor);
                ReadbackSnapshot mvReadback = Readback(sceneMv);
                bool drawChanged = colorReadback.NonZero || mvReadback.NonZero;
                bool mrtChanged = colorReadback.ByteCount > 0 && mvReadback.ByteCount > 0;
                bool passed = admission.Admitted &&
                    sceneColor.IsCreated() && sceneMv.IsCreated() &&
                    colorReadback.Succeeded && mvReadback.Succeeded &&
                    drawChanged && mrtChanged;

                return new DiagnosticResult(
                    passed,
                    passed ? string.Empty : "replay draw or two-MRT readback gate failed",
                    api,
                    admission,
                    materialState,
                    Describe(sceneColor),
                    Describe(sceneMv),
                    Describe(depth),
                    Describe(sceneSource),
                    survivors,
                    colorReadback,
                    mvReadback,
                    drawChanged,
                    mrtChanged);
            }
            finally
            {
                Release(sceneColor);
                Release(sceneMv);
                Release(depth);
                Release(sceneSource);
                if (cameraObject != null)
                    UnityEngine.Object.DestroyImmediate(cameraObject);
                if (instance != null)
                    UnityEngine.Object.DestroyImmediate(instance);
            }
        }

        private static Camera MakeCamera(out GameObject cameraObject)
        {
            cameraObject = new GameObject("CharInfoD3D12ReplayCamera");
            Camera camera = cameraObject.AddComponent<Camera>();
            camera.transform.position = new Vector3(0f, 0f, -5f);
            camera.transform.rotation = Quaternion.identity;
            camera.fieldOfView = 35f;
            camera.nearClipPlane = 0.01f;
            camera.farClipPlane = 100f;
            camera.aspect = (float)Width / Height;
            return camera;
        }

        private static DrawAdmission CaptureAdmission(
            EndfieldRecoveredParticleEffectSource marker,
            ParticleSystemRenderer renderer,
            Material material,
            Camera camera)
        {
            Bounds bounds = renderer.bounds;
            Plane[] planes = GeometryUtility.CalculateFrustumPlanes(camera);
            bool inFrustum = GeometryUtility.TestPlanesAABB(planes, bounds);
            bool materialGate = material.shader != null &&
                material.shader.name == ShaderName &&
                material.renderQueue == 3000 &&
                material.shaderKeywords.SequenceEqual(
                    new[] { "_USE_RBOFFSET" }, StringComparer.Ordinal) &&
                material.HasProperty("_RefractTex") &&
                material.GetTexture("_RefractTex") != null;
            bool markerGate = marker.contractSchema ==
                    EndfieldRecoveredCharEffectSpawner.CharInfoContractSchema &&
                marker.particleNodes != null && marker.particleNodes.Length == 2;
            bool admitted = renderer.enabled && !renderer.forceRenderingOff &&
                renderer.sharedMaterials.Length == 1 && materialGate &&
                markerGate && inFrustum;
            return new DrawAdmission(
                admitted,
                renderer.enabled,
                renderer.forceRenderingOff,
                renderer.sharedMaterials.Length,
                materialGate,
                markerGate,
                inFrustum,
                "unity_command_buffer_drawrenderer_replay_not_retail_capture");
        }

        private static MaterialSnapshot CaptureMaterial(Material material)
        {
            return new MaterialSnapshot(
                material.shader != null ? material.shader.name : string.Empty,
                material.renderQueue,
                material.shaderKeywords ?? Array.Empty<string>(),
                material.FindPass("Refraction"),
                "Distortion",
                material.HasProperty("_SrcBlend") ? material.GetFloat("_SrcBlend") : -1f,
                material.HasProperty("_DstBlend") ? material.GetFloat("_DstBlend") : -1f,
                material.HasProperty("_MVSrcColorBlend") ?
                    material.GetFloat("_MVSrcColorBlend") : -1f,
                material.HasProperty("_MVDstColorBlend") ?
                    material.GetFloat("_MVDstColorBlend") : -1f,
                material.HasProperty("_ZTest") ? material.GetFloat("_ZTest") : -1f,
                material.HasProperty("_ZWrite") ? material.GetFloat("_ZWrite") : -1f,
                material.HasProperty("_CullMode") ? material.GetFloat("_CullMode") : -1f,
                material.HasProperty("_RBOffset") ? material.GetVector("_RBOffset") : Vector4.zero,
                material.HasProperty("_RBMainColorMask") ?
                    material.GetColor("_RBMainColorMask") : Color.clear,
                material.HasProperty("_RBOffsetColorMask") ?
                    material.GetColor("_RBOffsetColorMask") : Color.clear,
                material.HasProperty("_RBIntensity") ? material.GetFloat("_RBIntensity") : -1f,
                material.HasProperty("_RefractUseRBOffset") ?
                    material.GetFloat("_RefractUseRBOffset") : -1f);
        }

        private static void RenderReplay(
            Camera camera,
            Renderer renderer,
            Material material,
            RenderTexture sceneColor,
            RenderTexture sceneMv,
            RenderTexture depth,
            RenderTexture sceneSource)
        {
            var command = new CommandBuffer
            {
                name = "Endfield CharInfo D3D12 replay diagnostic"
            };
            try
            {
                RenderTargetIdentifier[] colors =
                {
                    new RenderTargetIdentifier(sceneColor),
                    new RenderTargetIdentifier(sceneMv),
                };
                command.SetRenderTarget(
                    colors,
                    new RenderTargetIdentifier(depth));
                command.ClearRenderTarget(true, true, Color.clear, 1f);
                command.SetViewProjectionMatrices(
                    camera.worldToCameraMatrix,
                    camera.projectionMatrix);
                command.SetGlobalTexture(
                    Shader.PropertyToID("_SceneColorTexture"), sceneSource);
                command.SetGlobalFloat(
                    Shader.PropertyToID("_EndfieldSceneMVMRTReady"), 1f);
                command.SetGlobalFloat(
                    Shader.PropertyToID("_EndfieldRecoveredVFXGlobalsReady"), 1f);
                command.SetGlobalVector(
                    Shader.PropertyToID("_VFXParams0"),
                    new Vector4(0f, 0f, 0f, 0.125f));
                command.SetGlobalFloat(Shader.PropertyToID("_GlobalMipBias"), 0f);
                int pass = material.FindPass("Refraction");
                if (pass < 0)
                    throw new InvalidOperationException("VFXRefract Refraction pass is missing.");
                command.DrawRenderer(renderer, material, 0, pass);
                Graphics.ExecuteCommandBuffer(command);
            }
            finally
            {
                command.Release();
            }
        }

        private static List<ParticleSnapshot> CaptureSurvivors(
            ParticleSystem[] systems)
        {
            var result = new List<ParticleSnapshot>(systems.Length);
            foreach (ParticleSystem system in systems)
            {
                int count = system.particleCount;
                ParticleSystem.Particle[] particles =
                    new ParticleSystem.Particle[Math.Max(1, count)];
                int copied = count == 0 ? 0 : system.GetParticles(particles);
                ParticleSystem.Particle first = copied == 0
                    ? default(ParticleSystem.Particle)
                    : particles[0];
                result.Add(new ParticleSnapshot(
                    system.name,
                    count,
                    copied,
                    system.isPlaying,
                    system.isEmitting,
                    first.position,
                    first.velocity,
                    first.remainingLifetime,
                    first.startLifetime,
                    first.startSize,
                    first.startColor));
            }
            return result;
        }

        private static RenderTexture CreateTarget(GraphicsFormat format, string name)
        {
            if (!SystemInfo.IsFormatSupported(format, FormatUsage.Render))
                throw new InvalidOperationException(format + " is not render-supported.");
            var descriptor = new RenderTextureDescriptor(Width, Height)
            {
                graphicsFormat = format,
                depthStencilFormat = GraphicsFormat.None,
                depthBufferBits = 0,
                dimension = TextureDimension.Tex2D,
                volumeDepth = 1,
                msaaSamples = 1,
                bindMS = false,
                useMipMap = false,
                autoGenerateMips = false,
                enableRandomWrite = false,
                sRGB = false,
                useDynamicScale = false,
            };
            var target = new RenderTexture(descriptor)
            {
                name = name,
                filterMode = FilterMode.Point,
                wrapMode = TextureWrapMode.Clamp,
                anisoLevel = 0,
                hideFlags = HideFlags.HideAndDontSave,
            };
            if (!target.Create() || !target.IsCreated())
                throw new InvalidOperationException("Could not create " + name + ".");
            return target;
        }

        private static RenderTexture CreateDepthTarget()
        {
            var descriptor = new RenderTextureDescriptor(Width, Height)
            {
                graphicsFormat = GraphicsFormat.None,
                depthStencilFormat = DepthFormat,
                depthBufferBits = 32,
                dimension = TextureDimension.Tex2D,
                volumeDepth = 1,
                msaaSamples = 1,
                bindMS = false,
                useMipMap = false,
                autoGenerateMips = false,
                enableRandomWrite = false,
                sRGB = false,
            };
            var target = new RenderTexture(descriptor)
            {
                name = "CharInfo Depth",
                hideFlags = HideFlags.HideAndDontSave,
            };
            if (!target.Create() || !target.IsCreated())
                throw new InvalidOperationException("Could not create depth target.");
            return target;
        }

        private static RenderTexture CreateSceneSource()
        {
            var descriptor = new RenderTextureDescriptor(Width, Height)
            {
                graphicsFormat = GraphicsFormat.R16G16B16A16_SFloat,
                depthStencilFormat = GraphicsFormat.None,
                depthBufferBits = 0,
                dimension = TextureDimension.Tex2D,
                volumeDepth = 1,
                msaaSamples = 1,
                bindMS = false,
                useMipMap = false,
                autoGenerateMips = false,
                enableRandomWrite = false,
                sRGB = false,
            };
            var source = new RenderTexture(descriptor)
            {
                name = "CharInfo SceneColor source (replay fixture)",
                filterMode = FilterMode.Point,
                wrapMode = TextureWrapMode.Clamp,
                hideFlags = HideFlags.HideAndDontSave,
            };
            if (!source.Create() || !source.IsCreated())
                throw new InvalidOperationException("Could not create scene source.");
            var command = new CommandBuffer { name = "CharInfo scene source clear" };
            command.SetRenderTarget(source);
            command.ClearRenderTarget(false, true, new Color(0.2f, 0.35f, 0.5f, 1f));
            Graphics.ExecuteCommandBuffer(command);
            command.Release();
            return source;
        }

        private static ReadbackSnapshot Readback(RenderTexture target)
        {
            AsyncGPUReadbackRequest request = AsyncGPUReadback.Request(target, 0);
            request.WaitForCompletion();
            if (request.hasError)
                return ReadbackSnapshot.Failed();
            byte[] bytes = request.GetData<byte>().ToArray();
            bool nonZero = bytes.Any(value => value != 0);
            return new ReadbackSnapshot(
                true,
                bytes.Length,
                nonZero,
                Hash(bytes));
        }

        private static DescriptorSnapshot Describe(RenderTexture target)
        {
            RenderTextureDescriptor descriptor = target.descriptor;
            return new DescriptorSnapshot(
                descriptor.width,
                descriptor.height,
                descriptor.graphicsFormat.ToString(),
                descriptor.depthStencilFormat.ToString(),
                descriptor.depthBufferBits,
                descriptor.dimension.ToString(),
                descriptor.volumeDepth,
                descriptor.msaaSamples,
                descriptor.bindMS,
                descriptor.useMipMap,
                descriptor.autoGenerateMips,
                descriptor.enableRandomWrite,
                descriptor.sRGB,
                descriptor.useDynamicScale,
                target.filterMode.ToString(),
                target.wrapMode.ToString(),
                target.anisoLevel);
        }

        private static string Render(DiagnosticResult result)
        {
            var builder = new StringBuilder();
            builder.AppendLine("{");
            Append(builder, "schema", "endfield.charinfo-d3d12-replay-diagnostic.v1", true);
            Append(builder, "status", result.Passed ? "pass" : "fail", true);
            Append(builder, "error", result.Error, true);
            Append(builder, "actualGraphicsApi", result.Api.ToString(), true);
            Append(builder, "captureKind", "unity_command_buffer_replay_not_retail_capture", true);
            Append(builder, "retailCaptureClaim", "false", true, false);
            AppendObject(builder, "drawAdmission", result.Admission, true);
            AppendObject(builder, "materialState", result.MaterialState, true);
            AppendObject(builder, "sceneColorDescriptor", result.SceneColor, true);
            AppendObject(builder, "sceneMvDescriptor", result.SceneMv, true);
            AppendObject(builder, "depthDescriptor", result.Depth, true);
            AppendObject(builder, "sceneColorSourceDescriptor", result.SceneSource, true);
            AppendArray(builder, "particleSurvivors", result.Survivors, true);
            AppendObject(builder, "sceneColorReadback", result.ColorReadback, true);
            AppendObject(builder, "sceneMvReadback", result.MvReadback, true);
            Append(builder, "replayDrawChangedAnyTarget", result.DrawChanged, true);
            Append(builder, "replayMrtChangedBothTargets", result.MrtChanged, false);
            builder.AppendLine("}");
            return builder.ToString();
        }

        private static void AppendObject(
            StringBuilder builder, string name, object value, bool comma)
        {
            AppendRaw(builder, name, RenderObject(value), comma);
        }

        private static void AppendArray(
            StringBuilder builder, string name, IEnumerable<ParticleSnapshot> values, bool comma)
        {
            string[] rows = values.Select(value => RenderObject(value)).ToArray();
            AppendRaw(builder, name, "[" + string.Join(",", rows) + "]", comma);
        }

        private static string RenderObject(object value)
        {
            if (value is DrawAdmission admission)
            {
                return "{\"admitted\":" + Bool(admission.Admitted) +
                    ",\"rendererEnabled\":" + Bool(admission.RendererEnabled) +
                    ",\"forceRenderingOff\":" + Bool(admission.ForceRenderingOff) +
                    ",\"materialCount\":" + admission.MaterialCount +
                    ",\"materialGate\":" + Bool(admission.MaterialGate) +
                    ",\"markerGate\":" + Bool(admission.MarkerGate) +
                    ",\"frustumIntersects\":" + Bool(admission.FrustumIntersects) +
                    ",\"drawSource\":\"" + Escape(admission.DrawSource) + "\"}";
            }
            if (value is DescriptorSnapshot descriptor)
            {
                return "{\"width\":" + descriptor.Width +
                    ",\"height\":" + descriptor.Height +
                    ",\"graphicsFormat\":\"" + Escape(descriptor.GraphicsFormat) +
                    "\",\"depthStencilFormat\":\"" + Escape(descriptor.DepthStencilFormat) +
                    "\",\"depthBufferBits\":" + descriptor.DepthBufferBits +
                    ",\"dimension\":\"" + Escape(descriptor.Dimension) +
                    "\",\"volumeDepth\":" + descriptor.VolumeDepth +
                    ",\"msaaSamples\":" + descriptor.MsaaSamples +
                    ",\"bindMS\":" + Bool(descriptor.BindMs) +
                    ",\"useMipMap\":" + Bool(descriptor.UseMipMap) +
                    ",\"autoGenerateMips\":" + Bool(descriptor.AutoGenerateMips) +
                    ",\"enableRandomWrite\":" + Bool(descriptor.EnableRandomWrite) +
                    ",\"sRGB\":" + Bool(descriptor.Srgb) +
                    ",\"useDynamicScale\":" + Bool(descriptor.UseDynamicScale) +
                    ",\"filterMode\":\"" + Escape(descriptor.FilterMode) +
                    "\",\"wrapMode\":\"" + Escape(descriptor.WrapMode) +
                    "\",\"anisoLevel\":" + descriptor.AnisoLevel + "}";
            }
            if (value is MaterialSnapshot material)
            {
                return "{\"shader\":\"" + Escape(material.Shader) +
                    "\",\"renderQueue\":" + material.RenderQueue +
                    ",\"keywords\":[" + string.Join(",", material.Keywords.Select(
                        keyword => "\"" + Escape(keyword) + "\"")) +
                    "],\"refractionPassIndex\":" + material.RefractionPassIndex +
                    ",\"expectedLightMode\":\"" + Escape(material.ExpectedLightMode) +
                    "\",\"srcBlend\":" + Number(material.SrcBlend) +
                    ",\"dstBlend\":" + Number(material.DstBlend) +
                    ",\"mvSrcColorBlend\":" + Number(material.MvSrcColorBlend) +
                    ",\"mvDstColorBlend\":" + Number(material.MvDstColorBlend) +
                    ",\"zTest\":" + Number(material.ZTest) +
                    ",\"zWrite\":" + Number(material.ZWrite) +
                    ",\"cullMode\":" + Number(material.CullMode) +
                    ",\"rbOffset\":" + Vector(material.RbOffset) +
                    ",\"rbMainColorMask\":" + ColorValue(material.RbMainColorMask) +
                    ",\"rbOffsetColorMask\":" + ColorValue(material.RbOffsetColorMask) +
                    ",\"rbIntensity\":" + Number(material.RbIntensity) +
                    ",\"refractUseRbOffset\":" + Number(material.RefractUseRbOffset) + "}";
            }
            if (value is ParticleSnapshot particle)
            {
                return "{\"system\":\"" + Escape(particle.System) +
                    "\",\"particleCount\":" + particle.ParticleCount +
                    ",\"copiedCount\":" + particle.CopiedCount +
                    ",\"isPlaying\":" + Bool(particle.IsPlaying) +
                    ",\"isEmitting\":" + Bool(particle.IsEmitting) +
                    ",\"firstPosition\":" + Vector(particle.FirstPosition) +
                    ",\"firstVelocity\":" + Vector(particle.FirstVelocity) +
                    ",\"firstRemainingLifetime\":" + Number(particle.RemainingLifetime) +
                    ",\"firstStartLifetime\":" + Number(particle.StartLifetime) +
                    ",\"firstStartSize\":" + Number(particle.StartSize) +
                    ",\"firstStartColor\":" + ColorValue(particle.StartColor) + "}";
            }
            if (value is ReadbackSnapshot readback)
            {
                return "{\"succeeded\":" + Bool(readback.Succeeded) +
                    ",\"byteCount\":" + readback.ByteCount +
                    ",\"nonZero\":" + Bool(readback.NonZero) +
                    ",\"sha256\":\"" + Escape(readback.Sha256) + "\"}";
            }
            return "null";
        }

        private static void Append(
            StringBuilder builder, string name, string value, bool comma,
            bool quote = true)
        {
            AppendRaw(builder, name, quote ? "\"" + Escape(value) + "\"" : value, comma);
        }

        private static void Append(
            StringBuilder builder, string name, bool value, bool comma)
        {
            AppendRaw(builder, name, Bool(value), comma);
        }

        private static void AppendRaw(
            StringBuilder builder, string name, string value, bool comma)
        {
            builder.Append("  \"").Append(Escape(name)).Append("\":").Append(value);
            if (comma)
                builder.Append(',');
            builder.AppendLine();
        }

        private static string Vector(Vector3 value) =>
            "[" + Number(value.x) + "," + Number(value.y) + "," + Number(value.z) + "]";

        private static string ColorValue(Color32 value) =>
            "[" + value.r + "," + value.g + "," + value.b + "," + value.a + "]";

        private static string ColorValue(Color value) =>
            "[" + Number(value.r) + "," + Number(value.g) + "," +
            Number(value.b) + "," + Number(value.a) + "]";

        private static string Number(float value) =>
            value.ToString("R", CultureInfo.InvariantCulture);

        private static string Bool(bool value) => value ? "true" : "false";

        private static string Hash(byte[] bytes)
        {
            using (SHA256 sha = SHA256.Create())
                return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-", "");
        }

        private static string Escape(string value) =>
            (value ?? string.Empty).Replace("\\", "\\\\").Replace("\"", "\\\"")
                .Replace("\r", "\\r").Replace("\n", "\\n");

        private static string ReadArgument(string[] args, string name)
        {
            for (int index = 0; index + 1 < args.Length; index++)
                if (string.Equals(args[index], name, StringComparison.OrdinalIgnoreCase))
                    return args[index + 1];
            return null;
        }

        private static void Release(RenderTexture texture)
        {
            if (texture == null)
                return;
            if (texture.IsCreated())
                texture.Release();
            UnityEngine.Object.DestroyImmediate(texture);
        }

        private static void WriteText(string path, string text)
        {
            string directory = Path.GetDirectoryName(Path.GetFullPath(path));
            if (!string.IsNullOrEmpty(directory))
                Directory.CreateDirectory(directory);
            File.WriteAllText(path, text, new UTF8Encoding(false));
        }

        private sealed class DiagnosticResult
        {
            public readonly bool Passed;
            public readonly string Error;
            public readonly GraphicsDeviceType Api;
            public readonly DrawAdmission Admission;
            public readonly MaterialSnapshot MaterialState;
            public readonly DescriptorSnapshot SceneColor;
            public readonly DescriptorSnapshot SceneMv;
            public readonly DescriptorSnapshot Depth;
            public readonly DescriptorSnapshot SceneSource;
            public readonly List<ParticleSnapshot> Survivors;
            public readonly ReadbackSnapshot ColorReadback;
            public readonly ReadbackSnapshot MvReadback;
            public readonly bool DrawChanged;
            public readonly bool MrtChanged;

            public DiagnosticResult(
                bool passed, string error, GraphicsDeviceType api,
                DrawAdmission admission, MaterialSnapshot materialState,
                DescriptorSnapshot sceneColor,
                DescriptorSnapshot sceneMv, DescriptorSnapshot depth,
                DescriptorSnapshot sceneSource, List<ParticleSnapshot> survivors,
                ReadbackSnapshot colorReadback, ReadbackSnapshot mvReadback,
                bool drawChanged, bool mrtChanged)
            {
                Passed = passed;
                Error = error;
                Api = api;
                Admission = admission;
                MaterialState = materialState;
                SceneColor = sceneColor;
                SceneMv = sceneMv;
                Depth = depth;
                SceneSource = sceneSource;
                Survivors = survivors;
                ColorReadback = colorReadback;
                MvReadback = mvReadback;
                DrawChanged = drawChanged;
                MrtChanged = mrtChanged;
            }

            public static DiagnosticResult Failed(string error) =>
                new DiagnosticResult(
                    false, error, SystemInfo.graphicsDeviceType,
                    default(DrawAdmission), default(MaterialSnapshot),
                    default(DescriptorSnapshot),
                    default(DescriptorSnapshot), default(DescriptorSnapshot),
                    default(DescriptorSnapshot), new List<ParticleSnapshot>(),
                    ReadbackSnapshot.Failed(), ReadbackSnapshot.Failed(), false, false);
        }

        private readonly struct DrawAdmission
        {
            public readonly bool Admitted;
            public readonly bool RendererEnabled;
            public readonly bool ForceRenderingOff;
            public readonly int MaterialCount;
            public readonly bool MaterialGate;
            public readonly bool MarkerGate;
            public readonly bool FrustumIntersects;
            public readonly string DrawSource;

            public DrawAdmission(
                bool admitted, bool rendererEnabled, bool forceRenderingOff,
                int materialCount, bool materialGate, bool markerGate,
                bool frustumIntersects, string drawSource)
            {
                Admitted = admitted;
                RendererEnabled = rendererEnabled;
                ForceRenderingOff = forceRenderingOff;
                MaterialCount = materialCount;
                MaterialGate = materialGate;
                MarkerGate = markerGate;
                FrustumIntersects = frustumIntersects;
                DrawSource = drawSource;
            }
        }

        private readonly struct DescriptorSnapshot
        {
            public readonly int Width;
            public readonly int Height;
            public readonly string GraphicsFormat;
            public readonly string DepthStencilFormat;
            public readonly int DepthBufferBits;
            public readonly string Dimension;
            public readonly int VolumeDepth;
            public readonly int MsaaSamples;
            public readonly bool BindMs;
            public readonly bool UseMipMap;
            public readonly bool AutoGenerateMips;
            public readonly bool EnableRandomWrite;
            public readonly bool Srgb;
            public readonly bool UseDynamicScale;
            public readonly string FilterMode;
            public readonly string WrapMode;
            public readonly int AnisoLevel;

            public DescriptorSnapshot(
                int width, int height, string graphicsFormat,
                string depthStencilFormat, int depthBufferBits, string dimension,
                int volumeDepth, int msaaSamples, bool bindMs, bool useMipMap,
                bool autoGenerateMips, bool enableRandomWrite, bool srgb,
                bool useDynamicScale, string filterMode, string wrapMode,
                int anisoLevel)
            {
                Width = width;
                Height = height;
                GraphicsFormat = graphicsFormat;
                DepthStencilFormat = depthStencilFormat;
                DepthBufferBits = depthBufferBits;
                Dimension = dimension;
                VolumeDepth = volumeDepth;
                MsaaSamples = msaaSamples;
                BindMs = bindMs;
                UseMipMap = useMipMap;
                AutoGenerateMips = autoGenerateMips;
                EnableRandomWrite = enableRandomWrite;
                Srgb = srgb;
                UseDynamicScale = useDynamicScale;
                FilterMode = filterMode;
                WrapMode = wrapMode;
                AnisoLevel = anisoLevel;
            }
        }

        private readonly struct MaterialSnapshot
        {
            public readonly string Shader;
            public readonly int RenderQueue;
            public readonly string[] Keywords;
            public readonly int RefractionPassIndex;
            public readonly string ExpectedLightMode;
            public readonly float SrcBlend;
            public readonly float DstBlend;
            public readonly float MvSrcColorBlend;
            public readonly float MvDstColorBlend;
            public readonly float ZTest;
            public readonly float ZWrite;
            public readonly float CullMode;
            public readonly Vector4 RbOffset;
            public readonly Color RbMainColorMask;
            public readonly Color RbOffsetColorMask;
            public readonly float RbIntensity;
            public readonly float RefractUseRbOffset;

            public MaterialSnapshot(
                string shader, int renderQueue, string[] keywords,
                int refractionPassIndex, string expectedLightMode,
                float srcBlend, float dstBlend, float mvSrcColorBlend,
                float mvDstColorBlend, float zTest, float zWrite, float cullMode,
                Vector4 rbOffset, Color rbMainColorMask, Color rbOffsetColorMask,
                float rbIntensity, float refractUseRbOffset)
            {
                Shader = shader;
                RenderQueue = renderQueue;
                Keywords = keywords;
                RefractionPassIndex = refractionPassIndex;
                ExpectedLightMode = expectedLightMode;
                SrcBlend = srcBlend;
                DstBlend = dstBlend;
                MvSrcColorBlend = mvSrcColorBlend;
                MvDstColorBlend = mvDstColorBlend;
                ZTest = zTest;
                ZWrite = zWrite;
                CullMode = cullMode;
                RbOffset = rbOffset;
                RbMainColorMask = rbMainColorMask;
                RbOffsetColorMask = rbOffsetColorMask;
                RbIntensity = rbIntensity;
                RefractUseRbOffset = refractUseRbOffset;
            }
        }

        private readonly struct ParticleSnapshot
        {
            public readonly string System;
            public readonly int ParticleCount;
            public readonly int CopiedCount;
            public readonly bool IsPlaying;
            public readonly bool IsEmitting;
            public readonly Vector3 FirstPosition;
            public readonly Vector3 FirstVelocity;
            public readonly float RemainingLifetime;
            public readonly float StartLifetime;
            public readonly float StartSize;
            public readonly Color32 StartColor;

            public ParticleSnapshot(
                string system, int particleCount, int copiedCount,
                bool isPlaying, bool isEmitting, Vector3 firstPosition,
                Vector3 firstVelocity, float remainingLifetime,
                float startLifetime, float startSize, Color32 startColor)
            {
                System = system;
                ParticleCount = particleCount;
                CopiedCount = copiedCount;
                IsPlaying = isPlaying;
                IsEmitting = isEmitting;
                FirstPosition = firstPosition;
                FirstVelocity = firstVelocity;
                RemainingLifetime = remainingLifetime;
                StartLifetime = startLifetime;
                StartSize = startSize;
                StartColor = startColor;
            }
        }

        private readonly struct ReadbackSnapshot
        {
            public readonly bool Succeeded;
            public readonly int ByteCount;
            public readonly bool NonZero;
            public readonly string Sha256;

            public ReadbackSnapshot(
                bool succeeded, int byteCount, bool nonZero, string sha256)
            {
                Succeeded = succeeded;
                ByteCount = byteCount;
                NonZero = nonZero;
                Sha256 = sha256;
            }

            public static ReadbackSnapshot Failed() =>
                new ReadbackSnapshot(false, 0, false, string.Empty);
        }
    }
}
