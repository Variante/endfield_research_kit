Shader "Hidden/Endfield/Compatibility/Endminf/LitEffectM01M38"
{
    Properties
    {
        _BaseColorMap ("Recovered Base Color Map", 2D) = "white" {}
        _BaseColor ("Recovered Base Color", Color) = (1,1,1,1)
        _MROMap ("Recovered MRO Map", 2D) = "white" {}
        _NormalMap ("Recovered Normal Map", 2D) = "bump" {}
        _ParallaxMap ("Recovered Parallax Map", 2D) = "black" {}
        [HDR] _ParallaxColor ("Recovered Parallax Color", Color) = (1,0.3,0.05,1)
        _ParallaxIntensity ("Recovered Parallax Intensity", Float) = 1
    }
    SubShader
    {
        // VISUAL COMPATIBILITY ONLY. This is not the retail HGRP HGBuffer
        // implementation and must never be admitted by the exact default path.
        Tags { "RenderType"="Opaque" "Queue"="Geometry" }
        Pass
        {
            Name "EndminfLitEffectVisualCompatibility"
            Tags { "LightMode"="ForwardOnly" }
            Cull Back
            ZWrite On
            ZTest LEqual
            Blend Off

            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex Vert
            #pragma fragment Frag
            #include "UnityCG.cginc"
            sampler2D _BaseColorMap; float4 _BaseColorMap_ST;
            sampler2D _MROMap;
            sampler2D _NormalMap;
            sampler2D _ParallaxMap;
            float4 _BaseColor;
            float4 _ParallaxColor;
            float _ParallaxIntensity;

            struct Attributes { float4 positionOS:POSITION; float3 normalOS:NORMAL; float4 tangentOS:TANGENT; float2 uv:TEXCOORD0; };
            struct Varyings { float4 positionCS:SV_POSITION; float2 uv:TEXCOORD0; float3 normalWS:TEXCOORD1; };
            Varyings Vert(Attributes input)
            {
                Varyings output;
                output.positionCS = UnityObjectToClipPos(input.positionOS);
                output.uv = TRANSFORM_TEX(input.uv, _BaseColorMap);
                output.normalWS = UnityObjectToWorldNormal(input.normalOS);
                return output;
            }
            float4 Frag(Varyings input):SV_Target
            {
                float4 baseSample = tex2D(_BaseColorMap, input.uv) * _BaseColor;
                float3 mro = tex2D(_MROMap, input.uv).rgb;
                float parallax = tex2D(_ParallaxMap, input.uv).r;
                float3 n = normalize(input.normalWS);
                float3 l = normalize(float3(-0.35, 0.8, 0.45));
                float diffuse = 0.22 + 0.78 * saturate(dot(n, l));
                float3 lit = baseSample.rgb * diffuse * lerp(0.65, 1.0, mro.b);
                float3 emission = _ParallaxColor.rgb * parallax * _ParallaxIntensity * 0.0125;
                return float4(lit + emission, baseSample.a);
            }
            ENDHLSL
        }
    }
}
