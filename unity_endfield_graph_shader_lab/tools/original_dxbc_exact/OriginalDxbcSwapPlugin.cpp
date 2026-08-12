#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <d3d11.h>

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <cstring>

#include "IUnityInterface.h"
#include "IUnityGraphicsD3D11.h"
#include "IUnityShaderCompilerAccess.h"
#include "EmbeddedDxbc.generated.h"

namespace
{
constexpr const char* kReservedKeyword = "ENDFIELD_ORIGINAL_DXBC_EXACT";
constexpr std::uint32_t kContractVersion = 1;

IUnityInterfaces* g_unityInterfaces = nullptr;
std::atomic<bool> g_armed{false};
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
std::atomic<std::uint32_t> g_samplerMask{0};

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
    g_samplerMask.store(0, std::memory_order_relaxed);
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

    // Every callback for the reserved diagnostic keyword belongs to the
    // isolated shell's D3D11 variant set. Replace all of them: Unity may pick
    // a later local-keyword variant at player load rather than the first one
    // observed during the editor build. The stage-claim flags remain exposed
    // as historical counters, but no variant is blocked in this mode.
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
            g_EndfieldSelectedVertexDxbc,
            g_EndfieldSelectedVertexDxbcSize,
            nullptr,
            &shader);
        replacement = shader;
    }
    else
    {
        ID3D11PixelShader* shader = nullptr;
        result = device->CreatePixelShader(
            g_EndfieldSelectedPixelDxbc,
            g_EndfieldSelectedPixelDxbcSize,
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

void DrawExactRuntimeShader()
{
    if (!g_armed.load(std::memory_order_acquire))
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
    context->IASetInputLayout(nullptr);
    context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    context->VSSetShader(g_runtimeVertexShader, nullptr, 0);
    context->PSSetShader(g_runtimePixelShader, nullptr, 0);
    context->Draw(3, 0);

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

void UNITY_INTERFACE_API InspectPostDrawBindings(int eventId)
{
    if (!g_armed.load(std::memory_order_acquire))
        return;

    if (eventId == 0)
    {
        DrawExactRuntimeShader();
        return;
    }
    if (eventId != 1)
        return;

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

    ID3D11Buffer* constantBuffers[9] = {};
    ID3D11ShaderResourceView* resources[26] = {};
    ID3D11SamplerState* samplers[5] = {};
    context->PSGetConstantBuffers(0, 9, constantBuffers);
    context->PSGetShaderResources(0, 26, resources);
    context->PSGetSamplers(0, 5, samplers);

    std::uint32_t constantMask = 0;
    std::uint32_t resourceMask = 0;
    std::uint32_t samplerMask = 0;
    for (std::uint32_t index = 0; index < 9; ++index)
    {
        if (constantBuffers[index] != nullptr)
        {
            constantMask |= 1u << index;
            constantBuffers[index]->Release();
        }
    }
    for (std::uint32_t index = 0; index < 26; ++index)
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
    g_shaderResourceMask.store(resourceMask, std::memory_order_relaxed);
    g_samplerMask.store(samplerMask, std::memory_order_relaxed);
    g_renderEventCount.fetch_add(1, std::memory_order_relaxed);
}
} // namespace

extern "C" void UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
UnityPluginLoad(IUnityInterfaces* unityInterfaces)
{
    ReleaseRuntimeShaders();
    g_unityInterfaces = unityInterfaces;
    g_pluginLoadCount.fetch_add(1, std::memory_order_relaxed);
    g_armed.store(false, std::memory_order_release);
    ResetDiagnosticState();
}

extern "C" void UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API UnityPluginUnload()
{
    g_armed.store(false, std::memory_order_release);
    ReleaseRuntimeShaders();
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
        ReleaseRuntimeShaders();
        ResetDiagnosticState();
        g_armed.store(true, std::memory_order_release);
    }
    else
    {
        g_armed.store(false, std::memory_order_release);
        ReleaseRuntimeShaders();
    }
    return g_armed.load(std::memory_order_acquire) ? 1u : 0u;
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
EndfieldOriginalDxbcGetSamplerMask()
{
    return g_samplerMask.load(std::memory_order_relaxed);
}
