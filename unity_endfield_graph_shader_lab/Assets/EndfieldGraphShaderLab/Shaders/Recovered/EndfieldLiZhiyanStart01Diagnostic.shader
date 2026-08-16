Shader "Endfield/Recovered/LiZhiyanStart01Diagnostic"
{
    Properties
    {
        // This is a diagnostic material selector, not a retail shader
        // keyword/variant identity.  09/10 use the three-slot route and 11
        // uses the four-slot route proven by the serialized material payloads.
        [HideInInspector] _LiMaterialMode ("Li Material Mode (09/10/11)", Float) = 11

        _MainTex ("Main Texture", 2D) = "white" {}
        _DisturbTex1 ("Disturb Texture 1", 2D) = "gray" {}
        _MaskTex ("Mask Texture", 2D) = "white" {}
        _BlendTex ("Blend Texture", 2D) = "white" {}
        _DissolveTex ("Dissolve Texture", 2D) = "white" {}

        // Keep the serialized SampleTex environments addressable for source
        // inspection.  The fragment route intentionally samples the named
        // source aliases above so 09/10 cannot silently become 11's route.
        [HideInInspector] _SampleTex0 ("Serialized Sample 0", 2D) = "white" {}
        [HideInInspector] _SampleTex1 ("Serialized Sample 1", 2D) = "white" {}
        [HideInInspector] _SampleTex2 ("Serialized Sample 2", 2D) = "white" {}
        [HideInInspector] _SampleTex3 ("Serialized Sample 3", 2D) = "white" {}

        [HDR] _TintColor ("Tint Color", Color) = (1,1,1,1)
        _TintColorIntensity ("Tint Intensity", Float) = 1
        _TintColorAlpha ("Tint Alpha", Float) = 1
        _ExpThreshold ("Exposure Threshold", Float) = 1
        _ExpIntensity ("Exposure Intensity", Float) = 0
        _ProcedureAlpha ("Procedure Alpha", Float) = 1
        _UseMainTexAsAlpha ("Use Main Red As Alpha", Float) = 1
        _MainTexUseDisturb ("Disturb Main Texture", Float) = 0

        // Color is used deliberately: the source contract stores these
        // float4 lanes in m_Colors and the importer can apply them losslessly.
        [HideInInspector] _MainTexUVSpeed ("Main UV Speed", Color) = (0,0,0,0)
        [HideInInspector] _MainTexUVRotateMat ("Main UV Rotation", Color) = (1,0,0,1)
        [HideInInspector] _MainTexUVWeights ("Main UV Weights", Color) = (1,0,0,0)
        [HideInInspector] _SampleTex0UVSpeed ("Sample 0 UV Speed", Color) = (0,0,0,0)
        [HideInInspector] _SampleTex0UVRotateMat ("Sample 0 UV Rotation", Color) = (1,0,0,1)
        [HideInInspector] _SampleTex0UVWeights ("Sample 0 UV Weights", Color) = (1,0,0,0)
        [HideInInspector] _SampleTex1UVSpeed ("Sample 1 UV Speed", Color) = (0,0,0,0)
        [HideInInspector] _SampleTex1UVRotateMat ("Sample 1 UV Rotation", Color) = (1,0,0,1)
        [HideInInspector] _SampleTex1UVWeights ("Sample 1 UV Weights", Color) = (1,0,0,0)
        [HideInInspector] _SampleTex2UVSpeed ("Sample 2 UV Speed", Color) = (0,0,0,0)
        [HideInInspector] _SampleTex2UVRotateMat ("Sample 2 UV Rotation", Color) = (1,0,0,1)
        [HideInInspector] _SampleTex2UVWeights ("Sample 2 UV Weights", Color) = (1,0,0,0)
        [HideInInspector] _SampleTex3UVSpeed ("Sample 3 UV Speed", Color) = (0,0,0,0)
        [HideInInspector] _SampleTex3UVRotateMat ("Sample 3 UV Rotation", Color) = (1,0,0,1)
        [HideInInspector] _SampleTex3UVWeights ("Sample 3 UV Weights", Color) = (1,0,0,0)

        // Named source alias speeds are unsupported by the generic stack but
        // are useful for a deterministic diagnostic capture.
        [HideInInspector] _DisturbUVSpeed1 ("Disturb 1 UV Speed", Color) = (0,0,0,0)
        [HideInInspector] _MaskTexUVSpeed ("Mask UV Speed", Color) = (0,0,0,0)
        [HideInInspector] _BlendTexUVSpeed ("Blend UV Speed", Color) = (0,0,0,0)
        [HideInInspector] _DissolveUVSpeed ("Dissolve UV Speed", Color) = (0,0,0,0)

        _UseSampleTex0AsAlpha ("Sample 0 Red As Alpha", Float) = 0
        _UseSampleTex1AsAlpha ("Sample 1 Red As Alpha", Float) = 1
        _UseSampleTex2AsAlpha ("Sample 2 Red As Alpha", Float) = 0
        _UseSampleTex3AsAlpha ("Sample 3 Red As Alpha", Float) = 0
        _DisturbTex1Normal ("Disturb Is Signed Normal", Float) = 0
        _DisturbUIntensity1 ("Disturb U Intensity", Float) = 0
        _DisturbVIntensity1 ("Disturb V Intensity", Float) = 0
        _UseDisturb ("Use Disturb", Float) = 0
        _UseMask ("Use Mask", Float) = 1
        _UseBlend ("Use Blend", Float) = 0
        [HDR] _BlendTint ("Blend Tint", Color) = (1,1,1,1)
        _UseDissolve ("Use Dissolve", Float) = 1
        _DissolveScheduleOffset ("Dissolve Schedule Offset", Float) = 0
        _DissolveEdgeSharp ("Dissolve Edge Sharpness", Float) = 0.5
        _DissolveEmissiveEdge ("Dissolve Emissive Edge", Float) = 0.2
        [HDR] _DissolveEmissiveColor ("Dissolve Emissive Color", Color) = (0,0,0,0)

        // These are intentionally visible in the diagnostic shader because
        // all three source materials author them.  They do not claim that
        // the retail renderer ABI has been recovered.
        _UseMaskTexAsAlpha ("Use Mask Red As Alpha", Float) = 1
        _MaskTexUseDisturb ("Mask UV Disturb", Float) = 0
        _BlendTexUseDisturb ("Blend UV Disturb", Float) = 0
        _UseSoftBlend ("Use Soft Depth Blend", Float) = 0
        _SoftDistance ("Soft Depth Distance", Float) = 0.001
        _RenderTransparentAfterDOF ("Render After DOF (Source Marker)", Float) = 0
        _TransparentSortPriority ("Transparent Sort Priority (Source Marker)", Float) = 0

        [HideInInspector] _BlendMode ("Blend Mode", Float) = 0
        [HideInInspector] _SurfaceType ("Surface Type", Float) = 1
        [HideInInspector] _Responsive ("Responsive", Float) = 1
        [HideInInspector] _IsSceneEffect ("Scene Effect", Float) = 0
        [HideInInspector] _IgnorePostExposure ("Ignore Post Exposure", Float) = 1
        [HideInInspector] _SrcBlend ("Source Blend", Float) = 1
        [HideInInspector] _DstBlend ("Destination Blend", Float) = 10
        [HideInInspector] _AlphaSrcBlend ("Alpha Source Blend", Float) = 1
        [HideInInspector] _AlphaDstBlend ("Alpha Destination Blend", Float) = 10
        [HideInInspector] _ZTest ("Z Test", Float) = 4
        [HideInInspector] _ZWrite ("Z Write", Float) = 0
        [HideInInspector] _CullMode ("Cull", Float) = 2
        [HideInInspector] _RecoveredLODFade ("Recovered LOD Fade", Vector) = (1000,0,0,0)
        [HideInInspector] _DiagnosticForceVisible ("Diagnostic Force Visible", Float) = 0
    }

    SubShader
    {
        Tags { "Queue"="Transparent+700" "RenderType"="Transparent" }
        Pass
        {
            Name "LiZhiyanStart01DiagnosticColorOnly"
            Tags { "LightMode"="SRPDefaultUnlit" }
            Blend [_SrcBlend] [_DstBlend], [_AlphaSrcBlend] [_AlphaDstBlend]
            ZTest [_ZTest]
            ZWrite [_ZWrite]
            Cull [_CullMode]

            CGPROGRAM
            #pragma target 5.0
            #pragma vertex Vert
            #pragma fragment Frag
            #include "UnityCG.cginc"

            sampler2D _MainTex;
            sampler2D _DisturbTex1;
            sampler2D _MaskTex;
            sampler2D _BlendTex;
            sampler2D _DissolveTex;
            float4 _MainTex_ST;
            float4 _DisturbTex1_ST;
            float4 _MaskTex_ST;
            float4 _BlendTex_ST;
            float4 _DissolveTex_ST;

            float _LiMaterialMode;
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
            float4 _DisturbUVSpeed1;
            float4 _MaskTexUVSpeed;
            float4 _BlendTexUVSpeed;
            float4 _DissolveUVSpeed;
            float _UseSampleTex0AsAlpha;
            float _UseSampleTex1AsAlpha;
            float _UseSampleTex2AsAlpha;
            float _UseSampleTex3AsAlpha;
            float _DisturbTex1Normal;
            float _DisturbUIntensity1;
            float _DisturbVIntensity1;
            float _UseDisturb;
            float _UseMask;
            float _UseBlend;
            float4 _BlendTint;
            float _UseDissolve;
            float _DissolveScheduleOffset;
            float _DissolveEdgeSharp;
            float _DissolveEmissiveEdge;
            float4 _DissolveEmissiveColor;
            float _UseMaskTexAsAlpha;
            float _MaskTexUseDisturb;
            float _BlendTexUseDisturb;
            float _UseSoftBlend;
            float _SoftDistance;
            float _BlendMode;
            float _SurfaceType;
            float _Responsive;
            float _IsSceneEffect;
            float _IgnorePostExposure;
            float _SrcBlend;
            float _DstBlend;
            float4 _RecoveredLODFade;
            float _DiagnosticForceVisible;

            UNITY_DECLARE_DEPTH_TEXTURE(_CameraDepthTexture);

            struct Attributes
            {
                float4 vertex : POSITION;
                float4 color : COLOR;
                float2 uv0 : TEXCOORD0;
                float2 uv1 : TEXCOORD1;
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float4 screenPos : TEXCOORD5;
                float eyeDepth : TEXCOORD6;
                float4 color : COLOR;
                float2 mainUV : TEXCOORD0;
                float2 route0UV : TEXCOORD1;
                float2 route1UV : TEXCOORD2;
                float2 route2UV : TEXCOORD3;
                float2 route3UV : TEXCOORD4;
            };

            float2 BuildUV(
                float2 uv0, float2 uv1, float4 weights, float4 speed,
                float4 rotateMat, float4 textureST)
            {
                float2 uv = uv0 * weights.x + uv1 * weights.y;
                float2 centered = uv + speed.xy * _Time.y - 0.5;
                float2 rotated = float2(
                    dot(centered, rotateMat.xz),
                    dot(centered, rotateMat.yw)) + 0.5;
                return rotated * textureST.xy + textureST.zw;
            }

            Varyings Vert(Attributes input)
            {
                Varyings output;
                output.positionCS = UnityObjectToClipPos(input.vertex);
                output.screenPos = ComputeScreenPos(output.positionCS);
                output.eyeDepth = -UnityObjectToViewPos(input.vertex).z;
                output.color = input.color;
                output.mainUV = BuildUV(
                    input.uv0, input.uv1, _MainTexUVWeights,
                    _MainTexUVSpeed, _MainTexUVRotateMat, _MainTex_ST);

                // 09/10: route0=Mask, route1=Blend, route2=Dissolve.
                // 11:   route0=Disturb, route1=Mask, route2=Blend,
                //       route3=Dissolve.
                float fourSample = step(10.5, _LiMaterialMode);
                float4 route0ST = lerp(_MaskTex_ST, _DisturbTex1_ST, fourSample);
                float4 route1ST = lerp(_BlendTex_ST, _MaskTex_ST, fourSample);
                float4 route2ST = lerp(_DissolveTex_ST, _BlendTex_ST, fourSample);
                output.route0UV = BuildUV(
                    input.uv0, input.uv1, _SampleTex0UVWeights,
                    _SampleTex0UVSpeed, _SampleTex0UVRotateMat, route0ST);
                output.route1UV = BuildUV(
                    input.uv0, input.uv1, _SampleTex1UVWeights,
                    _SampleTex1UVSpeed, _SampleTex1UVRotateMat, route1ST);
                output.route2UV = BuildUV(
                    input.uv0, input.uv1, _SampleTex2UVWeights,
                    _SampleTex2UVSpeed, _SampleTex2UVRotateMat, route2ST);
                output.route3UV = BuildUV(
                    input.uv0, input.uv1, _SampleTex3UVWeights,
                    _SampleTex3UVSpeed, _SampleTex3UVRotateMat, _DissolveTex_ST);
                return output;
            }

            float AlphaCarrier(float4 value, float useRed)
            {
                return lerp(value.a, value.r, saturate(useRed));
            }

            float3 ColorCarrier(float4 value, float useRed)
            {
                return lerp(value.rgb, 1.0.xxx, saturate(useRed));
            }

            float SoftDepthFactor(Varyings input)
            {
                if (_UseSoftBlend <= 0.0001)
                    return 1.0;
                float sceneDepth = LinearEyeDepth(
                    SAMPLE_DEPTH_TEXTURE_PROJ(
                        _CameraDepthTexture,
                        UNITY_PROJ_COORD(input.screenPos)));
                float distance = max(_SoftDistance, 0.0001);
                return saturate((sceneDepth - input.eyeDepth) / distance);
            }

            float4 Frag(Varyings input) : SV_Target
            {
                if (_DiagnosticForceVisible > 0.5)
                    return float4(0.0, 1.0, 1.0, 1.0);
                float fourSample = step(10.5, _LiMaterialMode);
                float4 route0 = lerp(
                    tex2D(_MaskTex, input.route0UV),
                    tex2D(_DisturbTex1, input.route0UV), fourSample);
                float4 route1 = lerp(
                    tex2D(_BlendTex, input.route1UV),
                    tex2D(_MaskTex, input.route1UV), fourSample);
                float4 route2 = lerp(
                    tex2D(_DissolveTex, input.route2UV),
                    tex2D(_BlendTex, input.route2UV), fourSample);
                float4 route3 = tex2D(_DissolveTex, input.route3UV);
                float4 maskSample = lerp(route0, route1, fourSample);
                float4 blendSample = lerp(route1, route2, fourSample);
                float4 dissolveSample = lerp(route2, route3, fourSample);

                float2 disturbance = float2(0.0, 0.0);
                if (fourSample > 0.5)
                {
                    float2 signedDisturb = float2(
                        route0.r * route0.a * 2.0 - 1.0,
                        route0.g * 2.0 - 1.0);
                    float2 scalarDisturb = route0.rr;
                    disturbance = lerp(
                        scalarDisturb * float2(
                            _DisturbUIntensity1, _DisturbVIntensity1),
                        signedDisturb * _DisturbUIntensity1,
                        saturate(_DisturbTex1Normal));
                    disturbance *= saturate(_UseDisturb);
                }
                float4 mainSample = tex2D(
                    _MainTex,
                    input.mainUV + disturbance * saturate(_MainTexUseDisturb));
                float mainAlpha = AlphaCarrier(mainSample, _UseMainTexAsAlpha);
                float3 mainColor = ColorCarrier(mainSample, _UseMainTexAsAlpha);

                float maskAlpha = AlphaCarrier(maskSample, _UseMaskTexAsAlpha);
                float mask = lerp(1.0, maskAlpha, saturate(_UseMask));
                float blendUseRed = lerp(
                    _UseSampleTex1AsAlpha, _UseSampleTex2AsAlpha, fourSample);
                float3 blendCarrier = ColorCarrier(blendSample, blendUseRed);
                float dissolveCarrier = dissolveSample.r;

                float3 color = mainColor * _TintColor.rgb * _TintColorIntensity;
                color += blendCarrier * _BlendTint.rgb * saturate(_UseBlend);
                float dissolveThreshold = _DissolveScheduleOffset * 2.02 - 1.01;
                float dissolveDelta = dissolveCarrier - dissolveThreshold;
                float dissolveAlpha = saturate(dissolveDelta * _DissolveEdgeSharp);
                float dissolveEdge = saturate(
                    (_DissolveEmissiveEdge - dissolveDelta) * _DissolveEdgeSharp);
                float dissolveEnabled = saturate(_UseDissolve);
                color = lerp(
                    color,
                    dissolveEdge * _DissolveEmissiveColor.rgb * _TintColorIntensity,
                    dissolveEdge * dissolveEnabled);
                color = clamp(color, 0.0, 1000.0);

                float alpha = saturate(
                    mainAlpha * _TintColor.a * _TintColorAlpha *
                    input.color.a * mask);
                alpha *= lerp(1.0, dissolveAlpha, dissolveEnabled);
                alpha = lerp(1.0, alpha, saturate(_ProcedureAlpha));
                alpha *= SoftDepthFactor(input);
                float coverage = alpha;
                float isMultiply = step(1.5, _BlendMode);
                float3 premultiplied = lerp(
                    color * coverage,
                    lerp(1.0.xxx, color, coverage),
                    isMultiply);
                float outputAlpha = coverage * (1.0 - saturate(_BlendMode));
                return float4(premultiplied, outputAlpha);
            }
            ENDCG
        }
    }
    Fallback Off
}
