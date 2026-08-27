using System;
using System.Collections.Generic;
using System.Globalization;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Default-off compatibility owner for the source CharacterNPR PreGBuffer
    /// depth/stencil write. Unlike the offscreen diagnostic, this path binds
    /// the exact depth attachment consumed by the following opaque Forward
    /// renderer list. Source Equal is restored only after that command buffer
    /// has executed successfully; every validation failure retains LEqual.
    /// </summary>
    internal sealed class EndfieldRecoveredPreGBufferDepthOwner : IDisposable
    {
        internal const string EnvironmentVariable =
            "ENDFIELD_RECOVERED_PREGBUFFER_DEPTH_OWNER";
        internal const string CommandLineArgument =
            "-endfield-recovered-pregbuffer-depth-owner";

        private const string CharacterPassName = "RECOVERED_PREGBUFFER_DIAGNOSTIC";
        private const string ForwardPassName = "FORWARD";
        private const string DepthOnlyShaderName =
            "Hidden/Endfield/HGRPCompat/RecoveredPreGBufferDepthOnly";
        private const string ReferenceBackdropShaderName =
            "Endfield/CharacterRecovery/ReferenceBackdrop";
        private const string CanonicalFiveMrtKeyword =
            "ENDFIELD_RECOVERED_CANONICAL_FIVE_MRT";
        private const string SourceZTestPropertyName = "_RecoveredSourceZTest";
        private const int MaximumCharacterCount = 15;

        private static readonly GraphicsFormat ExactGBufferFormat =
            GraphicsFormat.A2B10G10R10_UNormPack32;
        private static readonly GraphicsFormat ExactGBufferCFormat =
            GraphicsFormat.R8G8B8A8_SRGB;
        private static readonly int GBufferAId =
            Shader.PropertyToID("_EndfieldRecoveredCanonicalPreGBufferA");
        private static readonly int GBufferBId =
            Shader.PropertyToID("_EndfieldRecoveredCanonicalPreGBufferB");
        private static readonly int GBufferCId =
            Shader.PropertyToID("_EndfieldRecoveredCanonicalPreGBufferC");
        private static readonly int SelectorBitsId =
            Shader.PropertyToID("_EndfieldRecoveredPreGBufferSelectorBits");
        private static readonly int ZTestId = Shader.PropertyToID("_ZTest");
        private static readonly int ZWriteId = Shader.PropertyToID("_ZWrite");
        private static readonly int SourceZTestId =
            Shader.PropertyToID(SourceZTestPropertyName);
        private static readonly int ReadyId =
            Shader.PropertyToID("_EndfieldRecoveredPreGBufferDepthOwnerReady");
        private static readonly int FiveMrtReadyId = Shader.PropertyToID(
            "_EndfieldRecoveredCanonicalCharacterPreGBufferReady");

        private static readonly HashSet<string> SupportedCharacterShaders =
            new HashSet<string>(StringComparer.Ordinal)
            {
                "Endfield/Recovered/CharacterCloth",
                "Endfield/Recovered/CharacterSkin",
                "Endfield/Recovered/CharacterEye",
                "Endfield/Recovered/CharacterHair"
            };

        private sealed class CharacterDraw
        {
            internal Renderer renderer;
            internal Material material;
            internal int submesh;
            internal int pass;
            internal Transform actorRoot;
            internal int renderQueue;
            internal float cameraDistanceSquared;
            internal string stableKey;
        }

        private sealed class GenericDepthDraw
        {
            internal Renderer renderer;
            internal int submesh;
            internal string stableKey;
        }

        private readonly struct MaterialState
        {
            internal readonly Material material;
            internal readonly float sourceZTest;

            internal MaterialState(Material material, float sourceZTest)
            {
                this.material = material;
                this.sourceZTest = sourceZTest;
            }
        }

        private readonly bool requested;
        private Material depthOnlyMaterial;
        private RenderTexture gBufferA;
        private RenderTexture gBufferB;
        private RenderTexture gBufferC;
        private Camera publicationCamera;
        private int publicationWidth;
        private int publicationHeight;
        private int publicationFrame = -1;
        private bool publicationReady;
        private string lastLoggedDrawSignature = string.Empty;
        private bool loggedFailure;
        private bool disposed;

        internal bool Requested => requested;

        internal EndfieldRecoveredPreGBufferDepthOwner()
        {
            requested = IsRequested();
            Shader.SetGlobalFloat(ReadyId, 0.0f);
            Shader.SetGlobalFloat(FiveMrtReadyId, 0.0f);
            if (!requested)
                return;

            Shader shader = Shader.Find(DepthOnlyShaderName);
            if (shader != null && shader.isSupported)
            {
                depthOnlyMaterial = new Material(shader)
                {
                    hideFlags = HideFlags.HideAndDontSave,
                    name = "Recovered canonical PreG generic depth owner"
                };
            }
        }

        public void Dispose()
        {
            if (disposed)
                return;
            disposed = true;
            Shader.SetGlobalFloat(ReadyId, 0.0f);
            Shader.SetGlobalFloat(FiveMrtReadyId, 0.0f);
            publicationReady = false;
            publicationCamera = null;
            publicationFrame = -1;
            ResetAllRecoveredCharacterZTestsToCompatibility();
            ReleaseGBuffer(ref gBufferA);
            ReleaseGBuffer(ref gBufferB);
            ReleaseGBuffer(ref gBufferC);
            if (depthOnlyMaterial != null)
            {
                if (Application.isPlaying)
                    UnityEngine.Object.Destroy(depthOnlyMaterial);
                else
                    UnityEngine.Object.DestroyImmediate(depthOnlyMaterial);
                depthOnlyMaterial = null;
            }
        }

        internal bool RenderCanonicalOwner(
            ScriptableRenderContext context,
            Camera camera,
            int width,
            int height,
            RenderTargetIdentifier canonicalColorTarget,
            RenderTexture canonicalSceneMV,
            RenderTargetIdentifier canonicalDepthTarget,
            bool canonicalDepthIsSeparate,
            GraphicsFormat canonicalDepthFormat,
            out string failure)
        {
            Shader.SetGlobalFloat(ReadyId, 0.0f);
            Shader.SetGlobalFloat(FiveMrtReadyId, 0.0f);
            publicationReady = false;
            publicationCamera = null;
            publicationFrame = -1;
            failure = "the source-gated canonical CharacterPrePass owner is disabled";
            if (!requested)
                return false;
            if (disposed)
                throw new ObjectDisposedException(nameof(EndfieldRecoveredPreGBufferDepthOwner));
            if (camera == null)
            {
                failure = "camera is null";
                return LogFailure(failure);
            }

            // This reset occurs before every validation branch. A material that
            // succeeded on a prior frame therefore cannot remain Equal when a
            // later frame loses the shared owner/resource contract.
            ResetCandidateZTestsToCompatibility(camera);

            if (depthOnlyMaterial == null)
            {
                failure = $"required shader '{DepthOnlyShaderName}' is missing or unsupported";
                return LogFailure(failure);
            }
            if (!canonicalDepthIsSeparate ||
                canonicalDepthFormat != GraphicsFormat.D32_SFloat_S8_UInt)
            {
                failure =
                    "canonical five-MRT CharacterPrePass requires the captured " +
                    $"separate D32_SFloat_S8_UInt depth/stencil owner; actual={canonicalDepthFormat}";
                return LogFailure(failure);
            }
            if (canonicalSceneMV == null || !canonicalSceneMV.IsCreated() ||
                canonicalSceneMV.width != width || canonicalSceneMV.height != height ||
                canonicalSceneMV.graphicsFormat !=
                    EndfieldRecoveredSceneMVCompositor.SceneMVFormat)
            {
                failure =
                    "canonical five-MRT CharacterPrePass requires the same-frame " +
                    "A2B10G10R10 SceneMV attachment";
                return LogFailure(failure);
            }
            if (SystemInfo.supportedRenderTargetCount < 5)
            {
                failure = "the graphics device cannot bind five recovered CharacterNPR targets";
                return LogFailure(failure);
            }
            if (!SystemInfo.IsFormatSupported(ExactGBufferFormat, FormatUsage.Render) ||
                !SystemInfo.IsFormatSupported(ExactGBufferCFormat, FormatUsage.Render))
            {
                failure =
                    $"exact CharacterNPR render-target support is unavailable: " +
                    $"A/B={ExactGBufferFormat}, C={ExactGBufferCFormat}";
                return LogFailure(failure);
            }

            List<GenericDepthDraw> genericDepthDraws;
            List<CharacterDraw> characterDraws;
            List<MaterialState> materialStates;
            if (!TryCollectDraws(
                    camera,
                    out genericDepthDraws,
                    out characterDraws,
                    out materialStates,
                    out failure))
            {
                return LogFailure(failure);
            }
            if (characterDraws.Count == 0)
            {
                failure = "no visible opaque recovered CharacterNPR draw requires the canonical owner";
                return LogFailure(failure);
            }

            int actorCount;
            Dictionary<Transform, int> actorIndices =
                BuildActorIndices(characterDraws, out actorCount);
            if (actorCount > MaximumCharacterCount)
            {
                failure =
                    $"{actorCount} visible character roots exceed the source selector capacity {MaximumCharacterCount}";
                return LogFailure(failure);
            }

            if (!EnsureGBuffers(width, height, out failure))
                return LogFailure(failure);
            var commandBuffer = new CommandBuffer
            {
                name = "Recovered canonical CharacterPrePass depth owner"
            };
            try
            {
                commandBuffer.SetRenderTarget(gBufferA);
                commandBuffer.ClearRenderTarget(false, true, Color.clear);
                commandBuffer.SetRenderTarget(gBufferB);
                commandBuffer.ClearRenderTarget(false, true, Color.clear);
                commandBuffer.SetRenderTarget(gBufferC);
                commandBuffer.ClearRenderTarget(false, true, Color.clear);
                commandBuffer.SetRenderTarget(canonicalSceneMV);
                commandBuffer.ClearRenderTarget(
                    false,
                    true,
                    EndfieldRecoveredSceneMVCompositor.SceneMVNeutral);
                HDRenderPipeline.ReportRecoveredSceneMVNeutralInitialization();
                RenderTargetIdentifier[] mrt =
                {
                    canonicalColorTarget,
                    new RenderTargetIdentifier(canonicalSceneMV),
                    new RenderTargetIdentifier(gBufferA),
                    new RenderTargetIdentifier(gBufferB),
                    new RenderTargetIdentifier(gBufferC)
                };
                commandBuffer.SetRenderTarget(mrt, canonicalDepthTarget);

                foreach (GenericDepthDraw draw in genericDepthDraws)
                {
                    commandBuffer.DrawRenderer(
                        draw.renderer,
                        depthOnlyMaterial,
                        draw.submesh,
                        0);
                }

                commandBuffer.EnableShaderKeyword(CanonicalFiveMrtKeyword);
                foreach (CharacterDraw draw in characterDraws)
                {
                    int actorIndex;
                    if (draw.actorRoot == null ||
                        !actorIndices.TryGetValue(draw.actorRoot, out actorIndex))
                    {
                        failure = draw.stableKey +
                            ": no deterministic source character selector slot";
                        return LogFailure(failure);
                    }
                    commandBuffer.SetGlobalInt(
                        SelectorBitsId,
                        unchecked((int)CharacterSelectorBits(actorIndex)));
                    commandBuffer.DrawRenderer(
                        draw.renderer,
                        draw.material,
                        draw.submesh,
                        draw.pass);
                }
                commandBuffer.DisableShaderKeyword(CanonicalFiveMrtKeyword);

                RestoreCanonicalTarget(
                    commandBuffer,
                    canonicalColorTarget,
                    canonicalDepthTarget,
                    canonicalDepthIsSeparate);
                commandBuffer.SetGlobalTexture(GBufferAId, gBufferA);
                commandBuffer.SetGlobalTexture(GBufferBId, gBufferB);
                commandBuffer.SetGlobalTexture(GBufferCId, gBufferC);
                context.ExecuteCommandBuffer(commandBuffer);

                // Material render state changes are deliberately deferred until
                // the owner command has executed. If any earlier branch fails,
                // source Equal remains disabled and Forward stays LEqual.
                ActivateSourceZTests(materialStates);
            }
            catch (Exception exception)
            {
                ResetMaterialStatesToCompatibility(materialStates);
                failure = "canonical PreG execution failed: " + exception.Message;
                return LogFailure(failure);
            }
            finally
            {
                commandBuffer.Release();
            }

            failure = string.Empty;
            publicationCamera = camera;
            publicationWidth = width;
            publicationHeight = height;
            publicationFrame = Time.frameCount;
            publicationReady = true;
            string[] characterKeys = characterDraws.ConvertAll(
                draw => draw.stableKey).ToArray();
            string drawList = string.Join(" | ", characterKeys);
            string[] membershipKeys = (string[])characterKeys.Clone();
            Array.Sort(membershipKeys, StringComparer.Ordinal);
            string drawSignature = string.Join(" | ", membershipKeys);
            if (!string.Equals(
                    drawSignature,
                    lastLoggedDrawSignature,
                    StringComparison.Ordinal))
            {
                Debug.Log(
                    "Recovered canonical CharacterPrePass owner active (default-off): " +
                    $"{genericDepthDraws.Count} source-safe generic depth draw(s), " +
                    $"{characterDraws.Count} opaque DepthCharacterOnly-compatible draw(s), " +
                    "captured five-MRT topology B10G11R11/A2B10G10R10/" +
                    "A2B10G10R10/A2B10G10R10/R8G8B8A8_SRGB, and the same " +
                    "D32S8 attachment consumed by the following opaque Forward list. " +
                    "CharacterNPR writes zero sceneColor, packed SceneMV, selector, normal/family, " +
                    "and material payload to slots 0..4 before source-ordered ForwardOpaque. " +
                    "Source Equal is activated only after owner execution. Draws=" +
                    drawList + ".");
                lastLoggedDrawSignature = drawSignature;
            }
            Shader.SetGlobalFloat(ReadyId, 1.0f);
            Shader.SetGlobalFloat(FiveMrtReadyId, 1.0f);
            return true;
        }

        internal bool TryGetCurrentPublication(
            Camera camera,
            int width,
            int height,
            out RenderTexture publishedGBufferA,
            out RenderTexture publishedGBufferB,
            out RenderTexture publishedGBufferC,
            out string failure)
        {
            publishedGBufferA = null;
            publishedGBufferB = null;
            publishedGBufferC = null;
            failure = string.Empty;
            if (!HasCurrentPublication(camera, width, height) ||
                !IsCreated(gBufferA) || !IsCreated(gBufferB) || !IsCreated(gBufferC))
            {
                failure =
                    "the canonical CharacterNPR five-MRT owner has no matching current-frame publication";
                return false;
            }
            publishedGBufferA = gBufferA;
            publishedGBufferB = gBufferB;
            publishedGBufferC = gBufferC;
            return true;
        }

        internal bool HasCurrentPublication(Camera camera, int width, int height)
        {
            return publicationReady && camera != null && camera == publicationCamera &&
                width == publicationWidth && height == publicationHeight &&
                publicationFrame == Time.frameCount;
        }

        private bool EnsureGBuffers(int width, int height, out string failure)
        {
            width = Mathf.Max(width, 1);
            height = Mathf.Max(height, 1);
            if (Matches(gBufferA, width, height, ExactGBufferFormat) &&
                Matches(gBufferB, width, height, ExactGBufferFormat) &&
                Matches(gBufferC, width, height, ExactGBufferCFormat))
            {
                failure = string.Empty;
                return true;
            }

            ReleaseGBuffer(ref gBufferA);
            ReleaseGBuffer(ref gBufferB);
            ReleaseGBuffer(ref gBufferC);
            gBufferA = CreateGBuffer(
                width,
                height,
                ExactGBufferFormat,
                "Recovered canonical CharacterNPR GBuffer A");
            gBufferB = CreateGBuffer(
                width,
                height,
                ExactGBufferFormat,
                "Recovered canonical CharacterNPR GBuffer B");
            gBufferC = CreateGBuffer(
                width,
                height,
                ExactGBufferCFormat,
                "Recovered canonical CharacterNPR GBuffer C");
            if (!IsCreated(gBufferA) || !IsCreated(gBufferB) || !IsCreated(gBufferC))
            {
                ReleaseGBuffer(ref gBufferA);
                ReleaseGBuffer(ref gBufferB);
                ReleaseGBuffer(ref gBufferC);
                failure =
                    "failed to allocate the exact CharacterNPR A/B/C attachments";
                return false;
            }
            failure = string.Empty;
            return true;
        }

        private static RenderTexture CreateGBuffer(
            int width,
            int height,
            GraphicsFormat format,
            string name)
        {
            var descriptor = new RenderTextureDescriptor(width, height)
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
                sRGB = format == GraphicsFormat.R8G8B8A8_SRGB,
                useDynamicScale = false
            };
            var texture = new RenderTexture(descriptor)
            {
                name = name,
                hideFlags = HideFlags.HideAndDontSave,
                filterMode = FilterMode.Point,
                wrapMode = TextureWrapMode.Clamp
            };
            if (!texture.Create())
            {
                if (Application.isPlaying)
                    UnityEngine.Object.Destroy(texture);
                else
                    UnityEngine.Object.DestroyImmediate(texture);
                return null;
            }
            return texture;
        }

        private static bool Matches(
            RenderTexture texture,
            int width,
            int height,
            GraphicsFormat format)
        {
            return IsCreated(texture) && texture.width == width &&
                   texture.height == height && texture.graphicsFormat == format &&
                   texture.depthStencilFormat == GraphicsFormat.None &&
                   texture.antiAliasing == 1;
        }

        private static bool IsCreated(RenderTexture texture)
        {
            return texture != null && texture.IsCreated();
        }

        private static void ReleaseGBuffer(ref RenderTexture texture)
        {
            if (texture == null)
                return;
            if (texture.IsCreated())
                texture.Release();
            if (Application.isPlaying)
                UnityEngine.Object.Destroy(texture);
            else
                UnityEngine.Object.DestroyImmediate(texture);
            texture = null;
        }

        private bool TryCollectDraws(
            Camera camera,
            out List<GenericDepthDraw> genericDepthDraws,
            out List<CharacterDraw> characterDraws,
            out List<MaterialState> materialStates,
            out string failure)
        {
            genericDepthDraws = new List<GenericDepthDraw>();
            characterDraws = new List<CharacterDraw>();
            materialStates = new List<MaterialState>();
            failure = string.Empty;
            var seenMaterials = new HashSet<Material>();
            Renderer[] renderers = UnityEngine.Object.FindObjectsOfType<Renderer>();
            Array.Sort(renderers, CompareRenderers);
            Plane[] frustumPlanes = GeometryUtility.CalculateFrustumPlanes(camera);

            foreach (Renderer renderer in renderers)
            {
                if (!IsRendererVisibleToCamera(renderer, camera, frustumPlanes))
                    continue;
                Material[] materials = renderer.sharedMaterials;
                for (int submesh = 0; submesh < materials.Length; submesh++)
                {
                    Material material = materials[submesh];
                    if (material == null || material.shader == null)
                        continue;
                    bool opaque =
                        material.renderQueue <= (int)RenderQueue.GeometryLast;
                    string shaderName = material.shader.name;
                    if (SupportedCharacterShaders.Contains(shaderName))
                    {
                        if (!opaque)
                            continue;
                        if (!material.HasProperty(SourceZTestId))
                        {
                            failure = shaderName + "/" + material.name +
                                $": missing {SourceZTestPropertyName}";
                            return false;
                        }
                        float sourceZTest = material.GetFloat(SourceZTestId);
                        if (!ApproximatelyCompareFunction(
                                sourceZTest,
                                CompareFunction.Equal) &&
                            !ApproximatelyCompareFunction(
                                sourceZTest,
                                CompareFunction.LessEqual))
                        {
                            failure = shaderName + "/" + material.name +
                                $": unsupported opaque source ZTest {sourceZTest:0.###}";
                            return false;
                        }
                        if (!material.HasProperty(ZWriteId) ||
                            material.GetFloat(ZWriteId) < 0.5f)
                        {
                            failure = shaderName + "/" + material.name +
                                ": opaque source owner requires ZWrite On";
                            return false;
                        }
                        int preGPass = material.FindPass(CharacterPassName);
                        int forwardPass = material.FindPass(ForwardPassName);
                        if (preGPass < 0 || forwardPass < 0)
                        {
                            failure = shaderName + "/" + material.name +
                                $": missing {CharacterPassName} and/or {ForwardPassName}";
                            return false;
                        }
                        if (seenMaterials.Add(material))
                            materialStates.Add(new MaterialState(material, sourceZTest));
                        characterDraws.Add(new CharacterDraw
                        {
                            renderer = renderer,
                            material = material,
                            submesh = submesh,
                            pass = preGPass,
                            actorRoot = ResolveActorRoot(renderer),
                            renderQueue = material.renderQueue,
                            cameraDistanceSquared =
                                (renderer.bounds.center - camera.transform.position).sqrMagnitude,
                            stableKey = BuildRendererKey(renderer) + "/" +
                                submesh.ToString("D4", CultureInfo.InvariantCulture) + "/" +
                                material.name
                        });
                        continue;
                    }

                    if (!opaque ||
                        string.Equals(
                            shaderName,
                            ReferenceBackdropShaderName,
                            StringComparison.Ordinal) ||
                        IsSourceBackedCharInfoPassAfterCharacterPreG(renderer, material))
                        continue;
                    if (shaderName.StartsWith("Endfield/Recovered/", StringComparison.Ordinal))
                    {
                        failure = shaderName + "/" + material.name +
                            ": unsupported recovered opaque family in the canonical pre-depth set";
                        return false;
                    }
                    if (HasAlphaTest(material))
                    {
                        failure = shaderName + "/" + material.name +
                            ": alpha-tested generic depth coverage is not source-closed";
                        return false;
                    }
                    genericDepthDraws.Add(new GenericDepthDraw
                    {
                        renderer = renderer,
                        submesh = submesh,
                        stableKey = BuildRendererKey(renderer) + "/" +
                            submesh.ToString("D4", CultureInfo.InvariantCulture) + "/" +
                            material.name
                    });
                }
            }

            characterDraws.Sort(CompareCharacterDraws);
            genericDepthDraws.Sort(
                (left, right) => string.CompareOrdinal(left.stableKey, right.stableKey));
            return true;
        }

        private static void RestoreCanonicalTarget(
            CommandBuffer commandBuffer,
            RenderTargetIdentifier canonicalColorTarget,
            RenderTargetIdentifier canonicalDepthTarget,
            bool canonicalDepthIsSeparate)
        {
            if (canonicalDepthIsSeparate)
                commandBuffer.SetRenderTarget(canonicalColorTarget, canonicalDepthTarget);
            else
                commandBuffer.SetRenderTarget(canonicalColorTarget);
        }

        private static void ActivateSourceZTests(List<MaterialState> states)
        {
            foreach (MaterialState state in states)
            {
                if (state.material != null && state.material.HasProperty(ZTestId))
                    state.material.SetFloat(ZTestId, state.sourceZTest);
            }
        }

        private static void ResetMaterialStatesToCompatibility(
            List<MaterialState> states)
        {
            foreach (MaterialState state in states)
            {
                if (state.material != null && state.material.HasProperty(ZTestId))
                {
                    state.material.SetFloat(
                        ZTestId,
                        (float)CompareFunction.LessEqual);
                }
            }
        }

        private static void ResetCandidateZTestsToCompatibility(Camera camera)
        {
            Renderer[] renderers = UnityEngine.Object.FindObjectsOfType<Renderer>();
            Plane[] frustumPlanes = GeometryUtility.CalculateFrustumPlanes(camera);
            foreach (Renderer renderer in renderers)
            {
                if (!IsRendererVisibleToCamera(renderer, camera, frustumPlanes))
                    continue;
                foreach (Material material in renderer.sharedMaterials)
                {
                    if (material == null || material.shader == null ||
                        material.renderQueue > (int)RenderQueue.GeometryLast ||
                        !SupportedCharacterShaders.Contains(material.shader.name) ||
                        !material.HasProperty(ZTestId))
                    {
                        continue;
                    }
                    material.SetFloat(ZTestId, (float)CompareFunction.LessEqual);
                }
            }
        }

        private static void ResetAllRecoveredCharacterZTestsToCompatibility()
        {
            Renderer[] renderers = UnityEngine.Object.FindObjectsOfType<Renderer>();
            foreach (Renderer renderer in renderers)
            {
                if (renderer == null)
                    continue;
                foreach (Material material in renderer.sharedMaterials)
                {
                    if (material == null || material.shader == null ||
                        !SupportedCharacterShaders.Contains(material.shader.name) ||
                        !material.HasProperty(ZTestId))
                    {
                        continue;
                    }
                    material.SetFloat(ZTestId, (float)CompareFunction.LessEqual);
                }
            }
        }

        private bool LogFailure(string failure)
        {
            if (!loggedFailure)
            {
                Debug.LogWarning(
                    "Recovered canonical CharacterPrePass owner was requested but failed " +
                    $"closed: {failure}. Opaque recovered characters retain LEqual.");
                loggedFailure = true;
            }
            return false;
        }

        private static bool HasAlphaTest(Material material)
        {
            return material.IsKeywordEnabled("_ALPHATEST_ON") ||
                   (material.HasProperty("_AlphaClip") &&
                    material.GetFloat("_AlphaClip") > 0.5f) ||
                   (material.HasProperty("_EnableAlphaTest") &&
                    material.GetFloat("_EnableAlphaTest") > 0.5f);
        }

        private static bool ApproximatelyCompareFunction(
            float value,
            CompareFunction function)
        {
            return Mathf.Abs(value - (float)function) < 0.01f;
        }

        private static Dictionary<Transform, int> BuildActorIndices(
            List<CharacterDraw> draws,
            out int actorCount)
        {
            var roots = new List<Transform>();
            var seen = new HashSet<Transform>();
            foreach (CharacterDraw draw in draws)
            {
                if (draw.actorRoot != null && seen.Add(draw.actorRoot))
                    roots.Add(draw.actorRoot);
            }
            roots.Sort((left, right) =>
                string.CompareOrdinal(BuildTransformPath(left), BuildTransformPath(right)));
            actorCount = roots.Count;
            var result = new Dictionary<Transform, int>();
            for (int i = 0; i < roots.Count && i < MaximumCharacterCount; i++)
                result.Add(roots[i], i);
            return result;
        }

        private static Transform ResolveActorRoot(Renderer renderer)
        {
            CharacterRecoveryRig rig = renderer.GetComponentInParent<CharacterRecoveryRig>();
            if (rig != null)
                return rig.transform;
            Transform current = renderer.transform;
            while (current != null)
            {
                if (current.parent != null &&
                    string.Equals(
                        current.parent.name,
                        "Characters",
                        StringComparison.OrdinalIgnoreCase))
                {
                    return current;
                }
                current = current.parent;
            }
            return renderer.transform.root;
        }

        private static bool IsSourceBackedCharInfoPassAfterCharacterPreG(
            Renderer renderer,
            Material material)
        {
            if (renderer == null || material == null || material.shader == null ||
                renderer.gameObject.layer != 13)
            {
                return false;
            }
            EndfieldRecoveredCharInfoPresentation presentation =
                renderer.GetComponentInParent<EndfieldRecoveredCharInfoPresentation>();
            if (presentation == null)
                return false;
            string shaderName = material.shader.name;
            if (renderer == presentation.floorRenderer)
            {
                return material.renderQueue == (int)RenderQueue.Geometry &&
                       string.Equals(
                           shaderName,
                           EndfieldRecoveredCharInfoPresentation.FloorShaderName,
                           StringComparison.Ordinal);
            }
            if (renderer == presentation.wallRenderer)
            {
                return material.renderQueue == (int)RenderQueue.Geometry &&
                       string.Equals(
                           shaderName,
                           EndfieldRecoveredCharInfoPresentation.WallShaderName,
                           StringComparison.Ordinal);
            }
            return false;
        }

        private static bool IsRendererVisibleToCamera(
            Renderer renderer,
            Camera camera,
            Plane[] frustumPlanes)
        {
            return renderer != null && renderer.enabled &&
                   renderer.gameObject.activeInHierarchy &&
                   (camera.cullingMask & (1 << renderer.gameObject.layer)) != 0 &&
                   GeometryUtility.TestPlanesAABB(frustumPlanes, renderer.bounds);
        }

        private static int CompareRenderers(Renderer left, Renderer right)
        {
            return string.CompareOrdinal(BuildRendererKey(left), BuildRendererKey(right));
        }

        private static int CompareCharacterDraws(CharacterDraw left, CharacterDraw right)
        {
            int queue = left.renderQueue.CompareTo(right.renderQueue);
            if (queue != 0)
                return queue;
            int distance = left.cameraDistanceSquared.CompareTo(right.cameraDistanceSquared);
            if (distance != 0)
                return distance;
            return string.CompareOrdinal(left.stableKey, right.stableKey);
        }

        private static string BuildRendererKey(Renderer renderer)
        {
            return renderer == null
                ? string.Empty
                : BuildTransformPath(renderer.transform) + "/" + renderer.GetType().Name;
        }

        private static string BuildTransformPath(Transform transform)
        {
            if (transform == null)
                return string.Empty;
            var names = new Stack<string>();
            Transform current = transform;
            while (current != null)
            {
                names.Push(current.name);
                current = current.parent;
            }
            return string.Join("/", names.ToArray());
        }

        private static uint CharacterSelectorBits(int index)
        {
            return index < 0 ? 0u : 1u << ((index + 8) & 31);
        }

        private static bool IsRequested()
        {
            bool enabled = IsEnabledValue(
                Environment.GetEnvironmentVariable(EnvironmentVariable));
            string[] arguments = Environment.GetCommandLineArgs();
            for (int i = 0; i < arguments.Length; i++)
            {
                string argument = arguments[i];
                if (string.Equals(
                        argument,
                        CommandLineArgument,
                        StringComparison.OrdinalIgnoreCase))
                {
                    enabled = true;
                    continue;
                }
                string prefix = CommandLineArgument + "=";
                if (argument.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                    enabled = IsEnabledValue(argument.Substring(prefix.Length));
            }
            return enabled;
        }

        private static bool IsEnabledValue(string value)
        {
            if (string.IsNullOrWhiteSpace(value))
                return false;
            string normalized = value.Trim();
            return string.Equals(normalized, "1", StringComparison.OrdinalIgnoreCase) ||
                   string.Equals(normalized, "true", StringComparison.OrdinalIgnoreCase) ||
                   string.Equals(normalized, "yes", StringComparison.OrdinalIgnoreCase) ||
                   string.Equals(normalized, "on", StringComparison.OrdinalIgnoreCase);
        }
    }
}
