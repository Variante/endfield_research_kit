Shader "Hidden/Endfield/HGRPCompat/TemporalResolve"
{
    SubShader
    {
        Tags { "RenderType"="Opaque" }
        Pass
        {
            ZTest Always
            ZWrite Off
            Cull Off

            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex Vert
            #pragma fragment Frag
            #include "UnityCG.cginc"

            sampler2D _MainTex;
            sampler2D _RecoveredTemporalCurrent;
            Texture2D<float4> _RecoveredTemporalCurrentLoad;
            sampler2D _RecoveredTemporalHistory;
            sampler2D _RecoveredTemporalSceneMV;
            sampler2D _EndfieldRecoveredTemporalDilatedDepth;
            sampler2D _EndfieldRecoveredTemporalDilatedMask;
            float4 _MainTex_TexelSize;
            float4 _RecoveredTemporalRenderSize;
            float _RecoveredTemporalHistoryWeight;
            float _RecoveredTemporalStaticHistoryWeight;
            float _RecoveredTemporalPackedResolve;
            float4 _RecoveredTemporalJitter;
            float _RecoveredTemporalFrameInfoY;
            float _RecoveredTemporalFastConverge;
            float _RecoveredTemporalResponsiveTransparency;

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float2 uv : TEXCOORD0;
            };

            Varyings Vert(appdata_img input)
            {
                Varyings output;
                output.positionCS = UnityObjectToClipPos(input.vertex);
                output.uv = input.texcoord.xy;
                return output;
            }

            float3 ToRetailYCoCg(float3 rgb)
            {
                // Exact ordinary-resolve matrix (the DXBC addresses RGB as
                // xzy): Y=R+B+2G, Co=2R-2B, Cg=-R-B+2G.
                return float3(
                    dot(rgb, float3(1.0, 2.0, 1.0)),
                    dot(rgb, float3(2.0, 0.0, -2.0)),
                    dot(rgb, float3(-1.0, 2.0, -1.0)));
            }

            float3 FromRetailYCoCg(float3 value)
            {
                return max(0.0, float3(
                    value.x + value.y - value.z,
                    value.x + value.z,
                    value.x - value.y - value.z) * 0.25);
            }

            float3 CompressRetailHistory(float2 uv)
            {
                float3 color = tex2Dlod(
                    _RecoveredTemporalHistory,
                    float4(saturate(uv), 0.0, 0.0)).rgb;
                return color / (1.0 + dot(
                    color,
                    float3(0.2126, 0.7152, 0.0722)));
            }

            float3 SampleRetailHistory(float2 uv, float2 texel)
            {
                // The ordinary DXBC folds Catmull-Rom's central pairs into
                // five bilinear taps and performs the interpolation in its
                // luminance-compressed domain.
                float2 textureSize = 1.0 / texel;
                float2 samplePosition = uv * textureSize;
                float2 texelCenter = floor(samplePosition - 0.5) + 0.5;
                float2 f = samplePosition - texelCenter;
                float2 f2 = f * f;
                float2 f3 = f2 * f;
                float2 w0 = -0.5 * f + f2 - 0.5 * f3;
                float2 w1 = 1.0 - 2.5 * f2 + 1.5 * f3;
                float2 w2 = 0.5 * f + 2.0 * f2 - 1.5 * f3;
                float2 w3 = -0.5 * f2 + 0.5 * f3;
                float2 w12 = w1 + w2;
                float2 pairedPosition = texelCenter + w2 / max(w12, 1e-5);
                float2 position0 = texelCenter - 1.0;
                float2 position3 = texelCenter + 2.0;

                float centerWeight = w12.x * w12.y;
                float leftWeight = w0.x * w12.y;
                float rightWeight = w3.x * w12.y;
                float bottomWeight = w12.x * w0.y;
                float topWeight = w12.x * w3.y;
                float weightSum = centerWeight + leftWeight + rightWeight +
                    bottomWeight + topWeight;
                float3 compressed =
                    CompressRetailHistory(pairedPosition * texel) * centerWeight +
                    CompressRetailHistory(float2(position0.x, pairedPosition.y) * texel) * leftWeight +
                    CompressRetailHistory(float2(position3.x, pairedPosition.y) * texel) * rightWeight +
                    CompressRetailHistory(float2(pairedPosition.x, position0.y) * texel) * bottomWeight +
                    CompressRetailHistory(float2(pairedPosition.x, position3.y) * texel) * topWeight;
                compressed /= max(weightSum, 1e-5);
                float compressedLuma = dot(
                    compressed,
                    float3(0.2126, 0.7152, 0.0722));
                return compressed / max(1.0 - compressedLuma, 1e-4);
            }

            int2 ClampPixel(int2 pixel, int2 size)
            {
                return clamp(pixel, int2(0, 0), size - 1);
            }

            float3 LoadCurrentRgb(int2 pixel, int2 size)
            {
                return max(0.0, _RecoveredTemporalCurrentLoad.Load(
                    int3(ClampPixel(pixel, size), 0)).rgb);
            }

            bool SimilarLuma(float center, float neighbor)
            {
                float low = min(center, neighbor);
                float ratio = max(center, neighbor) / low;
                return ratio > 0.0 && ratio < 1.9;
            }

            float4 Frag(Varyings input) : SV_Target
            {
                float2 uv = input.uv;
                float2 texel = _MainTex_TexelSize.xy;
                float4 packedMotion = tex2D(_RecoveredTemporalSceneMV, uv);
                int2 outputSize = max(int2(1, 1),
                    int2(_RecoveredTemporalRenderSize.xy));
                int2 centerPixel = ClampPixel(
                    int2(floor(input.positionCS.xy)), outputSize);
                float3 centerCurrent = tex2D(
                    _RecoveredTemporalCurrent, uv).rgb;
                float3 neighborhoodSum = 0.0;
                float3 neighborhoodSquareSum = 0.0;
                float3 gaussianCurrent = 0.0;

                [unroll]
                for (int y = -1; y <= 1; ++y)
                {
                    [unroll]
                    for (int x = -1; x <= 1; ++x)
                    {
                        float3 sampleColor = tex2D(
                            _RecoveredTemporalCurrent,
                            uv + float2(x, y) * texel).rgb;
                        float3 sampleYCoCg = ToRetailYCoCg(sampleColor);
                        neighborhoodSum += sampleYCoCg;
                        neighborhoodSquareSum += sampleYCoCg * sampleYCoCg;
                        float kernelWeight = (x == 0 && y == 0)
                            ? 0.2041799556
                            : ((x == 0 || y == 0)
                                ? 0.1238414032
                                : 0.0751136080);
                        gaussianCurrent += max(0.0, sampleColor) * kernelWeight;
                    }
                }

                // ComputeGaussianKernel's pinned native body (VA
                // 0x183c00bb0) receives constructor stdDev=1 and emits the
                // normalized weights above. Ordinary TAAU extracts bit 1 of
                // the 10-bit SceneMV B lane to select filtered vs center
                // current color before history blending.
                uint packedCurrentFlags =
                    (uint)(packedMotion.b * 1023.0 + 0.5);
                float useGaussianCurrent =
                    (float)((packedCurrentFlags >> 1) & 1u);
                float3 current = lerp(
                    centerCurrent,
                    gaussianCurrent,
                    useGaussianCurrent);
                float3 currentYCoCg = ToRetailYCoCg(current);

                // The shipped resolve clips reprojected history against the
                // current neighborhood before applying its history weight.
                // This bounded closure retains temporal VFX energy without
                // allowing an untracked actor silhouette to persist.
                // Literal Quality=0 HGRP/TAAUResolve DXBC decode: form
                // abs(encoded) * 2 - 1, raise it to the fourth power, choose
                // + below 0.5 / - above 0.5, then subtract that UV delta from
                // the current coordinate. This is already a history-UV delta;
                // treating it as an NDC delta introduced an erroneous 0.5
                // scale and opposite per-axis convention.
                float2 motionBase = abs(packedMotion.xy) * 2.0 - 1.0;
                float2 decodedUv = motionBase * motionBase;
                decodedUv *= decodedUv;
                decodedUv *= lerp(1.0, -1.0, step(0.5, packedMotion.xy));
                float motionValid = step(0.5, packedMotion.b);
                float2 previousUv = uv - motionValid * decodedUv;
                float3 history = SampleRetailHistory(previousUv, texel);
                // The ordinary resolve first bounds reconstructed history to
                // 0.2x..1.8x the direct reprojected history sample, then
                // performs a 3x3 variance clip in its exact YCoCg basis. Its
                // adaptive factor remains 1.25 throughout normalized
                // scene-color variance.
                float3 ordinaryDirectHistory = tex2Dlod(
                    _RecoveredTemporalHistory,
                    float4(previousUv, 0.0, 0.0)).rgb;
                history = clamp(
                    history,
                    ordinaryDirectHistory * 0.2,
                    ordinaryDirectHistory * 1.8);
                float3 neighborhoodMean = neighborhoodSum / 9.0;
                float3 neighborhoodVariance = max(
                    0.0,
                    neighborhoodSquareSum / 9.0 -
                    neighborhoodMean * neighborhoodMean);
                float3 neighborhoodDeviation = sqrt(neighborhoodVariance);
                float3 varianceFactor = saturate(
                    (neighborhoodDeviation - 20.0) * 0.05);
                varianceFactor = varianceFactor * varianceFactor *
                    (3.0 - 2.0 * varianceFactor);
                varianceFactor = 1.25 - 0.7 * varianceFactor;
                float3 neighborhoodMin = min(
                    neighborhoodMean - varianceFactor * neighborhoodDeviation,
                    currentYCoCg);
                float3 neighborhoodMax = max(
                    neighborhoodMean + varianceFactor * neighborhoodDeviation,
                    currentYCoCg);
                float3 historyYCoCg = clamp(
                    ToRetailYCoCg(history),
                    neighborhoodMin,
                    neighborhoodMax);
                history = FromRetailYCoCg(historyYCoCg);
                // CommonSettings serializes MinMotion=0 and MaxMotion=0.1;
                // DesktopSettings supplies 0.95 at rest and 0.85 in motion.
                // Motion-vector validity is a history gate, not the selector
                // for the in-motion weight: valid zero motion still uses the
                // static weight in the shipped ordinary (Quality=0) resolve.
                float motionAmount = saturate(
                    (abs(decodedUv.x) + abs(decodedUv.y)) / 0.1);
                motionAmount = motionAmount * motionAmount *
                    (3.0 - 2.0 * motionAmount);
                float historyWeight = lerp(
                    _RecoveredTemporalStaticHistoryWeight,
                    _RecoveredTemporalHistoryWeight,
                    motionAmount);
                historyWeight *= motionValid;
                float3 resolved = lerp(
                    current,
                    history,
                    saturate(historyWeight));
                if (_RecoveredTemporalPackedResolve < 0.5)
                    return float4(resolved, 1.0);

                // Full ordinary Quality-0 packed-resource experiment. The
                // shader math below is literal to the recovered no-keyword
                // DXBC; its opt-in gate remains required because capture-time
                // jitter/frame-info and live convergence lanes are not yet
                // admitted for the August reference.
                float2 outputUv = input.positionCS.xy *
                    _RecoveredTemporalRenderSize.zw;
                float2 unjitteredPixelF = floor(input.positionCS.xy);
                float2 jitteredPixelF = floor(clamp(
                    input.positionCS.xy - _RecoveredTemporalJitter.xy,
                    0.5,
                    _RecoveredTemporalRenderSize.xy - 0.5));
                int2 unjitteredPixel = ClampPixel(
                    int2(unjitteredPixelF), outputSize);
                int2 jitteredPixel = ClampPixel(
                    int2(jitteredPixelF), outputSize);
                packedMotion = tex2Dlod(
                    _RecoveredTemporalSceneMV,
                    float4((jitteredPixelF + 0.5) *
                        _RecoveredTemporalRenderSize.zw, 0.0, 0.0));
                float depth = tex2Dlod(
                    _EndfieldRecoveredTemporalDilatedDepth,
                    float4((jitteredPixelF + 0.5) *
                        _RecoveredTemporalRenderSize.zw, 0.0, 0.0)).x;

                motionBase = abs(packedMotion.xy) * 2.0 - 1.0;
                decodedUv = motionBase * motionBase;
                decodedUv *= decodedUv;
                decodedUv *= lerp(1.0, -1.0, step(0.5, packedMotion.xy));
                previousUv = outputUv - decodedUv;
                bool class06 = abs(packedMotion.w - 0.6) < 0.1;
                bool class03 = abs(packedMotion.w - 0.3) < 0.1;
                bool highClass = packedMotion.w > 0.9;
                packedCurrentFlags =
                    (uint)(packedMotion.b * 1023.0 + 0.5);
                useGaussianCurrent =
                    (float)((packedCurrentFlags >> 1) & 1u);

                centerPixel = class06 ? unjitteredPixel : jitteredPixel;
                neighborhoodSum = 0.0;
                neighborhoodSquareSum = 0.0;
                gaussianCurrent = 0.0;
                float3 samples[9];
                int sampleIndex = 0;
                [unroll]
                for (int py = -1; py <= 1; ++py)
                {
                    [unroll]
                    for (int px = -1; px <= 1; ++px)
                    {
                        float3 sampleRgb = LoadCurrentRgb(
                            centerPixel + int2(px, py), outputSize);
                        float3 sampleYC = ToRetailYCoCg(sampleRgb);
                        samples[sampleIndex++] = sampleYC;
                        neighborhoodSum += sampleYC;
                        neighborhoodSquareSum += sampleYC * sampleYC;
                        float kernelWeight = (px == 0 && py == 0)
                            ? 0.2041799556
                            : ((px == 0 || py == 0)
                                ? 0.1238414032
                                : 0.0751136080);
                        gaussianCurrent += sampleRgb * kernelWeight;
                    }
                }
                float3 centerYC = samples[4];
                currentYCoCg = lerp(
                    centerYC,
                    ToRetailYCoCg(gaussianCurrent),
                    useGaussianCurrent);

                float4 directHistory = tex2Dlod(
                    _RecoveredTemporalHistory,
                    float4(previousUv, 0.0, 0.0));
                float3 reconstructedHistory = SampleRetailHistory(
                    previousUv, texel);
                reconstructedHistory = clamp(
                    reconstructedHistory,
                    directHistory.rgb * 0.2,
                    directHistory.rgb * 1.8);
                float3 rawHistoryYCoCg = ToRetailYCoCg(
                    reconstructedHistory);
                neighborhoodMean = neighborhoodSum / 9.0;
                neighborhoodVariance = abs(
                    neighborhoodSquareSum / 9.0 -
                    neighborhoodMean * neighborhoodMean);
                neighborhoodDeviation = sqrt(neighborhoodVariance);
                varianceFactor = saturate(
                    (neighborhoodDeviation - 20.0) * 0.05);
                varianceFactor = varianceFactor * varianceFactor *
                    (3.0 - 2.0 * varianceFactor);
                varianceFactor = 1.25 - 0.7 * varianceFactor;
                neighborhoodMin = min(
                    neighborhoodMean - varianceFactor * neighborhoodDeviation,
                    centerYC);
                neighborhoodMax = max(
                    neighborhoodMean + varianceFactor * neighborhoodDeviation,
                    centerYC);
                float3 clippedHistoryYCoCg = clamp(
                    rawHistoryYCoCg, neighborhoodMin, neighborhoodMax);

                uint similarMask = 16u;
                float dissimilarMin = 100000.0;
                float dissimilarMax = 0.0;
                [unroll]
                for (uint neighborIndex = 0u; neighborIndex < 9u;
                    ++neighborIndex)
                {
                    if (neighborIndex == 4u)
                        continue;
                    bool similar = SimilarLuma(
                        centerYC.x, samples[neighborIndex].x);
                    if (similar)
                    {
                        similarMask |= 1u << neighborIndex;
                    }
                    else
                    {
                        dissimilarMin = min(
                            dissimilarMin, samples[neighborIndex].x);
                        dissimilarMax = max(
                            dissimilarMax, samples[neighborIndex].x);
                    }
                }
                bool centerOutside = centerYC.x < dissimilarMin ||
                    dissimilarMax < centerYC.x;
                bool completeQuadrant =
                    (similarMask & 27u) == 27u ||
                    (similarMask & 54u) == 54u ||
                    (similarMask & 216u) == 216u ||
                    (similarMask & 432u) == 432u;
                float historySupport = max(
                    (centerOutside && !completeQuadrant) ? 1.0 : 0.0,
                    0.9 * directHistory.a);

                bool outOfBounds = any(previousUv <
                    _RecoveredTemporalRenderSize.zw) ||
                    any((1.0 - _RecoveredTemporalRenderSize.zw) < previousUv);
                bool maskClear = !(tex2Dlod(
                    _EndfieldRecoveredTemporalDilatedMask,
                    float4(outputUv, 0.0, 0.0)).x > 0.0);
                float responsiveRisk = saturate(
                    _RecoveredTemporalResponsiveTransparency +
                    (highClass ? 1.0 : 0.0) + useGaussianCurrent);
                bool largeMotion = abs(decodedUv.x) + abs(decodedUv.y) > 0.3;
                float confidence = max(0.0,
                    (maskClear ? 1.0 : 0.0) - responsiveRisk -
                    (outOfBounds ? 1.0 : 0.0) -
                    (largeMotion ? 1.0 : 0.0) -
                    (class06 ? 1.0 : 0.0) -
                    _RecoveredTemporalFastConverge);
                confidence *= historySupport;
                bool validHistory = confidence >= 0.1;
                historyYCoCg = lerp(
                    clippedHistoryYCoCg,
                    rawHistoryYCoCg,
                    (validHistory && !outOfBounds) ? 1.0 : 0.0);

                float motionMeasure =
                    (abs(decodedUv.x) +
                     abs(decodedUv.y) * _RecoveredTemporalFrameInfoY) *
                    lerp(1.0, 256.0 * depth, class03 ? 1.0 : 0.0);
                float motionBlend = smoothstep(
                    0.00001, 0.00005, motionMeasure);
                historyWeight = lerp(
                    _RecoveredTemporalStaticHistoryWeight,
                    _RecoveredTemporalHistoryWeight,
                    motionBlend);
                float2 edgeDistance = abs(1.0 - 2.0 * frac(
                    _RecoveredTemporalRenderSize.xy * previousUv));
                float edge = max(edgeDistance.x, edgeDistance.y);
                historyWeight = lerp(historyWeight, 0.82, edge);
                historyWeight = lerp(
                    historyWeight,
                    0.5,
                    saturate(_RecoveredTemporalFastConverge +
                        (outOfBounds ? 1.0 : 0.0) +
                        (class06 ? 1.0 : 0.0)));
                historyWeight = lerp(
                    historyWeight, 0.3, responsiveRisk);
                historyWeight = validHistory ? 0.9 : historyWeight;

                float3 currentCompressed = currentYCoCg /
                    (1.0 + currentYCoCg.x);
                float3 historyCompressed = historyYCoCg /
                    (1.0 + historyYCoCg.x);
                float3 blendedCompressed = lerp(
                    currentCompressed,
                    historyCompressed,
                    historyWeight);
                float3 blendedYCoCg = blendedCompressed /
                    max(0.001, 1.0 - blendedCompressed.x);
                return float4(
                    FromRetailYCoCg(blendedYCoCg), confidence);
            }
            ENDHLSL
        }

        // The retail resolve's alpha is temporal confidence carried only by
        // its scene-color history. The lab's later compatibility Uber reads
        // source alpha as presentation opacity, so publish the resolved RGB
        // to beauty with opaque alpha while retaining pass 0 verbatim in the
        // persistent history texture.
        Pass
        {
            ZTest Always
            ZWrite Off
            Cull Off

            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex Vert
            #pragma fragment FragOpaqueBeauty
            #include "UnityCG.cginc"

            sampler2D _MainTex;

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float2 uv : TEXCOORD0;
            };

            Varyings Vert(appdata_img input)
            {
                Varyings output;
                output.positionCS = UnityObjectToClipPos(input.vertex);
                output.uv = input.texcoord.xy;
                return output;
            }

            float4 FragOpaqueBeauty(Varyings input) : SV_Target
            {
                return float4(tex2D(_MainTex, input.uv).rgb, 1.0);
            }
            ENDHLSL
        }
    }
    Fallback Off
}
