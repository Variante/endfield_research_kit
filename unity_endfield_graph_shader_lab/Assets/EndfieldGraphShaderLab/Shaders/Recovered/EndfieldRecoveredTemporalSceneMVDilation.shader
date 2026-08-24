Shader "Hidden/Endfield/HGRPCompat/TemporalSceneMVDilation"
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

            Texture2D<float> _RecoveredTemporalSceneDepth;
            Texture2D<float4> _RecoveredTemporalRawSceneMV;
            Texture2D<float> _RecoveredTemporalPreviousDilatedDepth;
            Texture2D<float4> _RecoveredTemporalPreviousDilatedSceneMV;
            float4 _RecoveredTemporalRenderSize;
            float4x4 _RecoveredTemporalReprojectionMatrix;
            float _RecoveredTemporalAuxiliaryHistoryValid;
            float _RecoveredTemporalOcclusionDepthDiff;

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
            };

            Varyings Vert(appdata_img input)
            {
                Varyings output;
                output.positionCS = UnityObjectToClipPos(input.vertex);
                return output;
            }

            float2 DecodeMotionVector(float2 encoded)
            {
                float2 magnitude = abs(2.0 * abs(encoded) - 1.0);
                return sign(0.5 - encoded) *
                    (magnitude * magnitude * magnitude * magnitude);
            }

            void SelectMaxDepthSceneMV(
                int2 center,
                int2 size,
                out float selectedDepth,
                out float4 selectedSceneMV)
            {
                selectedDepth = 0.0;
                int2 selectedOffset = int2(0, 0);
                [unroll]
                for (int y = -1; y <= 1; ++y)
                {
                    [unroll]
                    for (int x = -1; x <= 1; ++x)
                    {
                        int2 candidate = clamp(center + int2(x, y), 0, size - 1);
                        float candidateDepth = _RecoveredTemporalSceneDepth.Load(
                            int3(candidate, 0));
                        if (candidateDepth > selectedDepth)
                        {
                            selectedDepth = candidateDepth;
                            selectedOffset = int2(x, y);
                        }
                    }
                }

                // Retail clamps the point-sampled depth footprint, but keeps
                // the winning offset for the unbounded Texture2D.Load here.
                selectedSceneMV = _RecoveredTemporalRawSceneMV.Load(
                    int3(center + selectedOffset, 0));
            }

            float4 Frag(Varyings input) : SV_Target
            {
                int2 size = int2(_RecoveredTemporalRenderSize.xy);
                int2 center = clamp(int2(input.positionCS.xy), 0, size - 1);
                float selectedDepth;
                float4 currentSceneMV;
                SelectMaxDepthSceneMV(
                    center,
                    size,
                    selectedDepth,
                    currentSceneMV);

                float2 currentMotion = DecodeMotionVector(currentSceneMV.xy);
                int2 previousPixel = center -
                    (int2)(_RecoveredTemporalRenderSize.xy * currentMotion);

                float previousDepth = 0.0;
                float4 previousSceneMV = float4(0.5, 0.5, 0.0, 0.0);
                // The retail allocation/clear payload is not recovered. Keep
                // the first auxiliary frame deterministic and fail closed;
                // the separately recovered scene-color gate assigns zero
                // history weight on that frame.
                if (_RecoveredTemporalAuxiliaryHistoryValid > 0.5)
                {
                    previousDepth = _RecoveredTemporalPreviousDilatedDepth.Load(
                        int3(previousPixel, 0));
                    previousSceneMV =
                        _RecoveredTemporalPreviousDilatedSceneMV.Load(
                            int3(previousPixel, 0));
                }

                float2 pixel = input.positionCS.xy;
                float2 currentNdc =
                    2.0 * (pixel * _RecoveredTemporalRenderSize.zw) - 1.0;
                float4 previousClip = mul(
                    _RecoveredTemporalReprojectionMatrix,
                    float4(currentNdc.x, -currentNdc.y, selectedDepth, 1.0));
                float expectedPreviousDepth =
                    previousClip.z / previousClip.w;

                float2 previousMotion = DecodeMotionVector(previousSceneMV.xy);
                bool currentClass = abs(currentSceneMV.w - 0.3) < 0.1;
                bool previousClass = abs(previousSceneMV.w - 0.3) < 0.1;
                bool currentHigh = currentSceneMV.w > 0.9;
                bool previousHigh = previousSceneMV.w > 0.9;
                bool depthMismatch =
                    previousDepth - expectedPreviousDepth >
                    _RecoveredTemporalOcclusionDepthDiff;
                float motionDelta =
                    abs(currentMotion.x - previousMotion.x) +
                    abs(currentMotion.y - previousMotion.y);
                float motionGate = smoothstep(0.0001, 0.0005, motionDelta);
                float risk = saturate(
                    saturate(
                        (depthMismatch ? 1.0 : 0.0) +
                        abs(
                            (currentClass ? 1.0 : 0.0) -
                            (previousClass ? 1.0 : 0.0))) * motionGate +
                    abs(
                        (currentHigh ? 1.0 : 0.0) -
                        (previousHigh ? 1.0 : 0.0)));

                uint currentBase = (uint)currentSceneMV.z;
                uint previousBit0 =
                    ((uint)(previousSceneMV.z * 1023.0 + 0.5)) & 1u;
                uint bit1 =
                    ((uint)(risk * (currentClass ? 0.0 : 1.0))) << 1;
                uint bit2 =
                    ((currentSceneMV.z - (float)previousBit0) < 0.0
                        ? 1u
                        : 0u) << 2;
                currentSceneMV.z =
                    ((float)(currentBase | bit1 | bit2) + 0.5) / 1023.0;

                return currentSceneMV;
            }
            ENDHLSL
        }
        Pass
        {
            ZTest Always
            ZWrite Off
            Cull Off

            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex Vert
            #pragma fragment FragDepth
            #include "UnityCG.cginc"

            Texture2D<float> _RecoveredTemporalSceneDepth;
            float4 _RecoveredTemporalRenderSize;

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
            };

            Varyings Vert(appdata_img input)
            {
                Varyings output;
                output.positionCS = UnityObjectToClipPos(input.vertex);
                return output;
            }

            float FragDepth(Varyings input) : SV_Target
            {
                int2 size = int2(_RecoveredTemporalRenderSize.xy);
                int2 center = clamp(int2(input.positionCS.xy), 0, size - 1);
                float selectedDepth = 0.0;

                [unroll]
                for (int y = -1; y <= 1; ++y)
                {
                    [unroll]
                    for (int x = -1; x <= 1; ++x)
                    {
                        int2 candidate = clamp(center + int2(x, y), 0, size - 1);
                        selectedDepth = max(
                            selectedDepth,
                            _RecoveredTemporalSceneDepth.Load(
                                int3(candidate, 0)));
                    }
                }

                return selectedDepth;
            }
            ENDHLSL
        }
        Pass
        {
            ZTest Always
            ZWrite Off
            Cull Off

            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex Vert
            #pragma fragment FragSelectedSceneMV
            #include "UnityCG.cginc"

            Texture2D<float> _RecoveredTemporalSceneDepth;
            Texture2D<float4> _RecoveredTemporalRawSceneMV;
            float4 _RecoveredTemporalRenderSize;

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
            };

            Varyings Vert(appdata_img input)
            {
                Varyings output;
                output.positionCS = UnityObjectToClipPos(input.vertex);
                return output;
            }

            float4 FragSelectedSceneMV(Varyings input) : SV_Target
            {
                int2 size = int2(_RecoveredTemporalRenderSize.xy);
                int2 center = clamp(int2(input.positionCS.xy), 0, size - 1);
                float selectedDepth = 0.0;
                int2 selectedOffset = int2(0, 0);

                [unroll]
                for (int y = -1; y <= 1; ++y)
                {
                    [unroll]
                    for (int x = -1; x <= 1; ++x)
                    {
                        int2 candidate = clamp(center + int2(x, y), 0, size - 1);
                        float candidateDepth = _RecoveredTemporalSceneDepth.Load(
                            int3(candidate, 0));
                        if (candidateDepth > selectedDepth)
                        {
                            selectedDepth = candidateDepth;
                            selectedOffset = int2(x, y);
                        }
                    }
                }

                return _RecoveredTemporalRawSceneMV.Load(
                    int3(center + selectedOffset, 0));
            }
            ENDHLSL
        }
    }
    Fallback Off
}
