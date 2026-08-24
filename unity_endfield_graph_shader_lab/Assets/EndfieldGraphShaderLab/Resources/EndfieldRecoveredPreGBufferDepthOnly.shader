Shader "Hidden/Endfield/HGRPCompat/RecoveredPreGBufferDepthOnly"
{
    SubShader
    {
        Tags { "RenderPipeline"="HDRenderPipeline" }

        Pass
        {
            Name "DEPTH_ONLY"
            Cull Back
            ZWrite On
            ZTest LEqual
            ColorMask 0

            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex Vert
            #pragma fragment Frag
            #include "UnityCG.cginc"

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

            void Frag()
            {
            }
            ENDHLSL
        }
    }

    Fallback Off
}
