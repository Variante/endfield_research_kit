#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <d3d11.h>

#include <cstdint>
#include <cstring>
#include <vector>

#include "EmbeddedM23Dxbc.generated.h"

// Batch 1 is deliberately a native D3D11 contract only.  There is no Unity
// callback, draw, or readback here: a host supplies its D3D11 device and gets
// a complete creation report back.
struct EndfieldM23DxbcValidation {
    std::uint32_t shaderMask;
    std::uint32_t inputLayoutMask;
    std::uint32_t vertexBufferMask;
    std::uint32_t vertexConstantBufferMask;
    std::uint32_t pixelConstantBufferMask;
    std::uint32_t shaderResourceMask;
    std::uint32_t samplerMask;
    std::uint32_t stateMask;
};

namespace {

constexpr std::uint32_t kResourceCount = 5;
constexpr std::uint32_t kAllResourcesMask = (1u << kResourceCount) - 1u;
constexpr std::uint32_t kStateRasterizer = 1u << 0;
constexpr std::uint32_t kStateBlend = 1u << 1;
constexpr std::uint32_t kStateDepth = 1u << 2;
constexpr std::uint32_t kAllStateMask = kStateRasterizer | kStateBlend | kStateDepth;
constexpr std::uint32_t kVsConstantBufferFloats4[kResourceCount] = {2, 82, 104, 14, 50};
constexpr std::uint32_t kPsConstantBufferFloats4[kResourceCount] = {45, 105, 5, 1, 44};

template <typename T>
class ComObject {
public:
    ComObject() = default;
    ~ComObject() { Reset(); }
    ComObject(const ComObject&) = delete;
    ComObject& operator=(const ComObject&) = delete;
    T** Put() { Reset(); return &value_; }
    T* Get() const { return value_; }
    T* operator->() const { return value_; }
    void Reset() {
        if (value_ != nullptr) {
            value_->Release();
            value_ = nullptr;
        }
    }
private:
    T* value_ = nullptr;
};

struct Vertex {
    float position[3];
    float normal[3];
    float tangent[4];
    float color[4];
    float texcoord0[4];
    float texcoord1[4];
    float texcoord4[4];
    float blendWeights[4];
    std::uint32_t blendIndices[4];
};
static_assert(sizeof(Vertex) == 136, "M23 input layout stride must remain 136 bytes");

HRESULT CreateConstantBuffer(ID3D11Device* device, std::uint32_t float4Count,
                             ComObject<ID3D11Buffer>* result) {
    std::vector<std::uint32_t> initialData(static_cast<std::size_t>(float4Count) * 4u, 0u);
    D3D11_BUFFER_DESC description = {};
    description.ByteWidth = float4Count * 16u;
    description.Usage = D3D11_USAGE_DEFAULT;
    description.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
    D3D11_SUBRESOURCE_DATA data = {initialData.data(), 0, 0};
    return device->CreateBuffer(&description, &data, result->Put());
}

HRESULT CreateSimpleTextureAndView(ID3D11Device* device, std::uint32_t index,
                                   ComObject<ID3D11ShaderResourceView>* view) {
    D3D11_TEXTURE2D_DESC description = {};
    description.Width = 1;
    description.Height = 1;
    description.MipLevels = 1;
    description.ArraySize = 1;
    description.Format = DXGI_FORMAT_R32G32B32A32_FLOAT;
    description.SampleDesc.Count = 1;
    description.Usage = D3D11_USAGE_DEFAULT;
    description.BindFlags = D3D11_BIND_SHADER_RESOURCE;
    const float pixel[4] = {0.2f + 0.1f * static_cast<float>(index), 0.3f, 0.5f, 1.0f};
    D3D11_SUBRESOURCE_DATA data = {pixel, sizeof(pixel), 0};
    ComObject<ID3D11Texture2D> texture;
    HRESULT hr = device->CreateTexture2D(&description, &data, texture.Put());
    if (SUCCEEDED(hr)) {
        hr = device->CreateShaderResourceView(texture.Get(), nullptr, view->Put());
    }
    return hr;
}

HRESULT CreateSimpleSampler(ID3D11Device* device, ComObject<ID3D11SamplerState>* result) {
    D3D11_SAMPLER_DESC description = {};
    description.Filter = D3D11_FILTER_MIN_MAG_MIP_LINEAR;
    description.AddressU = D3D11_TEXTURE_ADDRESS_CLAMP;
    description.AddressV = D3D11_TEXTURE_ADDRESS_CLAMP;
    description.AddressW = D3D11_TEXTURE_ADDRESS_CLAMP;
    description.ComparisonFunc = D3D11_COMPARISON_NEVER;
    description.MinLOD = 0.0f;
    description.MaxLOD = D3D11_FLOAT32_MAX;
    return device->CreateSamplerState(&description, result->Put());
}

}  // namespace

extern "C" __declspec(dllexport) HRESULT __cdecl EndfieldOriginalM23DxbcValidate(
    ID3D11Device* device, EndfieldM23DxbcValidation* report) {
    if (report == nullptr || device == nullptr) {
        return E_INVALIDARG;
    }
    std::memset(report, 0, sizeof(*report));

    ComObject<ID3D11VertexShader> vertexShader;
    ComObject<ID3D11PixelShader> pixelShader;
    HRESULT hr = device->CreateVertexShader(
        g_EndfieldM23VertexDxbc, g_EndfieldM23VertexDxbcSize, nullptr, vertexShader.Put());
    if (FAILED(hr)) {
        return hr;
    }
    report->shaderMask |= 1u;
    hr = device->CreatePixelShader(
        g_EndfieldM23PixelDxbc, g_EndfieldM23PixelDxbcSize, nullptr, pixelShader.Put());
    if (FAILED(hr)) {
        return hr;
    }
    report->shaderMask |= 2u;

    // This is the exact VS ISGN contract from 0138: POSITION/NORMAL are
    // float3; all listed attributes except BLENDINDICES are float4; indices
    // are uint4.  The byte offsets also define the minimal matching vertex.
    const D3D11_INPUT_ELEMENT_DESC input[] = {
        {"POSITION", 0, DXGI_FORMAT_R32G32B32_FLOAT, 0, 0, D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"NORMAL", 0, DXGI_FORMAT_R32G32B32_FLOAT, 0, 12, D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TANGENT", 0, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 24, D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"COLOR", 0, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 40, D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 0, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 56, D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 1, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 72, D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 4, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 88, D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"BLENDWEIGHTS", 0, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 104, D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"BLENDINDICES", 0, DXGI_FORMAT_R32G32B32A32_UINT, 0, 120, D3D11_INPUT_PER_VERTEX_DATA, 0},
    };
    ComObject<ID3D11InputLayout> inputLayout;
    hr = device->CreateInputLayout(input, static_cast<UINT>(_countof(input)),
                                   g_EndfieldM23VertexDxbc, g_EndfieldM23VertexDxbcSize,
                                   inputLayout.Put());
    if (FAILED(hr)) {
        return hr;
    }
    report->inputLayoutMask = 1u;

    const Vertex vertices[3] = {
        {{-0.5f, -0.5f, 0.0f}, {0, 0, 1}, {1, 0, 0, 1}, {1, 1, 1, 1},
         {0, 0, 0, 0}, {0, 0, 0, 0}, {0, 0, 0, 0}, {1, 0, 0, 0}, {0, 0, 0, 0}},
        {{0.0f, 0.5f, 0.0f}, {0, 0, 1}, {1, 0, 0, 1}, {1, 1, 1, 1},
         {0, 1, 0, 0}, {0, 0, 0, 0}, {0, 0, 0, 0}, {1, 0, 0, 0}, {0, 0, 0, 0}},
        {{0.5f, -0.5f, 0.0f}, {0, 0, 1}, {1, 0, 0, 1}, {1, 1, 1, 1},
         {1, 0, 0, 0}, {0, 0, 0, 0}, {0, 0, 0, 0}, {1, 0, 0, 0}, {0, 0, 0, 0}},
    };
    D3D11_BUFFER_DESC vertexDescription = {};
    vertexDescription.ByteWidth = sizeof(vertices);
    vertexDescription.Usage = D3D11_USAGE_DEFAULT;
    vertexDescription.BindFlags = D3D11_BIND_VERTEX_BUFFER;
    D3D11_SUBRESOURCE_DATA vertexData = {vertices, 0, 0};
    ComObject<ID3D11Buffer> vertexBuffer;
    hr = device->CreateBuffer(&vertexDescription, &vertexData, vertexBuffer.Put());
    if (FAILED(hr)) {
        return hr;
    }
    report->vertexBufferMask = 1u;

    ComObject<ID3D11Buffer> vertexConstantBuffers[kResourceCount];
    for (std::uint32_t i = 0; i < kResourceCount; ++i) {
        hr = CreateConstantBuffer(device, kVsConstantBufferFloats4[i], &vertexConstantBuffers[i]);
        if (FAILED(hr)) {
            return hr;
        }
        report->vertexConstantBufferMask |= 1u << i;
    }
    ComObject<ID3D11Buffer> pixelConstantBuffers[kResourceCount];
    for (std::uint32_t i = 0; i < kResourceCount; ++i) {
        hr = CreateConstantBuffer(device, kPsConstantBufferFloats4[i], &pixelConstantBuffers[i]);
        if (FAILED(hr)) {
            return hr;
        }
        report->pixelConstantBufferMask |= 1u << i;
    }

    ComObject<ID3D11ShaderResourceView> shaderResources[kResourceCount];
    ComObject<ID3D11SamplerState> samplers[kResourceCount];
    for (std::uint32_t i = 0; i < kResourceCount; ++i) {
        hr = CreateSimpleTextureAndView(device, i, &shaderResources[i]);
        if (FAILED(hr)) {
            return hr;
        }
        report->shaderResourceMask |= 1u << i;
        hr = CreateSimpleSampler(device, &samplers[i]);
        if (FAILED(hr)) {
            return hr;
        }
        report->samplerMask |= 1u << i;
    }

    D3D11_RASTERIZER_DESC rasterizerDescription = {};
    rasterizerDescription.FillMode = D3D11_FILL_SOLID;
    rasterizerDescription.CullMode = D3D11_CULL_NONE;
    rasterizerDescription.DepthClipEnable = TRUE;
    ComObject<ID3D11RasterizerState> rasterizer;
    hr = device->CreateRasterizerState(&rasterizerDescription, rasterizer.Put());
    if (FAILED(hr)) {
        return hr;
    }
    report->stateMask |= kStateRasterizer;

    D3D11_BLEND_DESC blendDescription = {};
    blendDescription.RenderTarget[0].BlendEnable = FALSE;
    blendDescription.RenderTarget[0].RenderTargetWriteMask = D3D11_COLOR_WRITE_ENABLE_ALL;
    ComObject<ID3D11BlendState> blend;
    hr = device->CreateBlendState(&blendDescription, blend.Put());
    if (FAILED(hr)) {
        return hr;
    }
    report->stateMask |= kStateBlend;

    D3D11_DEPTH_STENCIL_DESC depthDescription = {};
    depthDescription.DepthEnable = FALSE;
    depthDescription.DepthWriteMask = D3D11_DEPTH_WRITE_MASK_ZERO;
    depthDescription.DepthFunc = D3D11_COMPARISON_ALWAYS;
    depthDescription.StencilEnable = FALSE;
    ComObject<ID3D11DepthStencilState> depth;
    hr = device->CreateDepthStencilState(&depthDescription, depth.Put());
    if (FAILED(hr)) {
        return hr;
    }
    report->stateMask |= kStateDepth;

    return (report->shaderMask == 3u && report->inputLayoutMask == 1u &&
            report->vertexBufferMask == 1u &&
            report->vertexConstantBufferMask == kAllResourcesMask &&
            report->pixelConstantBufferMask == kAllResourcesMask &&
            report->shaderResourceMask == kAllResourcesMask &&
            report->samplerMask == kAllResourcesMask && report->stateMask == kAllStateMask)
               ? S_OK
               : E_FAIL;
}

extern "C" __declspec(dllexport) std::uint32_t __cdecl EndfieldOriginalM23DxbcGetVsConstantBufferCount() {
    return kResourceCount;
}

extern "C" __declspec(dllexport) std::uint32_t __cdecl EndfieldOriginalM23DxbcGetPsConstantBufferCount() {
    return kResourceCount;
}
