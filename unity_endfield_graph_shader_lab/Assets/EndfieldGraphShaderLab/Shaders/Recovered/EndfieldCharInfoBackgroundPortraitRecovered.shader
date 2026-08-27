Shader "Endfield/Recovered/CharInfo/BackgroundPortrait"
{
    Properties
    {
        [NoScaleOffset] _MainTex ("Original bg_charinfo Texture", 2D) = "black" {}
        _TintColor ("Recovered Canvas Vertex Color", Color) = (1,1,1,0.35294118)
        _DepthOffset ("Recovered Raw Depth Offset", Float) = 0.011
    }

    SubShader
    {
        Tags
        {
            "Queue" = "Transparent"
            "RenderType" = "Transparent"
            "IgnoreProjector" = "True"
        }

        Pass
        {
            Name "Default"
            Tags { "LightMode" = "SRPDefaultUnlit" }

            Cull Off
            ZWrite Off
            ZTest Always
            Blend One OneMinusSrcAlpha
            ColorMask RGBA

            CGPROGRAM
            #pragma target 4.5
            #pragma vertex Vert
            #pragma fragment Frag

            #include "UnityCG.cginc"

            sampler2D _MainTex;
            float4 _TintColor;
            float _DepthOffset;
            float4x4 _NonJitteredViewNoTransProjMatrix;
            float4 _WorldSpaceCameraPos_Internal;
            float _RenderPathInjected;
            float _HGFlipX;
            float _HGFlipY;

            Texture2D<float> _SceneDepth;
            SamplerState sampler_LinearRepeat;
            float4 _SceneDepth_TexelSize;
            float _EndfieldRecoveredPostUberWorldUiReady;

            struct Attributes
            {
                float4 positionOS : POSITION;
                float2 uv : TEXCOORD0;
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float2 uv : TEXCOORD0;
            };

            Varyings Vert(Attributes input)
            {
                Varyings output;
                float3 worldPosition = mul(
                    unity_ObjectToWorld,
                    input.positionOS).xyz;
                float3 relativePosition = worldPosition -
                    _WorldSpaceCameraPos_Internal.xyz * _RenderPathInjected;
                if (_RenderPathInjected > 0.0)
                {
                    output.positionCS = mul(
                        _NonJitteredViewNoTransProjMatrix,
                        float4(relativePosition, 1.0));
                    output.positionCS.x *= 1.0 - 2.0 * _HGFlipX;
                    output.positionCS.y *= 1.0 - 2.0 * _HGFlipY;
                }
                else
                {
                    output.positionCS = mul(
                        UNITY_MATRIX_VP,
                        float4(relativePosition, 1.0));
                }
                output.uv = input.uv;
                return output;
            }

            half4 Frag(Varyings input) : SV_Target
            {
                // Original selected HGRP/UI/Default variant:
                // CLIP_SCENEDEPTH + HG_WORLD_UI, _isFarPlaneDepth=0,
                // _isZDepthOffset=1, _zDepthOffset=.011. The retail shader
                // computes saturate(z/w-.011), linearizes both depths, and
                // discards when scene depth is nearer. The default-off
                // compositor binds the preserved full-scene primary
                // depth/stencil after the fullscreen post, matching the
                // source-closed producer identity and chronology.
                clip(_EndfieldRecoveredPostUberWorldUiReady - 0.5);
                float2 screenUV = input.positionCS.xy *
                    _SceneDepth_TexelSize.xy;
                float sceneRawDepth = _SceneDepth.Sample(
                    sampler_LinearRepeat,
                    screenUV).r;
                float uiRawDepth = saturate(input.positionCS.z - _DepthOffset);
                float sceneLinearDepth = LinearEyeDepth(sceneRawDepth);
                float uiLinearDepth = LinearEyeDepth(uiRawDepth);
                clip(sceneLinearDepth - uiLinearDepth);

                half4 sampleValue = tex2D(_MainTex, input.uv);
                half alpha = sampleValue.a * _TintColor.a;
                half3 color = sampleValue.rgb * _TintColor.rgb * alpha;
                return half4(color, alpha);
            }
            ENDCG
        }
    }

    Fallback Off
}
