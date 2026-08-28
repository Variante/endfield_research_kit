Shader "Hidden/Endfield/HGRPCompat/ExposureTonemap"
{
    Properties
    {
        _MainTex ("Source", 2D) = "white" {}
        _RecoveredVignetteColor ("Recovered CharInfo Vignette Color", Color) = (0.06666667,0.067174576,0.07450981,1)
        _RecoveredShadowMultiplier ("Recovered CharInfo Shadow Grade", Float) = 0.89473686
    }

    SubShader
    {
        Tags { "RenderType"="Opaque" }
        Cull Off
        ZWrite Off
        ZTest Always

        Pass
        {
            CGPROGRAM
            #pragma target 3.0
            #pragma vertex vert_img
            #pragma fragment Frag
            #include "UnityCG.cginc"
            #include "EndfieldHGRPRecoveredPost.cginc"
            #include "EndfieldRecoveredCharInfoLut.cginc"

            sampler2D _MainTex;
            sampler2D _BloomTex;
            sampler2D _RecoveredColorGradingLut;
            float _PostExposure;
            float _TonemapMode;
            float _BloomIntensity;
            float4 _ToneCurveParams0; // toe strength/length, shoulder strength/length
            float4 _ToneCurveParams1; // shoulder angle, gamma, saturation, contrast
            float4 _VignetteParams; // intensity, smoothness, roundness, output aspect
            float4 _RecoveredVignetteColor;
            float _RecoveredShadowMultiplier;
            float _EndfieldRecoveredPostSemantics;
            float _RecoveredColorGradingLutReady;
            float _EndfieldRecoveredLinearUnormFinalTarget;
            // x=radial, y=chromatic, z=opt-in label/gate. This is a narrow
            // visual-compatibility response, not the recovered UberPost shader.
            float4 _EndminfVisualCompatibilityParams;
            float2 _EndminfVisualCompatibilityCenter;

            // Presentation flip. CommandBuffer.Blit to the backbuffer inverts Y
            // on UV-starts-at-top devices while a RenderTexture destination does
            // not, so the offscreen capture path and the Play-mode backbuffer
            // disagree. This is a global rather than a material property because
            // the same material records several deferred blits in one command
            // buffer and would otherwise observe only the final value.
            float _EndfieldPresentFlipY;
            float4 _EndfieldRecoveredFinalTargetSize;

            float EF_RecoveredLinearToIEC_sRGB(float value)
            {
                if (value <= 0.00313080009)
                    return 12.9200001 * value;
                return 1.05499995 * pow(abs(value), 1.0 / 2.4) - 0.0549999997;
            }

            float3 EF_RecoveredFinalOETFAndDither(float3 color, float2 uv)
            {
                float3 encoded = float3(
                    EF_RecoveredLinearToIEC_sRGB(color.r),
                    EF_RecoveredLinearToIEC_sRGB(color.g),
                    EF_RecoveredLinearToIEC_sRGB(color.b));
                float2 pixelPosition = _EndfieldRecoveredFinalTargetSize.xy * uv;
                float seed = dot(pixelPosition, float2(171.0, 231.0));
                float3 noise = frac(
                    seed * float3(1.0 / 103.0, 1.0 / 71.0, 1.0 / 97.0)) - 0.5;
                return encoded + noise * 0.0013725491;
            }

            float3 ACESFittedApproximation(float3 color)
            {
                // This is a stable ACES-style fit, not a claim of bit-identical HGRP
                // ACES_modified. The recovered component proves the selected mode and
                // control surface, while the final proprietary curve remains unresolved.
                const float a = 2.51;
                const float b = 0.03;
                const float c = 2.43;
                const float d = 0.59;
                const float e = 0.14;
                return saturate((color * (a * color + b)) / (color * (c * color + d) + e));
            }

            float3 ApplyRecoveredCurveControls(float3 color)
            {
                float toeStrength = saturate(_ToneCurveParams0.x);
                float toeLength = saturate(_ToneCurveParams0.y);
                float shoulderStrength = saturate(_ToneCurveParams0.z);
                float shoulderLength = max(_ToneCurveParams0.w, 0.0);
                float shoulderAngle = saturate(_ToneCurveParams1.x);

                float3 toeCurve = color * color / max(color + lerp(0.02, 0.5, toeLength), 1e-5);
                color = lerp(color, toeCurve, toeStrength);

                float shoulderScale = 1.0 + shoulderLength * 0.25;
                float3 shoulderCurve = 1.0 - exp(-color * shoulderScale);
                shoulderCurve = lerp(shoulderCurve, shoulderCurve / max(1.0 - shoulderAngle * 0.25, 1e-3), shoulderAngle);
                return lerp(color, shoulderCurve, shoulderStrength);
            }

            float4 SampleEndminfSceneLod0(float2 uv)
            {
                float2 clampedUv = saturate(uv);
                return tex2Dlod(
                    _MainTex, float4(clampedUv, 0.0, 0.0));
            }

            float3 SampleEndminfRecoveredRadialChromatic(
                float2 uv,
                float2 center,
                float radialIntensity,
                float chromaticIntensity,
                float effectivePower)
            {
                // Direct translation of shipped UberPost DXBC fragment
                // 3f490e1504c435541769ee03e881583df554e652df155e5b942a3a410d8e086b
                // (BLOOM + RADIAL_BLUR_CHROMATIC_ABERRATION), specialized to
                // Endminf's two active components. Both exact
                // serialized _averageSteps values are zero, so the DXBC keeps
                // the powered radial vector unnormalized.
                float2 delta = uv - center;
                float distanceSquared = dot(delta, delta);
                float2 poweredRadial = delta * pow(
                    max(distanceSquared, 1e-8), effectivePower * 0.5);

                // The shipped kernel uses SampleLevel(..., 0) for every
                // source-color fetch. Implicit tex2D derivatives select
                // coarser mips across the warped coordinates and visibly
                // break Endminf's thin late-pulse ring.
                float3 source = SampleEndminfSceneLod0(uv).rgb;
                if (_EndminfVisualCompatibilityParams.z > 3.0)
                {
                    float combined = chromaticIntensity + radialIntensity;
                    float3 accumulated = float3(source.r, 0.0, 0.0);
                    accumulated.r += SampleEndminfSceneLod0(
                        uv - poweredRadial * combined).r;
                    accumulated.r += SampleEndminfSceneLod0(
                        uv - poweredRadial * (2.0 * combined)).r;

                    accumulated.g += SampleEndminfSceneLod0(
                        uv - poweredRadial * chromaticIntensity).g;
                    accumulated.g += SampleEndminfSceneLod0(
                        uv - poweredRadial *
                        (2.0 * chromaticIntensity + radialIntensity)).g;
                    accumulated.g += SampleEndminfSceneLod0(
                        uv - poweredRadial *
                        (3.0 * chromaticIntensity + 2.0 * radialIntensity)).g;

                    accumulated.b += SampleEndminfSceneLod0(
                        uv - poweredRadial * (2.0 * chromaticIntensity)).b;
                    accumulated.b += SampleEndminfSceneLod0(
                        uv - poweredRadial *
                        (3.0 * chromaticIntensity + radialIntensity)).b;
                    accumulated.b += SampleEndminfSceneLod0(
                        uv - poweredRadial *
                        (4.0 * chromaticIntensity + 2.0 * radialIntensity)).b;
                    return accumulated * 0.333333403;
                }

                // The DXBC low branch keeps source red and samples green/blue
                // once along the same powered vector.
                return float3(
                    source.r,
                    SampleEndminfSceneLod0(uv - poweredRadial *
                        (2.0 * chromaticIntensity + radialIntensity)).g,
                    SampleEndminfSceneLod0(uv - poweredRadial *
                        (3.0 * chromaticIntensity + 2.0 * radialIntensity)).b);
            }

            float3 DecodeEndminfUberBloomInput(float3 bloom)
            {
                // The shipped combined BLOOM +
                // RADIAL_BLUR_CHROMATIC_ABERRATION Uber variant conditionally
                // decodes each bloom channel before the merge. Endminf/CharInfo
                // uses BloomParams.z == 0, so the retail condition is simply
                // channel > 0.3 and no blend-mode source subtraction remains.
                float3 decoded;
                decoded.r = bloom.r > 0.3
                    ? pow(bloom.r, 0.33) * 1.49380004 - 0.7
                    : bloom.r;
                decoded.g = bloom.g > 0.3
                    ? pow(bloom.g, 0.33) * 1.49380004 - 0.7
                    : bloom.g;
                decoded.b = bloom.b > 0.3
                    ? pow(bloom.b, 0.33) * 1.49380004 - 0.7
                    : bloom.b;
                return decoded;
            }

            float4 Frag(v2f_img input) : SV_Target
            {
                float2 presentUv = input.uv;
                presentUv.y = lerp(presentUv.y, 1.0 - presentUv.y, _EndfieldPresentFlipY);
                float radial = _EndminfVisualCompatibilityParams.x;
                float chromatic = _EndminfVisualCompatibilityParams.y;
                float4 source = tex2D(_MainTex, presentUv);
                bool endminfWarpActive =
                    _EndminfVisualCompatibilityParams.z > 0.5 &&
                    radial + chromatic > 0.00001;
                if (endminfWarpActive)
                {
                    source.rgb = SampleEndminfRecoveredRadialChromatic(
                        presentUv,
                        _EndminfVisualCompatibilityCenter,
                        radial,
                        chromatic,
                        _EndminfVisualCompatibilityParams.w);
                }
                float3 bloom = max(tex2D(_BloomTex, presentUv).rgb, 0.0);
                float bloomIntensity = _EndfieldRecoveredPostSemantics > 0.5
                    ? EF_BloomIntensityFromSerialized(_BloomIntensity)
                    : _BloomIntensity;
                // The shipped combined Uber variant warps the source-color
                // input first, then combines its separate bloom input at the
                // presentation UV. Bloom must not be resampled at each radial
                // or chromatic tap.
                float3 color;
                if (_EndfieldRecoveredPostSemantics > 0.5)
                {
                    // Retail Uber multiplies only the warped HDR source by
                    // _ExposureWithMiscParams.x. Its separate bloom input is
                    // decoded and merged afterwards. CharInfo's blend mode is
                    // zero and its normalized tint is white.
                    color = source.rgb * _PostExposure +
                        DecodeEndminfUberBloomInput(bloom) * bloomIntensity;
                }
                else
                {
                    color = (source.rgb + bloom * bloomIntensity) *
                        _PostExposure;
                }
                color = max(color, 0.0);

                if (_EndfieldRecoveredPostSemantics > 0.5)
                {
                    color = EF_ApplyCharInfoVignette(
                        color,
                        presentUv,
                        _VignetteParams.x,
                        _VignetteParams.y,
                        _VignetteParams.z,
                        _RecoveredVignetteColor.rgb);

                    if (_TonemapMode > 0.5)
                    {
                        if (_RecoveredColorGradingLutReady > 0.5)
                        {
                            color = EF_SampleRecoveredCharInfoLut(
                                _RecoveredColorGradingLut,
                                color);
                        }
                        else
                        {
                            float3 acescg = EF_AP0ToAP1(EF_LinearSRGBToAP0(color));
                            acescg = EF_ApplyCharInfoGradeAP1(
                                acescg,
                                _ToneCurveParams1.z,
                                _RecoveredShadowMultiplier);
                            color = EF_ACESModified(acescg);
                        }
                    }

                    // Only the validated linear-UNorm target path enables this.
                    // That path writes one R8G8B8A8_UNorm temporary and presents
                    // it with a same-format pixel-data copy, so no second shader
                    // or render-target OETF can occur.
                    if (_EndfieldRecoveredLinearUnormFinalTarget > 0.5)
                        color = EF_RecoveredFinalOETFAndDither(color, presentUv);
                    return float4(color, min(source.a, 1.0));
                }

                float luminance = dot(color, float3(0.2126, 0.7152, 0.0722));
                color = lerp(luminance.xxx, color, _ToneCurveParams1.z);
                color = (color - 0.18) * _ToneCurveParams1.w + 0.18;
                color = max(color, 0.0);

                if (_TonemapMode > 0.5)
                {
                    color = ACESFittedApproximation(color);
                    color = ApplyRecoveredCurveControls(color);
                }

                float2 vignetteUv = abs(presentUv - 0.5) * 2.0;
                float aspectCorrection = lerp(1.0, max(_VignetteParams.w, 1.0), _VignetteParams.z);
                vignetteUv.x *= aspectCorrection;
                float boxDistance = max(vignetteUv.x / aspectCorrection, vignetteUv.y);
                float roundDistance = length(vignetteUv) / max(length(float2(aspectCorrection, 1.0)), 1e-4);
                float vignetteDistance = lerp(boxDistance, roundDistance, saturate(_VignetteParams.z));
                float vignette = smoothstep(
                    1.0 - saturate(_VignetteParams.y),
                    1.0,
                    vignetteDistance);
                color *= 1.0 - vignette * saturate(_VignetteParams.x);

                color = pow(max(color, 0.0), rcp(max(_ToneCurveParams1.y, 1e-3)));
                return float4(color, source.a);
            }
            ENDCG
        }

        Pass
        {
            Name "CHARACTER_BLOOM_PREFILTER"

            CGPROGRAM
            #pragma target 3.0
            #pragma vertex vert_img
            #pragma fragment BloomPrefilterFrag
            #include "UnityCG.cginc"
            #include "EndfieldHGRPRecoveredPost.cginc"

            sampler2D _MainTex;
            float4 _MainTex_TexelSize;
            float4 _BloomTexelSize;
            float _BloomThreshold;
            float _BloomSoftness;
            float _EndfieldRecoveredPostSemantics;

            float4 BloomPrefilterFrag(v2f_img input) : SV_Target
            {
                if (_EndfieldRecoveredPostSemantics > 0.5)
                {
                    float3 recovered = EF_BloomPrefilter5Tap(
                        _MainTex,
                        input.uv,
                        _BloomTexelSize.zw,
                        _BloomThreshold);
                    return float4(recovered, 1.0);
                }

                float3 color = max(tex2D(_MainTex, input.uv).rgb, 0.0);
                float brightness = max(color.r, max(color.g, color.b));
                float knee = max(_BloomThreshold * _BloomSoftness, 1e-4);
                float soft = saturate((brightness - _BloomThreshold + knee) / (2.0 * knee));
                soft = soft * soft * knee;
                float contribution = max(brightness - _BloomThreshold, soft);
                return float4(color * (contribution / max(brightness, 1e-4)), 1.0);
            }
            ENDCG
        }

        Pass
        {
            Name "CHARACTER_BLOOM_BLUR"

            CGPROGRAM
            #pragma target 3.0
            #pragma vertex vert_img
            #pragma fragment BloomBlurFrag
            #include "UnityCG.cginc"
            #include "EndfieldHGRPRecoveredPost.cginc"

            sampler2D _MainTex;
            float4 _MainTex_TexelSize;
            float2 _BloomDirection;
            float _EndfieldRecoveredPostSemantics;

            float4 BloomBlurFrag(v2f_img input) : SV_Target
            {
                float2 stepUv = _MainTex_TexelSize.xy * _BloomDirection;

                if (_EndfieldRecoveredPostSemantics > 0.5)
                {
                    float3 recovered = abs(_BloomDirection.x) > abs(_BloomDirection.y)
                        ? EF_BloomBlurHorizontal9Tap(_MainTex, input.uv, stepUv)
                        : EF_BloomBlurVertical5Fetch(_MainTex, input.uv, stepUv);
                    return float4(recovered, 1.0);
                }

                float3 color = tex2D(_MainTex, input.uv).rgb * 0.227027;
                color += tex2D(_MainTex, input.uv + stepUv * 1.384615).rgb * 0.316216;
                color += tex2D(_MainTex, input.uv - stepUv * 1.384615).rgb * 0.316216;
                color += tex2D(_MainTex, input.uv + stepUv * 3.230769).rgb * 0.070270;
                color += tex2D(_MainTex, input.uv - stepUv * 3.230769).rgb * 0.070270;
                return float4(color, 1.0);
            }
            ENDCG
        }

        Pass
        {
            Name "RECOVERED_SCENE_BLOOM_UPSAMPLE"

            CGPROGRAM
            #pragma target 3.0
            #pragma vertex vert_img
            #pragma fragment BloomUpsampleFrag
            #include "UnityCG.cginc"
            #include "EndfieldHGRPRecoveredPost.cginc"

            sampler2D _MainTex;
            sampler2D _SourceTexLowMip;
            float4 _BloomBicubicParams;
            float _BloomScatter;

            float4 BloomUpsampleFrag(v2f_img input) : SV_Target
            {
                float3 highMip = max(tex2D(_MainTex, input.uv).rgb, 0.0);
                float3 lowMip = max(
                    EF_SampleBloomBicubic(
                        _SourceTexLowMip,
                        input.uv,
                        _BloomBicubicParams),
                    0.0);
                return float4(lerp(highMip, lowMip, _BloomScatter), 1.0);
            }
            ENDCG
        }

        Pass
        {
            Name "ENDMINF_POST_UBER_DEPTH_SYNC"

            CGPROGRAM
            #pragma target 3.0
            #pragma vertex vert_img
            #pragma fragment EndminfPostUberDepthFrag
            #include "UnityCG.cginc"

            sampler2D _MainTex;
            float4 _EndminfVisualCompatibilityParams;
            float2 _EndminfVisualCompatibilityCenter;

            float SampleEndminfRawDepth(float2 uv)
            {
                return tex2Dlod(
                    _MainTex,
                    float4(saturate(uv), 0.0, 0.0)).r;
            }

            void RetainNearestEndminfDepth(
                float2 uv,
                inout float nearestRawDepth,
                inout float nearestLinearDepth)
            {
                float rawDepth = SampleEndminfRawDepth(uv);
                float linearDepth = LinearEyeDepth(rawDepth);
                if (linearDepth < nearestLinearDepth)
                {
                    nearestRawDepth = rawDepth;
                    nearestLinearDepth = linearDepth;
                }
            }

            float EndminfPostUberDepthFrag(v2f_img input) : SV_Target
            {
                float2 uv = input.uv;
                float nearestRawDepth = SampleEndminfRawDepth(uv);
                float nearestLinearDepth = LinearEyeDepth(nearestRawDepth);
                float radialIntensity = _EndminfVisualCompatibilityParams.x;
                float chromaticIntensity = _EndminfVisualCompatibilityParams.y;
                bool warpActive =
                    _EndminfVisualCompatibilityParams.z > 0.5 &&
                    radialIntensity + chromaticIntensity > 0.00001;
                if (!warpActive)
                    return nearestRawDepth;

                float2 delta = uv - _EndminfVisualCompatibilityCenter;
                float distanceSquared = dot(delta, delta);
                float2 poweredRadial = delta * pow(
                    max(distanceSquared, 1e-8),
                    _EndminfVisualCompatibilityParams.w * 0.5);

                if (_EndminfVisualCompatibilityParams.z > 3.0)
                {
                    float combined = chromaticIntensity + radialIntensity;
                    RetainNearestEndminfDepth(
                        uv - poweredRadial * combined,
                        nearestRawDepth,
                        nearestLinearDepth);
                    RetainNearestEndminfDepth(
                        uv - poweredRadial * (2.0 * combined),
                        nearestRawDepth,
                        nearestLinearDepth);

                    RetainNearestEndminfDepth(
                        uv - poweredRadial * chromaticIntensity,
                        nearestRawDepth,
                        nearestLinearDepth);
                    RetainNearestEndminfDepth(
                        uv - poweredRadial *
                            (2.0 * chromaticIntensity + radialIntensity),
                        nearestRawDepth,
                        nearestLinearDepth);
                    RetainNearestEndminfDepth(
                        uv - poweredRadial *
                            (3.0 * chromaticIntensity +
                             2.0 * radialIntensity),
                        nearestRawDepth,
                        nearestLinearDepth);

                    RetainNearestEndminfDepth(
                        uv - poweredRadial * (2.0 * chromaticIntensity),
                        nearestRawDepth,
                        nearestLinearDepth);
                    RetainNearestEndminfDepth(
                        uv - poweredRadial *
                            (3.0 * chromaticIntensity + radialIntensity),
                        nearestRawDepth,
                        nearestLinearDepth);
                    RetainNearestEndminfDepth(
                        uv - poweredRadial *
                            (4.0 * chromaticIntensity +
                             2.0 * radialIntensity),
                        nearestRawDepth,
                        nearestLinearDepth);
                }
                else
                {
                    RetainNearestEndminfDepth(
                        uv - poweredRadial *
                            (2.0 * chromaticIntensity + radialIntensity),
                        nearestRawDepth,
                        nearestLinearDepth);
                    RetainNearestEndminfDepth(
                        uv - poweredRadial *
                            (3.0 * chromaticIntensity +
                             2.0 * radialIntensity),
                        nearestRawDepth,
                        nearestLinearDepth);
                }

                return nearestRawDepth;
            }
            ENDCG
        }
    }

    Fallback Off
}
