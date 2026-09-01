Shader "Hidden/Endfield/Compatibility/Endminf/LitEffectParallax"
{
    Properties
    {
        _BaseColorMap ("Recovered Base Color Map", 2D) = "white" {}
        _BaseColor ("Recovered Base Color", Color) = (1,1,1,1)
        _BaseColorTintCover ("Recovered Base Color Tint Cover", Float) = 0
        _BaseColorBrighterScale ("Recovered Base Color Brighter Scale", Float) = 1
        _MROMap ("Recovered MRO Map", 2D) = "white" {}
        _NormalMap ("Recovered Normal Map", 2D) = "bump" {}
        _ParallaxMap ("Recovered Parallax Map", 2D) = "black" {}
        [HideInInspector] _ParallaxNoiseMap ("Recovered Parallax Noise Map", 2D) = "black" {}
        _NormalScale ("Recovered Normal Scale", Float) = 1
        _TwoSidedNormal ("Recovered Two-Sided Normal", Float) = 1
        _RoughnessMin ("Recovered Roughness Minimum", Float) = 0
        _RoughnessMax ("Recovered Roughness Maximum", Float) = 1
        _OcclusionStrength ("Recovered Occlusion Strength", Float) = 1
        _Metallic ("Recovered Metallic", Float) = 0
        _BaseTextureMapCount ("Recovered Base Texture Map Count", Float) = 0
        _BaseUVSet ("Recovered Base UV Set", Float) = 0
        _BasePbrMapUVSet ("Recovered PBR UV Set", Float) = 0
        _ParallaxMapUVType ("Recovered Parallax UV Set", Float) = 0
        _ParallaxNoiseMapTilling ("Recovered Parallax Noise Tiling", Float) = 1
        [HDR] _ParallaxColor ("Recovered Parallax Color", Color) = (1,0.3,0.05,1)
        [HDR] _ParallaxColorDark ("Recovered Parallax Dark Color", Color) = (0,0,0,1)
        _ParallaxIntensity ("Recovered Parallax Intensity", Float) = 1
        _ParallaxFresnelStrength ("Recovered Parallax Fresnel Strength", Float) = 1
        _ParallaxStrength ("Recovered Parallax Strength", Float) = 0.096
        _ParallaxTilling ("Recovered Parallax Tiling", Float) = 3.36
        _ParallaxMarchNum ("Recovered Parallax March Count", Float) = 5
        _ParallaxMinBrightness ("Recovered Parallax Minimum Brightness", Float) = 0.2
        _RecoveredParallaxMarchCompatibility ("Recovered Parallax March Compatibility", Float) = 1
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
            Texture2D<float4> _BaseColorMap; float4 _BaseColorMap_ST;
            Texture2D<float4> _NormalMap; float4 _NormalMap_ST;
            Texture2D<float4> _MROMap;
            Texture2D<float4> _ParallaxMap;
            Texture2D<float4> _ParallaxNoiseMap;

            // Physical source pairing recovered from PackedBinding and the
            // pinned _PARALLAX_MAP fragment: t0/s0 Base/LinearClamp,
            // t1/s1 Normal/LinearRepeat, t2/s2 MRO/LinearMirror,
            // t3/s3 Parallax/LinearMirrorOnce and t5/s5 Noise/PointRepeat.
            SamplerState sampler_LinearClamp;
            SamplerState sampler_LinearRepeat;
            SamplerState sampler_LinearMirror;
            SamplerState sampler_LinearMirrorOnce;
            SamplerState sampler_PointRepeat;
            float4 _BaseColor;
            float _BaseColorTintCover;
            float _BaseColorBrighterScale;
            float4 _ParallaxColor;
            float4 _ParallaxColorDark;
            float _ParallaxIntensity;
            float _NormalScale;
            float _TwoSidedNormal;
            float _RoughnessMin;
            float _RoughnessMax;
            float _OcclusionStrength;
            float _Metallic;
            float _BaseTextureMapCount;
            float _BaseUVSet;
            float _BasePbrMapUVSet;
            float _ParallaxMapUVType;
            float _ParallaxNoiseMapTilling;
            float _ParallaxFresnelStrength;
            float _GlobalMipBias;
            float _GlobalMipBiasPow2;

            struct Attributes
            {
                float4 positionOS:POSITION;
                float3 normalOS:NORMAL;
                float4 tangentOS:TANGENT;
                float2 uv0:TEXCOORD0;
                float2 uv1:TEXCOORD1;
            };
            float _ParallaxStrength;
            float _ParallaxTilling;
            float _ParallaxMarchNum;
            float _ParallaxMinBrightness;
            float _RecoveredParallaxMarchCompatibility;

            struct Varyings
            {
                float4 positionCS:SV_POSITION;
                float2 uv0:TEXCOORD0;
                float2 uv1:TEXCOORD1;
                float3 normalWS:TEXCOORD2;
                float4 tangentWS:TEXCOORD3;
                float3 positionWS:TEXCOORD4;
            };
            Varyings Vert(Attributes input)
            {
                Varyings output;
                output.positionCS = UnityObjectToClipPos(input.positionOS);
                output.uv0 = input.uv0;
                output.uv1 = input.uv1;
                output.normalWS = UnityObjectToWorldNormal(input.normalOS);
                output.tangentWS = float4(
                    UnityObjectToWorldDir(input.tangentOS.xyz),
                    input.tangentOS.w * unity_WorldTransformParams.w);
                output.positionWS = mul(unity_ObjectToWorld, input.positionOS).xyz;
                return output;
            }
            float4 Frag(
                Varyings input,
                bool isFrontFace : SV_IsFrontFace):SV_Target
            {
                float2 baseUV = lerp(input.uv0, input.uv1, _BaseUVSet) *
                    _BaseColorMap_ST.xy + _BaseColorMap_ST.zw;
                float2 pbrUV = lerp(input.uv0, input.uv1, _BasePbrMapUVSet) *
                    _NormalMap_ST.xy + _NormalMap_ST.zw;
                float4 baseSample = _BaseColorMap.SampleBias(
                    sampler_LinearClamp, baseUV, _GlobalMipBias);
                float4 normalSample = _NormalMap.SampleBias(
                    sampler_LinearRepeat, pbrUV, _GlobalMipBias);
                float3 mro = _MROMap.SampleBias(
                    sampler_LinearMirror, pbrUV, _GlobalMipBias).rgb;
                // Preserve the selected retail b3 base-color subgraph before
                // the explicitly non-exact forward light model consumes it.
                float3 sourceBaseColor = lerp(
                    saturate(
                        baseSample.rgb * _BaseColor.rgb *
                        _BaseColorBrighterScale),
                    _BaseColor.rgb,
                    _BaseColorTintCover);
                // The exact HGBuffer variant consumes NORMAL and TANGENT and
                // the selected source materials bind _NormalMap with
                // _NormalScale=1.
                float3 geometricNormal = normalize(input.normalWS);
                float3 tangent = normalize(input.tangentWS.xyz);
                float3 bitangent = normalize(cross(geometricNormal, tangent)) *
                    input.tangentWS.w;
                float2 normalXY = float2(
                    normalSample.r * normalSample.a,
                    normalSample.g) * 2.0 - 1.0;
                float normalZ = max(
                    sqrt(1.0 - min(dot(normalXY, normalXY), 1.0)),
                    1.0000000168623835e-16);
                if (_TwoSidedNormal > 0.0 && !isFrontFace)
                    normalZ = -normalZ;
                float3 normalTS = float3(
                    normalXY * _NormalScale,
                    normalZ);
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
                uint parallaxSteps = min((uint)_ParallaxMarchNum, 20u);
                float layerStep = rcp((float)parallaxSteps);
                float inverseViewLength = rsqrt(dot(viewTS, viewTS));
                float normalizedViewZ = viewTS.z * inverseViewLength;
                float rayDenominator = normalizedViewZ +
                    0.41999998688697815;
                float safeViewZ = max(
                    normalizedViewZ,
                    0.0010000000474974513);
                float2 rayDelta =
                    ((viewTS.xy * inverseViewLength) / rayDenominator) /
                    safeViewZ * (-_ParallaxStrength);
                float2 rayStep = rayDelta * layerStep;
                float2 parallaxBaseUV = lerp(
                    input.uv0, input.uv1, _ParallaxMapUVType);
                float2 previousRayOffset = 0.0;
                float previousHeight = 0.0;
                float previousLayer = 1.0;
                float layer = 1.0 - layerStep;
                float2 rayOffset = rayStep;
                float hitHeight = 0.0;
                // The retail fragment multiplies coarse derivatives by the
                // live ShaderVariablesGlobal mip-bias power. Do not replace
                // this with the formerly captured 0.5 scalar.
                float2 noiseDx =
                    ddx_coarse(input.uv0) * _GlobalMipBiasPow2;
                float2 noiseDy =
                    ddy_coarse(input.uv0) * _GlobalMipBiasPow2;
                [loop]
                for (uint stepIndex = 0u;
                     stepIndex < parallaxSteps + 1u;
                     ++stepIndex)
                {
                    float sampledHeight = _ParallaxNoiseMap.SampleGrad(
                        sampler_PointRepeat,
                        parallaxBaseUV * _ParallaxNoiseMapTilling +
                            rayOffset,
                        noiseDx,
                        noiseDy).r;
                    if (layer < sampledHeight)
                    {
                        hitHeight = sampledHeight;
                        break;
                    }
                    previousRayOffset = rayOffset;
                    previousHeight = sampledHeight;
                    previousLayer = layer;
                    rayOffset += rayStep;
                    layer -= layerStep;
                    hitHeight = previousHeight;
                }
                float intersection =
                    (previousHeight - previousLayer) /
                    ((layer + previousHeight - hitHeight) - previousLayer);
                float2 marchedUV =
                    (parallaxBaseUV + rayStep * intersection +
                        previousRayOffset) * _ParallaxTilling;
                float2 directUV = parallaxBaseUV * _ParallaxTilling;
                float2 parallaxUV = lerp(
                    directUV,
                    marchedUV,
                    saturate(_RecoveredParallaxMarchCompatibility));
                float parallax = _ParallaxMap.SampleBias(
                    sampler_LinearMirrorOnce,
                    parallaxUV,
                    _GlobalMipBias).g;
                float3 l = normalize(float3(-0.35, 0.8, 0.45));
                float3 h = normalize(l + viewWS);
                float ndl = saturate(dot(n, l));
                float ndv = saturate(dot(n, viewWS));
                float ndh = saturate(dot(n, h));
                float vdh = saturate(dot(viewWS, h));
                // Source MRO packing is R=metallic, G=roughness,
                // B=occlusion. The previous compatibility port had R/G
                // swapped, materially changing every stone face.
                float sourceMetallic = lerp(
                    mro.r,
                    _Metallic,
                    saturate(_BaseTextureMapCount - 1.0));
                float sourceRoughness = lerp(
                    _RoughnessMin,
                    _RoughnessMax,
                    mro.g);
                float sourceOcclusion = mad(
                    _OcclusionStrength,
                    mro.b - 1.0,
                    1.0);
                // These bounds belong only to the fallback GGX evaluation;
                // sourceMetallic/sourceRoughness/sourceOcclusion above retain
                // the exact HGBuffer material decode.
                float metallic = saturate(sourceMetallic);
                float roughness = clamp(sourceRoughness, 0.06, 1.0);
                float occlusion = saturate(sourceOcclusion);
                float alphaRoughness = roughness * roughness;
                float alphaRoughness2 = alphaRoughness * alphaRoughness;
                float denominator = ndh * ndh * (alphaRoughness2 - 1.0) + 1.0;
                float distribution = alphaRoughness2 /
                    max(UNITY_PI * denominator * denominator, 0.001);
                float geometryK = (roughness + 1.0) * (roughness + 1.0) * 0.125;
                float geometryV = ndv / max(ndv * (1.0 - geometryK) + geometryK, 0.001);
                float geometryL = ndl / max(ndl * (1.0 - geometryK) + geometryK, 0.001);
                float3 f0 = lerp(0.04.xxx, sourceBaseColor, metallic);
                float3 fresnel = f0 + (1.0 - f0) * pow(1.0 - vdh, 5.0);
                float3 specular = distribution * geometryV * geometryL * fresnel * ndl;
                float3 diffuse = sourceBaseColor * (1.0 - metallic) *
                    (0.14 * occlusion + 0.86 * ndl) / UNITY_PI;
                float3 lit = diffuse + specular;
                float fresnelGate = pow(
                    max(ndv, 0.0010000000474974513),
                    floor(_ParallaxFresnelStrength));
                float3 parallaxColor = lerp(
                    _ParallaxColorDark.rgb,
                    _ParallaxColor.rgb,
                    parallax);
                // Preserve the recovered source HDR term. Presentation is
                // still explicitly non-exact because this pass has no retail
                // HGBuffer/SceneColor/deferred consumer.
                float3 emission = clamp(
                    parallaxColor * (baseSample.a * baseSample.a) *
                        fresnelGate,
                    0.0,
                    1000.0) * _ParallaxIntensity;
                return float4(lit + emission, baseSample.a);
            }
            ENDHLSL
        }
    }
}
