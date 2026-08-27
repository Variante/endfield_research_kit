Shader "Hidden/Endfield/Recovered/Zhuangfy/VFXBaseV2MRT"
{
    Properties
    {
        _MainTex ("Main Tex", 2D) = "white" {}
        _SampleTex0 ("Sample Tex 0", 2D) = "white" {}
        _SampleTex1 ("Sample Tex 1", 2D) = "white" {}
        _SampleTex2 ("Sample Tex 2", 2D) = "white" {}
        _SampleTex3 ("Sample Tex 3", 2D) = "white" {}
        _OffsetTex ("Vertex Offset Tex", 2D) = "white" {}
        _OffsetMaskTex ("Vertex Offset Mask Tex", 2D) = "white" {}
        // These six source texture environments provide the exact weighted ST
        // lanes used by shipped vertex blob 1236 for Sample0/Sample1 UVs.
        _DisturbTex1 ("Disturb Tex 1 ST Source", 2D) = "white" {}
        _DisturbTex2 ("Disturb Tex 2 ST Source", 2D) = "white" {}
        _WeightTex ("Weight Tex ST Source", 2D) = "white" {}
        _MaskTex ("Mask Tex ST Source", 2D) = "white" {}
        _BlendTex ("Blend Tex ST Source", 2D) = "white" {}
        _DissolveTex ("Dissolve Tex ST Source", 2D) = "white" {}
        _SurfaceType ("Surface Type", Float) = 1
        _BlendMode ("Blend Mode", Float) = 1
        _CullMode ("Cull Mode", Float) = 2
        _VertCameraOffset ("Vertex Camera Offset", Float) = 0
        [Toggle(_USE_VERTOFFSET)] _UseVertexOffset ("Use Vertex Offset", Float) = 0
        [Toggle(_USE_VERTOFFSETMASK)] _UseVertexOffsetMask ("Use Vertex Offset Mask", Float) = 0
        _Bi_Offset ("Bidirectional Vertex Offset", Float) = 0
        _OffsetSwitchDir ("Vertex Offset Direction Mode", Float) = 0
        _OffsetUVSet ("Vertex Offset UV Set", Float) = 0
        _OffsetIntensity ("Vertex Offset Intensity", Float) = 0
        _OffsetDir ("Vertex Offset Direction", Vector) = (0,0,0,0)
        _OffsetSpeed ("Vertex Offset Speed", Vector) = (0,0,0,0)
        _OffsetMaskPower ("Vertex Offset Mask Power", Float) = 0
        _OffsetMaskSpeed ("Vertex Offset Mask Speed", Vector) = (0,0,0,0)
        _TintColor ("Tint Color", Color) = (1,1,1,1)
        [HideInInspector] _UseRecoveredRawTintColor ("Use Recovered Raw Tint Color", Float) = 0
        [HideInInspector] _RecoveredRawTintColor ("Recovered Raw Tint Color", Vector) = (1,1,1,1)
        [HideInInspector] _Dian904RawTintColor ("Dian904 Raw Tint Color", Vector) = (0,0,0,0)
        [HideInInspector] _Dian904RawPerDrawC13 ("Dian904 Raw Per-Draw C13", Vector) = (0,0,0,0)
        [HideInInspector] _Dian904PSB0C0 ("Dian904 PS B0 C0", Vector) = (0,0,0,0)
        [HideInInspector] _Dian904PSB0C1 ("Dian904 PS B0 C1", Vector) = (0,0,0,0)
        [HideInInspector] _Dian904PSB0C2 ("Dian904 PS B0 C2", Vector) = (0,0,0,0)
        [HideInInspector] _Dian904PSB0C3 ("Dian904 PS B0 C3", Vector) = (0,0,0,0)
        [HideInInspector] _Dian904PSB0C24 ("Dian904 PS B0 C24", Vector) = (0,0,0,0)
        [HideInInspector] _Dian904PSB0C25 ("Dian904 PS B0 C25", Vector) = (0,0,0,0)
        [HideInInspector] _Dian904PSB0C26 ("Dian904 PS B0 C26", Vector) = (0,0,0,0)
        [HideInInspector] _Dian904PSB0C27 ("Dian904 PS B0 C27", Vector) = (0,0,0,0)
        [HideInInspector] _Dian904PSB1C0 ("Dian904 PS B1 C0", Vector) = (0,0,0,0)
        _TintColorIntensity ("Tint Color Intensity", Float) = 1
        _TintColorAlpha ("Tint Color Alpha", Float) = 1
        _ExpThreshold ("Exposure Threshold", Float) = 1
        _ExpIntensity ("Exposure Intensity", Float) = 0
        _ProcedureAlpha ("Procedure Alpha", Float) = 1
        _InParticle ("In Particle", Float) = 0
        _DisableVertColor ("Disable Vertex Color", Float) = 0
        _DisableParticleInstanceColor ("Disable Particle Instance Color", Float) = 0
        _EnableTransparentMV ("Enable Transparent MV", Float) = 0
        _Responsive ("Responsive", Float) = 0
        _IsSceneEffect ("Is Scene Effect", Float) = 0
        _IgnorePostExposure ("Ignore Post Exposure", Float) = 0

        _MainTexMipmapBias ("Main Tex Mipmap Bias", Float) = 0
        _MainTexUseDisturb ("Main Tex Use Disturb", Float) = 0
        _UseMainTexAsAlpha ("Use Main Tex As Alpha", Float) = 1
        _MainTexUVSpeed ("Main Tex UV Speed", Vector) = (0,0,0,0)
        _MainTexUVRotateMat ("Main Tex UV Rotate Mat", Vector) = (1,0,0,1)
        _MainTexUVWeights ("Main Tex UV Weights", Vector) = (1,0,0,0)

        _SampleTex0MipmapBias ("Sample 0 Mipmap Bias", Float) = 0
        _UseSampleTex0 ("Use Sample 0", Float) = 0
        _SampleTex0UseDisturb ("Sample 0 Use Disturb", Float) = 0
        _UseSampleTex0AsAlpha ("Use Sample 0 As Alpha", Float) = 1
        _SampleTex0UVSpeed ("Sample 0 UV Speed", Vector) = (0,0,0,0)
        _SampleTex0UVRotateMat ("Sample 0 UV Rotate Mat", Vector) = (1,0,0,1)
        _SampleTex0UVWeights ("Sample 0 UV Weights", Vector) = (1,0,0,0)
        _SampleTex0Use ("Sample 0 Use", Float) = 0
        _SampleTex0UseWeight0 ("Sample 0 Weight 0", Float) = 0
        _SampleTex0UseWeight2 ("Sample 0 Weight 2", Float) = 0
        _SampleTex0UseWeight3 ("Sample 0 Weight 3", Float) = 0
        _SampleTex0UseWeight4 ("Sample 0 Weight 4", Float) = 0
        _SampleTex0UseWeight5 ("Sample 0 Weight 5", Float) = 0

        _SampleTex1MipmapBias ("Sample 1 Mipmap Bias", Float) = 0
        _UseSampleTex1 ("Use Sample 1", Float) = 0
        _SampleTex1UseDisturb ("Sample 1 Use Disturb", Float) = 0
        _UseSampleTex1AsAlpha ("Use Sample 1 As Alpha", Float) = 1
        _SampleTex1UVSpeed ("Sample 1 UV Speed", Vector) = (0,0,0,0)
        _SampleTex1UVRotateMat ("Sample 1 UV Rotate Mat", Vector) = (1,0,0,1)
        _SampleTex1UVWeights ("Sample 1 UV Weights", Vector) = (1,0,0,0)
        _SampleTex1Use ("Sample 1 Use", Float) = 0
        _SampleTex1UseWeight1 ("Sample 1 Weight 1", Float) = 0
        _SampleTex1UseWeight2 ("Sample 1 Weight 2", Float) = 0
        _SampleTex1UseWeight3 ("Sample 1 Weight 3", Float) = 0
        _SampleTex1UseWeight4 ("Sample 1 Weight 4", Float) = 0
        _SampleTex1UseWeight5 ("Sample 1 Weight 5", Float) = 0

        _SampleTex2MipmapBias ("Sample 2 Mipmap Bias", Float) = 0
        _SampleTex2UseDisturb ("Sample 2 Use Disturb", Float) = 0
        _UseSampleTex2 ("Use Sample 2", Float) = 0
        _UseSampleTex2AsAlpha ("Use Sample 2 As Alpha", Float) = 1
        _SampleTex2UVSpeed ("Sample 2 UV Speed", Vector) = (0,0,0,0)
        _SampleTex2UVRotateMat ("Sample 2 UV Rotate Mat", Vector) = (1,0,0,1)
        _SampleTex2UVWeights ("Sample 2 UV Weights", Vector) = (1,0,0,0)
        _SampleTex2Use ("Sample 2 Use", Float) = 0
        _SampleTex2UseWeight4 ("Sample 2 Weight 4", Float) = 0
        _SampleTex2UseWeight5 ("Sample 2 Weight 5", Float) = 0

        _SampleTex3MipmapBias ("Sample 3 Mipmap Bias", Float) = 0
        _SampleTex3UseDisturb ("Sample 3 Use Disturb", Float) = 0
        _UseSampleTex3 ("Use Sample 3", Float) = 0
        _UseSampleTex3AsAlpha ("Use Sample 3 As Alpha", Float) = 1
        _SampleTex3UVSpeed ("Sample 3 UV Speed", Vector) = (0,0,0,0)
        _SampleTex3UVRotateMat ("Sample 3 UV Rotate Mat", Vector) = (1,0,0,1)
        _SampleTex3UVWeights ("Sample 3 UV Weights", Vector) = (1,0,0,0)
        _SampleTex3Use ("Sample 3 Use", Float) = 0
        _SampleTex3UseWeight5 ("Sample 3 Weight 5", Float) = 0

        _UsePolarUV ("Use Polar UV", Float) = 0
        _UseScreenUV ("Use Screen UV", Float) = 0

        _UseMask ("Use Mask", Float) = 0
        _UseBlend ("Use Blend", Float) = 0
        [HDR] [Gamma] _BlendTint ("Blend Tint", Color) = (1,1,1,1)
        _UseDissolve ("Use Dissolve", Float) = 0
        _DissolveScheduleOffset ("Dissolve Schedule Offset", Float) = 0
        _DissolveEdgeSharp ("Dissolve Edge Sharp", Float) = 1
        _DissolveEmissiveEdge ("Dissolve Emissive Edge", Float) = 0
        [HDR] [Gamma] _DissolveEmissiveColor ("Dissolve Emissive Color", Color) = (0,0,0,0)
        [Toggle(_USE_FRESNEL)] _UseFresnel ("Use Fresnel", Float) = 0
        [HDR] [Gamma] _FresnelColor ("Fresnel Color", Color) = (1,1,1,1)
        _FresnelBias ("Fresnel Bias", Float) = 0
        _FresnelAffectOpacity ("Fresnel Affect Opacity", Float) = 1
        _FresnelPower ("Fresnel Power", Float) = 1
        _FresnelFlip ("Fresnel Flip", Float) = 0.001
        _UseDisturb ("Use Disturb", Float) = 0
        _UseDisturb2 ("Use Disturb 2", Float) = 0
        _Bi_Disturb ("Bidirectional Disturb", Float) = 0
        _DisturbUseWeight ("Disturb Use Particle Weight", Float) = 0
        _UseParticleDisturb ("Use Particle Disturb Weight", Float) = 0
        _DisturbTex1Normal ("Disturb Tex 1 Normal", Float) = 0
        _DisturbUIntensity1 ("Disturb U Intensity 1", Float) = 0
        _DisturbVIntensity1 ("Disturb V Intensity 1", Float) = 0
        _DisturbTex2Normal ("Disturb Tex 2 Normal", Float) = 0
        _DisturbUIntensity2 ("Disturb U Intensity 2", Float) = 0
        _DisturbVIntensity2 ("Disturb V Intensity 2", Float) = 0
        _UseNearCameraFade ("Use Near Camera Fade", Float) = 0
        _NearCameraFadeDistanceStart ("Near Fade Start", Float) = 0.001
        _NearCameraFadeDistanceEnd ("Near Fade End", Float) = 10
        _NearCameraFadeDistanceStart2 ("Near Fade Start 2", Float) = 120
        _NearCameraFadeDistanceEnd2 ("Near Fade End 2", Float) = 100
        _UseSoftBlend ("Use Soft Blend", Float) = 0
        _SoftDistance ("Soft Distance", Float) = 0.001
        _SoftBias ("Soft Bias", Float) = 0
        _SrcBlend ("Source Blend", Float) = 1
        _DstBlend ("Destination Blend", Float) = 10
        _AlphaSrcBlend ("Alpha Source Blend", Float) = 1
        _AlphaDstBlend ("Alpha Destination Blend", Float) = 10
        _MVSrcColorBlend ("MV Source Color Blend", Float) = 3
        _MVDstColorBlend ("MV Destination Color Blend", Float) = 6
        _ZTest ("Z Test", Float) = 4
        _ZWrite ("Z Write", Float) = 0
        _RecoveredLODFade ("Recovered LOD Fade", Vector) = (1000,0,0,0)
        [HideInInspector] _Dian902ManualReplayIndex ("Dian902 Manual Replay Index", Float) = -1
        [HideInInspector] _Dian902ManualSourceTime ("Dian902 Manual Source Time", Float) = -1
        [HideInInspector] _Dian902ManualAgePercent ("Dian902 Manual Age Percent", Float) = -1
        [HideInInspector] _Dian902ManualRemainingLifetime ("Dian902 Manual Remaining Lifetime", Float) = -1
        [HideInInspector] _Dian901ManualReplayValid ("Dian901 Manual Replay Valid", Float) = 0
        [HideInInspector] _Dian901ManualReplayMagic ("Dian901 Manual Replay Magic", Float) = 0
        [HideInInspector] _Dian901ManualReplaySample ("Dian901 Manual Replay Sample", Float) = -1
        [HideInInspector] _Dian901ManualSourceTime ("Dian901 Manual Source Time", Float) = -1
        [HideInInspector] _Dian901ManualLiveCount ("Dian901 Manual Live Count", Float) = -1
        [HideInInspector] _Dian901ManualReplayEpoch ("Dian901 Manual Replay Epoch", Float) = -1
        [HideInInspector] _Dian901ManualPublishFrame ("Dian901 Manual Publish Frame", Float) = -1
        [HideInInspector] _Dian901ManualRendererFingerprint ("Dian901 Manual Renderer Fingerprint", Float) = 0
        [HideInInspector] _Dian901ManualReplayChecksum ("Dian901 Manual Replay Checksum", Float) = 0
        [HideInInspector] _Dian901AutomaticSchedulerChecksum ("Dian901 Automatic Scheduler Checksum", Float) = 0
        [HideInInspector] _Dian901AutomaticRowChecksum ("Dian901 Automatic Row Checksum", Float) = 0
        [HideInInspector] _Lightning902RetailCustom1X ("Lightning902 Retail Custom1.X", Float) = -1
        [HideInInspector] _Lightning902RetailReplayValid ("Lightning902 Retail Replay Valid", Float) = 0
        [HideInInspector] _Lightning902RetailReplayMagic ("Lightning902 Retail Replay Magic", Float) = 0
        [HideInInspector] _Lightning902RetailReplayEpoch ("Lightning902 Retail Replay Epoch", Float) = -1
        [HideInInspector] _Lightning902RetailPublishFrame ("Lightning902 Retail Publish Frame", Float) = -1
        [HideInInspector] _Lightning902RetailRendererFingerprint ("Lightning902 Retail Renderer Fingerprint", Float) = 0
        [HideInInspector] _Lightning902RetailReplayChecksum ("Lightning902 Retail Replay Checksum", Float) = 0
    }

    SubShader
    {
        Tags
        {
            "Queue"="Transparent"
            "RenderType"="Transparent"
            "EndfieldSceneMVMRT"="ExactSelectedFiftyThree"
        }

        Pass
        {
            Name "ForwardOnly"
            Tags { "LightMode"="ForwardOnly" }
            Blend 0 [_SrcBlend] [_DstBlend], [_AlphaSrcBlend] [_AlphaDstBlend]
            Blend 1 [_MVSrcColorBlend] [_MVDstColorBlend], One One
            ColorMask RGBA 0
            ColorMask RGBA 1
            ZTest [_ZTest]
            ZWrite [_ZWrite]
            Cull [_CullMode]

            CGPROGRAM
            #pragma target 5.0
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile_instancing
            #pragma instancing_options procedural:vertInstancingSetup
            #pragma shader_feature_local_fragment _SAMPLE_TEX0
            #pragma shader_feature_local _SAMPLE_TEX1
            #pragma shader_feature_local_fragment _SAMPLE_TEX2
            #pragma shader_feature_local_fragment _SAMPLE_TEX3
            #pragma shader_feature_local_fragment _USE_POLARUV
            #pragma shader_feature_local_fragment _USE_SCREENUV
            #pragma shader_feature_local_fragment _USE_FRESNEL
            #pragma shader_feature_local_fragment _USE_SOFTBLEND
            // Dormant only: M_fx_ui_dian_904 remains source-material
            // fail-closed. This specialization pins the exact 0859 static
            // sampler tuple for offline/diagnostic material comparison.
            #pragma shader_feature_local _DIAN904_EXACT_DORMANT_CANDIDATE
            // Diagnostic-only raw shipped-VS0858 post-vertex replay. No
            // generated material owns this local keyword.
            #pragma shader_feature_local_vertex _DIAN904_EXACT_POST_VS_REPLAY_DIAGNOSTIC
            // Diagnostic-only point capture of the normal maintained vertex
            // route. No generated material owns this local keyword.
            #pragma shader_feature_local _DIAN904_LIVE_VERT_CAPTURE_DIAGNOSTIC
            #pragma shader_feature_local_vertex _USE_VERTOFFSET
            #pragma shader_feature_local_vertex _USE_VERTOFFSETMASK
            #pragma shader_feature_local_vertex _LINE006_EXACT_STEP_REPLAY
            #pragma shader_feature_local _DIAN901_EXACT_FIXED_MANUAL_REPLAY
            #pragma shader_feature_local _DIAN901_EXACT_DYNAMIC_REPLAY
            #pragma shader_feature_local _DIAN902_EXACT_MANUAL_REPLAY
            #pragma shader_feature_local _DIAN902_EXACT_DYNAMIC_REPLAY
            #pragma shader_feature_local _LIGHTNING902_EXACT_RUNTIME_REPLAY
            #include "UnityCG.cginc"
            #include "UnityStandardParticleInstancing.cginc"
            #include "EndfieldZhuangfyDian901FixedManualReplay.hlsl"
            #include "EndfieldZhuangfyDian901DynamicReplay.hlsl"
            #include "EndfieldZhuangfyLightning902RuntimeReplay.hlsl"

            Texture2D<float4> _MainTex;
            Texture2D<float4> _SampleTex0;
            Texture2D<float4> _SampleTex1;
            Texture2D<float4> _SampleTex2;
            Texture2D<float4> _SampleTex3;
            Texture2D<float4> _OffsetTex;
            Texture2D<float4> _OffsetMaskTex;
            Texture2D<float> _SceneDepth;
            // Material textures use Unity's paired-sampler convention so the
            // exact installed Texture2D filter/wrap/aniso/mip-bias descriptors
            // applied by the importer remain authoritative per identity.
            SamplerState sampler_MainTex;
            SamplerState sampler_SampleTex0;
            SamplerState sampler_SampleTex1;
            // The shipped BaseV2 blobs use static sampler identities for
            // these slots. Paired Unity texture samplers can carry hidden
            // LOD/filter state even when their public Texture2D settings
            // match, which changes SampleBias/Grad selection.
            SamplerState sampler_LinearClamp;
            SamplerState sampler_LinearRepeat;
            SamplerState sampler_LinearMirror;
            SamplerState sampler_LinearMirrorOnce;
            SamplerState sampler_SampleTex2;
            SamplerState sampler_SampleTex3;
            SamplerState sampler_OffsetTex;
            SamplerState sampler_OffsetMaskTex;
            // Native parameter record 127 closes the soft-depth sampler as
            // s_point_clamp_float_sampler (PackedInfo 0x00010054). This is a
            // static global sampler, unlike the texture-derived material
            // samplers whose PackedInfo is the 0x0001FFFF sentinel.
            SamplerState s_point_clamp_float_sampler;
            ByteAddressBuffer _Dian904CapturedRows;
            ByteAddressBuffer _Dian904CapturedIndices;
            float4 _MainTex_ST;
            float4 _SampleTex0_ST;
            float4 _SampleTex1_ST;
            float4 _SampleTex2_ST;
            float4 _SampleTex3_ST;
            float4 _OffsetTex_ST;
            float4 _OffsetMaskTex_ST;
            float4 _DisturbTex1_ST;
            float4 _DisturbTex2_ST;
            float4 _WeightTex_ST;
            float4 _MaskTex_ST;
            float4 _BlendTex_ST;
            float4 _DissolveTex_ST;
            float4 _SceneDepth_TexelSize;
            float4 _MainTexUVSpeed;
            float4 _MainTexUVRotateMat;
            float4 _MainTexUVWeights;
            float4 _SampleTex0UVSpeed;
            float4 _SampleTex0UVRotateMat;
            float4 _SampleTex0UVWeights;
            float4 _SampleTex1UVSpeed;
            float4 _SampleTex1UVRotateMat;
            float4 _SampleTex1UVWeights;
            float4 _SampleTex2UVSpeed;
            float4 _SampleTex2UVRotateMat;
            float4 _SampleTex2UVWeights;
            float4 _SampleTex3UVSpeed;
            float4 _SampleTex3UVRotateMat;
            float4 _SampleTex3UVWeights;
            float4 _OffsetDir;
            float4 _OffsetSpeed;
            float4 _OffsetMaskSpeed;
            float4 _TintColor;
            float4 _RecoveredRawTintColor;
            float4 _Dian904RawTintColor;
            float4 _Dian904RawPerDrawC13;
            float4 _Dian904PSB0C0;
            float4 _Dian904PSB0C1;
            float4 _Dian904PSB0C2;
            float4 _Dian904PSB0C3;
            float4 _Dian904PSB0C24;
            float4 _Dian904PSB0C25;
            float4 _Dian904PSB0C26;
            float4 _Dian904PSB0C27;
            float4 _Dian904PSB1C0;
            float4 _BlendTint;
            float4 _DissolveEmissiveColor;
            float4 _FresnelColor;
            float4 _ExposureWithMiscParams;
            float4 _VFXParams0;
            float4 _RecoveredLODFade;
            float _GlobalMipBias;
            float _EndfieldSceneMVMRTReady;
            float _EndfieldRecoveredVFXGlobalsReady;
            float _SurfaceType;
            float _BlendMode;
            float _Responsive;
            float _InParticle;
            float _DisableVertColor;
            float _DisableParticleInstanceColor;
            float _VertCameraOffset;
            float _UseVertexOffset;
            float _UseVertexOffsetMask;
            float _Bi_Offset;
            float _OffsetSwitchDir;
            float _OffsetUVSet;
            float _OffsetIntensity;
            float _OffsetMaskPower;
            float _UseRecoveredRawTintColor;
            // Selected retail Forward/Transparent/after-DOF passes zero-fill
            // this per-pass lane. DepthOnly is a non-selected value-1 control.
            // No redundant Unity-side global publisher is needed.
            float _DisableAnimateVert;
            float _TintColorIntensity;
            float _TintColorAlpha;
            float _ExpThreshold;
            float _ExpIntensity;
            float _ProcedureAlpha;
            float _IgnorePostExposure;
            float _MainTexMipmapBias;
            float _MainTexUseDisturb;
            float _UseMainTexAsAlpha;
            float _SampleTex0MipmapBias;
            float _UseSampleTex0;
            float _UseSampleTex0AsAlpha;
            float _SampleTex0UseWeight0;
            float _SampleTex0UseWeight2;
            float _SampleTex0UseWeight3;
            float _SampleTex0UseWeight4;
            float _SampleTex1MipmapBias;
            float _UseSampleTex1;
            float _SampleTex1UseDisturb;
            float _UseSampleTex1AsAlpha;
            float _SampleTex1UseWeight1;
            float _SampleTex1UseWeight2;
            float _SampleTex1UseWeight3;
            float _SampleTex1UseWeight4;
            float _SampleTex1UseWeight5;
            float _SampleTex2MipmapBias;
            float _SampleTex2Use;
            float _UseSampleTex2AsAlpha;
            float _SampleTex2UseWeight4;
            float _SampleTex3MipmapBias;
            float _UseSampleTex3;
            float _SampleTex3UseDisturb;
            float _UseSampleTex3AsAlpha;
            float _SampleTex3UseWeight5;
            float _UsePolarUV;
            float _UseScreenUV;
            float _UseMask;
            float _UseBlend;
            float _UseDissolve;
            float _DissolveScheduleOffset;
            float _DissolveEdgeSharp;
            float _DissolveEmissiveEdge;
            float _FresnelBias;
            float _FresnelAffectOpacity;
            float _FresnelPower;
            float _FresnelFlip;
            float _UseDisturb;
            float _UseDisturb2;
            float _Bi_Disturb;
            float _DisturbUseWeight;
            float _UseParticleDisturb;
            float _DisturbTex1Normal;
            float _DisturbUIntensity1;
            float _DisturbVIntensity1;
            float _DisturbTex2Normal;
            float _DisturbUIntensity2;
            float _DisturbVIntensity2;
            float _UseNearCameraFade;
            float _NearCameraFadeDistanceStart;
            float _NearCameraFadeDistanceEnd;
            float _NearCameraFadeDistanceStart2;
            float _NearCameraFadeDistanceEnd2;
            float _SoftDistance;
            float _SoftBias;
            float _Dian902ManualReplayIndex;
            float _Dian902ManualSourceTime;
            float _Dian902ManualAgePercent;
            float _Dian902ManualRemainingLifetime;
            float _Dian901ManualReplayValid;
            float _Dian901ManualReplayMagic;
            float _Dian901ManualReplaySample;
            float _Dian901ManualSourceTime;
            float _Dian901ManualLiveCount;
            float _Dian901ManualReplayEpoch;
            float _Dian901ManualPublishFrame;
            float _Dian901ManualRendererFingerprint;
            float _Dian901ManualReplayChecksum;
            float _Dian901AutomaticSchedulerChecksum;
            float _Dian901AutomaticRowChecksum;
            float _Lightning902RetailCustom1X;
            float _Lightning902RetailReplayValid;
            float _Lightning902RetailReplayMagic;
            float _Lightning902RetailReplayEpoch;
            float _Lightning902RetailPublishFrame;
            float _Lightning902RetailRendererFingerprint;
            float _Lightning902RetailReplayChecksum;
            float _Dian904LiveVertCapturePage;

            struct Attributes
            {
                float4 vertex : POSITION;
                float3 normal : NORMAL;
                float4 color : COLOR;
                float4 uv0 : TEXCOORD0;
                float4 custom : TEXCOORD1;
                UNITY_VERTEX_INPUT_INSTANCE_ID
                #if defined(_LINE006_EXACT_STEP_REPLAY)
                    float2 recoveryCarrier : TEXCOORD2;
                #endif
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float4 color : COLOR;
                float2 mainUV : TEXCOORD0;
                float2 sample0UV : TEXCOORD1;
                float2 sample1UV : TEXCOORD2;
                float2 sample2UV : TEXCOORD3;
                float4 custom : TEXCOORD4;
                float4 screenPos : TEXCOORD5;
                float3 positionWS : TEXCOORD6;
                float3 normalWS : TEXCOORD7;
                float4 particleUV : TEXCOORD8;
                #if defined(_DIAN904_LIVE_VERT_CAPTURE_DIAGNOSTIC)
                    nointerpolation float4 diagnosticPositionCS : TEXCOORD9;
                    nointerpolation float4 diagnosticMainSampleUV : TEXCOORD10;
                    nointerpolation float4 diagnosticColor : TEXCOORD11;
                    nointerpolation float4 diagnosticCustom : TEXCOORD12;
                #endif
            };

            struct FragmentOutput
            {
                float4 color : SV_Target0;
                float4 sceneMV : SV_Target1;
            };

            #if defined(_LINE006_EXACT_STEP_REPLAY)
            #include "EndfieldZhuangfyLightning901ThirdReplay.hlsl"

            precise float EvaluateLine006RetailCustom(
                precise float agePercent)
            {
                precise float normalizedAge = agePercent * 0.01;
                precise float doubledAge = 2.0 * normalizedAge;
                precise float custom = -1.0 + doubledAge;
                return custom;
            }

            precise float RecoverLine006Custom1X(Attributes input)
            {
                precise float publicInvStartLifetime =
                    input.recoveryCarrier.y;
                uint publicInvBits =
                    asuint(publicInvStartLifetime);
                precise float retailInvLifetime;
                uint maxPriorStep;
                if (publicInvBits == 0x404485F0u)
                {
                    retailInvLifetime = publicInvStartLifetime;
                    maxPriorStep = 15u;
                }
                else if (publicInvBits == 0x4062CDE0u)
                {
                    retailInvLifetime = publicInvStartLifetime;
                    maxPriorStep = 13u;
                }
                else if (publicInvBits == 0x40714607u)
                {
                    retailInvLifetime = asfloat(0x40714606u);
                    maxPriorStep = 12u;
                }
                else
                    return input.custom.x;

                precise float retailIncrementPercent =
                    retailInvLifetime * 2.0;
                precise float liveCustom = input.custom.x;
                precise float retailAgePercent = 0.0;
                uint staleBits = asuint(input.custom.x);

                if (staleBits == 0xBF800000u)
                {
                    // Public Unity has no drawable N=0 row for either admitted
                    // renderer.  The first drawn N=1 row retains Custom1=-1
                    // while AgePercent is already positive.
                    if (input.recoveryCarrier.x > 0.0)
                    {
                        retailAgePercent =
                            retailAgePercent + retailIncrementPercent;
                        liveCustom =
                            EvaluateLine006RetailCustom(retailAgePercent);
                    }
                }
                else
                {
                    bool foundPriorStep = false;
                    [loop]
                    for (uint priorStep = 1u;
                        priorStep <= maxPriorStep;
                        ++priorStep)
                    {
                        retailAgePercent =
                            retailAgePercent + retailIncrementPercent;
                        precise float candidate =
                            EvaluateLine006RetailCustom(retailAgePercent);
                        if (asuint(candidate) == staleBits)
                        {
                            foundPriorStep = true;
                            break;
                        }
                    }
                    if (foundPriorStep)
                    {
                        retailAgePercent =
                            retailAgePercent + retailIncrementPercent;
                        liveCustom =
                            EvaluateLine006RetailCustom(retailAgePercent);
                    }
                }
                return liveCustom;
            }
            #endif

            #if defined(_DIAN902_EXACT_DYNAMIC_REPLAY)
            #include "EndfieldZhuangfyDian902DynamicRenderLeaf.hlsl"

            bool Dian902DynamicReplayTupleValid()
            {
                return IsDian902DynamicRenderTuple(
                    asuint(_Dian902ManualReplayIndex),
                    asuint(_Dian902ManualSourceTime),
                    asuint(_Dian902ManualAgePercent),
                    asuint(_Dian902ManualRemainingLifetime));
            }
            #endif

            #if defined(_DIAN902_EXACT_MANUAL_REPLAY)
            #include "EndfieldZhuangfyDian902ManualReplay.hlsl"

            bool Dian902ManualReplayTupleValid()
            {
                return IsDian902ManualReplayTuple(
                    asuint(_Dian902ManualReplayIndex),
                    asuint(_Dian902ManualSourceTime),
                    asuint(_Dian902ManualAgePercent),
                    asuint(_Dian902ManualRemainingLifetime));
            }
            #endif

            float2 BuildUV(float2 uv0, float customValue, float4 weights,
                float4 speed, float4 rotateMat, float4 textureST)
            {
                float2 uv = uv0 * weights.x;
                float2 centered = uv + speed.xy * _VFXParams0.w +
                    speed.zw * customValue - 0.5;
                float2 rotated = float2(
                    dot(centered, rotateMat.xz),
                    dot(centered, rotateMat.yw)) + 0.5;
                return rotated * textureST.xy + textureST.zw;
            }

            float2 Retail1236SourceUV(
                Attributes input, float4 weights, float4 speed,
                float customSpeedCarrier)
            {
                precise float2 selectedSecondaryUV = mad(
                    input.uv0.zw,
                    _InParticle.xx,
                    -input.custom.xy * _InParticle) + input.custom.xy;
                precise float2 uv = mad(
                    selectedSecondaryUV,
                    weights.yy,
                    input.uv0.xy * weights.xx);
                uv = mad(speed.xy, _VFXParams0.ww, uv);
                uv = mad(speed.zw, customSpeedCarrier.xx, uv);
                return uv - 0.5;
            }

            float2 Retail1236UV(
                Attributes input, float4 weights, float4 speed,
                float4 rotateMat, float4 textureST,
                float customSpeedCarrier)
            {
                precise float2 uv = Retail1236SourceUV(
                    input, weights, speed, customSpeedCarrier);
                precise float2 rotated;
                rotated.x = mad(uv.y, rotateMat.z, uv.x * rotateMat.x);
                rotated.y = mad(uv.y, rotateMat.w, uv.x * rotateMat.y);
                rotated += 0.5;
                return mad(rotated, textureST.xy, textureST.zw);
            }

            float4 Retail1236Sample0ST()
            {
                precise float4 textureST =
                    _DisturbTex1_ST * _SampleTex0UseWeight0;
                textureST = mad(
                    _WeightTex_ST,
                    _SampleTex0UseWeight2.xxxx,
                    textureST);
                textureST = mad(
                    _MaskTex_ST,
                    _SampleTex0UseWeight3.xxxx,
                    textureST);
                return mad(
                    _BlendTex_ST,
                    _SampleTex0UseWeight4.xxxx,
                    textureST);
            }

            float4 Retail1236Sample1ST()
            {
                precise float4 textureST =
                    _DisturbTex2_ST * _SampleTex1UseWeight1;
                textureST = mad(
                    _WeightTex_ST,
                    _SampleTex1UseWeight2.xxxx,
                    textureST);
                textureST = mad(
                    _MaskTex_ST,
                    _SampleTex1UseWeight3.xxxx,
                    textureST);
                textureST = mad(
                    _BlendTex_ST,
                    _SampleTex1UseWeight4.xxxx,
                    textureST);
                return mad(
                    _DissolveTex_ST,
                    _SampleTex1UseWeight5.xxxx,
                    textureST);
            }

            float3 Retail1236VertexOffsetDirection(
                Attributes input, out float maskFactor)
            {
                precise float2 selectedSecondaryUV = mad(
                    input.uv0.zw,
                    _InParticle.xx,
                    -input.custom.xy * _InParticle) + input.custom.xy;
                precise float2 offsetBaseUV = mad(
                    selectedSecondaryUV,
                    _OffsetUVSet.xx,
                    input.uv0.xy * (1.0 - _OffsetUVSet));

                precise float3 transformedNormal = mul(
                    (float3x3)unity_ObjectToWorld,
                    input.normal);
                precise float3 transformedAuthoredDirection = mul(
                    (float3x3)unity_ObjectToWorld,
                    _OffsetDir.xyz);
                precise float3 direction =
                    _OffsetSwitchDir == 1.0
                    ? _OffsetDir.xyz
                    : (_OffsetSwitchDir == 2.0
                        ? transformedNormal
                        : transformedAuthoredDirection);
                precise float amplitude = mad(
                    _OffsetDir.w,
                    input.custom.w,
                    _OffsetIntensity);
                direction *= amplitude;

                precise float2 offsetUV = mad(
                    offsetBaseUV,
                    _OffsetTex_ST.xy,
                    _OffsetTex_ST.zw);
                offsetUV = mad(
                    _OffsetSpeed.xy,
                    _VFXParams0.ww,
                    offsetUV);
                offsetUV = mad(
                    _OffsetSpeed.zw,
                    input.custom.ww,
                    offsetUV);
                precise float offsetSample = _OffsetTex.SampleLevel(
                    sampler_OffsetTex, offsetUV, 0.0).r;
                offsetSample = mad(
                    offsetSample,
                    1.0 + _Bi_Offset,
                    -_Bi_Offset);
                direction *= offsetSample;

                maskFactor = 1.0;
                #if defined(_USE_VERTOFFSETMASK)
                    precise float2 maskUV = mad(
                        offsetBaseUV,
                        _OffsetMaskTex_ST.xy,
                        _OffsetMaskTex_ST.zw);
                    maskUV = mad(
                        _OffsetMaskSpeed.xy,
                        _VFXParams0.ww,
                        maskUV);
                    maskUV = mad(
                        _OffsetMaskSpeed.zw,
                        input.custom.ww,
                        maskUV);
                    precise float maskSample = _OffsetMaskTex.SampleLevel(
                        sampler_OffsetMaskTex, maskUV, 0.0).r;
                    precise float maskPower =
                        0.2 * _OffsetMaskPower;
                    maskFactor = mad(
                        maskPower,
                        maskSample,
                        -maskPower) + 1.0;
                #endif
                return direction;
            }

            precise float4 Dian904RetailPositionCS(
                Attributes input,
                out float3 positionWS)
            {
                // Literal shipped 0858 order for the selected non-skinned,
                // no-vertex-offset Dian904 tuple.
                precise float3 basis =
                    unity_ObjectToWorld._m01_m11_m21 *
                    input.vertex.y;
                basis = mad(
                    unity_ObjectToWorld._m00_m10_m20,
                    input.vertex.x,
                    basis);
                basis = mad(
                    unity_ObjectToWorld._m02_m12_m22,
                    input.vertex.z,
                    basis);
                precise float3 translation =
                    unity_ObjectToWorld._m03_m13_m23;
                precise float3 objectPosition = basis + translation;
                precise float3 cameraDirection =
                    _WorldSpaceCameraPos.xyz - objectPosition;
                precise float cameraDistance =
                    sqrt(dot(cameraDirection, cameraDirection));
                cameraDirection = cameraDirection / cameraDistance;
                precise float cameraOffsetDistance =
                    min(
                        max(cameraDistance - 1.0, 0.0),
                        _VertCameraOffset) + 0.001;
                precise float animateGate =
                    1.0 - _DisableAnimateVert;
                precise float3 cameraRelative =
                    basis +
                    (translation - _WorldSpaceCameraPos.xyz);
                cameraRelative = mad(
                    cameraDirection,
                    cameraOffsetDistance * animateGate,
                    cameraRelative);
                positionWS = objectPosition + (
                    cameraDirection *
                    cameraOffsetDistance *
                    animateGate);

                // 0858 consumes a camera-relative view/projection matrix.
                // Apply only Unity view rotation, then publish through the
                // projection columns in the same Y/X/Z/translation order.
                precise float3 viewRelative;
                viewRelative.x = dot(
                    UNITY_MATRIX_V._m00_m01_m02,
                    cameraRelative);
                viewRelative.y = dot(
                    UNITY_MATRIX_V._m10_m11_m12,
                    cameraRelative);
                viewRelative.z = dot(
                    UNITY_MATRIX_V._m20_m21_m22,
                    cameraRelative);
                precise float4 clip =
                    UNITY_MATRIX_P._m01_m11_m21_m31 *
                    viewRelative.y;
                clip = mad(
                    UNITY_MATRIX_P._m00_m10_m20_m30,
                    viewRelative.x,
                    clip);
                clip = mad(
                    UNITY_MATRIX_P._m02_m12_m22_m32,
                    viewRelative.z,
                    clip);
                clip += UNITY_MATRIX_P._m03_m13_m23_m33;
                return clip;
            }

            Varyings Vert(
                Attributes input,
                uint proceduralVertexId : SV_VertexID)
            {
                #if defined(_DIAN904_EXACT_POST_VS_REPLAY_DIAGNOSTIC)
                    uint sourceVertex =
                        _Dian904CapturedIndices.Load(
                            proceduralVertexId * 4);
                    uint offset = sourceVertex * 88;
                    Varyings output;
                    float4 capturedPosition =
                        asfloat(_Dian904CapturedRows.Load4(offset));
                    float4 capturedMainUvAndCustom =
                        asfloat(_Dian904CapturedRows.Load4(offset + 16));
                    output.positionCS = capturedPosition;
                    output.color =
                        asfloat(_Dian904CapturedRows.Load4(offset + 48));
                    output.mainUV = capturedMainUvAndCustom.xy;
                    output.sample0UV =
                        asfloat(_Dian904CapturedRows.Load2(offset + 32));
                    output.sample1UV = 0.0.xx;
                    output.sample2UV = 0.0.xx;
                    // Original 0858 publishes the Dian904 dissolve/custom
                    // carriers in TEXCOORD0.zw. Preserve those exact lanes;
                    // x/y are algebraically dead in selected PS0859.
                    output.custom = float4(
                        0.0,
                        0.0,
                        capturedMainUvAndCustom.z,
                        capturedMainUvAndCustom.w);
                    output.screenPos = ComputeScreenPos(capturedPosition);
                    output.positionWS = 0.0.xxx;
                    output.normalWS = float3(0.0, 0.0, 1.0);
                    output.particleUV = 0.0.xxxx;
                    return output;
                #else
                UNITY_SETUP_INSTANCE_ID(input);
                #if defined(_LIGHTNING902_EXACT_RUNTIME_REPLAY)
                    input.custom.x =
                        ResolveLightning902RetailCustom1X(
                            input.custom.x,
                            _Lightning902RetailCustom1X,
                            _Lightning902RetailReplayValid,
                            _Lightning902RetailReplayMagic,
                            _Lightning902RetailReplayEpoch,
                            _Lightning902RetailPublishFrame,
                            _Lightning902RetailRendererFingerprint,
                            _Lightning902RetailReplayChecksum);
                #endif
                #if defined(_DIAN902_EXACT_MANUAL_REPLAY)
                    if (Dian902ManualReplayTupleValid())
                    {
                        input.custom.z = RecoverDian902ManualCustom1Z(
                            asuint(_Dian902ManualReplayIndex));
                        input.color = RecoverDian902ManualColor(
                            asuint(_Dian902ManualReplayIndex));
                    }
                #endif
                #if defined(_DIAN902_EXACT_DYNAMIC_REPLAY)
                    if (Dian902DynamicReplayTupleValid())
                    {
                        input.custom.z =
                            Dian902DynamicRenderCustom1Z(
                                asuint(_Dian902ManualAgePercent));
                        input.color = float4(
                            1.0,
                            0.0,
                            asfloat(0x3EDADADBu),
                            Dian902DynamicRenderFixedAlpha(
                                asuint(_Dian902ManualAgePercent)));
                    }
                #endif
                #if defined(_LINE006_EXACT_STEP_REPLAY)
                    uint scopedInvBits =
                        asuint(input.recoveryCarrier.y);
                    if (IsLightning901ThirdInvBits(scopedInvBits))
                    {
                        input.custom.x =
                            RecoverLightning901ThirdCustom1X(
                                scopedInvBits,
                                input.custom.x);
                        input.color =
                            RecoverLightning901ThirdColor(input.color);
                    }
                    else
                        input.custom.x = RecoverLine006Custom1X(input);
                #endif
                Varyings output;
                float3 positionWS;
                #if defined(_DIAN904_EXACT_DORMANT_CANDIDATE)
                    output.positionCS =
                        Dian904RetailPositionCS(input, positionWS);
                #else
                positionWS =
                    mul(unity_ObjectToWorld, input.vertex).xyz;
                float3 cameraDirectionWS =
                    _WorldSpaceCameraPos.xyz - positionWS;
                float cameraDistance = length(cameraDirectionWS);
                cameraDirectionWS /= cameraDistance;
                float cameraOffsetDistance =
                    min(
                        max(cameraDistance - 1.0, 0.0),
                        _VertCameraOffset) + 0.001;
                #if defined(_USE_VERTOFFSET)
                    // Shipped blob 1236 fuses the texture/mask displacement
                    // with camera offset before the animation-disable gate.
                    precise float maskFactor;
                    precise float3 offsetDirection =
                        Retail1236VertexOffsetDirection(
                            input, maskFactor);
                    precise float3 combinedOffset = mad(
                        offsetDirection,
                        maskFactor.xxx,
                        cameraDirectionWS * cameraOffsetDistance);
                    positionWS = mad(
                        combinedOffset,
                        (1.0 - _DisableAnimateVert).xxx,
                        positionWS);
                #else
                positionWS +=
                    cameraDirectionWS *
                    cameraOffsetDistance *
                    (1.0 - _DisableAnimateVert);
                #endif
                output.positionCS = UnityWorldToClipPos(positionWS);
                #endif
                #if defined(_DIAN904_EXACT_DORMANT_CANDIDATE)
                    precise float4 dian904OneMinusC13 =
                        1.0.xxxx - _Dian904RawPerDrawC13;
                    output.color =
                        input.color * dian904OneMinusC13;
                #elif !defined(_USE_VERTOFFSET) && defined(_SAMPLE_TEX1) && !defined(_SAMPLE_TEX2) && !defined(_USE_SOFTBLEND) && defined(UNITY_PARTICLE_INSTANCING_ENABLED)
                    // Shipped VS0036 reads the per-particle packed RGBA8
                    // carrier from UnityPerDraw c13 and multiplies it into
                    // source mesh COLOR unless _DisableParticleInstanceColor
                    // is nonzero. Stock Unity procedural particle instancing
                    // exposes the same packed RGBA8 carrier as
                    // DefaultParticleInstanceData.color. Read it directly as
                    // float32 so the exact 1/255 semantics are retained.
                    UNITY_PARTICLE_INSTANCE_DATA particleInstance =
                        unity_ParticleInstanceData[unity_InstanceID];
                    uint packedParticleColor = particleInstance.color;
                    float4 particleInstanceColor = float4(
                        packedParticleColor & 255u,
                        (packedParticleColor >> 8u) & 255u,
                        (packedParticleColor >> 16u) & 255u,
                        (packedParticleColor >> 24u) & 255u) *
                        (1.0 / 255.0);
                    output.color = _DisableParticleInstanceColor != 0.0
                        ? input.color
                        : input.color * particleInstanceColor;
                #else
                    // Preserve the established non-instanced and all other
                    // specialization behavior.
                    output.color = lerp(
                        input.color,
                        1.0.xxxx,
                        saturate(_DisableVertColor));
                #endif
                #if defined(_USE_VERTOFFSET)
                    output.mainUV = Retail1236UV(
                        input, _MainTexUVWeights, _MainTexUVSpeed,
                        _MainTexUVRotateMat, _MainTex_ST,
                        input.custom.x * _InParticle);
                    output.sample0UV = Retail1236UV(
                        input, _SampleTex0UVWeights, _SampleTex0UVSpeed,
                        _SampleTex0UVRotateMat, Retail1236Sample0ST(),
                        input.custom.x * _InParticle);
                    output.sample1UV = Retail1236UV(
                        input, _SampleTex1UVWeights, _SampleTex1UVSpeed,
                        _SampleTex1UVRotateMat, Retail1236Sample1ST(),
                        input.custom.y * _InParticle);
                #else
                    output.mainUV = BuildUV(input.uv0.xy, input.custom.x,
                        _MainTexUVWeights, _MainTexUVSpeed, _MainTexUVRotateMat, _MainTex_ST);
                    #if defined(_SAMPLE_TEX1) && !defined(_SAMPLE_TEX2) && !defined(_USE_SOFTBLEND)
                    // Exact shipped blob 0036 routes the Main custom-speed
                    // carrier from Custom1.X, but routes both Sample0 and
                    // Sample1 from Custom1.Y. Keep this scoped to its exact
                    // no-soft two-sample specialization.
                    output.sample0UV = BuildUV(input.uv0.xy, input.custom.y,
                        _SampleTex0UVWeights, _SampleTex0UVSpeed, _SampleTex0UVRotateMat, _SampleTex0_ST);
                    output.sample1UV = BuildUV(input.uv0.xy, input.custom.y,
                        _SampleTex1UVWeights, _SampleTex1UVSpeed, _SampleTex1UVRotateMat, _SampleTex1_ST);
                    #else
                    output.sample0UV = BuildUV(input.uv0.xy, input.custom.x,
                        _SampleTex0UVWeights, _SampleTex0UVSpeed, _SampleTex0UVRotateMat, _SampleTex0_ST);
                    output.sample1UV = BuildUV(input.uv0.xy, input.custom.x,
                        _SampleTex1UVWeights, _SampleTex1UVSpeed, _SampleTex1UVRotateMat, _SampleTex1_ST);
                    #endif
                #endif
                output.sample2UV = BuildUV(input.uv0.xy, input.custom.x,
                    _SampleTex2UVWeights, _SampleTex2UVSpeed, _SampleTex2UVRotateMat, _SampleTex2_ST);
                output.custom = input.custom;
                output.screenPos = ComputeScreenPos(output.positionCS);
                output.positionWS = positionWS;
                output.normalWS = normalize(UnityObjectToWorldNormal(input.normal));
                // The retail rainbow vertex blob forwards the particle
                // TEXCOORD float4 and Custom1 float4 unchanged. Its nonlinear
                // polar conversion therefore belongs in the fragment stage.
                output.particleUV = input.uv0;
                #if defined(_DIAN904_LIVE_VERT_CAPTURE_DIAGNOSTIC)
                    output.diagnosticPositionCS = output.positionCS;
                    output.diagnosticMainSampleUV = float4(
                        output.mainUV,
                        output.sample0UV);
                    output.diagnosticColor = output.color;
                    output.diagnosticCustom = output.custom;
                    // Point-list capture: vertex N lands at pixel N in a
                    // 22x1 RGBA32Float target. Computed live values remain in
                    // nointerpolation diagnostic varyings.
                    output.positionCS = float4(
                        ((proceduralVertexId + 0.5) / 22.0) * 2.0 - 1.0,
                        0.0,
                        0.0,
                        1.0);
                #endif
                return output;
                #endif
            }

            float2 RetailPolarCoordinate(float2 particleUV)
            {
                // Literal blob-1033 order. Keep the divide/comparison behavior
                // at the axes; replacing this with atan2 is not source-exact.
                float centeredX = particleUV.x - 0.5;
                float centeredY = particleUV.y - 0.5;
                float ratio = centeredX / centeredY;
                float magnitude = abs(ratio);
                bool direct = magnitude < 1.0;
                float reduced = direct ? magnitude : (1.0 / magnitude);
                float reducedSquared = reduced * reduced;
                float polynomial = mad(
                    mad(
                        reducedSquared,
                        0.087292902171611785888671875,
                        -0.3018949925899505615234375),
                    reducedSquared,
                    1.0);
                float approximateAtan = direct
                    ? reduced * polynomial
                    : mad(
                        -polynomial,
                        reduced,
                        1.57079637050628662109375);
                float signedAtan = ratio < 0.0
                    ? -approximateAtan
                    : approximateAtan;
                float quadrantAtan = centeredY < 0.0
                    ? (centeredX >= 0.0
                        ? 3.141592502593994140625
                        : -3.141592502593994140625) + signedAtan
                    : signedAtan;
                float angle = (
                    quadrantAtan +
                    3.1415927410125732421875) *
                    0.15915493667125701904296875;
                float radius = length(float2(centeredX, centeredY));
                return float2(angle, radius + radius);
            }

            float2 BuildRainbowFragmentUV(
                float4 particleUV,
                float4 custom,
                float customValue,
                float2 polarUV,
                float4 weights,
                float4 speed,
                float4 rotateMat,
                float4 textureST)
            {
                float2 rawUv1 = lerp(
                    custom.xy,
                    particleUV.zw,
                    _InParticle);
                float2 uv =
                    particleUV.xy * weights.x +
                    rawUv1 * weights.y;
                #if defined(_USE_POLARUV)
                    uv += polarUV * weights.z;
                #endif
                #if defined(_USE_SCREENUV)
                    // The only admitted screen-keyword identity has
                    // _UseScreenUV=0 and every live screen weight exactly 0.
                    // Preserve that zero without claiming a general producer.
                    uv += 0.0.xx * weights.w * _UseScreenUV;
                #endif
                float2 centered =
                    uv +
                    speed.xy * _VFXParams0.w +
                    speed.zw * customValue -
                    0.5;
                float2 rotated = float2(
                    dot(centered, rotateMat.xz),
                    dot(centered, rotateMat.yw)) + 0.5;
                return rotated * textureST.xy + textureST.zw;
            }

            float4 SampleMainPairedBias(float2 uv, float bias)
            {
                #if defined(_DIAN904_EXACT_DORMANT_CANDIDATE)
                // 0859: MainTex t1 / sampler_LinearRepeat s1.
                return _MainTex.SampleBias(
                    sampler_LinearRepeat, uv, bias + _GlobalMipBias);
                #elif defined(_SAMPLE_TEX3)
                // Exact blobs 1267/1289 (fragments 0079/0211): Main t0,
                // LinearClamp s0. The polar gfx13 specialization keeps the
                // same shipped static sampler ABI as non-polar gfx18.
                return _MainTex.SampleBias(
                    sampler_LinearClamp, uv, bias + _GlobalMipBias);
                #elif defined(_SAMPLE_TEX1) && !defined(_SAMPLE_TEX2) && !defined(_USE_SOFTBLEND)
                return _MainTex.SampleBias(
                    sampler_LinearClamp, uv, bias + _GlobalMipBias);
                #else
                return _MainTex.SampleBias(
                    sampler_MainTex, uv, bias + _GlobalMipBias);
                #endif
            }

            float4 Sample0PairedBias(float2 uv, float bias)
            {
                #if defined(_DIAN904_EXACT_DORMANT_CANDIDATE)
                // 0859: SampleTex0 t2 / sampler_LinearMirror s2. This
                // intentionally differs from the texture-derived Repeat
                // descriptor serialized by T_fx_flow_104_M.
                return _SampleTex0.SampleBias(
                    sampler_LinearMirror, uv, bias + _GlobalMipBias);
                #elif defined(_SAMPLE_TEX3)
                // Exact blobs 1267/1289: Sample0 t1, LinearRepeat s1.
                return _SampleTex0.SampleBias(
                    sampler_LinearRepeat, uv, bias + _GlobalMipBias);
                #elif defined(_SAMPLE_TEX1) && !defined(_SAMPLE_TEX2) && !defined(_USE_SOFTBLEND)
                return _SampleTex0.SampleBias(
                    sampler_LinearRepeat, uv, bias + _GlobalMipBias);
                #else
                return _SampleTex0.SampleBias(
                    sampler_SampleTex0, uv, bias + _GlobalMipBias);
                #endif
            }

            float4 Sample1PairedBias(float2 uv, float bias)
            {
                #if defined(_SAMPLE_TEX3)
                // Exact blobs 1267/1289: Sample1 t2, LinearMirror s2.
                return _SampleTex1.SampleBias(
                    sampler_LinearMirror, uv, bias + _GlobalMipBias);
                #elif defined(_SAMPLE_TEX1) && !defined(_SAMPLE_TEX2) && !defined(_USE_SOFTBLEND)
                return _SampleTex1.SampleBias(
                    sampler_LinearMirror, uv, bias + _GlobalMipBias);
                #else
                return _SampleTex1.SampleBias(
                    sampler_SampleTex1, uv, bias + _GlobalMipBias);
                #endif
            }

            float4 Sample2PairedBias(float2 uv, float bias)
            {
                #if defined(_SAMPLE_TEX3)
                // Exact blobs 1267/1289: Sample2 t3, LinearMirrorOnce s3.
                return _SampleTex2.SampleBias(
                    sampler_LinearMirrorOnce, uv, bias + _GlobalMipBias);
                #else
                return _SampleTex2.SampleBias(
                    sampler_SampleTex2, uv, bias + _GlobalMipBias);
                #endif
            }

            float4 Sample3PairedBias(float2 uv, float bias)
            {
                #if defined(_SAMPLE_TEX3)
                // Exact blobs 1267/1289: Sample3 t4, PointClamp s4.
                return _SampleTex3.SampleBias(
                    s_point_clamp_float_sampler, uv, bias + _GlobalMipBias);
                #else
                return _SampleTex3.SampleBias(
                    sampler_SampleTex3, uv, bias + _GlobalMipBias);
                #endif
            }

            float AlphaCarrier(float4 sampled, float useRed)
            {
                return lerp(sampled.a, sampled.r, saturate(useRed));
            }

            float2 DisturbCarrier(
                float4 sampled,
                float useRed,
                float useSample,
                float weight,
                float bidirectional,
                float useNormal,
                float uIntensity,
                float vIntensity)
            {
                float selector = saturate(useRed);
                float3 carrierColor = lerp(
                    sampled.rgb, 1.0.xxx, selector);
                float carrierAlpha = AlphaCarrier(sampled, selector);
                float inactive = 1.0 - saturate(useSample);
                float carrierR = mad(carrierColor.r, weight, inactive);
                float carrierG = mad(carrierColor.g, weight, inactive);
                float carrierA = mad(carrierAlpha, weight, inactive);
                // Retail blob 0877:
                //   scalar = carrierR * (Bi_Disturb + 1) - Bi_Disturb
                //   normal.x = (scalar * carrierA * 2 - 1) * UIntensity
                //   normal.y = (carrierG * 2 - 1) * UIntensity
                // The second signed remap on normal.x is significant for the
                // wooden-stake smoke, whose Sample0 carrier is active with
                // weight0=1, Bi_Disturb=1, and DisturbTex1Normal=1.
                float scalar = mad(
                    carrierR,
                    bidirectional + 1.0,
                    -bidirectional);
                float2 scalarDisturb =
                    scalar.xx * float2(uIntensity, vIntensity);
                float2 signedNormal = float2(
                    scalar * carrierA * 2.0 - 1.0,
                    carrierG * 2.0 - 1.0) * uIntensity;
                return lerp(
                    scalarDisturb,
                    signedNormal,
                    saturate(useNormal));
            }

            float DistanceFade(float3 positionWS)
            {
                // BASE blob 1254 reconstructs the fragment position and takes
                // abs(ViewMatrix * position).z. Preserve the authored signed
                // denominators: glow_902 intentionally serializes 45 -> 40
                // and 120 -> 100, so clamping either denominator changes the
                // branch rather than merely guarding it.
                float distanceToCamera = abs(
                    mul(UNITY_MATRIX_V, float4(positionWS, 1.0)).z);
                float nearFade = saturate(
                    (distanceToCamera - _NearCameraFadeDistanceStart) /
                    (_NearCameraFadeDistanceEnd -
                     _NearCameraFadeDistanceStart));
                float farFade = saturate(
                    (distanceToCamera - _NearCameraFadeDistanceStart2) /
                    (_NearCameraFadeDistanceEnd2 -
                     _NearCameraFadeDistanceStart2));
                return 0.0 != _UseNearCameraFade
                    ? nearFade * farFade
                    : 1.0;
            }

            FragmentOutput Frag(Varyings input)
            {
                #if defined(_DIAN904_LIVE_VERT_CAPTURE_DIAGNOSTIC)
                    FragmentOutput diagnostic;
                    if (_Dian904LiveVertCapturePage < 0.5)
                    {
                        diagnostic.color =
                            input.diagnosticPositionCS;
                    }
                    else if (_Dian904LiveVertCapturePage < 1.5)
                        diagnostic.color =
                            input.diagnosticMainSampleUV;
                    else if (_Dian904LiveVertCapturePage < 2.5)
                        diagnostic.color = input.diagnosticColor;
                    else
                        diagnostic.color = input.diagnosticCustom;
                    // Capture always reads target0. Target1 is zero so its
                    // authored source-color blend cannot transform payload.
                    diagnostic.sceneMV = 0.0.xxxx;
                    return diagnostic;
                #endif
                #if defined(_DIAN901_EXACT_FIXED_MANUAL_REPLAY)
                    #if defined(_DIAN901_EXACT_DYNAMIC_REPLAY)
                        clip(
                            IsDian901FixedManualReplayTuple(
                                _Dian901ManualReplayValid,
                                _Dian901ManualReplayMagic,
                                _Dian901ManualReplaySample,
                                _Dian901ManualSourceTime,
                                _Dian901ManualLiveCount,
                                _Dian901ManualReplayEpoch,
                                _Dian901ManualPublishFrame,
                                _Dian901ManualRendererFingerprint,
                                _Dian901ManualReplayChecksum) ||
                            IsDian901DynamicReplayTuple(
                                _Dian901ManualReplayValid,
                                _Dian901ManualReplayMagic,
                                _Dian901ManualReplaySample,
                                _Dian901ManualSourceTime,
                                _Dian901ManualLiveCount,
                                _Dian901ManualReplayEpoch,
                                _Dian901ManualPublishFrame,
                                _Dian901ManualRendererFingerprint,
                                _Dian901AutomaticSchedulerChecksum,
                                _Dian901AutomaticRowChecksum,
                                _Dian901ManualReplayChecksum)
                                    ? 1.0
                                    : -1.0);
                    #else
                        clip(
                            IsDian901FixedManualReplayTuple(
                                _Dian901ManualReplayValid,
                                _Dian901ManualReplayMagic,
                                _Dian901ManualReplaySample,
                                _Dian901ManualSourceTime,
                                _Dian901ManualLiveCount,
                                _Dian901ManualReplayEpoch,
                                _Dian901ManualPublishFrame,
                                _Dian901ManualRendererFingerprint,
                                _Dian901ManualReplayChecksum)
                                    ? 1.0
                                    : -1.0);
                    #endif
                #elif defined(_DIAN901_EXACT_DYNAMIC_REPLAY)
                    // The renderer-scoped clone contract always owns both
                    // keywords. Dynamic-only material drift must fail closed.
                    clip(-1.0);
                #endif
                #if defined(_LIGHTNING902_EXACT_RUNTIME_REPLAY)
                    clip(
                        IsLightning902RetailReplayTuple(
                            _Lightning902RetailCustom1X,
                            _Lightning902RetailReplayValid,
                            _Lightning902RetailReplayMagic,
                            _Lightning902RetailReplayEpoch,
                            _Lightning902RetailPublishFrame,
                            _Lightning902RetailRendererFingerprint,
                            _Lightning902RetailReplayChecksum)
                                ? 1.0
                                : -1.0);
                #endif
                #if defined(_DIAN902_EXACT_MANUAL_REPLAY)
                    #if defined(_DIAN902_EXACT_DYNAMIC_REPLAY)
                        clip(
                            Dian902ManualReplayTupleValid() ||
                            Dian902DynamicReplayTupleValid()
                                ? 1.0
                                : -1.0);
                    #else
                        clip(
                            Dian902ManualReplayTupleValid()
                                ? 1.0
                                : -1.0);
                    #endif
                #elif defined(_DIAN902_EXACT_DYNAMIC_REPLAY)
                    clip(
                        Dian902DynamicReplayTupleValid()
                            ? 1.0
                            : -1.0);
                #endif
                clip(min(_EndfieldSceneMVMRTReady,
                    _EndfieldRecoveredVFXGlobalsReady) - 0.5);

                float2 mainUV = input.mainUV;
                float2 sample0UV = input.sample0UV;
                float2 sample1UV = input.sample1UV;
                float2 sample2UV = input.sample2UV;
                float2 sample3UV = 0.0.xx;
                #if defined(_SAMPLE_TEX3)
                    float2 polarUV = 0.0.xx;
                    #if defined(_USE_POLARUV)
                    polarUV = RetailPolarCoordinate(input.particleUV.xy);
                    #endif
                    // Retail uses Custom1.X for Main and Custom1.Y for all
                    // samples. Sample3 speed.z=1 advances U by Custom1.Y.
                    mainUV = BuildRainbowFragmentUV(
                        input.particleUV, input.custom, input.custom.x,
                        polarUV, _MainTexUVWeights, _MainTexUVSpeed,
                        _MainTexUVRotateMat, _MainTex_ST);
                    sample0UV = BuildRainbowFragmentUV(
                        input.particleUV, input.custom, input.custom.y,
                        polarUV, _SampleTex0UVWeights, _SampleTex0UVSpeed,
                        _SampleTex0UVRotateMat, _SampleTex0_ST);
                    sample1UV = BuildRainbowFragmentUV(
                        input.particleUV, input.custom, input.custom.y,
                        polarUV, _SampleTex1UVWeights, _SampleTex1UVSpeed,
                        _SampleTex1UVRotateMat, _SampleTex1_ST);
                    sample2UV = BuildRainbowFragmentUV(
                        input.particleUV, input.custom, input.custom.y,
                        polarUV, _SampleTex2UVWeights, _SampleTex2UVSpeed,
                        _SampleTex2UVRotateMat, _SampleTex2_ST);
                    sample3UV = BuildRainbowFragmentUV(
                        input.particleUV, input.custom, input.custom.y,
                        polarUV, _SampleTex3UVWeights, _SampleTex3UVSpeed,
                        _SampleTex3UVRotateMat, _SampleTex3_ST);
                #endif

                float4 sample0 = Sample0PairedBias(sample0UV,
                    trunc(_SampleTex0MipmapBias));
                // Selected retail BaseV2 blobs gate both disturbance carriers
                // with UseParticleDisturb, not DisturbUseWeight. Ordinary
                // signatures (including 0877 and 1237) use Custom1.W alone.
                float particleDisturbWeight =
                    0.0 != _UseParticleDisturb
                    ? input.custom.w
                    : 1.0;
                // The selected rainbow 1033 polar+screen signature is the one
                // shipped exception: its gate also multiplies InParticle.
                #if defined(_USE_POLARUV) && defined(_USE_SCREENUV)
                    particleDisturbWeight =
                        0.0 != _UseParticleDisturb
                        ? input.custom.w * _InParticle
                        : 1.0;
                #endif
                // Blobs 0019/0037 route Sample0 weight 0 to Disturb1.
                // Blob 0037 then applies that disturbance to Sample1 UV only
                // when SampleTex1UseDisturb is authored, before Sample1 can
                // contribute the independently weighted Disturb2 carrier.
                float2 disturb1 = DisturbCarrier(
                    sample0,
                    _UseSampleTex0AsAlpha,
                    _UseSampleTex0,
                    _SampleTex0UseWeight0,
                    _Bi_Disturb,
                    _DisturbTex1Normal,
                    _DisturbUIntensity1,
                    _DisturbVIntensity1) *
                    saturate(_UseDisturb) *
                    particleDisturbWeight;
                float4 sample1 = Sample1PairedBias(
                    sample1UV +
                    disturb1 * saturate(_SampleTex1UseDisturb),
                    trunc(_SampleTex1MipmapBias));
                float2 disturb2 = DisturbCarrier(
                    sample1,
                    _UseSampleTex1AsAlpha,
                    _UseSampleTex1,
                    _SampleTex1UseWeight1,
                    _Bi_Disturb,
                    _DisturbTex2Normal,
                    _DisturbUIntensity2,
                    _DisturbVIntensity2) *
                    saturate(_UseDisturb2) *
                    particleDisturbWeight;
                float2 disturb = disturb1 + disturb2;
                float4 sample2 = Sample2PairedBias(
                    sample2UV,
                    trunc(_SampleTex2MipmapBias));
                float4 sample3 = Sample3PairedBias(
                    sample3UV + disturb * saturate(_SampleTex3UseDisturb),
                    trunc(_SampleTex3MipmapBias));
                float mask = 1.0;
                float dissolveCarrier = 1.0;

                #if defined(_SAMPLE_TEX3)
                    mask = AlphaCarrier(sample1, _UseSampleTex1AsAlpha);
                    dissolveCarrier = lerp(
                        sample3.r, 1.0, saturate(_UseSampleTex3AsAlpha));
                #elif defined(_SAMPLE_TEX2)
                    mask = AlphaCarrier(sample1, _UseSampleTex1AsAlpha);
                    dissolveCarrier = sample2.r;
                #elif defined(_SAMPLE_TEX1)
                    mask = AlphaCarrier(sample0, _UseSampleTex0AsAlpha);
                    dissolveCarrier = sample1.r;
                #elif defined(_SAMPLE_TEX0)
                    dissolveCarrier = sample0.r;
                #endif

                float4 mainSample = SampleMainPairedBias(
                    mainUV + disturb * saturate(_MainTexUseDisturb),
                    trunc(_MainTexMipmapBias));
                float mainAlpha = AlphaCarrier(mainSample, _UseMainTexAsAlpha);
                float3 mainColor = lerp(mainSample.rgb, 1.0.xxx,
                    saturate(_UseMainTexAsAlpha));
                float sample0UseWeight4 = saturate(_SampleTex0UseWeight4);
                float3 remappedSample0Color = lerp(sample0.rgb,
                    1.0.xxx,
                    saturate(_UseSampleTex0AsAlpha));
                float remappedSample0Alpha =
                    AlphaCarrier(sample0, _UseSampleTex0AsAlpha);
                float sample2UseWeight4 =
                    saturate(_SampleTex2UseWeight4);
                float3 remappedSample2Color = lerp(
                    sample2.rgb,
                    1.0.xxx,
                    saturate(_UseSampleTex2AsAlpha));
                float remappedSample2Alpha =
                    AlphaCarrier(sample2, _UseSampleTex2AsAlpha);
                float authoredMask;
                float3 authoredColorMask = 1.0.xxx;
                #if defined(_SAMPLE_TEX3)
                    // Exact blob 1289 routes Sample0/Sample1 to the two
                    // disturbance carriers, Sample2 to mask/blend, and
                    // Sample3 to dissolve. The earlier soft-blob translation
                    // incorrectly treated Sample1 as the visible mask.
                    float3 remappedSample1Color = lerp(
                        sample2.rgb,
                        1.0.xxx,
                        saturate(_UseSampleTex2AsAlpha));
                    float remappedSample1Alpha =
                        AlphaCarrier(sample2, _UseSampleTex2AsAlpha);
                    float sample2UseWeight3 =
                        abs(_SampleTex2Use - 3.0) < 0.5 ? 1.0 : 0.0;
                    authoredColorMask = mad(
                        remappedSample1Color,
                        sample2UseWeight3.xxx,
                        (1.0 - _UseMask).xxx);
                    authoredMask = mad(
                        remappedSample1Alpha,
                        sample2UseWeight3,
                        1.0 - _UseMask);
                #elif defined(_SAMPLE_TEX1) && !defined(_SAMPLE_TEX2)
                    // Exact retail blob 0037 (_SAMPLE_TEX0 +
                    // _SAMPLE_TEX1) keeps the two weight-3 carriers
                    // component-wise for RGB and independently for alpha.
                    // Collapsing this branch to the scalar `mask` carrier
                    // discards Sample0 color in the Zhuangfy lightning,
                    // redwave, and speedup-wind identities.
                    float3 remappedSample1Color = lerp(
                        sample1.rgb,
                        1.0.xxx,
                        saturate(_UseSampleTex1AsAlpha));
                    float remappedSample1Alpha =
                        AlphaCarrier(sample1, _UseSampleTex1AsAlpha);
                    authoredColorMask = mad(
                        remappedSample1Color,
                        _SampleTex1UseWeight3.xxx,
                        mad(
                            remappedSample0Color,
                            _SampleTex0UseWeight3.xxx,
                            (1.0 - _UseMask).xxx));
                    authoredMask = mad(
                        remappedSample1Alpha,
                        _SampleTex1UseWeight3,
                        mad(
                            remappedSample0Alpha,
                            _SampleTex0UseWeight3,
                            1.0 - _UseMask));
                #elif defined(_SAMPLE_TEX0) && !defined(_SAMPLE_TEX1)
                    // Blob 1397/33 applies the sample-0 weight-3 carrier
                    // independently to RGB and alpha:
                    //   rgbMask = sample0Remapped.rgb * weight3 + 1 - UseMask
                    //   alphaMask = sample0Remapped.a * weight3 + 1 - UseMask
                    // This is not a scalar alpha-only mask.  It is neutral for
                    // the admitted Blend/dissolve identities, whose weight3
                    // and UseMask are both zero.
                    authoredColorMask = mad(
                        remappedSample0Color,
                        _SampleTex0UseWeight3.xxx,
                        (1.0 - _UseMask).xxx);
                    authoredMask = mad(
                        remappedSample0Alpha,
                        _SampleTex0UseWeight3,
                        1.0 - _UseMask);
                #else
                    authoredMask = lerp(1.0, mask, saturate(_UseMask));
                #endif
                #if defined(_DIAN904_EXACT_DORMANT_CANDIDATE)
                    // The original b4 payload consumes the raw serialized
                    // Material vector. Unity Color properties are converted
                    // for linear rendering before shader upload, so the
                    // diagnostic-only 0858/0859 candidate uses a Vector
                    // transport populated directly from the source JSON.
                    float4 activeTintColor = _Dian904RawTintColor;
                #else
                    float4 activeTintColor = lerp(
                        _TintColor,
                        _RecoveredRawTintColor,
                        saturate(_UseRecoveredRawTintColor));
                #endif
                float preMaskMainAlpha = mainAlpha * activeTintColor.a *
                    _TintColorAlpha * input.color.a;

                float dissolveThreshold = mad(
                    input.custom.z + _DissolveScheduleOffset,
                    2.0199999809265137, -1.0099999904632568);
                float dissolveDelta = dissolveCarrier - dissolveThreshold;
                float dissolveAlpha = saturate(dissolveDelta * _DissolveEdgeSharp);
                float dissolveEdge = saturate(
                    (_DissolveEmissiveEdge - dissolveDelta) * _DissolveEdgeSharp);

                float3 color = mainColor * authoredColorMask *
                    input.color.rgb * activeTintColor.rgb *
                    _TintColorIntensity;
                float3 dissolveEdgeColor =
                    dissolveEdge * _DissolveEmissiveColor.rgb *
                    _TintColorIntensity;
                #if defined(_SAMPLE_TEX3) && defined(_USE_POLARUV)
                    // Blob 1426 forms base + Sample2 blend first, then applies
                    // the dissolve-edge interpolation to that combined RGB.
                    float blendFactor = saturate((
                        preMaskMainAlpha * authoredMask +
                        remappedSample2Alpha * sample2UseWeight4) *
                        _UseBlend);
                    color += blendFactor *
                        (remappedSample2Color * sample2UseWeight4) *
                        _BlendTint.rgb;
                    float3 dissolvedColor =
                        lerp(color, dissolveEdgeColor, dissolveEdge);
                    color = lerp(
                        color,
                        dissolvedColor,
                        saturate(_UseDissolve));
                #else
                    // Previously admitted blobs apply their bounded dissolve
                    // carrier before their blend specialization.
                    float3 dissolvedColor =
                        lerp(color, dissolveEdgeColor, dissolveEdge);
                    color = lerp(
                        color,
                        dissolvedColor,
                        saturate(_UseDissolve));
                    #if defined(_SAMPLE_TEX2) && !defined(_SAMPLE_TEX3)
                    // The M35 three-sample/vertex-offset specialization
                    // authors Sample2 as Blend (Use=4, weight4=1) while
                    // Sample0 is disturbance-only (weight4=0). Routing this
                    // branch through Sample0 discards the streak texture and
                    // exposes the dark Loft carrier silhouette.
                    float blendFactor = saturate((
                        preMaskMainAlpha * authoredMask +
                        remappedSample2Alpha * sample2UseWeight4) *
                        _UseBlend);
                    color += blendFactor *
                        (remappedSample2Color * sample2UseWeight4) *
                        _BlendTint.rgb;
                    #else
                    float blendFactor = saturate((
                        preMaskMainAlpha * authoredMask +
                        remappedSample0Alpha * sample0UseWeight4) *
                        _UseBlend);
                    color += blendFactor *
                        (remappedSample0Color * sample0UseWeight4) *
                        _BlendTint.rgb;
                    #endif
                #endif

                // 0961/0955 exact selected Fresnel branch.  The source takes
                // the powered biased N.V term, optionally flips it, uses it
                // directly for opacity, and uses FresnelColor.a only for the
                // RGB interpolation weight.
                float fresnel = 1.0;
                #if defined(_USE_FRESNEL)
                    float3 viewDirectionWS = normalize(
                        _WorldSpaceCameraPos.xyz - input.positionWS);
                    float biasedNdotV = saturate(
                        dot(viewDirectionWS, normalize(input.normalWS)) +
                        _FresnelBias);
                    float poweredFresnel = pow(biasedNdotV, _FresnelPower);
                    fresnel = lerp(
                        1.0 - poweredFresnel,
                        poweredFresnel,
                        _FresnelFlip);
                    color = lerp(
                        color,
                        _FresnelColor.rgb,
                        fresnel * _FresnelColor.a);
                #endif

                color += max(color - _ExpThreshold, 0.0) * _ExpIntensity;
                // Exact 0139 forms mad(reciprocalExposure,
                // IgnorePostExposure, 1-IgnorePostExposure) and multiplies
                // final RGB by the result.
                color *= lerp(1.0, _ExposureWithMiscParams.y,
                    saturate(_IgnorePostExposure));
                color = clamp(color, 0.0, 1000.0);

                float alpha = preMaskMainAlpha * authoredMask;
                alpha *= lerp(1.0, dissolveAlpha, saturate(_UseDissolve));
                #if defined(_USE_FRESNEL)
                    alpha *= lerp(
                        1.0, fresnel, _FresnelAffectOpacity);
                #endif
                alpha *= DistanceFade(input.positionWS);

                #if defined(_USE_SOFTBLEND)
                    #if defined(_DIAN904_EXACT_DORMANT_CANDIDATE)
                        // Literal PS0859 lines 45-73. Preserve the distinct
                        // integer-pixel scene reconstruction, continuous
                        // scene-depth sample UV, inverse-VP rows, view-Z dot,
                        // c3.z offset, abs subtraction, and soft parameters.
                        uint2 dian904PixelUint =
                            (uint2)input.positionCS.xy;
                        precise float2 dian904Pixel =
                            (float2)dian904PixelUint;
                        precise float2 dian904SceneNdc =
                            dian904Pixel * _Dian904PSB1C0.zw;
                        dian904SceneNdc = mad(
                            dian904SceneNdc,
                            2.0.xx,
                            -1.0.xx);
                        precise float4 dian904SceneH =
                            (-dian904SceneNdc.y) * _Dian904PSB0C25;
                        dian904SceneH = mad(
                            _Dian904PSB0C24,
                            dian904SceneNdc.x,
                            dian904SceneH);

                        precise float2 dian904DepthUv =
                            input.positionCS.xy * _Dian904PSB1C0.zw;
                        float sceneRawDepth = _SceneDepth.SampleLevel(
                            sampler_LinearClamp, dian904DepthUv, 0.0);
                        precise float2 dian904ParticleNdc = mad(
                            dian904DepthUv,
                            2.0.xx,
                            -1.0.xx);
                        dian904SceneH = mad(
                            _Dian904PSB0C26,
                            sceneRawDepth,
                            dian904SceneH);
                        dian904SceneH += _Dian904PSB0C27;
                        precise float3 dian904ScenePosition =
                            dian904SceneH.xyz / dian904SceneH.w;
                        precise float dian904SceneViewZ =
                            dian904ScenePosition.y * _Dian904PSB0C1.z;
                        dian904SceneViewZ = mad(
                            _Dian904PSB0C0.z,
                            dian904ScenePosition.x,
                            dian904SceneViewZ);
                        dian904SceneViewZ = mad(
                            _Dian904PSB0C2.z,
                            dian904ScenePosition.z,
                            dian904SceneViewZ);

                        precise float4 dian904ParticleH =
                            (-dian904ParticleNdc.y) *
                            _Dian904PSB0C25;
                        dian904ParticleH = mad(
                            _Dian904PSB0C24,
                            dian904ParticleNdc.x,
                            dian904ParticleH);
                        dian904ParticleH = mad(
                            _Dian904PSB0C26,
                            input.positionCS.z,
                            dian904ParticleH);
                        dian904ParticleH += _Dian904PSB0C27;
                        precise float3 dian904ParticlePosition =
                            dian904ParticleH.xyz /
                            dian904ParticleH.w;
                        precise float dian904ParticleViewZ =
                            dian904ParticlePosition.y *
                            _Dian904PSB0C1.z;
                        dian904ParticleViewZ = mad(
                            _Dian904PSB0C0.z,
                            dian904ParticlePosition.x,
                            dian904ParticleViewZ);
                        dian904ParticleViewZ = mad(
                            _Dian904PSB0C2.z,
                            dian904ParticlePosition.z,
                            dian904ParticleViewZ);
                        dian904SceneViewZ += _Dian904PSB0C3.z;
                        dian904ParticleViewZ += _Dian904PSB0C3.z;
                        precise float dian904SoftFactor = saturate((
                            abs(dian904SceneViewZ) -
                            abs(dian904ParticleViewZ) +
                            _SoftBias) / _SoftDistance);
                        alpha *= dian904SoftFactor;
                    #else
                        // Blob 0841 reconstructs scene/particle positions
                        // through inverse VP and evaluates
                        // abs(ViewMatrix * position).z. For Unity's
                        // perspective projection this reduces to
                        // LinearEyeDepth(rawDepth); retain that public-engine
                        // translation for every non-Dian904 specialization.
                        float2 particlePixelUV = input.positionCS.xy *
                            _SceneDepth_TexelSize.xy;
                        float sceneRawDepth = _SceneDepth.SampleLevel(
                            s_point_clamp_float_sampler, particlePixelUV, 0.0);
                        float sceneAbsoluteViewZ =
                            LinearEyeDepth(sceneRawDepth);
                        // The selected blob evaluates abs(ViewMatrix *
                        // particleWorldPosition).z. Fragment SV_Position.z is
                        // the rasterizer's device-depth value and is not an
                        // equivalent particle-position carrier on D3D12.
                        float particleAbsoluteViewZ = abs(mul(
                            UNITY_MATRIX_V,
                            float4(input.positionWS, 1.0)).z);
                        alpha *= saturate((
                            sceneAbsoluteViewZ -
                            particleAbsoluteViewZ +
                            _SoftBias) / _SoftDistance);
                    #endif
                #endif

                alpha = saturate(lerp(1.0, alpha, saturate(_ProcedureAlpha)));
                float positionHash = frac(frac(dot(input.positionCS.xy,
                    float2(0.0671105608344078, 0.00583714991807938))) *
                    52.98291778564453);
                float signedHash = _RecoveredLODFade.x >= 0.0
                    ? positionHash
                    : -positionHash;
                float ditherPass = _RecoveredLODFade.x - signedHash > 0.0
                    ? 1.0
                    : 1.0 - _SurfaceType;
                float coverage = ditherPass *
                    ((1.0 - _RecoveredLODFade.y) * alpha);
                float coverageComplement = 1.0 - coverage;
                float isMultiply = step(1.5, _BlendMode);
                float3 premultiplied = lerp(color * coverage,
                    color * coverage + coverageComplement, isMultiply);
                float outputAlpha = coverage * (1.0 - saturate(_BlendMode));
                float coverageLuma = dot(color,
                    float3(0.2126729041, 0.7151522040, 0.0721750036));
                float coverageActiveMask = step(0.5,
                    saturate(max(outputAlpha, coverage * coverageLuma) * 10.0)) *
                    _SurfaceType * _Responsive;

                FragmentOutput output;
                output.color = float4(premultiplied, outputAlpha);
                // Explicit boundary: the selected visible non-instanced
            // All 53 selected materials author _SurfaceType=1 and
            // _EnableTransparentMV=0. The 15 exact selected fragment
            // signatures therefore gate sceneMV XY to zero. Generic
            // transparent-motion-on transport remains outside this shader.
            output.sceneMV = float4(0.0, 0.0, 1.0, coverageActiveMask);
                return output;
            }
            ENDCG
        }
    }
    Fallback Off
}
