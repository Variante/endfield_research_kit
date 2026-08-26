Shader "Hidden/Endfield/Recovered/CharInfo/SphereOutsideDeferredPresentation"
{
    SubShader
    {
        Tags { "RenderPipeline" = "HGRenderPipeline" }
        Pass
        {
            Name "PublishSphereOutsideDepth"
            Cull Off
            ZTest Greater
            ZWrite On
            ColorMask 0
            Blend Off

            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex Vert
            #pragma fragment Frag

            Texture2D<float4> _EndfieldSphereOwnershipMask;
            Texture2D<float> _EndfieldSpherePrivateDepth;

            struct Varyings { float4 positionCS : SV_Position; };

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
                float3 owner = _EndfieldSphereOwnershipMask.Load(int3(pixel, 0)).rgb;
                if (max(owner.r, max(owner.g, owner.b)) <= 0.0)
                    discard;
                return _EndfieldSpherePrivateDepth.Load(int3(pixel, 0));
            }
            ENDHLSL
        }

        Pass
        {
            Name "PresentSphereOutsideDeferredResolve"
            Cull Off
            ZTest Equal
            ZWrite Off
            Blend Off

            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex Vert
            #pragma fragment Frag

            Texture2D<float4> _EndfieldSphereResolvedColor;
            Texture2D<float4> _EndfieldSphereSourceSceneColor;
            Texture2D<float4> _EndfieldSphereOwnershipMask;

            struct Varyings { float4 positionCS : SV_Position; };

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
                float3 owner = _EndfieldSphereOwnershipMask.Load(int3(pixel, 0)).rgb;
                if (max(owner.r, max(owner.g, owner.b)) <= 0.0)
                    discard;
                return _EndfieldSphereSourceSceneColor.Load(int3(pixel, 0)) +
                    _EndfieldSphereResolvedColor.Load(int3(pixel, 0));
            }
            ENDHLSL
        }
    }
    Fallback Off
}
