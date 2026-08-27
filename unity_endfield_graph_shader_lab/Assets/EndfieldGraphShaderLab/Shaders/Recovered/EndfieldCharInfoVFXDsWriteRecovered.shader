Shader "Endfield/Recovered/CharInfo/VFXDsWrite"
{
    Properties
    {
        _MainTex ("Main Tex", 2D) = "white" {}
        _TintColor ("Tint Color", Color) = (1,1,1,1)
        _TintColorIntensity ("Tint Intensity", Float) = 1
        _TintColorAlpha ("Tint Alpha", Float) = 1
        _DisableVertColor ("Disable Vertex Color", Float) = 0
        _InParticle ("In Particle", Float) = 1
        _IgnorePostExposure ("Ignore Post Exposure", Float) = 1
        _UseMainTexAsAlpha ("Use Main Tex As Alpha", Float) = 1
        _MainUVSet ("Main UV Set", Float) = 0
        _MainTexUVSpeed ("Main UV Speed", Vector) = (0,0,0,0)
        _MainTexUVRotate ("Main UV Rotation", Float) = 0
        _ForceMoveToFarPlane ("Force Far Plane", Float) = 0
        [Toggle(_USE_GRID_LINE)] _UseGridLine ("Use Grid Line", Float) = 0
        _GridLineWidth ("Grid Line Width", Float) = 1
        _UseNearCameraFade ("Use Near Camera Fade", Float) = 0
        _NearCameraFadeDistanceStart ("Near Fade Start", Float) = 0.001
        _NearCameraFadeDistanceEnd ("Near Fade End", Float) = 10
        _NearCameraFadeDistanceStart2 ("Far Fade Start", Float) = 120
        _NearCameraFadeDistanceEnd2 ("Far Fade End", Float) = 100
        [Toggle(_ALPHATEST_ON)] _UseAlphaTest ("Use Alpha Test", Float) = 0
        _AlphaClipThreshold ("Alpha Clip Threshold", Float) = 1
        _ExpThreshold ("Exp Threshold", Float) = 1
        _ExpIntensity ("Exp Intensity", Float) = 0
        [HideInInspector] _VFXParams0 ("VFX Params 0", Vector) = (0,0,0,0)
        [HideInInspector] _VFXParams1 ("VFX Params 1", Vector) = (1,1,1,1)
        [HideInInspector] _GlobalMipBias ("Global Mip Bias", Float) = 0
        [HideInInspector] _SrcBlend ("Source Blend", Float) = 5
        [HideInInspector] _DstBlend ("Destination Blend", Float) = 10
        [HideInInspector] _AlphaSrcBlend ("Alpha Source Blend", Float) = 1
        [HideInInspector] _AlphaDstBlend ("Alpha Destination Blend", Float) = 10
        [HideInInspector] _ZTest ("Z Test", Float) = 4
        [HideInInspector] _ZWriteMode ("Z Write", Float) = 0
        [HideInInspector] _CullMode ("Cull", Float) = 0
    }

    SubShader
    {
        Tags { "RenderType"="Transparent" "Queue"="Transparent" }

        Pass
        {
            Name "ForwardOnly"
            Tags { "LightMode"="ForwardOnly" }
            Blend [_SrcBlend] [_DstBlend], [_AlphaSrcBlend] [_AlphaDstBlend]
            ZTest [_ZTest]
            ZWrite [_ZWriteMode]
            Cull [_CullMode]

            CGPROGRAM
            #pragma target 5.0
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma shader_feature_local _USE_GRID_LINE
            #pragma shader_feature_local _ALPHATEST_ON
            #include "UnityCG.cginc"

            Texture2D _MainTex;
            SamplerState sampler_LinearClamp;
            float4 _MainTex_ST;
            float4 _TintColor;
            float _TintColorIntensity;
            float _TintColorAlpha;
            float _DisableVertColor;
            float _InParticle;
            float _IgnorePostExposure;
            float _UseMainTexAsAlpha;
            float _MainUVSet;
            float4 _MainTexUVSpeed;
            float _MainTexUVRotate;
            float _ForceMoveToFarPlane;
            float _GridLineWidth;
            float _UseNearCameraFade;
            float _NearCameraFadeDistanceStart;
            float _NearCameraFadeDistanceEnd;
            float _NearCameraFadeDistanceStart2;
            float _NearCameraFadeDistanceEnd2;
            float _AlphaClipThreshold;
            float _ExpThreshold;
            float _ExpIntensity;
            float4 _VFXParams0;
            float4 _VFXParams1;
            float _GlobalMipBias;
            float4 _ExposureParams;

            static const float3 EndfieldLuminance =
                float3(0.21267290413379669189453125,
                       0.715152204036712646484375,
                       0.072175003588199615478515625);
            static const float EndfieldDeg2Rad =
                0.01745329238474369049072265625;
            static const float EndfieldFloatMin =
                1.1754943508222875079687365372222e-38;
            static const float EndfieldGridScale =
                0.00999999977648258209228515625;

            struct Attributes
            {
                float3 vertex : POSITION;
                float3 normal : NORMAL;
                float4 color : COLOR;
                float4 uv0 : TEXCOORD0;
                float4 uv1 : TEXCOORD1;
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float4 uv : TEXCOORD0;
                float4 color : TEXCOORD1;
                float3 worldPos : TEXCOORD2;
            };

            float2 BuildMainUv(float4 uv0, float4 uv1)
            {
                float custom1X = uv1.x * _InParticle;
                bool polarSet = (0.0 != _MainUVSet);
                float baseU = polarSet
                    ? mad(uv0.z, _InParticle, -custom1X) + uv1.x
                    : uv0.x;
                float baseV = polarSet
                    ? mad(uv0.w, _InParticle, -(uv1.y * _InParticle)) + uv1.y
                    : uv0.y;
                float2 p;
                p.x = mad(_MainTexUVSpeed.z, custom1X,
                          mad(_MainTexUVSpeed.x, _Time.y, baseU)) - 0.5;
                p.y = mad(_MainTexUVSpeed.w, custom1X,
                          mad(_MainTexUVSpeed.y, _Time.y, baseV)) - 0.5;
                float angle = EndfieldDeg2Rad * _MainTexUVRotate;
                float sineValue;
                float cosineValue;
                sincos(angle, sineValue, cosineValue);
                float2 result;
                result.x = mad(
                    dot(p, float2(cosineValue, sineValue)) + 0.5,
                    _MainTex_ST.x,
                    _MainTex_ST.z);
                result.y = mad(
                    dot(p, float2(-sineValue, cosineValue)) + 0.5,
                    _MainTex_ST.y,
                    _MainTex_ST.w);
                return result;
            }

            Varyings BuildBaseVaryings(Attributes input)
            {
                Varyings output;
                output.positionCS = UnityObjectToClipPos(input.vertex);
                if (0.0 != _ForceMoveToFarPlane)
                {
                #if defined(UNITY_REVERSED_Z)
                    output.positionCS.z = 0.0;
                #else
                    output.positionCS.z = output.positionCS.w;
                #endif
                }
                output.uv.xy = input.uv0.xy;
                output.uv.zw = BuildMainUv(input.uv0, input.uv1);
                output.color = input.color;
                output.worldPos =
                    mul(unity_ObjectToWorld, float4(input.vertex, 1.0)).xyz;
                return output;
            }

            Varyings Vert(Attributes input)
            {
                Varyings output = BuildBaseVaryings(input);
            #ifdef _USE_GRID_LINE
                float3 column0 = float3(
                    unity_ObjectToWorld[0].x,
                    unity_ObjectToWorld[1].x,
                    unity_ObjectToWorld[2].x);
                float3 column1 = float3(
                    unity_ObjectToWorld[0].y,
                    unity_ObjectToWorld[1].y,
                    unity_ObjectToWorld[2].y);
                float3 column2 = float3(
                    unity_ObjectToWorld[0].z,
                    unity_ObjectToWorld[1].z,
                    unity_ObjectToWorld[2].z);
                float3 scaledNormal = float3(
                    input.normal.x / dot(column0, column0),
                    input.normal.y / dot(column1, column1),
                    input.normal.z / dot(column2, column2));
                float3 normalWS = mul((float3x3)unity_ObjectToWorld, scaledNormal);
                normalWS *= rsqrt(max(dot(normalWS, normalWS), EndfieldFloatMin));

                float3 viewPoint =
                    mul(unity_ObjectToWorld, float4(input.uv1.xyz, 1.0)).xyz;
                float3 viewVector = _WorldSpaceCameraPos - viewPoint;
                float3 viewDirection =
                    viewVector * rsqrt(max(dot(viewVector, viewVector), EndfieldFloatMin));
                float3 tangent = cross(normalWS, viewDirection);
                tangent *= rsqrt(max(dot(tangent, tangent), EndfieldFloatMin));

                float projectedX = dot(UNITY_MATRIX_VP[0].xyz, tangent);
                float projectedY = dot(UNITY_MATRIX_VP[1].xyz, tangent);
                float inverseProjectedLength = rsqrt(max(
                    dot(float2(projectedX, projectedY),
                        float2(projectedX, projectedY)),
                    EndfieldFloatMin));
                float offsetX = inverseProjectedLength * projectedX *
                    (_ScreenParams.y / _ScreenParams.x) *
                    _GridLineWidth * EndfieldGridScale;
                float offsetY = inverseProjectedLength * projectedY *
                    _GridLineWidth * EndfieldGridScale;
                float minimumPixelWidth =
                    (0.75 / min(_ScreenParams.x, _ScreenParams.y)) *
                    output.positionCS.w;
                float snappedX = abs(offsetX) < minimumPixelWidth
                    ? sign(offsetX) * minimumPixelWidth
                    : offsetX;
                float snappedY = abs(offsetY) < minimumPixelWidth
                    ? sign(offsetY) * minimumPixelWidth
                    : offsetY;
                output.positionCS.xy += float2(snappedX, snappedY);
            #endif
                return output;
            }

            float4 Frag(Varyings input) : SV_Target
            {
                float4 mainSample = _MainTex.SampleBias(
                    sampler_LinearClamp,
                    input.uv.zw,
                    _GlobalMipBias);
                float3 mainRgb = lerp(mainSample.rgb, 1.0.xxx,
                                      _UseMainTexAsAlpha);
                bool disableVertexColor = 0.0 != _DisableVertColor;
                float exposureDivisor = mad(
                    _IgnorePostExposure,
                    _ExposureParams.x - 1.0,
                    1.0);
                float3 vertexRgb = disableVertexColor
                    ? 1.0.xxx
                    : input.color.rgb;
                float3 color = vertexRgb * _TintColor.rgb *
                    _TintColorIntensity * mainRgb /
                    max(exposureDivisor, 1e-6);
                float3 glow = clamp(
                    mad(max(color - _ExpThreshold, 0.0),
                        _ExpIntensity,
                        color),
                    0.0,
                    1000.0);
                float luminance = dot(glow, EndfieldLuminance);
                float3 outputColor =
                    lerp(luminance.xxx, glow, _VFXParams1.w) *
                    _VFXParams1.xyz;

                float viewZ = mul(UNITY_MATRIX_V, float4(input.worldPos, 1.0)).z;
                float distanceToCamera = abs(viewZ);
                float farRing = saturate(
                    (distanceToCamera - _NearCameraFadeDistanceStart2) /
                    (_NearCameraFadeDistanceEnd2 -
                     _NearCameraFadeDistanceStart2));
                float nearRing = saturate(
                    (distanceToCamera - _NearCameraFadeDistanceStart) /
                    (_NearCameraFadeDistanceEnd -
                     _NearCameraFadeDistanceStart));
                float fade = 0.0 != _UseNearCameraFade
                    ? farRing * nearRing
                    : 1.0;
                float mainAlpha = lerp(
                    mainSample.a,
                    mainSample.r,
                    _UseMainTexAsAlpha);
                float vertexAlpha = disableVertexColor ? 1.0 : input.color.a;
                float alpha = saturate(
                    fade * mainAlpha * vertexAlpha *
                    _TintColor.a * _TintColorAlpha);
            #ifdef _ALPHATEST_ON
                clip(alpha - _AlphaClipThreshold);
            #endif
                return float4(outputColor, alpha);
            }
            ENDCG
        }
    }
    Fallback Off
}
