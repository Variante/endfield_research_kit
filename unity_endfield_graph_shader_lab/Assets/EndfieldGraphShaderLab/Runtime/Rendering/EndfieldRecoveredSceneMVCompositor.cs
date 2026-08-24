using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Unity.Collections;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    [Serializable]
    public sealed class EndfieldRendererIdSidecarEntry
    {
        public int id;
        public int rendererInstanceId;
        public string rendererPath;
        public string rendererOrdinalPath;
        public string stableRendererKey;
        public int materialIndex;
        public string materialName;
        public string shaderName;
        public int renderQueue;
    }

    public sealed class EndfieldRendererIdSidecarCapture
    {
        public string redChannelIdScope;
        public long captureInvocationSerial;
        public int frame;
        public int width;
        public int height;
        public bool available;
        public string failure;
        public float[] rgba;
        public EndfieldRendererIdSidecarEntry[] entries;
    }

    [Serializable]
    public sealed class EndfieldRendererIdSidecarDictionary
    {
        public string redChannelIdScope;
        public EndfieldRendererIdSidecarEntry[] entries;
    }

    internal readonly struct EndfieldRecoveredSceneColorHandle
    {
        internal readonly int identifier;
        internal readonly RenderTextureDescriptor descriptor;

        internal EndfieldRecoveredSceneColorHandle(
            int identifier,
            RenderTextureDescriptor descriptor)
        {
            this.identifier = identifier;
            this.descriptor = descriptor;
        }

        internal RenderTargetIdentifier Target =>
            new RenderTargetIdentifier(identifier);
    }

    internal readonly struct EndfieldRecoveredSceneMVRequest
    {
        internal readonly bool requested;
        internal readonly bool valid;
        internal readonly bool hasDistortion;
        internal readonly bool hasGlow902Queue3005;
        internal readonly string failure;

        internal EndfieldRecoveredSceneMVRequest(
            bool requested,
            bool valid,
            bool hasDistortion,
            string failure,
            bool hasGlow902Queue3005 = false)
        {
            this.requested = requested;
            this.valid = valid;
            this.hasDistortion = hasDistortion;
            this.hasGlow902Queue3005 = hasGlow902Queue3005;
            this.failure = failure ?? string.Empty;
        }
    }

    public static class EndfieldRecoveredRendererIdSidecarCaptureBridge
    {
        public const string RedChannelIdScope =
            "captureInvocationSerial-local";

        public static string BuildStableRendererKey(
            string rendererOrdinalPath,
            int materialIndex,
            string materialName)
        {
            return (rendererOrdinalPath ?? string.Empty) +
                "|materialSlot=" +
                materialIndex.ToString(CultureInfo.InvariantCulture) +
                "|materialName=" +
                (materialName ?? string.Empty);
        }

        public static void Begin(long serial)
        {
            EndfieldRecoveredSceneMVCompositor.BeginRendererIdSidecarCapture(serial);
        }

        public static void End()
        {
            EndfieldRecoveredSceneMVCompositor.EndRendererIdSidecarCapture();
        }

        public static void WaitForReadback()
        {
            EndfieldRecoveredSceneMVCompositor.WaitForRendererIdSidecarReadback();
        }

        public static bool TryTake(
            long serial,
            out EndfieldRendererIdSidecarCapture capture)
        {
            return EndfieldRecoveredSceneMVCompositor.TryTakeRendererIdSidecarCapture(
                serial,
                out capture);
        }
    }

    /// <summary>
    /// Surgical native-render-pass implementation of the source-closed
    /// current-frame sceneMV contract used by the seven admitted particle VFX
    /// materials and three exact piaodai ribbon materials. It does not
    /// synthesize unrecovered opaque writers.
    /// </summary>
    internal sealed class EndfieldRecoveredSceneMVCompositor : IDisposable
    {
        internal const string RendererIdSidecarEnvironmentVariable =
            "ENDFIELD_RECOVERED_RENDERER_ID_SIDECAR";
        internal const string RendererIdSidecarCommandLineArgument =
            "-endfield-recovered-renderer-id-sidecar";
        internal const GraphicsFormat RendererIdSidecarFormat =
            GraphicsFormat.R32G32B32A32_SFloat;
        private const string RendererIdSidecarShaderResource =
            "EndfieldRecoveredRendererIdSidecar";
        internal static readonly int RendererIdSidecarPropertyId =
            Shader.PropertyToID("_EndfieldRecoveredRendererIdSidecar");

        internal const GraphicsFormat SceneMVFormat =
            GraphicsFormat.A2B10G10R10_UNormPack32;
        internal static readonly Color SceneMVNeutral =
            new Color(0.5f, 0.5f, 0.0f, 0.0f);
        internal const string ExactShaderTag = "ExactSelectedFiftyThree";
        internal const string ExactPiaodaiShaderTag =
            "ExactSelectedPiaodaiThree";

        internal static readonly int PingColorId =
            Shader.PropertyToID("_EndfieldRecoveredSceneColorPing");
        internal static readonly int PostColorId =
            Shader.PropertyToID("_EndfieldRecoveredPostColor");
        internal static readonly int AfterPostColorId =
            Shader.PropertyToID("_EndfieldRecoveredAfterPostColor");
        internal static readonly int SceneMVMRTReadyId =
            Shader.PropertyToID("_EndfieldSceneMVMRTReady");
        internal static readonly int VFXGlobalsReadyId =
            Shader.PropertyToID("_EndfieldRecoveredVFXGlobalsReady");
        internal static readonly int VFXParams0Id =
            Shader.PropertyToID("_VFXParams0");
        internal static readonly int ExposureWithMiscParamsId =
            Shader.PropertyToID("_ExposureWithMiscParams");

        private static readonly int SceneColorTextureId =
            Shader.PropertyToID("_SceneColorTexture");
        private static readonly int BlitTextureId =
            Shader.PropertyToID("_BlitTexture");
        private static readonly int BlitScaleBiasId =
            Shader.PropertyToID("_BlitScaleBias");
        private static readonly int BlitMipLevelId =
            Shader.PropertyToID("_BlitMipLevel");

        private const string CopyShaderResource =
            "EndfieldRecoveredSceneColorCopyExact";
        private const string BaseShaderName =
            "Hidden/Endfield/Recovered/Zhuangfy/VFXBaseV2MRT";
        private const string RadialBlurShaderName =
            "Hidden/Endfield/Recovered/Zhuangfy/VFXRadialBlurMRT";
        private const string RefractShaderName =
            "Hidden/Endfield/Recovered/Zhuangfy/VFXRefractMRT";
        private const string PiaodaiShaderName =
            "Endfield/Recovered/VFXBaseV2SampleStack";
        private const string LiZhiyanDiagnosticShaderName =
            "Endfield/Recovered/LiZhiyanStart01Diagnostic";
        private const string LiZhiyanSampleStackMaterialPrefix =
            "M_fxui__lizhiyan_overview_";
        private const string LiZhiyanDiagnosticMaterialSuffix =
            ".DiagnosticSampleStack";
        private const string LiZhiyanComposedMaterialSuffix =
            ".LiZhiyanActorComposedInstance";

        private static bool IsExactZhuangfyPiaodaiMaterial(Material material)
        {
            if (material == null)
                return false;

            string name = material.name;
            return name == "M_fx_ui_zhangfy_piaodai_01" ||
                name == "M_fx_ui_zhangfy_piaodai_02" ||
                name == "M_fx_ui_zhangfy_piaodai_03";
        }

        private static bool IsLiZhiyanSampleStackDiagnosticMaterial(Material material)
        {
            if (material == null)
                return false;

            string name = material.name;
            if (string.IsNullOrEmpty(name) ||
                !name.StartsWith(LiZhiyanSampleStackMaterialPrefix,
                    System.StringComparison.Ordinal))
            {
                return false;
            }

            return name.EndsWith(LiZhiyanDiagnosticMaterialSuffix,
                       System.StringComparison.Ordinal) ||
                name.EndsWith(LiZhiyanComposedMaterialSuffix,
                    System.StringComparison.Ordinal);
        }

        private static bool IsLiZhiyanRendererIdOnlyDiagnosticMaterial(
            Material material)
        {
            if (activeCaptureInvocationSerial <= 0 || material == null ||
                material.shader == null ||
                material.shader.name != LiZhiyanDiagnosticShaderName)
                return false;

            string name = material.name;
            return !string.IsNullOrEmpty(name) &&
                name.StartsWith(LiZhiyanSampleStackMaterialPrefix,
                    System.StringComparison.Ordinal) &&
                name.EndsWith(LiZhiyanComposedMaterialSuffix,
                    System.StringComparison.Ordinal);
        }

        private static readonly ShaderTagId[] MainTransparentPasses =
        {
            new ShaderTagId("TransparentBackface"),
            new ShaderTagId("ForwardOnly"),
            new ShaderTagId("Forward"),
            new ShaderTagId("ForwardCharacterOnly"),
            new ShaderTagId("SRPDefaultUnlit")
        };

        private static readonly ShaderTagId[] DistortionPasses =
        {
            new ShaderTagId("Distortion")
        };

        private static readonly ShaderTagId[] AfterPostPasses =
        {
            new ShaderTagId("TransparentBackface"),
            new ShaderTagId("ForwardOnly"),
            new ShaderTagId("Forward"),
            new ShaderTagId("ForwardCharacterOnly"),
            new ShaderTagId("SRPDefaultUnlit"),
            new ShaderTagId("Distortion")
        };

        private readonly Material copyMaterial;
        private readonly Material rendererIdSidecarMaterial;
        private readonly bool rendererIdSidecarRequested;
        private readonly Dictionary<Camera, RendererIdSidecarResources>
            rendererIdSidecarResources =
                new Dictionary<Camera, RendererIdSidecarResources>();
        private static long activeCaptureInvocationSerial;
        private static readonly Dictionary<long, EndfieldRendererIdSidecarCapture>
            completedRendererIdSidecars =
                new Dictionary<long, EndfieldRendererIdSidecarCapture>();

        private sealed class RendererIdPropertyBlockRestore
        {
            internal Renderer renderer;
            internal int materialIndex;
            internal MaterialPropertyBlock original;
            internal bool originalWasEmpty;
        }

        private sealed class RendererIdSidecarResources : IDisposable
        {
            internal int width;
            internal int height;
            internal RenderTexture sidecar;
            internal readonly List<EndfieldRendererIdSidecarEntry> entries =
                new List<EndfieldRendererIdSidecarEntry>();
            internal readonly List<RendererIdPropertyBlockRestore> restores =
                new List<RendererIdPropertyBlockRestore>();
            internal bool preparedBeforeCull;
            internal bool readbackPending;
            internal bool disposeRequested;

            public void Dispose()
            {
                Restore();
                disposeRequested = true;
                if (!readbackPending)
                    ReleaseSidecar();
            }

            internal void ReleaseSidecar()
            {
                if (sidecar == null)
                    return;
                if (sidecar.IsCreated())
                    sidecar.Release();
                if (Application.isPlaying)
                    UnityEngine.Object.Destroy(sidecar);
                else
                    UnityEngine.Object.DestroyImmediate(sidecar);
                sidecar = null;
            }

            internal void Restore()
            {
                for (int i = restores.Count - 1; i >= 0; i--)
                {
                    RendererIdPropertyBlockRestore restore = restores[i];
                    if (restore == null || restore.renderer == null)
                        continue;
                    restore.renderer.SetPropertyBlock(
                        restore.originalWasEmpty ? null : restore.original,
                        restore.materialIndex);
                }
                restores.Clear();
                entries.Clear();
                preparedBeforeCull = false;
            }
        }

        private sealed class RendererIdSidecarPendingReadback
        {
            internal RendererIdSidecarResources resources;
            internal long captureInvocationSerial;
            internal int frame;
            internal int width;
            internal int height;
            internal EndfieldRendererIdSidecarEntry[] entries;
        }

        internal EndfieldRecoveredSceneMVCompositor()
        {
            rendererIdSidecarRequested = IsRequested(
                RendererIdSidecarEnvironmentVariable,
                RendererIdSidecarCommandLineArgument);
            Shader shader = Resources.Load<Shader>(CopyShaderResource);
            if (shader != null && shader.isSupported)
            {
                copyMaterial = new Material(shader)
                {
                    name = "Endfield exact scene-color copy (Pipeline)",
                    hideFlags = HideFlags.HideAndDontSave
                };
            }
            Shader sidecarShader = Resources.Load<Shader>(
                RendererIdSidecarShaderResource);
            if (sidecarShader != null && sidecarShader.isSupported)
            {
                rendererIdSidecarMaterial = new Material(sidecarShader)
                {
                    name = "Endfield renderer-ID sidecar (Pipeline)",
                    hideFlags = HideFlags.HideAndDontSave
                };
            }
        }

        internal static void BeginRendererIdSidecarCapture(long serial)
        {
            activeCaptureInvocationSerial = serial;
        }

        internal static void EndRendererIdSidecarCapture()
        {
            activeCaptureInvocationSerial = 0;
        }

        internal static void WaitForRendererIdSidecarReadback()
        {
            AsyncGPUReadback.WaitAllRequests();
        }

        internal static bool TryTakeRendererIdSidecarCapture(
            long serial,
            out EndfieldRendererIdSidecarCapture capture)
        {
            if (completedRendererIdSidecars.TryGetValue(serial, out capture))
            {
                completedRendererIdSidecars.Remove(serial);
                return true;
            }
            capture = null;
            return false;
        }

        public void Dispose()
        {
            if (copyMaterial != null)
            {
                if (Application.isPlaying)
                    UnityEngine.Object.Destroy(copyMaterial);
                else
                    UnityEngine.Object.DestroyImmediate(copyMaterial);
            }
            if (rendererIdSidecarMaterial != null)
            {
                if (Application.isPlaying)
                    UnityEngine.Object.Destroy(rendererIdSidecarMaterial);
                else
                    UnityEngine.Object.DestroyImmediate(rendererIdSidecarMaterial);
            }
            foreach (RendererIdSidecarResources resources in
                     rendererIdSidecarResources.Values)
                resources.Dispose();
            rendererIdSidecarResources.Clear();
        }

        internal void PrepareRendererIdSidecarBeforeCulling(Camera camera)
        {
            if (camera == null ||
                (!rendererIdSidecarRequested && activeCaptureInvocationSerial <= 0))
                return;

            RendererIdSidecarResources resources;
            if (!rendererIdSidecarResources.TryGetValue(camera, out resources))
            {
                resources = new RendererIdSidecarResources();
                rendererIdSidecarResources.Add(camera, resources);
            }
            if (resources.readbackPending)
                return;

            resources.Restore();
            resources.width = 0;
            resources.height = 0;
            Renderer[] renderers = UnityEngine.Object.FindObjectsOfType<Renderer>();
            Array.Sort(renderers, CompareRendererIds);
            var candidates = new List<RendererIdCandidate>();
            for (int rendererIndex = 0; rendererIndex < renderers.Length; rendererIndex++)
            {
                Renderer renderer = renderers[rendererIndex];
                if (renderer == null || !renderer.enabled ||
                    !renderer.gameObject.activeInHierarchy ||
                    (camera.cullingMask & (1 << renderer.gameObject.layer)) == 0)
                    continue;
                Material[] materials = renderer.sharedMaterials;
                for (int materialIndex = 0;
                     materialIndex < materials.Length;
                     materialIndex++)
                {
                    Material material = materials[materialIndex];
                    if (material == null || material.shader == null ||
                        material.renderQueue < 3660 || material.renderQueue > 3740)
                        continue;
                    string rendererPath = BuildRendererPath(renderer);
                    string rendererOrdinalPath =
                        BuildRendererOrdinalPath(renderer);
                    string materialName = material.name;
                    string stableRendererKey =
                        EndfieldRecoveredRendererIdSidecarCaptureBridge
                            .BuildStableRendererKey(
                                rendererOrdinalPath, materialIndex, materialName);
                    candidates.Add(new RendererIdCandidate
                    {
                        renderer = renderer,
                        material = material,
                        materialIndex = materialIndex,
                        sortKey = stableRendererKey,
                        rendererOrdinalPath = rendererOrdinalPath,
                        stableRendererKey = stableRendererKey,
                        rendererInstanceId = renderer.GetInstanceID()
                    });
                }
            }
            candidates.Sort(CompareRendererIdCandidates);
            if (candidates.Count >= (1 << 24))
                return;

            for (int index = 0; index < candidates.Count; index++)
            {
                RendererIdCandidate candidate = candidates[index];
                var original = new MaterialPropertyBlock();
                candidate.renderer.GetPropertyBlock(
                    original, candidate.materialIndex);
                resources.restores.Add(new RendererIdPropertyBlockRestore
                {
                    renderer = candidate.renderer,
                    materialIndex = candidate.materialIndex,
                    original = original,
                    originalWasEmpty = original.isEmpty
                });
                var applied = new MaterialPropertyBlock();
                candidate.renderer.GetPropertyBlock(
                    applied, candidate.materialIndex);
                applied.SetFloat(RendererIdSidecarPropertyId, index + 1);
                candidate.renderer.SetPropertyBlock(
                    applied, candidate.materialIndex);
                resources.entries.Add(new EndfieldRendererIdSidecarEntry
                {
                    id = index + 1,
                    rendererInstanceId = candidate.renderer.GetInstanceID(),
                    rendererPath = BuildRendererPath(candidate.renderer),
                    rendererOrdinalPath = candidate.rendererOrdinalPath,
                    stableRendererKey = candidate.stableRendererKey,
                    materialIndex = candidate.materialIndex,
                    materialName = candidate.material.name,
                    shaderName = candidate.material.shader.name,
                    renderQueue = candidate.material.renderQueue
                });
            }
            resources.preparedBeforeCull = true;
        }

        private sealed class RendererIdCandidate
        {
            internal Renderer renderer;
            internal Material material;
            internal int materialIndex;
            internal string sortKey;
            internal string rendererOrdinalPath;
            internal string stableRendererKey;
            internal int rendererInstanceId;
        }

        private static int CompareRendererIdCandidates(
            RendererIdCandidate left,
            RendererIdCandidate right)
        {
            int key = string.CompareOrdinal(left.sortKey, right.sortKey);
            if (key != 0)
                return key;
            return left.rendererInstanceId.CompareTo(right.rendererInstanceId);
        }

        internal EndfieldRecoveredSceneMVRequest CollectRequest(Camera camera)
        {
            bool requested = false;
            bool hasDistortion = false;
            bool hasGlow902Queue3005 = false;
            bool hasRendererIdOnlyDiagnostic = false;
            Renderer[] renderers = UnityEngine.Object.FindObjectsOfType<Renderer>();
            for (int rendererIndex = 0; rendererIndex < renderers.Length; rendererIndex++)
            {
                Renderer renderer = renderers[rendererIndex];
                if (renderer == null ||
                    !renderer.enabled ||
                    !renderer.gameObject.activeInHierarchy ||
                    (camera.cullingMask & (1 << renderer.gameObject.layer)) == 0)
                {
                    continue;
                }

                Material[] materials = renderer.sharedMaterials;
                for (int materialIndex = 0; materialIndex < materials.Length; materialIndex++)
                {
                    Material material = materials[materialIndex];
                    if (material == null || material.shader == null)
                        continue;

                    string shaderName = material.shader.name;
                    bool isBase = shaderName == BaseShaderName;
                    bool isSampleStack = shaderName == PiaodaiShaderName;
                    bool isExactZhuangfyPiaodai = isSampleStack &&
                        IsExactZhuangfyPiaodaiMaterial(material);
                    bool isLiZhiyanSampleStackDiagnostic = isSampleStack &&
                        IsLiZhiyanSampleStackDiagnosticMaterial(material);
                    if (IsLiZhiyanRendererIdOnlyDiagnosticMaterial(material))
                    {
                        // This shader deliberately does not claim retail MRT
                        // admission. During an explicit sidecar capture,
                        // nevertheless keep the camera on the recovered
                        // scene-color/AfterPost route so the shared
                        // cullingResults and depth attachment can feed the
                        // diagnostic renderer-ID draw. The ordinary viewer
                        // never enters this branch because the capture serial
                        // is zero outside the harness.
                        hasRendererIdOnlyDiagnostic = true;
                        continue;
                    }
                    if (isSampleStack && !isExactZhuangfyPiaodai &&
                        !isLiZhiyanSampleStackDiagnostic)
                    {
                        return new EndfieldRecoveredSceneMVRequest(
                            true,
                            false,
                            false,
                            $"SampleStack material '{material.name}' has no source-closed classification");
                    }
                    bool isPiaodai = isExactZhuangfyPiaodai;
                    bool isDistortion =
                        shaderName == RadialBlurShaderName ||
                        shaderName == RefractShaderName;
                    if (!isBase && !isPiaodai &&
                        !isLiZhiyanSampleStackDiagnostic && !isDistortion)
                    {
                        if (material.renderQueue == 3005)
                        {
                            return new EndfieldRecoveredSceneMVRequest(
                                true,
                                false,
                                false,
                                $"queue-3005 material '{material.name}' is not the exact Glow902 MRT shader");
                        }
                        continue;
                    }

                    requested = true;
                    string expectedTag = isPiaodai ||
                        isLiZhiyanSampleStackDiagnostic
                        ? ExactPiaodaiShaderTag
                        : ExactShaderTag;
                    if (material.GetTag(
                            "EndfieldSceneMVMRT",
                            false,
                            string.Empty) != expectedTag)
                    {
                        return new EndfieldRecoveredSceneMVRequest(
                            true,
                            false,
                            false,
                            $"material '{material.name}' lacks the exact MRT admission tag");
                    }

                    int queue = material.renderQueue;
                    if (queue == 3005)
                    {
                        string glowFailure = string.Empty;
                        if (!isBase ||
                            !TryValidateGlow902ParticleInstance(
                                renderer,
                                materialIndex,
                                material,
                                out glowFailure))
                        {
                            return new EndfieldRecoveredSceneMVRequest(
                                true,
                                false,
                                false,
                                $"queue-3005 material '{material.name}' failed the exact Glow902 gate: " +
                                glowFailure);
                        }
                        hasGlow902Queue3005 = true;
                    }
                    if (isPiaodai && queue != 3700)
                    {
                        return new EndfieldRecoveredSceneMVRequest(
                            true,
                            false,
                            false,
                            $"piaodai material '{material.name}' has unsupported queue {queue}");
                    }
                    if (isLiZhiyanSampleStackDiagnostic &&
                        (queue < 3660 || queue > 3740))
                    {
                        return new EndfieldRecoveredSceneMVRequest(
                            true,
                            false,
                            false,
                            $"Li Zhiyan SampleStack diagnostic material '{material.name}' " +
                            $"has unsupported preserved queue {queue}");
                    }
                    long exactEndminfQueue2999Material = material.name == "M_fx_endminm_gfx_31"
                        ? 0x602883BD6BB1831BL
                        : material.name == "M_fx_endminm_gfx_43" ? 0x73D80B62F5BA886FL : 0L;
                    bool isExactEndminfQueue2999 = isBase && queue == 2999 &&
                        exactEndminfQueue2999Material != 0L &&
                        renderer.GetComponentInParent<EndfieldRecoveredParticleEffectSource>(true) is EndfieldRecoveredParticleEffectSource endminfSource &&
                        endminfSource.contractSchema == EndfieldRecoveredCharEffectSpawner.EndminfOverviewContractSchema &&
                        endminfSource.particleNodes != null &&
                        endminfSource.particleNodes.Any(node => node.materialPathIds != null &&
                            node.materialPathIds.Contains(exactEndminfQueue2999Material));
                    if (isBase && queue != 3000 && queue != 3005 &&
                        !isExactEndminfQueue2999 &&
                        (queue < 3660 || queue > 3740))
                    {
                        return new EndfieldRecoveredSceneMVRequest(
                            true,
                            false,
                            false,
                            $"base material '{material.name}' has unsupported queue {queue}");
                    }
                    if (isDistortion && queue != 3000)
                    {
                        return new EndfieldRecoveredSceneMVRequest(
                            true,
                            false,
                            false,
                            $"distortion material '{material.name}' has unsupported queue {queue}");
                    }
                    hasDistortion |= isDistortion;
                }
            }

            bool rendererIdOnlyRequest =
                !requested && hasRendererIdOnlyDiagnostic;
            return new EndfieldRecoveredSceneMVRequest(
                requested || rendererIdOnlyRequest,
                requested || rendererIdOnlyRequest,
                hasDistortion,
                requested || rendererIdOnlyRequest
                    ? string.Empty
                    : "no exact selected MRT material is active",
                hasGlow902Queue3005);
        }

        private static bool TryValidateGlow902ParticleInstance(
            Renderer renderer,
            int materialIndex,
            Material material,
            out string failure)
        {
            const long expectedMaterialPathId = -6130217779138746968L;
            const long expectedGameObjectPathId = -1156292932489990889L;
            const long expectedParticleSystemPathId = -8131524883884167913L;
            const long expectedParticleRendererPathId = 1423202925434875159L;
            const string expectedEffectRoot =
                "P_fxui_zhuangfy_ui_overview_start_01_baofa";
            const string expectedHierarchySuffix = "/all/glow (2)";

            failure = string.Empty;
            EndfieldRecoveredParticleEffectSource marker =
                renderer != null
                    ? renderer.GetComponentInParent<
                        EndfieldRecoveredParticleEffectSource>()
                    : null;
            if (marker == null || marker.effectRoot != expectedEffectRoot)
            {
                failure = "renderer is not owned by the exact baofa particle source";
                return false;
            }

            EndfieldRecoveredParticleNodeSource sourceNode = null;
            EndfieldRecoveredParticleNodeSource hierarchyCandidate = null;
            foreach (EndfieldRecoveredParticleNodeSource candidate in
                     marker.particleNodes ??
                     Array.Empty<EndfieldRecoveredParticleNodeSource>())
            {
                if (candidate.hierarchy != null &&
                    candidate.hierarchy.EndsWith(
                        expectedHierarchySuffix,
                        StringComparison.Ordinal))
                {
                    hierarchyCandidate = candidate;
                }
                if (candidate.gameObjectPathId == expectedGameObjectPathId &&
                    candidate.particleSystemPathId == expectedParticleSystemPathId &&
                    candidate.particleRendererPathId ==
                        expectedParticleRendererPathId &&
                    candidate.hierarchy != null &&
                    candidate.hierarchy.EndsWith(
                        expectedHierarchySuffix,
                        StringComparison.Ordinal))
                {
                    sourceNode = candidate;
                    break;
                }
            }
            if (sourceNode == null ||
                sourceNode.materialPathIds == null ||
                materialIndex < 0 ||
                materialIndex >= sourceNode.materialPathIds.Length ||
                sourceNode.materialPathIds[materialIndex] !=
                    expectedMaterialPathId)
            {
                failure = hierarchyCandidate == null
                    ? "baofa source has no /all/glow (2) particle node"
                    :
                        "baofa glow(2) ownership changed: " +
                        $"GameObject={hierarchyCandidate.gameObjectPathId}, " +
                        $"ParticleSystem={hierarchyCandidate.particleSystemPathId}, " +
                        $"Renderer={hierarchyCandidate.particleRendererPathId}, " +
                        $"materialIndex={materialIndex}, " +
                        $"materialCount={hierarchyCandidate.materialPathIds?.Length ?? 0}";
                return false;
            }

            EndfieldRecoveredParticleHierarchyNodeSource hierarchyNode = null;
            foreach (EndfieldRecoveredParticleHierarchyNodeSource candidate in
                     marker.hierarchyNodes ??
                     Array.Empty<EndfieldRecoveredParticleHierarchyNodeSource>())
            {
                if (candidate.transformPathId == sourceNode.transformPathId)
                {
                    hierarchyNode = candidate;
                    break;
                }
            }
            Transform transform = renderer.transform;
            Texture mainTexture = material.GetTexture("_MainTex");
            var mismatches = new List<string>();
            if (hierarchyNode == null)
                mismatches.Add("hierarchyNode=missing");
            else if (!ReferenceEquals(hierarchyNode.generatedTransform, transform))
                mismatches.Add(
                    $"generatedTransform={hierarchyNode.generatedTransform?.name ?? "null"}");
            if (transform.parent == null)
                mismatches.Add("parent=null");
            else
            {
                if (transform.parent.name != "all")
                    mismatches.Add($"parent={transform.parent.name}");
                if (Vector3.Distance(
                        transform.parent.localPosition,
                        new Vector3(0.7055f, 1.5325f, 0.056f)) > 1.0e-4f)
                    mismatches.Add($"parentPosition={transform.parent.localPosition}");
            }
            if (transform.localPosition.sqrMagnitude > 1.0e-10f)
                mismatches.Add($"position={transform.localPosition}");
            if (Quaternion.Angle(transform.localRotation, Quaternion.identity) > 1.0e-4f)
                mismatches.Add($"rotation={transform.localRotation.eulerAngles}");
            if (Vector3.Distance(
                    transform.localScale,
                    new Vector3(0.8193355f, 0.8193355f, 0.8193355f)) > 1.0e-5f)
                mismatches.Add($"scale={transform.localScale}");
            if (material.name != "M_fx_ui_glow_902") mismatches.Add($"material={material.name}");
            if (material.shader == null || material.shader.name != BaseShaderName)
                mismatches.Add($"shader={material.shader?.name ?? "null"}");
            if (material.GetTag("RenderType", false, string.Empty) != "Transparent")
                mismatches.Add("RenderType");
            if (material.FindPass("ForwardOnly") < 0) mismatches.Add("ForwardOnly");
            AddFloatMismatch(mismatches, material, "_SurfaceType", 1f);
            AddFloatMismatch(mismatches, material, "_BlendMode", 0f);
            AddFloatMismatch(mismatches, material, "_EnableTransparentMV", 0f);
            AddFloatMismatch(mismatches, material, "_IgnorePostExposure", 1f);
            AddFloatMismatch(mismatches, material, "_InParticle", 1f);
            AddFloatMismatch(mismatches, material, "_ZWrite", 0f);
            AddFloatMismatch(mismatches, material, "_ZTest", 4f);
            AddFloatMismatch(mismatches, material, "_CullMode", 2f);
            AddFloatMismatch(mismatches, material, "_SrcBlend", 1f);
            AddFloatMismatch(mismatches, material, "_DstBlend", 10f);
            if (mainTexture == null ||
                mainTexture.name != "T_fx_glow_101_D_p622183D86F3FBEEF")
                mismatches.Add($"MainTex={mainTexture?.name ?? "null"}");
            if (mismatches.Count != 0)
            {
                failure =
                    "baofa glow(2) exact contract changed: " +
                    string.Join(", ", mismatches);
                return false;
            }
            return true;
        }

        private static void AddFloatMismatch(
            List<string> mismatches,
            Material material,
            string property,
            float expected)
        {
            if (!HasExactFloat(material, property, expected))
            {
                mismatches.Add(
                    material.HasProperty(property)
                        ? $"{property}={material.GetFloat(property):R}"
                        : $"{property}=missing");
            }
        }

        private static bool HasExactFloat(
            Material material,
            string property,
            float expected)
        {
            return material.HasProperty(property) &&
                   Mathf.Abs(material.GetFloat(property) - expected) <= 1.0e-6f;
        }

        internal bool TryCreateSceneMV(
            int width,
            int height,
            out RenderTexture sceneMV,
            out string failure)
        {
            sceneMV = null;
            failure = string.Empty;
            if (copyMaterial == null)
            {
                failure = $"Resources/{CopyShaderResource}.shader is unavailable or unsupported";
                return false;
            }
            if (!SystemInfo.IsFormatSupported(SceneMVFormat, FormatUsage.Render))
            {
                failure = $"{SceneMVFormat} is not supported for rendering";
                return false;
            }

            var descriptor = new RenderTextureDescriptor(width, height)
            {
                graphicsFormat = SceneMVFormat,
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
                shadowSamplingMode = ShadowSamplingMode.None,
                useDynamicScale = false
            };
            sceneMV = new RenderTexture(descriptor)
            {
                name = "sceneMV",
                filterMode = FilterMode.Point,
                wrapMode = TextureWrapMode.Repeat,
                anisoLevel = 0,
                hideFlags = HideFlags.HideAndDontSave
            };
            if (!sceneMV.Create() ||
                !sceneMV.IsCreated() ||
                !TryValidateSceneMVDescriptor(
                    sceneMV,
                    width,
                    height,
                    out failure))
            {
                ReleaseRenderTexture(sceneMV);
                sceneMV = null;
                return false;
            }
            HDRenderPipeline.ReportRecoveredSceneMVDescriptor(sceneMV);
            return true;
        }

        private static bool TryValidateSceneMVDescriptor(
            RenderTexture sceneMV,
            int width,
            int height,
            out string failure)
        {
            RenderTextureDescriptor descriptor = sceneMV.descriptor;
            bool valid =
                descriptor.width == width &&
                descriptor.height == height &&
                descriptor.volumeDepth == 1 &&
                descriptor.graphicsFormat == SceneMVFormat &&
                descriptor.depthStencilFormat == GraphicsFormat.None &&
                descriptor.depthBufferBits == 0 &&
                descriptor.dimension == TextureDimension.Tex2D &&
                descriptor.msaaSamples == 1 &&
                !descriptor.bindMS &&
                !descriptor.useMipMap &&
                !descriptor.autoGenerateMips &&
                !descriptor.enableRandomWrite &&
                !descriptor.sRGB &&
                !descriptor.useDynamicScale &&
                sceneMV.filterMode == FilterMode.Point &&
                sceneMV.wrapMode == TextureWrapMode.Repeat &&
                sceneMV.anisoLevel == 0;
            if (!valid)
            {
                failure =
                    "sceneMV descriptor drift: " +
                    $"extent={descriptor.width}x{descriptor.height}, " +
                    $"slices={descriptor.volumeDepth}, " +
                    $"format={descriptor.graphicsFormat}, " +
                    $"depth={descriptor.depthStencilFormat}/{descriptor.depthBufferBits}, " +
                    $"dimension={descriptor.dimension}, msaa={descriptor.msaaSamples}, " +
                    $"bindMS={descriptor.bindMS}, filter={sceneMV.filterMode}, " +
                    $"wrap={sceneMV.wrapMode}";
                return false;
            }
            failure = string.Empty;
            return true;
        }

        internal bool DrawOpaqueOwner(
            ScriptableRenderContext context,
            Camera camera,
            CullingResults cullingResults,
            EndfieldRecoveredSceneColorHandle color,
            RenderTexture sceneMV,
            RenderTexture depth,
            GraphicsFormat depthFormat,
            ShaderTagId[] shaderPasses,
            bool dynamicBatching,
            bool gpuInstancing,
            out string failure)
        {
            failure = string.Empty;
            try
            {
                var attachments = new NativeArray<AttachmentDescriptor>(3, Allocator.Temp);
                var colors = new NativeArray<int>(2, Allocator.Temp);
                try
                {
                    var colorAttachment = new AttachmentDescriptor(color.descriptor.graphicsFormat);
                    colorAttachment.ConfigureTarget(color.Target, true, true);
                    attachments[0] = colorAttachment;

                    var sceneMVAttachment = new AttachmentDescriptor(SceneMVFormat);
                    sceneMVAttachment.ConfigureClear(SceneMVNeutral);
                    sceneMVAttachment.ConfigureTarget(sceneMV, false, true);
                    attachments[1] = sceneMVAttachment;
                    HDRenderPipeline.ReportRecoveredSceneMVNeutralInitialization();

                    var depthAttachment = new AttachmentDescriptor(depthFormat);
                    depthAttachment.ConfigureTarget(depth, true, true);
                    attachments[2] = depthAttachment;
                    colors[0] = 0;
                    colors[1] = 1;

                    context.BeginRenderPass(
                        color.descriptor.width,
                        color.descriptor.height,
                        1,
                        attachments,
                        2);
                    context.BeginSubPass(colors, false, false);
                    DrawRenderers(
                        context,
                        camera,
                        cullingResults,
                        RenderQueueRange.opaque,
                        SortingCriteria.CommonOpaque,
                        camera.cullingMask,
                        shaderPasses,
                        dynamicBatching,
                        gpuInstancing);
                    context.EndSubPass();
                    context.EndRenderPass();
                }
                finally
                {
                    colors.Dispose();
                    attachments.Dispose();
                }

                RestoreTarget(context, color.Target, depth);
                return true;
            }
            catch (Exception exception)
            {
                failure = exception.Message;
                return false;
            }
        }

        internal bool CompositeMainTransparent(
            ScriptableRenderContext context,
            Camera camera,
            CullingResults cullingResults,
            EndfieldRecoveredSceneColorHandle input,
            int outputIdentifier,
            bool allocateOutput,
            RenderTexture sceneMV,
            RenderTexture depth,
            GraphicsFormat depthFormat,
            int layerMask,
            bool dynamicBatching,
            bool gpuInstancing,
            bool fallbackSceneColorReady,
            RenderTargetIdentifier fallbackSceneColor,
            out EndfieldRecoveredSceneColorHandle output,
            out string failure)
        {
            return Composite(
                context,
                camera,
                cullingResults,
                input,
                outputIdentifier,
                allocateOutput,
                sceneMV,
                depth,
                depthFormat,
                new RenderQueueRange(2999, 3000),
                MainTransparentPasses,
                true,
                RemoveWorldUILayer(layerMask),
                dynamicBatching,
                gpuInstancing,
                fallbackSceneColorReady,
                fallbackSceneColor,
                "ForwardOnly",
                out output,
                out failure);
        }
        internal bool CompositeDistortion(
            ScriptableRenderContext context,
            Camera camera,
            CullingResults cullingResults,
            EndfieldRecoveredSceneColorHandle input,
            int outputIdentifier,
            bool allocateOutput,
            RenderTexture sceneMV,
            RenderTexture depth,
            GraphicsFormat depthFormat,
            int layerMask,
            bool dynamicBatching,
            bool gpuInstancing,
            bool fallbackSceneColorReady,
            RenderTargetIdentifier fallbackSceneColor,
            out EndfieldRecoveredSceneColorHandle output,
            out string failure)
        {
            return Composite(
                context,
                camera,
                cullingResults,
                input,
                outputIdentifier,
                allocateOutput,
                sceneMV,
                depth,
                depthFormat,
                new RenderQueueRange(3000, 3000),
                DistortionPasses,
                false,
                layerMask,
                dynamicBatching,
                gpuInstancing,
                fallbackSceneColorReady,
                fallbackSceneColor,
                "Distortion",
                out output,
                out failure);
        }

        internal bool CompositeGlow902Queue3005(
            ScriptableRenderContext context,
            Camera camera,
            CullingResults cullingResults,
            EndfieldRecoveredSceneColorHandle input,
            int outputIdentifier,
            RenderTexture sceneMV,
            RenderTexture depth,
            GraphicsFormat depthFormat,
            int layerMask,
            bool dynamicBatching,
            bool gpuInstancing,
            bool fallbackSceneColorReady,
            RenderTargetIdentifier fallbackSceneColor,
            out EndfieldRecoveredSceneColorHandle output,
            out string failure)
        {
            bool ready = Composite(
                context,
                camera,
                cullingResults,
                input,
                outputIdentifier,
                false,
                sceneMV,
                depth,
                depthFormat,
                new RenderQueueRange(3005, 3005),
                MainTransparentPasses,
                true,
                layerMask,
                dynamicBatching,
                gpuInstancing,
                fallbackSceneColorReady,
                fallbackSceneColor,
                "source-closed Glow902 queue-3005 ForwardOnly",
                out output,
                out failure);
            if (ready)
                HDRenderPipeline.ReportRecoveredGlow902Queue3005Lane();
            return ready;
        }

        internal bool CompositeAfterPost(
            ScriptableRenderContext context,
            Camera camera,
            CullingResults cullingResults,
            EndfieldRecoveredSceneColorHandle input,
            int outputIdentifier,
            RenderTexture sceneMV,
            RenderTexture depth,
            GraphicsFormat depthFormat,
            int layerMask,
            bool dynamicBatching,
            bool gpuInstancing,
            out EndfieldRecoveredSceneColorHandle output,
            out string failure)
        {
            bool ready = Composite(
                context,
                camera,
                cullingResults,
                input,
                outputIdentifier,
                true,
                sceneMV,
                depth,
                depthFormat,
                new RenderQueueRange(3660, 3740),
                AfterPostPasses,
                true,
                RemoveWorldUILayer(layerMask),
                dynamicBatching,
                gpuInstancing,
                false,
                default,
                "after-postprocess ForwardOnly",
                out output,
                out failure);
            if (ready)
            {
                RenderRendererIdSidecar(
                    context,
                    camera,
                    cullingResults,
                    depth,
                    depthFormat,
                    RemoveWorldUILayer(layerMask),
                    dynamicBatching,
                    gpuInstancing);
                HDRenderPipeline.ReportRecoveredAfterPostDescriptors(
                    output.descriptor.graphicsFormat,
                    DescriptorsMatch(input.descriptor, output.descriptor));
            }
            else
            {
                PublishRendererIdSidecarFailureForCurrentCapture(
                    camera,
                    "after-post compositor rejected the frame: " + failure);
            }
            return ready;
        }

        internal void FinalizeRendererIdSidecarAfterSubmit()
        {
            foreach (RendererIdSidecarResources resources in
                     rendererIdSidecarResources.Values)
                resources.Restore();
        }

        private void RenderRendererIdSidecar(
            ScriptableRenderContext context,
            Camera camera,
            CullingResults cullingResults,
            RenderTexture depth,
            GraphicsFormat depthFormat,
            int layerMask,
            bool dynamicBatching,
            bool gpuInstancing)
        {
            if (camera == null ||
                (!rendererIdSidecarRequested && activeCaptureInvocationSerial <= 0))
                return;
            RendererIdSidecarResources resources;
            if (!rendererIdSidecarResources.TryGetValue(camera, out resources))
                return;
            if (rendererIdSidecarMaterial == null)
            {
                PublishRendererIdSidecarFailure(
                    activeCaptureInvocationSerial,
                    resources,
                    "renderer-ID sidecar shader is missing or unsupported");
                return;
            }
            if (depth == null)
            {
                PublishRendererIdSidecarFailure(
                    activeCaptureInvocationSerial,
                    resources,
                    "after-post depth target is unavailable");
                return;
            }
            if (!depth.IsCreated() || depth.width <= 0 || depth.height <= 0)
            {
                PublishRendererIdSidecarFailure(
                    activeCaptureInvocationSerial,
                    resources,
                    "after-post depth target has an invalid extent");
                return;
            }
            resources.width = depth.width;
            resources.height = depth.height;
            if (!resources.preparedBeforeCull)
            {
                PublishRendererIdSidecarFailure(
                    activeCaptureInvocationSerial,
                    resources,
                    "renderer-ID properties were not prepared before culling");
                return;
            }
            if (resources.entries.Count == 0)
            {
                PublishRendererIdSidecarFailure(
                    activeCaptureInvocationSerial,
                    resources,
                    "no active queue-3660..3740 renderer/material slots were eligible");
                return;
            }
            if (resources.readbackPending)
                return;
            if (!SystemInfo.supportsAsyncGPUReadback ||
                !SystemInfo.IsFormatSupported(
                    RendererIdSidecarFormat, FormatUsage.Render))
            {
                PublishRendererIdSidecarFailure(
                    activeCaptureInvocationSerial,
                    resources,
                    "RGBA32F render or async GPU readback is unsupported");
                return;
            }
            if (resources.sidecar == null ||
                !resources.sidecar.IsCreated() ||
                resources.sidecar.width != resources.width ||
                resources.sidecar.height != resources.height)
            {
                if (resources.sidecar != null)
                {
                    if (resources.sidecar.IsCreated())
                        resources.sidecar.Release();
                    if (Application.isPlaying)
                        UnityEngine.Object.Destroy(resources.sidecar);
                    else
                        UnityEngine.Object.DestroyImmediate(resources.sidecar);
                }
                var descriptor = new RenderTextureDescriptor(
                    resources.width,
                    resources.height)
                {
                    graphicsFormat = RendererIdSidecarFormat,
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
                    useDynamicScale = false
                };
                resources.sidecar = new RenderTexture(descriptor)
                {
                    name = "Recovered Renderer-ID Sidecar RGBA32F",
                    hideFlags = HideFlags.HideAndDontSave,
                    filterMode = FilterMode.Point,
                    wrapMode = TextureWrapMode.Clamp
                };
                resources.sidecar.Create();
            }
            if (!resources.sidecar.IsCreated() ||
                resources.sidecar.graphicsFormat != RendererIdSidecarFormat)
                return;

            bool renderPassBegun = false;
            bool subPassBegun = false;
            bool sidecarDrawRecorded = false;
            var attachments = new NativeArray<AttachmentDescriptor>(2, Allocator.Temp);
            var colors = new NativeArray<int>(1, Allocator.Temp);
            try
            {
                var sidecarAttachment = new AttachmentDescriptor(
                    RendererIdSidecarFormat);
                sidecarAttachment.ConfigureTarget(resources.sidecar, false, true);
                sidecarAttachment.ConfigureClear(Color.clear);
                attachments[0] = sidecarAttachment;
                var depthAttachment = new AttachmentDescriptor(depthFormat);
                depthAttachment.ConfigureTarget(depth, true, true);
                attachments[1] = depthAttachment;
                colors[0] = 0;
                context.BeginRenderPass(
                    resources.width,
                    resources.height,
                    1,
                    attachments,
                    1);
                renderPassBegun = true;
                context.BeginSubPass(colors, true, true);
                subPassBegun = true;
                DrawRenderers(
                    context,
                    camera,
                    cullingResults,
                    new RenderQueueRange(3660, 3740),
                    SortingCriteria.CommonTransparent |
                        SortingCriteria.OptimizeStateChanges |
                        SortingCriteria.RendererPriority,
                    layerMask,
                    AfterPostPasses,
                    dynamicBatching,
                    gpuInstancing,
                    rendererIdSidecarMaterial,
                    0);
                sidecarDrawRecorded = true;
            }
            catch (Exception exception)
            {
                PublishRendererIdSidecarFailure(
                    activeCaptureInvocationSerial,
                    resources,
                    exception.Message);
            }
            finally
            {
                if (subPassBegun)
                    context.EndSubPass();
                if (renderPassBegun)
                    context.EndRenderPass();
                colors.Dispose();
                attachments.Dispose();
            }

            if (!sidecarDrawRecorded)
                return;

            long serial = activeCaptureInvocationSerial;
            if (serial <= 0)
                return;
            var pending = new RendererIdSidecarPendingReadback
            {
                resources = resources,
                captureInvocationSerial = serial,
                frame = Time.frameCount,
                width = resources.width,
                height = resources.height,
                entries = resources.entries.ToArray()
            };
            resources.readbackPending = true;
            var readback = new CommandBuffer
            {
                name = "Recovered renderer-ID sidecar RGBA32F readback"
            };
            readback.RequestAsyncReadback(
                resources.sidecar,
                0,
                request => CompleteRendererIdSidecarReadback(pending, request));
            context.ExecuteCommandBuffer(readback);
            readback.Release();
        }

        private static void CompleteRendererIdSidecarReadback(
            RendererIdSidecarPendingReadback pending,
            AsyncGPUReadbackRequest request)
        {
            var capture = new EndfieldRendererIdSidecarCapture
            {
                captureInvocationSerial = pending.captureInvocationSerial,
                redChannelIdScope =
                    EndfieldRecoveredRendererIdSidecarCaptureBridge.RedChannelIdScope,
                frame = pending.frame,
                width = pending.width,
                height = pending.height,
                entries = pending.entries,
                available = !request.hasError,
                failure = request.hasError
                    ? "RGBA32F renderer-ID sidecar readback failed"
                    : string.Empty
            };
            if (!request.hasError)
            {
                try
                {
                    var data = request.GetData<float>();
                    capture.rgba = new float[data.Length];
                    for (int i = 0; i < data.Length; i++)
                        capture.rgba[i] = data[i];
                }
                catch (Exception exception)
                {
                    capture.available = false;
                    capture.failure =
                        "RGBA32F renderer-ID sidecar readback exception: " +
                        exception.Message;
                }
            }
            pending.resources.readbackPending = false;
            if (pending.resources.disposeRequested)
                pending.resources.ReleaseSidecar();
            completedRendererIdSidecars[pending.captureInvocationSerial] = capture;
        }

        private static void PublishRendererIdSidecarFailure(
            long serial,
            RendererIdSidecarResources resources,
            string failure)
        {
            if (serial <= 0)
                return;
            EndfieldRendererIdSidecarCapture existing;
            if (completedRendererIdSidecars.TryGetValue(serial, out existing) &&
                existing != null && existing.available)
            {
                return;
            }
            resources.readbackPending = false;
            completedRendererIdSidecars[serial] =
                new EndfieldRendererIdSidecarCapture
                {
                    captureInvocationSerial = serial,
                    redChannelIdScope =
                        EndfieldRecoveredRendererIdSidecarCaptureBridge.RedChannelIdScope,
                    frame = Time.frameCount,
                    width = resources.width,
                    height = resources.height,
                    available = false,
                    failure = failure ?? "renderer-ID sidecar failed closed",
                    entries = resources.entries.ToArray()
                };
        }

        internal void PublishRendererIdSidecarFailureForCurrentCapture(
            Camera camera,
            string failure)
        {
            if (activeCaptureInvocationSerial <= 0 || camera == null)
                return;
            RendererIdSidecarResources resources;
            if (!rendererIdSidecarResources.TryGetValue(camera, out resources))
                return;
            PublishRendererIdSidecarFailure(
                activeCaptureInvocationSerial,
                resources,
                failure);
        }

        private bool Composite(
            ScriptableRenderContext context,
            Camera camera,
            CullingResults cullingResults,
            EndfieldRecoveredSceneColorHandle input,
            int outputIdentifier,
            bool allocateOutput,
            RenderTexture sceneMV,
            RenderTexture depth,
            GraphicsFormat depthFormat,
            RenderQueueRange queueRange,
            ShaderTagId[] shaderPasses,
            bool depthReadOnly,
            int layerMask,
            bool dynamicBatching,
            bool gpuInstancing,
            bool fallbackSceneColorReady,
            RenderTargetIdentifier fallbackSceneColor,
            string label,
            out EndfieldRecoveredSceneColorHandle output,
            out string failure)
        {
            // RenderTextureDescriptor is a value type. Preserve the complete
            // current sceneColor descriptor; selected retail format/MSAA/
            // extent are runtime inputs, not independent AfterDOF constants.
            RenderTextureDescriptor outputDescriptor = input.descriptor;
            output = new EndfieldRecoveredSceneColorHandle(
                outputIdentifier,
                outputDescriptor);
            failure = string.Empty;
            bool exactRecoveredSceneColor =
                input.descriptor.graphicsFormat ==
                HDRenderPipeline.RecoveredSceneColorFormat;
            bool formatReady = exactRecoveredSceneColor
                ? HDRenderPipeline.TryValidateRecoveredSceneColorFormat(
                    out _)
                : SystemInfo.IsFormatSupported(
                    input.descriptor.graphicsFormat,
                    FormatUsage.Render) &&
                  SystemInfo.IsFormatSupported(
                    input.descriptor.graphicsFormat,
                    FormatUsage.Sample);
            if (!formatReady)
            {
                failure = $"scene color format {input.descriptor.graphicsFormat} is not render-and-sample capable";
                return false;
            }

            if (allocateOutput)
            {
                var allocate = new CommandBuffer
                {
                    name = $"Allocate recovered {label} scene-color clone"
                };
                allocate.GetTemporaryRT(
                    outputIdentifier,
                    input.descriptor,
                    FilterMode.Bilinear);
                context.ExecuteCommandBuffer(allocate);
                allocate.Release();
            }

            bool renderPassBegun = false;
            bool subPassBegun = false;
            bool success = false;
            try
            {
                var attachments = new NativeArray<AttachmentDescriptor>(3, Allocator.Temp);
                var colors = new NativeArray<int>(2, Allocator.Temp);
                try
                {
                    var outputAttachment = new AttachmentDescriptor(
                        input.descriptor.graphicsFormat);
                    outputAttachment.ConfigureTarget(output.Target, false, true);
                    attachments[0] = outputAttachment;

                    var sceneMVAttachment = new AttachmentDescriptor(SceneMVFormat);
                    sceneMVAttachment.ConfigureTarget(sceneMV, true, true);
                    attachments[1] = sceneMVAttachment;

                    var depthAttachment = new AttachmentDescriptor(depthFormat);
                    depthAttachment.ConfigureTarget(depth, true, true);
                    attachments[2] = depthAttachment;
                    colors[0] = 0;
                    colors[1] = 1;

                    context.BeginRenderPass(
                        input.descriptor.width,
                        input.descriptor.height,
                        1,
                        attachments,
                        2);
                    renderPassBegun = true;
                    context.BeginSubPass(
                        colors,
                        depthReadOnly,
                        depthReadOnly);
                    subPassBegun = true;

                    var copy = new CommandBuffer
                    {
                        name = $"Recovered {label} old-scene copy"
                    };
                    copy.SetGlobalTexture(BlitTextureId, input.Target);
                    copy.SetGlobalTexture(SceneColorTextureId, input.Target);
                    copy.SetGlobalVector(
                        BlitScaleBiasId,
                        new Vector4(1.0f, 1.0f, 0.0f, 0.0f));
                    copy.SetGlobalFloat(BlitMipLevelId, 0.0f);
                    copy.SetGlobalFloat(SceneMVMRTReadyId, 1.0f);
                    copy.DrawProcedural(
                        Matrix4x4.identity,
                        copyMaterial,
                        0,
                        MeshTopology.Triangles,
                        3,
                        1);
                    context.ExecuteCommandBuffer(copy);
                    copy.Release();

                    // SetupCameraProperties publishes the projection for the
                    // camera's final target.  This subpass instead rasterizes
                    // into an offscreen RenderTexture attachment.  On APIs
                    // whose render-texture UV origin is at the top (D3D), the
                    // GPU projection therefore needs Unity's renderIntoTexture
                    // conversion for the draw, independently of the old-scene
                    // fullscreen copy above.  Without it, world-space VFX are
                    // vertically mirrored while the copied actor remains in
                    // the existing scene-color convention.
                    var setOffscreenProjection = new CommandBuffer
                    {
                        name = $"Recovered {label} offscreen projection"
                    };
                    setOffscreenProjection.SetViewProjectionMatrices(
                        camera.worldToCameraMatrix,
                        GL.GetGPUProjectionMatrix(
                            camera.projectionMatrix,
                            true));
                    context.ExecuteCommandBuffer(setOffscreenProjection);
                    setOffscreenProjection.Release();

                    DrawRenderers(
                        context,
                        camera,
                        cullingResults,
                        queueRange,
                        SortingCriteria.CommonTransparent |
                            SortingCriteria.OptimizeStateChanges |
                            SortingCriteria.RendererPriority,
                        layerMask,
                        shaderPasses,
                        dynamicBatching,
                        gpuInstancing);
                    var restoreCameraProjection = new CommandBuffer
                    {
                        name = $"Restore {label} camera-target projection"
                    };
                    restoreCameraProjection.SetViewProjectionMatrices(
                        camera.worldToCameraMatrix,
                        GL.GetGPUProjectionMatrix(
                            camera.projectionMatrix,
                            false));
                    context.ExecuteCommandBuffer(restoreCameraProjection);
                    restoreCameraProjection.Release();
                    // Retail appends a separate HGMeshRender ECS handle here.
                    // Its deferred producer is source-closed, but Unity has no
                    // equivalent HG GPU-driven handle/consumer. Keep that lane
                    // absent instead of merging ECS records into DrawRenderers.
                    success = true;
                }
                finally
                {
                    colors.Dispose();
                    attachments.Dispose();
                }
            }
            catch (Exception exception)
            {
                failure = exception.Message;
            }
            finally
            {
                if (subPassBegun)
                    context.EndSubPass();
                if (renderPassBegun)
                    context.EndRenderPass();

                var restore = new CommandBuffer
                {
                    name = $"Finish recovered {label} scene-color handoff"
                };
                restore.SetGlobalFloat(SceneMVMRTReadyId, 0.0f);
                restore.SetGlobalTexture(
                    SceneColorTextureId,
                    fallbackSceneColorReady
                        ? fallbackSceneColor
                        : new RenderTargetIdentifier(Texture2D.blackTexture));
                restore.SetRenderTarget(
                    success ? output.Target : input.Target,
                    new RenderTargetIdentifier(depth));
                context.ExecuteCommandBuffer(restore);
                restore.Release();
            }
            return success;
        }

        private static bool DescriptorsMatch(
            RenderTextureDescriptor left,
            RenderTextureDescriptor right)
        {
            return
                left.width == right.width &&
                left.height == right.height &&
                left.volumeDepth == right.volumeDepth &&
                left.graphicsFormat == right.graphicsFormat &&
                left.depthStencilFormat == right.depthStencilFormat &&
                left.depthBufferBits == right.depthBufferBits &&
                left.dimension == right.dimension &&
                left.msaaSamples == right.msaaSamples &&
                left.bindMS == right.bindMS &&
                left.useMipMap == right.useMipMap &&
                left.autoGenerateMips == right.autoGenerateMips &&
                left.enableRandomWrite == right.enableRandomWrite &&
                left.sRGB == right.sRGB &&
                left.useDynamicScale == right.useDynamicScale;
        }

        private static int RemoveWorldUILayer(int layerMask)
        {
            // Retail HGRendererListUtils calls HGCamera.RemoveWorldUILayer on
            // camera.cullingMask before building every transparent descriptor.
            // Resolve the named layer instead of copying the current client's
            // numeric index into this standalone Unity project.
            int worldUiLayer = LayerMask.NameToLayer("WorldUI");
            return worldUiLayer >= 0
                ? layerMask & ~(1 << worldUiLayer)
                : layerMask;
        }

        private static void DrawRenderers(
            ScriptableRenderContext context,
            Camera camera,
            CullingResults cullingResults,
            RenderQueueRange queueRange,
            SortingCriteria sortingCriteria,
            int layerMask,
            ShaderTagId[] shaderPasses,
            bool dynamicBatching,
            bool gpuInstancing)
        {
            DrawRenderers(
                context,
                camera,
                cullingResults,
                queueRange,
                sortingCriteria,
                layerMask,
                shaderPasses,
                dynamicBatching,
                gpuInstancing,
                null,
                -1);
        }

        private static void DrawRenderers(
            ScriptableRenderContext context,
            Camera camera,
            CullingResults cullingResults,
            RenderQueueRange queueRange,
            SortingCriteria sortingCriteria,
            int layerMask,
            ShaderTagId[] shaderPasses,
            bool dynamicBatching,
            bool gpuInstancing,
            Material overrideMaterial,
            int overrideMaterialPassIndex)
        {
            var sortingSettings = new SortingSettings(camera)
            {
                criteria = sortingCriteria
            };
            var drawingSettings = new DrawingSettings(
                shaderPasses[0],
                sortingSettings)
            {
                enableDynamicBatching = dynamicBatching,
                enableInstancing = gpuInstancing,
                // Retail initializes m_CurrentRendererConfigurationBakedLighting
                // to 15 and GetPerObjectMotionVectorConfig returns 32 for every
                // non-null HGCamera. Preserve the exact combined descriptor
                // request (47); Unity owns the corresponding per-draw payloads.
                perObjectData = (PerObjectData)47
            };
            if (overrideMaterial != null)
            {
                drawingSettings.overrideMaterial = overrideMaterial;
                drawingSettings.overrideMaterialPassIndex =
                    overrideMaterialPassIndex;
            }
            for (int i = 1; i < shaderPasses.Length; i++)
                drawingSettings.SetShaderPassName(i, shaderPasses[i]);
            var filteringSettings = new FilteringSettings(queueRange, layerMask);
            context.DrawRenderers(
                cullingResults,
                ref drawingSettings,
                ref filteringSettings);
        }

        private static int CompareRendererIds(Renderer left, Renderer right)
        {
            int path = string.CompareOrdinal(
                BuildRendererPath(left), BuildRendererPath(right));
            if (path != 0)
                return path;
            return left.GetInstanceID().CompareTo(right.GetInstanceID());
        }

        private static string BuildRendererPath(Renderer renderer)
        {
            if (renderer == null)
                return string.Empty;
            var names = new List<string>();
            Transform current = renderer.transform;
            while (current != null)
            {
                names.Add(current.name);
                current = current.parent;
            }
            names.Reverse();
            return string.Join("/", names.ToArray());
        }

        private static string BuildRendererOrdinalPath(Renderer renderer)
        {
            if (renderer == null)
                return string.Empty;
            var segments = new List<string>();
            Transform current = renderer.transform;
            while (current != null)
            {
                segments.Add(current.name + "[" +
                    current.GetSiblingIndex().ToString(
                        CultureInfo.InvariantCulture) + "]");
                current = current.parent;
            }
            segments.Reverse();
            return string.Join("/", segments.ToArray());
        }

        private static bool IsRequested(
            string environmentVariable,
            string commandLineArgument)
        {
            string value = Environment.GetEnvironmentVariable(environmentVariable);
            if (IsEnabled(value))
                return true;
            string[] arguments = Environment.GetCommandLineArgs();
            for (int i = 0; i < arguments.Length; i++)
            {
                string argument = arguments[i];
                if (string.Equals(
                        argument,
                        commandLineArgument,
                        StringComparison.OrdinalIgnoreCase))
                    return true;
                string prefix = commandLineArgument + "=";
                if (argument.StartsWith(
                        prefix,
                        StringComparison.OrdinalIgnoreCase) &&
                    IsEnabled(argument.Substring(prefix.Length)))
                    return true;
            }
            return false;
        }

        private static bool IsEnabled(string value)
        {
            if (string.IsNullOrWhiteSpace(value))
                return false;
            string normalized = value.Trim();
            return string.Equals(normalized, "1", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(normalized, "true", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(normalized, "yes", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(normalized, "on", StringComparison.OrdinalIgnoreCase);
        }

        private static void RestoreTarget(
            ScriptableRenderContext context,
            RenderTargetIdentifier color,
            RenderTexture depth)
        {
            var commandBuffer = new CommandBuffer
            {
                name = "Restore target after recovered sceneMV render pass"
            };
            commandBuffer.SetRenderTarget(color, depth);
            context.ExecuteCommandBuffer(commandBuffer);
            commandBuffer.Release();
        }

        internal static void ReleaseRenderTexture(RenderTexture texture)
        {
            if (texture == null)
                return;
            if (texture.IsCreated())
                texture.Release();
            if (Application.isPlaying)
                UnityEngine.Object.Destroy(texture);
            else
                UnityEngine.Object.DestroyImmediate(texture);
        }
    }
}
