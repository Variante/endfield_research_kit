Shader "Endfield/Recovered/VFXBaseV2SampleStack"
{
    Properties
    {
        _MainTex ("Main Texture", 2D) = "white" {}
        _SampleTex0 ("Sample 0 (Disturb 1)", 2D) = "gray" {}
        _SampleTex1 ("Sample 1 (Mask)", 2D) = "white" {}
        _SampleTex2 ("Sample 2 (Dissolve or Blend)", 2D) = "white" {}
        _SampleTex3 ("Sample 3 (Dissolve)", 2D) = "white" {}

        [HDR] _TintColor ("Tint Color", Color) = (1,1,1,1)
        _TintColorIntensity ("Tint Intensity", Float) = 1
        _TintColorAlpha ("Tint Alpha", Float) = 1
        _ExpThreshold ("Exposure Threshold", Float) = 1
        _ExpIntensity ("Exposure Intensity", Float) = 0
        _ProcedureAlpha ("Procedure Alpha", Float) = 1
        _UseMainTexAsAlpha ("Use Main Red As Alpha", Float) = 1
        _MainTexUseDisturb ("Disturb Main Texture", Float) = 0

        _MainTexUVSpeed ("Main UV Speed", Vector) = (0,0,0,0)
        _MainTexUVRotateMat ("Main UV Rotation Matrix", Vector) = (1,0,0,1)
        _MainTexUVWeights ("Main UV Weights", Vector) = (1,0,0,0)
        _SampleTex0UVSpeed ("Sample 0 UV Speed", Vector) = (0,0,0,0)
        _SampleTex0UVRotateMat ("Sample 0 UV Rotation Matrix", Vector) = (1,0,0,1)
        _SampleTex0UVWeights ("Sample 0 UV Weights", Vector) = (1,0,0,0)
        _SampleTex1UVSpeed ("Sample 1 UV Speed", Vector) = (0,0,0,0)
        _SampleTex1UVRotateMat ("Sample 1 UV Rotation Matrix", Vector) = (1,0,0,1)
        _SampleTex1UVWeights ("Sample 1 UV Weights", Vector) = (1,0,0,0)
        _SampleTex2UVSpeed ("Sample 2 UV Speed", Vector) = (0,0,0,0)
        _SampleTex2UVRotateMat ("Sample 2 UV Rotation Matrix", Vector) = (1,0,0,1)
        _SampleTex2UVWeights ("Sample 2 UV Weights", Vector) = (1,0,0,0)
        _SampleTex3UVSpeed ("Sample 3 UV Speed", Vector) = (0,0,0,0)
        _SampleTex3UVRotateMat ("Sample 3 UV Rotation Matrix", Vector) = (1,0,0,1)
        _SampleTex3UVWeights ("Sample 3 UV Weights", Vector) = (1,0,0,0)

        _UseSampleTex0AsAlpha ("Sample 0 Uses Red As Alpha", Float) = 0
        _UseSampleTex1AsAlpha ("Sample 1 Uses Red As Alpha", Float) = 1
        _UseSampleTex2AsAlpha ("Sample 2 Uses Red As Alpha", Float) = 0
        _UseSampleTex3AsAlpha ("Sample 3 Uses Red As Alpha", Float) = 0
        _DisturbTex1Normal ("Sample 0 Is Normal Disturbance", Float) = 0
        _DisturbUIntensity1 ("Disturb U Intensity", Float) = 0
        _DisturbVIntensity1 ("Disturb V Intensity", Float) = 0
        _UseMask ("Use Mask", Float) = 1
        _UseBlend ("Use Blend", Float) = 0
        [HDR] _BlendTint ("Blend Tint", Color) = (1,1,1,1)
        _UseDissolve ("Use Dissolve", Float) = 1
        _DissolveScheduleOffset ("Dissolve Schedule Offset", Float) = 0
        _DissolveEdgeSharp ("Dissolve Edge Sharpness", Float) = 0.5
        _DissolveEmissiveEdge ("Dissolve Emissive Edge", Float) = 0.2
        [HDR] _DissolveEmissiveColor ("Dissolve Emissive Color", Color) = (0,0,0,0)
        [Toggle(_USE_FRESNEL)] _UseFresnel ("Use Fresnel", Float) = 0
        [HDR] _FresnelColor ("Fresnel Color", Color) = (1,1,1,1)
        _FresnelBias ("Fresnel Bias", Float) = 0
        _FresnelAffectOpacity ("Fresnel Affect Opacity", Float) = 1
        _FresnelPower ("Fresnel Power", Float) = 1
        _FresnelFlip ("Fresnel Flip", Float) = 0.001
        _UseSoftBlend ("Use Soft Blend", Float) = 0
        _SoftDistance ("Soft Distance", Float) = 0.001
        _SoftBias ("Soft Bias", Float) = 0

        _BlendMode ("Original Blend Mode", Float) = 0
        [HideInInspector] _SurfaceType ("Original Surface Type", Float) = 1
        [HideInInspector] _Responsive ("Original Responsive Mask", Float) = 1
        _IsSceneEffect ("Original Scene Effect Gate", Float) = 0
        _IgnorePostExposure ("Ignore Post Exposure", Float) = 1
        [HideInInspector] _VFXParams1 ("Original VFX Params 1", Vector) = (1,1,1,1)
        [HideInInspector] _RecoveredLODFade ("Recovered LOD Fade", Vector) = (1000,0,0,0)
        [HideInInspector] _SrcBlend ("Source Blend", Float) = 1
        [HideInInspector] _DstBlend ("Destination Blend", Float) = 10
        [HideInInspector] _AlphaSrcBlend ("Alpha Source Blend", Float) = 1
        [HideInInspector] _AlphaDstBlend ("Alpha Destination Blend", Float) = 10
        [HideInInspector] _MVSrcColorBlend ("MV Source Color Blend", Float) = 3
        [HideInInspector] _MVDstColorBlend ("MV Destination Color Blend", Float) = 6
        [HideInInspector] _ZTest ("Z Test", Float) = 4
        [HideInInspector] _ZWrite ("Z Write", Float) = 0
        [HideInInspector] _CullMode ("Cull", Float) = 2
    }

    SubShader
    {
        Tags
        {
            "Queue"="Transparent+700"
            "RenderType"="Transparent"
            "EndfieldSceneMVMRT"="ExactSelectedPiaodaiThree"
        }

        Pass
        {
            Name "ForwardOnly"
            Tags { "LightMode"="ForwardOnly" }
            Blend 0 [_SrcBlend] [_DstBlend], [_AlphaSrcBlend] [_AlphaDstBlend]
            Blend 1 [_MVSrcColorBlend] [_MVDstColorBlend], One One
            ColorMask RGBA 0
            ColorMask RGBA 1
            ZTest [_ZTest]
            ZWrite [_ZWrite]
            Cull [_CullMode]

            CGPROGRAM
            #pragma target 5.0
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma shader_feature_local_fragment _SAMPLE_TEX0
            #pragma shader_feature_local_fragment _SAMPLE_TEX1
            #pragma shader_feature_local_fragment _SAMPLE_TEX2
            #pragma shader_feature_local_fragment _SAMPLE_TEX3
            #pragma shader_feature_local_fragment _USE_FRESNEL
            #pragma shader_feature_local_fragment _USE_SOFTBLEND
            #include "UnityCG.cginc"

            sampler2D _MainTex;
            sampler2D _SampleTex0;
            sampler2D _SampleTex1;
            sampler2D _SampleTex2;
            sampler2D _SampleTex3;
            Texture2D<float> _CameraDepthTexture;
            // The Li Zhiyan _USE_SOFTBLEND DXBC variants bind the scene-depth
            // input with the static linear-clamp sampler (s0), not a material
            // texture sampler.
            SamplerState sampler_LinearClamp;
            float4 _MainTex_ST;
            float4 _SampleTex0_ST;
            float4 _SampleTex1_ST;
            float4 _SampleTex2_ST;
            float4 _SampleTex3_ST;
            float4 _CameraDepthTexture_TexelSize;

            float4 _TintColor;
            float _TintColorIntensity;
            float _TintColorAlpha;
            float _ExpThreshold;
            float _ExpIntensity;
            float _ProcedureAlpha;
            float _UseMainTexAsAlpha;
            float _MainTexUseDisturb;

            float4 _MainTexUVSpeed;
            float4 _MainTexUVRotateMat;
            float4 _MainTexUVWeights;
            float4 _SampleTex0UVSpeed;
            float4 _SampleTex0UVRotateMat;
            float4 _SampleTex0UVWeights;
            float4 _SampleTex1UVSpeed;
            float4 _SampleTex1UVRotateMat;
            float4 _SampleTex1UVWeights;
            float4 _SampleTex2UVSpeed;
            float4 _SampleTex2UVRotateMat;
            float4 _SampleTex2UVWeights;
            float4 _SampleTex3UVSpeed;
            float4 _SampleTex3UVRotateMat;
            float4 _SampleTex3UVWeights;

            float _UseSampleTex0AsAlpha;
            float _UseSampleTex1AsAlpha;
            float _UseSampleTex2AsAlpha;
            float _UseSampleTex3AsAlpha;
            float _DisturbTex1Normal;
            float _DisturbUIntensity1;
            float _DisturbVIntensity1;
            float _UseMask;
            float _UseBlend;
            float4 _BlendTint;
            float _UseDissolve;
            float _DissolveScheduleOffset;
            float _DissolveEdgeSharp;
            float _DissolveEmissiveEdge;
            float4 _DissolveEmissiveColor;
            float _UseFresnel;
            float4 _FresnelColor;
            float _FresnelBias;
            float _FresnelAffectOpacity;
            float _FresnelPower;
            float _FresnelFlip;
            float _UseSoftBlend;
            float _SoftDistance;
            float _SoftBias;
            float _BlendMode;
            float _SurfaceType;
            float _Responsive;
            float _IsSceneEffect;
            float _IgnorePostExposure;
            float _InParticle;
            float4 _VFXParams1;
            float4 _VFXParams0;
            float4 _ExposureWithMiscParams;
            float4 _RecoveredLODFade;
            float _EndfieldSceneMVMRTReady;
            float _EndfieldRecoveredVFXGlobalsReady;
            // Diagnostic-only admission gate. The authored soft-blend
            // keyword/property remain intact, but no depth read is allowed
            // until the capture binds the exact _CameraDepthTexture input.
            float _EndfieldRecoveredVFXSoftDepthReady;

            struct Attributes
            {
                float4 vertex : POSITION;
                float3 normal : NORMAL;
                float4 color : COLOR;
                // BakeMesh carries the source UV/UV2 pair in TEXCOORD0.xyzw
                // and ParticleSystemVertexStream.Custom1XYZW in TEXCOORD1.
                // Static start_01 meshes still use TEXCOORD1.xy as their
                // authored secondary UV when _InParticle is zero.
                float4 uv0 : TEXCOORD0;
                float4 custom : TEXCOORD1;
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 positionWS : TEXCOORD5;
                float3 normalWS : TEXCOORD6;
                float4 color : COLOR;
                float2 mainUV : TEXCOORD0;
                float2 sample0UV : TEXCOORD1;
                float2 sample1UV : TEXCOORD2;
                float2 sample2UV : TEXCOORD3;
                float2 sample3UV : TEXCOORD4;
            };

            struct FragmentOutput
            {
                float4 color : SV_Target0;
                float4 sceneMV : SV_Target1;
            };

            float2 BuildSelectedUV(
                float4 uv0,
                float4 custom,
                float4 weights,
                float4 speed,
                float4 rotateMat,
                float4 textureST)
            {
                // Retail VFXBaseV2 selects mesh UV1 for static geometry and
                // the UV2 lane packed in UV0.zw for particles. Its particle
                // path also advances UV by speed.zw * Custom1.X; this is the
                // authored Custom1XYZW stream (renderer stream 34), not a
                // second ordinary UV. Keep the static lane unchanged.
                float2 secondaryUV = lerp(custom.xy, uv0.zw, _InParticle);
                float2 uv = uv0.xy * weights.x + secondaryUV * weights.y;
                float2 centered = uv + speed.xy * _VFXParams0.w +
                    speed.zw * (custom.x * _InParticle) - 0.5;
                float2 rotated = float2(
                    dot(centered, rotateMat.xz),
                    dot(centered, rotateMat.yw)) + 0.5;
                return rotated * textureST.xy + textureST.zw;
            }

            Varyings Vert(Attributes input)
            {
                Varyings output;
                output.positionCS = UnityObjectToClipPos(input.vertex);
                output.positionWS = mul(unity_ObjectToWorld, input.vertex).xyz;
                output.normalWS = UnityObjectToWorldNormal(input.normal);
                output.color = input.color;
                output.mainUV = BuildSelectedUV(
                    input.uv0, input.custom, _MainTexUVWeights,
                    _MainTexUVSpeed, _MainTexUVRotateMat, _MainTex_ST);
                output.sample0UV = BuildSelectedUV(
                    input.uv0, input.custom, _SampleTex0UVWeights,
                    _SampleTex0UVSpeed, _SampleTex0UVRotateMat, _SampleTex0_ST);
                output.sample1UV = BuildSelectedUV(
                    input.uv0, input.custom, _SampleTex1UVWeights,
                    _SampleTex1UVSpeed, _SampleTex1UVRotateMat, _SampleTex1_ST);
                output.sample2UV = BuildSelectedUV(
                    input.uv0, input.custom, _SampleTex2UVWeights,
                    _SampleTex2UVSpeed, _SampleTex2UVRotateMat, _SampleTex2_ST);
                output.sample3UV = BuildSelectedUV(
                    input.uv0, input.custom, _SampleTex3UVWeights,
                    _SampleTex3UVSpeed, _SampleTex3UVRotateMat, _SampleTex3_ST);
                return output;
            }

            float SampleAlphaCarrier(float4 sampleValue, float useRedAsAlpha)
            {
                return lerp(sampleValue.a, sampleValue.r, saturate(useRedAsAlpha));
            }

            float3 SampleColorCarrier(float4 sampleValue, float useRedAsAlpha)
            {
                return lerp(sampleValue.rgb, 1.0.xxx, saturate(useRedAsAlpha));
            }

            FragmentOutput Frag(Varyings input)
            {
                clip(min(_EndfieldSceneMVMRTReady,
                    _EndfieldRecoveredVFXGlobalsReady) - 0.5);

                float4 sample0 = tex2D(_SampleTex0, input.sample0UV);
                float4 sample1 = tex2D(_SampleTex1, input.sample1UV);
                float4 sample2 = tex2D(_SampleTex2, input.sample2UV);

                // In all three source materials SampleTex0 routes to Disturb1.
                // The selected fragment uses R*A and G for its signed normal
                // branch, but repeats R across the scalar U/V branch.
                float2 signedDisturb = float2(
                    sample0.r * sample0.a * 2.0 - 1.0,
                    sample0.g * 2.0 - 1.0);
                float2 scalarDisturb = sample0.rr;
                float2 disturb = lerp(
                    scalarDisturb * float2(_DisturbUIntensity1, _DisturbVIntensity1),
                    signedDisturb * _DisturbUIntensity1,
                    saturate(_DisturbTex1Normal));

                float2 mainUV = input.mainUV + disturb * saturate(_MainTexUseDisturb);
                float4 mainSample = tex2D(_MainTex, mainUV);
                float mainAlpha = SampleAlphaCarrier(mainSample, _UseMainTexAsAlpha);
                float3 mainColor = SampleColorCarrier(mainSample, _UseMainTexAsAlpha);

                // SampleTex1 is the exact Mask route for all three materials.
                float mask = lerp(
                    1.0,
                    SampleAlphaCarrier(sample1, _UseSampleTex1AsAlpha),
                    saturate(_UseMask));

                #if defined(_SAMPLE_TEX3)
                    // Four-sample material 03 routes SampleTex2 to Blend and
                    // SampleTex3 to Dissolve.
                    float3 blendCarrier = SampleColorCarrier(
                        sample2, _UseSampleTex2AsAlpha);
                    float4 dissolveSample = tex2D(_SampleTex3, input.sample3UV);
                    // The selected original bytecode consumes the route's red
                    // component when UseAsAlpha=0. Material 03 serializes that
                    // exact state.
                    float dissolveCarrier = dissolveSample.r;
                #else
                    // Three-sample materials 01/02 route SampleTex2 directly
                    // to Dissolve and carry no selected Blend texture.
                    float3 blendCarrier = 0.0.xxx;
                    // Materials 01/02 serialize UseAsAlpha=0, making red the
                    // exact original dissolve carrier.
                    float dissolveCarrier = sample2.r;
                #endif

                float3 untinted = mainColor * _TintColor.rgb * _TintColorIntensity;
                untinted += blendCarrier * _BlendTint.rgb * saturate(_UseBlend);

                // Exact identity-gated serialized specialization of the
                // selected ForwardOnly DXBC. All three piaodai materials set
                // _InParticle=0, _DissolveUseWeight=0, and schedule offset=0,
                // collapsing the private remap to -1.01.
                float dissolveScheduleRemap = -1.01;
                float dissolveDelta = dissolveCarrier - dissolveScheduleRemap;
                float dissolveAlpha = saturate(
                    dissolveDelta * _DissolveEdgeSharp);
                float dissolveEdge = saturate(
                    (_DissolveEmissiveEdge - dissolveDelta) *
                    _DissolveEdgeSharp);
                float dissolveEnabled = saturate(_UseDissolve);
                float3 dissolveColor = lerp(
                    untinted,
                    dissolveEdge * _DissolveEmissiveColor.rgb * _TintColorIntensity,
                    dissolveEdge);
                untinted = lerp(untinted, dissolveColor, dissolveEnabled);

                float exposureDivisor = lerp(
                    1.0,
                    max(_ExposureWithMiscParams.y, 0.0001),
                    saturate(_IgnorePostExposure));
                float3 color = untinted / exposureDivisor;
#if defined(_USE_FRESNEL)
                // Exact recovered VFXBaseV2 Fresnel branch: powered biased
                // N.V, optional flip, color interpolation, and authored
                // opacity multiplier. M23 is visible at PTS40000 and carries
                // this keyword/property payload.
                float3 viewDirectionWS = normalize(
                    _WorldSpaceCameraPos.xyz - input.positionWS);
                float biasedNdotV = saturate(
                    dot(viewDirectionWS, normalize(input.normalWS)) +
                    _FresnelBias);
                float poweredFresnel = pow(biasedNdotV, _FresnelPower);
                float fresnel = lerp(
                    1.0 - poweredFresnel,
                    poweredFresnel,
                    _FresnelFlip);
                color = lerp(
                    color,
                    _FresnelColor.rgb,
                    fresnel * _FresnelColor.a);
#else
                float fresnel = 1.0;
#endif
                color += max(color - _ExpThreshold, 0.0) * _ExpIntensity;
                color = clamp(color, 0.0, 1000.0);

                float alpha = saturate(
                    mainAlpha * _TintColor.a * _TintColorAlpha *
                    input.color.a * mask);
                alpha *= lerp(1.0, dissolveAlpha, dissolveEnabled);
#if defined(_USE_FRESNEL)
                alpha *= lerp(1.0, fresnel, _FresnelAffectOpacity);
#endif
#if defined(_USE_SOFTBLEND)
                // Exact BaseV2 soft-blend path recovered from the shipped
                // ForwardOnly blob: sample continuous pixel UV, linearize
                // scene and particle depth, then apply the authored bias and
                // distance. The extra readiness gate is diagnostic-only and
                // keeps normal assets fail-closed when _CameraDepthTexture is absent.
                if (_EndfieldRecoveredVFXSoftDepthReady > 0.5 &&
                    _SoftDistance > 0.0)
                {
                    float2 particlePixelUV = input.positionCS.xy *
                        _CameraDepthTexture_TexelSize.xy;
                    float sceneRawDepth = _CameraDepthTexture.SampleLevel(
                        sampler_LinearClamp, particlePixelUV, 0.0);
                    float sceneAbsoluteViewZ =
                        LinearEyeDepth(sceneRawDepth);
                    float particleAbsoluteViewZ =
                        LinearEyeDepth(input.positionCS.z);
                    alpha *= saturate((
                        sceneAbsoluteViewZ - particleAbsoluteViewZ +
                        _SoftBias) / _SoftDistance);
                }
#endif
                alpha = lerp(1.0, alpha, saturate(_ProcedureAlpha));

                // The selected non-instanced retail SPIR-V reads
                // PerDrawBaseData.lodFade.xy directly at set 2/binding 0,
                // member byte offset 64. The selected source material carries
                // the retail disabled value (1000,0,0,0).
                float positionHash = frac(frac(dot(input.positionCS.xy,
                    float2(0.0671105608344078, 0.00583714991807938))) *
                    52.98291778564453);
                float signedHash = _RecoveredLODFade.x >= 0.0
                    ? positionHash
                    : -positionHash;
                float ditherPass = _RecoveredLODFade.x - signedHash > 0.0
                    ? 1.0
                    : 1.0 - _SurfaceType;
                float coverage = ditherPass *
                    ((1.0 - _RecoveredLODFade.y) * alpha);

                // Exact selected ForwardOnly equations: Alpha mode writes
                // premultiplied RGB + alpha; Additive mode writes the same
                // premultiplied RGB but forces alpha to zero. Multiply mode is
                // retained only as the bytecode's closed third branch.
                float isMultiply = step(1.5, _BlendMode);
                float3 premultiplied = lerp(
                    color * coverage,
                    lerp(1.0.xxx, color, coverage),
                    isMultiply);
                float outputAlpha = coverage * (1.0 - saturate(_BlendMode));

                float luminance = dot(
                    premultiplied,
                    float3(0.2126729041, 0.7151522040, 0.0721750036));
                float3 vfxAdjusted = lerp(
                    luminance.xxx,
                    premultiplied,
                    _VFXParams1.w) * _VFXParams1.xyz;
                float3 finalColor = lerp(
                    premultiplied,
                    vfxAdjusted,
                    saturate(_IsSceneEffect));
                float coverageLuma = dot(
                    color,
                    float3(0.2126729041, 0.7151522040, 0.0721750036));
                float activeMask = step(
                    0.5,
                    saturate(max(
                        outputAlpha,
                        coverage * coverageLuma) * 10.0)) *
                    _SurfaceType * _Responsive;

                FragmentOutput output;
                output.color = float4(finalColor, outputAlpha);
                output.sceneMV = float4(0.0, 0.0, 1.0, activeMask);
                return output;
            }
            ENDCG
        }
    }
    Fallback Off
}
