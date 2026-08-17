Shader "Hidden/Endfield/Diagnostics/OriginalM23Dxbc"
{
    SubShader
    {
        Tags { "DisableBatching" = "True" }
        Pass
        {
            Name "IsolatedExactM23DxbcDiagnostic"
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
            #pragma multi_compile_local __ ENDFIELD_ORIGINAL_M23_DXBC_EXACT

            cbuffer EndfieldM23CB0 : register(b0) { float4 _EndfieldM23CB0[45]; };
            cbuffer EndfieldM23CB1 : register(b1) { float4 _EndfieldM23CB1[105]; };
            cbuffer EndfieldM23CB2 : register(b2) { float4 _EndfieldM23CB2[104]; };
            cbuffer EndfieldM23CB3 : register(b3) { float4 _EndfieldM23CB3[14]; };
            cbuffer EndfieldM23CB4 : register(b4) { float4 _EndfieldM23CB4[50]; };

            StructuredBuffer<float4> _EndfieldM23VST0 : register(t0);
            Texture2D<float4> _EndfieldM23TextureT0 : register(t0);
            Texture2D<float4> _EndfieldM23TextureT1 : register(t1);
            Texture2D<float4> _EndfieldM23TextureT2 : register(t2);
            Texture2D<float4> _EndfieldM23TextureT3 : register(t3);
            Texture2D<float4> _EndfieldM23TextureT4 : register(t4);
            SamplerState sampler_EndfieldM23TextureT0 : register(s0);
            SamplerState sampler_EndfieldM23TextureT1 : register(s1);
            SamplerState sampler_EndfieldM23TextureT2 : register(s2);
            SamplerState sampler_EndfieldM23TextureT3 : register(s3);
            SamplerState sampler_EndfieldM23TextureT4 : register(s4);

            struct Attributes
            {
                float3 positionOS : POSITION;
                float3 normalOS : NORMAL;
                float4 tangentOS : TANGENT;
                float4 color : COLOR;
                float4 texcoord0 : TEXCOORD0;
                float4 texcoord1 : TEXCOORD1;
                float4 texcoord4 : TEXCOORD4;
                float4 blendWeights : BLENDWEIGHTS;
                uint4 blendIndices : BLENDINDICES;
            };

            struct Varyings
            {
                float4 positionCS : SV_Position;
                float4 texcoord0 : TEXCOORD0;
                float4 texcoord1 : TEXCOORD1;
                float4 texcoord2 : TEXCOORD2;
                float3 texcoord3 : TEXCOORD3;
                float4 texcoord4 : TEXCOORD4;
                float4 texcoord5 : TEXCOORD5;
                float3 texcoord6 : TEXCOORD6;
                float3 texcoord7 : TEXCOORD7;
            };

            Varyings BridgeVertex(Attributes input)
            {
                Varyings output;
                float4 keep = _EndfieldM23CB0[44] + _EndfieldM23CB1[104] +
                    _EndfieldM23CB2[103] + _EndfieldM23CB3[13] +
                    _EndfieldM23CB4[49] + _EndfieldM23VST0[0];
                float preserve = dot(keep, 0.0) + dot(input.normalOS, 0.0) +
                    dot(input.tangentOS, 0.0) + dot(input.blendWeights, 0.0) +
                    dot(float4(input.blendIndices), 0.0);
                output.positionCS = float4(input.positionOS + preserve, 1.0);
                output.texcoord0 = input.texcoord0;
                output.texcoord1 = input.texcoord1;
                output.texcoord2 = float4(input.normalOS, 0.0);
                output.texcoord3 = input.tangentOS.xyz;
                output.texcoord4 = input.texcoord4;
                output.texcoord5 = input.color;
                output.texcoord6 = input.normalOS;
                output.texcoord7 = input.positionOS;
                return output;
            }

            struct Targets
            {
                float4 target0 : SV_Target0;
                float4 target1 : SV_Target1;
            };

            Targets BridgePixel(Varyings input)
            {
                float4 value = _EndfieldM23TextureT0.SampleLevel(sampler_EndfieldM23TextureT0, input.texcoord0.xy, 0);
                value += _EndfieldM23TextureT1.SampleLevel(sampler_EndfieldM23TextureT1, input.texcoord0.xy, 0);
                value += _EndfieldM23TextureT2.SampleLevel(sampler_EndfieldM23TextureT2, input.texcoord0.xy, 0);
                value += _EndfieldM23TextureT3.SampleLevel(sampler_EndfieldM23TextureT3, input.texcoord0.xy, 0);
                value += _EndfieldM23TextureT4.SampleLevel(sampler_EndfieldM23TextureT4, input.texcoord0.xy, 0);
                value += _EndfieldM23CB0[44] + _EndfieldM23CB1[104] +
                    _EndfieldM23CB2[103] + _EndfieldM23CB3[13] + _EndfieldM23CB4[49];
                Targets output;
                output.target0 = value + input.texcoord5;
                output.target1 = output.target0 * 0.5 + 0.25;
                return output;
            }
            ENDHLSL
        }
    }
    Fallback Off
}
