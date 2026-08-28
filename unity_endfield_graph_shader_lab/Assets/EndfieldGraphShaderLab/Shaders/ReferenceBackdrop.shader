Shader "Endfield/CharacterRecovery/ReferenceBackdrop"
{
    Properties
    {
        _TopColor ("Top Color", Color) = (0.78,0.79,0.78,1)
        _BottomColor ("Bottom Color", Color) = (0.55,0.56,0.55,1)
        _GridColor ("Grid Color", Color) = (0.34,0.35,0.34,1)
        _SilhouetteColor ("Silhouette Color", Color) = (0.42,0.43,0.42,1)
        _GridOpacity ("Grid Opacity", Range(0,1)) = 0.18
        _DiagonalOpacity ("Diagonal Opacity", Range(0,1)) = 0.12
        _GridColumns ("Grid Columns", Float) = 6
        _GridRows ("Grid Rows", Float) = 5
        _GridPhaseX ("Grid Phase X", Float) = 0.08
        _GridPhaseY ("Grid Phase Y", Float) = 0.25
        _SilhouetteOpacity ("Silhouette Opacity", Range(0,1)) = 0.22
        _BottomVignette ("Bottom Vignette", Range(0,1)) = 0.22
        _BottomVignetteFloor ("Bottom Vignette Floor", Range(0,1)) = 0.02
        _BottomVignetteHeight ("Bottom Vignette Height", Range(0.05,1)) = 0.55
        // Scene-linear multiplier applied before the recovered HGRP post
        // chain. Values >= ~32 keep a neutral backdrop above the shipped
        // ACES_modified highlight-compression knee (acescg luma 2.0) across
        // the whole frame, so it reaches exact display white after post.
        _HdrBoost ("HDR Boost", Float) = 1
    }

    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Background" }
        Cull Off
        ZWrite Off
        ZTest LEqual

        Pass
        {
            Tags { "LightMode"="SRPDefaultUnlit" }
            CGPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #include "UnityCG.cginc"

            fixed4 _TopColor;
            fixed4 _BottomColor;
            fixed4 _GridColor;
            fixed4 _SilhouetteColor;
            float _GridOpacity;
            float _DiagonalOpacity;
            float _GridColumns;
            float _GridRows;
            float _GridPhaseX;
            float _GridPhaseY;
            float _SilhouetteOpacity;
            float _BottomVignette;
            float _BottomVignetteFloor;
            float _BottomVignetteHeight;
            float _HdrBoost;

            struct appdata
            {
                float4 vertex : POSITION;
                float2 uv : TEXCOORD0;
            };

            struct v2f
            {
                float4 pos : SV_POSITION;
                float2 uv : TEXCOORD0;
                float4 screenPos : TEXCOORD1;
            };

            v2f Vert(appdata v)
            {
                v2f o;
                o.pos = UnityObjectToClipPos(v.vertex);
                o.uv = v.uv;
                o.screenPos = ComputeScreenPos(o.pos);
                return o;
            }

            float GridLine(float value, float width)
            {
                float cell = frac(value);
                float local = min(cell, 1.0 - cell);
                return 1.0 - smoothstep(0.0, width, local);
            }

            float Ellipse(float2 uv, float2 center, float2 radius)
            {
                float2 p = (uv - center) / radius;
                return 1.0 - smoothstep(0.92, 1.02, dot(p, p));
            }

            float4 Frag(v2f i) : SV_Target
            {
                float2 uv = i.uv;
                float2 screenUv = i.screenPos.xy / max(i.screenPos.w, 1.0e-6);
                float3 color = lerp(_BottomColor.rgb, _TopColor.rgb, saturate(uv.y));

                float vertical = GridLine(uv.x * max(_GridColumns, 1.0) + _GridPhaseX, 0.012);
                float horizontal = GridLine(uv.y * max(_GridRows, 1.0) + _GridPhaseY, 0.010);
                float diagonalA = GridLine((uv.x + uv.y * 0.34) * 4.0, 0.010);
                float diagonalB = GridLine((uv.x - uv.y * 0.22) * 3.1, 0.008);
                float grid = saturate(max(vertical, horizontal) * _GridOpacity + max(diagonalA, diagonalB) * _DiagonalOpacity);
                color = lerp(color, _GridColor.rgb, grid);

                float body = Ellipse(uv, float2(0.18, 0.46), float2(0.20, 0.32));
                float head = Ellipse(uv, float2(0.16, 0.67), float2(0.12, 0.15));
                float shoulder = Ellipse(uv, float2(0.28, 0.39), float2(0.18, 0.11));
                float hornA = Ellipse(uv, float2(0.08, 0.84), float2(0.035, 0.22));
                float hornB = Ellipse(uv, float2(0.24, 0.82), float2(0.035, 0.22));
                float silhouette = saturate(body + head + shoulder + hornA + hornB);
                silhouette *= 1.0 - smoothstep(0.05, 0.56, uv.x);

                float hatch = step(0.42, frac((uv.x * 56.0 + uv.y * 82.0) * 0.5));
                float dotted = silhouette * lerp(0.34, 1.0, hatch);
                color = lerp(color, _SilhouetteColor.rgb, dotted * _SilhouetteOpacity);

                float bottomShade = (1.0 - smoothstep(
                    _BottomVignetteFloor,
                    max(_BottomVignetteHeight, _BottomVignetteFloor + 0.001),
                    screenUv.y)) *
                    _BottomVignette;
                color *= 1.0 - bottomShade;

                return float4(color * max(_HdrBoost, 0.0), 1.0);
            }
            ENDCG
        }
    }
    FallBack Off
}
