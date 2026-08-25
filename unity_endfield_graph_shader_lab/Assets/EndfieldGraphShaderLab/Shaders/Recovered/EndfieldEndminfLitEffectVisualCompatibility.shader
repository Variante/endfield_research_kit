Shader "Hidden/Endfield/Compatibility/Endminf/LitEffectParallax"
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
        _ParallaxStrength ("Recovered Parallax Strength", Float) = 0.096
        _ParallaxTilling ("Recovered Parallax Tiling", Float) = 3.36
        _ParallaxMarchNum ("Recovered Parallax March Count", Float) = 5
        _ParallaxMinBrightness ("Recovered Parallax Minimum Brightness", Float) = 0.2
        _RecoveredParallaxMarchCompatibility ("Recovered Parallax March Compatibility", Float) = 1
        // Presentation-domain calibration only. The retail fragment writes
        // HDR parallax radiance directly to SceneColor before deferred
        // lighting; this forward compatibility pass cannot reproduce the
        // unresolved _PARALLAX_MAP b3 extension/live deferred frame yet.
        _RecoveredParallaxCompatibilityScale ("Recovered Parallax Compatibility Scale", Float) = 0.0125
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
            float _RecoveredParallaxCompatibilityScale;

            struct Attributes { float4 positionOS:POSITION; float3 normalOS:NORMAL; float4 tangentOS:TANGENT; float2 uv:TEXCOORD0; };
            float _ParallaxStrength;
            float _ParallaxTilling;
            float _ParallaxMarchNum;
            float _ParallaxMinBrightness;
            float _RecoveredParallaxMarchCompatibility;

            struct Varyings
            {
                float4 positionCS:SV_POSITION;
                float2 uv:TEXCOORD0;
                float3 normalWS:TEXCOORD1;
                float4 tangentWS:TEXCOORD2;
                float3 positionWS:TEXCOORD3;
            };
            Varyings Vert(Attributes input)
            {
                Varyings output;
                output.positionCS = UnityObjectToClipPos(input.positionOS);
                output.uv = TRANSFORM_TEX(input.uv, _BaseColorMap);
                output.normalWS = UnityObjectToWorldNormal(input.normalOS);
                output.tangentWS = float4(
                    UnityObjectToWorldDir(input.tangentOS.xyz),
                    input.tangentOS.w * unity_WorldTransformParams.w);
                output.positionWS = mul(unity_ObjectToWorld, input.positionOS).xyz;
                return output;
            }
            float4 Frag(Varyings input):SV_Target
            {
                float4 baseSample = tex2D(_BaseColorMap, input.uv) * _BaseColor;
                float3 mro = tex2D(_MROMap, input.uv).rgb;
                // The exact HGBuffer variant consumes NORMAL and TANGENT and
                // the selected source materials bind _NormalMap with
                // _NormalScale=1.
                float3 geometricNormal = normalize(input.normalWS);
                float3 tangent = normalize(input.tangentWS.xyz);
                float3 bitangent = normalize(cross(geometricNormal, tangent)) *
                    input.tangentWS.w;
                float3 normalTS = UnpackNormal(tex2D(_NormalMap, input.uv));
                float3 n = normalize(
                    tangent * normalTS.x + bitangent * normalTS.y +
                    geometricNormal * normalTS.z);
                // The verified _PARALLAX_MAP fragment advances through the
                // texture in tangent-view space. M01/M38 author five steps,
                // strength 0.096 and tiling 3.36. This bounded forward port
                // restores that orientation-dependent internal pattern while
                // leaving the unresolved parallax-CB and live-frame contract explicit.
                float3 viewWS = normalize(_WorldSpaceCameraPos.xyz - input.positionWS);
                float3 viewTS = float3(
                    dot(viewWS, tangent),
                    dot(viewWS, bitangent),
                    dot(viewWS, geometricNormal));
                const int parallaxSteps = 5;
                float layerStep = 1.0 / parallaxSteps;
                float2 parallaxDelta =
                    (viewTS.xy / max(abs(viewTS.z), 0.08)) *
                    (_ParallaxStrength / parallaxSteps);
                float directParallax = tex2D(_ParallaxMap, input.uv).r;
                float2 parallaxUV = input.uv * _ParallaxTilling;
                float layerDepth = 0.0;
                float parallax = tex2D(_ParallaxMap, parallaxUV).r;
                [unroll]
                for (int stepIndex = 0; stepIndex < parallaxSteps; ++stepIndex)
                {
                    float advance = step(layerDepth, 1.0 - parallax);
                    parallaxUV -= parallaxDelta * advance;
                    layerDepth += layerStep * advance;
                    parallax = tex2D(_ParallaxMap, parallaxUV).r;
                }
                parallax = lerp(
                    directParallax,
                    max(parallax, _ParallaxMinBrightness),
                    saturate(_RecoveredParallaxMarchCompatibility));
                float3 l = normalize(float3(-0.35, 0.8, 0.45));
                float diffuse = 0.22 + 0.78 * saturate(dot(n, l));
                float3 lit = baseSample.rgb * diffuse * lerp(0.65, 1.0, mro.b);
                float3 emission = _ParallaxColor.rgb * parallax *
                    _ParallaxIntensity * _RecoveredParallaxCompatibilityScale;
                return float4(lit + emission, baseSample.a);
            }
            ENDHLSL
        }
    }
}
