Shader "Hidden/Endfield/Diagnostics/EndminfM27GenerativeExactAbiShell"
{
    Properties
    {
        _BaseColorMap ("M27 t0 BaseColor", 2D) = "white" {}
        _NormalMap ("M27 t1 Normal", 2D) = "bump" {}
        _MROMap ("M27 t2 MRO", 2D) = "white" {}
        _ParallaxMap ("M27 t3 Parallax", 2D) = "black" {}
        [HideInInspector] _ParallaxMaskMap ("M27 t4 mask", 2D) = "black" {}
        [HideInInspector] _ParallaxNoiseMap ("M27 t5 noise", 2D) = "black" {}
        // Source Material defaults for M_fx_endminm_gfx_27. The retained
        // compatibility material overrides every property it still carries;
        // fields absent from that narrow shader retain these serialized
        // source values rather than captured b3 bytes.
        [HideInInspector] _NormalScale ("", Float) = 1
        [HideInInspector] _RoughnessMin ("", Float) = 0
        [HideInInspector] _RoughnessMax ("", Float) = 1
        [HideInInspector] _OcclusionStrength ("", Float) = 1
        [HideInInspector] _TwoSidedNormal ("", Float) = 1
        [HideInInspector] _BaseUVSet ("", Float) = 0
        [HideInInspector] _BasePbrMapUVSet ("", Float) = 0
        [HideInInspector] _TAAUNormalBiasReverse ("", Float) = 0
        [HideInInspector] _BaseTextureMapCount ("", Float) = 0
        [HideInInspector] _BaseColorTintCover ("", Float) = 0
        [HideInInspector] _Metallic ("", Float) = 0
        [HideInInspector] _BaseColorBrighterScale ("", Float) = 1
        [HideInInspector] _AntiFlicker ("", Float) = 0
        [HideInInspector] _TaauMaskModeValue ("", Float) = 0
        [HideInInspector] _BaseColor ("", Color) = (1,1,1,1)
        [HideInInspector] _ParallaxStrength ("", Float) = 0.096
        [HideInInspector] _ParallaxMarchNum ("", Integer) = 5
        [HideInInspector] _ParallaxTilling ("", Float) = 3.36
        [HideInInspector] _ParallaxAnimSpeed ("", Float) = 0
        [HideInInspector] _ParallaxAnimRandom ("", Float) = 1
        [HideInInspector] _ParallaxMinBrightness ("", Float) = 0.2
        [HideInInspector] _ParallaxFresnelStrength ("", Float) = 1
        [HideInInspector] _ParallaxIgnorePostExposure ("", Float) = 1
        [HideInInspector] _ParallaxMaskChannel ("", Float) = 0
        [HideInInspector] _ParallaxMapUVType ("", Float) = 0
        [HideInInspector] _ParallaxMaskByLayerBlend ("", Float) = 0
        [HideInInspector] _ParallaxNoiseMapTilling ("", Float) = 1
        [HideInInspector] _ParallaxCharPos ("", Float) = 0
        [HideInInspector] _ParallaxBrightOuterRadius ("", Float) = 20
        [HideInInspector] _ParallaxBrightInnerRadius ("", Float) = 10
        [HideInInspector] _ParallaxBrightStrength ("", Float) = 1
        [HideInInspector] _UseParallaxMask ("", Float) = 0
        [HideInInspector] _ParallaxIntensity ("", Float) = 1
        [HideInInspector] _ParallaxColor ("", Color) = (964.7226,330.88165,85.55083,1)
        [HideInInspector] _ParallaxColorDark ("", Color) = (0,0,0,1)
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
            Name "M27GenerativeExactAbiShell"
            ZTest GEqual
            ZWrite On
            Cull Back
            Blend Off
            Stencil
            {
                Ref 0
                Comp Always
                Pass Replace
                Fail Keep
                ZFail Keep
            }

            HLSLPROGRAM
            #pragma target 5.0
            #pragma only_renderers d3d11
            #pragma vertex BridgeVertex
            #pragma fragment BridgePixel
            #pragma multi_compile __ ENDFIELD_ORIGINAL_DXBC_M27_EXACT

            #define ENDFIELD_M27_GENERATIVE_EXACT_ABI_SHELL_MARKER 1

            // The selected retail pair uses these physical slot extents:
            // VS b0[82], b1[20], b2[4091]; PS b0[45], b1[106],
            // b2[4085], b3[31], b4[1]. The names select the recovered full
            // global publishers, Unity's ParticleSystemRenderer per-draw
            // producer, the material buffer, and the source global b4.
            cbuffer _TransformVariables : register(b0)
            {
                float4 _M27TransformValues[82];
            };
            cbuffer ShaderVariablesGlobal : register(b1)
            {
                float4 _M27GlobalValues[106];
            };
            cbuffer UnityPerDraw : register(b2)
            {
                float4 _M27UnityPerDrawValues[4091];
            };
            cbuffer UnityPerMaterial : register(b3)
            {
                float _NormalScale : packoffset(c0.x);
                float _RoughnessMin : packoffset(c0.z);
                float _RoughnessMax : packoffset(c0.w);
                float _OcclusionStrength : packoffset(c1.x);
                float _TwoSidedNormal : packoffset(c1.w);
                float _BaseUVSet : packoffset(c2.w);
                float _BasePbrMapUVSet : packoffset(c3.x);
                float _TAAUNormalBiasReverse : packoffset(c3.y);
                float _BaseTextureMapCount : packoffset(c3.w);
                float _BaseColorTintCover : packoffset(c4.x);
                float _Metallic : packoffset(c4.y);
                float _BaseColorBrighterScale : packoffset(c4.z);
                float _AntiFlicker : packoffset(c7.x);
                float _TaauMaskModeValue : packoffset(c7.z);
                float4 _BaseColor : packoffset(c8);
                float4 _BaseColorMap_ST : packoffset(c11);
                float4 _NormalMap_ST : packoffset(c12);
                float _ParallaxStrength : packoffset(c22.x);
                uint _ParallaxMarchNum : packoffset(c24.x);
                float _ParallaxTilling : packoffset(c24.y);
                float _ParallaxAnimSpeed : packoffset(c24.z);
                float _ParallaxAnimRandom : packoffset(c24.w);
                float _ParallaxMinBrightness : packoffset(c25.x);
                float _ParallaxFresnelStrength : packoffset(c25.y);
                float _ParallaxIgnorePostExposure : packoffset(c25.z);
                float _ParallaxMaskChannel : packoffset(c25.w);
                float _ParallaxMapUVType : packoffset(c26.x);
                float _ParallaxMaskByLayerBlend : packoffset(c26.y);
                float _ParallaxNoiseMapTilling : packoffset(c26.z);
                float _ParallaxCharPos : packoffset(c26.w);
                float _ParallaxBrightOuterRadius : packoffset(c27.x);
                float _ParallaxBrightInnerRadius : packoffset(c27.y);
                float _ParallaxBrightStrength : packoffset(c27.z);
                float _UseParallaxMask : packoffset(c28.y);
                float _ParallaxIntensity : packoffset(c28.w);
                float4 _ParallaxColor : packoffset(c29);
                float4 _ParallaxColorDark : packoffset(c30);
            };
            cbuffer _TerrainSubsurfaceConstants : register(b4)
            {
                float3 _M27TerrainSubsurfacePadding : packoffset(c0.x);
                uint _TerrainSubsurfaceProfileInt : packoffset(c0.w);
            };

            // Subprogram 113 declares the optional skin palette at VS t0.
            // The selected Endminf stone mesh has no skin rows and its
            // source-produced record clears bit 5, but the shell must retain
            // the stage ABI so a replacement can never hide the dependency.
            StructuredBuffer<float4> _VertexSkinMatrices : register(t0);

            Texture2D<float4> _BaseColorMap : register(t0);
            Texture2D<float4> _NormalMap : register(t1);
            Texture2D<float4> _MROMap : register(t2);
            Texture2D<float4> _ParallaxMap : register(t3);
            // Retail PS DXBC declares and reads all six slots. The original
            // material serializes t4/t5 source properties as null, and their
            // recovered shader defaults are black; they are real retail
            // resources, not presentation values or compiler-only carriers.
            Texture2D<float4> _ParallaxMaskMap : register(t4);
            Texture2D<float4> _ParallaxNoiseMap : register(t5);
            SamplerState sampler_BaseColorMap : register(s0);
            SamplerState sampler_NormalMap : register(s1);
            SamplerState sampler_MROMap : register(s2);
            SamplerState sampler_ParallaxMap : register(s3);
            SamplerState sampler_ParallaxMaskMap : register(s4);
            SamplerState sampler_ParallaxNoiseMap : register(s5);

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
                keep += _M27TransformValues[81].x + _M27GlobalValues[19].x;
                uint record = min(input.instanceID << 4, 4075u);
                keep += _M27UnityPerDrawValues[record + 15].x;
                uint skinFlags = asuint(
                    _M27UnityPerDrawValues[record + 4].w);
                if ((skinFlags & 32u) != 0u)
                    keep += _VertexSkinMatrices[0].x * 1e-12;
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
                float4 value = _BaseColorMap.SampleLevel(
                    sampler_BaseColorMap, uv, 0);
                value += _NormalMap.SampleLevel(sampler_NormalMap, uv, 0);
                value += _MROMap.SampleLevel(sampler_MROMap, uv, 0);
                value += _ParallaxMap.SampleLevel(sampler_ParallaxMap, uv, 0);
                value += _ParallaxMaskMap.SampleLevel(
                    sampler_ParallaxMaskMap, uv, 0);
                value += _ParallaxNoiseMap.SampleLevel(
                    sampler_ParallaxNoiseMap, uv, 0);
                uint record = min(input.instanceID << 4, 4075u);
                value += _M27TransformValues[44] + _M27GlobalValues[105] +
                    _M27UnityPerDrawValues[record + 15] +
                    _ParallaxColorDark +
                    asfloat(_TerrainSubsurfaceProfileInt).xxxx;
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
