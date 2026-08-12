Shader "Hidden/Endfield/Recovered/CharInfo/HGRPLitUnavailable"
{
    Properties
    {
        _MROMap ("Original MRO Map", 2D) = "white" {}
        _BaseColor ("Original Base Color", Color) = (1,1,1,1)
        _Metallic ("Original Metallic", Float) = 0
        _NormalScale ("Original Normal Scale", Float) = 1
        _OcclusionStrength ("Original Occlusion Strength", Float) = 1
        _RoughnessMin ("Original Roughness Minimum", Float) = 0
        _RoughnessMax ("Original Roughness Maximum", Float) = 1
        _PorosityFactorX ("Original Porosity Offset", Float) = 0.2
        _PorosityFactorY ("Original Porosity Roughness Scale", Float) = 0.4
        _PorosityFactorZ ("Original Porosity Metallic Scale", Float) = 0
        _EnableSubsurface ("Original Subsurface Enable", Float) = 0
        _IgnorePostExposure ("Original Ignore Post Exposure", Float) = 1
        _CullMode ("Original Cull", Float) = 0
        _ZTestGBuffer ("Original HGBuffer ZTest", Float) = 4
        _ZWriteGBuffer ("Original HGBuffer ZWrite", Float) = 1
        _StencilRef ("Original Stencil Reference", Float) = 0
        _StencilOpGBuffer ("Original HGBuffer Stencil Pass", Float) = 2
    }

    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry" }
        Pass
        {
            Name "UnavailableHGRPLit"
            Tags { "LightMode"="ForwardOnly" }
            Cull Off
            ZWrite Off
            ColorMask 0

            CGPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #include "UnityCG.cginc"
            float4 Vert(float4 vertex : POSITION) : SV_POSITION
            {
                return UnityObjectToClipPos(vertex);
            }
            float4 Frag() : SV_Target
            {
                return 0.0;
            }
            ENDCG
        }

        // Default-off sidecar pass for the exact M_CharInfo_outside material.
        // The ordinary renderer never submits this LightMode. A dedicated
        // verifier draws it into the original five-MRT layout while the real
        // deferred resolver remains fail-closed.
        Pass
        {
            Name "RecoveredSphereOutsideHGBufferDiagnostic"
            Tags { "LightMode"="EndfieldRecoveredSphereOutsideHGBufferDiagnostic" }
            Cull [_CullMode]
            // Packing-only diagnostic: the attached D32S8 surface proves the
            // source target layout, while visibility/depth ownership remains
            // with the still-unrecovered HGBuffer render-graph route.
            ZTest Always
            ZWrite On

            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex SphereOutsideHGBufferVert
            #pragma fragment SphereOutsideHGBufferFrag
            #include "UnityCG.cginc"

            sampler2D _MROMap;
            float4 _MROMap_ST;
            float4 _BaseColor;
            float _Metallic;
            float _NormalScale;
            float _OcclusionStrength;
            float _RoughnessMin;
            float _RoughnessMax;
            float _PorosityFactorX;
            float _PorosityFactorY;
            float _PorosityFactorZ;
            float _EnableSubsurface;

            struct SphereOutsideAttributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
                float4 tangentOS : TANGENT;
                float2 uv0 : TEXCOORD0;
            };

            struct SphereOutsideVaryings
            {
                float4 positionCS : SV_POSITION;
                float2 uv0 : TEXCOORD0;
                float3 normalWS : TEXCOORD1;
                float4 tangentWS : TEXCOORD2;
            };

            struct SphereOutsideHGBufferOutput
            {
                float4 sceneColor : SV_Target0;
                float4 sceneMotion : SV_Target1;
                float4 gBufferA : SV_Target2;
                float4 gBufferB : SV_Target3;
                float4 gBufferC : SV_Target4;
            };

            float2 EncodeYUpOctNormal(float3 normalWS)
            {
                float3 normal = normalize(normalWS);
                float invL1 = rcp(
                    max(abs(normal.x) + abs(normal.y) + abs(normal.z), 1e-8));
                float2 oct = normal.xz * invL1;
                if (normal.y <= 0.0)
                {
                    oct = (1.0 - abs(oct.yx)) *
                        float2(oct.x >= 0.0 ? 1.0 : -1.0,
                               oct.y >= 0.0 ? 1.0 : -1.0);
                }
                return oct * 0.5 + 0.5;
            }

            SphereOutsideVaryings SphereOutsideHGBufferVert(
                SphereOutsideAttributes input)
            {
                SphereOutsideVaryings output;
                // The pass is an isolated packing audit, not a presentation
                // camera path. Sphere's exact source bounds are +/-0.5, so use
                // a deterministic diagnostic projection that cannot inherit
                // unrelated viewer/SRP matrix state.
                output.positionCS = float4(
                    input.positionOS.x * 1.6,
                    input.positionOS.y * 1.6,
                    0.5 - input.positionOS.z * 0.5,
                    1.0);
                output.uv0 = TRANSFORM_TEX(input.uv0, _MROMap);
                output.normalWS = UnityObjectToWorldNormal(input.normalOS);
                output.tangentWS = float4(
                    UnityObjectToWorldDir(input.tangentOS.xyz),
                    input.tangentOS.w * unity_WorldTransformParams.w);
                return output;
            }

            SphereOutsideHGBufferOutput SphereOutsideHGBufferFrag(
                SphereOutsideVaryings input)
            {
                SphereOutsideHGBufferOutput output;

                // Exact selected HGRP/Lit HGBuffer fragment starts target 0 at
                // (0,0,0,0.5). The static settled diagnostic has no current/
                // previous deformation or camera delta, so the signed fourth-
                // root scene-motion encoding lands on its neutral endpoint.
                output.sceneColor = float4(0.0, 0.0, 0.0, 0.5);
                output.sceneMotion = float4(0.5, 0.5, 0.0, 0.0);

                float3 mro = tex2D(_MROMap, input.uv0).rgb;
                float metallic = lerp(_Metallic, mro.r, 1.0);
                float occlusion = lerp(1.0, mro.b, _OcclusionStrength);
                float roughness = lerp(_RoughnessMin, _RoughnessMax, mro.g);

                // The selected binary evaluates:
                // saturate(PorosityY*roughness + metallic*PorosityZ +
                //          PorosityX) * 0.95 + 0.05,
                // then suppresses the lane for subsurface shading.
                float porosity = (
                    saturate(
                        _PorosityFactorY * roughness +
                        metallic * _PorosityFactorZ +
                        _PorosityFactorX) *
                    0.95 + 0.05) * (1.0 - _EnableSubsurface);

                output.gBufferA = float4(
                    metallic,
                    occlusion,
                    porosity,
                    0.0);
                output.gBufferB = float4(
                    EncodeYUpOctNormal(input.normalWS),
                    roughness,
                    0.0);
                output.gBufferC = float4(_BaseColor.rgb, 0.0);
                return output;
            }
            ENDHLSL
        }

        // Default-off same-camera producer used only by the recovered deferred
        // frame sidecar. Unlike the packing probe above, this uses the actual
        // source transform, camera matrices, depth comparison/write, and
        // material stencil state. Its five outputs are never presented until
        // the original pass-0 consumer is independently admitted.
        Pass
        {
            Name "RecoveredSphereOutsideHGBufferFrame"
            Tags { "LightMode"="EndfieldRecoveredSphereOutsideHGBufferFrame" }
            Cull [_CullMode]
            ZTest [_ZTestGBuffer]
            ZWrite [_ZWriteGBuffer]
            Stencil
            {
                Ref [_StencilRef]
                Comp Always
                Pass [_StencilOpGBuffer]
            }

            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex SphereOutsideHGBufferFrameVert
            #pragma fragment SphereOutsideHGBufferFrag
            #include "UnityCG.cginc"

            sampler2D _MROMap;
            float4 _MROMap_ST;
            float4 _BaseColor;
            float _Metallic;
            float _NormalScale;
            float _OcclusionStrength;
            float _RoughnessMin;
            float _RoughnessMax;
            float _PorosityFactorX;
            float _PorosityFactorY;
            float _PorosityFactorZ;
            float _EnableSubsurface;
            float4x4 _EndfieldRecoveredDeferredGpuViewProjection;
            float4x4 _EndfieldRecoveredDeferredPreviousGpuViewProjection;
            float4x4 _EndfieldRecoveredDeferredPreviousObjectToWorld;
            float _EndfieldRecoveredDeferredMotionValid;
            // Unity HDRP's UnityPerDraw motion-vector contract:
            // x=previous/deformed positions, y=allow motion, z=clip-space
            // depth bias, w=object-history (1) versus camera-only (0).
            float4 _EndfieldRecoveredDeferredMotionVectorsParams;

            struct SphereOutsideAttributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
                float4 tangentOS : TANGENT;
                float2 uv0 : TEXCOORD0;
            };

            struct SphereOutsideVaryings
            {
                float4 positionCS : SV_POSITION;
                float2 uv0 : TEXCOORD0;
                float3 normalWS : TEXCOORD1;
                float4 tangentWS : TEXCOORD2;
                // The source vertex writes current and previous clip x/y/w
                // into TEXCOORD5/TEXCOORD6 for HGRP/Lit's motion encoder.
                float3 currentClipXYW : TEXCOORD3;
                float3 previousClipXYW : TEXCOORD4;
            };

            struct SphereOutsideHGBufferOutput
            {
                float4 sceneColor : SV_Target0;
                float4 sceneMotion : SV_Target1;
                float4 gBufferA : SV_Target2;
                float4 gBufferB : SV_Target3;
                float4 gBufferC : SV_Target4;
            };

            float2 EncodeYUpOctNormal(float3 normalWS)
            {
                float3 normal = normalize(normalWS);
                float invL1 = rcp(
                    max(abs(normal.x) + abs(normal.y) + abs(normal.z), 1e-8));
                float2 oct = normal.xz * invL1;
                if (normal.y <= 0.0)
                {
                    oct = (1.0 - abs(oct.yx)) *
                        float2(oct.x >= 0.0 ? 1.0 : -1.0,
                               oct.y >= 0.0 ? 1.0 : -1.0);
                }
                return oct * 0.5 + 0.5;
            }

            SphereOutsideVaryings SphereOutsideHGBufferFrameVert(
                SphereOutsideAttributes input)
            {
                SphereOutsideVaryings output;
                float4 positionWS = mul(unity_ObjectToWorld, input.positionOS);
                float4 currentClip = mul(
                    _EndfieldRecoveredDeferredGpuViewProjection,
                    positionWS);
                bool cameraOnlyMotion =
                    _EndfieldRecoveredDeferredMotionVectorsParams.w <= 0.0;
                float4 previousPositionWS = mul(
                    cameraOnlyMotion
                        ? unity_ObjectToWorld
                        : _EndfieldRecoveredDeferredPreviousObjectToWorld,
                    input.positionOS);
                float4 previousClip = mul(
                    _EndfieldRecoveredDeferredPreviousGpuViewProjection,
                    previousPositionWS);
                output.positionCS = currentClip;
                output.currentClipXYW = currentClip.xyw;
                output.previousClipXYW = previousClip.xyw;
                output.uv0 = TRANSFORM_TEX(input.uv0, _MROMap);
                output.normalWS = UnityObjectToWorldNormal(input.normalOS);
                output.tangentWS = float4(
                    UnityObjectToWorldDir(input.tangentOS.xyz),
                    input.tangentOS.w * unity_WorldTransformParams.w);
                return output;
            }

            SphereOutsideHGBufferOutput SphereOutsideHGBufferFrag(
                SphereOutsideVaryings input)
            {
                SphereOutsideHGBufferOutput output;
                output.sceneColor = float4(0.0, 0.0, 0.0, 0.5);

                // This is the selected source fragment's signed fourth-root
                // motion encoding, using the same current/previous clip
                // x/y/w lanes produced by the source vertex. The validity
                // scalar is supplied by the C# history owner: the first
                // sample (or a camera/extent discontinuity) is neutral, and
                // subsequent settled samples carry the source valid endpoint.
                float currentW = max(input.currentClipXYW.z, 1e-8);
                float previousW = max(input.previousClipXYW.z, 1e-8);
                float currentX = input.currentClipXYW.x / currentW;
                float currentY = input.currentClipXYW.y / currentW;
                float previousX = input.previousClipXYW.x / previousW;
                float previousY = input.previousClipXYW.y / previousW;
                float deltaX = currentX - previousX;
                float deltaY = previousY - currentY;
                float encodedMotionX =
                    (deltaX > 0.0 ? 1.0 : (deltaX < 0.0 ? -1.0 : 0.0)) *
                    sqrt(sqrt(abs(deltaX * 0.5))) + 0.5;
                float encodedMotionY =
                    (deltaY > 0.0 ? 1.0 : (deltaY < 0.0 ? -1.0 : 0.0)) *
                    sqrt(sqrt(abs(deltaY * 0.5))) + 0.5;
                // SphereOutside is a static MeshRenderer, so x=0 is the
                // source-closed non-deformed path. If a future caller sends
                // x>0 without a previous skinned-position stream, fail
                // closed instead of turning object history into a false
                // deformation vector. y=0 is Unity's ForceNoMotion mode.
                float hasDeformation = step(
                    0.5,
                    _EndfieldRecoveredDeferredMotionVectorsParams.x);
                float allowMotion = step(
                    0.5,
                    _EndfieldRecoveredDeferredMotionVectorsParams.y);
                float motionValid = saturate(
                    _EndfieldRecoveredDeferredMotionValid) *
                    allowMotion * (1.0 - hasDeformation);
                output.sceneMotion = float4(
                    mad(motionValid, 0.5 - encodedMotionX, encodedMotionX),
                    mad(motionValid, 0.5 - encodedMotionY, encodedMotionY),
                    motionValid > 0.0 ? 1.0 : 0.0,
                    motionValid * 0.699999988079071);

                float3 mro = tex2D(_MROMap, input.uv0).rgb;
                float metallic = lerp(_Metallic, mro.r, 1.0);
                float occlusion = lerp(1.0, mro.b, _OcclusionStrength);
                float roughness = lerp(_RoughnessMin, _RoughnessMax, mro.g);
                float porosity = (
                    saturate(
                        _PorosityFactorY * roughness +
                        metallic * _PorosityFactorZ +
                        _PorosityFactorX) *
                    0.95 + 0.05) * (1.0 - _EnableSubsurface);

                output.gBufferA = float4(metallic, occlusion, porosity, 0.0);
                output.gBufferB = float4(
                    EncodeYUpOctNormal(input.normalWS),
                    roughness,
                    0.0);
                output.gBufferC = float4(_BaseColor.rgb, 0.0);
                return output;
            }
            ENDHLSL
        }
    }
    Fallback Off
}
