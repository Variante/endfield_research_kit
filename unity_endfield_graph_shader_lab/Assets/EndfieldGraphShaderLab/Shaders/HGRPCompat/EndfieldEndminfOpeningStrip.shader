Shader "Hidden/Endfield/HGRPCompat/EndminfOpeningStrip"
{
    Properties
    {
        _MainTex ("Source", 2D) = "black" {}
    }

    SubShader
    {
        Tags { "RenderType"="Opaque" }
        Cull Off
        ZWrite Off
        ZTest Always

        Pass
        {
            CGPROGRAM
            #pragma target 3.0
            #pragma vertex vert_img
            #pragma fragment Frag
            #include "UnityCG.cginc"

            sampler2D _MainTex;
            // x=envelope, y=max X displacement in pixels,
            // z=RGB edge separation in pixels, w=effect-local elapsed seconds.
            float4 _EndminfOpeningStripParams;
            float4 _EndminfOpeningStripSourceSize; // width, height, 1/width, 1/height

            float Hash11(float value)
            {
                return frac(sin(value * 91.3458 + 17.17) * 47453.5453);
            }

            float4 Frag(v2f_img input) : SV_Target
            {
                float2 uv = input.uv;
                float pixelY = uv.y * _EndminfOpeningStripSourceSize.y;

                // Six-pixel cells are grouped by a slowly changing offset.
                // The resulting boundaries stay perfectly horizontal while
                // their authored-looking heights vary between roughly 6 and
                // 30 pixels instead of becoming a regular scanline pattern.
                float cell = floor(pixelY / 6.0);
                float group = floor(cell / 4.0);
                float groupingOffset = floor(Hash11(group + 2.0) * 3.0);
                float band = floor((cell + groupingOffset) / 3.0);

                // Retail changes fracture ownership on frame boundaries. Keep
                // that cadence deterministic at 60 Hz; every pixel in a band
                // receives exactly the same horizontal displacement.
                float frame = floor(_EndminfOpeningStripParams.w * 60.0 + 0.5);
                float signedOffset = Hash11(band * 5.13 + frame * 1.71) * 2.0 - 1.0;
                float sparse = step(0.22, Hash11(band * 2.37 + frame * 0.43));
                float displacementPixels = signedOffset * sparse *
                    _EndminfOpeningStripParams.y;
                float displacementUv = displacementPixels *
                    _EndminfOpeningStripSourceSize.z;
                float chromaUv = _EndminfOpeningStripParams.z *
                    _EndminfOpeningStripSourceSize.z * sign(signedOffset + 1e-5);

                float2 shiftedUv = float2(
                    saturate(uv.x + displacementUv),
                    uv.y);
                float red = tex2Dlod(
                    _MainTex,
                    float4(saturate(shiftedUv + float2(chromaUv, 0.0)), 0.0, 0.0)).r;
                float green = tex2Dlod(
                    _MainTex,
                    float4(shiftedUv, 0.0, 0.0)).g;
                float blue = tex2Dlod(
                    _MainTex,
                    float4(saturate(shiftedUv - float2(chromaUv, 0.0)), 0.0, 0.0)).b;
                float alpha = tex2Dlod(
                    _MainTex,
                    float4(shiftedUv, 0.0, 0.0)).a;
                return float4(red, green, blue, alpha);
            }
            ENDCG
        }
    }
    Fallback Off
}
