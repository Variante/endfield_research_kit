Shader "Hidden/Endfield/Diagnostics/OriginalDeferredResolverDxbc"
{
    SubShader
    {
        Tags
        {
            "RenderPipeline" = "EndfieldOriginalDxbcDiagnostic"
            "DisableBatching" = "True"
        }

        Pass
        {
            Name "IsolatedExactDxbcDiagnostic"
            Blend Off
            ZTest Always
            ZWrite Off
            Cull Off
            ColorMask RGBA

            HLSLPROGRAM
            #pragma target 5.0
            #pragma only_renderers d3d11
            #pragma vertex BridgeVertex
            #pragma fragment BridgePixel
            #pragma multi_compile_local __ ENDFIELD_ORIGINAL_DXBC_EXACT

            // This is a Unity-owned resource/binding shell. The exact programs
            // are installed only while the native plugin is explicitly armed
            // and this unique local keyword is enabled.
            cbuffer EndfieldCB0 : register(b0) { float4 _EndfieldCB0[45]; };
            cbuffer EndfieldCB1 : register(b1) { float4 _EndfieldCB1[157]; };
            cbuffer EndfieldCB2 : register(b2) { float4 _EndfieldCB2[259]; };
            cbuffer EndfieldCB3 : register(b3) { float4 _EndfieldCB3[3]; };
            cbuffer EndfieldCB4 : register(b4) { float4 _EndfieldCB4[2054]; };
            cbuffer EndfieldCB5 : register(b5) { float4 _EndfieldCB5[401]; };
            cbuffer EndfieldCB6 : register(b6) { float4 _EndfieldCB6[216]; };
            cbuffer EndfieldCB7 : register(b7) { float4 _EndfieldCB7[15]; };
            cbuffer EndfieldCB8 : register(b8) { float4 _EndfieldCB8[160]; };
            cbuffer EndfieldCB9 : register(b9) { float4 _EndfieldCB9[4]; };

            StructuredBuffer<uint> _EndfieldBufferT0 : register(t0);
            Texture2D<float4> _EndfieldTextureT1 : register(t1);
            Texture2D<float4> _EndfieldTextureT2 : register(t2);
            Texture2D<float4> _EndfieldTextureT3 : register(t3);
            Texture2D<float4> _EndfieldTextureT4 : register(t4);
            Texture2DArray<float4> _EndfieldTextureT5 : register(t5);
            Texture2D<float4> _EndfieldTextureT6 : register(t6);
            Texture2D<float4> _EndfieldTextureT7 : register(t7);
            Texture2D<float4> _EndfieldTextureT8 : register(t8);
            Texture2D<float4> _EndfieldTextureT9 : register(t9);
            Texture2D<float4> _EndfieldTextureT10 : register(t10);
            Texture2DArray<float4> _EndfieldTextureT11 : register(t11);
            Texture2DArray<float4> _EndfieldTextureT12 : register(t12);
            Texture2D<float4> _EndfieldTextureT13 : register(t13);
            Texture2D<float4> _EndfieldTextureT14 : register(t14);
            Texture3D<float4> _EndfieldTextureT15 : register(t15);
            Texture2D<float4> _EndfieldTextureT16 : register(t16);
            Texture2D<float4> _EndfieldTextureT17 : register(t17);
            Texture3D<float4> _EndfieldTextureT18 : register(t18);
            Texture3D<float4> _EndfieldTextureT19 : register(t19);
            Texture3D<float4> _EndfieldTextureT20 : register(t20);
            Texture3D<float4> _EndfieldTextureT21 : register(t21);
            Texture2D<float4> _EndfieldTextureT22 : register(t22);
            Texture2D<float4> _EndfieldTextureT23 : register(t23);
            Texture2D<float4> _EndfieldTextureT24 : register(t24);
            Texture2D<float4> _EndfieldTextureT25 : register(t25);
            Texture2D<float4> _EndfieldTextureT26 : register(t26);
            Texture2D<float4> _EndfieldTextureT27 : register(t27);

            // Unity's sampler association convention keeps the shell's numeric
            // sampler slots compatible with the selected original program:
            // s0->t1, s1->t24, s2->3D probes, s3->t5, s4->t6 comparison.
            SamplerState sampler_EndfieldTextureT1 : register(s0);
            SamplerState sampler_EndfieldTextureT24 : register(s1);
            SamplerState sampler_EndfieldTextureT18 : register(s2);
            SamplerState sampler_EndfieldTextureT5 : register(s3);
            SamplerComparisonState sampler_EndfieldTextureT6 : register(s4);

            struct BridgeVaryings
            {
                float4 positionCS : SV_Position;
                float2 texcoord0 : TEXCOORD0;
            };

            BridgeVaryings BridgeVertex(uint vertexID : SV_VertexID)
            {
                BridgeVaryings output;
                float2 corner = float2((vertexID << 1) & 2, vertexID & 2);
                output.positionCS = float4(corner * 2.0 - 1.0, 0.0, 1.0);
                output.texcoord0 = float2(corner.x, 1.0 - corner.y);
                return output;
            }

            float4 BridgePixel(BridgeVaryings input) : SV_Target0
            {
                // Keep every resource and exact constant-buffer extent in
                // Unity's serialized binding metadata. This body is displaced
                // before execution only for the armed keyword variant.
                int2 pixel = int2(input.positionCS.xy);
                int3 voxel = int3(pixel, 0);
                float4 value = asfloat(_EndfieldBufferT0[0]).xxxx;
                value += _EndfieldTextureT1.Load(int3(pixel, 0));
                value += _EndfieldTextureT2.Load(int3(pixel, 0));
                value += _EndfieldTextureT3.Load(int3(pixel, 0));
                value += _EndfieldTextureT4.Load(int3(pixel, 0));
                value += _EndfieldTextureT5.Load(int4(pixel, 0, 0));
                value += _EndfieldTextureT6.Load(int3(pixel, 0));
                value += _EndfieldTextureT7.Load(int3(pixel, 0));
                value += _EndfieldTextureT8.Load(int3(pixel, 0));
                value += _EndfieldTextureT9.Load(int3(pixel, 0));
                value += _EndfieldTextureT10.Load(int3(pixel, 0));
                value += _EndfieldTextureT11.Load(int4(pixel, 0, 0));
                value += _EndfieldTextureT12.Load(int4(pixel, 0, 0));
                value += _EndfieldTextureT13.Load(int3(pixel, 0));
                value += _EndfieldTextureT14.Load(int3(pixel, 0));
                value += _EndfieldTextureT15.Load(int4(voxel, 0));
                value += _EndfieldTextureT16.Load(int3(pixel, 0));
                value += _EndfieldTextureT17.Load(int3(pixel, 0));
                value += _EndfieldTextureT18.Load(int4(voxel, 0));
                value += _EndfieldTextureT19.Load(int4(voxel, 0));
                value += _EndfieldTextureT20.Load(int4(voxel, 0));
                value += _EndfieldTextureT21.Load(int4(voxel, 0));
                value += _EndfieldTextureT22.Load(int3(pixel, 0));
                value += _EndfieldTextureT23.Load(int3(pixel, 0));
                value += _EndfieldTextureT24.Load(int3(pixel, 0));
                value += _EndfieldTextureT25.Load(int3(pixel, 0));
                value += _EndfieldTextureT26.Load(int3(pixel, 0));
                value += _EndfieldTextureT27.Load(int3(pixel, 0));
                value += _EndfieldTextureT1.SampleLevel(
                    sampler_EndfieldTextureT1, input.texcoord0, 0);
                value += _EndfieldTextureT24.SampleLevel(
                    sampler_EndfieldTextureT24, input.texcoord0, 0);
                value += _EndfieldTextureT18.SampleLevel(
                    sampler_EndfieldTextureT18, float3(input.texcoord0, 0), 0);
                value += _EndfieldTextureT5.SampleLevel(
                    sampler_EndfieldTextureT5, float3(input.texcoord0, 0), 0);
                value += _EndfieldTextureT6.SampleCmpLevelZero(
                    sampler_EndfieldTextureT6, input.texcoord0, 0).xxxx;
                value += _EndfieldCB0[44] + _EndfieldCB1[156] + _EndfieldCB2[258];
                value += _EndfieldCB3[2] + _EndfieldCB4[2053] + _EndfieldCB5[400];
                value += _EndfieldCB6[215] + _EndfieldCB7[14] + _EndfieldCB8[159];
                value += _EndfieldCB9[3];
                return value;
            }
            ENDHLSL
        }
    }
    Fallback Off
}
