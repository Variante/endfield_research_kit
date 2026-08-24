#ifndef ENDFIELD_CHARACTER_RECOVERED_COMMON_INCLUDED
#define ENDFIELD_CHARACTER_RECOVERED_COMMON_INCLUDED

// Shared approximations of the symbol-restored HGRP CharacterNPR shader family.
// These helpers deliberately keep the original texture packing contracts while
// targeting Unity 2022's built-in forward renderer.

// The recovered character-shadow caster path binds the original producer's
// GL.GetGPUProjectionMatrix(logicalProjection, true) * worldToLight contract
// explicitly. Normal camera/scene passes leave its keyword disabled.
float4x4 _EndfieldCharacterShadowPassVP;

inline float4 EndfieldRecoveredCharacterShadowClipPosition(float4 objectPosition)
{
    return mul(
        _EndfieldCharacterShadowPassVP,
        mul(unity_ObjectToWorld, objectPosition));
}

inline half EndfieldLuma(half3 color)
{
    return dot(color, half3(0.2126729h, 0.7151522h, 0.0721750h));
}

inline half3 EndfieldSaturation(half3 color, half saturation)
{
    half luma = EndfieldLuma(color);
    return lerp(luma.xxx, color, saturation);
}

inline half3 EndfieldDecodePackedNormal(half4 packedNormal, half scale)
{
    // CharacterNPR's regular normal map stores X across R*A and Y in G.
    half2 xy = half2(packedNormal.r * packedNormal.a * 2.0h - 1.0h,
                     packedNormal.g * 2.0h - 1.0h);
    xy *= scale;
    return normalize(half3(xy, sqrt(saturate(1.0h - dot(xy, xy)))));
}

inline half3 EndfieldDecodeNormalRG(half2 packedNormal, half scale)
{
    half2 xy = (packedNormal * 2.0h - 1.0h) * scale;
    return normalize(half3(xy, sqrt(saturate(1.0h - dot(xy, xy)))));
}

inline half3 EndfieldTangentToWorld(
    half3 normalTS,
    half3 tangentWS,
    half3 binormalWS,
    half3 normalWS)
{
    return normalize(
        normalTS.x * tangentWS +
        normalTS.y * binormalWS +
        normalTS.z * normalWS);
}

inline float3 EndfieldLinearToSRGB(float3 linearColor)
{
    linearColor = max(linearColor, 0.0);
    float3 lower = linearColor * 12.92;
    float3 upper = 1.055 * pow(linearColor, 1.0 / 2.4) - 0.055;
    return lerp(lower, upper, step(0.0031308, linearColor));
}

inline half3 EndfieldSampleFlattenedLut32(sampler2D lut, half3 linearBaseColor)
{
    // Original HGRP variants address a 32x32x32 LUT flattened into a 1024x32
    // texture. Blue selects adjacent 32-pixel horizontal slices.
    // HGRP runs in linear space, but keep the helper correct if this shader is
    // inspected in a gamma project: gamma-space texture samples must not be
    // encoded a second time before becoming LUT coordinates.
    #if defined(UNITY_COLORSPACE_GAMMA)
        float3 srgb = saturate(linearBaseColor);
    #else
        float3 srgb = saturate(EndfieldLinearToSRGB(linearBaseColor));
    #endif
    float blueSlice = srgb.b * 31.0;
    float slice0 = floor(blueSlice);
    float slice1 = min(slice0 + 1.0, 31.0);
    float redTexel = srgb.r * 31.0 + 0.5;
    float greenTexel = srgb.g * 31.0 + 0.5;
    float2 uv0 = float2((slice0 * 32.0 + redTexel) / 1024.0, greenTexel / 32.0);
    float2 uv1 = float2((slice1 * 32.0 + redTexel) / 1024.0, greenTexel / 32.0);
    return lerp(tex2D(lut, uv0).rgb, tex2D(lut, uv1).rgb, frac(blueSlice));
}

inline half3 EndfieldShadowColor(
    sampler2D lut,
    half useLut,
    half3 baseColor,
    half brightness,
    half saturation)
{
    half3 fallback = EndfieldSaturation(baseColor, saturation) * brightness;
    half3 lutColor = EndfieldSampleFlattenedLut32(lut, baseColor);
    return lerp(fallback, lutColor, saturate(useLut));
}

inline half4 EndfieldRampSample(sampler2D ramp, half nDotL, half nDotV)
{
    // Recovered CharacterNPR samples the direct-light ramp on its fixed
    // middle scanline. View dependence is a separate second alpha sample in
    // the original shader; using NdotV as the V coordinate incorrectly walks
    // through unrelated packed ramp rows and contaminates the diffuse hue.
    return tex2D(ramp, half2(saturate(nDotL * 0.5h + 0.5h), 0.5h));
}

inline half EndfieldDefaultDiffuseBand(half nDotL, half softness)
{
    half width = max(softness, 0.001h);
    return smoothstep(-width, width, nDotL);
}

inline half3 EndfieldAmbient(half3 normalWS)
{
    return max(ShadeSH9(half4(normalize(normalWS), 1.0h)), 0.0h);
}

inline half EndfieldFresnel(half3 normalWS, half3 viewWS, half power)
{
    return pow(saturate(1.0h - dot(normalize(normalWS), normalize(viewWS))),
               max(power, 0.001h));
}

inline half EndfieldKajiyaKay(
    half3 tangentWS,
    half3 halfVectorWS,
    half shift,
    half exponent)
{
    half3 shiftedTangent = normalize(tangentWS + shift * halfVectorWS);
    half tangentDotHalf = dot(shiftedTangent, halfVectorWS);
    half sinTheta = sqrt(saturate(1.0h - tangentDotHalf * tangentDotHalf));
    return pow(sinTheta, max(exponent, 1.0h));
}

inline half2 EndfieldParallaxOffset(half3 viewTS, half height, half scale)
{
    return (viewTS.xy / max(abs(viewTS.z), 0.15h)) * ((height - 0.5h) * scale);
}

inline half EndfieldCutout(half enabled, half alpha, half threshold)
{
    return lerp(1.0h, alpha - threshold, saturate(enabled));
}

// Default-off PreGBuffer sidecar contract. The original modified engine stores
// the CPU character selector bit pattern in unity_WorldTransformParams.z and
// the fragment reinterprets it with asuint. Stock Unity does not expose that
// carrier, so the diagnostic publishes the already-computed uint while keeping
// the exact A2B10G10R10 lane representation consumed by packUnorm4x10.
int _EndfieldRecoveredPreGBufferSelectorBits;
#if defined(ENDFIELD_RECOVERED_SAME_OWNER_AUDIT)
int _EndfieldRecoveredLogicalDrawId;
// Forward uses declared per-renderer Integer properties so indexed
// MaterialPropertyBlocks cannot fall through to PreG's last global ID.
int _EndfieldRecoveredForwardLogicalDrawId;
int _EndfieldRecoveredForwardRenderQueue;
#define ENDFIELD_RECOVERED_FACE_AND_PRIMITIVE_INPUT(name) \
    uint endfieldRecoveredPrimitiveId : SV_PrimitiveID, \
    bool name : SV_IsFrontFace
#define ENDFIELD_RECOVERED_SAME_OWNER_PRIMITIVE_PARAMETER \
    , uint primitiveId
#define ENDFIELD_RECOVERED_SAME_OWNER_PRIMITIVE_ARGUMENT \
    , endfieldRecoveredPrimitiveId
#define ENDFIELD_RECOVERED_SAME_OWNER_PRIMITIVE_VALUE \
    endfieldRecoveredPrimitiveId
#define ENDFIELD_RECOVERED_SAME_OWNER_TANGENT_PARAMETER \
    , float2 normalTSXY
#define ENDFIELD_RECOVERED_SAME_OWNER_TANGENT_DECLARE(name) \
    float2 name = 0.0
#define ENDFIELD_RECOVERED_SAME_OWNER_TANGENT_CAPTURE(name, value) \
    name = (value).xy
#define ENDFIELD_RECOVERED_MAKE_PREGBUFFER_OUTPUT(normalWS, familyTag, materialPayload, normalTSXY) \
    EndfieldRecoveredMakePreGBufferOutput( \
        normalWS, familyTag, materialPayload, normalTSXY, endfieldRecoveredPrimitiveId)
#define ENDFIELD_RECOVERED_FACE_IS_FRONT(name) (name)
#define ENDFIELD_RECOVERED_FACE_VALUE(name) ((name) ? 1.0 : -1.0)
#else
#define ENDFIELD_RECOVERED_FACE_AND_PRIMITIVE_INPUT(name) \
    fixed name : VFACE
#define ENDFIELD_RECOVERED_SAME_OWNER_PRIMITIVE_PARAMETER
#define ENDFIELD_RECOVERED_SAME_OWNER_PRIMITIVE_ARGUMENT
#define ENDFIELD_RECOVERED_SAME_OWNER_PRIMITIVE_VALUE 0u
#define ENDFIELD_RECOVERED_SAME_OWNER_TANGENT_PARAMETER
#define ENDFIELD_RECOVERED_SAME_OWNER_TANGENT_DECLARE(name)
#define ENDFIELD_RECOVERED_SAME_OWNER_TANGENT_CAPTURE(name, value)
#define ENDFIELD_RECOVERED_MAKE_PREGBUFFER_OUTPUT(normalWS, familyTag, materialPayload, normalTSXY) \
    EndfieldRecoveredMakePreGBufferOutput(normalWS, familyTag, materialPayload)
#define ENDFIELD_RECOVERED_FACE_IS_FRONT(name) ((name) >= 0.0)
#define ENDFIELD_RECOVERED_FACE_VALUE(name) (name)
#endif

struct EndfieldRecoveredPreGBufferOutput
{
    float4 selector : SV_Target0;
    float4 normalAndFamily : SV_Target1;
#if defined(ENDFIELD_RECOVERED_SAME_OWNER_AUDIT)
    float4 materialPayload : SV_Target2;
    float4 owner : SV_Target3;
#else
    float4 materialPayload : SV_Target2;
#endif
};

inline float4 EndfieldRecoveredEncodeSelectorBits(uint selectorBits)
{
    return float4(
        (selectorBits & 1023u) * (1.0 / 1023.0),
        ((selectorBits >> 10u) & 1023u) * (1.0 / 1023.0),
        ((selectorBits >> 20u) & 1023u) * (1.0 / 1023.0),
        ((selectorBits >> 30u) & 3u) * (1.0 / 3.0));
}

inline float2 EndfieldRecoveredEncodeYUpOctNormal(float3 normalWS)
{
    normalWS = normalize(normalWS);
    normalWS /= max(
        abs(normalWS.x) + abs(normalWS.y) + abs(normalWS.z),
        1.0e-8);
    float2 oct = normalWS.xz;
    if (normalWS.y < 0.0)
    {
        float2 signs = float2(
            oct.x >= 0.0 ? 1.0 : -1.0,
            oct.y >= 0.0 ? 1.0 : -1.0);
        oct = (1.0 - abs(oct.yx)) * signs;
    }
    return saturate(oct * 0.5 + 0.5);
}

inline EndfieldRecoveredPreGBufferOutput EndfieldRecoveredMakePreGBufferOutput(
    float3 normalWS,
    float familyTag,
    float4 materialPayload
    ENDFIELD_RECOVERED_SAME_OWNER_TANGENT_PARAMETER
    ENDFIELD_RECOVERED_SAME_OWNER_PRIMITIVE_PARAMETER)
{
    EndfieldRecoveredPreGBufferOutput output;
    output.selector = EndfieldRecoveredEncodeSelectorBits(
        (uint)_EndfieldRecoveredPreGBufferSelectorBits);
    output.normalAndFamily = float4(
        EndfieldRecoveredEncodeYUpOctNormal(normalWS),
        0.0,
        familyTag);
    output.materialPayload = float4(materialPayload.rgb, 1.0);
#if defined(ENDFIELD_RECOVERED_SAME_OWNER_AUDIT)
    // IEEE-754 binary32 represents every non-negative integer below 2^24
    // exactly. Logical IDs are range-checked on the CPU before drawing;
    // primitive overflow is carried as -1 and makes validation fail closed.
    bool primitiveIdExact = primitiveId < 16777216u;
    // Retry 10 retains the exact numeric owner pair in XY and adds the
    // fragment's decoded tangent-space normal in ZW before any TBN/world or
    // octahedral operation. The owner target is float-only RGBA32F.
    output.owner = float4(
        (float)_EndfieldRecoveredLogicalDrawId,
        primitiveIdExact ? (float)primitiveId : -1.0,
        normalTSXY);
#endif
    return output;
}

// CharacterNPR ForwardOpaque writes the current-frame packed motion target for
// every opaque skin/cloth/hair/eye family. The selected desktop variants share
// this fourth-root encoding; skin/cloth may select the 0.7 snow discriminator,
// while the active Endminf materials and all hair/eye variants use 0.4.
inline float EndfieldRecoveredCharacterMotionChannel(float value)
{
    return 0.5 + 0.5 * sign(value) * sqrt(sqrt(abs(value)));
}

inline float4 EndfieldRecoveredCharacterMotionMrt(
    float3 currentClipXYW,
    float3 previousClipXYW,
    float snowSurfaceClass)
{
    float2 currentNdc = currentClipXYW.xy /
        max(currentClipXYW.z, 1.0e-8);
    float2 previousNdc = previousClipXYW.xy /
        max(previousClipXYW.z, 1.0e-8);
    float2 halfMotion = 0.5 * float2(
        currentNdc.x - previousNdc.x,
        previousNdc.y - currentNdc.y);
    return float4(
        EndfieldRecoveredCharacterMotionChannel(halfMotion.x),
        EndfieldRecoveredCharacterMotionChannel(halfMotion.y),
        1.0,
        snowSurfaceClass > 0.1 ? 0.7 : 0.4);
}

#endif
