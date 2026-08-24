Shader "Hidden/Endfield/Recovered/Zhuangfy/VFXRefractMRT"
{
    Properties
    {
        _SurfaceType ("Surface Type", Float) = 1
        _CullMode ("Cull Mode", Float) = 2
        _DisableZTest ("Disable Z Test", Float) = 0
        _TintColorAlpha ("Tint Color Alpha", Float) = 1
        _ProcedureAlpha ("Procedure Alpha", Float) = 1
        _EnableTransparentMV ("Enable Transparent MV", Float) = 0
        _RefractTex ("Refract Tex", 2D) = "white" {}
        _RefractIsNormal ("Refract Is Normal", Float) = 1
        _RefractUVSpeed ("Refract UV Speed", Vector) = (0,0,0,0)
        _RefractTexUVRotate ("Refract Tex UV Rotate", Float) = 0
        _RefractSwitchUV ("Refract Switch UV", Float) = 0
        _RefractDir ("Refract Direction", Vector) = (1,1,0,0)
        _Intensity ("Refract Intensity", Float) = 1
        _Bi_Refract ("Bidirectional Refract", Float) = 0
        _RefractUseRBOffset ("Refract Uses RB Offset Scale", Float) = 0
        _UseRBOffset ("Use RB Offset", Float) = 0
        _RBIntensity ("RB Offset Intensity", Float) = 1
        _RBOffset ("RB Offset", Vector) = (0,0,0,0)
        _RBMainColorMask ("RB Main Color Mask", Color) = (1,0,0,1)
        _RBOffsetColorMask ("RB Offset Color Mask", Color) = (0,1,1,1)
        _UseMainTexAsMask ("Use Main Tex As Mask", Float) = 0
        _RenderTransparentAfterDOF ("Render Transparent After DOF", Float) = 0
        _UseDissolve ("Use Dissolve", Float) = 0
        _DissolveTex ("Dissolve Tex", 2D) = "white" {}
        _DissolveUVSpeed ("Dissolve UV Speed", Vector) = (0,0,0,0)
        _DissolveUVRotate ("Dissolve UV Rotate", Float) = 0
        _DissolveScheduleOffset ("Dissolve Schedule Offset", Float) = 0
        _DissolveEdgeSharp ("Dissolve Edge Sharp", Float) = 1
        _DissolveAffectBlend ("Dissolve Affect Blend", Float) = 0
        _UseNearCameraFade ("Use Near Camera Fade", Float) = 0
        _NearCameraFadeDistanceStart ("Near Fade Start", Float) = 0.001
        _NearCameraFadeDistanceEnd ("Near Fade End", Float) = 10
        _NearCameraFadeDistanceStart2 ("Near Fade Start 2", Float) = 120
        _NearCameraFadeDistanceEnd2 ("Near Fade End 2", Float) = 100
        _AlphaSrcBlend ("Alpha Source Blend", Float) = 1
        _AlphaDstBlend ("Alpha Destination Blend", Float) = 10
        _SrcBlend ("Source Blend", Float) = 5
        _DstBlend ("Destination Blend", Float) = 10
        _MVSrcColorBlend ("MV Source Color Blend", Float) = 3
        _MVDstColorBlend ("MV Destination Color Blend", Float) = 6
        _ZTest ("Z Test", Float) = 4
        _ZWrite ("Z Write", Float) = 1
        _RecoveredLODFade ("Recovered LOD Fade", Vector) = (1000,0,0,0)
    }

    SubShader
    {
        Tags
        {
            "Queue"="Transparent"
            "RenderType"="Transparent"
            "EndfieldSceneMVMRT"="ExactSelectedFiftyThree"
        }
        Pass
        {
            Name "Refraction"
            Tags { "LightMode"="Distortion" }
            // Parsed m_State binds the color blend factors, depth state, and
            // culling to material properties. The converted retail ShaderLab
            // prints their zero-valued parser defaults and is not the live
            // PSO. Alpha factors remain the fixed parsed Zero/One and One/One.
            Blend 0 [_SrcBlend] [_DstBlend], Zero One
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
            #pragma multi_compile_instancing
            #pragma instancing_options procedural:vertInstancingSetup
            #pragma shader_feature_local_fragment _USE_DISSOLVE
            #pragma shader_feature_local_fragment _USE_RBOFFSET
            #include "UnityCG.cginc"
            #include "UnityStandardParticleInstancing.cginc"

            sampler2D _RefractTex;
            sampler2D _DissolveTex;
            sampler2D _SceneColorTexture;
            float4 _RefractTex_ST;
            float4 _DissolveTex_ST;
            float4 _RefractUVSpeed;
            float4 _DissolveUVSpeed;
            float4 _RefractDir;
            float4 _RBOffset;
            float4 _RBMainColorMask;
            float4 _RBOffsetColorMask;
            float4 _VFXParams0;
            float4 _RecoveredLODFade;
            float _GlobalMipBias;
            float _EndfieldSceneMVMRTReady;
            float _EndfieldRecoveredVFXGlobalsReady;
            float _SurfaceType;
            float _EnableTransparentMV;
            float _TintColorAlpha;
            float _ProcedureAlpha;
            float _RefractIsNormal;
            float _RefractTexUVRotate;
            float _Intensity;
            float _Bi_Refract;
            float _RefractUseRBOffset;
            float _RBIntensity;
            float _UseMainTexAsMask;
            float _DissolveUVRotate;
            float _DissolveScheduleOffset;
            float _DissolveEdgeSharp;
            float _DissolveAffectBlend;
            float _UseNearCameraFade;
            float _NearCameraFadeDistanceStart;
            float _NearCameraFadeDistanceEnd;
            float _NearCameraFadeDistanceStart2;
            float _NearCameraFadeDistanceEnd2;

            struct Attributes
            {
                float4 vertex : POSITION;
                float4 color : COLOR;
                float4 uv0 : TEXCOORD0;
                float4 custom : TEXCOORD1;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float2 uv : TEXCOORD0;
                float4 color : COLOR;
                float4 custom : TEXCOORD1;
                float4 screenPos : TEXCOORD2;
                float3 positionWS : TEXCOORD3;
            };

            struct FragmentOutput
            {
                float4 color : SV_Target0;
                float4 sceneMV : SV_Target1;
            };

            float2 MirrorUV(float2 uv)
            {
                float2 wrapped = frac(uv * 0.5) * 2.0;
                return 1.0 - abs(wrapped - 1.0);
            }

            float2 RotateCentered(float2 uv, float degrees)
            {
                float sine;
                float cosine;
                sincos(degrees * 0.01745329238474369, sine, cosine);
                uv -= 0.5;
                return float2(dot(uv, float2(cosine, sine)),
                    dot(uv, float2(-sine, cosine))) + 0.5;
            }

            Varyings Vert(Attributes input)
            {
                UNITY_SETUP_INSTANCE_ID(input);
                Varyings output;
                output.positionCS = UnityObjectToClipPos(input.vertex);
                output.uv = input.uv0.xy;
                #if defined(UNITY_PARTICLE_INSTANCING_ENABLED)
                    // The original selected VS reads the per-particle
                    // transform through _VertexSkinMatrices and multiplies
                    // the packed particle color into mesh COLOR. Public
                    // Unity exposes the equivalent procedural particle
                    // transform through vertInstancingSetup and its packed
                    // RGBA8 carrier here.
                    UNITY_PARTICLE_INSTANCE_DATA particleInstance =
                        unity_ParticleInstanceData[unity_InstanceID];
                    uint packedParticleColor = particleInstance.color;
                    float4 particleInstanceColor = float4(
                        packedParticleColor & 255u,
                        (packedParticleColor >> 8u) & 255u,
                        (packedParticleColor >> 16u) & 255u,
                        (packedParticleColor >> 24u) & 255u) *
                        (1.0 / 255.0);
                    output.color = input.color * particleInstanceColor;
                #else
                    output.color = input.color;
                #endif
                output.custom = input.custom;
                output.screenPos = ComputeScreenPos(output.positionCS);
                output.positionWS = mul(unity_ObjectToWorld, input.vertex).xyz;
                return output;
            }

            float DistanceFade(float distanceToCamera)
            {
                float nearFade = saturate((distanceToCamera - _NearCameraFadeDistanceStart) /
                    max(_NearCameraFadeDistanceEnd - _NearCameraFadeDistanceStart, 1e-6));
                float farFade = saturate((_NearCameraFadeDistanceStart2 - distanceToCamera) /
                    max(_NearCameraFadeDistanceStart2 - _NearCameraFadeDistanceEnd2, 1e-6));
                return lerp(1.0, nearFade * farFade, saturate(_UseNearCameraFade));
            }

            FragmentOutput Frag(Varyings input)
            {
                clip(min(_EndfieldSceneMVMRTReady,
                    _EndfieldRecoveredVFXGlobalsReady) - 0.5);

                float2 refractUV = input.uv + _RefractUVSpeed.xy * _VFXParams0.w +
                    _RefractUVSpeed.zw * input.custom.x;
                refractUV = RotateCentered(refractUV, _RefractTexUVRotate);
                refractUV = refractUV * _RefractTex_ST.xy + _RefractTex_ST.zw;
                float4 refractSample = tex2Dbias(_RefractTex,
                    float4(frac(refractUV), 0.0, _GlobalMipBias));

                float refractX = mad(refractSample.r,
                    _Bi_Refract + 1.0, -_Bi_Refract);
                float2 fixedDirection = refractX * _RefractDir.xy;
                float2 decodedNormal = float2(
                    refractX * refractSample.a * 2.0 - 1.0,
                    refractSample.g * 2.0 - 1.0) * _RefractDir.xy;
                float2 refractDirection = lerp(fixedDirection,
                    decodedNormal, saturate(_RefractIsNormal));
                float strength = (1.0 - _RecoveredLODFade.y) *
                    _Intensity * _TintColorAlpha * input.color.a;

                float dissolve = 1.0;
                #if defined(_USE_DISSOLVE)
                    float2 dissolveUV = input.uv + _DissolveUVSpeed.xy * _VFXParams0.w +
                        _DissolveUVSpeed.zw * input.custom.y;
                    dissolveUV = RotateCentered(dissolveUV, _DissolveUVRotate);
                    dissolveUV = dissolveUV * _DissolveTex_ST.xy + _DissolveTex_ST.zw;
                    float dissolveSample = tex2Dbias(_DissolveTex,
                        float4(MirrorUV(dissolveUV), 0.0, _GlobalMipBias)).r;
                    float dissolveThreshold = mad(
                        input.custom.z + _DissolveScheduleOffset,
                        2.0199999809265137, -1.0099999904632568);
                    dissolve = saturate((dissolveSample - dissolveThreshold) *
                        _DissolveEdgeSharp);
                #endif

                float2 screenUV = input.screenPos.xy / max(input.screenPos.w, 1e-8);
                float2 distortedUV = screenUV + refractDirection * strength *
                    dissolve;
                float4 scene = tex2Dbias(_SceneColorTexture,
                    float4(saturate(distortedUV), 0.0, _GlobalMipBias));
                #if defined(_USE_RBOFFSET)
                    // Exact selected HG_ENABLE_MV + _USE_RBOFFSET DXBC
                    // shape (fragment hash f905de094d0261d5): retain the
                    // ordinary scene sample, take a second sample at the
                    // serialized percent-space RB offset, apply the two
                    // compiled RGB masks with max, then interpolate by the
                    // serialized RB intensity.
                    float refractMagnitude = lerp(
                        refractX,
                        length(decodedNormal),
                        saturate(_RefractIsNormal));
                    float rbDirectionScale = lerp(
                        1.0,
                        refractMagnitude,
                        saturate(_RefractUseRBOffset));
                    float2 rbUV = distortedUV + _RBOffset.xy * 0.01 *
                        (_TintColorAlpha * input.color.a) * rbDirectionScale;
                    float4 rbScene = tex2Dbias(_SceneColorTexture,
                        float4(saturate(rbUV), 0.0, _GlobalMipBias));
                    float3 rbCombined = max(
                        scene.rgb * _RBMainColorMask.rgb,
                        rbScene.rgb * _RBOffsetColorMask.rgb);
                    scene.rgb = lerp(
                        scene.rgb,
                        rbCombined,
                        saturate(_RBIntensity));
                #endif
                float alpha = DistanceFade(distance(_WorldSpaceCameraPos, input.positionWS));
                alpha *= lerp(1.0, dissolve, saturate(_DissolveAffectBlend));

                FragmentOutput output;
                output.color = float4(clamp(scene.rgb, 0.0, 1000.0), saturate(alpha));
                // Exact selected material: _SurfaceType=1 and
                // _EnableTransparentMV=0, so the shipped gate zeros XY.
                output.sceneMV = float4(0.0, 0.0, 1.0, 0.0);
                return output;
            }
            ENDCG
        }
    }
    Fallback Off
}
