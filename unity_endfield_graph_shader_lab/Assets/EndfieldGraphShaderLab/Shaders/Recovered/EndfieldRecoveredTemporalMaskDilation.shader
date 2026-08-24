Shader "Hidden/Endfield/HGRPCompat/TemporalMaskDilation"
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

            sampler2D _RecoveredTemporalPackedSceneMV;
            float4 _RecoveredTemporalRenderSize;

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

            float Frag(Varyings input) : SV_Target
            {
                float2 texel = _RecoveredTemporalRenderSize.zw;
                float packed = tex2Dlod(
                    _RecoveredTemporalPackedSceneMV,
                    float4(input.uv, 0.0, 0.0)).b;
                packed = max(packed, tex2Dlod(
                    _RecoveredTemporalPackedSceneMV,
                    float4(saturate(input.uv + texel), 0.0, 0.0)).b);
                packed = max(packed, tex2Dlod(
                    _RecoveredTemporalPackedSceneMV,
                    float4(saturate(input.uv + float2(-texel.x, texel.y)),
                        0.0, 0.0)).b);
                packed = max(packed, tex2Dlod(
                    _RecoveredTemporalPackedSceneMV,
                    float4(saturate(input.uv + float2(texel.x, -texel.y)),
                        0.0, 0.0)).b);
                packed = max(packed, tex2Dlod(
                    _RecoveredTemporalPackedSceneMV,
                    float4(saturate(input.uv - texel), 0.0, 0.0)).b);
                return packed > 0.0 ? 1.0 : 0.0;
            }
            ENDHLSL
        }
    }
    Fallback Off
}
