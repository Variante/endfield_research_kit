Shader "Hidden/Endfield/Recovered/Endminf/M27LitEffectHGBuffer"
{
    Properties
    {
        _BaseColorMap ("Base Color Map", 2D) = "white" {}
        _NormalMap ("Normal Map", 2D) = "bump" {}
        _MROMap ("MRO Map", 2D) = "white" {}
        _ParallaxNoiseMap ("Parallax Noise Map", 2D) = "black" {}
        _ParallaxMaskMap ("Parallax Mask Map", 2D) = "black" {}
        _ParallaxMap ("Parallax Map", 2D) = "black" {}

        _BaseColor ("Base Color", Color) = (1, 1, 1, 1)
        _BaseUVSet ("Base UV Set", Float) = 0
        _BasePbrMapUVSet ("Base PBR UV Set", Float) = 0
        _BaseTextureMapCount ("Base Texture Map Count", Float) = 0
        _BaseColorTintCover ("Base Color Tint Cover", Float) = 0
        _BaseColorBrighterScale ("Base Color Brighter Scale", Float) = 1
        _NormalScale ("Normal Scale", Float) = 1
        _TwoSidedNormal ("Two Sided Normal", Float) = 1
        _Metallic ("Metallic", Float) = 0
        _RoughnessMin ("Roughness Minimum", Float) = 0
        _RoughnessMax ("Roughness Maximum", Float) = 1
        _OcclusionStrength ("Occlusion Strength", Float) = 1

        _ParallaxStrength ("Parallax Strength", Float) = 0.096
        _ParallaxMarchNum ("Parallax March Count", Float) = 5
        _ParallaxTilling ("Parallax Tiling", Float) = 3.36
        _ParallaxAnimSpeed ("Parallax Animation Speed", Float) = 0
        _ParallaxAnimRandom ("Parallax Animation Random", Float) = 1
        _ParallaxMinBrightness ("Parallax Minimum Brightness", Float) = 0.2
        _ParallaxFresnelStrength ("Parallax Fresnel Strength", Float) = 1
        _ParallaxIgnorePostExposure ("Parallax Ignore Post Exposure", Float) = 1
        _ParallaxMaskChannel ("Parallax Mask Channel", Float) = 0
        _ParallaxMapUVType ("Parallax Map UV Type", Float) = 0
        _ParallaxMaskByLayerBlend ("Parallax Mask By Layer Blend", Float) = 0
        _ParallaxNoiseMapTilling ("Parallax Noise Map Tiling", Float) = 1
        _ParallaxCharPos ("Parallax Character Position", Float) = 0
        _ParallaxBrightOuterRadius ("Parallax Bright Outer Radius", Float) = 20
        _ParallaxBrightInnerRadius ("Parallax Bright Inner Radius", Float) = 10
        _ParallaxBrightStrength ("Parallax Bright Strength", Float) = 1
        _UseParallaxMask ("Use Parallax Mask", Float) = 0
        _ParallaxMaskMapColorStrength ("Parallax Mask Color Strength", Float) = 1
        _ParallaxIntensity ("Parallax Intensity", Float) = 1
        [HDR] _ParallaxColor ("Parallax Color", Color) = (964.7226, 330.88165, 85.55083, 1)
        [HDR] _ParallaxColorDark ("Parallax Color Dark", Color) = (0, 0, 0, 1)

        _TAAUNormalBiasReverse ("TAAU Normal Bias Reverse", Float) = 0
        _TaauMaskModeValue ("TAAU Mask Mode Value", Float) = 0
        _StencilRef ("Stencil Reference", Float) = 0
        _StencilOpGBuffer ("Stencil GBuffer Operation", Float) = 2

        // These are engine/per-draw inputs, not material tuning. Their defaults
        // are the exact values captured for M27 at retail frame 7439.
        [HideInInspector] _GlobalMipBias ("Global Mip Bias", Float) = -1
        [HideInInspector] _HGRPExposureMultiplier ("HGRP Exposure Multiplier", Float) = 1
        [HideInInspector] _VFXParams0 ("VFX Parameters 0", Vector) = (-67.2910004, 1.3897357, 0.389, 235.5681)
        [HideInInspector] _AnchorWaveBright ("Anchor Wave Bright", Vector) = (0, 0, 0, 0)
        [HideInInspector] _TerrainSubsurfaceProfileInt ("Terrain Subsurface Profile", Float) = 0
        [HideInInspector] _RecoveredM27InstanceRecordC3 ("Captured Instance Record c3", Vector) = (0, 0, 0, 1)
        [HideInInspector] _RecoveredM27InstanceRecordC4 ("Captured Instance Record c4", Vector) = (1000, 0, 0, 0)
        [HideInInspector] _RecoveredSourceAuthoredLitEffect ("Source-authored live LitEffect", Float) = 0
    }

    SubShader
    {
        LOD 600
        Tags
        {
            "RenderPipeline" = "HGRenderPipeline"
            "RenderType" = "HGLitShader"
        }

        Pass
        {
            Name "RecoveredEndminfM27HGBuffer"
            Tags
            {
                "LightMode" = "GBuffer"
                "RenderPipeline" = "HGRenderPipeline"
                "RenderType" = "HGLitShader"
            }

            // Hash-pinned HGBuffer pass state: ZTest Off, Cull Off, writable
            // depth through the bound depth attachment, and stencil replace.
            ZTest Off
            ZWrite On
            Cull Off
            Blend Off
            Stencil
            {
                Ref [_StencilRef]
                Comp Always
                Pass [_StencilOpGBuffer]
                Fail Keep
                ZFail Keep
            }

            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex Vert
            #pragma fragment Frag

            #include "UnityCG.cginc"

            Texture2D<float4> _BaseColorMap;
            Texture2D<float4> _NormalMap;
            Texture2D<float4> _MROMap;
            Texture2D<float4> _ParallaxNoiseMap;
            Texture2D<float4> _ParallaxMaskMap;
            Texture2D<float4> _ParallaxMap;

            // The retail program uses static samplers in this exact order.
            SamplerState sampler_LinearClamp;
            SamplerState sampler_LinearRepeat;
            SamplerState sampler_LinearMirror;
            SamplerState sampler_LinearMirrorOnce;
            SamplerState sampler_PointClamp;
            SamplerState sampler_PointRepeat;

            float4 _BaseColorMap_ST;
            float4 _NormalMap_ST;
            float4 _BaseColor;
            float4 _ParallaxColor;
            float4 _ParallaxColorDark;

            float _BaseUVSet;
            float _BasePbrMapUVSet;
            float _BaseTextureMapCount;
            float _BaseColorTintCover;
            float _BaseColorBrighterScale;
            float _NormalScale;
            float _TwoSidedNormal;
            float _Metallic;
            float _RoughnessMin;
            float _RoughnessMax;
            float _OcclusionStrength;

            float _ParallaxStrength;
            float _ParallaxMarchNum;
            float _ParallaxTilling;
            float _ParallaxAnimSpeed;
            float _ParallaxAnimRandom;
            float _ParallaxMinBrightness;
            float _ParallaxFresnelStrength;
            float _ParallaxIgnorePostExposure;
            float _ParallaxMaskChannel;
            float _ParallaxMapUVType;
            float _ParallaxMaskByLayerBlend;
            float _ParallaxNoiseMapTilling;
            float _ParallaxCharPos;
            float _ParallaxBrightOuterRadius;
            float _ParallaxBrightInnerRadius;
            float _ParallaxBrightStrength;
            float _UseParallaxMask;
            float _ParallaxMaskMapColorStrength;
            float _ParallaxIntensity;

            float _TAAUNormalBiasReverse;
            float _TaauMaskModeValue;
            float _GlobalMipBias;
            float _GlobalMipBiasPow2;
            float _HGRPExposureMultiplier;
            float4 _VFXParams0;
            float4 _AnchorWaveBright;
            float _TerrainSubsurfaceProfileInt;
            float4 _RecoveredM27InstanceRecordC3;
            float4 _RecoveredM27InstanceRecordC4;
            float _RecoveredSourceAuthoredLitEffect;

            struct Attributes
            {
                float3 positionOS : POSITION;
                float3 normalOS : NORMAL;
                float4 tangentOS : TANGENT;
                float4 color : COLOR;
                float2 uv0 : TEXCOORD0;
                float2 uv1 : TEXCOORD1;
                // Unity ParticleSystem Custom1XYZW is the bounded carrier for
                // retail TEXCOORD4. For M27 it carries previous-frame position.
                float4 previousPositionOS : TEXCOORD2;
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float2 uv0 : TEXCOORD0;
                float2 uv1 : TEXCOORD1;
                float3 normalWS : TEXCOORD2;
                float4 tangentWS : TEXCOORD3;
                float3 positionWS : TEXCOORD4;
                float3 currentScreenPosition : TEXCOORD5;
                float3 previousScreenPosition : TEXCOORD6;
                nointerpolation uint instanceIndex : TEXCOORD7;
                nointerpolation float particlePhase : TEXCOORD8;
            };

            struct M27HGBufferOutput
            {
                float4 sceneColor : SV_Target0;
                float4 sceneMotion : SV_Target1;
                float4 gBufferA : SV_Target2;
                float4 gBufferB : SV_Target3;
                float4 gBufferC : SV_Target4;
            };

            float SignedUnit(float value)
            {
                return value > 0.0 ? 1.0 : (value < 0.0 ? -1.0 : 0.0);
            }

            float SmoothCubic(float value)
            {
                return value * value * mad(value, -2.0, 3.0);
            }

            Varyings Vert(Attributes input)
            {
                Varyings output;

                // Retail expands 15 copies of the 72-index unskinned source
                // mesh before this draw. Unity ParticleSystem supplies that
                // expanded geometry, so this port intentionally does not use
                // UnityStandardParticleInstancing or _VertexSkinMatrices.
                float4 positionWS = mul(unity_ObjectToWorld, float4(input.positionOS, 1.0));
                float4 positionCS = mul(UNITY_MATRIX_VP, positionWS);

                // The diagnostic M27 packet carries previous position in the
                // retained TEXCOORD4 envelope. The maintained route instead
                // consumes Unity's live source ParticleSystem; its Custom1.x
                // is the authored per-particle phase and motion comes from the
                // current geometry until the original particle history
                // carrier is recovered.
                float3 previousPositionOS = lerp(
                    input.previousPositionOS.xyz,
                    input.positionOS,
                    saturate(_RecoveredSourceAuthoredLitEffect));
                float4 previousPositionWS = mul(
                    unity_ObjectToWorld,
                    float4(previousPositionOS, 1.0));
                float4 previousPositionCS = mul(UNITY_MATRIX_VP, previousPositionWS);

                output.positionCS = positionCS;
                output.uv0 = input.uv0;
                output.uv1 = input.uv1;
                output.normalWS = normalize(UnityObjectToWorldNormal(input.normalOS));
                output.tangentWS = float4(
                    normalize(UnityObjectToWorldDir(input.tangentOS.xyz)),
                    input.tangentOS.w * unity_WorldTransformParams.w);
                output.positionWS = positionWS.xyz;
                output.currentScreenPosition = positionCS.xyw;
                output.previousScreenPosition = previousPositionCS.xyw;
                output.instanceIndex = 0u;
                output.particlePhase = input.previousPositionOS.x;
                return output;
            }

            M27HGBufferOutput Frag(
                Varyings input,
                bool isFrontFace : SV_IsFrontFace)
            {
                M27HGBufferOutput output;

                float2 uvDelta = input.uv1 - input.uv0;
                float2 baseUV = mad(
                    lerp(input.uv0, input.uv1, _BaseUVSet),
                    _BaseColorMap_ST.xy,
                    _BaseColorMap_ST.zw);
                float2 pbrUV = mad(
                    lerp(input.uv0, input.uv1, _BasePbrMapUVSet),
                    _NormalMap_ST.xy,
                    _NormalMap_ST.zw);

                float4 baseSample = _BaseColorMap.SampleBias(
                    sampler_LinearClamp,
                    baseUV,
                    _GlobalMipBias);
                float4 normalSample = _NormalMap.SampleBias(
                    sampler_LinearRepeat,
                    pbrUV,
                    _GlobalMipBias);
                float4 mroSample = _MROMap.SampleBias(
                    sampler_LinearMirror,
                    pbrUV,
                    _GlobalMipBias);

                // Exact normal decode: X is stored in R*A, Y in G. Z is
                // reconstructed before NormalScale is applied to XY.
                float2 normalXY = mad(
                    float2(normalSample.r * normalSample.a, normalSample.g),
                    2.0,
                    -1.0);
                float normalZ = max(
                    sqrt(1.0 - min(dot(normalXY, normalXY), 1.0)),
                    1.0000000168623835e-16);
                if (_TwoSidedNormal > 0.0 && !isFrontFace)
                    normalZ = -normalZ;

                float3 geometricNormal = normalize(input.normalWS);
                float3 tangent = normalize(input.tangentWS.xyz);
                float3 bitangent = cross(geometricNormal, tangent) * input.tangentWS.w;
                float3 normalWS = normalize(
                    geometricNormal * normalZ +
                    tangent * (normalXY.x * _NormalScale) +
                    bitangent * (normalXY.y * _NormalScale));

                float3 tintedBase = saturate(
                    baseSample.rgb * _BaseColor.rgb * _BaseColorBrighterScale);
                output.gBufferC = float4(
                    lerp(tintedBase, _BaseColor.rgb, _BaseColorTintCover),
                    0.0);

                float parallaxMask;
                if (_UseParallaxMask != 0.0)
                {
                    float maskTexture = _ParallaxMaskMap.SampleBias(
                        sampler_PointClamp,
                        input.uv1,
                        _GlobalMipBias).r;
                    parallaxMask = lerp(
                        baseSample.a * _ParallaxMaskMapColorStrength,
                        maskTexture,
                        _UseParallaxMask);
                }
                else
                {
                    float selectedMask = lerp(
                        baseSample.a,
                        mroSample.a,
                        saturate(_ParallaxMaskChannel - 1.0));
                    parallaxMask = selectedMask * (1.0 - _ParallaxMaskByLayerBlend);
                }

                float3 viewWS = normalize(_WorldSpaceCameraPos.xyz - input.positionWS);
                float3 viewTS = float3(
                    dot(input.tangentWS.xyz, viewWS),
                    dot(bitangent, viewWS),
                    dot(geometricNormal, viewWS));
                float inverseViewTSLength = rsqrt(dot(viewTS, viewTS));
                float2 parallaxBaseUV = mad(_ParallaxMapUVType, uvDelta, input.uv0);

                uint marchCount = min((uint)_ParallaxMarchNum, 20u);
                float inverseMarchCount = rcp((float)marchCount);
                float normalizedViewZ = viewTS.z * inverseViewTSLength;
                float rayDenominator = mad(normalizedViewZ, 1.0, 0.41999998688697815);
                float safeViewZ = max(normalizedViewZ, 0.0010000000474974513);
                float2 rayDelta =
                    ((viewTS.xy * inverseViewTSLength) / rayDenominator) /
                    safeViewZ * (-_ParallaxStrength);
                float2 rayStep = rayDelta * inverseMarchCount;

                float2 previousRayOffset = 0.0;
                float previousHeight = 0.0;
                float previousLayer = 1.0;
                float layer = 1.0 - inverseMarchCount;
                float2 rayOffset = rayStep;
                float hitHeight = 0.0;

                // ShaderVariablesGlobal c26.y is _GlobalMipBiasPow2 in the
                // recovered source metadata. Consume that live engine value
                // instead of replaying the captured 0.5 value.
                float2 uvDx = ddx_coarse(input.uv0) * _GlobalMipBiasPow2;
                float2 uvDy = ddy_coarse(input.uv0) * _GlobalMipBiasPow2;

                [loop]
                for (uint stepIndex = 0u; stepIndex < marchCount + 1u; ++stepIndex)
                {
                    // Physical t5 is _ParallaxNoiseMap. PackedBinding and
                    // the pinned DXBC both place the height march here;
                    // physical t3 is sampled only after the intersection.
                    float sampledHeight = _ParallaxNoiseMap.SampleGrad(
                        sampler_PointRepeat,
                        parallaxBaseUV * _ParallaxNoiseMapTilling + rayOffset,
                        uvDx,
                        uvDy).r;
                    if (layer < sampledHeight)
                    {
                        hitHeight = sampledHeight;
                        break;
                    }

                    previousRayOffset = rayOffset;
                    previousHeight = sampledHeight;
                    previousLayer = layer;
                    rayOffset += rayStep;
                    layer -= inverseMarchCount;
                    hitHeight = previousHeight;
                }

                float intersection =
                    (previousHeight - previousLayer) /
                    ((layer + previousHeight - hitHeight) - previousLayer);
                float2 parallaxUV =
                    (parallaxBaseUV + rayStep * intersection + previousRayOffset) *
                    _ParallaxTilling;
                float parallaxSample = _ParallaxMap.SampleBias(
                    sampler_LinearMirrorOnce,
                    parallaxUV,
                    _GlobalMipBias).g;

                float fresnel = exp2(
                    log2(max(saturate(dot(viewWS, normalWS)), 0.0010000000474974513)) *
                    floor(_ParallaxFresnelStrength));
                fresnel *= parallaxMask * parallaxMask;

                // Captured record c3.xyz is the retail per-particle animation
                // phase. The selected M27 draw publishes zero for record 0.
                float capturedRandomPhase =
                    _RecoveredM27InstanceRecordC3.x +
                    _RecoveredM27InstanceRecordC3.y +
                    _RecoveredM27InstanceRecordC3.z;
                float randomPhase = lerp(
                    capturedRandomPhase,
                    input.particlePhase,
                    saturate(_RecoveredSourceAuthoredLitEffect));
                float minimumComplement = 1.0 - _ParallaxMinBrightness;
                float animatedBrightness = minimumComplement * 0.5 *
                    (((_ParallaxMinBrightness + 1.0) / minimumComplement) +
                    cos(mad(
                        _VFXParams0.w * _ParallaxAnimSpeed,
                        0.05000000074505806,
                        randomPhase * _ParallaxAnimRandom)));

                float2 anchorDelta = input.positionWS.xz - _AnchorWaveBright.xy;
                float anchorWave = saturate(
                    (length(anchorDelta) - _AnchorWaveBright.z) /
                    (-_AnchorWaveBright.z));
                float brightness = mad(
                    SmoothCubic(anchorWave),
                    _AnchorWaveBright.w,
                    animatedBrightness);

                if (_ParallaxCharPos != 0.0)
                {
                    float characterDistance = distance(
                        input.positionWS,
                        _VFXParams0.xyz);
                    float characterRamp = saturate(
                        (characterDistance - _ParallaxBrightOuterRadius) /
                        (_ParallaxBrightInnerRadius - _ParallaxBrightOuterRadius));
                    brightness = mad(
                        SmoothCubic(characterRamp),
                        _ParallaxBrightStrength,
                        brightness);
                }

                float exposure = _ParallaxIgnorePostExposure != 0.0
                    ? _HGRPExposureMultiplier
                    : 1.0;
                float3 parallaxColor = lerp(
                    _ParallaxColorDark.rgb,
                    _ParallaxColor.rgb,
                    parallaxSample);
                float3 emission = exposure * clamp(
                    brightness * fresnel * parallaxColor,
                    0.0,
                    1000.0);
                output.sceneColor = float4(
                    emission * _ParallaxIntensity,
                    0.5);

                // HG_ENABLE_MV packing, including the retail fourth-root
                // encoding and the captured record-c4 model-motion gate.
                float currentW = max(input.currentScreenPosition.z, 1.0e-8);
                float previousW = max(input.previousScreenPosition.z, 1.0e-8);
                float2 currentNDC = input.currentScreenPosition.xy / currentW;
                float2 previousNDC = input.previousScreenPosition.xy / previousW;
                float motionX = currentNDC.x - previousNDC.x;
                float motionY = previousNDC.y - currentNDC.y;
                float2 encodedMotion = float2(
                    mad(sqrt(sqrt(abs(motionX * 0.5))) * SignedUnit(motionX), 0.5, 0.5),
                    mad(sqrt(sqrt(abs(motionY * 0.5))) * SignedUnit(motionY), 0.5, 0.5));
                float modelMotion = saturate(SignedUnit(
                    max(
                        _RecoveredM27InstanceRecordC4.y,
                        _RecoveredM27InstanceRecordC4.z) -
                    0.10000002384185791));
                modelMotion *= 1.0 -
                    saturate(_RecoveredSourceAuthoredLitEffect);
                encodedMotion = lerp(encodedMotion, 0.5.xx, modelMotion);

                float taaNormal = lerp(
                    _TAAUNormalBiasReverse,
                    0.69999998807907104,
                    modelMotion);
                output.sceneMotion = float4(
                    encodedMotion,
                    taaNormal > 0.0 ? 1.0 : _TaauMaskModeValue,
                    taaNormal);

                uint terrainProfile = (uint)_TerrainSubsurfaceProfileInt;
                // The pinned b3 field map and fragment stores prove the
                // source MRO layout: R=metallic, G=roughness, B=occlusion.
                float metallic = lerp(
                    mroSample.r,
                    _Metallic,
                    saturate(_BaseTextureMapCount - 1.0));
                float roughness = lerp(
                    _RoughnessMin,
                    _RoughnessMax,
                    mroSample.g);
                float occlusion = mad(
                    _OcclusionStrength,
                    mroSample.b - 1.0,
                    1.0);
                output.gBufferA = float4(
                    metallic,
                    occlusion,
                    0.0,
                    (float)(terrainProfile >> 2u) * 0.3333333432674408);

                float normalL1 = dot(abs(normalWS), 1.0.xxx);
                float2 octNormal = normalWS.xz / normalL1;
                if (normalWS.y <= 0.0)
                {
                    octNormal = float2(
                        (octNormal.x >= 0.0 ? 1.0 : -1.0) *
                            (1.0 - abs(octNormal.y)),
                        (octNormal.y >= 0.0 ? 1.0 : -1.0) *
                            (1.0 - abs(octNormal.x)));
                }
                output.gBufferB = float4(
                    mad(octNormal, 0.5, 0.5),
                    roughness,
                    (float)(terrainProfile & 3u) * 0.3333333432674408);

                return output;
            }
            ENDHLSL
        }
    }
}
