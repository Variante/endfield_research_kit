Shader "Endfield/Recovered/CharacterHair"
{
    Properties
    {
        [MainTexture] _BaseMap ("Base Map", 2D) = "white" {}
        [MainColor] _BaseColor ("Base Color", Color) = (1,1,1,1)
        [HideInInspector] _MainTex ("Legacy Base Map", 2D) = "white" {}
        [HideInInspector] _Color ("Legacy Base Color", Color) = (1,1,1,1)
        [HideInInspector] [PerRendererData] _EndfieldRecoveredForwardLogicalDrawId ("Diagnostic Forward Logical Draw ID", Integer) = 0
        [HideInInspector] [PerRendererData] _EndfieldRecoveredForwardRenderQueue ("Diagnostic Forward Render Queue", Integer) = 0
        _HairBaseTintColor ("Hair Base Tint", Color) = (1,1,1,1)
        _HairAddTintColor ("Hair Additive Tint", Color) = (1,1,1,1)

        _BumpMap ("Packed Normal (R*A, G)", 2D) = "bump" {}
        _UseBumpMap ("Use Bump Map", Float) = 0
        _BumpScale ("Bump Scale", Range(0,2)) = 1
        _SplitNormalMap ("Split Normal (RG diffuse, BA specular)", 2D) = "gray" {}
        _UseSpecBumpMap ("Use Split Normal Map", Float) = 0
        _SpecBumpScale ("Specular Normal Scale", Range(0,2)) = 1

        _MetallicGlossMap ("RGBA: Metal, Spec, Shadow, Smooth", 2D) = "white" {}
        _UseMetallicGlossMap ("Use Packed Map", Float) = 0
        _Metallic ("Metallic", Range(0,1)) = 0
        _Specular ("Specular", Range(0,2)) = 1
        _Smoothness ("Smoothness", Range(0,1)) = 1

        _DiffRampMap ("Diffuse Ramp", 2D) = "white" {}
        _UseDiffRampMap ("Use Diffuse Ramp", Float) = 0
        _SpecRampMap ("Specular Ramp", 2D) = "white" {}
        _UseSpecRampMap ("Use Specular Ramp", Float) = 0
        _ShadowLutTex ("Flattened 32x32x32 Hair LUT", 2D) = "white" {}
        _UseShadowLutTex ("Use Shadow LUT", Float) = 0
        _ShadowColorBrightness ("Shadow Brightness", Float) = 0.58
        _ShadowColorSaturation ("Shadow Saturation", Float) = 1.3

        _Anisotropy ("Use Hair Anisotropy", Float) = 1
        _AnisotropyValue ("Anisotropy Value (Strand 1)", Range(0,1)) = 0.7
        _AnisotropyValue2 ("Anisotropy Value (Strand 2)", Range(0,1)) = 0.712
        _AnisotropyRange2 ("Anisotropy Range (Strand 2)", Range(-1,1)) = 0.8
        _AnisotropyIntensity ("Anisotropy Intensity", Float) = 2
        _AnisotropyEdgeFade ("Anisotropy Edge Fade", Float) = 6
        _AnisotropyDirX ("Anisotropy Direction X", Range(-1,1)) = 0
        [HDR] _AnisotropyColor2 ("Anisotropy Color (Strand 2)", Color) = (1,0.83,0.54,1)
        _StrokeMap ("Stroke Map (R: anisotropy offset)", 2D) = "gray" {}
        _StrokeOn ("Use Stroke Map", Float) = 0
        _StrokeScale ("Stroke Scale", Float) = 0

        _SpecularLine ("Specular Line", Float) = 1
        _LineMap ("Specular Line Map", 2D) = "white" {}
        _UseLineMap ("Use Line Map", Float) = 0
        _LineAmount ("Procedural Line Amount", Float) = 300
        _LineValue ("Line Shift", Range(0,1)) = 0.7
        _LineRange ("Line Range", Range(-1,1)) = 0.9
        _LineIntensity ("Line Intensity", Range(0,1)) = 0.35
        _LineSaturation ("Line Saturation", Range(0,1)) = 0.5

        _HairBrowMask ("Hair/Brow Stencil Mask", 2D) = "white" {}
        _HairBrowMaskThreshold ("Hair/Brow Mask Threshold", Range(0,1)) = 0.5
        _DrawUnderBrow ("Draw Under Brow", Float) = 1
        _HairStencilRef ("Hair Stencil Ref", Float) = 36

        _EmissionMap ("Emission Map", 2D) = "black" {}
        _UseEmission ("Use Emission", Float) = 0
        [HDR] _EmissionColor ("Emission Color", Color) = (0,0,0,0)
        _EmissionBrightness ("Emission Brightness", Float) = 1

        _OutlineMask ("Outline Mask", 2D) = "white" {}
        _EnableOutlineMask ("Use Outline Mask", Float) = 0
        _EnableOutline ("Enable Outline", Float) = 1
        _OutlineWidth ("Outline Width", Float) = 0.6
        _OutlineOffsetZ ("Outline Z Offset", Float) = 0
        _OutlineAverageNormal ("Use Packed Average Outline Normal", Float) = 1
        _OutlineColorBrightness ("Outline Brightness", Float) = 0.28
        _OutlineColorSaturation ("Outline Saturation", Float) = 1.15
        _OutlineColor ("Outline Tint", Color) = (1,1,1,1)

        _EnableAlphaTest ("Enable Alpha Test", Float) = 0
        [HideInInspector] _AlphaClip ("Alpha Clip Alias", Float) = 0
        [HideInInspector] _AlphaPremultiply ("Alpha Premultiply", Float) = 0
        _AlphaClipThreshold ("Alpha Clip Threshold", Range(0,1)) = 0.5
        [Enum(UnityEngine.Rendering.CullMode)] _Cull ("Cull", Float) = 2
        [Enum(On,0,Off,1)] _BackFaceNormalFlip ("Back Face Normal Flip", Float) = 0
        [Enum(UnityEngine.Rendering.BlendMode)] _SrcBlend ("Source Blend", Float) = 1
        [Enum(UnityEngine.Rendering.BlendMode)] _DstBlend ("Destination Blend", Float) = 0
        [Enum(Off,0,On,1)] _ZWrite ("Z Write", Float) = 1
        [Enum(UnityEngine.Rendering.CompareFunction)] _ZTest ("Z Test", Float) = 4
        [HideInInspector] _RecoveredSourceZTest ("Original Source Z Test", Float) = 4
        [HideInInspector] _OriginalHGRPProfile ("Original HGRP Profile", Float) = 1
        [HideInInspector] _DisableRainEffectOnMaterial ("Disable Rain Effect", Float) = 0
        [HideInInspector] _EndfieldRecoveredCharacterPerDraw2 ("Recovered Per Draw 2", Vector) = (0,0,0,0)

        _RecoveredBandSoftness ("Recovered Band Softness", Range(0.001,0.5)) = 0.065
        _RecoveredAmbientStrength ("Recovered Ambient Strength", Range(0,2)) = 0.68
        _RecoveredDirectStrength ("Recovered Direct Strength", Range(0,2)) = 1
        _RecoveredOutlineScale ("Recovered Outline Scale", Float) = 0.0035
        _RecoveredOutlineZScale ("Recovered Outline Z Scale", Float) = 0.00001
    }

    SubShader
    {
        Tags { "RenderType"="TransparentCutout" "Queue"="AlphaTest" }
        LOD 425

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
        sampler2D _SplitNormalMap;
        sampler2D _MetallicGlossMap;
        sampler2D _DiffRampMap;
        sampler2D _SpecRampMap;
        sampler2D _ShadowLutTex;
        sampler2D _StrokeMap;
        float4 _StrokeMap_ST;
        sampler2D _LineMap;
        float4 _LineMap_ST;
        sampler2D _HairBrowMask;
        sampler2D _EmissionMap;
        sampler2D _OutlineMask;
        float4 _OutlineMask_ST;

        half4 _BaseColor;
        half4 _HairBaseTintColor;
        half4 _HairAddTintColor;
        half _UseBumpMap;
        half _BumpScale;
        half _UseSpecBumpMap;
        half _SpecBumpScale;
        half _UseMetallicGlossMap;
        half _Metallic;
        half _Specular;
        half _Smoothness;
        half _UseDiffRampMap;
        half _UseSpecRampMap;
        half _UseShadowLutTex;
        half _ShadowColorBrightness;
        half _ShadowColorSaturation;
        half _Anisotropy;
        half _AnisotropyValue;
        half _AnisotropyValue2;
        half _AnisotropyRange2;
        half _AnisotropyIntensity;
        half _AnisotropyEdgeFade;
        half _AnisotropyDirX;
        half4 _AnisotropyColor2;
        half _StrokeOn;
        half _StrokeScale;
        half _SpecularLine;
        half _UseLineMap;
        half _LineAmount;
        half _LineValue;
        half _LineRange;
        half _LineIntensity;
        half _LineSaturation;
        half _HairBrowMaskThreshold;
        half _DrawUnderBrow;
        half _UseEmission;
        half4 _EmissionColor;
        half _EmissionBrightness;
        half _EnableOutlineMask;
        half _EnableOutline;
        half _OutlineWidth;
        half _OutlineOffsetZ;
        half _OutlineAverageNormal;
        half _OutlineColorBrightness;
        half _OutlineColorSaturation;
        half4 _OutlineColor;
        half _EnableAlphaTest;
        half _AlphaClip;
        half _AlphaPremultiply;
        half _AlphaClipThreshold;
        half _BackFaceNormalFlip;
        float _DisableRainEffectOnMaterial;
        float4 _EndfieldRecoveredCharacterPerDraw2;
        half _RecoveredBandSoftness;
        half _RecoveredAmbientStrength;
        half _RecoveredDirectStrength;
        half _RecoveredOutlineScale;
        half _RecoveredOutlineZScale;

        struct HairAppData
        {
            float4 vertex : POSITION;
            float3 normal : NORMAL;
            float4 tangent : TANGENT;
            float2 uv : TEXCOORD0;
            float4 outlineNormal : TEXCOORD2;
            float3 positionOld : TEXCOORD4;
        };

        struct HairVaryings
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

        HairVaryings HairVert(HairAppData v)
        {
            HairVaryings o;
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

        half EndfieldHairStrand(half3 normalWS, half3 binormalWS, half3 halfWS, half shift, half exponent)
        {
            half3 shiftedTangent = normalize(normalWS * shift + binormalWS);
            half tangentDotHalf = clamp(dot(shiftedTangent, halfWS), -0.9999h, 0.9999h);
            half sinTheta = max(sqrt(1.0h - tangentDotHalf * tangentDotHalf), 0.0001h);
            return pow(sinTheta, max(exponent, 1.0h));
        }

        half4 HairFrag(
            HairVaryings i,
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
            half4 baseSample = tex2D(_BaseMap, uv) * _BaseColor;
            baseSample.rgb *= _HairBaseTintColor.rgb;
            baseSample.rgb += (_HairAddTintColor.rgb - half3(1,1,1)) * 0.1h;
            half alphaTest = max(_EnableAlphaTest, _AlphaClip);
            clip(EndfieldCutout(alphaTest, baseSample.a, _AlphaClipThreshold));

            half3 geometryNormal = normalize(i.worldNormal);
            half3 tangentWS = normalize(i.worldTangent.xyz);
            half3 binormalWS =
                cross(geometryNormal, tangentWS) * i.worldTangent.w;
            half3 normalWS = geometryNormal;
            half3 specNormalWS = geometryNormal;
            ENDFIELD_RECOVERED_SAME_OWNER_TANGENT_DECLARE(
                endfieldSameOwnerNormalTS);

            if (_UseSpecBumpMap > 0.5h)
            {
                half4 splitNormal = tex2D(_SplitNormalMap, uv);
                half3 normalTS = EndfieldDecodeNormalRG(
                    splitNormal.rg,
                    _BumpScale);
                ENDFIELD_RECOVERED_SAME_OWNER_TANGENT_CAPTURE(
                    endfieldSameOwnerNormalTS,
                    normalTS);
                normalWS = EndfieldTangentToWorld(
                    normalTS,
                    tangentWS, binormalWS, geometryNormal);
                specNormalWS = EndfieldTangentToWorld(
                    EndfieldDecodeNormalRG(splitNormal.ba, _SpecBumpScale),
                    tangentWS, binormalWS, geometryNormal);
            }
            else if (_UseBumpMap > 0.5h)
            {
                half3 normalTS = EndfieldDecodePackedNormal(tex2D(_BumpMap, uv), _BumpScale);
                ENDFIELD_RECOVERED_SAME_OWNER_TANGENT_CAPTURE(
                    endfieldSameOwnerNormalTS,
                    normalTS);
                normalWS = EndfieldTangentToWorld(normalTS, tangentWS, binormalWS, geometryNormal);
                specNormalWS = normalWS;
            }

            // Exact selected Hair ForwardLit contract. Double-sided Wulfa
            // materials sign both the decoded diffuse normal and the geometry
            // normal by the real primitive face. A non-split specular normal
            // aliases that signed diffuse normal; the split BA normal remains
            // unsigned (and Zhuangfy's split-normal materials are front-only).
            half faceSign = ENDFIELD_RECOVERED_FACE_IS_FRONT(facing)
                ? 1.0h
                : (-1.0h + 2.0h * _BackFaceNormalFlip);
            half3 faceGeometryNormal = geometryNormal * faceSign;
            geometryNormal = faceGeometryNormal;
            normalWS *= faceSign;
            if (_UseSpecBumpMap <= 0.5h)
                specNormalWS = normalWS;

            half4 packed = tex2D(_MetallicGlossMap, uv);
            half metallic = lerp(_Metallic, packed.r, saturate(_UseMetallicGlossMap));
            half specularMask = lerp(_Specular, packed.g, saturate(_UseMetallicGlossMap));
            half shadowMask = lerp(1.0h, packed.b, saturate(_UseMetallicGlossMap));
            half smoothness = lerp(_Smoothness, packed.a, saturate(_UseMetallicGlossMap));

            half3 viewWS = normalize(UnityWorldSpaceViewDir(i.worldPos));
            half3 sceneLightWS = normalize(UnityWorldSpaceLightDir(i.worldPos));
            half3 lightWS = EndfieldHGRPCharacterLightDirection(sceneLightWS);
            lightWS = normalize(lightWS + tangentWS * _AnisotropyDirX);
            half3 halfWS = normalize(lightWS + viewWS);
            half nDotL = dot(normalWS, lightWS);
            half nDotV = dot(normalWS, viewWS);
            #if defined(ENDFIELD_RECOVERED_SCREEN_SHADOW_MASK_CONSUMER)
                float2 recoveredScreenShadowMask =
                    EndfieldHGRPLoadRecoveredScreenShadowMask(i.pos.xy);
                // Exact selected Hair screen boundary: use G directly. The
                // screen path replaces, rather than compounds, the atlas solve.
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
                3.0,
                1.0);
            ENDFIELD_WRITE_RECOVERED_SAME_OWNER_AUDIT(
                i.pos.xy,
                normalWS,
                faceGeometryNormal,
                ENDFIELD_RECOVERED_FACE_VALUE(facing),
                ENDFIELD_RECOVERED_SAME_OWNER_PRIMITIVE_VALUE,
                3u,
                1.0,
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
            half diffuseBand = lerp(
                EndfieldDefaultDiffuseBand(nDotL, _RecoveredBandSoftness),
                diffuseRamp.a,
                saturate(_UseDiffRampMap));
            half3 rampTint = lerp(half3(1,1,1), diffuseRamp.rgb, saturate(_UseDiffRampMap));
            half litAmount = saturate(min(diffuseBand, shadowMask) * shadowAttenuation);
            half3 authoredShadowColor = EndfieldShadowColor(
                _ShadowLutTex,
                _UseShadowLutTex,
                baseSample.rgb,
                _ShadowColorBrightness,
                _ShadowColorSaturation);
            half3 shadowColor = authoredShadowColor;
            shadowColor *= EndfieldHGRPCharacterShadowTint(0.0h);
            half3 diffuseColor = lerp(shadowColor, baseSample.rgb * rampTint, litAmount);

            // The source diffuse uses the unmodified character light. The
            // _AnisotropyDirX offset above remains exclusive to today's hair
            // specular path and cannot contaminate audit modes 2-5.
            float diffuseAuditMode = clamp(_EndfieldRecoveredDiffuseAuditMode, 0.0, 6.0);
            #if defined(ENDFIELD_RECOVERED_SOURCE_ENERGY_CORE)
                // The source-energy selector is a single, default-off route
                // through the proven live-shadow diffuse and material energy.
                diffuseAuditMode = 5.0;
            #endif
            half alphaPremultiply = lerp(
                1.0h,
                baseSample.a,
                saturate(_AlphaPremultiply));
            float recoveredDiffuseEnvironmentScale = 1.0;
            float recoveredDarkenedScale = 1.0;
            #if defined(ENDFIELD_RECOVERED_SOURCE_ENERGY_CORE)
                // Exact selected Hair environment carrier. The packed value is
                // an as-float uint ABI: CP10 wins over custom-per-draw index 2.
                float recoveredPackedEnvironment =
                    _EndfieldRecoveredCharacterPerDraw2.x;
                float recoveredWetWorldHeight =
                    _EndfieldRecoveredCharacterPerDraw2.y;
                if (_CharacterParams10.x > 0.5)
                {
                    recoveredPackedEnvironment = _CharacterParams10.y;
                    recoveredWetWorldHeight = _CharacterParams10.w;
                }

                uint recoveredPackedEnvironmentBits =
                    asuint(recoveredPackedEnvironment);
                float4 recoveredEnvironmentLanes = float4(
                    recoveredPackedEnvironmentBits & 255u,
                    (recoveredPackedEnvironmentBits >> 8u) & 255u,
                    (recoveredPackedEnvironmentBits >> 16u) & 255u,
                    (recoveredPackedEnvironmentBits >> 24u) & 255u) *
                    (1.0 / 255.0);
                float recoveredWetHeightMask = smoothstep(
                    -0.2,
                    0.15,
                    recoveredWetWorldHeight - (float)i.worldPos.y);
                float recoveredWetCombined = max(
                    recoveredEnvironmentLanes.z,
                    recoveredWetHeightMask * recoveredEnvironmentLanes.y);
                float recoveredEnvironmentEffect = max(
                    recoveredEnvironmentLanes.x,
                    recoveredWetCombined);
                bool recoveredEnvironmentEffectEnabled =
                    saturate(
                        recoveredEnvironmentLanes.x + recoveredWetCombined) -
                    _DisableRainEffectOnMaterial > 0.01;
                if (recoveredEnvironmentEffectEnabled)
                {
                    recoveredDiffuseEnvironmentScale = lerp(
                        1.0,
                        0.8,
                        recoveredEnvironmentEffect);
                    recoveredDarkenedScale = lerp(
                        1.0,
                        2.0,
                        recoveredEnvironmentEffect);
                }
            #endif
            half3 recoveredDiffuse = half3(0.0h, 0.0h, 0.0h);
            float3 recoveredFullDiffuse = float3(0.0, 0.0, 0.0);
            float3 recoveredNprDiffuse = float3(0.0, 0.0, 0.0);
            float recoveredNprShadow = 0.0;
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
                if (diffuseAuditMode > 3.5)
                {
                    // Selected hair SPIR-V uses packed R only for the strand
                    // basis blend. Its diffuse workflow is fixed dielectric
                    // 0.96, so passing packed R as metallic was incorrect.
                    EndfieldHGRPRecoveredLiveShadowEnergy(
                        baseSample.rgb * recoveredDiffuseEnvironmentScale,
                        authoredShadowColor * recoveredDiffuseEnvironmentScale,
                        0.0,
                        normalWS,
                        _LightColor0.rgb,
                        recoveredRampColor,
                        recoveredRampAlpha,
                        recoveredViewRampAlpha,
                        shadowMask,
                        characterShadowAttenuation,
                        sceneShadowAttenuation,
                        recoveredFullDiffuse,
                        recoveredNprDiffuse,
                        recoveredNprShadow);
                    recoveredDiffuse = recoveredFullDiffuse * recoveredNprDiffuse;
                    recoveredMinShadow = recoveredNprShadow;
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
            }

            half strokeValue = tex2D(_StrokeMap, uv * _StrokeMap_ST.xy + _StrokeMap_ST.zw).r * 2.0h - 1.0h;
            half strokeShift = strokeValue * _StrokeScale * saturate(_StrokeOn);
            half shift1 = strokeShift + _AnisotropyValue * 2.0h - 1.0h;
            half shift2 = strokeShift + _AnisotropyValue2 * 2.0h - 1.0h;
            half strand1 = EndfieldHairStrand(specNormalWS, binormalWS, halfWS, shift1, 200.0h);
            half strand2Exponent = max((1.0h - _AnisotropyRange2) * 200.0h, 1.0h);
            half strand2 = EndfieldHairStrand(specNormalWS, binormalWS, halfWS, shift2, strand2Exponent);

            half edgeDot = saturate(abs(dot(normalWS, viewWS)) + 0.15h);
            half edgeFade = pow(edgeDot, max(_AnisotropyEdgeFade * 0.16h, 0.01h));
            half4 specRamp = tex2D(_SpecRampMap, half2(strand1, edgeFade * edgeFade));
            half3 strand1Color = lerp(
                half3(strand1, strand1, strand1),
                specRamp.rgb * specRamp.a * strand1,
                saturate(_UseSpecRampMap));
            half3 anisotropicSpecular =
                strand1Color * edgeFade * _AnisotropyIntensity * 0.45h +
                strand2 * edgeFade * _AnisotropyColor2.rgb * 0.22h;
            anisotropicSpecular *= specularMask * litAmount * saturate(_Anisotropy);
            anisotropicSpecular *= lerp(half3(0.04h,0.04h,0.04h), baseSample.rgb, metallic);

            half lineShift = _LineValue * 2.0h - 1.0h;
            half lineStrand = EndfieldHairStrand(
                specNormalWS,
                binormalWS,
                halfWS,
                lineShift,
                max((1.0h - _LineRange) * 200.0h, 1.0h));
            half lineMapValue = tex2D(_LineMap, uv * _LineMap_ST.xy + _LineMap_ST.zw).r;
            half proceduralLine = ceil(max(frac(uv.x * _LineAmount) - 0.5h, 0.0h));
            half linePattern = lerp(proceduralLine, 1.0h - lineMapValue, saturate(_UseLineMap));
            half lineBlend = lerp(1.0h, linePattern, _LineIntensity);
            half lineModifier = lerp(1.0h, lineBlend * lineStrand + (1.0h - lineStrand),
                                     saturate(_SpecularLine));

            // Default-off material-response diagnostic recovered from the
            // selected Wulfa/Zhuangfy Vulkan Forward variants. In the source,
            // packed R does not tint the primary lobe as a metalness value:
            // it blends the object-space strand direction toward the authored
            // mesh tangent (including tangent handedness).
            float3 recoveredPunctualPrimaryStrandWS = (float3)specNormalWS;
            float recoveredPunctualEdgeFade = 0.0;
            #if defined(ENDFIELD_RECOVERED_HAIR_RESPONSE) || defined(ENDFIELD_RECOVERED_SOURCE_ENERGY_CORE)
            {
                float3 recoveredObjectColumn0 = float3(
                    unity_ObjectToWorld._m00,
                    unity_ObjectToWorld._m10,
                    unity_ObjectToWorld._m20);
                float3 recoveredObjectColumn1 = float3(
                    unity_ObjectToWorld._m01,
                    unity_ObjectToWorld._m11,
                    unity_ObjectToWorld._m21);
                float3 recoveredObjectColumn2 = float3(
                    unity_ObjectToWorld._m02,
                    unity_ObjectToWorld._m12,
                    unity_ObjectToWorld._m22);

                float3 recoveredAnisotropyDirection = normalize(
                    recoveredObjectColumn0 * _AnisotropyDirX +
                    recoveredObjectColumn1);
                float3 recoveredAuthoredBitangent = cross(
                    (float3)specNormalWS,
                    recoveredAnisotropyDirection);
                float3 recoveredBlendedBitangent = lerp(
                    recoveredAuthoredBitangent,
                    (float3)tangentWS,
                    (float)metallic);

                // The source interpolant carries the authored tangent W
                // directly; active actor transforms have positive determinant.
                float recoveredTangentSign = (float)i.worldTangent.w;
                float recoveredTangentSignScale = lerp(
                    1.0,
                    recoveredTangentSign,
                    (float)metallic);
                float3 recoveredStrandBasis = recoveredTangentSignScale * cross(
                    (float3)specNormalWS,
                    recoveredBlendedBitangent);

                float recoveredViewColumn0 = dot(
                    (float3)viewWS,
                    recoveredObjectColumn0);
                float recoveredViewColumn2 = dot(
                    (float3)viewWS,
                    recoveredObjectColumn2);
                float recoveredNormalColumn0 = dot(
                    (float3)specNormalWS,
                    recoveredObjectColumn0);
                float recoveredNormalColumn2 = dot(
                    (float3)specNormalWS,
                    recoveredObjectColumn2);
                float2 recoveredViewPlane = normalize(float2(
                    recoveredViewColumn0,
                    recoveredViewColumn2));
                float2 recoveredNormalPlane = normalize(float2(
                    recoveredNormalColumn0,
                    recoveredNormalColumn2));
                float recoveredEdgeDot = saturate(dot(
                    recoveredNormalPlane,
                    recoveredViewPlane));
                float recoveredEdgeFade = pow(
                    recoveredEdgeDot,
                    max((float)_AnisotropyEdgeFade, 0.0));
                recoveredPunctualEdgeFade = recoveredEdgeFade;

                // The source builds H from an object-column projection of the
                // unmodified character light. _AnisotropyDirX belongs to the
                // strand basis above, not to the light direction.
                float3 recoveredLightDirection =
                    EndfieldHGRPCharacterLightDirection((float3)sceneLightWS);
                float3 recoveredWorldContribution =
                    recoveredObjectColumn0 * recoveredViewColumn0 +
                    recoveredObjectColumn1 * recoveredLightDirection.y +
                    recoveredObjectColumn2 * recoveredViewColumn2;
                float3 recoveredHalfDirection = normalize(
                    normalize(
                        recoveredLightDirection +
                        recoveredWorldContribution * 2.0) +
                    (float3)viewWS);

                float recoveredShift1 =
                    (float)strokeShift + (float)_AnisotropyValue * 2.0 - 1.0;
                float3 recoveredShiftedStrand1 = normalize(
                    (float3)specNormalWS * recoveredShift1 +
                    recoveredStrandBasis);
                recoveredPunctualPrimaryStrandWS = recoveredShiftedStrand1;
                float recoveredTangentDotHalf1 = dot(
                    recoveredShiftedStrand1,
                    recoveredHalfDirection);
                float recoveredSinTheta1 = max(
                    sqrt(saturate(
                        1.0 -
                        recoveredTangentDotHalf1 * recoveredTangentDotHalf1)),
                    0.0001);
                float recoveredStrand1 = saturate(
                    pow(recoveredSinTheta1, 200.0) * (float)specularMask);
                float recoveredSpecRampV =
                    recoveredTangentDotHalf1 > 0.0
                        ? recoveredEdgeFade * recoveredEdgeFade
                        : 0.0;
                float3 recoveredSpecRamp = tex2Dlod(
                    _SpecRampMap,
                    float4(recoveredStrand1, recoveredSpecRampV, 0.0, 0.0)).rgb;
                float3 recoveredStrand1Spec = recoveredEdgeFade *
                    recoveredStrand1 *
                    lerp(
                        float3(1.0, 1.0, 1.0),
                        recoveredSpecRamp,
                        saturate((float)_UseSpecRampMap));
                float recoveredStrand1Maximum = max(
                    recoveredStrand1Spec.r,
                    max(recoveredStrand1Spec.g, recoveredStrand1Spec.b));

                float recoveredShift2 =
                    (float)strokeShift + (float)_AnisotropyValue2 * 2.0 - 1.0;
                float3 recoveredShiftedStrand2 = normalize(
                    (float3)specNormalWS * recoveredShift2 +
                    recoveredStrandBasis);
                float recoveredTangentDotHalf2 = dot(
                    recoveredShiftedStrand2,
                    recoveredHalfDirection);
                float recoveredSinTheta2 = max(
                    sqrt(saturate(
                        1.0 -
                        recoveredTangentDotHalf2 * recoveredTangentDotHalf2)),
                    0.0001);
                float recoveredStrand2Exponent = floor(
                    max(1.0 - (float)_AnisotropyRange2, 0.0) * 200.0);
                float3 recoveredStrand2Spec =
                    recoveredEdgeFade *
                    pow(recoveredSinTheta2, recoveredStrand2Exponent) *
                    ((float)smoothness * (float3)_AnisotropyColor2.rgb);

                float3 recoveredPrimarySpecular =
                    ((float)specularMask * 0.04) *
                    recoveredStrand1Spec *
                    ((float)_AnisotropyIntensity * 5.0);
                float3 recoveredSecondarySpecular = lerp(
                    recoveredStrand2Spec,
                    float3(0.0, 0.0, 0.0),
                    recoveredStrand1Maximum);
                anisotropicSpecular = (half3)(
                    (recoveredPrimarySpecular + recoveredSecondarySpecular) *
                    recoveredDarkenedScale *
                    saturate((float)_Anisotropy));

                float recoveredLineShift = (float)_LineValue * 2.0 - 1.0;
                float3 recoveredShiftedLineStrand = normalize(
                    (float3)specNormalWS * recoveredLineShift +
                    recoveredStrandBasis);
                float recoveredLineTangentDotHalf = dot(
                    recoveredShiftedLineStrand,
                    recoveredHalfDirection);
                float recoveredLineSinTheta = max(
                    sqrt(saturate(
                        1.0 -
                        recoveredLineTangentDotHalf *
                        recoveredLineTangentDotHalf)),
                    0.0001);
                float recoveredLineExponent = floor(
                    max(1.0 - (float)_LineRange, 0.0) * 200.0);
                float recoveredLinePower = saturate(pow(
                    recoveredLineSinTheta,
                    recoveredLineExponent));
                float recoveredLinePattern = lerp(
                    (float)proceduralLine,
                    1.0 - (float)lineMapValue,
                    (float)_UseLineMap);
                float recoveredLineBlend =
                    recoveredLinePattern * (float)_LineIntensity +
                    (1.0 - (float)_LineIntensity);
                float recoveredLineModifier =
                    (float)specularMask *
                    ((recoveredLineBlend +
                      (1.0 - recoveredLineBlend) *
                      recoveredStrand1Maximum - 1.0) *
                     recoveredLinePower) +
                    1.0;
                lineModifier = (half)lerp(
                    1.0,
                    recoveredLineModifier,
                    saturate((float)_SpecularLine));
            }
            #endif
            // Preserve HGRP_CharacterNPR_Hair_Fix's line-saturation contract.
            // _LineSaturation does not globally desaturate the hair: when the
            // specular-line modifier is neutral (1), the factor resolves to 1.
            half3 lineSaturatedLit = lineModifier * diffuseColor;
            half lineSaturatedLuma = EndfieldLuma(lineSaturatedLit);
            half lineSaturationFactor =
                lineModifier * (1.0h - _LineSaturation) + _LineSaturation;
            diffuseColor = lineSaturationFactor *
                (lineSaturatedLit - half3(lineSaturatedLuma, lineSaturatedLuma, lineSaturatedLuma)) +
                half3(lineSaturatedLuma, lineSaturatedLuma, lineSaturatedLuma);

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
                EndfieldHGRPMainLightMultiplier() * lerp(0.4h, 1.0h, litAmount);
            half3 illumination = environmentIllumination + directIllumination;
            half3 color = diffuseColor * illumination;
            if (diffuseAuditMode > 0.5 && diffuseAuditMode < 1.5)
            {
                half3 auditColor = EndfieldHGRPPreExposeCharacterColor(
                    color * alphaPremultiply);
                return half4(max(auditColor, 0.0h), baseSample.a);
            }
            if ((diffuseAuditMode > 2.5 && diffuseAuditMode < 3.5) ||
                diffuseAuditMode > 4.5)
            {
                // Hair Fix applies the authored specular-line mask after
                // mainLit, but before the anisotropic lobe. Preserve that
                // ordering in candidate-full mode without contaminating the
                // pure mode-2 diffuse audit.
                half3 recoveredMainLit = recoveredDiffuse * alphaPremultiply;
                half3 recoveredLineLit = lineModifier * recoveredMainLit;
                half recoveredLineLuminance = EndfieldLuma(recoveredLineLit);
                half recoveredLineSaturation =
                    lineModifier * (1.0h - _LineSaturation) + _LineSaturation;
                color = recoveredLineSaturation *
                    (recoveredLineLit - recoveredLineLuminance) +
                    recoveredLineLuminance;
            }

            #if defined(ENDFIELD_RECOVERED_SOURCE_ENERGY_CORE)
            {
                // Source-proven Wulfa/Zhuangfy hair material-energy carrier.
                // CP8.rgb=0, CP12.x=1, the absent emission keyword, and the
                // disabled VFX adjustment make those corresponding branches
                // exactly zero. The original SPIR-V also consumes renderer
                // custom-per-draw rain/wet/wet-global/snow state and wet-world
                // height. Those gameplay values are live-only and remain
                // neutral in this static source-energy path.
                float recoveredAmbientDiffuseIntensity =
                    recoveredNprShadow * (1.0 - _CharacterParams0.z) +
                    _CharacterParams0.z;
                float recoveredSpecularAmbientIntensity =
                    recoveredAmbientDiffuseIntensity *
                    (recoveredNprShadow * 0.5 + 0.5);

                float3 recoveredMainLit =
                    (float3)recoveredDiffuse * (float)alphaPremultiply;
                float3 recoveredLineLit =
                    (float)lineModifier * recoveredMainLit;
                float recoveredLineLuminance = EndfieldHGRPRecoveredLuma(
                    recoveredLineLit);
                float recoveredLineSaturation =
                    (float)lineModifier * (1.0 - (float)_LineSaturation) +
                    (float)_LineSaturation;
                float3 recoveredDiffuseContribution =
                    recoveredLineSaturation *
                    (recoveredLineLit - recoveredLineLuminance) +
                    recoveredLineLuminance;

                // Original hair specular is carried by fullDiffuse and the
                // NPR shadow energy. It is not multiplied by main-light RGB.
                float3 recoveredSpecularContribution =
                    recoveredSpecularAmbientIntensity *
                    recoveredFullDiffuse *
                    (float3)anisotropicSpecular *
                    _CharacterParams13.w;
                float3 recoveredCombined =
                    recoveredDiffuseContribution +
                    recoveredSpecularContribution;
                float recoveredCombinedLuminance =
                    EndfieldHGRPRecoveredLuma(recoveredCombined);
                float recoveredDesaturationAmount = clamp(
                    recoveredCombinedLuminance - 0.5,
                    0.0,
                    0.5);
                float recoveredDesaturationFactor =
                    recoveredDesaturationAmount *
                    recoveredDesaturationAmount + 1.0;
                float3 recoveredSourceEnergy =
                    recoveredDesaturationFactor *
                    (recoveredCombined - recoveredCombinedLuminance) +
                    recoveredCombinedLuminance;
                float3 recoveredCameraForwardWS = float3(
                    UNITY_MATRIX_I_V._m02,
                    UNITY_MATRIX_I_V._m12,
                    UNITY_MATRIX_I_V._m22);
                recoveredSourceEnergy =
                    EndfieldHGApplyRecoveredClusteredNprLights(
                        recoveredSourceEnergy,
                        (float3)i.worldPos,
                        (float4)i.pos,
                        (float3)geometryNormal,
                        (float3)normalWS,
                        (float3)specNormalWS,
                        (float3)viewWS,
                        recoveredCameraForwardWS,
                        0.96 * (float3)baseSample.rgb,
                        recoveredNprDiffuse,
                        (float3)normalWS,
                        0.0,
                        0.0,
                        float3(0.0, 0.0, 0.0),
                        1.0 - (float)smoothness,
                        (float)alphaPremultiply,
                        1.0,
                        _SpecRampMap,
                        recoveredPunctualPrimaryStrandWS,
                        recoveredPunctualEdgeFade,
                        (float)specularMask,
                        (float)_AnisotropyIntensity,
                        1.0);
                recoveredSourceEnergy = EndfieldHGRPPreExposeCharacterColor(
                    recoveredSourceEnergy);
                return half4(max((half3)recoveredSourceEnergy, 0.0h), baseSample.a);
            }
            #endif

            color += anisotropicSpecular * mainLightColor * EndfieldHGRPSpecularMultiplier();
            color += EndfieldHGOperatorAdditionalLighting(
                i.worldPos, normalWS, viewWS, baseSample.rgb,
                metallic, smoothness, specularMask);

            half rim = EndfieldFresnel(normalWS, viewWS, 3.5h);
            color += rim * baseSample.rgb * 0.12h * lerp(0.5h, 1.0h, litAmount);
            half3 normalVS = normalize(mul((half3x3)UNITY_MATRIX_V, normalWS));
            color = EndfieldHGRPApplyCharacterRim(color, baseSample.rgb, normalVS);

            half3 emission = tex2D(_EmissionMap, uv).rgb *
                             _EmissionColor.rgb * _EmissionBrightness;
            color += emission * saturate(_UseEmission);
            if ((diffuseAuditMode > 2.5 && diffuseAuditMode < 3.5) ||
                diffuseAuditMode > 4.5)
                color = EndfieldHGRPPreExposeCharacterColor(color);
            return half4(max(color, 0.0h), baseSample.a);
        }

        inline float2 EndfieldHGRPCharacterOutlineClipOffset(
            float3 normalWS, float clipW, float authoredWidth)
        {
            float3 normalVS = mul((float3x3)UNITY_MATRIX_V, normalize(normalWS));
            float2 projectedNormal = float2(
                dot(UNITY_MATRIX_P[0].xyz, normalVS),
                dot(UNITY_MATRIX_P[1].xyz, normalVS));
            projectedNormal *= rsqrt(max(dot(projectedNormal, projectedNormal), 1.17549435e-38));
            float halfFov = max(abs(atan(1.0 / UNITY_MATRIX_P._m11)), 1e-5);
            float widthScale = (0.39269908169872414 / halfFov) * authoredWidth;
            float depthFade = saturate(clipW * halfFov * 4.583662509918213);
            float2 offset = depthFade * widthScale * projectedNormal *
                float2(_ScreenParams.y / _ScreenParams.x, 1.0) * 0.005;
            float minimumScale = min(1.5707963267948966 / halfFov, max(clipW, 0.0));
            float2 minimumOffset = minimumScale * 2.0 / _ScreenParams.xy;
            return sign(offset) * max(abs(offset), minimumOffset);
        }

        inline float3 EndfieldHGRPCharacterOutlineNormal(
            float3 normalOS, float4 tangentOS, float2 packedNormal)
        {
            float3 normal = normalize(normalOS);
            float3 tangent = normalize(tangentOS.xyz);
            float packedZ = sqrt(1.0 - min(dot(packedNormal, packedNormal), 1.0));
            float3 averageNormal = packedZ * normal + packedNormal.x * tangent +
                tangentOS.w * cross(normal, tangent) * packedNormal.y;
            return _OutlineAverageNormal > 0.5 ? averageNormal : normal;
        }

        inline float EndfieldHGRPCharacterOutlineClipZ(
            float4 baseClipPos, float3 viewPosition, float depthOffset)
        {
            float4 shiftedClip = mul(
                UNITY_MATRIX_P,
                float4(viewPosition.xy, viewPosition.z - depthOffset, 1.0));
            return baseClipPos.w * shiftedClip.z / max(abs(shiftedClip.w), 1e-8);
        }

        struct HairOutlineVaryings
        {
            float4 pos : SV_POSITION;
            float2 uv : TEXCOORD0;
            float3 currentClipXYW : TEXCOORD1;
            float3 previousClipXYW : TEXCOORD2;
        };

        HairOutlineVaryings HairOutlineVert(HairAppData v)
        {
            HairOutlineVaryings o;
            float2 uv = TRANSFORM_TEX(v.uv, _BaseMap);
            float2 outlineUv = TRANSFORM_TEX(v.uv, _OutlineMask);
            float2 outlineMask = tex2Dlod(
                _OutlineMask,
                float4(outlineUv, 0, 0)).rg;
            float mask = lerp(1.0, outlineMask.r,
                              saturate(_EnableOutlineMask));
            float width = EndfieldHGRPCharacterOutlineWidth(
                _OutlineWidth * mask * saturate(_EnableOutline));
            float4 baseClipPos = UnityObjectToClipPos(v.vertex);
            float4 clipPos = baseClipPos;
            float3 outlineNormalOS = EndfieldHGRPCharacterOutlineNormal(
                v.normal,
                v.tangent,
                v.outlineNormal.xy);
            float3 normalWS = UnityObjectToWorldNormal(outlineNormalOS);
            clipPos.xy += EndfieldHGRPCharacterOutlineClipOffset(
                normalWS,
                clipPos.w,
                width);
            float depthOffset = 0.1 * _OutlineOffsetZ * lerp(
                1.0,
                outlineMask.g,
                saturate(_EnableOutlineMask));
            clipPos.z = EndfieldHGRPCharacterOutlineClipZ(
                baseClipPos,
                UnityObjectToViewPos(v.vertex),
                depthOffset);
            float4 previousLocalPosition = lerp(
                v.vertex,
                float4(v.positionOld, 1.0),
                step(0.5, unity_MotionVectorsParams.x));
            float4 previousClip = mul(
                UNITY_MATRIX_VP,
                mul(unity_MatrixPreviousM, previousLocalPosition));
            previousClip.xy += clipPos.xy - baseClipPos.xy;
            o.pos = clipPos;
            o.uv = uv;
            o.currentClipXYW = clipPos.xyw;
            o.previousClipXYW = previousClip.xyw;
            return o;
        }

        struct HairOutlineOutput
        {
            half4 color : SV_Target0;
            float4 sceneMV : SV_Target1;
        };

        HairOutlineOutput HairOutlineFrag(HairOutlineVaryings i)
        {
            clip(min(_EnableOutline, EndfieldHGRPCharacterOutlineEnable()) - 0.5h);
            half4 baseSample = tex2D(_BaseMap, i.uv) * _BaseColor;
            clip(EndfieldCutout(max(_EnableAlphaTest, _AlphaClip), baseSample.a, _AlphaClipThreshold));
            HairOutlineOutput output;
            output.color = 0.0h;
            output.sceneMV = EndfieldRecoveredCharacterMotionMrt(
                i.currentClipXYW,
                i.previousClipXYW,
                0.0);
            return output;
        }

        struct HairCameraDepthVaryings
        {
            float4 pos : SV_POSITION;
            float2 uv : TEXCOORD0;
        };

        HairCameraDepthVaryings HairCameraDepthVert(appdata_base v)
        {
            HairCameraDepthVaryings o;
            o.pos = UnityObjectToClipPos(v.vertex);
            o.uv = TRANSFORM_TEX(v.texcoord, _BaseMap);
            return o;
        }

        half4 HairCameraDepthFrag(HairCameraDepthVaryings i) : SV_Target
        {
            half alpha = tex2D(_BaseMap, i.uv).a * _BaseColor.a;
            clip(EndfieldCutout(max(_EnableAlphaTest, _AlphaClip), alpha, _AlphaClipThreshold));
            return half4(i.pos.z, i.pos.z, i.pos.z, 1.0h);
        }

        struct HairShadowVaryings
        {
            V2F_SHADOW_CASTER;
            float2 uv : TEXCOORD1;
        };

        HairShadowVaryings HairShadowVert(appdata_base v)
        {
            HairShadowVaryings o;
            TRANSFER_SHADOW_CASTER_NORMALOFFSET(o)
            #if defined(ENDFIELD_RECOVERED_CHARACTER_SHADOW_PASS_VP)
                o.pos = EndfieldRecoveredCharacterShadowClipPosition(v.vertex);
            #endif
            o.uv = TRANSFORM_TEX(v.texcoord, _BaseMap);
            return o;
        }

        float4 HairShadowFrag(HairShadowVaryings i) : SV_Target
        {
            half alpha = tex2D(_BaseMap, i.uv).a * _BaseColor.a;
            clip(EndfieldCutout(max(_EnableAlphaTest, _AlphaClip), alpha, _AlphaClipThreshold));
            SHADOW_CASTER_FRAGMENT(i)
        }

        EndfieldRecoveredPreGBufferOutput HairRecoveredPreGBufferDiagnosticFrag(
            HairVaryings i,
            ENDFIELD_RECOVERED_FACE_AND_PRIMITIVE_INPUT(facing))
        {
            half alpha = tex2D(_BaseMap, i.uv).a * _BaseColor.a;
            clip(EndfieldCutout(
                max(_EnableAlphaTest, _AlphaClip),
                alpha,
                _AlphaClipThreshold));
            if (_DrawUnderBrow > 0.5h)
            {
                half browMask = tex2D(_HairBrowMask, i.uv).x;
                clip(browMask - _HairBrowMaskThreshold);
            }

            half3 geometryNormal = normalize(i.worldNormal);
            half3 tangentWS = normalize(i.worldTangent.xyz);
            half3 binormalWS =
                cross(geometryNormal, tangentWS) * i.worldTangent.w;
            half3 normalWS = geometryNormal;
            ENDFIELD_RECOVERED_SAME_OWNER_TANGENT_DECLARE(
                endfieldSameOwnerNormalTS);
            if (_UseSpecBumpMap > 0.5h)
            {
                half4 splitNormal = tex2D(_SplitNormalMap, i.uv);
                half3 normalTS = EndfieldDecodeNormalRG(
                    splitNormal.rg,
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
            else if (_UseBumpMap > 0.5h)
            {
                // Exact _NORMALMAP-only Hair02 contract: X is packed in R*A
                // while Y is stored in G. Split-normal variants stay above.
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

            half faceSign = ENDFIELD_RECOVERED_FACE_IS_FRONT(facing)
                ? 1.0h
                : (-1.0h + 2.0h * _BackFaceNormalFlip);
            normalWS *= faceSign;
            return ENDFIELD_RECOVERED_MAKE_PREGBUFFER_OUTPUT(
                normalWS,
                1.0,
                tex2D(_BaseMap, i.uv) * _BaseColor,
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
                Ref [_HairStencilRef]
                ReadMask 16
                WriteMask 239
                Comp GEqual
                Pass Replace
            }

            CGPROGRAM
            #pragma target 5.0
            #pragma vertex HairVert
            #pragma fragment HairRecoveredPreGBufferDiagnosticFrag
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
                Ref [_HairStencilRef]
                ReadMask 20
                WriteMask 20
                Comp Always
                Pass Replace
            }

            CGPROGRAM
            #pragma target 5.0
            #pragma vertex HairVert
            #pragma fragment HairFrag
            #pragma multi_compile_fwdbase
            #pragma multi_compile __ ENDFIELD_RECOVERED_HAIR_RESPONSE
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
            ZWrite Off
            ZTest Less
            Blend 0 Zero Zero, Zero Zero
            Blend 1 One Zero
            Stencil
            {
                Ref 16
                ReadMask 16
                Comp NotEqual
                Pass Keep
            }

            CGPROGRAM
            #pragma target 5.0
            #pragma vertex HairOutlineVert
            #pragma fragment HairOutlineFrag
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
            #pragma vertex HairCameraDepthVert
            #pragma fragment HairCameraDepthFrag
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
            #pragma vertex HairShadowVert
            #pragma fragment HairShadowFrag
            #pragma multi_compile_shadowcaster
            #pragma multi_compile __ ENDFIELD_RECOVERED_CHARACTER_SHADOW_PASS_VP
            ENDCG
        }
    }

    Fallback Off
}
