#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <bcrypt.h>
#include <d3d11.h>
#include <d3dcompiler.h>

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <limits>
#include <mutex>
#include <new>

#include "IUnityInterface.h"
#include "IUnityGraphicsD3D11.h"
#include "IUnityShaderCompilerAccess.h"
#include "EmbeddedDxbc.generated.h"
#include "M14CapturePayload.generated.h"
#include "M27SubstitutionRegistry.h"

namespace
{
constexpr const char* kReservedKeyword = "ENDFIELD_ORIGINAL_DXBC_EXACT";
constexpr const char* kM27ReservedKeyword = "ENDFIELD_ORIGINAL_DXBC_M27_EXACT";
constexpr std::uint32_t kContractVersion = 2;
constexpr std::uint32_t kTextureSlotCount = 26;
constexpr std::uint32_t kConstantBufferSlotCount = 9;

enum class SubstitutionRoute : std::uint32_t
{
    None = 0,
    DeferredDiagnostic = 1,
    M27HashPinned = 2,
};

IUnityInterfaces* g_unityInterfaces = nullptr;
std::atomic<bool> g_armed{false};
std::atomic<SubstitutionRoute> g_substitutionRoute{SubstitutionRoute::None};
std::atomic<std::uint32_t> g_pluginLoadCount{0};
std::atomic<std::uint32_t> g_configureCount{0};
std::atomic<bool> g_vertexClaimed{false};
std::atomic<bool> g_pixelClaimed{false};
std::atomic<std::uint32_t> g_callbackCount{0};
std::atomic<std::uint32_t> g_unarmedCallbackCount{0};
std::atomic<std::uint32_t> g_blockedCount{0};
std::atomic<std::uint32_t> g_vertexSwapCount{0};
std::atomic<std::uint32_t> g_pixelSwapCount{0};
std::atomic<std::uint32_t> g_failureCount{0};
std::atomic<HRESULT> g_lastResult{S_OK};
std::atomic<void*> g_lastVertexShader{nullptr};
std::atomic<void*> g_lastPixelShader{nullptr};
ID3D11VertexShader* g_runtimeVertexShader = nullptr;
ID3D11PixelShader* g_runtimePixelShader = nullptr;
std::atomic<std::uint32_t> g_renderEventCount{0};
std::atomic<std::uint32_t> g_exactShaderBound{0};
std::atomic<std::uint32_t> g_constantBufferMask{0};
std::atomic<std::uint32_t> g_shaderResourceMask{0};
std::atomic<std::uint32_t> g_shaderResourceFailureMask{0};
HRESULT g_shaderResourceFailureResults[kTextureSlotCount] = {};
std::atomic<std::uint32_t> g_postDrawShaderResourceMask{0};
std::atomic<std::uint32_t> g_samplerMask{0};
std::uintptr_t g_texturePointers[kTextureSlotCount] = {};
std::atomic<std::uint32_t> g_texturePointerCount{0};
std::atomic<std::uint32_t> g_m27MatchCount{0};
std::atomic<std::uint32_t> g_m27MismatchCount{0};
std::atomic<std::uint32_t> g_m27VariantHashConflictCount{0};
std::atomic<std::uint32_t> g_m27MaxVertexInputCount{0};
std::atomic<std::uint32_t> g_m27MaxVertexOutputCount{0};
std::atomic<std::uint32_t> g_m27MaxPixelInputCount{0};
std::atomic<std::uint32_t> g_m27MaxPixelOutputCount{0};
std::atomic<std::uint8_t> g_m27ObservedVertexSha256[32] = {};
std::atomic<std::uint8_t> g_m27ObservedPixelSha256[32] = {};

ID3D11VertexShader* g_m14RuntimeVertexShader = nullptr;
ID3D11PixelShader* g_m14RuntimePixelShader = nullptr;
ID3D11InputLayout* g_m14InputLayout = nullptr;
ID3D11Buffer* g_m14VertexBuffer = nullptr;
ID3D11Buffer* g_m14DefaultVertexBuffer = nullptr;
ID3D11Buffer* g_m14IndexBuffer = nullptr;
ID3D11Buffer* g_m14VertexConstantBuffers[5] = {};
ID3D11Buffer* g_m14PixelConstantBuffers[4] = {};
ID3D11Buffer* g_m14SkinBuffer = nullptr;
ID3D11ShaderResourceView* g_m14SkinView = nullptr;
ID3D11SamplerState* g_m14Samplers[2] = {};
ID3D11BlendState* g_m14BlendState = nullptr;
ID3D11DepthStencilState* g_m14DepthState = nullptr;
ID3D11RasterizerState* g_m14RasterizerState = nullptr;
std::atomic<std::uintptr_t> g_m14DepthTexture{0};
std::atomic<std::uintptr_t> g_m14MainTexture{0};
std::atomic<std::uint32_t> g_m14DrawCount{0};
std::atomic<std::uint32_t> g_m14FailureCount{0};
std::atomic<HRESULT> g_m14LastResult{S_OK};

constexpr std::size_t kM27CallbackObservationCapacity = 512;
constexpr std::size_t kM27CallbackMetadataCount = 12;
struct M27CallbackObservation
{
    std::uint32_t metadata[kM27CallbackMetadataCount];
    unsigned char sha256[32];
};
M27CallbackObservation g_m27CallbackObservations[kM27CallbackObservationCapacity] = {};
std::size_t g_m27CallbackObservationCount = 0;
std::mutex g_m27CallbackObservationMutex;

bool Sha256(
    const unsigned char* data,
    std::size_t size,
    unsigned char digest[32])
{
    if (data == nullptr || size == 0 ||
        size > (std::numeric_limits<ULONG>::max)())
        return false;
    return BCRYPT_SUCCESS(BCryptHash(
        BCRYPT_SHA256_ALG_HANDLE,
        nullptr,
        0,
        const_cast<PUCHAR>(data),
        static_cast<ULONG>(size),
        digest,
        32));
}

void ObserveM27Callback(
    const unsigned char* byteCode,
    std::size_t byteCodeSize,
    bool isVertex)
{
    unsigned char digest[32] = {};
    if (!Sha256(byteCode, byteCodeSize, digest))
        return;

    M27CallbackObservation observation = {};
    observation.metadata[0] = isVertex ? 1u : 2u;
    observation.metadata[1] = static_cast<std::uint32_t>(byteCodeSize);
    std::memcpy(observation.sha256, digest, sizeof(digest));

    ID3D11ShaderReflection* reflection = nullptr;
    if (SUCCEEDED(D3DReflect(
            byteCode,
            byteCodeSize,
            IID_ID3D11ShaderReflection,
            reinterpret_cast<void**>(&reflection))) && reflection != nullptr)
    {
        D3D11_SHADER_DESC shader = {};
        if (SUCCEEDED(reflection->GetDesc(&shader)))
        {
            observation.metadata[2] = shader.InputParameters;
            observation.metadata[3] = shader.OutputParameters;
            observation.metadata[4] = shader.BoundResources;
            for (UINT index = 0; index < shader.BoundResources; ++index)
            {
                D3D11_SHADER_INPUT_BIND_DESC binding = {};
                if (FAILED(reflection->GetResourceBindingDesc(index, &binding)))
                    continue;
                if (binding.Type == D3D_SIT_CBUFFER &&
                    binding.BindPoint < 5u && binding.Name != nullptr)
                {
                    ID3D11ShaderReflectionConstantBuffer* buffer =
                        reflection->GetConstantBufferByName(binding.Name);
                    D3D11_SHADER_BUFFER_DESC description = {};
                    if (buffer != nullptr &&
                        SUCCEEDED(buffer->GetDesc(&description)))
                    {
                        observation.metadata[5u + binding.BindPoint] =
                            description.Size;
                    }
                }
                else if (binding.Type == D3D_SIT_TEXTURE &&
                    binding.BindPoint < 32u)
                {
                    observation.metadata[10] |= 1u << binding.BindPoint;
                }
                else if (binding.Type == D3D_SIT_SAMPLER &&
                    binding.BindPoint < 32u)
                {
                    observation.metadata[11] |= 1u << binding.BindPoint;
                }
            }
        }
        reflection->Release();
    }

    std::lock_guard<std::mutex> lock(g_m27CallbackObservationMutex);
    for (std::size_t index = 0; index < g_m27CallbackObservationCount; ++index)
    {
        if (std::memcmp(
                g_m27CallbackObservations[index].sha256,
                digest,
                sizeof(digest)) == 0)
        {
            return;
        }
    }
    if (g_m27CallbackObservationCount < kM27CallbackObservationCapacity)
        g_m27CallbackObservations[g_m27CallbackObservationCount++] = observation;
}

void RecordM27SignatureCounts(
    const unsigned char* byteCode,
    std::size_t byteCodeSize,
    bool isVertex)
{
    if (byteCode == nullptr || byteCodeSize == 0)
        return;

    ID3D11ShaderReflection* reflection = nullptr;
    const HRESULT reflected = D3DReflect(
        byteCode,
        byteCodeSize,
        IID_ID3D11ShaderReflection,
        reinterpret_cast<void**>(&reflection));
    if (FAILED(reflected) || reflection == nullptr)
        return;

    D3D11_SHADER_DESC description = {};
    if (SUCCEEDED(reflection->GetDesc(&description)))
    {
        std::atomic<std::uint32_t>& maxInputs = isVertex
            ? g_m27MaxVertexInputCount
            : g_m27MaxPixelInputCount;
        std::atomic<std::uint32_t>& maxOutputs = isVertex
            ? g_m27MaxVertexOutputCount
            : g_m27MaxPixelOutputCount;
        maxInputs.store(description.InputParameters, std::memory_order_relaxed);
        maxOutputs.store(description.OutputParameters, std::memory_order_relaxed);
    }

    reflection->Release();
}

IUnityGraphicsD3D11* GetD3D11()
{
    return g_unityInterfaces == nullptr
        ? nullptr
        : g_unityInterfaces->Get<IUnityGraphicsD3D11>();
}

void ResetDiagnosticState()
{
    g_vertexClaimed.store(false, std::memory_order_relaxed);
    g_pixelClaimed.store(false, std::memory_order_relaxed);
    g_callbackCount.store(0, std::memory_order_relaxed);
    g_unarmedCallbackCount.store(0, std::memory_order_relaxed);
    g_blockedCount.store(0, std::memory_order_relaxed);
    g_vertexSwapCount.store(0, std::memory_order_relaxed);
    g_pixelSwapCount.store(0, std::memory_order_relaxed);
    g_failureCount.store(0, std::memory_order_relaxed);
    g_lastResult.store(S_OK, std::memory_order_relaxed);
    g_lastVertexShader.store(nullptr, std::memory_order_relaxed);
    g_lastPixelShader.store(nullptr, std::memory_order_relaxed);
    g_renderEventCount.store(0, std::memory_order_relaxed);
    g_exactShaderBound.store(0, std::memory_order_relaxed);
    g_constantBufferMask.store(0, std::memory_order_relaxed);
    g_shaderResourceMask.store(0, std::memory_order_relaxed);
    g_shaderResourceFailureMask.store(0, std::memory_order_relaxed);
    std::memset(g_shaderResourceFailureResults, 0, sizeof(g_shaderResourceFailureResults));
    g_postDrawShaderResourceMask.store(0, std::memory_order_relaxed);
    g_samplerMask.store(0, std::memory_order_relaxed);
    std::memset(g_texturePointers, 0, sizeof(g_texturePointers));
    g_texturePointerCount.store(0, std::memory_order_relaxed);
    g_m27MatchCount.store(0, std::memory_order_relaxed);
    g_m27MismatchCount.store(0, std::memory_order_relaxed);
    g_m27VariantHashConflictCount.store(0, std::memory_order_relaxed);
    g_m27MaxVertexInputCount.store(0, std::memory_order_relaxed);
    g_m27MaxVertexOutputCount.store(0, std::memory_order_relaxed);
    g_m27MaxPixelInputCount.store(0, std::memory_order_relaxed);
    g_m27MaxPixelOutputCount.store(0, std::memory_order_relaxed);
    for (std::size_t index = 0; index < 32; ++index)
    {
        g_m27ObservedVertexSha256[index].store(0, std::memory_order_relaxed);
        g_m27ObservedPixelSha256[index].store(0, std::memory_order_relaxed);
    }
    {
        std::lock_guard<std::mutex> lock(g_m27CallbackObservationMutex);
        std::memset(g_m27CallbackObservations, 0, sizeof(g_m27CallbackObservations));
        g_m27CallbackObservationCount = 0;
    }
}

void ReplaceD3D11Shader(UnityShaderCompilerExtCustomBinaryVariantParams& params)
{
    if (params.platform != kUnityShaderCompilerExtCompPlatformD3D11 ||
        params.outputBinaryShader == nullptr)
    {
        return;
    }

    const bool isVertex =
        (params.programTypeMask & kUnityShaderCompilerExtGPUProgramVS) != 0;
    const bool isPixel =
        (params.programTypeMask & kUnityShaderCompilerExtGPUProgramPS) != 0;
    if (isVertex == isPixel)
        return;

    g_callbackCount.fetch_add(1, std::memory_order_relaxed);
    if (!g_armed.load(std::memory_order_acquire))
    {
        g_unarmedCallbackCount.fetch_add(1, std::memory_order_relaxed);
        return;
    }

    const SubstitutionRoute route =
        g_substitutionRoute.load(std::memory_order_acquire);
    const unsigned char* replacementDxbc = nullptr;
    std::size_t replacementDxbcSize = 0;
    if (route == SubstitutionRoute::M27HashPinned)
    {
        ObserveM27Callback(
            params.inputByteCode,
            params.inputByteCodeSize,
            isVertex);
        unsigned char digest[32] = {};
        if (!Sha256(params.inputByteCode, params.inputByteCodeSize, digest))
        {
            g_lastResult.store(E_INVALIDARG, std::memory_order_relaxed);
            g_failureCount.fetch_add(1, std::memory_order_relaxed);
            return;
        }
        const auto stage = isVertex
            ? EndfieldM27Substitution::Stage::Vertex
            : EndfieldM27Substitution::Stage::Pixel;
        const EndfieldM27Substitution::Entry* entry =
            EndfieldM27Substitution::Resolve(stage, digest);
        if (entry == nullptr)
        {
            // A callback keyword is not shader identity. Unknown bytecode must
            // retain Unity's shader object unchanged; only a stage+SHA registry
            // hit may substitute the retail M27 stage.
            g_blockedCount.fetch_add(1, std::memory_order_relaxed);
            return;
        }
        std::atomic<std::uint8_t>* observed =
            isVertex ? g_m27ObservedVertexSha256 : g_m27ObservedPixelSha256;
        for (std::size_t index = 0; index < sizeof(digest); ++index)
            observed[index].store(digest[index], std::memory_order_release);
        RecordM27SignatureCounts(
            params.inputByteCode,
            params.inputByteCodeSize,
            isVertex);
        replacementDxbc = entry->replacementDxbc;
        replacementDxbcSize = entry->replacementDxbcSize;
        g_m27MatchCount.fetch_add(1, std::memory_order_relaxed);
    }
    else if (route == SubstitutionRoute::DeferredDiagnostic)
    {
        // Preserve the existing isolated deferred diagnostic callback. Its
        // production proof uses the native fullscreen event and does not share
        // the M27 shell route.
        replacementDxbc = isVertex
            ? g_EndfieldSelectedVertexDxbc
            : g_EndfieldSelectedPixelDxbc;
        replacementDxbcSize = isVertex
            ? g_EndfieldSelectedVertexDxbcSize
            : g_EndfieldSelectedPixelDxbcSize;
    }
    else
    {
        g_blockedCount.fetch_add(1, std::memory_order_relaxed);
        return;
    }

    std::atomic<bool>& stageClaim = isVertex ? g_vertexClaimed : g_pixelClaimed;
    stageClaim.store(true, std::memory_order_relaxed);

    IUnityGraphicsD3D11* unityD3D11 = GetD3D11();
    ID3D11Device* device = unityD3D11 == nullptr ? nullptr : unityD3D11->GetDevice();
    if (device == nullptr)
    {
        g_lastResult.store(E_POINTER, std::memory_order_relaxed);
        g_failureCount.fetch_add(1, std::memory_order_relaxed);
        return;
    }

    IUnknown* replacement = nullptr;
    HRESULT result = E_INVALIDARG;
    if (isVertex)
    {
        ID3D11VertexShader* shader = nullptr;
        result = device->CreateVertexShader(
            replacementDxbc,
            replacementDxbcSize,
            nullptr,
            &shader);
        replacement = shader;
    }
    else
    {
        ID3D11PixelShader* shader = nullptr;
        result = device->CreatePixelShader(
            replacementDxbc,
            replacementDxbcSize,
            nullptr,
            &shader);
        replacement = shader;
    }

    g_lastResult.store(result, std::memory_order_relaxed);
    if (FAILED(result) || replacement == nullptr)
    {
        if (replacement != nullptr)
            replacement->Release();
        g_failureCount.fetch_add(1, std::memory_order_relaxed);
        return;
    }

    // Unity has already created its ordinary shader object. Replace it only
    // after exact-byte creation succeeds, then release the displaced reference.
    IUnknown* displaced = static_cast<IUnknown*>(*params.outputBinaryShader);
    *params.outputBinaryShader = replacement;
    if (displaced != nullptr)
        displaced->Release();

    if (isVertex)
    {
        g_lastVertexShader.store(replacement, std::memory_order_release);
        g_vertexSwapCount.fetch_add(1, std::memory_order_relaxed);
    }
    else
    {
        g_lastPixelShader.store(replacement, std::memory_order_release);
        g_pixelSwapCount.fetch_add(1, std::memory_order_relaxed);
    }
}

void ReleaseRuntimeShaders()
{
    if (g_runtimePixelShader != nullptr)
    {
        g_runtimePixelShader->Release();
        g_runtimePixelShader = nullptr;
    }
    if (g_runtimeVertexShader != nullptr)
    {
        g_runtimeVertexShader->Release();
        g_runtimeVertexShader = nullptr;
    }
}

template <typename T>
void ReleaseM14Object(T*& value)
{
    if (value != nullptr)
    {
        value->Release();
        value = nullptr;
    }
}

void ReleaseM14RuntimeResources()
{
    ReleaseM14Object(g_m14RasterizerState);
    ReleaseM14Object(g_m14DepthState);
    ReleaseM14Object(g_m14BlendState);
    for (ID3D11SamplerState*& sampler : g_m14Samplers)
        ReleaseM14Object(sampler);
    ReleaseM14Object(g_m14SkinView);
    ReleaseM14Object(g_m14SkinBuffer);
    for (ID3D11Buffer*& buffer : g_m14PixelConstantBuffers)
        ReleaseM14Object(buffer);
    for (ID3D11Buffer*& buffer : g_m14VertexConstantBuffers)
        ReleaseM14Object(buffer);
    ReleaseM14Object(g_m14IndexBuffer);
    ReleaseM14Object(g_m14DefaultVertexBuffer);
    ReleaseM14Object(g_m14VertexBuffer);
    ReleaseM14Object(g_m14InputLayout);
    ReleaseM14Object(g_m14RuntimePixelShader);
    ReleaseM14Object(g_m14RuntimeVertexShader);
}

HRESULT CreateM14ImmutableBuffer(
    ID3D11Device* device,
    UINT bindFlags,
    const void* data,
    UINT byteWidth,
    ID3D11Buffer** output,
    UINT miscFlags = 0,
    UINT structureStride = 0)
{
    if (device == nullptr || data == nullptr || output == nullptr || byteWidth == 0)
        return E_INVALIDARG;
    D3D11_BUFFER_DESC description = {};
    description.ByteWidth = byteWidth;
    description.Usage = D3D11_USAGE_IMMUTABLE;
    description.BindFlags = bindFlags;
    description.MiscFlags = miscFlags;
    description.StructureByteStride = structureStride;
    D3D11_SUBRESOURCE_DATA initial = {};
    initial.pSysMem = data;
    return device->CreateBuffer(&description, &initial, output);
}

HRESULT CreateM14ConstantBuffer(
    ID3D11Device* device,
    std::uint32_t declaredFloat4Count,
    const std::uint8_t* captured,
    std::size_t capturedBytes,
    ID3D11Buffer** output)
{
    if (declaredFloat4Count == 0 || declaredFloat4Count > 4096 ||
        captured == nullptr || capturedBytes > declaredFloat4Count * 16u)
        return E_INVALIDARG;
    const UINT byteWidth = declaredFloat4Count * 16u;
    unsigned char* payload = new (std::nothrow) unsigned char[byteWidth]();
    if (payload == nullptr)
        return E_OUTOFMEMORY;
    std::memcpy(payload, captured, capturedBytes);
    const HRESULT result = CreateM14ImmutableBuffer(
        device,
        D3D11_BIND_CONSTANT_BUFFER,
        payload,
        byteWidth,
        output);
    delete[] payload;
    return result;
}

HRESULT CreateM14RuntimeResources(ID3D11Device* device)
{
    if (device == nullptr)
        return E_POINTER;
    if (g_m14RuntimeVertexShader != nullptr &&
        g_m14RuntimePixelShader != nullptr)
        return S_OK;

    ReleaseM14RuntimeResources();
    HRESULT result = device->CreateVertexShader(
        g_EndfieldM14VertexDxbc,
        g_EndfieldM14VertexDxbcSize,
        nullptr,
        &g_m14RuntimeVertexShader);
    if (FAILED(result))
        return result;
    result = device->CreatePixelShader(
        g_EndfieldM14PixelDxbc,
        g_EndfieldM14PixelDxbcSize,
        nullptr,
        &g_m14RuntimePixelShader);
    if (FAILED(result))
        return result;

    const D3D11_INPUT_ELEMENT_DESC elements[] = {
        {"POSITION", 0, DXGI_FORMAT_R32G32B32_FLOAT, 0, 0,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"COLOR", 0, DXGI_FORMAT_R8G8B8A8_UNORM, 0, 24,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 0, DXGI_FORMAT_R32G32_FLOAT, 0, 28,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 1, DXGI_FORMAT_R32G32_FLOAT, 0, 28,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 4, DXGI_FORMAT_R32G32_FLOAT, 0, 28,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"BLENDWEIGHTS", 0, DXGI_FORMAT_R8G8B8A8_UNORM, 1, 16,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"BLENDINDICES", 0, DXGI_FORMAT_R8G8B8A8_UINT, 1, 0,
            D3D11_INPUT_PER_VERTEX_DATA, 0},
    };
    result = device->CreateInputLayout(
        elements,
        static_cast<UINT>(sizeof(elements) / sizeof(elements[0])),
        g_EndfieldM14VertexDxbc,
        g_EndfieldM14VertexDxbcSize,
        &g_m14InputLayout);
    if (FAILED(result))
        return result;
    // Retail's shared default-channel buffer is 20 bytes and is submitted
    // with stride zero. The exact 48fadbbd layout reads only the zero bone
    // indices at +0 and zero normalized weights at +16 from this row.
    const unsigned char defaultVertex[20] = {};
    result = CreateM14ImmutableBuffer(
        device,
        D3D11_BIND_VERTEX_BUFFER,
        defaultVertex,
        sizeof(defaultVertex),
        &g_m14DefaultVertexBuffer);
    if (FAILED(result))
        return result;
    result = CreateM14ImmutableBuffer(
        device,
        D3D11_BIND_VERTEX_BUFFER,
        g_EndfieldM14Vertices,
        static_cast<UINT>(g_EndfieldM14VerticesSize),
        &g_m14VertexBuffer);
    if (FAILED(result))
        return result;
    result = CreateM14ImmutableBuffer(
        device,
        D3D11_BIND_INDEX_BUFFER,
        g_EndfieldM14Indices,
        static_cast<UINT>(g_EndfieldM14IndicesSize),
        &g_m14IndexBuffer);
    if (FAILED(result))
        return result;

    const std::uint8_t* vsPayloads[] = {
        g_EndfieldM14VSCB0, g_EndfieldM14VSCB1, g_EndfieldM14VSCB2,
        g_EndfieldM14VSCB3, g_EndfieldM14VSCB4,
    };
    const std::size_t vsPayloadSizes[] = {
        g_EndfieldM14VSCB0Size, g_EndfieldM14VSCB1Size,
        g_EndfieldM14VSCB2Size, g_EndfieldM14VSCB3Size,
        g_EndfieldM14VSCB4Size,
    };
    for (std::size_t slot = 0; slot < 5; ++slot)
    {
        result = CreateM14ConstantBuffer(
            device,
            g_EndfieldM14VSDeclaredFloat4Counts[slot],
            vsPayloads[slot],
            vsPayloadSizes[slot],
            &g_m14VertexConstantBuffers[slot]);
        if (FAILED(result))
            return result;
    }
    const std::uint8_t* psPayloads[] = {
        g_EndfieldM14PSCB0, g_EndfieldM14PSCB1,
        g_EndfieldM14PSCB2, g_EndfieldM14PSCB3,
    };
    const std::size_t psPayloadSizes[] = {
        g_EndfieldM14PSCB0Size, g_EndfieldM14PSCB1Size,
        g_EndfieldM14PSCB2Size, g_EndfieldM14PSCB3Size,
    };
    for (std::size_t slot = 0; slot < 4; ++slot)
    {
        result = CreateM14ConstantBuffer(
            device,
            g_EndfieldM14PSDeclaredFloat4Counts[slot],
            psPayloads[slot],
            psPayloadSizes[slot],
            &g_m14PixelConstantBuffers[slot]);
        if (FAILED(result))
            return result;
    }

    const float zeroSkin[4] = {};
    result = CreateM14ImmutableBuffer(
        device,
        D3D11_BIND_SHADER_RESOURCE,
        zeroSkin,
        sizeof(zeroSkin),
        &g_m14SkinBuffer,
        D3D11_RESOURCE_MISC_BUFFER_STRUCTURED,
        sizeof(zeroSkin));
    if (FAILED(result))
        return result;
    result = device->CreateShaderResourceView(
        g_m14SkinBuffer, nullptr, &g_m14SkinView);
    if (FAILED(result))
        return result;

    D3D11_SAMPLER_DESC sampler = {};
    sampler.Filter = D3D11_FILTER_MIN_MAG_MIP_LINEAR;
    sampler.AddressU = D3D11_TEXTURE_ADDRESS_CLAMP;
    sampler.AddressV = D3D11_TEXTURE_ADDRESS_CLAMP;
    sampler.AddressW = D3D11_TEXTURE_ADDRESS_CLAMP;
    sampler.MaxLOD = D3D11_FLOAT32_MAX;
    result = device->CreateSamplerState(&sampler, &g_m14Samplers[0]);
    if (FAILED(result))
        return result;
    sampler.AddressU = D3D11_TEXTURE_ADDRESS_WRAP;
    sampler.AddressV = D3D11_TEXTURE_ADDRESS_WRAP;
    result = device->CreateSamplerState(&sampler, &g_m14Samplers[1]);
    if (FAILED(result))
        return result;

    D3D11_BLEND_DESC blend = {};
    blend.IndependentBlendEnable = TRUE;
    for (std::size_t target = 0; target < 2; ++target)
    {
        blend.RenderTarget[target].BlendEnable = TRUE;
        blend.RenderTarget[target].SrcBlend = D3D11_BLEND_ONE;
        blend.RenderTarget[target].DestBlend = D3D11_BLEND_INV_SRC_ALPHA;
        blend.RenderTarget[target].BlendOp = D3D11_BLEND_OP_ADD;
        blend.RenderTarget[target].SrcBlendAlpha = D3D11_BLEND_ONE;
        blend.RenderTarget[target].DestBlendAlpha = D3D11_BLEND_INV_SRC_ALPHA;
        blend.RenderTarget[target].BlendOpAlpha = D3D11_BLEND_OP_ADD;
        blend.RenderTarget[target].RenderTargetWriteMask =
            D3D11_COLOR_WRITE_ENABLE_ALL;
    }
    result = device->CreateBlendState(&blend, &g_m14BlendState);
    if (FAILED(result))
        return result;

    D3D11_DEPTH_STENCIL_DESC depth = {};
    depth.DepthEnable = FALSE;
    depth.DepthWriteMask = D3D11_DEPTH_WRITE_MASK_ZERO;
    depth.DepthFunc = D3D11_COMPARISON_ALWAYS;
    result = device->CreateDepthStencilState(&depth, &g_m14DepthState);
    if (FAILED(result))
        return result;
    D3D11_RASTERIZER_DESC rasterizer = {};
    rasterizer.FillMode = D3D11_FILL_SOLID;
    rasterizer.CullMode = D3D11_CULL_NONE;
    rasterizer.DepthClipEnable = TRUE;
    result = device->CreateRasterizerState(&rasterizer, &g_m14RasterizerState);
    return result;
}

DXGI_FORMAT ShaderResourceFormat(DXGI_FORMAT format)
{
    switch (format)
    {
        case DXGI_FORMAT_R8_TYPELESS:
            return DXGI_FORMAT_R8_UNORM;
        case DXGI_FORMAT_R8G8_TYPELESS:
            return DXGI_FORMAT_R8G8_UNORM;
        case DXGI_FORMAT_R8G8B8A8_TYPELESS:
            return DXGI_FORMAT_R8G8B8A8_UNORM;
        case DXGI_FORMAT_B8G8R8A8_TYPELESS:
            return DXGI_FORMAT_B8G8R8A8_UNORM;
        case DXGI_FORMAT_R16_TYPELESS:
            return DXGI_FORMAT_R16_UNORM;
        case DXGI_FORMAT_R16G16_TYPELESS:
            return DXGI_FORMAT_R16G16_UNORM;
        case DXGI_FORMAT_R16G16B16A16_TYPELESS:
            return DXGI_FORMAT_R16G16B16A16_FLOAT;
        case DXGI_FORMAT_R10G10B10A2_TYPELESS:
            return DXGI_FORMAT_R10G10B10A2_UNORM;
        case DXGI_FORMAT_R32G32_TYPELESS:
            return DXGI_FORMAT_R32G32_FLOAT;
        case DXGI_FORMAT_R32G32B32A32_TYPELESS:
            return DXGI_FORMAT_R32G32B32A32_FLOAT;
        case DXGI_FORMAT_D16_UNORM:
            return DXGI_FORMAT_R16_UNORM;
        case DXGI_FORMAT_D24_UNORM_S8_UINT:
            return DXGI_FORMAT_R24_UNORM_X8_TYPELESS;
        case DXGI_FORMAT_D32_FLOAT:
            return DXGI_FORMAT_R32_FLOAT;
        case DXGI_FORMAT_D32_FLOAT_S8X24_UINT:
            return DXGI_FORMAT_R32_FLOAT_X8X24_TYPELESS;
        case DXGI_FORMAT_R32_TYPELESS:
            return DXGI_FORMAT_R32_FLOAT;
        case DXGI_FORMAT_R24G8_TYPELESS:
            return DXGI_FORMAT_R24_UNORM_X8_TYPELESS;
        case DXGI_FORMAT_R32G8X24_TYPELESS:
            return DXGI_FORMAT_R32_FLOAT_X8X24_TYPELESS;
        default:
            return format;
    }
}

HRESULT CreateDiagnosticShaderResourceView(
    ID3D11Device* device,
    ID3D11Resource* resource,
    ID3D11ShaderResourceView** view)
{
    if (device == nullptr || resource == nullptr || view == nullptr)
        return E_POINTER;
    *view = nullptr;

    HRESULT result = device->CreateShaderResourceView(resource, nullptr, view);
    if (SUCCEEDED(result) && *view != nullptr)
        return result;

    D3D11_RESOURCE_DIMENSION dimension = D3D11_RESOURCE_DIMENSION_UNKNOWN;
    resource->GetType(&dimension);
    D3D11_SHADER_RESOURCE_VIEW_DESC description = {};
    if (dimension == D3D11_RESOURCE_DIMENSION_BUFFER)
    {
        ID3D11Buffer* buffer = nullptr;
        result = resource->QueryInterface(
            __uuidof(ID3D11Buffer),
            reinterpret_cast<void**>(&buffer));
        if (FAILED(result) || buffer == nullptr)
            return result;
        D3D11_BUFFER_DESC bufferDescription = {};
        buffer->GetDesc(&bufferDescription);
        buffer->Release();
        if (bufferDescription.StructureByteStride == 0)
        {
            // Raw ComputeBuffer resources are exposed as a typeless 32-bit
            // buffer SRV with the RAW flag, not as a structured SRV.
            description.Format = DXGI_FORMAT_R32_TYPELESS;
            description.ViewDimension = D3D11_SRV_DIMENSION_BUFFEREX;
            description.BufferEx.FirstElement = 0;
            description.BufferEx.NumElements =
                bufferDescription.ByteWidth / sizeof(std::uint32_t);
            description.BufferEx.Flags = D3D11_BUFFEREX_SRV_FLAG_RAW;
            return device->CreateShaderResourceView(resource, &description, view);
        }
        description.Format = DXGI_FORMAT_UNKNOWN;
        description.ViewDimension = D3D11_SRV_DIMENSION_BUFFER;
        description.Buffer.FirstElement = 0;
        description.Buffer.NumElements =
            bufferDescription.ByteWidth / bufferDescription.StructureByteStride;
        return device->CreateShaderResourceView(resource, &description, view);
    }

    if (dimension == D3D11_RESOURCE_DIMENSION_TEXTURE2D)
    {
        ID3D11Texture2D* texture = nullptr;
        result = resource->QueryInterface(
            __uuidof(ID3D11Texture2D),
            reinterpret_cast<void**>(&texture));
        if (FAILED(result) || texture == nullptr)
            return result;
        D3D11_TEXTURE2D_DESC textureDescription = {};
        texture->GetDesc(&textureDescription);
        texture->Release();
        description.Format = ShaderResourceFormat(textureDescription.Format);
        if (textureDescription.SampleDesc.Count > 1)
        {
            description.ViewDimension = textureDescription.ArraySize > 1
                ? D3D11_SRV_DIMENSION_TEXTURE2DMSARRAY
                : D3D11_SRV_DIMENSION_TEXTURE2DMS;
            if (description.ViewDimension == D3D11_SRV_DIMENSION_TEXTURE2DMSARRAY)
            {
                description.Texture2DMSArray.FirstArraySlice = 0;
                description.Texture2DMSArray.ArraySize = textureDescription.ArraySize;
            }
        }
        else if (textureDescription.ArraySize > 1)
        {
            description.ViewDimension = D3D11_SRV_DIMENSION_TEXTURE2DARRAY;
            description.Texture2DArray.MostDetailedMip = 0;
            description.Texture2DArray.MipLevels = textureDescription.MipLevels;
            description.Texture2DArray.FirstArraySlice = 0;
            description.Texture2DArray.ArraySize = textureDescription.ArraySize;
        }
        else
        {
            description.ViewDimension = D3D11_SRV_DIMENSION_TEXTURE2D;
            description.Texture2D.MostDetailedMip = 0;
            description.Texture2D.MipLevels = textureDescription.MipLevels;
        }
        return device->CreateShaderResourceView(resource, &description, view);
    }

    if (dimension == D3D11_RESOURCE_DIMENSION_TEXTURE3D)
    {
        ID3D11Texture3D* texture = nullptr;
        result = resource->QueryInterface(
            __uuidof(ID3D11Texture3D),
            reinterpret_cast<void**>(&texture));
        if (FAILED(result) || texture == nullptr)
            return result;
        D3D11_TEXTURE3D_DESC textureDescription = {};
        texture->GetDesc(&textureDescription);
        texture->Release();
        description.Format = ShaderResourceFormat(textureDescription.Format);
        description.ViewDimension = D3D11_SRV_DIMENSION_TEXTURE3D;
        description.Texture3D.MostDetailedMip = 0;
        description.Texture3D.MipLevels = textureDescription.MipLevels;
        return device->CreateShaderResourceView(resource, &description, view);
    }
    return result;
}

void DrawExactRuntimeShader()
{
    if (!g_armed.load(std::memory_order_acquire) ||
        g_substitutionRoute.load(std::memory_order_acquire) !=
            SubstitutionRoute::DeferredDiagnostic)
        return;

    IUnityGraphicsD3D11* unityD3D11 = GetD3D11();
    ID3D11Device* device = unityD3D11 == nullptr ? nullptr : unityD3D11->GetDevice();
    if (device == nullptr)
    {
        g_failureCount.fetch_add(1, std::memory_order_relaxed);
        g_lastResult.store(E_POINTER, std::memory_order_relaxed);
        return;
    }

    if (g_runtimeVertexShader == nullptr || g_runtimePixelShader == nullptr)
    {
        ReleaseRuntimeShaders();
        HRESULT vertexResult = device->CreateVertexShader(
            g_EndfieldSelectedVertexDxbc,
            g_EndfieldSelectedVertexDxbcSize,
            nullptr,
            &g_runtimeVertexShader);
        HRESULT pixelResult = device->CreatePixelShader(
            g_EndfieldSelectedPixelDxbc,
            g_EndfieldSelectedPixelDxbcSize,
            nullptr,
            &g_runtimePixelShader);
        if (FAILED(vertexResult) || FAILED(pixelResult))
        {
            if (g_runtimeVertexShader != nullptr)
            {
                g_runtimeVertexShader->Release();
                g_runtimeVertexShader = nullptr;
            }
            if (g_runtimePixelShader != nullptr)
            {
                g_runtimePixelShader->Release();
                g_runtimePixelShader = nullptr;
            }
            g_failureCount.fetch_add(1, std::memory_order_relaxed);
            g_lastResult.store(
                FAILED(vertexResult) ? vertexResult : pixelResult,
                std::memory_order_relaxed);
            return;
        }
    }

    ID3D11DeviceContext* context = nullptr;
    device->GetImmediateContext(&context);
    if (context == nullptr)
    {
        g_failureCount.fetch_add(1, std::memory_order_relaxed);
        g_lastResult.store(E_POINTER, std::memory_order_relaxed);
        return;
    }

    // The command buffer has already established the render target, constant
    // buffers, SRVs, and samplers. Draw from this plugin event so Unity cannot
    // overwrite the exact stages with the shell material between installation
    // and the draw call.
    // Unity's shell draw has already created the authoritative SRVs for these
    // RenderTextures. Reuse those views first: a RenderTexture may be
    // render-target-only at the raw resource level even though Unity owns a
    // compatible internal SRV for the material binding. Recreating a view
    // from the ID3D11Resource would incorrectly turn that valid binding into
    // E_INVALIDARG for typed, array, and MRT formats.
    ID3D11ShaderResourceView* resources[kTextureSlotCount] = {};
    context->PSGetShaderResources(0, kTextureSlotCount, resources);
    std::uint32_t resourceMask = 0;
    const std::uint32_t textureCount =
        g_texturePointerCount.load(std::memory_order_acquire);
    for (std::uint32_t slot = 0;
         slot < textureCount && slot < kTextureSlotCount;
         ++slot)
    {
        if (resources[slot] != nullptr)
        {
            resourceMask |= 1u << slot;
            continue;
        }
        if (g_texturePointers[slot] == 0)
            continue;
        ID3D11Resource* resource = reinterpret_cast<ID3D11Resource*>(
            g_texturePointers[slot]);
        HRESULT result = CreateDiagnosticShaderResourceView(
            device,
            resource,
            &resources[slot]);
        if (SUCCEEDED(result) && resources[slot] != nullptr)
            resourceMask |= 1u << slot;
        else
        {
            g_shaderResourceFailureMask.fetch_or(
                1u << slot,
                std::memory_order_relaxed);
            g_shaderResourceFailureResults[slot] = result;
        }
    }
    context->PSSetShaderResources(0, kTextureSlotCount, resources);
    g_shaderResourceMask.store(resourceMask, std::memory_order_relaxed);
    context->IASetInputLayout(nullptr);
    context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    context->VSSetShader(g_runtimeVertexShader, nullptr, 0);
    context->PSSetShader(g_runtimePixelShader, nullptr, 0);
    context->Draw(3, 0);
    for (std::uint32_t slot = 0; slot < kTextureSlotCount; ++slot)
    {
        if (resources[slot] != nullptr)
        {
            resources[slot]->Release();
            resources[slot] = nullptr;
        }
    }

    ID3D11VertexShader* vertex = nullptr;
    ID3D11PixelShader* pixel = nullptr;
    context->VSGetShader(&vertex, nullptr, nullptr);
    context->PSGetShader(&pixel, nullptr, nullptr);
    const bool exact =
        vertex == g_runtimeVertexShader && pixel == g_runtimePixelShader;
    if (vertex != nullptr)
        vertex->Release();
    if (pixel != nullptr)
        pixel->Release();
    context->Release();

    g_lastResult.store(S_OK, std::memory_order_relaxed);
    g_exactShaderBound.store(exact ? 1u : 0u, std::memory_order_relaxed);
    g_renderEventCount.fetch_add(1, std::memory_order_relaxed);
}

void ArmDiagnosticOnRenderThread()
{
    if (g_armed.load(std::memory_order_acquire))
        return;
    std::uintptr_t pointers[kTextureSlotCount] = {};
    const std::uint32_t pointerCount =
        g_texturePointerCount.load(std::memory_order_acquire);
    std::memcpy(pointers, g_texturePointers, sizeof(pointers));
    ResetDiagnosticState();
    std::memcpy(g_texturePointers, pointers, sizeof(pointers));
    g_texturePointerCount.store(pointerCount, std::memory_order_release);
    g_armed.store(true, std::memory_order_release);
}

void UNITY_INTERFACE_API InspectPostDrawBindings(int eventId)
{
    if (eventId == 3)
    {
        // The Unity shell draw must execute while disarmed so its own SRVs
        // remain authoritative. Arm the exact native event only after that
        // draw has completed on the render thread.
        ArmDiagnosticOnRenderThread();
        return;
    }
    if (!g_armed.load(std::memory_order_acquire))
        return;

    if (eventId == 0)
    {
        DrawExactRuntimeShader();
        return;
    }
    if (eventId != 1)
    {
        if (eventId == 2)
        {
            // Event 2 is queued after the exact draw and its readback copy.
            // Clear the native resource-pointer lifetime only on the render
            // thread; clearing it from C# immediately after ExecuteCommandBuffer
            // can race a deferred SRP submission.
            std::memset(g_texturePointers, 0, sizeof(g_texturePointers));
            g_texturePointerCount.store(0, std::memory_order_release);
            g_armed.store(false, std::memory_order_release);
            ReleaseRuntimeShaders();
        }
        return;
    }

    IUnityGraphicsD3D11* unityD3D11 = GetD3D11();
    ID3D11Device* device = unityD3D11 == nullptr ? nullptr : unityD3D11->GetDevice();
    if (device == nullptr)
    {
        g_failureCount.fetch_add(1, std::memory_order_relaxed);
        g_lastResult.store(E_POINTER, std::memory_order_relaxed);
        return;
    }

    ID3D11DeviceContext* context = nullptr;
    device->GetImmediateContext(&context);
    if (context == nullptr)
    {
        g_failureCount.fetch_add(1, std::memory_order_relaxed);
        g_lastResult.store(E_POINTER, std::memory_order_relaxed);
        return;
    }

    ID3D11VertexShader* vertex = nullptr;
    ID3D11PixelShader* pixel = nullptr;
    context->VSGetShader(&vertex, nullptr, nullptr);
    context->PSGetShader(&pixel, nullptr, nullptr);
    void* expectedVertex =
        g_lastVertexShader.load(std::memory_order_acquire);
    void* expectedPixel =
        g_lastPixelShader.load(std::memory_order_acquire);
    const bool exact =
        expectedVertex != nullptr &&
        expectedPixel != nullptr &&
        vertex == reinterpret_cast<ID3D11VertexShader*>(expectedVertex) &&
        pixel == reinterpret_cast<ID3D11PixelShader*>(expectedPixel);

    ID3D11Buffer* constantBuffers[kConstantBufferSlotCount] = {};
    ID3D11ShaderResourceView* resources[kTextureSlotCount] = {};
    ID3D11SamplerState* samplers[5] = {};
    context->PSGetConstantBuffers(0, kConstantBufferSlotCount, constantBuffers);
    context->PSGetShaderResources(0, kTextureSlotCount, resources);
    context->PSGetSamplers(0, 5, samplers);

    std::uint32_t constantMask = 0;
    std::uint32_t resourceMask = 0;
    std::uint32_t samplerMask = 0;
    for (std::uint32_t index = 0; index < kConstantBufferSlotCount; ++index)
    {
        if (constantBuffers[index] != nullptr)
        {
            constantMask |= 1u << index;
            constantBuffers[index]->Release();
        }
    }
    for (std::uint32_t index = 0; index < kTextureSlotCount; ++index)
    {
        if (resources[index] != nullptr)
        {
            resourceMask |= 1u << index;
            resources[index]->Release();
        }
    }
    for (std::uint32_t index = 0; index < 5; ++index)
    {
        if (samplers[index] != nullptr)
        {
            samplerMask |= 1u << index;
            samplers[index]->Release();
        }
    }
    if (pixel != nullptr)
        pixel->Release();
    if (vertex != nullptr)
        vertex->Release();
    context->Release();

    if (g_exactShaderBound.load(std::memory_order_relaxed) == 0)
        g_exactShaderBound.store(exact ? 1u : 0u, std::memory_order_relaxed);
    g_constantBufferMask.store(constantMask, std::memory_order_relaxed);
    g_postDrawShaderResourceMask.store(resourceMask, std::memory_order_relaxed);
    g_samplerMask.store(samplerMask, std::memory_order_relaxed);
    g_renderEventCount.fetch_add(1, std::memory_order_relaxed);
}

void UNITY_INTERFACE_API DrawM14ExactRuntime(int eventId)
{
    if (eventId != 0)
        return;
    IUnityGraphicsD3D11* unityD3D11 = GetD3D11();
    ID3D11Device* device = unityD3D11 == nullptr ? nullptr : unityD3D11->GetDevice();
    if (device == nullptr)
    {
        g_m14FailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m14LastResult.store(E_POINTER, std::memory_order_relaxed);
        return;
    }
    HRESULT result = CreateM14RuntimeResources(device);
    if (FAILED(result))
    {
        ReleaseM14RuntimeResources();
        g_m14FailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m14LastResult.store(result, std::memory_order_relaxed);
        return;
    }

    ID3D11Resource* depthResource = reinterpret_cast<ID3D11Resource*>(
        g_m14DepthTexture.load(std::memory_order_acquire));
    ID3D11Resource* mainResource = reinterpret_cast<ID3D11Resource*>(
        g_m14MainTexture.load(std::memory_order_acquire));
    ID3D11ShaderResourceView* m14PixelViews[2] = {};
    result = CreateDiagnosticShaderResourceView(
        device, depthResource, &m14PixelViews[0]);
    if (SUCCEEDED(result))
        result = CreateDiagnosticShaderResourceView(
            device, mainResource, &m14PixelViews[1]);
    if (FAILED(result) || m14PixelViews[0] == nullptr ||
        m14PixelViews[1] == nullptr)
    {
        ReleaseM14Object(m14PixelViews[1]);
        ReleaseM14Object(m14PixelViews[0]);
        g_m14FailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m14LastResult.store(FAILED(result) ? result : E_POINTER,
                              std::memory_order_relaxed);
        return;
    }

    ID3D11DeviceContext* context = nullptr;
    device->GetImmediateContext(&context);
    if (context == nullptr)
    {
        ReleaseM14Object(m14PixelViews[1]);
        ReleaseM14Object(m14PixelViews[0]);
        g_m14FailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m14LastResult.store(E_POINTER, std::memory_order_relaxed);
        return;
    }

    ID3D11RenderTargetView* renderTargets[2] = {};
    ID3D11DepthStencilView* renderDepth = nullptr;
    context->OMGetRenderTargets(2, renderTargets, &renderDepth);
    if (renderTargets[0] == nullptr || renderTargets[1] == nullptr)
    {
        ReleaseM14Object(renderDepth);
        ReleaseM14Object(renderTargets[1]);
        ReleaseM14Object(renderTargets[0]);
        ReleaseM14Object(m14PixelViews[1]);
        ReleaseM14Object(m14PixelViews[0]);
        context->Release();
        g_m14FailureCount.fetch_add(1, std::memory_order_relaxed);
        g_m14LastResult.store(E_INVALIDARG, std::memory_order_relaxed);
        return;
    }

    ID3D11VertexShader* oldVertexShader = nullptr;
    ID3D11PixelShader* oldPixelShader = nullptr;
    ID3D11InputLayout* oldInputLayout = nullptr;
    ID3D11Buffer* oldVertexBuffers[2] = {};
    ID3D11Buffer* oldIndexBuffer = nullptr;
    ID3D11Buffer* oldVertexCBs[5] = {};
    ID3D11Buffer* oldPixelCBs[4] = {};
    ID3D11ShaderResourceView* oldVertexView = nullptr;
    ID3D11ShaderResourceView* oldPixelViews[2] = {};
    ID3D11SamplerState* oldSamplers[2] = {};
    ID3D11BlendState* oldBlendState = nullptr;
    ID3D11DepthStencilState* oldDepthState = nullptr;
    ID3D11RasterizerState* oldRasterizerState = nullptr;
    D3D11_PRIMITIVE_TOPOLOGY oldTopology = D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
    DXGI_FORMAT oldIndexFormat = DXGI_FORMAT_UNKNOWN;
    UINT oldVertexStrides[2] = {};
    UINT oldVertexOffsets[2] = {};
    UINT oldIndexOffset = 0;
    FLOAT oldBlendFactor[4] = {};
    UINT oldSampleMask = 0;
    UINT oldStencilReference = 0;

    context->VSGetShader(&oldVertexShader, nullptr, nullptr);
    context->PSGetShader(&oldPixelShader, nullptr, nullptr);
    context->IAGetInputLayout(&oldInputLayout);
    context->IAGetVertexBuffers(
        0, 2, oldVertexBuffers, oldVertexStrides, oldVertexOffsets);
    context->IAGetIndexBuffer(&oldIndexBuffer, &oldIndexFormat, &oldIndexOffset);
    context->IAGetPrimitiveTopology(&oldTopology);
    context->VSGetConstantBuffers(0, 5, oldVertexCBs);
    context->PSGetConstantBuffers(0, 4, oldPixelCBs);
    context->VSGetShaderResources(0, 1, &oldVertexView);
    context->PSGetShaderResources(0, 2, oldPixelViews);
    context->PSGetSamplers(0, 2, oldSamplers);
    context->OMGetBlendState(&oldBlendState, oldBlendFactor, &oldSampleMask);
    context->OMGetDepthStencilState(&oldDepthState, &oldStencilReference);
    context->RSGetState(&oldRasterizerState);

    ID3D11Buffer* vertexBuffers[2] = {
        g_m14VertexBuffer,
        g_m14DefaultVertexBuffer,
    };
    const UINT strides[2] = {g_EndfieldM14VertexStride, 0};
    const UINT offsets[2] = {};
    const FLOAT blendFactor[4] = {};
    context->IASetInputLayout(g_m14InputLayout);
    context->IASetVertexBuffers(0, 2, vertexBuffers, strides, offsets);
    context->IASetIndexBuffer(g_m14IndexBuffer, DXGI_FORMAT_R16_UINT, 0);
    context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    context->VSSetShader(g_m14RuntimeVertexShader, nullptr, 0);
    context->PSSetShader(g_m14RuntimePixelShader, nullptr, 0);
    context->VSSetConstantBuffers(0, 5, g_m14VertexConstantBuffers);
    context->PSSetConstantBuffers(0, 4, g_m14PixelConstantBuffers);
    context->VSSetShaderResources(0, 1, &g_m14SkinView);
    context->PSSetShaderResources(0, 2, m14PixelViews);
    context->PSSetSamplers(0, 2, g_m14Samplers);
    context->OMSetBlendState(g_m14BlendState, blendFactor, 0xffffffffu);
    context->OMSetDepthStencilState(g_m14DepthState, 0);
    context->RSSetState(g_m14RasterizerState);
    context->DrawIndexed(g_EndfieldM14IndexCount, 0, 0);

    ID3D11ShaderResourceView* nullVertexView = nullptr;
    ID3D11ShaderResourceView* nullPixelViews[2] = {};
    context->VSSetShaderResources(0, 1, &nullVertexView);
    context->PSSetShaderResources(0, 2, nullPixelViews);
    context->IASetInputLayout(oldInputLayout);
    context->IASetVertexBuffers(
        0, 2, oldVertexBuffers, oldVertexStrides, oldVertexOffsets);
    context->IASetIndexBuffer(oldIndexBuffer, oldIndexFormat, oldIndexOffset);
    context->IASetPrimitiveTopology(oldTopology);
    context->VSSetShader(oldVertexShader, nullptr, 0);
    context->PSSetShader(oldPixelShader, nullptr, 0);
    context->VSSetConstantBuffers(0, 5, oldVertexCBs);
    context->PSSetConstantBuffers(0, 4, oldPixelCBs);
    context->VSSetShaderResources(0, 1, &oldVertexView);
    context->PSSetShaderResources(0, 2, oldPixelViews);
    context->PSSetSamplers(0, 2, oldSamplers);
    context->OMSetBlendState(oldBlendState, oldBlendFactor, oldSampleMask);
    context->OMSetDepthStencilState(oldDepthState, oldStencilReference);
    context->RSSetState(oldRasterizerState);

    for (ID3D11SamplerState*& value : oldSamplers)
        ReleaseM14Object(value);
    for (ID3D11ShaderResourceView*& value : oldPixelViews)
        ReleaseM14Object(value);
    ReleaseM14Object(oldVertexView);
    for (ID3D11Buffer*& value : oldPixelCBs)
        ReleaseM14Object(value);
    for (ID3D11Buffer*& value : oldVertexCBs)
        ReleaseM14Object(value);
    ReleaseM14Object(oldRasterizerState);
    ReleaseM14Object(oldDepthState);
    ReleaseM14Object(oldBlendState);
    ReleaseM14Object(oldIndexBuffer);
    for (ID3D11Buffer*& value : oldVertexBuffers)
        ReleaseM14Object(value);
    ReleaseM14Object(oldInputLayout);
    ReleaseM14Object(oldPixelShader);
    ReleaseM14Object(oldVertexShader);
    ReleaseM14Object(renderDepth);
    ReleaseM14Object(renderTargets[1]);
    ReleaseM14Object(renderTargets[0]);
    ReleaseM14Object(m14PixelViews[1]);
    ReleaseM14Object(m14PixelViews[0]);
    context->Release();

    g_m14DrawCount.fetch_add(1, std::memory_order_relaxed);
    g_m14LastResult.store(S_OK, std::memory_order_relaxed);
}
} // namespace

extern "C" void UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
UnityPluginLoad(IUnityInterfaces* unityInterfaces)
{
    ReleaseRuntimeShaders();
    ReleaseM14RuntimeResources();
    g_unityInterfaces = unityInterfaces;
    g_pluginLoadCount.fetch_add(1, std::memory_order_relaxed);
    g_armed.store(false, std::memory_order_release);
    g_substitutionRoute.store(SubstitutionRoute::None, std::memory_order_release);
    ResetDiagnosticState();
}

extern "C" void UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API UnityPluginUnload()
{
    g_armed.store(false, std::memory_order_release);
    g_substitutionRoute.store(SubstitutionRoute::None, std::memory_order_release);
    ReleaseRuntimeShaders();
    ReleaseM14RuntimeResources();
    g_unityInterfaces = nullptr;
}

extern "C" void UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
UnityShaderCompilerExtEvent(UnityShaderCompilerExtEventType eventType, void* data)
{
    if (eventType == kUnityShaderCompilerExtEventPluginConfigure)
    {
        g_configureCount.fetch_add(1, std::memory_order_relaxed);
        auto* configure = static_cast<IUnityShaderCompilerExtPluginConfigure*>(data);
        if (configure == nullptr)
            return;

        configure->ReserveKeyword(kReservedKeyword);
        configure->ReserveKeyword(kM27ReservedKeyword);
        configure->SetGPUProgramCompilerMask(
            (1u << kUnityShaderCompilerExtGPUProgramTargetDX11VertexSM50) |
            (1u << kUnityShaderCompilerExtGPUProgramTargetDX11PixelSM50));
        configure->SetShaderProgramMask(
            kUnityShaderCompilerExtGPUProgramVS |
            kUnityShaderCompilerExtGPUProgramPS);
        return;
    }

    if (eventType == kUnityShaderCompilerExtEventCreateCustomBinaryVariant &&
        data != nullptr)
    {
        ReplaceD3D11Shader(
            *static_cast<UnityShaderCompilerExtCustomBinaryVariantParams*>(data));
    }
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetContractVersion()
{
    return kContractVersion;
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetPluginLoadCount()
{
    return g_pluginLoadCount.load(std::memory_order_relaxed);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetConfigureCount()
{
    return g_configureCount.load(std::memory_order_relaxed);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcSetDiagnosticArmed(std::uint32_t armed)
{
    if (armed != 0)
    {
        g_armed.store(false, std::memory_order_release);
        g_substitutionRoute.store(
            SubstitutionRoute::DeferredDiagnostic,
            std::memory_order_release);
        ReleaseRuntimeShaders();
        ResetDiagnosticState();
        g_armed.store(true, std::memory_order_release);
    }
    else
    {
        g_armed.store(false, std::memory_order_release);
        g_substitutionRoute.store(SubstitutionRoute::None, std::memory_order_release);
        ReleaseRuntimeShaders();
    }
    return g_armed.load(std::memory_order_acquire) ? 1u : 0u;
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcSetM27SubstitutionArmed(std::uint32_t armed)
{
    g_armed.store(false, std::memory_order_release);
    g_substitutionRoute.store(
        armed != 0
            ? SubstitutionRoute::M27HashPinned
            : SubstitutionRoute::None,
        std::memory_order_release);
    ReleaseRuntimeShaders();
    ResetDiagnosticState();
    if (armed != 0)
        g_armed.store(true, std::memory_order_release);
    return g_armed.load(std::memory_order_acquire) ? 1u : 0u;
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM27RegistryReady()
{
    return EndfieldM27Substitution::Ready() ? 1u : 0u;
}

extern "C" UnityRenderingEvent UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM14RenderEventFunc()
{
    return DrawM14ExactRuntime;
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcSetM14TextureResources(void* sceneDepth, void* mainTexture)
{
    g_m14DepthTexture.store(
        reinterpret_cast<std::uintptr_t>(sceneDepth),
        std::memory_order_release);
    g_m14MainTexture.store(
        reinterpret_cast<std::uintptr_t>(mainTexture),
        std::memory_order_release);
    return sceneDepth != nullptr && mainTexture != nullptr ? 1u : 0u;
}

extern "C" void UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcResetM14RuntimeState()
{
    g_m14DepthTexture.store(0, std::memory_order_release);
    g_m14MainTexture.store(0, std::memory_order_release);
    g_m14DrawCount.store(0, std::memory_order_relaxed);
    g_m14FailureCount.store(0, std::memory_order_relaxed);
    g_m14LastResult.store(S_OK, std::memory_order_relaxed);
    ReleaseM14RuntimeResources();
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM14DrawCount()
{
    return g_m14DrawCount.load(std::memory_order_relaxed);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM14FailureCount()
{
    return g_m14FailureCount.load(std::memory_order_relaxed);
}

extern "C" std::int32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM14LastResult()
{
    return static_cast<std::int32_t>(
        g_m14LastResult.load(std::memory_order_relaxed));
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM27MatchCount()
{
    return g_m27MatchCount.load(std::memory_order_relaxed);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM27MismatchCount()
{
    return g_m27MismatchCount.load(std::memory_order_relaxed);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM27VariantHashConflictCount()
{
    return g_m27VariantHashConflictCount.load(std::memory_order_relaxed);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM27MaximumSignatureCounts(std::uint32_t stage)
{
    if (stage == 1u)
        return (g_m27MaxVertexInputCount.load(std::memory_order_relaxed) << 16) |
            g_m27MaxVertexOutputCount.load(std::memory_order_relaxed);
    if (stage == 2u)
        return (g_m27MaxPixelInputCount.load(std::memory_order_relaxed) << 16) |
            g_m27MaxPixelOutputCount.load(std::memory_order_relaxed);
    return 0;
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM27ObservedShellSha256(
    std::uint32_t stage,
    unsigned char* output,
    std::uint32_t outputSize)
{
    if (output == nullptr || outputSize < 32)
        return 0;
    const std::atomic<std::uint8_t>* observed = nullptr;
    if (stage == static_cast<std::uint32_t>(EndfieldM27Substitution::Stage::Vertex))
        observed = g_m27ObservedVertexSha256;
    else if (stage == static_cast<std::uint32_t>(EndfieldM27Substitution::Stage::Pixel))
        observed = g_m27ObservedPixelSha256;
    else
        return 0;
    for (std::size_t index = 0; index < 32; ++index)
        output[index] = observed[index].load(std::memory_order_acquire);
    return 32;
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM27CallbackObservationCount()
{
    std::lock_guard<std::mutex> lock(g_m27CallbackObservationMutex);
    return static_cast<std::uint32_t>(g_m27CallbackObservationCount);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetM27CallbackObservation(
    std::uint32_t index,
    std::uint32_t* metadata,
    std::uint32_t metadataCount,
    unsigned char* sha256,
    std::uint32_t sha256Size)
{
    if (metadata == nullptr || metadataCount < kM27CallbackMetadataCount ||
        sha256 == nullptr || sha256Size < 32u)
    {
        return 0;
    }
    std::lock_guard<std::mutex> lock(g_m27CallbackObservationMutex);
    if (index >= g_m27CallbackObservationCount)
        return 0;
    const M27CallbackObservation& observation =
        g_m27CallbackObservations[index];
    std::memcpy(
        metadata,
        observation.metadata,
        sizeof(observation.metadata));
    std::memcpy(sha256, observation.sha256, sizeof(observation.sha256));
    return static_cast<std::uint32_t>(kM27CallbackMetadataCount);
}

extern "C" void UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcSetDiagnosticTexturePointers(
    const std::uint64_t* texturePointers,
    std::uint32_t count)
{
    std::memset(g_texturePointers, 0, sizeof(g_texturePointers));
    if (texturePointers != nullptr && count != 0)
    {
        if (count > kTextureSlotCount)
            count = kTextureSlotCount;
        std::memcpy(
            g_texturePointers,
            texturePointers,
            static_cast<std::size_t>(count) * sizeof(std::uint64_t));
    }
    std::atomic_thread_fence(std::memory_order_release);
    g_texturePointerCount.store(
        texturePointers == nullptr ? 0 : count,
        std::memory_order_release);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetDiagnosticArmed()
{
    return g_armed.load(std::memory_order_acquire) ? 1u : 0u;
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetCallbackCount()
{
    return g_callbackCount.load(std::memory_order_relaxed);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetUnarmedCallbackCount()
{
    return g_unarmedCallbackCount.load(std::memory_order_relaxed);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetBlockedCount()
{
    return g_blockedCount.load(std::memory_order_relaxed);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetVertexSwapCount()
{
    return g_vertexSwapCount.load(std::memory_order_relaxed);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetPixelSwapCount()
{
    return g_pixelSwapCount.load(std::memory_order_relaxed);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetFailureCount()
{
    return g_failureCount.load(std::memory_order_relaxed);
}

extern "C" std::int32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetLastResult()
{
    return static_cast<std::int32_t>(g_lastResult.load(std::memory_order_relaxed));
}

extern "C" UnityRenderingEvent UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetRenderEventFunc()
{
    return InspectPostDrawBindings;
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetRenderEventCount()
{
    return g_renderEventCount.load(std::memory_order_relaxed);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetExactShaderBound()
{
    return g_exactShaderBound.load(std::memory_order_relaxed);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetConstantBufferMask()
{
    return g_constantBufferMask.load(std::memory_order_relaxed);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetShaderResourceMask()
{
    return g_shaderResourceMask.load(std::memory_order_relaxed);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetShaderResourceFailureMask()
{
    return g_shaderResourceFailureMask.load(std::memory_order_relaxed);
}

extern "C" std::int32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetShaderResourceFailureResult(std::uint32_t slot)
{
    if (slot >= kTextureSlotCount)
        return static_cast<std::int32_t>(E_INVALIDARG);
    return static_cast<std::int32_t>(g_shaderResourceFailureResults[slot]);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetPostDrawShaderResourceMask()
{
    return g_postDrawShaderResourceMask.load(std::memory_order_relaxed);
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalDxbcGetSamplerMask()
{
    return g_samplerMask.load(std::memory_order_relaxed);
}
