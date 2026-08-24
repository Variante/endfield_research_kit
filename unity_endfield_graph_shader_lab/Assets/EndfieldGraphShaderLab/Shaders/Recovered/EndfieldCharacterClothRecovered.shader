Shader "Endfield/Recovered/CharacterCloth"
{
    Properties
    {
        [MainTexture] _BaseMap ("Base Map", 2D) = "white" {}
        [MainColor] _BaseColor ("Base Color", Color) = (1,1,1,1)
        [HideInInspector] _MainTex ("Legacy Base Map", 2D) = "white" {}
        [HideInInspector] _Color ("Legacy Base Color", Color) = (1,1,1,1)
        [HideInInspector] [PerRendererData] _EndfieldRecoveredForwardLogicalDrawId ("Diagnostic Forward Logical Draw ID", Integer) = 0
        [HideInInspector] [PerRendererData] _EndfieldRecoveredForwardRenderQueue ("Diagnostic Forward Render Queue", Integer) = 0

        _BumpMap ("Packed Normal (R*A, G)", 2D) = "bump" {}
        _UseBumpMap ("Use Bump Map", Float) = 0
        _BumpScale ("Bump Scale", Range(0,2)) = 1

        _MetallicGlossMap ("RGBA: Metal, Spec, Shadow, Smooth", 2D) = "white" {}
        _UseMetallicGlossMap ("Use Packed Map", Float) = 0
        _Metallic ("Metallic", Range(0,1)) = 0
        _Specular ("Specular", Range(0,1)) = 0.25
        _Smoothness ("Smoothness", Range(0,1)) = 0.4

        _DiffRampMap ("Diffuse Ramp", 2D) = "white" {}
        _UseDiffRampMap ("Use Diffuse Ramp", Float) = 0
        _SpecRampMap ("Specular Ramp", 2D) = "white" {}
        _UseSpecRampMap ("Use Specular Ramp", Float) = 0
        [HideInInspector] _SpecRampIridescentMode ("Original Specular Ramp Iridescent Mode", Float) = 0
        _CubemapIntensity ("Character Cubemap Intensity", Float) = 1
        _ShadowLutTex ("Flattened 32x32x32 Shadow LUT", 2D) = "white" {}
        _UseShadowLutTex ("Use Shadow LUT", Float) = 0
        _ShadowColorBrightness ("Shadow Brightness", Float) = 0.55
        _ShadowColorSaturation ("Shadow Saturation", Float) = 1.25

        _EmissionMap ("Emission Map", 2D) = "black" {}
        _UseEmission ("Use Emission", Float) = 0
        [HDR] _EmissionColor ("Emission Color", Color) = (0,0,0,0)
        _EmissionBrightness ("Emission Brightness", Float) = 1
        // Exact selected CharacterNPR EntityVFX dissolve payload. These stay
        // inert on serialized character materials; the Zhuangfy runtime
        // enables the keyword and writes them only to its four replacement
        // LOD materials.
        [HideInInspector] _DissolveTex ("EntityVFX Dissolve Texture", 2D) = "white" {}
        [HideInInspector] _UseDissolve ("EntityVFX Use Dissolve", Float) = 0
        [HideInInspector] _DissolveScheduleOffset ("EntityVFX Dissolve Schedule", Float) = 0
        [HideInInspector] _DissolveEdgeSharp ("EntityVFX Dissolve Edge Sharpness", Float) = 0
        [HideInInspector] _DissolveEmissiveEdge ("EntityVFX Dissolve Emissive Edge", Float) = 0
        [HideInInspector] [HDR] _DissolveEmissiveColor ("EntityVFX Dissolve Emissive Color", Color) = (0,0,0,1)
        [HideInInspector] _DissolveUseViewUV ("EntityVFX Dissolve View UV", Float) = 0
        [HideInInspector] _DissolveUVSet ("EntityVFX Dissolve UV Set", Float) = 0

        _FurMap ("Fur Noise", 2D) = "white" {}
        _FurDirMap ("Fur Direction/Density/Length", 2D) = "bump" {}
        _UseCharacterFur ("Use Character Fur", Float) = 0
        _FurDirMapEnable ("Use Fur Direction Map", Float) = 0
        _FurLengthIntensity ("Fur Length", Float) = 1
        _FurCutoffStart ("Fur Root Cutoff", Range(0,1)) = 0
        _FurCutoffEnd ("Fur Tip Cutoff", Range(0,1)) = 1
        _FurAO ("Fur Root AO", Range(0,1)) = 1
        _FurEdgeFade ("Fur Edge Fade", Range(0,1)) = 0
        _FurGravityStrength ("Fur Gravity", Range(0,1)) = 0
        _FurTTIntensity ("Fur Direct Transmittance", Range(0,1)) = 0.5
        _FurSharpen ("Fur Tip Sharpen", Float) = 0
        _FurNoise ("Fur Strand Noise", Float) = 0
        // Exact serialized inputs retained for source completeness. Their
        // proprietary response stays neutral until a selected variant closes it.
        [HideInInspector] _Pantyhose ("Original Pantyhose Toggle", Float) = 0
        [HideInInspector] _ExtraAlphaMask ("Original Extra Alpha Mask", 2D) = "white" {}
        [HideInInspector] _VFXSpecialBlendTex ("Original VFX Special Blend", 2D) = "black" {}
        [HideInInspector] _FurDyeMap ("Original Fur Dye Map", 2D) = "white" {}
        [HideInInspector] _VFXSpecialMainTex ("Original VFX Special Main", 2D) = "black" {}
        [HideInInspector] _VertexAnimationNoise ("Original Vertex Animation Noise", 2D) = "gray" {}
        [HideInInspector] _DisableRainEffectOnMaterial ("Disable Rain Effect", Float) = 0
        [HideInInspector] _SurfaceType ("Original Surface Type", Float) = 0
        [HideInInspector] _EndfieldRecoveredCharacterPerDraw2 ("Recovered Per Draw 2", Vector) = (0,0,0,0)

        _UseAnisotropy ("Use Cloth Anisotropy", Float) = 0
        _AnisotropyDirectionMain ("Main Anisotropy Shift", Range(-1,1)) = 0
        _AnisotropyIntensityMultiplier ("Main Anisotropy Intensity", Float) = 1
        _AnisotropyDirectionAdditional ("Additional Anisotropy Shift", Range(-1,1)) = 0.25
        _AnisotropyOffsetAdditional ("Additional Anisotropy Offset", Range(-1,1)) = 0
        [HDR] _AnisotropyColorAdditional ("Additional Anisotropy Color", Color) = (1,1,1,1)

        _UseClearCoat ("Use Clear Coat", Float) = 0
        _ClearCoat ("Original Clear Coat Toggle", Float) = 0
        _ClearCoatMask ("Clear Coat Mask", 2D) = "white" {}
        _ClearCoatMaskValue ("Clear Coat Mask Value", Range(0,1)) = 1
        _ClearCoatMetallic ("Clear Coat Metallic", Range(0,1)) = 0
        _ClearCoatSmoothness ("Clear Coat Smoothness", Range(0,1)) = 0.85
        _ClearCoatNormalMode ("Clear Coat Normal Mode", Range(0,1)) = 0
        [HDR] _ClearCoatColor ("Clear Coat Color", Color) = (1,1,1,1)

        _UseParallax ("Use Parallax", Float) = 0
        _ParallaxTex ("Parallax Texture", 2D) = "gray" {}
        _ParallaxScale ("Parallax Scale", Float) = 0.02
        _ParallaxMarchNum ("Parallax March Steps", Range(1,8)) = 1

        [Toggle(_SILK_STOCKINGS)] _SilkStockings ("Original Silk Stockings", Float) = 0
        _SilkStockingsDryColor ("Silk Stockings Dry Color", Color) = (1,1,1,1)
        _SilkStockingsWetColor ("Silk Stockings Wet Color", Color) = (1,1,1,1)
        _SilkStockingsColor ("Silk Stockings Edge Color", Color) = (0,0,0,1)
        _SilkStockingsMinAffect ("Silk Stockings Minimum Affect", Range(0,0.49)) = 0.05
        _SilkStockingsMaxAffect ("Silk Stockings Maximum Affect", Range(0.5,0.9)) = 0.9
        _SilkStockingsAdvance ("Silk Stockings Advanced Mask", Float) = 0
        _SilkStockingsAnisoDirection ("Silk Stockings Anisotropy Direction", Range(-1,1)) = 0
        _SilkStockingsMask ("Silk Stockings Mask", 2D) = "white" {}
        _SilkStockingsSpecularInt ("Silk Stockings Specular Intensity", Float) = 5
        _SilkStockingsSpecularMinAtMinWetness ("Silk Stockings Dry Specular Minimum", Range(0,1)) = 0
        _SilkStockingsSpecularFalloff ("Silk Stockings Specular Falloff", Range(0,1)) = 0.8
        _SilkStockingsSpecularValue ("Silk Stockings Specular Value", Range(-2,2)) = 2
        _SilkStockingsRainWetMaskScale ("Silk Stockings Rain Wet Mask Scale", Range(0,1)) = 0.7
        _SilkStockingsAlbedoAffectType ("Silk Stockings Wet Albedo Affect", Range(-0.9,0.5)) = 0.5
        [HideInInspector] _RecoveredLastRiteSilkStockingsVariant ("Recovered Last Rite Silk Stockings Variant", Float) = 0

        _UseStylizedFresnel ("Use Stylized Fresnel", Float) = 0
        _EnableStylizedFresnel ("Original Stylized Fresnel Toggle", Float) = 0
        _StylizedFresnelColor ("Stylized Fresnel Color", Color) = (1,1,1,1)
        _StylizedFresnelPower ("Stylized Fresnel Power", Float) = 4
        _StylizedFresnelIntensity ("Stylized Fresnel Intensity", Float) = 0.25
        _StylizedFresnelPow ("Original Stylized Fresnel Power", Float) = 4
        _StylizedFresnelAmount ("Original Stylized Fresnel Amount", Float) = 0.25
        _StylizedFresnelNoiseMap ("Stylized Fresnel Noise", 2D) = "white" {}

        _RimTintColor ("Rim Tint", Color) = (1,1,1,1)
        _RimScale ("Rim Scale", Float) = 0.15
        _RimPower ("Rim Power", Float) = 3
        _RimWidth ("Rim Width", Range(0,1)) = 0.5
        _RimFeather ("Rim Feather", Range(0.001,1)) = 0.2

        _OutlineMask ("Outline Mask", 2D) = "white" {}
        _UseOutlineMask ("Use Outline Mask", Float) = 0
        _EnableOutlineMask ("Original Outline Mask Toggle", Float) = 0
        _EnableOutline ("Enable Outline", Float) = 1
        _OutlineWidth ("Outline Width", Float) = 0.6
        _OutlineZOffset ("Outline Z Offset", Float) = 0
        _OutlineOffsetZ ("Original Outline Z Offset", Float) = 0
        _OutlineBrightness ("Outline Brightness", Float) = 0.35
        _OutlineSaturation ("Outline Saturation", Float) = 1.1
        _OutlineColorBrightness ("Original Outline Brightness", Float) = 0.35
        _OutlineColorSaturation ("Original Outline Saturation", Float) = 1.1
        _OutlineColor ("Outline Tint", Color) = (1,1,1,1)

        _EnableAlphaTest ("Enable Alpha Test", Float) = 0
        [HideInInspector] _AlphaClip ("Alpha Clip Alias", Float) = 0
        [HideInInspector] _AlphaPremultiply ("Alpha Premultiply", Float) = 0
        _AlphaClipThreshold ("Alpha Clip Threshold", Range(0,1)) = 0.5
        [Enum(UnityEngine.Rendering.CullMode)] _Cull ("Cull", Float) = 2
        [HideInInspector] [Enum(On,0,Off,1)] _BackFaceNormalFlip ("Original Back Face Normal Flip", Float) = 0
        [Enum(UnityEngine.Rendering.BlendMode)] _SrcBlend ("Source Blend", Float) = 1
        [Enum(UnityEngine.Rendering.BlendMode)] _DstBlend ("Destination Blend", Float) = 0
        [Enum(Off,0,On,1)] _ZWrite ("Z Write", Float) = 1
        [Enum(UnityEngine.Rendering.CompareFunction)] _ZTest ("Z Test", Float) = 4
        [HideInInspector] _RecoveredSourceZTest ("Original Source Z Test", Float) = 4
        [HideInInspector] _StencilRefOption ("Character Stencil Ref", Float) = 4
        [HideInInspector] _PreZStencilRefOption ("Original Character Stencil Ref", Float) = 36
        [HideInInspector] _OriginalHGRPProfile ("Original HGRP Profile", Float) = 1

        _RecoveredBandSoftness ("Recovered Band Softness", Range(0.001,0.5)) = 0.08
        _RecoveredAmbientStrength ("Recovered Ambient Strength", Range(0,2)) = 0.7
        _RecoveredDirectStrength ("Recovered Direct Strength", Range(0,2)) = 1
        _RecoveredOutlineScale ("Recovered Outline Scale", Float) = 0.0035
        _RecoveredOutlineZScale ("Recovered Outline Z Scale", Float) = 0.00001
    }

    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry" }
        LOD 350

        CGINCLUDE
        #include "UnityCG.cginc"
        #include "Lighting.cginc"
        #include "AutoLight.cginc"
        #include "EndfieldCharacterRecoveredCommon.cginc"
        #include "../HGRPCompat/EndfieldHGRPCharacterLighting.cginc"

        // RendererConfiguration.PerObjectMotionVectors built-ins are not
        // declared by UnityCG.cginc in this custom SRP shader, but Unity binds
        // them when DrawingSettings requests PerObjectData.MotionVectors.
        float4x4 unity_MatrixPreviousM;
        float4 unity_MotionVectorsParams;

        sampler2D _BaseMap;
        float4 _BaseMap_ST;
        sampler2D _BumpMap;
        sampler2D _MetallicGlossMap;
        sampler2D _DiffRampMap;
        sampler2D _SpecRampMap;
        sampler2D _ShadowLutTex;
        sampler2D _EmissionMap;
        Texture2D _DissolveTex;
        // Unity's inline-sampler naming convention creates the independent
        // point/repeat state used by the selected CharacterNPR DXBC. The
        // shared source Texture2D itself correctly remains bilinear/repeat.
        SamplerState sampler_PointRepeat;
        sampler2D _FurMap;
        float4 _FurMap_ST;
        sampler2D _FurDirMap;
        float4 _FurDirMap_ST;
        sampler2D _ClearCoatMask;
        sampler2D _ParallaxTex;
        sampler2D _SilkStockingsMask;
        sampler2D _OutlineMask;
        sampler2D _StylizedFresnelNoiseMap;
        samplerCUBE _CharMaxCubemap;

        half4 _BaseColor;
        half _UseBumpMap;
        half _BumpScale;
        half _UseMetallicGlossMap;
        half _Metallic;
        half _Specular;
        half _Smoothness;
        half _UseDiffRampMap;
        half _UseSpecRampMap;
        half _SpecRampIridescentMode;
        half _CubemapIntensity;
        half _UseShadowLutTex;
        half _ShadowColorBrightness;
        half _ShadowColorSaturation;
        half _UseEmission;
        half4 _EmissionColor;
        half _EmissionBrightness;
        float4 _DissolveTex_ST;
        float _UseDissolve;
        float _DissolveScheduleOffset;
        float _DissolveEdgeSharp;
        float _DissolveEmissiveEdge;
        float4 _DissolveEmissiveColor;
        float _DissolveUseViewUV;
        float _DissolveUVSet;
        half _UseCharacterFur;
        half _FurDirMapEnable;
        float _FurLengthIntensity;
        half _FurCutoffStart;
        half _FurCutoffEnd;
        half _FurAO;
        half _FurEdgeFade;
        float _FurGravityStrength;
        half _FurTTIntensity;
        half _FurSharpen;
        half _FurNoise;
        float _DisableRainEffectOnMaterial;
        float _SurfaceType;
        float4 _EndfieldRecoveredCharacterPerDraw2;
        half _UseAnisotropy;
        half _AnisotropyDirectionMain;
        half _AnisotropyIntensityMultiplier;
        half _AnisotropyDirectionAdditional;
        half _AnisotropyOffsetAdditional;
        half4 _AnisotropyColorAdditional;
        half _UseClearCoat;
        half _ClearCoat;
        half _ClearCoatMaskValue;
        half _ClearCoatMetallic;
        half _ClearCoatSmoothness;
        half _ClearCoatNormalMode;
        half4 _ClearCoatColor;
        half _UseParallax;
        half _ParallaxScale;
        half _ParallaxMarchNum;
        half _SilkStockings;
        half4 _SilkStockingsDryColor;
        half4 _SilkStockingsWetColor;
        half4 _SilkStockingsColor;
        half _SilkStockingsMinAffect;
        half _SilkStockingsMaxAffect;
        half _SilkStockingsAdvance;
        half _SilkStockingsAnisoDirection;
        half _SilkStockingsSpecularInt;
        half _SilkStockingsSpecularMinAtMinWetness;
        half _SilkStockingsSpecularFalloff;
        half _SilkStockingsSpecularValue;
        half _SilkStockingsRainWetMaskScale;
        half _SilkStockingsAlbedoAffectType;
        half _RecoveredLastRiteSilkStockingsVariant;
        half _UseStylizedFresnel;
        half _EnableStylizedFresnel;
        half4 _StylizedFresnelColor;
        half _StylizedFresnelPower;
        half _StylizedFresnelIntensity;
        half _StylizedFresnelPow;
        half _StylizedFresnelAmount;
        half4 _RimTintColor;
        half _RimScale;
        half _RimPower;
        half _RimWidth;
        half _RimFeather;
        half _UseOutlineMask;
        half _EnableOutlineMask;
        half _EnableOutline;
        half _OutlineWidth;
        half _OutlineZOffset;
        half _OutlineOffsetZ;
        half _OutlineBrightness;
        half _OutlineSaturation;
        half _OutlineColorBrightness;
        half _OutlineColorSaturation;
        half4 _OutlineColor;
        half _EnableAlphaTest;
        half _AlphaClip;
        half _AlphaPremultiply;
        half _AlphaClipThreshold;
        half _BackFaceNormalFlip;
        half _RecoveredBandSoftness;
        half _RecoveredAmbientStrength;
        half _RecoveredDirectStrength;
        half _RecoveredOutlineScale;
        half _RecoveredOutlineZScale;
        float _EndfieldRecoveredClothSpecularMode;
        float _EndfieldRecoveredCharCubemapBound;
        float _GlobalMipBias;

        static const float ENDFIELD_CLOTH_NEAR_ZERO = 6.103515625e-05;

        // Rational split-sum DFG approximation recovered from the shipped
        // CharacterNPR Vulkan fragments. Keep the original polynomial layout:
        // the seemingly unusual dot products match the SPIR-V constants.
        void EndfieldRecoveredClothEnvBRDF(
            float nDotV,
            float perceptualRoughnessSquared,
            out float dfgX,
            out float dfgY)
        {
            float nDotV2 = nDotV * nDotV;
            float nDotV3 = nDotV * nDotV2;
            float roughness6 =
                perceptualRoughnessSquared * perceptualRoughnessSquared *
                perceptualRoughnessSquared;

            float2 numeratorX = float2(
                dot(float2(3.32707, 1.0), float2(nDotV, 0.0365463)),
                dot(float2(-9.04756, 1.0), float2(nDotV, 9.0632)));
            float3 denominatorX = float3(
                dot(float3(3.59685, -1.36772, 1.0),
                    float3(nDotV2, nDotV3, 1.0)),
                dot(float3(-16.3174, 1.0, 9.22949),
                    float3(nDotV2, 9.04401, nDotV3)),
                dot(float3(1.0, 19.7886, -20.2123),
                    float3(5.56589, nDotV2, nDotV3)));
            dfgX = dot(numeratorX, float2(1.0, perceptualRoughnessSquared)) /
                dot(denominatorX,
                    float3(1.0, perceptualRoughnessSquared, roughness6));

            float2 numeratorY = float2(
                dot(float2(-1.28514, 1.0), float2(nDotV, 0.99044)),
                dot(float2(1.0, -0.755907), float2(1.29678, nDotV)));
            float3 denominatorY = float3(
                dot(float3(2.92338, 59.4188, 1.0),
                    float3(nDotV, nDotV3, 1.0)),
                dot(float3(1.0, -27.0302, 222.592),
                    float3(20.3225, nDotV, nDotV3)),
                dot(float3(626.13, 316.627, 1.0),
                    float3(nDotV, nDotV3, 121.563)));
            dfgY = dot(numeratorY, float2(1.0, perceptualRoughnessSquared)) /
                dot(denominatorY,
                    float3(1.0, perceptualRoughnessSquared, roughness6));
        }

        // Reconstructs the light/shadow energy factors consumed by both the
        // shipped direct GGX and character-cubemap branches. This is the live
        // selector form found in the selected Wulfa/Zhuangfy SPIR-V, rather
        // than FractalMiner's older charShadow=1 simplification.
        void EndfieldRecoveredClothSpecularCoupling(
            float3 normalWS,
            float3 sceneMainLightColor,
            float rampAlpha,
            float viewRampAlpha,
            float materialShadowMask,
            float characterShadowAttenuation,
            float directionalShadowAttenuation,
            out float ambientExposure,
            out float charShadow,
            out float nprShadow,
            out float3 fullDiffuse)
        {
            charShadow = EndfieldHGRPRecoveredLiveShadowSelector(
                directionalShadowAttenuation);
            float characterShadow = saturate(characterShadowAttenuation);
            float shadowMask = saturate(materialShadowMask);
            float minShadow = min(min(characterShadow, shadowMask), rampAlpha);
            float viewShadowProduct = viewRampAlpha * shadowMask * characterShadow;
            nprShadow = lerp(viewShadowProduct, minShadow, charShadow);

            ambientExposure =
                (_CharacterParams12.w * (1.0 - _EnvironmentGlobalParams0.x) +
                 _EnvironmentGlobalParams0.x) * _ExposureParams.x;
            float3 ambientTint = _CharacterParams2.rgb;
            float ambientNdotL =
                saturate(dot(normalize(normalWS), _CharacterParams6.xyz) +
                         _CharacterParams7.x) * _CharacterParams7.y +
                _CharacterParams7.z;
            float shadowStrength = minShadow * _CharacterParams1.y;
            float3 shadowedAmbient = ambientNdotL *
                (shadowStrength * (1.0 - ambientTint) + ambientTint);

            float bright065 = min(ambientExposure * 0.35 + 0.65, 1.5);
            float brightAlternate = clamp(ambientExposure, 1.25, 1.75);
            float brightMix = lerp(bright065, brightAlternate, _CharacterParams1.x);
            float3 brightAmbient =
                brightMix * shadowedAmbient * _CharacterParams0.w;

            float3 baseMainLightColor = lerp(
                sceneMainLightColor,
                _CharacterParams5.rgb,
                _CharacterParams12.y);
            float3 directMainLightColor = baseMainLightColor * lerp(
                EndfieldHGRPCharacterMainIntensity(),
                1.0,
                _CharacterParams12.w);
            float lightLuminance = dot(
                directMainLightColor,
                float3(0.2126729, 0.7151522, 0.0721750));
            // The selected retail fragments keep descriptor RGB unscaled for
            // the ambient lightBlend and apply descriptor W only to the
            // neighboring direct luma/chroma term.
            float3 lightBlend = baseMainLightColor * _CharacterParams12.y +
                                (1.0 - _CharacterParams12.y);
            float brightFull = clamp(ambientExposure, 0.0, 1.5);
            float3 fullDirect =
                (shadowedAmbient * brightFull * lightBlend +
                 minShadow * (directMainLightColor - lightLuminance) +
                 lightLuminance) * _CharacterParams0.y;
            fullDiffuse = lerp(brightAmbient, fullDirect, charShadow);
        }

        // Exact scalar hash used by selected CharacterNPR ForwardLit
        // fragment blob500/33 (_CHARACTER_FUR, _ALPHABLEND_ON).
        float EndfieldRecoveredFurHash(float2 value, float2 constants)
        {
            return frac(sin(dot(value, constants)) * 43758.546875);
        }

        // The selected fragment reads the environment carrier from the same
        // CP10/custom-per-draw ABI as the recovered hair program. Bytes are
        // unpacked as rain, height-wet, global-wet and the remaining lane.
        void EndfieldRecoveredFurEnvironment(
            float worldY,
            out float wetness,
            out float wetVisibility)
        {
            float packedEnvironment = _EndfieldRecoveredCharacterPerDraw2.x;
            float wetWorldHeight = _EndfieldRecoveredCharacterPerDraw2.y;
            if (_CharacterParams10.x > 0.5)
            {
                packedEnvironment = _CharacterParams10.y;
                wetWorldHeight = _CharacterParams10.w;
            }

            uint packedEnvironmentBits = asuint(packedEnvironment);
            float4 environmentLanes = float4(
                packedEnvironmentBits & 255u,
                (packedEnvironmentBits >> 8u) & 255u,
                (packedEnvironmentBits >> 16u) & 255u,
                (packedEnvironmentBits >> 24u) & 255u) * (1.0 / 255.0);
            float wetHeightMask = smoothstep(
                -0.2,
                0.15,
                wetWorldHeight - worldY);
            float wetCombined = max(
                environmentLanes.z,
                wetHeightMask * environmentLanes.y);
            float environmentEffect = max(environmentLanes.x, wetCombined);
            bool environmentEffectEnabled =
                saturate(environmentLanes.x + wetCombined) -
                _DisableRainEffectOnMaterial > 0.01;
            wetness = environmentEffectEnabled
                ? min(environmentEffect * 2.0, 1.0)
                : 0.0;
            wetVisibility = 1.0 - wetHeightMask * environmentLanes.y;
        }

        // Exact raw CharacterNPR wetness scalar consumed by the selected
        // _SILK_STOCKINGS fragment. Unlike the fur visibility path above,
        // this carrier is not doubled and is not gated by the material's
        // general rain-disable switch before the stockings tint/specular
        // parameters consume it.
        float EndfieldRecoveredSilkStockingsWetness(float worldY)
        {
            float packedEnvironment = _EndfieldRecoveredCharacterPerDraw2.x;
            float wetWorldHeight = _EndfieldRecoveredCharacterPerDraw2.y;
            if (_CharacterParams10.x > 0.5)
            {
                packedEnvironment = _CharacterParams10.y;
                wetWorldHeight = _CharacterParams10.w;
            }

            uint packedEnvironmentBits = asuint(packedEnvironment);
            float3 environmentLanes = float3(
                packedEnvironmentBits & 255u,
                (packedEnvironmentBits >> 8u) & 255u,
                (packedEnvironmentBits >> 16u) & 255u) * (1.0 / 255.0);
            float wetHeightMask = smoothstep(
                -0.2,
                0.15,
                wetWorldHeight - worldY);
            return max(
                environmentLanes.x,
                max(environmentLanes.z, environmentLanes.y * wetHeightMask));
        }

        // Exact selected blob500/33 vertex gravity. The carrier is the same
        // CP10/custom-per-draw UNorm8 word used by the fragment path. Rain,
        // height-wet and global-wet raise the authored gravity toward 0.8;
        // the original does not clamp or normalize the resulting bend vector.
        float EndfieldRecoveredFurVertexGravity(float worldY)
        {
            float packedEnvironment = _EndfieldRecoveredCharacterPerDraw2.x;
            float wetWorldHeight = _EndfieldRecoveredCharacterPerDraw2.y;
            if (_CharacterParams10.x > 0.5)
            {
                packedEnvironment = _CharacterParams10.y;
                wetWorldHeight = _CharacterParams10.w;
            }

            uint packedEnvironmentBits = asuint(packedEnvironment);
            float3 environmentLanes = float3(
                packedEnvironmentBits & 255u,
                (packedEnvironmentBits >> 8u) & 255u,
                (packedEnvironmentBits >> 16u) & 255u) * (1.0 / 255.0);
            float wetHeightMask = smoothstep(
                -0.2,
                0.15,
                wetWorldHeight - worldY);
            float environmentGravity = max(
                environmentLanes.x,
                max(environmentLanes.z, environmentLanes.y * wetHeightMask));
            return lerp(
                _FurGravityStrength,
                max(_FurGravityStrength, 0.8),
                environmentGravity);
        }

        float3 EndfieldRecoveredFurVertexDirection(
            float3 normalWS,
            float shell,
            float gravity)
        {
            float3 gravityDirection = lerp(
                normalWS,
                float3(0.0, -1.0, 0.0),
                gravity);
            float gravityBend = shell * (0.5 - 0.5 * normalWS.y);
            return lerp(normalWS, gravityDirection, gravityBend);
        }

        // Exact auxiliary ForwardLit MRT encoding from the paired fragment.
        // The live compatibility SRP has no retail previous-transform/history
        // producer yet, so this source-closed helper remains unbound.
        // Full selected fur coverage equation. The direction map's RG channels
        // warp the noise lookup, B supplies density, and A remains a vertex
        // shell-length input. Neither RG nor B replaces the shading normal.
        float EndfieldRecoveredFurCoverage(
            float2 uv,
            float shell,
            float3 geometryNormal,
            float3 viewWS,
            float wetness,
            out float furNoiseSample)
        {
            float4 furDirectionSample = tex2D(_FurDirMap, uv);
            float tiling = _FurMap_ST.x;
            float2 cell = floor(uv * tiling * 2.0);
            float angle = EndfieldRecoveredFurHash(
                cell + 123.0,
                float2(127.1, 311.7)) * 6.283185482025146484375;
            float radius = sqrt(EndfieldRecoveredFurHash(
                cell + 123.1,
                float2(127.1, 311.7)));
            float2 randomCenter =
                cell * 0.5 + 0.25 +
                radius * float2(cos(angle), sin(angle)) * 0.25;
            float2 cellDelta = uv * tiling - randomCenter;
            float shellRandom =
                (EndfieldRecoveredFurHash(
                    shell.xx,
                    float2(12.9898, 78.233)) * 2.0 - 1.0) *
                _FurNoise * 0.05;
            float2 directionOffset =
                (furDirectionSample.rg * 2.0 - 1.0) *
                    _FurDirMapEnable * 0.005 +
                shellRandom;
            float2 furUv =
                uv * tiling + _FurMap_ST.zw -
                shell * tiling * directionOffset +
                0.5 * shell * shell * cellDelta * wetness * wetness;
            furNoiseSample = tex2D(_FurMap, furUv).r;

            float cellAttenuation = 1.0 - wetness *
                (1.0 - min(length(cellDelta) * 2.8284270763397216796875, 1.0)) *
                saturate(shell * 2.0);
            float cutoff = lerp(_FurCutoffStart, _FurCutoffEnd, shell);
            cutoff = lerp(cutoff, sqrt(cutoff), _FurSharpen);
            float lowerCutoff = max(cutoff - 0.25, 0.0);
            float upperCutoff = min(cutoff + 0.25, 1.0);
            float densityCoordinate = saturate(
                (furDirectionSample.b * furNoiseSample * cellAttenuation -
                 lowerCutoff) /
                (upperCutoff - lowerCutoff));
            float smoothedDensity =
                densityCoordinate * densityCoordinate *
                (3.0 - 2.0 * densityCoordinate);
            if (shell <= 0.01)
            {
                smoothedDensity = 1.0;
            }

            float viewEdge =
                1.0 - shell * shell * shell +
                (dot(geometryNormal, viewWS) - _FurEdgeFade);
            float coverage = saturate(smoothedDensity * viewEdge);
            return lerp(1.0, coverage, ceil(shell));
        }

        float EndfieldRecoveredFurNdotL(
            float3 normalWS,
            float3 lightWS,
            float3 horizontalReferenceWS,
            float shell,
            float furNoiseSample,
            float wetness)
        {
            float thinCoordinate = saturate((1.0 - furNoiseSample) / 0.7);
            float thinSmooth = thinCoordinate * thinCoordinate *
                (3.0 - 2.0 * thinCoordinate);
            float2 horizontalLight = normalize(
                lightWS.xz + float2(0.0, 0.00006103515625));
            float2 horizontalReference = normalize(
                horizontalReferenceWS.xz + float2(0.0, 0.00006103515625));
            float backlight = saturate(
                -dot(horizontalReference, horizontalLight));
            float wetTTIntensity = _FurTTIntensity *
                (1.0 - min(wetness * 1.2, 1.0));
            float rootTransmittance = lerp(
                wetTTIntensity,
                1.15,
                thinSmooth * backlight * _FurNoise);
            return clamp(
                dot(normalWS, lightWS) + shell * rootTransmittance,
                -1.0,
                1.0);
        }

        struct ClothAppData
        {
            float4 vertex : POSITION;
            float3 normal : NORMAL;
            float4 tangent : TANGENT;
            float2 uv : TEXCOORD0;
            float2 uv2 : TEXCOORD1;
            // Unity supplies the previous skinned position in TEXCOORD4 when
            // PerObjectData.MotionVectors and skinnedMotionVectors are active.
            float3 positionOld : TEXCOORD4;
        };

        struct ClothVaryings
        {
            float4 pos : SV_POSITION;
            float2 uv : TEXCOORD0;
            float3 worldPos : TEXCOORD1;
            half3 worldNormal : TEXCOORD2;
            float4 worldTangent : TEXCOORD3;
            float3 furData : TEXCOORD4;
            UNITY_SHADOW_COORDS(5)
            float3 currentClipXYW : TEXCOORD6;
            float3 previousClipXYW : TEXCOORD7;
        };

        ClothVaryings ClothVert(ClothAppData v)
        {
            ClothVaryings o;
            float3 normalWS = normalize(mul(
                (float3x3)unity_ObjectToWorld,
                v.normal));
            float3 worldPosition = mul(unity_ObjectToWorld, v.vertex).xyz;
            if (_UseCharacterFur > 0.5h)
            {
                float4 furDirection = tex2Dlod(
                    _FurDirMap,
                    float4(v.uv, 0, 0));
                float shell = v.uv2.x;
                float gravity = EndfieldRecoveredFurVertexGravity(
                    worldPosition.y);
                float3 furDirectionWS = EndfieldRecoveredFurVertexDirection(
                    normalWS,
                    shell,
                    gravity);
                worldPosition += furDirectionWS *
                    shell * _FurLengthIntensity * 0.01 * furDirection.a;
            }
            o.pos = UnityWorldToClipPos(worldPosition);
            o.currentClipXYW = o.pos.xyw;
            float4 previousLocalPosition = lerp(
                v.vertex,
                float4(v.positionOld, 1.0),
                step(0.5, unity_MotionVectorsParams.x));
            float4 previousWorldPosition = mul(
                unity_MatrixPreviousM,
                previousLocalPosition);
            // Endminf's overview camera is fixed. UNITY_MATRIX_VP therefore
            // equals the previous non-jittered camera transform while retaining
            // Unity's exact previous skinned/object position stream.
            float4 previousClip = mul(
                UNITY_MATRIX_VP,
                previousWorldPosition);
            o.previousClipXYW = previousClip.xyw;
            o.uv = TRANSFORM_TEX(v.uv, _BaseMap);
            o.worldPos = worldPosition;
            o.worldNormal = normalWS;
            o.worldTangent = float4(
                normalize(UnityObjectToWorldDir(v.tangent.xyz)),
                v.tangent.w);
            o.furData = float3(v.uv, v.uv2.x);
            UNITY_TRANSFER_SHADOW(o, v.uv);
            return o;
        }

        half4 ClothFrag(
            ClothVaryings i,
            ENDFIELD_RECOVERED_FACE_AND_PRIMITIVE_INPUT(facing)
            #if !(SHADER_TARGET >= 45 && defined(ENDFIELD_RECOVERED_SCREEN_DIRECT_AUDIT))
            , out float4 endfieldCharacterSceneMV : SV_Target1
            #endif
            ENDFIELD_RECOVERED_SCREEN_DIRECT_AUDIT_OUTPUTS
            ENDFIELD_RECOVERED_SAME_OWNER_AUDIT_OUTPUTS) : SV_Target
        {
            #if !(SHADER_TARGET >= 45 && defined(ENDFIELD_RECOVERED_SCREEN_DIRECT_AUDIT))
            endfieldCharacterSceneMV = EndfieldRecoveredCharacterMotionMrt(
                i.currentClipXYW,
                i.previousClipXYW,
                0.0);
            #endif
            half3 geometryNormal = normalize(i.worldNormal);
            half3 tangentWS = normalize(i.worldTangent.xyz);
            half3 binormalWS =
                cross(geometryNormal, tangentWS) * i.worldTangent.w;
            half3 viewWS = normalize(UnityWorldSpaceViewDir(i.worldPos));

            half2 uv = i.uv;
            float recoveredCharacterDissolveEdge = 0.0;
            #if defined(VFX_CHARACTER_DISSOLVE)
            {
                // Exact selected subshader0/pass0:ForwardLit fragment branch
                // (blob695/33). The authored Zhuangfy EntityVFX payload fixes
                // UVSet=0 and UseViewUV=false, so its retail path samples the
                // base varying with the authored ST. GlobalMipBias is the same
                // source bias used by the original SampleBias instruction.
                float2 recoveredDissolveUV =
                    (float2)i.uv * _DissolveTex_ST.xy +
                    _DissolveTex_ST.zw;
                float recoveredDissolveSample = _DissolveTex.SampleBias(
                    sampler_PointRepeat,
                    recoveredDissolveUV,
                    _GlobalMipBias).r;
                float recoveredDissolveSchedule = max(
                    _DissolveScheduleOffset,
                    _EndfieldRecoveredCharacterPerDraw2.w);
                float recoveredDissolveDelta =
                    (recoveredDissolveSample -
                     mad(
                         recoveredDissolveSchedule,
                         2.0199999809265137,
                         -1.0099999904632568)) *
                    _UseDissolve;
                clip(
                    saturate(
                        recoveredDissolveDelta *
                        _DissolveEdgeSharp) -
                    0.009999999776482582);
                recoveredCharacterDissolveEdge = saturate(
                    (_DissolveEmissiveEdge - recoveredDissolveDelta) *
                    _DissolveEdgeSharp);
            }
            #endif
            if (_UseParallax > 0.5h)
            {
                half3 viewTS = half3(dot(viewWS, tangentWS),
                                     dot(viewWS, binormalWS),
                                     dot(viewWS, geometryNormal));
                half height = tex2D(_ParallaxTex, uv).r;
                half2 parallaxOffset = EndfieldParallaxOffset(viewTS, height, _ParallaxScale);
                half marchSteps = clamp(round(_ParallaxMarchNum), 1.0h, 8.0h);
                [unroll(8)]
                for (int marchIndex = 1; marchIndex < 8; ++marchIndex)
                {
                    if (marchIndex < marchSteps)
                    {
                        half progress = (marchIndex + 1.0h) / marchSteps;
                        half marchedHeight = tex2D(
                            _ParallaxTex,
                            uv + parallaxOffset * progress).r;
                        half2 refinedOffset = EndfieldParallaxOffset(
                            viewTS,
                            marchedHeight,
                            _ParallaxScale);
                        parallaxOffset = lerp(
                            parallaxOffset,
                            refinedOffset,
                            rcp(marchIndex + 1.0h));
                    }
                }
                uv += parallaxOffset;
            }

            half4 baseSample = tex2D(_BaseMap, uv) * _BaseColor;
            clip(EndfieldCutout(max(_EnableAlphaTest, _AlphaClip), baseSample.a, _AlphaClipThreshold));

            float furShell = saturate(i.furData.z);
            float furNoiseSample = 1.0;
            float furWetness = 0.0;
            float furWetVisibility = 1.0;
            float furAlpha = baseSample.a;
            if (_UseCharacterFur > 0.5h)
            {
                EndfieldRecoveredFurEnvironment(
                    i.worldPos.y,
                    furWetness,
                    furWetVisibility);
                float furShellCoverage = EndfieldRecoveredFurCoverage(
                    i.uv,
                    furShell,
                    geometryNormal,
                    viewWS,
                    furWetness,
                    furNoiseSample);
                furAlpha = furShellCoverage * furWetVisibility;
                clip(furAlpha - 0.003);
                baseSample.a = (_SurfaceType == 1.0) ? furAlpha : 1.0;
            }

            half3 normalWS = geometryNormal;
            half3 normalTS = half3(0.0h, 0.0h, 1.0h);
            ENDFIELD_RECOVERED_SAME_OWNER_TANGENT_DECLARE(
                endfieldSameOwnerNormalTS);
            if (_UseBumpMap > 0.5h)
            {
                normalTS = EndfieldDecodePackedNormal(tex2D(_BumpMap, uv), _BumpScale);
                ENDFIELD_RECOVERED_SAME_OWNER_TANGENT_CAPTURE(
                    endfieldSameOwnerNormalTS,
                    normalTS);
                normalWS = EndfieldTangentToWorld(normalTS, tangentWS, binormalWS, geometryNormal);
            }

            float furShadowEdge = 1.0;
            if (_UseCharacterFur > 0.5h)
            {
                float doubledNormalZ = min(normalTS.z * 2.0, 1.0);
                float rootNormalOcclusion = doubledNormalZ * doubledNormalZ;
                furShadowEdge = lerp(
                    rootNormalOcclusion * _FurAO,
                    1.0,
                    furShell);
                furShadowEdge = lerp(
                    furShadowEdge,
                    max(furShadowEdge, 0.88),
                    furWetness);
            }

            half faceSign = ENDFIELD_RECOVERED_FACE_IS_FRONT(facing)
                ? 1.0h
                : (-1.0h + 2.0h * _BackFaceNormalFlip);
            half3 faceGeometryNormal = geometryNormal * faceSign;
            normalWS *= faceSign;

            half4 packed = tex2D(_MetallicGlossMap, uv);
            half metallic = lerp(_Metallic, packed.r, saturate(_UseMetallicGlossMap));
            half specularMask = lerp(_Specular, packed.g, saturate(_UseMetallicGlossMap));
            half shadowMask = lerp(1.0h, packed.b, saturate(_UseMetallicGlossMap));
            half smoothness = lerp(_Smoothness, packed.a, saturate(_UseMetallicGlossMap));

            half3 sceneLightWS = normalize(UnityWorldSpaceLightDir(i.worldPos));
            half3 lightWS = EndfieldHGRPCharacterLightDirection(sceneLightWS);
            half3 halfWS = normalize(lightWS + viewWS);
            half nDotL = dot(normalWS, lightWS);
            if (_UseCharacterFur > 0.5h)
            {
                nDotL = EndfieldRecoveredFurNdotL(
                    normalWS,
                    lightWS,
                    viewWS,
                    furShell,
                    furNoiseSample,
                    furWetness);
            }
            half nDotV = dot(normalWS, viewWS);
            half nDotH = saturate(dot(normalWS, halfWS));

            // Exact non-advanced branch of Last Rite cloth-03's selected
            // _SILK_STOCKINGS fragment. Its null stockings mask and authored
            // Advance=0 bypass the texture-driven branch. Coverage remains the
            // shipped BaseMap/BaseColor alpha carrier (SilkColor.a is one),
            // while raw CP10 rain/height/global wetness selects dry/wet tint.
            float recoveredSilkCoverage = 0.0;
            float recoveredSilkAnisotropy = 0.0;
            float recoveredSilkSpecularScale = 0.0;
            if (_RecoveredLastRiteSilkStockingsVariant > 0.5h)
            {
                float recoveredSilkWetness =
                    EndfieldRecoveredSilkStockingsWetness(i.worldPos.y);
                recoveredSilkCoverage = saturate(
                    baseSample.a + 1.0 - _SilkStockingsColor.a);
                recoveredSilkAnisotropy = -lerp(
                    _SilkStockingsAnisoDirection,
                    0.5,
                    saturate(baseSample.a * 0.5));
                recoveredSilkSpecularScale =
                    lerp(
                        _SilkStockingsSpecularMinAtMinWetness,
                        1.0,
                        recoveredSilkWetness) *
                    _SilkStockingsSpecularInt;
                half silkNdotV = saturate(nDotV);
                half silkViewAffect = min(
                    pow(
                        max(1.05h - silkNdotV, 0.0h),
                        2.0h * recoveredSilkCoverage),
                    1.0h);
                half silkAffect = lerp(
                    _SilkStockingsMinAffect,
                    _SilkStockingsMaxAffect,
                    silkViewAffect);
                half3 silkTint = lerp(
                    _SilkStockingsDryColor.rgb,
                    _SilkStockingsWetColor.rgb,
                    recoveredSilkWetness);
                baseSample.rgb = lerp(
                    baseSample.rgb * silkTint,
                    _SilkStockingsColor.rgb,
                    silkAffect);
            }
            #if defined(ENDFIELD_RECOVERED_SCREEN_SHADOW_MASK_CONSUMER)
                float2 recoveredScreenShadowMask =
                    EndfieldHGRPLoadRecoveredScreenShadowMask(i.pos.xy);
                // Exact selected Cloth screen boundary: use G directly. The
                // no-screen character-strength lerp must not run a second time.
                float sceneShadowAttenuation = recoveredScreenShadowMask.x;
                float characterShadowAttenuation = recoveredScreenShadowMask.y;
            #else
                half sceneShadowAttenuation =
                    UNITY_SHADOW_ATTENUATION(i, i.worldPos);
                half characterShadowAttenuation = EndfieldHGRPSampleCharacterShadow(
                    EndfieldHGRPCharacterShadowCoord(i.worldPos, faceGeometryNormal),
                    i.pos.xy);
            #endif
            if (_UseCharacterFur > 0.5h)
            {
                characterShadowAttenuation *= furShadowEdge;
            }
            ENDFIELD_WRITE_RECOVERED_SCREEN_DIRECT_AUDIT(
                i.pos.xy,
                i.worldPos,
                faceGeometryNormal,
                ENDFIELD_RECOVERED_FACE_VALUE(facing),
                2.0,
                0.0);
            ENDFIELD_WRITE_RECOVERED_SAME_OWNER_AUDIT(
                i.pos.xy,
                normalWS,
                faceGeometryNormal,
                ENDFIELD_RECOVERED_FACE_VALUE(facing),
                ENDFIELD_RECOVERED_SAME_OWNER_PRIMITIVE_VALUE,
                2u,
                0.0,
                endfieldSameOwnerNormalTS);
            if (_EndfieldRecoveredDiffuseAuditMode > 5.5)
            {
                half3 auditShadow = EndfieldHGRPPreExposeCharacterColor(
                    characterShadowAttenuation.xxx);
                return half4(auditShadow, baseSample.a);
            }
            half resolvedSceneShadowAttenuation =
                EndfieldHGRPCharacterShadowAttenuation(sceneShadowAttenuation);
            half shadowAttenuation = min(
                resolvedSceneShadowAttenuation,
                characterShadowAttenuation);

            half4 diffuseRamp = EndfieldRampSample(_DiffRampMap, nDotL, nDotV);
            half defaultBand = EndfieldDefaultDiffuseBand(nDotL, _RecoveredBandSoftness);
            half diffuseBand = lerp(defaultBand, diffuseRamp.a, saturate(_UseDiffRampMap));
            half3 rampTint = lerp(half3(1,1,1), diffuseRamp.rgb, saturate(_UseDiffRampMap));
            half litAmount = saturate(diffuseBand * shadowMask * shadowAttenuation);

            half3 authoredShadowColor = EndfieldShadowColor(
                _ShadowLutTex,
                _UseShadowLutTex,
                baseSample.rgb,
                _ShadowColorBrightness,
                _ShadowColorSaturation);
            half3 shadowColor = authoredShadowColor;
            shadowColor *= EndfieldHGRPCharacterShadowTint(0.0h);
            half3 litColor = baseSample.rgb * rampTint;
            half3 diffuseColor = lerp(shadowColor, litColor, litAmount);

            half3 ambient = EndfieldAmbient(normalWS);
            half ambientLobe = EndfieldHGRPCharacterAmbientLobe(normalWS);
            half3 environmentIllumination =
                (half3(0.2h,0.2h,0.2h) + ambient) * _RecoveredAmbientStrength *
                EndfieldHGRPEnvironmentLightMultiplier() * ambientLobe *
                EndfieldHGRPSceneEnvironmentWeight();
            environmentIllumination *= lerp(
                EndfieldHGRPEnvironmentShadowMultiplier(), 1.0h, litAmount);
            half3 mainLightColor = lerp(
                _LightColor0.rgb,
                EndfieldHGRPCharacterMainColor(0.0h),
                EndfieldHGRPCompatibilityWeight());
            half3 directIllumination = mainLightColor * _RecoveredDirectStrength *
                EndfieldHGRPMainLightMultiplier() * lerp(0.35h, 1.0h, litAmount);
            half3 illumination = environmentIllumination + directIllumination;
            half3 color = diffuseColor * illumination;

            // Audit modes are global and intentionally bypass material mutation.
            // Both diffuse-only outputs share the same alpha and pre-exposure
            // treatment so their delta isolates the diffuse formulation.
            float diffuseAuditMode = clamp(_EndfieldRecoveredDiffuseAuditMode, 0.0, 6.0);
            #if defined(ENDFIELD_RECOVERED_SOURCE_ENERGY_CORE)
                // One default-off route through the source-proven live-shadow
                // diffuse and the matching shipped material energy.
                diffuseAuditMode = 5.0;
            #endif
            half alphaPremultiply = lerp(
                1.0h,
                baseSample.a,
                saturate(_AlphaPremultiply));
            float3 recoveredOperatorNprDiffuse = float3(0.0, 0.0, 0.0);
            if (diffuseAuditMode > 0.5 && diffuseAuditMode < 1.5)
            {
                half3 auditColor = EndfieldHGRPPreExposeCharacterColor(
                    color * alphaPremultiply);
                return half4(max(auditColor, 0.0h), baseSample.a);
            }

            if (diffuseAuditMode > 1.5)
            {
                float3 cameraForwardWS = float3(
                    UNITY_MATRIX_I_V._m02,
                    UNITY_MATRIX_I_V._m12,
                    UNITY_MATRIX_I_V._m22);
                float3 recoveredLightWS = normalize(lerp(
                    (float3)sceneLightWS,
                    _CharacterParams11.xyz,
                    _CharacterParams1.w));
                float recoveredWrappedNdotL = EndfieldHGRPRecoveredWrappedNdotL(
                    normalWS,
                    recoveredLightWS,
                    cameraForwardWS);
                if (_UseCharacterFur > 0.5h)
                {
                    recoveredWrappedNdotL = EndfieldRecoveredFurNdotL(
                        normalWS,
                        recoveredLightWS,
                        viewWS,
                        furShell,
                        furNoiseSample,
                        furWetness);
                }
                float3 recoveredRampColor;
                float recoveredRampAlpha;
                float recoveredViewRampAlpha;
                EndfieldHGRPRecoveredDiffuseRamp(
                    _DiffRampMap,
                    _UseDiffRampMap,
                    recoveredWrappedNdotL,
                    normalWS,
                    cameraForwardWS,
                    recoveredRampColor,
                    recoveredRampAlpha,
                    recoveredViewRampAlpha);
                float recoveredMinShadow;
                half3 recoveredDiffuse;
                if (diffuseAuditMode > 3.5)
                {
                    float3 recoveredOperatorFullDiffuse;
                    EndfieldHGRPRecoveredLiveShadowEnergy(
                        baseSample.rgb,
                        authoredShadowColor,
                        metallic,
                        normalWS,
                        _LightColor0.rgb,
                        recoveredRampColor,
                        recoveredRampAlpha,
                        recoveredViewRampAlpha,
                        shadowMask,
                        characterShadowAttenuation,
                        sceneShadowAttenuation,
                        recoveredOperatorFullDiffuse,
                        recoveredOperatorNprDiffuse,
                        recoveredMinShadow);
                    recoveredDiffuse = (half3)(
                        recoveredOperatorFullDiffuse *
                        recoveredOperatorNprDiffuse);
                }
                else
                {
                    float recoveredCastShadow = smoothstep(
                        0.0,
                        1.0,
                        shadowAttenuation);
                    recoveredDiffuse = EndfieldHGRPRecoveredSourceDiffuse(
                        baseSample.rgb,
                        authoredShadowColor,
                        metallic,
                        normalWS,
                        _LightColor0.rgb,
                        recoveredRampColor,
                        recoveredRampAlpha,
                        recoveredViewRampAlpha,
                        shadowMask,
                        recoveredCastShadow,
                        recoveredMinShadow);
                }

                if (diffuseAuditMode < 2.5 ||
                    (diffuseAuditMode > 3.5 && diffuseAuditMode < 4.5))
                {
                    half3 auditColor = EndfieldHGRPPreExposeCharacterColor(
                        recoveredDiffuse * alphaPremultiply);
                    return half4(max(auditColor, 0.0h), baseSample.a);
                }

                // Modes 3/5 are candidate full renders: replace only the
                // diffuse base and retain current downstream lobes.
                color = recoveredDiffuse;
            }

            half specularPower = exp2(2.0h + smoothness * 9.0h);
            half directSpecular = pow(nDotH, specularPower) * litAmount;
            half dielectricSpecular = specularMask * 0.04h;
            half3 authoredSpecularColor =
                metallic * (baseSample.rgb - dielectricSpecular) + dielectricSpecular;

            // Exact recovered cloth-ramp addressing contract. The ramp colors
            // modulate the authored GGX/specular color; they never replace the
            // lobe at full strength. The old replacement path was the source of
            // the large pastel/pink wash on saturated fabrics.
            half roughnessRaw = 1.0h - smoothness;
            half roughness = max(roughnessRaw * roughnessRaw, 0.0078125h);
            half roughnessSquared = roughness * roughness;
            half specularDenominator =
                (nDotH * roughnessSquared - nDotH) * nDotH + 1.0h;
            half dRaw = roughnessSquared /
                max(specularDenominator * specularDenominator, 1e-4h);
            half specRampU = dRaw * (roughnessSquared + 1e-4h);
            half specRampV = (1.0h - metallic) * roughnessRaw;
            half3 specRampColor = tex2D(
                _SpecRampMap,
                half2(saturate(specRampU), saturate(specRampV))).rgb;
            half3 specularColor = authoredSpecularColor * directSpecular *
                lerp(half3(1,1,1), specRampColor, saturate(_UseSpecRampMap));

            // Default-off shipped CharacterNPR material response probe:
            //   0 current canonical direct lobe, no character cubemap
            //   1 recovered direct GGX only
            //   2 recovered direct GGX plus recovered cubemap/DFG contract
            //   3 canonical direct lobe plus cubemap/DFG (isolates IBL delta)
            float clothSpecularMode = clamp(
                _EndfieldRecoveredClothSpecularMode,
                0.0,
                3.0);
            #if defined(ENDFIELD_RECOVERED_SOURCE_ENERGY_CORE)
                clothSpecularMode = 2.0;
            #endif
            float3 recoveredDirectSpecularContribution = 0.0;
            float3 recoveredCubemapContribution = 0.0;
            float3 recoveredOperatorSpecRampColor = float3(0.0, 0.0, 0.0);
            float3 recoveredClearCoatDiffuseAttenuation = float3(1.0, 1.0, 1.0);
            if (clothSpecularMode > 0.5)
            {
                float3 cameraForwardWS = float3(
                    UNITY_MATRIX_I_V._m02,
                    UNITY_MATRIX_I_V._m12,
                    UNITY_MATRIX_I_V._m22);
                float3 recoveredLightWS = normalize(lerp(
                    (float3)sceneLightWS,
                    _CharacterParams11.xyz,
                    _CharacterParams1.w));
                float recoveredWrappedNdotL = EndfieldHGRPRecoveredWrappedNdotL(
                    normalWS,
                    recoveredLightWS,
                    cameraForwardWS);
                if (_UseCharacterFur > 0.5h)
                {
                    recoveredWrappedNdotL = EndfieldRecoveredFurNdotL(
                        normalWS,
                        recoveredLightWS,
                        viewWS,
                        furShell,
                        furNoiseSample,
                        furWetness);
                }
                float3 recoveredDiffuseRampColor;
                float recoveredDiffuseRampAlpha;
                float recoveredViewRampAlpha;
                EndfieldHGRPRecoveredDiffuseRamp(
                    _DiffRampMap,
                    _UseDiffRampMap,
                    recoveredWrappedNdotL,
                    normalWS,
                    cameraForwardWS,
                    recoveredDiffuseRampColor,
                    recoveredDiffuseRampAlpha,
                    recoveredViewRampAlpha);

                float recoveredAmbientExposure;
                float recoveredCharShadow;
                float recoveredNprShadow;
                float3 recoveredFullDiffuse;
                EndfieldRecoveredClothSpecularCoupling(
                    normalWS,
                    _LightColor0.rgb,
                    recoveredDiffuseRampAlpha,
                    recoveredViewRampAlpha,
                    shadowMask,
                    characterShadowAttenuation,
                    sceneShadowAttenuation,
                    recoveredAmbientExposure,
                    recoveredCharShadow,
                    recoveredNprShadow,
                    recoveredFullDiffuse);

                // The shipped lobe deliberately does not use normalize(L+V).
                // Exact selected SPIR-V keeps the same live char-shadow selector
                // in the half-vector: at selector 1 this reduces to the readable
                // FractalMiner V*3 + L + camera*2 endpoint; at selector 0 it is
                // V*2 + camera*2 and the camera Y term moves to 0.5.
                float recoveredNdotV = saturate(dot(normalWS, viewWS));
                float3 cameraForwardModifiedRaw = float3(
                    cameraForwardWS.x,
                    lerp(0.5, recoveredLightWS.y, recoveredCharShadow),
                    cameraForwardWS.z);
                float3 cameraForwardModified = cameraForwardModifiedRaw * rsqrt(
                    max(1.1754943508222875e-38,
                        dot(cameraForwardModifiedRaw, cameraForwardModifiedRaw)));
                float3 recoveredHalfWS = normalize(
                    recoveredLightWS * recoveredCharShadow +
                    cameraForwardModified * 2.0 +
                    viewWS * (2.0 + recoveredCharShadow));
                float recoveredNdotH = dot(normalWS, recoveredHalfWS);
                float recoveredRoughnessRaw = 1.0 - smoothness;
                float recoveredRoughness = max(
                    recoveredRoughnessRaw * recoveredRoughnessRaw,
                    0.0078125);
                float recoveredRoughnessSquared =
                    recoveredRoughness * recoveredRoughness;
                float recoveredDenominator =
                    (recoveredNdotH * recoveredRoughnessSquared -
                     recoveredNdotH) * recoveredNdotH + 1.0;
                float recoveredDenominatorSquared =
                    recoveredDenominator * recoveredDenominator;
                float recoveredDistribution =
                    recoveredDenominatorSquared != recoveredRoughnessSquared
                    ? recoveredRoughnessSquared / recoveredDenominatorSquared
                    : 1.0;
                float recoveredGgxTerm = clamp(
                    recoveredDistribution * 0.5 /
                    (recoveredNdotV * 2.0 + recoveredRoughness + 1e-4) -
                    ENDFIELD_CLOTH_NEAR_ZERO,
                    0.0,
                    20.0);

                // Exact second direct lobe added only by the selected
                // _SILK_STOCKINGS member. The source orthogonalizes the
                // interpolated tangent against the final normal, offsets the
                // shipped half vector toward V by SpecularValue, then uses an
                // anisotropic distribution with independently widened/narrowed
                // roughness axes. For cloth-03, SpecularFalloff=0 keeps the
                // authored anisotropy at full strength and
                // SpecularMinAtMinWetness=1 makes this lobe dry/wet invariant.
                float recoveredSilkStockingsTerm = 0.0;
                if (_RecoveredLastRiteSilkStockingsVariant > 0.5h)
                {
                    float recoveredSilkFalloff = 1.0 - saturate(
                        recoveredSilkCoverage *
                        _SilkStockingsSpecularFalloff);
                    float recoveredSilkRoughnessX = recoveredRoughness *
                        (1.0 + recoveredSilkAnisotropy * recoveredSilkFalloff);
                    float recoveredSilkRoughnessY = recoveredRoughness *
                        (1.0 - recoveredSilkAnisotropy * recoveredSilkFalloff);
                    float3 recoveredSilkTangentWS = normalize(
                        (float3)tangentWS -
                        (float3)normalWS * dot(tangentWS, normalWS));
                    float3 recoveredSilkBitangentWS =
                        cross((float3)normalWS, recoveredSilkTangentWS) *
                        i.worldTangent.w;
                    float3 recoveredSilkHalfWS = normalize(
                        recoveredHalfWS +
                        (float3)viewWS * _SilkStockingsSpecularValue);
                    float recoveredSilkRoughnessProduct =
                        recoveredSilkRoughnessX * recoveredSilkRoughnessY;
                    float3 recoveredSilkDistributionVector = float3(
                        recoveredSilkRoughnessX * dot(
                            recoveredSilkTangentWS,
                            recoveredSilkHalfWS),
                        recoveredSilkRoughnessY * dot(
                            recoveredSilkBitangentWS,
                            recoveredSilkHalfWS),
                        recoveredSilkRoughnessProduct * dot(
                            normalWS,
                            recoveredSilkHalfWS));
                    float recoveredSilkDistributionDenominator = dot(
                        recoveredSilkDistributionVector,
                        recoveredSilkDistributionVector);
                    float recoveredSilkDistributionDenominatorSquared =
                        recoveredSilkDistributionDenominator *
                        recoveredSilkDistributionDenominator;
                    float recoveredSilkDistributionNumerator =
                        recoveredSilkRoughnessProduct *
                        recoveredSilkRoughnessProduct *
                        recoveredSilkRoughnessProduct;
                    float recoveredSilkDistribution =
                        recoveredSilkDistributionDenominatorSquared !=
                        recoveredSilkDistributionNumerator
                        ? clamp(
                            recoveredSilkDistributionNumerator /
                            recoveredSilkDistributionDenominatorSquared,
                            0.0,
                            20.0)
                        : 1.0;
                    recoveredSilkStockingsTerm =
                        recoveredSilkDistribution *
                        recoveredSilkSpecularScale;
                }

                float recoveredSpecRampPartial = recoveredDistribution *
                    (recoveredRoughnessSquared + 1e-4);
                float recoveredSpecRampU = lerp(
                    recoveredSpecRampPartial,
                    recoveredNdotV * recoveredNdotV,
                    saturate(_SpecRampIridescentMode));
                float recoveredSpecRampV =
                    (1.0 - metallic) * recoveredRoughnessRaw;
                float3 recoveredSpecRampSample = tex2Dlod(
                    _SpecRampMap,
                    float4(recoveredSpecRampU, recoveredSpecRampV, 0.0, 0.0)).rgb;
                float3 recoveredSpecRampColor = lerp(
                    (float3)authoredSpecularColor,
                    (float3)authoredSpecularColor * recoveredSpecRampSample,
                    saturate(_UseSpecRampMap));
                recoveredOperatorSpecRampColor = recoveredSpecRampColor;
                float3 recoveredSpecRampEnvironment = lerp(
                    (float3)authoredSpecularColor,
                    recoveredSpecRampColor,
                    saturate(_SpecRampIridescentMode));

                float recoveredAmbientDiffuseIntensity =
                    recoveredNprShadow * (1.0 - _CharacterParams0.z) +
                    _CharacterParams0.z;
                float recoveredSpecularAmbientIntensity =
                    recoveredAmbientDiffuseIntensity *
                    (recoveredNprShadow * 0.5 + 0.5);
                float3 recoveredSpecularLighting =
                    recoveredSpecularAmbientIntensity * recoveredFullDiffuse *
                    _CharacterParams13.w;
                recoveredDirectSpecularContribution = recoveredSpecularLighting *
                    ((recoveredGgxTerm + recoveredSilkStockingsTerm) *
                     recoveredSpecRampColor);

                // Exact `_CLEARCOAT` ForwardLit carrier selected from original
                // D3D11 blob392/33. The source uses the raw mask R channel,
                // squares 1-smoothness before the 1/128 floor, keeps the
                // authored (not renormalized) normal-mode lerp, and applies a
                // Schlick-colored second GGX lobe. `_ClearCoatMaskValue` is a
                // compatibility alias for older exports and is deliberately
                // absent here: none of the eight current clear-coat materials
                // serializes such a scalar.
                float recoveredClearCoatMask = tex2Dbias(
                    _ClearCoatMask,
                    float4(uv, 0.0, _GlobalMipBias)).r;
                bool recoveredClearCoatActive =
                    max((float)_UseClearCoat, (float)_ClearCoat) > 0.5 &&
                    recoveredClearCoatMask > 0.001;
                float3 recoveredClearCoatNormal = lerp(
                    (float3)faceGeometryNormal,
                    (float3)normalWS,
                    saturate((float)_ClearCoatNormalMode));
                float recoveredClearCoatNdotH = dot(
                    recoveredClearCoatNormal,
                    recoveredHalfWS);
                float recoveredClearCoatNdotV = saturate(dot(
                    recoveredClearCoatNormal,
                    viewWS));
                float recoveredClearCoatRoughnessRaw =
                    1.0 - (float)_ClearCoatSmoothness;
                float recoveredClearCoatRoughness = max(
                    recoveredClearCoatRoughnessRaw *
                    recoveredClearCoatRoughnessRaw,
                    0.0078125);
                float recoveredClearCoatRoughnessSquared =
                    recoveredClearCoatRoughness *
                    recoveredClearCoatRoughness;
                float recoveredClearCoatDenominator =
                    (recoveredClearCoatNdotH *
                     recoveredClearCoatRoughnessSquared -
                     recoveredClearCoatNdotH) *
                    recoveredClearCoatNdotH + 1.0;
                float recoveredClearCoatDenominatorSquared =
                    recoveredClearCoatDenominator *
                    recoveredClearCoatDenominator;
                float recoveredClearCoatDistribution =
                    recoveredClearCoatDenominatorSquared !=
                    recoveredClearCoatRoughnessSquared
                    ? recoveredClearCoatRoughnessSquared /
                      recoveredClearCoatDenominatorSquared
                    : 1.0;
                float recoveredClearCoatOneMinusVdotH =
                    1.0 - saturate(dot(viewWS, recoveredHalfWS));
                float recoveredClearCoatOneMinusVdotH2 =
                    recoveredClearCoatOneMinusVdotH *
                    recoveredClearCoatOneMinusVdotH;
                float recoveredClearCoatOneMinusVdotH5 =
                    recoveredClearCoatOneMinusVdotH *
                    recoveredClearCoatOneMinusVdotH2 *
                    recoveredClearCoatOneMinusVdotH2;
                float3 recoveredClearCoatF0 =
                    lerp(0.04, 1.0, saturate((float)_ClearCoatMetallic)) *
                    (float3)_ClearCoatColor.rgb;
                float3 recoveredClearCoatFresnel = lerp(
                    recoveredClearCoatF0,
                    float3(1.0, 1.0, 1.0),
                    recoveredClearCoatOneMinusVdotH5);
                float3 recoveredClearCoatMaskedFresnel =
                    recoveredClearCoatMask * recoveredClearCoatFresnel;
                if (recoveredClearCoatActive)
                {
                    float recoveredClearCoatVisibility =
                        0.5 / (recoveredClearCoatNdotV * 2.0 +
                               recoveredClearCoatRoughness + 1e-4);
                    float3 recoveredClearCoatGgx = clamp(
                        recoveredClearCoatVisibility *
                        (recoveredClearCoatDistribution *
                         recoveredClearCoatMaskedFresnel),
                        0.0,
                        20.0);
                    float3 recoveredClearCoatBaseSpecAttenuation =
                        1.0 - recoveredClearCoatMaskedFresnel;
                    recoveredDirectSpecularContribution =
                        recoveredSpecularLighting *
                        (recoveredGgxTerm * recoveredSpecRampColor *
                         recoveredClearCoatBaseSpecAttenuation *
                         recoveredClearCoatBaseSpecAttenuation +
                         recoveredClearCoatGgx);
                    recoveredClearCoatDiffuseAttenuation =
                        1.0 - recoveredClearCoatMask *
                        recoveredClearCoatMaskedFresnel;
                }

                if (clothSpecularMode > 1.5)
                {
                    float3 reflectionWS = reflect(-viewWS, normalWS);
                    float cubemapMip =
                        log2(max(recoveredRoughnessRaw, 0.001)) * 1.2 + 5.0;
                    float3 cubemapSample = texCUBElod(
                        _CharMaxCubemap,
                        float4(reflectionWS, cubemapMip)).rgb;
                    cubemapSample *= saturate(
                        _EndfieldRecoveredCharCubemapBound);

                    float dfgX;
                    float dfgY;
                    EndfieldRecoveredClothEnvBRDF(
                        recoveredNdotV,
                        recoveredRoughness,
                        dfgX,
                        dfgY);
                    float3 environmentBrdf =
                        recoveredSpecRampEnvironment * dfgX + dfgY;
                    float totalReflection = dfgX + dfgY;
                    float reflectionBoost =
                        (1.0 - totalReflection) /
                        max(totalReflection, 1e-6);
                    float3 cubemapReflection =
                        cubemapSample * environmentBrdf *
                        (1.0 + reflectionBoost *
                         recoveredSpecRampEnvironment);
                    float cubemapAmbientIntensity =
                        recoveredAmbientDiffuseIntensity *
                        (clamp(recoveredAmbientExposure, 0.5, 1.5) *
                         _CharacterParams0.w);
                    recoveredCubemapContribution =
                        cubemapAmbientIntensity * cubemapReflection *
                        _CharacterParams2.rgb * _CubemapIntensity;

                    if (recoveredClearCoatActive)
                    {
                        float3 recoveredClearCoatReflectionWS = reflect(
                            -viewWS,
                            recoveredClearCoatNormal);
                        float recoveredClearCoatCubemapMip =
                            log2(max(
                                recoveredClearCoatRoughnessRaw,
                                0.001)) * 1.2 + 5.0;
                        float3 recoveredClearCoatCubemapSample = texCUBElod(
                            _CharMaxCubemap,
                            float4(
                                recoveredClearCoatReflectionWS,
                                recoveredClearCoatCubemapMip)).rgb;
                        recoveredClearCoatCubemapSample *= saturate(
                            _EndfieldRecoveredCharCubemapBound);

                        float recoveredClearCoatDfgX;
                        float recoveredClearCoatDfgY;
                        EndfieldRecoveredClothEnvBRDF(
                            recoveredClearCoatNdotV,
                            recoveredClearCoatRoughness,
                            recoveredClearCoatDfgX,
                            recoveredClearCoatDfgY);
                        float3 recoveredClearCoatEnvironmentBrdf =
                            recoveredClearCoatF0 * recoveredClearCoatDfgX +
                            recoveredClearCoatDfgY;
                        float recoveredClearCoatTotalReflection =
                            recoveredClearCoatDfgX + recoveredClearCoatDfgY;
                        float recoveredClearCoatReflectionBoost =
                            (1.0 - recoveredClearCoatTotalReflection) /
                            max(recoveredClearCoatTotalReflection, 1e-6);
                        float3 recoveredClearCoatCubemapReflection =
                            recoveredClearCoatCubemapSample *
                            recoveredClearCoatEnvironmentBrdf *
                            (1.0 + recoveredClearCoatReflectionBoost *
                             recoveredClearCoatF0);
                        recoveredCubemapContribution +=
                            cubemapAmbientIntensity *
                            recoveredClearCoatCubemapReflection *
                            recoveredClearCoatMask *
                            _CharacterParams2.rgb * _CubemapIntensity;
                    }
                }
            }

            #if defined(ENDFIELD_RECOVERED_SOURCE_ENERGY_CORE)
            {
                // Exact active Wulfa/Zhuangfy CharacterNPR cloth core. Their
                // source payloads do not select clearcoat, pantyhose, parallax,
                // or the lab-only anisotropy branch. CP8.rgb=0 and CP12.x=1
                // also make the source skin-edge/subsurface carriers exactly
                // zero. The separately default-off operator-light gate below
                // adds only the recovered direct-rig subset; IV and final post
                // remain outside this intentionally incomplete selector.
                float3 recoveredMainLit =
                    (float3)color * recoveredClearCoatDiffuseAttenuation *
                    (float)alphaPremultiply +
                    recoveredDirectSpecularContribution;
                float recoveredMainLuminance =
                    EndfieldHGRPRecoveredLuma(recoveredMainLit);
                float recoveredDesaturationAmount = clamp(
                    recoveredMainLuminance - 0.5,
                    0.0,
                    0.5);
                float recoveredDesaturationFactor =
                    recoveredDesaturationAmount *
                    recoveredDesaturationAmount + 1.0;
                float3 recoveredSourceEnergy =
                    recoveredDesaturationFactor *
                    (recoveredMainLit - recoveredMainLuminance) +
                    recoveredMainLuminance;

                float3 recoveredEmission =
                    tex2D(_EmissionMap, uv).rgb *
                    (float3)_EmissionColor.rgb *
                    (float)_EmissionBrightness *
                    saturate((float)_UseEmission) *
                    (float)alphaPremultiply;
                // In blob695/33 the dissolve color is accumulated beside the
                // authored emission carrier before their shared
                // alpha-premultiply multiplication.
                float3 recoveredDissolveEmission =
                    (float3)_DissolveEmissiveColor.rgb *
                    recoveredCharacterDissolveEdge *
                    (float)alphaPremultiply;
                recoveredSourceEnergy +=
                    recoveredEmission +
                    recoveredDissolveEmission +
                    recoveredCubemapContribution;
                float3 recoveredCameraForwardWS = float3(
                    UNITY_MATRIX_I_V._m02,
                    UNITY_MATRIX_I_V._m12,
                    UNITY_MATRIX_I_V._m22);
                float3 recoveredPunctualDiffuseAlbedo =
                    (1.0 - (float)metallic) * 0.96 * (float3)baseSample.rgb;
                recoveredSourceEnergy =
                    EndfieldHGApplyRecoveredClusteredNprLights(
                        recoveredSourceEnergy,
                        (float3)i.worldPos,
                        (float4)i.pos,
                        (float3)faceGeometryNormal,
                        (float3)normalWS,
                        (float3)normalWS,
                        (float3)viewWS,
                        recoveredCameraForwardWS,
                        recoveredPunctualDiffuseAlbedo,
                        recoveredOperatorNprDiffuse,
                        (float3)normalWS,
                        0.0,
                        0.0,
                        recoveredOperatorSpecRampColor,
                        1.0 - (float)smoothness,
                        (float)alphaPremultiply,
                        ENDFIELD_RECOVERED_FACE_IS_FRONT(facing) ? 0.0 : 4.0,
                        _SpecRampMap,
                        float3(0.0, 1.0, 0.0),
                        0.0,
                        0.0,
                        0.0,
                        0.0);
                recoveredSourceEnergy = EndfieldHGRPPreExposeCharacterColor(
                    recoveredSourceEnergy);
                return half4(max((half3)recoveredSourceEnergy, 0.0h), baseSample.a);
            }
            #endif

            if (_UseAnisotropy > 0.5h)
            {
                half anisotropyPower = lerp(24.0h, 128.0h, smoothness);
                half mainLobe = EndfieldKajiyaKay(
                    tangentWS, halfWS, _AnisotropyDirectionMain, anisotropyPower);
                half additionalLobe = EndfieldKajiyaKay(
                    tangentWS,
                    halfWS,
                    _AnisotropyDirectionAdditional + _AnisotropyOffsetAdditional,
                    anisotropyPower * 0.65h);
                specularColor += (mainLobe * _AnisotropyIntensityMultiplier +
                                  additionalLobe * _AnisotropyColorAdditional.rgb) *
                                 specularMask * litAmount;
            }

            if (max(_UseClearCoat, _ClearCoat) > 0.5h)
            {
                half coatMask = tex2D(_ClearCoatMask, uv).r * _ClearCoatMaskValue;
                half coatPower = exp2(4.0h + _ClearCoatSmoothness * 10.0h);
                half3 coatColor = lerp(half3(0.04h,0.04h,0.04h), baseSample.rgb,
                                       _ClearCoatMetallic);
                specularColor += coatColor * pow(nDotH, coatPower) * coatMask * litAmount;
            }

            if (clothSpecularMode > 0.5 && clothSpecularMode < 2.5)
                color += recoveredDirectSpecularContribution;
            else
                color += specularColor * mainLightColor * EndfieldHGRPSpecularMultiplier();
            if (clothSpecularMode > 1.5)
                color += recoveredCubemapContribution;
            color += EndfieldHGOperatorAdditionalLighting(
                i.worldPos, normalWS, viewWS, baseSample.rgb,
                metallic, smoothness, specularMask);

            half rim = EndfieldFresnel(normalWS, viewWS, _RimPower);
            half rimBand = smoothstep(
                saturate(_RimWidth - _RimFeather),
                saturate(_RimWidth + _RimFeather),
                rim);
            color += rimBand * _RimScale * _RimTintColor.rgb * litColor;
            half3 normalVS = normalize(mul((half3x3)UNITY_MATRIX_V, normalWS));
            color = EndfieldHGRPApplyCharacterRim(color, baseSample.rgb, normalVS);

            half originalFresnel = saturate(_EnableStylizedFresnel);
            half stylizedPower = lerp(_StylizedFresnelPower, _StylizedFresnelPow, originalFresnel);
            half stylizedAmount = lerp(_StylizedFresnelIntensity, _StylizedFresnelAmount * 0.1h,
                                       originalFresnel);
            half stylizedFresnel = EndfieldFresnel(normalWS, viewWS, stylizedPower);
            half fresnelNoise = tex2D(_StylizedFresnelNoiseMap, uv).r;
            color += stylizedFresnel * _StylizedFresnelColor.rgb *
                     stylizedAmount * fresnelNoise *
                     saturate(max(_UseStylizedFresnel, _EnableStylizedFresnel));

            half3 emission = tex2D(_EmissionMap, uv).rgb *
                             _EmissionColor.rgb * _EmissionBrightness;
            color += emission * saturate(_UseEmission);
            color *= lerp(1.0h, baseSample.a, saturate(_AlphaPremultiply));
            if (diffuseAuditMode > 2.5)
                color = EndfieldHGRPPreExposeCharacterColor(color);
            return half4(max(color, 0.0h), baseSample.a);
        }

        struct OutlineVaryings
        {
            float4 pos : SV_POSITION;
            float2 uv : TEXCOORD0;
        };

        OutlineVaryings ClothOutlineVert(ClothAppData v)
        {
            OutlineVaryings o;
            float2 uv = TRANSFORM_TEX(v.uv, _BaseMap);
            float mask = lerp(1.0, tex2Dlod(_OutlineMask, float4(uv, 0, 0)).r,
                              saturate(max(_UseOutlineMask, _EnableOutlineMask)));
            float width = EndfieldHGRPCharacterOutlineWidth(
                _OutlineWidth * _RecoveredOutlineScale * mask * saturate(_EnableOutline));
            float4 clipPos = UnityObjectToClipPos(v.vertex + float4(v.normal * width, 0));
            clipPos.z += (_OutlineZOffset + _OutlineOffsetZ) *
                         _RecoveredOutlineZScale * clipPos.w;
            o.pos = clipPos;
            o.uv = uv;
            return o;
        }

        half4 ClothOutlineFrag(OutlineVaryings i) : SV_Target
        {
            clip(min(_EnableOutline, EndfieldHGRPCharacterOutlineEnable()) - 0.5h);
            half4 baseSample = tex2D(_BaseMap, i.uv) * _BaseColor;
            clip(EndfieldCutout(max(_EnableAlphaTest, _AlphaClip),
                                baseSample.a,
                                _AlphaClipThreshold));
            half outlineSaturation = _OutlineColorSaturation;
            half outlineBrightness = _OutlineColorBrightness;
            half3 outline = EndfieldSaturation(baseSample.rgb, outlineSaturation) *
                            outlineBrightness * _OutlineColor.rgb;
            outline = EndfieldHGRPCharacterOutlineColor(outline);
            outline = EndfieldHGRPPreExposeCharacterColor(outline);
            return half4(outline, baseSample.a);
        }

        struct ClothCameraDepthVaryings
        {
            float4 pos : SV_POSITION;
            float2 uv : TEXCOORD0;
        };

        ClothCameraDepthVaryings ClothCameraDepthVert(appdata_base v)
        {
            ClothCameraDepthVaryings o;
            o.pos = UnityObjectToClipPos(v.vertex);
            o.uv = TRANSFORM_TEX(v.texcoord, _BaseMap);
            return o;
        }

        half4 ClothCameraDepthFrag(ClothCameraDepthVaryings i) : SV_Target
        {
            half alpha = tex2D(_BaseMap, i.uv).a * _BaseColor.a;
            clip(EndfieldCutout(max(_EnableAlphaTest, _AlphaClip), alpha, _AlphaClipThreshold));
            return half4(i.pos.z, i.pos.z, i.pos.z, 1.0h);
        }

        struct ShadowVaryings
        {
            V2F_SHADOW_CASTER;
            float2 uv : TEXCOORD1;
        };

        ShadowVaryings ClothShadowVert(appdata_base v)
        {
            ShadowVaryings o;
            TRANSFER_SHADOW_CASTER_NORMALOFFSET(o)
            #if defined(ENDFIELD_RECOVERED_CHARACTER_SHADOW_PASS_VP)
                o.pos = EndfieldRecoveredCharacterShadowClipPosition(v.vertex);
            #endif
            o.uv = TRANSFORM_TEX(v.texcoord, _BaseMap);
            return o;
        }

        float4 ClothShadowFrag(ShadowVaryings i) : SV_Target
        {
            half alpha = tex2D(_BaseMap, i.uv).a * _BaseColor.a;
            clip(EndfieldCutout(max(_EnableAlphaTest, _AlphaClip), alpha, _AlphaClipThreshold));
            SHADOW_CASTER_FRAGMENT(i)
        }

        EndfieldRecoveredPreGBufferOutput ClothRecoveredPreGBufferDiagnosticFrag(
            ClothVaryings i,
            ENDFIELD_RECOVERED_FACE_AND_PRIMITIVE_INPUT(facing))
        {
            half4 baseSample = tex2D(_BaseMap, i.uv) * _BaseColor;
            clip(EndfieldCutout(
                max(_EnableAlphaTest, _AlphaClip),
                baseSample.a,
                _AlphaClipThreshold));

            half3 geometryNormal = normalize(i.worldNormal);
            half3 tangentWS = normalize(i.worldTangent.xyz);
            half3 binormalWS =
                cross(geometryNormal, tangentWS) * i.worldTangent.w;
            half3 normalWS = geometryNormal;
            ENDFIELD_RECOVERED_SAME_OWNER_TANGENT_DECLARE(
                endfieldSameOwnerNormalTS);
            if (_UseBumpMap > 0.5h)
            {
                half3 normalTS = EndfieldDecodePackedNormal(
                    tex2D(_BumpMap, i.uv),
                    _BumpScale);
                ENDFIELD_RECOVERED_SAME_OWNER_TANGENT_CAPTURE(
                    endfieldSameOwnerNormalTS,
                    normalTS);
                normalWS = EndfieldTangentToWorld(
                    normalTS,
                    tangentWS,
                    binormalWS,
                    geometryNormal);
            }

            // The selected CharacterNPR PreGBuffer variant signs the decoded
            // normal by the real primitive face before Y-up oct encoding.
            normalWS *= ENDFIELD_RECOVERED_FACE_IS_FRONT(facing)
                ? 1.0h
                : (-1.0h + 2.0h * _BackFaceNormalFlip);
            return ENDFIELD_RECOVERED_MAKE_PREGBUFFER_OUTPUT(
                normalWS,
                0.0,
                baseSample,
                endfieldSameOwnerNormalTS);
        }
        ENDCG

        Pass
        {
            Name "RECOVERED_PREGBUFFER_DIAGNOSTIC"
            Tags { "LightMode"="Always" }
            Cull Off
            ZWrite On
            ZTest LEqual
            Blend Off
            Stencil
            {
                Ref [_PreZStencilRefOption]
                Comp Always
                Pass Replace
            }

            CGPROGRAM
            #pragma target 5.0
            #pragma vertex ClothVert
            #pragma fragment ClothRecoveredPreGBufferDiagnosticFrag
            #pragma multi_compile __ ENDFIELD_RECOVERED_SAME_OWNER_AUDIT
            ENDCG
        }

        Pass
        {
            Name "FORWARD"
            Tags { "LightMode"="ForwardBase" }
            Cull [_Cull]
            ZWrite [_ZWrite]
            ZTest [_ZTest]
            Blend 0 [_SrcBlend] [_DstBlend]
            Blend 1 One Zero
            Blend 2 One Zero
            Blend 3 Off
            Blend 4 Off
            Blend 5 Off
            Blend 6 Off
            Blend 7 Off
            ColorMask RGBA 3
            ColorMask RGBA 4
            ColorMask RGBA 5
            ColorMask RGBA 6
            ColorMask RGBA 7
            Stencil
            {
                Ref [_PreZStencilRefOption]
                ReadMask 20
                WriteMask 20
                Comp Always
                Pass Replace
            }

            CGPROGRAM
            #pragma target 5.0
            #pragma vertex ClothVert
            #pragma fragment ClothFrag
            #pragma shader_feature_local _CHARACTER_FUR
            // Runtime-created replacement materials are the only authored
            // users, so keep both local variants in player builds instead of
            // allowing shader-feature stripping to remove the dissolve path.
            #pragma multi_compile_local_fragment _ VFX_CHARACTER_DISSOLVE
            #pragma multi_compile_fwdbase
            #pragma multi_compile_fog
            #pragma multi_compile __ ENDFIELD_RECOVERED_SOURCE_ENERGY_CORE
            #pragma multi_compile __ ENDFIELD_RECOVERED_SCREEN_SHADOW_MASK_CONSUMER
            #pragma multi_compile __ ENDFIELD_RECOVERED_SCREEN_DIRECT_AUDIT
            #pragma multi_compile __ ENDFIELD_RECOVERED_SAME_OWNER_AUDIT
            ENDCG
        }

        Pass
        {
            Name "CHARACTER_OUTLINE"
            Tags { "LightMode"="Always" }
            Cull Front
            ZWrite [_ZWrite]
            ZTest [_ZTest]
            Blend [_SrcBlend] [_DstBlend]

            CGPROGRAM
            #pragma target 5.0
            #pragma vertex ClothOutlineVert
            #pragma fragment ClothOutlineFrag
            ENDCG
        }

        Pass
        {
            Name "CAMERA_DEPTH_COPY"
            Tags { "LightMode"="Always" }
            Cull [_Cull]
            ZWrite On
            ZTest LEqual
            ColorMask R

            CGPROGRAM
            #pragma target 5.0
            #pragma vertex ClothCameraDepthVert
            #pragma fragment ClothCameraDepthFrag
            ENDCG
        }

        Pass
        {
            Name "SHADOWCASTER"
            Tags { "LightMode"="ShadowCaster" }
            Cull [_Cull]
            ZWrite On
            ZTest LEqual

            CGPROGRAM
            #pragma target 5.0
            #pragma vertex ClothShadowVert
            #pragma fragment ClothShadowFrag
            #pragma multi_compile_shadowcaster
            #pragma multi_compile __ ENDFIELD_RECOVERED_CHARACTER_SHADOW_PASS_VP
            ENDCG
        }
    }

    Fallback Off
}
