using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Last-camera diagnostic observation for the source-closed sceneMV and
    /// AfterDOF descriptor relationships. The selected retail color/depth
    /// formats, MSAA and extent remain deliberately outside this snapshot.
    /// </summary>
    public sealed class EndfieldRecoveredSceneMVDiagnosticState
    {
        public bool requested { get; internal set; }
        public string requestFailure { get; internal set; }
        public bool descriptorCreated { get; internal set; }
        public int sceneMVWidth { get; internal set; }
        public int sceneMVHeight { get; internal set; }
        public int sceneMVSlices { get; internal set; }
        public GraphicsFormat sceneMVGraphicsFormat { get; internal set; }
        public TextureDimension sceneMVDimension { get; internal set; }
        public FilterMode sceneMVFilterMode { get; internal set; }
        public TextureWrapMode sceneMVWrapMode { get; internal set; }
        public int sceneMVMSAASamples { get; internal set; }
        public bool sceneMVBindMS { get; internal set; }
        public bool sceneMVNeutralInitialization { get; internal set; }
        public bool afterPostSceneMVLoadStoreNoClear { get; internal set; }
        public bool afterPostTarget0DescriptorClone { get; internal set; }
        public GraphicsFormat afterPostTarget0GraphicsFormat { get; internal set; }
        public bool glow902Queue3005Requested { get; internal set; }
        public bool glow902Queue3005Executed { get; internal set; }
    }

    /// <summary>
    /// Immutable, non-owning contract for the dedicated character-shadow
    /// atlas produced earlier in the same camera frame.
    /// </summary>
    internal readonly struct EndfieldRecoveredCharacterShadowFrame
    {
        internal readonly bool ready;
        internal readonly bool temporaryRtAllocated;
        internal readonly string failure;
        internal readonly int cameraInstanceId;
        internal readonly Transform actorRoot;
        internal readonly int actorRootInstanceId;
        internal readonly string actorRootPath;
        internal readonly int atlasIdentifier;
        internal readonly int resolution;
        internal readonly int depthBits;
        internal readonly Matrix4x4 worldToShadow;
        internal readonly Vector4 receiverBias;
        internal readonly Vector3 virtualLightDirection;
        internal readonly Vector4 liveForwardParams;
        internal readonly float observedDirectionalShadowStrength;
        internal readonly string strengthSourceExpression;

        internal EndfieldRecoveredCharacterShadowFrame(
            bool ready,
            bool temporaryRtAllocated,
            string failure,
            int cameraInstanceId,
            Transform actorRoot,
            string actorRootPath,
            int atlasIdentifier,
            int resolution,
            int depthBits,
            Matrix4x4 worldToShadow,
            Vector4 receiverBias,
            Vector3 virtualLightDirection,
            Vector4 liveForwardParams,
            float observedDirectionalShadowStrength,
            string strengthSourceExpression)
        {
            this.ready = ready;
            this.temporaryRtAllocated = temporaryRtAllocated;
            this.failure = failure ?? string.Empty;
            this.cameraInstanceId = cameraInstanceId;
            this.actorRoot = actorRoot;
            actorRootInstanceId = actorRoot != null
                ? actorRoot.GetInstanceID()
                : 0;
            this.actorRootPath = actorRootPath ?? string.Empty;
            this.atlasIdentifier = atlasIdentifier;
            this.resolution = resolution;
            this.depthBits = depthBits;
            this.worldToShadow = worldToShadow;
            this.receiverBias = receiverBias;
            this.virtualLightDirection = virtualLightDirection;
            this.liveForwardParams = liveForwardParams;
            this.observedDirectionalShadowStrength =
                observedDirectionalShadowStrength;
            this.strengthSourceExpression =
                strengthSourceExpression ?? string.Empty;
        }

        internal static EndfieldRecoveredCharacterShadowFrame Unavailable(
            string failure)
        {
            return new EndfieldRecoveredCharacterShadowFrame(
                false,
                false,
                failure,
                0,
                null,
                string.Empty,
                0,
                0,
                0,
                Matrix4x4.identity,
                Vector4.zero,
                Vector3.zero,
                Vector4.zero,
                0.0f,
                "directionalLight.shadowStrength (observed only; not applied by screen producer G)");
        }
    }

    // The recovered HGRP shaders are tagged with RenderPipeline=HDRenderPipeline.
    // Unity's SubShader selection checks that name before SRP draw code runs, so
    // this lightweight compatibility pipeline intentionally uses the same class
    // name while keeping only the minimal draw loop needed for inspection.
    public class HDRenderPipeline : RenderPipeline
    {
        private static HDRenderPipeline activeInstance;

        private static readonly int CharacterShadowMapId = Shader.PropertyToID("_EndfieldCharacterShadowMap");
        private static readonly int CharacterShadowRawDepthMapId =
            Shader.PropertyToID("_EndfieldCharacterShadowRawDepthMap");
        private static readonly int CharacterWorldToShadowId = Shader.PropertyToID("_EndfieldCharacterWorldToShadow");
        private static readonly int CharacterShadowParamsId = Shader.PropertyToID("_EndfieldCharacterShadowParams");
        private static readonly int CharacterShadowBiasId = Shader.PropertyToID("_EndfieldCharacterShadowBias");
        private static readonly int CharacterShadowLightDirectionId =
            Shader.PropertyToID("_EndfieldCharacterShadowLightDirection");
        private static readonly int CharacterWorldToShadowArrayId =
            Shader.PropertyToID("_EndfieldCharacterWorldToShadowArray");
        private static readonly int CharacterShadowBiasArrayId =
            Shader.PropertyToID("_EndfieldCharacterShadowBiasArray");
        private static readonly int CharacterShadowLightDirectionArrayId =
            Shader.PropertyToID("_EndfieldCharacterShadowLightDirectionArray");
        private static readonly int CharacterShadowAtlasRectArrayId =
            Shader.PropertyToID("_EndfieldCharacterShadowAtlasRectArray");
        private static readonly int CharacterShadowMultiAtlasParamsId =
            Shader.PropertyToID("_EndfieldCharacterShadowMultiAtlasParams");
        private static readonly int CharacterShadowAtlasTexelSizeId =
            Shader.PropertyToID("_EndfieldCharacterShadowAtlasTexelSize");
        private static readonly int CharacterShadowPassVpId =
            Shader.PropertyToID("_EndfieldCharacterShadowPassVP");
        private static readonly int WorldSpaceLightPositionId = Shader.PropertyToID("_WorldSpaceLightPos0");
        private static readonly int UnityLightShadowBiasId = Shader.PropertyToID("unity_LightShadowBias");
        private static readonly int OverlayCameraRelativeOriginId =
            Shader.PropertyToID("_EndfieldRecoveredOverlayCameraRelativeOrigin");
        private static readonly int OverlayTaaJitterStrengthId =
            Shader.PropertyToID("_EndfieldRecoveredOverlayTaaJitterStrength");
        private static readonly int OverlayEnvironmentParamsId =
            Shader.PropertyToID("_EndfieldRecoveredOverlayEnvironmentParams");
        private static readonly int GlobalMipBiasId =
            Shader.PropertyToID("_GlobalMipBias");
        private static readonly int GlobalMipBiasPow2Id =
            Shader.PropertyToID("_GlobalMipBiasPow2");
        private static readonly int CameraColorId = Shader.PropertyToID("_EndfieldHGCameraColor");
        private static readonly int SceneColorTextureId = Shader.PropertyToID("_SceneColorTexture");
        private static readonly int RecoveredRefractionSceneColorId =
            Shader.PropertyToID("_EndfieldRecoveredRefractionSceneColor");
        private static readonly int SceneDepthId = Shader.PropertyToID("_SceneDepth");
        private static readonly int SceneDepthTexelSizeId = Shader.PropertyToID("_SceneDepth_TexelSize");
        private static readonly int CameraDepthTextureId =
            Shader.PropertyToID("_CameraDepthTexture");
        private static readonly int CameraDepthTextureTexelSizeId =
            Shader.PropertyToID("_CameraDepthTexture_TexelSize");
        private static readonly int RecoveredVFXSoftDepthReadyId =
            Shader.PropertyToID("_EndfieldRecoveredVFXSoftDepthReady");
        private static readonly int RecoveredPostUberWorldUiReadyId =
            Shader.PropertyToID("_EndfieldRecoveredPostUberWorldUiReady");
        private static readonly int RecoveredPostUberPortraitDepthId =
            Shader.PropertyToID("_EndfieldRecoveredPostUberPortraitDepth");
        private static readonly int NonJitteredViewNoTransProjMatrixId =
            Shader.PropertyToID("_NonJitteredViewNoTransProjMatrix");
        private static readonly int WorldSpaceCameraPosInternalId =
            Shader.PropertyToID("_WorldSpaceCameraPos_Internal");
        private static readonly int RenderPathInjectedId =
            Shader.PropertyToID("_RenderPathInjected");
        private static readonly int HGFlipXId = Shader.PropertyToID("_HGFlipX");
        private static readonly int HGFlipYId = Shader.PropertyToID("_HGFlipY");
        private static readonly int RecoveredCameraDepthTextureId =
            Shader.PropertyToID("_EndfieldRecoveredCameraDepthTexture");
        private static readonly int RecoveredCameraDepthTextureTexelSizeId =
            Shader.PropertyToID("_EndfieldRecoveredCameraDepthTexture_TexelSize");
        private static readonly int RecoveredCameraDepthReadyId =
            Shader.PropertyToID("_EndfieldRecoveredCameraDepthReady");
        private static readonly int CharacterBloomSourceId = Shader.PropertyToID("_EndfieldCharacterBloomSource");
        private static readonly int RecoveredEndminfPostSourceId =
            Shader.PropertyToID("_EndfieldRecoveredEndminfPostSource");
        private static readonly int RecoveredEndminfOpeningStripSourceId =
            Shader.PropertyToID("_EndfieldRecoveredEndminfOpeningStripSource");
        private static readonly int RecoveredEndminfOpeningStripSceneMVId =
            Shader.PropertyToID("_EndfieldRecoveredEndminfOpeningStripSceneMV");
        private static readonly int CharacterBloomAId = Shader.PropertyToID("_EndfieldCharacterBloomA");
        private static readonly int CharacterBloomBId = Shader.PropertyToID("_EndfieldCharacterBloomB");
        private static readonly int BloomTextureId = Shader.PropertyToID("_BloomTex");
        private static readonly int BloomIntensityId = Shader.PropertyToID("_BloomIntensity");
        private static readonly int BloomThresholdId = Shader.PropertyToID("_BloomThreshold");
        private static readonly int BloomSoftnessId = Shader.PropertyToID("_BloomSoftness");
        // Presentation flip for the backbuffer. CommandBuffer.Blit inverts Y when
        // the destination is the screen on UV-starts-at-top devices but not when
        // it is a RenderTexture, so the offscreen capture path this lab was built
        // around is upright while Play mode is upside down. The offscreen path
        // always assigns camera.targetTexture, so the condition below is false
        // there and the validated capture output is unchanged.
        private static readonly int PresentFlipYId =
            Shader.PropertyToID("_EndfieldPresentFlipY");

        private static bool ShouldFlipPresentation(Camera camera)
        {
            return camera != null &&
                   camera.targetTexture == null &&
                   SystemInfo.graphicsUVStartsAtTop;
        }

        /// <summary>
        /// Presents an already-composed colour target to the camera target,
        /// compensating for the backbuffer Y inversion when there is one.
        /// </summary>
        private static void PresentToCameraTarget(
            CommandBuffer commandBuffer,
            RenderTargetIdentifier source,
            Camera camera)
        {
            var destination =
                new RenderTargetIdentifier(BuiltinRenderTextureType.CameraTarget);
            if (ShouldFlipPresentation(camera))
            {
                commandBuffer.Blit(
                    source,
                    destination,
                    new Vector2(1.0f, -1.0f),
                    new Vector2(0.0f, 1.0f));
                return;
            }

            commandBuffer.Blit(source, destination);
        }

        private static readonly int BloomDirectionId = Shader.PropertyToID("_BloomDirection");
        private static readonly int BloomTexelSizeId = Shader.PropertyToID("_BloomTexelSize");
        private static readonly int BloomLowMipTextureId = Shader.PropertyToID("_SourceTexLowMip");
        private static readonly int BloomBicubicParamsId = Shader.PropertyToID("_BloomBicubicParams");
        private static readonly int BloomScatterId = Shader.PropertyToID("_BloomScatter");
        private static readonly int RecoveredTemporalHistoryId =
            Shader.PropertyToID("_RecoveredTemporalHistory");
        private static readonly int RecoveredTemporalCurrentId =
            Shader.PropertyToID("_RecoveredTemporalCurrent");
        private static readonly int RecoveredTemporalCurrentLoadId =
            Shader.PropertyToID("_RecoveredTemporalCurrentLoad");
        private static readonly int RecoveredTemporalSceneMVId =
            Shader.PropertyToID("_RecoveredTemporalSceneMV");
        private static readonly int RecoveredTemporalSceneDepthId =
            Shader.PropertyToID("_RecoveredTemporalSceneDepth");
        private static readonly int RecoveredTemporalRawSceneMVId =
            Shader.PropertyToID("_RecoveredTemporalRawSceneMV");
        private static readonly int RecoveredTemporalRenderSizeId =
            Shader.PropertyToID("_RecoveredTemporalRenderSize");
        private static readonly int RecoveredTemporalReprojectionMatrixId =
            Shader.PropertyToID("_RecoveredTemporalReprojectionMatrix");
        private static readonly int RecoveredTemporalAuxiliaryHistoryValidId =
            Shader.PropertyToID("_RecoveredTemporalAuxiliaryHistoryValid");
        private static readonly int RecoveredTemporalOcclusionDepthDiffId =
            Shader.PropertyToID("_RecoveredTemporalOcclusionDepthDiff");
        private static readonly int RecoveredTemporalPreviousDilatedDepthId =
            Shader.PropertyToID("_RecoveredTemporalPreviousDilatedDepth");
        private static readonly int RecoveredTemporalPreviousDilatedSceneMVId =
            Shader.PropertyToID("_RecoveredTemporalPreviousDilatedSceneMV");
        private static readonly int RecoveredTemporalDilatedDepthId =
            Shader.PropertyToID("_EndfieldRecoveredTemporalDilatedDepth");
        private static readonly int RecoveredTemporalDilatedSceneMVId =
            Shader.PropertyToID("_EndfieldRecoveredTemporalDilatedSceneMV");
        private static readonly int RecoveredTemporalSelectedSceneMVId =
            Shader.PropertyToID("_EndfieldRecoveredTemporalSelectedSceneMV");
        private static readonly int RecoveredTemporalPackedSceneMVId =
            Shader.PropertyToID("_RecoveredTemporalPackedSceneMV");
        private static readonly int RecoveredTemporalDilatedMaskId =
            Shader.PropertyToID("_EndfieldRecoveredTemporalDilatedMask");
        private static readonly int RecoveredTemporalHistoryWeightId =
            Shader.PropertyToID("_RecoveredTemporalHistoryWeight");
        private static readonly int RecoveredTemporalStaticHistoryWeightId =
            Shader.PropertyToID("_RecoveredTemporalStaticHistoryWeight");
        private static readonly int RecoveredTemporalPackedResolveId =
            Shader.PropertyToID("_RecoveredTemporalPackedResolve");
        private static readonly int RecoveredTemporalJitterId =
            Shader.PropertyToID("_RecoveredTemporalJitter");
        private static readonly int RecoveredTemporalFrameInfoYId =
            Shader.PropertyToID("_RecoveredTemporalFrameInfoY");
        private static readonly int RecoveredTemporalFastConvergeId =
            Shader.PropertyToID("_RecoveredTemporalFastConverge");
        private static readonly int RecoveredTemporalResponsiveTransparencyId =
            Shader.PropertyToID("_RecoveredTemporalResponsiveTransparency");
        private static readonly int RecoveredTemporalResolveId =
            Shader.PropertyToID("_EndfieldRecoveredTemporalResolve");
        private static readonly int RecoveredTemporalPresentationId =
            Shader.PropertyToID("_EndfieldRecoveredTemporalPresentation");
        private static readonly int RecoveredPostSemanticsId = Shader.PropertyToID("_EndfieldRecoveredPostSemantics");
        private static readonly int RecoveredColorGradingLutId = Shader.PropertyToID("_RecoveredColorGradingLut");
        private static readonly int RecoveredColorGradingLutReadyId = Shader.PropertyToID("_RecoveredColorGradingLutReady");
        private static readonly int RecoveredLinearUnormFinalTargetId =
            Shader.PropertyToID("_EndfieldRecoveredLinearUnormFinalTarget");
        private static readonly int RecoveredFinalTargetSizeId =
            Shader.PropertyToID("_EndfieldRecoveredFinalTargetSize");
        private static readonly int RecoveredFinalDisplayId =
            Shader.PropertyToID("_EndfieldRecoveredFinalDisplay");
        private static readonly int ExposureParamsId = Shader.PropertyToID("_ExposureParams");
        private static readonly int AutoExposureSourceId =
            Shader.PropertyToID("_HGAutoExposureSource");
        private static readonly int AutoExposureHistogramBufferId =
            Shader.PropertyToID("_HGAutoExposureHistogramBuffer");
        private static readonly int AutoExposureTextureWidthId =
            Shader.PropertyToID("_HGAutoExposureTextureWidth");
        private static readonly int AutoExposureTextureHeightId =
            Shader.PropertyToID("_HGAutoExposureTextureHeight");
        private static readonly int AutoExposureThreadGroupsXId =
            Shader.PropertyToID("_HGAutoExposureThreadGroupsX");
        private static readonly int AutoExposureThreadGroupsYId =
            Shader.PropertyToID("_HGAutoExposureThreadGroupsY");
        private static readonly int AutoExposureSampleStrideId =
            Shader.PropertyToID("_HGAutoExposureSampleStride");
        private static readonly int AutoExposureMinEVId =
            Shader.PropertyToID("_HGAutoExposureMinEV");
        private static readonly int AutoExposureMaxEVId =
            Shader.PropertyToID("_HGAutoExposureMaxEV");
        private static readonly int AutoExposureCenterPixelWeightId =
            Shader.PropertyToID("_HGAutoExposureCenterPixelWeight");
        private static readonly int PostExposureId = Shader.PropertyToID("_PostExposure");
        private static readonly int EndminfVisualCompatibilityParamsId =
            Shader.PropertyToID("_EndminfVisualCompatibilityParams");
        private static readonly int EndminfVisualCompatibilityCenterId =
            Shader.PropertyToID("_EndminfVisualCompatibilityCenter");
        private static readonly int EndminfOpeningStripParamsId =
            Shader.PropertyToID("_EndminfOpeningStripParams");
        private static readonly int EndminfOpeningStripSourceSizeId =
            Shader.PropertyToID("_EndminfOpeningStripSourceSize");
        private static readonly int EndminfOpeningStripSelectorId =
            Shader.PropertyToID("_EndminfOpeningStripSelector");
        private static readonly int TonemapModeId = Shader.PropertyToID("_TonemapMode");
        private static readonly int ToneCurveParams0Id = Shader.PropertyToID("_ToneCurveParams0");
        private static readonly int ToneCurveParams1Id = Shader.PropertyToID("_ToneCurveParams1");
        private static readonly int VignetteParamsId = Shader.PropertyToID("_VignetteParams");

        private const int MaxRecoveredBloomMipCount = 16;
        private const float RecoveredBloomHeightCap = 1080.0f;
        private const float RecoveredBloomSerializedThreshold = 0.75f;
        private const float RecoveredBloomSerializedIntensity = 0.45f;
        private const float RecoveredBloomSerializedScatter = 0.8f;
        // Public-Unity HLSL receives a different pre-Uber temporal source than
        // retail's Streamline output. A matched peak sweep against clean frame
        // 269 selects one quarter of the source intensity for this fallback;
        // the native exact path below still receives the unscaled retail state.
        private const float EndminfCompatibilityUberIntensityScale = 0.25f;
        private const float RecoveredGachaBloomSerializedThreshold = 0.95f;
        private const float RecoveredGachaBloomSerializedIntensity = 0.5f;
        private const float RecoveredGachaBloomSerializedScatter = 0.4f;
        private static readonly Color RecoveredGachaSceneColorClear =
            new Color(0.025f, 0.07f, 0.19f, 0.0f);
        private const int RecoveredCharacterShadowTileResolution = 1024;
        private const int RecoveredCharacterShadowMaxAssignableSlots = 14;
        private const int RecoveredCharacterShadowShaderArrayLength = 15;
        private const float RecoveredCharacterShadowPcf3x3BiasScale = 1.5f;
        private const float RecoveredCharacterShadowShaderDepthBiasScale = 2.0f;
        private const float RecoveredCharacterShadowShaderNormalBiasScale = 4.0f;
        private const float RecoveredCharacterShadowHardwareDepthBias = 8.0f;
        // The current installed physical Gacha camera has source-closed
        // HGAdditionalCameraData.enableAlpha=false. GetColorBufferFormat
        // therefore selects pipeline format 74, B10G11R11, rather than the
        // alpha-capable RGBA16F override. Other cameras remain outside that
        // selected-route conclusion. AfterDOF must clone whichever current
        // sceneColor descriptor the diagnostic owns.
        public const GraphicsFormat RecoveredSceneColorFormat =
            GraphicsFormat.B10G11R11_UFloatPack32;
        public static GraphicsFormat LastRecoveredEndminfPostSourceGraphicsFormat
            { get; private set; } = GraphicsFormat.None;
        public static GraphicsFormat LastRecoveredEndminfBloomGraphicsFormat
            { get; private set; } = GraphicsFormat.None;
        public static int LastRecoveredEndminfBloomWidth
            { get; private set; }
        public static int LastRecoveredEndminfBloomHeight
            { get; private set; }
        public static bool LastRecoveredEndminfExactUberRequested
            { get; private set; }
        public static bool LastRecoveredEndminfExactUberSubmitted
            { get; private set; }
        public static bool LastRecoveredEndminfExactUberValidated
            { get; private set; }
        public static string LastRecoveredEndminfExactUberVariant
            { get; private set; } = string.Empty;
        public static string LastRecoveredEndminfExactUberFailure
            { get; private set; } = string.Empty;
        public static bool LastRecoveredEndminfOpeningStripCompatibilityApplied
            { get; private set; }
        public static bool LastRecoveredEndminfOpeningStripSceneMVApplied
            { get; private set; }
        public static bool LastRecoveredUnityPublicNgxProxyRequested
            { get; private set; }
        public static bool LastRecoveredUnityPublicNgxProxySubmitted
            { get; private set; }
        public static bool LastRecoveredUnityPublicNgxProxyValidated
            { get; private set; }
        public static string LastRecoveredUnityPublicNgxProxyFailure
            { get; private set; } = string.Empty;
        public static Vector2 LastRecoveredUnityPublicNgxProxyJitterOffset
            { get; private set; }
        public static int LastRecoveredUnityPublicNgxProxyJitterPhase
            { get; private set; } = -1;
        public static int LastRecoveredUnityPublicNgxProxyIndicatorInvertAxisX
            { get; private set; } = -1;
        public static int LastRecoveredUnityPublicNgxProxyIndicatorInvertAxisY
            { get; private set; } = -1;
        public static EndfieldRecoveredSceneMVDiagnosticState
            LastRecoveredSceneMVDiagnostic { get; } =
                new EndfieldRecoveredSceneMVDiagnosticState();

        internal static void ResetRecoveredSceneMVDiagnostic(bool requested)
        {
            EndfieldRecoveredSceneMVDiagnosticState state =
                LastRecoveredSceneMVDiagnostic;
            state.requested = requested;
            state.requestFailure = string.Empty;
            state.descriptorCreated = false;
            state.sceneMVWidth = 0;
            state.sceneMVHeight = 0;
            state.sceneMVSlices = 0;
            state.sceneMVGraphicsFormat = GraphicsFormat.None;
            state.sceneMVDimension = TextureDimension.Unknown;
            state.sceneMVFilterMode = FilterMode.Point;
            state.sceneMVWrapMode = TextureWrapMode.Repeat;
            state.sceneMVMSAASamples = 0;
            state.sceneMVBindMS = false;
            state.sceneMVNeutralInitialization = false;
            state.afterPostSceneMVLoadStoreNoClear = false;
            state.afterPostTarget0DescriptorClone = false;
            state.afterPostTarget0GraphicsFormat = GraphicsFormat.None;
            state.glow902Queue3005Requested = false;
            state.glow902Queue3005Executed = false;
        }

        internal static void ReportRecoveredSceneMVDescriptor(
            RenderTexture sceneMV)
        {
            EndfieldRecoveredSceneMVDiagnosticState state =
                LastRecoveredSceneMVDiagnostic;
            RenderTextureDescriptor descriptor = sceneMV.descriptor;
            state.descriptorCreated = true;
            state.sceneMVWidth = descriptor.width;
            state.sceneMVHeight = descriptor.height;
            state.sceneMVSlices = descriptor.volumeDepth;
            state.sceneMVGraphicsFormat = descriptor.graphicsFormat;
            state.sceneMVDimension = descriptor.dimension;
            state.sceneMVFilterMode = sceneMV.filterMode;
            state.sceneMVWrapMode = sceneMV.wrapMode;
            state.sceneMVMSAASamples = descriptor.msaaSamples;
            state.sceneMVBindMS = descriptor.bindMS;
        }

        internal static void ReportRecoveredGlow902Queue3005Lane()
        {
            LastRecoveredSceneMVDiagnostic.glow902Queue3005Executed = true;
        }

        internal static void ReportRecoveredSceneMVNeutralInitialization()
        {
            LastRecoveredSceneMVDiagnostic.sceneMVNeutralInitialization = true;
        }

        internal static void ReportRecoveredAfterPostDescriptors(
            GraphicsFormat target0GraphicsFormat,
            bool target0DescriptorClone)
        {
            EndfieldRecoveredSceneMVDiagnosticState state =
                LastRecoveredSceneMVDiagnostic;
            state.afterPostSceneMVLoadStoreNoClear = true;
            state.afterPostTarget0DescriptorClone = target0DescriptorClone;
            state.afterPostTarget0GraphicsFormat = target0GraphicsFormat;
        }

        private sealed class RecoveredCharacterShadowActor
        {
            internal string actorName;
            internal Transform actorRoot;
            internal Bounds bounds;
            internal int resolvedSphereCount;
            internal int missingSphereCount;
            internal int secondarySphereCount;
            internal Renderer[] proxyRenderers;
            internal int proxyEntryCount;
            internal Renderer[] realtimeCasterRenderers;
            internal int realtimeFalseExcludedCount;
            internal int slot;
        }

        // The original pipeline keeps scene directional CSM and the character
        // self-shadow atlas as separate inputs. CharInfo disables the former
        // while leaving the latter enabled. This selector probes that topology
        // without changing Light.shadows or the canonical pipeline asset.
        public const string SeparateCharacterShadowEnvironmentVariable =
            "ENDFIELD_RECOVERED_SEPARATE_CHARACTER_SHADOW";
        public const string SeparateCharacterShadowCommandLineArgument =
            "-endfield-recovered-separate-character-shadow";
        public const string MultiCharacterShadowAtlasEnvironmentVariable =
            "ENDFIELD_RECOVERED_MULTI_CHARACTER_SHADOW_ATLAS";
        public const string MultiCharacterShadowAtlasCommandLineArgument =
            "-endfield-recovered-multi-character-shadow-atlas";
        public const string
            OriginalRealtimeCharacterShadowCastersEnvironmentVariable =
                "ENDFIELD_RECOVERED_ORIGINAL_REALTIME_CHARACTER_SHADOW_CASTERS";
        public const string
            OriginalRealtimeCharacterShadowCastersCommandLineArgument =
                "-endfield-recovered-original-realtime-character-shadow-casters";

        // The shipped UberPost performs its IEC sRGB OETF and deterministic
        // RGB dither while writing a linear R8G8B8A8_UNorm target. Unity's
        // ordinary CameraTarget contract is not sufficiently constrained to
        // reproduce that safely. This selector is therefore accepted only for
        // an exact, non-sRGB R8G8B8A8_UNorm camera.targetTexture; the encoded
        // temporary is then presented with a same-format CopyTexture command.
        public const string LinearUnormFinalTargetEnvironmentVariable =
            "ENDFIELD_RECOVERED_LINEAR_UNORM_FINAL_TARGET";
        public const string LinearUnormFinalTargetCommandLineArgument =
            "-endfield-recovered-linear-unorm-final-target";

        // Compatibility name retained for the default-off HGRP Auto-mode
        // histogram diagnostic. The shipped CharInfo volume selects mode 1
        // (Manual), EV 0, so this selector is not original CharInfo behavior.
        // It requires the recovered post path so the same diagnostic multiplier
        // can pre-expose character output and be removed in Uber.
        public const string LiveCharInfoAutoExposureEnvironmentVariable =
            "ENDFIELD_RECOVERED_LIVE_CHARINFO_AUTO_EXPOSURE";
        public const string LiveCharInfoAutoExposureCommandLineArgument =
            "-endfield-recovered-live-charinfo-auto-exposure";
        // The ordinary Quality-0 shader math is closed, but the August capture
        // does not admit TAAU over DLSS/DLAA and does not expose live jitter,
        // frame-info, or convergence state. Keep packed-resource consumption
        // as an explicit comparison experiment until those gates close.
        public const string PackedTemporalResolveEnvironmentVariable =
            "ENDFIELD_RECOVERED_TAAU_PACKED_RESOLVE";
        private const string LiveCharInfoAutoExposureComputeResource =
            "EndfieldRecoveredCharInfoExposure";

        private static readonly int[] RecoveredBloomMipDownIds =
            CreateBloomMipIds("_EndfieldRecoveredBloomMipDown");
        private static readonly int[] RecoveredBloomMipUpIds =
            CreateBloomMipIds("_EndfieldRecoveredBloomMipUp");

        // Retail's deferred mesh pass is named "HGBuffer", but its renderer-list
        // LightMode is "GBuffer". Do not add that tag here until this pipeline
        // binds the exact SceneColor/SceneMV/GBufferA/B/C MRT set plus sceneDepth
        // and supplies the compatible deferred consumer and frame resources.
        private static readonly ShaderTagId[] OpaqueShaderPasses =
        {
            new ShaderTagId("ForwardLit"),
            new ShaderTagId("ForwardCharacterOnly"),
            new ShaderTagId("ForwardOnly"),
            new ShaderTagId("Forward"),
            new ShaderTagId("ForwardBase"),
            new ShaderTagId("SRPDefaultUnlit"),
            new ShaderTagId("UniversalForward")
        };

        // The installed DefaultDeferred path builds one transparent renderer
        // list with this source order (CharacterOutline is inserted before the
        // unlit fallback when enabled), then submits that SRP list together
        // with the ECS list. Keep the retail tags first. The trailing three
        // tags are lab-only compatibility names used by reconstructed shaders.
        private static readonly ShaderTagId[] TransparentShaderPasses =
        {
            new ShaderTagId("TransparentBackface"),
            new ShaderTagId("ForwardOnly"),
            new ShaderTagId("Forward"),
            new ShaderTagId("ForwardCharacterOnly"),
            new ShaderTagId("CharacterOutline"),
            new ShaderTagId("SRPDefaultUnlit"),
            new ShaderTagId("ForwardLit"),
            new ShaderTagId("ForwardBase"),
            new ShaderTagId("UniversalForward")
        };

        private readonly HGCompatRenderPipelineAsset asset;
        private readonly Material postProcessMaterial;
        private readonly EndfieldRecoveredCharInfoLut recoveredColorGradingLut;
        private readonly EndfieldRecoveredEndminfUberExactRuntime
            recoveredEndminfUberExactRuntime;
        private readonly EndfieldRecoveredEndminfM28PeakExactRuntime
            recoveredEndminfM28PeakExactRuntime;
        private readonly bool separateCharacterShadowDiagnosticEnabled;
        private readonly bool recoveredMultiCharacterShadowAtlasRequested;
        private readonly bool
            recoveredOriginalRealtimeCharacterShadowCastersRequested;
        private readonly bool recoveredLinearUnormFinalTargetRequested;
        private readonly bool recoveredLiveCharInfoAutoExposureRequested;
        private readonly ComputeShader recoveredLiveCharInfoAutoExposureCompute;
        private readonly int recoveredLiveCharInfoAutoExposureKernel = -1;
        private readonly EndfieldRecoveredLightBinning recoveredLightBinning;
        private readonly EndfieldRecoveredReflectionProbeFallback
            recoveredReflectionProbeFallback;
        private readonly EndfieldRecoveredVisibilitySHConstants
            recoveredVisibilitySHConstants;
        private readonly EndfieldRecoveredDeferredTransformVariables
            recoveredDeferredTransformVariables;
        private readonly EndfieldRecoveredShaderVariablesGlobal
            recoveredShaderVariablesGlobal;
        private readonly EndfieldRecoveredDeferredLightData
            recoveredDeferredLightData;
        private readonly EndfieldRecoveredDeferredShadowData
            recoveredDeferredShadowData;
        private readonly EndfieldRecoveredPunctualShadowProducer
            recoveredPunctualShadowProducer;
        private readonly EndfieldRecoveredPreGBufferDiagnostic
            recoveredPreGBufferDiagnostic;
        private readonly EndfieldRecoveredPreGBufferDepthOwner
            recoveredPreGBufferDepthOwner;
        private readonly EndfieldRecoveredVisibilitySHProducer
            recoveredVisibilitySHProducer;
        private readonly EndfieldRecoveredDeferredGBufferFrame
            recoveredDeferredGBufferFrame;
        private readonly EndfieldRecoveredDeferredResolverInputProbe
            recoveredDeferredResolverInputProbe;
        private readonly EndfieldRecoveredDeferredExactConsumer
            recoveredDeferredExactConsumer;
        private readonly EndfieldRecoveredEndminfM27DeferredPresentation
            recoveredEndminfM27DeferredPresentation;
        private readonly EndfieldRecoveredSphereOutsideDeferredPresentation
            recoveredSphereOutsideDeferredPresentation;
        private readonly EndfieldRecoveredDirectionalCSMProducer
            recoveredDirectionalCSMProducer;
        private readonly EndfieldRecoveredContactShadowProducer
            recoveredContactShadowProducer;
        private readonly EndfieldRecoveredLowResDirectionalShadowProducer
            recoveredLowResDirectionalShadowProducer;
        private readonly EndfieldRecoveredScreenShadowMaskDiagnostic
            recoveredScreenShadowMaskDiagnostic;
        private readonly EndfieldRecoveredScreenShadowMaskProducer
            recoveredScreenShadowMaskProducer;
        private readonly EndfieldRecoveredScreenDirectAudit
            recoveredScreenDirectAudit;
        private readonly EndfieldRecoveredSceneMVCompositor
            recoveredSceneMVCompositor;
        private readonly EndfieldRecoveredCombinedVelocityProducer
            recoveredCombinedVelocityProducer;
        private readonly EndfieldRecoveredUnityPublicNgxProxy
            recoveredUnityPublicNgxProxy;
        private RenderTexture recoveredExactCameraDepth;
        private sealed class RecoveredTemporalCameraState
        {
            internal RenderTexture history;
            internal RenderTexture historyDilatedDepth;
            internal RenderTexture historyDilatedSceneMV;
            internal bool auxiliaryHistoryValid;
            internal Matrix4x4 previousNonJitteredViewProjection;
            internal bool hasPreviousNonJitteredViewProjection;
            internal float lastElapsed = float.NaN;
            internal int lastFrame = -1;
        }
        private readonly System.Collections.Generic.Dictionary<
            Camera,
            RecoveredTemporalCameraState> recoveredTemporalStates =
                new System.Collections.Generic.Dictionary<
                    Camera,
                    RecoveredTemporalCameraState>();
        private readonly System.Collections.Generic.Dictionary<
            Camera,
            EndfieldRecoveredCharInfoAutoExposureCameraState>
            recoveredLiveCharInfoAutoExposureStates =
                new System.Collections.Generic.Dictionary<
                    Camera,
                    EndfieldRecoveredCharInfoAutoExposureCameraState>();
        private readonly int[] recoveredBloomMipWidths = new int[MaxRecoveredBloomMipCount];
        private readonly int[] recoveredBloomMipHeights = new int[MaxRecoveredBloomMipCount];
        private int loggedRecoveredBloomWidth = -1;
        private int loggedRecoveredBloomHeight = -1;
        private bool loggedSeparateCharacterShadowDiagnostic;
        private bool loggedSeparateCharacterShadowDiagnosticFailure;
        private bool loggedRecoveredMultiCharacterShadowAtlas;
        private bool loggedRecoveredMultiCharacterShadowAtlasFailure;
        private readonly System.Collections.Generic.List<
            RecoveredCharacterShadowActor>
            recoveredMultiCharacterShadowActors =
                new System.Collections.Generic.List<
                    RecoveredCharacterShadowActor>();
        private readonly System.Collections.Generic.Dictionary<Renderer, uint>
            recoveredMultiCharacterOriginalRenderingLayers =
                new System.Collections.Generic.Dictionary<Renderer, uint>();
        private bool loggedRecoveredLinearUnormFinalTarget;
        private bool loggedRecoveredLinearUnormFinalTargetFailure;
        private bool loggedRecoveredLiveCharInfoAutoExposure;
        private bool loggedRecoveredLiveCharInfoAutoExposureFailure;
        private bool loggedRecoveredLiveCharInfoAutoExposureDispatchFailure;
        private bool loggedRecoveredPostUberWorldUi;
        private bool loggedRecoveredPostUberWorldUiFailure;
        private bool loggedRecoveredPostUberPortraitDepthSync;
        private bool loggedRecoveredPostUberPortraitDepthSyncFailure;
        private bool loggedRecoveredPreGBufferDepthOwnerFailure;
        private bool loggedRecoveredSceneMV;
        private bool loggedRecoveredSceneMVFailure;
        private bool loggedRecoveredVFXGlobalsFailure;
        private bool loggedRecoveredSceneColorFormatFailure;
        private bool loggedRecoveredPreTransparentSceneColorFormatFailure;
        private bool loggedRecoveredReflectionFrameActivation;
        private bool loggedRecoveredReflectionFrameFailure;
        private bool loggedRecoveredDeferredTransformActivation;
        private bool loggedRecoveredDeferredTransformFailure;
        private bool loggedRecoveredShaderVariablesGlobalActivation;
        private bool loggedRecoveredShaderVariablesGlobalFailure;
        private bool loggedRecoveredDeferredLightDataActivation;
        private bool loggedRecoveredDeferredLightDataFailure;
        private bool loggedRecoveredDeferredEndminfLightDataResult;
        private bool loggedRecoveredDeferredShadowDataActivation;
        private bool loggedRecoveredDeferredShadowDataFailure;
        private Material recoveredTemporalMaterial;
        private Material recoveredTemporalDilationMaterial;
        private Material recoveredTemporalMaskDilationMaterial;
        private Material recoveredEndminfOpeningStripMaterial;
        private bool loggedRecoveredEndminfOpeningStrip;
        private bool loggedRecoveredTemporalResolve;

        private static int[] CreateBloomMipIds(string prefix)
        {
            int[] ids = new int[MaxRecoveredBloomMipCount];
            for (int i = 0; i < ids.Length; i++)
                ids[i] = Shader.PropertyToID(prefix + i);
            return ids;
        }

        public HDRenderPipeline(HGCompatRenderPipelineAsset asset)
        {
            activeInstance = this;
            this.asset = asset;
            separateCharacterShadowDiagnosticEnabled =
                IsSeparateCharacterShadowDiagnosticEnabled();
            recoveredMultiCharacterShadowAtlasRequested =
                IsRecoveredMultiCharacterShadowAtlasRequested();
            recoveredOriginalRealtimeCharacterShadowCastersRequested =
                IsRecoveredOriginalRealtimeCharacterShadowCastersRequested();
            recoveredLinearUnormFinalTargetRequested =
                IsRecoveredLinearUnormFinalTargetRequested();
            recoveredLiveCharInfoAutoExposureRequested =
                IsRecoveredLiveCharInfoAutoExposureRequested();
            recoveredLightBinning = new EndfieldRecoveredLightBinning();
            recoveredReflectionProbeFallback =
                new EndfieldRecoveredReflectionProbeFallback();
            recoveredVisibilitySHConstants =
                new EndfieldRecoveredVisibilitySHConstants();
            recoveredDeferredTransformVariables =
                new EndfieldRecoveredDeferredTransformVariables();
            recoveredShaderVariablesGlobal =
                new EndfieldRecoveredShaderVariablesGlobal();
            recoveredDeferredLightData =
                new EndfieldRecoveredDeferredLightData();
            recoveredDeferredShadowData =
                new EndfieldRecoveredDeferredShadowData();
            recoveredPunctualShadowProducer =
                new EndfieldRecoveredPunctualShadowProducer();
            recoveredScreenDirectAudit =
                new EndfieldRecoveredScreenDirectAudit();
            recoveredScreenShadowMaskDiagnostic =
                new EndfieldRecoveredScreenShadowMaskDiagnostic(
                    recoveredScreenDirectAudit.Requested);
            recoveredScreenShadowMaskProducer =
                new EndfieldRecoveredScreenShadowMaskProducer();
            recoveredVisibilitySHProducer =
                new EndfieldRecoveredVisibilitySHProducer();
            recoveredDeferredGBufferFrame =
                new EndfieldRecoveredDeferredGBufferFrame();
            recoveredDeferredResolverInputProbe =
                new EndfieldRecoveredDeferredResolverInputProbe();
            recoveredDeferredExactConsumer =
                new EndfieldRecoveredDeferredExactConsumer();
            recoveredEndminfM27DeferredPresentation =
                new EndfieldRecoveredEndminfM27DeferredPresentation();
            recoveredSphereOutsideDeferredPresentation =
                new EndfieldRecoveredSphereOutsideDeferredPresentation();
            recoveredContactShadowProducer =
                new EndfieldRecoveredContactShadowProducer();
            recoveredLowResDirectionalShadowProducer =
                new EndfieldRecoveredLowResDirectionalShadowProducer(
                    recoveredScreenShadowMaskProducer.Requested);
            recoveredDirectionalCSMProducer =
                new EndfieldRecoveredDirectionalCSMProducer(
                    recoveredLowResDirectionalShadowProducer.Requested);
            recoveredPreGBufferDiagnostic =
                new EndfieldRecoveredPreGBufferDiagnostic(
                    recoveredScreenShadowMaskDiagnostic.Requested ||
                    recoveredVisibilitySHProducer.Requested ||
                    recoveredLowResDirectionalShadowProducer.Requested ||
                    recoveredContactShadowProducer.Requested,
                    recoveredScreenDirectAudit.SameOwnerRequested,
                    recoveredContactShadowProducer.Requested);
            recoveredPreGBufferDepthOwner =
                new EndfieldRecoveredPreGBufferDepthOwner();
            recoveredSceneMVCompositor =
                new EndfieldRecoveredSceneMVCompositor();
            recoveredCombinedVelocityProducer =
                new EndfieldRecoveredCombinedVelocityProducer();
            recoveredUnityPublicNgxProxy =
                new EndfieldRecoveredUnityPublicNgxProxy(
                    recoveredCombinedVelocityProducer);
            recoveredEndminfUberExactRuntime =
                new EndfieldRecoveredEndminfUberExactRuntime();
            recoveredEndminfM28PeakExactRuntime =
                new EndfieldRecoveredEndminfM28PeakExactRuntime();
            GraphicsSettings.useScriptableRenderPipelineBatching = true;

            if (recoveredLiveCharInfoAutoExposureRequested)
            {
                recoveredLiveCharInfoAutoExposureCompute =
                    Resources.Load<ComputeShader>(LiveCharInfoAutoExposureComputeResource);
                if (recoveredLiveCharInfoAutoExposureCompute != null)
                {
                    try
                    {
                        recoveredLiveCharInfoAutoExposureKernel =
                            recoveredLiveCharInfoAutoExposureCompute.FindKernel(
                                "HGLuminanceHistogramCS");
                    }
                    catch (System.Exception exception)
                    {
                        Debug.LogWarning(
                            "Recovered HGRP Auto-mode histogram diagnostic could not resolve the " +
                            $"HGLuminanceHistogramCS kernel: {exception.Message}");
                    }
                }
            }

            Shader postShader = Shader.Find("Hidden/Endfield/HGRPCompat/ExposureTonemap");
            if (postShader != null && postShader.isSupported)
            {
                postProcessMaterial = new Material(postShader)
                {
                    hideFlags = HideFlags.HideAndDontSave,
                    name = "Endfield HGRP Character Post (Pipeline)"
                };
                recoveredColorGradingLut = new EndfieldRecoveredCharInfoLut();
            }
            Shader temporalShader = Shader.Find(
                "Hidden/Endfield/HGRPCompat/TemporalResolve");
            if (temporalShader != null && temporalShader.isSupported)
            {
                recoveredTemporalMaterial = new Material(temporalShader)
                {
                    hideFlags = HideFlags.HideAndDontSave,
                    name = "Endfield HGRP TAAU History Resolve (Pipeline)"
                };
            }
            Shader temporalDilationShader = Shader.Find(
                "Hidden/Endfield/HGRPCompat/TemporalSceneMVDilation");
            if (temporalDilationShader != null && temporalDilationShader.isSupported)
            {
                recoveredTemporalDilationMaterial = new Material(temporalDilationShader)
                {
                    hideFlags = HideFlags.HideAndDontSave,
                    name = "Endfield HGRP TAAU SceneMV Dilation (Pipeline)"
                };
            }
            Shader temporalMaskDilationShader = Shader.Find(
                "Hidden/Endfield/HGRPCompat/TemporalMaskDilation");
            if (temporalMaskDilationShader != null &&
                temporalMaskDilationShader.isSupported)
            {
                recoveredTemporalMaskDilationMaterial = new Material(
                    temporalMaskDilationShader)
                {
                    hideFlags = HideFlags.HideAndDontSave,
                    name = "Endfield HGRP TAAU Mask Dilation (Pipeline)"
                };
            }
            Shader openingStripShader = Shader.Find(
                "Hidden/Endfield/HGRPCompat/EndminfOpeningStrip");
            if (openingStripShader != null && openingStripShader.isSupported)
            {
                recoveredEndminfOpeningStripMaterial = new Material(
                    openingStripShader)
                {
                    hideFlags = HideFlags.HideAndDontSave,
                    name = "Recovered Endminf Opening Strip (Pipeline)"
                };
            }
        }

        protected override void Dispose(bool disposing)
        {
            base.Dispose(disposing);
            if (ReferenceEquals(activeInstance, this))
                activeInstance = null;
            RestoreRecoveredMultiCharacterShadowTransport();
            foreach (EndfieldRecoveredCharInfoAutoExposureCameraState state in
                     recoveredLiveCharInfoAutoExposureStates.Values)
            {
                state.Dispose();
            }
            recoveredLiveCharInfoAutoExposureStates.Clear();
            recoveredScreenShadowMaskDiagnostic?.Dispose();
            recoveredScreenShadowMaskProducer?.Dispose();
            recoveredLowResDirectionalShadowProducer?.Dispose();
            recoveredContactShadowProducer?.Dispose();
            recoveredDirectionalCSMProducer?.Dispose();
            recoveredScreenDirectAudit?.Dispose();
            recoveredPreGBufferDepthOwner?.Dispose();
            recoveredPreGBufferDiagnostic?.Dispose();
            recoveredDeferredGBufferFrame?.Dispose();
            recoveredDeferredResolverInputProbe?.Dispose();
            recoveredDeferredExactConsumer?.Dispose();
            recoveredEndminfM27DeferredPresentation?.Dispose();
            recoveredSphereOutsideDeferredPresentation?.Dispose();
            recoveredVisibilitySHProducer?.Dispose();
            recoveredPunctualShadowProducer?.Dispose();
            recoveredDeferredShadowData?.Dispose();
            recoveredDeferredLightData?.Dispose();
            recoveredShaderVariablesGlobal?.Dispose();
            recoveredDeferredTransformVariables?.Dispose();
            recoveredVisibilitySHConstants?.Dispose();
            recoveredReflectionProbeFallback?.Dispose();
            recoveredLightBinning?.Dispose();
            recoveredColorGradingLut?.Dispose();
            recoveredEndminfUberExactRuntime?.Dispose();
            recoveredEndminfM28PeakExactRuntime?.Dispose();
            recoveredSceneMVCompositor?.Dispose();
            recoveredUnityPublicNgxProxy?.Dispose();
            ReleaseRecoveredPrimarySceneDepth(recoveredExactCameraDepth);
            recoveredExactCameraDepth = null;
            foreach (RecoveredTemporalCameraState state in recoveredTemporalStates.Values)
                ReleaseRecoveredTemporalHistory(state);
            recoveredTemporalStates.Clear();
            if (recoveredTemporalMaterial != null)
            {
                if (Application.isPlaying)
                    Object.Destroy(recoveredTemporalMaterial);
                else
                    Object.DestroyImmediate(recoveredTemporalMaterial);
                recoveredTemporalMaterial = null;
            }
            if (recoveredTemporalDilationMaterial != null)
            {
                if (Application.isPlaying)
                    Object.Destroy(recoveredTemporalDilationMaterial);
                else
                    Object.DestroyImmediate(recoveredTemporalDilationMaterial);
                recoveredTemporalDilationMaterial = null;
            }
            if (recoveredTemporalMaskDilationMaterial != null)
            {
                if (Application.isPlaying)
                    Object.Destroy(recoveredTemporalMaskDilationMaterial);
                else
                    Object.DestroyImmediate(recoveredTemporalMaskDilationMaterial);
                recoveredTemporalMaskDilationMaterial = null;
            }
            if (recoveredEndminfOpeningStripMaterial != null)
            {
                if (Application.isPlaying)
                    Object.Destroy(recoveredEndminfOpeningStripMaterial);
                else
                    Object.DestroyImmediate(recoveredEndminfOpeningStripMaterial);
                recoveredEndminfOpeningStripMaterial = null;
            }
            if (postProcessMaterial == null)
                return;

            if (Application.isPlaying)
                Object.Destroy(postProcessMaterial);
            else
                Object.DestroyImmediate(postProcessMaterial);
        }

        /// <summary>
        /// Read-only standalone diagnostic access to the source-backed live exposure
        /// state. Rendering behavior does not depend on this method.
        /// </summary>
        public static bool TryGetRecoveredLiveCharInfoAutoExposureState(
            Camera camera,
            out float currentExposure,
            out float targetExposure,
            out float averageEV,
            out int readbackLatencyFrames)
        {
            currentExposure = EndfieldRecoveredCharInfoAutoExposure.NeutralExposure;
            targetExposure = EndfieldRecoveredCharInfoAutoExposure.NeutralExposure;
            averageEV = float.NaN;
            readbackLatencyFrames = -1;

            HDRenderPipeline pipeline = activeInstance;
            if (pipeline == null || camera == null)
                return false;

            EndfieldRecoveredCharInfoAutoExposureCameraState state;
            if (!pipeline.recoveredLiveCharInfoAutoExposureStates.TryGetValue(
                    camera,
                    out state) ||
                state == null)
            {
                return false;
            }

            currentExposure = state.CurrentExposure;
            targetExposure = state.TargetExposure;
            averageEV = state.LastAverageEV;
            readbackLatencyFrames = state.LastReadbackLatencyFrames;
            return true;
        }

        /// <summary>
        /// Validates the exact public-NGX execution submitted by the most
        /// recent synchronized diagnostic render. This does not enable the
        /// proxy or make it canonical; it only closes capture telemetry over
        /// the output that was actually read back.
        /// </summary>
        public static bool ValidateRecoveredUnityPublicNgxProxyAfterSynchronizedRender(
            out string failure)
        {
            failure = string.Empty;
            HDRenderPipeline pipeline = activeInstance;
            if (pipeline == null || pipeline.recoveredUnityPublicNgxProxy == null)
            {
                failure = "active recovered render pipeline is unavailable";
                LastRecoveredUnityPublicNgxProxyValidated = false;
                LastRecoveredUnityPublicNgxProxyFailure = failure;
                return false;
            }
            bool valid = pipeline.recoveredUnityPublicNgxProxy
                .ValidatePendingAfterSynchronizedRender(out failure);
            LastRecoveredUnityPublicNgxProxyValidated = valid;
            LastRecoveredUnityPublicNgxProxyFailure = valid
                ? string.Empty
                : failure;
            return valid;
        }

        /// <summary>
        /// Validates the exact Endminf Uber plugin event after the capture's
        /// ReadPixels synchronization point. Submission alone is not evidence
        /// that the retained native draw executed successfully.
        /// </summary>
        public static bool ValidateRecoveredEndminfExactUberAfterSynchronizedRender(
            out string failure)
        {
            failure = string.Empty;
            HDRenderPipeline pipeline = activeInstance;
            if (pipeline == null ||
                pipeline.recoveredEndminfUberExactRuntime == null)
            {
                failure = "active recovered render pipeline is unavailable";
                LastRecoveredEndminfExactUberValidated = false;
                LastRecoveredEndminfExactUberFailure = failure;
                return false;
            }
            bool valid = pipeline.recoveredEndminfUberExactRuntime
                .ValidatePendingAfterSynchronizedRender(out failure);
            LastRecoveredEndminfExactUberValidated = valid;
            LastRecoveredEndminfExactUberFailure = valid
                ? string.Empty
                : failure;
            return valid;
        }

        protected override void Render(ScriptableRenderContext context, Camera[] cameras)
        {
            foreach (Camera camera in cameras)
                RenderCamera(context, camera);
        }

        private void RenderCamera(ScriptableRenderContext context, Camera camera)
        {
            // This must run before culling: the neutral ReferenceBackdrop is a
            // presentation surface, not part of the original physical-HDR
            // CharInfo scene or its raw-scene histogram. The finally block is
            // equally important: RenderSettings and the presentation renderer
            // are shared state and must not leak into the next camera.
            bool drawRecoveredCharInfoSky;
            EndfieldRecoveredCharInfoSky preparedSourceSky =
                EndfieldRecoveredCharInfoSky.PrepareForCamera(
                    camera,
                    out drawRecoveredCharInfoSky);
            try
            {
                if (recoveredMultiCharacterShadowAtlasRequested)
                    PrepareRecoveredMultiCharacterShadowTransport(camera);
                RenderPreparedCamera(
                    context,
                    camera,
                    drawRecoveredCharInfoSky);
            }
            finally
            {
                RestoreRecoveredMultiCharacterShadowTransport();
                recoveredScreenDirectAudit.RestoreAfterCamera(camera);
                EndfieldRecoveredCharInfoSky.RestoreAfterCamera(
                    preparedSourceSky);
            }
        }

        private void RenderPreparedCamera(
            ScriptableRenderContext context,
            Camera camera,
            bool drawRecoveredCharInfoSky)
        {
            ScriptableCullingParameters cullingParameters;
            if (!camera.TryGetCullingParameters(out cullingParameters))
                return;
            bool exactEndminfM21PeakPrepared =
                EndfieldRecoveredEndminfM21PeakExactRuntime
                    .PrepareBeforeCulling(camera);
            bool exactEndminfM20PeakPrepared =
                EndfieldRecoveredEndminfM20PeakExactRuntime
                    .PrepareBeforeCulling(camera);
            bool exactEndminfM18PeakPrepared =
                EndfieldRecoveredEndminfM18PeakExactRuntime
                    .PrepareBeforeCulling(camera);
            bool exactEndminfM28PeakPrepared =
                recoveredEndminfM28PeakExactRuntime
                    .PrepareBeforeCulling(camera);
            bool exactEndminfM13Prepared =
                EndfieldRecoveredEndminfM13ExactRuntime
                    .PrepareBeforeCulling(camera);
            bool exactEndminfOpeningStripPrepared =
                EndfieldRecoveredEndminfOpeningStripExactRuntime
                    .PrepareBeforeCulling(camera);
            bool exactEndminfVFXBaseV2PeakPrepared =
                EndfieldRecoveredEndminfVFXBaseV2PeakCohortRuntime
                    .PrepareBeforeCulling(camera);
            bool exactEndminfM14Prepared =
                !exactEndminfVFXBaseV2PeakPrepared &&
                EndfieldRecoveredEndminfM14ExactRuntime
                    .PrepareBeforeCulling(camera);
            bool exactEndminfM29Prepared =
                EndfieldRecoveredEndminfM29ExactRuntime
                    .PrepareBeforeCulling(camera);
            bool exactEndminfM30Prepared =
                !exactEndminfVFXBaseV2PeakPrepared &&
                EndfieldRecoveredEndminfM30ExactRuntime
                    .PrepareBeforeCulling(camera);
            bool exactEndminfM31PeakPrepared =
                !exactEndminfVFXBaseV2PeakPrepared &&
                EndfieldRecoveredEndminfM31PeakExactRuntime
                    .PrepareBeforeCulling(camera);

            float requestedShadowDistance =
                recoveredDirectionalCSMProducer.Requested
                    ? Mathf.Max(
                        asset.characterShadowDistance,
                        EndfieldRecoveredDirectionalCSMProducer.MaxDistance)
                    : asset.characterShadowDistance;
            cullingParameters.shadowDistance = Mathf.Min(
                requestedShadowDistance,
                camera.farClipPlane);

            if (recoveredScreenDirectAudit.SameOwnerRequested)
            {
                EndfieldRecoveredPreGBufferDiagnostic.LogicalDrawInfo[]
                    logicalDrawsBeforeCull =
                        recoveredPreGBufferDiagnostic
                            .CollectLogicalDrawsForSameOwner(camera);
                recoveredScreenDirectAudit.PrepareSameOwnerBeforeCulling(
                    camera,
                    logicalDrawsBeforeCull);
            }
            recoveredSceneMVCompositor.PrepareRendererIdSidecarBeforeCulling(camera);

            EndfieldRecoveredDirectionalCSMProducer.CullingOverride
                directionalCSMCullingOverride =
                    recoveredDirectionalCSMProducer.PrepareForCulling(camera);
            bool recoveredDirectionalCSMReady = false;
            CullingResults cullingResults;
            try
            {
                cullingResults = context.Cull(ref cullingParameters);
                recoveredDirectionalCSMReady =
                    recoveredDirectionalCSMProducer.Render(
                    context,
                    camera,
                    cullingResults,
                    directionalCSMCullingOverride.light);
            }
            finally
            {
                directionalCSMCullingOverride.Restore();
            }
            EndfieldRecoveredCharacterShadowFrame characterShadowFrame =
                RenderCharacterShadowMap(
                context, camera, cullingResults);
            context.SetupCameraProperties(camera);

            EndfieldHGRPCharacterLightingVolume characterVolume =
                Object.FindObjectOfType<EndfieldHGRPCharacterLightingVolume>();
            if (characterVolume != null)
                characterVolume.ApplyGlobals(camera);
            EndfieldHGOperatorLightRig operatorLightRig =
                camera.GetComponent<EndfieldHGOperatorLightRig>();
            EndfieldHGOperatorPresentation operatorPresentation =
                camera.GetComponent<EndfieldHGOperatorPresentation>();

            CommandBuffer commandBuffer = new CommandBuffer { name = "HGCompat Camera Setup" };
            int renderWidth = Mathf.Max(camera.pixelWidth, 1);
            int renderHeight = Mathf.Max(camera.pixelHeight, 1);
            bool postProcessRequested =
                asset.applyCharacterPostProcess && postProcessMaterial != null;
            bool recoveredSceneColorFormatReady =
                TryValidateRecoveredSceneColorFormat(
                    out string recoveredSceneColorFormatFailure);
            bool applyPostProcess =
                postProcessRequested && recoveredSceneColorFormatReady;
            if (postProcessRequested &&
                !recoveredSceneColorFormatReady &&
                !loggedRecoveredSceneColorFormatFailure)
            {
                Debug.LogWarning(
                    "Recovered scene-color/post chain failed closed for " +
                    $"camera '{camera.name}': {recoveredSceneColorFormatFailure}. " +
                    "The pipeline will not substitute Unity DefaultHDR.");
                loggedRecoveredSceneColorFormatFailure = true;
            }
            RenderTextureDescriptor cameraColorDescriptor = default;
            int canonicalForwardDepthBits = 0;
            bool useRecoveredPostSemantics =
                Shader.GetGlobalFloat(RecoveredPostSemanticsId) > 0.5f;
            bool recoveredPostUberWorldUiRequested;
            string recoveredPostUberWorldUiFailure;
            RenderTexture recoveredPrimarySceneDepth;
            GraphicsFormat recoveredPrimarySceneDepthFormat;
            bool useRecoveredPostUberWorldUi = TryPrepareRecoveredPostUberWorldUi(
                camera,
                renderWidth,
                renderHeight,
                applyPostProcess,
                useRecoveredPostSemantics,
                out recoveredPostUberWorldUiRequested,
                out recoveredPrimarySceneDepth,
                out recoveredPrimarySceneDepthFormat,
                out recoveredPostUberWorldUiFailure);
            EndfieldRecoveredSceneMVRequest recoveredSceneMVRequest =
                recoveredSceneMVCompositor.CollectRequest(camera);
            if ((exactEndminfM14Prepared || exactEndminfM29Prepared ||
                    exactEndminfOpeningStripPrepared ||
                    exactEndminfM28PeakPrepared ||
                    exactEndminfVFXBaseV2PeakPrepared) &&
                !recoveredSceneMVRequest.requested)
            {
                recoveredSceneMVRequest = new EndfieldRecoveredSceneMVRequest(
                    true,
                    true,
                    false,
                    string.Empty);
            }
            ResetRecoveredSceneMVDiagnostic(recoveredSceneMVRequest.requested);
            LastRecoveredSceneMVDiagnostic.requestFailure =
                recoveredSceneMVRequest.failure ?? string.Empty;
            LastRecoveredSceneMVDiagnostic.glow902Queue3005Requested =
                recoveredSceneMVRequest.hasGlow902Queue3005;
            RenderTexture recoveredSceneMV = null;
            string recoveredSceneMVFailure = recoveredSceneMVRequest.failure;
            bool useRecoveredSceneMV = false;
            if (recoveredSceneMVRequest.requested &&
                recoveredSceneMVRequest.valid &&
                applyPostProcess)
            {
                if (recoveredPrimarySceneDepth == null &&
                    !TryCreateRecoveredPrimarySceneDepth(
                        renderWidth,
                        renderHeight,
                        out recoveredPrimarySceneDepth,
                        out recoveredPrimarySceneDepthFormat,
                        out recoveredSceneMVFailure))
                {
                    useRecoveredSceneMV = false;
                }
                else
                {
                    useRecoveredSceneMV = recoveredSceneMVCompositor.TryCreateSceneMV(
                        renderWidth,
                        renderHeight,
                        out recoveredSceneMV,
                        out recoveredSceneMVFailure);
                }
            }
            else if (recoveredSceneMVRequest.requested && !applyPostProcess)
            {
                recoveredSceneMVFailure =
                    "the owned physical-HDR/post scene-color chain is disabled";
            }
            if (!useRecoveredSceneMV)
            {
                string sidecarFailure = recoveredSceneMVFailure;
                if (string.IsNullOrEmpty(sidecarFailure))
                {
                    sidecarFailure = recoveredSceneMVRequest.requested
                        ? "recovered SceneMV was not used after request evaluation"
                        : "no exact selected MRT material is active";
                }
                recoveredSceneMVCompositor
                    .PublishRendererIdSidecarFailureForCurrentCapture(
                        camera,
                        sidecarFailure);
            }
            if (recoveredSceneMVRequest.requested &&
                !useRecoveredSceneMV &&
                !loggedRecoveredSceneMVFailure)
            {
                Debug.LogWarning(
                    "Recovered sceneMV path failed closed for " +
                    $"camera '{camera.name}': {recoveredSceneMVFailure}.");
                loggedRecoveredSceneMVFailure = true;
            }
            bool useRecoveredPreGBufferDepthOwner = false;
            if (recoveredPreGBufferDepthOwner.Requested)
            {
                string recoveredPreGBufferDepthAllocationFailure = null;
                bool depthReady = recoveredPrimarySceneDepth != null ||
                    TryCreateRecoveredPrimarySceneDepth(
                        renderWidth,
                        renderHeight,
                        out recoveredPrimarySceneDepth,
                        out recoveredPrimarySceneDepthFormat,
                        out recoveredPreGBufferDepthAllocationFailure);
                bool sceneMVReady = recoveredSceneMV != null ||
                    recoveredSceneMVCompositor.TryCreateSceneMV(
                        renderWidth,
                        renderHeight,
                        out recoveredSceneMV,
                        out recoveredPreGBufferDepthAllocationFailure);
                if (depthReady && sceneMVReady)
                {
                    useRecoveredPreGBufferDepthOwner = true;
                }
                else if (!loggedRecoveredPreGBufferDepthOwnerFailure)
                {
                    Debug.LogWarning(
                        "Recovered canonical CharacterPrePass depth owner failed " +
                        $"closed for camera '{camera.name}': " +
                        recoveredPreGBufferDepthAllocationFailure + ".");
                    loggedRecoveredPreGBufferDepthOwnerFailure = true;
                }
            }
            if (!useRecoveredSceneMV &&
                !useRecoveredPostUberWorldUi &&
                !useRecoveredPreGBufferDepthOwner &&
                recoveredPrimarySceneDepth != null)
            {
                ReleaseRecoveredPrimarySceneDepth(recoveredPrimarySceneDepth);
                recoveredPrimarySceneDepth = null;
                recoveredPrimarySceneDepthFormat = GraphicsFormat.None;
            }
            bool useSeparatePrimaryDepth =
                useRecoveredPostUberWorldUi ||
                useRecoveredSceneMV ||
                useRecoveredPreGBufferDepthOwner;
            if (recoveredPostUberWorldUiRequested &&
                !useRecoveredPostUberWorldUi &&
                !loggedRecoveredPostUberWorldUiFailure)
            {
                Debug.LogWarning(
                    "Recovered post-Uber CharInfo world UI failed closed for " +
                    $"camera '{camera.name}': {recoveredPostUberWorldUiFailure}. " +
                    "The source portrait shader remains clipped and ordinary non-world-UI " +
                    "transparents retain their canonical schedule.");
                loggedRecoveredPostUberWorldUiFailure = true;
            }
            bool useRecoveredCameraDepth =
                applyPostProcess &&
                operatorLightRig != null &&
                operatorLightRig.sourceBackedClusteredNprLightLoop &&
                ((!useRecoveredPostUberWorldUi && !useRecoveredSceneMV) ||
                 recoveredDeferredExactConsumer.Requested);
            RenderTexture physicalRecoveredCameraDepth = null;
            EndfieldRecoveredCharInfoAutoExposureCameraState liveAutoExposureState =
                PrepareRecoveredLiveCharInfoAutoExposure(
                    camera,
                    applyPostProcess,
                    useRecoveredPostSemantics,
                    recoveredSceneMVRequest.requested &&
                    camera.GetComponent<EndfieldHGOperatorPresentation>() is
                        EndfieldHGOperatorPresentation exposurePresentation &&
                    exposurePresentation.environmentPhaseSnapshot != null &&
                    exposurePresentation.environmentPhaseSnapshot
                        .IsGachaRoomSourceClosed);
            if (applyPostProcess)
            {
                cameraColorDescriptor = CreateRecoveredSceneColorDescriptor(
                    renderWidth,
                    renderHeight,
                    useSeparatePrimaryDepth ? 0 : 24);
                canonicalForwardDepthBits = useSeparatePrimaryDepth
                    ? recoveredPrimarySceneDepthFormat == GraphicsFormat.D32_SFloat_S8_UInt
                        ? 32
                        : 24
                    : cameraColorDescriptor.depthBufferBits;
                commandBuffer.GetTemporaryRT(
                    CameraColorId,
                    cameraColorDescriptor,
                    FilterMode.Point);
                if (useSeparatePrimaryDepth)
                {
                    commandBuffer.SetRenderTarget(
                        new RenderTargetIdentifier(CameraColorId),
                        new RenderTargetIdentifier(recoveredPrimarySceneDepth));
                }
                else
                {
                    commandBuffer.SetRenderTarget(CameraColorId);
                }
                if (useRecoveredCameraDepth)
                {
                    var cameraDepthDescriptor = new RenderTextureDescriptor(
                        renderWidth,
                        renderHeight,
                        RenderTextureFormat.RFloat,
                        0)
                    {
                        msaaSamples = 1,
                        sRGB = false
                    };
                    if (recoveredDeferredExactConsumer.Requested)
                    {
                        physicalRecoveredCameraDepth =
                            EnsureRecoveredExactCameraDepth(
                                cameraDepthDescriptor);
                    }
                    else
                    {
                        commandBuffer.GetTemporaryRT(
                            RecoveredCameraDepthTextureId,
                            cameraDepthDescriptor,
                            // The selected HGRP/UI/Default variant binds _SceneDepth
                            // through its LinearRepeat sampler. This lab texture is
                            // still a character-only substitute, but its in-range
                            // sampling must retain the original linear filter.
                            FilterMode.Bilinear);
                    }
                }
            }
            commandBuffer.SetGlobalFloat(RecoveredCameraDepthReadyId, 0.0f);
            // Soft-blend admission is published only after the source-backed
            // primary scene depth has been selected below. This remains zero
            // for ordinary cameras and every failed/degraded route.
            commandBuffer.SetGlobalFloat(RecoveredVFXSoftDepthReadyId, 0.0f);
            commandBuffer.SetGlobalFloat(RecoveredPostUberWorldUiReadyId, 0.0f);
            commandBuffer.SetGlobalFloat(RenderPathInjectedId, 0.0f);
            commandBuffer.SetGlobalFloat(HGFlipXId, 0.0f);
            commandBuffer.SetGlobalFloat(HGFlipYId, 0.0f);
            commandBuffer.SetGlobalFloat(
                EndfieldRecoveredSceneMVCompositor.SceneMVMRTReadyId,
                0.0f);
            commandBuffer.SetGlobalFloat(
                EndfieldRecoveredSceneMVCompositor.VFXGlobalsReadyId,
                0.0f);
            Vector3 overlayCameraOrigin = camera.transform.position;
            commandBuffer.SetGlobalVector(
                OverlayCameraRelativeOriginId,
                new Vector4(
                    overlayCameraOrigin.x,
                    overlayCameraOrigin.y,
                    overlayCameraOrigin.z,
                    1.0f));
            // Jitter is retained at zero until the matching motion/depth
            // reprojection is active. The exact native Halton sequence was
            // validated separately; applying it to unreprojected history is a
            // measured regression rather than a valid partial TAAU state.
            commandBuffer.SetGlobalVector(OverlayTaaJitterStrengthId, Vector4.zero);
            // Retail HGCamera.Update copies HGAdditionalCameraData.materialMipBias
            // into ShaderVariablesGlobal._GlobalMipBias and publishes
            // _GlobalMipBiasPow2 = pow(2, bias). The original ExternalCamera
            // used by the selected recovery scene serializes bias 0, matching
            // every currently recovered camera component, so 0/1 is the exact
            // authored pair rather than an unresolved compatibility fallback.
            commandBuffer.SetGlobalFloat(GlobalMipBiasId, 0.0f);
            commandBuffer.SetGlobalFloat(GlobalMipBiasPow2Id, 1.0f);
            // UpdateShaderVariablesGraphFeaturesGlobalParam0 writes z/w = 1;
            // the selected overlay therefore bypasses atmosphere modulation.
            // The isolated CharInfo rig publishes its source-backed punctual
            // rows and XY/Z membership later in this camera setup. If that
            // producer is unavailable, this carrier retains the exact neutral
            // zero-occlusion endpoint.
            commandBuffer.SetGlobalVector(
                OverlayEnvironmentParamsId,
                new Vector4(0.0f, 1.0f, 1.0f, 1.0f));
            if (useRecoveredSceneMV)
            {
                commandBuffer.SetGlobalTexture(
                    SceneDepthId,
                    recoveredPrimarySceneDepth);
                commandBuffer.SetGlobalTexture(
                    CameraDepthTextureId,
                    recoveredPrimarySceneDepth);
                commandBuffer.SetGlobalVector(
                    SceneDepthTexelSizeId,
                    new Vector4(
                        1.0f / renderWidth,
                        1.0f / renderHeight,
                        renderWidth,
                        renderHeight));
                commandBuffer.SetGlobalVector(
                    CameraDepthTextureTexelSizeId,
                    new Vector4(
                        1.0f / renderWidth,
                        1.0f / renderHeight,
                        renderWidth,
                        renderHeight));
                commandBuffer.SetGlobalFloat(RecoveredVFXSoftDepthReadyId, 1.0f);
            }
            else if (recoveredPostUberWorldUiRequested)
            {
                commandBuffer.SetGlobalTexture(SceneDepthId, Texture2D.blackTexture);
                commandBuffer.SetGlobalTexture(CameraDepthTextureId, Texture2D.blackTexture);
            }
            float recoveredVFXExposure = liveAutoExposureState != null
                ? liveAutoExposureState.CurrentExposure
                : Shader.GetGlobalVector(ExposureParamsId).x;
            bool recoveredVFXExposureReady =
                recoveredVFXExposure > 0.0f &&
                !float.IsNaN(recoveredVFXExposure) &&
                !float.IsInfinity(recoveredVFXExposure);
            if (recoveredVFXExposureReady)
            {
                commandBuffer.SetGlobalVector(
                    EndfieldRecoveredSceneMVCompositor.ExposureWithMiscParamsId,
                    new Vector4(
                        recoveredVFXExposure,
                        1.0f / recoveredVFXExposure,
                        renderWidth / (float)renderHeight,
                        0.0f));
            }
            Transform recoveredVFXPlayerCenter = null;
            bool recoveredVFXPlayerCenterReady =
                useRecoveredSceneMV &&
                TryResolveRecoveredVFXPlayerCenter(out recoveredVFXPlayerCenter);
            if (useRecoveredSceneMV &&
                recoveredVFXExposureReady &&
                recoveredVFXPlayerCenterReady)
            {
                Vector3 playerCenter = recoveredVFXPlayerCenter.position;
                commandBuffer.SetGlobalVector(
                    EndfieldRecoveredSceneMVCompositor.VFXParams0Id,
                    new Vector4(
                        playerCenter.x,
                        playerCenter.y,
                        playerCenter.z,
                        Time.time % 1024.0f));
                commandBuffer.SetGlobalFloat(
                    EndfieldRecoveredSceneMVCompositor.VFXGlobalsReadyId,
                    1.0f);
            }
            else if (useRecoveredSceneMV && !loggedRecoveredVFXGlobalsFailure)
            {
                Debug.LogWarning(
                    "Recovered VFX globals remained fail-closed for " +
                    $"camera '{camera.name}': exposure={recoveredVFXExposure:0.######}, " +
                    $"exposureReady={recoveredVFXExposureReady}, " +
                    $"uniquePlayerCenterReady={recoveredVFXPlayerCenterReady}. " +
                    "The selected VFX program will clip before writing either MRT.");
                loggedRecoveredVFXGlobalsFailure = true;
            }
            if (liveAutoExposureState != null)
            {
                float currentExposure = liveAutoExposureState.CurrentExposure;
                commandBuffer.SetGlobalVector(
                    ExposureParamsId,
                    new Vector4(currentExposure, 0.0f, 0.0f, 0.0f));
                if (characterVolume != null)
                {
                    characterVolume.ApplyRecoveredExposureDependentGlobals(
                        commandBuffer,
                        currentExposure);
                }
            }
            bool selectedGachaSceneColor =
                operatorPresentation != null &&
                operatorPresentation.useRecoveredGachaRoomPostProfile;
            Color sceneColorClear = selectedGachaSceneColor
                ? RecoveredGachaSceneColorClear
                : drawRecoveredCharInfoSky
                    ? Color.clear
                    : asset.clearColor;
            commandBuffer.ClearRenderTarget(true, true, sceneColorClear);
            ApplyLightingGlobals(commandBuffer);
            recoveredReflectionProbeFallback.ResetPublication(commandBuffer);
            recoveredVisibilitySHConstants.ResetPublication(commandBuffer);
            recoveredDeferredTransformVariables.ResetPublication(commandBuffer);
            recoveredShaderVariablesGlobal.ResetPublication(commandBuffer);
            recoveredDeferredLightData.ResetPublication(commandBuffer);
            recoveredDeferredShadowData.ResetPublication(commandBuffer);
            bool recoveredCanonicalBinningReady =
                recoveredLightBinning.PrepareCamera(
                camera,
                renderWidth,
                renderHeight,
                operatorLightRig,
                commandBuffer);
            bool recoveredCanonicalFrameResourcesReady = false;
            bool recoveredDeferredTransformsReady = false;
            bool recoveredShaderVariablesGlobalReady = false;
            if (recoveredCanonicalBinningReady)
            {
                string reflectionFailure;
                bool recoveredReflectionFrameReady = false;
                try
                {
                    recoveredReflectionFrameReady =
                        recoveredReflectionProbeFallback
                            .PrepareAndPublishRecoveredResources(
                                camera,
                                renderWidth,
                                renderHeight,
                                characterVolume != null
                                    ? characterVolume.environmentReflectionCubemap
                                    : null,
                                commandBuffer,
                                false,
                                out reflectionFailure);
                }
                catch (System.Exception exception)
                {
                    reflectionFailure =
                        "reflection resource publication threw: " +
                        exception.Message;
                }
                if (!recoveredReflectionFrameReady)
                {
                    recoveredLightBinning.DisableCanonicalPublication(
                        commandBuffer);
                    if (!loggedRecoveredReflectionFrameFailure)
                    {
                        Debug.LogWarning(
                            "Recovered canonical CharInfo reflection frame " +
                            "failed closed: " + reflectionFailure + ".");
                        loggedRecoveredReflectionFrameFailure = true;
                    }
                }
                else
                {
                    string visibilityConstantsFailure;
                    bool recoveredVisibilityConstantsReady =
                        recoveredVisibilitySHConstants.PrepareAndPublish(
                            renderWidth,
                            renderHeight,
                            commandBuffer,
                            out visibilityConstantsFailure);
                    if (!recoveredVisibilityConstantsReady)
                    {
                        recoveredLightBinning.DisableCanonicalPublication(
                            commandBuffer);
                        recoveredReflectionProbeFallback.ResetPublication(
                            commandBuffer);
                        if (!loggedRecoveredReflectionFrameFailure)
                        {
                            Debug.LogWarning(
                                "Recovered canonical CharInfo " +
                                "VisibilitySHConstData frame failed closed: " +
                                visibilityConstantsFailure + ".");
                            loggedRecoveredReflectionFrameFailure = true;
                        }
                    }
                    else
                    {
                        if (!loggedRecoveredReflectionFrameActivation)
                        {
                            Debug.Log(
                                "Recovered canonical CharInfo binning + reflection " +
                                "oct/global + exact VisibilitySHConstData " +
                                "frame resources are active for the exact " +
                                "no-local-probe fixture.");
                            loggedRecoveredReflectionFrameActivation = true;
                        }
                        recoveredCanonicalFrameResourcesReady = true;
                        if (EndfieldRecoveredDeferredTransformVariables.IsRequested)
                        {
                            recoveredDeferredTransformsReady =
                                recoveredDeferredTransformVariables
                                    .PrepareAndPublish(
                                        camera,
                                        true,
                                        commandBuffer,
                                        out string transformFailure);
                            if (recoveredDeferredTransformsReady)
                            {
                                if (!loggedRecoveredDeferredTransformActivation)
                                {
                                    Debug.Log(
                                        "Recovered selected deferred " +
                                        "_TransformVariables b30 reads are active " +
                                        "for the physical CharInfo camera; pass0=" +
                                        "disabled.");
                                    loggedRecoveredDeferredTransformActivation = true;
                                }
                            }
                            else if (!loggedRecoveredDeferredTransformFailure)
                            {
                                Debug.LogWarning(
                                    "Recovered selected deferred " +
                                    "_TransformVariables failed closed: " +
                                    transformFailure + ".");
                                loggedRecoveredDeferredTransformFailure = true;
                            }
                        }
                        if (EndfieldRecoveredShaderVariablesGlobal.IsRequested)
                        {
                            Vector4 environmentParams = characterVolume != null
                                ? characterVolume.environmentGlobalParams0
                                : Vector4.zero;
                            recoveredShaderVariablesGlobalReady =
                                recoveredShaderVariablesGlobal.PrepareAndPublish(
                                    camera,
                                    renderWidth,
                                    renderHeight,
                                    environmentParams,
                                    recoveredDeferredTransformsReady,
                                    commandBuffer,
                                    out string shaderVariablesFailure);
                            if (recoveredShaderVariablesGlobalReady)
                            {
                                if (!loggedRecoveredShaderVariablesGlobalActivation)
                                {
                                    Debug.Log(
                                        "Recovered selected " +
                                        "ShaderVariablesGlobal b35 / " +
                                        "EndfieldCB1 reads are active; pass0=" +
                                        "disabled.");
                                    loggedRecoveredShaderVariablesGlobalActivation =
                                        true;
                                }
                            }
                            else if (!loggedRecoveredShaderVariablesGlobalFailure)
                            {
                                Debug.LogWarning(
                                    "Recovered selected ShaderVariablesGlobal " +
                                    "failed closed: " + shaderVariablesFailure + ".");
                                loggedRecoveredShaderVariablesGlobalFailure = true;
                            }
                        }
                    }
                }
            }
            if (EndfieldRecoveredDeferredTransformVariables.IsRequested &&
                !recoveredCanonicalFrameResourcesReady &&
                !loggedRecoveredDeferredTransformFailure)
            {
                Debug.LogWarning(
                    "Recovered selected deferred _TransformVariables failed " +
                    "closed: canonical binning/reflection/" +
                    "VisibilitySHConstData prerequisites are not ready.");
                loggedRecoveredDeferredTransformFailure = true;
            }
            if (EndfieldRecoveredShaderVariablesGlobal.IsRequested &&
                !recoveredCanonicalFrameResourcesReady &&
                !loggedRecoveredShaderVariablesGlobalFailure)
            {
                Debug.LogWarning(
                    "Recovered selected ShaderVariablesGlobal failed closed: " +
                    "canonical binning/reflection/VisibilitySHConstData " +
                    "prerequisites are not ready.");
                loggedRecoveredShaderVariablesGlobalFailure = true;
            }
            context.ExecuteCommandBuffer(commandBuffer);
            commandBuffer.Release();

            bool recoveredPunctualShadowReady =
                recoveredPunctualShadowProducer.Render(
                context,
                camera,
                operatorLightRig,
                applyPostProcess
                    ? new RenderTargetIdentifier(CameraColorId)
                    : new RenderTargetIdentifier(BuiltinRenderTextureType.CameraTarget));

            bool recoveredDeferredLightDataReady = false;
            bool recoveredDeferredShadowDataReady = false;
            if (EndfieldRecoveredDeferredLightData.IsRequested)
            {
                CommandBuffer lightDataCommand = new CommandBuffer
                {
                    name = "Recovered selected deferred LightData"
                };
                recoveredDeferredLightDataReady =
                    recoveredDeferredLightData.PrepareAndPublish(
                        camera,
                        cullingResults,
                        characterVolume != null
                            ? characterVolume.sceneMainLight
                            : null,
                        operatorLightRig,
                        recoveredCanonicalFrameResourcesReady,
                        recoveredDeferredTransformsReady,
                        lightDataCommand,
                        out string lightDataFailure);
                context.ExecuteCommandBuffer(lightDataCommand);
                lightDataCommand.Release();
                if (recoveredDeferredLightDataReady)
                {
                    bool endminfLightData = operatorLightRig != null &&
                        operatorLightRig.actorRoot != null &&
                        string.Equals(
                            operatorLightRig.actorRoot.name,
                            "Endminf",
                            System.StringComparison.OrdinalIgnoreCase);
                    if (endminfLightData &&
                        !loggedRecoveredDeferredEndminfLightDataResult)
                    {
                        Debug.Log(
                            "Recovered selected deferred _LightDataBuffer b31 " +
                            "reads are active for the source-closed Endminf " +
                            "12-light CharInfo fixture; pass0=disabled, presented=false.");
                        loggedRecoveredDeferredEndminfLightDataResult = true;
                    }
                    if (!loggedRecoveredDeferredLightDataActivation)
                    {
                        Debug.Log(
                            "Recovered selected deferred _LightDataBuffer b31 " +
                            "reads are active for the source-closed " +
                            "Wulfa/Zhuangfy CharInfo fixture; pass0=disabled.");
                        loggedRecoveredDeferredLightDataActivation = true;
                    }
                }
                else
                {
                    bool endminfLightData = operatorLightRig != null &&
                        operatorLightRig.actorRoot != null &&
                        string.Equals(
                            operatorLightRig.actorRoot.name,
                            "Endminf",
                            System.StringComparison.OrdinalIgnoreCase);
                    if (endminfLightData &&
                        !loggedRecoveredDeferredEndminfLightDataResult)
                    {
                        Debug.LogWarning(
                            "Recovered selected deferred Endminf 12-light " +
                            "_LightDataBuffer failed closed: " +
                            lightDataFailure + ".");
                        loggedRecoveredDeferredEndminfLightDataResult = true;
                    }
                    if (!loggedRecoveredDeferredLightDataFailure)
                    {
                        Debug.LogWarning(
                            "Recovered selected deferred _LightDataBuffer failed " +
                            "closed: " + lightDataFailure + ".");
                        loggedRecoveredDeferredLightDataFailure = true;
                    }
                }
            }

            if (EndfieldRecoveredDeferredShadowData.IsRequested)
            {
                CommandBuffer shadowDataCommand = new CommandBuffer
                {
                    name = "Recovered selected deferred ShadowData"
                };
                recoveredDeferredShadowDataReady =
                    recoveredDeferredShadowData.PrepareAndPublish(
                        camera,
                        operatorLightRig,
                        recoveredPunctualShadowProducer,
                        recoveredDeferredLightDataReady,
                        recoveredPunctualShadowReady,
                        shadowDataCommand,
                        out string shadowDataFailure);
                context.ExecuteCommandBuffer(shadowDataCommand);
                shadowDataCommand.Release();
                if (recoveredDeferredShadowDataReady)
                {
                    if (!loggedRecoveredDeferredShadowDataActivation)
                    {
                        Debug.Log(
                            "Recovered selected deferred ShadowData b34 " +
                            "punctual section and matching D16 atlas are " +
                            "active for the validated isolated actor fixture; " +
                            "pass0=disabled.");
                        loggedRecoveredDeferredShadowDataActivation = true;
                    }
                }
                else if (!loggedRecoveredDeferredShadowDataFailure)
                {
                    Debug.LogWarning(
                        "Recovered selected deferred ShadowData failed " +
                        "closed: " + shadowDataFailure + ".");
                    loggedRecoveredDeferredShadowDataFailure = true;
                }
            }

            if (useRecoveredCameraDepth)
            {
                RenderRecoveredCameraDepth(
                    context,
                    camera,
                    renderWidth,
                    renderHeight,
                    physicalRecoveredCameraDepth != null
                        ? new RenderTargetIdentifier(
                            physicalRecoveredCameraDepth)
                        : new RenderTargetIdentifier(
                            RecoveredCameraDepthTextureId));
            }

            RenderTargetIdentifier canonicalColorTarget = applyPostProcess
                ? new RenderTargetIdentifier(CameraColorId)
                : new RenderTargetIdentifier(BuiltinRenderTextureType.CameraTarget);
            EndfieldRecoveredPreGBufferDiagnostic.Frame preGBufferFrame =
                recoveredPreGBufferDiagnostic.Render(
                    context,
                    camera,
                    renderWidth,
                    renderHeight,
                    canonicalColorTarget);
            RenderTargetIdentifier canonicalDepthTarget =
                useSeparatePrimaryDepth
                    ? new RenderTargetIdentifier(recoveredPrimarySceneDepth)
                    : applyPostProcess
                        ? new RenderTargetIdentifier(CameraColorId)
                        : new RenderTargetIdentifier(BuiltinRenderTextureType.CameraTarget);
            bool recoveredDeferredGBufferFrameReady =
                recoveredDeferredGBufferFrame.Render(
                    context,
                    camera,
                    renderWidth,
                    renderHeight,
                    recoveredCanonicalFrameResourcesReady,
                    canonicalColorTarget,
                    canonicalDepthTarget);
            recoveredEndminfM27DeferredPresentation.PublishDepth(
                context,
                camera,
                renderWidth,
                renderHeight,
                recoveredDeferredGBufferFrameReady,
                recoveredDeferredGBufferFrame,
                canonicalColorTarget,
                canonicalDepthTarget);
            recoveredSphereOutsideDeferredPresentation.PublishDepth(
                context,
                camera,
                renderWidth,
                renderHeight,
                recoveredDeferredGBufferFrameReady,
                recoveredDeferredGBufferFrame,
                canonicalColorTarget,
                canonicalDepthTarget);
            EndfieldRecoveredContactShadowProducer.Frame
                recoveredContactShadowFrame =
                    recoveredContactShadowProducer.Render(
                        context,
                        camera,
                        preGBufferFrame,
                        characterVolume != null
                            ? characterVolume.sceneMainLight
                            : null,
                        canonicalColorTarget,
                        canonicalDepthTarget);
            bool recoveredLowResDirectionalShadowReady =
                recoveredLowResDirectionalShadowProducer.Render(
                context,
                camera,
                preGBufferFrame,
                recoveredDirectionalCSMReady,
                useSeparatePrimaryDepth
                    ? recoveredPrimarySceneDepth
                    : null,
                recoveredContactShadowFrame,
                canonicalColorTarget);
            recoveredVisibilitySHProducer.Render(
                context,
                camera,
                preGBufferFrame,
                canonicalColorTarget,
                canonicalDepthTarget,
                recoveredCanonicalFrameResourcesReady);
            bool recoveredScreenShadowMaskReady =
                recoveredScreenShadowMaskDiagnostic.Render(
                context,
                camera,
                preGBufferFrame,
                characterShadowFrame,
                canonicalColorTarget);

            if (useSeparatePrimaryDepth)
            {
                commandBuffer = new CommandBuffer
                {
                    name = "Restore recovered primary scene color/depth"
                };
                commandBuffer.SetRenderTarget(
                    new RenderTargetIdentifier(CameraColorId),
                    new RenderTargetIdentifier(recoveredPrimarySceneDepth));
                context.ExecuteCommandBuffer(commandBuffer);
                commandBuffer.Release();
            }

            string recoveredPreGBufferDepthOwnerFailure;
            recoveredPreGBufferDepthOwner.RenderCanonicalOwner(
                context,
                camera,
                renderWidth,
                renderHeight,
                canonicalColorTarget,
                recoveredSceneMV,
                canonicalDepthTarget,
                useSeparatePrimaryDepth,
                useSeparatePrimaryDepth
                    ? recoveredPrimarySceneDepthFormat
                    : GraphicsFormat.None,
                out recoveredPreGBufferDepthOwnerFailure);

            // Installed DefaultDeferred orders screen-shadow resolve after
            // DepthPrepass/GBuffer/contact/capsule work and before deferred
            // lighting/ForwardOpaque. This is a default-off attachment-only
            // diagnostic until every producer of retail scene R is recovered;
            // it deliberately returns content-invalid and cannot enable Eye R.
            recoveredScreenShadowMaskProducer.Render(
                context,
                camera,
                renderWidth,
                renderHeight,
                canonicalColorTarget,
                canonicalDepthTarget,
                preGBufferFrame,
                characterShadowFrame,
                recoveredLowResDirectionalShadowReady,
                recoveredContactShadowFrame.ready);

            EndfieldRecoveredDeferredResolverInputProbe.ResourceFrame
                recoveredDeferredResolverResources =
                    EndfieldRecoveredDeferredResolverInputProbe.CaptureResources(
                        camera,
                        renderWidth,
                        renderHeight,
                        useRecoveredCameraDepth,
                        physicalRecoveredCameraDepth,
                        recoveredLightBinning,
                        recoveredReflectionProbeFallback,
                        recoveredPunctualShadowProducer,
                        recoveredLowResDirectionalShadowProducer,
                        recoveredScreenShadowMaskProducer,
                        recoveredVisibilitySHProducer);
            recoveredDeferredResolverInputProbe.Render(
                context,
                camera,
                renderWidth,
                renderHeight,
                recoveredDeferredGBufferFrame,
                recoveredDeferredGBufferFrameReady,
                recoveredDeferredTransformsReady,
                recoveredShaderVariablesGlobalReady,
                recoveredDeferredLightDataReady,
                recoveredDeferredShadowDataReady,
                recoveredDeferredResolverResources,
                canonicalColorTarget,
                canonicalDepthTarget);
            bool recoveredDeferredExactConsumerReady =
                recoveredDeferredExactConsumer.Render(
                context,
                camera,
                renderWidth,
                renderHeight,
                recoveredDeferredGBufferFrame,
                recoveredDeferredResolverResources,
                recoveredDeferredTransformVariables,
                recoveredShaderVariablesGlobal,
                recoveredReflectionProbeFallback,
                recoveredLightBinning,
                recoveredVisibilitySHConstants,
                recoveredDeferredLightData,
                recoveredDeferredShadowData,
                recoveredDeferredTransformsReady,
                recoveredShaderVariablesGlobalReady,
                recoveredDeferredLightDataReady,
                recoveredDeferredShadowDataReady,
                canonicalColorTarget,
                canonicalDepthTarget);
            recoveredSphereOutsideDeferredPresentation.Render(
                context,
                camera,
                renderWidth,
                renderHeight,
                recoveredDeferredExactConsumerReady,
                recoveredDeferredGBufferFrame,
                recoveredDeferredExactConsumer.RecoveredHlslOutput,
                canonicalColorTarget,
                canonicalDepthTarget);
            recoveredScreenDirectAudit.BeginForward(
                context,
                camera,
                applyPostProcess,
                canonicalForwardDepthBits,
                canonicalColorTarget,
                recoveredScreenShadowMaskReady,
                preGBufferFrame,
                characterShadowFrame);
            var recoveredCurrentSceneColor = new EndfieldRecoveredSceneColorHandle(
                CameraColorId,
                cameraColorDescriptor);
            if (useRecoveredSceneMV)
            {
                string opaqueSceneMVFailure;
                useRecoveredSceneMV = recoveredSceneMVCompositor.DrawOpaqueOwner(
                    context,
                    camera,
                    cullingResults,
                    recoveredCurrentSceneColor,
                    recoveredSceneMV,
                    recoveredPrimarySceneDepth,
                    recoveredPrimarySceneDepthFormat,
                    OpaqueShaderPasses,
                    asset.dynamicBatching,
                    asset.gpuInstancing,
                    recoveredPreGBufferDepthOwner.HasCurrentPublication(
                        camera,
                        renderWidth,
                        renderHeight),
                    out opaqueSceneMVFailure);
                if (!useRecoveredSceneMV && !loggedRecoveredSceneMVFailure)
                {
                    Debug.LogWarning(
                        "Recovered sceneMV opaque owner failed closed: " +
                        opaqueSceneMVFailure);
                    loggedRecoveredSceneMVFailure = true;
                }
            }
            if (!useRecoveredSceneMV)
            {
                DrawRenderers(
                    context,
                    camera,
                    cullingResults,
                    RenderQueueRange.opaque,
                    SortingCriteria.CommonOpaque);
            }
            DrawManualPassFallback(context, camera);
            DrawRecoveredAuxiliaryPasses(
                context,
                camera,
                "CHARACTER_OUTLINE",
                canonicalColorTarget,
                useRecoveredSceneMV ? recoveredSceneMV : null,
                useRecoveredSceneMV ? recoveredPrimarySceneDepth : null);

            // M27 depth is published before ForwardOpaque so the actor can
            // occlude its exact deferred fragments. Present its resolved color
            // only after ForwardOpaque: the CharInfo forward/background cohort
            // otherwise overwrites all 921 certified peak pixels even though
            // the deferred command itself succeeds.
            recoveredEndminfM27DeferredPresentation.Render(
                context,
                camera,
                renderWidth,
                renderHeight,
                recoveredDeferredExactConsumerReady,
                recoveredDeferredGBufferFrame,
                recoveredDeferredExactConsumer.RecoveredHlslOutput,
                cameraColorDescriptor,
                canonicalColorTarget,
                canonicalDepthTarget);

            if (asset.drawSkybox || drawRecoveredCharInfoSky)
                context.DrawSkybox(camera);

            bool recoveredPreTransparentSceneColorReady =
                PrepareRecoveredPreTransparentSceneColor(
                    context,
                    camera,
                    renderWidth,
                    renderHeight,
                    canonicalColorTarget,
                    cameraColorDescriptor,
                    applyPostProcess,
                    useSeparatePrimaryDepth,
                    recoveredPrimarySceneDepth);

            int ordinaryTransparentLayerMask = useRecoveredPostUberWorldUi
                ? camera.cullingMask & ~(1 << EndfieldRecoveredCharInfoBackgroundPortrait.SourceUiLayer)
                : camera.cullingMask;
            bool recoveredSceneColorPingAllocated = false;
            if (useRecoveredSceneMV)
            {
                DrawRenderers(
                    context,
                    camera,
                    cullingResults,
                    new RenderQueueRange(2501, 2998),
                    SortingCriteria.CommonTransparent | SortingCriteria.RendererPriority,
                    ordinaryTransparentLayerMask,
                    TransparentShaderPasses);

                string compositorFailure;
                EndfieldRecoveredSceneColorHandle composedSceneColor;
                bool mainReady =
                    recoveredSceneMVCompositor.CompositeMainTransparentQueue2999(
                    context,
                    camera,
                    cullingResults,
                    recoveredCurrentSceneColor,
                    EndfieldRecoveredSceneMVCompositor.PingColorId,
                    true,
                    recoveredSceneMV,
                    recoveredPrimarySceneDepth,
                    recoveredPrimarySceneDepthFormat,
                    ordinaryTransparentLayerMask,
                    asset.dynamicBatching,
                    asset.gpuInstancing,
                    recoveredPreTransparentSceneColorReady,
                    new RenderTargetIdentifier(RecoveredRefractionSceneColorId),
                    out composedSceneColor,
                    out compositorFailure);
                recoveredSceneColorPingAllocated = true;
                if (mainReady)
                    recoveredCurrentSceneColor = composedSceneColor;
                // Frames 1896-1965 retain the retail owner interval as
                // M31(first) -> transparent pre-M29/M30 work -> M31(second).
                if (mainReady && exactEndminfM31PeakPrepared)
                {
                    mainReady =
                        EndfieldRecoveredEndminfM31PeakExactRuntime.RenderFirst(
                            context,
                            camera,
                            recoveredCurrentSceneColor,
                            recoveredSceneMV,
                            recoveredPrimarySceneDepth);
                    if (!mainReady)
                    {
                        compositorFailure =
                            "exact Endminf M31 first split transport failed " +
                            "closed: " +
                            EndfieldRecoveredEndminfM31PeakExactRuntime.Failure;
                    }
                }
                if (mainReady && exactEndminfVFXBaseV2PeakPrepared)
                {
                    mainReady = EndfieldRecoveredEndminfVFXBaseV2PeakCohortRuntime
                        .RenderPreM29(
                            context,
                            camera,
                            recoveredCurrentSceneColor,
                            recoveredSceneMV,
                            recoveredPrimarySceneDepth);
                    if (!mainReady)
                    {
                        compositorFailure =
                            "exact Endminf VFXBaseV2 peak pre-M29 cohort failed " +
                            "closed: " +
                            EndfieldRecoveredEndminfVFXBaseV2PeakCohortRuntime
                                .Failure;
                    }
                }
                if (mainReady && exactEndminfM30Prepared)
                {
                    mainReady = EndfieldRecoveredEndminfM30ExactRuntime.Render(
                        context,
                        camera,
                        recoveredCurrentSceneColor,
                        recoveredSceneMV,
                        recoveredPrimarySceneDepth);
                    if (!mainReady)
                    {
                        compositorFailure =
                            "exact Endminf M30 transport failed closed: " +
                            EndfieldRecoveredEndminfM30ExactRuntime.Failure;
                    }
                }
                if (mainReady)
                {
                    EndfieldRecoveredSceneColorHandle queue3000Color;
                    int queue3000OutputIdentifier =
                        recoveredCurrentSceneColor.identifier ==
                            EndfieldRecoveredSceneMVCompositor.PingColorId
                            ? CameraColorId
                            : EndfieldRecoveredSceneMVCompositor.PingColorId;
                    mainReady = recoveredSceneMVCompositor
                        .CompositeMainTransparentQueue3000(
                            context,
                            camera,
                            cullingResults,
                            recoveredCurrentSceneColor,
                            queue3000OutputIdentifier,
                            recoveredSceneMV,
                            recoveredPrimarySceneDepth,
                            recoveredPrimarySceneDepthFormat,
                            ordinaryTransparentLayerMask,
                            asset.dynamicBatching,
                            asset.gpuInstancing,
                            recoveredPreTransparentSceneColorReady,
                            new RenderTargetIdentifier(
                                RecoveredRefractionSceneColorId),
                            out queue3000Color,
                            out compositorFailure);
                    if (mainReady)
                        recoveredCurrentSceneColor = queue3000Color;
                }
                // M29 shares queue 3000 with the live transparent cohort. The
                // old capture does not preserve equal-queue chronology, so
                // replay it after the surviving live cohort and before the
                // existing exact M14 replacement until drawOrdinal evidence
                // closes their retail order.
                if (mainReady && exactEndminfM29Prepared)
                {
                    mainReady = EndfieldRecoveredEndminfM29ExactRuntime.Render(
                        context,
                        camera,
                        recoveredCurrentSceneColor,
                        recoveredSceneMV,
                        recoveredPrimarySceneDepth);
                    if (!mainReady)
                    {
                        compositorFailure =
                            "exact Endminf M29 transport failed closed: " +
                            EndfieldRecoveredEndminfM29ExactRuntime.Failure;
                    }
                }
                if (mainReady && exactEndminfM31PeakPrepared)
                {
                    mainReady =
                        EndfieldRecoveredEndminfM31PeakExactRuntime.RenderSecond(
                            context,
                            camera,
                            recoveredCurrentSceneColor,
                            recoveredSceneMV,
                            recoveredPrimarySceneDepth);
                    if (!mainReady)
                    {
                        compositorFailure =
                            "exact Endminf M31 second split transport failed " +
                            "closed: " +
                            EndfieldRecoveredEndminfM31PeakExactRuntime.Failure;
                    }
                }
                if (!mainReady && exactEndminfM31PeakPrepared &&
                    EndfieldRecoveredEndminfM31PeakExactRuntime
                        .HasPendingSchedule)
                {
                    EndfieldRecoveredEndminfM31PeakExactRuntime
                        .AbortPendingSchedule(
                        "the retail M31/M29/M30 owner interval failed");
                }
                if (mainReady && exactEndminfVFXBaseV2PeakPrepared)
                {
                    mainReady = EndfieldRecoveredEndminfVFXBaseV2PeakCohortRuntime
                        .RenderPostM29(
                            context,
                            camera,
                            recoveredCurrentSceneColor,
                            recoveredSceneMV,
                            recoveredPrimarySceneDepth);
                    if (!mainReady)
                    {
                        compositorFailure =
                            "exact Endminf VFXBaseV2 peak post-M29 cohort failed " +
                            "closed: " +
                            EndfieldRecoveredEndminfVFXBaseV2PeakCohortRuntime
                                .Failure;
                    }
                }
                if (mainReady && exactEndminfM14Prepared)
                {
                    mainReady = EndfieldRecoveredEndminfM14ExactRuntime.Render(
                        context,
                        camera,
                        recoveredCurrentSceneColor,
                        recoveredSceneMV,
                        recoveredPrimarySceneDepth);
                    if (!mainReady)
                    {
                        compositorFailure =
                            "exact Endminf M14 transport failed closed: " +
                            EndfieldRecoveredEndminfM14ExactRuntime.Failure;
                    }
                }
                if (mainReady && exactEndminfOpeningStripPrepared)
                {
                    mainReady =
                        EndfieldRecoveredEndminfOpeningStripExactRuntime.Render(
                            context,
                            camera,
                            recoveredCurrentSceneColor,
                            recoveredSceneMV,
                            recoveredPrimarySceneDepth);
                    if (!mainReady)
                    {
                        compositorFailure =
                            "exact Endminf opening-strip transport failed closed: " +
                            EndfieldRecoveredEndminfOpeningStripExactRuntime.Failure;
                    }
                }
                // Full frame 2775 records the M21 stone shell at ordinal 74,
                // immediately before the exact M13 ring at ordinal 75.
                if (mainReady && exactEndminfM21PeakPrepared)
                {
                    mainReady = EndfieldRecoveredEndminfM21PeakExactRuntime.Render(
                        context,
                        camera,
                        recoveredCurrentSceneColor,
                        recoveredPrimarySceneDepth);
                    if (!mainReady)
                    {
                        compositorFailure =
                            "exact Endminf M21 peak transport failed closed: " +
                            EndfieldRecoveredEndminfM21PeakExactRuntime.Failure;
                    }
                }
                if (mainReady && exactEndminfM13Prepared)
                {
                    mainReady = EndfieldRecoveredEndminfM13ExactRuntime.Render(
                        context,
                        camera,
                        recoveredCurrentSceneColor,
                        recoveredSceneMV);
                    if (!mainReady)
                    {
                        compositorFailure =
                            "exact Endminf M13 transport failed closed: " +
                            EndfieldRecoveredEndminfM13ExactRuntime.Failure;
                    }
                }
                // Retail frame 1748 records the 36-index M20 gas plume after
                // the M21 stone shell and adjacent M13 peak owner. Its live
                // program writes SceneColor plus SceneMV and samples the
                // current scene depth with the captured runtime atlas.
                if (mainReady && exactEndminfM20PeakPrepared)
                {
                    mainReady = EndfieldRecoveredEndminfM20PeakExactRuntime.Render(
                        context,
                        camera,
                        recoveredCurrentSceneColor,
                        recoveredSceneMV,
                        recoveredPrimarySceneDepth);
                    if (!mainReady)
                    {
                        compositorFailure =
                            "exact Endminf M20 peak transport failed closed: " +
                            EndfieldRecoveredEndminfM20PeakExactRuntime.Failure;
                    }
                }
                // Full frame 2775 records the broad M18 diffusion shell at
                // ordinal 82, after the M21/M13 peak owners and intervening
                // live queue-3000 draws.
                if (mainReady && exactEndminfM18PeakPrepared)
                {
                    mainReady = EndfieldRecoveredEndminfM18PeakExactRuntime.Render(
                        context,
                        camera,
                        recoveredCurrentSceneColor,
                        recoveredPrimarySceneDepth);
                    if (!mainReady)
                    {
                        compositorFailure =
                            "exact Endminf M18 peak transport failed closed: " +
                            EndfieldRecoveredEndminfM18PeakExactRuntime.Failure;
                    }
                }
                // Retained frame 1977 places the third M31 owner immediately
                // after exact M18 (ordinal 88 -> 89). Packet 7 remains
                // fail-closed until the corrected observer validates the
                // SceneColor version at all three schedule boundaries.
                if (mainReady && exactEndminfM31PeakPrepared &&
                    EndfieldRecoveredEndminfM31PeakExactRuntime
                        .HasPendingSchedule)
                {
                    mainReady = EndfieldRecoveredEndminfM31PeakExactRuntime
                        .RenderAfterM18BeforeQueue3001(
                            context,
                            camera,
                            recoveredCurrentSceneColor,
                            recoveredSceneMV,
                            recoveredPrimarySceneDepth);
                    if (!mainReady)
                    {
                        compositorFailure =
                            "exact Endminf M31 post-M18 transport failed " +
                            "closed: " +
                            EndfieldRecoveredEndminfM31PeakExactRuntime.Failure;
                    }
                }
                if (!mainReady && exactEndminfM31PeakPrepared &&
                    EndfieldRecoveredEndminfM31PeakExactRuntime
                        .HasPendingSchedule)
                {
                    EndfieldRecoveredEndminfM31PeakExactRuntime
                        .AbortPendingSchedule(
                            "the retail M31 post-M18 owner interval failed");
                }
                if (mainReady && recoveredSceneMVRequest.hasGlow902Queue3005)
                {
                    DrawRenderers(
                        context,
                        camera,
                        cullingResults,
                        new RenderQueueRange(3001, 3004),
                        SortingCriteria.CommonTransparent |
                            SortingCriteria.RendererPriority,
                        ordinaryTransparentLayerMask,
                        TransparentShaderPasses);
                    EndfieldRecoveredSceneColorHandle glow902Color;
                    int glow902OutputIdentifier =
                        recoveredCurrentSceneColor.identifier ==
                            EndfieldRecoveredSceneMVCompositor.PingColorId
                            ? CameraColorId
                            : EndfieldRecoveredSceneMVCompositor.PingColorId;
                    bool glow902Ready =
                        recoveredSceneMVCompositor.CompositeGlow902Queue3005(
                            context,
                            camera,
                            cullingResults,
                            recoveredCurrentSceneColor,
                            glow902OutputIdentifier,
                            recoveredSceneMV,
                            recoveredPrimarySceneDepth,
                            recoveredPrimarySceneDepthFormat,
                            ordinaryTransparentLayerMask,
                            asset.dynamicBatching,
                            asset.gpuInstancing,
                            recoveredPreTransparentSceneColorReady,
                            new RenderTargetIdentifier(
                                RecoveredRefractionSceneColorId),
                            out glow902Color,
                            out compositorFailure);
                    if (glow902Ready)
                        recoveredCurrentSceneColor = glow902Color;
                    else
                        mainReady = false;
                }
                if (mainReady && recoveredSceneMVRequest.hasDistortion)
                {
                    EndfieldRecoveredSceneColorHandle distortionColor;
                    int distortionOutputIdentifier =
                        recoveredCurrentSceneColor.identifier ==
                            EndfieldRecoveredSceneMVCompositor.PingColorId
                            ? CameraColorId
                            : EndfieldRecoveredSceneMVCompositor.PingColorId;
                    bool distortionReady = recoveredSceneMVCompositor.CompositeDistortion(
                        context,
                        camera,
                        cullingResults,
                        recoveredCurrentSceneColor,
                        distortionOutputIdentifier,
                        false,
                        recoveredSceneMV,
                        recoveredPrimarySceneDepth,
                        recoveredPrimarySceneDepthFormat,
                        ordinaryTransparentLayerMask,
                        asset.dynamicBatching,
                        asset.gpuInstancing,
                        recoveredPreTransparentSceneColorReady,
                        new RenderTargetIdentifier(RecoveredRefractionSceneColorId),
                        out distortionColor,
                        out compositorFailure);
                    if (distortionReady)
                        recoveredCurrentSceneColor = distortionColor;
                    else
                        mainReady = false;
                }
                // Full frame 2775 records M28 at ordinal 87, after the broad
                // M18 shell and the surviving queue-3005/distortion cohort.
                // Its t2 SceneColor SRV is a persistent snapshot, so the exact
                // draw can write the current SceneColor/SceneMV MRTs in place.
                if (mainReady && exactEndminfM28PeakPrepared)
                {
                    mainReady = recoveredEndminfM28PeakExactRuntime.Render(
                        context,
                        camera,
                        recoveredCurrentSceneColor,
                        recoveredSceneMV,
                        recoveredPrimarySceneDepth);
                    if (!mainReady)
                    {
                        compositorFailure =
                            "exact Endminf M28 peak transport failed closed: " +
                            recoveredEndminfM28PeakExactRuntime.Failure;
                    }
                }
                if (!mainReady)
                {
                    commandBuffer = new CommandBuffer
                    {
                        name = "Restore fail-closed scene color after MRT compositor failure"
                    };
                    if (recoveredCurrentSceneColor.identifier != CameraColorId)
                    {
                        commandBuffer.Blit(
                            recoveredCurrentSceneColor.Target,
                            CameraColorId);
                    }
                    commandBuffer.SetRenderTarget(
                        new RenderTargetIdentifier(CameraColorId),
                        recoveredPrimarySceneDepth);
                    context.ExecuteCommandBuffer(commandBuffer);
                    commandBuffer.Release();
                    recoveredCurrentSceneColor = new EndfieldRecoveredSceneColorHandle(
                        CameraColorId,
                        cameraColorDescriptor);
                    useRecoveredSceneMV = false;
                    if (!loggedRecoveredSceneMVFailure)
                    {
                        Debug.LogWarning(
                            "Recovered sceneMV transparent compositor failed closed: " +
                            compositorFailure);
                        loggedRecoveredSceneMVFailure = true;
                    }
                    DrawRenderers(
                        context,
                        camera,
                        cullingResults,
                        new RenderQueueRange(3000, 5000),
                        SortingCriteria.CommonTransparent | SortingCriteria.RendererPriority,
                        ordinaryTransparentLayerMask,
                        TransparentShaderPasses);
                }

                if (useRecoveredSceneMV)
                {
                    if (recoveredSceneMVRequest.hasGlow902Queue3005)
                    {
                        DrawRenderers(
                            context,
                            camera,
                            cullingResults,
                            new RenderQueueRange(3006, 3659),
                            SortingCriteria.CommonTransparent |
                                SortingCriteria.RendererPriority,
                            ordinaryTransparentLayerMask,
                            TransparentShaderPasses);
                    }
                    else
                    {
                        DrawRenderers(
                            context,
                            camera,
                            cullingResults,
                            new RenderQueueRange(3001, 3659),
                            SortingCriteria.CommonTransparent |
                                SortingCriteria.RendererPriority,
                            ordinaryTransparentLayerMask,
                            TransparentShaderPasses);
                    }
                    DrawRenderers(
                        context,
                        camera,
                        cullingResults,
                        new RenderQueueRange(3741, 5000),
                        SortingCriteria.CommonTransparent | SortingCriteria.RendererPriority,
                        ordinaryTransparentLayerMask,
                        TransparentShaderPasses);
                }
            }
            else
            {
                DrawRenderers(
                    context,
                    camera,
                    cullingResults,
                    RenderQueueRange.transparent,
                    SortingCriteria.CommonTransparent | SortingCriteria.RendererPriority,
                    ordinaryTransparentLayerMask,
                    TransparentShaderPasses);
            }
            DrawRecoveredEndminfShadowPlane(
                context,
                recoveredCurrentSceneColor.Target,
                recoveredPrimarySceneDepth);
            if (useRecoveredSceneMV &&
                recoveredCurrentSceneColor.identifier != CameraColorId)
            {
                // CompositeMainTransparent alternates into PingColor. The
                // recovered bloom and Uber graph below still reads the
                // canonical CameraColor allocation, so publish the exact
                // current HDR scene before post. Both allocations share the
                // same descriptor; CopyTexture preserves the value without an
                // unintended filter, conversion, or shader pass.
                commandBuffer = new CommandBuffer
                {
                    name = "Publish recovered MRT scene color for post"
                };
                commandBuffer.CopyTexture(
                    recoveredCurrentSceneColor.Target,
                    new RenderTargetIdentifier(CameraColorId));
                commandBuffer.SetRenderTarget(
                    new RenderTargetIdentifier(CameraColorId),
                    recoveredPrimarySceneDepth);
                context.ExecuteCommandBuffer(commandBuffer);
                commandBuffer.Release();
                recoveredCurrentSceneColor =
                    new EndfieldRecoveredSceneColorHandle(
                        CameraColorId,
                        cameraColorDescriptor);
            }
            if (recoveredPreTransparentSceneColorReady)
            {
                commandBuffer = new CommandBuffer
                {
                    name = "Release recovered pre-transparent scene color"
                };
                commandBuffer.SetGlobalTexture(
                    SceneColorTextureId,
                    Texture2D.blackTexture);
                commandBuffer.ReleaseTemporaryRT(RecoveredRefractionSceneColorId);
                context.ExecuteCommandBuffer(commandBuffer);
                commandBuffer.Release();
            }
            if (applyPostProcess)
            {
                ApplyRecoveredEndminfOpeningStripCompatibilityBeforeTemporal(
                    context,
                    camera,
                    useRecoveredPostSemantics,
                    cameraColorDescriptor,
                    useRecoveredSceneMV ? recoveredSceneMV : null);
                EndfieldRecoveredPostStageDiagnostic
                    .CaptureBeforeTemporalIfArmed(
                        context,
                        camera,
                        new RenderTargetIdentifier(CameraColorId),
                        cameraColorDescriptor);
                EndfieldRecoveredPrePostHdrDiagnostic.CaptureIfArmed(
                    context,
                    camera,
                    new RenderTargetIdentifier(CameraColorId),
                    cameraColorDescriptor);
            }
            recoveredScreenDirectAudit.EndForward(
                context,
                camera,
                canonicalForwardDepthBits,
                useRecoveredSceneMV
                    ? recoveredCurrentSceneColor.Target
                    : canonicalColorTarget,
                preGBufferFrame,
                characterShadowFrame);
            recoveredScreenShadowMaskDiagnostic.ResetConsumerState(context);
            recoveredScreenShadowMaskProducer.ResetAfterForward(context);
            recoveredVisibilitySHProducer.ResetAfterForward(context);
            recoveredLowResDirectionalShadowProducer.ResetAfterForward(
                context);
            recoveredContactShadowProducer.ResetAfterForward(context);
            recoveredDirectionalCSMProducer.ResetAfterForward(context);

            EndfieldRecoveredSceneColorHandle recoveredDeferredPostColor = default;
            bool recoveredDeferredLinearUnorm = false;
            if (applyPostProcess)
            {
                ApplyCharacterPostProcess(
                    context,
                    camera,
                    cullingResults,
                    useRecoveredPostSemantics,
                    liveAutoExposureState,
                    useRecoveredPostUberWorldUi,
                    recoveredPrimarySceneDepth,
                    useRecoveredSceneMV,
                    recoveredSceneMV,
                    cameraColorDescriptor,
                    out recoveredDeferredPostColor,
                    out recoveredDeferredLinearUnorm);
            }

            bool recoveredAfterPostColorAllocated = false;
            if (useRecoveredSceneMV)
            {
                string afterPostFailure;
                EndfieldRecoveredSceneColorHandle recoveredAfterPostColor;
                bool afterPostReady = recoveredSceneMVCompositor.CompositeAfterPost(
                    context,
                    camera,
                    cullingResults,
                    recoveredDeferredPostColor,
                    EndfieldRecoveredSceneMVCompositor.AfterPostColorId,
                    recoveredSceneMV,
                    recoveredPrimarySceneDepth,
                    recoveredPrimarySceneDepthFormat,
                    camera.cullingMask,
                    asset.dynamicBatching,
                    asset.gpuInstancing,
                    out recoveredAfterPostColor,
                    out afterPostFailure);
                recoveredAfterPostColorAllocated = true;
                if (afterPostReady)
                {
                    commandBuffer = new CommandBuffer
                    {
                        name = "Present recovered post/after-post scene color"
                    };
                    if (recoveredDeferredLinearUnorm)
                    {
                        commandBuffer.CopyTexture(
                            recoveredAfterPostColor.Target,
                            new RenderTargetIdentifier(camera.targetTexture));
                    }
                    else
                    {
                        PresentToCameraTarget(
                            commandBuffer,
                            recoveredAfterPostColor.Target,
                            camera);
                    }
                    context.ExecuteCommandBuffer(commandBuffer);
                    commandBuffer.Release();

                    if (!loggedRecoveredSceneMV)
                    {
                        Debug.Log(
                            "Recovered sceneMV compositor active: exact A2B10G10R10 current-frame " +
                            "target, one neutral opaque clear, ForwardOnly/Distortion/after-post " +
                            "old-scene copy and handle handoff. Main ForwardOnly precedes Distortion " +
                            "in the source-closed current retail total order.");
                        loggedRecoveredSceneMV = true;
                    }
                }
                else
                {
                    commandBuffer = new CommandBuffer
                    {
                        name = "Present fail-closed recovered post color"
                    };
                    if (recoveredDeferredLinearUnorm)
                    {
                        commandBuffer.CopyTexture(
                            recoveredDeferredPostColor.Target,
                            new RenderTargetIdentifier(camera.targetTexture));
                    }
                    else
                    {
                        PresentToCameraTarget(
                            commandBuffer,
                            recoveredDeferredPostColor.Target,
                            camera);
                    }
                    context.ExecuteCommandBuffer(commandBuffer);
                    commandBuffer.Release();
                    if (!loggedRecoveredSceneMVFailure)
                    {
                        Debug.LogWarning(
                            "Recovered sceneMV after-post compositor failed closed: " +
                            afterPostFailure);
                        loggedRecoveredSceneMVFailure = true;
                    }
                }
            }

            if (useRecoveredCameraDepth)
            {
                commandBuffer = new CommandBuffer
                {
                    name = "Release recovered CharInfo camera depth"
                };
                commandBuffer.SetGlobalFloat(RecoveredCameraDepthReadyId, 0.0f);
                commandBuffer.SetGlobalTexture(
                    RecoveredCameraDepthTextureId,
                    Texture2D.blackTexture);
                if (physicalRecoveredCameraDepth == null)
                {
                    commandBuffer.ReleaseTemporaryRT(
                        RecoveredCameraDepthTextureId);
                }
                context.ExecuteCommandBuffer(commandBuffer);
                commandBuffer.Release();
            }

            if (characterShadowFrame.temporaryRtAllocated)
            {
                commandBuffer = new CommandBuffer
                {
                    name = "Unpublish and release HGCompat Character Shadow"
                };
                // Retail HGRenderGraph.ReadShadowResult registers the character
                // atlas as a read in every consuming pass. The graph compiler
                // releases its pooled texture only after max(latest read,
                // latest write). End this compatibility publication in the same
                // order: neutralize all global carriers before returning the
                // temporary depth texture to Unity's pool.
                SetCharacterShadowUnavailableGlobals(commandBuffer);
                commandBuffer.ReleaseTemporaryRT(CharacterShadowMapId);
                context.ExecuteCommandBuffer(commandBuffer);
                commandBuffer.Release();
            }
            if (recoveredSceneColorPingAllocated ||
                useRecoveredSceneMV ||
                recoveredAfterPostColorAllocated)
            {
                commandBuffer = new CommandBuffer
                {
                    name = "Release recovered sceneMV scene-color chain"
                };
                commandBuffer.SetGlobalFloat(
                    EndfieldRecoveredSceneMVCompositor.SceneMVMRTReadyId,
                    0.0f);
                commandBuffer.SetGlobalFloat(
                    EndfieldRecoveredSceneMVCompositor.VFXGlobalsReadyId,
                    0.0f);
                commandBuffer.SetGlobalTexture(SceneColorTextureId, Texture2D.blackTexture);
                commandBuffer.SetGlobalTexture(SceneDepthId, Texture2D.blackTexture);
                commandBuffer.SetGlobalTexture(CameraDepthTextureId, Texture2D.blackTexture);
                commandBuffer.SetGlobalFloat(RecoveredVFXSoftDepthReadyId, 0.0f);
                if (recoveredSceneColorPingAllocated)
                {
                    commandBuffer.ReleaseTemporaryRT(
                        EndfieldRecoveredSceneMVCompositor.PingColorId);
                }
                if (useRecoveredSceneMV)
                {
                    commandBuffer.ReleaseTemporaryRT(CameraColorId);
                    commandBuffer.ReleaseTemporaryRT(
                        EndfieldRecoveredSceneMVCompositor.PostColorId);
                }
                if (recoveredAfterPostColorAllocated)
                {
                    commandBuffer.ReleaseTemporaryRT(
                        EndfieldRecoveredSceneMVCompositor.AfterPostColorId);
                }
                context.ExecuteCommandBuffer(commandBuffer);
                commandBuffer.Release();
            }
            // The canonical CharacterPrePass and Forward lists leave the
            // separately owned CameraDepthStencil bound. D3D11 rejects a
            // RenderTexture.Release while that texture is still the active
            // depth surface; repeated viewer captures then exhaust the
            // deferred-destroy cohort and later allocations report
            // GraphicsFormat.None. Return ownership to the camera target and
            // submit that unbind before releasing the explicit depth object.
            if (recoveredPrimarySceneDepth != null)
            {
                commandBuffer = new CommandBuffer
                {
                    name = "Unbind recovered primary scene depth"
                };
                commandBuffer.SetRenderTarget(
                    BuiltinRenderTextureType.CameraTarget);
                context.ExecuteCommandBuffer(commandBuffer);
                commandBuffer.Release();
            }
            context.Submit();
            recoveredSceneMVCompositor.FinalizeRendererIdSidecarAfterSubmit();
            EndfieldRecoveredSceneMVCompositor.ReleaseRenderTexture(
                recoveredSceneMV);
            ReleaseRecoveredPrimarySceneDepth(recoveredPrimarySceneDepth);
            recoveredScreenShadowMaskDiagnostic.FinalizeConsumerKeywordAfterSubmit();
            recoveredScreenDirectAudit.FinalizeKeywordAfterSubmit();
        }

        internal static bool TryValidateRecoveredSceneColorFormat(
            out string failure)
        {
            if (!SystemInfo.IsFormatSupported(
                    RecoveredSceneColorFormat,
                    FormatUsage.Render))
            {
                failure =
                    $"{RecoveredSceneColorFormat} is not supported for rendering";
                return false;
            }
            // Unity 2022.3 reports FormatUsage.Sample=false for D3D12
            // B10G11R11 even though the corresponding RGB111110Float
            // RenderTexture capability is present and live shader sampling is
            // valid (covered by the D3D12 validator). Use Unity's dedicated
            // render-texture capability for this exact packed format.
            if (!SystemInfo.SupportsRenderTextureFormat(
                    RenderTextureFormat.RGB111110Float))
            {
                failure =
                    "RGB111110Float render-texture capability is unavailable";
                return false;
            }
            failure = string.Empty;
            return true;
        }

        private static RenderTextureDescriptor
            CreateRecoveredSceneColorDescriptor(
                int width,
                int height,
                int depthBufferBits)
        {
            return new RenderTextureDescriptor(
                Mathf.Max(width, 1),
                Mathf.Max(height, 1),
                RecoveredSceneColorFormat,
                depthBufferBits)
            {
                msaaSamples = 1,
                sRGB = false
            };
        }

        private bool PrepareRecoveredPreTransparentSceneColor(
            ScriptableRenderContext context,
            Camera camera,
            int width,
            int height,
            RenderTargetIdentifier canonicalColorTarget,
            RenderTextureDescriptor canonicalSceneColorDescriptor,
            bool applyPostProcess,
            bool useRecoveredPostUberWorldUi,
            RenderTexture recoveredPrimarySceneDepth)
        {
            Renderer[] renderers = Object.FindObjectsOfType<Renderer>();
            bool activeSourceConsumer = false;
            for (int rendererIndex = 0;
                 rendererIndex < renderers.Length && !activeSourceConsumer;
                 rendererIndex++)
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
                for (int materialIndex = 0;
                     materialIndex < materials.Length;
                     materialIndex++)
                {
                    Material material = materials[materialIndex];
                    if (material == null || material.shader == null)
                        continue;

                    bool recoveredRefractionConsumer =
                        material.shader.name == "Endfield/Recovered/VFXRefract";
                    bool recoveredOverlayHairSuppressionConsumer =
                        material.shader.name ==
                            "Endfield/Recovered/CharacterOverlayShadow" &&
                        material.HasProperty("_DisableDrawUnderHair") &&
                        material.GetFloat("_DisableDrawUnderHair") <= 0.5f;
                    if (recoveredRefractionConsumer ||
                        recoveredOverlayHairSuppressionConsumer)
                    {
                        activeSourceConsumer = true;
                        break;
                    }
                }
            }
            if (!activeSourceConsumer)
                return false;

            if (!TryValidateRecoveredSceneColorFormat(
                    out string formatFailure))
            {
                if (!loggedRecoveredPreTransparentSceneColorFormatFailure)
                {
                    Debug.LogWarning(
                        "Recovered pre-transparent scene-color copy failed " +
                        $"closed for camera '{camera.name}': {formatFailure}. " +
                        "The pipeline will not substitute Unity DefaultHDR.");
                    loggedRecoveredPreTransparentSceneColorFormatFailure = true;
                }
                return false;
            }
            RenderTextureDescriptor descriptor = applyPostProcess
                ? canonicalSceneColorDescriptor
                : CreateRecoveredSceneColorDescriptor(width, height, 0);
            // The refraction/overlay copy is color-only but otherwise clones
            // canonical sceneColor. Recovered sceneMV ping and AfterDOF targets
            // retain the same descriptor through EndfieldRecoveredSceneColorHandle.
            descriptor.depthBufferBits = 0;
            descriptor.depthStencilFormat = GraphicsFormat.None;
            var commandBuffer = new CommandBuffer
            {
                name = "Recovered pre-transparent opaque-scene copy"
            };
            commandBuffer.GetTemporaryRT(
                RecoveredRefractionSceneColorId,
                descriptor,
                FilterMode.Bilinear);
            commandBuffer.Blit(
                canonicalColorTarget,
                new RenderTargetIdentifier(RecoveredRefractionSceneColorId));
            commandBuffer.SetGlobalTexture(
                SceneColorTextureId,
                new RenderTargetIdentifier(RecoveredRefractionSceneColorId));
            if (applyPostProcess)
            {
                if (useRecoveredPostUberWorldUi)
                {
                    commandBuffer.SetRenderTarget(
                        canonicalColorTarget,
                        new RenderTargetIdentifier(recoveredPrimarySceneDepth));
                }
                else
                {
                    commandBuffer.SetRenderTarget(canonicalColorTarget);
                }
            }
            else
            {
                commandBuffer.SetRenderTarget(canonicalColorTarget);
            }
            context.ExecuteCommandBuffer(commandBuffer);
            commandBuffer.Release();
            return true;
        }

        private static bool TryPrepareRecoveredPostUberWorldUi(
            Camera camera,
            int width,
            int height,
            bool applyPostProcess,
            bool useRecoveredPostSemantics,
            out bool requested,
            out RenderTexture primarySceneDepth,
            out GraphicsFormat primarySceneDepthFormat,
            out string failure)
        {
            requested = false;
            primarySceneDepth = null;
            primarySceneDepthFormat = GraphicsFormat.None;
            failure = "the source portrait selector is disabled";

            EndfieldRecoveredCharInfoBackgroundPortrait[] portraits =
                Object.FindObjectsOfType<EndfieldRecoveredCharInfoBackgroundPortrait>();
            bool foundExactActivePortrait = false;
            for (int i = 0; i < portraits.Length; i++)
            {
                EndfieldRecoveredCharInfoBackgroundPortrait portrait = portraits[i];
                if (portrait == null || !portrait.RecoveredPortraitRequested)
                    continue;

                requested = true;
                Renderer renderer = portrait.portraitRenderer != null
                    ? portrait.portraitRenderer
                    : portrait.GetComponent<Renderer>();
                if (!portrait.enabled ||
                    !portrait.gameObject.activeInHierarchy ||
                    renderer == null ||
                    !renderer.enabled ||
                    renderer.gameObject.layer !=
                        EndfieldRecoveredCharInfoBackgroundPortrait.SourceUiLayer)
                {
                    continue;
                }

                Material[] materials = renderer.sharedMaterials;
                for (int materialIndex = 0;
                     materialIndex < materials.Length;
                     materialIndex++)
                {
                    Material material = materials[materialIndex];
                    if (material == null ||
                        material.shader == null ||
                        material.shader.name !=
                            EndfieldRecoveredCharInfoBackgroundPortrait.ShaderName ||
                        material.renderQueue <= (int)RenderQueue.GeometryLast)
                    {
                        continue;
                    }
                    foundExactActivePortrait = true;
                    break;
                }
            }

            if (!requested)
                return false;
            if (!foundExactActivePortrait)
            {
                failure =
                    "no active layer-16 renderer has the exact recovered portrait shader and " +
                    "transparent queue";
                return false;
            }
            if (!applyPostProcess)
            {
                failure = "the HGCompat fullscreen post is unavailable";
                return false;
            }
            if (!useRecoveredPostSemantics)
            {
                failure = "the recovered post-semantics selector is disabled";
                return false;
            }
            if ((camera.cullingMask &
                 (1 << EndfieldRecoveredCharInfoBackgroundPortrait.SourceUiLayer)) == 0)
            {
                failure = "the camera culling mask excludes source world-UI layer 16";
                return false;
            }

            return TryCreateRecoveredPrimarySceneDepth(
                width,
                height,
                out primarySceneDepth,
                out primarySceneDepthFormat,
                out failure);
        }

        private static bool TryCreateRecoveredPrimarySceneDepth(
            int width,
            int height,
            out RenderTexture primarySceneDepth,
            out GraphicsFormat selectedFormat,
            out string failure)
        {
            primarySceneDepth = null;
            selectedFormat = GraphicsFormat.None;
            failure = "no supported stencil-bearing depth render format is available";

            GraphicsFormat[] sourceOrderedFormats =
            {
                GraphicsFormat.D32_SFloat_S8_UInt,
                GraphicsFormat.D24_UNorm_S8_UInt
            };
            for (int i = 0; i < sourceOrderedFormats.Length; i++)
            {
                GraphicsFormat candidate = sourceOrderedFormats[i];
                // Combined depth/stencil formats report FormatUsage.Sample=false
                // on D3D12 even when Unity can create the RawDepth depth-plane
                // SRV used by a shader. Render support, exact retained format,
                // and ShadowSamplingMode.RawDepth are the applicable contract.
                if (!SystemInfo.IsFormatSupported(candidate, FormatUsage.Render))
                {
                    continue;
                }
                selectedFormat = candidate;
                break;
            }
            if (selectedFormat == GraphicsFormat.None)
                return false;

            var descriptor = new RenderTextureDescriptor(width, height)
            {
                graphicsFormat = GraphicsFormat.None,
                depthBufferBits = 0,
                dimension = TextureDimension.Tex2D,
                volumeDepth = 1,
                msaaSamples = 1,
                bindMS = false,
                useMipMap = false,
                autoGenerateMips = false,
                enableRandomWrite = false,
                sRGB = false,
                shadowSamplingMode = ShadowSamplingMode.RawDepth,
                useDynamicScale = false
            };
            descriptor.depthStencilFormat = selectedFormat;
            primarySceneDepth = new RenderTexture(descriptor)
            {
                name = "CameraDepthStencil",
                filterMode = FilterMode.Point,
                wrapMode = TextureWrapMode.Clamp,
                anisoLevel = 0,
                hideFlags = HideFlags.HideAndDontSave
            };
            if (!primarySceneDepth.Create() ||
                !primarySceneDepth.IsCreated() ||
                primarySceneDepth.depthStencilFormat != selectedFormat)
            {
                GraphicsFormat actualFormat = primarySceneDepth.depthStencilFormat;
                ReleaseRecoveredPrimarySceneDepth(primarySceneDepth);
                primarySceneDepth = null;
                failure =
                    $"the {width}x{height} primary depth/stencil could not retain " +
                    $"{selectedFormat} (actual {actualFormat})";
                return false;
            }
            return true;
        }

        private static void ReleaseRecoveredPrimarySceneDepth(RenderTexture texture)
        {
            if (texture == null)
                return;
            if (texture.IsCreated())
                texture.Release();
#if UNITY_EDITOR
            // Editor validation drives many explicit Camera.Render calls
            // before the next player-loop destruction sweep. Every GPU use of
            // this transient owner has already been submitted and explicitly
            // unbound above, so do not accumulate deferred-destroy instances.
            Object.DestroyImmediate(texture);
#else
            Object.Destroy(texture);
#endif
        }

        private RenderTexture EnsureRecoveredExactCameraDepth(
            RenderTextureDescriptor descriptor)
        {
            if (recoveredExactCameraDepth != null &&
                recoveredExactCameraDepth.IsCreated() &&
                recoveredExactCameraDepth.width == descriptor.width &&
                recoveredExactCameraDepth.height == descriptor.height &&
                recoveredExactCameraDepth.graphicsFormat ==
                    descriptor.graphicsFormat)
            {
                return recoveredExactCameraDepth;
            }
            ReleaseRecoveredPrimarySceneDepth(recoveredExactCameraDepth);
            recoveredExactCameraDepth = new RenderTexture(descriptor)
            {
                name = "Recovered exact-consumer camera depth",
                filterMode = FilterMode.Bilinear,
                wrapMode = TextureWrapMode.Repeat,
                hideFlags = HideFlags.HideAndDontSave
            };
            if (!recoveredExactCameraDepth.Create())
            {
                ReleaseRecoveredPrimarySceneDepth(
                    recoveredExactCameraDepth);
                recoveredExactCameraDepth = null;
                throw new System.InvalidOperationException(
                    "Could not allocate the exact-consumer camera depth texture.");
            }
            return recoveredExactCameraDepth;
        }

        private static void RenderRecoveredCameraDepth(
            ScriptableRenderContext context,
            Camera camera,
            int width,
            int height,
            RenderTargetIdentifier cameraDepthTarget)
        {
            CommandBuffer commandBuffer = new CommandBuffer
            {
                name = "Recovered CharInfo camera depth prepass"
            };
            commandBuffer.SetRenderTarget(
                cameraDepthTarget,
                new RenderTargetIdentifier(CameraColorId));
            float farDepth = SystemInfo.usesReversedZBuffer ? 0.0f : 1.0f;
            commandBuffer.ClearRenderTarget(
                false,
                true,
                new Color(farDepth, farDepth, farDepth, farDepth));
            context.ExecuteCommandBuffer(commandBuffer);
            commandBuffer.Release();

            DrawRecoveredAuxiliaryPasses(context, camera, "CAMERA_DEPTH_COPY");

            commandBuffer = new CommandBuffer
            {
                name = "Bind recovered CharInfo camera depth"
            };
            commandBuffer.SetRenderTarget(CameraColorId);
            commandBuffer.SetGlobalTexture(
                RecoveredCameraDepthTextureId,
                cameraDepthTarget);
            commandBuffer.SetGlobalVector(
                RecoveredCameraDepthTextureTexelSizeId,
                new Vector4(1.0f / width, 1.0f / height, width, height));
            commandBuffer.SetGlobalFloat(RecoveredCameraDepthReadyId, 1.0f);
            context.ExecuteCommandBuffer(commandBuffer);
            commandBuffer.Release();
        }

        private void ApplyCharacterPostProcess(
            ScriptableRenderContext context,
            Camera camera,
            CullingResults cullingResults,
            bool useRecoveredPostSemantics,
            EndfieldRecoveredCharInfoAutoExposureCameraState liveAutoExposureState,
            bool useRecoveredPostUberWorldUi,
            RenderTexture recoveredPrimarySceneDepth,
            bool deferPresentationForSceneMV,
            RenderTexture recoveredSceneMV,
            RenderTextureDescriptor recoveredSceneColorDescriptor,
            out EndfieldRecoveredSceneColorHandle deferredPostColor,
            out bool deferredLinearUnorm)
        {
            deferredPostColor = default;
            deferredLinearUnorm = false;
            LastRecoveredEndminfExactUberRequested =
                recoveredEndminfUberExactRuntime.Requested;
            LastRecoveredEndminfExactUberSubmitted = false;
            LastRecoveredEndminfExactUberValidated = false;
            LastRecoveredEndminfExactUberVariant = string.Empty;
            LastRecoveredEndminfExactUberFailure = string.Empty;
            EndfieldHGOperatorPresentation operatorPresentation =
                camera.GetComponent<EndfieldHGOperatorPresentation>();
            int width = Mathf.Max(camera.pixelWidth, 1);
            int height = Mathf.Max(camera.pixelHeight, 1);
            string finalTargetFailure = "target contract was not evaluated";
            bool useRecoveredLinearUnormFinalTarget =
                recoveredLinearUnormFinalTargetRequested &&
                useRecoveredPostSemantics &&
                TryValidateRecoveredLinearUnormFinalTarget(
                    camera,
                    width,
                    height,
                    out finalTargetFailure);
            if (recoveredLinearUnormFinalTargetRequested &&
                !useRecoveredLinearUnormFinalTarget &&
                !loggedRecoveredLinearUnormFinalTargetFailure)
            {
                if (!useRecoveredPostSemantics)
                    finalTargetFailure = "the recovered CharInfo post-semantics selector is disabled";
                Debug.LogWarning(
                    "Recovered linear-UNorm final target was requested but remains disabled for " +
                    $"camera '{camera.name}': {finalTargetFailure}. The compatibility CameraTarget " +
                    "blit remains active without explicit OETF/dither.");
                loggedRecoveredLinearUnormFinalTargetFailure = true;
            }
            int bloomWidth = Mathf.Max(width / 2, 1);
            int bloomHeight = Mathf.Max(height / 2, 1);

            var characterSourceDescriptor = new RenderTextureDescriptor(
                width,
                height,
                RenderTextureFormat.DefaultHDR,
                0)
            {
                msaaSamples = 1,
                sRGB = false
            };
            var bloomDescriptor = new RenderTextureDescriptor(
                bloomWidth,
                bloomHeight,
                RenderTextureFormat.DefaultHDR,
                0)
            {
                msaaSamples = 1,
                sRGB = false
            };

            CommandBuffer commandBuffer = new CommandBuffer
            {
                name = "HGCompat Character Post"
            };
            int recoveredTemporalPostSourceId = 0;
            bool releaseRecoveredTemporalPostSource = false;
            RenderTextureDescriptor recoveredTemporalPostSourceDescriptor =
                default;
            bool hasRecoveredTemporalPostSource =
                useRecoveredPostSemantics &&
                EnqueueRecoveredEndminfTemporalResolve(
                    commandBuffer,
                    camera,
                    width,
                    height,
                    recoveredPrimarySceneDepth,
                    recoveredSceneMV,
                    out recoveredTemporalPostSourceId,
                    out recoveredTemporalPostSourceDescriptor,
                    out releaseRecoveredTemporalPostSource);
            // The retained retail Uber draw binds full-resolution
            // R16G16B16A16_FLOAT t0 after the packed B10G11R11 sceneColor
            // owner. Preserve that post-handoff promotion for Endminf before
            // bloom and Uber sample the source.
            bool useRecoveredEndminfRgba16PostSource =
                useRecoveredPostSemantics &&
                !hasRecoveredTemporalPostSource &&
                EndfieldEndminfVisualCompatibilityClock.Requested &&
                SystemInfo.IsFormatSupported(
                    GraphicsFormat.R16G16B16A16_SFloat,
                    FormatUsage.Render);
            RenderTargetIdentifier recoveredPostSource =
                hasRecoveredTemporalPostSource
                    ? new RenderTargetIdentifier(
                        recoveredTemporalPostSourceId)
                    : new RenderTargetIdentifier(CameraColorId);
            RenderTextureDescriptor recoveredPostSourceDescriptor =
                hasRecoveredTemporalPostSource
                    ? recoveredTemporalPostSourceDescriptor
                    : recoveredSceneColorDescriptor;
            LastRecoveredEndminfPostSourceGraphicsFormat =
                recoveredPostSourceDescriptor.graphicsFormat;
            if (useRecoveredEndminfRgba16PostSource)
            {
                recoveredPostSourceDescriptor = new RenderTextureDescriptor(
                    width,
                    height)
                {
                    graphicsFormat = GraphicsFormat.R16G16B16A16_SFloat,
                    depthStencilFormat = GraphicsFormat.None,
                    msaaSamples = 1,
                    useMipMap = false,
                    autoGenerateMips = false,
                    sRGB = false
                };
                commandBuffer.GetTemporaryRT(
                    RecoveredEndminfPostSourceId,
                    recoveredPostSourceDescriptor,
                    FilterMode.Bilinear);
                commandBuffer.Blit(
                    CameraColorId,
                    RecoveredEndminfPostSourceId);
                recoveredPostSource = new RenderTargetIdentifier(
                    RecoveredEndminfPostSourceId);
                LastRecoveredEndminfPostSourceGraphicsFormat =
                    recoveredPostSourceDescriptor.graphicsFormat;
            }
            if (useRecoveredPostSemantics)
            {
                // This checkpoint owns the pure temporal/DLAA handoff. Keep it
                // before Endminf's separate opening-strip distortion so the
                // diagnostic name and captured surface have one exact owner.
                EndfieldRecoveredPostStageDiagnostic.EnqueueStageIfActive(
                    commandBuffer,
                    EndfieldRecoveredPostStageDiagnostic.AfterTemporal,
                    recoveredPostSource,
                    recoveredPostSourceDescriptor);
            }
            if (!useRecoveredPostSemantics)
            {
                // Keep the original compatibility path byte-for-byte equivalent:
                // selector 0 still redraws only recovered character surfaces into
                // one half-resolution blur pair.
                commandBuffer.GetTemporaryRT(
                    CharacterBloomSourceId,
                    characterSourceDescriptor,
                    FilterMode.Bilinear);
                commandBuffer.GetTemporaryRT(CharacterBloomAId, bloomDescriptor, FilterMode.Bilinear);
                commandBuffer.GetTemporaryRT(CharacterBloomBId, bloomDescriptor, FilterMode.Bilinear);
                commandBuffer.SetRenderTarget(
                    new RenderTargetIdentifier(CharacterBloomSourceId),
                    new RenderTargetIdentifier(CameraColorId));
                commandBuffer.ClearRenderTarget(false, true, Color.clear);

                Renderer[] renderers = Object.FindObjectsOfType<Renderer>();
                foreach (Renderer renderer in renderers)
                {
                    if (renderer == null || !renderer.enabled || !renderer.gameObject.activeInHierarchy)
                        continue;
                    if ((camera.cullingMask & (1 << renderer.gameObject.layer)) == 0)
                        continue;

                    Material[] materials = renderer.sharedMaterials;
                    for (int submesh = 0; submesh < materials.Length; submesh++)
                    {
                        Material material = materials[submesh];
                        if (material == null || material.shader == null ||
                            !material.shader.name.StartsWith("Endfield/Recovered/"))
                            continue;

                        int forwardPass = material.FindPass("FORWARD");
                        if (forwardPass >= 0)
                            commandBuffer.DrawRenderer(renderer, material, submesh, forwardPass);
                    }
                }
            }

            float bloomThreshold = operatorPresentation != null
                ? operatorPresentation.characterBloomThreshold
                : asset.characterBloomThreshold;
            float bloomSoftness = operatorPresentation != null
                ? operatorPresentation.characterBloomSoftness
                : asset.characterBloomSoftness;
            float bloomIntensity = operatorPresentation != null
                ? operatorPresentation.characterBloomIntensity
                : asset.characterBloomIntensity * asset.characterBloomCompatibilityScale;
            float bloomSerializedScatter = RecoveredBloomSerializedScatter;
            bool useRecoveredGachaRoomPostProfile =
                operatorPresentation != null &&
                operatorPresentation.useRecoveredGachaRoomPostProfile;
            if (useRecoveredPostSemantics)
            {
                // Both source profiles disable the separate character-mask branch.
                // GachaRoom_Volume selects a different general Bloom response from
                // CharInfo, so keep that selection camera-local.
                bloomThreshold = useRecoveredGachaRoomPostProfile
                    ? RecoveredGachaBloomSerializedThreshold
                    : RecoveredBloomSerializedThreshold;
                bloomIntensity = useRecoveredGachaRoomPostProfile
                    ? RecoveredGachaBloomSerializedIntensity
                    : RecoveredBloomSerializedIntensity;
                bloomSerializedScatter = useRecoveredGachaRoomPostProfile
                    ? RecoveredGachaBloomSerializedScatter
                    : RecoveredBloomSerializedScatter;
            }
            float exposureEv = operatorPresentation != null
                ? operatorPresentation.fixedPostExposureEV
                : asset.fixedPostExposureEV;
            float saturation = operatorPresentation != null
                ? operatorPresentation.saturation
                : 1.0f;
            Vector4 vignetteParams = operatorPresentation != null
                ? new Vector4(
                    operatorPresentation.vignetteIntensity,
                    operatorPresentation.vignetteSmoothness,
                    operatorPresentation.vignetteRoundness,
                    (float)width / height)
                : new Vector4(0.0f, 0.41f, 1.0f, (float)width / height);

            postProcessMaterial.SetFloat(BloomThresholdId, bloomThreshold);
            postProcessMaterial.SetFloat(BloomSoftnessId, bloomSoftness);
            int bloomOutputId;
            int recoveredBloomMipCount = 0;
            if (useRecoveredPostSemantics)
            {
                // CharInfo's characterBloomControl is zero. Its active bloom is
                // the general scene bloom, so the recovered path starts from the
                // already-rendered HDR camera color rather than a character redraw.
                recoveredBloomMipCount = BuildRecoveredSceneBloomPyramid(
                    commandBuffer,
                    recoveredPostSource,
                    width,
                    height,
                    bloomThreshold,
                    bloomIntensity,
                    bloomSerializedScatter,
                    useRecoveredGachaRoomPostProfile);
                bloomOutputId = recoveredBloomMipCount > 1
                    ? RecoveredBloomMipUpIds[0]
                    : RecoveredBloomMipDownIds[0];
            }
            else
            {
                commandBuffer.Blit(
                    CharacterBloomSourceId,
                    CharacterBloomAId,
                    postProcessMaterial,
                    1);
                // Record the blur direction as command-buffer state. Mutating one
                // Material twice before ExecuteCommandBuffer leaves both deferred
                // Blits observing the final value, which made both passes vertical.
                commandBuffer.SetGlobalVector(
                    BloomDirectionId,
                    new Vector4(1.0f, 0.0f, 0.0f, 0.0f));
                commandBuffer.Blit(CharacterBloomAId, CharacterBloomBId, postProcessMaterial, 2);
                commandBuffer.SetGlobalVector(
                    BloomDirectionId,
                    new Vector4(0.0f, 1.0f, 0.0f, 0.0f));
                commandBuffer.Blit(CharacterBloomBId, CharacterBloomAId, postProcessMaterial, 2);
                bloomOutputId = CharacterBloomAId;
            }

            // Native HGRenderPathScene builds bloom before ExecuteAutoExposure,
            // then runs Uber. In HGRP Auto mode the histogram reads unchanged
            // HDR scene input. CharInfo selects Manual mode, so this opt-in
            // dispatch is a renderer diagnostic rather than its original path.
            if (ShouldEnqueueRecoveredAutoHistogram(
                    recoveredLiveCharInfoAutoExposureRequested,
                    recoveredLiveCharInfoAutoExposureCompute != null &&
                        recoveredLiveCharInfoAutoExposureKernel >= 0,
                    liveAutoExposureState != null))
            {
                EnqueueRecoveredLiveCharInfoHistogram(
                    commandBuffer,
                    camera,
                    liveAutoExposureState,
                    width,
                height);
            }

            bool recoveredLutReady =
                useRecoveredPostSemantics &&
                recoveredColorGradingLut != null &&
                recoveredColorGradingLut.EnqueueBuild(commandBuffer);
            Texture exactEndminfLut = null;
            if (useRecoveredPostSemantics &&
                recoveredEndminfUberExactRuntime.Requested &&
                recoveredColorGradingLut != null &&
                recoveredColorGradingLut.EnsureExactEndminfTexture())
            {
                exactEndminfLut =
                    recoveredColorGradingLut.ExactEndminfTexture;
            }
            // In the recovered live path _ExposureParams.x was used to divide
            // character HDR during ForwardLit. The shipped Uber multiplies the
            // same current camera value back before the authored post exposure
            // (CharInfo is exactly zero EV). _PostExposure is the compatibility
            // shader's carrier for that mathematically identical undo.
            float exposure = liveAutoExposureState != null
                ? liveAutoExposureState.CurrentExposure
                : Mathf.Pow(2.0f, exposureEv);
            postProcessMaterial.SetFloat(PostExposureId, exposure);
            bool hasEndminfPost =
                EndfieldEndminfVisualCompatibilityClock.TryEvaluateRecoveredPost(
                    camera,
                    out EndfieldEndminfVisualCompatibilityClock.RecoveredPostState
                        endminfPost);
            postProcessMaterial.SetVector(
                EndminfVisualCompatibilityParamsId,
                hasEndminfPost
                    ? new Vector4(
                        endminfPost.radialIntensity *
                            EndminfCompatibilityUberIntensityScale,
                        endminfPost.chromaticIntensity *
                            EndminfCompatibilityUberIntensityScale,
                        endminfPost.mode,
                        endminfPost.effectivePower)
                    : Vector4.zero);
            postProcessMaterial.SetVector(
                EndminfVisualCompatibilityCenterId,
                hasEndminfPost
                    ? endminfPost.centerViewport
                    : new Vector2(0.5f, 0.5f));
            postProcessMaterial.SetFloat(
                TonemapModeId,
                asset.applyAcesModifiedApproximation ? 1.0f : 0.0f);
            postProcessMaterial.SetFloat(BloomIntensityId, bloomIntensity);
            postProcessMaterial.SetVector(ToneCurveParams0Id, new Vector4(0.0f, 0.5f, 0.0f, 0.5f));
            postProcessMaterial.SetVector(ToneCurveParams1Id, new Vector4(0.0f, 1.0f, saturation, 1.0f));
            postProcessMaterial.SetVector(VignetteParamsId, vignetteParams);
            postProcessMaterial.SetFloat(
                RecoveredColorGradingLutReadyId,
                recoveredLutReady ? 1.0f : 0.0f);
            if (recoveredLutReady)
            {
                postProcessMaterial.SetTexture(
                    RecoveredColorGradingLutId,
                    recoveredColorGradingLut.Texture);
            }
            commandBuffer.SetGlobalTexture(
                BloomTextureId,
                new RenderTargetIdentifier(bloomOutputId));
            commandBuffer.SetGlobalFloat(
                RecoveredLinearUnormFinalTargetId,
                useRecoveredLinearUnormFinalTarget ? 1.0f : 0.0f);
            commandBuffer.SetGlobalVector(
                RecoveredFinalTargetSizeId,
                new Vector4(width, height, 1.0f / width, 1.0f / height));
            RenderTargetIdentifier postColorTarget;
            RenderTextureDescriptor deferredPostDescriptor = default;
            if (deferPresentationForSceneMV)
            {
                deferredPostDescriptor = recoveredSceneColorDescriptor;
                deferredPostDescriptor.depthBufferBits = 0;
                deferredPostDescriptor.depthStencilFormat = GraphicsFormat.None;
                if (useRecoveredLinearUnormFinalTarget)
                {
                    deferredPostDescriptor = new RenderTextureDescriptor(
                        width,
                        height,
                        RenderTextureFormat.ARGB32,
                        0)
                    {
                        msaaSamples = 1,
                        sRGB = false,
                        useMipMap = false,
                        autoGenerateMips = false
                    };
                    deferredPostDescriptor.graphicsFormat =
                        GraphicsFormat.R8G8B8A8_UNorm;
                }
                commandBuffer.GetTemporaryRT(
                    EndfieldRecoveredSceneMVCompositor.PostColorId,
                    deferredPostDescriptor,
                    useRecoveredLinearUnormFinalTarget
                        ? FilterMode.Point
                        : FilterMode.Bilinear);
                commandBuffer.SetGlobalFloat(PresentFlipYId, 0.0f);
                var deferredPostTarget = new RenderTargetIdentifier(
                    EndfieldRecoveredSceneMVCompositor.PostColorId);
                bool exactDeferredUber =
                    useRecoveredLinearUnormFinalTarget &&
                    useRecoveredPostSemantics &&
                    recoveredEndminfUberExactRuntime.Enqueue(
                        commandBuffer,
                        recoveredPostSource,
                        new RenderTargetIdentifier(bloomOutputId),
                        exactEndminfLut,
                        deferredPostTarget,
                        width,
                        height,
                        recoveredBloomMipWidths[0],
                        recoveredBloomMipHeights[0],
                        exposure,
                        hasEndminfPost,
                        endminfPost);
                if (!exactDeferredUber)
                {
                    commandBuffer.Blit(
                        recoveredPostSource,
                        EndfieldRecoveredSceneMVCompositor.PostColorId,
                        postProcessMaterial,
                        0);
                }
                LastRecoveredEndminfExactUberSubmitted = exactDeferredUber;
                if (exactDeferredUber)
                    LastRecoveredEndminfExactUberVariant =
                        recoveredEndminfUberExactRuntime.LastSubmittedVariant;
                if (LastRecoveredEndminfExactUberRequested && !exactDeferredUber)
                {
                    LastRecoveredEndminfExactUberFailure =
                        exactEndminfLut == null &&
                        recoveredColorGradingLut != null &&
                        !string.IsNullOrEmpty(
                            recoveredColorGradingLut.ExactEndminfFailure)
                        ? recoveredColorGradingLut.ExactEndminfFailure
                        : recoveredEndminfUberExactRuntime.Failure;
                }
                EndfieldRecoveredPostStageDiagnostic.EnqueueStageIfActive(
                    commandBuffer,
                    EndfieldRecoveredPostStageDiagnostic.FinalUber,
                    new RenderTargetIdentifier(
                        EndfieldRecoveredSceneMVCompositor.PostColorId),
                    deferredPostDescriptor);
                postColorTarget = new RenderTargetIdentifier(
                    EndfieldRecoveredSceneMVCompositor.PostColorId);
                deferredPostColor = new EndfieldRecoveredSceneColorHandle(
                    EndfieldRecoveredSceneMVCompositor.PostColorId,
                    deferredPostDescriptor);
                deferredLinearUnorm = useRecoveredLinearUnormFinalTarget;
            }
            else if (useRecoveredLinearUnormFinalTarget)
            {
                var finalDisplayDescriptor = new RenderTextureDescriptor(
                    width,
                    height,
                    RenderTextureFormat.ARGB32,
                    0)
                {
                    msaaSamples = 1,
                    sRGB = false,
                    useMipMap = false,
                    autoGenerateMips = false
                };
                finalDisplayDescriptor.graphicsFormat = GraphicsFormat.R8G8B8A8_UNorm;
                commandBuffer.GetTemporaryRT(
                    RecoveredFinalDisplayId,
                    finalDisplayDescriptor,
                    FilterMode.Point);
                commandBuffer.SetGlobalFloat(PresentFlipYId, 0.0f);
                var finalDisplayTarget = new RenderTargetIdentifier(
                    RecoveredFinalDisplayId);
                bool exactDisplayUber =
                    useRecoveredPostSemantics &&
                    recoveredEndminfUberExactRuntime.Enqueue(
                        commandBuffer,
                        recoveredPostSource,
                        new RenderTargetIdentifier(bloomOutputId),
                        exactEndminfLut,
                        finalDisplayTarget,
                        width,
                        height,
                        recoveredBloomMipWidths[0],
                        recoveredBloomMipHeights[0],
                        exposure,
                        hasEndminfPost,
                        endminfPost);
                if (!exactDisplayUber)
                {
                    commandBuffer.Blit(
                        recoveredPostSource,
                        RecoveredFinalDisplayId,
                        postProcessMaterial,
                        0);
                }
                LastRecoveredEndminfExactUberSubmitted = exactDisplayUber;
                if (exactDisplayUber)
                    LastRecoveredEndminfExactUberVariant =
                        recoveredEndminfUberExactRuntime.LastSubmittedVariant;
                if (LastRecoveredEndminfExactUberRequested && !exactDisplayUber)
                {
                    LastRecoveredEndminfExactUberFailure =
                        exactEndminfLut == null &&
                        recoveredColorGradingLut != null &&
                        !string.IsNullOrEmpty(
                            recoveredColorGradingLut.ExactEndminfFailure)
                        ? recoveredColorGradingLut.ExactEndminfFailure
                        : recoveredEndminfUberExactRuntime.Failure;
                }
                EndfieldRecoveredPostStageDiagnostic.EnqueueStageIfActive(
                    commandBuffer,
                    EndfieldRecoveredPostStageDiagnostic.FinalUber,
                    new RenderTargetIdentifier(RecoveredFinalDisplayId),
                    finalDisplayDescriptor);
                postColorTarget = new RenderTargetIdentifier(RecoveredFinalDisplayId);

                if (!loggedRecoveredLinearUnormFinalTarget)
                {
                    Debug.Log(
                        "Recovered linear-UNorm final target active: UberPost IEC sRGB OETF and " +
                        "deterministic RGB dither write one R8G8B8A8_UNorm temporary, followed " +
                        "by a same-format CommandBuffer.CopyTexture presentation copy.");
                    loggedRecoveredLinearUnormFinalTarget = true;
                }
            }
            else
            {
                commandBuffer.SetGlobalFloat(
                    PresentFlipYId,
                    ShouldFlipPresentation(camera) ? 1.0f : 0.0f);
                commandBuffer.Blit(
                    recoveredPostSource,
                    BuiltinRenderTextureType.CameraTarget,
                    postProcessMaterial,
                    0);
                var cameraTargetDescriptor = new RenderTextureDescriptor(
                    width,
                    height,
                    RenderTextureFormat.ARGB32,
                    0)
                {
                    msaaSamples = 1,
                    sRGB = true,
                    useMipMap = false,
                    autoGenerateMips = false
                };
                EndfieldRecoveredPostStageDiagnostic.EnqueueStageIfActive(
                    commandBuffer,
                    EndfieldRecoveredPostStageDiagnostic.FinalUber,
                    new RenderTargetIdentifier(
                        BuiltinRenderTextureType.CameraTarget),
                    cameraTargetDescriptor);
                postColorTarget = new RenderTargetIdentifier(
                    BuiltinRenderTextureType.CameraTarget);
            }

            if (useRecoveredPostSemantics)
            {
                for (int i = 0; i < recoveredBloomMipCount; i++)
                {
                    commandBuffer.ReleaseTemporaryRT(RecoveredBloomMipDownIds[i]);
                    if (recoveredBloomMipCount > 1)
                        commandBuffer.ReleaseTemporaryRT(RecoveredBloomMipUpIds[i]);
                }
            }
            else
            {
                commandBuffer.ReleaseTemporaryRT(CharacterBloomBId);
                commandBuffer.ReleaseTemporaryRT(CharacterBloomAId);
                commandBuffer.ReleaseTemporaryRT(CharacterBloomSourceId);
            }
            if (!deferPresentationForSceneMV)
                commandBuffer.ReleaseTemporaryRT(CameraColorId);
            if (useRecoveredEndminfRgba16PostSource)
                commandBuffer.ReleaseTemporaryRT(RecoveredEndminfPostSourceId);
            if (hasRecoveredTemporalPostSource &&
                releaseRecoveredTemporalPostSource)
                commandBuffer.ReleaseTemporaryRT(
                    recoveredTemporalPostSourceId);
            context.ExecuteCommandBuffer(commandBuffer);
            commandBuffer.Release();

            if (useRecoveredPostUberWorldUi)
            {
                DrawRecoveredPostUberWorldUi(
                    context,
                    camera,
                    cullingResults,
                    postColorTarget,
                    recoveredPrimarySceneDepth,
                    width,
                    height,
                    hasEndminfPost &&
                        endminfPost.mode > 0.5f &&
                        endminfPost.radialIntensity +
                            endminfPost.chromaticIntensity > 0.00001f);
            }

            commandBuffer = new CommandBuffer
            {
                name = "Finalize HGCompat Character Post"
            };
            if (useRecoveredPostUberWorldUi)
            {
                commandBuffer.SetGlobalFloat(RecoveredPostUberWorldUiReadyId, 0.0f);
                commandBuffer.SetGlobalTexture(SceneDepthId, Texture2D.blackTexture);
            }
            if (useRecoveredLinearUnormFinalTarget &&
                !deferPresentationForSceneMV)
            {
                commandBuffer.CopyTexture(
                    new RenderTargetIdentifier(RecoveredFinalDisplayId),
                    new RenderTargetIdentifier(camera.targetTexture));
                commandBuffer.ReleaseTemporaryRT(RecoveredFinalDisplayId);
            }
            context.ExecuteCommandBuffer(commandBuffer);
            commandBuffer.Release();
        }

        private void DrawRecoveredPostUberWorldUi(
            ScriptableRenderContext context,
            Camera camera,
            CullingResults cullingResults,
            RenderTargetIdentifier postColorTarget,
            RenderTexture primarySceneDepth,
            int width,
            int height,
            bool compatibilityUberWarpActive)
        {
            CommandBuffer commandBuffer = new CommandBuffer
            {
                name = "Recovered post-Uber CharInfo world UI"
            };
            bool diagnosticDepthSyncRequested = IsEnabledSelectorValue(
                System.Environment.GetEnvironmentVariable(
                    "ENDFIELD_DIAGNOSTIC_SYNC_POST_UBER_PORTRAIT_DEPTH"));
            bool diagnosticDepthSyncReady = false;
            RenderTargetIdentifier portraitSceneDepth =
                new RenderTargetIdentifier(primarySceneDepth);
            if (diagnosticDepthSyncRequested && compatibilityUberWarpActive)
            {
                int depthSyncPass = postProcessMaterial != null
                    ? postProcessMaterial.FindPass("ENDMINF_POST_UBER_DEPTH_SYNC")
                    : -1;
                bool formatReady = SystemInfo.IsFormatSupported(
                    GraphicsFormat.R32_SFloat,
                    FormatUsage.Render);
                if (depthSyncPass >= 0 && formatReady)
                {
                    var depthDescriptor = new RenderTextureDescriptor(
                        width,
                        height,
                        GraphicsFormat.R32_SFloat,
                        0)
                    {
                        msaaSamples = 1,
                        sRGB = false,
                        useMipMap = false,
                        autoGenerateMips = false,
                        enableRandomWrite = false,
                        useDynamicScale = false
                    };
                    commandBuffer.GetTemporaryRT(
                        RecoveredPostUberPortraitDepthId,
                        depthDescriptor,
                        FilterMode.Bilinear);
                    // Diagnostic only: use the exact compatibility-Uber sample
                    // footprint and retain the nearest raw scene depth among all
                    // color contributors. This tests whether the body-shaped
                    // portrait cutout is caused by post-Uber color sampling
                    // against the untouched primary depth. It is not source
                    // authority for changing the canonical _SceneDepth owner.
                    commandBuffer.Blit(
                        primarySceneDepth,
                        RecoveredPostUberPortraitDepthId,
                        postProcessMaterial,
                        depthSyncPass);
                    portraitSceneDepth = new RenderTargetIdentifier(
                        RecoveredPostUberPortraitDepthId);
                    diagnosticDepthSyncReady = true;
                }
                else if (!loggedRecoveredPostUberPortraitDepthSyncFailure)
                {
                    Debug.LogWarning(
                        "Diagnostic post-Uber portrait-depth synchronization " +
                        "failed closed: " +
                        (depthSyncPass < 0
                            ? "the ENDMINF_POST_UBER_DEPTH_SYNC shader pass is unavailable"
                            : "R32_SFloat render targets are unavailable") +
                        ". The portrait continues to sample primary scene depth.");
                    loggedRecoveredPostUberPortraitDepthSyncFailure = true;
                }
            }
            // The retail pass samples the primary general scene depth while a
            // distinct generated output-depth target is paired with the post
            // color. The selected UI pass is ZTest Always/ZWrite Off, so this
            // lab binds only the source-closed primary depth SRV. Unity's
            // lightweight DrawRenderers API cannot expose that same resource as
            // a read-only DSV, and the distinct retail output-depth descriptor
            // is not source-closed.
            commandBuffer.SetRenderTarget(postColorTarget);
            commandBuffer.SetGlobalTexture(SceneDepthId, portraitSceneDepth);
            commandBuffer.SetGlobalVector(
                SceneDepthTexelSizeId,
                new Vector4(1.0f / width, 1.0f / height, width, height));
            commandBuffer.SetGlobalFloat(RecoveredPostUberWorldUiReadyId, 1.0f);
            Matrix4x4 viewNoTranslation = camera.worldToCameraMatrix;
            viewNoTranslation.m03 = 0.0f;
            viewNoTranslation.m13 = 0.0f;
            viewNoTranslation.m23 = 0.0f;
            viewNoTranslation.m33 = 1.0f;
            Matrix4x4 projection = GL.GetGPUProjectionMatrix(
                camera.nonJitteredProjectionMatrix,
                true);
            commandBuffer.SetGlobalMatrix(
                NonJitteredViewNoTransProjMatrixId,
                projection * viewNoTranslation);
            Vector3 cameraPosition = camera.transform.position;
            commandBuffer.SetGlobalVector(
                WorldSpaceCameraPosInternalId,
                new Vector4(
                    cameraPosition.x,
                    cameraPosition.y,
                    cameraPosition.z,
                    1.0f));
            commandBuffer.SetGlobalFloat(RenderPathInjectedId, 1.0f);
            commandBuffer.SetGlobalFloat(HGFlipXId, 0.0f);
            commandBuffer.SetGlobalFloat(
                HGFlipYId,
                camera.targetTexture == null ? 1.0f : 0.0f);
            context.ExecuteCommandBuffer(commandBuffer);
            commandBuffer.Release();

            DrawRenderers(
                context,
                camera,
                cullingResults,
                RenderQueueRange.transparent,
                SortingCriteria.CommonTransparent,
                1 << EndfieldRecoveredCharInfoBackgroundPortrait.SourceUiLayer);

            commandBuffer = new CommandBuffer
            {
                name = "Reset recovered post-Uber CharInfo world UI globals"
            };
            commandBuffer.SetGlobalFloat(RenderPathInjectedId, 0.0f);
            commandBuffer.SetGlobalFloat(HGFlipXId, 0.0f);
            commandBuffer.SetGlobalFloat(HGFlipYId, 0.0f);
            if (diagnosticDepthSyncReady)
                commandBuffer.ReleaseTemporaryRT(RecoveredPostUberPortraitDepthId);
            context.ExecuteCommandBuffer(commandBuffer);
            commandBuffer.Release();

            if (diagnosticDepthSyncReady &&
                !loggedRecoveredPostUberPortraitDepthSync)
            {
                Debug.Log(
                    "Diagnostic post-Uber portrait-depth synchronization is " +
                    "active: _SceneDepth contains the nearest primary depth " +
                    "from the compatibility Uber color-sampling footprint. " +
                    "This is a causality probe, not a canonical render change.");
                loggedRecoveredPostUberPortraitDepthSync = true;
            }

            if (!loggedRecoveredPostUberWorldUi)
            {
                Debug.Log(
                    "Recovered post-Uber CharInfo world UI active: ordinary transparents " +
                    "exclude source layer 16; the fullscreen post completes first; layer 16 " +
                    "then draws into that post color while _SceneDepth samples the preserved " +
                    $"full-scene primary {primarySceneDepth.depthStencilFormat} depth/stencil.");
                loggedRecoveredPostUberWorldUi = true;
            }
        }

        private bool ApplyRecoveredEndminfOpeningStripCompatibilityBeforeTemporal(
            ScriptableRenderContext context,
            Camera camera,
            bool useRecoveredPostSemantics,
            RenderTextureDescriptor sceneColorDescriptor,
            RenderTexture recoveredSceneMV)
        {
            LastRecoveredEndminfOpeningStripCompatibilityApplied = false;
            LastRecoveredEndminfOpeningStripSceneMVApplied = false;
            int width = Mathf.Max(sceneColorDescriptor.width, 1);
            int height = Mathf.Max(sceneColorDescriptor.height, 1);
            EndfieldEndminfVisualCompatibilityClock.RecoveredOpeningStripState
                openingStripState = default;
            RenderTexture openingStripSelector = null;
            RenderTexture unusedOpeningStripGBufferB;
            RenderTexture unusedOpeningStripGBufferC;
            string openingStripSelectorFailure;
            bool hasOpeningStripSelector =
                recoveredPreGBufferDepthOwner != null &&
                recoveredPreGBufferDepthOwner.TryGetCurrentPublication(
                    camera,
                    width,
                    height,
                    out openingStripSelector,
                    out unusedOpeningStripGBufferB,
                    out unusedOpeningStripGBufferC,
                    out openingStripSelectorFailure);
            bool useRecoveredEndminfOpeningStripCompatibility =
                useRecoveredPostSemantics &&
                !EndfieldRecoveredEndminfOpeningStripExactRuntime.ActiveThisFrame &&
                recoveredEndminfOpeningStripMaterial != null &&
                hasOpeningStripSelector &&
                EndfieldEndminfVisualCompatibilityClock.TryEvaluateOpeningStrip(
                    out openingStripState);
            if (!useRecoveredEndminfOpeningStripCompatibility)
                return false;

            var commandBuffer = new CommandBuffer
            {
                name =
                    "Recovered Endminf opening-strip compatibility before temporal"
            };
            commandBuffer.GetTemporaryRT(
                RecoveredEndminfOpeningStripSourceId,
                sceneColorDescriptor,
                FilterMode.Bilinear);
            commandBuffer.SetGlobalVector(
                EndminfOpeningStripParamsId,
                new Vector4(
                    openingStripState.intensity,
                    openingStripState.displacementPixels,
                    openingStripState.chromaticEdgePixels,
                    openingStripState.elapsed));
            commandBuffer.SetGlobalVector(
                EndminfOpeningStripSourceSizeId,
                new Vector4(width, height, 1.0f / width, 1.0f / height));
            commandBuffer.SetGlobalTexture(
                EndminfOpeningStripSelectorId,
                openingStripSelector);
            commandBuffer.Blit(
                CameraColorId,
                RecoveredEndminfOpeningStripSourceId,
                recoveredEndminfOpeningStripMaterial,
                0);
            commandBuffer.CopyTexture(
                RecoveredEndminfOpeningStripSourceId,
                CameraColorId);
            commandBuffer.ReleaseTemporaryRT(
                RecoveredEndminfOpeningStripSourceId);
            // The Target1 write is source-backed, but the focused A/B remains
            // inside startup temporal-history variance. Keep it diagnostic
            // until a deterministic dense sequence demonstrates improvement.
            bool publishSceneMV = recoveredSceneMV != null &&
                System.String.Equals(
                    System.Environment.GetEnvironmentVariable(
                        "ENDFIELD_ENDMINF_OPENING_STRIP_SCENEMV"),
                    "1",
                    System.StringComparison.Ordinal);
            if (publishSceneMV)
            {
                RenderTextureDescriptor sceneMVDescriptor =
                    recoveredSceneMV.descriptor;
                sceneMVDescriptor.depthBufferBits = 0;
                sceneMVDescriptor.msaaSamples = 1;
                sceneMVDescriptor.bindMS = false;
                commandBuffer.GetTemporaryRT(
                    RecoveredEndminfOpeningStripSceneMVId,
                    sceneMVDescriptor,
                    FilterMode.Point);
                commandBuffer.Blit(
                    recoveredSceneMV,
                    RecoveredEndminfOpeningStripSceneMVId,
                    recoveredEndminfOpeningStripMaterial,
                    1);
                commandBuffer.CopyTexture(
                    RecoveredEndminfOpeningStripSceneMVId,
                    recoveredSceneMV);
                commandBuffer.ReleaseTemporaryRT(
                    RecoveredEndminfOpeningStripSceneMVId);
                LastRecoveredEndminfOpeningStripSceneMVApplied = true;
            }
            context.ExecuteCommandBuffer(commandBuffer);
            commandBuffer.Release();
            LastRecoveredEndminfOpeningStripCompatibilityApplied = true;

            if (!loggedRecoveredEndminfOpeningStrip)
            {
                Debug.Log(
                    "Recovered Endminf opening horizontal-strip compatibility " +
                    "pass active in packed SceneColor before temporal resolve; " +
                    "captured Target1 SceneMV-B publication remains an " +
                    "explicit diagnostic; " +
                    "the separately gated exact retained packet path remains " +
                    "authoritative.");
                loggedRecoveredEndminfOpeningStrip = true;
            }
            return true;
        }

        private bool EnqueueRecoveredEndminfTemporalResolve(
            CommandBuffer commandBuffer,
            Camera camera,
            int width,
            int height,
            RenderTexture recoveredPrimarySceneDepth,
            RenderTexture recoveredSceneMV,
            out int temporalPostSourceId,
            out RenderTextureDescriptor temporalPostSourceDescriptor,
            out bool releaseTemporalPostSource)
        {
            temporalPostSourceId = 0;
            temporalPostSourceDescriptor = default;
            releaseTemporalPostSource = false;
            LastRecoveredUnityPublicNgxProxyRequested =
                recoveredUnityPublicNgxProxy != null &&
                recoveredUnityPublicNgxProxy.Requested;
            LastRecoveredUnityPublicNgxProxySubmitted = false;
            LastRecoveredUnityPublicNgxProxyValidated = false;
            LastRecoveredUnityPublicNgxProxyFailure = string.Empty;
            LastRecoveredUnityPublicNgxProxyJitterOffset = Vector2.zero;
            LastRecoveredUnityPublicNgxProxyJitterPhase = -1;
            LastRecoveredUnityPublicNgxProxyIndicatorInvertAxisX = -1;
            LastRecoveredUnityPublicNgxProxyIndicatorInvertAxisY = -1;
            if (recoveredTemporalMaterial == null ||
                System.String.Equals(
                    System.Environment.GetEnvironmentVariable(
                        "ENDFIELD_ENDMINF_DISABLE_TEMPORAL_RESOLVE"),
                    "1",
                    System.StringComparison.Ordinal) ||
                !EndfieldEndminfVisualCompatibilityClock.Requested)
            {
                return false;
            }

            if (LastRecoveredUnityPublicNgxProxyRequested)
            {
                LastRecoveredUnityPublicNgxProxySubmitted =
                    recoveredUnityPublicNgxProxy.TryEnqueue(
                        commandBuffer,
                        new RenderTargetIdentifier(CameraColorId),
                        recoveredPrimarySceneDepth,
                        recoveredSceneMV,
                        width,
                        height);
                if (!LastRecoveredUnityPublicNgxProxySubmitted)
                {
                    LastRecoveredUnityPublicNgxProxyFailure =
                        recoveredUnityPublicNgxProxy.Failure;
                    Debug.LogWarning(
                        "UnityPublicNgxProxy failed closed: " +
                        LastRecoveredUnityPublicNgxProxyFailure + ".");
                }
                if (!LastRecoveredUnityPublicNgxProxySubmitted)
                    return false;
                LastRecoveredUnityPublicNgxProxyJitterOffset =
                    recoveredUnityPublicNgxProxy.LastJitterOffset;
                LastRecoveredUnityPublicNgxProxyJitterPhase =
                    recoveredUnityPublicNgxProxy.LastJitterPhase;
                LastRecoveredUnityPublicNgxProxyIndicatorInvertAxisX =
                    EndfieldRecoveredUnityPublicNgxProxy
                        .CapturedIndicatorInvertAxisX;
                LastRecoveredUnityPublicNgxProxyIndicatorInvertAxisY =
                    EndfieldRecoveredUnityPublicNgxProxy
                        .CapturedIndicatorInvertAxisY;
                if (!recoveredUnityPublicNgxProxy.TryGetOutputDescriptor(
                        out temporalPostSourceDescriptor))
                {
                    LastRecoveredUnityPublicNgxProxySubmitted = false;
                    LastRecoveredUnityPublicNgxProxyFailure =
                        "public DLSS output descriptor is unavailable or inexact";
                    return false;
                }
                temporalPostSourceId =
                    EndfieldRecoveredUnityPublicNgxProxy.OutputTextureId;
                return true;
            }

            bool temporalResolveActive =
                EndfieldEndminfVisualCompatibilityClock.TryGetElapsed(
                    out float elapsed);

            if (!recoveredTemporalStates.TryGetValue(
                    camera,
                    out RecoveredTemporalCameraState state))
            {
                state = new RecoveredTemporalCameraState();
                recoveredTemporalStates.Add(camera, state);
            }

            bool canRunDilation =
                recoveredTemporalDilationMaterial != null &&
                recoveredPrimarySceneDepth != null &&
                recoveredSceneMV != null;
            bool invalidHistory = state.history == null ||
                state.history.width != width ||
                state.history.height != height ||
                state.history.graphicsFormat !=
                    GraphicsFormat.R16G16B16A16_SFloat ||
                (canRunDilation &&
                    (state.historyDilatedDepth == null ||
                     state.historyDilatedDepth.width != width ||
                     state.historyDilatedDepth.height != height ||
                     state.historyDilatedSceneMV == null ||
                     state.historyDilatedSceneMV.width != width ||
                     state.historyDilatedSceneMV.height != height)) ||
                (temporalResolveActive &&
                    !float.IsNaN(state.lastElapsed) &&
                    elapsed + 0.001f < state.lastElapsed);
            if (invalidHistory)
            {
                ReleaseRecoveredTemporalHistory(state);
                var historyDescriptor = new RenderTextureDescriptor(
                    width,
                    height)
                {
                    graphicsFormat = GraphicsFormat.R16G16B16A16_SFloat,
                    depthStencilFormat = GraphicsFormat.None,
                    msaaSamples = 1,
                    useMipMap = false,
                    autoGenerateMips = false,
                    sRGB = false
                };
                state.history = new RenderTexture(historyDescriptor)
                {
                    name = "Endfield Recovered TAAU History " + camera.name,
                    filterMode = FilterMode.Bilinear,
                    wrapMode = TextureWrapMode.Clamp,
                    hideFlags = HideFlags.HideAndDontSave
                };
                state.history.Create();
                commandBuffer.Blit(
                    new RenderTargetIdentifier(CameraColorId),
                    state.history);

                if (canRunDilation)
                {
                    state.historyDilatedDepth = CreateRecoveredTemporalTexture(
                        width,
                        height,
                        GraphicsFormat.R32_SFloat,
                        FilterMode.Point,
                        "Endfield Recovered TAAU Dilated Depth History " +
                        camera.name);
                    state.historyDilatedSceneMV = CreateRecoveredTemporalTexture(
                        width,
                        height,
                        EndfieldRecoveredSceneMVCompositor.SceneMVFormat,
                        FilterMode.Point,
                        "Endfield Recovered TAAU Dilated SceneMV History " +
                        camera.name);
                }
            }

            Matrix4x4 currentNonJitteredViewProjection =
                GL.GetGPUProjectionMatrix(
                    camera.nonJitteredProjectionMatrix,
                    true) * camera.worldToCameraMatrix;
            Matrix4x4 reprojectionMatrix =
                state.hasPreviousNonJitteredViewProjection
                    ? state.previousNonJitteredViewProjection *
                      currentNonJitteredViewProjection.inverse
                    : Matrix4x4.identity;

            bool useCurrentSceneMVDilation = canRunDilation &&
                state.historyDilatedDepth != null &&
                state.historyDilatedSceneMV != null;
            bool useCurrentMaskDilation = false;
            if (useCurrentSceneMVDilation)
            {
                var sceneMvDescriptor = new RenderTextureDescriptor(
                    width,
                    height)
                {
                    graphicsFormat =
                        EndfieldRecoveredSceneMVCompositor.SceneMVFormat,
                    depthStencilFormat = GraphicsFormat.None,
                    msaaSamples = 1,
                    useMipMap = false,
                    autoGenerateMips = false,
                    sRGB = false
                };
                var depthDescriptor = sceneMvDescriptor;
                depthDescriptor.graphicsFormat = GraphicsFormat.R32_SFloat;
                commandBuffer.GetTemporaryRT(
                    RecoveredTemporalDilatedSceneMVId,
                    sceneMvDescriptor,
                    FilterMode.Point);
                commandBuffer.GetTemporaryRT(
                    RecoveredTemporalSelectedSceneMVId,
                    sceneMvDescriptor,
                    FilterMode.Point);
                commandBuffer.GetTemporaryRT(
                    RecoveredTemporalDilatedDepthId,
                    depthDescriptor,
                    FilterMode.Point);
                useCurrentMaskDilation =
                    recoveredTemporalMaskDilationMaterial != null;
                if (useCurrentMaskDilation)
                {
                    var maskDescriptor = sceneMvDescriptor;
                    maskDescriptor.graphicsFormat = GraphicsFormat.R8_UNorm;
                    commandBuffer.GetTemporaryRT(
                        RecoveredTemporalDilatedMaskId,
                        maskDescriptor,
                        FilterMode.Point);
                }
                commandBuffer.SetGlobalTexture(
                    RecoveredTemporalSceneDepthId,
                    new RenderTargetIdentifier(recoveredPrimarySceneDepth));
                commandBuffer.SetGlobalTexture(
                    RecoveredTemporalRawSceneMVId,
                    new RenderTargetIdentifier(recoveredSceneMV));
                commandBuffer.SetGlobalTexture(
                    RecoveredTemporalPreviousDilatedDepthId,
                    state.historyDilatedDepth);
                commandBuffer.SetGlobalTexture(
                    RecoveredTemporalPreviousDilatedSceneMVId,
                    state.historyDilatedSceneMV);
                commandBuffer.SetGlobalVector(
                    RecoveredTemporalRenderSizeId,
                    new Vector4(width, height, 1.0f / width, 1.0f / height));
                commandBuffer.SetGlobalMatrix(
                    RecoveredTemporalReprojectionMatrixId,
                    reprojectionMatrix);
                commandBuffer.SetGlobalFloat(
                    RecoveredTemporalAuxiliaryHistoryValidId,
                    state.auxiliaryHistoryValid &&
                    state.hasPreviousNonJitteredViewProjection
                        ? 1.0f
                        : 0.0f);
                commandBuffer.SetGlobalFloat(
                    RecoveredTemporalOcclusionDepthDiffId,
                    0.0002f);
                commandBuffer.Blit(
                    CameraColorId,
                    RecoveredTemporalDilatedSceneMVId,
                    recoveredTemporalDilationMaterial,
                    0);
                commandBuffer.Blit(
                    CameraColorId,
                    RecoveredTemporalDilatedDepthId,
                    recoveredTemporalDilationMaterial,
                    1);
                commandBuffer.Blit(
                    CameraColorId,
                    RecoveredTemporalSelectedSceneMVId,
                    recoveredTemporalDilationMaterial,
                    2);
                if (useCurrentMaskDilation)
                {
                    commandBuffer.SetGlobalTexture(
                        RecoveredTemporalPackedSceneMVId,
                        new RenderTargetIdentifier(
                            RecoveredTemporalDilatedSceneMVId));
                    commandBuffer.Blit(
                        CameraColorId,
                        RecoveredTemporalDilatedMaskId,
                        recoveredTemporalMaskDilationMaterial,
                        0);
                }
            }

            if (!invalidHistory && temporalResolveActive)
            {

                var resolveDescriptor = new RenderTextureDescriptor(
                    width,
                    height)
                {
                    graphicsFormat = GraphicsFormat.R16G16B16A16_SFloat,
                    depthStencilFormat = GraphicsFormat.None,
                    msaaSamples = 1,
                    useMipMap = false,
                    autoGenerateMips = false,
                    sRGB = false
                };
                commandBuffer.GetTemporaryRT(
                    RecoveredTemporalResolveId,
                    resolveDescriptor,
                    FilterMode.Bilinear);
                recoveredTemporalMaterial.SetTexture(
                    RecoveredTemporalHistoryId,
                    state.history);
                commandBuffer.SetGlobalTexture(
                    RecoveredTemporalCurrentId,
                    new RenderTargetIdentifier(CameraColorId));
                commandBuffer.SetGlobalTexture(
                    RecoveredTemporalCurrentLoadId,
                    new RenderTargetIdentifier(CameraColorId));
                bool usePackedResolve = useCurrentSceneMVDilation &&
                    useCurrentMaskDilation &&
                    System.String.Equals(
                        System.Environment.GetEnvironmentVariable(
                            PackedTemporalResolveEnvironmentVariable),
                        "1",
                        System.StringComparison.Ordinal);
                commandBuffer.SetGlobalTexture(
                    RecoveredTemporalSceneMVId,
                    usePackedResolve
                        ? new RenderTargetIdentifier(
                            RecoveredTemporalDilatedSceneMVId)
                        : useCurrentSceneMVDilation
                        ? new RenderTargetIdentifier(
                            RecoveredTemporalSelectedSceneMVId)
                        : recoveredSceneMV != null
                        ? new RenderTargetIdentifier(recoveredSceneMV)
                        : new RenderTargetIdentifier(Texture2D.grayTexture));
                recoveredTemporalMaterial.SetFloat(
                    RecoveredTemporalPackedResolveId,
                    usePackedResolve ? 1.0f : 0.0f);
                if (usePackedResolve)
                {
                    commandBuffer.SetGlobalTexture(
                        RecoveredTemporalDilatedDepthId,
                        new RenderTargetIdentifier(
                            RecoveredTemporalDilatedDepthId));
                    commandBuffer.SetGlobalTexture(
                        RecoveredTemporalDilatedMaskId,
                        new RenderTargetIdentifier(
                            RecoveredTemporalDilatedMaskId));
                    recoveredTemporalMaterial.SetVector(
                        RecoveredTemporalJitterId,
                        Vector4.zero);
                    recoveredTemporalMaterial.SetFloat(
                        RecoveredTemporalFrameInfoYId,
                        1.0f);
                    recoveredTemporalMaterial.SetFloat(
                        RecoveredTemporalFastConvergeId,
                        0.0f);
                    recoveredTemporalMaterial.SetFloat(
                        RecoveredTemporalResponsiveTransparencyId,
                        0.0f);
                }
                // Desktop TAAU serializes distinct 0.95 static and 0.85
                // in-motion history weights. The exact SceneMV decoder in the
                // resolve selects between them per pixel.
                recoveredTemporalMaterial.SetFloat(
                    RecoveredTemporalHistoryWeightId,
                    0.85f);
                recoveredTemporalMaterial.SetFloat(
                    RecoveredTemporalStaticHistoryWeightId,
                    0.95f);
                commandBuffer.Blit(
                    CameraColorId,
                    RecoveredTemporalResolveId,
                    recoveredTemporalMaterial,
                    0);
                if (usePackedResolve)
                {
                    commandBuffer.CopyTexture(
                        new RenderTargetIdentifier(RecoveredTemporalResolveId),
                        state.history);
                    commandBuffer.GetTemporaryRT(
                        RecoveredTemporalPresentationId,
                        resolveDescriptor,
                        FilterMode.Bilinear);
                    commandBuffer.Blit(
                        RecoveredTemporalResolveId,
                        RecoveredTemporalPresentationId,
                        recoveredTemporalMaterial,
                        1);
                    commandBuffer.ReleaseTemporaryRT(
                        RecoveredTemporalResolveId);
                    temporalPostSourceId =
                        RecoveredTemporalPresentationId;
                }
                else
                {
                    commandBuffer.CopyTexture(
                        new RenderTargetIdentifier(RecoveredTemporalResolveId),
                        state.history);
                    temporalPostSourceId = RecoveredTemporalResolveId;
                }
                temporalPostSourceDescriptor = resolveDescriptor;
                releaseTemporalPostSource = true;

                if (!loggedRecoveredTemporalResolve)
                {
                    Debug.Log(
                        "Recovered Endminf pre-Bloom temporal history resolve is active " +
                        "with the shipped current-frame max-depth SceneMV dilation, " +
                        "exact fourth-root reprojection, and desktop static/motion " +
                        "weights 0.95/0.85" +
                        (usePackedResolve
                            ? "; opt-in packed Quality-0 consumer experiment active."
                            : "."));
                    loggedRecoveredTemporalResolve = true;
                }
            }
            else if (!invalidHistory)
            {
                // TAA history belongs to the camera, not Endminf's `_02`
                // effect clock. Keep the latest pre-selection scene color so
                // the first visible actor frame can consume the immediately
                // preceding blank model-swap frame observed in retail.
                commandBuffer.Blit(
                    new RenderTargetIdentifier(CameraColorId),
                    state.history);
            }

            if (useCurrentSceneMVDilation)
            {
                commandBuffer.CopyTexture(
                    new RenderTargetIdentifier(RecoveredTemporalDilatedDepthId),
                    state.historyDilatedDepth);
                commandBuffer.CopyTexture(
                    new RenderTargetIdentifier(RecoveredTemporalDilatedSceneMVId),
                    state.historyDilatedSceneMV);
                commandBuffer.ReleaseTemporaryRT(
                    RecoveredTemporalDilatedDepthId);
                commandBuffer.ReleaseTemporaryRT(
                    RecoveredTemporalDilatedSceneMVId);
                commandBuffer.ReleaseTemporaryRT(
                    RecoveredTemporalSelectedSceneMVId);
                if (recoveredTemporalMaskDilationMaterial != null)
                    commandBuffer.ReleaseTemporaryRT(
                        RecoveredTemporalDilatedMaskId);
                state.auxiliaryHistoryValid = true;
            }
            else
            {
                // A skipped producer frame breaks the recovered consecutive-
                // frame auxiliary-history contract. Re-enter with the
                // deterministic first-frame seed instead of stale textures.
                state.auxiliaryHistoryValid = false;
            }

            state.previousNonJitteredViewProjection =
                currentNonJitteredViewProjection;
            state.hasPreviousNonJitteredViewProjection = true;
            state.lastElapsed = temporalResolveActive ? elapsed : float.NaN;
            state.lastFrame = Time.frameCount;
            return temporalPostSourceId != 0;
        }

        private static void ReleaseRecoveredTemporalHistory(
            RecoveredTemporalCameraState state)
        {
            if (state == null)
                return;
            DestroyRecoveredTemporalTexture(ref state.history);
            DestroyRecoveredTemporalTexture(ref state.historyDilatedDepth);
            DestroyRecoveredTemporalTexture(ref state.historyDilatedSceneMV);
            state.auxiliaryHistoryValid = false;
            state.hasPreviousNonJitteredViewProjection = false;
            state.previousNonJitteredViewProjection = Matrix4x4.identity;
            state.lastElapsed = float.NaN;
            state.lastFrame = -1;
        }

        private static RenderTexture CreateRecoveredTemporalTexture(
            int width,
            int height,
            GraphicsFormat graphicsFormat,
            FilterMode filterMode,
            string name)
        {
            var descriptor = new RenderTextureDescriptor(width, height)
            {
                graphicsFormat = graphicsFormat,
                depthStencilFormat = GraphicsFormat.None,
                msaaSamples = 1,
                useMipMap = false,
                autoGenerateMips = false,
                sRGB = false
            };
            var texture = new RenderTexture(descriptor)
            {
                name = name,
                filterMode = filterMode,
                wrapMode = TextureWrapMode.Clamp,
                hideFlags = HideFlags.HideAndDontSave
            };
            texture.Create();
            return texture;
        }

        private static void DestroyRecoveredTemporalTexture(
            ref RenderTexture texture)
        {
            if (texture == null)
                return;
            texture.Release();
            if (Application.isPlaying)
                Object.Destroy(texture);
            else
                Object.DestroyImmediate(texture);
            texture = null;
        }

        private int BuildRecoveredSceneBloomPyramid(
            CommandBuffer commandBuffer,
            RenderTargetIdentifier sourceColor,
            int sourceWidth,
            int sourceHeight,
            float serializedThreshold,
            float serializedIntensity,
            float serializedScatter,
            bool useRecoveredGachaRoomPostProfile)
        {
            // Bloom starts at half source resolution, then caps that working
            // image to 1080 pixels high. The retained 3840x2160 Uber t1 is
            // therefore 1920x1080, not 960x540.
            float workingScale = Mathf.Min(
                0.5f,
                RecoveredBloomHeightCap / Mathf.Max(sourceHeight, 1));
            int cappedWidth = Mathf.Max(
                1,
                Mathf.RoundToInt(sourceWidth * workingScale));
            int cappedHeight = Mathf.Max(
                1,
                Mathf.RoundToInt(sourceHeight * workingScale));

            // Derive the count from the actual first bloom mip. At the native
            // 3840x2160 source this produces exactly eight bloom mips.
            int maxSize = Mathf.Max(cappedWidth, cappedHeight);
            int iterations = Mathf.FloorToInt(Mathf.Log(maxSize, 2.0f) - 2.0f);
            int mipCount = Mathf.Clamp(iterations, 1, MaxRecoveredBloomMipCount);

            for (int i = 0; i < mipCount; i++)
            {
                float mipScale = 1.0f / Mathf.Pow(2.0f, i);
                recoveredBloomMipWidths[i] = Mathf.Max(
                    1,
                    Mathf.RoundToInt(cappedWidth * mipScale));
                recoveredBloomMipHeights[i] = Mathf.Max(
                    1,
                    Mathf.RoundToInt(cappedHeight * mipScale));

                var descriptor = new RenderTextureDescriptor(
                    recoveredBloomMipWidths[i],
                    recoveredBloomMipHeights[i],
                    RecoveredSceneColorFormat,
                    0)
                {
                    msaaSamples = 1,
                    sRGB = false
                };
                commandBuffer.GetTemporaryRT(
                    RecoveredBloomMipDownIds[i],
                    descriptor,
                    FilterMode.Bilinear);
                if (mipCount > 1)
                {
                    commandBuffer.GetTemporaryRT(
                        RecoveredBloomMipUpIds[i],
                        descriptor,
                        FilterMode.Bilinear);
                }
                LastRecoveredEndminfBloomGraphicsFormat =
                    descriptor.graphicsFormat;
                if (i == 0)
                {
                    LastRecoveredEndminfBloomWidth = descriptor.width;
                    LastRecoveredEndminfBloomHeight = descriptor.height;
                }
            }

            // The recovered rotated-grid prefilter uses the first bloom mip's
            // texel size, even when the scene was first capped from 2160p.
            commandBuffer.SetGlobalVector(
                BloomTexelSizeId,
                new Vector4(
                    recoveredBloomMipWidths[0],
                    recoveredBloomMipHeights[0],
                    1.0f / recoveredBloomMipWidths[0],
                    1.0f / recoveredBloomMipHeights[0]));
            commandBuffer.Blit(
                sourceColor,
                RecoveredBloomMipDownIds[0],
                postProcessMaterial,
                1);
            var diagnosticMip0Descriptor = new RenderTextureDescriptor(
                recoveredBloomMipWidths[0],
                recoveredBloomMipHeights[0],
                RecoveredSceneColorFormat,
                0)
            {
                msaaSamples = 1,
                sRGB = false
            };
            EndfieldRecoveredPostStageDiagnostic.EnqueueStageIfActive(
                commandBuffer,
                EndfieldRecoveredPostStageDiagnostic.BloomPrefilterMip0,
                new RenderTargetIdentifier(RecoveredBloomMipDownIds[0]),
                diagnosticMip0Descriptor);

            // Each lower level uses the shipped nine-sample horizontal kernel
            // while downsampling, followed by the optimized five-fetch vertical
            // kernel at the destination size.
            for (int i = 1; i < mipCount; i++)
            {
                commandBuffer.SetGlobalVector(
                    BloomDirectionId,
                    new Vector4(1.0f, 0.0f, 0.0f, 0.0f));
                commandBuffer.Blit(
                    RecoveredBloomMipDownIds[i - 1],
                    RecoveredBloomMipUpIds[i],
                    postProcessMaterial,
                    2);
                commandBuffer.SetGlobalVector(
                    BloomDirectionId,
                    new Vector4(0.0f, 1.0f, 0.0f, 0.0f));
                commandBuffer.Blit(
                    RecoveredBloomMipUpIds[i],
                    RecoveredBloomMipDownIds[i],
                    postProcessMaterial,
                    2);
            }

            // Reconstruct from the smallest level. High quality samples the low
            // mip with the shipped cubic B-spline filter, then applies
            // lerp(highMip, lowMip, lerp(0.05, 0.95, serializedScatter)).
            float bloomScatter = Mathf.Lerp(
                0.05f,
                0.95f,
                Mathf.Clamp01(serializedScatter));
            commandBuffer.SetGlobalFloat(BloomScatterId, bloomScatter);
            for (int i = mipCount - 2; i >= 0; i--)
            {
                int lowMipId = i == mipCount - 2
                    ? RecoveredBloomMipDownIds[i + 1]
                    : RecoveredBloomMipUpIds[i + 1];
                int lowWidth = recoveredBloomMipWidths[i + 1];
                int lowHeight = recoveredBloomMipHeights[i + 1];
                commandBuffer.SetGlobalTexture(
                    BloomLowMipTextureId,
                    new RenderTargetIdentifier(lowMipId));
                commandBuffer.SetGlobalVector(
                    BloomBicubicParamsId,
                    new Vector4(
                        lowWidth,
                        lowHeight,
                        1.0f / lowWidth,
                        1.0f / lowHeight));
                commandBuffer.Blit(
                    RecoveredBloomMipDownIds[i],
                    RecoveredBloomMipUpIds[i],
                    postProcessMaterial,
                    3);
            }
            int reconstructedMip0Id = mipCount > 1
                ? RecoveredBloomMipUpIds[0]
                : RecoveredBloomMipDownIds[0];
            EndfieldRecoveredPostStageDiagnostic.EnqueueStageIfActive(
                commandBuffer,
                EndfieldRecoveredPostStageDiagnostic.BloomReconstructedMip0,
                new RenderTargetIdentifier(reconstructedMip0Id),
                diagnosticMip0Descriptor);

            LogRecoveredBloomGraphOnce(
                sourceWidth,
                sourceHeight,
                cappedWidth,
                cappedHeight,
                mipCount,
                serializedThreshold,
                serializedIntensity,
                serializedScatter,
                bloomScatter,
                useRecoveredGachaRoomPostProfile);
            return mipCount;
        }

        private void LogRecoveredBloomGraphOnce(
            int sourceWidth,
            int sourceHeight,
            int cappedWidth,
            int cappedHeight,
            int mipCount,
            float serializedThreshold,
            float serializedIntensity,
            float serializedScatter,
            float bloomScatter,
            bool useRecoveredGachaRoomPostProfile)
        {
            if (loggedRecoveredBloomWidth == sourceWidth &&
                loggedRecoveredBloomHeight == sourceHeight)
                return;

            loggedRecoveredBloomWidth = sourceWidth;
            loggedRecoveredBloomHeight = sourceHeight;
            string dimensions = string.Empty;
            for (int i = 0; i < mipCount; i++)
            {
                if (i > 0)
                    dimensions += ", ";
                dimensions += recoveredBloomMipWidths[i] + "x" + recoveredBloomMipHeights[i];
            }

            Debug.Log(
                "Recovered " +
                (useRecoveredGachaRoomPostProfile ? "GachaRoom" : "CharInfo") +
                " scene bloom: source=" + sourceWidth + "x" + sourceHeight +
                ", capped=" + cappedWidth + "x" + cappedHeight +
                ", mips=" + mipCount + " [" + dimensions + "]" +
                ", threshold=" + serializedThreshold.ToString("0.###") +
                ", intensity=" + serializedIntensity.ToString("0.###") +
                "->" + (Mathf.Pow(2.0f, serializedIntensity) - 1.0f).ToString("0.########") +
                ", scatter=" + serializedScatter.ToString("0.###") +
                "->" + bloomScatter.ToString("0.###") +
                ", characterBloomControl=0");
        }

        private void PrepareRecoveredMultiCharacterShadowTransport(Camera camera)
        {
            RestoreRecoveredMultiCharacterShadowTransport();
            if (camera == null)
                return;

            foreach (string actorName in new[]
                     {
                         "Wulfa",
                         "Zhuangfy",
                         "Lifeng",
                         "Mifu",
                         "Pelica",
                         "Endminm",
                         "Endminf",
                         "Chen",
                         "Wolfgd",
                         "Aglina",
                         "Aurora",
                         "Antal",
                         "Ardelia",
                         "Bounda"
                     })
            {
                if (!EndfieldRecoveredCharacterSphereBoundsDiagnostic
                        .TryComputeBoundsForActor(
                            actorName,
                            out Bounds bounds,
                            out Transform actorRoot,
                            out int resolvedSphereCount,
                            out int missingSphereCount,
                            out int secondarySphereCount))
                {
                    continue;
                }

                Renderer[] proxyRenderers = null;
                int proxyEntryCount = 0;
                Renderer[] realtimeCasterRenderers = null;
                int realtimeFalseExcludedCount = 0;
                string casterFailure;
                bool hasCasterSet =
                    recoveredOriginalRealtimeCharacterShadowCastersRequested
                        ? EndfieldRecoveredCharacterRealtimeShadowCasterProvider
                            .TryGetExactLod0Casters(
                                actorRoot,
                                actorName,
                                out realtimeCasterRenderers,
                                out realtimeFalseExcludedCount,
                                out casterFailure)
                        : EndfieldRecoveredCharacterShadowProxyProvider
                            .TryGetOrCreate(
                                actorRoot,
                                actorName,
                                out proxyRenderers,
                                out proxyEntryCount,
                                out casterFailure);
                if (!hasCasterSet)
                {
                    if (!loggedRecoveredMultiCharacterShadowAtlasFailure)
                    {
                        Debug.LogWarning(
                            "Recovered multi-character shadow atlas could not " +
                            "build the requested exact original caster set for " +
                            "actor '" + actorName + "': " + casterFailure + ".");
                        loggedRecoveredMultiCharacterShadowAtlasFailure = true;
                    }
                    RestoreRecoveredMultiCharacterShadowTransport();
                    return;
                }

                recoveredMultiCharacterShadowActors.Add(
                    new RecoveredCharacterShadowActor
                    {
                        actorName = actorName,
                        actorRoot = actorRoot,
                        bounds = bounds,
                        resolvedSphereCount = resolvedSphereCount,
                        missingSphereCount = missingSphereCount,
                        secondarySphereCount = secondarySphereCount,
                        proxyRenderers = proxyRenderers,
                        proxyEntryCount = proxyEntryCount,
                        realtimeCasterRenderers = realtimeCasterRenderers,
                        realtimeFalseExcludedCount =
                            realtimeFalseExcludedCount
                    });
            }

            recoveredMultiCharacterShadowActors.Sort(
                (left, right) =>
                    left.actorRoot.GetInstanceID().CompareTo(
                        right.actorRoot.GetInstanceID()));
            if (recoveredMultiCharacterShadowActors.Count < 2 ||
                recoveredMultiCharacterShadowActors.Count >
                    RecoveredCharacterShadowMaxAssignableSlots)
            {
                if (!loggedRecoveredMultiCharacterShadowAtlasFailure)
                {
                    Debug.LogWarning(
                        "Recovered multi-character shadow atlas requires two " +
                        "active source-backed actors and supports at most 14. " +
                        "The current source-backed diagnostic roster contains " +
                        recoveredMultiCharacterShadowActors.Count + ".");
                    loggedRecoveredMultiCharacterShadowAtlasFailure = true;
                }
                RestoreRecoveredMultiCharacterShadowTransport();
                return;
            }

            for (int actorIndex = 0;
                 actorIndex < recoveredMultiCharacterShadowActors.Count;
                 actorIndex++)
            {
                RecoveredCharacterShadowActor actor =
                    recoveredMultiCharacterShadowActors[actorIndex];
                actor.slot = actorIndex;
                uint recoveredLayer = 1u << ((actorIndex + 8) & 31);
                Renderer[] actorRenderers =
                    actor.actorRoot.GetComponentsInChildren<Renderer>(true);
                foreach (Renderer renderer in actorRenderers)
                {
                    if (renderer == null)
                        continue;
                    if (!recoveredMultiCharacterOriginalRenderingLayers
                            .ContainsKey(renderer))
                    {
                        recoveredMultiCharacterOriginalRenderingLayers.Add(
                            renderer,
                            renderer.renderingLayerMask);
                    }
                    renderer.renderingLayerMask = recoveredLayer;
                }
            }
        }

        private void RestoreRecoveredMultiCharacterShadowTransport()
        {
            foreach (
                System.Collections.Generic.KeyValuePair<Renderer, uint> pair in
                recoveredMultiCharacterOriginalRenderingLayers)
            {
                if (pair.Key != null)
                    pair.Key.renderingLayerMask = pair.Value;
            }
            recoveredMultiCharacterOriginalRenderingLayers.Clear();
            recoveredMultiCharacterShadowActors.Clear();
        }

        private EndfieldRecoveredCharacterShadowFrame RenderCharacterShadowMap(
            ScriptableRenderContext context,
            Camera camera,
            CullingResults cullingResults)
        {
            if (recoveredMultiCharacterShadowAtlasRequested)
            {
                return RenderRecoveredMultiCharacterShadowAtlas(
                    context,
                    camera,
                    cullingResults);
            }

            bool separateCharacterShadowDiagnostic =
                separateCharacterShadowDiagnosticEnabled ||
                recoveredScreenShadowMaskDiagnostic.Requested;
            if (!asset.renderCharacterShadows && !separateCharacterShadowDiagnostic)
            {
                DisableCharacterShadow(context);
                return EndfieldRecoveredCharacterShadowFrame.Unavailable(
                    "the dedicated character-shadow producer is disabled");
            }

            Bounds recoveredCharacterBounds = default;
            string recoveredBoundsActor = string.Empty;
            Transform recoveredBoundsActorRoot = null;
            int recoveredBoundsResolved = 0;
            int recoveredBoundsMissing = 0;
            int recoveredBoundsSecondary = 0;
            Renderer[] recoveredDesktopShadowProxyRenderers = null;
            int recoveredDesktopShadowProxyEntryCount = 0;
            Renderer[] recoveredOriginalRealtimeShadowCasters = null;
            int recoveredOriginalRealtimeFalseExcludedCount = 0;
            if (separateCharacterShadowDiagnostic &&
                !EndfieldRecoveredCharacterSphereBoundsDiagnostic.TryComputeBoundsForActiveActor(
                    out recoveredCharacterBounds,
                    out recoveredBoundsActor,
                    out recoveredBoundsActorRoot,
                    out recoveredBoundsResolved,
                    out recoveredBoundsMissing,
                    out recoveredBoundsSecondary))
            {
                if (!loggedSeparateCharacterShadowDiagnosticFailure)
                {
                    Debug.LogWarning(
                        "Recovered separate character-shadow diagnostic could not resolve one " +
                        "active authored sphere hierarchy. The character shadow input remains " +
                        "disabled; expected exactly one active Wulfa or Zhuangfy actor with all " +
                        "original-data sphere paths present.");
                    loggedSeparateCharacterShadowDiagnosticFailure = true;
                }
                DisableCharacterShadow(context);
                return EndfieldRecoveredCharacterShadowFrame.Unavailable(
                    "exactly one active authored Wulfa or Zhuangfy sphere hierarchy was not available");
            }
            string recoveredCasterFailure = string.Empty;
            bool recoveredCasterSetAvailable =
                !separateCharacterShadowDiagnostic ||
                (recoveredOriginalRealtimeCharacterShadowCastersRequested
                    ? EndfieldRecoveredCharacterRealtimeShadowCasterProvider
                        .TryGetExactLod0Casters(
                            recoveredBoundsActorRoot,
                            recoveredBoundsActor,
                            out recoveredOriginalRealtimeShadowCasters,
                            out recoveredOriginalRealtimeFalseExcludedCount,
                            out recoveredCasterFailure)
                    : EndfieldRecoveredCharacterShadowProxyProvider
                        .TryGetOrCreate(
                            recoveredBoundsActorRoot,
                            recoveredBoundsActor,
                            out recoveredDesktopShadowProxyRenderers,
                            out recoveredDesktopShadowProxyEntryCount,
                            out recoveredCasterFailure));
            if (!recoveredCasterSetAvailable)
            {
                if (!loggedSeparateCharacterShadowDiagnosticFailure)
                {
                    Debug.LogWarning(
                        "Recovered separate character-shadow diagnostic could " +
                        "not resolve the requested exact original caster set. " +
                        "The character shadow input remains disabled: " +
                        recoveredCasterFailure + ".");
                    loggedSeparateCharacterShadowDiagnosticFailure = true;
                }
                DisableCharacterShadow(context);
                return EndfieldRecoveredCharacterShadowFrame.Unavailable(
                    "the requested exact original character-shadow caster set " +
                    "was unavailable: " + recoveredCasterFailure);
            }

            int visibleLightIndex = -1;
            Light shadowLight = null;
            int fallbackDirectionalIndex = -1;
            Light fallbackDirectionalLight = null;
            Light preferredDiagnosticLight = null;
            if (separateCharacterShadowDiagnostic)
            {
                EndfieldHGRPCharacterLightingVolume characterVolume =
                    Object.FindObjectOfType<EndfieldHGRPCharacterLightingVolume>();
                if (characterVolume != null && characterVolume.sceneMainLight != null &&
                    characterVolume.sceneMainLight.type == LightType.Directional)
                {
                    preferredDiagnosticLight = characterVolume.sceneMainLight;
                }
            }

            var visibleLights = cullingResults.visibleLights;
            for (int i = 0; i < visibleLights.Length; i++)
            {
                Light candidate = visibleLights[i].light;
                if (candidate == null || candidate.type != LightType.Directional)
                    continue;

                if (separateCharacterShadowDiagnostic)
                {
                    if (fallbackDirectionalIndex < 0)
                    {
                        fallbackDirectionalIndex = i;
                        fallbackDirectionalLight = candidate;
                    }

                    if (preferredDiagnosticLight == null || candidate != preferredDiagnosticLight)
                        continue;
                }
                else if (candidate.shadows == LightShadows.None ||
                         candidate.shadowStrength <= 0.0f)
                {
                    continue;
                }

                visibleLightIndex = i;
                shadowLight = candidate;
                break;
            }

            if (separateCharacterShadowDiagnostic && visibleLightIndex < 0)
            {
                visibleLightIndex = fallbackDirectionalIndex;
                shadowLight = fallbackDirectionalLight;
            }

            if (visibleLightIndex < 0 || shadowLight == null)
            {
                if (separateCharacterShadowDiagnostic &&
                    !loggedSeparateCharacterShadowDiagnosticFailure)
                {
                    Debug.LogWarning(
                        "Recovered separate character-shadow diagnostic is enabled, but no " +
                        "visible directional light was available. The character shadow input " +
                        "remains disabled; scene CSM state was not changed.");
                    loggedSeparateCharacterShadowDiagnosticFailure = true;
                }
                DisableCharacterShadow(context);
                return EndfieldRecoveredCharacterShadowFrame.Unavailable(
                    "no visible directional light was available for CameraVirtualLight");
            }

            int resolution = separateCharacterShadowDiagnostic
                ? RecoveredCharacterShadowTileResolution
                : Mathf.Clamp(asset.characterShadowResolution, 256, 4096);
            Matrix4x4 viewMatrix;
            Matrix4x4 projectionMatrix;
            ShadowSplitData splitData = default;
            Vector3 recoveredShadowLightDirection = Vector3.zero;
            bool hasMatrices;
            if (separateCharacterShadowDiagnostic)
            {
                EndfieldHGRPCharacterLightingVolume characterVolume =
                    Object.FindObjectOfType<EndfieldHGRPCharacterLightingVolume>();
                hasMatrices = TryBuildRecoveredCameraVirtualLightMatrices(
                    camera,
                    recoveredCharacterBounds,
                    characterVolume,
                    out viewMatrix,
                    out projectionMatrix,
                    out recoveredShadowLightDirection);
            }
            else
            {
                hasMatrices = cullingResults.ComputeDirectionalShadowMatricesAndCullingPrimitives(
                    visibleLightIndex,
                    0,
                    1,
                    Vector3.zero,
                    resolution,
                    shadowLight.shadowNearPlane,
                    out viewMatrix,
                    out projectionMatrix,
                    out splitData);
            }
            if (!hasMatrices)
            {
                if (separateCharacterShadowDiagnostic &&
                    !loggedSeparateCharacterShadowDiagnosticFailure)
                {
                    Debug.LogWarning(
                        "Recovered separate character-shadow diagnostic selected directional " +
                        "light '" + shadowLight.name + "' (Light.shadows=" +
                        shadowLight.shadows + "), but the recovered CameraVirtualLight fit " +
                        "could not produce finite shadow matrices. " +
                        "The character shadow input remains disabled; scene CSM state was not " +
                        "changed. Exact authored sphere bounds were resolved for actor='" +
                        recoveredBoundsActor + "' center=" + recoveredCharacterBounds.center +
                        " extents=" + recoveredCharacterBounds.extents + ".");
                    loggedSeparateCharacterShadowDiagnosticFailure = true;
                }
                DisableCharacterShadow(context);
                return EndfieldRecoveredCharacterShadowFrame.Unavailable(
                    "CameraVirtualLight could not produce finite shadow matrices");
            }

            if (separateCharacterShadowDiagnostic &&
                !loggedSeparateCharacterShadowDiagnostic)
            {
                Debug.Log(
                    "Recovered separate character-shadow diagnostic enabled: light='" +
                    shadowLight.name + "', Light.shadows=" + shadowLight.shadows +
                    ", matrices=success, resolution=" + resolution +
                    ", actor='" + recoveredBoundsActor + "', sphereBoundsCenter=" +
                    recoveredCharacterBounds.center + ", sphereBoundsExtents=" +
                    recoveredCharacterBounds.extents + ", resolvedSpheres=" +
                    recoveredBoundsResolved + ", missingSpheres=" + recoveredBoundsMissing +
                    ", secondaryCandidates=" + recoveredBoundsSecondary +
                    (recoveredOriginalRealtimeCharacterShadowCastersRequested
                        ? ", originalRealtimeLod0Casters=" +
                          recoveredOriginalRealtimeShadowCasters.Length +
                          ", realtimeFalseExcluded=" +
                          recoveredOriginalRealtimeFalseExcludedCount
                        : ", desktopShadowProxies=" +
                          recoveredDesktopShadowProxyRenderers.Length + "/" +
                          recoveredDesktopShadowProxyEntryCount) +
                    ", virtualLightDirection=" + recoveredShadowLightDirection +
                    ". Scene CSM state is unchanged. The selector uses the recovered " +
                    "CameraVirtualLight (32,12) fit, exact authored sphere union, one 1024px " +
                    "atlas tile, and the requested exact source-backed caster " +
                    "membership.");
                loggedSeparateCharacterShadowDiagnostic = true;
            }

            var descriptor = new RenderTextureDescriptor(
                resolution,
                resolution,
                RenderTextureFormat.Shadowmap,
                16)
            {
                msaaSamples = 1,
                sRGB = false,
                shadowSamplingMode = ShadowSamplingMode.CompareDepths
            };

            CommandBuffer commandBuffer = new CommandBuffer { name = "Render HGCompat Character Shadow" };
            commandBuffer.GetTemporaryRT(
                CharacterShadowMapId,
                descriptor,
                FilterMode.Bilinear);
            commandBuffer.SetRenderTarget(CharacterShadowMapId);
            commandBuffer.ClearRenderTarget(true, false, Color.clear);
            commandBuffer.SetViewProjectionMatrices(viewMatrix, projectionMatrix);
            if (separateCharacterShadowDiagnostic)
            {
                // The original character-shadow pass does not consume Unity's
                // camera matrix globals. It uploads this exact device projection
                // times world-to-light matrix through ShadowVertexBuffer.
                Matrix4x4 gpuProjection = GL.GetGPUProjectionMatrix(
                    projectionMatrix,
                    true);
                commandBuffer.SetGlobalMatrix(
                    CharacterShadowPassVpId,
                    gpuProjection * viewMatrix);
                commandBuffer.SetViewport(new Rect(0.0f, 0.0f, resolution, resolution));
                commandBuffer.EnableScissorRect(
                    new Rect(1.0f, 1.0f, resolution - 2.0f, resolution - 2.0f));
                commandBuffer.EnableShaderKeyword(
                    "ENDFIELD_RECOVERED_CHARACTER_SHADOW_PASS_VP");
            }
            commandBuffer.SetGlobalDepthBias(
                separateCharacterShadowDiagnostic
                    ? RecoveredCharacterShadowHardwareDepthBias
                    : shadowLight.shadowBias,
                separateCharacterShadowDiagnostic
                    ? 0.0f
                    : shadowLight.shadowNormalBias);
            context.ExecuteCommandBuffer(commandBuffer);
            commandBuffer.Clear();

            if (separateCharacterShadowDiagnostic)
            {
                commandBuffer.SetGlobalVector(
                    WorldSpaceLightPositionId,
                    new Vector4(
                        -recoveredShadowLightDirection.x,
                        -recoveredShadowLightDirection.y,
                        -recoveredShadowLightDirection.z,
                        0.0f));
                commandBuffer.SetGlobalVector(UnityLightShadowBiasId, Vector4.zero);
                DrawRecoveredCharacterShadowCasters(
                    commandBuffer,
                    recoveredOriginalRealtimeCharacterShadowCastersRequested
                        ? recoveredOriginalRealtimeShadowCasters
                        : recoveredDesktopShadowProxyRenderers,
                    camera);
                commandBuffer.SetGlobalDepthBias(0.0f, 0.0f);
                commandBuffer.DisableShaderKeyword(
                    "ENDFIELD_RECOVERED_CHARACTER_SHADOW_PASS_VP");
                commandBuffer.DisableScissorRect();
                context.ExecuteCommandBuffer(commandBuffer);
                commandBuffer.Clear();
            }
            else
            {
                var shadowSettings = new ShadowDrawingSettings(
                    cullingResults,
                    visibleLightIndex,
                    BatchCullingProjectionType.Orthographic)
                {
                    splitData = splitData
                };
                context.DrawShadows(ref shadowSettings);
            }

            Matrix4x4 worldToShadow = ConvertToShadowTextureMatrix(
                projectionMatrix * viewMatrix);
            float texelWorldSize = Mathf.Abs(projectionMatrix.m00) > 1e-6f
                ? (2.0f / Mathf.Abs(projectionMatrix.m00)) / resolution
                : 0.0f;
            Vector4 recoveredShadowBias = separateCharacterShadowDiagnostic
                ? new Vector4(
                    texelWorldSize * RecoveredCharacterShadowShaderDepthBiasScale *
                        RecoveredCharacterShadowPcf3x3BiasScale,
                    texelWorldSize * RecoveredCharacterShadowShaderNormalBiasScale *
                        RecoveredCharacterShadowPcf3x3BiasScale,
                    texelWorldSize,
                    256.0f)
                : new Vector4(0.0f, asset.characterShadowNormalBias, 0.0f, 0.0f);
            // Retail SetupCharacterShadowReceiverConstants publishes
            // Light.shadowStrength directly in CharacterShadowParams.x. The
            // character-light volume does not add a second self-shadow scale.
            float recoveredShadowStrength = separateCharacterShadowDiagnostic
                ? shadowLight.shadowStrength
                : asset.characterShadowStrength;
            commandBuffer.SetGlobalDepthBias(0.0f, 0.0f);
            commandBuffer.SetGlobalMatrix(CharacterWorldToShadowId, worldToShadow);
            commandBuffer.SetGlobalVector(CharacterShadowBiasId, recoveredShadowBias);
            commandBuffer.SetGlobalVector(
                CharacterShadowLightDirectionId,
                new Vector4(
                    recoveredShadowLightDirection.x,
                    recoveredShadowLightDirection.y,
                    recoveredShadowLightDirection.z,
                    0.0f));
            commandBuffer.SetGlobalVector(
                CharacterShadowMultiAtlasParamsId,
                Vector4.zero);
            commandBuffer.SetGlobalVector(
                CharacterShadowAtlasTexelSizeId,
                new Vector4(
                    1.0f / resolution,
                    1.0f / resolution,
                    resolution,
                    resolution));
            commandBuffer.SetGlobalTexture(
                CharacterShadowMapId,
                new RenderTargetIdentifier(CharacterShadowMapId));
            commandBuffer.SetGlobalTexture(
                CharacterShadowRawDepthMapId,
                new RenderTargetIdentifier(CharacterShadowMapId));
            Vector4 liveForwardParams = new Vector4(
                    1.0f,
                    separateCharacterShadowDiagnostic
                        ? recoveredShadowStrength
                        : recoveredShadowStrength *
                            (shadowLight.shadows == LightShadows.None
                                ? 1.0f
                                : shadowLight.shadowStrength),
                    separateCharacterShadowDiagnostic ? 0.0f : asset.characterShadowNormalBias,
                    separateCharacterShadowDiagnostic ? 1.0f / resolution : 0.0f);
            commandBuffer.SetGlobalVector(
                CharacterShadowParamsId,
                liveForwardParams);
            context.ExecuteCommandBuffer(commandBuffer);
            commandBuffer.Release();
            return new EndfieldRecoveredCharacterShadowFrame(
                true,
                true,
                string.Empty,
                camera.GetInstanceID(),
                recoveredBoundsActorRoot,
                BuildTransformPath(recoveredBoundsActorRoot),
                CharacterShadowMapId,
                resolution,
                16,
                worldToShadow,
                recoveredShadowBias,
                recoveredShadowLightDirection,
                liveForwardParams,
                shadowLight.shadowStrength,
                "directionalLight.shadowStrength (observed provenance only; producer G is raw attenuation)");
        }

        private EndfieldRecoveredCharacterShadowFrame
            RenderRecoveredMultiCharacterShadowAtlas(
                ScriptableRenderContext context,
                Camera camera,
                CullingResults cullingResults)
        {
            if (!separateCharacterShadowDiagnosticEnabled)
            {
                DisableCharacterShadow(context);
                return EndfieldRecoveredCharacterShadowFrame.Unavailable(
                    "the multi-character atlas requires the separate character-shadow diagnostic");
            }
            if (recoveredScreenShadowMaskDiagnostic.Requested ||
                recoveredScreenDirectAudit.Requested)
            {
                DisableCharacterShadow(context);
                return EndfieldRecoveredCharacterShadowFrame.Unavailable(
                    "the multi-character atlas cannot share the scalar one-actor screen-shadow diagnostics");
            }
            int actorCount = recoveredMultiCharacterShadowActors.Count;
            if (actorCount < 2 ||
                actorCount > RecoveredCharacterShadowMaxAssignableSlots)
            {
                DisableCharacterShadow(context);
                return EndfieldRecoveredCharacterShadowFrame.Unavailable(
                    "the source-backed multi-character roster was not available before culling");
            }

            int visibleLightIndex = -1;
            Light shadowLight = null;
            int fallbackDirectionalIndex = -1;
            Light fallbackDirectionalLight = null;
            EndfieldHGRPCharacterLightingVolume characterVolume =
                Object.FindObjectOfType<EndfieldHGRPCharacterLightingVolume>();
            Light preferredLight =
                characterVolume != null &&
                characterVolume.sceneMainLight != null &&
                characterVolume.sceneMainLight.type == LightType.Directional
                    ? characterVolume.sceneMainLight
                    : null;
            var visibleLights = cullingResults.visibleLights;
            for (int lightIndex = 0;
                 lightIndex < visibleLights.Length;
                 lightIndex++)
            {
                Light candidate = visibleLights[lightIndex].light;
                if (candidate == null ||
                    candidate.type != LightType.Directional)
                {
                    continue;
                }
                if (fallbackDirectionalIndex < 0)
                {
                    fallbackDirectionalIndex = lightIndex;
                    fallbackDirectionalLight = candidate;
                }
                if (preferredLight != null && candidate != preferredLight)
                    continue;
                visibleLightIndex = lightIndex;
                shadowLight = candidate;
                break;
            }
            if (visibleLightIndex < 0)
            {
                visibleLightIndex = fallbackDirectionalIndex;
                shadowLight = fallbackDirectionalLight;
            }
            if (visibleLightIndex < 0 || shadowLight == null)
            {
                DisableCharacterShadow(context);
                return EndfieldRecoveredCharacterShadowFrame.Unavailable(
                    "no visible directional light was available for the multi-character CameraVirtualLight fits");
            }

            int columns = actorCount <= 4 ? actorCount : 4;
            int rows = actorCount <= 4
                ? 1
                : (actorCount + 3) / 4;
            int atlasWidth =
                columns * RecoveredCharacterShadowTileResolution;
            int atlasHeight =
                rows * RecoveredCharacterShadowTileResolution;
            var viewMatrices = new Matrix4x4[actorCount];
            var projectionMatrices = new Matrix4x4[actorCount];
            var lightDirections = new Vector3[actorCount];
            var worldToShadowArray =
                new Matrix4x4[RecoveredCharacterShadowShaderArrayLength];
            var receiverBiasArray =
                new Vector4[RecoveredCharacterShadowShaderArrayLength];
            var lightDirectionArray =
                new Vector4[RecoveredCharacterShadowShaderArrayLength];
            var atlasRectArray =
                new Vector4[RecoveredCharacterShadowShaderArrayLength];
            for (int arrayIndex = 0;
                 arrayIndex < worldToShadowArray.Length;
                 arrayIndex++)
            {
                worldToShadowArray[arrayIndex] = Matrix4x4.identity;
            }

            for (int actorIndex = 0; actorIndex < actorCount; actorIndex++)
            {
                RecoveredCharacterShadowActor actor =
                    recoveredMultiCharacterShadowActors[actorIndex];
                if (!TryBuildRecoveredCameraVirtualLightMatrices(
                        camera,
                        actor.bounds,
                        characterVolume,
                        out viewMatrices[actorIndex],
                        out projectionMatrices[actorIndex],
                        out lightDirections[actorIndex]))
                {
                    DisableCharacterShadow(context);
                    return EndfieldRecoveredCharacterShadowFrame.Unavailable(
                        "CameraVirtualLight could not produce finite matrices for actor '" +
                        actor.actorName + "'");
                }

                Matrix4x4 localWorldToShadow =
                    ConvertToShadowTextureMatrix(
                        projectionMatrices[actorIndex] *
                        viewMatrices[actorIndex]);
                int tileX = actorIndex % columns;
                int tileY = actorIndex / columns;
                Matrix4x4 tileTransform = Matrix4x4.identity;
                tileTransform.m00 = 1.0f / columns;
                tileTransform.m03 = (float)tileX / columns;
                tileTransform.m11 = 1.0f / rows;
                tileTransform.m13 = (float)tileY / rows;
                worldToShadowArray[actorIndex] =
                    tileTransform * localWorldToShadow;

                float texelWorldSize =
                    Mathf.Abs(projectionMatrices[actorIndex].m00) > 1e-6f
                        ? (2.0f /
                            Mathf.Abs(
                                projectionMatrices[actorIndex].m00)) /
                            RecoveredCharacterShadowTileResolution
                        : 0.0f;
                uint recoveredLayer =
                    1u << ((actorIndex + 8) & 31);
                receiverBiasArray[actorIndex] = new Vector4(
                    texelWorldSize *
                        RecoveredCharacterShadowShaderDepthBiasScale *
                        RecoveredCharacterShadowPcf3x3BiasScale,
                    texelWorldSize *
                        RecoveredCharacterShadowShaderNormalBiasScale *
                        RecoveredCharacterShadowPcf3x3BiasScale,
                    texelWorldSize,
                    recoveredLayer);
                lightDirectionArray[actorIndex] = new Vector4(
                    lightDirections[actorIndex].x,
                    lightDirections[actorIndex].y,
                    lightDirections[actorIndex].z,
                    0.0f);
                atlasRectArray[actorIndex] = new Vector4(
                    (float)tileX / columns,
                    (float)tileY / rows,
                    1.0f / columns,
                    1.0f / rows);
            }

            var descriptor = new RenderTextureDescriptor(
                atlasWidth,
                atlasHeight,
                RenderTextureFormat.Shadowmap,
                16)
            {
                msaaSamples = 1,
                sRGB = false,
                shadowSamplingMode = ShadowSamplingMode.CompareDepths
            };
            var commandBuffer = new CommandBuffer
            {
                name =
                    "Render recovered multi-character shadow atlas"
            };
            commandBuffer.GetTemporaryRT(
                CharacterShadowMapId,
                descriptor,
                FilterMode.Bilinear);
            commandBuffer.SetRenderTarget(CharacterShadowMapId);
            commandBuffer.ClearRenderTarget(true, false, Color.clear);
            commandBuffer.EnableShaderKeyword(
                "ENDFIELD_RECOVERED_CHARACTER_SHADOW_PASS_VP");
            commandBuffer.SetGlobalVector(
                UnityLightShadowBiasId,
                Vector4.zero);
            commandBuffer.SetGlobalDepthBias(
                RecoveredCharacterShadowHardwareDepthBias,
                0.0f);

            for (int actorIndex = 0; actorIndex < actorCount; actorIndex++)
            {
                int tileX =
                    (actorIndex % columns) *
                    RecoveredCharacterShadowTileResolution;
                int tileY =
                    (actorIndex / columns) *
                    RecoveredCharacterShadowTileResolution;
                commandBuffer.SetRenderTarget(CharacterShadowMapId);
                commandBuffer.SetViewProjectionMatrices(
                    viewMatrices[actorIndex],
                    projectionMatrices[actorIndex]);
                commandBuffer.SetGlobalMatrix(
                    CharacterShadowPassVpId,
                    GL.GetGPUProjectionMatrix(
                        projectionMatrices[actorIndex],
                        true) *
                    viewMatrices[actorIndex]);
                commandBuffer.SetViewport(
                    new Rect(
                        tileX,
                        tileY,
                        RecoveredCharacterShadowTileResolution,
                        RecoveredCharacterShadowTileResolution));
                commandBuffer.EnableScissorRect(
                    new Rect(
                        tileX + 1,
                        tileY + 1,
                        RecoveredCharacterShadowTileResolution - 2,
                        RecoveredCharacterShadowTileResolution - 2));
                Vector3 lightDirection =
                    lightDirections[actorIndex];
                commandBuffer.SetGlobalVector(
                    WorldSpaceLightPositionId,
                    new Vector4(
                        -lightDirection.x,
                        -lightDirection.y,
                        -lightDirection.z,
                        0.0f));
                DrawRecoveredCharacterShadowCasters(
                    commandBuffer,
                    recoveredOriginalRealtimeCharacterShadowCastersRequested
                        ? recoveredMultiCharacterShadowActors[actorIndex]
                            .realtimeCasterRenderers
                        : recoveredMultiCharacterShadowActors[actorIndex]
                            .proxyRenderers,
                    camera);
            }

            commandBuffer.SetGlobalDepthBias(0.0f, 0.0f);
            commandBuffer.DisableShaderKeyword(
                "ENDFIELD_RECOVERED_CHARACTER_SHADOW_PASS_VP");
            commandBuffer.DisableScissorRect();
            commandBuffer.SetGlobalMatrixArray(
                CharacterWorldToShadowArrayId,
                worldToShadowArray);
            commandBuffer.SetGlobalVectorArray(
                CharacterShadowBiasArrayId,
                receiverBiasArray);
            commandBuffer.SetGlobalVectorArray(
                CharacterShadowLightDirectionArrayId,
                lightDirectionArray);
            commandBuffer.SetGlobalVectorArray(
                CharacterShadowAtlasRectArrayId,
                atlasRectArray);
            commandBuffer.SetGlobalVector(
                CharacterShadowMultiAtlasParamsId,
                new Vector4(1.0f, actorCount, columns, rows));
            commandBuffer.SetGlobalVector(
                CharacterShadowAtlasTexelSizeId,
                new Vector4(
                    1.0f / atlasWidth,
                    1.0f / atlasHeight,
                    atlasWidth,
                    atlasHeight));
            commandBuffer.SetGlobalMatrix(
                CharacterWorldToShadowId,
                worldToShadowArray[0]);
            commandBuffer.SetGlobalVector(
                CharacterShadowBiasId,
                receiverBiasArray[0]);
            commandBuffer.SetGlobalVector(
                CharacterShadowLightDirectionId,
                lightDirectionArray[0]);
            commandBuffer.SetGlobalTexture(
                CharacterShadowMapId,
                new RenderTargetIdentifier(CharacterShadowMapId));
            commandBuffer.SetGlobalTexture(
                CharacterShadowRawDepthMapId,
                new RenderTargetIdentifier(CharacterShadowMapId));
            Vector4 liveForwardParams = new Vector4(
                1.0f,
                shadowLight.shadowStrength,
                0.0f,
                1.0f / atlasWidth);
            commandBuffer.SetGlobalVector(
                CharacterShadowParamsId,
                liveForwardParams);
            context.ExecuteCommandBuffer(commandBuffer);
            commandBuffer.Release();

            if (!loggedRecoveredMultiCharacterShadowAtlas)
            {
                string slots = string.Empty;
                for (int actorIndex = 0;
                     actorIndex < actorCount;
                     actorIndex++)
                {
                    RecoveredCharacterShadowActor actor =
                        recoveredMultiCharacterShadowActors[actorIndex];
                    if (actorIndex > 0)
                        slots += ", ";
                    slots +=
                        actorIndex + ":" + actor.actorName +
                        "(instanceID=" +
                        actor.actorRoot.GetInstanceID() +
                        ",layer=" +
                        (1u << ((actorIndex + 8) & 31));
                    if (recoveredOriginalRealtimeCharacterShadowCastersRequested)
                    {
                        slots +=
                            ",realtimeLod0Casters=" +
                            actor.realtimeCasterRenderers.Length +
                            ",realtimeFalseExcluded=" +
                            actor.realtimeFalseExcludedCount + ")";
                    }
                    else
                    {
                        slots +=
                            ",proxies=" +
                            actor.proxyRenderers.Length + "/" +
                            actor.proxyEntryCount + ")";
                    }
                }
                Debug.Log(
                    "Recovered multi-character shadow atlas active " +
                    "(default-off): count=" + actorCount +
                    ", grid=" + columns + "x" + rows +
                    ", atlas=" + atlasWidth + "x" + atlasHeight +
                    ", tile=1024, D16, slots=[" + slots +
                    "]. Ordering is priority 100 descending then " +
                    "GetInstanceID ascending; renderer transport uses the " +
                    "exact 1<<((slot+8)&31) rendering-layer carrier. Caster " +
                    "membership=" +
                    (recoveredOriginalRealtimeCharacterShadowCastersRequested
                        ? "original regular LOD0 m_RealtimeShadowCaster=1 " +
                          "rows; mode-3/4 proxies remain invalid index 15"
                        : "legacy recovered retail desktop proxy probe") +
                    ".");
                loggedRecoveredMultiCharacterShadowAtlas = true;
            }

            RecoveredCharacterShadowActor firstActor =
                recoveredMultiCharacterShadowActors[0];
            return new EndfieldRecoveredCharacterShadowFrame(
                true,
                true,
                string.Empty,
                camera.GetInstanceID(),
                firstActor.actorRoot,
                BuildTransformPath(firstActor.actorRoot),
                CharacterShadowMapId,
                atlasWidth,
                16,
                worldToShadowArray[0],
                receiverBiasArray[0],
                lightDirections[0],
                liveForwardParams,
                shadowLight.shadowStrength,
                "directionalLight.shadowStrength; multi-character rendering-layer transport");
        }

        private static bool TryBuildRecoveredCameraVirtualLightMatrices(
            Camera camera,
            Bounds bounds,
            EndfieldHGRPCharacterLightingVolume characterVolume,
            out Matrix4x4 viewMatrix,
            out Matrix4x4 projectionMatrix,
            out Vector3 lightDirection)
        {
            viewMatrix = Matrix4x4.identity;
            projectionMatrix = Matrix4x4.identity;
            lightDirection = Vector3.zero;
            if (camera == null || bounds.size.sqrMagnitude <= 1e-8f)
                return false;

            Vector3 cameraForward = camera.transform.forward;
            if (cameraForward.sqrMagnitude <= 1e-8f)
                return false;

            Vector3 cameraEuler = Quaternion.LookRotation(cameraForward, Vector3.up).eulerAngles;
            float signedPitch = cameraEuler.x > 180.0f
                ? cameraEuler.x - 360.0f
                : cameraEuler.x;
            Vector2 cameraFollowBias = characterVolume != null
                ? characterVolume.cameraFollowLightBias
                : new Vector2(32.0f, 12.0f);
            Quaternion virtualLightRotation = Quaternion.Euler(
                Mathf.Max(cameraFollowBias.x, signedPitch),
                cameraEuler.y + cameraFollowBias.y,
                0.0f);

            lightDirection = (virtualLightRotation * Vector3.forward).normalized;
            Vector3 rotatedUp = (virtualLightRotation * Vector3.up).normalized;
            Vector3 extents = bounds.extents;
            float supportDistance = extents.magnitude;
            Vector3 lightPosition = bounds.center - lightDirection * supportDistance;

            Matrix4x4 firstWorldToLight = Matrix4x4.TRS(
                lightPosition,
                virtualLightRotation,
                Vector3.one).inverse;
            Vector3 minimum = new Vector3(float.PositiveInfinity, float.PositiveInfinity, float.PositiveInfinity);
            Vector3 maximum = new Vector3(float.NegativeInfinity, float.NegativeInfinity, float.NegativeInfinity);
            for (int cornerIndex = 0; cornerIndex < 8; cornerIndex++)
            {
                Vector3 corner = bounds.center + Vector3.Scale(
                    extents,
                    new Vector3(
                        (cornerIndex & 1) == 0 ? -1.0f : 1.0f,
                        (cornerIndex & 2) == 0 ? -1.0f : 1.0f,
                        (cornerIndex & 4) == 0 ? -1.0f : 1.0f));
                Vector3 lightSpaceCorner = firstWorldToLight.MultiplyPoint(corner);
                minimum = Vector3.Min(minimum, lightSpaceCorner);
                maximum = Vector3.Max(maximum, lightSpaceCorner);
            }

            Vector3 rotatedRight = virtualLightRotation * Vector3.right;
            lightPosition += rotatedRight * ((minimum.x + maximum.x) * 0.5f);
            lightPosition += rotatedUp * ((minimum.y + maximum.y) * 0.5f);
            Quaternion fittedRotation = Quaternion.LookRotation(-lightDirection, rotatedUp);
            viewMatrix = Matrix4x4.TRS(lightPosition, fittedRotation, Vector3.one).inverse;

            float width = maximum.x - minimum.x;
            float height = maximum.y - minimum.y;
            float nearPlane = minimum.z;
            float farPlane = maximum.z;
            if (!IsFinite(width) || !IsFinite(height) || !IsFinite(nearPlane) || !IsFinite(farPlane) ||
                width <= 1e-5f || height <= 1e-5f || farPlane - nearPlane <= 1e-5f)
                return false;

            Matrix4x4 cpuProjection = Matrix4x4.Ortho(
                -width * 0.5f,
                width * 0.5f,
                -height * 0.5f,
                height * 0.5f,
                nearPlane,
                farPlane);
            // Preserve the logical projection as the shared source of truth.
            // The caster path converts it with GL.GetGPUProjectionMatrix(...,
            // true) before upload, while ConvertToShadowTextureMatrix applies
            // the original receiver's independent reversed-Z transform.
            projectionMatrix = cpuProjection;
            return IsFinite(viewMatrix) && IsFinite(projectionMatrix);
        }

        private static void DrawRecoveredCharacterShadowCasters(
            CommandBuffer commandBuffer,
            Renderer[] renderers,
            Camera camera)
        {
            if (renderers == null)
                return;

            foreach (Renderer renderer in renderers)
            {
                if (renderer == null || !renderer.enabled || !renderer.gameObject.activeInHierarchy)
                    continue;
                if ((camera.cullingMask & (1 << renderer.gameObject.layer)) == 0)
                    continue;

                Material[] materials = renderer.sharedMaterials;
                for (int submesh = 0; submesh < materials.Length; submesh++)
                {
                    Material material = materials[submesh];
                    if (material == null)
                        continue;
                    int shadowCasterPass = material.FindPass("SHADOWCASTER");
                    if (shadowCasterPass >= 0)
                        commandBuffer.DrawRenderer(renderer, material, submesh, shadowCasterPass);
                }
            }
        }

        private static string BuildTransformPath(Transform transform)
        {
            if (transform == null)
                return string.Empty;
            var names = new System.Collections.Generic.Stack<string>();
            Transform current = transform;
            while (current != null)
            {
                names.Push(current.name);
                current = current.parent;
            }
            return string.Join("/", names.ToArray());
        }

        private static bool IsFinite(float value)
        {
            return !float.IsNaN(value) && !float.IsInfinity(value);
        }

        private static bool IsFinite(Matrix4x4 matrix)
        {
            for (int i = 0; i < 16; i++)
            {
                if (!IsFinite(matrix[i]))
                    return false;
            }
            return true;
        }

        private EndfieldRecoveredCharInfoAutoExposureCameraState
            PrepareRecoveredLiveCharInfoAutoExposure(
                Camera camera,
                bool applyPostProcess,
                bool useRecoveredPostSemantics,
                bool useRecoveredGachaManualExposure)
        {
            EndfieldRecoveredCharInfoAutoExposureCameraState state;
            recoveredLiveCharInfoAutoExposureStates.TryGetValue(camera, out state);
            float deltaTime = Time.deltaTime;

            // Env_gachaRoom_01 selects Manual zero EV with symmetric 0.6/0.6
            // adaptation. Installed retail samples scaled Time.deltaTime while
            // preparing the pass, carries the physical HGCamera's current and
            // target values through ExecuteAutoExposure, then commits the
            // clamped Lerp result back to that same camera. Keep this state
            // alive even though its exact neutral lab startup remains 1. The
            // opt-in histogram diagnostic below is a separate Auto-mode lane.
            if (!recoveredLiveCharInfoAutoExposureRequested)
            {
                // Do not leak the Gacha-specific profile into scene, preview,
                // reflection, or unrelated operator cameras. The recovered
                // sceneMV request admits only cameras currently rendering the
                // selected entrance's VFX consumers, while the camera-local
                // operator presentation marks the physical recovery camera.
                if (!useRecoveredGachaManualExposure)
                    return null;
                if (state == null)
                {
                    state = new EndfieldRecoveredCharInfoAutoExposureCameraState();
                    recoveredLiveCharInfoAutoExposureStates.Add(camera, state);
                }
                state.AdvanceGachaRoom(deltaTime);
                return state;
            }

            string failure = null;
            if (!applyPostProcess)
            {
                failure = "the HG compatibility post process is disabled";
            }
            else if (!useRecoveredPostSemantics)
            {
                failure =
                    "ENDFIELD_RECOVERED_POST_SEMANTICS is disabled, so the " +
                    "matching Uber pre-exposure undo is unavailable";
            }
            else if (recoveredLiveCharInfoAutoExposureCompute == null ||
                     recoveredLiveCharInfoAutoExposureKernel < 0)
            {
                failure =
                    $"Resources/{LiveCharInfoAutoExposureComputeResource}.compute " +
                    "or its HGLuminanceHistogramCS kernel is unavailable";
            }
            else if (!SystemInfo.supportsComputeShaders)
            {
                failure = "the active graphics device does not support compute shaders";
            }
            else if (!SystemInfo.supportsAsyncGPUReadback)
            {
                failure =
                    "the active graphics device does not support asynchronous GPU readback";
            }

            if (failure != null)
            {
                if (state != null)
                    state.AdvanceInactive(deltaTime);
                if (!loggedRecoveredLiveCharInfoAutoExposureFailure)
                {
                    Debug.LogWarning(
                        "Recovered HGRP Auto-mode histogram diagnostic was requested but remains " +
                        $"neutral/inactive for camera '{camera.name}': {failure}. No " +
                        "synchronous readback or fixed-EV fallback is substituted.");
                    loggedRecoveredLiveCharInfoAutoExposureFailure = true;
                }
                return null;
            }

            if (state == null)
            {
                state = new EndfieldRecoveredCharInfoAutoExposureCameraState();
                recoveredLiveCharInfoAutoExposureStates.Add(camera, state);
            }

            state.Advance(deltaTime, Time.frameCount);
            if (!loggedRecoveredLiveCharInfoAutoExposure)
            {
                Debug.Log(
                    "Recovered HGRP Auto-mode histogram diagnostic active (not selected " +
                    "by the original CharInfo Manual profile): per-camera neutral " +
                    "startup, exact 16-bin center histogram, 5%-95% native reduction, " +
                    "[-4,+4] EV clamps, 20/20 adaptation, and _ExposureParams=(current,0,0,0). " +
                    "One Unity AsyncGPUReadback is allowed in flight. Its actual callback " +
                    "latency is measured rather than claimed to match the proprietary " +
                    "render-graph scheduler.");
                loggedRecoveredLiveCharInfoAutoExposure = true;
            }
            if (state.ConsumedHistogramThisFrame && !state.LoggedFirstHistogram)
            {
                Debug.Log(
                    $"Recovered HGRP Auto-mode diagnostic first histogram for '{camera.name}': " +
                    $"averageEV={state.LastAverageEV:0.######}, " +
                    $"target={state.TargetExposure:0.######}, " +
                    $"current={state.CurrentExposure:0.######}, " +
                    $"GPU/readback latency={state.LastReadbackLatencyFrames} frame(s).");
                state.LoggedFirstHistogram = true;
            }
            return state;
        }

        private void EnqueueRecoveredLiveCharInfoHistogram(
            CommandBuffer commandBuffer,
            Camera camera,
            EndfieldRecoveredCharInfoAutoExposureCameraState state,
            int width,
            int height)
        {
            if (state.ReadbackPending)
                return;

            int threadGroupsX = Mathf.CeilToInt(
                width /
                (float)EndfieldRecoveredCharInfoAutoExposure.DispatchCoverage);
            int threadGroupsY = Mathf.CeilToInt(
                height /
                (float)EndfieldRecoveredCharInfoAutoExposure.DispatchCoverage);
            string bufferFailure;
            if (!state.PrepareHistogramBuffer(
                    threadGroupsX,
                    threadGroupsY,
                    out bufferFailure))
            {
                if (!loggedRecoveredLiveCharInfoAutoExposureDispatchFailure)
                {
                    Debug.LogWarning(
                        "Recovered HGRP Auto-mode diagnostic histogram dispatch was skipped for " +
                        $"camera '{camera.name}': {bufferFailure}.");
                    loggedRecoveredLiveCharInfoAutoExposureDispatchFailure = true;
                }
                return;
            }

            commandBuffer.SetComputeTextureParam(
                recoveredLiveCharInfoAutoExposureCompute,
                recoveredLiveCharInfoAutoExposureKernel,
                AutoExposureSourceId,
                new RenderTargetIdentifier(CameraColorId));
            commandBuffer.SetComputeBufferParam(
                recoveredLiveCharInfoAutoExposureCompute,
                recoveredLiveCharInfoAutoExposureKernel,
                AutoExposureHistogramBufferId,
                state.HistogramBuffer);
            commandBuffer.SetComputeIntParam(
                recoveredLiveCharInfoAutoExposureCompute,
                AutoExposureTextureWidthId,
                width);
            commandBuffer.SetComputeIntParam(
                recoveredLiveCharInfoAutoExposureCompute,
                AutoExposureTextureHeightId,
                height);
            commandBuffer.SetComputeIntParam(
                recoveredLiveCharInfoAutoExposureCompute,
                AutoExposureThreadGroupsXId,
                threadGroupsX);
            commandBuffer.SetComputeIntParam(
                recoveredLiveCharInfoAutoExposureCompute,
                AutoExposureThreadGroupsYId,
                threadGroupsY);
            commandBuffer.SetComputeIntParam(
                recoveredLiveCharInfoAutoExposureCompute,
                AutoExposureSampleStrideId,
                EndfieldRecoveredCharInfoAutoExposure.HistogramTileSize);
            commandBuffer.SetComputeFloatParam(
                recoveredLiveCharInfoAutoExposureCompute,
                AutoExposureMinEVId,
                EndfieldRecoveredCharInfoAutoExposure.ExposureRangeMinEV);
            commandBuffer.SetComputeFloatParam(
                recoveredLiveCharInfoAutoExposureCompute,
                AutoExposureMaxEVId,
                EndfieldRecoveredCharInfoAutoExposure.ExposureRangeMaxEV);
            commandBuffer.SetComputeFloatParam(
                recoveredLiveCharInfoAutoExposureCompute,
                AutoExposureCenterPixelWeightId,
                EndfieldRecoveredCharInfoAutoExposure.CenterPixelWeight);
            commandBuffer.DispatchCompute(
                recoveredLiveCharInfoAutoExposureCompute,
                recoveredLiveCharInfoAutoExposureKernel,
                threadGroupsX,
                threadGroupsY,
                1);

            int expectedElementCount = state.HistogramElementCount;
            int dispatchFrame = Time.frameCount;
            string cameraName = camera.name;
            commandBuffer.RequestAsyncReadback(
                state.HistogramBuffer,
                request =>
                {
                    string readbackFailure;
                    if (!state.CompleteReadback(
                            request,
                            expectedElementCount,
                            threadGroupsX,
                            threadGroupsY,
                            dispatchFrame,
                            out readbackFailure))
                    {
                        Debug.LogWarning(
                            "Recovered live CharInfo histogram readback failed for " +
                            $"camera '{cameraName}': {readbackFailure}.");
                    }
                });
            state.MarkReadbackPending(dispatchFrame);
        }

        private static bool ShouldEnqueueRecoveredAutoHistogram(
            bool autoHistogramRequested,
            bool autoHistogramComputeReady,
            bool exposureStateAvailable)
        {
            // The persistent Gacha-room Manual recurrence intentionally returns
            // a camera state so Uber can undo the same current exposure value.
            // It does not own the separate default-off Auto histogram lane.
            return autoHistogramRequested &&
                autoHistogramComputeReady &&
                exposureStateAvailable;
        }

        public static bool IsRecoveredLiveCharInfoAutoExposureRequested()
        {
            bool enabled = IsEnabledSelectorValue(
                System.Environment.GetEnvironmentVariable(
                    LiveCharInfoAutoExposureEnvironmentVariable));

            string[] arguments = System.Environment.GetCommandLineArgs();
            for (int i = 0; i < arguments.Length; i++)
            {
                string argument = arguments[i];
                if (string.Equals(
                    argument,
                    LiveCharInfoAutoExposureCommandLineArgument,
                    System.StringComparison.OrdinalIgnoreCase))
                {
                    enabled = true;
                    continue;
                }

                string prefix = LiveCharInfoAutoExposureCommandLineArgument + "=";
                if (argument.StartsWith(prefix, System.StringComparison.OrdinalIgnoreCase))
                    enabled = IsEnabledSelectorValue(argument.Substring(prefix.Length));
            }

            return enabled;
        }

        private static bool IsSeparateCharacterShadowDiagnosticEnabled()
        {
            bool enabled = IsEnabledSelectorValue(
                System.Environment.GetEnvironmentVariable(
                    SeparateCharacterShadowEnvironmentVariable));

            string[] arguments = System.Environment.GetCommandLineArgs();
            for (int i = 0; i < arguments.Length; i++)
            {
                string argument = arguments[i];
                if (string.Equals(
                    argument,
                    SeparateCharacterShadowCommandLineArgument,
                    System.StringComparison.OrdinalIgnoreCase))
                {
                    enabled = true;
                    continue;
                }

                string prefix = SeparateCharacterShadowCommandLineArgument + "=";
                if (argument.StartsWith(prefix, System.StringComparison.OrdinalIgnoreCase))
                    enabled = IsEnabledSelectorValue(argument.Substring(prefix.Length));
            }

            return enabled;
        }

        public static bool IsRecoveredMultiCharacterShadowAtlasRequested()
        {
            bool enabled = IsEnabledSelectorValue(
                System.Environment.GetEnvironmentVariable(
                    MultiCharacterShadowAtlasEnvironmentVariable));

            string[] arguments = System.Environment.GetCommandLineArgs();
            for (int i = 0; i < arguments.Length; i++)
            {
                string argument = arguments[i];
                if (string.Equals(
                    argument,
                    MultiCharacterShadowAtlasCommandLineArgument,
                    System.StringComparison.OrdinalIgnoreCase))
                {
                    enabled = true;
                    continue;
                }

                string prefix =
                    MultiCharacterShadowAtlasCommandLineArgument + "=";
                if (argument.StartsWith(
                        prefix,
                        System.StringComparison.OrdinalIgnoreCase))
                {
                    enabled = IsEnabledSelectorValue(
                        argument.Substring(prefix.Length));
                }
            }

            return enabled;
        }

        public static bool
            IsRecoveredOriginalRealtimeCharacterShadowCastersRequested()
        {
            bool enabled = IsEnabledSelectorValue(
                System.Environment.GetEnvironmentVariable(
                    OriginalRealtimeCharacterShadowCastersEnvironmentVariable));

            string[] arguments = System.Environment.GetCommandLineArgs();
            for (int i = 0; i < arguments.Length; i++)
            {
                string argument = arguments[i];
                if (string.Equals(
                        argument,
                        OriginalRealtimeCharacterShadowCastersCommandLineArgument,
                        System.StringComparison.OrdinalIgnoreCase))
                {
                    enabled = true;
                    continue;
                }

                string prefix =
                    OriginalRealtimeCharacterShadowCastersCommandLineArgument +
                    "=";
                if (argument.StartsWith(
                        prefix,
                        System.StringComparison.OrdinalIgnoreCase))
                {
                    enabled = IsEnabledSelectorValue(
                        argument.Substring(prefix.Length));
                }
            }

            return enabled;
        }

        public static bool IsRecoveredLinearUnormFinalTargetRequested()
        {
            bool enabled = IsEnabledSelectorValue(
                System.Environment.GetEnvironmentVariable(
                    LinearUnormFinalTargetEnvironmentVariable));

            string[] arguments = System.Environment.GetCommandLineArgs();
            for (int i = 0; i < arguments.Length; i++)
            {
                string argument = arguments[i];
                if (string.Equals(
                    argument,
                    LinearUnormFinalTargetCommandLineArgument,
                    System.StringComparison.OrdinalIgnoreCase))
                {
                    enabled = true;
                    continue;
                }

                string prefix = LinearUnormFinalTargetCommandLineArgument + "=";
                if (argument.StartsWith(prefix, System.StringComparison.OrdinalIgnoreCase))
                    enabled = IsEnabledSelectorValue(argument.Substring(prefix.Length));
            }

            return enabled;
        }

        private static bool TryValidateRecoveredLinearUnormFinalTarget(
            Camera camera,
            int width,
            int height,
            out string failure)
        {
            failure = null;
            RenderTexture target = camera != null ? camera.targetTexture : null;
            if (target == null)
            {
                failure = "camera.targetTexture is null, so the screen backbuffer format/write state is not proven";
                return false;
            }

            if (!target.IsCreated())
            {
                failure = "camera target has not created its GPU resource";
                return false;
            }

            if (target.graphicsFormat != GraphicsFormat.R8G8B8A8_UNorm || target.sRGB)
            {
                failure =
                    $"camera target is {target.graphicsFormat} (sRGB={target.sRGB}), not linear " +
                    "GraphicsFormat.R8G8B8A8_UNorm";
                return false;
            }

            if (target.width != width || target.height != height)
            {
                failure =
                    $"camera target size {target.width}x{target.height} does not match the " +
                    $"{width}x{height} post viewport";
                return false;
            }

            if (target.antiAliasing != 1 || target.dimension != TextureDimension.Tex2D ||
                target.volumeDepth != 1 || target.useMipMap || target.mipmapCount != 1)
            {
                failure =
                    $"camera target topology is MSAA {target.antiAliasing}, {target.dimension}, " +
                    $"depth {target.volumeDepth}, mips {target.mipmapCount}; exact presentation " +
                    "requires one non-MSAA Texture2D slice with one mip";
                return false;
            }

            if ((SystemInfo.copyTextureSupport & CopyTextureSupport.Basic) == 0)
            {
                failure = "the active graphics device does not report basic GPU CopyTexture support";
                return false;
            }

            if (!SystemInfo.IsFormatSupported(
                GraphicsFormat.R8G8B8A8_UNorm,
                FormatUsage.Render))
            {
                failure = "the active graphics device cannot render to R8G8B8A8_UNorm";
                return false;
            }

            return true;
        }

        private static bool IsEnabledSelectorValue(string rawValue)
        {
            if (string.IsNullOrWhiteSpace(rawValue))
                return false;

            string normalized = rawValue.Trim();
            return string.Equals(normalized, "1", System.StringComparison.OrdinalIgnoreCase) ||
                   string.Equals(normalized, "true", System.StringComparison.OrdinalIgnoreCase) ||
                   string.Equals(normalized, "yes", System.StringComparison.OrdinalIgnoreCase) ||
                   string.Equals(normalized, "on", System.StringComparison.OrdinalIgnoreCase);
        }

        private static Matrix4x4 ConvertToShadowTextureMatrix(Matrix4x4 matrix)
        {
            if (SystemInfo.usesReversedZBuffer)
            {
                matrix.m20 = -matrix.m20;
                matrix.m21 = -matrix.m21;
                matrix.m22 = -matrix.m22;
                matrix.m23 = -matrix.m23;
            }

            Matrix4x4 result = matrix;
            result.m00 = 0.5f * (matrix.m00 + matrix.m30);
            result.m01 = 0.5f * (matrix.m01 + matrix.m31);
            result.m02 = 0.5f * (matrix.m02 + matrix.m32);
            result.m03 = 0.5f * (matrix.m03 + matrix.m33);
            result.m10 = 0.5f * (matrix.m10 + matrix.m30);
            result.m11 = 0.5f * (matrix.m11 + matrix.m31);
            result.m12 = 0.5f * (matrix.m12 + matrix.m32);
            result.m13 = 0.5f * (matrix.m13 + matrix.m33);
            result.m20 = 0.5f * (matrix.m20 + matrix.m30);
            result.m21 = 0.5f * (matrix.m21 + matrix.m31);
            result.m22 = 0.5f * (matrix.m22 + matrix.m32);
            result.m23 = 0.5f * (matrix.m23 + matrix.m33);
            return result;
        }

        private static void DisableCharacterShadow(ScriptableRenderContext context)
        {
            CommandBuffer commandBuffer = new CommandBuffer { name = "Disable HGCompat Character Shadow" };
            SetCharacterShadowUnavailableGlobals(commandBuffer);
            context.ExecuteCommandBuffer(commandBuffer);
            commandBuffer.Release();
        }

        private static void SetCharacterShadowUnavailableGlobals(
            CommandBuffer commandBuffer)
        {
            commandBuffer.SetGlobalTexture(CharacterShadowMapId, Texture2D.whiteTexture);
            commandBuffer.SetGlobalTexture(CharacterShadowRawDepthMapId, Texture2D.whiteTexture);
            commandBuffer.SetGlobalVector(CharacterShadowParamsId, Vector4.zero);
            commandBuffer.SetGlobalVector(CharacterShadowBiasId, Vector4.zero);
            commandBuffer.SetGlobalVector(CharacterShadowLightDirectionId, Vector4.zero);
            commandBuffer.SetGlobalVector(
                CharacterShadowMultiAtlasParamsId,
                Vector4.zero);
            commandBuffer.SetGlobalVector(
                CharacterShadowAtlasTexelSizeId,
                Vector4.zero);
        }

        private static void DrawManualPassFallback(ScriptableRenderContext context, Camera camera)
        {
            CommandBuffer commandBuffer = new CommandBuffer { name = "HGCompat Manual Pass Fallback" };
            Renderer[] renderers = Object.FindObjectsOfType<Renderer>();

            foreach (Renderer renderer in renderers)
            {
                if (renderer == null || !renderer.enabled || !renderer.gameObject.activeInHierarchy)
                    continue;
                if ((camera.cullingMask & (1 << renderer.gameObject.layer)) == 0)
                    continue;

                Material[] materials = renderer.sharedMaterials;
                for (int submesh = 0; submesh < materials.Length; submesh++)
                {
                    Material material = materials[submesh];
                    if (material == null || material.passCount == 0 || !NeedsManualPassFallback(material.shader))
                        continue;

                    for (int pass = 0; pass < material.passCount; pass++)
                        commandBuffer.DrawRenderer(renderer, material, submesh, pass);
                }
            }

            context.ExecuteCommandBuffer(commandBuffer);
            commandBuffer.Release();
        }

        private static void DrawRecoveredAuxiliaryPasses(
            ScriptableRenderContext context,
            Camera camera,
            string passName)
        {
            DrawRecoveredAuxiliaryPasses(
                context,
                camera,
                passName,
                default(RenderTargetIdentifier),
                null,
                null);
        }

        private static void DrawRecoveredAuxiliaryPasses(
            ScriptableRenderContext context,
            Camera camera,
            string passName,
            RenderTargetIdentifier colorTarget,
            RenderTexture sceneMV,
            RenderTexture depth)
        {
            CommandBuffer commandBuffer = new CommandBuffer
            {
                name = "HGCompat Recovered " + passName
            };
            bool bindSceneMVMrt = sceneMV != null && depth != null;
            if (bindSceneMVMrt)
            {
                commandBuffer.SetRenderTarget(
                    new[]
                    {
                        colorTarget,
                        new RenderTargetIdentifier(sceneMV)
                    },
                    new RenderTargetIdentifier(depth));
            }
            Renderer[] renderers = Object.FindObjectsOfType<Renderer>();

            foreach (Renderer renderer in renderers)
            {
                if (renderer == null || !renderer.enabled || !renderer.gameObject.activeInHierarchy)
                    continue;
                if ((camera.cullingMask & (1 << renderer.gameObject.layer)) == 0)
                    continue;

                Material[] materials = renderer.sharedMaterials;
                for (int submesh = 0; submesh < materials.Length; submesh++)
                {
                    Material material = materials[submesh];
                    if (material == null || material.shader == null ||
                        !material.shader.name.StartsWith("Endfield/Recovered/"))
                        continue;

                    int pass = material.FindPass(passName);
                    if (pass >= 0)
                        commandBuffer.DrawRenderer(renderer, material, submesh, pass);
                }
            }

            if (bindSceneMVMrt)
                commandBuffer.SetRenderTarget(colorTarget, depth);

            context.ExecuteCommandBuffer(commandBuffer);
            commandBuffer.Release();
        }

        private static bool NeedsManualPassFallback(Shader shader)
        {
            if (shader == null)
                return false;

            return shader.name.StartsWith("HGRP/") || shader.name.StartsWith("Endfield/Preview/");
        }

        private static bool TryResolveRecoveredVFXPlayerCenter(
            out Transform playerCenter)
        {
            if (CharacterRecoveryViewerUI.TryGetSelectedActorRoot(out playerCenter))
                return true;

            playerCenter = null;
            CharacterRecoveryRig[] rigs =
                Object.FindObjectsOfType<CharacterRecoveryRig>();
            for (int i = 0; i < rigs.Length; i++)
            {
                CharacterRecoveryRig rig = rigs[i];
                if (rig == null || !rig.gameObject.activeInHierarchy)
                    continue;
                if (playerCenter != null && playerCenter != rig.transform)
                {
                    playerCenter = null;
                    return false;
                }
                playerCenter = rig.transform;
            }
            return playerCenter != null;
        }

        private void DrawRenderers(
            ScriptableRenderContext context,
            Camera camera,
            CullingResults cullingResults,
            RenderQueueRange queueRange,
            SortingCriteria sortingCriteria,
            int layerMask = -1,
            ShaderTagId[] shaderPasses = null)
        {
            shaderPasses = shaderPasses ?? OpaqueShaderPasses;
            SortingSettings sortingSettings = new SortingSettings(camera) { criteria = sortingCriteria };
            DrawingSettings drawingSettings = new DrawingSettings(shaderPasses[0], sortingSettings)
            {
                enableDynamicBatching = asset.dynamicBatching,
                enableInstancing = asset.gpuInstancing,
                // Retail HGRenderPipeline.GetPerObjectDataConfig delegates to
                // GetPerObjectMotionVectorConfig, which returns exactly
                // PerObjectData.MotionVectors (0x20) while HGCamera.enableMV
                // is true (the retail getter is unconditionally true). Let
                // Unity own the previous-matrix/validity history behind this
                // public SRP contract instead of synthesizing it here.
                perObjectData = PerObjectData.MotionVectors
            };

            for (int i = 1; i < shaderPasses.Length; i++)
                drawingSettings.SetShaderPassName(i, shaderPasses[i]);

            FilteringSettings filteringSettings = new FilteringSettings(
                queueRange,
                layerMask);
            context.DrawRenderers(cullingResults, ref drawingSettings, ref filteringSettings);
        }

        private static void DrawRecoveredEndminfShadowPlane(
            ScriptableRenderContext context,
            RenderTargetIdentifier colorTarget,
            RenderTargetIdentifier depthTarget)
        {
            if (EndfieldRecoveredSelector.Explicit(
                    EndfieldRecoveredCharInfoPresentation.
                        EndminfBackdropVisualCompatibilityEnvironmentVariable) != true)
                return;

            EndfieldRecoveredCharInfoPresentation presentation =
                Object.FindObjectOfType<EndfieldRecoveredCharInfoPresentation>(true);
            Renderer renderer = presentation == null
                ? null
                : presentation.shadowPlaneRenderer;
            if (renderer == null || !renderer.enabled ||
                !renderer.gameObject.activeInHierarchy)
                return;

            Material material = renderer.sharedMaterial;
            int pass = material == null
                ? -1
                : material.FindPass("ShadowReceiver");
            if (pass < 0)
                return;

            CommandBuffer commands = new CommandBuffer
            {
                name = "Recovered Endminf ShadowPlane transparent submission"
            };
            commands.SetRenderTarget(colorTarget, depthTarget);
            commands.DrawRenderer(renderer, material, 0, pass);
            context.ExecuteCommandBuffer(commands);
            commands.Release();
        }

        private static void ApplyLightingGlobals(CommandBuffer commandBuffer)
        {
            Light mainLight = null;
            Light[] lights = Object.FindObjectsOfType<Light>();
            foreach (Light light in lights)
            {
                if (light != null && light.type == LightType.Directional && light.enabled)
                {
                    mainLight = light;
                    break;
                }
            }

            Vector3 lightToSurfaceDirection = mainLight != null
                ? mainLight.transform.forward.normalized
                : new Vector3(-0.35f, -0.75f, -0.55f).normalized;
            Vector3 surfaceToLightDirection = -lightToSurfaceDirection;
            Color color = mainLight != null ? mainLight.color * mainLight.intensity : Color.white;
            Color ambient = RenderSettings.ambientLight;

            commandBuffer.SetGlobalVector("_DirectionalLightDirection", new Vector4(lightToSurfaceDirection.x, lightToSurfaceDirection.y, lightToSurfaceDirection.z, 0.0f));
            commandBuffer.SetGlobalVector("_WorldSpaceLightPos0", new Vector4(surfaceToLightDirection.x, surfaceToLightDirection.y, surfaceToLightDirection.z, 0.0f));
            commandBuffer.SetGlobalVector("_MainLightPosition", new Vector4(surfaceToLightDirection.x, surfaceToLightDirection.y, surfaceToLightDirection.z, 0.0f));
            commandBuffer.SetGlobalColor("_LightColor0", color);
            commandBuffer.SetGlobalColor("_DirectionalLightColor", color);
            commandBuffer.SetGlobalColor("_MainLightColor", color);

            commandBuffer.SetGlobalVector("unity_SHAr", new Vector4(0.0f, 0.0f, 0.0f, ambient.r));
            commandBuffer.SetGlobalVector("unity_SHAg", new Vector4(0.0f, 0.0f, 0.0f, ambient.g));
            commandBuffer.SetGlobalVector("unity_SHAb", new Vector4(0.0f, 0.0f, 0.0f, ambient.b));
            commandBuffer.SetGlobalVector("unity_SHBr", Vector4.zero);
            commandBuffer.SetGlobalVector("unity_SHBg", Vector4.zero);
            commandBuffer.SetGlobalVector("unity_SHBb", Vector4.zero);
            commandBuffer.SetGlobalVector("unity_SHC", Vector4.zero);
        }
    }

    public sealed class HGCompatRenderPipeline : HDRenderPipeline
    {
        public HGCompatRenderPipeline(HGCompatRenderPipelineAsset asset)
            : base(asset)
        {
        }
    }
}
