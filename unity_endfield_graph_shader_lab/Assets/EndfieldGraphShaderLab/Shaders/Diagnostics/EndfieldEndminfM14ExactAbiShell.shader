Shader "Hidden/Endfield/Diagnostics/EndminfM14ExactAbiShell"
{
    Properties
    {
        _M14SceneDepth ("M14 scene depth", 2D) = "black" {}
        _M14MainTexture ("M14 main texture", 2D) = "white" {}
    }

    SubShader
    {
        Tags
        {
            "RenderPipeline" = "EndfieldM14ExactAbiDiagnostic"
            "DisableBatching" = "True"
            "Queue" = "Transparent"
        }

        Pass
        {
            Name "M14ExactAbiShell"
            ZTest Always
            ZWrite Off
            Cull Off
            Blend One OneMinusSrcAlpha

            HLSLPROGRAM
            #pragma target 5.0
            #pragma only_renderers d3d11
            #pragma vertex BridgeVertex
            #pragma fragment BridgePixel
            // Reuse the plugin's existing reserved callback keyword. Shader
            // identity remains the stage plus the Unity bytecode SHA-256, so
            // sharing the reservation cannot select either M14 or M27.
            #pragma multi_compile __ ENDFIELD_ORIGINAL_DXBC_M27_EXACT

            // Shared maximum extents preserve every physical slot used by the
            // captured VS4914/PS4915 pair. The compiler strips stage-unused
            // declarations while retaining the exact D3D11 binding envelope.
            cbuffer EndfieldM14CB0 : register(b0) { float4 _M14CB0[28]; };
            cbuffer EndfieldM14CB1 : register(b1) { float4 _M14CB1[105]; };
            cbuffer EndfieldM14CB2 : register(b2) { float4 _M14CB2[4085]; };
            cbuffer EndfieldM14CB3 : register(b3) { float4 _M14CB3[4094]; };
            cbuffer EndfieldM14CB4 : register(b4) { float4 _M14CB4[10]; };

            Texture2D<float4> _M14SceneDepth : register(t0);
            Texture2D<float4> _M14MainTexture : register(t1);
            SamplerState sampler_M14SceneDepth : register(s0);
            SamplerState sampler_M14MainTexture : register(s1);

            struct RetailAttributes
            {
                float3 position : POSITION0;
                float4 color : COLOR0;
                float4 uv0 : TEXCOORD0;
                float4 uv1 : TEXCOORD1;
                float3 previousPosition : TEXCOORD4;
                float4 blendWeights : BLENDWEIGHTS0;
                uint4 blendIndices : BLENDINDICES0;
                uint instanceID : SV_InstanceID;
            };

            struct RetailVaryings
            {
                float4 position : SV_Position;
                float4 uv0 : TEXCOORD0;
                float4 uv1 : TEXCOORD1;
                float4 color : TEXCOORD2;
                float3 positionRws : TEXCOORD3;
                float3 previousPositionRws : TEXCOORD4;
                nointerpolation uint instanceID : TEXCOORD5;
            };

            RetailVaryings BridgeVertex(RetailAttributes input)
            {
                RetailVaryings output;
                uint record = min(input.instanceID << 4, 4078u);
                // The pinned retail VS consumes a structured SRV at t0. The
                // shell keeps t0 as a Unity-bindable SRV; the exact draw path
                // replaces that stage binding with the captured float4 buffer.
                float4 skin = _M14SceneDepth.Load(int3(0, 0, 0));
                float keep = dot(input.blendWeights, skin) +
                    dot(float4(input.blendIndices), 1.0) * 1e-12;
                keep += _M14CB0[1].x + _M14CB1[81].x + _M14CB2[103].x;
                keep += _M14CB3[record + 15].x + _M14CB4[9].x;
                output.position = float4(input.position + keep * 1e-12, 1.0);
                output.uv0 = input.uv0;
                output.uv1 = input.uv1;
                output.color = input.color;
                output.positionRws = input.position;
                output.previousPositionRws = input.previousPosition;
                output.instanceID = input.instanceID;
                return output;
            }

            struct RetailTargets
            {
                float4 sceneColor : SV_Target0;
                float4 sceneMotionVectors : SV_Target1;
            };

            RetailTargets BridgePixel(RetailVaryings input)
            {
                float2 uv = input.uv0.xy;
                float4 value = _M14SceneDepth.SampleLevel(
                    sampler_M14SceneDepth, uv, 0);
                value += _M14MainTexture.SampleLevel(
                    sampler_M14MainTexture, uv, 0);
                uint record = min(input.instanceID << 4, 4080u);
                value += _M14CB0[27] + _M14CB1[104] +
                    _M14CB2[record + 4] + _M14CB3[21];
                value += input.color + input.uv1 * 1e-12;
                value.xyz += (input.positionRws + input.previousPositionRws) *
                    1e-12;

                RetailTargets output;
                output.sceneColor = value;
                output.sceneMotionVectors = value;
                return output;
            }
            ENDHLSL
        }
    }
}
