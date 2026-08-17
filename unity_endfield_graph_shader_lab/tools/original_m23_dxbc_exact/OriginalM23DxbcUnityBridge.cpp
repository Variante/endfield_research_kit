#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <d3d11.h>

#include <array>
#include <atomic>
#include <cstdint>
#include <cstring>
#include <mutex>

#include "IUnityInterface.h"
#include "IUnityGraphicsD3D11.h"
#include "IUnityShaderCompilerAccess.h"
#include "EmbeddedM23Dxbc.generated.h"
#include "M23DxbcValidation.h"

extern "C" HRESULT __cdecl EndfieldOriginalM23DxbcValidate(
    ID3D11Device* device, ID3D11DeviceContext* context,
    EndfieldM23DxbcValidation* report);
extern "C" HRESULT __cdecl EndfieldOriginalM23DxbcValidateExactTexturesHighNeutralRgbGateWithGrid(
    ID3D11Device* device, ID3D11DeviceContext* context,
    EndfieldM23DxbcValidation* report, float* outputFloats,
    std::uint32_t outputFloatCount);

// This file is deliberately separate from OriginalM23DxbcExactPlugin.cpp.
// The latter is the offline WARP fixture and its ABI/report must remain
// stable.  This translation unit only adds the opt-in Unity bridge.
namespace {

constexpr char kReservedKeyword[] = "ENDFIELD_ORIGINAL_M23_DXBC_EXACT";
constexpr std::uint32_t kContractVersion = 1u;
constexpr std::uint32_t kVisualModeControlledExact = 0u;
constexpr std::uint32_t kVisualModeExactTexturesHighNeutralRgb = 1u;
constexpr std::uint32_t kVisualGridSize = 16u;
constexpr std::uint32_t kVisualGridFloatCount = kVisualGridSize * kVisualGridSize * 4u;
// The recovered M23 VS declares cb3[14]. Observation is deliberately
// fail-closed: a different-sized slot is reported as unavailable rather than
// truncating or guessing at the draw-time payload.
constexpr std::uint32_t kRealDrawVsCb3ByteCount = 14u * 16u;
// Source hash, PNG decode, high-neutral domain, b2 gate, neutral reciprocal
// exposure, white COLOR0 input, and the causal RGB gate.
constexpr std::uint32_t kVisualConfigAllBits = 0x7fu;

IUnityInterfaces* g_unityInterfaces = nullptr;
std::atomic<bool> g_armed{false};
std::atomic<std::uint32_t> g_pluginLoadCount{0};
std::atomic<std::uint32_t> g_configureCount{0};
std::atomic<std::uint32_t> g_callbackCount{0};
std::atomic<std::uint32_t> g_unarmedCallbackCount{0};
std::atomic<std::uint32_t> g_platformBlockedCount{0};
std::atomic<std::uint32_t> g_shellInputObservedCount{0};
std::atomic<std::uint32_t> g_blockedCount{0};
std::atomic<std::uint32_t> g_vertexSwapCount{0};
std::atomic<std::uint32_t> g_pixelSwapCount{0};
std::atomic<std::uint32_t> g_failureCount{0};
std::atomic<std::int32_t> g_lastResult{S_OK};
std::atomic<std::uint32_t> g_renderEventCount{0};
std::atomic<std::uint32_t> g_ignoredRenderEventCount{0};
std::atomic<std::uint32_t> g_nativeExecutionCount{0};
std::atomic<std::uint32_t> g_nativeDrawIssued{0};
std::atomic<std::uint32_t> g_nativeReadbackFinite{0};
std::atomic<std::uint32_t> g_nativeReadbackChanged{0};
std::atomic<std::uint32_t> g_nativeReadbackChangedFromZero{0};
std::atomic<std::uint32_t> g_nativeOutputMask{0};
std::atomic<std::uint32_t> g_nativeStateCleared{0};
std::atomic<std::uint32_t> g_exactShaderBound{0};
std::atomic<std::uint32_t> g_vertexConstantBufferMask{0};
std::atomic<std::uint32_t> g_vertexShaderResourceMask{0};
std::atomic<std::uint32_t> g_pixelConstantBufferMask{0};
std::atomic<std::uint32_t> g_pixelShaderResourceMask{0};
std::atomic<std::uint32_t> g_pixelSamplerMask{0};
std::atomic<std::uint32_t> g_lastEventId{0};
std::atomic<std::uint32_t> g_cleanupCount{0};
std::atomic<bool> g_cleanupPending{false};
std::atomic<std::uint32_t> g_visualMode{kVisualModeControlledExact};
std::atomic<std::uint32_t> g_visualConfigMask{0};
std::atomic<std::uint32_t> g_visualGridSize{0};
std::atomic<std::uint32_t> g_visualGridFinitePixels{0};
std::atomic<std::uint32_t> g_visualGridNonzeroPixels{0};
std::atomic<std::uint32_t> g_visualGridRgbNonzeroPixels{0};
std::atomic<std::uint32_t> g_visualGridAlphaNonzeroPixels{0};
std::atomic<std::uint32_t> g_visualGridValid{0};

std::mutex g_shaderMutex;
std::mutex g_readbackMutex;
std::mutex g_realDrawMutex;
std::array<float, 4> g_nativeReadback{};
std::array<float, kVisualGridFloatCount> g_visualGrid{};

// Event IDs 4/5 are a non-destructive observation pair for a real Unity
// DrawMesh.  They never call the synthetic WARP fixture and never clear the
// D3D11 context.  The managed side can issue 4 immediately before DrawMesh
// and 5 immediately after it in one CommandBuffer.
struct RealDrawSnapshot {
    std::uint32_t captured = 0;
    std::uint32_t exactShaderBound = 0;
    std::uint32_t vertexShaderBound = 0;
    std::uint32_t pixelShaderBound = 0;
    std::uint32_t inputLayoutBound = 0;
    std::uint32_t vertexBufferBound = 0;
    std::uint32_t vertexBufferMask = 0;
    std::uint32_t indexBufferBound = 0;
    std::uint32_t indexFormat = 0;
    std::uint32_t vertexStrides[8] = {};
    std::uint32_t vertexOffsets[8] = {};
    std::uint32_t vertexConstantBufferMask = 0;
    std::uint32_t vertexShaderResourceMask = 0;
    std::uint32_t pixelConstantBufferMask = 0;
    std::uint32_t pixelShaderResourceMask = 0;
    std::uint32_t pixelSamplerMask = 0;
    std::uint32_t renderTargetBound = 0;
    std::uint32_t topology = 0;
    std::uint32_t viewport = 0;
    std::uint32_t vertexStride = 0;
    std::uint32_t vertexOffset = 0;
    std::uint32_t vertexCb3ByteWidth = 0;
    std::uint32_t vertexCb3CaptureStatus = 0;
    std::array<std::uint8_t, kRealDrawVsCb3ByteCount> vertexCb3Bytes{};
    // Observer-owned guarantee only: event 4/5 never calls ClearState. This
    // does not claim that Unity preserves every binding across DrawMesh.
    std::uint32_t observerDidNotClearState = 1;
};
RealDrawSnapshot g_realDrawBefore;
RealDrawSnapshot g_realDrawAfter;
std::uint32_t g_realDrawBeforeCount = 0;
std::uint32_t g_realDrawAfterCount = 0;
ID3D11VertexShader* g_lastVertexShader = nullptr;
ID3D11PixelShader* g_lastPixelShader = nullptr;
bool g_vertexClaimed = false;
bool g_pixelClaimed = false;

IUnityGraphicsD3D11* GetD3D11()
{
    return g_unityInterfaces == nullptr
        ? nullptr
        : g_unityInterfaces->Get<IUnityGraphicsD3D11>();
}

void ReleaseShaderReferences()
{
    std::lock_guard<std::mutex> lock(g_shaderMutex);
    if (g_lastVertexShader != nullptr) {
        g_lastVertexShader->Release();
        g_lastVertexShader = nullptr;
    }
    if (g_lastPixelShader != nullptr) {
        g_lastPixelShader->Release();
        g_lastPixelShader = nullptr;
    }
    g_vertexClaimed = false;
    g_pixelClaimed = false;
}

void ResetArmedState()
{
    ReleaseShaderReferences();
    g_callbackCount.store(0, std::memory_order_relaxed);
    g_unarmedCallbackCount.store(0, std::memory_order_relaxed);
    g_platformBlockedCount.store(0, std::memory_order_relaxed);
    g_shellInputObservedCount.store(0, std::memory_order_relaxed);
    g_blockedCount.store(0, std::memory_order_relaxed);
    g_vertexSwapCount.store(0, std::memory_order_relaxed);
    g_pixelSwapCount.store(0, std::memory_order_relaxed);
    g_failureCount.store(0, std::memory_order_relaxed);
    g_lastResult.store(S_OK, std::memory_order_relaxed);
    g_renderEventCount.store(0, std::memory_order_relaxed);
    g_ignoredRenderEventCount.store(0, std::memory_order_relaxed);
    g_nativeExecutionCount.store(0, std::memory_order_relaxed);
    g_nativeDrawIssued.store(0, std::memory_order_relaxed);
    g_nativeReadbackFinite.store(0, std::memory_order_relaxed);
    g_nativeReadbackChanged.store(0, std::memory_order_relaxed);
    g_nativeReadbackChangedFromZero.store(0, std::memory_order_relaxed);
    g_nativeOutputMask.store(0, std::memory_order_relaxed);
    g_nativeStateCleared.store(0, std::memory_order_relaxed);
    {
        std::lock_guard<std::mutex> lock(g_readbackMutex);
        g_nativeReadback.fill(0.0f);
        g_visualGrid.fill(0.0f);
    }
    g_exactShaderBound.store(0, std::memory_order_relaxed);
    g_vertexConstantBufferMask.store(0, std::memory_order_relaxed);
    g_vertexShaderResourceMask.store(0, std::memory_order_relaxed);
    g_pixelConstantBufferMask.store(0, std::memory_order_relaxed);
    g_pixelShaderResourceMask.store(0, std::memory_order_relaxed);
    g_pixelSamplerMask.store(0, std::memory_order_relaxed);
    g_lastEventId.store(0, std::memory_order_relaxed);
    g_cleanupCount.store(0, std::memory_order_relaxed);
    g_cleanupPending.store(false, std::memory_order_relaxed);
    g_visualConfigMask.store(0, std::memory_order_relaxed);
    g_visualGridSize.store(0, std::memory_order_relaxed);
    g_visualGridFinitePixels.store(0, std::memory_order_relaxed);
    g_visualGridNonzeroPixels.store(0, std::memory_order_relaxed);
    g_visualGridRgbNonzeroPixels.store(0, std::memory_order_relaxed);
    g_visualGridAlphaNonzeroPixels.store(0, std::memory_order_relaxed);
    g_visualGridValid.store(0, std::memory_order_relaxed);
    {
        std::lock_guard<std::mutex> lock(g_realDrawMutex);
        g_realDrawBefore = RealDrawSnapshot{};
        g_realDrawAfter = RealDrawSnapshot{};
        g_realDrawBeforeCount = 0;
        g_realDrawAfterCount = 0;
    }
}

void ReplaceD3D11Shader(
    UnityShaderCompilerExtCustomBinaryVariantParams& params)
{
    if (params.platform != kUnityShaderCompilerExtCompPlatformD3D11) {
        g_platformBlockedCount.fetch_add(1, std::memory_order_relaxed);
        return;
    }
    if (params.outputBinaryShader == nullptr) {
        g_failureCount.fetch_add(1, std::memory_order_relaxed);
        g_lastResult.store(E_POINTER, std::memory_order_relaxed);
        return;
    }

    const bool isVertex =
        (params.programTypeMask & kUnityShaderCompilerExtGPUProgramVS) != 0;
    const bool isPixel =
        (params.programTypeMask & kUnityShaderCompilerExtGPUProgramPS) != 0;
    if (isVertex == isPixel) {
        g_blockedCount.fetch_add(1, std::memory_order_relaxed);
        return;
    }
    g_callbackCount.fetch_add(1, std::memory_order_relaxed);
    if (!g_armed.load(std::memory_order_acquire)) {
        g_unarmedCallbackCount.fetch_add(1, std::memory_order_relaxed);
        return;
    }
    // Unity supplies the shell/variant bytecode here rather than the original
    // retail 0138/0139 DXBC. Do not compare it with the embedded bytes: the
    // explicit arm boundary, reserved keyword, D3D11 platform gate, and one
    // claim per stage are the bridge's opt-in contract.
    if (params.inputByteCode != nullptr)
        g_shellInputObservedCount.fetch_add(1, std::memory_order_relaxed);

    std::lock_guard<std::mutex> lock(g_shaderMutex);
    // Arming can be revoked while a compiler callback is waiting for the
    // stage-claim lock. Recheck under that lock so disarm is fail-closed.
    if (!g_armed.load(std::memory_order_acquire)) {
        g_unarmedCallbackCount.fetch_add(1, std::memory_order_relaxed);
        return;
    }
    bool& claimed = isVertex ? g_vertexClaimed : g_pixelClaimed;
    if (claimed) {
        g_blockedCount.fetch_add(1, std::memory_order_relaxed);
        return;
    }

    IUnityGraphicsD3D11* unityD3D11 = GetD3D11();
    ID3D11Device* device = unityD3D11 == nullptr ? nullptr : unityD3D11->GetDevice();
    if (device == nullptr) {
        g_failureCount.fetch_add(1, std::memory_order_relaxed);
        g_lastResult.store(E_POINTER, std::memory_order_relaxed);
        return;
    }

    IUnknown* replacement = nullptr;
    HRESULT result = E_INVALIDARG;
    if (isVertex) {
        ID3D11VertexShader* shader = nullptr;
        result = device->CreateVertexShader(
            g_EndfieldM23VertexDxbc, g_EndfieldM23VertexDxbcSize,
            nullptr, &shader);
        replacement = shader;
    } else {
        ID3D11PixelShader* shader = nullptr;
        result = device->CreatePixelShader(
            g_EndfieldM23PixelDxbc, g_EndfieldM23PixelDxbcSize,
            nullptr, &shader);
        replacement = shader;
    }
    g_lastResult.store(result, std::memory_order_relaxed);
    if (FAILED(result) || replacement == nullptr) {
        if (replacement != nullptr)
            replacement->Release();
        g_failureCount.fetch_add(1, std::memory_order_relaxed);
        return;
    }

    IUnknown* displaced = static_cast<IUnknown*>(*params.outputBinaryShader);
    *params.outputBinaryShader = replacement;
    if (displaced != nullptr)
        displaced->Release();

    // Keep one independent reference for render-event identity checks. Unity
    // owns the output reference above and may release it before the event.
    replacement->AddRef();
    if (isVertex) {
        g_lastVertexShader = static_cast<ID3D11VertexShader*>(replacement);
        g_vertexSwapCount.fetch_add(1, std::memory_order_relaxed);
    } else {
        g_lastPixelShader = static_cast<ID3D11PixelShader*>(replacement);
        g_pixelSwapCount.fetch_add(1, std::memory_order_relaxed);
    }
    claimed = true;
}

void ExecuteNativeExactDraw()
{
    IUnityGraphicsD3D11* unityD3D11 = GetD3D11();
    ID3D11Device* device = unityD3D11 == nullptr ? nullptr : unityD3D11->GetDevice();
    if (device == nullptr) {
        g_failureCount.fetch_add(1, std::memory_order_relaxed);
        g_lastResult.store(E_POINTER, std::memory_order_relaxed);
        return;
    }
    ID3D11DeviceContext* context = nullptr;
    device->GetImmediateContext(&context);
    if (context == nullptr) {
        g_failureCount.fetch_add(1, std::memory_order_relaxed);
        g_lastResult.store(E_POINTER, std::memory_order_relaxed);
        return;
    }

    // Reuse the already-pinned fixture. Mode 0 is the original one-pixel exact
    // pair diagnostic. Mode 1 is the first visual path: real five PNG
    // textures, recovered high-neutral b4/b2 constants, neutral reciprocal
    // exposure, and white COLOR0/TEXCOORD5 input into the exact PS. It writes
    // a deterministic 16x16 float grid which is copied through the bridge ABI.
    EndfieldM23DxbcValidation report = {};
    std::array<float, kVisualGridFloatCount> visualGrid{};
    const std::uint32_t visualMode = g_visualMode.load(std::memory_order_acquire);
    HRESULT result = visualMode == kVisualModeExactTexturesHighNeutralRgb
        ? EndfieldOriginalM23DxbcValidateExactTexturesHighNeutralRgbGateWithGrid(
            device, context, &report, visualGrid.data(), kVisualGridFloatCount)
        : EndfieldOriginalM23DxbcValidate(device, context, &report);
    g_lastResult.store(result, std::memory_order_relaxed);
    g_nativeDrawIssued.store(report.drawIssued, std::memory_order_relaxed);
    g_nativeReadbackFinite.store(report.readbackFinite, std::memory_order_relaxed);
    g_nativeReadbackChanged.store(report.readbackChanged, std::memory_order_relaxed);
    g_nativeReadbackChangedFromZero.store(
        report.readbackChangedFromZero, std::memory_order_relaxed);
    g_nativeOutputMask.store(
        (report.drawIssued ? 1u : 0u) |
        (report.readbackFinite ? 2u : 0u) |
        (report.readbackChanged ? 4u : 0u) |
        (report.readbackChangedFromZero ? 8u : 0u),
        std::memory_order_relaxed);
    // Publish the controlled fixture's identity masks, not Unity's transient
    // post-DrawMesh state observed by event 1.
    g_vertexConstantBufferMask.store(report.vsConstantBufferBindingMask,
                                     std::memory_order_relaxed);
    g_vertexShaderResourceMask.store(report.vertexShaderResourceBindingMask,
                                      std::memory_order_relaxed);
    g_pixelConstantBufferMask.store(report.psConstantBufferBindingMask,
                                    std::memory_order_relaxed);
    g_pixelShaderResourceMask.store(report.shaderResourceBindingMask,
                                    std::memory_order_relaxed);
    g_pixelSamplerMask.store(report.samplerBindingMask,
                             std::memory_order_relaxed);
    {
        std::lock_guard<std::mutex> lock(g_readbackMutex);
        std::memcpy(g_nativeReadback.data(), report.readback,
                    sizeof(report.readback));
        if (visualMode == kVisualModeExactTexturesHighNeutralRgb)
            std::memcpy(g_visualGrid.data(), visualGrid.data(),
                        sizeof(float) * kVisualGridFloatCount);
    }
    if (visualMode == kVisualModeExactTexturesHighNeutralRgb) {
        const std::uint32_t configMask =
            (report.exactTextureSourceHashMask == 0x1fu ? 1u : 0u) |
            (report.exactTextureDecodeMask == 0x1fu ? 2u : 0u) |
            (report.highNeutralDomainMask == 1u ? 4u : 0u) |
            (report.diagnosticB2GateMask == 1u ? 8u : 0u) |
            16u | // reciprocal exposure = 1, the recovered neutral producer
            32u | // diagnostic VS COLOR0/TEXCOORD5 = white
            (report.exactTextureCausalOverrideMask == 1u ? 64u : 0u);
        g_visualConfigMask.store(configMask, std::memory_order_relaxed);
        g_visualGridSize.store(report.exactTextureGridSize,
                                std::memory_order_relaxed);
        g_visualGridFinitePixels.store(report.exactTextureGridFinitePixels,
                                       std::memory_order_relaxed);
        g_visualGridNonzeroPixels.store(report.exactTextureGridNonzeroPixels,
                                        std::memory_order_relaxed);
        g_visualGridRgbNonzeroPixels.store(report.exactTextureGridRgbNonzeroPixels,
                                           std::memory_order_relaxed);
        g_visualGridAlphaNonzeroPixels.store(report.exactTextureGridAlphaNonzeroPixels,
                                             std::memory_order_relaxed);
        g_visualGridValid.store(
            SUCCEEDED(result) && configMask == kVisualConfigAllBits &&
            report.exactTextureGridSize == kVisualGridSize &&
            report.exactTextureGridFinitePixels == kVisualGridSize * kVisualGridSize
                ? 1u : 0u,
            std::memory_order_relaxed);
    }
    g_exactShaderBound.store(
        report.vsBindingMask == 1u && report.psBindingMask == 1u ? 1u : 0u,
        std::memory_order_relaxed);
    if (SUCCEEDED(result) && report.drawIssued != 0u)
        g_nativeExecutionCount.fetch_add(1, std::memory_order_relaxed);
    else
        g_failureCount.fetch_add(1, std::memory_order_relaxed);

    // The fixture intentionally owns the immediate context for this event.
    // Clear all temporary bindings before returning; event 3 then releases
    // retained compiler-created shader references on the render thread.
    context->ClearState();
    context->Flush();
    g_nativeStateCleared.store(1u, std::memory_order_relaxed);
    context->Release();
}

void CaptureRealDrawState(bool afterDraw)
{
    RealDrawSnapshot snapshot;
    IUnityGraphicsD3D11* unityD3D11 = GetD3D11();
    ID3D11Device* device = unityD3D11 == nullptr ? nullptr : unityD3D11->GetDevice();
    if (device == nullptr) {
        g_failureCount.fetch_add(1, std::memory_order_relaxed);
        g_lastResult.store(E_POINTER, std::memory_order_relaxed);
        return;
    }
    ID3D11DeviceContext* context = nullptr;
    device->GetImmediateContext(&context);
    if (context == nullptr) {
        g_failureCount.fetch_add(1, std::memory_order_relaxed);
        g_lastResult.store(E_POINTER, std::memory_order_relaxed);
        return;
    }

    ID3D11VertexShader* vertex = nullptr;
    ID3D11PixelShader* pixel = nullptr;
    ID3D11VertexShader* expectedVertex = nullptr;
    ID3D11PixelShader* expectedPixel = nullptr;
    context->VSGetShader(&vertex, nullptr, nullptr);
    context->PSGetShader(&pixel, nullptr, nullptr);
    {
        std::lock_guard<std::mutex> lock(g_shaderMutex);
        expectedVertex = g_lastVertexShader;
        expectedPixel = g_lastPixelShader;
        if (expectedVertex != nullptr) expectedVertex->AddRef();
        if (expectedPixel != nullptr) expectedPixel->AddRef();
    }
    snapshot.vertexShaderBound = vertex != nullptr ? 1u : 0u;
    snapshot.pixelShaderBound = pixel != nullptr ? 1u : 0u;
    snapshot.exactShaderBound = expectedVertex != nullptr && expectedPixel != nullptr &&
        vertex == expectedVertex && pixel == expectedPixel ? 1u : 0u;

    ID3D11Buffer* vsBuffers[5] = {};
    ID3D11ShaderResourceView* vsResources[1] = {};
    ID3D11Buffer* psBuffers[5] = {};
    ID3D11ShaderResourceView* psResources[5] = {};
    ID3D11SamplerState* psSamplers[5] = {};
    context->VSGetConstantBuffers(0, 5, vsBuffers);
    context->VSGetShaderResources(0, 1, vsResources);
    context->PSGetConstantBuffers(0, 5, psBuffers);
    context->PSGetShaderResources(0, 5, psResources);
    context->PSGetSamplers(0, 5, psSamplers);
    ID3D11Buffer* vertexCb3 = vsBuffers[3];
    if (vertexCb3 != nullptr) vertexCb3->AddRef();
    for (std::uint32_t i = 0; i < 5; ++i) {
        if (vsBuffers[i] != nullptr) { snapshot.vertexConstantBufferMask |= 1u << i; vsBuffers[i]->Release(); }
        if (psBuffers[i] != nullptr) { snapshot.pixelConstantBufferMask |= 1u << i; psBuffers[i]->Release(); }
        if (psResources[i] != nullptr) { snapshot.pixelShaderResourceMask |= 1u << i; psResources[i]->Release(); }
        if (psSamplers[i] != nullptr) { snapshot.pixelSamplerMask |= 1u << i; psSamplers[i]->Release(); }
    }
    if (vsResources[0] != nullptr) { snapshot.vertexShaderResourceMask = 1u; vsResources[0]->Release(); }

    // Read only the VS b3 resource observed at this exact event boundary.
    // CopyResource/Map operate on a staging buffer and do not bind, clear, or
    // otherwise mutate the Unity context. Require the recovered 224-byte
    // contract before publishing any bytes.
    if (vertexCb3 != nullptr) {
        D3D11_BUFFER_DESC sourceDescription = {};
        vertexCb3->GetDesc(&sourceDescription);
        snapshot.vertexCb3ByteWidth = sourceDescription.ByteWidth;
        if (sourceDescription.ByteWidth == kRealDrawVsCb3ByteCount) {
            D3D11_BUFFER_DESC stagingDescription = {};
            stagingDescription.ByteWidth = kRealDrawVsCb3ByteCount;
            stagingDescription.Usage = D3D11_USAGE_STAGING;
            stagingDescription.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
            ID3D11Buffer* staging = nullptr;
            const HRESULT createResult = device->CreateBuffer(&stagingDescription, nullptr, &staging);
            if (SUCCEEDED(createResult) && staging != nullptr) {
                context->CopyResource(staging, vertexCb3);
                D3D11_MAPPED_SUBRESOURCE mapped = {};
                const HRESULT mapResult = context->Map(staging, 0, D3D11_MAP_READ, 0, &mapped);
                if (SUCCEEDED(mapResult) && mapped.pData != nullptr) {
                    std::memcpy(snapshot.vertexCb3Bytes.data(), mapped.pData,
                                kRealDrawVsCb3ByteCount);
                    snapshot.vertexCb3CaptureStatus = 1u;
                    context->Unmap(staging, 0);
                } else {
                    snapshot.vertexCb3CaptureStatus = 3u;
                }
                staging->Release();
            } else {
                snapshot.vertexCb3CaptureStatus = 3u;
            }
        } else {
            snapshot.vertexCb3CaptureStatus = 2u;
        }
        vertexCb3->Release();
    }

    ID3D11InputLayout* inputLayout = nullptr;
    ID3D11Buffer* vertexBuffers[8] = {};
    UINT strides[8] = {}, offsets[8] = {};
    context->IAGetInputLayout(&inputLayout);
    context->IAGetVertexBuffers(0, 8, vertexBuffers, strides, offsets);
    snapshot.inputLayoutBound = inputLayout != nullptr ? 1u : 0u;
    for (std::uint32_t i = 0; i < 8; ++i) {
        if (vertexBuffers[i] != nullptr) {
            snapshot.vertexBufferMask |= 1u << i;
            vertexBuffers[i]->Release();
        }
        snapshot.vertexStrides[i] = strides[i];
        snapshot.vertexOffsets[i] = offsets[i];
    }
    snapshot.vertexBufferBound = (snapshot.vertexBufferMask & 1u) != 0u ? 1u : 0u;
    snapshot.vertexStride = snapshot.vertexStrides[0];
    snapshot.vertexOffset = snapshot.vertexOffsets[0];
    if (inputLayout != nullptr) inputLayout->Release();

    ID3D11Buffer* indexBuffer = nullptr;
    DXGI_FORMAT indexFormat = DXGI_FORMAT_UNKNOWN;
    UINT indexOffset = 0;
    context->IAGetIndexBuffer(&indexBuffer, &indexFormat, &indexOffset);
    snapshot.indexBufferBound = indexBuffer != nullptr ? 1u : 0u;
    snapshot.indexFormat = static_cast<std::uint32_t>(indexFormat);
    if (indexBuffer != nullptr) indexBuffer->Release();

    D3D11_PRIMITIVE_TOPOLOGY topology = D3D11_PRIMITIVE_TOPOLOGY_UNDEFINED;
    context->IAGetPrimitiveTopology(&topology);
    snapshot.topology = topology == D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST ? 1u : 0u;
    UINT viewportCount = 1;
    D3D11_VIEWPORT viewport = {};
    context->RSGetViewports(&viewportCount, &viewport);
    snapshot.viewport = viewportCount == 1 && viewport.Width > 0.0f && viewport.Height > 0.0f ? 1u : 0u;
    ID3D11RenderTargetView* renderTarget = nullptr;
    context->OMGetRenderTargets(1, &renderTarget, nullptr);
    snapshot.renderTargetBound = renderTarget != nullptr ? 1u : 0u;
    if (renderTarget != nullptr) renderTarget->Release();
    snapshot.captured = 1u;
    snapshot.observerDidNotClearState = 1u;

    if (vertex != nullptr) vertex->Release();
    if (pixel != nullptr) pixel->Release();
    if (expectedVertex != nullptr) expectedVertex->Release();
    if (expectedPixel != nullptr) expectedPixel->Release();
    context->Release();

    {
        std::lock_guard<std::mutex> lock(g_realDrawMutex);
        if (afterDraw) {
            g_realDrawAfter = snapshot;
            ++g_realDrawAfterCount;
        } else {
            g_realDrawBefore = snapshot;
            ++g_realDrawBeforeCount;
        }
    }
}

std::uint32_t RealDrawBindingMask(const RealDrawSnapshot& snapshot)
{
    return (snapshot.captured ? 1u : 0u) |
        (snapshot.exactShaderBound ? 1u << 1 : 0u) |
        (snapshot.inputLayoutBound ? 1u << 2 : 0u) |
        (snapshot.vertexBufferBound ? 1u << 3 : 0u) |
        (snapshot.renderTargetBound ? 1u << 4 : 0u) |
        (snapshot.topology ? 1u << 5 : 0u) |
        (snapshot.viewport ? 1u << 6 : 0u) |
        (snapshot.observerDidNotClearState ? 1u << 7 : 0u);
}

void UNITY_INTERFACE_API InspectBindings(int eventId)
{
    if (eventId == 3) {
        // SetArmed(0) only flips the gate. Queue event 3 with
        // GL.IssuePluginEvent before unloading/rearming so COM references are
        // released on the render thread after prior inspection callbacks.
        g_armed.store(false, std::memory_order_release);
        ReleaseShaderReferences();
        g_exactShaderBound.store(0, std::memory_order_relaxed);
        g_vertexConstantBufferMask.store(0, std::memory_order_relaxed);
        g_vertexShaderResourceMask.store(0, std::memory_order_relaxed);
        g_pixelConstantBufferMask.store(0, std::memory_order_relaxed);
        g_pixelShaderResourceMask.store(0, std::memory_order_relaxed);
        g_pixelSamplerMask.store(0, std::memory_order_relaxed);
        g_cleanupPending.store(false, std::memory_order_release);
        g_cleanupCount.fetch_add(1, std::memory_order_relaxed);
        g_renderEventCount.fetch_add(1, std::memory_order_relaxed);
        g_lastEventId.store(3u, std::memory_order_relaxed);
        return;
    }
    if (!g_armed.load(std::memory_order_acquire)) {
        g_ignoredRenderEventCount.fetch_add(1, std::memory_order_relaxed);
        return;
    }
    if (eventId == 4 || eventId == 5) {
        // These are deliberately observation-only. In particular, do not
        // call ExecuteNativeExactDraw or ClearState here: the caller is
        // placing event 4/5 around a real Unity DrawMesh and needs the actual
        // post-draw bindings to remain untouched for subsequent work.
        CaptureRealDrawState(eventId == 5);
        g_renderEventCount.fetch_add(1, std::memory_order_relaxed);
        g_lastEventId.store(static_cast<std::uint32_t>(eventId), std::memory_order_relaxed);
        return;
    }
    if (eventId == 2) {
        ExecuteNativeExactDraw();
        g_renderEventCount.fetch_add(1, std::memory_order_relaxed);
        g_lastEventId.store(2u, std::memory_order_relaxed);
        return;
    }
    if (eventId != 1) {
        g_ignoredRenderEventCount.fetch_add(1, std::memory_order_relaxed);
        return;
    }
    IUnityGraphicsD3D11* unityD3D11 = GetD3D11();
    ID3D11Device* device = unityD3D11 == nullptr ? nullptr : unityD3D11->GetDevice();
    if (device == nullptr) {
        g_failureCount.fetch_add(1, std::memory_order_relaxed);
        g_lastResult.store(E_POINTER, std::memory_order_relaxed);
        return;
    }
    ID3D11DeviceContext* context = nullptr;
    device->GetImmediateContext(&context);
    if (context == nullptr) {
        g_failureCount.fetch_add(1, std::memory_order_relaxed);
        g_lastResult.store(E_POINTER, std::memory_order_relaxed);
        return;
    }

    ID3D11VertexShader* vertex = nullptr;
    ID3D11PixelShader* pixel = nullptr;
    context->VSGetShader(&vertex, nullptr, nullptr);
    context->PSGetShader(&pixel, nullptr, nullptr);
    ID3D11VertexShader* expectedVertex = nullptr;
    ID3D11PixelShader* expectedPixel = nullptr;
    {
        std::lock_guard<std::mutex> lock(g_shaderMutex);
        expectedVertex = g_lastVertexShader;
        expectedPixel = g_lastPixelShader;
        if (expectedVertex != nullptr) expectedVertex->AddRef();
        if (expectedPixel != nullptr) expectedPixel->AddRef();
    }
    g_exactShaderBound.store(
        expectedVertex != nullptr && expectedPixel != nullptr &&
        vertex == expectedVertex && pixel == expectedPixel ? 1u : 0u,
        std::memory_order_relaxed);

    ID3D11Buffer* vsBuffers[5] = {};
    ID3D11ShaderResourceView* vsResources[1] = {};
    ID3D11Buffer* psBuffers[5] = {};
    ID3D11ShaderResourceView* psResources[5] = {};
    ID3D11SamplerState* psSamplers[5] = {};
    context->VSGetConstantBuffers(0, 5, vsBuffers);
    context->VSGetShaderResources(0, 1, vsResources);
    context->PSGetConstantBuffers(0, 5, psBuffers);
    context->PSGetShaderResources(0, 5, psResources);
    context->PSGetSamplers(0, 5, psSamplers);
    std::uint32_t vsCb = 0, vsSrv = 0, psCb = 0, psSrv = 0, psSamp = 0;
    for (std::uint32_t i = 0; i < 5; ++i) {
        if (vsBuffers[i] != nullptr) { vsCb |= 1u << i; vsBuffers[i]->Release(); }
        if (psBuffers[i] != nullptr) { psCb |= 1u << i; psBuffers[i]->Release(); }
        if (psResources[i] != nullptr) { psSrv |= 1u << i; psResources[i]->Release(); }
        if (psSamplers[i] != nullptr) { psSamp |= 1u << i; psSamplers[i]->Release(); }
    }
    if (vsResources[0] != nullptr) { vsSrv = 1u; vsResources[0]->Release(); }
    if (vertex != nullptr) vertex->Release();
    if (pixel != nullptr) pixel->Release();
    context->Release();

    g_vertexConstantBufferMask.store(vsCb, std::memory_order_relaxed);
    g_vertexShaderResourceMask.store(vsSrv, std::memory_order_relaxed);
    g_pixelConstantBufferMask.store(psCb, std::memory_order_relaxed);
    g_pixelShaderResourceMask.store(psSrv, std::memory_order_relaxed);
    g_pixelSamplerMask.store(psSamp, std::memory_order_relaxed);
    g_renderEventCount.fetch_add(1, std::memory_order_relaxed);
    g_lastEventId.store(static_cast<std::uint32_t>(eventId), std::memory_order_relaxed);
    if (eventId == 2 && g_exactShaderBound.load(std::memory_order_relaxed) != 0)
        g_nativeExecutionCount.fetch_add(1, std::memory_order_relaxed);
    if (expectedVertex != nullptr) expectedVertex->Release();
    if (expectedPixel != nullptr) expectedPixel->Release();
}

} // namespace

extern "C" void UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
UnityPluginLoad(IUnityInterfaces* unityInterfaces)
{
    g_unityInterfaces = unityInterfaces;
    g_pluginLoadCount.fetch_add(1, std::memory_order_relaxed);
    g_armed.store(false, std::memory_order_release);
    ResetArmedState();
}

extern "C" void UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API UnityPluginUnload()
{
    g_armed.store(false, std::memory_order_release);
    ReleaseShaderReferences();
    g_unityInterfaces = nullptr;
}

extern "C" void UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
UnityShaderCompilerExtEvent(UnityShaderCompilerExtEventType eventType, void* data)
{
    if (eventType == kUnityShaderCompilerExtEventPluginConfigure) {
        g_configureCount.fetch_add(1, std::memory_order_relaxed);
        auto* configure = static_cast<IUnityShaderCompilerExtPluginConfigure*>(data);
        if (configure == nullptr) return;
        configure->ReserveKeyword(kReservedKeyword);
        configure->SetGPUProgramCompilerMask(
            (1u << kUnityShaderCompilerExtGPUProgramTargetDX11VertexSM50) |
            (1u << kUnityShaderCompilerExtGPUProgramTargetDX11PixelSM50));
        configure->SetShaderProgramMask(
            kUnityShaderCompilerExtGPUProgramVS | kUnityShaderCompilerExtGPUProgramPS);
        return;
    }
    if (eventType == kUnityShaderCompilerExtEventCreateCustomBinaryVariant && data != nullptr)
        ReplaceD3D11Shader(*static_cast<UnityShaderCompilerExtCustomBinaryVariantParams*>(data));
}

extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetContractVersion() { return kContractVersion; }
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetPluginLoadCount() { return g_pluginLoadCount.load(); }
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetConfigureCount() { return g_configureCount.load(); }
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeSetVisualMode(std::uint32_t mode)
{
    // Mode changes are only accepted while disarmed. This prevents a managed
    // caller from changing the fixture contract between shader compilation
    // and the render event that consumes it.
    if (mode > kVisualModeExactTexturesHighNeutralRgb ||
        g_armed.load(std::memory_order_acquire))
        return 0u;
    g_visualMode.store(mode, std::memory_order_release);
    return 1u;
}
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetVisualMode() { return g_visualMode.load(); }
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeSetArmed(std::uint32_t armed)
{
    if (armed != 0u) {
        g_armed.store(false, std::memory_order_release);
        ResetArmedState();
        g_cleanupPending.store(false, std::memory_order_release);
        g_armed.store(true, std::memory_order_release);
    } else {
        g_armed.store(false, std::memory_order_release);
        // COM cleanup is intentionally deferred to render event ID 3.
        g_cleanupPending.store(true, std::memory_order_release);
    }
    return g_armed.load(std::memory_order_acquire) ? 1u : 0u;
}
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetArmed() { return g_armed.load() ? 1u : 0u; }
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetCallbackCount() { return g_callbackCount.load(); }
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetUnarmedCallbackCount() { return g_unarmedCallbackCount.load(); }
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetPlatformBlockedCount() { return g_platformBlockedCount.load(); }
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetShellInputObservedCount() { return g_shellInputObservedCount.load(); }
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetBlockedCount() { return g_blockedCount.load(); }
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetVertexSwapCount() { return g_vertexSwapCount.load(); }
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetPixelSwapCount() { return g_pixelSwapCount.load(); }
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetFailureCount() { return g_failureCount.load(); }
extern "C" std::int32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetLastResult() { return g_lastResult.load(); }
extern "C" UnityRenderingEvent UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetRenderEventFunc() { return InspectBindings; }
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetRenderEventCount() { return g_renderEventCount.load(); }
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetIgnoredRenderEventCount() { return g_ignoredRenderEventCount.load(); }
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetCleanupCount() { return g_cleanupCount.load(); }
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetCleanupPending() { return g_cleanupPending.load() ? 1u : 0u; }
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetNativeExecutionCount() { return g_nativeExecutionCount.load(); }
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetNativeDrawIssued() { return g_nativeDrawIssued.load(); }
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetNativeReadbackFinite() { return g_nativeReadbackFinite.load(); }
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetNativeReadbackChanged() { return g_nativeReadbackChanged.load(); }
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetNativeReadbackChangedFromZero() { return g_nativeReadbackChangedFromZero.load(); }
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetNativeOutputMask() { return g_nativeOutputMask.load(); }
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetNativeStateCleared() { return g_nativeStateCleared.load(); }
extern "C" void UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeCopyNativeReadback(float* outputFourFloats)
{
    if (outputFourFloats == nullptr) return;
    std::lock_guard<std::mutex> lock(g_readbackMutex);
    std::memcpy(outputFourFloats, g_nativeReadback.data(), sizeof(float) * 4u);
}
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetVisualGridSize() { return g_visualGridSize.load(); }
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetVisualGridValid() { return g_visualGridValid.load(); }
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetVisualConfigMask() { return g_visualConfigMask.load(); }
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetVisualGridFinitePixels() { return g_visualGridFinitePixels.load(); }
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetVisualGridNonzeroPixels() { return g_visualGridNonzeroPixels.load(); }
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetVisualGridRgbNonzeroPixels() { return g_visualGridRgbNonzeroPixels.load(); }
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetVisualGridAlphaNonzeroPixels() { return g_visualGridAlphaNonzeroPixels.load(); }
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeCopyVisualGrid(float* outputFloats,
                                             std::uint32_t outputFloatCount)
{
    if (outputFloats == nullptr ||
        g_visualGridValid.load(std::memory_order_acquire) == 0u)
        return 0u;
    const std::uint32_t count = outputFloatCount < kVisualGridFloatCount
        ? outputFloatCount : kVisualGridFloatCount;
    std::lock_guard<std::mutex> lock(g_readbackMutex);
    std::memcpy(outputFloats, g_visualGrid.data(), sizeof(float) * count);
    return count;
}
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetExactShaderBound() { return g_exactShaderBound.load(); }
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetVertexConstantBufferMask() { return g_vertexConstantBufferMask.load(); }
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetVertexShaderResourceMask() { return g_vertexShaderResourceMask.load(); }
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetPixelConstantBufferMask() { return g_pixelConstantBufferMask.load(); }
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetPixelShaderResourceMask() { return g_pixelShaderResourceMask.load(); }
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetPixelSamplerMask() { return g_pixelSamplerMask.load(); }
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetRealDrawBeforeCount()
{
    std::lock_guard<std::mutex> lock(g_realDrawMutex);
    return g_realDrawBeforeCount;
}
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetRealDrawAfterCount()
{
    std::lock_guard<std::mutex> lock(g_realDrawMutex);
    return g_realDrawAfterCount;
}
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetRealDrawBeforeBindingMask()
{
    std::lock_guard<std::mutex> lock(g_realDrawMutex);
    return RealDrawBindingMask(g_realDrawBefore);
}
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetRealDrawAfterBindingMask()
{
    std::lock_guard<std::mutex> lock(g_realDrawMutex);
    return RealDrawBindingMask(g_realDrawAfter);
}
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetRealDrawAfterVertexConstantBufferMask()
{
    std::lock_guard<std::mutex> lock(g_realDrawMutex);
    return g_realDrawAfter.vertexConstantBufferMask;
}
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetRealDrawAfterVertexShaderResourceMask()
{
    std::lock_guard<std::mutex> lock(g_realDrawMutex);
    return g_realDrawAfter.vertexShaderResourceMask;
}
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetRealDrawAfterPixelConstantBufferMask()
{
    std::lock_guard<std::mutex> lock(g_realDrawMutex);
    return g_realDrawAfter.pixelConstantBufferMask;
}
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetRealDrawAfterPixelShaderResourceMask()
{
    std::lock_guard<std::mutex> lock(g_realDrawMutex);
    return g_realDrawAfter.pixelShaderResourceMask;
}
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetRealDrawAfterPixelSamplerMask()
{
    std::lock_guard<std::mutex> lock(g_realDrawMutex);
    return g_realDrawAfter.pixelSamplerMask;
}
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetRealDrawAfterVertexStride()
{
    std::lock_guard<std::mutex> lock(g_realDrawMutex);
    return g_realDrawAfter.vertexStride;
}
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetRealDrawAfterVertexOffset()
{
    std::lock_guard<std::mutex> lock(g_realDrawMutex);
    return g_realDrawAfter.vertexOffset;
}
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetRealDrawAfterVertexBufferMask()
{
    std::lock_guard<std::mutex> lock(g_realDrawMutex);
    return g_realDrawAfter.vertexBufferMask;
}
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetRealDrawAfterVertexStrideAt(std::uint32_t slot)
{
    if (slot >= 8u) return 0u;
    std::lock_guard<std::mutex> lock(g_realDrawMutex);
    return g_realDrawAfter.vertexStrides[slot];
}
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetRealDrawAfterVertexOffsetAt(std::uint32_t slot)
{
    if (slot >= 8u) return 0u;
    std::lock_guard<std::mutex> lock(g_realDrawMutex);
    return g_realDrawAfter.vertexOffsets[slot];
}
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetRealDrawAfterIndexBufferBound()
{
    std::lock_guard<std::mutex> lock(g_realDrawMutex);
    return g_realDrawAfter.indexBufferBound;
}
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetRealDrawAfterIndexFormat()
{
    std::lock_guard<std::mutex> lock(g_realDrawMutex);
    return g_realDrawAfter.indexFormat;
}
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetRealDrawBeforeVsCb3Valid()
{
    std::lock_guard<std::mutex> lock(g_realDrawMutex);
    return g_realDrawBefore.vertexCb3CaptureStatus == 1u ? 1u : 0u;
}
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetRealDrawAfterVsCb3Valid()
{
    std::lock_guard<std::mutex> lock(g_realDrawMutex);
    return g_realDrawAfter.vertexCb3CaptureStatus == 1u ? 1u : 0u;
}
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetRealDrawBeforeVsCb3ByteWidth()
{
    std::lock_guard<std::mutex> lock(g_realDrawMutex);
    return g_realDrawBefore.vertexCb3ByteWidth;
}
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetRealDrawAfterVsCb3ByteWidth()
{
    std::lock_guard<std::mutex> lock(g_realDrawMutex);
    return g_realDrawAfter.vertexCb3ByteWidth;
}
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeCopyRealDrawBeforeVsCb3(
    std::uint8_t* outputBytes, std::uint32_t outputByteCount)
{
    if (outputBytes == nullptr) return 0u;
    std::lock_guard<std::mutex> lock(g_realDrawMutex);
    if (g_realDrawBefore.vertexCb3CaptureStatus != 1u) return 0u;
    const std::uint32_t count = outputByteCount < kRealDrawVsCb3ByteCount
        ? outputByteCount : kRealDrawVsCb3ByteCount;
    std::memcpy(outputBytes, g_realDrawBefore.vertexCb3Bytes.data(), count);
    return count;
}
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeCopyRealDrawAfterVsCb3(
    std::uint8_t* outputBytes, std::uint32_t outputByteCount)
{
    if (outputBytes == nullptr) return 0u;
    std::lock_guard<std::mutex> lock(g_realDrawMutex);
    if (g_realDrawAfter.vertexCb3CaptureStatus != 1u) return 0u;
    const std::uint32_t count = outputByteCount < kRealDrawVsCb3ByteCount
        ? outputByteCount : kRealDrawVsCb3ByteCount;
    std::memcpy(outputBytes, g_realDrawAfter.vertexCb3Bytes.data(), count);
    return count;
}
extern "C" std::uint32_t UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API
EndfieldOriginalM23DxbcBridgeGetRealDrawObserverDidNotClearState()
{
    std::lock_guard<std::mutex> lock(g_realDrawMutex);
    return g_realDrawAfter.captured != 0u &&
        g_realDrawAfter.observerDidNotClearState != 0u ? 1u : 0u;
}
