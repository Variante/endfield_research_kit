Shader "Hidden/Endfield/Recovered/Endminf/M27DeferredPresentation"
{
    SubShader
    {
        Tags { "RenderPipeline" = "HGRenderPipeline" }
        Pass
        {
            Name "PublishM27Depth"
            Cull Off
            ZTest Greater
            ZWrite On
            ColorMask 0
            Blend Off

            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex Vert
            #pragma fragment Frag

            Texture2D<float4> _EndfieldM27OwnershipMask;
            Texture2D<float> _EndfieldM27PrivateDepth;

            struct Varyings
            {
                float4 positionCS : SV_Position;
            };

            Varyings Vert(uint vertexId : SV_VertexID)
            {
                Varyings output;
                uint yBit = vertexId & 2u;
                uint xBit = (vertexId << 1u) & 2u;
                float2 corner = float2((float)xBit, (float)yBit);
                output.positionCS = float4(corner * 2.0 - 1.0, 0.0, 1.0);
                return output;
            }

            float Frag(float4 positionCS : SV_Position) : SV_Depth
            {
                int2 pixel = int2(positionCS.xy);
                float3 ownership =
                    _EndfieldM27OwnershipMask.Load(int3(pixel, 0)).rgb;
                if (max(ownership.r, max(ownership.g, ownership.b)) <= 0.0)
                    discard;
                return _EndfieldM27PrivateDepth.Load(int3(pixel, 0));
            }
            ENDHLSL
        }

        Pass
        {
            Name "PresentM27DeferredResolve"
            Cull Off
            ZTest Equal
            ZWrite Off
            Blend Off

            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex Vert
            #pragma fragment Frag

            Texture2D<float4> _EndfieldM27ResolvedColor;
            Texture2D<float4> _EndfieldM27SourceSceneColor;
            Texture2D<float4> _EndfieldM27OwnershipMask;

            struct Varyings
            {
                float4 positionCS : SV_Position;
            };

            Varyings Vert(uint vertexId : SV_VertexID)
            {
                Varyings output;
                uint yBit = vertexId & 2u;
                uint xBit = (vertexId << 1u) & 2u;
                float2 corner = float2((float)xBit, (float)yBit);
                output.positionCS = float4(corner * 2.0 - 1.0, 0.0, 1.0);
                return output;
            }

            float4 Frag(float4 positionCS : SV_Position) : SV_Target0
            {
                int2 pixel = int2(positionCS.xy);
                float3 ownership =
                    _EndfieldM27OwnershipMask.Load(int3(pixel, 0)).rgb;
                if (max(ownership.r, max(ownership.g, ownership.b)) <= 0.0)
                    discard;
                return _EndfieldM27SourceSceneColor.Load(int3(pixel, 0)) +
                    _EndfieldM27ResolvedColor.Load(int3(pixel, 0));
            }
            ENDHLSL
        }
    }
    Fallback Off
}
