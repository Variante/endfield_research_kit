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

            float4 Frag(Varyings input) : SV_Target
            {
                int2 size = int2(_RecoveredTemporalRenderSize.xy);
                int2 center = clamp(int2(input.positionCS.xy), 0, size - 1);
                int2 selected = center;
                float selectedDepth = _RecoveredTemporalSceneDepth.Load(
                    int3(center, 0));

                // Literal current-frame spatial half of HGRP/TAAUDilation:
                // reversed-Z depth is maximized over the 3x3 footprint and
                // SceneMV is loaded from the winning pixel. The retail pass
                // subsequently repacks flags from auxiliary-frame histories;
                // that independently gated temporal half is intentionally not
                // synthesized here.
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
                            selected = candidate;
                        }
                    }
                }

                return _RecoveredTemporalRawSceneMV.Load(int3(selected, 0));
            }
            ENDHLSL
        }
    }
    Fallback Off
}
