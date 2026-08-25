Shader "Endfield/Recovered/CharacterEye"
{
    Properties
    {
        [MainTexture] _BaseMap ("Base Map", 2D) = "white" {}
        [MainColor] _BaseColor ("Base Color", Color) = (1,1,1,1)
        [HideInInspector] _MainTex ("Legacy Base Map", 2D) = "white" {}
        [HideInInspector] _Color ("Legacy Base Color", Color) = (1,1,1,1)
        [HideInInspector] [PerRendererData] _EndfieldRecoveredForwardLogicalDrawId ("Diagnostic Forward Logical Draw ID", Integer) = 0
        [HideInInspector] [PerRendererData] _EndfieldRecoveredForwardRenderQueue ("Diagnostic Forward Render Queue", Integer) = 0
        _EyeTintColor ("Eye Tint", Color) = (1,1,1,1)

        _DiffRampMap ("Diffuse Ramp", 2D) = "white" {}
        _UseDiffRampMap ("Use Diffuse Ramp", Float) = 0
        _ShadowLutTex ("Flattened 32x32x32 Shadow LUT", 2D) = "white" {}
        _UseShadowLutTex ("Use Shadow LUT", Float) = 0
        _ShadowColorBrightness ("Shadow Brightness", Float) = 0.65
        _ShadowColorSaturation ("Shadow Saturation", Float) = 1.2

        _MatcapTex ("Iris Matcap", 2D) = "white" {}
        _UseMatcap ("Use Iris Matcap", Float) = 0
        _MatcapNormalScale ("Matcap Normal Scale", Range(0,1.5)) = 1
        [HDR] _MatcapColor ("Matcap Color", Color) = (1,1,1,1)
        _ParallaxScale ("Iris Parallax Scale", Range(0,0.15)) = 0.03
        _EyeHighLight ("Eye Highlight", Float) = 0
        [HDR] _EyeHighLightColor ("Eye Highlight Color", Color) = (2,2,2,1)
        [HDR] _EyeScatteringColor ("Eye Scattering Color", Color) = (1,1,1,1)
        [HideInInspector] _AlphaPremultiply ("Original Alpha Premultiply", Float) = 0

        _Metallic ("Metallic", Range(0,1)) = 0
        _Specular ("Specular", Range(0,1)) = 0
        _Smoothness ("Smoothness", Range(0,1)) = 0

        _UseEmission ("Use Emission", Float) = 0
        _EmissionMap ("Emission Map", 2D) = "black" {}
        [HDR] _EmissionColor ("Emission Color", Color) = (0,0,0,0)
        _EmissionBrightness ("Emission Brightness", Float) = 1

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
        _PreZStencilRefOption ("Eye/Brow Stencil Ref", Float) = 52
        [HideInInspector] _OriginalHGRPProfile ("Original HGRP Profile", Float) = 1
        [HideInInspector] _RecoveredEyeForwardVariantClass ("Pinned Eye Forward Variant Class", Float) = 0

        _RecoveredBandSoftness ("Recovered Band Softness", Range(0.001,0.5)) = 0.06
        _RecoveredAmbientStrength ("Recovered Ambient Strength", Range(0,2)) = 0.76
        _RecoveredDirectStrength ("Recovered Direct Strength", Range(0,2)) = 0.9
        _RecoveredEyeDirectStrength ("Recovered Eye Direct Strength", Range(0,1)) = 0.18
    }

    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry+2" }
        LOD 350

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
        sampler2D _DiffRampMap;
        sampler2D _ShadowLutTex;
        sampler2D _MatcapTex;
        sampler2D _EmissionMap;

        half4 _BaseColor;
        half4 _EyeTintColor;
        half _UseDiffRampMap;
        half _UseShadowLutTex;
        half _ShadowColorBrightness;
        half _ShadowColorSaturation;
        half _UseMatcap;
        half _MatcapNormalScale;
        half4 _MatcapColor;
        half _ParallaxScale;
        half _EyeHighLight;
        half4 _EyeHighLightColor;
        half4 _EyeScatteringColor;
        half _AlphaPremultiply;
        half _Metallic;
        half _Specular;
        half _Smoothness;
        half _UseEmission;
        half4 _EmissionColor;
        half _EmissionBrightness;
        half _EnableAlphaTest;
        half _AlphaClip;
        half _AlphaClipThreshold;
        half _BackFaceNormalFlip;
        half _RecoveredEyeForwardVariantClass;
        half _RecoveredBandSoftness;
        half _RecoveredAmbientStrength;
        half _RecoveredDirectStrength;
        half _RecoveredEyeDirectStrength;

        struct EyeAppData
        {
            float4 vertex : POSITION;
            float3 normal : NORMAL;
            float4 tangent : TANGENT;
            float2 uv : TEXCOORD0;
            float3 positionOld : TEXCOORD4;
        };

        struct EyeVaryings
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

        EyeVaryings EyeVert(EyeAppData v)
        {
            EyeVaryings o;
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

        half EndfieldRecoveredEyeVariantIs(half variantClass)
        {
            return 1.0h - step(0.25h, abs(
                _RecoveredEyeForwardVariantClass - variantClass));
        }

        half3 EndfieldRecoveredEyeSourceResponse(
            half3 albedo,
            half baseAlpha,
            half2 sampleUv,
            half3 lightNormal,
            half3 matcapNormal,
            half3 viewWS,
            half3 adjustedLightDirection,
            half directionalShadowAttenuation,
            half outsideIris,
            half insideIris,
            out half3 punctualNprDiffuse)
        {
            // Source-shaped CharacterNPR_Eye ForwardLit core. The selected
            // Wulfa/Zhuangfy/brow SPIR-V variants and serialized material
            // keywords prove the feature topology; the readable Fix shader
            // supplies the same stripped-symbol arithmetic.
            const half nearZeroY = 6.103515625e-05h;

            half3 objectRight = half3(
                unity_ObjectToWorld._m00,
                unity_ObjectToWorld._m10,
                unity_ObjectToWorld._m20);
            half3 objectUp = half3(
                unity_ObjectToWorld._m01,
                unity_ObjectToWorld._m11,
                unity_ObjectToWorld._m21);
            half3 objectForward = half3(
                unity_ObjectToWorld._m02,
                unity_ObjectToWorld._m12,
                unity_ObjectToWorld._m22);
            half3x3 objectToWorld3x3 = half3x3(
                objectRight.x, objectUp.x, objectForward.x,
                objectRight.y, objectUp.y, objectForward.y,
                objectRight.z, objectUp.z, objectForward.z);

            half3 localLight = mul(adjustedLightDirection, objectToWorld3x3);
            localLight *= rsqrt(max(dot(localLight, localLight), 1.175494e-38));
            half3 projectedLight = mul(
                objectToWorld3x3,
                half3(localLight.x, 0.0h, localLight.z));
            projectedLight *= rsqrt(max(dot(projectedLight, projectedLight), 1.175494e-38));

            half3 cameraForwardWS = normalize(half3(
                UNITY_MATRIX_I_V._m02,
                UNITY_MATRIX_I_V._m12,
                UNITY_MATRIX_I_V._m22));
            half rampInput = clamp(
                _CharacterParams11.w * _CharacterParams12.x +
                dot(lightNormal, projectedLight),
                -1.0h,
                1.0h) * 0.5h + 0.5h;
            half4 directRampSample = tex2Dlod(
                _DiffRampMap,
                half4(rampInput, 0.5h, 0.0h, 0.0h));
            half4 viewRampSample = tex2Dlod(
                _DiffRampMap,
                half4(saturate(dot(lightNormal, cameraForwardWS) * 0.5h + 0.5h),
                      0.5h, 0.0h, 0.0h));
            half useDiffuseRamp = saturate(_UseDiffRampMap);
            half3 rampColor = lerp(half3(1,1,1), directRampSample.rgb, useDiffuseRamp);
            half rampAlpha = lerp(1.0h, directRampSample.a, useDiffuseRamp);
            half viewRampAlpha = viewRampSample.a * useDiffuseRamp;
            half rampChroma = max(rampColor.r, max(rampColor.g, rampColor.b)) -
                              min(rampColor.r, min(rampColor.g, rampColor.b));

            half3 eyeBlend = half3(1,1,1);
            if (EndfieldRecoveredEyeVariantIs(1.0h) > 0.5h)
            {
                half3 highlightTerm = lerp(
                    insideIris.xxx,
                    _EyeHighLightColor.rgb * outsideIris + insideIris,
                    saturate(_EyeHighLight));
                eyeBlend = highlightTerm *
                    (_EyeScatteringColor.rgb * baseAlpha + (1.0h - baseAlpha));
            }

            half oneMinusReflectivity = (1.0h - _Metallic) * 0.96h;
            half3 diffuseAlbedo = oneMinusReflectivity * albedo;
            half3 shadowColor = oneMinusReflectivity * EndfieldShadowColor(
                _ShadowLutTex,
                EndfieldRecoveredEyeVariantIs(2.0h),
                albedo,
                _ShadowColorBrightness,
                _ShadowColorSaturation);
            half minRampAlpha = min(rampAlpha, 1.0h);
            // The exact Eye raster uses the resolved main shadow as a branch
            // selector, not as one final RGB multiplier. Feed the ungated
            // directional input here: the helper applies directional strength
            // and CharacterParams1.z exactly once.
            half liveShadowSelector = EndfieldHGRPRecoveredLiveShadowSelector(
                directionalShadowAttenuation);

            half3 flatLightNormal = half3(lightNormal.x, nearZeroY, lightNormal.z);
            flatLightNormal *= rsqrt(max(dot(flatLightNormal, flatLightNormal), 1e-8));
            half ambientNdotL =
                saturate(dot(flatLightNormal, _CharacterParams6.xyz) +
                         _CharacterParams7.x) * _CharacterParams7.y +
                _CharacterParams7.z;
            half shadowStrength = minRampAlpha * _CharacterParams1.y;
            half3 shadowedAmbient = ambientNdotL *
                (shadowStrength * (1.0h - _CharacterParams2.rgb) +
                 _CharacterParams2.rgb);

            half exposure =
                (_CharacterParams12.w * (1.0h - _EnvironmentGlobalParams0.x) +
                 _EnvironmentGlobalParams0.x) * _ExposureParams.x;
            half shadowExposure = lerp(
                min(lerp(0.65h, 1.0h, exposure), 1.5h),
                clamp(exposure, 1.25h, 1.75h),
                _CharacterParams1.x);
            half3 directionalCustomColor = lerp(
                _LightColor0.rgb,
                _CharacterParams5.rgb,
                _CharacterParams12.y);
            half3 blendedLightColor = directionalCustomColor * lerp(
                (half)EndfieldHGRPCharacterMainIntensity(),
                1.0h,
                _CharacterParams12.w);
            half lightLuminance = EndfieldLuma(blendedLightColor);
            half3 ambientDirectionalColor = lerp(
                half3(1,1,1),
                directionalCustomColor,
                _CharacterParams12.y);
            half3 shadowFullDiffuse =
                shadowedAmbient * shadowExposure * _CharacterParams0.w;
            half3 litFullDiffuse =
                (shadowedAmbient * clamp(exposure, 0.0h, 1.5h) *
                     ambientDirectionalColor +
                 minRampAlpha * (blendedLightColor - lightLuminance) +
                 lightLuminance) * _CharacterParams0.y;
            half3 fullDiffuse = lerp(
                shadowFullDiffuse,
                litFullDiffuse,
                liveShadowSelector);

            half3 ambientScaled = shadowColor * _CharacterParams0.z;
            half ambientScaledLuminance = EndfieldLuma(ambientScaled * 0.65h);
            half3 desaturatedShadow =
                (ambientScaled * 0.65h - ambientScaledLuminance) * 1.2h +
                ambientScaledLuminance;
            half combinationWeight = saturate(rampAlpha + viewRampAlpha);
            half3 weightedAmbient = lerp(
                desaturatedShadow,
                ambientScaled,
                combinationWeight);
            half3 shadowBlended = lerp(
                weightedAmbient,
                diffuseAlbedo * eyeBlend,
                minRampAlpha);
            half3 rampTinted = shadowBlended *
                (rampColor * rampChroma + (1.0h - rampChroma));
            half luminanceRatio = clamp(
                EndfieldLuma(shadowBlended) /
                max(EndfieldLuma(rampTinted), 0.001h),
                0.0h,
                1.5h);
            half3 rampBranch = rampTinted * luminanceRatio;
            half3 viewBranch = lerp(
                ambientScaled,
                diffuseAlbedo * eyeBlend,
                viewRampAlpha);
            half3 nprDiffuse = lerp(
                viewBranch,
                rampBranch,
                liveShadowSelector);
            punctualNprDiffuse = nprDiffuse;
            half nprShadow = lerp(
                viewRampAlpha,
                minRampAlpha,
                liveShadowSelector);

            half alphaPremultiply = lerp(1.0h, baseAlpha, _AlphaPremultiply);
            half3 matcapContribution = half3(0,0,0);
            if (EndfieldRecoveredEyeVariantIs(1.0h) > 0.5h)
            {
                half matcapIntensity =
                    (nprShadow * (1.0h - _CharacterParams0.z) +
                     _CharacterParams0.z) *
                    (nprShadow * 0.5h + 0.5h);
                half3 viewNormal = mul((half3x3)UNITY_MATRIX_V, matcapNormal);
                half2 matcapUv = normalize(viewNormal).xy * 0.5h + 0.5h;
                half4 matcapSample = tex2D(_MatcapTex, matcapUv);
                half3 matcapColor =
                    matcapSample.rgb * _MatcapColor.a +
                    matcapSample.a * _MatcapColor.rgb;
                matcapContribution = matcapColor * (matcapIntensity * fullDiffuse);
            }

            half3 mainLit =
                nprDiffuse * fullDiffuse * alphaPremultiply +
                matcapContribution;
            half mainLitLuminance = EndfieldLuma(mainLit);
            half desaturationAmount = clamp(mainLitLuminance - 0.5h, 0.0h, 0.5h);
            half desaturationFactor =
                desaturationAmount * desaturationAmount + 1.0h;
            half3 desaturatedMain =
                desaturationFactor * (mainLit - mainLitLuminance) +
                mainLitLuminance;

            half2 adjustedLightXZ = adjustedLightDirection.xz;
            half adjustedLightXZInvLength = rsqrt(max(
                dot(adjustedLightXZ, adjustedLightXZ) + nearZeroY * nearZeroY,
                1e-8));
            half3 normalizedLightXZ = half3(
                adjustedLightDirection.x * adjustedLightXZInvLength,
                nearZeroY * adjustedLightXZInvLength,
                adjustedLightDirection.z * adjustedLightXZInvLength);
            half wrapNdotL = saturate(
                0.5h + dot(normalizedLightXZ, lightNormal) -
                0.5h * dot(normalizedLightXZ, lightNormal) *
                dot(normalizedLightXZ, lightNormal));
            half2 cameraForwardXZ = cameraForwardWS.xz;
            cameraForwardXZ *= rsqrt(max(dot(cameraForwardXZ, cameraForwardXZ), 1e-8));
            half cameraLightDot = -dot(normalizedLightXZ.xz, cameraForwardXZ);
            half cameraLightFacing =
                (1.0h - _CharacterParams12.x) * saturate(cameraLightDot);
            half edgeFactor = saturate(
                (-abs(dot(viewWS, lightNormal)) + 0.4h) * 5.0h);
            edgeFactor = edgeFactor * edgeFactor * (3.0h - 2.0h * edgeFactor);
            half brightnessGate = saturate(
                (0.1h - EndfieldLuma(diffuseAlbedo)) * 16.666h);
            brightnessGate = brightnessGate * brightnessGate *
                (3.0h - 2.0h * brightnessGate);
            half3 subsurfaceSpecular =
                brightnessGate * edgeFactor * cameraLightFacing * wrapNdotL *
                blendedLightColor * max(diffuseAlbedo, 0.15h);

            half3 eyeDirect = half3(0,0,0);
            if (EndfieldRecoveredEyeVariantIs(1.0h) > 0.5h)
            {
                half3 highlightEmission =
                    outsideIris * _EyeHighLightColor.rgb * saturate(_EyeHighLight);
                eyeDirect =
                    (albedo * _CharacterParams13.x +
                     highlightEmission * _CharacterParams13.y +
                     (baseAlpha * _EyeScatteringColor.rgb) * _CharacterParams13.z) *
                    alphaPremultiply;
            }

            return eyeDirect + subsurfaceSpecular + desaturatedMain;
        }

        half4 EyeFrag(
            EyeVaryings i,
            ENDFIELD_RECOVERED_FACE_AND_PRIMITIVE_INPUT(facing)
            #if !(SHADER_TARGET >= 45 && defined(ENDFIELD_RECOVERED_SCREEN_DIRECT_AUDIT))
            , out float4 endfieldCharacterSceneMV : SV_Target1
            #endif
            ) : SV_Target
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

            half2 fractionalUv = frac(i.uv);
            half2 centeredUv = fractionalUv - 0.5h;
            half distanceSquared = dot(centeredUv, centeredUv);
            half outsideIris = step(0.25h, distanceSquared);
            half insideIris = 1.0h - outsideIris;

            half2 sampleUv = i.uv;
            half3 lightNormal = geometryNormal;
            half3 matcapNormal = geometryNormal;
            half selectedIrisVariant = EndfieldRecoveredEyeVariantIs(1.0h);
            half useIrisGeometry = _RecoveredEyeForwardVariantClass > 0.5h
                ? selectedIrisVariant
                : saturate(_UseMatcap);
            if (useIrisGeometry > 0.5h)
            {
                half3 viewTS = half3(dot(tangentWS, viewWS),
                                     dot(binormalWS, viewWS),
                                     dot(geometryNormal, viewWS));
                half viewLength = rsqrt(max(dot(viewTS, viewTS), 0.0001h));
                half parallaxRaw = saturate((distanceSquared - 0.25h) * -5.0h);
                half parallaxSmooth = parallaxRaw * parallaxRaw * (3.0h - 2.0h * parallaxRaw);
                sampleUv.x -= viewLength * viewTS.x * _ParallaxScale * parallaxSmooth;
                sampleUv.y -= viewLength * viewTS.y * _ParallaxScale * 0.25h * parallaxSmooth;

                half2 sphereXY = fractionalUv * 2.0h - 1.0h;
                half sphereZ = sqrt(saturate(1.0h - dot(sphereXY, sphereXY)));
                half scaledX = -sphereXY.x * _MatcapNormalScale;
                half scaledY = -sphereXY.y * _MatcapNormalScale;
                half irisLightingScale = -0.125h * insideIris;
                lightNormal = normalize(
                    tangentWS * (scaledX * irisLightingScale) +
                    binormalWS * (scaledY * irisLightingScale) +
                    geometryNormal * lerp(sphereZ, 1.0h, outsideIris));
                matcapNormal = normalize(
                    tangentWS * scaledX +
                    binormalWS * scaledY +
                    geometryNormal * sphereZ);
            }

            half faceSign = ENDFIELD_RECOVERED_FACE_IS_FRONT(facing)
                ? 1.0h
                : (-1.0h + 2.0h * _BackFaceNormalFlip);
            half3 faceGeometryNormal = geometryNormal * faceSign;

            half4 baseSample = tex2D(_BaseMap, sampleUv) * _BaseColor;
            baseSample.rgb *= _EyeTintColor.rgb;
            clip(EndfieldCutout(max(_EnableAlphaTest, _AlphaClip),
                                baseSample.a,
                                _AlphaClipThreshold));

            half3 lightWS = EndfieldHGRPCharacterLightDirection(
                normalize(UnityWorldSpaceLightDir(i.worldPos)));
            half nDotL = dot(lightNormal, lightWS);
            half nDotV = dot(lightNormal, viewWS);
            #if defined(ENDFIELD_RECOVERED_EYE_SCREEN_SHADOW_MASK_R)
                // Exact current Eye boundary: mandatory integer-pixel Load of
                // retail _ScreenSpaceShadowMask R only. The lab keyword is
                // enabled only by a producer that reports retail scene-R
                // content valid; the neutral attachment diagnostic cannot.
                float sceneShadowAttenuation =
                    EndfieldHGRPLoadScreenSpaceShadowMaskR(i.pos.xy);
                float characterShadowAttenuation = 1.0;
            #elif defined(ENDFIELD_RECOVERED_SCREEN_SHADOW_MASK_CONSUMER)
                float2 recoveredScreenShadowMask =
                    EndfieldHGRPLoadRecoveredScreenShadowMask(i.pos.xy);
                // Exact selected Eye screen modules read R only. Keep the
                // character carrier neutral and never sample/apply G here.
                float sceneShadowAttenuation = recoveredScreenShadowMask.x;
                float characterShadowAttenuation = 1.0;
            #else
                // The current installed pass-0 corpus has no equivalent
                // no-screen-mask Eye member. Keep this compatibility fallback
                // only while the exact scene-R content producer remains open;
                // do not claim it as an original variant.
                half sceneShadowAttenuation =
                    UNITY_SHADOW_ATTENUATION(i, i.worldPos);
                half characterShadowAttenuation = EndfieldHGRPSampleCharacterShadow(
                    EndfieldHGRPCharacterShadowCoord(i.worldPos, faceGeometryNormal),
                    i.pos.xy);
            #endif
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

            #if defined(ENDFIELD_RECOVERED_EYE_RESPONSE)
            if (_RecoveredEyeForwardVariantClass > 0.5h)
            {
                half3 punctualNprDiffuse;
                half3 recoveredEyeColor = EndfieldRecoveredEyeSourceResponse(
                    baseSample.rgb,
                    baseSample.a,
                    sampleUv,
                    lightNormal,
                    matcapNormal,
                    viewWS,
                    lightWS,
                    sceneShadowAttenuation,
                    outsideIris,
                    insideIris,
                    punctualNprDiffuse);
                // The three current playable variants compile without
                // _EMISSION. Exact pass-0 ordering is base response, punctual
                // traversal, then whole-result pre-exposure. Skin/Eye use the
                // same 32x32 XY + linear-Z list as Cloth/Hair; Eye mode keeps
                // Default diffuse and order-sensitive Fog while Rim is zero.
                half3 cameraForwardWS = normalize(half3(
                    UNITY_MATRIX_I_V._m02,
                    UNITY_MATRIX_I_V._m12,
                    UNITY_MATRIX_I_V._m22));
                half punctualAlphaPremultiply = lerp(
                    1.0h,
                    baseSample.a,
                    _AlphaPremultiply);
                recoveredEyeColor = EndfieldHGApplyRecoveredClusteredNprLights(
                    recoveredEyeColor,
                    i.worldPos,
                    i.pos,
                    faceGeometryNormal,
                    lightNormal,
                    lightNormal,
                    viewWS,
                    cameraForwardWS,
                    baseSample.rgb,
                    punctualNprDiffuse,
                    lightNormal,
                    0.0h,
                    0.0h,
                    half3(0,0,0),
                    1.0h,
                    punctualAlphaPremultiply,
                    3.0h,
                    _DiffRampMap,
                    half3(0,0,0),
                    0.0h,
                    0.0h,
                    0.0h,
                    0.0h);
                recoveredEyeColor = EndfieldHGRPPreExposeCharacterColor(
                    recoveredEyeColor);
                // All 57 current playable Eye-family materials are exact
                // opaque members. The selected blobs resolve Target0.a after
                // lighting/fog as (SurfaceType == 1 ? baseAlpha : 1), so the
                // current source-gated classes pin alpha to one.
                return half4(max(recoveredEyeColor, 0.0h), 1.0h);
            }
            #endif

            half4 diffuseRamp = EndfieldRampSample(_DiffRampMap, nDotL, nDotV);
            half diffuseBand = lerp(
                EndfieldDefaultDiffuseBand(nDotL, _RecoveredBandSoftness),
                diffuseRamp.a,
                saturate(_UseDiffRampMap));
            half3 rampTint = lerp(half3(1,1,1), diffuseRamp.rgb, saturate(_UseDiffRampMap));
            half litAmount = saturate(diffuseBand * shadowAttenuation);

            half3 eyeBlend = half3(1,1,1);
            if (_UseMatcap > 0.5h)
            {
                half3 highlightTerm = lerp(
                    half3(insideIris,insideIris,insideIris),
                    _EyeHighLightColor.rgb * outsideIris + insideIris,
                    saturate(_EyeHighLight));
                eyeBlend = highlightTerm *
                    (_EyeScatteringColor.rgb * baseSample.a + (1.0h - baseSample.a));
            }

            half3 shadowColor = EndfieldShadowColor(
                _ShadowLutTex,
                _UseShadowLutTex,
                baseSample.rgb,
                _ShadowColorBrightness,
                _ShadowColorSaturation);
            shadowColor *= EndfieldHGRPCharacterShadowTint(0.0h);
            half3 diffuseColor = lerp(
                shadowColor,
                baseSample.rgb * rampTint * eyeBlend,
                litAmount);
            half3 ambient = EndfieldAmbient(lightNormal);
            half ambientLobe = EndfieldHGRPCharacterAmbientLobe(lightNormal);
            half3 environmentIllumination =
                (half3(0.25h,0.25h,0.25h) + ambient) * _RecoveredAmbientStrength *
                EndfieldHGRPEnvironmentLightMultiplier() * ambientLobe *
                EndfieldHGRPSceneEnvironmentWeight();
            environmentIllumination *= lerp(
                EndfieldHGRPEnvironmentShadowMultiplier(), 1.0h, litAmount);
            half3 mainLightColor = lerp(
                _LightColor0.rgb,
                EndfieldHGRPCharacterMainColor(0.0h),
                EndfieldHGRPCompatibilityWeight());
            half3 directIllumination = mainLightColor * _RecoveredDirectStrength *
                EndfieldHGRPMainLightMultiplier() * lerp(0.55h, 1.0h, litAmount);
            half3 illumination = environmentIllumination + directIllumination;
            half3 color = diffuseColor * illumination;

            if (_UseMatcap > 0.5h)
            {
                half3 viewNormal = mul((half3x3)UNITY_MATRIX_V, matcapNormal);
                half2 matcapUv = normalize(viewNormal).xy * 0.5h + 0.5h;
                half4 matcap = tex2D(_MatcapTex, matcapUv);
                // Matches the recovered HGRP combination: texture RGB is weighted
                // by MatcapColor.a while texture alpha carries the colored term.
                half3 matcapContribution =
                    matcap.rgb * _MatcapColor.a + matcap.a * _MatcapColor.rgb;
                color += matcapContribution * illumination * lerp(0.5h, 1.0h, litAmount);

                half3 eyeDirect =
                    _EyeHighLightColor.rgb * outsideIris * saturate(_EyeHighLight) +
                    baseSample.a * _EyeScatteringColor.rgb;
                half3 volumeEyeDirect = EndfieldHGRPApplyEyeVolumeLight(
                    baseSample.rgb,
                    _EyeHighLightColor.rgb * outsideIris * saturate(_EyeHighLight),
                    baseSample.a * _EyeScatteringColor.rgb);
                half volumeEyeGate = EndfieldHGRPCompatibilityWeight() * saturate(
                    max(_CharacterParams13.x,
                        max(_CharacterParams13.y, _CharacterParams13.z)));
                color += lerp(eyeDirect, volumeEyeDirect, volumeEyeGate) *
                         insideIris * _RecoveredEyeDirectStrength;
            }

            half3 halfWS = normalize(lightWS + viewWS);
            half specularPower = exp2(2.0h + _Smoothness * 9.0h);
            half specular = pow(saturate(dot(lightNormal, halfWS)), specularPower) *
                            _Specular * litAmount;
            color += specular * lerp(half3(0.04h,0.04h,0.04h), baseSample.rgb, _Metallic) *
                     mainLightColor * EndfieldHGRPSpecularMultiplier();
            color += EndfieldHGOperatorAdditionalLighting(
                i.worldPos, lightNormal, viewWS, baseSample.rgb,
                _Metallic, _Smoothness, _Specular);
            color += tex2D(_EmissionMap, sampleUv).rgb * _EmissionColor.rgb *
                     _EmissionBrightness * saturate(_UseEmission);
            color = EndfieldHGRPPreExposeCharacterColor(color);
            return half4(max(color, 0.0h), baseSample.a);
        }

        struct EyeCameraDepthVaryings
        {
            float4 pos : SV_POSITION;
            float2 uv : TEXCOORD0;
        };

        EyeCameraDepthVaryings EyeCameraDepthVert(appdata_base v)
        {
            EyeCameraDepthVaryings o;
            o.pos = UnityObjectToClipPos(v.vertex);
            o.uv = TRANSFORM_TEX(v.texcoord, _BaseMap);
            return o;
        }

        half4 EyeCameraDepthFrag(EyeCameraDepthVaryings i) : SV_Target
        {
            half alpha = tex2D(_BaseMap, i.uv).a * _BaseColor.a;
            clip(EndfieldCutout(max(_EnableAlphaTest, _AlphaClip), alpha, _AlphaClipThreshold));
            return half4(i.pos.z, i.pos.z, i.pos.z, 1.0h);
        }

        struct EyeShadowVaryings
        {
            V2F_SHADOW_CASTER;
            float2 uv : TEXCOORD1;
        };

        EyeShadowVaryings EyeShadowVert(appdata_base v)
        {
            EyeShadowVaryings o;
            TRANSFER_SHADOW_CASTER_NORMALOFFSET(o)
            #if defined(ENDFIELD_RECOVERED_CHARACTER_SHADOW_PASS_VP)
                o.pos = EndfieldRecoveredCharacterShadowClipPosition(v.vertex);
            #endif
            o.uv = TRANSFORM_TEX(v.texcoord, _BaseMap);
            return o;
        }

        float4 EyeShadowFrag(EyeShadowVaryings i) : SV_Target
        {
            half alpha = tex2D(_BaseMap, i.uv).a * _BaseColor.a;
            clip(EndfieldCutout(max(_EnableAlphaTest, _AlphaClip), alpha, _AlphaClipThreshold));
            SHADOW_CASTER_FRAGMENT(i)
        }

        EndfieldRecoveredPreGBufferOutput EyeRecoveredPreGBufferDiagnosticFrag(
            EyeVaryings i,
            ENDFIELD_RECOVERED_FACE_AND_PRIMITIVE_INPUT(facing))
        {
            half alpha = tex2D(_BaseMap, i.uv).a * _BaseColor.a;
            clip(EndfieldCutout(
                max(_EnableAlphaTest, _AlphaClip),
                alpha,
                _AlphaClipThreshold));
            half faceSign = ENDFIELD_RECOVERED_FACE_IS_FRONT(facing)
                ? 1.0h
                : (-1.0h + 2.0h * _BackFaceNormalFlip);
            ENDFIELD_RECOVERED_SAME_OWNER_TANGENT_DECLARE(
                endfieldSameOwnerNormalTS);
            return ENDFIELD_RECOVERED_MAKE_PREGBUFFER_OUTPUT(
                normalize(i.worldNormal) * faceSign,
                0.7,
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
                Ref [_PreZStencilRefOption]
                Comp Always
                Pass Replace
            }

            CGPROGRAM
            #pragma target 5.0
            #pragma vertex EyeVert
            #pragma fragment EyeRecoveredPreGBufferDiagnosticFrag
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
            Blend [_SrcBlend] [_DstBlend]
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
            #pragma vertex EyeVert
            #pragma fragment EyeFrag
            #pragma multi_compile_fwdbase
            #pragma multi_compile __ ENDFIELD_RECOVERED_EYE_RESPONSE
            #pragma multi_compile __ ENDFIELD_RECOVERED_EYE_SCREEN_SHADOW_MASK_R
            #pragma multi_compile __ ENDFIELD_RECOVERED_SCREEN_SHADOW_MASK_CONSUMER
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
            #pragma vertex EyeCameraDepthVert
            #pragma fragment EyeCameraDepthFrag
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
            #pragma vertex EyeShadowVert
            #pragma fragment EyeShadowFrag
            #pragma multi_compile_shadowcaster
            #pragma multi_compile __ ENDFIELD_RECOVERED_CHARACTER_SHADOW_PASS_VP
            ENDCG
        }
    }

    Fallback Off
}
