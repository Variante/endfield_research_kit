Shader "Hidden/Endfield/Recovered/RendererIdSidecar"
{
    Properties
    {
        [PerRendererData] _EndfieldRecoveredRendererIdSidecar
            ("Recovered Renderer ID", Float) = 0
    }

    SubShader
    {
        Tags { "RenderType" = "Opaque" "Queue" = "Geometry" }
        Pass
        {
            Name "RendererIdSidecar"
            Tags { "LightMode" = "ForwardOnly" }
            Cull Back
            ZWrite Off
            ZTest LEqual
            Blend Off

            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #include "UnityCG.cginc"

            float _EndfieldRecoveredRendererIdSidecar;

            struct Attributes
            {
                float4 positionOS : POSITION;
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
            };

            Varyings Vert(Attributes input)
            {
                Varyings output;
                output.positionCS = UnityObjectToClipPos(input.positionOS);
                return output;
            }

            float4 Frag(Varyings input) : SV_Target
            {
                return float4(
                    _EndfieldRecoveredRendererIdSidecar,
                    0.0,
                    0.0,
                    1.0);
            }
            ENDHLSL
        }
    }
    FallBack Off
}
