Shader "Hidden/Endfield/Recovered/DeferredResolverInputProbe"
{
    SubShader
    {
        Tags { "RenderType" = "Opaque" "Queue" = "Overlay" }

        Pass
        {
            Name "DeferredResolverInputProbe"
            Cull Off
            ZTest Always
            ZWrite Off
            Blend Off

            HLSLPROGRAM
            #pragma target 5.0
            #pragma only_renderers d3d11 d3d12
            #pragma vertex Vert
            #pragma fragment Frag

            // These are intentionally the numeric D3D11 bridge slots used by
            // the selected original resolver. The probe consumes the source
            // GBuffer names _62/_61/_60 in t23/t24/t25 order plus the
            // source-backed target resources t0/t1/t5/t6/t7/t22. It never
            // writes to the camera-owned target.
            cbuffer EndfieldCB0 : register(b0) { float4 _cb0; };
            cbuffer EndfieldCB1 : register(b1) { float4 _cb1; };
            cbuffer EndfieldCB2 : register(b2) { float4 _cb2; };
            cbuffer EndfieldCB3 : register(b3) { float4 _cb3; };
            cbuffer EndfieldCB4 : register(b4) { float4 _cb4; };
            cbuffer EndfieldCB5 : register(b5) { float4 _cb5; };
            cbuffer EndfieldCB6 : register(b6) { float4 _cb6; };
            cbuffer EndfieldCB7 : register(b7) { float4 _cb7; };
            cbuffer EndfieldCB8 : register(b8) { float4 _cb8; };

            StructuredBuffer<uint> _ResolverT0 : register(t0);
            Texture2D<float> _ResolverT1 : register(t1);
            Texture2DArray<float4> _ResolverT5 : register(t5);
            Texture2D<float> _ResolverT6 : register(t6);
            Texture2D<float> _ResolverT7 : register(t7);
            Texture2D<float2> _ResolverT22 : register(t22);
            Texture2D<float4> _62 : register(t23);
            Texture2D<float4> _61 : register(t24);
            Texture2D<float4> _60 : register(t25);

            struct Attributes
            {
                uint vertexId : SV_VertexID;
            };

            struct Varyings
            {
                float4 position : SV_Position;
            };

            Varyings Vert(Attributes input)
            {
                Varyings output;
                float2 position = float2(
                    (input.vertexId == 1u) ? 3.0 : -1.0,
                    (input.vertexId == 2u) ? 3.0 : -1.0);
                output.position = float4(position, 0.0, 1.0);
                return output;
            }

            float4 Frag(Varyings input) : SV_Target0
            {
                int2 pixel = int2(input.position.xy);
                float4 gBufferC = _62.Load(int3(pixel, 0));
                float4 gBufferB = _61.Load(int3(pixel, 0));
                float4 gBufferA = _60.Load(int3(pixel, 0));
                float binning = (float)(_ResolverT0[0] & 0xffu);
                float cameraDepth = _ResolverT1.Load(int3(pixel, 0));
                float4 reflection = _ResolverT5.Load(int4(0, 0, 0, 0));
                float punctualShadow = _ResolverT6.Load(int3(0, 0, 0));
                float lowResShadow = _ResolverT7.Load(int3(0, 0, 0));
                float2 screenShadow = _ResolverT22.Load(int3(pixel, 0));
                float bridge = dot(
                    _cb0 + _cb1 + _cb2 + _cb3 + _cb4 + _cb5 +
                    _cb6 + _cb7 + _cb8,
                    float4(1.0, 0.5, 0.25, 0.125));

                // Preserve the source C/B/A read order while keeping this
                // diagnostic numerically bounded and visibly non-presented.
                return float4(
                    saturate(abs(gBufferC.r) + abs(bridge) * 1.0e-6),
                    saturate(abs(gBufferB.g) + abs(bridge) * 1.0e-6 +
                        abs(cameraDepth + punctualShadow + lowResShadow) * 1.0e-7),
                    saturate(abs(gBufferA.b) + abs(bridge) * 1.0e-6 +
                        abs(binning + reflection.x + screenShadow.x) * 1.0e-7),
                    1.0);
            }
            ENDHLSL
        }
    }
}
