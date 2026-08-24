Shader "Hidden/Endfield/VisualCompatibility/VFXRefract28"
{
    Properties
    {
        _RefractTex ("Recovered source refraction texture", 2D) = "gray" {}
        _DissolveTex ("Recovered source dissolve texture", 2D) = "white" {}
        _RefractTex_ST ("Texture transform", Vector) = (1,1,0,0)
        _DissolveTex_ST ("Dissolve texture transform", Vector) = (1,1,0,0)
        _RefractUVSpeed ("Recovered UV speed", Vector) = (0,0,0,0)
        _DissolveUVSpeed ("Recovered dissolve UV speed", Vector) = (0,0,0,0)
        _RefractDir ("Recovered direction", Vector) = (1,1,0,0)
        _Intensity ("Recovered intensity", Float) = 1
        _RefractIsNormal ("Recovered normal decode", Float) = 1
        _Bi_Refract ("Recovered bidirectional decode", Float) = 0
        _TintColorAlpha ("Recovered alpha carrier", Float) = 1
        _DissolveUVRotate ("Recovered dissolve rotation", Float) = 0
        _DissolveScheduleOffset ("Recovered dissolve schedule", Float) = 0
        _DissolveEdgeSharp ("Recovered dissolve edge sharpness", Float) = 1
        _CullMode ("Recovered cull", Float) = 2
        _ZTest ("Recovered depth test", Float) = 4
    }
    SubShader
    {
        Tags { "Queue"="Transparent" "RenderType"="Transparent" }
        Pass
        {
            Name "VISUAL_COMPATIBILITY_REFRACTION_NOT_EXACT"
            Tags { "LightMode"="ForwardOnly" }
            Blend One Zero
            // The source carrier is a circular mesh whose authored UV rim is
            // interior to 0..1. Without the retail full-screen distortion
            // resolve, any ordinary scene-color replacement exposes that rim
            // as the conspicuous cropped disc. Keep the recovered material and
            // schedule bound, but fail the unresolved color write closed; the
            // independently source-backed additive flare remains visible.
            ColorMask 0
            ZWrite Off
            ZTest [_ZTest]
            Cull [_CullMode]
            CGPROGRAM
            #pragma target 4.5
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma shader_feature_local_fragment _USE_DISSOLVE
            #include "UnityCG.cginc"
            sampler2D _RefractTex;
            sampler2D _DissolveTex;
            sampler2D _SceneColorTexture;
            float4 _RefractTex_ST, _DissolveTex_ST, _RefractUVSpeed,
                _DissolveUVSpeed, _RefractDir, _VFXParams0;
            float _Intensity, _RefractIsNormal, _Bi_Refract, _TintColorAlpha,
                _DissolveUVRotate, _DissolveScheduleOffset, _DissolveEdgeSharp;
            struct A { float4 vertex:POSITION; float4 color:COLOR; float2 uv:TEXCOORD0; float4 custom:TEXCOORD1; };
            struct V { float4 positionCS:SV_POSITION; float4 screenPos:TEXCOORD0; float2 uv:TEXCOORD1; float4 color:COLOR; float4 custom:TEXCOORD2; };
            V Vert(A i) { V o; o.positionCS=UnityObjectToClipPos(i.vertex); o.screenPos=ComputeScreenPos(o.positionCS); o.uv=i.uv; o.color=i.color; o.custom=i.custom; return o; }
            float2 MirrorUV(float2 uv)
            {
                float2 wrapped = frac(uv * 0.5) * 2.0;
                return 1.0 - abs(wrapped - 1.0);
            }
            float2 RotateCentered(float2 uv, float degrees)
            {
                float sine, cosine;
                sincos(degrees * 0.01745329238474369, sine, cosine);
                uv -= 0.5;
                return float2(dot(uv, float2(cosine, sine)),
                    dot(uv, float2(-sine, cosine))) + 0.5;
            }
            float4 Frag(V i):SV_Target
            {
                float2 uv = frac(i.uv * _RefractTex_ST.xy + _RefractTex_ST.zw +
                    _RefractUVSpeed.xy * _VFXParams0.w);
                float4 n = tex2D(_RefractTex, uv);
                float x = mad(n.r, _Bi_Refract + 1.0, -_Bi_Refract);
                float2 fixedDir = x * _RefractDir.xy;
                float2 normalDir = float2(x * n.a * 2.0 - 1.0, n.g * 2.0 - 1.0) * _RefractDir.xy;
                float2 dir = lerp(fixedDir, normalDir, saturate(_RefractIsNormal));
                float dissolve = 1.0;
                #if defined(_USE_DISSOLVE)
                    // Exact selected retail DXBC dissolve branch. M28's
                    // serialized stream supplies the schedule in Custom1.z;
                    // its material supplies -90/0.571/1 and the recovered BC7
                    // dissolve texture. This masks distortion strength, not
                    // geometry alpha, matching the distortion consumer.
                    float2 dissolveUV = i.uv +
                        _DissolveUVSpeed.xy * _VFXParams0.w +
                        _DissolveUVSpeed.zw * i.custom.y;
                    dissolveUV = RotateCentered(dissolveUV, _DissolveUVRotate);
                    dissolveUV = dissolveUV * _DissolveTex_ST.xy +
                        _DissolveTex_ST.zw;
                    float dissolveSample = tex2D(
                        _DissolveTex, MirrorUV(dissolveUV)).r;
                    float dissolveThreshold = mad(
                        i.custom.z + _DissolveScheduleOffset,
                        2.0199999809265137, -1.0099999904632568);
                    dissolve = saturate((dissolveSample - dissolveThreshold) *
                        _DissolveEdgeSharp);
                #endif
                // Deliberately bounded compatibility scale: source units cannot be
                // transferred directly without the retail distortion consumer.
                // The retail consumer resolves distortion into a full-screen
                // target; drawing this recovered carrier as ordinary geometry
                // otherwise leaves a hard circular replacement edge. Fade the
                // displacement to zero at the billboard boundary so the sampled
                // scene color becomes identical to the underlying pixel there.
                float2 edgeUv = abs(i.uv - 0.5) * 2.0;
                float edgeFade = 1.0 - smoothstep(0.78, 1.0, max(edgeUv.x, edgeUv.y));
                float strength = saturate(abs(_Intensity)) * _TintColorAlpha *
                    i.color.a * dissolve * edgeFade * 0.0125;
                float2 screenUV = i.screenPos.xy / max(i.screenPos.w, 1e-6);
                #if UNITY_UV_STARTS_AT_TOP
                    // The compatibility pass executes in the recovered
                    // offscreen MRT subpass. Its scene-color input retains
                    // RenderTexture sampling orientation while the corrected
                    // VFX projection is render-target oriented.
                    screenUV.y = 1.0 - screenUV.y;
                #endif
                return tex2D(_SceneColorTexture, saturate(screenUV + dir * strength));
            }
            ENDCG
        }
    }
}
