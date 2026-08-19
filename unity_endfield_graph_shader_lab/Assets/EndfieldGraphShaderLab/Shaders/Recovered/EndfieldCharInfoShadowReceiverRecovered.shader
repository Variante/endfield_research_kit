Shader "Endfield/Recovered/CharInfo/CharacterNPR_ShadowReceiver"
{
    Properties
    {
        [MainColor] _ShadowColor ("Shadow Color", Color) = (0.5, 0.5, 0.5, 1)
        _CapsuleAoColor ("Capsule AO Color", Color) = (0.25, 0.25, 0.25, 1)
        [ToggleUI] _DisableCharacterSelfShadow ("Disable Character Self Shadow", Float) = 0
        [ToggleUI] _DisableSceneShadow ("Disable Scene Shadow", Float) = 0
        [ToggleUI] _CircleFade ("Circle Fade", Float) = 0
        _CircleFadeDistance ("Circle Fade Distance", Range(0.01, 3)) = 0.5
        _CircleFadeSmoothness ("Circle Fade Smoothness", Range(0, 3)) = 0
    }

    SubShader
    {
        Tags
        {
            "Queue" = "Transparent"
            "RenderType" = "Transparent"
        }

        Pass
        {
            Name "ShadowReceiver"
            Tags { "LightMode" = "ForwardOnly" }

            // Exact selected CharacterNPR_ShadowReceiver render state.
            Blend Zero SrcColor, Zero SrcColor
            ZWrite Off
            Stencil
            {
                Ref 32
                ReadMask 32
                Comp NotEqual
                Pass Keep
                Fail Keep
                ZFail Keep
            }

            HLSLPROGRAM
            #pragma target 5.0
            #pragma vertex Vert
            #pragma fragment Frag
            #include "UnityCG.cginc"
            #include "../HGRPCompat/EndfieldHGRPCharacterLighting.cginc"

            float4 _ShadowColor;
            float4 _CapsuleAoColor;
            float _DisableCharacterSelfShadow;
            float _DisableSceneShadow;
            float _CircleFade;
            float _CircleFadeDistance;
            float _CircleFadeSmoothness;

            // Recovered capsule-AO inputs. The receiver consumes the
            // VisibilitySH screen buffer and the exact _ABLutTex coefficient
            // table; see shadow_receiver_capsule_ao_contract.json. Every value
            // below is source-closed, and the term stays disabled until the
            // producer publishes, so an unpublished frame keeps the neutral
            // zero-occlusion endpoint rather than a fitted darkening.
            Texture2D _EndfieldRecoveredVisibilitySH;
            SamplerState sampler_EndfieldRecoveredVisibilitySH;
            Texture2D _EndfieldRecoveredABLutTex;
            SamplerState sampler_EndfieldRecoveredABLutTex;
            float _EndfieldRecoveredVisibilitySHReady;
            float4 _EndfieldRecoveredVisibilitySHScreenScale;
            float4 _EndfieldRecoveredVisibilitySHCoeffParams;
            float4 _EndfieldRecoveredVisibilitySHEncodeParams;

            // Exact SH exponentiation of the log-space visibility buffer.
            // 0.282095 is Y00, 3.544908 is its inverse 2*sqrt(pi), -0.325735 is
            // the band-1 irradiance convolution weight, and 0.406977 is
            // Y00*log2(e) so that exp2 reproduces the source exp(Y00*x).
            float EndfieldRecoveredCapsuleOcclusion(float2 screenUV)
            {
                float4 sh = _EndfieldRecoveredVisibilitySH.SampleLevel(
                    sampler_EndfieldRecoveredVisibilitySH, screenUV, 0.0);
                if (all(abs(sh) <= 1.0e-4))
                    return 0.0;

                // Normalise by halving, counting the halvings so the trailing
                // self-products can undo them.
                float scale = 1.0;
                float working = length(sh.yzw);
                int halvings = 0;
                [loop]
                for (int step = 0; step < 16; ++step)
                {
                    if (working <= 4.6)
                        break;
                    scale *= 0.5;
                    working *= 0.5;
                    ++halvings;
                }
                sh *= scale;

                float coordinate =
                    length(sh.yzw) * _EndfieldRecoveredVisibilitySHEncodeParams.x +
                    _EndfieldRecoveredVisibilitySHEncodeParams.y;
                coordinate = (coordinate * 255.0 + 0.5) * (1.0 / 256.0);

                // B and A are zero across the whole table; the source reads xy.
                float2 lut = _EndfieldRecoveredABLutTex.SampleLevel(
                    sampler_EndfieldRecoveredABLutTex,
                    float2(coordinate, 0.5),
                    0.0).xy;
                float2 coefficients =
                    lut * _EndfieldRecoveredVisibilitySHCoeffParams.xy +
                    _EndfieldRecoveredVisibilitySHCoeffParams.zw;

                float4 band = float4(
                    coefficients.x * 3.544908,
                    coefficients.y * sh.y,
                    coefficients.y * sh.z,
                    coefficients.y * sh.w);
                band *= exp2(sh.x * 0.406977);

                [loop]
                for (int product = 0; product < halvings; ++product)
                {
                    float4 scaled = band * 0.282095;
                    band = float4(
                        dot(scaled, band),
                        dot(scaled.yx, band.xy),
                        dot(scaled.zx, band.xz),
                        dot(scaled.wx, band.xw));
                }

                float2 visibility = float2(band.y * -0.325735, band.x * 0.282095);
                return 1.0 - min(max(visibility.x + visibility.y, 0.0), 1.0);
            }

            struct Attributes
            {
                float3 vertex : POSITION;
                float3 normal : NORMAL;
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 worldPos : TEXCOORD0;
                float3 normalWS : TEXCOORD1;
            };

            Varyings Vert(Attributes input)
            {
                Varyings output;
                output.positionCS = UnityObjectToClipPos(input.vertex);
                output.worldPos =
                    mul(unity_ObjectToWorld, float4(input.vertex, 1.0)).xyz;
                output.normalWS = UnityObjectToWorldNormal(input.normal);
                return output;
            }

            float4 Frag(Varyings input) : SV_Target
            {
                float4 shadowCoord = EndfieldHGRPCharacterShadowCoord(
                    input.worldPos,
                    normalize(input.normalWS));
                float characterShadow =
                    EndfieldHGRPSampleCharacterShadowWithStrength(
                        shadowCoord,
                        input.positionCS.xy,
                        1.0);

                // The exact source material disables the scene-shadow branch,
                // so the scene term is the source identity value. The separate
                // recovered character atlas remains active.
                float sceneTerm = lerp(1.0, 1.0, _DisableSceneShadow);
                float characterTerm = lerp(
                    characterShadow,
                    1.0,
                    _DisableCharacterSelfShadow);
                float shadowMask = saturate(
                    0.949999988079071044921875 -
                    min(sceneTerm, characterTerm)) * _ShadowColor.a;

                float3 objectOrigin = float3(
                    unity_ObjectToWorld._m03,
                    unity_ObjectToWorld._m13,
                    unity_ObjectToWorld._m23);
                float fadeEnd =
                    _CircleFadeDistance + _CircleFadeSmoothness;
                float radial = saturate(
                    (distance(input.worldPos, objectOrigin) - fadeEnd) /
                    (_CircleFadeDistance - fadeEnd));
                float smoothRadial =
                    radial * radial * mad(radial, -2.0, 3.0);
                float fadedMask = 0.0 != _CircleFade
                    ? smoothRadial * shadowMask
                    : shadowMask;

                float3 shadowTint = lerp(
                    1.0.xxx,
                    _ShadowColor.rgb,
                    fadedMask);
                // The producer publishes readiness only after it has written
                // the VisibilitySH buffer for this camera. Without it the
                // neutral empty-buffer endpoint is zero occlusion.
                float capsuleAo = _EndfieldRecoveredVisibilitySHReady > 0.5
                    ? EndfieldRecoveredCapsuleOcclusion(
                        input.positionCS.xy *
                        _EndfieldRecoveredVisibilitySHScreenScale.xy)
                    : 0.0;
                float3 outputColor = lerp(
                    shadowTint,
                    _CapsuleAoColor.rgb,
                    capsuleAo);
                return float4(outputColor, 1.0);
            }
            ENDHLSL
        }
    }
}
