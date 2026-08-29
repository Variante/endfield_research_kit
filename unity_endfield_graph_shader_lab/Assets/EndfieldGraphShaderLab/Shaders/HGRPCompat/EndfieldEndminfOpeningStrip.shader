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
            sampler2D _EndminfOpeningStripSelector;
            // x=envelope, y=max X displacement in pixels,
            // z=RGB edge separation in pixels, w=effect-local elapsed seconds.
            float4 _EndminfOpeningStripParams;
            float4 _EndminfOpeningStripSourceSize; // width, height, 1/width, 1/height

            bool TryGetMeasuredBand(
                int frame,
                int bandIndex,
                out float4 rectangle,
                out float2 shift)
            {
                rectangle = 0.0;
                shift = 0.0;
                // rectangle = destination x0/x1/top-y0/top-y1 at the
                // authoritative 1920x1080 comparison resolution;
                // shift = rightward source displacement / RGB split pixels.
                if (frame == 4 && bandIndex == 0) { rectangle=float4(902,1007,663,684); shift=float2(253,2.5); return true; }
                if (frame == 6 && bandIndex == 0) { rectangle=float4(744,779,250,255); shift=float2(234,2.5); return true; }
                if (frame == 7 && bandIndex == 0) { rectangle=float4(656,756,251,262); shift=float2(183,2.0); return true; }
                if (frame == 7 && bandIndex == 1) { rectangle=float4(903,989,662,680); shift=float2(201,2.0); return true; }
                if (frame == 7 && bandIndex == 2) { rectangle=float4(839,936,805,819); shift=float2(154,2.0); return true; }
                if (frame == 8 && bandIndex == 0) { rectangle=float4(703,821,447,454); shift=float2(141,1.5); return true; }
                if (frame == 8 && bandIndex == 1) { rectangle=float4(834,993,783,799); shift=float2(240,2.5); return true; }
                if (frame == 9 && bandIndex == 0) { rectangle=float4(813,904,430,442); shift=float2(242,2.5); return true; }
                if (frame == 9 && bandIndex == 1) { rectangle=float4(836,958,737,758); shift=float2(168,2.0); return true; }
                if (frame == 10 && bandIndex == 0) { rectangle=float4(748,837,392,395); shift=float2(195,2.0); return true; }
                if (frame == 10 && bandIndex == 1) { rectangle=float4(801,883,520,533); shift=float2(193,2.0); return true; }
                if (frame == 11 && bandIndex == 0) { rectangle=float4(683,779,403,419); shift=float2(118,1.5); return true; }
                if (frame == 11 && bandIndex == 1) { rectangle=float4(733,827,502,521); shift=float2(124,1.5); return true; }
                if (frame == 12 && bandIndex == 0) { rectangle=float4(780,879,566,571); shift=float2(153,2.0); return true; }
                if (frame == 18 && bandIndex == 0) { rectangle=float4(739,832,414,422); shift=float2(116,1.5); return true; }
                if (frame == 19 && bandIndex == 0) { rectangle=float4(739,828,413,422); shift=float2(94,1.5); return true; }
                if (frame == 20 && bandIndex == 0) { rectangle=float4(752,821,413,420); shift=float2(77,1.0); return true; }
                return false;
            }

            float4 Frag(v2f_img input) : SV_Target
            {
                float2 uv = input.uv;
                float2 retailPixel = float2(
                    uv.x * _EndminfOpeningStripSourceSize.x,
                    (1.0 - uv.y) * _EndminfOpeningStripSourceSize.y) *
                    float2(1920.0 / _EndminfOpeningStripSourceSize.x,
                           1080.0 / _EndminfOpeningStripSourceSize.y);
                int frame = (int)floor(
                    _EndminfOpeningStripParams.w * 60.0 + 0.5);
                float2 activeShift = 0.0;
                float activeBand = 0.0;
                [unroll]
                for (int bandIndex = 0; bandIndex < 3; ++bandIndex)
                {
                    float4 rectangle;
                    float2 shift;
                    if (TryGetMeasuredBand(frame, bandIndex, rectangle, shift))
                    {
                        float inside = step(rectangle.x, retailPixel.x) *
                            step(retailPixel.x, rectangle.y) *
                            step(rectangle.z, retailPixel.y) *
                            step(retailPixel.y, rectangle.w);
                        if (inside > 0.5)
                        {
                            activeShift = shift;
                            activeBand = 1.0;
                        }
                    }
                }

                float displacementPixels = activeShift.x *
                    (_EndminfOpeningStripSourceSize.x / 1920.0);
                float displacementUv = displacementPixels *
                    _EndminfOpeningStripSourceSize.z;
                float chromaUv = activeShift.y *
                    (_EndminfOpeningStripSourceSize.x / 1920.0) *
                    _EndminfOpeningStripSourceSize.z;

                float2 shiftedUv = float2(
                    saturate(uv.x - displacementUv),
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
                float4 shifted = float4(red, green, blue, alpha);

                // GBufferA is cleared to zero and receives selector bits only
                // where the current CharacterPrePass owns a pixel. Sample it
                // at the displaced coordinate: copied character bands may
                // protrude into the static field, while portrait/GridFar
                // samples remain untouched.
                float4 selector = tex2Dlod(
                    _EndminfOpeningStripSelector,
                    float4(shiftedUv, 0.0, 0.0));
                float shiftedOwner = step(
                    1e-5,
                    dot(abs(selector), float4(1.0, 1.0, 1.0, 1.0)));
                float4 destinationSelector = tex2Dlod(
                    _EndminfOpeningStripSelector,
                    float4(uv, 0.0, 0.0));
                float destinationOwner = step(
                    1e-5,
                    dot(abs(destinationSelector),
                        float4(1.0, 1.0, 1.0, 1.0)));
                float4 original = tex2Dlod(
                    _MainTex,
                    float4(uv, 0.0, 0.0));
                return lerp(
                    original,
                    shifted,
                    saturate(_EndminfOpeningStripParams.x) *
                    activeBand * shiftedOwner * (1.0 - destinationOwner));
            }
            ENDCG
        }
    }
    Fallback Off
}
