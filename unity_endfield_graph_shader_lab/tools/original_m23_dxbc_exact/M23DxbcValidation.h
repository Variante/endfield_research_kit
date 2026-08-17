#pragma once

#include <cstdint>

// Shared ABI between the offline WARP fixture and the opt-in Unity render
// event. Keep field order stable: reports are also consumed by Python/C#.
struct EndfieldM23DxbcValidation {
    std::uint32_t mode;
    std::uint32_t shaderMask;
    std::uint32_t inputLayoutMask;
    std::uint32_t vertexBufferMask;
    std::uint32_t vertexConstantBufferMask;
    std::uint32_t pixelConstantBufferMask;
    std::uint32_t shaderResourceMask;
    std::uint32_t samplerMask;
    std::uint32_t stateMask;
    std::uint32_t vsBindingMask;
    std::uint32_t psBindingMask;
    std::uint32_t inputBindingMask;
    std::uint32_t vertexBindingMask;
    std::uint32_t vsConstantBufferBindingMask;
    std::uint32_t psConstantBufferBindingMask;
    std::uint32_t shaderResourceBindingMask;
    std::uint32_t vertexShaderResourceCreationMask;
    std::uint32_t vertexShaderResourceBindingMask;
    std::uint32_t samplerBindingMask;
    std::uint32_t stateBindingMask;
    std::uint32_t renderTargetBindingMask;
    std::uint32_t topologyBindingMask;
    std::uint32_t viewportBindingMask;
    std::uint32_t drawIssued;
    std::uint32_t readbackFinite;
    std::uint32_t readbackChanged;
    std::uint32_t visualFidelityClaim;
    std::uint32_t diagnosticVsSignatureMask;
    std::uint32_t diagnosticVsSourceHashMask;
    std::uint32_t diagnosticVsCompiledHashMask;
    char diagnosticVsSourceSha256[65];
    char diagnosticVsCompiledSha256[65];
    std::uint32_t namedLowMaterialHashMask;
    std::uint32_t namedLowContractHashMask;
    std::uint32_t namedLowComponentMapMask;
    char namedLowMaterialSha256[65];
    char namedLowContractSha256[65];
    char namedLowComponentMap[1024];
    std::uint32_t readbackChangedFromZero;
    std::uint32_t highProbeExecutionMask;
    std::uint32_t highProbeRegister;
    std::uint32_t highProbeComponent;
    std::uint32_t highBaselineValueMask;
    std::uint32_t highAblationGroupMask;
    std::uint32_t highNeutralDomainMask;
    std::uint32_t diagnosticB2GateMask;
    std::uint32_t highNeutralOverrideMask;
    std::uint32_t syntheticT0ReadbackMask;
    std::uint32_t syntheticT0HashMask;
    char syntheticT0Sha256[65];
    std::uint32_t exactTextureSourceHashMask;
    std::uint32_t exactTextureDecodeMask;
    std::uint32_t exactTextureWidth[5];
    std::uint32_t exactTextureHeight[5];
    std::uint32_t exactTextureVsSignatureMask;
    std::uint32_t exactTextureVsSourceHashMask;
    std::uint32_t exactTextureVsCompiledHashMask;
    char exactTextureVsSourceSha256[65];
    char exactTextureVsCompiledSha256[65];
    std::uint32_t exactTextureGridFinitePixels;
    std::uint32_t exactTextureGridNonzeroPixels;
    std::uint32_t exactTextureGridSize;
    float exactTextureGridMax[4];
    std::uint32_t exactTextureCausalOverrideMask;
    std::uint32_t exactTextureGridRgbNonzeroPixels;
    std::uint32_t exactTextureGridAlphaNonzeroPixels;
    float exactTextureGridRgbMax[3];
    float exactTextureGridRgbMin[3];
    float readback[4];
};

