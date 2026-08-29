#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <bcrypt.h>
#include <d3d11.h>

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iterator>
#include <vector>

#include "EmbeddedDxbc.generated.h"
#include "EndminfUberCapturePayload.generated.h"

namespace
{
constexpr UINT kFixtureWidth = 32;
constexpr UINT kFixtureHeight = 16;
constexpr std::uint64_t kExpectedNormalHash = 0xc9a020a5e66757f2ull;
constexpr std::uint64_t kExpectedPeakHash = 0x07186ed30b54b6abull;
constexpr std::uint8_t kExpectedLutSha256[32] = {
    0x71, 0x7c, 0x1d, 0x48, 0x36, 0x62, 0xc0, 0x0a,
    0xbe, 0x55, 0xe1, 0xc5, 0x6a, 0x9d, 0x02, 0x4f,
    0x45, 0xe5, 0xc8, 0x4c, 0x43, 0x0e, 0xd9, 0xdd,
    0x28, 0x54, 0xcb, 0x38, 0x6f, 0x37, 0x24, 0x82,
};

template <typename T>
void Release(T*& value)
{
    if (value != nullptr)
        value->Release();
    value = nullptr;
}

std::uint16_t FloatToHalf(float value)
{
    std::uint32_t bits = 0;
    std::memcpy(&bits, &value, sizeof(bits));
    const std::uint32_t sign = (bits >> 16u) & 0x8000u;
    std::int32_t exponent = static_cast<std::int32_t>(
        (bits >> 23u) & 0xffu) - 127 + 15;
    std::uint32_t mantissa = bits & 0x7fffffu;
    if (exponent <= 0)
    {
        if (exponent < -10)
            return static_cast<std::uint16_t>(sign);
        mantissa = (mantissa | 0x800000u) >> (1u - exponent);
        return static_cast<std::uint16_t>(
            sign | ((mantissa + 0x1000u) >> 13u));
    }
    if (exponent >= 31)
        return static_cast<std::uint16_t>(sign | 0x7c00u);
    return static_cast<std::uint16_t>(
        sign | (static_cast<std::uint32_t>(exponent) << 10u) |
        ((mantissa + 0x1000u) >> 13u));
}

void StoreHalf4(std::uint16_t* destination,
                float red, float green, float blue, float alpha)
{
    destination[0] = FloatToHalf(red);
    destination[1] = FloatToHalf(green);
    destination[2] = FloatToHalf(blue);
    destination[3] = FloatToHalf(alpha);
}

HRESULT CreateHalfTexture(
    ID3D11Device* device,
    UINT width,
    UINT height,
    const std::vector<std::uint16_t>& pixels,
    ID3D11Texture2D** texture,
    ID3D11ShaderResourceView** view)
{
    D3D11_TEXTURE2D_DESC description = {};
    description.Width = width;
    description.Height = height;
    description.MipLevels = 1;
    description.ArraySize = 1;
    description.Format = DXGI_FORMAT_R16G16B16A16_FLOAT;
    description.SampleDesc.Count = 1;
    description.Usage = D3D11_USAGE_IMMUTABLE;
    description.BindFlags = D3D11_BIND_SHADER_RESOURCE;
    D3D11_SUBRESOURCE_DATA initial = {};
    initial.pSysMem = pixels.data();
    initial.SysMemPitch = width * 8u;
    initial.SysMemSlicePitch = width * height * 8u;
    HRESULT result = device->CreateTexture2D(
        &description, &initial, texture);
    if (SUCCEEDED(result))
        result = device->CreateShaderResourceView(*texture, nullptr, view);
    return result;
}

HRESULT CreateConstantBuffer(
    ID3D11Device* device,
    const void* bytes,
    UINT byteCount,
    ID3D11Buffer** output)
{
    D3D11_BUFFER_DESC description = {};
    description.ByteWidth = byteCount;
    description.Usage = D3D11_USAGE_IMMUTABLE;
    description.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
    D3D11_SUBRESOURCE_DATA initial = {};
    initial.pSysMem = bytes;
    return device->CreateBuffer(&description, &initial, output);
}

void PatchFloat(std::vector<std::uint8_t>& bytes,
                std::size_t floatIndex, float value)
{
    const std::size_t offset = floatIndex * sizeof(float);
    if (offset + sizeof(float) <= bytes.size())
        std::memcpy(bytes.data() + offset, &value, sizeof(value));
}

std::uint64_t Fnv1a(const std::vector<std::uint8_t>& bytes)
{
    std::uint64_t value = 1469598103934665603ull;
    for (std::uint8_t byte : bytes)
    {
        value ^= byte;
        value *= 1099511628211ull;
    }
    return value;
}

bool HasExactLutDigest(const std::vector<std::uint8_t>& bytes)
{
    BCRYPT_ALG_HANDLE algorithm = nullptr;
    BCRYPT_HASH_HANDLE hash = nullptr;
    DWORD objectBytes = 0;
    DWORD hashBytes = 0;
    DWORD returned = 0;
    bool valid = BCryptOpenAlgorithmProvider(
        &algorithm, BCRYPT_SHA256_ALGORITHM, nullptr, 0) == 0;
    if (valid)
        valid = BCryptGetProperty(
            algorithm, BCRYPT_OBJECT_LENGTH,
            reinterpret_cast<PUCHAR>(&objectBytes), sizeof(objectBytes),
            &returned, 0) == 0;
    if (valid)
        valid = BCryptGetProperty(
            algorithm, BCRYPT_HASH_LENGTH,
            reinterpret_cast<PUCHAR>(&hashBytes), sizeof(hashBytes),
            &returned, 0) == 0 && hashBytes == 32u;
    std::vector<std::uint8_t> object(objectBytes);
    std::uint8_t digest[32] = {};
    if (valid)
        valid = BCryptCreateHash(
            algorithm, &hash, object.data(), objectBytes,
            nullptr, 0, 0) == 0;
    if (valid)
        valid = BCryptHashData(
            hash, const_cast<PUCHAR>(bytes.data()),
            static_cast<ULONG>(bytes.size()), 0) == 0;
    if (valid)
        valid = BCryptFinishHash(hash, digest, sizeof(digest), 0) == 0;
    if (hash != nullptr)
        BCryptDestroyHash(hash);
    if (algorithm != nullptr)
        BCryptCloseAlgorithmProvider(algorithm, 0);
    return valid && std::memcmp(
        digest, kExpectedLutSha256, sizeof(digest)) == 0;
}

HRESULT Render(
    ID3D11Device* device,
    ID3D11DeviceContext* context,
    ID3D11VertexShader* vertexShader,
    ID3D11PixelShader* pixelShader,
    ID3D11ShaderResourceView* const resources[3],
    ID3D11SamplerState* sampler,
    ID3D11RasterizerState* rasterizer,
    ID3D11DepthStencilState* depthState,
    ID3D11BlendState* blendState,
    ID3D11RenderTargetView* target,
    ID3D11DepthStencilView* depthTarget,
    ID3D11Texture2D* output,
    UINT width,
    UINT height,
    bool patchFixtureConstants,
    const std::vector<std::uint8_t>* replayPsB0,
    const std::vector<std::uint8_t>* replayPsB1,
    bool peak,
    std::vector<std::uint8_t>& pixels)
{
    std::vector<std::uint8_t> psB0(
        g_EndfieldUberPsB0,
        g_EndfieldUberPsB0 + g_EndfieldUberPsB0Size);
    std::vector<std::uint8_t> psB1(
        g_EndfieldUberPsB1,
        g_EndfieldUberPsB1 + g_EndfieldUberPsB1Size);
    if (replayPsB0 != nullptr)
        psB0 = *replayPsB0;
    if (replayPsB1 != nullptr)
        psB1 = *replayPsB1;
    if (patchFixtureConstants)
    {
        PatchFloat(psB0, 0, static_cast<float>(width));
        PatchFloat(psB0, 1, static_cast<float>(height));
        PatchFloat(psB0, 2, 1.0f / static_cast<float>(width));
        PatchFloat(psB0, 3, 1.0f / static_cast<float>(height));
        PatchFloat(psB0, 27u * 4u, 1.0f);
        PatchFloat(psB0, 27u * 4u + 2u,
                   static_cast<float>(width) / static_cast<float>(height));
        PatchFloat(psB1, 0, 0.5f);
        PatchFloat(psB1, 1, 0.5f);
        PatchFloat(psB1, 2, peak ? 0.18f : 0.0f);
        PatchFloat(psB1, 3, 1.0f);
    }

    ID3D11Buffer* vsConstant = nullptr;
    ID3D11Buffer* psConstants[2] = {};
    HRESULT result = CreateConstantBuffer(
        device, g_EndfieldUberVsB0,
        static_cast<UINT>(g_EndfieldUberVsB0Size), &vsConstant);
    if (SUCCEEDED(result))
        result = CreateConstantBuffer(
            device, psB0.data(), static_cast<UINT>(psB0.size()),
            &psConstants[0]);
    if (SUCCEEDED(result))
        result = CreateConstantBuffer(
            device, psB1.data(), static_cast<UINT>(psB1.size()),
            &psConstants[1]);
    if (FAILED(result))
    {
        Release(psConstants[1]);
        Release(psConstants[0]);
        Release(vsConstant);
        return result;
    }

    const FLOAT clear[4] = {};
    const D3D11_VIEWPORT viewport = {
        0.0f, 0.0f, static_cast<FLOAT>(width),
        static_cast<FLOAT>(height), 0.0f, 1.0f};
    const D3D11_RECT scissor = {
        0, 0, static_cast<LONG>(width), static_cast<LONG>(height)};
    const FLOAT blendFactor[4] = {};
    context->ClearRenderTargetView(target, clear);
    context->ClearDepthStencilView(
        depthTarget, D3D11_CLEAR_DEPTH | D3D11_CLEAR_STENCIL, 0.0f, 0u);
    context->OMSetRenderTargets(1, &target, depthTarget);
    context->OMSetBlendState(blendState, blendFactor, 0xffffffffu);
    context->OMSetDepthStencilState(depthState, 0u);
    context->RSSetState(rasterizer);
    context->RSSetViewports(1, &viewport);
    context->RSSetScissorRects(1, &scissor);
    context->IASetInputLayout(nullptr);
    context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    context->VSSetShader(vertexShader, nullptr, 0);
    context->PSSetShader(pixelShader, nullptr, 0);
    context->VSSetConstantBuffers(0, 1, &vsConstant);
    context->PSSetConstantBuffers(0, 2, psConstants);
    context->PSSetShaderResources(0, 3, resources);
    context->PSSetSamplers(0, 1, &sampler);
    context->Draw(3, 0);

    D3D11_TEXTURE2D_DESC stagingDescription = {};
    output->GetDesc(&stagingDescription);
    stagingDescription.Usage = D3D11_USAGE_STAGING;
    stagingDescription.BindFlags = 0;
    stagingDescription.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
    ID3D11Texture2D* staging = nullptr;
    result = device->CreateTexture2D(
        &stagingDescription, nullptr, &staging);
    if (SUCCEEDED(result))
    {
        ID3D11ShaderResourceView* nullResources[3] = {};
        context->PSSetShaderResources(0, 3, nullResources);
        context->CopyResource(staging, output);
        D3D11_MAPPED_SUBRESOURCE mapped = {};
        result = context->Map(staging, 0, D3D11_MAP_READ, 0, &mapped);
        if (SUCCEEDED(result))
        {
            pixels.resize(static_cast<std::size_t>(width) * height * 4u);
            for (UINT row = 0; row < height; ++row)
            {
                std::memcpy(
                    pixels.data() +
                        static_cast<std::size_t>(row) * width * 4u,
                    static_cast<const std::uint8_t*>(mapped.pData) +
                        row * mapped.RowPitch,
                    width * 4u);
            }
            context->Unmap(staging, 0);
        }
    }
    Release(staging);
    Release(psConstants[1]);
    Release(psConstants[0]);
    Release(vsConstant);
    return result;
}
}

int main(int argc, char** argv)
{
    const bool replay = argc == 9;
    if (argc != 2 && !replay)
    {
        std::fprintf(
            stderr,
            "usage: ValidateEndminfUberShaders LUT_BYTES "
            "[SOURCE_RGBA16F WIDTH HEIGHT OUTPUT_RGBA8 normal|peak "
            "PS_B0 PS_B1]\n");
        return 2;
    }
    std::ifstream lutStream(argv[1], std::ios::binary);
    const std::vector<std::uint8_t> lutBytes(
        (std::istreambuf_iterator<char>(lutStream)),
        std::istreambuf_iterator<char>());
    if (lutBytes.size() != 1024u * 32u * 8u ||
        !HasExactLutDigest(lutBytes))
    {
        std::fprintf(stderr, "exact_lut_validation=failed bytes=%zu\n",
                     lutBytes.size());
        return 3;
    }

    UINT width = kFixtureWidth;
    UINT height = kFixtureHeight;
    bool replayPeak = false;
    std::vector<std::uint8_t> sourceBytes;
    std::vector<std::uint8_t> replayPsB0;
    std::vector<std::uint8_t> replayPsB1;
    if (replay)
    {
        const unsigned long parsedWidth = std::strtoul(argv[3], nullptr, 10);
        const unsigned long parsedHeight = std::strtoul(argv[4], nullptr, 10);
        if (parsedWidth == 0 || parsedHeight == 0 ||
            parsedWidth > 16384 || parsedHeight > 16384 ||
            (std::strcmp(argv[6], "normal") != 0 &&
             std::strcmp(argv[6], "peak") != 0))
        {
            std::fprintf(stderr, "replay_arguments=invalid\n");
            return 3;
        }
        width = static_cast<UINT>(parsedWidth);
        height = static_cast<UINT>(parsedHeight);
        replayPeak = std::strcmp(argv[6], "peak") == 0;
        std::ifstream sourceStream(argv[2], std::ios::binary);
        sourceBytes.assign(
            (std::istreambuf_iterator<char>(sourceStream)),
            std::istreambuf_iterator<char>());
        const std::size_t expectedSourceBytes =
            static_cast<std::size_t>(width) * height * 8u;
        if (sourceBytes.size() != expectedSourceBytes)
        {
            std::fprintf(
                stderr, "source_validation=failed bytes=%zu expected=%zu\n",
                sourceBytes.size(), expectedSourceBytes);
            return 3;
        }
        std::ifstream b0Stream(argv[7], std::ios::binary);
        replayPsB0.assign(
            (std::istreambuf_iterator<char>(b0Stream)),
            std::istreambuf_iterator<char>());
        std::ifstream b1Stream(argv[8], std::ios::binary);
        replayPsB1.assign(
            (std::istreambuf_iterator<char>(b1Stream)),
            std::istreambuf_iterator<char>());
        if (replayPsB0.size() != g_EndfieldUberPsB0Size ||
            replayPsB1.size() != g_EndfieldUberPsB1Size)
        {
            std::fprintf(
                stderr,
                "replay_constant_validation=failed b0=%zu/%zu "
                "b1=%zu/%zu\n",
                replayPsB0.size(), g_EndfieldUberPsB0Size,
                replayPsB1.size(), g_EndfieldUberPsB1Size);
            return 3;
        }
    }

    ID3D11Device* device = nullptr;
    ID3D11DeviceContext* context = nullptr;
    D3D_FEATURE_LEVEL level = D3D_FEATURE_LEVEL_11_0;
    HRESULT result = D3D11CreateDevice(
        nullptr, D3D_DRIVER_TYPE_WARP, nullptr, 0, &level, 1,
        D3D11_SDK_VERSION, &device, nullptr, &context);
    if (FAILED(result))
        return 2;

    ID3D11VertexShader* vertex = nullptr;
    ID3D11PixelShader* normal = nullptr;
    ID3D11PixelShader* peak = nullptr;
    result = device->CreateVertexShader(
        g_EndfieldUberVertexDxbc, g_EndfieldUberVertexDxbcSize,
        nullptr, &vertex);
    if (SUCCEEDED(result))
        result = device->CreatePixelShader(
            g_EndfieldUberNormalPixelDxbc,
            g_EndfieldUberNormalPixelDxbcSize, nullptr, &normal);
    if (SUCCEEDED(result))
        result = device->CreatePixelShader(
            g_EndfieldUberPixelDxbc, g_EndfieldUberPixelDxbcSize,
            nullptr, &peak);

    std::vector<std::uint16_t> source(
        static_cast<std::size_t>(width) * height * 4u);
    if (replay)
        std::memcpy(source.data(), sourceBytes.data(), sourceBytes.size());
    for (UINT y = 0; !replay && y < height; ++y)
    {
        for (UINT x = 0; x < width; ++x)
        {
            const float fx = static_cast<float>(x) / (width - 1u);
            const float fy = static_cast<float>(y) / (height - 1u);
            StoreHalf4(&source[(y * width + x) * 4u],
                       0.05f + 1.5f * fx,
                       0.04f + 0.7f * fy,
                       0.03f + 0.4f * (1.0f - fx), 1.0f);
        }
    }
    std::vector<std::uint16_t> lut(lutBytes.size() / sizeof(std::uint16_t));
    std::memcpy(lut.data(), lutBytes.data(), lutBytes.size());
    ID3D11Texture2D* textures[3] = {};
    ID3D11ShaderResourceView* resources[3] = {};
    if (SUCCEEDED(result))
        result = CreateHalfTexture(
            device, width, height, source, &textures[0], &resources[0]);

    D3D11_TEXTURE2D_DESC bloomDescription = {};
    bloomDescription.Width = (width + 1u) / 2u;
    bloomDescription.Height = (height + 1u) / 2u;
    bloomDescription.MipLevels = 1;
    bloomDescription.ArraySize = 1;
    bloomDescription.Format = DXGI_FORMAT_R11G11B10_FLOAT;
    bloomDescription.SampleDesc.Count = 1;
    bloomDescription.BindFlags =
        D3D11_BIND_SHADER_RESOURCE | D3D11_BIND_RENDER_TARGET;
    ID3D11RenderTargetView* bloomTarget = nullptr;
    if (SUCCEEDED(result))
        result = device->CreateTexture2D(
            &bloomDescription, nullptr, &textures[1]);
    if (SUCCEEDED(result))
        result = device->CreateShaderResourceView(
            textures[1], nullptr, &resources[1]);
    if (SUCCEEDED(result))
        result = device->CreateRenderTargetView(
            textures[1], nullptr, &bloomTarget);
    if (SUCCEEDED(result))
    {
        const FLOAT fixtureBloom[4] = {0.08f, 0.04f, 0.02f, 1.0f};
        const FLOAT zeroBloom[4] = {};
        const FLOAT* bloomClear = replay ? zeroBloom : fixtureBloom;
        context->ClearRenderTargetView(bloomTarget, bloomClear);
        result = CreateHalfTexture(
            device, 1024u, 32u, lut, &textures[2], &resources[2]);
    }

    D3D11_TEXTURE2D_DESC outputDescription = {};
    outputDescription.Width = width;
    outputDescription.Height = height;
    outputDescription.MipLevels = 1;
    outputDescription.ArraySize = 1;
    outputDescription.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
    outputDescription.SampleDesc.Count = 1;
    outputDescription.BindFlags = D3D11_BIND_RENDER_TARGET;
    ID3D11Texture2D* output = nullptr;
    ID3D11RenderTargetView* target = nullptr;
    if (SUCCEEDED(result))
        result = device->CreateTexture2D(
            &outputDescription, nullptr, &output);
    if (SUCCEEDED(result))
        result = device->CreateRenderTargetView(output, nullptr, &target);

    D3D11_TEXTURE2D_DESC depthTextureDescription = {};
    depthTextureDescription.Width = width;
    depthTextureDescription.Height = height;
    depthTextureDescription.MipLevels = 1;
    depthTextureDescription.ArraySize = 1;
    depthTextureDescription.Format = DXGI_FORMAT_R24G8_TYPELESS;
    depthTextureDescription.SampleDesc.Count = 1;
    depthTextureDescription.BindFlags = D3D11_BIND_DEPTH_STENCIL;
    ID3D11Texture2D* depthTexture = nullptr;
    ID3D11DepthStencilView* depthTarget = nullptr;
    if (SUCCEEDED(result))
        result = device->CreateTexture2D(
            &depthTextureDescription, nullptr, &depthTexture);
    D3D11_DEPTH_STENCIL_VIEW_DESC depthViewDescription = {};
    depthViewDescription.Format = DXGI_FORMAT_D24_UNORM_S8_UINT;
    depthViewDescription.ViewDimension = D3D11_DSV_DIMENSION_TEXTURE2D;
    if (SUCCEEDED(result))
        result = device->CreateDepthStencilView(
            depthTexture, &depthViewDescription, &depthTarget);

    D3D11_SAMPLER_DESC samplerDescription = {};
    samplerDescription.Filter = D3D11_FILTER_MIN_MAG_MIP_LINEAR;
    samplerDescription.AddressU = D3D11_TEXTURE_ADDRESS_CLAMP;
    samplerDescription.AddressV = D3D11_TEXTURE_ADDRESS_CLAMP;
    samplerDescription.AddressW = D3D11_TEXTURE_ADDRESS_CLAMP;
    samplerDescription.MaxLOD = D3D11_FLOAT32_MAX;
    ID3D11SamplerState* sampler = nullptr;
    if (SUCCEEDED(result))
        result = device->CreateSamplerState(&samplerDescription, &sampler);

    D3D11_RASTERIZER_DESC rasterizerDescription = {};
    rasterizerDescription.FillMode = D3D11_FILL_SOLID;
    rasterizerDescription.CullMode = D3D11_CULL_NONE;
    rasterizerDescription.DepthClipEnable = TRUE;
    rasterizerDescription.ScissorEnable = TRUE;
    ID3D11RasterizerState* rasterizer = nullptr;
    if (SUCCEEDED(result))
        result = device->CreateRasterizerState(
            &rasterizerDescription, &rasterizer);
    D3D11_DEPTH_STENCIL_DESC depthDescription = {};
    depthDescription.DepthEnable = FALSE;
    depthDescription.DepthWriteMask = D3D11_DEPTH_WRITE_MASK_ZERO;
    depthDescription.DepthFunc = D3D11_COMPARISON_ALWAYS;
    ID3D11DepthStencilState* depthState = nullptr;
    if (SUCCEEDED(result))
        result = device->CreateDepthStencilState(
            &depthDescription, &depthState);
    D3D11_BLEND_DESC blendDescription = {};
    blendDescription.RenderTarget[0].BlendEnable = FALSE;
    blendDescription.RenderTarget[0].RenderTargetWriteMask =
        D3D11_COLOR_WRITE_ENABLE_ALL;
    ID3D11BlendState* blendState = nullptr;
    if (SUCCEEDED(result))
        result = device->CreateBlendState(
            &blendDescription, &blendState);

    std::vector<std::uint8_t> normalPixels;
    std::vector<std::uint8_t> peakPixels;
    if (SUCCEEDED(result) && (!replay || !replayPeak))
        result = Render(
            device, context, vertex, normal, resources, sampler,
            rasterizer, depthState, blendState,
            target, depthTarget, output, width, height, !replay,
            replayPsB0.empty() ? nullptr : &replayPsB0,
            replayPsB1.empty() ? nullptr : &replayPsB1,
            false, normalPixels);
    if (SUCCEEDED(result) && (!replay || replayPeak))
        result = Render(
            device, context, vertex, peak, resources, sampler,
            rasterizer, depthState, blendState,
            target, depthTarget, output, width, height, !replay,
            replayPsB0.empty() ? nullptr : &replayPsB0,
            replayPsB1.empty() ? nullptr : &replayPsB1,
            true, peakPixels);

    if (SUCCEEDED(result) && replay)
    {
        const std::vector<std::uint8_t>& replayPixels =
            replayPeak ? peakPixels : normalPixels;
        std::ofstream replayOutput(
            argv[5], std::ios::binary | std::ios::trunc);
        replayOutput.write(
            reinterpret_cast<const char*>(replayPixels.data()),
            static_cast<std::streamsize>(replayPixels.size()));
        if (!replayOutput)
            result = E_FAIL;
        else
            std::printf(
                "replay=1 variant=%s width=%u height=%u bloom=zero "
                "frame_constants=%s "
                "output_bytes=%zu output_fnv1a=0x%016llx exact_lut=1\n",
                replayPeak ? "peak" : "normal", width, height,
                "external",
                replayPixels.size(),
                static_cast<unsigned long long>(Fnv1a(replayPixels)));
    }

    const std::uint64_t normalHash = Fnv1a(normalPixels);
    const std::uint64_t peakHash = Fnv1a(peakPixels);
    const bool normalNonzero = std::any_of(
        normalPixels.begin(), normalPixels.end(),
        [](std::uint8_t value) { return value != 0; });
    const bool peakNonzero = std::any_of(
        peakPixels.begin(), peakPixels.end(),
        [](std::uint8_t value) { return value != 0; });
    const bool hashesMatch = !replay &&
        normalHash == kExpectedNormalHash &&
        peakHash == kExpectedPeakHash;
    if (!replay)
        std::printf(
        "feature_level=0x%x normal=0x%016llx peak=0x%016llx "
        "normal_nonzero=%u peak_nonzero=%u distinct=%u hashes_match=%u "
        "exact_lut=1\n",
        static_cast<unsigned int>(level),
        static_cast<unsigned long long>(normalHash),
        static_cast<unsigned long long>(peakHash),
        normalNonzero ? 1u : 0u, peakNonzero ? 1u : 0u,
        normalHash != peakHash ? 1u : 0u, hashesMatch ? 1u : 0u);

    Release(blendState);
    Release(depthState);
    Release(rasterizer);
    Release(sampler);
    Release(target);
    Release(output);
    Release(depthTarget);
    Release(depthTexture);
    Release(resources[2]);
    Release(resources[1]);
    Release(resources[0]);
    Release(bloomTarget);
    Release(textures[2]);
    Release(textures[1]);
    Release(textures[0]);
    Release(peak);
    Release(normal);
    Release(vertex);
    Release(context);
    Release(device);
    if (replay)
        return SUCCEEDED(result) ? 0 : 3;
    return SUCCEEDED(result) && normalNonzero && peakNonzero &&
            normalHash != peakHash && hashesMatch
        ? 0
        : 3;
}
