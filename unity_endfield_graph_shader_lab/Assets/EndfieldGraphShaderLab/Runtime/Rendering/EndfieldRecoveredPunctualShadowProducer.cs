using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Source-backed, isolated reconstruction of the original overview
    /// punctual-shadow producer. It intentionally owns only the validated
    /// Wulfa/Zhuangfy target and Endminf RimLight_2/RimLight_2 (1) rows, and
    /// publishes no cache slot unless every recovered
    /// identity, resource, projection, atlas, and caster condition is valid.
    /// </summary>
    internal sealed class EndfieldRecoveredPunctualShadowProducer : IDisposable
    {
        internal const int CacheSlotCount = 56;
        internal const int DynamicCacheBase = 40;
        internal const int EnvironmentDynamicCapacity = 6;
        internal const int MovableDynamicCapacity = 2;
        internal const int DynamicCapacity =
            EnvironmentDynamicCapacity + MovableDynamicCapacity;
        internal const int StaticAtlasTileColumns = 4;
        internal const int AtlasTileRows = 4;
        internal const int TileScissorInset = 2;
        internal const float PointGuardAngleDegrees = 2.0f;
        internal const float RasterConstantBiasScale = 2.0f;
        internal const float RasterSlopeBias = 1.0f;
        internal const float Pcf3x3BiasMultiplier = 1.5f;

        // Keep this identical to EndfieldHGOperatorLightRig.MaxLights. Endminf's
        // source RimLight_2 (1) is packed after eight earlier descriptors, so
        // the original eight-row compatibility buffer could not publish it.
        private const int MaxOperatorLights = 16;
        private const int OpaqueQueueMaximum = (int)RenderQueue.GeometryLast;
        private const string ClearShaderName =
            "Hidden/Endfield/Recovered/PunctualShadowClear";
        private const string CasterKeyword =
            "ENDFIELD_RECOVERED_CHARACTER_SHADOW_PASS_VP";
        private const string CharacterShadowProxyShaderName =
            "Hidden/Endfield/Recovered/CharacterShadowProxy";

        private static readonly int ShadowMapId =
            Shader.PropertyToID("_EndfieldRecoveredPunctualShadowMap");
        private static readonly int WorldToShadowId =
            Shader.PropertyToID("_EndfieldRecoveredPunctualWorldToShadow");
        private static readonly int ShadowParamsId =
            Shader.PropertyToID("_EndfieldRecoveredPunctualShadowParams");
        private static readonly int ShadowRectsId =
            Shader.PropertyToID("_EndfieldRecoveredPunctualShadowRects");
        private static readonly int ShadowTexelSizeId =
            Shader.PropertyToID("_EndfieldRecoveredPunctualShadowTexelSize");
        private static readonly int ShadowAvailableId =
            Shader.PropertyToID("_EndfieldRecoveredPunctualShadowAvailable");
        private static readonly int LightShadowDataId =
            Shader.PropertyToID("_EndfieldOperatorLightPunctualShadowData");
        private static readonly int CharacterShadowPassVpId =
            Shader.PropertyToID("_EndfieldCharacterShadowPassVP");
        private static readonly int WorldSpaceLightPositionId =
            Shader.PropertyToID("_WorldSpaceLightPos0");
        private static readonly int UnityLightShadowBiasId =
            Shader.PropertyToID("unity_LightShadowBias");

        private static readonly HashSet<string> SupportedCasterShaders =
            new HashSet<string>(StringComparer.Ordinal)
            {
                "Endfield/Recovered/CharacterCloth",
                "Endfield/Recovered/CharacterHair",
                "Endfield/Recovered/CharacterSkin",
                "Endfield/Recovered/CharacterEye",
                // The exact desktop LOD1 Shadow_Proxy hierarchy is created by
                // EndfieldRecoveredCharacterShadowProxyProvider. Its material
                // owns the same source-backed ShadowCaster contract and must
                // be admitted when the punctual producer enumerates the
                // actor root; rejecting it leaves b34 unavailable even though
                // the proxy mesh/material contract was recovered.
                CharacterShadowProxyShaderName
            };

        private readonly Matrix4x4[] worldToShadow =
            new Matrix4x4[CacheSlotCount];
        private readonly Vector4[] shadowParams = new Vector4[CacheSlotCount];
        private readonly Vector4[] shadowRects = new Vector4[CacheSlotCount];
        private readonly Vector4[] lightShadowData = new Vector4[MaxOperatorLights];
        private readonly Matrix4x4[] casterMatrices = new Matrix4x4[6];
        private readonly Rect[] casterRects = new Rect[6];
        private readonly List<CasterDraw> casterDraws = new List<CasterDraw>();
        private readonly Dictionary<Material, Material> cullOffCasterMaterials =
            new Dictionary<Material, Material>();

        private Material clearMaterial;
        private RenderTexture atlas;
        private int atlasTileResolution;
        private int atlasWidth;
        private int atlasHeight;
        private string lastFailure = string.Empty;
        private string lastActiveDescription = string.Empty;
        private bool publicationReady;
        private bool disposed;

        private struct CasterDraw
        {
            internal Renderer renderer;
            internal Material material;
            internal int submesh;
            internal int pass;
            internal string stableKey;
        }

        internal bool Render(
            ScriptableRenderContext context,
            Camera camera,
            EndfieldHGOperatorLightRig rig,
            RenderTargetIdentifier restoreTarget)
        {
            if (disposed)
                throw new ObjectDisposedException(nameof(EndfieldRecoveredPunctualShadowProducer));
            if (camera == null)
                throw new ArgumentNullException(nameof(camera));
            publicationReady = false;

            if (rig == null || !rig.sourceBackedIsolatedPunctualSoftShadowProducer)
            {
                BindDisabled(context);
                return false;
            }

            if (!SystemInfo.usesReversedZBuffer)
            {
                return Fail(
                    context,
                    "the active graphics backend is not reversed-Z; the recovered D16/clear-zero contract is unavailable");
            }
            // Unity's D3D12 backend can report a depth-only shadow resource as
            // unsupported for the generic FormatUsage.Sample query even though
            // it can create and bind the exact D16 depth/SRV resource.  The
            // recovered contract therefore gates on depth rendering here and
            // treats exact resource creation below as the authoritative sample
            // capability check.  Do not substitute a compatible depth format.
            if (!SystemInfo.IsFormatSupported(GraphicsFormat.D16_UNorm, FormatUsage.Render))
            {
                return Fail(context, "D16_UNorm depth-render support is unavailable");
            }

            EndfieldHGIsolatedPunctualShadowTarget target;
            string failure;
            if (!rig.TryGetIsolatedPunctualSoftShadowTarget(
                    camera,
                    out target,
                    out failure))
            {
                return Fail(context, failure);
            }
            EndfieldHGIsolatedPunctualShadowTarget secondaryTarget = default;
            int targetCount = 1;
            if (string.Equals(target.actorKey, "endminf", StringComparison.Ordinal))
            {
                if (!rig.TryGetIsolatedPunctualSoftShadowTarget(
                        camera,
                        out secondaryTarget,
                        out failure,
                        3))
                {
                    return Fail(context, failure);
                }
                targetCount = 2;
            }
            if (!BuildCasterList(target, camera, out failure))
                return Fail(context, failure);

            bool atlasWasCreated;
            if (!EnsureResources(
                    rig.sourceBackedPunctualShadowTileResolution,
                    out atlasWasCreated,
                    out failure))
            {
                return Fail(context, failure);
            }

            ClearShadowData();
            int primaryFaceCount = target.light.spot ? 1 : 6;
            if (!BuildShadowData(target, primaryFaceCount, 0, 0, out failure))
                return Fail(context, failure);
            int secondaryFaceCount = 0;
            if (targetCount == 2)
            {
                secondaryFaceCount = secondaryTarget.light.spot ? 1 : 6;
                if (!BuildShadowData(
                        secondaryTarget,
                        secondaryFaceCount,
                        primaryFaceCount,
                        primaryFaceCount,
                        out failure))
                {
                    return Fail(context, failure);
                }
            }

            CommandBuffer commandBuffer = new CommandBuffer
            {
                name = "Recovered isolated overview punctual shadows"
            };
            try
            {
                commandBuffer.SetRenderTarget(atlas);
                commandBuffer.SetGlobalVector(UnityLightShadowBiasId, Vector4.zero);

                if (atlasWasCreated)
                {
                    // The isolated topology has no static cached casters. A
                    // one-time depth-zero initialization makes the unused
                    // static square and dynamic guard borders deterministic.
                    commandBuffer.DisableScissorRect();
                    commandBuffer.SetViewport(
                        new Rect(0.0f, 0.0f, atlasWidth, atlasHeight));
                    DrawDepthZero(commandBuffer);
                }

                commandBuffer.EnableShaderKeyword(CasterKeyword);
                int matrixOffset = 0;
                for (int targetIndex = 0; targetIndex < targetCount; targetIndex++)
                {
                    EndfieldHGIsolatedPunctualShadowTarget activeTarget =
                        targetIndex == 0 ? target : secondaryTarget;
                    int activeFaceCount = targetIndex == 0
                        ? primaryFaceCount
                        : secondaryFaceCount;
                    commandBuffer.SetGlobalVector(
                        WorldSpaceLightPositionId,
                        new Vector4(
                            activeTarget.worldPosition.x,
                            activeTarget.worldPosition.y,
                            activeTarget.worldPosition.z,
                            1.0f));
                    for (int face = 0; face < activeFaceCount; face++)
                    {
                        int matrixIndex = matrixOffset + face;
                        Rect rect = casterRects[matrixIndex];
                        commandBuffer.SetViewport(rect);
                        commandBuffer.EnableScissorRect(new Rect(
                            rect.x + TileScissorInset,
                            rect.y + TileScissorInset,
                            rect.width - TileScissorInset * 2,
                            rect.height - TileScissorInset * 2));
                        DrawDepthZero(commandBuffer);
                        commandBuffer.SetGlobalMatrix(
                            CharacterShadowPassVpId,
                            casterMatrices[matrixIndex]);
                        commandBuffer.SetGlobalDepthBias(
                            RasterConstantBiasScale * activeTarget.light.shadowBias,
                            RasterSlopeBias);

                        for (int drawIndex = 0; drawIndex < casterDraws.Count; drawIndex++)
                        {
                            CasterDraw draw = casterDraws[drawIndex];
                            commandBuffer.DrawRenderer(
                                draw.renderer,
                                draw.material,
                                draw.submesh,
                                draw.pass);
                        }

                        commandBuffer.DisableScissorRect();
                        commandBuffer.SetGlobalDepthBias(0.0f, 0.0f);
                    }
                    matrixOffset += activeFaceCount;
                }
                commandBuffer.DisableShaderKeyword(CasterKeyword);

                commandBuffer.SetGlobalTexture(ShadowMapId, atlas);
                commandBuffer.SetGlobalMatrixArray(WorldToShadowId, worldToShadow);
                commandBuffer.SetGlobalVectorArray(ShadowParamsId, shadowParams);
                commandBuffer.SetGlobalVectorArray(ShadowRectsId, shadowRects);
                commandBuffer.SetGlobalVector(
                    ShadowTexelSizeId,
                    new Vector4(
                        1.0f / atlasWidth,
                        1.0f / atlasHeight,
                        atlasWidth,
                        atlasHeight));
                commandBuffer.SetGlobalVectorArray(LightShadowDataId, lightShadowData);
                commandBuffer.SetGlobalFloat(ShadowAvailableId, 1.0f);
                commandBuffer.SetRenderTarget(restoreTarget);
                context.ExecuteCommandBuffer(commandBuffer);
            }
            catch (Exception exception)
            {
                commandBuffer.SetGlobalDepthBias(0.0f, 0.0f);
                commandBuffer.DisableShaderKeyword(CasterKeyword);
                commandBuffer.DisableScissorRect();
                commandBuffer.Clear();
                commandBuffer.Release();
                return Fail(context, "render command construction failed: " + exception.Message);
            }
            commandBuffer.Release();
            publicationReady = true;

            lastFailure = string.Empty;
            string activeDescription =
                $"{target.actorKey}: rows " +
                (targetCount == 2
                    ? $"{secondaryTarget.sourceIndex}/{target.sourceIndex}, packed lights " +
                      $"{secondaryTarget.packedIndex}/{target.packedIndex}"
                    : $"{target.sourceIndex}, packed light {target.packedIndex}") +
                $", slots 40..{39 + primaryFaceCount + secondaryFaceCount}, B={atlasTileResolution}, " +
                $"atlas={atlasWidth}x{atlasHeight}, D16, casters={casterDraws.Count}";
            if (!string.Equals(
                    activeDescription,
                    lastActiveDescription,
                    StringComparison.Ordinal))
            {
                Debug.Log(
                    "Recovered isolated punctual soft-shadow producer active: " +
                    activeDescription +
                    ". Receiver/raster bias, point bases, projections, 2px scissor, " +
                    "and static+dynamic actor-caster inclusion are source-backed.");
                lastActiveDescription = activeDescription;
            }
            return true;
        }

        internal bool TryGetCurrentPublication(
            out Matrix4x4[] publishedWorldToShadow,
            out Vector4[] publishedShadowParams,
            out Vector4[] publishedShadowRects,
            out Vector4 publishedTexelSize,
            out RenderTexture publishedAtlas,
            out string failure)
        {
            publishedWorldToShadow = null;
            publishedShadowParams = null;
            publishedShadowRects = null;
            publishedTexelSize = Vector4.zero;
            publishedAtlas = null;
            failure = string.Empty;
            if (!publicationReady || atlas == null || !atlas.IsCreated() ||
                atlasWidth <= 0 || atlasHeight <= 0)
            {
                failure =
                    "the isolated punctual-shadow producer has no current-frame publication";
                return false;
            }
            publishedWorldToShadow = worldToShadow;
            publishedShadowParams = shadowParams;
            publishedShadowRects = shadowRects;
            publishedTexelSize = new Vector4(
                1.0f / atlasWidth,
                1.0f / atlasHeight,
                atlasWidth,
                atlasHeight);
            publishedAtlas = atlas;
            return true;
        }

        private void ClearShadowData()
        {
            Array.Clear(worldToShadow, 0, worldToShadow.Length);
            Array.Clear(shadowParams, 0, shadowParams.Length);
            Array.Clear(shadowRects, 0, shadowRects.Length);
            for (int index = 0; index < lightShadowData.Length; index++)
                lightShadowData[index] = new Vector4(-1.0f, 0.0f, 0.0f, 0.0f);
        }

        private bool BuildShadowData(
            EndfieldHGIsolatedPunctualShadowTarget target,
            int faceCount,
            int slotOffset,
            int matrixOffset,
            out string failure)
        {
            failure = string.Empty;

            float fieldOfView = target.light.spot
                ? Mathf.Clamp(
                    target.light.outerSpotAngle + target.light.shadowGuardAngle,
                    0.0f,
                    179.9f)
                : 90.0f + PointGuardAngleDegrees;
            float nearPlane = Mathf.Max(target.light.shadowNearPlane, 0.0001f);
            float farPlane = Mathf.Clamp(
                target.light.shadowFarPlane,
                nearPlane,
                nearPlane * 10000000.0f);
            Matrix4x4 sourceProjection = BuildSourcePerspective(
                fieldOfView,
                nearPlane,
                farPlane);
            if (!IsFinite(sourceProjection) || !(sourceProjection.m00 > 0.0f))
            {
                failure = "the recovered source projection is invalid";
                return false;
            }

            float texelWorld = (2.0f / sourceProjection.m00) / atlasTileResolution;
            Vector4 receiverParams = new Vector4(
                0.0f,
                Pcf3x3BiasMultiplier * texelWorld * target.light.shadowNormalBias,
                texelWorld,
                target.light.shadowStrength);

            for (int face = 0; face < faceCount; face++)
            {
                int slot = DynamicCacheBase + slotOffset + face;
                int dynamicIndex = slot - DynamicCacheBase;
                int tileX = StaticAtlasTileColumns + dynamicIndex / AtlasTileRows;
                int tileY = dynamicIndex & (AtlasTileRows - 1);
                Rect rect = new Rect(
                    tileX * atlasTileResolution,
                    tileY * atlasTileResolution,
                    atlasTileResolution,
                    atlasTileResolution);
                Matrix4x4 view = target.light.spot
                    ? BuildSpotView(target.worldPosition, target.worldRotation)
                    : BuildPointView(target.worldPosition, face);
                Matrix4x4 casterProjection = GL.GetGPUProjectionMatrix(
                    sourceProjection,
                    true);
                Matrix4x4 casterMatrix = casterProjection * view;
                Matrix4x4 receiverMatrix = BuildReceiverWorldToShadow(
                    sourceProjection,
                    view);
                if (!IsFinite(view) || !IsFinite(casterMatrix) || !IsFinite(receiverMatrix))
                {
                    failure = $"shadow face {face} produced a non-finite matrix";
                    return false;
                }

                casterMatrices[matrixOffset + face] = casterMatrix;
                casterRects[matrixOffset + face] = rect;
                worldToShadow[slot] = receiverMatrix;
                shadowParams[slot] = receiverParams;
                shadowRects[slot] = new Vector4(
                    rect.xMin / atlasWidth,
                    rect.yMin / atlasHeight,
                    rect.xMax / atlasWidth,
                    rect.yMax / atlasHeight);
            }

            lightShadowData[target.packedIndex] = new Vector4(
                DynamicCacheBase + slotOffset,
                faceCount,
                target.sourceIndex,
                1.0f);
            return true;
        }

        private bool BuildCasterList(
            EndfieldHGIsolatedPunctualShadowTarget target,
            Camera camera,
            out string failure)
        {
            failure = string.Empty;
            casterDraws.Clear();
            Renderer[] renderers = target.actorRoot.GetComponentsInChildren<Renderer>(true);
            for (int rendererIndex = 0; rendererIndex < renderers.Length; rendererIndex++)
            {
                Renderer renderer = renderers[rendererIndex];
                if (renderer == null || !renderer.enabled ||
                    !renderer.gameObject.activeInHierarchy ||
                    renderer.shadowCastingMode == ShadowCastingMode.Off)
                {
                    continue;
                }
                if ((camera.cullingMask & (1 << renderer.gameObject.layer)) == 0)
                    continue;

                Material[] materials = renderer.sharedMaterials;
                for (int submesh = 0; submesh < materials.Length; submesh++)
                {
                    Material sourceMaterial = materials[submesh];
                    if (sourceMaterial == null ||
                        sourceMaterial.renderQueue > OpaqueQueueMaximum)
                    {
                        continue;
                    }

                    int sourcePass = sourceMaterial.FindPass("SHADOWCASTER");
                    if (sourcePass < 0)
                        continue;
                    string shaderName = sourceMaterial.shader != null
                        ? sourceMaterial.shader.name
                        : string.Empty;
                    if (!SupportedCasterShaders.Contains(shaderName))
                    {
                        failure =
                            $"active actor material '{sourceMaterial.name}' exposes a " +
                            $"ShadowCaster pass through unsupported shader '{shaderName}'";
                        casterDraws.Clear();
                        return false;
                    }

                    Material cullOffMaterial = GetCullOffCasterMaterial(sourceMaterial);
                    int pass = cullOffMaterial.FindPass("SHADOWCASTER");
                    if (pass < 0)
                    {
                        failure =
                            $"CullOff clone of '{sourceMaterial.name}' lost its ShadowCaster pass";
                        casterDraws.Clear();
                        return false;
                    }
                    casterDraws.Add(new CasterDraw
                    {
                        renderer = renderer,
                        material = cullOffMaterial,
                        submesh = submesh,
                        pass = pass,
                        stableKey = HierarchyPath(target.actorRoot, renderer.transform) +
                            "|" + renderer.GetType().Name + "|" + submesh
                    });
                }
            }

            casterDraws.Sort((left, right) =>
                string.CompareOrdinal(left.stableKey, right.stableKey));
            if (casterDraws.Count == 0)
            {
                failure =
                    "the active actor supplies no enabled opaque recovered ShadowCaster submeshes";
                return false;
            }
            return true;
        }

        private Material GetCullOffCasterMaterial(Material source)
        {
            Material clone;
            if (!cullOffCasterMaterials.TryGetValue(source, out clone) ||
                clone == null || clone.shader != source.shader)
            {
                if (clone != null)
                    DestroyObject(clone);
                clone = new Material(source)
                {
                    hideFlags = HideFlags.HideAndDontSave,
                    name = source.name + " [Recovered Punctual Shadow CullOff]"
                };
                cullOffCasterMaterials[source] = clone;
            }
            else
            {
                clone.CopyPropertiesFromMaterial(source);
                clone.shaderKeywords = source.shaderKeywords;
                clone.renderQueue = source.renderQueue;
                clone.enableInstancing = source.enableInstancing;
            }
            clone.SetFloat("_Cull", (float)CullMode.Off);
            return clone;
        }

        private bool EnsureResources(
            int tileResolution,
            out bool atlasWasCreated,
            out string failure)
        {
            atlasWasCreated = false;
            failure = string.Empty;
            if (clearMaterial == null)
            {
                Shader shader = Shader.Find(ClearShaderName);
                if (shader == null || !shader.isSupported)
                {
                    failure = $"required shader '{ClearShaderName}' is missing or unsupported";
                    return false;
                }
                clearMaterial = new Material(shader)
                {
                    hideFlags = HideFlags.HideAndDontSave,
                    name = "Recovered Punctual Shadow Depth-Zero Clear"
                };
            }

            int dynamicColumns =
                (DynamicCapacity + AtlasTileRows - 1) / AtlasTileRows;
            int width = tileResolution * (StaticAtlasTileColumns + dynamicColumns);
            int height = tileResolution * AtlasTileRows;
            if (atlas != null && atlas.IsCreated() &&
                atlasTileResolution == tileResolution &&
                atlasWidth == width && atlasHeight == height)
            {
                return true;
            }

            ReleaseAtlas();
            var descriptor = new RenderTextureDescriptor(width, height)
            {
                graphicsFormat = GraphicsFormat.None,
                depthStencilFormat = GraphicsFormat.D16_UNorm,
                depthBufferBits = 16,
                dimension = TextureDimension.Tex2D,
                volumeDepth = 1,
                msaaSamples = 1,
                bindMS = false,
                useMipMap = false,
                autoGenerateMips = false,
                enableRandomWrite = false,
                sRGB = false,
                shadowSamplingMode = ShadowSamplingMode.CompareDepths,
                useDynamicScale = false
            };
            atlas = new RenderTexture(descriptor)
            {
                name = "Punctual Shadowmap",
                filterMode = FilterMode.Point,
                wrapMode = TextureWrapMode.Clamp,
                anisoLevel = 0,
                hideFlags = HideFlags.HideAndDontSave
            };
            if (!atlas.Create() || !atlas.IsCreated())
            {
                failure = $"could not allocate the {width}x{height} D16 punctual atlas";
                ReleaseAtlas();
                return false;
            }
            if (atlas.depthStencilFormat != GraphicsFormat.D16_UNorm)
            {
                failure =
                    $"the {width}x{height} punctual atlas was silently substituted with " +
                    $"{atlas.depthStencilFormat} instead of exact D16_UNorm";
                ReleaseAtlas();
                return false;
            }

            atlasTileResolution = tileResolution;
            atlasWidth = width;
            atlasHeight = height;
            atlasWasCreated = true;
            return true;
        }

        private static Matrix4x4 BuildSourcePerspective(
            float fieldOfViewDegrees,
            float nearPlane,
            float farPlane)
        {
            float cotangent = 1.0f / Mathf.Tan(
                fieldOfViewDegrees * Mathf.Deg2Rad * 0.5f);
            float inverseRange = 1.0f / (farPlane - nearPlane);
            Matrix4x4 projection = Matrix4x4.zero;
            projection.m00 = cotangent;
            projection.m11 = cotangent;
            projection.m22 = -(farPlane + nearPlane) * inverseRange;
            projection.m23 = -2.0f * farPlane * nearPlane * inverseRange;
            projection.m32 = -1.0f;
            return projection;
        }

        private static Matrix4x4 BuildSpotView(
            Vector3 worldPosition,
            Quaternion worldRotation)
        {
            Matrix4x4 view = Matrix4x4.TRS(
                worldPosition,
                worldRotation,
                Vector3.one).inverse;
            view.m20 = -view.m20;
            view.m21 = -view.m21;
            view.m22 = -view.m22;
            view.m23 = -view.m23;
            return view;
        }

        private static Matrix4x4 BuildPointView(Vector3 worldPosition, int face)
        {
            Matrix4x4 basis = Matrix4x4.identity;
            switch (face)
            {
                case 0: // +X
                    basis.SetRow(0, new Vector4(0.0f, 0.0f, -1.0f, 0.0f));
                    basis.SetRow(1, new Vector4(0.0f, -1.0f, 0.0f, 0.0f));
                    basis.SetRow(2, new Vector4(-1.0f, 0.0f, 0.0f, 0.0f));
                    break;
                case 1: // -X
                    basis.SetRow(0, new Vector4(0.0f, 0.0f, 1.0f, 0.0f));
                    basis.SetRow(1, new Vector4(0.0f, -1.0f, 0.0f, 0.0f));
                    basis.SetRow(2, new Vector4(1.0f, 0.0f, 0.0f, 0.0f));
                    break;
                case 2: // +Y
                    basis.SetRow(0, new Vector4(1.0f, 0.0f, 0.0f, 0.0f));
                    basis.SetRow(1, new Vector4(0.0f, 0.0f, 1.0f, 0.0f));
                    basis.SetRow(2, new Vector4(0.0f, -1.0f, 0.0f, 0.0f));
                    break;
                case 3: // -Y
                    basis.SetRow(0, new Vector4(1.0f, 0.0f, 0.0f, 0.0f));
                    basis.SetRow(1, new Vector4(0.0f, 0.0f, -1.0f, 0.0f));
                    basis.SetRow(2, new Vector4(0.0f, 1.0f, 0.0f, 0.0f));
                    break;
                case 4: // +Z
                    basis.SetRow(0, new Vector4(1.0f, 0.0f, 0.0f, 0.0f));
                    basis.SetRow(1, new Vector4(0.0f, -1.0f, 0.0f, 0.0f));
                    basis.SetRow(2, new Vector4(0.0f, 0.0f, -1.0f, 0.0f));
                    break;
                case 5: // -Z
                    basis.SetRow(0, new Vector4(-1.0f, 0.0f, 0.0f, 0.0f));
                    basis.SetRow(1, new Vector4(0.0f, -1.0f, 0.0f, 0.0f));
                    basis.SetRow(2, new Vector4(0.0f, 0.0f, 1.0f, 0.0f));
                    break;
                default:
                    throw new ArgumentOutOfRangeException(nameof(face));
            }
            return basis * Matrix4x4.TRS(
                -worldPosition,
                Quaternion.identity,
                Vector3.one);
        }

        private static Matrix4x4 BuildReceiverWorldToShadow(
            Matrix4x4 sourceProjection,
            Matrix4x4 view)
        {
            Matrix4x4 projection = GL.GetGPUProjectionMatrix(
                sourceProjection,
                false);
            // This producer refuses non-reversed backends, matching the native
            // GetShadowTransform branch for the captured PC path.
            projection.m20 = -projection.m20;
            projection.m21 = -projection.m21;
            projection.m22 = -projection.m22;
            projection.m23 = -projection.m23;
            Matrix4x4 matrix = projection * view;
            Matrix4x4 scaleOffset = Matrix4x4.identity;
            scaleOffset.m00 = 0.5f;
            scaleOffset.m11 = 0.5f;
            scaleOffset.m22 = 0.5f;
            scaleOffset.m03 = 0.5f;
            scaleOffset.m13 = 0.5f;
            scaleOffset.m23 = 0.5f;
            return scaleOffset * matrix;
        }

        private void DrawDepthZero(CommandBuffer commandBuffer)
        {
            commandBuffer.DrawProcedural(
                Matrix4x4.identity,
                clearMaterial,
                0,
                MeshTopology.Triangles,
                3,
                1);
        }

        private bool Fail(
            ScriptableRenderContext context,
            string failure)
        {
            BindDisabled(context);
            if (!string.Equals(failure, lastFailure, StringComparison.Ordinal))
            {
                Debug.LogWarning(
                    "Recovered isolated punctual soft-shadow producer stayed disabled: " +
                    failure + ". The two soft Rim rows remain exact zero; shadowless " +
                    "Rim rows keep their recovered fallback.");
                lastFailure = failure;
            }
            lastActiveDescription = string.Empty;
            return false;
        }

        private void BindDisabled(ScriptableRenderContext context)
        {
            publicationReady = false;
            for (int index = 0; index < lightShadowData.Length; index++)
                lightShadowData[index] = new Vector4(-1.0f, 0.0f, 0.0f, 0.0f);
            CommandBuffer commandBuffer = new CommandBuffer
            {
                name = "Disable recovered punctual soft shadows"
            };
            commandBuffer.SetGlobalFloat(ShadowAvailableId, 0.0f);
            commandBuffer.SetGlobalVectorArray(LightShadowDataId, lightShadowData);
            commandBuffer.SetGlobalTexture(ShadowMapId, Texture2D.blackTexture);
            commandBuffer.SetGlobalVector(ShadowTexelSizeId, Vector4.zero);
            commandBuffer.SetGlobalDepthBias(0.0f, 0.0f);
            commandBuffer.DisableShaderKeyword(CasterKeyword);
            commandBuffer.DisableScissorRect();
            context.ExecuteCommandBuffer(commandBuffer);
            commandBuffer.Release();
        }

        private static string HierarchyPath(Transform root, Transform value)
        {
            string result = value != null ? value.name : string.Empty;
            Transform current = value != null ? value.parent : null;
            while (current != null && current != root)
            {
                result = current.name + "/" + result;
                current = current.parent;
            }
            return root.name + "/" + result;
        }

        private static bool IsFinite(Matrix4x4 matrix)
        {
            for (int index = 0; index < 16; index++)
            {
                if (float.IsNaN(matrix[index]) || float.IsInfinity(matrix[index]))
                    return false;
            }
            return true;
        }

        private void ReleaseAtlas()
        {
            publicationReady = false;
            if (atlas == null)
                return;
            if (atlas.IsCreated())
                atlas.Release();
            DestroyObject(atlas);
            atlas = null;
            atlasTileResolution = 0;
            atlasWidth = 0;
            atlasHeight = 0;
        }

        private static void DestroyObject(UnityEngine.Object value)
        {
            if (value == null)
                return;
            if (Application.isPlaying)
                UnityEngine.Object.Destroy(value);
            else
                UnityEngine.Object.DestroyImmediate(value);
        }

        public void Dispose()
        {
            if (disposed)
                return;
            disposed = true;
            ReleaseAtlas();
            foreach (Material material in cullOffCasterMaterials.Values)
                DestroyObject(material);
            cullOffCasterMaterials.Clear();
            DestroyObject(clearMaterial);
            clearMaterial = null;
        }
    }
}
