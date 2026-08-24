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
            sampler2D _RecoveredTemporalHistory;
            sampler2D _RecoveredTemporalSceneMV;
            float4 _MainTex_TexelSize;
            float _RecoveredTemporalHistoryWeight;
            float _RecoveredTemporalStaticHistoryWeight;

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

            float4 Frag(Varyings input) : SV_Target
            {
                float2 uv = input.uv;
                float2 texel = _MainTex_TexelSize.xy;
                float4 packedMotion = tex2D(_RecoveredTemporalSceneMV, uv);
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
                // 0.2x..1.8x the center sample, then performs a 3x3 variance
                // clip in its exact YCoCg basis. Its adaptive factor remains
                // 1.25 throughout normalized scene-color variance.
                history = clamp(history, current * 0.2, current * 1.8);
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
                return float4(resolved, 1.0);
            }
            ENDHLSL
        }
    }
    Fallback Off
}
