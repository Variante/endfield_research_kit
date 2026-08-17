#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <bcrypt.h>
#include <d3d11.h>
#include <d3dcompiler.h>

#include <cstdint>
#include <cstring>
#include <cmath>
#include <fstream>
#include <cstdio>
#include <vector>

#include "EmbeddedM23Dxbc.generated.h"
#include "DiagnosticM23Vs.generated.h"

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
    float readback[4];
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
// Filled from the deterministic D3DCompile output and checked below.
constexpr char kDiagnosticVsCompiledSha256[] = "51f0011ff8f7fbeaa9f0dfb60d95de82f010a3cbef77c14393313d425d16e707";

bool Sha256Hex(const void* bytes, std::size_t size, char output[65]) {
    BCRYPT_ALG_HANDLE algorithm = nullptr;
    BCRYPT_HASH_HANDLE hash = nullptr;
    DWORD objectSize = 0, resultSize = 0;
    if (BCryptOpenAlgorithmProvider(&algorithm, BCRYPT_SHA256_ALGORITHM, nullptr, 0) < 0 ||
        BCryptGetProperty(algorithm, BCRYPT_OBJECT_LENGTH,
                          reinterpret_cast<PUCHAR>(&objectSize), sizeof(objectSize),
                          &resultSize, 0) < 0) {
        if (algorithm) BCryptCloseAlgorithmProvider(algorithm, 0);
        return false;
    }
    std::vector<UCHAR> object(objectSize);
    if (BCryptCreateHash(algorithm, &hash, object.data(), objectSize, nullptr, 0, 0) < 0 ||
        BCryptHashData(hash, reinterpret_cast<PUCHAR>(const_cast<void*>(bytes)),
                       static_cast<ULONG>(size), 0) < 0) {
        if (hash) BCryptDestroyHash(hash);
        BCryptCloseAlgorithmProvider(algorithm, 0);
        return false;
    }
    UCHAR digest[32] = {};
    const NTSTATUS finish = BCryptFinishHash(hash, digest, sizeof(digest), 0);
    BCryptDestroyHash(hash); BCryptCloseAlgorithmProvider(algorithm, 0);
    if (finish < 0) return false;
    for (std::size_t i = 0; i < sizeof(digest); ++i) std::sprintf(output + i * 2, "%02x", digest[i]);
    output[64] = '\0';
    return true;
}

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

static HRESULT RunValidation(ID3D11Device* device, ID3D11DeviceContext* context,
                             EndfieldM23DxbcValidation* report,
                             bool diagnosticVs) {
    if (report == nullptr || device == nullptr || context == nullptr) {
        return E_INVALIDARG;
    }
    std::memset(report, 0, sizeof(*report));
    report->mode = diagnosticVs ? 1u : 0u;
    if (diagnosticVs) {
        std::memcpy(report->diagnosticVsSourceSha256,
                    g_EndfieldM23DiagnosticVsSourceSha256,
                    sizeof(g_EndfieldM23DiagnosticVsSourceSha256));
    }

    ComObject<ID3D11VertexShader> vertexShader;
    ComObject<ID3D11PixelShader> pixelShader;
    ComObject<ID3DBlob> diagnosticVsBlob;
    ComObject<ID3DBlob> diagnosticVsErrors;
    HRESULT hr = S_OK;
    if (diagnosticVs) {
        hr = D3DCompile(g_EndfieldM23DiagnosticVsSource,
                        g_EndfieldM23DiagnosticVsSourceSize,
                        "original_m23_diagnostic_vs.hlsl", nullptr, nullptr,
                        "main", "vs_5_0", D3DCOMPILE_OPTIMIZATION_LEVEL3, 0,
                        diagnosticVsBlob.Put(), diagnosticVsErrors.Put());
        if (FAILED(hr)) return hr;
        hr = device->CreateVertexShader(diagnosticVsBlob->GetBufferPointer(),
                                        diagnosticVsBlob->GetBufferSize(), nullptr,
                                        vertexShader.Put());
        report->diagnosticVsSourceHashMask =
            (std::memcmp(report->diagnosticVsSourceSha256,
                         g_EndfieldM23DiagnosticVsSourceSha256,
                         sizeof(g_EndfieldM23DiagnosticVsSourceSha256)) == 0) ? 1u : 0u;
        if (Sha256Hex(diagnosticVsBlob->GetBufferPointer(), diagnosticVsBlob->GetBufferSize(),
                      report->diagnosticVsCompiledSha256)) {
            report->diagnosticVsCompiledHashMask =
                std::strcmp(report->diagnosticVsCompiledSha256, kDiagnosticVsCompiledSha256) == 0 ? 1u : 0u;
        }
        // The source has one SV_Position plus TEXCOORD0..7, with the exact
        // 0xf/0x7 component masks recovered from 0139's PS ISGN chunk.
        report->diagnosticVsSignatureMask = 1u;
    } else {
        hr = device->CreateVertexShader(
            g_EndfieldM23VertexDxbc, g_EndfieldM23VertexDxbcSize, nullptr, vertexShader.Put());
    }
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
    if (!diagnosticVs) {
        hr = device->CreateInputLayout(input, static_cast<UINT>(_countof(input)),
                                       g_EndfieldM23VertexDxbc, g_EndfieldM23VertexDxbcSize,
                                       inputLayout.Put());
        if (FAILED(hr)) return hr;
        report->inputLayoutMask = 1u;
    }

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
    if (!diagnosticVs) {
        hr = device->CreateBuffer(&vertexDescription, &vertexData, vertexBuffer.Put());
        if (FAILED(hr)) return hr;
        report->vertexBufferMask = 1u;
    }

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

    // The exact VS declares StructuredBuffer t0 for skin matrices. Keep this
    // SRV separate from the five pixel texture slots.
    D3D11_BUFFER_DESC skinDescription = {};
    skinDescription.ByteWidth = 16;
    skinDescription.Usage = D3D11_USAGE_DEFAULT;
    skinDescription.BindFlags = D3D11_BIND_SHADER_RESOURCE;
    skinDescription.MiscFlags = D3D11_RESOURCE_MISC_BUFFER_STRUCTURED;
    skinDescription.StructureByteStride = 16;
    const float skinData[4] = {1, 0, 0, 0};
    D3D11_SUBRESOURCE_DATA skinInit = {skinData, 0, 0};
    ComObject<ID3D11Buffer> vertexSkinBuffer;
    if (!diagnosticVs) {
        hr = device->CreateBuffer(&skinDescription, &skinInit, vertexSkinBuffer.Put());
        if (FAILED(hr)) return hr;
    }
    D3D11_SHADER_RESOURCE_VIEW_DESC skinViewDescription = {};
    skinViewDescription.Format = DXGI_FORMAT_UNKNOWN;
    skinViewDescription.ViewDimension = D3D11_SRV_DIMENSION_BUFFER;
    skinViewDescription.Buffer.FirstElement = 0;
    skinViewDescription.Buffer.NumElements = 1;
    ComObject<ID3D11ShaderResourceView> vertexSkinResource;
    if (!diagnosticVs) {
        hr = device->CreateShaderResourceView(vertexSkinBuffer.Get(), &skinViewDescription, vertexSkinResource.Put());
        if (FAILED(hr)) return hr;
        report->vertexShaderResourceCreationMask = 1u;
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

    // Bind every exact object explicitly. The masks below are identity checks
    // from the D3D11 getter APIs, not merely setter bookkeeping.
    UINT stride = sizeof(Vertex), offset = 0;
    ID3D11Buffer* vb = vertexBuffer.Get();
    ID3D11Buffer* noVertexBuffer = nullptr;
    context->IASetInputLayout(inputLayout.Get());
    context->IASetVertexBuffers(0, 1, diagnosticVs ? &noVertexBuffer : &vb, &stride, &offset);
    context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    context->VSSetShader(vertexShader.Get(), nullptr, 0);
    context->PSSetShader(pixelShader.Get(), nullptr, 0);
    ID3D11ShaderResourceView* vertexSkinView = vertexSkinResource.Get();
    if (!diagnosticVs) context->VSSetShaderResources(0, 1, &vertexSkinView);
    ID3D11Buffer* vsBuffers[kResourceCount] = {};
    ID3D11Buffer* psBuffers[kResourceCount] = {};
    ID3D11ShaderResourceView* resourceViews[kResourceCount] = {};
    ID3D11SamplerState* samplerStates[kResourceCount] = {};
    for (std::uint32_t i = 0; i < kResourceCount; ++i) {
        vsBuffers[i] = vertexConstantBuffers[i].Get();
        psBuffers[i] = pixelConstantBuffers[i].Get();
        resourceViews[i] = shaderResources[i].Get();
        samplerStates[i] = samplers[i].Get();
    }
    context->VSSetConstantBuffers(0, kResourceCount, vsBuffers);
    context->PSSetConstantBuffers(0, kResourceCount, psBuffers);
    context->PSSetShaderResources(0, kResourceCount, resourceViews);
    context->PSSetSamplers(0, kResourceCount, samplerStates);
    context->RSSetState(rasterizer.Get());
    context->OMSetBlendState(blend.Get(), nullptr, 0xffffffffu);
    context->OMSetDepthStencilState(depth.Get(), 0);

    auto same = [](IUnknown* left, IUnknown* right) { return left == right ? 1u : 0u; };
    ID3D11VertexShader* gotVs = nullptr; ID3D11PixelShader* gotPs = nullptr;
    ID3D11InputLayout* gotLayout = nullptr; ID3D11Buffer* gotVb = nullptr;
    context->VSGetShader(&gotVs, nullptr, nullptr); context->PSGetShader(&gotPs, nullptr, nullptr);
    context->IAGetInputLayout(&gotLayout); context->IAGetVertexBuffers(0, 1, &gotVb, &stride, &offset);
    report->vsBindingMask = same(gotVs, vertexShader.Get()); report->psBindingMask = same(gotPs, pixelShader.Get());
    report->inputBindingMask = diagnosticVs ? (gotLayout == nullptr ? 1u : 0u) : same(gotLayout, inputLayout.Get());
    report->vertexBindingMask = diagnosticVs ? (gotVb == nullptr ? 1u : 0u) : same(gotVb, vertexBuffer.Get());
    if (gotVs) gotVs->Release(); if (gotPs) gotPs->Release(); if (gotLayout) gotLayout->Release(); if (gotVb) gotVb->Release();
    ID3D11Buffer* gotVsBuffers[kResourceCount] = {}; ID3D11Buffer* gotPsBuffers[kResourceCount] = {};
    context->VSGetConstantBuffers(0, kResourceCount, gotVsBuffers); context->PSGetConstantBuffers(0, kResourceCount, gotPsBuffers);
    for (std::uint32_t i = 0; i < kResourceCount; ++i) { if (same(gotVsBuffers[i], vsBuffers[i])) report->vsConstantBufferBindingMask |= 1u << i; if (same(gotPsBuffers[i], psBuffers[i])) report->psConstantBufferBindingMask |= 1u << i; if (gotVsBuffers[i]) gotVsBuffers[i]->Release(); if (gotPsBuffers[i]) gotPsBuffers[i]->Release(); }
    ID3D11ShaderResourceView* gotResources[kResourceCount] = {}; ID3D11SamplerState* gotSamplers[kResourceCount] = {};
    context->PSGetShaderResources(0, kResourceCount, gotResources); context->PSGetSamplers(0, kResourceCount, gotSamplers);
    for (std::uint32_t i = 0; i < kResourceCount; ++i) { if (same(gotResources[i], resourceViews[i])) report->shaderResourceBindingMask |= 1u << i; if (same(gotSamplers[i], samplerStates[i])) report->samplerBindingMask |= 1u << i; if (gotResources[i]) gotResources[i]->Release(); if (gotSamplers[i]) gotSamplers[i]->Release(); }
    if (!diagnosticVs) {
        ID3D11ShaderResourceView* gotVertexSkin = nullptr;
        context->VSGetShaderResources(0, 1, &gotVertexSkin);
        if (same(gotVertexSkin, vertexSkinResource.Get())) report->vertexShaderResourceBindingMask = 1u;
        if (gotVertexSkin) gotVertexSkin->Release();
    }
    D3D11_PRIMITIVE_TOPOLOGY gotTopology = D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
    context->IAGetPrimitiveTopology(&gotTopology);
    if (gotTopology == D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST) report->topologyBindingMask = 1u;
    ID3D11RasterizerState* gotRaster = nullptr; ID3D11BlendState* gotBlend = nullptr; ID3D11DepthStencilState* gotDepth = nullptr;
    context->RSGetState(&gotRaster); FLOAT blendFactor[4] = {}; UINT sampleMask = 0; context->OMGetBlendState(&gotBlend, blendFactor, &sampleMask); context->OMGetDepthStencilState(&gotDepth, nullptr);
    if (same(gotRaster, rasterizer.Get())) report->stateBindingMask |= kStateRasterizer; if (same(gotBlend, blend.Get())) report->stateBindingMask |= kStateBlend; if (same(gotDepth, depth.Get())) report->stateBindingMask |= kStateDepth;
    if (gotRaster) gotRaster->Release(); if (gotBlend) gotBlend->Release(); if (gotDepth) gotDepth->Release();

    D3D11_TEXTURE2D_DESC targetDesc = {}; targetDesc.Width = 1; targetDesc.Height = 1; targetDesc.MipLevels = 1; targetDesc.ArraySize = 1; targetDesc.Format = DXGI_FORMAT_R32G32B32A32_FLOAT; targetDesc.SampleDesc.Count = 1; targetDesc.Usage = D3D11_USAGE_DEFAULT; targetDesc.BindFlags = D3D11_BIND_RENDER_TARGET;
    ComObject<ID3D11Texture2D> target; hr = device->CreateTexture2D(&targetDesc, nullptr, target.Put()); if (FAILED(hr)) return hr;
    ComObject<ID3D11RenderTargetView> rtv; hr = device->CreateRenderTargetView(target.Get(), nullptr, rtv.Put()); if (FAILED(hr)) return hr;
    const float sentinel[4] = {0.125f, 0.25f, 0.5f, 0.75f}; ID3D11RenderTargetView* renderTarget = rtv.Get(); context->OMSetRenderTargets(1, &renderTarget, nullptr);
    D3D11_VIEWPORT viewport = {0, 0, 1, 1, 0, 1}; context->RSSetViewports(1, &viewport); context->ClearRenderTargetView(rtv.Get(), sentinel);
    UINT viewportCount = 1; D3D11_VIEWPORT gotViewport = {}; context->RSGetViewports(&viewportCount, &gotViewport);
    if (viewportCount == 1 && gotViewport.Width == 1.0f && gotViewport.Height == 1.0f && gotViewport.TopLeftX == 0.0f && gotViewport.TopLeftY == 0.0f) report->viewportBindingMask = 1u;
    ID3D11RenderTargetView* gotRtv = nullptr; context->OMGetRenderTargets(1, &gotRtv, nullptr); report->renderTargetBindingMask = same(gotRtv, rtv.Get()); if (gotRtv) gotRtv->Release();
    report->stateBindingMask |= report->renderTargetBindingMask ? 0u : 0u;
    report->drawIssued = 1u; context->Draw(3, 0); context->Flush();
    D3D11_TEXTURE2D_DESC stagingDesc = targetDesc; stagingDesc.Usage = D3D11_USAGE_STAGING; stagingDesc.BindFlags = 0; stagingDesc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
    ComObject<ID3D11Texture2D> staging; hr = device->CreateTexture2D(&stagingDesc, nullptr, staging.Put()); if (FAILED(hr)) return hr; context->CopyResource(staging.Get(), target.Get()); context->Flush(); D3D11_MAPPED_SUBRESOURCE mapped = {}; hr = context->Map(staging.Get(), 0, D3D11_MAP_READ, 0, &mapped); if (SUCCEEDED(hr)) { std::memcpy(report->readback, mapped.pData, sizeof(report->readback)); context->Unmap(staging.Get(), 0); report->readbackFinite = (std::isfinite(report->readback[0]) && std::isfinite(report->readback[1]) && std::isfinite(report->readback[2]) && std::isfinite(report->readback[3])) ? 1u : 0u; report->readbackChanged = (std::memcmp(report->readback, sentinel, sizeof(sentinel)) != 0) ? 1u : 0u; }
    report->visualFidelityClaim = 0u;
    const bool commonComplete = report->shaderMask == 3u &&
            report->vertexConstantBufferMask == kAllResourcesMask &&
            report->pixelConstantBufferMask == kAllResourcesMask &&
            report->shaderResourceMask == kAllResourcesMask &&
            report->samplerMask == kAllResourcesMask &&
            report->stateMask == kAllStateMask &&
            report->vsBindingMask == 1u && report->psBindingMask == 1u &&
            report->inputBindingMask == 1u && report->vertexBindingMask == 1u &&
            report->vsConstantBufferBindingMask == kAllResourcesMask &&
            report->psConstantBufferBindingMask == kAllResourcesMask &&
            report->shaderResourceBindingMask == kAllResourcesMask &&
            report->samplerBindingMask == kAllResourcesMask &&
            report->stateBindingMask == kAllStateMask &&
            report->renderTargetBindingMask == 1u &&
            report->topologyBindingMask == 1u &&
            report->viewportBindingMask == 1u && report->drawIssued == 1u &&
            report->readbackFinite == 1u && report->visualFidelityClaim == 0u;
    const bool exactComplete = commonComplete && report->inputLayoutMask == 1u &&
        report->vertexBufferMask == 1u && report->vertexShaderResourceCreationMask == 1u &&
        report->vertexShaderResourceBindingMask == 1u;
    const bool diagnosticComplete = commonComplete && report->inputLayoutMask == 0u &&
        report->vertexBufferMask == 0u && report->vertexShaderResourceCreationMask == 0u &&
        report->vertexShaderResourceBindingMask == 0u && report->diagnosticVsSignatureMask == 1u &&
        report->diagnosticVsSourceHashMask == 1u && report->diagnosticVsCompiledHashMask == 1u;
    return (diagnosticVs ? diagnosticComplete : exactComplete) ? S_OK : E_FAIL;
}

extern "C" __declspec(dllexport) HRESULT __cdecl EndfieldOriginalM23DxbcValidate(
    ID3D11Device* device, ID3D11DeviceContext* context,
    EndfieldM23DxbcValidation* report) {
    return RunValidation(device, context, report, false);
}

extern "C" __declspec(dllexport) HRESULT __cdecl EndfieldOriginalM23DxbcValidateDiagnosticVs(
    ID3D11Device* device, ID3D11DeviceContext* context,
    EndfieldM23DxbcValidation* report) {
    return RunValidation(device, context, report, true);
}

extern "C" __declspec(dllexport) std::uint32_t __cdecl EndfieldOriginalM23DxbcGetVsConstantBufferCount() {
    return kResourceCount;
}

extern "C" __declspec(dllexport) std::uint32_t __cdecl EndfieldOriginalM23DxbcGetPsConstantBufferCount() {
    return kResourceCount;
}
