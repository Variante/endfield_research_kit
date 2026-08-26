Shader "Hidden/Endfield/Diagnostics/EndminfM27ExactAbiShell"
{
    Properties
    {
        _M27T0 ("M27 t0", 2D) = "white" {}
        _M27T1 ("M27 t1", 2D) = "bump" {}
        _M27T2 ("M27 t2", 2D) = "white" {}
        _M27T3 ("M27 t3", 2D) = "black" {}
        _M27T4 ("M27 t4", 2D) = "black" {}
        _M27T5 ("M27 t5", 2D) = "black" {}
    }

    SubShader
    {
        Tags
        {
            "RenderPipeline" = "EndfieldM27ExactAbiDiagnostic"
            "DisableBatching" = "True"
        }

        Pass
        {
            Name "M27ExactAbiShell"
            ZTest Off
            ZWrite On
            Cull Off
            Blend Off

            HLSLPROGRAM
            #pragma target 5.0
            #pragma only_renderers d3d11
            #pragma vertex BridgeVertex
            #pragma fragment BridgePixel
            #pragma multi_compile_local __ ENDFIELD_ORIGINAL_DXBC_M27_EXACT

            // The selected retail pair uses these physical slot extents:
            // VS b0[82], b1[20], b2[4091]; PS b0[45], b1[106],
            // b2[4085], b3[31], b4[1]. Shared maximum-sized shells keep the
            // Unity binding metadata compatible with both stages.
            cbuffer EndfieldM27CB0 : register(b0) { float4 _M27CB0[82]; };
            cbuffer EndfieldM27CB1 : register(b1) { float4 _M27CB1[106]; };
            cbuffer EndfieldM27CB2 : register(b2) { float4 _M27CB2[4091]; };
            cbuffer EndfieldM27CB3 : register(b3) { float4 _M27CB3[31]; };
            cbuffer EndfieldM27CB4 : register(b4) { float4 _M27CB4[1]; };

            Texture2D<float4> _M27T0 : register(t0);
            Texture2D<float4> _M27T1 : register(t1);
            Texture2D<float4> _M27T2 : register(t2);
            Texture2D<float4> _M27T3 : register(t3);
            Texture2D<float4> _M27T4 : register(t4);
            Texture2D<float4> _M27T5 : register(t5);
            SamplerState sampler_M27T0 : register(s0);
            SamplerState sampler_M27T1 : register(s1);
            SamplerState sampler_M27T2 : register(s2);
            SamplerState sampler_M27T3 : register(s3);
            SamplerState sampler_M27T4 : register(s4);
            SamplerState sampler_M27T5 : register(s5);

            struct RetailAttributes
            {
                float3 position : POSITION0;
                float3 normal : NORMAL0;
                float4 tangent : TANGENT0;
                float4 color : COLOR0;
                float2 uv0 : TEXCOORD0;
                float2 uv1 : TEXCOORD1;
                float4 previousPosition : TEXCOORD4;
                float4 blendWeights : BLENDWEIGHTS0;
                uint4 blendIndices : BLENDINDICES0;
                uint instanceID : SV_InstanceID;
            };

            struct RetailVaryings
            {
                float4 position : SV_Position;
                float2 uv0 : TEXCOORD0;
                float2 uv1 : TEXCOORD1;
                float3 normal : TEXCOORD2;
                float4 tangent : TEXCOORD3;
                float4 unusedRetailTexcoord4 : TEXCOORD4;
                float3 positionRws : TEXCOORD5;
                float3 previousPositionRws : TEXCOORD6;
                nointerpolation uint instanceID : TEXCOORD7;
            };

            RetailVaryings BridgeVertex(RetailAttributes input)
            {
                RetailVaryings output;
                float keep = dot(input.color, 1.0) + dot(input.blendWeights, 1.0);
                keep += dot(float4(input.blendIndices), 1.0) * 1e-12;
                keep += _M27CB0[81].x + _M27CB1[19].x;
                uint record = min(input.instanceID << 4, 4075u);
                keep += _M27CB2[record + 15].x;
                output.position = float4(input.position + keep * 1e-12, 1.0);
                output.uv0 = input.uv0;
                output.uv1 = input.uv1;
                output.normal = input.normal;
                output.tangent = input.tangent;
                output.unusedRetailTexcoord4 = 0.0;
                output.positionRws = input.position;
                output.previousPositionRws = input.previousPosition.xyz;
                output.instanceID = input.instanceID;
                return output;
            }

            struct RetailTargets
            {
                float4 target0 : SV_Target0;
                float4 target1 : SV_Target1;
                float4 target2 : SV_Target2;
                float4 target3 : SV_Target3;
                float4 target4 : SV_Target4;
            };

            RetailTargets BridgePixel(
                RetailVaryings input,
                bool frontFace : SV_IsFrontFace)
            {
                float2 uv = input.uv0 + input.uv1 * 1e-12;
                float4 value = _M27T0.SampleLevel(sampler_M27T0, uv, 0);
                value += _M27T1.SampleLevel(sampler_M27T1, uv, 0);
                value += _M27T2.SampleLevel(sampler_M27T2, uv, 0);
                value += _M27T3.SampleLevel(sampler_M27T3, uv, 0);
                value += _M27T4.SampleLevel(sampler_M27T4, uv, 0);
                value += _M27T5.SampleLevel(sampler_M27T5, uv, 0);
                uint record = min(input.instanceID << 4, 4075u);
                value += _M27CB0[44] + _M27CB1[105] +
                    _M27CB2[record + 15] + _M27CB3[30] + _M27CB4[0];
                value += float4(
                    input.normal + input.positionRws * 1e-12,
                    frontFace ? 1.0 : 0.0);
                value += input.tangent * 1e-12;
                value += input.unusedRetailTexcoord4 * 1e-12;
                value.xyz += input.previousPositionRws * 1e-12;

                RetailTargets output;
                output.target0 = value;
                output.target1 = value;
                output.target2 = value;
                output.target3 = value;
                output.target4 = value;
                return output;
            }
            ENDHLSL
        }
    }
}
