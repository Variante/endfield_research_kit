Shader "Endfield/Recovered/CharacterSkin"
{
    Properties
    {
        [MainTexture] _BaseMap ("Base Map", 2D) = "white" {}
        [MainColor] _BaseColor ("Base Color", Color) = (1,1,1,1)
        [HideInInspector] _MainTex ("Legacy Base Map", 2D) = "white" {}
        [HideInInspector] _Color ("Legacy Base Color", Color) = (1,1,1,1)
        [HideInInspector] [PerRendererData] _EndfieldRecoveredForwardLogicalDrawId ("Diagnostic Forward Logical Draw ID", Integer) = 0
        [HideInInspector] [PerRendererData] _EndfieldRecoveredForwardRenderQueue ("Diagnostic Forward Render Queue", Integer) = 0
        [HideInInspector] _RecoveredSkinBodyForwardVariant ("Exact Recovered Body Skin Forward Variant", Float) = 0
        [HideInInspector] _RecoveredBodyBaseMapPoint ("Exact Body Base Point Source", 2D) = "black" {}
        [HideInInspector] _RecoveredBodyBumpMapPoint ("Exact Body Packed Normal Point Source", 2D) = "black" {}
        [HideInInspector] _RecoveredBodyShadowLutPoint ("Exact Body Shadow LUT Point Source", 2D) = "black" {}

        _BumpMap ("Packed Normal (R*A, G)", 2D) = "bump" {}
        _UseBumpMap ("Use Bump Map", Float) = 0
        _BumpScale ("Bump Scale", Range(0,2)) = 1

        _DiffRampMap ("Diffuse Ramp", 2D) = "white" {}
        _UseDiffRampMap ("Use Diffuse Ramp", Float) = 0
        _SpecRampMap ("Specular Ramp", 2D) = "white" {}
        _UseSpecRampMap ("Use Specular Ramp", Float) = 0
        _ShadowLutTex ("Flattened 32x32x32 Skin LUT", 2D) = "white" {}
        _UseShadowLutTex ("Use Shadow LUT", Float) = 0
        _ShadowColorBrightness ("Shadow Brightness", Float) = 0.55
        _ShadowColorSaturation ("Shadow Saturation", Float) = 1.4

        _SDFLightmap ("Face SDF Light Map", 2D) = "gray" {}
        _UseSDFLightmap ("Use Face SDF", Float) = 0
        _SDFMask ("Face SDF Feature Mask", 2D) = "white" {}
        _SDFLightmapSmooth ("SDF Smooth", Range(0.001,0.3)) = 0.04
        _SDFLightmapSmoothDeadzone ("SDF Deadzone", Range(0,0.5)) = 0.02
        _SDFRimColor ("Face Rim Color", Color) = (1,0.55,0.45,1)
        _SDFRimScale ("Face Rim Scale", Float) = 0.2
        _SDFRimPower ("Face Rim Power", Float) = 3
        _SDFRimFalloff ("Face Rim Falloff", Float) = 1
        _SDFLightmapRimFalloff ("Original Face Rim Falloff", Float) = 1
        _SDFRimOffset ("Face Rim Offset", Float) = 0
        _SDFRimCameraFade ("Face Rim Camera Fade", Float) = 1
        _SkinRimOff ("Skin Rim Off", Float) = 0
        _SkinRimOffScale ("Skin Rim Off Scale", Float) = 1
        _FaceRimOffScale ("Face Rim Off Scale", Float) = 1

        _EmotionMap ("Emotion 2x2 Atlas", 2D) = "black" {}
        _UseEmotionMap ("Use Emotion Map", Float) = 0
        _EmotionIndex ("Emotion Atlas Index", Range(0,3)) = 0
        _EmotionBlend ("Emotion Blend", Range(0,1)) = 0
        _HighlightMap ("Face Highlight Map", 2D) = "black" {}
        _FaceHighlightMap ("Use Face Highlight", Float) = 0
        _HighlightMapVector ("Highlight Map Vector", Vector) = (1,1,1,1)

        _Metallic ("Metallic", Range(0,1)) = 0
        _Specular ("Specular", Range(0,1)) = 0.25
        _Smoothness ("Smoothness", Range(0,1)) = 0.35
        _SDFSpecular ("SDF Specular", Float) = 0
        _SDFSpecularScale ("SDF Specular Scale", Float) = 1
        _SDFSpecularOffset ("SDF Specular Offset", Float) = 0
        _SDFSpecularSideOffset ("SDF Specular Side Offset", Float) = 0
        _Subsurface ("Subsurface", Float) = 1
        _SubsurfaceAmount ("Subsurface Amount", Range(0,2)) = 0.25
        _SubsurfaceColor ("Subsurface Color", Color) = (1,0.45,0.36,1)

        _CharacterHeavyShadow ("Use Character Heavy Shadow", Float) = 0
        _CharacterHeavyShadowInt ("Heavy Shadow Intensity", Range(0,2)) = 1
        _CharacterHeavyShadowColor ("Heavy Shadow Color", Color) = (0.25,0.18,0.2,1)
        _CharacterHeavyShadowBackFaceFade ("Heavy Shadow Backface Fade", Float) = 1
        _CharacterHeavyShadowBackFaceFadeRange ("Heavy Shadow Backface Range", Float) = 0.25

        _EmissionMap ("Emission Map", 2D) = "black" {}
        _UseEmission ("Use Emission", Float) = 0
        [HDR] _EmissionColor ("Emission Color", Color) = (0,0,0,0)
        _EmissionBrightness ("Emission Brightness", Float) = 1

        _OutlineMask ("Outline Mask", 2D) = "white" {}
        _EnableOutlineMask ("Use Outline Mask", Float) = 0
        [HideInInspector] _UseOutlineMask ("Use Outline Mask Alias", Float) = 0
        _EnableOutline ("Enable Outline", Float) = 1
        _OutlineWidth ("Outline Width", Float) = 0.6
        _OutlineOffsetZ ("Outline Z Offset", Float) = 0
        _OutlineColorBrightness ("Outline Brightness", Float) = 0.32
        _OutlineColorSaturation ("Outline Saturation", Float) = 1.05
        _OutlineColor ("Outline Tint", Color) = (1,1,1,1)

        _EnableAlphaTest ("Enable Alpha Test", Float) = 0
        [HideInInspector] _AlphaClip ("Alpha Clip Alias", Float) = 0
        _AlphaClipThreshold ("Alpha Clip Threshold", Range(0,1)) = 0.5
        [Enum(UnityEngine.Rendering.CullMode)] _Cull ("Cull", Float) = 2
        [HideInInspector] [Enum(On,0,Off,1)] _BackFaceNormalFlip ("Original Back Face Normal Flip", Float) = 0
        [Enum(UnityEngine.Rendering.BlendMode)] _SrcBlend ("Source Blend", Float) = 1
        [Enum(UnityEngine.Rendering.BlendMode)] _DstBlend ("Destination Blend", Float) = 0
        [Enum(Off,0,On,1)] _ZWrite ("Z Write", Float) = 1
        [Enum(UnityEngine.Rendering.CompareFunction)] _ZTest ("Z Test", Float) = 4
        [HideInInspector] _RecoveredSourceZTest ("Original Source Z Test", Float) = 4
        [HideInInspector] _StencilRefOption ("Character Stencil Ref", Float) = 4
        [HideInInspector] _OriginalHGRPProfile ("Original HGRP Profile", Float) = 1

        _RecoveredBandSoftness ("Recovered Band Softness", Range(0.001,0.5)) = 0.075
        _RecoveredAmbientStrength ("Recovered Ambient Strength", Range(0,2)) = 0.72
        _RecoveredDirectStrength ("Recovered Direct Strength", Range(0,2)) = 0.95
        _RecoveredOutlineScale ("Recovered Outline Scale", Float) = 0.0035
        _RecoveredOutlineZScale ("Recovered Outline Z Scale", Float) = 0.00001
    }

    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry" }
        LOD 400

        CGINCLUDE
        #include "UnityCG.cginc"
        #include "Lighting.cginc"
        #include "AutoLight.cginc"
        #include "EndfieldCharacterRecoveredCommon.cginc"
        #include "../HGRPCompat/EndfieldHGRPCharacterLighting.cginc"

        float4x4 unity_MatrixPreviousM;
        float4 unity_MotionVectorsParams;

        sampler2D _BaseMap;
        float4 _BaseMap_ST;
        sampler2D _BumpMap;
        sampler2D _DiffRampMap;
        sampler2D _SpecRampMap;
        sampler2D _ShadowLutTex;
        sampler2D _SDFLightmap;
        sampler2D _SDFMask;
        sampler2D _EmotionMap;
        Texture2D<float4> _RecoveredBodyBaseMapPoint;
        Texture2D<float4> _RecoveredBodyBumpMapPoint;
        Texture2D<float4> _RecoveredBodyShadowLutPoint;
        SamplerState endfield_point_mirror_sampler;
        SamplerState endfield_point_repeat_sampler;
        SamplerState endfield_point_clamp_sampler;
        Texture2D<float4> _HighlightMap;
        SamplerState endfield_point_mirroronce_sampler;
        sampler2D _EmissionMap;
        sampler2D _OutlineMask;

        half4 _BaseColor;
        half _RecoveredSkinBodyForwardVariant;
        half _UseBumpMap;
        half _BumpScale;
        half _UseDiffRampMap;
        half _UseSpecRampMap;
        half _UseShadowLutTex;
        half _ShadowColorBrightness;
        half _ShadowColorSaturation;
        half _UseSDFLightmap;
        half _SDFLightmapSmooth;
        half _SDFLightmapSmoothDeadzone;
        half4 _SDFRimColor;
        half _SDFRimScale;
        half _SDFRimPower;
        half _SDFRimFalloff;
        half _SDFLightmapRimFalloff;
        half _SDFRimOffset;
        half _SDFRimCameraFade;
        half _SkinRimOff;
        half _SkinRimOffScale;
        half _FaceRimOffScale;
        half _UseEmotionMap;
        half _EmotionIndex;
        half _EmotionBlend;
        half _FaceHighlightMap;
        half4 _HighlightMapVector;
        half _Metallic;
        half _Specular;
        half _Smoothness;
        half _SDFSpecular;
        half _SDFSpecularScale;
        half _SDFSpecularOffset;
        half _SDFSpecularSideOffset;
        half _Subsurface;
        half _SubsurfaceAmount;
        half4 _SubsurfaceColor;
        half _CharacterHeavyShadow;
        half _CharacterHeavyShadowInt;
        half4 _CharacterHeavyShadowColor;
        half _CharacterHeavyShadowBackFaceFade;
        half _CharacterHeavyShadowBackFaceFadeRange;
        half _UseEmission;
        half4 _EmissionColor;
        half _EmissionBrightness;
        half _EnableOutlineMask;
        half _UseOutlineMask;
        half _EnableOutline;
        half _OutlineWidth;
        half _OutlineOffsetZ;
        half _OutlineColorBrightness;
        half _OutlineColorSaturation;
        half4 _OutlineColor;
        half _EnableAlphaTest;
        half _AlphaClip;
        half _AlphaClipThreshold;
        half _BackFaceNormalFlip;
        half _RecoveredBandSoftness;
        half _RecoveredAmbientStrength;
        half _RecoveredDirectStrength;
        half _RecoveredOutlineScale;
        half _RecoveredOutlineZScale;
        float _EndfieldRecoveredFaceHighlightSemantics;
        float _GlobalMipBias;

        float3 EndfieldRecoveredBodyShadowLutPoint(float3 linearBaseColor)
        {
            #if defined(UNITY_COLORSPACE_GAMMA)
                float3 srgb = saturate(linearBaseColor);
            #else
                float3 srgb = saturate(EndfieldLinearToSRGB(linearBaseColor));
            #endif
            float blueSlice = srgb.b * 31.0;
            float slice0 = floor(blueSlice);
            float2 uv0 = float2(
                (slice0 * 32.0 + srgb.r * 31.0 + 0.5) / 1024.0,
                (srgb.g * 31.0 + 0.5) / 32.0);
            float2 uv1 = uv0 + float2(1.0 / 32.0, 0.0);
            float3 value0 = _RecoveredBodyShadowLutPoint.SampleLevel(
                endfield_point_clamp_sampler,
                uv0,
                0.0).rgb;
            float3 value1 = _RecoveredBodyShadowLutPoint.SampleLevel(
                endfield_point_clamp_sampler,
                uv1,
                0.0).rgb;
            return lerp(value0, value1, frac(blueSlice));
        }

        struct SkinAppData
        {
            float4 vertex : POSITION;
            float3 normal : NORMAL;
            float4 tangent : TANGENT;
            float2 uv : TEXCOORD0;
            float3 positionOld : TEXCOORD4;
        };

        struct SkinVaryings
        {
            float4 pos : SV_POSITION;
            float2 uv : TEXCOORD0;
            float3 worldPos : TEXCOORD1;
            half3 worldNormal : TEXCOORD2;
            float4 worldTangent : TEXCOORD3;
            UNITY_SHADOW_COORDS(5)
            float3 currentClipXYW : TEXCOORD6;
            float3 previousClipXYW : TEXCOORD7;
        };

        SkinVaryings SkinVert(SkinAppData v)
        {
            SkinVaryings o;
            o.pos = UnityObjectToClipPos(v.vertex);
            o.currentClipXYW = o.pos.xyw;
            float4 previousLocalPosition = lerp(
                v.vertex,
                float4(v.positionOld, 1.0),
                step(0.5, unity_MotionVectorsParams.x));
            o.previousClipXYW = mul(
                UNITY_MATRIX_VP,
                mul(unity_MatrixPreviousM, previousLocalPosition)).xyw;
            o.uv = TRANSFORM_TEX(v.uv, _BaseMap);
            o.worldPos = mul(unity_ObjectToWorld, v.vertex).xyz;
            o.worldNormal = normalize(UnityObjectToWorldNormal(v.normal));
            o.worldTangent = float4(
                normalize(UnityObjectToWorldDir(v.tangent.xyz)),
                v.tangent.w);
            UNITY_TRANSFER_SHADOW(o, v.uv);
            return o;
        }

        float EndfieldRecoveredSignedSdfNdotL(float sdfValue, float wrappedNdotL)
        {
            float halfWrap = wrappedNdotL * 0.5;
            float threshold = clamp(0.5 - halfWrap, 0.001, 0.999);
            float lower = max(2.0 * threshold - 1.0, 0.0);
            float upper = min(2.0 * threshold, 1.0);
            float value = saturate((sdfValue * 0.5 - lower) / (upper - lower));
            value = value * value * (3.0 - 2.0 * value);
            return (value + ceil(halfWrap) * halfWrap) * 2.0 - 1.0;
        }

        half4 SkinFrag(
            SkinVaryings i,
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
            half2 uv = i.uv;
            // Exact material identity is authored by the importer. The
            // additional visible-state checks keep stale material assets from
            // entering this neutral-static source reduction.
            bool sourceExactBodyForwardVariant = false;
            #if defined(ENDFIELD_RECOVERED_SOURCE_ENERGY_CORE)
                sourceExactBodyForwardVariant =
                    _RecoveredSkinBodyForwardVariant > 0.5h &&
                    _UseSDFLightmap < 0.5h &&
                    _UseBumpMap > 0.5h &&
                    _UseDiffRampMap > 0.5h &&
                    _UseShadowLutTex > 0.5h &&
                    abs((float)_Metallic) < 1e-6 &&
                    _CharacterParams10.x < 0.5;
            #endif
            half4 baseSample = tex2D(_BaseMap, uv) * _BaseColor;
            if (sourceExactBodyForwardVariant)
            {
                // Vulkan source: SampleBias(PointMirror). D3D independently
                // agrees on point filtering and bias, while its recovered
                // address label is ambiguous; that boundary is documented.
                baseSample = (half4)_RecoveredBodyBaseMapPoint.SampleBias(
                    endfield_point_mirror_sampler,
                    (float2)uv,
                    _GlobalMipBias) * _BaseColor;
            }

            if (_UseEmotionMap > 0.5h && _EmotionBlend > 0.001h)
            {
                half emotionIndex = clamp(floor(_EmotionIndex + 0.5h), 0.0h, 3.0h);
                half2 emotionTile = half2(fmod(emotionIndex, 2.0h), floor(emotionIndex * 0.5h));
                half2 emotionUv = uv * 0.5h + emotionTile * 0.5h;
                half4 emotion = tex2D(_EmotionMap, emotionUv);
                baseSample.rgb = lerp(
                    baseSample.rgb,
                    emotion.rgb,
                    saturate(emotion.a * _EmotionBlend));
            }

            half alphaTest = max(_EnableAlphaTest, _AlphaClip);
            clip(EndfieldCutout(alphaTest, baseSample.a, _AlphaClipThreshold));

            half3 geometryNormal = normalize(i.worldNormal);
            half3 tangentWS = normalize(i.worldTangent.xyz);
            half3 binormalWS =
                cross(geometryNormal, tangentWS) * i.worldTangent.w;
            half3 normalWS = geometryNormal;
            ENDFIELD_RECOVERED_SAME_OWNER_TANGENT_DECLARE(
                endfieldSameOwnerNormalTS);
            if (_UseBumpMap > 0.5h)
            {
                half4 packedNormalSample = tex2D(_BumpMap, uv);
                if (sourceExactBodyForwardVariant)
                {
                    // Both sources agree on Point+SampleBias; Vulkan names the
                    // selected packed-normal address mode Repeat.
                    packedNormalSample =
                        (half4)_RecoveredBodyBumpMapPoint.SampleBias(
                            endfield_point_repeat_sampler,
                            (float2)uv,
                            _GlobalMipBias);
                }
                half3 normalTS = EndfieldDecodePackedNormal(
                    packedNormalSample,
                    _BumpScale);
                ENDFIELD_RECOVERED_SAME_OWNER_TANGENT_CAPTURE(
                    endfieldSameOwnerNormalTS,
                    normalTS);
                normalWS = EndfieldTangentToWorld(normalTS, tangentWS, binormalWS, geometryNormal);
            }

            half faceSign = ENDFIELD_RECOVERED_FACE_IS_FRONT(facing)
                ? 1.0h
                : (-1.0h + 2.0h * _BackFaceNormalFlip);
            half3 faceGeometryNormal = geometryNormal * faceSign;
            normalWS *= faceSign;

            half3 viewWS = normalize(UnityWorldSpaceViewDir(i.worldPos));
            half3 sceneLightWS = normalize(UnityWorldSpaceLightDir(i.worldPos));
            half3 lightWS = EndfieldHGRPCharacterLightDirection(sceneLightWS);
            half3 halfWS = normalize(lightWS + viewWS);
            half nDotL = dot(normalWS, lightWS);
            half nDotV = dot(normalWS, viewWS);
            half nDotH = saturate(dot(normalWS, halfWS));
            #if defined(ENDFIELD_RECOVERED_SKIN_SCREEN_SHADOW_MASK_RG)
                float2 recoveredScreenShadowMask =
                    EndfieldHGRPLoadSkinScreenSpaceShadowMaskRG(i.pos.xy);
                // Source-shaped retail boundary: R enters the scene selector
                // and G replaces the local character-atlas solve.
                float sceneShadowAttenuation = recoveredScreenShadowMask.x;
                float characterShadowAttenuation = recoveredScreenShadowMask.y;
            #elif defined(ENDFIELD_RECOVERED_SCREEN_SHADOW_MASK_CONSUMER)
                float2 recoveredScreenShadowMask =
                    EndfieldHGRPLoadRecoveredScreenShadowMask(i.pos.xy);
                // Diagnostic comparison boundary: the separate diagnostic
                // texture is intentionally not the retail global binding.
                float sceneShadowAttenuation = recoveredScreenShadowMask.x;
                float characterShadowAttenuation = recoveredScreenShadowMask.y;
            #else
                half sceneShadowAttenuation =
                    UNITY_SHADOW_ATTENUATION(i, i.worldPos);
                half characterShadowAttenuation = EndfieldHGRPSampleCharacterShadow(
                    EndfieldHGRPCharacterShadowCoord(i.worldPos, faceGeometryNormal),
                    i.pos.xy);
            #endif
            ENDFIELD_WRITE_RECOVERED_SCREEN_DIRECT_AUDIT(
                i.pos.xy,
                i.worldPos,
                faceGeometryNormal,
                ENDFIELD_RECOVERED_FACE_VALUE(facing),
                1.0,
                1.0 / 3.0);
            ENDFIELD_WRITE_RECOVERED_SAME_OWNER_AUDIT(
                i.pos.xy,
                normalWS,
                faceGeometryNormal,
                ENDFIELD_RECOVERED_FACE_VALUE(facing),
                ENDFIELD_RECOVERED_SAME_OWNER_PRIMITIVE_VALUE,
                1u,
                1.0 / 3.0,
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

            half4 sdfMask = tex2D(_SDFMask, uv);
            half compatibilityWeight = EndfieldHGRPCompatibilityWeight();
            half sourceRecoveryWeight = compatibilityWeight;
            #if defined(ENDFIELD_RECOVERED_SOURCE_ENERGY_CORE)
                sourceRecoveryWeight = 1.0h;
            #endif
            // This is the neutral-static CharInfo reduction. CP10.x only
            // rejects an active global weather override; retail can otherwise
            // read a packed renderer-instance weather carrier that the lab
            // does not yet expose, and that limitation remains explicit.
            // The shipped Skin fragment uses the raw CP1.w lerp result for its
            // NPR dot products and SDF branch.  The shared compatibility helper
            // normalizes that result for the conventional fallback path, so
            // retain the exact raw vector locally when compatibility is active.
            float3 sourceCharacterLightWS = lerp(
                (float3)sceneLightWS,
                (float3)_CharacterParams11.xyz,
                _CharacterParams1.w * sourceRecoveryWeight);
            half3 cameraForwardWS = normalize(float3(
                UNITY_MATRIX_I_V._m02,
                UNITY_MATRIX_I_V._m12,
                UNITY_MATRIX_I_V._m22));
            float3 skinObjectOrigin = float3(
                unity_ObjectToWorld._m03,
                i.worldPos.y,
                unity_ObjectToWorld._m23);
            float3 skinFlatDirection = (float3)i.worldPos - skinObjectOrigin;
            skinFlatDirection.y = 6.103515625e-5;
            skinFlatDirection *= rsqrt(max(
                dot(skinFlatDirection, skinFlatDirection),
                1.1754943508222875e-38));
            float3 skinFaceDiffuseNormal = (float3)normalWS;
            float3 cameraForwardOS = mul(
                (float3x3)unity_WorldToObject,
                (float3)cameraForwardWS);
            cameraForwardOS *= rsqrt(max(
                dot(cameraForwardOS, cameraForwardOS),
                1.1754943508222875e-38));
            float2 cameraForwardObjectXZ = cameraForwardOS.xz;
            cameraForwardObjectXZ *= rsqrt(max(
                dot(cameraForwardObjectXZ, cameraForwardObjectXZ),
                1.1754943508222875e-38));
            float objectCameraForwardXZ = cameraForwardObjectXZ.y;
            half rangeBias =
                _CharacterParams11.w * _CharacterParams12.x *
                sourceRecoveryWeight;
            half sourceNdotL = dot(normalWS, (half3)sourceCharacterLightWS);
            half rampSigned = clamp(
                lerp(nDotL, sourceNdotL, sourceRecoveryWeight) + rangeBias,
                -1.0h,
                1.0h);

            half3 normalFlat = half3(normalWS.x, 1e-4h, normalWS.z);
            normalFlat *= rsqrt(max(dot(normalFlat, normalFlat), 1e-5h));
            half3 blendedAmbientDirection = normalFlat;
            if (_UseSDFLightmap > 0.5h)
            {
                // The shipped fragment reads the renderer instance's raw
                // object-to-world rows, not a separate face/head basis.  These
                // columns reproduce its world-to-object light transform and its
                // object-to-world SDF-normal transform without normalizing each
                // axis independently.
                float3 faceRightWS = float3(
                    unity_ObjectToWorld._m00,
                    unity_ObjectToWorld._m10,
                    unity_ObjectToWorld._m20);
                float3 faceUpWS = float3(
                    unity_ObjectToWorld._m01,
                    unity_ObjectToWorld._m11,
                    unity_ObjectToWorld._m21);
                float3 faceForwardWS = float3(
                    unity_ObjectToWorld._m02,
                    unity_ObjectToWorld._m12,
                    unity_ObjectToWorld._m22);

                float3 objectLightDirection = float3(
                    dot(sourceCharacterLightWS, faceRightWS),
                    6.103515625e-5,
                    dot(sourceCharacterLightWS, faceForwardWS));
                objectLightDirection *= rsqrt(max(
                    dot(objectLightDirection, objectLightDirection),
                    1.1754943508222875e-38));
                float sdfLightZ = objectLightDirection.z;
                float lightSide = objectLightDirection.x > 0.0 ? 1.0 : 0.0;
                float2 sdfUv = float2(lerp(1.0 - uv.x, uv.x, lightSide), uv.y);
                float4 sdf = tex2Dlod(_SDFLightmap, float4(sdfUv, 0, 0));

                float flatNormalXBase = 1.0 - 2.0 * sdf.b;
                float flatNormalX = lerp(flatNormalXBase, -flatNormalXBase, lightSide);
                float flatNormalZ = 1.0 - abs(flatNormalX);
                float3 sdfNormalWS = normalize(
                    flatNormalX * faceRightWS +
                    6.103515625e-5 * faceUpWS +
                    flatNormalZ * faceForwardWS);
                half3 sdfBlendedNormal = normalize(lerp(
                    sdfNormalWS,
                    normalWS,
                    saturate(sdfMask.g)));
                skinFaceDiffuseNormal = (float3)sdfBlendedNormal;

                float3 flatSourceLightWS = normalize(float3(
                    sourceCharacterLightWS.x,
                    6.103515625e-5,
                    sourceCharacterLightWS.z));
                float2 cameraXZ = normalize((float2)cameraForwardWS.xz);
                float cameraLightDot = -dot(flatSourceLightWS.xz, cameraXZ);
                float backlitFactor = saturate(cameraLightDot) * saturate(-sdfLightZ) *
                    (1.0 - _CharacterParams12.x * sourceRecoveryWeight);
                float wrappedNdotL = sdfLightZ + backlitFactor *
                    0.5 * (1.0 - sdfLightZ * sdfLightZ);
                float sdfNdotL = EndfieldRecoveredSignedSdfNdotL(
                    sdf.r + sdf.g,
                    wrappedNdotL);
                rampSigned = lerp(sdfNdotL, rampSigned, saturate(sdfMask.g));

                blendedAmbientDirection = normalize(lerp(
                    (half3)skinFlatDirection,
                    normalFlat,
                    saturate(sdfMask.g)));
            }

            half defaultRampAlpha = EndfieldDefaultDiffuseBand(
                rampSigned,
                _RecoveredBandSoftness);
            half4 diffuseRamp = tex2Dlod(
                _DiffRampMap,
                half4(saturate(rampSigned * 0.5h + 0.5h), 0.5h, 0, 0));
            half useDiffuseRamp = saturate(_UseDiffRampMap);
            half rampAlpha = lerp(defaultRampAlpha, diffuseRamp.a, useDiffuseRamp);
            half3 rampColor = lerp(half3(1,1,1), diffuseRamp.rgb, useDiffuseRamp);
            half rampChroma = max(rampColor.r, max(rampColor.g, rampColor.b)) -
                              min(rampColor.r, min(rampColor.g, rampColor.b));
            half rampChromaInverse = 1.0h - rampChroma;

            half castShadow = lerp(shadowAttenuation, 1.0h, saturate(_UseSDFLightmap));
            half minShadow = saturate(min(rampAlpha, baseSample.a) * castShadow);
            half litAmount = minShadow;

            half oneMinusReflectivity = (1.0h - _Metallic) * 0.96h;
            half3 diffuseAlbedo = oneMinusReflectivity * baseSample.rgb;
            float sourceFaceArea = (float)sdfMask.r * lerp(
                saturate(objectCameraForwardXZ + 0.5),
                1.0,
                (float)sdfMask.g);
            float sourceGrazing = 1.0 - saturate(
                saturate(dot((float3)faceGeometryNormal, (float3)viewWS)) *
                0.85 + 0.15);
            float sourceSdfRimWeight = saturate(
                sourceGrazing * sourceFaceArea * lerp(
                    (float)_SkinRimOff,
                    (float)_SkinRimOffScale,
                    (float)sdfMask.b));
            float3 sourceBaseWithSdfRim = (float3)baseSample.rgb * lerp(
                float3(1.0, 1.0, 1.0),
                (float3)_SDFRimColor.rgb,
                sourceSdfRimWeight);
            if (sourceExactBodyForwardVariant)
            {
                // Exact normal-mapped body variant: unlike the face path,
                // grazing rim weight is independent of SDFMask channels and
                // uses the packed-normal shading normal, not face geometry.
                float sourceBodyGrazing = 1.0 - saturate(
                    saturate(dot((float3)normalWS, (float3)viewWS)) *
                        0.85 + 0.15);
                float sourceBodyRimWeight = saturate(
                    sourceBodyGrazing * (float)_SkinRimOffScale);
                sourceBaseWithSdfRim = (float3)baseSample.rgb * lerp(
                    float3(1.0, 1.0, 1.0),
                    (float3)_SDFRimColor.rgb,
                    sourceBodyRimWeight);
            }
            float3 sourceSkinDiffuseAlbedo = sourceBaseWithSdfRim *
                (0.96 - (float)_Metallic * 0.96);
            half3 rawShadowColor = EndfieldShadowColor(
                _ShadowLutTex,
                _UseShadowLutTex,
                baseSample.rgb,
                _ShadowColorBrightness,
                _ShadowColorSaturation);
            if (sourceExactBodyForwardVariant)
            {
                // Retail uses PointClamp LOD0 for R/G quantization and manually
                // interpolates only the adjacent blue slices.
                rawShadowColor = (half3)EndfieldRecoveredBodyShadowLutPoint(
                    (float3)baseSample.rgb);
            }
            half3 shadowLut = oneMinusReflectivity * rawShadowColor;

            half3 ambientTint = EndfieldHGRPCharacterShadowTint(1.0h);
            half ambientLobe = EndfieldHGRPCharacterAmbientLobe(blendedAmbientDirection);
            half shadowStrength = minShadow * _CharacterParams1.y;
            half3 shadowedAmbient = ambientLobe *
                (shadowStrength * (1.0h - ambientTint) + ambientTint);

            half recoveredAmbientExposure = lerp(
                max(_EnvironmentGlobalParams0.x, 0.0h),
                1.0h,
                saturate(_CharacterParams12.w)) *
                max(_ExposureParams.x, 0.0h);
            half ambientExposure = lerp(
                1.0h,
                recoveredAmbientExposure,
                compatibilityWeight);
            half brightFull = clamp(ambientExposure, 0.0h, 1.5h);
            half3 mainLightColor = lerp(
                _LightColor0.rgb,
                _CharacterParams4.rgb,
                saturate(_CharacterParams12.y) * compatibilityWeight);
            half lightLuminance = EndfieldLuma(mainLightColor);
            half overrideColorGate = saturate(_CharacterParams12.y) * compatibilityWeight;
            half3 lightBlend = mainLightColor * overrideColorGate +
                               (1.0h - overrideColorGate);
            half3 fullDiffuse =
                (shadowedAmbient * brightFull * lightBlend +
                 minShadow * (mainLightColor - lightLuminance) +
                 lightLuminance) * EndfieldHGRPMainLightMultiplier();

            half3 ambientScaled = shadowLut * EndfieldHGRPEnvironmentLightMultiplier();
            half ambientScaledLuminance = EndfieldLuma(ambientScaled * 0.65h);
            half3 desaturatedShadow =
                (ambientScaled * 0.65h - ambientScaledLuminance) * 1.2h +
                ambientScaledLuminance;
            half combinationWeight = saturate(baseSample.a + rampAlpha);
            half3 weightedAmbient = lerp(
                desaturatedShadow,
                ambientScaled,
                combinationWeight);
            half3 shadowBlended = lerp(weightedAmbient, diffuseAlbedo, minShadow);
            half3 rampTinted = shadowBlended *
                (rampColor * rampChroma + rampChromaInverse);
            half rampLuminance = EndfieldLuma(rampTinted);
            half luminanceRatio = clamp(
                EndfieldLuma(shadowBlended) / max(rampLuminance, 0.001h),
                0.0h,
                1.5h);
            half3 recoveredDiffuseColor = fullDiffuse * rampTinted * luminanceRatio;

            // Exact selected Skin punctual diffuse carrier. Unlike the main
            // directional endpoint above, this keeps the original scene-shadow
            // selector and SDF-aware character-shadow mix.
            float sourceFaceShadowWeight = max(
                (float)sdfMask.g,
                (float)sdfMask.b * smoothstep(
                    0.75,
                    0.25,
                    objectCameraForwardXZ));
            if (sourceExactBodyForwardVariant)
                sourceFaceShadowWeight = 1.0;
            float sourceCharacterShadowMix = lerp(
                1.0,
                (float)characterShadowAttenuation,
                sourceFaceShadowWeight);
            float sourceMinimumState = min(
                min(sourceCharacterShadowMix, (float)baseSample.a),
                (float)rampAlpha);
            float sourceShadowMixWeight = saturate(
                (float)baseSample.a *
                    ((1.0 - (float)sdfMask.g) +
                     sourceCharacterShadowMix * (float)sdfMask.g) +
                (float)rampAlpha);
            if (sourceExactBodyForwardVariant)
            {
                sourceShadowMixWeight = saturate(
                    (float)baseSample.a * sourceCharacterShadowMix +
                    (float)rampAlpha);
            }
            float3 sourceAmbientScaled = (float3)ambientScaled;
            #if defined(ENDFIELD_RECOVERED_SOURCE_ENERGY_CORE)
                sourceAmbientScaled =
                    (float3)shadowLut * _CharacterParams0.z;
            #endif
            float3 sourceAmbientDark = sourceAmbientScaled * 0.65;
            float sourceAmbientDarkLuminance =
                EndfieldHGRPRecoveredLuma(sourceAmbientDark);
            float3 sourceAmbientDesaturated = lerp(
                sourceAmbientDarkLuminance.xxx,
                sourceAmbientDark,
                1.2);
            float3 sourceRampBase = lerp(
                lerp(
                    sourceAmbientDesaturated,
                    sourceAmbientScaled,
                    sourceShadowMixWeight),
                sourceSkinDiffuseAlbedo,
                sourceMinimumState);
            float3 sourceRampTinted = sourceRampBase *
                ((1.0 - (float)rampChroma) +
                 (float3)rampColor * (float)rampChroma);
            float sourceRampLuminance = max(
                EndfieldHGRPRecoveredLuma(sourceRampTinted),
                0.001);
            float3 sourceLuminancePreserved = sourceRampTinted * clamp(
                EndfieldHGRPRecoveredLuma(sourceRampBase) /
                    sourceRampLuminance,
                0.0,
                1.5);
            float3 sourceSceneFallback = lerp(
                sourceAmbientScaled,
                lerp(
                    EndfieldHGRPRecoveredLuma(
                        sourceSkinDiffuseAlbedo).xxx,
                    sourceSkinDiffuseAlbedo,
                    1.2),
                (float)baseSample.a * sourceCharacterShadowMix);
            float3 sourceSkinNprDiffuse = lerp(
                sourceSceneFallback,
                sourceLuminancePreserved,
                (float)resolvedSceneShadowAttenuation);
            float3 sourceSkinAngularNormal = normalize(lerp(
                float3(
                    skinFlatDirection.x,
                    6.103515625e-5,
                    skinFlatDirection.z),
                skinFaceDiffuseNormal,
                (float)sdfMask.g));
            float3 sourceSkinF0 =
                (0.04 * (float)_Specular * (float)sdfMask.g).xxx;
            if (sourceExactBodyForwardVariant)
            {
                sourceSkinAngularNormal = normalize((float3)normalWS);
                sourceSkinF0 = (0.04 * (float)_Specular).xxx;
            }

            // Exact selected Skin main-directional energy. Unlike the legacy
            // reconstruction above, this consumes the recovered native-shaped
            // main-light intensity and preserves both scene-shadow endpoints.
            float sourceSkinAmbientLobe =
                saturate(dot(
                    normalize((float3)blendedAmbientDirection),
                    _CharacterParams6.xyz) + _CharacterParams7.x) *
                _CharacterParams7.y + _CharacterParams7.z;
            float3 sourceSkinShadowedAmbient = sourceSkinAmbientLobe *
                (sourceMinimumState * _CharacterParams1.y *
                    (1.0 - _CharacterParams3.rgb) +
                 _CharacterParams3.rgb);
            float sourceSkinAmbientExposure =
                (_CharacterParams12.w *
                    (1.0 - _EnvironmentGlobalParams0.x) +
                 _EnvironmentGlobalParams0.x) * _ExposureParams.x;
            float sourceSkinBright065 = min(
                sourceSkinAmbientExposure * 0.35 + 0.65,
                1.5);
            float sourceSkinBrightAlternate = clamp(
                sourceSkinAmbientExposure,
                1.25,
                1.75);
            float sourceSkinBrightMix = lerp(
                sourceSkinBright065,
                sourceSkinBrightAlternate,
                _CharacterParams1.x);
            float3 sourceSkinBrightAmbient =
                sourceSkinShadowedAmbient * sourceSkinBrightMix *
                _CharacterParams0.w;
            float3 sourceSkinBaseMainLightColor = lerp(
                (float3)_LightColor0.rgb,
                _CharacterParams4.rgb,
                _CharacterParams12.y);
            float3 sourceSkinMainLightColor = sourceSkinBaseMainLightColor;
            float sourceSkinNativeMainIntensity =
                EndfieldHGRPCharacterMainIntensity();
            #if defined(ENDFIELD_RECOVERED_SOURCE_ENERGY_CORE)
                sourceSkinNativeMainIntensity = max(
                    _EndfieldCharMainLightIntensity,
                    0.0);
            #endif
            sourceSkinMainLightColor *= lerp(
                sourceSkinNativeMainIntensity,
                1.0,
                _CharacterParams12.w);
            float sourceSkinMainLightLuminance =
                EndfieldHGRPRecoveredLuma(sourceSkinMainLightColor);
            // All three installed playable face witnesses (Wulfa, Zhuangfy,
            // and Li's normal-mapped face) keep the unscaled directional RGB
            // for this ambient lightBlend. The intensity-scaled carrier is
            // used only by the neighboring luma/chroma direct term. The body
            // witness has the same split.
            float3 sourceSkinLightBlend =
                sourceSkinBaseMainLightColor * _CharacterParams12.y +
                (1.0 - _CharacterParams12.y);
            float3 sourceSkinFullDirect =
                (sourceSkinShadowedAmbient *
                    clamp(sourceSkinAmbientExposure, 0.0, 1.5) *
                    sourceSkinLightBlend +
                 sourceMinimumState *
                    (sourceSkinMainLightColor -
                     sourceSkinMainLightLuminance) +
                 sourceSkinMainLightLuminance) * _CharacterParams0.y;
            float3 sourceSkinFullDiffuse = lerp(
                sourceSkinBrightAmbient,
                sourceSkinFullDirect,
                (float)resolvedSceneShadowAttenuation);
            float sourceSkinViewState =
                (float)baseSample.a * sourceCharacterShadowMix;
            float sourceSkinNprShadow = lerp(
                sourceSkinViewState,
                sourceMinimumState,
                (float)resolvedSceneShadowAttenuation);
            float sourceSkinAmbientDiffuseIntensity = lerp(
                _CharacterParams0.z,
                1.0,
                sourceSkinNprShadow);
            float sourceSkinSpecularAmbientIntensity =
                sourceSkinAmbientDiffuseIntensity *
                (sourceSkinNprShadow * 0.5 + 0.5);

            // Exact selected Skin directional GGX and HighlightMap carrier.
            // Both terms share fullDiffuse*specAmbient; HighlightMap is RGB
            // only and uses the original view-shifted object-basis UV.
            float3 sourceSkinCameraMod = normalize(float3(
                cameraForwardWS.x,
                lerp(
                    0.5,
                    sourceCharacterLightWS.y,
                    (float)resolvedSceneShadowAttenuation),
                cameraForwardWS.z));
            float3 sourceSkinHalfDirection = normalize(
                sourceCharacterLightWS *
                    (float)resolvedSceneShadowAttenuation +
                sourceSkinCameraMod * 2.0 +
                (float3)viewWS *
                    (2.0 + (float)resolvedSceneShadowAttenuation));
            float sourceSkinNoV = saturate(dot(
                (float3)normalWS,
                (float3)viewWS));
            float sourceSkinNoH = dot(
                (float3)normalWS,
                sourceSkinHalfDirection);
            float sourceSkinPerceptualRoughness =
                1.0 - (float)_Smoothness;
            float sourceSkinAlpha = max(
                sourceSkinPerceptualRoughness *
                    sourceSkinPerceptualRoughness,
                0.0078125);
            float sourceSkinAlphaSquared =
                sourceSkinAlpha * sourceSkinAlpha;
            float sourceSkinGgxDenominator =
                (sourceSkinNoH * sourceSkinAlphaSquared -
                 sourceSkinNoH) * sourceSkinNoH + 1.0;
            float sourceSkinGgxDenominatorSquared =
                sourceSkinGgxDenominator * sourceSkinGgxDenominator;
            float sourceSkinDistribution =
                sourceSkinAlphaSquared !=
                    sourceSkinGgxDenominatorSquared
                ? sourceSkinAlphaSquared /
                    sourceSkinGgxDenominatorSquared
                : 1.0;
            float sourceSkinGgx = clamp(
                sourceSkinDistribution * 0.5 /
                    (sourceSkinNoV * 2.0 +
                     sourceSkinAlpha + 1e-4) -
                    6.103515625e-5,
                0.0,
                20.0);
            float3 sourceSkinSpecularHighlightCarrier =
                sourceSkinFullDiffuse *
                sourceSkinSpecularAmbientIntensity;
            float3 sourceSkinDirectSpecular =
                sourceSkinF0 * sourceSkinGgx *
                sourceSkinSpecularHighlightCarrier *
                _CharacterParams13.w;
            float3 sourceSkinHighlightBasisX = float3(
                unity_ObjectToWorld._m00,
                unity_ObjectToWorld._m10,
                unity_ObjectToWorld._m20);
            float3 sourceSkinHighlightBasisY = float3(
                unity_ObjectToWorld._m01,
                unity_ObjectToWorld._m11,
                unity_ObjectToWorld._m21);
            float2 sourceSkinHighlightUv = uv + float2(
                dot((float3)viewWS, sourceSkinHighlightBasisX) *
                    _HighlightMapVector.x,
                dot((float3)viewWS, sourceSkinHighlightBasisY) *
                    _HighlightMapVector.y);
            float3 sourceSkinHighlight =
                (float3)_HighlightMap.SampleBias(
                    endfield_point_mirroronce_sampler,
                    sourceSkinHighlightUv,
                    _GlobalMipBias).rgb *
                sourceSkinSpecularHighlightCarrier *
                float(_FaceHighlightMap > 0.5h);
            #if defined(ENDFIELD_RECOVERED_SOURCE_ENERGY_CORE)
                recoveredDiffuseColor = (half3)(
                    sourceSkinFullDiffuse * sourceSkinNprDiffuse);
            #endif

            // Keep a neutral fallback for non-HGRP inspection while the active
            // compatibility path uses the recovered luminance-preserving core.
            half3 fallbackShadow = rawShadowColor * ambientTint;
            half3 fallbackDiffuse = lerp(
                fallbackShadow,
                baseSample.rgb * rampColor,
                minShadow);
            half3 fallbackAmbient =
                (half3(0.22h,0.22h,0.22h) + EndfieldAmbient(normalWS)) *
                _RecoveredAmbientStrength *
                EndfieldHGRPEnvironmentLightMultiplier() *
                EndfieldHGRPCharacterAmbientLobe(normalWS) *
                EndfieldHGRPSceneEnvironmentWeight();
            fallbackAmbient *= lerp(
                EndfieldHGRPEnvironmentShadowMultiplier(),
                1.0h,
                minShadow);
            half3 fallbackDirect = mainLightColor * _RecoveredDirectStrength *
                EndfieldHGRPMainLightMultiplier() * lerp(0.4h, 1.0h, minShadow);
            #if defined(ENDFIELD_RECOVERED_SOURCE_ENERGY_CORE)
                half3 color = recoveredDiffuseColor;
                color += (half3)(
                    sourceSkinDirectSpecular + sourceSkinHighlight);
            #else
            half3 color = lerp(
                fallbackDiffuse * (fallbackAmbient + fallbackDirect),
                recoveredDiffuseColor,
                compatibilityWeight);
            half heavyShadow = saturate(
                _CharacterHeavyShadow * _CharacterHeavyShadowInt *
                (1.0h - shadowAttenuation));
            half backFaceFade = smoothstep(
                -max(_CharacterHeavyShadowBackFaceFadeRange, 0.001h),
                max(_CharacterHeavyShadowBackFaceFadeRange, 0.001h),
                nDotV);
            heavyShadow *= lerp(1.0h, backFaceFade, saturate(_CharacterHeavyShadowBackFaceFade));
            color = lerp(
                color,
                color * _CharacterHeavyShadowColor.rgb,
                heavyShadow);

            half smoothnessPower = exp2(3.0h + _Smoothness * 8.0h);
            half directSpecular = pow(nDotH, smoothnessPower) * _Specular * litAmount;
            half4 specRamp = tex2D(_SpecRampMap, half2(saturate(directSpecular), _Smoothness));
            half3 specular = lerp(
                lerp(half3(0.028h,0.025h,0.024h), baseSample.rgb, _Metallic) * directSpecular,
                specRamp.rgb * specRamp.a * _Specular * litAmount,
                saturate(_UseSpecRampMap));

            if (_UseSDFLightmap > 0.5h && _SDFSpecular > 0.5h)
            {
                half faceSpec = smoothstep(
                    saturate(0.6h + _SDFSpecularOffset),
                    saturate(0.85h + _SDFSpecularOffset),
                    nDotH + _SDFSpecularSideOffset * tangentWS.x);
                specular += faceSpec * _SDFSpecularScale * sdfMask.r * litAmount;
            }
            color += specular * mainLightColor * EndfieldHGRPSpecularMultiplier();
            color += EndfieldHGOperatorAdditionalLighting(
                i.worldPos, normalWS, viewWS, baseSample.rgb,
                _Metallic, _Smoothness, _Specular);

            half2 lightXZ = normalize(lightWS.xz + half2(1e-4h, 1e-4h));
            half2 cameraXZ = normalize(cameraForwardWS.xz + half2(1e-4h, 1e-4h));
            half cameraLightFacing = saturate(-dot(lightXZ, cameraXZ)) *
                (1.0h - _CharacterParams12.x * compatibilityWeight);
            half wrapNdotL = saturate(0.5h + dot(normalWS.xz, lightXZ) -
                0.5h * dot(normalWS.xz, lightXZ) * dot(normalWS.xz, lightXZ));
            half edgeFactor = saturate((-abs(dot(viewWS, normalWS)) + 0.4h) * 5.0h);
            edgeFactor = edgeFactor * edgeFactor * (3.0h - 2.0h * edgeFactor);
            half darkAlbedoGate = saturate((0.1h - EndfieldLuma(diffuseAlbedo)) * 16.666h);
            darkAlbedoGate = darkAlbedoGate * darkAlbedoGate;
            color += darkAlbedoGate * baseSample.a * edgeFactor *
                cameraLightFacing * wrapNdotL * mainLightColor *
                max(diffuseAlbedo, 0.15h) * _SubsurfaceAmount *
                saturate(_Subsurface);

            half rim = EndfieldFresnel(normalWS, viewWS, _SDFRimPower);
            rim = saturate((rim + _SDFRimOffset) *
                           min(_SDFRimFalloff, _SDFLightmapRimFalloff));
            half rimMask = lerp(1.0h, 1.0h - sdfMask.g * _FaceRimOffScale,
                                saturate(_UseSDFLightmap));
            rimMask *= 1.0h - saturate(_SkinRimOff * _SkinRimOffScale);
            color += rim * rimMask * _SDFRimScale * _SDFRimCameraFade *
                     _SDFRimColor.rgb * baseSample.rgb;
            color = EndfieldHGRPApplyFaceRim(color, baseSample.rgb, normalWS);

            if (_EndfieldRecoveredFaceHighlightSemantics > 0.5)
            {
                // Original CharacterNPR_Skin semantics: _HighlightMapVector.xy
                // are view-dependent UV offsets, not an RGBA intensity.  The
                // active Wulfa/Zhuangfy face materials serialize w=0, so the
                // compatibility fallback below otherwise suppresses this map
                // completely.  Keep this path opt-in until both actors have
                // been measured against their reference views.
                half3 objectRightWS = normalize(float3(
                    unity_ObjectToWorld._m00,
                    unity_ObjectToWorld._m10,
                    unity_ObjectToWorld._m20));
                half3 objectUpWS = normalize(float3(
                    unity_ObjectToWorld._m01,
                    unity_ObjectToWorld._m11,
                    unity_ObjectToWorld._m21));
                half2 highlightUv = uv + half2(
                    dot(viewWS, objectRightWS) * _HighlightMapVector.x,
                    dot(viewWS, objectUpWS) * _HighlightMapVector.y);
                half3 recoveredHighlight = _HighlightMap.Sample(
                    endfield_point_mirroronce_sampler,
                    highlightUv).rgb;
                half recoveredAmbientDiffuseIntensity =
                    (minShadow * (1.0h - _CharacterParams0.z) + _CharacterParams0.z) *
                    (minShadow * 0.5h + 0.5h);
                color += recoveredHighlight * recoveredAmbientDiffuseIntensity *
                         fullDiffuse * saturate(_FaceHighlightMap);
            }
            else
            {
                half4 highlight = _HighlightMap.Sample(
                    endfield_point_mirroronce_sampler,
                    uv);
                color += highlight.rgb * highlight.a * _HighlightMapVector.rgb *
                         _HighlightMapVector.a * saturate(_FaceHighlightMap);
            }
            #endif

            #if defined(ENDFIELD_RECOVERED_SOURCE_ENERGY_CORE)
                // Original ordering: extrapolate high-luma chroma after the
                // directional diffuse/GGX/Highlight group, before emission,
                // punctual lights, fog, and final pre-exposure division.
                float sourceSkinOutputLuminance =
                    EndfieldHGRPRecoveredLuma((float3)color);
                float sourceSkinChromaAmount = clamp(
                    sourceSkinOutputLuminance - 0.5,
                    0.0,
                    0.5);
                float sourceSkinChromaFactor =
                    sourceSkinChromaAmount * sourceSkinChromaAmount + 1.0;
                color = (half3)(
                    ((float3)color - sourceSkinOutputLuminance) *
                        sourceSkinChromaFactor +
                    sourceSkinOutputLuminance);
            #endif

            half3 emission = tex2D(_EmissionMap, uv).rgb *
                             _EmissionColor.rgb * _EmissionBrightness;
            color += emission * saturate(_UseEmission);
            #if defined(ENDFIELD_RECOVERED_SOURCE_ENERGY_CORE)
                // Face mode 2 retains the prior exact opaque, zero-metal,
                // no-bump/no-weather route. Body mode 5 is reachable only
                // through the exact manifest identity selector above and uses
                // its distinct decompiled type-3 rim equation in the helper.
                // The later `_2870` body directional-rim group is exact zero
                // for both selected overview rigs: CP8.rgb is zero because
                // charAutoRimEnable=false, while the subsurface term is gated
                // by (1-CP12.x) and both modifiers override main-light range
                // bias (CP12.x=1). General nonzero `_2870` behavior remains
                // deliberately deferred rather than guessed.
                bool sourceExactFaceForwardVariant =
                    _UseSDFLightmap > 0.5h &&
                    abs((float)_Metallic) < 1e-6 &&
                    _UseBumpMap < 0.5h &&
                    _CharacterParams10.x < 0.5;
                if (sourceExactFaceForwardVariant ||
                    sourceExactBodyForwardVariant)
                {
                    color = (half3)EndfieldHGApplyRecoveredClusteredNprLights(
                        (float3)color,
                        (float3)i.worldPos,
                        (float4)i.pos,
                        (float3)faceGeometryNormal,
                        sourceExactBodyForwardVariant
                            ? (float3)normalWS
                            : skinFaceDiffuseNormal,
                        (float3)normalWS,
                        (float3)viewWS,
                        (float3)cameraForwardWS,
                        sourceSkinDiffuseAlbedo,
                        sourceSkinNprDiffuse,
                        sourceSkinAngularNormal,
                        objectCameraForwardXZ,
                        sourceExactBodyForwardVariant
                            ? 0.0
                            : (float)sdfMask.a,
                        sourceSkinF0,
                        1.0 - (float)_Smoothness,
                        1.0,
                        sourceExactBodyForwardVariant ? 5.0 : 2.0,
                        _SpecRampMap,
                        float3(0.0, 1.0, 0.0),
                        0.0,
                        0.0,
                        0.0,
                        0.0);
                }
            #endif
            #if defined(ENDFIELD_RECOVERED_SOURCE_ENERGY_CORE)
                half preExposureDivisor = max(
                    _ExposureParams.x,
                    1e-4h);
                return half4(
                    max(color / preExposureDivisor, 0.0h),
                    1.0h);
            #else
                half preExposureDivisor = lerp(
                    1.0h,
                    max(_ExposureParams.x, 1e-4h),
                    compatibilityWeight);
                return half4(
                    max(color / preExposureDivisor, 0.0h),
                    baseSample.a);
            #endif
        }

        struct SkinOutlineVaryings
        {
            float4 pos : SV_POSITION;
            float2 uv : TEXCOORD0;
        };

        SkinOutlineVaryings SkinOutlineVert(SkinAppData v)
        {
            SkinOutlineVaryings o;
            float2 uv = TRANSFORM_TEX(v.uv, _BaseMap);
            float useMask = saturate(max(_EnableOutlineMask, _UseOutlineMask));
            float mask = lerp(1.0, tex2Dlod(_OutlineMask, float4(uv, 0, 0)).r, useMask);
            float width = EndfieldHGRPCharacterOutlineWidth(
                _OutlineWidth * _RecoveredOutlineScale * mask * saturate(_EnableOutline));
            float4 clipPos = UnityObjectToClipPos(v.vertex + float4(v.normal * width, 0));
            clipPos.z += _OutlineOffsetZ * _RecoveredOutlineZScale * clipPos.w;
            o.pos = clipPos;
            o.uv = uv;
            return o;
        }

        half4 SkinOutlineFrag(SkinOutlineVaryings i) : SV_Target
        {
            clip(min(_EnableOutline, EndfieldHGRPCharacterOutlineEnable()) - 0.5h);
            half4 baseSample = tex2D(_BaseMap, i.uv) * _BaseColor;
            clip(EndfieldCutout(max(_EnableAlphaTest, _AlphaClip), baseSample.a, _AlphaClipThreshold));
            half3 outline = EndfieldSaturation(baseSample.rgb, _OutlineColorSaturation) *
                            _OutlineColorBrightness * _OutlineColor.rgb;
            outline = EndfieldHGRPCharacterOutlineColor(outline);
            outline = EndfieldHGRPPreExposeCharacterColor(outline);
            return half4(outline, baseSample.a);
        }

        struct SkinCameraDepthVaryings
        {
            float4 pos : SV_POSITION;
            float2 uv : TEXCOORD0;
        };

        SkinCameraDepthVaryings SkinCameraDepthVert(appdata_base v)
        {
            SkinCameraDepthVaryings o;
            o.pos = UnityObjectToClipPos(v.vertex);
            o.uv = TRANSFORM_TEX(v.texcoord, _BaseMap);
            return o;
        }

        half4 SkinCameraDepthFrag(SkinCameraDepthVaryings i) : SV_Target
        {
            half alpha = tex2D(_BaseMap, i.uv).a * _BaseColor.a;
            clip(EndfieldCutout(max(_EnableAlphaTest, _AlphaClip), alpha, _AlphaClipThreshold));
            return half4(i.pos.z, i.pos.z, i.pos.z, 1.0h);
        }

        struct SkinShadowVaryings
        {
            V2F_SHADOW_CASTER;
            float2 uv : TEXCOORD1;
        };

        SkinShadowVaryings SkinShadowVert(appdata_base v)
        {
            SkinShadowVaryings o;
            TRANSFER_SHADOW_CASTER_NORMALOFFSET(o)
            #if defined(ENDFIELD_RECOVERED_CHARACTER_SHADOW_PASS_VP)
                o.pos = EndfieldRecoveredCharacterShadowClipPosition(v.vertex);
            #endif
            o.uv = TRANSFORM_TEX(v.texcoord, _BaseMap);
            return o;
        }

        float4 SkinShadowFrag(SkinShadowVaryings i) : SV_Target
        {
            half alpha = tex2D(_BaseMap, i.uv).a * _BaseColor.a;
            clip(EndfieldCutout(max(_EnableAlphaTest, _AlphaClip), alpha, _AlphaClipThreshold));
            SHADOW_CASTER_FRAGMENT(i)
        }

        EndfieldRecoveredPreGBufferOutput SkinRecoveredPreGBufferDiagnosticFrag(
            SkinVaryings i,
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

            normalWS *= ENDFIELD_RECOVERED_FACE_IS_FRONT(facing)
                ? 1.0h
                : (-1.0h + 2.0h * _BackFaceNormalFlip);
            return ENDFIELD_RECOVERED_MAKE_PREGBUFFER_OUTPUT(
                normalWS,
                0.4,
                baseSample,
                endfieldSameOwnerNormalTS,
                i.currentClipXYW,
                i.previousClipXYW);
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
                // The shipped Skin PreGBuffer pass uses a fixed 36 ref.
                Ref 36
                Comp Always
                Pass Replace
            }

            CGPROGRAM
            #pragma target 5.0
            #pragma vertex SkinVert
            #pragma fragment SkinRecoveredPreGBufferDiagnosticFrag
            #pragma multi_compile __ ENDFIELD_RECOVERED_SAME_OWNER_AUDIT ENDFIELD_RECOVERED_CANONICAL_FIVE_MRT
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
                Ref [_StencilRefOption]
                ReadMask 20
                WriteMask 20
                Comp Always
                Pass Replace
            }

            CGPROGRAM
            #pragma target 5.0
            #pragma vertex SkinVert
            #pragma fragment SkinFrag
            #pragma multi_compile_fwdbase
            #pragma multi_compile __ ENDFIELD_RECOVERED_SOURCE_ENERGY_CORE
            #pragma multi_compile __ ENDFIELD_RECOVERED_SKIN_SCREEN_SHADOW_MASK_RG
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
            #pragma vertex SkinOutlineVert
            #pragma fragment SkinOutlineFrag
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
            #pragma vertex SkinCameraDepthVert
            #pragma fragment SkinCameraDepthFrag
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
            #pragma vertex SkinShadowVert
            #pragma fragment SkinShadowFrag
            #pragma multi_compile_shadowcaster
            #pragma multi_compile __ ENDFIELD_RECOVERED_CHARACTER_SHADOW_PASS_VP
            ENDCG
        }
    }

    Fallback Off
}
