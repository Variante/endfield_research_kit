using System;
using System.Collections.Generic;
using System.Globalization;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Default-off replay of the installed VisibilitySH capsule producer. It
    /// publishes the half-resolution target to the canonical property only
    /// when the exact binning/reflection/b33 same-frame gate is also ready.
    /// </summary>
    internal sealed class EndfieldRecoveredVisibilitySHProducer : IDisposable
    {
        internal const string EnvironmentVariable =
            "ENDFIELD_RECOVERED_VISIBILITY_SH";
        internal const string CommandLineArgument =
            "-endfield-recovered-visibility-sh";
        internal const string DebugCommandLineArgument =
            "-endfield-recovered-visibility-sh-debug";
        internal const string RelaxedDebugCommandLineArgument =
            "-endfield-recovered-visibility-sh-debug-relaxed";

        private const string ShaderName =
            "Hidden/Endfield/HGRPCompat/RecoveredVisibilitySH";
        private const string PayloadResource =
            "EndfieldRecoveredVisibilitySH/visibility_sh_runtime";
        private const string SphereResource =
            "EndfieldRecoveredVisibilitySH/pSphere1_pF916E56CC12EC3D6";
        private const int CapsuleCapacity = 128;
        private const int RetailSphereMeshVertexCount = 79;
        private const int RetailSphereMeshIndexCount = 336;

        private static readonly GraphicsFormat ExactColorFormat =
            GraphicsFormat.R16G16B16A16_SFloat;
        private static readonly GraphicsFormat ExactDepthFormat =
            GraphicsFormat.D32_SFloat_S8_UInt;

        private static readonly int CanonicalOutputId =
            Shader.PropertyToID("_VisibilitySHRT");
        private static readonly int DiagnosticOutputId =
            Shader.PropertyToID("_EndfieldRecoveredVisibilitySH");
        private static readonly int ReadyId =
            Shader.PropertyToID("_EndfieldRecoveredVisibilitySHReady");
        private static readonly int CapsulesId =
            Shader.PropertyToID("_VisibilityCapsules");
        private static readonly int InputDepthId =
            Shader.PropertyToID("_InputDepthTexture");
        private static readonly int CameraDepthId =
            Shader.PropertyToID("_CameraDepthTexture");
        private static readonly int GBufferId =
            Shader.PropertyToID("_GBufferTexture1");
        private static readonly int LutId =
            Shader.PropertyToID("_LogSHLutTex");
        private static readonly int GpuViewProjectionId =
            Shader.PropertyToID("_GpuViewProjection");
        private static readonly int InverseGpuViewProjectionId =
            Shader.PropertyToID("_InverseGpuViewProjection");
        private static readonly int SphereParamsId =
            Shader.PropertyToID("_SphereParams");
        private static readonly int GStarParamsId =
            Shader.PropertyToID("_GStarParams");
        private static readonly int DebugModeId =
            Shader.PropertyToID("_VisibilityDebugMode");
        private static readonly int ZTestId =
            Shader.PropertyToID("_VisibilityZTest");
        private static readonly int CullId =
            Shader.PropertyToID("_VisibilityCull");

        [Serializable]
        private sealed class Payload
        {
            public RetailDefaults retailDefaults;
            public Vector4 gStarParams;
            public string visibilityShLutRgba32Base64;
            public Actor[] actors;
        }

        [Serializable]
        private sealed class RetailDefaults
        {
            public bool enabled;
            public bool halfResolution;
            public float sphereIntervalScale;
            public float sphereRangeScale;
        }

        [Serializable]
        private sealed class Actor
        {
            public string name;
            public Capsule[] capsules;
        }

        [Serializable]
        private sealed class Capsule
        {
            public string path;
            public float radius;
            public float height;
            public Vector3 offset;
            public Vector3 rotation;
            public float intensity;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct GpuCapsule
        {
            public Vector4 pa;
            public Vector4 pb;
            public Vector4 direction;
        }

        private sealed class CameraResources : IDisposable
        {
            internal readonly int width;
            internal readonly int height;
            internal readonly RenderTexture depth;
            internal readonly RenderTexture color;

            internal CameraResources(
                int width,
                int height,
                RenderTexture depth,
                RenderTexture color)
            {
                this.width = width;
                this.height = height;
                this.depth = depth;
                this.color = color;
            }

            public void Dispose()
            {
                Release(depth);
                Release(color);
            }
        }

        private readonly Dictionary<Camera, CameraResources> cameraResources =
            new Dictionary<Camera, CameraResources>();
        private readonly GpuCapsule[] cpuCapsules =
            new GpuCapsule[CapsuleCapacity];
        private readonly int[] survivorIndices =
            new int[CapsuleCapacity];
        private readonly MaterialPropertyBlock downsampleProperties =
            new MaterialPropertyBlock();
        private readonly MaterialPropertyBlock capsuleProperties =
            new MaterialPropertyBlock();
        private readonly bool requested;
        private readonly bool debugOutput;
        private readonly bool relaxedDebugState;

        private Payload payload;
        private Material material;
        private Mesh sphereMesh;
        private Texture2D visibilityShLut;
        private ComputeBuffer capsuleBuffer;
        private bool initialized;
        private bool loggedActive;
        private bool loggedFailure;
        private bool readbackRequested;
        private bool disposed;

        internal EndfieldRecoveredVisibilitySHProducer()
        {
            debugOutput =
                HasCommandLineArgument(DebugCommandLineArgument) ||
                HasCommandLineArgument(RelaxedDebugCommandLineArgument);
            relaxedDebugState =
                HasCommandLineArgument(RelaxedDebugCommandLineArgument);
            requested = ReadBooleanEnvironment(EnvironmentVariable) ||
                        HasCommandLineArgument(CommandLineArgument) ||
                        debugOutput;
            Shader.SetGlobalTexture(
                CanonicalOutputId,
                Texture2D.blackTexture);
            Shader.SetGlobalTexture(
                DiagnosticOutputId,
                Texture2D.blackTexture);
            Shader.SetGlobalFloat(ReadyId, 0.0f);
        }

        internal bool Requested => requested;

        internal bool TryGetCurrentPublication(
            Camera camera,
            int width,
            int height,
            out Texture2D logShLut,
            out RenderTexture visibilitySh,
            out string failure)
        {
            logShLut = null;
            visibilitySh = null;
            failure = string.Empty;
            if (!requested || disposed)
            {
                failure = "VisibilitySH producer is not requested";
                return false;
            }
            if (!initialized || visibilityShLut == null)
            {
                failure = "VisibilitySH exact LUT has not been initialized";
                return false;
            }
            if (camera == null ||
                !cameraResources.TryGetValue(camera, out CameraResources resources) ||
                resources.width != Math.Max(1, width / 2) ||
                resources.height != Math.Max(1, height / 2) ||
                resources.color == null ||
                !resources.color.IsCreated())
            {
                failure =
                    "VisibilitySH same-camera publication is unavailable for " +
                    $"{width}x{height}";
                return false;
            }
            logShLut = visibilityShLut;
            visibilitySh = resources.color;
            return true;
        }

        internal bool Render(
            ScriptableRenderContext context,
            Camera camera,
            EndfieldRecoveredPreGBufferDiagnostic.Frame preGBuffer,
            RenderTargetIdentifier canonicalColorTarget,
            RenderTargetIdentifier canonicalDepthTarget,
            bool canonicalFrameResourcesReady)
        {
            if (disposed)
                throw new ObjectDisposedException(
                    nameof(EndfieldRecoveredVisibilitySHProducer));

            if (!requested)
                return false;

            string failure;
            if (!TryInitialize(out failure) ||
                !ValidateFrame(camera, preGBuffer, out failure))
            {
                PublishFailure(context, failure);
                return false;
            }

            Actor actor;
            Transform actorRoot;
            if (!TryResolveActor(out actor, out actorRoot, out failure))
            {
                PublishFailure(context, failure);
                return false;
            }

            int authoredCapsuleCount;
            int capsuleCount = BuildCapsules(
                actor,
                actorRoot,
                camera,
                out authoredCapsuleCount,
                out failure);
            if (capsuleCount <= 0)
            {
                PublishFailure(context, failure);
                return false;
            }

            CameraResources resources;
            if (!TryGetResources(
                    camera,
                    Math.Max(1, preGBuffer.width / 2),
                    Math.Max(1, preGBuffer.height / 2),
                    out resources,
                    out failure))
            {
                PublishFailure(context, failure);
                return false;
            }

            capsuleBuffer.SetData(cpuCapsules, 0, 0, capsuleCount);
            Matrix4x4 gpuProjection =
                GL.GetGPUProjectionMatrix(camera.projectionMatrix, true);
            Matrix4x4 gpuViewProjection =
                gpuProjection * camera.worldToCameraMatrix;

            var commandBuffer = new CommandBuffer
            {
                name = "Recovered retail VisibilitySH capsule producer"
            };
            commandBuffer.BeginSample(
                "Recovered retail VisibilitySH capsule producer");

            // The retail pass clears a fresh stencil-bearing target and then
            // writes min(Gather2x2(sourceDepth)) as SV_Depth.
            commandBuffer.SetRenderTarget(resources.depth);
            commandBuffer.ClearRenderTarget(
                true,
                false,
                Color.clear,
                SystemInfo.usesReversedZBuffer ? 0.0f : 1.0f);
            downsampleProperties.Clear();
            downsampleProperties.SetTexture(
                InputDepthId,
                preGBuffer.depthCopy);
            commandBuffer.DrawProcedural(
                Matrix4x4.identity,
                material,
                0,
                MeshTopology.Triangles,
                3,
                1,
                downsampleProperties);

            commandBuffer.SetRenderTarget(
                new RenderTargetIdentifier(resources.color),
                new RenderTargetIdentifier(resources.depth));
            commandBuffer.ClearRenderTarget(false, true, Color.clear);
            capsuleProperties.Clear();
            capsuleProperties.SetBuffer(CapsulesId, capsuleBuffer);
            capsuleProperties.SetTexture(
                CameraDepthId,
                preGBuffer.depthCopy);
            capsuleProperties.SetTexture(GBufferId, preGBuffer.gBufferB);
            capsuleProperties.SetTexture(LutId, visibilityShLut);
            capsuleProperties.SetMatrix(
                GpuViewProjectionId,
                gpuViewProjection);
            capsuleProperties.SetMatrix(
                InverseGpuViewProjectionId,
                preGBuffer.inverseGpuViewProjection);
            capsuleProperties.SetVector(
                SphereParamsId,
                new Vector4(
                    payload.retailDefaults.sphereIntervalScale,
                    payload.retailDefaults.sphereRangeScale,
                    1.0f / resources.width,
                    1.0f / resources.height));
            capsuleProperties.SetVector(
                GStarParamsId,
                payload.gStarParams);
            capsuleProperties.SetFloat(
                DebugModeId,
                debugOutput ? 1.0f : 0.0f);
            commandBuffer.DrawMeshInstancedProcedural(
                sphereMesh,
                0,
                material,
                1,
                capsuleCount,
                capsuleProperties);
            commandBuffer.SetGlobalTexture(
                DiagnosticOutputId,
                resources.color);
            commandBuffer.SetGlobalTexture(
                CanonicalOutputId,
                canonicalFrameResourcesReady
                    ? (Texture)resources.color
                    : Texture2D.blackTexture);
            commandBuffer.SetGlobalFloat(
                ReadyId,
                canonicalFrameResourcesReady ? 1.0f : 0.0f);
            RequestOneShotReadback(
                commandBuffer,
                resources.color,
                actor.name);
            commandBuffer.SetRenderTarget(
                canonicalColorTarget,
                canonicalDepthTarget);
            commandBuffer.EndSample(
                "Recovered retail VisibilitySH capsule producer");
            context.ExecuteCommandBuffer(commandBuffer);
            commandBuffer.Release();

            if (!loggedActive)
            {
                LogCapsuleFixture(actor.name, capsuleCount);
                Debug.Log(
                    "Recovered VisibilitySH producer active: " +
                    $"{actor.name}, {capsuleCount}/{authoredCapsuleCount} " +
                    "retail-cull survivors, order=[" +
                    FormatSurvivorOrder(capsuleCount) + "], " +
                    $"{resources.width}x{resources.height} RGBAHalf, " +
                    "retail defaults interval=0.8/range=5/half-resolution, " +
                    "canonicalPublication=" +
                    (canonicalFrameResourcesReady ? "ready" : "fail-closed") +
                    (debugOutput
                        ? relaxedDebugState
                            ? ", DEBUG solid output with relaxed depth/cull."
                            : ", DEBUG solid output with exact depth/cull."
                        : "."));
                loggedActive = true;
            }
            return canonicalFrameResourcesReady;
        }

        private void RequestOneShotReadback(
            CommandBuffer commandBuffer,
            RenderTexture texture,
            string actorName)
        {
            if (readbackRequested ||
                commandBuffer == null ||
                texture == null)
                return;
            readbackRequested = true;
            int width = texture.width;
            int height = texture.height;
            commandBuffer.RequestAsyncReadback(texture, 0, request =>
            {
                if (request.hasError)
                {
                    Debug.LogWarning(
                        "Recovered VisibilitySH GPU readback failed.");
                    return;
                }

                var native = request.GetData<byte>();
                byte[] raw = native.ToArray();
                int nonzeroPixels = 0;
                for (int offset = 0; offset + 7 < raw.Length; offset += 8)
                {
                    bool nonzero = false;
                    for (int channel = 0; channel < 4; channel++)
                    {
                        int halfOffset = offset + channel * 2;
                        ushort bits = (ushort)(
                            raw[halfOffset] |
                            (raw[halfOffset + 1] << 8));
                        if ((bits & 0x7FFF) != 0)
                            nonzero = true;
                    }
                    if (nonzero)
                        nonzeroPixels++;
                }

                byte[] hash;
                using (SHA256 sha = SHA256.Create())
                    hash = sha.ComputeHash(raw);
                string hashText =
                    BitConverter.ToString(hash)
                        .Replace("-", string.Empty)
                        .ToLowerInvariant();
                Debug.Log(
                    "Recovered VisibilitySH GPU readback: " +
                    $"actor={actorName}, size={width}x{height}, " +
                    $"bytes={raw.Length}, nonzeroPixels={nonzeroPixels}, " +
                    $"sha256={hashText}.");
            });
        }

        internal void ResetAfterForward(ScriptableRenderContext context)
        {
            if (!requested || disposed)
                return;
            var commandBuffer = new CommandBuffer
            {
                name = "Reset recovered VisibilitySH publication"
            };
            commandBuffer.SetGlobalFloat(ReadyId, 0.0f);
            commandBuffer.SetGlobalTexture(
                DiagnosticOutputId,
                Texture2D.blackTexture);
            commandBuffer.SetGlobalTexture(
                CanonicalOutputId,
                Texture2D.blackTexture);
            context.ExecuteCommandBuffer(commandBuffer);
            commandBuffer.Release();
        }

        public void Dispose()
        {
            if (disposed)
                return;
            disposed = true;
            foreach (CameraResources resources in cameraResources.Values)
                resources.Dispose();
            cameraResources.Clear();
            if (capsuleBuffer != null)
            {
                capsuleBuffer.Release();
                capsuleBuffer = null;
            }
            DestroyResource(visibilityShLut);
            visibilityShLut = null;
            DestroyResource(material);
            material = null;
            Shader.SetGlobalTexture(
                CanonicalOutputId,
                Texture2D.blackTexture);
            Shader.SetGlobalTexture(
                DiagnosticOutputId,
                Texture2D.blackTexture);
            Shader.SetGlobalFloat(ReadyId, 0.0f);
        }

        private bool TryInitialize(out string failure)
        {
            failure = string.Empty;
            if (initialized)
                return true;

            TextAsset source = Resources.Load<TextAsset>(PayloadResource);
            if (source == null)
            {
                failure = "exact visibility payload resource is missing";
                return false;
            }
            payload = JsonUtility.FromJson<Payload>(source.text);
            if (payload == null ||
                payload.retailDefaults == null ||
                !payload.retailDefaults.enabled ||
                !payload.retailDefaults.halfResolution ||
                payload.actors == null)
            {
                failure = "exact visibility payload is invalid";
                return false;
            }

            Shader shader = Shader.Find(ShaderName);
            if (shader == null || !shader.isSupported)
            {
                failure = $"shader is missing or unsupported: {ShaderName}";
                return false;
            }
            material = new Material(shader)
            {
                hideFlags = HideFlags.HideAndDontSave,
                name = "Recovered retail VisibilitySH material",
                enableInstancing = true
            };
            material.SetInt(
                ZTestId,
                (int)(relaxedDebugState
                    ? CompareFunction.Always
                    : CompareFunction.Greater));
            material.SetInt(
                CullId,
                (int)(relaxedDebugState
                    ? CullMode.Off
                    : CullMode.Front));

            sphereMesh = Resources.Load<Mesh>(SphereResource);
            if (sphereMesh == null ||
                sphereMesh.vertexCount != RetailSphereMeshVertexCount ||
                sphereMesh.GetIndexCount(0) != RetailSphereMeshIndexCount)
            {
                failure =
                    "exact pSphere1 mesh is missing or its 79/336 topology drifted";
                return false;
            }

            byte[] lutBytes;
            try
            {
                lutBytes = Convert.FromBase64String(
                    payload.visibilityShLutRgba32Base64);
            }
            catch (FormatException)
            {
                failure = "exact VisibilitySH LUT base64 is invalid";
                return false;
            }
            if (lutBytes.Length != 256 * 4)
            {
                failure = "exact VisibilitySH LUT is not 1024 bytes";
                return false;
            }
            visibilityShLut = new Texture2D(
                256,
                1,
                TextureFormat.RGBA32,
                false,
                false)
            {
                hideFlags = HideFlags.HideAndDontSave,
                name = "visibility_sh_lut (exact retail Gamma payload)",
                filterMode = FilterMode.Bilinear,
                wrapMode = TextureWrapMode.Clamp,
                anisoLevel = 1
            };
            visibilityShLut.LoadRawTextureData(lutBytes);
            visibilityShLut.Apply(false, true);

            capsuleBuffer = new ComputeBuffer(
                CapsuleCapacity,
                Marshal.SizeOf<GpuCapsule>(),
                ComputeBufferType.Structured);
            initialized = true;
            return true;
        }

        private static bool ValidateFrame(
            Camera camera,
            EndfieldRecoveredPreGBufferDiagnostic.Frame frame,
            out string failure)
        {
            failure = string.Empty;
            if (camera == null)
                failure = "camera is null";
            else if (!frame.ready)
                failure = "PreGBuffer producer is unavailable: " + frame.failure;
            else if (frame.cameraInstanceId != camera.GetInstanceID())
                failure = "PreGBuffer frame belongs to another camera";
            else if (frame.depthCopy == null || frame.gBufferB == null)
                failure = "PreGBuffer depth copy or GBuffer B is missing";
            else if (frame.depthStencilFormat != ExactDepthFormat)
                failure =
                    $"exact D32_SFloat_S8_UInt source is required, got {frame.depthStencilFormat}";
            return failure.Length == 0;
        }

        private bool TryResolveActor(
            out Actor actor,
            out Transform actorRoot,
            out string failure)
        {
            actor = null;
            actorRoot = null;
            failure = string.Empty;
            foreach (Actor candidate in payload.actors)
            {
                GameObject gameObject = GameObject.Find(candidate.name);
                if (gameObject == null || !gameObject.activeInHierarchy)
                    continue;
                if (actor != null)
                {
                    failure =
                        "multiple supported actors are active; actor ownership is ambiguous";
                    return false;
                }
                actor = candidate;
                actorRoot = gameObject.transform;
            }
            if (actor == null)
            {
                failure = "no active Wulfa or Zhuangfy actor was found";
                return false;
            }
            return true;
        }

        private int BuildCapsules(
            Actor actor,
            Transform actorRoot,
            Camera camera,
            out int authoredCount,
            out string failure)
        {
            failure = string.Empty;
            authoredCount =
                actor.capsules != null ? actor.capsules.Length : 0;
            if (actor.capsules == null ||
                actor.capsules.Length == 0 ||
                actor.capsules.Length > CapsuleCapacity)
            {
                failure = "actor capsule count is invalid";
                return 0;
            }

            Plane[] frustumPlanes =
                GeometryUtility.CalculateFrustumPlanes(camera);
            int count = 0;
            for (int sourceIndex = 0;
                sourceIndex < actor.capsules.Length;
                sourceIndex++)
            {
                Capsule source = actor.capsules[sourceIndex];
                Transform bone = actorRoot.Find(source.path);
                if (bone == null)
                {
                    failure = $"missing exact capsule bone: {source.path}";
                    return 0;
                }

                Quaternion localRotation = Quaternion.Euler(source.rotation);
                Vector3 worldCenter = bone.TransformPoint(source.offset);
                Vector3 worldDirection =
                    bone.TransformDirection(localRotation * Vector3.up).normalized;
                float fullHeight = Mathf.Max(
                    source.height,
                    2.0f * source.radius);
                float cullExtent =
                    0.5f * fullHeight * 5.0f;
                var cullingBounds = new Bounds(
                    worldCenter,
                    Vector3.one * (2.0f * cullExtent));
                if (!GeometryUtility.TestPlanesAABB(
                        frustumPlanes,
                        cullingBounds))
                    continue;

                float halfSegment =
                    0.5f * fullHeight - source.radius;
                Vector3 pa = worldCenter - worldDirection * halfSegment;
                Vector3 pb = worldCenter + worldDirection * halfSegment;
                cpuCapsules[count++] = new GpuCapsule
                {
                    pa = new Vector4(pa.x, pa.y, pa.z, source.radius),
                    pb = new Vector4(pb.x, pb.y, pb.z, fullHeight),
                    direction = new Vector4(
                        worldDirection.x,
                        worldDirection.y,
                        worldDirection.z,
                        Mathf.Clamp(source.intensity, 0.01f, 2.0f))
                };
                survivorIndices[count - 1] = sourceIndex;
            }
            if (count == 0)
                failure =
                    "all exact authored capsules failed the retail " +
                    "conservative view-plane cull";
            return count;
        }

        private void LogCapsuleFixture(string actorName, int count)
        {
            byte[] raw = new byte[count * 48];
            int offset = 0;
            for (int index = 0; index < count; index++)
            {
                GpuCapsule capsule = cpuCapsules[index];
                WriteVector(raw, ref offset, capsule.pa);
                WriteVector(raw, ref offset, capsule.pb);
                WriteVector(raw, ref offset, capsule.direction);
            }

            byte[] hash;
            using (SHA256 sha = SHA256.Create())
                hash = sha.ComputeHash(raw);
            string hashText =
                BitConverter.ToString(hash)
                    .Replace("-", string.Empty)
                    .ToLowerInvariant();
            Debug.Log(
                "Recovered VisibilitySH CPU capsule fixture: " +
                $"actor={actorName}, count={count}, stride=48, " +
                "order=[" + FormatSurvivorOrder(count) + "], " +
                $"sha256={hashText}.");

            for (int index = 0; index < count; index++)
            {
                GpuCapsule capsule = cpuCapsules[index];
                Debug.Log(
                    "Recovered VisibilitySH CPU capsule record: " +
                    $"actor={actorName}, outputIndex={index}, " +
                    $"sourceIndex={survivorIndices[index]}, " +
                    $"pa={FormatVector(capsule.pa)}, " +
                    $"pb={FormatVector(capsule.pb)}, " +
                    $"dir={FormatVector(capsule.direction)}.");
            }
        }

        private static void WriteVector(
            byte[] destination,
            ref int offset,
            Vector4 value)
        {
            WriteSingle(destination, ref offset, value.x);
            WriteSingle(destination, ref offset, value.y);
            WriteSingle(destination, ref offset, value.z);
            WriteSingle(destination, ref offset, value.w);
        }

        private static void WriteSingle(
            byte[] destination,
            ref int offset,
            float value)
        {
            byte[] source = BitConverter.GetBytes(value);
            if (!BitConverter.IsLittleEndian)
                Array.Reverse(source);
            Buffer.BlockCopy(source, 0, destination, offset, 4);
            offset += 4;
        }

        private static string FormatVector(Vector4 value)
        {
            return "[" +
                value.x.ToString("R", CultureInfo.InvariantCulture) + "," +
                value.y.ToString("R", CultureInfo.InvariantCulture) + "," +
                value.z.ToString("R", CultureInfo.InvariantCulture) + "," +
                value.w.ToString("R", CultureInfo.InvariantCulture) + "]";
        }

        private string FormatSurvivorOrder(int count)
        {
            if (count <= 0)
                return string.Empty;
            string[] values = new string[count];
            for (int index = 0; index < count; index++)
                values[index] = survivorIndices[index].ToString();
            return string.Join(",", values);
        }

        private bool TryGetResources(
            Camera camera,
            int width,
            int height,
            out CameraResources resources,
            out string failure)
        {
            failure = string.Empty;
            if (cameraResources.TryGetValue(camera, out resources) &&
                resources.width == width &&
                resources.height == height &&
                resources.depth != null &&
                resources.depth.IsCreated() &&
                resources.color != null &&
                resources.color.IsCreated())
                return true;

            if (resources != null)
            {
                resources.Dispose();
                cameraResources.Remove(camera);
            }

            if (!SystemInfo.IsFormatSupported(
                    ExactColorFormat,
                    FormatUsage.Render) ||
                !SystemInfo.IsFormatSupported(
                    ExactDepthFormat,
                    FormatUsage.Render))
            {
                failure =
                    "GPU lacks exact RGBA16F or D32S8 render-target support";
                resources = null;
                return false;
            }

            var depthDescriptor = new RenderTextureDescriptor(width, height)
            {
                graphicsFormat = GraphicsFormat.None,
                depthStencilFormat = ExactDepthFormat,
                msaaSamples = 1,
                volumeDepth = 1,
                sRGB = false,
                useMipMap = false,
                autoGenerateMips = false
            };
            var depth = new RenderTexture(depthDescriptor)
            {
                hideFlags = HideFlags.HideAndDontSave,
                name = "Recovered VisibilitySH half-resolution D32S8",
                filterMode = FilterMode.Point,
                wrapMode = TextureWrapMode.Clamp
            };

            var colorDescriptor = new RenderTextureDescriptor(width, height)
            {
                graphicsFormat = ExactColorFormat,
                depthStencilFormat = GraphicsFormat.None,
                msaaSamples = 1,
                volumeDepth = 1,
                sRGB = false,
                useMipMap = false,
                autoGenerateMips = false
            };
            var color = new RenderTexture(colorDescriptor)
            {
                hideFlags = HideFlags.HideAndDontSave,
                name = "Recovered VisibilitySH half-resolution RGBAHalf",
                filterMode = FilterMode.Bilinear,
                wrapMode = TextureWrapMode.Clamp
            };
            if (!depth.Create() || !color.Create() ||
                depth.depthStencilFormat != ExactDepthFormat ||
                color.graphicsFormat != ExactColorFormat)
            {
                Release(depth);
                Release(color);
                failure = "exact VisibilitySH target allocation was substituted";
                resources = null;
                return false;
            }

            resources = new CameraResources(width, height, depth, color);
            cameraResources.Add(camera, resources);
            return true;
        }

        private void PublishFailure(
            ScriptableRenderContext context,
            string failure)
        {
            var commandBuffer = new CommandBuffer
            {
                name = "Fail closed recovered VisibilitySH producer"
            };
            commandBuffer.SetGlobalFloat(ReadyId, 0.0f);
            commandBuffer.SetGlobalTexture(
                CanonicalOutputId,
                Texture2D.blackTexture);
            commandBuffer.SetGlobalTexture(
                DiagnosticOutputId,
                Texture2D.blackTexture);
            context.ExecuteCommandBuffer(commandBuffer);
            commandBuffer.Release();
            if (!loggedFailure)
            {
                Debug.LogWarning(
                    "Recovered retail VisibilitySH producer failed closed: " +
                    failure);
                loggedFailure = true;
            }
        }

        private static bool ReadBooleanEnvironment(string name)
        {
            string value = Environment.GetEnvironmentVariable(name);
            if (string.IsNullOrWhiteSpace(value))
                return false;
            value = value.Trim();
            return value == "1" ||
                   value.Equals("true", StringComparison.OrdinalIgnoreCase) ||
                   value.Equals("yes", StringComparison.OrdinalIgnoreCase) ||
                   value.Equals("on", StringComparison.OrdinalIgnoreCase);
        }

        private static bool HasCommandLineArgument(string argument)
        {
            foreach (string value in Environment.GetCommandLineArgs())
            {
                if (string.Equals(
                        value,
                        argument,
                        StringComparison.OrdinalIgnoreCase))
                    return true;
            }
            return false;
        }

        private static void Release(RenderTexture texture)
        {
            if (texture == null)
                return;
            texture.Release();
            DestroyResource(texture);
        }

        private static void DestroyResource(UnityEngine.Object resource)
        {
            if (resource == null)
                return;
            if (Application.isPlaying)
                UnityEngine.Object.Destroy(resource);
            else
                UnityEngine.Object.DestroyImmediate(resource);
        }
    }
}
