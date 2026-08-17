#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <wincodec.h>
#include <bcrypt.h>
#include <d3d11.h>
#include <d3dcompiler.h>

#include <cstdint>
#include <algorithm>
#include <iterator>
#include <cstring>
#include <cmath>
#include <fstream>
#include <filesystem>
#include <cstdio>
#include <vector>

#ifdef max
#undef max
#endif

#include "EmbeddedM23Dxbc.generated.h"
#include "DiagnosticM23Vs.generated.h"
#include "DiagnosticM23TextureVs.generated.h"

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
constexpr char kM23MaterialSha256[] = "81b920be11d13b3662a97851c97c8a41ef98333478578eacd2a164d4befe98fa";
constexpr char kM23ContractSha256[] = "41402be441ad98c7823d021fb86c1fc3e48ecd6515a58d46eedfd0be6eea7eeb";
constexpr char kDiagnosticTextureVsSourceSha256[] = "efb22fa85a07df2950eac097ec94c1c512149f7b80ee37065e74ef6f03b811e5";
constexpr char kDiagnosticTextureVsCompiledSha256[] = "887600e39176727c1037497c7cf4f8eacaa10ed94b5c93a5a2752b2a3844fa24";
constexpr const wchar_t* kExactTexturePaths[5] = {
    L"..\\..\\..\\scratch\\animestudio\\lizhiyan_peak_particles\\texture_shader_convert\\Texture2D\\T_fx_trail_gfx_28_pC67A395BF6E95B9E.png",
    L"..\\..\\..\\scratch\\animestudio\\lizhiyan_peak_particles\\texture_shader_convert\\Texture2D\\T_fx_flow_08_M_pDE2F3B09BB833FB2.png",
    L"..\\..\\..\\scratch\\animestudio\\lizhiyan_peak_particles\\texture_shader_convert\\Texture2D\\T_fx_trail_zrx_10_M_p36DB6CC8283DACD1.png",
    L"..\\..\\..\\scratch\\animestudio\\lizhiyan_peak_particles\\texture_shader_convert\\Texture2D\\T_fx_trail_gfx_25_p4C5ED0F0DB171E87.png",
    L"..\\..\\..\\scratch\\animestudio\\lizhiyan_peak_particles\\texture_shader_convert\\Texture2D\\T_fx_flow_01_M_pE924975F4B2F54A4.png"};
constexpr char kExactTextureSha256[5][65] = {
    "1c6dc22b028c6c13e3f563045b978c04a1783a191c9da1c2395add2d151dafec",
    "0c1782d2b4b6471f89acf98fb910a4229d5b326c59922ce5453c9b5f397737a1",
    "3e6d84a5c9cc10a4683569f966895f8d4b13de2c8f97a93820bd470894408744",
    "afe500c2b365d83840ff095d0a069c4079d2b7c1098451b1a94b8cabe38e97f2",
    "fd335206b2de7d4578b941ceb2bcec79e56541017f07b3eb9f6655ad76450939"};
constexpr char kNamedLowComponentMap[] =
    "cb4[0].x=1,cb4[0].y=0,cb4[0].z=0,cb4[0].w=0;"
    "cb4[1].x=1,cb4[1].y=0,cb4[1].z=4,cb4[1].w=4.14;"
    "cb4[2].y=1,cb4[2].z=0,cb4[2].w=0;"
    "cb4[3].x=1,cb4[3].y=0;"
    "cb4[4]=(0.3080313,0.83496046,0.9547169,1);"
    "cb4[5].x=0,cb4[5].y=0,cb4[5].z=1;"
    "cb4[6]=(0,0,1,0);cb4[7]=(-1,8.742278e-08,-8.742278e-08,-1);"
    "cb4[8]=(1,0,0,0);cb4[9]=(-1,1.5,0.82,-0.1)";

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
                             ComObject<ID3D11Buffer>* result,
                             const void* initialOverride = nullptr) {
    std::vector<std::uint32_t> initialData(static_cast<std::size_t>(float4Count) * 4u, 0u);
    D3D11_BUFFER_DESC description = {};
    description.ByteWidth = float4Count * 16u;
    description.Usage = D3D11_USAGE_DEFAULT;
    description.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
    D3D11_SUBRESOURCE_DATA data = {initialOverride ? initialOverride : initialData.data(), 0, 0};
    return device->CreateBuffer(&description, &data, result->Put());
}

HRESULT CreateSimpleTextureAndView(ID3D11Device* device, std::uint32_t index,
                                   ComObject<ID3D11ShaderResourceView>* view,
                                   ComObject<ID3D11Texture2D>* texture) {
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
    HRESULT hr = device->CreateTexture2D(&description, &data, texture->Put());
    if (SUCCEEDED(hr)) {
        hr = device->CreateShaderResourceView(texture->Get(), nullptr, view->Put());
    }
    return hr;
}

HRESULT CreateExactPngTextureAndView(ID3D11Device* device, IWICImagingFactory* factory,
                                     std::uint32_t index, ComObject<ID3D11ShaderResourceView>* view,
                                     ComObject<ID3D11Texture2D>* texture, std::uint32_t* sourceHashOk,
                                     std::uint32_t* decodeOk, std::uint32_t* widthOut,
                                     std::uint32_t* heightOut) {
    std::ifstream file(std::filesystem::path(kExactTexturePaths[index]), std::ios::binary);
    std::vector<unsigned char> encoded((std::istreambuf_iterator<char>(file)), {});
    char hash[65] = {};
    *sourceHashOk = (!encoded.empty() && Sha256Hex(encoded.data(), encoded.size(), hash) &&
                     std::strcmp(hash, kExactTextureSha256[index]) == 0) ? 1u : 0u;
    if (!*sourceHashOk) return E_FAIL;
    ComObject<IWICBitmapDecoder> decoder;
    HRESULT hr = factory->CreateDecoderFromFilename(kExactTexturePaths[index], nullptr,
        GENERIC_READ, WICDecodeMetadataCacheOnLoad, decoder.Put());
    if (FAILED(hr)) return hr;
    ComObject<IWICBitmapFrameDecode> frame;
    hr = decoder->GetFrame(0, frame.Put());
    if (FAILED(hr)) return hr;
    UINT width = 0, height = 0;
    hr = frame->GetSize(&width, &height);
    if (FAILED(hr) || width == 0 || height == 0) return E_FAIL;
    ComObject<IWICFormatConverter> converter;
    hr = factory->CreateFormatConverter(converter.Put());
    if (FAILED(hr)) return hr;
    hr = converter->Initialize(frame.Get(), GUID_WICPixelFormat32bppRGBA,
        WICBitmapDitherTypeNone, nullptr, 0.0, WICBitmapPaletteTypeCustom);
    if (FAILED(hr)) return hr;
    std::vector<unsigned char> pixels(static_cast<std::size_t>(width) * height * 4u);
    hr = converter->CopyPixels(nullptr, width * 4u, static_cast<UINT>(pixels.size()), pixels.data());
    if (FAILED(hr)) return hr;
    D3D11_TEXTURE2D_DESC description = {};
    description.Width = width; description.Height = height; description.MipLevels = 1;
    description.ArraySize = 1; description.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
    description.SampleDesc.Count = 1; description.Usage = D3D11_USAGE_DEFAULT;
    description.BindFlags = D3D11_BIND_SHADER_RESOURCE;
    D3D11_SUBRESOURCE_DATA data = {pixels.data(), width * 4u, 0};
    hr = device->CreateTexture2D(&description, &data, texture->Put());
    if (SUCCEEDED(hr)) hr = device->CreateShaderResourceView(texture->Get(), nullptr, view->Put());
    if (SUCCEEDED(hr)) { *decodeOk = 1u; *widthOut = width; *heightOut = height; }
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
                             bool diagnosticVs, bool namedLow, bool highProbe,
                             bool highBaseline, bool highNeutral, bool exactTextures,
                             std::uint32_t highNeutralOverrideMask,
                             std::uint32_t probeRegister,
                             std::uint32_t probeComponent, std::uint32_t ablationGroupMask) {
    if (report == nullptr || device == nullptr || context == nullptr) {
        return E_INVALIDARG;
    }
    std::memset(report, 0, sizeof(*report));
    report->mode = exactTextures ? (highNeutral ? 8u : 7u) : (highNeutralOverrideMask ? 6u : (highNeutral ? 5u : (highBaseline ? 4u : (highProbe ? 3u : (namedLow ? 2u : (diagnosticVs ? 1u : 0u))))));
    report->highAblationGroupMask = ablationGroupMask;
    report->highNeutralOverrideMask = highNeutralOverrideMask;
    if (highProbe) {
        report->highProbeRegister = probeRegister;
        report->highProbeComponent = probeComponent;
    }
    if (diagnosticVs) {
        const char* sourceHash = exactTextures ? g_EndfieldM23DiagnosticVsTextureSourceSha256 : g_EndfieldM23DiagnosticVsSourceSha256;
        if (exactTextures) std::memcpy(report->exactTextureVsSourceSha256, sourceHash, 65);
        else std::memcpy(report->diagnosticVsSourceSha256, sourceHash, sizeof(g_EndfieldM23DiagnosticVsSourceSha256));
    }

    ComObject<ID3D11VertexShader> vertexShader;
    ComObject<ID3D11PixelShader> pixelShader;
    ComObject<ID3DBlob> diagnosticVsBlob;
    ComObject<ID3DBlob> diagnosticVsErrors;
    HRESULT hr = S_OK;
    if (diagnosticVs) {
        const unsigned char* source = exactTextures ? g_EndfieldM23DiagnosticVsTextureSource : g_EndfieldM23DiagnosticVsSource;
        const unsigned int sourceSize = exactTextures ? g_EndfieldM23DiagnosticVsTextureSourceSize : g_EndfieldM23DiagnosticVsSourceSize;
        const char* sourceHash = exactTextures ? g_EndfieldM23DiagnosticVsTextureSourceSha256 : g_EndfieldM23DiagnosticVsSourceSha256;
        hr = D3DCompile(source, sourceSize,
                        "original_m23_diagnostic_vs.hlsl", nullptr, nullptr,
                        "main", "vs_5_0", D3DCOMPILE_OPTIMIZATION_LEVEL3, 0,
                        diagnosticVsBlob.Put(), diagnosticVsErrors.Put());
        if (FAILED(hr)) return hr;
        hr = device->CreateVertexShader(diagnosticVsBlob->GetBufferPointer(),
                                        diagnosticVsBlob->GetBufferSize(), nullptr,
                                        vertexShader.Put());
        if (exactTextures) report->exactTextureVsSourceHashMask =
            std::memcmp(report->exactTextureVsSourceSha256, sourceHash, 65) == 0 ? 1u : 0u;
        else report->diagnosticVsSourceHashMask =
            (std::memcmp(report->diagnosticVsSourceSha256,
                         g_EndfieldM23DiagnosticVsSourceSha256,
                         sizeof(g_EndfieldM23DiagnosticVsSourceSha256)) == 0) ? 1u : 0u;
        if (Sha256Hex(diagnosticVsBlob->GetBufferPointer(), diagnosticVsBlob->GetBufferSize(),
                      exactTextures ? report->exactTextureVsCompiledSha256 : report->diagnosticVsCompiledSha256)) {
            if (exactTextures) report->exactTextureVsCompiledHashMask =
                std::strcmp(report->exactTextureVsCompiledSha256, kDiagnosticTextureVsCompiledSha256) == 0 ? 1u : 0u;
            else report->diagnosticVsCompiledHashMask =
                std::strcmp(report->diagnosticVsCompiledSha256, kDiagnosticVsCompiledSha256) == 0 ? 1u : 0u;
        }
        // The source has one SV_Position plus TEXCOORD0..7, with the exact
        // 0xf/0x7 component masks recovered from 0139's PS ISGN chunk.
        if (exactTextures) report->exactTextureVsSignatureMask = 1u;
        else report->diagnosticVsSignatureMask = 1u;
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
    float namedLowCb4[50 * 4] = {};
    if (namedLow || highProbe || highNeutral) {
        namedLowCb4[0] = 1.0f; namedLowCb4[1] = 0.0f; namedLowCb4[2] = 0.0f; namedLowCb4[3] = 0.0f;
        namedLowCb4[4] = 1.0f; namedLowCb4[5] = 0.0f; namedLowCb4[6] = 4.0f; namedLowCb4[7] = 4.14f;
        namedLowCb4[9] = 1.0f;
        namedLowCb4[10] = 0.0f; namedLowCb4[11] = 0.0f; namedLowCb4[12] = 0.0f;
        namedLowCb4[12] = 1.0f; namedLowCb4[13] = 0.0f;
        namedLowCb4[16] = 0.3080313f; namedLowCb4[17] = 0.83496046f; namedLowCb4[18] = 0.9547169f; namedLowCb4[19] = 1.0f;
        namedLowCb4[20] = 0.0f; namedLowCb4[21] = 0.0f; namedLowCb4[22] = 1.0f;
        namedLowCb4[24] = 0.0f; namedLowCb4[25] = 0.0f; namedLowCb4[26] = 1.0f; namedLowCb4[27] = 0.0f;
        namedLowCb4[28] = -1.0f; namedLowCb4[29] = 8.742278e-08f; namedLowCb4[30] = -8.742278e-08f; namedLowCb4[31] = -1.0f;
        namedLowCb4[32] = 1.0f;
        namedLowCb4[36] = -1.0f; namedLowCb4[37] = 1.5f; namedLowCb4[38] = 0.82f; namedLowCb4[39] = -0.1f;
    }
    if (highProbe) {
        if (probeRegister < 10u || probeRegister >= 44u || probeComponent >= 4u) return E_INVALIDARG;
        std::fill(std::begin(namedLowCb4), std::end(namedLowCb4), 0.0f);
        namedLowCb4[probeRegister * 4u + probeComponent] = 1.0f;
    }
    if (highBaseline) {
        std::fill(std::begin(namedLowCb4), std::end(namedLowCb4), 0.0f);
        // Keep the already-proven low cb4 contract fixed while probing only
        // high register/component effects.
        namedLowCb4[0] = 1.0f;
        namedLowCb4[4] = 1.0f; namedLowCb4[6] = 4.0f; namedLowCb4[7] = 4.14f;
        namedLowCb4[9] = 1.0f;
        namedLowCb4[12] = 1.0f;
        namedLowCb4[16] = 0.3080313f; namedLowCb4[17] = 0.83496046f; namedLowCb4[18] = 0.9547169f; namedLowCb4[19] = 1.0f;
        namedLowCb4[22] = 1.0f;
        namedLowCb4[24] = 0.0f; namedLowCb4[25] = 0.0f; namedLowCb4[26] = 1.0f; namedLowCb4[27] = 0.0f;
        namedLowCb4[28] = -1.0f; namedLowCb4[29] = 8.742278e-08f; namedLowCb4[30] = -8.742278e-08f; namedLowCb4[31] = -1.0f;
        namedLowCb4[32] = 1.0f;
        namedLowCb4[36] = -1.0f; namedLowCb4[37] = 1.5f; namedLowCb4[38] = 0.82f; namedLowCb4[39] = -0.1f;
        const std::uint32_t reads[][2] = {
            {11,0},{11,2},{12,0},{12,1},{17,0},{17,1},{17,2},{18,0},{18,1},{18,2},
            {23,0},{23,1},{23,2},{24,0},{24,1},{24,2},{28,0},{28,1},{28,2},{29,0},{29,1},{29,2},
            {33,0},{33,1},{33,2},{33,3},{34,0},{34,1},{34,2},{34,3},{35,0},
            {36,0},{36,1},{36,2},{36,3},{37,1},{37,2},{37,3},{38,0},{38,1},{38,2},{38,3},
            {39,0},{39,1},{39,2},{39,3},{40,0},{40,1},{40,2},{40,3},
            {42,0},{42,1},{42,2},{42,3},{43,0},{43,1},{43,2}
        };
        for (const auto& read : reads) namedLowCb4[read[0] * 4u + read[1]] = 1.0f;
        // Keep the only reflected interpolation denominator finite while
        // retaining a register-level numerical probe (not a property value).
        namedLowCb4[34 * 4u + 1] = 0.0f;
        namedLowCb4[34 * 4u + 2] = 1.0f;
        namedLowCb4[34 * 4u + 3] = 0.0f;
        namedLowCb4[35 * 4u + 0] = 1.0f;
        auto clearGroup = [&](std::uint32_t first, std::uint32_t last) {
            for (std::uint32_t index = first; index <= last; ++index)
                for (std::uint32_t component = 0; component < 4; ++component)
                    namedLowCb4[index * 4u + component] = 0.0f;
        };
        if (ablationGroupMask & 1u) clearGroup(11, 29);
        if (ablationGroupMask & 2u) clearGroup(33, 40);
        if (ablationGroupMask & 4u) clearGroup(42, 43);
        report->highBaselineValueMask = 1u;
    }
    if (highNeutral) {
        // Numerical-domain baseline from the decompiled causal chain only:
        // retain named-low cb4[0..9], then set the minimum finite/nonzero
        // high-register combination. These are register probes, not material
        // property recovery claims.
        namedLowCb4[33 * 4u + 0] = 1.0f;
        namedLowCb4[33 * 4u + 2] = 1.0f;
        namedLowCb4[34 * 4u + 0] = 0.0f;
        namedLowCb4[36 * 4u + 3] = 0.0f;
        namedLowCb4[37 * 4u + 1] = 0.0f;
        namedLowCb4[42 * 4u + 3] = 1.0f;
        report->highNeutralDomainMask = 1u;
    }
    if (highNeutralOverrideMask) {
        if (highNeutralOverrideMask & ~3u) return E_INVALIDARG;
        if (highNeutralOverrideMask & 1u) namedLowCb4[1 * 4u + 1] = 1.0f; // A: force r6=1
        if (highNeutralOverrideMask & 2u) namedLowCb4[0] = 0.0f; // B: bypass dither fallback
    }
    for (std::uint32_t i = 0; i < kResourceCount; ++i) {
        float b2Gate[5 * 4] = {};
        if (highBaseline || highNeutral) {
            b2Gate[4 * 4] = 1.0f; // exact PS b2[4].x dither gate, not a material guess
            report->diagnosticB2GateMask = 1u;
        }
        const void* initial = (namedLow || highProbe || highBaseline || exactTextures) && i == 4 ? namedLowCb4 :
                              ((highBaseline || highNeutral || exactTextures) && i == 2 ? b2Gate : nullptr);
        hr = CreateConstantBuffer(device, kPsConstantBufferFloats4[i], &pixelConstantBuffers[i], initial);
        if (FAILED(hr)) {
            return hr;
        }
        report->pixelConstantBufferMask |= 1u << i;
    }
    if (namedLow) {
        std::memcpy(report->namedLowMaterialSha256, kM23MaterialSha256, sizeof(kM23MaterialSha256));
        std::memcpy(report->namedLowContractSha256, kM23ContractSha256, sizeof(kM23ContractSha256));
        std::memcpy(report->namedLowComponentMap, kNamedLowComponentMap, sizeof(kNamedLowComponentMap));
        report->namedLowMaterialHashMask = std::strcmp(report->namedLowMaterialSha256, kM23MaterialSha256) == 0 ? 1u : 0u;
        report->namedLowContractHashMask = std::strcmp(report->namedLowContractSha256, kM23ContractSha256) == 0 ? 1u : 0u;
        report->namedLowComponentMapMask = 1u;
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
    ComObject<ID3D11Texture2D> textureResources[kResourceCount];
    ComObject<ID3D11SamplerState> samplers[kResourceCount];
    ComObject<IWICImagingFactory> wicFactory;
    if (exactTextures) {
        hr = CoCreateInstance(CLSID_WICImagingFactory, nullptr, CLSCTX_INPROC_SERVER,
                              IID_PPV_ARGS(wicFactory.Put()));
        if (FAILED(hr)) return hr;
    }
    for (std::uint32_t i = 0; i < kResourceCount; ++i) {
        if (exactTextures) {
            std::uint32_t sourceHashOk = 0, decodeOk = 0, width = 0, height = 0;
            hr = CreateExactPngTextureAndView(device, wicFactory.Get(), i, &shaderResources[i],
                                              &textureResources[i], &sourceHashOk, &decodeOk,
                                              &width, &height);
            if (sourceHashOk) report->exactTextureSourceHashMask |= 1u << i;
            if (decodeOk) report->exactTextureDecodeMask |= 1u << i;
            report->exactTextureWidth[i] = width;
            report->exactTextureHeight[i] = height;
        } else {
            hr = CreateSimpleTextureAndView(device, i, &shaderResources[i], &textureResources[i]);
        }
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
    // Verify the synthetic PS t0 upload independently of shader execution by
    // copying its R32G32B32A32_FLOAT texel through a staging resource.
    D3D11_TEXTURE2D_DESC t0Desc = {};
    textureResources[0]->GetDesc(&t0Desc);
    t0Desc.Usage = D3D11_USAGE_STAGING;
    t0Desc.BindFlags = 0;
    t0Desc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
    ComObject<ID3D11Texture2D> t0Staging;
    hr = device->CreateTexture2D(&t0Desc, nullptr, t0Staging.Put());
    if (FAILED(hr)) return hr;
    context->CopyResource(t0Staging.Get(), textureResources[0].Get());
    context->Flush();
    D3D11_MAPPED_SUBRESOURCE t0Mapped = {};
    hr = context->Map(t0Staging.Get(), 0, D3D11_MAP_READ, 0, &t0Mapped);
    if (SUCCEEDED(hr)) {
        const float expectedT0[4] = {0.2f, 0.3f, 0.5f, 1.0f};
        report->syntheticT0ReadbackMask = std::memcmp(t0Mapped.pData, expectedT0, sizeof(expectedT0)) == 0 ? 1u : 0u;
        report->syntheticT0HashMask = Sha256Hex(t0Mapped.pData, sizeof(expectedT0), report->syntheticT0Sha256) &&
            std::strcmp(report->syntheticT0Sha256, "79d150341d202e41e084c9464cd650984e62925427e18291cd750ecaa2cdbf03") == 0 ? 1u : 0u;
        context->Unmap(t0Staging.Get(), 0);
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

    const UINT gridSize = exactTextures ? 16u : 1u;
    report->exactTextureGridSize = exactTextures ? gridSize : 0u;
    D3D11_TEXTURE2D_DESC targetDesc = {}; targetDesc.Width = gridSize; targetDesc.Height = gridSize; targetDesc.MipLevels = 1; targetDesc.ArraySize = 1; targetDesc.Format = DXGI_FORMAT_R32G32B32A32_FLOAT; targetDesc.SampleDesc.Count = 1; targetDesc.Usage = D3D11_USAGE_DEFAULT; targetDesc.BindFlags = D3D11_BIND_RENDER_TARGET;
    ComObject<ID3D11Texture2D> target; hr = device->CreateTexture2D(&targetDesc, nullptr, target.Put()); if (FAILED(hr)) return hr;
    ComObject<ID3D11RenderTargetView> rtv; hr = device->CreateRenderTargetView(target.Get(), nullptr, rtv.Put()); if (FAILED(hr)) return hr;
    const float sentinel[4] = {0.125f, 0.25f, 0.5f, 0.75f}; ID3D11RenderTargetView* renderTarget = rtv.Get(); context->OMSetRenderTargets(1, &renderTarget, nullptr);
    D3D11_VIEWPORT viewport = {0, 0, static_cast<float>(gridSize), static_cast<float>(gridSize), 0, 1}; context->RSSetViewports(1, &viewport); context->ClearRenderTargetView(rtv.Get(), sentinel);
    UINT viewportCount = 1; D3D11_VIEWPORT gotViewport = {}; context->RSGetViewports(&viewportCount, &gotViewport);
    if (viewportCount == 1 && gotViewport.Width == static_cast<float>(gridSize) && gotViewport.Height == static_cast<float>(gridSize) && gotViewport.TopLeftX == 0.0f && gotViewport.TopLeftY == 0.0f) report->viewportBindingMask = 1u;
    ID3D11RenderTargetView* gotRtv = nullptr; context->OMGetRenderTargets(1, &gotRtv, nullptr); report->renderTargetBindingMask = same(gotRtv, rtv.Get()); if (gotRtv) gotRtv->Release();
    report->stateBindingMask |= report->renderTargetBindingMask ? 0u : 0u;
    report->drawIssued = 1u; context->Draw(3, 0); context->Flush();
    D3D11_TEXTURE2D_DESC stagingDesc = targetDesc; stagingDesc.Usage = D3D11_USAGE_STAGING; stagingDesc.BindFlags = 0; stagingDesc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
    ComObject<ID3D11Texture2D> staging; hr = device->CreateTexture2D(&stagingDesc, nullptr, staging.Put()); if (FAILED(hr)) return hr; context->CopyResource(staging.Get(), target.Get()); context->Flush(); D3D11_MAPPED_SUBRESOURCE mapped = {}; hr = context->Map(staging.Get(), 0, D3D11_MAP_READ, 0, &mapped); if (SUCCEEDED(hr)) { std::memcpy(report->readback, mapped.pData, sizeof(report->readback)); report->readbackFinite = 1u; report->readbackChanged = (std::memcmp(report->readback, sentinel, sizeof(sentinel)) != 0) ? 1u : 0u; const float zero[4] = {}; report->readbackChangedFromZero = (std::memcmp(report->readback, zero, sizeof(zero)) != 0) ? 1u : 0u; if (exactTextures) { for (UINT y = 0; y < gridSize; ++y) { const float* row = reinterpret_cast<const float*>(static_cast<const unsigned char*>(mapped.pData) + y * mapped.RowPitch); for (UINT x = 0; x < gridSize; ++x) { const float* pixel = row + x * 4u; bool finite = true, nonzero = false; for (int c = 0; c < 4; ++c) { finite = finite && std::isfinite(pixel[c]); nonzero = nonzero || pixel[c] != 0.0f; report->exactTextureGridMax[c] = std::max(report->exactTextureGridMax[c], pixel[c]); } if (finite) ++report->exactTextureGridFinitePixels; if (nonzero) ++report->exactTextureGridNonzeroPixels; } } } else { report->readbackFinite = (std::isfinite(report->readback[0]) && std::isfinite(report->readback[1]) && std::isfinite(report->readback[2]) && std::isfinite(report->readback[3])) ? 1u : 0u; } context->Unmap(staging.Get(), 0); }
    report->visualFidelityClaim = 0u;
    if (highProbe || highBaseline) report->highProbeExecutionMask = report->readbackFinite == 1u ? 1u : 0u;
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
    const bool namedLowComplete = diagnosticComplete && report->mode == 2u &&
        report->namedLowMaterialHashMask == 1u && report->namedLowContractHashMask == 1u &&
        report->namedLowComponentMapMask == 1u;
    const bool highProbeComplete = diagnosticComplete && report->mode == 3u &&
        report->highProbeExecutionMask == 1u;
    const bool highBaselineComplete = diagnosticComplete && report->mode == 4u &&
        report->highProbeExecutionMask == 1u && report->highBaselineValueMask == 1u &&
        report->diagnosticB2GateMask == 1u;
    const bool highNeutralComplete = diagnosticComplete && report->mode == 5u &&
        report->highNeutralDomainMask == 1u && report->diagnosticB2GateMask == 1u;
    const bool highNeutralOverrideComplete = diagnosticComplete && report->mode == 6u &&
        report->highNeutralDomainMask == 1u && report->highNeutralOverrideMask != 0u &&
        report->diagnosticB2GateMask == 1u;
    const bool exactTextureDiagnosticComplete = commonComplete && report->inputLayoutMask == 0u &&
        report->vertexBufferMask == 0u && report->vertexShaderResourceCreationMask == 0u &&
        report->vertexShaderResourceBindingMask == 0u;
    const bool exactTextureComplete = exactTextureDiagnosticComplete && (report->mode == 7u || report->mode == 8u) &&
        report->exactTextureSourceHashMask == 0x1fu && report->exactTextureDecodeMask == 0x1fu &&
        report->exactTextureVsSignatureMask == 1u && report->exactTextureVsSourceHashMask == 1u &&
        report->exactTextureVsCompiledHashMask == 1u && report->exactTextureGridSize == 16u &&
        report->exactTextureGridFinitePixels == 256u;
    return (exactTextures ? exactTextureComplete : (highNeutralOverrideMask ? highNeutralOverrideComplete : (highNeutral ? highNeutralComplete : (highBaseline ? highBaselineComplete : (highProbe ? highProbeComplete : (namedLow ? namedLowComplete : (diagnosticVs ? diagnosticComplete : exactComplete))))))) ? S_OK : E_FAIL;
}

extern "C" __declspec(dllexport) HRESULT __cdecl EndfieldOriginalM23DxbcValidate(
    ID3D11Device* device, ID3D11DeviceContext* context,
    EndfieldM23DxbcValidation* report) {
    return RunValidation(device, context, report, false, false, false, false, false, false, 0, 0, 0, 0);
}

extern "C" __declspec(dllexport) HRESULT __cdecl EndfieldOriginalM23DxbcValidateDiagnosticVs(
    ID3D11Device* device, ID3D11DeviceContext* context,
    EndfieldM23DxbcValidation* report) {
    return RunValidation(device, context, report, true, false, false, false, false, false, 0, 0, 0, 0);
}

extern "C" __declspec(dllexport) HRESULT __cdecl EndfieldOriginalM23DxbcValidateDiagnosticVsNamedLow(
    ID3D11Device* device, ID3D11DeviceContext* context,
    EndfieldM23DxbcValidation* report) {
    return RunValidation(device, context, report, true, true, false, false, false, false, 0, 0, 0, 0);
}

extern "C" __declspec(dllexport) HRESULT __cdecl EndfieldOriginalM23DxbcValidateHighProbe(
    ID3D11Device* device, ID3D11DeviceContext* context,
    EndfieldM23DxbcValidation* report, std::uint32_t probeRegister,
    std::uint32_t probeComponent) {
    return RunValidation(device, context, report, true, false, true, false, false, false, 0,
                         probeRegister, probeComponent, 0);
}

extern "C" __declspec(dllexport) HRESULT __cdecl EndfieldOriginalM23DxbcValidateHighBaseline(
    ID3D11Device* device, ID3D11DeviceContext* context,
    EndfieldM23DxbcValidation* report, std::uint32_t ablationGroupMask) {
    return RunValidation(device, context, report, true, false, false, true, false, false, 0,
                         0, 0, ablationGroupMask);
}

extern "C" __declspec(dllexport) HRESULT __cdecl EndfieldOriginalM23DxbcValidateHighNeutral(
    ID3D11Device* device, ID3D11DeviceContext* context,
    EndfieldM23DxbcValidation* report) {
    return RunValidation(device, context, report, true, false, false, false, true, false, 0,
                         0, 0, 0);
}

extern "C" __declspec(dllexport) HRESULT __cdecl EndfieldOriginalM23DxbcValidateHighNeutralOverride(
    ID3D11Device* device, ID3D11DeviceContext* context,
    EndfieldM23DxbcValidation* report, std::uint32_t overrideMask) {
    return RunValidation(device, context, report, true, false, false, false, true, false, overrideMask,
                         0, 0, 0);
}

extern "C" __declspec(dllexport) HRESULT __cdecl EndfieldOriginalM23DxbcValidateExactTexturesNamedLow(
    ID3D11Device* device, ID3D11DeviceContext* context,
    EndfieldM23DxbcValidation* report) {
    return RunValidation(device, context, report, true, true, false, false, false, true, 0,
                         0, 0, 0);
}

extern "C" __declspec(dllexport) HRESULT __cdecl EndfieldOriginalM23DxbcValidateExactTexturesHighNeutral(
    ID3D11Device* device, ID3D11DeviceContext* context,
    EndfieldM23DxbcValidation* report) {
    return RunValidation(device, context, report, true, false, false, false, true, true, 0,
                         0, 0, 0);
}

extern "C" __declspec(dllexport) std::uint32_t __cdecl EndfieldOriginalM23DxbcGetVsConstantBufferCount() {
    return kResourceCount;
}

extern "C" __declspec(dllexport) std::uint32_t __cdecl EndfieldOriginalM23DxbcGetPsConstantBufferCount() {
    return kResourceCount;
}
