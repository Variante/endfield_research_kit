Shader "Hidden/Endfield/HGRPCompat/RecoveredCharInfoLutBuilder2D"
{
    SubShader
    {
        Tags { "RenderType"="Opaque" }
        Cull Off
        ZWrite Off
        ZTest Always

        Pass
        {
            Name "RECOVERED_CHARINFO_LUT_BUILDER_2D"

            CGPROGRAM
            #pragma target 4.5
            #pragma vertex Vert
            #pragma fragment Frag
            #include "EndfieldHGRPRecoveredPost.cginc"

            struct Varyings
            {
                float4 position : SV_POSITION;
                float2 uv : TEXCOORD0;
            };

            Varyings Vert(uint vertexID : SV_VertexID)
            {
                // Exact full-screen triangle convention from the shipped pass.
                uint2 integerCorner = uint2(
                    (vertexID << 1) & 2u,
                    vertexID & 2u);
                float2 corner = float2(integerCorner);
                Varyings output;
                output.position = float4(corner * 2.0 - 1.0, 1.0, 1.0);
                output.uv = float2(corner.x, 1.0 - corner.y);
                return output;
            }

            float3 EF_RecoveredLogCToLinear(float3 logC)
            {
                return 0.179999992 *
                    (exp2(13.6054821 * (logC - 0.386036009)) - 0.0479959995);
            }

            float3 EF_ApplyRecoveredNeutralWhiteBalance(float3 linearSRGB)
            {
                // CharInfo temperature/tint are zero, but the shipped native
                // GetColorBalanceCoeffs path does not round to exact (1,1,1).
                // These three float32 results are recovered from that path.
                float3 lms = float3(
                    dot(float3(0.390404999, 0.549941003, 0.00892631989), linearSRGB),
                    dot(float3(0.070841603, 0.963172019, 0.00135775004), linearSRGB),
                    dot(float3(0.0231081992, 0.128021002, 0.936245024), linearSRGB));
                lms *= float3(1.00000036, 0.999999285, 1.00000346);
                return float3(
                    dot(float3(2.85846996, -1.62879002, -0.0248910002), lms),
                    dot(float3(-0.210181996, 1.15820003, 0.000324280991), lms),
                    dot(float3(-0.0418119989, -0.118169002, 1.06867003), lms));
            }

            float3 EF_LinearAP0ToACEScc(float3 linearAP0)
            {
                linearAP0 = clamp(linearAP0, 0.0, 65504.0);
                float3 low =
                    (log2(linearAP0 * 0.5 + 0.00001525878) + 9.72000027) *
                    0.0570776239;
                float3 high =
                    (log2(max(linearAP0, 0.0000000001)) + 9.72000027) *
                    0.0570776239;
                float3 useLow = 1.0 - step(0.0000305175708, linearAP0);
                return lerp(high, low, useLow);
            }

            float3 EF_ACESccToLinearAP0(float3 acescc)
            {
                float3 exponent = exp2(acescc * 17.5200005 - 9.72000027);
                float3 low = (exponent - 0.0000152587891) * 2.0;
                float3 middleOrHigh = lerp(
                    exponent,
                    65504.0.xxx,
                    step(1.46799648, acescc));
                return lerp(
                    middleOrHigh,
                    low,
                    1.0 - step(-0.301369876, acescc));
            }

            float4 Frag(Varyings input) : SV_Target
            {
                // Shipped _Lut_Params for N=32:
                // (32, 0.5/(32*32), 0.5/32, 32/31).
                const float size = 32.0;
                const float halfTexelX = 0.00048828125;
                const float halfTexelY = 0.015625;
                const float scaleToUnitGrid = 1.032258064516129;

                float2 coordinate = input.uv - float2(halfTexelX, halfTexelY);
                float red = frac(size * coordinate.x);
                float blue = coordinate.x - red / size;
                float3 logC = float3(red, coordinate.y, blue) * scaleToUnitGrid;
                float3 linearSRGB = EF_RecoveredLogCToLinear(logC);

                linearSRGB = EF_ApplyRecoveredNeutralWhiteBalance(linearSRGB);
                float3 linearAP0 = EF_LinearSRGBToAP0(linearSRGB);

                // Contrast is neutral (1.0), but preserve the shipped ACEScc
                // encode/decode path and its clamps rather than deleting it.
                float3 acescc = EF_LinearAP0ToACEScc(linearAP0);
                acescc = (acescc - 0.413588405) * 1.0 + 0.413588405;
                linearAP0 = EF_ACESccToLinearAP0(acescc);

                float3 acescg = EF_AP0ToAP1(linearAP0);
                acescg = EF_ApplyCharInfoGradeAP1(
                    acescg,
                    1.08,
                    0.89473686);
                return float4(EF_ACESModified(acescg), 1.0);
            }
            ENDCG
        }

        Pass
        {
            Name "VERIFY_EXACT_ENDMINF_LUT_SENTINELS"

            CGPROGRAM
            #pragma target 4.5
            #pragma vertex VertVerify
            #pragma fragment FragVerify

            sampler2D _ExactEndminfLut;

            struct VerifyVaryings
            {
                float4 position : SV_POSITION;
            };

            VerifyVaryings VertVerify(uint vertexID : SV_VertexID)
            {
                uint2 corner = uint2((vertexID << 1) & 2u, vertexID & 2u);
                VerifyVaryings output;
                output.position = float4(float2(corner) * 2.0 - 1.0, 1.0, 1.0);
                return output;
            }

            float4 FragVerify(float4 position : SV_POSITION) : SV_Target
            {
                uint lane = min((uint)position.x, 4u);
                const uint2 coordinates[5] =
                {
                    uint2(0u, 0u),
                    uint2(31u, 0u),
                    uint2(0u, 31u),
                    uint2(992u, 0u),
                    uint2(1023u, 31u)
                };
                float2 uv = (float2(coordinates[lane]) + 0.5) /
                    float2(1024.0, 32.0);
                return tex2Dlod(_ExactEndminfLut, float4(uv, 0.0, 0.0));
            }
            ENDCG
        }
    }

    Fallback Off
}
